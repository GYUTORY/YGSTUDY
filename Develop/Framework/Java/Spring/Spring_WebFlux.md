---
title: Spring WebFlux
tags: [spring, webflux, reactive, mono, flux, r2dbc, webclient, netty, non-blocking, backpressure, websocket]
updated: 2026-03-26
---

# Spring WebFlux

## 개요

Spring WebFlux는 비동기-논블로킹 리액티브 웹 프레임워크다. Spring MVC의 요청-스레드 모델 대신, 소수의 스레드로 많은 동시 연결을 처리한다. I/O 바운드 워크로드에서 높은 처리량을 낸다.

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

### 2. 어노테이션 컨트롤러

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

### 3. Functional Endpoints

어노테이션 컨트롤러의 대안이다. `RouterFunction`으로 라우팅을 정의하고, `HandlerFunction`으로 요청을 처리한다. 라우팅 로직이 한 곳에 모이기 때문에 API 구조를 한눈에 파악하기 좋다.

```java
@Configuration
public class UserRouter {

    @Bean
    public RouterFunction<ServerResponse> userRoutes(UserHandler handler) {
        return RouterFunctions.route()
            .path("/api/users", builder -> builder
                .GET("/{id}", handler::getUser)
                .GET("", handler::getAllUsers)
                .POST("", handler::createUser)
                .DELETE("/{id}", handler::deleteUser)
            )
            .build();
    }
}
```

```java
@Component
public class UserHandler {

    private final UserService userService;

    public UserHandler(UserService userService) {
        this.userService = userService;
    }

    public Mono<ServerResponse> getUser(ServerRequest request) {
        String id = request.pathVariable("id");
        return userService.findById(id)
            .flatMap(user -> ServerResponse.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(UserResponse.from(user)))
            .switchIfEmpty(ServerResponse.notFound().build());
    }

    public Mono<ServerResponse> getAllUsers(ServerRequest request) {
        Flux<UserResponse> users = userService.findAll().map(UserResponse::from);
        return ServerResponse.ok()
            .contentType(MediaType.APPLICATION_JSON)
            .body(users, UserResponse.class);
    }

    public Mono<ServerResponse> createUser(ServerRequest request) {
        return request.bodyToMono(CreateUserRequest.class)
            .flatMap(userService::create)
            .flatMap(user -> ServerResponse
                .created(URI.create("/api/users/" + user.getId()))
                .bodyValue(UserResponse.from(user)));
    }

    public Mono<ServerResponse> deleteUser(ServerRequest request) {
        String id = request.pathVariable("id");
        return userService.deleteById(id)
            .then(ServerResponse.noContent().build());
    }
}
```

Functional Endpoints에서 요청 검증은 직접 해야 한다. `@Valid` 같은 어노테이션이 안 먹는다.

```java
public Mono<ServerResponse> createUser(ServerRequest request) {
    return request.bodyToMono(CreateUserRequest.class)
        .doOnNext(this::validate) // 직접 검증
        .flatMap(userService::create)
        .flatMap(user -> ServerResponse.created(URI.create("/api/users/" + user.getId()))
            .bodyValue(UserResponse.from(user)));
}

private void validate(CreateUserRequest req) {
    Errors errors = new BeanPropertyBindingResult(req, "request");
    validator.validate(req, errors);
    if (errors.hasErrors()) {
        throw new ServerWebInputException(errors.toString());
    }
}
```

### 4. R2DBC (Reactive Database)

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

#### R2DBC 트랜잭션

리액티브 환경에서 `@Transactional`은 동작 방식이 다르다. Spring MVC에서는 ThreadLocal에 트랜잭션 컨텍스트를 저장하지만, WebFlux에서는 Reactor Context에 저장한다.

```java
@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final InventoryRepository inventoryRepository;
    private final TransactionalOperator txOperator;

    // 방법 1: @Transactional (선언적)
    // ReactiveTransactionManager 빈이 있어야 동작한다
    @Transactional
    public Mono<Order> placeOrder(OrderRequest request) {
        return inventoryRepository.decreaseStock(request.getProductId(), request.getQuantity())
            .then(orderRepository.save(Order.from(request)));
    }

    // 방법 2: TransactionalOperator (프로그래밍 방식)
    // 트랜잭션 범위를 더 세밀하게 제어할 때 사용한다
    public Mono<Order> placeOrderManual(OrderRequest request) {
        return inventoryRepository.decreaseStock(request.getProductId(), request.getQuantity())
            .then(orderRepository.save(Order.from(request)))
            .as(txOperator::transactional);
    }
}
```

