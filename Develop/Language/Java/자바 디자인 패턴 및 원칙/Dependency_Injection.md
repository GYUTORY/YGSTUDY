---
title: Java - Dependency Injection (의존성 주입)
tags: [language, java, design-pattern, dependency-injection, spring, ioc]
updated: 2026-05-02
---

## 의존성 주입이란

의존성 주입(Dependency Injection, DI)은 객체가 협력 객체를 직접 생성하지 않고 외부에서 받아서 사용하는 방식이다. 한 줄로 끝나는 정의지만, 실제로는 객체 그래프를 누가 조립하느냐 하는 책임의 이동에 가깝다. `new`로 직접 만들면 만든 쪽이 조립 책임을 지고, 외부에서 받으면 그 책임이 컨테이너나 호출 측으로 넘어간다.

DI를 처음 접하면 Spring 같은 프레임워크의 기능으로 오해하기 쉽지만, DI 자체는 일반적인 설계 기법이다. 생성자 인자로 의존 객체를 받아서 필드에 저장하는 코드를 짠 적이 있다면 이미 DI를 한 것이다. Spring은 그 조립 과정을 컨테이너가 자동으로 해 줄 뿐이다.

### IoC와의 관계

IoC(Inversion of Control)는 제어의 흐름을 뒤집는다는 큰 개념이다. 콜백을 등록하고 프레임워크가 그것을 호출하게 만드는 것도 IoC고, 객체 생성 시점과 라이프사이클을 컨테이너가 관리하게 만드는 것도 IoC다. DI는 이 IoC 중에서 "의존 객체를 어떻게 받을 것인가"라는 한 가지 측면을 다룬다.

정리하면 IoC가 우산이고 DI는 그 안의 한 가지 구현 패턴이다. Spring을 IoC 컨테이너라고 부르는 이유는 DI 외에도 빈 라이프사이클 관리, AOP, 이벤트 디스패치 같은 제어 역전을 함께 제공하기 때문이다.

```java
public class OrderService {
    private final PaymentGateway paymentGateway;
    private final InventoryClient inventoryClient;

    public OrderService(PaymentGateway paymentGateway, InventoryClient inventoryClient) {
        this.paymentGateway = paymentGateway;
        this.inventoryClient = inventoryClient;
    }
}
```

이 클래스는 Spring 어노테이션이 하나도 없지만 DI를 따른다. 어떤 PaymentGateway 구현체를 쓸지 OrderService는 모르고, 결정권이 외부에 있다. 이게 DI의 본질이다.

## 세 가지 주입 방식과 실제 선택 기준

### 생성자 주입

객체를 만들 때 생성자 파라미터로 의존성을 전달한다. 다섯 줄 정도로 끝나는 단순한 구조지만 장점이 가장 많아서 기본 선택지다.

```java
@Service
public class OrderService {
    private final PaymentGateway paymentGateway;
    private final InventoryClient inventoryClient;

    public OrderService(PaymentGateway paymentGateway, InventoryClient inventoryClient) {
        this.paymentGateway = paymentGateway;
        this.inventoryClient = inventoryClient;
    }
}
```

장점부터 보면 첫째, 의존성을 `final`로 선언할 수 있어서 한 번 주입되면 바뀌지 않는다는 보장이 컴파일 타임에 생긴다. 둘째, 객체가 만들어진 시점에 모든 의존성이 채워져 있으므로 메서드 호출 중간에 NPE가 터질 가능성이 거의 없다. 셋째, 의존성이 많아지면 생성자 시그니처가 길어지면서 "이 클래스가 너무 많은 일을 하고 있구나"라는 신호를 강제로 받게 된다. 필드 주입은 이 신호가 약하다.

Spring 4.3부터는 생성자가 하나뿐이면 `@Autowired`를 생략할 수 있다. Lombok을 쓰면 `@RequiredArgsConstructor`로 더 줄어든다.

### 세터 주입

객체를 먼저 만들고 나중에 setter로 의존성을 주입한다.

```java
@Service
public class OrderService {
    private PaymentGateway paymentGateway;

    @Autowired
    public void setPaymentGateway(PaymentGateway paymentGateway) {
        this.paymentGateway = paymentGateway;
    }
}
```

생성자 주입이 안 되는 상황에서만 쓰는 보조 수단으로 생각하는 게 맞다. 실무에서 세터 주입을 의도적으로 선택하는 경우는 거의 없고, 순환 의존성 우회나 라이프사이클상 늦게 들어오는 의존성을 받을 때 정도다.

### 필드 주입

필드에 직접 `@Autowired`를 붙이는 방식이다.

