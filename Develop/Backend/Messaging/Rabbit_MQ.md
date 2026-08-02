---
title: RabbitMQ 심화
tags: [rabbitmq, AMQP, messaging, NestJS AMQP, Quorum Queue]
updated: 2026-04-02
---

# RabbitMQ 심화

RabbitMQ는 AMQP 0-9-1 프로토콜 기반의 메시지 브로커다. Kafka와 달리 메시지를 Consumer가 처리하면 큐에서 제거하는 전통적인 메시지 큐 모델이다. 이 문서는 RabbitMQ를 운영 수준에서 다루기 위해 필요한 내용을 정리한다.

---

## Publisher Confirms

메시지를 publish한 뒤 브로커가 실제로 받았는지 확인하는 메커니즘이다. 기본 설정에서는 `publish()`가 완료되더라도 브로커에 메시지가 도착했다는 보장이 없다.

### Confirm 모드 활성화

```typescript
import * as amqplib from 'amqplib';

const connection = await amqplib.connect('amqp://localhost');
const channel = await connection.createConfirmChannel(); // confirm 채널 생성
```

`createConfirmChannel()`을 사용하면 해당 Channel에서 발행하는 모든 메시지에 대해 브로커가 ack/nack을 보낸다.

### 3가지 확인 방식

**개별 확인 (동기 - Promise)**

```typescript
import * as amqplib from 'amqplib';

async function publishWithConfirm(channel: amqplib.ConfirmChannel, body: Buffer): Promise<void> {
  return new Promise((resolve, reject) => {
    channel.publish('exchange', 'routing.key', body, {}, (err) => {
      if (err) {
        // 재발행 또는 로깅
        reject(err);
      } else {
        resolve();
      }
    });
  });
}
```

메시지 하나마다 await로 대기한다. 처리량이 떨어지기 때문에 배치 처리에는 부적합하다.

**배치 확인 (waitForConfirms)**

```typescript
import * as amqplib from 'amqplib';

async function publishBatch(
  channel: amqplib.ConfirmChannel,
  messages: Buffer[],
  batchSize = 100,
): Promise<void> {
  let count = 0;

  for (const msg of messages) {
    channel.publish('exchange', 'routing.key', msg);
    count++;
    if (count >= batchSize) {
      // 배치 내 모든 메시지 confirm 대기 (하나라도 nack이면 throw)
      await channel.waitForConfirms();
      count = 0;
    }
  }
  // 나머지 flush
  if (count > 0) {
    await channel.waitForConfirms();
  }
}
```

배치 중 하나라도 실패하면 어떤 메시지가 실패했는지 알 수 없다. 전체를 재발행해야 하는 문제가 있다.

**비동기 확인 (권장)**

```typescript
import * as amqplib from 'amqplib';

interface PendingMessage {
  body: Buffer;
  seqNo: number;
}

async function publishAsync(
  channel: amqplib.ConfirmChannel,
  messages: Buffer[],
): Promise<void> {
  const outstanding = new Map<number, Buffer>();

  // ack 콜백: 처리 성공
  channel.on('ack', (seqNo: number, multiple: boolean) => {
    if (multiple) {
      // seqNo 이하 모든 메시지 제거
      for (const [key] of outstanding) {
        if (key <= seqNo) outstanding.delete(key);
      }
    } else {
      outstanding.delete(seqNo);
    }
  });

  // nack 콜백: 처리 실패 → 재발행
  channel.on('nack', (seqNo: number, multiple: boolean) => {
    const toRepublish: Buffer[] = [];
    if (multiple) {
      for (const [key, body] of outstanding) {
        if (key <= seqNo) {
          toRepublish.push(body);
          outstanding.delete(key);
        }
      }
    } else {
      const body = outstanding.get(seqNo);
      if (body) {
        toRepublish.push(body);
        outstanding.delete(seqNo);
      }
    }
    // 재발행
    for (const body of toRepublish) {
      channel.publish('exchange', 'routing.key', body);
    }
  });

  for (const msg of messages) {
    const seq = (channel as unknown as { _deliveryTagCounter: number })
      ._deliveryTagCounter + 1;
    outstanding.set(seq, msg);
    channel.publish('exchange', 'routing.key', msg);
  }
}
```

