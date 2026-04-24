---
title: Java Builder Pattern
tags: [language, java, 객체지향-프로그래밍-oop, builder-pattern, lombok]
updated: 2026-04-24
---

# Java Builder Pattern

## 왜 빌더 패턴이 필요한가

생성자에 매개변수가 4개를 넘기 시작하면 코드가 눈에 안 들어온다. 실무에서 흔히 보는 패턴이 "텔레스코핑 생성자"다.

```java
public class Order {
    public Order(String orderId, String userId, String productId,
                 int quantity, String address, String couponCode,
                 boolean isGift, String giftMessage) { ... }
}
```

이걸 쓰는 쪽에서는 이렇게 된다.

```java
new Order("ORD-001", "USR-123", "PRD-456", 2, "서울시 강남구", null, true, null);
```

`null`이 몇 개인지, 세 번째 `null`이 쿠폰인지 선물 메시지인지 알 수 없다. 필드가 추가될 때마다 생성자를 하나씩 더 만들거나 기존 생성자 시그니처를 바꿔야 한다.

자바빈즈 패턴(setter 방식)으로 대안을 잡으면 객체가 완전히 구성되기 전 중간 상태가 노출된다. `setOrderId()` 직후 `setUserId()` 이전 타이밍에 누군가 그 객체를 참조하면 일관성이 깨진다. `final` 필드도 쓸 수 없다.

빌더 패턴은 이 두 문제를 동시에 잡는다. 생성 과정과 최종 객체를 분리하고, `build()` 호출 전까지 실제 객체를 만들지 않는다.

---

## 직접 구현

### 기본 구조

```java
public class Order {
    private final String orderId;    // 필수
    private final String userId;     // 필수
    private final String productId;  // 필수
    private final int quantity;      // 필수
    private final String address;    // 필수
    private final String couponCode; // 선택
    private final boolean isGift;    // 선택
    private final String giftMessage;// 선택

    private Order(Builder builder) {
        this.orderId = builder.orderId;
        this.userId = builder.userId;
        this.productId = builder.productId;
        this.quantity = builder.quantity;
        this.address = builder.address;
        this.couponCode = builder.couponCode;
        this.isGift = builder.isGift;
        this.giftMessage = builder.giftMessage;
    }

    public static class Builder {
        private final String orderId;
        private final String userId;
        private final String productId;
        private final int quantity;
        private final String address;
        private String couponCode;
        private boolean isGift;
        private String giftMessage;

        public Builder(String orderId, String userId, String productId,
                       int quantity, String address) {
            this.orderId = orderId;
            this.userId = userId;
            this.productId = productId;
            this.quantity = quantity;
            this.address = address;
        }

        public Builder couponCode(String couponCode) {
            this.couponCode = couponCode;
            return this;
        }

        public Builder isGift(boolean isGift) {
            this.isGift = isGift;
            return this;
        }

        public Builder giftMessage(String giftMessage) {
            this.giftMessage = giftMessage;
            return this;
        }

        public Order build() {
            return new Order(this);
        }
    }
}
```

필수값은 빌더 생성자에 넣고, 선택값은 메서드로 뺀다. `Order`의 생성자는 `private`으로 막아서 빌더를 거치지 않으면 생성이 안 된다.

```java
Order order = new Order.Builder("ORD-001", "USR-123", "PRD-456", 2, "서울시 강남구")
    .couponCode("SUMMER10")
    .isGift(true)
    .giftMessage("생일 축하해요")
    .build();
```

### build() 내 필수값 검증

빌더 생성자에 필수값을 강제해도, 런타임에 `null`이 들어오는 경우는 막아야 한다. `build()`에서 검증한다.

```java
public Order build() {
    if (orderId == null || orderId.isBlank()) {
        throw new IllegalStateException("orderId는 필수입니다");
    }
    if (quantity <= 0) {
        throw new IllegalStateException("quantity는 1 이상이어야 합니다");
    }
    if (isGift && (giftMessage == null || giftMessage.isBlank())) {
        throw new IllegalStateException("선물 주문에는 giftMessage가 필요합니다");
    }
    return new Order(this);
}
```

생성자에서 검증하는 것과 동일하지만, 빌더 패턴에서는 복합 조건(isGift + giftMessage처럼 두 필드 간 의존 관계)을 이 시점에 처리하기 수월하다.

---

## Lombok @Builder

직접 구현은 보일러플레이트가 많다. 실무에서는 Lombok을 쓴다.

```java
@Builder
public class Order {
    private final String orderId;
    private final String userId;
    private final String productId;
    private final int quantity;
    private final String address;
    private String couponCode;
    private boolean isGift;
    private String giftMessage;
}
```

```java
Order order = Order.builder()
    .orderId("ORD-001")
    .userId("USR-123")
    .productId("PRD-456")
    .quantity(2)
    .address("서울시 강남구")
    .couponCode("SUMMER10")
    .build();
```

`@Builder`는 모든 필드를 선택값으로 처리한다. 필수값 강제가 필요하면 `@NonNull`을 쓴다.

```java
@Builder
public class Order {
    @NonNull private final String orderId;
    @NonNull private final String userId;
    private String couponCode;
}
```

`@NonNull`은 빌더가 아닌 생성자 레벨에서 체크한다. `null`을 넣으면 `NullPointerException`이 발생한다.

### @Builder 기본값 설정

`@Builder`는 기본값을 자동으로 잡지 않는다. 아래처럼 쓰면 `isGift`는 기본값 `false`가 아니라 항상 `false`인데, 이건 자바 기본값이지 Lombok이 처리한 게 아니다.

```java
@Builder
public class Order {
    @Builder.Default
    private boolean isGift = false;

    @Builder.Default
    private int quantity = 1;
}
```

