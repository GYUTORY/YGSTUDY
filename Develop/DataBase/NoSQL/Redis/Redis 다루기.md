---
title: Redis 다루기 — 코드 패턴과 실무 트러블슈팅
tags: [database, nosql, redis, cache, spring-boot, node]
updated: 2026-03-27
---

# Redis 다루기

> Redis 내부 동작 원리와 아키텍처는 [Redis](Redis.md), 클러스터/센티널/분산락 심화는 [Redis 심화](Redis_Advanced.md) 참고.

---

## CLI 기본 패턴

```bash
# ── String ─────────────────────────────────────────
SET counter 0
INCR counter          # 1 (원자적 증가)
INCRBY counter 5      # 6
DECRBY counter 2      # 4
SET name "Alice" EX 60  # 60초 TTL
GETEX name EX 120       # 조회하면서 TTL 갱신

# ── Hash ───────────────────────────────────────────
HSET product:1 name "노트북" price 1500000 stock 10
HGET product:1 price          # "1500000"
HMGET product:1 name stock    # ["노트북", "10"]
HINCRBY product:1 stock -1    # 재고 감소 (원자적)
HEXISTS product:1 price       # 1

# ── List ───────────────────────────────────────────
RPUSH job:queue task1 task2 task3   # 우측 추가 (큐 IN)
LPOP job:queue                      # 좌측 제거 (큐 OUT) → "task1"
BRPOPLPUSH job:queue processing 0  # 블로킹 이동 (신뢰성 있는 큐)
LRANGE job:queue 0 -1              # 전체 조회
LLEN job:queue                     # 길이

# ── Set ────────────────────────────────────────────
SADD tags:post:1 redis nosql database
SISMEMBER tags:post:1 redis     # 1
SCARD tags:post:1               # 3
SUNION tags:post:1 tags:post:2  # 합집합
SINTER tags:post:1 tags:post:2  # 교집합

# ── Sorted Set ─────────────────────────────────────
ZADD leaderboard NX 1500 "player1"
ZADD leaderboard NX 2000 "player2"
ZINCRBY leaderboard 100 "player1"          # 1600
ZREVRANGE leaderboard 0 4 WITHSCORES      # 상위 5명 (내림차순)
ZRANK leaderboard "player1"               # 순위 (0부터)
ZRANGEBYSCORE leaderboard 1500 2000       # 스코어 범위 조회

# ── 공통 ───────────────────────────────────────────
SCAN 0 MATCH user:* COUNT 100  # 안전한 키 순회 (KEYS * 대신 사용)
TTL session:abc       # 남은 시간 (초)
PERSIST session:abc   # TTL 제거 (영구화)
TYPE product:1        # 데이터 타입 확인
OBJECT ENCODING user:1  # 내부 인코딩 확인
UNLINK large_key      # 비동기 삭제 (DEL 대신 큰 키에 사용)
```

---

## Node.js (ioredis) 패턴

```javascript
const Redis = require('ioredis');

const redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: 6379,
    password: process.env.REDIS_PASSWORD,
    db: 0,
    retryStrategy: (times) => Math.min(times * 50, 2000)
});

// ── Cache Aside ───────────────────────────────────
async function getProduct(productId) {
    const key = `product:${productId}`;
    const cached = await redis.get(key);
    if (cached) return JSON.parse(cached);

    const product = await db.findProduct(productId);
    if (product) await redis.setex(key, 300, JSON.stringify(product));
    return product;
}

async function invalidateProduct(productId) {
    await redis.del(`product:${productId}`);
}

// ── Rate Limiting (Fixed Window) ──────────────────
async function checkRateLimit(userId, limitPerMinute = 60) {
    const key = `ratelimit:${userId}:${Math.floor(Date.now() / 60000)}`;
    const count = await redis.incr(key);
    if (count === 1) await redis.expire(key, 60);
    return count <= limitPerMinute;
}

// ── Pipeline ──────────────────────────────────────
async function getUserDashboard(userId) {
    const pipeline = redis.pipeline();
    pipeline.hgetall(`user:${userId}`);
    pipeline.lrange(`user:${userId}:recent`, 0, 9);
    pipeline.zscore('leaderboard', userId);

    const results = await pipeline.exec();
    return {
        profile: results[0][1],
        recentActivity: results[1][1],
        score: results[2][1]
    };
}

// ── Pub/Sub ───────────────────────────────────────
// publisher
const pub = new Redis();
await pub.publish('order:events', JSON.stringify({
    type: 'ORDER_COMPLETED',
    orderId: 'order-001',
    userId: 'user-123'
}));

// subscriber (별도 커넥션 필수)
const sub = new Redis();
await sub.subscribe('order:events');
sub.on('message', (channel, message) => {
    const event = JSON.parse(message);
    console.log(`Received ${event.type}:`, event);
});
```

