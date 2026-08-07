---
title: Spring Cache
tags: [spring, cache, cacheable, cacheevict, cacheput, caffeine, redis, cache-manager, cache-key, cache-invalidation, conditional-caching]
updated: 2026-07-29
---

# Spring Cache

Spring Cache는 메서드 반환값을 캐싱하는 추상화 레이어다. 실제 저장소(Caffeine, Redis 등)와 분리되어 있어서 `CacheManager` 빈만 바꾸면 저장소를 교체할 수 있다.

주의할 점은 Spring AOP 프록시 기반으로 동작한다는 것이다. 같은 클래스 내에서 `@Cacheable` 붙은 메서드를 직접 호출하면 캐시가 동작하지 않는다(self-invocation 문제). 이 부분을 모르고 쓰다가 캐시가 전혀 동작 안 한다며 시간을 낭비하는 경우가 많다.

## CacheManager 설정

`@EnableCaching`을 붙여야 Spring이 캐시 어노테이션을 처리한다. `CacheManager` 빈이 없으면 애플리케이션 시작 자체가 실패하므로 반드시 설정해야 한다.

### Caffeine (로컬 캐시)

단일 인스턴스 환경이거나 코드 테이블·공지사항처럼 서버 간 정합성이 덜 중요한 데이터에 적합하다. Redis 왕복 없이 수십 ns 수준으로 빠르지만, 서버 2대 이상이면 각 인스턴스가 서로 다른 값을 캐싱하고 있을 수 있다.

```java
@Configuration
@EnableCaching
public class CaffeineCacheConfig {

    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager();
        manager.setCaffeine(
            Caffeine.newBuilder()
                .expireAfterWrite(5, TimeUnit.MINUTES)
                .maximumSize(1000)
                .recordStats()  // 캐시 히트율 모니터링 시 필요
        );
        return manager;
    }
}
```

`recordStats()`를 넣으면 Actuator를 통해 히트율을 확인할 수 있다. 운영에서 캐시가 실제로 동작하는지 확인할 때 필수다.

캐시 이름마다 TTL과 크기를 다르게 주고 싶으면 `CaffeineCacheManager` 대신 `SimpleCacheManager` + 개별 `CaffeineCache`를 직접 구성한다.

```java
@Bean
public CacheManager cacheManager() {
    SimpleCacheManager manager = new SimpleCacheManager();
    manager.setCaches(List.of(
        new CaffeineCache("products",
            Caffeine.newBuilder().expireAfterWrite(10, TimeUnit.MINUTES).maximumSize(500).build()),
        new CaffeineCache("users",
            Caffeine.newBuilder().expireAfterWrite(1, TimeUnit.MINUTES).maximumSize(200).build())
    ));
    return manager;
}
```

### Redis (분산 캐시)

서버 인스턴스가 여럿이거나, 재고·세션처럼 모든 서버가 동일한 값을 봐야 할 때 사용한다.

```java
@Configuration
@EnableCaching
public class RedisCacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .disableCachingNullValues()
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer()
                )
            );

        // 캐시 이름마다 TTL 다르게 설정
        Map<String, RedisCacheConfiguration> configs = Map.of(
            "products", defaultConfig.entryTtl(Duration.ofHours(1)),
            "users", defaultConfig.entryTtl(Duration.ofMinutes(5))
        );

        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(defaultConfig)
            .withInitialCacheConfigurations(configs)
            .build();
    }
}
```

`disableCachingNullValues()`를 빠뜨리면 DB에서 null이 반환됐을 때 null이 Redis에 저장되고, 이후 요청에서 캐시 히트로 null을 돌려준다. Cache-Aside 패턴에서 DB를 조회할 기회를 영원히 잃게 된다.

직렬화는 `GenericJackson2JsonRedisSerializer`를 쓰면 타입 정보를 JSON에 같이 저장해서 역직렬화가 안전하다. `StringRedisSerializer` + 수동 변환 방식을 쓰는 코드도 있는데, DTO 클래스 패키지를 바꾸면 기존 캐시를 역직렬화 못 해서 서비스 장애가 난다.

## @Cacheable

![키 기반 캐시 조회 구조 — 해시 테이블로 SpEL 키를 매핑하는 원리](../../../assets/images/auto/캐싱/8cb61583.webp)

![실제 서비스의 캐시 히트·미스 비율 모니터링 화면 (캐시 미스 발생 시 동시 스레드 문제와 직결)](../../../assets/images/auto/캐싱/d2789c7e.webp)


