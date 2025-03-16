
# 🌱 Spring Bean 개념과 예제

## 1. Spring Bean이란?

Spring에서 **Bean(빈)** 이란, **Spring IoC(Inversion of Control) 컨테이너가 관리하는 객체**를 의미합니다.

- 일반적으로 **@Component**, **@Service**, **@Repository**, **@Controller** 같은 어노테이션을 사용하여 선언하면 Spring이 자동으로 관리합니다.
- 또는 **@Bean** 어노테이션을 사용하여 수동으로 등록할 수도 있습니다.

## 2. Spring Bean의 특징

✅ **Spring 컨테이너가 관리한다**  
✅ **싱글톤(Singleton) 스코프가 기본값이다**  
✅ **객체의 생성과 소멸을 Spring이 담당한다**

---

## 3. Spring Bean 등록 방법

### 👉🏻 1) 자동 등록 (@Component 사용)

```java
import org.springframework.stereotype.Component;

@Component  // Spring이 자동으로 관리하는 Bean 등록
public class MyComponent {
    public void doSomething() {
        System.out.println("MyComponent 동작 중!");
    }
}
```

**✔️ 설명**
- `@Component` 어노테이션을 붙이면, Spring이 자동으로 객체를 생성하고 관리합니다.
- 이 객체는 필요할 때 `@Autowired`를 사용하여 주입할 수 있습니다.

---

### 👉🏻 2) 자동 등록 (@Service, @Repository 사용)

```java
import org.springframework.stereotype.Service;

@Service  // 비즈니스 로직을 수행하는 서비스 계층
public class MyService {
    public String getMessage() {
        return "Hello, Spring Bean!";
    }
}
```

```java
import org.springframework.stereotype.Repository;

@Repository  // 데이터베이스와 관련된 작업을 수행하는 Repository 계층
public class MyRepository {
    public String getData() {
        return "DB에서 가져온 데이터";
    }
}
```

**✔️ 설명**
- `@Service`: 서비스 계층에서 사용. 비즈니스 로직을 수행하는 클래스에 붙임.
- `@Repository`: 데이터 계층에서 사용. 데이터베이스와 직접 연결되는 클래스에 붙임.

---

### 👉🏻 3) 수동 등록 (@Bean 사용)

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration  // 설정 파일임을 명시
public class AppConfig {

    @Bean  // 수동으로 Spring Bean을 등록
    public MyComponent myComponent() {
        return new MyComponent(); // 직접 객체 생성 후 반환
    }
}
```

**✔️ 설명**
- `@Configuration` 클래스 내부에서 `@Bean`을 사용하여 Bean을 등록할 수 있습니다.
- `@Component` 방식과 다르게, 직접 객체를 생성하여 반환하는 방식입니다.

---

## 4. Spring Bean 주입 (DI, Dependency Injection)

Spring에서 **의존성 주입(DI, Dependency Injection)** 을 사용하여 Bean을 다른 객체에 주입할 수 있습니다.

### ✨ 1) 필드 주입 (Field Injection)

```java
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class MyService {

    @Autowired  // MyRepository 빈을 자동으로 주입
    private MyRepository myRepository;

    public String getData() {
        return myRepository.getData();
    }
}
```

✔️ **문제점**: 필드 주입 방식은 `final` 키워드를 사용할 수 없고, 테스트가 어려워지므로 **권장되지 않습니다.**

---

### ✨ 2) 생성자 주입 (Constructor Injection) - **권장 방식**

```java
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class MyService {

    private final MyRepository myRepository;

    @Autowired  // Spring이 MyRepository를 자동으로 주입
    public MyService(MyRepository myRepository) {
        this.myRepository = myRepository;
    }

    public String getData() {
        return myRepository.getData();
    }
}
```

✔️ **장점**:
- **불변성 유지 가능** (final 키워드 사용 가능)
- **테스트가 용이** (의존성을 명확히 주입할 수 있음)

---

## 5. Bean 스코프 (Scope) 설정

Spring Bean의 기본 스코프는 **싱글톤(Singleton)** 입니다. 하지만 필요에 따라 다른 스코프를 지정할 수 있습니다.

### 👉🏻 Singleton (기본값)

```java
import org.springframework.stereotype.Component;

@Component
public class SingletonBean {
    public SingletonBean() {
        System.out.println("SingletonBean 생성됨!");
    }
}
```

- **한 번만 생성**되며, 모든 곳에서 동일한 인스턴스를 공유함.

---

### 👉🏻 Prototype (매번 새 객체 생성)

```java
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

@Component
@Scope("prototype")  // 매번 새로운 인스턴스 생성
public class PrototypeBean {
    public PrototypeBean() {
        System.out.println("PrototypeBean 생성됨!");
    }
}
```

- **매번 새로운 객체가 생성**됨.

---

## 6. Spring Bean의 생명주기

Spring Bean은 특정한 **생명주기(Lifecycle)** 를 가집니다.

1️⃣ 객체 생성  
2️⃣ 의존성 주입 (Dependency Injection)  
3️⃣ 초기화 (Initializing)  
4️⃣ 사용  
5️⃣ 소멸 (Destroying)

### 👉🏻 초기화 & 소멸 메서드 설정

```java
import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import org.springframework.stereotype.Component;

@Component
public class LifeCycleBean {

    @PostConstruct // 빈이 생성된 후 실행됨
    public void init() {
        System.out.println("Bean 초기화됨!");
    }

    @PreDestroy // 빈이 제거되기 전에 실행됨
    public void destroy() {
        System.out.println("Bean 소멸됨!");
    }
}
```

✔️ **설명**
- `@PostConstruct`: Bean이 생성된 후 자동 실행
- `@PreDestroy`: Bean이 제거되기 전에 자동 실행

