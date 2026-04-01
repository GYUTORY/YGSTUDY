---
title: 메시지 큐 & 이벤트 기반 아키텍처
tags: [backend, messaging, kafka, rabbitmq, event-driven, pub-sub, message-queue, async]
updated: 2026-04-02
---

# 메시지 큐 & 이벤트 기반 아키텍처

## 개요

메시지 큐는 서비스 간 **비동기 통신**을 가능하게 하는 미들웨어이다. 생산자(Producer)가 메시지를 큐에 넣으면, 소비자(Consumer)가 자신의 속도로 처리한다. 마이크로서비스 간 결합도를 낮추고 시스템 안정성을 높인다.

### 왜 필요한가

```
동기 방식 (HTTP 직접 호출):
  주문 서비스 → 결제 서비스 → 재고 서비스 → 알림 서비스
  ❌ 하나라도 실패하면 전체 실패
  ❌ 느린 서비스가 전체를 지연
  ❌ 서비스 간 강결합

비동기 방식 (메시지 큐):
  주문 서비스 → [메시지 큐] → 결제 서비스 (독립 처리)
                            → 재고 서비스 (독립 처리)
                            → 알림 서비스 (독립 처리)
  ✅ 서비스 독립적으로 처리
  ✅ 실패 시 재시도 가능
  ✅ 느슨한 결합
```

### 핵심 패턴

| 패턴 | 설명 | 사용 예 |
|------|------|---------|
| **Point-to-Point** | 1 Producer → 1 Consumer | 작업 큐, 배치 처리 |
| **Pub/Sub** | 1 Producer → N Consumer | 이벤트 브로드캐스트 |
| **Request-Reply** | 요청 후 응답 대기 | RPC 대체 |
| **Dead Letter Queue** | 처리 실패 메시지 격리 | 에러 분석, 재처리 |

## 핵심

### 1. Kafka vs RabbitMQ 비교

| 항목 | Apache Kafka | RabbitMQ |
|------|-------------|----------|
| **모델** | 분산 로그 (이벤트 스트리밍) | 메시지 브로커 (전통적 큐) |
| **처리량** | 초당 수백만 건 | 초당 수만 건 |
| **메시지 보존** | 디스크에 영구 보존 (설정 기간) | 소비 후 삭제 (기본) |
| **순서 보장** | 파티션 내 보장 | 큐 내 보장 |
| **Consumer 그룹** | 네이티브 지원 | 플러그인 필요 |
| **프로토콜** | 자체 프로토콜 | AMQP, MQTT, STOMP |
| **재처리** | offset 리셋으로 재처리 가능 | 불가 (소비 후 삭제) |
| **학습 곡선** | 높음 | 낮음 |
| **적합한 상황** | 이벤트 소싱, 로그 수집, 실시간 스트리밍 | 작업 큐, RPC, 라우팅 |

📌 **선택 기준**: 이벤트를 **저장하고 재처리**해야 하면 Kafka, 단순 **작업 분배**면 RabbitMQ.

### 2. Apache Kafka

#### 아키텍처

```
Producer ──▶ Broker Cluster ──▶ Consumer Group
               │
        ┌──────┼──────┐
     Topic A  Topic B  Topic C
        │
   ┌────┼────┐
  P0   P1   P2        (Partitions)
```

| 개념 | 설명 |
|------|------|
| **Topic** | 메시지 카테고리 (예: `order-events`, `user-events`) |
| **Partition** | Topic을 나눈 단위. 병렬 처리의 기본 |
| **Offset** | 파티션 내 메시지 위치 (번호) |
| **Consumer Group** | 같은 그룹은 파티션을 나눠 소비 (로드밸런싱) |
| **Broker** | Kafka 서버 인스턴스 |
| **Replication** | 파티션 복제본으로 장애 대응 |

#### Spring Boot + Kafka 예시

```yaml
# application.yml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
    consumer:
      group-id: order-service
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "com.example.event"
```

