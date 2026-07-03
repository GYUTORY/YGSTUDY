---
title: Spring AOP & 트랜잭션 심화
tags: [framework, java, spring, aop, transaction, aspect, transactional, propagation, isolation]
updated: 2026-04-30
---

# Spring AOP & 트랜잭션 심화

## 시작하기 전에

이 문서는 `@Transactional`을 한 번이라도 붙여본 사람이 읽는다는 가정으로 쓴다. 동작 원리보다는 실제로 운영하면서 만난 문제들을 정리한다. "트랜잭션이 안 걸려요", "롤백이 안 돼요", "왜 데드락이 나죠" 같은 질문이 반복적으로 들어오는데, 원인은 거의 정해져 있다. 프록시 구조를 모르거나, 전파 옵션을 잘못 골랐거나, 격리 수준이 어떻게 동작하는지 모르거나.

---

## AOP의 본질: 프록시 객체

Spring AOP는 컴파일 시점에 코드를 바꾸지 않는다. 런타임에 대상 빈을 감싼 프록시 객체를 만들어서 컨테이너에 등록한다. `@Autowired`나 `@RequiredArgsConstructor`로 주입받는 빈은 원본이 아니라 프록시다. 이 사실 하나만 정확히 이해해도 트랜잭션 트러블슈팅의 80%는 해결된다.

프록시는 두 가지 방식으로 만들어진다. 인터페이스가 있으면 JDK Dynamic Proxy를, 없으면 CGLIB로 클래스를 상속해서 만든다. Spring Boot 2.x부터는 기본값이 CGLIB로 바뀌었고, `spring.aop.proxy-target-class=false`로 명시하지 않는 한 항상 CGLIB가 동작한다. CGLIB는 클래스를 상속하기 때문에 `final` 클래스나 `final` 메서드를 프록시할 수 없다. 이게 뒤에서 다룰 함정 중 하나다.

```
호출 흐름:

  Controller → ProxyBean.method() → Interceptor → TargetBean.method()
                     ↑
              여기서 트랜잭션 시작/커밋
```

프록시는 외부에서 들어오는 호출만 가로챈다. 같은 객체 안에서 `this.method()`로 호출하는 순간 프록시를 거치지 않으므로 어떤 어드바이스도 동작하지 않는다.

---

## Pointcut 표현식 핵심

Pointcut은 어디에 어드바이스를 적용할지 지정하는 표현식이다. 실무에서 가장 많이 쓰는 형태는 세 가지다.

```java
// 패키지 + 클래스 + 메서드 패턴
execution(* com.example.service..*.*(..))

// 어노테이션 기반 (가장 명시적이라 권장)
@annotation(com.example.annotation.AuditLog)

// 두 조건의 교집합
execution(* com.example.service..*.*(..)) && @annotation(org.springframework.transaction.annotation.Transactional)
```

`execution` 표현식을 너무 넓게 잡으면 의도하지 않은 메서드까지 AOP가 적용되면서 성능 저하나 무한 루프 같은 문제가 생긴다. `getter/setter`가 트랜잭션 어드바이스에 걸려서 매 호출마다 트랜잭션 매니저가 동작하는 사례를 종종 본다. 어노테이션 기반 Pointcut을 쓰는 게 가장 안전하다.

---

## Advice 5종과 실행 순서

`@Around`는 메서드 실행 전후를 모두 감싸므로 가장 자주 쓴다. 하지만 `joinPoint.proceed()`를 호출하지 않으면 원본 메서드가 아예 실행되지 않는다. 호출 누락은 "메서드를 호출했는데 아무 일도 안 일어나요" 같은 황당한 버그로 이어진다.

```java
@Aspect
@Component
@Slf4j
public class ExecutionTimeAspect {

    @Around("@annotation(com.example.annotation.MeasureTime)")
    public Object measure(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.nanoTime();
        try {
            return pjp.proceed();
        } finally {
            long elapsedMs = (System.nanoTime() - start) / 1_000_000;
            log.info("{} took {}ms", pjp.getSignature().toShortString(), elapsedMs);
        }
    }
}
```

