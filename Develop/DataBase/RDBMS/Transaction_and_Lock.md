---
title: 트랜잭션과 Lock
tags: [database, transaction, acid, isolation-level, lock, mvcc, deadlock, OptimisticLock, pessimistic-lock, savepoint, spring-transactional]
updated: 2026-04-10
---

# 트랜잭션과 Lock

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

```
ACID와 실제 DB 내부 구조:

┌─────────────────────────────────────────────────┐
│                   트랜잭션                        │
│                                                   │
│   SQL 실행 ──→ Buffer Pool (메모리)               │
│       │              │                            │
│       ▼              ▼                            │
│   Undo Log      Redo Log (WAL)                    │
│   (롤백용)       (복구용)                          │
│       │              │                            │
│   ROLLBACK 시    COMMIT 시                        │
│   이전 상태로    디스크에 기록 보장                  │
│   되돌림         (fsync)                          │
└─────────────────────────────────────────────────┘
```

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

```
Lock 호환성 매트릭스:

            요청하는 Lock
보유 Lock   │  S (공유)  │  X (배타)
────────────┼───────────┼──────────
S (공유)    │  허용      │  대기
X (배타)    │  대기      │  대기

  T1이 S Lock 보유 → T2가 S Lock 요청 → 즉시 획득
  T1이 S Lock 보유 → T2가 X Lock 요청 → T1 해제까지 대기
  T1이 X Lock 보유 → T2가 아무 Lock 요청 → T1 해제까지 대기
```

#### 락 모니터링

운영 환경에서 느린 쿼리나 타임아웃이 발생하면 락 상태부터 확인한다.

**MySQL (InnoDB)**

```sql
-- 현재 실행 중인 트랜잭션 확인
SELECT trx_id, trx_state, trx_started, trx_wait_started,
       trx_mysql_thread_id, trx_query
FROM information_schema.innodb_trx;

-- 락 대기 관계 확인 (누가 누구를 막고 있는지)
SELECT
    r.trx_id AS waiting_trx_id,
    r.trx_query AS waiting_query,
    b.trx_id AS blocking_trx_id,
    b.trx_query AS blocking_query,
    b.trx_started AS blocking_since
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;

-- MySQL 8.0 이상에서는 performance_schema 사용
SELECT * FROM performance_schema.data_lock_waits;
SELECT * FROM performance_schema.data_locks;

-- 오래 실행 중인 트랜잭션 찾기 (5분 이상)
SELECT trx_id, trx_state, trx_started,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS running_seconds,
       trx_rows_locked, trx_rows_modified
FROM information_schema.innodb_trx
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 300;
```

**PostgreSQL**

```sql
-- 현재 락 보유/대기 현황
SELECT pid, mode, relation::regclass, granted,
       pg_blocking_pids(pid) AS blocked_by
FROM pg_locks
WHERE NOT granted;

-- 락 대기 중인 쿼리와 블로킹 쿼리를 함께 조회
SELECT
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query,
    NOW() - blocked.query_start AS waiting_duration
FROM pg_stat_activity blocked
JOIN pg_locks blocked_locks ON blocked.pid = blocked_locks.pid
JOIN pg_locks blocking_locks ON blocked_locks.relation = blocking_locks.relation
    AND blocked_locks.pid != blocking_locks.pid
JOIN pg_stat_activity blocking ON blocking_locks.pid = blocking.pid
WHERE NOT blocked_locks.granted;

-- 오래 실행 중인 트랜잭션
SELECT pid, state, query_start,
       NOW() - query_start AS duration,
       query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < NOW() - INTERVAL '5 minutes';
```

```
락 모니터링 시 확인 흐름:

1. 느린 쿼리/타임아웃 발생
      │
      ▼
2. innodb_trx / pg_stat_activity로 실행 중인 트랜잭션 확인
      │
      ▼
3. 락 대기 관계 확인 (누가 누구를 블로킹하는지)
      │
      ▼
4. 블로킹 트랜잭션의 쿼리/시작 시간 확인
      │
      ▼
5. 판단: 대기 or 강제 종료 (KILL / pg_terminate_backend)
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

```
MVCC 버전 관리 방식 비교:

