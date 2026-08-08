---
title: Kafka Consumer Group Rebalancing
tags: [messaging, backend]
updated: 2026-08-02
---

# Kafka Consumer Group Rebalancing

컨슈머 그룹 리밸런싱은 파티션 소유권을 재배분하는 과정이다. 리밸런싱 자체는 정상 동작이지만, 잦은 리밸런싱은 처리를 멈추게 해서 컨슈머 지연을 만든다.

## 리밸런스 트리거

리밸런스는 크게 세 가지 상황에서 발생한다.

**컨슈머 수 변경**

새 컨슈머가 그룹에 합류하거나, 컨슈머가 `consumer.close()`로 정상 종료하거나, 크래시·네트워크 단절로 heartbeat가 끊길 때 트리거된다. 크래시와 네트워크 단절은 Group Coordinator 입장에서 구분되지 않는다. 둘 다 `session.timeout.ms` 초과로 처리된다.

**파티션 수 변경**

토픽에 파티션을 추가하면 기존 파티션의 offset은 유지한 채 새 파티션을 재배분한다.

**세션/poll 타임아웃 초과**

`session.timeout.ms` 안에 heartbeat가 도착하지 않으면 Group Coordinator가 해당 컨슈머를 죽은 것으로 판단한다. `max.poll.interval.ms`를 초과해서 `poll()`을 호출하지 않으면 그룹에서 제외된다. 두 타이머가 독립적으로 동작하므로 heartbeat 스레드가 살아있어도 poll 간격이 길면 리밸런스가 발생한다.

## Eager Rebalance vs Incremental Cooperative Rebalance

Kafka 2.4 이전까지 기본 방식은 Eager Rebalance다. 리밸런스가 시작되면 모든 컨슈머가 파티션 소유권을 즉시 반납하고, 새 배정을 받을 때까지 아무 메시지도 처리하지 않는다.

```
[Eager Rebalance 진행 순서]

1. Group Coordinator → 모든 컨슈머: 리밸런스 시작 공지
2. 모든 컨슈머: 보유 파티션 전부 revoke (처리 중단)
3. 모든 컨슈머 → Coordinator: JoinGroup 요청
4. 그룹 리더: 파티션 재배분 계산
5. 리더 → Coordinator: SyncGroup로 배정 결과 전파
6. 모든 컨슈머: 새 파티션으로 fetch 재개
```

3 → 6단계 사이에 전체 처리가 멈춘다. 컨슈머 10개인 그룹에서 컨슈머 1개만 추가해도 나머지 9개가 모두 멈춘다.

**Incremental Cooperative Rebalance**는 Kafka 2.4에서 도입됐다(KIP-429). 두 라운드로 진행된다.

```
[Incremental Cooperative Rebalance 진행 순서]

라운드 1:
1. 모든 컨슈머: 현재 파티션 배정 유지한 채로 JoinGroup 전송
2. 리더: 어떤 파티션을 이동할지 계산
3. revoke 대상 컨슈머만 해당 파티션 반납 (나머지는 계속 처리)

라운드 2:
4. revoke 완료된 컨슈머 → Coordinator: JoinGroup 재전송
5. 리더: 반납된 파티션을 새 컨슈머에게 배정
6. 이동 대상이 아닌 파티션은 처음부터 계속 처리 중
```

처리 중단은 파티션을 이동하는 컨슈머에서만 발생한다. 트래픽이 많은 환경에서 리밸런스가 자주 발생하면 Cooperative 방식이 눈에 띄게 차이가 난다.

**Java 클라이언트 설정:**

```java
props.put(
    ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
    CooperativeStickyAssignor.class.getName()
);
```

**kafkajs (Node.js):**

```typescript
import { Kafka, PartitionAssigners } from 'kafkajs'

const consumer = kafka.consumer({
  groupId: 'order-consumer-group',
  partitionAssigners: [PartitionAssigners.cooperativeSticky]
})
```

Eager에서 Cooperative로 전환할 때 주의점이 있다. 클러스터 내 모든 컨슈머 인스턴스가 동일한 assignor를 써야 한다. 롤링 배포 중 일부는 Eager, 일부는 Cooperative를 쓰면 호환 문제가 생긴다. Kafka는 이를 위한 마이그레이션 경로를 제공한다.

```java
// 마이그레이션 단계: Cooperative를 1순위, Range를 폴백으로
props.put(
    ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
    List.of(
        CooperativeStickyAssignor.class.getName(),
        RangeAssignor.class.getName()
    )
);
// 배포가 완료되고 모든 인스턴스가 Cooperative를 쓰게 되면 RangeAssignor를 제거
```

