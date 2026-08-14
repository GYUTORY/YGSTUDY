---
title: Java this와 super 키워드
tags: [language, java]
updated: 2025-12-28
---

# Java this와 super 키워드
## 배경

Java에서 `this`와 `super`는 객체지향 프로그래밍의 핵심 키워드다. `this`는 현재 객체를 참조하고, `super`는 부모 클래스를 참조한다.

### this와 super의 필요성
- **명확한 참조**: 같은 이름의 변수나 메서드를 구분하여 참조
- **생성자 체이닝**: 효율적인 객체 초기화
- **상속 관계 관리**: 부모-자식 클래스 간의 명확한 관계 설정
- **코드 가독성**: 의도가 명확한 코드 작성

### 기본 개념
- **this**: 현재 객체의 인스턴스를 참조하는 키워드
- **super**: 부모 클래스의 인스턴스를 참조하는 키워드
- **생성자 체이닝**: 생성자 간의 호출을 통한 코드 재사용
- **변수 섀도잉**: 지역 변수가 인스턴스 변수를 가리는 현상

## 핵심

### 1. this 키워드

#### this의 주요 사용 목적
1. **인스턴스 변수와 지역 변수 구분**: 같은 이름을 가진 변수들을 명확히 구분
2. **현재 객체 참조**: 메서드 내부에서 현재 객체를 다른 메서드나 생성자로 전달
3. **생성자 간 호출**: 클래스 내에서 다른 생성자를 호출

#### 인스턴스 변수와 지역 변수 구분
```java
class Person {
    String name;
    int age;

    public Person(String name, int age) {
        this.name = name; // 'this'를 사용하여 인스턴스 변수 명시
        this.age = age;
    }
    
    public void setAge(int age) {
        this.age = age; // 매개변수 age와 인스턴스 변수 age 구분
    }
}
```

#### 현재 객체 참조
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
    
    public Person getCurrentInstance() {
        return this; // 현재 객체 반환
    }
}
```

#### 생성자 간 호출
```java
class Person {
    String name;
    int age;
    String email;

    // 기본 생성자
    public Person() {
        this("Unknown", 0); // 다른 생성자 호출
    }

    // 이름과 나이만 받는 생성자
    public Person(String name, int age) {
        this(name, age, ""); // 다른 생성자 호출
    }

    // 모든 정보를 받는 생성자
    public Person(String name, int age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }
}
```

### 2. super 키워드

#### super의 주요 사용 목적
1. **부모 클래스의 변수 참조**: 부모 클래스에 정의된 변수에 접근
2. **부모 클래스의 메서드 호출**: 자식 클래스에서 부모 클래스의 메서드 호출
3. **부모 클래스 생성자 호출**: 자식 클래스 생성자에서 부모 클래스 생성자 호출

#### 부모 클래스의 변수 참조
```java
class Animal {
    String name = "Animal";
    int age = 0;
}

class Dog extends Animal {
    String name = "Dog"; // 변수 섀도잉

    public void printNames() {
        System.out.println(name);       // 현재 클래스의 name: "Dog"
        System.out.println(this.name);  // 현재 클래스의 name: "Dog"
        System.out.println(super.name); // 부모 클래스의 name: "Animal"
    }
    
    public void printAge() {
        System.out.println(age);        // 부모 클래스의 age (섀도잉되지 않음)
        System.out.println(super.age);  // 부모 클래스의 age
    }
}
```

주석은 전부 맞다. 하지만 **필드 섀도잉의 진짜 함정은 클래스 안이 아니라 밖에 있다.** 필드는 메서드와 달리 다형적으로 동작하지 않는다. 필드는 **참조 변수의 타입**으로, 메서드는 **실제 객체의 타입**으로 결정된다.

```java
Dog d = new Dog();
Animal ref = d;          // 같은 객체를 부모 타입으로 가리킨다

((Dog) ref).name         // "Dog"
ref.name                 // "Animal"   ← 객체는 Dog 인데 Animal 의 필드를 읽는다
ref.who()                // "Dog"      ← 메서드는 오버라이딩이 적용된다
```

객체는 하나인데 `ref.name` 과 `ref.who()` 가 서로 다른 클래스를 가리킨다. 필드 섀도잉은 부모 필드를 덮어쓰는 게 아니라 **같은 이름의 필드를 하나 더 만드는 것**이고, 인스턴스 안에는 `name` 이 두 개 존재한다. 어느 쪽을 읽을지는 컴파일 시점에 참조 타입으로 정해진다.

그래서 실무 규칙은 단순하다. **필드는 섀도잉하지 않는다.** 부모와 자식이 같은 이름의 필드를 가져야 할 이유는 거의 없고, 있다면 대개 설계가 잘못된 것이다. 값을 바꾸고 싶으면 필드를 새로 선언하는 대신 부모 필드에 다른 값을 넣거나, 접근을 메서드로 감싸 오버라이딩한다.

`age` 가 "섀도잉되지 않음"인 이유도 같다. `Dog` 이 `age` 를 다시 선언하지 않았으니 필드가 하나뿐이고, 그래서 `age` 와 `super.age` 가 같은 값을 읽는다.

#### 부모 클래스의 메서드 호출
```java
class Animal {
    public void makeSound() {
        System.out.println("Some animal sound");
    }
    
