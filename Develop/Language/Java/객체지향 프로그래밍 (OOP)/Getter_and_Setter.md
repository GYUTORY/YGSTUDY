---
title: Getter와 Setter
tags: [language, java, 객체지향-프로그래밍-oop, getter-and-setter]
updated: 2026-07-26
---

# Getter와 Setter

Getter와 Setter는 private 필드에 대한 읽기/쓰기 메서드다. public 필드를 직접 노출하면 외부에서 유효하지 않은 값을 마음대로 넣을 수 있고, 나중에 검증 로직을 추가하거나 반환 타입을 바꿀 때 모든 호출 지점을 수정해야 한다. 메서드로 감싸면 내부 구현을 바꿔도 외부 인터페이스는 그대로 유지된다.

## 1. 기본 구조

private 필드를 외부에서 직접 접근할 수 없게 막고, 메서드로 읽기/쓰기 권한을 개별 제어하는 패턴이다. 캡슐화의 가장 기본적인 구현이다.

```java
class Person {
    private String name;
    private int age;

    public String getName() {
        return name;
    }

    public int getAge() {
        return age;
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setAge(int age) {
        if (age <= 0) {
            throw new IllegalArgumentException("나이는 0보다 커야 한다: " + age);
        }
        this.age = age;
    }
}
```

```java
Person person = new Person();
person.setName("홍길동");
person.setAge(25);
System.out.println(person.getName()); // 홍길동
person.setAge(-1); // IllegalArgumentException
```

## 2. Setter에서 데이터 검증

### 2.1 예외를 던져야 하는 이유

Setter 검증 예제를 보면 `System.out.println`으로 메시지만 출력하고 넘어가는 코드가 많다. 실무에서 이렇게 쓰면 호출하는 쪽에서 값이 설정되지 않았다는 걸 알 방법이 없다.

```java
// 나쁜 예 - 실패해도 호출자가 모른다
public void setPrice(int price) {
    if (price < 0) {
        System.out.println("가격은 0 이상이어야 합니다!");
        // 여기서 return하면 price는 여전히 0(초기값)
    } else {
        this.price = price;
    }
}

// 올바른 예 - 실패하면 호출자가 반드시 알게 된다
public void setPrice(int price) {
    if (price < 0) {
        throw new IllegalArgumentException("가격은 0 이상이어야 한다: " + price);
    }
    this.price = price;
}
```

null이나 빈 문자열 검증도 마찬가지다. `setName(null)`을 호출했을 때 아무 일도 안 일어나면 NPE가 나중에 엉뚱한 곳에서 터진다.

```java
public void setName(String name) {
    if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("상품명은 비어있을 수 없다");
    }
    this.name = name;
}
```

### 2.2 읽기/쓰기 전용 설정

Getter만 제공하면 읽기 전용이 된다. 은행 계좌처럼 잔액을 외부에서 직접 변경하면 안 되는 경우가 대표적이다.

```java
class BankAccount {
    private final String owner;
    private double balance;

    public BankAccount(String owner, double balance) {
        this.owner = owner;
        this.balance = balance;
    }

    public String getOwner() {
        return owner;
    }

    public double getBalance() {
        return balance;
    }

    // setBalance()가 없다. 잔액은 deposit/withdraw로만 변경한다.
    public void deposit(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("입금액은 0보다 커야 한다");
        }
        balance += amount;
    }

    public void withdraw(double amount) {
        if (amount > balance) {
            throw new IllegalStateException("잔액 부족");
        }
        balance -= amount;
    }
}
```

`setBalance(10000000)` 같은 코드를 컴파일 단계에서 막는다. Setter를 제공하지 않는 것 자체가 설계 의도를 드러낸다.

## 3. Lombok 활용

`@Getter`, `@Setter`를 붙이면 메서드를 직접 작성하지 않아도 된다.

```java
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
class User {
    private String username;
    private String email;
}
```

### 3.1 @Data를 JPA 엔티티에 쓰면 안 되는 이유

`@Data`는 `@Getter`, `@Setter`, `@ToString`, `@EqualsAndHashCode`, `@RequiredArgsConstructor`를 한 번에 붙여준다. 편리하지만 JPA 엔티티에는 쓰지 않는 것이 낫다.

```java
// 문제가 생기는 코드
@Data
@Entity
class Order {
    @Id
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private Member member;
}
```

Lombok이 생성하는 `equals()`와 `hashCode()`는 기본적으로 모든 필드를 포함한다. LAZY 로딩 관계 필드를 `equals()` 안에서 접근하면 프록시 객체가 초기화되면서 예상치 못한 쿼리가 실행된다. 양방향 연관관계에서 서로를 참조하는 구조면 `toString()`이나 `hashCode()`가 무한 재귀에 빠지는 경우도 있다.

JPA 엔티티에는 `@Getter`만 붙이고 `equals()`와 `hashCode()`는 id 필드만 써서 직접 구현하거나 `@EqualsAndHashCode(of = "id")`를 명시한다.

```java
@Getter
@EqualsAndHashCode(of = "id")
@Entity
class Order {
    @Id
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private Member member;
}
```

## 4. Getter와 Setter를 쓰지 말아야 하는 경우

### 4.1 불변 객체와 VO

