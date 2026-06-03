---
title: Spring Lombok 심화
tags: [framework, java, spring, lombok, annotation-processor, jpa]
updated: 2026-06-03
---

# Spring Lombok 심화

기본 어노테이션 사용법은 [Lombok.md](Lombok.md)에서 다뤘다. 이 문서는 Lombok이 실제로 어떻게 동작하는지, 그리고 실무에서 자주 만나는 버그와 잘못된 사용 패턴을 정리한다.

## 1. Lombok이 컴파일 시점에 동작하는 원리

Lombok은 런타임 리플렉션을 쓰지 않는다. javac가 컴파일하는 도중에 끼어들어 AST(Abstract Syntax Tree)를 조작한다. 이 동작이 Lombok을 이해하는 출발점이다.

### 1.1 Annotation Processor와 javac plugin

표준 JSR 269 Annotation Processor는 새로운 클래스 파일을 생성할 수만 있다. 이미 존재하는 클래스의 메서드를 추가하지는 못한다. Lombok은 이 제약을 우회하려고 javac 내부 API를 직접 호출한다.

`lombok.javac.JavacAnnotationHandler`가 진입점이다. javac가 어노테이션을 발견하면 Lombok의 핸들러를 호출하는데, 이 시점에 핸들러는 `com.sun.tools.javac.tree.JCTree` 객체를 직접 수정해서 메서드 노드를 끼워 넣는다. Eclipse의 ECJ에도 동일한 작업을 하는 별도 핸들러가 있다(`lombok.eclipse.EclipseAnnotationHandler`).

```
javac 시작
  ↓
.java 파싱 → AST 생성
  ↓
Annotation Processor 라운드 시작
  ↓
Lombok이 JavacAnnotationHandler로 끼어들어 AST에 직접 메서드 노드 삽입
  ↓
타입 검증 → .class 생성
```

표준 API만으로는 불가능한 작업이라서, Lombok은 `--add-opens` 같은 JDK 내부 모듈 접근을 요구하는 경우가 생긴다. Java 17 이후 환경에서 빌드가 깨지는 원인 중 하나가 이것이다.

### 1.2 delombok으로 본 실제 결과물

`@Data`가 붙은 클래스가 실제로 어떤 코드로 변환되는지 보려면 `delombok` 태스크를 쓴다. Gradle에서는 `io.freefair.lombok` 플러그인의 `delombok` 태스크가 있다.

```java
@Data
public class User {
    private Long id;
    private String name;
}
```

이 코드는 javac 단계에서 다음과 같이 확장된다.

```java
public class User {
    private Long id;
    private String name;

    public User() {}

    public Long getId() { return this.id; }
    public String getName() { return this.name; }
    public void setId(Long id) { this.id = id; }
    public void setName(String name) { this.name = name; }

    public boolean equals(final Object o) {
        if (o == this) return true;
        if (!(o instanceof User)) return false;
        final User other = (User) o;
        if (!other.canEqual(this)) return false;
        // ... id, name 비교
    }

    public int hashCode() { /* ... */ }
    public String toString() { /* ... */ }
    protected boolean canEqual(final Object other) { return other instanceof User; }
}
```

`canEqual` 메서드가 자동으로 생성되는데, 상속 관계에서 `equals` 비교가 깨지지 않도록 하는 가드다. 이게 있어서 Lombok이 만든 `equals`는 상속해도 대체로 안전하다. 하지만 JPA Entity처럼 프록시가 끼면 이야기가 달라진다.

## 2. @EqualsAndHashCode와 JPA Entity 충돌

JPA Entity에 `@Data`나 `@EqualsAndHashCode`를 무심코 붙이면 거의 반드시 사고가 난다.

### 2.1 Lazy 프록시 비교에서 LazyInitializationException

`@OneToMany`, `@ManyToOne` 관계는 기본이 Lazy 로딩이다. 이 상태에서 `equals`나 `hashCode`가 연관 컬렉션을 건드리면 영속성 컨텍스트 밖에서 `LazyInitializationException`이 터진다.

```java
@Entity
@Getter
@EqualsAndHashCode  // 모든 필드 포함 — 위험
public class Order {
    @Id
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private User user;

    @OneToMany(mappedBy = "order")
    private List<OrderItem> items = new ArrayList<>();
}
```

`order1.equals(order2)`를 호출하는 순간 `user`와 `items`까지 모두 비교하려고 한다. 트랜잭션이 끝난 뒤 컨트롤러에서 비교하면 예외가 터진다. 이걸 막으려면 ID만 비교하도록 강제해야 한다.

