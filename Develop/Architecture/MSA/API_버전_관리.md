---
title: API 버전 관리
tags: [backend, msa, api, versioning, gateway]
updated: 2026-04-01
---

# API 버전 관리

## 개요

MSA 환경에서 API 변경은 일상이다. 서비스 하나가 바뀔 때 해당 API를 호출하는 클라이언트가 수십 개일 수 있고, 모바일 앱처럼 강제 업데이트가 어려운 클라이언트도 있다. API를 바꿨는데 구버전 클라이언트가 깨지면 장애다.

API 버전 관리는 기존 클라이언트를 깨뜨리지 않으면서 API를 변경하는 방법이다. 버전을 어디에 명시할지, 스키마가 바뀌면 어떻게 대응할지, 언제 구버전을 폐기할지를 다룬다.

---

## 버전 관리 방식 비교

API 버전을 명시하는 방식은 크게 세 가지가 있다.

### URL Path 방식

URL 경로에 버전 번호를 넣는 방식이다.

```
GET /api/v1/orders/123
GET /api/v2/orders/123
```

가장 직관적이고 널리 사용된다. 브라우저에서 바로 확인 가능하고, 로그에서 어떤 버전으로 호출했는지 바로 보인다.

```java
@RestController
@RequestMapping("/api/v1/orders")
public class OrderV1Controller {

    @GetMapping("/{id}")
    public OrderV1Response getOrder(@PathVariable Long id) {
        Order order = orderService.findById(id);
        return OrderV1Response.from(order);
    }
}

@RestController
@RequestMapping("/api/v2/orders")
public class OrderV2Controller {

    @GetMapping("/{id}")
    public OrderV2Response getOrder(@PathVariable Long id) {
        Order order = orderService.findById(id);
        return OrderV2Response.from(order);
    }
}
```

단점은 버전이 올라갈 때마다 컨트롤러가 늘어난다는 점이다. v1과 v2의 로직이 거의 같은데 응답 형식만 다른 경우에도 별도 컨트롤러를 만들게 된다. 서비스가 10개이고 각각 v1, v2를 유지하면 컨트롤러가 20개다.

실무에서 많이 쓰이는 이유는 디버깅이 쉽기 때문이다. 로그에 `/api/v1/orders`가 찍히면 어떤 버전인지 바로 안다. API Gateway에서 라우팅할 때도 URL 패턴 매칭만 하면 돼서 설정이 단순하다.

### Custom Header 방식

HTTP 헤더에 버전 정보를 넣는 방식이다.

```
GET /api/orders/123
X-API-Version: 1

GET /api/orders/123
X-API-Version: 2
```

URL이 깔끔하게 유지된다. REST 원칙에 더 가깝다는 의견이 있다. 같은 리소스를 가리키는 URL이 하나니까.

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @GetMapping("/{id}")
    public ResponseEntity<?> getOrder(
            @PathVariable Long id,
            @RequestHeader(value = "X-API-Version", defaultValue = "1") int version) {

        Order order = orderService.findById(id);

        if (version == 2) {
            return ResponseEntity.ok(OrderV2Response.from(order));
        }
        return ResponseEntity.ok(OrderV1Response.from(order));
    }
}
```

문제는 헤더를 빠뜨리는 클라이언트가 많다는 점이다. 프론트엔드 개발자가 Axios 인터셉터에 헤더를 넣어놓고 잊어버리면, 나중에 다른 API 호출할 때 헤더가 빠진다. `defaultValue`를 설정하지 않으면 500 에러가 난다.

브라우저에서 직접 테스트할 때 헤더를 넣기 번거롭고, Swagger 문서에서 버전 전환이 직관적이지 않다.

### Content-Type(Accept Header) 방식

`Accept` 헤더에 미디어 타입을 지정하는 방식이다. Content Negotiation이라고도 부른다.

```
GET /api/orders/123
Accept: application/vnd.mycompany.order.v1+json

GET /api/orders/123
Accept: application/vnd.mycompany.order.v2+json
```

GitHub API가 이 방식을 쓴다. HTTP 표준에 가장 부합하고, 같은 리소스에 대해 다양한 표현을 제공한다는 REST 원래 의도와 맞는다.

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @GetMapping(value = "/{id}", produces = "application/vnd.mycompany.order.v1+json")
    public OrderV1Response getOrderV1(@PathVariable Long id) {
        Order order = orderService.findById(id);
        return OrderV1Response.from(order);
    }

    @GetMapping(value = "/{id}", produces = "application/vnd.mycompany.order.v2+json")
    public OrderV2Response getOrderV2(@PathVariable Long id) {
        Order order = orderService.findById(id);
        return OrderV2Response.from(order);
    }
}
```

