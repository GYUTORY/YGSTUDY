---
title: Java 객체지향 프로그래밍(OOP) 가이드
tags: [language, java, 객체지향-프로그래밍-oop, oop, encapsulation, inheritance, polymorphism, abstraction]
updated: 2026-01-07
---

# Java 객체지향 프로그래밍(OOP) 가이드

## 배경

객체지향 프로그래밍(Object-Oriented Programming, OOP)은 객체(Object)를 기반으로 프로그램을 구성하는 프로그래밍 패러다임입니다. Java는 대표적인 객체지향 언어로, 클래스와 객체를 활용하여 코드의 재사용성을 높이고 유지보수를 용이하게 만듭니다.

### OOP의 필요성
- **코드 재사용성**: 기존 코드를 활용하여 새로운 기능 개발
- **유지보수성**: 모듈화된 구조로 쉬운 수정과 확장
- **데이터 보호**: 캡슐화를 통한 데이터 무결성 보장
- **개발 효율성**: 팀 개발에서 명확한 역할 분담

### 기본 개념
- **객체**: 데이터와 기능을 가진 실체
- **클래스**: 객체를 생성하기 위한 템플릿
- **캡슐화**: 데이터와 메서드를 하나로 묶어 보호
- **상속**: 기존 클래스를 확장하여 새로운 클래스 생성
- **다형성**: 같은 메서드가 다양한 방식으로 동작
- **추상화**: 불필요한 세부사항을 숨기고 핵심 기능만 제공

## 핵심

### 1. 캡슐화(Encapsulation)

#### 캡슐화의 개념
데이터(필드)를 외부에서 직접 접근하지 못하도록 `private`으로 보호하고, Getter와 Setter를 이용하여 데이터를 안전하게 접근하는 기법입니다.

#### 캡슐화 예제
```java
class BankAccount {
    private String owner;    // private으로 데이터 보호
    private double balance;  // 외부에서 직접 접근 불가

    public BankAccount(String owner, double balance) {
        this.owner = owner;
        this.balance = balance;
    }

    // Getter: 데이터를 안전하게 읽기
    public double getBalance() {
        return balance;
    }

    public String getOwner() {
        return owner;
    }

    // Setter: 데이터를 안전하게 수정
    public void deposit(double amount) {
        if (amount > 0) {
            balance += amount;
            System.out.println(amount + "원이 입금되었습니다. 현재 잔액: " + balance);
        } else {
            System.out.println("입금 금액은 0보다 커야 합니다.");
        }
    }

    public void withdraw(double amount) {
        if (amount > 0 && amount <= balance) {
            balance -= amount;
            System.out.println(amount + "원이 출금되었습니다. 현재 잔액: " + balance);
        } else {
            System.out.println("잔액이 부족하거나 잘못된 금액입니다.");
        }
    }
}

// 사용 예시
public class EncapsulationExample {
    public static void main(String[] args) {
        BankAccount account = new BankAccount("김철수", 10000);
        
        // 직접 접근 불가: account.balance = -1000; (컴파일 오류)
        
        account.deposit(5000);  // 안전한 입금
        account.withdraw(2000); // 안전한 출금
        System.out.println("현재 잔액: " + account.getBalance());
    }
}
```

### 2. 상속(Inheritance)

#### 상속의 개념
기존 클래스의 속성과 메서드를 새로운 클래스가 재사용할 수 있게 하는 기법입니다. 코드 중복을 줄이고 계층 구조를 만들 수 있습니다.

#### 상속 예제
```java
// 부모 클래스 (기본 클래스)
class Animal {
    protected String name;  // protected: 자식 클래스에서 접근 가능
    protected int age;

    public Animal(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public void makeSound() {
        System.out.println("동물이 소리를 냅니다.");
    }

    public void eat() {
        System.out.println(name + "이(가) 먹이를 먹습니다.");
    }

    public void sleep() {
        System.out.println(name + "이(가) 잠을 잡니다.");
    }
}

// 자식 클래스 (파생 클래스)
class Dog extends Animal {
    private String breed;  // Dog 클래스만의 고유 속성

    public Dog(String name, int age, String breed) {
        super(name, age);  // 부모 클래스 생성자 호출
        this.breed = breed;
    }

    @Override
    public void makeSound() {
        System.out.println(name + "가 멍멍 짖습니다!");
    }

    public void fetch() {
        System.out.println(name + "가 공을 가져옵니다.");
    }

    public String getBreed() {
        return breed;
    }
}

// 사용 예시
public class InheritanceExample {
    public static void main(String[] args) {
        Dog dog = new Dog("바둑이", 3, "진돗개");
        
        // 부모 클래스의 메서드 사용
        dog.eat();      // 바둑이가 먹이를 먹습니다.
        dog.sleep();    // 바둑이가 잠을 잡니다.
        
        // 오버라이드된 메서드 사용
        dog.makeSound(); // 바둑이가 멍멍 짖습니다!
        
        // 자식 클래스만의 메서드 사용
        dog.fetch();    // 바둑이가 공을 가져옵니다.
        
        System.out.println("품종: " + dog.getBreed());
    }
}
```

