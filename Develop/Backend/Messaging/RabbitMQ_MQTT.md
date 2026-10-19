---
title: RabbitMQ MQTT Plugin - AMQP와 MQTT 브릿지 실무
tags: [messaging, backend, aws]
updated: 2026-10-19
---

# RabbitMQ MQTT Plugin

RabbitMQ는 `rabbitmq_mqtt` 플러그인으로 MQTT 브로커 역할을 한다. Mosquitto 같은 브로커를 따로 두지 않고, 디바이스가 MQTT로 발행한 메시지를 AMQP 컨슈머가 그대로 받게 만드는 구성이다.

이 문서의 동작 수치는 RabbitMQ 3.13.7과 4.0.9 컨테이너에 paho-mqtt 2.1.0, pika 1.4.4, raw 소켓으로 붙어서 직접 얻은 값이다. 두 버전이 갈리는 곳은 따로 적었고, 돌려보지 못한 부분은 돌려보지 못했다고 적었다.

## 플러그인 활성화와 리스너

```bash
rabbitmq-plugins enable rabbitmq_mqtt
```

컨테이너에서 실행했을 때 `Offline change; changes will take effect at broker restart`가 나왔고, 재시작한 뒤에야 `rabbitmq-diagnostics listeners`에 `protocol: mqtt, port: 1883`이 보였다. 활성화만 하고 리스너를 확인하지 않으면 클라이언트가 접속 거부만 받는다.

1883은 평문 TCP, 8883은 TLS 리스너로 설정했을 때 쓰는 포트다. 8883 TLS 리스너는 이 문서에서 실행해 보지 않았다. 1883만 실측했다.

`rabbitmq.conf` 기본 설정:

```ini
# MQTT 리스너 포트
mqtt.listeners.tcp.default = 1883

# TLS 설정
mqtt.listeners.ssl.default = 8883
ssl_options.cacertfile = /path/to/ca_certificate.pem
ssl_options.certfile   = /path/to/server_certificate.pem
ssl_options.keyfile    = /path/to/server_key.pem

# TCP accept 대기열
mqtt.tcp_listen_options.backlog = 4096

# MQTT 클라이언트는 vhost를 지정할 수 없으므로 여기서 정한다
mqtt.vhost = /

# 익명 접속 차단
mqtt.allow_anonymous = false
```

`mqtt.allow_anonymous = true`는 운영에서 쓰지 않는다. 디바이스가 수천 대 붙는 환경에서 인증 없이 열어 두면 아무 클라이언트나 `amq.topic`에 발행할 수 있게 된다.

이 문서의 이전 판에 있던 설정 두 가지는 기동 자체를 막는 것으로 확인됐다.

- `mqtt.default_user`, `mqtt.default_pass`: 4.0.9에서 `You've tried to set mqtt.default_user, but there is no setting with that name.`을 내고 부팅에 실패한다. 3.13.7에서는 이 키에서 걸리지 않았다. 버전을 올리다가 설정 파일 때문에 노드가 안 뜨는 경우가 여기서 나온다.
- `mqtt.subscription_ttl`: 3.13.7과 4.0.9 모두 `Since 3.13 mqtt.subscription_ttl (in milliseconds) is unsupported. Use mqtt.max_session_expiry_interval_seconds (in seconds) instead.`를 내며 `BOOT FAILED`로 끝난다. 3.12 이하 설정을 그대로 들고 올 때 걸린다. 대체 키는 뒤의 Clean Session 절에서 다룬다.

사용자는 설정 파일 대신 `rabbitmqctl add_user`로 만든다. 권한 설정은 인증 절에 있다.

## Amazon MQ에서는 이 플러그인을 쓸 수 없다

관리형 서비스로 옮기면서 "MQTT 플러그인만 켜면 된다"고 생각하기 쉽다. 8883이라는 포트 번호가 자체 호스팅 RabbitMQ의 MQTT TLS 기본 포트와 같아서 더 헷갈린다. AWS 문서를 확인한 결과는 이렇다.

- Amazon MQ for RabbitMQ의 플러그인 항목에는 management, shovel, federation, consistent hash exchange, OAuth 2, LDAP, HTTP, SSL certificate, aws, JMS topic exchange, Prometheus가 올라 있다. `rabbitmq_mqtt`는 목록에 없다(2026-10-19에 확인한 페이지 기준).
- 브로커 노드에 접근할 수 없어서 `rabbitmq-plugins enable`을 직접 실행할 방법도 없다. 임의 플러그인을 켤 수 없다는 점은 [Amazon MQ 운영 노트](../../Cloud/AWS/Application_Integration/Amazon_MQ.md)에서 지연 메시지 플러그인 사례로 다뤘다.
- AWS 문서에서 `ssl://...:8883`으로 MQTT에 붙는 예제는 ActiveMQ 페이지에 있다. Amazon MQ에서 8883은 ActiveMQ 브로커의 MQTT 엔드포인트다. RabbitMQ 브로커의 접속 포트는 `amqps` 5671이고 관리 콘솔은 443이다.

