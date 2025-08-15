---
title: Java
tags: [language, java, 객체지향-프로그래밍-oop, interface, functionalinterface]
updated: 2025-08-10
---

## 1. 함수형 인터페이스란?

## 배경
**함수형 인터페이스**는 **하나의 추상 메서드만 가지는 인터페이스**를 의미합니다. Java 8부터 람다식을 통해 이러한 인터페이스를 구현할 수 있습니다.

- 추상 메서드가 **하나만 존재**해야 함.
- `@FunctionalInterface` 어노테이션으로 함수형 인터페이스임을 명시 가능 (선택 사항).
- Java의 기본 제공 함수형 인터페이스(`Runnable`, `Callable`, `Supplier` 등)도 많음.

```java
@FunctionalInterface
interface Process {
    void run(); // 단 하나의 추상 메서드
}
```

---

람다식은 **익명 함수(Anonymous Function)**의 간결한 표현으로, 함수형 인터페이스의 단일 추상 메서드를 구현하는 데 사용됩니다.

```java
(매개변수) -> { 구현부 }
```

1. **매개변수**: 함수의 입력값.
2. **화살표(->)**: 매개변수와 구현부를 구분.
3. **구현부**: 함수가 수행할 작업.

#### 예제
```java
() -> System.out.println("람다식 사용 예제");
```

위 코드는 매개변수가 없고, `System.out.println()`을 실행하는 람다식을 표현한 것입니다.

---

```java
() -> System.out.println("람다식 사용 예제");
```

위 코드는 매개변수가 없고, `System.out.println()`을 실행하는 람다식을 표현한 것입니다.

---

```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("익명 클래스 사용");
    }
});
```

```java
hello(() -> System.out.println("람다식 사용"));
```

람다식은 익명 클래스를 단순화한 표현으로 볼 수 있습니다.

람다식:
```java
() -> System.out.println("람다식 사용")
```

컴파일러가 변환:
```java
new Process() {
    @Override
    public void run() {
        System.out.println("람다식 사용");
    }
}
```

---

- 함수형 인터페이스를 구현하려면 추상 메서드를 반드시 재정의해야 함.
- 컴파일러가 람다식을 함수형 인터페이스의 단일 추상 메서드에 매핑.

#### 예제: 함수형 인터페이스와 람다식
```java
@FunctionalInterface
interface Process {
    void run();
}

public class LambdaExample {
    public static void main(String[] args) {
        Process process = () -> System.out.println("람다식 동작");
        process.run(); // 출력: 람다식 동작
    }
}
```

`Process` 인터페이스는 `run()`이라는 추상 메서드 하나를 가지고 있으므로, 컴파일러는 `()->{}` 코드 블록을 자동으로 `run()` 메서드의 구현으로 간주합니다.

---

```java
@FunctionalInterface
interface Process {
    void run();
}

public class LambdaExample {
    public static void main(String[] args) {
        Process process = () -> System.out.println("람다식 동작");
        process.run(); // 출력: 람다식 동작
    }
}
```

`Process` 인터페이스는 `run()`이라는 추상 메서드 하나를 가지고 있으므로, 컴파일러는 `()->{}` 코드 블록을 자동으로 `run()` 메서드의 구현으로 간주합니다.

---

#### 익명 클래스
```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("주사위 값 출력");
    }
});
```

#### 람다식
```java
hello(() -> System.out.println("주사위 값 출력"));
```

---

```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("주사위 값 출력");
    }
});
```

```java
hello(() -> System.out.println("주사위 값 출력"));
```

---

1. **`Runnable`**: 매개변수 없이 동작 수행.
2. **`Consumer<T>`**: 입력값을 소비하고 반환값 없음.
3. **`Supplier<T>`**: 값을 반환하지만 입력값 없음.
4. **`Function<T, R>`**: 입력값을 받아 변환 후 반환.

#### 예제: `Runnable` 사용
```java
Runnable runnable = () -> System.out.println("Runnable 동작");
runnable.run();
```

---


람다식과 함수형 인터페이스는 Java에서 함수형 프로그래밍 스타일을 도입하기 위한 중요한 도구입니다. 익명 클래스의 간결한 대안으로, 코드를 더욱 읽기 쉽고 유지보수 가능하게 만듭니다.

- **람다식**: 함수형 인터페이스의 단일 추상 메서드를 구현하는 축약 문법.
- **함수형 인터페이스**: 람다식의 기반이 되는 단일 추상 메서드를 가진 인터페이스.

이를 올바르게 이해하고 활용하면 Java 프로그래밍의 생산성을 크게 향상시킬 수 있습니다.






- Java의 람다식과 함수형 인터페이스는 코드의 간결성과 가독성을 높이는 데 중요한 역할을 합니다.
- 이 문서에서는 람다식이 동작하는 원리와 함수형 인터페이스의 개념을 자세히 설명하고, 예제를 통해 이를 이해할 수 있도록 합니다.

