---
title: MySQL InnoDB 락 심화
tags: [mysql, rdbms, database]
updated: 2026-07-30
---

# MySQL InnoDB 락 심화

## 락이 인덱스 레코드에 걸린다는 의미

InnoDB의 락은 행(row)이 아니라 인덱스 레코드에 걸린다. 이 한 가지 사실을 모르면 "왜 이 쿼리가 다른 행까지 잠그지?"라는 의문을 계속 해결 못 한다.

테이블에 인덱스가 없으면 InnoDB는 내부적으로 생성한 클러스터드 인덱스(rowid)를 사용한다. WHERE 절에 인덱스가 없는 컬럼을 쓰면 MySQL은 그 조건을 만족하는 행을 찾기 위해 클러스터드 인덱스를 전체 스캔한다. 스캔하는 모든 레코드에 락이 걸린다. WHERE 조건을 만족하는 행 하나만 잠그고 싶었는데 테이블 전체에 락이 걸리는 상황이 된다.

## Record Lock

인덱스 레코드 하나에 걸리는 락이다. `id = 5`처럼 고유 인덱스를 사용한 단일 행 조회가 여기에 해당한다.

```sql
-- 트랜잭션 A: id = 5에 Record Lock
SELECT * FROM orders WHERE id = 5 FOR UPDATE;
```

이 쿼리는 id = 5인 인덱스 레코드 하나에만 X락을 건다. 다른 트랜잭션이 id = 5를 건드리려 하면 대기하고, id = 6은 영향을 받지 않는다.

## Gap Lock

인덱스 레코드 사이의 간격(gap)에 걸리는 락이다. Gap Lock이 존재하는 이유는 Phantom Read 방지다. REPEATABLE READ 격리 수준에서 같은 범위 쿼리를 두 번 실행했을 때 새 행이 끼어들지 않도록 막는다.

id 컬럼에 값 1, 5, 10이 있다고 가정한다.

```sql
-- 트랜잭션 A: id 6~9 범위에 Gap Lock
SELECT * FROM orders WHERE id BETWEEN 6 AND 9 FOR UPDATE;
```

여기서 id = 7인 행은 없지만, 다른 트랜잭션이 id = 7을 INSERT하면 대기한다. Gap Lock은 레코드가 아닌 간격 자체를 잠그기 때문이다.

중요한 특성이 있다. Gap Lock은 서로 충돌하지 않는다. 두 트랜잭션이 같은 간격에 Gap Lock을 동시에 걸 수 있다. 이 특성이 데드락의 원인이 되기도 한다.

## Next-Key Lock

Record Lock과 Gap Lock을 합친 형태다. 레코드 자체와 그 레코드 앞의 간격을 함께 잠근다. InnoDB가 REPEATABLE READ에서 기본으로 사용하는 락 형태다.

id 컬럼에 1, 5, 10이 있을 때 Next-Key Lock의 범위는 이렇게 나뉜다:

```
(-∞, 1]
(1, 5]
(5, 10]
(10, +∞)
```

```sql
-- id = 5 조회 시 (1, 5] 범위에 Next-Key Lock
SELECT * FROM orders WHERE id = 5 FOR UPDATE;
```

유니크 인덱스를 사용한 단일 행 조회는 예외다. 이 경우 Next-Key Lock이 Record Lock으로 축소된다. 반면 세컨더리 인덱스나 범위 조건은 Next-Key Lock이 그대로 걸린다.

## 인덱스 없는 컬럼 UPDATE의 위험성

실무에서 데드락이 나는 가장 흔한 원인 중 하나다.

```sql
-- status 컬럼에 인덱스가 없는 경우
UPDATE orders SET amount = 1000 WHERE status = 'PENDING';
```

MySQL은 status = 'PENDING'인 행을 찾으려면 전체 클러스터드 인덱스를 스캔해야 한다. 스캔하는 과정에서 지나치는 모든 레코드에 Next-Key Lock이 걸린다. 실제로 업데이트되는 행이 3개뿐이어도 테이블의 모든 행과 모든 gap에 락이 걸릴 수 있다.

동시에 다른 트랜잭션이 같은 패턴의 쿼리를 다른 status 값으로 실행하면, 두 트랜잭션이 서로 상대방이 잠근 레코드를 기다리면서 데드락이 발생한다.