    public void eat() {
        System.out.println("Animal is eating");
    }
}

class Dog extends Animal {
    @Override
    public void makeSound() {
        System.out.println("Woof! Woof!");
    }
    
    public void bark() {
        super.makeSound(); // 부모 클래스의 makeSound() 호출
        this.makeSound();  // 현재 클래스의 makeSound() 호출
    }
    
    public void eatAndBark() {
        super.eat();       // 부모 클래스의 eat() 호출
        this.makeSound();  // 현재 클래스의 makeSound() 호출
    }
}
```

#### 부모 클래스 생성자 호출
```java
class Animal {
    String name;
    int age;
    
    public Animal(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    public Animal() {
        this("Unknown Animal", 0);
    }
}

class Dog extends Animal {
    String breed;
    
    // 부모 클래스의 생성자 호출
    public Dog(String name, int age, String breed) {
        super(name, age); // 부모 클래스 생성자 호출 (반드시 첫 번째 줄)
        this.breed = breed;
    }
    
    // 부모 클래스의 기본 생성자 호출
    public Dog(String breed) {
        super(); // 부모 클래스의 기본 생성자 호출
        this.breed = breed;
    }
    
    // 부모 클래스의 매개변수 생성자 호출
    public Dog(String name, String breed) {
        super(name, 1); // 부모 클래스 생성자 호출
        this.breed = breed;
    }
}
```

### 3. this와 super의 차이점

#### 사용 시점과 목적
```java
class Parent {
    String name = "Parent";
    
    public Parent() {
        System.out.println("Parent constructor");
    }
    
    public void method() {
        System.out.println("Parent method");
    }
}

class Child extends Parent {
    String name = "Child";
    
    public Child() {
        super(); // 부모 클래스 생성자 호출
        System.out.println("Child constructor");
    }
    
    public void method() {
        System.out.println("Child method");
    }
    
    public void demonstrate() {
        // 변수 참조
        System.out.println(name);        // "Child"
        System.out.println(this.name);   // "Child"
        System.out.println(super.name);  // "Parent"
        
        // 메서드 호출
        this.method();   // "Child method"
        super.method();  // "Parent method"
    }
}
```

## 예시

### 1. 실제 사용 사례

#### 계층적 객체 구조
```java
class Vehicle {
    String brand;
    String model;
    int year;
    
    public Vehicle(String brand, String model, int year) {
        this.brand = brand;
        this.model = model;
        this.year = year;
    }
    
    public void displayInfo() {
        System.out.println("Brand: " + brand + ", Model: " + model + ", Year: " + year);
    }
    
    public void start() {
        System.out.println("Vehicle is starting...");
    }
}

class Car extends Vehicle {
    int numDoors;
    
    public Car(String brand, String model, int year, int numDoors) {
        super(brand, model, year); // 부모 클래스 생성자 호출
        this.numDoors = numDoors;
    }
    
    @Override
    public void displayInfo() {
        super.displayInfo(); // 부모 클래스의 displayInfo() 호출
        System.out.println("Number of doors: " + this.numDoors);
    }
    
    @Override
    public void start() {
        System.out.println("Car engine is starting...");
        super.start(); // 부모 클래스의 start() 호출
    }
}

class ElectricCar extends Car {
    int batteryCapacity;
    
    public ElectricCar(String brand, String model, int year, int numDoors, int batteryCapacity) {
        super(brand, model, year, numDoors); // 부모 클래스 생성자 호출
        this.batteryCapacity = batteryCapacity;
    }
    
    @Override
    public void start() {
        System.out.println("Electric car is starting silently...");
        super.start(); // 부모 클래스의 start() 호출
    }
    
    public void charge() {
        System.out.println("Charging with " + this.batteryCapacity + "kWh capacity");
    }
}
```

#### 빌더 패턴에서의 활용
```java
class Person {
    private String name;
    private int age;
    private String email;
    private String address;
    
    // 기본 생성자
    private Person() {}
    
    // 모든 매개변수를 받는 생성자
    private Person(String name, int age, String email, String address) {
        this.name = name;
        this.age = age;
        this.email = email;
        this.address = address;
    }
    
    // 정적 내부 클래스로 빌더 구현
    public static class Builder {
        private String name;
        private int age;
        private String email;
        private String address;
        
        public Builder name(String name) {
            this.name = name;
            return this; // 메서드 체이닝을 위해 this 반환
        }
        
