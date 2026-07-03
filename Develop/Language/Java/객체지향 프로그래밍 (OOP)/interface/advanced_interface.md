---
title: "Java 고급 인터페이스 (Advanced Interface)"
tags: [Java, Interface, Default Method, Static Method, Private Method, Sealed Interface]
updated: 2026-04-08
---

# Java 고급 인터페이스 (Advanced Interface)

Java 8 이전의 인터페이스는 추상 메서드와 상수만 가질 수 있었다. Java 8부터 default, static 메서드가 추가되고, Java 9에서 private 메서드, Java 17에서 sealed interface가 도입되면서 인터페이스의 역할이 크게 바뀌었다.

이 문서는 Java 8 ~ 17에서 추가된 인터페이스 기능을 다룬다. 기본적인 인터페이스 정의나 구현은 [Interface](Interface.md) 문서를 참고한다.

---

## 1. Default 메서드 (Java 8+)

### 1.1 왜 생겼나

Java 8에서 `Collection` 인터페이스에 `stream()` 메서드를 추가해야 했다. 문제는 `Collection`을 구현한 서드파티 클래스가 수천 개 존재한다는 것이다. 인터페이스에 메서드를 추가하면 모든 구현체가 컴파일 에러를 내게 된다.

이 하위 호환성 문제를 해결하기 위해 default 메서드가 도입됐다. 인터페이스에 구현부가 있는 메서드를 정의할 수 있고, 구현 클래스는 이 메서드를 오버라이드하지 않아도 된다.

```java
public interface Collection<E> extends Iterable<E> {
    // 기존 추상 메서드들...

    // Java 8에서 추가된 default 메서드
    default Stream<E> stream() {
        return StreamSupport.stream(spliterator(), false);
    }
}
```

기존 구현체들은 코드 변경 없이 `stream()`을 사용할 수 있게 됐다.

### 1.2 기본 사용법

```java
interface Loggable {
    String getName();

    default void log(String message) {
        System.out.println("[" + getName() + "] " + message);
    }
}

class OrderService implements Loggable {
    @Override
    public String getName() {
        return "OrderService";
    }

    public void createOrder() {
        log("주문 생성 시작");  // default 메서드 호출
        // 주문 로직...
        log("주문 생성 완료");
    }
}
```

구현 클래스에서 `log()`를 오버라이드하지 않았지만 그대로 사용할 수 있다. 필요하면 오버라이드해서 동작을 바꾸면 된다.

### 1.3 다이아몬드 문제 (Diamond Problem)

두 인터페이스가 같은 시그니처의 default 메서드를 가지고 있으면, 이를 동시에 구현하는 클래스에서 컴파일 에러가 발생한다.

```java
interface Flyable {
    default void move() {
        System.out.println("날아서 이동");
    }
}

interface Swimmable {
    default void move() {
        System.out.println("헤엄쳐서 이동");
    }
}

// 컴파일 에러: class Duck inherits unrelated defaults for move()
class Duck implements Flyable, Swimmable {
}
```

해결 방법은 구현 클래스에서 직접 오버라이드하는 것이다.

```java
class Duck implements Flyable, Swimmable {
    @Override
    public void move() {
        // 방법 1: 특정 인터페이스의 default 메서드 선택
        Flyable.super.move();

        // 방법 2: 완전히 새로운 구현
        // System.out.println("오리는 걸어서 이동");
    }
}
```

**클래스 vs 인터페이스 우선순위**: 상위 클래스에 같은 시그니처의 메서드가 있으면 인터페이스의 default 메서드보다 클래스의 메서드가 우선한다. 이것을 "클래스 우선 규칙(Class wins rule)"이라고 한다.

```java
class Animal {
    public void move() {
        System.out.println("동물이 이동");
    }
}

interface Flyable {
    default void move() {
        System.out.println("날아서 이동");
    }
}

class Bird extends Animal implements Flyable {
    // move()를 오버라이드하지 않으면 Animal.move()가 호출된다.
    // Flyable.move()는 무시된다.
}
```

이 규칙 때문에 기존 클래스 계층에 인터페이스를 추가해도 동작이 바뀌지 않는다. 의도한 설계다.

**인터페이스 상속 시 충돌**: 인터페이스끼리도 상속 관계가 있으면 더 구체적인(하위) 인터페이스의 default 메서드가 우선한다.

