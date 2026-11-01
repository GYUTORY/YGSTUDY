---
title: Java AOP 심화
tags: [java, spring, proxy, language]
updated: 2026-11-01
---

# Java 관점지향 프로그래밍(AOP) Deep Dive

## 1. AOP가 왜 필요한가

5년차쯤 되면 누구나 한 번은 비슷한 경험을 한다. 트랜잭션 시작·종료 로그를 모든 서비스 메서드에 박아넣다가 어느 순간 비즈니스 로직보다 부가 로직이 더 길어진 코드를 보게 된다. 로깅, 트랜잭션, 권한 검사, 실행 시간 측정, 캐시 키 생성처럼 여러 모듈에 횡단으로 흩어지는 관심사(cross-cutting concern)를 본래 로직에서 떼어내는 게 AOP의 출발점이다.

AOP는 OOP를 대체하는 게 아니라 보완한다. 객체 책임은 그대로 두고, 객체 호출 직전·직후·예외 시점에 끼어들어 부가 동작을 실행하는 메커니즘이라고 보면 된다.

## 2. 핵심 용어 — 실무 관점

용어가 많아 보이지만 실제로 손에 익는 건 다섯 개다.

- **Aspect**: 관심사 자체. `@Aspect`가 붙은 클래스 하나가 하나의 Aspect다. 예: `LoggingAspect`, `AuditAspect`.
- **JoinPoint**: 부가 동작이 끼어들 수 있는 지점. Spring AOP에서는 메서드 실행 시점만이 JoinPoint다. 생성자 호출, 필드 접근 같은 건 Spring AOP가 잡지 못한다(AspectJ는 잡음).
- **Pointcut**: JoinPoint를 골라내는 표현식. "어떤 메서드에 끼어들 것인가"를 정의한다.
- **Advice**: 끼어들었을 때 실제로 할 일. `@Before`, `@After`, `@Around` 같은 어노테이션이 Advice 종류를 결정한다.
- **Weaving**: Pointcut으로 골라낸 JoinPoint에 Advice를 결합하는 과정. Spring AOP는 런타임 위빙만 한다.

처음에는 JoinPoint와 Pointcut이 헷갈리는데, JoinPoint는 "후보 지점", Pointcut은 "그 후보 중 내가 고른 것"이라고 외워두면 편하다.

## 3. Spring AOP 동작 원리 — 프록시 기반

Spring AOP는 본질적으로 프록시 객체를 만들어서 빈을 감싼다. 컨테이너에 등록되는 빈은 원본이 아니라 프록시고, 호출자가 메서드를 부르면 프록시가 먼저 받아서 Advice를 실행한 뒤 원본 메서드로 위임한다.

### 3.1 JDK Dynamic Proxy vs CGLIB

```mermaid
flowchart LR
    A[Caller] --> B[Proxy]
    B --> C[Advice 체인]
    C --> D[Target Bean]
```

프록시를 만드는 방식이 두 가지다.

**JDK Dynamic Proxy**

- `java.lang.reflect.Proxy`로 만들고, **인터페이스가 반드시 있어야** 동작한다.
- 인터페이스 메서드만 프록시된다. 구현체에만 있는 public 메서드는 프록시 우회.
- 프록시 객체는 인터페이스 타입으로만 참조 가능. `(MyServiceImpl) bean`으로 캐스팅하면 `ClassCastException`이 터진다.

**CGLIB**

- 대상 클래스를 상속받아 서브클래스 프록시를 생성한다. 인터페이스가 없어도 됨.
- 상속 기반이라 `final` 클래스/메서드는 프록시할 수 없다. 메서드가 `final`이면 그 메서드만 조용히 프록시 우회되는 함정이 있다.
- `private`, `static` 메서드도 프록시 대상이 아니다.

### 3.2 프록시는 빈 생성 시점에 정해진다

프록시 여부와 종류는 호출할 때가 아니라 빈이 만들어질 때 결정된다. `@EnableAspectJAutoProxy`(Boot는 자동 설정)가 `AnnotationAwareAspectJAutoProxyCreator`라는 `BeanPostProcessor`를 등록하고, 이 후처리기가 모든 빈의 초기화가 끝난 직후 `postProcessAfterInitialization`에서 Advisor 목록을 훑는다. `@Aspect` 클래스의 Advice 메서드 하나하나와 `@Transactional`을 처리하는 `BeanFactoryTransactionAttributeSourceAdvisor`가 전부 이 목록에 들어 있다.

아래 흐름도는 그 판단 순서다. 매칭되는 Advisor가 하나도 없으면 프록시를 만들지 않고, 있으면 `proxyTargetClass`와 인터페이스 유무로 JDK/CGLIB을 고른다. 마지막 `final` 분기에서 실패 방식이 갈린다는 점을 보면 된다.

