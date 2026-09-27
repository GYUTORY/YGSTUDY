---
title: 컨슈머 배압과 전달 보장 붕괴
tags: [backend, messaging, architecture, observability, performance, aws, kubernetes]
updated: 2026-09-27
---

# 컨슈머 배압과 전달 보장 붕괴

배압(backpressure)은 컨슈머가 브로커가 밀어주는 속도를 따라가지 못할 때 생긴다. 브로커 설정을 아무리 잘 잡아도 컨슈머 처리 한계에 닿는 순간 전달 보장이 무너지기 시작한다.

at-least-once를 쓰고 있다면 "한 번 이상 전달"이 "무한정 재전달"로 변한다. exactly-once라고 생각했다면 사실 at-least-once에 멱등 처리를 얹은 구조일 텐데, 컨슈머가 처리를 완료하지 못한 채 타임아웃으로 이탈하면 그 멱등 레이어도 의미가 없어진다.

---

## Kafka: lag 폭증의 구조

Kafka lag는 "아직 처리하지 못한 메시지 수"다. lag = (파티션 최신 오프셋) - (컨슈머 커밋 오프셋). lag가 폭증한다는 건 프로듀서가 넣는 속도보다 컨슈머가 처리하는 속도가 느리다는 뜻이다.

문제는 lag 자체가 아니다. lag가 폭증할 때 컨슈머가 리밸런싱까지 겪으면 진행했던 작업이 전부 취소되고 다른 컨슈머가 같은 메시지를 다시 가져간다. 이때 두 가지가 동시에 일어난다.

1. `max.poll.interval.ms` 초과로 컨슈머가 그룹에서 떠난다
2. 떠난 컨슈머가 처리 중이던 메시지는 커밋이 안 됐으므로 다음 컨슈머가 같은 메시지를 받는다

`max.poll.interval.ms` 기본값은 5분이다. 컨슈머가 `poll()`을 5분 안에 다시 호출하지 않으면 브로커는 그 컨슈머가 죽었다고 판단하고 리밸런싱을 시작한다.

배치로 메시지를 DB에 넣거나 외부 API를 호출하는 경우, 메시지 수가 많으면 5분 안에 다음 `poll()`까지 못 돌아오는 상황이 발생한다.

### max.poll.records 조정

`max.poll.records`는 `poll()` 한 번에 가져올 메시지 수다. 기본값 500이다.

```java
props.put("max.poll.records", 50);
```

이 값을 줄이면 배치 크기가 작아져서 처리 시간이 짧아진다. 대신 처리량(throughput)도 줄어든다. 메시지 하나 처리에 100ms가 걸린다면 500개 배치는 50초다. `max.poll.interval.ms`가 5분이라면 여유가 있어 보이지만 GC 멈춤, 외부 API 응답 지연, DB 슬로우 쿼리가 겹치면 바로 초과한다.

실무 기준으로 `max.poll.records`는 "(max.poll.interval.ms × 0.7) / 메시지 하나 처리 시간 p99"로 산정한다. p99를 쓰는 건 평균으로 잡으면 느린 케이스에서 초과가 나기 때문이다.

```
메시지 처리 p99 = 800ms
max.poll.interval.ms = 300,000ms (5분)
안전 여유 70% 적용 → 300,000 × 0.7 = 210,000ms
max.poll.records = 210,000 / 800 ≈ 262 → 200으로 내림
```

### max.poll.interval.ms 조정

처리 시간이 길 수밖에 없는 작업(동영상 인코딩, 대용량 파일 처리 등)이라면 `max.poll.interval.ms`를 늘리는 쪽이 맞다.

```java
props.put("max.poll.interval.ms", 1800000); // 30분
props.put("max.poll.records", 1);           // 메시지 하나씩
```

단, 이 경우 컨슈머 장애 감지가 30분 지연된다는 트레이드오프가 있다. 컨슈머가 죽어도 30분 뒤에야 리밸런싱이 시작된다.

긴 작업에는 메시지를 `poll()`로 받은 뒤 별도 스레드로 처리를 위임하고, 메인 스레드는 `pause()` + `poll(keepAlive)` 패턴으로 하트비트를 유지하는 방법을 쓰기도 한다. Kafka Consumer의 `pause()`와 `resume()`은 파티션 단위로 동작하므로 처리 중인 파티션만 일시 정지해 브로커와 연결을 유지할 수 있다.

