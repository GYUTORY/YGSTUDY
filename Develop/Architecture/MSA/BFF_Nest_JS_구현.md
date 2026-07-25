---
title: BFF 패턴 - NestJS 구현
tags: [backend, msa, bff, nestjs, rxjs, axios, typescript]
updated: 2026-07-25
---

# BFF 패턴 - NestJS 구현

NestJS로 BFF를 만들 때 Java/Spring과 다른 점이 몇 가지 있다. HttpService가 RxJS Observable을 반환하고, axios 인스턴스를 서비스별로 분리하는 방법이 Spring의 RestTemplate이나 WebClient와 다르다. 이 문서는 NestJS 생태계에서 BFF를 구현할 때 실제로 마주치는 부분을 다룬다.

---

## 기본 구조

NestJS BFF의 뼈대는 이렇게 잡는다.

```
web-bff/
├── src/
│   ├── order/
│   │   ├── order.module.ts
│   │   ├── order.controller.ts
│   │   └── order.service.ts
│   ├── http/
│   │   ├── order-http.module.ts
│   │   ├── payment-http.module.ts
│   │   └── product-http.module.ts
│   ├── interceptors/
│   │   └── response.interceptor.ts
│   └── app.module.ts
```

서비스별로 HttpModule을 분리하는 이유는 타임아웃을 서비스마다 다르게 잡아야 하기 때문이다. 하나의 HttpModule을 전역으로 등록하면 모든 서비스 호출에 같은 설정이 적용된다.

---

## axios 인스턴스별 타임아웃 설정

주문 서비스는 DB 조회가 느려서 3초를 줘야 하고, 상품 서비스는 캐시가 있어서 500ms면 충분한 경우가 있다. 이런 차이를 하나의 HttpModule로는 처리할 수 없다.

서비스별로 HttpModule을 별도 모듈에서 등록한다.

```typescript
// http/order-http.module.ts
import { HttpModule } from '@nestjs/axios';
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { OrderHttpClient } from './order-http.client';

@Module({
  imports: [
    HttpModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        baseURL: config.get('ORDER_SERVICE_URL'),
        timeout: 3000,
        headers: { 'X-Service-Name': 'web-bff' },
      }),
    }),
  ],
  providers: [OrderHttpClient],
  exports: [OrderHttpClient],
})
export class OrderHttpModule {}
```

```typescript
// http/product-http.module.ts
@Module({
  imports: [
    HttpModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        baseURL: config.get('PRODUCT_SERVICE_URL'),
        timeout: 500,
        headers: { 'X-Service-Name': 'web-bff' },
      }),
    }),
  ],
  providers: [ProductHttpClient],
  exports: [ProductHttpClient],
})
export class ProductHttpModule {}
```

주문 모듈에서 OrderHttpModule과 ProductHttpModule을 각각 import하면, 주문 클라이언트는 3초 타임아웃, 상품 클라이언트는 500ms 타임아웃이 독립적으로 적용된다.

### 서비스 클라이언트 구현

```typescript
// http/order-http.client.ts
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { NotFoundException, ServiceUnavailableException } from '@nestjs/common';
import { Observable } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AxiosError } from 'axios';

@Injectable()
export class OrderHttpClient {
  constructor(private readonly httpService: HttpService) {}

  getOrder(orderId: string): Observable<OrderDto> {
    return this.httpService.get<OrderDto>(`/orders/${orderId}`).pipe(
      map((response) => response.data),
      catchError((error: AxiosError) => {
        if (error.response?.status === 404) {
          throw new NotFoundException(`주문 ${orderId}를 찾을 수 없다`);
        }
        throw new ServiceUnavailableException('주문 서비스 호출 실패');
      }),
    );
  }

  getOrders(orderIds: string[]): Observable<OrderDto[]> {
    return this.httpService
      .post<OrderDto[]>('/orders/batch', { ids: orderIds })
      .pipe(map((response) => response.data));
  }
}
```

