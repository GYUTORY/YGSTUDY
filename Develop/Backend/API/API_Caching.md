---
title: API 캐싱 (HTTP Caching)
tags: [backend, api, caching, http, cdn, etag, cache-control]
updated: 2026-04-15
---

# API 캐싱 (HTTP Caching)

## 개요

API 응답을 매번 서버에서 새로 만들 필요는 없다. 같은 데이터를 반복해서 요청하는 클라이언트가 많고, 데이터가 자주 바뀌지 않는 경우라면 캐싱으로 서버 부하를 줄이고 응답 시간을 단축할 수 있다.

HTTP 캐싱은 크게 두 가지로 나뉜다. 클라이언트(브라우저)가 로컬에 저장한 응답을 재사용하는 방식과, 서버에 "내가 가진 데이터가 아직 유효한지" 확인하고 변경이 없으면 본문 없이 304를 받는 방식이다. 전자를 강한 캐시(Cache-Control), 후자를 조건부 요청(ETag, Last-Modified)이라 한다.

## Cache-Control 헤더

### 주요 디렉티브

캐시 동작을 제어하는 핵심 헤더다. 응답에 포함시키면 클라이언트와 중간 프록시(CDN 포함)가 이 지시를 따른다.

| 디렉티브 | 의미 |
|----------|------|
| `max-age=N` | N초 동안 캐시된 응답을 그대로 사용. 서버에 요청을 보내지 않는다 |
| `s-maxage=N` | CDN/프록시 전용 max-age. 브라우저는 무시한다 |
| `no-cache` | 캐시에 저장은 하되, 사용 전에 반드시 서버에 재검증 요청을 보낸다 |
| `no-store` | 아예 캐시에 저장하지 않는다. 민감한 데이터에 사용 |
| `private` | 브라우저만 캐시 가능. CDN이나 프록시는 캐시하면 안 된다 |
| `public` | 누구나 캐시 가능. CDN, 프록시 모두 캐시할 수 있다 |
| `must-revalidate` | max-age가 만료되면 반드시 서버에 재검증해야 한다. 만료된 캐시를 임의로 사용하지 못하게 막는다 |
| `stale-while-revalidate=N` | 만료 후 N초 동안은 만료된 캐시를 반환하면서 백그라운드에서 재검증한다 |

혼동하기 쉬운 부분이 있다. `no-cache`는 "캐시 금지"가 아니다. 캐시는 하되 매번 서버에 확인하라는 뜻이다. 캐시를 아예 금지하려면 `no-store`를 써야 한다.

### API 유형별 설정

```
# 거의 바뀌지 않는 설정 데이터 (국가 코드, 카테고리 목록 등)
Cache-Control: public, max-age=86400, s-maxage=604800

# 자주 조회하지만 실시간성이 중요한 데이터 (상품 목록 등)
Cache-Control: public, max-age=0, s-maxage=60, stale-while-revalidate=30

# 사용자별 데이터 (프로필, 설정 등)
Cache-Control: private, max-age=300

# 인증 정보, 결제 데이터
Cache-Control: no-store

# 자주 안 바뀌지만 바뀌면 즉시 반영돼야 하는 데이터
Cache-Control: public, no-cache
```

`max-age=0`과 `no-cache`의 차이는 미묘하다. 둘 다 서버에 재검증 요청을 보내는 건 같지만, `max-age=0`은 중간 프록시가 무시할 수 있고, `no-cache`는 무시할 수 없다. 엄밀한 제어가 필요하면 `no-cache`를 쓴다.

## 조건부 요청: ETag

### 동작 방식

서버가 응답할 때 리소스의 "버전 식별자"를 `ETag` 헤더에 담아 보낸다. 클라이언트가 다음 요청에서 `If-None-Match` 헤더에 이전에 받은 ETag 값을 보내면, 서버가 현재 리소스의 ETag와 비교한다. 같으면 304 Not Modified를 본문 없이 반환한다.

```
# 첫 번째 요청
GET /api/v1/products/123 HTTP/1.1

# 응답
HTTP/1.1 200 OK
ETag: "a1b2c3d4"
Cache-Control: no-cache
Content-Type: application/json

{"id": 123, "name": "상품A", "price": 50000}
```

