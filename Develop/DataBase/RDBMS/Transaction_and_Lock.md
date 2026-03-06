---
title: 트랜잭션과 Lock 심화 가이드
tags: [database, transaction, acid, isolation-level, lock, mvcc, deadlock, optimistic-lock, pessimistic-lock]
updated: 2026-03-01
---

# 트랜잭션과 Lock 심화

## 개요

트랜잭션(Transaction)은 데이터베이스에서 **하나의 논리적 작업 단위**이다. 여러 SQL 문을 묶어 전부 성공하거나 전부 실패하도록 보장한다. Lock은 동시에 여러 트랜잭션이 같은 데이터에 접근할 때 **일관성을 유지**하기 위한 메커니즘이다.

```
트랜잭션 없이:
  계좌 A에서 100만원 출금 → 성공
  계좌 B에 100만원 입금 → 실패 (네트워크 오류)
  → 100만원이 증발!

트랜잭션 사용:
  BEGIN
    계좌 A에서 100만원 출금
    계좌 B에 100만원 입금
  COMMIT (전부 성공) 또는 ROLLBACK (전부 취소)
  → 데이터 일관성 보장
```

## 핵심

### 1. ACID 속성

| 속성 | 의미 | 보장 메커니즘 |
|------|------|-------------|
| **Atomicity** (원자성) | 전부 성공 or 전부 실패 | Undo Log (롤백) |
| **Consistency** (일관성) | 트랜잭션 전후 데이터 무결성 유지 | 제약 조건, 트리거 |
| **Isolation** (격리성) | 동시 실행 트랜잭션이 서로 영향 없음 | Lock, MVCC |
| **Durability** (지속성) | 커밋된 데이터는 영구 보존 | Redo Log (WAL) |

```sql
-- 트랜잭션 기본
BEGIN;

UPDATE accounts SET balance = balance - 1000000
WHERE id = 'A';

UPDATE accounts SET balance = balance + 1000000
WHERE id = 'B';

-- 둘 다 성공하면
COMMIT;

-- 문제 발생 시
ROLLBACK;
```

### 2. 격리 수준 (Isolation Level)

동시 트랜잭션 간 **얼마나 격리할 것인가**를 결정한다.

#### 동시성 문제

```
1. Dirty Read (더티 리드)
   커밋되지 않은 데이터를 읽음

   T1: UPDATE balance = 0 WHERE id = 'A'  (미커밋)
   T2: SELECT balance FROM ... WHERE id = 'A'  → 0 (잘못된 값)
   T1: ROLLBACK  → 실제로는 원래 값이어야 함

2. Non-Repeatable Read (반복 불가 읽기)
   같은 쿼리를 두 번 실행했는데 결과가 다름

   T1: SELECT balance → 100만원
   T2: UPDATE balance = 50만원; COMMIT;
   T1: SELECT balance → 50만원  (값이 변경됨!)

3. Phantom Read (팬텀 리드)
   같은 조건의 쿼리인데 행의 수가 달라짐

   T1: SELECT COUNT(*) WHERE age > 20 → 5명
   T2: INSERT INTO users (age=25); COMMIT;
   T1: SELECT COUNT(*) WHERE age > 20 → 6명  (유령 행 출현!)
```

#### 격리 수준 비교

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read | 성능 |
|----------|-----------|-------------------|-------------|------|
| **READ UNCOMMITTED** | 발생 | 발생 | 발생 | 가장 빠름 |
| **READ COMMITTED** | 방지 | 발생 | 발생 | 빠름 |
| **REPEATABLE READ** | 방지 | 방지 | 발생 (InnoDB 방지) | 보통 |
| **SERIALIZABLE** | 방지 | 방지 | 방지 | 느림 |

```sql
-- 격리 수준 설정
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- MySQL 전역 설정
SET GLOBAL transaction_isolation = 'REPEATABLE-READ';

-- PostgreSQL
SET default_transaction_isolation = 'read committed';
```

#### 각 격리 수준 상세

```
READ UNCOMMITTED:
  다른 트랜잭션의 미커밋 데이터도 읽음
  사용: 거의 안 함 (로그 조회 등 극히 제한적)

READ COMMITTED (PostgreSQL 기본):
  커밋된 데이터만 읽음
  매 쿼리마다 최신 스냅샷 사용
  사용: 대부분의 OLTP 시스템

REPEATABLE READ (MySQL/InnoDB 기본):
  트랜잭션 시작 시점의 스냅샷 사용
  같은 쿼리는 항상 같은 결과
  InnoDB는 갭 락으로 Phantom Read도 방지
  사용: 금융, 재고 관리

SERIALIZABLE:
  트랜잭션을 완전히 순차 실행하는 것처럼 동작
  모든 SELECT에 공유 락
  사용: 극도의 정합성 필요 (결제 핵심 로직)
```

### 3. Lock (잠금)

#### Lock 종류

