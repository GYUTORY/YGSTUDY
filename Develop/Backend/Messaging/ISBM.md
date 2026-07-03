---
title: ISBM (Integration Services for Business Messaging)
tags: [backend, messaging, isbm, oasis, pub-sub, b2b, ws-notification, rest-api]
updated: 2026-04-06
---

# ISBM (Integration Services for Business Messaging)

## 개요

ISBM은 OASIS에서 정의한 B2B 메시지 통합 표준이다. 시스템 간 메시지를 주고받을 때 공통 인터페이스를 제공해서, 내부 메시징 시스템이 뭐든 상관없이 동일한 방식으로 연동할 수 있게 한다.

쉽게 말하면, A 회사가 RabbitMQ를 쓰고 B 회사가 Kafka를 쓰더라도, 둘 다 ISBM 인터페이스를 통해 메시지를 주고받으면 서로의 내부 구현을 몰라도 된다.

### 배경

기업 간 시스템 통합에서 반복되는 문제가 있다.

```
A사: RabbitMQ + 자체 프로토콜
B사: ActiveMQ + SOAP 기반 연동
C사: IBM MQ + 독자 포맷

→ 세 회사가 서로 데이터를 주고받으려면?
→ 각각 별도 어댑터 개발 (3 x 2 = 6개)
→ 새로운 회사가 추가되면 어댑터 수가 기하급수적으로 증가
```

ISBM은 이 문제를 표준 인터페이스 하나로 해결한다. 각 시스템이 ISBM 어댑터만 구현하면, 다른 시스템과 바로 통신할 수 있다.

### WS-Notification 기반

ISBM의 Pub/Sub 모델은 WS-Notification 표준을 기반으로 한다. WS-Notification이 SOAP/XML 기반이라 무겁다는 문제가 있었는데, ISBM 2.0부터는 RESTful API도 지원한다.

```
WS-Notification 구조:
  NotificationProducer  →  NotificationBroker  →  NotificationConsumer
       (발행자)              (중개자/ISBM)            (구독자)

ISBM이 NotificationBroker 역할을 수행한다.
```

## 핵심 개념

### Channel

메시지가 흐르는 논리적 통로다. RabbitMQ의 Exchange나 Kafka의 Topic과 비슷한 개념이지만, ISBM에서는 Channel 자체에 타입이 있다.

| Channel 타입 | 설명 | 메시지 흐름 |
|-------------|------|------------|
| Publication | Pub/Sub용 | 1:N (하나의 메시지를 여러 구독자가 수신) |
| Request | Request/Response용 | 요청자 → 제공자 → 응답 |

Channel은 URI로 식별한다. 보통 비즈니스 도메인 기반으로 이름을 정한다.

```
/channels/order-events
/channels/inventory-sync
/channels/invoice-exchange
```

### Session

Channel에 연결하려면 Session을 열어야 한다. Session은 발행자/구독자가 Channel과 맺는 연결 상태를 나타낸다.

```
                 ┌── Publication Session (발행용)
Channel ────────┤
                 └── Subscription Session (구독용)
```

Session에는 ID가 부여되고, 이후 모든 메시지 발행/구독은 이 Session ID를 통해 이루어진다. 세션을 열지 않고 메시지를 보내거나 받을 수 없다.

**세션의 생명주기:**

1. Channel 생성 (또는 기존 Channel 사용)
2. Session 열기 (Publication 또는 Subscription)
3. 메시지 발행/구독
4. Session 닫기

### Message

ISBM 메시지는 다음 요소로 구성된다.

| 필드 | 설명 |
|------|------|
| MessageID | 메시지 고유 식별자 |
| MessageContent | 실제 페이로드 (XML, JSON 등) |
| Topic | 메시지 분류용 토픽 (Pub/Sub에서 필터링에 사용) |
| Expiry | 메시지 만료 시간 (선택) |

Kafka와 다른 점은, ISBM에서 구독자가 메시지를 읽어도 큐에서 바로 사라지지 않는다. 명시적으로 `RemovePublication`을 호출해야 해당 구독자의 큐에서 제거된다.

## REST API 기반 메시지 흐름

ISBM 2.0은 RESTful API를 제공한다. 실제 연동 시 흐름을 순서대로 정리한다.

### Pub/Sub 흐름

