---
title: DDD 빌딩 블록 (전술적 설계)
tags: [ddd, tactical-design, entity, value-object, aggregate, repository, domain-service, factory, jpa, hibernate]
updated: 2026-04-17
---

# DDD 빌딩 블록 (전술적 설계)

## 이 문서의 위치

DDD에는 두 축이 있다. 하나는 전략적 설계(Strategic Design)로 Bounded Context를 나누고 Context Map을 그리는 일이다. 다른 하나가 전술적 설계(Tactical Design)로 한 Bounded Context 안의 도메인 모델을 어떻게 코드로 옮길지를 다룬다.

이 문서는 전술적 설계만 깊게 판다. Bounded Context를 어떻게 자를지, 서비스로 어떻게 쪼갤지는 [서비스_분해_및_도메인_설계.md](../MSA/서비스_분해_및_도메인_설계.md)에서 다룬다. 상위 개요는 [DDD.md](../DDD.md)에 있다.

여기서 다루는 주제는 다음과 같다.

- Entity와 Value Object를 어떤 기준으로 구분하나
- Aggregate의 경계를 어디까지 잡아야 하나 — 트랜잭션 일관성 vs 결과적 일관성
- Aggregate 간 참조는 왜 ID로만 해야 하나
- Repository는 누구 단위로 만드나
- Domain Service를 남용하면 왜 Anemic Model이 되나
- Factory는 언제 필요한가
- JPA/Hibernate로 매핑할 때 자주 박히는 덫 — Cascade, FetchType, Lazy Loading

---

## Entity와 Value Object의 구분

### 식별성(Identity)이 기준이다

둘을 가르는 기준은 "같은 값이면 같은 객체로 봐도 되는가"다.

- Entity: ID로 구분된다. 속성이 바뀌어도 같은 Entity다. 예: 회원, 주문, 상품.
- Value Object: 속성 전체가 곧 정체성이다. 속성이 같으면 같은 객체로 본다. 예: 금액, 주소, 기간, 좌표.

주소(Address)로 예를 들어보자. "서울시 강남구 테헤란로 123"이라는 주소가 두 개 있을 때, 이 둘은 같은 주소인가 다른 주소인가. 대부분의 도메인에서는 같다고 본다. 이 관점이 맞으면 Address는 Value Object다.

반대로 회원 "홍길동"이 두 명 있다. 이름이 같다고 같은 사람인가. 아니다. 회원은 고유 ID로 식별한다. 이 관점이 Entity다.

### 같은 개념이 도메인마다 다르게 잡힌다

Money를 예로 들면 대부분의 쇼핑몰 도메인에서는 Value Object다. 1000원은 1000원이다. 그런데 은행 시스템으로 들어가면 돈 한 장 한 장에 고유 일련번호가 찍혀 있고, 자금세탁방지(AML) 관점에서는 어느 계좌에서 어느 경로를 거쳐 왔는지 추적해야 한다. 이때 Money는 Entity가 된다.

즉 Entity냐 VO냐는 "그 대상 자체의 속성"이 아니라 "도메인이 이 대상을 어떻게 다루고 싶은가"에 달렸다. 모델링의 첫 단추는 이 결정을 도메인 전문가와 맞추는 일이다.

### Value Object 구현 원칙

VO는 세 가지를 지켜야 한다.

**1. 불변(Immutable)**

한 번 만들어지면 상태가 바뀌지 않는다. setter가 없어야 한다. 값을 바꾸고 싶으면 새 인스턴스를 만들어서 교체한다.

```java
public final class Money {
    private final long amount;
    private final Currency currency;

    public Money(long amount, Currency currency) {
        if (amount < 0) {
            throw new IllegalArgumentException("금액은 음수가 될 수 없다");
        }
        this.amount = amount;
        this.currency = Objects.requireNonNull(currency);
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalStateException("통화가 다른 금액은 합칠 수 없다");
        }
        return new Money(this.amount + other.amount, this.currency);
    }

    public Money subtract(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalStateException("통화가 다른 금액은 뺄 수 없다");
        }
        long result = this.amount - other.amount;
        if (result < 0) {
            throw new IllegalStateException("결과 금액이 음수다");
        }
        return new Money(result, this.currency);
    }
}
```