status 컬럼에 인덱스를 추가하면 InnoDB가 해당 인덱스를 타고 실제로 필요한 레코드만 스캔한다. 락 범위가 그만큼 줄어든다.

## 범위 쿼리에서의 Next-Key Lock 과도 잠금

날짜나 상태 기반 범위 쿼리는 예상보다 훨씬 넓은 범위를 잠근다.

```sql
SELECT * FROM orders 
WHERE created_at >= '2024-01-01' AND created_at < '2024-02-01' 
FOR UPDATE;
```

이 쿼리는 조건에 맞는 레코드뿐 아니라 범위 내 모든 gap에도 락을 건다. 1월 15일에 새 행을 INSERT하면 대기 상태가 된다.

배치 작업에서 이런 쿼리를 자주 쓰면 일반 트랜잭션의 INSERT가 줄줄이 대기 상태가 된다. 데드락이 없어도 배치와 서비스가 서로 발목을 잡는 상황이 된다.

`FOR UPDATE` 없이 SELECT 후 애플리케이션 레벨에서 처리하거나, 배치를 작은 단위로 쪼개서 커밋 주기를 짧게 가져가는 방법을 쓴다.

## EXPLAIN으로 락 범위 예측

락 문제를 디버깅하기 전에 어떤 인덱스를 쓰는지, 얼마나 많은 레코드를 스캔하는지 먼저 파악한다. EXPLAIN이 그 도구다.

```sql
EXPLAIN SELECT * FROM orders WHERE status = 'PENDING' FOR UPDATE\G
```

출력에서 핵심은 `type`과 `rows` 컬럼이다.

```
*************************** 1. row ***************************
           id: 1
  select_type: SIMPLE
        table: orders
         type: ALL          ← 풀 스캔
possible_keys: NULL
          key: NULL         ← 인덱스 미사용
         rows: 150000       ← 15만 행 스캔
        Extra: Using where
```

`type: ALL`, `key: NULL`이면 테이블 전체 스캔이다. 15만 행 전체에 Next-Key Lock이 걸린다. 이 상태에서 동시 UPDATE 두 개가 실행되면 데드락 확률이 매우 높다.

인덱스를 추가한 후:

```
         type: ref          ← 인덱스 사용
          key: idx_status
         rows: 1200         ← 1,200행만 스캔
        Extra: Using index condition
```

`type: ref`로 바뀌고 스캔 행이 줄면 락도 그만큼만 걸린다. 추정 rows와 실제 락 수가 항상 일치하지는 않지만, 줄기는 한다.

### type 값별 락 범위

| type 값 | 의미 | 예상 락 범위 |
|---|---|---|
| ALL | 풀 테이블 스캔 | 전체 테이블 |
| index | 인덱스 풀 스캔 | 인덱스 전체 |
| range | 인덱스 범위 스캔 | 조건 범위 내 레코드 + gap |
| ref | 비유니크 인덱스 동등 조건 | 해당 인덱스 레코드 + gap |
| eq_ref | 유니크 인덱스 조인 | 해당 레코드 (Record Lock) |
| const | 기본키/유니크 단일 조회 | 해당 레코드 하나 (Record Lock) |

`const`나 `eq_ref`가 나오면 Record Lock 하나만 걸린다. `range`나 `ref`는 Gap Lock이 추가된다. `ALL`이나 `index`는 테이블 전체 락을 각오해야 한다.

### 세컨더리 인덱스와 클러스터드 인덱스 이중 락

세컨더리 인덱스를 사용한 FOR UPDATE 쿼리는 세컨더리 인덱스 레코드와 클러스터드 인덱스(기본키) 레코드 양쪽에 락이 걸린다.

```sql
-- idx_status 세컨더리 인덱스 사용
SELECT * FROM orders WHERE status = 'PENDING' FOR UPDATE;
```

InnoDB는 세컨더리 인덱스에서 조건을 걸러낸 뒤 실제 행을 읽기 위해 클러스터드 인덱스로 접근한다. 이 과정에서 두 인덱스 모두에 락이 생긴다. performance_schema.data_locks에서 같은 행에 대해 두 줄이 나오는 이유가 여기 있다.

## 트랜잭션 시나리오별 락 경합 패턴

