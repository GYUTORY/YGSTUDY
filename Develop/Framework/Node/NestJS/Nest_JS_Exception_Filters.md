---
title: NestJS Exception Filters
tags:
  - nestjs
  - exception
  - error-handling
  - prisma
  - typeorm
  - sentry
updated: 2026-06-01
---

# NestJS Exception Filters

Exception Filter는 핸들러 내부에서 던져진 예외를 가로채서 HTTP 응답으로 변환하는 자리다. NestJS는 기본 필터(`BaseExceptionFilter`)를 가지고 있어서 아무것도 안 해도 어느 정도는 동작한다. `throw new BadRequestException()` 같은 걸 던지면 400 응답이 나가고, 그냥 `throw new Error()`를 던지면 500이 나간다. 여기까지는 누구나 안다.

문제는 운영 환경으로 넘어가면서 시작된다. Prisma가 던지는 `PrismaClientKnownRequestError`는 기본 필터에서 그대로 500이 된다. 유니크 제약 위반인지, 외래키 위반인지, 레코드 없음인지 모두 똑같이 500이다. 클라이언트는 자세한 이유를 받지 못하고, 백엔드 로그에는 스택 트레이스만 잔뜩 쌓인다. 비동기 핸들러에서 던진 예외가 어디로 흘러가는지, `setImmediate` 안에서 던진 예외가 왜 프로세스를 죽이는지도 헷갈리기 시작한다.

이 문서는 HttpException 계층의 구조부터 시작해서, 전역 필터를 어떻게 짜야 운영에서 흔히 만나는 케이스를 모두 잡을 수 있는지, ORM 에러를 HTTP 응답으로 어떻게 매핑하는지, Sentry 같은 외부 모니터링과 붙일 때 무엇이 어긋나는지를 정리한다.

## HttpException 계층 구조

NestJS의 모든 HTTP 예외는 `HttpException`을 상속한다. 이게 출발점이다.

```typescript
export class HttpException extends Error {
  constructor(
    response: string | Record<string, any>,
    status: number,
    options?: HttpExceptionOptions,
  );

  getResponse(): string | object;
  getStatus(): number;
  cause?: unknown;
}
```

`response`는 클라이언트에게 보낼 응답 본문이고, `status`는 HTTP 상태 코드다. `response`로 문자열을 주면 NestJS가 자동으로 `{ statusCode, message }` 형태로 감싸서 응답한다. 객체를 주면 그 객체를 그대로 응답으로 쓴다. 이 차이를 모르면 응답 포맷이 라우트마다 제각각이 되는 일이 생긴다.

`HttpException`을 직접 던지는 경우는 드물고, 보통은 NestJS가 미리 만들어둔 서브클래스를 쓴다. 자주 쓰는 것만 정리하면 다음과 같다.

| 클래스 | 상태 코드 | 의미 |
|---|---|---|
| `BadRequestException` | 400 | 요청이 잘못됨. ValidationPipe가 던지는 기본 예외 |
| `UnauthorizedException` | 401 | 인증 실패. JWT 만료, 토큰 없음 |
| `ForbiddenException` | 403 | 권한 없음. 인증은 됐지만 접근 권한 없음 |
| `NotFoundException` | 404 | 리소스 없음 |
| `ConflictException` | 409 | 충돌. 유니크 제약 위반에 자주 쓴다 |
| `UnprocessableEntityException` | 422 | 요청 형식은 맞지만 의미상 처리 불가 |
| `InternalServerErrorException` | 500 | 서버 내부 오류. 기본 fallback |
| `ServiceUnavailableException` | 503 | 서비스 일시 중단. 헬스체크 실패 등 |

401과 403의 구분을 잘못 쓰는 경우가 의외로 많다. 401은 "당신이 누구인지 모르겠다"이고, 403은 "당신이 누구인지는 아는데 이건 못 본다"다. JWT 토큰이 없으면 401, 토큰은 유효한데 admin 권한이 없으면 403이다. 이걸 헷갈리면 프론트엔드의 인증 흐름(토큰 재발급, 로그인 페이지 리다이렉트)이 꼬인다.