```
# 두 번째 요청 (ETag 포함)
GET /api/v1/products/123 HTTP/1.1
If-None-Match: "a1b2c3d4"

# 변경 없으면
HTTP/1.1 304 Not Modified
ETag: "a1b2c3d4"

# 변경 있으면
HTTP/1.1 200 OK
ETag: "e5f6g7h8"
Content-Type: application/json

{"id": 123, "name": "상품A", "price": 45000}
```

304 응답에는 본문이 없으므로 대역폭을 절약할 수 있다. 수 MB짜리 목록 응답이라면 꽤 차이가 난다.

### ETag 생성 방법

#### 해시 기반

응답 본문을 해시해서 ETag를 만드는 방식이다. 데이터가 조금이라도 바뀌면 ETag가 달라진다.

```java
@GetMapping("/products/{id}")
public ResponseEntity<Product> getProduct(@PathVariable Long id,
        HttpServletRequest request) {

    Product product = productService.findById(id);
    String body = objectMapper.writeValueAsString(product);
    String etag = "\"" + DigestUtils.md5Hex(body) + "\"";

    String ifNoneMatch = request.getHeader("If-None-Match");
    if (etag.equals(ifNoneMatch)) {
        return ResponseEntity.status(HttpStatus.NOT_MODIFIED)
                .eTag(etag)
                .build();
    }

    return ResponseEntity.ok()
            .eTag(etag)
            .cacheControl(CacheControl.noCache())
            .body(product);
}
```

문제가 있다. 304를 반환하려고 해도 일단 DB에서 데이터를 가져와서 직렬화하고 해시를 계산해야 한다. DB 부하는 줄어들지 않고, 네트워크 대역폭만 절약된다. 목록 API에서 수천 건을 직렬화하고 해시하는 비용이 만만치 않다.

#### 버전/타임스탬프 기반

DB의 `updated_at` 컬럼이나 버전 번호로 ETag를 만든다. 데이터를 전부 읽지 않아도 ETag를 비교할 수 있다.

```java
@GetMapping("/products/{id}")
public ResponseEntity<Product> getProduct(@PathVariable Long id,
        HttpServletRequest request) {

    // updated_at만 조회하는 가벼운 쿼리
    Instant updatedAt = productService.getUpdatedAt(id);
    String etag = "\"" + id + "-" + updatedAt.toEpochMilli() + "\"";

    String ifNoneMatch = request.getHeader("If-None-Match");
    if (etag.equals(ifNoneMatch)) {
        return ResponseEntity.status(HttpStatus.NOT_MODIFIED)
                .eTag(etag)
                .build();
    }

    Product product = productService.findById(id);
    return ResponseEntity.ok()
            .eTag(etag)
            .cacheControl(CacheControl.noCache())
            .body(product);
}
```

이 방식이 실무에서 더 쓸만하다. 304를 반환할 때 전체 데이터를 읽지 않으니 DB 부하도 줄어든다. 다만 `updated_at`의 정밀도가 초 단위면, 1초 안에 두 번 수정될 때 같은 ETag가 나올 수 있다. 밀리초 단위로 저장하거나 별도 버전 컬럼을 두는 게 안전하다.

### Spring의 ShallowEtagHeaderFilter

Spring에는 응답 본문을 자동으로 해시해서 ETag를 붙여주는 필터가 있다.

```java
@Bean
public FilterRegistrationBean<ShallowEtagHeaderFilter> shallowEtagFilter() {
    FilterRegistrationBean<ShallowEtagHeaderFilter> registration =
            new FilterRegistrationBean<>(new ShallowEtagHeaderFilter());
    registration.addUrlPatterns("/api/*");
    return registration;
}
```

편하지만, 위에서 말한 해시 기반의 단점을 그대로 가진다. 매 요청마다 컨트롤러 로직이 전부 실행되고, 응답 본문을 메모리에 버퍼링한 뒤 해시를 계산한다. 대역폭만 절약하고 싶을 때 쓴다.

## 조건부 요청: Last-Modified

ETag와 비슷하지만 시간 기반이다. 서버가 `Last-Modified` 헤더로 리소스의 마지막 수정 시간을 알려주고, 클라이언트가 `If-Modified-Since`로 확인한다.

