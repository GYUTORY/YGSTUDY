---
title: API 버저닝 실무
tags: [backend, api, versioning, migration, backward-compatibility, deprecation]
updated: 2026-03-26
---

# API 버저닝 실무

## 왜 버저닝이 필요한가

API를 운영하다 보면 응답 구조를 바꾸거나 파라미터를 변경해야 할 때가 온다. 클라이언트가 하나면 그냥 같이 수정하면 되는데, 모바일 앱이 붙어 있으면 이야기가 달라진다. 앱스토어 심사에 3~5일 걸리고, 사용자가 업데이트를 안 하는 경우도 있다. 구버전 앱이 새 API를 호출했을 때 깨지면 장애다.

버저닝은 이런 상황에서 기존 클라이언트는 그대로 동작하게 두면서 새 스펙을 배포하는 방법이다.

## 방식별 비교와 실제 운영에서 겪는 문제

### URI 경로 방식 (`/api/v1/users`)

가장 많이 쓰는 방식이다. URL만 보면 어떤 버전인지 바로 알 수 있다.

```
GET /api/v1/users/1
GET /api/v2/users/1
```

**운영에서 좋은 점:**

- CDN/리버스 프록시에서 버전별 캐시 분리가 자연스럽다. Nginx에서 `/api/v1/*`과 `/api/v2/*`를 다른 upstream으로 보내는 것도 간단하다.
- 접근 로그에서 `grep /api/v1/` 한 줄이면 구버전 트래픽을 바로 파악할 수 있다.
- Swagger 문서를 버전별로 나누기 쉽다.

**운영에서 겪는 문제:**

- 컨트롤러가 버전별로 복제된다. v1, v2, v3 컨트롤러가 생기면 같은 비즈니스 로직을 호출하는 컨트롤러 클래스가 3개가 된다. 서비스 레이어에 변경이 생겼을 때 컨트롤러마다 영향 확인을 해야 한다.
- 버전마다 URL이 바뀌기 때문에 외부 연동 시 상대방에게 URL 변경을 안내해야 한다. B2B API에서 이게 꽤 번거롭다.
- API Gateway 라우팅 규칙도 버전마다 추가해야 한다.

```nginx
# Nginx에서 버전별 라우팅 — 이게 쌓이면 관리가 귀찮아진다
location /api/v1/ {
    proxy_pass http://app-v1/;
}
location /api/v2/ {
    proxy_pass http://app-v2/;
}
```

### Header 방식 (`Accept: application/vnd.myapp.v2+json`)

GitHub API가 이 방식을 쓴다. URL은 하나로 유지하고 Accept 헤더로 버전을 구분한다.

```
GET /api/users/1
Accept: application/vnd.myapp.v2+json
```

**운영에서 좋은 점:**

- URL이 변하지 않으니 외부 연동 파트너에게 URL 변경 안내를 할 필요가 없다.
- RESTful 원칙에 가장 가깝다. 같은 리소스에 대해 표현만 다른 것이므로 URI가 같은 게 맞다.

**운영에서 겪는 문제:**

- 개발자가 Postman이나 브라우저로 테스트할 때 헤더를 매번 설정해야 한다. curl로 빠르게 확인하려 해도 `-H` 플래그를 빠뜨리면 다른 버전이 응답한다.
- 클라이언트 개발자가 헤더를 빠뜨리는 경우가 실제로 빈번하다. 기본 버전 정책을 안 정해두면 장애로 이어진다.
- CDN에서 캐시 키에 Accept 헤더를 포함시켜야 하는데, Vary 헤더 설정을 잘못하면 다른 버전의 캐시가 반환되는 사고가 난다.
- 접근 로그에서 버전별 트래픽을 구분하려면 로그 포맷에 Accept 헤더를 추가해야 한다. 기본 Nginx 로그로는 보이지 않는다.

```
# CDN 캐시 사고를 방지하려면 Vary 헤더가 필수다
Vary: Accept
```

### Query Parameter 방식 (`/api/users?version=2`)

구현이 가장 단순하다. 소규모 내부 API에서 간혹 쓴다.

```
GET /api/users/1?version=2
```

**운영에서 좋은 점:**