`UnprocessableEntityException`(422)도 자주 오용된다. 422는 요청 본문의 형식(JSON 파싱, 타입)은 맞는데 비즈니스 규칙상 처리할 수 없는 경우에 쓴다. 예를 들면 "이미 결제 완료된 주문을 다시 결제 요청"한 경우다. 형식 자체가 잘못된 경우(필수 필드 누락, 타입 불일치)는 400이다.

### 커스텀 예외 만들기

도메인 예외를 만들고 싶을 때 두 가지 선택지가 있다.

첫째, `HttpException`을 바로 상속한다.

```typescript
export class OrderAlreadyPaidException extends HttpException {
  constructor(orderId: string) {
    super(
      {
        errorCode: 'ORDER_ALREADY_PAID',
        message: '이미 결제 완료된 주문입니다',
        orderId,
      },
      HttpStatus.CONFLICT,
    );
  }
}
```

응답 본문에 `errorCode`를 박아두면 프론트에서 에러 분기가 깔끔해진다. 메시지 문자열로 분기하는 건 위험하다. 메시지가 바뀌는 순간 프론트의 분기 로직이 깨진다.

둘째, 도메인 계층에서는 NestJS와 무관한 순수 에러를 던지고, 인프라 경계(컨트롤러나 전역 필터)에서 HTTP로 변환한다.

```typescript
// 도메인 계층 - NestJS와 무관
export class DomainError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message);
  }
}

export class OrderAlreadyPaidError extends DomainError {
  constructor(public readonly orderId: string) {
    super('ORDER_ALREADY_PAID', '이미 결제 완료된 주문입니다');
  }
}
```

도메인 로직이 HTTP 프로토콜에 의존하지 않게 된다. 같은 도메인 코드를 gRPC나 큐 컨슈머에서 재사용할 때 HTTP 상태 코드가 끼어 있으면 어색하다. 단점은 어딘가에서 도메인 에러를 HTTP 상태로 매핑하는 코드가 한 번 더 필요하다는 점이다. 마이크로서비스나 멀티 프로토콜 환경이 아니라면 첫 번째 방식이 빠르다.

## 기본 필터의 동작과 한계

NestJS는 `BaseExceptionFilter`라는 전역 fallback을 기본으로 가진다. 이 필터의 동작은 단순하다.

- 던져진 게 `HttpException`이면 `getStatus()`와 `getResponse()`를 그대로 응답으로 내보낸다.
- 그렇지 않으면 500을 내보낸다. `process.env.NODE_ENV === 'production'`이면 "Internal server error" 같은 일반 메시지로, 개발 환경이면 스택 트레이스를 포함해서 응답에 박는다.

문제는 ORM 에러, validation 라이브러리 에러, 외부 SDK 에러가 모두 `HttpException`을 상속하지 않는다는 점이다. 그래서 기본 필터에 맡기면 전부 500이 된다. Prisma가 `P2002`(유니크 위반)을 던지든, `P2025`(레코드 없음)을 던지든, 클라이언트는 똑같은 500을 받는다.

또 하나 빠뜨리기 쉬운 점은 응답 포맷이 일관적이지 않다는 것이다. 기본 필터는 `HttpException`의 응답 본문을 가공 없이 그대로 넘긴다. 그래서 어떤 라우트는 `{ statusCode, message }` 형태이고, 어떤 라우트는 커스텀 객체가 그대로 내려간다. 클라이언트 입장에서 응답 스키마가 라우트마다 다른 셈이다. 운영 들어가서 모니터링 대시보드를 짜려고 보면 이게 발목을 잡는다.

## 전역 예외 필터 구현

전역 필터는 모든 예외를 한 곳에서 받아서 응답 포맷을 통일하고, 로깅하고, 필요하면 외부 시스템으로 보내는 단일 진입점 역할을 한다. 기본 형태는 다음과 같다.

