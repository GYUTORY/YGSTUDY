---
title: API 설계 패턴
tags: [backend, api, rest, graphql]
updated: 2026-03-26
---

# API 설계 패턴

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

표에 없지만 실무에서 갈리는 자리가 몇 군데 있다.

**403 을 주면 리소스의 존재가 새어 나간다.** 남의 주문 `/orders/1234` 에 403 을 돌려주면 "그 주문은 있다"는 사실을 알려준 것이다. ID 를 훑으면 어떤 번호가 실재하는지 지도를 그릴 수 있다. 그래서 **다른 사용자의 리소스는 404 로 감추는** 선택을 많이 한다. 대신 권한이 없는 것과 정말 없는 것을 클라이언트가 구분하지 못하고, 지원 문의가 늘어난다. 어느 쪽이든 **같은 API 안에서 일관되게** 정해야 하고, 한 엔드포인트만 403 을 주면 그 하나가 정보 노출 경로가 된다.

**400 과 422 를 나눌지 정한다.** 형식이 틀린 것(`age: "스물"`)과 형식은 맞지만 규칙에 어긋나는 것(`age: -1`, 이미 예약된 시간)은 클라이언트 대응이 다르다. 전자는 코드 버그라 재시도해도 소용없고, 후자는 사용자에게 고쳐서 다시 제출하라고 안내한다. 둘을 다 400 으로 보내면 프론트가 메시지 문자열을 보고 분기하게 된다. 나눌 거면 전부 나누고, 안 나눌 거면 본문 `code` 필드로 구분한다.

**409 는 중복만이 아니다.** 낙관적 잠금 충돌(다른 사람이 먼저 수정함), 상태 전이 위반(이미 취소된 주문을 다시 취소) 도 409 다. 이쪽은 재시도하면 성공할 수 있으므로 클라이언트 동작이 다르다.

**204 로 고정한 DELETE 는 "없는 것을 지울 때"를 정해야 한다.** 이미 지워진 리소스에 DELETE 가 또 오면 404 인가 204 인가. 재시도가 흔한 환경이라면 204 로 두는 편이 클라이언트가 단순해진다 — 어차피 목표 상태(없음)에 도달했다. 404 로 두면 "지워졌는지 원래 없었는지"를 구분할 수 있지만, 네트워크 재시도마다 에러 알림이 뜬다.

**`200 OK` 안에 `{"success": false}` 를 담지 않는다.** 이게 실무에서 가장 자주 보이는 형태인데, HTTP 계층의 모니터링·재시도·서킷 브레이커가 전부 이 응답을 성공으로 센다. 장애 대시보드가 초록불인데 사용자는 아무것도 못 하는 상태가 여기서 나온다.

#### 페이징, 필터링, 정렬

```
GET /api/v1/products?page=0&size=20&sort=price,desc&category=electronics&minPrice=10000

응답:
{
  "content": [ ... ],
  "page": { "number": 0, "size": 20, "totalElements": 150, "totalPages": 8 }
}
```

#### 오프셋 페이징은 목록이 변하면 어긋난다

`page` 와 `size` 로 자르는 방식은 **요청 사이에 목록이 바뀌지 않는다**는 전제 위에 있다. 최신순 목록에서 1페이지를 본 뒤 새 글이 하나 등록되면 전체가 한 칸 밀린다.

```
1페이지: item10 item9 item8
(새 글 item11 등록)
2페이지: item8  item7 item6      ← item8 이 두 번 보인다
```

삭제되면 반대로 빠진다.

```
1페이지: item10 item9 item8
(item9 삭제)
2페이지: item6  item5 item4      ← item7 은 어느 페이지에도 안 나온다
```

무한 스크롤에서 같은 항목이 두 번 나오거나, 배치가 전체를 훑는데 일부를 건너뛰는 사고가 여기서 나온다. **누락 쪽이 더 위험하다** — 화면에서는 눈치채기 어렵고, 정산·마이그레이션 배치라면 데이터가 조용히 빠진다.

