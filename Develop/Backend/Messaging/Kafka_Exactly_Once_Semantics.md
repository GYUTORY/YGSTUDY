---
title: Kafka Exactly-Once Semantics (EOS)
tags: [kafka, exactly-once, idempotent-producer, transactions, eos, kafka-streams, messaging]
updated: 2026-08-02
---

# Kafka Exactly-Once Semantics (EOS)

Kafka EOS는 두 개의 독립 기능이 합쳐진 결과다. 하나는 Idempotent Producer로 프로듀서 재시도로 인한 중복을 제거하는 것이고, 다른 하나는 트랜잭션 API로 읽기-처리-쓰기를 원자적으로 묶는 것이다. 이 둘을 이해하지 않고 `exactly-once`라는 단어만 믿으면, Kafka→DB 파이프라인에서 중복이 발생할 때 원인을 찾을 수 없다.

## Idempotent Producer: PID + sequence number

프로듀서가 `acks=all`로 메시지를 보내고 브로커로부터 응답을 받지 못하면 재시도한다. 브로커가 실제로는 메시지를 받아서 저장했는데 응답만 유실된 경우, 이 재시도는 중복이 된다.

Idempotent Producer는 각 프로듀서 인스턴스에 **PID(Producer ID)** 를 부여하고, 보내는 메시지마다 파티션별 **sequence number** 를 붙인다. 브로커는 `(PID, 파티션, sequence number)` 조합으로 이미 저장한 메시지인지 판단한다. 같은 조합이 오면 저장 대신 ack만 돌려보낸다.

```
Producer                    Broker (partition leader)
  |                              |
  |  msg(PID=42, seq=5, value=X) |
  | ---------------------------> |
  |                              | 저장 완료
  |                   <네트워크 유실>
  |  (timeout, retry)            |
  |  msg(PID=42, seq=5, value=X) |
  | ---------------------------> |
  |                              | seq=5 이미 있음 → ack만 반환
  |  ack                         |
  | <--------------------------- |
```

`enable.idempotence=true`를 켜면 자동으로 활성화된다. `acks=-1(all)`, `max.in.flight.requests.per.connection=5`도 자동 적용된다. 명시적으로 다른 값을 설정하면 충돌 오류가 난다.

```typescript
import { Kafka } from 'kafkajs'

const producer = kafka.producer({
  idempotent: true,
  // acks=-1, maxInFlightRequests=5가 자동 설정됨
})
```

Java 클라이언트:

```java
Properties props = new Properties();
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
// acks=-1, retries=Integer.MAX_VALUE, max.in.flight=5 자동 적용
```

PID는 브로커가 프로듀서 세션 단위로 발급한다. 프로듀서가 재시작하면 PID가 바뀐다. 같은 토픽에 이전과 같은 내용을 보내도 PID가 달라지기 때문에 중복으로 인식하지 않는다. Idempotent Producer가 막는 건 **같은 프로듀서 세션 내의 재시도 중복**이지, 애플리케이션 레벨에서 두 번 호출한 중복이 아니다.

sequence number는 파티션별로 따로 관리한다. 파티션 A에 seq=5를 보내고 파티션 B에도 seq=5를 보내는 건 각각 별개다.

### max.in.flight.requests.per.connection을 5로 놓는 이유

이전에는 idempotent producer를 쓰려면 이 값을 1로 제한해야 순서가 보장된다고 알려져 있었다. Kafka 1.0.0부터 5까지 허용하더라도 브로커가 sequence number로 순서를 보장한다. 5보다 크면 안 된다. in-flight가 6 이상인 상태에서 재시도가 발생하면 브로커가 sequence number 연속성을 보장할 수 없어서 `OutOfOrderSequenceException`이 발생한다.

## 트랜잭션 API

Idempotent Producer가 단일 프로듀서의 재시도 중복을 막는다면, 트랜잭션 API는 **여러 파티션에 대한 write와 컨슈머 offset commit을 원자적으로 묶는다**. "원자적으로"의 의미는 모두 성공하거나, 모두 없었던 일이 되거나 둘 중 하나라는 뜻이다.