---

## Spring Boot 설정 및 패턴

### 기본 설정

```yaml
# application.yml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: 6379
      password: ${REDIS_PASSWORD:}
      timeout: 2000ms
      lettuce:
        pool:
          max-active: 10
          max-idle: 5
          min-idle: 2
```

### RedisTemplate 설정

```java
@Configuration
@EnableCaching
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory cf) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(cf);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory cf) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .serializeKeysWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(cf).cacheDefaults(config).build();
    }
}
```

### @Cacheable / @CacheEvict

```java
@Service
@RequiredArgsConstructor
public class ProductService {
    private final RedisTemplate<String, Object> redisTemplate;

    @Cacheable(value = "products", key = "#id", unless = "#result == null")
    public Product getProduct(Long id) {
        return productRepository.findById(id).orElse(null);
    }

    @CacheEvict(value = "products", key = "#product.id")
    public Product updateProduct(Product product) {
        return productRepository.save(product);
    }

    // Sorted Set 직접 사용
    public void addScore(String userId, double score) {
        redisTemplate.opsForZSet().add("leaderboard", userId, score);
    }

    public Set<Object> getTopRankers(int count) {
        return redisTemplate.opsForZSet().reverseRange("leaderboard", 0, count - 1);
    }
}
```

### 분산 락 (Redisson)

```java
// build.gradle: implementation 'org.redisson:redisson-spring-boot-starter:3.25.0'

@Service
@RequiredArgsConstructor
public class OrderService {
    private final RedissonClient redisson;

    public void processOrder(String orderId) {
        RLock lock = redisson.getLock("order:lock:" + orderId);
        try {
            // 최대 10초 대기, 30초 후 자동 해제
            if (lock.tryLock(10, 30, TimeUnit.SECONDS)) {
                try {
                    doProcessOrder(orderId);
                } finally {
                    lock.unlock();
                }
            } else {
                throw new RuntimeException("주문 처리 중");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

## Cache Stampede 대응

캐시 만료 시점에 수백 개 요청이 동시에 DB를 치는 현상이다. 트래픽이 높은 서비스에서는 반드시 대비해야 한다.

### 뮤텍스 락 방식

캐시가 없으면 락을 잡고, 락을 잡은 하나의 요청만 DB를 조회한다. 나머지 요청은 대기하거나 stale 데이터를 반환한다.

```java
@Service
@RequiredArgsConstructor
public class CacheService {
    private final RedisTemplate<String, String> redisTemplate;

    public String getWithMutex(String key, Supplier<String> loader, Duration ttl) {
        String value = redisTemplate.opsForValue().get(key);
        if (value != null) return value;

        String lockKey = "lock:" + key;
        // SET NX EX: 키가 없을 때만 설정 + 만료시간 (락 획득)
        Boolean locked = redisTemplate.opsForValue()
            .setIfAbsent(lockKey, "1", Duration.ofSeconds(5));

        if (Boolean.TRUE.equals(locked)) {
            try {
                // 락 획득 후 다시 확인 (다른 스레드가 이미 갱신했을 수 있음)
                value = redisTemplate.opsForValue().get(key);
                if (value != null) return value;

                value = loader.get();
                redisTemplate.opsForValue().set(key, value, ttl);
                return value;
            } finally {
                redisTemplate.delete(lockKey);
            }
        }

        // 락 획득 실패: 짧게 대기 후 재시도
        try { Thread.sleep(50); } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        return getWithMutex(key, loader, ttl);
    }
}
```

재귀 호출이 깊어지면 문제가 되므로, 실제로는 최대 재시도 횟수를 두거나 stale 데이터를 반환하는 방식을 섞는다.

### 확률적 조기 갱신 (Probabilistic Early Recomputation)

TTL이 완전히 만료되기 전에 확률적으로 미리 갱신한다. "XFetch" 알고리즘이라고도 부른다.

```java
/**
 * 캐시 값과 함께 실제 만료 시간을 저장한다.
 * 남은 시간이 짧을수록 갱신 확률이 높아진다.
 */