```
1. 채널 생성
   POST /channels
   { "uri": "/order-events", "type": "Publication" }

2. 발행 세션 열기
   POST /channels/{channel-uri}/publication-sessions

3. 구독 세션 열기 (다른 시스템에서)
   POST /channels/{channel-uri}/subscription-sessions
   { "topics": ["order.created", "order.updated"] }

4. 메시지 발행
   POST /sessions/{session-id}/publications
   { "topics": ["order.created"], "messageContent": { ... } }

5. 메시지 읽기
   GET /sessions/{session-id}/publication

6. 메시지 제거 (읽은 후)
   DELETE /sessions/{session-id}/publication/{message-id}
```

### Request/Response 흐름

```
1. Request 채널 생성
   POST /channels
   { "uri": "/price-inquiry", "type": "Request" }

2. 제공자 세션 열기
   POST /channels/{channel-uri}/provider-sessions

3. 요청자 세션 열기
   POST /channels/{channel-uri}/consumer-sessions

4. 요청 메시지 발행
   POST /sessions/{consumer-session-id}/requests
   { "topics": ["price.query"], "messageContent": { "sku": "ABC-123" } }

5. 제공자가 요청 읽기
   GET /sessions/{provider-session-id}/request

6. 응답 발행
   POST /sessions/{provider-session-id}/responses/{request-message-id}
   { "messageContent": { "sku": "ABC-123", "price": 15000 } }

7. 요청자가 응답 읽기
   GET /sessions/{consumer-session-id}/responses/{request-message-id}
```

## 코드 예제

Python으로 ISBM REST API를 호출하는 예제다. 실제 ISBM 서버(OpenO&M 등)가 필요하다.

### 채널 생성 및 세션 열기

```python
import requests
import json

ISBM_BASE_URL = "http://isbm-server:8080/api/v2"

class ISBMClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}

    def create_channel(self, uri, channel_type="Publication"):
        """채널 생성. 이미 존재하면 409 에러가 발생한다."""
        resp = requests.post(
            f"{self.base_url}/channels",
            headers=self.headers,
            json={"uri": uri, "type": channel_type}
        )
        if resp.status_code == 201:
            return resp.json()
        elif resp.status_code == 409:
            # 이미 존재하는 채널 — 그대로 사용하면 된다
            return {"uri": uri, "existed": True}
        else:
            raise Exception(f"채널 생성 실패: {resp.status_code} {resp.text}")

    def open_publication_session(self, channel_uri):
        """발행 세션 열기"""
        resp = requests.post(
            f"{self.base_url}/channels/{channel_uri}/publication-sessions",
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()["sessionId"]

    def open_subscription_session(self, channel_uri, topics):
        """구독 세션 열기. topics로 관심 있는 메시지만 필터링한다."""
        resp = requests.post(
            f"{self.base_url}/channels/{channel_uri}/subscription-sessions",
            headers=self.headers,
            json={"topics": topics}
        )
        resp.raise_for_status()
        return resp.json()["sessionId"]
```

### 메시지 발행

```python
def publish_message(self, session_id, topics, content, expiry=None):
    """
    메시지 발행.
    expiry를 설정하지 않으면 메시지가 영구 보관되므로,
    반드시 적절한 만료 시간을 설정해야 한다.
    """
    payload = {
        "topics": topics,
        "messageContent": content
    }
    if expiry:
        payload["expiry"] = expiry  # ISO 8601 duration, 예: "PT1H" (1시간)

    resp = requests.post(
        f"{self.base_url}/sessions/{session_id}/publications",
        headers=self.headers,
        json=payload
    )
    resp.raise_for_status()
    return resp.json()["messageId"]
```

### 메시지 구독 (Polling)

```python
import time

def poll_messages(self, session_id, interval=5, max_retries=100):
    """
    ISBM은 WebSocket을 지원하지 않는다.
    구독자는 주기적으로 polling 해서 메시지를 가져와야 한다.
    """
    retry_count = 0
    while retry_count < max_retries:
        resp = requests.get(
            f"{self.base_url}/sessions/{session_id}/publication",
            headers=self.headers
        )

        if resp.status_code == 200:
            message = resp.json()
            message_id = message["messageId"]
            content = message["messageContent"]

            # 메시지 처리
            self.process_message(content)

            # 처리 완료 후 메시지 제거 — 이걸 빠뜨리면 같은 메시지를 계속 읽는다
            requests.delete(
                f"{self.base_url}/sessions/{session_id}/publication/{message_id}",
                headers=self.headers
            )
            retry_count = 0  # 메시지를 받았으면 카운터 초기화
        elif resp.status_code == 204:
            # 읽을 메시지 없음
            retry_count += 1
            time.sleep(interval)
        else:
            raise Exception(f"polling 실패: {resp.status_code}")
```

