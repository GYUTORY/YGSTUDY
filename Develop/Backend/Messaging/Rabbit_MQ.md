---
title: RabbitMQ 심화
tags: [messaging, backend, aws]
updated: 2026-10-19
---

# RabbitMQ 심화

RabbitMQ는 AMQP 0-9-1 프로토콜 기반의 메시지 브로커다. Kafka와 달리 메시지를 Consumer가 처리하면 큐에서 제거하는 전통적인 메시지 큐 모델이다. 이 문서는 RabbitMQ를 운영 수준에서 다루기 위해 필요한 내용을 정리한다.

---

## 메시지가 큐에 닿는 경로

Producer는 큐에 직접 쓰지 않는다. Exchange에 메시지를 발행하고, Exchange가 바인딩 규칙에 따라 큐를 고른다. Consumer는 큐에서만 읽는다. 이 구조를 놓치면 "publish는 성공했는데 아무도 못 받는" 상황을 설명할 수 없다.

아래 도식은 Exchange 타입 네 가지가 각자 어떤 기준으로 큐를 고르는지 보여준다. Exchange 하나는 타입 하나만 가진다. 같은 메시지를 타입별로 다르게 나누려면 Exchange를 따로 만든다.

```mermaid
flowchart LR
    P1["Producer A"] -->|"routing key: order.kr.created"| XD{{"direct Exchange"}}
    P1 -->|"routing key: order.kr.created"| XT{{"topic Exchange"}}
    P2["Producer B"] --> XF{{"fanout Exchange"}}
    P2 -->|"헤더 region=kr, tier=gold"| XH{{"headers Exchange"}}

    XD -->|"Binding: order.kr.created"| Q1[["Queue: payment"]]
    XT -->|"Binding: order.*.created"| Q2[["Queue: shipping"]]
    XT -->|"Binding: order.#"| Q3[["Queue: audit"]]
    XF -->|"Binding: 조건 없음"| Q3
    XF -->|"Binding: 조건 없음"| Q4[["Queue: mail"]]
    XH -->|"Binding: x-match=all"| Q5[["Queue: vip"]]

    Q1 --> C1["Consumer"]
    Q2 --> C2["Consumer"]
    Q3 --> C3["Consumer"]
    Q4 --> C4["Consumer"]
    Q5 --> C5["Consumer"]
```

타입별 매칭 규칙은 4.0.9 단일 노드에서 직접 발행해 확인했다.

| 타입 | 매칭 기준 | 확인한 결과 |
|------|-----------|-------------|
| direct | routing key와 binding key가 정확히 일치 | 일치하지 않으면 큐에 가지 않는다 |
| topic | `*`는 단어 하나, `#`은 단어 0개 이상 | `order.*.created`에 `order.kr.created`만 매칭, `order.created`와 `order.kr.jp.created`는 불일치. `order.#`에는 세 키가 모두 매칭 |
| fanout | routing key를 보지 않고 바인딩된 모든 큐로 복사 | 큐마다 사본이 생긴다 |
| headers | 메시지 헤더와 binding 인자 비교, `x-match`가 `all`이면 전부 일치해야 한다 | `region=kr, tier=gold` 둘 다 있으면 라우팅, `region=kr`만 있으면 `routed: false` |

topic에서 `*`와 `#`을 헷갈리면 큐가 비어 있는 원인을 한참 찾게 된다. `order.*.created`는 점으로 구분한 단어가 정확히 세 개일 때만 맞는다. 단어 수가 가변이면 `#`을 써야 한다.

도식의 `audit` 큐처럼 한 큐에 topic과 fanout이 같이 바인딩돼 있으면, 같은 이벤트를 두 Exchange에 모두 발행하는 순간 사본이 두 개 쌓인다. 바인딩을 추가할 때는 그 큐에 이미 걸린 다른 Exchange를 먼저 본다.

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

### ack, nack, requeue가 DLX로 이어지는 경로

메시지는 큐에서 Consumer로 나가는 순간 `unacked`가 되고, 이후 경로는 Consumer가 무엇을 보내느냐로 갈린다. Consumer가 응답하지 않고 채널이나 연결이 끊기면 브로커가 `unacked` 메시지를 `ready`로 되돌린다. TTL 만료와 max-length 초과는 Consumer와 무관하게 큐 쪽에서 바로 DLX로 간다.

```mermaid
flowchart TD
    R["Queue: ready"] -->|"deliver"| U["unacked"]
    U -->|"ack"| DONE["큐에서 제거"]
    U -->|"채널/연결 종료"| R
    U -->|"nack/reject, requeue=true"| LIM{"x-delivery-limit 초과<br/>(쿼럼 큐만)"}
    LIM -->|"아니오"| R
    LIM -->|"예"| DLXQ{"DLX 설정됨"}
    U -->|"nack/reject, requeue=false"| DLXQ
    R -->|"message TTL 만료<br/>x-max-length 초과"| DLXQ
    DLXQ -->|"예"| DLQ["Dead Letter Exchange<br/>→ DLQ"]
    DLXQ -->|"아니오"| DROP["메시지 폐기"]
```