커서 방식은 "마지막으로 본 항목 다음부터"를 기준으로 잡아 이 문제가 없다.

```
GET /api/v1/products?after=eyJpZCI6MTAsInByaWNlIjo1MDAwfQ&size=20
```

| | 오프셋 (`page` + `size`) | 커서 (`after`) |
|---|---|---|
| 임의 페이지로 점프 | 된다 | 안 된다 (앞뒤로만) |
| 총 페이지 수 표시 | 된다 | 어렵다 |
| 목록 변경 시 | 중복·누락 발생 | 안전 |
| 깊은 페이지 성능 | `OFFSET` 만큼 건너뛰느라 느려진다 | 인덱스로 바로 찾는다 |
| 정렬 기준 변경 | 자유롭다 | 커서에 정렬 키가 묶여 있다 |

**"페이지 번호를 눌러 이동하는 UI 가 실제로 필요한가"** 로 고르면 대체로 답이 나온다. 무한 스크롤·앱 목록·배치 순회는 커서, 관리자 표는 오프셋이다.

`totalElements` 도 공짜가 아니다. 페이지를 넘길 때마다 조건이 같은 `COUNT(*)` 가 함께 돈다. 필터가 여러 테이블을 걸치면 COUNT 가 본 쿼리보다 비싸지는 일이 흔하다. 총 개수가 화면에 꼭 필요한 값인지 먼저 보고, "1,000개 이상"처럼 상한만 표시해도 되면 `LIMIT 1001` 로 세는 방법이 있다.

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
  - 라우팅: URL 기반으로 적절한 서비스로 전달
  - 인증/인가: 토큰 검증을 한 곳에서 처리
  - Rate Limiting: 과도한 요청 차단
  - 로깅/모니터링: 모든 API 호출 추적
  - 로드밸런싱: 서비스 인스턴스 분배
  - 응답 캐싱: 자주 조회되는 데이터 캐시
```

| API Gateway | 특징 |
|-------------|------|
| **AWS API Gateway** | AWS 관리형, Lambda 연동 |
| **Kong** | 오픈소스, 플러그인 풍부 |
| **Spring Cloud Gateway** | Spring 생태계, Java 네이티브 |
| **Nginx** | 경량, 고성능 |
| **Envoy** | K8s 서비스 메시 (Istio 기본) |

### 4. API 버전 관리

#### 방식별 비교

| 방식 | 예시 | 장점 | 단점 |
|------|------|------|------|
| **URL 경로** | `/api/v1/users` | 직관적, 캐싱 쉬움 | 버전마다 URL이 바뀜 |
| **헤더** | `Accept: application/vnd.api.v1+json` | URL이 깔끔함 | Postman/브라우저에서 테스트하기 번거로움 |
| **쿼리 파라미터** | `/api/users?version=1` | 구현이 단순함 | CDN 캐시 키가 복잡해짐 |

대부분의 프로젝트에서는 URL 경로 방식을 쓴다. 헤더 방식은 GitHub API처럼 외부 공개 API에서 간혹 보이는데, 클라이언트 개발자가 헤더를 빠뜨리면 어떤 버전이 응답하는지 혼란이 생긴다.

#### URL 경로 방식 — 마이그레이션 절차

NestJS 기준으로 v1과 v2를 동시 운영하는 구조다.

```typescript
// v1 컨트롤러 — 기존 응답 유지
import { Controller, Get, Param } from '@nestjs/common';
import { UserService } from '../user.service';

@Controller('api/v1/users')
export class UserV1Controller {
    constructor(private readonly userService: UserService) {}

    @Get(':id')
    async getUser(@Param('id') id: string): Promise<UserV1Response> {
        const user = await this.userService.findById(Number(id));
        // v1은 address를 단일 문자열로 반환
        return { id: user.id, name: user.name, address: user.fullAddress };
    }
}

// v2 컨트롤러 — address를 구조화된 객체로 변경
@Controller('api/v2/users')
export class UserV2Controller {
    constructor(private readonly userService: UserService) {}

