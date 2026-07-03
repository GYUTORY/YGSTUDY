---
title: Spring MVC와 REST API 설계
tags: [framework, java, spring, spring-mvc, rest-api, controller, exception-handling, validation]
updated: 2026-05-09
---

# Spring MVC와 REST API 설계

## 시작하기 전에

REST API를 만든다는 건 결국 HTTP 요청 하나를 받아서 자바 객체로 바꾸고, 비즈니스 로직을 돌린 뒤 다시 직렬화해서 응답으로 돌려주는 일이다. 이 단순해 보이는 흐름 안에 DispatcherServlet, HandlerMapping, ArgumentResolver, HttpMessageConverter, ExceptionHandler가 줄지어 끼어든다. 어느 단계가 무엇을 하는지 모르면 415가 떠도 원인을 못 찾고, 응답 JSON에 `null` 필드가 빠지거나 LocalDateTime이 배열로 나가는 사고를 만난다.

5년쯤 Spring을 만지면 Controller 코드보다 그 주변에서 시간을 더 쓰게 된다. 이 문서는 그 주변 이야기 위주로 정리한다.

## DispatcherServlet 내부 동작

### 요청이 Controller에 도달하기까지

DispatcherServlet은 모든 HTTP 요청을 받아 적절한 Controller로 분배하는 단일 진입점(Front Controller)이다. 흐름을 풀어 쓰면 이렇다.

```
HTTP 요청
   │
   ▼
[Servlet Filter Chain]            ← Spring 밖, javax.servlet
   │
   ▼
DispatcherServlet.doDispatch()
   │
   ├─ 1. HandlerMapping
   │     · @RequestMapping 메타데이터로 Controller 메서드 검색
   │     · RequestMappingHandlerMapping이 기본
   │
   ├─ 2. HandlerInterceptor.preHandle()  ← Spring MVC 안쪽
   │
   ├─ 3. HandlerAdapter.handle()
   │     ├─ HandlerMethodArgumentResolver  (파라미터 바인딩)
   │     ├─ Controller 메서드 실행
   │     └─ HandlerMethodReturnValueHandler (리턴값 처리)
   │           └─ HttpMessageConverter (JSON 직렬화)
   │
   ├─ 4. HandlerInterceptor.postHandle()
   │
   ├─ 5. processDispatchResult() (View 렌더링 또는 예외 처리)
   │
   └─ 6. HandlerInterceptor.afterCompletion()
```

여기서 헷갈리는 건 Filter와 Interceptor의 위치다. Filter는 Servlet 표준이라 DispatcherServlet 바깥에서 동작한다. Interceptor는 DispatcherServlet 안쪽, 즉 HandlerMapping이 끝나고 Controller 직전에 끼어든다.

### Filter와 Interceptor 선택 기준

실무에서 둘 중 무엇을 쓸지 고민될 때가 많다. 기준은 단순하다.

**Filter를 쓰는 경우:**
- Spring Bean에 의존하지 않는 처리 (요청 로깅, 인코딩 변환)
- 인증·인가 (Spring Security가 대표적인 Filter 기반 구현)
- 요청·응답 본문을 통째로 가공해야 할 때 (`ContentCachingRequestWrapper`)
- DispatcherServlet 진입 자체를 막아야 할 때

**Interceptor를 쓰는 경우:**
- HandlerMethod 정보가 필요한 경우 (어떤 Controller 메서드가 호출됐는지 알아야 할 때)
- Spring Bean을 주입받아야 할 때 (Service 호출 등)
- View 렌더링 전후로 ModelAndView를 가공해야 할 때

```java
// HandlerMethod에서 어노테이션을 꺼내는 Interceptor 예시
@Component
public class AuditInterceptor implements HandlerInterceptor {

    private final AuditService auditService;

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
        if (!(handler instanceof HandlerMethod method)) {
            return true;
        }
        Audit audit = method.getMethodAnnotation(Audit.class);
        if (audit != null) {
            req.setAttribute("auditAction", audit.value());
        }
        return true;
    }
}
```

Filter에서는 `handler` 정보가 없어 위 같은 처리가 불가능하다. 반대로 Interceptor에서 `request.getInputStream()`을 한 번 읽으면 Controller에서 `@RequestBody`가 비게 된다. 본문을 미리 손대야 한다면 Filter에서 `ContentCachingRequestWrapper`로 감싸야 한다.

## HandlerMethodArgumentResolver와 파라미터 바인딩

### @RequestParam, @ModelAttribute, @RequestBody 차이

세 어노테이션은 모두 요청 데이터를 메서드 파라미터로 가져오는 역할인데, 동작 방식이 완전히 다르다.