```typescript
import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(GlobalExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    const { status, body } = this.toHttpResponse(exception);

    this.log(exception, request, status);

    response.status(status).json({
      ...body,
      path: request.url,
      timestamp: new Date().toISOString(),
      requestId: request.headers['x-request-id'],
    });
  }

  private toHttpResponse(exception: unknown): {
    status: number;
    body: Record<string, any>;
  } {
    if (exception instanceof HttpException) {
      const res = exception.getResponse();
      const body =
        typeof res === 'string'
          ? { message: res }
          : (res as Record<string, any>);

      return {
        status: exception.getStatus(),
        body: {
          errorCode: body.errorCode ?? 'HTTP_EXCEPTION',
          message: body.message ?? exception.message,
        },
      };
    }

    return {
      status: HttpStatus.INTERNAL_SERVER_ERROR,
      body: {
        errorCode: 'INTERNAL_SERVER_ERROR',
        message: '서버 내부 오류가 발생했습니다',
      },
    };
  }

  private log(exception: unknown, request: Request, status: number): void {
    const message = `${request.method} ${request.url} -> ${status}`;

    if (status >= 500) {
      this.logger.error(
        message,
        exception instanceof Error ? exception.stack : exception,
      );
    } else if (status >= 400) {
      this.logger.warn(message);
    }
  }
}
```

`@Catch()`를 인자 없이 쓰면 모든 예외를 잡는다. 특정 예외만 잡고 싶으면 `@Catch(PrismaClientKnownRequestError)`처럼 지정할 수 있다. 필터 여러 개를 등록하면 더 좁은 타입의 필터가 먼저 매칭된다.

`ArgumentsHost`를 거쳐서 Express의 `Request`/`Response` 객체를 꺼낸다. Fastify를 쓰는 경우 객체 타입만 다르고 흐름은 같다. WebSocket이나 gRPC에서도 같은 필터가 호출될 수 있어서, HTTP 컨텍스트가 아닌 경우의 처리도 필요하면 분기해야 한다.

```typescript
catch(exception: unknown, host: ArgumentsHost): void {
  if (host.getType() !== 'http') {
    // WebSocket이나 RPC 컨텍스트는 별도 처리
    return;
  }
  // ...
}
```

### 등록 방법

전역 필터를 등록하는 방법이 두 가지인데, 결과가 다르다.

```typescript
// 방법 1: main.ts
const app = await NestFactory.create(AppModule);
app.useGlobalFilters(new GlobalExceptionFilter());
```

```typescript
// 방법 2: 모듈 provider
@Module({
  providers: [
    {
      provide: APP_FILTER,
      useClass: GlobalExceptionFilter,
    },
  ],
})
export class AppModule {}
```

방법 1은 인스턴스를 직접 만들어서 등록하기 때문에 DI 컨테이너 밖에 있다. 그래서 필터 안에서 다른 서비스(예: Logger, ConfigService)를 주입받을 수 없다. 방법 2는 DI 컨테이너 안에서 인스턴스화되어 주입이 가능하다. 외부 모니터링 SDK나 ConfigService를 쓸 거면 무조건 방법 2를 써야 한다.

이걸 모르고 main.ts에서 `new`로 만들면, 필터 안에서 `this.configService`가 undefined이고 디버깅에 한참 헤맨다.

## ORM 에러 매핑

Prisma와 TypeORM이 던지는 에러를 HTTP 응답으로 매핑하는 게 실무에서 가장 자주 만나는 케이스다.

### Prisma 에러 매핑

Prisma는 알려진 에러를 `PrismaClientKnownRequestError`로 감싸서 던지고, 에러 코드(`P2002`, `P2025` 등)로 종류를 구분한다. 자주 만나는 코드는 다음과 같다.

| 코드 | 의미 | 매핑할 HTTP 상태 |
|---|---|---|
| `P2002` | 유니크 제약 위반 | 409 Conflict |
| `P2003` | 외래키 제약 위반 | 400 Bad Request |
| `P2025` | 작업 대상 레코드 없음 (update, delete) | 404 Not Found |
| `P2000` | 컬럼 길이 초과 | 400 Bad Request |
| `P2014` | 관계 위반 | 400 Bad Request |

전역 필터에 매핑 로직을 추가하면 된다.