```mermaid
flowchart TD
    A["빈 초기화 완료<br/>postProcessAfterInitialization"] --> B["Advisor 목록 순회<br/>클래스 필터와 메서드 매처로 Pointcut 평가"]
    B --> C{"매칭되는 Advisor가 있는가"}
    C -->|없음| RAW["프록시 없이 원본 빈 등록"]
    C -->|있음| D{"proxyTargetClass=true 인가"}
    D -->|예| F{"대상 클래스가 final 인가"}
    D -->|아니오| E{"마커가 아닌 인터페이스가 있는가"}
    E -->|있음| JDK["JDK Dynamic Proxy<br/>인터페이스 타입으로만 주입 가능"]
    E -->|없음| F
    F -->|예| ERR["빈 생성 실패<br/>Cannot subclass final class"]
    F -->|아니오| CG["CGLIB 서브클래스 프록시<br/>final 메서드는 조용히 우회"]
```

Spring 6.1.14에서 `proxyTargetClass=false`로 직접 돌려 본 결과는 이렇다.

| 대상 빈 | 결과 |
|---|---|
| `Port` 인터페이스를 구현한 클래스 | JDK Dynamic Proxy |
| `Serializable`만 구현한 클래스 | CGLIB. `Serializable`, `InitializingBean` 같은 마커·콜백 인터페이스는 인터페이스로 치지 않는다 |
| 인터페이스가 없는 클래스 | CGLIB |
| 어떤 Pointcut에도 안 걸리는 클래스 | 프록시 아님. 원본 객체가 그대로 주입된다 |
| `final` 클래스 | `IllegalArgumentException: Cannot subclass final class` |
| 메서드만 `final` 인 클래스 | CGLIB 프록시는 만들어지지만 그 메서드에서 Advice가 실행되지 않는다 |

마지막 행이 문제다. 예외도 로그도 없이 빈은 정상 기동하고, `final` 메서드로 호출했을 때만 Advice가 빠진다. 3.4절의 `AopUtils`로 프록시 여부를 확인해도 `true`가 나오기 때문에, 메서드 단위로 한 번 호출해 봐야 안다.

### 3.3 Spring Boot의 기본값

Spring Boot 2.x부터 `proxyTargetClass=true`가 기본이다. 즉 인터페이스 유무와 무관하게 **CGLIB이 디폴트**다. 이유는 인터페이스가 있다가 나중에 구현체로 캐스팅이 필요해지는 경우 등 운영 사고가 빈번해서다.

명시적으로 바꾸려면:

```java
@SpringBootApplication
@EnableAspectJAutoProxy(proxyTargetClass = false) // JDK Dynamic Proxy 강제
public class Application { }
```

또는 `application.yml`:

```yaml
spring:
  aop:
    proxy-target-class: false
```

### 3.4 프록시 클래스명으로 디버깅하기

운영 중 디버거에 찍히는 클래스명을 보면 어떤 프록시인지 바로 안다.

```java
@Service
public class OrderService { }
```

- CGLIB 프록시: `OrderService$$EnhancerBySpringCGLIB$$abc1234`
- JDK Dynamic Proxy: `com.sun.proxy.$Proxy42` (인터페이스 타입으로 보임)

`AopUtils.isAopProxy(bean)`, `AopUtils.isCglibProxy(bean)`, `AopUtils.isJdkDynamicProxy(bean)`로 코드에서 확인할 수도 있다.

## 4. AspectJ vs Spring AOP — 무엇을 쓸 것인가

대부분의 백엔드 프로젝트에서는 Spring AOP로 충분하다. 하지만 한계를 명확히 알아둬야 한다.

| 항목 | Spring AOP | AspectJ |
|------|-----------|---------|
| 위빙 시점 | 런타임 (프록시) | 컴파일 타임 / 로드 타임 / 런타임 |
| JoinPoint 범위 | public 메서드 호출 | 메서드, 생성자, 필드, static 초기화 등 전부 |
| Self-invocation | 동작 안 함 | 정상 동작 |
| 의존성 | Spring만 있으면 됨 | aspectj-weaver, 별도 컴파일러/javaagent |
| 성능 오버헤드 | 프록시 호출 비용 | 거의 없음 (바이트코드 수정) |

운영 중 도메인 객체의 필드 접근까지 가로채야 하거나, 같은 클래스 내부 호출도 Advice가 적용되어야 하는 요구가 생기면 그제야 AspectJ를 검토하면 된다.

### Weaving 종류

- **Compile-time Weaving (CTW)**: AspectJ 컴파일러(`ajc`)가 `.class` 만들 때 Aspect를 박아넣는다. 빌드는 느려지지만 런타임 오버헤드가 가장 적다.
- **Load-time Weaving (LTW)**: JVM 클래스 로딩 시 javaagent(`aspectjweaver.jar`)가 바이트코드를 수정한다. 컴파일은 손대지 않아도 되지만 실행 옵션 관리가 귀찮다.
- **Runtime Weaving**: Spring AOP 방식. 프록시로 우회한다. 가장 제약이 많지만 가장 쉽다.

