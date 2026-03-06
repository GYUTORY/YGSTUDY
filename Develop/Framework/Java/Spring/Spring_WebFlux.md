---
title: Spring WebFlux 가이드
tags: [spring, webflux, reactive, mono, flux, r2dbc, webclient, netty, non-blocking]
updated: 2026-03-01
---

# Spring WebFlux

## 개요

Spring WebFlux는 **비동기-논블로킹 리액티브 웹 프레임워크**이다. Spring MVC의 요청-스레드 모델 대신, 소수의 스레드로 많은 동시 연결을 처리한다. I/O 바운드 워크로드에서 높은 처리량을 제공한다.

```
Spring MVC (블로킹):
  요청 1 → 스레드 1 (DB 쿼리 대기...) → 응답
  요청 2 → 스레드 2 (API 호출 대기...) → 응답
  요청 3 → 스레드 3 (파일 읽기 대기...) → 응답
  → 200 스레드 풀 = 최대 200 동시 요청

Spring WebFlux (논블로킹):
  요청 1 → 이벤트 루프 (DB 쿼리 요청 → 다른 요청 처리)
  요청 2 → 이벤트 루프 (API 호출 요청 → 다른 요청 처리)
  요청 3 → 이벤트 루프 (파일 읽기 요청 → 다른 요청 처리)
  → 소수 스레드(CPU 코어 수)로 수만 동시 연결
```

### MVC vs WebFlux 비교

| 항목 | Spring MVC | Spring WebFlux |
|------|-----------|---------------|
| **프로그래밍 모델** | 명령형 (Imperative) | 리액티브 (Reactive) |
| **서버** | Tomcat (서블릿) | **Netty** (논블로킹) |
| **스레드 모델** | 요청당 스레드 | 이벤트 루프 |
| **동시성** | 스레드 풀 크기 제한 | 소수 스레드로 대량 처리 |
| **DB 접근** | JDBC (블로킹) | R2DBC (논블로킹) |
| **HTTP 클라이언트** | RestTemplate | WebClient |
| **적합한 경우** | CRUD, 전통적 웹앱 | I/O 바운드, 스트리밍, 대량 연결 |

## 핵심

### 1. Mono와 Flux

리액티브 스트림의 두 가지 Publisher 타입.

```java
// Mono<T>: 0~1개 요소 (단건)
Mono<User> user = userRepository.findById(id);
Mono<Void> result = userRepository.save(user);

// Flux<T>: 0~N개 요소 (다건)
Flux<User> users = userRepository.findAll();
Flux<String> stream = Flux.just("a", "b", "c");
```

#### 생성

```java
// Mono 생성
Mono.just("Hello");
Mono.empty();
Mono.error(new RuntimeException("에러"));
Mono.fromCallable(() -> blockingOperation());
Mono.defer(() -> Mono.just(dynamicValue()));

// Flux 생성
Flux.just(1, 2, 3);
Flux.fromIterable(List.of(1, 2, 3));
Flux.range(1, 10);
Flux.interval(Duration.ofSeconds(1));  // 매 초마다 0, 1, 2, ...
Flux.empty();
```

#### 변환 연산자

```java
// map: 동기 변환
userMono.map(user -> user.getName());

// flatMap: 비동기 변환 (중요!)
userMono.flatMap(user -> orderRepository.findByUserId(user.getId()));

// flatMapMany: Mono → Flux
userMono.flatMapMany(user -> orderRepository.findByUserId(user.getId()));

// filter
users.filter(user -> user.getAge() >= 20);

// zip: 여러 Publisher 결합
Mono.zip(userMono, ordersMono, cartMono)
    .map(tuple -> new Dashboard(tuple.getT1(), tuple.getT2(), tuple.getT3()));

// switchIfEmpty: 비어있을 때 대체
userRepository.findById(id)
    .switchIfEmpty(Mono.error(new NotFoundException("User not found")));

// onErrorResume: 에러 시 대체
externalApi.call()
    .onErrorResume(ex -> cachedData.get());
```

