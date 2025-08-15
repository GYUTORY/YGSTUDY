---
title: Abstract Class Interface
tags: [language, java, 객체지향-프로그래밍-oop, interface, abstract-class-vs-interface]
updated: 2025-08-10
---
## 1. Abstract Class와 Interface란?
### Abstract Class
`Abstract Class`는 **공통된 기능을 정의하고 이를 확장하는** 데 사용되는 클래스입니다. 하나 이상의 **추상 메서드**(구현되지 않은 메서드)를 포함할 수 있으며, 구현된 메서드도 포함할 수 있습니다.

### Interface
`Interface`는 **클래스가 반드시 구현해야 하는 메서드의 청사진(Contract)** 을 정의하는 데 사용됩니다. 다중 상속이 불가능한 Java에서 **다중 구현**을 가능하게 하는 수단입니다.

---

## 2. Abstract Class와 Interface의 비교

| **특징**                     | **Abstract Class**                      | **Interface**                           |
|------------------------------|------------------------------------------|------------------------------------------|
| **키워드**                   | `abstract class`                        | `interface`                              |
| **다중 구현**                | 불가능 (단일 상속만 가능)                 | 가능                                     |
| **메서드 구현 여부**          | 구현된 메서드와 추상 메서드 포함 가능      | Java 8 이상: `default`/`static` 메서드 포함 가능 |
| **변수**                     | 모든 종류의 변수 선언 가능                | `public static final` (상수만 가능)       |
| **생성자**                   | 생성자 선언 가능                         | 생성자 선언 불가능                        |
| **목적**                     | 공통된 기능 제공 및 코드 재사용성 증대     | 클래스가 반드시 따라야 하는 계약 정의      |
| **접근 제한자**              | 메서드와 변수에 모든 접근 제한자 사용 가능 | 모든 메서드는 기본적으로 `public`          |
| **속도**                     | 클래스의 일부로 간주되어 실행 속도가 더 빠름| 인터페이스는 구현된 클래스의 레벨에서 동작 |
| **호환성**                   | 클래스와만 상속 관계를 맺을 수 있음         | 클래스를 포함하여 다른 인터페이스와도 연동 |

---

## 3. Abstract Class와 Interface의 예제

### Abstract Class 예제
```java
abstract class Animal {
    String name;

    Animal(String name) {
        this.name = name;
    }

    abstract void sound();

    void eat() {
        System.out.println(name + " is eating.");
    }
}

class Dog extends Animal {
    Dog(String name) {
        super(name);
    }

    @Override
    void sound() {
        System.out.println("Bark!");
    }
}
```

### Interface 예제
```java
interface Animal {
    void sound();
    void eat();
}

class Dog implements Animal {
    @Override
    public void sound() {
        System.out.println("Bark!");
    }

    @Override
    public void eat() {
        System.out.println("Dog is eating.");
    }
}
```

---

## 4. 언제 Abstract Class를 사용할까?
- 클래스 간의 강한 연관성이 있을 때 (예: Animal → Dog, Cat).
- 공통된 속성과 메서드의 재사용이 필요할 때.
- 일부 메서드만 추상화하고, 나머지는 구현이 필요할 때.

### Abstract Class 사용 사례
```java
abstract class Shape {
int x, y;

    Shape(int x, int y) {
        this.x = x;
        this.y = y;
    }

    abstract void draw();
    void move(int newX, int newY) {
        x = newX;
        y = newY;
    }
}
```

---

## 5. 언제 Interface를 사용할까?
- 다중 구현이 필요할 때.
- 서로 다른 클래스들이 공통된 동작을 공유해야 할 때.
- 설계의 유연성과 테스트 용이성을 높이고 싶을 때.

### Interface 사용 사례
```java
interface Flyable {
    void fly();
}

interface Swimmable {
    void swim();
}

class Bird implements Flyable, Swimmable {
    @Override
    public void fly() {
        System.out.println("Bird is flying.");
    }

    @Override
    public void swim() {
        System.out.println("Bird is swimming.");
    }
}
```

---

## 6. Abstract Class와 Interface를 함께 사용하는 사례
- 두 개념을 함께 사용하여 더욱 강력한 설계를 할 수 있습니다.

```java
abstract class Vehicle {
    String brand;

    Vehicle(String brand) {
        this.brand = brand;
    }

    abstract void drive();
}

interface Electric {
    void chargeBattery();
}

class Tesla extends Vehicle implements Electric {
    Tesla(String brand) {
        super(brand);
    }

    @Override
    void drive() {
        System.out.println(brand + " is driving silently.");
    }

    @Override
    public void chargeBattery() {
        System.out.println(brand + " is charging its battery.");
    }
}
```

---

## 7. 결론
Abstract Class와 Interface는 각각의 장단점이 있으며, 상황에 따라 적절히 선택해야 합니다.
- Abstract Class는 공통된 속성과 메서드를 공유할 때 유용합니다.
- Interface는 다중 구현이 필요한 경우와 코드의 유연성을 높이고자 할 때 유용합니다.
- 효율적인 설계를 위해 두 개념을 함께 사용하는 것도 고려해볼 수 있습니다.









## 배경





Java의 `Abstract Class`와 `Interface`는 둘 다 추상화를 제공하여 객체 지향 프로그래밍의 중요한 요소를 구성합니다. 하지만 두 개념은 서로 다른 목적과 사용 사례를 가지고 있습니다.





# Abstract Class와 Interface의 차이점

