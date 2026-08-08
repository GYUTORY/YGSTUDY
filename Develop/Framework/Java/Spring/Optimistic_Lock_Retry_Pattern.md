---
title: 낙관적 락 충돌 후 재시도 처리
tags: [spring, java, redis]
updated: 2026-08-03
---

# 낙관적 락 충돌 후 재시도 처리

낙관적 락은 충돌을 막지 않는다. 충돌을 감지한다. 그래서 재시도 로직이 반드시 따라와야 하는데, 재시도를 잘못 구현하면 충돌이 나도 효과가 없거나, 트래픽이 몰릴 때 재시도 자체가 서비스를 죽이는 상황이 된다.

## @Version 기반 낙관적 락 동작 방식

```java
@Entity
public class Product {
    @Id
    private Long id;

    private int stock;

    @Version
    private Long version;
}
```

JPA가 UPDATE 쿼리를 날릴 때 WHERE 절에 version 컬럼을 포함시킨다.

```sql
UPDATE product SET stock = 9, version = 2 WHERE id = 1 AND version = 1
```

동시에 두 트랜잭션이 version=1 상태로 읽어서 각자 업데이트를 시도하면, 먼저 커밋한 쪽이 version을 2로 바꾼다. 나중에 들어온 쪽은 WHERE version=1 조건이 맞지 않아 영향받은 행이 0이 되고, JPA가 `OptimisticLockException`을 던진다.

---

## @Retryable + @Transactional 조합의 함정

Spring Retry의 `@Retryable`과 `@Transactional`을 같은 메서드에 붙이면 직관적으로 "예외 발생 시 트랜잭션을 처음부터 다시 시작하겠지"라고 생각하기 쉽다. 실제로는 그렇지 않다.

```java
// 이렇게 쓰면 안 된다
@Retryable(retryFor = OptimisticLockException.class, maxAttempts = 3)
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findById(productId).orElseThrow();
    product.decreaseStock(quantity);
}
```

`@Retryable`은 메서드 레벨에서 예외를 잡아 재호출한다. `@Transactional`은 프록시가 트랜잭션을 열고 메서드 본문을 실행한다.

문제는 AOP 프록시 적용 순서다. 바깥쪽 프록시가 먼저 감싸는데, 일반적으로 `@Transactional`이 `@Retryable`보다 안쪽에 위치한다. `OptimisticLockException`이 발생하면 이미 트랜잭션에 롤백 마크(`rollback-only`)가 찍힌 상태고, `@Retryable`이 메서드를 다시 호출해도 새 트랜잭션이 열리지 않는다. 기존에 롤백 마크가 찍힌 트랜잭션 안에서 재시도가 일어나거나 `TransactionSystemException`이 연달아 터진다.

`@Order`를 명시적으로 지정해서 `@Retryable`이 트랜잭션보다 바깥쪽에 오도록 강제하면 해결되긴 한다. 하지만 이 설정은 나중에 다른 개발자가 순서를 건드리면 조용히 깨진다. 재시도 범위와 트랜잭션 범위는 코드 구조 자체로 분리하는 편이 안전하다.

---

## 재시도 폭풍 (Retry Storm)

수동 재시도 루프를 쓰더라도, 트래픽이 몰리는 상황에서는 재시도 자체가 문제가 된다.

재고 차감 요청이 100건 동시에 들어왔다고 하면, 100개 스레드가 모두 version=5 상태로 읽는다. 스레드 1이 먼저 커밋해서 version을 6으로 바꾼다. 나머지 99개 스레드는 전부 `OptimisticLockException`을 받는다. 이 99개가 거의 동시에 재시도에 들어간다. 다시 스레드 하나가 성공하고 98개가 실패해서 재시도한다. 충돌 → 재시도 → 충돌 → 재시도가 계단식으로 반복된다.

각 재시도는 SELECT + UPDATE 쿼리를 DB에 날린다. `maxAttempts=3`으로 설정했다면 이론상 최악의 경우 100 × 3 = 300번의 DB 접근이 발생한다. 커넥션 풀이 30개라면 스레드들이 커넥션을 대기하면서 응답 시간이 폭발적으로 늘어난다.

