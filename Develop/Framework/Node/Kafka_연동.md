---
title: "kafkajs Consumer Group 운영과 재처리"
tags: [nodejs, messaging, event-driven, backend, architecture]
updated: 2026-09-05
---

## Consumer Group이 실제로 하는 일

kafkajs로 Consumer Group을 구성하면 내부에서 파티션 할당 협상(rebalance)이 일어난다. 인스턴스가 3개고 파티션이 6개면 각 인스턴스가 2개씩 가져간다. 인스턴스를 하나 내리면 나머지 둘이 3개씩 재할당받는다. 이 재할당 중에 소비가 멈추는 시간이 있다 — 기본 `sessionTimeout`(30초)과 `heartbeatInterval`(3초)이 그 길이를 결정한다.

문제는 `sessionTimeout`을 짧게 잡으면 배포나 GC pause 때 쓸데없이 rebalance가 터진다는 것이다. 운영하다 보면 배포할 때마다 컨슈머가 30초씩 멈추는 상황을 겪는다. kafkajs 기본값은 이미 타이트하다.

```ts
const consumer = kafka.consumer({
  groupId: 'order-service',
  sessionTimeout: 30000,
  heartbeatInterval: 3000,
  maxWaitTimeInMs: 5000,   // poll 한 번에 최대 대기
  minBytes: 1,
  maxBytes: 1048576,       // 1MB per fetch
});
```

`maxWaitTimeInMs`는 브로커가 minBytes를 채울 때까지 기다리는 시간이다. 낮추면 폴링 빈도가 올라가고 CPU가 올라간다. 메시지 유입이 드문 토픽은 50~200ms로 잡는 게 맞다.

## 파티션 수와 처리량 계산

파티션 수가 처리량 한계를 결정한다. Consumer Group 내에서 파티션 하나는 인스턴스 하나에만 붙는다. 파티션 3개면 인스턴스를 10개 띄워도 3개만 일한다.

목표 처리량에서 파티션 수를 역산하는 공식이다.

```
파티션 수 = 목표 TPS / (인스턴스당 처리 TPS)

예:
- 목표: 초당 1,000 메시지
- 인스턴스 1개가 처리할 수 있는 TPS: 200 (DB write 포함 기준)
- 필요 파티션: 1000 / 200 = 5 → 여유분 포함 6~8
```

여기서 자주 틀리는 부분이 있다. 인스턴스당 TPS를 "순수 kafkajs poll 속도"로 잡으면 틀린다. 메시지 한 건 처리하는 데 DB write, 외부 API 호출, 캐시 조회가 포함된다면 그 지연이 처리량을 결정한다. `eachMessage` 안에서 await 하나에 50ms가 걸리면 인스턴스 하나가 20 TPS밖에 못 낸다.

배치 처리로 이 한계를 넘길 수 있다.

```ts
await consumer.run({
  eachBatchAutoResolve: false,
  eachBatch: async ({ batch, resolveOffset, heartbeat, isRunning, isStale }) => {
    const messages = batch.messages;

    // 100건씩 묶어서 DB bulk insert
    for (let i = 0; i < messages.length; i += 100) {
      if (!isRunning() || isStale()) break;

      const chunk = messages.slice(i, i + 100);
      await bulkInsert(chunk.map(m => JSON.parse(m.value.toString())));

      resolveOffset(chunk[chunk.length - 1].offset);
      await heartbeat(); // 긴 배치 처리 중 세션 유지
    }
  },
});
```

`eachBatchAutoResolve: false`로 두고 직접 `resolveOffset`을 호출한다. 중간에 실패하면 마지막으로 커밋한 offset 이후부터 재처리된다.

## commit 시점 선택

kafkajs의 `autoCommit`은 기본 true고, `autoCommitInterval`마다 현재까지 poll한 메시지의 offset을 커밋한다. 처리 중간에 프로세스가 죽으면 이미 커밋된 메시지는 재처리되지 않는다 — 유실이다.

```ts
// autoCommit 기본 설정 (유실 가능)
const consumer = kafka.consumer({ groupId: 'order-service' });
await consumer.run({
  autoCommit: true,
  autoCommitInterval: 5000,
  eachMessage: async ({ message }) => {
    await processOrder(message); // 여기서 죽으면 재처리 없음
  },
});
```

적어도 한 번 처리(at-least-once)가 필요하면 `autoCommit: false`로 끄고 처리 완료 후 직접 커밋한다.

```ts
await consumer.run({
  autoCommit: false,
  eachMessage: async ({ topic, partition, message }) => {
    await processOrder(message);

    await consumer.commitOffsets([{
      topic,
      partition,
      offset: (BigInt(message.offset) + 1n).toString(),
    }]);
  },
});
```

offset은 "다음에 읽을 위치"다. 현재 offset이 42면 43을 커밋해야 43부터 읽는다. 이걸 빠뜨리고 42를 커밋하면 42를 무한히 재처리한다.

