# NestJS 마이크로서비스 (gRPC / RabbitMQ)

NestJS로 서비스를 나누다 보면 “이건 동기 호출이 깔끔하겠다” 싶은 것과 “메시지로 흘려보내는 게 안전하겠다” 싶은 게 명확히 갈린다. 일반적으로 조회·간단한 계산은 gRPC 같은 RPC가 잘 맞고, 상태 변경·이벤트 브로드캐스트·버퍼링이 필요한 작업은 RabbitMQ 같은 메시지 브로커가 잘 맞는다. 대다수 실무 시스템은 둘을 섞는다.

아래는 통신 패턴, 스키마(프로토/메시지) 버저닝, 멱등 처리까지 한 번에 정리한 내용이다. 용어가 낯설다면 각 섹션의 “용어 풀기”를 참고하면 된다.

---

## gRPC 통신 패턴

gRPC는 Google이 만든 고성능 RPC 프레임워크다. 스키마는 Protocol Buffers(proto)로 정의하고, HTTP/2 위에서 바이너리로 주고받는다. 강한 타입과 스트리밍(단방향·양방향)이 장점이다.

### 스키마(proto) 기본 예시

```proto
syntax = "proto3";
package user.v1;

service UserService {
  rpc GetUser (GetUserRequest) returns (GetUserResponse);
  rpc StreamUsers (StreamUsersRequest) returns (stream GetUserResponse); // 서버 스트리밍 예시
}

message GetUserRequest { string id = 1; }
message StreamUsersRequest { repeated string ids = 1; }
message GetUserResponse { string id = 1; string name = 2; }
```

### 서버 부트스트랩

```ts
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.GRPC,
    options: {
      package: ['user.v1'],
      protoPath: ['proto/user.proto'],
      url: '0.0.0.0:50051',
      // maxSendMessageLength, maxReceiveMessageLength 등 운영 파라미터도 필요 시 조정
    },
  });
  await app.listen();
}
bootstrap();
```

### gRPC 핸들러

```ts
import { Controller } from '@nestjs/common';
import { GrpcMethod } from '@nestjs/microservices';

@Controller()
export class UserController {
  @GrpcMethod('UserService', 'GetUser')
  getUser({ id }: { id: string }) {
    return { id, name: 'Alice' };
  }
}
```

### 클라이언트 모듈/사용

```ts
import { Module, Inject, OnModuleInit } from '@nestjs/common';
import { ClientsModule, Transport, ClientGrpc } from '@nestjs/microservices';

interface UserServiceClient {
  getUser(request: { id: string }): any; // 실제론 ts-proto 등으로 생성된 타입 사용 권장
}

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'USER_GRPC',
        transport: Transport.GRPC,
        options: { package: 'user.v1', protoPath: 'proto/user.proto', url: 'user:50051' },
      },
    ]),
  ],
})
export class ApiModule implements OnModuleInit {
  private userSvc!: UserServiceClient;
  constructor(@Inject('USER_GRPC') private readonly client: ClientGrpc) {}
  onModuleInit() {
    this.userSvc = this.client.getService<UserServiceClient>('UserService');
  }
}
```

### 에러/타임아웃/메타데이터

- 타임아웃(Deadline): 호출 단위로 마감시간을 정해 지연 누적을 방지한다.
- 에러 매핑: gRPC Status(Code) ↔ 도메인 에러를 인터셉터에서 일관되게 매핑한다.
- 메타데이터: `correlationId`, 사용자/테넌트 정보 등을 메타데이터로 함께 전달한다.

용어 풀기
- Protocol Buffers(proto): 메시지 스키마(IDL)를 정의하는 포맷. 컴파일러가 언어별 타입을 생성해준다.
- HTTP/2: 하나의 연결에서 여러 요청을 멀티플렉싱. 헤더 압축, 서버 푸시 지원.
- 스트리밍: 단건(unary) 외에, 서버/클라이언트/양방향 스트리밍을 지원한다.