세 방식은 Advice가 코드에 들어가는 시점이 다르다. 오른쪽으로 갈수록 늦게 끼어들고, 늦을수록 건드릴 수 있는 범위가 좁아진다.

```mermaid
flowchart LR
    S["소스 컴파일"] --> L["클래스 로딩"] --> R["빈 생성과 메서드 호출"]
    CTW["CTW<br/>ajc가 .class에 Advice를 직접 삽입<br/>필드 접근, 생성자, self-invocation 모두 적용"] -.-> S
    LTW["LTW<br/>javaagent가 로딩 때 바이트코드 수정<br/>javac로 컴파일해도 되지만 -javaagent 필요"] -.-> L
    SPR["Spring AOP<br/>BeanPostProcessor가 프록시로 감쌈<br/>프록시를 거친 public 메서드 호출만 적용"] -.-> R
```

CTW는 빌드 파이프라인에 `ajc`를 넣어야 하고, LTW는 모든 실행 환경(로컬, 테스트, 컨테이너)에 같은 `-javaagent` 옵션을 맞춰야 한다. 한 군데라도 빠지면 그 환경에서만 Advice가 조용히 사라진다.

## 5. Advice 다섯 가지

같은 메서드에 여러 Advice가 걸리면 실행 순서는 정해져 있다. `@Around` → `@Before` → 메서드 실행 → `@AfterReturning`/`@AfterThrowing` → `@After` → `@Around`(after).

```java
@Aspect
@Component
public class LoggingAspect {

    @Pointcut("execution(* com.example.service..*Service.*(..))")
    public void serviceLayer() {}

    @Before("serviceLayer()")
    public void before(JoinPoint jp) {
        log.info("[Before] {}", jp.getSignature().toShortString());
    }

    @AfterReturning(pointcut = "serviceLayer()", returning = "result")
    public void afterReturning(JoinPoint jp, Object result) {
        log.info("[AfterReturning] {} -> {}", jp.getSignature().getName(), result);
    }

    @AfterThrowing(pointcut = "serviceLayer()", throwing = "ex")
    public void afterThrowing(JoinPoint jp, Throwable ex) {
        log.error("[AfterThrowing] {}: {}", jp.getSignature().getName(), ex.getMessage());
    }

    @After("serviceLayer()")
    public void after(JoinPoint jp) {
        // finally 블록처럼 항상 실행. 정상/예외 모두 통과.
    }

    @Around("serviceLayer()")
    public Object around(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.nanoTime();
        try {
            return pjp.proceed(); // 이거 빠뜨리면 메서드가 아예 실행되지 않음
        } finally {
            long elapsed = System.nanoTime() - start;
            log.info("[Around] {} took {} ns", pjp.getSignature().getName(), elapsed);
        }
    }
}
```

### 5.1 Aspect가 둘 이상일 때의 호출 순서

Aspect가 여러 개면 `@Order` 값이 작은 쪽이 바깥에서 감싼다. 양파 껍질처럼 바깥 Aspect의 Around와 Before가 먼저 실행되고, 안쪽 Aspect를 거쳐 대상 메서드에 닿는다. 돌아올 때는 같은 경로를 거꾸로 올라온다. 각각 `@Around`, `@Before`, `@AfterReturning`, `@AfterThrowing`, `@After`를 가진 Aspect A(`@Order(1)`)와 B(`@Order(2)`)를 같은 메서드에 걸고 로그를 찍어 확인한 순서다.

```mermaid
sequenceDiagram
    participant C as Caller
    participant A as Aspect A (Order 1)
    participant B as Aspect B (Order 2)
    participant T as Target
    C->>A: run()
    Note over A: A.Around 진입, A.Before
    A->>B: proceed()
    Note over B: B.Around 진입, B.Before
    B->>T: proceed()
    T-->>B: 정상 반환
    Note over B: B.AfterReturning, B.After, B.Around 복귀
    B-->>A: 반환
    Note over A: A.AfterReturning, A.After, A.Around 복귀
    A-->>C: 반환
```

한 Aspect 안에서는 Around 진입 → Before → 대상 → AfterReturning 또는 AfterThrowing → After → Around 복귀 순이다. 대상이 예외를 던지면 AfterReturning 자리에 AfterThrowing이 들어가고, 나머지는 같다. B의 예외는 B의 AfterThrowing을 거쳐 A로 올라가서 A의 AfterThrowing도 실행한다. 바깥 Aspect가 안쪽 Aspect의 결과(반환값, 예외)를 항상 나중에 본다는 게 포인트다. 트랜잭션과 재시도 문제가 전부 여기서 나온다.

`@Order`를 안 붙인 Aspect는 가장 낮은 우선순위(`Ordered.LOWEST_PRECEDENCE`)로 취급되고, 같은 값끼리의 순서는 스펙으로 보장되지 않는다. 순서에 의미가 있는 Aspect에는 값을 명시한다.

