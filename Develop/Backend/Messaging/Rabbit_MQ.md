---
title: RabbitMQ 심화
tags: [RabbitMQ, AMQP, Messaging, Spring AMQP, Quorum Queue]
updated: 2026-04-02
---

# RabbitMQ 심화

RabbitMQ는 AMQP 0-9-1 프로토콜 기반의 메시지 브로커다. Kafka와 달리 메시지를 Consumer가 처리하면 큐에서 제거하는 전통적인 메시지 큐 모델이다. 이 문서는 RabbitMQ를 운영 수준에서 다루기 위해 필요한 내용을 정리한다.

---

## Publisher Confirms

메시지를 publish한 뒤 브로커가 실제로 받았는지 확인하는 메커니즘이다. 기본 설정에서는 `basicPublish()`가 리턴되더라도 브로커에 메시지가 도착했다는 보장이 없다.

### Confirm 모드 활성화

```java
Channel channel = connection.createChannel();
channel.confirmSelect(); // confirm 모드 ON
```

`confirmSelect()`를 호출하면 해당 Channel에서 발행하는 모든 메시지에 대해 브로커가 ack/nack을 보낸다.

### 3가지 확인 방식

**개별 확인 (동기)**

```java
channel.basicPublish("exchange", "routing.key", null, body);
boolean confirmed = channel.waitForConfirms(5000); // 5초 타임아웃
if (!confirmed) {
    // 재발행 또는 로깅
}
```

메시지 하나마다 블로킹으로 대기한다. 처리량이 떨어지기 때문에 배치 처리에는 부적합하다.

**배치 확인 (동기)**

```java
int batchSize = 100;
int count = 0;

for (Message msg : messages) {
    channel.basicPublish("exchange", "routing.key", null, msg.getBytes());
    count++;
    if (count >= batchSize) {
        channel.waitForConfirmsOrDie(10000); // 하나라도 nack이면 IOException
        count = 0;
    }
}
```

배치 중 하나라도 실패하면 어떤 메시지가 실패했는지 알 수 없다. 전체를 재발행해야 하는 문제가 있다.

**비동기 확인 (권장)**

```java
ConcurrentNavigableMap<Long, String> outstanding = new ConcurrentSkipListMap<>();

channel.addConfirmListener(new ConfirmListener() {
    @Override
    public void handleAck(long deliveryTag, boolean multiple) {
        if (multiple) {
            outstanding.headMap(deliveryTag + 1).clear();
        } else {
            outstanding.remove(deliveryTag);
        }
    }

    @Override
    public void handleNack(long deliveryTag, boolean multiple) {
        // nack된 메시지 재발행 로직
        if (multiple) {
            ConcurrentNavigableMap<Long, String> nacked = outstanding.headMap(deliveryTag + 1);
            nacked.values().forEach(body -> {
                // 재발행
            });
            nacked.clear();
        } else {
            String body = outstanding.remove(deliveryTag);
            // 재발행
        }
    }
});

for (Message msg : messages) {
    long seq = channel.getNextPublishSeqNo();
    outstanding.put(seq, msg.getBody());
    channel.basicPublish("exchange", "routing.key", null, msg.getBytes());
}
```

`deliveryTag`는 Channel 단위로 1부터 순차 증가한다. `multiple=true`면 해당 태그 이하 모든 메시지를 의미한다.

### Mandatory 플래그

```java
channel.basicPublish("exchange", "routing.key", true, null, body); // mandatory=true
channel.addReturnListener(returnMessage -> {
    // 라우팅 불가 메시지 처리
});
```

`mandatory=true`로 설정하면, exchange에서 어떤 큐로도 라우팅되지 않는 메시지를 publisher에게 돌려보낸다. 설정하지 않으면 메시지가 조용히 사라진다. 운영에서 꽤 자주 겪는 문제가 exchange-queue 바인딩을 빠뜨리고 메시지가 유실되는 건데, mandatory와 return listener를 같이 설정해두면 잡을 수 있다.