주의할 점:
- `@Transactional` 메서드에서 Mono/Flux를 반환해야 한다. `void`로 반환하면 트랜잭션이 안 걸린다.
- 리액티브 체인이 끊기면 트랜잭션도 끊긴다. `.subscribe()`를 체인 중간에 호출하면 별도 구독이 생기면서 트랜잭션 밖에서 실행된다.
- R2DBC는 JPA의 `@Entity` 연관 매핑이 없다. join이 필요하면 `@Query`로 직접 작성하거나 서비스 레이어에서 조합해야 한다.

```java
// 트랜잭션 전파 확인용 — 문제가 생기면 로그로 확인한다
@Transactional
public Mono<Void> outerMethod() {
    return innerService.innerMethod() // 이 메서드도 @Transactional이면 같은 트랜잭션에 참여
        .doOnSubscribe(s -> log.info("tx active: {}",
            TransactionSynchronizationManager.isActualTransactionActive()));
}
```

### 5. WebClient (HTTP 클라이언트)

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

### 6. 에러 처리

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

### 7. 블로킹 코드 통합

기존 블로킹 라이브러리를 WebFlux에서 사용할 때.

```java
// 이벤트 루프 스레드에서 블로킹 호출하면 안 된다
Mono.just(jdbcTemplate.query(...)); // 이러면 이벤트 루프가 멈춘다

// 별도 스케줄러에서 블로킹 실행
Mono.fromCallable(() -> jdbcTemplate.query(...))
    .subscribeOn(Schedulers.boundedElastic());  // 블로킹 전용 스레드 풀
```

## Backpressure

리액티브 스트림의 핵심 개념이다. Consumer가 처리할 수 있는 속도보다 Producer가 데이터를 빠르게 보내면 문제가 생긴다. Backpressure는 Consumer가 Producer에게 "나 이만큼만 처리할 수 있으니 천천히 보내라"고 알려주는 메커니즘이다.

```java
// request(n): Subscriber가 n개만 요청한다. Reactor 내부에서 자동 관리한다.
// 실무에서 직접 request()를 호출할 일은 거의 없고, 연산자로 제어한다.

// limitRate: 한 번에 가져오는 양을 제한
Flux.range(1, 10000)
    .limitRate(100)  // 내부적으로 100개씩 request
    .subscribe(item -> process(item));

// onBackpressureBuffer: 처리 못하는 데이터를 버퍼에 저장
Flux.interval(Duration.ofMillis(1))
    .onBackpressureBuffer(1000)  // 버퍼 크기 1000
    .subscribe(item -> slowProcess(item));

// onBackpressureDrop: 처리 못하면 버린다
Flux.interval(Duration.ofMillis(1))
    .onBackpressureDrop(dropped -> log.warn("dropped: {}", dropped))
    .subscribe(item -> slowProcess(item));

// onBackpressureLatest: 최신 값만 유지하고 나머지 버린다
Flux.interval(Duration.ofMillis(1))
    .onBackpressureLatest()
    .subscribe(item -> slowProcess(item));
```

실무에서 Backpressure 문제를 겪는 경우:
- DB에서 대량 데이터를 Flux로 읽어서 외부 API에 하나씩 보낼 때 — `flatMap`의 concurrency 파라미터로 동시 실행 수를 제한한다
- WebSocket이나 SSE로 데이터를 푸시할 때 클라이언트가 느리면 — `onBackpressureBuffer`에 maxSize를 설정하고 overflow 시 연결을 끊는다
- `Flux.interval()`은 시간 기반이라 backpressure를 지원하지 않는다. 느린 subscriber와 함께 쓰면 `OverflowException`이 난다

```java
// DB에서 10만 건 읽어서 외부 API 호출하는 경우
userRepository.findAll()
    .flatMap(user -> externalApi.sync(user), 10)  // 동시 10건까지만
    .subscribe();

// flatMap의 두 번째 파라미터(concurrency)를 안 쓰면 기본값이 256이다
// 외부 API에 동시 256개 요청이 나가면서 rate limit에 걸리는 경우가 많다
```

## Reactor Context

리액티브 체인은 스레드를 넘나들기 때문에 ThreadLocal이 안 먹는다. MDC 로깅, 인증 정보 전파, 트레이싱 ID 같은 것들을 리액티브 체인 전체에 전달하려면 Reactor Context를 써야 한다.

