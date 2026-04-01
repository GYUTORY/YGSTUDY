---
title: 분산 트랜잭션
tags: [database, distributed-transaction, 2pc, saga, tcc, outbox, compensation, eventual-consistency]
updated: 2026-04-01
---

# 분산 트랜잭션

## 개요

단일 DB에서는 `BEGIN → COMMIT/ROLLBACK`으로 트랜잭션을 처리한다. 그런데 서비스가 쪼개지면서 주문 DB, 결제 DB, 재고 DB가 각각 다른 서버에 있는 상황이 된다. 이때 "주문 생성 → 결제 처리 → 재고 차감"을 하나의 트랜잭션처럼 묶는 건 단일 DB의 트랜잭션으로는 불가능하다.

```
단일 DB:
  BEGIN
    INSERT INTO orders ...
    UPDATE payments ...
    UPDATE inventory ...
  COMMIT  ← 하나의 DB 커넥션에서 처리

분산 환경:
  주문 서비스 (DB-A) → INSERT INTO orders ...
  결제 서비스 (DB-B) → INSERT INTO payments ...
  재고 서비스 (DB-C) → UPDATE inventory ...
  → 각각 다른 DB. 하나가 실패하면 나머지는 어떻게 되돌리나?
```

분산 트랜잭션의 핵심 문제는 **부분 실패(Partial Failure)**다. 3개 서비스 중 2개는 성공하고 1개만 실패했을 때, 성공한 2개를 어떻게 되돌릴 것인가. 이걸 해결하는 패턴들을 하나씩 살펴본다.


## 2PC (Two-Phase Commit)

분산 트랜잭션의 가장 고전적인 방법이다. 코디네이터(Coordinator)가 참여 노드들에게 "커밋할 준비 됐나?"를 물어보고, 전부 OK면 커밋, 하나라도 NO면 전체 롤백한다.

### 동작 방식

```
Phase 1 (Prepare / Vote):
  코디네이터 → 참여자 A: "커밋 준비해라"
  코디네이터 → 참여자 B: "커밋 준비해라"
  코디네이터 → 참여자 C: "커밋 준비해라"

  참여자 A → 코디네이터: "OK, 준비 완료" (redo/undo log 기록, lock 유지)
  참여자 B → 코디네이터: "OK, 준비 완료"
  참여자 C → 코디네이터: "NO, 실패"

Phase 2 (Commit / Abort):
  C가 NO → 코디네이터가 전체 ABORT 결정
  코디네이터 → 참여자 A: "ROLLBACK"
  코디네이터 → 참여자 B: "ROLLBACK"
  코디네이터 → 참여자 C: "ROLLBACK"
```

### 실제 구현 예시 (Spring + JTA)

```java
// JTA를 사용한 2PC - 여러 DataSource를 하나의 트랜잭션으로 묶음
@Configuration
public class XADataSourceConfig {

    @Bean
    public DataSource orderDataSource() {
        AtomikosDataSourceBean ds = new AtomikosDataSourceBean();
        ds.setUniqueResourceName("orderDB");
        ds.setXaDataSourceClassName("com.mysql.cj.jdbc.MysqlXADataSource");
        ds.setPoolSize(10);
        Properties props = new Properties();
        props.put("url", "jdbc:mysql://order-db:3306/orders");
        ds.setXaProperties(props);
        return ds;
    }

    @Bean
    public DataSource paymentDataSource() {
        AtomikosDataSourceBean ds = new AtomikosDataSourceBean();
        ds.setUniqueResourceName("paymentDB");
        ds.setXaDataSourceClassName("com.mysql.cj.jdbc.MysqlXADataSource");
        ds.setPoolSize(10);
        Properties props = new Properties();
        props.put("url", "jdbc:mysql://payment-db:3306/payments");
        ds.setXaProperties(props);
        return ds;
    }
}

@Service
public class OrderService {

    @Transactional  // JtaTransactionManager가 2PC 처리
    public void createOrder(OrderRequest request) {
        // 주문 DB에 INSERT
        orderRepository.save(new Order(request));
        // 결제 DB에 INSERT - 다른 DataSource지만 같은 트랜잭션
        paymentRepository.save(new Payment(request));
        // 둘 중 하나라도 실패하면 양쪽 다 롤백
    }
}
```