| 어노테이션 | 데이터 소스 | 변환기 | 검증 |
|-----------|------------|-------|-----|
| `@RequestParam` | 쿼리스트링, form-urlencoded | `Converter`, `PropertyEditor` | `@Validated` (메서드 레벨) |
| `@ModelAttribute` | 쿼리스트링, form-urlencoded, multipart | `WebDataBinder` (setter 또는 생성자) | `@Valid` |
| `@RequestBody` | request body (JSON 등) | `HttpMessageConverter` (Jackson) | `@Valid` |

요청 헤더 `Content-Type`이 무엇이냐가 1차 분기다.

```
Content-Type: application/x-www-form-urlencoded → @ModelAttribute, @RequestParam
Content-Type: multipart/form-data              → @ModelAttribute, @RequestPart
Content-Type: application/json                 → @RequestBody
```

### 실수하기 쉬운 케이스

**케이스 1: GET 요청에 @RequestBody를 쓴 경우**

GET 요청은 본문을 보내지 않는 게 표준이다. 일부 클라이언트는 무시하고 일부는 막는다. 검색 조건이 길어 본문에 담고 싶다면 POST로 바꾸거나 GET을 유지하되 `@ModelAttribute`로 받아야 한다.

```java
// 잘못된 사용: GET + @RequestBody
@GetMapping("/search")
public List<User> search(@RequestBody SearchCondition cond) { ... }

// 권장: GET + @ModelAttribute (생략 가능)
@GetMapping("/search")
public List<User> search(SearchCondition cond) { ... }  // 객체 타입은 기본 @ModelAttribute
```

**케이스 2: record 타입 @ModelAttribute 바인딩**

Spring 6 미만에서는 `@ModelAttribute`로 record를 바인딩하지 못한다. `WebDataBinder`가 setter를 찾기 때문이다. Spring 6.1부터 생성자 바인딩을 정식 지원한다. 이전 버전에서는 클래스로 만들거나 `@RequestParam` 개별로 받아야 한다.

**케이스 3: 단일 객체 파라미터 자동 추론**

```java
@GetMapping("/users")
public List<User> list(UserSearch search) { ... }
```

이 코드의 `search`는 자동으로 `@ModelAttribute`로 처리된다. 그런데 본문에 JSON을 보내도 절대 바인딩되지 않는다. 디버깅할 때 `@RequestBody`가 빠진 줄 모르고 한참 헤매는 경우가 잦다.

**케이스 4: @RequestParam에 컬렉션**

```java
@GetMapping("/items")
public List<Item> items(@RequestParam List<Long> ids) { ... }
```

`?ids=1,2,3` 또는 `?ids=1&ids=2&ids=3` 둘 다 받는다. 다만 콤마 구분 동작은 `Converter` 등록 여부에 따라 다르므로 `@RequestParam(required = false) List<Long> ids = new ArrayList<>()` 같은 기본값 처리가 필요하다.

## HttpMessageConverter 커스터마이징

`@RequestBody`로 들어오는 JSON을 객체로 바꾸고, 응답 객체를 JSON으로 바꾸는 역할이 `HttpMessageConverter`다. Spring Boot에서는 `MappingJackson2HttpMessageConverter`가 기본 등록된다. Jackson `ObjectMapper`만 손봐도 응답 포맷의 90%는 결정된다.

### Jackson ObjectMapper 설정

```java
@Configuration
public class JacksonConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer jacksonCustomizer() {
        return builder -> builder
            .featuresToDisable(
                SerializationFeature.WRITE_DATES_AS_TIMESTAMPS,         // 날짜를 ISO-8601 문자열로
                DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES        // 모르는 필드는 무시
            )
            .featuresToEnable(
                SerializationFeature.INDENT_OUTPUT                       // 개발 환경에서만
            )
            .serializationInclusion(JsonInclude.Include.NON_NULL)        // null 필드 제외
            .modules(new JavaTimeModule())                               // LocalDateTime 등 지원
            .timeZone(TimeZone.getTimeZone("Asia/Seoul"));
    }
}
```

`Jackson2ObjectMapperBuilderCustomizer`를 쓰면 Spring Boot가 만든 `ObjectMapper`에 설정만 얹는다. `@Bean ObjectMapper`로 통째로 교체하면 Spring Security OAuth 같은 모듈이 기본 설정에 의존하다 깨진다. 가능하면 Customizer 방식을 쓴다.

### LocalDateTime 직렬화 문제

`JavaTimeModule`을 등록하지 않으면 `LocalDateTime`이 `[2026,5,9,12,0,0]` 같은 배열로 나간다. Spring Boot 2.x부터는 자동 등록되지만, `@JsonFormat`으로 포맷을 명시하는 게 안전하다.

