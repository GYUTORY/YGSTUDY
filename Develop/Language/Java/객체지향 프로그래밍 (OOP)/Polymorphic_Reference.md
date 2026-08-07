---
title: "다형적 참조 (Polymorphic Reference)"
tags: [java, polymorphism, dynamic-dispatch, upcasting, interface, abstract-class, repository-pattern, strategy-pattern, instanceof]
updated: 2026-07-30
---

# 다형적 참조 (Polymorphic Reference)

## 참조 변수에 담긴 두 가지 타입 정보

Java에서 변수 선언은 두 가지 타입 정보를 가진다.

- **컴파일 타임 타입(선언 타입)**: 변수 앞에 쓴 타입. 컴파일러가 어떤 멤버에 접근 가능한지 판단하는 기준이다.
- **런타임 타입(실제 타입)**: `new`로 생성한 객체의 실제 클래스. JVM이 어떤 메서드를 실행할지 결정하는 기준이다.

```java
Animal animal = new Dog();
//  ↑ 컴파일 타임 타입    ↑ 런타임 타입
```

`animal.eat()`를 호출하면 컴파일러는 `Animal`에 `eat()`이 선언되어 있는지 확인하고, 실제 실행 시에는 JVM이 `Dog`의 `eat()`를 호출한다. 이 두 단계가 분리되어 있다는 게 다형적 참조의 핵심이다.

업캐스팅 문법 자체는 [Type_Casting.md](../Java%20기본%20개념/Type_Casting.md)에서 다루고 있다. 여기서는 "왜 상위 타입 참조를 써야 하는가"와 그 동작 방식에 집중한다.

---

## 동적 디스패치

인스턴스 메서드 호출이 런타임 타입에 따라 결정되는 메커니즘이다. 오버라이딩된 메서드는 참조 변수 타입이 아니라 실제 객체 타입을 기준으로 호출된다.

```java
class Animal {
    String name = "Animal";

    void sound() {
        System.out.println("...");
    }

    static void type() {
        System.out.println("Animal static");
    }
}

class Dog extends Animal {
    String name = "Dog";  // 필드 숨김

    @Override
    void sound() {
        System.out.println("woof");
    }

    static void type() {
        System.out.println("Dog static");  // 메서드 숨김
    }
}

Animal animal = new Dog();

animal.sound();        // "woof" — 동적 디스패치, Dog의 메서드 호출
System.out.println(animal.name);  // "Animal" — 필드는 컴파일 타임 타입 기준
animal.type();         // "Animal static" — 정적 메서드는 참조 타입 기준
```

`sound()`는 오버라이딩이라 런타임 타입이 적용되지만, 필드 `name`과 정적 메서드 `type()`은 컴파일 타임 타입을 따른다. 이 차이를 모르고 있으면 예상치 못한 결과를 만나게 된다.

JVM 내부적으로는 vtable(virtual method table)로 동적 디스패치가 구현된다. 각 클래스는 오버라이딩한 메서드의 주소를 vtable에 저장하고, 호출 시 런타임 타입의 vtable을 조회해서 실행한다. `final` 메서드나 `private` 메서드는 vtable에 올라가지 않고 정적 바인딩된다.

오버라이딩 규칙 자체는 [Override과 Overriding.md](Override과%20Overriding.md)에서 다룬다.

---

## 오버로딩 vs 오버라이딩 — 결정 시점이 다르다

오버라이딩은 런타임에 결정되지만 오버로딩은 컴파일 타임에 결정된다. 이 차이가 헷갈리는 경우가 있다.

```java
class Printer {
    void print(Animal a) { System.out.println("Animal"); }
    void print(Dog d)    { System.out.println("Dog"); }
}

Printer printer = new Printer();
Animal animal = new Dog();

printer.print(animal);  // "Animal" — 오버로딩 해석은 컴파일 타임 타입 기준
```

`animal`의 런타임 타입은 `Dog`이지만, `print()` 오버로딩 선택은 컴파일 타임 타입인 `Animal`을 기준으로 한다. 그래서 `print(Animal a)`가 호출된다. 런타임 타입이 `Dog`여도 `print(Dog d)`가 호출되지 않는다.

