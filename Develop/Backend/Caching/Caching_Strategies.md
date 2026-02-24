---
title: 캐싱 전략 (Caching Strategies)
tags: [backend, caching, redis, caffeine, cache-aside, write-through, write-behind, cache-invalidation]
updated: 2026-01-18
---

# 캐싱 전략 (Caching Strategies)

## 개요

캐시는 데이터를 빠르게 조회하기 위해 메모리에 저장한다. DB 부하를 줄이고 응답 속도를 개선한다. 하지만 캐시와 DB 간 일관성 문제가 발생한다. 적절한 캐싱 전략을 선택해야 한다.

### 왜 필요한가

**문제 상황:**

**시나리오:**
상품 상세 페이지. 초당 1,000개 요청.

**캐시 없이:**
```java
@GetMapping("/products/{id}")
public Product getProduct(@PathVariable Long id) {
    return productRepository.findById(id)
        .orElseThrow(() -> new ProductNotFoundException(id));
}
```

**문제:**
- 초당 1,000개 DB 쿼리
- 같은 상품을 반복 조회
- DB 부하 증가
- 응답 시간 느림 (평균 50ms)

**캐시 적용:**
```java
@Cacheable(value = "products", key = "#id")
@GetMapping("/products/{id}")
public Product getProduct(@PathVariable Long id) {
    return productRepository.findById(id)
        .orElseThrow(() -> new ProductNotFoundException(id));
}
```

**효과:**
- 첫 요청만 DB 조회
- 이후 요청은 캐시에서 반환
- DB 쿼리: 1,000 → 10 (새 상품만)
- 응답 시간: 50ms → 1ms

**99% DB 부하 감소, 50배 속도 향상**

## 캐시 패턴

### Cache-Aside (Lazy Loading)

**가장 많이 사용하는 패턴.** 애플리케이션이 캐시를 직접 관리한다.

**읽기:**
1. 캐시 확인
2. 캐시에 있으면 반환 (Cache Hit)
3. 없으면 DB 조회 (Cache Miss)
4. DB 결과를 캐시에 저장
5. 반환

**코드:**
```java
@Service
public class ProductService {
    
    private final ProductRepository productRepository;
    private final RedisTemplate<String, Product> redisTemplate;
    
    public Product getProduct(Long id) {
        String cacheKey = "product:" + id;
        
        // 1. 캐시 확인
        Product cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            return cached;  // Cache Hit
        }
        
        // 2. DB 조회 (Cache Miss)
        Product product = productRepository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException(id));
        
        // 3. 캐시 저장
        redisTemplate.opsForValue().set(cacheKey, product, Duration.ofMinutes(10));
        
        return product;
    }
}
```

**Spring Cache 추상화:**
```java
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) {
    return productRepository.findById(id)
        .orElseThrow(() -> new ProductNotFoundException(id));
}
```

**장점:**
- 간단하다
- 필요한 데이터만 캐시 (Lazy)
- 캐시 장애 시에도 동작 (DB로 직접 조회)

**단점:**
- Cache Miss 시 두 번의 호출 (캐시 + DB)
- 초기 요청이 느리다

### Write-Through

쓰기 시 캐시와 DB를 동시에 업데이트한다.

**동작:**
1. 캐시 업데이트
2. DB 업데이트
3. 성공 응답

**코드:**
```java
@Service
public class ProductService {
    
    @CachePut(value = "products", key = "#product.id")
    @Transactional
    public Product updateProduct(Product product) {
        // 1. DB 업데이트
        Product saved = productRepository.save(product);
        
        // 2. 캐시 업데이트 (@CachePut이 자동 처리)
        return saved;
    }
}
```

**수동 구현:**
```java
@Transactional
public Product updateProduct(Product product) {
    // 1. DB 저장
    Product saved = productRepository.save(product);
    
    // 2. 캐시 저장
    String cacheKey = "product:" + product.getId();
    redisTemplate.opsForValue().set(cacheKey, saved, Duration.ofMinutes(10));
    
    return saved;
}
```

**장점:**
- 캐시와 DB가 항상 동기화
- 읽기 성능 좋음

**단점:**
- 쓰기 성능 저하 (캐시 + DB 두 번)
- 캐시에 안 쓰는 데이터도 저장될 수 있음