    @Get(':id')
    async getUser(@Param('id') id: string): Promise<UserV2Response> {
        const user = await this.userService.findById(Number(id));
        // v2는 address를 city, street, zipCode로 분리
        return { id: user.id, name: user.name, address: user.address };
    }
}
```

v1을 폐기할 때는 바로 삭제하지 말고 Deprecation 헤더를 먼저 내려준다. 클라이언트 개발자가 로그에서 감지할 수 있게 하는 게 핵심이다.

```typescript
// v1 폐기 예고 — NestJS 인터셉터로 일괄 처리
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { Response, Request } from 'express';

@Injectable()
export class DeprecationInterceptor implements NestInterceptor {
    intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
        const req = context.switchToHttp().getRequest<Request>();
        const res = context.switchToHttp().getResponse<Response>();

        if (req.path.includes('/api/v1/')) {
            res.setHeader('Deprecation', 'true');
            res.setHeader('Sunset', 'Sat, 01 Aug 2026 00:00:00 GMT');
            const v2Path = '/api/v2' + req.path.substring(7);
            res.setHeader('Link', `<${v2Path}>; rel="successor-version"`);
        }

        return next.handle();
    }
}
```

마이그레이션 순서:

1. v2 엔드포인트를 배포한다
2. v1에 Deprecation 헤더를 추가한다
3. 클라이언트 팀에 전환 기한을 공유한다 (보통 3~6개월)
4. v1 트래픽을 모니터링하면서 0에 가까워지면 v1을 제거한다

#### Header 방식 — 마이그레이션 절차

하나의 컨트롤러에서 Accept 헤더로 분기한다.

```typescript
// Accept 헤더로 버전을 구분 — NestJS 컨트롤러
import { Controller, Get, Param, Headers } from '@nestjs/common';
import { UserService } from './user.service';

@Controller('api/users')
export class UserController {
    constructor(private readonly userService: UserService) {}

    @Get(':id')
    async getUser(
        @Param('id') id: string,
        @Headers('accept') accept: string,
    ): Promise<UserV1Response | UserV2Response> {
        const user = await this.userService.findById(Number(id));

        if (accept?.includes('vnd.myapp.v2+json')) {
            return new UserV2Response(user);
        }
        // 헤더 누락 시 v1을 기본으로 반환
        return new UserV1Response(user);
    }
}
```

문제는 클라이언트가 `Accept` 헤더 없이 요청하는 경우다. 기본 버전을 어떤 것으로 할지 정해야 하는데, 보통 최신 버전을 기본으로 두면 기존 클라이언트가 깨진다. **헤더 누락 시 v1을 기본으로 반환**하는 게 안전하다.

```typescript
// 헤더 없는 요청의 기본 버전 설정 — NestJS 미들웨어로 처리
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class ContentNegotiationMiddleware implements NestMiddleware {
    use(req: Request, res: Response, next: NextFunction): void {
        if (!req.headers['accept'] || req.headers['accept'] === '*/*') {
            // Accept 헤더 누락 시 v1을 기본으로 설정
            req.headers['accept'] = 'application/vnd.myapp.v1+json';
        }
        next();
    }
}
```

#### Query Parameter 방식 — 마이그레이션 절차

```typescript
// 쿼리 파라미터로 버전을 구분 — NestJS 컨트롤러
import { Controller, Get, Param, Query } from '@nestjs/common';

@Controller('api/users')
export class UserController {
    constructor(private readonly userService: UserService) {}

