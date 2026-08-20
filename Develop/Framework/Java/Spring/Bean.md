---
title: Spring Bean 개념과 사용법
tags: [java, spring]
updated: 2025-08-10
---

# Spring Bean 개념과 사용법

## 배경

Spring Framework에서 Bean은 IoC(Inversion of Control) 컨테이너가 관리하는 객체다. 객체 생성과 의존성 주입, 생명주기까지 Spring이 맡으니 개발자는 비즈니스 로직에 집중하면 된다.

### Spring Bean의 필요성
- **의존성 관리**: 객체 간의 의존성을 자동으로 관리
- **생명주기 관리**: 객체의 생성과 소멸을 Spring이 담당
- **싱글톤 패턴**: 기본적으로 싱글톤 스코프로 메모리 효율성 확보
- **테스트 용이성**: Mock 객체를 주입한 단위 테스트 지원

### 기본 개념
- **Bean**: Spring IoC 컨테이너가 관리하는 객체
- **IoC**: 제어의 역전, 객체 생성과 의존성 주입을 Spring이 담당
- **DI**: 의존성 주입, 객체가 필요로 하는 의존성을 외부에서 제공
- **스코프**: Bean의 생명주기와 범위를 정의

## 핵심

### 1. Spring Bean의 특징

#### 기본 특징
- **Spring 컨테이너가 관리**: 객체의 생성과 소멸을 Spring이 담당
- **싱글톤 스코프**: 기본적으로 애플리케이션 전체에서 하나의 인스턴스만 생성
- **의존성 주입**: 객체가 필요로 하는 의존성을 자동으로 주입
- **생명주기 관리**: 초기화와 정리 작업을 Spring이 관리

#### Bean 생명주기
```java
@Component
public class MyBean implements InitializingBean, DisposableBean {
    
    public MyBean() {
        System.out.println("1. 생성자 호출");
    }
    
    @PostConstruct
    public void postConstruct() {
        System.out.println("2. @PostConstruct 호출");
    }
    
    @Override
    public void afterPropertiesSet() throws Exception {
        System.out.println("3. InitializingBean.afterPropertiesSet() 호출");
    }
    
    @PreDestroy
    public void preDestroy() {
        System.out.println("4. @PreDestroy 호출");
    }
    
    @Override
    public void destroy() throws Exception {
        System.out.println("5. DisposableBean.destroy() 호출");
    }
}
```

주석의 번호는 실제 호출 순서와 맞다. Spring 5.3.31 컨테이너에 그대로 올려 확인한 출력이다.

```
생성자
@PostConstruct
afterPropertiesSet
--- 컨테이너 기동 완료, 이제 close ---
@PreDestroy
DisposableBean.destroy
```

여기서 봐야 할 건 순서보다 **소멸 콜백이 언제 도는가**다. 위 출력의 `@PreDestroy` 와 `destroy` 는 `ctx.close()` 를 명시적으로 불렀기 때문에 나온 것이다. `close()` 없이 JVM 이 그냥 끝나면 **소멸 콜백은 아예 안 돈다.** 그래서 `@PreDestroy` 에 커넥션 반납이나 파일 flush 를 넣어두고 "종료 시 정리되겠지" 하면 안 된다. 웹 애플리케이션은 컨테이너가 `close()` 를 불러주지만, 배치나 `main()` 에서 띄운 컨텍스트는 직접 닫거나 `ctx.registerShutdownHook()` 을 걸어야 한다.

또 하나 — **한 클래스에 초기화 콜백을 세 방식(`@PostConstruct` / `InitializingBean` / `@Bean(initMethod=)`)이나 겹쳐 쓸 이유는 없다.** 위 예제는 순서를 보여주려는 것이고, 실제 코드에서는 `@PostConstruct` 하나로 통일한다. `InitializingBean` 을 구현하면 그 클래스가 Spring 인터페이스에 묶여 순수 자바 테스트가 번거로워진다.