### 전체 연동 예제

```python
# 발행자 측
client = ISBMClient(ISBM_BASE_URL)
client.create_channel("/order-events", "Publication")
pub_session = client.open_publication_session("/order-events")

order_data = {
    "orderId": "ORD-20260406-001",
    "items": [{"sku": "ITEM-A", "qty": 3}],
    "totalAmount": 45000
}

msg_id = client.publish_message(
    pub_session,
    topics=["order.created"],
    content=json.dumps(order_data),
    expiry="PT24H"  # 24시간 후 만료
)
print(f"발행 완료: {msg_id}")

# 구독자 측 (다른 시스템)
sub_session = client.open_subscription_session(
    "/order-events",
    topics=["order.created"]
)
client.poll_messages(sub_session)
```

## Kafka, RabbitMQ와의 차이

ISBM은 메시징 시스템 자체가 아니라, 메시징 시스템 위에 올라가는 표준 인터페이스다. 이 차이를 명확히 이해해야 한다.

| 항목 | ISBM | Kafka | RabbitMQ |
|------|------|-------|----------|
| 성격 | 표준 인터페이스 | 분산 스트리밍 플랫폼 | 메시지 브로커 |
| 프로토콜 | REST/SOAP | 자체 바이너리 프로토콜 | AMQP |
| 처리량 | 구현체에 의존 | 초당 수백만 건 | 초당 수만 건 |
| 메시지 소비 | Polling + 명시적 제거 | Consumer Group 기반 offset | ACK 기반 |
| 실시간성 | 낮음 (Polling) | 높음 | 높음 |
| 주 사용처 | B2B 시스템 통합, 산업 표준 준수 | 이벤트 스트리밍, 로그 수집 | 서비스 간 비동기 통신 |
| 내부 구현 | 별도 메시징 시스템 필요 | 자체 스토리지 | 자체 큐 |

핵심 차이: Kafka나 RabbitMQ는 그 자체로 메시지를 저장하고 전달하는 시스템이다. ISBM은 그런 시스템 위에 표준 API를 씌운 것이다. ISBM 서버 내부에서 실제로 RabbitMQ나 다른 MQ를 백엔드로 쓸 수 있다.

### 언제 ISBM을 쓰는가

- 조직 간 메시지 연동에서 표준 인터페이스가 필요할 때
- 산업 표준(특히 광업, 에너지, 제조업 분야의 OpenO&M)을 준수해야 할 때
- 내부 메시징 시스템을 외부에 노출하지 않고 표준 API로 감싸야 할 때

내부 서비스 간 통신에는 Kafka나 RabbitMQ를 직접 쓰는 게 낫다. ISBM은 추상화 레이어를 하나 더 거치기 때문에, 성능이나 실시간성이 중요한 경우에는 맞지 않는다.

## 실무에서 겪는 문제들

### 세션 관리

세션을 열고 닫지 않으면 ISBM 서버에 좀비 세션이 쌓인다. 서버 구현체마다 다르지만, 세션이 많아지면 성능이 떨어지는 경우가 있다.

```python
class ISBMSessionManager:
    """
    세션을 context manager로 관리한다.
    예외가 발생해도 세션이 정리되도록 한다.
    """
    def __init__(self, client, channel_uri, session_type="publication"):
        self.client = client
        self.channel_uri = channel_uri
        self.session_type = session_type
        self.session_id = None

    def __enter__(self):
        if self.session_type == "publication":
            self.session_id = self.client.open_publication_session(self.channel_uri)
        elif self.session_type == "subscription":
            self.session_id = self.client.open_subscription_session(
                self.channel_uri, topics=["#"]  # 전체 토픽
            )
        return self.session_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session_id:
            try:
                requests.delete(
                    f"{self.client.base_url}/sessions/{self.session_id}",
                    headers=self.client.headers
                )
            except Exception:
                # 세션 종료 실패는 로깅만 하고 넘어간다
                pass
        return False
```