`eachBatch`에서 `eachBatchAutoResolve: false`를 쓸 때도 마찬가지다. `resolveOffset`은 내부 상태만 바꾸고 실제 커밋은 `commitOffsets`로 별도 호출해야 한다. 아니면 `eachBatchAutoResolve: true`로 두고 배치 전체가 끝난 뒤 자동으로 커밋되도록 두는 것도 방법이다. 단, 배치 중간에 죽으면 배치 전체를 다시 받는다.

### 멱등성이 없으면 at-least-once는 의미가 없다

수동 커밋으로 at-least-once를 보장해도 처리 로직이 멱등하지 않으면 중복 처리가 그대로 생긴다. 결제 요청 메시지를 두 번 처리하면 결제가 두 번 나간다. DB에 `message_id`를 unique key로 잡거나, Redis에 처리 여부를 기록하는 방식으로 멱등성을 따로 구현해야 한다.

## DLQ 패턴과 재처리

메시지 처리가 실패했을 때 그냥 에러를 던지면 kafkajs가 같은 메시지를 계속 재시도한다. `retry` 옵션이 소진되면 컨슈머가 crash하고 재시작된다 — 처리 못 하는 메시지 하나가 전체 파티션 소비를 멈춘다.

DLQ(Dead Letter Queue)는 실패한 메시지를 별도 토픽으로 빼내는 패턴이다. 원본 파티션 소비는 계속 진행하고, 실패 메시지는 나중에 따로 처리한다.

```ts
const producer = kafka.producer();

await consumer.run({
  autoCommit: false,
  eachMessage: async ({ topic, partition, message }) => {
    let attempt = 0;
    const maxAttempts = 3;

    while (attempt < maxAttempts) {
      try {
        await processOrder(message);
        break;
      } catch (err) {
        attempt++;
        if (attempt >= maxAttempts) {
          // DLQ로 이동
          await producer.send({
            topic: `${topic}.dlq`,
            messages: [{
              key: message.key,
              value: message.value,
              headers: {
                ...message.headers,
                'x-original-topic': topic,
                'x-original-partition': String(partition),
                'x-original-offset': message.offset,
                'x-failure-reason': err.message,
                'x-retry-count': String(attempt),
              },
            }],
          });
        } else {
          // 지수 백오프
          await new Promise(r => setTimeout(r, 100 * 2 ** attempt));
        }
      }
    }

    await consumer.commitOffsets([{
      topic,
      partition,
      offset: (BigInt(message.offset) + 1n).toString(),
    }]);
  },
});
```

DLQ 토픽에 원본 위치 정보(`x-original-topic`, `x-original-partition`, `x-original-offset`)를 헤더로 남기는 게 중요하다. 나중에 원인을 파악하고 재처리할 때 어디서 왔는지 추적할 수 있다.

DLQ 소비자는 별도로 구성한다. 수동으로 트리거하거나, 알림을 받고 수정 후 재발행하는 흐름으로 운영한다.

### 재처리 시 주의

DLQ에서 원본 토픽으로 메시지를 다시 보낼 때 파티션 지정에 주의해야 한다. key 기반 파티셔닝을 쓰는 토픽이면 같은 key로 재발행하면 같은 파티션으로 간다. 파티션 수가 바뀌었으면 다른 파티션으로 갈 수 있다 — 순서 보장이 필요한 경우 문제가 된다.

## Consumer Group 운영 중 흔히 겪는 것들

**rebalance가 너무 자주 일어난다.** `sessionTimeout`을 늘리거나, `maxPollIntervalMs`를 처리 시간에 맞게 늘린다. `eachMessage`에서 처리 하나에 10초가 걸리는데 `maxPollIntervalMs`가 5초면 매번 rebalance가 터진다.

```ts
const consumer = kafka.consumer({
  groupId: 'order-service',
  sessionTimeout: 45000,
  maxWaitTimeInMs: 5000,
  // kafkajs에는 maxPollIntervalMs 직접 옵션 없음
  // 브로커 설정 max.poll.interval.ms 와 맞춰야 함
});
```

**lag이 계속 쌓인다.** `kafka-consumer-groups.sh --describe` 또는 Kafka UI로 lag을 모니터링한다. lag이 줄지 않으면 파티션을 늘리거나 인스턴스를 추가해야 한다. 단, 파티션 추가는 브로커에서 해야 하고, key 기반 라우팅을 쓰면 기존 메시지 분포가 깨진다.

**특정 파티션에서만 처리가 느리다.** key 설계 문제다. 주문 ID를 key로 쓰면 균등하게 분산되지만, 특정 userId를 key로 쓰면 그 유저의 주문이 다 같은 파티션으로 간다. hot partition이 생기면 파티션 수를 늘려도 해당 파티션의 처리량은 안 늘어난다. key 설계를 바꾸는 것 외에 방법이 없다.
