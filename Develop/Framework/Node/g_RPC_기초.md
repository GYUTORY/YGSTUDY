---
title: "gRPC — Protobuf 스키마부터 NestJS 게이트웨이까지"
tags: [nodejs, grpc, api, backend, microservices, typescript]
updated: 2026-09-05
---

## gRPC를 쓰는 이유와 쓰지 말아야 할 상황

gRPC는 HTTP/2 위에서 동작하고, 페이로드는 Protobuf로 직렬화한다. REST + JSON 대비 페이로드가 작고 멀티플렉싱이 되니까 마이크로서비스 간 내부 통신에서 자주 쓴다.

문제는 디버깅이다. Protobuf는 바이너리라 `curl`로 바로 때릴 수가 없다. `grpcurl`이나 Postman gRPC 탭이 없으면 개발 중에 요청/응답을 눈으로 확인하기 힘들다. 팀 모두가 이 불편을 감수할 준비가 됐을 때 도입하는 게 맞다. 외부 클라이언트(웹 브라우저, 모바일 앱)와 직접 통신하는 엔드포인트에는 gRPC를 쓰지 않는다 — 브라우저는 HTTP/2 raw 스트림을 제어할 수 없어서 gRPC-Web 레이어가 필요하고, 복잡도가 REST 대비 크게 올라간다.

내부 서비스 간, 특히 지연 민감한 통신이나 스트리밍이 필요한 경우에만 gRPC를 꺼낸다.

## .proto 스키마 정의

Protobuf 스키마 파일이 gRPC 계약의 전부다. 서버와 클라이언트가 모두 이 파일에서 타입을 생성한다.

```protobuf
syntax = "proto3";

package order;

service OrderService {
  rpc GetOrder (GetOrderRequest) returns (OrderResponse);
  rpc ListOrders (ListOrdersRequest) returns (stream OrderResponse);
}

message GetOrderRequest {
  string order_id = 1;
}

message ListOrdersRequest {
  string user_id = 1;
  int32 page_size = 2;
}

message OrderResponse {
  string order_id = 1;
  string status = 2;
  int64 total_amount = 3;
  string created_at = 4;
}
```

필드 번호(1, 2, 3...)가 실제 직렬화 키다. 한번 배포된 스키마에서 필드 번호를 재사용하면 안 된다. 필드를 제거해도 그 번호는 영구 예약 상태로 둔다.

```protobuf
message OrderResponse {
  reserved 2;           // 예약. 이 번호는 다시 쓰지 않는다
  reserved "status";    // 필드명도 예약
  string order_id = 1;
  int64 total_amount = 3;
  string created_at = 4;
}
```

`proto3`에서 필드는 기본적으로 optional이다. 값이 없으면 기본값(숫자 0, 문자열 "")이 온다. 클라이언트가 "값이 없음"과 "기본값"을 구별해야 한다면 `optional` 키워드를 명시하거나 `google.protobuf.StringValue` 같은 wrapper 타입을 쓴다.

## NestJS에서 gRPC 서버 구성

```bash
npm install @nestjs/microservices @grpc/grpc-js @grpc/proto-loader
```

`main.ts`에서 마이크로서비스로 부트스트랩하거나, 기존 HTTP 앱에 hybrid 방식으로 붙인다.

```ts
// main.ts — HTTP + gRPC 하이브리드 앱
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { join } from 'path';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.connectMicroservice<MicroserviceOptions>({
    transport: Transport.GRPC,
    options: {
      package: 'order',
      protoPath: join(__dirname, '../proto/order.proto'),
      url: '0.0.0.0:5000',
    },
  });

  await app.startAllMicroservices();
  await app.listen(3000); // HTTP도 같이 뜬다
}
bootstrap();
```

`GrpcOptions`에서 자주 쓰는 설정들이다.

```ts
options: {
  package: 'order',
  protoPath: join(__dirname, '../proto/order.proto'),
  url: '0.0.0.0:5000',
  maxSendMessageLength: 1024 * 1024 * 4,  // 4MB (기본 4MB)
  maxReceiveMessageLength: 1024 * 1024 * 4,
  loader: {
    keepCase: true,      // proto의 snake_case를 그대로 유지
    longs: String,       // int64를 string으로 받음. Number면 정밀도 손실
    enums: String,
    defaults: true,
    oneofs: true,
  },
}
```

