---
title: 정합성 검증 시점
tags: [backend, api, architecture, os]
updated: 2026-07-30
---

# 정합성 검증 시점

정합성 검증은 "어디서" 하느냐보다 "언제" 하느냐가 더 중요하다. 검증 시점이 틀리면 잘못된 데이터가 저장되거나, 동시 요청에서 race condition이 발생하거나, 필요 없는 DB 조회가 늘어난다.

## 계층별 책임 분리

### Controller: 형식과 타입

Controller에서는 요청이 "올바른 형식인가"만 확인한다. 필드 타입, 필수 필드 존재 여부, 길이 제한, 이메일·UUID 같은 형식 제약이 이 범위다.

비즈니스 규칙을 Controller에서 검증하면 같은 규칙이 여러 Controller에 중복되고, 규칙이 바뀔 때 Controller를 전부 찾아 수정해야 한다.

```java
@PostMapping("/orders")
public ResponseEntity<OrderResponse> createOrder(
    @Valid @RequestBody CreateOrderRequest request
) {
    // 재고 충분 여부는 여기서 확인하지 않는다
    return ResponseEntity.ok(orderService.createOrder(request));
}

public class CreateOrderRequest {
    @NotNull
    @Positive  // 0보다 큰 양수인지 — 형식 수준의 검증
    private Integer quantity;

    @NotBlank
    private String productId;

    @Email
    private String customerEmail;
}
```

### Service: 비즈니스 규칙

Service에서는 "이 요청이 현재 시스템 상태에서 허용되는가"를 판단한다. 핵심 판단 기준은 엔티티를 로드하기 전에 검증할지, 로드한 후에 검증할지다.

**엔티티 로드 전 검증이 맞는 경우:**
- 요청 자체에서 논리적 모순이 드러날 때 (시작일이 종료일보다 늦은 경우)
- 외부 시스템 상태를 먼저 확인해야 할 때 (결제 수단 유효성)
- 로드 비용이 큰 엔티티를 불필요하게 조회하지 않으려 할 때

```java
public OrderId createOrder(CreateOrderCommand command) {
    // 엔티티 로드 전 — 요청 자체의 논리적 모순
    if (command.getDeliveryDate().isBefore(LocalDate.now())) {
        throw new InvalidDeliveryDateException("과거 날짜로 배송 예약 불가");
    }

    Product product = productRepository.findById(command.getProductId())
        .orElseThrow(ProductNotFoundException::new);

    // 엔티티 로드 후 — 현재 상태에 의존하는 규칙
    if (!product.isAvailable()) {
        throw new ProductUnavailableException();
    }
    if (product.getStock() < command.getQuantity()) {
        throw new InsufficientStockException();
    }

    // ...
}
```

엔티티 로드 순서도 중요하다. 검증에 필요한 데이터가 적은 엔티티를 먼저 로드하고, 무거운 엔티티는 나중에 로드한다. 앞 단계에서 실패하면 뒤 단계 조회 자체가 일어나지 않는다.

### Domain: 불변식

Domain 객체의 불변식(invariant)은 생성자나 팩토리 메서드에서 강제한다. 불변식이란 해당 객체가 유효한 상태로 존재하기 위해 항상 참이어야 하는 조건이다.

```java
public class Money {
    private final BigDecimal amount;
    private final Currency currency;

    public Money(BigDecimal amount, Currency currency) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("금액은 0 이상이어야 한다");
        }
        if (currency == null) {
            throw new IllegalArgumentException("통화는 null일 수 없다");
        }
        this.amount = amount;
        this.currency = currency;
    }
}
```

```java
public class Order {
    private OrderStatus status;
    private List<OrderItem> items;

    // 팩토리 메서드에서 생성 시 검증
    public static Order create(CustomerId customerId, List<OrderItem> items) {
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("주문 항목은 하나 이상이어야 한다");
        }
        return new Order(customerId, items, OrderStatus.PENDING);
    }

    // 상태 전이 메서드에서 불변식 유지
    public void confirm() {
        if (this.status != OrderStatus.PENDING) {
            throw new IllegalStateException(
                "PENDING 상태의 주문만 확정 가능. 현재 상태: " + this.status
            );
        }
        this.status = OrderStatus.CONFIRMED;
    }
}
```

Domain 객체 외부에서 상태를 직접 변경할 수 없게 막고, 모든 상태 변경은 메서드를 통해서만 일어나도록 한다. setter를 열어두면 불변식 검증을 우회할 수 있다.