실무에서 데드락이나 락 대기가 발생하는 상황은 몇 가지 패턴으로 수렴한다.

### 패턴 1: 업데이트 순서 역전 데드락

두 트랜잭션이 같은 행들을 다른 순서로 업데이트한다. 가장 고전적인 데드락 패턴이다.

```
트랜잭션 A                           트랜잭션 B
------                               ------
BEGIN                                BEGIN
UPDATE orders SET ... WHERE id=1
-- id=1 Record Lock 획득
                                     UPDATE orders SET ... WHERE id=2
                                     -- id=2 Record Lock 획득
UPDATE orders SET ... WHERE id=2
-- id=2 대기 (B가 잡고 있음)
                                     UPDATE orders SET ... WHERE id=1
                                     -- id=1 대기 (A가 잡고 있음) → 데드락
```

해결책은 항상 같은 순서로 잠그는 것이다. A와 B 모두 id 오름차순으로 처리하면 B는 A가 id=1을 처리할 때까지 기다리고, A가 id=2로 넘어가면 B가 id=1을 잡는 구조가 된다.

```java
// 반드시 id 오름차순 정렬 후 처리
List<Long> ids = List.of(orderId1, orderId2);
Collections.sort(ids);
for (Long id : ids) {
    orderRepository.findByIdForUpdate(id);
}
```

### 패턴 2: 재고 차감 경합

동시에 여러 요청이 같은 재고 행을 차감하는 경우다.

```sql
-- 요청 A, B, C가 동시에 실행
BEGIN;
SELECT stock FROM products WHERE id = 100 FOR UPDATE;
-- A가 먼저 X락 획득, B와 C는 대기
UPDATE products SET stock = stock - 1 WHERE id = 100;
COMMIT;
-- 커밋 후 B가 락 획득, 이어서 C
```

이 패턴은 데드락이 아니라 직렬 대기다. A가 끝나면 B가, B가 끝나면 C가 실행된다. 동시 요청이 100개면 마지막 요청은 앞선 99개가 끝날 때까지 기다린다.

`innodb_lock_wait_timeout`(기본 50초)을 넘기면 오류가 발생한다. 초당 수십 건의 동시 재고 차감이 발생하는 서비스라면 이 방식은 병목이 된다.

SELECT 없이 단일 UPDATE로 처리하는 방식이 락 보유 시간을 줄인다:

```sql
UPDATE products 
SET stock = stock - 1 
WHERE id = 100 AND stock > 0;
-- affected rows가 0이면 재고 부족 처리
```

단일 UPDATE는 내부적으로 행을 읽고 쓰는 과정이 있지만, SELECT FOR UPDATE + UPDATE 두 번으로 잠그는 것보다 락 보유 시간이 짧다.

### 패턴 3: 주문-결제 락 순서 충돌

주문 생성과 결제 처리가 서로 다른 테이블을 다른 순서로 잠그는 경우다.

```
주문 생성 트랜잭션 A                  결제 처리 트랜잭션 B
------                               ------
BEGIN                                BEGIN

SELECT * FROM accounts               SELECT * FROM orders
WHERE id = 1 FOR UPDATE              WHERE id = 101 FOR UPDATE
-- accounts(id=1) X락 획득            -- orders(id=101) X락 획득

INSERT INTO orders ...               UPDATE accounts
                                     SET balance = balance - 5000
SELECT * FROM orders                 WHERE id = 1 FOR UPDATE
WHERE id = 101 FOR UPDATE            -- accounts(id=1) 대기
-- orders(id=101) 대기 → 데드락
```

테이블 접근 순서를 전사적으로 통일해야 한다. "항상 accounts → orders 순서로 잠근다"는 규칙을 코드 레벨에서 강제한다. 어느 한 곳에서 순서가 뒤집히면 데드락 조건이 완성된다.

### 패턴 4: 배치와 실시간 INSERT 충돌

배치가 날짜 범위로 FOR UPDATE를 걸면, 그 범위에 속하는 INSERT가 전부 대기 상태가 된다.

```
배치 트랜잭션                         실시간 주문 생성 트랜잭션
------                               ------
BEGIN

SELECT * FROM orders
WHERE created_at >= '2024-01-01'
AND created_at < '2024-02-01'
FOR UPDATE;
-- (2024-01-01, 2024-02-01) 범위 전체에 Gap Lock
                                     INSERT INTO orders
                                     (created_at, ...)
                                     VALUES ('2024-01-15', ...);
                                     -- Gap Lock에 막혀 대기
```

