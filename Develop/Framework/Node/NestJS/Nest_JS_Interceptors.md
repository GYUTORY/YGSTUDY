---
title: NestJS Interceptor 동작 원리와 실무 활용
tags: [nestjs, interceptor, rxjs, aop, observable, node]
updated: 2026-06-06
---

# NestJS Interceptor 동작 원리와 실무 활용

NestJS에서 Interceptor는 핸들러의 앞뒤를 감싸는 레이어다. 자바 Spring의 AOP나 Express의 미들웨어를 다뤄봤다면 비슷한 인상을 받을 텐데, 결정적인 차이가 하나 있다. NestJS Interceptor는 RxJS Observable 위에서 동작한다. 핸들러의 반환값이 Observable 스트림으로 흘러나오고, Interceptor는 그 스트림을 가로채서 변환한다. 이 메커니즘이 익숙하지 않으면 응답 가공, 타임아웃, 캐싱 같은 패턴을 짤 때 매번 막힌다.

이 문서는 Interceptor가 실제로 어떻게 호출되는지, RxJS 파이프라인이 응답을 어떻게 흘려보내는지부터 짚고, 운영하면서 부딪힌 케이스 위주로 정리한다.

## Interceptor가 풀어주는 문제

같은 동작을 여러 컨트롤러에서 반복하면 코드가 갈수록 더러워진다. 모든 응답에 timestamp를 박고 싶다든지, 모든 핸들러 호출 시간을 측정하고 싶다든지, 특정 DB 에러를 도메인 예외로 변환하고 싶다든지. 핸들러 안에 try/catch와 시간 측정 코드를 매번 쓰는 건 5명짜리 서비스에서도 금방 한계가 온다.

Interceptor는 이 횡단 관심사(cross-cutting concern)를 한 곳으로 모은다. Express 미들웨어로도 비슷하게 할 수 있지만 미들웨어는 응답을 다루기 어렵다. `res.send`를 후킹하거나, 응답 객체를 monkey-patch해야 한다. Interceptor는 응답이 Observable로 흘러나오는 시점에 자연스럽게 개입할 수 있도록 설계되어 있다.

## Interceptor의 구조

모든 Interceptor는 `NestInterceptor` 인터페이스를 구현한다. 메서드는 `intercept` 하나뿐이다.

```typescript
import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class SampleInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    // next.handle() 호출 전: before 로직
    return next.handle().pipe(
      // next.handle() 호출 후: after 로직
    );
  }
}
```

`context`는 ExecutionContext로 HTTP, WebSocket, gRPC 어떤 트랜스포트인지 추상화된 정보를 들고 있다. `next`는 CallHandler인데 여기서 `handle()`을 호출해야 실제 핸들러 체인이 실행된다. `handle()`을 부르지 않으면 컨트롤러는 영원히 실행되지 않는다.

핵심은 `handle()`이 반환하는 값이 Observable이라는 점이다. 컨트롤러가 `return user;` 처럼 평범한 객체를 반환하더라도 NestJS 내부에서 자동으로 Observable로 감싼다. Promise를 반환해도 마찬가지다. 그래서 Interceptor에서는 `.pipe()` 안에 RxJS 연산자를 연결해서 응답을 가공하면 된다.

### ExecutionContext에서 꺼낼 수 있는 것

`ExecutionContext`는 `ArgumentsHost`를 확장한 인터페이스다. 트랜스포트 타입에 따라 다른 방식으로 접근해야 한다.

```typescript
intercept(context: ExecutionContext, next: CallHandler) {
  const type = context.getType(); // 'http' | 'ws' | 'rpc'

  if (type === 'http') {
    const req = context.switchToHttp().getRequest();
    const res = context.switchToHttp().getResponse();
  } else if (type === 'ws') {
    const client = context.switchToWs().getClient();
    const data = context.switchToWs().getData();
  } else if (type === 'rpc') {
    const data = context.switchToRpc().getData();
  }

  // 메타데이터, 핸들러, 클래스 정보
  const handler = context.getHandler();
  const controller = context.getClass();

  return next.handle();
}
```

`getHandler()`와 `getClass()`는 데코레이터로 붙인 메타데이터를 읽을 때 자주 쓴다. `Reflector`와 같이 쓰면 핸들러에 붙은 커스텀 데코레이터 값을 꺼내서 분기할 수 있다.

```typescript
import { Reflector } from '@nestjs/core';

constructor(private reflector: Reflector) {}

intercept(context: ExecutionContext, next: CallHandler) {
  const cacheTtl = this.reflector.get<number>('cache-ttl', context.getHandler());
  // cacheTtl이 없으면 캐싱 안 함
}
```

## 실행 순서: 가드, 파이프와의 관계

요청이 들어오면 Middleware → Guard → Interceptor(before) → Pipe → Handler → Interceptor(after) → Exception Filter 순으로 흐른다. 헷갈리는 부분이 둘 있다.

