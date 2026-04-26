---
title: DDD (Domain-Driven Design)
tags: [architecture, ddd, domain-driven-design, aggregate, entity, value-object, bounded-context, specification, factory]
updated: 2026-03-31
---

# DDD (Domain-Driven Design)

## 개요

DDD(도메인 주도 설계)는 복잡한 비즈니스 도메인을 소프트웨어 모델로 표현하는 설계 방법론이다. Eric Evans가 2003년에 제안했으며, 기술이 아닌 도메인(비즈니스 영역)을 중심으로 설계한다.

### 핵심 철학

```
기술 중심 설계:
  "어떤 프레임워크를 쓸까?" → "테이블을 어떻게 설계할까?"

도메인 중심 설계:
  "비즈니스 문제가 뭘까?" → "도메인 모델을 어떻게 표현할까?"
```

### DDD가 필요한 시점

| 상황 | DDD 필요성 |
|------|-----------|
| 간단한 CRUD 앱 | 불필요 (오버 엔지니어링) |
| 비즈니스 규칙이 복잡한 시스템 | 필요 |
| MSA로 서비스 분리가 필요한 시스템 | 필요 (경계 설정 근거) |
| 도메인 전문가와 협업이 많은 프로젝트 | 필요 (유비쿼터스 언어) |

---

## 전략적 설계 (Strategic Design)

시스템을 큰 단위로 나누는 설계. 어떤 도메인이 있고, 어떻게 경계를 나눌 것인가를 결정한다.

### 유비쿼터스 언어 (Ubiquitous Language)

개발자와 도메인 전문가가 같은 용어를 사용한다.

```
용어 불일치 — 흔히 발생하는 문제:
  기획자: "주문을 접수한다"
  개발자: "OrderData를 INSERT한다"
  DB 설계자: "T_ORD 테이블에 레코드 추가"

유비쿼터스 언어 적용 후:
  모두: "주문(Order)을 접수(place)한다"
  → 코드에서도: order.place()
```

### Bounded Context (바운디드 컨텍스트)

같은 용어라도 맥락에 따라 다른 의미를 가진다. Bounded Context는 이 의미가 유효한 경계를 정의한다.

```
"상품(Product)"의 의미:

카탈로그 컨텍스트:  이름, 설명, 이미지, 카테고리
가격 컨텍스트:      정가, 할인율, 프로모션 가격
재고 컨텍스트:      SKU, 수량, 창고 위치
배송 컨텍스트:      무게, 크기, 배송 제한

→ 각 컨텍스트에서 Product는 다른 속성과 행동을 가진다
→ 하나의 Product 클래스로 모든 것을 담으면 God Object가 된다
```

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   주문 BC     │  │   결제 BC     │  │   배송 BC     │
│              │  │              │  │              │
│ Order        │  │ Payment      │  │ Shipment     │
│ OrderItem    │  │ Transaction  │  │ Delivery     │
│ Customer(id) │  │ Customer(id) │  │ Address      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─── 이벤트로 느슨하게 연결 ──────────┘
```

### Context Map (컨텍스트 맵)

바운디드 컨텍스트 간의 관계를 정의한다.

| 관계 | 설명 | 예시 |
|------|------|------|
| **Shared Kernel** | 공유 모델 | 두 팀이 공통 라이브러리 사용 |
| **Customer-Supplier** | 상류-하류 관계 | 주문(상류) → 배송(하류) |
| **Conformist** | 하류가 상류 모델을 그대로 따름 | 외부 API 그대로 사용 |
| **Anti-Corruption Layer** | 외부 모델을 내부 모델로 변환 | 레거시 시스템 연동 |
| **Published Language** | 표준 포맷으로 통신 | JSON 이벤트 스키마 |

```
Anti-Corruption Layer 예시:

레거시 시스템          ACL (변환 계층)           새 시스템
┌──────────┐       ┌──────────────┐       ┌──────────┐
│ CustData │──────▶│ LegacyAdapter│──────▶│ Customer │
│ cst_nm   │       │ 필드명 변환    │       │ name     │
│ cst_addr │       │ 형식 변환     │       │ address  │
└──────────┘       └──────────────┘       └──────────┘
```

---

## 전술적 설계 (Tactical Design)

바운디드 컨텍스트 내부를 구체적으로 구현하는 패턴들이다.

### Entity

고유 식별자(ID)를 가지며, 생명주기 동안 속성이 변해도 같은 객체로 취급된다.

```java
public class Order {
    private final OrderId id;       // 식별자 (불변)
    private OrderStatus status;     // 변할 수 있는 상태
    private List<OrderItem> items;
    private Money totalPrice;