`LIM`에서 `ready`로 돌아가는 화살표가 무한 루프의 원인이다. 쿼럼 큐에서는 `x-delivery-limit`이 그 루프를 끊는다. 이 판정에 기대지 않는 경우에는 앞에서 말한 대로 재시도 횟수를 직접 세야 한다.

4.0.9 쿼럼 큐에서 `x-delivery-limit: 2`, DLX 지정, 매번 `requeue=true`로 reject하는 조건으로 돌려봤다. 전달은 총 3번 일어났다. 최초 전달 1번에 재전달 2번이고, 네 번째 get은 빈 결과였다. DLQ에 들어온 메시지의 `x-death`는 `reason: delivery_limit`이었다. 아래 DLX 절에서 다루는 `rejected`, `expired`, `maxlen`에 이 값이 하나 더 있다.

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

RabbitMQ 3.8부터 Quorum Queue가 도입됐다. Classic Mirrored Queue는 3.13.7에서 `rabbitmqctl list_deprecated_features`에 `classic_queue_mirroring`이 `permitted_by_default`로 올라 있고, 4.0.9에서는 같은 항목이 `removed`다. 4.0.9에 `ha-mode` 정책을 걸면 `are not recognised policy settings`로 400이 돌아온다. 3.13에서 잘 돌던 정책 스크립트가 4.0 업그레이드 때 그대로 실패한다는 뜻이다. 신규 시스템은 Quorum Queue를 써야 한다.

두 방식은 리더가 죽었을 때 새 리더를 정하는 방식이 다르다. 아래 도식은 3노드 클러스터에서 노드 1이 리더(마스터)일 때를 기준으로 그렸다.

```mermaid
flowchart LR
    subgraph CM["Classic Mirrored Queue (3.13 이하)"]
        direction TB
        CP["Publisher"] --> CL["노드 1: 마스터"]
        CL -->|"정책 ha-mode로 복제"| CM2["노드 2: 미러"]
        CL -->|"정책 ha-mode로 복제"| CM3["노드 3: 미러"]
        CL -.->|"노드 1 장애"| CPR["동기화된 미러 중 하나가 마스터로 승격"]
    end

    subgraph QQ["Quorum Queue (Raft)"]
        direction TB
        QP["Publisher"] --> QL["노드 1: 리더"]
        QL -->|"로그 복제"| QF2["노드 2: 팔로워"]
        QL -->|"로그 복제"| QF3["노드 3: 팔로워"]
        QL -.->|"노드 1 장애"| QEL["남은 팔로워가 투표해 과반수로 새 리더 선출"]
    end
```

왼쪽은 마스터가 죽으면 살아 있는 미러 중에서 승격시킨다. 오른쪽은 투표다. 과반수가 모이지 않으면 리더가 뽑히지 않는다. 3.13.7 3노드 클러스터에 `ha-mode: all`, `ha-sync-mode: automatic` 정책을 걸고 마스터 노드(노드 1)를 내리자 동기화된 미러였던 노드 3이 마스터가 됐고, 노드 2는 그대로 미러로 남았다.

4.0.9 3노드 클러스터에서 쿼럼 큐를 선언하면 `x-quorum-initial-group-size`를 주지 않아도 멤버 3개(리더 1, 팔로워 2)로 만들어졌다. 리더 노드를 내리면 남은 두 노드 중 하나가 새 리더가 됐다. `rabbitmq-queues quorum_status`에서 내려간 노드는 `{nodedown,...}`으로 보이고, 리더 선출을 거치면서 Term이 1에서 4로 올라갔다. 노드를 하나 더 내려 한 대만 남기면 그 노드는 `leader`가 되지 못하고 `pre_vote`에 머물렀다. 과반수(3대 중 2대)를 채우지 못하면 투표가 끝나지 않는다.

| 항목 | Classic Mirrored Queue | Quorum Queue |
|------|----------------------|--------------|
| 복제 방식 | 마스터 1개와 미러, `ha-mode` 정책으로 지정 | Raft 합의 알고리즘 |
| 리더 장애 시 | 동기화된 미러가 마스터로 승격 | 팔로워 투표로 새 리더 선출, 과반수 필요 |
| 설정 | Policy 기반 (`ha-mode`, `ha-params`) | Queue 선언 시 `x-queue-type: quorum` |
| 메시지 TTL(`x-message-ttl`) | 지원 | 선언 성공 (3.13.7, 4.0.9) |
| 큐 TTL(`x-expires`) | 지원 | 선언 성공 (3.13.7, 4.0.9) |
| `x-max-priority` | 지원 | 선언 거부 (3.13.7, 4.0.9) |
| `exclusive`, non-durable | 가능 | 선언 거부 (3.13.7, 4.0.9) |
| 4.0 이후 | 제거됨 | 복제 큐의 유일한 선택지 |

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