---

## Consumer Acknowledgement

Consumer가 메시지를 받은 뒤 처리 결과를 브로커에 알리는 메커니즘이다. auto-ack(`autoAck=true`)를 쓰면 브로커가 메시지를 보내는 순간 처리 완료로 간주한다. 처리 중 Consumer가 죽으면 메시지가 유실된다.

### Manual Ack

```java
channel.basicConsume("queue", false, (consumerTag, delivery) -> {
    try {
        process(delivery.getBody());
        channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);
    } catch (Exception e) {
        // 처리 실패
        channel.basicNack(delivery.getEnvelope().getDeliveryTag(), false, true);
    }
}, consumerTag -> {});
```

`autoAck` 파라미터를 `false`로 넘겨야 manual ack가 동작한다.

### ack, nack, reject 차이

| 메서드 | 파라미터 | 동작 |
|--------|----------|------|
| `basicAck(tag, multiple)` | multiple: 해당 tag 이하 전체 ack | 정상 처리 완료, 큐에서 제거 |
| `basicNack(tag, multiple, requeue)` | requeue=true: 큐 앞쪽에 재입력 | 처리 실패, 여러 메시지 한번에 거부 가능 |
| `basicReject(tag, requeue)` | requeue=true: 큐 앞쪽에 재입력 | 처리 실패, 메시지 1개만 거부 |

`basicNack`는 RabbitMQ 확장이고, `basicReject`은 AMQP 표준이다. 차이는 `basicNack`만 `multiple` 파라미터를 지원한다는 점이다.

### requeue의 함정

`requeue=true`로 nack/reject하면 메시지가 큐 앞쪽에 다시 들어간다. 처리 로직에 버그가 있으면 같은 메시지가 무한 반복된다.

```
Consumer 받음 → 처리 실패 → nack(requeue=true) → 큐에 재입력 → 다시 받음 → 또 실패 → ...
```

이걸 방지하려면:

1. 재시도 횟수를 메시지 헤더(x-death)로 추적하고 임계값 초과 시 DLQ로 보낸다
2. Spring AMQP의 RetryTemplate을 사용한다 (아래 참조)
3. `requeue=false`로 설정하고 DLQ에서 별도 처리한다

### Prefetch Count

