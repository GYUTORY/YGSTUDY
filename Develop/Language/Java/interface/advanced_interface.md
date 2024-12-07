
## 1. Default 메서드
Java 8부터 interface에 default 메서드를 정의할 수 있습니다. 이는 인터페이스에서도 구현부를 가진 메서드를 제공할 수 있음을 의미합니다.

### 목적
- 인터페이스를 구현한 기존 클래스와의 호환성을 유지하면서 새로운 메서드를 추가할 수 있음.
- 구현 클래스에서 선택적으로 메서드를 재정의할 수 있음.

### 예제
```java
interface Animal {
    void sound();

    // Default 메서드
    default void sleep() {
        System.out.println("This animal is sleeping.");
    }
}

class Dog implements Animal {
    @Override
    public void sound() {
        System.out.println("Bark!");
    }
}

public class Main {
    public static void main(String[] args) {
        Dog dog = new Dog();
        dog.sound(); // Bark!
        dog.sleep(); // This animal is sleeping.
    }
}
```

---

## 2. Static 메서드
Java 8부터 interface에 static 메서드도 정의할 수 있습니다. 이는 해당 인터페이스와 관련된 유틸리티 메서드를 제공하는 데 유용합니다.

### 예제
```java
interface MathOperations {
    static int add(int a, int b) {
        return a + b;
    }

    static int multiply(int a, int b) {
        return a * b;
    }
}

public class Main {
    public static void main(String[] args) {
        System.out.println(MathOperations.add(5, 3));       // 8
        System.out.println(MathOperations.multiply(5, 3)); // 15
    }
}
```
---

## 3. Private 메서드
Java 9부터 interface에 private 메서드를 정의할 수 있습니다. 이는 인터페이스 내부에서만 사용되는 헬퍼 메서드를 제공할 수 있게 합니다.

### 예제
```java
interface Logger {
    default void logInfo(String message) {
        log("INFO", message);
    }

    default void logError(String message) {
        log("ERROR", message);
    }

    // Private 메서드
    private void log(String level, String message) {
        System.out.println(level + ": " + message);
    }
}

class Application implements Logger {}

public class Main {
    public static void main(String[] args) {
        Application app = new Application();
        app.logInfo("Application started"); // INFO: Application started
        app.logError("An error occurred");  // ERROR: An error occurred
    }
}
```

---


## 4. 다중 인터페이스 구현과 충돌 해결
Java는 다중 인터페이스 구현을 지원하지만, 동일한 시그니처를 가진 default 메서드가 여러 인터페이스에 존재하면 충돌이 발생합니다. 이를 해결하려면 구현 클래스에서 명시적으로 오버라이드해야 합니다.

### 예제
```java
interface InterfaceA {
    default void show() {
        System.out.println("InterfaceA");
    }
}

interface InterfaceB {
    default void show() {
        System.out.println("InterfaceB");
    }
}

class MyClass implements InterfaceA, InterfaceB {
    @Override
    public void show() {
        // 명시적으로 선택하거나 새로운 구현 제공
        InterfaceA.super.show();
        InterfaceB.super.show();
        System.out.println("MyClass");
    }
}

public class Main {
    public static void main(String[] args) {
        MyClass obj = new MyClass();
        obj.show();
        // 출력:
        // InterfaceA
        // InterfaceB
        // MyClass
    }
}
```

## 5. 함수형 인터페이스와 람다 표현식
Java 8부터 함수형 인터페이스(Functional Interface)가 도입되었습니다. 함수형 인터페이스는 추상 메서드가 하나만 있는 인터페이스를 의미하며, 람다 표현식과 함께 사용됩니다.

### 예제
```java
@FunctionalInterface
interface Calculator {
    int calculate(int a, int b);
}

public class Main {
    public static void main(String[] args) {
        // 람다 표현식 사용
        Calculator add = (a, b) -> a + b;
        Calculator multiply = (a, b) -> a * b;

        System.out.println(add.calculate(5, 3));       // 8
        System.out.println(multiply.calculate(5, 3)); // 15
    }
}
```

## 6. Marker Interface (마커 인터페이스)
Marker Interface는 메서드가 없는 빈 인터페이스로, 특정 클래스에 특별한 속성을 부여하거나 식별하기 위해 사용됩니다.

### 예제
Java에서 대표적인 마커 인터페이스
- java.io.Serializable: 객체를 직렬화 가능하게 표시.
- java.lang.Cloneable: 객체를 복제 가능하게 표시.
사용 예:
```java
class Data implements java.io.Serializable {
    private String content;
    public Data(String content) {
        this.content = content;
    }
}
```

## 7. 인터페이스와 제네릭
인터페이스는 제네릭(Generic) 을 지원하여 다양한 데이터 타입을 다룰 수 있습니다.

### 예제
```java
interface Pair<K, V> {
    K getKey();
    V getValue();
}

class KeyValuePair<K, V> implements Pair<K, V> {
    private K key;
    private V value;

    KeyValuePair(K key, V value) {
        this.key = key;
        this.value = value;
    }

    @Override
    public K getKey() {
        return key;
    }

    @Override
    public V getValue() {
        return value;
    }
}

public class Main {
    public static void main(String[] args) {
        Pair<String, Integer> pair = new KeyValuePair<>("Age", 30);
        System.out.println(pair.getKey() + ": " + pair.getValue()); // Age: 30
    }
}
```

## 8. 인터페이스의 확장
interface는 다른 인터페이스를 상속받을 수 있습니다. 이를 통해 인터페이스의 기능을 확장할 수 있습니다.

### 예제
```java
interface Animal {
void sound();
}

interface Pet extends Animal {
    void play();
}

class Dog implements Pet {
    @Override
    public void sound() {
        System.out.println("Bark!");
    }

    @Override
    public void play() {
        System.out.println("Playing fetch!");
    }
}

public class Main {
    public static void main(String[] args) {
        Dog dog = new Dog();
        dog.sound(); // Bark!
        dog.play();  // Playing fetch!
    }
}
```

## 9. 인터페이스와 Dependency Injection
인터페이스는 의존성 주입(Dependency Injection) 을 통해 유연한 설계를 가능하게 합니다. 이는 구현체의 변경이 용이하고 테스트 코드 작성이 간편하다는 장점이 있습니다.

### 예제
```java
interface Service {
    void execute();
}

class EmailService implements Service {
    @Override
    public void execute() {
        System.out.println("Sending email...");
    }
}

class Notification {
    private Service service;

    Notification(Service service) {
        this.service = service;
    }

    void notifyUser() {
        service.execute();
    }
}

public class Main {
    public static void main(String[] args) {
        Service emailService = new EmailService();
        Notification notification = new Notification(emailService);
        notification.notifyUser(); // Sending email...
    }
}
```