```java
public record OrderResponse(
    Long id,
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Seoul")
    LocalDateTime createdAt
) {}
```

전역 포맷이 필요하면 `application.yml`에 다음 설정을 추가한다.

```yaml
spring:
  jackson:
    date-format: yyyy-MM-dd HH:mm:ss
    time-zone: Asia/Seoul
    serialization:
      write-dates-as-timestamps: false
```

### snake_case 변환

응답 필드를 snake_case로 내려야 할 때가 있다 (모바일 클라이언트 요구사항이 자주 그렇다).

```java
// 전역 적용
@Bean
public Jackson2ObjectMapperBuilderCustomizer snakeCaseCustomizer() {
    return builder -> builder.propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
}
```

문제는 일부 API만 snake_case로 내려야 하는 상황이다. 이때는 DTO 클래스에 `@JsonNaming`을 붙인다.

```java
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record LegacyUserResponse(Long userId, String userName, LocalDateTime createdAt) {}
// → { "user_id": 1, "user_name": "kim", "created_at": "2026-05-09T..." }
```

camelCase ↔ snake_case 컨버전을 클라이언트마다 다르게 한다면 별도 `MappingJackson2HttpMessageConverter`를 등록하고 `produces`/`consumes`로 분기하는 방법도 있다. 다만 운영 부담이 커지므로 대부분은 한쪽으로 통일한다.

## Content Negotiation

### 응답 포맷을 결정하는 순서

같은 URL이라도 클라이언트가 무엇을 원하느냐에 따라 JSON, XML, CSV 등으로 응답할 수 있다. Spring은 다음 순서로 응답 타입을 결정한다.

1. URL 확장자 (`.json`, `.xml`) — Spring 5.3 이후 기본 비활성화
2. URL 쿼리 파라미터 (`?format=json`)
3. `Accept` 헤더

`Accept` 헤더 기반이 표준이다. Controller의 `produces`와 클라이언트의 `Accept`가 매칭되어야 응답이 나간다.

```java
@GetMapping(value = "/users/{id}", produces = MediaType.APPLICATION_JSON_VALUE)
public UserResponse getUser(@PathVariable Long id) { ... }
```

### Accept 헤더 트러블슈팅

**문제 1: 406 Not Acceptable**

클라이언트가 `Accept: application/xml`을 보냈는데 서버에 XML 컨버터가 없을 때 발생한다. Spring Boot 기본은 JSON만 등록되어 있으므로 XML이 필요하면 `jackson-dataformat-xml` 의존성을 추가해야 한다.

**문제 2: */*  처리**

브라우저나 일부 라이브러리는 `Accept: */*`를 보낸다. 이때 Spring은 등록된 컨버터 중 우선순위가 높은 것을 고르는데, 여러 컨버터가 있으면 의도치 않은 포맷이 나갈 수 있다. `produces`를 명시하면 강제할 수 있다.

**문제 3: JSON과 application/json 혼동**

`@RequestMapping(produces = "json")` 같은 잘못된 표기는 매칭되지 않는다. 반드시 `MediaType.APPLICATION_JSON_VALUE` 상수나 정확한 MIME 타입을 쓴다.

```java
// application.yml — Content Negotiation 동작 제어
spring:
  mvc:
    contentnegotiation:
      favor-parameter: false              # ?format=json 사용 안 함
      media-types:
        json: application/json
```

## ResponseEntity, @ResponseStatus, ResponseBodyAdvice

응답을 반환하는 방법이 세 가지인데, 각자 역할이 다르다.

### ResponseEntity

상태 코드와 헤더, 본문을 메서드별로 다르게 줘야 할 때 쓴다. 가장 자유도가 높다.

```java
@PostMapping
public ResponseEntity<UserResponse> create(@Valid @RequestBody CreateUserRequest req) {
    UserResponse created = userService.create(req);
    URI location = URI.create("/api/v1/users/" + created.id());
    return ResponseEntity.created(location)
        .header("X-Request-Id", MDC.get("requestId"))
        .body(created);
}
```

### @ResponseStatus

상태 코드가 항상 같은 메서드라면 `@ResponseStatus`로 선언한다. 본문을 그대로 반환하므로 코드가 깔끔하다.

```java
@PostMapping
@ResponseStatus(HttpStatus.CREATED)
public UserResponse create(@Valid @RequestBody CreateUserRequest req) {
    return userService.create(req);
}
```

예외 클래스에 붙여서 자동으로 상태 코드를 매핑할 수도 있다.

```java
@ResponseStatus(HttpStatus.NOT_FOUND)
public class UserNotFoundException extends RuntimeException { ... }
```

다만 `@ControllerAdvice`로 `ExceptionHandler`를 잡으면 `@ResponseStatus`가 무시된다. 둘이 동시에 있으면 ExceptionHandler가 이긴다.

### ResponseBodyAdvice

모든 응답을 가로채서 후처리하고 싶을 때 쓴다. 응답을 공통 Envelope로 감싸거나 암호화하는 등의 작업에 적합하다.

```java
@ControllerAdvice
public class CommonResponseAdvice implements ResponseBodyAdvice<Object> {

