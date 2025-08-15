---
title: Marker Interface
tags: [language, java, 객체지향-프로그래밍-oop, interface, makrerinterface]
updated: 2025-08-10
---

# 마커 인터페이스 (Marker Interface)

## 배경
마커 인터페이스(Marker Interface)란 메서드가 없는, 즉 아무 내용도 가지지 않는 빈 인터페이스를 의미합니다. 이러한 인터페이스는 특정 클래스가 해당 인터페이스를 구현함으로써 **특정 속성이나 동작을 가지는 클래스**임을 나타내는 데 사용됩니다.

### 특징
- 메서드나 필드가 없기 때문에 구현하는 클래스가 추가적으로 어떤 작업을 수행할 필요가 없습니다.
- 클래스에 태그(tag)를 부여하여 **특별한 의미**를 전달하거나 **특정 동작**을 활성화시키는 역할을 합니다.
- 주로 런타임 시 리플렉션(Reflection)을 통해 인터페이스를 구현한 클래스의 존재 여부를 확인하여 특정 처리를 수행합니다.

---

- 메서드나 필드가 없기 때문에 구현하는 클래스가 추가적으로 어떤 작업을 수행할 필요가 없습니다.
- 클래스에 태그(tag)를 부여하여 **특별한 의미**를 전달하거나 **특정 동작**을 활성화시키는 역할을 합니다.
- 주로 런타임 시 리플렉션(Reflection)을 통해 인터페이스를 구현한 클래스의 존재 여부를 확인하여 특정 처리를 수행합니다.

---


### Java의 `Serializable` 인터페이스
Java에서 가장 대표적인 마커 인터페이스는 `java.io.Serializable`입니다.  
이 인터페이스는 **객체를 직렬화 가능하게 표시**하는 데 사용됩니다.

```java
import java.io.Serializable;

public class MyClass implements Serializable {
    private String name;
    private int age;

    // 생성자 및 메서드
    public MyClass(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
```

`MyClass`가 `Serializable` 인터페이스를 구현하면, 이 클래스의 객체는 직렬화(Serialization)와 역직렬화(Deserialization)가 가능합니다.

### 사용자 정의 마커 인터페이스 예시
```java
// 마커 인터페이스 정의
public interface VIP {}

// 마커 인터페이스를 구현한 클래스
public class Customer implements VIP {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}

// 마커 인터페이스 확인 로직
public class Main {
    public static void main(String[] args) {
        Customer customer = new Customer("Alice");

        if (customer instanceof VIP) {
            System.out.println(customer.getName() + "는 VIP입니다!");
        } else {
            System.out.println(customer.getName() + "는 일반 고객입니다.");
        }
    }
}
```

위 예제에서 `VIP` 인터페이스는 마커 역할을 하여 특정 조건(예: VIP 고객 여부)을 나타냅니다.

---

```java
// 마커 인터페이스 정의
public interface VIP {}

// 마커 인터페이스를 구현한 클래스
public class Customer implements VIP {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}

// 마커 인터페이스 확인 로직
public class Main {
    public static void main(String[] args) {
        Customer customer = new Customer("Alice");

        if (customer instanceof VIP) {
            System.out.println(customer.getName() + "는 VIP입니다!");
        } else {
            System.out.println(customer.getName() + "는 일반 고객입니다.");
        }
    }
}
```

위 예제에서 `VIP` 인터페이스는 마커 역할을 하여 특정 조건(예: VIP 고객 여부)을 나타냅니다.

---

1. **단순성**: 메서드 구현이 필요 없으므로 간단하게 태그 역할을 수행할 수 있습니다.
2. **유연성**: 리플렉션을 활용하면 다양한 런타임 동작을 유연하게 처리할 수 있습니다.
3. **가독성 향상**: 클래스가 어떤 특징을 가지는지 명시적으로 보여줄 수 있습니다.

---

- **단점**:
    - 아무 메서드도 포함하지 않으므로 인터페이스 자체만으로는 의미가 모호할 수 있습니다.
    - 런타임에만 확인 가능하므로 컴파일 타임 안전성이 떨어질 수 있습니다.

