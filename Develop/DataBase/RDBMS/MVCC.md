---
title: MVCC (Multi-Version Concurrency Control)
tags: [database, rdbms, postgresql, mysql, performance]
updated: 2026-09-12
---

# MVCC (Multi-Version Concurrency Control)

트랜잭션이 서로 블로킹 없이 실행되도록 각 트랜잭션에 일관된 스냅샷을 제공하는 동시성 제어 기법이다.
쓰기가 읽기를 막지 않고, 읽기가 쓰기를 막지 않는다.

---

## 행 버전 관리

행을 제자리에서 수정하지 않는다. 새 버전을 만들고 이전 버전을 그대로 둔다.
각 트랜잭션은 자신이 시작된 시점의 버전만 본다.

```
txn_id=100이 행을 UPDATE하면:
┌─────────────────────────────────────────┐
│ xmin=100 | xmax=∞  | data="new value"  │  ← 새 버전
│ xmin=50  | xmax=100 | data="old value" │  ← 이전 버전 (아직 삭제 안 됨)
└─────────────────────────────────────────┘
```

- `xmin`: 이 버전을 만든 트랜잭션 ID
- `xmax`: 이 버전을 삭제(무효화)한 트랜잭션 ID. 없으면 0 또는 특수값

```sql
-- 숨겨진 시스템 컬럼 직접 조회
SELECT ctid, xmin, xmax, * FROM orders WHERE id = 1;
```

트랜잭션이 시작할 때 PostgreSQL은 스냅샷을 찍는다:

```
snapshot = {
  xmin: 현재 실행 중인 가장 오래된 txn ID,
  xmax: 다음에 발급될 txn ID,
  xip:  현재 진행 중인 txn ID 목록
}
```

한 행이 보이려면 세 조건을 모두 만족해야 한다:

1. `tuple.xmin < snapshot.xmax` — 스냅샷 이전에 시작됨
2. `tuple.xmin`이 `xip`에 없음 — 이미 커밋됨
3. `tuple.xmax == 0` OR `tuple.xmax >= snapshot.xmax` — 아직 삭제 안 됨

격리 수준별로 스냅샷을 찍는 시점이 다르다:

```
READ COMMITTED   → 쿼리마다 스냅샷 갱신
REPEATABLE READ  → 트랜잭션 시작 시 스냅샷 고정
SERIALIZABLE     → SSI(Serializable Snapshot Isolation) 추가 적용
```

---

## HOT Update — 인덱스를 건드리지 않는 조건

PostgreSQL UPDATE는 기본적으로 새 행 버전을 만들고 해당 행의 모든 인덱스에 새 항목을 추가한다.
인덱스 수가 10개인 테이블에서 UPDATE 하나가 인덱스 페이지 10개를 건드린다.

HOT(Heap Only Tuple) Update는 두 조건이 모두 충족될 때 인덱스 갱신을 건너뛴다:

1. 변경된 컬럼이 인덱스 키에 포함되지 않는다
2. 이전 버전과 새 버전이 **같은 페이지** 안에 있다

조건 2가 핵심이다. 같은 페이지 안에 여유 공간이 없으면 새 버전이 다른 페이지로 넘어가고 HOT가 깨진다.

`fillfactor`는 페이지를 채우는 비율을 제한해서 HOT용 공간을 확보한다:

```sql
-- 테이블 생성 시
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    status TEXT,
    updated_at TIMESTAMPTZ
) WITH (fillfactor = 70);

-- 기존 테이블에 적용 후 즉시 반영하려면 VACUUM FULL이 필요
ALTER TABLE events SET (fillfactor = 70);
VACUUM FULL events;
```

`fillfactor = 70`이면 페이지의 30%를 UPDATE 여분으로 남긴다.
쓰기가 잦은 테이블에 적용하면 인덱스 팽창이 눈에 띄게 줄었다.
읽기 위주 테이블에는 기본값(100)을 그대로 두는 게 낫다 — 낮추면 같은 데이터가 더 많은 페이지에 나뉘어 풀스캔 비용이 올라간다.

HOT 발생률 확인:

```sql
SELECT relname,
       n_tup_upd,
       n_tup_hot_upd,
       round(n_tup_hot_upd::numeric / nullif(n_tup_upd, 0) * 100, 1) AS hot_ratio
FROM pg_stat_user_tables
WHERE n_tup_upd > 0
ORDER BY hot_ratio ASC;
```

`hot_ratio`가 낮은 테이블이 fillfactor 조정 후보다. 조건 1(인덱스 컬럼 변경 여부)도 같이 확인한다.

---

## Visibility Map과 Index-Only Scan

PostgreSQL은 테이블마다 Visibility Map(VM)을 별도 파일(`_vm` 접미사)로 관리한다.
페이지당 2비트다:

