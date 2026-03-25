---
title: Enum
tags: [Java, Enum, 상수, EnumMap, EnumSet]
updated: 2026-03-25
---

# Enum

## Enum이란

Java에서 상수를 정의할 때 `public static final`로 선언하는 방식은 타입 안전성이 없다.

```java
public class OrderStatus {
    public static final int PENDING = 0;
    public static final int CONFIRMED = 1;
    public static final int SHIPPED = 2;
}

// 이런 코드가 컴파일 에러 없이 통과한다
int status = OrderStatus.PENDING + OrderStatus.CONFIRMED; // 의미 없는 연산
```

Enum은 이 문제를 해결한다. 정해진 값만 사용할 수 있고, 컴파일 타임에 타입 체크가 된다.

```java
public enum OrderStatus {
    PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
}
```

## 필드와 메서드 추가

Enum은 클래스다. 필드, 생성자, 메서드를 가질 수 있다.

```java
public enum OrderStatus {
    PENDING("주문접수", true),
    CONFIRMED("확인완료", true),
    SHIPPED("배송중", false),
    DELIVERED("배송완료", false),
    CANCELLED("취소", false);

    private final String description;
    private final boolean cancellable;

    OrderStatus(String description, boolean cancellable) {
        this.description = description;
        this.cancellable = cancellable;
    }

    public String getDescription() {
        return description;
    }

    public boolean isCancellable() {
        return cancellable;
    }
}
```

```java
OrderStatus status = OrderStatus.SHIPPED;
System.out.println(status.getDescription()); // "배송중"
System.out.println(status.isCancellable());  // false
```

생성자는 `private`만 가능하다. 외부에서 `new OrderStatus()`를 호출할 수 없다.

## 추상 메서드 패턴

각 상수마다 다른 동작이 필요하면 추상 메서드를 선언하고 상수별로 구현한다.

```java
public enum PaymentType {
    CARD {
        @Override
        public long calculateFee(long amount) {
            return (long) (amount * 0.03); // 카드 수수료 3%
        }
    },
    BANK_TRANSFER {
        @Override
        public long calculateFee(long amount) {
            return 500L; // 이체 수수료 고정 500원
        }
    },
    VIRTUAL_ACCOUNT {
        @Override
        public long calculateFee(long amount) {
            return amount >= 10000 ? 0L : 300L;
        }
    };

    public abstract long calculateFee(long amount);
}
```

```java
PaymentType type = PaymentType.CARD;
long fee = type.calculateFee(50000L); // 1500
```

if-else나 switch로 분기하는 것보다 낫다. 새 결제 수단을 추가할 때 `calculateFee` 구현을 빠뜨리면 컴파일 에러가 난다.

## Enum과 인터페이스

Enum이 인터페이스를 구현할 수도 있다. 여러 Enum이 같은 인터페이스를 구현하면 다형성을 쓸 수 있다.

```java
public interface Discountable {
    long applyDiscount(long price);
}

public enum MemberGrade implements Discountable {
    BRONZE {
        @Override
        public long applyDiscount(long price) {
            return price;
        }
    },
    SILVER {
        @Override
        public long applyDiscount(long price) {
            return (long) (price * 0.95);
        }
    },
    GOLD {
        @Override
        public long applyDiscount(long price) {
            return (long) (price * 0.9);
        }
    };
}
```

## EnumSet

특정 Enum 값들의 집합이 필요할 때 `HashSet` 대신 `EnumSet`을 쓴다. 내부적으로 비트 연산을 사용하기 때문에 메모리와 성능 면에서 유리하다.

```java
EnumSet<OrderStatus> activeStatuses = EnumSet.of(
    OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.SHIPPED
);

EnumSet<OrderStatus> inactiveStatuses = EnumSet.complementOf(activeStatuses);
// [DELIVERED, CANCELLED]

EnumSet<OrderStatus> allStatuses = EnumSet.allOf(OrderStatus.class);
```

```java
// 주문 상태가 활성 상태인지 확인
if (activeStatuses.contains(order.getStatus())) {
    // 처리
}
```

주의할 점: `EnumSet`은 `null`을 허용하지 않는다. `null`을 넣으면 `NullPointerException`이 발생한다.

## EnumMap

Enum을 키로 쓰는 Map이 필요하면 `HashMap` 대신 `EnumMap`을 쓴다. 내부적으로 배열 기반이라 해시 충돌이 없고 빠르다.

```java
EnumMap<OrderStatus, String> statusMessages = new EnumMap<>(OrderStatus.class);
statusMessages.put(OrderStatus.PENDING, "주문이 접수되었습니다.");
statusMessages.put(OrderStatus.CONFIRMED, "주문이 확인되었습니다.");
statusMessages.put(OrderStatus.SHIPPED, "상품이 발송되었습니다.");
statusMessages.put(OrderStatus.DELIVERED, "배송이 완료되었습니다.");
statusMessages.put(OrderStatus.CANCELLED, "주문이 취소되었습니다.");
```

```java
String message = statusMessages.get(order.getStatus());
```

## DB 매핑 시 주의사항

### ordinal() 사용 금지

`ordinal()`은 Enum 상수의 선언 순서(0부터 시작)를 반환한다. 이걸 DB에 저장하면 나중에 상수 순서를 바꾸거나 중간에 새 값을 추가할 때 기존 데이터가 꼬인다.