Amazon MQ에서 RabbitMQ 브로커를 직접 만들어 MQTT 접속을 시도해 보지는 않았다. 위 내용은 문서 기준 판단이다. 실제 브로커를 만들었다면 콘솔의 Connections 항목에 나오는 엔드포인트 목록이 최종 근거가 된다.

```mermaid
flowchart LR
    subgraph SELF["자체 호스팅 RabbitMQ"]
        D1["MQTT 클라이언트"] -->|"1883 또는 8883"| P1["rabbitmq_mqtt"]
        P1 --> X1["amq.topic"]
        X1 --> C1["AMQP 컨슈머"]
    end
    subgraph AMQRMQ["Amazon MQ RabbitMQ 엔진"]
        D2["MQTT 클라이언트"] -.->|"문서상 엔드포인트 없음"| B2["RabbitMQ 브로커"]
        C2["AMQP 컨슈머"] -->|"5671 amqps"| B2
    end
    subgraph AMQACT["Amazon MQ ActiveMQ 엔진"]
        D3["MQTT 클라이언트"] -->|"8883 ssl"| B3["ActiveMQ 브로커"]
    end
```

세 구성의 차이를 한 장으로 본 것이다. 가운데 RabbitMQ 엔진 쪽 점선이 문서상 MQTT 진입로가 없다는 뜻이고, 오른쪽 ActiveMQ는 MQTT가 되지만 `amq.topic`이나 라우팅 키 변환 같은 이 문서의 매핑 규칙은 적용되지 않는다. exchange 개념이 RabbitMQ 플러그인에 속하기 때문이다.

| 구성 | MQTT 접속 | MQTT 메시지를 AMQP 컨슈머가 받는 방식 |
|---|---|---|
| 자체 호스팅 RabbitMQ | 1883 (TLS 설정 시 8883) | `amq.topic`에 바인딩한 큐로 받는다 |
| Amazon MQ RabbitMQ | 문서상 없음 | 해당 없음 |
| Amazon MQ ActiveMQ | 8883 (ssl) | ActiveMQ 자체 규칙이라 이 문서의 매핑과 무관 |

디바이스는 MQTT, 백엔드는 AMQP 0-9-1인 구성을 Amazon MQ에서 유지하려는 경우에 선택지는 둘이다. RabbitMQ를 EC2 같은 곳에 직접 올리거나, ActiveMQ 엔진으로 가면서 백엔드 컨슈머를 ActiveMQ가 받는 프로토콜로 다시 짜는 것이다. 후자는 마이그레이션이 아니라 재작성에 가깝다.

## 토픽이 라우팅 키로 바뀌는 과정

MQTT 클라이언트가 토픽에 발행하면 플러그인이 슬래시를 점으로 바꿔 `amq.topic`에 라우팅 키로 넘긴다. 구독 쪽은 필터를 바인딩 키로 바꿔 구독 큐를 `amq.topic`에 묶는다.

```mermaid
flowchart LR
    T["MQTT 토픽<br/>sensor/temperature/room1"] --> S["슬래시를 점으로 치환"]
    S --> K["라우팅 키<br/>sensor.temperature.room1"]
    K --> X["amq.topic<br/>topic exchange"]
    X -->|"바인딩 sensor.temperature.#"| Q1["sensor.data.queue<br/>AMQP 컨슈머용"]
    X -->|"바인딩 sensor.*.room1<br/>MQTT 필터 sensor/+/room1"| Q2["mqtt-subscription-sub-wildqos1<br/>MQTT 구독자용"]
    X -.->|"바인딩 a.* 는 단계 수가 달라 불일치"| Q3["mqtt-subscription 큐 다른 구독자"]
```

한 라우팅 키가 여러 바인딩에 동시에 매칭되면 각 큐로 복사된다. AMQP 컨슈머용 큐와 MQTT 구독자용 큐가 같은 `amq.topic`에 붙어 있어서, MQTT 구독자와 AMQP 컨슈머가 같은 메시지를 따로 받는다.

3.13.7과 4.0.9에서 같은 결과가 나온 변환 결과다.

| MQTT 발행 토픽 | AMQP 라우팅 키 |
|---|---|
| `sensor/temperature/room1` | `sensor.temperature.room1` |
| `a.b/c` | `a.b.c` |
| `/lead/slash` | `.lead.slash` |
| `trail/` | `trail.` |
| `a//b` | `a..b` |

