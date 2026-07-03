---
title: Override Overriding
tags: [language, java, 객체지향-프로그래밍-oop, override과-overriding]
updated: 2026-04-09
---

# 오버라이드(Override)와 오버라이딩(Overriding)

## 1. Override와 Overriding 구분

Java에서 두 용어는 자주 혼용되지만, 가리키는 대상이 다르다.

- **Override**: 재정의된 메서드 자체. 결과물을 지칭한다.
- **Overriding**: 부모 클래스의 메서드를 자식 클래스에서 재정의하는 행위.

```java
class Animal {
    public void makeSound() {
        System.out.println("동물이 소리를 냅니다.");
    }
}

class Dog extends Animal {
    @Override  // 이 행위가 Overriding
    public void makeSound() {  // 이 메서드가 Override된 메서드
        System.out.println("멍멍!");
    }
}
```

실무에서는 구분 없이 "오버라이딩한다"로 통용된다. 중요한 건 용어가 아니라 동작 원리다.

---

## 2. 오버라이딩 규칙

오버라이딩은 아무 메서드나 되는 게 아니다. 컴파일러가 검증하는 규칙이 있고, 이걸 모르면 컴파일 에러를 만난다.

### 메서드 시그니처 일치

메서드 이름, 매개변수 타입과 개수가 부모와 정확히 같아야 한다. 하나라도 다르면 오버라이딩이 아니라 새로운 메서드 정의가 된다.

```java
class Parent {
    public void process(String data) { }
}

class Child extends Parent {
    // 컴파일 에러 없지만, 오버라이딩이 아니라 오버로딩이다
    public void process(String data, int retry) { }

    // 이것이 오버라이딩
    @Override
    public void process(String data) { }
}
```

### 접근 제어자 규칙

자식 메서드의 접근 범위는 부모보다 **같거나 넓어야** 한다. 좁히면 컴파일 에러가 발생한다.

```
부모가 public    → 자식도 public만 가능
부모가 protected → 자식은 protected 또는 public
부모가 default   → 자식은 default, protected, public
```

```java
class Parent {
    protected void doWork() { }
}

class Child extends Parent {
    // 컴파일 에러: Cannot reduce the visibility of the inherited method
    // private void doWork() { }

    // 가능: protected → public으로 넓힘
    @Override
    public void doWork() { }
}
```

왜 이런 제약이 있는가? 부모 타입으로 참조할 때 호출 가능했던 메서드가 자식에서 갑자기 접근 불가가 되면 다형성이 깨진다.

### 예외 제약 (throws)

오버라이딩할 때 checked exception은 부모가 선언한 것과 **같거나 더 구체적인 하위 타입**만 던질 수 있다. 부모가 선언하지 않은 새로운 checked exception을 추가하면 컴파일 에러다.

```java
class Parent {
    public void read() throws IOException { }
}

class Child extends Parent {
    // 가능: IOException의 하위 타입
    @Override
    public void read() throws FileNotFoundException { }

    // 가능: 예외를 안 던지는 것도 허용
    // @Override
    // public void read() { }

    // 컴파일 에러: Exception은 IOException보다 상위 타입
    // @Override
    // public void read() throws Exception { }
}
```

unchecked exception(RuntimeException 계열)은 이 제약과 무관하다. 자유롭게 추가할 수 있다.

### 오버라이딩 불가능한 메서드

세 가지 키워드가 붙은 메서드는 오버라이딩할 수 없다.

```java
class Parent {
    // 1. final 메서드: 재정의 금지가 목적
    public final void validate() { }

    // 2. static 메서드: 인스턴스가 아닌 클래스에 바인딩됨
    public static void utility() { }

    // 3. private 메서드: 자식이 볼 수 없으므로 오버라이딩 자체가 성립하지 않음
    private void internal() { }
}

class Child extends Parent {
    // 컴파일 에러: Cannot override the final method from Parent
    // @Override public void validate() { }

    // 컴파일 에러: This instance method cannot override the static method from Parent
    // @Override public void utility() { }

    // 이건 오버라이딩이 아니라 Child만의 새 메서드
    private void internal() { }
}
```

