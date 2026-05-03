---
title: Java 클래스(Class)와 메서드(Method)
tags: [language, java, 객체지향-프로그래밍-oop, class, class-vs-method]
updated: 2026-05-03
---

## 클래스와 메서드의 위치

자바를 처음 배우면 클래스와 메서드의 차이를 단순히 "클래스는 설계도, 메서드는 함수"로 외운다. 실무에서는 이 정도로는 부족하다. 메서드 시그니처가 어떻게 구성되는지, 정적 메서드와 인스턴스 메서드가 호출될 때 JVM 내부에서 무슨 일이 벌어지는지, 오버로딩된 메서드 중 컴파일러가 어떤 기준으로 하나를 고르는지를 모르면 NoSuchMethodError나 AmbiguousMethodCallException 같은 예외가 터졌을 때 원인을 찾기 어렵다.

클래스는 JVM 메서드 영역(Method Area)에 로드되는 타입 정보다. 클래스를 정의하면 그 안에 필드, 메서드, 생성자, 정적 블록, 중첩 클래스 같은 멤버가 들어간다. 메서드는 그중 동작을 표현하는 멤버 하나일 뿐이다. 즉 메서드는 항상 어떤 클래스에 속해 있고, 자바에는 클래스 바깥의 자유 함수(free function)가 존재하지 않는다.

```java
public class OrderService {
    private final OrderRepository repository;

    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }

    public Order findById(long id) {
        return repository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
    }
}
```

위 코드에서 `OrderService`는 클래스, `findById`는 인스턴스 메서드다. `findById`는 `OrderService`라는 타입 정보 안에 묶여 메서드 영역에 로드된다. 객체를 `new OrderService(repo)`로 생성하면 힙(heap)에 인스턴스가 만들어지지만, 메서드 본문 자체는 인스턴스마다 복사되지 않고 메서드 영역에 한 번만 존재한다. 인스턴스가 1만 개여도 `findById`의 바이트코드는 한 벌이다.

---

## 메서드 시그니처를 구성하는 요소

자바 언어 명세(JLS)에서 메서드 시그니처는 **메서드 이름 + 매개변수 타입 목록**만을 의미한다. 실무에서 흔히 "메서드 시그니처"라고 부를 때는 접근 제어자, 리턴 타입, throws 절까지 포함한 메서드 헤더 전체를 가리키는 경우가 많다. 이 둘을 구분하지 못하면 오버로딩 규칙을 잘못 이해하게 된다.

```java
public <T extends Comparable<T>> List<T> sortedCopy(Collection<? extends T> source)
        throws NullPointerException {
    // ...
}
```

이 메서드 헤더를 분해하면 다음 요소가 보인다.

- 접근 제어자(`public`): 호출 가능한 범위를 결정한다. `public`, `protected`, `default(생략)`, `private` 네 가지가 있다.
- 비접근 제어자(`static`, `final`, `abstract`, `synchronized`, `native`, `strictfp`): 메서드의 동작 방식을 바꾼다. `static`이면 인스턴스 없이 호출되고, `final`이면 하위 클래스에서 오버라이드를 막는다.
- 제네릭 타입 파라미터(`<T extends Comparable<T>>`): 호출 시점에 타입을 추론하기 위한 선언.
- 리턴 타입(`List<T>`): 호출자에게 돌려줄 값의 타입. `void`도 리턴 타입의 일종이다.
- 메서드 이름(`sortedCopy`): 자바에서 메서드 이름은 식별자이며, 동일 클래스 안에서 같은 이름이 여러 개 존재할 수 있다(오버로딩).
- 파라미터 목록(`Collection<? extends T> source`): 시그니처를 구성하는 핵심. 변수 이름은 시그니처에 포함되지 않는다. 즉 `void f(int a)`와 `void f(int b)`는 같은 메서드다.
- throws 절(`throws NullPointerException`): 체크 예외(checked exception)는 반드시 throws에 명시하거나 메서드 안에서 잡아야 한다. 언체크 예외는 throws에 적어도 되고 안 적어도 된다.

throws 절은 시그니처가 아니기 때문에, throws만 다른 두 메서드를 같은 클래스에 정의할 수 없다. 비슷하게 리턴 타입만 다른 메서드도 오버로딩이 안 된다. 이를 모르고 `int parse(String s)`와 `long parse(String s)`를 같은 클래스에 두려다가 컴파일 에러를 만나는 경우가 종종 있다.