- **all-visible 비트**: 페이지의 모든 튜플이 현재 실행 중인 모든 트랜잭션에 보임
- **all-frozen 비트**: 페이지의 모든 튜플이 FREEZE 처리됨 (XID Wraparound 위험 없음)

all-visible 비트가 Index-Only Scan 성능에 직접 영향을 준다.

Index-Only Scan은 인덱스 항목만으로 결과를 돌려줄 수 있을 때 사용한다.
MVCC 때문에 "인덱스에 있다고 실제로 보이는 행인지" 확인이 필요한데, all-visible 비트가 켜진 페이지는 이 확인을 건너뛴다 — heap fetch가 필요 없다.

```
all-visible = ON  → Index-Only Scan이 heap 접근 없이 바로 결과 반환
all-visible = OFF → heap fetch 발생 (MVCC 가시성 재확인)
```

테이블에 UPDATE/DELETE가 발생하면 해당 페이지의 all-visible 비트가 꺼진다.
VACUUM이 dead tuple을 정리하면서 비트를 다시 켠다.
VACUUM이 밀리면 all-visible 페이지 비율이 떨어지고, Index-Only Scan이 실제로는 heap도 읽게 된다.

EXPLAIN에서 `Heap Fetches: N`이 크면 VACUUM이 밀린 것이다:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM orders WHERE created_at > '2026-01-01';
-- "Heap Fetches: 48302" 같이 나오면 VM 비트가 꺼진 페이지가 많다는 뜻
```

```sql
-- VM 파일 크기로 간접 확인
SELECT relname,
       pg_size_pretty(pg_relation_size(oid)) AS table_size,
       pg_size_pretty(pg_relation_size(oid, 'vm')) AS vm_size
FROM pg_class
WHERE relkind = 'r'
ORDER BY pg_relation_size(oid) DESC
LIMIT 10;
```

---

## Write Skew — MVCC가 막지 못하는 이상 현상

MVCC는 Dirty Read, Non-Repeatable Read, Phantom Read를 막는다. Write Skew는 막지 못한다.

### 전형적인 시나리오

당직 의사 시스템. 규칙: 항상 최소 1명이 당직이어야 한다.

```
의사 A (txn 1)                    의사 B (txn 2)
  BEGIN                              BEGIN
  SELECT COUNT(*) FROM duty
  WHERE on_duty = true;
  -- 결과: 2 (A, B 모두 당직)
                                     SELECT COUNT(*) FROM duty
                                     WHERE on_duty = true;
                                     -- 결과: 2 (동일 스냅샷)

  -- 2명 이상이니 나는 빠질 수 있다
  UPDATE duty SET on_duty = false
  WHERE doctor_id = 'A';
                                     -- 2명 이상이니 나는 빠질 수 있다
                                     UPDATE duty SET on_duty = false
                                     WHERE doctor_id = 'B';
  COMMIT                             COMMIT

  -- 결과: 당직 의사 0명