```java
// Context에 값 쓰기 — 체인의 아래(downstream)에서 위(upstream)로 전파된다
// contextWrite는 체인의 마지막에 가까운 곳에 쓴다
Mono.deferContextual(ctx -> {
        String traceId = ctx.get("traceId");
        log.info("[{}] processing", traceId);
        return userService.findById(id);
    })
    .contextWrite(Context.of("traceId", UUID.randomUUID().toString()));
```

#### MDC 로깅 연동

WebFlux에서 로그에 traceId를 남기려면 MDC와 Reactor Context를 연결해야 한다.

```java
// WebFilter로 요청마다 traceId를 Context에 넣는다
@Component
public class TraceIdFilter implements WebFilter {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String traceId = exchange.getRequest().getHeaders()
            .getFirst("X-Trace-Id");
        if (traceId == null) {
            traceId = UUID.randomUUID().toString();
        }
        String finalTraceId = traceId;
        return chain.filter(exchange)
            .contextWrite(Context.of("traceId", finalTraceId));
    }
}
```

```java
// Reactor의 Hooks로 MDC 자동 복원
// 애플리케이션 시작 시 한 번 설정한다
@PostConstruct
public void setupReactorMdc() {
    Hooks.onEachOperator("mdc",
        Operators.lift((scannable, subscriber) -> new CoreSubscriber<Object>() {
            @Override
            public Context currentContext() {
                return subscriber.currentContext();
            }

            @Override
            public void onSubscribe(Subscription s) {
                subscriber.onSubscribe(s);
            }

            @Override
            public void onNext(Object o) {
                copyContextToMdc(subscriber.currentContext());
                subscriber.onNext(o);
            }

            @Override
            public void onError(Throwable t) {
                copyContextToMdc(subscriber.currentContext());
                subscriber.onError(t);
            }

            @Override
            public void onComplete() {
                copyContextToMdc(subscriber.currentContext());
                subscriber.onComplete();
            }
        }));
}

private void copyContextToMdc(Context context) {
    if (context.hasKey("traceId")) {
        MDC.put("traceId", context.get("traceId"));
    }
}
```

Reactor 3.5+에서는 `Micrometer`와의 자동 Context 전파를 지원한다. `context-propagation` 라이브러리를 쓰면 위처럼 수동으로 Hooks를 설정하지 않아도 된다.

```java
// build.gradle
// implementation 'io.micrometer:context-propagation:1.1.1'

// 애플리케이션 시작 시
Hooks.enableAutomaticContextPropagation();
```

#### 인증 정보 전파

Spring Security의 `ReactiveSecurityContextHolder`도 내부적으로 Reactor Context를 쓴다.

```java
// 현재 인증 정보 가져오기
ReactiveSecurityContextHolder.getContext()
    .map(SecurityContext::getAuthentication)
    .map(auth -> (UserDetails) auth.getPrincipal())
    .flatMap(user -> orderService.findByUserId(user.getId()));
```

## WebSocket

SSE는 서버 → 클라이언트 단방향이다. 양방향 실시간 통신이 필요하면 WebSocket을 쓴다.

```java
@Configuration
public class WebSocketConfig {

    @Bean
    public HandlerMapping webSocketMapping(ChatWebSocketHandler handler) {
        Map<String, WebSocketHandler> map = Map.of("/ws/chat", handler);
        SimpleUrlHandlerMapping mapping = new SimpleUrlHandlerMapping();
        mapping.setUrlMap(map);
        mapping.setOrder(-1); // 다른 핸들러보다 먼저 매칭
        return mapping;
    }

    @Bean
    public WebSocketHandlerAdapter handlerAdapter() {
        return new WebSocketHandlerAdapter();
    }
}
```

```java
@Component
public class ChatWebSocketHandler implements WebSocketHandler {

    private final Sinks.Many<String> chatSink = Sinks.many().multicast().onBackpressureBuffer();

    @Override
    public Mono<Void> handle(WebSocketSession session) {
        // 클라이언트 → 서버: 메시지 수신
        Mono<Void> input = session.receive()
            .map(WebSocketMessage::getPayloadAsText)
            .doOnNext(msg -> chatSink.tryEmitNext(msg))
            .then();

        // 서버 → 클라이언트: 브로드캐스트
        Mono<Void> output = session.send(
            chatSink.asFlux()
                .map(session::textMessage)
        );

        // input과 output을 동시에 처리
        return Mono.zip(input, output).then();
    }
}
```

