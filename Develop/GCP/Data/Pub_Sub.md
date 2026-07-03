---
title: "Cloud Pub/Sub"
tags: [GCP, Pub/Sub, Messaging, Queue, Ordering Key, Dead Letter]
updated: 2026-07-03
---

# Cloud Pub/Sub

GCP의 메시지 브로커다. 발행자(publisher)가 토픽에 메시지를 던지면, 그 토픽을 구독한 여러 구독(subscription)이 각자 사본을 받아간다. Kafka를 먼저 써봤다면 개념이 겹치는데, 파티션이라는 게 표면에 드러나지 않고 오프셋을 직접 관리하지 않는다는 점이 다르다. 스케일링과 저장은 GCP가 알아서 하고, 우리는 토픽과 구독만 만든다.

처음 쓸 때 가장 헷갈리는 게 토픽과 구독의 관계다. 메시지는 토픽에 저장되는 게 아니라 **구독마다 따로 쌓인다**. 토픽 하나에 구독 세 개가 붙어 있으면, 발행된 메시지 한 건이 세 개의 구독에 각각 복제되어 들어간다. 구독 A가 메시지를 ack해서 지워도 구독 B, C에는 그대로 남아 있다. 그래서 같은 이벤트를 서로 다른 서비스가 독립적으로 소비하게 만들려면 서비스마다 구독을 따로 파는 게 기본이다.

```mermaid
flowchart LR
    P[Publisher] -->|publish| T[Topic]
    T --> S1[Subscription A]
    T --> S2[Subscription B]
    T --> S3[Subscription C]
    S1 --> C1[주문 서비스]
    S2 --> C2[정산 서비스]
    S3 --> C3[알림 서비스]
```

## 토픽과 구독 모델

토픽은 메시지가 들어오는 입구고, 구독은 그 메시지를 빼가는 출구다. 하나의 토픽에 구독이 없으면 발행한 메시지는 그냥 버려진다. 구독이 생기기 전에 발행한 메시지는 그 구독에서 볼 수 없다. 이 순서 때문에 초기 세팅에서 "메시지를 보냈는데 구독자가 못 받는다"는 상황이 종종 나온다. 구독을 먼저 만들고 발행을 시작해야 한다.

구독에는 메시지 보관 기간이 있다. 기본 7일이고 최대 31일까지 늘릴 수 있다. 구독자가 이 기간 안에 ack하지 못한 메시지는 사라진다. 장애로 컨슈머가 며칠 죽어 있어도 이 기간 안에만 복구하면 밀린 메시지를 그대로 받는다. 반대로 보관 기간을 넘겨 죽어 있었다면 그 사이 메시지는 유실이다.

```bash
# 토픽 생성
gcloud pubsub topics create order-events

# 풀 구독 생성 (ack deadline 30초, 보관 7일)
gcloud pubsub subscriptions create order-worker \
  --topic=order-events \
  --ack-deadline=30 \
  --message-retention-duration=7d
```

## 푸시 vs 풀 구독

구독은 메시지를 가져가는 방식에 따라 풀(pull)과 푸시(push)로 나뉜다. 이 선택이 나중에 운영 난이도를 크게 가른다.

풀 구독은 구독자가 능동적으로 Pub/Sub에 "메시지 있냐"고 요청해서 받아온다. 컨슈머 애플리케이션이 클라이언트 라이브러리로 스트리밍 풀 연결을 열고 계속 당겨오는 구조다. 처리 속도를 컨슈머가 제어하고, 동시에 몇 개까지 붙들지도 조절할 수 있다. 백엔드 워커를 직접 돌린다면 대부분 풀이 맞다.

푸시 구독은 Pub/Sub가 지정한 HTTPS 엔드포인트로 메시지를 POST로 밀어 넣는다. 컨슈머는 그냥 웹 서버로 요청을 받고 200 OK를 돌려주면 그게 ack다. Cloud Run이나 Cloud Functions처럼 요청 기반으로 뜨는 서버리스와 궁합이 좋다. 상시 떠 있는 워커 없이 이벤트 올 때만 인스턴스가 뜨는 구조를 만들 수 있다.