에러 핸들링을 클라이언트 레이어에서 처리하면 서비스 레이어에서 하위 서비스 에러 타입을 신경 쓰지 않아도 된다. 404는 NestJS 예외로 변환하고, 나머지는 503으로 올린다.

---

## forkJoin으로 병렬 호출

RxJS의 `forkJoin`은 여러 Observable이 모두 완료되면 결과를 한번에 묶어준다. Java의 `CompletableFuture.allOf`와 같은 역할이다.

```typescript
// order/order.service.ts
import { Injectable } from '@nestjs/common';
import { Observable, forkJoin } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';

@Injectable()
export class OrderBffService {
  constructor(
    private readonly orderClient: OrderHttpClient,
    private readonly paymentClient: PaymentHttpClient,
    private readonly productClient: ProductHttpClient,
  ) {}

  getOrderDetail(orderId: string): Observable<OrderDetailResponse> {
    return this.orderClient.getOrder(orderId).pipe(
      switchMap((order) =>
        forkJoin({
          payment: this.paymentClient.getPayment(order.paymentId),
          products: this.productClient.getProducts(order.productIds),
        }).pipe(
          map(({ payment, products }) =>
            this.toOrderDetailResponse(order, payment, products),
          ),
        ),
      ),
    );
  }

  private toOrderDetailResponse(
    order: OrderDto,
    payment: PaymentDto,
    products: ProductDto[],
  ): OrderDetailResponse {
    return {
      orderId: order.id,
      status: order.status,
      payment: {
        method: payment.method,
        status: payment.status,
      },
      products: products.map((p) => ({
        name: p.name,
        price: p.price,
        thumbnailUrl: p.thumbnailUrl,
      })),
    };
  }
}
```

`switchMap` 안에서 `forkJoin`을 쓰는 패턴이 기본이다. 주문을 먼저 가져와야 결제 ID와 상품 ID를 알 수 있으니 순차 실행이 불가피하다. 결제와 상품은 서로 독립적이니 `forkJoin`으로 묶어 병렬 처리한다.

`forkJoin`에 배열 대신 객체를 넘기면 결과를 꺼낼 때 인덱스 대신 키로 접근해서 코드가 읽기 좋다.

---

## combineLatest와 forkJoin 차이

둘 다 여러 Observable을 합치는데 동작 방식이 다르다.

`forkJoin`은 모든 Observable이 **완료**될 때 마지막 값을 모아서 한 번 방출한다. HTTP 호출처럼 값을 한 번 내고 끝나는 경우에 맞다.

`combineLatest`는 Observable 중 하나라도 새 값을 방출하면 즉시 최신 값 조합을 내보낸다. 스트림이 계속 살아있으면서 값이 바뀌는 경우에 쓴다.

BFF에서 HTTP 호출을 병렬 처리할 때는 `forkJoin`이 맞다. `combineLatest`를 HTTP 호출에 쓰면 동작은 하지만 의도가 명확하지 않다.

`combineLatest`는 관리자 대시보드처럼 여러 실시간 데이터 스트림을 합쳐야 할 때 쓴다.

```typescript
// 관리자 대시보드 - WebSocket이나 폴링으로 받는 지표를 합치는 경우
getDashboardMetrics(): Observable<DashboardMetrics> {
  return combineLatest({
    orderStats: this.orderStatsStream(),
    activeUsers: this.activeUsersStream(),
    systemHealth: this.systemHealthStream(),
  }).pipe(
    map(({ orderStats, activeUsers, systemHealth }) => ({
      orderCount: orderStats.total,
      activeUserCount: activeUsers.count,
      isHealthy: systemHealth.status === 'ok',
    })),
  );
}
```

---

## Interceptor로 응답 변환

응답 형태를 통일하거나 에러 응답 포맷을 맞출 때 Interceptor를 쓴다. 컨트롤러마다 같은 변환 코드를 넣는 것보다 한 곳에서 처리하는 게 낫다.

```typescript
// interceptors/response.interceptor.ts
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
}

@Injectable()
export class ResponseInterceptor<T>
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

전역으로 적용하려면 `main.ts`에 등록한다.

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalInterceptors(new ResponseInterceptor());
  await app.listen(3000);
}
```