프로덕션에서 이 상황이 처음 발생하면 서비스가 느려지거나 타임아웃이 터지는 것처럼 보인다. 로그를 보면 같은 `productId`에 대한 `OptimisticLockException`이 초당 수십 건씩 찍혀 있다.

해결 방향은 두 가지다. 재시도 간격에 랜덤 지연(jitter)을 넣어서 충돌 타이밍을 분산시키거나, 충돌 빈도 자체가 높은 리소스는 낙관적 락 대신 벌크 UPDATE나 Redis 분산 락으로 전환하는 것이다.

---

## 수동 재시도 루프 구현

재시도 범위와 트랜잭션 범위를 별도 클래스로 분리하는 게 명확하다.

```java
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockTransactionalService stockTransactionalService;

    public void decreaseStockWithRetry(Long productId, int quantity) {
        int maxAttempts = 3;

        for (int attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                stockTransactionalService.decreaseStock(productId, quantity);
                return;
            } catch (OptimisticLockException | ObjectOptimisticLockingFailureException e) {
                if (attempt == maxAttempts - 1) {
                    throw new StockUpdateFailedException("재고 업데이트 실패: " + maxAttempts + "회 충돌", e);
                }
                applyBackoff(attempt);
            }
        }
    }

    private void applyBackoff(int attempt) {
        try {
            Thread.sleep(exponentialBackoffWithJitter(attempt));
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw new StockUpdateFailedException("재시도 중단", ie);
        }
    }
}

@Service
@RequiredArgsConstructor
public class StockTransactionalService {

    private final ProductRepository productRepository;

    @Transactional
    public void decreaseStock(Long productId, int quantity) {
        Product product = productRepository.findById(productId).orElseThrow();
        product.decreaseStock(quantity);
    }
}
```

매 재시도마다 새 트랜잭션이 열리고, 최신 version 값을 다시 읽어온다. `ObjectOptimisticLockingFailureException`도 같이 처리해야 한다. Spring Data JPA는 JPA의 `OptimisticLockException`을 이 클래스로 변환해서 던지는 경우가 있다.

---

## Exponential Backoff 구현

고정 대기 시간(fixed delay)은 충돌이 분산되지 않는다. 50ms 뒤에 재시도하는 스레드 99개가 여전히 같은 시점에 몰린다. Exponential Backoff에 Jitter를 더해야 충돌 타이밍이 퍼진다.

```java
private long exponentialBackoffWithJitter(int attempt) {
    long baseDelay = 100L;
    long maxDelay = 1000L;

    // attempt=0 → 100ms, attempt=1 → 200ms, attempt=2 → 400ms 상한
    long exponential = Math.min(baseDelay * (1L << attempt), maxDelay);

    // Full Jitter: [0, exponential) 범위 무작위
    return ThreadLocalRandom.current().nextLong(exponential);
}
```

Full Jitter 방식이다. `[0, cap)` 범위 전체를 무작위로 쓰면 Equal Jitter보다 충돌 분산 효과가 크다. attempt=0일 때 0~100ms, attempt=1일 때 0~200ms, attempt=2일 때 0~400ms 범위에서 각 스레드가 서로 다른 시점에 재시도한다.

더 분산이 필요하면 Decorrelated Jitter를 쓴다. 이전 대기 시간을 기준으로 다음 대기 시간을 결정해서 스레드 간 패턴이 겹치지 않는다.

```java
private long decorrelatedJitter(long prevDelay) {
    long minDelay = 100L;
    long maxDelay = 1000L;
    // prevDelay의 3배를 상한으로 무작위 선택
    long next = ThreadLocalRandom.current().nextLong(minDelay, prevDelay * 3);
    return Math.min(next, maxDelay);
}
```

실무에서는 Full Jitter로 충분한 경우가 대부분이다. Decorrelated Jitter는 재시도 간격이 매우 촘촘한 상황(초당 수백 건 이상)에서만 차이가 눈에 띈다.

재시도 횟수 결정 기준은 비즈니스 SLA에 따른다. 사용자 요청을 직접 처리하는 API라면 3회 초과는 응답 시간이 허용 범위를 넘기기 쉽다. 백그라운드 작업이라면 5회까지도 무방하다. 충돌이 잦은 케이스에서 재시도 횟수를 늘리는 건 문제 해결이 아니라 증상 가리기다.