    public void addItem(Product product, int quantity) {
        if (status != OrderStatus.DRAFT) {
            throw new IllegalStateException("확정된 주문에는 상품을 추가할 수 없습니다");
        }
        items.add(new OrderItem(product.getId(), product.getPrice(), quantity));
        recalculateTotal();
    }

    @Override
    public boolean equals(Object o) {
        if (o instanceof Order other) {
            return this.id.equals(other.id);
        }
        return false;
    }
}
```

### Value Object

식별자가 없고, 값 자체로 동등성을 판단한다. 불변(Immutable)이다.

```java
// Primitive Obsession — 원시 타입만 쓰면 유효성 검증이 흩어진다
public void createOrder(String address, int price, String currency) {
    // address가 유효한지? price가 음수면? currency가 "KRW"인지?
}

// Value Object로 표현하면 생성 시점에 유효성을 보장한다
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("금액은 음수일 수 없습니다");
        }
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException("통화가 다릅니다");
        }
        return new Money(this.amount.add(other.amount), this.currency);
    }
}

public record Address(String city, String street, String zipCode) {
    public Address {
        if (zipCode == null || !zipCode.matches("\\d{5}")) {
            throw new IllegalArgumentException("우편번호 형식이 잘못되었습니다");
        }
    }
}
```

| 비교 | Entity | Value Object |
|------|--------|-------------|
| **동등성** | ID로 비교 | 값으로 비교 |
| **가변성** | 가변 (상태 변경) | 불변 (새 객체 생성) |
| **생명주기** | 독립적 | Entity에 종속 |
| **예시** | 주문, 사용자, 상품 | 금액, 주소, 기간 |

### Aggregate (집합체)

관련 Entity와 Value Object를 하나의 일관성 경계로 묶는다. 외부에서는 Aggregate Root를 통해서만 접근한다.

```
Order Aggregate:
  ┌─────────────────────────────────┐
  │  Order (Aggregate Root)         │
  │    ├── OrderItem (Entity)       │
  │    ├── OrderItem (Entity)       │
  │    ├── ShippingAddress (VO)     │
  │    └── Money totalPrice (VO)    │
  └─────────────────────────────────┘

규칙:
  - 외부에서 OrderItem을 직접 수정 불가
  - 반드시 Order를 통해서만 조작
  - 하나의 트랜잭션 = 하나의 Aggregate
```

```java
// Aggregate Root
public class Order {
    private OrderId id;
    private List<OrderItem> items = new ArrayList<>();

    // Aggregate Root를 통해서만 OrderItem 조작
    public void addItem(ProductId productId, Money price, int quantity) {
        OrderItem item = new OrderItem(productId, price, quantity);
        items.add(item);
        recalculateTotal();
    }

    public void removeItem(ProductId productId) {
        items.removeIf(item -> item.getProductId().equals(productId));
        recalculateTotal();
    }
}

// 이렇게 하면 안 된다 — Aggregate Root를 우회하는 코드
// order.getItems().add(new OrderItem(...));
```

### Aggregate 설계 규칙

| 규칙 | 설명 |
|------|------|
| **작게 유지** | Aggregate는 가능한 작게. 큰 Aggregate = 동시성 문제 |
| **ID로 참조** | 다른 Aggregate는 ID로만 참조 (객체 참조 X) |
| **하나의 트랜잭션** | 하나의 Aggregate만 하나의 트랜잭션에서 수정 |
| **결과적 일관성** | Aggregate 간에는 이벤트로 결과적 일관성 유지 |

```
잘못된 설계 (Aggregate가 너무 큼):
  Order → OrderItem → Product → Category → ...
  (하나의 트랜잭션으로 모든 것을 잠금)

올바른 설계 (ID로 참조):
  Order → OrderItem(productId만 보유)
  Product는 별도 Aggregate