`deliveryTag`는 Channel 단위로 1부터 순차 증가한다. `multiple=true`면 해당 태그 이하 모든 메시지를 의미한다.

### Mandatory 플래그

```typescript
import * as amqplib from 'amqplib';

async function setupMandatoryPublish(
  channel: amqplib.ConfirmChannel,
  body: Buffer,
): Promise<void> {
  // mandatory=true: 라우팅 불가 메시지를 publisher에게 반환
  channel.publish('exchange', 'routing.key', body, { mandatory: true });

  // 라우팅 불가 메시지 처리
  channel.on('return', (msg: amqplib.Message) => {
    console.error('Unroutable message returned:', msg.fields.replyText);
    // 라우팅 불가 메시지 처리 로직
  });
}
```

`mandatory: true`로 설정하면, exchange에서 어떤 큐로도 라우팅되지 않는 메시지를 publisher에게 돌려보낸다. 설정하지 않으면 메시지가 조용히 사라진다. 운영에서 꽤 자주 겪는 문제가 exchange-queue 바인딩을 빠뜨리고 메시지가 유실되는 건데, mandatory와 return 이벤트를 같이 설정해두면 잡을 수 있다.

---

## Consumer Acknowledgement

Consumer가 메시지를 받은 뒤 처리 결과를 브로커에 알리는 메커니즘이다. `noAck: true`를 쓰면 브로커가 메시지를 보내는 순간 처리 완료로 간주한다. 처리 중 Consumer가 죽으면 메시지가 유실된다.

### Manual Ack

```typescript
import * as amqplib from 'amqplib';

async function startConsumer(channel: amqplib.Channel): Promise<void> {
  // noAck: false → manual ack 모드
  await channel.consume('queue', async (msg) => {
    if (!msg) return;

    try {
      await process(msg.content);
      channel.ack(msg); // 처리 완료
    } catch (err) {
      // 처리 실패: requeue=true로 큐에 재입력
      channel.nack(msg, false, true);
    }
  }, { noAck: false });
}
```

`noAck: false`를 넘겨야 manual ack가 동작한다.

### ack, nack, reject 차이

| 메서드 | 파라미터 | 동작 |
|--------|----------|------|
| `ack(msg, allUpTo?)` | allUpTo: 해당 태그 이하 전체 ack | 정상 처리 완료, 큐에서 제거 |
| `nack(msg, allUpTo?, requeue?)` | requeue=true: 큐 앞쪽에 재입력 | 처리 실패, 여러 메시지 한번에 거부 가능 |
| `reject(msg, requeue?)` | requeue=true: 큐 앞쪽에 재입력 | 처리 실패, 메시지 1개만 거부 |

`nack`는 RabbitMQ 확장이고, `reject`은 AMQP 표준이다. 차이는 `nack`만 `allUpTo` 파라미터를 지원한다는 점이다.

### requeue의 함정

`requeue: true`로 nack/reject하면 메시지가 큐 앞쪽에 다시 들어간다. 처리 로직에 버그가 있으면 같은 메시지가 무한 반복된다.

```
Consumer 받음 → 처리 실패 → nack(requeue=true) → 큐에 재입력 → 다시 받음 → 또 실패 → ...
```

이걸 방지하려면:

1. 재시도 횟수를 메시지 헤더(x-death)로 추적하고 임계값 초과 시 DLQ로 보낸다
2. amqplib 레벨에서 재시도 카운터를 관리한다 (아래 참조)
3. `requeue: false`로 설정하고 DLQ에서 별도 처리한다

### Prefetch Count

```typescript
// Consumer가 한 번에 받을 수 있는 미확인 메시지 수
await channel.prefetch(10);
```