```java
channel.basicQos(10); // Consumer가 한 번에 받을 수 있는 미확인 메시지 수
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

**Channel은 스레드 세이프하지 않다.** 여러 스레드에서 하나의 Channel을 공유하면 프레임이 섞여서 프로토콜 에러가 발생한다. 스레드마다 Channel을 분리하거나, Channel Pool을 사용해야 한다.

**Publisher와 Consumer의 Connection을 분리해야 하는 경우가 있다.** TCP backpressure가 걸리면 하나의 Connection에서 publish와 consume이 서로 영향을 준다. 처리량이 높은 시스템에서는 Publisher Connection과 Consumer Connection을 별도로 둔다.

### Channel Pooling (Spring AMQP)

```java
@Bean
public CachingConnectionFactory connectionFactory() {
    CachingConnectionFactory factory = new CachingConnectionFactory("localhost");
    factory.setUsername("guest");
    factory.setPassword("guest");
    
    // Channel 캐싱 (기본값)
    factory.setCacheMode(CachingConnectionFactory.CacheMode.CHANNEL);
    factory.setChannelCacheSize(25); // 기본 25
    
    // 또는 Connection 캐싱 (Connection도 풀링)
    // factory.setCacheMode(CachingConnectionFactory.CacheMode.CONNECTION);
    // factory.setConnectionCacheSize(5);
    
    return factory;
}
```

`CHANNEL` 모드는 Connection 1개를 공유하고 Channel만 풀링한다. `CONNECTION` 모드는 Connection 자체도 풀링하는데, Publisher/Consumer를 분리하거나 Connection 수준 격리가 필요할 때 쓴다.

`channelCheckoutTimeout`을 설정하면 풀에서 Channel을 꺼낼 때 타임아웃을 줄 수 있다.

```java
factory.setChannelCheckoutTimeout(5000); // 5초 대기 후 AmqpTimeoutException
```

이걸 설정하지 않으면 풀이 가득 차도 새 Channel을 무한정 만든다. 운영에서는 반드시 설정해야 한다.

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

```java
Map<String, Object> args = new HashMap<>();
args.put("x-queue-type", "quorum");
args.put("x-quorum-initial-group-size", 3); // 복제 노드 수
channel.queueDeclare("my.quorum.queue", true, false, false, args);
```

`x-quorum-initial-group-size`는 클러스터 노드 수 이하로 설정해야 한다. 3노드 클러스터면 3이 적당하다. 5노드 클러스터에서 5로 설정하면 모든 노드에 복제되지만 쓰기 성능이 떨어진다.

**Quorum Queue에서 주의할 점:**

- `exclusive`, `non-durable` 옵션은 쓸 수 없다. 항상 durable이다.
- 메시지가 requeue되면 원래 순서가 보장되지 않는다. 순서가 중요한 처리에서 nack+requeue를 쓸 때 주의해야 한다.
- poison message handling을 위해 `x-delivery-limit`을 설정할 수 있다. 이 횟수를 초과하면 DLQ로 간다.

```java
args.put("x-delivery-limit", 5); // 5번 재전달 후 DLQ로
```

### Lazy Queue

Lazy Queue는 메시지를 최대한 디스크에 저장하고 Consumer가 요청할 때만 메모리로 올린다.

```java
Map<String, Object> args = new HashMap<>();
args.put("x-queue-mode", "lazy");
channel.queueDeclare("my.lazy.queue", true, false, false, args);
```

일반 큐는 메시지를 메모리에 유지하다가 메모리 pressure가 생기면 디스크로 내린다. Lazy Queue는 처음부터 디스크에 쓴다.

쓰는 경우:

- 큐에 메시지가 수백만 건 쌓이는 구조 (Consumer가 간헐적으로 처리)
- Memory Alarm이 자주 발생하는 환경
- 처리량보다 안정성이 중요한 경우

RabbitMQ 3.12부터 Quorum Queue는 기본적으로 lazy 동작을 한다. Classic Queue에서만 별도 설정이 필요하다.

### Priority Queue

```java
Map<String, Object> args = new HashMap<>();
args.put("x-max-priority", 10); // 우선순위 범위 0~10
channel.queueDeclare("my.priority.queue", true, false, false, args);
```

메시지 발행 시 priority를 지정한다:

```java
AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
    .priority(5)
    .build();
channel.basicPublish("exchange", "routing.key", props, body);
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

## Spring AMQP 심화

### RetryTemplate 설정

Consumer 처리 실패 시 재시도 로직을 Spring 레벨에서 처리한다. RabbitMQ의 requeue와 다르게 메시지를 큐에 돌려보내지 않고 Consumer 프로세스 내에서 재시도한다.

```java
@Configuration
public class RabbitConfig {

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        
        RetryTemplate retryTemplate = new RetryTemplate();
        
        // 최대 3번 재시도, 초기 간격 1초, 2배씩 증가, 최대 10초
        ExponentialBackOffPolicy backOff = new ExponentialBackOffPolicy();
        backOff.setInitialInterval(1000);
        backOff.setMultiplier(2.0);
        backOff.setMaxInterval(10000);
        retryTemplate.setBackOffPolicy(backOff);
        
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy();
        retryPolicy.setMaxAttempts(3);
        retryTemplate.setRetryPolicy(retryPolicy);
        
        factory.setRetryTemplate(retryTemplate);
        
        return factory;
    }
}
```

주의: RetryTemplate은 같은 스레드에서 블로킹으로 재시도한다. 재시도 간격이 길면 해당 Consumer 스레드가 묶인다. prefetch에 포함된 다른 메시지 처리도 지연된다.