    @Get(':id')
    async getUser(
        @Param('id') id: string,
        @Query('version') version = '1',
    ): Promise<UserV1Response | UserV2Response> {
        const user = await this.userService.findById(Number(id));
        if (version === '2') {
            return new UserV2Response(user);
        }
        return new UserV1Response(user);
    }
}
```

if문으로 분기하니까 코드가 쉽게 지저분해진다. 버전이 3, 4로 늘어나면 걷잡을 수 없어진다. 소규모 내부 API가 아니면 쓰지 않는 게 낫다.

#### 하위 호환성이 깨지는 케이스

버전을 올려야 하는 상황, 즉 Breaking Change가 발생하는 경우를 정리한다. 이걸 모르면 "이 정도는 v1에 넣어도 되겠지" 하다가 클라이언트가 터진다.

| 변경 유형 | 예시 | Breaking 여부 |
|-----------|------|:---:|
| 필드 삭제 | 응답에서 `address` 필드 제거 | O |
| 필드 이름 변경 | `userName` → `name` | O |
| 필드 타입 변경 | `age: "25"` → `age: 25` | O |
| 필수 파라미터 추가 | 기존에 없던 `region` 파라미터를 필수로 추가 | O |
| Enum 값 삭제 | `status`에서 `PENDING` 제거 | O |
| 응답 구조 변경 | 단일 객체 → 배열 래핑 | O |
| 필드 추가 (선택) | 응답에 `createdAt` 필드 추가 | X |
| 선택 파라미터 추가 | `?sort=name` 쿼리 파라미터 추가 | X |
| Enum 값 추가 | `status`에 `REFUNDED` 추가 | 주의 필요 |

Enum 값 추가가 "주의 필요"인 이유: 클라이언트가 switch문이나 패턴 매칭으로 Enum을 처리하고 있으면, 알 수 없는 값이 들어올 때 예외가 발생한다. 클라이언트 코드에 `default` 케이스가 없으면 깨진다.

```typescript
// 클라이언트가 이렇게 처리하고 있으면
switch (order.status) {
    case 'COMPLETED': // ...
        break;
    case 'CANCELLED': // ...
        break;
    // default 없음 → REFUNDED가 들어오면 아무 처리도 안 됨
}
```

하위 호환성을 유지하면서 변경하는 방법:

```json
// Bad: 기존 필드를 삭제하고 새 필드로 대체
// v1 응답에서 address(String)를 없애고 addressDetail(Object)로 바꿈
// → 기존 클라이언트 전부 깨짐

// Good: 기존 필드는 유지하고 새 필드를 추가
{
    "address": "서울시 강남구 테헤란로 123",
    "addressDetail": {
        "city": "서울시",
        "district": "강남구",
        "street": "테헤란로 123",
        "zipCode": "06236"
    }
}
```

#### 버전의 비용은 만들 때가 아니라 지울 때 든다

v2 를 띄우는 일은 라우팅 한 줄이다. 어려운 것은 **v1 을 끄는 일**이고, 대부분의 프로젝트가 여기서 실패한다.

- 누가 아직 v1 을 쓰는지 알아야 한다. 접근 로그에 버전별 호출 수와 클라이언트 식별자가 남지 않으면 끌 근거가 없다.
- 모바일 앱은 강제 업데이트를 하지 않는 한 구버전이 남는다. 사용자가 앱을 안 지우면 v1 은 몇 년씩 산다.
- 그 사이 두 버전이 **같은 DB 를 본다.** 스키마를 바꾸면 v1 어댑터도 함께 고쳐야 하고, 이 부담이 버전 수만큼 곱해진다.

그래서 실무의 목표는 "버전 관리를 잘하는 것"이 아니라 **버전을 안 올리는 것**이 된다. 위 Breaking Change 표에서 X 로 표시된 변경(필드 추가, 선택 파라미터 추가)만으로 요구사항을 소화할 수 있는지 먼저 본다. 필드 이름을 바꿔야 하면 새 이름을 추가하고 옛 이름을 한동안 함께 내려보내는 식이다.

이게 성립하려면 **클라이언트가 모르는 것을 무시하도록 만들어져야 한다.** 응답에 새 필드가 생겼다고 파싱이 실패하거나, 모르는 enum 값에 예외를 던지면 서버는 아무것도 추가할 수 없다. 위 enum 예시가 그 이야기이고, 방향을 뒤집어 정리하면 이렇다.

| 서버가 지켜야 할 것 | 클라이언트가 지켜야 할 것 |
|---|---|
| 기존 필드를 지우거나 이름을 바꾸지 않는다 | 모르는 필드는 무시한다 |
| 응답 구조를 감싸거나 벗기지 않는다 | 모르는 enum 값에 `default` 를 둔다 |
| 새 요청 파라미터는 선택으로 넣는다 | 필드 순서에 의존하지 않는다 |

**한쪽만 지켜서는 성립하지 않는다.** 사내 API 라면 클라이언트 쪽 규칙을 코드 리뷰로 강제할 수 있지만, 외부 공개 API 는 그럴 수 없다. 공개 API 에서 버전 정책이 훨씬 보수적인 이유가 이것이다.

버전을 올리기로 했다면 끝나는 조건을 함께 정한다 — 언제까지 v1 을 유지할지, 어떤 지표(v1 호출 비율)가 얼마 아래로 떨어지면 끌지, 끄기 전에 무엇으로 알릴지. 이 셋이 없으면 v1 은 영구히 남는다.

### 5. 에러 응답 표준화

모든 API에서 에러 응답 형식이 제각각이면 프론트엔드에서 에러 처리 로직이 엔드포인트마다 달라진다. 에러 응답 DTO를 하나로 통일하고, `@RestControllerAdvice`로 모든 예외를 잡아서 같은 형식으로 내려줘야 한다.

#### 에러 응답 DTO

```typescript
export interface FieldError {
    field: string;
    message: string;
    rejectedValue: unknown;
}

