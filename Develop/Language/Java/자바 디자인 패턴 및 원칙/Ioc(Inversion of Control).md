---
title: Java - IoC (Inversion of Control, 제어의 역전)
tags: [language, java, design-pattern, ioc, spring, container]
updated: 2026-05-02
---

## 제어의 역전이 실제로 뒤집는 것

IoC(Inversion of Control)는 한 단어로는 잘 와닿지 않는 개념이다. "제어가 뒤집힌다"고 하면 추상적이지만, 실제로 IoC가 다루는 건 세 가지 책임의 이전이다. 객체를 누가 만드는가, 객체의 생명주기를 누가 관리하는가, 의존하는 다른 객체를 누가 찾아 주는가. 평범한 자바 코드에서는 이 셋이 모두 객체 자신 또는 그것을 호출하는 코드의 책임이다. IoC를 적용하면 이 책임이 외부의 어떤 주체(보통은 컨테이너)로 옮겨 간다.

가장 단순한 예로 비교해 보면 이렇다.

```java
public class OrderService {
    private final PaymentGateway gateway = new TossPayGateway();
    private final OrderRepository repository = new JdbcOrderRepository();

    public void place(Order order) {
        repository.save(order);
        gateway.charge(order);
    }
}
```

이 코드는 자기가 쓸 의존 객체를 자기가 만든다. 어떤 결제 게이트웨이를 쓸지, 그 객체를 언제 만들지, 누구와 공유할지 모두 OrderService가 결정한다. IoC를 적용한 버전은 정반대다.

```java
public class OrderService {
    private final PaymentGateway gateway;
    private final OrderRepository repository;

    public OrderService(PaymentGateway gateway, OrderRepository repository) {
        this.gateway = gateway;
        this.repository = repository;
    }
}
```

OrderService는 더 이상 누가 자기에게 무엇을 줄지 모른다. 결정권이 외부로 넘어갔다. 이 외부 주체가 "객체 그래프 조립"이라는 일을 책임지는 IoC 컨테이너다.

흔히 IoC를 DI와 동의어처럼 쓰지만 정확히는 그렇지 않다. IoC는 큰 우산이고 DI는 그 안에 들어가는 한 가지 기법이다. 콜백을 등록해 두고 프레임워크가 호출해 주는 구조도 IoC고, 톰캣의 서블릿 컨테이너가 서블릿 인스턴스 생명주기를 관리하는 것도 IoC고, 스레드풀이 작업 객체를 받아서 실행하는 것도 IoC다. DI는 이 모든 IoC 중에서 "의존 객체를 어떻게 받을 것인가" 한 측면만을 다룬다.

이 문서는 IoC라는 우산 자체와 그것을 구현하는 컨테이너의 동작을 본다. DI 자체의 세부(생성자/세터/필드 주입의 차이, `@Autowired` 매칭 규칙, 순환 의존성 해법 등)는 별도의 [Dependency_Injection](Dependency_Injection.md) 문서에서 다룬다.

## IoC의 여러 얼굴 — DI, Service Locator, Template Method, Strategy

IoC를 구현하는 방법은 하나가 아니다. 같은 "제어 역전"이라는 목적을 달성하기 위해 역사적으로 여러 패턴이 쓰였고, 지금도 환경에 따라 골라서 쓴다. 각각이 무엇을 뒤집는지를 보면 IoC라는 개념이 더 선명해진다.

### DI (Dependency Injection)

객체가 자기 의존성을 직접 만들지 않고 외부에서 받는다. 책임의 이전 방향은 "의존성 해결"이다.

```java
public class OrderService {
    private final PaymentGateway gateway;

    public OrderService(PaymentGateway gateway) {
        this.gateway = gateway;
    }
}
```

OrderService는 PaymentGateway가 어디에서 왔는지 모른다. 외부에서 주입해 준다. 이 방식은 객체가 자기 의존을 명시적으로 드러내기 때문에 테스트하기 쉽고 결합이 약하다. Spring이 가장 잘 다루는 영역이다.

### Service Locator

의존 객체를 글로벌 레지스트리에서 직접 찾아온다. 책임의 이전이 있긴 하지만 절반만 이뤄진다.

```java
public class OrderService {
    private final PaymentGateway gateway;

    public OrderService() {
        this.gateway = ServiceLocator.get(PaymentGateway.class);
    }
}
```

