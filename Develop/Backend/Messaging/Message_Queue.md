---
title: 메시지 큐 & 이벤트 기반 아키텍처
tags: [backend, messaging, event-driven, language]
updated: 2026-04-02
---

# 메시지 큐 & 이벤트 기반 아키텍처

## 개요

메시지 큐는 서비스 간 **비동기 통신**을 가능하게 하는 미들웨어이다. 생산자(Producer)가 메시지를 큐에 넣으면, 소비자(Consumer)가 자신의 속도로 처리한다. 마이크로서비스 간 결합도를 낮추고 시스템 안정성을 높인다.

### 왜 필요한가

```
동기 방식 (HTTP 직접 호출):
  주문 서비스 → 결제 서비스 → 재고 서비스 → 알림 서비스
  ❌ 하나라도 실패하면 전체 실패
  ❌ 느린 서비스가 전체를 지연
  ❌ 서비스 간 강결합

비동기 방식 (메시지 큐):
  주문 서비스 → [메시지 큐] → 결제 서비스 (독립 처리)
                            → 재고 서비스 (독립 처리)
                            → 알림 서비스 (독립 처리)
  ✅ 서비스 독립적으로 처리
  ✅ 실패 시 재시도 가능
  ✅ 느슨한 결합
```

### 핵심 패턴

| 패턴 | 설명 | 사용 예 |
|------|------|---------|
| **Point-to-Point** | 1 Producer → 1 Consumer | 작업 큐, 배치 처리 |
| **Pub/Sub** | 1 Producer → N Consumer | 이벤트 브로드캐스트 |
| **Request-Reply** | 요청 후 응답 대기 | RPC 대체 |
| **Dead Letter Queue** | 처리 실패 메시지 격리 | 에러 분석, 재처리 |

## 핵심

### 1. Kafka vs RabbitMQ 비교

| 항목 | Apache Kafka | RabbitMQ |
|------|-------------|----------|
| **모델** | 분산 로그 (이벤트 스트리밍) | 메시지 브로커 (전통적 큐) |
| **처리량** | 초당 수백만 건 | 초당 수만 건 |
| **메시지 보존** | 디스크에 영구 보존 (설정 기간) | 소비 후 삭제 (기본) |
| **순서 보장** | 파티션 내 보장 | 큐 내 보장 |
| **Consumer 그룹** | 네이티브 지원 | 플러그인 필요 |
| **프로토콜** | 자체 프로토콜 | AMQP, MQTT, STOMP |
| **재처리** | offset 리셋으로 재처리 가능 | 불가 (소비 후 삭제) |
| **학습 곡선** | 높음 | 낮음 |
| **적합한 상황** | 이벤트 소싱, 로그 수집, 실시간 스트리밍 | 작업 큐, RPC, 라우팅 |

📌 **선택 기준**: 이벤트를 **저장하고 재처리**해야 하면 Kafka, 단순 **작업 분배**면 RabbitMQ.

#### 표에서 두 줄은 손봐야 한다

**"Consumer 그룹: RabbitMQ = 플러그인 필요"** 는 두 개념을 겹쳐 놓은 결과다. 큐 하나를 여러 컨슈머가 나눠 먹는 것(competing consumers)은 RabbitMQ 의 기본 동작이고 아무것도 설치할 필요가 없다. Kafka 의 컨슈머 그룹이 추가로 주는 것은 **같은 메시지를 여러 그룹이 각자 전부 받는 것**인데, RabbitMQ 에서는 exchange 에 큐를 여러 개 바인딩하면 같은 모양이 된다. 차이는 "가능한가"가 아니라 **누가 팬아웃을 정의하는가**다 — Kafka 는 소비자가 그룹을 만들어 스스로 붙고, RabbitMQ 는 큐와 바인딩을 미리 만들어 둬야 한다. 소비자가 계속 늘어나는 구조라면 이 차이가 크게 다가온다.

