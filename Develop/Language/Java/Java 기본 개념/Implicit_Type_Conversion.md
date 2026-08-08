---
title: "암묵적 형변환"
tags: [java, language]
updated: 2026-08-05
---

# 암묵적 형변환

Java에서 타입이 자동으로 바뀌는 상황은 단순한 widening 외에도 여러 곳에 숨어 있다. 메서드 오버로딩 해결, 삼항 연산자 타입 결정, 문자열 연결 연산, 비교 연산에서도 컴파일러가 조용히 타입을 바꾼다. 각 케이스마다 JLS가 다른 규칙을 적용하기 때문에 이를 모르면 예상치 못한 컴파일 에러나 런타임 NPE를 만난다.

---

## 메서드 오버로딩 해결 시 widening 우선순위

오버로딩된 메서드가 여러 개 있을 때 컴파일러는 JLS가 정의한 3단계 절차로 어느 메서드를 호출할지 결정한다.

1단계는 widening primitive conversion만 허용한다. 박싱도 varargs도 고려하지 않는다. 1단계에서 적합한 후보를 찾으면 2, 3단계는 건너뛴다.

2단계는 박싱/언박싱을 허용한다. varargs는 여전히 고려하지 않는다.

3단계는 varargs를 허용한다.

```java
static void print(long l)    { System.out.println("long: " + l); }
static void print(Integer i) { System.out.println("Integer: " + i); }

print(1);  // "long: 1"
```

`1`은 `int` 리터럴이다. `print(long)`은 `int → long` widening(1단계)으로 선택된다. `print(Integer)`는 `int → Integer` 박싱(2단계)이 필요해 후순위다.

varargs도 같은 방식으로 밀린다.

```java
static void calc(double d)    { System.out.println("double"); }
static void calc(int... nums) { System.out.println("varargs"); }

calc(1);  // "double" — int → double widening이 varargs보다 앞
```

widening 순서 안에서 여러 후보가 있으면 가장 구체적인(narrow한) 타입을 선택한다.

```java
static void process(short s) { System.out.println("short"); }
static void process(int i)   { System.out.println("int"); }
static void process(long l)  { System.out.println("long"); }

process((byte) 1);  // "short" — byte에서 가장 가까운 widening 대상
```

`byte → short → int → long` 순서에서 `short`가 첫 번째 단계이기 때문에 선택된다. JLS의 "가장 구체적인 메서드(most specific method)" 규칙에 따라, `process(short)`가 `process(int)`보다 구체적이라 이긴다.

후보가 둘 이상이고 어느 쪽도 더 구체적이지 않으면 컴파일 에러가 난다.

```java
static void ambiguous(long a, int b) {}
static void ambiguous(int a, long b) {}

ambiguous(1, 2);  // 컴파일 에러 — 어느 후보도 다른 것보다 더 구체적이지 않음
```

실무에서 이 우선순위가 문제가 되는 경우는 `long` 오버로딩과 `Integer` 오버로딩이 공존할 때다. `int` 값을 넘기면 박싱 타입 쪽이 아니라 widening 쪽이 선택된다. 의도한 오버로딩이 호출되지 않는 것처럼 보여서 혼란이 생긴다.

---

## 삼항 연산자 타입 승격 규칙

`condition ? A : B`의 결과 타입은 A와 B를 컴파일 타임에 함께 보고 결정된다. 런타임에 어느 분기가 실행되는지와는 무관하다.

숫자 타입끼리는 widening 방향으로 승격된다. 하나가 `double`이면 결과 타입은 `double`, 하나가 `float`면 결과는 `float`, 하나가 `long`이면 결과는 `long`이다.

```java
boolean flag = true;

double d = flag ? 1 : 2.0;   // 1이 1.0으로 widening, 결과 타입 double
float  f = flag ? 1 : 2.0f;  // 결과 타입 float
long   l = flag ? 1 : 2L;    // 결과 타입 long
```