| Lock 유형 | 영문 | 동작 | 호환성 |
|----------|------|------|--------|
| **공유 락 (S Lock)** | Shared Lock | 읽기 허용, 쓰기 차단 | S + S 호환 |
| **배타 락 (X Lock)** | Exclusive Lock | 읽기/쓰기 모두 차단 | 모든 Lock과 충돌 |
| **의도 락 (IS/IX)** | Intention Lock | 테이블 레벨 의도 표시 | 행 락 효율화 |
| **갭 락 (Gap Lock)** | Gap Lock | 인덱스 사이 구간 잠금 | Phantom Read 방지 |

```sql
-- 공유 락 (SELECT ... FOR SHARE)
SELECT * FROM products WHERE id = 1 FOR SHARE;
-- 다른 트랜잭션도 읽기 가능, 쓰기는 대기

-- 배타 락 (SELECT ... FOR UPDATE)
SELECT * FROM products WHERE id = 1 FOR UPDATE;
-- 다른 트랜잭션은 읽기/쓰기 모두 대기

-- NOWAIT / SKIP LOCKED (대기 안 하고 즉시 처리)
SELECT * FROM orders WHERE status = 'PENDING'
FOR UPDATE SKIP LOCKED LIMIT 10;
-- 이미 락이 걸린 행은 건너뜀 (작업 큐 패턴)
```

#### Lock 범위

```
행 락 (Row Lock):
  특정 행만 잠금 → 동시성 높음
  InnoDB 기본 동작

페이지 락 (Page Lock):
  데이터 페이지 단위 잠금

테이블 락 (Table Lock):
  테이블 전체 잠금 → 동시성 낮음
  DDL 작업 시 자동 적용

갭 락 (Gap Lock):
  인덱스 값 사이의 "틈"을 잠금
  Phantom Read 방지

  예: age 인덱스에 10, 20, 30이 있을 때
  SELECT * WHERE age BETWEEN 10 AND 30 FOR UPDATE;
  → 10~30 사이 갭도 잠금 → INSERT age=25 차단
```

### 4. MVCC (다중 버전 동시성 제어)

Lock 대신 **데이터의 여러 버전을 유지**하여 읽기와 쓰기가 서로 차단하지 않는 방식.

```
MVCC 동작 (PostgreSQL):

T1 시작 (txid=100)
T2 시작 (txid=101)

  데이터: balance = 100만원 (version: txid=99)

T2: UPDATE balance = 50만원; COMMIT;
  → 새 버전 생성: balance = 50만원 (version: txid=101)

T1: SELECT balance
  → T1 시작 시점(txid=100) 기준 → 100만원 (이전 버전 읽음)
  → T2의 변경은 T1에게 보이지 않음 (Snapshot Isolation)
```

| 비교 | Lock 기반 | MVCC |
|------|----------|------|
| **읽기-쓰기 충돌** | 대기 (블로킹) | **대기 없음** |
| **읽기-읽기** | 동시 가능 | 동시 가능 |
| **쓰기-쓰기** | 대기 | 대기 (또는 충돌 감지) |
| **오버헤드** | 락 관리 | 버전 저장 공간 |
| **사용 DB** | 전통적 RDBMS | PostgreSQL, MySQL/InnoDB, Oracle |

### 5. 낙관적 vs 비관적 잠금

#### 비관적 잠금 (Pessimistic Lock)

**충돌이 자주 발생**할 것으로 예상할 때 사용. 데이터를 읽는 시점에 락을 건다.

```java
// JPA 비관적 잠금
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT p FROM Product p WHERE p.id = :id")
Optional<Product> findByIdWithLock(@Param("id") Long id);

// 사용
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findByIdWithLock(productId)
        .orElseThrow();
    product.decreaseStock(quantity);  // 재고 감소
    // 트랜잭션 종료 시 락 해제
}
```

```sql
-- SQL
BEGIN;
SELECT * FROM products WHERE id = 1 FOR UPDATE;  -- 락 획득
UPDATE products SET stock = stock - 1 WHERE id = 1;
COMMIT;  -- 락 해제
```

#### 낙관적 잠금 (Optimistic Lock)

**충돌이 드물게 발생**할 것으로 예상할 때 사용. 커밋 시점에 충돌을 감지한다.

```java
@Entity
public class Product {
    @Id
    private Long id;

    @Version  // 낙관적 잠금용 버전 컬럼
    private Long version;

    private int stock;
}

// 사용
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findById(productId)
        .orElseThrow();
    product.decreaseStock(quantity);
    // 커밋 시 version 체크 → 변경되었으면 OptimisticLockException
}
```

```sql
-- SQL (수동 구현)
SELECT id, stock, version FROM products WHERE id = 1;
-- 결과: stock=10, version=3

UPDATE products
SET stock = 9, version = 4
WHERE id = 1 AND version = 3;
-- 영향받은 행 0 → 다른 트랜잭션이 먼저 수정함 → 재시도
```

#### 재시도 패턴

```java
@Retryable(
    value = OptimisticLockException.class,
    maxAttempts = 3,
    backoff = @Backoff(delay = 100)
)
@Transactional
public void decreaseStock(Long productId, int quantity) {
    Product product = productRepository.findById(productId).orElseThrow();
    product.decreaseStock(quantity);
}
```