### 2. Spring Bean 등록 방법

#### 자동 등록 (@Component 사용)
```java
import org.springframework.stereotype.Component;

@Component  // Spring이 자동으로 관리하는 Bean 등록
public class MyComponent {
    public void doSomething() {
        System.out.println("MyComponent 동작 중!");
    }
}
```

#### 계층별 어노테이션 사용
```java
import org.springframework.stereotype.Service;

@Service  // 비즈니스 로직을 수행하는 서비스 계층
public class UserService {
    public String getUserInfo(String userId) {
        return "사용자 정보: " + userId;
    }
}
```

```java
import org.springframework.stereotype.Repository;

@Repository  // 데이터베이스와 관련된 작업을 수행하는 Repository 계층
public class UserRepository {
    public String findUserById(String userId) {
        return "DB에서 가져온 사용자: " + userId;
    }
}
```

```java
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller  // 웹 요청을 처리하는 컨트롤러 계층
public class UserController {
    
    @GetMapping("/users")
    public String getUsers() {
        return "사용자 목록";
    }
}
```

#### 수동 등록 (@Bean 사용)
```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration  // 설정 파일임을 명시
public class AppConfig {

    @Bean  // 수동으로 Spring Bean을 등록
    public MyComponent myComponent() {
        return new MyComponent(); // 직접 객체 생성 후 반환
    }
    
    @Bean
    public DataSource dataSource() {
        // 외부 라이브러리 클래스를 Bean으로 등록할 때 유용
        return new BasicDataSource();
    }
}
```

`@Bean` 메서드 안에서 다른 `@Bean` 메서드를 **직접 호출**해도 `new` 가 두 번 되지 않는다. `@Configuration` 클래스는 CGLIB 로 프록시되어, 메서드 호출을 가로채 컨테이너의 싱글톤을 돌려준다.

```java
@Configuration
static class Cfg {
    @Bean MyBean myBean() { return new MyBean(); }
    @Bean Holder holder() { return new Holder(myBean(), myBean()); }   // 두 번 호출
}
```

```
생성자                                    ← 딱 한 번
  두 호출이 같은 인스턴스인가? true
```

여기서 `@Configuration` 을 `@Component` 로 바꾸면(또는 `@Configuration(proxyBeanMethods = false)`) 이 가로채기가 사라져 **호출할 때마다 진짜로 새 객체가 생긴다.** 같은 코드가 설정 애노테이션 하나로 정반대로 동작하는 지점이라, `@Bean` 메서드를 서로 부르는 스타일이라면 이 차이를 알고 있어야 한다. 애초에 필요한 빈을 **메서드 파라미터로 받는 편**이 프록시 유무와 무관해서 안전하다.

```java
@Bean Holder holder(MyBean myBean) { return new Holder(myBean, myBean); }   // ✓ 프록시에 의존하지 않는다
```

### 3. Spring Bean 주입 (DI, Dependency Injection)

#### 생성자 주입 (권장)
```java
@Service
public class UserService {
    private final UserRepository userRepository;
    
    // 생성자 주입 (권장 방식)
    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
    
    public String getUserInfo(String userId) {
        return userRepository.findUserById(userId);
    }
}
```

#### 필드 주입
```java
@Service
public class UserService {
    @Autowired  // 필드 주입 (권장하지 않음)
    private UserRepository userRepository;
    
    public String getUserInfo(String userId) {
        return userRepository.findUserById(userId);
    }
}
```

#### Setter 주입
```java
@Service
public class UserService {
    private UserRepository userRepository;
    
    @Autowired  // Setter 주입
    public void setUserRepository(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
    
    public String getUserInfo(String userId) {
        return userRepository.findUserById(userId);
    }
}
```

### 4. Bean 스코프