```typescript
import { Prisma } from '@prisma/client';

private mapPrismaError(
  exception: Prisma.PrismaClientKnownRequestError,
): { status: number; body: Record<string, any> } {
  switch (exception.code) {
    case 'P2002': {
      const target = (exception.meta?.target as string[])?.join(', ');
      return {
        status: HttpStatus.CONFLICT,
        body: {
          errorCode: 'UNIQUE_CONSTRAINT_VIOLATION',
          message: `중복된 값이 존재합니다: ${target}`,
          field: target,
        },
      };
    }
    case 'P2025':
      return {
        status: HttpStatus.NOT_FOUND,
        body: {
          errorCode: 'RECORD_NOT_FOUND',
          message: '대상 레코드를 찾을 수 없습니다',
        },
      };
    case 'P2003':
      return {
        status: HttpStatus.BAD_REQUEST,
        body: {
          errorCode: 'FOREIGN_KEY_VIOLATION',
          message: '참조하는 레코드가 존재하지 않습니다',
        },
      };
    default:
      return {
        status: HttpStatus.INTERNAL_SERVER_ERROR,
        body: {
          errorCode: `PRISMA_${exception.code}`,
          message: '데이터베이스 처리 중 오류가 발생했습니다',
        },
      };
  }
}
```

Prisma 에러 메시지를 그대로 클라이언트에 노출하는 건 위험하다. 메시지에 테이블명, 컬럼명, 제약 조건 이름이 그대로 들어 있다. 운영 DB의 스키마 정보가 외부로 새어 나가는 셈이다. 위 예처럼 `meta.target`은 가공해서 필요한 필드명만 노출하고, 메시지는 사람이 읽기 좋은 한국어로 다시 쓰는 게 맞다.

`PrismaClientValidationError`(타입 불일치)와 `PrismaClientInitializationError`(연결 실패)도 따로 처리해야 한다. 후자는 500보다는 503(`ServiceUnavailableException`)이 맞다. 헬스체크 로직과 묶여서 모니터링되는 경우가 많다.

### TypeORM 에러 매핑

TypeORM은 Prisma보다 에러 분류가 덜 체계적이다. 드라이버가 던지는 에러를 그대로 노출하거나, `QueryFailedError`로 감싸서 던진다. DB 종류(MySQL, PostgreSQL)에 따라 에러 코드가 다르다.

```typescript
import { QueryFailedError } from 'typeorm';

private mapTypeOrmError(
  exception: QueryFailedError,
): { status: number; body: Record<string, any> } {
  const driverError = (exception as any).driverError;
  const code = driverError?.code;

  // PostgreSQL 에러 코드
  if (code === '23505') {
    return {
      status: HttpStatus.CONFLICT,
      body: {
        errorCode: 'UNIQUE_CONSTRAINT_VIOLATION',
        message: '중복된 값이 존재합니다',
      },
    };
  }
  if (code === '23503') {
    return {
      status: HttpStatus.BAD_REQUEST,
      body: {
        errorCode: 'FOREIGN_KEY_VIOLATION',
        message: '참조하는 레코드가 존재하지 않습니다',
      },
    };
  }

  // MySQL 에러 코드 (ER_DUP_ENTRY, ER_NO_REFERENCED_ROW_2)
  if (code === 'ER_DUP_ENTRY') {
    return {
      status: HttpStatus.CONFLICT,
      body: { errorCode: 'UNIQUE_CONSTRAINT_VIOLATION', message: '중복' },
    };
  }

  return {
    status: HttpStatus.INTERNAL_SERVER_ERROR,
    body: {
      errorCode: 'DATABASE_ERROR',
      message: '데이터베이스 처리 중 오류가 발생했습니다',
    },
  };
}
```

`(exception as any).driverError`로 캐스팅하는 부분이 거슬리지만 TypeORM의 타입 정의가 driver별로 정확하지 않아서 어쩔 수 없다. DB 종류가 정해져 있다면 인터페이스를 좁혀서 타입을 정의해두면 깔끔해진다.

TypeORM의 `EntityNotFoundError`는 `findOneOrFail`이 던진다. 이걸 잡아서 404로 변환하면 컨트롤러 코드가 단순해진다.