| 구분 | 풀(Pull) | 푸시(Push) |
|------|---------|-----------|
| 흐름 제어 | 구독자가 당겨오는 만큼 | Pub/Sub가 미는 대로 |
| 처리량 조절 | 동시 처리 수를 직접 제어 | 엔드포인트 응답 속도에 따라 자동 조절 |
| 인프라 | 상시 워커 필요 | 서버리스 엔드포인트로 충분 |
| 재시도 | ack 안 하면 재전송 | non-200 응답 시 재전송 |
| 적합 | 대량 배치, 처리량 큰 워커 | 저빈도 이벤트, 서버리스 |

푸시에서 자주 당하는 건 엔드포인트가 느려질 때다. 푸시는 응답이 200으로 돌아와야 ack로 처리하는데, 엔드포인트 처리가 느리면 Pub/Sub가 동시 푸시 개수를 자동으로 줄인다(slow-start 비슷하게 흐름을 조인다). 반대로 엔드포인트가 빠르게 200을 돌려주면 밀어 넣는 속도를 올린다. 그래서 푸시 엔드포인트에서 무거운 동기 처리를 그대로 하면 처리량이 안 올라간다. 받자마자 큐에 적재하고 200을 먼저 돌려주는 식으로 짜야 하는 경우가 있는데, 그러면 처리 실패 시 재전송 보장이 깨지므로 그 트레이드오프를 알고 써야 한다.

## 메시지 순서 보장 (ordering key)

기본적으로 Pub/Sub는 순서를 보장하지 않는다. A를 먼저 보내고 B를 나중에 보내도 구독자가 B를 먼저 받을 수 있다. 여러 서버에 분산되어 처리되기 때문에 이건 결함이 아니라 설계다.

순서가 필요하면 발행할 때 ordering key를 지정하고, 구독에서 message ordering을 켠다. 같은 ordering key를 가진 메시지들끼리는 발행 순서대로 전달된다. 키가 다르면 서로 순서 보장이 없다. 보통 이 키를 엔티티 ID로 잡는다. 주문 ID를 키로 쓰면 같은 주문에 대한 이벤트는 순서대로 오고, 다른 주문끼리는 병렬로 처리된다.

```python
from google.cloud import pubsub_v1

# 순서 보장을 켜려면 publisher 옵션에 enable_message_ordering 필요
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True
    )
)
topic_path = publisher.topic_path("my-project", "order-events")

# 같은 ordering_key끼리 순서 보장
future = publisher.publish(
    topic_path,
    b'{"event": "created"}',
    ordering_key="order-12345",
)
future.result()
```

구독 쪽은 생성할 때 `--enable-message-ordering`을 줘야 한다. 발행만 키를 붙이고 구독에서 안 켜면 순서는 보장되지 않는다.

순서 보장을 켜면 대가가 있다. 같은 키의 메시지 하나가 처리에 실패해서 계속 재전송되면, 그 키의 뒤 메시지들이 앞의 것이 성공할 때까지 막힌다. 순서를 지키려니 앞의 것을 건너뛸 수 없어서다. 그래서 순서 보장 구독에서는 독성 메시지(poison message) 하나가 특정 키의 전체 흐름을 정지시키는 상황이 생긴다. 데드레터 토픽을 반드시 같이 걸어서, 몇 번 실패한 메시지는 옆으로 빼내야 흐름이 다시 흐른다. 그리고 순서 보장은 처리량을 떨어뜨리는 방향으로 작동하므로, 정말 순서가 필요한 토픽에만 켜는 게 맞다. 전 구간에 다 켜면 처리량이 이유 없이 깎인다.

## 중복 전달 (at-least-once)

Pub/Sub는 최소 1회 전달(at-least-once)을 보장한다. 정확히 1회가 아니다. 같은 메시지가 두 번 이상 올 수 있다는 뜻이고, 이건 예외 상황이 아니라 정상 동작 범위다. 네트워크 지연으로 ack가 제때 안 닿거나, ack deadline을 넘겨서 Pub/Sub가 "구독자가 못 받았나 보다" 판단하고 다시 보내는 경우가 대표적이다.

그래서 구독자는 **멱등하게(idempotent)** 짜야 한다. 같은 메시지를 두 번 처리해도 결과가 같아야 한다. 결제 승인처럼 두 번 실행되면 안 되는 작업이라면, 메시지에 붙는 `message_id`나 애플리케이션이 부여한 고유 키로 중복을 걸러낸다. 처리 이력 테이블에 키를 유니크 제약으로 걸고, 이미 있으면 스킵하는 방식이 흔하다.

