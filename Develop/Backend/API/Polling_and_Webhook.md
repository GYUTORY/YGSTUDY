---
title: Polling과 Webhook
tags: [api, architecture, backend]
updated: 2026-05-06
---

# Polling과 Webhook

## Polling이란

클라이언트가 서버에 주기적으로 요청을 보내서 새로운 데이터가 있는지 확인하는 방식이다. 서버는 요청을 받을 때마다 현재 상태를 응답한다.

```
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "없음"
(3초 후)
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "없음"
(3초 후)
클라이언트 → 서버: "새 데이터 있어?"
서버 → 클라이언트: "있음, 여기"
```

구현이 단순하다는 게 가장 큰 장점이고, 대부분의 경우 첫 번째 선택지가 된다.

## Webhook이란

서버에서 이벤트가 발생하면 미리 등록된 URL로 HTTP 요청을 보내는 방식이다. 클라이언트가 물어보는 게 아니라 서버가 알려준다.

```
클라이언트 → 서버: "이 URL로 알려줘" (등록)
(이벤트 발생)
서버 → 클라이언트: POST /webhook {event: "payment_complete", data: {...}}
```

GitHub의 Push 이벤트 알림, Stripe의 결제 완료 알림, Slack의 메시지 이벤트가 대표적인 Webhook 사용 예다.

---

## Short Polling

가장 기본적인 Polling 방식이다. 일정 간격으로 요청을 보내고, 서버는 즉시 응답한다.

### NestJS 서버

```typescript
import { Controller, Get, Param, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order } from './order.entity';

interface OrderStatus {
  status: string;
  updatedAt: Date;
}

@Controller('api/orders')
export class OrderController {
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
  ) {}

  @Get(':orderId/status')
  async getOrderStatus(@Param('orderId') orderId: string): Promise<OrderStatus> {
    const order = await this.orderRepository.findOneBy({ id: Number(orderId) });
    if (!order) throw new NotFoundException(`Order ${orderId} not found`);

    return { status: order.status, updatedAt: order.updatedAt };
  }
}
```

### 클라이언트 (JavaScript)

```javascript
async function pollOrderStatus(orderId) {
    const INTERVAL = 3000; // 3초
    const MAX_ATTEMPTS = 60; // 최대 3분
    let attempts = 0;

    while (attempts < MAX_ATTEMPTS) {
        const response = await fetch(`/api/orders/${orderId}/status`);
        const data = await response.json();

        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            return data;
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, INTERVAL));
    }

    throw new Error('Polling timeout');
}
```

### Short Polling의 문제

3초 간격으로 100명이 동시에 주문 상태를 확인하면, 서버는 1분에 2,000번의 요청을 처리해야 한다. 대부분의 응답은 "변경 없음"이다. DB 커넥션도 매 요청마다 잡히고, 네트워크 비용도 계속 발생한다.

간격을 늘리면 서버 부하는 줄지만, 상태 변경을 감지하는 데 시간이 오래 걸린다. 이 트레이드오프에서 벗어나려면 Long Polling을 쓴다.

---

## Long Polling

서버가 새 데이터가 생길 때까지 응답을 보류하는 방식이다. 클라이언트는 요청을 보내고, 서버는 데이터가 준비될 때까지 커넥션을 열어둔다.

### NestJS 서버 (Observable + Subject 사용)

```typescript
import { Controller, Get, Param, Res } from '@nestjs/common';
import { Response } from 'express';
import { Subject, firstValueFrom } from 'rxjs';
import { timeout, catchError } from 'rxjs/operators';
import { of } from 'rxjs';

interface OrderStatus {
  status: string;
  updatedAt: Date;
}

@Controller('api/orders')
export class OrderLongPollingController {
  // orderId → 대기 중인 클라이언트 Subject 목록
  private readonly waitingClients = new Map<number, Subject<OrderStatus>[]>();

  @Get(':orderId/status/poll')
  async pollOrderStatus(
    @Param('orderId') orderId: string,
    @Res() res: Response,
  ): Promise<void> {
    const id = Number(orderId);
    const subject = new Subject<OrderStatus>();

    if (!this.waitingClients.has(id)) {
      this.waitingClients.set(id, []);
    }
    this.waitingClients.get(id)!.push(subject);

    try {
      // 25초 타임아웃 — 프록시 타임아웃보다 짧게
      const status = await firstValueFrom(
        subject.pipe(
          timeout(25_000),
          catchError(() => of(null)), // 타임아웃 시 null 반환
        ),
      );

      if (status === null) {
        // 타임아웃: 204 No Content
        res.status(204).send();
      } else {
        res.status(200).json(status);
      }
    } finally {
      // 목록에서 제거
      const clients = this.waitingClients.get(id) ?? [];
      const idx = clients.indexOf(subject);
      if (idx !== -1) clients.splice(idx, 1);
    }
  }

  // 주문 상태가 변경되면 대기 중인 클라이언트에게 알림
  notifyStatusChange(orderId: number, status: OrderStatus): void {
    const clients = this.waitingClients.get(orderId) ?? [];
    clients.forEach((subject) => subject.next(status));
    this.waitingClients.delete(orderId);
  }
}
```

### 클라이언트