static 메서드에서 주의할 점: 자식 클래스에서 같은 시그니처의 static 메서드를 선언하면 **메서드 하이딩(method hiding)**이 발생한다. 오버라이딩과 비슷해 보이지만 동적 바인딩이 적용되지 않는다.

```java
class Parent {
    public static void greet() {
        System.out.println("Parent");
    }
}

class Child extends Parent {
    public static void greet() {  // 하이딩: @Override 붙이면 에러남
        System.out.println("Child");
    }
}

Parent ref = new Child();
ref.greet();  // "Parent" 출력 — 참조 타입 기준으로 호출됨
```

---

## 3. `@Override` 어노테이션

컴파일러에게 "이 메서드는 부모 메서드를 재정의한 것"이라고 알려주는 어노테이션이다. 실수로 메서드 이름을 잘못 쓰거나 매개변수 타입을 틀리면 컴파일 에러로 잡아준다.

```java
class Parent {
    public void showMessage() {
        System.out.println("부모 메시지");
    }
}

class Child extends Parent {
    // @Override 없으면: 새 메서드로 인식되어 버그가 런타임까지 숨는다
    public void showMessages() {  // 오타: showMessage → showMessages
        System.out.println("자식 메시지");
    }
}
```

`@Override`를 붙이면 `showMessages()`가 부모에 없다는 걸 컴파일 시점에 알려준다. 모든 오버라이딩 메서드에 `@Override`를 붙이는 것이 기본이다.

---

## 4. super 키워드 활용

오버라이딩한 메서드에서 부모의 원본 로직을 호출해야 할 때 `super`를 쓴다. 부모 로직을 완전히 대체하는 게 아니라 확장하고 싶을 때 유용하다.

```java
class BaseRepository {
    public void save(Entity entity) {
        // 공통 저장 로직: 유효성 검증, 감사 로그 기록
        validate(entity);
        auditLog(entity);
        entityManager.persist(entity);
    }
}

class UserRepository extends BaseRepository {
    @Override
    public void save(Entity entity) {
        // 부모의 공통 로직 먼저 실행
        super.save(entity);

        // User 전용 후처리
        if (entity instanceof User user) {
            cacheManager.evict("user:" + user.getId());
            eventPublisher.publish(new UserSavedEvent(user));
        }
    }
}
```

`super.save()`를 빠뜨리면 유효성 검증과 감사 로그가 누락된다. 부모 로직에 의존하는 경우 super 호출을 잊는 게 흔한 버그 원인이다.

super 호출 위치도 중요하다. 전처리가 필요하면 super 호출 전에, 후처리가 필요하면 super 호출 후에 코드를 배치한다.

```java
class FilterChain extends BaseFilter {
    @Override
    public void doFilter(Request req) {
        // 전처리: 요청 변환
        req.addHeader("X-Trace-Id", generateTraceId());

        super.doFilter(req);  // 부모 필터 로직

        // 후처리: 응답 로깅
        log.info("Filter completed for {}", req.getPath());
    }
}
```

---

## 5. 공변 반환 타입 (Covariant Return Type)

Java 5부터 오버라이딩할 때 반환 타입을 부모의 반환 타입의 하위 타입으로 변경할 수 있다. 이걸 공변 반환 타입이라고 한다.

```java
class AnimalFactory {
    public Animal create() {
        return new Animal();
    }
}

class DogFactory extends AnimalFactory {
    @Override
    public Dog create() {  // Animal → Dog로 반환 타입 변경 (Dog은 Animal의 하위 타입)
        return new Dog();
    }
}
```

공변 반환 타입이 없으면 팩토리 패턴에서 매번 캐스팅이 필요하다.

```java
// 공변 반환 타입 없을 때
Animal animal = dogFactory.create();
Dog dog = (Dog) animal;  // 캐스팅 필요

// 공변 반환 타입 사용 시
Dog dog = dogFactory.create();  // 캐스팅 불필요
```

빌더 패턴에서도 자주 쓰인다.

```java
class Builder<T extends Builder<T>> {
    protected String name;

    public T name(String name) {
        this.name = name;
        return (T) this;
    }

    public Product build() {
        return new Product(this);
    }
}

class SpecialBuilder extends Builder<SpecialBuilder> {
    private int priority;

    public SpecialBuilder priority(int priority) {
        this.priority = priority;
        return this;
    }

    @Override
    public SpecialProduct build() {  // Product → SpecialProduct 공변 반환
        return new SpecialProduct(this);
    }
}
```