| 비교 | 비관적 잠금 | 낙관적 잠금 |
|------|-----------|-----------|
| **잠금 시점** | 데이터 읽기 시 | 데이터 커밋 시 |
| **충돌 처리** | 대기 (블로킹) | 예외 발생 → 재시도 |
| **동시성** | 낮음 | 높음 |
| **데드락 가능** | ✅ | ❌ |
| **적합한 경우** | 충돌 빈번 (재고 차감) | 충돌 드묾 (프로필 수정) |
| **구현** | `FOR UPDATE` | `@Version` |

### 6. 데드락 (Deadlock)

두 트랜잭션이 서로가 가진 락을 기다리며 **무한 대기**하는 상태.

```
T1: Lock(A) → Lock(B) 대기
T2: Lock(B) → Lock(A) 대기

  T1 ──Lock(A)──▶ ◀──Lock(A) 대기── T2
      ──Lock(B) 대기──▶ ◀──Lock(B)──

→ 둘 다 영원히 대기 (교착 상태)
```

```sql
-- 데드락 발생 예시
-- T1
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 'A';  -- Lock A
-- T2
BEGIN;
UPDATE accounts SET balance = balance - 200 WHERE id = 'B';  -- Lock B

-- T1
UPDATE accounts SET balance = balance + 100 WHERE id = 'B';  -- Lock B 대기 (T2가 보유)
-- T2
UPDATE accounts SET balance = balance + 200 WHERE id = 'A';  -- Lock A 대기 (T1이 보유)

-- → DEADLOCK! DB가 한쪽 트랜잭션을 강제 롤백
```

#### 데드락 방지

```sql
-- 1. 자원 접근 순서 통일
-- 항상 ID가 작은 것부터 잠금
BEGIN;
SELECT * FROM accounts WHERE id IN ('A', 'B')
ORDER BY id FOR UPDATE;  -- A → B 순서 보장

-- 2. 타임아웃 설정
SET innodb_lock_wait_timeout = 5;  -- 5초 대기 후 포기

-- 3. 트랜잭션 크기 최소화
-- 락 보유 시간을 줄임
```

```sql
-- 데드락 조회 (MySQL)
SHOW ENGINE INNODB STATUS;  -- LATEST DETECTED DEADLOCK 섹션 확인

-- PostgreSQL 데드락 로그
-- postgresql.conf: log_lock_waits = on
```

### 7. 실전 패턴

#### 재고 차감 (동시성 핵심)

```java
// 방법 1: 비관적 잠금
@Transactional
public void order(Long productId, int qty) {
    Product p = productRepository.findByIdWithPessimisticLock(productId);
    p.decreaseStock(qty);
}

// 방법 2: 낙관적 잠금 + 재시도
@Retryable(value = OptimisticLockException.class, maxAttempts = 3)
@Transactional
public void order(Long productId, int qty) {
    Product p = productRepository.findById(productId).orElseThrow();
    p.decreaseStock(qty);
}

// 방법 3: DB 레벨 원자적 연산 (가장 단순)
@Modifying
@Query("UPDATE Product p SET p.stock = p.stock - :qty WHERE p.id = :id AND p.stock >= :qty")
int decreaseStock(@Param("id") Long id, @Param("qty") int qty);
// 반환값 0이면 재고 부족 → 예외 처리

// 방법 4: Redis 분산 락 (MSA 환경)
public void order(Long productId, int qty) {
    String lockKey = "lock:product:" + productId;
    boolean locked = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "1", Duration.ofSeconds(5));
    if (!locked) throw new ConcurrencyException();
    try {
        // 재고 차감 로직
    } finally {
        redisTemplate.delete(lockKey);
    }
}
```

| 방법 | 장점 | 단점 | 적합한 경우 |
|------|------|------|-----------|
| 비관적 잠금 | 확실한 동시성 제어 | 대기 시간, 데드락 가능 | 재고 차감, 좌석 예약 |
| 낙관적 잠금 | 높은 동시성 | 충돌 시 재시도 비용 | 게시글 수정, 설정 변경 |
| DB 원자적 연산 | 단순, 빠름 | 복잡한 로직 불가 | 단순 카운터 |
| Redis 분산 락 | MSA 환경 지원 | 인프라 의존 | 분산 시스템 |

#### SKIP LOCKED 작업 큐

```sql
-- 작업 큐 패턴 (여러 워커가 동시에 작업 가져감)
BEGIN;
SELECT * FROM tasks
WHERE status = 'PENDING'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 1;

UPDATE tasks SET status = 'PROCESSING', worker_id = 'worker-1'
WHERE id = ?;
COMMIT;

-- SKIP LOCKED: 이미 다른 워커가 락 건 행은 건너뜀
-- → 동일 작업을 중복 처리하지 않음
```

## 참고

- [MySQL InnoDB Locking](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html)
- [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [인덱스 전략](RDBMS에서의 index.md) — 인덱스와 락의 관계
- [성능 튜닝](데이터베이스_성능_튜닝.md) — 쿼리 최적화
- [Deadlock](../../OS/Deadlock.md) — OS 레벨 데드락 개념