`@Builder.Default`를 붙이지 않으면 `Order.builder().build()`로 생성했을 때 `quantity`가 `0`이 된다. 명시적으로 `@Builder.Default`를 써야 의도한 기본값이 적용된다.

---

## @SuperBuilder — 상속 구조에서의 빌더

부모 클래스에 `@Builder`가 붙어있고 자식 클래스도 빌더가 필요하면 `@SuperBuilder`를 써야 한다.

```java
@SuperBuilder
public class BaseEntity {
    private final Long id;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;
}

@SuperBuilder
public class User extends BaseEntity {
    private final String email;
    private final String name;
}
```

```java
User user = User.builder()
    .id(1L)
    .createdAt(LocalDateTime.now())
    .email("user@example.com")
    .name("홍길동")
    .build();
```

`@SuperBuilder`를 쓰지 않고 자식 클래스에만 `@Builder`를 붙이면 컴파일 오류가 난다.

```
error: constructor User in class User cannot be applied to given types
```

부모 클래스 필드를 빌더 체인에 포함할 수 없기 때문이다. 계층 구조 전체에 `@SuperBuilder`를 붙여야 한다. 부모 하나만 `@Builder`로 두면 자식 클래스에서 `@SuperBuilder`를 써도 오류가 난다.

---

## 불변 객체와 final 필드

빌더 패턴의 장점 중 하나는 불변 객체를 자연스럽게 만든다는 점이다. 모든 필드를 `final`로 선언하고 setter를 두지 않으면, 생성 이후 상태 변경이 불가능하다.

```java
@Builder
public class UserInfo {
    private final String userId;
    private final String email;
    private final String name;
    private final Role role;
}
```

JPA Entity는 `final`과 기본 생성자 요구 사항이 충돌해서 불변으로 만들기 어렵다. DTO나 Value Object는 `final`을 써도 문제없다. Entity는 뒤에서 따로 다룬다.

---

## Spring 실무 사용 패턴

### DTO

요청/응답 DTO는 빌더가 어울린다. 특히 테스트 코드에서 픽스처를 만들 때 가독성이 좋다.

```java
@Builder
@Getter
public class OrderRequest {
    @NotNull
    private String productId;
    @Min(1)
    private int quantity;
    private String couponCode;
    private String address;
}
```

```java
// 테스트 픽스처
OrderRequest request = OrderRequest.builder()
    .productId("PRD-001")
    .quantity(2)
    .address("서울시 강남구")
    .build();
```

### Entity

JPA Entity에 `@Builder`를 붙이는 경우가 많다. 주의할 점이 있다.

JPA는 프록시 생성을 위해 기본 생성자가 필요하다. `@Builder`만 붙이면 Lombok이 전체 필드를 받는 생성자를 만들고 기본 생성자는 안 만든다. `@NoArgsConstructor`와 함께 써야 한다.

```java
@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Builder
public class Order {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userId;

    @Column(nullable = false)
    private String productId;

    private int quantity;
    private String address;
    private String couponCode;
}
```

`@NoArgsConstructor(access = AccessLevel.PROTECTED)`로 외부에서 직접 기본 생성자를 호출하는 걸 막는다. JPA 내부에서만 쓸 수 있다.

`@Builder`와 `@NoArgsConstructor`를 같이 쓰면 Lombok이 두 생성자 간 충돌을 일으키는 경우가 있다. 이때는 `@AllArgsConstructor`를 추가로 붙인다.

```java
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
```

---

## 빌더 패턴 남용

필드가 2~3개인 객체에 빌더를 쓰는 경우가 있다.

```java
@Builder
public class PageRequest {
    private int page;
    private int size;
}

// 쓰는 쪽
PageRequest req = PageRequest.builder().page(1).size(10).build();
```

이 정도 객체는 생성자나 정적 팩터리 메서드가 낫다.

```java
public class PageRequest {
    public static PageRequest of(int page, int size) {
        return new PageRequest(page, size);
    }
}
```

빌더는 코드량이 늘고 객체 생성에 빌더 인스턴스가 하나 더 생긴다. 단순한 경우에는 오버엔지니어링이다. 필드가 4개 이상이거나 선택적 필드가 많을 때 쓰는 게 맞다.

---

## 자주 겪는 문제

**@Builder와 Jackson 역직렬화**

Jackson이 JSON을 객체로 변환할 때 기본 생성자가 없으면 오류가 난다. `@Builder`만 있으면 `@JsonDeserialize(builder = ...)` 설정이 필요하거나 `@Jacksonized`를 붙여야 한다.

```java
@Builder
@Jacksonized
public class OrderRequest {
    private String productId;
    private int quantity;
}
```

`@Jacksonized`는 Lombok 1.18.14부터 지원한다. 이전 버전이면 직접 `@JsonDeserialize`를 설정해야 한다.

**빌더 재사용**

빌더 인스턴스는 재사용하면 안 된다. `build()`를 두 번 호출해도 새 객체가 생기지만, 중간에 메서드를 호출하면 이전 빌드 결과에는 반영되지 않는다.

```java
Order.Builder builder = Order.builder().userId("USR-001");
Order a = builder.productId("PRD-001").build();
Order b = builder.productId("PRD-002").build(); // builder 상태가 PRD-002로 변경된 상태

// a.productId는 "PRD-001", b.productId는 "PRD-002"처럼 보이지만
// builder 필드는 마지막 set 값이므로 실제로는 두 객체 모두 "PRD-002"를 참조한다
// (직접 구현체에 따라 다를 수 있음)
```

매 생성마다 새 빌더 인스턴스를 만드는 게 안전하다.