```java
@Entity
@Getter
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Order {
    @Id
    @EqualsAndHashCode.Include
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    private User user;
}
```

`onlyExplicitlyIncluded = true`로 잡고, `@EqualsAndHashCode.Include`를 명시한 필드만 비교한다. JPA Entity에서는 사실상 이 패턴이 표준이다.

### 2.2 ID 기반 비교의 함정

ID만 비교한다고 끝이 아니다. ID는 `persist` 호출 전에는 `null`이다. `@GeneratedValue(strategy = IDENTITY)`라면 INSERT 시점까지 ID가 안 잡힌다. 영속화 전 객체를 `HashSet`에 넣었다가 `persist` 호출 후 다시 찾으면 못 찾는다. `hashCode`가 `null` 기반에서 ID 기반으로 바뀌었기 때문이다.

```java
Set<Order> orders = new HashSet<>();
Order order = new Order();
orders.add(order);          // hashCode 는 null 기반
entityManager.persist(order);  // id 생성됨
orders.contains(order);     // false — hashCode 가 바뀌어버림
```

이 동작 때문에 일부는 UUID를 클라이언트에서 생성해서 영속화 전에 ID를 확정해버리는 방식을 쓴다. Hibernate `IDENTITY` 전략을 쓰는 한 이 문제는 피할 수 없다.

### 2.3 Hibernate 프록시 unwrap

`getReference()`나 Lazy 연관관계로 가져온 객체는 실제 Entity가 아니라 Hibernate가 만든 프록시다. `actualOrder.equals(proxyOrder)`가 false로 나오는 경우가 있다. Lombok이 만든 `equals`는 `instanceof Order`로 타입을 체크하는데, 프록시는 `Order$HibernateProxy$xyz`라는 서브클래스라서 통과하긴 한다. 그러나 `getClass()`로 비교하는 코드라면 깨진다.

`Hibernate.unproxy(proxy)`로 실제 객체를 꺼내서 비교하거나, `equals` 자체를 ID 기반으로 단순화해야 한다.

## 3. @Builder의 함정

`@Builder`는 자주 쓰지만 함정도 많다.

### 3.1 @Builder.Default 누락

필드에 직접 초기값을 줘도 빌더는 이걸 무시한다.

```java
@Builder
public class Config {
    private List<String> tags = new ArrayList<>();  // 빌더가 무시
    private int timeout = 30;                        // 빌더가 무시
}

Config c = Config.builder().build();
// c.tags == null, c.timeout == 0
```

`build()` 결과는 `tags`가 `null`, `timeout`이 0이다. 빌더는 필드 초기화 코드를 보지 않고 자기 내부 변수만 본다. 명시적으로 `@Builder.Default`를 붙여야 초기값을 인식한다.

```java
@Builder
public class Config {
    @Builder.Default
    private List<String> tags = new ArrayList<>();
    @Builder.Default
    private int timeout = 30;
}
```

이걸 모르고 운영에 배포했다가 `NullPointerException`이 폭발하는 사고가 흔하다. 실무에서는 컴파일러 경고를 켜둬도 잡히지 않으니, 코드 리뷰에서 손으로 확인하는 수밖에 없다.

### 3.2 상속과 @SuperBuilder

클래스에 `@Builder`를 붙이면 해당 클래스의 빌더만 생긴다. 부모 필드를 자식 빌더에서 설정할 수 없다.

```java
@Getter
@Builder
public class Animal {
    private String name;
}

@Getter
@Builder
public class Dog extends Animal {
    private String breed;
}

Dog d = Dog.builder().breed("푸들").build();
// name 을 설정할 방법이 없다
```

이 문제를 풀려면 `@SuperBuilder`를 쓴다. 부모와 자식 모두 `@SuperBuilder`를 붙이고, 부모는 `@NoArgsConstructor`도 필요하다.

```java
@Getter
@SuperBuilder
@NoArgsConstructor
public class Animal {
    private String name;
}

@Getter
@SuperBuilder
public class Dog extends Animal {
    private String breed;
}

Dog d = Dog.builder().name("초코").breed("푸들").build();
```

JPA Entity 상속에서 자주 쓰는 패턴이지만, `@SuperBuilder`는 `toBuilder = true` 옵션 사용 시 제약이 있다. 추상 클래스가 끼면 더 복잡해진다.

### 3.3 toBuilder = true의 얕은 복사