```java
@Service
public class OrderService {
    @Autowired
    private PaymentGateway paymentGateway;
}
```

코드는 가장 짧지만 단점이 분명하다. `final`을 쓸 수 없고, 테스트에서 Mockito 같은 도구 없이 일반 객체로 만들어 쓸 수 없으며, 의존성이 늘어도 시그니처가 변하지 않아 클래스 비대화를 알아채기 어렵다. 새 코드에서는 쓰지 않는 게 맞다.

### 선택 기준

원칙은 단순하다. 기본은 생성자 주입을 쓰고, 정말 안 되는 경우만 세터 주입으로 우회한다. 필드 주입은 레거시 코드를 만지다가 어쩔 수 없이 만나는 정도로만 받아들이고 새로 추가하지 않는다. 이걸 한 번 정해 두면 코드 리뷰에서 매번 같은 얘기를 반복할 일이 줄어든다.

## @Autowired의 동작 원리

`@Autowired`가 붙은 곳에 빈을 주입하는 일은 `AutowiredAnnotationBeanPostProcessor`가 처리한다. 빈이 생성된 직후 이 후처리기가 클래스 메타데이터를 훑어서 `@Autowired`가 붙은 생성자, 메서드, 필드를 찾고, 컨테이너에서 매칭되는 빈을 꺼내 주입한다.

매칭 순서는 타입을 먼저 본다. 같은 타입의 빈이 하나면 그걸 그대로 주입하고, 여러 개면 이름으로 매칭을 시도한다. 그래도 결정이 안 되면 `@Primary`나 `@Qualifier` 같은 추가 정보를 본다. 이 단계까지 결정이 안 되면 `NoUniqueBeanDefinitionException`이 던져진다. 매칭되는 빈이 아예 없으면 `NoSuchBeanDefinitionException`이 나오는데, `required = false`로 명시하면 null로 두고 넘어간다.

```java
@Service
public class NotificationService {
    private final MessageSender messageSender;

    public NotificationService(@Qualifier("smsSender") MessageSender messageSender) {
        this.messageSender = messageSender;
    }
}
```

생성자 주입에서 `@Autowired`를 생략할 수 있는 이유는 Spring이 단일 생성자를 만나면 자동으로 그것을 주입 대상으로 인식하기 때문이다. 생성자가 둘 이상이면 어느 쪽을 쓸지 명시적으로 알려 줘야 한다.

### BeanFactory와 ApplicationContext

DI 컨테이너의 가장 기본 인터페이스가 `BeanFactory`다. 빈을 정의하고, 이름이나 타입으로 꺼내고, 싱글턴 여부를 확인하는 최소한의 기능만 가진다. 메모리가 빠듯한 환경에서 지연 초기화 위주로 쓰겠다면 `BeanFactory`로 충분하다.

`ApplicationContext`는 `BeanFactory`를 확장한 인터페이스다. 메시지 소스, 이벤트 퍼블리싱, 리소스 로딩, 환경 추상화(`Environment`) 같은 부가 기능이 붙어 있다. 그리고 기본적으로 싱글턴 빈을 컨테이너 시작 시점에 미리 만들어 둔다(eager initialization). 일반적인 Spring 애플리케이션은 거의 항상 `ApplicationContext`를 쓴다.

차이를 한 줄로 정리하면 `BeanFactory`는 DI 그 자체, `ApplicationContext`는 DI에 엔터프라이즈 기능을 얹은 상위 컨테이너다. 자주 보는 구현은 `AnnotationConfigApplicationContext`(Java config), `ClassPathXmlApplicationContext`(XML), Spring Boot가 내부적으로 쓰는 `AnnotationConfigServletWebServerApplicationContext` 정도다.

## 동일 타입 빈이 여러 개일 때

같은 인터페이스를 구현한 빈이 여러 개 등록되면 Spring은 어느 것을 주입할지 결정하지 못한다. 결제 수단을 추상화한 `PaymentGateway` 인터페이스에 `KakaoPayGateway`와 `TossPayGateway`가 모두 등록된 상황을 떠올리면 된다.

### @Primary

가장 자주 쓰이는 빈을 기본값으로 지정한다.

```java
@Service
@Primary
public class TossPayGateway implements PaymentGateway { }

@Service
public class KakaoPayGateway implements PaymentGateway { }
```

이 상태에서 `PaymentGateway` 타입으로 주입을 받으면 자동으로 `TossPayGateway`가 들어온다. 9할은 이게 맞고 1할은 다른 게 필요할 때 효과적이다.

### @Qualifier

특정 빈을 콕 집어 가져올 때 쓴다. 빈 이름이나 사용자 정의 식별자를 지정한다.