메서드가 처음 호출되면 결과를 캐시에 저장하고, 이후 같은 키로 호출되면 메서드를 실행하지 않고 캐시 값을 반환한다.

```java
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

`value`는 캐시 이름, `key`는 SpEL 표현식이다. `key`를 생략하면 메서드 파라미터 전체를 조합한 기본 키를 사용한다. 파라미터가 없는 메서드는 `SimpleKey.EMPTY`가 키가 된다.

### 동기화 문제와 sync=true

캐시 미스가 발생하면 여러 스레드가 동시에 메서드를 실행할 수 있다. TTL이 만료된 순간 트래픽이 몰리면 모두 DB를 찌른다. `sync=true`를 주면 한 스레드만 메서드를 실행하고 나머지는 대기한다.

```java
@Cacheable(value = "products", key = "#id", sync = true)
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

단, `sync = true`는 `unless`와 함께 쓸 수 없다. 같이 쓰면 시작 시점에 `IllegalStateException`이 발생한다. 또한 모든 `CacheManager` 구현체가 `sync`를 지원하지 않는다. Caffeine은 지원하지만, Redis 기반 `RedisCacheManager`는 지원하지 않는다. Redis 환경에서 동기화가 필요하면 분산 락(Redisson, Lettuce)을 별도로 구현해야 한다.

## @CacheEvict

캐시를 무효화한다. 데이터를 수정하거나 삭제할 때 함께 호출해서 캐시와 DB의 불일치를 방지한다.

```java
@CacheEvict(value = "products", key = "#product.id")
public void updateProduct(Product product) {
    productRepository.save(product);
}

// 캐시 전체 삭제
@CacheEvict(value = "products", allEntries = true)
public void clearProductCache() {
    // 실제 로직 없이 캐시만 지울 수도 있다
}
```

`allEntries = true`는 해당 캐시 이름의 모든 항목을 삭제한다. Redis를 쓰는 경우 `products::*` 패턴으로 키를 스캔해서 삭제하는데, 캐시에 항목이 수만 개 있으면 SCAN 연산이 Redis 응답에 영향을 준다. 운영에서 `allEntries`를 쓸 때는 캐시 항목 수를 확인해야 한다.

기본적으로 `@CacheEvict`는 메서드 실행 후 캐시를 삭제한다. `beforeInvocation = true`를 주면 메서드 실행 전에 삭제한다. 메서드에서 예외가 발생해도 캐시가 삭제돼야 한다면 `beforeInvocation = true`가 맞다.

## @CachePut

메서드를 항상 실행하고, 결과를 캐시에 저장하거나 갱신한다. `@Cacheable`은 캐시 히트 시 메서드를 건너뛰지만, `@CachePut`은 항상 실행한다는 차이가 있다.

```java
@CachePut(value = "products", key = "#product.id")
public Product updateProduct(Product product) {
    return productRepository.save(product);
}
```

수정 후 캐시를 무효화하는 대신 새 값으로 교체하고 싶을 때 사용한다. 단, 반환 타입과 `@Cacheable`의 반환 타입이 동일해야 한다. 타입이 다르면 역직렬화에서 실패한다.

`@CachePut`과 `@CacheEvict`를 동시에 쓰고 싶으면 `@Caching`으로 묶는다.

## @Caching

![@Caching 적용 시 개별 키별로 분리 관리되는 캐시 엔트리 구조](../../../assets/images/auto/캐싱/8cb61583.webp)

![캐시 채우기·무효화 복합 연산 후 히트율 변화를 확인하는 모니터링 예시](../../../assets/images/auto/캐싱/d2789c7e.webp)


여러 캐시 어노테이션을 한 메서드에 함께 적용한다.

```java
@Caching(
    put = {
        @CachePut(value = "products", key = "#result.id"),
        @CachePut(value = "productsByCategory", key = "#result.categoryId")
    },
    evict = {
        @CacheEvict(value = "productList", allEntries = true)
    }
)
public Product createProduct(CreateProductRequest request) {
    return productRepository.save(request.toEntity());
}
```

상품을 생성할 때 개별 상품 캐시는 채우고, 목록 캐시는 무효화하는 패턴이다.

## 조건부 캐싱

### condition

메서드 실행 전에 평가한다. `false`면 캐시를 아예 쓰지 않는다(읽지도, 쓰지도 않는다).

