---
title: 메시지 큐 & 이벤트 기반 아키텍처
tags: [backend, messaging, kafka, rabbitmq, event-driven, pub-sub, message-queue, async]
updated: 2026-03-01
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

#### Spring Boot + RabbitMQ 예시

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
            .withArgument("x-dead-letter-exchange", "dlx.exchange")  // DLQ 설정
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