### 5.2 ProceedingJoinPoint.proceed() 누락 사고

`@Around`에서 가장 자주 발생하는 사고다. proceed()를 호출하지 않으면 원본 메서드가 실행되지 않은 채 Advice가 끝나고, 반환값은 null이 된다. 컴파일 에러도 없고 예외도 안 나서 운영에 올라간 뒤에야 "이 API 응답이 항상 비어 있어요"로 발견되곤 한다.

```java
@Around("...")
public Object around(ProceedingJoinPoint pjp) throws Throwable {
    log.info("call");
    return null; // 메서드 실행 누락 — 호출자는 영문도 모르고 NPE
}
```

리턴 타입이 primitive(예: `int`)면 NPE가 터지고, 객체면 조용히 null이 흐른다. 후자가 훨씬 위험하다.

### 5.3 proceed에 인자 넘기기

`pjp.proceed(args)`로 원본 메서드의 인자를 가공해서 넘길 수 있다. 입력 sanitize, 마스킹 같은 데 쓴다.

```java
@Around("execution(* save(..)) && args(dto)")
public Object around(ProceedingJoinPoint pjp, MyDto dto) throws Throwable {
    MyDto sanitized = dto.toBuilder().email(mask(dto.getEmail())).build();
    return pjp.proceed(new Object[] { sanitized });
}
```

## 6. Pointcut 표현식 전종

Pointcut 지정자는 여러 개고, 각각 잡는 대상이 다르다.

### 6.1 execution

가장 많이 쓴다. 메서드 시그니처를 직접 매칭한다.

```
execution([수식어] 리턴타입 [선언타입.]메서드이름(파라미터) [throws 예외])
```

```java
// 모든 public 메서드
@Pointcut("execution(public * *(..))")

// com.example.service 패키지(하위 포함)의 모든 메서드
@Pointcut("execution(* com.example.service..*.*(..))")

// 이름이 find로 시작, 인자 무관
@Pointcut("execution(* find*(..))")

// String 반환, 인자 1개
@Pointcut("execution(String *(*))")

// 인자가 (Long, ..) 형태 — 첫 인자 Long, 나머지 무관
@Pointcut("execution(* *(Long, ..))")
```

`..`은 패키지에서는 "하위 패키지 포함", 인자 자리에서는 "0개 이상의 인자"를 뜻한다. 헷갈리니까 매번 확인해야 한다.

### 6.2 within

타입(클래스) 단위로 매칭. execution보다 가볍게 쓴다.

```java
// OrderService 클래스 내부의 모든 메서드
@Pointcut("within(com.example.service.OrderService)")

// service 패키지 전체
@Pointcut("within(com.example.service..*)")
```

### 6.3 @annotation

메서드에 특정 어노테이션이 붙어 있을 때 매칭. 커스텀 어노테이션 패턴에서 가장 자주 쓴다.

```java
@Pointcut("@annotation(com.example.audit.Audited)")
public void audited() {}
```

### 6.4 @within vs @target

이 둘은 늘 헷갈린다.

- **@within(Annotation)**: 클래스에 어노테이션이 붙어 있는지를 **선언 타입 기준**으로 판단. 정적 결정.
- **@target(Annotation)**: 런타임 객체의 실제 타입에 어노테이션이 붙어 있는지를 판단. 동적 결정.

```java
@MyMarker
public class Parent {}
public class Child extends Parent {} // Child에는 @MyMarker 없음

// @within(MyMarker) — Child의 메서드는 매칭 안 됨 (선언 타입 기준)
// @target(MyMarker) — Child 인스턴스도 매칭됨 (런타임 타입이 @MyMarker 붙은 클래스를 상속)
```

`@target`은 Spring AOP에서는 CGLIB 프록시가 필요해서 비용이 더 든다.

### 6.5 target vs this

이건 AOP 입문자가 거의 다 틀린다.

- **target**: 프록시 뒤에 있는 **실제 객체**의 타입.
- **this**: 호출자 입장에서 본 **프록시 객체**의 타입.

JDK Dynamic Proxy를 쓸 때, `this(OrderServiceImpl)`은 매칭되지 않는다. 왜냐면 프록시가 인터페이스만 구현하지 `OrderServiceImpl`을 상속하지 않기 때문이다. CGLIB이라면 프록시가 `OrderServiceImpl`의 서브클래스라서 매칭된다.

```java
@Pointcut("target(com.example.service.OrderService)") // 실제 빈 타입
@Pointcut("this(com.example.service.OrderService)")   // 프록시 타입
```

운영 중 `target` 쓸 때가 더 많다.

### 6.6 args

런타임 인자 타입으로 매칭. 인자 바인딩에도 쓴다.

```java
@Pointcut("args(java.lang.String)")              // 인자 1개, String
@Pointcut("args(.., java.lang.Long)")            // 마지막 인자가 Long
@Before("args(userId)")                           // userId로 바인딩
public void before(String userId) { ... }
```