여러 Aspect가 같은 메서드에 걸리면 `@Order` 값으로 순서를 제어한다. 값이 작을수록 바깥쪽 프록시가 된다. 트랜잭션 Aspect는 기본 `Order.LOWEST_PRECEDENCE - 100`으로 등록되는데, 커스텀 Aspect가 트랜잭션 안쪽에서 동작해야 한다면 더 큰 값을 줘야 한다. 거꾸로 트랜잭션 시작 전에 동작해야 할 검증 Aspect라면 더 작은 값을 줘야 한다. 이 순서를 잘못 잡으면 `@Around`에서 던진 예외가 트랜잭션 롤백에 영향을 못 주는 상황이 생긴다.

---

## @Transactional이 안 먹는 6가지 케이스

운영에서 가장 자주 겪는 문제다. 하나씩 원인과 진단법까지 본다.

### 1. Self-invocation (같은 객체 내부 호출)

가장 흔한 케이스다. 같은 클래스 내에서 `this.someMethod()`로 호출하면 프록시를 우회하므로 `@Transactional`이 적용되지 않는다.

```java
@Service
public class OrderService {

    public void createOrder(OrderRequest req) {
        validate(req);
        save(req);  // 프록시 거치지 않음 → @Transactional 무시
    }

    @Transactional
    public void save(OrderRequest req) {
        orderRepository.save(toEntity(req));
    }
}
```

진단 방법은 의외로 간단하다. `TransactionSynchronizationManager.isActualTransactionActive()`를 메서드 진입 시점에서 찍어보면 된다. `false`가 나오면 트랜잭션이 시작되지 않은 것이다. 또는 Hibernate 로그 레벨을 `org.hibernate.engine.transaction=DEBUG`로 올려서 트랜잭션 begin 로그가 찍히는지 확인한다.

해결 방법은 클래스를 분리하는 게 가장 깔끔하다. 자기 자신을 주입하는 방식은 동작은 하지만 코드를 보는 사람이 의도를 파악하기 어렵다. `AopContext.currentProxy()`를 쓰는 방법도 있는데 `exposeProxy = true` 설정이 필요하고 침투적이라 잘 안 쓴다.

### 2. private/protected 메서드

CGLIB 프록시는 클래스를 상속해서 메서드를 오버라이드하는 방식이라 `private` 메서드는 오버라이드할 수 없다. `protected`나 package-private은 오버라이드는 가능하지만 Spring의 트랜잭션 어드바이저가 `public` 메서드만 대상으로 삼도록 기본 설정되어 있다. 결과적으로 `private` 메서드에 `@Transactional`을 붙이면 IDE도 경고를 안 띄우는데 동작은 안 한다.

```java
@Service
public class ReportService {

    public void generate(Long id) {
        process(id);
    }

    @Transactional  // 동작 안 함
    private void process(Long id) {
        ...
    }
}
```

진단은 메서드 시그니처를 `public`으로 바꿔보고 동작이 달라지는지 확인하는 게 가장 빠르다. Spring Boot 6 / Spring Framework 7부터 `@Transactional`을 `protected`나 package-private에서도 인식하도록 옵션이 추가되었지만, 기본값은 여전히 `public`만이다.

### 3. Checked Exception은 기본적으로 롤백 안 됨

이게 가장 위험한 함정이다. `RuntimeException`과 `Error`는 자동 롤백되지만, `IOException`, `SQLException` 같은 Checked Exception은 던져도 트랜잭션이 그대로 커밋된다. EJB 시절의 규약을 그대로 따르는 건데, Java 진영 외에는 거의 모르는 동작이다.

```java
@Transactional
public void importFile(Path path) throws IOException {
    repository.save(...);
    Files.readAllBytes(path);  // IOException → 데이터는 커밋됨
}
```

진단은 어렵다. 예외가 던져졌으니 호출자는 실패했다고 생각하는데 DB에는 데이터가 남는다. 데이터 정합성 사고가 며칠 뒤에 발견되는 경우가 많다. 모든 예외에 대해 롤백하려면 `rollbackFor = Exception.class`를 명시적으로 붙이거나, 사내 Custom Exception 정책으로 RuntimeException 상속을 강제하는 방식을 쓴다.

### 4. AOP Aspect 순서 문제