```java
// 이벤트 정의
public record OrderCreatedEvent(
    Long orderId,
    Long userId,
    int totalPrice,
    LocalDateTime createdAt
) {}

// Producer
@Service
@RequiredArgsConstructor
public class OrderEventPublisher {

    private final KafkaTemplate<String, OrderCreatedEvent> kafkaTemplate;

    public void publishOrderCreated(Order order) {
        OrderCreatedEvent event = new OrderCreatedEvent(
            order.getId(), order.getUserId(),
            order.getTotalPrice(), LocalDateTime.now());

        kafkaTemplate.send("order-events", order.getId().toString(), event)
            .whenComplete((result, ex) -> {
                if (ex != null) {
                    log.error("이벤트 발행 실패: orderId={}", order.getId(), ex);
                } else {
                    log.info("이벤트 발행 성공: topic={}, offset={}",
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().offset());
                }
            });
    }
}

// Consumer
@Service
@Slf4j
public class OrderEventConsumer {

    @KafkaListener(topics = "order-events", groupId = "notification-service")
    public void handleOrderCreated(OrderCreatedEvent event) {
        log.info("주문 이벤트 수신: orderId={}", event.orderId());
        // 알림 발송, 포인트 적립 등
        notificationService.sendOrderConfirmation(event.userId(), event.orderId());
    }

    // 에러 처리
    @KafkaListener(topics = "order-events", groupId = "inventory-service")
    public void handleInventoryUpdate(OrderCreatedEvent event) {
        try {
            inventoryService.decreaseStock(event.orderId());
        } catch (Exception e) {
            log.error("재고 차감 실패: orderId={}", event.orderId(), e);
            // Dead Letter Topic으로 전송하거나 재시도
            throw e;
        }
    }
}
```

### 3. RabbitMQ

#### 아키텍처

```
Producer → Exchange → Binding → Queue → Consumer
              │
         ┌────┼────┐
       Direct  Topic  Fanout    (Exchange Types)
```

| Exchange 타입 | 라우팅 방식 | 사용 예 |
|-------------|-----------|---------|
| **Direct** | routing key 정확히 매칭 | 특정 서비스로 전달 |
| **Topic** | 패턴 매칭 (`order.*`, `#.error`) | 카테고리별 라우팅 |
| **Fanout** | 모든 바인딩된 큐로 브로드캐스트 | 이벤트 알림 |
| **Headers** | 헤더 속성 기반 | 복잡한 라우팅 조건 |

#### Spring Boot + RabbitMQ 기본 예시

```yaml
# application.yml
spring:
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
```

```java
// 설정
@Configuration
public class RabbitConfig {

    @Bean
    public TopicExchange orderExchange() {
        return new TopicExchange("order.exchange");
    }

    @Bean
    public Queue orderCreatedQueue() {
        return QueueBuilder.durable("order.created.queue")
            .withArgument("x-dead-letter-exchange", "dlx.exchange")
            .withArgument("x-dead-letter-routing-key", "dlq.order.created")
            .build();
    }

    @Bean
    public Binding orderCreatedBinding() {
        return BindingBuilder
            .bind(orderCreatedQueue())
            .to(orderExchange())
            .with("order.created");
    }

    @Bean
    public Jackson2JsonMessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}

// Producer
@Service
@RequiredArgsConstructor
public class OrderEventPublisher {

    private final RabbitTemplate rabbitTemplate;

    public void publishOrderCreated(Order order) {
        OrderCreatedEvent event = new OrderCreatedEvent(
            order.getId(), order.getUserId(), order.getTotalPrice());

        rabbitTemplate.convertAndSend(
            "order.exchange",       // exchange
            "order.created",        // routing key
            event);
    }
}

// Consumer
@Service
@Slf4j
public class OrderEventConsumer {

    @RabbitListener(queues = "order.created.queue")
    public void handleOrderCreated(OrderCreatedEvent event) {
        log.info("주문 이벤트 수신: orderId={}", event.orderId());
        notificationService.sendOrderConfirmation(event);
    }
}
```

#### 실무 라우팅 패턴