```javascript
async function longPollOrderStatus(orderId) {
    while (true) {
        try {
            const response = await fetch(`/api/orders/${orderId}/status/poll`);

            if (response.status === 204) {
                // 타임아웃, 재연결
                continue;
            }

            const data = await response.json();
            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                return data;
            }
            // 중간 상태면 다시 연결
        } catch (error) {
            // 네트워크 에러 시 잠시 대기 후 재연결
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}
```

### Long Polling 사용 시 주의할 점

#### 스레드 점유 문제

NestJS/Node.js는 이벤트 루프 기반이라 커넥션을 열어두는 것 자체는 스레드를 점유하지 않는다. Promise/Observable로 비동기 처리가 기본이다. 다만 백프레셔를 어디서 처리할지는 따로 설계해야 한다.

#### LB·프록시 타임아웃과의 충돌

Long Polling을 운영하면서 가장 자주 만나는 문제다. 서버는 정상 동작하는데 클라이언트가 갑자기 504나 빈 응답을 받기 시작하면 거의 이 문제다.

서버 측 Long Polling 타임아웃은 경로상의 모든 중간 장비 idle timeout보다 짧아야 한다. 일반적인 기본값은 다음과 같다.

| 장비/서비스 | 기본 idle timeout | 비고 |
|---|---|---|
| AWS ALB | 60초 | `idle_timeout.timeout_seconds`로 변경 |
| AWS NLB | 350초 | TCP idle, 변경 불가 |
| Nginx `proxy_read_timeout` | 60초 | upstream 응답 대기 시간 |
| Cloudflare Free/Pro | 100초 | Enterprise는 6000초까지 |
| AWS API Gateway | 29초 | 변경 불가, Long Polling 부적합 |
| GCP HTTPS LB | 30초 | `backend_service.timeoutSec`로 변경 |
| Heroku Router | 30초 | 변경 불가 |

서버 타임아웃은 보통 `min(중간 장비 타임아웃) - 5초` 정도로 잡는다. 예를 들어 ALB 기본값 60초를 쓰면 서버는 25~30초로 잡는다. 5초 마진을 두는 이유는 응답 직렬화·flush·네트워크 전송에 시간이 걸리기 때문이다. 서버가 60초에 응답을 만들기 시작하면, 그 응답이 ALB를 통과하기 전에 ALB가 먼저 커넥션을 끊는다.

타임아웃이 어긋나면 증상이 까다롭게 나온다. 서버 로그에는 정상 응답한 것처럼 찍히는데 클라이언트는 504만 받는다. ALB 액세스 로그의 `target_status_code`는 200이고 `elb_status_code`가 504면 거의 확정이다.

API Gateway나 Heroku처럼 타임아웃 변경이 막혀 있는 환경에서는 Long Polling 자체를 포기하고 SSE나 WebSocket으로 가야 한다. 28초마다 끊기는 Long Polling은 사실상 Short Polling과 다를 게 없다.

#### Sticky Session과 이벤트 전파

Sticky Session이 없으면, 클라이언트가 재연결할 때 다른 서버로 갈 수 있다. 이벤트 발생 서버와 대기 중인 클라이언트가 연결된 서버가 다르면 알림이 전달되지 않는다. Redis Pub/Sub이나 Kafka로 서버 간 이벤트를 전파해야 한다.

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { OrderLongPollingController } from './order-long-polling.controller';

interface OrderEvent {
  orderId: number;
  status: string;
  updatedAt: string;
}

@Injectable()
export class OrderEventBridge implements OnModuleInit {
  private readonly subscriber: Redis;

  constructor(
    @InjectRedis() private readonly redis: Redis,
    private readonly controller: OrderLongPollingController,
  ) {
    this.subscriber = new Redis({ host: 'localhost', port: 6379 });
  }

  async onModuleInit(): Promise<void> {
    await this.subscriber.psubscribe('order.status.*');
    this.subscriber.on('pmessage', (_pattern, _channel, message) => {
      const event = JSON.parse(message) as OrderEvent;
      this.controller.notifyStatusChange(event.orderId, {
        status: event.status,
        updatedAt: new Date(event.updatedAt),
      });
    });
  }
}
```

---

## Webhook 발신 측 구현

### 재시도 정책 — Exponential Backoff with Jitter

발신 측에서 가장 신경 써야 하는 부분이다. 단순히 간격만 늘려가면서 재시도하면 안 된다. 같은 시각에 여러 발신자가 동시에 죽었다가 같이 살아나는 경우, 모두 같은 backoff 패턴으로 재시도하면 thundering herd가 생긴다.

상대 서버가 5분 동안 죽었다가 살아나는 순간, 그 5분 동안 발생한 모든 이벤트의 재시도가 같은 시각에 한꺼번에 몰린다. 살아난 서버가 그 폭주를 못 견디고 다시 죽는다.

해결책은 jitter다. 재시도 간격에 무작위성을 섞어서 요청을 시간축에 분산시킨다.

```typescript
import { Injectable } from '@nestjs/common';

@Injectable()
export class WebhookRetryScheduler {
  // exponential backoff base: 1분
  private static readonly BASE_DELAY_MS = 60_000;
  // 최대 재시도: 24시간
  private static readonly MAX_DELAY_MS = 24 * 60 * 60 * 1000;
  // 최대 재시도 횟수
  private static readonly MAX_ATTEMPTS = 10;