트랜잭션 Aspect와 다른 커스텀 Aspect가 같은 메서드에 걸릴 때 순서를 잘못 잡으면 트랜잭션이 의도와 다르게 동작한다. 흔한 케이스는 재시도(retry) Aspect가 트랜잭션 바깥에서 도는 게 아니라 안쪽에서 도는 경우다.

```java
@Aspect
@Order(0)  // 트랜잭션보다 안쪽
public class RetryAspect {
    @Around("@annotation(retry)")
    public Object retry(ProceedingJoinPoint pjp, Retry retry) throws Throwable {
        for (int i = 0; i < retry.maxAttempts(); i++) {
            try { return pjp.proceed(); }
            catch (Exception e) { if (i == retry.maxAttempts() - 1) throw e; }
        }
        return null;
    }
}
```

`@Order(0)`이면 RetryAspect가 바깥쪽이라 트랜잭션이 매번 새로 시작되지만, 위 코드처럼 잘못 이해하고 트랜잭션 안에서 retry를 돌리면 한 번 롤백된 트랜잭션 위에서 재시도하게 되어 의미가 없어진다. 진단은 `@Order` 값을 명시하고 디버거로 어드바이저 체인을 확인한다. `org.springframework.aop.framework.JdkDynamicAopProxy` 또는 `CglibAopProxy`에 브레이크포인트를 걸면 어떤 순서로 인터셉터가 호출되는지 보인다.

### 5. 프록시 우회 호출 (직접 new 또는 ApplicationContext 우회)

빈을 직접 `new`로 생성해서 사용하면 당연히 프록시가 아니라 원본 객체이므로 어떤 AOP도 동작하지 않는다. 더 미묘한 케이스는 `ApplicationContextAware`로 컨텍스트에서 빈을 꺼낼 때 타입을 인터페이스가 아닌 구현체로 지정한 경우인데, 일반적으로는 같은 프록시 객체가 반환되므로 큰 문제는 없다. 정작 문제가 되는 건 컴포넌트 스캔 범위 밖에서 빈이 생성되는 경우다. 테스트 코드에서 수동으로 객체를 만들어서 검증하면 트랜잭션이 안 걸린다.

```java
// 테스트 코드 — 트랜잭션 동작 안 함
OrderService service = new OrderService(orderRepository);
service.createOrder(req);
```

통합 테스트에서는 `@SpringBootTest`로 컨테이너에서 빈을 가져와야 트랜잭션이 적용된다. 단위 테스트에서 트랜잭션 동작까지 검증하려면 별도의 통합 테스트로 분리해야 한다.

### 6. final 클래스 / final 메서드

CGLIB는 상속을 통해 프록시를 만들기 때문에 `final` 클래스는 프록시 자체가 불가능하고, `final` 메서드는 오버라이드되지 않아서 어드바이스가 적용되지 않는다. Kotlin으로 Spring을 쓸 때 자주 만나는 문제인데, Kotlin 클래스는 기본이 `final`이라 `kotlin-spring` 플러그인을 적용해야 자동으로 `open` 처리된다.

```java
@Service
public final class PaymentService {  // final → 프록시 생성 실패
    @Transactional
    public void pay(Long id) { ... }
}
```

Spring Boot 시작 시 `Could not generate CGLIB subclass of class ... : final classes can not be subclassed` 같은 예외가 뜨면 이 케이스다. JDK Proxy(인터페이스 기반)로 강제하는 방법도 있지만 권장하진 않는다.

---

## 트랜잭션 전파 7종 완벽 정리

전파(Propagation)는 트랜잭션 경계가 중첩될 때 어떻게 동작할지를 결정한다. 7종이 있는데, 실제로는 `REQUIRED`와 `REQUIRES_NEW`만 거의 다 쓴다. 그래도 나머지를 알아야 의도치 않은 동작을 막을 수 있다.

### REQUIRED (기본값)

기존 트랜잭션이 있으면 참여하고, 없으면 새로 만든다. 가장 직관적이지만 함정이 하나 있다. 참여한 트랜잭션이 내부에서 롤백을 결정하면 외부 트랜잭션 전체가 `UnexpectedRollbackException`으로 롤백된다. "분명히 try/catch로 잡았는데 왜 롤백이 되죠"라는 질문의 정답이 이거다.