객체를 생성하는 책임은 ServiceLocator에 넘겨졌지만, "누구를 의존하는지"는 여전히 OrderService 안에 숨어 있다. 외부에서 보면 OrderService의 의존 관계가 코드를 까 봐야 보인다. 그래서 DI보다 결합이 강하고 테스트가 어렵다. 스프링이 보편화되기 전 Java EE 환경에서 JNDI 기반으로 많이 썼고, 안드로이드처럼 DI 도입이 부담스러운 환경에서 가끔 만난다.

DI와 Service Locator의 차이는 "의존 관계가 외부에서 보이는가"로 갈린다. DI는 시그니처에 다 드러나고, Service Locator는 숨는다.

### Template Method

부모 클래스가 알고리즘의 골격을 정의하고, 변하는 부분만 자식 클래스가 채운다. 호출 흐름의 제어가 부모에게 있다는 점에서 IoC다. "Don't call us, we'll call you"라는 헐리우드 원칙이 가장 잘 보이는 패턴이다.

```java
public abstract class HttpServlet {
    protected final void service(HttpServletRequest req, HttpServletResponse resp) {
        if (req.getMethod().equals("GET")) {
            doGet(req, resp);
        } else if (req.getMethod().equals("POST")) {
            doPost(req, resp);
        }
    }

    protected void doGet(HttpServletRequest req, HttpServletResponse resp) { }
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) { }
}
```

자식 클래스는 doGet, doPost만 채운다. 언제 자식 메서드가 불릴지는 부모가 결정한다. JDBC의 트랜잭션 템플릿, Spring의 `JdbcTemplate`, JUnit의 테스트 라이프사이클이 모두 이 구조다.

### Strategy

런타임에 알고리즘을 바꿔 끼우는 패턴이다. DI와 닮았지만 강조점이 다르다. DI는 "누가 의존성을 결정하는가"에 초점이 있고, Strategy는 "행동을 갈아 끼울 수 있다"는 데 초점이 있다.

```java
public class PaymentService {
    private PaymentStrategy strategy;

    public void setStrategy(PaymentStrategy strategy) {
        this.strategy = strategy;
    }

    public void pay(Order order) {
        strategy.pay(order);
    }
}
```

실무에서는 DI 컨테이너가 Strategy를 주입하는 형태로 둘이 합쳐진다. 결제 수단별 게이트웨이를 모두 빈으로 등록해 두고 런타임에 골라 쓰는 구조가 그 예다.

이 네 가지를 모두 알면 IoC가 단일한 메커니즘이 아니라 여러 패턴의 묶음이라는 게 보인다. Spring 컨테이너는 이 중 DI를 중심으로 하되, 라이프사이클 관리(Template Method 비슷한 후크)와 빈 선택(Strategy 비슷한 동적 디스패치)도 섞어서 제공한다.

## Spring IoC 컨테이너의 내부 동작

스프링 컨테이너가 빈을 어떻게 만드는지를 따라가 보면 IoC라는 개념이 어떻게 구현되는지가 구체적으로 보인다. 큰 흐름은 세 단계다. BeanDefinition 등록, 빈 인스턴스 생성, 의존성 해결.

### 1단계 — BeanDefinition 등록

컨테이너가 시작되면 가장 먼저 하는 일은 "어떤 빈을 만들 것인지"의 메타데이터 수집이다. 이 메타데이터를 담는 객체가 `BeanDefinition`이다. 빈 클래스, 스코프, 생성자 인자, 의존하는 다른 빈 이름, 라이프사이클 콜백 같은 정보가 들어간다.

수집 경로는 보통 셋 중 하나다.

- 컴포넌트 스캔: `@Component`, `@Service`, `@Repository`, `@Controller`가 붙은 클래스를 클래스패스에서 찾아낸다.
- Java config: `@Configuration` 클래스의 `@Bean` 메서드를 메타데이터로 변환한다.
- XML: `<bean id="..." class="...">` 항목을 읽는다.

이 시점에는 아직 어떤 빈도 인스턴스가 만들어지지 않는다. "이런 빈이 있을 것이다"라는 청사진만 `DefaultListableBeanFactory` 안의 맵에 쌓인다. 같은 이름의 BeanDefinition이 두 번 등록되면 기본적으로 나중 것이 앞 것을 덮어쓰는데, Spring Boot 2.1부터는 이 덮어쓰기가 디폴트로 막혀 있다. 빈 이름이 우연히 충돌하면 시작 실패로 빠르게 드러난다.

