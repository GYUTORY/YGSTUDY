---
title: 격리 수준별 이상 현상 재현
tags: [database, mysql, postgresql, rdbms]
updated: 2026-07-30
---

# 격리 수준별 이상 현상 재현

이론으로만 접하면 어느 순간 헷갈리는 게 격리 수준이다. "Phantom Read는 REPEATABLE READ에서 발생한다"는 정의는 알지만, 실제로 재현해보려 하면 MySQL InnoDB에서는 일반 SELECT로는 잘 안 된다. MVCC가 자체적으로 막아버리기 때문이다.

아래 예제는 세션이 두 개 필요하다. 타임라인 순서대로 실행한다. MySQL 기준으로 먼저 다루고, PostgreSQL에서 동작이 다른 경우에만 별도로 언급한다.

## 테스트 환경 준비

```sql
-- 예제 테이블 (MySQL/PostgreSQL 모두 동일)
CREATE TABLE inventory (
    id INT PRIMARY KEY,
    product_name VARCHAR(100),
    stock INT
);

CREATE TABLE accounts (
    id INT PRIMARY KEY,
    balance INT
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,  -- PostgreSQL: SERIAL
    amount INT
);

INSERT INTO inventory VALUES (1, '노트북', 100);
INSERT INTO accounts VALUES (1, 10000);
INSERT INTO orders VALUES (1, 500), (2, 1500), (3, 2000);
```

## Dirty Read — READ UNCOMMITTED

아직 커밋되지 않은 다른 트랜잭션의 변경값을 읽는 현상이다. 읽은 데이터가 이후 롤백되면 실제로는 존재한 적 없는 값을 기반으로 로직을 수행한 게 된다.

실무에서 READ UNCOMMITTED를 쓰는 경우는 거의 없다. 대략적인 집계 카운트가 필요하고 정합성보다 속도가 중요한 상황에서 간혹 쓰이는 정도다. 결제, 재고, 잔액을 다루는 곳에는 절대 쓰면 안 된다.

### 재현 (MySQL)

```sql
-- Session A: 격리 수준 설정
SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
```

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | |
| 2 | | `START TRANSACTION;` |
| 3 | | `UPDATE inventory SET stock = 0 WHERE id = 1;` (커밋 안 함) |
| 4 | `SELECT stock FROM inventory WHERE id = 1;` → **0** | |
| 5 | -- stock=0이므로 "재고 없음"으로 처리 | |
| 6 | | `ROLLBACK;` (재고는 100으로 복구) |
| 7 | Session A는 이미 0을 읽고 로직을 진행했음 | |

Session A가 읽은 0은 DB에 확정된 적 없는 값이다. Session B가 롤백했으므로 재고는 원래대로 100이지만, Session A는 "재고 소진"으로 주문을 거절하거나 잘못된 처리를 했을 수 있다.

PostgreSQL에서는 READ UNCOMMITTED로 설정해도 내부적으로 READ COMMITTED처럼 동작한다. PostgreSQL MVCC 구조상 커밋되지 않은 행 버전을 읽는 경로가 없어서, 설정값이 무시되는 것과 동일한 효과다.

## Non-Repeatable Read — READ COMMITTED

같은 트랜잭션 안에서 같은 행을 두 번 SELECT했는데 값이 달라지는 현상이다. 두 번의 SELECT 사이에 다른 트랜잭션이 UPDATE하고 커밋했기 때문이다.

READ COMMITTED는 PostgreSQL의 기본 격리 수준이다. 스냅샷을 트랜잭션 단위로 찍는 게 아니라, SQL 문장마다 최신 커밋 상태를 읽는다. 같은 트랜잭션 내에서도 시간이 지나면 다른 값을 읽을 수 있다.

### 재현 (MySQL / PostgreSQL 동일)

```sql
-- Session A (MySQL)
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | |
| 2 | `SELECT balance FROM accounts WHERE id = 1;` → **10000** | |
| 3 | | `UPDATE accounts SET balance = 3000 WHERE id = 1; COMMIT;` |
| 4 | `SELECT balance FROM accounts WHERE id = 1;` → **3000** | |
| 5 | `COMMIT;` | |

같은 트랜잭션 내에서 읽은 값이 바뀌었다. Session A가 2번 단계에서 잔액이 10000이라고 확인하고 출금 가능 여부를 판단했는데, 실제 UPDATE 시점에는 이미 3000으로 바뀐 상태다.

잔액 확인 → 잔액 차감 흐름이 두 SELECT로 분리된 경우 이 문제에 걸린다. 두 SELECT 사이의 시간 간격이 아무리 짧아도 OS 스케줄러가 컨텍스트 스위치를 하면 충분히 발생한다.

### SELECT FOR UPDATE로 방어

격리 수준을 올리지 않아도 읽기 시점에 락을 걸면 Non-Repeatable Read를 막을 수 있다.

```sql
-- Session A
START TRANSACTION;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
-- 이 시점부터 Session B는 id=1 행을 수정할 수 없고 대기 상태가 됨