첫째, Interceptor의 before 단계는 Pipe보다 먼저 실행된다. 즉 파라미터 검증/변환이 끝나기 전에 Interceptor가 동작한다. 그래서 Interceptor에서 `request.body`를 읽을 때는 DTO 변환이 안 된 raw 값이다. ValidationPipe 통과 후의 값을 다루려면 메서드 데코레이터로 감는 게 아니라 응답 단계에서 처리해야 한다.

둘째, Interceptor의 after 단계는 등록 순서의 역순으로 풀린다. 스택처럼 쌓였다가 빠진다. 글로벌 → 컨트롤러 → 메서드 순으로 들어왔다면, 응답은 메서드 → 컨트롤러 → 글로벌 순으로 빠져나간다. 응답에 메타데이터를 덮어쓰는 경우 누가 마지막에 덮어쓰는지 헷갈리면 디버깅이 길어진다.

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Guard
    participant IB as Interceptor before
    participant P as Pipe
    participant H as Handler
    participant IA as Interceptor after
    participant EF as Exception Filter

    C->>G: Request
    G->>IB: canActivate 통과
    IB->>P: next.handle 호출
    P->>H: 파라미터 변환 완료
    H-->>IA: 반환값 Observable
    IA-->>C: 응답 가공 후 전달
    Note over IA,EF: 예외 발생 시 Filter로 분기
```

## next.handle()의 내부 흐름

Interceptor를 여러 개 걸었을 때 `next.handle()`이 어떻게 합성되는지 이해해두면 디버깅이 빨라진다. NestJS는 등록된 Interceptor들을 안쪽에서 바깥쪽으로 감싸 들어간다. 가장 안쪽 `CallHandler`는 컨트롤러 핸들러를 호출하는 함수다. 각 Interceptor는 그 핸들러를 받아서 자신의 `intercept`를 호출하고, 자신의 `intercept`가 반환한 Observable을 새로운 핸들러로 만들어 다음 Interceptor에 넘긴다.

대략 이런 구조다.

```typescript
// NestJS 내부 동작을 단순화한 의사 코드
function buildChain(interceptors: NestInterceptor[], handler: () => Observable<any>) {
  return interceptors.reduceRight<CallHandler>(
    (nextHandler, current) => ({
      handle: () => current.intercept(context, nextHandler),
    }),
    { handle: handler },
  );
}

const chain = buildChain([globalI, controllerI, methodI], runActualHandler);
chain.handle().subscribe(/* HTTP 응답 전송 */);
```

이 합성 구조에서 두 가지가 명확해진다.

첫째, before 단계(즉 `next.handle()` 호출 전 코드)는 글로벌 → 컨트롤러 → 메서드 순으로 차례대로 실행된다. 바깥쪽 Interceptor의 `intercept`가 먼저 호출되기 때문이다. 둘째, after 단계는 정반대다. `.pipe()`로 연결한 연산자는 가장 안쪽 Observable이 값을 흘려보낸 후에 그 위에서 동작하므로 메서드 → 컨트롤러 → 글로벌 순으로 적용된다.

응답 값을 `map`으로 두 번 가공하는 두 개의 Interceptor를 글로벌과 메서드에 걸었을 때, 메서드 Interceptor가 먼저 값을 변환하고 글로벌 Interceptor가 그 결과를 다시 받는다. 응답 형식이 의도와 다르게 나온다면 이 순서를 먼저 의심한다.

## RxJS 파이프라인이 응답을 다루는 방식

Interceptor가 RxJS 기반이라는 건 단순한 트리비아가 아니다. 응답 변환 코드 작성 방식 자체가 달라진다. 자주 쓰는 연산자는 `tap`, `map`, `catchError`, `timeout`이다.

### tap: 부수 효과만 일으킬 때

`tap`은 스트림을 통과시키면서 부수 효과만 일으킨다. 응답 값을 바꾸지 않고 로깅만 하고 싶을 때 쓴다.

```typescript
import { tap } from 'rxjs/operators';

intercept(context: ExecutionContext, next: CallHandler) {
  const startedAt = Date.now();
  return next.handle().pipe(
    tap(() => {
      const elapsed = Date.now() - startedAt;
      console.log(`elapsed=${elapsed}ms`);
    }),
  );
}
```

`map`을 잘못 쓰면 응답을 통째로 덮어버리는 사고가 난다. 로깅 의도라면 반드시 `tap`을 쓴다.

`tap`은 옵저버 객체 형태로 next/error/complete 콜백을 분리해서 받을 수도 있다. 로깅처럼 성공/실패 양쪽을 다뤄야 한다면 이 형태가 깔끔하다.

```typescript
return next.handle().pipe(
  tap({
    next: (value) => this.logger.log(`성공: ${JSON.stringify(value).slice(0, 100)}`),
    error: (err) => this.logger.error(`실패: ${err.message}`),
    complete: () => this.logger.log('완료'),
  }),
);
```

### map: 응답을 가공할 때

응답 구조를 표준화할 때 쓴다. 예를 들어 모든 응답을 `{ data, timestamp }` 형태로 감싸고 싶을 때다.

```typescript
import { map } from 'rxjs/operators';

