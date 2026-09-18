---
title: Spring Cache 어노테이션 동작 원리
tags: [spring, java, cache, backend, kotlin]
updated: 2026-09-18
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

## Caffeine L1 + Redis L2 구성과 backfill 문제

단일 Redis 캐시는 네트워크 레이턴시가 항상 따라온다. 조회가 많고 변경이 적은 데이터라면 Caffeine을 로컬 1차 캐시로 두고 Redis를 2차로 두는 구성이 유효하다.

Spring Cache 기본 추상화로는 L1+L2를 직접 지원하지 않는다. `CompositeCacheManager`를 쓰거나, 커스텀 `CacheManager`를 구현해야 한다.

```java
@Configuration
public class CacheConfig {

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory redisConnectionFactory) {
        CaffeineCacheManager caffeineCacheManager = new CaffeineCacheManager();
        caffeineCacheManager.setCaffeine(
            Caffeine.newBuilder()
                .maximumSize(1000)
                .expireAfterWrite(Duration.ofSeconds(30))
        );

        RedisCacheManager redisCacheManager = RedisCacheManager.builder(redisConnectionFactory)
            .cacheDefaults(
                RedisCacheConfiguration.defaultCacheConfig()
                    .entryTtl(Duration.ofMinutes(10))
            )
            .build();

        CompositeCacheManager compositeCacheManager = new CompositeCacheManager(
            caffeineCacheManager, redisCacheManager
        );
        compositeCacheManager.setFallbackToNoOpCache(false);
        return compositeCacheManager;
    }
}
```

`CompositeCacheManager`는 등록된 순서대로 캐시 매니저를 순회하면서 해당 캐시 이름을 처리할 수 있는 매니저를 찾는다. Caffeine이 먼저라면 Caffeine에서 히트하고, 미스면 Redis로 넘어간다.

**L2 히트 시 L1 역채움(backfill) 문제.** 이 방식의 결정적인 한계는 L1 미스 후 L2에서 찾은 값을 L1에 자동으로 채워주지 않는다는 것이다. L1 미스 → L2 히트 → 다음 조회도 L1 미스 → L2 조회가 반복된다. L2에서 읽는 비용이 결국 줄지 않는다.

역채움을 구현하려면 `Cache` 인터페이스를 직접 감싸는 래퍼를 만들어야 한다.

```java
public class TwoLevelCache implements Cache {

    private final Cache l1;   // Caffeine
    private final Cache l2;   // Redis
    private final String name;

    public TwoLevelCache(String name, Cache l1, Cache l2) {
        this.name = name;
        this.l1 = l1;
        this.l2 = l2;
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public Object getNativeCache() {
        return this;
    }

    @Override
    public ValueWrapper get(Object key) {
        // L1 먼저
        ValueWrapper l1Value = l1.get(key);
        if (l1Value != null) {
            return l1Value;
        }
        // L2 조회 후 L1에 역채움
        ValueWrapper l2Value = l2.get(key);
        if (l2Value != null) {
            l1.put(key, l2Value.get());
        }
        return l2Value;
    }

    @Override
    public <T> T get(Object key, Class<T> type) {
        T l1Value = l1.get(key, type);
        if (l1Value != null) {
            return l1Value;
        }
        T l2Value = l2.get(key, type);
        if (l2Value != null) {
            l1.put(key, l2Value);
        }
        return l2Value;
    }

    @Override
    public void put(Object key, Object value) {
        l1.put(key, value);
        l2.put(key, value);
    }

    @Override
    public void evict(Object key) {
        l1.evict(key);
        l2.evict(key);
    }

    @Override
    public void clear() {
        l1.clear();
        l2.clear();
    }
}
```

이 래퍼를 `CacheManager`에 묶어야 한다.

```java
@Bean
public CacheManager cacheManager(
    CaffeineCacheManager caffeineCacheManager,
    RedisCacheManager redisCacheManager
) {
    return new CacheManager() {
        @Override
        public Cache getCache(String name) {
            Cache l1 = caffeineCacheManager.getCache(name);
            Cache l2 = redisCacheManager.getCache(name);
            if (l1 == null || l2 == null) return null;
            return new TwoLevelCache(name, l1, l2);
        }

        @Override
        public Collection<String> getCacheNames() {
            return redisCacheManager.getCacheNames();
        }
    };
}
```

멀티 인스턴스 환경에서 L1 캐시는 인스턴스마다 독립적이다. 한 인스턴스에서 데이터를 변경하면 다른 인스턴스의 L1은 stale 상태가 된다. `TwoLevelCache.evict()`가 로컬 L1만 지우고 다른 인스턴스의 L1은 그대로 남는다. 이를 해소하려면 Redis Pub/Sub로 캐시 무효화 이벤트를 브로드캐스트해서 모든 인스턴스의 L1을 비워야 한다.

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