특정 엔드포인트에서 래핑을 건너뛰어야 하면 커스텀 데코레이터를 붙인다.

```typescript
// decorators/skip-response-wrap.decorator.ts
import { SetMetadata } from '@nestjs/common';
export const SkipResponseWrap = () => SetMetadata('skipResponseWrap', true);

// interceptor 수정
@Injectable()
export class ResponseInterceptor<T>
  implements NestInterceptor<T, ApiResponse<T> | T>
{
  constructor(private readonly reflector: Reflector) {}

  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<ApiResponse<T> | T> {
    const skip = this.reflector.get<boolean>(
      'skipResponseWrap',
      context.getHandler(),
    );
    if (skip) {
      return next.handle();
    }
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

---

## 에러 처리와 부분 실패

하위 서비스에서 에러가 나면 BFF에서 어떻게 처리할지 명확히 정해야 한다.

`forkJoin`은 하나라도 에러가 나면 전체가 에러로 끝난다. 부분 실패를 허용하려면 각 Observable에 `catchError`를 붙인다.

```typescript
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

getOrderDetailWithFallback(orderId: string): Observable<OrderDetailResponse> {
  return this.orderClient.getOrder(orderId).pipe(
    switchMap((order) =>
      forkJoin({
        payment: this.paymentClient.getPayment(order.paymentId).pipe(
          catchError(() => of(null)),
        ),
        shipping: this.shippingClient.getShipping(order.id).pipe(
          catchError(() => of(null)),
        ),
      }).pipe(
        map(({ payment, shipping }) =>
          this.toResponse(order, payment, shipping),
        ),
      ),
    ),
  );
}
```

배송 조회에 실패해도 주문과 결제 정보는 정상적으로 내려준다. `null`을 받은 `toResponse`는 배송 필드를 `null`로 채운다.

어디까지 부분 실패를 허용할지는 비즈니스 판단이다. 결제 정보 없는 주문 상세를 내려보내도 되는지는 클라이언트 팀과 합의해서 정한다. BFF가 임의로 결정하면 안 된다.

---

## RxJS 타임아웃 처리

axios 인스턴스에 타임아웃을 설정해도, 서버가 응답을 느리게 보내는 경우(스트리밍 응답, 헤더만 보내고 바디를 늦게 보내는 경우)는 axios 타임아웃이 잡지 못한다. RxJS 파이프라인에서 별도로 타임아웃을 잡는 게 더 안전하다.

```typescript
import { timeout, TimeoutError } from 'rxjs';
import { GatewayTimeoutException } from '@nestjs/common';

getOrder(orderId: string): Observable<OrderDto> {
  return this.httpService.get<OrderDto>(`/orders/${orderId}`).pipe(
    map((res) => res.data),
    timeout(2000),
    catchError((error) => {
      if (error instanceof TimeoutError) {
        throw new GatewayTimeoutException('주문 서비스 응답 시간 초과');
      }
      throw error;
    }),
  );
}
```

axios 타임아웃과 RxJS 타임아웃 값을 다르게 설정할 때는 RxJS 타임아웃을 더 짧게 잡는다. axios가 먼저 끊으면 RxJS 타임아웃 에러 대신 axios 에러가 올라오는데, 두 경우를 `catchError`에서 다르게 처리해야 한다면 로그에서 혼동이 생긴다.

---

## Observable을 Promise로 변환

팀 전체가 RxJS에 익숙하지 않으면 컨트롤러에서 `firstValueFrom`으로 Promise로 변환해서 반환한다. NestJS 컨트롤러 핸들러는 Observable과 Promise 모두 처리한다.

```typescript
// order/order.controller.ts
import { Controller, Get, Param } from '@nestjs/common';
import { firstValueFrom } from 'rxjs';

@Controller('orders')
export class OrderController {
  constructor(private readonly orderBffService: OrderBffService) {}

