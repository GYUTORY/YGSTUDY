---
title: JPA @Lock 어노테이션 종류 비교
tags: [java, spring]
updated: 2026-07-30
---

# JPA @Lock 어노테이션 종류 비교

JPA가 제공하는 락 모드는 5가지다. 이름이 비슷해서 헷갈리기 쉽고, 실제 DB에서 어떤 쿼리가 실행되는지 알아야 제대로 선택할 수 있다.

| 락 모드 | DB Lock | @Version 필요 | 실행 SQL |
|---|---|---|---|
| `PESSIMISTIC_READ` | S Lock | 불필요 | `SELECT ... FOR SHARE` |
| `PESSIMISTIC_WRITE` | X Lock | 불필요 | `SELECT ... FOR UPDATE` |
| `PESSIMISTIC_FORCE_INCREMENT` | X Lock | 필요 | `SELECT ... FOR UPDATE` + version 증가 |
| `OPTIMISTIC` | 없음 | 필요 | `SELECT` + 커밋 시 version 재확인 |
| `OPTIMISTIC_FORCE_INCREMENT` | 없음 | 필요 | `SELECT` + 커밋 시 version 강제 증가 |

---

## PESSIMISTIC_WRITE

실무에서 비관적 락을 쓴다고 하면 대부분 이 모드를 의미한다. `SELECT ... FOR UPDATE`를 실행해서 대상 행에 X Lock을 건다.

```java
public interface AccountRepository extends JpaRepository<Account, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM Account a WHERE a.id = :id")
    Optional<Account> findByIdWithLock(@Param("id") Long id);
}

@Transactional
public void withdraw(Long accountId, Long amount) {
    Account account = accountRepository.findByIdWithLock(accountId)
        .orElseThrow(() -> new EntityNotFoundException("계좌 없음"));

    if (account.getBalance() < amount) {
        throw new IllegalStateException("잔액 부족");
    }
    account.setBalance(account.getBalance() - amount);
}
```

```sql
-- InnoDB에서 실행되는 쿼리
SELECT * FROM account WHERE id = 1 FOR UPDATE;
```

X Lock이 걸린 행은 다른 트랜잭션이 읽거나 쓸 때 대기한다. `FOR UPDATE`는 MVCC를 우회해서 현재 커밋된 최신 데이터를 읽는다. 같은 트랜잭션 안에서 SNAPSHOT으로 읽던 결과와 다를 수 있다.

데드락 위험은 락 획득 순서가 트랜잭션마다 다를 때 생긴다. 트랜잭션 A가 account 1을 잠그고 account 2를 잠그려 할 때, 트랜잭션 B는 account 2를 잠근 채 account 1을 기다리고 있다면 데드락이다. 여러 행을 잠가야 하는 경우 항상 같은 순서(예: id 오름차순)로 잠근다.

락 대기 시간은 `innodb_lock_wait_timeout`(기본 50초)이 지나면 `Lock wait timeout exceeded` 오류가 발생한다. 트랜잭션 범위가 길수록 다른 트랜잭션의 대기가 길어지므로, 락을 잡고 나서 외부 API 호출 같은 I/O 작업이 들어가면 안 된다.

---

## PESSIMISTIC_READ

`SELECT ... FOR SHARE`를 실행한다. S Lock이어서 다른 트랜잭션이 같은 행을 읽는 것은 허용하고, 쓰는 것은 막는다.

```java
@Lock(LockModeType.PESSIMISTIC_READ)
@Query("SELECT a FROM Account a WHERE a.id = :id")
Optional<Account> findByIdForRead(@Param("id") Long id);
```

```sql
SELECT * FROM account WHERE id = 1 FOR SHARE;
```

실무 사용 빈도가 낮다. "읽는 동안 다른 트랜잭션이 쓰지 못하게 막고 싶다"는 요구사항이 생각보다 드물고, `PESSIMISTIC_WRITE`로 충분한 경우가 많다.

데드락 위험이 `PESSIMISTIC_WRITE`보다 오히려 높다. 트랜잭션 A와 B가 둘 다 `FOR SHARE`로 같은 행을 읽으면, 양쪽 모두 S Lock을 가진다. 이후 A가 해당 행을 업데이트하려면 X Lock이 필요한데, B의 S Lock 때문에 대기한다. B도 같은 상황이라면 데드락이 된다. S Lock은 공유 가능한 락이라 데드락이 없을 것처럼 보이지만, S → X 승격 순간 교착 상태가 발생한다.

