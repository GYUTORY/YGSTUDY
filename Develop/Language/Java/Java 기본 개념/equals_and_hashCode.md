---
title: "equals()와 hashCode()"
tags: [Java, Object, equals, hashCode, HashMap]
updated: 2026-03-25
---

# equals()와 hashCode()

## equals()와 hashCode() 계약

`Object` 클래스에 정의된 두 메서드는 서로 계약 관계에 있다.

1. `equals()`가 true인 두 객체는 반드시 같은 `hashCode()`를 반환해야 한다.
2. `hashCode()`가 같다고 `equals()`가 true일 필요는 없다. (해시 충돌)
3. `equals()`가 false인 두 객체가 같은 `hashCode()`를 가질 수 있다.

핵심은 1번이다. **equals만 오버라이드하고 hashCode를 오버라이드하지 않으면 HashMap, HashSet에서 버그가 발생한다.**

```java
public class Money {
    private int amount;
    private String currency;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Money money = (Money) o;
        return amount == money.amount && Objects.equals(currency, money.currency);
    }

    @Override
    public int hashCode() {
        return Objects.hash(amount, currency);
    }
}
```

`Objects.hash()`는 내부적으로 `Arrays.hashCode()`를 호출한다. 필드를 배열로 만들어서 해시를 계산하는 방식이라 호출마다 배열 생성 비용이 있다. 성능이 민감한 객체라면 직접 계산하는 게 낫다.

```java
@Override
public int hashCode() {
    int result = amount;
    result = 31 * result + (currency != null ? currency.hashCode() : 0);
    return result;
}
```

31을 곱하는 이유는 소수(prime)이면서 `31 * i == (i << 5) - i`로 비트 연산 최적화가 가능하기 때문이다. String 클래스도 같은 방식을 쓴다.

---

## HashMap에서의 동작 원리

HashMap은 키 객체의 `hashCode()`로 버킷 인덱스를 결정하고, 같은 버킷 안에서 `equals()`로 정확한 키를 찾는다.

```
put(key, value) 흐름:
1. key.hashCode() 호출 → 내부 해시 함수로 버킷 인덱스 계산
2. 해당 버킷에 이미 노드가 있으면 → key.equals()로 비교
3. equals가 true → 값 교체 / false → 연결 리스트(또는 트리)에 추가

get(key) 흐름:
1. key.hashCode() 호출 → 버킷 인덱스 계산
2. 해당 버킷의 노드들과 key.equals() 비교
3. 일치하는 노드의 value 반환
```

여기서 문제가 되는 시나리오를 보자.

### equals만 오버라이드한 경우

```java
public class UserId {
    private long id;

    public UserId(long id) {
        this.id = id;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        return id == ((UserId) o).id;
    }

    // hashCode 오버라이드 안 함
}
```

```java
Map<UserId, String> map = new HashMap<>();
map.put(new UserId(1L), "홍길동");

String name = map.get(new UserId(1L));
System.out.println(name); // null 출력
```

`new UserId(1L)`을 두 번 생성했다. `equals()`는 true를 반환하지만, `hashCode()`는 `Object`의 기본 구현(메모리 주소 기반)을 사용하므로 서로 다른 값이 나온다. 다른 버킷을 찾아가니 당연히 못 찾는다.

이 버그는 단위 테스트에서 잡기 어렵다. `equals()`로 직접 비교하면 정상이고, HashMap/HashSet에 넣었을 때만 문제가 드러난다.

### hashCode만 오버라이드한 경우

```java
public class UserId {
    private long id;

    public UserId(long id) {
        this.id = id;
    }

    @Override
    public int hashCode() {
        return Long.hashCode(id);
    }

    // equals 오버라이드 안 함
}
```

```java
Map<UserId, String> map = new HashMap<>();
map.put(new UserId(1L), "홍길동");

String name = map.get(new UserId(1L));
System.out.println(name); // null 출력
```

같은 버킷까지는 찾아가지만, `equals()`가 `Object`의 기본 구현(참조 비교)을 사용하므로 서로 다른 인스턴스는 false다. 마찬가지로 못 찾는다.

---

## 실무에서 자주 발생하는 버그 사례

### mutable 필드를 hashCode에 포함한 경우

```java
public class Session {
    private String sessionId;
    private String status; // "ACTIVE", "EXPIRED" 등

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Session s = (Session) o;
        return Objects.equals(sessionId, s.sessionId)
            && Objects.equals(status, s.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(sessionId, status);
    }
}
```

```java
Set<Session> sessions = new HashSet<>();
Session s = new Session("abc123", "ACTIVE");
sessions.add(s);

s.setStatus("EXPIRED"); // 상태 변경

sessions.contains(s); // false — 이미 들어있는데 못 찾음
sessions.remove(s);   // false — 삭제도 안 됨
sessions.size();       // 1 — 메모리 누수
```

`status`가 바뀌면 `hashCode()`가 달라진다. HashSet은 이전 hashCode로 계산한 버킷에 저장했으니, 새 hashCode로는 해당 버킷을 찾지 못한다. 객체는 Set 안에 남아있지만 접근할 수 없는 상태가 된다.

**hashCode 계산에는 불변 필드만 사용해야 한다.** 위 예제에서는 `sessionId`만 사용하는 게 맞다.

### JPA Entity에서의 equals/hashCode

JPA Entity는 특수한 상황이다. `persist()` 전에는 `id`가 null이고, 이후에 값이 할당된다.

```java
@Entity
public class Order {
    @Id @GeneratedValue
    private Long id;

    // 이렇게 하면 안 된다
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        return Objects.equals(id, ((Order) o).id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
```