리턴 타입에 관해 한 가지 더 알아둘 점은 **공변 반환 타입(covariant return type)** 이다. 자바 5부터 오버라이드한 메서드는 부모보다 더 구체적인 타입을 반환할 수 있다. `Object clone()`을 오버라이드하면서 `Order clone()`으로 좁히는 식이다. 이건 시그니처 동일성 규칙의 예외가 아니라, 오버라이드의 호환성 규칙으로 별도로 정의되어 있다.

---

## 인스턴스 메서드와 정적 메서드: 호출 메커니즘의 차이

표면적으로 인스턴스 메서드는 `obj.method()`, 정적 메서드는 `Class.method()`로 호출한다는 차이만 있어 보인다. 실제 JVM에서는 두 메서드가 완전히 다른 바이트코드 명령으로 디스패치된다. 이 차이를 모르면 성능 분석을 하거나 모킹 라이브러리가 왜 정적 메서드를 못 잡는지를 이해하기 어렵다.

### 호출 명령의 차이

자바 바이트코드에는 메서드 호출 명령이 다섯 종류 있다.

- `invokestatic`: 정적 메서드 호출.
- `invokevirtual`: 일반 인스턴스 메서드 호출. 가상 디스패치(virtual dispatch).
- `invokespecial`: 생성자, `super.method()`, private 메서드 호출. 디스패치 없이 정확한 타깃을 호출한다.
- `invokeinterface`: 인터페이스 메서드 호출.
- `invokedynamic`: 람다, 메서드 레퍼런스 등에서 사용.

`Math.max(1, 2)`는 `invokestatic`으로, `list.add(item)`은 `invokevirtual`(또는 `invokeinterface`)로 컴파일된다. 정적 메서드는 호출 시점에 어떤 메서드를 실행할지가 컴파일 시점에 이미 결정되어 있다. 인스턴스 메서드는 런타임에 객체의 실제 타입을 보고 어떤 구현을 부를지를 결정한다. 이게 다형성의 핵심이다.

```java
class Animal {
    void sound() { System.out.println("..."); }
    static void info() { System.out.println("Animal.info"); }
}

class Dog extends Animal {
    @Override
    void sound() { System.out.println("멍멍"); }
    static void info() { System.out.println("Dog.info"); }
}

Animal a = new Dog();
a.sound();   // "멍멍" — 런타임 타입(Dog) 기준 디스패치
a.info();    // "Animal.info" — 컴파일 시점 타입(Animal) 기준
```

정적 메서드는 오버라이드되지 않는다. `Dog.info()`는 부모의 `Animal.info()`를 가리는(hide) 것이지 재정의하는 게 아니다. 변수 `a`의 선언 타입이 `Animal`이므로 `a.info()`는 컴파일러가 `Animal.info()`로 변환한다. 이걸 모르고 정적 메서드에 다형성이 적용될 거라 기대하면 디버깅하다가 한참을 헤맨다.

### 메모리와 수명

정적 메서드와 정적 필드는 클래스가 처음 사용되는 시점에 클래스 로더가 클래스 메타데이터와 함께 메서드 영역(JDK 8 이후로는 Metaspace)에 올린다. 인스턴스 메서드도 메서드 영역에 올라간다는 점은 동일하지만, 호출 시 항상 첫 번째 인자로 `this` 참조를 암시적으로 받는다.

```java
class Counter {
    int count;
    void increment() { count++; }
}
```

`increment()`의 바이트코드는 사실상 `static void increment(Counter this)` 형태로 동작한다. 그래서 인스턴스 메서드를 호출하려면 항상 객체 참조가 스택에 먼저 올라가야 한다. `null.method()`를 호출하면 NullPointerException이 나는 이유가 여기 있다. 정적 메서드는 객체 참조가 필요 없으니 null 체크 없이도 호출이 가능하다.

### 실무 판단 기준

정적 메서드로 만들지, 인스턴스 메서드로 만들지를 고민할 때는 다음을 기준으로 판단한다.

- 객체 상태(필드)에 의존하지 않고, 입력만으로 결과가 결정되면 정적 메서드 후보다. `Math.max`, `Collections.sort` 같은 유틸리티가 대표적이다.
- 객체 상태를 읽거나 변경한다면 무조건 인스턴스 메서드여야 한다.
- 단위 테스트에서 모킹이 필요하다면 정적 메서드를 피해야 한다. Mockito 같은 일반 모킹 도구는 정적 메서드를 가로채지 못한다(mockito-inline을 쓰면 가능하지만 비용이 크다). 그래서 외부 시스템과 통신하는 코드는 정적 메서드로 만들지 않는다.
- 정적 메서드는 상속 계층의 다형성 혜택을 못 받는다. 미래에 다른 구현으로 바꿀 가능성이 있다면 인터페이스 + 인스턴스 메서드로 가는 게 안전하다.