```java
@Transactional  // 외부
public void outer() {
    try {
        inner();  // 내부에서 예외 → 외부 트랜잭션도 rollback-only로 마킹
    } catch (Exception e) {
        // 예외는 잡았지만 트랜잭션은 이미 롤백 결정됨
    }
    // 커밋 시점에 UnexpectedRollbackException 발생
}

@Transactional
public void inner() { throw new RuntimeException(); }
```

내부 메서드의 예외를 외부에서 무시하고 싶다면 내부를 `REQUIRES_NEW`로 분리하거나, 별도의 빈으로 떼어내야 한다.

### REQUIRES_NEW

기존 트랜잭션을 일시 정지(suspend)하고 항상 새 트랜잭션을 시작한다. 새 트랜잭션은 별도의 DB 커넥션을 잡는다. 외부와 완전히 독립적이라 외부 롤백에 영향받지 않는다. 알림 발송, 감사 로그, 이벤트 기록처럼 본 트랜잭션과 무관하게 무조건 남겨야 하는 작업에 쓴다.

주의할 점은 커넥션을 추가로 사용한다는 점이다. 외부 트랜잭션이 커넥션 1개, 내부가 1개를 잡으니 동시에 2개를 점유한다. 커넥션 풀 크기가 작은 환경에서 `REQUIRES_NEW`를 남발하면 데드락이나 풀 고갈로 이어진다. HikariCP 기본값이 10인데, 10개의 외부 트랜잭션이 모두 `REQUIRES_NEW` 내부 호출에 들어가면 그 자리에서 멈춘다.

### NESTED

물리적으로는 같은 트랜잭션이지만 SAVEPOINT를 만들어서 부분 롤백이 가능하게 한다. JDBC `Connection.setSavepoint()`를 사용하므로 JTA 환경에서는 동작하지 않는다. JPA에서도 일부 드라이버는 지원하지 않는다.

```java
@Transactional  // 외부
public void importBatch(List<Item> items) {
    for (Item item : items) {
        try {
            saveOne(item);  // NESTED
        } catch (DataIntegrityViolationException e) {
            log.warn("skip: {}", item);  // SAVEPOINT 롤백, 외부는 살아있음
        }
    }
}

@Transactional(propagation = Propagation.NESTED)
public void saveOne(Item item) { ... }
```

배치 처리에서 일부 실패는 건너뛰고 나머지는 커밋해야 할 때 유용하다. 다만 외부 트랜잭션이 롤백되면 SAVEPOINT는 의미가 없어진다.

### SUPPORTS

기존 트랜잭션이 있으면 참여하고, 없으면 트랜잭션 없이 실행한다. 트랜잭션이 없는 상태에서도 동작은 하지만, JPA를 쓴다면 영속성 컨텍스트가 트랜잭션 단위로 관리되므로 이상한 동작이 생긴다. 거의 안 쓴다.

### NOT_SUPPORTED

기존 트랜잭션을 일시 정지하고 트랜잭션 없이 실행한다. 트랜잭션 안에서 실행하면 락이 길어지는 느린 조회나 외부 API 호출을 분리할 때 쓴다. 다만 이런 경우 호출하는 메서드 자체에 트랜잭션을 빼는 게 더 깔끔하다.

### MANDATORY

기존 트랜잭션이 반드시 있어야 한다. 없으면 `IllegalTransactionStateException`을 던진다. 항상 다른 트랜잭션의 일부로만 호출되어야 하는 메서드를 강제할 때 쓴다. 라이브러리 내부 메서드에 가끔 본다.

### NEVER

기존 트랜잭션이 있으면 예외를 던진다. 절대로 트랜잭션 안에서 호출되면 안 되는 메서드를 보호할 때 쓴다. 외부 시스템 호출처럼 트랜잭션 길이에 영향을 주면 안 되는 작업에 가끔 쓴다.

---

## 격리 수준 4단계와 이상 현상

