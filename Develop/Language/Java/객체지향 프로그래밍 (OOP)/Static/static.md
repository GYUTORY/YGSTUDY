---
title: static
tags: [language, java, 객체지향-프로그래밍-oop, static]
updated: 2025-08-10
---
## 1. `static` 키워드란? 🧐

`static` 키워드는 **클래스 레벨에서 선언된 변수 및 메서드를 의미**합니다.  
즉, 인스턴스(객체) 없이도 **클래스명으로 접근**할 수 있으며, 모든 인스턴스가 동일한 메모리 공간을 공유합니다.

> **📌 `static` 키워드를 사용할 경우**
> - 개별 객체가 아닌 **클래스 자체에 속하는 변수 및 메서드**가 된다.
> - **인스턴스 없이 클래스명으로 직접 접근 가능**하다.
> - **객체마다 개별적으로 존재하지 않고, 하나의 공유 메모리 공간을 사용**한다.

---

## 2. 멤버 변수(필드)의 종류와 특징

### 2.1 인스턴스 변수 (Instance Variable)
✔ 객체(인스턴스)가 생성될 때마다 메모리에 **새로운 공간이 할당**되는 변수입니다.  
✔ **각 인스턴스마다 독립적으로 존재**하여 서로 다른 값을 가질 수 있습니다.  
✔ 반드시 **객체를 생성한 후 사용**해야 합니다.  
✔ `static` 키워드를 사용하지 않습니다.

## 배경
```java
class Person {
    String name; // 인스턴스 변수
    int age;     // 인스턴스 변수

    // 생성자
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    // 인스턴스 메서드
    public void introduce() {
        System.out.println("안녕하세요! 저는 " + name + "이고, 나이는 " + age + "살입니다.");
    }
}

public class InstanceVariableExample {
    public static void main(String[] args) {
        Person p1 = new Person("홍길동", 25);
        Person p2 = new Person("이순신", 30);

        p1.introduce(); // 홍길동: 25
        p2.introduce(); // 이순신: 30
    }
}
```
> **📝 인스턴스 변수는 객체마다 다르게 저장됨!**
> - `p1`과 `p2`는 각기 다른 `name`과 `age` 값을 가짐
> - 객체를 생성해야지만 해당 변수를 사용할 수 있음

---

```java
class Counter {
    static int count = 0; // 정적 변수 (클래스 변수)

    public Counter() {
        count++; // 객체가 생성될 때마다 count 증가
    }

    public static void showCount() {
        System.out.println("현재 객체 수: " + count);
    }
}

public class StaticVariableExample {
    public static void main(String[] args) {
        Counter c1 = new Counter();
        Counter c2 = new Counter();
        Counter c3 = new Counter();

        // static 변수는 모든 객체가 공유하므로, 3이 출력됨
        Counter.showCount(); // 현재 객체 수: 3
    }
}
```
> **✨ `count` 변수는 `static`으로 선언되어 모든 객체가 공유!**
> - 객체가 생성될 때마다 `count` 값이 증가하지만, 각 객체가 개별적으로 값을 가지지 않음
> - `Counter.showCount();`와 같이 **클래스명으로 직접 접근 가능**

---

```java
class Car {
    String model;

    public Car(String model) {
        this.model = model;
    }

    public void drive() { // 인스턴스 메서드
        System.out.println(model + "가 주행 중입니다!");
    }
}

public class InstanceMethodExample {
    public static void main(String[] args) {
        Car car1 = new Car("Tesla");
        Car car2 = new Car("BMW");

        car1.drive(); // Tesla가 주행 중입니다!
        car2.drive(); // BMW가 주행 중입니다!
    }
}
```
> **📌 인스턴스 메서드는 반드시 객체를 생성한 후 사용해야 함!**
> - `car1.drive();` → Tesla 객체의 `drive()` 실행
> - `car2.drive();` → BMW 객체의 `drive()` 실행

---

```java
class MathUtil {
    public static int add(int a, int b) { // 정적 메서드
        return a + b;
    }
}

public class StaticMethodExample {
    public static void main(String[] args) {
        int sum = MathUtil.add(5, 10); // 클래스명으로 직접 호출 가능
        System.out.println("합계: " + sum);
    }
}
```
> **📝 `static` 메서드는 객체 없이 바로 호출 가능!**
> - `MathUtil.add(5, 10);` 처럼 사용 가능
> - 인스턴스 변수는 사용할 수 없음

---

- **`static` 변수** → 모든 객체가 공유하는 **클래스 변수**
- **인스턴스 변수** → 객체마다 개별적으로 존재
- **`static` 메서드** → 객체 없이 호출 가능
- **인스턴스 메서드** → 반드시 객체를 생성한 후 호출 가능

> **👉🏻 `static`은 객체 생성 없이 사용할 수 있지만, 무분별한 사용은 피해야 함!**






자바(Java)에서 `static` 키워드는 클래스 레벨에서 변수를 선언하거나 메서드를 정의할 때 사용됩니다.  
이 문서에서는 `static` 키워드의 역할과 인스턴스 멤버(변수/메서드)와의 차이점을 예제와 함께 설명합니다.

### 2.2 정적 변수 (Static Variable)
✔ **클래스에 하나만 존재하며, 모든 객체가 공유**합니다.  
✔ **클래스가 로드될 때 메모리에 한 번만 할당**됩니다.  
✔ **객체 생성 없이 `클래스명.변수명`으로 접근 가능**합니다.  
✔ `static` 키워드를 사용하여 선언합니다.





# 자바의 `static` 키워드와 멤버 변수/메서드의 종류 및 특성

## 3. 멤버 메서드의 종류와 특징

### 3.1 인스턴스 메서드 (Instance Method)
✔ **객체가 생성된 후에만 호출 가능**합니다.  
✔ 주로 **객체의 상태(인스턴스 변수)를 변경하거나 사용하는 용도**로 사용됩니다.  
✔ `static` 키워드를 사용하지 않습니다.

### 3.2 정적 메서드 (Static Method)
✔ **객체 생성 없이 호출 가능** (`클래스명.메서드명()`)  
✔ **인스턴스 변수 사용 불가** (객체 없이 실행되기 때문)  
✔ **공통적인 기능을 제공할 때 유용**  
✔ `static` 키워드를 사용하여 선언합니다.

## 4. `static`을 사용할 때 주의할 점 ⚠

✔ **인스턴스 변수는 `static` 메서드에서 직접 접근할 수 없음**  
✔ **메모리 사용을 고려하여 불필요한 `static` 사용을 지양**  
✔ **공통적인 데이터(설정값, 카운트 등)에만 사용**

---