### 6.7 bean

빈 이름으로 매칭. Spring AOP 전용.

```java
@Pointcut("bean(orderService)")
@Pointcut("bean(*Service)")
```

### 6.8 조합

`&&`, `||`, `!`로 묶는다.

```java
@Pointcut(
  "execution(* com.example.service..*(..)) "
  + "&& @annotation(com.example.audit.Audited) "
  + "&& !within(com.example.service.internal..*)"
)
public void auditedServiceMethods() {}
```

여러 줄에 나눠 적을 때는 문자열 연결을 빼먹지 않게 주의한다.

## 7. Self-invocation 함정

가장 자주 발생하는 사고이자 신입 디버깅의 통과의례다.

```java
@Service
public class OrderService {

    @Transactional
    public void outer() {
        inner(); // this.inner() — 프록시 우회
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void inner() { ... }
}
```

`outer()`가 외부에서 호출되면 프록시를 거친다. 그런데 그 안에서 `inner()`를 부르면 `this.inner()`가 호출되고, 이는 원본 객체의 메서드 직접 호출이다. 프록시를 거치지 않으니 `@Transactional`도, `@Async`도, 모든 Advice가 무시된다.

`@Transactional`이 안 먹는 버그의 90%는 이 문제다.

### 해결법 1 — 자기 자신 주입

```java
@Service
public class OrderService {

    @Lazy
    @Autowired
    private OrderService self; // @Lazy 안 붙이면 순환 참조

    @Transactional
    public void outer() {
        self.inner(); // 프록시 호출
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void inner() { ... }
}
```

### 해결법 2 — AopContext.currentProxy()

```java
@SpringBootApplication
@EnableAspectJAutoProxy(exposeProxy = true) // 필수
public class Application { }
```

```java
public void outer() {
    ((OrderService) AopContext.currentProxy()).inner();
}
```

`exposeProxy=true`가 빠지면 `IllegalStateException`이 터진다. 그리고 ThreadLocal을 쓰는 방식이라 비동기 코드와 궁합이 나쁘다.

### 해결법 3 — 클래스 분리 (가장 권장)

내부 호출이 필요하다는 건 보통 책임이 두 개라는 신호다. `inner()`를 별도 빈으로 분리하면 자연스럽게 프록시를 거친다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final InnerService innerService;

    @Transactional
    public void outer() {
        innerService.run();
    }
}

@Service
public class InnerService {
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void run() { ... }
}
```

세 번째 방법을 가장 권한다. 앞의 두 개는 워크어라운드에 가깝다.

## 8. 실무 패턴 — 커스텀 어노테이션 + @Around

대부분의 실전 AOP는 이 조합으로 끝난다.

### 8.1 감사(Audit) 로그

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    String action();
}
```

```java
@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {
    private final AuditLogRepository repository;

    @Around("@annotation(audited)")
    public Object record(ProceedingJoinPoint pjp, Audited audited) throws Throwable {
        String userId = SecurityContextHolder.getContext().getAuthentication().getName();
        Object result = pjp.proceed();
        repository.save(AuditLog.of(userId, audited.action(), pjp.getArgs()));
        return result;
    }
}
```

```java
@Audited(action = "ORDER_CANCEL")
public void cancel(Long orderId) { ... }
```

### 8.2 실행 시간 측정

```java
@Around("@annotation(com.example.metric.Timed)")
public Object measure(ProceedingJoinPoint pjp) throws Throwable {
    long start = System.nanoTime();
    try {
        return pjp.proceed();
    } finally {
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;
        meterRegistry.timer("method.elapsed",
            "method", pjp.getSignature().toShortString())
            .record(elapsedMs, TimeUnit.MILLISECONDS);
    }
}
```

운영에서 슬로우 메서드 잡을 때 빠르게 도입할 수 있다.

### 8.3 재시도

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Retry {
    int max() default 3;
    long backoffMs() default 200;
}
```

```java
@Around("@annotation(retry)")
public Object run(ProceedingJoinPoint pjp, Retry retry) throws Throwable {
    int attempt = 0;
    while (true) {
        try {
            return pjp.proceed();
        } catch (Exception e) {
            attempt++;
            if (attempt >= retry.max()) throw e;
            Thread.sleep(retry.backoffMs() * attempt); // 단순 선형 백오프
        }
    }
}
```

Spring Retry를 쓰면 더 풍부하지만, 단순 케이스는 이걸로 충분하다. 단, 트랜잭션 내부에서 재시도하면 같은 트랜잭션이 롤백 마크된 채 재시도되어 의미가 없다. 트랜잭션 바깥(파사드 레이어 등)에서 적용해야 한다. 이 Aspect에 `@Order`를 안 붙이면 트랜잭션과 순서가 동률이 되어 안쪽에 들어가는 경우가 있다. 실제 로그는 9장에서 본다.

### 8.4 메서드 권한 체크

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RequireRole {
    String value();
}
```