PostgreSQL (다중 버전 저장):
┌──────────────┐
│ 원본 행        │  xmin=99, xmax=101 (dead tuple)
├──────────────┤
│ 새 행          │  xmin=101, xmax=∞   (live tuple)
└──────────────┘
→ UPDATE 시 원본 행을 지우지 않고 새 행을 추가
→ dead tuple이 누적됨 → VACUUM으로 정리

MySQL/InnoDB (Undo Log 방식):
┌──────────────┐
│ 최신 데이터     │  ← 테이블 공간에 저장
└──────┬───────┘
       │ roll_pointer
       ▼
┌──────────────┐
│ Undo Log      │  ← 이전 버전 (롤백 세그먼트에 저장)
└──────┬───────┘
       │ roll_pointer
       ▼
┌──────────────┐
│ Undo Log      │  ← 더 이전 버전
└──────────────┘
→ 테이블에는 최신 데이터만 유지
→ 이전 버전은 Undo Log 체인으로 추적
→ purge thread가 불필요한 Undo Log 정리
```

| 비교 | Lock 기반 | MVCC |
|------|----------|------|
| **읽기-쓰기 충돌** | 대기 (블로킹) | **대기 없음** |
| **읽기-읽기** | 동시 가능 | 동시 가능 |
| **쓰기-쓰기** | 대기 | 대기 (또는 충돌 감지) |
| **오버헤드** | 락 관리 | 버전 저장 공간 |
| **사용 DB** | 전통적 RDBMS | PostgreSQL, MySQL/InnoDB, Oracle |

#### MVCC 버전 정리 — VACUUM과 Purge

MVCC는 이전 버전 데이터를 보관하기 때문에, 정리하지 않으면 디스크와 성능에 문제가 생긴다.

**PostgreSQL — VACUUM**

PostgreSQL은 UPDATE/DELETE 시 기존 행을 바로 삭제하지 않는다. dead tuple로 남겨두고, 나중에 VACUUM이 정리한다.

```sql
-- 테이블별 dead tuple 확인
SELECT relname, n_live_tup, n_dead_tup,
       ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_ratio
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- 수동 VACUUM (일반)
VACUUM VERBOSE my_table;

-- VACUUM FULL (테이블 재작성 — 배타 락 걸림, 운영 중 주의)
VACUUM FULL my_table;
```

```
VACUUM 동작:

VACUUM (일반):
  dead tuple 공간을 "재사용 가능"으로 표시
  테이블 크기는 줄어들지 않음
  락 안 걸림, 운영 중 실행 가능

VACUUM FULL:
  테이블을 새로 작성하여 물리적으로 축소
  배타 락 걸림 → 운영 중 실행하면 서비스 중단
  대안: pg_repack 사용 (온라인으로 테이블 재작성)
```

autovacuum이 기본으로 켜져 있지만, 대량 UPDATE가 발생하는 테이블에서는 autovacuum이 따라가지 못하는 경우가 있다. 이때 흔히 발생하는 문제:

- **테이블 bloat**: dead tuple이 쌓여서 테이블 크기가 실제 데이터 대비 2~3배까지 커짐
- **인덱스 bloat**: 인덱스도 dead tuple을 참조하기 때문에 같이 비대해짐
- **Transaction ID Wraparound**: PostgreSQL의 txid는 32bit이므로 약 21억 개까지 사용 가능. VACUUM이 밀리면 wraparound 방지를 위해 DB가 강제로 읽기 전용 모드로 전환됨

```sql
-- autovacuum 설정 조정 (대량 쓰기 테이블)
ALTER TABLE high_write_table SET (
    autovacuum_vacuum_scale_factor = 0.01,    -- 기본 0.2 → 더 자주 실행
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay = 2          -- 기본 20ms → 더 공격적으로
);

-- Transaction ID 나이 확인 (wraparound 위험도)
SELECT relname, age(relfrozenxid) AS xid_age,
       pg_size_pretty(pg_relation_size(oid)) AS table_size
FROM pg_class
WHERE relkind = 'r'
ORDER BY age(relfrozenxid) DESC
LIMIT 10;
```

**MySQL/InnoDB — Purge**

InnoDB는 Undo Log에 이전 버전을 저장한다. purge thread가 더 이상 필요 없는 Undo Log를 삭제한다.

```sql
-- Undo Log 상태 확인
SHOW ENGINE INNODB STATUS\G
-- History list length 값 확인 → 높으면 purge가 밀리고 있다는 뜻