운영 팁
- HTTP/1.1 프록시만 허용되는 구간에서는 gRPC가 막힐 수 있다. 게이트웨이에서 gRPC-Web 또는 REST 프록시를 고려한다.
- 코드 생성기(ts-proto 등)를 써서 DTO와 타입을 정합성 있게 유지한다.
- 패키지 네임스페이스(`user.v1`, `user.v2`)로 버저닝하면 충돌을 줄일 수 있다.

---

## RabbitMQ(AMQP) 통신 패턴

RabbitMQ는 AMQP 프로토콜 기반 메시지 브로커다. 발행/구독 모델로 느슨한 결합, 버퍼링, 재시도를 쉽게 구현할 수 있다.

핵심 구성 요소
- Exchange: 메시지를 라우팅하는 허브. 종류로는 direct, topic, fanout, headers가 있다.
- Queue: 메시지가 쌓였다가 소비되는 버퍼.
- Binding: Exchange와 Queue 사이의 라우팅 규칙.

### 연결/클라이언트 등록

```ts
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'RMQ',
        transport: Transport.RMQ,
        options: {
          urls: ['amqp://guest:guest@rabbitmq:5672'],
          queue: 'user.events',
          queueOptions: { durable: true },
          prefetchCount: 10, // 소비자당 동시 처리 제한(QoS)
        },
      },
    ]),
  ],
})
export class MessagingModule {}
```

### 발행과 소비

```ts
// publisher
import { Injectable, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';

@Injectable()
export class UserPublisher {
  constructor(@Inject('RMQ') private readonly client: ClientProxy) {}
  userCreated(evt: { id: string; name: string }) {
    return this.client.emit('user.created', evt); // fire-and-forget 이벤트
  }
}

// consumer
import { Controller } from '@nestjs/common';
import { Ctx, EventPattern, Payload, RmqContext } from '@nestjs/microservices';

@Controller()
export class UserConsumer {
  @EventPattern('user.created')
  async handleUserCreated(@Payload() data: any, @Ctx() ctx: RmqContext) {
    const ch = ctx.getChannelRef();
    const msg = ctx.getMessage();
    try {
      // ...업무 처리
      ch.ack(msg);
    } catch (e) {
      ch.nack(msg, false, false); // 재큐잉(false) 시 DLX로 이동하도록 구성
    }
  }
}
```

### 재시도/DLQ(Dead Letter Queue)

- 큐에 `x-dead-letter-exchange`, `x-message-ttl`을 설정해 지연 재시도나 실패 격리를 구성한다.
- 소비자는 반드시 수동 `ack/nack`로 처리 성공/실패를 명확히 표기한다.

용어 풀기
- QoS(prefetch): 소비자가 한 번에 끌어오는 처리량 상한. 폭주를 막는다.
- DLX: 실패 메시지가 이동하는 교환기. 원인 분석 및 지연 재처리에 쓴다.
- Routing Key: 메시지 라우팅에 사용하는 문자열. topic 교환기에서 와일드카드를 지원한다.

운영 팁
- 순서 보장을 원하면 파티션 키(예: userId)로 큐를 나누거나, 메시지에 순번을 붙여 검증한다.
- RPC가 꼭 필요하면 `client.send()`와 `@MessagePattern` 조합으로 요청/응답을 구현할 수 있지만, 큐 점유와 타임아웃 관리에 신경 써야 한다.

---

## 메시지 스키마 버저닝

시간이 지나면 이벤트의 필드가 늘거나 의미가 바뀐다. 생산자와 소비자가 독립적으로 배포되기 때문에 “하위 호환”을 우선시하는 규칙이 필요하다.

전략
- 이벤트 이름에 버전 포함: `user.created.v1`, `user.created.v2`
- 페이로드에 `version` 필드 포함: `{ version: 2, id, name, nickname }`
- gRPC는 proto 패키지 네임스페이스로 버전 분리: `package user.v1`, `package user.v2`