### Write-Behind (Write-Back)

쓰기 시 캐시만 업데이트하고 나중에 DB에 반영한다.

**동작:**
1. 캐시 업데이트
2. 즉시 성공 응답
3. 비동기로 DB 업데이트 (배치)

**코드:**
```java
@Service
public class ProductService {
    
    private final Queue<Product> writeQueue = new ConcurrentLinkedQueue<>();
    
    public Product updateProduct(Product product) {
        // 1. 캐시 업데이트
        String cacheKey = "product:" + product.getId();
        redisTemplate.opsForValue().set(cacheKey, product);
        
        // 2. 큐에 추가
        writeQueue.offer(product);
        
        return product;
    }
    
    @Scheduled(fixedDelay = 5000)
    public void flushToDatabase() {
        List<Product> batch = new ArrayList<>();
        Product product;
        
        // 큐에서 가져오기
        while ((product = writeQueue.poll()) != null && batch.size() < 100) {
            batch.add(product);
        }
        
        if (!batch.isEmpty()) {
            // 배치로 DB 업데이트
            productRepository.saveAll(batch);
        }
    }
}
```

**장점:**
- 쓰기 성능이 매우 빠름
- DB 부하 감소 (배치 쓰기)

**단점:**
- 캐시 장애 시 데이터 손실 위험
- 캐시와 DB 불일치 기간 존재
- 구현 복잡

**사용 사례:**
- 좋아요 수, 조회수 (정확성이 덜 중요)
- 로그 집계
- 실시간 랭킹

### Read-Through

캐시가 DB 조회를 대신한다. 애플리케이션은 캐시만 접근한다.

**동작:**
1. 애플리케이션 → 캐시 요청
2. 캐시에 있으면 반환
3. 없으면 캐시가 DB 조회
4. 캐시에 저장 후 반환

**특징:**
- Cache-Aside와 비슷하지만 캐시가 주도
- Redis 같은 일반 캐시로는 구현 어려움
- 전용 솔루션 필요 (Ehcache with JSR-107)

## 로컬 캐시 vs 분산 캐시

### 로컬 캐시 (Caffeine)

애플리케이션 메모리에 저장.

**Caffeine 설정:**
```java
@Configuration
@EnableCaching
public class CacheConfig {
    
    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager cacheManager = new CaffeineCacheManager("products", "users");
        cacheManager.setCaffeine(Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(10))
            .recordStats());
        return cacheManager;
    }
}
```

**사용:**
```java
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

**장점:**
- 매우 빠름 (네트워크 없음)
- 간단함
- 비용 없음

**단점:**
- 서버마다 다른 캐시 (불일치)
- 메모리 제한
- 서버 재시작 시 캐시 소실

**사용 사례:**
- 설정 값 (변경 없음)
- 코드 테이블
- 서버별로 달라도 되는 데이터

### 분산 캐시 (Redis)

별도 서버에 저장. 모든 애플리케이션 서버가 공유.

**Redis 설정:**
```java
@Configuration
@EnableCaching
public class RedisConfig {
    
    @Bean
    public RedisConnectionFactory redisConnectionFactory() {
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName("localhost");
        config.setPort(6379);
        return new LettuceConnectionFactory(config);
    }
    
    @Bean
    public CacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new StringRedisSerializer()))
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer()));
        
        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(config)
            .build();
    }
}
```

**장점:**
- 모든 서버가 공유 (일관성)
- 메모리 확장 가능
- 영속성 (AOF/RDB)

**단점:**
- 네트워크 지연 (0.5-2ms)
- 비용 (인프라)
- 장애 시 영향 큼

**사용 사례:**
- 세션
- 사용자 데이터
- 여러 서버에서 접근하는 데이터

### 2단계 캐시 (L1 + L2)

로컬 캐시 (L1)와 분산 캐시 (L2)를 함께 사용.

**구조:**
```
요청 → L1 (Caffeine) → L2 (Redis) → DB
       0.01ms            1ms          50ms
```

**코드:**
```java
@Service
public class ProductService {
    
    private final LoadingCache<Long, Product> l1Cache;  // Caffeine
    private final RedisTemplate<String, Product> redis;  // Redis
    private final ProductRepository repository;
    