기본값은 0(무제한)인데, 이러면 RabbitMQ가 큐에 있는 메시지를 한꺼번에 Consumer로 밀어넣는다. Consumer가 느리면 메모리가 터진다. 운영에서는 반드시 설정해야 한다.

적정값은 처리 시간에 따라 다른데, 네트워크 RTT와 메시지 처리 시간을 고려해서 Consumer가 유휴 상태가 되지 않을 정도로 설정한다. 보통 10~50 사이에서 시작해서 조정한다.

---

## Connection과 Channel 관리

### 구조

```
Application
  └─ Connection (TCP 소켓 1개, heartbeat 관리)
       ├─ Channel 1 (Publisher용)
       ├─ Channel 2 (Consumer용)
       └─ Channel 3 (Consumer용)
```

Connection은 TCP 소켓이다. 비용이 크기 때문에 하나의 Connection 위에 여러 Channel을 멀티플렉싱한다. Channel이 실제 AMQP 명령을 주고받는 논리적 단위다.

### 주의사항

**Channel은 동시 사용에 안전하지 않다.** 여러 코루틴/Promise에서 하나의 Channel을 동시에 사용하면 프레임이 섞여서 프로토콜 에러가 발생한다. 작업마다 Channel을 분리하거나, Channel Pool을 사용해야 한다.

**Publisher와 Consumer의 Connection을 분리해야 하는 경우가 있다.** TCP backpressure가 걸리면 하나의 Connection에서 publish와 consume이 서로 영향을 준다. 처리량이 높은 시스템에서는 Publisher Connection과 Consumer Connection을 별도로 둔다.

### NestJS에서 Connection/Channel 관리

```typescript
import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import * as amqplib from 'amqplib';

@Injectable()
export class RabbitMQService implements OnModuleInit, OnModuleDestroy {
  private connection: amqplib.Connection | null = null;
  private publisherChannel: amqplib.ConfirmChannel | null = null;
  private consumerChannel: amqplib.Channel | null = null;

  async onModuleInit(): Promise<void> {
    this.connection = await amqplib.connect('amqp://guest:guest@localhost');

    // Publisher용 Channel
    this.publisherChannel = await this.connection.createConfirmChannel();

    // Consumer용 Channel (별도)
    this.consumerChannel = await this.connection.createChannel();
    await this.consumerChannel.prefetch(10); // prefetch 설정 필수
  }

  async onModuleDestroy(): Promise<void> {
    await this.publisherChannel?.close();
    await this.consumerChannel?.close();
    await this.connection?.close();
  }

  getPublisherChannel(): amqplib.ConfirmChannel {
    if (!this.publisherChannel) throw new Error('Publisher channel not initialized');
    return this.publisherChannel;
  }

  getConsumerChannel(): amqplib.Channel {
    if (!this.consumerChannel) throw new Error('Consumer channel not initialized');
    return this.consumerChannel;
  }
}
```

`channelCheckoutTimeout`에 해당하는 패턴으로, Channel Pool이 필요하면 `amqplib-plus` 또는 직접 Pool 구현을 사용한다.

```typescript
// Channel Pool 예시 (간단 구현)
@Injectable()
export class ChannelPoolService {
  private readonly pool: amqplib.Channel[] = [];
  private readonly maxSize = 25;

  async acquire(connection: amqplib.Connection): Promise<amqplib.Channel> {
    const ch = this.pool.pop() ?? await connection.createChannel();
    return ch;
  }

  release(channel: amqplib.Channel): void {
    if (this.pool.length < this.maxSize) {
      this.pool.push(channel);
    } else {
      void channel.close();
    }
  }
}
```

---

## Queue 종류

### Quorum Queue vs Classic Mirrored Queue

RabbitMQ 3.8부터 Quorum Queue가 도입됐고, Classic Mirrored Queue는 3.13부터 deprecated다. 신규 시스템은 Quorum Queue를 써야 한다.