불변으로 만들면 공유해도 안전하다. 멀티스레드 환경에서 synchronized가 필요 없다. 한 주문이 가진 `totalPrice`를 다른 스레드가 접근해도 값이 바뀌지 않는다.

**2. equals/hashCode는 모든 필드 기반**

VO의 동일성은 속성 전체로 판단한다. Lombok의 `@EqualsAndHashCode`, Java 16+ record, Kotlin data class를 쓰면 자동으로 생성되지만, 수동으로 쓸 때는 실수가 잦다.

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Money)) return false;
    Money money = (Money) o;
    return amount == money.amount && currency.equals(money.currency);
}

@Override
public int hashCode() {
    return Objects.hash(amount, currency);
}
```

주의할 점은 equals 비교 시 BigDecimal을 쓰는 경우다. `new BigDecimal("1.00")`과 `new BigDecimal("1.0")`은 `equals`로 비교하면 false다. 스케일이 다르기 때문이다. 금액 VO의 equals를 BigDecimal로 구현했는데 "금액이 같은데 왜 다른 객체로 인식하지"라는 버그가 실제로 자주 나온다. `compareTo == 0`으로 비교하거나, 스케일을 생성자에서 정규화해야 한다.

```java
public Money(BigDecimal amount, Currency currency) {
    this.amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.HALF_UP);
    this.currency = currency;
}
```

**3. 자기 검증**

생성자에서 불변식(invariant)을 전부 검증한다. "금액은 음수가 될 수 없다", "종료일은 시작일보다 이후여야 한다" 같은 규칙을 객체 생성 시점에 막아야 한다. 검증을 Service 쪽으로 미루면 VO를 믿을 수 없게 된다. 어디선가 검증을 빠뜨린 흐름에서 잘못된 Money가 만들어지면 이후 모든 계산이 오염된다.

### Entity 구현 원칙

Entity는 equals/hashCode를 ID만으로 한다. 다른 필드를 섞으면 안 된다.

```java
public class Member {
    private final MemberId id;
    private String name;
    private Email email;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Member)) return false;
        Member member = (Member) o;
        return id.equals(member.id);
    }

    @Override
    public int hashCode() {
        return id.hashCode();
    }
}
```

이름이 바뀌어도 같은 회원이다. 이메일을 바꿔도 같은 회원이다. ID만으로 비교해야 이 의미가 성립한다.

여기서 Hibernate를 쓸 때 주의점이 있다. `@Id` 필드가 DB 저장 전까지 null인 경우다. 저장 전 객체와 저장 후 객체를 같은 Set에 넣으면 hashCode가 달라져서 꺼낼 수 없는 상황이 된다. 이 문제를 피하려면 ID를 DB 시퀀스가 아니라 애플리케이션에서 UUID로 선생성하거나, 생성자에서 바로 부여한다.

---

## Aggregate와 Aggregate Root

### Aggregate는 일관성 경계다

Aggregate는 "이 안에 있는 객체들은 한 트랜잭션 안에서 반드시 일관성을 유지해야 한다"는 단위다. 이 경계를 Aggregate Root가 대표한다. 외부에서는 Aggregate Root만 볼 수 있고, 내부 Entity는 Root를 통해서만 접근한다.

주문(Order)을 Aggregate로 본다면 이런 구조가 된다.

```
Order (Root)
├── OrderItem (내부 Entity)
├── OrderItem
├── ShippingAddress (VO)
└── TotalPrice (VO)
```

외부 코드가 OrderItem을 직접 수정하지 못한다. `order.changeItemQuantity(itemId, 3)`처럼 Root를 통해서만 바꾼다. Root가 "주문 확정 후에는 수량을 변경할 수 없다" 같은 불변식을 지키는 책임을 지기 때문이다.

### Aggregate 경계를 어디까지 잡을 것인가

이게 DDD 전술적 설계에서 가장 어려운 판단이다. 크게 잡으면 성능 문제가 생기고, 작게 잡으면 일관성 문제가 생긴다.

판단 기준은 한 가지다. 이 두 객체가 **같은 트랜잭션에서 반드시 함께 변경되어야 하는가**.

같이 변경되어야 한다면 같은 Aggregate로 묶는다. 약간의 시차가 허용되면 다른 Aggregate로 쪼갠다.

주문-주문아이템을 예로 들자. 주문 상태가 "결제 완료"일 때 아이템을 추가하면 주문 총액과 실제 아이템 합이 안 맞는다. 이건 한 트랜잭션 안에서 막아야 한다. 즉 OrderItem은 Order Aggregate 안에 있어야 한다.

반면 주문과 회원의 관계를 보자. 회원 이름이 바뀌었다고 해서 기존 주문의 회원 정보가 즉시 바뀌어야 하는가. 대부분 아니다. 이벤트로 나중에 동기화해도 된다. 즉 Member와 Order는 별도 Aggregate다.

### 트랜잭션 일관성 vs 결과적 일관성

한 트랜잭션 안의 일관성을 **트랜잭션 일관성(Transactional Consistency)**이라 한다. DB 레벨에서 ACID로 보장받는다.

Aggregate 간의 일관성은 **결과적 일관성(Eventual Consistency)**이다. 한동안은 데이터가 안 맞을 수 있고, 일정 시간 후 맞춰진다. 도메인 이벤트, 메시지 큐, Outbox 패턴으로 구현한다.

```
주문 생성 (Order Aggregate 트랜잭션)
  ↓
  주문 저장 + OrderCreated 이벤트 Outbox 저장  ← 한 트랜잭션
  ↓
  이벤트 발행 (다른 트랜잭션)
  ↓
