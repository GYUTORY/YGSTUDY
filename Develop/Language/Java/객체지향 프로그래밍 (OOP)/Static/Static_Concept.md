---
title: Java static
tags: [language, java, 객체지향-프로그래밍-oop, static, staticconcept]
updated: 2025-08-10
---
# Java `static` 키워드의 개념과 활용 🚀

## 1. `static` 키워드란? 🤔

Java에서 `static` 키워드는 **클래스 레벨에서 선언된 변수 및 메서드**를 의미합니다.  
즉, 객체(인스턴스)와 관계없이 **클래스 자체에 속하는 멤버**를 만들 때 사용됩니다.

> **✨ `static` 키워드의 주요 특징**
> - **객체 생성 없이 `클래스명.변수명` 또는 `클래스명.메서드명`으로 접근 가능**
> - **모든 인스턴스가 하나의 정적 변수(static variable)를 공유**
> - **메모리에 한 번만 할당되며, 프로그램 종료 시까지 유지**
> - **인스턴스 변수(객체 변수)를 직접 참조할 수 없음**

---

## 2. `static` 키워드의 활용 예제

### 2.1 정적 변수 (Static Variable)

✔ 클래스가 로드될 때 한 번만 메모리에 할당되며, 모든 객체가 공유함  
✔ **객체를 생성하지 않고도 사용할 수 있음**  
✔ **객체마다 개별적인 값을 가지지 않고, 동일한 값 유지**

## 배경
```java
class Counter {
    static int count = 0; // 정적 변수 (클래스 변수)

    public Counter() {
        count++; // 객체가 생성될 때마다 count 증가
    }
}

public class StaticVariableExample {
    public static void main(String[] args) {
        Counter c1 = new Counter();
        Counter c2 = new Counter();
        Counter c3 = new Counter();

        System.out.println("현재 객체 수: " + Counter.count); // 3
    }
}
```
> **📌 모든 객체가 `count` 값을 공유!**
> - `Counter.count`는 객체를 생성하지 않아도 접근 가능

---

```java
class MathUtil {
    public static int add(int a, int b) {
        return a + b;
    }
}

public class StaticMethodExample {
    public static void main(String[] args) {
        int sum = MathUtil.add(5, 10); // 객체 없이 사용 가능
        System.out.println("합계: " + sum);
    }
}
```
> **📝 `static` 메서드는 인스턴스 생성 없이 호출 가능!**

---

```java
class Config {
    static String appName;

    // 정적 블록: 클래스가 로드될 때 실행됨
    static {
        appName = "My Application";
        System.out.println("정적 블록 실행: " + appName);
    }
}

public class StaticBlockExample {
    public static void main(String[] args) {
        System.out.println("앱 이름: " + Config.appName);
    }
}
```
> **👉🏻 `static` 블록은 한 번만 실행되며, 정적 변수 초기화에 유용!**

---

```java
class Outer {
    static class Inner {
        void display() {
            System.out.println("정적 내부 클래스 실행!");
        }
    }
}

public class StaticInnerClassExample {
    public static void main(String[] args) {
        Outer.Inner obj = new Outer.Inner(); // 외부 클래스의 인스턴스 없이 사용 가능
        obj.display();
    }
}
```
> **✨ 정적 내부 클래스는 `Outer.Inner` 형태로 바로 생성 가능!**

---

- **`static` 변수** → 모든 객체가 공유하는 **클래스 변수**
- **`static` 메서드** → 객체 없이 호출 가능
- **`static` 블록** → 클래스 로드 시 한 번만 실행됨
- **`static` 내부 클래스** → 외부 클래스 인스턴스 없이 사용 가능

> **👉🏻 `static` 키워드는 객체 독립적인 데이터와 기능을 다룰 때 사용해야 함!**






### 2.2 정적 메서드 (Static Method)

✔ **객체 생성 없이 호출 가능** (`클래스명.메서드명()`)  
✔ 인스턴스 변수(객체 변수) 사용 불가  
✔ **공통적인 기능을 제공하는 유틸리티 메서드** 등에 주로 사용됨

### 2.3 정적 블록 (Static Block)

✔ **클래스가 처음 로드될 때 단 한 번 실행**됨  
✔ **복잡한 초기화 로직을 수행할 때 유용**

### 2.4 정적 내부 클래스 (Static Inner Class)

✔ **외부 클래스의 인스턴스 없이도 내부 클래스 사용 가능**  
✔ **주로 유틸리티 클래스 또는 특정 기능을 캡슐화할 때 사용**





## 3. `static` 키워드를 사용할 때 주의할 점 ⚠️

✔ **인스턴스 변수(객체 변수)는 `static` 메서드에서 직접 사용할 수 없음**  
✔ **메모리 사용을 고려하여 불필요한 `static` 사용을 피할 것**  
✔ **공통적인 데이터(설정값, 카운트 등)에만 사용**

---