| 항목 | Classic Mirrored Queue | Quorum Queue |
|------|----------------------|--------------|
| 복제 방식 | 비동기 미러링 (ha-mode) | Raft 합의 알고리즘 |
| 데이터 안전성 | 미러 lag 중 마스터 장애 시 유실 가능 | 과반수 노드에 기록된 후 ack |
| 설정 | Policy 기반 (`ha-mode`, `ha-params`) | Queue 선언 시 `x-queue-type: quorum` |
| 비순차 재전달 | 없음 | 있을 수 있음 (at-least-once) |
| TTL 지원 | 지원 | 메시지 TTL만 지원 (큐 TTL 미지원) |
| Priority Queue | 지원 | 미지원 |

**Quorum Queue 선언:**

```typescript
import * as amqplib from 'amqplib';

async function declareQuorumQueue(channel: amqplib.Channel): Promise<void> {
  await channel.assertQueue('my.quorum.queue', {
    durable: true,
    arguments: {
      'x-queue-type': 'quorum',
      'x-quorum-initial-group-size': 3, // 복제 노드 수
    },
  });
}
```

`x-quorum-initial-group-size`는 클러스터 노드 수 이하로 설정해야 한다. 3노드 클러스터면 3이 적당하다. 5노드 클러스터에서 5로 설정하면 모든 노드에 복제되지만 쓰기 성능이 떨어진다.

**Quorum Queue에서 주의할 점:**

- `exclusive`, `non-durable` 옵션은 쓸 수 없다. 항상 durable이다.
- 메시지가 requeue되면 원래 순서가 보장되지 않는다. 순서가 중요한 처리에서 nack+requeue를 쓸 때 주의해야 한다.
- poison message handling을 위해 `x-delivery-limit`을 설정할 수 있다. 이 횟수를 초과하면 DLQ로 간다.

```typescript
await channel.assertQueue('my.quorum.queue', {
  durable: true,
  arguments: {
    'x-queue-type': 'quorum',
    'x-delivery-limit': 5, // 5번 재전달 후 DLQ로
  },
});
```

### Lazy Queue

Lazy Queue는 메시지를 최대한 디스크에 저장하고 Consumer가 요청할 때만 메모리로 올린다.

```typescript
await channel.assertQueue('my.lazy.queue', {
  durable: true,
  arguments: {
    'x-queue-mode': 'lazy',
  },
});
```

일반 큐는 메시지를 메모리에 유지하다가 메모리 pressure가 생기면 디스크로 내린다. Lazy Queue는 처음부터 디스크에 쓴다.

쓰는 경우:

- 큐에 메시지가 수백만 건 쌓이는 구조 (Consumer가 간헐적으로 처리)
- Memory Alarm이 자주 발생하는 환경
- 처리량보다 안정성이 중요한 경우

RabbitMQ 3.12부터 Quorum Queue는 기본적으로 lazy 동작을 한다. Classic Queue에서만 별도 설정이 필요하다.

### Priority Queue

```typescript
await channel.assertQueue('my.priority.queue', {
  durable: true,
  arguments: {
    'x-max-priority': 10, // 우선순위 범위 0~10
  },
});
```

메시지 발행 시 priority를 지정한다:

```typescript
channel.publish('exchange', 'routing.key', Buffer.from(body), {
  priority: 5,
});
```

`x-max-priority` 값이 클수록 내부적으로 우선순위별 서브큐를 많이 만든다. 10 이하로 설정하는 게 좋다. 255까지 가능하지만 메모리와 CPU 오버헤드가 심하다.

priority가 같은 메시지끼리는 FIFO 순서를 유지한다. Consumer의 prefetch가 높으면 브로커 측에서 정렬해도 Consumer 측 버퍼에서 순서가 섞일 수 있다. 우선순위가 중요하면 prefetch를 1로 낮추는 게 안전하다.

---

## Memory/Disk Alarm과 Flow Control

### Memory Alarm

RabbitMQ는 사용 메모리가 임계값을 초과하면 **모든 Publisher의 Connection을 블로킹**한다. Consumer는 정상 동작한다.