intercept(context: ExecutionContext, next: CallHandler) {
  return next.handle().pipe(
    map((data) => ({
      data,
      timestamp: new Date().toISOString(),
    })),
  );
}
```

여기서 주의할 점이 있다. 컨트롤러가 `void`를 반환하거나 `res.json()`을 직접 호출해서 응답을 처리하는 경우 `map`이 동작하지 않는다. NestJS는 핸들러 반환값이 `undefined`이거나 사용자가 직접 응답을 보낸 경우 Interceptor의 변환 결과를 무시한다.

### catchError: 예외를 가로챌 때

핸들러나 다른 Interceptor에서 던진 예외를 잡을 수 있다. 단, 여기서 잡은 예외를 처리하는 방식이 Exception Filter와 충돌하는 게 실무에서 가장 자주 만나는 함정이다.

```typescript
import { catchError, throwError } from 'rxjs';
import { BadRequestException } from '@nestjs/common';

intercept(context: ExecutionContext, next: CallHandler) {
  return next.handle().pipe(
    catchError((err) => {
      if (err.code === 'ER_DUP_ENTRY') {
        return throwError(() => new BadRequestException('중복된 항목'));
      }
      return throwError(() => err);
    }),
  );
}
```

`throwError(() => err)`로 다시 던지면 Exception Filter가 받아서 처리한다. 그냥 `throw`로 던지면 Observable 컨텍스트를 벗어나서 unhandled rejection으로 흐를 수 있다. 반드시 `throwError`로 감싼다.

### timeout: 응답 시간 제한

```typescript
import { timeout, catchError, throwError } from 'rxjs';
import { RequestTimeoutException } from '@nestjs/common';

intercept(context: ExecutionContext, next: CallHandler) {
  return next.handle().pipe(
    timeout(5000),
    catchError((err) => {
      if (err.name === 'TimeoutError') {
        return throwError(() => new RequestTimeoutException());
      }
      return throwError(() => err);
    }),
  );
}
```

`timeout`만 걸면 RxJS의 `TimeoutError`가 그대로 전파된다. 클라이언트에 의미 있는 HTTP 응답을 주려면 `catchError`로 잡아서 `RequestTimeoutException`으로 변환해야 한다.

### switchMap / concatMap: 비동기 작업을 합성할 때

`intercept` 안에서 비동기 작업이 먼저 끝나야 핸들러를 호출할 수 있는 경우가 있다. 외부 토큰을 검증하거나, 캐시 키를 비동기로 만들어야 할 때다. Promise를 직접 await하지 말고 RxJS로 합성한다.

```typescript
import { from, switchMap } from 'rxjs';

intercept(context: ExecutionContext, next: CallHandler) {
  return from(this.tokenService.resolveUser(context)).pipe(
    switchMap((user) => {
      context.switchToHttp().getRequest().user = user;
      return next.handle();
    }),
  );
}
```

`switchMap`은 직전 Observable이 끝나기 전에 새 값이 들어오면 이전 구독을 끊는다. HTTP 한 번에 한 번만 실행되는 Interceptor에서는 `switchMap`/`concatMap` 둘 다 같은 결과를 낸다. 다만 의도를 명확히 하려면 순차 실행이 중요한 곳에는 `concatMap`을 쓰는 게 코드만 봐도 흐름이 읽힌다.

## 자주 쓰는 Interceptor 구현

### 로깅 인터셉터

요청/응답을 한 줄씩 남기는 가장 기본적인 패턴이다. 운영 중 디버깅에서 가장 자주 쓴다.

```typescript
import {
  CallHandler,
  ExecutionContext,
  Injectable,
  Logger,
  NestInterceptor,
} from '@nestjs/common';
import { Observable, tap, catchError, throwError } from 'rxjs';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(LoggingInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    const { method, url } = req;
    const startedAt = Date.now();

    this.logger.log(`req ${method} ${url}`);

    return next.handle().pipe(
      tap(() => {
        const elapsed = Date.now() - startedAt;
        this.logger.log(`res ${method} ${url} ${elapsed}ms`);
      }),
      catchError((err) => {
        const elapsed = Date.now() - startedAt;
        this.logger.error(`err ${method} ${url} ${elapsed}ms ${err.message}`);
        return throwError(() => err);
      }),
    );
  }
}
```

요청 시작 시각을 클로저에 잡아두고 응답이 흘러나올 때 차이를 잰다. 예외가 발생해도 시간 기록을 남기려고 `catchError`까지 붙였다. 실패한 요청의 응답 시간은 정상 응답보다 더 신경 써서 봐야 한다.

요청 ID를 자동으로 박아 추적 가능성을 높이려면 `request.headers['x-request-id']`를 읽거나, 없으면 `crypto.randomUUID()`로 만들어 컨텍스트에 심어둔다. 이때 로그 메시지에 한 번만 박지 말고 응답 헤더에도 같이 내려보내야 클라이언트와 서버 로그를 매칭할 수 있다.

### 응답 직렬화 인터셉터

API 응답 포맷을 통일하는 용도다. 예를 들어 모든 응답을 `{ success, data, error }` 구조로 감싼다.

```typescript
import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from '@nestjs/common';
import { Observable, map } from 'rxjs';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
}

