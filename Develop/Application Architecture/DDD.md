---
title: DDD (Domain-Driven Design) 가이드
tags: [architecture, ddd, domain-driven-design, aggregate, entity, value-object, bounded-context, event-storming]
updated: 2026-03-01
---

# DDD (Domain-Driven Design)

## 개요

DDD(도메인 주도 설계)는 **복잡한 비즈니스 도메인을 소프트웨어 모델로 표현**하는 설계 방법론이다. Eric Evans가 2003년에 제안했으며, 기술이 아닌 **도메인(비즈니스 영역)**을 중심으로 설계한다.

### 핵심 철학

```
❌ 기술 중심 설계:
  "어떤 프레임워크를 쓸까?" → "테이블을 어떻게 설계할까?"

✅ 도메인 중심 설계:
  "비즈니스 문제가 뭘까?" → "도메인 모델을 어떻게 표현할까?"
```

### DDD가 필요한 시점

| 상황 | DDD 필요성 |
|------|-----------|
| 간단한 CRUD 앱 | 불필요 (오버 엔지니어링) |
| 비즈니스 규칙이 복잡한 시스템 | **필요** |
| MSA로 서비스 분리가 필요한 시스템 | **매우 필요** (경계 설정) |
| 도메인 전문가와 협업이 많은 프로젝트 | **필요** (유비쿼터스 언어) |

## 핵심

### 1. 전략적 설계 (Strategic Design)

시스템을 큰 단위로 나누는 설계. **어떤 도메인이 있고, 어떻게 경계를 나눌 것인가.**

#### 유비쿼터스 언어 (Ubiquitous Language)

개발자와 도메인 전문가가 **같은 용어**를 사용한다.

```
❌ 용어 불일치:
  기획자: "주문을 접수한다"
  개발자: "OrderData를 INSERT한다"
  DB 설계자: "T_ORD 테이블에 레코드 추가"

✅ 유비쿼터스 언어:
  모두: "주문(Order)을 접수(place)한다"
  → 코드에서도: order.place()
```

#### Bounded Context (바운디드 컨텍스트)

같은 용어라도 **맥락에 따라 다른 의미**를 가진다. Bounded Context는 이 의미가 유효한 경계를 정의한다.

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

#### Context Map (컨텍스트 맵)

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

### 2. 전술적 설계 (Tactical Design)

바운디드 컨텍스트 내부를 구체적으로 구현하는 패턴들.

#### Entity

**고유 식별자(ID)**를 가지며, 생명주기 동안 속성이 변해도 같은 객체로 취급된다.

```java
public class Order {
    private final OrderId id;       // 식별자 (불변)
    private OrderStatus status;     // 변할 수 있는 상태
    private List<OrderItem> items;
    private Money totalPrice;

    // 비즈니스 규칙
    public void addItem(Product product, int quantity) {
        if (status != OrderStatus.DRAFT) {
            throw new IllegalStateException("확정된 주문에는 상품을 추가할 수 없습니다");
        }
        items.add(new OrderItem(product.getId(), product.getPrice(), quantity));
        recalculateTotal();
    }

    // 두 Order가 같은 id를 가지면 같은 주문이다
    @Override
    public boolean equals(Object o) {
        if (o instanceof Order other) {
            return this.id.equals(other.id);
        }
        return false;
    }
}
```

#### Value Object

식별자가 없고, **값 자체로 동등성**을 판단한다. 불변(Immutable)이다.

```java
// ❌ Primitive Obsession (원시 타입 집착)
public void createOrder(String address, int price, String currency) {
    // address가 유효한지? price가 음수면? currency가 "KRW"인지?
}

// ✅ Value Object로 표현
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

#### Aggregate (집합체)

관련 Entity와 Value Object를 하나의 **일관성 경계**로 묶는다. 외부에서는 **Aggregate Root**를 통해서만 접근한다.

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

    // ✅ Aggregate Root를 통해서만 OrderItem 조작
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

// ❌ 외부에서 직접 OrderItem을 조작하면 안 된다
// order.getItems().add(new OrderItem(...));  // 규칙 위반!
```

#### Aggregate 설계 규칙

| 규칙 | 설명 |
|------|------|
| **작게 유지** | Aggregate는 가능한 작게. 큰 Aggregate = 동시성 문제 |
| **ID로 참조** | 다른 Aggregate는 ID로만 참조 (객체 참조 X) |
| **하나의 트랜잭션** | 하나의 Aggregate만 하나의 트랜잭션에서 수정 |
| **결과적 일관성** | Aggregate 간에는 이벤트로 결과적 일관성 유지 |

```
❌ 잘못된 설계 (Aggregate가 너무 큼):
  Order → OrderItem → Product → Category → ...
  (하나의 트랜잭션으로 모든 것을 잠금)

✅ 올바른 설계 (ID로 참조):
  Order → OrderItem(productId만 보유)
  Product는 별도 Aggregate
```

#### Domain Service

Entity나 Value Object에 속하기 어려운 **도메인 로직**을 담는다.

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

#### Domain Event

도메인에서 발생한 **중요한 사건**을 표현한다. Aggregate 간 결과적 일관성을 달성하는 핵심 수단.

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
        // 비즈니스 규칙 검증
        validate();
        this.status = OrderStatus.PLACED;

        // 도메인 이벤트 등록
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
        // 재고 차감
        inventoryService.decreaseStock(event.orderId());
        // 결제 요청
        paymentService.requestPayment(event.orderId(), event.totalPrice());
    }
}
```

### 3. Repository 패턴

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

### 4. Event Storming

도메인을 빠르게 탐색하고 모델링하는 **워크숍 기법**이다. 개발자, 기획자, 도메인 전문가가 함께 참여한다.

```
포스트잇 색상 규칙:
  🟧 주황: Domain Event (과거형, "주문이 접수되었다")
  🟦 파랑: Command ("주문을 접수하라")
  🟨 노랑: Aggregate (Order, Payment)
  🟪 보라: Policy/Rule ("주문 접수되면 재고 차감")
  🟩 초록: Read Model (조회 화면)
  🟥 빨강: Hotspot (논쟁, 미해결 문제)

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

### 5. 적용 가이드

```
DDD 점진적 적용:

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

## 참고

- [Domain-Driven Design — Eric Evans](https://www.domainlanguage.com/ddd/)
- [Implementing Domain-Driven Design — Vaughn Vernon](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577)
- [클린 아키텍처](Clean_Architecture.md) — 아키텍처 패턴
- [이벤트 소싱 & CQRS](MSA/이벤트_소싱_및_CQRS.md) — 이벤트 기반 설계
- [Saga 패턴](MSA/Saga_패턴_및_분산_트랜잭션.md) — 분산 트랜잭션