    public ProductService() {
        this.l1Cache = Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(Duration.ofMinutes(1))
            .build(this::loadFromL2);
    }
    
    public Product getProduct(Long id) {
        // L1 캐시 조회
        return l1Cache.get(id);
    }
    
    private Product loadFromL2(Long id) {
        // L2 캐시 (Redis) 조회
        String key = "product:" + id;
        Product product = redis.opsForValue().get(key);
        
        if (product != null) {
            return product;
        }
        
        // DB 조회
        product = repository.findById(id)
            .orElseThrow(() -> new ProductNotFoundException(id));
        
        // L2 캐시 저장
        redis.opsForValue().set(key, product, Duration.ofMinutes(10));
        
        return product;
    }
    
    public void updateProduct(Product product) {
        // DB 업데이트
        repository.save(product);
        
        // L2 캐시 업데이트
        String key = "product:" + product.getId();
        redis.opsForValue().set(key, product, Duration.ofMinutes(10));
        
        // L1 캐시 무효화
        l1Cache.invalidate(product.getId());
    }
}
```

**효과:**
- 대부분 L1에서 처리 (매우 빠름)
- L1 Miss 시 L2에서 처리 (빠름)
- 서버 간 일관성 유지 (L2 공유)

## 캐시 일관성

### 문제

캐시와 DB가 다른 값을 가질 수 있다.

**시나리오:**
```
서버 A: 상품 가격 변경 (10,000원 → 15,000원)
  1. DB 업데이트 (15,000원)
  2. 캐시 무효화 (삭제)

서버 B: 동시에 상품 조회
  1. 캐시 확인 (없음)
  2. DB 조회 (15,000원)
  3. 캐시 저장 (15,000원)

서버 C: 상품 조회
  1. 캐시 확인 (10,000원) ← 오래된 캐시
```

### 해결 1: Cache Invalidation

캐시를 삭제한다. 다음 조회 시 DB에서 가져온다.

```java
@CacheEvict(value = "products", key = "#id")
public void updateProduct(Long id, Product product) {
    productRepository.save(product);
}
```

**문제:**
삭제와 새로운 캐시 저장 사이에 짧은 불일치 기간 존재.

### 해결 2: Pub/Sub으로 캐시 동기화

업데이트 시 모든 서버에 알림.

**Redis Pub/Sub:**
```java
@Service
public class ProductService {
    
    private final RedisTemplate<String, String> redisTemplate;
    private final LoadingCache<Long, Product> localCache;
    
    public void updateProduct(Product product) {
        // 1. DB 업데이트
        productRepository.save(product);
        
        // 2. Redis 캐시 업데이트
        redisTemplate.opsForValue().set(
            "product:" + product.getId(), 
            product, 
            Duration.ofMinutes(10)
        );
        
        // 3. 모든 서버에 알림
        redisTemplate.convertAndSend(
            "product-updates", 
            product.getId().toString()
        );
    }
    
    @RedisMessageListener(topic = "product-updates")
    public void handleProductUpdate(String productId) {
        // 로컬 캐시 무효화
        localCache.invalidate(Long.parseLong(productId));
    }
}
```

**Listener 설정:**
```java
@Configuration
public class RedisConfig {
    
    @Bean
    public RedisMessageListenerContainer container(
            RedisConnectionFactory connectionFactory,
            MessageListenerAdapter listenerAdapter) {
        
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.addMessageListener(
            listenerAdapter, 
            new PatternTopic("product-updates")
        );
        return container;
    }
    
    @Bean
    public MessageListenerAdapter listenerAdapter(ProductService productService) {
        return new MessageListenerAdapter(productService, "handleProductUpdate");
    }
}
```

### 해결 3: Versioning

캐시에 버전을 포함한다.

```java
@Data
public class CachedProduct {
    private Long id;
    private String name;
    private Integer price;
    private Long version;  // 버전
    private LocalDateTime updatedAt;
}

@Service
public class ProductService {
    