배치 처리 시간이 5분이면 그 5분 동안 1월의 신규 주문이 전부 대기한다. 운영 시간대에 이런 배치를 돌리면 안 되는 이유다. 배치를 작은 단위로 쪼개서 커밋 주기를 짧게 가져가거나, FOR UPDATE 없이 처리하는 방향으로 설계를 바꾼다.

### 패턴 5: 세컨더리 인덱스 UPDATE 데드락

서로 다른 세컨더리 인덱스를 사용하는 UPDATE 두 개가 같은 클러스터드 인덱스 행에서 충돌한다.

```sql
-- 세션 A: idx_user_id 인덱스 사용
UPDATE orders SET status = 'DONE' WHERE user_id = 10;

-- 세션 B: idx_status 인덱스 사용 (동시에 실행)
UPDATE orders SET user_id = 20 WHERE status = 'PENDING';
```

세션 A는 `idx_user_id → 클러스터드 인덱스` 순서로 락을 획득한다. 세션 B는 `idx_status → 클러스터드 인덱스` 순서로 락을 획득한다. 두 쿼리가 클러스터드 인덱스의 동일한 행에서 충돌하면서 데드락이 난다.

## performance_schema 활용 데드락 추적

### 현재 락 상황 파악

```sql
SELECT 
    dl.engine_lock_id,
    dl.thread_id,
    dl.object_name AS table_name,
    dl.index_name,
    dl.lock_type,
    dl.lock_mode,
    dl.lock_status,
    dl.lock_data
FROM performance_schema.data_locks dl
WHERE dl.object_name = 'orders'
ORDER BY dl.thread_id;
```

`lock_mode` 값 해석:
- `X`: Next-Key Lock (배타 락 + gap)
- `X,REC_NOT_GAP`: Record Lock만 (gap 제외)
- `X,GAP`: Gap Lock만
- `S`: Shared Next-Key Lock
- `S,REC_NOT_GAP`: Shared Record Lock

`lock_data` 컬럼에 인덱스 키 값이 나온다. `supremum pseudo-record`는 인덱스의 마지막 레코드 이후 gap을 의미한다.

### 락 대기 관계 조회

```sql
SELECT
    r.thread_id AS waiting_thread,
    r.object_name AS table_name,
    r.index_name,
    r.lock_mode AS waiting_mode,
    b.thread_id AS blocking_thread,
    b.lock_mode AS blocking_mode,
    b.lock_data
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks r 
    ON r.engine_lock_id = w.requesting_engine_lock_id
JOIN performance_schema.data_locks b 
    ON b.engine_lock_id = w.blocking_engine_lock_id;
```

### 실행 중인 트랜잭션과 연결

```sql
SELECT
    r_trx.trx_id AS waiting_trx_id,
    r_trx.trx_started AS waiting_started,
    r_trx.trx_query AS waiting_query,
    b_trx.trx_id AS blocking_trx_id,
    b_trx.trx_started AS blocking_started,
    b_trx.trx_query AS blocking_query,
    TIMESTAMPDIFF(SECOND, r_trx.trx_started, NOW()) AS wait_seconds
FROM performance_schema.data_lock_waits w
JOIN information_schema.innodb_trx r_trx 
    ON r_trx.trx_id = w.requesting_engine_transaction_id
JOIN information_schema.innodb_trx b_trx 
    ON b_trx.trx_id = w.blocking_engine_transaction_id
ORDER BY wait_seconds DESC;
```

`wait_seconds`가 30초를 넘는 행이 있으면 `innodb_lock_wait_timeout`으로 곧 오류가 난다.

### sys 스키마 활용

MySQL 8.0에서는 `sys.innodb_lock_waits` 뷰가 위 조인을 미리 해놓은 형태로 제공한다.

```sql
SELECT * FROM sys.innodb_lock_waits\G
```

출력에 `wait_age`, `locked_table`, `blocking_query` 등이 한 번에 나온다. 운영 장애 상황에서 빠르게 파악할 때 쓴다.

### 데드락 이력 확인