    @Override
    public boolean supports(MethodParameter returnType, Class<? extends HttpMessageConverter<?>> converterType) {
        // ErrorResponse나 ResponseEntity는 건드리지 않음
        return !returnType.getParameterType().equals(ErrorResponse.class);
    }

    @Override
    public Object beforeBodyWrite(Object body, MethodParameter returnType,
                                   MediaType selectedContentType,
                                   Class<? extends HttpMessageConverter<?>> selectedConverterType,
                                   ServerHttpRequest request, ServerHttpResponse response) {
        if (body instanceof ApiResponse<?>) return body;
        return ApiResponse.ok(body);
    }
}
```

`ResponseBodyAdvice`는 적용 범위가 넓은 만큼 위험하다. 모든 응답에 끼어들어 디버깅이 어려워지고, 일부 컨버터는 우회한다. Envelope 패턴이 정말 필요한지 다시 한번 검토하고 도입한다.

## 비동기 처리

Servlet 3.0부터 비동기 응답을 지원한다. Spring MVC에서는 `Callable`, `DeferredResult`, `WebAsyncTask`, `CompletableFuture`를 리턴 타입으로 쓰면 된다.

### Callable과 DeferredResult 차이

`Callable`은 Spring이 알아서 별도 스레드(`mvc.async.task-executor`)로 실행해 준다. 처리는 서버 내부에서 끝나고 결과만 비동기로 묶인다.

`DeferredResult`는 결과를 외부 이벤트가 결정한다. 메시지 큐에서 응답이 올 때까지 기다리거나, 다른 사용자의 요청이 들어와야 응답이 완성되는 롱폴링 같은 시나리오에 쓴다.

```java
// Callable: 무거운 작업을 다른 스레드로
@GetMapping("/heavy")
public Callable<ReportResponse> heavy() {
    return () -> reportService.generate();  // mvc.async.task-executor에서 실행
}

// DeferredResult: 외부 이벤트로 응답 완성
private final Map<Long, DeferredResult<MessageResponse>> waiters = new ConcurrentHashMap<>();

@GetMapping("/messages/wait")
public DeferredResult<MessageResponse> waitForMessage(@RequestParam Long userId) {
    DeferredResult<MessageResponse> result = new DeferredResult<>(30_000L, MessageResponse.empty());
    waiters.put(userId, result);
    result.onCompletion(() -> waiters.remove(userId));
    return result;
}

// 다른 곳에서 결과 세팅
public void onMessageArrived(Long userId, Message msg) {
    DeferredResult<MessageResponse> result = waiters.remove(userId);
    if (result != null) result.setResult(MessageResponse.from(msg));
}
```

### @Async와의 차이

`@Async`는 Spring AOP 기반 메서드 비동기 실행이다. Controller의 비동기 응답과는 다른 영역이다. `@Async` 메서드를 Controller에서 호출하면 호출 즉시 리턴되고 응답이 비어버린다. 비동기 결과를 응답으로 돌려주려면 `@Async`가 `CompletableFuture`를 반환하게 하고 Controller에서 그대로 리턴한다.

```java
@Service
public class ReportService {
    @Async
    public CompletableFuture<ReportResponse> generateAsync() {
        return CompletableFuture.completedFuture(generate());
    }
}

@RestController
public class ReportController {
    @GetMapping("/report")
    public CompletableFuture<ReportResponse> get() {
        return reportService.generateAsync();
    }
}
```

### 타임아웃 설정

비동기 응답이 영원히 안 오면 Tomcat 워커 스레드가 묶인다. 타임아웃을 반드시 건다.

```yaml
spring:
  mvc:
    async:
      request-timeout: 30000   # ms (전역 기본)
```

`DeferredResult`는 생성자에서 개별 타임아웃을 줄 수 있고, `onTimeout` 콜백으로 후처리한다. `@Async` 메서드에는 별도 타임아웃이 없으므로 `CompletableFuture.orTimeout()`을 쓴다.

## 검증 (Validation)

### Bean Validation 기본

```java
public record CreateUserRequest(
    @NotBlank(message = "이메일은 필수입니다")
    @Email(message = "올바른 이메일 형식이 아닙니다")
    String email,

    @NotBlank @Size(min = 8, max = 20)
    String password,

    @NotBlank @Size(min = 2, max = 50)
    String name
) {}
```

Controller 파라미터에 `@Valid`를 붙이면 위 제약이 검증되고, 실패 시 `MethodArgumentNotValidException`이 던져진다.

### 검증 그룹으로 생성/수정 분리

생성 시에는 모든 필드가 필수지만 수정 시에는 일부만 보내는 PATCH 시나리오가 흔하다. 같은 DTO를 쓰되 그룹으로 분리한다.

```java
public interface OnCreate {}
public interface OnUpdate {}