### MessageRecoverer

RetryTemplate의 재시도가 모두 실패하면 MessageRecoverer가 호출된다. 기본 동작은 `RejectAndDontRequeueRecoverer`(메시지 버림)다.

```java
@Bean
public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
        ConnectionFactory connectionFactory, RabbitTemplate rabbitTemplate) {
    SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
    factory.setConnectionFactory(connectionFactory);
    
    // ... retryTemplate 설정 ...
    
    // 재시도 전부 실패 시 DLQ exchange로 발행
    factory.setRecoveryCallback(new RepublishMessageRecoverer(
        rabbitTemplate, "dlx.exchange", "dlx.routing.key"
    ).recoveryCallback());
    
    return factory;
}
```

`RepublishMessageRecoverer`는 원본 메시지에 예외 스택트레이스를 헤더로 붙여서 DLQ로 발행한다. 나중에 DLQ에서 메시지를 꺼내 원인을 분석할 때 유용하다.

다른 Recoverer 옵션:

- `RejectAndDontRequeueRecoverer`: 메시지를 reject(requeue=false). DLX가 설정되어 있으면 DLQ로 간다.
- `ImmediateRequeueMessageRecoverer`: 메시지를 큐에 다시 넣는다. 무한 루프 위험이 있어서 거의 쓰지 않는다.

### @RabbitListener concurrency 설정

```java
@RabbitListener(queues = "my.queue", concurrency = "3-10")
public void handle(Message message) {
    // 최소 3개, 최대 10개 Consumer 스레드
}
```

`concurrency = "3-10"`은 동적 스케일링이다. 큐에 메시지가 쌓이면 스레드를 늘리고, 줄어들면 다시 줄인다.

`concurrency = "5"`로 고정하면 항상 5개 스레드가 동작한다.

동적 스케일링은 `SimpleMessageListenerContainer`에서만 지원한다. `DirectMessageListenerContainer`는 고정 수만 지원한다.

### Container Factory 커스터마이징

용도별로 Container Factory를 분리하면 큐마다 다른 설정을 적용할 수 있다.

```java
@Configuration
public class RabbitConfig {

    // 일반 처리용
    @Bean
    public SimpleRabbitListenerContainerFactory defaultFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setPrefetchCount(10);
        factory.setConcurrentConsumers(3);
        factory.setMaxConcurrentConsumers(10);
        factory.setDefaultRequeueRejected(false); // 처리 실패 시 requeue 안 함
        return factory;
    }

    // 고처리량용
    @Bean
    public SimpleRabbitListenerContainerFactory highThroughputFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setPrefetchCount(50);
        factory.setConcurrentConsumers(10);
        factory.setMaxConcurrentConsumers(20);
        factory.setBatchSize(10); // 배치 리스너용
        return factory;
    }

    // 순서 보장용
    @Bean
    public SimpleRabbitListenerContainerFactory orderedFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setPrefetchCount(1);  // 하나씩 처리
        factory.setConcurrentConsumers(1);  // 단일 Consumer
        return factory;
    }
}
```

리스너에서 사용:

```java
@RabbitListener(queues = "high.volume.queue", containerFactory = "highThroughputFactory")
public void handleHighVolume(List<Message> messages) {
    // 배치 처리
}

@RabbitListener(queues = "ordered.queue", containerFactory = "orderedFactory")
public void handleOrdered(Message message) {
    // 순서 보장 처리
}
```

### SimpleMessageListenerContainer vs DirectMessageListenerContainer

| 항목 | SimpleMLLC | DirectMLLC |
|------|-----------|-----------|
| 스레드 모델 | 내부 스레드 풀에서 Consumer 스레드 생성 | RabbitMQ Client 스레드에서 직접 콜백 |
| 동적 스케일링 | `min-max` concurrency 지원 | 고정 consumers-per-queue만 지원 |
| 트랜잭션 | 지원 | 지원 |
| 리소스 | 스레드 풀 오버헤드 있음 | 스레드 풀 없어서 가벼움 |
| 큐 추가/제거 | 컨테이너 재시작 필요 | 런타임에 큐 추가/제거 가능 |