---

## 유니크 제약 충돌 처리

낙관적 락 재시도 루프를 구현할 때, `DataIntegrityViolationException`을 `ObjectOptimisticLockingFailureException`과 같은 catch 블록에 묶으면 재시도로 해소되지 않는 케이스까지 재시도하게 된다.

두 예외는 발생 원인이 다르다. `ObjectOptimisticLockingFailureException`은 타이밍 문제다. 두 트랜잭션이 같은 행을 동시에 읽어서 나중에 커밋한 쪽이 version 불일치로 받는다. 재시도하면 최신 version을 다시 읽어 성공할 수 있다. `DataIntegrityViolationException`은 데이터 제약 위반이다. UNIQUE, NOT NULL, FK 위반이 여기 해당한다. 재시도해도 같은 예외가 반복된다.

```java
public void registerWithRetry(UserRegisterCommand command) {
    int maxAttempts = 3;

    for (int attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            userTransactionalService.register(command);
            return;
        } catch (DataIntegrityViolationException e) {
            // 제약 위반은 재시도로 해소되지 않는다
            handleConstraintViolation(e);
        } catch (ObjectOptimisticLockingFailureException e) {
            if (attempt == maxAttempts - 1) {
                throw new RegistrationFailedException("등록 실패", e);
            }
            applyBackoff(attempt);
        }
    }
}
```

### 제약 이름으로 충돌 컬럼 특정

`DataIntegrityViolationException`의 원인 예외 체인을 따라가면 `org.hibernate.exception.ConstraintViolationException`이 나온다. `jakarta.validation.ConstraintViolationException`이 아니다. 둘을 혼동해서 잘못된 타입으로 캐스팅하면 분기 자체가 동작하지 않는다.

`ConstraintViolationException.getConstraintName()`으로 어떤 제약이 위반됐는지 알 수 있다.

```java
private void handleConstraintViolation(DataIntegrityViolationException e) {
    Throwable cause = e.getCause();
    if (!(cause instanceof org.hibernate.exception.ConstraintViolationException cve)) {
        throw new DataConflictException("데이터 제약 위반", e);
    }

    String constraintName = cve.getConstraintName();
    if (constraintName == null) {
        // 일부 JDBC 드라이버는 제약 이름을 null로 반환한다
        throw new DataConflictException("제약 이름 불명", e);
    }

    // DB에 따라 대소문자가 다를 수 있어 소문자로 정규화
    String normalized = constraintName.toLowerCase();

    if (normalized.equals("uk_user_email")) {
        throw new DuplicateEmailException();
    }
    if (normalized.equals("uk_user_phone")) {
        throw new DuplicatePhoneException();
    }

    throw new DataConflictException("알 수 없는 제약 위반: " + constraintName, e);
}
```

제약 이름을 직접 지정하지 않으면 DB마다 자동 생성 규칙이 달라서 문제가 된다. PostgreSQL은 `tablename_columnname_key`, MySQL은 컬럼명을 그대로 제약 이름으로 쓰는 경우가 많다. 테스트 환경에서 H2를 쓰고 프로덕션에서 PostgreSQL을 쓰는 환경이라면, 같은 코드에서 제약 이름이 달라져 분기가 동작하지 않는다.

엔티티에 `@UniqueConstraint`의 `name`을 명시하면 이 문제를 피할 수 있다.

```java
@Entity
@Table(
    name = "users",
    uniqueConstraints = {
        @UniqueConstraint(name = "uk_user_email", columnNames = "email"),
        @UniqueConstraint(name = "uk_user_phone", columnNames = "phone")
    }
)
public class User {
    @Id
    private Long id;

    private String email;
    private String phone;
}
```

`name`을 지정하면 H2, MySQL, PostgreSQL 모두 동일한 이름으로 제약이 생성된다. Flyway나 Liquibase를 쓴다면 `CONSTRAINT uk_user_email UNIQUE (email)` 형태로 명시해도 같다.

### 재시도 대상 여부 판단 기준