    public Product getProduct(Long id) {
        String key = "product:" + id;
        CachedProduct cached = redis.opsForValue().get(key);
        
        if (cached != null) {
            // DB 버전 확인
            Long dbVersion = productRepository.getVersion(id);
            
            if (cached.getVersion().equals(dbVersion)) {
                return cached.toProduct();  // 최신
            }
            // 버전 불일치, DB 재조회
        }
        
        Product product = productRepository.findById(id).orElseThrow();
        redis.opsForValue().set(key, CachedProduct.from(product));
        return product;
    }
}
```

## 캐시 무효화

### TTL (Time To Live)

시간 기반 만료.

```java
// 10분 후 만료
redisTemplate.opsForValue().set(key, value, Duration.ofMinutes(10));

// Spring Cache
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

**application.yml:**
```yaml
spring:
  cache:
    redis:
      time-to-live: 600000  # 10분 (ms)
```

**장점:**
- 자동
- 간단

**단점:**
- 만료 전까지 오래된 데이터
- 적절한 TTL 설정 어려움

### 수동 무효화

업데이트 시 명시적으로 삭제.

```java
@CacheEvict(value = "products", key = "#id")
public void updateProduct(Long id, Product product) {
    productRepository.save(product);
}

// 전체 삭제
@CacheEvict(value = "products", allEntries = true)
public void updateAllProducts() {
    // ...
}
```

**수동:**
```java
redisTemplate.delete("product:" + id);
```

### 태그 기반 무효화

관련 캐시를 그룹으로 삭제.

```java
@Service
public class ProductService {
    
    public Product getProduct(Long id) {
        String key = "product:" + id;
        Product product = redis.opsForValue().get(key);
        
        if (product == null) {
            product = productRepository.findById(id).orElseThrow();
            
            // 캐시 저장 + 태그
            redis.opsForValue().set(key, product);
            redis.opsForSet().add("category:" + product.getCategoryId(), key);
        }
        
        return product;
    }
    
    public void updateCategory(Long categoryId) {
        // 해당 카테고리의 모든 상품 캐시 삭제
        Set<String> keys = redis.opsForSet().members("category:" + categoryId);
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
        redis.delete("category:" + categoryId);
    }
}
```

## 캐시 스탬피드 방지

### 문제

인기 있는 데이터의 캐시가 만료되면 동시에 많은 요청이 DB로 몰린다.

**시나리오:**
```
캐시 만료 (인기 상품)
  ↓
동시에 1,000개 요청
  ↓
1,000개 DB 쿼리 (동일한 상품)
  ↓
DB 과부하
```

### 해결 1: Lock

첫 요청만 DB 조회, 나머지는 대기.

```java
@Service
public class ProductService {
    
    private final ConcurrentHashMap<String, Lock> locks = new ConcurrentHashMap<>();
    
    public Product getProduct(Long id) {
        String key = "product:" + id;
        
        // 캐시 확인
        Product cached = redis.opsForValue().get(key);
        if (cached != null) {
            return cached;
        }
        
        // Lock 획득
        Lock lock = locks.computeIfAbsent(key, k -> new ReentrantLock());
        lock.lock();
        try {
            // Double-check (다른 스레드가 이미 저장했을 수 있음)
            cached = redis.opsForValue().get(key);
            if (cached != null) {
                return cached;
            }
            
            // DB 조회
            Product product = productRepository.findById(id).orElseThrow();
            
            // 캐시 저장
            redis.opsForValue().set(key, product, Duration.ofMinutes(10));
            
            return product;
        } finally {
            lock.unlock();
        }
    }
}
```

### 해결 2: Redis Lock

분산 환경에서 Lock.

```java
@Service
public class ProductService {
    
    private final RedissonClient redissonClient;
    
    public Product getProduct(Long id) {
        String key = "product:" + id;
        Product cached = redis.opsForValue().get(key);
        
        if (cached != null) {
            return cached;
        }
        
        // Redis 분산 Lock
        RLock lock = redissonClient.getLock("lock:product:" + id);
        try {
            // Lock 획득 시도 (최대 10초 대기, 5초 후 자동 해제)
            if (lock.tryLock(10, 5, TimeUnit.SECONDS)) {
                // Double-check
                cached = redis.opsForValue().get(key);
                if (cached != null) {
                    return cached;
                }
                
                // DB 조회
                Product product = productRepository.findById(id).orElseThrow();
                redis.opsForValue().set(key, product, Duration.ofMinutes(10));
                return product;
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            lock.unlock();
        }
        
        // Lock 획득 실패 시 DB 직접 조회
        return productRepository.findById(id).orElseThrow();
    }
}
```

