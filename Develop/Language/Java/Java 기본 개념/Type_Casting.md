---
title: "Java 형변환 (Type Casting)"
tags: [java, type-casting, primitive, reference, instanceof]
updated: 2026-03-25
---

# Java 형변환 (Type Casting)

## 형변환이란

한 타입의 값을 다른 타입으로 변환하는 것이다. Java에서는 크게 **기본 타입(primitive) 형변환**과 **참조 타입(reference) 형변환**으로 나뉜다.

---

## 기본 타입 형변환

### 묵시적 형변환 (Widening)

작은 타입에서 큰 타입으로 변환할 때 자동으로 일어난다. 컴파일러가 알아서 처리하기 때문에 별도 캐스팅 구문이 필요 없다.

```java
int num = 100;
long bigNum = num;       // int → long, 자동 변환
double d = bigNum;       // long → double, 자동 변환
```

변환 방향은 다음과 같다:

```
byte → short → int → long → float → double
              char ↗
```

여기서 주의할 점이 하나 있다. `long → float` 변환이 자동으로 되긴 하는데, **정밀도 손실이 발생한다.**

```java
long bigValue = 1234567890123456789L;
float f = bigValue;
System.out.println(f);              // 1.23456794E18
System.out.println((long) f);       // 1234567939550609408

// 원래 값과 완전히 다른 숫자가 된다
```

`float`는 유효 자릿수가 약 7자리밖에 안 되기 때문에 `long`의 큰 값을 담으면 뒷자리가 날아간다. 컴파일 에러가 안 나서 놓치기 쉬운 부분이다.

### 명시적 형변환 (Narrowing)

큰 타입에서 작은 타입으로 변환할 때는 직접 캐스팅해야 한다.

```java
double pi = 3.14159;
int intPi = (int) pi;    // 3, 소수점 이하 버림 (반올림 아님)

long big = 300;
byte b = (byte) big;     // 44, 오버플로우 발생
```

`byte`의 범위는 -128~127이다. 300을 `byte`로 캐스팅하면 하위 8비트만 남기 때문에 전혀 다른 값이 나온다. 컴파일러가 경고도 안 해주기 때문에 범위를 직접 확인해야 한다.

### 정밀도 손실이 실제로 문제가 되는 경우

금액 계산에서 `double`을 쓰면 거의 반드시 문제가 생긴다.

```java
double price = 0.1 + 0.2;
System.out.println(price);           // 0.30000000000000004
System.out.println(price == 0.3);    // false
```

이런 경우 `BigDecimal`을 써야 한다.

```java
BigDecimal a = new BigDecimal("0.1");
BigDecimal b = new BigDecimal("0.2");
BigDecimal result = a.add(b);
System.out.println(result);                        // 0.3
System.out.println(result.compareTo(new BigDecimal("0.3")) == 0);  // true
```

`BigDecimal` 생성 시 `new BigDecimal(0.1)` 처럼 double을 직접 넣으면 이미 부동소수점 오차가 들어간 상태로 생성된다. 반드시 문자열로 넣어야 한다.

### int 연산 시 형변환

```java
int a = 1_000_000;
int b = 1_000_000;
int result = a * b;           // 오버플로우, -727379968
long correct = (long) a * b;  // 1000000000000
```

`a * b`를 먼저 계산하면 이미 `int` 범위를 넘기 때문에 오버플로우가 발생한다. `(long) a * b`로 피연산자 하나를 먼저 `long`으로 변환해야 한다. `(long)(a * b)`는 이미 오버플로우된 결과를 변환하는 것이라 의미가 없다.

---

## 참조 타입 형변환

### 업캐스팅 (Upcasting)

하위 클래스를 상위 클래스 타입으로 변환하는 것이다. 자동으로 된다.

```java
class Animal {
    void eat() { System.out.println("eating"); }
}

class Dog extends Animal {
    void bark() { System.out.println("woof"); }
}

Animal animal = new Dog();  // 업캐스팅, 자동
animal.eat();               // OK
// animal.bark();           // 컴파일 에러 — Animal 타입이라 bark()에 접근 불가
```

실제 객체는 `Dog`이지만, 참조 변수 타입이 `Animal`이라 `Dog`에만 있는 메서드는 호출할 수 없다.

### 다운캐스팅 (Downcasting)

상위 클래스를 하위 클래스 타입으로 변환하는 것이다. 명시적 캐스팅이 필요하고, **실패할 수 있다.**

```java
Animal animal = new Dog();
Dog dog = (Dog) animal;     // OK — 실제 객체가 Dog이니까
dog.bark();                 // woof

Animal animal2 = new Animal();
Dog dog2 = (Dog) animal2;   // ClassCastException 발생
```