-- History list length 모니터링
SELECT NAME, COUNT FROM information_schema.innodb_metrics
WHERE NAME = 'trx_rseg_history_len';
```

```
History list length가 높아지는 원인:
  1. 장기 실행 트랜잭션이 오래된 스냅샷을 잡고 있음
     → purge가 해당 시점 이후의 Undo Log를 지울 수 없음
  2. purge thread가 쓰기 부하를 따라가지 못함
     → innodb_purge_threads 값 증가 고려 (기본 4)

History list length가 계속 증가하면:
  - Undo tablespace 크기 증가
  - 쿼리 성능 저하 (Undo Log 체인이 길어져서 이전 버전 조회가 느려짐)
  - 디스크 공간 부족
```

### 5. SAVEPOINT

트랜잭션 전체를 롤백하지 않고, **특정 지점까지만 되돌리고 싶을 때** 사용한다. 배치 처리에서 한 건 실패했다고 전체를 롤백하면 이미 처리한 건까지 날아가므로, SAVEPOINT로 부분 롤백하는 방식을 쓴다.

```sql
BEGIN;

INSERT INTO orders (id, amount) VALUES (1, 10000);
SAVEPOINT sp1;

INSERT INTO orders (id, amount) VALUES (2, 20000);
SAVEPOINT sp2;

INSERT INTO orders (id, amount) VALUES (3, 30000);
-- 3번 주문에 문제가 생겼다면
ROLLBACK TO SAVEPOINT sp2;
-- 1번, 2번 주문은 유지됨

-- 나머지 처리 후
COMMIT;
```

```
SAVEPOINT 동작:

BEGIN
  │
  ├── INSERT 1 ──→ SAVEPOINT sp1
  │                    │
  │                    ├── INSERT 2 ──→ SAVEPOINT sp2
  │                    │                    │
  │                    │                    ├── INSERT 3 (실패)
  │                    │                    │
  │                    │               ROLLBACK TO sp2
  │                    │               (INSERT 3만 취소)
  │                    │
  │                    ├── INSERT 4
  │                    │
COMMIT (INSERT 1, 2, 4 반영)
```

배치 처리에서의 활용:

```typescript
async processBatch(orders: Order[]): Promise<BatchResult> {
    let success = 0;
    let failed = 0;

    await this.dataSource.transaction(async (manager) => {
        for (const order of orders) {
            // SAVEPOINT 생성
            await manager.query(`SAVEPOINT sp_order_${order.id}`);
            try {
                await this.orderService.processOrder(order, manager);
                success++;
            } catch (e) {
                // 해당 건만 롤백
                await manager.query(`ROLLBACK TO SAVEPOINT sp_order_${order.id}`);
                failed++;
                logger.warn('주문 처리 실패', { orderId: order.id, error: e });
            }
        }
    });
    // 성공한 건들은 COMMIT됨
    return new BatchResult(success, failed);
}
```

주의사항:

- SAVEPOINT는 중첩할 수 있지만, 너무 많이 만들면 Undo Log가 커진다
- `ROLLBACK TO SAVEPOINT`는 SAVEPOINT를 제거하지 않는다. 같은 이름으로 다시 ROLLBACK 가능
- `RELEASE SAVEPOINT`로 명시적으로 제거할 수 있다
- MySQL에서는 DDL 문(ALTER TABLE 등)이 실행되면 모든 SAVEPOINT가 사라진다

### 6. 낙관적 vs 비관적 잠금

#### 비관적 잠금 (Pessimistic Lock)

**충돌이 자주 발생**할 것으로 예상할 때 사용. 데이터를 읽는 시점에 락을 건다.

```typescript
// TypeORM 비관적 잠금
async findByIdWithLock(id: number): Promise<Product> {
    return this.productRepository.findOne({
        where: { id },
        lock: { mode: 'pessimistic_write' },
    });
}

// 사용
async decreaseStock(productId: number, quantity: number): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        const product = await manager.findOne(Product, {
            where: { id: productId },
            lock: { mode: 'pessimistic_write' },
        });
        product.decreaseStock(quantity);  // 재고 감소
        await manager.save(product);
        // 트랜잭션 종료 시 락 해제
    });
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

