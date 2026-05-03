---
title: Enum
tags: [Java, Enum, 상수, EnumMap, EnumSet, 싱글턴, 전략패턴]
updated: 2026-05-03
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

겉보기에는 키워드 하나지만 컴파일러가 만들어내는 결과물은 일반 클래스와 비슷한 형태를 띤다. 어떻게 변환되는지 알아두면 메모리 구조와 싱글턴 보장을 자연스럽게 이해할 수 있다.

## 컴파일 결과와 메모리 구조

`enum` 키워드는 컴파일 시점에 `java.lang.Enum`을 상속하는 `final` 클래스로 변환된다. 위의 `OrderStatus`를 컴파일하고 javap로 까보면 대략 이런 형태가 된다.

```java
public final class OrderStatus extends Enum<OrderStatus> {
    public static final OrderStatus PENDING;
    public static final OrderStatus CONFIRMED;
    public static final OrderStatus SHIPPED;
    public static final OrderStatus DELIVERED;
    public static final OrderStatus CANCELLED;

    private static final OrderStatus[] $VALUES;

    static {
        PENDING = new OrderStatus("PENDING", 0);
        CONFIRMED = new OrderStatus("CONFIRMED", 1);
        SHIPPED = new OrderStatus("SHIPPED", 2);
        DELIVERED = new OrderStatus("DELIVERED", 3);
        CANCELLED = new OrderStatus("CANCELLED", 4);
        $VALUES = new OrderStatus[]{ PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED };
    }

    private OrderStatus(String name, int ordinal) {
        super(name, ordinal);
    }

    public static OrderStatus[] values() {
        return $VALUES.clone();
    }

    public static OrderStatus valueOf(String name) {
        return Enum.valueOf(OrderStatus.class, name);
    }
}
```

여기서 중요한 게 몇 가지 있다.

- 모든 Enum 상수는 클래스 로딩 시점에 `static` 초기화 블록에서 한 번만 생성된다. 즉 `OrderStatus.PENDING` 같은 참조는 **JVM 내에서 단 하나만 존재한다**.
- 상수 객체는 GC 대상이 아니다. 클래스가 언로딩될 때까지 메서드 영역(또는 그 클래스의 ClassLoader가 살아있는 동안 힙에 보관되는 클래스 메타데이터)에 묶여 살아남는다.
- `name`과 `ordinal`은 `Enum` 부모 클래스의 필드다. 직접 정의하지 않아도 자동으로 들어간다.
- `$VALUES`라는 내부 배열이 모든 상수의 참조를 들고 있다. `values()`는 이 배열을 **clone()해서** 반환한다.

상수 자체는 일반 객체와 동일하게 힙에 할당되고, 인스턴스 필드(설명 문자열, 수수료율 같은 것들)도 객체 안에 들어간다. 다만 그 참조를 가리키는 `static` 필드와 `$VALUES` 배열은 클래스 로딩 시 단 한 번만 채워지고 변하지 않는다.

## 싱글턴 보장이 단단한 이유

싱글턴 패턴을 직접 만들어본 적이 있다면 신경 쓸 게 많다는 걸 안다. 멀티스레드 환경에서의 초기화, 직렬화/역직렬화 시 새 인스턴스가 만들어지는 문제, 리플렉션으로 private 생성자를 뚫는 공격 등. Enum은 이걸 모두 JVM 차원에서 막아준다.

- **클래스 로딩의 원자성**: JVM 스펙상 클래스 초기화는 한 스레드만 수행하고 다른 스레드는 대기한다. 즉 `static` 블록에서 만들어지는 상수 인스턴스는 별도 락 없이도 단 한 번만 만들어진다.
- **리플렉션 차단**: `Constructor.newInstance()`는 대상이 Enum이면 `IllegalArgumentException("Cannot reflectively create enum objects")`을 던진다. JDK 내부에서 명시적으로 막아둔다.
- **직렬화 안정성**: 일반 클래스는 역직렬화할 때 `readObject`가 새 인스턴스를 만들지만, Enum은 직렬화 형식이 특별해서 `name()` 문자열만 저장하고 역직렬화 시 `valueOf()`로 기존 상수를 찾아 반환한다. 그래서 직렬화/역직렬화를 거쳐도 `==` 비교가 성립한다.
- **clone() 차단**: `Enum.clone()`은 `final`이고 `CloneNotSupportedException`을 던진다.