### 2PC의 문제점

실무에서 2PC를 쓰면 바로 부딪히는 문제들이 있다.

**1. Blocking 문제**
Prepare 단계에서 참여자가 lock을 잡고 코디네이터의 Commit/Abort 결정을 기다린다. 코디네이터가 죽으면 참여자는 lock을 잡은 채로 무한 대기한다. 그 동안 해당 row에 접근하는 다른 트랜잭션은 전부 멈춘다.

```
참여자 A: Prepare OK → lock 잡은 상태로 대기
코디네이터: (네트워크 단절 or 서버 다운)
참여자 A: Commit? Rollback? 결정을 못 받음 → lock 유지한 채 대기
  → 이 row를 읽으려는 다른 요청 전부 타임아웃
```

**2. 코디네이터 단일 장애점(SPOF)**
코디네이터 하나가 전체 트랜잭션의 생사를 결정한다. 코디네이터가 Prepare 응답을 다 받고, Commit을 보내기 직전에 죽으면 참여자들은 결정을 모른다.

**3. 성능 저하**
네트워크 왕복이 최소 4번(Prepare 요청 → Prepare 응답 → Commit 요청 → Commit 응답) 필요하고, 그 사이에 lock이 유지된다. 트래픽이 몰리면 lock 경합이 심해지면서 처리량이 급락한다.

이런 이유로 마이크로서비스 환경에서는 2PC 대신 Saga 패턴을 주로 쓴다.


## Saga 패턴

Saga는 분산 트랜잭션을 **여러 개의 로컬 트랜잭션**으로 쪼개고, 중간에 실패하면 **보상 트랜잭션(Compensation Transaction)**을 실행해서 이전 단계를 되돌리는 방식이다.

```
정상 흐름:
  T1(주문 생성) → T2(결제 처리) → T3(재고 차감) → 완료

T3 실패 시:
  T1(주문 생성) → T2(결제 처리) → T3(재고 차감 실패!)
                                  → C2(결제 취소) → C1(주문 취소)
```

핵심은 각 로컬 트랜잭션이 **즉시 커밋**된다는 점이다. 2PC처럼 lock을 잡고 기다리지 않는다. 대신 실패 시 보상으로 되돌린다.

### Choreography 방식

중앙 조율자 없이, 각 서비스가 이벤트를 발행하고 다음 서비스가 그 이벤트를 구독해서 자기 작업을 수행한다.

```
주문 서비스 → "주문 생성됨" 이벤트 발행
결제 서비스 → 이벤트 수신 → 결제 처리 → "결제 완료됨" 이벤트 발행
재고 서비스 → 이벤트 수신 → 재고 차감 → "재고 차감됨" 이벤트 발행

재고 차감 실패 시:
재고 서비스 → "재고 차감 실패" 이벤트 발행
결제 서비스 → 이벤트 수신 → 결제 취소 → "결제 취소됨" 이벤트 발행
주문 서비스 → 이벤트 수신 → 주문 취소
```

```java
// 주문 서비스 - 이벤트 발행
@Service
public class OrderService {

    private final ApplicationEventPublisher eventPublisher;
    private final OrderRepository orderRepository;

    @Transactional
    public Order createOrder(OrderRequest request) {
        Order order = Order.create(request);
        order.setStatus(OrderStatus.PENDING);
        orderRepository.save(order);

        // 로컬 트랜잭션 커밋 후 이벤트 발행
        eventPublisher.publishEvent(new OrderCreatedEvent(order.getId(), request.getAmount()));
        return order;
    }

    // 보상 트랜잭션 - 결제 실패 시 주문 취소
    @TransactionalEventListener
    public void handlePaymentFailed(PaymentFailedEvent event) {
        Order order = orderRepository.findById(event.getOrderId())
            .orElseThrow();
        order.setStatus(OrderStatus.CANCELLED);
        orderRepository.save(order);
    }
}

// 결제 서비스 - 이벤트 구독 및 처리
@Service
public class PaymentService {

    @KafkaListener(topics = "order-created")
    @Transactional
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            Payment payment = Payment.process(event.getOrderId(), event.getAmount());
            paymentRepository.save(payment);

            kafkaTemplate.send("payment-completed",
                new PaymentCompletedEvent(event.getOrderId(), payment.getId()));
        } catch (InsufficientBalanceException e) {
            // 결제 실패 → 보상 이벤트 발행
            kafkaTemplate.send("payment-failed",
                new PaymentFailedEvent(event.getOrderId(), e.getMessage()));
        }
    }

    // 재고 차감 실패 시 결제 취소 (보상 트랜잭션)
    @KafkaListener(topics = "inventory-failed")
    @Transactional
    public void handleInventoryFailed(InventoryFailedEvent event) {
        Payment payment = paymentRepository.findByOrderId(event.getOrderId())
            .orElseThrow();
        payment.cancel();  // 환불 처리
        paymentRepository.save(payment);

        kafkaTemplate.send("payment-cancelled",
            new PaymentCancelledEvent(event.getOrderId()));
    }
}
```