기본 Exchange 타입만으로 해결 안 되는 상황이 생각보다 빨리 온다. 서비스가 3~4개만 넘어가도 라우팅 구조가 복잡해지는데, RabbitMQ는 이걸 해결하는 몇 가지 패턴을 제공한다.

##### Exchange-to-Exchange (E2E) 바인딩

Exchange끼리 바인딩하는 기능이다. AMQP 스펙이 아니라 RabbitMQ 확장 기능이다.

주문이 들어오면 결제, 재고, 알림 세 시스템에 각각 다른 형태로 라우팅해야 하는 경우를 생각해보자. 하나의 Exchange에서 모든 큐로 바인딩하면 관리가 엉망이 된다. Exchange를 계층 구조로 만들면 각 도메인별로 라우팅 책임을 분리할 수 있다.

```
Producer → order.exchange (topic)
              ├──▶ payment.exchange (direct) → payment.queue
              ├──▶ inventory.exchange (direct) → inventory.queue
              └──▶ notification.exchange (fanout) → email.queue
                                                  → sms.queue
```

```java
@Configuration
public class E2EBindingConfig {

    // 1단계: 메인 Exchange
    @Bean
    public TopicExchange orderExchange() {
        return new TopicExchange("order.exchange");
    }

    // 2단계: 도메인별 하위 Exchange
    @Bean
    public DirectExchange paymentExchange() {
        return new DirectExchange("payment.exchange");
    }

    @Bean
    public FanoutExchange notificationExchange() {
        return new FanoutExchange("notification.exchange");
    }

    // Exchange → Exchange 바인딩
    @Bean
    public Binding orderToPayment() {
        return BindingBuilder
            .bind(paymentExchange())
            .to(orderExchange())
            .with("order.created");
    }

    @Bean
    public Binding orderToNotification() {
        return BindingBuilder
            .bind(notificationExchange())
            .to(orderExchange())
            .with("order.#");  // 주문 관련 모든 이벤트를 알림으로
    }

    // 하위 Exchange → Queue 바인딩
    @Bean
    public Queue paymentQueue() {
        return QueueBuilder.durable("payment.queue").build();
    }

    @Bean
    public Binding paymentBinding() {
        return BindingBuilder
            .bind(paymentQueue())
            .to(paymentExchange())
            .with("order.created");
    }

    @Bean
    public Queue emailQueue() {
        return QueueBuilder.durable("email.queue").build();
    }

    @Bean
    public Queue smsQueue() {
        return QueueBuilder.durable("sms.queue").build();
    }

    @Bean
    public Binding emailBinding() {
        return BindingBuilder.bind(emailQueue()).to(notificationExchange());
    }

    @Bean
    public Binding smsBinding() {
        return BindingBuilder.bind(smsQueue()).to(notificationExchange());
    }
}
```

이 구조의 장점은 알림 채널을 추가할 때 `notification.exchange`에만 큐를 바인딩하면 된다는 점이다. Producer 코드는 건드릴 필요 없다.

##### Alternate Exchange

routing key가 어디에도 매칭되지 않는 메시지가 들어오면 기본적으로 그냥 버려진다. `mandatory` 플래그를 켜면 Publisher에게 반환되지만, Publisher 쪽에서 반환 처리를 해야 해서 번거롭다.

Alternate Exchange는 라우팅 실패한 메시지를 자동으로 다른 Exchange로 보낸다. 메시지 유실을 막으면서도 Publisher 코드를 깔끔하게 유지할 수 있다.

```
Producer → order.exchange (routing key 매칭 실패)
              │
              └── alternate ──▶ unrouted.exchange (fanout) → unrouted.queue
```

```java
@Configuration
public class AlternateExchangeConfig {

    // 라우팅 실패 메시지를 받을 Exchange + Queue
    @Bean
    public FanoutExchange unroutedExchange() {
        return new FanoutExchange("unrouted.exchange");
    }

    @Bean
    public Queue unroutedQueue() {
        return QueueBuilder.durable("unrouted.queue").build();
    }

    @Bean
    public Binding unroutedBinding() {
        return BindingBuilder.bind(unroutedQueue()).to(unroutedExchange());
    }

    // 메인 Exchange에 alternate-exchange 설정
    @Bean
    public TopicExchange orderExchange() {
        return ExchangeBuilder
            .topicExchange("order.exchange")
            .durable(true)
            .alternate("unrouted.exchange")
            .build();
    }
}
```