---

## 6. 동적 바인딩 (Dynamic Binding)

오버라이딩의 핵심 동작 원리다. 컴파일 타임이 아닌 런타임에 실제 객체의 타입을 보고 호출할 메서드를 결정한다.

```java
class Payment {
    public void process() {
        System.out.println("기본 결제 처리");
    }
}

class CardPayment extends Payment {
    @Override
    public void process() {
        System.out.println("카드 결제 처리");
    }
}

class TransferPayment extends Payment {
    @Override
    public void process() {
        System.out.println("계좌이체 처리");
    }
}

// 컴파일 타임: payments의 타입은 Payment
// 런타임: 실제 객체에 따라 다른 메서드 호출
List<Payment> payments = List.of(new CardPayment(), new TransferPayment());
for (Payment p : payments) {
    p.process();  // 동적 바인딩으로 각각 다른 메서드 실행
}
```

### JVM 내부에서 일어나는 일

JVM은 각 클래스마다 **vtable(가상 메서드 테이블)**을 관리한다. 객체의 메서드를 호출하면 JVM이 해당 객체의 실제 클래스의 vtable을 조회해서 호출할 메서드 주소를 찾는다.

```
Payment vtable:
  process() → Payment.process

CardPayment vtable:
  process() → CardPayment.process   ← 오버라이딩으로 교체됨

TransferPayment vtable:
  process() → TransferPayment.process
```

변수의 선언 타입(컴파일 타임 타입)은 **어떤 메서드를 호출할 수 있는지** 결정하고, 실제 객체 타입(런타임 타입)은 **어떤 구현이 실행되는지** 결정한다.

### 동적 바인딩이 적용되지 않는 경우

- **static 메서드**: 클래스에 바인딩되므로 참조 타입 기준으로 호출된다 (정적 바인딩).
- **private 메서드**: 상속 자체가 안 되므로 바인딩 대상이 아니다.
- **final 메서드**: JVM이 최적화 여지가 있지만, 개념적으로는 동적 바인딩 대상이 맞다. 단, 오버라이딩이 불가능하므로 vtable에서 교체가 일어나지 않는다.
- **필드 접근**: 필드는 동적 바인딩 대상이 아니다. 참조 타입 기준으로 접근된다.

```java
class Parent {
    public String name = "Parent";
    public String getName() { return name; }
}

class Child extends Parent {
    public String name = "Child";
    @Override
    public String getName() { return name; }
}

Parent obj = new Child();
System.out.println(obj.name);        // "Parent" — 필드는 정적 바인딩
System.out.println(obj.getName());   // "Child"  — 메서드는 동적 바인딩
```

---

## 7. equals, hashCode, toString 오버라이딩

실무에서 가장 자주 오버라이딩하는 메서드 세 가지다. Object 클래스에 정의되어 있고, 기본 구현은 대부분 실무에서 쓸모없다.

### equals()

Object의 기본 equals()는 `==`과 동일하게 참조 비교를 한다. 값 기반 비교가 필요하면 오버라이딩해야 한다.

```java
public class Money {
    private final int amount;
    private final String currency;

    public Money(int amount, String currency) {
        this.amount = amount;
        this.currency = currency;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Money money = (Money) o;
        return amount == money.amount
            && Objects.equals(currency, money.currency);
    }
}
```

equals() 구현 시 지켜야 할 규약:

- **반사성**: `x.equals(x)`는 항상 true
- **대칭성**: `x.equals(y)`가 true면 `y.equals(x)`도 true
- **추이성**: `x.equals(y)`와 `y.equals(z)`가 true면 `x.equals(z)`도 true
- **일관성**: 같은 객체에 대해 여러 번 호출해도 결과가 같아야 한다
- **null 비교**: `x.equals(null)`은 항상 false

`instanceof` 대신 `getClass()`를 쓴 이유가 있다. `instanceof`를 쓰면 상속 관계에서 대칭성이 깨질 수 있다.