- 구현 코드가 짧다. 파라미터 하나로 분기하면 끝이다.
- curl이나 브라우저에서 바로 테스트할 수 있다.

**운영에서 겪는 문제:**

- 버전이 늘어나면 if-else 분기가 길어진다. 3개 이상 버전이 공존하는 순간 유지보수가 어려워진다.
- CDN 캐시 키에 쿼리 파라미터가 들어가야 하는데, 일부 CDN은 쿼리 파라미터를 무시하고 캐시하도록 기본 설정되어 있다. CloudFront에서 이걸 빠뜨려서 v1 응답이 v2로 나간 경험이 있다.
- OpenAPI 스펙으로 문서화할 때 같은 엔드포인트에서 버전별로 다른 응답 스키마를 표현하기 어렵다.

### 방식 선택 기준

| 상황 | 추천 방식 |
|------|-----------|
| 외부 공개 API, B2B 연동이 많은 서비스 | URI 경로 |
| REST 순수주의, URL 변경이 어려운 구조 | Header |
| 내부 서비스 간 통신, 버전이 2개 이하 | Query Parameter |
| 모바일 앱 + 웹 프론트 동시 지원 | URI 경로 |

대부분의 경우 URI 경로 방식을 쓰게 된다. Header 방식은 팀 내 모든 개발자가 헤더 관리에 익숙해야 해서 진입 장벽이 있다.

## v1에서 v2 마이그레이션 절차

버전 전환은 코드 배포가 아니라 **운영 프로세스**다. 코드를 배포하고 끝이 아니라, 기존 클라이언트가 전부 전환될 때까지 관리해야 한다.

### 1단계: v2 엔드포인트 배포

v1을 건드리지 말고 v2를 새로 추가한다. v1은 그대로 동작해야 한다.

```java
// v2 컨트롤러를 별도로 만든다. v1 코드는 건드리지 않는다.
@RestController
@RequestMapping("/api/v2/orders")
public class OrderV2Controller {

    private final OrderService orderService;

    @GetMapping("/{id}")
    public ResponseEntity<OrderV2Response> getOrder(@PathVariable Long id) {
        Order order = orderService.findById(id);
        return ResponseEntity.ok(OrderV2Response.from(order));
    }
}
```

v1과 v2가 같은 서비스 레이어를 호출하되, 응답 DTO만 다르게 가져가는 구조가 가장 깔끔하다. 서비스 로직 자체가 달라져야 하면 서비스 메서드를 분리한다.

```java
// 서비스 레이어는 공유하고, 응답 변환만 버전별로 다르게 한다
@Service
public class OrderService {

    // v1, v2 모두 이 메서드를 호출한다
    public Order findById(Long id) {
        return orderRepository.findById(id)
            .orElseThrow(() -> new BusinessException(ErrorCode.ORDER_NOT_FOUND));
    }
}

// v1 응답: address가 문자열
public record OrderV1Response(Long id, String address, int totalAmount) {
    public static OrderV1Response from(Order order) {
        return new OrderV1Response(order.getId(), order.getFullAddress(), order.getTotalAmount());
    }
}

// v2 응답: address가 구조화된 객체
public record OrderV2Response(Long id, Address address, int totalAmount) {
    public static OrderV2Response from(Order order) {
        return new OrderV2Response(order.getId(), order.getAddress(), order.getTotalAmount());
    }
}
```

### 2단계: Deprecation 공지

v2 배포가 안정화되면 v1에 deprecation 신호를 보낸다. HTTP 표준 헤더인 `Deprecation`과 `Sunset`을 사용한다.

```java
@Component
public class ApiDeprecationFilter extends OncePerRequestFilter {

    // 버전별 sunset 날짜 관리
    private static final Map<String, String> SUNSET_DATES = Map.of(
        "/api/v1/", "Sat, 01 Nov 2026 00:00:00 GMT"
    );

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        String uri = request.getRequestURI();

        SUNSET_DATES.forEach((prefix, sunsetDate) -> {
            if (uri.startsWith(prefix)) {
                response.setHeader("Deprecation", "true");
                response.setHeader("Sunset", sunsetDate);
                // 대체 버전 URL을 알려준다
                String v2Uri = uri.replace(prefix, "/api/v2/");
                response.setHeader("Link", "<" + v2Uri + ">; rel=\"successor-version\"");
            }
        });

        filterChain.doFilter(request, response);
    }
}
```

