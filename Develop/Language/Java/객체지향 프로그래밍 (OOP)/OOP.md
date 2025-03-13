# 객체 지향 프로그래밍(OOP) 개념 및 활용 🚀

## 1. 객체 지향 프로그래밍(OOP)이란? 🤔

**객체 지향 프로그래밍(Object-Oriented Programming, OOP)**은 **객체(Object)를 기반으로 프로그램을 구성하는 프로그래밍 패러다임**입니다.  
자바(Java)는 대표적인 객체 지향 언어로, **클래스와 객체를 활용하여 코드의 재사용성을 높이고, 유지보수를 용이하게** 만듭니다.

> **✨ OOP의 주요 특징**
> - **캡슐화(Encapsulation)** → 데이터와 메서드를 하나의 객체로 묶어 보호
> - **상속(Inheritance)** → 기존 클래스를 확장하여 새로운 클래스를 생성
> - **다형성(Polymorphism)** → 같은 메서드가 다양한 방식으로 동작 가능
> - **추상화(Abstraction)** → 불필요한 세부 사항을 숨기고 핵심 기능만 제공

---

## 2. OOP의 4대 특징 및 예제

### 2.1 캡슐화(Encapsulation) 🛡️

✔ **데이터(필드)를 외부에서 직접 접근하지 못하도록 `private`으로 보호**  
✔ **Getter와 Setter를 이용하여 데이터를 안전하게 접근**  
✔ **정보 은닉을 통해 무결성을 유지하고, 보안성을 향상**

#### ✅ 예제
```java
class BankAccount {
    private String owner;
    private double balance;

    public BankAccount(String owner, double balance) {
        this.owner = owner;
        this.balance = balance;
    }

    public double getBalance() { // Getter
        return balance;
    }

    public void deposit(double amount) { // Setter
        if (amount > 0) {
            balance += amount;
            System.out.println(amount + "원이 입금되었습니다. 현재 잔액: " + balance);
        } else {
            System.out.println("입금 금액은 0보다 커야 합니다.");
        }
    }
}

public class EncapsulationExample {
    public static void main(String[] args) {
        BankAccount account = new BankAccount("김철수", 10000);
        account.deposit(5000); // 입금 성공
        System.out.println("현재 잔액: " + account.getBalance());
    }
}
```
> **📌 `private` 키워드를 사용하여 데이터 보호 및 무결성 유지!**

---

### 2.2 상속(Inheritance) 🔄

✔ **부모 클래스의 속성과 기능을 자식 클래스가 상속받아 재사용 가능**  
✔ **코드 중복을 줄이고, 유지보수를 쉽게 함**  
✔ **`extends` 키워드를 사용하여 상속 구현**

#### ✅ 예제
```java
class Animal {
    String name;

    public void makeSound() {
        System.out.println("동물이 소리를 냅니다.");
    }
}

// Dog 클래스가 Animal 클래스를 상속받음
class Dog extends Animal {
    public void bark() {
        System.out.println(name + "가 멍멍 짖습니다!");
    }
}

public class InheritanceExample {
    public static void main(String[] args) {
        Dog dog = new Dog();
        dog.name = "바둑이";
        dog.makeSound(); // 부모 클래스 메서드 사용
        dog.bark(); // 자식 클래스 메서드 사용
    }
}
```
> **👉🏻 상속을 통해 기존 기능을 재사용하고, 새로운 기능을 추가할 수 있음!**

---

### 2.3 다형성(Polymorphism) 🎭

✔ **같은 메서드가 여러 형태로 동작할 수 있음**  
✔ **메서드 오버라이딩(Method Overriding)과 메서드 오버로딩(Method Overloading)으로 구현**

#### ✅ 예제 (메서드 오버라이딩)
```java
class Animal {
    public void makeSound() {
        System.out.println("동물이 소리를 냅니다.");
    }
}

class Cat extends Animal {
    @Override
    public void makeSound() {
        System.out.println("야옹!");
    }
}

public class PolymorphismExample {
    public static void main(String[] args) {
        Animal myAnimal = new Cat(); // 부모 타입으로 자식 객체 참조
        myAnimal.makeSound(); // 야옹! (오버라이딩된 메서드 실행)
    }
}
```
> **📌 부모 클래스의 메서드를 자식 클래스에서 재정의(오버라이딩)하여 다형성을 구현!**

---

### 2.4 추상화(Abstraction) 🎭

✔ **불필요한 세부 사항을 숨기고, 필요한 기능만 제공**  
✔ **`abstract` 키워드를 사용하여 추상 클래스를 만들고, 서브 클래스에서 구현**

#### ✅ 예제
```java
abstract class Vehicle {
    abstract void start(); // 추상 메서드 (구현 X)

    public void stop() {
        System.out.println("차량이 정지합니다.");
    }
}

class Car extends Vehicle {
    @Override
    void start() {
        System.out.println("자동차 시동을 겁니다.");
    }
}

public class AbstractionExample {
    public static void main(String[] args) {
        Car myCar = new Car();
        myCar.start();
        myCar.stop();
    }
}
```
> **👉🏻 추상 클래스를 사용하면 공통 기능을 제공하면서도, 각 클래스가 구체적인 동작을 정의하도록 강제할 수 있음!**

---

## 3. OOP를 활용한 실전 예제

✔ **OOP 개념을 적용하여 관리 시스템을 구현**  
✔ **캡슐화, 상속, 다형성, 추상화를 모두 포함**

#### ✅ 예제 (학교 시스템)
```java
abstract class Person {
    protected String name;
    protected int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    abstract void introduce();
}

class Student extends Person {
    private String studentId;

    public Student(String name, int age, String studentId) {
        super(name, age);
        this.studentId = studentId;
    }

    @Override
    void introduce() {
        System.out.println("안녕하세요, 저는 " + name + "입니다. 나이는 " + age + "살이고, 학번은 " + studentId + "입니다.");
    }
}

class Teacher extends Person {
    private String subject;

    public Teacher(String name, int age, String subject) {
        super(name, age);
        this.subject = subject;
    }

    @Override
    void introduce() {
        System.out.println("안녕하세요, 저는 " + name + "입니다. 나이는 " + age + "살이고, 담당 과목은 " + subject + "입니다.");
    }
}

public class SchoolSystem {
    public static void main(String[] args) {
        Student student = new Student("김영희", 20, "2023001");
        Teacher teacher = new Teacher("이선생", 45, "수학");

        student.introduce();
        teacher.introduce();
    }
}
```
> **📌 `Person` 클래스를 부모로 두고, `Student`와 `Teacher` 클래스가 상속받아 다형성을 구현!**

---

## 📌 결론
- **캡슐화** → 데이터 보호 (`private` 필드 + Getter/Setter 활용)
- **상속** → 코드 재사용 (`extends` 키워드 활용)
- **다형성** → 같은 메서드가 다양한 형태로 동작 (`오버라이딩` 사용)
- **추상화** → 불필요한 정보 숨기고 핵심 기능만 제공 (`abstract` 클래스 사용)

> **👉🏻 OOP 개념을 잘 활용하면 유지보수성과 확장성이 뛰어난 프로그램을 만들 수 있음!**  

