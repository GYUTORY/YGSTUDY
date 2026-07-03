---
title: Java 고급 클래스 기능 심화 가이드
tags: [language, java, 객체지향-프로그래밍-oop, class, advancedclass, sealed-class, record, inner-class, anonymous-class]
updated: 2026-04-26
---

## 들어가며

Java 클래스를 어느 정도 다뤄봤다면 `class`, `extends`, `implements` 키워드는 손에 익었을 것이다. 그런데 실무에서 코드를 읽다 보면 중첩 클래스 안에 또 익명 클래스가 있고, sealed로 도메인 모델을 닫아두고, record로 DTO를 선언해두는 코드가 나타난다. 이런 고급 기능들은 단순히 "있으니까 쓴다"가 아니라 각자 해결하려는 문제가 명확하다.

이 문서는 클래스의 기본 개념(상속, 접근 제어자, 인터페이스 구현 등)은 안다고 가정하고, 실무에서 자주 충돌하거나 메모리 누수의 원인이 되는 고급 기능들을 다룬다. 컴파일러가 어떻게 합성 클래스를 만들어내는지, 람다와 익명 클래스가 바이트코드 레벨에서 어떻게 다른지, sealed/record 같은 최신 문법을 도메인 모델링에 어떻게 녹이는지를 중심으로 설명한다.

---

## 1. 중첩 클래스의 4가지 형태와 컴파일러 동작

Java의 중첩 클래스는 보통 4가지로 분류한다. 정적 중첩 클래스(static nested class), 멤버 내부 클래스(inner class), 지역 클래스(local class), 익명 클래스(anonymous class). 이름은 비슷하지만 외부 클래스와의 관계, 컴파일된 결과물, 메모리 점유 방식이 모두 다르다.

### 정적 중첩 클래스 vs 멤버 내부 클래스

가장 큰 차이는 외부 클래스 인스턴스에 대한 암묵적 참조 보유 여부다. `static` 키워드를 붙이면 정적 중첩 클래스가 되고, 외부 클래스 인스턴스 없이도 단독으로 생성할 수 있다. 반면 `static`이 없는 멤버 내부 클래스는 항상 외부 클래스 인스턴스를 통해서만 만들 수 있고, 컴파일 시 외부 인스턴스를 가리키는 합성 필드 `this$0`이 자동으로 추가된다.

이 합성 필드가 실무에서 메모리 누수의 단골 원인이다. 내부 클래스 인스턴스가 살아있는 한, 외부 클래스 인스턴스도 GC 대상이 되지 않는다. 캐시나 정적 컬렉션에 내부 클래스 객체를 넣어두면 외부 객체까지 따라 살아남는다.

```java
public class OuterContainer {
    private byte[] heavyData = new byte[10 * 1024 * 1024]; // 10MB

    // 외부 인스턴스를 암묵적으로 참조함
    public class LeakyInner {
        public void doSomething() {
            System.out.println("inner work");
        }
    }

    // 외부 인스턴스를 참조하지 않음
    public static class SafeNested {
        public void doSomething() {
            System.out.println("nested work");
        }
    }
}
```

`LeakyInner` 인스턴스를 어딘가에 오래 보관하면 `heavyData` 10MB도 같이 살아남는다. 외부 상태가 정말 필요하지 않다면 항상 `static`을 붙이는 습관이 안전하다. IntelliJ는 외부 참조를 쓰지 않는 내부 클래스에 대해 "Inner class may be 'static'" 경고를 띄우는데, 이걸 무시하지 말아야 한다.

### 지역 클래스와 익명 클래스의 effectively final 제약

메서드 안에서 정의되는 지역 클래스와 익명 클래스는 외부 메서드의 지역 변수를 캡처할 수 있다. 단, Java 8부터는 이 변수가 `effectively final`이어야 한다. 명시적으로 `final` 키워드를 붙이지 않아도 한 번만 할당되면 컴파일러가 final로 간주한다.

