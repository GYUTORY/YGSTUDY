---
title: Spring MVC & REST API 설계 가이드
tags: [framework, java, spring, spring-mvc, rest-api, controller, exception-handling, validation]
updated: 2026-03-01
---

# Spring MVC & REST API 설계 가이드

## 배경

Spring MVC는 Model-View-Controller 패턴 기반의 웹 프레임워크이며, REST API 개발에 가장 널리 사용된다. 요청 처리, 응답 변환, 예외 처리, 유효성 검증을 체계적으로 관리할 수 있다.

### 요청 처리 흐름

```
HTTP 요청 → DispatcherServlet
               │
               ├─ HandlerMapping (어떤 Controller?)
               ├─ HandlerAdapter (메서드 실행)
               ├─ ArgumentResolver (파라미터 변환)
               ├─ Controller 메서드 실행
               ├─ ReturnValueHandler (응답 변환)
               └─ HttpMessageConverter (JSON 직렬화)
               │
           HTTP 응답
```

### 핵심 어노테이션 요약

| 어노테이션 | 위치 | 역할 |
|-----------|------|------|
| `@RestController` | 클래스 | `@Controller` + `@ResponseBody` |
| `@RequestMapping` | 클래스/메서드 | URL 매핑의 공통 경로 |
| `@GetMapping` | 메서드 | GET 요청 매핑 |
| `@PostMapping` | 메서드 | POST 요청 매핑 |
| `@PathVariable` | 파라미터 | URL 경로 변수 바인딩 |
| `@RequestBody` | 파라미터 | JSON → 객체 변환 |
| `@RequestParam` | 파라미터 | 쿼리 파라미터 바인딩 |
| `@Valid` | 파라미터 | 유효성 검증 실행 |

## 핵심

### 1. Controller 설계

#### RESTful Controller 기본 구조

```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    // 목록 조회 (페이징)
    @GetMapping
    public Page<UserResponse> getUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return userService.getUsers(PageRequest.of(page, size));
    }

    // 단건 조회
    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) {
        return userService.getUser(id);
    }

    // 생성
    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Valid @RequestBody CreateUserRequest request) {
        UserResponse response = userService.createUser(request);
        URI location = URI.create("/api/v1/users/" + response.getId());
        return ResponseEntity.created(location).body(response);
    }

    // 수정
    @PutMapping("/{id}")
    public UserResponse updateUser(
            @PathVariable Long id,
            @Valid @RequestBody UpdateUserRequest request) {
        return userService.updateUser(id, request);
    }

    // 삭제
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }
}
```

#### HTTP 메서드와 응답 코드

| 메서드 | 용도 | 성공 코드 | 응답 본문 |
|--------|------|----------|----------|
| `GET` | 조회 | 200 OK | 데이터 |
| `POST` | 생성 | 201 Created | 생성된 데이터 + Location 헤더 |
| `PUT` | 전체 수정 | 200 OK | 수정된 데이터 |
| `PATCH` | 부분 수정 | 200 OK | 수정된 데이터 |
| `DELETE` | 삭제 | 204 No Content | 없음 |

### 2. Request/Response DTO 패턴

Entity를 직접 노출하지 않고 DTO를 사용하는 것이 원칙이다.

```java
// 요청 DTO
public record CreateUserRequest(
    @NotBlank(message = "이메일은 필수입니다")
    @Email(message = "올바른 이메일 형식이 아닙니다")
    String email,

    @NotBlank(message = "비밀번호는 필수입니다")
    @Size(min = 8, max = 20, message = "비밀번호는 8~20자입니다")
    String password,

    @NotBlank(message = "이름은 필수입니다")
    @Size(min = 2, max = 50)
    String name
) {}

// 응답 DTO
public record UserResponse(
    Long id,
    String email,
    String name,
    String role,
    LocalDateTime createdAt
) {
    public static UserResponse from(User user) {
        return new UserResponse(
            user.getId(),
            user.getEmail(),
            user.getName(),
            user.getRole().name(),
            user.getCreatedAt()
        );
    }
}
```

📌 **Java 16+ record** 사용을 권장한다. 불변 객체이며 보일러플레이트가 최소화된다.

### 3. 유효성 검증 (Validation)

#### Bean Validation 어노테이션

| 어노테이션 | 용도 | 예시 |
|-----------|------|------|
| `@NotNull` | null 불가 | 객체 필드 |
| `@NotBlank` | null, "", " " 불가 | 문자열 |
| `@NotEmpty` | null, "" 불가 | 문자열, 컬렉션 |
| `@Size` | 길이/크기 제한 | `@Size(min=2, max=50)` |
| `@Min` / `@Max` | 숫자 범위 | `@Min(0) @Max(100)` |
| `@Email` | 이메일 형식 | `@Email` |
| `@Pattern` | 정규식 매칭 | `@Pattern(regexp = "^01[016789]\\d{7,8}$")` |
| `@Past` / `@Future` | 날짜 제약 | 생년월일, 예약일 |

#### 커스텀 Validator

```java
// 커스텀 어노테이션
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = PhoneNumberValidator.class)
public @interface PhoneNumber {
    String message() default "올바른 전화번호 형식이 아닙니다";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

// Validator 구현
public class PhoneNumberValidator implements ConstraintValidator<PhoneNumber, String> {
    private static final Pattern PATTERN = Pattern.compile("^01[016789]\\d{7,8}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) return true;  // @NotBlank와 조합
        return PATTERN.matcher(value).matches();
    }
}

// 사용
public record CreateUserRequest(
    @NotBlank String name,
    @PhoneNumber String phone
) {}
```