```java
interface A {
    default void hello() { System.out.println("A"); }
}

interface B extends A {
    default void hello() { System.out.println("B"); }
}

class MyClass implements A, B {
    // B가 A의 하위 인터페이스이므로 B.hello()가 호출된다.
    // 컴파일 에러 아님.
}
```

### 1.4 default 메서드 사용 시 주의점

default 메서드는 인터페이스에 상태(필드)가 없기 때문에 제약이 있다. 인스턴스 변수에 접근할 수 없고, 오직 다른 인터페이스 메서드 호출이나 파라미터만 사용할 수 있다.

```java
interface Cacheable {
    // 인터페이스에는 인스턴스 변수를 선언할 수 없다.
    // private Map<String, Object> cache = new HashMap<>();  // 컴파일 에러

    default String getCacheKey() {
        // this를 사용할 수 있지만, 인터페이스 메서드만 호출 가능
        return this.getClass().getSimpleName() + "_" + this.hashCode();
    }
}
```

default 메서드를 너무 많이 넣으면 인터페이스가 사실상 추상 클래스처럼 되어버린다. 인터페이스의 본래 목적인 "계약 정의"에서 벗어나게 되니, 공통 로직이 많다면 추상 클래스 사용을 고려한다.

---

## 2. Static 메서드 (Java 8+)

### 2.1 개념

인터페이스에 static 메서드를 정의할 수 있다. 인터페이스와 관련된 유틸리티 메서드를 별도 클래스(`Collections`, `Paths` 등) 없이 인터페이스 자체에 둘 수 있게 된 것이다.

```java
interface Validator<T> {
    boolean validate(T value);

    static <T> Validator<T> not(Validator<T> validator) {
        return value -> !validator.validate(value);
    }

    static Validator<String> nonEmpty() {
        return value -> value != null && !value.isEmpty();
    }

    static Validator<Integer> range(int min, int max) {
        return value -> value >= min && value <= max;
    }
}
```

```java
Validator<String> nameValidator = Validator.nonEmpty();
Validator<Integer> ageValidator = Validator.range(1, 150);
Validator<String> emptyValidator = Validator.not(Validator.nonEmpty());

System.out.println(nameValidator.validate("홍길동"));  // true
System.out.println(ageValidator.validate(200));         // false
System.out.println(emptyValidator.validate(""));        // true
```

### 2.2 static 메서드의 제약사항

인터페이스의 static 메서드는 클래스의 static 메서드와 다른 점이 몇 가지 있다.

**상속되지 않는다.** 구현 클래스나 하위 인터페이스에서 인터페이스의 static 메서드를 직접 호출할 수 없다.

```java
interface Parent {
    static void hello() {
        System.out.println("Parent hello");
    }
}

interface Child extends Parent {
    // Parent.hello()가 상속되지 않는다.
}

class MyClass implements Parent {
}

// 호출 방법
Parent.hello();      // OK - 인터페이스 이름으로 직접 호출
// Child.hello();    // 컴파일 에러 - 상속되지 않음
// MyClass.hello();  // 컴파일 에러 - 구현 클래스로 호출 불가
```

클래스의 static 메서드는 하위 클래스를 통해 호출할 수 있지만, 인터페이스의 static 메서드는 반드시 해당 인터페이스 이름으로만 호출해야 한다. 이렇게 설계한 이유는 다중 구현에서 어떤 인터페이스의 static 메서드를 호출하는지 모호해지는 것을 방지하기 위해서다.

**오버라이드할 수 없다.** static이니 당연하지만, 하위 인터페이스에서 같은 시그니처의 static 메서드를 선언하면 이것은 오버라이드가 아니라 별개의 메서드다.

```java
interface Base {
    static void info() { System.out.println("Base"); }
}

interface Sub extends Base {
    static void info() { System.out.println("Sub"); }  // Base.info()와 별개
}

Base.info();  // "Base"
Sub.info();   // "Sub"
```

---

## 3. Private 메서드 (Java 9+)

### 3.1 도입 배경

Java 8에서 default 메서드가 도입되면서 인터페이스 내부에 구현 코드가 들어가기 시작했다. 여러 default 메서드에서 공통 로직이 있을 때, 이를 분리할 방법이 없었다. public default 메서드로 만들면 외부에 노출되고, 구현 클래스에서 오버라이드할 수도 있다.