```python
def callback(message):
    msg_id = message.message_id
    # 이미 처리한 메시지면 그냥 ack하고 넘어감
    if already_processed(msg_id):
        message.ack()
        return
    try:
        handle(message.data)
        mark_processed(msg_id)  # 처리 이력에 기록
        message.ack()
    except Exception:
        message.nack()  # 재전송 유도
```

정확히 1회에 가깝게 하고 싶으면 구독에 exactly-once delivery 옵션이 있다. 이걸 켜면 Pub/Sub가 ack된 메시지의 재전송을 억제한다. 다만 이건 단일 구독 안에서의 중복을 줄이는 것이지, 애플리케이션 레벨의 멱등성을 대체하지는 않는다. 여전히 멱등 처리를 기본으로 깔아두는 게 안전하다. exactly-once를 켜면 ack 처리 방식이 달라져서(ack가 성공했는지 응답을 받아야 함) 지연이 조금 늘고, 처리량도 영향을 받는다.

## 데드레터 토픽

몇 번을 재전송해도 계속 실패하는 메시지가 있다. 형식이 깨졌거나, 파싱이 안 되거나, 참조하는 데이터가 없어서 영원히 실패하는 것들이다. 이걸 그냥 두면 같은 메시지가 무한히 재전송되면서 워커 리소스를 계속 갉아먹고, 순서 보장 구독이라면 뒤 메시지까지 막는다.

데드레터 토픽(dead letter topic)은 일정 횟수 이상 전달 실패한 메시지를 별도 토픽으로 빼내는 장치다. 구독에 max delivery attempts를 설정하면, 그 횟수를 넘긴 메시지는 원래 구독에서 지워지고 지정한 데드레터 토픽으로 넘어간다. 거기에 다시 구독을 붙여서 실패 메시지를 따로 조사하거나, 수동으로 재처리한다.

```bash
# 데드레터용 토픽과 구독을 먼저 만들어 둠
gcloud pubsub topics create order-events-dlq
gcloud pubsub subscriptions create order-events-dlq-sub \
  --topic=order-events-dlq

# 원래 구독에 데드레터 정책 연결 (5회 실패 시 DLQ로)
gcloud pubsub subscriptions update order-worker \
  --dead-letter-topic=order-events-dlq \
  --max-delivery-attempts=5
```

여기서 놓치기 쉬운 게 권한이다. 데드레터로 메시지를 옮기는 주체는 우리 서비스가 아니라 Pub/Sub 서비스 계정이다. 이 서비스 계정에 원본 구독의 `subscriber` 권한과 데드레터 토픽의 `publisher` 권한을 둘 다 줘야 한다. 이 권한이 없으면 데드레터 정책을 걸어놨는데도 메시지가 DLQ로 안 넘어가고 계속 원래 구독에서 재전송된다. 설정은 됐는데 동작을 안 하는 것처럼 보이는 대부분의 경우가 이 권한 누락이다.

max delivery attempts 카운트는 정확한 값이 아니라 근사치라는 점도 알아둬야 한다. 5로 걸었다고 딱 5번 만에 넘어가는 게 아니라, 6~7번 시도된 뒤 넘어가기도 한다. DLQ로 넘어가는 시점을 카운트에 정밀하게 의존하는 로직은 짜지 않는 게 좋다.

## ack deadline 관리

구독자가 메시지를 받으면, 정해진 시간(ack deadline) 안에 ack를 보내야 한다. 이 시간을 넘기면 Pub/Sub는 그 메시지가 처리 안 됐다고 보고 다른(또는 같은) 구독자에게 다시 보낸다. 기본값은 10초, 최대 600초(10분)까지 설정할 수 있다.

이 값을 처리 시간에 맞게 잡는 게 중요하다. 메시지 하나 처리에 평균 20초 걸리는데 ack deadline을 10초로 두면, 아직 처리 중인 메시지를 Pub/Sub가 미처리로 판단해서 중복 전달한다. 워커는 멀쩡히 처리하고 있는데 같은 메시지가 계속 새로 들어오는 상황이 벌어진다. 처리 시간보다 넉넉하게 잡아야 한다.