Choreography의 문제는 **서비스가 3~4개만 넘어가도 이벤트 흐름을 추적하기 어렵다**는 점이다. 어떤 이벤트가 어디서 발행되고 누가 구독하는지 코드만 봐서는 전체 흐름이 안 보인다. 서비스 간 순환 의존성이 생기기도 한다.


### Orchestration 방식

중앙의 Saga Orchestrator가 전체 흐름을 관리한다. 각 서비스에게 "이거 해라"라고 지시하고, 응답을 받아서 다음 단계를 결정한다.

```
Orchestrator → 주문 서비스: "주문 생성해라"
Orchestrator ← 주문 서비스: "완료"
Orchestrator → 결제 서비스: "결제 처리해라"
Orchestrator ← 결제 서비스: "완료"
Orchestrator → 재고 서비스: "재고 차감해라"
Orchestrator ← 재고 서비스: "실패"
Orchestrator → 결제 서비스: "결제 취소해라"  ← 보상
Orchestrator → 주문 서비스: "주문 취소해라"  ← 보상
```

```java
// Saga Orchestrator - 상태 머신 기반 구현
@Service
public class OrderSagaOrchestrator {

    private final OrderServiceClient orderClient;
    private final PaymentServiceClient paymentClient;
    private final InventoryServiceClient inventoryClient;
    private final SagaStateRepository sagaStateRepository;

    public void execute(OrderRequest request) {
        String sagaId = UUID.randomUUID().toString();
        SagaState state = new SagaState(sagaId, SagaStep.ORDER_CREATE);
        sagaStateRepository.save(state);

        try {
            // Step 1: 주문 생성
            OrderResult orderResult = orderClient.createOrder(request);
            state.setOrderId(orderResult.getOrderId());
            state.setStep(SagaStep.PAYMENT_PROCESS);
            sagaStateRepository.save(state);

            // Step 2: 결제 처리
            PaymentResult paymentResult = paymentClient.processPayment(
                orderResult.getOrderId(), request.getAmount());
            state.setPaymentId(paymentResult.getPaymentId());
            state.setStep(SagaStep.INVENTORY_DEDUCT);
            sagaStateRepository.save(state);

            // Step 3: 재고 차감
            inventoryClient.deductStock(request.getProductId(), request.getQuantity());
            state.setStep(SagaStep.COMPLETED);
            sagaStateRepository.save(state);

        } catch (Exception e) {
            compensate(state);
        }
    }

    private void compensate(SagaState state) {
        // 현재 단계에서 역순으로 보상 실행
        switch (state.getStep()) {
            case INVENTORY_DEDUCT:
                // 재고 차감 실패 → 결제 취소 필요
                paymentClient.cancelPayment(state.getPaymentId());
                // fall through
            case PAYMENT_PROCESS:
                // 결제 처리 실패 → 주문 취소 필요
                orderClient.cancelOrder(state.getOrderId());
                // fall through
            case ORDER_CREATE:
                break;
        }
        state.setStep(SagaStep.COMPENSATED);
        sagaStateRepository.save(state);
    }
}
```