## Static Group Membership

기본적으로 컨슈머는 재시작할 때마다 새 member ID를 받는다. Group Coordinator는 이전 멤버가 떠나고 새 멤버가 들어온 것으로 인식해서 리밸런스를 두 번 트리거한다 — 종료 시 한 번, 재합류 시 한 번.

`group.instance.id`를 설정하면 이 동작이 달라진다.

```java
props.put(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, "order-consumer-instance-0");
props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, "60000");
```

같은 `group.instance.id`로 돌아온 컨슈머는 `session.timeout.ms` 안에 재합류하면 파티션 배정을 그대로 유지한다. 리밸런스 없이 이전 파티션으로 바로 fetch를 재개한다.

롤링 재시작으로 인스턴스가 10~30초 내에 재기동되는 환경에서 효과가 크다. `session.timeout.ms`를 60초로 설정하면 재시작 주기 안에 복귀가 완료되므로 배포 동안 리밸런스가 발생하지 않는다.

kafkajs는 `group.instance.id`를 공식 지원하지 않는다. Static Membership이 필요하다면 Java 클라이언트나 librdkafka 기반 클라이언트(node-rdkafka)를 검토해야 한다.

인스턴스 ID 관리 시 주의할 점: 같은 `group.instance.id`를 가진 인스턴스가 동시에 두 개 실행되면 Group Coordinator가 혼란을 겪는다. 쿠버네티스에서 StatefulSet 파드 이름을 그대로 쓰면 안전하지만, Deployment에서 파드가 교체될 때 이름이 바뀌는 경우가 있으므로 확인이 필요하다.

## 리밸런스 중 처리 중단 최소화

### max.poll.interval.ms 튜닝

`max.poll.interval.ms`는 `poll()` 호출 간격의 최대 허용 시간이다. 이 시간 안에 poll을 호출하지 않으면 Group Coordinator는 해당 컨슈머를 죽은 것으로 보고 리밸런스를 트리거한다.

기본값은 5분(300,000ms)이다. 처리 로직이 느릴 때 이 값을 무조건 늘리면 안 된다. 설정값을 올리면 실제로 죽은 컨슈머를 그룹에서 제거하는 시간도 같이 늘어나서 해당 파티션 처리 공백이 커진다.

처리 로직을 비동기로 분리하고 poll loop를 빠르게 유지하는 방향이 맞다.

```typescript
// 잘못된 패턴 — poll 루프 안에서 오래 걸리는 작업
await consumer.run({
  eachMessage: async ({ message }) => {
    await slowExternalApiCall(message) // 30초 걸리면 다음 poll이 30초 뒤
    await processMessage(message)
  }
})

// 긴 배치 처리 중에도 heartbeat를 명시적으로 유지하는 패턴
await consumer.run({
  eachBatch: async ({ batch, resolveOffset, heartbeat, commitOffsetsIfNecessary }) => {
    for (const message of batch.messages) {
      await processMessage(message)
      resolveOffset(message.offset)
      await heartbeat() // 각 메시지 처리 후 heartbeat
    }
    await commitOffsetsIfNecessary()
  }
})
```

`eachBatch`에서 `heartbeat()`를 명시적으로 호출하는 게 중요하다. `eachMessage`는 kafkajs가 자동으로 heartbeat를 관리하지만, `eachBatch`에서는 직접 호출해야 한다.

### poll loop 설계

메시지 처리 시간이 일정하지 않은 경우, 처리와 poll을 분리하는 구조가 안정적이다.

```typescript
import PQueue from 'p-queue'

const processingQueue = new PQueue({ concurrency: 5 })

await consumer.run({
  eachBatch: async ({ batch, resolveOffset, heartbeat }) => {
    const tasks = batch.messages.map((message) =>
      processingQueue.add(async () => {
        await processMessage(message)
        resolveOffset(message.offset)
      })
    )
    // 배치 내 모든 메시지가 큐에 들어가면 poll은 바로 다음 배치로 넘어감
    // heartbeat는 실제 처리 완료와 무관하게 계속 발생
    await heartbeat()
    await Promise.all(tasks)
  }
})
```

이 방식은 컨슈머가 비정상 종료할 때 큐에 쌓인 미완료 작업이 유실될 수 있다. offset 커밋 시점을 처리 완료 후로 명확히 맞춰야 한다.