public record UserRequest(
    @NotNull(groups = OnUpdate.class)
    Long id,

    @NotBlank(groups = OnCreate.class)
    @Email(groups = {OnCreate.class, OnUpdate.class})
    String email,

    @NotBlank(groups = OnCreate.class)
    @Size(min = 8, max = 20, groups = {OnCreate.class, OnUpdate.class})
    String password
) {}

@PostMapping
public UserResponse create(@Validated(OnCreate.class) @RequestBody UserRequest req) { ... }

@PutMapping("/{id}")
public UserResponse update(@PathVariable Long id,
                           @Validated(OnUpdate.class) @RequestBody UserRequest req) { ... }
```

`@Valid`는 그룹을 지정할 수 없다. 그룹을 쓸 때는 Spring의 `@Validated`를 사용한다.

### ConstraintViolationException과 MethodArgumentNotValidException 차이

둘 다 검증 실패 예외인데, 발생 위치와 구조가 다르다.

| 항목 | MethodArgumentNotValidException | ConstraintViolationException |
|------|--------------------------------|------------------------------|
| 발생 위치 | Controller 메서드의 `@Valid @RequestBody` 객체 | `@Validated`가 클래스에 붙은 `@RequestParam`, `@PathVariable` 직접 검증 |
| 트리거 | DTO 객체 검증 | 메서드 파라미터 단일 값 검증 |
| 에러 정보 | `BindingResult` (필드 단위) | `Set<ConstraintViolation>` (path 단위) |
| 기본 응답 코드 | 400 | 500 (별도 처리 안 하면) |

```java
// MethodArgumentNotValidException 케이스
@PostMapping
public UserResponse create(@Valid @RequestBody CreateUserRequest req) { ... }

// ConstraintViolationException 케이스
@RestController
@Validated  // 클래스에 붙여야 동작
public class UserController {
    @GetMapping
    public List<UserResponse> list(@RequestParam @Min(0) int page,
                                    @RequestParam @Max(100) int size) { ... }
}
```

두 예외를 동일하게 응답으로 묶으려면 `@ControllerAdvice`에서 둘 다 핸들링한다.

```java
@ExceptionHandler(ConstraintViolationException.class)
public ResponseEntity<ErrorResponse> handleConstraint(ConstraintViolationException e) {
    List<FieldError> errors = e.getConstraintViolations().stream()
        .map(v -> new FieldError(v.getPropertyPath().toString(), v.getMessage(), v.getInvalidValue()))
        .toList();
    return ResponseEntity.badRequest()
        .body(ErrorResponse.of("VALIDATION_ERROR", "입력값이 올바르지 않습니다", errors));
}
```

## 예외 처리

### 통합 에러 응답 구조

```java
public record ErrorResponse(
    String code,
    String message,
    List<FieldError> errors,
    LocalDateTime timestamp
) {
    public record FieldError(String field, String message, Object rejectedValue) {}

    public static ErrorResponse of(String code, String message) {
        return new ErrorResponse(code, message, List.of(), LocalDateTime.now());
    }

    public static ErrorResponse of(String code, String message, List<FieldError> errors) {
        return new ErrorResponse(code, message, errors, LocalDateTime.now());
    }
}
```

### Global Exception Handler

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        List<ErrorResponse.FieldError> fieldErrors = e.getBindingResult()
            .getFieldErrors().stream()
            .map(error -> new ErrorResponse.FieldError(
                error.getField(),
                error.getDefaultMessage(),
                error.getRejectedValue()))
            .toList();

        return ResponseEntity.badRequest()
            .body(ErrorResponse.of("VALIDATION_ERROR", "입력값이 올바르지 않습니다", fieldErrors));
    }

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException e) {
        return ResponseEntity.status(e.getStatus())
            .body(ErrorResponse.of(e.getCode(), e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception e) {
        log.error("Unexpected error", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorResponse.of("INTERNAL_ERROR", "서버 내부 오류가 발생했습니다"));
    }
}
```

### 예외 처리 우선순위

Spring은 예외에 대한 핸들러를 다음 순서로 찾는다.

1. 같은 Controller 안의 `@ExceptionHandler` (지역 핸들러)
2. `@ControllerAdvice` 안의 `@ExceptionHandler` (전역 핸들러)
3. `@ExceptionHandler` 안에서 가장 구체적인 타입 매칭 (`IllegalArgumentException` < `RuntimeException` < `Exception`)