```java
// 처리 시작 시
consumer.pause(partitions);

// 처리 중 하트비트 유지 (빈 poll)
while (!done) {
    consumer.poll(Duration.ofMillis(100));
    Thread.sleep(100);
}

// 처리 완료 후
consumer.commitSync(offsets);
consumer.resume(partitions);
```

---

## RabbitMQ: prefetch_count 산정

RabbitMQ는 push 기반이라 브로커가 컨슈머로 메시지를 밀어넣는다. prefetch_count 없이 컨슈머를 연결하면 브로커가 큐에 있는 메시지를 전부 컨슈머의 TCP 버퍼로 밀어버린다. 컨슈머가 죽으면 TCP 버퍼에 있던 메시지는 모두 재큐잉된다.

prefetch_count는 "ack 없이 컨슈머가 들고 있을 수 있는 최대 메시지 수"다.

```python
channel.basic_qos(prefetch_count=10)
```

값이 너무 작으면 컨슈머가 처리 완료 → ack → 다음 메시지 대기 → 브로커 왕복 지연이 생겨 처리량이 떨어진다. 값이 너무 크면 컨슈머 하나가 메시지를 독점해서 다른 컨슈머가 놀게 된다.

### 산정 방법

기본 공식은 `prefetch_count = (처리 지연 시간 / 메시지 처리 시간) × 안전 계수`다.

네트워크 왕복이 5ms이고 메시지 처리가 20ms라면 prefetch가 1이면 컨슈머가 25%만 일하고 75%는 대기한다. prefetch를 4 이상으로 잡아야 컨슈머가 쉬지 않고 메시지를 처리한다.

실제로는 컨슈머 수와 큐 깊이를 같이 본다. 컨슈머 10개에 prefetch 100이면 브로커가 순간적으로 1,000개 메시지를 컨슈머에 분산시킨다. 처리 중 컨슈머 하나가 OOM으로 죽으면 그 컨슈머의 100개가 한꺼번에 재큐잉된다.

배압 관점에서 prefetch_count는 "컨슈머 하나의 in-flight 메시지 허용량"이기도 하다. 메모리 사용량이 올라간다면 prefetch를 낮춰 in-flight를 제한하는 게 첫 번째 조치다.

컨슈머 하나당 적정 prefetch는 테스트로 찾는 수밖에 없다. 처리 시간이 균일한 작업이라면 10~50이 흔한 범위다. 처리 시간 편차가 크거나(DB 조회가 있거나 외부 API가 섞이면 p50과 p99가 10배 이상 차이 나기도 한다) 메시지 처리 자체가 메모리를 많이 쓴다면 5 이하로 잡아야 할 수도 있다.

---

## SQS: visibility timeout과 처리 시간 불일치

SQS는 ack 개념이 없다. 컨슈머가 메시지를 받으면 그 메시지는 visibility timeout 동안 다른 컨슈머에게 보이지 않는다. 처리가 끝나면 `DeleteMessage`를 호출해 큐에서 지운다. 처리가 `visibility timeout` 안에 끝나지 않으면 메시지가 다시 큐에 보이게 되고, 다른 컨슈머가 같은 메시지를 받는다.

visibility timeout 기본값은 30초다. 처리가 30초를 넘기면 같은 메시지가 두 번 처리된다. at-least-once가 발생하는 가장 흔한 원인이다.

```python
# 메시지를 받고
response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=10,
    VisibilityTimeout=300  # 5분
)

# 처리하다가 오래 걸릴 것 같으면
sqs.change_message_visibility(
    QueueUrl=queue_url,
    ReceiptHandle=receipt_handle,
    VisibilityTimeout=300  # 연장
)
```

처리 시간이 가변적인 작업에서는 처리 중에 주기적으로 `ChangeMessageVisibility`를 호출해 타임아웃을 연장한다. 이 연장 호출을 별도 스레드에서 처리 시간의 40% 간격으로 호출하는 패턴을 쓴다.

visibility timeout이 30초고 처리 p99가 25초라면 처리가 완료되더라도 여유가 5초밖에 없다. 이 상태에서 네트워크 지연이나 GC 멈춤이 5초를 넘기면 중복 처리가 발생한다. visibility timeout은 처리 p99의 3배 이상으로 잡아야 안전하다.

SQS에서 또 자주 발생하는 상황은 `MaxReceiveCount` 도달이다. 메시지가 처리 실패 + 재표시(visibility timeout 초과)를 반복하다 `MaxReceiveCount`(기본 1~1,000, 설정에 따라 다름)에 도달하면 DLQ로 이동한다. 이 경우 메시지가 실제로 처리하기 너무 오래 걸려서 visibility timeout을 계속 초과한 건지, 처리 자체가 실패한 건지 구분해야 한다. CloudWatch의 `NumberOfMessagesNotVisible` 메트릭이 높다면 전자다.