`ClassCastException`은 런타임에 터진다. 컴파일 시점에는 문제가 없어 보이기 때문에 실제 서비스에서 이걸로 장애가 나는 경우가 있다.

### ClassCastException 발생 패턴

실무에서 자주 보는 패턴:

```java
// 컬렉션에서 꺼낼 때
List<Object> list = new ArrayList<>();
list.add("hello");
list.add(123);

for (Object obj : list) {
    String s = (String) obj;  // 두 번째 원소에서 ClassCastException
}
```

제네릭을 제대로 쓰면 이런 문제는 생기지 않는다. `List<Object>`로 선언한 시점에서 이미 설계가 잘못된 것이다.

---

## instanceof와 패턴 매칭

### 기본 instanceof

다운캐스팅 전에 타입을 확인하는 방법이다.

```java
Animal animal = getAnimal();  // 어떤 타입이 올지 모름

if (animal instanceof Dog) {
    Dog dog = (Dog) animal;
    dog.bark();
}
```

### instanceof 패턴 매칭 (Java 16+)

Java 16부터 `instanceof`와 동시에 변수 선언이 가능해졌다. 캐스팅 코드를 따로 쓸 필요가 없다.

```java
if (animal instanceof Dog dog) {
    dog.bark();  // 바로 사용 가능
}
```

기존 코드와 비교하면 한 줄이 줄어든 것뿐이지만, 캐스팅 실수를 원천적으로 방지한다.

### 패턴 매칭의 스코프

패턴 변수의 스코프가 직관적이지 않은 경우가 있다.

```java
// if-else에서 사용
if (obj instanceof String s) {
    System.out.println(s.length());  // OK
} else {
    // s 사용 불가
}

// 부정문에서 사용
if (!(obj instanceof String s)) {
    return;
}
// 여기서 s 사용 가능 — 위에서 return했으니 여기 도달하면 반드시 String
s.length();
```

부정문에서 패턴 변수가 살아있는 건 처음 보면 헷갈릴 수 있다. 컴파일러가 흐름을 분석해서 해당 변수가 확실히 할당된 경우에만 사용을 허용한다.

### switch 패턴 매칭 (Java 21+)

Java 21에서는 `switch`문에서도 패턴 매칭을 쓸 수 있다.

```java
static String describe(Object obj) {
    return switch (obj) {
        case Integer i -> "정수: " + i;
        case String s  -> "문자열 길이: " + s.length();
        case int[] arr -> "int 배열, 크기: " + arr.length;
        case null      -> "null";
        default        -> "알 수 없는 타입: " + obj.getClass().getName();
    };
}
```

`null` 케이스를 별도로 처리할 수 있다는 점이 기존 `switch`와 다르다. `null`을 안 넣으면 `NullPointerException`이 발생하니 주의해야 한다.

### guarded pattern

조건을 추가로 걸 수 있다.

```java
return switch (obj) {
    case String s when s.length() > 10 -> "긴 문자열";
    case String s                      -> "짧은 문자열";
    case Integer i when i > 0          -> "양수";
    case Integer i                     -> "0 이하";
    default                            -> "기타";
};
```

패턴 순서가 중요하다. 더 구체적인 조건을 위에 써야 한다. 순서를 바꾸면 컴파일 에러가 난다.

---

## 형변환 관련 주의사항

### 오토박싱/언박싱에서의 함정

```java
Integer a = 127;
Integer b = 127;
System.out.println(a == b);   // true — Integer 캐시 범위 (-128~127)

Integer c = 128;
Integer d = 128;
System.out.println(c == d);   // false — 캐시 범위 밖이라 다른 객체
```

`==`는 참조 비교이기 때문에 `equals()`를 써야 한다. 127까지는 캐시 때문에 우연히 `true`가 나와서 버그를 늦게 발견하는 경우가 있다.

### null 언박싱

```java
Integer boxed = null;
int primitive = boxed;  // NullPointerException
```

DB에서 nullable 컬럼을 `Integer`로 받은 다음 `int`에 넣으면 이 문제가 생긴다. MyBatis나 JPA에서 결과를 매핑할 때 자주 겪는다.

### 문자열 → 숫자 변환

```java
int num = Integer.parseInt("123");       // OK
int fail = Integer.parseInt("123.45");   // NumberFormatException
int fail2 = Integer.parseInt("");         // NumberFormatException
int fail3 = Integer.parseInt(null);      // NumberFormatException

// 안전한 변환
public static Optional<Integer> safeParseInt(String s) {
    try {
        return Optional.of(Integer.parseInt(s));
    } catch (NumberFormatException e) {
        return Optional.empty();
    }
}
```

외부에서 들어오는 값(HTTP 파라미터, 설정 파일 등)을 파싱할 때는 항상 예외 처리가 필요하다.