운영 환경에서 `unrouted.queue`를 모니터링하면 라우팅 설정 실수를 빨리 잡을 수 있다. routing key 오타 같은 문제가 여기서 잡힌다.

##### Consistent Hash Exchange

RabbitMQ 기본 제공이 아니라 플러그인(`rabbitmq_consistent_hash_exchange`)을 활성화해야 한다.

```bash
rabbitmq-plugins enable rabbitmq_consistent_hash_exchange
```

같은 키를 가진 메시지가 항상 같은 큐로 간다. 여러 Consumer 인스턴스가 있을 때, 특정 사용자의 메시지를 항상 같은 Consumer가 처리하게 할 수 있다. 순서 보장이 필요한 상황에서 쓴다.

```
Producer → hash.exchange (x-consistent-hash)
              ├── weight:10 ──▶ worker.queue.1 → Consumer A
              ├── weight:10 ──▶ worker.queue.2 → Consumer B
              └── weight:10 ──▶ worker.queue.3 → Consumer C
```

routing key가 `user-123`이면 항상 같은 큐로 간다. weight 값은 해시 링에서 차지하는 비중이다. 모든 큐에 같은 값을 주면 균등 분배된다.

```java
@Configuration
public class ConsistentHashConfig {

    @Bean
    public CustomExchange hashExchange() {
        Map<String, Object> args = new HashMap<>();
        args.put("hash-header", "user-id");  // 헤더 기반 해싱을 쓸 경우
        return new CustomExchange(
            "hash.exchange",
            "x-consistent-hash",  // Exchange 타입
            true,   // durable
            false,  // auto-delete
            args
        );
    }

    @Bean
    public Queue workerQueue1() {
        return QueueBuilder.durable("worker.queue.1").build();
    }

    @Bean
    public Queue workerQueue2() {
        return QueueBuilder.durable("worker.queue.2").build();
    }

    // routing key 자리에 weight 값을 넣는다
    @Bean
    public Binding hashBinding1() {
        return BindingBuilder
            .bind(workerQueue1())
            .to(hashExchange())
            .with("10")    // weight
            .noargs();
    }

    @Bean
    public Binding hashBinding2() {
        return BindingBuilder
            .bind(workerQueue2())
            .to(hashExchange())
            .with("10")
            .noargs();
    }
}
```

주의할 점이 있다. Consumer 수를 늘리거나 줄이면 해시 링이 재배치된다. 이때 일부 메시지의 라우팅 대상이 바뀌므로, 순서가 중요한 경우 Consumer 수를 쉽게 변경하면 안 된다. Kafka의 파티션 리밸런싱과 비슷한 문제다.

#### DLX + DLQ 전체 흐름

위 기본 예시에서 `x-dead-letter-exchange`를 한 줄 넣는 것만으로는 DLQ가 동작하지 않는다. DLX(Dead Letter Exchange)와 DLQ를 명시적으로 선언하고 바인딩해야 한다.

메시지가 DLX로 가는 조건은 세 가지다:

- Consumer가 `basic.reject` 또는 `basic.nack`으로 메시지를 거부하고 `requeue=false`인 경우
- 메시지 TTL이 만료된 경우
- 큐의 `x-max-length`를 초과한 경우

```
정상 흐름:
  Producer → order.exchange → order.created.queue → Consumer (처리 성공)

실패 흐름:
  Consumer (처리 실패, 3회 재시도 후)
    → order.created.queue에서 reject (requeue=false)
    → dlx.exchange (routing key: dlq.order.created)
    → dlq.order.created.queue
    → DLQ Consumer (로깅, 알림, 수동 재처리)
```

