---
title: Spring Cache 어노테이션 동작 원리
tags: [spring, java, cache, backend]
updated: 2026-09-15
---

## @Cacheable, @CacheEvict, @CachePut 동작 원리

Spring Cache 추상화는 AOP 기반이다. `@Cacheable`이 붙은 메서드 호출 전에 캐시를 먼저 조회하고, 값이 있으면 메서드 자체를 실행하지 않는다. `@CacheEvict`는 메서드 실행 후(기본값) 지정한 키를 삭제하고, `@CachePut`은 항상 메서드를 실행한 뒤 반환값을 캐시에 넣는다.

```java
@Cacheable(value = "user", key = "#userId")
public User getUser(Long userId) {
    return userRepository.findById(userId).orElseThrow();
}

@CacheEvict(value = "user", key = "#user.id")
public void updateUser(User user) {
    userRepository.save(user);
}

@CachePut(value = "user", key = "#result.id")
public User createUser(UserCreateRequest request) {
    return userRepository.save(request.toEntity());
}
```

`@Cacheable`과 `@CachePut`의 차이를 헷갈리는 경우가 많다. `@Cacheable`은 캐시 히트 시 메서드를 건너뛰고, `@CachePut`은 항상 실행한다. 생성 직후 캐시를 워밍하려면 `@CachePut`이 맞다. `@Cacheable`을 쓰면 첫 조회 전까지 캐시에 아무것도 없다.

---

## Self-invocation 함정

Spring Cache는 프록시 기반이라 같은 클래스 내부에서 호출하면 AOP가 동작하지 않는다.

```java
@Service
public class OrderService {

    public void processOrder(Long orderId) {
        // 이 호출은 캐시가 동작하지 않는다
        Order order = getOrder(orderId);
        // ...
    }

    @Cacheable(value = "order", key = "#orderId")
    public Order getOrder(Long orderId) {
        return orderRepository.findById(orderId).orElseThrow();
    }
}
```

`processOrder`에서 `getOrder`를 직접 호출하면 `this.getOrder()`가 되고, 프록시를 거치지 않는다. 캐시 어노테이션이 붙어 있어도 실제로는 DB를 매번 조회한다. 로그를 보면 캐시 히트가 전혀 없는데 어노테이션은 분명히 붙어 있어서 한참 헤맨 경험이 있다.

해결 방법은 두 가지다.

첫 번째는 `@Lazy`로 자기 자신을 주입받는 방식이다.

```java
@Service
public class OrderService {

    @Lazy
    @Autowired
    private OrderService self;

    public void processOrder(Long orderId) {
        Order order = self.getOrder(orderId);
        // ...
    }

    @Cacheable(value = "order", key = "#orderId")
    public Order getOrder(Long orderId) {
        return orderRepository.findById(orderId).orElseThrow();
    }
}
```

두 번째는 캐시 대상 메서드를 별도 빈으로 분리하는 방식이다. 구조가 조금 복잡해지지만 순환 의존성이 없고 테스트하기도 쉽다. 규모가 있는 프로젝트라면 분리 쪽이 낫다.

---

## 키 생성 규칙과 충돌 케이스

기본 키 생성기(`SimpleKeyGenerator`)는 파라미터 조합으로 키를 만든다.

- 파라미터 없음 → `SimpleKey.EMPTY`
- 파라미터 1개 → 그 값 자체
- 파라미터 2개 이상 → `SimpleKey(param1, param2, ...)`

문제는 파라미터가 1개일 때다. `getUser(1L)`과 `getOrder(1L)`이 같은 캐시 이름을 쓴다면 키가 둘 다 `1L`이 되어 충돌한다. 캐시 이름을 다르게 쓰면 괜찮지만, 같은 이름 아래 다른 타입의 값이 들어가면 역직렬화 시 `ClassCastException`이 발생한다.

```java
// 이 두 메서드가 같은 캐시를 쓰면 위험하다
@Cacheable(value = "entity", key = "#id")
public User getUser(Long id) { ... }

@Cacheable(value = "entity", key = "#id")
public Order getOrder(Long id) { ... }
```

SpEL로 키를 명시적으로 분리하는 게 안전하다.

```java
@Cacheable(value = "entity", key = "'user:' + #id")
public User getUser(Long id) { ... }

@Cacheable(value = "entity", key = "'order:' + #id")
public Order getOrder(Long id) { ... }
```

`condition`과 `unless` 조건도 자주 놓친다. `condition`은 캐시 조회 전에 평가하고, `unless`는 캐시 저장 전에 평가한다. `null` 반환값을 캐시하지 않으려면 `unless = "#result == null"`을 쓴다. `condition`으로 걸면 조회도 안 해서 효과가 없다.

---

## Caffeine L1 + Redis L2 구성

단일 Redis 캐시는 네트워크 레이턴시가 항상 따라온다. 조회가 많고 변경이 적은 데이터라면 Caffeine을 로컬 1차 캐시로 두고 Redis를 2차로 두는 구성이 유효하다.

Spring Cache 기본 추상화로는 L1+L2를 직접 지원하지 않는다. `CompositeCacheManager`를 쓰거나, 커스텀 `CacheManager`를 구현해야 한다.

```java
@Configuration
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory redisConnectionFactory) {
        // L1: Caffeine
        CaffeineCacheManager caffeineCacheManager = new CaffeineCacheManager();
        caffeineCacheManager.setCaffeine(
            Caffeine.newBuilder()
                .maximumSize(1000)
                .expireAfterWrite(Duration.ofSeconds(30))
        );

        // L2: Redis
        RedisCacheManager redisCacheManager = RedisCacheManager.builder(redisConnectionFactory)
            .cacheDefaults(
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofMinutes(10))
            )
            .build();

        // L1 miss 시 L2로 넘어간다
        CompositeCacheManager compositeCacheManager = new CompositeCacheManager(
            caffeineCacheManager, redisCacheManager
        );
        compositeCacheManager.setFallbackToNoOpCache(false);
        return compositeCacheManager;
    }
}
```