### 2단계 — 빈 인스턴스 생성

BeanDefinition이 모이면 컨테이너는 싱글턴 빈들을 미리 만들기 시작한다. 이걸 pre-instantiation 단계라고 부른다. `getBean(name)`을 처음 호출할 때 만들어지는 게 아니라 컨테이너 시작 시점에 만들어진다는 게 핵심이다. 그래서 설정 오류가 있으면 운영 트래픽이 들어오기 전에 빠르게 노출된다.

생성 자체는 리플렉션으로 생성자를 호출하는 형태다. 어떤 생성자를 쓸지는 다음 순서로 정한다.

- 생성자가 하나뿐이면 그것을 쓴다.
- 생성자가 여러 개면 `@Autowired`가 붙은 것을 찾는다.
- 그래도 결정되지 않으면 기본 생성자를 시도한다.
- 어느 것도 안 되면 `BeanInstantiationException`이 난다.

### 3단계 — 의존성 해결과 후처리

객체가 만들어지면 의존성을 채운다. 생성자 주입은 1단계와 2단계 사이에 같이 일어나고(생성자 인자를 미리 풀어서 넘겨야 하니까), 세터/필드 주입은 객체가 만들어진 다음에 별도로 수행된다.

이때 `BeanPostProcessor`가 끼어든다. 가장 자주 보는 게 `AutowiredAnnotationBeanPostProcessor`로 `@Autowired` 처리를 담당한다. `CommonAnnotationBeanPostProcessor`는 `@PostConstruct`, `@Resource` 처리를 맡는다. AOP 프록시가 만들어지는 시점도 여기다. `AnnotationAwareAspectJAutoProxyCreator`가 빈을 감싸서 프록시로 교체한다.

후처리가 끝나면 라이프사이클 콜백이 호출된다. 순서는 `@PostConstruct` → `InitializingBean.afterPropertiesSet()` → `@Bean(initMethod)`. 동일한 의미의 콜백이 셋이나 있는 건 역사적인 이유 때문이고, 새 코드에서는 `@PostConstruct`를 쓰면 충분하다.

이 모든 과정이 끝나야 빈이 "사용 가능" 상태가 된다. 컨테이너가 시작되면서 무거운 일을 다 끝내 두는 셈이다.

```text
ApplicationContext.refresh()
    ├─ BeanDefinition 수집 (스캔, config 처리)
    ├─ BeanFactoryPostProcessor 실행 (BeanDefinition 변경 가능)
    ├─ 싱글턴 빈 pre-instantiation
    │     ├─ 생성자 호출 (생성자 주입 해결)
    │     ├─ 필드/세터 주입
    │     ├─ BeanPostProcessor.before
    │     ├─ @PostConstruct / afterPropertiesSet
    │     └─ BeanPostProcessor.after  (AOP 프록시 생성)
    └─ ContextRefreshedEvent 발행
```

### 의존성 해결 순서가 만드는 함정

같은 빈 정의에서 두 빈이 서로를 참조하면 컨테이너는 만들기 시작한 빈을 일단 "현재 생성 중" 상태로 표시해 두고 의존하는 빈을 만들러 간다. 그 의존 빈이 다시 첫 빈을 요구하면 "현재 생성 중"이 다시 발견되고 `BeanCurrentlyInCreationException`이 난다. 세터 주입에서는 부분적으로 해결되는데, 미완성 상태의 빈을 노출하는 early reference라는 메커니즘으로 빠져나온다. 이게 가능한 이유는 빈 객체 자체가 final 필드 없이 만들어진 상태라 뒤에 채워 넣을 수 있기 때문이다.

이런 동작은 IoC 컨테이너가 단순히 "객체를 만들어 주는 도구"가 아니라 객체 그래프의 구성 순서를 정교하게 푸는 그래프 해결 엔진이라는 걸 보여 준다.

## ApplicationContext 종류별 차이

`ApplicationContext`는 인터페이스이고 구현체가 여럿이다. 구현체마다 BeanDefinition을 어디에서 읽어오는지가 다르다.

### AnnotationConfigApplicationContext

`@Configuration` 클래스나 컴포넌트 스캔 경로를 받아서 컨테이너를 구성한다. 요즘 Java config 기반 애플리케이션의 표준이다.