  /**
   * Full Jitter: AWS Architecture Blog에서 추천하는 방식
   * delay = random(0, min(MAX, BASE * 2^attempt))
   */
  nextDelay(attempt: number): number | null {
    if (attempt >= WebhookRetryScheduler.MAX_ATTEMPTS) {
      return null; // 더 이상 재시도하지 않음
    }

    const exponential = WebhookRetryScheduler.BASE_DELAY_MS * Math.pow(2, attempt);
    const capped = Math.min(exponential, WebhookRetryScheduler.MAX_DELAY_MS);
    const jittered = Math.random() * capped;

    // 최소 BASE_DELAY_MS는 보장 (너무 즉시 재시도 방지)
    return Math.max(jittered, WebhookRetryScheduler.BASE_DELAY_MS);
  }
}
```

`Full Jitter` 외에 `Equal Jitter`(절반은 고정, 절반은 랜덤), `Decorrelated Jitter`(이전 delay를 기반으로 다음 delay 결정) 같은 변형이 있다. AWS 벤치마크 기준으로는 Full Jitter가 가장 분산이 잘 된다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import * as crypto from 'crypto';
import { WebhookDelivery } from './webhook-delivery.entity';
import { WebhookRetryScheduler } from './webhook-retry-scheduler.service';

@Injectable()
export class WebhookSender {
  private readonly logger = new Logger(WebhookSender.name);

  constructor(
    private readonly httpService: HttpService,
    private readonly retryScheduler: WebhookRetryScheduler,
  ) {}

  async send(delivery: WebhookDelivery): Promise<void> {
    const signature = this.sign(delivery.payload, delivery.secret);

    try {
      const response = await firstValueFrom(
        this.httpService.post(delivery.url, delivery.payload, {
          headers: {
            'Content-Type': 'application/json',
            'X-Signature': signature,
            'X-Webhook-Id': delivery.deliveryId,
            'X-Webhook-Event': delivery.eventType,
            'X-Webhook-Timestamp': String(Math.floor(Date.now() / 1000)),
          },
          timeout: 10_000, // 10초 타임아웃
        }),
      );

      const status = response.status;

      if (status >= 200 && status < 300) {
        this.markSuccess(delivery);
      } else if (status >= 400 && status < 500 && status !== 408 && status !== 429) {
        // 4xx는 재시도해도 의미 없음 (클라이언트 에러). 408, 429는 예외.
        this.markPermanentFailure(delivery, status);
      } else {
        // 5xx, 408, 429는 재시도
        this.scheduleRetry(delivery);
      }
    } catch (err) {
      // 네트워크/타임아웃 에러는 재시도
      this.scheduleRetry(delivery);
    }
  }

  private scheduleRetry(delivery: WebhookDelivery): void {
    const nextAttempt = delivery.attempt + 1;
    const delayMs = this.retryScheduler.nextDelay(nextAttempt);

    if (delayMs === null) {
      this.moveToDeadLetterQueue(delivery);
      return;
    }

    delivery.nextRetryAt = new Date(Date.now() + delayMs);
    delivery.attempt = nextAttempt;
    // retryRepository.save(delivery);
  }

  private sign(payload: string, secret: string): string {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payload, 'utf8');
    return `sha256=${hmac.digest('hex')}`;
  }

  private markSuccess(_delivery: WebhookDelivery): void { /* ... */ }
  private markPermanentFailure(_delivery: WebhookDelivery, _status: number): void { /* ... */ }
  private moveToDeadLetterQueue(_delivery: WebhookDelivery): void { /* ... */ }
}
```

재시도 가능 여부는 응답 코드로 판단한다. 4xx 중에서 408(Request Timeout)과 429(Too Many Requests)는 재시도 대상, 나머지 4xx는 영구 실패로 취급한다. 401·403·404를 계속 재시도하는 건 양쪽 모두에게 부하만 준다.

요청 타임아웃은 짧게 잡는다. 보통 5~10초. Webhook 수신 측은 즉시 응답하고 비동기로 처리하는 게 표준이라, 응답이 느리다는 건 무언가 잘못됐다는 뜻이다.

### HMAC-SHA256 서명 생성

발신 측에서 페이로드에 서명을 붙인다. 수신 측이 위변조를 검증할 수 있게 해준다.

```typescript
import { Injectable } from '@nestjs/common';
import * as crypto from 'crypto';

@Injectable()
export class WebhookSignatureSigner {
  sign(payload: string, secret: string): string {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payload, 'utf8');
    return `sha256=${hmac.digest('hex')}`;
  }

  /**
   * 타임스탬프를 포함한 서명 — replay attack 방지
   * Stripe 방식: signed_payload = timestamp + "." + body
   */
  signWithTimestamp(payload: string, timestamp: number, secret: string): string {
    const signedPayload = `${timestamp}.${payload}`;
    return this.sign(signedPayload, secret);
  }
}
```

타임스탬프를 서명에 포함시키면 공격자가 옛날 요청을 그대로 캡처해서 재전송하는 replay attack을 막을 수 있다. 수신 측은 타임스탬프와 현재 시각의 차이가 일정 범위(예: 5분) 안에 있는지 확인한다.

### DLQ 운영

10번 재시도해도 실패하는 이벤트는 DLQ(Dead Letter Queue)로 보낸다. DLQ는 단순한 실패 보관소가 아니라 운영의 핵심이다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { DeadLetterEntry } from './dead-letter-entry.entity';
import { WebhookDelivery } from './webhook-delivery.entity';