현실적인 문제가 크다. 프론트엔드 개발자가 `application/vnd.mycompany.order.v2+json`을 매번 타이핑하는 건 실수를 유발한다. API 클라이언트 라이브러리에서 Accept 헤더를 자동으로 `application/json`으로 설정하는 경우가 있어서, 의도치 않게 버전 매칭이 안 되는 경우가 생긴다.

### 방식별 비교

| 기준 | URL Path | Custom Header | Content-Type |
|------|----------|---------------|--------------|
| 직관성 | 높음 | 보통 | 낮음 |
| 디버깅 | 로그에서 바로 확인 | 헤더 로깅 필요 | 헤더 로깅 필요 |
| Gateway 라우팅 | URL 매칭으로 단순 | 헤더 기반 라우팅 필요 | 헤더 파싱 필요 |
| REST 원칙 준수 | 낮음 | 보통 | 높음 |
| 클라이언트 실수 가능성 | 낮음 | 헤더 누락 | 미디어 타입 오타 |
| 캐싱 | URL별 캐싱 용이 | Vary 헤더 필요 | Vary 헤더 필요 |

대부분의 팀에서 URL Path 방식을 쓴다. 디버깅과 운영 편의성이 다른 장점을 압도한다. REST 순수주의자가 아니라면 URL Path를 기본으로 쓰고, 특별한 이유가 있을 때만 다른 방식을 고려한다.

---

## 하위 호환성 유지

버전을 올리지 않고 기존 API를 수정하려면 하위 호환성을 지켜야 한다. 하위 호환성이 깨지면 구버전 클라이언트가 동작하지 않는다.

### 하위 호환이 되는 변경

**필드 추가**는 안전하다. 응답에 새 필드를 추가해도 기존 클라이언트는 모르는 필드를 무시한다. JSON 파서가 알 수 없는 필드를 만나면 그냥 넘어간다.

```json
// v1 응답
{
  "orderId": 123,
  "amount": 50000,
  "status": "PAID"
}

// 필드 추가 후 (하위 호환됨)
{
  "orderId": 123,
  "amount": 50000,
  "status": "PAID",
  "deliveryDate": "2026-04-05"
}
```

**선택적 요청 파라미터 추가**도 안전하다. 기존 클라이언트가 보내지 않으면 기본값을 사용하면 된다.

```java
@GetMapping("/orders")
public List<OrderResponse> getOrders(
        @RequestParam(required = false) String status,
        @RequestParam(required = false, defaultValue = "createdAt") String sortBy) {  // 새로 추가
    // 기존 클라이언트는 sortBy를 안 보내고, 기본값 createdAt 적용
}
```

**새 엔드포인트 추가**도 안전하다. 기존 엔드포인트에 영향이 없다.

### 하위 호환이 깨지는 변경

**필드 삭제나 이름 변경**은 깨진다. 클라이언트가 `userName` 필드를 읽고 있는데 `name`으로 바꾸면 클라이언트에서 null이 된다.

```json
// 변경 전
{ "userName": "홍길동" }

// 필드 이름 변경 (하위 호환 깨짐)
{ "name": "홍길동" }
```

이 경우 양쪽 다 내려주는 방법이 있다.

```json
{
  "userName": "홍길동",
  "name": "홍길동"
}
```

일정 기간 두 필드를 모두 내려주다가, 구버전 클라이언트가 충분히 사라지면 `userName`을 제거한다.

**필드 타입 변경**도 깨진다.

```json
// 변경 전: amount가 숫자
{ "amount": 50000 }

// 변경 후: amount가 객체
{ "amount": { "value": 50000, "currency": "KRW" } }
```

클라이언트가 `response.amount + 1000` 같은 코드를 쓰고 있으면 타입 에러가 난다. 이런 변경은 새 버전으로 올려야 한다.

**필수 요청 파라미터 추가**도 깨진다. 기존 클라이언트가 해당 파라미터를 보내지 않으니까 400 에러가 난다.

### Jackson에서 하위 호환을 위한 설정

Java/Spring 기준으로, 클라이언트가 보낸 JSON에 서버가 모르는 필드가 있을 때 에러가 나지 않게 설정한다.