```java
public class App {
    public static void main(String[] args) {
        ApplicationContext ctx =
                new AnnotationConfigApplicationContext(AppConfig.class);
        OrderService service = ctx.getBean(OrderService.class);
        service.place(new Order(1L, 10_000));
    }
}

@Configuration
@ComponentScan("com.example")
class AppConfig { }
```

XML 파일 없이 모든 설정을 자바 코드로 표현하므로 IDE에서 타입 체크가 되고 리팩터링이 안전하다.

### ClassPathXmlApplicationContext / FileSystemXmlApplicationContext

XML 설정 기반이다. 레거시 시스템에서 종종 만난다.

```java
ApplicationContext ctx = new ClassPathXmlApplicationContext("beans.xml");
```

새 프로젝트에서 XML config로 시작할 일은 거의 없지만, 옛 코드를 이관할 때 둘 다 섞어 써야 하는 경우가 있다. 이때는 `@ImportResource("classpath:beans.xml")`로 XML과 Java config를 한 컨테이너에 묶을 수 있다.

### AnnotationConfigServletWebServerApplicationContext

Spring Boot가 웹 애플리케이션을 띄울 때 내부에서 만드는 컨테이너다. 일반 ApplicationContext에 내장 톰캣/제티/언더토우 서버 관리 기능이 추가돼 있다. 직접 인스턴스화하는 일은 거의 없고 `SpringApplication.run()`을 통해 간접적으로 사용한다.

### GenericApplicationContext

위 구현체들의 공통 베이스 격이다. BeanDefinition을 직접 등록하고 싶을 때, 즉 컴포넌트 스캔이나 설정 파일 없이 코드로 모두 정의하고 싶을 때 쓴다.

```java
GenericApplicationContext ctx = new GenericApplicationContext();
ctx.registerBean(PaymentGateway.class, TossPayGateway::new);
ctx.registerBean(OrderService.class);
ctx.refresh();
```

테스트에서 미니 컨테이너를 만들 때 가끔 쓴다.

### 어느 것을 골라야 하나

서버 애플리케이션은 거의 다 Spring Boot의 자동 구성에 맡기고 직접 컨테이너를 고를 일이 없다. 라이브러리나 임베디드 환경에서 직접 컨테이너를 띄워야 한다면 Java config면 `AnnotationConfigApplicationContext`, 동적 등록이 필요하면 `GenericApplicationContext`가 무난하다. XML은 새로 시작할 이유가 없다.

## 빈 스코프와 컨테이너의 책임

빈 스코프는 컨테이너가 빈 인스턴스를 얼마나 공유하느냐를 정한다. 같은 빈 정의에서 인스턴스를 하나만 만들어 모두 공유할지, 요청마다 새로 만들지에 대한 정책이다.

### singleton (기본값)

컨테이너당 인스턴스 하나. 같은 타입을 100군데서 주입받아도 모두 같은 객체를 가리킨다. 메모리 효율이 좋고 상태가 없는 서비스 빈에 자연스럽다. Spring은 별도 지정이 없으면 모든 빈을 싱글턴으로 만든다.

다중 스레드 환경에서 싱글턴 빈은 무상태(stateless)이거나 스레드 안전해야 한다. 빈 안에 가변 필드를 두면 동시성 버그의 단골 원인이 된다.

### prototype

`getBean`을 호출할 때마다 새 인스턴스를 만든다. 컨테이너는 만들어 주기만 하고 라이프사이클 관리는 하지 않는다. `@PreDestroy`가 호출되지 않으니, 자원 해제가 필요한 객체는 호출 측이 직접 책임져야 한다.

```java
@Component
@Scope("prototype")
public class ReportBuilder { }
```

싱글턴 빈에 프로토타입 빈을 주입하면 함정이 있다. 싱글턴은 한 번만 의존성이 채워지므로, 안에 들어간 프로토타입 빈도 사실상 싱글턴처럼 한 인스턴스로 고정된다. 매번 새 인스턴스를 받고 싶으면 `ObjectProvider`나 `@Lookup` 메서드를 써야 한다.

```java
@Component
public class ReportService {
    private final ObjectProvider<ReportBuilder> builderProvider;

    public ReportService(ObjectProvider<ReportBuilder> builderProvider) {
        this.builderProvider = builderProvider;
    }

    public Report build() {
        ReportBuilder builder = builderProvider.getObject();
        return builder.build();
    }
}
```

### request, session, application (웹 스코프)