재고 차감 (Stock Aggregate 트랜잭션)
```

주문과 재고 사이에 약간의 시차가 생긴다. 재고가 마이너스로 갈 수도 있다. 이걸 허용할지 말지는 도메인이 정한다. 이커머스에서는 대부분 "일시적 초과판매를 허용하고 관리자가 수동 조정"으로 간다. 항공권이나 호텔처럼 같은 좌석/객실에 두 명이 배정되면 치명적인 도메인은 트랜잭션 일관성으로 묶는다.

### Aggregate 간 참조는 ID로만

한 Aggregate에서 다른 Aggregate를 참조할 때는 객체 레퍼런스가 아니라 ID만 들고 있는다. 주문에서 회원을 참조한다면 `Member member`가 아니라 `MemberId memberId`다.

```java
public class Order {
    private OrderId id;
    private MemberId buyerId;   // Member 객체가 아닌 ID
    private List<OrderItem> items;
    // ...
}
```

ID 참조를 고집하는 이유가 여러 개 있다.

**Aggregate 경계가 지켜진다**

객체 레퍼런스로 물려 있으면 `order.getBuyer().setName("...")`처럼 다른 Aggregate의 상태를 건드리는 코드가 쉽게 생긴다. Aggregate 경계가 허물어지면 일관성 책임이 어디에 있는지가 흐릿해진다. ID로만 참조하면 다른 Aggregate를 바꾸려면 반드시 그쪽 Repository를 거쳐야 한다.

**큰 객체 그래프가 메모리에 끌려오지 않는다**

JPA에서 `@ManyToOne Member buyer`로 잡아 놓으면 주문 하나 조회할 때 회원, 그 회원이 가진 배송지 목록, 포인트 이력까지 줄줄이 딸려올 수 있다. LAZY로 잡아도 프록시 초기화되는 순간 터진다. ID만 들고 있으면 필요할 때만 Member Repository에 질의해서 가져온다.

**분산 환경에서 유리하다**

나중에 주문 서비스와 회원 서비스가 다른 DB, 다른 서버로 갈라질 수 있다. ID 참조로 만들어 놓으면 경계를 따라 쪼개기가 쉽다. 객체 레퍼런스로 물려 있으면 이 경계를 자르는 작업 자체가 큰 리팩터링이 된다.

**순환 참조를 피할 수 있다**

Member가 List<Order>를 들고 있고 Order가 Member를 들고 있으면 양방향 객체 그래프가 된다. 직렬화, toString, equals에서 무한 루프가 난다. ID만 쓰면 이 문제가 원천 차단된다.

### 한 트랜잭션에 Aggregate 하나만 수정

Aggregate 설계 규칙 중 자주 인용되는 것이 "한 트랜잭션에서는 한 Aggregate만 수정한다"다. 두 개 이상의 Aggregate를 같은 트랜잭션에서 바꾸면 Aggregate를 쪼갠 의미가 사라진다. 여러 Aggregate를 함께 바꿔야 하는 흐름이면 Aggregate 경계를 다시 생각해야 한다는 신호로 받는다.

실무에서는 이 규칙을 강하게 지키기 어려운 경우가 있다. 그럴 때는 이벤트로 푼다. Aggregate A의 변경을 커밋한 후 이벤트를 발행하고, 구독자가 Aggregate B를 별도 트랜잭션에서 바꾼다. 이때 이벤트 유실을 막기 위해 [트랜잭셔널 아웃박스 패턴](../MSA/트랜잭셔널_아웃박스_패턴.md)을 쓴다.

---

## Repository

### Aggregate Root당 하나의 Repository

Repository는 Aggregate Root 단위로 만든다. OrderItem Repository, ShippingAddress Repository는 만들지 않는다. 항상 Order Repository다.

이 규칙을 지키지 않으면 Aggregate 경계가 무너진다. OrderItem을 따로 조회해서 따로 저장하면, Order 단위의 불변식(총액 일치, 주문 상태에 따른 수정 제한 등)을 Root가 지킬 수 없다.

```java
public interface OrderRepository {
    Order findById(OrderId id);
    void save(Order order);
    void delete(Order order);
}
```

조회 메서드도 도메인 언어로 쓴다. `findByStatusAndCreatedAtAfter` 같은 DB 질의 조건이 그대로 드러나는 이름보다 `findPendingOrdersOlderThan(Duration)`처럼 도메인 개념으로 올린다.

### 조회 전용 쿼리는 Repository에 넣지 말라

통계 화면, 관리자 리스트처럼 "Aggregate를 로드해서 행위를 수행하는 게 아니라 그냥 표시용 데이터만 뽑아오는" 질의는 Repository에 넣지 않는다. CQRS 관점에서 Query 측은 Aggregate를 우회해서 JPQL, QueryDSL, 네이티브 쿼리, MyBatis로 바로 뽑는다.

Repository에 `findAllForAdminDashboard()` 같은 화면용 메서드가 하나둘 쌓이기 시작하면 Aggregate 모델이 조회 화면의 요구에 끌려다니기 시작한다. 이 둘을 분리하는 게 장기적으로 모델을 지키는 방법이다. [이벤트_소싱_및_CQRS](../MSA/이벤트_소싱_및_CQRS.md)에서 이 갈라짐을 더 깊이 다룬다.

---

## Domain Service

### Domain Service가 필요한 순간

어떤 비즈니스 로직이 "한 Entity/VO 안에 자연스럽게 놓이지 않을 때" Domain Service를 쓴다. 특히 두 Aggregate에 걸친 로직이 대표적이다.

환전 로직을 예로 들자.

```java
public class CurrencyExchangeService {
    private final ExchangeRateRepository exchangeRateRepository;

