---
title: 낙관적 락 충돌 후 재시도 처리
tags: [Spring, JPA, 낙관적락, 동시성, 트랜잭션, OptimisticLock]
updated: 2026-07-28
---

# 낙관적 락 충돌 후 재시도 처리

낙관적 락은 충돌을 막지 않는다. 충돌이 발생한 후에 감지한다. 그래서 재시도 로직이 반드시 따라와야 하는데, 이 재시도를 잘못 구현하면 충돌이 나도 아무 효과가 없는 코드가 된다.

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

Spring Retry의 `@Retryable`과 `@Transactional`을 함께 쓰면 직관적으로 "예외 발생 시 트랜잭션을 처음부터 다시 시작하겠지"라고 생각하기 쉽다. 실제로는 그렇지 않다.

```java
// 이렇게 쓰면 안 된다
@Retryable(retryFor = OptimisticLockException.class, maxAttempts = 3)
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findById(productId).orElseThrow();
    product.decreaseStock(quantity);
    // OptimisticLockException 발생 시 @Retryable이 재시도
    // 그런데 같은 트랜잭션 컨텍스트 안에서 재시도가 일어난다
}
```

`@Retryable`은 메서드 레벨에서 예외를 잡아 재호출한다. `@Transactional`은 프록시가 트랜잭션을 열고 메서드 본문을 실행한다.

문제는 AOP 프록시 적용 순서다. 바깥쪽 프록시가 먼저 감싸는데, 일반적으로 `@Transactional`이 `@Retryable`보다 안쪽에 위치한다. `OptimisticLockException`이 발생하면 이미 트랜잭션이 롤백 마크(`rollback-only`)가 찍힌 상태고, `@Retryable`이 메서드를 다시 호출해도 새 트랜잭션이 열리지 않는다. 기존에 롤백 마크가 찍힌 트랜잭션 안에서 재시도가 일어나거나 `TransactionSystemException`이 연달아 터진다.

`@Order`를 명시적으로 지정해서 `@Retryable`이 트랜잭션보다 바깥쪽에 오도록 강제하면 해결되긴 하지만, 이 방식은 설정이 복잡하고 나중에 다른 개발자가 순서를 건드리면 조용히 깨진다.

---

## 수동 재시도 루프 구현

재시도 범위와 트랜잭션 범위를 명확히 분리하는 게 낫다.