```java
// instanceof 사용 시 문제
class ColorMoney extends Money {
    private String color;

    @Override
    public boolean equals(Object o) {
        if (!(o instanceof ColorMoney)) return false;
        // ...
    }
}

Money m = new Money(1000, "KRW");
ColorMoney cm = new ColorMoney(1000, "KRW", "red");

m.equals(cm);   // true  — Money의 equals에서 cm은 instanceof Money
cm.equals(m);   // false — ColorMoney의 equals에서 m은 instanceof ColorMoney가 아님
// 대칭성 위반
```

### hashCode()

**equals()를 오버라이딩하면 hashCode()도 반드시 오버라이딩해야 한다.** 이걸 빠뜨리면 HashMap, HashSet에서 버그가 발생한다.

```java
public class Money {
    // ... equals 생략

    @Override
    public int hashCode() {
        return Objects.hash(amount, currency);
    }
}
```

왜 반드시 함께 오버라이딩해야 하는가?

```java
Money a = new Money(1000, "KRW");
Money b = new Money(1000, "KRW");

// equals만 오버라이딩하고 hashCode를 안 한 경우
Set<Money> set = new HashSet<>();
set.add(a);
set.contains(b);  // false가 나올 수 있다!
```

HashMap/HashSet은 먼저 hashCode()로 버킷을 찾고, 같은 버킷 안에서 equals()로 비교한다. hashCode()가 다르면 같은 버킷에 들어가지 않으므로 equals()가 호출될 기회조차 없다.

규약: `a.equals(b)`가 true면 `a.hashCode() == b.hashCode()`도 true여야 한다. 역은 성립하지 않아도 된다(해시 충돌 허용).

### toString()

Object의 기본 toString()은 `클래스명@해시코드` 형태를 반환한다. 디버깅할 때 쓸모없는 정보다.

```java
public class Money {
    @Override
    public String toString() {
        return amount + " " + currency;  // "1000 KRW"
    }
}
```

toString()은 디버깅과 로깅에서 쓰이므로 객체의 핵심 정보를 포함해야 한다. 민감 정보(비밀번호, 개인정보)는 마스킹 처리하거나 제외한다.

```java
public class User {
    private String name;
    private String email;
    private String password;

    @Override
    public String toString() {
        // password는 포함하지 않는다
        return "User{name='" + name + "', email='" + email + "'}";
    }
}
```

### record를 쓸 수 있는 경우

Java 16+ record를 사용하면 equals(), hashCode(), toString()이 자동 생성된다. 불변 데이터 객체에는 record가 적합하다.

```java
public record Money(int amount, String currency) {
    // equals, hashCode, toString 자동 생성
    // 커스텀이 필요하면 직접 오버라이딩 가능
}
```

---

## 8. 오버로딩(Overloading)과의 차이

오버라이딩과 이름이 비슷해서 혼동하기 쉽지만 완전히 다른 개념이다.

| 구분 | 오버라이딩 (Overriding) | 오버로딩 (Overloading) |
|------|------------------------|------------------------|
| 위치 | 상속 관계의 자식 클래스 | 같은 클래스 내부 |
| 메서드 이름 | 동일 | 동일 |
| 매개변수 | 동일해야 함 | 달라야 함 |
| 반환 타입 | 동일 또는 공변 타입 | 무관 |
| 바인딩 시점 | 런타임 (동적 바인딩) | 컴파일 타임 (정적 바인딩) |
| 어노테이션 | `@Override` 사용 | 없음 |

```java
class Calculator {
    // 오버로딩: 같은 이름, 다른 매개변수
    public int add(int a, int b) { return a + b; }
    public double add(double a, double b) { return a + b; }
    public int add(int a, int b, int c) { return a + b + c; }
}

class ScientificCalculator extends Calculator {
    // 오버라이딩: 부모 메서드 재정의
    @Override
    public int add(int a, int b) {
        int result = super.add(a, b);
        log.debug("add({}, {}) = {}", a, b, result);
        return result;
    }
}
```

오버로딩은 컴파일 타임에 매개변수 타입으로 호출할 메서드가 결정된다. 오버라이딩은 런타임에 객체 타입으로 결정된다. 이 차이를 명확히 이해해야 한다.