| MQTT 구독 필터 | 생성된 바인딩 |
|---|---|
| `sensor/+/room1` | `sensor.*.room1` |
| `sensor/#` | `sensor.#` |
| `a.b/+` | `a.b.*` |

실무에서 걸리는 부분이 세 가지 있다.

토픽 안의 점은 이스케이프되지 않는다. `a.b/c`와 `a/b/c`는 둘 다 `a.b.c`가 된다. AMQP 컨슈머가 받은 라우팅 키만 보고는 원래 토픽이 어느 쪽인지 알 수 없다. 디바이스 ID에 점이 들어가는 `device.001/status` 같은 토픽을 쓰면 단계 수가 AMQP 쪽 바인딩 패턴과 어긋난다. 토픽에 점을 쓰지 않는 규칙을 디바이스 쪽에 강제하는 편이 낫다.

맨 앞 슬래시는 맨 앞 점이 된다. `/lead/slash`로 발행하는 클라이언트가 있으면 라우팅 키가 `.lead.slash`라서 `lead.#` 바인딩에 걸리지 않는다. 빈 단계도 그대로 살아 있다. `e/+/z` 필터로 구독하면 `e/a/z`와 `e//z`가 모두 전달됐고, 단계가 하나 더 많은 `e/a/b/z`는 전달되지 않았다.

반대 방향도 같은 규칙이다. AMQP 퍼블리셔가 `amq.topic`에 라우팅 키 `amqp.one.x`로 발행하면 `amqp/+/x`를 구독한 MQTT 클라이언트에게 토픽 `amqp/one/x`로 도착했다.

기본 exchange를 바꾸려면 `rabbitmq.conf`에 `mqtt.exchange = my.mqtt.exchange`를 쓴다. 이 설정을 바꾸면 기존에 `amq.topic`에 바인딩된 AMQP 컨슈머가 메시지를 못 받게 되므로, 운영 중인 시스템에서는 컨슈머 쪽 바인딩도 같이 옮겨야 한다.

## MQTT 발행에서 AMQP 소비까지

디바이스가 발행한 메시지가 AMQP 컨슈머에게 닿는 순서다. 컨슈머가 먼저 큐를 만들고 바인딩해 두는 단계가 맨 앞에 있는 점을 본다.

```mermaid
sequenceDiagram
    participant C as AMQP 컨슈머
    participant Q as sensor.data.queue
    participant X as amq.topic
    participant P as MQTT 플러그인
    participant D as MQTT 클라이언트

    C->>Q: queue.declare, bind(sensor.temperature.#)
    C->>Q: basic.consume
    D->>P: PUBLISH sensor/temperature/room1, QoS 1
    P->>X: publish, routing key sensor.temperature.room1
    par 발행 확인
        P-->>D: PUBACK
    and 라우팅
        X->>Q: 바인딩 매칭, 큐에 적재
        Q->>C: deliver
    end
    C-->>Q: basic.ack
```

PUBACK이 큐 적재보다 앞서는지 뒤서는지는 이 실험으로 가려내지 못해서 `par`로 순서를 열어 뒀다. 확인한 것은 다음 사실이다. 바인딩이 하나도 없는 토픽에 QoS 1로 발행해도 PUBACK이 돌아왔고(`is_published` true), 나중에 큐를 바인딩해도 그 전에 발행한 메시지는 없었다. 바인딩한 뒤에 발행한 메시지만 큐에 들어왔다.

그래서 AMQP 컨슈머는 디바이스가 접속하기 전에 큐와 바인딩이 선언돼 있어야 한다. 컨슈머 배포가 늦어지는 동안 발행된 메시지는 사라지고, MQTT 클라이언트는 PUBACK을 받았으니 성공으로 처리한다. 클라이언트 쪽에서는 유실을 알아챌 방법이 없다.

AMQP 쪽에서 받은 메시지 속성도 직접 봤다. QoS 1 발행은 `delivery_mode=2`, QoS 0 발행은 `delivery_mode=1`이었고, `content_type`과 `headers`는 비어 있었다(`None`). 컨슈머 라이브러리가 content-type으로 역직렬화 방식을 고르는 경우에는 이 때문에 실패한다.

AMQP 쪽에서 이 메시지를 받으려면 queue를 만들고 `amq.topic`에 바인딩한다.

```typescript
// NestJS + @golevelup/nestjs-rabbitmq: MQTT Exchange/Queue 바인딩 설정
import { Module } from '@nestjs/common';
import { RabbitMQModule } from '@golevelup/nestjs-rabbitmq';

@Module({
  imports: [
    RabbitMQModule.forRoot(RabbitMQModule, {
      uri: 'amqp://user:password@rabbitmq-host:5672',
      exchanges: [
        {
          name: 'amq.topic',
          type: 'topic',
          // MQTT 플러그인이 사용하는 기본 exchange — 미리 선언되어 있으므로 durable: true
          options: { durable: true },
        },
      ],
      queues: [
        {
          name: 'sensor.data.queue',
          options: {
            durable: true,
            arguments: { 'x-message-ttl': 60000 }, // 1분 TTL
          },
          exchange: 'amq.topic',
          // MQTT 토픽 sensor/temperature/# 에 해당
          routingKey: 'sensor.temperature.#',
        },
      ],
    }),
  ],
})
export class MqttAmqpModule {}
```