여기서 함정은 `@ControllerAdvice`가 여러 개 있을 때 순서가 보장되지 않는다는 점이다. `@Order(Ordered.HIGHEST_PRECEDENCE)`를 명시해야 의도대로 동작한다.

```java
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class SecurityExceptionHandler {
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handle(AccessDeniedException e) { ... }
}

@RestControllerAdvice
@Order(Ordered.LOWEST_PRECEDENCE)
public class GlobalExceptionHandler { ... }
```

### @ControllerAdvice basePackages 분리

API와 관리자 페이지의 응답 포맷이 다르거나, V1과 V2의 에러 구조가 다른 경우가 있다. `basePackages`로 적용 범위를 분리한다.

```java
@RestControllerAdvice(basePackages = "com.app.api.v1")
public class V1ExceptionHandler { ... }

@RestControllerAdvice(basePackages = "com.app.api.v2")
public class V2ExceptionHandler { ... }

@RestControllerAdvice(annotations = AdminController.class)
public class AdminExceptionHandler { ... }
```

`basePackages` 외에 `assignableTypes`, `annotations`로도 범위를 좁힐 수 있다. 무분별하게 전역 핸들러를 늘리는 대신, 책임 단위로 쪼개는 편이 운영하기 편하다.

### 커스텀 Exception 계층

```java
@Getter
public class BusinessException extends RuntimeException {
    private final String code;
    private final HttpStatus status;

    public BusinessException(String code, String message, HttpStatus status) {
        super(message);
        this.code = code;
        this.status = status;
    }
}

public class ResourceNotFoundException extends BusinessException {
    public ResourceNotFoundException(String resource, Long id) {
        super("NOT_FOUND",
              String.format("%s(id=%d)를 찾을 수 없습니다", resource, id),
              HttpStatus.NOT_FOUND);
    }
}

public class DuplicateEmailException extends BusinessException {
    public DuplicateEmailException(String email) {
        super("DUPLICATE_EMAIL",
              String.format("이미 사용 중인 이메일입니다: %s", email),
              HttpStatus.CONFLICT);
    }
}
```

## PUT vs PATCH 실무 구현

PUT은 리소스 전체 교체, PATCH는 부분 수정이다. 정의는 단순하지만 구현 방식이 갈린다.

### PUT 구현

PUT은 클라이언트가 보내지 않은 필드를 `null`로 처리해야 한다. 즉 모든 필드를 받아서 그대로 덮어쓴다.

```java
@PutMapping("/{id}")
public UserResponse update(@PathVariable Long id, @Valid @RequestBody UpdateUserRequest req) {
    User user = userRepository.findById(id).orElseThrow(...);
    user.update(req.email(), req.name(), req.role());  // 모든 필드 갱신
    return UserResponse.from(user);
}
```

### PATCH 구현 1: 부분 DTO 방식

가장 흔한 방식이다. DTO 필드를 모두 nullable로 두고, null이 아닌 필드만 반영한다.

```java
public record PatchUserRequest(String email, String name, String role) {}

@PatchMapping("/{id}")
public UserResponse patch(@PathVariable Long id, @RequestBody PatchUserRequest req) {
    User user = userRepository.findById(id).orElseThrow(...);
    if (req.email() != null) user.updateEmail(req.email());
    if (req.name() != null)  user.updateName(req.name());
    if (req.role() != null)  user.updateRole(req.role());
    return UserResponse.from(user);
}
```

문제는 "필드를 명시적으로 null로 보내고 싶다"와 "필드를 안 보냈다"를 구분하지 못한다는 점이다. JSON `{"email": null}`과 `{}` 둘 다 `email = null`로 들어온다.

### PATCH 구현 2: JsonPatch (RFC 6902)

명시적 작업 목록을 본문에 담는다. 표현력이 가장 강하지만 클라이언트도 같은 표준을 알아야 한다.

```
Content-Type: application/json-patch+json

[
  { "op": "replace", "path": "/email", "value": "new@example.com" },
  { "op": "remove",  "path": "/role" }
]
```

```java
// 의존성: com.github.java-json-tools:json-patch
@PatchMapping(value = "/{id}", consumes = "application/json-patch+json")
public UserResponse patch(@PathVariable Long id, @RequestBody JsonPatch patch)
        throws JsonPatchException, JsonProcessingException {
    User user = userRepository.findById(id).orElseThrow(...);
    JsonNode patched = patch.apply(objectMapper.valueToTree(user));
    User updated = objectMapper.treeToValue(patched, User.class);
    userRepository.save(updated);
    return UserResponse.from(updated);
}
```

