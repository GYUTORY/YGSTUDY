---
title: RabbitMQ MQTT Plugin - AMQP와 MQTT 브릿지 실무
tags: [RabbitMQ, MQTT, IoT, Messaging, AMQP]
updated: 2026-03-26
---

# RabbitMQ MQTT Plugin

RabbitMQ는 `rabbitmq_mqtt` 플러그인을 통해 MQTT 브로커로 동작한다. 별도의 MQTT 브로커(Mosquitto 등)를 띄우지 않고, 기존 RabbitMQ 인프라에서 MQTT 디바이스의 메시지를 AMQP Consumer가 그대로 소비할 수 있다.

## 플러그인 활성화

```bash
rabbitmq-plugins enable rabbitmq_mqtt
```

활성화하면 1883 포트(TCP)와 8883 포트(TLS)에서 MQTT 클라이언트 접속을 받는다.

`rabbitmq.conf` 기본 설정:

```ini
# MQTT 리스너 포트
mqtt.listeners.tcp.default = 1883

# TLS 설정
mqtt.listeners.ssl.default = 8883
ssl_options.cacertfile = /path/to/ca_certificate.pem
ssl_options.certfile   = /path/to/server_certificate.pem
ssl_options.keyfile    = /path/to/server_key.pem

# 동시 접속 제한
mqtt.tcp_listen_options.backlog = 4096

# 기본 vhost (MQTT 클라이언트가 vhost를 지정할 수 없으므로 여기서 설정)
mqtt.vhost = /

# 기본 사용자 (익명 접속 허용 시)
mqtt.allow_anonymous = false
mqtt.default_user = mqtt_user
mqtt.default_pass = mqtt_password
```

`mqtt.allow_anonymous = true`로 설정하면 인증 없이 접속이 가능한데, 운영에서는 절대 쓰면 안 된다. 디바이스가 수천 대 붙는 환경에서 인증 없이 열어두면 어떤 일이 벌어지는지 상상하기 싫다.

## Exchange/Queue 매핑 구조

MQTT 클라이언트가 토픽에 publish하면 RabbitMQ 내부에서 다음과 같이 매핑된다.

```
MQTT Topic: sensor/temperature/room1
    ↓
AMQP Exchange: amq.topic (topic exchange)
AMQP Routing Key: sensor.temperature.room1
```

핵심 규칙:

- MQTT 토픽 구분자 `/`는 AMQP 라우팅 키의 `.`으로 변환된다
- MQTT 와일드카드 `+`는 AMQP의 `*`로, `#`은 그대로 `#`으로 변환된다
- 모든 MQTT 메시지는 기본적으로 `amq.topic` exchange로 들어간다

```
MQTT subscribe: sensor/+/room1  →  AMQP binding: sensor.*.room1
MQTT subscribe: sensor/#        →  AMQP binding: sensor.#
```

Exchange를 바꾸고 싶으면 `rabbitmq.conf`에서 설정한다:

```ini
mqtt.exchange = my.mqtt.exchange
```

이 설정을 바꾸면 기존에 `amq.topic`에 바인딩된 AMQP Consumer들이 메시지를 못 받게 되니까, 이미 운영 중인 시스템에서 변경할 때는 Consumer 쪽도 같이 바꿔야 한다.

## MQTT publish → AMQP consume 흐름

실제 메시지 흐름을 보면 이렇다:

```
[IoT Device] --MQTT publish--> [RabbitMQ MQTT Plugin]
                                       |
                                       v
                               amq.topic exchange
                                       |
                            routing key: sensor.temperature.room1
                                       |
                                       v
                               Queue (AMQP binding)
                                       |
                                       v
                            [Spring Boot AMQP Consumer]
```

AMQP 쪽에서 이 메시지를 받으려면 queue를 만들고 `amq.topic`에 바인딩하면 된다:

```java
@Configuration
public class MqttAmqpConfig {

    @Bean
    public TopicExchange mqttExchange() {
        // MQTT 플러그인이 사용하는 기본 exchange
        return new TopicExchange("amq.topic");
    }

    @Bean
    public Queue sensorQueue() {
        return QueueBuilder.durable("sensor.data.queue")
                .withArgument("x-message-ttl", 60000) // 1분 TTL
                .build();
    }

    @Bean
    public Binding sensorBinding(Queue sensorQueue, TopicExchange mqttExchange) {
        // MQTT 토픽 sensor/temperature/# 에 해당
        return BindingBuilder.bind(sensorQueue)
                .to(mqttExchange)
                .with("sensor.temperature.#");
    }
}
```

