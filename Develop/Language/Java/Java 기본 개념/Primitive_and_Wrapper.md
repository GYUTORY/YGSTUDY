---
title: "원시 타입과 래퍼 클래스"
tags: [java, primitive, wrapper, autoboxing, unboxing]
updated: 2026-03-25
---

# 원시 타입과 래퍼 클래스

## 원시 타입 8종

Java의 원시 타입은 객체가 아니라 값 자체를 스택에 저장한다.

| 타입 | 크기 | 기본값 | 범위 |
|------|------|--------|------|
| `byte` | 1byte | 0 | -128 ~ 127 |
| `short` | 2byte | 0 | -32,768 ~ 32,767 |
| `int` | 4byte | 0 | 약 -21억 ~ 21억 |
| `long` | 8byte | 0L | 약 -922경 ~ 922경 |
| `float` | 4byte | 0.0f | IEEE 754 단정밀도 |
| `double` | 8byte | 0.0d | IEEE 754 배정밀도 |
| `char` | 2byte | '\u0000' | 0 ~ 65,535 |
| `boolean` | JVM 구현에 따라 다름 | false | true / false |

`boolean`의 실제 크기는 JVM 스펙에 정의되어 있지 않다. HotSpot에서는 내부적으로 1byte를 쓰지만, 배열에서는 1byte, 단독 필드에서는 4byte(int로 처리)인 경우도 있다.

## 래퍼 클래스

각 원시 타입에 대응하는 래퍼 클래스가 있다.

| 원시 타입 | 래퍼 클래스 |
|-----------|-------------|
| `byte` | `Byte` |
| `short` | `Short` |
| `int` | `Integer` |
| `long` | `Long` |
| `float` | `Float` |
| `double` | `Double` |
| `char` | `Character` |
| `boolean` | `Boolean` |

래퍼 클래스는 힙에 객체로 생성된다. 원시 타입보다 메모리를 더 쓰고, GC 대상이 된다.

## 오토박싱과 언박싱

Java 5부터 컴파일러가 원시 타입과 래퍼 사이의 변환을 자동으로 넣어준다.

```java
// 오토박싱: int → Integer
Integer a = 10; // 컴파일러가 Integer.valueOf(10)으로 변환

// 언박싱: Integer → int
int b = a; // 컴파일러가 a.intValue()로 변환
```

바이트코드를 확인하면 실제로 `Integer.valueOf()`와 `intValue()`가 호출되는 걸 볼 수 있다.

### 언박싱 시 NullPointerException

래퍼 타입이 `null`일 때 언박싱하면 NPE가 발생한다. 이건 실무에서 자주 만나는 문제다.

```java
Integer count = null;
int result = count; // NullPointerException 발생
```

DB에서 nullable 컬럼을 조회할 때 흔히 발생한다.

```java
// MyBatis나 JPA에서 nullable int 컬럼을 조회할 때
public class Order {
    private int quantity; // DB에 NULL이 들어있으면 NPE
}

// 이렇게 해야 한다
public class Order {
    private Integer quantity; // nullable 컬럼은 래퍼 타입으로 받아야 한다
}
```

삼항 연산자에서도 예상 못한 언박싱이 일어난다.

```java
Integer a = null;
Integer b = (a != null) ? a : 0;
// 문제없어 보이지만, 오른쪽이 int 리터럴이라서
// 컴파일러가 전체를 int로 추론 → a를 언박싱 시도 → NPE
// 실제로는 조건이 false이므로 0이 반환되어 이 경우엔 괜찮지만,
// 아래처럼 조건이 true일 때 문제가 된다

Boolean flag = null;
boolean result = (flag != null) ? flag : false;
// flag가 null이 아닌 경우에도 문제없지만,
// 타입 추론 자체가 boolean이라서 flag가 null이면 NPE

// 안전한 방법
Integer a = null;
Integer b = (a != null) ? a : Integer.valueOf(0);
```

## Integer 캐시 함정

`Integer.valueOf()`는 -128에서 127 사이의 값을 캐시한다. 이 범위 안의 값은 같은 객체를 반환한다.

```java
Integer a = 127;
Integer b = 127;
System.out.println(a == b); // true (같은 캐시 객체)

Integer c = 128;
Integer d = 128;
System.out.println(c == d); // false (다른 객체)
```

이게 버그의 원인이 되는 이유는, 테스트에서 작은 값으로 확인했을 때는 `==`가 잘 동작하다가 운영에서 큰 값이 들어오면 갑자기 실패하기 때문이다.

```java
// 이런 코드가 테스트는 통과하고 운영에서 터진다
public boolean isSameProduct(Integer productId1, Integer productId2) {
    return productId1 == productId2; // 128 이상이면 false
}

// 반드시 equals를 써야 한다
public boolean isSameProduct(Integer productId1, Integer productId2) {
    return Objects.equals(productId1, productId2);
}
```

캐시 범위는 JVM 옵션 `-XX:AutoBoxCacheMax`로 변경할 수 있지만, 이걸 건드리는 건 좋은 생각이 아니다. 근본적으로 래퍼 타입끼리 `==`로 비교하지 않는 게 맞다.