```java
@Service
public class RefundService {
    private final PaymentGateway gateway;

    public RefundService(@Qualifier("kakaoPayGateway") PaymentGateway gateway) {
        this.gateway = gateway;
    }
}
```

`@Primary`와 `@Qualifier`가 동시에 있을 때는 `@Qualifier`가 이긴다. 사용자 정의 어노테이션을 만들어 `@Qualifier`를 메타 어노테이션처럼 쓰는 패턴도 자주 쓴다. 문자열 이름이 곳곳에 흩어지는 걸 막아 준다.

```java
@Qualifier("kakaoPayGateway")
@Retention(RetentionPolicy.RUNTIME)
public @interface KakaoPay { }
```

이렇게 만들어 두면 주입 지점에서 `@KakaoPay PaymentGateway gateway` 형태로 받을 수 있다.

## 순환 의존성

A가 B를 주입받고, B가 다시 A를 주입받는 구조를 순환 의존성이라고 한다. 생성자 주입에서 이 상태를 만들면 빈을 만드는 시점에 두 객체 모두 상대를 요구하면서 어느 쪽도 완성되지 않는다. Spring은 이 상황을 감지해서 `BeanCurrentlyInCreationException`을 던진다.

```java
@Service
public class OrderService {
    public OrderService(MemberService memberService) { }
}

@Service
public class MemberService {
    public MemberService(OrderService orderService) { }
}
```

해결법은 세 가지가 있는데, 우선 순위가 분명하다.

첫째, 구조를 바꾼다. 두 서비스가 서로를 부른다는 건 책임이 잘못 나뉘어 있다는 신호다. 공통 로직을 제3의 컴포넌트로 빼서 양쪽이 그것을 의존하게 만들거나, 한쪽이 이벤트를 발행하고 다른 쪽이 구독하는 방식으로 바꾸면 결합이 풀린다. 실제 운영 코드에서 순환 의존성이 보이면 가장 먼저 의심해야 할 게 도메인 경계다.

둘째, 구조를 당장 바꾸기 어렵다면 한쪽을 세터 주입으로 돌린다. 생성자 시점에 상대가 없어도 일단 자기 자신은 만들어지고, 나중에 setter로 채워진다.

```java
@Service
public class OrderService {
    private MemberService memberService;

    @Autowired
    public void setMemberService(MemberService memberService) {
        this.memberService = memberService;
    }
}
```

셋째, `@Lazy`를 붙인다. 주입 지점에 프록시를 끼워서 실제 빈은 처음 호출되는 시점에 해석되게 만든다.

```java
@Service
public class OrderService {
    private final MemberService memberService;

    public OrderService(@Lazy MemberService memberService) {
        this.memberService = memberService;
    }
}
```

`@Lazy`는 잘 작동하지만 진짜 문제를 가리는 부작용이 있다. 임시로 막아 두고 다음 스프린트에 구조를 정리하는 식으로 쓰는 게 맞고, 그대로 방치하면 같은 패턴이 사방으로 번진다.

Spring Boot 2.6부터는 기본적으로 순환 의존성을 허용하지 않는다. `spring.main.allow-circular-references=true`로 강제로 켤 수는 있지만 새 코드에는 쓰지 말아야 한다.

## final 필드와 NullPointerException

생성자 주입을 쓰면서 의존성을 `final`로 선언하는 건 단순한 관습이 아니라 NPE 방지에 직접적인 영향을 준다. final 필드는 생성자에서 반드시 초기화돼야 하므로, 컴파일러가 "주입 안 된 상태로 객체가 만들어지는 경로"를 봉쇄해 준다.

```java
@Service
public class OrderService {
    private final PaymentGateway paymentGateway;

    public OrderService(PaymentGateway paymentGateway) {
        this.paymentGateway = paymentGateway;
    }
}
```

필드 주입을 쓰면 어떤 일이 벌어지는지가 대조적이다. 객체를 `new OrderService()`로 만들고 나서 Spring이 리플렉션으로 필드를 채우기 전까지는 의존성이 null이다. 테스트에서 일반 객체처럼 만들어서 메서드를 호출하면 그 사이 구간에 들어와서 NPE가 난다.

런타임에 Spring이 빈을 만드는 흐름에서는 어차피 다 채워지기 때문에 운영 환경에서는 차이가 잘 안 보이지만, 단위 테스트에서 그대로 드러난다. 생성자 주입과 final의 조합은 "주입 누락"이라는 버그 카테고리 자체를 없앤다는 점에서 가치가 있다.

## 선택적 의존성

