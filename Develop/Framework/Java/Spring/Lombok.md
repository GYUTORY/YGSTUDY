---
title: Project Lombok
tags: [framework, java, spring, lombok]
updated: 2026-06-03
---

# Project Lombok

Java 코드에서 반복되는 getter/setter/생성자/toString 같은 보일러플레이트를 컴파일 시점에 자동으로 생성해 주는 라이브러리다. 어노테이션 프로세서로 동작하기 때문에 런타임 비용은 없고, 빌드 결과물에는 직접 작성한 메서드와 똑같은 바이트코드가 박힌다. Spring Boot 프로젝트라면 거의 표준처럼 쓰지만, 잘못 쓰면 도메인 모델이 망가지거나 컴파일 단계에서 사람을 곤란하게 만든다.

심화 주제 — 어노테이션 프로세싱 내부 동작, JPA/JSON 직렬화와의 충돌, 모듈 시스템 대응 — 는 [Lombok_Deep_Dive.md](./Lombok_Deep_Dive.md)에 정리해 두었다.

참고 문서:
- [Project Lombok 공식 문서](https://projectlombok.org/features/all)
- [Spring Boot with Lombok](https://spring.io/blog/2018/12/12/spring-boot-with-lombok)

## 1. 환경 설정

### 1.1 의존성

Gradle Kotlin DSL 기준이다. Spring Boot 프로젝트라면 `compileOnly` + `annotationProcessor` 조합으로 충분하다. 런타임에 Lombok jar를 끌고 갈 이유가 없다.

```kotlin
dependencies {
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    testCompileOnly("org.projectlombok:lombok")
    testAnnotationProcessor("org.projectlombok:lombok")
}
```

Maven은 `<scope>provided</scope>`로 거의 같은 효과를 낸다. 다만 `spring-boot-starter-parent`를 쓰는 경우 버전을 명시하지 말고 BOM이 관리하도록 두는 편이 안전하다. 버전을 직접 박았다가 Spring Boot 업그레이드 후 호환되지 않는 Lombok 버전 때문에 빌드가 깨진 적이 한두 번이 아니다.

```xml
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <scope>provided</scope>
</dependency>
```

### 1.2 IDE 설정 — 빠지면 종일 헤맨다

처음 Lombok을 도입한 팀에서 가장 자주 겪는 사고가 "IntelliJ가 컴파일은 통과시키는데 로컬에서 빨간 줄이 가득 떠 있는" 상황이다. 원인은 두 가지로 갈린다.

- IntelliJ에 Lombok 플러그인이 설치되지 않은 경우: getter 호출이 전부 빨간 줄이 된다. 최신 IntelliJ에는 번들이지만 가끔 비활성화된 채로 깔린다.
- Annotation Processing이 꺼져 있는 경우: `Settings → Build, Execution, Deployment → Compiler → Annotation Processors`에서 "Enable annotation processing"을 켜야 한다. 끄고 있으면 IntelliJ 내장 빌더가 Lombok이 생성할 메서드를 만들지 못해서 `cannot find symbol getId()` 같은 에러가 난다.

CI 서버에서는 잘 빌드되는데 로컬에서만 깨진다면 십중팔구 위 두 가지 중 하나다. 새로 합류한 팀원이 첫날 빌드 안 된다고 호출하는 패턴이 거의 똑같다.

Gradle 빌드 캐시가 꼬여서 Lombok 생성 메서드를 못 찾는 경우도 있다. `./gradlew clean compileJava --rerun-tasks` 한 번이면 거의 해결된다.

## 2. 자주 쓰는 어노테이션

### 2.1 @Getter / @Setter

필드 단위로도, 클래스 단위로도 붙일 수 있다. 접근 수준을 좁히고 싶으면 `AccessLevel`을 명시한다.

```java
@Getter
public class User {
    private String username;
    private String email;

    @Getter(AccessLevel.PROTECTED)
    private String passwordHash;
}
```

`@Setter`를 클래스 전체에 거는 경우는 거의 없다. 도메인 객체에 무차별 Setter가 생기면 의미 없는 상태 전이가 코드 곳곳에서 일어나고, 결국 도메인 규칙을 검증할 자리를 잃는다. 뒤에서 다시 다룬다.

### 2.2 @ToString — 양방향 연관관계에서 사고가 난다

`@ToString`은 기본적으로 모든 필드를 찍는다. JPA Entity에 그대로 붙이면 양방향 연관관계에서 StackOverflowError가 난다. `User`의 `toString()`이 `orders`를 찍고, `Order`의 `toString()`이 다시 `user`를 찍고, 무한 루프에 빠진다.

처음 이 사고를 겪었을 때는 로그를 한 줄 찍으려고 `log.info("user={}", user)` 한 게 전부였는데, JVM이 통째로 죽었다. 원인을 찾는 데 한참 걸렸다. 해결책은 단순하다 — 연관관계 필드는 명시적으로 제외한다.

```java
@Entity
@Getter
@ToString(exclude = {"orders"})
public class User {
    @Id
    private Long id;
    private String username;

    @OneToMany(mappedBy = "user")
    private List<Order> orders = new ArrayList<>();
}
```

필드가 많아지면 `exclude`로 일일이 빼는 게 귀찮다. 반대로 포함할 필드만 골라 쓰는 게 안전하다.

```java
@ToString(onlyExplicitlyIncluded = true)
public class User {
    @ToString.Include private Long id;
    @ToString.Include private String username;

    @OneToMany(mappedBy = "user")
    private List<Order> orders;
}
```

기본값을 "필요한 것만"으로 두면 새 필드가 추가될 때마다 의식해서 `@ToString.Include`를 붙이게 된다. 사고를 한 번 겪고 나서는 모든 JPA Entity에 `onlyExplicitlyIncluded = true`를 기본으로 깔게 됐다.

### 2.3 생성자 — @NoArgsConstructor / @AllArgsConstructor / @RequiredArgsConstructor

세 개 중 실무에서 가장 자주 쓰는 건 `@RequiredArgsConstructor`다. Spring의 생성자 주입과 잘 맞는다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentClient paymentClient;
    // 생성자 자동 생성 → 필드 final만 모아서 주입
}
```

JPA Entity에는 `@NoArgsConstructor(access = AccessLevel.PROTECTED)`를 같이 건다. JPA 스펙상 기본 생성자가 필요한데, 도메인 코드에서는 직접 호출하지 못하게 막아야 의미 없는 빈 객체가 돌아다니지 않는다.

```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order {
    @Id @GeneratedValue
    private Long id;

    private String productName;
    private int quantity;

    public Order(String productName, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("quantity must be positive");
        this.productName = productName;
        this.quantity = quantity;
    }
}
```

`@AllArgsConstructor`는 필드 순서가 바뀌면 호출부가 조용히 망가지기 때문에 — 같은 타입이 연속해 있으면 컴파일러가 잡아주지도 않는다 — DTO처럼 작고 단순한 곳에만 쓰는 편이 낫다. 도메인에는 의도가 분명한 생성자를 직접 적는다.

### 2.4 @Data 남발 — 도메인이 망가지는 가장 흔한 패턴

`@Data`는 `@Getter`, `@Setter`, `@ToString`, `@EqualsAndHashCode`, `@RequiredArgsConstructor`를 한꺼번에 붙인다. 편해 보이지만 도메인 객체에 붙이면 거의 반드시 후회한다.

실제로 겪은 사례 한 가지를 옮긴다. 주문 도메인의 `Order` 엔티티에 `@Data`가 붙어 있었다. 처음에는 문제가 없었는데, 결제 모듈을 만든 동료가 `order.setStatus("PAID")`를 직접 호출하기 시작했다. 원래는 `order.markPaid(payment)` 같은 메서드를 거쳐 결제 정보 검증과 이벤트 발행이 함께 일어나야 했는데, Setter가 공개돼 있으니 그걸 우회했다. 한 달 뒤 결제 완료 이벤트를 구독하던 적립금 모듈이 누락된 주문을 발견했고, 그제서야 도메인 규칙이 우회되고 있다는 걸 알았다.

`@Data`가 문제의 본질은 아니다. 문제는 Setter가 도메인 의도와 상관없이 모든 필드에 노출된다는 점이다. 다음 원칙으로 정리하면 사고가 줄어든다.

- JPA Entity, 도메인 객체에는 `@Data`를 쓰지 않는다. 필요한 어노테이션만 골라 붙인다 (`@Getter`, `@ToString(onlyExplicitlyIncluded = true)`, 필요한 생성자).
- 상태 변경은 의미 있는 메서드(`markPaid`, `cancel`)로 표현한다.
- `@Data`는 외부 시스템과 주고받는 단순 DTO 정도에 한정한다. 그것도 가능하면 `record` 또는 `@Value`로 불변 객체를 쓰는 게 낫다.

### 2.5 @Value — 불변 DTO

`@Value`는 클래스를 final로, 모든 필드를 final로 만들고 Setter 없이 Getter만 노출한다. Java 16+의 `record`와 거의 같은 자리를 차지한다. 새 프로젝트에서 JDK 17 이상을 쓴다면 `record`가 우선이고, 옛 코드베이스나 JDK 11 환경에서는 `@Value`가 여전히 유용하다.

```java
@Value
public class Money {
    long amount;
    String currency;
}
```

### 2.6 @Builder

필드가 4개 넘어가면 빌더의 가독성이 확실히 살아난다. `@Builder.Default`로 기본값을 잡을 수 있고, `toBuilder = true`로 일부만 바꾼 사본을 만들 수 있다.

```java
@Builder(toBuilder = true)
@Getter
public class OrderRequest {
    private final Long userId;
    private final String productName;
    private final int quantity;

    @Builder.Default
    private final String channel = "WEB";
}

OrderRequest original = OrderRequest.builder()
    .userId(1L)
    .productName("키보드")
    .quantity(1)
    .build();

OrderRequest mobile = original.toBuilder().channel("MOBILE").build();
```

클래스에 붙이면 모든 필드를 받는 빌더가 만들어진다. 생성자에 붙이면 그 생성자 시그니처에 맞는 빌더만 만들어진다. JPA Entity에서 일부 필드만 받는 빌더가 필요하다면 생성자에 붙이는 쪽이 깔끔하다.

```java
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User {
    @Id @GeneratedValue
    private Long id;
    private String username;
    private String email;

    @Builder
    public User(String username, String email) {
        this.username = username;
        this.email = email;
    }
}
```

### 2.7 @EqualsAndHashCode — JPA Entity에서 특히 조심

JPA Entity에 `@Data`나 `@EqualsAndHashCode`를 기본 옵션으로 붙이면 모든 필드가 비교 대상에 들어간다. 컬렉션 필드(예: `List<Order> orders`)가 비교에 끼면 LAZY 로딩이 강제로 트리거되거나, 양방향 관계에서 StackOverflowError가 다시 발생한다.

엔티티의 동일성은 식별자 하나로 판정하는 게 가장 안전하다.

```java
@Entity
@Getter
@EqualsAndHashCode(of = "id")
public class Product {
    @Id @GeneratedValue
    private Long id;
    private String name;
    private int price;
}
```

다만 ID가 영속화 전(`null`)인 객체와 영속화 후(`Long`) 객체가 같은 컬렉션에 들어가면 hashCode가 달라져서 `Set`에서 사라지는 경우가 생긴다. 이 문제는 [Lombok_Deep_Dive.md](./Lombok_Deep_Dive.md)에서 영속성 기반 동일성 판정을 다룰 때 더 자세히 설명한다.

### 2.8 @Slf4j

별 것 아닌 어노테이션이지만 매일 쓴다. `private static final Logger log = LoggerFactory.getLogger(...)`를 손으로 적을 일이 없어진다.

```java
@Slf4j
@Service
public class PaymentService {
    public void process(Long orderId) {
        log.info("payment start orderId={}", orderId);
    }
}
```

SLF4J 외에도 `@Log4j2`, `@CommonsLog`, `@Log` 같은 변형이 있는데, Spring Boot의 기본 로깅 추상화가 SLF4J라서 다른 걸 쓸 일은 거의 없다.

## 3. Spring Boot 실전 예제

Service 계층 전형적인 형태다. 생성자 주입과 로깅이 합쳐진다.

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class UserService {
    private final UserRepository userRepository;

    @Transactional
    public Long register(String username, String email) {
        log.info("register username={} email={}", username, email);
        User user = User.builder()
            .username(username)
            .email(email)
            .build();
        return userRepository.save(user).getId();
    }
}
```

Controller에서 받는 요청 DTO는 `record`를 쓰거나, JDK 버전이 낮으면 `@Value` + `@Builder` 조합이 무난하다. `@Data`는 Jackson 역직렬화가 Setter를 요구하던 시절의 흔적이라 요즘은 굳이 쓸 이유가 적다.

```java
public record CreateOrderRequest(
    Long userId,
    String productName,
    int quantity
) {}
```

## 4. 자주 마주치는 함정

지금까지 끌어 모은 사고 사례를 한 번 더 정리한다.

도메인 객체에 `@Data`를 붙여 놓고 Setter로 상태를 바꾸기 시작하면 도메인 규칙이 흩어진다. 한두 군데에서 시작된 우회는 시간이 지나면 추적이 거의 불가능한 수준으로 퍼진다. 어노테이션 한 개로 절약한 몇 줄과 맞바꾸기에는 너무 비싸다.

JPA 양방향 연관관계에서 `@ToString` 기본 동작을 그대로 두면 로그 한 줄에 JVM이 멈춘다. `exclude` 또는 `onlyExplicitlyIncluded`를 기본으로 깔고 시작한다.

IDE에서 Lombok 플러그인이나 Annotation Processing이 꺼져 있으면 빨간 줄이 가득하지만 빌드는 통과하는 기묘한 상황이 생긴다. 새로 합류한 개발자가 환경 세팅에서 막혔다면 이 두 가지를 먼저 본다.

`@AllArgsConstructor`는 필드 순서가 곧 생성자 시그니처라서, 같은 타입 필드가 둘 이상 연속하면 호출부가 조용히 잘못된 값을 받게 된다. DTO처럼 작은 곳에 한정해서 쓰고, 도메인에서는 의도가 드러나는 생성자를 직접 적는다.

`@EqualsAndHashCode`를 기본 옵션으로 JPA Entity에 붙이면 LAZY 로딩이 의도치 않게 발동되거나 순환 참조가 생긴다. `of = "id"` 로 좁히거나, 식별자 기반 동일성 정책을 직접 정의한다.

Lombok 버전을 직접 박는 것보다 Spring Boot BOM이 관리하게 두는 편이 안전하다. 직접 박았다가 Boot 업그레이드 후 어노테이션 프로세서가 깨진 사례를 적지 않게 봤다.

심화 주제 — 어노테이션 프로세싱 동작 원리, JPA/Jackson과의 상호작용, 모듈 시스템에서의 설정, delombok 작업 — 은 [Lombok_Deep_Dive.md](./Lombok_Deep_Dive.md)로 이어진다.