```java
@Configuration
public class JacksonConfig {

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        // 모르는 필드가 와도 에러 안 냄
        mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        return mapper;
    }
}
```

Spring Boot에서는 `application.yml`로도 설정 가능하다.

```yaml
spring:
  jackson:
    deserialization:
      fail-on-unknown-properties: false
```

이 설정이 빠져있으면 클라이언트가 새 필드를 보낼 때 서버에서 역직렬화 에러가 발생한다. MSA에서 서비스 간 통신할 때 특히 문제가 되는데, A 서비스가 필드를 추가했는데 B 서비스의 DTO에는 해당 필드가 없으면 B 서비스가 에러를 뱉는다.

---

## 스키마 변경 시 기존 클라이언트 대응

실무에서 자주 겪는 시나리오별 대응 방법이다.

### 응답 필드 구조 변경

주소 정보를 단일 문자열에서 구조화된 객체로 바꿔야 하는 경우.

```json
// 기존
{ "address": "서울시 강남구 테헤란로 123" }

// 변경하고 싶은 형태
{
  "address": {
    "city": "서울시",
    "district": "강남구",
    "street": "테헤란로 123"
  }
}
```

방법 1: 새 필드명으로 추가하고, 기존 필드도 유지한다.

```json
{
  "address": "서울시 강남구 테헤란로 123",
  "addressDetail": {
    "city": "서울시",
    "district": "강남구",
    "street": "테헤란로 123"
  }
}
```

방법 2: 새 API 버전을 만든다. 구조가 크게 바뀌면 이 쪽이 깔끔하다.

### Enum 값 변경

주문 상태에 새 값이 추가되는 경우.

```java
// 기존: PENDING, PAID, SHIPPED, DELIVERED
// 추가: REFUND_REQUESTED, REFUNDED
public enum OrderStatus {
    PENDING, PAID, SHIPPED, DELIVERED,
    REFUND_REQUESTED, REFUNDED  // 새로 추가
}
```

Enum 값 추가는 하위 호환이 되는 것처럼 보이지만, 클라이언트 쪽에서 문제가 생길 수 있다. 클라이언트가 Enum을 파싱할 때 알 수 없는 값이 오면 에러를 내는 경우가 있다.

```java
// 클라이언트 측 - 이렇게 하면 새 Enum 값에서 에러남
OrderStatus status = OrderStatus.valueOf(response.getStatus());

// 안전한 방식 - 모르는 값은 UNKNOWN 처리
public static OrderStatus fromString(String value) {
    try {
        return OrderStatus.valueOf(value);
    } catch (IllegalArgumentException e) {
        return OrderStatus.UNKNOWN;
    }
}
```

서버 쪽에서도 Jackson 설정을 해둔다.

```java
@JsonEnumDefaultValue
UNKNOWN;  // Enum에 추가

// ObjectMapper 설정
mapper.enable(DeserializationFeature.READ_UNKNOWN_ENUM_VALUES_USING_DEFAULT_VALUE);
```

### 필수 필드가 새로 생기는 경우

기존 API에서 선택이었던 `phoneNumber`가 필수가 되어야 하는 경우. 기존 클라이언트는 이 필드를 안 보내고 있다.

바로 필수로 바꾸면 기존 클라이언트가 깨진다. 단계적으로 진행해야 한다.

1단계: 서버에서 `phoneNumber`가 없으면 기본값을 넣거나, 별도 로직으로 채운다.

```java
public Order createOrder(CreateOrderRequest request) {
    if (request.getPhoneNumber() == null) {
        // 회원 정보에서 가져오기
        String phone = memberService.getPhone(request.getMemberId());
        request.setPhoneNumber(phone);
    }
    // ...
}
```

2단계: 클라이언트에 공지하고 마이그레이션 기간을 준다. API 문서에 "이 필드는 다음 버전부터 필수입니다"라고 명시한다.

3단계: 마이그레이션 기간이 끝나면 필수로 변경한다. 또는 새 버전에서 필수로 만든다.

---

## Deprecation 절차

구버전 API를 폐기하는 과정이다. 갑자기 끊으면 장애가 나니까 단계적으로 진행한다.

### 폐기 예고

응답 헤더에 폐기 예정 정보를 넣는다. IETF RFC 8594에 정의된 `Deprecation` 헤더와 `Sunset` 헤더를 사용한다.