```typescript
@Entity()
export class Product {
    @PrimaryGeneratedColumn()
    id: number;

    @VersionColumn()  // 낙관적 잠금용 버전 컬럼
    version: number;

    @Column()
    stock: number;
}

// 사용
async decreaseStock(productId: number, quantity: number): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        const product = await manager.findOne(Product, {
            where: { id: productId },
            lock: { mode: 'optimistic', version: undefined },
        });
        product.decreaseStock(quantity);
        await manager.save(product);
        // 커밋 시 version 체크 → 변경되었으면 OptimisticLockVersionMismatchError
    });
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

```typescript
async decreaseStock(productId: number, quantity: number, attempt = 0): Promise<void> {
    const maxAttempts = 3;
    try {
        await this.dataSource.transaction(async (manager) => {
            const product = await manager.findOne(Product, { where: { id: productId } });
            product.decreaseStock(quantity);
            await manager.save(product);
        });
    } catch (e) {
        if (e instanceof OptimisticLockVersionMismatchError && attempt < maxAttempts - 1) {
            await new Promise((res) => setTimeout(res, 100));
            return this.decreaseStock(productId, quantity, attempt + 1);
        }
        throw e;
    }
}
```

| 비교 | 비관적 잠금 | 낙관적 잠금 |
|------|-----------|-----------|
| **잠금 시점** | 데이터 읽기 시 | 데이터 커밋 시 |
| **충돌 처리** | 대기 (블로킹) | 예외 발생 → 재시도 |
| **동시성** | 낮음 | 높음 |
| **데드락 가능** | 있음 | 없음 |
| **적합한 경우** | 충돌 빈번 (재고 차감) | 충돌 드묾 (프로필 수정) |
| **구현** | `FOR UPDATE` | `@Version` |

### 7. 데드락 (Deadlock)

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

### 8. 트랜잭션 실무 주의사항

트랜잭션을 잘못 사용할 때 빈번하게 발생하는 문제들이 있다.

#### 내부 호출 시 트랜잭션 미적용 문제

같은 클래스 내부에서 트랜잭션 메서드를 직접 호출하면 **별도 트랜잭션이 시작되지 않아** 의도한 원자성이 보장되지 않는다.

```typescript
@Injectable()
export class OrderService {

    createOrder(request: OrderRequest): void {
        // 이 호출은 dataSource.transaction 밖에서 실행 → 트랜잭션 미적용
        this.processPayment(request);
    }

    async processPayment(request: OrderRequest): Promise<void> {
        // 트랜잭션이 걸려야 하지만, 내부 호출이라 안 걸림
        await this.dataSource.transaction(async (manager) => {
            await manager.save(Payment, payment);
            await manager.update(Account, { userId: request.userId }, { balance: () => `balance - ${request.amount}` });
        });
    }
}
```

```
트랜잭션 범위 동작 방식:

올바른 호출 (트랜잭션 적용됨):
  Controller ──→ PaymentService.processPayment()
                     │
                     └── dataSource.transaction() → BEGIN / COMMIT 처리

내부 호출 (트랜잭션 미적용):
  OrderService.createOrder() ──→ this.processPayment()
                                   │
                                   └── 별도 트랜잭션 없음 → dataSource.transaction() 미호출
```

해결 방법:

```typescript
// 방법 1: 별도 서비스로 분리 (권장)
@Injectable()
export class OrderService {
    constructor(private readonly paymentService: PaymentService) {}

    async createOrder(request: OrderRequest): Promise<void> {
        await this.paymentService.processPayment(request);  // 별도 서비스에서 트랜잭션 처리
    }
}

@Injectable()
export class PaymentService {
    constructor(private readonly dataSource: DataSource) {}

    async processPayment(request: OrderRequest): Promise<void> {
        await this.dataSource.transaction(async (manager) => {
            // 트랜잭션 정상 동작
        });
    }
}
```

#### 읽기 전용 커넥션과 쓰기 혼용 문제

읽기 전용 복제본(replica) 커넥션에서 쓰기 메서드를 호출하면, **읽기 전용 커넥션에서 쓰기가 실패**하는 경우가 있다.

```typescript
@Injectable()
export class ReportService {
    constructor(
        private readonly reportRepository: ReportRepository,
        private readonly auditService: AuditService,
    ) {}