**"재처리: RabbitMQ = 불가"** 도 조건이 빠졌다. 기본 큐는 ack 하면 메시지가 사라지므로 "지난 것을 다시 읽기"는 안 되지만, DLQ 에 쌓인 것을 원래 큐로 되돌리는 것은 표준 운영 절차다. 스트림 큐를 쓰면 오프셋 기반 재소비도 된다([RabbitMQ Streams](https://www.rabbitmq.com/docs/streams)). 정확히 말하면 **"과거 이벤트를 기본 저장 모델로 보관하느냐"** 가 다른 것이고, Kafka 는 보관이 기본이고 RabbitMQ 는 별도 선택이다.

처리량 두 줄도 그대로 인용하지 않는 편이 낫다. 메시지 크기, `acks` 설정, 복제 계수, 배치 여부에 따라 자릿수가 달라진다. 두 시스템의 상대 순위를 기억하는 정도로 쓰고, 실제 수치는 자기 메시지 크기로 직접 재야 한다.

### 2. Apache Kafka

#### 아키텍처

```
Producer ──▶ Broker Cluster ──▶ Consumer Group
               │
        ┌──────┼──────┐
     Topic A  Topic B  Topic C
        │
   ┌────┼────┐
  P0   P1   P2        (Partitions)
```

| 개념 | 설명 |
|------|------|
| **Topic** | 메시지 카테고리 (예: `order-events`, `user-events`) |
| **Partition** | Topic을 나눈 단위. 병렬 처리의 기본 |
| **Offset** | 파티션 내 메시지 위치 (번호) |
| **Consumer Group** | 같은 그룹은 파티션을 나눠 소비 (로드밸런싱) |
| **Broker** | Kafka 서버 인스턴스 |
| **Replication** | 파티션 복제본으로 장애 대응 |

#### NestJS + Kafka 예시

```typescript
// .env
// KAFKA_BROKERS=localhost:9092

// main.ts - Kafka 마이크로서비스 설정
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.KAFKA,
    options: {
      client: {
        brokers: [process.env.KAFKA_BROKERS ?? 'localhost:9092'],
      },
      consumer: {
        groupId: 'order-service',
      },
    },
  });
  await app.listen();
}
bootstrap();
```

```typescript
// 이벤트 정의
export interface OrderCreatedEvent {
  orderId: number;
  userId: number;
  totalPrice: number;
  createdAt: string;
}

// Producer
import { Injectable, Logger } from '@nestjs/common';
import { ClientKafka, Client, Transport } from '@nestjs/microservices';

@Injectable()
export class OrderEventPublisher {
  private readonly logger = new Logger(OrderEventPublisher.name);

  @Client({
    transport: Transport.KAFKA,
    options: {
      client: { brokers: ['localhost:9092'] },
    },
  })
  private kafkaClient: ClientKafka;

  async publishOrderCreated(order: { id: number; userId: number; totalPrice: number }): Promise<void> {
    const event: OrderCreatedEvent = {
      orderId: order.id,
      userId: order.userId,
      totalPrice: order.totalPrice,
      createdAt: new Date().toISOString(),
    };

    this.kafkaClient.emit('order-events', { key: String(order.id), value: event })
      .subscribe({
        error: (err: Error) => this.logger.error(`이벤트 발행 실패: orderId=${order.id}`, err.stack),
        complete: () => this.logger.log(`이벤트 발행 성공: topic=order-events, orderId=${order.id}`),
      });
  }
}

// Consumer
import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';

@Controller()
export class OrderEventConsumer {
  private readonly logger = new Logger(OrderEventConsumer.name);

  @EventPattern('order-events')
  async handleOrderCreated(@Payload() event: OrderCreatedEvent): Promise<void> {
    this.logger.log(`주문 이벤트 수신: orderId=${event.orderId}`);
    // 알림 발송, 포인트 적립 등
    await this.notificationService.sendOrderConfirmation(event.userId, event.orderId);
  }

  // 에러 처리 (별도 Consumer 그룹)
  @EventPattern('order-events')
  async handleInventoryUpdate(@Payload() event: OrderCreatedEvent): Promise<void> {
    try {
      await this.inventoryService.decreaseStock(event.orderId);
    } catch (e) {
      this.logger.error(`재고 차감 실패: orderId=${event.orderId}`, (e as Error).stack);
      // Dead Letter Topic으로 전송하거나 재시도
      throw e;
    }
  }
}
```

#### 위 Consumer 의 두 핸들러는 "별도 Consumer 그룹" 이 아니다

`handleOrderCreated` 와 `handleInventoryUpdate` 가 같은 `@EventPattern('order-events')` 를 달고 한 컨트롤러에 있다. 주석은 별도 그룹이라고 하지만 **컨슈머 그룹은 `createMicroservice` 의 `consumer.groupId` 로 정해지고 한 프로세스에 하나다.** 같은 앱 안의 두 핸들러가 서로 다른 그룹이 될 수 없다.

같은 토픽을 두 갈래로 처리하려면 선택지는 둘이다.

- **프로세스를 나눈다.** 알림 서비스와 재고 서비스를 각각 다른 `groupId` 로 띄운다. 그러면 한쪽이 실패해도 다른 쪽 오프셋에 영향이 없다 — 이게 컨슈머 그룹을 나누는 진짜 이유다.
- **한 핸들러 안에서 순서대로 부른다.** 대신 재고 차감이 실패하면 알림도 함께 재처리되므로 알림이 여러 번 나갈 수 있다.

두 번째를 고른다면 아래 `throw e` 가 무엇을 뜻하는지 알아야 한다. 예외를 그대로 던지면 오프셋이 커밋되지 않고 **같은 메시지가 계속 다시 온다.** 원인이 일시적 장애가 아니라 잘못된 메시지라면 그 파티션이 그 자리에서 영원히 막힌다(poison message). 재시도로 풀릴 실패와 아닌 실패를 나눠서, 후자는 잡아서 DLT 로 보내고 오프셋은 진행시켜야 한다.

```typescript
try {
  await this.inventoryService.decreaseStock(event.orderId);
} catch (e) {
  if (isRetryable(e)) throw e;                 // 일시적 → 다시 받는다
  await this.dlt.emit('order-events.DLT', { event, error: String(e) });
  // 던지지 않는다 → 오프셋이 진행되고 파티션이 막히지 않는다
}
```

### 3. RabbitMQ

#### 아키텍처

```
Producer → Exchange → Binding → Queue → Consumer
              │
         ┌────┼────┐
       Direct  Topic  Fanout    (Exchange Types)
```

| Exchange 타입 | 라우팅 방식 | 사용 예 |
|-------------|-----------|---------|
| **Direct** | routing key 정확히 매칭 | 특정 서비스로 전달 |
| **Topic** | 패턴 매칭 (`order.*`, `#.error`) | 카테고리별 라우팅 |
| **Fanout** | 모든 바인딩된 큐로 브로드캐스트 | 이벤트 알림 |
| **Headers** | 헤더 속성 기반 | 복잡한 라우팅 조건 |

#### NestJS + RabbitMQ 기본 예시

```typescript
// .env
// RABBITMQ_URL=amqp://guest:guest@localhost:5672

// app.module.ts
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: process.env.RABBITMQ_URL ?? 'amqp://guest:guest@localhost:5672',
      exchanges: [
        { name: 'order.exchange', type: 'topic' },
        { name: 'dlx.exchange', type: 'direct' },
      ],
      queues: [
        {
          name: 'order.created.queue',
          bindingExchanges: [
            { exchange: 'order.exchange', routingKey: 'order.created' },
          ],
          options: {
            durable: true,
            arguments: {
              'x-dead-letter-exchange': 'dlx.exchange',
              'x-dead-letter-routing-key': 'dlq.order.created',
            },
          },
        },
      ],
    }),
  ],
})
export class AppModule {}
```

```typescript
// Producer
import { Injectable } from '@nestjs/common';
import { AmqpConnection } from '@golevelup/nestjs-rabbitmq';

export interface OrderCreatedEvent {
  orderId: number;
  userId: number;
  totalPrice: number;
}

@Injectable()
export class OrderEventPublisher {
  constructor(private readonly amqpConnection: AmqpConnection) {}

  async publishOrderCreated(order: { id: number; userId: number; totalPrice: number }): Promise<void> {
    const event: OrderCreatedEvent = {
      orderId: order.id,
      userId: order.userId,
      totalPrice: order.totalPrice,
    };

    await this.amqpConnection.publish(
      'order.exchange',   // exchange
      'order.created',    // routing key
      event,
    );
  }
}

// Consumer
import { Injectable, Logger } from '@nestjs/common';
import { RabbitSubscribe } from '@golevelup/nestjs-rabbitmq';

@Injectable()
export class OrderEventConsumer {
  private readonly logger = new Logger(OrderEventConsumer.name);

  @RabbitSubscribe({
    exchange: 'order.exchange',
    routingKey: 'order.created',
    queue: 'order.created.queue',
  })
  async handleOrderCreated(event: OrderCreatedEvent): Promise<void> {
    this.logger.log(`주문 이벤트 수신: orderId=${event.orderId}`);
    await this.notificationService.sendOrderConfirmation(event);
  }
}
```

#### 실무 라우팅 패턴

기본 Exchange 타입만으로 해결 안 되는 상황이 생각보다 빨리 온다. 서비스가 3~4개만 넘어가도 라우팅 구조가 복잡해지는데, RabbitMQ는 이걸 해결하는 몇 가지 패턴을 제공한다.

##### Exchange-to-Exchange (E2E) 바인딩

Exchange끼리 바인딩하는 기능이다. AMQP 스펙이 아니라 RabbitMQ 확장 기능이다.

주문이 들어오면 결제, 재고, 알림 세 시스템에 각각 다른 형태로 라우팅해야 하는 경우를 생각해보자. 하나의 Exchange에서 모든 큐로 바인딩하면 관리가 엉망이 된다. Exchange를 계층 구조로 만들면 각 도메인별로 라우팅 책임을 분리할 수 있다.

```
Producer → order.exchange (topic)
              ├──▶ payment.exchange (direct) → payment.queue
              ├──▶ inventory.exchange (direct) → inventory.queue
              └──▶ notification.exchange (fanout) → email.queue
                                                  → sms.queue
```

```typescript
// NestJS + golevelup/nestjs-rabbitmq E2E 바인딩 설정
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: process.env.RABBITMQ_URL ?? 'amqp://localhost:5672',
      exchanges: [
        // 1단계: 메인 Exchange
        { name: 'order.exchange', type: 'topic' },
        // 2단계: 도메인별 하위 Exchange
        { name: 'payment.exchange', type: 'direct' },
        { name: 'notification.exchange', type: 'fanout' },
      ],
      queues: [
        {
          name: 'payment.queue',
          bindingExchanges: [
            { exchange: 'payment.exchange', routingKey: 'order.created' },
          ],
          options: { durable: true },
        },
        {
          name: 'email.queue',
          bindingExchanges: [
            { exchange: 'notification.exchange', routingKey: '' },
          ],
          options: { durable: true },
        },
        {
          name: 'sms.queue',
          bindingExchanges: [
            { exchange: 'notification.exchange', routingKey: '' },
          ],
          options: { durable: true },
        },
      ],
    }),
  ],
})
export class E2EBindingModule {}

// Exchange → Exchange 바인딩은 amqplib를 통해 수동으로 설정
// (golevelup/nestjs-rabbitmq가 E2E 바인딩을 직접 지원하지 않을 경우)
import { Injectable, OnModuleInit } from '@nestjs/common';
import { AmqpConnection } from '@golevelup/nestjs-rabbitmq';

@Injectable()
export class ExchangeBindingSetup implements OnModuleInit {
  constructor(private readonly amqpConnection: AmqpConnection) {}

  async onModuleInit(): Promise<void> {
    const channel = this.amqpConnection.channel;
    // Exchange → Exchange 바인딩
    await channel.bindExchange('payment.exchange', 'order.exchange', 'order.created');
    await channel.bindExchange('notification.exchange', 'order.exchange', 'order.#');
    // Exchange → Queue 바인딩
    await channel.bindQueue('payment.queue', 'payment.exchange', 'order.created');
  }
}
```

이 구조의 장점은 알림 채널을 추가할 때 `notification.exchange`에만 큐를 바인딩하면 된다는 점이다. Producer 코드는 건드릴 필요 없다.

##### Alternate Exchange

routing key가 어디에도 매칭되지 않는 메시지가 들어오면 기본적으로 그냥 버려진다. `mandatory` 플래그를 켜면 Publisher에게 반환되지만, Publisher 쪽에서 반환 처리를 해야 해서 번거롭다.

Alternate Exchange는 라우팅 실패한 메시지를 자동으로 다른 Exchange로 보낸다. 메시지 유실을 막으면서도 Publisher 코드를 깔끔하게 유지할 수 있다.

```
Producer → order.exchange (routing key 매칭 실패)
              │
              └── alternate ──▶ unrouted.exchange (fanout) → unrouted.queue
```

```typescript
// NestJS에서 Alternate Exchange 설정
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: process.env.RABBITMQ_URL ?? 'amqp://localhost:5672',
      exchanges: [
        // 라우팅 실패 메시지를 받을 Exchange
        { name: 'unrouted.exchange', type: 'fanout' },
        // 메인 Exchange에 alternate-exchange 설정
        {
          name: 'order.exchange',
          type: 'topic',
          options: {
            durable: true,
            arguments: { 'alternate-exchange': 'unrouted.exchange' },
          },
        },
      ],
      queues: [
        {
          name: 'unrouted.queue',
          bindingExchanges: [
            { exchange: 'unrouted.exchange', routingKey: '' },
          ],
          options: { durable: true },
        },
      ],
    }),
  ],
})
export class AlternateExchangeModule {}
```

운영 환경에서 `unrouted.queue`를 모니터링하면 라우팅 설정 실수를 빨리 잡을 수 있다. routing key 오타 같은 문제가 여기서 잡힌다.

##### Consistent Hash Exchange

RabbitMQ 기본 제공이 아니라 플러그인(`rabbitmq_consistent_hash_exchange`)을 활성화해야 한다.

```bash
rabbitmq-plugins enable rabbitmq_consistent_hash_exchange
```

같은 키를 가진 메시지가 항상 같은 큐로 간다. 여러 Consumer 인스턴스가 있을 때, 특정 사용자의 메시지를 항상 같은 Consumer가 처리하게 할 수 있다. 순서 보장이 필요한 상황에서 쓴다.

```
Producer → hash.exchange (x-consistent-hash)
              ├── weight:10 ──▶ worker.queue.1 → Consumer A
              ├── weight:10 ──▶ worker.queue.2 → Consumer B
              └── weight:10 ──▶ worker.queue.3 → Consumer C
```

routing key가 `user-123`이면 항상 같은 큐로 간다. weight 값은 해시 링에서 차지하는 비중이다. 모든 큐에 같은 값을 주면 균등 분배된다.

```typescript
// NestJS에서 Consistent Hash Exchange 설정
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: process.env.RABBITMQ_URL ?? 'amqp://localhost:5672',
      exchanges: [
        {
          name: 'hash.exchange',
          type: 'x-consistent-hash', // Exchange 타입 (플러그인 필요)
          options: {
            durable: true,
            arguments: { 'hash-header': 'user-id' }, // 헤더 기반 해싱을 쓸 경우
          },
        },
      ],
      queues: [
        {
          name: 'worker.queue.1',
          bindingExchanges: [
            { exchange: 'hash.exchange', routingKey: '10' }, // routing key 자리에 weight 값을 넣는다
          ],
          options: { durable: true },
        },
        {
          name: 'worker.queue.2',
          bindingExchanges: [
            { exchange: 'hash.exchange', routingKey: '10' },
          ],
          options: { durable: true },
        },
      ],
    }),
  ],
})
export class ConsistentHashModule {}
```

주의할 점이 있다. Consumer 수를 늘리거나 줄이면 해시 링이 재배치된다. 이때 일부 메시지의 라우팅 대상이 바뀌므로, 순서가 중요한 경우 Consumer 수를 쉽게 변경하면 안 된다. Kafka의 파티션 리밸런싱과 비슷한 문제다.

#### DLX + DLQ 전체 흐름

위 기본 예시에서 `x-dead-letter-exchange`를 한 줄 넣는 것만으로는 DLQ가 동작하지 않는다. DLX(Dead Letter Exchange)와 DLQ를 명시적으로 선언하고 바인딩해야 한다.

메시지가 DLX로 가는 조건은 세 가지다:

- Consumer가 `basic.reject` 또는 `basic.nack`으로 메시지를 거부하고 `requeue=false`인 경우
- 메시지 TTL이 만료된 경우
- 큐의 `x-max-length`를 초과한 경우

```
정상 흐름:
  Producer → order.exchange → order.created.queue → Consumer (처리 성공)

실패 흐름:
  Consumer (처리 실패, 3회 재시도 후)
    → order.created.queue에서 reject (requeue=false)
    → dlx.exchange (routing key: dlq.order.created)
    → dlq.order.created.queue
    → DLQ Consumer (로깅, 알림, 수동 재처리)
```

```typescript
// NestJS DLX + DLQ 설정
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: process.env.RABBITMQ_URL ?? 'amqp://localhost:5672',
      exchanges: [
        // === 정상 처리 경로 ===
        { name: 'order.exchange', type: 'topic' },
        // === DLX 경로 ===
        { name: 'dlx.exchange', type: 'direct' },
      ],
      queues: [
        {
          name: 'order.created.queue',
          bindingExchanges: [
            { exchange: 'order.exchange', routingKey: 'order.created' },
          ],
          options: {
            durable: true,
            arguments: {
              'x-dead-letter-exchange': 'dlx.exchange',
              'x-dead-letter-routing-key': 'dlq.order.created',
              'x-message-ttl': 60000,   // 60초 TTL (선택)
              'x-max-length': 10000,    // 큐 최대 길이 (선택)
            },
          },
        },
        {
          name: 'dlq.order.created.queue',
          // DLQ에도 TTL을 걸어서 일정 시간 후 원래 큐로 재진입시킬 수 있다
          bindingExchanges: [
            { exchange: 'dlx.exchange', routingKey: 'dlq.order.created' },
          ],
          options: {
            durable: true,
            arguments: {
              'x-dead-letter-exchange': 'order.exchange',
              'x-dead-letter-routing-key': 'order.created',
              'x-message-ttl': 300000, // 5분 후 원래 큐로 재시도
            },
          },
        },
      ],
    }),
  ],
})
export class DlxModule {}
```

위 설정에서 `dlq.order.created.queue`에 다시 `x-dead-letter-exchange`를 걸어 원래 Exchange로 보내는 패턴이 "재시도 큐" 패턴이다. 5분 후 자동으로 다시 처리를 시도한다. 무한 루프가 되지 않도록 메시지 헤더의 `x-death` 카운트를 확인해서 최대 재시도 횟수를 제한해야 한다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { RabbitSubscribe, Nack } from '@golevelup/nestjs-rabbitmq';
import { ConsumeMessage } from 'amqplib';

@Injectable()
export class DlqConsumer {
  private readonly logger = new Logger(DlqConsumer.name);
  private static readonly MAX_RETRY_COUNT = 3;

  @RabbitSubscribe({
    exchange: 'dlx.exchange',
    routingKey: 'dlq.order.created',
    queue: 'dlq.order.created.queue',
  })
  async handleDeadLetter(msg: unknown, amqpMsg: ConsumeMessage): Promise<Nack | void> {
    const headers = amqpMsg.properties.headers as Record<string, unknown>;
    const xDeath = headers['x-death'] as Array<{ count: number }> | undefined;

    let retryCount = 0;
    if (xDeath && xDeath.length > 0) {
      retryCount = xDeath[0].count;
    }

    if (retryCount >= DlqConsumer.MAX_RETRY_COUNT) {
      // 최대 재시도 초과 → 파킹 큐로 보내거나 DB에 기록
      this.logger.error(
        `최대 재시도 초과. 메시지 파킹 처리: ${JSON.stringify(msg)}`,
      );
      await this.saveToParkingLot(msg);
      return new Nack(false); // requeue=false
    }

    this.logger.warn(`DLQ 메시지 수신. 재시도 횟수: ${retryCount}, 메시지: ${JSON.stringify(msg)}`);
    // TTL 만료 후 자동으로 원래 큐로 재진입
  }

  private async saveToParkingLot(msg: unknown): Promise<void> {
    // DB에 저장하거나 parking-lot 큐로 전송
    // 운영자가 확인 후 수동으로 재처리
  }
}
```

재시도 간격을 점진적으로 늘리고 싶으면 DLQ를 여러 개 만들어서 TTL을 다르게 설정한다. `retry.1.queue` (10초) → `retry.2.queue` (30초) → `retry.3.queue` (5분) 식이다. 구현이 복잡해지므로 Spring의 `RetryTemplate`이나 `spring-retry`를 같이 쓰는 게 관리하기 편하다.

```typescript
// NestJS + golevelup/nestjs-rabbitmq 재시도 설정
// (RabbitMQModule 옵션에서 재시도 전략 설정)
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

RabbitMQModule.forRoot(RabbitMQModule, {
  uri: process.env.RABBITMQ_URL ?? 'amqp://localhost:5672',
  // 3회 재시도, 재시도 간격 1초 → 2초 → 4초 (exponential backoff)
  prefetchCount: 10,
  // Consumer에서 예외 발생 시 Nack(false)를 반환해 DLX로 전달하는 방식을 사용
  // 또는 커스텀 errorHandler를 통해 재시도 로직 구현
  connectionInitOptions: { wait: false },
});

// Consumer에서 직접 재시도 로직 구현 예시
import { Injectable } from '@nestjs/common';
import { RabbitSubscribe, Nack } from '@golevelup/nestjs-rabbitmq';

@Injectable()
export class OrderEventConsumerWithRetry {
  private readonly maxAttempts = 3;

  @RabbitSubscribe({
    exchange: 'order.exchange',
    routingKey: 'order.created',
    queue: 'order.created.queue',
  })
  async handleWithRetry(msg: unknown): Promise<Nack | void> {
    try {
      await this.processMessage(msg);
    } catch {
      // 재시도 모두 실패 시 requeue=false → DLX로 전달
      return new Nack(false);
    }
  }

  private async processMessage(msg: unknown): Promise<void> {
    // 처리 로직
  }
}
```

### 4. 이벤트 기반 아키텍처 패턴

#### Transactional Outbox 패턴

DB 트랜잭션과 메시지 발행의 원자성을 보장하는 패턴이다.

```
문제:
  1. DB에 주문 저장  ← 성공
  2. Kafka에 이벤트 발행  ← 실패  → 불일치!

해결 (Outbox 패턴):
  1. DB 트랜잭션에서 주문 저장 + Outbox 테이블에 이벤트 저장
  2. 별도 프로세스(CDC/Polling)가 Outbox → Kafka로 발행
  3. 발행 완료 후 Outbox 레코드 삭제
```

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { Order } from './order.entity';
import { OutboxEvent } from './outbox-event.entity';

@Injectable()
export class OrderService {
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
    @InjectRepository(OutboxEvent)
    private readonly outboxRepository: Repository<OutboxEvent>,
    private readonly dataSource: DataSource,
  ) {}

  async createOrder(request: CreateOrderRequest): Promise<Order> {
    return this.dataSource.transaction(async (manager) => {
      // 주문 저장
      const order = await manager.save(Order, Order.from(request));

      // 같은 트랜잭션에서 Outbox에 이벤트 저장
      await manager.save(OutboxEvent, {
        aggregateType: 'Order',
        aggregateId: String(order.id),
        eventType: 'OrderCreated',
        payload: JSON.stringify({ orderId: order.id, totalPrice: order.totalPrice }),
      });

      return order;
    });
  }
}
```

위 코드는 3단계 중 1단계뿐이다. 어려운 부분은 전부 빠진 2·3단계에 있다.

**폴링을 여러 인스턴스가 돌리면 같은 행을 집는다.** 서버가 두 대면 둘 다 같은 미발행 이벤트를 읽어 각자 발행한다. 행 잠금이 필요하고, 잠긴 행을 기다리지 않고 건너뛰려면 `FOR UPDATE SKIP LOCKED` 가 사실상 표준이다.

**"발행 후 삭제" 사이에서 죽으면 다시 발행된다.** 발행은 성공했는데 삭제 전에 프로세스가 내려가면 다음 폴링이 같은 이벤트를 또 보낸다. 순서를 뒤집어 "삭제 후 발행"으로 하면 이번엔 유실이 된다. **Outbox 로 얻는 것은 정확히 1회가 아니라 최소 1회다.** 그래서 이 패턴은 컨슈머 쪽 중복 처리와 항상 같이 간다. 중복을 거르려면 이벤트에 고유 ID 를 실어 보내고 컨슈머가 처리한 ID 를 기록해야 하는데, 위 payload 에는 그 ID 가 없다.

**순서가 깨질 수 있다.** 배치로 꺼낸 이벤트를 병렬로 발행하면 같은 주문의 `OrderCreated` 와 `OrderCancelled` 가 뒤바뀌어 도착할 수 있다. aggregate 단위로는 순차 발행하도록 묶거나, 발행 순번을 함께 실어 컨슈머가 판단하게 한다.

**payload 에 무엇을 담을지도 결정 사항이다.** 위처럼 `orderId` 와 `totalPrice` 만 담으면 컨슈머가 나머지를 알기 위해 원본 테이블을 다시 조회하게 되는데, 그 시점엔 값이 이미 바뀌어 있을 수 있다. 이벤트는 **그 시점의 사실**이므로 필요한 값을 그 안에 다 담는 편이 안전하다. 대신 메시지가 커지고, 스키마를 바꿀 때 구·신 컨슈머 호환을 챙겨야 한다.

**Outbox 테이블은 계속 자란다.** 삭제하지 않고 상태 컬럼만 바꾸는 구성이라면 정리 배치가 반드시 필요하고, 삭제하는 구성이라면 발행 이력이 남지 않아 사고 조사가 어려워진다. 어느 쪽이든 운영 작업이 하나 늘어난다 — DB 트랜잭션과 메시지 발행을 붙이는 대가다.

### 5. 에러 처리 전략

| 전략 | 설명 | 적합한 상황 |
|------|------|-----------|
| **재시도** | 일정 횟수 재시도 후 실패 | 일시적 에러 (네트워크, 타임아웃) |
| **Dead Letter Queue** | 실패 메시지를 별도 큐로 이동 | 분석/수동 처리 필요 |
| **Exponential Backoff** | 재시도 간격을 점점 늘림 | 외부 서비스 과부하 방지 |
| **Circuit Breaker** | 연속 실패 시 일시 중단 | 연쇄 장애 방지 |

```typescript
// NestJS + kafkajs 재시도 설정 (main.ts)
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.KAFKA,
    options: {
      client: {
        brokers: [process.env.KAFKA_BROKERS ?? 'localhost:9092'],
        retry: {
          retries: 3,           // 3회 재시도
          initialRetryTime: 1000, // 1초 간격
          factor: 1,            // 고정 간격 (exponential backoff는 factor > 1)
        },
      },
      consumer: {
        groupId: 'order-service',
      },
    },
  });
  await app.listen();
}
bootstrap();
// DLT(Dead Letter Topic)로 전송하려면 Consumer에서 예외 캐치 후 별도 토픽으로 emit
```

## 운영 팁

### 선택 가이드

| 상황 | 추천 |
|------|------|
| 이벤트 소싱, 로그 수집 | **Kafka** |
| 실시간 스트리밍, 대용량 | **Kafka** |
| 단순 작업 큐, RPC 패턴 | **RabbitMQ** |
| 복잡한 라우팅 규칙 | **RabbitMQ** |
| AWS 관리형 | **SQS/SNS** (간단), **MSK** (Kafka) |

### 주의사항

| 항목 | 주의 |
|------|------|
| **멱등성** | 같은 메시지가 여러 번 처리될 수 있음 → Consumer에 멱등성 보장 |
| **순서 보장** | Kafka: 파티션 내에서만 보장. 주문 키로 같은 파티션 유도 |
| **모니터링** | Consumer Lag(지연) 모니터링 필수 |
| **파티션 수** | Consumer 수 ≤ 파티션 수 (초과 시 놀게 됨) |

### 파티션 수는 나중에 고치기 어렵다

"주문 키로 같은 파티션 유도"와 "Consumer 수 ≤ 파티션 수" 는 서로 당긴다. 순서를 보장하려고 키를 고정하면 **그 키의 처리량이 파티션 하나의 처리량으로 묶인다.** 특정 대형 고객의 주문이 몰리면 그 파티션만 밀리고 나머지는 놀게 되는데, 컨슈머를 늘려도 해결되지 않는다.

그렇다고 파티션을 늘리는 것도 간단하지 않다. 기본 파티셔너는 키 해시를 파티션 수로 나눈 나머지를 쓰므로 **파티션 수가 바뀌면 키의 목적지가 바뀐다.** 임의의 키 1,000개로 3에서 6으로 늘려 보면 478개가 다른 파티션으로 옮겨 간다. 옮겨 간 키는 예전 메시지가 옛 파티션에, 새 메시지가 새 파티션에 남으므로 **그 시점을 걸친 순서 보장이 깨진다.** 파티션은 줄일 수도 없다.

그래서 순서가 중요한 토픽은 처음에 정할 때 아래를 같이 본다.

| 정할 것 | 기준 |
|---|---|
| 파티션 수 | 예상 최대 컨슈머 수보다 넉넉하게. 늘리기가 어렵다는 전제로 |
| 키 선택 | 순서를 지켜야 하는 최소 단위로. 넓게 잡으면 병렬성이 죽는다 |
| 순서가 정말 필요한가 | 컨슈머가 순서에 무관하게 동작하도록 만들 수 있으면 그게 가장 싸다 |

마지막 줄이 실무에서 가장 자주 답이 된다. 상태를 덮어쓰는 대신 "이 버전보다 오래된 이벤트는 무시"처럼 컨슈머가 순서 역전을 견디게 만들면, 키 고정도 파티션 증설 걱정도 필요 없어진다.

## 참고

- [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/)
- [RabbitMQ 공식 문서](https://www.rabbitmq.com/documentation.html)
- [Spring for Apache Kafka](https://docs.spring.io/spring-kafka/reference/)
- [Spring AMQP](https://docs.spring.io/spring-amqp/reference/)
- [메시지 큐 및 분산 락](../../Architecture/MSA/메시지_큐_및_분산_락.md)

---
이 문서는 [메시징과 전달 보장 허브](../../_hub/메시징과_전달_보장.md)의 일부입니다.