```typescript
// NestJS @golevelup/nestjs-rabbitmq: MQTT 메시지 소비
import { Injectable, Logger } from '@nestjs/common';
import { RabbitSubscribe, AmqpConnection } from '@golevelup/nestjs-rabbitmq';
import { ConsumeMessage } from 'amqplib';

@Injectable()
export class SensorDataConsumer {
  private readonly logger = new Logger(SensorDataConsumer.name);

  @RabbitSubscribe({
    exchange: 'amq.topic',
    routingKey: 'sensor.temperature.#',
    queue: 'sensor.data.queue',
  })
  handleSensorData(msg: Buffer | string, amqpMsg: ConsumeMessage): void {
    // MQTT 메시지의 payload는 Buffer로 들어올 수 있으므로 직접 파싱
    const payload =
      typeof msg === 'string' ? msg : Buffer.from(msg).toString('utf-8');

    // 원본 MQTT 토픽은 AMQP routing key로 확인 (sensor.temperature.room1)
    const receivedRoutingKey = amqpMsg.fields.routingKey;
    // "sensor.temperature.room1" → 원래 MQTT 토픽은 sensor/temperature/room1

    this.logger.log(`routing key: ${receivedRoutingKey}, payload: ${payload}`);
  }
}
```

payload는 byte 배열로 들어온다. JSON이든 문자열이든 직접 파싱해야 한다. 위에서 본 대로 content-type 헤더가 비어 있어서 `MessageConverter`에 의존하면 역직렬화에 실패할 수 있다.

## QoS는 어디까지 보장되는가

MQTT QoS가 RabbitMQ 안에서 어떻게 바뀌는지 3.13.7과 4.0.9에서 확인한 결과다. 두 버전 모두 같았고, 다른 부분은 표에 따로 적었다.

| 확인 항목 | 결과 |
|---|---|
| 구독 QoS 0 요청 시 SUBACK | granted 0 |
| 구독 QoS 1 요청 시 SUBACK | granted 1 |
| 구독 QoS 2 요청 시 SUBACK | granted 1 (QoS 1로 내려감) |
| QoS 2로 구독한 세션의 큐 이름 | `mqtt-subscription-{clientId}qos1` |
| QoS 0 구독 큐 타입 | 3.13.7은 `classic`, 4.0.9는 `rabbit_mqtt_qos0_queue` |
| QoS 0 발행 시 AMQP `delivery_mode` | 1 |
| QoS 1 발행 시 AMQP `delivery_mode` | 2 |
| QoS 2 발행 시 AMQP `delivery_mode` | 2 |
| QoS 1 발행에 서버 응답 | PUBACK |
| QoS 2 발행에 서버 응답 | PUBREC가 아니라 PUBACK |
| 같은 packet id를 DUP으로 재전송 (QoS 1) | 큐에 2건 |
| 같은 packet id를 DUP으로 재전송 (QoS 2) | 큐에 2건 |
| AMQP `delivery_mode=2` 발행, QoS 1 구독자 | QoS 1로 전달 |
| AMQP `delivery_mode=1` 발행, QoS 1 구독자 | QoS 0으로 전달 |

### QoS 0

발행이 `delivery_mode=1`로 AMQP에 들어간다. 브로커 재시작에서 살아남을 이유가 없는 메시지로 취급한다는 뜻이다. IoT 센서처럼 다음 값이 곧 오는 데이터에 쓴다. 4.0.9에서는 QoS 0 구독자용 큐 타입이 `rabbit_mqtt_qos0_queue`로 따로 생긴다. 3.13.7에서 4.0.9로 올릴 때 `list_queues`나 모니터링 쿼리를 `classic`으로 거르고 있었다면 QoS 0 구독 큐가 결과에서 빠진다.

### QoS 1

PUBACK을 돌려주고, 같은 packet id를 다시 보내면 중복을 걸러내지 않는다. 네트워크가 끊겨서 클라이언트가 재전송하면 컨슈머는 같은 메시지를 두 번 받는다. 컨슈머 쪽 멱등 처리가 필요하다. MQTT packet id는 AMQP 쪽 속성으로 확인되지 않았으므로(속성 `content_type`, `headers` 모두 비어 있었다) 중복 판별용 ID는 payload 안에 넣어야 한다.

### QoS 2