격리 수준은 동시에 실행되는 트랜잭션끼리 서로의 데이터를 어디까지 볼 수 있는지를 결정한다. 격리가 강할수록 정합성은 좋아지지만 동시성은 떨어진다. 격리 수준은 ANSI SQL 표준에 정의되어 있고, DB 별로 구현이 미묘하게 다르다.

세 가지 이상 현상이 있다.

**Dirty Read**: 다른 트랜잭션이 아직 커밋하지 않은 데이터를 읽는 것. A가 잔액을 100→200으로 바꾸고 커밋 전인데 B가 200을 읽고 처리한 뒤, A가 롤백하면 B는 존재하지 않는 데이터로 작업한 게 된다.

**Non-Repeatable Read**: 같은 트랜잭션 안에서 같은 행을 두 번 조회했는데 값이 다른 것. 첫 조회와 두 번째 조회 사이에 다른 트랜잭션이 그 행을 UPDATE하고 커밋했기 때문이다.

**Phantom Read**: 같은 트랜잭션 안에서 같은 조건으로 조회했는데 결과 행 수가 다른 것. 다른 트랜잭션이 INSERT/DELETE를 하고 커밋했기 때문이다. Non-Repeatable이 행의 값 변경이라면, Phantom은 행의 존재 자체가 달라진다.

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|---------|-----------|--------------------|---------------|
| READ_UNCOMMITTED | 발생 | 발생 | 발생 |
| READ_COMMITTED | 방지 | 발생 | 발생 |
| REPEATABLE_READ | 방지 | 방지 | 발생(표준) / 방지(MySQL InnoDB) |
| SERIALIZABLE | 방지 | 방지 | 방지 |

여기서 주의할 점이 두 가지다. 첫째, MySQL InnoDB의 `REPEATABLE_READ`는 표준과 달리 Phantom Read도 막는다. 갭 락(Gap Lock)을 사용해서 범위 자체를 잠그기 때문이다. 둘째, PostgreSQL의 `READ_UNCOMMITTED`는 사실상 `READ_COMMITTED`로 동작한다. PostgreSQL은 MVCC 기반이라 dirty read 자체가 불가능하다.

```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public Report calculate() {
    // 같은 행을 여러 번 조회해도 같은 값 보장
}
```

운영에서 격리 수준을 명시적으로 지정하는 경우는 드물다. 대부분 DB 기본값(MySQL은 REPEATABLE_READ, PostgreSQL/Oracle은 READ_COMMITTED)을 따른다. 격리 수준을 올리는 것보다 비관적 락(`SELECT ... FOR UPDATE`)이나 낙관적 락(`@Version`)을 쓰는 게 더 명확한 경우가 많다.

---

## rollbackFor / noRollbackFor 사용 패턴

기본 동작은 명확히 외워둬야 한다.

- `RuntimeException`과 `Error` → 롤백
- `Exception` (Checked) → 커밋

이 동작을 바꾸는 게 `rollbackFor`와 `noRollbackFor`다.

```java
// 모든 예외에 대해 롤백 (Checked Exception 포함)
@Transactional(rollbackFor = Exception.class)
public void importBatch() throws IOException { ... }

// 특정 비즈니스 예외는 정상 흐름이므로 커밋
@Transactional(noRollbackFor = NotFoundException.class)
public Optional<User> findOrCreate(Long id) {
    try { return Optional.of(repository.findOrThrow(id)); }
    catch (NotFoundException e) { return Optional.empty(); }
}
```

`noRollbackFor`를 쓰는 패턴은 비즈니스 흐름상 예외지만 데이터는 그대로 둬야 할 때다. 예를 들어 검증 실패 로그를 남겨야 하는데 검증 실패 자체가 RuntimeException으로 던져지는 구조라면 `noRollbackFor`로 로그 INSERT가 살아남게 한다.

실무에서 더 깔끔한 방식은 회사 차원의 베이스 예외 클래스 두 개를 만드는 것이다. `BusinessException extends RuntimeException`은 항상 롤백, `RecoverableException extends RuntimeException`은 `noRollbackFor`로 지정하는 식이다. 매번 `rollbackFor`를 붙이는 것보다 일관성이 있다.

`rollbackFor = Exception.class`는 거의 모든 프로젝트에서 디폴트로 깔아둘 만하다. Java의 Checked Exception 자동 커밋 정책은 사실상 버그 유발 요인이다.