읽기 후 수정이 필요한 케이스라면 처음부터 `PESSIMISTIC_WRITE`를 쓴다.

---

## PESSIMISTIC_FORCE_INCREMENT

`SELECT ... FOR UPDATE`에 더해 엔티티의 `@Version` 값을 강제로 증가시킨다. `@Version` 컬럼이 없으면 `javax.persistence.PersistenceException`이 발생한다.

```java
@Lock(LockModeType.PESSIMISTIC_FORCE_INCREMENT)
@Query("SELECT a FROM Account a WHERE a.id = :id")
Optional<Account> findByIdWithForceIncrement(@Param("id") Long id);
```

```sql
-- SELECT
SELECT * FROM account WHERE id = 1 FOR UPDATE;

-- 커밋 시 (엔티티를 수정하지 않아도 실행됨)
UPDATE account SET version = 2 WHERE id = 1 AND version = 1;
```

엔티티를 실제로 수정하지 않아도 version이 증가한다. "이 엔티티를 읽었다"는 사실 자체를 낙관적 락 체계에 반영해야 하는 경우에 쓴다. 부모 엔티티를 직접 수정하지 않지만, 자식 엔티티 변경이 부모의 버전 체계에 포함되어야 하는 집계 일관성 시나리오가 해당된다.

실무 사용 빈도는 낮다. 이 모드가 필요하다고 느끼는 경우 대부분은 도메인 설계 자체를 먼저 검토하는 편이 낫다.

---

## OPTIMISTIC

DB 락을 걸지 않는다. 커밋 시점에 version 컬럼이 SELECT 시점과 같은지 확인한다.

```java
@Entity
public class Product {
    @Id
    private Long id;
    private int stock;

    @Version
    private Long version;
}

// Repository
@Lock(LockModeType.OPTIMISTIC)
@Query("SELECT p FROM Product p WHERE p.id = :id")
Optional<Product> findByIdOptimistic(@Param("id") Long id);
```

```sql
-- SELECT 시점 (DB Lock 없음)
SELECT id, stock, version FROM product WHERE id = 1;

-- 커밋 시점 (version 재확인)
SELECT version FROM product WHERE id = 1;
-- version이 다르면 OptimisticLockException 발생
-- 같으면 UPDATE 진행
UPDATE product SET stock = 9, version = 2 WHERE id = 1 AND version = 1;
```

`@Version`이 있는 엔티티는 별도로 `@Lock(LockModeType.OPTIMISTIC)`을 선언하지 않아도 JPA가 UPDATE 시 version 체크를 수행한다. 이 모드를 명시적으로 선언하면 UPDATE가 없는 읽기 전용 작업에서도 version을 재확인한다. "이 엔티티를 읽는 동안 다른 트랜잭션이 수정했으면 예외를 던져라"라는 의미다.

SELECT 후 아무것도 수정하지 않는 트랜잭션이라도 다른 트랜잭션이 중간에 해당 엔티티를 변경했다면 `OptimisticLockException`이 발생한다. 읽기 일관성을 낙관적 락 체계로 보장하고 싶을 때 쓴다.

---

## OPTIMISTIC_FORCE_INCREMENT

DB 락 없이 커밋 시점에 version을 강제로 증가시킨다. 엔티티를 수정하지 않아도 version이 올라간다.

```java
@Lock(LockModeType.OPTIMISTIC_FORCE_INCREMENT)
@Query("SELECT o FROM Order o WHERE o.id = :id")
Optional<Order> findByIdOptimisticForce(@Param("id") Long id);
```

```sql
-- SELECT (DB Lock 없음)
SELECT id, total_amount, version FROM orders WHERE id = 1;

-- 커밋 시점 (수정 없어도 version 증가)
UPDATE orders SET version = 2 WHERE id = 1 AND version = 1;
-- version 불일치면 OptimisticLockException
```