QoS 2를 지원하지 않는다. 구독은 QoS 1로 내려가고, 발행은 더 걸리는 부분이 있다. raw 소켓으로 QoS 2 PUBLISH를 보내면 스펙대로라면 PUBREC가 와야 하는데 PUBACK(`40 02 00 0c`)이 왔고, 이어서 PUBREL을 보내자 브로커가 연결을 끊었다.

```mermaid
sequenceDiagram
    participant C as MQTT 클라이언트 raw 소켓
    participant B as RabbitMQ 3.13.7, 4.0.9

    C->>B: PUBLISH QoS 2, packet id 12
    B-->>C: PUBACK packet id 12
    C->>B: PUBREL packet id 12
    B-->>C: 연결 종료, EOF
```

스펙의 QoS 2 핸드셰이크는 PUBLISH, PUBREC, PUBREL, PUBCOMP 네 단계다. 이 브로커는 첫 응답부터 PUBACK을 보내서 핸드셰이크가 진행되지 않는다. paho-mqtt 2.1.0으로 QoS 2 발행을 했을 때는 `on_publish`가 호출됐고 연결도 유지됐다. 라이브러리가 PUBACK을 받고 완료로 처리해서 PUBREL을 보내지 않았기 때문으로 보인다. 라이브러리마다 이 처리가 같다고 장담할 수 없고, PUBREL까지 보내는 구현은 위 그림처럼 연결이 끊긴다.

QoS 2 발행도 QoS 1처럼 DUP 재전송이 중복으로 들어온다. 중복 없는 한 번 전달은 이 플러그인에서 기대하면 안 된다. 클라이언트 코드를 QoS 2로 짜 두었더라도 QoS 1과 같은 보장이라고 보고 컨슈머를 설계한다. 브로커 로그에는 QoS 2 관련 경고가 남지 않았다. QoS 2를 썼는지 로그로는 알 수 없다.

### AMQP에서 MQTT로 가는 방향

AMQP 퍼블리셔가 `delivery_mode`를 지정하지 않으면(기본 1) QoS 1로 구독한 MQTT 클라이언트도 QoS 0으로 받는다. 실측에서 `delivery_mode=1` 발행은 QoS 0으로, `delivery_mode=2` 발행은 QoS 1로 전달됐다. 백엔드가 디바이스에게 명령을 내려보내는 경로에서 AMQP 퍼블리셔가 persistent 설정을 빼먹으면, 디바이스가 QoS 1로 구독해 놓았어도 재전송 보장 없이 한 번 던지고 끝난다.

## Retain 메시지

retain은 토픽의 마지막 메시지를 브로커가 들고 있다가 새 구독자에게 바로 넘기는 기능이다. 기본 설정의 4.0.9, 그리고 `mqtt.retained_message_store = rabbit_mqtt_retained_msg_store_dets`를 준 3.13.7과 4.0.9에서 확인한 결과다.

| 확인 항목 | 결과 |
|---|---|
| 정확한 토픽 필터(`r7/keep`)로 새로 구독 | retain 메시지 전달, retain 플래그 true |
| QoS 0으로 발행한 retain 메시지 | 같은 방식으로 전달 |
| 빈 payload + retain으로 발행 | 이후 새 구독자에게 전달 안 됨 |
| 브로커 재시작 후 | retain 메시지 유지 |
| 와일드카드 필터(`r3/#`, `r3/+`)로 새로 구독 | 전달 안 됨 |

마지막 줄이 실무에서 걸린다. `device/+/status`처럼 와일드카드로 구독하는 클라이언트는 접속 직후에 각 디바이스의 마지막 상태를 못 받는다. 같은 구독을 정확한 토픽으로 나눠서 걸면 받는다. 와일드카드 구독으로 "최신 상태 스냅샷"을 얻으려던 설계는 이 플러그인에서 작동하지 않았다. 와일드카드 구독 직후 상태가 필요하면 AMQP 쪽이든 DB든 다른 경로로 읽어야 한다.

retain 메시지를 지우려면 해당 토픽에 빈 payload를 retain 플래그와 함께 발행한다.

```python
# retain 메시지 삭제 (paho-mqtt)
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("rabbitmq-host", 1883)
# 빈 payload + retain=True → 해당 토픽의 retain 메시지 삭제
client.publish("sensor/temperature/room1", payload=b"", retain=True)
```

노드 간 retain 동기화와 대량 retain 시의 재시작 로딩 시간은 클러스터나 대량 데이터로 돌려보지 않아서 이 문서에서 다루지 않는다.

## NestJS에서 MQTT 직접 연결

`mqtt` npm 패키지로 AMQP가 아닌 MQTT 프로토콜로 RabbitMQ에 직접 연결할 수 있다.

```bash
npm install mqtt
```