```

---

## Anemic Domain Model vs Rich Domain Model

DDD를 도입했다고 하면서 실제로는 Anemic Domain Model로 구현하는 경우가 매우 흔하다. Spring + JPA 프로젝트에서 DDD 실패의 가장 큰 원인이다.

### Anemic Domain Model (빈약한 도메인 모델)

Entity에 getter/setter만 있고, 비즈니스 로직이 전부 Service 레이어에 있는 구조다. Martin Fowler는 이것을 안티패턴이라고 했다.

```java
// Entity — getter/setter 덩어리
@Entity
public class Order {
    @Id private Long id;
    private String status;
    private BigDecimal totalPrice;
    private List<OrderItem> items;

    // getter, setter만 존재
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public void setTotalPrice(BigDecimal totalPrice) { this.totalPrice = totalPrice; }
}

// Service — 비즈니스 로직이 전부 여기에 몰려있다
@Service
public class OrderService {

    public void cancelOrder(Long orderId) {
        Order order = orderRepository.findById(orderId).orElseThrow();

        // 도메인 로직이 Service에 흩어져 있다
        if (!"PLACED".equals(order.getStatus())) {
            throw new IllegalStateException("접수된 주문만 취소 가능합니다");
        }
        if (order.getTotalPrice().compareTo(new BigDecimal("1000000")) > 0) {
            throw new IllegalStateException("100만원 이상 주문은 관리자 승인 필요");
        }

        order.setStatus("CANCELLED");
        // 금액 재계산 로직도 여기에...
    }
}
```

이 구조의 문제점:

- 같은 비즈니스 규칙이 여러 Service에 중복된다. `cancelOrder`에서 검증하는 상태 체크가 `refundOrder`, `modifyOrder`에도 반복된다.
- Order의 상태 변경 규칙을 알려면 모든 Service 코드를 뒤져야 한다.
- setter가 열려있어서 아무 데서나 `order.setStatus("SHIPPED")`를 호출할 수 있다.

### Rich Domain Model (풍부한 도메인 모델)

비즈니스 로직이 Entity 안에 있다. 상태 변경은 반드시 의미 있는 메서드를 통해서만 이루어진다.

```java
@Entity
public class Order {
    @Id private Long id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    private Money totalPrice;
    private List<OrderItem> items;

    // setter 없음. 비즈니스 의미가 있는 메서드만 제공한다.
    public void cancel() {
        if (this.status != OrderStatus.PLACED) {
            throw new IllegalStateException("접수된 주문만 취소 가능합니다");
        }
        if (this.totalPrice.isGreaterThan(Money.of(1_000_000))) {
            throw new IllegalStateException("100만원 이상 주문은 관리자 승인 필요");
        }
        this.status = OrderStatus.CANCELLED;
    }

    public void addItem(ProductId productId, Money price, int quantity) {
        if (this.status != OrderStatus.DRAFT) {
            throw new IllegalStateException("작성 중인 주문에만 상품 추가 가능");
        }
        this.items.add(new OrderItem(productId, price, quantity));
        recalculateTotal();
    }

    private void recalculateTotal() {
        this.totalPrice = items.stream()
            .map(OrderItem::getSubtotal)
            .reduce(Money.ZERO, Money::add);
    }
}

// Service — 흐름 제어만 담당
@Service
public class OrderService {

    @Transactional
    public void cancelOrder(Long orderId) {
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.cancel();  // 도메인 로직은 Order가 책임진다
        orderRepository.save(order);
    }
}
```

| 비교 | Anemic Model | Rich Model |
|------|-------------|------------|
| 로직 위치 | Service | Entity |
| 상태 변경 | setter로 자유롭게 | 비즈니스 메서드로만 |
| 규칙 중복 | 여러 Service에 분산 | Entity에 집중 |
| 테스트 | Service 의존성 많음 | Entity 단위 테스트 가능 |
| 실무 현실 | 대부분의 Spring 프로젝트 | DDD를 제대로 적용한 프로젝트 |

---

## Domain Service

Entity나 Value Object에 속하기 어려운 도메인 로직을 담는다.

```java
// 할인 계산: 주문(Order)에도, 상품(Product)에도 속하지 않는 로직
public class DiscountPolicy {

    public Money calculateDiscount(Order order, Customer customer) {
        Money discount = Money.ZERO;

        // VIP 고객 10% 할인
        if (customer.isVip()) {
            discount = order.getTotalPrice().multiply(0.1);
        }

        // 5만원 이상 5천원 추가 할인
        if (order.getTotalPrice().isGreaterThan(Money.of(50000))) {
            discount = discount.add(Money.of(5000));
        }

        return discount;
    }
}
```

---

## Domain Event

도메인에서 발생한 중요한 사건을 표현한다. Aggregate 간 결과적 일관성을 달성하는 핵심 수단이다.

```java
// 도메인 이벤트 정의
public record OrderPlacedEvent(
    OrderId orderId,
    Long userId,
    Money totalPrice,
    LocalDateTime occurredAt
) {}

