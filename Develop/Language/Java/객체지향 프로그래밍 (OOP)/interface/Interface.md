---
title: Java Interface
tags: [language, java, 객체지향-프로그래밍-oop, interface]
updated: 2025-08-10
---
# Java Interface에 대한 자세한 설명

## 1. Interface란 무엇인가?
`Interface`는 Java에서 **다중 상속 문제를 해결하고, 코드의 일관성과 유지보수를 돕기 위한** 일종의 계약(Contract)입니다. `Interface`는 클래스와 비슷하지만, **구현(Implementation)** 없이 메서드의 시그니처(Signature)만 정의합니다.

## 배경
- **추상 메서드**와 **상수**만 포함할 수 있습니다. (Java 8 이상부터는 `default` 메서드와 `static` 메서드도 포함 가능)
- `implements` 키워드를 사용하여 클래스에서 인터페이스를 구현합니다.
- **다중 구현**이 가능합니다.
- 객체를 생성할 수 없습니다. (즉, 직접 인스턴스화 불가)










## 2. Interface의 구성 요소

### 2.1 추상 메서드
- Interface의 메서드는 기본적으로 **public**과 **abstract**입니다.
```java
public interface Animal {
    void sound(); // 추상 메서드
}
```

### 2.2 상수
- Interface 내에 선언된 변수는 public static final이 생략된 상태로 항상 상수로 동작합니다.

```java
public interface Animal {
    String TYPE = "Mammal"; // 상수
}
```

### 2.3 Default 메서드 (Java 8 이상)
- 구현부를 가지는 메서드를 Interface에 정의할 수 있습니다.

```java
public interface Animal {
    default void eat() {
        System.out.println("This animal eats food.");
    }
}
```

### 2.4 Static 메서드 (Java 8 이상)
- 클래스처럼 정적 메서드도 Interface에 정의 가능합니다.

```java
public interface Animal {
    static void info() {
        System.out.println("This is an Animal interface.");
    }
}
```

### 2.5 Private 메서드 (Java 9 이상)
- Private 접근 제어자를 가진 메서드로, 내부적으로만 사용됩니다.

```java
public interface Animal {
    private void helper() {
        System.out.println("This is a helper method.");
    }
}
```

## 3. Interface 구현
### 3.1 단일 인터페이스 구현
- 클래스는 implements 키워드를 사용하여 인터페이스를 구현합니다.

```java
public interface Animal {
    void sound();
}

public class Dog implements Animal {
    @Override
    public void sound() {
        System.out.println("Bark!");
    }
}
```

### 3.2 다중 인터페이스 구현
- Java는 다중 상속을 지원하지 않지만, 다중 인터페이스 구현은 가능합니다.

```java
public interface Animal {
    void sound();
}

public interface Pet {
    void play();
}

public class Dog implements Animal, Pet {
    @Override
    public void sound() {
        System.out.println("Bark!");
    }

    @Override
    public void play() {
        System.out.println("Playing fetch!");
    }
}
```

## 4. Interface의 활용
### 4.1 다형성(Polymorphism)
- Interface는 다형성을 제공하여, 다양한 구현체를 같은 방식으로 처리할 수 있게 합니다.

```java
public class Main {
    public static void main(String[] args) {
        Animal myDog = new Dog();
        myDog.sound(); // Bark!
    }
}
```

### 4.2 표준화된 설계
- Interface는 기능을 표준화하여 여러 클래스가 동일한 메서드를 구현하도록 강제합니다.

### 4.3 Dependency Injection
- Interface를 사용하면 의존성 주입을 통해 유연하고 확장 가능한 설계를 할 수 있습니다.

## 5. Interface와 Abstract Class 비교
| **특징**           | **Interface**                         | **Abstract Class**               |
|--------------------|---------------------------------------|-----------------------------------|
| **키워드**         | `interface`                          | `abstract class`                 |
| **다중 구현**      | 가능                                  | 불가능 (단일 상속만 가능)          |
| **메서드 구현 여부**| Java 8 이상: `default`/`static` 메서드 | 구현된 메서드 포함 가능             |
| **변수**           | `public static final` (상수만 가능)   | 모든 종류의 변수 선언 가능          |
| **생성자**         | 불가능                                | 가능                              |



## 6. Interface 사용 시 주의점
### 6.1 복잡도 증가
- 너무 많은 인터페이스를 사용하면 유지보수가 어려워질 수 있습니다.
### 6.2 기능의 명확성
- 인터페이스는 "무엇을 해야 하는가"에 초점을 맞추고, "어떻게"는 구현 클래스에 위임해야 합니다.
### 6.3 Default 메서드 남용 금지
- Default 메서드는 편리하지만, 설계 철학을 흐릴 수 있습니다.

--- 

## 7. 결론
- Interface는 객체 지향 프로그래밍에서 계약 역할을 하며, 코드의 유연성과 재사용성을 높입니다. 
- 올바르게 사용하면 유지보수와 확장성 측면에서 큰 이점을 제공합니다.

