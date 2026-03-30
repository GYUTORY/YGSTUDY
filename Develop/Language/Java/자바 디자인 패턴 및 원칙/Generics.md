---
title: Java Generics
tags: [language, java, 자바-디자인-패턴-및-원칙, generics, type-erasure, pecs]
updated: 2026-03-30
---

# Java Generics

제네릭은 컴파일 타임에 타입을 검증하고, 런타임에는 타입 정보가 사라지는 구조다. 이 간극 때문에 실무에서 예상치 못한 문제가 발생한다.

---

## Type Erasure

컴파일러는 제네릭 타입 파라미터를 컴파일 시점에 검증한 뒤, 바이트코드에서 제거한다. `List<String>`과 `List<Integer>`는 런타임에 같은 `List`다.

```java
List<String> strings = new ArrayList<>();
List<Integer> integers = new ArrayList<>();

// true — 런타임에 타입 파라미터 정보가 없다
System.out.println(strings.getClass() == integers.getClass());
```

컴파일러가 하는 일은 두 가지다.

1. 타입 파라미터를 바운드 타입이나 `Object`로 교체
2. 타입 안전성을 보장하기 위해 필요한 곳에 캐스트 삽입

```java
// 컴파일 전
public class Box<T> {
    private T value;
    public T get() { return value; }
}

// Type Erasure 후 (바이트코드 수준)
public class Box {
    private Object value;
    public Object get() { return value; }
}
```

바운드가 있으면 해당 타입으로 교체된다.

```java
// 컴파일 전
public class NumberBox<T extends Number> {
    private T value;
    public T get() { return value; }
}

// Type Erasure 후
public class NumberBox {
    private Number value;
    public Number get() { return value; }
}
```

### Type Erasure로 인한 제약사항

**primitive 타입 사용 불가**

타입 파라미터가 `Object`로 교체되기 때문에 primitive는 들어갈 수 없다. `List<int>`는 컴파일 에러다.

```java
// 컴파일 에러
// List<int> list = new ArrayList<>();

// 오토박싱으로 우회
List<Integer> list = new ArrayList<>();
```

대량 데이터를 다룰 때 박싱/언박싱 오버헤드가 문제가 된다. 이런 경우 `IntStream`, `int[]` 등 primitive 전용 API를 쓰는 게 낫다.

**instanceof 사용 불가**

런타임에 타입 파라미터 정보가 없으므로 `instanceof`로 제네릭 타입을 확인할 수 없다.

```java
public <T> void check(Object obj) {
    // 컴파일 에러 — 런타임에 T가 뭔지 알 수 없다
    // if (obj instanceof T) { }

    // 컴파일 에러
    // if (obj instanceof List<String>) { }

    // 이건 가능 — raw type 체크
    if (obj instanceof List<?>) {
        // 안의 타입은 알 수 없다
    }
}
```

타입을 확인해야 하는 상황이라면 `Class<T>` 토큰을 넘기는 패턴을 쓴다.

```java
public <T> T cast(Object obj, Class<T> type) {
    if (type.isInstance(obj)) {
        return type.cast(obj);
    }
    throw new ClassCastException("Expected " + type.getName());
}
```

**제네릭 배열 생성 불가**

```java
// 컴파일 에러
// T[] arr = new T[10];

// 컴파일 에러
// List<String>[] arr = new ArrayList<String>[10];
```

배열은 런타임에 원소 타입을 알아야 `ArrayStoreException`을 던질 수 있다. 제네릭 타입 정보는 런타임에 사라지므로 타입 안전성을 보장할 수 없다.

```java
// 만약 제네릭 배열 생성이 허용된다고 가정하면
Object[] objArr = new List<String>[10]; // 가정: 허용
objArr[0] = new ArrayList<Integer>();   // ArrayStoreException이 발생해야 하지만
                                         // 런타임에는 둘 다 List이므로 통과
// 나중에 String으로 꺼낼 때 ClassCastException 발생
```

배열이 필요한 경우 `@SuppressWarnings("unchecked")`와 함께 캐스팅하거나, `List<T>`를 쓴다.