MySQL은 마지막 데드락 하나만 메모리에 유지한다. 이전 데드락은 에러 로그에서 찾아야 한다.

```sql
-- 데드락 발생 시 에러 로그에 기록
SET GLOBAL innodb_print_all_deadlocks = ON;
```

이 설정을 켜두면 데드락이 발생할 때마다 MySQL 에러 로그(`/var/log/mysql/error.log`)에 기록된다. 데드락 빈도가 높다면 로그가 빠르게 쌓이므로 로그 로테이션 설정을 확인한다.

현재 설정 확인:

```sql
SHOW VARIABLES LIKE 'innodb_print_all_deadlocks';
```

마지막 데드락은 여기서 확인한다:

```sql
SHOW ENGINE INNODB STATUS\G
```

## 데드락 로그 읽는 법

데드락이 발생하면 MySQL은 가장 최근 데드락 정보를 메모리에 보관한다.

```sql
SHOW ENGINE INNODB STATUS\G
```

출력에서 `LATEST DETECTED DEADLOCK` 섹션을 찾는다.

```
------------------------
LATEST DETECTED DEADLOCK
------------------------
2024-03-15 14:23:01 0x7f...
*** (1) TRANSACTION:
TRANSACTION 421893, ACTIVE 0 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 3 lock struct(s), heap size 1128, 2 row lock(s)
MySQL thread id 142, OS thread handle ..., query id 8924 ...
UPDATE orders SET status = 'DONE' WHERE id = 10

*** (1) HOLDS THE LOCK(S):
RECORD LOCKS space id 45 page no 4 n bits 72 index PRIMARY of table `shop`.`orders`
trx id 421893 lock_mode X locks rec but not gap
Record lock, heap no 3 PHYSICAL RECORD: n_fields 5; compact format; info bits 0
 0: len 8; hex 8000000000000005; asc         ;;  -- id = 5

*** (1) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 45 page no 4 n bits 72 index PRIMARY of table `shop`.`orders`
trx id 421893 lock_mode X locks rec but not gap waiting
Record lock, heap no 5 PHYSICAL RECORD: n_fields 5; compact format; info bits 0
 0: len 8; hex 800000000000000a; asc         ;;  -- id = 10
```

읽는 순서가 있다. 트랜잭션 1이 무엇을 들고 있고(HOLDS THE LOCK) 무엇을 기다리는지(WAITING FOR), 트랜잭션 2가 무엇을 들고 있고 무엇을 기다리는지를 각각 파악한다. 트랜잭션 1이 기다리는 것을 트랜잭션 2가 들고 있고, 트랜잭션 2가 기다리는 것을 트랜잭션 1이 들고 있으면 데드락이다.

`lock_mode` 부분에서 락의 종류를 확인한다:
- `X locks rec but not gap`: Record Lock (X)
- `X locks gap before rec`: Gap Lock
- `X`: Next-Key Lock (Record + Gap)
- `S`: Shared Next-Key Lock

`PHYSICAL RECORD`의 hex 값이 실제 인덱스 키 값이다. `8000000000000005`는 id = 5를 의미한다(big-endian unsigned 64-bit, MSB 반전된 형태).

### 데드락 로그에서 원인 쿼리 찾기

데드락 로그에 나온 쿼리는 마지막으로 실행한 쿼리일 뿐이다. 그 이전에 잡은 락이 실제 원인인 경우가 많다.

로그에 `UPDATE orders SET status='DONE' WHERE id=10`이 나와 있어도, 그 트랜잭션이 그 전에 `SELECT * FROM payments WHERE order_id=5 FOR UPDATE`로 payments 테이블에 락을 잡았을 수 있다. 실제 원인은 payments 테이블의 락 순서에 있는 것이다.

`HOLDS THE LOCK(S)` 섹션에 있는 인덱스와 키 값을 보고 애플리케이션 코드에서 해당 행을 잠그는 쿼리를 역으로 찾는다. 그 쿼리가 어디서 호출되는지까지 추적해야 데드락의 전체 그림이 나온다.

## Gap Lock으로 인한 INSERT 데드락 패턴

Gap Lock 충돌로 생기는 데드락은 패턴이 정해져 있다. 두 트랜잭션이 같은 범위에 Gap Lock을 걸고(이건 충돌하지 않아 둘 다 성공), 이후 두 트랜잭션이 각자 그 범위에 INSERT를 시도한다. INSERT는 Gap Lock과 충돌하기 때문에 서로 상대방의 Gap Lock 해제를 기다리다가 데드락이 된다.