Java 9에서 private 메서드를 도입해서 인터페이스 내부에서만 사용하는 헬퍼 메서드를 만들 수 있게 됐다.

### 3.2 실제 활용 패턴

```java
interface HttpClient {
    // 공개 API
    default String get(String url) {
        return sendRequest("GET", url, null);
    }

    default String post(String url, String body) {
        return sendRequest("POST", url, body);
    }

    default String put(String url, String body) {
        return sendRequest("PUT", url, body);
    }

    // 내부 공통 로직 - 외부에 노출되지 않음
    private String sendRequest(String method, String url, String body) {
        validateUrl(url);
        String requestLog = formatLog(method, url);
        System.out.println(requestLog);
        // 실제 HTTP 요청 처리...
        return "response";
    }

    private void validateUrl(String url) {
        if (url == null || !url.startsWith("http")) {
            throw new IllegalArgumentException("잘못된 URL: " + url);
        }
    }

    private String formatLog(String method, String url) {
        return "[" + java.time.LocalDateTime.now() + "] " + method + " " + url;
    }
}
```

`sendRequest`, `validateUrl`, `formatLog`는 외부에서 호출할 수 없다. default 메서드의 내부 구현을 깔끔하게 분리하면서 인터페이스의 공개 API를 오염시키지 않는다.

### 3.3 private static 메서드

private 메서드에도 static을 붙일 수 있다. static 메서드에서 호출하려면 private static이어야 한다.

```java
interface Parser {
    // public static
    static int parsePort(String input) {
        validate(input);
        return Integer.parseInt(input.trim());
    }

    // default에서도 호출 가능
    default String parseHost(String url) {
        validate(url);
        // 파싱 로직...
        return url;
    }

    // private static - static 메서드와 default 메서드 모두에서 호출 가능
    private static void validate(String input) {
        if (input == null || input.isBlank()) {
            throw new IllegalArgumentException("입력값이 비어있음");
        }
    }
}
```

| 메서드 종류 | 호출 가능 위치 |
|---|---|
| `private` (non-static) | 같은 인터페이스의 default 메서드, 다른 private 메서드 |
| `private static` | 같은 인터페이스의 모든 메서드 (static, default, private) |

---

## 4. Sealed Interface (Java 17+)

### 4.1 개념

sealed 인터페이스는 이 인터페이스를 구현할 수 있는 클래스/인터페이스를 제한한다. `permits` 절에 명시된 타입만 구현할 수 있다.

```java
public sealed interface Shape permits Circle, Rectangle, Triangle {
    double area();
}

// permits에 명시된 클래스만 구현 가능
public final class Circle implements Shape {
    private final double radius;

    public Circle(double radius) { this.radius = radius; }

    @Override
    public double area() { return Math.PI * radius * radius; }
}

public final class Rectangle implements Shape {
    private final double width, height;

    public Rectangle(double width, double height) {
        this.width = width;
        this.height = height;
    }

    @Override
    public double area() { return width * height; }
}

public non-sealed class Triangle implements Shape {
    // non-sealed: Triangle을 상속하는 클래스에는 제한이 없다
    private final double base, height;

    public Triangle(double base, double height) {
        this.base = base;
        this.height = height;
    }

    @Override
    public double area() { return 0.5 * base * height; }
}
```

### 4.2 permits에 올 수 있는 타입의 조건

permits에 명시된 타입은 반드시 다음 중 하나의 modifier를 가져야 한다:

- `final` — 더 이상 상속 불가
- `sealed` — 다시 permits로 제한
- `non-sealed` — 제한 해제, 누구나 상속 가능

```java
sealed interface Payment permits CreditCard, BankTransfer, CryptoPayment {
    void process();
}

// final: 하위 타입 없음
final class CreditCard implements Payment {
    public void process() { /* ... */ }
}

// sealed: 하위 타입을 다시 제한
sealed class BankTransfer implements Payment permits DomesticTransfer, InternationalTransfer {
    public void process() { /* ... */ }
}

final class DomesticTransfer extends BankTransfer { }
final class InternationalTransfer extends BankTransfer { }

// non-sealed: 제한 풀림
non-sealed class CryptoPayment implements Payment {
    public void process() { /* ... */ }
}

// CryptoPayment은 non-sealed이므로 자유롭게 상속 가능
class BitcoinPayment extends CryptoPayment { }
```