```java
@SuppressWarnings("unchecked")
T[] createArray(int size) {
    return (T[]) new Object[size]; // 실제로는 Object[]
}
```

이 패턴은 외부에 노출하면 위험하다. `ArrayList` 내부 구현이 이 방식을 쓰지만, `toArray(T[])` 메서드에서는 `Array.newInstance`를 사용해 실제 타입의 배열을 만든다.

---

## Bounded Type Parameter

타입 파라미터에 상한을 지정하면 해당 타입의 메서드를 사용할 수 있다.

```java
// T는 Comparable을 구현한 타입만 받는다
public static <T extends Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

여러 바운드를 동시에 걸 수 있다. 클래스가 먼저, 인터페이스가 뒤에 온다.

```java
// T는 Number의 하위 클래스이면서 Comparable을 구현해야 한다
public static <T extends Number & Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

### 재귀적 타입 바운드 (Recursive Type Bound)

`<T extends Comparable<T>>` 형태를 재귀적 타입 바운드라 한다. 자기 자신과 비교 가능한 타입만 받겠다는 의미다.

이 패턴은 `Comparable`, `Builder`, `Enum` 등에서 자주 나온다.

```java
// Enum의 실제 선언
public abstract class Enum<E extends Enum<E>> implements Comparable<E> { }
```

Builder 패턴에서 상속을 지원할 때 쓰는 방법이다.

```java
public abstract class Pizza {
    final Set<String> toppings;

    abstract static class Builder<T extends Builder<T>> {
        Set<String> toppings = new HashSet<>();

        public T addTopping(String topping) {
            toppings.add(topping);
            return self();
        }

        // 하위 클래스에서 this를 반환
        protected abstract T self();
        public abstract Pizza build();
    }

    Pizza(Builder<?> builder) {
        toppings = new HashSet<>(builder.toppings);
    }
}

public class Calzone extends Pizza {
    private final boolean sauceInside;

    public static class Builder extends Pizza.Builder<Builder> {
        private boolean sauceInside = false;

        public Builder sauceInside() {
            sauceInside = true;
            return this;
        }

        @Override
        protected Builder self() { return this; }

        @Override
        public Calzone build() { return new Calzone(this); }
    }

    private Calzone(Builder builder) {
        super(builder);
        sauceInside = builder.sauceInside;
    }
}

// 메서드 체이닝이 하위 타입을 반환한다
Calzone calzone = new Calzone.Builder()
    .addTopping("Ham")      // Calzone.Builder 반환 (Pizza.Builder가 아님)
    .sauceInside()
    .build();
```

`self()` 없이 `return (T) this`로 캐스팅하면 동작은 하지만, 타입 안전하지 않다. 잘못된 상속 구조에서 `ClassCastException`이 날 수 있다.

---

## PECS (Producer Extends, Consumer Super)

와일드카드를 쓸 때 `extends`와 `super` 중 뭘 써야 하는지 판단하는 규칙이다.

- 데이터를 **읽기만** 하면(produce) `? extends T`
- 데이터를 **쓰기만** 하면(consume) `? super T`
- 읽고 쓰기 **둘 다** 하면 와일드카드를 쓰지 않는다

```java
// src에서 읽고(produce), dst에 쓴다(consume)
public static <T> void copy(List<? extends T> src, List<? super T> dst) {
    for (T item : src) {
        dst.add(item);
    }
}
```

`Collections.copy`의 실제 시그니처가 이 형태다.

### 왜 이렇게 해야 하는가

`List<? extends Number>`에는 `List<Integer>`, `List<Double>` 등이 올 수 있다. 여기에 값을 넣으면 실제 리스트 타입과 충돌할 수 있으므로 읽기만 가능하다.

```java
List<? extends Number> numbers = new ArrayList<Integer>();
Number n = numbers.get(0);   // OK — Number로 읽을 수 있다
// numbers.add(1);            // 컴파일 에러 — Integer인지 Double인지 알 수 없다
```

`List<? super Integer>`에는 `List<Integer>`, `List<Number>`, `List<Object>` 등이 올 수 있다. Integer는 이 모든 타입의 하위이므로 쓰기가 가능하다. 읽을 때는 `Object`로만 받을 수 있다.