`Sinks`는 Reactor 3.4에서 `Processor`를 대체한다. 멀티스레드 환경에서 안전하게 값을 발행하는 용도다.

```java
// Sinks 종류
Sinks.many().multicast().onBackpressureBuffer();   // 여러 subscriber, 버퍼링
Sinks.many().unicast().onBackpressureBuffer();     // 단일 subscriber
Sinks.many().replay().limit(10);                    // 최근 10개 재생

// 값 발행
Sinks.EmitResult result = sink.tryEmitNext(value);
if (result.isFailure()) {
    // FAIL_NON_SERIALIZED: 동시 발행 충돌
    // FAIL_OVERFLOW: 버퍼 초과
    // FAIL_CANCELLED: subscriber가 취소
    log.warn("emit failed: {}", result);
}
```

WebSocket 연결 관리 시 주의할 점:
- 세션이 끊기면 `receive()`의 Flux가 complete된다. 이 시점에 리소스 정리를 해야 한다.
- 클라이언트가 느려서 메시지를 못 받으면 버퍼가 무한히 쌓인다. `onBackpressureBuffer()`에 maxSize를 꼭 설정한다.
- ping/pong 프레임은 Netty가 자동 처리하지만, 애플리케이션 레벨 heartbeat가 필요하면 별도로 구현해야 한다.

## 테스트

### WebTestClient

WebFlux 컨트롤러의 통합 테스트 도구다. 실제 서버를 띄우거나, MockServer로 테스트한다.

```java
@WebFluxTest(UserController.class)
class UserControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private UserService userService;

    @Test
    void getUser_존재하면_200() {
        User user = new User(1L, "kim", "kim@test.com");
        when(userService.findById("1")).thenReturn(Mono.just(user));

        webTestClient.get()
            .uri("/api/users/1")
            .exchange()
            .expectStatus().isOk()
            .expectBody()
            .jsonPath("$.name").isEqualTo("kim")
            .jsonPath("$.email").isEqualTo("kim@test.com");
    }

    @Test
    void getUser_없으면_404() {
        when(userService.findById("999")).thenReturn(Mono.empty());

        webTestClient.get()
            .uri("/api/users/999")
            .exchange()
            .expectStatus().isNotFound();
    }

    @Test
    void getAllUsers_스트리밍() {
        when(userService.findAll()).thenReturn(
            Flux.just(new User(1L, "kim", "a@b.com"), new User(2L, "lee", "c@d.com")));

        webTestClient.get()
            .uri("/api/users")
            .exchange()
            .expectStatus().isOk()
            .expectBodyList(UserResponse.class).hasSize(2);
    }

    @Test
    void createUser_유효하면_201() {
        CreateUserRequest req = new CreateUserRequest("kim", "kim@test.com");
        User created = new User(1L, "kim", "kim@test.com");
        when(userService.create(any())).thenReturn(Mono.just(created));

        webTestClient.post()
            .uri("/api/users")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(req)
            .exchange()
            .expectStatus().isCreated()
            .expectBody()
            .jsonPath("$.id").isEqualTo(1);
    }
}
```

Functional Endpoints 테스트는 `RouterFunction`을 직접 바인딩한다.

```java
@Test
void functionalEndpoint_테스트() {
    UserHandler handler = new UserHandler(mockUserService);
    RouterFunction<ServerResponse> route = new UserRouter().userRoutes(handler);

    WebTestClient client = WebTestClient
        .bindToRouterFunction(route)
        .build();

    client.get()
        .uri("/api/users/1")
        .exchange()
        .expectStatus().isOk();
}
```

### StepVerifier

리액티브 스트림의 동작을 단계별로 검증한다. 서비스 레이어 단위 테스트에 쓴다.

```java
@Test
void findById_존재하면_반환() {
    Mono<User> result = userService.findById("1");

    StepVerifier.create(result)
        .assertNext(user -> {
            assertThat(user.getName()).isEqualTo("kim");
            assertThat(user.getEmail()).isEqualTo("kim@test.com");
        })
        .verifyComplete();
}

@Test
void findById_없으면_에러() {
    Mono<User> result = userService.findById("999");

    StepVerifier.create(result)
        .expectError(NotFoundException.class)
        .verify();
}

@Test
void findAll_순서_확인() {
    Flux<User> result = userService.findAll();

    StepVerifier.create(result)
        .expectNextCount(3)
        .verifyComplete();
}

// 시간 기반 테스트 — virtual time으로 실제 대기 없이 검증
@Test
void interval_테스트() {
    StepVerifier.withVirtualTime(() ->
            Flux.interval(Duration.ofHours(1)).take(3))
        .expectSubscription()
        .thenAwait(Duration.ofHours(3))
        .expectNext(0L, 1L, 2L)
        .verifyComplete();
}
```

