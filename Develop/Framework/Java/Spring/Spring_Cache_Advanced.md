---
title: Spring Cache 심화
tags: [spring, cache, redis, java, microservices]
updated: 2026-09-18
---

# Spring Cache 심화

## @CacheConfig

`@CacheConfig`는 클래스 레벨에서 캐시 설정을 공유하는 어노테이션이다. 메서드마다 `value`, `cacheManager`, `keyGenerator`를 반복 지정해야 할 때 클래스에 한 번 선언하면 된다.

```java
@Service
@CacheConfig(cacheNames = "products", cacheManager = "redisCacheManager")
public class ProductService {

    @Cacheable(key = "#id")
    public Product getProduct(Long id) { ... }

    @CachePut(key = "#product.id")
    public Product updateProduct(Product product) { ... }

    @CacheEvict(key = "#id")
    public void deleteProduct(Long id) { ... }
}
```

`@CacheConfig`에 선언한 값은 메서드 어노테이션의 기본값이 된다. 메서드에서 같은 속성을 명시하면 메서드 어노테이션이 우선한다. `cacheNames`를 `"products"`로 지정했어도 특정 메서드에서 `value = "productDetail"`을 쓰면 그 메서드만 다른 캐시를 쓴다.

`cacheManager`를 클래스 레벨에서 지정하는 경우는 주로 캐시 저장소가 여럿일 때다. Caffeine과 Redis `CacheManager`가 둘 다 있을 때, 특정 서비스는 항상 Redis를 쓰겠다고 클래스 레벨에서 명시한다. `@Primary`로 기본 `CacheManager`를 설정하고 나머지를 빈 이름으로 참조하는 방식이다.

주의할 점은 `@CacheConfig`가 인터페이스에는 붙지 않는다는 것이다. 인터페이스에 붙이면 Spring이 메타데이터를 읽지 못해 설정이 무시된다. 반드시 구현 클래스에 붙인다.

## 커스텀 KeyGenerator

Spring의 기본 `KeyGenerator`는 `SimpleKeyGenerator`다. 파라미터가 하나면 그 값 자체를, 여럿이면 `SimpleKey`로 감싸서 키를 만든다. 타입 정보는 포함하지 않는다.

같은 캐시 이름에 파라미터 값이 같은 메서드가 두 개 이상 있으면 키가 충돌한다.

```java
// 두 메서드가 동일한 키를 만든다
@Cacheable("items")
public Product getProduct(Long id) { ... }  // items::100

@Cacheable("items")
public Order getOrder(Long id) { ... }  // items::100 — 충돌
```

`getProduct(100L)`이 먼저 호출되면 `items::100`에 `Product`가 저장된다. 이후 `getOrder(100L)`을 호출하면 캐시 히트로 `Product`를 꺼내고, 이를 `Order`로 역직렬화하려다 실패한다. Redis를 쓰면 `SerializationException`, Caffeine을 쓰면 `ClassCastException`이 발생한다.

타입 정보를 키에 포함하는 `KeyGenerator`를 직접 구현하면 이 충돌을 방지할 수 있다.

```java
@Component("typeAwareKeyGenerator")
public class TypeAwareKeyGenerator implements KeyGenerator {

    @Override
    public Object generate(Object target, Method method, Object... params) {
        StringBuilder key = new StringBuilder();
        key.append(method.getReturnType().getSimpleName()).append(":");

        for (Object param : params) {
            if (param == null) {
                key.append("null");
            } else {
                key.append(param.getClass().getSimpleName())
                   .append("=")
                   .append(param);
            }
            key.append(",");
        }

        return key.toString();
    }
}
```

```java
@Cacheable(value = "items", keyGenerator = "typeAwareKeyGenerator")
public Product getProduct(Long id) { ... }  // items::Product:Long=100,

@Cacheable(value = "items", keyGenerator = "typeAwareKeyGenerator")
public Order getOrder(Long id) { ... }  // items::Order:Long=100,
```

반환 타입을 키에 넣으면 같은 파라미터 값이어도 키가 달라진다.

`@Cacheable(key = "...")`와 `keyGenerator`는 동시에 쓸 수 없다. 둘 다 지정하면 `IllegalStateException`이 발생한다. SpEL 키로 충분히 표현 가능한 경우 `KeyGenerator`보다 `key` 속성이 낫다. `KeyGenerator`는 SpEL로 표현하기 어려운 복잡한 로직이 필요할 때만 쓴다.

`KeyGenerator`가 반환하는 객체는 `toString()`이 의미 있는 값을 돌려줘야 한다. Redis 키로 변환할 때 `toString()`을 호출하는데, `toString()`을 재정의하지 않은 커스텀 클래스를 반환하면 `ClassName@hashcode` 형식이 나와 키가 실행마다 달라진다. `String`을 반환하거나 `toString()`을 구현한 값 객체를 반환한다.