```java
@Before("@annotation(requireRole)")
public void check(JoinPoint jp, RequireRole requireRole) {
    Authentication auth = SecurityContextHolder.getContext().getAuthentication();
    boolean ok = auth.getAuthorities().stream()
        .anyMatch(g -> g.getAuthority().equals("ROLE_" + requireRole.value()));
    if (!ok) throw new AccessDeniedException("권한 없음: " + requireRole.value());
}
```

Spring Security `@PreAuthorize`가 있는데도 굳이 만드는 경우는 도메인 규칙이 SpEL로 표현하기 까다로울 때다.

### 8.5 캐시 키 추출

```java
@Around("@annotation(cacheable)")
public Object cache(ProceedingJoinPoint pjp, MyCacheable cacheable) throws Throwable {
    String key = buildKey(cacheable.keyPrefix(), pjp.getArgs());
    Object hit = redis.opsForValue().get(key);
    if (hit != null) return hit;
    Object result = pjp.proceed();
    redis.opsForValue().set(key, result, cacheable.ttl(), TimeUnit.SECONDS);
    return result;
}
```

Spring Cache 추상화가 있긴 하지만, 키 생성 규칙이 복잡하거나 Redis Hash 같은 비표준 자료구조를 직접 다루고 싶을 때 직접 만든다.

## 9. @Transactional과 커스텀 Aspect의 순서 충돌

`@Transactional`도 결국 Aspect다. `TransactionInterceptor`라는 Advice가 메서드를 감싸고, 커스텀 Aspect와 같은 메서드에 걸리면 5.1절의 `@Order` 규칙이 그대로 적용된다. 재시도, 감사 로그, 분산 락처럼 트랜잭션 안이냐 밖이냐에 따라 의미가 달라지는 Aspect를 만들 때 이 순서가 사고로 이어진다.

### 9.1 트랜잭션 Advisor의 기본 순서는 맨 끝이다

`@EnableTransactionManagement`의 `order` 속성 기본값은 `Ordered.LOWEST_PRECEDENCE`, 즉 `Integer.MAX_VALUE`다. Spring 6.1.14에서 `BeanFactoryTransactionAttributeSourceAdvisor.getOrder()`를 찍으면 2147483647이 나온다. `@Order`를 안 붙인 커스텀 Aspect도 같은 값이라 둘은 동률이다.

동률이면 누가 바깥인지 스펙으로 정해져 있지 않다. 아래 재현에서는 `@Order`가 없는 RetryAspect가 트랜잭션 안쪽에 들어갔다. 이 결과는 Advisor 등록 순서에 걸려 있는 우연이라, 버전을 올리거나 빈 정의 순서가 바뀌면 뒤집힌다.

| RetryAspect 설정 | 트랜잭션 대비 위치 | 시도마다 |
|---|---|---|
| `@Order(0)` | 바깥 | 새 트랜잭션 시작 |
| `@Order` 없음 | 동률, 보장 없음 | 이 재현에서는 한 트랜잭션을 공유 |
| `@EnableTransactionManagement(order = 50)`처럼 트랜잭션 값을 더 작게 | 안쪽 | 한 트랜잭션을 공유 |

### 9.2 재시도가 트랜잭션 안쪽에 있을 때

재현에 쓴 코드다. `OrderService.order()`가 `@Transactional`이고, 그 안에서 부르는 `PaymentClient.charge()`도 `@Transactional`(기본 REQUIRED)이다. 결제 호출은 앞의 두 번을 `IllegalStateException`으로 실패하고 세 번째에 성공한다. 트랜잭션 매니저는 begin, commit, rollback, rollback-only 표시를 출력하는 스텁으로 바꿨다.

```java
@Retention(RetentionPolicy.RUNTIME)
@interface Retry { int max() default 3; }

@Aspect
class RetryAspect implements Ordered {
    private final int order;
    RetryAspect(int order) { this.order = order; }
    public int getOrder() { return order; }

    @Around("@annotation(retry)")
    public Object run(ProceedingJoinPoint pjp, Retry retry) throws Throwable {
        for (int i = 1; ; i++) {
            System.out.println(" [Retry] attempt " + i);
            try {
                return pjp.proceed();
            } catch (IllegalStateException e) {
                if (i >= retry.max()) throw e;
            }
        }
    }
}

class OrderService {
    private final PaymentClient paymentClient;
    OrderService(PaymentClient paymentClient) { this.paymentClient = paymentClient; }

    @Retry
    @Transactional
    public void order() { paymentClient.charge(); }
}

class PaymentClient {
    private int calls = 0;

    @Transactional
    public void charge() {
        if (++calls < 3) throw new IllegalStateException("timeout#" + calls);
    }
}
```

`RetryAspect`를 `LOWEST_PRECEDENCE`로 두면 이렇게 나온다.

