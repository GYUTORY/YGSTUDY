---
title: HTTP 에러 응답 설계 (RFC 7807 Problem Details)
tags: [rest, http, RFC7807, ProblemDetails, error-handling, spring, nestjs, msa]
updated: 2026-07-26
---

# HTTP 에러 응답 설계 (RFC 7807 Problem Details)

## 왜 에러 응답 형식이 문제가 되나

API를 여럿 만들다 보면 팀마다, 심지어 같은 팀 내에서도 에러 형식이 다 다르다. 어떤 엔드포인트는 `{"error": "not found"}`, 어떤 곳은 `{"code": 404, "message": "리소스 없음"}`, 또 다른 곳은 `{"success": false, "data": null, "errorCode": "E001"}` 같은 식이다.

이게 사내 API 하나일 때는 그냥 넘어갈 수 있지만, MSA 환경에서 여러 서비스가 각자 다른 에러 형식을 뱉으면 클라이언트에서 에러 처리 코드가 서비스 수만큼 달라진다. Gateway 레벨에서 에러를 통합하려 해도 파싱 로직이 따로따로 생긴다.

RFC 7807은 이 문제를 해결하려고 2016년에 나왔다. 표준 필드 집합을 정의해서 모든 HTTP API가 동일한 구조로 에러를 표현하게 한다. 2022년에 RFC 9457로 업데이트됐지만 현장에서는 여전히 7807을 많이 언급한다.

## RFC 7807 필드 구조

```json
{
  "type": "https://api.example.com/problems/insufficient-balance",
  "title": "Insufficient Balance",
  "status": 400,
  "detail": "현재 잔액 5,000원으로는 10,000원 결제를 처리할 수 없습니다.",
  "instance": "/payments/tx-a1b2c3d4"
}
```

각 필드의 실제 의미는 이렇다.

**type**: 에러 유형을 식별하는 URI. 실제로 접근 가능한 URL이면 그 페이지에 에러 상세 설명을 담아두는 게 이상적이지만, 현실에서는 문서가 없는 URN 형태로만 쓰는 팀도 많다. 중요한 건 같은 에러 유형이면 항상 같은 type 값을 쓴다는 것이다. 클라이언트는 type 값으로 에러 종류를 분기 처리한다.

**title**: type의 사람이 읽을 수 있는 요약. 에러 유형이 같으면 title도 항상 같아야 한다. "결제 잔액 부족", "이메일 중복" 같은 수준으로 고정한다. 동적인 정보를 여기에 넣으면 안 된다.

**status**: HTTP 상태 코드를 그대로 담는다. 응답 헤더의 상태 코드와 동일해야 한다. 이 값이 달라지는 상황은 Proxy나 CDN이 중간에서 응답을 가공했거나 버그다.

**detail**: 이 요청에서 실제로 무슨 일이 벌어졌는지 설명. title이 고정값이라면 detail은 요청별로 달라지는 동적 정보를 담는다. 사용자에게 보여줄 수 있는 수준의 설명을 여기에 쓴다.

**instance**: 이 에러 발생 건을 추적할 수 있는 URI. 요청 URL이나 트랜잭션 ID URI를 담는다. 로그에서 이 값으로 검색할 수 있게 해두면 디버깅이 편해진다.

## 미디어 타입

RFC 7807 응답은 `Content-Type: application/problem+json`을 사용한다.

```
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json
```

클라이언트가 이 미디어 타입을 보면 표준 에러 구조임을 알 수 있다. `application/json`으로 보내도 동작하지만, 클라이언트가 미디어 타입으로 에러 응답과 정상 응답을 구분하는 경우라면 구분이 안 된다.

Accept 헤더로 `application/problem+json`을 요청하는 클라이언트는 서버가 이를 지원하는지 확인하고 싶다는 뜻이다. 구현 시 이 Content-Type 헤더 설정을 빠뜨리는 경우가 많으니 주의한다.

## 비즈니스 에러 vs HTTP 에러 구분