### 3. 다형성(Polymorphism)

#### 다형성의 개념
같은 메서드가 다양한 방식으로 동작하는 기법입니다. 오버라이딩과 오버로딩을 통해 구현됩니다.

#### 다형성 예제
```java
// 다형성을 위한 인터페이스
interface Animal {
    void makeSound();
    void move();
}

// 다양한 동물 클래스들
class Dog implements Animal {
    @Override
    public void makeSound() {
        System.out.println("멍멍!");
    }

    @Override
    public void move() {
        System.out.println("강아지가 뛰어갑니다.");
    }
}

class Cat implements Animal {
    @Override
    public void makeSound() {
        System.out.println("야옹!");
    }

    @Override
    public void move() {
        System.out.println("고양이가 걸어갑니다.");
    }
}

class Bird implements Animal {
    @Override
    public void makeSound() {
        System.out.println("짹짹!");
    }

    @Override
    public void move() {
        System.out.println("새가 날아갑니다.");
    }
}

// 다형성을 활용한 메서드
public class PolymorphismExample {
    public static void main(String[] args) {
        Animal[] animals = {
            new Dog(),
            new Cat(),
            new Bird()
        };

        // 같은 메서드 호출이지만 각각 다른 동작
        for (Animal animal : animals) {
            animal.makeSound();
            animal.move();
            System.out.println();
        }
    }

    // 다형성을 활용한 메서드
    public static void animalAction(Animal animal) {
        animal.makeSound();
        animal.move();
    }
}
```

### 4. 추상화(Abstraction)

#### 추상화의 개념
복잡한 시스템에서 핵심적인 개념이나 기능을 간추려 표현하는 기법입니다. 추상 클래스와 인터페이스를 통해 구현됩니다.

#### 추상화 예제
```java
// 추상 클래스: 공통 기능을 정의하고 일부는 구현을 강제
abstract class Vehicle {
    protected String brand;
    protected String model;

    public Vehicle(String brand, String model) {
        this.brand = brand;
        this.model = model;
    }

    // 공통 메서드
    public void start() {
        System.out.println(brand + " " + model + " 시동을 겁니다.");
    }

    public void stop() {
        System.out.println(brand + " " + model + " 정지합니다.");
    }

    // 추상 메서드: 자식 클래스에서 반드시 구현해야 함
    public abstract void accelerate();
    public abstract void brake();
}

// 구체적인 클래스들
class Car extends Vehicle {
    public Car(String brand, String model) {
        super(brand, model);
    }

    @Override
    public void accelerate() {
        System.out.println("자동차가 가속합니다.");
    }

    @Override
    public void brake() {
        System.out.println("자동차가 브레이크를 밟습니다.");
    }
}

class Motorcycle extends Vehicle {
    public Motorcycle(String brand, String model) {
        super(brand, model);
    }

    @Override
    public void accelerate() {
        System.out.println("오토바이가 가속합니다.");
    }

    @Override
    public void brake() {
        System.out.println("오토바이가 브레이크를 밟습니다.");
    }
}

// 사용 예시
public class AbstractionExample {
    public static void main(String[] args) {
        Vehicle car = new Car("현대", "아반떼");
        Vehicle motorcycle = new Motorcycle("혼다", "CBR");

        car.start();
        car.accelerate();
        car.brake();
        car.stop();

        System.out.println();

        motorcycle.start();
        motorcycle.accelerate();
        motorcycle.brake();
        motorcycle.stop();
    }
}
```

## 예시

### 1. 실제 사용 사례

#### 도서 관리 시스템
```java
// 추상 클래스: 도서의 기본 정보
abstract class Book {
    protected String title;
    protected String author;
    protected String isbn;
    protected boolean isAvailable;

    public Book(String title, String author, String isbn) {
        this.title = title;
        this.author = author;
        this.isbn = isbn;
        this.isAvailable = true;
    }

    public abstract void displayInfo();
    public abstract String getType();

    // 공통 메서드
    public void borrow() {
        if (isAvailable) {
            isAvailable = false;
            System.out.println(title + "이(가) 대출되었습니다.");
        } else {
            System.out.println(title + "은(는) 이미 대출 중입니다.");
        }
    }

    public void returnBook() {
        if (!isAvailable) {
            isAvailable = true;
            System.out.println(title + "이(가) 반납되었습니다.");
        } else {
            System.out.println(title + "은(는) 이미 반납된 상태입니다.");
        }
    }
}

// 구체적인 도서 클래스들
class FictionBook extends Book {
    private String genre;

    public FictionBook(String title, String author, String isbn, String genre) {
        super(title, author, isbn);
        this.genre = genre;
    }

    @Override
    public void displayInfo() {
        System.out.println("소설: " + title + " | 저자: " + author + " | 장르: " + genre);
    }

    @Override
    public String getType() {
        return "소설";
    }
}

class NonFictionBook extends Book {
    private String subject;

    public NonFictionBook(String title, String author, String isbn, String subject) {
        super(title, author, isbn);
        this.subject = subject;
    }

    @Override
    public void displayInfo() {
        System.out.println("비소설: " + title + " | 저자: " + author + " | 주제: " + subject);
    }

    @Override
    public String getType() {
        return "비소설";
    }
}

// 도서관 관리 클래스
class Library {
    private List<Book> books;

    public Library() {
        this.books = new ArrayList<>();
    }

    public void addBook(Book book) {
        books.add(book);
        System.out.println(book.getType() + " 도서가 추가되었습니다.");
    }

    public void displayAllBooks() {
        System.out.println("=== 도서 목록 ===");
        for (Book book : books) {
            book.displayInfo();
            System.out.println("대출 가능: " + book.isAvailable);
            System.out.println();
        }
    }

    public void borrowBook(String title) {
        for (Book book : books) {
            if (book.title.equals(title)) {
                book.borrow();
                return;
            }
        }
        System.out.println("도서를 찾을 수 없습니다.");
    }
}
```