```typescript
import { EntityNotFoundError } from 'typeorm';

if (exception instanceof EntityNotFoundError) {
  return {
    status: HttpStatus.NOT_FOUND,
    body: {
      errorCode: 'RECORD_NOT_FOUND',
      message: '대상 레코드를 찾을 수 없습니다',
    },
  };
}
```

### 전체 매핑을 합친 필터

전역 필터의 `toHttpResponse` 메서드를 다음처럼 확장한다.

```typescript
private toHttpResponse(exception: unknown) {
  if (exception instanceof HttpException) {
    return this.mapHttpException(exception);
  }
  if (exception instanceof Prisma.PrismaClientKnownRequestError) {
    return this.mapPrismaError(exception);
  }
  if (exception instanceof Prisma.PrismaClientValidationError) {
    return {
      status: HttpStatus.BAD_REQUEST,
      body: {
        errorCode: 'PRISMA_VALIDATION_ERROR',
        message: '요청 파라미터가 올바르지 않습니다',
      },
    };
  }
  if (exception instanceof EntityNotFoundError) {
    return {
      status: HttpStatus.NOT_FOUND,
      body: { errorCode: 'RECORD_NOT_FOUND', message: '대상 없음' },
    };
  }
  if (exception instanceof QueryFailedError) {
    return this.mapTypeOrmError(exception);
  }
  return {
    status: HttpStatus.INTERNAL_SERVER_ERROR,
    body: {
      errorCode: 'INTERNAL_SERVER_ERROR',
      message: '서버 내부 오류가 발생했습니다',
    },
  };
}
```

`instanceof` 체크 순서가 중요하다. 좁은 타입을 먼저 체크해야 한다. `HttpException`을 상속한 커스텀 예외를 먼저 잡고, 그 다음 ORM 에러, 마지막에 fallback이다.

## 로깅 통합

운영 환경에서 예외 필터의 로깅은 두 가지를 만족해야 한다. 첫째, 4xx와 5xx를 구분해서 로그 레벨을 다르게 가져간다. 둘째, 로그에 요청 컨텍스트(URL, requestId, userId)가 포함되어야 추적이 가능하다.

```typescript
private log(
  exception: unknown,
  request: Request,
  status: number,
): void {
  const requestId = request.headers['x-request-id'] as string;
  const userId = (request as any).user?.id;

  const context = {
    method: request.method,
    url: request.url,
    requestId,
    userId,
    status,
  };

  if (status >= 500) {
    this.logger.error(
      `Unhandled exception: ${this.getErrorMessage(exception)}`,
      exception instanceof Error ? exception.stack : undefined,
      JSON.stringify(context),
    );
  } else if (status >= 400 && status !== 404) {
    // 404는 너무 시끄러워서 보통 제외
    this.logger.warn(this.getErrorMessage(exception), JSON.stringify(context));
  }
}

private getErrorMessage(exception: unknown): string {
  if (exception instanceof HttpException) {
    const res = exception.getResponse();
    return typeof res === 'string'
      ? res
      : (res as any).message ?? exception.message;
  }
  if (exception instanceof Error) {
    return exception.message;
  }
  return 'Unknown exception';
}
```

4xx를 전부 ERROR 레벨로 찍으면 로그가 폭발한다. ValidationPipe가 던지는 400이 정상 사용자 흐름에서도 자주 나오는데 이게 다 ERROR로 쌓이면 진짜 에러가 묻힌다. 보통 4xx는 WARN, 5xx는 ERROR로 가져간다. 404는 사람이 의도적으로 찔러보는 경우가 많아서 WARN조차 빼는 곳도 많다.

`request.headers['x-request-id']`는 인입 게이트웨이나 ALB에서 박아주는 헤더다. 없으면 미들웨어에서 `uuid`로 만들어서 박는다. 마이크로서비스로 갈수록 이게 없으면 분산 트레이싱이 불가능해진다.

### 로그 포맷