처리 시간이 들쭉날쭉하면 고정 deadline으로는 맞추기 어렵다. 이럴 때 클라이언트 라이브러리의 ack deadline 자동 연장 기능을 쓴다. 라이브러리가 메시지를 붙들고 있는 동안 주기적으로 `modifyAckDeadline`을 호출해서 만료 시각을 미룬다. 파이썬/자바 공식 클라이언트는 이걸 기본으로 해주는데, 그래도 상한이 있다. 무한정 연장되는 게 아니라 max lease duration까지만 미룬다.

```python
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
sub_path = subscriber.subscription_path("my-project", "order-worker")

# flow control로 동시에 붙드는 메시지 수 제한
flow_control = pubsub_v1.types.FlowControl(max_messages=100)

streaming_pull = subscriber.subscribe(
    sub_path, callback=callback, flow_control=flow_control
)
```

deadline을 너무 길게 잡는 것도 문제다. 600초로 잡아뒀는데 워커가 그 메시지를 잡은 채로 죽으면, Pub/Sub는 600초가 지나야 죽은 걸 알고 다른 워커에 재전송한다. 그 사이 그 메시지는 10분 동안 아무도 처리 못 하는 상태로 붙들려 있다. deadline은 처리 시간보다는 넉넉하되 지나치게 길지 않게, 실제 처리 시간에 여유분을 더한 값으로 잡는 게 낫다.

## 처리 지연 시 재전송 폭주

운영에서 제일 아프게 겪는 문제다. 구독자 처리가 느려지거나 일부 워커가 죽으면, ack deadline을 넘기는 메시지가 늘고, Pub/Sub는 미처리 판단한 메시지를 재전송한다. 그런데 이미 워커는 밀린 상태다. 재전송으로 들어온 메시지가 처리 큐에 더 쌓이고, 그것들도 deadline을 넘겨 또 재전송되면서 부하가 눈덩이처럼 불어난다. 처리가 느려서 재전송이 늘고, 재전송이 늘어서 더 느려지는 악순환이다.

이게 시작되면 백로그(미처리 메시지 수)가 급증하는데, 실제 유입량은 그대로인데도 재전송분 때문에 처리해야 할 양이 몇 배로 부풀어 보인다. 모니터링에서 `num_undelivered_messages`가 유입 대비 이상하게 크면 이 상황을 의심한다.

대응은 몇 갈래다.

첫째, flow control로 워커가 한 번에 붙드는 메시지 수를 제한한다. 위 예제의 `max_messages`가 그것이다. 워커가 감당할 만큼만 당겨오면, 붙들었다가 deadline 넘겨 재전송되는 메시지가 줄어든다. 소화도 못 할 만큼 당겨놓고 deadline을 넘기는 게 폭주의 흔한 시작점이다.

둘째, ack deadline과 실제 처리 시간의 간격을 다시 본다. 처리가 느려진 원인이 일시적이라면 deadline을 처리 시간보다 확실히 크게 잡아 불필요한 재전송을 막는다. 자동 연장이 켜져 있는지도 확인한다.

셋째, 처리 자체를 스케일아웃한다. 풀 구독이면 워커 인스턴스를 늘려서 백로그를 빼낸다. Pub/Sub는 컨슈머 수에 맞춰 분산해주므로 워커를 늘리면 처리량이 대체로 선형에 가깝게 오른다. 다만 순서 보장 구독이라면 같은 키는 한 번에 한 곳에서만 처리되므로 무작정 늘려도 그 키의 처리 속도는 안 오른다.

넷째, 실패가 특정 메시지 때문이라면 데드레터 토픽으로 그 메시지를 빼낸다. 독성 메시지 하나가 재전송을 반복하며 부하를 만드는 경우, DLQ로 격리하면 흐름이 정상으로 돌아온다.

마지막으로, 유입 자체가 순간적으로 폭증한 거라면 워커를 늘리는 것과 별개로 다운스트림(DB 등)이 병목인지 본다. Pub/Sub는 메시지를 잘 밀어주는데 워커 뒤의 DB가 못 받아내서 처리가 느려지는 경우가 많다. 이때 Pub/Sub만 튜닝해봐야 소용이 없고, DB 커넥션 풀이나 배치 처리를 손봐야 한다.