    public Money exchange(Money source, Currency target) {
        if (source.getCurrency().equals(target)) {
            return source;
        }
        ExchangeRate rate = exchangeRateRepository.findLatest(source.getCurrency(), target);
        return rate.apply(source);
    }
}
```

환전은 Money 한 개 안의 연산으로 끝나지 않는다. 환율(ExchangeRate)이라는 별도 Aggregate가 필요하다. 이럴 때 Domain Service가 중재자 역할을 한다.

### Domain Service ≠ Application Service

둘을 자주 섞는다. 차이는 이렇다.

- **Domain Service**: 순수 도메인 로직만. 트랜잭션, 권한, 로깅, 외부 시스템 호출을 알지 않는다.
- **Application Service (Use Case)**: 유스케이스를 조율한다. 트랜잭션 시작/종료, 권한 체크, Repository에서 Aggregate 로드/저장, Domain Service 호출.

실무 코드에서 자주 보이는 실수가 Application Service에 도메인 로직이 들어가는 것이다. "주문 생성" 유스케이스에서 할인 계산, 재고 검증, 총액 산출을 Application Service가 직접 하면, 같은 로직이 "주문 수정", "주문 복제" 유스케이스에서 복사된다. 이 로직은 Domain Service나 Aggregate 안에 있어야 한다.

### Domain Service 남용이 Anemic Model을 만든다

Domain Service를 "애매한 로직을 담는 쓰레기통"으로 쓰면 Entity와 VO는 getter/setter만 가진 데이터 컨테이너가 된다. 이게 Anemic Domain Model이다. 객체지향의 이점이 사라지고 절차적 프로그래밍으로 회귀한다.

판단 기준은 "이 로직이 한 Aggregate 안에서 처리될 수 있나"를 먼저 묻는 것이다. 처리될 수 있으면 Aggregate에 넣는다. 두 개 이상의 Aggregate에 걸쳐야만 말이 되면 그때 Domain Service로 뺀다.

```java
// 나쁜 예 — 할인 계산을 Service로 뽑아놨다
public class DiscountService {
    public Money calculateDiscount(Order order, Coupon coupon) {
        if (order.getTotalPrice().isGreaterThan(coupon.getMinOrderAmount())) {
            return coupon.apply(order.getTotalPrice());
        }
        return Money.ZERO;
    }
}

