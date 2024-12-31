
# Java - 의존성 주입 (Dependency Injection)

**의존성 주입(Dependency Injection, DI)**은 객체 지향 프로그래밍에서 객체 간의 의존성을 외부에서 주입하는 설계 패턴입니다. DI는 코드의 유연성과 재사용성을 높이고, 테스트를 용이하게 합니다.

## DI의 핵심 개념

1. **의존성(Dependency)**: 객체가 다른 객체를 사용하는 관계.
2. **주입(Injection)**: 필요한 의존성을 외부에서 제공하는 행위.

DI를 사용하면 객체가 스스로 의존성을 생성하지 않고, 외부에서 전달받기 때문에 **느슨한 결합(Loose Coupling)**을 실현할 수 있습니다.

## DI를 구현하는 방법

1. **생성자 주입(Constructor Injection)**
2. **세터 주입(Setter Injection)**
3. **필드 주입(Field Injection)**

## 예제 코드

### 1. 생성자 주입

```java
// 의존성 클래스
class Engine {
    public void start() {
        System.out.println("Engine started.");
    }
}

// 주입 대상 클래스
class Car {
    private final Engine engine;

    // 생성자를 통해 의존성을 주입
    public Car(Engine engine) {
        this.engine = engine;
    }

    public void drive() {
        engine.start();
        System.out.println("Car is driving.");
    }
}

// Main 클래스
public class Main {
    public static void main(String[] args) {
        Engine engine = new Engine(); // 의존성 생성
        Car car = new Car(engine);    // 의존성 주입
        car.drive();
    }
}
```

### 2. 세터 주입

```java
class Car {
    private Engine engine;

    // 세터 메서드를 통해 의존성을 주입
    public void setEngine(Engine engine) {
        this.engine = engine;
    }

    public void drive() {
        engine.start();
        System.out.println("Car is driving.");
    }
}

public class Main {
    public static void main(String[] args) {
        Engine engine = new Engine();
        Car car = new Car();
        car.setEngine(engine); // 의존성 주입
        car.drive();
    }
}
```

### 3. 필드 주입

Spring 프레임워크에서 주로 사용되며, `@Autowired` 애노테이션을 활용합니다.

```java
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
class Engine {
    public void start() {
        System.out.println("Engine started.");
    }
}

@Component
class Car {
    @Autowired // 필드에 직접 의존성 주입
    private Engine engine;

    public void drive() {
        engine.start();
        System.out.println("Car is driving.");
    }
}
```

### Spring Framework에서 DI 예제

Spring 컨테이너는 의존성을 자동으로 관리해줍니다.

#### 설정 클래스

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
class AppConfig {
    @Bean
    public Engine engine() {
        return new Engine();
    }

    @Bean
    public Car car(Engine engine) {
        return new Car(engine);
    }
}
```

#### Main 클래스

```java
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

public class Main {
    public static void main(String[] args) {
        ApplicationContext context = new AnnotationConfigApplicationContext(AppConfig.class);
        Car car = context.getBean(Car.class);
        car.drive();
    }
}
```

## DI의 장점

1. **유연성**: 객체 간의 결합도를 낮추고, 객체 교체 및 확장이 용이.
2. **테스트 용이성**: 의존성을 쉽게 교체할 수 있어 단위 테스트 작성이 간편.
3. **재사용성 증가**: 객체를 재사용 가능하게 만들어 코드 중복 감소.

## DI의 단점

1. **초기 설정 비용**: DI 컨테이너(Spring 등)를 사용하는 경우 설정이 복잡할 수 있음.
2. **학습 곡선**: DI 개념 및 프레임워크를 이해하는 데 시간이 필요.

## 결론

의존성 주입은 객체 간의 결합도를 낮추어 확장성과 유지보수성을 높이는 중요한 설계 패턴입니다. Java에서는 Spring과 같은 프레임워크를 사용하여 DI를 쉽게 구현할 수 있습니다.