```java
@Configuration
public class DlxConfig {

    // === 정상 처리 경로 ===

    @Bean
    public TopicExchange orderExchange() {
        return new TopicExchange("order.exchange");
    }

    @Bean
    public Queue orderCreatedQueue() {
        return QueueBuilder.durable("order.created.queue")
            .withArgument("x-dead-letter-exchange", "dlx.exchange")
            .withArgument("x-dead-letter-routing-key", "dlq.order.created")
            .withArgument("x-message-ttl", 60000)    // 60초 TTL (선택)
            .withArgument("x-max-length", 10000)      // 큐 최대 길이 (선택)
            .build();
    }

    @Bean
    public Binding orderCreatedBinding() {
        return BindingBuilder
            .bind(orderCreatedQueue())
            .to(orderExchange())
            .with("order.created");
    }

    // === DLX 경로 ===

    @Bean
    public DirectExchange dlxExchange() {
        return new DirectExchange("dlx.exchange");
    }

    @Bean
    public Queue dlqOrderCreatedQueue() {
        // DLQ에도 TTL을 걸어서 일정 시간 후 원래 큐로 재진입시킬 수 있다
        return QueueBuilder.durable("dlq.order.created.queue")
            .withArgument("x-dead-letter-exchange", "order.exchange")
            .withArgument("x-dead-letter-routing-key", "order.created")
            .withArgument("x-message-ttl", 300000)  // 5분 후 원래 큐로 재시도
            .build();
    }

    @Bean
    public Binding dlqBinding() {
        return BindingBuilder
            .bind(dlqOrderCreatedQueue())
            .to(dlxExchange())
            .with("dlq.order.created");
    }
}
```

위 설정에서 `dlq.order.created.queue`에 다시 `x-dead-letter-exchange`를 걸어 원래 Exchange로 보내는 패턴이 "재시도 큐" 패턴이다. 5분 후 자동으로 다시 처리를 시도한다. 무한 루프가 되지 않도록 메시지 헤더의 `x-death` 카운트를 확인해서 최대 재시도 횟수를 제한해야 한다.

```java
@Service
@Slf4j
public class DlqConsumer {

    private static final int MAX_RETRY_COUNT = 3;

    @RabbitListener(queues = "dlq.order.created.queue")
    public void handleDeadLetter(Message message) {
        Map<String, Object> headers = message.getMessageProperties().getHeaders();
        List<Map<String, Object>> xDeath =
            (List<Map<String, Object>>) headers.get("x-death");

        long retryCount = 0;
        if (xDeath != null && !xDeath.isEmpty()) {
            retryCount = (long) xDeath.get(0).get("count");
        }

        if (retryCount >= MAX_RETRY_COUNT) {
            // 최대 재시도 초과 → 파킹 큐로 보내거나 DB에 기록
            log.error("최대 재시도 초과. 메시지 파킹 처리: {}",
                new String(message.getBody()));
            saveToParkingLot(message);
            return;
        }

        log.warn("DLQ 메시지 수신. 재시도 횟수: {}, 메시지: {}",
            retryCount, new String(message.getBody()));
        // TTL 만료 후 자동으로 원래 큐로 재진입
    }

    private void saveToParkingLot(Message message) {
        // DB에 저장하거나 parking-lot 큐로 전송
        // 운영자가 확인 후 수동으로 재처리
    }
}
```

재시도 간격을 점진적으로 늘리고 싶으면 DLQ를 여러 개 만들어서 TTL을 다르게 설정한다. `retry.1.queue` (10초) → `retry.2.queue` (30초) → `retry.3.queue` (5분) 식이다. 구현이 복잡해지므로 Spring의 `RetryTemplate`이나 `spring-retry`를 같이 쓰는 게 관리하기 편하다.

```java
// Spring AMQP 재시도 설정 (SimpleRetryPolicy + DLQ 조합)
@Bean
public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
        ConnectionFactory connectionFactory) {

    SimpleRabbitListenerContainerFactory factory =
        new SimpleRabbitListenerContainerFactory();
    factory.setConnectionFactory(connectionFactory);

    // 3회 재시도, 재시도 간격 1초 → 2초 → 4초 (exponential backoff)
    RetryInterceptorBuilder.StatelessRetryInterceptorBuilder retryBuilder =
        RetryInterceptorBuilder.stateless()
            .maxAttempts(3)
            .backOffOptions(1000, 2.0, 10000);

    // 재시도 모두 실패 시 reject → DLX로 전달
    retryBuilder.recoverer(new RejectAndDontRequeueRecoverer());

    factory.setAdviceChain(retryBuilder.build());
    return factory;
}
```