`CompositeCacheManager`는 내부적으로 등록된 순서대로 캐시 매니저를 순회하면서 해당 캐시 이름을 처리할 수 있는 매니저를 찾는다. Caffeine이 먼저라면 Caffeine에서 히트하고, 미스면 Redis로 넘어간다.

단, 이 방식은 L1 미스 후 L2에서 찾은 값을 L1에 자동으로 채워주지 않는다. L1에서 미스 → L2에서 히트 → 다음 조회도 L1 미스 → L2 조회가 반복된다. L2 히트 시 L1을 채우는 로직은 직접 구현해야 한다. 커스텀 `Cache` 구현체를 만들어서 `get()` 메서드에서 L1 미스 시 L2를 조회하고 L1에 put하는 방식이 일반적이다.

또한 멀티 인스턴스 환경에서 L1 캐시는 인스턴스마다 독립적이다. 한 인스턴스에서 데이터를 변경하면 다른 인스턴스의 L1은 stale 상태가 된다. 이를 해소하려면 Redis Pub/Sub로 캐시 무효화 이벤트를 브로드캐스트해야 한다.

---

## TTL별 캐시 매니저 분리

모든 캐시에 같은 TTL을 적용하면 데이터 특성을 반영하지 못한다. 코드성 데이터는 몇 시간, 사용자 정보는 몇 분, 실시간 집계는 몇 초가 적절할 수 있다.

`RedisCacheManager`는 캐시 이름별로 다른 설정을 줄 수 있다.

```java
@Bean
public CacheManager redisCacheManager(RedisConnectionFactory factory) {
    RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofMinutes(10))
        .serializeValuesWith(
            RedisSerializationContext.SerializationPair.fromSerializer(
                new GenericJackson2JsonRedisSerializer()
            )
        );

    Map<String, RedisCacheConfiguration> cacheConfigs = new HashMap<>();
    cacheConfigs.put("code", defaultConfig.entryTtl(Duration.ofHours(6)));
    cacheConfigs.put("user", defaultConfig.entryTtl(Duration.ofMinutes(5)));
    cacheConfigs.put("realtime", defaultConfig.entryTtl(Duration.ofSeconds(10)));

    return RedisCacheManager.builder(factory)
        .cacheDefaults(defaultConfig)
        .withInitialCacheConfigurations(cacheConfigs)
        .build();
}
```

`@Cacheable(value = "code")`를 쓰면 6시간 TTL 설정이 적용된다. 어노테이션에서 TTL을 바꾸는 방법은 없고 반드시 `CacheManager` 설정에서 관리한다.

여러 캐시 매니저가 필요한 경우 `@Primary`나 `@Qualifier`로 구분한다.

```java
@Cacheable(value = "user", cacheManager = "shortLiveCacheManager")
public User getUser(Long userId) { ... }
```

`cacheManager` 속성이 없으면 `@Primary`로 등록된 매니저를 쓴다. 두 개 이상의 `CacheManager` 빈을 만들면 반드시 하나에 `@Primary`를 붙여야 한다. 안 붙이면 Spring이 어느 걸 써야 할지 모르고 기동 시 에러가 난다.

---

## 트랜잭션 롤백 시 캐시 동기화

Spring Cache의 기본 동작은 트랜잭션을 인식하지 않는다. `@CacheEvict`가 붙은 메서드가 트랜잭션 중에 실행되면, 그 즉시 캐시를 삭제한다. 이후 트랜잭션이 롤백되어도 삭제된 캐시는 복구되지 않는다.

```java
@Transactional
@CacheEvict(value = "user", key = "#userId")
public void updateUserStatus(Long userId, UserStatus status) {
    User user = userRepository.findById(userId).orElseThrow();
    user.changeStatus(status);
    // 외부 API 호출에서 예외가 나면 트랜잭션은 롤백된다
    // 그러나 캐시는 이미 삭제된 상태다
    externalApiClient.notifyStatusChange(userId, status);
}
```

DB는 롤백됐는데 캐시는 비어있어서 다음 조회 시 DB에서 읽어오면 롤백 전 값을 반환한다. 일시적이지만 데이터 정합성 문제가 생긴다.

`@CacheEvict(afterInvocation = true)`는 기본값이라 메서드 정상 완료 후 삭제한다. 예외가 나면 삭제하지 않아서 이 문제를 어느 정도 피할 수 있다. 하지만 트랜잭션 커밋 전에 삭제하는 타이밍 문제는 여전히 남는다.

근본적으로 해결하려면 트랜잭션 커밋 후에 캐시 작업을 수행해야 한다.

```java
@Service
@RequiredArgsConstructor
public class UserCacheService {

    private final Cache userCache;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void evictAfterCommit(UserStatusChangedEvent event) {
        userCache.evict(event.getUserId());
    }
}
```

`@TransactionalEventListener`를 `AFTER_COMMIT` 페이즈로 쓰면 트랜잭션이 실제로 커밋된 후에 캐시를 삭제한다. 롤백 시에는 이벤트가 발행되지 않는다.

`@CachePut`도 같은 문제가 있다. 트랜잭션 중간에 캐시에 값을 넣었다가 롤백되면 캐시에는 DB에 없는 값이 들어간다. TTL이 짧으면 잠깐이라 넘어갈 수 있지만, TTL이 길면 실제로 문제가 된다. 결국 쓰기 경로에서 캐시를 직접 관리할 때는 트랜잭션 경계와 캐시 작업 타이밍을 명시적으로 맞춰야 한다.