## 실무 트러블슈팅

### 리액티브 체인 디버깅

리액티브 코드에서 에러가 나면 스택트레이스가 거의 쓸모없다. 어느 연산자에서 터졌는지 알 수 없다.

```java
// checkpoint: 체인에 이름을 붙여서 에러 발생 위치를 추적한다
userRepository.findById(id)
    .checkpoint("findById 이후")
    .flatMap(user -> orderRepository.findByUserId(user.getId()))
    .checkpoint("findByUserId 이후")
    .map(order -> OrderResponse.from(order));

// 에러 시 출력 예:
// Assembly trace from producer [checkpoint("findByUserId 이후")]
```

```java
// log(): 구독, 요청, 데이터 흐름을 전부 출력한다. 디버깅 끝나면 반드시 제거한다.
userRepository.findById(id)
    .log("UserRepo.findById")  // onSubscribe, request, onNext, onComplete 전부 출력
    .flatMap(user -> orderService.getOrders(user));
```

```java
// Hooks.onOperatorDebug(): 모든 연산자에 스택트레이스를 붙인다
// 성능이 심하게 떨어지므로 로컬 개발에서만 쓴다
// 운영 환경에서는 ReactorDebugAgent를 쓴다

// 로컬 개발용
Hooks.onOperatorDebug();

// 운영 환경용 — 바이트코드 변환 방식이라 오버헤드가 적다
// build.gradle: implementation 'io.projectreactor:reactor-tools'
ReactorDebugAgent.init();
```

### BlockHound — 블로킹 호출 탐지

이벤트 루프 스레드에서 블로킹 호출이 일어나면 전체 처리량이 급락한다. 문제는 코드만 봐서는 찾기 어렵다. `Thread.sleep()`, `InputStream.read()`, JDBC 호출 같은 게 라이브러리 깊숙이 숨어있는 경우가 많다.

```java
// build.gradle
// testImplementation 'io.projectreactor.tools:blockhound:1.0.9.RELEASE'

// 테스트 시 활성화
@BeforeAll
static void setUp() {
    BlockHound.install();
}

@Test
void 블로킹_호출이_없어야_한다() {
    // BlockHound가 설치된 상태에서 블로킹 호출이 발생하면
    // reactor.blockhound.BlockingOperationError가 던져진다
    StepVerifier.create(userService.findById("1"))
        .assertNext(user -> assertNotNull(user))
        .verifyComplete();
}
```

```java
// 특정 블로킹 호출을 허용해야 할 때 (라이브러리 내부 등)
BlockHound.install(builder -> builder
    .allowBlockingCallsInside(
        "com.example.legacy.LegacyClient", "connect")
);
```

BlockHound가 잡아내는 흔한 케이스:
- `ObjectMapper`로 JSON 직렬화할 때 내부적으로 블로킹 I/O가 일어나는 경우 — 대부분의 Jackson 설정에서는 문제없지만, 특정 SerializerProvider 구현이 파일을 읽는 경우가 있다
- Redis Lettuce 드라이버가 DNS를 동기 resolve하는 경우
- 로깅 프레임워크가 파일에 동기로 쓰는 경우 — Logback의 `AsyncAppender`를 써야 한다

### 메모리 누수 패턴

리액티브 코드에서 구독을 관리하지 않으면 메모리가 새는 경우가 있다.

```java
// 구독을 저장하지 않고 fire-and-forget으로 호출하는 패턴
// Disposable이 GC되면서 구독이 취소될 수도 있고, 안 될 수도 있다
void handleEvent(Event event) {
    processAsync(event).subscribe(); // Disposable을 버린다
}

// subscribe()를 무한 Flux에 대해 호출하고 취소하지 않으면 영원히 실행된다
Flux.interval(Duration.ofSeconds(1))
    .subscribe(i -> check()); // 언제 멈추나?

// 해결: Disposable을 관리한다
private Disposable healthCheck;

@PostConstruct
void start() {
    healthCheck = Flux.interval(Duration.ofSeconds(1))
        .subscribe(i -> check());
}

@PreDestroy
void stop() {
    if (healthCheck != null) {
        healthCheck.dispose();
    }
}
```