#### 기본 스코프들
```java
@Component
@Scope("singleton")  // 기본값, 애플리케이션 전체에서 하나의 인스턴스
public class SingletonBean {
    // 싱글톤 스코프
}

@Component
@Scope("prototype")  // 요청할 때마다 새로운 인스턴스 생성
public class PrototypeBean {
    // 프로토타입 스코프
}

@Component
@Scope("request")    // HTTP 요청마다 새로운 인스턴스
public class RequestBean {
    // 요청 스코프
}

@Component
@Scope("session")    // HTTP 세션마다 새로운 인스턴스
public class SessionBean {
    // 세션 스코프
}
```

#### 스코프가 다른 빈을 주입하면 주입하는 쪽의 수명이 이긴다

`@Scope("prototype")` 을 싱글톤에 주입하면 프로토타입이 아니게 된다. 주입은 싱글톤이 만들어질 때 딱 한 번 일어나기 때문이다.

```java
@Bean @Scope("prototype") Pb pb() { return new Pb(); }
@Bean Sb sb(Pb pb) { return new Sb(pb); }   // 싱글톤이 프로토타입을 들고 있다
```

```
컨테이너에서 직접 꺼낼 때: 2, 3, 4          ← 매번 새 인스턴스
싱글톤이 들고 있는 프로토타입 id: 1, 다시 봐도 1   ← 처음 것 그대로
```

(Spring 5.3.31 실측)

컨테이너에서 직접 꺼내면 `getBean` 마다 새 객체가 나오는데, 싱글톤 안에 박힌 것은 영원히 1번이다. **"프로토타입으로 선언했으니 매번 새것"이라고 믿고 상태를 담으면 그 상태가 전역으로 공유된다.** 매번 새 인스턴스가 정말 필요하면 `ObjectProvider<Pb>` 나 `@Lookup`, 혹은 `@Scope(value="prototype", proxyMode=ScopedProxyMode.TARGET_CLASS)` 를 쓴다.

`request`/`session` 스코프도 같은 문제를 더 사납게 겪는다. 싱글톤 서비스에 그냥 주입하면 **기동 시점에는 HTTP 요청이 없어서** 빈을 만들 수조차 없다. 이쪽은 스코프드 프록시가 사실상 필수다.

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```java
// Entity
@Entity
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String username;
    private String email;
    
    // 생성자, getter, setter 생략
}

// Repository
@Repository
public class UserRepository {
    @PersistenceContext
    private EntityManager em;
    
    public User findById(Long id) {
        return em.find(User.class, id);
    }
    
    public List<User> findAll() {
        return em.createQuery("SELECT u FROM User u", User.class)
                .getResultList();
    }
    
    public void save(User user) {
        em.persist(user);
    }
}

// Service
@Service
public class UserService {
    private final UserRepository userRepository;
    
    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
    
    public User getUserById(Long id) {
        return userRepository.findById(id);
    }
    
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }
    
    public void createUser(User user) {
        userRepository.save(user);
    }
}

// Controller
@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;
    
    public UserController(UserService userService) {
        this.userService = userService;
    }
    
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.getUserById(id);
    }
    
    @GetMapping
    public List<User> getAllUsers() {
        return userService.getAllUsers();
    }
    
    @PostMapping
    public void createUser(@RequestBody User user) {
        userService.createUser(user);
    }
}
```

### 2. 고급 패턴

#### 조건부 Bean 등록
```java
@Configuration
public class DatabaseConfig {
    
    @Bean
    @ConditionalOnProperty(name = "database.type", havingValue = "mysql")
    public DataSource mysqlDataSource() {
        return new MysqlDataSource();
    }
    
    @Bean
    @ConditionalOnProperty(name = "database.type", havingValue = "postgresql")
    public DataSource postgresqlDataSource() {
        return new PostgresqlDataSource();
    }
    
    @Bean
    @ConditionalOnMissingBean(DataSource.class)
    public DataSource defaultDataSource() {
        return new H2DataSource();
    }
}
```