Orchestration은 흐름이 한 곳에서 보여서 디버깅이 쉽다. 대신 Orchestrator가 단일 장애점이 될 수 있고, Orchestrator 자체의 상태 관리가 필요하다.

### Choreography vs Orchestration 비교

| 기준 | Choreography | Orchestration |
|------|-------------|---------------|
| 흐름 제어 | 각 서비스가 알아서 | 중앙 오케스트레이터 |
| 결합도 | 이벤트를 통한 느슨한 결합 | 오케스트레이터에 의존 |
| 디버깅 | 이벤트 추적이 어려움 | 한 곳에서 흐름 확인 |
| 서비스 수가 적을 때 | 간단하고 빠름 | 오버엔지니어링 |
| 서비스 수가 많을 때 | 이벤트 스파게티 | 관리가 수월 |
| 장애점 | 분산됨 | 오케스트레이터가 SPOF |

3~4개 서비스 이하의 단순한 흐름은 Choreography로 충분하다. 그 이상이거나 조건 분기가 복잡하면 Orchestration이 맞다.


## TCC 패턴 (Try-Confirm-Cancel)

TCC는 비즈니스 로직 수준에서 2PC를 구현한 패턴이다. DB 레벨의 lock 대신 **비즈니스 레벨의 리소스 예약**을 사용한다.

```
Try 단계: 리소스 예약 (실제 차감은 안 함)
  - 재고: 10개 중 2개를 "예약" 상태로 변경
  - 결제: 잔액에서 금액을 "동결" 처리
  - 좌석: 해당 좌석을 "임시 점유"

Confirm 단계: 예약을 확정
  - 재고: "예약" → "차감 완료"
  - 결제: "동결" → "결제 완료"
  - 좌석: "임시 점유" → "확정"

Cancel 단계: 예약을 취소
  - 재고: "예약" → 원복
  - 결제: "동결" → 잔액 복원
  - 좌석: "임시 점유" → 해제
```

```java
// 재고 서비스 - TCC 인터페이스 구현
@Service
public class InventoryTccService {

    // Try: 재고 예약
    @Transactional
    public String tryReserve(String productId, int quantity) {
        Inventory inventory = inventoryRepository.findByProductIdForUpdate(productId);

        if (inventory.getAvailable() < quantity) {
            throw new InsufficientStockException();
        }

        // 가용 재고에서 빼고, 예약 재고에 넣음
        inventory.setAvailable(inventory.getAvailable() - quantity);
        inventory.setReserved(inventory.getReserved() + quantity);
        inventoryRepository.save(inventory);

        // 예약 ID 반환 (나중에 Confirm/Cancel 할 때 필요)
        String reservationId = UUID.randomUUID().toString();
        reservationRepository.save(new Reservation(reservationId, productId, quantity));
        return reservationId;
    }

    // Confirm: 예약 확정 → 실제 차감
    @Transactional
    public void confirm(String reservationId) {
        Reservation reservation = reservationRepository.findById(reservationId)
            .orElseThrow();

        if (reservation.getStatus() != ReservationStatus.PENDING) {
            return;  // 멱등성 보장 - 이미 처리된 경우 무시
        }

        Inventory inventory = inventoryRepository.findByProductIdForUpdate(
            reservation.getProductId());
        inventory.setReserved(inventory.getReserved() - reservation.getQuantity());
        inventoryRepository.save(inventory);

        reservation.setStatus(ReservationStatus.CONFIRMED);
        reservationRepository.save(reservation);
    }

    // Cancel: 예약 취소 → 가용 재고 복원
    @Transactional
    public void cancel(String reservationId) {
        Reservation reservation = reservationRepository.findById(reservationId)
            .orElseThrow();

        if (reservation.getStatus() != ReservationStatus.PENDING) {
            return;  // 멱등성 보장
        }

        Inventory inventory = inventoryRepository.findByProductIdForUpdate(
            reservation.getProductId());
        inventory.setAvailable(inventory.getAvailable() + reservation.getQuantity());
        inventory.setReserved(inventory.getReserved() - reservation.getQuantity());
        inventoryRepository.save(inventory);

        reservation.setStatus(ReservationStatus.CANCELLED);
        reservationRepository.save(reservation);
    }
}
```