```java
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockTransactionalService stockTransactionalService;

    public void decreaseStockWithRetry(Long productId, int quantity) {
        int maxAttempts = 3;
        int attempts = 0;

        while (attempts < maxAttempts) {
            try {
                stockTransactionalService.decreaseStock(productId, quantity);
                return;
            } catch (OptimisticLockException | ObjectOptimisticLockingFailureException e) {
                attempts++;
                if (attempts >= maxAttempts) {
                    throw new StockUpdateFailedException("재고 업데이트 실패: " + attempts + "회 충돌", e);
                }
                // 재시도 전 짧은 대기 (선택 사항)
                try {
                    Thread.sleep(50L * attempts);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new StockUpdateFailedException("재시도 중단", ie);
                }
            }
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

재시도 로직은 트랜잭션 바깥에, 실제 작업은 `@Transactional` 메서드 안에 분리한다. 매 재시도마다 새 트랜잭션이 열리고, 새 트랜잭션에서 최신 version 값을 다시 읽어온다.

`ObjectOptimisticLockingFailureException`도 같이 처리해야 한다. Spring Data JPA는 JPA의 `OptimisticLockException`을 이 클래스로 변환해서 던지는 경우가 있다.

---

## 재시도 상한과 대기 시간

재시도 횟수를 너무 크게 잡으면 충돌이 잦은 상황에서 스레드가 오래 묶여 있는다. 너무 작게 잡으면 정상 트래픽에서도 실패가 잦다.

경험상 재고 감소처럼 쓰기 충돌이 잦은 케이스는 3회 정도가 적당하다. 충돌 빈도가 낮은 케이스라면 1~2회도 충분하다.

재시도 사이 대기 시간은 없어도 되지만, 충돌 빈도가 높으면 같은 시점에 몰린 요청들이 계속 서로 방해한다. Jitter(무작위 지연)를 섞으면 충돌이 분산된다.

```java
long baseDelay = 50L;
long jitter = (long) (Math.random() * 50);
Thread.sleep(baseDelay * attempts + jitter);
```

---

## Fallback 설계

재시도를 다 소진한 후 어떻게 처리할지가 중요하다. 단순히 예외를 그대로 던지면 HTTP 500이 클라이언트에게 내려간다.

상황에 따라 선택지가 달라진다:

**사용자 요청 직접 처리인 경우**: 409 Conflict나 503 등 클라이언트가 재시도 가능하다는 신호를 주고 종료한다.

```java
catch (StockUpdateFailedException e) {
    throw new ResponseStatusException(HttpStatus.CONFLICT, "요청이 혼잡합니다. 잠시 후 다시 시도해주세요.");
}
```

**비동기 작업, 배치, 메시지 큐 컨슈머인 경우**: Dead Letter Queue로 보내거나 재처리 테이블에 기록한다. 즉시 실패보다는 나중에 재처리 가능한 형태로 남기는 게 낫다.

**재고 감소처럼 幂等性(멱등성)이 중요한 경우**: 요청 ID를 함께 받아서 같은 요청이 중복 처리되지 않도록 처리 이력을 남긴다.

---

## JPA @Version vs Redis 분산 락 선택

낙관적 락이 적합한 상황과 Redis 분산 락이 적합한 상황은 다르다.

**JPA @Version이 적합한 경우**

단일 서버 혹은 단일 DB 환경에서 충돌 빈도가 낮을 때다. 재고 감소가 초당 수십 건 수준이고, 충돌 시 재시도 비용을 감수할 수 있으면 DB 수준에서 해결하는 게 구조가 단순하다. 별도 인프라가 필요 없고, DB가 version을 관리하므로 일관성 보장이 명확하다.

충돌이 드문 케이스(읽기가 많고 쓰기가 가끔)에서는 락 획득 비용 없이 충돌 시에만 비용을 치른다. 대부분 충돌 없이 지나가면 비관적 락보다 성능이 좋다.

**Redis 분산 락이 필요한 경우**

여러 서버 인스턴스가 동시에 동작하는 환경에서 충돌 빈도가 높다면 Redis 분산 락이 낫다. 플래시 세일처럼 동시 요청이 수백 건 이상 몰리면 낙관적 락 재시도가 폭발적으로 증가한다. 이때는 락을 선점해서 한 번에 하나씩 처리하는 비관적 방식이 DB 부하를 오히려 줄인다.

```java
// Redisson 기반 분산 락 예시
RLock lock = redissonClient.getLock("stock:" + productId);
boolean acquired = lock.tryLock(3, 5, TimeUnit.SECONDS);

if (!acquired) {
    throw new LockAcquisitionFailedException("락 획득 실패");
}

try {
    stockTransactionalService.decreaseStock(productId, quantity);
} finally {
    lock.unlock();
}
```

Redis 분산 락은 락 타임아웃 설정에 신경 써야 한다. 락을 잡은 서버가 다운되면 타임아웃 시간 동안 다른 요청이 대기한다. 너무 짧으면 정상 처리 중에 락이 풀리고, 너무 길면 장애 시 대기 시간이 길다.

멀티 인스턴스 환경이 아니더라도 여러 서비스가 같은 리소스에 접근하는 구조라면 Redis 분산 락이 명시적으로 의도를 드러낸다.

---

## 정리하면

낙관적 락 재시도 구현의 핵심은 재시도 범위와 트랜잭션 범위의 분리다. `@Retryable`과 `@Transactional`을 같은 메서드에 붙이는 방식은 AOP 순서 문제로 의도대로 동작하지 않는 경우가 많다. 재시도 루프는 트랜잭션 바깥에서 돌리고, 실제 DB 작업은 별도 메서드에서 새 트랜잭션으로 처리하는 구조가 명확하다.

재시도 횟수와 fallback은 비즈니스 요구사항에 따라 결정한다. 충돌이 잦아지면 낙관적 락 자체를 재검토하고 Redis 분산 락으로 전환하는 시점을 판단해야 한다.

---
이 문서는 [트랜잭션과 동시성 허브](../../../_hub/트랜잭션과_동시성.md)의 일부입니다.