### 4. 이벤트 기반 아키텍처 패턴

#### Transactional Outbox 패턴

DB 트랜잭션과 메시지 발행의 원자성을 보장하는 패턴이다.

```
문제:
  1. DB에 주문 저장  ← 성공
  2. Kafka에 이벤트 발행  ← 실패  → 불일치!

해결 (Outbox 패턴):
  1. DB 트랜잭션에서 주문 저장 + Outbox 테이블에 이벤트 저장
  2. 별도 프로세스(CDC/Polling)가 Outbox → Kafka로 발행
  3. 발행 완료 후 Outbox 레코드 삭제
```

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;

    @Transactional
    public Order createOrder(CreateOrderRequest request) {
        // 주문 저장
        Order order = orderRepository.save(Order.from(request));

        // 같은 트랜잭션에서 Outbox에 이벤트 저장
        outboxRepository.save(OutboxEvent.builder()
            .aggregateType("Order")
            .aggregateId(order.getId().toString())
            .eventType("OrderCreated")
            .payload(objectMapper.writeValueAsString(
                new OrderCreatedEvent(order.getId(), order.getTotalPrice())))
            .build());

        return order;
    }
}
```

### 5. 에러 처리 전략

| 전략 | 설명 | 적합한 상황 |
|------|------|-----------|
| **재시도** | 일정 횟수 재시도 후 실패 | 일시적 에러 (네트워크, 타임아웃) |
| **Dead Letter Queue** | 실패 메시지를 별도 큐로 이동 | 분석/수동 처리 필요 |
| **Exponential Backoff** | 재시도 간격을 점점 늘림 | 외부 서비스 과부하 방지 |
| **Circuit Breaker** | 연속 실패 시 일시 중단 | 연쇄 장애 방지 |

```java
// Spring Kafka 재시도 설정
@Bean
public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory() {
    ConcurrentKafkaListenerContainerFactory<String, Object> factory = new ConcurrentKafkaListenerContainerFactory<>();
    factory.setConsumerFactory(consumerFactory());
    factory.setCommonErrorHandler(new DefaultErrorHandler(
        new DeadLetterPublishingRecoverer(kafkaTemplate),   // DLT로 전송
        new FixedBackOff(1000L, 3)                          // 1초 간격, 3회 재시도
    ));
    return factory;
}
```

## 운영 팁

### 선택 가이드

| 상황 | 추천 |
|------|------|
| 이벤트 소싱, 로그 수집 | **Kafka** |
| 실시간 스트리밍, 대용량 | **Kafka** |
| 단순 작업 큐, RPC 패턴 | **RabbitMQ** |
| 복잡한 라우팅 규칙 | **RabbitMQ** |
| AWS 관리형 | **SQS/SNS** (간단), **MSK** (Kafka) |

### 주의사항

| 항목 | 주의 |
|------|------|
| **멱등성** | 같은 메시지가 여러 번 처리될 수 있음 → Consumer에 멱등성 보장 |
| **순서 보장** | Kafka: 파티션 내에서만 보장. 주문 키로 같은 파티션 유도 |
| **모니터링** | Consumer Lag(지연) 모니터링 필수 |
| **파티션 수** | Consumer 수 ≤ 파티션 수 (초과 시 놀게 됨) |

## 참고

- [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/)
- [RabbitMQ 공식 문서](https://www.rabbitmq.com/documentation.html)
- [Spring for Apache Kafka](https://docs.spring.io/spring-kafka/reference/)
- [Spring AMQP](https://docs.spring.io/spring-amqp/reference/)
- [메시지 큐 및 분산 락](../Application Architecture/MSA/메시지_큐_및_분산_락.md)