```
# 응답
HTTP/1.1 200 OK
Last-Modified: Tue, 15 Apr 2026 10:30:00 GMT
Cache-Control: no-cache

# 재요청
GET /api/v1/products/123 HTTP/1.1
If-Modified-Since: Tue, 15 Apr 2026 10:30:00 GMT

# 변경 없으면
HTTP/1.1 304 Not Modified
```

```java
@GetMapping("/products/{id}")
public ResponseEntity<Product> getProduct(@PathVariable Long id,
        WebRequest request) {

    Instant updatedAt = productService.getUpdatedAt(id);
    long lastModifiedMillis = updatedAt.toEpochMilli();

    // checkNotModified가 true를 반환하면 304
    if (request.checkNotModified(lastModifiedMillis)) {
        return null;
    }

    Product product = productService.findById(id);
    return ResponseEntity.ok()
            .lastModified(lastModifiedMillis)
            .body(product);
}
```

ETag와 Last-Modified를 동시에 쓸 수 있다. 이 경우 ETag가 우선한다. HTTP 스펙에서 `If-None-Match`가 있으면 `If-Modified-Since`는 무시하도록 정하고 있다. 둘 다 제공하면 ETag를 지원하는 클라이언트는 ETag를, 지원하지 않는 클라이언트는 Last-Modified를 사용하게 된다.

## CDN 캐시

### CDN 캐시 계층 구조

CDN을 API 앞에 두면 오리진 서버에 도달하는 요청 자체를 줄일 수 있다. 브라우저 캐시는 개별 사용자에게만 적용되지만, CDN 캐시는 모든 사용자에게 공유된다.

```
클라이언트 → CDN Edge → 오리진 서버
         ↑           ↑
    브라우저 캐시   CDN 캐시
   (private)     (shared)
```

`Cache-Control`의 `max-age`와 `s-maxage`를 분리해서 브라우저와 CDN의 캐시 시간을 다르게 설정하는 게 핵심이다.

```
# 브라우저는 10초, CDN은 5분 캐시
Cache-Control: public, max-age=10, s-maxage=300
```

이렇게 하면 CDN에서 5분 동안 캐시를 서빙하고, 브라우저는 10초마다 CDN에 재검증 요청을 보낸다. CDN 캐시가 살아있으면 CDN이 바로 응답하므로 오리진에는 요청이 가지 않는다.

### CDN 캐시 무효화 (Purge)

데이터가 변경되면 CDN에 캐시된 응답을 지워야 한다. `s-maxage`가 만료되기 전에 변경이 발생하면 사용자가 오래된 데이터를 보게 되기 때문이다.

#### CloudFront 캐시 무효화

```java
@Service
public class CdnInvalidationService {

    private final CloudFrontClient cloudFront;
    private final String distributionId;

    public void invalidate(List<String> paths) {
        cloudFront.createInvalidation(req -> req
                .distributionId(distributionId)
                .invalidationBatch(batch -> batch
                        .callerReference(UUID.randomUUID().toString())
                        .paths(p -> p
                                .quantity(paths.size())
                                .items(paths)
                        )
                )
        );
    }

    // 상품 수정 시 캐시 무효화
    public void onProductUpdated(Long productId) {
        invalidate(List.of(
                "/api/v1/products/" + productId,
                "/api/v1/products"  // 목록 캐시도 무효화
        ));
    }
}
```

CloudFront 무효화는 즉시 되지 않는다. 전 세계 엣지 로케이션에 전파되는 데 보통 수 초에서 수 분이 걸린다. 월 1,000건까지는 무료인데, 그 이후는 건당 과금된다. 무효화를 너무 자주 하면 비용이 나온다.

#### Surrogate-Key 기반 무효화

Fastly 같은 CDN은 `Surrogate-Key` 헤더로 태그 기반 무효화를 지원한다. 경로 패턴 대신 태그로 무효화할 수 있어서 더 정밀하다.

```java
@GetMapping("/products/{id}")
public ResponseEntity<Product> getProduct(@PathVariable Long id) {
    Product product = productService.findById(id);

    return ResponseEntity.ok()
            .header("Surrogate-Key",
                    "product-" + id + " category-" + product.getCategoryId())
            .header("Surrogate-Control", "max-age=3600")
            .cacheControl(CacheControl.noCache())
            .body(product);
}
```