이 헤더를 내려주면 클라이언트 쪽에서 로그로 감지할 수 있다. 다만 클라이언트가 이 헤더를 확인하지 않는 경우가 많기 때문에, 별도로 공지도 해야 한다.

공지 채널:

- API 문서(Swagger)에 v1 엔드포인트를 `@Deprecated`로 표시
- 슬랙 채널이나 메일로 전환 일정 공유
- B2B 파트너가 있으면 개별 연락 필수

```java
// Swagger에서 deprecated 표시
@Deprecated
@Operation(summary = "사용자 조회 (deprecated)", deprecated = true,
           description = "이 API는 2026-11-01에 종료된다. /api/v2/users/{id}를 사용해야 한다.")
@GetMapping("/{id}")
public ResponseEntity<UserV1Response> getUser(@PathVariable Long id) { ... }
```

### 3단계: 클라이언트별 전환 추적

v1을 제거하기 전에 누가 아직 v1을 호출하는지 파악해야 한다. API Key나 클라이언트 식별자가 있으면 클라이언트별로 추적할 수 있다.

```java
@Component
@Slf4j
public class VersionTrackingFilter extends OncePerRequestFilter {

    private final MeterRegistry meterRegistry;

    public VersionTrackingFilter(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        String uri = request.getRequestURI();
        String clientId = request.getHeader("X-Client-Id");
        if (clientId == null) {
            clientId = "unknown";
        }
        String version = extractVersion(uri);

        if (version != null) {
            // Prometheus 메트릭으로 기록
            meterRegistry.counter("api.request",
                "version", version,
                "client", clientId,
                "endpoint", normalizeUri(uri)
            ).increment();

            // v1 호출이면 경고 로그
            if ("v1".equals(version)) {
                log.warn("Deprecated API call: client={}, uri={}", clientId, uri);
            }
        }

        filterChain.doFilter(request, response);
    }

    private String extractVersion(String uri) {
        if (uri.contains("/v1/")) return "v1";
        if (uri.contains("/v2/")) return "v2";
        return null;
    }

    private String normalizeUri(String uri) {
        // /api/v1/users/123 → /api/v1/users/{id}
        return uri.replaceAll("/\\d+", "/{id}");
    }
}
```

Grafana 대시보드에서 `api.request` 메트릭을 version 라벨로 필터링하면 v1 트래픽 추이를 볼 수 있다. 특정 클라이언트가 전환을 안 하고 있으면 해당 팀에 직접 연락한다.

### 4단계: v1 종료

v1 트래픽이 0에 가까워지면 v1을 제거한다. 바로 삭제하지 말고 단계를 밟는다.

```java
// 1) v1 응답에 410 Gone을 반환하는 단계 (2주 정도 유지)
@RestController
@RequestMapping("/api/v1/**")
public class V1GoneController {

    @RequestMapping
    public ResponseEntity<ErrorResponse> gone(HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.GONE)
            .body(ErrorResponse.of(
                "API_VERSION_GONE",
                "이 API 버전은 종료되었다. /api/v2를 사용해야 한다.",
                request.getRequestURI()
            ));
    }
}
```

```
// 2) 410 응답도 제거하고 404가 나가게 놔둔다
// 3) v1 컨트롤러 코드를 삭제한다
```

전체 타임라인 예시:

```
2026-04  v2 배포, v1/v2 병행 운영 시작
2026-05  v1에 Deprecation 헤더 추가, 공지 발송
2026-08  v1 트래픽 모니터링, 미전환 클라이언트 개별 연락
2026-10  v1 트래픽 0% 확인
2026-11  v1 → 410 Gone 전환
2026-12  v1 코드 삭제
```

## 하위 호환성이 깨지는 변경 유형과 대응법

버전을 올릴지 말지 판단하는 기준은 **기존 클라이언트가 코드 변경 없이 정상 동작하는가**다.

### 버전을 올려야 하는 변경 (Breaking Change)