### 인바운드 (Subscribe)

```typescript
// NestJS MQTT 직접 연결 인바운드 — mqtt 패키지 사용
import { Injectable, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import * as mqtt from 'mqtt';
import { MqttClient } from 'mqtt';
import { randomBytes } from 'crypto';

@Injectable()
export class MqttInboundService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(MqttInboundService.name);
  private client: MqttClient;

  onModuleInit(): void {
    // Client ID에 랜덤 값 추가 — 인스턴스가 여러 개 뜰 때 충돌 방지
    const clientId = `nestjs-subscriber-${randomBytes(4).toString('hex')}`;

    this.client = mqtt.connect('tcp://rabbitmq-host:1883', {
      clientId,
      username: 'mqtt_user',
      password: 'mqtt_password',
      clean: false,           // 세션 유지 (cleanSession=false)
      reconnectPeriod: 1000,  // 자동 재연결 (ms)
      keepalive: 30,
      connectTimeout: 10_000,
    });

    this.client.on('connect', () => {
      this.logger.log(`MQTT connected: ${clientId}`);
      // 구독 토픽 등록
      this.client.subscribe(['sensor/temperature/#', 'device/status/#'], { qos: 1 });
    });

    this.client.on('message', (topic: string, payload: Buffer) => {
      this.handleMqttMessage(topic, payload.toString('utf-8'));
    });

    this.client.on('error', (err: Error) => {
      this.logger.error(`MQTT error: ${err.message}`);
    });
  }

  private handleMqttMessage(topic: string, payload: string): void {
    this.logger.log(`topic: ${topic}, payload: ${payload}`);
  }

  onModuleDestroy(): void {
    this.client?.end();
  }
}
```

Client ID가 같으면 먼저 접속한 클라이언트가 끊긴다. NestJS 인스턴스가 여러 개 뜨는데 고정 Client ID를 쓰면 두 인스턴스가 서로를 계속 끊는다. 위 코드에서 `randomBytes`를 붙인 이유다. 다만 `clean: false`와 랜덤 Client ID를 같이 쓰면 재시작할 때마다 새 ID의 세션 큐가 남는다. 세션을 이어가려면 인스턴스별로 고정된 ID(파드 이름 같은 값)가 필요하고, 그 경우 같은 ID를 가진 인스턴스가 동시에 둘 뜨지 않게 롤링 배포 방식을 봐야 한다.

### 아웃바운드 (Publish)

```typescript
// NestJS MQTT 아웃바운드 — MqttPublisher Injectable 서비스
import { Injectable, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import * as mqtt from 'mqtt';
import { MqttClient } from 'mqtt';
import { randomBytes } from 'crypto';

@Injectable()
export class MqttPublisher implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(MqttPublisher.name);
  private client: MqttClient;

  onModuleInit(): void {
    const clientId = `nestjs-publisher-${randomBytes(4).toString('hex')}`;

    this.client = mqtt.connect('tcp://rabbitmq-host:1883', {
      clientId,
      username: 'mqtt_user',
      password: 'mqtt_password',
      clean: true,
      reconnectPeriod: 1000,
    });

    this.client.on('connect', () => {
      this.logger.log(`MQTT publisher connected: ${clientId}`);
    });

    this.client.on('error', (err: Error) => {
      this.logger.error(`MQTT publisher error: ${err.message}`);
    });
  }

  // QoS 2는 이 브로커에서 QoS 1처럼 동작하므로 받지 않는다
  publish(topic: string, payload: string, qos: 0 | 1 = 1): void {
    this.client.publish(topic, payload, { qos }, (err?: Error) => {
      if (err) {
        this.logger.error(`MQTT publish failed [${topic}]: ${err.message}`);
      }
    });
  }

  onModuleDestroy(): void {
    this.client?.end();
  }
}
```

## 인증과 ACL

### 기본 인증

RabbitMQ의 기존 사용자 체계를 그대로 쓴다. MQTT 클라이언트의 username/password가 RabbitMQ 사용자로 인증된다.

```bash
# MQTT 전용 사용자 생성
rabbitmqctl add_user mqtt_device device_password
rabbitmqctl set_permissions -p / mqtt_device "^mqtt-subscription-.*$" "^(amq\.topic|mqtt-subscription-.*)$" "^(amq\.topic|mqtt-subscription-.*)$"
```

권한 설정을 풀면:

- **configure**: `mqtt-subscription-*` — MQTT 플러그인이 자동으로 만드는 queue 이름 패턴
- **write**: `amq.topic`과 `mqtt-subscription-*` — publish 시 exchange에 write, subscribe 시 자동 생성 queue에 write
- **read**: `amq.topic`과 `mqtt-subscription-*` — subscribe 시 exchange에서 read, 자동 생성 queue에서 read

