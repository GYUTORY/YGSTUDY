
# Java `static` 키워드의 개념과 활용

`static` 키워드는 Java에서 **클래스 레벨에서 공유되는 멤버**를 정의하는 데 사용됩니다. 이 문서에서는 `static`의 기본 개념과 사용해야 할 곳, 사용하지 않아야 할 곳을 예제와 함께 상세히 설명합니다.

---

## 1. `static`의 기본 개념
`static` 키워드는 **클래스의 인스턴스에 종속되지 않고 클래스 자체에 속하는 멤버(필드, 메서드, 내부 클래스 등)를 정의**할 때 사용됩니다.

- **인스턴스 멤버**: 객체가 생성될 때마다 별도로 존재하는 멤버.
- **정적 멤버(static 멤버)**: 클래스 로드 시점에 메모리에 한 번만 생성되고, 모든 인스턴스가 공유.

### 정적 멤버의 특징
1. 객체 생성 없이도 접근 가능 (클래스 이름을 통해 호출 가능).
2. 모든 인스턴스가 공유(필드의 경우 모든 객체가 같은 값을 참조).
3. 클래스 로드 시 초기화되고, 프로그램 종료 시 소멸.

### 예제: 정적 필드와 메서드
```java
class StaticExample {
    // 정적 필드
    static int counter = 0;

    // 정적 메서드
    static void incrementCounter() {
        counter++;
    }
}

public class StaticDemo {
    public static void main(String[] args) {
        // 인스턴스 없이 클래스 이름으로 정적 멤버에 접근
        StaticExample.incrementCounter();
        System.out.println("Counter: " + StaticExample.counter); // 출력: Counter: 1
    }
}
```

---

## 2. `static`을 선언해야 하는 경우
`static`을 사용하는 가장 일반적인 시나리오는 **공유해야 하는 데이터나 유틸리티 성격의 메서드**입니다.

### 2.1 공통 데이터(공유 리소스)
모든 객체가 동일한 값을 가져야 하는 변수는 `static`으로 선언합니다.

#### 예제: 공통 카운터
```java
class Counter {
    static int count = 0; // 모든 인스턴스가 공유

    public Counter() {
        count++;
    }
}

public class CounterTest {
    public static void main(String[] args) {
        new Counter();
        new Counter();
        System.out.println("생성된 객체 수: " + Counter.count); // 출력: 생성된 객체 수: 2
    }
}
```

### 2.2 유틸리티 메서드
객체와 관계없이 사용할 수 있는 함수는 `static`으로 선언합니다.

#### 예제: 유틸리티 클래스
```java
class MathUtils {
    static int add(int a, int b) {
        return a + b;
    }
}

public class MathTest {
    public static void main(String[] args) {
        int result = MathUtils.add(5, 10); // 객체 생성 없이 호출
        System.out.println("결과: " + result); // 출력: 결과: 15
    }
}
```

---

## 3. `static`을 사용하지 말아야 하는 경우
1. **인스턴스별로 상태가 달라야 하는 경우**:
    - 객체마다 고유한 값을 가져야 하는 변수는 정적 필드로 선언하지 않습니다.

#### 잘못된 사용 예제
```java
class Person {
    static String name; // 모든 객체가 같은 이름을 공유

    public Person(String name) {
        this.name = name; // 새로운 객체가 생성되면 기존 이름이 덮어써짐
    }
}

public class PersonTest {
    public static void main(String[] args) {
        Person p1 = new Person("Alice");
        Person p2 = new Person("Bob");

        System.out.println(p1.name); // 출력: Bob
        System.out.println(p2.name); // 출력: Bob
    }
}
```

#### 올바른 사용 예제
```java
class Person {
    String name; // 인스턴스별로 고유

    public Person(String name) {
        this.name = name;
    }
}

public class PersonTest {
    public static void main(String[] args) {
        Person p1 = new Person("Alice");
        Person p2 = new Person("Bob");

        System.out.println(p1.name); // 출력: Alice
        System.out.println(p2.name); // 출력: Bob
    }
}
```

2. **객체의 고유 동작이 필요한 경우**:
    - 메서드가 인스턴스의 상태를 조작해야 할 때는 `static`을 사용하지 않습니다.

---

## 4. 정적 블록 (Static Block)
정적 블록은 클래스가 로드될 때 한 번 실행되는 코드 블록으로, 정적 필드 초기화에 사용됩니다.

#### 예제: 정적 블록
```java
class StaticBlockExample {
    static int value;

    static {
        value = 42; // 클래스 로드 시 초기화
        System.out.println("정적 블록 실행");
    }
}

public class StaticBlockDemo {
    public static void main(String[] args) {
        System.out.println("Value: " + StaticBlockExample.value);
    }
}
```

---

## 5. 내부 클래스에서의 `static`
1. **정적 중첩 클래스 (Static Nested Class)**:
    - 외부 클래스의 인스턴스와 독립적으로 사용 가능.

#### 예제: 정적 중첩 클래스
```java
class OuterClass {
    static class StaticNestedClass {
        void display() {
            System.out.println("정적 중첩 클래스입니다.");
        }
    }
}

public class NestedClassDemo {
    public static void main(String[] args) {
        OuterClass.StaticNestedClass nested = new OuterClass.StaticNestedClass();
        nested.display(); // 출력: 정적 중첩 클래스입니다.
    }
}
```

2. **비정적 내부 클래스에서 `static` 사용 불가**:
    - 비정적 내부 클래스는 외부 클래스의 인스턴스에 종속되므로, `static` 멤버를 선언할 수 없습니다.

#### 잘못된 예제
```java
class OuterClass {
    class InnerClass {
        static int value; // 컴파일 에러: 정적 멤버 선언 불가
    }
}
```

---

## 결론
`static` 키워드는 **객체와 무관하게 동작해야 하는 필드 및 메서드**를 정의할 때 유용합니다. 하지만 객체별 고유 상태나 동작이 필요한 경우에는 사용하지 않는 것이 중요합니다. 이를 올바르게 활용하면 코드의 성능과 재사용성을 크게 향상시킬 수 있습니다.