@Injectable()
export class DeadLetterQueueService {
  private readonly logger = new Logger(DeadLetterQueueService.name);

  constructor(
    @InjectRepository(DeadLetterEntry)
    private readonly dlqRepository: Repository<DeadLetterEntry>,
  ) {}

  async enqueue(delivery: WebhookDelivery, reason: string): Promise<void> {
    const entry = this.dlqRepository.create({
      deliveryId: delivery.deliveryId,
      url: delivery.url,
      payload: delivery.payload,
      eventType: delivery.eventType,
      lastStatusCode: delivery.lastStatusCode,
      lastError: delivery.lastError,
      totalAttempts: delivery.attempt,
      firstFailedAt: delivery.firstFailedAt,
      deadAt: new Date(),
      reason,
    });

    await this.dlqRepository.save(entry);

    // 같은 endpoint에서 임계치 이상 누적되면 알림
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    const recentFailures = await this.dlqRepository.count({
      where: { url: delivery.url },
      // deadAt > oneHourAgo 조건은 QueryBuilder로 처리
    });

    if (recentFailures > 10) {
      this.logger.error(`Endpoint 장애 감지: url=${delivery.url}, failures=${recentFailures}`);
      // notificationService.alertEndpointDown(delivery.url, recentFailures);
    }
  }
}
```

DLQ를 운영할 때 필요한 것들이 있다.

**1. 페이로드 원본 보존**: 재처리할 수 있도록 페이로드, 헤더, 타임스탬프를 그대로 저장한다. 압축해서 S3나 별도 스토리지에 두는 것도 방법이다. DB에 그대로 쌓으면 금방 비대해진다.

**2. 실패 사유 분류**: 5xx 누적, timeout 누적, DNS 실패, SSL 인증서 오류 같은 카테고리로 나눠서 저장한다. 분류가 안 되어 있으면 운영자가 매번 페이로드를 까봐야 한다.

**3. Endpoint별 상태 모니터링**: 특정 endpoint로 가는 webhook이 한 시간 안에 N개 이상 DLQ로 빠지면 알림을 보낸다. 보통 그 endpoint의 서버가 죽었거나 인증서가 만료된 경우다.

**4. 재처리 API**: 운영자가 DLQ에 쌓인 이벤트를 다시 큐에 넣을 수 있어야 한다. 한 건씩 또는 endpoint 단위로 일괄 재처리.

```typescript
import { Controller, Post, Param, Body } from '@nestjs/common';

interface ReplayRequest {
  url?: string;
  eventType?: string;
  since?: string;
}

interface ReplayResult {
  replayed: number;
  total: number;
}

@Controller('admin/dlq')
export class DlqAdminController {
  constructor(
    private readonly dlqService: DeadLetterQueueService,
    private readonly webhookSender: WebhookSender,
  ) {}

  @Post(':entryId/replay')
  async replayEntry(@Param('entryId') entryId: string): Promise<void> {
    const entry = await this.dlqService.findById(Number(entryId));
    const delivery = WebhookDelivery.fromDlqEntry(entry);
    delivery.resetAttempts();
    await this.webhookSender.send(delivery);
    await this.dlqService.markReplayed(Number(entryId), new Date());
  }

  @Post('replay')
  async replayBatch(@Body() request: ReplayRequest): Promise<ReplayResult> {
    const entries = await this.dlqService.findReplayable(
      request.url,
      request.eventType,
      request.since ? new Date(request.since) : undefined,
    );

    let replayed = 0;
    for (const entry of entries) {
      try {
        const delivery = WebhookDelivery.fromDlqEntry(entry);
        delivery.resetAttempts();
        await this.webhookSender.send(delivery);
        await this.dlqService.markReplayed(entry.id, new Date());
        replayed++;
      } catch (err) {
        this.logger.error(`재처리 실패: entryId=${entry.id}`, err);
      }
    }

    return { replayed, total: entries.length };
  }
}
```

**5. 보존 기간**: 영원히 쌓아두지 않는다. 보통 30~90일 보관 후 아카이브 또는 삭제. 너무 오래된 이벤트는 재처리해봐야 의미 없다.

**6. 수동 폐기 기록**: 일부 이벤트는 재처리하면 안 된다(예: 24시간 지난 결제 알림은 이미 만료된 세션을 가리킬 수 있다). 폐기 사유와 폐기자를 기록한다.

---

## Webhook 수신 서버 구현

### 기본 구조 (NestJS)

```typescript
import {
  Controller, Post, Headers, Body, HttpCode,
  UnauthorizedException,
} from '@nestjs/common';
import { WebhookEventProcessor } from './webhook-event-processor.service';
import { WebhookSignatureVerifier } from './webhook-signature-verifier.service';

@Controller('webhooks')
export class WebhookController {
  constructor(
    private readonly eventProcessor: WebhookEventProcessor,
    private readonly verifier: WebhookSignatureVerifier,
  ) {}