```java
List<? super Integer> list = new ArrayList<Number>();
list.add(1);                  // OK — Integer는 넣을 수 있다
Object obj = list.get(0);    // OK — Object로만 읽을 수 있다
// Integer i = list.get(0);   // 컴파일 에러
```

### 실무 적용

`Comparator`를 파라미터로 받을 때 흔히 실수하는 부분이다.

```java
// 이렇게 하면 Comparator<String>만 받을 수 있다
public static <T> void sort(List<T> list, Comparator<T> comparator) { }

// 이렇게 하면 Comparator<Object>도 받을 수 있다
// Comparator는 T를 consume하므로 super를 쓴다
public static <T> void sort(List<T> list, Comparator<? super T> comparator) { }
```

`Collections.sort`의 실제 시그니처가 `Comparator<? super T>`를 받는다. `Comparator<Object>`로 모든 타입을 비교할 수 있어야 하는 상황이 있기 때문이다.

```java
// Comparator<Object>를 String 리스트에도 쓸 수 있다
Comparator<Object> byHashCode = Comparator.comparingInt(Object::hashCode);
List<String> names = Arrays.asList("Kim", "Lee", "Park");
names.sort(byHashCode); // Comparator<? super String>이므로 가능
```

---

## 공변, 반공변, 무공변

배열과 제네릭의 타입 관계가 다르다. 이걸 모르면 런타임 에러를 만나게 된다.

**배열은 공변(covariant)**

`Integer`가 `Number`의 하위 타입이면, `Integer[]`도 `Number[]`의 하위 타입이다.

```java
Number[] numbers = new Integer[10]; // 컴파일 OK
numbers[0] = 3.14;                  // 런타임에 ArrayStoreException
```

컴파일은 되지만 런타임에 터진다. 배열의 공변성은 제네릭 이전의 설계 결정이다.

**제네릭은 무공변(invariant)**

`List<Integer>`는 `List<Number>`의 하위 타입이 아니다.

```java
// 컴파일 에러
// List<Number> numbers = new ArrayList<Integer>();

// 와일드카드를 써야 한다
List<? extends Number> numbers = new ArrayList<Integer>(); // OK
```

무공변이기 때문에 컴파일 시점에 타입 안전성을 보장한다. 배열처럼 런타임에 터지는 일이 없다.

**와일드카드로 공변/반공변 표현**

- `? extends T` — 공변. 읽기 전용으로 하위 타입 허용
- `? super T` — 반공변. 쓰기 전용으로 상위 타입 허용

이 관계를 이해하면 PECS가 자연스럽게 따라온다.

---

## 힙 오염 (Heap Pollution)

매개변수화된 타입의 변수가 실제로는 다른 타입의 객체를 참조하는 상태다. 주로 가변인자(varargs)와 제네릭을 조합할 때 발생한다.

```java
public static void faultyMethod(List<String>... stringLists) {
    Object[] array = stringLists;          // List<String>[]이 Object[]로 변환
    List<Integer> intList = Arrays.asList(42);
    array[0] = intList;                     // 힙 오염 발생
    String s = stringLists[0].get(0);       // ClassCastException
}
```

가변인자 메서드는 내부적으로 배열을 만든다. `List<String>...`은 `List<String>[]`이 되는데, Type Erasure 후에는 `List[]`가 된다. 배열의 공변성 때문에 `Object[]`로 변환 가능하고, 여기에 다른 타입의 `List`를 넣을 수 있게 된다.

### @SafeVarargs

메서드가 가변인자 배열을 통해 힙 오염을 일으키지 않는다고 보장할 때 쓴다. 컴파일러 경고를 제거한다.

```java
// 안전한 경우 — 배열을 읽기만 한다
@SafeVarargs
public static <T> List<T> listOf(T... elements) {
    return Arrays.asList(elements);  // 배열에 쓰지 않음
}

// 안전하지 않은 경우 — 배열에 쓴다
// @SafeVarargs를 붙이면 안 된다
public static <T> void unsafeMethod(T... args) {
    Object[] array = args;
    array[0] = "wrong type"; // 힙 오염 가능성
}
```