```java
public Runnable makeTask(String prefix) {
    int counter = 0;
    // counter++; // 이 라인을 추가하면 아래 람다/익명 클래스가 컴파일 에러

    return new Runnable() {
        @Override
        public void run() {
            // prefix와 counter는 캡처되어 사용 가능
            System.out.println(prefix + ":" + counter);
        }
    };
}
```

이 제약이 존재하는 이유는 캡처가 값 복사로 이뤄지기 때문이다. 컴파일러는 익명 클래스에 합성 필드를 만들고 생성자 호출 시 외부 변수 값을 복사해 넣는다. 만약 외부에서 변수가 바뀌어도 익명 클래스 내부의 복사본은 변경되지 않으므로, 두 값이 어긋나는 혼란을 막기 위해 처음부터 변경 자체를 금지한 것이다.

이 제약을 우회하려면 배열이나 가변 객체로 감싸야 한다. 다만 이 패턴이 자주 보인다면 클로저 흉내를 내는 것보다 명시적인 클래스로 상태를 관리하는 게 가독성에 좋다.

```java
public Runnable makeCounter() {
    int[] counter = {0}; // 배열로 감싸면 참조 자체는 final이지만 내용은 변경 가능
    return () -> {
        counter[0]++;
        System.out.println(counter[0]);
    };
}
```

### 컴파일 결과물 확인하기

중첩 클래스는 컴파일 시 외부 클래스와 별도의 `.class` 파일로 만들어진다. 익명 클래스는 `OuterClass$1.class`, `OuterClass$2.class` 같은 숫자 접미사가 붙고, 멤버 내부 클래스는 `OuterClass$InnerClass.class` 형태가 된다. 이 파일들이 빌드 결과물에 같이 포함되지 않으면 런타임에 `NoClassDefFoundError`가 발생한다. 라이브러리를 jar로 패키징할 때 합성 클래스 누락은 가끔 만나는 이슈다.

`javap -p OuterContainer\$LeakyInner.class` 명령으로 디스어셈블해보면 `final OuterContainer this$0;` 같은 합성 필드와 외부 인스턴스를 받는 생성자가 추가된 것을 직접 확인할 수 있다.

---

## 2. sealed 클래스로 도메인 닫기

Java 17에서 정식 추가된 `sealed` 클래스는 상속 가능한 하위 클래스를 명시적으로 제한한다. 결제 상태, 주문 상태처럼 "이 도메인은 정확히 이 N개의 상태만 존재한다"고 표현해야 할 때 쓴다. 기존에는 enum으로 표현하거나 abstract 클래스에 protected 생성자를 두는 식으로 흉내 냈는데, sealed는 컴파일러가 직접 폐쇄성을 강제해준다.

```java
public sealed abstract class PaymentResult
        permits PaymentResult.Success, PaymentResult.Failed, PaymentResult.Pending {

    private final String transactionId;

    protected PaymentResult(String transactionId) {
        this.transactionId = transactionId;
    }

    public String getTransactionId() {
        return transactionId;
    }

    public static final class Success extends PaymentResult {
        private final long approvedAmount;

        public Success(String transactionId, long approvedAmount) {
            super(transactionId);
            this.approvedAmount = approvedAmount;
        }

        public long getApprovedAmount() {
            return approvedAmount;
        }
    }

    public static final class Failed extends PaymentResult {
        private final String errorCode;
        private final String reason;

        public Failed(String transactionId, String errorCode, String reason) {
            super(transactionId);
            this.errorCode = errorCode;
            this.reason = reason;
        }

        public String getErrorCode() { return errorCode; }
        public String getReason() { return reason; }
    }

    public static final class Pending extends PaymentResult {
        public Pending(String transactionId) {
            super(transactionId);
        }
    }
}
```

`permits` 절에 명시되지 않은 클래스가 `extends PaymentResult`를 시도하면 컴파일러가 막는다. 그리고 `permits`에 적힌 하위 클래스는 반드시 `final`, `sealed`, 또는 `non-sealed` 셋 중 하나로 선언해야 한다. `final`은 더 이상 상속 불가, `sealed`는 또 한 번 제한된 상속 허용, `non-sealed`는 봉인을 풀어 자유로운 상속 허용이다.