대부분의 의존성은 필수지만 가끔 없어도 동작해야 하는 경우가 있다. 결제 후 알림을 보내는 서비스가 있는데 알림 발송기가 등록 안 된 환경에서도 결제는 되어야 한다고 치자. 이럴 때 두 가지 방법이 있다.

```java
@Service
public class OrderService {
    private final PaymentGateway paymentGateway;
    private final Optional<NotificationService> notificationService;

    public OrderService(PaymentGateway paymentGateway,
                        Optional<NotificationService> notificationService) {
        this.paymentGateway = paymentGateway;
        this.notificationService = notificationService;
    }

    public void place(Order order) {
        paymentGateway.charge(order);
        notificationService.ifPresent(n -> n.send(order));
    }
}
```

`Optional<T>`로 받으면 빈이 없을 때 `Optional.empty()`가 들어온다. 호출 측은 `ifPresent`로 처리하면 된다.

다른 방법은 `@Autowired(required = false)`다.

```java
@Autowired(required = false)
private NotificationService notificationService;
```

이쪽은 빈이 없으면 null로 남는다. 호출할 때 null 체크가 필요하다는 점에서 `Optional`보다 명시성이 떨어진다. 새로 짜는 코드라면 `Optional`이나 `ObjectProvider<T>`를 쓰는 게 의도가 분명하다.

`ObjectProvider`는 한발 더 나간 옵션이다. 0개, 1개, 여러 개의 후보 빈을 모두 다룰 수 있고 lazy 해석도 된다.

## 테스트와 Mockito @InjectMocks

생성자 주입은 테스트에서 가장 큰 보상이 돌아오는 부분이다. 컨테이너 없이 일반 객체로 만들어서 모의 객체를 그대로 끼워 넣을 수 있다.

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    PaymentGateway paymentGateway;

    @Mock
    InventoryClient inventoryClient;

    @InjectMocks
    OrderService orderService;

    @Test
    void 결제와_재고차감을_순서대로_호출한다() {
        Order order = new Order(1L, 10_000);

        orderService.place(order);

        verify(paymentGateway).charge(order);
        verify(inventoryClient).deduct(order);
    }
}
```

`@InjectMocks`는 대상 객체의 생성자를 보고 같은 타입의 `@Mock` 필드를 자동으로 끼워 넣는다. 생성자 주입을 쓰면 이 매칭이 깔끔하게 된다. 필드 주입을 쓰면 Mockito가 리플렉션으로 필드에 직접 값을 박는데, 우선순위가 꼬이거나 final 필드를 못 건드리는 등 이상한 케이스가 가끔 생긴다.

통합 테스트 쪽에서는 `@SpringBootTest`나 `@WebMvcTest`로 컨테이너를 띄우고 `@MockBean`으로 특정 빈만 모의 객체로 바꾸는 방식을 쓰는데, 이건 DI 자체보다는 Spring Test의 영역이라 여기서는 깊이 들어가지 않는다.

## 순수 자바 DI와 Guice/Dagger

Spring을 쓰지 않으면 DI를 어떻게 하는지도 알아 두면 도움이 된다. 가장 단순한 방법은 수동 와이어링이다. 애플리케이션 진입점에서 의존 객체들을 직접 만들어서 위에서부터 아래로 넘긴다.

```java
public class Application {
    public static void main(String[] args) {
        DataSource dataSource = new HikariDataSource(loadConfig());
        OrderRepository repository = new JdbcOrderRepository(dataSource);
        PaymentGateway gateway = new TossPayGateway(httpClient());
        OrderService service = new OrderService(repository, gateway);

        new HttpServer(service).start(8080);
    }
}
```

작은 애플리케이션, CLI 도구, 람다 함수처럼 객체 그래프가 단순한 곳에서는 이 방식이 오히려 가독성이 좋다. 컨테이너의 마법 없이 의존 관계가 한눈에 보이고, 디버깅도 쉽다.

객체가 많아지면 손으로 조립하기 버거워진다. 이때 Spring 외의 선택지로 Guice와 Dagger가 있다.

Guice는 Google이 만든 런타임 DI 컨테이너다. Spring처럼 리플렉션 기반이고, 모듈에서 바인딩을 정의한다. Spring보다 가볍고 단순한 게 특징이다. AOP나 트랜잭션 같은 것까지는 지원하지 않고 DI만 한다.

```java
public class OrderModule extends AbstractModule {
    @Override
    protected void configure() {
        bind(PaymentGateway.class).to(TossPayGateway.class);
        bind(OrderRepository.class).to(JdbcOrderRepository.class);
    }
}