`Money`, `Address`, `PhoneNumber` 같은 값 객체에는 Setter가 없어야 한다. 생성 이후 상태가 바뀌면 안 되는 객체들이다.

```java
class Money {
    private final long amount;
    private final String currency;

    public Money(long amount, String currency) {
        if (amount < 0) {
            throw new IllegalArgumentException("금액은 0 이상이어야 한다");
        }
        this.amount = amount;
        this.currency = currency;
    }

    public long getAmount() {
        return amount;
    }

    public String getCurrency() {
        return currency;
    }

    // 기존 객체를 변경하지 않고 새 객체를 반환한다
    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new IllegalArgumentException("통화 단위가 다르다");
        }
        return new Money(this.amount + other.amount, this.currency);
    }
}
```

Setter가 있으면 `money.setAmount(-100)`으로 불변식을 깰 수 있다.

### 4.2 mutable 객체 반환 시 방어적 복사

Getter가 mutable 객체를 그대로 반환하면 외부에서 내부 상태를 바꿀 수 있다.

```java
class Schedule {
    private List<String> tasks = new ArrayList<>();

    // 위험한 코드 - 반환된 리스트를 수정하면 내부 상태가 바뀐다
    public List<String> getTasks() {
        return tasks;
    }
}

Schedule schedule = new Schedule();
schedule.getTasks().add("외부에서 임의로 추가"); // 이게 가능하다
```

반환 시 복사본을 넘기거나 수정 불가 뷰를 반환한다.

```java
public List<String> getTasks() {
    return Collections.unmodifiableList(tasks);
    // 또는 new ArrayList<>(tasks)로 복사본을 반환
}
```

`Date` 객체도 같은 문제가 있다. `getCreatedAt()`이 `Date`를 그대로 반환하면 `date.setTime(0)`으로 내부 날짜를 조작할 수 있다. `LocalDateTime` 같은 불변 타입으로 교체하는 것이 근본적인 해결이다.

## 5. Java 16+ Record 클래스

불변 데이터 클래스가 필요할 때 Record를 쓰면 Getter 코드를 직접 작성하지 않아도 된다.

```java
record Point(int x, int y) {}

Point p = new Point(3, 4);
System.out.println(p.x()); // Getter 이름이 getX()가 아니라 x()
System.out.println(p.y());
```

Record는 private final 필드, 생성자, getter, `equals()`, `hashCode()`, `toString()`을 자동 생성한다. Setter는 없다. 불변 DTO나 VO에서 Lombok `@Value` 대신 쓸 수 있다.

getter 이름이 `getX()` 대신 `x()`라는 점이 주요 차이다. Jackson은 기본적으로 Record getter를 인식하지만, `get` prefix를 기대하는 일부 라이브러리와 호환 문제가 생길 수 있다.

## 6. Jackson 직렬화와 getter 네이밍

Jackson은 getter 이름으로 JSON 키를 결정한다. `getName()`은 `name`으로, `getAge()`는 `age`로 직렬화된다.

boolean 필드는 `isXxx()` 네이밍을 써야 Jackson이 올바르게 인식한다.

```java
class UserStatus {
    private boolean active;
    private boolean emailVerified;

    public boolean isActive() {
        return active;
    }

    public boolean isEmailVerified() {
        return emailVerified;
    }
}
// {"active": true, "emailVerified": false}
```

Lombok `@Getter`는 `boolean` 타입에서는 `isXxx()` 메서드를, `Boolean`(wrapper) 타입에서는 `getXxx()` 메서드를 생성한다.

```java
@Getter
class Flags {
    private boolean active;  // isActive() 생성
    private Boolean visible; // getVisible() 생성
}
```

직렬화는 두 경우 모두 동작하지만, `Boolean visible`에 `isVisible()`을 기대하는 코드와 섞이면 혼란이 생긴다. 같은 클래스에서 `boolean`과 `Boolean`을 섞어 쓰지 않는 것이 낫다. 명시적으로 `@JsonProperty`를 붙이면 getter 이름과 무관하게 JSON 키를 고정할 수 있다.

## 7. Setter와 멀티스레드

Setter가 있는 객체를 여러 스레드에서 공유하면 데이터 경합이 생긴다.

```java
class Counter {
    private int count = 0;

    public int getCount() {
        return count;
    }

    public void setCount(int count) {
        this.count = count;
    }
}

// 두 스레드가 동시에 접근하는 상황
Counter counter = new Counter();
// Thread A: counter.setCount(counter.getCount() + 1);
// Thread B: counter.setCount(counter.getCount() + 1);
// 최종 count가 2가 아니라 1이 될 수 있다
```

공유 상태가 필요하다면 `AtomicInteger`처럼 스레드 안전한 타입을 쓰거나 `synchronized`로 보호해야 한다. 불변 객체로 만들어서 공유 상태 자체를 없애는 방법도 있다.

스프링 빈은 기본적으로 싱글톤이다. 컨트롤러나 서비스 빈에 Setter로 요청별 상태를 저장하면 동시 요청이 들어올 때 서로의 데이터를 덮어쓴다. 스프링 빈의 인스턴스 변수는 요청과 무관한 공유 설정값에만 써야 한다.