        public Builder age(int age) {
            this.age = age;
            return this;
        }
        
        public Builder email(String email) {
            this.email = email;
            return this;
        }
        
        public Builder address(String address) {
            this.address = address;
            return this;
        }
        
        public Person build() {
            return new Person(this.name, this.age, this.email, this.address);
        }
    }
    
    // getter 메서드들
    public String getName() { return this.name; }
    public int getAge() { return this.age; }
    public String getEmail() { return this.email; }
    public String getAddress() { return this.address; }
}

// 사용 예시
Person person = new Person.Builder()
    .name("John Doe")
    .age(30)
    .email("john@example.com")
    .address("123 Main St")
    .build();
```

### 2. 고급 패턴

#### 메서드 체이닝
```java
class Calculator {
    private double result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public Calculator(double initialValue) {
        this.result = initialValue;
    }
    
    public Calculator add(double value) {
        this.result += value;
        return this; // 메서드 체이닝을 위해 this 반환
    }
    
    public Calculator subtract(double value) {
        this.result -= value;
        return this;
    }
    
    public Calculator multiply(double value) {
        this.result *= value;
        return this;
    }
    
    public Calculator divide(double value) {
        if (value != 0) {
            this.result /= value;
        }
        return this;
    }
    
    public double getResult() {
        return this.result;
    }
    
    public void reset() {
        this.result = 0;
    }
}

// 사용 예시
Calculator calc = new Calculator(10)
    .add(5)
    .multiply(2)
    .subtract(3)
    .divide(4);
    
System.out.println("Result: " + calc.getResult()); // 5.5
```

**주석의 `5.5` 는 틀렸다. 실제로 실행하면 `6.75` 가 나온다.**

```
10 + 5 = 15  →  × 2 = 30  →  − 3 = 27  →  ÷ 4 = 6.75
```

메서드 체이닝은 **왼쪽에서 오른쪽으로 순서대로** 적용될 뿐 사칙연산 우선순위를 따르지 않는다. `10 + 5 * 2 - 3 / 4` 를 수학 규칙대로 계산하면 19.25 이고, 그것도 5.5 는 아니다. 체이닝 API 를 읽을 때 무의식적으로 연산자 우선순위를 적용하게 되는 것이 이 방식의 알려진 함정이다.

`divide` 에도 짚어 둘 게 있다. `if (value != 0)` 으로 0 을 걸러내는데, **0 을 넘기면 아무 일도 일어나지 않고 이전 결과가 그대로 남는다.**

```java
new Calculator(10).add(5).multiply(2).subtract(3).divide(0).getResult();  // 27.0
```

예외도 없고 로그도 없다. 호출한 쪽은 나눗셈이 수행됐다고 믿는데 값은 나누기 전 상태다. 0 으로 나누는 게 오류라면 예외를 던지고, 무시가 정말 의도라면 그 사실을 반환값으로 알려야 한다. **조용히 아무것도 하지 않는 것이 가장 나쁜 선택지다.**

참고로 `double` 나눗셈은 0 으로 나눠도 예외가 아니라 `Infinity` 를 준다(정수 나눗셈만 `ArithmeticException` 을 던진다). 즉 이 가드가 없어도 프로그램은 죽지 않고 `Infinity` 가 전파된다. 어느 쪽이든 명시적으로 처리하는 편이 낫다.

#### 상속 체인에서의 생성자 호출
```java
class GrandParent {
    String familyName;
    
    public GrandParent() {
        this.familyName = "Smith";
        System.out.println("GrandParent constructor called");
    }
    
    public GrandParent(String familyName) {
        this.familyName = familyName;
        System.out.println("GrandParent constructor with familyName called");
    }
}

class Parent extends GrandParent {
    String firstName;
    
    public Parent() {
        super(); // GrandParent의 기본 생성자 호출
        this.firstName = "John";
        System.out.println("Parent constructor called");
    }
    
    public Parent(String firstName) {
        super("Johnson"); // GrandParent의 매개변수 생성자 호출
        this.firstName = firstName;
        System.out.println("Parent constructor with firstName called");
    }
}

class Child extends Parent {
    String middleName;
    
    public Child() {
        super(); // Parent의 기본 생성자 호출
        this.middleName = "Michael";
        System.out.println("Child constructor called");
    }
    
    public Child(String middleName) {
        super("Jane"); // Parent의 매개변수 생성자 호출
        this.middleName = middleName;
        System.out.println("Child constructor with middleName called");
    }
    