- **대안**:
    - Java에서는 마커 인터페이스 대신 **애노테이션(annotation)**을 사용하여 유사한 기능을 구현하는 것이 일반적입니다.
    - 예: `@Override`, `@Deprecated`와 같은 표준 애노테이션.

### 애노테이션 예시
```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface VIP {}

@VIP
public class Customer {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}
```

---

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface VIP {}

@VIP
public class Customer {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}
```

---

마커 인터페이스는 단순하고 강력한 개념이지만, 현대 프로그래밍에서는 애노테이션과 같은 대안이 더 선호됩니다.  
그러나 기존 시스템에서는 여전히 중요한 역할을 수행하고 있습니다.






- 메서드나 필드가 없기 때문에 구현하는 클래스가 추가적으로 어떤 작업을 수행할 필요가 없습니다.
- 클래스에 태그(tag)를 부여하여 **특별한 의미**를 전달하거나 **특정 동작**을 활성화시키는 역할을 합니다.
- 주로 런타임 시 리플렉션(Reflection)을 통해 인터페이스를 구현한 클래스의 존재 여부를 확인하여 특정 처리를 수행합니다.

---

- 메서드나 필드가 없기 때문에 구현하는 클래스가 추가적으로 어떤 작업을 수행할 필요가 없습니다.
- 클래스에 태그(tag)를 부여하여 **특별한 의미**를 전달하거나 **특정 동작**을 활성화시키는 역할을 합니다.
- 주로 런타임 시 리플렉션(Reflection)을 통해 인터페이스를 구현한 클래스의 존재 여부를 확인하여 특정 처리를 수행합니다.

---


```java
// 마커 인터페이스 정의
public interface VIP {}

// 마커 인터페이스를 구현한 클래스
public class Customer implements VIP {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}

// 마커 인터페이스 확인 로직
public class Main {
    public static void main(String[] args) {
        Customer customer = new Customer("Alice");

        if (customer instanceof VIP) {
            System.out.println(customer.getName() + "는 VIP입니다!");
        } else {
            System.out.println(customer.getName() + "는 일반 고객입니다.");
        }
    }
}
```

위 예제에서 `VIP` 인터페이스는 마커 역할을 하여 특정 조건(예: VIP 고객 여부)을 나타냅니다.

---

```java
// 마커 인터페이스 정의
public interface VIP {}

// 마커 인터페이스를 구현한 클래스
public class Customer implements VIP {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}

// 마커 인터페이스 확인 로직
public class Main {
    public static void main(String[] args) {
        Customer customer = new Customer("Alice");

        if (customer instanceof VIP) {
            System.out.println(customer.getName() + "는 VIP입니다!");
        } else {
            System.out.println(customer.getName() + "는 일반 고객입니다.");
        }
    }
}
```

위 예제에서 `VIP` 인터페이스는 마커 역할을 하여 특정 조건(예: VIP 고객 여부)을 나타냅니다.

---

1. **단순성**: 메서드 구현이 필요 없으므로 간단하게 태그 역할을 수행할 수 있습니다.
2. **유연성**: 리플렉션을 활용하면 다양한 런타임 동작을 유연하게 처리할 수 있습니다.
3. **가독성 향상**: 클래스가 어떤 특징을 가지는지 명시적으로 보여줄 수 있습니다.

---

- **단점**:
    - 아무 메서드도 포함하지 않으므로 인터페이스 자체만으로는 의미가 모호할 수 있습니다.
    - 런타임에만 확인 가능하므로 컴파일 타임 안전성이 떨어질 수 있습니다.

- **대안**:
    - Java에서는 마커 인터페이스 대신 **애노테이션(annotation)**을 사용하여 유사한 기능을 구현하는 것이 일반적입니다.
    - 예: `@Override`, `@Deprecated`와 같은 표준 애노테이션.

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface VIP {}

@VIP
public class Customer {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}
```

---

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface VIP {}

@VIP
public class Customer {
    private String name;

    public Customer(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}
```

---

마커 인터페이스는 단순하고 강력한 개념이지만, 현대 프로그래밍에서는 애노테이션과 같은 대안이 더 선호됩니다.  
그러나 기존 시스템에서는 여전히 중요한 역할을 수행하고 있습니다.