`ObjectOptimisticLockingFailureException`은 재시도 대상이다. 최신 데이터를 다시 읽으면 충돌이 해소될 수 있다.

`DataIntegrityViolationException` 중 UNIQUE 위반은 재시도 대상이 아니다. 같은 값이 이미 DB에 존재한다. 재시도를 소진하기 전에 상위 레이어에서 사전 검사하거나 클라이언트에 409를 돌려줘야 한다.

NOT NULL, FK 위반도 재시도 대상이 아니다. 요청 데이터나 애플리케이션 코드에 문제가 있는 것이라 재시도로 해결되지 않는다.

`DeadlockLoserDataAccessException`은 재시도 대상이다. DB 데드락 감지로 롤백된 것이라 동일 작업을 재시도하면 성공하는 경우가 많다. `DataAccessException` 하위 클래스지만 `DataIntegrityViolationException`과는 다른 계층이라 별도로 catch해야 한다.

```java
} catch (DataIntegrityViolationException e) {
    // 재시도 없음. 제약 위반은 데이터 문제다
    handleConstraintViolation(e);
} catch (DeadlockLoserDataAccessException | ObjectOptimisticLockingFailureException e) {
    // 재시도 가능. 타이밍 문제다
    if (attempt == maxAttempts - 1) {
        throw new ProcessFailedException("처리 실패", e);
    }
    applyBackoff(attempt);
}
```

---

## JPA 벌크 UPDATE 전환 판단 기준

재시도 폭풍이 발생하는 케이스 중 상당수는 낙관적 락 자체가 과도한 선택인 경우다. 재고를 `quantity = quantity - amount` 형태로 줄이는 것처럼 단순 수치 연산이라면, DB의 원자 연산으로 충분하다.

```java
@Repository
public interface StockRepository extends JpaRepository<Stock, Long> {

    @Modifying(clearAutomatically = true)
    @Query("UPDATE Stock s SET s.quantity = s.quantity - :amount " +
           "WHERE s.id = :id AND s.quantity >= :amount")
    int decreaseStock(@Param("id") Long id, @Param("amount") int amount);
}

@Service
@RequiredArgsConstructor
public class StockService {

    private final StockRepository stockRepository;

    @Transactional
    public void decreaseStock(Long stockId, int amount) {
        int updated = stockRepository.decreaseStock(stockId, amount);
        if (updated == 0) {
            throw new InsufficientStockException("재고 부족 또는 동시 충돌");
        }
    }
}
```

`quantity = quantity - amount`는 DB가 원자적으로 실행한다. `WHERE quantity >= amount` 조건이 동시성 제어 역할을 한다. 먼저 실행된 쿼리가 재고를 줄이면, 나중에 들어온 쿼리는 재고 부족으로 0 rows updated가 된다. version 컬럼도, 재시도 로직도 필요 없다.

**벌크 UPDATE가 맞는 경우**

수치 증감만 하는 단순 케이스다. 재고 차감, 포인트 적립/차감, 카운터 증가가 여기 해당한다. JPA 생명주기 이벤트(`@PreUpdate`, `@PostUpdate`)가 필요 없고, Hibernate Envers로 변경 이력을 추적하지 않는 경우다.

**벌크 UPDATE를 쓰면 안 되는 경우**

엔티티 상태에 따른 비즈니스 로직이 들어가야 하는 경우다. 재고가 0으로 떨어지면 상태를 `SOLD_OUT`으로 바꿔야 한다든지, 변경 시점에 도메인 이벤트를 발행해야 하는 경우가 여기 해당한다. 벌크 UPDATE는 영속성 컨텍스트를 거치지 않아서 `@PreUpdate`가 동작하지 않는다. 감사 로그를 JPA 이벤트 리스너로 남기고 있다면 벌크 UPDATE는 그 이력을 빠뜨린다.

`clearAutomatically = true`는 벌크 UPDATE 후 1차 캐시를 초기화한다. 같은 트랜잭션에서 엔티티를 조회했다가 벌크 UPDATE를 하면, 이 옵션 없이는 1차 캐시에 업데이트 전 값이 남아 있어서 다시 조회해도 이전 값을 반환한다.

---

## Redis 분산 락 vs 낙관적 락 선택 기준