**응답 필드 삭제 또는 이름 변경:**

```java
// Before: v1
{ "userName": "김개발", "age": 30 }

// After: userName을 name으로 변경 — 기존 클라이언트에서 userName을 참조하면 null
{ "name": "김개발", "age": 30 }
```

대응: 필드 이름을 바꿔야 하면 v2를 만들어야 한다. v1에서는 기존 필드를 유지하고, v2에서 새 이름을 쓴다.

**응답 필드 타입 변경:**

```java
// Before: price가 정수
{ "price": 10000 }

// After: price가 문자열로 변경 — JSON.parse 후 산술 연산하는 코드가 깨진다
{ "price": "10000" }
```

**필수 파라미터 추가:**

```java
// Before: name, email만 보내면 됐음
POST /api/v1/users
{ "name": "김개발", "email": "kim@dev.com" }

// After: phoneNumber가 필수가 됨 — 기존 클라이언트에서 400 에러
POST /api/v1/users
{ "name": "김개발", "email": "kim@dev.com" }
// → 400 Bad Request: phoneNumber is required
```

대응: 새 필수 파라미터는 v2에서 추가한다. v1에서는 선택 파라미터로 두고 기본값을 넣는다.

**응답 구조 변경:**

```java
// Before: 배열 직접 반환
[{ "id": 1 }, { "id": 2 }]

// After: 객체로 래핑 — response[0]으로 접근하던 코드가 깨진다
{ "data": [{ "id": 1 }, { "id": 2 }], "total": 2 }
```

이건 흔히 겪는 실수다. 처음부터 배열을 직접 반환하지 말고 객체로 감싸서 반환하는 게 좋다. 나중에 total이나 page 같은 메타 정보를 추가할 여지를 남겨둘 수 있다.

**URL 경로 변경:**

```
Before: GET /api/v1/users/1/orders
After:  GET /api/v1/orders?userId=1
```

같은 버전 내에서 URL 구조를 바꾸면 클라이언트가 404를 만난다. URL을 바꿔야 하면 리다이렉트(301)를 걸어주거나, v2로 넘긴다.

### 버전을 올리지 않아도 되는 변경

- 선택 필드 추가: 응답에 `createdAt` 필드를 추가하는 건 괜찮다. JSON 파싱 시 모르는 필드는 무시되니까.
- 선택 파라미터 추가: `?sort=name` 같은 선택 쿼리 파라미터는 기존 요청에 영향 없다.
- 에러 메시지 문구 변경: 에러 코드가 같으면 메시지 문구는 바꿔도 된다. 다만 클라이언트가 메시지 문자열로 분기하고 있으면 문제가 되니까, 에러 코드를 기준으로 처리하도록 문서화해둬야 한다.

### 주의가 필요한 변경

**Enum 값 추가:**

```java
// 서버: status에 REFUNDED 추가
public enum OrderStatus { PENDING, COMPLETED, CANCELLED, REFUNDED }

// 클라이언트: default 케이스가 없으면 문제
switch (status) {
    case "PENDING":    // ...
    case "COMPLETED":  // ...
    case "CANCELLED":  // ...
    // REFUNDED가 오면? → 아무 처리도 안 됨
}
```

Enum 값을 추가하는 건 이론적으로 non-breaking이지만, 실제로는 클라이언트 구현에 따라 깨질 수 있다. API 문서에 "알 수 없는 enum 값이 올 수 있으니 default 처리를 해달라"고 명시해야 한다.

**null이 될 수 있는 필드:**

기존에 항상 값이 있던 필드가 null이 될 수 있도록 바뀌면, 클라이언트에서 null 체크 없이 바로 사용하던 코드가 NPE를 만날 수 있다. 이건 필드 타입은 안 바뀌지만 사실상 계약이 바뀐 거다.

## Spring에서의 버전 라우팅 구현

### 커스텀 어노테이션으로 버전 관리

컨트롤러마다 `@RequestMapping("/api/v1/...")`, `@RequestMapping("/api/v2/...")`를 반복하는 건 번거롭다. 커스텀 어노테이션으로 정리할 수 있다.

```java
@Target({ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ApiVersion {
    int[] value();
}
```