### 2. 고급 패턴

#### 팩토리 패턴과 OOP
```java
// 제품 인터페이스
interface Product {
    void create();
    void use();
}

// 구체적인 제품들
class ConcreteProductA implements Product {
    @Override
    public void create() {
        System.out.println("제품 A를 생성합니다.");
    }

    @Override
    public void use() {
        System.out.println("제품 A를 사용합니다.");
    }
}

class ConcreteProductB implements Product {
    @Override
    public void create() {
        System.out.println("제품 B를 생성합니다.");
    }

    @Override
    public void use() {
        System.out.println("제품 B를 사용합니다.");
    }
}

// 팩토리 클래스
class ProductFactory {
    public static Product createProduct(String type) {
        switch (type.toLowerCase()) {
            case "a":
                return new ConcreteProductA();
            case "b":
                return new ConcreteProductB();
            default:
                throw new IllegalArgumentException("알 수 없는 제품 타입: " + type);
        }
    }
}

// 사용 예시
public class FactoryPatternExample {
    public static void main(String[] args) {
        Product productA = ProductFactory.createProduct("A");
        Product productB = ProductFactory.createProduct("B");

        productA.create();
        productA.use();

        productB.create();
        productB.use();
    }
}
```

## 운영 팁

### 설계 원칙

#### SOLID 원칙 적용
```java
// 단일 책임 원칙 (SRP)
class UserManager {
    public void createUser(String name, String email) {
        // 사용자 생성 로직만 담당
    }
}

class EmailService {
    public void sendEmail(String to, String subject, String content) {
        // 이메일 전송 로직만 담당
    }
}

// 개방-폐쇄 원칙 (OCP)
interface PaymentMethod {
    void processPayment(double amount);
}

class CreditCardPayment implements PaymentMethod {
    @Override
    public void processPayment(double amount) {
        System.out.println("신용카드로 " + amount + "원 결제");
    }
}

class BankTransferPayment implements PaymentMethod {
    @Override
    public void processPayment(double amount) {
        System.out.println("계좌이체로 " + amount + "원 결제");
    }
}
```

### 성능 최적화

#### 메모리 효율성
```java
// 불변 객체 활용
public final class ImmutablePoint {
    private final int x;
    private final int y;

    public ImmutablePoint(int x, int y) {
        this.x = x;
        this.y = y;
    }

    public int getX() { return x; }
    public int getY() { return y; }

    // 새로운 객체 생성하여 반환
    public ImmutablePoint move(int dx, int dy) {
        return new ImmutablePoint(x + dx, y + dy);
    }
}
```

## 참고

### OOP의 4대 특징 비교

| 특징 | 설명 | 장점 |
|------|------|------|
| **캡슐화** | 데이터와 메서드를 하나로 묶어 보호 | 데이터 무결성, 보안성 |
| **상속** | 기존 클래스를 확장하여 새로운 클래스 생성 | 코드 재사용, 계층 구조 |
| **다형성** | 같은 메서드가 다양한 방식으로 동작 | 유연성, 확장성 |
| **추상화** | 불필요한 세부사항을 숨기고 핵심 기능만 제공 | 복잡성 감소, 명확성 |

### OOP 설계 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **데이터 보호** | 캡슐화 사용 | 무결성 유지 |
| **코드 재사용** | 상속 활용 | 중복 제거 |
| **확장성** | 다형성 적용 | 유연한 설계 |
| **복잡성 관리** | 추상화 활용 | 명확한 구조 |

### 결론
객체지향 프로그래밍은 현대 소프트웨어 개발의 핵심 패러다임입니다.
캡슐화, 상속, 다형성, 추상화를 적절히 활용하여 견고한 시스템을 구축하세요.
SOLID 원칙을 준수하여 유지보수하기 쉬운 코드를 작성하세요.
OOP의 개념을 이해하고 실무에 적용하여 개발 효율성을 높이세요.