`toBuilder = true`는 기존 객체에서 새 빌더를 만들 수 있게 해준다. 하지만 컬렉션 필드는 얕은 복사가 일어난다.

```java
@Builder(toBuilder = true)
@Getter
public class Order {
    private final List<String> items;
}

Order original = Order.builder().items(new ArrayList<>()).build();
Order copy = original.toBuilder().build();
copy.getItems().add("새 항목");
// original.getItems() 에도 "새 항목" 이 들어감
```

`items` 참조가 그대로 복사되기 때문에 한쪽에서 수정하면 양쪽이 다 바뀐다. 불변성을 지키려면 빌더 내부에서 `Collections.unmodifiableList()`로 감싸거나, 별도 메서드로 깊은 복사를 해야 한다.

### 3.4 Generic 타입 충돌

제네릭 메서드와 `@Builder`가 함께 쓰일 때 IDE가 타입 추론을 못 하는 경우가 있다.

```java
@Builder
public class Response<T> {
    private T data;
    private int code;
}

Response<String> r = Response.<String>builder()
    .data("ok")
    .code(200)
    .build();
```

`Response.builder()`가 아니라 `Response.<String>builder()`로 타입 파라미터를 명시해야 컴파일러가 인식한다. 메서드 체이닝 중간에 타입 추론이 실패하면 원인 찾기가 어렵다.

## 4. @Data가 위험한 이유

`@Data`는 신입 때 편하다고 무지성으로 붙이지만, 5년쯤 굴려보면 빼고 싶어진다.

### 4.1 Setter가 만드는 불변성 파괴

`@Data`는 `@Setter`를 포함한다. JPA Entity에 붙이면 `entity.setStatus("DELETED")` 같은 코드가 어디서든 가능해진다. 도메인 규칙을 우회하는 경로가 열려버린다. 이 변경이 어느 시점에 일어났는지 추적이 어렵다.

```java
@Data
@Entity
public class Order {
    @Id
    private Long id;
    private String status;
    private LocalDateTime cancelledAt;
}

// 어디서든 이런 코드가 가능
order.setStatus("CANCELLED");
// cancelledAt 갱신은 잊어버린 채 status 만 바꿈
```

도메인 메서드로 강제해야 한다.

```java
@Getter
@Entity
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order {
    @Id
    private Long id;
    private String status;
    private LocalDateTime cancelledAt;

    public void cancel() {
        if ("CANCELLED".equals(this.status)) {
            throw new IllegalStateException("이미 취소됨");
        }
        this.status = "CANCELLED";
        this.cancelledAt = LocalDateTime.now();
    }
}
```

### 4.2 @ToString 순환 참조

양방향 연관관계에서 `@ToString`이 만나는 사고는 거의 클래식이다.

```java
@Entity
@Data
public class User {
    @Id
    private Long id;

    @OneToMany(mappedBy = "user")
    private List<Order> orders;
}

@Entity
@Data
public class Order {
    @Id
    private Long id;

    @ManyToOne
    private User user;
}
```

`order.toString()` 호출 시 `user`를 출력하려고 하고, `user.toString()`은 `orders`를 출력하려고 하고, `orders` 안의 `order.toString()`은 다시 `user`를... `StackOverflowError`가 난다. Spring Boot 로그에 `log.info("주문: {}", order)` 한 줄 적었다가 운영 서버가 죽는 사고가 실제로 흔하다.

해결은 한쪽 또는 양쪽에서 제외한다.

```java
@ToString(exclude = "user")
@Entity
public class Order { /* ... */ }
```

또는 `@ToString(onlyExplicitlyIncluded = true)`로 잡고 명시적인 필드만 포함시킨다.

### 4.3 컬렉션 비교 비용

`@EqualsAndHashCode`가 모든 필드를 포함하면, `equals` 호출 한 번이 List 전체를 순회한다. Entity가 수백 개 자식을 가진 컬렉션을 들고 있으면, `Set.contains()` 한 번이 굉장히 비싸진다. 이 비용은 프로파일러에서 잘 안 보이는 곳에서 누적된다.

## 5. JPA Entity에서 Lombok 사용 규칙

위 내용을 종합하면 JPA Entity에 적용할 실무 규칙이 나온다.

### 5.1 @NoArgsConstructor(access = PROTECTED)