결과 타입이 결정된 이후 대입 대상 타입이 그보다 좁으면 컴파일 에러가 난다.

```java
int x = flag ? 1 : 2.0;   // 컴파일 에러
// 삼항 표현식 결과 타입이 double인데 int에 대입하려면 명시적 캐스팅 필요
```

`1`이 분명히 `int`인데 왜 에러가 나냐고 처음엔 이해가 안 될 수 있다. 컴파일러가 `1`과 `2.0`을 함께 보고 결과 타입을 `double`로 정했기 때문이다. 이미 `double`로 정해진 표현식을 `int`에 담으려니 좁아지는 변환이 발생한다.

```java
int x = (int)(flag ? 1 : 2.0);  // 결과를 명시적 캐스팅
int y = flag ? 1 : 2;            // 두 피연산자를 모두 int로
```

참조 타입이 섞이면 공통 상위 타입으로 결정된다.

```java
Object result = flag ? "string" : 42;
// 42는 Integer로 박싱, "string"은 String
// 두 타입의 공통 상위 타입으로 결정됨
```

---

## 문자열 + 연산에서 연산자 결합 순서

`+` 연산자는 왼쪽에서 오른쪽으로 결합한다. 피연산자 중 하나가 `String`이면 나머지를 문자열로 변환해 연결한다. 이 두 규칙이 합쳐지면 괄호 위치에 따라 결과가 달라진다.

```java
String s1 = "a" + 1 + 2;     // "a12"
String s2 = "a" + (1 + 2);   // "a3"
```

`"a" + 1 + 2`는 `("a" + 1) + 2`로 평가된다. `"a" + 1`이 먼저 `"a1"`이 되고, `"a1" + 2`가 `"a12"`가 된다. `"a" + (1 + 2)`는 괄호 안에서 `int` 덧셈이 먼저 일어나 `3`이 되고, `"a" + 3`이 `"a3"`가 된다.

숫자가 앞에 오면 다르게 동작한다.

```java
String s3 = 1 + 2 + "a";   // "3a"
String s4 = 1 + "a" + 2;   // "1a2"
```

`1 + 2 + "a"`는 `(1 + 2) + "a"` 순서라 `int` 덧셈이 먼저 된다. `1 + "a" + 2`는 `(1 + "a") + 2` 순서라 처음부터 문자열 연결이 일어난다.

실무에서 가장 많이 실수하는 패턴은 로그나 메시지 출력이다.

```java
int a = 10, b = 20;
System.out.println("합계: " + a + b);    // "합계: 1020" — 연결, 덧셈 아님
System.out.println("합계: " + (a + b));  // "합계: 30"
```

컴파일 에러도 경고도 없기 때문에 런타임에 잘못된 출력을 보기 전까지 발견이 어렵다.

`char` 타입을 문자열에 붙이는 경우도 주의가 필요하다.

```java
char c1 = 'A', c2 = 'B';
System.out.println("" + c1 + c2);  // "AB" — 왼쪽부터 문자열에 붙음
System.out.println(c1 + c2);       // 131 — int 덧셈 (65 + 66), 문자열 아님
```

`"" + c1 + c2`는 빈 문자열이 왼쪽에 있어서 `c1`부터 문자열 연결로 처리된다. `c1 + c2`는 왼쪽에 문자열이 없기 때문에 numeric promotion이 일어나 `int` 덧셈이 된다.

---

## 비교 연산자에서 char/byte/short의 int 승격

`==`, `<`, `>`, `!=` 같은 비교 연산자에서 `char`, `byte`, `short` 타입은 `int`로 승격된다. `'A' == 65`가 `true`가 되는 이유가 여기에 있다.

```java
char ch = 'A';
System.out.println(ch == 65);   // true — 'A'의 유니코드 포인트 65로 승격 비교
System.out.println(ch == 'A');  // true
```

`'A'`를 `int` 65와 비교할 때 `char` 값 65가 `int` 65로 승격된다. 값 변환 없이 같은 숫자 값으로 비교되기 때문에 `true`가 나온다.