  @Post('payment')
  @HttpCode(200)
  async handlePaymentWebhook(
    @Headers('x-signature') signature: string,
    @Headers('x-webhook-timestamp') timestamp: string,
    @Headers('x-webhook-id') deliveryId: string,
    @Body() rawBody: string, // raw body를 받으려면 별도 설정 필요
  ): Promise<void> {
    // 1. 타임스탬프 윈도우 검증 (replay attack 방지)
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - Number(timestamp)) > 300) { // 5분
      throw new UnauthorizedException('Timestamp out of window');
    }

    // 2. 서명 검증
    if (!this.verifier.verifyWithTimestamp(rawBody, Number(timestamp), signature)) {
      throw new UnauthorizedException('Invalid signature');
    }

    // 3. 멱등 큐에 적재 (즉시 응답)
    void this.eventProcessor.enqueue(deliveryId, rawBody);

    // 4. 빠르게 200 반환 (void이므로 자동 응답)
  }
}
```

수신 서버에서 가장 중요한 건 빠르게 200을 반환하는 것이다. 발신자는 응답이 5~10초 안에 안 오면 타임아웃 처리하고 재시도한다. 실제 비즈니스 로직은 비동기로 처리한다.

### HMAC-SHA256 서명 검증

`X-Signature` 헤더에 들어 있는 서명을 검증한다. 발신 측과 동일한 비밀키·동일한 알고리즘을 사용한다.

```typescript
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as crypto from 'crypto';

@Injectable()
export class WebhookSignatureVerifier {
  private readonly webhookSecret: string;

  constructor(private readonly configService: ConfigService) {
    this.webhookSecret = this.configService.get<string>('WEBHOOK_SECRET', '');
  }

  verifyWithTimestamp(payload: string, timestamp: number, receivedSignature: string): boolean {
    const signedPayload = `${timestamp}.${payload}`;
    return this.verify(signedPayload, receivedSignature);
  }

  verify(payload: string, receivedSignature: string): boolean {
    try {
      const hmac = crypto.createHmac('sha256', this.webhookSecret);
      hmac.update(payload, 'utf8');
      const computed = `sha256=${hmac.digest('hex')}`;

      // 타이밍 공격 방지: crypto.timingSafeEqual은 상수 시간 비교
      return crypto.timingSafeEqual(
        Buffer.from(computed, 'utf8'),
        Buffer.from(receivedSignature, 'utf8'),
      );
    } catch {
      return false;
    }
  }

  // 비밀키 로테이션: 현재 키와 이전 키를 둘 다 시도
  verifyWithRotation(payload: string, signature: string, previousSecret: string): boolean {
    return (
      this.verify(payload, signature) ||
      this.verifyWithSecret(payload, signature, previousSecret)
    );
  }

  private verifyWithSecret(payload: string, receivedSignature: string, secret: string): boolean {
    try {
      const hmac = crypto.createHmac('sha256', secret);
      hmac.update(payload, 'utf8');
      const computed = `sha256=${hmac.digest('hex')}`;
      return crypto.timingSafeEqual(
        Buffer.from(computed, 'utf8'),
        Buffer.from(receivedSignature, 'utf8'),
      );
    } catch {
      return false;
    }
  }
}
```

검증 단계에서 자주 실수하는 것들이 있다.

**raw body를 그대로 받아야 한다.** NestJS에서 JSON을 파싱하면 키 순서, 공백이 달라져서 서명이 안 맞는다. raw body 미들웨어를 설정해야 한다.

**상수 시간 비교를 써야 한다.** `===`는 첫 다른 바이트를 만나면 즉시 false를 반환한다. 응답 시간 차이로 서명을 한 글자씩 맞춰가는 타이밍 공격이 가능하다. `crypto.timingSafeEqual()`은 길이가 같으면 모든 바이트를 비교하기 때문에 시간이 일정하다.

**서명 헤더 형식을 명확히 정의한다.** `sha256=abc123...` 형식으로 알고리즘 prefix를 붙이면 나중에 알고리즘을 바꿀 때 호환을 유지할 수 있다. 알고리즘이 둘 이상이면 `t=timestamp,v1=hash1,v0=hash0` 같이 콤마로 구분하는 형식을 쓴다(Stripe 방식).

### 멱등키 처리

발신 측이 재시도하기 때문에, 같은 이벤트를 여러 번 받는 건 정상 상황이다. 같은 이벤트를 두 번 처리하면 결제가 두 번 되거나 이메일이 두 번 발송되는 사고가 난다.

멱등키는 발신 측이 보내는 unique ID(`X-Webhook-Id` 또는 페이로드의 `event_id`)를 사용한다. 받은 키를 DB에 기록하고, 이미 있으면 처리를 건너뛴다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { ProcessedEvent, ProcessingStatus } from './processed-event.entity';

@Injectable()
export class WebhookEventProcessor {
  private readonly logger = new Logger(WebhookEventProcessor.name);

  constructor(
    @InjectRepository(ProcessedEvent)
    private readonly processedRepo: Repository<ProcessedEvent>,
    private readonly dataSource: DataSource,
  ) {}

  async process(deliveryId: string, payload: string): Promise<void> {
    const event = JSON.parse(payload) as { eventId: string };
    const idempotencyKey = event.eventId ?? deliveryId;

    try {
      await this.dataSource.transaction(async (manager) => {
        // 1. 멱등 레코드 먼저 INSERT (유니크 제약으로 중복 차단)
        const record = manager.create(ProcessedEvent, {
          eventId: idempotencyKey,
          processedAt: new Date(),
          status: ProcessingStatus.IN_PROGRESS,
        });
        await manager.save(record);

        // 2. 비즈니스 로직 실행
        await this.executeBusinessLogic(event);

        // 3. 완료 상태로 업데이트
        await manager.update(ProcessedEvent, { eventId: idempotencyKey }, {
          status: ProcessingStatus.COMPLETED,
          completedAt: new Date(),
        });
      });
    } catch (err: unknown) {
      // 유니크 제약 위반 — 이미 처리되었거나 처리 중
      if (this.isDuplicateKeyError(err)) {
        await this.handleDuplicate(idempotencyKey);
        return;
      }
      throw err;
    }
  }

  async enqueue(deliveryId: string, payload: string): Promise<void> {
    // 비동기 처리를 위한 큐 적재 (실제 구현에서는 Bull 등 사용)
    void this.process(deliveryId, payload);
  }

  private async handleDuplicate(key: string): Promise<void> {
    const existing = await this.processedRepo.findOneBy({ eventId: key });
    if (!existing) return;

    if (existing.status === ProcessingStatus.IN_PROGRESS) {
      const staleThreshold = new Date(Date.now() - 10 * 60 * 1000); // 10분
      if (existing.processedAt < staleThreshold) {
        await this.processedRepo.delete({ eventId: key });
        throw new Error('stale lock 정리, 재시도 필요');
      }
    }
    // COMPLETED면 그냥 무시
    this.logger.log(`중복 이벤트 무시: eventId=${key}, status=${existing.status}`);
  }

  private isDuplicateKeyError(err: unknown): boolean {
    // TypeORM QueryFailedError with unique constraint violation
    return (err as { code?: string })?.code === '23505' // PostgreSQL
      || (err as { code?: string })?.code === 'ER_DUP_ENTRY'; // MySQL
  }

  private async executeBusinessLogic(_event: unknown): Promise<void> { /* ... */ }
}
```