sealed의 진짜 장점은 switch 표현식과 만났을 때 드러난다. Java 21부터는 패턴 매칭 switch가 sealed 타입의 모든 하위 케이스를 다뤘는지 컴파일러가 검증해준다. 새로운 결제 상태가 추가되면 컴파일 에러가 나서 누락된 분기를 빠짐없이 잡아낸다.

```java
public String describe(PaymentResult result) {
    return switch (result) {
        case PaymentResult.Success s -> "승인됨: " + s.getApprovedAmount() + "원";
        case PaymentResult.Failed f -> "실패: " + f.getErrorCode() + " - " + f.getReason();
        case PaymentResult.Pending p -> "대기 중";
        // default 절이 없어도 컴파일러가 OK함 (sealed 덕분)
    };
}
```

실무에서 sealed를 쓸 때 주의할 점은 모듈 시스템과의 상호작용이다. sealed 클래스와 permitted 하위 클래스는 같은 모듈 또는 같은 패키지에 있어야 한다. 멀티모듈 프로젝트에서 도메인 코어에 sealed를 두고 어댑터 모듈에서 상속하려고 하면 컴파일이 실패한다. 이 제약 때문에 sealed는 외부 확장을 허용하지 않는 폐쇄적 도메인 모델에 가장 잘 맞는다.

---

## 3. record 클래스의 컴팩트 생성자와 검증 위치

record는 Java 14에서 미리보기, 16에서 정식 추가된 불변 데이터 운반체용 문법이다. equals, hashCode, toString, 접근자 메서드를 컴파일러가 자동 생성한다. DTO나 값 객체(value object)를 만들 때 코드량이 압도적으로 줄어든다.

```java
public record Money(long amount, String currency) {}
```

이 한 줄로 amount, currency 접근자, equals/hashCode, toString이 모두 만들어진다. 그런데 실제 도메인에서는 검증 로직이 필요하다. amount가 음수면 안 되고, currency는 ISO 4217 코드여야 한다. 이런 검증을 어디에 넣을지가 record를 처음 쓸 때 가장 자주 헷갈리는 부분이다.

### 컴팩트 생성자

record는 표준 생성자 시그니처를 그대로 두면서 검증/정규화 로직만 추가하는 컴팩트 생성자(compact constructor) 문법을 제공한다.

```java
public record Money(long amount, String currency) {
    public Money {
        if (amount < 0) {
            throw new IllegalArgumentException("금액은 음수일 수 없다: " + amount);
        }
        if (currency == null || currency.length() != 3) {
            throw new IllegalArgumentException("통화 코드는 3자리여야 한다: " + currency);
        }
        currency = currency.toUpperCase(); // 정규화도 가능
    }
}
```

컴팩트 생성자는 매개변수 목록과 괄호를 생략한다. 컴파일러가 마지막에 자동으로 `this.amount = amount; this.currency = currency;`를 붙여주기 때문에 검증과 정규화에만 집중하면 된다. 단, 컴팩트 생성자 안에서 `this.amount = ...` 식으로 직접 필드에 할당하려고 하면 컴파일 에러가 난다. 정규화는 매개변수 변수 자체를 재할당해야 한다.

### 정적 팩토리 메서드 패턴

생성자 외에 다른 형태로 만들고 싶다면 정적 팩토리 메서드를 추가한다. record도 일반 클래스처럼 정적 메서드를 가질 수 있다.

```java
public record Money(long amount, String currency) {
    public Money {
        if (amount < 0) throw new IllegalArgumentException();
        if (currency == null || currency.length() != 3) throw new IllegalArgumentException();
    }

    public static Money krw(long amount) {
        return new Money(amount, "KRW");
    }

    public static Money zero(String currency) {
        return new Money(0, currency);
    }
}
```

생성자는 검증만 담당하고, 자주 쓰는 조합은 정적 팩토리로 의도를 드러낸다. `Money.krw(10000)`이 `new Money(10000, "KRW")`보다 읽기 쉽다.

### 자동 생성된 equals/hashCode의 한계

