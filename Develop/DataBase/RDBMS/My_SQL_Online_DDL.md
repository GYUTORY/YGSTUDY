---
title: MySQL Online DDL
tags: [mysql, ddl, online-ddl, innodb, alter-table, migration, mdl, aurora, performance-schema]
updated: 2026-08-06
---

# MySQL Online DDL

MySQL 5.6부터 `ALTER TABLE`에 `ALGORITHM`과 `LOCK` 옵션이 추가됐다. 이 두 옵션의 조합으로 DDL 실행 중 테이블 접근을 얼마나 허용할지 결정한다.

```sql
ALTER TABLE orders
  ADD COLUMN memo VARCHAR(500) NULL,
  ALGORITHM=INSTANT,
  LOCK=NONE;
```

옵션을 명시하지 않으면 MySQL이 해당 변경에 가장 빠른 알고리즘을 자동 선택한다. 문제는 자동 선택 시 어떤 알고리즘이 선택될지 예측하기 어렵다. `ALGORITHM=INSTANT`를 명시해두면 INSTANT가 불가능한 변경일 때 에러를 내서 의도치 않게 COPY 알고리즘으로 수십 분짜리 DDL이 실행되는 사고를 막는다.

---

## 알고리즘 세 가지

### INSTANT

메타데이터만 바꾼다. 실제 행 데이터를 건드리지 않으므로 수십 밀리초면 끝난다. 테이블 크기와 무관하다.

내부적으로는 테이블의 `instant add column count`라는 메타데이터를 올리고, 컬럼 기본값을 데이터 딕셔너리에 기록한다. 행을 읽을 때 이 메타데이터를 참조해서 컬럼이 없는 구행(old row)에는 기본값을 반환한다.

**8.0.12 이전**: 테이블 끝에 컬럼을 추가하는 경우만 INSTANT를 지원한다. `AFTER` 절로 중간에 끼워 넣거나, 기존 컬럼 앞에 추가하는 건 안 된다.

**8.0.29 이상**: 임의 위치에 컬럼을 추가해도 INSTANT가 된다. AFTER나 FIRST 절을 써도 동작한다.

```sql
-- 8.0.12+ 가능 (끝에 추가)
ALTER TABLE orders ADD COLUMN note TEXT NULL, ALGORITHM=INSTANT;

-- 8.0.12 이전 불가 (중간 삽입), 8.0.29+ 가능
ALTER TABLE orders ADD COLUMN note TEXT NULL AFTER user_id, ALGORITHM=INSTANT;
```

INSTANT 컬럼이 누적된 테이블은 `OPTIMIZE TABLE`을 주기적으로 실행해서 내부를 정리하는 게 좋다. 구행/신행이 섞인 상태가 오래 지속되면 행 파싱 비용이 늘어난다.

### INPLACE

테이블 파일을 통째로 복사하지는 않지만, 인덱스를 재구성하거나 내부 데이터를 정렬하는 작업은 수행한다. 인덱스 추가가 대표적인 사례다.

DDL 시작 시 잠깐 MDL(Metadata Lock)을 잡고, 본 작업 중에는 동시 DML을 허용하고, 완료 직전에 다시 MDL을 잡는 구조다. 작업 시간은 인덱스 크기와 테이블 크기에 비례한다.

```sql
-- 인덱스 추가: INPLACE로 처리됨
ALTER TABLE orders
  ADD INDEX idx_status_created (status, created_at),
  ALGORITHM=INPLACE,
  LOCK=NONE;
```

### COPY

임시 테이블을 하나 더 만들고, 원본 데이터를 새 스키마에 맞게 전부 복사한다. 복사가 완료되면 원본과 임시 테이블을 교체한다.

가장 느리고, 디스크 공간을 원본 테이블의 약 2배 소비한다. 수천만 행 테이블에서 COPY 알고리즘이 돌면 디스크 풀로 이어지는 경우가 있다. 미리 여유 공간을 확인해야 한다.

```sql
-- 디스크 여유 공간 먼저 확인
SELECT table_schema, table_name,
       ROUND(data_length / 1024 / 1024, 2) AS data_mb,
       ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables
WHERE table_name = 'orders';
```

---

## DDL 종류별 알고리즘 지원 매트릭스