```ini
# rabbitmq.conf
vm_memory_high_watermark.relative = 0.4  # 시스템 메모리의 40% (기본값)
# 또는 절대값
# vm_memory_high_watermark.absolute = 2GB
```

Memory Alarm이 발생하면:

1. Publisher Connection이 블로킹된다 (write 버퍼가 꽉 찬 것처럼 동작)
2. 브로커가 메모리를 확보하려고 큐의 메시지를 디스크로 내린다 (paging)
3. 메모리가 임계값 아래로 내려가면 블로킹이 풀린다

`vm_memory_high_watermark_paging_ratio`(기본 0.5)를 설정하면 임계값의 50%에서 미리 paging을 시작한다.

### Disk Alarm

```ini
disk_free_limit.relative = 1.5  # 메모리 크기의 1.5배 (기본값)
# 또는 절대값
disk_free_limit.absolute = 5GB
```

디스크 여유 공간이 임계값 아래로 떨어지면 Memory Alarm과 마찬가지로 Publisher를 블로킹한다. 여기에 더해 메시지를 디스크에 쓰는 것도 중단한다.

디스크가 가득 차면 브로커 자체가 기동 불가 상태에 빠질 수 있다. 운영에서 디스크 모니터링은 필수다.

### Flow Control

Publisher가 브로커 처리 속도보다 빠르게 메시지를 보내면 내부적으로 credit 기반 flow control이 동작한다.

```
Publisher → [TCP Buffer] → [Connection Process] → [Channel Process] → [Queue Process]
```

각 단계의 프로세스가 뒤쪽 프로세스에게 credit을 발급한다. credit이 소진되면 앞쪽 프로세스가 일시 정지한다. Management UI에서 Connection 상태가 `flow`로 표시되면 해당 Connection에 flow control이 걸린 것이다.

flow control이 자주 발생하면:

- Publisher 속도를 줄이거나
- Consumer를 늘리거나
- 큐를 여러 개로 분산(consistent hash exchange 등)하거나
- 노드를 추가해야 한다

---

## Shovel과 Federation

두 기능 모두 서로 다른 RabbitMQ 클러스터(또는 노드) 간에 메시지를 전달하는 용도다.

### Shovel

한쪽 큐에서 메시지를 꺼내서 다른 쪽 exchange/queue로 넣는다. 단순한 포인트-투-포인트 전달이다.

```bash
rabbitmq-plugins enable rabbitmq_shovel
rabbitmq-plugins enable rabbitmq_shovel_management  # Management UI 연동
```

**Dynamic Shovel (API로 설정):**

```bash
rabbitmqctl set_parameter shovel my-shovel \
  '{"src-protocol": "amqp091", "src-uri": "amqp://user:pass@source-host",
    "src-queue": "source-queue",
    "dest-protocol": "amqp091", "dest-uri": "amqp://user:pass@dest-host",
    "dest-exchange": "dest-exchange",
    "ack-mode": "on-confirm",
    "reconnect-delay": 5}'
```

`ack-mode` 옵션:

- `on-confirm`: 대상 브로커의 confirm을 받은 후 원본에서 ack. 메시지 유실 없음.
- `on-publish`: 대상 브로커에 publish한 즉시 원본에서 ack. confirm보다 빠르지만 유실 가능.
- `no-ack`: 원본에서 auto-ack. 가장 빠르지만 유실 위험 큼.

### Federation

Exchange나 Queue를 upstream/downstream 관계로 연결한다. Shovel과 달리 "구독" 기반이라서 downstream 쪽에서 Consumer가 있을 때만 메시지를 가져온다.

```bash
rabbitmq-plugins enable rabbitmq_federation
rabbitmq-plugins enable rabbitmq_federation_management
```

```bash
# upstream 정의
rabbitmqctl set_parameter federation-upstream my-upstream \
  '{"uri": "amqp://user:pass@upstream-host", "expires": 3600000}'

# policy로 exchange에 federation 적용
rabbitmqctl set_policy federate-me "^federated\." \
  '{"federation-upstream-set": "all"}' --apply-to exchanges
```