// Order Aggregate에서 이벤트 발행
public class Order extends AbstractAggregateRoot<Order> {

    public void place() {
        validate();
        this.status = OrderStatus.PLACED;

        registerEvent(new OrderPlacedEvent(
            this.id, this.userId, this.totalPrice, LocalDateTime.now()
        ));
    }
}

// 이벤트 핸들러 (다른 Bounded Context)
@Component
public class OrderEventHandler {

    @EventListener
    public void handleOrderPlaced(OrderPlacedEvent event) {
        inventoryService.decreaseStock(event.orderId());
        paymentService.requestPayment(event.orderId(), event.totalPrice());
    }
}
```

---

## Repository 패턴

Aggregate 단위로 영속성을 관리한다.

```java
// Repository 인터페이스 (도메인 레이어)
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(OrderId id);
    List<Order> findByUserId(Long userId);
    void delete(Order order);
}

// 구현체 (인프라 레이어)
@Repository
public class OrderRepositoryImpl implements OrderRepository {
    private final OrderJpaRepository jpaRepository;

    @Override
    public Order save(Order order) {
        OrderJpaEntity entity = OrderMapper.toJpaEntity(order);
        OrderJpaEntity saved = jpaRepository.save(entity);
        return OrderMapper.toDomain(saved);
    }
}
```

| 규칙 | 설명 |
|------|------|
| Aggregate Root마다 하나의 Repository | OrderItem용 Repository는 만들지 않는다 |
| Repository는 도메인 레이어에 인터페이스 | 구현체는 인프라 레이어에 |
| 컬렉션처럼 동작 | save, findById, delete |

---

## Factory 패턴

Aggregate 생성 로직이 복잡해지면 생성자에 모든 것을 넣기 어렵다. Factory로 분리한다.

### 문제 상황

```java
// 생성자가 비대해지는 경우
public class Order {
    public Order(Long userId, List<CartItem> cartItems, Address shippingAddress,
                 CouponId couponId, PaymentMethod paymentMethod, String note) {
        // 장바구니 → 주문 항목 변환
        // 쿠폰 적용 가능 여부 확인
        // 배송지 유효성 검증
        // 결제 수단별 초기 상태 설정
        // ...30줄의 초기화 로직
    }
}
```

생성자에 비즈니스 로직이 과도하게 들어가면 Order 클래스가 자기 자신의 생성 방법까지 알아야 한다. 다른 Aggregate의 정보(Cart, Coupon)를 참조해야 하는 경우 의존성도 복잡해진다.

### Factory로 분리

```java
@Component
public class OrderFactory {

    private final CouponRepository couponRepository;

    public Order createFromCart(Long userId, Cart cart, Address shippingAddress,
                                CouponId couponId) {
        // 장바구니에 상품이 있는지 확인
        if (cart.isEmpty()) {
            throw new IllegalArgumentException("장바구니가 비어있습니다");
        }

        // 장바구니 항목을 주문 항목으로 변환
        List<OrderItem> orderItems = cart.getItems().stream()
            .map(cartItem -> new OrderItem(
                cartItem.getProductId(),
                cartItem.getPrice(),
                cartItem.getQuantity()))
            .toList();

        // 쿠폰 적용
        Money discount = Money.ZERO;
        if (couponId != null) {
            Coupon coupon = couponRepository.findById(couponId).orElseThrow();
            discount = coupon.calculateDiscount(orderItems);
        }

        return new Order(userId, orderItems, shippingAddress, discount);
    }
}
```

Factory를 쓰는 기준:

- Aggregate 생성 시 다른 Aggregate의 정보가 필요한 경우
- 생성 규칙이 복잡하거나 여러 생성 경로가 있는 경우
- 단순한 생성이면 생성자나 정적 팩토리 메서드로 충분하다. 무조건 Factory 클래스를 만들 필요는 없다.

---

## Specification 패턴

복잡한 비즈니스 규칙을 개별 객체로 분리해서 조합하고 재사용한다.

### 문제 상황

```java
// 할인 적용 조건이 여러 곳에 분산된다
public class DiscountService {
    public boolean canApplyDiscount(Order order) {
        return order.getTotalPrice().isGreaterThan(Money.of(50000))
            && order.getStatus() == OrderStatus.PLACED
            && order.getItemCount() >= 3
            && !order.hasAlreadyDiscounted();
    }
}