```
# 특정 상품 캐시 무효화
curl -X POST https://api.fastly.com/service/{id}/purge/product-123 \
  -H "Fastly-Key: {api-key}"

# 카테고리 전체 무효화 (해당 카테고리의 모든 상품)
curl -X POST https://api.fastly.com/service/{id}/purge/category-5 \
  -H "Fastly-Key: {api-key}"
```

`Surrogate-Control`은 CDN 전용 캐시 헤더로, CDN이 이 헤더를 소비하고 클라이언트에게 전달하지 않는다. `Cache-Control`과 분리해서 CDN과 브라우저의 캐시 정책을 완전히 독립적으로 관리할 수 있다.

### Vary 헤더

같은 URL이라도 요청 헤더에 따라 다른 응답을 보내는 경우가 있다. `Accept-Language`에 따라 한국어/영어 응답이 다르거나, `Authorization`에 따라 다른 데이터를 보내는 경우다. `Vary` 헤더로 이를 CDN에 알려줘야 한다.

```
# 언어별로 다른 캐시
Cache-Control: public, s-maxage=300
Vary: Accept-Language

# 인코딩별로 다른 캐시 (gzip vs br)
Vary: Accept-Encoding
```

`Vary: Authorization`은 쓰면 안 된다. 사용자마다 다른 캐시를 저장해야 하니 사실상 CDN 캐시가 의미 없어진다. 사용자별 데이터는 `Cache-Control: private`로 브라우저 캐시만 활용한다.

## API 응답 캐싱 계층 구성

### 다층 캐시 아키텍처

실무에서는 여러 캐시 레이어를 조합해서 쓴다.

```
클라이언트 → CDN → API Gateway 캐시 → 애플리케이션 로컬 캐시 → Redis → DB
```

각 계층의 역할이 다르다.

| 계층 | TTL | 용도 |
|------|-----|------|
| 브라우저 | 10초 ~ 5분 | 같은 사용자의 반복 요청 |
| CDN | 1분 ~ 1시간 | 지역별 캐시, 오리진 보호 |
| API Gateway | 10초 ~ 5분 | 오리진 보호, rate limiting과 조합 |
| 로컬 캐시 (Caffeine 등) | 5초 ~ 1분 | JVM 내부, 네트워크 비용 없음 |
| Redis | 1분 ~ 1시간 | 인스턴스 간 공유, DB 부하 감소 |

### Spring Boot + Caffeine + Redis 2단 캐시

```java
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory redisFactory) {
        // L1: Caffeine (로컬)
        CaffeineCacheManager localCacheManager = new CaffeineCacheManager();
        localCacheManager.setCaffeine(Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterWrite(Duration.ofSeconds(10)));

        // L2: Redis
        RedisCacheManager redisCacheManager = RedisCacheManager.builder(redisFactory)
                .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig()
                        .entryTtl(Duration.ofMinutes(10))
                        .serializeValuesWith(
                                SerializationPair.fromSerializer(
                                        new GenericJackson2JsonRedisSerializer())))
                .build();

        // L1 → L2 순서로 조회
        return new CompositeCacheManager(localCacheManager, redisCacheManager);
    }
}
```

```java
@Service
public class ProductService {

    private final ProductRepository productRepository;
    private final CacheManager cacheManager;

    @Cacheable(value = "products", key = "#id")
    public Product findById(Long id) {
        return productRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("상품을 찾을 수 없음: " + id));
    }

    @CacheEvict(value = "products", key = "#id")
    public Product update(Long id, ProductUpdateRequest request) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("상품을 찾을 수 없음: " + id));
        product.update(request);
        return productRepository.save(product);
    }
}
```

`CompositeCacheManager`는 단순히 여러 CacheManager를 순서대로 조회한다. L1 miss → L2 조회 → L2 miss → DB 조회 흐름이 자동으로 동작한다. 다만 L1에 없고 L2에 있는 경우, L1에 자동으로 채우지 않는다. 이런 세밀한 제어가 필요하면 직접 구현해야 한다.