```
[TX 1] begin
 [Retry] attempt 1
[TX 1] mark rollback-only
 [Retry] attempt 2
[TX 1] mark rollback-only
 [Retry] attempt 3
   charge ok
[TX 1] mark rollback-only
[TX 1] rollback
RESULT UnexpectedRollbackException: Transaction rolled back because it has been marked as rollback-only
```

세 번째 시도에서 결제가 성공했는데도 호출자는 `UnexpectedRollbackException`을 받는다. 내부 `charge()`의 `@Transactional(REQUIRED)`는 새 트랜잭션을 여는 게 아니라 바깥 트랜잭션 1번에 참여한다. 참여한 쪽에서 예외가 나가면 `TransactionInterceptor`가 공유 트랜잭션에 rollback-only를 표시한다. 재시도 Aspect가 예외를 삼켜도 이 표시는 지워지지 않고, 마지막에 `order()`가 정상 반환해서 커밋하려는 순간 매니저가 표시를 보고 롤백한다. 흐름은 이렇다.

```mermaid
sequenceDiagram
    participant Tx as TransactionInterceptor
    participant R as RetryAspect
    participant S as OrderService
    participant P as PaymentClient 프록시
    Tx->>Tx: 트랜잭션 1 시작
    Tx->>R: proceed()
    R->>S: 시도 1
    S->>P: charge()
    P-->>S: 예외 (REQUIRED라서 트랜잭션 1에 참여한 상태)
    Note over P: 트랜잭션 1에 rollback-only 표시
    S-->>R: 예외 전파
    R->>S: 시도 2, 같은 트랜잭션
    S->>P: charge()
    P-->>S: 예외, 표시는 그대로
    R->>S: 시도 3
    S->>P: charge()
    P-->>S: 성공
    S-->>R: 정상 반환
    R-->>Tx: 정상 반환
    Tx->>Tx: 커밋 시도
    Note over Tx: rollback-only 확인, 롤백 후 UnexpectedRollbackException
```

예외가 `@Transactional` 경계를 넘지 않는 경우에는 표시가 안 붙어서 마지막에 커밋이 되어 버린다. 이때는 앞 시도에서 이미 실행된 INSERT·UPDATE가 같은 트랜잭션에 남아 있다가 같이 커밋된다. 중복 행이 생기는 쪽이 `UnexpectedRollbackException`보다 훨씬 늦게 발견된다. JPA를 쓰면 예외가 난 뒤의 영속성 컨텍스트 상태도 믿을 수 없게 된다.

백오프 대기도 문제다. 재시도가 트랜잭션 안쪽이면 `Thread.sleep(backoffMs)` 동안 DB 커넥션을 쥐고 있다. 재시도가 몰리는 장애 상황에서 커넥션 풀이 먼저 바닥나는 경우가 있다.

### 9.3 재시도가 트랜잭션 바깥에 있을 때

같은 코드에서 `RetryAspect`의 order만 `0`으로 바꾼 결과다.

```
 [Retry] attempt 1
[TX 1] begin
[TX 1] mark rollback-only
[TX 1] rollback
 [Retry] attempt 2
[TX 2] begin
[TX 2] mark rollback-only
[TX 2] rollback
 [Retry] attempt 3
[TX 3] begin
   charge ok
[TX 3] commit
RESULT ok
```

시도마다 트랜잭션이 새로 열리고, 실패한 시도는 rollback-only 표시와 함께 통째로 롤백된 뒤 버려진다. 세 번째 시도는 깨끗한 트랜잭션에서 시작해서 정상 커밋된다. 백오프 대기는 트랜잭션 밖에서 일어나므로 커넥션도 반납된 상태다.

```mermaid
flowchart LR
    subgraph outside["Retry 바깥 (Order 0)"]
        direction TB
        O1["RetryAspect"] --> O2["TransactionInterceptor<br/>트랜잭션 시작"]
        O2 --> O3["OrderService.order()"]
        O3 -->|예외| O4["롤백, 트랜잭션 종료"]
        O4 -->|재시도| O1
    end
    subgraph inside["Retry 안쪽 (동률 또는 더 큰 값)"]
        direction TB
        I1["TransactionInterceptor<br/>트랜잭션 시작"] --> I2["RetryAspect"]
        I2 --> I3["OrderService.order()"]
        I3 -->|예외| I4["rollback-only 표시, 트랜잭션 유지"]
        I4 -->|재시도| I2
    end
```

### 9.4 순서를 코드로 고정한다

재시도는 `@Order`를 명시해서 트랜잭션보다 바깥에 고정한다. 값은 상수로 한곳에 모아 두면 Aspect가 늘어도 상대 위치를 한눈에 본다.

```java
public final class AspectOrder {
    public static final int RETRY = 100;   // 트랜잭션 바깥. 시도마다 새 트랜잭션
    public static final int AUDIT = 200;   // 트랜잭션 바깥. 업무 트랜잭션이 롤백돼도 감사 로그는 남김
    // TransactionInterceptor는 Ordered.LOWEST_PRECEDENCE
}

@Aspect
@Component
@Order(AspectOrder.RETRY)
public class RetryAspect { /* 위와 동일 */ }
```