```

왜 막히지 않는가. 두 트랜잭션이 서로 다른 행을 수정했다.
같은 행에 동시 쓰기가 없으니 MVCC 관점에서는 충돌이 없다.
각자 스냅샷에서 조건을 확인하고 별개 행을 썼을 뿐이다.

REPEATABLE READ도 마찬가지다. 스냅샷 고정만 더 강하게 걸릴 뿐, 두 트랜잭션이 서로 쓴 행을 못 읽는 것은 동일하다.

### SSI가 Write Skew를 잡는 방법

PostgreSQL SERIALIZABLE은 SSI(Serializable Snapshot Isolation)를 쓴다.
Oracle과 MySQL InnoDB의 SERIALIZABLE은 S-Lock을 잡아 사실상 직렬 실행이 되지만, PostgreSQL SSI는 스냅샷 기반으로 동작하면서 위험한 의존 사이클만 잡는다.

핵심은 **read-write 의존 추적**이다.

```
T1이 특정 행 집합을 읽음   →  T1 --(rw)--> T2 (T2가 그 범위에 쓸 예정)
T2가 특정 행 집합을 읽음   →  T2 --(rw)--> T1 (T1이 그 범위에 쓸 예정)
```

T1 → T2 → T1 사이클이 형성되면 직렬 순서가 존재하지 않는다.
PostgreSQL은 이 사이클을 감지하면 한 트랜잭션을 중단시킨다:

```
ERROR: could not serialize access due to read/write dependencies among transactions
DETAIL:  Reason code: Canceled on identification as a pivot, during commit attempt.
```

당직 시스템에서의 흐름:

1. T1이 `duty` 테이블을 읽을 때 SIReadLock 획득
2. T2가 `duty` 테이블을 읽을 때 SIReadLock 획득
3. T1이 `doctor_id='A'` 행을 쓸 때 T2의 읽기 범위와 충돌 → T2 --(rw)--> T1 등록
4. T2가 `doctor_id='B'` 행을 쓸 때 T1의 읽기 범위와 충돌 → T1 --(rw)--> T2 등록
5. COMMIT 시점에 사이클 검출 → 하나 롤백

```sql
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT COUNT(*) FROM duty WHERE on_duty = true;
UPDATE duty SET on_duty = false WHERE doctor_id = 'A';
COMMIT;
-- 경쟁 트랜잭션이 사이클을 형성하면 serialization failure 발생
-- 애플리케이션에서 재시도 처리가 필요하다
```

SSI의 비용: 트랜잭션마다 predicate lock 정보를 메모리에 유지해야 한다.
동시 트랜잭션이 많을수록 `max_pred_locks_per_transaction` 메모리 소비가 늘어난다.
처리량이 높은 시스템에서 전체 테이블에 SERIALIZABLE을 걸기보다, 충돌 가능한 지점만 `SELECT FOR UPDATE`로 명시 잠금하는 게 나은 경우가 많다.

---

## VACUUM 심화

### autovacuum 트리거 조건과 튜닝

autovacuum은 아래 조건을 만족할 때 실행된다:

```
n_dead_tup > autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * n_live_tup
```

기본값:

```
autovacuum_vacuum_threshold    = 50
autovacuum_vacuum_scale_factor = 0.2   (live 행의 20%)
```

`orders` 테이블에 live 행 1,000만 개가 있으면 dead tuple이 200만 개 쌓여야 autovacuum이 뜬다.
UPDATE가 잦은 테이블은 낮춰야 bloat가 안 쌓인다:

```sql
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_vacuum_threshold    = 1000
);
```

`vacuum_cost_delay`는 VACUUM이 I/O를 얼마나 양보하는지 제어한다:

```
vacuum_cost_delay = 0     → VACUUM이 I/O를 최대한 씀. 쿼리 응답에 영향
vacuum_cost_delay = 2ms   → PostgreSQL 14 이후 기본값
vacuum_cost_delay = 20ms  → 피크 타임에 VACUUM을 많이 양보
```

테이블별로 다르게 줄 수 있다:

```sql
ALTER TABLE orders SET (autovacuum_vacuum_cost_delay = 10);
```

autovacuum 현황 확인:

```sql
SELECT schemaname, relname,
       last_autovacuum, last_autoanalyze,
       n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_ratio DESC;
```

### autovacuum_freeze_max_age와 FREEZE

PostgreSQL XID는 32비트다. 순환 전에 오래된 XID를 FROZEN 상태로 바꿔야 한다.
`autovacuum_freeze_max_age`(기본 200,000,000)에 도달한 테이블은 autovacuum이 강제로 FREEZE를 실행한다.

```sql
-- 각 테이블의 XID 소비량 확인
SELECT relname,
       age(relfrozenxid) AS xid_age,
       pg_size_pretty(pg_total_relation_size(oid)) AS size
FROM pg_class
WHERE relkind = 'r'
ORDER BY xid_age DESC
LIMIT 10;
```

`age(relfrozenxid) > 150,000,000` 수준에서 수동 FREEZE를 미리 실행하는 게 안전하다:

```sql
VACUUM FREEZE ANALYZE orders;
```

Visibility Map의 all-frozen 비트가 켜진 페이지는 이후 FREEZE VACUUM에서 건너뛴다.
처음 한 번 FREEZE 처리 후에는 비용이 급감한다.

### table bloat 실전 대응

`pg_stat_user_tables`의 dead_ratio는 추정값이다. 실제 bloat는 pgstattuple로 정확하게 잰다:

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;

SELECT * FROM pgstattuple('orders');
/*
 table_len          │ 1073741824
 tuple_count        │    5000000
 tuple_len          │  800000000
 tuple_percent      │      74.50
 dead_tuple_count   │    1200000
 dead_tuple_len     │  200000000
 dead_tuple_percent │      18.63
 free_space         │   73741824
 free_percent       │       6.87
*/
```

`dead_tuple_percent`가 20%를 넘기면 VACUUM 주기가 맞지 않는 것이다.
`free_percent`가 높은데 dead_tuple은 적다면 VACUUM은 됐지만 OS에 공간이 반환되지 않은 상태다. 이때 VACUUM FULL 또는 pg_repack이 필요하다.

VACUUM FULL은 `AccessExclusiveLock`을 잡아 운영 중 사용하기 어렵다. pg_repack은 이 잠금 없이 테이블을 재구성한다:

```bash
# 설치
apt install postgresql-14-repack

# 운영 중에도 실행 가능
pg_repack -t orders -U postgres -d mydb
```

pg_bloat_check는 여러 테이블을 한 번에 점검한다:

```bash
# https://github.com/keithf4/pg_bloat_check
python pg_bloat_check.py -c "host=localhost dbname=mydb" --min_wasted_size 1073741824
```

wasted 1GB 이상 테이블만 리포트하는 식으로 노이즈를 줄인다.

---

## MySQL InnoDB의 구현과 purge thread

InnoDB는 변경된 이전 값을 Undo Log에 기록한다.

```
현재 행 (클러스터드 인덱스)
    │  DB_TRX_ID, DB_ROLL_PTR
    └──→ Undo Log 체인
              prev_ver_1 → prev_ver_2 → ...
```

읽기 뷰(Read View)가 필요한 버전에 도달할 때까지 Undo Log를 역추적한다.
체인이 길어질수록 쿼리가 느려진다.

### purge thread

커밋이 끝난 트랜잭션의 Undo Log는 즉시 삭제하지 않는다.
다른 트랜잭션이 아직 그 버전을 읽을 수 있어서다.
purge thread가 "더 이상 어떤 읽기 뷰도 필요로 하지 않는" Undo Log를 정리한다.

purge 진행 현황:

```sql
-- History List Length가 높으면 purge가 밀린 것이다
SHOW ENGINE INNODB STATUS\G
-- 출력 중: History list length N

-- 또는
SELECT name, count
FROM information_schema.innodb_metrics
WHERE name = 'trx_rseg_history_len';
```

`history_list_length`가 수만 단위로 올라가면 쿼리 응답 시간이 함께 오른다.
오래 열린 트랜잭션이 거의 항상 원인이다.

purge thread 수는 쓰기 부하에 따라 조정한다:

```ini
# my.cnf
innodb_purge_threads = 4   # 기본 4, 쓰기가 많으면 8까지
```

### innodb_undo_log_truncate

MySQL 8.0에서 undo tablespace 크기를 자동으로 줄이는 기능이다.

```ini
# my.cnf
innodb_undo_log_truncate              = ON    # 기본 ON (8.0.2+)
innodb_max_undo_log_size              = 1G    # 이 크기 초과 시 truncate 트리거
innodb_purge_rseg_truncate_frequency  = 128   # purge 루프 128번마다 truncate 시도
```

대량 배치 작업 후 undo 파일이 10GB로 불어난 적이 있다. `innodb_max_undo_log_size = 2G`로 낮게 설정하면 purge 후 truncate가 더 자주 발생해 파일이 줄어든다. truncate 자체가 I/O 부하를 유발하니 피크 타임에는 피한다.

undo tablespace 상태 확인:

```sql
SELECT tablespace_name,
       file_name,
       round(file_size / 1024 / 1024) AS size_mb,
       state
FROM information_schema.innodb_tablespaces
WHERE tablespace_name LIKE 'innodb_undo%';
```

---

## Long-Running Transaction과 Wraparound

오래 열린 트랜잭션은 그 시점 이후의 dead tuple 전부를 VACUUM(또는 InnoDB purge)이 지우지 못하게 막는다.
그 트랜잭션의 읽기 뷰가 옛 버전을 아직 필요로 할 수 있어서다. PostgreSQL이든 InnoDB든 동일하다.

```sql
-- PostgreSQL — 오래된 트랜잭션 찾기
SELECT pid,
       now() - xact_start AS duration,
       state,
       query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND state != 'idle'
ORDER BY duration DESC;
```

5분 이상 열린 트랜잭션이 있으면 VACUUM이 막혀 bloat가 쌓이기 시작한다.
`statement_timeout`만으로는 IDLE 상태로 잠긴 커넥션을 끊지 못한다. `idle_in_transaction_session_timeout`을 별도로 설정해야 한다:

```sql
-- postgresql.conf
idle_in_transaction_session_timeout = '5min'
```

### Transaction ID Wraparound

PostgreSQL XID는 32비트(`2^32 ≈ 42억`). 순환하면 미래 트랜잭션이 과거처럼 보인다 — 데이터 유실 위험이다.

```sql
-- xid 소비 현황
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

`age > 150,000,000`이면 즉시 VACUUM FREEZE를 실행한다.
모니터링에 이 지표를 넣어 두면 임박하기 전에 알 수 있다.

```sql
VACUUM FREEZE ANALYZE orders;
```

---

## MVCC vs 잠금 기반 동시성

| 구분 | MVCC | 잠금(Lock) |
|------|------|------------|
| 읽기-쓰기 충돌 | 없음 | 읽기가 쓰기 대기 |
| 스토리지 오버헤드 | 버전 저장 | 잠금 테이블만 |
| Phantom Read | 스냅샷으로 방지 | 레인지 락 필요 |
| Write Skew | REPEATABLE READ까지는 발생 | SERIALIZABLE Lock으로 방지 |
| Write-Write 충돌 | 여전히 잠금 필요 | 잠금으로 직렬화 |