record가 자동으로 만들어주는 equals는 모든 필드를 비교한다. 이게 항상 정답은 아니다. 예를 들어 식별자 기반으로만 비교해야 하는 엔티티를 record로 만들면, 다른 필드가 바뀐 두 인스턴스를 다른 것으로 판단해버린다. 그래서 record는 보통 엔티티가 아니라 값 객체나 응답 DTO에만 쓴다.

또한 record의 필드가 가변 컬렉션이나 배열이면 record 자체는 final 참조이지만 내부 상태는 변경 가능해서 진짜 불변이 아니다. 이런 경우 컴팩트 생성자에서 방어적 복사를 하고 접근자도 오버라이드해야 한다.

```java
public record OrderItems(List<String> items) {
    public OrderItems {
        items = List.copyOf(items); // 불변 리스트로 복사
    }
}
```

`List.copyOf`는 입력이 이미 불변이면 그대로 반환하므로 비용이 거의 없고, 가변 리스트가 들어오면 불변 복사본을 만든다.

마지막으로 record는 다른 클래스를 `extends`할 수 없다. 항상 `java.lang.Record`를 암묵적으로 상속하기 때문이다. 인터페이스 구현은 가능하므로 sealed 인터페이스의 케이스로 record를 쓰는 패턴이 자주 나온다.

```java
public sealed interface ApiResponse permits ApiResponse.Ok, ApiResponse.Error {
    record Ok(Object data) implements ApiResponse {}
    record Error(int code, String message) implements ApiResponse {}
}
```

---

## 4. 익명 클래스 vs 람다의 바이트코드 차이

Java 8 이전에는 함수형 인터페이스 인스턴스를 만들 때 익명 클래스를 썼다. 8부터는 람다 표현식이 추가됐는데, 이 둘은 문법만 다른 게 아니라 바이트코드 레벨에서도 다르게 컴파일된다.

### this 바인딩

익명 클래스 안에서 `this`는 익명 클래스 자기 자신을 가리킨다. 외부 클래스의 this는 `OuterClass.this`로 명시해야 한다. 람다 안에서 `this`는 그 람다를 둘러싼 외부 클래스 인스턴스를 직접 가리킨다. 람다는 별도의 클래스 인스턴스가 아니라 외부 메서드의 일부처럼 동작하기 때문이다.

```java
public class ThisBindingExample {
    private String name = "outer";

    public void anonymous() {
        Runnable r = new Runnable() {
            private String name = "anonymous";

            @Override
            public void run() {
                System.out.println(this.name);              // "anonymous"
                System.out.println(ThisBindingExample.this.name); // "outer"
            }
        };
        r.run();
    }

    public void lambda() {
        Runnable r = () -> {
            System.out.println(this.name); // "outer" — 람다에는 자체 this가 없음
        };
        r.run();
    }
}
```

이 차이가 실무에서 가장 자주 나오는 케이스는 Swing/안드로이드 콜백이나 이벤트 리스너에서 self-reference가 필요할 때다. 익명 클래스는 자기 자신을 콜백에 등록할 수 있지만, 람다는 외부의 this만 보이므로 같은 패턴을 못 쓴다.

### 메모리 점유와 클래스 파일

익명 클래스는 컴파일 시 별도의 `.class` 파일이 만들어지고, 매번 호출할 때마다 `new` 연산으로 새 인스턴스가 할당된다. 람다는 `invokedynamic` 명령어와 `LambdaMetafactory`를 통해 런타임에 클래스가 동적으로 생성된다. 캡처하는 변수가 없는 람다(`() -> System.out.println("hi")` 같은)는 보통 싱글톤처럼 재사용되어 매번 새 인스턴스를 만들지 않는다.

이게 의미하는 건, 캡처 없는 람다는 익명 클래스보다 메모리 효율이 훨씬 좋다는 점이다. 반복적으로 같은 람다를 쓰는 코드(`stream().map(x -> x.getId())` 같은)에서 람다는 한 번만 만들어진다.

다만 캡처가 있는 람다는 캡처할 때마다 새 인스턴스를 만들 수 있다. 그래서 핫패스에서 무거운 캡처가 있는 람다를 반복 호출하면 GC 압력이 증가한다. JIT가 어느 정도 최적화해주지만 억 단위 호출 루프에서는 측정해보고 결정해야 한다.