`processed_events` 테이블에 `event_id` 유니크 인덱스를 거는 게 핵심이다. 애플리케이션 레벨에서 `existsBy → save`로 체크하면 동시에 같은 이벤트가 들어왔을 때 둘 다 통과한다. DB 제약으로 막아야 한다.

```sql
CREATE TABLE processed_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(128) NOT NULL,
    processed_at TIMESTAMP NOT NULL,
    status VARCHAR(32) NOT NULL,
    completed_at TIMESTAMP,
    UNIQUE (event_id)
);

CREATE INDEX idx_processed_at ON processed_events(processed_at);
```

멱등 테이블은 무한정 쌓이면 안 된다. 발신자의 최대 재시도 기간(보통 24시간~7일)보다 길게 보존한 후 삭제한다. Webhook 발신자가 30일 후에 같은 event_id로 재시도하지는 않는다.

```sql
DELETE FROM processed_events WHERE processed_at < NOW() - INTERVAL '30 days';
```

Redis로 멱등 체크를 하는 경우는 더 간단하지만 영속성에 주의해야 한다. Redis가 죽었다 살아나면 데이터가 날아갈 수 있고, 그 시점에 들어온 webhook은 중복 처리될 수 있다. 결제 같은 critical한 영역은 DB로, 알림 같은 영역은 Redis로 나누는 식으로 쓴다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class RedisIdempotencyGuard {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async tryClaim(key: string, ttlSeconds: number): Promise<boolean> {
    const result = await this.redis.set(
      `webhook:idem:${key}`,
      '1',
      'NX',
      'EX',
      ttlSeconds,
    );
    return result === 'OK';
  }
}
```

---

## Webhook 등록 endpoint 검증 (Echo Challenge)

새 Webhook URL을 등록할 때, 그 URL이 실제로 우리가 통제할 수 있는 곳인지 확인해야 한다. 검증 없이 등록을 받으면 누군가 임의의 URL을 등록해서 우리 시스템을 트래픽 발사대로 사용할 수 있다(reflection attack). 또 단순 오타로 잘못된 URL이 등록되어도 운영 사고가 난다.

검증은 challenge-response 패턴을 쓴다. 등록 요청을 받으면, 등록하려는 URL로 무작위 문자열을 보내고 그대로 echo해서 돌려주는지 확인한다.

### Slack 방식 (URL Verification)

Slack의 Events API가 쓰는 방식이다. 등록 시점에 한 번 호출한다.

```typescript
import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import * as crypto from 'crypto';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { WebhookSubscription } from './webhook-subscription.entity';

interface RegisterRequest {
  url: string;
}

@Controller('api/webhooks/subscriptions')
export class WebhookSubscriptionController {
  constructor(
    private readonly httpService: HttpService,
    @InjectRepository(WebhookSubscription)
    private readonly subscriptionRepository: Repository<WebhookSubscription>,
  ) {}

  @Post()
  async register(@Body() request: RegisterRequest): Promise<void> {
    const { url } = request;

    // 1. URL 형식과 도메인 검증
    if (!this.isValidWebhookUrl(url)) {
      throw new BadRequestException('invalid url');
    }

    // 2. challenge 발송
    const challenge = this.generateChallenge();

    try {
      const response = await firstValueFrom(
        this.httpService.post<{ challenge: string }>(
          url,
          { type: 'url_verification', challenge },
          {
            headers: { 'X-Webhook-Verification': 'challenge' },
            timeout: 5_000, // 5초 타임아웃
          },
        ),
      );

      // 3. challenge 값이 그대로 echo되는지 확인
      if (response.data.challenge !== challenge) {
        throw new BadRequestException('challenge mismatch');
      }

      // 4. 검증 성공 — 구독 저장
      const subscription = this.subscriptionRepository.create({
        url,
        secret: this.generateSecret(),
        verifiedAt: new Date(),
      });
      await this.subscriptionRepository.save(subscription);
    } catch (err) {
      if (err instanceof BadRequestException) throw err;
      throw new BadRequestException(`verification failed: ${(err as Error).message}`);
    }
  }