가장 많이 헷갈리는 부분이다. "잔액 부족"은 400인가 402인가 422인가? 팀마다 다르게 쓴다.

HTTP 상태 코드는 프로토콜 레벨의 결과를 나타낸다. 비즈니스 에러는 HTTP 레벨에서 보면 요청 자체는 문법적으로 올바른데 도메인 규칙 위반으로 처리 불가능한 경우다.

실무에서 쓰는 기준:

| 상황 | HTTP 상태 | type 구분 |
|------|-----------|-----------|
| 요청 파라미터 파싱 실패 | 400 | HTTP 에러 |
| 인증 토큰 없음/만료 | 401 | HTTP 에러 |
| 권한 없음 | 403 | HTTP 에러 |
| 리소스 없음 | 404 | HTTP 에러 |
| 잔액 부족 | 400 | 비즈니스 에러 |
| 중복 주문 | 409 | 비즈니스 에러 |
| 재고 소진 | 422 | 비즈니스 에러 |
| 외부 결제 API 실패 | 502 | HTTP 에러 |

비즈니스 에러는 같은 HTTP 상태 코드라도 type 필드로 세분화한다. 클라이언트는 HTTP 상태 코드로 1차 분기하고, type 값으로 2차 분기한다.

```json
// 요청 파라미터 오류 (HTTP 에러)
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Bad Request",
  "status": 400,
  "detail": "amount 필드는 양수여야 합니다.",
  "instance": "/payments/req-xyz"
}

// 잔액 부족 (비즈니스 에러)
{
  "type": "https://api.example.com/problems/insufficient-balance",
  "title": "Insufficient Balance",
  "status": 400,
  "detail": "현재 잔액 5,000원으로는 10,000원 결제를 처리할 수 없습니다.",
  "instance": "/payments/req-xyz",
  "currentBalance": 5000,
  "requiredAmount": 10000
}
```

위 예시처럼 RFC 7807은 확장 필드를 허용한다. 표준 필드 외에 도메인 특화 정보를 추가로 넣을 수 있다.

## 에러 코드 계층 설계

type URI를 어떻게 구성하느냐가 에러 코드 계층을 결정한다. 직접 운영하면서 잘 돌아간 방식은 도메인/하위도메인 구조다.

```
https://api.example.com/problems/{domain}/{error-slug}

예:
https://api.example.com/problems/payment/insufficient-balance
https://api.example.com/problems/payment/duplicate-transaction
https://api.example.com/problems/inventory/out-of-stock
https://api.example.com/problems/auth/token-expired
https://api.example.com/problems/auth/insufficient-scope
```

이렇게 하면 `problems/payment/` 로 시작하는 건 결제 관련 에러임을 한눈에 알 수 있고, 클라이언트에서도 prefix 매칭으로 처리할 수 있다.

에러 슬러그는 명사+상태 형태(`out-of-stock`)가 동사 형태(`cannot-purchase`)보다 낫다. 나중에 같은 에러가 다른 흐름에서 발생해도 재사용할 수 있다.

서비스 내 에러 상수로 type URI를 관리한다.

```typescript
import { HttpStatus } from '@nestjs/common';

interface ProblemTypeDefinition {
  typeUri: string;
  title: string;
  status: HttpStatus;
}

export const ProblemType = {
  INSUFFICIENT_BALANCE: {
    typeUri: 'https://api.example.com/problems/payment/insufficient-balance',
    title: 'Insufficient Balance',
    status: HttpStatus.BAD_REQUEST,
  },
  DUPLICATE_TRANSACTION: {
    typeUri: 'https://api.example.com/problems/payment/duplicate-transaction',
    title: 'Duplicate Transaction',
    status: HttpStatus.CONFLICT,
  },
  OUT_OF_STOCK: {
    typeUri: 'https://api.example.com/problems/inventory/out-of-stock',
    title: 'Out of Stock',
    status: HttpStatus.UNPROCESSABLE_ENTITY,
  },
} as const satisfies Record<string, ProblemTypeDefinition>;
```