```java
@Service
public class ProductCacheService {

    private final Cache<Long, Product> localCache;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final ProductRepository productRepository;

    public ProductCacheService(StringRedisTemplate redis,
                                ObjectMapper objectMapper,
                                ProductRepository productRepository) {
        this.localCache = Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterWrite(Duration.ofSeconds(10))
                .build();
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.productRepository = productRepository;
    }

    public Product findById(Long id) {
        // L1 조회
        Product cached = localCache.getIfPresent(id);
        if (cached != null) return cached;

        // L2 조회
        String redisKey = "product:" + id;
        String json = redis.opsForValue().get(redisKey);
        if (json != null) {
            Product product = objectMapper.readValue(json, Product.class);
            localCache.put(id, product); // L1에 채움
            return product;
        }

        // DB 조회
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("상품을 찾을 수 없음: " + id));

        // L1, L2 모두 저장
        localCache.put(id, product);
        redis.opsForValue().set(redisKey,
                objectMapper.writeValueAsString(product),
                Duration.ofMinutes(10));

        return product;
    }

    public void evict(Long id) {
        localCache.invalidate(id);
        redis.delete("product:" + id);
    }
}
```

### 다중 인스턴스에서 로컬 캐시 동기화

서버가 여러 대인 경우, 한 인스턴스에서 데이터를 수정하면 다른 인스턴스의 로컬 캐시는 여전히 이전 데이터를 가지고 있다. Redis Pub/Sub으로 캐시 무효화 이벤트를 전파하는 방식이 일반적이다.

```java
@Component
public class CacheInvalidationPublisher {

    private final StringRedisTemplate redis;
    private static final String CHANNEL = "cache:invalidation";

    public void publishEviction(String cacheName, String key) {
        String message = cacheName + ":" + key;
        redis.convertAndSend(CHANNEL, message);
    }
}

@Component
public class CacheInvalidationSubscriber implements MessageListener {

    private final Cache<Long, Product> localCache;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String payload = new String(message.getBody());
        String[] parts = payload.split(":");
        String cacheName = parts[0];
        String key = parts[1];

        if ("products".equals(cacheName)) {
            localCache.invalidate(Long.parseLong(key));
        }
    }
}
```

이 방식은 결국 짧은 시간 동안 불일치가 발생한다. Redis Pub/Sub 메시지가 전파되기 전에 다른 인스턴스가 이전 데이터를 서빙할 수 있다. 보통 수 밀리초 수준이라 대부분의 서비스에서는 문제되지 않지만, 금융 데이터처럼 엄격한 일관성이 필요한 경우에는 로컬 캐시 자체를 쓰지 않는 게 맞다.

## 실무에서 겪는 문제들

### Cache Stampede (Thundering Herd)

캐시가 만료되는 순간 대량의 요청이 동시에 DB로 몰리는 현상이다. 인기 상품의 캐시가 만료되면 수십~수백 개의 요청이 동시에 같은 쿼리를 실행한다.

```java
public Product findById(Long id) {
    String key = "product:" + id;
    String json = redis.opsForValue().get(key);
    if (json != null) return deserialize(json);

    // 여기에 100개의 요청이 동시에 도달
    // → DB에 같은 쿼리 100번 실행
    Product product = productRepository.findById(id).orElseThrow();
    redis.opsForValue().set(key, serialize(product), Duration.ofMinutes(10));
    return product;
}
```

해결 방법은 분산 락을 걸어 하나의 요청만 DB에 접근하게 하는 것이다.

```java
public Product findById(Long id) {
    String key = "product:" + id;
    String json = redis.opsForValue().get(key);
    if (json != null) return deserialize(json);

    String lockKey = "lock:" + key;
    Boolean acquired = redis.opsForValue()
            .setIfAbsent(lockKey, "1", Duration.ofSeconds(5));

    if (Boolean.TRUE.equals(acquired)) {
        try {
            // 다시 한번 확인 (락 대기 중 다른 스레드가 캐시를 채웠을 수 있다)
            json = redis.opsForValue().get(key);
            if (json != null) return deserialize(json);

            Product product = productRepository.findById(id).orElseThrow();
            redis.opsForValue().set(key, serialize(product),
                    Duration.ofMinutes(10));
            return product;
        } finally {
            redis.delete(lockKey);
        }
    } else {
        // 락 획득 실패: 잠깐 대기 후 재시도
        Thread.sleep(50);
        return findById(id);
    }
}
```

다른 방법은 TTL을 랜덤하게 분산시키는 것이다. 모든 캐시가 같은 시각에 만료되면 stampede가 발생하므로, 기본 TTL에 랜덤 값을 더한다.