// 좋은 예 — Order 안에서 처리한다
public class Order {
    public void applyCoupon(Coupon coupon) {
        if (this.status != OrderStatus.DRAFT) {
            throw new IllegalStateException("초안 상태에서만 쿠폰을 적용할 수 있다");
        }
        this.appliedDiscount = coupon.calculateDiscountFor(this.totalPrice);
    }
}
```

두 번째 예에서 Order가 "초안 상태에서만 쿠폰 적용 가능"이라는 불변식을 직접 지킨다. 이게 Rich Domain Model이다.

---

## Factory

### 복잡한 생성 로직을 분리한다

Aggregate 하나를 만들 때 여러 단계의 검증, 다른 Aggregate와의 협업, 순서 있는 초기화가 필요할 때 Factory를 쓴다. 생성 책임을 Aggregate Root에 두면 Root가 다른 Aggregate나 Repository를 의존해야 하므로 모델이 더러워진다.

```java
public class OrderFactory {
    private final ProductRepository productRepository;
    private final MemberRepository memberRepository;

    public Order createOrder(MemberId buyerId, List<OrderItemRequest> requests, CouponCode couponCode) {
        Member buyer = memberRepository.findById(buyerId);
        if (!buyer.canPlaceOrder()) {
            throw new IllegalStateException("주문 자격이 없는 회원이다");
        }

        List<OrderItem> items = requests.stream()
            .map(req -> {
                Product product = productRepository.findById(req.productId());
                return new OrderItem(product.getId(), product.getCurrentPrice(), req.quantity());
            })
            .toList();

        Order order = new Order(OrderId.newId(), buyerId, items);
        if (couponCode != null) {
            order.applyCoupon(couponCode);
        }
        return order;
    }
}
```

Factory가 Repository에 의존하는 건 허용된다. Aggregate 자체에 Repository를 끼워 넣는 것보다 낫다.

### Factory가 필요 없는 경우도 많다

생성 로직이 단순한 Aggregate는 생성자만으로 충분하다. Factory를 일률적으로 만들면 단순한 생성에도 두 개의 클래스를 건너야 한다. "Order를 만드는 데 다른 Aggregate 정보가 필요하다" 같은 신호가 있을 때만 꺼낸다.

정적 팩터리 메서드도 좋은 선택이다. `Order.create(...)`, `Order.reconstitute(...)`처럼 의도를 드러내는 이름을 붙인다. 특히 `reconstitute`는 DB에서 로드한 상태를 복원할 때 쓰는데, `create`와 다른 불변식 검증(이미 과거에 유효했던 상태이므로 현재 검증을 건너뛴다)이 필요할 때 분리한다.

---

## JPA/Hibernate로 Aggregate 매핑할 때의 덫

### Cascade 설정을 잘못 걸면 일관성이 깨진다

Aggregate Root와 내부 Entity의 관계에는 대부분 `CascadeType.ALL + orphanRemoval = true`를 건다. Root의 생명주기가 내부 Entity의 생명주기를 지배하기 때문이다.

```java
@Entity
public class Order {
    @Id
    private Long id;