### TCC 구현 시 주의사항

**1. 멱등성(Idempotency)은 필수다**

Confirm이나 Cancel 요청이 네트워크 문제로 중복 전달될 수 있다. 같은 reservationId로 Confirm을 두 번 호출해도 결과가 같아야 한다. 위 코드에서 `status != PENDING`이면 무시하는 부분이 멱등성 처리다.

**2. Try 타임아웃 처리**

Try 후 Confirm도 Cancel도 안 오는 경우가 있다. 이러면 리소스가 "예약" 상태로 영원히 잠긴다. 스케줄러를 돌려서 일정 시간(예: 5분) 이상 PENDING 상태인 예약을 자동 Cancel 해야 한다.

```java
@Scheduled(fixedRate = 60000)  // 1분마다 실행
public void cleanupExpiredReservations() {
    LocalDateTime threshold = LocalDateTime.now().minusMinutes(5);
    List<Reservation> expired = reservationRepository
        .findByStatusAndCreatedAtBefore(ReservationStatus.PENDING, threshold);

    for (Reservation reservation : expired) {
        cancel(reservation.getId());
        log.warn("Expired reservation auto-cancelled: {}", reservation.getId());
    }
}
```

**3. Confirm/Cancel 실패 시**

네트워크 오류 등으로 Confirm이나 Cancel 자체가 실패하는 경우가 있다. 이때는 재시도 로직이 필수다. 재시도가 계속 실패하면 수동 개입이 필요하니, 알림과 함께 별도 테이블에 기록해 두는 게 좋다.


## Outbox 패턴

Saga를 구현하다 보면 빠지기 쉬운 함정이 있다. "DB에 저장하고 이벤트를 발행한다"는 두 동작이 원자적이지 않다는 점이다.

```
문제 상황:
  1. orderRepository.save(order)  → 성공 (DB 커밋 됨)
  2. kafkaTemplate.send(event)    → 실패 (Kafka 다운)
  → DB에는 주문이 있는데, 이벤트는 안 나감
  → 결제 서비스는 주문이 생긴 걸 모름 → 정합성 깨짐

반대 상황:
  1. kafkaTemplate.send(event)    → 성공
  2. orderRepository.save(order)  → 실패 (DB 다운)
  → 이벤트는 나갔는데 주문은 없음 → 정합성 깨짐
```

Outbox 패턴은 이 문제를 **이벤트를 같은 DB 트랜잭션에 함께 저장**하는 방식으로 해결한다.

### 동작 방식

```
1. 비즈니스 데이터와 이벤트를 같은 DB 트랜잭션으로 저장
   BEGIN
     INSERT INTO orders (...)          -- 주문 저장
     INSERT INTO outbox_events (...)   -- 이벤트도 같은 DB에 저장
   COMMIT

2. 별도 프로세스가 outbox_events 테이블을 폴링해서 메시지 브로커로 발행
   Outbox Relay → SELECT * FROM outbox_events WHERE published = false
                → Kafka에 발행
                → UPDATE outbox_events SET published = true
```

### 구현

```sql
-- Outbox 테이블
CREATE TABLE outbox_events (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,   -- 예: "Order"
    aggregate_id   VARCHAR(100) NOT NULL,   -- 예: 주문 ID
    event_type    VARCHAR(100) NOT NULL,    -- 예: "OrderCreated"
    payload       JSON NOT NULL,            -- 이벤트 데이터
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published     BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_outbox_unpublished ON outbox_events(published, created_at);
```

