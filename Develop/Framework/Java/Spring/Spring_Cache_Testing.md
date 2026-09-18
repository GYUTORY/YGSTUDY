---
title: Spring Cache 테스트
tags: [spring, cache, java, testing]
updated: 2026-09-18
---

# Spring Cache 테스트

Spring Cache는 AOP 프록시 기반이라 테스트가 일반 단위 테스트와 다르게 동작한다. 메서드 자체가 아니라 프록시를 통해 호출되는지 여부가 캐시 동작을 결정하기 때문에, 테스트에서도 Spring 컨텍스트가 만든 프록시 객체를 통해야 캐시 어노테이션이 처리된다.

직접 `new ProductService(mockRepo)`로 만든 인스턴스를 쓰면 프록시가 없어 `@Cacheable`이 붙어 있어도 캐시가 동작하지 않는다. `@SpringBootTest`나 최소 컨텍스트에서 `@Autowired`로 주입받은 객체를 써야 한다.

## 캐시를 꺼야 하는 테스트 vs 켜야 하는 테스트

서비스 로직을 검증하는 단위 테스트에서는 캐시를 끄는 게 낫다. 캐시가 켜져 있으면 첫 번째 테스트가 값을 캐시에 넣고, 두 번째 테스트가 DB 상태와 다른 캐시 값을 받아 실패한다. 테스트 간 격리가 깨지고 순서에 의존하는 플래키 테스트가 된다.

캐시 동작 자체를 검증하는 테스트(히트/미스 여부, evict 후 상태)에서는 실제 `CacheManager`를 써야 의미가 있다.

### NoOpCacheManager — 캐시 비활성화

`NoOpCacheManager`를 쓰면 캐시 어노테이션을 코드에 그대로 두면서 실제 캐싱 동작만 끌 수 있다. `Cache` 인터페이스를 구현하지만 모든 연산이 no-op이다. `get`은 항상 null을 반환하고 `put`은 버린다. 덕분에 `@Cacheable`이 붙은 메서드는 매 호출마다 실제 로직을 실행한다.

```java
@TestConfiguration
public class NoOpCacheConfig {

    @Bean
    @Primary
    public CacheManager cacheManager() {
        return new NoOpCacheManager();
    }
}
```

```java
@SpringBootTest
@Import(NoOpCacheConfig.class)
class ProductServiceTest {

    @Autowired
    private ProductService productService;

    @MockBean
    private ProductRepository productRepository;

    @Test
    void 캐시_없이_항상_DB_조회() {
        given(productRepository.findById(1L))
            .willReturn(Optional.of(new Product(1L, "상품")));

        productService.getProduct(1L);
        productService.getProduct(1L);

        verify(productRepository, times(2)).findById(1L);
    }
}
```

`@Primary`를 붙여야 애플리케이션 설정에서 정의한 `CacheManager`보다 이 빈이 우선된다. 빠뜨리면 실제 `CacheManager`와 충돌해서 `NoUniqueBeanDefinitionException`이 발생한다.

## @Cacheable 히트/미스 검증 — Mockito verify

캐시가 실제로 동작하는지 검증하는 가장 직관적인 방법은 메서드 내부의 호출 횟수를 세는 것이다. `@Cacheable`이 정상 동작하면 첫 번째 호출에만 `Repository`를 조회하고 이후는 캐시에서 반환하므로, `verify(repo, times(1))`로 확인할 수 있다.

```java
@SpringBootTest
class CacheHitTest {

    @Autowired
    private ProductService productService;

    @MockBean
    private ProductRepository productRepository;

    @Autowired
    private CacheManager cacheManager;

    @BeforeEach
    void clearCache() {
        cacheManager.getCache("products").clear();
    }

    @Test
    void 두번째_호출부터_캐시_히트() {
        given(productRepository.findById(1L))
            .willReturn(Optional.of(new Product(1L, "상품")));

        productService.getProduct(1L);
        productService.getProduct(1L);
        productService.getProduct(1L);

        verify(productRepository, times(1)).findById(1L);
    }

    @Test
    void 다른_키는_각각_캐시_미스() {
        given(productRepository.findById(anyLong()))
            .willReturn(Optional.of(new Product(1L, "상품")));

        productService.getProduct(1L);
        productService.getProduct(2L);
        productService.getProduct(1L);

        verify(productRepository, times(1)).findById(1L);
        verify(productRepository, times(1)).findById(2L);
    }
}
```

`@BeforeEach`에서 캐시를 초기화하지 않으면 테스트 간에 캐시가 공유된다. 같은 Spring 컨텍스트를 재사용하는 테스트들은 `CacheManager`도 공유한다. 앞선 테스트가 1L을 캐시에 넣었다면 `두번째_호출부터_캐시_히트` 테스트의 첫 번째 호출도 캐시 히트가 되어 `findById`가 한 번도 호출되지 않고 verify가 실패한다.