**Shovel vs Federation 선택 기준:**

- 단순히 한쪽에서 다른 쪽으로 메시지를 옮기는 거면 Shovel
- 여러 데이터센터의 exchange를 논리적으로 합치고 싶으면 Federation
- Shovel은 항상 메시지를 전달하고, Federation은 downstream에 Consumer가 있을 때만 전달한다

---

## Management Plugin 모니터링

```bash
rabbitmq-plugins enable rabbitmq_management
```

기본 포트 15672에서 웹 UI를 제공한다. 운영에서 봐야 할 핵심 지표:

### 주요 메트릭

**큐 레벨:**

- `messages_ready`: Consumer에게 전달 가능한 메시지 수. 계속 증가하면 Consumer가 부족하다는 뜻.
- `messages_unacknowledged`: Consumer에게 전달됐지만 아직 ack 안 된 메시지 수. 이 값이 prefetch와 같으면 Consumer가 처리 한계에 도달한 것.
- `message_bytes`: 큐가 점유하는 메모리/디스크 크기.

**노드 레벨:**

- `mem_used` / `mem_limit`: 메모리 사용량과 임계값.
- `disk_free` / `disk_free_limit`: 디스크 여유 공간.
- `fd_used` / `fd_total`: 파일 디스크립터 사용량. 고갈되면 새 연결을 못 받는다.
- `sockets_used` / `sockets_total`: 소켓 사용량.

**Connection/Channel 레벨:**

- `state`: running, blocking, blocked, flow 등. blocked나 flow가 보이면 문제.
- `channels`: Connection당 Channel 수. 비정상적으로 많으면 Channel leak을 의심.

### HTTP API

Management Plugin은 REST API도 제공한다.

```bash
# 큐 목록
curl -u guest:guest http://localhost:15672/api/queues

# 특정 큐 상세
curl -u guest:guest http://localhost:15672/api/queues/%2F/my-queue

# 노드 상태
curl -u guest:guest http://localhost:15672/api/nodes
```

Prometheus 연동이 필요하면 `rabbitmq_prometheus` 플러그인을 쓴다.

```bash
rabbitmq-plugins enable rabbitmq_prometheus
# http://localhost:15692/metrics 에서 Prometheus 형식으로 노출
```

---

## NestJS amqplib 심화

### 재시도 설정 (Exponential Backoff)

Consumer 처리 실패 시 재시도 로직을 NestJS 레벨에서 처리한다. RabbitMQ의 requeue와 다르게 메시지를 큐에 돌려보내지 않고 Consumer 프로세스 내에서 재시도한다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import * as amqplib from 'amqplib';

interface RetryOptions {
  maxAttempts: number;
  initialInterval: number; // ms
  multiplier: number;
  maxInterval: number; // ms
}

@Injectable()
export class RabbitConsumerService {
  private readonly logger = new Logger(RabbitConsumerService.name);

