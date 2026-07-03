---
title: Spring Bean 개념과 사용법
tags: [framework, java, spring, bean, dependency-injection, ioc]
updated: 2025-08-10
---

# Spring Bean 개념과 사용법

## 배경

Spring Framework에서 Bean은 IoC(Inversion of Control) 컨테이너가 관리하는 객체를 의미합니다. Spring은 객체의 생성, 의존성 주입, 생명주기를 관리하여 개발자가 비즈니스 로직에 집중할 수 있도록 도와줍니다.

### Spring Bean의 필요성
- **의존성 관리**: 객체 간의 의존성을 자동으로 관리
- **생명주기 관리**: 객체의 생성과 소멸을 Spring이 담당
- **싱글톤 패턴**: 기본적으로 싱글톤 스코프로 메모리 효율성 확보
- **테스트 용이성**: Mock 객체 주입을 통한 단위 테스트 지원

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
Spring Bean은 IoC 컨테이너가 관리하는 객체로, 의존성 주입을 통해 객체 간의 결합도를 낮춥니다.
생성자 주입을 우선적으로 사용하여 불변성과 테스트 용이성을 확보하세요.
Bean 스코프를 적절히 활용하여 메모리 효율성을 높이세요.
순환 의존성을 피하고, 조건부 Bean 등록을 통해 유연한 설정을 구현하세요.