Hibernate가 프록시를 만들 때 기본 생성자가 필요하다. `public`으로 열어두면 외부에서 `new Entity()`로 빈 객체를 만들 수 있어서 도메인 규칙을 우회한다. `PROTECTED`로 잡아두면 Hibernate는 리플렉션으로 접근 가능하지만 일반 코드에서는 막힌다.

```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product {
    @Id
    @GeneratedValue
    private Long id;
    private String name;

    public Product(String name) {
        this.name = name;
    }
}
```

`PRIVATE`까지 잠그면 Hibernate가 프록시 생성 시 `BytecodeProviderException`을 던지는 경우가 있다. `PROTECTED`가 안전한 기본값이다.

### 5.2 @Setter 금지

도메인 메서드로 상태 변경을 강제한다. `setName()` 같은 일반적인 setter 대신 `rename(String newName)` 같은 비즈니스 의미를 가진 메서드를 만든다. Setter 한두 개 살려두면 결국 모든 필드에 다 붙어버린다.

### 5.3 연관관계 필드 제외

`@ToString`과 `@EqualsAndHashCode`에서 연관관계 필드는 무조건 제외한다.

```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@ToString(onlyExplicitlyIncluded = true)
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Order {
    @Id
    @ToString.Include
    @EqualsAndHashCode.Include
    private Long id;

    @ToString.Include
    private String status;

    @ManyToOne(fetch = FetchType.LAZY)
    private User user;  // 둘 다에서 제외

    @OneToMany(mappedBy = "order")
    private List<OrderItem> items = new ArrayList<>();  // 둘 다에서 제외
}
```

## 6. 생성자 주입과 @RequiredArgsConstructor

Spring 4.3 이후로 생성자가 하나면 `@Autowired` 없이 자동 주입된다. `@RequiredArgsConstructor`가 final 필드를 모은 생성자를 만들어주면 그게 그대로 주입 통로가 된다.

### 6.1 final 필드 자동 감지

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentClient paymentClient;
    private final ApplicationEventPublisher eventPublisher;

    // 자동 생성:
    // public OrderService(OrderRepository, PaymentClient, ApplicationEventPublisher) { ... }
}
```

`final`이 아닌 필드는 빠진다. 의존성을 명시적으로 final로 선언하라는 코딩 규칙을 자연스럽게 강제한다.

### 6.2 @Lazy 주입과 @Qualifier

순환 의존성을 끊으려고 `@Lazy`를 붙이거나, 같은 타입의 빈 중 특정 빈을 골라야 할 때는 필드에 어노테이션을 직접 붙이고 Lombok 설정으로 생성자 파라미터에 전달해야 한다.

`lombok.config` 파일에 다음을 추가한다.

```properties
lombok.copyableAnnotations += org.springframework.beans.factory.annotation.Qualifier
lombok.copyableAnnotations += org.springframework.context.annotation.Lazy
```

이렇게 하면 필드의 어노테이션이 생성자 파라미터로 복사된다.

```java
@Service
@RequiredArgsConstructor
public class NotificationService {
    @Qualifier("emailSender")
    private final MessageSender emailSender;

    @Lazy
    private final ReportService reportService;
}
```

`lombok.config`에 등록 안 하면 어노테이션이 필드에만 붙고 생성자 파라미터에는 안 붙어서 주입이 실패한다. 이 설정을 모르면 "왜 의존성 주입이 안 되지" 한참 헤맨다.

### 6.3 @Value 어노테이션 충돌

Spring의 `@Value`(`org.springframework.beans.factory.annotation.Value`)와 Lombok의 `@Value`(`lombok.Value`)는 완전히 다른 기능이다. 같은 클래스에서 둘 다 쓰면 import 충돌이 난다.

```java
import lombok.Value;
import org.springframework.beans.factory.annotation.Value;  // 충돌
```

해결은 한쪽을 풀네임으로 쓰는 것이다.

```java
import lombok.Value;