**낙관적 락이 맞는 경우**

충돌 확률이 낮을 때다. 충돌 빈도가 요청의 10% 미만이라면 대부분 락 없이 성공하고, 드물게 충돌 시에만 재시도 비용을 치른다. 사용자 프로필 수정, 게시글 수정처럼 같은 리소스를 동시에 수정할 일이 드문 케이스가 여기 해당한다. 추가 인프라 없이 DB만으로 해결할 수 있다.

**Redis 분산 락이 맞는 경우**

충돌 빈도가 높은 케이스다. 플래시 세일 재고 차감처럼 수백 개의 요청이 같은 행을 동시에 수정하려 하면, 낙관적 락 재시도가 폭발적으로 증가해서 DB 부하가 오히려 커진다. Redis에서 직렬화하면 DB에는 성공하는 쿼리만 들어간다.

스케줄러 중복 실행 방지처럼 락 선점 자체가 목적인 경우에도 Redis 분산 락이 적합하다. 낙관적 락은 충돌 감지 후 롤백이지, 선점이 아니다.

```java
@Service
@RequiredArgsConstructor
public class StockService {

    private final RedissonClient redissonClient;
    private final StockTransactionalService stockTransactionalService;

    public void decreaseStock(Long productId, int quantity) {
        RLock lock = redissonClient.getLock("stock:" + productId);

        boolean acquired;
        try {
            // waitTime: 락 획득 대기, leaseTime: 락 유지 시간
            acquired = lock.tryLock(3, 5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new LockAcquisitionFailedException("락 획득 중단", e);
        }

        if (!acquired) {
            throw new LockAcquisitionFailedException("락 획득 실패: productId=" + productId);
        }

        try {
            stockTransactionalService.decreaseStock(productId, quantity);
        } finally {
            // leaseTime이 지나서 락이 이미 해제된 경우 예외 방지
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

`leaseTime` 안에 작업이 끝나지 않으면 락이 자동 해제된다. 서버가 다운되더라도 `leaseTime` 이후에는 락이 풀린다. `leaseTime`을 너무 짧게 잡으면 정상 처리 중에 락이 풀리고, 너무 길게 잡으면 서버 장애 시 복구가 느려진다. 실제 작업 시간의 3~5배를 기준으로 잡는다.

`lock.isHeldByCurrentThread()` 확인 없이 `lock.unlock()`을 호출하면, `leaseTime`이 지나서 락이 이미 해제된 상태에서 `IllegalMonitorStateException`이 터진다.

**선택 흐름**

단순 수치 증감이고 JPA 이벤트가 필요 없다 → 벌크 UPDATE.
충돌 확률이 낮고 추가 인프라를 도입하고 싶지 않다 → 낙관적 락.
충돌 확률이 높거나(동일 리소스에 초당 수십 건 이상) 재시도 폭풍이 관측됐다 → Redis 분산 락.

---

## Fallback 설계

재시도를 다 소진한 후 어떻게 처리할지도 중요하다. 예외를 그대로 두면 HTTP 500이 클라이언트에게 내려간다.

사용자 요청 직접 처리인 경우, 409 Conflict나 503으로 클라이언트가 재시도 가능하다는 신호를 준다.

```java
catch (StockUpdateFailedException e) {
    throw new ResponseStatusException(HttpStatus.CONFLICT, "요청이 혼잡합니다. 잠시 후 다시 시도해주세요.");
}
```

비동기 작업, 배치, 메시지 큐 컨슈머인 경우 Dead Letter Queue로 보내거나 재처리 테이블에 기록한다. 즉시 실패보다 나중에 재처리 가능한 형태로 남기는 게 낫다.

멱등성이 중요한 케이스(재고 차감, 결제)는 요청 ID를 함께 받아서 중복 처리가 발생하지 않도록 처리 이력을 남긴다. 재시도 중에 실제로는 첫 번째 시도가 성공했는데 응답만 못 받은 경우, 두 번째 재시도에서 같은 작업이 다시 실행되는 경우가 있다.

---

이 문서는 [트랜잭션과 동시성 허브](../../../_hub/트랜잭션과_동시성.md)의 일부입니다.