  async consumeWithRetry(
    channel: amqplib.Channel,
    queueName: string,
    handler: (msg: amqplib.ConsumeMessage) => Promise<void>,
    options: RetryOptions = {
      maxAttempts: 3,
      initialInterval: 1000,
      multiplier: 2.0,
      maxInterval: 10000,
    },
  ): Promise<void> {
    await channel.consume(queueName, async (msg) => {
      if (!msg) return;

      let attempt = 0;
      let delay = options.initialInterval;

      while (attempt < options.maxAttempts) {
        try {
          await handler(msg);
          channel.ack(msg);
          return;
        } catch (err) {
          attempt++;
          this.logger.warn(`처리 실패 (시도 ${attempt}/${options.maxAttempts}): ${err}`);

          if (attempt >= options.maxAttempts) {
            // 모든 재시도 실패 → DLQ로 (requeue=false)
            channel.nack(msg, false, false);
            return;
          }

          // 지수 백오프 대기
          await new Promise((r) => setTimeout(r, Math.min(delay, options.maxInterval)));
          delay *= options.multiplier;
        }
      }
    }, { noAck: false });
  }
}
```

주의: 재시도 간격이 길면 해당 Promise가 묶인다. prefetch에 포함된 다른 메시지 처리도 지연된다.

### MessageRecoverer 패턴

재시도가 모두 실패하면 DLQ exchange로 재발행한다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import * as amqplib from 'amqplib';

@Injectable()
export class DeadLetterPublisher {
  private readonly logger = new Logger(DeadLetterPublisher.name);

  async republishToDeadLetter(
    channel: amqplib.ConfirmChannel,
    originalMsg: amqplib.ConsumeMessage,
    error: Error,
    dlxExchange: string,
    dlxRoutingKey: string,
  ): Promise<void> {
    // 원본 메시지에 예외 정보를 헤더로 추가
    const headers = {
      ...originalMsg.properties.headers,
      'x-exception-message': error.message,
      'x-exception-stack': error.stack?.substring(0, 500) ?? '',
      'x-original-queue': originalMsg.fields.routingKey,
    };

    return new Promise((resolve, reject) => {
      channel.publish(
        dlxExchange,
        dlxRoutingKey,
        originalMsg.content,
        { headers, persistent: true },
        (err) => (err ? reject(err) : resolve()),
      );
    });
  }
}
```

`RepublishMessageRecoverer`와 동일한 역할: 원본 메시지에 예외 스택트레이스를 헤더로 붙여서 DLQ로 발행한다. 나중에 DLQ에서 메시지를 꺼내 원인을 분석할 때 유용하다.

### 용도별 Consumer 분리

용도별로 Channel을 분리하면 큐마다 다른 설정을 적용할 수 있다.

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import * as amqplib from 'amqplib';

@Injectable()
export class MultiConsumerService implements OnModuleInit {
  private connection!: amqplib.Connection;

  async onModuleInit(): Promise<void> {
    this.connection = await amqplib.connect('amqp://guest:guest@localhost');

    // 일반 처리용 Channel
    await this.setupDefaultConsumer();

    // 고처리량용 Channel
    await this.setupHighThroughputConsumer();

    // 순서 보장용 Channel
    await this.setupOrderedConsumer();
  }

  private async setupDefaultConsumer(): Promise<void> {
    const channel = await this.connection.createChannel();
    await channel.prefetch(10); // 기본 prefetch
    await channel.consume('default.queue', async (msg) => {
      if (!msg) return;
      try {
        await this.handleDefault(msg);
        channel.ack(msg);
      } catch {
        channel.nack(msg, false, false); // DLX로
      }
    }, { noAck: false });
  }

  private async setupHighThroughputConsumer(): Promise<void> {
    const channel = await this.connection.createChannel();
    await channel.prefetch(50); // 고처리량: prefetch 높게
    // 배치 처리를 위해 버퍼 수집
    const buffer: amqplib.ConsumeMessage[] = [];
    await channel.consume('high.volume.queue', async (msg) => {
      if (!msg) return;
      buffer.push(msg);
      if (buffer.length >= 10) {
        const batch = buffer.splice(0, 10);
        await this.handleBatch(batch);
        batch.forEach((m) => channel.ack(m));
      }
    }, { noAck: false });
  }

  private async setupOrderedConsumer(): Promise<void> {
    const channel = await this.connection.createChannel();
    await channel.prefetch(1); // 순서 보장: prefetch=1, 하나씩 처리
    await channel.consume('ordered.queue', async (msg) => {
      if (!msg) return;
      await this.handleOrdered(msg);
      channel.ack(msg);
    }, { noAck: false });
  }

  private async handleDefault(msg: amqplib.ConsumeMessage): Promise<void> { /* ... */ }
  private async handleBatch(msgs: amqplib.ConsumeMessage[]): Promise<void> { /* ... */ }
  private async handleOrdered(msg: amqplib.ConsumeMessage): Promise<void> { /* ... */ }
}
```

---

## Dead Letter Exchange (DLX) 구성

메시지가 DLQ로 가는 조건:

1. Consumer가 `reject` 또는 `nack`(requeue=false)
2. 메시지 TTL 만료
3. 큐의 max-length 초과

```typescript
import * as amqplib from 'amqplib';

