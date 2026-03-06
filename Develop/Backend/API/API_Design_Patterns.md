---
title: API 설계 패턴 비교 가이드
tags: [backend, api, rest, graphql, grpc, api-gateway, versioning, design-patterns]
updated: 2026-03-01
---

# API 설계 패턴 비교 가이드

## 개요

백엔드 서비스의 API 통신 방식은 크게 REST, GraphQL, gRPC로 나뉜다. 각각의 특성을 이해하고 상황에 맞게 선택해야 한다.

## 핵심

### 1. REST vs GraphQL vs gRPC

| 항목 | REST | GraphQL | gRPC |
|------|------|---------|------|
| **프로토콜** | HTTP/1.1 (JSON) | HTTP/1.1 (JSON) | HTTP/2 (Protobuf) |
| **데이터 형식** | JSON | JSON | Protocol Buffers (바이너리) |
| **요청 방식** | URL + HTTP Method | 단일 엔드포인트 + 쿼리 | 서비스 메서드 호출 |
| **Over-fetching** | 발생 (고정 응답) | 없음 (필요한 필드만) | 없음 (스키마 정의) |
| **Under-fetching** | 발생 (여러 번 호출) | 없음 (한 번에 조합) | 없음 |
| **타입 안전성** | 낮음 (OpenAPI로 보완) | 높음 (스키마 기반) | 매우 높음 (IDL) |
| **성능** | 보통 | 보통 | 매우 빠름 (바이너리) |
| **스트리밍** | 미지원 (SSE 제외) | Subscription | 양방향 스트리밍 |
| **학습 곡선** | 낮음 | 중간 | 높음 |
| **적합한 상황** | 일반 웹 API | 복잡한 프론트 요구사항 | MSA 내부 통신 |

```
REST:
  GET  /api/users/1          → { id, name, email, address, orders, ... }
  GET  /api/users/1/orders   → [ { id, total, items, ... } ]
  (2번 호출, 불필요한 데이터 포함)

GraphQL:
  POST /graphql
  { query: "{ user(id: 1) { name, orders { total } } }" }
  → { name: "홍길동", orders: [{ total: 50000 }] }
  (1번 호출, 필요한 데이터만)

gRPC:
  userService.GetUser(UserRequest { id: 1 })
  → UserResponse { name: "홍길동", ... }
  (바이너리 직렬화, 매우 빠름)
```

### 2. REST API 설계 원칙

#### URL 설계 규칙

| 규칙 | 좋은 예 | 나쁜 예 |
|------|---------|---------|
| 명사 복수형 | `/api/users` | `/api/getUsers` |
| 소문자 + 하이픈 | `/api/order-items` | `/api/OrderItems` |
| 계층 관계 표현 | `/api/users/1/orders` | `/api/getUserOrders?userId=1` |
| 동사 지양 | `POST /api/orders` | `POST /api/createOrder` |
| 버전 포함 | `/api/v1/users` | `/api/users?version=1` |

#### 상태 코드 가이드

| 코드 | 의미 | 사용 상황 |
|------|------|----------|
| **200** | OK | 조회/수정 성공 |
| **201** | Created | 생성 성공 (Location 헤더 포함) |
| **204** | No Content | 삭제 성공 |
| **400** | Bad Request | 유효성 검증 실패 |
| **401** | Unauthorized | 인증 실패 (토큰 없음/만료) |
| **403** | Forbidden | 인가 실패 (권한 없음) |
| **404** | Not Found | 리소스 없음 |
| **409** | Conflict | 중복 데이터 |
| **429** | Too Many Requests | Rate Limit 초과 |
| **500** | Internal Server Error | 서버 에러 |

#### 페이징, 필터링, 정렬

```
GET /api/v1/products?page=0&size=20&sort=price,desc&category=electronics&minPrice=10000

응답:
{
  "content": [ ... ],
  "page": { "number": 0, "size": 20, "totalElements": 150, "totalPages": 8 }
}
```

### 3. API Gateway

마이크로서비스 환경에서 **단일 진입점**을 제공한다.

```
클라이언트
    │
    ▼
API Gateway
    │
    ├─ /api/users/*    → User Service
    ├─ /api/orders/*   → Order Service
    ├─ /api/products/* → Product Service
    └─ /api/payments/* → Payment Service

역할:
  ✅ 라우팅: URL 기반으로 적절한 서비스로 전달
  ✅ 인증/인가: 토큰 검증을 한 곳에서 처리
  ✅ Rate Limiting: 과도한 요청 차단
  ✅ 로깅/모니터링: 모든 API 호출 추적
  ✅ 로드밸런싱: 서비스 인스턴스 분배
  ✅ 응답 캐싱: 자주 조회되는 데이터 캐시
```

