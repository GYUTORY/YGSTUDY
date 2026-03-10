---
title: Spring AOP & 트랜잭션 심화
tags: [framework, java, spring, aop, transaction, aspect, transactional, propagation]
updated: 2026-03-08
---

# Spring AOP & 트랜잭션 심화

## AOP 개요

AOP(Aspect-Oriented Programming)는 **핵심 비즈니스 로직과 횡단 관심사(cross-cutting concern)를 분리**하는 프로그래밍 패러다임이다. 로깅, 트랜잭션, 보안, 캐싱 등 여러 곳에 반복되는 코드를 한 곳에서 관리한다.

```
횡단 관심사 예시:
  - 모든 서비스 메서드 실행 전후 로깅
  - 모든 DB 작업에 트랜잭션 적용
  - 특정 패키지 접근 시 권한 체크
  - 메서드 실행 시간 측정
```

---

## AOP 핵심 용어

| 용어 | 설명 | 예시 |
|------|------|------|
| **Aspect** | 횡단 관심사 모듈 | `LoggingAspect`, `TransactionAspect` |
| **Advice** | 실제 부가 기능 코드 | `@Before`, `@After`, `@Around` |
| **Pointcut** | Advice를 적용할 메서드 기준 | `execution(* com.example.service.*.*(..))` |
| **JoinPoint** | Advice가 적용될 수 있는 지점 | 메서드 실행, 예외 발생 |
| **Weaving** | Aspect를 대상 코드에 적용 | Spring은 런타임 프록시 방식 사용 |

---

## Pointcut 표현식

```java
// execution(접근제어자? 반환타입 패키지..클래스.메서드(파라미터))

// service 패키지의 모든 메서드
execution(* com.example.service.*.*(..))

// UserService의 모든 public 메서드
execution(public * com.example.service.UserService.*(..))

// 이름이 get으로 시작하는 모든 메서드
execution(* get*(..))

// Long 타입 파라미터 하나를 받는 메서드
execution(* com.example.*.*(Long))

// @Transactional 어노테이션이 붙은 메서드
@annotation(org.springframework.transaction.annotation.Transactional)

// 특정 어노테이션이 붙은 클래스의 모든 메서드
@within(com.example.annotation.LogExecution)
```

---

## Advice 종류

```java
@Aspect
@Component
public class LoggingAspect {

    // 메서드 실행 전
    @Before("execution(* com.example.service.*.*(..))")
    public void logBefore(JoinPoint joinPoint) {
        log.info("호출: {}.{}",
            joinPoint.getTarget().getClass().getSimpleName(),
            joinPoint.getSignature().getName());
    }

    // 메서드 정상 반환 후
    @AfterReturning(
        pointcut = "execution(* com.example.service.*.*(..))",
        returning = "result"
    )
    public void logAfterReturning(JoinPoint joinPoint, Object result) {
        log.info("반환: {} → {}", joinPoint.getSignature().getName(), result);
    }

    // 예외 발생 후
    @AfterThrowing(
        pointcut = "execution(* com.example.service.*.*(..))",
        throwing = "ex"
    )
    public void logAfterThrowing(JoinPoint joinPoint, Exception ex) {
        log.error("예외: {} → {}", joinPoint.getSignature().getName(), ex.getMessage());
    }

    // 메서드 실행 전후 모두 (가장 강력)
    @Around("execution(* com.example.service.*.*(..))")
    public Object measureExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            Object result = joinPoint.proceed(); // 실제 메서드 실행
            long duration = System.currentTimeMillis() - start;
            log.info("{} 실행 시간: {}ms", joinPoint.getSignature().getName(), duration);
            return result;
        } catch (Exception e) {
            log.error("예외 발생: {}", e.getMessage());
            throw e;
        }
    }
}
```

---

## 실무 활용 예시

### 커스텀 어노테이션 + AOP

```java
// 1. 어노테이션 정의
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface AuditLog {
    String action() default "";
}

// 2. Aspect 구현
@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditRepository auditRepository;

    @Around("@annotation(auditLog)")
    public Object audit(ProceedingJoinPoint joinPoint, AuditLog auditLog) throws Throwable {
        Object result = joinPoint.proceed();

        auditRepository.save(AuditLog.builder()
            .action(auditLog.action())
            .method(joinPoint.getSignature().toShortString())
            .timestamp(LocalDateTime.now())
            .build());

        return result;
    }
}

// 3. 사용
@Service
public class OrderService {
    @AuditLog(action = "ORDER_CREATE")
    public Order createOrder(OrderRequest request) { ... }
}
```

---

## @Transactional 심화

### 전파 레벨 (Propagation)