```java
@Component
public class SensorDataConsumer {

    @RabbitListener(queues = "sensor.data.queue")
    public void handleSensorData(Message message) {
        byte[] body = message.getBody();
        String payload = new String(body, StandardCharsets.UTF_8);

        // MQTT 메시지의 원본 토픽은 헤더에서 확인 가능
        MessageProperties props = message.getMessageProperties();
        String receivedRoutingKey = props.getReceivedRoutingKey();
        // "sensor.temperature.room1" → 원래 MQTT 토픽은 sensor/temperature/room1

        log.info("routing key: {}, payload: {}", receivedRoutingKey, payload);
    }
}
```

주의할 점이 하나 있다. MQTT 메시지의 payload는 byte 배열로 들어온다. JSON이든 문자열이든 직접 파싱해야 한다. AMQP의 content-type 헤더가 세팅되지 않는 경우가 많아서, `MessageConverter`에 의존하면 역직렬화에 실패할 수 있다.

## QoS 레벨별 동작 차이

MQTT QoS와 RabbitMQ 내부 동작이 직접적으로 연관된다.

### QoS 0 (At most once)

- MQTT 클라이언트가 publish하면 RabbitMQ는 ACK 없이 바로 exchange에 전달
- 메시지 유실 가능성이 있다
- RabbitMQ 내부에서 queue에 들어간 후에는 AMQP의 delivery guarantee를 따른다
- IoT 센서 데이터처럼 간헐적 유실이 허용되는 경우에 쓴다

### QoS 1 (At least once)

- PUBACK을 보내기 전에 RabbitMQ가 queue에 메시지를 넣는다
- **메시지 중복이 발생할 수 있다** — 네트워크 끊김 후 재전송 시
- Consumer 쪽에서 멱등성 처리가 필요하다

### QoS 2 (Exactly once)

RabbitMQ MQTT 플러그인은 **QoS 2를 지원하지 않는다**. 클라이언트가 QoS 2로 publish하면 QoS 1로 다운그레이드된다. 이걸 모르고 "exactly once delivery"를 기대하면 문제가 된다.

```ini
# QoS 2 → QoS 1 다운그레이드 (기본 동작, 변경 불가)
# 클라이언트 라이브러리에서 QoS 2 publish 시 로그에 경고가 남는다
```

subscribe 쪽도 마찬가지다. QoS 2로 subscribe해도 QoS 1로 처리된다.

## Retain 메시지 처리

MQTT retain 메시지는 토픽에 마지막으로 publish된 메시지를 브로커가 저장해두고, 새 subscriber가 접속하면 즉시 전달하는 기능이다.

RabbitMQ에서는 retain 메시지를 Mnesia(내장 DB) 또는 ETS 테이블에 저장한다.

```ini
# retain 메시지 저장소 설정
mqtt.retained_message_store = rabbit_mqtt_retained_msg_store_dets

# DETS 파일 경로 (기본값)
mqtt.retained_message_store_dets_sync_interval = 2000
```

운영에서 겪는 문제:

- retain 메시지가 많아지면 노드 재시작 시 로딩 시간이 길어진다
- 클러스터 환경에서 retain 메시지 동기화가 느리다 — 노드 간 불일치가 발생할 수 있다
- retain 메시지를 삭제하려면 해당 토픽에 빈 payload를 retain flag와 함께 publish해야 한다

```python
# retain 메시지 삭제 (paho-mqtt)
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("rabbitmq-host", 1883)
# 빈 payload + retain=True → 해당 토픽의 retain 메시지 삭제
client.publish("sensor/temperature/room1", payload=b"", retain=True)
```

## Spring Boot에서 MQTT 인바운드/아웃바운드 채널 설정

Spring Integration의 MQTT 지원을 쓰면 AMQP가 아닌 MQTT 프로토콜로 직접 RabbitMQ에 연결할 수 있다.

### 의존성

```xml
<dependency>
    <groupId>org.springframework.integration</groupId>
    <artifactId>spring-integration-mqtt</artifactId>
</dependency>
```

### 인바운드 (Subscribe)