Injector injector = Guice.createInjector(new OrderModule());
OrderService service = injector.getInstance(OrderService.class);
```

Dagger는 Google이 만든 컴파일 타임 DI다. 어노테이션 프로세서가 컴파일 시점에 그래프 코드를 생성한다. 리플렉션을 쓰지 않으므로 시작 속도가 빠르고 의존 그래프 오류가 빌드 시점에 잡힌다. 안드로이드처럼 리플렉션 비용이 큰 환경에서 강점이 있다. 단점은 학습 곡선과 빌드 설정 복잡도가 Guice보다 가파르다는 점이다.

서버 백엔드는 거의 Spring으로 수렴한다. Guice/Dagger는 Spring을 안 쓰는 라이브러리, 안드로이드, 작은 마이크로서비스에서 만나는 정도다.

## 트러블슈팅

### NoSuchBeanDefinitionException

주입하려는 타입의 빈이 컨테이너에 등록돼 있지 않을 때 나온다. 메시지는 보통 `No qualifying bean of type 'com.example.PaymentGateway' available`처럼 찍힌다.

원인을 추적할 때 가장 먼저 확인하는 건 컴포넌트 스캔 범위다. `@SpringBootApplication`이 붙은 클래스의 패키지 아래에 있는 빈만 자동으로 잡힌다. 다른 패키지에 있다면 `@ComponentScan(basePackages = "...")`로 범위를 넓히거나 `@Configuration`에서 `@Bean`으로 직접 등록해야 한다.

다음으로 의심할 건 어노테이션이다. 구현 클래스에 `@Service`나 `@Component`가 빠진 경우, 인터페이스에만 어노테이션을 붙인 경우, JAR 분리로 다른 모듈에서 스캔이 안 닿는 경우가 흔하다. 마지막으로 프로필 조건이다. `@Profile("prod")`가 붙은 빈은 해당 프로필이 활성화돼야 등록되므로, 테스트나 로컬에서 빠질 수 있다.

### NoUniqueBeanDefinitionException

같은 타입의 빈이 여러 개 등록돼 있고 어느 것을 쓸지 결정할 정보가 부족할 때 발생한다. 메시지에 후보 빈 이름이 모두 나열된다.

해결은 두 가지 방향이다. 모든 주입 지점에서 동일한 빈을 기본으로 쓰는 게 자연스러우면 한 빈에 `@Primary`를 붙인다. 주입 지점마다 다른 빈을 골라야 하면 `@Qualifier`로 명시한다. 컬렉션으로 받고 싶으면 `List<PaymentGateway>` 또는 `Map<String, PaymentGateway>`로 받으면 컨테이너가 모든 빈을 모아서 넣어 준다. 키는 빈 이름이 들어간다.

```java
public OrderService(Map<String, PaymentGateway> gateways) {
    this.gateways = gateways;
}
```

이 패턴은 결제 수단처럼 런타임에 골라야 하는 경우에 종종 쓴다.

### BeanCurrentlyInCreationException

순환 의존성이 발생했을 때 나온다. 메시지에 `Requested bean is currently in creation: Is there an unresolvable circular reference?`라는 문구가 있다.

원인은 앞에서 다룬 그대로다. 해결도 그대로다. 도메인 경계를 다시 그려서 의존 방향을 단방향으로 만드는 게 정석이고, 임시 우회책으로 세터 주입이나 `@Lazy`를 쓴다. 같은 메시지가 여러 빈에서 동시에 나온다면 도메인 모델 전반의 결합이 잘못 잡혀 있다는 신호이므로 부분 패치보다는 설계 검토가 필요하다.

스코프가 다른 빈끼리의 순환은 또 다른 케이스다. 싱글턴이 프로토타입을 가지고 있고 프로토타입이 싱글턴을 다시 참조하는 식의 구조에서도 비슷한 예외가 난다. 이때는 `ObjectProvider`로 lazy lookup을 하는 게 일반적인 해법이다.

### 그 외 자주 보는 메시지

`UnsatisfiedDependencyException`은 위 세 가지 예외를 감싸는 상위 메시지다. "이 빈을 만들다가 의존성 주입에서 실패했다"는 의미이고, 안에 들어 있는 cause를 보면 위에서 본 셋 중 하나인 경우가 많다.

`BeanCreationException`은 더 넓은 범위의 빈 생성 실패다. `@PostConstruct`에서 던진 예외, JDBC 풀 초기화 실패, 설정값 변환 실패 같은 게 모두 여기에 잡힌다. 스택 안쪽의 cause를 따라가야 진짜 원인이 보인다.

DI 관련 예외는 메시지 자체가 친절한 편이라 처음 한두 번만 패턴을 익혀 두면 그 다음부터는 빠르게 짚어 낼 수 있다.