```python
# 사용
with ISBMSessionManager(client, "/order-events", "publication") as session_id:
    client.publish_message(session_id, ["order.created"], order_data)
# 블록을 벗어나면 세션이 자동으로 닫힌다
```

### 메시지 만료 설정

메시지에 만료 시간을 설정하지 않으면, 구독자가 없는 상태에서 메시지가 무한히 쌓인다. ISBM 서버의 디스크가 가득 차는 장애를 겪을 수 있다.

```python
# 잘못된 예 — 만료 시간 없음
client.publish_message(session_id, ["event"], data)

# 올바른 예 — 비즈니스 요구사항에 맞는 만료 시간 설정
client.publish_message(session_id, ["event"], data, expiry="PT1H")   # 1시간
client.publish_message(session_id, ["event"], data, expiry="P1D")    # 1일
client.publish_message(session_id, ["event"], data, expiry="PT30M")  # 30분
```

만료 시간은 ISO 8601 Duration 형식을 따른다. `PT1H`는 1시간, `P1D`는 1일, `PT30M`은 30분이다.

### 메시지 제거 누락

구독자가 메시지를 읽은 뒤 `DELETE`를 호출하지 않으면, 다음 `GET`에서 같은 메시지가 반복 반환된다. 이걸 모르면 무한 루프에 빠질 수 있다.

```python
# 문제 상황: 메시지 읽기만 하고 제거하지 않음
while True:
    msg = get_message(session_id)
    process(msg)  # 같은 메시지가 계속 반복된다

# 해결: 반드시 읽은 후 제거
while True:
    msg = get_message(session_id)
    if msg:
        process(msg)
        remove_message(session_id, msg["messageId"])  # 필수
```

### Polling 부하

ISBM은 Push 방식을 지원하지 않기 때문에, 구독자가 주기적으로 서버에 요청을 보내야 한다. 구독자가 많아지면 서버에 부하가 집중된다.

대응 방법:

- polling 간격을 적절히 조절한다. 실시간성이 덜 중요하면 10~30초 간격이면 충분하다.
- 메시지가 없을 때(204 응답) 간격을 점진적으로 늘리는 backoff 로직을 적용한다.
- 구독자 수가 많으면 ISBM 서버 앞에 로드밸런서를 두고 수평 확장한다.

```python
def adaptive_poll(self, session_id):
    """메시지 빈도에 따라 polling 간격을 조절한다."""
    interval = 1  # 시작은 1초
    max_interval = 30
    min_interval = 1

    while True:
        msg = self.get_message(session_id)
        if msg:
            self.process_message(msg)
            self.remove_message(session_id, msg["messageId"])
            interval = min_interval  # 메시지가 있으면 간격을 줄인다
        else:
            interval = min(interval * 2, max_interval)  # 없으면 간격을 늘린다
        time.sleep(interval)
```

### 에러 처리

ISBM 서버와의 네트워크가 불안정한 경우, 메시지 발행은 성공했지만 응답을 받지 못하는 상황이 생길 수 있다. 재시도 시 중복 발행이 발생한다.

```python
import hashlib

def publish_with_dedup(self, session_id, topics, content, expiry=None):
    """
    멱등성 보장을 위해 content 기반 해시를 토픽에 포함한다.
    수신 측에서 이 해시로 중복을 판별한다.
    """
    content_str = json.dumps(content, sort_keys=True)
    content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:12]

    enriched_content = {
        "_dedup_key": content_hash,
        "_timestamp": time.time(),
        "payload": content
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            return self.publish_message(
                session_id, topics,
                json.dumps(enriched_content), expiry
            )
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
```

ISBM 자체는 멱등성을 보장하지 않기 때문에, 발행자나 구독자 쪽에서 직접 중복 처리 로직을 구현해야 한다.

## 정리

ISBM은 고성능 메시징이 목적이 아니다. 서로 다른 시스템 간의 메시지 교환을 표준화하는 것이 목적이다. 내부 서비스 간 통신에는 과한 선택이고, 조직 간/기업 간 통합에서 공통 인터페이스가 필요할 때 고려할 수 있다.

도입 전에 확인할 것:

- ISBM 서버 구현체가 있는가 (OpenO&M ISBM Adapter 등)
- 연동 대상 시스템이 ISBM을 지원하는가
- Polling 기반의 지연을 비즈니스에서 허용할 수 있는가
- 메시지 만료와 세션 관리 정책을 사전에 정해둬야 한다