```java
@Configuration
public class MqttInboundConfig {

    @Bean
    public MqttPahoClientFactory mqttClientFactory() {
        DefaultMqttPahoClientFactory factory = new DefaultMqttPahoClientFactory();
        MqttConnectOptions options = new MqttConnectOptions();
        options.setServerURIs(new String[]{"tcp://rabbitmq-host:1883"});
        options.setUserName("mqtt_user");
        options.setPassword("mqtt_password".toCharArray());
        options.setCleanSession(false); // 세션 유지
        options.setAutomaticReconnect(true);
        options.setKeepAliveInterval(30);
        options.setConnectionTimeout(10);
        factory.setConnectionOptions(options);
        return factory;
    }

    @Bean
    public MessageProducerSupport mqttInbound(MqttPahoClientFactory factory) {
        MqttPahoMessageDrivenChannelAdapter adapter =
                new MqttPahoMessageDrivenChannelAdapter(
                        "spring-subscriber-" + UUID.randomUUID().toString().substring(0, 8),
                        factory,
                        "sensor/temperature/#",
                        "device/status/#"
                );
        adapter.setCompletionTimeout(5000);
        adapter.setConverter(new DefaultPahoMessageConverter());
        adapter.setQos(1);
        adapter.setOutputChannel(mqttInputChannel());
        return adapter;
    }

    @Bean
    public MessageChannel mqttInputChannel() {
        return new DirectChannel();
    }

    @ServiceActivator(inputChannel = "mqttInputChannel")
    public void handleMqttMessage(
            @Header(MqttHeaders.RECEIVED_TOPIC) String topic,
            @Payload String payload) {
        log.info("topic: {}, payload: {}", topic, payload);
    }
}
```

Client ID에 랜덤 값을 넣는 이유가 있다. Spring Boot 인스턴스가 여러 개 뜰 때 Client ID가 같으면 먼저 접속한 클라이언트가 강제로 끊긴다. MQTT 스펙상 같은 Client ID로 새 연결이 들어오면 기존 연결을 끊어버린다. 이걸 모르고 고정 Client ID를 쓰면 두 인스턴스가 서로를 계속 끊는 현상이 발생한다.

### 아웃바운드 (Publish)

```java
@Configuration
public class MqttOutboundConfig {

    @Bean
    public MessageChannel mqttOutboundChannel() {
        return new DirectChannel();
    }

    @Bean
    @ServiceActivator(inputChannel = "mqttOutboundChannel")
    public MessageHandler mqttOutbound(MqttPahoClientFactory factory) {
        MqttPahoMessageHandler handler = new MqttPahoMessageHandler(
                "spring-publisher-" + UUID.randomUUID().toString().substring(0, 8),
                factory
        );
        handler.setAsync(true);
        handler.setDefaultTopic("command/response");
        handler.setDefaultQos(1);
        return handler;
    }
}
```

```java
@Component
@RequiredArgsConstructor
public class MqttPublisher {

    @Qualifier("mqttOutboundChannel")
    private final MessageChannel mqttOutboundChannel;

    public void publish(String topic, String payload) {
        Message<String> message = MessageBuilder
                .withPayload(payload)
                .setHeader(MqttHeaders.TOPIC, topic)
                .setHeader(MqttHeaders.QOS, 1)
                .build();
        mqttOutboundChannel.send(message);
    }
}
```

## 인증과 ACL 설정

### 기본 인증

RabbitMQ의 기존 사용자 인증 체계를 그대로 쓴다. MQTT 클라이언트의 username/password가 RabbitMQ 사용자로 인증된다.

```bash
# MQTT 전용 사용자 생성
rabbitmqctl add_user mqtt_device device_password
rabbitmqctl set_permissions -p / mqtt_device "^mqtt-subscription-.*$" "^(amq\.topic|mqtt-subscription-.*)$" "^(amq\.topic|mqtt-subscription-.*)$"
```

이 권한 설정을 풀어보면:

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

```java
// Spring Boot 인증 서비스 예시
@RestController
@RequestMapping("/rabbitmq")
public class RabbitMqAuthController {

    @PostMapping("/user")
    public String checkUser(
            @RequestParam String username,
            @RequestParam String password) {
        // 디바이스 인증 로직
        boolean valid = deviceAuthService.authenticate(username, password);
        return valid ? "allow" : "deny";
    }

    @PostMapping("/topic")
    public String checkTopic(
            @RequestParam String username,
            @RequestParam String routing_key,
            @RequestParam String permission) {
        // routing_key는 AMQP 형식 (sensor.temperature.room1)
        // username별 토픽 접근 권한 확인
        boolean allowed = aclService.checkTopicPermission(
                username, routing_key, permission);
        return allowed ? "allow" : "deny";
    }
}
```

## Clean Session 동작

MQTT의 `cleanSession` 플래그에 따라 RabbitMQ의 queue 생명주기가 달라진다.

### cleanSession = true (기본값)

- 접속할 때마다 새 queue를 만든다
- 연결이 끊기면 queue가 삭제된다
- 오프라인 동안의 메시지를 받지 못한다

### cleanSession = false

- `mqtt-subscription-{clientId}qos{N}` 형태의 durable queue가 생성된다
- 연결이 끊겨도 queue가 남아있어서 메시지가 쌓인다
- 재접속 시 밀린 메시지를 받을 수 있다

```
# cleanSession=false일 때 생성되는 queue 이름 예시
mqtt-subscription-device001qos1
```