public class PromotionService {
    public boolean isEligibleForPromotion(Order order) {
        // 비슷한 조건이 또 나온다
        return order.getTotalPrice().isGreaterThan(Money.of(50000))
            && order.getItemCount() >= 3;
    }
}
```

### Specification으로 규칙 분리

```java
public interface Specification<T> {
    boolean isSatisfiedBy(T candidate);

    default Specification<T> and(Specification<T> other) {
        return candidate -> this.isSatisfiedBy(candidate) && other.isSatisfiedBy(candidate);
    }

    default Specification<T> or(Specification<T> other) {
        return candidate -> this.isSatisfiedBy(candidate) || other.isSatisfiedBy(candidate);
    }

    default Specification<T> not() {
        return candidate -> !this.isSatisfiedBy(candidate);
    }
}

// 개별 규칙을 각각 클래스로 분리
public class MinimumOrderAmountSpec implements Specification<Order> {
    private final Money minimumAmount;

    public MinimumOrderAmountSpec(Money minimumAmount) {
        this.minimumAmount = minimumAmount;
    }

    @Override
    public boolean isSatisfiedBy(Order order) {
        return order.getTotalPrice().isGreaterThan(minimumAmount);
    }
}

public class MinimumItemCountSpec implements Specification<Order> {
    private final int minCount;

    public MinimumItemCountSpec(int minCount) {
        this.minCount = minCount;
    }

    @Override
    public boolean isSatisfiedBy(Order order) {
        return order.getItemCount() >= minCount;
    }
}

public class OrderPlacedSpec implements Specification<Order> {
    @Override
    public boolean isSatisfiedBy(Order order) {
        return order.getStatus() == OrderStatus.PLACED;
    }
}
```

### 조합해서 사용

```java
public class DiscountService {
    // 규칙을 조합한다 — 각 규칙은 재사용 가능
    private final Specification<Order> discountSpec =
        new MinimumOrderAmountSpec(Money.of(50000))
            .and(new OrderPlacedSpec())
            .and(new MinimumItemCountSpec(3));

    public boolean canApplyDiscount(Order order) {
        return discountSpec.isSatisfiedBy(order);
    }
}

public class PromotionService {
    // 같은 규칙을 다르게 조합
    private final Specification<Order> promotionSpec =
        new MinimumOrderAmountSpec(Money.of(50000))
            .and(new MinimumItemCountSpec(3));

    public boolean isEligibleForPromotion(Order order) {
        return promotionSpec.isSatisfiedBy(order);
    }
}
```

Specification 패턴은 조건이 3개 이상이고, 여러 곳에서 조합이 달라지는 경우에 쓴다. 단순한 if문 하나로 끝나는 조건에 Specification을 적용하면 오히려 코드만 복잡해진다.

---

## DDD + JPA/Spring 실무 매핑 문제

DDD 책에 나오는 도메인 모델을 JPA Entity로 그대로 옮기면 여러 충돌이 발생한다. Spring + JPA 환경에서 실제로 겪는 문제들이다.

### Aggregate와 JPA Entity 매핑

DDD에서 Aggregate Root는 도메인 객체이고, JPA Entity는 영속성 객체다. 이 둘을 분리할지 합칠지가 첫 번째 결정이다.

```java
// 방법 1: 도메인 모델과 JPA Entity를 분리
// 도메인 모델
public class Order {
    private OrderId id;
    private OrderStatus status;
    private List<OrderItem> items;
    public void cancel() { /* 비즈니스 로직 */ }
}

// JPA Entity
@Entity
@Table(name = "orders")
public class OrderJpaEntity {
    @Id @GeneratedValue
    private Long id;
    @Enumerated(EnumType.STRING)
    private OrderStatus status;
    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItemJpaEntity> items;
}