### 4.3 패턴 매칭과 함께 사용

sealed interface의 진짜 가치는 패턴 매칭(Java 21 switch)과 결합할 때 드러난다. 컴파일러가 모든 구현 타입을 알고 있으므로 switch에서 모든 케이스를 다뤘는지 검증할 수 있다.

```java
sealed interface Result<T> permits Success, Failure {
    // 빈 인터페이스 - 타입 자체가 의미를 가짐
}

record Success<T>(T value) implements Result<T> { }
record Failure<T>(String error) implements Result<T> { }
```

```java
public String handleResult(Result<String> result) {
    return switch (result) {
        case Success<String> s -> "성공: " + s.value();
        case Failure<String> f -> "실패: " + f.error();
        // default가 필요 없다 - 컴파일러가 모든 경우를 다뤘음을 확인
    };
}
```

새로운 구현 타입을 추가하면 (예: `Pending`을 permits에 추가), 이 switch문은 컴파일 에러가 난다. 처리되지 않은 케이스가 있다는 뜻이다. 런타임에 `ClassCastException`이나 잘못된 분기를 타는 것보다 컴파일 타임에 잡아주는 게 낫다.

### 4.4 sealed interface 제약사항

- permits에 명시된 클래스는 sealed 인터페이스와 **같은 모듈** (모듈을 사용하지 않으면 같은 패키지)에 있어야 한다.
- 같은 파일에 선언된 경우 permits를 생략할 수 있다. 컴파일러가 자동으로 추론한다.

```java
// Shape.java 파일 하나에 모두 선언하면 permits 생략 가능
sealed interface Shape {
    double area();
}

record Circle(double radius) implements Shape {
    public double area() { return Math.PI * radius * radius; }
}

record Square(double side) implements Shape {
    public double area() { return side * side; }
}
```

---

## 5. 버전별 인터페이스 기능 정리

```
Java 8  이전:  추상 메서드 + 상수(public static final)만 가능
Java 8:       + default 메서드, static 메서드
Java 9:       + private 메서드, private static 메서드
Java 14:      + record가 인터페이스 구현 가능
Java 17:      + sealed interface
Java 21:      + 패턴 매칭 switch에서 sealed 타입 완전 지원
```

---

## 6. 실무에서 겪는 문제들

### default 메서드와 Spring AOP

Spring의 AOP(프록시 기반)는 인터페이스의 default 메서드에 대해 동작이 다를 수 있다. JDK 동적 프록시를 사용하는 경우, default 메서드에 걸어둔 `@Transactional` 같은 어노테이션이 동작하지 않는 경우가 있다.

```java
interface UserService {
    void save(User user);

    // 이 @Transactional이 프록시에서 무시될 수 있다
    @Transactional
    default void saveAll(List<User> users) {
        users.forEach(this::save);
    }
}
```

이런 경우 default 메서드 대신 구현 클래스에 메서드를 옮기거나, Spring의 CGLIB 프록시를 사용하도록 설정을 변경해야 한다.

### 직렬화 문제

인터페이스의 default 메서드가 반환하는 값을 Jackson 등으로 직렬화할 때, getter 규칙에 맞는 default 메서드가 있으면 의도치 않게 JSON 필드로 포함될 수 있다.

```java
interface Identifiable {
    String getId();

    // Jackson이 이것을 JSON 필드 "displayName"으로 인식한다
    default String getDisplayName() {
        return "ID-" + getId();
    }
}
```

`@JsonIgnore`를 붙이거나, DTO로 변환해서 직렬화하는 방식으로 해결한다.

### sealed interface와 리플렉션

sealed interface의 구현 타입 제한은 컴파일 타임에만 적용된다. 리플렉션으로는 제한을 우회할 수 있다. 런타임에 sealed 타입의 구현체 목록을 가져오려면 `Class.getPermittedSubclasses()`를 사용한다.

```java
Class<?>[] permitted = Shape.class.getPermittedSubclasses();
for (Class<?> c : permitted) {
    System.out.println(c.getName());
}
```