`longs: String`은 중요하다. int64 범위 값을 JavaScript Number로 받으면 53비트 이상에서 정밀도가 깨진다. 주문 ID나 타임스탬프처럼 큰 정수를 다루는 경우 반드시 String으로 받고, 필요하면 BigInt로 변환한다.

## Unary RPC 구현

컨트롤러에 `@GrpcMethod` 데코레이터를 붙인다. 메서드 이름이 proto의 rpc 이름과 일치해야 한다.

```ts
import { Controller } from '@nestjs/common';
import { GrpcMethod } from '@nestjs/microservices';

interface GetOrderRequest {
  orderId: string;
}

interface OrderResponse {
  orderId: string;
  totalAmount: string;
  createdAt: string;
}

@Controller()
export class OrderController {
  constructor(private readonly orderService: OrderService) {}

  @GrpcMethod('OrderService', 'GetOrder')
  async getOrder(data: GetOrderRequest): Promise<OrderResponse> {
    const order = await this.orderService.findById(data.orderId);
    if (!order) {
      // gRPC 에러는 RpcException으로 던진다
      throw new RpcException({
        code: Status.NOT_FOUND,
        message: `order ${data.orderId} not found`,
      });
    }
    return {
      orderId: order.id,
      totalAmount: order.totalAmount.toString(),
      createdAt: order.createdAt.toISOString(),
    };
  }
}
```

`RpcException`과 gRPC status 코드를 함께 써야 클라이언트가 에러 유형을 판별할 수 있다. HTTP 상태 코드처럼 gRPC에도 `NOT_FOUND`, `INVALID_ARGUMENT`, `INTERNAL`, `UNAUTHENTICATED` 등이 있다.

```ts
import { RpcException } from '@nestjs/microservices';
import { status as Status } from '@grpc/grpc-js';

throw new RpcException({
  code: Status.INVALID_ARGUMENT,
  message: 'order_id must not be empty',
});
```

## Server-streaming RPC

서버가 하나의 요청에 대해 여러 응답을 순차로 보내는 패턴이다. 주문 목록 페이지네이션, 실시간 상태 업데이트, 대용량 데이터 내보내기에서 쓴다.

```ts
import { Observable, Subject } from 'rxjs';

@GrpcMethod('OrderService', 'ListOrders')
listOrders(data: ListOrdersRequest): Observable<OrderResponse> {
  const subject = new Subject<OrderResponse>();

  // 비동기 스트림을 Observable로 감싼다
  (async () => {
    try {
      const cursor = this.orderService.streamByUser(data.userId, data.pageSize);
      for await (const order of cursor) {
        subject.next({
          orderId: order.id,
          totalAmount: order.totalAmount.toString(),
          createdAt: order.createdAt.toISOString(),
        });
      }
      subject.complete();
    } catch (err) {
      subject.error(new RpcException({
        code: Status.INTERNAL,
        message: err.message,
      }));
    }
  })();

  return subject.asObservable();
}
```

Subject를 쓰는 이유는 `for await...of` 루프 안에서 비동기로 값을 밀어 넣어야 하기 때문이다. `new Observable(subscriber => {...})` 방식으로도 할 수 있지만, async/await를 섞으면 에러 처리가 복잡해진다.

클라이언트에서는 스트림이 끝날 때까지 이벤트로 받는다.

```ts
const client = /* GrpcClient 주입 */;

client.listOrders({ userId: '123', pageSize: 100 })
  .subscribe({
    next: (order) => console.log(order),
    error: (err) => console.error(err),
    complete: () => console.log('스트림 완료'),
  });
```

스트림 도중 클라이언트가 연결을 끊으면 서버의 Observable이 구독 해제된다. `for await...of` 루프가 진행 중일 때 이 해제가 즉시 반영되지 않으므로, 긴 스트림에서는 `subject.closed` 또는 별도의 취소 신호를 확인하는 로직이 필요할 수 있다.

## gRPC 클라이언트 — NestJS에서 다른 서비스 호출

HTTP 클라이언트처럼 모듈에 등록하고 주입받는다.

```ts
// order.module.ts
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { join } from 'path';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'ORDER_SERVICE',
        transport: Transport.GRPC,
        options: {
          package: 'order',
          protoPath: join(__dirname, '../proto/order.proto'),
          url: 'order-service:5000',
        },
      },
    ]),
  ],
})
export class OrderModule {}
```