부모 엔티티의 낙관적 락 체계 안에 자식 엔티티 변경을 포함시켜야 할 때 쓴다. 자식 엔티티를 변경하면서 부모 엔티티에 이 모드를 걸면, 누군가 같은 부모나 그 자식을 동시에 수정했을 때 충돌이 감지된다.

```java
@Transactional
public void addOrderItem(Long orderId, OrderItem item) {
    // 자식(OrderItem)을 추가하면서 부모(Order)의 version을 올린다
    Order order = orderRepository.findByIdOptimisticForce(orderId)
        .orElseThrow();
    order.addItem(item);
    // 커밋 시 Order의 version이 올라가므로,
    // 같은 Order를 동시에 수정한 다른 트랜잭션과 충돌이 감지된다
}
```

---

## @Version과의 조합 요약

| 락 모드 | @Version 없을 때 | @Version 있을 때 |
|---|---|---|
| `PESSIMISTIC_READ` | 정상 동작 | version 체크 없이 S Lock만 사용 |
| `PESSIMISTIC_WRITE` | 정상 동작 | version 체크 없이 X Lock만 사용 |
| `PESSIMISTIC_FORCE_INCREMENT` | PersistenceException | X Lock + version 강제 증가 |
| `OPTIMISTIC` | PersistenceException | DB Lock 없이 커밋 시 version 재확인 |
| `OPTIMISTIC_FORCE_INCREMENT` | PersistenceException | DB Lock 없이 커밋 시 version 강제 증가 |

비관적 락(`PESSIMISTIC_READ`, `PESSIMISTIC_WRITE`)은 `@Version` 없이도 동작한다. DB 레벨 락으로 동시성을 제어하기 때문이다. 낙관적 락과 `FORCE_INCREMENT` 계열 모드는 `@Version`이 없으면 예외가 발생한다.

---

## 데드락 위험도 비교

| 락 모드 | 데드락 위험 | 주요 원인 |
|---|---|---|
| `PESSIMISTIC_WRITE` | 높음 | 여러 행을 다른 순서로 잠글 때 |
| `PESSIMISTIC_READ` | 매우 높음 | S → X 락 승격 시 교착 발생 |
| `PESSIMISTIC_FORCE_INCREMENT` | 높음 | `PESSIMISTIC_WRITE`와 동일 |
| `OPTIMISTIC` | 없음 | DB Lock을 잡지 않음 |
| `OPTIMISTIC_FORCE_INCREMENT` | 없음 | DB Lock을 잡지 않음 |

`PESSIMISTIC_READ`가 데드락 위험이 가장 높다. 쓰기 락으로 전환할 때 이미 다른 S Lock을 가진 트랜잭션과 교착 상태가 된다. 읽기 후 수정이 필요한 경우 처음부터 `PESSIMISTIC_WRITE`를 쓰는 게 낫다.

낙관적 락은 DB 락이 없어서 데드락은 발생하지 않지만, 충돌이 많으면 재시도 폭풍이 문제가 된다. 자세한 내용은 [낙관적 락 충돌 후 재시도 처리](./Optimistic_Lock_Retry_Pattern.md) 참고.

---

## 모드 선택 판단

```
재고·잔액처럼 충돌 확률이 높다
→ PESSIMISTIC_WRITE

읽기 동안 변경을 막고 싶고 이후 수정이 없다 (드문 케이스)
→ PESSIMISTIC_READ (S→X 승격 없을 때만)

낙관적 락 체계에서 읽기만 해도 충돌을 감지해야 한다
→ OPTIMISTIC

자식 엔티티 변경을 부모 version 체계에 반영해야 한다
→ OPTIMISTIC_FORCE_INCREMENT

비관적 락 + version 체계를 같이 써야 한다 (매우 드묾)
→ PESSIMISTIC_FORCE_INCREMENT
```

Spring Data JPA Repository에서 `@Lock`을 쓸 때 `@Query`를 함께 명시하지 않으면 메서드명으로 자동 생성된 쿼리에 락이 적용된다. 반환 타입이 단건이면 대부분 문제없지만, 컬렉션 반환 시 쿼리 생성이 예상과 다를 수 있어 `@Query`를 함께 선언하는 편이 안전하다.

---

이 문서는 [트랜잭션과 동시성 허브](../../../_hub/트랜잭션과_동시성.md)의 일부입니다.
