---
title: API Input Validation
tags: [security, api, validation, json-schema, bean-validation, file-upload, content-type]
updated: 2026-04-07
---

# API 입력값 검증

API 서버에서 가장 많이 터지는 문제 중 하나가 입력값 검증이다. 프론트엔드에서 검증했으니 괜찮겠지 하고 넘어가면 Postman이나 curl로 직접 호출하는 순간 바로 뚫린다.

입력값 검증은 반드시 서버 사이드에서 해야 한다. 프론트엔드 검증은 UX를 위한 것이지, 보안을 위한 것이 아니다.

---

## Bean Validation으로 요청 검증

Spring Boot 기준으로 `jakarta.validation` 어노테이션을 사용해서 DTO에 검증 규칙을 건다.

```java
public class CreateOrderRequest {

    @NotBlank(message = "상품 ID는 필수다")
    private String productId;

    @Min(value = 1, message = "수량은 1 이상이어야 한다")
    @Max(value = 9999, message = "수량은 9999를 넘을 수 없다")
    private int quantity;

    @Size(max = 200, message = "배송 메모는 200자 이내")
    private String deliveryNote;

    @Pattern(regexp = "^\\d{5}$", message = "우편번호 형식이 아니다")
    private String zipCode;
}
```

컨트롤러에서 `@Valid`를 빼먹으면 검증이 동작하지 않는다. 실수로 빠뜨리는 경우가 생각보다 많다.

```java
@PostMapping("/orders")
public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest request) {
    // @Valid가 없으면 검증이 아예 동작하지 않는다
    return ResponseEntity.ok(orderService.create(request));
}
```

### 검증 실패 시 응답 처리

기본 에러 응답은 클라이언트가 파싱하기 어렵다. `@RestControllerAdvice`로 통일된 형식을 만든다.

```java
@RestControllerAdvice
public class ValidationExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        List<FieldError> errors = e.getBindingResult().getFieldErrors().stream()
                .map(field -> new FieldError(field.getField(), field.getDefaultMessage()))
                .toList();

        return ResponseEntity.badRequest()
                .body(new ErrorResponse("VALIDATION_ERROR", errors));
    }
}
```

주의할 점: 검증 에러 메시지에 내부 구현 정보를 노출하면 안 된다. `"DB column 'product_id' cannot be null"` 같은 메시지가 나가는 경우를 봤다. 메시지는 항상 사용자 관점에서 작성한다.

---

## 중첩 객체 검증 누락

가장 흔하게 놓치는 부분이다. DTO 안에 다른 객체가 있을 때 `@Valid`를 안 걸면 내부 객체의 검증이 무시된다.

```java
public class CreateOrderRequest {

    @Valid  // 이게 없으면 address 내부 필드 검증이 동작하지 않는다
    @NotNull
    private AddressDto address;

    @Valid
    @Size(min = 1, message = "주문 항목은 최소 1개")
    private List<OrderItemDto> items;
}

public class AddressDto {

    @NotBlank
    private String street;

    @NotBlank
    private String city;
}

public class OrderItemDto {

    @NotBlank
    private String productId;

    @Positive
    private int quantity;
}
```

List 안의 객체에도 `@Valid`가 필요하다. `List<OrderItemDto>` 자체에 `@Valid`를 걸어야 리스트 내 각 원소에 대해 검증이 동작한다.

실무에서 이걸 놓치면 빈 `address`나 `quantity: -1`인 주문이 DB에 들어간다. 데이터 정합성이 깨지고 나중에 원인을 추적하기 어렵다.

---

## JSON Schema 기반 검증