// Mapper로 변환
public class OrderMapper {
    public static Order toDomain(OrderJpaEntity entity) { /* ... */ }
    public static OrderJpaEntity toEntity(Order domain) { /* ... */ }
}
```

분리하면 도메인 모델이 JPA 애노테이션에 오염되지 않지만, 매핑 코드가 계속 늘어난다. Aggregate 내부 구조가 복잡해질수록 Mapper 유지보수가 고통이다.

```java
// 방법 2: JPA Entity에 도메인 로직을 직접 넣기 (실무에서 흔한 타협)
@Entity
@Table(name = "orders")
public class Order {
    @Id @GeneratedValue
    private Long id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "order_id")
    private List<OrderItem> items = new ArrayList<>();

    // JPA용 기본 생성자
    protected Order() {}

    // 도메인 로직
    public void cancel() {
        if (this.status != OrderStatus.PLACED) {
            throw new IllegalStateException("접수된 주문만 취소 가능");
        }
        this.status = OrderStatus.CANCELLED;
    }
}
```

대부분의 Spring 프로젝트에서는 방법 2를 선택한다. 완벽한 DDD는 아니지만, Mapper 지옥을 피하면서 Rich Domain Model은 유지할 수 있다.

### Value Object와 @Embeddable 매핑

DDD의 Value Object를 JPA에서 표현하려면 `@Embeddable`을 쓴다.

```java
@Embeddable
public class Money {
    private BigDecimal amount;

    @Enumerated(EnumType.STRING)
    private CurrencyType currency;

    protected Money() {} // JPA용 기본 생성자 — 도메인 관점에서는 불필요하다

    public Money(BigDecimal amount, CurrencyType currency) {
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("금액은 음수일 수 없습니다");
        }
        this.amount = amount;
        this.currency = currency;
    }

    // equals, hashCode 반드시 구현
}

@Entity
public class Order {
    @Embedded
    @AttributeOverrides({
        @AttributeOverride(name = "amount", column = @Column(name = "total_amount")),
        @AttributeOverride(name = "currency", column = @Column(name = "total_currency"))
    })
    private Money totalPrice;
}
```

Value Object 매핑에서 자주 겪는 문제:

- `@Embeddable`은 기본 생성자가 필요하다. `protected`로 만들어서 외부에서 부르지 못하게 한다.
- Java record를 `@Embeddable`로 쓰려면 Hibernate 6.2 이상이 필요하다. 그 이전 버전에서는 일반 클래스로 만들어야 한다.
- 같은 Value Object 타입을 한 Entity에서 여러 번 쓰면 `@AttributeOverrides`로 컬럼명을 지정해야 한다.

### ID 클래스 매핑

DDD에서는 `OrderId`, `ProductId` 같은 타입 안전한 ID를 사용한다. JPA에서는 몇 가지 방법이 있다.

```java
// 방법 1: @Embeddable ID
@Embeddable
public class OrderId implements Serializable {
    private Long value;

    protected OrderId() {}
    public OrderId(Long value) { this.value = value; }
    // equals, hashCode 필수
}

@Entity
public class Order {
    @EmbeddedId
    private OrderId id;
}

// 방법 2: 단순 래퍼 (JPA 밖에서만 사용)
// JPA Entity에서는 Long id를 쓰고, 도메인 레이어에서 OrderId로 감싼다
@Entity
public class Order {
    @Id @GeneratedValue
    private Long id;

    public OrderId getOrderId() {
        return new OrderId(this.id);
    }
}
```

`@EmbeddedId`를 쓰면 `@GeneratedValue`를 같이 쓸 수 없다. 자동 채번이 필요하면 방법 2가 현실적이다.

### Lazy Loading과 Aggregate 경계 충돌

Aggregate 내부의 컬렉션은 EAGER로 가져와야 일관성이 보장된다. 그런데 JPA 기본값은 `@OneToMany`가 LAZY다.

```java
@Entity
public class Order {
    @OneToMany(cascade = CascadeType.ALL, fetch = FetchType.LAZY) // 기본값: LAZY
    private List<OrderItem> items;

    public Money calculateTotal() {
        // LazyInitializationException 발생 가능
        // 트랜잭션 밖에서 이 메서드를 호출하면 터진다
        return items.stream()
            .map(OrderItem::getSubtotal)
            .reduce(Money.ZERO, Money::add);
    }
}
```

해결 방법:

```java
// 1. Aggregate 내부는 EAGER로 변경 (Aggregate가 작을 때)
@OneToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER)
private List<OrderItem> items;