웹 환경에서만 의미가 있다. request는 HTTP 요청 하나당 하나, session은 HTTP 세션 하나당 하나, application은 ServletContext당 하나다. request 스코프 빈은 매 요청마다 새로 만들어지고 응답이 끝나면 폐기된다.

이런 스코프 빈을 싱글턴 빈에 주입하려면 프록시가 필요하다. 싱글턴이 만들어질 때는 아직 요청이 없을 수 있으니 실제 객체를 직접 끼워 넣을 수 없기 때문이다. `@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)`로 프록시 모드를 켜면 컨테이너가 CGLIB 프록시를 만들어 끼워 두고, 메서드 호출 시점에 현재 요청에 맞는 실제 빈으로 디스패치한다.

### websocket과 사용자 정의 스코프

`websocket` 스코프는 STOMP 세션 단위로 빈을 유지한다. 이외에 `Scope` 인터페이스를 직접 구현해서 사용자 정의 스코프를 만들 수도 있다. 멀티테넌시에서 테넌트별 빈을 분리하거나, 배치 작업 단위로 빈을 쓰고 버리는 패턴에서 가끔 쓴다.

스코프는 결국 "빈 인스턴스를 누구와 공유하느냐"에 대한 컨테이너의 정책 결정이고, 이 정책 자체가 IoC가 다루는 영역이다. 객체의 생성과 파기 시점을 호출 측이 결정하지 않는다는 것 자체가 제어 역전이다.

## IoC 컨테이너 없이 Java로만 만들어 보기

스프링이 어떻게 동작하는지 감을 잡으려면 같은 일을 손으로 해 보는 게 빠르다. 50줄 정도면 동작하는 미니 IoC 컨테이너를 만들 수 있다. 기능은 단순하다. 클래스를 등록하고, 의존하는 다른 빈을 자동으로 찾아 생성자에 넣어 주고, 싱글턴으로 캐시한다.

```java
import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class MiniContainer {
    private final Map<Class<?>, Class<?>> bindings = new HashMap<>();
    private final Map<Class<?>, Object> singletons = new HashMap<>();

    public <T> void bind(Class<T> from, Class<? extends T> to) {
        bindings.put(from, to);
    }

    public <T> T get(Class<T> type) {
        if (singletons.containsKey(type)) {
            return type.cast(singletons.get(type));
        }
        Class<?> impl = bindings.getOrDefault(type, type);
        T instance = type.cast(create(impl));
        singletons.put(type, instance);
        return instance;
    }

    private Object create(Class<?> impl) {
        Constructor<?> ctor = impl.getDeclaredConstructors()[0];
        Class<?>[] paramTypes = ctor.getParameterTypes();
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++) {
            args[i] = get(paramTypes[i]);
        }
        try {
            return ctor.newInstance(args);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("빈 생성 실패: " + impl, e);
        }
    }
}
```

쓰는 쪽은 이렇게 된다.

```java
public class App {
    public static void main(String[] args) {
        MiniContainer container = new MiniContainer();
        container.bind(PaymentGateway.class, TossPayGateway.class);

        OrderService service = container.get(OrderService.class);
        service.place(new Order(1L, 10_000));
    }
}
```

이 50줄짜리 컨테이너가 하는 일을 보면 스프링이 하는 일의 핵심이 그대로 들어 있다. 첫째, 인터페이스와 구현 클래스를 매핑한다(BeanDefinition의 단순한 형태). 둘째, 생성자 파라미터 타입을 보고 재귀적으로 의존을 해결한다(생성자 주입). 셋째, 싱글턴 캐시를 둔다(스코프 관리). 스프링은 여기에 어노테이션 스캔, 라이프사이클 콜백, AOP, 스코프 다양화, 순환 의존성 처리, 프록시 생성 등을 더 얹은 것뿐이다.

직접 만들어 보면 두 가지가 분명해진다. IoC 컨테이너의 본질은 어렵지 않다는 점, 그리고 운영용 컨테이너가 되려면 위에 얹어야 할 게 많다는 점이다. 후자가 스프링의 가치다.

## 실무에서 IoC 컨테이너의 한계와 비용

IoC 컨테이너는 무료가 아니다. 실제 운영에서 마주치는 비용 몇 가지를 짚어 둔다.

### 시작 시간