### ConsumerRebalanceListener 활용 (Java)

리밸런스 발생 시 처리 중인 작업을 정리할 기회를 주는 콜백이다.

```java
consumer.subscribe(topics, new ConsumerRebalanceListener() {
    @Override
    public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
        // 파티션이 revoke되기 전 호출 — 처리 중인 메시지가 있으면 여기서 커밋
        consumer.commitSync(currentOffsets);
    }

    @Override
    public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
        // 새 파티션이 배정된 직후 호출 — 파티션별 초기화 작업이 필요하면 여기서
    }
});
```

`onPartitionsRevoked`에서 `commitSync`를 호출하면 파티션을 넘겨주기 전에 현재까지 처리한 offset을 커밋한다. 다음 컨슈머가 이어받을 때 중복 처리 범위가 줄어든다.

Cooperative Rebalance를 쓰는 경우엔 `onPartitionsRevoked` 대신 `onPartitionsLost`가 호출되는 경우가 있다. `onPartitionsRevoked`는 정상적인 revoke 시, `onPartitionsLost`는 세션 만료 등으로 파티션이 강제로 빼앗길 때 호출된다. 두 콜백 모두 처리해야 안전하다.

## 갑자기 리밸런스가 늘어날 때 진단

리밸런스가 예상보다 자주 발생하면 로그와 메트릭으로 원인을 좁혀야 한다.

### 브로커 로그 확인

Group Coordinator는 리밸런스 발생 시 사유를 로그에 남긴다. 브로커 로그에서 그룹 ID로 필터링한다.

```bash
grep "order-consumer-group" /var/log/kafka/server.log | grep -E "Rebalance|LeaveGroup|JoinGroup|heartbeat"
```

자주 보이는 패턴:

- `Member ... failed to respond to heartbeat request` — session timeout 초과. heartbeat 스레드가 막혔거나, JVM GC pause가 길거나, 컨슈머 프로세스가 과부하 상태
- `LeaveGroup ... reason: the consumer is being closed` — 정상 종료인데 자주 일어난다면 배포 주기가 짧거나 헬스체크 실패로 프로세스가 자주 재시작되는 것
- `Member ... has exceeded the maximum poll interval` — `max.poll.interval.ms` 초과. 처리 로직이 느리거나 poll loop가 블로킹되는 구간이 있음

### 컨슈머 메트릭 확인

JMX 또는 Prometheus exporter로 아래 메트릭을 확인한다.

```
kafka_consumer_rebalance_total             # 리밸런스 발생 횟수
kafka_consumer_last_rebalance_seconds      # 마지막 리밸런스로부터 경과 시간
kafka_consumer_rebalance_latency_avg       # 리밸런스 소요 시간
kafka_consumer_heartbeat_response_time_max # heartbeat 응답 지연
```

`rebalance_latency_avg`가 크면 리밸런스 자체가 오래 걸린다는 의미다. 컨슈머 수가 많거나 파티션이 많을 때 SyncGroup 단계에서 지연이 생기는 경우가 있다.

### GC pause 확인

JVM 기반 컨슈머라면 Full GC pause가 `session.timeout.ms`를 초과하면 heartbeat가 끊겨 리밸런스가 발생한다. GC 로그에서 pause 시간을 확인한다.

```
-Xlog:gc*:file=/var/log/app/gc.log:time,level,tags
```

`session.timeout.ms`를 기본값(10초)보다 길게 설정하거나, GC 튜닝으로 pause 시간을 줄이는 방향 중 하나를 선택한다. 두 방법을 동시에 쓰는 경우도 많다.

### 처리 시간 분포 확인

`max.poll.interval.ms` 초과가 원인이라면 메시지별 처리 시간을 측정해서 outlier를 찾는다.

```typescript
await consumer.run({
  eachMessage: async ({ message }) => {
    const start = Date.now()
    await processMessage(message)
    const elapsed = Date.now() - start
    if (elapsed > 10_000) {
      logger.warn({ elapsed, offset: message.offset, partition: message.partition },
        'slow message processing')
    }
  }
})
```

외부 API 타임아웃이 설정되지 않거나, DB 쿼리에 인덱스가 없거나, 특정 파티션의 메시지가 유독 큰 경우가 실제 현장에서 `max.poll.interval.ms` 초과를 만드는 원인으로 자주 나온다. slow 메시지의 offset과 partition을 기록해두면 어느 파티션에서 집중적으로 발생하는지 빠르게 파악할 수 있다.