### transactional.id

트랜잭션 프로듀서는 반드시 `transactional.id`를 설정해야 한다. 이 값은 브로커가 같은 논리적 프로듀서를 식별하는 기준이다. PID는 세션마다 새로 발급되지만, `transactional.id`는 재시작 후에도 동일하게 유지된다. 브로커는 이 값으로 좀비 프로듀서의 진행 중인 트랜잭션을 중단시킨다.

`transactional.id`는 파티션이나 컨슈머 그룹처럼 **인스턴스별로 고유해야 한다**. 같은 id를 여러 프로듀서 인스턴스가 동시에 쓰면 그 중 하나는 `ProducerFencedException`이 발생한다.

### initTransactions / beginTransaction / commitTransaction / abortTransaction

`initTransactions()`는 프로듀서를 트랜잭션 모드로 등록하고, 이전에 완료되지 않은 트랜잭션이 있으면 정리한다. 프로듀서 인스턴스 생명주기에서 한 번만 호출한다. 재시작 후 다시 호출하면 브로커가 이전 PID를 무효화하고 새 PID를 발급한다. 이전 PID로 진행 중이던 트랜잭션은 abort로 처리된다.

```java
producer.initTransactions();  // 시작 시 한 번

try {
    producer.beginTransaction();

    // 여러 파티션에 메시지 전송
    producer.send(new ProducerRecord<>("orders", orderId, orderData));
    producer.send(new ProducerRecord<>("audit-log", orderId, auditData));

    // 컨슈머 offset도 트랜잭션에 포함
    producer.sendOffsetsToTransaction(
        Map.of(
            new TopicPartition("input-topic", 0),
            new OffsetAndMetadata(offset + 1)
        ),
        new ConsumerGroupMetadata("order-consumer-group")
    );

    producer.commitTransaction();
} catch (ProducerFencedException e) {
    // 좀비 프로듀서 상태. 복구 불가, 인스턴스 종료해야 함
    throw e;
} catch (KafkaException e) {
    producer.abortTransaction();
    // 재처리 로직 또는 상위로 예외 전파
}
```

kafkajs는 `transaction()` 메서드로 begin/commit/abort를 묶어서 처리한다.

```typescript
import { Kafka } from 'kafkajs'

const producer = kafka.producer({
  transactionalId: 'order-processor-0',
  idempotent: true,
  maxInFlightRequests: 1,  // kafkajs 트랜잭션은 in-flight 1 권장
})

await producer.connect()

const transaction = await producer.transaction()

try {
  await transaction.send({
    topic: 'orders',
    messages: [{ key: orderId, value: JSON.stringify(orderData) }],
  })

  await transaction.sendOffsets({
    consumerGroupId: 'order-consumer-group',
    topics: [{
      topic: 'input-topic',
      partitions: [{ partition: 0, offset: String(nextOffset) }],
    }],
  })

  await transaction.commit()
} catch (err) {
  await transaction.abort()
  throw err
}
```

### sendOffsetsToTransaction

컨슈머 offset을 커밋하는 작업을 트랜잭션 안에 넣는 메서드다. 메시지 처리와 offset 커밋이 원자적이 된다.

트랜잭션이 abort되면 offset 커밋도 없었던 일이 된다. 컨슈머는 이전 offset에서 다시 읽는다. 트랜잭션이 commit되면 offset이 저장된다.

이 동작을 위해 컨슈머 쪽에서도 `isolation.level` 설정이 필요하다.

```java
props.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
// 기본값은 read_uncommitted — 아직 commit되지 않은 트랜잭션 메시지도 읽음
```

`read_committed`로 설정한 컨슈머는 abort된 트랜잭션의 메시지를 건너뛴다. `read_uncommitted` 상태에서는 나중에 abort될 메시지도 읽어서 처리해버릴 수 있다.

## Kafka Streams EOS