### 4. 예외 처리 (Exception Handling)

#### 통합 에러 응답 구조

```java
// 에러 응답 DTO
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

#### Global Exception Handler

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    // 유효성 검증 실패 (400)
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(
            MethodArgumentNotValidException e) {
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

    // 리소스 없음 (404)
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(ErrorResponse.of("NOT_FOUND", e.getMessage()));
    }

    // 비즈니스 로직 에러 (409)
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException e) {
        return ResponseEntity.status(e.getStatus())
            .body(ErrorResponse.of(e.getCode(), e.getMessage()));
    }

    // 서버 에러 (500)
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception e) {
        log.error("Unexpected error", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorResponse.of("INTERNAL_ERROR", "서버 내부 오류가 발생했습니다"));
    }
}
```

#### 커스텀 Exception 계층

```java
// 비즈니스 예외 기반 클래스
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

// 구체적인 예외
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

### 5. 응답 포맷 표준화

#### API 응답 Envelope (선택)

```java
// 팀에 따라 Envelope 패턴을 사용하기도 한다
public record ApiResponse<T>(
    boolean success,
    T data,
    ErrorResponse error
) {
    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null);
    }

    public static <T> ApiResponse<T> error(ErrorResponse error) {
        return new ApiResponse<>(false, null, error);
    }
}
```

📌 **참고**: Envelope 패턴 없이 성공 시 데이터만 반환하고, 에러 시 ErrorResponse를 반환하는 방식이 더 RESTful하다. HTTP 상태 코드로 성공/실패를 구분하는 것이 표준이다.

### 6. API 버전 관리

```java
// URL 경로 기반 (가장 보편적)
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
| **URL 경로** (`/api/v1/`) | 직관적, 브라우저 테스트 쉬움 | URL이 길어짐 |
| **헤더** | URL 깔끔 | 테스트 불편 |
| **쿼리 파라미터** (`?version=1`) | 간단 | 캐싱 복잡 |

## 예시

### 1. 주문 API 전체 구현

```java
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(
            @CurrentUser UserDetails user,
            @Valid @RequestBody CreateOrderRequest request) {
        OrderResponse response = orderService.createOrder(user.getUsername(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping
    public Page<OrderResponse> getMyOrders(
            @CurrentUser UserDetails user,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return orderService.getOrders(user.getUsername(), PageRequest.of(page, size));
    }

    @GetMapping("/{orderId}")
    public OrderResponse getOrder(
            @CurrentUser UserDetails user,
            @PathVariable Long orderId) {
        return orderService.getOrder(user.getUsername(), orderId);
    }

    @PatchMapping("/{orderId}/cancel")
    public OrderResponse cancelOrder(
            @CurrentUser UserDetails user,
            @PathVariable Long orderId) {
        return orderService.cancelOrder(user.getUsername(), orderId);
    }
}
```

### 2. 파일 업로드

```java
@PostMapping(value = "/profile/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
public UserResponse uploadProfileImage(
        @CurrentUser UserDetails user,
        @RequestPart("file") MultipartFile file) {

    if (file.getSize() > 5 * 1024 * 1024) {   // 5MB 제한
        throw new BusinessException("FILE_TOO_LARGE", "파일 크기는 5MB 이하여야 합니다",
                                     HttpStatus.BAD_REQUEST);
    }
    return userService.updateProfileImage(user.getUsername(), file);
}
```

## 운영 팁

### REST API 설계 체크리스트

| 항목 | 규칙 | 예시 |
|------|------|------|
| **URL** | 명사 복수형, 소문자, 하이픈 | `/api/v1/order-items` |
| **HTTP 메서드** | 동사 역할은 메서드로 | `DELETE /users/1` (O) `/deleteUser?id=1` (X) |
| **상태 코드** | 의미에 맞는 코드 사용 | 201, 204, 400, 404, 409 |
| **에러 응답** | 일관된 구조 | `{ code, message, errors }` |
| **페이징** | 큰 목록은 반드시 페이징 | `?page=0&size=20` |
| **필터링** | 쿼리 파라미터 사용 | `?status=ACTIVE&sort=createdAt,desc` |
| **HATEOAS** | 필요 시 링크 포함 | `_links: { self, next }` |

### 성능 팁

```java
// 응답 압축 활성화
// application.yml
server:
  compression:
    enabled: true
    mime-types: application/json,text/html
    min-response-size: 1024
```

```java
// 캐시 헤더 설정
@GetMapping("/{id}")
public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
    UserResponse response = userService.getUser(id);
    return ResponseEntity.ok()
        .cacheControl(CacheControl.maxAge(30, TimeUnit.MINUTES))
        .body(response);
}
```

## 참고

- [Spring MVC 공식 문서](https://docs.spring.io/spring-framework/reference/web/webmvc.html)
- [REST API 설계 원칙](../../Framework/Node/API/API_설계_원칙.md)
- [Bean Validation 스펙](https://beanvalidation.org/)
- [HTTP 상태 코드](https://developer.mozilla.org/ko/docs/Web/HTTP/Status)