`@SafeVarargs`를 붙일 수 있는 조건:
- 가변인자 배열에 값을 쓰지 않는다
- 가변인자 배열의 참조를 외부로 노출하지 않는다
- `final`, `static`, `private` 메서드 또는 생성자에만 붙일 수 있다 (오버라이드 불가한 메서드)

```java
// 이런 메서드는 @SafeVarargs를 쓰면 안 된다
public static <T> T[] toArray(T... args) {
    return args;  // 배열 참조를 외부로 노출
}

// 호출 시
String[] result = toArray("a", "b");  // ClassCastException
// 실제로는 Object[]가 반환되기 때문
```

---

## Bridge Method

제네릭을 상속할 때 컴파일러가 자동으로 생성하는 메서드다. Type Erasure로 인해 부모와 자식의 메서드 시그니처가 달라지는 것을 보정한다.

```java
public class Node<T> {
    private T data;
    public void setData(T data) {
        this.data = data;
    }
}

public class StringNode extends Node<String> {
    @Override
    public void setData(String data) {
        System.out.println("StringNode: " + data);
        super.setData(data);
    }
}
```

Type Erasure 후 `Node.setData`는 `setData(Object)`가 된다. 그런데 `StringNode.setData`는 `setData(String)`이다. 시그니처가 다르므로 오버라이드가 아니라 오버로드가 된다.

이를 해결하기 위해 컴파일러가 Bridge Method를 생성한다.

```java
// 컴파일러가 StringNode에 자동 생성하는 Bridge Method
public void setData(Object data) {
    setData((String) data);  // 실제 메서드로 위임
}
```

### 디버깅 시 주의점

**스택 트레이스에 Bridge Method가 나타난다**

```
Exception in thread "main" java.lang.ClassCastException:
    java.lang.Integer cannot be cast to java.lang.String
    at StringNode.setData(StringNode.java:1)  // Bridge Method
    at Main.main(Main.java:5)
```

Bridge Method에서 캐스트 실패가 발생하면, 소스 코드에 없는 줄에서 에러가 나는 것처럼 보인다. 이때 바이트코드를 확인하면 원인을 파악할 수 있다.

```bash
javap -c StringNode.class
```

**리플렉션에서 Bridge Method가 잡힌다**

```java
for (Method m : StringNode.class.getDeclaredMethods()) {
    System.out.println(m.getName() + " - bridge: " + m.isBridge()
        + " - params: " + Arrays.toString(m.getParameterTypes()));
}
// setData - bridge: false - params: [class java.lang.String]
// setData - bridge: true  - params: [class java.lang.Object]
```

리플렉션으로 메서드를 찾을 때 `isBridge()`로 필터링하지 않으면 같은 이름의 메서드가 두 개 나와서 혼란스럽다.

```java
// Bridge Method를 제외하고 실제 메서드만 가져오기
Arrays.stream(StringNode.class.getDeclaredMethods())
    .filter(m -> !m.isBridge())
    .forEach(System.out::println);
```

---

## 제네릭과 리플렉션

런타임에 타입 정보가 사라지지만, 클래스의 필드나 메서드 시그니처에 선언된 제네릭 타입 정보는 바이트코드 메타데이터로 남아 있다. 리플렉션으로 이 정보를 꺼낼 수 있다.

### 타입 토큰 패턴 (Type Token)

`Class<T>`를 넘겨서 런타임에 타입 정보를 유지하는 패턴이다.

```java
public class JsonParser {
    public <T> T parse(String json, Class<T> type) {
        // Jackson, Gson 등의 라이브러리가 이 패턴을 쓴다
        return objectMapper.readValue(json, type);
    }
}

// 사용
User user = parser.parse(jsonString, User.class);
```

문제는 `Class<T>`로는 `List<String>` 같은 매개변수화된 타입을 표현할 수 없다는 것이다. `List<String>.class`라는 건 존재하지 않는다.

### Super Type Token

Neal Gafter가 제안한 패턴으로, 익명 클래스의 제네릭 타입 정보가 바이트코드에 남는 점을 이용한다.