운영에서는 JSON 로그 포맷이 거의 표준이다. CloudWatch Logs Insights, Datadog, Loki 같은 도구가 모두 JSON 필드 기반으로 검색한다. NestJS 기본 Logger를 그대로 쓰면 사람 읽기 좋은 텍스트 포맷이라 운영에서 곤란해진다. Winston이나 Pino로 갈아끼우는 게 보통이다.

```typescript
// pino 기반 로거를 주입받는 예
constructor(
  @Inject(PINO_LOGGER) private readonly pinoLogger: Logger,
) {}

// 필터 안에서
this.pinoLogger.error(
  {
    err: exception,
    method: request.method,
    url: request.url,
    requestId,
    userId,
    status,
  },
  'Unhandled exception',
);
```

pino는 `err` 필드에 에러 객체를 넣으면 자동으로 직렬화한다. 스택 트레이스를 JSON 필드로 떨궈주기 때문에 검색이 편하다. NestJS의 `Logger`를 직접 쓰면 스택 트레이스가 메시지에 박혀서 검색이 안 된다.

## 비동기 에러 처리 패턴

NestJS 핸들러는 async 함수다. 핸들러 안에서 `throw`하거나 reject된 Promise를 반환하면 필터가 자동으로 잡는다. 여기까지는 자연스럽다.

문제는 핸들러 바깥의 비동기 경로다.

### setImmediate, setTimeout 안에서 던진 예외

```typescript
@Get()
async problematic() {
  setImmediate(() => {
    throw new Error('이건 어디로 갈까');
  });
  return { ok: true };
}
```

이 예외는 NestJS의 필터로 가지 않는다. Node.js의 이벤트 루프 콜백 안에서 던져진 예외는 핸들러의 컨텍스트를 이미 벗어났기 때문에 try/catch도 못 잡고, 결국 `process.on('uncaughtException')`으로 흘러간다. 기본 동작은 프로세스가 죽는다.

콜백 안에서 작업이 필요하면 다음처럼 감싸야 한다.

```typescript
setImmediate(async () => {
  try {
    await someAsyncWork();
  } catch (err) {
    this.logger.error('Background work failed', err);
  }
});
```

더 나은 방법은 백그라운드 작업을 큐(BullMQ 같은)로 보내는 것이다. 응답 라이프사이클이 끝난 뒤에 돌아야 하는 작업을 핸들러 안에서 fire-and-forget으로 띄우면 에러 처리, 재시도, 모니터링이 전부 빠진다.

### Promise를 await 안 하기

```typescript
@Post()
async create(@Body() dto: CreateDto) {
  const result = await this.service.create(dto);
  this.service.sendNotification(result.id); // await 안 함
  return result;
}
```

`sendNotification`에서 던진 에러는 unhandled promise rejection이 된다. Node.js 15부터는 기본 동작이 프로세스 종료다. await을 빼먹지 않는 게 가장 단순한 답이지만, 응답 시간 때문에 정말로 fire-and-forget이 필요한 경우엔 명시적으로 처리한다.

```typescript
this.service
  .sendNotification(result.id)
  .catch((err) => this.logger.error('Notification failed', err));
```

### 핸들러가 Observable을 반환할 때

NestJS는 Observable 반환도 지원한다. RxJS 스트림 안에서 에러가 던져지면 NestJS가 잡아서 필터로 보낸다.

```typescript
@Get()
findAll(): Observable<User[]> {
  return this.userService.findAll().pipe(
    map(users => users.filter(u => u.active)),
    catchError(err => throwError(() => new InternalServerErrorException())),
  );
}
```

`catchError`로 변환하지 않고 그대로 흘려보내도 NestJS가 잡는다. 다만 RxJS 에러는 스택 트레이스가 얕아서 디버깅이 어렵다. 가능하면 비즈니스 로직에서 명확한 HttpException으로 바꿔주는 게 낫다.

## 전체 흐름

요청부터 응답까지의 에러 처리 흐름을 정리하면 다음과 같다.