## 트랜잭션 롤백 + @CachePut 조합

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

`@CachePut`은 이 문제가 더 심각하다. 트랜잭션 중간에 캐시에 값을 넣었다가 롤백되면 캐시에는 DB에 없는 값이 들어간다. 재고 차감 같은 시나리오에서 실제로 문제가 됐다. DB는 차감 전 수량으로 롤백됐는데 캐시에는 차감 후 수량이 남아 있고, 그 TTL 동안 잘못된 재고 정보를 서빙하게 된다.

```java
@Transactional
@CachePut(value = "inventory", key = "#productId")
public Inventory decreaseStock(Long productId, int quantity) {
    Inventory inventory = inventoryRepository.findById(productId).orElseThrow();
    inventory.decrease(quantity);
    inventoryRepository.save(inventory);
    // 결제 처리 중 예외 발생 → DB 롤백
    // 캐시에는 차감된 재고가 그대로 남는다
    paymentService.charge(productId, quantity);
    return inventory;
}
```

`@CacheEvict(afterInvocation = true)`는 기본값이라 메서드 정상 완료 후 삭제한다. 예외가 나면 삭제하지 않아서 이 문제를 어느 정도 피할 수 있다. 하지만 트랜잭션 커밋 전에 삭제하는 타이밍 문제는 여전히 남는다.

트랜잭션 커밋 후에 캐시 작업을 수행하는 게 근본적인 해결책이다.

```java
@Service
@RequiredArgsConstructor
public class UserCacheService {

    private final Cache userCache;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void evictAfterCommit(UserStatusChangedEvent event) {
        userCache.evict(event.getUserId());
    }

    // @CachePut 대신 — 트랜잭션 커밋 후 최신 값을 직접 채운다
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void putAfterCommit(InventoryChangedEvent event) {
        // 커밋이 확정된 뒤에 DB에서 다시 읽어서 캐시에 넣는다
        // 이 조회는 트랜잭션 밖이라 커밋된 값을 본다
        Inventory confirmed = inventoryRepository.findById(event.getProductId()).orElseThrow();
        inventoryCache.put(event.getProductId(), confirmed);
    }
}
```

`@TransactionalEventListener`를 `AFTER_COMMIT` 페이즈로 쓰면 트랜잭션이 실제로 커밋된 후에 캐시를 조작한다. 롤백 시에는 이벤트가 발행되지 않는다. `@CachePut`을 `AFTER_COMMIT`에 쓸 때는 DB를 한 번 더 조회하는 비용이 있지만, 잘못된 값을 캐시에 넣는 것보다 낫다.

`@Transactional`과 `@Cacheable`을 같은 메서드에 붙일 때도 주의가 필요하다. 트랜잭션 내에서 캐시 히트가 나면 메서드를 건너뛰는데, 그러면 트랜잭션도 시작되지 않는다. 캐시 히트로 인해 격리 수준 보장을 받지 못하는 상황이 생긴다.

---

## @CacheEvict allEntries와 KEYS vs SCAN

`@CacheEvict(value = "user", allEntries = true)`는 해당 캐시의 모든 엔트리를 삭제한다. Redis 백엔드에서는 `user::*` 패턴으로 매칭되는 키를 전부 찾아서 삭제한다.

기본 `RedisCacheWriter`는 이 패턴 조회에 `KEYS` 명령을 사용한다. `KEYS`는 O(N) 단일 블로킹 명령이라 Redis 서버 전체를 멈추게 한다. 키가 수만 개라면 밀리초 단위지만, 수백만 개라면 수백 밀리초 동안 다른 요청을 전부 막는다. 프로덕션에서 `KEYS`를 쓰지 말라는 건 이 이유다.

Spring Boot의 기본 `RedisCacheManager`는 Spring Data Redis 2.6 이전까지 `KEYS`를 사용했다. 지금도 `BatchStrategy`를 명시하지 않으면 `KEYS`가 기본이다.

`SCAN`으로 바꾸려면 `RedisCacheWriter`를 커스터마이징해야 한다.

```java
@Bean
public CacheManager redisCacheManager(RedisConnectionFactory factory) {
    RedisCacheWriter cacheWriter = RedisCacheWriter.nonLockingRedisCacheWriter(
        factory,
        BatchStrategies.scan(100)  // 한 번에 100개씩 cursor 기반으로 스캔
    );

    RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofMinutes(10))
        .serializeValuesWith(
            RedisSerializationContext.SerializationPair.fromSerializer(
                new GenericJackson2JsonRedisSerializer()
            )
        );

    return RedisCacheManager.builder(cacheWriter)
        .cacheDefaults(defaultConfig)
        .build();
}
```