```java
// REQUIRED (기본값): 트랜잭션이 있으면 참여, 없으면 새로 생성
@Transactional(propagation = Propagation.REQUIRED)
public void methodA() {
    methodB(); // methodA 트랜잭션에 참여
}

// REQUIRES_NEW: 항상 새 트랜잭션 생성 (기존 트랜잭션 일시 중단)
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void sendNotification() {
    // 주문 실패해도 알림은 독립적으로 처리
}

// NESTED: 중첩 트랜잭션 (savepoint 활용)
@Transactional(propagation = Propagation.NESTED)
public void nestedMethod() {
    // 실패 시 이 메서드만 롤백, 외부 트랜잭션은 유지
}

// SUPPORTS: 트랜잭션 있으면 참여, 없으면 없이 실행
// NOT_SUPPORTED: 트랜잭션 없이 실행 (기존 트랜잭션 중단)
// NEVER: 트랜잭션이 있으면 예외 발생
// MANDATORY: 트랜잭션이 없으면 예외 발생
```

| 전파 레벨 | 기존 트랜잭션 있을 때 | 없을 때 |
|---------|-----------------|--------|
| REQUIRED | 참여 | 새로 생성 |
| REQUIRES_NEW | 중단 후 새로 생성 | 새로 생성 |
| SUPPORTS | 참여 | 없이 실행 |
| MANDATORY | 참여 | 예외 |
| NESTED | 중첩(savepoint) | 새로 생성 |
| NEVER | 예외 | 없이 실행 |
| NOT_SUPPORTED | 중단 후 없이 실행 | 없이 실행 |

### 격리 레벨 (Isolation)

```java
@Transactional(isolation = Isolation.READ_COMMITTED) // 대부분의 DB 기본값
@Transactional(isolation = Isolation.REPEATABLE_READ) // MySQL InnoDB 기본값
@Transactional(isolation = Isolation.SERIALIZABLE)    // 가장 강한 격리
```

### readOnly 옵션

```java
// 읽기 전용 — JPA flush 모드를 NEVER로 설정 → 더티체킹 비용 절약
@Transactional(readOnly = true)
public List<User> findAll() {
    return userRepository.findAll();
}

// 쓰기 메서드는 readOnly = false (기본값)
@Transactional
public User save(User user) {
    return userRepository.save(user);
}
```

### 롤백 기준

```java
// 기본: RuntimeException, Error 발생 시 롤백 (Checked Exception은 커밋)
@Transactional

// 특정 예외에도 롤백
@Transactional(rollbackFor = {IOException.class, CustomException.class})

// 특정 예외는 롤백 안 함
@Transactional(noRollbackFor = BusinessException.class)
```

---

## Self-invocation 문제

Spring AOP는 프록시 기반이므로 **같은 클래스 내에서 메서드를 직접 호출하면 AOP가 적용되지 않는다.**

```java
@Service
public class OrderService {

    // ❌ 문제: 내부 호출은 프록시를 거치지 않아 @Transactional 미적용
    public void createOrder(OrderRequest request) {
        this.saveOrder(request); // AOP 무시됨!
    }

    @Transactional
    public void saveOrder(OrderRequest request) {
        orderRepository.save(...);
    }
}
```

```java
// ✅ 해결책 1: 클래스 분리
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderSaver orderSaver;

    public void createOrder(OrderRequest request) {
        orderSaver.saveOrder(request); // 프록시 거침
    }
}

@Service
public class OrderSaver {
    @Transactional
    public void saveOrder(OrderRequest request) { ... }
}

// ✅ 해결책 2: ApplicationContext에서 자기 자신 주입 (비추)
@Service
public class OrderService {
    @Autowired
    private OrderService self; // 자기 자신의 프록시 주입

    public void createOrder(OrderRequest request) {
        self.saveOrder(request);
    }

    @Transactional
    public void saveOrder(OrderRequest request) { ... }
}
```

---

## 선언적 vs 프로그래밍 트랜잭션

```java
// 선언적 트랜잭션 (@Transactional) — 대부분의 경우 권장
@Transactional
public void transfer(Long fromId, Long toId, BigDecimal amount) {
    accountRepository.debit(fromId, amount);
    accountRepository.credit(toId, amount);
}

// 프로그래밍 트랜잭션 — 세밀한 제어가 필요할 때
@RequiredArgsConstructor
public class TransferService {
    private final TransactionTemplate transactionTemplate;

    public void transfer(Long fromId, Long toId, BigDecimal amount) {
        transactionTemplate.execute(status -> {
            try {
                accountRepository.debit(fromId, amount);
                accountRepository.credit(toId, amount);
                return null;
            } catch (Exception e) {
                status.setRollbackOnly(); // 수동 롤백
                throw e;
            }
        });
    }
}
```

---

## 체크리스트

- [ ] Pointcut 표현식은 너무 넓지 않게 — 불필요한 메서드까지 AOP 적용되지 않도록
- [ ] `@Around`에서 `joinPoint.proceed()` 반드시 호출 (누락 시 원본 메서드 실행 안 됨)
- [ ] Self-invocation 발생 여부 항상 확인
- [ ] `readOnly = true`를 조회 메서드에 적극 활용 (성능 이점)
- [ ] Checked Exception 롤백이 필요하면 `rollbackFor` 명시
- [ ] `REQUIRES_NEW`는 새 커넥션을 생성하므로 커넥션 풀 여유분 확인