-- 잔액 확인 후 차감
UPDATE accounts SET balance = balance - 2000 WHERE id = 1;
COMMIT;
```

`FOR UPDATE`는 해당 행에 X Lock을 걸어서, 락을 해제하기 전까지 다른 트랜잭션이 그 행을 수정하지 못하게 막는다.

## Phantom Read — REPEATABLE READ

범위 조건으로 SELECT했을 때, 같은 트랜잭션 내 두 번째 조회에서 행 개수가 달라지는 현상이다. 다른 트랜잭션이 그 사이 INSERT/DELETE하고 커밋했기 때문이다.

REPEATABLE READ는 행의 값이 바뀌는 Non-Repeatable Read는 막지만, 범위 내 행 개수 변화는 원칙적으로 막지 않는다. MySQL InnoDB는 여기서 예외다.

### 일반 SELECT에서는 발생하지 않는다 (MySQL InnoDB)

InnoDB REPEATABLE READ는 트랜잭션 시작 시점의 스냅샷을 고정해서 유지한다. 같은 트랜잭션 안에서는 외부 변화가 보이지 않는다.

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | |
| 2 | `SELECT * FROM orders WHERE amount > 1000;` → **2건** (id=2, 3) | |
| 3 | | `INSERT INTO orders (amount) VALUES (1800); COMMIT;` |
| 4 | `SELECT * FROM orders WHERE amount > 1000;` → **2건** (id=2, 3만 보임) | |

4번 단계에서 id=4인 새 행이 보이지 않는다. InnoDB가 2번 단계의 스냅샷을 유지하기 때문이다. 교과서 정의대로라면 Phantom Read가 발생해야 하지만, InnoDB는 의도적으로 더 강한 보장을 제공한다.

### SELECT FOR UPDATE에서 발생한다

`FOR UPDATE`나 `FOR SHARE`는 현재 최신 데이터를 읽는다. 스냅샷이 아닌 현재 상태를 읽기 때문에 Phantom Read가 발생한다.

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | |
| 2 | `SELECT * FROM orders WHERE amount > 1000 FOR UPDATE;` → **2건** | |
| 3 | | `INSERT INTO orders (amount) VALUES (1800);` → **대기** (Gap Lock) |
| 4 | Session A `COMMIT;` | |
| 5 | | 대기 해제, INSERT 완료, `COMMIT;` |
| 6 | Session A 새 트랜잭션: `SELECT * FROM orders WHERE amount > 1000 FOR UPDATE;` → **3건** | |

6번 단계에서 처음과 다른 행 수가 반환된다. 이게 Phantom Read다.

단 3번에서 Session B가 대기 상태가 됐다는 점에 주목해야 한다. InnoDB가 `amount > 1000` 범위에 Gap Lock을 걸어서, 같은 트랜잭션 내 두 번의 `FOR UPDATE` 사이에는 Phantom Read 자체를 막는다. Phantom Read는 다른 트랜잭션이 끼어드는 시점, 즉 Session A가 트랜잭션을 끝낸 뒤 새 트랜잭션에서 같은 조회를 할 때 보인다.

### PostgreSQL REPEATABLE READ

PostgreSQL의 REPEATABLE READ는 트랜잭션 시작 시점 스냅샷을 트랜잭션 내내 유지한다. 일반 SELECT와 `FOR UPDATE` 모두 같은 스냅샷을 기준으로 읽기 때문에, MySQL InnoDB보다 일관된 동작을 보인다.

```sql
-- PostgreSQL
BEGIN;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT * FROM orders WHERE amount > 1000;  -- 2건
-- 다른 세션에서 INSERT + COMMIT 발생
SELECT * FROM orders WHERE amount > 1000;  -- 여전히 2건 (스냅샷 유지)
SELECT * FROM orders WHERE amount > 1000 FOR UPDATE;  -- 현재 상태 반영, 3건
COMMIT;
```

PostgreSQL에서 `FOR UPDATE`는 잠금을 위해 현재 버전으로 전환된다. 이 시점에 다른 세션이 이미 커밋한 행이 보인다.

## REPEATABLE READ 기본값에서 발생하는 예상치 못한 동작

MySQL InnoDB 기본값이 REPEATABLE READ다. "Phantom Read는 거의 안 생긴다"는 인식 때문에 방심하기 쉬운데, 실무에서 당황스러운 상황이 몇 가지 있다.

### Lost Update — 갱신 손실

두 트랜잭션이 같은 값을 읽고 각자 수정해서 커밋하면, 먼저 커밋한 트랜잭션의 변경이 사라진다. REPEATABLE READ가 해결해주지 않는 문제다.

```sql
-- 초기 재고: 10
```

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | `START TRANSACTION;` |
| 2 | `SELECT stock FROM inventory WHERE id = 1;` → **10** | `SELECT stock FROM inventory WHERE id = 1;` → **10** |
| 3 | `UPDATE inventory SET stock = 9 WHERE id = 1;` | |
| 4 | `COMMIT;` | |
| 5 | | `UPDATE inventory SET stock = 9 WHERE id = 1;` |
| 6 | | `COMMIT;` |

최종 재고가 9다. 두 트랜잭션이 각각 1개씩 차감했으므로 8이어야 하는데 9가 됐다. Session B가 Session A의 커밋을 모르고 자기가 읽은 10 기준으로 9를 덮어썼기 때문이다.

```sql
-- 방법 1: SELECT FOR UPDATE로 락 획득 후 차감
START TRANSACTION;
SELECT stock FROM inventory WHERE id = 1 FOR UPDATE;
UPDATE inventory SET stock = stock - 1 WHERE id = 1;
COMMIT;

