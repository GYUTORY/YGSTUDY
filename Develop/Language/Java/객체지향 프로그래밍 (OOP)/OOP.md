
# Java - 객체지향 프로그래밍 (Object-Oriented Programming, OOP)

객체지향 프로그래밍(OOP)은 **객체(Object)**를 중심으로 프로그램을 설계하고 구현하는 프로그래밍 패러다임입니다. Java는 대표적인 객체지향 프로그래밍 언어로, OOP의 핵심 개념을 충실히 따릅니다.

## OOP의 핵심 개념

1. **클래스와 객체(Class and Object)**
2. **캡슐화(Encapsulation)**
3. **상속(Inheritance)**
4. **다형성(Polymorphism)**
5. **추상화(Abstraction)**

### 1. 클래스와 객체

- **클래스(Class)**: 객체를 정의하는 청사진(템플릿).
- **객체(Object)**: 클래스의 인스턴스.

```java
class Car {
    String brand;
    int speed;

    void drive() {
        System.out.println(brand + " is driving at " + speed + " km/h.");
    }
}

public class Main {
    public static void main(String[] args) {
        Car car = new Car(); // 객체 생성
        car.brand = "Toyota";
        car.speed = 120;
        car.drive();
    }
}
```

### 2. 캡슐화 (Encapsulation)

캡슐화는 데이터(필드)와 이를 처리하는 메서드를 하나로 묶는 것입니다. 필드는 `private`로 보호하고, 접근 메서드(getter/setter)를 통해 간접적으로 접근할 수 있도록 합니다.

```java
class BankAccount {
    private double balance;

    public double getBalance() {
        return balance;
    }

    public void deposit(double amount) {
        if (amount > 0) {
            balance += amount;
        }
    }
}

public class Main {
    public static void main(String[] args) {
        BankAccount account = new BankAccount();
        account.deposit(1000);
        System.out.println("Balance: " + account.getBalance());
    }
}
```

### 3. 상속 (Inheritance)

상속은 기존 클래스를 재사용하여 새로운 클래스를 정의하는 것입니다. `extends` 키워드를 사용합니다.

```java
class Animal {
    void eat() {
        System.out.println("This animal eats food.");
    }
}

class Dog extends Animal {
    void bark() {
        System.out.println("Dog barks.");
    }
}

public class Main {
    public static void main(String[] args) {
        Dog dog = new Dog();
        dog.eat();  // 부모 클래스 메서드
        dog.bark(); // 자식 클래스 메서드
    }
}
```

### 4. 다형성 (Polymorphism)

다형성은 동일한 메서드 이름이 다양한 형태로 동작할 수 있도록 하는 것입니다. 오버로딩과 오버라이딩으로 구현할 수 있습니다.

#### 오버로딩 (Overloading)
```java
class Calculator {
    int add(int a, int b) {
        return a + b;
    }

    double add(double a, double b) {
        return a + b;
    }
}

public class Main {
    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println(calc.add(5, 10));       // int 메서드 호출
        System.out.println(calc.add(5.5, 10.5));  // double 메서드 호출
    }
}
```

#### 오버라이딩 (Overriding)
```java
class Animal {
    void sound() {
        System.out.println("Some generic animal sound.");
    }
}

class Cat extends Animal {
    @Override
    void sound() {
        System.out.println("Meow!");
    }
}

public class Main {
    public static void main(String[] args) {
        Animal animal = new Cat(); // 업캐스팅
        animal.sound(); // "Meow!" 출력
    }
}
```

### 5. 추상화 (Abstraction)

추상화는 불필요한 세부사항을 숨기고, 핵심 기능만 노출하는 것입니다. Java에서는 추상 클래스와 인터페이스를 통해 구현할 수 있습니다.

#### 추상 클래스
```java
abstract class Shape {
    abstract void draw();
}

class Circle extends Shape {
    @Override
    void draw() {
        System.out.println("Drawing a circle.");
    }
}

public class Main {
    public static void main(String[] args) {
        Shape shape = new Circle();
        shape.draw();
    }
}
```

#### 인터페이스
```java
interface Flyable {
    void fly();
}

class Airplane implements Flyable {
    @Override
    public void fly() {
        System.out.println("Airplane is flying.");
    }
}

public class Main {
    public static void main(String[] args) {
        Flyable airplane = new Airplane();
        airplane.fly();
    }
}
```

## OOP의 장점

1. **코드 재사용성**: 상속과 클래스 구조를 통해 코드 중복 감소.
2. **유지보수 용이**: 모듈화된 구조로 변경과 확장이 간편.
3. **데이터 은닉**: 캡슐화를 통해 데이터 보호.
4. **유연성과 확장성**: 다형성과 추상화를 통해 프로그램의 확장성을 높임.

## OOP의 단점

1. **복잡성 증가**: 작은 프로젝트에서는 구조가 복잡해질 수 있음.
2. **처리 속도**: 절차지향 프로그래밍에 비해 실행 속도가 느릴 수 있음.

## 결론

Java의 객체지향 프로그래밍은 코드의 재사용성과 유지보수성을 높이는 강력한 패러다임입니다. 클래스, 캡슐화, 상속, 다형성, 추상화 등의 개념을 잘 이해하고 활용하면 더 나은 품질의 소프트웨어를 개발할 수 있습니다.