### 직렬화

익명 클래스는 외부 클래스 인스턴스 참조를 들고 있기 때문에, 익명 클래스를 직렬화하려면 외부 인스턴스도 직렬화 가능해야 한다. 안 그러면 `NotSerializableException`이 터진다. 이 함정은 뒤의 트러블슈팅 섹션에서 자세히 다룬다.

람다를 직렬화하려면 함수형 인터페이스가 `Serializable`을 상속해야 한다(`Function & Serializable`). 람다는 합성 메서드로 컴파일되기 때문에 외부 클래스 직렬화 가능 여부와는 별개로 캡처된 변수만 직렬화 가능하면 된다. 다만 람다 직렬화는 JVM 구현에 따라 호환성 이슈가 있어서 RMI 같은 특수한 경우가 아니면 권장되지 않는다.

---

## 5. 정적 중첩 클래스로 Builder 구현하기

Builder 패턴은 생성자 매개변수가 많거나 선택적 필드가 있는 객체를 만들 때 자주 쓴다. Java에서 Builder는 보통 정적 중첩 클래스로 구현한다. 멤버 내부 클래스로 만들면 외부 인스턴스 참조 누수 문제가 생기기 때문이다.

```java
public final class HttpRequest {
    private final String url;
    private final String method;
    private final Map<String, String> headers;
    private final byte[] body;
    private final int timeoutMs;

    private HttpRequest(Builder b) {
        this.url = b.url;
        this.method = b.method;
        this.headers = Map.copyOf(b.headers);
        this.body = b.body;
        this.timeoutMs = b.timeoutMs;
    }

    public static Builder builder(String url) {
        return new Builder(url);
    }

    public static final class Builder {
        private final String url;
        private String method = "GET";
        private final Map<String, String> headers = new HashMap<>();
        private byte[] body;
        private int timeoutMs = 5000;

        private Builder(String url) {
            this.url = url;
        }

        public Builder method(String method) {
            this.method = method;
            return this;
        }

        public Builder header(String name, String value) {
            this.headers.put(name, value);
            return this;
        }

        public Builder body(byte[] body) {
            this.body = body;
            return this;
        }

        public Builder timeout(int timeoutMs) {
            this.timeoutMs = timeoutMs;
            return this;
        }

        public HttpRequest build() {
            if (url == null) throw new IllegalStateException("url is required");
            return new HttpRequest(this);
        }
    }
}
```

여기서 핵심은 `Builder`가 `static`이라는 점이다. 외부 클래스 `HttpRequest` 인스턴스 없이도 만들 수 있어야 한다. 만약 `static`이 빠지면 `new HttpRequest.Builder(url)` 같은 호출이 불가능해지고, 빌더 객체가 외부 인스턴스 참조를 들게 된다.

또 Builder를 정적 팩토리 메서드 `builder()`를 통해서만 만들 수 있도록 생성자를 `private`으로 둔 것도 의도가 있다. 사용자가 `new HttpRequest.Builder()`로 직접 만드는 경로를 닫아두면, 추후 빌더 생성 로직이 바뀌어도 호환성을 유지하기 쉽다.

Lombok의 `@Builder`는 이 패턴을 자동 생성해주지만 어노테이션 처리 단계에서 코드를 만들기 때문에 디버깅이 어렵고, IDE 분석 도구와 충돌하기도 한다. 빌더가 단순하지 않거나 검증 로직이 들어간다면 직접 작성하는 게 결과적으로 더 명확하다.

---

## 6. 추상 클래스의 메서드와 인터페이스 default 메서드 충돌

Java 8에서 인터페이스에 default 메서드가 추가되면서, 한 클래스가 인터페이스의 default 메서드와 추상 클래스(또는 부모 클래스)의 같은 시그니처 메서드를 동시에 상속하는 상황이 생겼다. 이때 어느 쪽이 호출되는지에 대한 규칙이 명확히 정의되어 있다.

### 규칙 1: 클래스가 인터페이스를 이긴다

