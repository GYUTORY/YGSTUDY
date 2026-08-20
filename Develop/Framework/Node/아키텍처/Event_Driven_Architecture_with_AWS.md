---
title: NestJS Event Driven Architecture with AWS
tags: [nodejs, event-driven, aws, messaging]
updated: 2025-12-15
---

# NestJS Event Driven Architecture with AWS
## 목차

1. [개요](#개요)
2. [Event Driven Architecture 기본 개념](#event-driven-architecture-기본-개념)
3. [NestJS에서 EDA 구현 패턴](#nestjs에서-eda-구현-패턴)
4. [AWS SNS/SQS를 활용한 이벤트 버스](#aws-snssqs를-활용한-이벤트-버스)
5. [Lambda를 활용한 이벤트 핸들러](#lambda를-활용한-이벤트-핸들러)
6. [NestJS 마이크로서비스와 AWS 통합](#nestjs-마이크로서비스와-aws-통합)
7. [실전 프로젝트 구조](#실전-프로젝트-구조)
8. [테스트](#테스트)
9. [트러블슈팅](#트러블슈팅)

---

## 개요

### Event Driven Architecture란?

Event Driven Architecture(EDA)는 이벤트의 생성, 감지, 소비, 반응을 중심으로 구성된 아키텍처 패턴이다. 서비스 간 결합을 느슨하게 만들어 확장성과 유연성을 높인다.

### NestJS와 AWS를 활용한 EDA의 장점

```mermaid
graph TD
    A[NestJS EDA + AWS] --> B[확장성]
    A --> C[신뢰성]
    A --> D[비용 효율성]
    A --> E[개발 생산성]
    
    B --> B1[자동 확장]
    B --> B2[무제한 처리량]
    
    C --> C1[메시지 지속성]
    C --> C2[재시도 메커니즘]
    
    D --> D1[서버리스]
    D --> D2[사용한 만큼만 과금]
    
    E --> E1[NestJS 모듈화]
    E --> E2[AWS 관리형 서비스]
    
    style A fill:#4fc3f7
    style B fill:#66bb6a
    style C fill:#ff9800
    style D fill:#9c27b0
    style E fill:#ef5350
```

### 아키텍처 비교

```mermaid
graph LR
    subgraph "전통적 동기 통신"
        A1[Service A] -->|HTTP| A2[Service B]
        A2 -->|HTTP| A3[Service C]
    end
    
    subgraph "Event Driven Architecture"
        B1[Service A] -->|Event| B2[Event Bus]
        B2 -->|Event| B3[Service B]
        B2 -->|Event| B4[Service C]
        B2 -->|Event| B5[Service D]
    end
    
    style B2 fill:#66bb6a
```

---

## Event Driven Architecture 기본 개념

### 핵심 구성 요소

#### 1. Event Producer (이벤트 생산자)
이벤트를 생성하고 발행하는 서비스

#### 2. Event Bus (이벤트 버스)
이벤트를 라우팅하고 전달하는 중앙 허브

#### 3. Event Consumer (이벤트 소비자)
이벤트를 수신하고 처리하는 서비스

### 이벤트 흐름

```mermaid
sequenceDiagram
    participant P as Producer
    participant EB as Event Bus (SNS)
    participant Q as Queue (SQS)
    participant L as Lambda Handler
    participant C as Consumer Service
    
    P->>EB: Publish Event
    EB->>Q: Route to Queue
    Q->>L: Trigger Lambda
    L->>C: Process Event
    C->>Q: Delete Message
```

### 이벤트 설계 원칙

#### 1. 이벤트는 과거 시제로 명명
- 권장: `order.created`
- 권장: `user.registered`
- 권장: `payment.completed`
- 비권장: `create.order`
- 비권장: `register.user`

#### 2. 이벤트는 불변(Immutable)
이벤트는 발생한 사실을 기록하므로 변경할 수 없다.

#### 3. 이벤트는 자급자족(Self-contained)
이벤트를 처리하는 데 필요한 정보를 전부 담아야 한다.

---

## NestJS에서 EDA 구현 패턴

### 그 전에 — 내부 EventEmitter 는 아직 이벤트 기반이 아니다

아래 두 패턴은 이름만 비슷하고 성질이 전혀 다르다. 이걸 구분하지 않으면 "EDA 로 바꿨는데 나아진 게 없다"가 된다.

`EventEmitter` 의 `emit()` 은 **같은 프로세스에서 리스너를 그 자리에서 호출한다.** 직접 확인해보면 이렇다.

```javascript
em.on('x', () => { /* 오래 걸리는 작업 */ console.log('리스너 완료'); });

console.log('emit 직전');
em.emit('x');
console.log('emit 직후');
```

```
emit 직전
리스너 완료      ← 리스너가 먼저 끝난다
emit 직후
```

그래서 다음 세 가지가 따라온다.

**호출 스택이 이어져 있다.** 리스너가 던진 예외는 `emit()` 을 부른 쪽까지 그대로 올라온다. 주문 저장 코드가 이메일 발송 실패로 500 을 내는 상황이 이렇게 만들어진다 — 함수를 직접 부른 것과 결과가 같다.

**async 리스너는 기다려주지 않는다.** 리스너를 `async` 로 만들면 `emit()` 은 그 안의 `await` 를 기다리지 않고 곧장 반환한다. 실패해도 아무도 모르고, 처리되지 않은 프로미스 거부만 남는다.

```
emit 직후          ← 먼저 찍힌다
async 리스너 완료   ← 나중
```

**트랜잭션이 아직 열려 있다.** 서비스 메서드 안에서 `emit()` 하면 커밋 전에 리스너가 돈다. 뒤에서 롤백되면 **DB 에는 없는 주문에 대한 이메일이 나간 상태**가 된다. 이 문제를 피하려고 나온 것이 아웃박스 패턴이다 — 이벤트를 같은 트랜잭션 안의 테이블에 쓰고, 커밋된 뒤 별도 프로세스가 발행한다.

정리하면 `EventEmitter` 는 **코드 구조를 정리하는 도구**지 서비스를 분리하는 도구가 아니다. 프로세스가 죽으면 대기 중인 이벤트도 같이 사라진다.

| | EventEmitter | SNS/SQS |
|---|---|---|
| 실행 위치 | 같은 프로세스 | 다른 프로세스·다른 서비스 |
| 발행자 영향 | 리스너 예외가 전파된다 | 격리된다 |
| 유실 | 프로세스가 죽으면 사라진다 | 큐에 남는다 |
| 재시도 | 없다 | 큐가 해준다 |
| 얻는 것 | 코드 정리 | 실제 결합도 분리 |

**진짜로 분리해야 하는 경계에만 SNS/SQS 를 쓰고, 나머지는 EventEmitter 로 두는 것**이 현실적이다. 전부 큐로 보내면 디버깅 비용만 늘어난다.

### 패턴 1: 내부 이벤트 버스 (EventEmitter)

간단한 내부 이벤트를 처리할 때 쓰는 패턴이다.

#### 이벤트 모듈 생성

```typescript
// src/events/events.module.ts
import { Module } from '@nestjs/common';
import { EventEmitterModule } from '@nestjs/event-emitter';
import { OrdersModule } from '../orders/orders.module';
import { EmailModule } from '../email/email.module';

@Module({
  imports: [
    EventEmitterModule.forRoot({
      wildcard: true,
      delimiter: '.',
      maxListeners: 10,
      verboseMemoryLeak: true,
    }),
    OrdersModule,
    EmailModule,
  ],
})
export class EventsModule {}
```

#### 이벤트 발행

```typescript
// src/orders/orders.service.ts
import { Injectable } from '@nestjs/common';
import { EventEmitter2 } from '@nestjs/event-emitter';

@Injectable()
export class OrdersService {
  constructor(private eventEmitter: EventEmitter2) {}

  async createOrder(orderData: any) {
    const order = await this.saveOrder(orderData);

    // 이벤트 발행
    this.eventEmitter.emit('order.created', {
      orderId: order.id,
      userId: order.userId,
      items: order.items,
      totalAmount: order.totalAmount,
      timestamp: new Date(),
    });

    return order;
  }
}
```

#### 이벤트 구독

```typescript
// src/email/email.service.ts
import { Injectable } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';

@Injectable()
export class EmailService {
  @OnEvent('order.created')
  async handleOrderCreated(payload: {
    orderId: string;
    userId: string;
    items: any[];
    totalAmount: number;
  }) {
    console.log('Sending order confirmation email:', payload.orderId);
    
    // 이메일 발송 로직
    await this.sendEmail({
      to: payload.userId,
      subject: '주문 확인',
      body: `주문 번호: ${payload.orderId}`,
    });
  }
}
```

### 패턴 2: AWS SNS 기반 이벤트 버스

분산 환경에서 쓰는 패턴이다.

#### 이벤트 버스 서비스

```typescript
// src/events/aws-event-bus.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { SNSClient, PublishCommand } from '@aws-sdk/client-sns';

export interface DomainEvent {
  eventType: string;
  eventVersion: string;
  aggregateId: string;
  occurredOn: string;
  data: Record<string, any>;
  metadata?: Record<string, any>;
}

@Injectable()
export class AwsEventBusService {
  private readonly logger = new Logger(AwsEventBusService.name);
  private readonly snsClient: SNSClient;
  private readonly topicArnPrefix: string;

  constructor(private configService: ConfigService) {
    this.snsClient = new SNSClient({
      region: this.configService.get<string>('AWS_REGION'),
    });

    this.topicArnPrefix = this.configService.get<string>('AWS_SNS_TOPIC_ARN_PREFIX');
  }

  /**
   * 도메인 이벤트 발행
   */
  async publish(event: DomainEvent): Promise<string> {
    const topicArn = `${this.topicArnPrefix}:${event.eventType}`;

    try {
      const command = new PublishCommand({
        TopicArn: topicArn,
        Message: JSON.stringify(event),
        MessageAttributes: {
          'event-type': {
            DataType: 'String',
            StringValue: event.eventType,
          },
          'event-version': {
            DataType: 'String',
            StringValue: event.eventVersion,
          },
          'aggregate-id': {
            DataType: 'String',
            StringValue: event.aggregateId,
          },
        },
      });

      const response = await this.snsClient.send(command);
      
      this.logger.log({
        message: 'Event published',
        eventType: event.eventType,
        messageId: response.MessageId,
        aggregateId: event.aggregateId,
      });

      return response.MessageId;
    } catch (error) {
      this.logger.error({
        message: 'Failed to publish event',
        eventType: event.eventType,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * 여러 이벤트 배치 발행
   */
  async publishBatch(events: DomainEvent[]): Promise<string[]> {
    const results = await Promise.allSettled(
      events.map(event => this.publish(event))
    );

    const messageIds: string[] = [];
    const errors: Error[] = [];

    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        messageIds.push(result.value);
      } else {
        errors.push(new Error(`Failed to publish event ${events[index].eventType}: ${result.reason}`));
      }
    });

    if (errors.length > 0) {
      this.logger.error({
        message: 'Some events failed to publish',
        errors: errors.map(e => e.message),
      });
    }

    return messageIds;
  }
}
```

#### 토픽 ARN 을 문자열로 조립하는 부분이 뒤의 Terraform 과 맞지 않는다

```typescript
const topicArn = `${this.topicArnPrefix}:${event.eventType}`;
```

이 코드는 **이벤트 타입마다 토픽이 하나씩 있다**고 전제한다. `order.created`, `order.cancelled`, `user.registered` 각각에 토픽이 필요하다. 그런데 뒤의 Terraform 은 `order-events`, `user-events` 두 개만 만든다 — **도메인마다 하나**다. 둘 중 하나는 반드시 틀린다.

거기에 이름 규칙도 걸린다. SNS 토픽 이름에는 영숫자와 하이픈·밑줄만 쓸 수 있다([CreateTopic 문서](https://docs.aws.amazon.com/sns/latest/api/API_CreateTopic.html)). `order.created` 처럼 점이 들어간 이름은 만들 수 없으므로, 위 문자열로 조립한 ARN 은 **존재할 수 없는 토픽을 가리킨다.** 발행은 런타임에 `NotFound` 로 실패한다.

두 설계 중 무엇을 고를지는 취향이 아니라 운영 방식의 문제다.

| | 이벤트 타입마다 토픽 | 도메인마다 토픽 + 속성 필터 |
|---|---|---|
| 새 이벤트 추가 | 인프라 변경(토픽 + 구독)이 필요하다 | 코드만 바꾸면 된다 |
| 구독자가 원하는 것만 받기 | 토픽을 골라 구독 | `FilterPolicy` 로 거른다 |
| 토픽 개수 | 이벤트 종류만큼 늘어난다 | 도메인 수로 유지된다 |
| 권한 관리 | 토픽 단위로 세밀하게 | 도메인 단위로 뭉뚱그려진다 |

**"새 이벤트를 추가할 때 인프라 코드를 고쳐야 하는가"** 가 실질적인 갈림길이다. 대부분은 후자를 고르고, 그러면 `MessageAttributes` 에 `event-type` 을 싣는 위 코드가 그대로 값을 한다 — 다만 **구독 쪽에 `FilterPolicy` 를 걸어야** 의미가 생긴다. 뒤의 Terraform 구독에는 필터가 없어서, 지금 상태로는 `order-events` 를 구독한 이메일 큐가 주문 취소·환불 이벤트까지 전부 받는다.

#### `publishBatch` 는 실패를 삼킨다

`Promise.allSettled` 로 결과를 모은 뒤 실패는 로그만 남기고, 반환값은 **성공한 messageId 배열**뿐이다. 호출자가 `events.length` 와 반환 길이를 비교하지 않는 한 일부가 안 나갔다는 사실을 알 방법이 없다.

이름도 오해를 부른다. "배치 발행"이지만 원자적이지 않아서 **절반만 나가는 상태**가 정상 경로에 있다. 주문 하나에 이벤트 세 개를 함께 발행했는데 두 개만 나가면, 그 시점부터 다운스트림 상태가 어긋난다.

```typescript
async publishBatch(events: DomainEvent[]): Promise<{ succeeded: string[]; failed: DomainEvent[] }> {
  // 실패 목록을 반환해 호출자가 재시도하거나 실패로 처리하게 한다
}
```

동시성 제한이 없다는 것도 함께 봐야 한다. `events.map(publish)` 는 이벤트 수만큼 SNS 요청을 동시에 띄운다. 아웃박스에 밀린 이벤트 수천 건을 한 번에 넘기면 그대로 throttling 을 맞고, 그 실패는 위 로직에서 조용히 사라진다. 동시 실행 수에 상한을 두거나 SNS 의 `PublishBatch`(호출당 10건)를 쓴다.

그리고 이 서비스는 **트랜잭션 안에서 부르면 안 된다.** 앞 절에서 `EventEmitter` 에 대해 말한 문제가 여기서는 더 나쁘다 — 커밋 전에 발행하고 뒤에서 롤백되면, 내부 이벤트와 달리 **SNS 로 나간 메시지는 되돌릴 수 없다.** 아웃박스 테이블에 쓰고 커밋 후 별도 프로세스가 발행하는 구조가 사실상 필수다.

#### 이벤트 팩토리

```typescript
// src/events/event.factory.ts
import { DomainEvent } from './aws-event-bus.service';

export class EventFactory {
  static createOrderCreatedEvent(data: {
    orderId: string;
    userId: string;
    items: Array<{ productId: string; quantity: number }>;
    totalAmount: number;
  }): DomainEvent {
    return {
      eventType: 'order.created',
      eventVersion: '1.0',
      aggregateId: data.orderId,
      occurredOn: new Date().toISOString(),
      data,
      metadata: {
        source: 'order-service',
        correlationId: this.generateCorrelationId(),
      },
    };
  }

  static createUserRegisteredEvent(data: {
    userId: string;
    email: string;
    name: string;
  }): DomainEvent {
    return {
      eventType: 'user.registered',
      eventVersion: '1.0',
      aggregateId: data.userId,
      occurredOn: new Date().toISOString(),
      data,
      metadata: {
        source: 'user-service',
        correlationId: this.generateCorrelationId(),
      },
    };
  }

  private static generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

#### 사용 예제

```typescript
// src/orders/orders.service.ts
import { Injectable } from '@nestjs/common';
import { AwsEventBusService } from '../events/aws-event-bus.service';
import { EventFactory } from '../events/event.factory';

@Injectable()
export class OrdersService {
  constructor(private eventBus: AwsEventBusService) {}

  async createOrder(orderData: any) {
    const order = await this.saveOrder(orderData);

    // 이벤트 생성 및 발행
    const event = EventFactory.createOrderCreatedEvent({
      orderId: order.id,
      userId: order.userId,
      items: order.items,
      totalAmount: order.totalAmount,
    });

    await this.eventBus.publish(event);

    return order;
  }
}
```

---

## AWS SNS/SQS를 활용한 이벤트 버스

### 이벤트 버스 아키텍처

```mermaid
graph TB
    A[NestJS Services] -->|Publish Events| B[SNS Topics]
    B -->|Subscribe| C[SQS Queues]
    C -->|Trigger| D[Lambda Functions]
    C -->|Poll| E[NestJS Consumers]
    
    D -->|Process| F[External Services]
    E -->|Process| G[Internal Services]
    
    style A fill:#4fc3f7
    style B fill:#66bb6a
    style C fill:#ff9800
    style D fill:#9c27b0
    style E fill:#4fc3f7
```

### SQS 기반 이벤트 소비자 구현

#### 이벤트 소비자 서비스

```typescript
// src/events/sqs-event-consumer.service.ts
import { Injectable, Logger, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  SQSClient,
  ReceiveMessageCommand,
  DeleteMessageCommand,
} from '@aws-sdk/client-sqs';
import { DomainEvent } from './aws-event-bus.service';

export interface EventHandler {
  handle(event: DomainEvent): Promise<void>;
}

@Injectable()
export class SqsEventConsumerService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(SqsEventConsumerService.name);
  private readonly sqsClient: SQSClient;
  private readonly queueUrl: string;
  private readonly handlers = new Map<string, EventHandler[]>();
  private isPolling = false;
  private pollingInterval: NodeJS.Timeout;

  constructor(private configService: ConfigService) {
    this.sqsClient = new SQSClient({
      region: this.configService.get<string>('AWS_REGION'),
    });

    this.queueUrl = this.configService.get<string>('EVENT_QUEUE_URL');
  }

  /**
   * 이벤트 핸들러 등록
   */
  registerHandler(eventType: string, handler: EventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
  }

  /**
   * 모듈 초기화 시 폴링 시작
   */
  async onModuleInit() {
    this.logger.log('Starting event consumer polling');
    this.startPolling();
  }

  /**
   * 모듈 종료 시 폴링 중지
   */
  async onModuleDestroy() {
    this.logger.log('Stopping event consumer polling');
    this.stopPolling();
  }

  /**
   * 메시지 폴링 시작
   */
  private startPolling() {
    this.isPolling = true;
    this.poll();
  }

  /**
   * 메시지 폴링 중지
   */
  private stopPolling() {
    this.isPolling = false;
    if (this.pollingInterval) {
      clearTimeout(this.pollingInterval);
    }
  }

  /**
   * 메시지 폴링 및 처리
   */
  private async poll() {
    if (!this.isPolling) {
      return;
    }

    try {
      const command = new ReceiveMessageCommand({
        QueueUrl: this.queueUrl,
        MaxNumberOfMessages: 10,
        WaitTimeSeconds: 20, // Long Polling
        MessageAttributeNames: ['All'],
      });

      const response = await this.sqsClient.send(command);

      if (response.Messages && response.Messages.length > 0) {
        await this.processMessages(response.Messages);
      }

      // 다음 폴링 예약
      this.pollingInterval = setTimeout(() => this.poll(), 100);
    } catch (error) {
      this.logger.error('Error polling messages:', error);
      // 에러 발생 시 잠시 대기 후 재시도
      this.pollingInterval = setTimeout(() => this.poll(), 5000);
    }
  }

  /**
   * 메시지 처리
   */
  private async processMessages(messages: any[]) {
    const promises = messages.map(async (message) => {
      try {
        // SNS 메시지 형식 파싱
        const snsMessage = JSON.parse(message.Body);
        const event: DomainEvent = JSON.parse(snsMessage.Message);

        // 이벤트 타입에 맞는 핸들러 실행
        const handlers = this.handlers.get(event.eventType) || [];
        
        await Promise.all(
          handlers.map(handler => handler.handle(event))
        );

        // 처리 완료 후 메시지 삭제
        await this.deleteMessage(message.ReceiptHandle);
        
        this.logger.log({
          message: 'Event processed successfully',
          eventType: event.eventType,
          aggregateId: event.aggregateId,
        });
      } catch (error) {
        this.logger.error({
          message: 'Failed to process event',
          error: error.message,
          messageId: message.MessageId,
        });
        // 에러 발생 시 메시지는 삭제하지 않음 (재시도)
      }
    });

    await Promise.allSettled(promises);
  }

  /**
   * 메시지 삭제
   */
  private async deleteMessage(receiptHandle: string) {
    try {
      const command = new DeleteMessageCommand({
        QueueUrl: this.queueUrl,
        ReceiptHandle: receiptHandle,
      });

      await this.sqsClient.send(command);
    } catch (error) {
      this.logger.error('Failed to delete message:', error);
    }
  }
}
```

#### 이 폴러가 조용히 메시지를 중복 처리하는 자리

**메시지 10건을 `Promise.all` 로 동시에 처리하는데, 가시성 타임아웃(visibility timeout)에 대한 처리가 없다.** SQS 는 메시지를 꺼내준 뒤 정해진 시간 동안만 다른 소비자에게 숨긴다. 그 시간 안에 `DeleteMessage` 가 안 오면 메시지는 다시 보이게 되고, **첫 번째 처리가 아직 돌고 있는 중에 두 번째 소비자가 같은 메시지를 가져간다.**

핸들러가 무거울수록, 배치가 클수록 이 확률이 올라간다. 10건을 동시에 처리하다 보면 뒤쪽 건이 늦게 끝나기 쉽다. 대응은 셋 중 하나다.

- 큐의 가시성 타임아웃을 **최악의 처리 시간보다 넉넉하게** 잡는다
- 처리가 길어지면 `ChangeMessageVisibility` 로 연장한다(하트비트)
- 한 번에 가져오는 개수를 줄인다

어느 쪽을 택하든 **중복 수신을 없앨 수는 없다.** SQS 표준 큐는 최소 한 번 전달이라, 네트워크 사정만으로도 같은 메시지가 두 번 온다. 핸들러는 두 번 실행돼도 결과가 같아야 한다.

`catch` 블록의 주석도 정확하지 않다. "에러 발생 시 메시지는 삭제하지 않음 (재시도)" 는 맞지만, **재시도 횟수 제한이 없다.** 항상 실패하는 메시지 하나가 있으면 그것만 무한히 되돌아오며 큐를 붙잡는다. 큐에 **DLQ(Dead Letter Queue)와 `maxReceiveCount`** 를 붙여야 그 메시지가 빠져나간다. 아래 Terraform 절의 `redrive_policy` 가 그 설정이다 — 코드가 아니라 인프라 쪽에 있어서 잊기 쉽다.

마지막으로 `poll()` 의 에러 경로는 항상 5초 후 재시도다. 자격증명 만료나 큐 삭제처럼 **회복되지 않는 오류에서도 같은 간격으로 영원히 반복**하며 에러 로그만 쌓는다. 지수 백오프와 상한을 둔다.

#### 이벤트 핸들러 데코레이터

```typescript
// src/events/event-handler.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const EVENT_HANDLER_KEY = 'event:handler';

export const EventHandler = (eventType: string) =>
  SetMetadata(EVENT_HANDLER_KEY, eventType);
```

#### 이벤트 핸들러 구현

```typescript
// src/email/email.event-handler.ts
import { Injectable, Logger } from '@nestjs/common';
import { EventHandler } from '../events/event-handler.decorator';
import { DomainEvent, EventHandler as IEventHandler } from '../events/sqs-event-consumer.service';

@Injectable()
export class EmailEventHandler implements IEventHandler {
  private readonly logger = new Logger(EmailEventHandler.name);

  @EventHandler('order.created')
  async handleOrderCreated(event: DomainEvent) {
    this.logger.log(`Handling order.created event: ${event.aggregateId}`);
    
    const { orderId, userId, totalAmount } = event.data;
    
    // 이메일 발송 로직
    await this.sendOrderConfirmationEmail(userId, {
      orderId,
      totalAmount,
    });
  }

  @EventHandler('user.registered')
  async handleUserRegistered(event: DomainEvent) {
    this.logger.log(`Handling user.registered event: ${event.aggregateId}`);
    
    const { userId, email, name } = event.data;
    
    // 환영 이메일 발송
    await this.sendWelcomeEmail(email, { name });
  }

  async handle(event: DomainEvent): Promise<void> {
    // 이벤트 타입에 따라 적절한 메서드 호출
    switch (event.eventType) {
      case 'order.created':
        await this.handleOrderCreated(event);
        break;
      case 'user.registered':
        await this.handleUserRegistered(event);
        break;
      default:
        this.logger.warn(`Unknown event type: ${event.eventType}`);
    }
  }

  private async sendOrderConfirmationEmail(userId: string, data: any) {
    // 이메일 발송 구현
  }

  private async sendWelcomeEmail(email: string, data: any) {
    // 이메일 발송 구현
  }
}
```

---

## Lambda를 활용한 이벤트 핸들러

### Lambda 함수 구조

#### Lambda 핸들러 예제

```typescript
// lambda/order-processor/index.ts
import { SQSHandler, SQSEvent } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';

const dynamoClient = DynamoDBDocumentClient.from(new DynamoDBClient({}));

interface OrderCreatedEvent {
  eventType: 'order.created';
  eventVersion: string;
  aggregateId: string;
  occurredOn: string;
  data: {
    orderId: string;
    userId: string;
    items: Array<{ productId: string; quantity: number }>;
    totalAmount: number;
  };
}

export const handler: SQSHandler = async (event: SQSEvent) => {
  console.log('Received SQS event:', JSON.stringify(event, null, 2));

  for (const record of event.Records) {
    try {
      // SNS 메시지 파싱
      const snsMessage = JSON.parse(record.body);
      const domainEvent: OrderCreatedEvent = JSON.parse(snsMessage.Message);

      console.log('Processing event:', domainEvent.eventType);

      // 이벤트 타입별 처리
      switch (domainEvent.eventType) {
        case 'order.created':
          await handleOrderCreated(domainEvent);
          break;
        default:
          console.warn(`Unknown event type: ${domainEvent.eventType}`);
      }
    } catch (error) {
      console.error('Error processing event:', error);
      throw error; // 재시도 트리거
    }
  }
};

async function handleOrderCreated(event: OrderCreatedEvent) {
  const { orderId, userId, items, totalAmount } = event.data;

  // 주문 정보를 DynamoDB에 저장
  await dynamoClient.send(
    new PutCommand({
      TableName: process.env.ORDERS_TABLE_NAME!,
      Item: {
        orderId,
        userId,
        items,
        totalAmount,
        status: 'created',
        createdAt: new Date().toISOString(),
      },
    })
  );

  // 재고 차감 로직
  for (const item of items) {
    await updateInventory(item.productId, item.quantity);
  }

  console.log(`Order ${orderId} processed successfully`);
}

async function updateInventory(productId: string, quantity: number) {
  // 재고 업데이트 로직
  console.log(`Updating inventory for product ${productId}: -${quantity}`);
}
```

#### `throw error; // 재시도 트리거` 는 **배치 전체**를 재시도한다

이 한 줄이 이 코드에서 가장 위험하다. `serverless.yml` 의 `batchSize: 10` 과 맞물리면, 10건 중 7번째가 실패했을 때 **이미 성공한 1~6번까지 다시 온다.**

> When your Lambda function encounters an error while processing a batch, all messages in that batch become visible in the queue again by default, including messages that Lambda processed successfully. As a result, your function can end up processing the same message several times.
>
> — [Handling errors for an SQS event source in Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)

이 핸들러가 하는 일이 DynamoDB 저장과 **재고 차감**이라는 점이 결정적이다. `updateInventory` 가 상대적 차감(`-quantity`)이라면 재시도마다 재고가 또 깎인다. 1~6번 주문의 재고가 두 번, 세 번 빠진다. 그리고 이건 에러가 아니라 **AWS 가 설계대로 동작한 결과**라서 어디에도 경고가 안 뜬다.

거기에 더해, `for` 루프 안에서 `throw` 하면 **8~10번 레코드는 처리조차 되지 않는다.** 실패한 7번 하나 때문에 뒤쪽이 통째로 건너뛰어지고, 재시도 때 다시 1번부터 시작한다.

고치는 방법은 이벤트 소스 매핑에 `ReportBatchItemFailures` 를 켜고, 실패한 메시지 ID 만 돌려주는 것이다.

```typescript
export const handler = async (event: SQSEvent): Promise<SQSBatchResponse> => {
  const batchItemFailures: SQSBatchItemFailure[] = [];

  for (const record of event.Records) {
    try {
      const snsMessage = JSON.parse(record.body);
      await route(JSON.parse(snsMessage.Message));
    } catch (error) {
      console.error('record 처리 실패', record.messageId, error);
      batchItemFailures.push({ itemIdentifier: record.messageId });   // 이 건만 되돌린다
    }
  }
  return { batchItemFailures };
};
```

```yaml
# serverless.yml — 이 설정이 없으면 위 반환값은 무시된다
functionResponseTypes:
  - ReportBatchItemFailures
```

**설정과 코드가 둘 다 있어야 동작한다.** 코드만 고치고 이벤트 소스 매핑을 안 바꾸면 반환값이 버려지고, 예전처럼 배치 전체가 되돌아온다. 반대로 설정만 켜고 코드가 여전히 `throw` 하면 AWS 문서가 말하는 그대로다 — *"If your function throws an exception, the entire batch is considered a complete failure."*

그리고 **재시도가 정상 동작이라는 전제를 코드에 반영해야 한다.** 부분 배치 응답을 켜도 같은 메시지가 두 번 올 수 있다(SQS 표준 큐는 최소 한 번 전달이다). 재고 차감처럼 반복하면 안 되는 작업은 이벤트 ID 로 처리 여부를 기록하고 건너뛰거나, 상대적 차감 대신 "이 주문 이후의 재고는 얼마"처럼 결과가 같아지는 형태로 만든다.

### Lambda 배포 설정

#### serverless.yml 예제

```yaml
service: order-processor

provider:
  name: aws
  runtime: nodejs18.x
  region: ap-northeast-2
  environment:
    ORDERS_TABLE_NAME: ${self:custom.ordersTableName}
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:PutItem
            - dynamodb:UpdateItem
          Resource: arn:aws:dynamodb:${self:provider.region}:*:table/${self:provider.environment.ORDERS_TABLE_NAME}

functions:
  orderProcessor:
    handler: lambda/order-processor/index.handler
    events:
      - sqs:
          arn: arn:aws:sqs:${self:provider.region}:*:order-queue
          batchSize: 10
          maximumBatchingWindowInSeconds: 5
    timeout: 30
    memorySize: 256
    reservedConcurrentExecutions: 10

resources:
  Resources:
    OrdersTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:provider.environment.ORDERS_TABLE_NAME}
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: orderId
            AttributeType: S
        KeySchema:
          - AttributeName: orderId
            KeyType: HASH
```

---

## NestJS 마이크로서비스와 AWS 통합

### 하이브리드 아키텍처

```mermaid
graph TB
    A[API Gateway] --> B[Order Service]
    A --> C[User Service]
    
    B -->|Publish| D[SNS]
    C -->|Publish| D
    
    D -->|Subscribe| E[SQS Queue 1]
    D -->|Subscribe| F[SQS Queue 2]
    
    E -->|Trigger| G[Lambda 1]
    F -->|Poll| H[NestJS Consumer]
    
    G --> I[External Service]
    H --> J[Internal Service]
    
    style A fill:#4fc3f7
    style B fill:#66bb6a
    style C fill:#66bb6a
    style D fill:#ff9800
    style E fill:#9c27b0
    style F fill:#9c27b0
    style G fill:#ef5350
    style H fill:#4fc3f7
```

### NestJS 마이크로서비스 설정

#### 마이크로서비스 모듈

```typescript
// src/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { OrdersModule } from './orders/orders.module';
import { EventsModule } from './events/events.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    EventsModule,
    OrdersModule,
  ],
})
export class AppModule {}
```

#### 이벤트 모듈 통합

```typescript
// src/events/events.module.ts
import { Module } from '@nestjs/common';
import { AwsEventBusService } from './aws-event-bus.service';
import { SqsEventConsumerService } from './sqs-event-consumer.service';
import { EmailEventHandler } from '../email/email.event-handler';

@Module({
  providers: [
    AwsEventBusService,
    SqsEventConsumerService,
    EmailEventHandler,
  ],
  exports: [AwsEventBusService],
})
export class EventsModule {
  constructor(
    private consumer: SqsEventConsumerService,
    private emailHandler: EmailEventHandler,
  ) {
    // 이벤트 핸들러 등록
    this.consumer.registerHandler('order.created', this.emailHandler);
    this.consumer.registerHandler('user.registered', this.emailHandler);
  }
}
```

---

## 실전 프로젝트 구조

### 프로젝트 디렉토리 구조

```
project/
├── src/
│   ├── events/
│   │   ├── aws-event-bus.service.ts
│   │   ├── sqs-event-consumer.service.ts
│   │   ├── event.factory.ts
│   │   ├── event-handler.decorator.ts
│   │   └── events.module.ts
│   ├── orders/
│   │   ├── orders.controller.ts
│   │   ├── orders.service.ts
│   │   └── orders.module.ts
│   ├── email/
│   │   ├── email.service.ts
│   │   ├── email.event-handler.ts
│   │   └── email.module.ts
│   └── app.module.ts
├── lambda/
│   ├── order-processor/
│   │   ├── index.ts
│   │   └── package.json
│   └── inventory-updater/
│       ├── index.ts
│       └── package.json
├── infrastructure/
│   ├── terraform/
│   │   ├── sns.tf
│   │   ├── sqs.tf
│   │   └── lambda.tf
│   └── serverless/
│       └── serverless.yml
├── test/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── package.json
```

### Terraform 인프라 설정

#### SNS Topic 생성

```hcl
# infrastructure/terraform/sns.tf
resource "aws_sns_topic" "order_events" {
  name              = "order-events"
  display_name      = "Order Events"
  
  tags = {
    Environment = var.environment
    Service     = "order-service"
  }
}

resource "aws_sns_topic" "user_events" {
  name              = "user-events"
  display_name      = "User Events"
  
  tags = {
    Environment = var.environment
    Service     = "user-service"
  }
}
```

#### SQS Queue 및 구독 설정

```hcl
# infrastructure/terraform/sqs.tf
resource "aws_sqs_queue" "order_email_queue" {
  name                      = "order-email-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_email_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "order_email_dlq" {
  name = "order-email-queue-dlq"
}

resource "aws_sns_topic_subscription" "order_email_subscription" {
  topic_arn = aws_sns_topic.order_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.order_email_queue.arn
}

resource "aws_sqs_queue_policy" "order_email_queue_policy" {
  queue_url = aws_sqs_queue.order_email_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.order_email_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.order_events.arn
          }
        }
      }
    ]
  })
}
```

#### 이 구독 설정에서 나오는 두 가지

**하나, 메시지가 봉투에 싸여 온다.** `aws_sns_topic_subscription` 에 `raw_message_delivery` 를 지정하지 않으면 기본값은 꺼짐이고, SQS 는 SNS 가 감싼 JSON 을 받는다. 그래서 앞의 소비자 코드가 두 번 파싱한다.

```typescript
const snsMessage = JSON.parse(message.Body);      // SNS 봉투
const event: DomainEvent = JSON.parse(snsMessage.Message);   // 실제 이벤트
```

이 코드는 지금 설정과는 맞는다. 문제는 **나중에 `raw_message_delivery = true` 로 바꾸면 조용히 깨진다**는 점이다. 그때 `message.Body` 는 이벤트 JSON 자체라서 `snsMessage.Message` 가 `undefined` 가 되고, `JSON.parse(undefined)` 가 던진다. 인프라 설정 한 줄이 애플리케이션 파싱 코드의 전제라는 것을 어딘가에 적어 두지 않으면 반드시 밟는다.

여기에 딸린 것이 **`MessageAttributes` 의 위치**다. 발행자는 `event-type` 등을 SNS 속성으로 실었고 소비자는 `MessageAttributeNames: ['All']` 로 요청한다. 그런데 봉투 방식에서는 그 속성들이 봉투 JSON 안에 들어가 있지 SQS 메시지 속성으로 올라오지 않는다. **소비자가 요청한 자리에는 아무것도 없다.** 속성을 SQS 레벨에서 쓰려면 raw 전달을 켜야 하고, 그러면 위 파싱을 고쳐야 한다. 둘은 한 세트로 결정한다.

**둘, 구독에 필터가 없다.** `order-events` 토픽의 모든 이벤트가 `order-email-queue` 로 들어간다. 이메일 서비스는 자기와 무관한 이벤트까지 받아서 하나씩 걸러야 하고, 그 판별을 빠뜨리면 엉뚱한 메일이 나간다. 발행자가 이미 `event-type` 속성을 싣고 있으니 구독에서 받을 것을 선언하는 편이 낫다.

```hcl
resource "aws_sns_topic_subscription" "order_email_subscription" {
  topic_arn     = aws_sns_topic.order_events.arn
  protocol      = "sqs"
  endpoint      = aws_sqs_queue.order_email_queue.arn
  filter_policy = jsonencode({ "event-type" = ["order.created"] })
}
```

큐 설정 자체는 잘 잡혀 있다 — `receive_wait_time_seconds = 20`(롱 폴링), DLQ + `maxReceiveCount = 3`, 14일 보존. 다만 `visibility_timeout_seconds = 300` 은 앞 절의 지적과 함께 봐야 한다. **가시성 타임아웃은 "한 메시지를 처리하는 데 걸리는 최악 시간"보다 커야 하고**, 람다를 연결한다면 람다 타임아웃보다도 커야 한다. 이 값이 처리 시간보다 짧으면 같은 이벤트가 중복 처리되고, DLQ 로 가기 전에 `maxReceiveCount` 만 축낸다.

DLQ 도 만들어 두는 것으로 끝나지 않는다. **DLQ 에 메시지가 쌓이는 것을 알려 주는 경보가 없으면 그건 조용한 쓰레기통이다.** `ApproximateNumberOfMessagesVisible` 에 알람을 걸고, 원인을 고친 뒤 원래 큐로 되돌리는 절차까지 정해 둬야 이 구성이 완성된다.

---

## 테스트

### 단위 테스트

```typescript
// src/events/aws-event-bus.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { AwsEventBusService } from './aws-event-bus.service';
import { SNSClient } from '@aws-sdk/client-sns';

describe('AwsEventBusService', () => {
  let service: AwsEventBusService;
  let snsClient: jest.Mocked<SNSClient>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AwsEventBusService,
        {
          provide: ConfigService,
          useValue: {
            get: jest.fn((key: string) => {
              const config = {
                AWS_REGION: 'ap-northeast-2',
                AWS_SNS_TOPIC_ARN_PREFIX: 'arn:aws:sns:ap-northeast-2:123456789012',
              };
              return config[key];
            }),
          },
        },
      ],
    }).compile();

    service = module.get<AwsEventBusService>(AwsEventBusService);
  });

  it('should publish event successfully', async () => {
    const event = {
      eventType: 'order.created',
      eventVersion: '1.0',
      aggregateId: 'order-123',
      occurredOn: new Date().toISOString(),
      data: { orderId: 'order-123', userId: 'user-456' },
    };

    const messageId = await service.publish(event);

    expect(messageId).toBeDefined();
  });
});
```

### 통합 테스트 (LocalStack)

```typescript
// test/integration/event-bus.integration.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { AwsEventBusService } from '../../src/events/aws-event-bus.service';
import { SqsEventConsumerService } from '../../src/events/sqs-event-consumer.service';

describe('Event Bus Integration', () => {
  let eventBus: AwsEventBusService;
  let consumer: SqsEventConsumerService;

  beforeAll(async () => {
    // LocalStack 환경 설정
    process.env.AWS_ENDPOINT = 'http://localhost:4566';
    process.env.AWS_REGION = 'us-east-1';

    const module: TestingModule = await Test.createTestingModule({
      providers: [AwsEventBusService, SqsEventConsumerService, ConfigService],
    }).compile();

    eventBus = module.get<AwsEventBusService>(AwsEventBusService);
    consumer = module.get<SqsEventConsumerService>(SqsEventConsumerService);
  });

  it('should publish and consume event', async () => {
    const event = {
      eventType: 'order.created',
      eventVersion: '1.0',
      aggregateId: 'order-123',
      occurredOn: new Date().toISOString(),
      data: { orderId: 'order-123', userId: 'user-456' },
    };

    // 이벤트 발행
    const messageId = await eventBus.publish(event);
    expect(messageId).toBeDefined();

    // 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 2000));

    // 이벤트 소비 확인 (실제로는 핸들러에서 확인)
  });
});
```

---

## 트러블슈팅

### 일반적인 문제

#### 문제 1: 이벤트가 발행되었지만 소비되지 않음

**원인:**
- SNS Topic과 SQS Queue 구독 설정 오류
- IAM 권한 부족

**해결:**
```bash
# SNS 구독 확인
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>

# SQS Queue 정책 확인
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names Policy
```

#### 문제 2: 이벤트 중복 처리

**원인:**
- 멱등성 키 미사용
- Standard Queue 사용 시 중복 가능

**해결:**
- FIFO Queue 사용
- DynamoDB 조건부 쓰기로 멱등성 보장

---

## 참고 자료

### NestJS 관련
- [NestJS Event Emitter](https://docs.nestjs.com/techniques/events)
- [NestJS Microservices](https://docs.nestjs.com/microservices/basics)

### AWS 관련
- [AWS SNS 개발자 가이드](https://docs.aws.amazon.com/ko_kr/sns/latest/dg/welcome.html)
- [AWS SQS 개발자 가이드](https://docs.aws.amazon.com/ko_kr/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [AWS Lambda 개발자 가이드](https://docs.aws.amazon.com/ko_kr/lambda/latest/dg/welcome.html)

### 도구
- [LocalStack](https://localstack.cloud/)
- [Serverless Framework](https://www.serverless.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

**문서 작성일:** 2025-01-16  
**최종 업데이트:** 2025-01-16