### DB: 제약 조건

DB 제약 조건은 마지막 방어선이다. 애플리케이션 계층이 제대로 동작하더라도 마이그레이션 스크립트, 관리자 직접 접근, 다른 서비스의 버그 등으로 잘못된 데이터가 들어갈 수 있다.

**즉시 검사 (IMMEDIATE) — 기본값:**

SQL 문장이 실행되는 즉시 제약 조건을 검사한다. 대부분의 경우 이 방식을 쓴다.

```sql
ALTER TABLE order_items
    ADD CONSTRAINT fk_order_items_product
    FOREIGN KEY (product_id) REFERENCES products(id)
    ON DELETE RESTRICT;
```

`ON DELETE RESTRICT`는 참조된 레코드를 삭제하려 할 때 즉시 오류를 낸다. `ON DELETE NO ACTION`과 달리 RESTRICT는 지연(deferrable) 검사가 불가능하다.

**지연 검사 (DEFERRABLE) — 커밋 시점 검사:**

트랜잭션 내에서 일시적으로 제약 조건을 위반한 상태를 허용하고 커밋 시점에 검사한다. 트리 구조 재정렬처럼 중간 상태에서 순환 참조나 일시적 참조 위반이 생기는 경우에 필요하다.

```sql
ALTER TABLE nodes
    ADD CONSTRAINT fk_parent
    FOREIGN KEY (parent_id) REFERENCES nodes(id)
    DEFERRABLE INITIALLY DEFERRED;
```

```sql
BEGIN;
SET CONSTRAINTS fk_parent DEFERRED;

-- A의 parent를 B로, B의 parent를 A로 교체하는 과정에서
-- 일시적으로 서로를 참조하는 상태가 된다
UPDATE nodes SET parent_id = 2 WHERE id = 1;
UPDATE nodes SET parent_id = 1 WHERE id = 2;

COMMIT;  -- 커밋 시점에 제약 조건 검사
```

PostgreSQL은 DEFERRABLE을 완전히 지원한다. MySQL은 외래 키 지연 검사가 불가능하다.

**Unique 제약 조건과 애플리케이션 검증의 관계:**

Service에서 중복 확인 후 INSERT를 해도 동시 요청이 있으면 race condition이 발생한다. DB의 Unique 제약 조건이 이를 막는다.

```java
// Service의 중복 확인 — race condition 가능
if (userRepository.existsByEmail(email)) {
    throw new DuplicateEmailException();
}
// 이 사이에 다른 요청이 같은 email로 INSERT할 수 있다
userRepository.save(new User(email, ...));
```

Service의 중복 확인은 사용자에게 명확한 오류 메시지를 주기 위한 것이고, DB의 Unique 제약 조건은 실제 데이터 정합성을 보장한다. 둘 다 필요하다.

## 이벤트 기반 아키텍처에서 검증 시점

이벤트 기반 아키텍처에서는 "발행 전"과 "소비 후" 중 어느 시점에 검증할지 결정해야 한다.

### 발행 전 검증

이벤트를 발행하기 전에 검증하고, 실패하면 이벤트를 발행하지 않는다. 불필요한 이벤트가 브로커에 쌓이는 걸 막는다. 소비자가 이벤트를 받아 처리하다가 실패하는 것보다 발행 전에 막는 게 낫다.

```java
public void processOrder(OrderCommand command) {
    Order order = orderRepository.findById(command.getOrderId())
        .orElseThrow(OrderNotFoundException::new);

    if (order.getStatus() != OrderStatus.PENDING) {
        throw new InvalidOrderStatusException();
    }

    // 검증 통과 후 이벤트 발행
    eventPublisher.publish(new OrderProcessingStartedEvent(order.getId()));
}
```

문제는 DB에 상태를 저장한 후 이벤트를 발행하는 과정에서 장애가 나면 이벤트가 유실된다는 점이다. Outbox 패턴이 이를 해결한다.

```
트랜잭션 내:
  1. orders 테이블에 상태 저장
  2. outbox 테이블에 이벤트 저장  ← 같은 트랜잭션

트랜잭션 외부:
  3. outbox 폴링 → 브로커로 발행  ← 별도 프로세스
```

### 소비 후 검증

이벤트를 받은 소비자가 처리하면서 검증한다. 소비자 쪽에서만 알 수 있는 비즈니스 규칙을 적용할 때 쓴다.