```java
@GetMapping("/api/v1/orders/{id}")
public ResponseEntity<OrderV1Response> getOrder(@PathVariable Long id) {
    Order order = orderService.findById(id);
    OrderV1Response response = OrderV1Response.from(order);

    return ResponseEntity.ok()
            .header("Deprecation", "true")
            .header("Sunset", "Sat, 01 Aug 2026 00:00:00 GMT")
            .header("Link", "</api/v2/orders/{id}>; rel=\"successor-version\"")
            .body(response);
}
```

- `Deprecation: true` — 이 API는 폐기 예정이다
- `Sunset` — 이 날짜 이후로 사용할 수 없다
- `Link` — 대체할 새 버전의 위치

### 모니터링 기반 폐기

폐기를 결정하기 전에 구버전 API 호출량을 모니터링해야 한다.

```java
@Aspect
@Component
public class ApiVersionMetrics {

    private final MeterRegistry meterRegistry;

    @Around("@annotation(apiVersion)")
    public Object trackVersion(ProceedingJoinPoint joinPoint, ApiVersion apiVersion) throws Throwable {
        meterRegistry.counter("api.calls",
                "version", apiVersion.value(),
                "endpoint", joinPoint.getSignature().getName()
        ).increment();
        return joinPoint.proceed();
    }
}
```

Grafana 같은 모니터링 도구에서 v1 호출량 추이를 보고, 충분히 줄어들었을 때 폐기를 진행한다.

### 폐기 단계

**1단계 — 공지 (폐기 3~6개월 전)**

- API 문서에 Deprecated 표시
- 응답 헤더에 Deprecation, Sunset 추가
- 클라이언트 팀에 직접 공지

**2단계 — 경고 (폐기 1~3개월 전)**

- 응답에 경고 메시지 추가
- 호출량 모니터링 강화
- 아직 마이그레이션하지 않은 클라이언트 팀에 개별 연락

```java
@GetMapping("/api/v1/orders/{id}")
public ResponseEntity<OrderV1Response> getOrder(@PathVariable Long id) {
    // 응답에 경고 포함
    OrderV1Response response = OrderV1Response.from(orderService.findById(id));
    response.setWarning("This API version will be removed on 2026-08-01. Please migrate to /api/v2/orders.");

    return ResponseEntity.ok()
            .header("Deprecation", "true")
            .header("Sunset", "Sat, 01 Aug 2026 00:00:00 GMT")
            .body(response);
}
```

**3단계 — 차단 (폐기일 이후)**

바로 404를 내리지 않고, 먼저 429(Too Many Requests)나 301(Redirect)로 전환하는 팀도 있다.

```java
@GetMapping("/api/v1/orders/{id}")
public ResponseEntity<Void> getOrder(@PathVariable Long id) {
    return ResponseEntity.status(HttpStatus.GONE)  // 410 Gone
            .header("Link", "</api/v2/orders/" + id + ">; rel=\"successor-version\"")
            .build();
}
```

`410 Gone`을 쓰면 "이 리소스는 영구적으로 사라졌다"는 의미다. `404 Not Found`와 다르게, 클라이언트에게 의도적인 제거임을 알려준다.

---

## Gateway에서의 버전 라우팅 처리

API Gateway가 버전별로 요청을 적절한 서비스 인스턴스로 라우팅하는 방법이다.

### URL Path 기반 라우팅