같은 이름과 시그니처를 가진 메서드가 부모 클래스(추상 클래스 포함)와 인터페이스에 동시에 있으면, 부모 클래스 쪽이 우선한다. 인터페이스의 default 메서드는 무시된다.

```java
interface Greeter {
    default String hello() {
        return "hello from interface";
    }
}

abstract class AbstractGreeter {
    public String hello() {
        return "hello from abstract class";
    }
}

class MyGreeter extends AbstractGreeter implements Greeter {
    // hello()를 오버라이드하지 않아도 컴파일 OK
    // new MyGreeter().hello() → "hello from abstract class"
}
```

### 규칙 2: 더 구체적인 인터페이스가 이긴다

부모 클래스에 같은 메서드가 없고, 두 인터페이스 모두 default 메서드를 가지고 있으면, 더 하위(구체적)인 인터페이스의 것이 이긴다. 두 인터페이스가 형제 관계라 우열을 가릴 수 없으면 컴파일 에러가 발생한다.

```java
interface A {
    default String greet() { return "A"; }
}

interface B {
    default String greet() { return "B"; }
}

// A와 B 사이에 상속 관계가 없으므로 컴파일 에러
class AB implements A, B {
    // 반드시 직접 오버라이드해야 함
    @Override
    public String greet() {
        return A.super.greet(); // 명시적으로 어느 쪽을 부를지 선택
    }
}
```

`InterfaceName.super.methodName()` 문법으로 어느 쪽 default 메서드를 호출할지 명시할 수 있다. 두 default 메서드의 동작을 합치고 싶을 때도 이 문법을 쓴다.

### 추상 클래스에 default 메서드가 닿을 때 주의

실무에서 자주 보는 사례는 이렇다. 기존에 추상 클래스 `BaseService`가 있고, 새로 도입한 인터페이스 `Auditable`이 default `audit()` 메서드를 가진다. `BaseService`도 우연히 `audit()`을 구현하고 있다면, 자식 클래스에서 `Auditable`을 implements해도 인터페이스의 default가 적용되지 않는다. 부모 클래스의 메서드가 이긴다는 규칙 때문이다.

이 동작을 모르고 default 메서드만 보고 "audit 동작이 이렇겠지"라고 가정하면 디버깅이 매우 까다로워진다. 추상 클래스를 가진 계층에 인터페이스를 끼워넣을 때는 메서드 충돌이 없는지 일일이 확인해야 한다.

---

## 7. 익명 클래스의 직렬화와 메모리 누수 트러블슈팅

이 섹션은 실무에서 직접 만난 익명 클래스 관련 문제들을 정리한 것이다. 책에서는 잘 다루지 않지만 운영 환경에서는 흔히 마주치는 함정들이다.

### 사례 1: 익명 클래스 직렬화 시 NotSerializableException

오래된 캐시 라이브러리에서 직렬화 가능한 콜백을 등록받는 API가 있었다. 누군가 익명 클래스로 콜백을 만들어 등록했더니 운영 중에 캐시가 디스크로 swap되는 시점에 `NotSerializableException`이 터졌다.

```java
public class ProductService {
    private byte[] largeBuffer = new byte[1024];

    public void registerCallback(CallbackRegistry registry) {
        registry.register(new SerializableCallback() {
            @Override
            public void onEvent(Event e) {
                System.out.println("handled: " + e);
            }
        });
    }
}
```

여기서 익명 클래스는 `SerializableCallback` 인터페이스를 구현하지만, 컴파일러가 합성 필드 `this$0`로 외부 `ProductService` 인스턴스를 참조한다. 직렬화하려면 외부 인스턴스도 직렬화 가능해야 하는데, `ProductService`가 `Serializable`을 구현하지 않거나, 구현했더라도 직렬화 불가능한 필드(예: `Logger`, `EntityManager`)를 가지면 그대로 터진다.

해결책은 두 가지다. 외부 인스턴스 참조가 필요 없다면 정적 중첩 클래스로 빼서 외부 참조를 끊는다. 외부 상태가 정말 필요하다면 그 값만 명시적으로 final 변수로 캡처해서 외부 참조를 우회한다.