### Topic Authorization (ACL)

`rabbitmq_auth_backend_http` 또는 `rabbitmq_auth_backend_cache`를 쓰면 토픽 레벨 ACL을 구현할 수 있다.

```ini
# HTTP 백엔드 인증
auth_backends.1 = http

auth_http.user_path     = http://auth-service:8080/rabbitmq/user
auth_http.vhost_path    = http://auth-service:8080/rabbitmq/vhost
auth_http.resource_path = http://auth-service:8080/rabbitmq/resource
auth_http.topic_path    = http://auth-service:8080/rabbitmq/topic
```

```typescript
// NestJS 인증 서비스 예시 — RabbitMQ HTTP Auth Backend 연동
import { Controller, Post, Body } from '@nestjs/common';
import { Injectable } from '@nestjs/common';

interface RabbitMqUserRequest {
  username: string;
  password: string;
}

interface RabbitMqTopicRequest {
  username: string;
  routing_key: string;
  permission: string;
}

@Controller('rabbitmq')
export class RabbitMqAuthController {
  constructor(
    private readonly deviceAuthService: DeviceAuthService,
    private readonly aclService: AclService,
  ) {}

  @Post('user')
  async checkUser(@Body() body: RabbitMqUserRequest): Promise<string> {
    // 디바이스 인증 로직
    const valid = await this.deviceAuthService.authenticate(
      body.username,
      body.password,
    );
    return valid ? 'allow' : 'deny';
  }

  @Post('topic')
  async checkTopic(@Body() body: RabbitMqTopicRequest): Promise<string> {
    // routing_key는 AMQP 형식 (sensor.temperature.room1)
    // username별 토픽 접근 권한 확인
    const allowed = await this.aclService.checkTopicPermission(
      body.username,
      body.routing_key,
      body.permission,
    );
    return allowed ? 'allow' : 'deny';
  }
}
```

ACL 서비스가 받는 `routing_key`는 변환이 끝난 점 구분 형식이다. 앞에서 본 대로 `a.b/c`와 `a/b/c`가 같은 키가 되므로, 토픽 단위로 권한을 나눌 때는 점이 들어간 토픽이 우회 경로가 되지 않는지 따져야 한다.

## Clean Session 동작

`cleanSession` 플래그에 따라 RabbitMQ의 구독 큐 수명이 달라진다. 큐 이름은 `mqtt-subscription-{clientId}qos{N}` 형태이고, 실측에서 `qs-1-1`이라는 Client ID로 QoS 1 구독했더니 `mqtt-subscription-qs-1-1qos1`이 생겼다.

```mermaid
stateDiagram-v2
    [*] --> 접속
    접속 --> 구독큐생성: SUBSCRIBE
    구독큐생성 --> 큐삭제: DISCONNECT, cleanSession=true
    구독큐생성 --> 큐유지: DISCONNECT, cleanSession=false
    큐유지 --> 구독큐생성: 같은 Client ID로 재접속
    큐유지 --> 큐삭제: x-expires 경과
    큐삭제 --> [*]
```

### cleanSession = true

접속할 때마다 새 큐를 만들고, 연결이 끊기면 삭제된다. 끊긴 직후 `list_queues`에서 해당 큐가 사라진 것을 확인했다. 오프라인 동안 발행된 메시지는 받지 못한다.

### cleanSession = false

연결이 끊겨도 큐가 남아 메시지가 쌓이고, 재접속하면 밀린 메시지를 받는다. 큐는 `durable=true`이고 `x-expires: 86400000`(24시간)이 기본으로 붙어 있었다. 24시간 접속하지 않으면 큐가 삭제된다는 뜻이다.

만료 시간은 `mqtt.max_session_expiry_interval_seconds`로 바꾼다. 3600을 줬더니 3.13.7과 4.0.9 모두 새 구독 큐에 `x-expires: 3600000`이 붙었다.

```ini
# 세션 큐 만료 시간(초). 이 시간 동안 접속이 없으면 구독 큐 삭제
mqtt.max_session_expiry_interval_seconds = 3600
```

`cleanSession=false` 디바이스가 한꺼번에 오프라인이 되면 구독 큐마다 메시지가 쌓여 메모리가 부담이 된다. 만료 시간만으로는 만료 전까지 쌓이는 양을 막지 못하므로 정책으로 TTL과 max-length를 같이 건다(커넥션 폭증 절의 `set_policy` 참조).

## 운영 시 커넥션 폭증 대응

IoT 환경에서 수천~수만 대의 디바이스가 동시에 접속하면 생기는 문제들이다.

### TCP 백로그 설정

```ini
# 동시 접속 시 TCP handshake 대기열
mqtt.tcp_listen_options.backlog = 4096

# 소켓 버퍼 사이즈
mqtt.tcp_listen_options.sndbuf = 2048
mqtt.tcp_listen_options.recbuf = 2048
```