  private generateChallenge(): string {
    return crypto.randomBytes(32).toString('base64url');
  }

  private generateSecret(): string {
    return crypto.randomBytes(32).toString('hex');
  }

  private isValidWebhookUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== 'https:') return false; // HTTPS만 허용

      const hostname = parsed.hostname;
      // 내부 IP 차단 (SSRF 방지)
      const privateRanges = [
        /^127\./,
        /^10\./,
        /^172\.(1[6-9]|2\d|3[01])\./,
        /^192\.168\./,
        /^169\.254\./,
        /^::1$/,
        /^fc00:/,
        /^fe80:/,
      ];
      return !privateRanges.some((re) => re.test(hostname));
    } catch {
      return false;
    }
  }
}
```

수신 측 구현:

```typescript
import { Controller, Post, Body, HttpCode } from '@nestjs/common';

interface WebhookBody {
  type?: string;
  challenge?: string;
  [key: string]: unknown;
}

@Controller('webhooks/payment')
export class PaymentWebhookController {
  @Post()
  @HttpCode(200)
  async handle(@Body() body: WebhookBody): Promise<Record<string, unknown> | void> {
    // URL 검증 요청이면 challenge를 그대로 돌려준다
    if (body.type === 'url_verification') {
      return { challenge: body.challenge };
    }

    // 일반 이벤트 처리
    return this.processEvent(body);
  }

  private processEvent(_body: WebhookBody): void { /* ... */ }
}
```

### Meta/Facebook 방식 (GET hub.challenge)

Meta Webhook은 GET 요청으로 challenge를 보낸다. 수신 측은 `hub.challenge` 쿼리 파라미터를 plain text로 그대로 응답한다.

```typescript
import { Controller, Get, Query, ForbiddenException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Controller('webhooks/payment')
export class PaymentWebhookController {
  private readonly verifyToken: string;

  constructor(private readonly configService: ConfigService) {
    this.verifyToken = this.configService.get<string>('WEBHOOK_VERIFY_TOKEN', '');
  }

  @Get()
  verify(
    @Query('hub.mode') mode: string,
    @Query('hub.verify_token') verifyToken: string,
    @Query('hub.challenge') challenge: string,
  ): string {
    if (mode === 'subscribe' && verifyToken === this.verifyToken) {
      return challenge;
    }
    throw new ForbiddenException();
  }
}
```

GET 방식은 브라우저 등에서 우연히 호출돼도 부수효과가 없다는 게 장점이다. POST는 멱등성을 따로 신경 써야 한다.

### URL 검증 시 보안 고려사항

검증 자체보다 검증 단계의 SSRF가 더 큰 문제다. 임의의 URL로 HTTP 요청을 보내는 코드가 외부에서 호출 가능한 상태로 노출되는 셈이다.

내부 IP로 가는 요청을 차단해야 한다. `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`(AWS 메타데이터 endpoint) 같은 주소가 들어오면 거부한다.

DNS resolution도 한 번만 하고 끝나면 안 된다. 처음 검증할 때 외부 IP로 응답하다가, 실제 webhook 발송 시점에 내부 IP로 응답이 바뀌는 DNS rebinding 공격이 가능하다. 검증한 IP를 저장해두고 실제 발송 시 다시 확인하거나, HTTP 클라이언트 레벨에서 매번 IP를 검증하는 식으로 방어한다.

검증 요청에도 짧은 타임아웃(5초 정도)을 걸어둔다. 등록 API가 외부 서버 응답을 기다리며 막히면 안 된다.

---

## Polling에서 Webhook으로 전환

### 전환 기간에는 둘 다 운영해야 한다

Webhook을 붙였다고 바로 Polling을 끄면 안 된다. Webhook이 실패하거나 누락될 수 있으니, 전환 기간에는 Polling을 fallback으로 유지한다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { WebhookSubscription } from './webhook-subscription.entity';

@Injectable()
export class OrderStatusService {
  constructor(
    @InjectRepository(WebhookSubscription)
    private readonly webhookSubscriptionRepository: Repository<WebhookSubscription>,
  ) {}

  async checkOrderStatus(orderId: number): Promise<void> {
    const subscription = await this.webhookSubscriptionRepository.findOneBy({
      orderId,
      active: true,
    });

    if (subscription) {
      // Webhook이 정상 동작 중이면 대기
      // 일정 시간 내에 Webhook이 안 오면 Polling fallback
      this.schedulePollingFallback(orderId, 5 * 60 * 1000); // 5분 후 폴백
    } else {
      // Webhook이 없으면 기존 Polling 방식
      await this.pollOrderStatus(orderId);
    }
  }

  private schedulePollingFallback(orderId: number, delayMs: number): void {
    setTimeout(() => void this.pollOrderStatus(orderId), delayMs);
  }

  private async pollOrderStatus(_orderId: number): Promise<void> { /* ... */ }
}
```

### Webhook 수신 서버의 가용성

Polling은 내가 능동적으로 가져오는 거라 내 서버만 살아있으면 된다. Webhook은 수신 서버가 죽어있으면 이벤트를 놓친다. Webhook 수신 서버가 죽었을 때를 대비한 복구 방법이 있어야 한다.

- 발신자가 재시도를 지원하는지 확인
- 재시도 횟수가 소진된 후의 이벤트를 어떻게 복구할지 (수동 재전송 API, 이벤트 목록 조회 API 등)
- 발신자의 대시보드에서 실패한 Webhook을 재전송할 수 있는지

### 방화벽과 네트워크

Polling은 아웃바운드 요청이라 대부분 방화벽에 걸리지 않는다. Webhook은 인바운드 요청을 받아야 하니까, 수신 서버가 외부에서 접근 가능해야 한다. 내부망에 있는 서버라면 별도의 프록시를 두거나 VPN 터널을 설정해야 한다.

### 순서 보장

Webhook은 이벤트 발생 순서대로 도착한다는 보장이 없다. 네트워크 상황이나 재시도 일정에 따라 먼저 보낸 요청이 나중에 도착할 수 있다. 순서가 중요한 경우에는 이벤트에 타임스탬프나 시퀀스 번호를 포함하고, 수신 측에서 순서를 맞춰야 한다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order } from './order.entity';
import { DataSource } from 'typeorm';