```java
public class ApiVersionRequestMappingHandlerMapping extends RequestMappingHandlerMapping {

    @Override
    protected RequestMappingInfo getMappingForMethod(Method method, Class<?> handlerType) {
        RequestMappingInfo info = super.getMappingForMethod(method, handlerType);
        if (info == null) return null;

        ApiVersion apiVersion = AnnotationUtils.findAnnotation(handlerType, ApiVersion.class);
        if (apiVersion != null) {
            // 지원하는 모든 버전에 대해 매핑 생성
            RequestMappingInfo.Builder builder = RequestMappingInfo.paths(
                Arrays.stream(apiVersion.value())
                    .mapToObj(v -> "/api/v" + v)
                    .toArray(String[]::new)
            );
            info = builder.build().combine(info);
        }
        return info;
    }
}
```

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        // 기본 핸들러 매핑 대신 커스텀 매핑 사용
    }

    @Bean
    public ApiVersionRequestMappingHandlerMapping apiVersionHandlerMapping() {
        return new ApiVersionRequestMappingHandlerMapping();
    }
}
```

```java
// 사용법: v1과 v2 모두 지원하는 컨트롤러
@RestController
@ApiVersion({1, 2})
@RequestMapping("/users")
public class UserController {

    // GET /api/v1/users/1, GET /api/v2/users/1 모두 이 메서드로 온다
    @GetMapping("/{id}")
    public ResponseEntity<?> getUser(@PathVariable Long id, HttpServletRequest request) {
        int version = extractVersion(request);
        User user = userService.findById(id);

        if (version == 1) {
            return ResponseEntity.ok(UserV1Response.from(user));
        }
        return ResponseEntity.ok(UserV2Response.from(user));
    }

    private int extractVersion(HttpServletRequest request) {
        String uri = request.getRequestURI();
        // /api/v2/users/1 → 2
        return Integer.parseInt(uri.split("/api/v")[1].split("/")[0]);
    }
}
```

이 방식은 컨트롤러 클래스를 버전별로 분리하지 않아도 된다는 장점이 있지만, 메서드 내부에서 버전 분기가 생기는 건 피할 수 없다. 응답 구조가 크게 다르면 컨트롤러 자체를 분리하는 게 낫다.

### 버전별 컨트롤러 분리 + 공통 로직 추출

실무에서 가장 많이 쓰는 패턴이다. 컨트롤러는 버전별로 분리하되, 서비스와 도메인은 공유한다.

```
src/main/java/com/example/
├── controller/
│   ├── v1/
│   │   ├── UserV1Controller.java
│   │   └── OrderV1Controller.java
│   └── v2/
│       ├── UserV2Controller.java
│       └── OrderV2Controller.java
├── dto/
│   ├── v1/
│   │   ├── UserV1Response.java
│   │   └── OrderV1Response.java
│   └── v2/
│       ├── UserV2Response.java
│       └── OrderV2Response.java
├── service/
│   ├── UserService.java        ← 버전 구분 없음
│   └── OrderService.java
└── domain/
    ├── User.java               ← 버전 구분 없음
    └── Order.java
```

서비스 레이어에 버전이 침투하면 안 된다. 서비스는 도메인 객체를 반환하고, 컨트롤러에서 버전에 맞는 DTO로 변환한다.

```java
// 서비스: 도메인 객체 반환. 버전을 모른다.
@Service
public class UserService {
    public User findById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
    }
}

// v1 컨트롤러: 도메인 → v1 DTO 변환
@RestController
@RequestMapping("/api/v1/users")
public class UserV1Controller {
    @GetMapping("/{id}")
    public ResponseEntity<UserV1Response> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(UserV1Response.from(userService.findById(id)));
    }
}

// v2 컨트롤러: 도메인 → v2 DTO 변환
@RestController
@RequestMapping("/api/v2/users")
public class UserV2Controller {
    @GetMapping("/{id}")
    public ResponseEntity<UserV2Response> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(UserV2Response.from(userService.findById(id)));
    }
}
```

## Express에서의 버전 라우팅 구현

### 라우터 분리 방식

Express에서는 라우터 파일을 버전별로 나누는 게 자연스럽다.

```
src/
├── routes/
│   ├── v1/
│   │   ├── index.js
│   │   └── users.js
│   └── v2/
│       ├── index.js
│       └── users.js
├── services/
│   └── userService.js      ← 버전 구분 없음
└── app.js
```

```javascript
// app.js
const express = require('express');
const v1Router = require('./routes/v1');
const v2Router = require('./routes/v2');