```java
// 절대 하지 말 것
@Column
private int status = OrderStatus.PENDING.ordinal(); // 0
```

PENDING과 CONFIRMED 사이에 `PAYMENT_WAITING`을 추가하면? 기존에 1로 저장된 CONFIRMED 데이터가 전부 `PAYMENT_WAITING`으로 해석된다.

### name()으로 저장

문자열로 저장하는 게 안전하다.

```java
// JPA 사용 시
@Enumerated(EnumType.STRING)
@Column(length = 20)
private OrderStatus status;
```

`@Enumerated(EnumType.ORDINAL)`이 기본값이니까 반드시 `EnumType.STRING`을 명시해야 한다. 빠뜨리면 ordinal로 저장된다.

### name() 변경에 대한 주의

`EnumType.STRING`을 써도 Enum 상수 이름 자체를 변경하면 기존 데이터와 매핑이 깨진다. DB에 `"PENDING"`으로 저장된 데이터가 있는데 상수 이름을 `WAITING`으로 바꾸면 조회할 때 에러가 난다.

상수 이름은 한 번 정하면 바꾸지 않는 게 원칙이다.

### 커스텀 코드 매핑

상수 이름과 DB 저장 값을 분리하고 싶으면 별도 코드를 두고 `AttributeConverter`를 쓴다.

```java
public enum OrderStatus {
    PENDING("P"),
    CONFIRMED("C"),
    SHIPPED("S"),
    DELIVERED("D"),
    CANCELLED("X");

    private final String code;

    OrderStatus(String code) {
        this.code = code;
    }

    public String getCode() {
        return code;
    }

    private static final Map<String, OrderStatus> CODE_MAP =
        Arrays.stream(values())
              .collect(Collectors.toMap(OrderStatus::getCode, Function.identity()));

    public static OrderStatus fromCode(String code) {
        OrderStatus status = CODE_MAP.get(code);
        if (status == null) {
            throw new IllegalArgumentException("Unknown code: " + code);
        }
        return status;
    }
}
```

```java
@Converter(autoApply = true)
public class OrderStatusConverter implements AttributeConverter<OrderStatus, String> {

    @Override
    public String convertToDatabaseColumn(OrderStatus status) {
        return status == null ? null : status.getCode();
    }

    @Override
    public OrderStatus convertToEntityAttribute(String code) {
        return code == null ? null : OrderStatus.fromCode(code);
    }
}
```

이렇게 하면 Enum 상수 이름이 바뀌어도 code 값만 유지하면 DB 데이터에 영향이 없다.

## Enum 싱글턴 패턴

Enum은 JVM이 인스턴스 생성을 보장하기 때문에 싱글턴 구현에 쓸 수 있다. 리플렉션으로도 새 인스턴스를 만들 수 없고, 직렬화/역직렬화 시에도 같은 인스턴스가 유지된다.

```java
public enum AppConfig {
    INSTANCE;

    private String apiUrl;
    private int timeout;

    public void load() {
        // 설정 파일에서 읽기
        this.apiUrl = "https://api.example.com";
        this.timeout = 3000;
    }

    public String getApiUrl() {
        return apiUrl;
    }

    public int getTimeout() {
        return timeout;
    }
}
```

```java
AppConfig.INSTANCE.load();
String url = AppConfig.INSTANCE.getApiUrl();
```

다만 Spring 같은 DI 컨테이너를 쓰고 있다면 굳이 이 패턴을 쓸 필요는 없다. 컨테이너가 이미 싱글턴을 관리해 준다.

## 자주 겪는 실수

### values() 호출 시 배열 복사

`values()`는 호출할 때마다 새 배열을 만들어 반환한다. 반복문 안에서 매번 호출하면 GC 부담이 생긴다.

```java
// 매 호출마다 새 배열 생성
for (int i = 0; i < 10000; i++) {
    for (OrderStatus status : OrderStatus.values()) { // 배열 복사 10000번
        // ...
    }
}

// 캐싱해서 쓰는 게 낫다
private static final OrderStatus[] VALUES = OrderStatus.values();
```

### valueOf() 예외

`valueOf()`에 존재하지 않는 이름을 넘기면 `IllegalArgumentException`이 발생한다. 외부 입력을 받아서 변환할 때는 예외 처리를 해야 한다.

```java
// 사용자 입력을 Enum으로 변환할 때
public static OrderStatus fromString(String value) {
    try {
        return OrderStatus.valueOf(value.toUpperCase());
    } catch (IllegalArgumentException e) {
        throw new InvalidOrderStatusException("잘못된 주문 상태: " + value);
    }
}
```

### switch 문에서 default 처리

Enum에 새 값이 추가될 수 있으니 switch 문에서 default를 넣되, 조용히 넘기지 말고 예외를 던져야 한다.

```java
switch (status) {
    case PENDING:
        // 처리
        break;
    case CONFIRMED:
        // 처리
        break;
    // ...
    default:
        throw new IllegalStateException("처리되지 않은 상태: " + status);
}
```

default에서 로그만 찍고 넘기면 새 상태가 추가됐을 때 문제를 늦게 발견하게 된다.