```java
// 비즈니스 로직과 이벤트를 같은 트랜잭션으로 저장
@Service
public class OrderService {

    @Transactional  // 하나의 트랜잭션
    public Order createOrder(OrderRequest request) {
        // 비즈니스 데이터 저장
        Order order = Order.create(request);
        orderRepository.save(order);

        // 같은 트랜잭션에서 Outbox에 이벤트 저장
        OutboxEvent event = OutboxEvent.builder()
            .aggregateType("Order")
            .aggregateId(order.getId())
            .eventType("OrderCreated")
            .payload(objectMapper.writeValueAsString(
                new OrderCreatedPayload(order.getId(), request.getAmount())))
            .build();
        outboxEventRepository.save(event);

        return order;
    }
}

// Outbox Relay - 폴링 방식
@Component
public class OutboxRelay {

    @Scheduled(fixedDelay = 1000)  // 1초마다 폴링
    @Transactional
    public void publishEvents() {
        List<OutboxEvent> events = outboxEventRepository
            .findTop100ByPublishedFalseOrderByCreatedAtAsc();

        for (OutboxEvent event : events) {
            try {
                kafkaTemplate.send(
                    event.getAggregateType() + "." + event.getEventType(),
                    event.getAggregateId(),
                    event.getPayload()
                ).get();  // 동기 방식으로 발행 확인

                event.setPublished(true);
                outboxEventRepository.save(event);
            } catch (Exception e) {
                log.error("Failed to publish outbox event: {}", event.getId(), e);
                break;  // 순서 보장을 위해 실패하면 중단
            }
        }
    }
}
```

### CDC (Change Data Capture) 방식

폴링 대신 DB의 변경 로그를 직접 읽어서 이벤트를 발행하는 방법도 있다. Debezium 같은 도구가 MySQL의 binlog나 PostgreSQL의 WAL을 읽어서 outbox_events 테이블의 INSERT를 감지하고, 자동으로 Kafka에 발행한다.

```
Debezium 방식:
  orderRepository.save(order)     ← 같은 트랜잭션
  outboxEventRepository.save(event)  ← 같은 트랜잭션

  Debezium → MySQL binlog 감시 → outbox_events INSERT 감지 → Kafka에 발행
```

폴링보다 지연이 적고 DB 부하도 줄어든다. 다만 Debezium 자체를 운영해야 하니 인프라 복잡도가 올라간다. 트래픽이 적으면 폴링으로 시작하고, 지연이 문제 되면 CDC로 전환하는 게 현실적이다.


## 부분 정합성 깨짐: 실제로 겪는 문제들

패턴을 아무리 잘 설계해도, 분산 환경에서는 정합성이 깨지는 순간이 온다. 자주 발생하는 케이스와 대응 방법을 정리한다.

### 1. 보상 트랜잭션 자체가 실패하는 경우

재고 차감이 실패해서 결제 취소(보상)를 시도하는데, 결제 서비스도 장애인 경우.

```
주문 생성 (성공) → 결제 처리 (성공) → 재고 차감 (실패)
  → 결제 취소 시도 → 결제 서비스 다운!
  → 결제는 됐는데 주문은 취소, 재고도 안 빠짐
```

**대응**: 보상 트랜잭션은 반드시 **재시도 가능한 구조**로 만들어야 한다. 실패한 보상을 별도 테이블에 저장해두고, 스케줄러가 성공할 때까지 재시도한다.

```java
@Entity
public class PendingCompensation {
    @Id
    private String id;
    private String sagaId;
    private String serviceType;      // "PAYMENT", "ORDER"
    private String compensationData;  // JSON
    private int retryCount;
    private LocalDateTime nextRetryAt;
    private CompensationStatus status; // PENDING, COMPLETED, FAILED_PERMANENTLY
}

@Scheduled(fixedRate = 30000)
public void retryFailedCompensations() {
    List<PendingCompensation> pending = compensationRepository
        .findByStatusAndNextRetryAtBefore(
            CompensationStatus.PENDING, LocalDateTime.now());

    for (PendingCompensation comp : pending) {
        try {
            executeCompensation(comp);
            comp.setStatus(CompensationStatus.COMPLETED);
        } catch (Exception e) {
            comp.setRetryCount(comp.getRetryCount() + 1);

            if (comp.getRetryCount() >= 10) {
                // 10번 이상 실패 → 사람이 개입해야 함
                comp.setStatus(CompensationStatus.FAILED_PERMANENTLY);
                alertService.sendAlert("보상 트랜잭션 영구 실패: " + comp.getId());
            } else {
                // 지수 백오프로 재시도 간격 늘리기
                long delaySeconds = (long) Math.pow(2, comp.getRetryCount()) * 10;
                comp.setNextRetryAt(LocalDateTime.now().plusSeconds(delaySeconds));
            }
        }
        compensationRepository.save(comp);
    }
}
```