@Injectable()
export class ResponseSerializeInterceptor<T>
  implements NestInterceptor<T, ApiResponse<T>>
{
  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<ApiResponse<T>> {
    return next.handle().pipe(
      map((data) => ({
        success: true,
        data,
        timestamp: new Date().toISOString(),
      })),
    );
  }
}
```

이 패턴을 쓸 때 자주 부딪히는 함정이 두 가지다.

첫째, Swagger 응답 스키마가 깨진다. 컨트롤러의 `@ApiResponse({ type: UserDto })`는 Interceptor 적용 전 타입을 가리키므로 실제 응답과 스키마가 어긋난다. 공통 응답 DTO를 만들어서 `@ApiExtraModels`와 `getSchemaPath`로 명시적으로 합성해야 정확해진다.

둘째, 예외 응답은 이 Interceptor를 거치지 않는다. 예외는 Exception Filter가 처리하므로 `{ success: false, error: ... }` 형식도 별도로 맞춰야 한다. Interceptor에서만 처리하면 정상 응답과 예외 응답의 포맷이 어긋난다.

### 캐싱 인터셉터

GET 요청에 한해서 응답을 메모리에 캐싱한다. 단순한 인메모리 캐시지만 실제로 Redis로 바꿔도 구조는 같다.

```typescript
import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from '@nestjs/common';
import { Observable, of, tap } from 'rxjs';

@Injectable()
export class CacheInterceptor implements NestInterceptor {
  private readonly store = new Map<string, { value: any; expiresAt: number }>();
  private readonly ttlMs = 30_000;

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    if (req.method !== 'GET') {
      return next.handle();
    }

    const key = req.originalUrl;
    const cached = this.store.get(key);
    const now = Date.now();

    if (cached && cached.expiresAt > now) {
      return of(cached.value);
    }

    return next.handle().pipe(
      tap((value) => {
        this.store.set(key, { value, expiresAt: now + this.ttlMs });
      }),
    );
  }
}
```

`of(cached.value)`로 새 Observable을 만들어 반환하면 핸들러를 호출하지 않고 캐시된 값으로 응답한다. 핵심은 `next.handle()`을 부르지 않는 것이다. 이 분기에 들어가면 컨트롤러는 실행되지 않는다.

운영에서 이 패턴을 그대로 쓰면 위험하다. Map에 무한히 쌓이므로 메모리 누수가 일어난다. TTL이 지난 항목을 주기적으로 정리하거나, LRU 캐시 라이브러리 (`lru-cache`)를 쓰거나, Redis로 빼야 한다. NestJS 공식 패키지 `@nestjs/cache-manager`를 쓰는 것도 방법이다.

캐시 키를 URL만으로 만들면 인증 사용자별로 분기되지 않아서 사용자 A의 응답이 사용자 B에게 노출되는 사고가 난다. 인증된 사용자의 데이터를 캐싱한다면 키에 사용자 식별자를 반드시 포함시킨다. 응답이 사용자 무관한 공개 데이터일 때만 URL 키가 안전하다.

### 타임아웃 인터셉터

전역으로 거는 경우가 많다. 외부 API 호출, DB 쿼리가 느려질 때 클라이언트를 무한히 기다리게 두지 않으려는 용도다.

```typescript
import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
  RequestTimeoutException,
} from '@nestjs/common';
import { Observable, TimeoutError, timeout, catchError, throwError } from 'rxjs';

@Injectable()
export class TimeoutInterceptor implements NestInterceptor {
  constructor(private readonly ms: number = 10_000) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      timeout(this.ms),
      catchError((err) => {
        if (err instanceof TimeoutError) {
          return throwError(() => new RequestTimeoutException());
        }
        return throwError(() => err);
      }),
    );
  }
}
```

여기서 흔히 놓치는 부분이 있다. `timeout`은 Observable 스트림이 끊긴 것이지 실제 비동기 작업이 취소된 게 아니다. 예를 들어 DB 쿼리가 10초 안에 안 끝나서 타임아웃이 떴어도, 그 쿼리는 백엔드에서 계속 돌고 있다. 진짜로 작업을 끊으려면 AbortController나 DB 드라이버 레벨의 쿼리 타임아웃을 따로 걸어야 한다. 이 사실을 모르면 "타임아웃 잘 동작하는데 DB 커넥션 풀이 왜 자꾸 고갈되지?"로 헤매게 된다.

그리고 글로벌로 타임아웃을 걸어두면 파일 업로드나 대용량 export 같은 엔드포인트가 같이 잘리는 사고가 난다. 라우트 단위로 타임아웃 시간을 다르게 가져갈 수 있도록 메타데이터 기반 설정을 권한다.

```typescript
import { SetMetadata } from '@nestjs/common';
export const Timeout = (ms: number) => SetMetadata('timeout', ms);