    // 읽기 전용 연결로 실행
    async generateReport(userId: number): Promise<Report> {
        const report = await this.reportRepository.calculate(userId);

        // 문제: auditService는 읽기 전용 연결로 쓰기를 시도하면 실패 가능
        await this.auditService.logReportGeneration(userId);  // 쓰기 동작 → 실패 가능

        return report;
    }
}

@Injectable()
export class AuditService {
    constructor(private readonly dataSource: DataSource) {}

    async logReportGeneration(userId: number): Promise<void> {
        // 별도 트랜잭션으로 쓰기 처리
        await this.dataSource.transaction(async (manager) => {
            await manager.save(AuditLog, { userId, action: 'REPORT_GENERATED' });
        });
    }
}
```

```
읽기 전용 커넥션 혼용 상황:

generateReport() → 읽기 전용 커넥션 사용
    │
    ├── SELECT (정상)
    │
    └── logReportGeneration() → 쓰기 시도
            │
            └── 읽기 전용 커넥션에서 INSERT 시도
                → 실패 (read-only connection error)
```

해결:

```typescript
@Injectable()
export class AuditService {
    constructor(private readonly dataSource: DataSource) {}

    // 항상 별도 트랜잭션으로 실행
    async logReportGeneration(userId: number): Promise<void> {
        await this.dataSource.transaction(async (manager) => {
            await manager.save(AuditLog, { userId, action: 'REPORT_GENERATED' });
        });
    }
}
```

#### 에러 발생 시 롤백 동작

TypeScript/Node.js에서는 `dataSource.transaction()` 내부에서 에러가 throw되면 **항상 자동으로 롤백**된다. Java Spring과 달리 checked/unchecked 예외 구분이 없다.

```typescript
// 문제 없음: TypeScript/Node.js에는 checked/unchecked 구분이 없음
// throw된 에러는 항상 트랜잭션 롤백 트리거
async transferMoney(from: number, to: number, amount: number): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        await this.accountRepository.withdraw(from, amount, manager);
        await this.accountRepository.deposit(to, amount, manager);

        if (someConditionFails()) {
            // 에러를 throw하면 트랜잭션이 롤백됨
            throw new InsufficientBalanceError('잔액 부족');
        }
    });
}
```

```
dataSource.transaction() 롤백 규칙 (TypeScript/TypeORM):

  throw Error (모든 종류) → 롤백 O
  정상 종료               → 커밋 O
  → Java의 checked exception 문제 없음
```

해결:

```typescript
// TypeScript에서는 모든 에러가 throw되면 트랜잭션 롤백됨 — 별도 설정 불필요
async transferMoney(from: number, to: number, amount: number): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        await this.accountRepository.withdraw(from, amount, manager);
        await this.accountRepository.deposit(to, amount, manager);
    });
    // 에러 발생 시 자동 롤백
}

// 커스텀 에러 클래스 (TypeScript)
export class InsufficientBalanceError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'InsufficientBalanceError';
    }
}
```

TypeScript/Node.js에서는 모든 에러가 동일하게 처리되므로 `dataSource.transaction()` 내부에서 throw된 에러는 종류에 관계없이 항상 롤백된다.

### 9. 장기 트랜잭션과 커넥션 풀 고갈

트랜잭션이 오래 열려 있으면 그 트랜잭션이 점유한 DB 커넥션은 풀에 반환되지 않는다. 동시 요청이 많은 상황에서 장기 트랜잭션 몇 개가 커넥션 풀을 고갈시키면 **전체 서비스가 멈춘다**.

```
장기 트랜잭션 → 커넥션 풀 고갈 흐름:

커넥션 풀 (max=10)
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│사│사│사│사│사│사│사│사│  │  │   ← 8개 사용 중
│용│용│용│용│용│용│용│용│  │  │
└──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘

이 중 3개가 장기 트랜잭션 (외부 API 호출, 대량 처리 등)
→ 3개 커넥션이 수 분간 반환 안 됨
→ 새 요청 7개 → 풀에 남은 커넥션 2개 → 5개는 대기
→ 대기 타임아웃 → ConnectionPoolExhausted

