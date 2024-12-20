
# Java Class 개념과 활용 
- Java에서 클래스는 객체 지향 프로그래밍(OOP)의 핵심 구성 요소입니다. 이 문서에서는 Java 클래스의 주요 개념과 중급 이상의 활용법을 예제와 함께 설명합니다.

---

## 1. 클래스(Class)란?
클래스는 객체를 정의하는 설계도입니다. 클래스는 **속성(필드)**과 **동작(메서드)**을 포함하여 객체의 상태와 행동을 정의합니다.

### 클래스의 기본 구조
```java
public class Example {
    // 필드
    private String name;
    private int age;

    // 생성자
    public Example(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // 메서드
    public void displayInfo() {
        System.out.println("이름: " + name + ", 나이: " + age);
    }
}
```

---

## 2. 접근 제어자(Access Modifiers)
Java 클래스의 필드와 메서드에 접근을 제어하여 캡슐화를 구현합니다.

- **public**: 어디서나 접근 가능
- **private**: 클래스 내부에서만 접근 가능
- **protected**: 같은 패키지와 하위 클래스에서 접근 가능
- **default(생략)**: 같은 패키지에서만 접근 가능

### 예제: 접근 제어자 활용
```java
public class AccessExample {
    private String secret = "비밀";
    public String name = "공개";

    public String getSecret() {
        return secret; // private 필드에 접근
    }
}
```

---

## 3. 상속(Inheritance)
Java는 **`extends` 키워드**를 사용해 클래스를 상속합니다. 상속을 통해 코드 재사용성과 확장성을 높일 수 있습니다.

### 예제: 상속
```java
// 부모 클래스
class Animal {
    public void sound() {
        System.out.println("동물이 소리를 냅니다.");
    }
}

// 자식 클래스
class Dog extends Animal {
    @Override
    public void sound() {
        System.out.println("멍멍!");
    }
}

public class InheritanceExample {
    public static void main(String[] args) {
        Animal myDog = new Dog();
        myDog.sound(); // 출력: 멍멍!
    }
}
```

---

## 4. 추상 클래스(Abstract Class)
추상 클래스는 공통적인 속성과 동작을 정의하면서, 일부 메서드는 하위 클래스에서 구현하도록 강제합니다.

### 예제: 추상 클래스
```java
abstract class Shape {
    abstract void draw(); // 추상 메서드

    public void display() {
        System.out.println("이것은 도형입니다.");
    }
}

class Circle extends Shape {
    @Override
    void draw() {
        System.out.println("원을 그립니다.");
    }
}

public class AbstractExample {
    public static void main(String[] args) {
        Shape shape = new Circle();
        shape.display(); // 출력: 이것은 도형입니다.
        shape.draw();    // 출력: 원을 그립니다.
    }
}
```

---

## 5. 인터페이스(Interface)
인터페이스는 클래스가 구현해야 하는 메서드의 집합을 정의합니다. **`implements` 키워드**를 사용하여 구현합니다.

### 예제: 인터페이스
```java
interface Vehicle {
    void start();
    void stop();
}

class Car implements Vehicle {
    @Override
    public void start() {
        System.out.println("자동차가 출발합니다.");
    }

    @Override
    public void stop() {
        System.out.println("자동차가 멈춥니다.");
    }
}

public class InterfaceExample {
    public static void main(String[] args) {
        Vehicle myCar = new Car();
        myCar.start(); // 출력: 자동차가 출발합니다.
        myCar.stop();  // 출력: 자동차가 멈춥니다.
    }
}
```

---

## 6. 내부 클래스(Inner Class)
클래스 내부에 선언된 클래스를 **내부 클래스**라고 합니다.

### 예제: 내부 클래스
```java
class OuterClass {
    private String message = "Hello, Inner Class!";

    class InnerClass {
        public void printMessage() {
            System.out.println(message);
        }
    }
}

public class InnerClassExample {
    public static void main(String[] args) {
        OuterClass outer = new OuterClass();
        OuterClass.InnerClass inner = outer.new InnerClass();
        inner.printMessage(); // 출력: Hello, Inner Class!
    }
}
```

---

## 7. 익명 클래스(Anonymous Class)
익명 클래스는 이름이 없는 클래스로, 주로 인터페이스나 추상 클래스를 구현할 때 사용됩니다.

### 예제: 익명 클래스
```java
interface Greeting {
    void sayHello();
}

public class AnonymousClassExample {
    public static void main(String[] args) {
        Greeting greeting = new Greeting() {
            @Override
            public void sayHello() {
                System.out.println("안녕하세요!");
            }
        };
        greeting.sayHello(); // 출력: 안녕하세요!
    }
}
```

---

## 8. 정적 멤버와 클래스(Static Members and Class)
**`static` 키워드**를 사용해 정적 필드, 메서드, 또는 중첩 클래스를 선언할 수 있습니다.

### 예제: 정적 멤버와 클래스
```java
class StaticExample {
    static int counter = 0;

    public static void incrementCounter() {
        counter++;
    }
}

public class StaticClassExample {
    public static void main(String[] args) {
        StaticExample.incrementCounter();
        StaticExample.incrementCounter();
        System.out.println("카운터 값: " + StaticExample.counter); // 출력: 카운터 값: 2
    }
}
```

---

## 9. 제네릭 클래스(Generic Class)
제네릭은 클래스와 메서드에서 타입을 매개변수화하여 코드의 재사용성을 높입니다.

### 예제: 제네릭 클래스
```java
class GenericBox<T> {
    private T item;

    public void setItem(T item) {
        this.item = item;
    }

    public T getItem() {
        return item;
    }
}

public class GenericExample {
    public static void main(String[] args) {
        GenericBox<String> box = new GenericBox<>();
        box.setItem("안녕하세요!");
        System.out.println(box.getItem()); // 출력: 안녕하세요!
    }
}
```

---

## 결론
Java 클래스는 단순한 객체 생성의 도구를 넘어, 코드의 재사용성과 구조화를 가능하게 하는 강력한 도구입니다. 클래스의 다양한 활용법(상속, 추상 클래스, 인터페이스, 제네릭 등)을 익히고, 적절히 설계하는 연습을 통해 더 나은 코드를 작성할 수 있습니다.