하드코딩된 문자열을 여러 곳에 쓰지 말고, 이런 상수 객체 하나에서 관리해야 type 오타나 불일치를 막을 수 있다.

## NestJS ProblemDetail 구현 (심화)

NestJS 필터에서 커스텀 예외를 잡아 ValidationPipe 에러도 함께 처리하는 예시다.

```typescript
// global-exception.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { Request, Response } from 'express';

interface ValidationErrorDetail {
  field: string;
  message: string;
}

@Catch()
export class GlobalProblemDetailFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    if (exception instanceof InsufficientBalanceException) {
      response
        .status(HttpStatus.BAD_REQUEST)
        .header('Content-Type', 'application/problem+json')
        .json({
          type: 'https://api.example.com/problems/payment/insufficient-balance',
          title: 'Insufficient Balance',
          status: HttpStatus.BAD_REQUEST,
          detail: exception.message,
          instance: request.url,
          // 확장 필드
          currentBalance: exception.currentBalance,
          requiredAmount: exception.requiredAmount,
        });
      return;
    }

    // class-validator (ValidationPipe) 에러 처리
    if (exception instanceof BadRequestException) {
      const res = exception.getResponse() as Record<string, unknown>;
      const rawErrors = Array.isArray(res['message']) ? res['message'] : [res['message']];

      const errors: ValidationErrorDetail[] = rawErrors.map((msg: unknown) => ({
        field: typeof msg === 'string' ? msg.split(' ')[0] : 'unknown',
        message: typeof msg === 'string' ? msg : 'invalid',
      }));

      response
        .status(HttpStatus.BAD_REQUEST)
        .header('Content-Type', 'application/problem+json')
        .json({
          type: 'https://api.example.com/problems/validation-failed',
          title: 'Validation Failed',
          status: HttpStatus.BAD_REQUEST,
          detail: '입력값 검증에 실패했습니다.',
          instance: request.url,
          errors,
        });
      return;
    }

    const status =
      exception instanceof HttpException ? exception.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR;

    response
      .status(status)
      .header('Content-Type', 'application/problem+json')
      .json({
        type: 'https://api.example.com/problems/internal-error',
        title: 'Internal Server Error',
        status,
        detail: 'An unexpected error occurred.',
        instance: request.url,
      });
  }
}
```

## NestJS 구현

NestJS에는 ProblemDetail 내장 지원이 없어서 직접 만든다.

```typescript
// problem-detail.interface.ts
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  [key: string]: unknown;
}

// problem.exception.ts
export class ProblemException extends HttpException {
  constructor(
    private readonly problemDetail: Omit<ProblemDetail, 'status'>,
    status: HttpStatus,
  ) {
    super(problemDetail, status);
  }

  getProblemDetail(): ProblemDetail {
    return {
      ...this.problemDetail,
      status: this.getStatus(),
    };
  }
}

// problem.filter.ts
@Catch()
export class ProblemDetailFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    if (exception instanceof ProblemException) {
      const problem = exception.getProblemDetail();
      problem.instance = request.url;

      return response
        .status(problem.status)
        .header('Content-Type', 'application/problem+json')
        .json(problem);
    }

    // 예상치 못한 에러
    const status = exception instanceof HttpException
      ? exception.getStatus()
      : 500;

    return response
      .status(status)
      .header('Content-Type', 'application/problem+json')
      .json({
        type: 'https://api.example.com/problems/internal-error',
        title: 'Internal Server Error',
        status,
        detail: 'An unexpected error occurred.',
        instance: request.url,
      });
  }
}
```

사용 시:

```typescript
throw new ProblemException(
  {
    type: 'https://api.example.com/problems/payment/insufficient-balance',
    title: 'Insufficient Balance',
    detail: `현재 잔액 ${currentBalance}원으로는 ${requiredAmount}원 결제를 처리할 수 없습니다.`,
    currentBalance,
    requiredAmount,
  },
  HttpStatus.BAD_REQUEST,
);
```