Kafka Streams는 `Kafka → 처리 → Kafka` 파이프라인을 하나의 단위로 운영할 때 쓰는 스트리밍 라이브러리다. EOS 설정 하나로 읽기-처리-쓰기 전체를 트랜잭션으로 묶는다.

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "order-processor");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka:9092");
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);
// Kafka 2.6 이상. 이전에는 EXACTLY_ONCE (deprecated)
```

`exactly_once_v2`는 Kafka 2.5에서 도입된 두 번째 버전이다(KIP-447). 기존 `exactly_once`는 컨슈머 그룹 코디네이터와 트랜잭션 코디네이터 사이에 추가 통신이 필요했는데, v2에서는 불필요한 round-trip을 제거했다.

Kafka Streams가 내부적으로 하는 일:

- task별 프로듀서를 만들고 `transactional.id`를 `{applicationId}-{taskId}` 형태로 자동 생성한다
- 처리 interval마다 `commitTransaction` → `beginTransaction`을 반복한다
- 컨슈머 offset을 `sendOffsetsToTransaction`으로 같은 트랜잭션 안에 포함시킨다

Kafka Streams로 파이프라인을 구성하면 EOS 설정만으로 상당한 중복 처리 문제가 사라진다. 단, 처리 로직 안에서 외부 API를 호출하거나 DB에 쓰는 부분은 Kafka EOS 범위 밖이다.

`exactly_once` vs `exactly_once_v2` 선택: 브로커와 클라이언트가 모두 Kafka 2.5 이상이면 v2를 쓴다. 그 미만이면 `exactly_once`(deprecated)를 쓰는 수밖에 없다.

## Kafka→DB 쓰기가 EOS 범위 밖인 이유

Kafka 트랜잭션은 Kafka 내부에서만 성립한다. DB 쓰기는 별도의 트랜잭션 시스템이다. 두 시스템을 하나의 트랜잭션으로 묶으려면 2PC(Two-Phase Commit)가 필요하다. Kafka는 2PC를 지원하지 않는다.

실제로 어떤 일이 벌어지는지 보면 이해가 빠르다.

```
시나리오 1 — DB 성공, Kafka offset 실패:
  컨슈머가 메시지 읽음
  → DB INSERT 실행 후 commit 성공
  → Kafka offset commit 실패 (네트워크 오류)
  → 컨슈머 재시작
  → 같은 메시지를 다시 읽음
  → DB에 같은 INSERT 다시 실행 → 중복

시나리오 2 — DB 실패, Kafka offset 이미 커밋:
  컨슈머가 메시지 읽음
  → Kafka offset commit 성공
  → DB INSERT 실행 중 크래시
  → 컨슈머 재시작
  → offset이 앞으로 가 있어서 해당 메시지 영구 유실