```java
Set<Order> orders = new HashSet<>();
Order order = new Order();
orders.add(order);       // id = null, hashCode = Objects.hash(null) = 0

em.persist(order);       // id = 1L 할당됨
orders.contains(order);  // false — hashCode가 바뀌었다
```

persist 전에 HashSet에 넣고, persist 후에 조회하면 못 찾는다. 해결 방법은 두 가지다.

**방법 1: 비즈니스 키 사용**

```java
@Entity
public class Order {
    @Id @GeneratedValue
    private Long id;

    @Column(unique = true, nullable = false)
    private String orderNumber; // 비즈니스 키

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        return Objects.equals(orderNumber, ((Order) o).orderNumber);
    }

    @Override
    public int hashCode() {
        return Objects.hash(orderNumber);
    }
}
```

**방법 2: 고정 hashCode 반환**

```java
@Override
public int hashCode() {
    return getClass().hashCode();
}
```

모든 인스턴스가 같은 hashCode를 반환하므로 HashMap 성능이 O(n)으로 떨어진다. 하지만 정합성은 보장된다. Entity를 대량으로 Set에 넣는 경우가 아니라면 실무에서 문제될 일은 거의 없다.

---

## Lombok @EqualsAndHashCode 주의점

### 기본 동작

```java
@EqualsAndHashCode
public class Product {
    private Long id;
    private String name;
    private int price;
}
```

Lombok은 모든 non-static, non-transient 필드를 equals/hashCode에 포함한다. 위 코드는 `id`, `name`, `price` 세 필드 모두 사용한다.

### 상속 구조에서 callSuper

```java
@EqualsAndHashCode
public class Animal {
    private String species;
}

@EqualsAndHashCode
public class Dog extends Animal {
    private String name;
}
```

컴파일하면 Lombok이 경고를 낸다.

```
Generating equals/hashCode implementation but without a call to superclass,
even though this class does not extend java.lang.Object.
```

`Dog`의 equals/hashCode가 `name`만 비교하고 부모의 `species`는 무시한다. 같은 이름의 개와 고양이가 같은 객체로 취급될 수 있다.

```java
@EqualsAndHashCode(callSuper = true)
public class Dog extends Animal {
    private String name;
}
```

`callSuper = true`를 붙이면 부모 클래스의 equals/hashCode를 먼저 호출한다. **상속 구조에서는 반드시 `callSuper` 설정을 확인해야 한다.**

### 특정 필드 제외

```java
@EqualsAndHashCode(exclude = "updatedAt")
public class Product {
    private Long id;
    private String name;
    private LocalDateTime updatedAt;
}
```

`exclude`로 특정 필드를 뺄 수 있다. mutable하거나 비교 대상이 아닌 필드는 제외하는 게 좋다.

반대로 특정 필드만 포함하려면 `@EqualsAndHashCode.Include`와 `onlyExplicitlyIncluded`를 쓴다.

```java
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Product {
    @EqualsAndHashCode.Include
    private Long id;

    private String name;        // 제외됨
    private LocalDateTime updatedAt; // 제외됨
}
```

### JPA Entity에 @EqualsAndHashCode 쓰면 안 되는 이유

```java
@Entity
@EqualsAndHashCode // 하면 안 된다
public class Order {
    @Id @GeneratedValue
    private Long id;

    @OneToMany(mappedBy = "order")
    private List<OrderItem> items;
}
```

두 가지 문제가 있다.

1. `id`가 포함된다. 위에서 설명한 persist 전후 hashCode 변경 문제가 발생한다.
2. `items` 같은 연관 관계 필드가 포함된다. `equals()` 호출 시 lazy loading이 트리거되어 N+1 쿼리가 발생하거나, 세션이 닫힌 상태라면 `LazyInitializationException`이 터진다.

JPA Entity의 equals/hashCode는 직접 구현하는 게 안전하다. 비즈니스 키가 있으면 비즈니스 키로, 없으면 고정 hashCode + id 비교 방식으로 작성한다.

---

## equals() 구현 시 확인할 것

`equals()`를 직접 구현할 때 빠뜨리기 쉬운 부분들이 있다.

```java
@Override
public boolean equals(Object o) {
    // 1. 참조 비교 — 같은 인스턴스면 바로 true
    if (this == o) return true;

    // 2. null 체크와 타입 체크
    // instanceof를 쓰면 null 체크가 포함된다
    // 하지만 상속 구조에서 대칭성이 깨질 수 있다
    if (o == null || getClass() != o.getClass()) return false;

    // 3. 캐스팅 후 필드 비교
    Money money = (Money) o;
    return amount == money.amount
        && Objects.equals(currency, money.currency);
}
```

`instanceof` vs `getClass()` 선택은 상황에 따라 다르다.

- `instanceof`: 하위 클래스도 비교 대상에 포함. Liskov 치환 원칙을 따르지만 대칭성이 깨질 수 있다.
- `getClass()`: 정확히 같은 클래스만 비교. 대칭성이 보장되지만 다형성을 활용한 비교가 안 된다.

실무에서는 `getClass()` 비교가 안전하다. `instanceof`를 쓰려면 `equals()`를 final로 선언해서 하위 클래스가 오버라이드하지 못하게 막아야 한다.

```java
// instanceof 방식을 쓸 거면 final로 선언
public final boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Money money)) return false;
    return amount == money.amount
        && Objects.equals(currency, money.currency);
}
```

Java 16+에서는 `instanceof` 패턴 매칭으로 캐스팅을 줄일 수 있다.