| DDL 작업 | INSTANT | INPLACE | COPY | 동시 DML |
|---|---|---|---|---|
| 컬럼 추가 (끝) | 8.0.12+ | O | O | INSTANT/INPLACE 모두 허용 |
| 컬럼 추가 (임의 위치) | 8.0.29+ | O | O | INSTANT/INPLACE 모두 허용 |
| 컬럼 삭제 | X | O | O | INPLACE: 허용 |
| 컬럼 이름 변경 | X | O | O | INPLACE: 허용 |
| 컬럼 타입 변경 (VARCHAR 확장) | X | 일부만 | O | INPLACE: 허용 |
| 컬럼 타입 변경 (VARCHAR 축소/다른 타입) | X | X | O | COPY: 차단 |
| NOT NULL → NULL 허용 | X | O | O | INPLACE: 허용 |
| NULL → NOT NULL | X | O (데이터 검증 필요) | O | INPLACE: 허용 |
| DEFAULT 값 변경 | O | O | O | 허용 |
| 컬럼 순서 변경 | X | X | O | COPY: 차단 |
| PRIMARY KEY 추가 | X | O | O | INPLACE: 허용 |
| PRIMARY KEY 삭제 | X | X | O | COPY: 차단 |
| 일반 인덱스 추가 | X | O | O | INPLACE: 허용 |
| FULLTEXT 인덱스 추가 (첫 번째) | X | O | O | INPLACE: 차단 |
| SPATIAL 인덱스 추가 | X | O | O | INPLACE: 차단 |
| 인덱스 삭제 | X | O | O | INPLACE: 허용 |
| ENUM 값 추가 (끝에) | O | O | O | 허용 |
| ENUM 값 추가 (중간) | X | X | O | COPY: 차단 |
| ROW_FORMAT 변경 | X | O | O | INPLACE: 일부 제한 |
| CHARACTER SET 변경 | X | X | O | COPY: 차단 |
| FOREIGN KEY 추가 | X | O | O | INPLACE: 허용 |
| FOREIGN KEY 삭제 | X | O | O | INPLACE: 허용 |

VARCHAR 확장은 `ROW_FORMAT=DYNAMIC` 기준으로 현재 바이트 수가 1바이트 표현 범위(255바이트 이하)에서 2바이트 범위(256 이상)로 넘어가지 않는 경우에만 INPLACE가 가능하다. `VARCHAR(200)`에서 `VARCHAR(250)`은 INPLACE지만, `VARCHAR(200)`에서 `VARCHAR(300)`은 COPY다.

---

## DYNAMIC row format 요건

INSTANT와 INPLACE 알고리즘 상당수가 `ROW_FORMAT=DYNAMIC`(또는 COMPRESSED)을 전제로 한다. MySQL 5.7.9 이후 InnoDB 기본값이 DYNAMIC으로 바뀌었다. 그 이전에 만들어진 테이블은 COMPACT일 수 있다.

```sql
-- 현재 row format 확인
SELECT table_name, row_format
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'orders';

-- COMPACT라면 먼저 변환 (테이블 재작성 발생)
ALTER TABLE orders ROW_FORMAT=DYNAMIC, ALGORITHM=COPY;
```

한번 DYNAMIC으로 바꾸면 이후 INSTANT DDL을 쓸 수 있다. 변환 자체는 COPY 알고리즘이라 시간이 걸리지만, 이후 컬럼 추가를 매번 밀리초 만에 끝낼 수 있다면 충분히 감내할 만하다.

---

## MDL이 Online DDL 대기에 미치는 영향

Online DDL이라고 해서 MDL을 전혀 안 잡는 게 아니다. 다음 세 시점에 MDL을 잡는다.

```
1. DDL 시작 시: 공유 MDL 획득 → 다른 DDL 차단, 일반 DML은 허용
2. 본 작업 구간: MDL 해제 → DML 완전 허용 (INPLACE/INSTANT)
3. 완료 직전: 배타 MDL 획득 → DML 포함 모든 접근 차단 (테이블 교체)
```

3번 구간이 문제다. 배타 MDL을 획득하려면 현재 실행 중인 모든 트랜잭션이 끝나길 기다려야 한다. 롱 트랜잭션이 있으면 DDL이 이 시점에서 멈춘다.