export class ErrorResponse {
    readonly code: string;           // 비즈니스 에러 코드 (VALIDATION_ERROR, USER_NOT_FOUND 등)
    readonly message: string;        // 사람이 읽을 수 있는 메시지
    readonly errors: FieldError[];   // 필드별 검증 에러 (없으면 빈 배열)
    readonly path: string;           // 요청 경로
    readonly timestamp: string;

    private constructor(code: string, message: string, errors: FieldError[], path: string) {
        this.code = code;
        this.message = message;
        this.errors = errors;
        this.path = path;
        this.timestamp = new Date().toISOString();
    }

    static of(code: string, message: string, path: string): ErrorResponse;
    static of(code: string, message: string, errors: FieldError[], path: string): ErrorResponse;
    static of(code: string, message: string, errorsOrPath: FieldError[] | string, path?: string): ErrorResponse {
        if (typeof errorsOrPath === 'string') {
            return new ErrorResponse(code, message, [], errorsOrPath);
        }
        return new ErrorResponse(code, message, errorsOrPath, path as string);
    }
}
```

#### 비즈니스 예외 정의

```typescript
import { HttpStatus } from '@nestjs/common';

export interface ErrorCodeDef {
    code: string;
    message: string;
    httpStatus: HttpStatus;
}

// 비즈니스 에러 코드 정의
export const ErrorCode = {
    // 400
    INVALID_INPUT:   { code: 'INVALID_INPUT',   message: '잘못된 입력값이다',       httpStatus: HttpStatus.BAD_REQUEST },
    DUPLICATE_EMAIL: { code: 'DUPLICATE_EMAIL', message: '이미 등록된 이메일이다',  httpStatus: HttpStatus.CONFLICT },

    // 404
    USER_NOT_FOUND:  { code: 'USER_NOT_FOUND',  message: '해당 사용자가 없다',      httpStatus: HttpStatus.NOT_FOUND },
    ORDER_NOT_FOUND: { code: 'ORDER_NOT_FOUND', message: '해당 주문이 없다',        httpStatus: HttpStatus.NOT_FOUND },

    // 403
    ACCESS_DENIED:   { code: 'ACCESS_DENIED',   message: '접근 권한이 없다',        httpStatus: HttpStatus.FORBIDDEN },

    // 500
    INTERNAL_ERROR:  { code: 'INTERNAL_ERROR',  message: '서버 내부 오류가 발생했다', httpStatus: HttpStatus.INTERNAL_SERVER_ERROR },
} as const satisfies Record<string, ErrorCodeDef>;