## MSA에서 에러 전파 시 context 보존

MSA에서 서비스 A가 서비스 B를 호출하고 B에서 에러가 발생하면, A는 이 에러를 어떻게 클라이언트에 전달해야 하는가가 문제다.

세 가지 방식이 있다.

**1. 그대로 전파**: B의 에러를 A가 그대로 클라이언트에 전달한다. 클라이언트가 내부 서비스 구조를 알게 되는 단점이 있다. B의 에러 형식이 표준화되어 있지 않으면 더 심각하다.

**2. 래핑 전파**: A가 자신의 관점에서 새로운 에러를 만들고, B의 에러를 내부 context로 포함시킨다. 외부에서 보기엔 A의 에러로 보이지만 디버깅 시 B의 에러 정보도 확인할 수 있다.

**3. 완전 변환**: A가 B의 에러를 자신의 도메인 언어로 완전히 바꾼다. 캡슐화는 완전하지만 B에서 온 에러 정보가 소실될 수 있다.

실무에서는 2번 래핑 전파가 가장 많이 쓰인다. context 필드에 upstream 에러 정보를 담는다.

```json
{
  "type": "https://api.example.com/problems/order/payment-failed",
  "title": "Payment Failed",
  "status": 502,
  "detail": "결제 처리 중 오류가 발생했습니다.",
  "instance": "/orders/order-abc123",
  "traceId": "trace-xyz789",
  "context": {
    "upstream": "payment-service",
    "upstreamType": "https://payment.internal/problems/gateway-timeout",
    "upstreamTitle": "Payment Gateway Timeout",
    "upstreamInstance": "/payments/tx-def456"
  }
}
```

`context.upstream`으로 어떤 서비스에서 온 에러인지, `context.upstreamType`으로 원래 에러 유형을 보존한다. 로그에서 `traceId`로 전체 흐름을 추적할 수 있다.

주의할 점은 `context` 필드를 외부 클라이언트에 노출할 때다. 내부 서비스 명칭이나 구조가 드러나면 보안상 문제가 될 수 있다. 외부 API Gateway에서 `context` 필드를 제거하거나 내부 API와 외부 API의 에러 형식을 분리하는 방법을 쓴다.

```typescript
// Gateway 레벨 필터 예시
interface ProblemDetailPayload {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  context?: unknown;
  [key: string]: unknown;
}

function sanitizeForExternal(problem: ProblemDetailPayload): Omit<ProblemDetailPayload, 'context'> {
  const { context: _context, ...rest } = problem;
  // context 필드 제외 — 내부 서비스 정보 노출 방지
  return rest;
}
```

## 자주 겪는 문제들

**에러 응답인데 200 반환**: `{"success": false, "error": {...}}` 패턴에서 HTTP 상태 코드를 200으로 고정해두는 경우가 있다. 모바일 클라이언트가 상태 코드 파싱을 못해서 이렇게 만든 경우인데, 결국 Retrofit이나 Axios 같은 HTTP 클라이언트 라이브러리의 에러 인터셉터를 못 쓰게 된다. 표준 상태 코드를 써야 한다.

**detail에 스택 트레이스 포함**: 개발 환경에서는 편하지만 프로덕션에서 실수로 나가면 내부 구조가 노출된다. 환경별로 분리하거나 프로덕션에서는 완전히 제외한다.

**type URI가 실제로 존재하지 않음**: 클라이언트가 type URI에 접근했을 때 404가 나오면 혼란스럽다. 최소한 404 대신 해당 에러 타입의 설명 페이지를 반환하거나, URI 형식을 `urn:` 스킴으로 바꿔서 접근 불가 URI임을 명확히 한다.

```
urn:com.example:problems:payment:insufficient-balance
```

**instance URI 설계 미스**: `/payments/` 같이 컬렉션 URI를 instance로 쓰면 어떤 요청인지 특정할 수 없다. 가능하면 요청별 고유 URI나 트랜잭션 ID가 포함된 URI를 쓴다.