### 2. 컨트롤러

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    @GetMapping("/{id}")
    public Mono<ResponseEntity<UserResponse>> getUser(@PathVariable String id) {
        return userService.findById(id)
            .map(user -> ResponseEntity.ok(UserResponse.from(user)))
            .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    @GetMapping
    public Flux<UserResponse> getAllUsers() {
        return userService.findAll()
            .map(UserResponse::from);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<UserResponse> createUser(@RequestBody @Valid Mono<CreateUserRequest> request) {
        return request
            .flatMap(userService::create)
            .map(UserResponse::from);
    }

    @DeleteMapping("/{id}")
    public Mono<ResponseEntity<Void>> deleteUser(@PathVariable String id) {
        return userService.deleteById(id)
            .then(Mono.just(ResponseEntity.noContent().<Void>build()))
            .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    // SSE 스트리밍
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<UserResponse> streamUsers() {
        return userService.findAll()
            .delayElements(Duration.ofMillis(500))
            .map(UserResponse::from);
    }
}
```

### 3. R2DBC (Reactive Database)

```java
// 의존성 (build.gradle)
// implementation 'org.springframework.boot:spring-boot-starter-data-r2dbc'
// implementation 'io.asyncer:r2dbc-mysql'

@Table("users")
public class User {
    @Id
    private Long id;
    private String name;
    private String email;
    private LocalDateTime createdAt;
}

public interface UserRepository extends ReactiveCrudRepository<User, Long> {

    Flux<User> findByNameContaining(String name);

    @Query("SELECT * FROM users WHERE age >= :minAge ORDER BY created_at DESC")
    Flux<User> findByMinAge(@Param("minAge") int minAge);

    Mono<Long> countByEmail(String email);
}
```

```yaml
# application.yml
spring:
  r2dbc:
    url: r2dbc:mysql://localhost:3306/mydb
    username: root
    password: password
    pool:
      initial-size: 5
      max-size: 20
```

### 4. WebClient (HTTP 클라이언트)

RestTemplate의 리액티브 대체.

```java
@Configuration
public class WebClientConfig {

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
            .baseUrl("https://api.example.com")
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .filter(ExchangeFilterFunctions.basicAuthentication("user", "pass"))
            .build();
    }
}

@Service
public class ExternalApiService {

    private final WebClient webClient;

    // GET 요청
    public Mono<UserDto> fetchUser(String id) {
        return webClient.get()
            .uri("/users/{id}", id)
            .retrieve()
            .onStatus(HttpStatusCode::is4xxClientError,
                response -> Mono.error(new NotFoundException("User not found")))
            .bodyToMono(UserDto.class)
            .timeout(Duration.ofSeconds(5))
            .retryWhen(Retry.backoff(3, Duration.ofSeconds(1)));
    }

    // POST 요청
    public Mono<OrderDto> createOrder(OrderRequest request) {
        return webClient.post()
            .uri("/orders")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(OrderDto.class);
    }

    // 여러 API 병렬 호출
    public Mono<Dashboard> getDashboard(String userId) {
        Mono<UserDto> user = fetchUser(userId);
        Mono<List<OrderDto>> orders = fetchOrders(userId).collectList();
        Mono<CartDto> cart = fetchCart(userId);

        return Mono.zip(user, orders, cart)
            .map(t -> new Dashboard(t.getT1(), t.getT2(), t.getT3()));
    }
}
```

### 5. 에러 처리

```java
@ControllerAdvice
public class GlobalErrorHandler {

    @ExceptionHandler(NotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public Mono<ErrorResponse> handleNotFound(NotFoundException ex) {
        return Mono.just(new ErrorResponse("NOT_FOUND", ex.getMessage()));
    }

    @ExceptionHandler(WebExchangeBindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Mono<ErrorResponse> handleValidation(WebExchangeBindException ex) {
        List<String> errors = ex.getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage())
            .toList();
        return Mono.just(new ErrorResponse("VALIDATION_ERROR", errors.toString()));
    }
}

// 리액티브 체인에서 에러 처리
userService.findById(id)
    .switchIfEmpty(Mono.error(new NotFoundException("User not found")))
    .onErrorResume(TimeoutException.class, ex -> {
        log.warn("Timeout, using cache");
        return cacheService.getUser(id);
    })
    .onErrorMap(DatabaseException.class, ex ->
        new ServiceException("DB error", ex));
```

### 6. 블로킹 코드 통합

기존 블로킹 라이브러리를 WebFlux에서 사용할 때.

```java
// ❌ 이벤트 루프 스레드에서 블로킹 호출 (절대 금지!)
Mono.just(jdbcTemplate.query(...));

// ✅ 별도 스케줄러에서 블로킹 실행
Mono.fromCallable(() -> jdbcTemplate.query(...))
    .subscribeOn(Schedulers.boundedElastic());  // 블로킹 전용 스레드 풀
```

## 참고

- [Spring WebFlux 공식 문서](https://docs.spring.io/spring-framework/reference/web/webflux.html)
- [Project Reactor](https://projectreactor.io/docs/core/release/reference/)
- [Spring MVC REST API](Spring_MVC_REST_API.md) — MVC 방식과 비교
- [Spring Data JPA](Spring_Data_JPA.md) — 블로킹 DB 접근 (비교)