    public void displayFullName() {
        System.out.println("Full name: " + this.firstName + " " + 
                          this.middleName + " " + this.familyName);
    }
}
```

실행하면 **생성자 본문은 조상부터 역순으로** 찍힌다. `super()` 가 첫 줄이라 자식 본문은 부모가 끝난 뒤에야 실행된다.

```
=== new Child() ===
GrandParent constructor called
Parent constructor called
Child constructor called
Full name: John Michael Smith

=== new Child("Lee") ===
GrandParent constructor with familyName called
Parent constructor with firstName called
Child constructor with middleName called
Full name: Jane Lee Johnson
```

`new Child("Lee")` 에서 `familyName` 이 `"Johnson"` 이 되는 게 이 예제의 요점이다. `Child(String)` → `super("Jane")` → `Parent(String)` → `super("Johnson")` 순으로 전달돼, **호출한 쪽이 준 값이 아니라 중간 생성자가 하드코딩한 값**이 최상위에 도달한다.

이 "부모 먼저" 순서가 만드는 함정이 하나 있다. **생성자에서 오버라이딩 가능한 메서드를 부르면 자식 필드가 아직 초기화되지 않은 상태로 실행된다.**

```java
class Base {
    Base() { init(); }                  // 오버라이딩 가능한 메서드 호출
    void init() { }
}
class Derived extends Base {
    private String value = "assigned";
    private final int n = 42;
    @Override void init() { System.out.println("value=" + value + ", n=" + n); }
}
new Derived();
```

```
value=null, n=42
```

`init()` 은 오버라이딩됐으니 `Derived` 것이 불리는데, 그 시점에는 `Base` 생성자가 도는 중이라 `Derived` 의 필드 초기화가 아직 실행되지 않았다. `value` 는 기본값 `null` 이다. `n` 이 `42` 로 보이는 건 `final int` 상수라 컴파일 시점에 값이 인라인되기 때문이고, 이 예외가 오히려 헷갈림을 키운다.

**생성자에서는 오버라이딩 가능한 메서드를 호출하지 않는다.** 꼭 필요하면 `private` 나 `final` 로 선언해 오버라이딩 자체를 막는다.

## 운영 팁

### 성능 최적화

#### 생성자 체이닝 최적화
```java
class OptimizedPerson {
    private final String name;
    private final int age;
    private final String email;
    
    // 가장 구체적인 생성자를 기본 생성자로 사용
    public OptimizedPerson(String name, int age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }
    
    // 기본값을 사용하는 생성자
    public OptimizedPerson(String name, int age) {
        this(name, age, ""); // 생성자 체이닝
    }
    
    // 이름만 받는 생성자
    public OptimizedPerson(String name) {
        this(name, 0, ""); // 생성자 체이닝
    }
    
    // 기본 생성자
    public OptimizedPerson() {
        this("Unknown", 0, ""); // 생성자 체이닝
    }
}
```

### 에러 처리

#### 안전한 생성자 호출
```java
class SafePerson {
    private String name;
    private int age;
    
    public SafePerson(String name, int age) {
        // 유효성 검사
        if (name == null || name.trim().isEmpty()) {
            throw new IllegalArgumentException("Name cannot be null or empty");
        }
        if (age < 0) {
            throw new IllegalArgumentException("Age cannot be negative");
        }
        
        this.name = name.trim();
        this.age = age;
    }
    
    public SafePerson(String name) {
        this(name, 0); // 기본 나이로 생성자 체이닝
    }
    
    public SafePerson() {
        this("Unknown", 0); // 기본값으로 생성자 체이닝
    }
}
```

### 주의사항

#### 생성자 호출 순서
```java
class ConstructorOrder {
    public ConstructorOrder() {
        // super()는 자동으로 호출되지만, 명시적으로 호출할 수도 있음
        // super(); // 부모 클래스 생성자 호출 (생략 가능)
        System.out.println("ConstructorOrder constructor");
    }
}

class ChildOrder extends ConstructorOrder {
    public ChildOrder() {
        super(); // 부모 클래스 생성자 호출 (반드시 첫 번째 줄)
        System.out.println("ChildOrder constructor");
        // super(); // 컴파일 오류! 생성자 호출은 반드시 첫 번째 줄에 있어야 함
    }
}
```

## 참고

### this와 super 사용 비교

| 상황 | this 사용 | super 사용 |
|------|-----------|------------|
| **변수 참조** | 현재 클래스의 변수 | 부모 클래스의 변수 |
| **메서드 호출** | 현재 클래스의 메서드 | 부모 클래스의 메서드 |
| **생성자 호출** | 같은 클래스의 다른 생성자 | 부모 클래스의 생성자 |
| **객체 참조** | 현재 객체 인스턴스 | 부모 객체 인스턴스 |

### this와 super 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **변수 섀도잉** | this 사용 | 명확한 구분 |
| **메서드 오버라이딩** | super 사용 | 부모 기능 활용 |
| **생성자 체이닝** | this 사용 | 코드 재사용 |
| **부모 생성자 호출** | super 사용 | 상속 관계 초기화 |
| **메서드 체이닝** | this 반환 | 유연한 API |