```java
public void registerCallback(CallbackRegistry registry) {
    final String prefix = this.prefix; // 필요한 값만 로컬 final로 추출
    registry.register(new StaticCallback(prefix));
}

private static class StaticCallback implements SerializableCallback {
    private final String prefix;
    StaticCallback(String prefix) { this.prefix = prefix; }
    @Override
    public void onEvent(Event e) { System.out.println(prefix + ": " + e); }
}
```

### 사례 2: 익명 리스너로 인한 메모리 누수

이벤트 버스나 옵저버 패턴에서 익명 클래스로 리스너를 등록하고 해제를 잊으면 메모리 누수가 누적된다. 익명 리스너는 외부 인스턴스를 참조하므로, 이벤트 버스가 살아있는 동안 외부 인스턴스 전체가 GC되지 않는다.

```java
public class OrderViewController {
    private LargeOrderModel model;

    public OrderViewController(EventBus bus) {
        bus.subscribe(OrderEvent.class, new EventListener<OrderEvent>() {
            @Override
            public void onEvent(OrderEvent e) {
                model.update(e); // OrderViewController.this.model 참조
            }
        });
    }
}
```

`OrderViewController`의 라이프사이클이 끝나도 `EventBus`가 살아있으면 익명 리스너 → `OrderViewController` → `LargeOrderModel`까지 줄줄이 살아남는다. 힙 덤프를 떠보면 GC root에서 `EventBus.subscribers` 컬렉션을 통해 컨트롤러가 retain되어 있는 것을 확인하게 된다.

해결책은 명시적인 unsubscribe다. 컨트롤러가 dispose될 때 자신이 등록한 리스너를 해제해야 한다. 이를 강제하려면 EventBus가 `WeakReference`로 리스너를 보관하거나, subscribe 결과로 `Subscription` 핸들을 반환해서 close 가능한 자원으로 다루는 식으로 API를 설계한다.

### 사례 3: ThreadLocal에 익명 클래스 저장

ThreadLocal에 익명 Initializer나 Cleaner를 익명 클래스로 넣으면, 스레드 풀 환경에서 외부 인스턴스가 스레드 수명만큼 살아남는다. 톰캣 같은 컨테이너에서 webapp이 reload되어도 스레드 풀의 ThreadLocal에 남은 외부 참조 때문에 클래스로더 누수가 발생한다. 이 시나리오는 OOM과 함께 `[webapp] appears to have started a thread named ...` 로그가 동반된다.

ThreadLocal 초기화는 가능하면 `ThreadLocal.withInitial(SomeClass::create)` 형태의 메서드 참조로 하고, 정적 컨텍스트에서 동작하도록 설계해야 한다. 람다 중에서도 캡처 없는 람다는 합성 정적 메서드로 컴파일되어 외부 참조를 갖지 않는다.

---

## 마무리

여기까지 다룬 내용은 Java 클래스의 고급 기능 중에서도 컴파일러 동작과 메모리 관리에 직접 영향을 미치는 부분들이다. 정리하면 이렇게 요약할 수 있다.

중첩 클래스는 외부 참조 필요 여부에 따라 static 여부가 결정된다. 익명 클래스와 람다는 문법적 대체재가 아니라 this 바인딩과 메모리 점유가 다른 별개의 도구다. sealed와 record는 도메인 모델링 코드를 압축하면서 컴파일러의 도움을 받게 해주는 최신 문법이고, 인터페이스 default 메서드는 추상 클래스와 충돌할 때 부모 클래스가 이긴다는 규칙을 외워두면 디버깅이 빨라진다.

이 기능들은 알고 쓰면 코드가 짧아지고 안전해지지만, 모르고 쓰면 메모리 누수와 직렬화 예외의 진원지가 된다. 특히 익명 클래스의 외부 인스턴스 캡처는 신입부터 시니어까지 가장 자주 만나는 함정이므로, 익명 클래스 자리에는 람다나 정적 중첩 클래스를 쓸 수 있는지 먼저 검토하는 습관을 들이는 게 좋다.