    @OneToMany(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "order_id")
    private List<OrderItem> items = new ArrayList<>();
}
```

자주 하는 실수 세 가지가 있다.

**1. Aggregate 간에 Cascade를 거는 실수**

Order와 Member처럼 서로 다른 Aggregate 관계에 Cascade를 걸면 안 된다. 주문을 저장할 때 회원 정보까지 덮어써지거나, 주문을 삭제했더니 회원이 같이 삭제되는 참사가 난다. 앞서 말한 "Aggregate 간 참조는 ID로"를 지키면 이 실수가 원천 차단된다.

**2. orphanRemoval을 빼먹는 실수**

`CascadeType.REMOVE`만 걸고 `orphanRemoval`을 안 걸면, 부모에서 자식 컬렉션을 `clear()`했을 때 자식이 삭제되지 않는다. 외래키가 null인 고아 레코드가 남는다. Aggregate 내부 Entity라면 항상 `orphanRemoval = true`를 같이 건다.

**3. Cascade.PERSIST만 쓰는 실수**

`CascadeType.PERSIST`만 걸면 새로 만든 Order를 저장할 때는 OrderItem까지 저장되지만, 기존 Order에 OrderItem을 추가했을 때는 안 된다. `MERGE`, `REMOVE`까지 포함된 `ALL`을 쓰거나 필요한 전파를 빠짐없이 적는다.

### FetchType 기본값의 비대칭

JPA 기본값이 관계 종류마다 다르다.

- `@OneToMany`, `@ManyToMany` → LAZY
- `@ManyToOne`, `@OneToOne` → EAGER

`@ManyToOne`이 EAGER라는 점을 모르면 예상치 못한 쿼리 폭탄을 맞는다. OrderItem에서 Product를 `@ManyToOne`으로 잡아 놓고 OrderItem 1000개를 조회했는데, Product가 1000번 추가로 조회되는 N+1이 났는데, "왜 난 LAZY로 했는데 이럴까" 하면 보통 이 함정이다. 설정을 안 했으니 EAGER였던 것이다.

모든 연관을 명시적으로 LAZY로 잡는 것이 표준 관행이다. EAGER가 필요한 시점은 거의 없고, 필요하면 쿼리 단위에서 fetch join으로 해결한다.

```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "product_id")
private Product product;
```

### Lazy Loading과 Aggregate 경계의 충돌

이게 Aggregate 매핑에서 가장 다루기 까다로운 문제다.

Order가 OrderItem 컬렉션을 LAZY로 들고 있다 치자. Application Service가 트랜잭션 안에서 `order.getItems().size()`를 호출하면 잘 동작한다. 그런데 이 Order를 JSON으로 직렬화해서 Controller가 응답으로 내려보내려고 하면, 트랜잭션이 이미 끝난 상태에서 `getItems()`가 호출되어 `LazyInitializationException`이 터진다.

해결 방법이 몇 가지 있다.

**1. Aggregate를 Application Service 바깥으로 내보내지 않는다**

Controller에는 DTO를 내려보낸다. Aggregate를 그대로 JSON으로 노출하는 건 Aggregate 불변식을 외부에 흘리는 셈이기도 하다. DTO 변환은 트랜잭션 안에서 끝낸다.

**2. `Open Session In View`에 의존하지 않는다**

Spring Boot의 기본값이 `spring.jpa.open-in-view=true`다. View 렌더링까지 세션이 열려 있어서 Lazy 프록시가 초기화된다. 단기적으로 편하지만, 쿼리가 Controller나 View 단에서 무작위로 튀어서 성능 튜닝 지점을 찾기 어려워진다. 팀 단위로 `false`로 끄고, 트랜잭션 안에서 필요한 데이터를 다 로드하는 원칙을 잡는 편이 낫다.

**3. 필요한 연관은 fetch join으로 한 번에 로드**

특정 유스케이스에서 Order와 함께 OrderItem이 필요하면 쿼리 단위로 fetch join을 건다.

```java
@Query("select o from Order o join fetch o.items where o.id = :id")
Optional<Order> findByIdWithItems(@Param("id") OrderId id);
```

한 쿼리에 여러 OneToMany를 join fetch하면 `MultipleBagFetchException`이 난다. 이땐 `@OrderColumn`을 쓰거나, Set으로 바꾸거나, 일부를 `@BatchSize`로 빼서 IN 쿼리로 끌어오는 방식으로 우회한다.

### @Embeddable로 Value Object 매핑

Value Object는 `@Embeddable`로 매핑한다. 별도 테이블이 아니라 부모 테이블의 컬럼으로 풀어 넣는다.

```java
@Embeddable
public class Money {
    @Column(name = "amount")
    private long amount;