---

## 메서드 오버로딩과 컴파일러의 매칭 규칙

같은 클래스 안에 같은 이름의 메서드를 여러 개 정의하는 게 오버로딩이다. 컴파일러는 호출 시점의 인자 타입을 보고 후보 메서드 중 가장 적합한 하나를 골라야 한다. 이 규칙이 직관적이지 않아서, "왜 내가 의도한 메서드가 호출되지 않지?"라는 의문이 생기곤 한다.

JLS는 오버로딩 해소(overload resolution)를 세 단계로 정의한다.

1. **1단계 — 박싱/언박싱과 가변 인자 없이 적용 가능한 메서드 찾기**: 인자를 그대로 넘길 수 있는 메서드를 찾는다. 형변환은 위젓닝(int → long 같은 확장 변환)만 허용한다.
2. **2단계 — 박싱/언박싱을 허용하고 다시 찾기**: 1단계에서 못 찾으면 박싱/언박싱을 적용해 다시 시도한다.
3. **3단계 — 가변 인자(varargs)를 허용하고 다시 찾기**: 그래도 못 찾으면 varargs 메서드까지 후보에 포함시킨다.

핵심은 **컴파일러가 한 단계 안에서 후보를 찾으면 다음 단계로 넘어가지 않는다**는 점이다. 1단계에서 매칭되면 박싱이나 varargs 메서드는 무시된다.

```java
class Printer {
    void print(int x) { System.out.println("int"); }
    void print(Integer x) { System.out.println("Integer"); }
    void print(long x) { System.out.println("long"); }
    void print(Object x) { System.out.println("Object"); }
}

Printer p = new Printer();
p.print(10);          // "int" — 정확히 일치, 1단계에서 종료
p.print(10L);         // "long" — 정확히 일치
p.print((Integer) 10);// "Integer" — 정확히 일치
p.print("hello");     // "Object" — String은 Object로 위젓닝
```

여기서 `p.print(10)`이 `Integer`나 `Object`가 아닌 `int`로 가는 이유는 1단계에서 정확히 매칭되는 메서드가 있어 박싱(Integer)이나 위젓닝(Object)으로 넘어가지 않기 때문이다. 자바 5에서 오토박싱이 도입될 때 기존 코드의 동작이 바뀌지 않게 하려고 박싱을 더 낮은 우선순위로 둔 것이다.

가장 헷갈리는 케이스는 같은 단계에서 후보가 둘 이상 남는 경우다. 컴파일러는 "더 구체적인(more specific)" 메서드를 선택한다. `String`은 `Object`보다 더 구체적이고, `ArrayList`는 `List`보다 더 구체적이다. 어느 쪽이 더 구체적인지 결정할 수 없으면 컴파일 에러("reference to xxx is ambiguous")가 발생한다.

```java
class Ambiguous {
    void f(Integer x, Object y) {}
    void f(Object x, Integer y) {}
}

new Ambiguous().f(1, 1); // 컴파일 에러: ambiguous
```

`(Integer, Integer)` 인자에 대해 두 메서드가 모두 적용 가능하지만, 어느 쪽도 다른 쪽보다 더 구체적이지 않다. 이런 코드는 실무에서 만나면 둘 중 하나를 명시적으로 캐스팅해서 호출해야 한다. `null` 인자도 비슷한 문제를 일으킨다. `print(null)`을 호출했을 때 후보가 `print(String)`과 `print(Object)`라면 `String`이 더 구체적이라서 `print(String)`이 호출된다.

오버로딩과 오버라이드를 혼동하지 말아야 한다. 오버로딩은 컴파일 시점에 결정(static dispatch), 오버라이드는 런타임에 결정(dynamic dispatch)된다. `super.method()`도 오버라이드한 메서드 중 부모 구현을 명시적으로 부르는 것이지 오버로딩과는 무관하다.

---

## varargs를 쓸 때 조심해야 할 것들