export class BusinessException extends Error {
    readonly errorCode: ErrorCodeDef;

    constructor(errorCode: ErrorCodeDef) {
        super(errorCode.message);
        this.errorCode = errorCode;
        this.name = 'BusinessException';
    }
}
```

#### 전역 예외 처리

```typescript
import {
    ExceptionFilter, Catch, ArgumentsHost, HttpException,
    HttpStatus, Logger, BadRequestException,
} from '@nestjs/common';
import { Request, Response } from 'express';
import { BusinessException, ErrorCode } from './error-code';
import { ErrorResponse, FieldError } from './error-response';

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
    private readonly logger = new Logger(GlobalExceptionFilter.name);

    catch(exception: unknown, host: ArgumentsHost): void {
        const ctx = host.switchToHttp();
        const req = ctx.getRequest<Request>();
        const res = ctx.getResponse<Response>();
        const path = req.path;

        // 비즈니스 예외
        if (exception instanceof BusinessException) {
            const { code, message, httpStatus } = exception.errorCode;
            this.logger.warn(`Business exception: ${code} at ${path}`);
            res.status(httpStatus).json(ErrorResponse.of(code, message, path));
            return;
        }

        // NestJS 유효성 검증 실패 (class-validator @IsEmail 등)
        if (exception instanceof BadRequestException) {
            const response = (exception as BadRequestException).getResponse() as { message?: string[] };
            const fieldErrors: FieldError[] = (response.message ?? []).map((msg) => ({
                field: '',
                message: msg,
                rejectedValue: undefined,
            }));
            res.status(HttpStatus.BAD_REQUEST).json(
                ErrorResponse.of('VALIDATION_ERROR', '입력값 검증에 실패했다', fieldErrors, path),
            );
            return;
        }

        // 그 외 모든 예외 — 스택 트레이스를 클라이언트에 절대 노출하지 않는다
        this.logger.error(`Unhandled exception at ${path}`, exception);
        res.status(HttpStatus.INTERNAL_SERVER_ERROR).json(
            ErrorResponse.of(
                ErrorCode.INTERNAL_ERROR.code,
                ErrorCode.INTERNAL_ERROR.message,
                path,
            ),
        );
    }
}
```

#### 실제 응답 예시

검증 실패 시 (400):

```json
{
    "code": "VALIDATION_ERROR",
    "message": "입력값 검증에 실패했다",
    "errors": [
        {
            "field": "email",
            "message": "올바른 이메일 형식이 아닙니다",
            "rejectedValue": "not-an-email"
        },
        {
            "field": "name",
            "message": "이름은 2자 이상이어야 합니다",
            "rejectedValue": "김"
        }
    ],
    "path": "/api/v1/users",
    "timestamp": "2026-03-26T14:30:00"
}
```

리소스 없음 (404):

```json
{
    "code": "USER_NOT_FOUND",
    "message": "해당 사용자가 없다",
    "errors": [],
    "path": "/api/v1/users/999",
    "timestamp": "2026-03-26T14:31:00"
}
```

서비스 코드에서 쓸 때:

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';
import { BusinessException, ErrorCode } from './error-code';

@Injectable()
export class UserService {
    constructor(
        @InjectRepository(User)
        private readonly userRepository: Repository<User>,
    ) {}

    async findById(id: number): Promise<User> {
        const user = await this.userRepository.findOne({ where: { id } });
        if (!user) throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        return user;
    }

    async register(request: UserCreateRequest): Promise<User> {
        const exists = await this.userRepository.existsBy({ email: request.email });
        if (exists) throw new BusinessException(ErrorCode.DUPLICATE_EMAIL);
        return this.userRepository.save(this.userRepository.create(request));
    }
}
```

주의할 점: `Exception.class`를 잡는 핸들러에서 에러 메시지를 `e.getMessage()`로 내려보내면 안 된다. NullPointerException 같은 경우 내부 구현이 노출되고, SQL 예외면 테이블 구조까지 보일 수 있다. 항상 고정된 메시지를 내려주고 실제 예외는 서버 로그에만 남긴다.