쿼럼 큐에는 `x-queue-mode: lazy`를 줄 수 없다. 3.13.7과 4.0.9 모두 `invalid arg 'x-queue-mode' ... of queue type rabbit_quorum_queue`로 선언이 거부된다. 쿼럼 큐를 쓰는 곳에서 기존 클래식 큐 선언 코드를 복사해 오면서 이 인자를 같이 끌고 오면 여기서 걸린다. Classic 큐 선언은 4.0.9에서도 받아들여졌지만, 4.0에서 이 인자가 실제로 동작을 바꾸는지는 확인하지 않았다.

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

아래 도식은 위 세 단계를 상태 전이로 그린 것이다. 블로킹된 동안에도 Consumer는 계속 동작하므로 메모리가 줄어들 길이 열려 있다는 점을 보면 된다.

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Blocked : 메모리가 high watermark 초과
    Blocked --> Blocked : paging 으로 큐 메시지를 디스크에 내림
    Blocked --> Normal : 메모리가 임계값 아래로 내려감
```

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

두 방식의 전달 조건 차이를 나란히 놓으면 아래와 같다. Federation 쪽에서만 downstream의 Consumer 유무가 분기점이 된다.

```mermaid
flowchart LR
    subgraph SH["Shovel"]
        direction LR
        SQ["source Queue"] -->|"항상 꺼내서 전달"| SD["dest Exchange / Queue"]
    end

    subgraph FD["Federation"]
        direction LR
        UP["upstream Exchange"] --> CHK{"downstream에 Consumer 있음"}
        CHK -->|"예"| DOWN["downstream Exchange"]
        CHK -->|"아니오"| HOLD["전달하지 않음"]
    end
```

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

위 `consumeWithRetry`의 분기를 흐름으로 그리면 아래와 같다. 재시도는 requeue 없이 Consumer 프로세스 안에서 돌고, 마지막에만 `nack(requeue=false)`로 DLX에 넘긴다.

```mermaid
flowchart TD
    M["메시지 수신"] --> H["handler 실행"]
    H -->|"성공"| A["ack"]
    H -->|"실패"| C{"attempt >= maxAttempts"}
    C -->|"아니오"| W["지수 백오프 대기<br/>delay *= multiplier"]
    W --> H
    C -->|"예"| N["nack, requeue=false"]
    N --> DLX["DLX → DLQ"]
```

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
4. 쿼럼 큐에서 `x-delivery-limit` 초과

경로 전체는 앞의 Consumer Acknowledgement 절 도식에 있다.

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
  reason: string;  // 'rejected' | 'expired' | 'maxlen' | 'delivery_limit'(쿼럼 큐)
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

## Amazon MQ에서 달라지는 것

Amazon MQ for RabbitMQ는 브로커 소프트웨어가 오픈소스 RabbitMQ 그대로라 AMQP 0-9-1 클라이언트 코드는 대부분 그대로 붙는다. 달라지는 쪽은 노드를 만지는 운영 절차다. 이 문서의 예제 중 셸 명령은 자체 호스팅 기준이다.

| 이 문서의 절차 | 관리형에서 |
|----------------|-------------|
| `rabbitmqctl set_policy`, `set_parameter` | 브로커 호스트에 SSH로 들어갈 수 없고 노드 직접 조작이 막혀 있다. 관리 콘솔과 HTTP API만 열려 있다 |
| `rabbitmq-plugins enable ...` | 임의 플러그인을 켤 수 없다. 커뮤니티 플러그인(`rabbitmq_delayed_message_exchange` 등)에 기대면 옮길 수 없다 |
| `amqp://` 5672 평문 접속 | TLS가 강제된다. `amqps://`와 5671을 쓴다 |
| `ha-mode` 미러링 정책 | 엔진 버전이 4.0 이상이면 정책 자체가 없다. 복제가 필요한 큐는 쿼럼 큐로 선언한다 |

Shovel·Federation 절의 `rabbitmq-plugins enable`과 `rabbitmqctl set_parameter` 절차는 위 표 때문에 그대로 쓸 수 없다. 이 두 기능을 관리형에서 쓸 수 있는지는 이 문서에서 확인하지 못했다. 서비스가 제공하는 플러그인 목록과 지원 버전은 브로커를 만들기 전에 AWS 문서에서 확인한다.

자체 호스팅 스크립트가 `rabbitmqctl`로 정책을 걸었다면 HTTP API 호출로 바꾼다. 일반 RabbitMQ 4.0.9에서 확인한 형식은 이렇다.

```bash
curl -u user:pass -H 'content-type: application/json' -X PUT \
  https://<broker-endpoint>/api/policies/%2F/max-len \
  -d '{"pattern":"^work\\.","definition":{"max-length":100000},"apply-to":"queues"}'
```

이 형식을 Amazon MQ 엔드포인트에 그대로 쓸 수 있는지는 직접 호출해 보지 않았다. 지원 버전, 클러스터 배포에서 쿼럼 큐와 미러링이 롤링 재시작 때 어떻게 달라지는지, 메모리 알람 대응은 [Amazon MQ 운영 노트](../../Cloud/AWS/Application_Integration/Amazon_MQ.md)에 정리돼 있다.

---
이 문서는 [메시징과 전달 보장 허브](../../_hub/메시징과_전달_보장.md)의 일부입니다.