가변 인자(varargs)는 자바 5에서 도입됐다. `void log(String... messages)`처럼 파라미터 타입 뒤에 `...`을 붙이면 호출자가 인자를 0개부터 N개까지 자유롭게 넘길 수 있다. 편리하지만 실무에서 사고를 내는 케이스가 몇 가지 있다.

### 내부적으로는 배열이다

`void log(String... messages)`는 컴파일 후 `void log(String[] messages)`와 사실상 같다. 호출 시점마다 배열이 새로 생성되므로, 핫패스(hot path)에서 varargs 메서드를 무차별로 호출하면 GC 부담이 늘어난다. 로그 라이브러리들이 `log(String, Object)`, `log(String, Object, Object)` 같은 오버로딩을 제공하는 이유다.

### Object... 와 Object[] 사이의 함정

```java
void show(Object... args) {
    System.out.println("개수: " + args.length);
}

show("a", "b", "c");          // 개수: 3
show(new String[]{"a", "b"}); // 개수: 2 — 배열을 펼친다
show(new Object[]{"a", "b"}); // 개수: 2
show((Object) new String[]{"a", "b"}); // 개수: 1 — 배열 자체를 인자로
```

`Object...` 파라미터에 배열을 넘기면 컴파일러가 그 배열을 그대로 varargs 배열로 취급할지, 단일 인자로 취급할지를 결정해야 한다. 배열 타입이 `Object[]`나 그 하위 타입이면 펼쳐서 전달하고, 아니면 단일 원소로 감싼다. 의도와 다르게 동작하는 경우가 잦으므로 명시적으로 `(Object)` 캐스팅을 해야 안전하다. `String.format`에 `Object[]`를 넘기다가 인자가 한 개로 인식돼 포맷이 깨지는 일이 흔하다.

### 오버로딩과 함께 쓰면 우선순위에서 밀린다

앞서 말한 매칭 규칙의 3단계가 varargs다. 정확한 시그니처가 있으면 varargs 메서드는 절대 호출되지 않는다. `print(int x)`와 `print(int... xs)`가 함께 있으면 `print(1)`은 항상 `print(int)`로 간다. varargs 버전을 부르려면 `print(new int[]{1})`처럼 배열로 명시해야 한다.

### 제네릭 varargs와 힙 오염(heap pollution)

```java
@SafeVarargs
static <T> List<T> asList(T... elements) {
    return Arrays.asList(elements);
}
```

제네릭 타입의 varargs는 내부적으로 `Object[]`로 만들어진다. 배열은 공변(covariant)인데 제네릭은 불공변(invariant)이라서 둘이 만나면 타입 안정성이 깨질 수 있다. 컴파일러가 "unchecked" 경고를 내는데, 메서드 본문에서 배열을 외부로 노출하지 않고 읽기만 한다면 `@SafeVarargs`를 붙여 경고를 억제할 수 있다. 단, 어노테이션은 `static`, `final`, `private` 메서드에만 붙일 수 있다. 인스턴스 메서드에서는 오버라이드 가능성 때문에 안전을 보장할 수 없어서 막혀 있다.

### 가변 인자는 마지막 파라미터여야 한다

`void f(String... names, int count)`처럼 varargs 뒤에 다른 파라미터를 둘 수 없다. 시그니처에서 varargs는 항상 마지막에 와야 한다. 호출 시점에 어디까지가 varargs인지 결정할 수 없기 때문이다.

---

## 정리

클래스와 메서드는 단순히 "설계도와 함수"의 관계가 아니다. 클래스는 JVM 메서드 영역에 로드되는 타입 정보의 단위이고, 메서드는 그 안에서 동작을 표현하는 멤버다. 메서드 시그니처는 이름과 파라미터 타입으로만 결정되며, 리턴 타입과 throws는 시그니처가 아니다. 인스턴스 메서드는 `invokevirtual`로 동적 디스패치되고 정적 메서드는 `invokestatic`으로 정적 바인딩되는데, 이 차이가 다형성과 모킹 가능 여부를 가른다. 오버로딩 해소는 정확 일치 → 박싱 → varargs 순서로 단계적으로 진행되며, 같은 단계 안에서는 더 구체적인 메서드가 선택된다. varargs는 편리하지만 배열로 변환되는 특성, 오버로딩 우선순위, 제네릭과의 상호작용 때문에 함정이 많다. 이 디테일을 알고 있어야 NoSuchMethodError, AmbiguousMethodCall, 의도와 다른 오버로드 호출 같은 문제를 빠르게 진단할 수 있다.