---

## readOnly = true의 실제 효과

`@Transactional(readOnly = true)`는 단순한 힌트가 아니다. 실제로 여러 단계에서 동작이 바뀐다.

**Hibernate Flush Mode**: `FlushType.MANUAL`로 설정되어 영속성 컨텍스트의 dirty checking이 비활성화된다. 트랜잭션 종료 시점에 변경 감지를 위한 스냅샷 비교를 건너뛰므로 메모리와 CPU를 절약한다. 조회만 하는 메서드에서는 무조건 켜는 게 이득이다.

**JDBC Connection 힌트**: Spring이 `Connection.setReadOnly(true)`를 호출한다. 일부 드라이버(예: MySQL Connector/J)는 이를 보고 read replica로 라우팅하거나, 트랜잭션 로그 기록을 줄이는 최적화를 한다. 단 동작은 드라이버마다 다르므로 의존하면 안 된다.

**스프링 데이터 라우팅**: `AbstractRoutingDataSource`로 read-only일 때 슬레이브 DB를 보도록 구성한 환경에서는 이 플래그가 라우팅 키가 된다. read replica가 있는 운영 환경에서는 거의 필수다.

```java
@Transactional(readOnly = true)
public Page<Order> search(SearchCondition cond, Pageable pageable) {
    return orderRepository.findByCondition(cond, pageable);
}
```

함정도 있다. `readOnly = true` 안에서 실수로 엔티티 필드를 수정해도 dirty checking이 안 일어나서 INSERT/UPDATE가 안 나간다. "코드는 잘 돌아가는데 DB에 반영이 안 돼요"라는 질문의 원인 중 하나다. 또한 `readOnly = true`는 DB 쪽에 강제력을 갖지 않는다. 마음만 먹으면 INSERT를 할 수 있고, 실제로 INSERT가 발생할 수 있는 메서드(`save()` 호출 등)에서 readOnly를 켜놓으면 예측이 어려워진다.

---

## TransactionTemplate으로 프로그래밍 방식 트랜잭션

`@Transactional`로 안 되는 케이스가 두 가지 있다.

첫째, 트랜잭션 경계를 메서드보다 더 작게 잡고 싶을 때다. 메서드의 일부 구간만 트랜잭션으로 감싸고 싶거나, 한 메서드 안에서 여러 개의 작은 트랜잭션을 돌려야 할 때 사용한다.

둘째, 트랜잭션 시작/종료 시점을 코드로 직접 제어해야 할 때다. 예를 들어 외부 API 호출 결과에 따라 트랜잭션 옵션을 동적으로 바꿔야 한다면 어노테이션으로는 표현이 안 된다.

```java
@Service
@RequiredArgsConstructor
public class BatchService {

    private final TransactionTemplate transactionTemplate;
    private final ItemRepository itemRepository;

    public void process(List<Item> items) {
        for (List<Item> chunk : Lists.partition(items, 1000)) {
            transactionTemplate.execute(status -> {
                try {
                    chunk.forEach(itemRepository::save);
                    return null;
                } catch (Exception e) {
                    status.setRollbackOnly();
                    throw e;
                }
            });
        }
    }
}
```

배치 처리에서 청크 단위로 커밋하는 패턴이 대표적이다. 메서드 전체를 한 트랜잭션으로 묶으면 메모리에 1차 캐시가 쌓여서 OOM이 나는데, 청크마다 커밋하면 1차 캐시가 비워진다. Spring Batch가 내부적으로 하는 일이 이거다.

`TransactionTemplate`은 빈으로 등록해서 주입받는다. 옵션을 바꾸려면 별도의 인스턴스를 만들거나 `setPropagationBehavior()` 같은 setter로 바꿔야 한다. setter는 thread-safe하지 않으므로 옵션이 다른 트랜잭션이 필요하면 인스턴스를 분리하는 게 안전하다.

```java
@Bean("readOnlyTxTemplate")
public TransactionTemplate readOnlyTxTemplate(PlatformTransactionManager tm) {
    TransactionTemplate template = new TransactionTemplate(tm);
    template.setReadOnly(true);
    template.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
    return template;
}
```