```java
Duration ttl = Duration.ofMinutes(10)
        .plusSeconds(ThreadLocalRandom.current().nextInt(0, 60));
redis.opsForValue().set(key, serialize(product), ttl);
```

### 목록 API의 캐시 키 설계

목록 API는 페이지네이션, 필터, 정렬 파라미터 조합이 다양해서 캐시 키 설계가 까다롭다.

```java
public String buildCacheKey(ProductSearchRequest request) {
    // 파라미터 정렬 후 해시 → 같은 조건이면 같은 키
    Map<String, String> sorted = new TreeMap<>();
    sorted.put("category", String.valueOf(request.getCategoryId()));
    sorted.put("page", String.valueOf(request.getPage()));
    sorted.put("size", String.valueOf(request.getSize()));
    sorted.put("sort", request.getSort());

    String params = sorted.entrySet().stream()
            .map(e -> e.getKey() + "=" + e.getValue())
            .collect(Collectors.joining("&"));

    return "products:list:" + DigestUtils.md5Hex(params);
}
```

파라미터 조합이 너무 많으면 캐시 적중률이 떨어진다. 이 경우 목록 전체를 캐시하기보다는, 각 상품의 개별 캐시를 활용하는 편이 낫다. 목록 API에서는 ID 목록만 캐시하고, 각 상품 데이터는 개별 캐시에서 가져오는 방식이다.

### 캐시 예열 (Warming)

서버를 새로 배포하면 캐시가 비어있으니 배포 직후에 DB 부하가 치솟을 수 있다. 배포 시 자주 요청되는 데이터를 미리 캐시에 채워두는 예열이 필요하다.

```java
@Component
public class CacheWarmer implements ApplicationRunner {

    private final ProductService productService;
    private final CategoryService categoryService;

    @Override
    public void run(ApplicationArguments args) {
        // 인기 상품 Top 100 캐시 예열
        List<Long> popularIds = productService.getPopularProductIds(100);
        popularIds.forEach(productService::findById);

        // 카테고리 목록은 거의 안 바뀌므로 전체 예열
        categoryService.findAll();
    }
}
```

Redis를 공유 캐시로 쓰고 있으면 배포 시 로컬 캐시만 비어있는 거라 예열 부담이 줄어든다. Redis 자체를 재시작하는 경우에만 본격적인 예열이 필요하다.

### Write-Through vs Write-Behind

캐시 갱신 시점에 대한 두 가지 접근이 있다.

**Write-Through**: 데이터 수정 시 DB와 캐시를 동시에 갱신한다. 일관성은 보장되지만 쓰기 지연이 생긴다.

```java
public Product update(Long id, ProductUpdateRequest request) {
    Product product = productRepository.findById(id).orElseThrow();
    product.update(request);
    productRepository.save(product);

    // DB 저장 직후 캐시도 갱신
    String key = "product:" + id;
    redis.opsForValue().set(key, serialize(product), Duration.ofMinutes(10));

    return product;
}
```

**Write-Behind (Write-Back)**: 캐시만 먼저 갱신하고, DB 반영은 비동기로 처리한다. 쓰기가 빠르지만 캐시가 죽으면 데이터를 잃는다. 조회수, 좋아요 수 같은 유실돼도 치명적이지 않은 데이터에 적합하다.

```java
@Scheduled(fixedDelay = 5000)
public void flushViewCounts() {
    Set<String> keys = redis.keys("view_count:product:*");
    if (keys == null || keys.isEmpty()) return;

    for (String key : keys) {
        String countStr = redis.opsForValue().getAndDelete(key);
        if (countStr == null) continue;

        Long productId = extractProductId(key);
        int count = Integer.parseInt(countStr);

        productRepository.incrementViewCount(productId, count);
    }
}
```

대부분의 API에서는 Write-Through가 무난하다. 수정보다 조회가 압도적으로 많으니 쓰기 지연은 감수할 만하다. Cache-Aside 패턴(수정 시 캐시를 삭제하고, 다음 조회 때 캐시를 채우는 방식)도 많이 쓰는데, 수정 직후 조회가 바로 들어오면 캐시 miss가 한 번 발생한다는 차이가 있다.