@Value
public class ServerConfig {
    @org.springframework.beans.factory.annotation.Value("${server.port}")
    int port;
}
```

또는 Lombok의 `@Value` 대신 `@Getter` + `@AllArgsConstructor`를 명시적으로 쓴다. 실무에서는 후자가 더 흔하다. Lombok `@Value`는 의미가 모호하고 `final` 클래스를 만들어버려서 모킹이 어려워지기 때문이다.

## 7. @Slf4j 내부 동작과 logger 종류

`@Slf4j`는 SLF4J Logger를 생성한다. 다른 로깅 어노테이션도 비슷한 방식으로 동작한다.

### 7.1 어노테이션별 생성 코드

```java
@Slf4j      // private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(MyClass.class);
@Log4j2     // private static final org.apache.logging.log4j.Logger log = org.apache.logging.log4j.LogManager.getLogger(MyClass.class);
@CommonsLog // private static final org.apache.commons.logging.Log log = org.apache.commons.logging.LogFactory.getLog(MyClass.class);
@Log        // private static final java.util.logging.Logger log = java.util.logging.Logger.getLogger(MyClass.class.getName());
@JBossLog   // JBoss Logger
@Flogger    // Google Flogger
```

Spring Boot 기본은 SLF4J + Logback 조합이라서 `@Slf4j`가 기본 선택이다. Log4j2로 갈아탄 프로젝트는 `@Log4j2`를 쓰는데, classpath에 둘 다 있으면 어느 쪽이 동작할지 헷갈리니 한 가지로 통일해야 한다.

### 7.2 static 변수와 로깅 레벨

생성된 `log` 변수는 `static final`이다. 인스턴스마다 만들어지지 않는다. 로깅 레벨 변경은 SLF4J Logger 객체 자체를 바꾸는 게 아니라, 바인딩된 구현체(Logback 등)의 설정을 변경한다. Spring Boot Actuator의 `/actuator/loggers` 엔드포인트로 런타임에 레벨을 바꿀 수 있는 이유다. Logger 인스턴스는 그대로지만 내부 레벨 필드가 바뀐다.

### 7.3 topic 옵션

`@Slf4j(topic = "AUDIT")` 처럼 토픽을 지정하면 클래스명 대신 그 이름으로 Logger가 만들어진다. 감사 로그처럼 별도 logback 설정에 매핑할 때 쓴다.

```java
@Slf4j(topic = "AUDIT")
@Service
public class UserService {
    public void login(String userId) {
        log.info("login: {}", userId);  // "AUDIT" logger 로 기록
    }
}
```

`logback-spring.xml`에서 `<logger name="AUDIT">`로 별도 파일에 쓰도록 설정 가능하다.

## 8. Lombok 사용 시 트러블슈팅

### 8.1 IntelliJ annotation processing 비활성화

`Settings → Build → Compiler → Annotation Processors → Enable annotation processing`이 꺼져 있으면 컴파일은 되어도 IDE가 getter/setter를 인식 못 한다. 빨간 줄이 도배되는 증상이다. Lombok 플러그인은 IDE 인식을 도와주는 보조 도구일 뿐이고, 실제 코드 생성은 annotation processor가 한다.

### 8.2 Gradle 멀티모듈에서 annotationProcessor 누락

루트 모듈에 `compileOnly("org.projectlombok:lombok")`만 있고 `annotationProcessor`가 빠지면 컴파일은 깨지지만 에러 메시지가 모호하다. `cannot find symbol: method getXxx()` 같은 메시지로 나온다. 각 서브모듈마다 둘 다 선언해야 한다.

```kotlin
subprojects {
    dependencies {
        compileOnly("org.projectlombok:lombok")
        annotationProcessor("org.projectlombok:lombok")
        testCompileOnly("org.projectlombok:lombok")
        testAnnotationProcessor("org.projectlombok:lombok")
    }
}
```

`testCompileOnly`와 `testAnnotationProcessor`도 빠뜨리면 안 된다. 테스트 코드에서 `@Builder`를 못 쓰는 증상이 나타난다.

### 8.3 Java 17+ internal API 제한

JEP 403에 따라 JDK 내부 패키지는 기본적으로 모듈 외부에 닫혔다. Lombok이 `com.sun.tools.javac.*`를 직접 호출하기 때문에 빌드 시 다음 옵션이 필요할 수 있다.

```kotlin
tasks.withType<JavaCompile> {
    options.compilerArgs.addAll(listOf(
        "--add-opens", "jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.comp=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.main=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.model=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.processing=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED",
        "--add-opens", "jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED"
    ))
}
```

Lombok 1.18.30 이상에서는 대부분 자동 처리되지만, 환경에 따라 수동으로 잡아야 하는 경우가 남아있다.

### 8.4 MapStruct와 빌드 순서

Lombok이 만든 getter/setter를 MapStruct가 읽어서 매퍼 코드를 생성한다. annotation processor 실행 순서가 중요해진다. Gradle에서는 `lombok-mapstruct-binding`을 추가해야 한다.

```kotlin
dependencies {
    annotationProcessor("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok-mapstruct-binding:0.2.0")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.5.5.Final")
    implementation("org.mapstruct:mapstruct:1.5.5.Final")
    compileOnly("org.projectlombok:lombok")
}
```

`lombok-mapstruct-binding`이 없으면 MapStruct가 Lombok이 만든 메서드를 못 보고 "no property name" 류의 에러를 낸다. annotationProcessor 등록 순서도 영향을 미친다는 보고가 있으니 위 순서를 지키는 게 안전하다.

## 9. Lombok 대안

### 9.1 Java 14 record

Java 14에서 정식 도입된 `record`는 `@Value`와 비슷한 불변 데이터 클래스를 만든다.

```java
public record Money(long amount, String currency) {}
// 자동 생성: 생성자, amount(), currency(), equals, hashCode, toString
```

문법은 깔끔하지만 한계가 분명하다.

- **상속 불가**: record는 다른 클래스를 상속할 수 없다. `extends`가 막혀있다.
- **JPA Entity 불가**: JPA는 기본 생성자를 요구하는데 record는 모든 필드를 받는 생성자만 있다. `@Embeddable`이나 `@Entity`로 직접 쓸 수 없다.
- **getter 이름 규칙 다름**: `amount()` 형식이라서 `getAmount()`를 기대하는 기존 라이브러리(Jackson 일부 설정 등)와 충돌할 수 있다.

DTO나 값 객체로는 좋지만 도메인 모델 전반을 대체하기는 어렵다.

### 9.2 Kotlin data class

Kotlin은 `data class` 키워드로 record와 비슷한 기능을 제공한다. `copy()` 메서드까지 자동 생성되어 빌더 없이도 부분 수정이 쉽다.

```kotlin
data class User(val id: Long, val name: String, val email: String)