-- 방법 2: 원자적 UPDATE (락 없이 처리 가능한 경우)
UPDATE inventory SET stock = stock - 1 WHERE id = 1 AND stock > 0;
-- affected rows가 0이면 재고 부족으로 처리
```

방법 2는 SELECT를 아예 없애고 UPDATE 하나로 처리하기 때문에 Lost Update가 발생하지 않는다. 재고 차감처럼 단순한 경우에는 이 방식이 락 오버헤드도 없고 코드도 단순해진다.

### Write Skew — 쓰기 왜곡

두 트랜잭션이 서로 다른 행을 수정하는데, 각자가 읽은 조건을 기반으로 한 결정이 전체적으로 제약을 위반하는 경우다.

당직 시스템 예시다. 최소 1명 이상 당직을 서야 하는 제약이 있다. 현재 당직자가 2명일 때, 두 사람이 각자 "1명 이상 있으니 나는 빠져도 된다"고 판단하고 동시에 취소하면 0명이 된다.

```sql
CREATE TABLE doctors (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    on_call BOOLEAN
);
INSERT INTO doctors VALUES (1, 'Alice', TRUE), (2, 'Bob', TRUE);
```

| 순서 | Session A (Alice) | Session B (Bob) |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | `START TRANSACTION;` |
| 2 | `SELECT COUNT(*) FROM doctors WHERE on_call = TRUE;` → **2** | `SELECT COUNT(*) FROM doctors WHERE on_call = TRUE;` → **2** |
| 3 | -- 2명이니 한 명 빠져도 됨 | -- 2명이니 한 명 빠져도 됨 |
| 4 | `UPDATE doctors SET on_call = FALSE WHERE id = 1;` | |
| 5 | `COMMIT;` | |
| 6 | | `UPDATE doctors SET on_call = FALSE WHERE id = 2;` |
| 7 | | `COMMIT;` |

당직자가 0명이 됐다. 각 트랜잭션은 자기 판단 시점에 조건을 만족했지만, 전체 결과는 제약을 어긴다.

Write Skew는 SERIALIZABLE이어야 완전히 막힌다. REPEATABLE READ에서 막으려면 조건 조회에도 `FOR UPDATE`를 걸어야 한다.

```sql
-- 해결: 범위 조건 조회에 FOR UPDATE를 건다
START TRANSACTION;
SELECT COUNT(*) FROM doctors WHERE on_call = TRUE FOR UPDATE;
-- 다른 세션의 doctors 행 수정이 블로킹됨
UPDATE doctors SET on_call = FALSE WHERE id = 1;
COMMIT;
```

### MVCC 스냅샷과 INSERT 충돌

REPEATABLE READ 스냅샷으로 읽을 때는 없어 보이지만, 실제 INSERT 시점에 유니크 제약 위반이 발생하는 경우다.

| 순서 | Session A | Session B |
|------|-----------|-----------|
| 1 | `START TRANSACTION;` | |
| 2 | `SELECT * FROM orders WHERE id = 4;` → **없음** | |
| 3 | | `INSERT INTO orders VALUES (4, 1800); COMMIT;` |
| 4 | `INSERT INTO orders VALUES (4, 900);` → **Duplicate key 오류** | |

Session A의 스냅샷에는 id=4가 없어서 "없으니 INSERT해도 된다"고 판단했지만, 실제 DB에는 Session B가 커밋한 id=4가 있다. 쓰기는 항상 현재 상태에 반영되기 때문에 유니크 제약이 잡힌다.

JPA에서 `findById()` → 없으면 `save()`하는 패턴이 이 상황에 취약하다. "없으면 생성"류의 로직은 유니크 제약 위반을 예외로 잡아서 처리하거나, `INSERT ... ON DUPLICATE KEY UPDATE`로 원자적으로 처리해야 한다.

```java
// 취약한 패턴
Optional<Order> existing = orderRepository.findByOrderNo(orderNo);
if (existing.isEmpty()) {
    orderRepository.save(new Order(orderNo));  // 동시 요청이면 Duplicate key 발생
}

// 안전한 패턴: 예외를 잡아서 처리
try {
    orderRepository.save(new Order(orderNo));
} catch (DataIntegrityViolationException e) {
    // 다른 트랜잭션이 이미 생성함. 기존 건을 조회해서 반환
    return orderRepository.findByOrderNo(orderNo).orElseThrow();
}
```

예외 처리 방식이 깔끔하지 않아 보여도, `findById` → `save` 패턴보다 동시성 상황에서 훨씬 안전하다.