```mermaid
sequenceDiagram
    participant C as Client
    participant H as Handler
    participant S as Service
    participant DB as Database
    participant F as Global Filter
    participant L as Logger
    participant M as Monitor

    C->>H: POST /orders
    H->>S: createOrder()
    S->>DB: prisma.order.create()
    DB-->>S: P2002 (unique violation)
    S-->>H: throws PrismaClientKnownRequestError
    H-->>F: 핸들러 밖으로 던져짐
    F->>F: instanceof 분기
    F->>L: warn 로그 기록
    F->>M: Sentry 전송 (5xx만)
    F-->>C: 409 Conflict
```

5xx만 Sentry로 보내는 분기에 주목해라. 4xx는 클라이언트 잘못이거나 정상적인 비즈니스 흐름인 경우가 많아서 전부 외부 모니터링으로 보내면 노이즈가 폭발한다.

## Sentry 연동 시 주의점

Sentry 같은 에러 트래커를 붙일 때 흔히 놓치는 게 있다.

### 4xx까지 전부 보내면 안 된다

기본적으로 5xx만 Sentry로 보내야 한다. 4xx는 클라이언트의 잘못된 요청, validation 실패, 인증 실패 같은 정상 흐름이 대부분이다. 이걸 전부 Sentry로 보내면 한 달 안에 Sentry 요금이 폭발한다. 게다가 진짜 봐야 할 5xx가 4xx 노이즈에 묻혀서 안 보인다.

```typescript
private async reportToSentry(
  exception: unknown,
  request: Request,
  status: number,
): Promise<void> {
  if (status < 500) return;
  // 예외 중에서도 의도적으로 던진 5xx는 제외할 수 있음
  if (exception instanceof ServiceUnavailableException) return;

  Sentry.withScope((scope) => {
    scope.setTag('method', request.method);
    scope.setTag('url', request.url);
    scope.setUser({ id: (request as any).user?.id });
    scope.setContext('request', {
      headers: this.sanitizeHeaders(request.headers),
      query: request.query,
    });
    Sentry.captureException(exception);
  });
}
```

### PII와 시크릿 마스킹

요청 헤더와 본문에 인증 토큰, 비밀번호, 개인정보가 들어있다. Sentry로 그대로 보내면 외부 서비스에 민감 정보가 쌓인다. GDPR이나 개인정보보호법 이슈로 번질 수 있다.

```typescript
private sanitizeHeaders(headers: Record<string, any>): Record<string, any> {
  const sensitive = ['authorization', 'cookie', 'x-api-key'];
  const cleaned = { ...headers };
  for (const key of sensitive) {
    if (cleaned[key]) cleaned[key] = '[REDACTED]';
  }
  return cleaned;
}
```

요청 본문도 마찬가지다. `password`, `pin`, `ssn`, `card_number` 같은 키는 무조건 마스킹한다. Sentry SDK 자체에 `beforeSend` 훅이 있어서 거기서 일괄 처리하는 게 더 안전하다. 필터에서 누락해도 SDK 레벨에서 한 번 더 거른다.

```typescript
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers['authorization'];
      delete event.request.headers['cookie'];
    }
    return event;
  },
});
```

### 같은 에러 그룹화

Sentry는 스택 트레이스와 메시지로 에러를 그룹화한다. 그런데 메시지에 동적인 값(주문 ID, 사용자 ID)이 들어가면 같은 종류의 에러가 매번 다른 그룹으로 잡힌다. 그룹이 폭발하면 알림이 무용지물이 된다.

```typescript
// 안 좋은 예: 매번 다른 그룹
throw new InternalServerErrorException(
  `결제 처리 실패: orderId=${orderId}, amount=${amount}`,
);

// 좋은 예: 메시지는 고정, 동적 값은 extra로
Sentry.withScope((scope) => {
  scope.setExtras({ orderId, amount });
  Sentry.captureException(new PaymentProcessingError());
});
```

전역 필터에서 메시지를 정규화하거나, `fingerprint`를 명시적으로 지정해서 그룹화 키를 통제하는 방법도 있다.

```typescript
scope.setFingerprint(['payment-error', exception.code ?? 'unknown']);
```

### 비동기 전송이 응답을 늦추면 안 된다