```java
// 오버라이딩은 런타임 타입 기준
class Animal {
    void describe() { System.out.println("I am Animal"); }
}
class Dog extends Animal {
    @Override
    void describe() { System.out.println("I am Dog"); }
}

Animal a = new Dog();
a.describe();  // "I am Dog" — 오버라이딩은 런타임 타입 기준
```

오버로딩과 오버라이딩이 함께 쓰이면 더 복잡해지는데, 구분 기준은 단순하다. 메서드 선택이 어느 시점에 일어나는가다.

---

## 인터페이스와 추상 클래스 참조

추상 클래스나 인터페이스는 직접 인스턴스를 만들 수 없지만, 참조 변수 타입으로는 쓸 수 있다. 구현체를 상위 타입 참조 변수에 담는 것이 다형적 참조의 일반적인 형태다.

```java
interface Drawable {
    void draw();
}

abstract class Shape {
    abstract double area();
}

class Circle extends Shape implements Drawable {
    @Override
    public void draw() { System.out.println("원 그리기"); }

    @Override
    public double area() { return Math.PI * radius * radius; }
    
    private double radius;
    public Circle(double radius) { this.radius = radius; }
}

Drawable drawable = new Circle(5.0);  // 인터페이스 참조
drawable.draw();

Shape shape = new Circle(5.0);        // 추상 클래스 참조
shape.area();
```

인터페이스 참조와 추상 클래스 참조 모두 동적 디스패치가 일어난다. 참조 타입의 성격이 다를 뿐이다. 인터페이스는 "무엇을 할 수 있는가"(능력), 추상 클래스는 "무엇인가"(정체성)에 가깝다. 실무에서는 유연성 때문에 인터페이스 참조를 더 많이 쓴다.

---

## 다형적 컬렉션

같은 상위 타입을 가진 객체들을 하나의 컬렉션에 담을 수 있다.

```java
List<Animal> animals = new ArrayList<>();
animals.add(new Dog());
animals.add(new Cat());
animals.add(new Bird());

for (Animal animal : animals) {
    animal.sound();  // 각각 Dog, Cat, Bird의 sound() 호출
}
```

`List<Animal>`에 하위 타입 객체를 담고 순회하면 각 객체의 실제 타입에 맞는 메서드가 호출된다. 타입마다 분기를 쓸 필요가 없다.

이 방식이 깔끔하게 작동하려면 상위 타입에 적절한 메서드가 선언되어 있어야 한다. `Animal`에 `sound()`가 없다면 컬렉션을 순회하면서 각 타입의 고유 메서드를 호출할 수 없다. 그 경우 설계를 다시 봐야 한다.

---

## 실무에서 자주 쓰는 패턴

### Repository 인터페이스

Spring에서 가장 흔하게 보는 다형적 참조 패턴이다.

```java
public interface UserRepository {
    User findById(Long id);
    void save(User user);
}

@Repository
public class JpaUserRepository implements UserRepository {
    @PersistenceContext
    private EntityManager em;

    @Override
    public User findById(Long id) {
        return em.find(User.class, id);
    }

    @Override
    public void save(User user) {
        em.persist(user);
    }
}

@Service
public class UserService {
    private final UserRepository repository;  // 컴파일 타임: UserRepository

    public UserService(UserRepository repository) {
        this.repository = repository;  // 런타임: JpaUserRepository
    }

    public User getUser(Long id) {
        return repository.findById(id);  // 실제 구현체의 메서드 호출
    }
}
```

`UserService`는 `UserRepository` 인터페이스만 의존한다. `JpaUserRepository`에서 `MongoUserRepository`로 교체해도 서비스 코드를 건드리지 않아도 된다. 테스트 시에는 가짜 구현체를 주입하면 된다.

이 패턴이 작동하는 근거가 다형적 참조다. 컴파일 타임에는 `UserRepository`의 메서드만 알고, 런타임에는 실제 주입된 구현체의 메서드가 호출된다.

### 전략 패턴

런타임에 알고리즘을 교체해야 할 때 쓴다.