public String getWithEarlyRefresh(String key, Supplier<String> loader, Duration ttl) {
    String raw = redisTemplate.opsForValue().get(key);
    if (raw != null) {
        CacheEntry entry = deserialize(raw);
        long remaining = entry.expireAt - System.currentTimeMillis();
        // delta: DB 조회에 걸리는 예상 시간(ms)
        double delta = 200;
        double beta = 1.0;
        // remaining이 적을수록 갱신 확률이 높아짐
        boolean shouldRefresh = remaining > 0
            && (delta * beta * Math.log(Math.random())) * -1 >= remaining;

        if (!shouldRefresh) return entry.value;
    }

    String value = loader.get();
    CacheEntry entry = new CacheEntry(value, System.currentTimeMillis() + ttl.toMillis());
    redisTemplate.opsForValue().set(key, serialize(entry), ttl.plusSeconds(30));
    return value;
}
```

Redis TTL보다 논리적 만료 시간을 앞당겨 저장하는 게 핵심이다. Redis TTL은 논리적 만료 + 여유 시간(위 예제에서 30초)으로 설정해서, 갱신 중에도 stale 데이터를 제공할 수 있게 한다.

뮤텍스 락 vs 확률적 조기 갱신:
- 뮤텍스 락은 구현이 단순하고 DB 부하를 확실히 막는다. 대신 락 경합이 생기면 응답 지연이 발생한다.
- 확률적 조기 갱신은 락 없이 동작하므로 응답이 빠르다. 대신 간헐적으로 동시 갱신이 발생할 수 있다.
- 트래픽이 매우 높은 키에는 두 방식을 조합하는 경우도 있다.

---

## Hot Key 분산

특정 키에 읽기가 몰리면 해당 Redis 노드만 과부하가 걸린다. 클러스터 환경에서 특히 문제가 된다.

### 로컬 캐시 조합

Hot Key는 애플리케이션 로컬 캐시에 올려서 Redis 요청 자체를 줄인다.

```java
@Service
public class HotKeyService {
    private final RedisTemplate<String, String> redisTemplate;
    // Caffeine: JVM 내부 캐시. Redis 앞단에 둔다.
    private final Cache<String, String> localCache = Caffeine.newBuilder()
        .maximumSize(1000)
        .expireAfterWrite(Duration.ofSeconds(5))  // 짧은 TTL
        .build();

    public String get(String key) {
        // 1차: 로컬 캐시
        String value = localCache.getIfPresent(key);
        if (value != null) return value;

        // 2차: Redis
        value = redisTemplate.opsForValue().get(key);
        if (value != null) {
            localCache.put(key, value);
        }
        return value;
    }
}
```

주의할 점이 있다. 로컬 캐시 TTL이 길면 인스턴스마다 다른 데이터를 보여줄 수 있다. 일관성이 중요한 데이터에는 TTL을 1~5초 수준으로 짧게 잡아야 한다. Pub/Sub으로 캐시 무효화를 전파하는 방식도 있지만 복잡도가 올라간다.

### 키 샤딩 (Read Replica Spreading)

같은 데이터를 여러 키에 복제해서 읽기를 분산한다.

```java
public String getSharded(String key, int replicaCount) {
    // 요청마다 랜덤으로 레플리카 키를 선택
    int shard = ThreadLocalRandom.current().nextInt(replicaCount);
    String shardKey = key + ":shard:" + shard;
    return redisTemplate.opsForValue().get(shardKey);
}