```java
// 간소화한 구현
public abstract class TypeReference<T> {
    private final Type type;

    protected TypeReference() {
        Type superClass = getClass().getGenericSuperclass();
        this.type = ((ParameterizedType) superClass).getActualTypeArguments()[0];
    }

    public Type getType() { return type; }
}

// 사용 — 반드시 익명 클래스(중괄호 {})로 생성해야 한다
TypeReference<List<String>> ref = new TypeReference<List<String>>() {};
System.out.println(ref.getType());
// java.util.List<java.lang.String>
```

Jackson의 `TypeReference`, Guice의 `TypeLiteral`이 이 패턴의 구현체다.

```java
// Jackson에서 제네릭 타입 역직렬화
List<User> users = objectMapper.readValue(
    json,
    new TypeReference<List<User>>() {}
);
```

중괄호(`{}`)를 빼먹으면 익명 클래스가 아닌 `TypeReference` 자체를 인스턴스화하려는 것이 되어 컴파일 에러가 난다. 이 실수를 꽤 자주 한다.

### 리플렉션으로 필드의 제네릭 타입 확인

```java
public class Repository {
    private List<String> names;
    private Map<String, List<Integer>> data;
}

Field namesField = Repository.class.getDeclaredField("names");
Type type = namesField.getGenericType();

if (type instanceof ParameterizedType) {
    ParameterizedType pt = (ParameterizedType) type;
    System.out.println("Raw type: " + pt.getRawType());
    // Raw type: interface java.util.List
    System.out.println("Type args: " + Arrays.toString(pt.getActualTypeArguments()));
    // Type args: [class java.lang.String]
}
```

이 방식은 프레임워크에서 의존성 주입 시 타입을 결정하거나, ORM에서 엔티티 필드의 타입을 분석할 때 쓴다. Spring의 `ResolvableType`, Jackson의 `JavaType`이 이 메커니즘 위에 만들어져 있다.

### 제네릭 타입 정보를 활용한 팩토리

```java
public abstract class GenericDao<T> {
    private final Class<T> entityClass;

    @SuppressWarnings("unchecked")
    protected GenericDao() {
        Type superClass = getClass().getGenericSuperclass();
        ParameterizedType pt = (ParameterizedType) superClass;
        this.entityClass = (Class<T>) pt.getActualTypeArguments()[0];
    }

    public T findById(Long id) {
        return entityManager.find(entityClass, id);
    }
}

// 사용
public class UserDao extends GenericDao<User> {
    // entityClass가 User.class로 자동 설정된다
}
```

JPA의 `GenericDao` 패턴이 이 방식이다. 주의할 점은 중간에 제네릭을 유지한 채 한 번 더 상속하면 `getGenericSuperclass()`가 예상과 다른 결과를 줄 수 있다는 것이다.

```java
// 이런 구조는 문제가 생긴다
public abstract class SpecialDao<T> extends GenericDao<T> { }
public class UserDao extends SpecialDao<User> { }
// GenericDao의 생성자에서 SpecialDao<User>를 보게 되므로
// getActualTypeArguments()[0]이 User가 아니라 T가 된다
```

이 경우 타입 계층을 타고 올라가며 실제 타입 인자를 찾는 유틸리티가 필요하다. Spring의 `GenericTypeResolver`가 이런 상황을 처리한다.

---

## 정리

제네릭을 쓸 때 기억해야 할 것들:

- Type Erasure 때문에 런타임에는 타입 파라미터 정보가 없다. `instanceof`, 제네릭 배열 생성, primitive 타입이 안 되는 이유가 다 여기에 있다.
- PECS — 데이터를 꺼내면 `extends`, 넣으면 `super`. `Comparator`는 대상을 소비하므로 `? super T`다.
- 가변인자와 제네릭을 같이 쓰면 힙 오염이 발생할 수 있다. 배열에 쓰지 않고 참조를 노출하지 않을 때만 `@SafeVarargs`를 쓴다.
- Bridge Method는 스택 트레이스와 리플렉션에서 혼란을 준다. `isBridge()`로 필터링한다.
- 런타임에 제네릭 타입이 필요하면 타입 토큰이나 Super Type Token을 쓴다. 중괄호 빼먹지 않도록 주의한다.