const app = express();

app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);

// v1 deprecation 미들웨어
app.use('/api/v1', (req, res, next) => {
    res.set('Deprecation', 'true');
    res.set('Sunset', 'Sat, 01 Nov 2026 00:00:00 GMT');
    const v2Path = req.originalUrl.replace('/api/v1', '/api/v2');
    res.set('Link', `<${v2Path}>; rel="successor-version"`);
    next();
});
```

```javascript
// routes/v1/users.js
const router = require('express').Router();
const userService = require('../../services/userService');

router.get('/:id', async (req, res) => {
    const user = await userService.findById(req.params.id);
    // v1: address가 문자열
    res.json({
        id: user.id,
        name: user.name,
        address: user.fullAddress
    });
});

module.exports = router;
```

```javascript
// routes/v2/users.js
const router = require('express').Router();
const userService = require('../../services/userService');

router.get('/:id', async (req, res) => {
    const user = await userService.findById(req.params.id);
    // v2: address가 객체
    res.json({
        id: user.id,
        name: user.name,
        address: {
            city: user.city,
            street: user.street,
            zipCode: user.zipCode
        }
    });
});

module.exports = router;
```

### 버전 추적 미들웨어

```javascript
// middleware/versionTracking.js
const versionTracking = (req, res, next) => {
    const match = req.originalUrl.match(/\/api\/v(\d+)\//);
    if (match) {
        const version = match[1];
        const clientId = req.headers['x-client-id'] || 'unknown';

        // 메트릭 기록 (prom-client 등)
        apiVersionCounter.inc({
            version: `v${version}`,
            client: clientId,
            method: req.method,
            path: req.route ? req.route.path : req.path
        });

        if (version === '1') {
            console.warn(`Deprecated API call: client=${clientId}, path=${req.originalUrl}`);
        }
    }
    next();
};

module.exports = versionTracking;
```

## 실무에서 자주 하는 실수

**1. 버전을 너무 자주 올린다**

작은 변경마다 버전을 올리면 v5, v6까지 금방 간다. 하위 호환이 유지되는 변경은 같은 버전에 넣어야 한다. 버전을 올릴 때는 여러 breaking change를 모아서 한 번에 올리는 게 관리가 편하다.

**2. 구버전 코드를 방치한다**

v2를 배포한 뒤 v1 코드를 계속 남겨두면 의존성 업데이트나 리팩토링할 때 두 배로 작업해야 한다. sunset 기한을 정하고 반드시 삭제한다.

**3. 서비스 레이어에 버전 분기를 넣는다**

```java
// 이렇게 하면 안 된다
@Service
public class UserService {
    public Object getUser(Long id, int version) {
        User user = findById(id);
        if (version == 1) return toV1(user);
        if (version == 2) return toV2(user);
        return toV3(user);
    }
}
```

서비스는 도메인 객체를 반환하고, DTO 변환은 컨트롤러 레이어에서 한다. 서비스에 버전이 들어가면 비즈니스 로직과 표현 로직이 섞여서 테스트하기 어려워진다.

**4. 버전 없이 시작한다**

"나중에 필요하면 넣지" 하다가 이미 여러 클라이언트가 `/api/users`를 호출하고 있으면 버저닝 도입 자체가 breaking change가 된다. 처음부터 `/api/v1/`으로 시작하는 게 비용이 거의 없고, 나중에 고생을 줄여준다.

## 참고

- [API Versioning (Microsoft)](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design#versioning-a-restful-web-api)
- [GitHub API Versioning](https://docs.github.com/en/rest/about-the-rest-api/api-versions)
- [Sunset HTTP Header (RFC 8594)](https://www.rfc-editor.org/rfc/rfc8594)
- [API 설계 패턴](./API_Design_Patterns.md) — 버전 관리 개요, REST/GraphQL/gRPC 비교