@Injectable()
export class TimeoutInterceptor implements NestInterceptor {
  constructor(
    private readonly reflector: Reflector,
    private readonly defaultMs: number,
  ) {}

  intercept(context: ExecutionContext, next: CallHandler) {
    const ms =
      this.reflector.get<number>('timeout', context.getHandler()) ??
      this.defaultMs;

    return next.handle().pipe(
      timeout(ms),
      catchError((err) =>
        err instanceof TimeoutError
          ? throwError(() => new RequestTimeoutException())
          : throwError(() => err),
      ),
    );
  }
}
```

핸들러에 `@Timeout(60_000)`을 붙이면 그 라우트만 60초로 늘어난다. 글로벌 기본값은 그대로 둔다.

### 에러 매핑 인터셉터

DB 드라이버나 외부 API 클라이언트에서 던지는 에러는 자기네 라이브러리 형식이지 도메인 예외가 아니다. 컨트롤러 안에서 매번 try/catch로 변환하는 건 지저분하다. 에러를 한곳에서 도메인 예외로 매핑하는 Interceptor를 두면 컨트롤러는 본업에만 집중할 수 있다.

```typescript
import {
  BadRequestException,
  CallHandler,
  ConflictException,
  ExecutionContext,
  Injectable,
  Logger,
  NestInterceptor,
  NotFoundException,
} from '@nestjs/common';
import { Observable, catchError, throwError } from 'rxjs';
import { QueryFailedError, EntityNotFoundError } from 'typeorm';

@Injectable()
export class ErrorMappingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(ErrorMappingInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      catchError((err) => throwError(() => this.map(err))),
    );
  }

  private map(err: unknown): Error {
    if (err instanceof EntityNotFoundError) {
      return new NotFoundException('대상을 찾을 수 없다');
    }

    if (err instanceof QueryFailedError) {
      const code = (err as any).code;
      if (code === '23505') {
        return new ConflictException('중복된 항목');
      }
      if (code === '23503') {
        return new BadRequestException('참조 무결성 위반');
      }
    }

    if (this.isAxiosError(err)) {
      const status = err.response?.status;
      if (status === 404) return new NotFoundException('외부 리소스 없음');
      if (status === 401) return new BadRequestException('외부 인증 실패');
    }

    this.logger.error('매핑되지 않은 에러', (err as Error).stack);
    return err as Error;
  }

  private isAxiosError(err: unknown): err is { response?: { status?: number } } {
    return typeof err === 'object' && err !== null && 'isAxiosError' in err;
  }
}
```

이 패턴이 잘 동작하려면 두 가지를 지켜야 한다. 첫째, 매핑되지 않은 에러는 변형 없이 그대로 다시 던져서 Exception Filter가 받게 한다. Interceptor에서 모든 에러를 무리하게 잡아 도메인 예외로 변환하면 원인 추적이 어려워진다. 둘째, 변환 전후의 에러 메시지/스택을 잃지 않도록 로그를 남기든지, 새 예외의 `cause`에 원본을 담는다.

```typescript
return new ConflictException('중복된 항목', { cause: err });
```

`@nestjs/common`의 HttpException 계열은 `cause` 옵션을 받는다. Filter에서 원인까지 로깅하면 운영 디버깅이 한결 수월하다.

## 스코프: 어디에 적용하느냐

Interceptor는 네 위치에 등록할 수 있다. 같은 인터페이스를 구현하지만 등록 위치에 따라 동작 범위와 DI 동작이 다르다.

| 등록 방식 | 적용 범위 | DI 주입 | 인스턴스 생성 시점 | 비고 |
|---|---|---|---|---|
| 메서드 `@UseInterceptors` | 해당 핸들러만 | O | 모듈 초기화 | 라우트별 차등 적용에 적합 |
| 컨트롤러 `@UseInterceptors` | 컨트롤러 전체 | O | 모듈 초기화 | 도메인 단위 응답 규약에 적합 |
| `APP_INTERCEPTOR` 토큰 | 전역 | O | 모듈 DI 컨텍스트 | DI 가능한 진짜 글로벌 |
| `app.useGlobalInterceptors(new ...)` | 전역 | X | 수동 인스턴스화 | 의존성 없는 단순 Interceptor 전용 |

### 메서드 스코프

특정 핸들러에만 적용한다. `@UseInterceptors`를 메서드에 단다.

```typescript
@Get(':id')
@UseInterceptors(CacheInterceptor)
findOne(@Param('id') id: string) {
  return this.userService.findOne(id);
}
```

해당 라우트만 통과한다. 캐싱처럼 라우트별로 특성이 다른 기능은 메서드 단위로 거는 게 명확하다.

### 컨트롤러 스코프

컨트롤러 전체에 적용한다. 클래스에 `@UseInterceptors`를 단다.

```typescript
@Controller('users')
@UseInterceptors(ResponseSerializeInterceptor)
export class UserController {}
```

해당 컨트롤러의 모든 핸들러에 동일하게 걸린다. 도메인 단위로 응답 포맷을 다르게 가져갈 때 유용하다.

### 모듈 스코프

모듈의 providers에 `APP_INTERCEPTOR` 토큰으로 등록한다. 이 방식은 의존성 주입을 정상적으로 받을 수 있다는 게 핵심이다.

```typescript
import { APP_INTERCEPTOR } from '@nestjs/core';