async function setupDlxQueues(channel: amqplib.Channel): Promise<void> {
  // DLX와 DLQ 선언
  await channel.assertExchange('dlx.exchange', 'direct', { durable: true });
  await channel.assertQueue('dlq.queue', { durable: true });
  await channel.bindQueue('dlq.queue', 'dlx.exchange', 'dlx.routing.key');

  // 원본 큐에 DLX 설정
  await channel.assertQueue('my.queue', {
    durable: true,
    arguments: {
      'x-dead-letter-exchange': 'dlx.exchange',
      'x-dead-letter-routing-key': 'dlx.routing.key',
      'x-message-ttl': 60000, // 60초 후 만료 → DLQ로
    },
  });
}
```

DLQ에 들어간 메시지의 `x-death` 헤더를 보면 어디서 왜 dead letter가 됐는지 알 수 있다.

```typescript
import { Injectable, Logger } from '@nestjs/common';
import * as amqplib from 'amqplib';

interface XDeath {
  reason: string;  // 'rejected' | 'expired' | 'maxlen'
  queue: string;   // 원본 큐 이름
  count: number;   // dead letter된 횟수
}

@Injectable()
export class DeadLetterConsumer {
  private readonly logger = new Logger(DeadLetterConsumer.name);

  async startDlqConsumer(channel: amqplib.Channel): Promise<void> {
    await channel.consume('dlq.queue', (msg) => {
      if (!msg) return;

      const xDeath = msg.properties.headers?.['x-death'] as XDeath[] | undefined;
      if (xDeath && xDeath.length > 0) {
        const death = xDeath[0];
        this.logger.error(
          `DLQ 메시지 수신 - reason: ${death.reason}, queue: ${death.queue}, count: ${death.count}`,
        );
        // 알림 전송 또는 별도 처리
      }

      channel.ack(msg);
    }, { noAck: false });
  }
}
```

---

## 운영 시 자주 겪는 문제

### Channel leak

Connection은 살아있는데 Channel이 계속 늘어나는 경우. 보통 Channel을 열고 닫지 않는 코드 버그다. Management UI에서 Connection당 Channel 수를 확인한다.

amqplib에서 직접 Channel을 생성하는 경우 반드시 try-finally로 닫아야 한다.

```typescript
const channel = await connection.createChannel();
try {
  // 작업 수행
  await channel.publish(/* ... */);
} finally {
  await channel.close(); // 반드시 닫기
}
```

장기 실행 서비스에서는 onModuleInit에서 생성하고 onModuleDestroy에서 닫는 패턴을 사용한다.

### Unacked 메시지 증가

`messages_unacknowledged`가 계속 증가하면 Consumer가 ack를 보내지 않는 것이다. 처리가 느린 건지 ack 코드를 빼먹은 건지 확인해야 한다. Consumer가 죽으면 해당 Consumer의 unacked 메시지는 다시 큐로 돌아간다.

### 큐 메시지 폭증

Consumer보다 Publisher가 빠르면 메시지가 계속 쌓인다. Memory Alarm이 발생하기 전에 `x-max-length`나 `x-max-length-bytes`로 큐 크기 제한을 걸어두면 overflow 시 DLQ로 보내거나 head 메시지를 버릴 수 있다.

```typescript
await channel.assertQueue('my.queue', {
  durable: true,
  arguments: {
    'x-max-length': 100000,
    'x-overflow': 'reject-publish', // 큐 가득 차면 publisher에게 nack
    // 또는 'drop-head': 가장 오래된 메시지 버림
  },
});
```

---
이 문서는 [메시징과 전달 보장 허브](../../_hub/메시징과_전달_보장.md)의 일부입니다.