### 2. 이벤트 순서가 꼬이는 경우

Kafka 파티션이 여러 개면 같은 주문에 대한 이벤트 순서가 보장되지 않는다.

```
실제 발생 순서: 주문 생성 → 주문 취소
Kafka 수신 순서: 주문 취소 → 주문 생성
  → 결제 서비스: "없는 주문인데 취소?" → 무시
  → 그 다음 "주문 생성됨" → 결제 처리
  → 이미 취소된 주문인데 결제가 됨
```

**대응**: 같은 aggregate(예: 같은 주문 ID)의 이벤트는 같은 Kafka 파티션으로 보내야 한다. 주문 ID를 파티션 키로 사용하면 해당 주문의 이벤트 순서가 보장된다.

```java
// 주문 ID를 키로 사용 → 같은 파티션으로 전송
kafkaTemplate.send("order-events", order.getId(), eventPayload);
```

### 3. 중복 이벤트 처리

네트워크 재시도나 컨슈머 리밸런싱으로 같은 이벤트가 두 번 올 수 있다.

```
"결제 처리해라" 이벤트가 2번 도착
  → 1차: 10만원 결제 성공
  → 2차: 10만원 또 결제 → 20만원 결제됨!
```

**대응**: 모든 이벤트 처리에 멱등성 키를 적용한다.

```java
@KafkaListener(topics = "order-created")
@Transactional
public void handleOrderCreated(OrderCreatedEvent event) {
    // 이미 처리한 이벤트인지 확인
    if (processedEventRepository.existsByEventId(event.getEventId())) {
        log.info("이미 처리된 이벤트, 무시: {}", event.getEventId());
        return;
    }

    // 비즈니스 로직 실행
    Payment payment = Payment.process(event.getOrderId(), event.getAmount());
    paymentRepository.save(payment);

    // 처리 완료 기록 (같은 트랜잭션)
    processedEventRepository.save(new ProcessedEvent(event.getEventId()));
}
```

### 4. 타이밍 이슈로 인한 데이터 불일치

주문 서비스에서 주문을 생성하고 이벤트를 발행했는데, 사용자가 그 사이에 주문 상세를 조회하면 결제 상태는 아직 "대기 중"이다. 이건 버그가 아니라 **최종 일관성(Eventual Consistency)**의 특성이다.

```
시간 ---→
  T1: 주문 생성 (주문 서비스)
  T2: 사용자가 주문 조회 → 결제 상태: "대기중" (아직 처리 안 됨)
  T3: 결제 처리 완료 (결제 서비스)
  T4: 사용자가 주문 조회 → 결제 상태: "완료"
```

**대응**: UI에서 "처리 중" 상태를 보여주고, 폴링이나 웹소켓으로 상태 변화를 알려주는 게 일반적이다. API 레벨에서는 주문 조회 시 결제 서비스에도 실시간으로 물어볼지, 캐시된 상태를 보여줄지 판단해야 한다. 대부분의 경우 캐시된 상태 + 비동기 갱신이면 충분하다.


## 패턴 선택 기준

| 상황 | 적합한 패턴 |
|------|-----------|
| DB가 2~3개이고 강한 일관성이 필요 | 2PC (JTA) |
| 마이크로서비스, 서비스 3개 이하 | Saga (Choreography) |
| 마이크로서비스, 서비스 4개 이상 | Saga (Orchestration) |
| 리소스 예약이 핵심인 도메인 (좌석, 재고) | TCC |
| DB 저장과 이벤트 발행의 원자성이 필요 | Outbox |

실무에서는 보통 **Saga + Outbox**를 조합해서 쓴다. Saga로 서비스 간 흐름을 관리하고, 각 서비스의 이벤트 발행은 Outbox 패턴으로 안전하게 처리하는 구조다. TCC는 티켓 예매나 좌석 선점처럼 "예약 → 확정" 흐름이 자연스러운 도메인에서 쓰인다.

어떤 패턴을 쓰든, 분산 환경에서 100% 정합성은 없다. 결국 **멱등성, 재시도, 모니터링, 수동 보정 도구**가 분산 트랜잭션의 실질적인 안전망이다.