## CacheResolver

`CacheResolver`는 `@Cacheable`이 실제로 사용할 `Cache` 인스턴스를 런타임에 결정한다. `cacheManager`나 `value` 속성이 컴파일 타임에 고정된 것과 달리, 실행 중 컨텍스트를 보고 다른 캐시 저장소를 선택할 수 있다.

멀티테넌트 환경에서 테넌트별 캐시를 분리하는 경우가 대표적인 사용처다.

```java
@Component("tenantCacheResolver")
public class TenantCacheResolver extends AbstractCacheResolver {

    public TenantCacheResolver(CacheManager cacheManager) {
        super(cacheManager);
    }

    @Override
    protected Collection<String> getCacheNames(CacheOperationInvocationContext<?> context) {
        String tenantId = TenantContext.getCurrentTenantId();
        String cacheName = context.getOperation().getCacheNames().iterator().next();
        return Collections.singleton(tenantId + ":" + cacheName);
    }
}
```

```java
@Cacheable(cacheResolver = "tenantCacheResolver", cacheNames = "products")
public Product getProduct(Long id) {
    return productRepository.findById(id).orElseThrow();
}
```

같은 `id`여도 테넌트가 다르면 전혀 다른 캐시 항목을 참조하게 된다.

`CacheResolver`가 반환하는 캐시 이름에 해당하는 `Cache` 인스턴스가 `CacheManager`에 없으면 예외가 발생한다. `CaffeineCacheManager`는 동적으로 캐시를 생성하지만, `SimpleCacheManager`는 미리 등록된 캐시만 반환한다. 동적 캐시 이름을 쓰는 경우 `CacheManager` 구현체가 동적 생성을 지원하는지 확인한다.

`CacheOperationInvocationContext`에서 메서드 파라미터(`context.getArgs()`)와 대상 객체(`context.getTarget()`)에 접근할 수 있어서 비즈니스 로직 기반으로 캐시를 선택하는 것도 가능하다. `cacheResolver`와 `cacheManager`, `cacheNames`는 동시에 쓸 수 없다. `cacheResolver`를 지정하면 나머지 두 속성이 무시된다.

## WebFlux에서 @Cacheable이 동작하지 않는 이유

`@Cacheable`을 `Mono`나 `Flux`를 반환하는 WebFlux 메서드에 붙이면 동작하지 않는다. 정확히는 캐시에 실제 값 대신 `Mono` 인스턴스 자체가 저장된다.

```java
// 캐시가 동작하지 않는다
@Cacheable("products")
public Mono<Product> getProduct(Long id) {
    return productRepository.findById(id);
}
```

Spring AOP는 메서드 반환값을 캐시에 넣는다. 이 메서드는 `Mono<Product>`를 반환하고, AOP 인터셉터는 그 `Mono` 객체를 캐시에 저장한다. 두 번째 호출에서 캐시 히트가 발생하면 저장된 `Mono`를 꺼내 반환하는데, 리액티브 스트림에서 `Mono`는 구독할 때마다 새 시퀀스를 만든다. 첫 번째 구독에서 완료된 cold `Mono`를 재구독하면 빈 시퀀스가 반환되거나 예외가 발생한다.

`productRepository.findById(id)`는 cold source다. 구독마다 DB 쿼리를 새로 실행한다. 캐시에 `Mono`가 저장됐어도 매 요청마다 새 쿼리가 실행되거나, 완료 상태의 `Mono`를 재구독해서 빈 결과를 받게 된다.

이 문제는 Spring의 캐시 추상화가 동기 메서드 반환값을 다루도록 설계됐기 때문에 발생한다. AOP 인터셉터가 리액티브 타입을 인식하지 못한다.

## reactor-addons의 CacheMono / CacheFlux

`reactor-addons` 라이브러리의 `CacheMono`와 `CacheFlux`는 리액티브 스트림 체인 안에서 캐시를 다루는 방법을 제공한다. `@Cacheable` 어노테이션 대신 명시적인 API를 쓴다.

```xml
<dependency>
    <groupId>io.projectreactor.addons</groupId>
    <artifactId>reactor-extra</artifactId>
    <version>3.5.1</version>
</dependency>
```

Caffeine을 캐시 저장소로 쓰는 경우다.