```java
// 자주 보이는 메모리 누수: WebSocket 세션에서 Sinks를 연결 해제 시 정리하지 않는 경우
// 세션별 Flux를 Map에 저장하고, 연결 끊길 때 제거해야 한다
private final Map<String, Sinks.Many<String>> sessions = new ConcurrentHashMap<>();

@Override
public Mono<Void> handle(WebSocketSession session) {
    Sinks.Many<String> sink = Sinks.many().unicast().onBackpressureBuffer();
    sessions.put(session.getId(), sink);

    return session.send(sink.asFlux().map(session::textMessage))
        .doFinally(signal -> sessions.remove(session.getId()));
}
```

## Netty 설정과 튜닝

WebFlux의 기본 서버는 Netty다. 운영 환경에서는 기본값으로 충분하지 않은 경우가 있다.

```java
@Configuration
public class NettyConfig {

    @Bean
    public WebServerFactoryCustomizer<NettyReactiveWebServerFactory> nettyCustomizer() {
        return factory -> factory.addServerCustomizers(server -> server
            // 워커 스레드 수 — 기본값은 CPU 코어 수
            // I/O 작업이 많으면 늘리는 게 아니라, 비동기 처리를 점검해야 한다
            // 블로킹 코드가 섞여있을 때만 임시로 늘린다
            .runOn(LoopResources.create("custom-loop", 1,
                Runtime.getRuntime().availableProcessors() * 2, true))

            // 커넥션 타임아웃
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)

            // idle 타임아웃 — 연결 유지 시간
            .idleTimeout(Duration.ofSeconds(30))

            // 최대 동시 연결 수
            .maxKeepAliveRequests(1000)
        );
    }
}
```

```yaml
# application.yml로 설정하는 것들
server:
  port: 8080
  netty:
    # 요청 헤더 최대 크기
    max-initial-line-length: 8192
    # HTTP 요청 본문 최대 크기
    max-chunk-size: 65536
    # 연결 유지
    connection-timeout: 5000
  # HTTP/2 활성화
  http2:
    enabled: true
```

#### WebClient의 커넥션 풀 설정

WebClient는 내부적으로 Reactor Netty의 커넥션 풀을 사용한다. 외부 API를 많이 호출하면 풀 설정이 중요하다.

```java
@Bean
public WebClient webClient() {
    ConnectionProvider provider = ConnectionProvider.builder("custom")
        .maxConnections(200)                        // 전체 최대 커넥션
        .maxIdleTime(Duration.ofSeconds(30))        // idle 커넥션 유지 시간
        .maxLifeTime(Duration.ofMinutes(5))         // 커넥션 최대 수명
        .pendingAcquireTimeout(Duration.ofSeconds(10))  // 풀에서 커넥션 대기 시간
        .evictInBackground(Duration.ofSeconds(30))  // 백그라운드 정리 주기
        .build();

    HttpClient httpClient = HttpClient.create(provider)
        .responseTimeout(Duration.ofSeconds(5))
        .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 3000);

    return WebClient.builder()
        .clientConnector(new ReactorClientHttpConnector(httpClient))
        .build();
}
```

커넥션 풀 관련 에러:
- `PoolAcquireTimeoutException`: 풀에서 커넥션을 못 얻음. `pendingAcquireTimeout`이 짧거나 `maxConnections`가 부족하다. 원인은 대부분 응답이 느린 외부 API다.
- `PrematureCloseException`: 서버가 커넥션을 먼저 닫음. `maxLifeTime`을 서버의 keep-alive보다 짧게 설정한다.
- 메트릭에서 `active connections`가 계속 올라가면 응답 body를 소비하지 않는 코드가 있는지 확인한다. `retrieve()` 후 body를 안 읽으면 커넥션이 반환되지 않는다.

## 참고

- [Spring WebFlux 공식 문서](https://docs.spring.io/spring-framework/reference/web/webflux.html)
- [Project Reactor](https://projectreactor.io/docs/core/release/reference/)
- [Spring MVC REST API](Spring_MVC_REST_API.md) — MVC 방식과 비교
- [Spring Data JPA](Spring_Data_JPA.md) — 블로킹 DB 접근 (비교)