/**
 * 원본 키를 갱신할 때 모든 샤드도 같이 갱신한다.
 * Pipeline으로 묶어서 RTT를 줄인다.
 */
public void setSharded(String key, String value, int replicaCount, Duration ttl) {
    redisTemplate.executePipelined((RedisCallback<Object>) connection -> {
        byte[] valBytes = value.getBytes();
        long seconds = ttl.getSeconds();
        for (int i = 0; i < replicaCount; i++) {
            byte[] k = (key + ":shard:" + i).getBytes();
            connection.stringCommands().setEx(k, seconds, valBytes);
        }
        return null;
    });
}
```

샤드 수를 3~5개로 잡으면 읽기 부하가 그만큼 분산된다. 쓰기 비용은 샤드 수만큼 늘어나므로 읽기 비율이 높은 키에만 쓴다.

---

## Big Key 분리

Hash가 수만 필드, List가 수십만 건이면 DEL 한 번에 수백 ms 블로킹이 발생한다. `MEMORY USAGE` 명령으로 확인해서 10MB 이상이면 분리를 고려한다.

### 진단

```bash
# 특정 키의 메모리 사용량
redis-cli MEMORY USAGE big:hash SAMPLES 0

# 큰 키 찾기 (--bigkeys)
redis-cli --bigkeys
# WARNING: 프로덕션에서는 부하가 있으므로 레플리카에서 실행한다
redis-cli -h replica-host --bigkeys
```

### Hash 분리

필드가 많은 Hash는 prefix로 분리한다.

```java
/**
 * user:profile 하나에 100개 필드가 있으면
 * user:profile:0, user:profile:1, ... 으로 나눈다.
 * 필드 이름의 해시값으로 버킷을 결정한다.
 */
public void hsetBucketed(String key, String field, String value, int bucketCount) {
    int bucket = Math.abs(field.hashCode() % bucketCount);
    String bucketKey = key + ":" + bucket;
    redisTemplate.opsForHash().put(bucketKey, field, value);
}

public Object hgetBucketed(String key, String field, int bucketCount) {
    int bucket = Math.abs(field.hashCode() % bucketCount);
    String bucketKey = key + ":" + bucket;
    return redisTemplate.opsForHash().get(bucketKey, field);
}
```

### List 분리

시계열 데이터나 로그를 List에 쌓는 경우, 시간 단위로 키를 나눈다.

```java
/**
 * log:events에 무한정 쌓는 대신
 * log:events:2026-03-27 같이 날짜별로 분리한다.
 */
public void appendLog(String baseKey, String entry) {
    String dateKey = baseKey + ":" + LocalDate.now();
    redisTemplate.opsForList().rightPush(dateKey, entry);
    // 7일 후 자동 삭제
    redisTemplate.expire(dateKey, Duration.ofDays(7));
}
```

Big Key를 삭제해야 할 때는 반드시 `UNLINK`를 쓴다. `DEL`은 메인 스레드에서 동기적으로 메모리를 해제하므로 그 시간 동안 모든 요청이 멈춘다. `UNLINK`는 백그라운드 스레드에서 해제한다.

---

## 직렬화 문제

Spring에서 Redis를 쓸 때 직렬화 관련 문제를 한 번쯤은 겪게 된다.

### ClassNotFoundException

`JdkSerializationRedisSerializer`(기본값)로 저장한 데이터는 Java 클래스의 패키지 경로까지 포함한다. 클래스를 다른 패키지로 옮기거나 이름을 바꾸면 역직렬화가 터진다.

```
org.springframework.data.redis.serializer.SerializationException:
Cannot deserialize; nested exception is
java.lang.ClassNotFoundException: com.old.package.ProductDto
```

해결: `GenericJackson2JsonRedisSerializer`나 `Jackson2JsonRedisSerializer`를 쓴다. JSON으로 저장하면 클래스 경로에 의존하지 않는다.

```java
// JDK 직렬화 (문제가 생기는 방식)
template.setValueSerializer(new JdkSerializationRedisSerializer());
// 저장 형태: 바이너리 (클래스 메타데이터 포함)