@Module({
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
```

이름은 `APP_INTERCEPTOR`라서 전역처럼 보이지만, 실제로는 등록한 모듈의 DI 컨텍스트를 따른다. 같은 토큰을 여러 모듈에서 등록하면 각각 다른 인스턴스로 동작한다.

여러 개를 같이 등록해도 된다. providers 배열에 같은 토큰으로 여러 개를 넣으면 모두 활성화된다. 다만 등록 순서가 실행 순서를 결정하지 않는다는 점이 함정이다. 같은 토큰으로 등록된 글로벌 Interceptor의 실행 순서는 NestJS 버전에 따라 변할 수 있어서, 순서가 중요한 경우 한쪽을 컨트롤러/메서드 스코프로 옮기는 편이 안전하다.

### 전역 스코프 (bootstrap)

`main.ts`에서 `app.useGlobalInterceptors()`로 등록하면 진짜 전역이 된다. 단점이 명확하다. DI 컨테이너 바깥에서 인스턴스를 만들기 때문에 다른 Injectable을 주입받을 수 없다.

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalInterceptors(new TimeoutInterceptor(5000));
  await app.listen(3000);
}
```

`TimeoutInterceptor`처럼 외부 의존성이 없는 단순한 Interceptor라면 이 방식이 깔끔하다. 하지만 Repository나 ConfigService 같은 걸 주입받아야 한다면 무조건 `APP_INTERCEPTOR` 토큰 방식을 써야 한다.

`useGlobalInterceptors`가 받는 인자에 클래스(`new` 없이)를 넘기는 실수도 자주 본다. 이 메서드는 인스턴스를 받는다. 클래스를 그대로 넘기면 런타임에 동작이 깨진다.

## Request-scoped Interceptor

기본적으로 Interceptor는 싱글톤으로 동작한다. 그래서 클래스 필드에 상태를 두면 모든 요청이 공유한다. 요청별로 다른 상태가 필요하다면 `Scope.REQUEST`를 명시한다.

```typescript
import { Injectable, Scope, Inject } from '@nestjs/common';
import { REQUEST } from '@nestjs/core';

@Injectable({ scope: Scope.REQUEST })
export class RequestContextInterceptor implements NestInterceptor {
  constructor(@Inject(REQUEST) private readonly request: Request) {}

  intercept(context: ExecutionContext, next: CallHandler) {
    this.request.startedAt = Date.now();
    return next.handle();
  }
}
```

주의할 점은 비용이다. Request-scoped로 만들면 요청마다 새 인스턴스를 생성하고, 의존성 트리도 함께 새로 만든다. 이 Interceptor가 주입받는 다른 Provider 중 싱글톤이 있어도 Request-scoped로 묶여서 처음부터 다시 만들어진다. 그래서 단순히 요청별 상태가 필요하다는 이유만으로 Request-scoped를 쓰지 말고, `AsyncLocalStorage` 기반의 context 모듈(`nestjs-cls` 등)을 검토하는 게 낫다. AsyncLocalStorage는 싱글톤 안에서 요청별 컨텍스트를 안전하게 다룰 수 있게 해준다.

또 글로벌로 Request-scoped Interceptor를 거는 건 권장하지 않는다. 모든 요청마다 인스턴스화 비용이 발생한다. 정말 필요하면 컨트롤러나 메서드 단위에서 제한적으로 쓴다.

## 가드, 파이프와 비교

세 가지가 비슷해 보이는데 책임이 다르다.

Guard는 요청을 통과시킬지 말지를 결정한다. boolean 또는 boolean Promise/Observable을 반환한다. 응답을 가공하는 책임이 없다.

Pipe는 파라미터를 변환하거나 검증한다. 메서드 파라미터 단위로 동작하며 변환된 값을 반환한다. 응답에는 손대지 않는다.

Interceptor는 핸들러 앞뒤를 감싸면서 응답을 변형하거나 부가 동작을 한다. RxJS Observable 위에서 동작한다는 게 결정적 차이다.

실무에서 헷갈리는 케이스는 "권한 검사 결과에 따라 응답을 다르게 주고 싶다"같은 경우다. 권한 자체는 Guard가, 응답 가공은 Interceptor가 한다. Guard에서 응답을 직접 만지려고 들면 Filter나 Interceptor와 충돌한다.

## WebSocket과 Microservice에서의 동작 차이

Interceptor는 HTTP 전용이 아니다. WebSocket 게이트웨이의 메시지 핸들러나 마이크로서비스의 패턴 핸들러에도 똑같이 걸린다. 다만 `intercept`에서 꺼낼 수 있는 정보가 다르다.

WebSocket에서는 `context.switchToWs()`로 `client`와 `data`를 꺼낸다. 응답이 HTTP처럼 단일 객체로 끝나지 않고 서버에서 메시지를 emit하는 형태인 경우 응답 변환이 의도와 다르게 동작할 수 있다. WebSocket Interceptor는 보통 메시지 입력 검증, 인증된 사용자 컨텍스트 주입, 메시지 처리 시간 측정 같은 부수 효과 위주로 쓴다.

마이크로서비스(`@MessagePattern`, `@EventPattern`)에서는 `context.switchToRpc().getData()`로 페이로드를 꺼낸다. RPC 응답은 HTTP와 비슷하게 단일 반환값이라 응답 변환 패턴이 그대로 통한다. 다만 `@EventPattern`은 응답을 보내지 않는다. 이 차이를 모르고 응답 변환 Interceptor를 글로벌로 걸어두면 이벤트 핸들러에서도 변환이 일어나지만 어디로도 안 나간다.

```typescript
intercept(context: ExecutionContext, next: CallHandler) {
  if (context.getType() === 'rpc') {
    // RPC 트랜스포트 전용 로직
  }
  if (context.getType() === 'http') {
    // HTTP 전용
  }
  return next.handle();
}
```

여러 트랜스포트를 같이 쓰는 프로젝트에서는 트랜스포트 분기를 명시적으로 두는 게 안전하다.

## 인터셉터 테스트

Interceptor는 함수 하나만 있는 클래스라 단위 테스트가 어렵지 않다. `intercept` 메서드에 가짜 `ExecutionContext`와 `CallHandler`를 넘기고 반환 Observable을 검증한다.

```typescript
import { of, lastValueFrom } from 'rxjs';
import { ExecutionContext, CallHandler } from '@nestjs/common';

describe('ResponseSerializeInterceptor', () => {
  it('응답을 ApiResponse로 감싸야 한다', async () => {
    const interceptor = new ResponseSerializeInterceptor();

    const context = {
      switchToHttp: () => ({
        getRequest: () => ({}),
        getResponse: () => ({}),
      }),
      getType: () => 'http',
    } as unknown as ExecutionContext;

    const next: CallHandler = {
      handle: () => of({ id: 1, name: 'kim' }),
    };

    const result = await lastValueFrom(interceptor.intercept(context, next));

    expect(result.success).toBe(true);
    expect(result.data).toEqual({ id: 1, name: 'kim' });
    expect(result.timestamp).toBeDefined();
  });
});
```

`catchError`가 들어간 Interceptor는 `throwError`를 반환하는 가짜 `CallHandler`를 만들어 테스트한다.

```typescript
import { throwError } from 'rxjs';

const next: CallHandler = {
  handle: () => throwError(() => new EntityNotFoundError('User', { id: 1 })),
};

await expect(
  lastValueFrom(interceptor.intercept(context, next)),
).rejects.toBeInstanceOf(NotFoundException);
```

통합 테스트는 `Test.createTestingModule`로 모듈을 띄우고 supertest로 호출하면 된다. 글로벌 Interceptor의 실제 동작까지 확인하고 싶을 때 이쪽이 안전하다.

## 실무 트러블슈팅

### 응답이 변환되지 않는 경우

`map`을 걸었는데 응답이 그대로 나가는 경우가 있다. 대부분 컨트롤러에서 `@Res() res: Response`로 Express 응답 객체를 직접 받아서 `res.json()`을 호출한 경우다. 이러면 NestJS의 응답 파이프라인을 우회하므로 Interceptor의 변환이 적용되지 않는다.

해결책은 둘 중 하나다. `@Res({ passthrough: true })`로 응답 객체를 받되 NestJS 파이프라인은 그대로 두든지, 아예 `@Res()`를 빼고 반환값으로 응답을 만들든지. 라이브러리 모드와 표준 모드를 섞으면 Interceptor 동작을 신뢰할 수 없게 된다.

### 메모리 누수

가장 흔한 케이스가 캐싱 Interceptor를 직접 짜면서 만료 처리를 안 넣은 경우다. 위 예제에서 본 `Map`에 무한히 쌓이는 패턴이다. 운영 환경에서는 반드시 LRU 캐시나 외부 캐시 (Redis, Memcached)를 쓴다.

또 다른 케이스는 Interceptor 내부에서 subscribe를 직접 호출하는 경우다.

```typescript
intercept(context: ExecutionContext, next: CallHandler) {
  next.handle().subscribe((value) => {
    // 이렇게 하면 안 된다
  });
  return next.handle();
}
```

`next.handle()`을 두 번 호출하면 핸들러가 두 번 실행된다. 게다가 직접 `subscribe`한 Observable은 자동 해제되지 않아서 메모리 누수가 일어난다. Interceptor에서는 항상 `next.handle()`을 한 번만 호출하고 `.pipe()`로 변환을 연결하는 것이 원칙이다.

### Exception Filter와의 충돌

Interceptor에서 `catchError`로 예외를 잡으면 Exception Filter가 실행되지 않는 경우가 생긴다. 다음 코드를 보자.

```typescript
return next.handle().pipe(
  catchError((err) => {
    return of({ error: err.message });
  }),
);
```

`throwError`가 아니라 `of`로 빠져나오면 정상 응답으로 처리된다. Exception Filter가 받지 못하고, 클라이언트는 HTTP 200으로 에러를 받는다. 의도한 동작이 아니라면 반드시 `throwError(() => err)`로 다시 던져야 한다.

반대로 Interceptor에서 예외를 변환해서 다시 던졌는데, 컨트롤러에 붙은 다른 Exception Filter가 원본 예외 클래스를 잡으려고 한다면 변환 후 클래스로는 매칭되지 않는다. Filter 등록 위치(글로벌/컨트롤러/메서드)와 Interceptor의 변환 순서를 함께 봐야 한다.

### 동기 핸들러와 Observable의 혼동

Interceptor의 `intercept`가 Observable을 반환해야 한다. Promise를 반환하면 컴파일 에러는 안 나도 런타임에 응답이 안 나가거나, NestJS가 Promise를 한 번 resolve해서 Observable로 감싸는 식으로 예기치 못한 동작을 한다.

비동기 작업이 필요하다면 `from(promise)`로 Observable로 변환해서 합성한다.

```typescript
import { from, switchMap } from 'rxjs';

intercept(context: ExecutionContext, next: CallHandler) {
  return from(this.someAsyncCheck()).pipe(
    switchMap(() => next.handle()),
  );
}
```

### 전역 Interceptor에서 DI가 안 될 때

`app.useGlobalInterceptors(new MyInterceptor())`로 등록한 Interceptor가 다른 서비스를 주입받지 못한다. 콘솔에는 `Cannot read property 'xxx' of undefined`만 뜬다. 위에서 언급한 대로, `APP_INTERCEPTOR` 토큰 방식으로 전환하면 해결된다.

```typescript
@Module({
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: MyInterceptor,
    },
  ],
})
export class AppModule {}
```

이 차이를 모르고 `app.useGlobalInterceptors`를 쓰다가 `new Interceptor(someService)`처럼 수동 주입을 시도하면 모듈 초기화 순서에 따라 깨진다. DI가 필요하면 무조건 토큰 방식이다.

### 다중 Interceptor 순서가 꼬일 때

같은 응답에 두 Interceptor가 모두 `map`을 거는데 결과가 예상과 다르면, 합성 순서를 먼저 따져본다. before는 바깥쪽(글로벌)부터, after는 안쪽(메서드)부터 실행된다. 응답 직렬화는 가장 바깥에서 한 번만 일어나야 하므로 일반적으로 글로벌 또는 모듈 스코프에 둔다. 캐싱은 핸들러 직전에서 동작해야 하므로 메서드 스코프가 안전하다. 둘 다 글로벌에 두고 둘 다 응답을 가공하면, 캐시에 저장되는 값과 클라이언트로 나가는 값이 어긋난다.

### 매번 새로운 Observable이 만들어진다는 점

`tap` 안의 콜백이나 `map`의 변환 함수가 매 요청마다 새로 평가된다. 클로저에 무거운 객체를 넣어두면 GC가 그만큼 일을 더 한다. 가능한 한 Interceptor 인스턴스 필드에 상태/설정을 두고, `intercept` 안에서는 그 참조만 쓴다.

```typescript
@Injectable()
export class HeavyInterceptor implements NestInterceptor {
  private readonly bigConfig = buildBigConfig(); // 한 번만 만든다

  intercept(context: ExecutionContext, next: CallHandler) {
    return next.handle().pipe(
      map((data) => transform(data, this.bigConfig)),
    );
  }
}
```

## 정리해서 보자

Interceptor는 RxJS 기반 응답 파이프라인 위에서 동작한다는 점이 다른 NestJS 요소와 결정적으로 다르다. `tap`, `map`, `catchError`, `timeout` 정도만 익숙해져도 실무에서 마주치는 대부분의 케이스를 처리할 수 있다. 등록 스코프에 따라 DI 동작이 달라진다는 점, 예외 처리는 반드시 `throwError`로 다시 던져야 한다는 점, `next.handle()`은 한 번만 호출한다는 점, 합성 순서가 before는 바깥부터/after는 안쪽부터라는 점, 이 네 가지가 가장 자주 발이 걸리는 곳이다.