| API Gateway | 특징 |
|-------------|------|
| **AWS API Gateway** | AWS 관리형, Lambda 연동 |
| **Kong** | 오픈소스, 플러그인 풍부 |
| **Spring Cloud Gateway** | Spring 생태계, Java 네이티브 |
| **Nginx** | 경량, 고성능 |
| **Envoy** | K8s 서비스 메시 (Istio 기본) |

### 4. API 버전 관리

| 방식 | 예시 | 장점 | 단점 |
|------|------|------|------|
| **URL 경로** | `/api/v1/users` | 직관적, 가장 보편적 | URL 변경 |
| **헤더** | `Accept: application/vnd.api.v1+json` | URL 깔끔 | 발견 어려움 |
| **쿼리 파라미터** | `/api/users?version=1` | 간단 | 캐싱 복잡 |

📌 **실무 권장**: URL 경로 방식 (`/api/v1/`). 가장 직관적이고 브라우저/문서에서 쉽게 구분된다.

#### 버전 전환 전략

```
1. 새 버전 배포: /api/v2/users 추가
2. 마이그레이션 기간: v1, v2 동시 운영
3. 클라이언트 전환: v1 → v2 이전 요청
4. v1 폐지: Deprecated 헤더 추가 → 최종 제거

HTTP/1.1 200 OK
Sunset: Sat, 01 Jun 2026 00:00:00 GMT
Deprecation: true
Link: </api/v2/users>; rel="successor-version"
```

### 5. 에러 응답 표준화

```json
{
  "code": "VALIDATION_ERROR",
  "message": "입력값이 올바르지 않습니다",
  "errors": [
    {
      "field": "email",
      "message": "올바른 이메일 형식이 아닙니다",
      "rejectedValue": "invalid"
    }
  ],
  "timestamp": "2026-03-01T10:30:00Z",
  "path": "/api/v1/users"
}
```

| 원칙 | 설명 |
|------|------|
| **일관된 구조** | 모든 에러가 같은 JSON 형태 |
| **의미 있는 코드** | HTTP 상태 코드 + 비즈니스 에러 코드 |
| **구체적 메시지** | 개발자가 원인을 파악할 수 있는 메시지 |
| **보안 주의** | 500 에러 시 스택 트레이스 노출 금지 |

### 6. OpenAPI / Swagger

API 문서를 자동 생성하고, 프론트엔드 개발자와 소통하는 표준이다.

```java
// Spring Boot 3.x + springdoc-openapi
// build.gradle
implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0'
```

```yaml
# application.yml
springdoc:
  api-docs:
    path: /api-docs
  swagger-ui:
    path: /swagger-ui.html
```

```java
@RestController
@RequestMapping("/api/v1/users")
@Tag(name = "User", description = "사용자 관리 API")
public class UserController {

    @Operation(summary = "사용자 조회", description = "ID로 사용자를 조회합니다")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "조회 성공"),
        @ApiResponse(responseCode = "404", description = "사용자 없음")
    })
    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) { ... }
}
```

## 운영 팁

### API 설계 체크리스트

| 항목 | 확인 |
|------|------|
| URL이 명사 복수형인가 | `/api/users` (O) |
| HTTP 메서드가 적절한가 | `DELETE /users/1` (O) |
| 상태 코드가 의미에 맞는가 | 201 Created (O) |
| 에러 응답이 일관적인가 | 통일된 JSON 구조 |
| 페이징이 적용되어 있는가 | 대규모 목록 |
| API 문서가 있는가 | OpenAPI/Swagger |
| 버전 관리를 하고 있는가 | `/api/v1/` |
| Rate Limiting이 있는가 | 429 반환 |
| 인증이 적용되어 있는가 | 401/403 처리 |

## 참고

- [RESTful Web API Design (Microsoft)](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [GraphQL 공식 문서](https://graphql.org/learn/)
- [gRPC 공식 문서](https://grpc.io/docs/)
- [OpenAPI 스펙](https://swagger.io/specification/)
- [API 설계 원칙](../../Framework/Node/API/API_설계_원칙.md) — Node.js 관점
- [Spring MVC REST API](../../Framework/Java/Spring/Spring_MVC_REST_API.md) — Spring 구현