큐 수가 많고 동적으로 관리해야 하면 `DirectMessageListenerContainer`가 낫다. Consumer 수를 동적으로 조절해야 하면 `SimpleMessageListenerContainer`를 써야 한다.

```java
@Bean
public DirectRabbitListenerContainerFactory directFactory(
        ConnectionFactory connectionFactory) {
    DirectRabbitListenerContainerFactory factory = new DirectRabbitListenerContainerFactory();
    factory.setConnectionFactory(connectionFactory);
    factory.setConsumersPerQueue(5);
    factory.setPrefetchCount(10);
    return factory;
}
```

---

## Dead Letter Exchange (DLX) 구성

메시지가 DLQ로 가는 조건:

1. Consumer가 `reject` 또는 `nack`(requeue=false)
2. 메시지 TTL 만료
3. 큐의 max-length 초과

```java
// DLX와 DLQ 선언
channel.exchangeDeclare("dlx.exchange", "direct");
channel.queueDeclare("dlq.queue", true, false, false, null);
channel.queueBind("dlq.queue", "dlx.exchange", "dlx.routing.key");

// 원본 큐에 DLX 설정
Map<String, Object> args = new HashMap<>();
args.put("x-dead-letter-exchange", "dlx.exchange");
args.put("x-dead-letter-routing-key", "dlx.routing.key");
args.put("x-message-ttl", 60000); // 60초 후 만료 → DLQ로
channel.queueDeclare("my.queue", true, false, false, args);
```

DLQ에 들어간 메시지의 `x-death` 헤더를 보면 어디서 왜 dead letter가 됐는지 알 수 있다.

```java
@RabbitListener(queues = "dlq.queue")
public void handleDeadLetter(Message message) {
    List<Map<String, Object>> xDeath = 
        (List<Map<String, Object>>) message.getMessageProperties().getHeaders().get("x-death");
    
    if (xDeath != null) {
        Map<String, Object> death = xDeath.get(0);
        String reason = (String) death.get("reason");    // rejected, expired, maxlen
        String queue = (String) death.get("queue");       // 원본 큐 이름
        Long count = (Long) death.get("count");           // dead letter된 횟수
        // 로깅 또는 알림
    }
}
```

---

## 운영 시 자주 겪는 문제

### Channel leak

Connection은 살아있는데 Channel이 계속 늘어나는 경우. 보통 Channel을 열고 닫지 않는 코드 버그다. Management UI에서 Connection당 Channel 수를 확인한다.

Spring AMQP의 `CachingConnectionFactory`를 쓰면 Channel이 풀로 관리되니까 직접 Channel을 열고 닫을 일이 없다. 직접 AMQP Client를 쓰는 경우 try-with-resources로 Channel을 닫아야 한다.

### Unacked 메시지 증가

`messages_unacknowledged`가 계속 증가하면 Consumer가 ack를 보내지 않는 것이다. 처리가 느린 건지 ack 코드를 빼먹은 건지 확인해야 한다. Consumer가 죽으면 해당 Consumer의 unacked 메시지는 다시 큐로 돌아간다.

### 큐 메시지 폭증

Consumer보다 Publisher가 빠르면 메시지가 계속 쌓인다. Memory Alarm이 발생하기 전에 `x-max-length`나 `x-max-length-bytes`로 큐 크기 제한을 걸어두면 overflow 시 DLQ로 보내거나 head 메시지를 버릴 수 있다.

```java
Map<String, Object> args = new HashMap<>();
args.put("x-max-length", 100000);
args.put("x-overflow", "reject-publish"); // 큐 가득 차면 publisher에게 nack
// 또는 "drop-head": 가장 오래된 메시지 버림
```