```java
@Service
public class ProductService {

    private final Cache<Long, Product> localCache = Caffeine.newBuilder()
        .maximumSize(1000)
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .build();

    public Mono<Product> getProduct(Long id) {
        return CacheMono.lookup(key -> {
            Product cached = localCache.getIfPresent(key);
            return cached != null
                ? Mono.just(Signal.next(cached))
                : Mono.empty();
        }, id)
        .onCacheMissResume(() -> productRepository.findById(id))
        .andWriteWith((key, signal) -> Mono.fromRunnable(() -> {
            if (signal.hasValue()) {
                localCache.put(key, signal.get());
            }
        }));
    }
}
```

`CacheMono.lookup`은 캐시에서 값을 찾는 함수를 받는다. 캐시 히트면 `Signal.next(value)`를 `Mono`로 감싸서 반환하고, 미스면 `Mono.empty()`를 반환한다. `onCacheMissResume`은 캐시 미스 시 실행할 실제 소스를 제공한다. `andWriteWith`는 값을 캐시에 저장하는 로직이다.

Redis를 캐시 저장소로 쓸 때는 `ReactiveRedisTemplate`을 사용한다.

```java
@Service
public class ProductService {

    private final ReactiveRedisTemplate<String, Product> redisTemplate;

    public Mono<Product> getProduct(Long id) {
        String cacheKey = "products:" + id;

        return CacheMono.lookup(k -> redisTemplate.opsForValue().get(k)
                    .map(Signal::next), cacheKey)
            .onCacheMissResume(() -> productRepository.findById(id))
            .andWriteWith((k, signal) -> {
                if (signal.hasValue()) {
                    return redisTemplate.opsForValue()
                        .set(k, signal.get(), Duration.ofMinutes(10))
                        .then();
                }
                return Mono.empty();
            });
    }
}
```

Spring Boot 3.x에서 `spring-boot-starter-data-redis`를 쓰면 `ReactiveRedisTemplate` 자동 구성이 포함된다. 별도 빈 정의 없이 주입해서 쓸 수 있다.

`CacheMono` 방식은 `@Cacheable`보다 코드가 길지만, 캐시 읽기·쓰기 로직이 명시적으로 드러난다. 오류가 발생했을 때 어디서 문제가 생겼는지 찾기 쉽고, 캐시 미스 처리나 null 처리를 세밀하게 제어할 수 있다. `CacheFlux`는 `Flux<T>`를 반환하는 경우에 사용한다. 사용 방식은 `CacheMono`와 동일하다.

## 마이크로서비스 환경에서 키 네임스페이스 충돌

Redis를 여러 서비스가 공유할 때 키 충돌이 발생한다. `products::100`이라는 키를 상품 서비스와 추천 서비스가 각자 다른 구조의 데이터로 저장하면, 나중에 쓴 서비스의 값이 앞서 쓴 서비스의 값을 덮어쓴다.

### 서비스 이름 접두사

`RedisCacheConfiguration`에서 키 접두사를 설정하면 모든 캐시 키에 자동으로 붙는다.

```java
@Bean
public CacheManager cacheManager(RedisConnectionFactory connectionFactory) {
    RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
        .computePrefixWith(cacheName -> "product-service:" + cacheName + ":");

    return RedisCacheManager.builder(connectionFactory)
        .cacheDefaults(config)
        .build();
}
```

기본 prefix는 `cacheName + "::"` 형식이다. `computePrefixWith`로 재정의하면 `product-service:products:100` 형식이 된다. 서비스 이름을 접두사로 넣으면 다른 서비스와 키가 겹치지 않는다.

접두사를 `application.yml`에서 읽어서 배포 환경마다 다르게 줄 수도 있다. 개발 환경에서 여러 사람이 같은 Redis를 공유할 때도 같은 방법으로 분리한다.

```yaml
app:
  cache:
    prefix: product-service
```

```java
@Value("${app.cache.prefix}")
private String cachePrefix;

@Bean
public CacheManager cacheManager(RedisConnectionFactory connectionFactory) {
    RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
        .computePrefixWith(cacheName -> cachePrefix + ":" + cacheName + ":");

    return RedisCacheManager.builder(connectionFactory)
        .cacheDefaults(config)
        .build();
}
```

### 키 구조 설계

Redis 키 구조는 한 번 정하면 바꾸기 어렵다. 이미 저장된 키 형식을 바꾸면 기존 캐시 데이터를 읽지 못하고 전부 캐시 미스가 발생한다. 처음부터 `{서비스}:{캐시이름}:{식별자}` 형식으로 정해두는 게 낫다.

같은 Redis를 쓰는 서비스들이 많아지면 키 관리가 복잡해진다. 공유 Redis에서 한 서비스의 `KEYS *` 또는 `SCAN` 패턴 삭제 연산이 다른 서비스에 영향을 준다. 트래픽이 높은 환경에서는 공유 Redis의 메모리나 커넥션이 병목이 되기 전에 서비스별 Redis 인스턴스 분리를 검토한다.