위 키들은 4.0.9에서 설정 파일 검증을 통과했다.

### 커넥션 수 제한

```bash
# 전체 커넥션 수 확인
rabbitmqctl list_connections | wc -l

# MQTT 커넥션만 확인
rabbitmqctl list_connections protocol | grep -c mqtt
```

vhost 단위로 커넥션 수를 제한할 수 있다.

```bash
rabbitmqctl set_vhost_limits -p / '{"max-connections": 10000}'
```

### 커넥션 폭증 시 증상

**파일 디스크립터 부족**

```bash
# 현재 제한 확인
rabbitmqctl status | grep -A 5 "file_descriptors"

# 시스템 레벨
ulimit -n 65536
```

에러 로그에 `Too many open files`가 보이면 이 설정부터 확인한다. 보통 커넥션 수의 2배 이상으로 잡는다.

**Erlang process 한계**

MQTT 커넥션 하나가 Erlang process를 여러 개 쓴다. 기본값 1048576이 부족할 수 있다.

```bash
# 현재 process 사용량 확인
rabbitmqctl eval 'erlang:system_info(process_count).'
```

**메모리 알람**

`cleanSession=false` 디바이스가 많으면 큐가 계속 남아서 메모리를 먹는다.

```bash
# 오래된 MQTT subscription queue 확인
rabbitmqctl list_queues name messages consumers \
  --formatter pretty_table | grep mqtt-subscription
```

메시지가 쌓여 있는데 consumer가 0인 큐는 오프라인 디바이스의 큐다. 정책으로 정리한다.

```bash
# 메시지 TTL과 max-length 정책 적용
rabbitmqctl set_policy mqtt-ttl "^mqtt-subscription-" \
  '{"message-ttl": 3600000, "max-length": 1000}' \
  --apply-to queues
```

## 트러블슈팅

### 클라이언트가 접속 직후 끊기는 경우

대부분 Client ID 충돌이다. 같은 Client ID로 두 번째 접속이 들어오면 먼저 접속한 쪽이 끊긴다. 브로커 로그에 이런 줄이 남는다.

```
MQTT disconnecting client <<"172.17.0.1:36520 -> 172.17.0.4:1883">> with duplicate id 'dup-id'
```

paho의 자동 재연결이 켜진 두 클라이언트로 재현했더니, 한쪽이 끊기고 재연결하면 다른 쪽이 끊기는 일이 반복됐다. 로그에 `duplicate id`가 반복해서 찍히면 이 상황이다.

### AMQP Consumer가 메시지를 못 받는 경우

1. binding routing key 확인 — MQTT 토픽의 `/`가 `.`으로 변환됐는지, 맨 앞 슬래시가 점으로 남지 않았는지
2. exchange 확인 — `amq.topic`이 아닌 다른 exchange를 쓰는지
3. vhost 확인 — MQTT 플러그인의 vhost와 AMQP Consumer의 vhost가 같은지
4. 발행 시점 확인 — 큐 바인딩보다 먼저 발행된 메시지는 남아 있지 않다

```bash
# exchange의 binding 확인
rabbitmqctl list_bindings source_name routing_key destination_name \
  --formatter pretty_table | grep amq.topic
```

### 메시지 순서가 뒤바뀌는 경우

QoS 1 재전송이 일어나면 순서가 바뀔 수 있다. 단일 큐에 단일 consumer여도 prefetch count가 1보다 크면 처리 순서가 뒤바뀔 수 있다.

```typescript
// NestJS @golevelup/nestjs-rabbitmq prefetch 설정
RabbitMQModule.forRoot(RabbitMQModule, {
  uri: 'amqp://user:password@rabbitmq-host:5672',
  prefetchCount: 1, // 순서가 필요하면 1로 설정
  exchanges: [/* ... */],
});
```

### MQTT 5.0

3.13.7에서는 MQTT 5.0 클라이언트가 접속하면 `Unsupported protocol version`으로 거부됐다. 4.0.9에서는 접속에 성공했고, `$share/g1/shared/t` 공유 구독 SUBSCRIBE에 `Granted QoS 1`이 돌아왔다. MQTT 5.0이 필요하면 4.0 이상이어야 한다. 공유 구독으로 실제 메시지가 컨슈머들에게 나뉘어 가는지, Message Expiry와 Topic Alias가 동작하는지는 확인하지 못했다.

---
이 문서는 [메시징과 전달 보장 허브](../../_hub/메시징과_전달_보장.md)의 일부입니다. Amazon MQ로 옮기는 경우는 [Amazon MQ 운영 노트](../../Cloud/AWS/Application_Integration/Amazon_MQ.md)를 함께 본다.
