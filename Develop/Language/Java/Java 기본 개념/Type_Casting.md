---
title: "Java 형변환 (Type Casting)"
tags: [java, typescript, language]
updated: 2026-07-09
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

### 수치 타입 승격 (Numeric Promotion)

Java에서 산술 연산을 할 때 피연산자가 자동으로 승격된다. `byte`, `short`, `char`끼리 연산하면 결과가 `int`가 된다.

```java
byte a = 10;
byte b = 20;
// byte result = a + b;  // 컴파일 에러 — a + b의 결과가 int
int result = a + b;      // OK

byte c = (byte)(a + b);  // 명시적 캐스팅 필요
```

처음 Java를 배울 때 이 부분에서 컴파일 에러가 나면 당황하는 경우가 많다. `byte + byte = int`라는 규칙은 의도적인 설계로, JVM 명세에서 `int`보다 작은 타입의 산술은 `int`로 승격해서 처리한다.

```java
short x = 100;
short y = 200;
// short sum = x + y;   // 컴파일 에러
short sum = (short)(x + y);  // OK

// 복합 대입 연산자는 예외 — 암묵적으로 캐스팅이 들어감
x += y;  // 컴파일 에러 없음 (x = (short)(x + y)와 동일)
```

복합 대입 연산자(`+=`, `-=` 등)는 묵시적 캐스팅이 포함되어 있어서 컴파일 에러가 나지 않는다. 일반 `+` 연산과 동작이 달라 혼란스럽다.

`int`와 `long`이 섞이면 `long`으로 승격되고, `long`과 `float`가 섞이면 `float`으로 승격된다.

```java
int i = 10;
long l = 20L;
long promoted = i + l;   // int → long 승격 후 계산

float f = 1.5f;
float result2 = l + f;   // long → float 승격 후 계산 (정밀도 손실 가능)
```

### char 캐스팅의 특수성

`char`는 부호 없는 16비트 정수(0~65535)로 동작한다. `short`와 같은 크기지만 부호가 없어서 서로 호환되지 않는다.

```java
char ch = 'A';
int code = ch;           // 65, 묵시적 변환 가능 (char → int)
System.out.println(ch);  // A
System.out.println(code); // 65

// 역방향은 명시적 캐스팅 필요
char back = (char) 65;   // 'A'
char unicode = '\u0041'; // 'A'와 동일
```

`char`를 `short`로 직접 변환하면 부호 범위가 달라서 주의해야 한다.

```java
char ch = 40000;      // 유효 (char 범위: 0~65535)
// short s = ch;      // 컴파일 에러 — short 범위(-32768~32767) 초과 가능
short s = (short) ch; // -25536, 부호 비트 해석이 달라짐
```

문자 산술 연산에서도 승격이 일어난다.

```java
char a = 'A';
// char result = a + 1;  // 컴파일 에러 — int로 승격됨
char result = (char)(a + 1);  // 'B'

// for 루프에서 문자 순회
for (char c = 'a'; c <= 'z'; c++) {
    System.out.print(c);  // abcdefghijklmnopqrstuvwxyz
}
```

`char`를 문자열로 변환할 때도 함정이 있다.

```java
char ch = '5';
int num = ch - '0';          // 5 (문자를 숫자로)
String s1 = String.valueOf(ch);  // "5"
String s2 = "" + ch;         // "5" (문자열 연결)
String s3 = Character.toString(ch); // "5"

// 주의: (String)(Object) ch 같은 직접 캐스팅은 불가
```

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

## Wrapper 타입 변환 메서드

`Integer`, `Double` 같은 Wrapper 클래스는 다른 기본 타입으로 변환하는 메서드를 제공한다.

```java
Integer intObj = 42;
int    i  = intObj.intValue();      // 42
long   l  = intObj.longValue();     // 42L
double d  = intObj.doubleValue();   // 42.0
float  f  = intObj.floatValue();    // 42.0f
byte   b  = intObj.byteValue();     // 42
short  s  = intObj.shortValue();    // 42

Double dblObj = 3.99;
int truncated = dblObj.intValue();  // 3, 소수점 버림
long lVal     = dblObj.longValue(); // 3
```

`doubleValue()`, `longValue()` 같은 메서드들은 `Number` 추상 클래스에 정의되어 있어서, `Number` 타입으로 받아도 호출할 수 있다.

```java
Number num = Integer.valueOf(100);
double d = num.doubleValue();  // 100.0
```

실무에서는 직접 `intValue()`를 호출하는 것보다 언박싱(오토언박싱)을 더 많이 쓰지만, `Number` 타입으로 받아서 변환해야 할 때는 명시적 메서드가 필요하다.

`Number` 계열 클래스에서 다운 범위로 변환하면 값이 잘린다.

```java
Double big = 1234567890.99;
int cut = big.intValue();    // 1234567890, 소수 버림
byte byt = big.byteValue();  // 82, 하위 8비트만 남음
```

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

### 인터페이스 타입 캐스팅 런타임 동작

인터페이스 캐스팅은 클래스 상속 계층과 무관하게 실제 객체가 해당 인터페이스를 구현했는지만 본다.

