---
title: Java Generics
tags: [language, java, 자바-디자인-패턴-및-원칙, generics]
updated: 2025-08-10
---

# Java 제네릭 (Generics)

## 배경
1. **타입 안전성**: 컬렉션이나 메서드에서 잘못된 타입의 객체 사용을 방지.
2. **코드 재사용성**: 데이터 타입에 상관없이 동일한 코드를 재사용 가능.
3. **타입 캐스팅 제거**: 명시적 타입 캐스팅을 줄여 코드 가독성을 향상.

---

```java
class 클래스명<T> {
    private T data;

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}
```

```java
class Box<T> {
    private T value;

    public void set(T value) {
        this.value = value;
    }

    public T get() {
        return value;
    }
}

public class Main {
    public static void main(String[] args) {
        Box<Integer> intBox = new Box<>();
        intBox.set(123);
        System.out.println("정수 값: " + intBox.get());

        Box<String> strBox = new Box<>();
        strBox.set("안녕하세요, 제네릭!");
        System.out.println("문자열 값: " + strBox.get());
    }
}
```

```
정수 값: 123
문자열 값: 안녕하세요, 제네릭!
```

---

```java
class Utility {
    public static <T> void printArray(T[] array) {
        for (T element : array) {
            System.out.print(element + " ");
        }
        System.out.println();
    }
}
```

```java
public class Main {
    public static void main(String[] args) {
        Integer[] intArray = {1, 2, 3};
        String[] strArray = {"A", "B", "C"};

        Utility.printArray(intArray);
        Utility.printArray(strArray);
    }
}
```

```
1 2 3 
A B C
```

---

```java
import java.util.Arrays;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        List<Integer> intList = Arrays.asList(1, 2, 3);
        List<Double> doubleList = Arrays.asList(1.1, 2.2, 3.3);
        List<Object> objList = Arrays.asList("A", "B", "C");

        System.out.println("제한 없는 와일드카드:");
        printList(intList);

        System.out.println("상한 경계 와일드카드:");
        processNumbers(doubleList);

        System.out.println("하한 경계 와일드카드:");
        addToList(objList);
    }

    public static void printList(List<?> list) {
        for (Object obj : list) {
            System.out.print(obj + " ");
        }
        System.out.println();
    }

    public static void processNumbers(List<? extends Number> list) {
        for (Number num : list) {
            System.out.println(num);
        }
    }

    public static void addToList(List<? super Integer> list) {
        list.add(42);
    }
}
```

```
제한 없는 와일드카드:
1 2 3 
상한 경계 와일드카드:
1.1
2.2
3.3
하한 경계 와일드카드:
42
```

---

- Java 제네릭은 코드 유연성과 타입 안전성을 동시에 제공.
- 제네릭 클래스, 메서드, 와일드카드(`?`, `? extends`, `? super`)를 이해하면 더욱 견고한 Java 애플리케이션을 작성 가능.

---

제네릭을 활용하면 더 안전하고 효율적인 코드를 작성할 수 있습니다!






Java의 제네릭은 클래스, 인터페이스, 메서드가 다양한 데이터 타입에서 작동하도록 하며, **컴파일 시 타입 안정성**을 제공합니다.

---





## **1. 제네릭 클래스**
제네릭 클래스는 클래스 정의 시 타입 매개변수를 사용하여 다양한 데이터 타입을 처리할 수 있습니다.

## **2. 제네릭 메서드**
제네릭 메서드는 클래스의 타입 매개변수와 독립적으로 동작하는 메서드를 정의합니다.

## **3. 제네릭 와일드카드**
와일드카드는 `?`로 표현되며, 보다 유연한 코드를 작성하는 데 사용됩니다.

### **3.1 제한 없는 와일드카드 (`?`)**
- 특정 타입에 구애받지 않을 때 사용.

```java
public static void printList(List<?> list) {
    for (Object obj : list) {
        System.out.print(obj + " ");
    }
}
```

### **3.2 상한 경계 와일드카드 (`? extends Type`)**
- 특정 타입의 하위 클래스만 허용.

```java
public static void processNumbers(List<? extends Number> list) {
    for (Number num : list) {
        System.out.println(num);
    }
}
```

### **3.3 하한 경계 와일드카드 (`? super Type`)**
- 특정 타입의 상위 클래스만 허용.

```java
public static void addToList(List<? super Integer> list) {
    list.add(42); // Integer 타입 추가 가능
}
```

## **4. 제네릭의 장점**
1. **컴파일 시 타입 검사**: 컴파일 시점에서 타입 불일치를 탐지.
2. **타입 캐스팅 제거**: 명시적 타입 캐스팅을 제거하여 코드 간결화.
3. **코드 재사용성**: 제네릭을 통해 여러 타입에서 재사용 가능한 클래스 및 메서드 작성.

---