더 심각한 문제는 대기 중인 DDL이 뒤따라오는 SELECT까지 모두 대기 상태로 만든다는 점이다.

```
상황:
  트랜잭션 A: 30초짜리 집계 쿼리 실행 중
  → ALTER TABLE 실행 (배타 MDL 대기)
  → 이후 들어오는 모든 SELECT, INSERT가 줄줄이 대기
  → 30초 후 트랜잭션 A 종료 → DDL 획득 → 수백 ms 만에 완료
  → 쌓인 쿼리들 일시에 실행
```

배포 시 DDL을 실행하기 전에 `SHOW PROCESSLIST`나 `INFORMATION_SCHEMA.INNODB_TRX`로 롱 트랜잭션이 없는지 확인해야 한다.

```sql
-- 실행 중인 트랜잭션 확인
SELECT trx_id, trx_started, trx_state,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS sec,
       trx_query
FROM information_schema.innodb_trx
ORDER BY trx_started;

-- 10초 이상 실행 중인 프로세스
SELECT id, user, db, command, time, state, info
FROM information_schema.processlist
WHERE time > 10
  AND command != 'Sleep'
ORDER BY time DESC;
```

DDL에 `lock_wait_timeout`을 별도로 설정하는 방법도 있다. 기본값은 31536000(1년)이라 사실상 무한 대기다.

```sql
SET SESSION lock_wait_timeout = 30;
ALTER TABLE orders ADD COLUMN memo TEXT NULL, ALGORITHM=INSTANT;
-- MDL 획득에 30초 초과 시 에러 반환 (대기 쿼리들도 즉시 해제)
```

---

## performance_schema로 진행 상황 모니터링

INPLACE DDL처럼 시간이 걸리는 작업은 진행 상황을 확인할 수 있다. `performance_schema.events_stages_current`를 쓴다.

```sql
-- Online DDL 진행 상황 확인
SELECT
  t.processlist_id,
  t.processlist_info,
  e.event_name,
  e.work_completed,
  e.work_estimated,
  ROUND(e.work_completed / e.work_estimated * 100, 1) AS progress_pct,
  FORMAT_PICO_TIME(e.timer_wait) AS elapsed
FROM performance_schema.events_stages_current e
JOIN performance_schema.threads t
  ON e.thread_id = t.thread_id
WHERE e.event_name LIKE '%alter%'
   OR e.event_name LIKE '%online%'
   OR t.processlist_info LIKE '%ALTER%';
```

모니터링이 동작하려면 performance_schema 설정이 켜져 있어야 한다.

```sql
-- 필요한 instruments 활성화 (세션 한정)
UPDATE performance_schema.setup_instruments
SET enabled = 'YES', timed = 'YES'
WHERE name LIKE 'stage/innodb/alter%';

UPDATE performance_schema.setup_consumers
SET enabled = 'YES'
WHERE name = 'events_stages_current';
```

`work_completed / work_estimated` 비율이 진행률이다. 다만 `work_estimated`는 작업 초반에 갱신되고 이후 고정되므로, 실제 남은 시간을 정확히 예측하지 못하는 경우가 있다.

DDL을 실행하는 세션이 별도라면 다른 세션에서 위 쿼리를 주기적으로 실행해서 진행 상황을 확인할 수 있다. `processlist_info`에서 DDL 쿼리가 보이면 아직 실행 중이다.

---

## 동시 DML 허용 범위

알고리즘과 작업 단계별로 동시 DML 허용 범위가 다르다.

**INSTANT:**
- DDL 실행 전 구간: 정상 DML 허용
- MDL 획득 후: 수 밀리초 동안 DML 대기 (실사용에서 체감 거의 없음)
- 완료 후: 정상 복귀

**INPLACE 인덱스 추가:**
- DDL 시작 후 본 작업 구간: SELECT, INSERT, UPDATE, DELETE 모두 허용
- 단, DDL이 실행되는 동안 INSERT/UPDATE는 내부 버퍼(row log buffer)에 변경사항을 기록해두고, 인덱스 구성 완료 후 이 버퍼를 반영한다
- 버퍼가 꽉 차면 DDL이 중단됨. `innodb_online_alter_log_max_size`로 조절 (기본 128MB)