## Caffeine으로 슬라이스 테스트

`@SpringBootTest`는 전체 컨텍스트를 로드한다. 캐시 동작만 검증할 때는 필요한 빈만 최소로 로드하는 방식이 낫다. 전체 빌드가 느릴수록 이 차이가 체감된다.

```java
@ExtendWith(SpringExtension.class)
@ContextConfiguration(classes = {ProductService.class, CacheSliceTest.CacheTestConfig.class})
@EnableCaching
class CacheSliceTest {

    @TestConfiguration
    @EnableCaching
    static class CacheTestConfig {

        @Bean
        public CacheManager cacheManager() {
            CaffeineCacheManager manager = new CaffeineCacheManager("products");
            manager.setCaffeine(
                Caffeine.newBuilder()
                    .maximumSize(100)
                    .expireAfterWrite(10, TimeUnit.MINUTES)
            );
            return manager;
        }
    }

    @Autowired
    private ProductService productService;

    @MockBean
    private ProductRepository productRepository;

    @Autowired
    private CacheManager cacheManager;

    @BeforeEach
    void clearCache() {
        cacheManager.getCache("products").clear();
    }

    @Test
    void Caffeine_캐시_히트_검증() {
        given(productRepository.findById(1L))
            .willReturn(Optional.of(new Product(1L, "상품")));

        productService.getProduct(1L);
        productService.getProduct(1L);

        verify(productRepository, times(1)).findById(1L);
    }
}
```

`@EnableCaching`을 테스트 컨텍스트에 명시적으로 붙여야 한다. 빠뜨리면 `CacheManager` 빈이 있어도 캐시 어노테이션이 처리되지 않는다. 코드에 `@EnableCaching`이 붙어있어도 해당 설정 클래스가 로드되지 않으면 소용없다.

`CaffeineCacheManager("products")`처럼 캐시 이름을 명시하면 해당 이름 외의 캐시를 요청했을 때 예외가 발생한다. 서비스에서 쓰는 캐시 이름과 정확히 맞춰야 한다.

## @CacheEvict 후 상태 검증

evict가 동작했는지 확인하는 방법은 evict 이후 같은 키를 조회할 때 DB 접근이 발생하는지 보는 것이다.

```java
@SpringBootTest
class CacheEvictTest {

    @Autowired
    private ProductService productService;

    @MockBean
    private ProductRepository productRepository;

    @Autowired
    private CacheManager cacheManager;

    @BeforeEach
    void clearCache() {
        cacheManager.getCache("products").clear();
    }

    @Test
    void evict_후_다음_조회에서_DB_접근() {
        Product product = new Product(1L, "상품");
        given(productRepository.findById(1L)).willReturn(Optional.of(product));
        given(productRepository.save(any())).willReturn(product);

        productService.getProduct(1L);           // 캐시 채우기
        verify(productRepository, times(1)).findById(1L);

        productService.updateProduct(product);   // evict 발생

        productService.getProduct(1L);           // 캐시 미스 — DB 재조회
        verify(productRepository, times(2)).findById(1L);
    }

    @Test
    void allEntries_evict_후_모든_키_캐시_미스() {
        given(productRepository.findById(anyLong()))
            .willReturn(Optional.of(new Product(1L, "상품")));

        productService.getProduct(1L);
        productService.getProduct(2L);

        productService.clearProductCache();  // allEntries = true

        productService.getProduct(1L);
        productService.getProduct(2L);

        verify(productRepository, times(2)).findById(1L);
        verify(productRepository, times(2)).findById(2L);
    }
}
```

`CacheManager`에서 직접 `cache.get(key)`로 null 여부를 확인하는 방법도 있다. 다만 캐시 구현마다 내부 키 생성 방식이 다르다. `@Cacheable(key = "#id")`로 Long 타입 1L을 쓰면 실제 저장 키는 구현에 따라 Long 그대로이거나 `SimpleKey`로 감싸진다. `cache.get(1L)`이 null을 반환해도 실제로 값이 있는 경우가 생긴다. Mockito verify 방식은 캐시 구현 내부에 의존하지 않아서 더 안정적이다.

## @CachePut 검증

`@CachePut`은 항상 메서드를 실행하면서 결과를 캐시에 넣는다. 이후 `@Cacheable`로 조회했을 때 캐시 히트가 발생하는지가 검증 대상이다.

```java
@Test
void cachePut_후_조회_시_캐시_히트() {
    Product updated = new Product(1L, "수정된 상품");
    given(productRepository.save(any())).willReturn(updated);

    productService.updateProduct(updated);   // @CachePut — 항상 실행, 캐시 갱신

    productService.getProduct(1L);
    productService.getProduct(1L);

    // updateProduct 내부에서 save는 호출되지만, findById는 한 번도 호출되지 않아야 한다
    verify(productRepository, never()).findById(1L);
}
```

