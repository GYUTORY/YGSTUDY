
# `this`와 `super`의 차이

자바에서 `this`와 `super`는 객체 지향 프로그래밍에서 중요한 키워드입니다. 이 둘은 모두 참조의 역할을 하지만, 참조하는 대상과 사용 방법에서 차이가 있습니다.

## 1. `this` 키워드

`this`는 **현재 객체 자신**을 참조하는 데 사용됩니다. 주로 다음과 같은 상황에서 활용됩니다.

### 1.1 `this`의 주요 사용 목적
1. **인스턴스 변수와 지역 변수 구분**  
   같은 이름을 가진 지역 변수와 인스턴스 변수가 혼재할 때, `this`를 사용하여 인스턴스 변수를 명확히 참조합니다.

2. **현재 객체 참조**  
   메서드 내부에서 현재 객체를 다른 메서드나 생성자로 전달할 때 사용합니다.

3. **생성자 간 호출**  
   클래스 내에서 다른 생성자를 호출할 때 `this()`를 사용합니다.

### 1.2 `this`의 사용 예시

#### 1.2.1 인스턴스 변수와 지역 변수 구분
```java
class Person {
    String name;
    int age;

    public Person(String name, int age) {
        this.name = name; // 'this'를 사용하여 인스턴스 변수 명시
        this.age = age;
    }
}
```

#### 1.2.2 현재 객체 참조
```java
class Person {
    String name;

    public Person(String name) {
        this.name = name;
    }

    public void printInfo() {
        System.out.println("Name: " + this.name);
    }

    public void callAnotherMethod() {
        this.printInfo(); // 현재 객체의 메서드 호출
    }
}
```

#### 1.2.3 생성자 간 호출
```java
class Person {
    String name;
    int age;

    public Person() {
        this("Unknown", 0); // 다른 생성자 호출
    }

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
```

---

## 2. `super` 키워드

`super`는 **부모 클래스의 멤버**를 참조하거나 호출할 때 사용됩니다. 자식 클래스에서 부모 클래스와 관련된 작업을 수행할 때 매우 유용합니다.

### 2.1 `super`의 주요 사용 목적
1. **부모 클래스의 변수 참조**  
   부모 클래스에 정의된 변수에 접근할 때 사용합니다.

2. **부모 클래스의 메서드 호출**  
   자식 클래스에서 부모 클래스의 메서드를 호출할 때 사용합니다.

3. **부모 클래스 생성자 호출**  
   자식 클래스의 생성자에서 부모 클래스의 생성자를 명시적으로 호출할 때 사용합니다.

### 2.2 `super`의 사용 예시

#### 2.2.1 부모 클래스의 변수 참조
```java
class Animal {
    String name = "Animal";
}

class Dog extends Animal {
    String name = "Dog";

    public void printNames() {
        System.out.println(name);       // 현재 클래스의 name
        System.out.println(super.name); // 부모 클래스의 name
    }
}
```

#### 2.2.2 부모 클래스의 메서드 호출
```java
class Animal {
    public void sound() {
        System.out.println("Animal makes a sound");
    }
}

class Dog extends Animal {
    @Override
    public void sound() {
        super.sound(); // 부모 클래스의 메서드 호출
        System.out.println("Dog barks");
    }
}
```

#### 2.2.3 부모 클래스 생성자 호출
```java
class Animal {
    String name;

    public Animal(String name) {
        this.name = name;
    }
}

class Dog extends Animal {
    public Dog(String name) {
        super(name); // 부모 클래스의 생성자 호출
    }
}
```

---

## 3. `this`와 `super`의 주요 차이점

| 구분             | `this`                                    | `super`                                    |
|------------------|-------------------------------------------|-------------------------------------------|
| **참조 대상**    | 현재 객체                                 | 부모 클래스                               |
| **주요 목적**    | 현재 객체의 변수, 메서드, 생성자 호출     | 부모 클래스의 변수, 메서드, 생성자 호출   |
| **생성자 호출**  | 같은 클래스 내 다른 생성자를 호출         | 부모 클래스의 생성자를 호출               |
| **사용 위치**    | 인스턴스 메서드와 생성자                 | 자식 클래스의 메서드와 생성자             |
| **오버라이딩**   | 오버라이딩 메서드에서 현재 클래스의 메서드 호출 | 오버라이딩 메서드에서 부모 클래스의 메서드 호출 |

---

## 4. 결론

- `this`는 **현재 객체 자신**을 참조하며, 인스턴스 변수 구분, 메서드 호출, 생성자 호출 등에 사용됩니다.
- `super`는 **부모 클래스**를 참조하며, 부모 클래스의 변수, 메서드, 생성자를 호출할 때 사용됩니다.

두 키워드는 객체 지향 프로그래밍에서 클래스 간의 관계를 명확히 하고, 코드의 재사용성을 높이는 데 중요한 역할을 합니다.