```java
public interface DiscountPolicy {
    int discount(int price);
}

public class RateDiscountPolicy implements DiscountPolicy {
    private static final int DISCOUNT_RATE = 10;

    @Override
    public int discount(int price) {
        return price * DISCOUNT_RATE / 100;
    }
}

public class FixDiscountPolicy implements DiscountPolicy {
    private static final int DISCOUNT_AMOUNT = 1000;

    @Override
    public int discount(int price) {
        return DISCOUNT_AMOUNT;
    }
}

public class OrderService {
    private final DiscountPolicy discountPolicy;

    public OrderService(DiscountPolicy discountPolicy) {
        this.discountPolicy = discountPolicy;
    }

    public int calculatePrice(int originalPrice) {
        return originalPrice - discountPolicy.discount(originalPrice);
    }
}
```

`OrderService`는 어떤 할인 정책이 들어올지 모른다. `discountPolicy.discount()` 호출 시 런타임에 실제 타입이 결정된다. 새로운 할인 정책이 생겨도 기존 코드를 수정하지 않고 구현체만 추가하면 된다.

---

## 상위 타입 참조로 하위 타입 고유 메서드에 접근할 때

상위 타입 참조로는 하위 타입에만 있는 메서드를 바로 호출할 수 없다.

```java
Animal animal = new Dog();
animal.bark();  // 컴파일 에러 — Animal에 bark() 없음
```

다운캐스팅이나 `instanceof` 분기로 해결하는데, 선택 기준은 실제 타입을 얼마나 확신하느냐다.

다운캐스팅은 실제 타입을 확실히 알 때 쓴다. 잘못된 타입으로 캐스팅하면 `ClassCastException`이 런타임에 발생한다. 다운캐스팅 문법은 [Type_Casting.md](../Java%20기본%20개념/Type_Casting.md)를 참고한다.

`instanceof` 분기는 실제 타입을 모를 때 쓴다.

```java
void processAnimal(Animal animal) {
    if (animal instanceof Dog dog) {
        dog.bark();
    } else if (animal instanceof Cat cat) {
        cat.meow();
    }
}
```

Java 16+의 패턴 매칭 `instanceof`는 캐스팅과 변수 선언을 동시에 처리한다. 기존 방식(`instanceof` 확인 → 명시적 캐스팅)보다 실수가 줄어든다.

`instanceof` 분기가 여러 곳에 반복된다면 설계를 다시 봐야 한다. 하위 타입마다 다른 동작이 필요하다면 상위 타입에 추상 메서드로 올리는 게 낫다. 타입 분기는 새로운 하위 타입이 추가될 때 분기가 있는 곳을 모두 찾아서 고쳐야 하는 부담이 있다.

```java
// instanceof 분기가 반복될 때의 대안
abstract class Animal {
    abstract void makeSound();
    abstract void performAction();  // 하위 타입 고유 동작을 추상 메서드로
}

class Dog extends Animal {
    @Override
    void makeSound() { System.out.println("woof"); }

    @Override
    void performAction() { System.out.println("공 물어오기"); }
}

class Cat extends Animal {
    @Override
    void makeSound() { System.out.println("meow"); }

    @Override
    void performAction() { System.out.println("그루밍"); }
}
```

단, 외부 라이브러리 타입이나 레거시 코드처럼 상위 타입을 수정할 수 없는 경우에는 `instanceof` 분기가 불가피하다. 그럴 때는 분기를 한 곳에 모아두는 게 유지보수하기 낫다.

---

## 참조 타입이 중요한 이유

코드를 구체적인 타입에 묶어두면 변경할 때 파급 범위가 커진다. `JpaUserRepository`에 직접 의존하는 코드가 10군데 있으면, 구현체를 바꿀 때 10군데를 모두 수정해야 한다. `UserRepository` 인터페이스에 의존하면 주입 지점 하나만 바꾸면 된다.

테스트 측면에서도 마찬가지다. 구체적인 타입에 의존하면 실제 DB나 외부 API가 있어야 테스트를 돌릴 수 있다. 인터페이스에 의존하면 가짜 구현체를 끼워 넣고 독립적으로 테스트할 수 있다.

컴파일 타임 타입을 인터페이스나 추상 클래스로 선언하는 것 자체가 "나는 이 타입의 계약만 알아야 한다"는 선언이다. 구현 세부사항을 모르기 때문에 나중에 구현체를 바꿔도 영향을 받지 않는다.