```

DB commit과 Kafka commit 사이의 창이 존재하는 한 중복이나 유실 중 하나가 가능성으로 남는다. Kafka 트랜잭션을 켜도 이 창은 없어지지 않는다.

## at-least-once + 멱등으로 수렴하는 이유

브로커 수준의 exactly-once를 달성하더라도, 파이프라인 끝단에 Kafka 바깥의 시스템이 있는 한 at-least-once로 돌아온다. 선택지는 두 가지다.

**DB 쓰기에 멱등 처리 추가**: `INSERT ... ON CONFLICT DO NOTHING`처럼 같은 메시지가 두 번 들어와도 결과가 같게 만든다.

**Transactional Outbox**: DB와 메시지 발행을 같은 DB 트랜잭션 안에서 처리한다. 메시지는 Outbox 테이블에 먼저 저장하고, CDC나 폴링으로 Kafka로 발행한다.

실무에서는 대부분 전자로 해결한다. 로직이 단순하고 추가 인프라가 없어도 된다.

```java
@Transactional
public void handle(OrderEvent event) {
    jdbcTemplate.update(
        "INSERT INTO processed_orders(event_id, order_id, status) " +
        "VALUES (?, ?, ?) ON CONFLICT (event_id) DO NOTHING",
        event.getEventId(), event.getOrderId(), event.getStatus()
    );
    // ON CONFLICT DO NOTHING — 같은 event_id가 두 번 들어와도 두 번째는 insert 안 됨
}
```

`event_id`에 unique constraint를 걸어두면 컨슈머 로직 자체가 멱등해진다. Kafka EOS 설정 유무와 관계없이 중복 처리가 막힌다.

## transactional.id 관리

### 파티션 수에 맞춘 인스턴스 관리

트랜잭션 프로듀서를 직접 사용하는 경우(Kafka Streams 미사용), `transactional.id`를 인스턴스별로 고유하게 배정해야 한다. 일반적인 패턴은 파티션 번호를 suffix로 붙이는 방식이다.

```
transactional.id = {서비스명}-{파티션번호}
예: order-processor-0, order-processor-1, order-processor-2
```

컨슈머 인스턴스가 특정 파티션을 담당하고, 그 파티션에 대응하는 `transactional.id`를 쓴다. 리밸런스로 파티션 소유권이 바뀌면 `transactional.id`도 함께 이동해야 한다. 이 매핑을 직접 관리하는 게 복잡하면 Kafka Streams를 쓰는 게 낫다. Streams는 이 매핑을 자동으로 처리한다.

### 좀비 프로듀서 방어

`transactional.id`의 핵심 역할 중 하나가 좀비 프로듀서 방어다. 좀비 프로듀서는 네트워크 파티션이나 GC pause 등으로 죽었다고 간주되었지만 실제로는 살아있는 프로듀서 인스턴스다.

브로커는 `transactional.id`별로 **epoch** 값을 관리한다. 새 프로듀서가 같은 `transactional.id`로 `initTransactions()`를 호출하면 epoch가 1 증가한다. 이전 epoch의 프로듀서가 트랜잭션을 계속 진행하려 하면 브로커가 거부한다.

```
Instance A (epoch=1, 좀비):
  beginTransaction() 진행 중
  
Instance B (epoch=2, 새 인스턴스):
  initTransactions() → epoch를 2로 증가
  beginTransaction() 정상 진행
  
Instance A가 계속 메시지를 보내려 하면:
  → 브로커: epoch 불일치 → ProducerFencedException 발생
  → Instance A의 트랜잭션 무효화
```

`ProducerFencedException`을 받은 인스턴스는 복구가 불가능하다. 해당 프로듀서 인스턴스를 종료하고 새로 시작해야 한다. 이 예외를 잡아서 재시도하거나 무시하면 안 된다.

```java
try {
    producer.beginTransaction();
    // ... 처리 ...
    producer.commitTransaction();
} catch (ProducerFencedException e) {
    // 복구 불가 — 인스턴스를 종료하고 재시작
    log.error("Producer fenced. Shutting down.", e);
    System.exit(1);
} catch (KafkaException e) {
    try {
        producer.abortTransaction();
    } catch (KafkaException abortEx) {
        log.error("Failed to abort transaction", abortEx);
    }
    // 재처리 로직 또는 상위로 예외 전파
}
```

epoch는 브로커에서 증가만 하고 줄지 않는다. `initTransactions()` 호출이 잦으면 epoch가 빠르게 올라간다. 배포마다 새 프로듀서를 만들지 않고 프로세스 내에서 재사용하는 설계가 맞다.

## EOS를 써야 하는 경우

파이프라인이 `Kafka → 처리 → Kafka` 형태이고, 처리 결과가 다시 Kafka 토픽으로 가는 경우에 EOS가 의미 있다. 이벤트 집계, 스트림 조인, 토픽 간 데이터 변환이 여기에 해당한다.

`Kafka → DB`, `Kafka → 외부 API` 형태라면 EOS를 켜도 외부 시스템 쪽에서 중복이 발생한다. 이 경우에는 at-least-once로 두고 DB 멱등 처리 또는 API 멱등 키를 쓰는 게 현실적이다.

EOS를 켜면 처리량이 떨어진다. 트랜잭션 코디네이터와 추가 통신이 발생하고, `read_committed` 컨슈머는 트랜잭션이 닫힐 때까지 메시지를 읽지 않아서 지연이 생긴다. 지연 시간 요구사항이 엄격한 파이프라인에서는 트레이드오프를 검토해야 한다.

---
이 문서는 [메시징과 전달 보장 허브](../../_hub/메시징과_전달_보장.md)의 일부입니다.