`byte`와 `short`도 동일하게 승격된다.

```java
byte b = 127;
System.out.println(b == 127);   // true
System.out.println(b < 200);    // true — 127 < 200

short s = 1000;
System.out.println(s == 1000);  // true
```

`char`와 `short`를 직접 비교할 때 주의할 점이 있다. 둘 다 16비트지만 부호 해석이 다르다. 비교 시 둘 다 `int`로 승격되는데, 값이 달라질 수 있다.

```java
char  c = 40000;
short s = (short) 40000;  // -25536 — short 범위(-32768~32767)를 넘어 오버플로우

System.out.println(c == s);  // false
System.out.println((int) c); // 40000
System.out.println((int) s); // -25536
```

`c`는 `int` 40000으로, `s`는 `int` -25536으로 승격된다. 같은 비트 패턴에서 시작했지만 `char`는 0 확장(zero-extension), `short`는 부호 확장(sign-extension)으로 `int`가 되기 때문에 다른 값이 된다.

비교 연산의 한쪽이 `Character` 같은 박싱 타입이면 언박싱이 먼저 일어나고 비교한다.

```java
char c = 'A';
Character boxedChar = 'A';

System.out.println(c == boxedChar);  // true — Character가 언박싱되어 char → int 비교
System.out.println(boxedChar == 65); // true — Character 언박싱 → char → int
```

---

## 조건 표현식에서 null과 기본 타입 혼합 시 언박싱 NPE

삼항 연산자에서 한 피연산자가 기본 타입이고 다른 쪽이 박싱 타입 참조일 때 언박싱이 발생한다. 참조가 `null`이면 NPE가 난다.

```java
Integer boxed = null;
int result = condition ? boxed : 0;  // NPE — condition이 true일 때
```

이 코드가 NPE를 내는 과정은 이렇다. 삼항 표현식의 두 피연산자가 `Integer`(참조)와 `int`(기본)다. 한쪽이 기본 타입이면 JLS는 결과 타입을 기본 타입(`int`)으로 결정한다. `Integer` 피연산자를 `int`로 만들기 위해 언박싱이 필요하다. `boxed`가 `null`이면 언박싱 시점에 NPE가 발생한다.

```java
// 컴파일러가 생성하는 코드와 의미상 동일
int result = condition ? boxed.intValue() : 0;
```

대입 대상 타입이 `Integer`(참조)면 언박싱이 일어나지 않아서 NPE가 없다.

```java
Integer boxed = null;
Integer ref = condition ? boxed : 0;  // NPE 없음 — 결과 타입이 Integer
// condition이 true면 ref = null
// condition이 false면 0이 Integer로 박싱되어 ref에 저장
```

`condition ? null : 0` 형태는 컴파일부터 주의가 필요하다.

```java
int x = condition ? null : 0;
// 컴파일러는 null을 수용하기 위해 결과 타입을 Integer로 결정
// Integer → int 대입 시 언박싱 발생
// condition이 true면 null을 언박싱 → NPE

Integer y = condition ? null : 0;  // NPE 없음 — 결과가 Integer로 유지
```

`Boolean`을 `if` 조건식에 바로 쓸 때도 같은 메커니즘으로 NPE가 발생한다.

```java
Map<String, Boolean> flags = new HashMap<>();
// flags.get("key")는 키가 없으면 null 반환

if (flags.get("enabled")) {  // NPE — Boolean → boolean 언박싱, null이면 터짐
    // ...
}

// 안전하게 쓰는 방법
if (Boolean.TRUE.equals(flags.get("enabled"))) {
    // ...
}
```

`if` 조건식은 `boolean` 기본 타입이 필요하기 때문에 `Boolean` 참조를 언박싱한다. `null`이 들어오면 NPE가 발생한다.

MyBatis나 JPA에서 nullable 컬럼을 박싱 타입으로 받아서 삼항 연산자나 조건식에 바로 쓰는 코드가 이 문제를 자주 만든다.