Spring Cloud Gateway 기준으로 URL에 포함된 버전 정보로 라우팅한다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-v1
          uri: lb://order-service-v1
          predicates:
            - Path=/api/v1/orders/**
          filters:
            - StripPrefix=2  # /api/v1 제거 후 전달

        - id: order-v2
          uri: lb://order-service-v2
          predicates:
            - Path=/api/v2/orders/**
          filters:
            - StripPrefix=2
```

서비스 인스턴스를 버전별로 따로 띄우는 방식이다. v1과 v2가 완전히 다른 배포 단위가 된다. 독립 배포가 가능하지만 인프라 비용이 두 배다.

### 같은 서비스에서 버전 처리

인프라 비용을 줄이려면 하나의 서비스 인스턴스에서 여러 버전을 처리한다. Gateway는 단순 라우팅만 하고, 서비스 내부에서 버전을 분기한다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/v{version}/orders/**
```

서비스 내부에서 버전별 컨트롤러를 분리하거나, 하나의 컨트롤러에서 버전을 파라미터로 받아 분기한다.

### Header 기반 라우팅

Custom Header 방식을 쓸 경우, Gateway에서 헤더 값으로 라우팅한다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-v1
          uri: lb://order-service-v1
          predicates:
            - Path=/api/orders/**
            - Header=X-API-Version, 1

        - id: order-v2
          uri: lb://order-service-v2
          predicates:
            - Path=/api/orders/**
            - Header=X-API-Version, 2

        - id: order-default
          uri: lb://order-service-v1
          predicates:
            - Path=/api/orders/**
          # 헤더가 없으면 v1로 라우팅
```

주의할 점은 라우팅 규칙의 순서다. Spring Cloud Gateway는 위에서부터 매칭하므로, 구체적인 조건(헤더 있음)을 위에, 기본 라우팅(헤더 없음)을 아래에 배치해야 한다.

### Nginx에서 버전 라우팅

Nginx를 API Gateway로 쓰는 경우.

```nginx
upstream order_v1 {
    server order-v1-service:8080;
}

upstream order_v2 {
    server order-v2-service:8080;
}

server {
    listen 80;

    # URL Path 기반
    location /api/v1/orders {
        proxy_pass http://order_v1;
    }

    location /api/v2/orders {
        proxy_pass http://order_v2;
    }

    # Header 기반
    location /api/orders {
        set $target order_v1;

        if ($http_x_api_version = "2") {
            set $target order_v2;
        }

        proxy_pass http://$target;
    }
}
```

### 카나리 배포와 버전 라우팅 결합

새 버전을 배포할 때 트래픽을 점진적으로 전환하는 방식이다. Gateway에서 가중치 기반 라우팅을 설정한다.

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-v2-canary
          uri: lb://order-service-v2
          predicates:
            - Path=/api/v2/orders/**
            - Weight=order-v2, 10  # 10% 트래픽

        - id: order-v2-stable
          uri: lb://order-service-v1
          predicates:
            - Path=/api/v2/orders/**
            - Weight=order-v2, 90  # 90% 트래픽은 아직 v1으로
```

처음에 10%만 v2로 보내고, 에러율과 응답 시간을 모니터링하면서 비율을 올린다. 문제가 생기면 다시 100% v1으로 돌린다.

---

## 실무에서 겪는 문제들

### 버전이 무한히 늘어나는 문제

"하위 호환이 깨질 때마다 버전을 올리자"는 원칙을 세워놓으면, 시간이 지나면서 v1, v2, v3, v4... 가 쌓인다. 각 버전을 유지보수해야 하니까 코드가 복잡해진다.

실무에서는 동시에 유지하는 버전을 최대 2~3개로 제한한다. 새 버전이 나오면 가장 오래된 버전의 폐기 절차를 시작한다.

### 내부 서비스 간 버전 관리

클라이언트-서버 간 버전 관리는 당연히 하는데, 내부 서비스 간에도 버전 관리가 필요한지는 팀마다 의견이 갈린다.

내부 서비스는 배포를 직접 컨트롤할 수 있으니까, 스키마가 바뀌면 호출하는 쪽도 같이 배포하는 방식이 있다. 서비스 수가 적을 때는 이 방식이 간단하다.

서비스가 많아지면 내부에서도 버전 관리를 해야 한다. 주문 서비스 API를 바꿨는데, 결제, 배송, 알림, 정산 서비스가 전부 호출하고 있으면 동시 배포가 현실적으로 어렵다. 이때는 외부 API와 마찬가지로 하위 호환성을 유지하면서 점진적으로 변경한다.

### API 문서 버전 관리

Swagger(OpenAPI)를 쓸 때 버전별 문서를 분리해야 한다.

```java
@Configuration
public class SwaggerConfig {

    @Bean
    public GroupedOpenApi v1Api() {
        return GroupedOpenApi.builder()
                .group("v1")
                .pathsToMatch("/api/v1/**")
                .build();
    }

    @Bean
    public GroupedOpenApi v2Api() {
        return GroupedOpenApi.builder()
                .group("v2")
                .pathsToMatch("/api/v2/**")
                .build();
    }
}
```

Swagger UI에서 드롭다운으로 버전을 선택할 수 있게 된다. Deprecated 엔드포인트는 `@Deprecated` 어노테이션을 달면 Swagger에서 취소선으로 표시된다.

```java
@Deprecated
@Operation(summary = "주문 조회 (v1)", deprecated = true,
           description = "이 API는 2026-08-01에 폐기됩니다. /api/v2/orders를 사용하세요.")
@GetMapping("/api/v1/orders/{id}")
public OrderV1Response getOrder(@PathVariable Long id) {
    // ...
}
```