---

## 중첩 트랜잭션과 SAVEPOINT 동작

`PROPAGATION_NESTED`의 동작을 좀 더 자세히 본다. 외부 트랜잭션이 시작된 상태에서 NESTED로 진입하면 Spring은 JDBC 커넥션의 `setSavepoint()`를 호출해서 SAVEPOINT를 만든다. 내부에서 예외가 발생하면 `rollback(savepoint)`로 SAVEPOINT까지만 롤백한다. 외부 트랜잭션은 그대로 유지된다.

```sql
-- 실제 DB에서 일어나는 일
BEGIN;                          -- 외부 트랜잭션 시작
INSERT INTO orders ...;
SAVEPOINT sp1;                  -- NESTED 진입
INSERT INTO order_items ...;    -- 실패
ROLLBACK TO SAVEPOINT sp1;      -- 여기까지만 롤백
INSERT INTO error_logs ...;     -- 외부 트랜잭션은 살아있음
COMMIT;                         -- orders, error_logs는 커밋됨
```

제약이 몇 가지 있다.

JTA 트랜잭션 매니저는 SAVEPOINT를 지원하지 않는다. JTA는 분산 트랜잭션 매니저라 단일 커넥션 단위의 SAVEPOINT 개념이 없다.

JPA를 사용하는 경우에도 `JpaTransactionManager`가 SAVEPOINT를 지원하지만, Hibernate의 영속성 컨텍스트는 SAVEPOINT 롤백 시점에 자동으로 클리어되지 않는다. 즉 DB는 롤백되었지만 영속성 컨텍스트에는 롤백 전 엔티티가 그대로 남아있어 다음 flush 때 문제가 생길 수 있다. 이래서 NESTED는 JPA보다 순수 JDBC나 MyBatis 환경에서 더 안전하다.

외부 트랜잭션이 롤백되면 SAVEPOINT가 살아있어 봤자 의미가 없다. NESTED는 외부가 커밋된다는 가정 하에 일부만 부분 롤백할 때 쓴다. 외부와 독립적으로 커밋이 보장되어야 한다면 `REQUIRES_NEW`를 써야 한다.

---

## 트랜잭션 디버깅 도구

문제 진단이 어려울 때 쓰는 도구들이다.

**TransactionSynchronizationManager**: 현재 스레드에 트랜잭션이 활성화되어 있는지, read-only인지 등을 확인한다. 의심되는 메서드 진입부에 한 줄 찍어보면 트랜잭션이 걸려있는지 즉시 알 수 있다.

```java
log.info("tx active: {}, name: {}, readOnly: {}",
    TransactionSynchronizationManager.isActualTransactionActive(),
    TransactionSynchronizationManager.getCurrentTransactionName(),
    TransactionSynchronizationManager.isCurrentTransactionReadOnly());
```

**Hibernate SQL 로그**: `org.hibernate.SQL=DEBUG`로 쿼리 발생을 확인하고, `org.hibernate.engine.transaction=DEBUG`로 트랜잭션 begin/commit 시점을 본다. `org.springframework.transaction.interceptor=TRACE`까지 켜면 어떤 메서드가 어떤 옵션으로 트랜잭션을 시작하는지 모두 보인다.

**P6Spy 또는 datasource-proxy**: 실제 DB로 나가는 SQL과 커밋/롤백 시점을 로깅한다. JPA 캐시 때문에 코드 흐름과 실제 DB 호출 시점이 다른 경우가 많은데, 이런 도구로 보면 명확해진다.

```yaml
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE
    org.springframework.transaction.interceptor: TRACE
```

---

## 마지막으로

트랜잭션 문제는 거의 항상 다음 중 하나로 귀결된다. 프록시를 거치지 않는 호출이 있거나, 전파 옵션을 잘못 골랐거나, 예외 타입을 잘못 던졌거나. 의심스러우면 일단 트랜잭션이 실제로 시작되는지부터 확인한다. 코드만 읽고 추측하지 말고 로그를 켜서 begin/commit이 찍히는지 본다. 이 한 가지 습관만으로 디버깅 시간이 절반으로 준다.