#### Bean 팩토리 패턴
```java
@Component
public class PaymentProcessorFactory {
    
    private final Map<String, PaymentProcessor> processors;
    
    public PaymentProcessorFactory(List<PaymentProcessor> processorList) {
        processors = processorList.stream()
                .collect(Collectors.toMap(
                    PaymentProcessor::getType,
                    processor -> processor
                ));
    }
    
    public PaymentProcessor getProcessor(String type) {
        return processors.get(type);
    }
}

@Component
public class CreditCardProcessor implements PaymentProcessor {
    @Override
    public String getType() {
        return "credit";
    }
    
    @Override
    public void processPayment(double amount) {
        System.out.println("신용카드로 " + amount + "원 결제");
    }
}

@Component
public class BankTransferProcessor implements PaymentProcessor {
    @Override
    public String getType() {
        return "transfer";
    }
    
    @Override
    public void processPayment(double amount) {
        System.out.println("계좌이체로 " + amount + "원 결제");
    }
}
```

이 팩토리 패턴은 구현체를 하나 더 붙일 때 조용히 깨진다. `Collectors.toMap` 은 **키가 겹치면 예외를 던진다.**

```
java.lang.IllegalStateException: Duplicate key credit
  (attempted merging values CreditCardProcessor and AnotherCreditProcessor)
```

`getType()` 이 같은 구현체를 둘 만드는 순간(오타든, 복사해서 만들다 안 고쳤든) **애플리케이션이 기동 자체를 못 한다.** 메시지에 클래스 이름이 나오는 건 `toString()` 을 재정의했을 때뿐이라, 보통은 `com.example.Xxx@1a2b3c` 두 개를 보고 어느 쪽인지 헤맨다. 어느 쪽을 이기게 할지 정해서 3번째 인자를 주거나, 중복을 진짜 오류로 취급하려면 예외 메시지에 타입 이름이 남게 만든다.

```java
processors = processorList.stream().collect(Collectors.toMap(
    PaymentProcessor::getType,
    p -> p,
    (a, b) -> { throw new IllegalStateException(
        "결제 타입 중복: " + a.getType() + " → " + a.getClass() + ", " + b.getClass()); }));
```

반대편 함정도 있다. `getProcessor(type)` 은 **없는 타입에 `null` 을 반환한다.**

```
빈 목록 → {} / getProcessor("credit") → null
```

구현체를 담은 모듈이 컴포넌트 스캔 범위 밖이면 리스트가 비어도 기동은 성공하고, 결제 시점에 `NullPointerException` 이 난다. 기동 시 등록된 타입을 로그로 찍고, 조회 실패는 `Optional` 이나 명시적 예외로 드러낸다.

## 운영 팁

### 성능 최적화

#### Lazy Loading 활용
```java
@Component
@Lazy  // 필요할 때까지 Bean 생성 지연
public class ExpensiveBean {
    public ExpensiveBean() {
        // 초기화에 시간이 오래 걸리는 작업
        System.out.println("ExpensiveBean 초기화 중...");
    }
}

@Service
public class UserService {
    private final ExpensiveBean expensiveBean;
    
    public UserService(@Lazy ExpensiveBean expensiveBean) {
        this.expensiveBean = expensiveBean;
    }
    
    public void useExpensiveBean() {
        // 실제로 사용할 때 Bean이 생성됨
        expensiveBean.doSomething();
    }
}
```

### 에러 처리

#### Bean 생성 실패 처리
```java
@Configuration
public class AppConfig {
    
    @Bean
    public DataSource dataSource() {
        try {
            BasicDataSource dataSource = new BasicDataSource();
            dataSource.setUrl("jdbc:mysql://localhost:3306/mydb");
            dataSource.setUsername("user");
            dataSource.setPassword("password");
            return dataSource;
        } catch (Exception e) {
            throw new BeanCreationException("DataSource 생성 실패", e);
        }
    }
}
```

### 주의사항