### 해결 3: Probabilistic Early Expiration

만료 전에 미리 갱신.

```java
public Product getProduct(Long id) {
    String key = "product:" + id;
    Long ttl = redis.getExpire(key, TimeUnit.SECONDS);
    
    // 만료까지 1분 미만이고 랜덤으로 선택되면 갱신
    if (ttl != null && ttl < 60 && Math.random() < 0.1) {
        // 비동기로 갱신
        CompletableFuture.runAsync(() -> {
            Product product = productRepository.findById(id).orElseThrow();
            redis.opsForValue().set(key, product, Duration.ofMinutes(10));
        });
    }
    
    Product cached = redis.opsForValue().get(key);
    if (cached != null) {
        return cached;
    }
    
    // 캐시 없으면 DB 조회
    Product product = productRepository.findById(id).orElseThrow();
    redis.opsForValue().set(key, product, Duration.ofMinutes(10));
    return product;
}
```

## 실무 패턴

### 사용자 세션

**Redis:**
```java
@Service
public class SessionService {
    
    private final RedisTemplate<String, UserSession> redis;
    
    public void saveSession(String token, UserSession session) {
        redis.opsForValue().set(
            "session:" + token,
            session,
            Duration.ofHours(2)  // 2시간 만료
        );
    }
    
    public UserSession getSession(String token) {
        UserSession session = redis.opsForValue().get("session:" + token);
        
        if (session != null) {
            // 활동 시 TTL 갱신 (Sliding Window)
            redis.expire("session:" + token, Duration.ofHours(2));
        }
        
        return session;
    }
}
```

### API 응답 캐싱

```java
@RestController
public class ProductController {
    
    @GetMapping("/api/products/{id}")
    @Cacheable(value = "api:products", key = "#id")
    public ResponseEntity<ProductResponse> getProduct(@PathVariable Long id) {
        Product product = productService.getProduct(id);
        return ResponseEntity.ok()
            .cacheControl(CacheControl.maxAge(10, TimeUnit.MINUTES))
            .body(ProductResponse.from(product));
    }
}
```

### 랭킹/리더보드

**Redis Sorted Set:**
```java
@Service
public class LeaderboardService {
    
    private final RedisTemplate<String, String> redis;
    
    public void updateScore(String userId, double score) {
        redis.opsForZSet().add("leaderboard", userId, score);
    }
    
    public List<String> getTopUsers(int count) {
        Set<String> top = redis.opsForZSet()
            .reverseRange("leaderboard", 0, count - 1);
        return new ArrayList<>(top);
    }
    
    public Long getRank(String userId) {
        return redis.opsForZSet().reverseRank("leaderboard", userId);
    }
}
```

## 모니터링

### Caffeine Stats

```java
@Configuration
public class CacheConfig {
    
    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager();
        manager.setCaffeine(Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(10))
            .recordStats());  // 통계 활성화
        return manager;
    }
    
    @Scheduled(fixedRate = 60000)
    public void logCacheStats() {
        CaffeineCacheManager manager = (CaffeineCacheManager) cacheManager;
        
        for (String cacheName : manager.getCacheNames()) {
            CaffeineCache cache = (CaffeineCache) manager.getCache(cacheName);
            CacheStats stats = cache.getNativeCache().stats();
            
            log.info("Cache: {}, Hit Rate: {}, Evictions: {}", 
                cacheName,
                stats.hitRate(),
                stats.evictionCount());
        }
    }
}
```

### Redis Monitoring

```bash
# Redis 정보
redis-cli INFO stats

# 키 개수
redis-cli DBSIZE

# 메모리 사용량
redis-cli INFO memory

# 느린 쿼리
redis-cli SLOWLOG GET 10
```

## 참고

- Caffeine GitHub: https://github.com/ben-manes/caffeine
- Spring Cache: https://docs.spring.io/spring-framework/docs/current/reference/html/integration.html#cache
- Redis 공식 문서: https://redis.io/documentation
- Redisson: https://github.com/redisson/redisson