`Sentry.captureException`은 동기 호출처럼 보이지만 내부적으로 큐에 쌓이고 비동기 전송된다. 응답을 보내기 전에 `await Sentry.flush(2000)`를 하면 응답이 그만큼 지연된다. 짧은 핸들러일수록 체감이 크다.

Sentry 전송은 fire-and-forget으로 두고, 프로세스가 종료되기 전에만 flush한다. AWS Lambda 같은 환경이라면 handler 종료 직전에 flush가 필요할 수 있다. 일반 컨테이너라면 SIGTERM 핸들러에 flush를 걸어두면 된다.

```typescript
process.on('SIGTERM', async () => {
  await Sentry.flush(5000);
  process.exit(0);
});
```

### 운영 환경만 켜기

로컬 개발 환경에서 Sentry로 에러가 가면 노이즈도 노이즈고, 개발 중인 에러가 외부 시스템에 쌓이는 게 보안상 좋지 않다. `enabled` 옵션으로 환경별 분기를 명확히 한다.

```typescript
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  enabled: process.env.NODE_ENV === 'production',
  environment: process.env.NODE_ENV,
  release: process.env.APP_VERSION,
});
```

`release`는 배포 버전과 묶이는 키다. Sentry에서 "이 에러가 어떤 버전부터 등장했나"를 볼 때 쓰는데, 이게 없으면 회귀 추적이 안 된다. CI에서 빌드할 때 git SHA나 태그를 박아주는 게 흔하다.

## 컨트롤러/메서드 단위 필터

전역 필터로 대부분 해결되지만 특정 컨트롤러나 메서드에만 다른 처리가 필요한 경우가 있다.

```typescript
@Controller('webhooks')
@UseFilters(WebhookExceptionFilter)
export class WebhookController {
  // 웹훅은 200을 반환하지 않으면 외부에서 재시도하므로
  // 실패해도 200을 주고 내부적으로 알림만 보내는 등의 처리
}
```

웹훅 컨트롤러가 대표적이다. Stripe나 GitHub 웹훅은 200이 아니면 재시도하는데, 처리 중 에러가 났다고 500을 보내면 무한 재시도가 돌아간다. 그래서 웹훅 전용 필터로 200을 강제하고 내부 로깅만 하는 패턴이 흔하다.

`@UseFilters`로 메서드에 붙이면 그 메서드만 다른 필터를 탄다. 우선순위는 메서드 → 컨트롤러 → 전역 순서다.

## 실무 체크포인트

전역 필터를 처음 짜고 운영에 올리면 보통 다음 순서로 문제가 드러난다.

1. 응답 포맷이 라우트마다 다르다. 어떤 건 `{ statusCode, message }`, 어떤 건 `{ errorCode, message }`. 클라이언트가 분기 코드를 만들기 어렵다. 전역 필터에서 응답 포맷을 강제 통일한다.
2. 500 응답에 스택 트레이스가 그대로 노출된다. 운영 빌드에서는 무조건 일반 메시지로 마스킹한다.
3. ValidationPipe의 400 응답이 너무 자세하다. 클래스 validator 메시지를 그대로 노출하면 내부 DTO 필드명이 다 보인다. 필요하면 응답 가공이 필요하다.
4. Prisma 에러가 500으로 잡혀서 클라이언트가 재시도 로직을 안 탄다. 적절한 4xx로 변환해야 클라이언트의 에러 처리가 동작한다.
5. Sentry에 4xx까지 다 보내서 쿼터를 다 쓴다. 5xx만 보내고, 그 안에서도 ServiceUnavailable처럼 의도된 5xx는 제외한다.
6. 비동기 콜백 안의 에러가 프로세스를 죽인다. `uncaughtException`, `unhandledRejection` 핸들러를 등록해서 최소한 로그라도 남기게 한다.

전역 필터는 한 번 잘 짜두면 오래 간다. 다만 도메인 예외 → HTTP 매핑 테이블이 늘어날수록 필터 안의 분기가 비대해진다. 매핑 로직을 별도 서비스로 빼서 주입받게 만들면 테스트도 쉽고 변경도 단순해진다.