interface WebhookEvent {
  orderId: number;
  status: string;
  timestamp: string; // ISO 8601
}

@Injectable()
export class OrderEventProcessor {
  private readonly logger = new Logger(OrderEventProcessor.name);

  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
    private readonly dataSource: DataSource,
  ) {}

  async processOrderEvent(event: WebhookEvent): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
      const order = await manager.findOneBy(Order, { id: event.orderId });
      if (!order) return;

      const eventTime = new Date(event.timestamp);

      // 이전 이벤트보다 오래된 이벤트면 무시
      if (order.lastEventTimestamp && eventTime < order.lastEventTimestamp) {
        this.logger.warn(
          `순서가 맞지 않는 이벤트 무시: orderId=${event.orderId}, eventTime=${eventTime.toISOString()}, lastTime=${order.lastEventTimestamp.toISOString()}`,
        );
        return;
      }

      order.status = event.status;
      order.lastEventTimestamp = eventTime;
      await manager.save(order);
    });
  }
}
```

상태 머신을 정의해두는 것도 방법이다. `PENDING → PAID → SHIPPED → DELIVERED` 순서가 정해져 있다면, 역방향 전이는 무조건 무시한다. 타임스탬프만으로는 시계 어긋남 문제가 있어서, 도메인 규칙을 같이 쓰는 게 안전하다.

---

## 선택 기준

### Polling이 맞는 경우

- 이벤트 빈도가 높고 거의 매번 데이터가 있는 경우 (예: 주식 시세 — 어차피 매 요청마다 새 데이터가 있다)
- 수신 서버를 외부에 노출할 수 없는 환경
- 상대 시스템이 Webhook을 지원하지 않는 경우
- 구현 복잡도를 낮추고 싶은 경우 (초기 프로토타입, MVP)

### Webhook이 맞는 경우

- 이벤트가 드물게 발생하는 경우 (예: 결제 완료 — 하루에 몇 건 안 되는데 매초 Polling하면 낭비다)
- 실시간에 가까운 반응이 필요한 경우
- 서버 리소스를 아껴야 하는 경우

### 둘 다 쓰는 경우

실무에서는 Webhook을 기본으로 쓰되, Polling을 보조 수단으로 두는 패턴이 많다. Webhook이 누락됐을 때 Polling으로 상태를 맞추는 방식이다. Stripe, GitHub 같은 대형 서비스가 Webhook과 함께 이벤트 목록 조회 API를 제공하는 이유가 이것이다.

```typescript
import { Injectable } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ProcessedEvent } from './processed-event.entity';

@Injectable()
export class PaymentReconciliationService {
  private lastCheckedTime: Date = new Date();

  constructor(
    @InjectRepository(ProcessedEvent)
    private readonly eventRepository: Repository<ProcessedEvent>,
    private readonly eventProcessor: WebhookEventProcessor,
  ) {}

  // Webhook으로 실시간 이벤트 수신은 WebhookController에서 처리

  // 5분마다 누락된 이벤트가 없는지 Polling으로 확인
  @Cron('*/5 * * * *')
  async reconcilePaymentEvents(): Promise<void> {
    const since = this.lastCheckedTime;
    const now = new Date();

    // paymentApi.getEvents(since, now)로 이벤트 목록 조회
    // const events = await this.paymentApi.getEvents(since, now);

    // for (const event of events) {
    //   const exists = await this.eventRepository.existsBy({ eventId: event.id });
    //   if (!exists) {
    //     console.warn(`Webhook 누락된 이벤트 발견: ${event.id}`);
    //     await this.eventProcessor.process(event.id, JSON.stringify(event));
    //   }
    // }

    this.lastCheckedTime = now;
  }
}
```

이 조합이 가장 안정적이다. Webhook으로 실시간성을 확보하고, Polling으로 데이터 정합성을 맞춘다.