// JSON 직렬화 (권장)
template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
// 저장 형태: {"@class":"com.example.Product","id":1,"name":"노트북"}
```

`GenericJackson2JsonRedisSerializer`는 `@class` 필드에 클래스 정보를 넣는다. 이 방식에서도 클래스를 옮기면 문제가 생기지만, JSON이므로 수동으로 마이그레이션할 수 있다는 차이가 있다.

### 클래스 필드 변경 시 버전 호환성

캐시에 저장된 JSON에는 없는 필드가 새로 추가되거나, 있던 필드가 삭제된 경우 역직렬화가 실패할 수 있다.

```java
// ObjectMapper 설정으로 미지의 필드 무시
@Bean
public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory cf) {
    ObjectMapper om = new ObjectMapper();
    om.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    // null 필드도 허용
    om.setSerializationInclusion(JsonInclude.Include.NON_NULL);

    GenericJackson2JsonRedisSerializer serializer =
        new GenericJackson2JsonRedisSerializer(om);

    RedisTemplate<String, Object> template = new RedisTemplate<>();
    template.setConnectionFactory(cf);
    template.setKeySerializer(new StringRedisSerializer());
    template.setValueSerializer(serializer);
    return template;
}
```

배포할 때 주의해야 하는 순서:
1. 새 필드를 추가할 때: 역직렬화 측에서 `FAIL_ON_UNKNOWN_PROPERTIES = false`를 먼저 배포한다. 그 다음 새 필드를 포함한 코드를 배포한다.
2. 기존 필드를 삭제할 때: 직렬화 측에서 필드를 제거한 코드를 먼저 배포한다. 캐시 TTL이 지나 기존 데이터가 만료되면 역직렬화 측도 필드를 제거한다.
3. 필드 타입을 변경하는 경우(int → String 등): 캐시를 한 번 전체 무효화하는 게 가장 깔끔하다. 변환 로직을 넣으면 복잡도만 올라간다.

### String으로 단순화

캐시 대상이 단일 객체이고 직렬화 이슈를 피하고 싶으면, `StringRedisTemplate` + 수동 JSON 변환이 가장 단순하다.

```java
@Service
@RequiredArgsConstructor
public class SimpleCache {
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    public <T> T get(String key, Class<T> type) {
        String json = stringRedisTemplate.opsForValue().get(key);
        if (json == null) return null;
        return objectMapper.readValue(json, type);
    }

    public void set(String key, Object value, Duration ttl) {
        String json = objectMapper.writeValueAsString(value);
        stringRedisTemplate.opsForValue().set(key, json, ttl);
    }
}
```

이 방식은 `@class` 필드도 안 들어가고, 디버깅할 때 `redis-cli GET`으로 바로 읽을 수 있다.

---

## 모니터링 명령어

```bash
# 서버 상태
redis-cli INFO server | grep redis_version
redis-cli INFO memory | grep -E "used_memory_human|mem_fragmentation_ratio"
redis-cli INFO stats | grep -E "total_commands_processed|instantaneous_ops_per_sec"
redis-cli INFO clients | grep connected_clients

# 슬로우 로그 (10ms 이상)
redis-cli CONFIG SET slowlog-log-slower-than 10000
redis-cli SLOWLOG GET 10

# 실시간 모니터링
redis-cli --stat          # 초당 명령어 통계
redis-cli MONITOR         # 실시간 명령어 스트림 (프로덕션 주의: 부하 발생)

# 키 만료 통계
redis-cli INFO keyspace
# db0:keys=1234,expires=567,avg_ttl=300000

# 큰 키 탐지
redis-cli --bigkeys       # 레플리카에서 실행 권장
```

---

## 참조

- [Redis 명령어 레퍼런스](https://redis.io/commands/)
- [Redis 데이터 타입](https://redis.io/docs/data-types/)
- [ioredis GitHub](https://github.com/redis/ioredis)
- [Spring Data Redis 문서](https://docs.spring.io/spring-data/redis/reference/)
- [Redisson GitHub](https://github.com/redisson/redisson)