---

```java
() -> System.out.println("람다식 사용 예제");
```

위 코드는 매개변수가 없고, `System.out.println()`을 실행하는 람다식을 표현한 것입니다.

---

```java
() -> System.out.println("람다식 사용 예제");
```

위 코드는 매개변수가 없고, `System.out.println()`을 실행하는 람다식을 표현한 것입니다.

---

```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("익명 클래스 사용");
    }
});
```

```java
hello(() -> System.out.println("람다식 사용"));
```

람다식은 익명 클래스를 단순화한 표현으로 볼 수 있습니다.

람다식:
```java
() -> System.out.println("람다식 사용")
```

컴파일러가 변환:
```java
new Process() {
    @Override
    public void run() {
        System.out.println("람다식 사용");
    }
}
```

---

- 함수형 인터페이스를 구현하려면 추상 메서드를 반드시 재정의해야 함.
- 컴파일러가 람다식을 함수형 인터페이스의 단일 추상 메서드에 매핑.

```java
@FunctionalInterface
interface Process {
    void run();
}

public class LambdaExample {
    public static void main(String[] args) {
        Process process = () -> System.out.println("람다식 동작");
        process.run(); // 출력: 람다식 동작
    }
}
```

`Process` 인터페이스는 `run()`이라는 추상 메서드 하나를 가지고 있으므로, 컴파일러는 `()->{}` 코드 블록을 자동으로 `run()` 메서드의 구현으로 간주합니다.

---

```java
@FunctionalInterface
interface Process {
    void run();
}

public class LambdaExample {
    public static void main(String[] args) {
        Process process = () -> System.out.println("람다식 동작");
        process.run(); // 출력: 람다식 동작
    }
}
```

`Process` 인터페이스는 `run()`이라는 추상 메서드 하나를 가지고 있으므로, 컴파일러는 `()->{}` 코드 블록을 자동으로 `run()` 메서드의 구현으로 간주합니다.

---

```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("주사위 값 출력");
    }
});
```

```java
hello(() -> System.out.println("주사위 값 출력"));
```

---

```java
hello(new Process() {
    @Override
    public void run() {
        System.out.println("주사위 값 출력");
    }
});
```

```java
hello(() -> System.out.println("주사위 값 출력"));
```

---

1. **`Runnable`**: 매개변수 없이 동작 수행.
2. **`Consumer<T>`**: 입력값을 소비하고 반환값 없음.
3. **`Supplier<T>`**: 값을 반환하지만 입력값 없음.
4. **`Function<T, R>`**: 입력값을 받아 변환 후 반환.





# Java 람다식과 함수형 인터페이스

## 2. 람다식이란?

## 3. 람다식의 동작 원리

람다식은 **컴파일러가 함수형 인터페이스의 단일 추상 메서드를 구현한 익명 클래스의 인스턴스로 변환**합니다.

### 예제 1: 익명 클래스 vs 람다식

## 4. `@Override` 없이 동작하는 이유

람다식은 함수형 인터페이스의 **단일 추상 메서드(SAM: Single Abstract Method)**와 연결됩니다. 컴파일러는 이를 자동으로 구현하므로 `@Override`를 명시하지 않아도 됩니다.

## 5. 람다식의 장점

1. **간결성**:
    - 불필요한 익명 클래스 정의를 없애고, 코드를 단순화.
2. **가독성**:
    - 코드의 목적과 흐름이 명확하게 보임.
3. **표준화된 문법**:
    - Java에서 함수형 프로그래밍을 지원.

## 6. 람다식과 함수형 인터페이스의 실제 활용

### 예제 1: 주사위 값 출력
```java
import java.util.Random;

public class LambdaExample {
    public static void main(String[] args) {
        hello(() -> {
            int randomValue = new Random().nextInt(6) + 1;
            System.out.println("주사위 = " + randomValue);
        });
    }

    public static void hello(Process process) {
        process.run();
    }
}
```

출력 예:
```
주사위 = 4
```

### 예제 2: 반복 작업 수행
```java
hello(() -> {
    for (int i = 0; i < 3; i++) {
        System.out.println("i = " + i);
    }
});
```

출력 예:
```
i = 0
i = 1
i = 2
```

---

## 7. 함수형 인터페이스와 기본 제공 인터페이스

Java에서는 자주 사용하는 함수형 인터페이스를 기본 제공하고 있습니다.

## 8. 주의사항

1. **단일 추상 메서드만 허용**:
    - 함수형 인터페이스에는 반드시 하나의 추상 메서드만 존재해야 함.
2. **람다식에서 상태 관리**:
    - 람다식 내부에서 외부 변수를 수정하려면 `final` 또는 사실상 `final`이어야 함.

---