8.1의 `AuditAspect`도 order에 따라 동작이 달라진다. 트랜잭션 바깥이면 `repository.save()`가 별도 트랜잭션으로 커밋되어 업무 로직이 롤백돼도 감사 로그가 남고, 안쪽이면 업무 트랜잭션과 함께 롤백된다. 어느 쪽이 요구사항인지 정하고 order로 표현해야 한다.

트랜잭션 쪽 order를 바꿔야 하면 `@EnableTransactionManagement(order = ...)`로 조정한다. 실제 순서가 의도대로인지는 로그로 확인한다. `org.springframework.transaction.interceptor`를 TRACE로 올리면 트랜잭션이 열리는 지점이 찍히므로, 재시도 로그보다 앞에 찍히는지 뒤에 찍히는지가 곧 바깥/안쪽 판별이다.

## 10. 트러블슈팅 — 프록시가 안 잡힐 때

"Aspect를 분명히 만들었는데 안 동작해요"라는 질문이 들어오면 거의 다음 중 하나다.

### 10.1 같은 클래스 내부 호출

7장의 self-invocation 문제. 가장 흔하다.

### 10.2 private/static 메서드

Spring AOP는 public 메서드만 프록시한다. CGLIB이라도 `private`은 상속이 안 되므로 불가, `static`은 인스턴스가 아니므로 불가. 개발 중 `private`을 임시로 `public`으로 바꿔 동작 여부 확인하는 식으로 자주 디버깅한다.

### 10.3 final 메서드/클래스

CGLIB은 상속 기반이라 `final`이면 프록시 못 만든다. 대상 클래스가 통째로 `final`이면 빈 등록 시점에 예외, 메서드만 `final`이면 그 메서드는 조용히 우회된다. 후자가 정말 디버깅하기 어렵다.

Kotlin 클래스는 기본 `final`이라 `kotlin-allopen` 플러그인 + `@SpringBootApplication` 조합이 필요하다.

### 10.4 컴포넌트 스캔 누락

`@Aspect`만 붙어 있고 `@Component`(또는 `@Configuration`의 `@Bean`)가 없으면 빈으로 안 올라간다. 두 어노테이션 다 필요하다.

### 10.5 @EnableAspectJAutoProxy 누락

Spring Boot의 `spring-boot-starter-aop`를 쓰면 자동 활성화되지만, 순수 Spring 환경이거나 의존성을 직접 관리하면 명시해야 한다.

```java
@Configuration
@EnableAspectJAutoProxy
public class AopConfig { }
```

### 10.6 Pointcut 표현식 오타

`execution(* com.example.serivce..*(..))` 같은 패키지명 오타는 컴파일러가 안 잡는다. AspectJ 표현식은 문자열이라 IDE 도움도 제한적이다. 동작 안 하면 의심해야 하는 첫 번째 항목이다.

### 10.7 Aspect 자체를 디버깅

빈이 프록시인지 확인하는 가장 빠른 방법.

```java
@Component
@RequiredArgsConstructor
public class StartupCheck implements ApplicationRunner {
    private final OrderService orderService;

    @Override
    public void run(ApplicationArguments args) {
        log.info("class = {}", orderService.getClass()); // CGLIB이면 $$EnhancerBy...
        log.info("isAopProxy = {}", AopUtils.isAopProxy(orderService));
    }
}
```

## 11. 정리하면서

AOP는 로깅, 감사, 메트릭, 권한, 트랜잭션처럼 횡단 관심사가 분명하고 비즈니스 로직과 무관하며 어노테이션 + `@Around` 조합으로 끝나는 곳에만 쓸 때 코드가 읽기 쉬워진다. 리팩토링이 귀찮아서 AOP로 우회하기 시작하면 어디서 호출되는지 추적이 안 되는 코드가 된다. 디버깅은 결국 누가 한다.

Aspect가 하나일 때는 대부분 문제가 없다. 사고는 둘 이상이 겹칠 때 난다. 프록시는 빈 생성 시점에 한 번 정해지고(3.2절), 겹친 Aspect는 `@Order`가 작은 쪽부터 안으로 들어가며(5.1절), `@Transactional`은 그 줄 맨 끝에 서 있다(9장). 재시도처럼 트랜잭션 안팎에 따라 의미가 달라지는 Aspect에는 `@Order`를 명시하고, 동작이 이상하면 프록시 종류와 Advisor 순서부터 로그로 확인한다.

트랜잭션 쪽 이야기는 이 문서에서 순서 문제만 다뤘다. 전파 옵션, 롤백 규칙, `readOnly`, 커넥션 점유와 풀 고갈, 커밋 후 처리까지 이어서 보려면 [Spring AOP & 트랜잭션 심화](../../../Framework/Java/Spring/AOP_트랜잭션.md)를 읽는다.