`@CachePut`이 달린 메서드의 키와 `@Cacheable`의 키가 일치해야 한다. `updateProduct`에서 `key = "#product.id"`를 쓰고 `getProduct`에서 `key = "#id"`를 쓰면 키 SpEL의 결과값이 같더라도 Spring이 동일 키로 인식한다. 하지만 캐시 이름(`value`)이 다르면 별개의 저장소이므로 히트가 발생하지 않는다.

## 테스트 간 캐시 격리

같은 Spring 컨텍스트를 재사용하는 테스트들이 `CacheManager`를 공유한다는 점이 핵심 문제다. 격리 방법은 세 가지다.

`@BeforeEach`에서 캐시를 초기화하는 방법이 가장 빠르다. 특정 캐시 이름을 알면 직접 지우고, 모르면 `cacheManager.getCacheNames()`로 전체를 순회한다.

```java
@BeforeEach
void clearCache() {
    cacheManager.getCacheNames()
        .forEach(name -> cacheManager.getCache(name).clear());
}
```

`@DirtiesContext`는 테스트마다 새 컨텍스트를 만들어서 캐시를 포함한 모든 상태를 초기화한다. 격리는 완벽하지만 컨텍스트를 재시작하는 비용이 크다. 캐시 격리만을 위해 쓰기에는 과하다.

캐시 동작 검증 테스트와 서비스 로직 테스트를 다른 클래스로 분리하는 방법도 있다. 캐시 동작을 검증할 때만 실제 `CacheManager`를 쓰는 컨텍스트를 올리고, 나머지는 `NoOpCacheManager`를 써서 공유 상태 자체를 없앤다. 컨텍스트도 분리되고 격리도 된다.

## Redis 통합 테스트

로컬 캐시(Caffeine)와 달리 Redis는 직렬화, TTL, 키 패턴을 실제 환경과 동일하게 검증해야 의미가 있다. Testcontainers로 Redis를 직접 띄우는 방법이 현실적이다.

```java
@SpringBootTest
@Testcontainers
class RedisCacheIntegrationTest {

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void redisProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", () -> redis.getMappedPort(6379));
    }

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CacheManager cacheManager;

    @BeforeEach
    void setup() {
        cacheManager.getCache("products").clear();
        productRepository.deleteAll();
    }

    @Test
    void Redis_캐시_히트_검증() {
        Product saved = productRepository.save(new Product("상품"));

        productService.getProduct(saved.getId());  // 캐시 채우기

        productRepository.deleteAll();              // DB에서 삭제 (캐시 우회)

        Product fromCache = productService.getProduct(saved.getId());
        assertThat(fromCache.getId()).isEqualTo(saved.getId());  // 캐시 히트
    }

    @Test
    void Redis_직렬화_정상_동작() {
        Product saved = productRepository.save(new Product("상품"));

        productService.getProduct(saved.getId());

        // Redis에 실제로 저장됐는지 확인
        Cache cache = cacheManager.getCache("products");
        Cache.ValueWrapper cached = cache.get(saved.getId());
        assertThat(cached).isNotNull();
        assertThat(((Product) cached.get()).getId()).isEqualTo(saved.getId());
    }
}
```

`@Container`를 static으로 선언해야 테스트 클래스 전체에서 컨테이너를 공유한다. 인스턴스 필드로 선언하면 테스트 메서드마다 컨테이너를 재시작해서 속도가 극도로 느려진다.

`spring.redis.host` 대신 `spring.data.redis.host`를 써야 한다. Spring Boot 3.x부터 Redis 프로퍼티 네임스페이스가 `spring.data.redis`로 바뀌었다. 이전 키를 쓰면 설정이 무시되고 기본 localhost:6379를 바라봐서 테스트가 실제 Redis 연결을 시도한다.

`@MockBean`을 쓰지 않고 실제 `ProductRepository`를 쓰는 게 포인트다. DB에 직접 넣고, 캐시를 채운 뒤, DB에서 삭제해도 캐시에서 반환하는 시나리오를 실제 저장소로 검증한다. `@MockBean`으로는 이 시나리오를 재현하기 어렵다.

직렬화 오류가 생기는 경우는 대부분 DTO 클래스를 수정한 뒤 기존 캐시를 지우지 않았을 때다. Redis에는 `@class` 필드로 클래스 경로가 박히는데, 패키지나 클래스명이 바뀌면 역직렬화에서 `SerializationException`이 발생한다. 통합 테스트에서 이 케이스를 미리 확인해두면 운영 배포 전에 잡을 수 있다.