// 2. Repository에서 fetch join으로 가져오기 (Aggregate가 클 때)
public interface OrderRepository extends JpaRepository<Order, Long> {
    @Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.id = :id")
    Optional<Order> findByIdWithItems(@Param("id") Long id);
}
```

Aggregate가 작으면 EAGER도 문제없다. Aggregate가 커지면 fetch join을 쓰되, 그 전에 Aggregate를 더 작게 나눌 수 있는지 먼저 고민해야 한다.

---

## Aggregate 설계 시 실무 트러블슈팅

### 큰 Aggregate로 인한 락 경합

주문 Aggregate에 주문 항목, 결제 정보, 배송 정보를 전부 넣으면 하나의 주문을 수정할 때 관련 데이터 전체에 락이 걸린다.

```
문제 시나리오:
  - 사용자 A: 주문 상품 변경 중 (Order 락 획득)
  - 시스템 B: 결제 상태 업데이트 시도 (Order 락 대기)
  - 시스템 C: 배송 상태 업데이트 시도 (Order 락 대기)
  → 동시 처리 불가. 트래픽이 몰리면 타임아웃 발생
```

```java
// 잘못된 설계 — 하나의 거대한 Aggregate
@Entity
public class Order {
    @Id private Long id;
    private OrderStatus orderStatus;
    @OneToMany private List<OrderItem> items;
    @OneToOne private Payment payment;         // 결제도 포함
    @OneToOne private Delivery delivery;       // 배송도 포함
}

// 개선 — Aggregate를 분리하고 ID로 참조
@Entity
public class Order {
    @Id private Long id;
    private OrderStatus status;
    @OneToMany private List<OrderItem> items;
    // Payment, Delivery는 별도 Aggregate
}

@Entity
public class Payment {
    @Id private Long id;
    private Long orderId;  // ID로만 참조
    private PaymentStatus status;
}

@Entity
public class Delivery {
    @Id private Long id;
    private Long orderId;  // ID로만 참조
    private DeliveryStatus status;
}
```

Aggregate를 분리하면 Order를 수정하는 동안 Payment, Delivery는 독립적으로 업데이트할 수 있다.

### Aggregate 간 참조 시 N+1 문제

Aggregate를 ID로 참조하면 조회 시 N+1 문제가 발생하는 경우가 있다.

```java
// 주문 목록에서 상품명을 보여줘야 하는 화면
public List<OrderSummaryDto> getOrderList(Long userId) {
    List<Order> orders = orderRepository.findByUserId(userId);  // 쿼리 1번

    return orders.stream().map(order -> {
        // 각 주문의 각 항목마다 Product를 조회한다 → N+1
        List<String> productNames = order.getItems().stream()
            .map(item -> productRepository.findById(item.getProductId()))  // 쿼리 N번
            .map(Product::getName)
            .toList();

        return new OrderSummaryDto(order.getId(), productNames);
    }).toList();
}
```

해결 방법 — 조회 전용 모델(Read Model)을 따로 만든다:

```java
// CQRS 적용 — 조회용 쿼리를 별도로 작성
public interface OrderQueryRepository {

    @Query("""
        SELECT new com.example.dto.OrderSummaryDto(
            o.id, o.status, oi.productName, oi.price, oi.quantity)
        FROM Order o
        JOIN o.items oi
        WHERE o.userId = :userId
        """)
    List<OrderSummaryDto> findOrderSummaries(@Param("userId") Long userId);
}
```

명령(Command)은 Aggregate를 통해, 조회(Query)는 전용 Repository를 통해 처리한다. Aggregate의 ID 참조 원칙을 조회 때문에 포기할 필요는 없다.

### 결과적 일관성 실패 시 보상 처리

Aggregate 간 이벤트 기반으로 결과적 일관성을 유지할 때, 이벤트 처리가 실패하면 데이터 불일치가 생긴다.

```java
// 주문 접수 → 재고 차감 → 결제 요청 순서로 이벤트가 흐른다
// 재고 차감은 성공했는데 결제가 실패하면?

@Component
public class PaymentEventHandler {

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void handleOrderPlaced(OrderPlacedEvent event) {
        try {
            paymentService.requestPayment(event.orderId(), event.totalPrice());
        } catch (PaymentFailedException e) {
            // 결제 실패 → 보상 트랜잭션 발행
            compensationService.publish(new PaymentFailedEvent(
                event.orderId(),
                e.getReason()
            ));
        }
    }
}

@Component
public class CompensationHandler {