```java
@EventHandler
public void handle(OrderCreatedEvent event) {
    Customer customer = customerRepository.findById(event.getCustomerId())
        .orElseThrow(() -> new CustomerNotFoundException(event.getCustomerId()));

    if (!customer.isActive()) {
        throw new InvalidCustomerStateException();
    }

    // 처리 계속
}
```

소비 후 검증에서 실패하면 재시도 정책과 Dead Letter Queue가 필요하다. 재시도로 해결 가능한 일시적 오류(네트워크 실패, 일시적 DB 오류)와 재시도해도 해결되지 않는 영구적 오류(비즈니스 규칙 위반)를 구분해야 한다.

```java
@RetryableTopic(attempts = "3", backoff = @Backoff(delay = 1000))
public void handle(OrderCreatedEvent event) {
    try {
        processOrder(event);
    } catch (BusinessRuleViolationException e) {
        // 재시도해도 소용없는 오류 — 바로 DLQ로
        throw new NonRetryableException(e);
    }
}
```

발행 전에 검증 가능한 정보는 발행 전에 검증한다. 소비자 도메인에서만 알 수 있는 정보는 소비 후에 검증한다. 발행자는 자신이 알 수 있는 범위에서 검증하고, 소비자는 자신의 도메인 규칙으로 추가 검증하는 구조가 자연스럽다.

## 동시 요청 충돌과 검증 시점 조정

동시 요청이 들어올 때 검증 시점 자체가 race condition의 원인이 된다. "조회해서 확인" → "업데이트" 사이에 다른 트랜잭션이 끼어들면 검증은 통과했지만 실제 상태는 달라진다.

### 낙관적 잠금

조회 시점과 업데이트 시점 사이에 다른 트랜잭션이 변경했는지 version 컬럼으로 확인한다. 충돌이 드물 때 유리하다.

```java
@Entity
public class Product {
    @Id
    private Long id;

    private int stock;

    @Version
    private Long version;  // JPA가 자동으로 관리
}
```

```java
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findById(productId).orElseThrow();

    if (product.getStock() < quantity) {
        throw new InsufficientStockException();
    }

    product.setStock(product.getStock() - quantity);
    // 커밋 시 version 불일치면 OptimisticLockException
    // 다른 트랜잭션이 이미 version을 올렸으면 이 트랜잭션은 실패
}
```

낙관적 잠금의 문제는 검증을 통과했어도 커밋 시 실패할 수 있다는 점이다. 재시도 로직이 필요하다.

```java
@Retryable(
    value = OptimisticLockingFailureException.class,
    maxAttempts = 3,
    backoff = @Backoff(delay = 100)
)
public void decreaseStock(Long productId, int quantity) {
    // ...
}
```

재시도 시점에는 다른 트랜잭션이 커밋한 최신 상태를 읽는다. 재고가 실제로 부족해졌을 수 있으므로 검증도 다시 한다.

### 비관적 잠금

조회 시점에 잠금을 걸어 다른 트랜잭션이 해당 레코드에 접근하지 못하게 막는다. 충돌이 잦거나 충돌 비용이 클 때 쓴다.

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT p FROM Product p WHERE p.id = :id")
Optional<Product> findByIdWithLock(@Param("id") Long id);
```

```java
@Transactional
public void decreaseStock(Long productId, int quantity) {
    // SELECT ... FOR UPDATE — 이 시점에 잠금 획득
    Product product = productRepository.findByIdWithLock(productId).orElseThrow();

    // 잠금을 잡고 있으므로 이 검증은 정확하다
    // 다른 트랜잭션은 이 트랜잭션이 커밋/롤백할 때까지 대기
    if (product.getStock() < quantity) {
        throw new InsufficientStockException();
    }

    product.setStock(product.getStock() - quantity);
}
```

비관적 잠금은 검증과 업데이트 사이의 일관성을 보장하지만, 대기 시간이 늘어나고 deadlock 위험이 있다.

### 선택 기준

재고 감소, 티켓 예약처럼 동시 요청이 많고 충돌이 잦은 경우에는 비관적 잠금이 낫다. 사용자 프로필 업데이트처럼 같은 리소스를 동시에 수정하는 경우가 드물면 낙관적 잠금으로 충분하다.

충돌 후 재시도가 의미 있는지도 고려한다. 재시도해서 성공할 수 있으면 낙관적 잠금 + 재시도, 재시도해도 결국 실패할 가능성이 높으면 비관적 잠금으로 처음부터 직렬화한다.