### 6. OpenAPI / Swagger

API 문서를 자동 생성하고, 프론트엔드 개발자와 소통하는 표준이다.

```bash
# NestJS + @nestjs/swagger
npm install @nestjs/swagger swagger-ui-express
```

```typescript
// main.ts — Swagger 설정
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
    const app = await NestFactory.create(AppModule);

    const config = new DocumentBuilder()
        .setTitle('API 문서')
        .setVersion('1.0')
        .addBearerAuth()
        .build();

    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('swagger-ui', app, document, {
        jsonDocumentUrl: 'api-docs',
    });

    await app.listen(3000);
}
void bootstrap();
```

```typescript
// NestJS + @nestjs/swagger 데코레이터
import { Controller, Get, Param } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';

@ApiTags('User')
@Controller('api/v1/users')
export class UserController {
    @ApiOperation({ summary: '사용자 조회', description: 'ID로 사용자를 조회합니다' })
    @ApiResponse({ status: 200, description: '조회 성공' })
    @ApiResponse({ status: 404, description: '사용자 없음' })
    @Get(':id')
    async getUser(@Param('id') id: string): Promise<UserResponse> { /* ... */ }
}
```

### 7. HATEOAS

HATEOAS(Hypermedia as the Engine of Application State)는 REST의 성숙도 모델에서 Level 3에 해당한다. 응답에 다음에 할 수 있는 행동을 링크로 포함하는 방식이다.

#### 기본 개념

```json
{
    "id": 1,
    "name": "김개발",
    "email": "kim@example.com",
    "_links": {
        "self": { "href": "/api/v1/users/1" },
        "orders": { "href": "/api/v1/users/1/orders" },
        "update": { "href": "/api/v1/users/1", "method": "PUT" },
        "delete": { "href": "/api/v1/users/1", "method": "DELETE" }
    }
}
```

클라이언트가 URL을 하드코딩하지 않아도 응답의 링크를 따라가면서 API를 탐색할 수 있다는 게 이론적인 장점이다.

#### NestJS HATEOAS 구현

```typescript
// NestJS에서는 응답 DTO에 _links 필드를 직접 추가하는 방식이 일반적이다
import { Controller, Get, Param } from '@nestjs/common';
import { UserService } from './user.service';

interface HalLink { href: string; method?: string }
interface HalResponse<T> { data: T; _links: Record<string, HalLink> }

@Controller('api/v1/users')
export class UserController {
    constructor(private readonly userService: UserService) {}

    @Get(':id')
    async getUser(@Param('id') id: string): Promise<HalResponse<UserResponse>> {
        const user = await this.userService.findById(Number(id));
        const response = UserResponse.from(user);

        return {
            data: response,
            _links: {
                self:   { href: `/api/v1/users/${id}` },
                orders: { href: `/api/v1/users/${id}/orders` },
                update: { href: `/api/v1/users/${id}`, method: 'PUT' },
                delete: { href: `/api/v1/users/${id}`, method: 'DELETE' },
            },
        };
    }

    @Get()
    async getUsers(): Promise<HalResponse<UserResponse[]>> {
        const users = await this.userService.findAll();

        return {
            data: users.map((u) => UserResponse.from(u)),
            _links: {
                self: { href: '/api/v1/users' },
            },
        };
    }
}
```

#### 실무에서 겪는 문제

이론은 깔끔한데, 실제로 도입하면 여러 가지 문제가 생긴다.

**1. 프론트엔드가 링크를 쓰지 않는다**

가장 큰 문제다. React/Vue 같은 SPA 프론트엔드는 이미 API 경로를 상수로 관리하고 있다. 응답에 링크가 있어도 프론트 개발자가 `response._links.orders.href`를 파싱해서 쓰지 않는다. 그냥 `/api/v1/users/${id}/orders`를 직접 호출한다.