### PATCH 구현 3: JsonMergePatch (RFC 7396)

JSON 본문을 그대로 머지한다. JsonPatch보다 직관적이지만 "필드를 null로 만든다"는 표현이 모호하다 (RFC상 null은 삭제로 해석).

```java
@PatchMapping(value = "/{id}", consumes = "application/merge-patch+json")
public UserResponse patch(@PathVariable Long id, @RequestBody JsonMergePatch mergePatch)
        throws JsonPatchException, JsonProcessingException {
    User user = userRepository.findById(id).orElseThrow(...);
    JsonNode patched = mergePatch.apply(objectMapper.valueToTree(user));
    User updated = objectMapper.treeToValue(patched, User.class);
    userRepository.save(updated);
    return UserResponse.from(updated);
}
```

실무에서는 부분 DTO 방식이 가장 널리 쓰인다. JsonPatch/MergePatch는 API가 외부 표준을 따라야 하거나 클라이언트가 다양한 경우에 도입한다.

## 페이징 응답과 PagedModel

`Page<T>`를 그대로 응답으로 반환하면 다음 경고가 나온다.

```
Serializing PageImpl instances as-is is not supported, meaning that there is
no guarantee about the stability of the resulting JSON structure!
```

Spring Data 3.3부터 표시되는 경고로, `PageImpl`의 직렬화 구조가 향후 바뀔 수 있어 직접 노출하지 말라는 뜻이다. 기존 응답 구조는 다음과 같다.

```json
{
  "content": [...],
  "pageable": { ... },
  "totalElements": 100,
  "totalPages": 5,
  "number": 0,
  "size": 20,
  "sort": { ... }
}
```

해결책은 두 가지다.

### 직접 응답 DTO 만들기

가장 안전하다. 응답 구조를 완전히 통제할 수 있다.

```java
public record PageResponse<T>(
    List<T> content,
    int page,
    int size,
    long totalElements,
    int totalPages,
    boolean hasNext
) {
    public static <T> PageResponse<T> from(Page<T> page) {
        return new PageResponse<>(
            page.getContent(),
            page.getNumber(),
            page.getSize(),
            page.getTotalElements(),
            page.getTotalPages(),
            page.hasNext()
        );
    }
}
```

### Spring HATEOAS의 PagedModel

REST 표준에 가까운 응답이 필요하면 `PagedModel`을 쓴다. 의존성에 `spring-boot-starter-hateoas`를 추가한다.

```java
@GetMapping
public PagedModel<UserResponse> list(Pageable pageable, PagedResourcesAssembler<User> assembler) {
    Page<User> page = userRepository.findAll(pageable);
    return assembler.toModel(page, UserResponse::from);
}
```

응답에 `_links.self`, `_links.next` 같은 링크가 포함되어 페이지 이동 URL을 클라이언트가 만들지 않아도 된다. 다만 응답 포맷이 HATEOAS 컨벤션을 따르므로 클라이언트와 합의가 필요하다.

설정으로 자동 변환을 켤 수도 있다 (Spring Data 3.3+).

```yaml
spring:
  data:
    web:
      pageable:
        page-parameter: page
        size-parameter: size
```

## 자주 만나는 문제 디버깅

### 415 Unsupported Media Type

`@RequestBody` 메서드에 요청을 보냈는데 415가 떨어진다. 원인은 다음 중 하나다.

1. **요청 헤더에 `Content-Type`이 없음** — curl에서 `-H "Content-Type: application/json"` 누락
2. **`consumes` 매핑 불일치** — `@PostMapping(consumes = "application/xml")`인데 JSON을 보냄
3. **Jackson 의존성 누락** — `spring-boot-starter-web`을 빼고 `spring-web`만 받았을 때
4. **본문이 비어있는데 `@RequestBody required = true`** — DELETE/GET 등에서 자주 발생

디버그할 때는 다음을 확인한다.

```java
// 1. 어떤 컨버터가 등록됐는지 확인
@Bean
public CommandLineRunner converterPrinter(RequestMappingHandlerAdapter adapter) {
    return args -> adapter.getMessageConverters()
        .forEach(c -> System.out.println(c.getClass().getName() + " " + c.getSupportedMediaTypes()));
}

// 2. 요청 헤더 로깅 (CommonsRequestLoggingFilter)
@Bean
public CommonsRequestLoggingFilter loggingFilter() {
    CommonsRequestLoggingFilter filter = new CommonsRequestLoggingFilter();
    filter.setIncludeHeaders(true);
    filter.setIncludePayload(true);
    filter.setMaxPayloadLength(2000);
    return filter;
}
```

### CORS 프리플라이트 실패

