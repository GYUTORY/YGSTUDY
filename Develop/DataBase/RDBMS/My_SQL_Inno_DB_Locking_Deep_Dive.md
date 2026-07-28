---
title: MySQL InnoDB 락 심화
tags: [MySQL, InnoDB, Lock, Deadlock, Transaction, Database, RDBMS]
updated: 2026-07-28
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

status 컬럼에 인덱스를 추가하면 InnoDB가 해당 인덱스를 타고 실제로 필요한 레코드만 스캔한다. 락 범위가 극적으로 줄어든다.

## 범위 쿼리에서의 Next-Key Lock 과도 잠금

날짜나 상태 기반 범위 쿼리는 예상보다 훨씬 넓은 범위를 잠근다.

```sql
-- created_at 컬럼에 인덱스가 있어도 범위가 크면
SELECT * FROM orders 
WHERE created_at >= '2024-01-01' AND created_at < '2024-02-01' 
FOR UPDATE;
```

이 쿼리는 조건에 맞는 레코드뿐 아니라 범위 내 모든 gap에도 락을 건다. 1월 15일에 새 행을 INSERT하면 대기 상태가 된다.

배치 작업에서 이런 쿼리를 자주 쓰면 일반 트랜잭션의 INSERT가 줄줄이 대기 상태가 된다. 데드락이 없어도 배치와 서비스가 서로 발목을 잡는 상황이 된다.

이 경우 `FOR UPDATE` 없이 SELECT 후 애플리케이션 레벨에서 처리하거나, 배치를 작은 단위로 쪼개서 커밋 주기를 짧게 가져가는 방법을 쓴다.

## 락 범위 확인: performance_schema

MySQL 8.0부터는 `performance_schema.data_locks`로 현재 걸려 있는 락을 직접 볼 수 있다.

```sql
-- 현재 활성화된 락 조회
SELECT 
    engine_lock_id,
    thread_id,
    object_name,
    index_name,
    lock_type,
    lock_mode,
    lock_status,
    lock_data
FROM performance_schema.data_locks
WHERE object_name = 'orders';
```

`lock_data` 컬럼이 핵심이다. Record Lock이면 인덱스 레코드의 키 값이 표시되고, Gap Lock이면 `supremum pseudo-record`처럼 gap의 경계가 표시된다.

락 대기 관계는 `data_lock_waits`로 확인한다.

```sql
-- 누가 누구를 기다리는지 조회
SELECT 
    requesting_engine_lock_id,
    blocking_engine_lock_id,
    requesting_thread_id,
    blocking_thread_id
FROM performance_schema.data_lock_waits;
```

두 쿼리를 JOIN하면 어떤 트랜잭션이 어떤 인덱스의 어느 범위를 잠그고 있어서 다른 트랜잭션이 대기 중인지 전부 볼 수 있다.

```sql
-- 락 대기 상황 종합 조회
SELECT
    r.trx_id AS waiting_trx_id,
    r.trx_mysql_thread_id AS waiting_thread,
    r.trx_query AS waiting_query,
    b.trx_id AS blocking_trx_id,
    b.trx_mysql_thread_id AS blocking_thread,
    b.trx_query AS blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;
```

MySQL 5.7까지는 `information_schema.innodb_locks`와 `innodb_lock_waits`를 썼다. 8.0부터는 performance_schema로 이전됐다.

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

데드락 로그에서 실행 중이던 쿼리와 락을 들고 있는 인덱스, 기다리는 인덱스를 연결하면 "이 두 쿼리가 이 순서로 실행됐을 때 서로를 기다렸다"는 그림이 나온다.

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

---

데드락은 반드시 재현 가능한 환경에서 분석해야 한다. 운영 데드락 로그만 보고 원인을 추정하는 건 절반만 아는 것이다. 실제로 트랜잭션 순서를 재현해서 performance_schema로 락 흐름을 확인하는 편이 정확하다.