```typescript
// 프론트엔드에서 실제로 하는 방식
const API = {
    users: (id: number) => `/api/v1/users/${id}`,
    userOrders: (id: number) => `/api/v1/users/${id}/orders`,
};

// HATEOAS 링크를 따라가는 코드는 거의 작성하지 않는다
// fetch(response._links.orders.href) ← 이렇게 안 함
```

**2. 응답 크기가 불필요하게 커진다**

목록 API에서 100건을 조회하면 각 항목마다 링크가 붙는다. 응답 크기가 30~50% 정도 늘어나는 경우가 있다. 모바일 클라이언트에서 대역폭이 아까울 수 있다.

```json
// 100건 목록의 각 항목마다 이런 링크가 붙음
{
    "id": 1,
    "name": "상품A",
    "price": 10000,
    "_links": {
        "self": { "href": "/api/v1/products/1" },
        "reviews": { "href": "/api/v1/products/1/reviews" },
        "category": { "href": "/api/v1/categories/5" },
        "seller": { "href": "/api/v1/sellers/3" }
    }
}
// × 100건 = 링크 데이터만 수 KB
```

**3. 컨트롤러 코드가 복잡해진다**

`linkTo(methodOn(...))` 코드가 비즈니스 로직보다 길어지는 경우가 있다. 조건부 링크(권한에 따라 삭제 링크를 보여주거나 숨기거나)를 넣기 시작하면 코드가 급격히 복잡해진다.

```typescript
// 조건부 링크 — 코드가 금방 지저분해진다
const links: Record<string, HalLink> = {
    self: { href: `/api/v1/orders/${id}` },
};

if (order.status === 'PENDING') {
    links['cancel'] = { href: `/api/v1/orders/${id}/cancel`, method: 'POST' };
}
if (order.status === 'SHIPPED') {
    links['confirm'] = { href: `/api/v1/orders/${id}/confirm`, method: 'POST' };
}
if (currentUser.isAdmin) {
    links['delete'] = { href: `/api/v1/orders/${id}`, method: 'DELETE' };
}
```

**4. API 테스트가 번거로워진다**

응답에 링크가 포함되니까 테스트에서 응답 검증 코드도 길어진다. 링크 URL이 바뀔 때마다 테스트도 수정해야 한다.

```typescript
// Jest + supertest — 링크 검증까지 해야 해서 테스트가 길어짐
import * as request from 'supertest';

test('사용자 조회 응답에 링크가 포함된다', async () => {
    const res = await request(app.getHttpServer())
        .get('/api/v1/users/1')
        .expect(200);

    expect(res.body.data.name).toBe('김개발');
    // 링크 검증까지 해야 해서 테스트가 길어짐
    expect(res.body._links.self.href).toBe('/api/v1/users/1');
    expect(res.body._links.orders.href).toBe('/api/v1/users/1/orders');
});
```

#### 도입 판단 기준

HATEOAS를 넣을지 말지는 다음을 기준으로 판단한다.

| 상황 | 판단 |
|------|------|
| 내부 SPA 프론트엔드만 쓰는 API | 넣지 않는다 |
| 외부 공개 API (제3자 개발자가 사용) | 고려할 만하다 |
| 리소스 간 관계가 복잡하고 탐색이 필요한 API | 고려할 만하다 |
| 팀 내 프론트/백엔드가 긴밀하게 협업 | 넣지 않는다 |

대부분의 사내 프로젝트에서는 OpenAPI(Swagger) 문서를 잘 관리하는 것이 HATEOAS보다 실용적이다. HATEOAS는 REST 순수주의에 가깝고, 실무에서 비용 대비 이득이 크지 않은 경우가 많다.

## 참고

- [RESTful Web API Design (Microsoft)](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [GraphQL 공식 문서](https://graphql.org/learn/)
- [gRPC 공식 문서](https://grpc.io/docs/)
- [OpenAPI 스펙](https://swagger.io/specification/)
- [API 설계 원칙](../../Framework/Node/API/API_설계_원칙.md) — Node.js 관점
- [Spring MVC REST API](../../Framework/Java/Spring/Spring_MVC_REST_API.md) — Spring 구현