스프링 컨테이너는 BeanDefinition 스캔, 빈 생성, AOP 프록시 작성, `@PostConstruct` 호출까지 전부 시작 시점에 한다. 빈이 수백 개 단위가 되면 시작 시간이 수 초에서 십수 초까지 늘어난다. 람다 함수처럼 콜드 스타트가 중요한 환경에서는 이 비용이 치명적이다. Spring Boot 3 이후로는 GraalVM native image로 AOT 컴파일을 통해 시작 시간을 1초 이내로 줄이는 길이 열렸지만, 리플렉션이나 동적 프록시를 쓰는 코드를 추가로 설정해 줘야 한다는 부담이 있다.

큰 모놀리스에서는 개발 중에 자주 재시작하는 게 고통스럽다. spring-boot-devtools나 JRebel 같은 도구가 부분적으로 완화해 주지만 근본 해결은 아니다.

### 디버깅 난이도

빈이 만들어지는 과정이 사용자 코드 밖에서 일어나기 때문에 문제가 생기면 추적이 어렵다. `@Autowired`가 왜 다른 빈을 골랐는지, 왜 두 개 등록된 빈이 있는지, 왜 `@Profile` 조건이 안 맞아서 빈이 빠졌는지를 알려면 컨테이너의 동작 모델을 이해해야 한다.

에러가 났을 때 스택 트레이스가 길고 핵심 원인이 안쪽 cause에 묻혀 있는 경우도 많다. `UnsatisfiedDependencyException`을 풀려면 메시지를 끝까지 따라가서 진짜 원인을 찾는 습관이 필요하다.

### 마법 같은 동작과 가시성 손상

`@Transactional`이 어떻게 트랜잭션을 만들고 닫는지, `@Async`가 어떻게 스레드를 갈아타는지, `@Cacheable`이 언제 캐시를 깨는지는 어노테이션만 봐서는 보이지 않는다. 모두 AOP 프록시가 메서드 호출 사이에 끼어들어 처리한다. 호출 그래프가 IDE의 "Find Usage"로 추적되지 않아서 신참 개발자가 흐름을 파악하는 데 시간이 걸린다.

특히 같은 클래스 내부에서 `@Transactional` 메서드를 호출하면 프록시를 거치지 않으므로 트랜잭션이 적용되지 않는 함정이 유명하다. 이런 종류의 "AOP 인지 차이"는 IoC 컨테이너가 만드는 마법의 그림자다.

### 런타임 리플렉션 의존

스프링은 상당 부분이 리플렉션 기반이다. 메모리와 시작 시간에 영향이 있고, GraalVM native image로 컴파일할 때 별도 설정이 필요하다. Dagger 같은 컴파일 타임 DI를 쓰면 이 비용이 사라지지만 학습 곡선이 가팔라진다.

### 컨테이너를 빼는 결정

이런 비용을 알게 되면 "정말 IoC 컨테이너가 필요한가"라는 질문이 자연스럽다. 도구가 짧고 의존이 단순하면 main에서 손으로 조립하는 편이 더 단순하다. 람다 함수, CLI 도구, 네이티브 이미지로 빌드하는 마이크로 서비스는 컨테이너 없이 가는 선택을 진지하게 검토할 만하다.

반대로 도메인이 크고 빈이 백 개를 넘기 시작하면 손 조립이 더 비싸진다. 그 경계는 팀과 도메인에 따라 다르지만, IoC 컨테이너를 "당연히 쓴다"가 아니라 "비용과 이득을 보고 고른다"의 위치로 두는 게 맞다.

## DI 문서와의 역할 분리

이 문서는 IoC를 우산으로 두고 컨테이너 자체의 동작에 집중한다. 정리하면 이 문서가 다루는 것은 다음이다.

- IoC가 뒤집는 책임의 정체
- DI 외의 IoC 구현 방식들
- Spring 컨테이너의 내부 동작과 빈 생성 순서
- ApplicationContext 구현체별 용도
- 빈 스코프와 컨테이너의 라이프사이클 관리 책임
- 컨테이너 없이 만들어 보는 미니 IoC
- 컨테이너의 한계와 비용

DI의 구체 메커니즘 — 생성자/세터/필드 주입의 비교, `@Autowired`의 매칭 규칙, `@Primary`/`@Qualifier`, 순환 의존성 해결, `@InjectMocks` 같은 테스트 패턴, NoSuchBeanDefinitionException 같은 예외 트러블슈팅 — 은 [Dependency_Injection](Dependency_Injection.md) 문서에서 다룬다. 둘을 같이 읽으면 "왜 IoC가 필요한가"와 "DI를 어떻게 쓰는가"가 함께 잡힌다.