  @Get(':orderId')
  async getOrderDetail(
    @Param('orderId') orderId: string,
  ): Promise<OrderDetailResponse> {
    return firstValueFrom(this.orderBffService.getOrderDetail(orderId));
  }
}
```

서비스 레이어는 RxJS로 유지하고, 컨트롤러에서만 변환하는 방식이다. `firstValueFrom`은 Observable에서 첫 번째 값을 받으면 구독을 끊는다. Observable이 값을 방출하지 않고 끝나면 `EmptyError`를 던지니 주의해야 한다. `firstValueFrom(obs$, { defaultValue: null })`처럼 기본값을 지정하면 EmptyError를 피할 수 있다.

---

## 요청 컨텍스트 전파

클라이언트에서 받은 인증 토큰이나 트레이싱 헤더(X-Request-ID)를 하위 서비스로 넘겨야 하는 경우가 있다. 컨트롤러에서 헤더를 꺼내서 서비스 클라이언트까지 파라미터로 넘기는 방법도 있지만, 함수 시그니처가 오염된다.

`nestjs-cls` 라이브러리로 요청 컨텍스트를 유지하면 서비스 레이어에서 별도 파라미터 없이 꺼낼 수 있다.

```typescript
// app.module.ts
import { ClsModule } from 'nestjs-cls';

@Module({
  imports: [
    ClsModule.forRoot({
      global: true,
      middleware: {
        mount: true,
        setup: (cls, req) => {
          cls.set('requestId', req.headers['x-request-id'] ?? crypto.randomUUID());
          cls.set('authorization', req.headers['authorization']);
        },
      },
    }),
  ],
})
export class AppModule {}
```

```typescript
// http/order-http.client.ts
@Injectable()
export class OrderHttpClient {
  constructor(
    private readonly httpService: HttpService,
    private readonly cls: ClsService,
  ) {}

  getOrder(orderId: string): Observable<OrderDto> {
    const requestId = this.cls.get('requestId');
    const authorization = this.cls.get('authorization');

    return this.httpService
      .get<OrderDto>(`/orders/${orderId}`, {
        headers: {
          'X-Request-ID': requestId,
          Authorization: authorization,
        },
      })
      .pipe(map((res) => res.data));
  }
}
```

요청마다 생성된 requestId를 모든 하위 서비스 호출에 전달하면 분산 추적에서 한 요청의 흐름을 한눈에 볼 수 있다.

---

## 실제로 겪는 문제들

**ECONNREFUSED 처리**: 로컬 개발 환경에서 하위 서비스가 안 떠 있으면 ECONNREFUSED 에러가 난다. 환경변수로 Mock 여부를 제어하는 개발 환경 전용 설정을 만들어두면 BFF만 띄우고 개발할 수 있다.

**메모리 누수**: 컨트롤러 핸들러에서 Observable을 반환하면 NestJS가 구독 생명주기를 관리해준다. 핸들러 밖에서 직접 `subscribe()`를 호출하면 직접 해제해야 한다. 특히 전역 인터셉터나 가드에서 Observable을 직접 구독하는 코드는 주의해야 한다.

**forkJoin에 빈 배열**: `forkJoin([])` 또는 `forkJoin({})` 처럼 빈 배열이나 객체를 넘기면 즉시 완료된 Observable을 반환한다. 상품 ID 목록이 비어있을 때 상품 클라이언트를 호출하면 이런 경우가 생긴다. 빈 경우를 별도로 처리하거나, 빈 입력이면 빈 배열을 즉시 반환하는 분기를 넣어야 한다.

```typescript
getProducts(productIds: string[]): Observable<ProductDto[]> {
  if (productIds.length === 0) {
    return of([]);
  }
  return this.httpService
    .post<ProductDto[]>('/products/batch', { ids: productIds })
    .pipe(map((res) => res.data));
}
```

**타입 추론 한계**: `forkJoin`에 객체를 넘길 때 TypeScript가 각 필드의 타입을 제대로 추론하지 못하는 경우가 있다. 명시적으로 타입을 지정하거나 제네릭을 넣어주면 해결된다.