    @Column(name = "currency")
    @Enumerated(EnumType.STRING)
    private Currency currency;

    protected Money() {}  // JPA 기본 생성자 — package-private

    public Money(long amount, Currency currency) {
        // ... 검증
    }
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

주의점이 몇 가지 있다.

JPA가 기본 생성자를 요구한다. VO의 불변 원칙과 충돌하는 지점이다. 이걸 타협하는 방법으로는 기본 생성자를 `protected`로 두고 `final` 필드를 포기하되 setter는 만들지 않는 방식이 일반적이다. Kotlin data class나 Java record는 JPA와 궁합이 좋지 않아서 VO 용도로는 평범한 클래스를 쓰게 된다(Hibernate 6부터 record 지원이 개선되고 있다).

한 Entity 안에 같은 타입의 VO를 두 개 이상 넣으려면 `@AttributeOverrides`로 컬럼명을 분리한다. 배송지와 청구지를 둘 다 `Address`로 두면 `@Embedded Address shippingAddress`, `@Embedded Address billingAddress` 각각에 오버라이드가 필요하다.

VO 컬렉션은 `@ElementCollection`으로 매핑한다. 별도 테이블이 생기고, 부모 ID가 외래키가 된다. 단 이 방식은 성능 특성이 낯설다. 컬렉션을 수정할 때마다 전체 삭제 후 재삽입이 일어나는 경우가 있다. 대량의 VO 컬렉션은 차라리 별도 Entity로 올려서 Aggregate 내부 Entity로 관리하는 편이 성능상 낫다.

### 식별자 타입을 Long으로만 두지 말라

`Long id`만 들고 다니면 타입 안정성이 없다. MemberId와 OrderId가 둘 다 `Long`이면 파라미터 순서를 헷갈렸을 때 컴파일러가 잡아주지 못한다.

```java
@Embeddable
public class OrderId {
    @Column(name = "id")
    private Long value;

    protected OrderId() {}

    public OrderId(Long value) {
        this.value = Objects.requireNonNull(value);
    }

    public static OrderId newId() {
        return new OrderId(SnowflakeIdGenerator.next());
    }
}
```

`@EmbeddedId`나 `@IdClass`로 묶으면 매핑이 다소 번거로워진다. Hibernate의 `@Type`으로 커스텀 UserType을 등록하는 방법도 있다. 팀 합의에 따라 과감하게 `Long id`를 쓰되 Repository 시그니처만 타입 안전하게 유지하는 절충도 가능하다.

---

## Entity 식별자 생성 시점

### DB 시퀀스 vs 애플리케이션 선생성

ID를 언제 부여하느냐가 Aggregate 설계에 은근히 영향을 준다.

`@GeneratedValue(strategy = IDENTITY)`나 DB 시퀀스를 쓰면 `persist()` 전까지 ID가 null이다. 그래서 도메인 이벤트를 발행할 때 Aggregate ID가 비어 있는 상태로 이벤트가 나갈 수 있다. 또 ID 기반 equals/hashCode가 Set에서 이상하게 동작한다.

UUID나 Snowflake ID를 애플리케이션에서 선생성하면 이 문제가 사라진다.

```java
public class Order {
    private OrderId id;

    private Order(OrderId id, MemberId buyerId) {
        this.id = id;
        this.buyerId = buyerId;
    }

    public static Order place(MemberId buyerId, List<OrderItem> items) {
        Order order = new Order(OrderId.newId(), buyerId);
        order.addItems(items);
        order.register(new OrderPlacedEvent(order.id, buyerId));  // ID가 이미 있다
        return order;
    }
}
```

Snowflake가 분산 환경에서도 정렬 가능한 ID라는 장점 때문에 많이 쓴다. UUID v4는 완전 랜덤이라 인덱스 성능이 떨어지고, UUID v7이 최근 표준에 올라왔는데 시간 기반이라 인덱스 친화적이다. 팀 상황에 맞게 고른다.

---

## 정리: 설계 결정 흐름

한 도메인 요소를 모델링할 때 거치는 결정 흐름을 정리하면 이렇다.

```
이 객체는 ID로 구분되는가?
├─ 예 → Entity
│   ├─ 이 Entity가 일관성 경계의 Root인가?
│   │   ├─ 예 → Aggregate Root (Repository 필요)
│   │   └─ 아니오 → Aggregate 내부 Entity (Root 통해서만 접근)
└─ 아니오 → Value Object (불변, equals는 모든 필드)

이 비즈니스 로직은 어디에 두나?
├─ 한 Aggregate 안에서 처리 가능한가?
│   ├─ 예 → Aggregate Root 또는 내부 Entity/VO의 메서드
│   └─ 아니오 → Domain Service (두 개 이상의 Aggregate 필요할 때만)

이 객체를 만들 때 복잡한 협업이 필요한가?
├─ 예 → Factory (Repository/다른 Aggregate 조회 필요)
└─ 아니오 → 생성자 또는 정적 팩터리 메서드
```

이 흐름을 기계적으로 따르는 게 아니라, 각 분기에서 "왜 이쪽인가"를 도메인 전문가와 이야기하며 맞춰야 한다. DDD는 코드 패턴 카탈로그가 아니라 모델링에 대한 사고방식이다. Entity/VO/Aggregate는 그 사고를 코드로 표현하기 위한 어휘일 뿐이다.

---

## 참고

- Eric Evans, *Domain-Driven Design* (2003)
- Vaughn Vernon, *Implementing Domain-Driven Design* (2013)
- Vaughn Vernon, *Effective Aggregate Design* (IBM developerWorks 3부작 논문)
- Martin Fowler, "AnemicDomainModel" — martinfowler.com
