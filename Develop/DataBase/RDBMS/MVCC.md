---
title: MVCC (Multi-Version Concurrency Control)
tags: [database, rdbms, postgresql, mysql]
updated: 2026-08-23
---

# MVCC (Multi-Version Concurrency Control)

트랜잭션들이 서로 블로킹 없이 동시에 실행될 수 있도록, 각 트랜잭션에게 **일관된 스냅샷**을 제공하는 동시성 제어 기법이다.
쓰기가 읽기를 막지 않고, 읽기가 쓰기를 막지 않는다.

---

## 핵심 아이디어

행(row)을 제자리에서 수정하지 않는다.
대신 **새 버전**을 만들고 이전 버전을 유지한다.
각 트랜잭션은 자신이 시작된 시점의 버전만 본다.

```
txn_id=100이 행을 UPDATE하면:
┌─────────────────────────────────────────┐
│ xmin=100 | xmax=∞  | data="new value"  │  ← 새 버전
│ xmin=50  | xmax=100 | data="old value" │  ← 이전 버전 (아직 삭제 안 됨)
└─────────────────────────────────────────┘
```

- `xmin`: 이 버전을 만든 트랜잭션 ID
- `xmax`: 이 버전을 삭제(무효화)한 트랜잭션 ID, 없으면 ∞

---

## PostgreSQL의 구현

### Heap Tuple Header

PostgreSQL은 각 행에 숨겨진 시스템 컬럼을 붙인다:

| 컬럼 | 의미 |
|------|------|
| `ctid` | 현재 물리적 위치 (page, offset) |
| `xmin` | INSERT한 트랜잭션 ID |
| `xmax` | DELETE/UPDATE한 트랜잭션 ID |
| `cmin` | command ID (같은 트랜잭션 내 순서) |

```sql
-- 숨겨진 컬럼 직접 조회
SELECT ctid, xmin, xmax, * FROM orders WHERE id = 1;
```

### 스냅샷(Snapshot)

트랜잭션이 시작될 때 PostgreSQL은 스냅샷을 찍는다:

```
snapshot = {
  xmin: 현재 실행 중인 가장 오래된 txn ID,
  xmax: 다음에 발급될 txn ID,
  xip:  현재 진행 중인 txn ID 목록
}
```

한 행이 **보이는 조건**:
1. `tuple.xmin < snapshot.xmax` → 스냅샷 이전에 시작됨
2. `tuple.xmin`이 `xip`에 없음 → 이미 커밋됨
3. `tuple.xmax == 0` OR `tuple.xmax >= snapshot.xmax` → 아직 삭제 안 됨

### Isolation Level별 스냅샷 시점

```
READ COMMITTED   → 쿼리마다 스냅샷 갱신
REPEATABLE READ  → 트랜잭션 시작 시 스냅샷 고정
SERIALIZABLE     → SSI(Serializable Snapshot Isolation) 추가 적용
```

---

## MySQL InnoDB의 구현

InnoDB는 행을 클러스터드 인덱스에 저장하고, 변경된 이전 값을 **Undo Log**에 기록한다.

```
현재 행 (클러스터드 인덱스)
    │
    └──→ Undo Log 체인 (이전 버전들)
              prev_ver_1 → prev_ver_2 → ...
```

읽기 뷰(Read View)가 필요한 버전에 도달할 때까지 Undo Log를 역추적한다.

---

## Dead Tuple과 VACUUM

MVCC의 부작용: 이전 버전 행들이 테이블에 쌓인다(**dead tuple**).

```
VACUUM ANALYZE orders;
```

VACUUM이 하는 일:
1. 더 이상 어떤 스냅샷에도 필요 없는 old tuple 제거
2. 회수된 공간을 FSM(Free Space Map)에 등록
3. 통계 정보 갱신 (ANALYZE 옵션)

`autovacuum`이 자동으로 돌지만, 대량 UPDATE/DELETE 후에는 수동으로 실행하는 게 낫다.

### 팽창(Bloat) 확인

```sql
SELECT
  relname,
  n_dead_tup,
  n_live_tup,
  round(n_dead_tup::numeric / nullif(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_ratio
FROM pg_stat_user_tables
ORDER BY dead_ratio DESC;
```

---

## MVCC vs 잠금 기반 동시성

| 구분 | MVCC | 잠금(Lock) |
|------|------|------------|
| 읽기-쓰기 충돌 | 없음 | 읽기가 쓰기 대기 |
| 메모리/스토리지 | 버전 저장 오버헤드 | 잠금 테이블만 |
| Phantom Read | Snapshot으로 방지 | 레인지 락 필요 |
| Write-Write 충돌 | 여전히 잠금 필요 | 잠금으로 직렬화 |

---

## 흔한 함정

### Transaction ID Wraparound

PostgreSQL 트랜잭션 ID는 32비트 (`2^32 ≈ 42억`).
순환하면 미래 트랜잭션이 과거처럼 보인다 → **데이터 유실 위험**.

```sql
-- xid 소비 현황 확인
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

`age(datfrozenxid) > 1.5억` 이면 VACUUM FREEZE를 능동적으로 실행해야 한다.

### Long-Running Transaction

오래 실행되는 트랜잭션은 그 시점 이후의 dead tuple 전부를 VACUUM이 지우지 못하게 막는다.

```sql
-- 오래된 트랜잭션 찾기
SELECT pid, now() - xact_start AS duration, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY duration DESC;
```

---

## 요약

- MVCC는 버전 관리로 읽기-쓰기 충돌을 없앤다.
- PostgreSQL은 행 헤더(`xmin/xmax`)로, InnoDB는 Undo Log 체인으로 구현한다.
- Dead tuple이 쌓이면 VACUUM이 회수한다. Long transaction이 이를 방해한다.
- Transaction ID Wraparound는 적극적인 VACUUM FREEZE로 예방한다.