```ts
// 사용하는 서비스
import { Inject, OnModuleInit } from '@nestjs/common';
import { ClientGrpc } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class GatewayService implements OnModuleInit {
  private orderService: any;

  constructor(@Inject('ORDER_SERVICE') private client: ClientGrpc) {}

  onModuleInit() {
    this.orderService = this.client.getService('OrderService');
  }

  async getOrder(orderId: string) {
    return firstValueFrom(
      this.orderService.getOrder({ orderId })
    );
  }
}
```

`firstValueFrom`으로 Observable을 Promise로 바꾼다. Unary RPC는 값 하나를 내고 완료되므로 이 변환이 안전하다. 스트리밍 RPC는 Observable 그대로 써야 한다.

## REST-gRPC 게이트웨이

외부 클라이언트는 REST로 통신하고, 게이트웨이 내부에서 gRPC 마이크로서비스를 호출하는 구조다.

```
[클라이언트] --HTTP/REST--> [NestJS 게이트웨이] --gRPC--> [OrderService]
                                                 --gRPC--> [UserService]
                                                 --gRPC--> [PaymentService]
```

게이트웨이 자체는 HTTP 서버로만 띄우고, 각 내부 서비스에 대한 gRPC 클라이언트를 등록한다.

```ts
// gateway/main.ts
const app = await NestFactory.create(AppModule);
// gRPC 마이크로서비스로 connectMicroservice 하지 않는다
// 게이트웨이는 HTTP만 열린다
await app.listen(3000);
```

게이트웨이 컨트롤러에서 HTTP 요청을 받아 gRPC로 전달한다.

```ts
@Controller('orders')
export class OrdersController {
  constructor(private readonly gatewayService: GatewayService) {}

  @Get(':id')
  async getOrder(@Param('id') id: string) {
    try {
      return await this.gatewayService.getOrder(id);
    } catch (err) {
      // gRPC 에러를 HTTP 에러로 매핑
      if (err.code === Status.NOT_FOUND) {
        throw new NotFoundException(err.message);
      }
      throw new InternalServerErrorException();
    }
  }
}
```

gRPC 에러 코드와 HTTP 상태 코드의 매핑은 Google의 gRPC-HTTP transcoding 사양이 기준이 된다. `NOT_FOUND → 404`, `INVALID_ARGUMENT → 400`, `UNAUTHENTICATED → 401`, `PERMISSION_DENIED → 403` 정도는 반드시 처리한다.

## 자주 마주치는 문제

**proto 파일 경로가 빌드 후에 달라진다.** `__dirname`은 `.js` 파일 위치를 기준으로 한다. `dist/` 아래로 빌드하면 proto 파일이 `src/proto/`에 있는데 `__dirname`은 `dist/order/` 같은 경로가 된다. 가장 단순한 해결은 proto 파일을 빌드 출력 디렉토리에 복사하거나, `tsconfig.json`의 `rootDir`을 조정해 경로가 일치하게 만드는 것이다.

**keepCase를 안 쓰면 필드명이 camelCase로 바뀐다.** proto 기본 파서는 `order_id`를 `orderId`로 변환한다. `keepCase: true`로 고정하지 않으면 서버/클라이언트 어느 한쪽에서만 camelCase가 적용돼 필드가 undefined로 오는 상황이 생긴다.

**`maxSendMessageLength` 기본값을 초과하면 조용히 실패한다.** 기본 4MB를 넘는 메시지는 에러 없이 잘린다. 스트리밍으로 청크를 나눠 보내거나, 대용량이 예상되는 곳에서는 한도를 명시적으로 올린다.

**TLS 없이 프로덕션에 올리면 메타데이터가 평문으로 흐른다.** 인증 토큰이나 트레이스 ID를 gRPC 메타데이터로 전달하는 경우, TLS가 없으면 망 내부 스니핑에 노출된다. 쿠버네티스에서 서비스 메시(Istio, Linkerd)를 쓰면 mTLS가 자동으로 붙지만, 없는 환경이라면 credentials 설정을 직접 해야 한다.

```ts
import { credentials } from '@grpc/grpc-js';

options: {
  // TLS 연결
  credentials: credentials.createSsl(),
  // 또는 개발 환경 평문
  credentials: credentials.createInsecure(),
}
```