```sql
-- row log buffer 크기 조절
SET GLOBAL innodb_online_alter_log_max_size = 268435456; -- 256MB
```

대용량 테이블에서 인덱스를 추가하는 중에 트래픽이 많으면 버퍼가 넘칠 수 있다. DDL이 실패하면 처음부터 다시 해야 하므로, 트래픽이 낮은 시간대를 골라야 한다.

**COPY:**
- 복사 중 SELECT: 원본 테이블에서 읽으므로 허용
- 복사 중 INSERT/UPDATE/DELETE: 차단. 쓰기 락이 걸린다
- 테이블이 클수록 서비스에 미치는 영향이 크다. COPY가 불가피하면 pt-online-schema-change나 gh-ost를 쓰는 게 낫다

---

## Aurora MySQL과 일반 MySQL의 동작 차이

Aurora MySQL은 스토리지 레이어가 다르다. 이 차이가 Online DDL 동작에도 영향을 준다.

**INSTANT DDL:**
Aurora MySQL 3.x(MySQL 8.0 호환)에서 INSTANT를 지원하지만, 일반 MySQL과 동작이 완전히 같지는 않다. Aurora는 분산 스토리지를 쓰기 때문에 INSTANT 컬럼 메타데이터 전파 방식이 다르다.

Aurora MySQL 2.x(MySQL 5.7 호환)에서는 INSTANT를 지원하지 않는다.

```sql
-- Aurora 버전 확인
SELECT @@aurora_version, @@version;
```

**INPLACE 성능:**
Aurora는 스토리지 I/O 구조가 달라서 인덱스 재구성 성능이 일반 MySQL과 다를 수 있다. 특히 Aurora I/O 최적화 클러스터에서는 INPLACE 인덱스 추가 속도가 체감상 빠른 경우가 있다.

**리더 인스턴스 영향:**
일반 MySQL 복제에서는 DDL이 Primary에서 실행된 후 Replica로 binlog를 통해 전달된다. Aurora는 스토리지를 공유하므로, Primary에서 INSTANT DDL이 완료되면 Reader 인스턴스에는 거의 즉시 반영된다. 그러나 Reader에서 DDL 실행 후 메타데이터 캐시가 갱신되는 데 약간의 지연이 있을 수 있다.

**pt-online-schema-change / gh-ost:**
Aurora에서 이 도구들을 쓸 때 주의사항이 있다. Aurora의 binlog는 기본 비활성 상태다. gh-ost는 binlog 읽기 권한이 필요하므로, Aurora에서 gh-ost를 쓰려면 binlog를 활성화해야 한다.

```sql
-- Aurora에서 binlog 확인
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
```

Aurora는 자체 Online DDL 기능(fast DDL)을 제공하는데, Aurora 파라미터 그룹에서 `aurora_lab_mode`를 활성화해야 한다. 일반 MySQL의 Online DDL과 다른 경로로 구현됐다.

---

## 실무 사용 패턴

컬럼을 추가할 때 항상 INSTANT부터 시도하고, 안 되면 INPLACE, 그것도 안 되면 외부 도구를 쓰는 순서로 결정한다.

```sql
-- 1순위: INSTANT 시도
ALTER TABLE orders ADD COLUMN note TEXT NULL, ALGORITHM=INSTANT;
-- 에러 발생 시 INSTANT 불가 확인

-- 2순위: INPLACE
ALTER TABLE orders ADD COLUMN note TEXT NULL, ALGORITHM=INPLACE, LOCK=NONE;
-- 에러 발생 시 INPLACE 불가 확인 → gh-ost 또는 pt-osc 사용 검토

-- 지원 여부를 미리 확인 (에러만 반환하고 실제 변경 없음)
-- MySQL은 이런 dry-run 기능을 제공하지 않으므로, 개발 환경에서 먼저 테스트
```

대용량 테이블(1억 행 이상)에서 INPLACE로 인덱스를 추가하는 경우, 예상 소요 시간을 미리 계산하기 어렵다. 개발 환경에서 같은 크기의 데이터를 복제해서 먼저 실행해보는 게 가장 확실하다.

```sql
-- DDL 실행 중 취소 (세션 종료)
KILL QUERY {process_id};
-- INPLACE 작업을 중간에 종료하면 내부 정리 과정에서 잠깐 락이 발생할 수 있다
```