이행 가이드
- 생산자: 새 필드를 추가하되 기본값을 넣어 기존 소비자가 깨지지 않게 한다(“확장 전용” 변경).
- 소비자: 알 수 없는 필드는 무시하고, 누락된 필드는 기본값으로 보완한다.
- 전환 기간 동안 두 버전을 동시에 발행하거나, 브리징 소비자를 둬서 v1→v2 변환을 담당하게 한다.

예시(proto 패키지 버전 업)

```proto
// v1
package user.v1;
message User { string id = 1; string name = 2; }

// v2: nickname 추가, 의미는 확장
package user.v2;
message User { string id = 1; string name = 2; string nickname = 3; }
```

---

## 멱등성(Idempotency) 처리

메시지는 언제든 중복될 수 있다. 같은 메시지가 여러 번 와도 결과가 한 번만 반영되도록 만들어야 한다.

핵심 아이디어
- “멱등 키(idempotency key)”를 정한다. 보통 도메인에서 유일한 값(예: 결제 영수증 ID)을 쓴다.
- 처리한 키를 기록해 두고, 재수신 시 건너뛴다.
- DB 유니크 제약/UPSERT를 이용해 중복 삽입을 물리적으로 차단한다.

스니펫

```ts
// 테이블 예: processed_event(id text primary key, processed_at timestamptz)
import { Controller } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';

@Controller()
export class PaymentConsumer {
  constructor(private readonly repo: ProcessedEventRepo) {}

  @EventPattern('payment.captured.v1')
  async handle(@Payload() evt: { id: string; orderId: string }) {
    const seen = await this.repo.exists(evt.id);
    if (seen) return;

    await this.repo.tx(async () => {
      await this.repo.insert(evt.id); // 유니크 키 충돌 시 롤백
      await this.applyBusiness(evt);
    });
  }
}
```

gRPC에서의 멱등성
- 재시도 가능한 읽기(API)는 서버가 부작용 없이 여러 번 처리할 수 있게 설계한다.
- 상태 변경 API는 `Idempotency-Key` 같은 메타데이터를 받아 키 기준으로 한 번만 적용한다.

메시징에서의 멱등성
- RabbitMQ 메시지 속성의 `messageId`/헤더에 멱등 키를 넣고, 소비자에서 중복 검출한다.
- “Outbox 패턴”을 사용하면 DB 트랜잭션과 메시지 발행의 일관성을 높일 수 있다. 상태 변경을 DB에 커밋하면서 같은 트랜잭션으로 `outbox` 테이블에 이벤트를 적재하고, 별도 퍼블리셔가 이를 발행한다.

용어 풀기
- 멱등성: 같은 입력을 여러 번 넣어도 결과가 변하지 않는 성질. 메시징에서는 “중복 수신에도 부작용이 1회만 난다”는 의미로 쓴다.
- Outbox/Inbox 패턴: 서비스 경계를 넘는 통신을 로컬 트랜잭션으로 안전하게 만들기 위한 비동기 합의 패턴.

---

## 관찰성/운영 팁 한 묶음

- 상관관계 ID(correlationId)를 gRPC 메타데이터/메시지 헤더에 항상 실어 로그/트레이싱을 잇는다.
- OpenTelemetry 인터셉터를 붙여 분산 추적을 기본값으로 둔다.
- 재시도는 지수 백오프로 하되, 멱등 설계가 먼저다. 재시도만으로 일관성은 보장되지 않는다.
- 소비자 `prefetch`와 처리 시간(슬로우 컨슈머)을 꾸준히 모니터링한다. 지연이 커지면 파티션을 늘리거나 소비자를 수평 확장한다.

---

## 무엇을 언제 고를까

- 동기 RPC 스타일(즉시 응답 필요, 강한 타입) → gRPC
- 느슨한 결합/버퍼링/비동기 이벤트 흐름 → RabbitMQ

현실에선 두 방식을 섞는다. 중요한 건 “스키마 버저닝”과 “멱등성”을 초기 설계부터 포함시키는 것이다. 이 두 가지가 통신 방식의 선택보다 시스템 안정성에 더 큰 영향을 준다.