```sql
-- 트랜잭션 A
BEGIN;
SELECT * FROM orders WHERE id = 7 FOR UPDATE;
-- id = 7이 없으면 gap lock on (5, 10) 획득
-- (이 시점에 트랜잭션 B도 같은 쿼리 실행, 같은 gap lock 획득)
INSERT INTO orders (id, amount) VALUES (7, 500);
-- 트랜잭션 B의 gap lock 때문에 대기

-- 트랜잭션 B
BEGIN;
SELECT * FROM orders WHERE id = 7 FOR UPDATE;  -- gap lock on (5, 10) 획득
INSERT INTO orders (id, amount) VALUES (7, 500);
-- 트랜잭션 A의 gap lock 때문에 대기 → 데드락
```

이 패턴은 INSERT 전에 존재 여부를 확인하는 코드에서 자주 발생한다. `INSERT ... ON DUPLICATE KEY UPDATE`나 `INSERT IGNORE`로 대체하면 데드락을 피할 수 있다.

## 락 타임아웃 vs 데드락

두 가지를 구분한다.

**락 타임아웃**은 한 트랜잭션이 다른 트랜잭션이 잡은 락을 기다리다가 `innodb_lock_wait_timeout` 초를 넘기면 발생한다. 교착 상태가 아니라 단순 대기다. MySQL이 자동으로 감지하지 않고, 타임아웃이 지나면 오류를 돌려준다.

```
ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction
```

타임아웃이 발생하면 해당 SQL 문만 롤백된다. 트랜잭션 자체는 아직 열려 있다. 명시적으로 `ROLLBACK`을 해야 트랜잭션이 닫힌다. 이걸 모르면 트랜잭션이 열린 채로 락을 계속 들고 있는 상황이 생긴다.

**데드락**은 두 트랜잭션이 서로를 기다리는 상황이다. MySQL이 이 상태를 자동으로 감지하고, 더 적은 락을 가진 트랜잭션을 희생 트랜잭션(victim)으로 선택해 롤백한다. 롤백된 쪽은 다음 오류를 받는다:

```
ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction
```

데드락은 트랜잭션 전체가 롤백된다. 애플리케이션에서 이 오류를 받으면 트랜잭션 전체를 재시도해야 한다.

```java
@Retryable(
    retryFor = {DeadlockLoserDataAccessException.class},
    maxAttempts = 3,
    backoff = @Backoff(delay = 50, multiplier = 2)
)
@Transactional
public void processOrder(Long orderId) {
    // ...
}
```

Spring에서는 `DeadlockLoserDataAccessException`으로 변환된다. `@Retryable`과 `@Transactional`을 같이 쓰면 재시도마다 새 트랜잭션이 시작된다.

## 데드락 재현 환경 구성

운영에서 발생한 데드락을 재현하려면 두 개의 MySQL 세션을 열고 순서를 맞춰야 한다.

```sql
-- 세션 1 터미널
SET SESSION innodb_lock_wait_timeout = 10;
START TRANSACTION;
SELECT * FROM orders WHERE id = 5 FOR UPDATE;
-- 여기서 멈추고 세션 2로 이동

-- 세션 2 터미널
START TRANSACTION;
SELECT * FROM orders WHERE id = 10 FOR UPDATE;
UPDATE orders SET status='DONE' WHERE id = 5;  -- 세션 1이 잡은 id=5 대기

-- 다시 세션 1
UPDATE orders SET status='DONE' WHERE id = 10;  -- 세션 2가 잡은 id=10 대기 → 데드락
```

재현 중 performance_schema를 별도 세션에서 조회하면 락 흐름을 실시간으로 볼 수 있다.

---

데드락은 반드시 재현 가능한 환경에서 분석해야 한다. 운영 데드락 로그만 보고 원인을 추정하는 건 절반만 아는 것이다. 실제로 트랜잭션 순서를 재현해서 performance_schema로 락 흐름을 확인하는 편이 정확하다.

---
이 문서는 [트랜잭션과 동시성 허브](../../_hub/트랜잭션과_동시성.md)의 일부입니다.