```java
interface Flyable {
    void fly();
}

class Bird extends Animal implements Flyable {
    public void fly() { System.out.println("flying"); }
}

class Cat extends Animal {
    // Flyable 구현 안 함
}

Animal bird = new Bird();
Animal cat  = new Cat();

// 컴파일러는 Animal → Flyable 캐스팅을 허용 (Animal이 Flyable을 구현했을 수도 있으니)
Flyable f1 = (Flyable) bird;  // OK — Bird가 Flyable을 구현함
f1.fly();                     // flying

Flyable f2 = (Flyable) cat;   // ClassCastException — Cat은 Flyable 미구현
```

컴파일러가 막아주지 않기 때문에 런타임 전까지 에러가 안 난다. 상속 관계가 없는 두 클래스 간에는 컴파일러가 잡아주는 경우도 있다.

```java
String s = "hello";
// Integer i = (Integer) s;  // 컴파일 에러 — String과 Integer는 관련 없음
```

`String`과 `Integer`처럼 공통 상위 타입이 `Object`뿐이고 명백히 관계없으면 컴파일러가 거부한다. 반면 인터페이스는 구현 여부를 컴파일 타임에 알 수 없는 경우가 많아서 통과시킨다.

```java
// 안전하게 쓰려면 instanceof 확인
if (animal instanceof Flyable flyable) {
    flyable.fly();
}
```

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

## 배열 타입 캐스팅

배열도 참조 타입이기 때문에 캐스팅 규칙이 적용된다. 단, 기본 타입 배열은 공변(covariant)이 아니다.

```java
// 참조 타입 배열은 공변
Object[] objects = new String[3];  // OK — String[]은 Object[]의 하위 타입
objects[0] = "hello";              // OK
objects[1] = 42;                   // ArrayStoreException (런타임) — 실제 배열은 String[]

// 기본 타입 배열은 공변 아님
// Object[] ints = new int[3];     // 컴파일 에러
```

`Object[] objects = new String[3]` 처럼 배열을 업캐스팅하면 컴파일은 되지만, 실제 `String[]`이 아닌 타입을 넣으려 하면 `ArrayStoreException`이 발생한다. 제네릭이 없던 시절 레거시 코드에서 자주 보이는 패턴이다.

```java
// 배열 다운캐스팅
Object[] objs = new Dog[3];
Dog[] dogs = (Dog[]) objs;    // OK — 실제 타입이 Dog[]이니까
Cat[] cats = (Cat[]) objs;    // ClassCastException
```

```java
// 다차원 배열도 마찬가지
Object[][] matrix = new String[3][3];
String[][] strMatrix = (String[][]) matrix;  // OK
```

배열을 메서드 파라미터로 `Object[]`로 받을 때 실제 타입을 확인하려면:

```java
void process(Object[] arr) {
    if (arr instanceof String[] strArr) {
        // String[] 로직
    } else if (arr instanceof Integer[] intArr) {
        // Integer[] 로직
    }
}
```

---

## 제네릭과 타입 소거

### 타입 소거 (Type Erasure)

Java 제네릭은 컴파일 타임에만 존재하고, 바이트코드에서는 타입 파라미터가 지워진다. 런타임에 `List<String>`과 `List<Integer>`는 모두 `List`로 동일하다.

```java
List<String> strList = new ArrayList<>();
List<Integer> intList = new ArrayList<>();

System.out.println(strList.getClass() == intList.getClass());  // true
System.out.println(strList.getClass().getName());              // java.util.ArrayList
```

이 때문에 제네릭 타입으로 캐스팅할 때 컴파일러가 "unchecked cast" 경고를 낸다.

```java
Object obj = new ArrayList<String>();

// 컴파일 경고: unchecked cast
List<String> list = (List<String>) obj;

// 런타임에는 List로만 확인하고 <String>은 검사하지 않음
// 나중에 꺼낼 때 ClassCastException이 발생할 수 있음
```

타입 소거 때문에 제네릭 타입 파라미터로 `instanceof` 검사가 불가능하다.

```java
// 컴파일 에러 — 타입 파라미터는 소거되어 런타임에 확인 불가
// if (obj instanceof List<String>) { }

// 이건 가능 — 원시 타입(raw type)으로 확인
if (obj instanceof List<?>) {
    List<?> list = (List<?>) obj;
}
```

### Unchecked Cast와 힙 오염 (Heap Pollution)

타입 소거로 인해 런타임에 잘못된 타입이 컬렉션에 들어갈 수 있다.

```java
@SuppressWarnings("unchecked")
List<String> badList = (List<String>) (List<?>) new ArrayList<Integer>();
// 여기까지는 예외 없음

badList.add("valid");
// Integer가 들어있는 List<String>에 접근하면 나중에 터짐

for (String s : badList) {  // ClassCastException
    System.out.println(s.length());
}
```

이런 상황을 힙 오염이라고 한다. `@SuppressWarnings("unchecked")`로 경고를 무시하고 강제로 캐스팅하면 이 문제가 발생할 수 있다.

### 제네릭 배열 생성 불가

타입 소거 때문에 제네릭 타입의 배열을 직접 생성할 수 없다.

```java
// 컴파일 에러
// List<String>[] arr = new List<String>[10];

// 우회 방법 1 — raw type으로 생성 후 캐스팅 (경고 발생)
@SuppressWarnings("unchecked")
List<String>[] arr = (List<String>[]) new List[10];

// 우회 방법 2 — List<List<String>> 사용 (더 안전)
List<List<String>> listOfLists = new ArrayList<>();
```

실무에서는 우회 방법 1보다 방법 2를 쓰는 게 낫다. 배열 대신 컬렉션을 쓰면 타입 안정성을 유지할 수 있다.

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