---

## 배압 감지 메트릭

세 브로커 공통으로 다음 세 가지 메트릭을 본다.

**Consumer lag**: Kafka는 `kafka_consumer_group_lag`, RabbitMQ는 `rabbitmq_queue_messages_ready`, SQS는 `ApproximateNumberOfMessagesNotVisible + ApproximateNumberOfMessagesVisible`. lag가 선형으로 늘어나면 처리량이 부족한 것이고, 계단식으로 늘어나면 주기적인 처리 실패가 있는 것이다. 계단 모양을 주의해야 한다 — 처리는 되고 있어서 늦게 눈치채기 쉽다.

**DLQ 증가율**: DLQ 메시지가 생기기 시작하면 컨슈머가 처리를 포기하고 있다는 뜻이다. lag 증가보다 더 심각한 신호다. lag는 "느리다"는 신호고 DLQ 증가는 "처리 불가 메시지가 생겼다"는 신호다. DLQ 증가율이 0이 아니면 즉시 알림을 받아야 한다.

**in-flight 메시지 수**: Kafka의 경우 `kafka_consumer_fetch_manager_records_lag_max`와 현재 처리 중인 메시지 수를 비교한다. RabbitMQ는 `rabbitmq_queue_messages_unacknowledged`. SQS는 `ApproximateNumberOfMessagesNotVisible`. in-flight가 prefetch_count(RabbitMQ) 또는 설정한 배치 크기(Kafka)에 근접하면 컨슈머가 포화 상태다.

---

## 자동 스케일아웃 트리거 설계

배압 메트릭을 기반으로 컨슈머를 자동으로 늘리는 건 Kubernetes HPA나 KEDA로 구현한다.

KEDA는 Kafka lag, RabbitMQ 큐 깊이, SQS 큐 길이를 직접 메트릭 소스로 지원한다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-consumer-scaler
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka:9092
        consumerGroup: order-group
        topic: orders
        lagThreshold: "1000"        # 파티션당 lag
        offsetResetPolicy: latest
```

`lagThreshold`는 "파티션 하나당 lag가 이 값을 넘으면 스케일아웃"이다. 파티션 수가 12개고 lagThreshold가 1,000이면 총 lag 12,000부터 스케일아웃한다.

스케일아웃 트리거를 너무 민감하게 잡으면 lag 스파이크마다 파드가 생성·삭제를 반복한다. Kafka는 컨슈머가 새로 붙을 때마다 리밸런싱이 발생한다. 리밸런싱 자체가 처리를 멈추는 이벤트라서 스케일아웃이 오히려 처리를 더 느리게 만들 수 있다.

이를 피하려면 scaledown을 늦게 한다.

```yaml
spec:
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300  # 5분간 lag가 안정돼야 줄인다
          policies:
            - type: Percent
              value: 25                    # 한 번에 25%씩만 줄인다
            - periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 30   # 올릴 때는 빠르게
```

RabbitMQ 기반이라면 메시지 수가 줄어드는 게 빠르므로 scaleDown stabilization을 짧게 잡아도 된다. Kafka는 lag가 줄었더라도 프로듀서 트래픽이 다시 오를 수 있으니 5분은 유지한다.

SQS는 `ApproximateNumberOfMessagesVisible`을 KEDA trigger로 쓴다.

```yaml
triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.ap-northeast-2.amazonaws.com/123456789/orders
      targetQueueLength: "50"   # 컨슈머 하나당 허용 메시지 수
      awsRegion: ap-northeast-2
```

스케일아웃이 실제로 배압을 해소하는지 확인하는 지표는 **lag 감소 속도**다. 파드를 2배 늘렸는데 lag 감소 속도가 2배가 되지 않는다면 병목이 컨슈머 수가 아니라 다른 곳(DB 커넥션 풀, 외부 API rate limit)에 있다는 뜻이다. 스케일아웃 이후 lag 감소율을 항상 모니터링해야 한다.

처리가 DB 집약적인 경우 컨슈머를 늘리면 오히려 DB 커넥션이 고갈돼 처리 속도가 더 내려가는 상황도 있다. 스케일아웃 전에 컨슈머 하나의 처리량 상한이 어디서 막히는지 파악하는 게 먼저다.