브라우저는 단순 요청이 아닌 경우 (커스텀 헤더, JSON Content-Type, PUT/DELETE 등) `OPTIONS` 프리플라이트를 먼저 보낸다. 여기서 막히면 본 요청이 가지 못한다.

```java
@Configuration
public class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOriginPatterns("https://*.example.com")  // 와일드카드는 Patterns 사용
            .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600);
    }
}
```

흔한 실패 원인:

- `allowCredentials(true)`인데 `allowedOrigins("*")` — 두 조합은 금지. `allowedOriginPatterns`로 바꿔야 한다.
- Spring Security를 쓰는데 `http.cors()` 설정 누락 — `CorsFilter`가 Security 체인을 통과 못 한다.
- 프리플라이트가 인증 필터에 막힘 — `OPTIONS` 요청은 인증 헤더를 보내지 않는다. Security에서 `permitAll()` 처리해야 한다.

### JSON 역직렬화 실패 디버깅

`HttpMessageNotReadableException`이 던져지는 경우다. 메시지를 들여다보면 원인이 보인다.

| 메시지 패턴 | 원인 |
|------------|-----|
| `Cannot construct instance ... no Creators` | record 또는 생성자가 없는 클래스를 역직렬화하려 함 |
| `Unrecognized field "xxx"` | DTO에 없는 필드가 들어옴. `FAIL_ON_UNKNOWN_PROPERTIES` 비활성화 |
| `Cannot deserialize value of type LocalDateTime` | `JavaTimeModule` 미등록 또는 포맷 불일치 |
| `Cannot deserialize from Object value (no delegate- or property-based Creator)` | enum 역직렬화에서 잘못된 구조 |
| `Required request body is missing` | `@RequestBody`인데 본문이 비어있음 |

디버깅 팁: `@RestControllerAdvice`에서 `HttpMessageNotReadableException`을 잡아 `e.getMessage()`를 로그로 남기면 원인이 거의 한 줄에 나온다.

```java
@ExceptionHandler(HttpMessageNotReadableException.class)
public ResponseEntity<ErrorResponse> handleNotReadable(HttpMessageNotReadableException e) {
    log.warn("JSON 파싱 실패: {}", e.getMessage());
    return ResponseEntity.badRequest()
        .body(ErrorResponse.of("MALFORMED_JSON", "요청 본문 형식이 올바르지 않습니다"));
}
```

## API 버전 관리

```java
// URL 경로 기반 (가장 널리 쓰임)
@RequestMapping("/api/v1/users")
public class UserV1Controller { }

@RequestMapping("/api/v2/users")
public class UserV2Controller { }

// 헤더 기반
@GetMapping(value = "/users", headers = "X-API-VERSION=1")
public List<UserV1Response> getUsersV1() { }
```

| 방식 | 장점 | 단점 |
|------|------|------|
| URL 경로 (`/api/v1/`) | 직관적, 브라우저 테스트 쉬움 | URL이 길어짐 |
| 헤더 | URL이 깔끔 | 테스트 불편, 캐싱 키 관리 필요 |
| 쿼리 파라미터 (`?version=1`) | 간단 | CDN 캐싱이 복잡 |

URL 경로 방식이 운영 부담이 가장 적다. 클라이언트가 어느 버전을 호출 중인지 액세스 로그만 봐도 안다.

## 운영에서 챙기는 것들

### 응답 압축

```yaml
server:
  compression:
    enabled: true
    mime-types: application/json,text/html
    min-response-size: 1024
```

작은 응답까지 gzip하면 오히려 CPU만 쓰므로 1KB 미만은 제외한다.

### 캐시 헤더

```java
@GetMapping("/{id}")
public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
    UserResponse response = userService.getUser(id);
    return ResponseEntity.ok()
        .cacheControl(CacheControl.maxAge(30, TimeUnit.MINUTES))
        .body(response);
}
```

ETag 기반 조건부 응답이 필요하면 `ShallowEtagHeaderFilter`를 등록한다.

### 요청 로깅 주의

`CommonsRequestLoggingFilter`로 본문을 로그에 찍을 때, 비밀번호나 토큰이 그대로 나가지 않는지 확인한다. 마스킹이 필요하면 직접 Filter를 만들어 써야 한다.

## 참고

- [Spring MVC 공식 문서](https://docs.spring.io/spring-framework/reference/web/webmvc.html)
- [Bean Validation 스펙](https://beanvalidation.org/)
- [HTTP 상태 코드 (MDN)](https://developer.mozilla.org/ko/docs/Web/HTTP/Status)
- [RFC 6902 - JSON Patch](https://datatracker.ietf.org/doc/html/rfc6902)
- [RFC 7396 - JSON Merge Patch](https://datatracker.ietf.org/doc/html/rfc7396)