다른 정상적인 짧은 트랜잭션까지 전부 실패
```

흔히 발생하는 원인:

```typescript
// 문제 1: 트랜잭션 안에서 외부 API 호출
async processOrder(order: Order): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        await manager.save(Order, order);

        // 외부 API 호출 — 응답이 3초 걸림
        // 이 시간 동안 DB 커넥션을 잡고 있음
        const result = await this.paymentGateway.charge(order.amount);

        order.paymentId = result.id;
        await manager.save(Order, order);
    });
}

// 해결: 트랜잭션 밖에서 외부 호출
async processOrder(order: Order): Promise<void> {
    // 1단계: 주문 저장 (짧은 트랜잭션)
    await this.orderService.saveOrder(order);

    // 2단계: 외부 API 호출 (트랜잭션 밖)
    const result = await this.paymentGateway.charge(order.amount);

    // 3단계: 결과 저장 (짧은 트랜잭션)
    await this.orderService.updatePaymentResult(order.id, result);
}
```

```typescript
// 문제 2: 대량 데이터 처리를 한 트랜잭션으로
async migrateAllUsers(): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        const users = await manager.find(User);  // 100만 건
        for (const user of users) {
            user.status = 'MIGRATED';
            // 100만 건 처리 동안 커넥션 점유
        }
        await manager.save(User, users);
    });
}

// 해결: 배치 단위로 분할
async migrateAllUsers(): Promise<void> {
    const batchSize = 1000;
    let page = 0;
    let hasMore = true;

    while (hasMore) {
        const batch = await this.userRepository.find({
            skip: page * batchSize,
            take: batchSize,
        });
        if (batch.length === 0) { hasMore = false; break; }
        await this.migrateService.migrateBatch(batch);  // 별도 트랜잭션
        page++;
    }
}

async migrateBatch(users: User[]): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        // 1000건씩만 처리 → 커넥션 빨리 반환
        users.forEach((u) => { u.status = 'MIGRATED'; });
        await manager.save(User, users);
    });
}
```

HikariCP 설정에서 `leak-detection-threshold`를 설정하면 커넥션을 오래 잡고 있는 코드를 로그로 잡아낼 수 있다:

```yaml
# application.yml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      connection-timeout: 3000          # 커넥션 대기 최대 3초
      leak-detection-threshold: 30000   # 30초 이상 반환 안 하면 경고 로그
```

### 10. 실전 패턴

#### 재고 차감 (동시성 핵심)

```typescript
// 방법 1: 비관적 잠금
async order(productId: number, qty: number): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
        const p = await manager.findOne(Product, {
            where: { id: productId },
            lock: { mode: 'pessimistic_write' },
        });
        p.decreaseStock(qty);
        await manager.save(p);
    });
}

// 방법 2: 낙관적 잠금 + 재시도
async order(productId: number, qty: number, attempt = 0): Promise<void> {
    try {
        await this.dataSource.transaction(async (manager) => {
            const p = await manager.findOne(Product, { where: { id: productId } });
            p.decreaseStock(qty);
            await manager.save(p);
        });
    } catch (e) {
        if (e instanceof OptimisticLockVersionMismatchError && attempt < 2) {
            return this.order(productId, qty, attempt + 1);
        }
        throw e;
    }
}

// 방법 3: DB 레벨 원자적 연산 (가장 단순)
async decreaseStock(id: number, qty: number): Promise<number> {
    const result = await this.productRepository
        .createQueryBuilder()
        .update(Product)
        .set({ stock: () => `stock - ${qty}` })
        .where('id = :id AND stock >= :qty', { id, qty })
        .execute();
    return result.affected ?? 0;
    // 반환값 0이면 재고 부족 → 예외 처리
}

// 방법 4: Redis 분산 락 (MSA 환경)
async order(productId: number, qty: number): Promise<void> {
    const lockKey = `lock:product:${productId}`;
    const locked = await this.redis.set(lockKey, '1', 'EX', 5, 'NX');
    if (!locked) throw new ConcurrencyError();
    try {
        // 재고 차감 로직
    } finally {
        await this.redis.del(lockKey);
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
- [인덱스 전략](RDBMS에서의%20index.md) — 인덱스와 락의 관계
- [성능 튜닝](데이터베이스_성능_튜닝.md) — 쿼리 최적화
- [Deadlock](../../OS/Process%20%26%20Thread/Deadlock.md) — OS 레벨 데드락 개념

---
이 문서는 [트랜잭션과 동시성 허브](../../_hub/트랜잭션과_동시성.md)의 일부입니다.