val updated = user.copy(email = "new@example.com")
```

Kotlin은 JPA Entity 사용 시 `kotlin-jpa` 플러그인으로 기본 생성자 문제를 해결한다. Lombok 없는 환경이 처음부터 자연스럽다. Java 프로젝트에서 Kotlin으로 점진 마이그레이션하는 팀이 많은 이유 중 하나다.

## 10. 실무 코드 컨벤션

여러 프로젝트를 거치면서 자리잡는 컨벤션이 있다.

### 10.1 @Getter만 명시적 사용

`@Data` 대신 필요한 것만 붙인다. `@Getter`는 거의 항상 안전하다. `@Setter`는 도메인 객체에 붙이지 않는다. `@ToString`은 연관관계 필드를 무조건 제외한다.

```java
@Getter
@Entity
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@ToString(of = {"id", "status"})
@EqualsAndHashCode(of = "id")
public class Order { /* ... */ }
```

### 10.2 @Builder.Default와 nullable 처리

`@Builder`를 쓸 때 컬렉션은 `@Builder.Default`로 빈 컬렉션을 초기화한다.

```java
@Builder
public class SearchCondition {
    @Builder.Default
    private List<String> categories = Collections.emptyList();
    @Builder.Default
    private Pageable pageable = PageRequest.of(0, 20);
    private String keyword;  // nullable 허용 필드는 default 없음
}
```

primitive 타입은 굳이 default를 안 줘도 0/false로 초기화된다. 그래도 의미 있는 기본값(예: `timeout = 30`)이 필요하면 명시한다.

### 10.3 Validation과 @Builder 조합

`@NotNull`, `@NotBlank` 같은 검증 어노테이션이 붙은 필드는 빌더로 안 넣으면 검증 시점에 실패한다. 객체 생성 자체를 막으려면 빌더에서 검증을 강제해야 한다.

```java
@Getter
public class RegisterRequest {
    @NotBlank
    private final String username;
    @Email
    private final String email;

    @Builder
    public RegisterRequest(String username, String email) {
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("username 필수");
        }
        this.username = username;
        this.email = email;
    }
}
```

생성자에 `@Builder`를 붙이면 그 생성자가 빌더의 진입점이 된다. 클래스에 붙이는 `@Builder`와 달리 검증 로직을 끼울 수 있다. 다만 `@Builder.Default`는 클래스 단위 `@Builder`에서만 동작하니 둘을 같이 쓸 때 동작 차이를 확인해야 한다.

## 참고

- [Project Lombok 공식 문서](https://projectlombok.org/features/all)
- [Hibernate ORM User Guide — Equality](https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#mapping-identifiers-derived)
- [JEP 395: Records](https://openjdk.org/jeps/395)
- [SLF4J Manual](https://www.slf4j.org/manual.html)