이 네 가지 덕분에 Enum 싱글턴은 흔히 말하는 "가장 깨지기 어려운 싱글턴"이다. Effective Java도 이 패턴을 권장한다.

```java
public enum AppConfig {
    INSTANCE;

    private String apiUrl;
    private int timeout;

    public void load() {
        this.apiUrl = "https://api.example.com";
        this.timeout = 3000;
    }

    public String getApiUrl() {
        return apiUrl;
    }
}
```

다만 Spring 같은 DI 컨테이너를 쓰는 환경이라면 굳이 이 패턴을 쓸 이유는 없다. 컨테이너가 이미 싱글턴 빈을 관리해 주고, Enum 싱글턴은 의존성 주입을 받기가 까다롭다(생성자가 닫혀 있어 외부에서 의존성을 넣을 수 없다).

## 필드와 메서드 추가

Enum은 클래스다. 필드, 생성자, 메서드를 가질 수 있다. 생성자는 항상 `private`이다. 외부에서 `new`로 만들 수 없다.

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

    public String getDescription() { return description; }
    public boolean isCancellable() { return cancellable; }
}
```

필드는 `final`로 두는 게 안전하다. 상수가 싱글턴이라 변경 가능한 상태를 두면 모든 사용처가 같은 객체를 공유한다는 걸 잊고 동시성 버그가 생긴다.

## 추상 메서드를 가진 Enum

각 상수마다 동작이 달라야 할 때 추상 메서드를 선언하고 상수별로 구현한다.

```java
public enum PaymentType {
    CARD {
        @Override
        public long calculateFee(long amount) {
            return (long) (amount * 0.03);
        }
    },
    BANK_TRANSFER {
        @Override
        public long calculateFee(long amount) {
            return 500L;
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

여기서 컴파일러가 하는 일을 알아두면 동작이 명확해진다. `CARD { ... }`처럼 본문을 가진 상수는 사실 `PaymentType`의 **익명 서브클래스 인스턴스**다. 컴파일하면 `PaymentType$1`, `PaymentType$2` 같은 익명 클래스 파일이 별도로 생긴다.

즉 추상 메서드를 가진 Enum은 내부적으로 이렇게 변환된다.

```java
public abstract class PaymentType extends Enum<PaymentType> {
    public static final PaymentType CARD = new PaymentType("CARD", 0) {
        @Override public long calculateFee(long amount) { return (long)(amount * 0.03); }
    };
    // ...
    public abstract long calculateFee(long amount);
}
```

그래서 `PaymentType.CARD.getClass()`는 `PaymentType.class`가 아니라 익명 서브클래스의 클래스 객체를 반환한다. `getDeclaringClass()`를 쓰면 부모인 `PaymentType.class`가 나온다. 가끔 클래스 비교를 잘못해서 `equals` 같은 곳에서 헷갈리는 경우가 있다.

if-else나 switch로 분기하는 것보다 이 방식이 확장에 강하다. 새 결제 수단을 추가할 때 `calculateFee` 구현을 빠뜨리면 컴파일 에러가 난다. switch를 쓴 코드는 빠뜨려도 런타임까지 모르고 지나간다.

## Enum으로 구현하는 전략 패턴

전략 패턴은 알고리즘을 객체로 캡슐화하고 런타임에 바꿔 끼우는 패턴이다. 보통 `Strategy` 인터페이스를 만들고 구현 클래스를 여러 개 두는데, 전략의 종류가 고정돼 있고 수가 적다면 Enum이 훨씬 간결하다.

위의 `PaymentType` 예제가 이미 전략 패턴 구현이다. 각 상수가 하나의 전략이고, `calculateFee`가 전략 메서드다. 호출부에서는 다음과 같이 쓴다.

```java
public long processPayment(PaymentType type, long amount) {
    long fee = type.calculateFee(amount);
    return amount + fee;
}
```

타입 자체에 전략이 담겨 있어서 별도의 전략 객체 주입이나 팩토리가 필요 없다. 전략을 식별하는 키와 전략 객체가 분리되지 않는다는 게 장점이다. 클래스 기반 전략 패턴은 `Map<String, Strategy>` 같은 매핑 테이블을 따로 들고 있어야 키로 전략을 찾을 수 있는데, Enum은 그게 필요 없다.

여러 동작을 묶고 싶을 때는 인터페이스를 함께 쓴다.

```java
public interface FeePolicy {
    long calculateFee(long amount);
}

public interface RefundPolicy {
    boolean canRefund(LocalDateTime paidAt);
}

public enum PaymentType implements FeePolicy, RefundPolicy {
    CARD {
        @Override public long calculateFee(long amount) { return (long)(amount * 0.03); }
        @Override public boolean canRefund(LocalDateTime paidAt) {
            return paidAt.isAfter(LocalDateTime.now().minusDays(30));
        }
    },
    BANK_TRANSFER {
        @Override public long calculateFee(long amount) { return 500L; }
        @Override public boolean canRefund(LocalDateTime paidAt) {
            return paidAt.isAfter(LocalDateTime.now().minusDays(7));
        }
    };
}
```

다만 전략의 종류가 동적으로 늘어나거나(플러그인 방식), 외부 의존성을 주입받아야 한다면 Enum 전략은 한계가 있다. 그럴 때는 일반 클래스 기반 전략 패턴이 맞다. Enum 전략은 "값과 동작이 함께 묶여 있고, 종류가 고정된" 경우에 빛난다.

## values()와 valueOf()의 동작

`values()`와 `valueOf()`는 Enum 클래스에 컴파일러가 자동으로 만들어주는 메서드다. `Enum` 부모 클래스에 정의된 게 아니라 각 Enum 클래스마다 독립적으로 생성된다.

### values()

`values()`는 호출할 때마다 내부 `$VALUES` 배열을 `clone()`해서 반환한다. 같은 배열을 그대로 주면 호출자가 배열 내용을 바꿀 위험이 있어서 방어적 복사를 한다.

문제는 이게 **호출할 때마다 일어난다는 것**이다. 반복문 안에서 `values()`를 매번 부르면 매번 새 배열이 만들어지고 GC 부담이 생긴다.

```java
// 반복마다 새 배열 생성 (10000번 복사)
for (int i = 0; i < 10000; i++) {
    for (OrderStatus status : OrderStatus.values()) {
        // ...
    }
}

// 캐싱해서 쓴다
private static final OrderStatus[] VALUES = OrderStatus.values();
```

핫 패스에서 자주 쓴다면 클래스 레벨에 캐싱하거나, `EnumSet.allOf(...)` 같은 컬렉션을 미리 만들어 두는 편이 낫다.

### valueOf()

`valueOf(String)`은 내부적으로 `Enum.valueOf(Class, String)`을 호출하고, 그 메서드는 클래스마다 캐싱된 `Map<String, Enum>`에서 찾는다. 첫 호출 시 한 번 맵을 만들고 이후 재사용하기 때문에 호출 자체는 빠르다.

다만 존재하지 않는 이름을 넘기면 `IllegalArgumentException`이 발생한다. 메시지에 입력값이 그대로 들어가기 때문에 외부 입력을 그대로 넘기면 로그에 사용자 입력이 노출될 수 있다는 점도 주의한다.

```java
public static Optional<OrderStatus> fromString(String value) {
    if (value == null) return Optional.empty();
    try {
        return Optional.of(OrderStatus.valueOf(value.toUpperCase(Locale.ROOT)));
    } catch (IllegalArgumentException e) {
        return Optional.empty();
    }
}
```

대소문자 처리, null 처리, 미존재 처리를 묶어서 `Optional`로 감싸는 헬퍼를 두는 게 호출부를 깔끔하게 만든다. `toUpperCase()`는 반드시 `Locale.ROOT`를 명시한다. 터키어 환경에서 `i`가 `İ`로 변환되는 유명한 버그가 있어서다.

## EnumSet의 성능 이점

`EnumSet`은 Enum 전용 `Set` 구현체다. 내부 구현이 비트마스크라서 `HashSet`보다 메모리도 적게 쓰고 연산도 빠르다.

크기에 따라 두 가지 구현으로 갈린다.

- **RegularEnumSet**: 상수 개수가 64개 이하일 때 사용. 내부에 `long` 하나(64비트)를 두고, 각 비트가 상수 하나의 포함 여부를 나타낸다.
- **JumboEnumSet**: 65개 이상일 때 사용. `long[]` 배열을 두고 비슷하게 비트마스크로 관리한다.

`add`, `remove`, `contains`는 모두 비트 연산 한 번이면 끝난다. `HashSet`처럼 해시 계산, 버킷 탐색, 충돌 처리 같은 게 없다. `union`, `intersection` 같은 집합 연산도 `OR`, `AND` 비트 연산으로 끝나서 압도적으로 빠르다.

```java
EnumSet<OrderStatus> activeStatuses = EnumSet.of(
    OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.SHIPPED
);

EnumSet<OrderStatus> inactiveStatuses = EnumSet.complementOf(activeStatuses);
EnumSet<OrderStatus> allStatuses = EnumSet.allOf(OrderStatus.class);

// 활성 상태인지 검사 — 비트 AND 한 번
if (activeStatuses.contains(order.getStatus())) {
    // ...
}
```

상태 플래그를 비트마스크로 직접 관리하는 코드를 본 적이 있을 것이다. `EnumSet`은 그 효율을 그대로 누리면서 타입 안전성과 가독성을 함께 얻는다. `null`은 허용하지 않으니 넣지 않도록 한다(NPE 발생).

## EnumMap의 성능 이점

`EnumMap`은 Enum을 키로 쓰는 `Map`이다. 내부 구현이 배열이라서 해시 충돌이 없고 메모리 지역성이 좋다.

구체적으로는 키 Enum의 `ordinal()` 값을 인덱스로 사용해 내부 `Object[]`에 값을 직접 저장한다. `put`은 `array[key.ordinal()] = value` 한 줄, `get`은 `array[key.ordinal()]` 한 줄이다. `HashMap`처럼 `hashCode()` 계산도, 버킷 탐색도 없다.

```java
EnumMap<OrderStatus, String> statusMessages = new EnumMap<>(OrderStatus.class);
statusMessages.put(OrderStatus.PENDING, "주문이 접수되었습니다.");
statusMessages.put(OrderStatus.CONFIRMED, "주문이 확인되었습니다.");
statusMessages.put(OrderStatus.SHIPPED, "상품이 발송되었습니다.");
```

생성자에 키 타입의 클래스 객체를 넘겨야 한다. 내부 배열 크기를 결정하기 위해서다. `new HashMap<>()`에 비해 한 단계 더 들어가는 것 같지만 그만큼 얻는 게 크다.

상태별로 핸들러를 매핑하거나, 통계를 카운팅할 때 자주 쓴다.

```java
EnumMap<OrderStatus, AtomicLong> counters = new EnumMap<>(OrderStatus.class);
for (OrderStatus s : OrderStatus.values()) {
    counters.put(s, new AtomicLong());
}
counters.get(order.getStatus()).incrementAndGet();
```

이런 패턴을 `HashMap`으로 짜면 동작은 같지만 성능 차이가 분명하다. 호출 빈도가 높은 곳에서는 `EnumMap`이 기본 선택이다.

## switch와 함께 쓸 때 주의점

Enum과 switch는 잘 어울리지만 알고 써야 할 점이 몇 가지 있다.

### case에 상수 이름만 적는다

switch가 Enum 타입을 알고 있어서 `case OrderStatus.PENDING`이 아니라 `case PENDING`이라고 쓴다. 이걸 모르고 정규화된 이름을 쓰면 컴파일 에러가 난다.

```java
switch (status) {
    case PENDING:    // OK
        break;
    case OrderStatus.CONFIRMED:  // 컴파일 에러
        break;
}
```

### 컴파일러가 만드는 $SwitchMap

Enum switch는 컴파일하면 별도의 합성 클래스(이름이 보통 `OuterClass$1`)에 `$SwitchMap$패키지$EnumName`이라는 `int[]`를 만든다. 그 배열의 인덱스가 Enum의 `ordinal()`이고 값이 case 분기 번호다.

런타임에 switch는 `$SwitchMap[status.ordinal()]`을 읽어 그 결과로 `tableswitch` 바이트코드를 실행한다. 한 단계 indirection이 들어가는 이유는 Enum 상수 순서가 바뀌어도 호출하는 클래스를 다시 컴파일하지 않아도 되도록 하기 위해서다.

이걸 알아두면 두 가지 경우에 도움이 된다.

- **Enum 상수를 추가/순서 변경했는데 switch가 있는 다른 모듈을 다시 컴파일하지 않았다면** 의도치 않게 이전 분기로 빠지거나 default로 떨어진다. JAR를 부분적으로만 교체하는 환경에서 가끔 겪는 문제다. 라이브러리로 배포하는 Enum이라면 더 조심한다.
- **`$SwitchMap` 클래스는 호출하는 쪽에 생성**된다. 같은 Enum을 여러 클래스에서 switch로 쓰면 각 클래스마다 별도의 `$SwitchMap` 배열이 생긴다. 메모리에 큰 영향은 없지만 클래스 파일 수가 늘어난다.

### 새 상수 추가 시 누락 방지

switch는 Enum의 모든 상수를 다루도록 컴파일러가 강제하지 않는다(전통적인 statement switch 기준). 새 상수를 추가하고 switch를 업데이트하지 않으면 default로 빠지거나 아무 분기도 안 타고 그냥 지나간다.

이걸 막으려면 default에 예외를 던진다. 조용히 무시하지 않는다.

```java
switch (status) {
    case PENDING:
        // ...
        break;
    case CONFIRMED:
        // ...
        break;
    default:
        throw new IllegalStateException("처리되지 않은 상태: " + status);
}
```

### switch 표현식과 패턴 매칭 (Java 14+)

Java 14부터 도입된 switch 표현식은 컴파일러가 모든 case를 다뤘는지 검사한다. Enum의 모든 상수를 case로 적었으면 default 없이도 컴파일된다. default를 넣지 않으면 새 상수 추가 시 컴파일 에러가 나서 누락을 강제로 발견할 수 있다.

```java
String message = switch (status) {
    case PENDING -> "주문 접수";
    case CONFIRMED -> "주문 확인";
    case SHIPPED -> "배송 중";
    case DELIVERED -> "배송 완료";
    case CANCELLED -> "취소됨";
};
```

새 상수를 추가하면 위 코드는 컴파일 에러가 난다. 모든 분기를 한 곳에서 강제로 검토하게 된다는 점에서 기존 statement switch보다 안전하다. 가능하면 표현식 형태를 쓴다.

다만 switch 표현식이라 해도 case에서 빠뜨리지 않는 것보다 **추상 메서드를 가진 Enum 패턴이 더 낫다**는 원칙은 유효하다. 분기가 한두 곳이고 단순한 매핑이면 switch가 깔끔하지만, 분기 로직이 길어지거나 같은 분기가 여러 곳에 반복되면 동작을 Enum 안으로 넣는다.

## DB 매핑 시 주의사항

### ordinal() 사용 금지

`ordinal()`은 선언 순서를 반환한다. 이걸 DB에 저장하면 상수 순서를 바꾸거나 중간에 새 값을 추가할 때 기존 데이터가 꼬인다.

```java
// 절대 하지 말 것
@Column
private int status = OrderStatus.PENDING.ordinal(); // 0
```

PENDING과 CONFIRMED 사이에 `PAYMENT_WAITING`을 추가하면? 기존에 1로 저장된 CONFIRMED 데이터가 전부 `PAYMENT_WAITING`으로 해석된다.

### name()으로 저장

문자열로 저장하는 게 안전하다.

```java
@Enumerated(EnumType.STRING)
@Column(length = 20)
private OrderStatus status;
```

`@Enumerated(EnumType.ORDINAL)`이 기본값이라 반드시 `EnumType.STRING`을 명시한다. 빠뜨리면 ordinal로 저장되어 위와 같은 사고가 난다.

### name() 변경 주의

`EnumType.STRING`을 써도 상수 이름 자체를 변경하면 기존 데이터와 매핑이 깨진다. `"PENDING"`으로 저장된 행이 있는데 상수 이름을 `WAITING`으로 바꾸면 조회할 때 에러가 난다. 상수 이름은 한 번 정하면 바꾸지 않는 게 원칙이다.

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

    OrderStatus(String code) { this.code = code; }
    public String getCode() { return code; }

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

상수 이름이 바뀌어도 code 값만 유지하면 DB 데이터에 영향이 없다.

## 정리

Enum을 단순한 상수 모음으로만 쓰는 건 절반만 쓰는 것이다. 컴파일러가 만들어주는 `$VALUES` 배열, JVM이 보장하는 단일 인스턴스, 추상 메서드를 통한 다형성, `EnumSet`/`EnumMap`의 비트 연산·배열 기반 구현, switch와의 결합 방식까지 알고 써야 코드의 구조와 성능 모두 정리된다.

분기 로직이 분산돼 있으면 추상 메서드 패턴으로 모으고, 키-값 매핑이 자주 일어나면 `EnumMap`으로 바꾸고, 부분집합 연산이 많으면 `EnumSet`으로 옮긴다. switch는 표현식 형태로 쓰되 동작이 길어지면 Enum 내부로 옮긴다. 이 정도 원칙만 지켜도 분기 코드가 흩어져서 생기는 버그의 절반은 사라진다.