    @EventListener
    public void handlePaymentFailed(PaymentFailedEvent event) {
        // 재고 원복
        inventoryService.restoreStock(event.orderId());
        // 주문 상태를 실패로 변경
        orderService.markAsFailed(event.orderId(), event.getReason());
    }
}
```

보상 처리에서 주의할 점:

- 보상 이벤트도 실패할 수 있다. 재시도 메커니즘이 필요하다. Spring Retry나 메시지 큐의 DLQ(Dead Letter Queue)를 활용한다.
- 이벤트 유실을 막으려면 Transactional Outbox 패턴을 쓴다. 이벤트를 DB 테이블에 먼저 저장하고, 별도 프로세스가 이 테이블을 폴링해서 발행한다.
- `@TransactionalEventListener`를 쓰면 트랜잭션 커밋 후에 이벤트가 발행된다. 커밋은 됐는데 이벤트 발행 전에 애플리케이션이 죽으면 이벤트가 유실된다.

```java
// Transactional Outbox 패턴
@Entity
@Table(name = "outbox_events")
public class OutboxEvent {
    @Id @GeneratedValue
    private Long id;
    private String aggregateType;
    private Long aggregateId;
    private String eventType;
    private String payload;      // JSON 직렬화된 이벤트
    private boolean published;
    private LocalDateTime createdAt;
}

// Aggregate 저장과 이벤트를 같은 트랜잭션에 넣는다
@Transactional
public void placeOrder(Order order) {
    orderRepository.save(order);
    outboxRepository.save(new OutboxEvent(
        "Order", order.getId(), "OrderPlaced",
        objectMapper.writeValueAsString(new OrderPlacedEvent(order))
    ));
}

// 별도 스케줄러가 미발행 이벤트를 폴링해서 메시지 큐로 보낸다
@Scheduled(fixedDelay = 1000)
public void publishOutboxEvents() {
    List<OutboxEvent> events = outboxRepository.findByPublishedFalse();
    for (OutboxEvent event : events) {
        messageQueue.publish(event.getEventType(), event.getPayload());
        event.markAsPublished();
        outboxRepository.save(event);
    }
}
```

---

## Event Storming

도메인을 빠르게 탐색하고 모델링하는 워크숍 기법이다. 개발자, 기획자, 도메인 전문가가 함께 참여한다.

```
포스트잇 색상 규칙:
  주황: Domain Event (과거형, "주문이 접수되었다")
  파랑: Command ("주문을 접수하라")
  노랑: Aggregate (Order, Payment)
  보라: Policy/Rule ("주문 접수되면 재고 차감")
  초록: Read Model (조회 화면)
  빨강: Hotspot (논쟁, 미해결 문제)

진행 순서:
  1. Domain Event 나열 (시간순으로 벽에 붙이기)
  2. Command 추가 (이벤트를 일으키는 행동)
  3. Aggregate 식별 (Command를 처리하는 주체)
  4. Bounded Context 도출 (관련 Aggregate 묶기)
  5. Context Map 작성 (BC 간 관계 정의)
```

```
예시: 전자상거래

주문 접수됨 → 결제 요청됨 → 결제 완료됨 → 재고 차감됨 → 배송 시작됨
    ↑            ↑            ↑            ↑            ↑
 주문 접수    결제 요청    결제 처리    재고 차감    배송 시작
    ↑            ↑            ↑            ↑            ↑
  [Order]    [Payment]    [Payment]  [Inventory]  [Shipment]
    ↓            ↓            ↓            ↓            ↓
  주문 BC      결제 BC      결제 BC     재고 BC      배송 BC
```

---

## DDD 적용 순서

```
1단계: 유비쿼터스 언어 정립
  → 도메인 용어 사전 만들기

2단계: Bounded Context 식별
  → 시스템 경계 나누기

3단계: Entity/Value Object 구분
  → 도메인 모델 설계

4단계: Aggregate 설계
  → 일관성 경계 정의

5단계: Domain Event 도입
  → Aggregate 간 이벤트 기반 통신
```

---

## 참고

- [Domain-Driven Design — Eric Evans](https://www.domainlanguage.com/ddd/)
- [Implementing Domain-Driven Design — Vaughn Vernon](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577)
- [클린 아키텍처](Clean_Architecture.md) — 아키텍처 패턴
- [이벤트 소싱 & CQRS](MSA/이벤트_소싱_및_CQRS.md) — 이벤트 기반 설계
- [Saga 패턴](MSA/Saga_패턴_및_분산_트랜잭션.md) — 분산 트랜잭션