```java
// id가 0보다 클 때만 캐시 적용
@Cacheable(value = "products", key = "#id", condition = "#id > 0")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

### unless

메서드 실행 후 반환값을 보고 평가한다. `true`면 캐시에 저장하지 않는다. `#result`로 반환값에 접근한다.

```java
// 반환값이 null이거나 재고가 0인 상품은 캐시하지 않는다
@Cacheable(
    value = "products",
    key = "#id",
    unless = "#result == null || #result.stock == 0"
)
public Product getProduct(Long id) {
    return productRepository.findById(id).orElse(null);
}
```

`condition`과 `unless`를 헷갈리기 쉽다. 실행 전 / 실행 후 평가 시점이 핵심 차이다. `#result`는 `unless`에서만 쓸 수 있고, `condition`에서 `#result`를 참조하면 항상 null이다.

## 캐시 키 충돌 방지

기본 키 생성기는 메서드 파라미터를 조합한다. 서로 다른 메서드의 파라미터 타입과 값이 같으면 키가 충돌한다.

```java
// 두 메서드가 같은 캐시 이름에 같은 키를 생성할 수 있다
@Cacheable(value = "items", key = "#id")
public Product getProduct(Long id) { ... }

@Cacheable(value = "items", key = "#id")
public Order getOrder(Long id) { ... }
```

id가 100으로 같다면 두 메서드가 동일한 `items::100` 키를 공유한다. 캐시 이름을 분리하거나, 키에 타입 정보를 포함시킨다.

```java
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) { ... }

@Cacheable(value = "orders", key = "#id")
public Order getOrder(Long id) { ... }
```

캐시 이름을 분리하는 것이 가장 단순하고 명확하다. 같은 캐시 이름을 써야 한다면 SpEL로 프리픽스를 붙인다.

```java
@Cacheable(value = "items", key = "'product:' + #id")
public Product getProduct(Long id) { ... }

@Cacheable(value = "items", key = "'order:' + #id")
public Order getOrder(Long id) { ... }
```

파라미터가 객체인 경우에는 해당 클래스에 `equals`와 `hashCode`를 구현해야 올바른 키가 생성된다. 구현하지 않으면 인스턴스 참조 기반으로 키가 만들어져서 같은 값을 가진 객체도 다른 키가 된다.

## 운영 중 캐시 무효화 시 주의사항

### 클래스 변경과 직렬화 오류

Redis에 Java 객체를 직렬화해서 저장한 상태에서 DTO 클래스를 수정하면 역직렬화에 실패한다. `GenericJackson2JsonRedisSerializer`를 쓰면 JSON에 `@class` 필드로 클래스 경로가 박힌다. 패키지나 클래스명을 바꾸면 기존 캐시 데이터를 읽지 못한다.

배포 전에 해당 캐시를 전부 비우거나, 캐시 값을 읽을 때 `try-catch`로 역직렬화 실패를 잡아서 캐시를 삭제하고 DB에서 재조회하는 방어 코드가 필요하다. 운영에서 이 문제를 겪으면 서비스 전체가 `SerializationException`으로 다운된다.

### 배포 직후 캐시 플러시

모든 캐시를 한 번에 날리면 DB에 부하가 집중된다. 캐시 항목이 많을수록 플러시 직후 응답 시간이 급격히 느려진다. 단계적으로 날리거나, 배포 전 캐시를 미리 채워두는 워밍업 로직을 검토해야 한다.

### allEntries와 Redis 성능

`@CacheEvict(allEntries = true)`를 Redis 환경에서 쓰면 내부적으로 패턴 삭제를 수행한다. `spring-data-redis`의 기본 구현은 `KEYS` 명령어를 쓰는 경우가 있는데, `KEYS`는 Redis를 블로킹한다. 캐시 항목이 많은 상황에서 `KEYS`가 실행되면 Redis 전체가 멈추고 서비스 장애로 이어진다.

`RedisCacheWriter`를 직접 구성해서 `SCAN` 기반으로 동작하게 하거나, `allEntries` 대신 개별 키를 명시적으로 삭제하는 방식으로 바꾸는 게 안전하다.

### TTL 설정이 없는 캐시

CacheManager에서 TTL을 설정하지 않으면 Redis에 만료 없이 영구 저장된다. 데이터가 갱신돼도 캐시에는 옛날 값이 남는다. `@CacheEvict`로 수동 삭제하지 않는 한 오래된 데이터를 계속 반환하게 된다. TTL은 반드시 설정해야 한다.