Bean Validation이 커버하지 못하는 복잡한 구조 검증이 필요할 때 JSON Schema를 쓴다. 특히 외부 시스템에서 들어오는 webhook이나, 스키마가 동적으로 바뀌는 경우에 유용하다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["eventType", "payload"],
  "properties": {
    "eventType": {
      "type": "string",
      "enum": ["ORDER_CREATED", "ORDER_CANCELLED", "PAYMENT_COMPLETED"]
    },
    "payload": {
      "type": "object",
      "required": ["orderId"],
      "properties": {
        "orderId": {
          "type": "string",
          "minLength": 1,
          "maxLength": 50
        },
        "amount": {
          "type": "number",
          "minimum": 0,
          "exclusiveMaximum": 100000000
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

`additionalProperties: false`를 빼먹으면 스키마에 정의되지 않은 필드가 그대로 통과한다. 의도하지 않은 필드가 들어와서 로직에 영향을 주는 경우가 있다.

Java에서 JSON Schema 검증은 `networknt/json-schema-validator` 라이브러리를 많이 쓴다.

```java
// JSON Schema 검증 예시
JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);
JsonSchema schema = factory.getSchema(schemaInputStream);

Set<ValidationMessage> errors = schema.validate(jsonNode);
if (!errors.isEmpty()) {
    throw new InvalidPayloadException(errors.toString());
}
```

---

## 페이로드 크기 제한

요청 본문 크기를 제한하지 않으면 수 GB짜리 JSON을 보내는 것만으로 서버 메모리를 잡아먹을 수 있다.

### Spring Boot 설정

```yaml
# application.yml
spring:
  servlet:
    multipart:
      max-file-size: 10MB
      max-request-size: 20MB

server:
  max-http-request-header-size: 8KB
  tomcat:
    max-swallow-size: 2MB
```

JSON 요청 본문의 크기 제한은 별도로 걸어야 한다. Spring의 기본 설정으로는 JSON body 크기가 제한되지 않는다.

```java
@Component
public class RequestSizeLimitFilter extends OncePerRequestFilter {

    private static final long MAX_BODY_SIZE = 1024 * 1024; // 1MB

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        if (request.getContentLengthLong() > MAX_BODY_SIZE) {
            response.setStatus(HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE);
            response.getWriter().write("{\"error\":\"Request body too large\"}");
            return;
        }
        filterChain.doFilter(request, response);
    }
}
```

`Content-Length` 헤더를 조작하거나 아예 보내지 않는 경우도 있다. `Transfer-Encoding: chunked`로 요청이 오면 `Content-Length`가 없으므로, 실제로 읽은 바이트 수를 체크하는 래퍼를 써야 한다.

```java
public class LimitedInputStream extends InputStream {

    private final InputStream delegate;
    private final long maxBytes;
    private long bytesRead = 0;

    public LimitedInputStream(InputStream delegate, long maxBytes) {
        this.delegate = delegate;
        this.maxBytes = maxBytes;
    }

    @Override
    public int read() throws IOException {
        if (bytesRead >= maxBytes) {
            throw new PayloadTooLargeException("Request body exceeded " + maxBytes + " bytes");
        }
        int data = delegate.read();
        if (data != -1) {
            bytesRead++;
        }
        return data;
    }
}
```

---

## 타입 강제 변환 문제

JSON에서 Java 객체로 역직렬화할 때 Jackson이 암묵적으로 타입을 변환하는 경우가 있다. 이게 보안 문제로 이어진다.

### 숫자 → 문자열 변환

```json
{
  "userId": 12345
}
```

DTO에서 `userId`가 `String` 타입이면 Jackson이 `12345`를 `"12345"`로 변환한다. 의도한 동작이 아닐 수 있다.

```java
// Jackson 설정에서 암묵적 변환 차단
ObjectMapper mapper = new ObjectMapper();
mapper.configure(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES, true);
mapper.configure(MapperFeature.ALLOW_COERCION_OF_SCALARS, false);

// Spring Boot 3.x에서는 application.yml로도 설정 가능
// spring.jackson.deserialization.fail-on-null-for-primitives: true
```

### 배열에 단일 값이 오는 경우

```json
{
  "tags": "single-tag"
}
```

`ACCEPT_SINGLE_VALUE_AS_ARRAY` 옵션이 켜져 있으면 문자열 하나가 배열로 변환된다. 기본값은 꺼져 있지만, 누군가 편의상 켜놓은 경우가 있다.

```java
// 이 옵션이 켜져 있으면 "tags": "value" → "tags": ["value"]로 변환된다
// 보안 관점에서 명시적으로 꺼두는 게 낫다
mapper.configure(DeserializationFeature.ACCEPT_SINGLE_VALUE_AS_ARRAY, false);
```

### 알 수 없는 필드 처리

요청에 DTO에 정의되지 않은 필드가 오면 기본적으로 무시된다. Mass Assignment 공격의 원인이 된다.

```java
// 정의되지 않은 필드가 오면 에러를 발생시킨다
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);
```

실제로 겪은 케이스: `role` 필드가 DTO에 없는데 `{"name": "test", "role": "ADMIN"}`을 보내면 무시되니까 괜찮다고 생각할 수 있다. 하지만 나중에 누군가 DTO에 `role` 필드를 추가하는 순간 외부에서 권한을 조작할 수 있게 된다. 처음부터 알 수 없는 필드를 차단하는 게 안전하다.

---

## Content-Type 검증

`Content-Type` 헤더를 확인하지 않으면 예상치 못한 형식의 데이터가 들어온다.

### Spring에서의 Content-Type 처리

Spring MVC의 `@RequestBody`는 기본적으로 `application/json`만 처리한다. 하지만 `consumes` 속성을 명시하지 않으면 다른 Content-Type으로 요청이 왔을 때 에러 메시지가 불친절하다.

```java
// Content-Type을 명시적으로 제한한다
@PostMapping(value = "/orders", consumes = MediaType.APPLICATION_JSON_VALUE)
public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest request) {
    return ResponseEntity.ok(orderService.create(request));
}
```

### Content-Type 불일치 공격

`Content-Type: text/plain`으로 보내면서 본문은 JSON인 경우가 있다. 일부 프레임워크는 Content-Type을 무시하고 본문을 파싱하려 한다.

```java
// Content-Type 검증 필터
@Component
public class ContentTypeValidationFilter extends OncePerRequestFilter {

    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "application/json",
            "multipart/form-data"
    );

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        if ("POST".equals(request.getMethod()) || "PUT".equals(request.getMethod())) {
            String contentType = request.getContentType();
            if (contentType == null) {
                response.setStatus(HttpServletResponse.SC_UNSUPPORTED_MEDIA_TYPE);
                return;
            }

            // Content-Type에서 charset 등의 파라미터를 제거하고 비교
            String mediaType = contentType.split(";")[0].trim().toLowerCase();
            if (!ALLOWED_CONTENT_TYPES.contains(mediaType)) {
                response.setStatus(HttpServletResponse.SC_UNSUPPORTED_MEDIA_TYPE);
                return;
            }
        }
        filterChain.doFilter(request, response);
    }
}
```

---

## 파일 업로드 검증

파일 업로드는 검증할 게 많고, 하나라도 빠지면 심각한 보안 문제가 된다.

### 확장자만 검증하면 안 된다

확장자를 `.jpg`로 바꿔서 `.jsp` 파일을 올리는 건 기본적인 공격이다. 파일의 실제 내용(매직 바이트)을 확인해야 한다.

```java
public class FileValidator {

    // 허용할 파일 타입의 매직 바이트
    private static final Map<String, byte[]> MAGIC_BYTES = Map.of(
            "image/jpeg", new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF},
            "image/png", new byte[]{(byte) 0x89, 0x50, 0x4E, 0x47},
            "application/pdf", new byte[]{0x25, 0x50, 0x44, 0x46}
    );

    public void validate(MultipartFile file) {
        // 1. 파일 크기 검증
        if (file.getSize() > 10 * 1024 * 1024) {
            throw new InvalidFileException("파일 크기가 10MB를 초과한다");
        }

        // 2. 파일명 검증 - 경로 탐색 문자 차단
        String filename = file.getOriginalFilename();
        if (filename == null || filename.contains("..") || filename.contains("/") || filename.contains("\\")) {
            throw new InvalidFileException("잘못된 파일명이다");
        }

        // 3. 확장자 검증
        String extension = getExtension(filename).toLowerCase();
        Set<String> allowedExtensions = Set.of("jpg", "jpeg", "png", "pdf");
        if (!allowedExtensions.contains(extension)) {
            throw new InvalidFileException("허용되지 않는 파일 형식이다");
        }

        // 4. 매직 바이트 검증 - 실제 파일 내용 확인
        try {
            byte[] fileBytes = file.getBytes();
            String expectedContentType = file.getContentType();
            byte[] expected = MAGIC_BYTES.get(expectedContentType);

            if (expected == null) {
                throw new InvalidFileException("지원하지 않는 Content-Type이다");
            }

            for (int i = 0; i < expected.length; i++) {
                if (fileBytes[i] != expected[i]) {
                    throw new InvalidFileException("파일 내용이 확장자와 일치하지 않는다");
                }
            }
        } catch (IOException e) {
            throw new InvalidFileException("파일을 읽을 수 없다");
        }
    }

    private String getExtension(String filename) {
        int lastDot = filename.lastIndexOf('.');
        if (lastDot == -1) return "";
        return filename.substring(lastDot + 1);
    }
}
```

### 파일명 처리

업로드된 파일의 원본 파일명을 그대로 저장하면 안 된다. 파일명에 특수문자나 경로 탐색 문자가 포함될 수 있다.

```java
public String generateSafeFilename(String originalFilename) {
    String extension = getExtension(originalFilename);
    // UUID로 새 파일명을 생성하고, 확장자만 유지한다
    return UUID.randomUUID() + "." + extension;
}
```

저장 경로도 주의해야 한다. 웹 서버의 document root 아래에 저장하면 업로드한 파일이 직접 실행될 수 있다. 별도의 스토리지 경로를 사용하거나 S3 같은 외부 스토리지를 쓴다.

---

## 경로 파라미터와 쿼리 파라미터 검증

JSON 요청 본문만 검증하고, URL의 경로 파라미터나 쿼리 파라미터 검증은 빠뜨리는 경우가 많다.

### 경로 파라미터

```java
@GetMapping("/users/{userId}/orders/{orderId}")
public Order getOrder(
        @PathVariable @Pattern(regexp = "^[a-zA-Z0-9-]{1,36}$") String userId,
        @PathVariable @Positive Long orderId) {
    return orderService.getOrder(userId, orderId);
}
```

`@PathVariable`에 검증 어노테이션을 쓰려면 컨트롤러 클래스에 `@Validated`가 있어야 한다. `@Valid`가 아니라 `@Validated`다.

```java
@RestController
@Validated  // 이게 있어야 @PathVariable, @RequestParam에 대한 검증이 동작한다
public class OrderController {
    // ...
}
```

### 쿼리 파라미터

페이징 파라미터를 검증하지 않으면 `page=0&size=1000000`으로 전체 데이터를 한 번에 가져갈 수 있다.

```java
@GetMapping("/orders")
public Page<Order> listOrders(
        @RequestParam(defaultValue = "0") @Min(0) int page,
        @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
        @RequestParam(defaultValue = "createdAt") String sort) {

    // sort 파라미터는 허용된 값만 받는다
    Set<String> allowedSortFields = Set.of("createdAt", "amount", "status");
    if (!allowedSortFields.contains(sort)) {
        throw new InvalidParameterException("허용되지 않는 정렬 기준이다");
    }

    return orderService.list(PageRequest.of(page, size, Sort.by(sort).descending()));
}
```

`sort` 파라미터를 그대로 SQL에 넣으면 SQL Injection이 된다. 화이트리스트로 검증해야 한다.

---

## 문자열 입력값의 함정

문자열 검증에서 자주 놓치는 부분들이 있다.

### 공백 문자 처리

`@NotBlank`는 null과 빈 문자열, 공백만 있는 문자열을 잡아준다. 하지만 탭이나 줄바꿈 같은 제어 문자는 통과한다.

```java
// 이름 필드에 제어 문자가 들어오는 걸 막으려면 패턴을 건다
@NotBlank
@Pattern(regexp = "^[\\p{L}\\p{N}\\s]{1,50}$", message = "허용되지 않는 문자가 포함되어 있다")
private String name;
```

### Unicode 정규화

같은 글자처럼 보이지만 다른 유니코드 코드포인트인 경우가 있다. `"café"`가 NFC와 NFD로 다르게 인코딩될 수 있다. 검색이나 중복 체크에서 문제를 일으킨다.

```java
// 입력값을 NFC로 정규화한다
String normalized = java.text.Normalizer.normalize(input, java.text.Normalizer.Form.NFC);
```

### HTML/Script 태그

입력값에 `<script>alert(1)</script>` 같은 걸 넣는 건 기본적인 XSS 시도다. 저장 시점에 이스케이프하거나, 출력 시점에 이스케이프한다. 두 곳 다 하면 이중 이스케이프 문제가 생기므로 한 곳에서만 처리한다.

보통은 출력 시점에 이스케이프하는 것을 권장한다. 저장 시점에 이스케이프하면 원본 데이터가 변형되어 검색이나 다른 용도로 사용할 때 문제가 생긴다.

---

## 검증 순서

입력값 검증은 순서가 있다. 잘못된 순서로 검증하면 의미 없는 에러 메시지가 나가거나, 비즈니스 로직에서 예외가 터진다.

1. **Content-Type 확인** — 잘못된 형식의 요청은 파싱하기 전에 거부한다
2. **페이로드 크기 확인** — 파싱 전에 크기를 체크해서 메모리 낭비를 방지한다
3. **구문 검증(파싱)** — JSON이 올바른 형식인지 확인한다
4. **구조 검증** — 필수 필드 존재 여부, 타입, 길이 등을 확인한다
5. **비즈니스 규칙 검증** — 존재하는 상품인지, 재고가 있는지 등 도메인 로직 검증

Spring에서는 1~4단계가 프레임워크와 Bean Validation으로 처리되고, 5단계는 서비스 레이어에서 처리한다. 서비스 레이어 검증을 컨트롤러에 넣으면 코드가 복잡해지고, 다른 진입점(메시지 큐, 배치 등)에서 검증이 누락된다.

---

## 실무에서 자주 터지는 상황 정리

**빈 배열 vs null**: `"items": []`와 `"items": null`과 `items` 필드가 아예 없는 경우를 구분해야 한다. `@NotNull`은 null만 잡고, `@Size(min=1)`은 빈 배열을 잡는다. 필드가 아예 없으면 null로 들어온다.

**숫자 범위**: `int` 타입의 `quantity` 필드에 `2147483648`(Integer.MAX_VALUE + 1)을 보내면 Jackson에서 파싱 에러가 난다. Long으로 받아야 하는데 int로 받고 있다면, 큰 숫자가 왔을 때 오버플로우가 아니라 파싱 에러가 나는지 확인해야 한다.

**날짜 형식**: `"2026-13-01"`이나 `"2026-02-30"` 같은 잘못된 날짜를 Jackson이 어떻게 처리하는지 확인해야 한다. `lenient` 모드가 켜져 있으면 `2026-13-01`이 `2027-01-01`로 변환된다.

```java
// 날짜 필드의 lenient 모드를 끈다
@JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd", lenient = OptBoolean.FALSE)
private LocalDate orderDate;
```

**enum 값**: DTO에서 String으로 받아서 수동으로 변환하는 것보다 enum 타입으로 받는 게 낫다. 잘못된 값이 오면 Jackson이 자동으로 에러를 발생시킨다. 단, 에러 메시지가 내부 구현(enum 클래스명)을 노출할 수 있으므로 `@JsonCreator`로 커스텀 처리하는 게 좋다.

```java
public enum OrderStatus {
    PENDING, CONFIRMED, SHIPPED, DELIVERED;

    @JsonCreator
    public static OrderStatus fromString(String value) {
        try {
            return OrderStatus.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new InvalidParameterException("잘못된 주문 상태: " + value);
        }
    }
}
```