#### 순환 의존성 방지
```java
// 잘못된 예: 순환 의존성
@Service
public class ServiceA {
    private final ServiceB serviceB;
    
    public ServiceA(ServiceB serviceB) {
        this.serviceB = serviceB;
    }
}

@Service
public class ServiceB {
    private final ServiceA serviceA;
    
    public ServiceB(ServiceA serviceA) {
        this.serviceA = serviceA;
    }
}

// 올바른 예: 인터페이스 분리
@Service
public class ServiceA {
    private final ServiceB serviceB;
    
    public ServiceA(ServiceB serviceB) {
        this.serviceB = serviceB;
    }
}

@Service
public class ServiceB {
    // ServiceA에 직접 의존하지 않음
    public void doSomething() {
        // 독립적인 로직
    }
}
```

순환 의존성에서 알아야 할 건 "피해야 한다"보다 **주입 방식에 따라 결과가 정반대**라는 사실이다. 같은 순환을 생성자 주입과 필드 주입으로 각각 만들어 돌려보면:

```
생성자 주입 순환 → UnsatisfiedDependencyException / 최종 원인: BeanCurrentlyInCreationException
필드 주입 순환: 기동 성공, a.b.a == a ? true
```

(Spring 5.3.31 실측)

**생성자 주입은 기동을 실패시키고, 필드 주입은 아무 일 없다는 듯 성공한다.** 필드 주입은 객체를 먼저 만들고 나중에 필드를 채우는 방식이라 순환을 만들어낼 수 있기 때문이다.

그래서 아래 표의 "필드 주입 단점: 순환 의존성"은 정확히는 **순환 의존성을 만들어도 안 걸린다**는 뜻이다. 설계가 꼬여 있다는 신호를 컨테이너가 기동 실패로 알려주는 게 생성자 주입의 값이다. 순환을 못 만드는 게 아니라, 만들면 즉시 알려준다.

Spring Boot 는 2.6.0 에서 이 구멍을 막았다. 각 버전의 `spring-configuration-metadata.json` 을 직접 열어보면 확인된다.

```
# spring-boot-2.5.7.jar → allow-circular-references 검색 결과: 0건
# spring-boot-2.6.0.jar →
{ "name": "spring.main.allow-circular-references",
  "type": "java.lang.Boolean",
  "defaultValue": false }
```

기본값이 `false` 라 2.6 이상에서는 필드 주입이어도 순환이 있으면 기동이 실패한다. 버전을 올리다 여기서 막히면 `spring.main.allow-circular-references=true` 로 되돌릴 수 있지만, 그건 유예지 해결이 아니다.

## 참고

### Bean 등록 방법 비교

| 방법 | 장점 | 단점 | 사용 시기 |
|------|------|------|-----------|
| **@Component** | 간편함, 자동 스캔 | 세밀한 제어 어려움 | 일반적인 컴포넌트 |
| **@Bean** | 세밀한 제어 가능 | 코드 복잡성 증가 | 외부 라이브러리, 설정 |
| **@Configuration** | 설정 그룹화 | 클래스 수 증가 | 관련 설정 모음 |

### 의존성 주입 방식 비교

| 방식 | 장점 | 단점 | 권장도 |
|------|------|------|--------|
| **생성자 주입** | 불변성, 필수 의존성 보장 | 매개변수 많을 때 복잡 | ⭐⭐⭐⭐⭐ |
| **Setter 주입** | 선택적 의존성, 런타임 변경 | 불변성 보장 안됨 | ⭐⭐⭐ |
| **필드 주입** | 간편함 | 테스트 어려움, 순환 의존성 | ⭐⭐ |

### 결론
Spring Bean은 IoC 컨테이너가 관리하는 객체고, 의존성 주입으로 객체 간의 결합도를 낮춘다.
생성자 주입을 먼저 쓰면 불변성과 테스트 용이성을 같이 얻는다.
Bean 스코프를 상황에 맞게 골라 쓰면 메모리를 아낀다.
순환 의존성은 피하고, 설정을 유연하게 가져가려면 조건부 Bean 등록을 쓴다.