`BatchStrategies.scan(100)`은 `SCAN 0 MATCH user::* COUNT 100` 식으로 반복하며 키를 찾는다. `KEYS`처럼 한 번에 전부 찾지 않고 cursor를 이동하면서 배치로 처리한다. 블로킹 시간이 분산된다.

단, `SCAN`은 완전한 일관성을 보장하지 않는다. cursor 반복 중에 새 키가 추가되거나 삭제되면 그 키를 놓치거나 중복 처리할 수 있다. `allEntries` 삭제에서 몇 개가 남을 수 있다는 뜻이다. 캐시 레이어에서는 이 정도 허용 범위가 대부분 괜찮다.

`BatchStrategies`는 Spring Data Redis 2.6(Spring Boot 2.6)에서 추가됐다. 그 이전 버전이라면 `RedisCacheWriter`를 직접 구현해야 한다.

`allEntries = true`를 쓰는 상황 자체를 피할 수 있다면 더 낫다. 어떤 키가 영향을 받는지 알 수 있다면 개별 키 삭제로 처리한다. 패턴 기반 전체 삭제는 캐시 구조를 재설계하기 어려울 때 쓰는 차선책이다.

---

## Kotlin suspend 함수에서 @Cacheable 비동작

Kotlin coroutine의 `suspend` 함수에 `@Cacheable`을 붙이면 동작하지 않는다. 정확히는 예외도 없이 매번 원본 함수를 호출한다.

```kotlin
@Service
class UserService(private val userRepository: UserRepository) {

    // 이 어노테이션은 아무 효과가 없다
    @Cacheable(value = ["user"], key = "#userId")
    suspend fun getUser(userId: Long): User {
        return userRepository.findById(userId) ?: throw NoSuchElementException()
    }
}
```

이유는 Spring AOP가 coroutine을 인식하지 못하기 때문이다. `suspend` 함수는 컴파일 후 마지막 파라미터로 `Continuation<T>`가 추가된 일반 함수가 된다. Spring의 캐시 인터셉터는 메서드 반환 타입이 `Object`(혹은 `CompletableFuture` 등 지원 타입)여야 값을 캐시에 저장할 수 있는데, coroutine 중단점이 있는 함수는 그 반환 타입 처리를 AOP 레이어에서 제대로 추적하지 못한다.

Spring Framework 6.1(Spring Boot 3.2)부터 coroutine `suspend` 함수에 대한 캐시 지원이 추가됐다. 그 전 버전이라면 우회해야 한다.

**방법 1 — 캐시 로직을 non-suspend 함수로 분리한다.**

```kotlin
@Service
class UserService(
    private val userRepository: UserRepository,
    private val cacheManager: CacheManager
) {

    suspend fun getUser(userId: Long): User {
        val cache = cacheManager.getCache("user")
        cache?.get(userId)?.get()?.let { return it as User }

        val user = userRepository.findById(userId) ?: throw NoSuchElementException()
        cache?.put(userId, user)
        return user
    }
}
```

`suspend` 컨텍스트 안에서 `CacheManager`를 직접 다루는 방식이다. 어노테이션이 없어서 번거롭지만 동작이 명확하다.

**방법 2 — blocking 래퍼 함수에 어노테이션을 붙이고 suspend에서 위임한다.**

```kotlin
@Service
class UserCacheHelper(private val userRepository: UserRepository) {

    @Cacheable(value = ["user"], key = "#userId")
    fun getUserBlocking(userId: Long): User {
        // runBlocking은 coroutine 컨텍스트 밖에서만 써야 한다
        // 여기서는 서비스 레이어에서 직접 호출할 경우를 위한 예시
        return userRepository.findByIdBlocking(userId) ?: throw NoSuchElementException()
    }
}

@Service
class UserService(
    private val userCacheHelper: UserCacheHelper,
    private val userRepository: UserRepository
) {

    suspend fun getUser(userId: Long): User {
        // IO dispatcher로 전환해서 blocking 캐시 헬퍼를 호출한다
        return withContext(Dispatchers.IO) {
            userCacheHelper.getUserBlocking(userId)
        }
    }
}
```

`Dispatchers.IO`로 전환하면 coroutine 스레드 풀을 막지 않는다. 하지만 `UserRepository`가 `suspend` 함수만 제공한다면 이 패턴을 쓸 수 없다. reactive 또는 blocking 변형이 필요하다.

**Spring Boot 3.2 이상이라면** `@Cacheable`이 `suspend` 함수에서 정상 동작하므로 별도 처리 없이 어노테이션만 붙이면 된다. 단, 반환 타입이 nullable이면 `unless = "#result == null"` 처리를 빠뜨리지 않는다.

```kotlin
// Spring Boot 3.2+
@Cacheable(value = ["user"], key = "#userId", unless = "#result == null")
suspend fun getUser(userId: Long): User? {
    return userRepository.findById(userId)
}
```