여기서 주의할 게 있다. `cleanSession=false`인 디바이스가 접속을 안 하면 queue에 메시지가 계속 쌓인다. 디바이스 수천 대가 한꺼번에 오프라인 상태가 되면 RabbitMQ 메모리가 폭발한다. 반드시 TTL과 max-length를 설정해야 한다:

```ini
# 세션 queue 정책 설정
mqtt.subscription_ttl = 86400000
# 24시간 동안 접속 안 하면 queue 자동 삭제
```

## 운영 시 커넥션 폭증 대응

IoT 환경에서 수천~수만 대의 디바이스가 동시에 접속하면 생기는 문제들.

### TCP 백로그 설정

```ini
# 동시 접속 시 TCP handshake 대기열
mqtt.tcp_listen_options.backlog = 4096

# 소켓 버퍼 사이즈
mqtt.tcp_listen_options.sndbuf = 2048
mqtt.tcp_listen_options.recbuf = 2048

# Erlang process 제한
# vm_memory_high_watermark.relative = 0.6
```

### 커넥션 수 제한

```bash
# 전체 커넥션 수 확인
rabbitmqctl list_connections | wc -l

# MQTT 커넥션만 확인
rabbitmqctl list_connections protocol | grep -c mqtt
```

vhost 단위로 커넥션 수를 제한할 수 있다:

```bash
rabbitmqctl set_vhost_limits -p / '{"max-connections": 10000}'
```

### 커넥션 폭증 시 나타나는 증상과 대응

**증상 1: 파일 디스크립터 부족**

```bash
# 현재 제한 확인
rabbitmqctl status | grep -A 5 "file_descriptors"

# 시스템 레벨
ulimit -n 65536

# rabbitmq.conf
# 보통 커넥션 수의 2배 이상으로 설정
```

에러 로그에 `Too many open files`가 보이면 이 설정부터 확인한다.

**증상 2: Erlang process 한계**

```ini
# rabbitmq.conf
# MQTT 커넥션 하나당 Erlang process 여러 개를 쓴다
# 기본값(1048576)이 부족할 수 있다
```

```bash
# 현재 process 사용량 확인
rabbitmqctl eval 'erlang:system_info(process_count).'
```

**증상 3: 메모리 알람**

`cleanSession=false` 디바이스가 많으면 queue가 계속 남아서 메모리를 먹는다.

```bash
# 오래된 MQTT subscription queue 확인
rabbitmqctl list_queues name messages consumers \
  --formatter pretty_table | grep mqtt-subscription
```

메시지가 쌓여있는데 consumer가 0인 queue는 오프라인 디바이스의 queue다. 정책으로 정리한다:

```bash
# 메시지 TTL과 max-length 정책 적용
rabbitmqctl set_policy mqtt-ttl "^mqtt-subscription-" \
  '{"message-ttl": 3600000, "max-length": 1000}' \
  --apply-to queues
```

## 트러블슈팅

### 클라이언트가 접속 직후 끊기는 경우

대부분 Client ID 충돌이다. 같은 Client ID로 두 클라이언트가 접속하면 먼저 접속한 쪽이 끊긴다. 로그에서 확인할 수 있다:

```
connection <0.1234.0>, client ID "device001": kicked out by new connection
```

### AMQP Consumer가 메시지를 못 받는 경우

1. binding routing key 확인 — MQTT 토픽의 `/`가 `.`으로 변환되었는지
2. exchange 확인 — `amq.topic`이 아닌 다른 exchange를 쓰고 있는지
3. vhost 확인 — MQTT 플러그인의 vhost와 AMQP Consumer의 vhost가 같은지

```bash
# exchange의 binding 확인
rabbitmqctl list_bindings source_name routing_key destination_name \
  --formatter pretty_table | grep amq.topic
```

### 메시지 순서가 보장되지 않는 경우

MQTT QoS 1에서 재전송이 발생하면 순서가 바뀔 수 있다. 단일 queue에 단일 consumer면 RabbitMQ 내에서는 순서가 보장되지만, prefetch count가 1보다 크면 처리 순서가 뒤바뀔 수 있다.

```yaml
# application.yml
spring:
  rabbitmq:
    listener:
      simple:
        prefetch: 1  # 순서 보장이 필요하면 1로 설정
```

### MQTT 5.0 지원

RabbitMQ 3.13부터 MQTT 5.0을 지원한다. Shared Subscription, Message Expiry, Topic Alias 등을 쓸 수 있다. 다만 아직 모든 MQTT 5.0 기능이 구현된 건 아니라서, 사용 전에 RabbitMQ 릴리스 노트를 확인해야 한다.