### Long, Short, Byte, Character도 캐시한다

`Long.valueOf()`, `Short.valueOf()`, `Byte.valueOf()`도 -128~127 범위를 캐시한다. `Character.valueOf()`는 0~127을 캐시한다. `Float`과 `Double`은 캐시하지 않는다.

```java
Long a = 127L;
Long b = 127L;
System.out.println(a == b); // true

Long c = 128L;
Long d = 128L;
System.out.println(c == d); // false
```

## == vs equals 정리

```java
int a = 100;
int b = 100;
a == b; // true (값 비교)

Integer c = 100;
Integer d = 100;
c == d;      // true (캐시 범위라서 같은 객체)
c.equals(d); // true (값 비교)

Integer e = 200;
Integer f = 200;
e == f;      // false (캐시 범위 밖이라 다른 객체)
e.equals(f); // true (값 비교)

int g = 200;
Integer h = 200;
g == h; // true (h가 언박싱되어 값 비교)
```

규칙은 단순하다.

- 원시 타입끼리 비교: `==` 사용
- 래퍼 타입끼리 비교: `equals()` 사용
- 원시 타입과 래퍼 비교: `==` 가능 (언박싱 발생), 단 래퍼가 null이면 NPE

실무에서는 `Objects.equals()`를 쓰는 게 안전하다. null-safe하기 때문이다.

## 성능 차이

래퍼 타입은 객체이므로 원시 타입보다 메모리를 많이 쓰고, GC 부담이 생긴다.

```java
// 원시 타입: 약 40ms
long start = System.nanoTime();
long sum = 0;
for (int i = 0; i < 10_000_000; i++) {
    sum += i;
}

// 래퍼 타입: 약 200ms 이상
Long sum2 = 0L;
for (int i = 0; i < 10_000_000; i++) {
    sum2 += i; // 매 반복마다 언박싱 → 연산 → 오토박싱
}
```

반복문 안에서 래퍼 타입을 쓰면 매번 박싱/언박싱이 일어나면서 불필요한 객체가 대량 생성된다.

메모리 차이도 크다.

| 타입 | 메모리 |
|------|--------|
| `int` | 4byte |
| `Integer` | 약 16byte (객체 헤더 12byte + int 4byte, 8byte 정렬) |
| `int[1000]` | 약 4KB |
| `Integer[1000]` | 약 20KB (객체 참조 + 각 Integer 객체) |

## 래퍼 타입을 써야 하는 경우

원시 타입을 쓸 수 있는 곳에서는 원시 타입을 쓴다. 래퍼를 써야 하는 경우는 정해져 있다.

**제네릭 타입 파라미터**

```java
List<int> list = new ArrayList<>();    // 컴파일 에러
List<Integer> list = new ArrayList<>(); // OK
Map<String, Integer> map = new HashMap<>();
```

제네릭은 참조 타입만 받기 때문에 래퍼를 써야 한다.

**null이 의미를 가지는 경우**

```java
// "값이 없음"을 표현해야 할 때
public class SearchCondition {
    private Integer minPrice;  // null이면 조건 없음
    private Integer maxPrice;  // null이면 조건 없음
}
```

원시 타입은 null이 될 수 없어서, "값이 설정되지 않음"을 표현할 방법이 없다. 0이나 -1 같은 매직 넘버를 쓰는 것보다 null을 쓰는 게 의도가 명확하다.

**DB 매핑에서 nullable 컬럼**

```java
// JPA Entity
@Entity
public class Product {
    private int stock;          // NOT NULL 컬럼
    private Integer discountRate; // nullable 컬럼
}
```

**Optional과 함께 쓸 때**

```java
OptionalInt optInt = OptionalInt.of(10);       // 원시 타입 전용
Optional<Integer> optInteger = Optional.of(10); // 래퍼 타입

// 원시 타입 전용 Optional이 있으니 되도록 이쪽을 쓴다
OptionalInt, OptionalLong, OptionalDouble
```

## 실무에서 자주 하는 실수

### 1. Map의 getOrDefault와 언박싱

```java
Map<String, Integer> map = new HashMap<>();
int value = map.getOrDefault("key", null); // NPE
```

`getOrDefault`의 반환 타입이 `Integer`인데, null이 반환되면 `int`로 언박싱하면서 NPE가 발생한다.

### 2. 컬렉션 remove 메서드 혼동

```java
List<Integer> list = new ArrayList<>(List.of(1, 2, 3, 4, 5));
list.remove(3);           // 인덱스 3의 요소를 제거 → [1, 2, 3, 5]
list.remove(Integer.valueOf(3)); // 값 3을 제거 → [1, 2, 4, 5]
```

`remove(int index)`와 `remove(Object o)` 두 메서드가 오버로딩되어 있어서, `int` 리터럴을 넘기면 인덱스로 동작한다. 값으로 제거하려면 명시적으로 `Integer`로 변환해야 한다.

### 3. switch문에서 null

```java
Integer status = null;
switch (status) { // NPE - switch는 내부적으로 intValue()를 호출한다
    case 1: break;
    case 2: break;
}
```

Java 17 이전까지 switch에 null을 넘길 수 없다. null 체크를 먼저 해야 한다.
