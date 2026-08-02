---
title: "Cloud SQL 성능 분석"
tags: [GCP, Cloud SQL, mysql, postgresql, Query Insights, performance_schema, pg_stat_statements, explain, 튜닝]
updated: 2026-07-26
---

# Cloud SQL 성능 분석

쿼리가 갑자기 느려졌을 때 원인을 찾는 순서가 없으면 시간을 낭비한다. DB 재시작, 인스턴스 업그레이드, 인덱스 추가를 아무 근거 없이 시도하다가 정작 원인은 통계 정보 만료나 커넥션 폭증이었던 경우가 많다. 여기서는 Cloud SQL에서 슬로우 쿼리를 발견하고 원인을 특정하는 순서를 정리한다.

## 슬로우 쿼리 원인 찾는 순서

쿼리가 느려졌다는 신고가 들어오면 아래 순서로 확인한다. 각 단계에서 원인이 특정되면 그 이후는 건너뛴다.

**1단계: Cloud Monitoring 지표 확인**

CPU가 90% 이상이고 디스크 IOPS도 한계에 가깝다면 플래그 튜닝이나 쿼리 최적화보다 인스턴스 업그레이드가 먼저다. 반대로 자원 사용률이 낮은데 쿼리가 느리다면 잠금 대기나 플랜 변경을 의심한다.

**2단계: Query Insights에서 슬로우 쿼리 식별**

어떤 쿼리가 문제인지 특정한다. 실행 횟수가 적어도 총 지연 시간이 높은 쿼리를 먼저 본다.

**3단계: performance_schema / pg_stat_statements로 세부 확인**

잠금 대기, 임시 테이블 사용, 정렬 디스크 스필 여부를 확인한다.

**4단계: EXPLAIN ANALYZE로 플랜 분석**

실행 계획이 바뀌었는지, 인덱스를 제대로 타는지 확인한다.

**5단계: 플래그 튜닝 또는 인덱스 추가**

원인에 맞는 조치를 취한다. 원인 없이 플래그를 건드리지 않는다.

## Cloud Monitoring 핵심 지표

Cloud SQL 인스턴스 상태를 보는 지표는 많지만 실무에서 먼저 확인하는 것은 다섯 가지다.

**CPU 사용률 (`database/cpu/utilization`)**

지속적으로 80% 이상이면 인스턴스 업그레이드를 검토한다. 순간 피크는 괜찮지만 평상시 기저치가 높으면 쿼리 최적화로는 한계가 있다. MySQL은 단일 쿼리가 멀티코어를 못 쓰는 경우가 많아서 vCPU 수를 늘려도 단일 쿼리 성능은 개선되지 않는다. 그런 경우 쿼리를 쪼개거나 읽기 레플리카를 쓰는 게 낫다.

**메모리 사용률 (`database/memory/utilization`)**

메모리 사용률보다 `innodb_buffer_pool_size`(MySQL) 또는 `shared_buffers`(PostgreSQL)가 실제로 얼마나 채워져 있는지가 더 중요하다. 버퍼 풀 히트율이 낮으면 디스크 읽기가 많아진다. Cloud Monitoring에서 직접 히트율을 보려면 `database/mysql/innodb_buffer_pool_pages_total`과 `database/mysql/innodb_buffer_pool_dirty_pages` 지표를 함께 봐야 한다.

**디스크 읽기/쓰기 IOPS (`database/disk/read_ops_count`, `database/disk/write_ops_count`)**

SSD 스토리지 기준으로 Cloud SQL의 IOPS는 디스크 용량에 비례한다. 100GB면 읽기 3000 IOPS, 쓰기 3000 IOPS가 한계다. 이 한계에 붙으면 쿼리가 빠르게 나빠진다. 디스크를 늘리거나 `innodb_io_capacity`를 올려서 플러시를 앞당기는 방법 둘 다 시도해볼 수 있다.

```bash
# 현재 인스턴스의 IOPS 한계 계산
# 공식: provisioned_IOPS = disk_size_gb * 30 (최대 60000)
gcloud sql instances describe prod-mysql \
  --format="value(settings.dataDiskSizeGb)"
```

**복제 지연 (`database/replication/replica_lag`)**

읽기 레플리카를 쓰는 경우 이 지표가 올라가면 레플리카에서 읽는 데이터가 최신이 아니다. 복제 지연의 원인은 대부분 바이너리 로그 이벤트 처리 속도가 프라이머리 쓰기 속도를 못 따라가는 경우다. 레플리카에서 느린 쿼리가 돌고 있으면 복제 SQL 스레드가 블로킹되어 지연이 급격히 올라간다.

**활성 커넥션 수 (`database/postgresql/num_backends` / MySQL은 `database/network/connections`)**

커넥션 수가 `max_connections` 한계에 가까우면 새 커넥션이 대기하거나 실패한다. Cloud SQL은 메모리 기준으로 `max_connections` 기본값이 설정되는데, PostgreSQL은 커넥션당 메모리 사용량이 커서 이 값을 무턱대고 올리면 OOM이 난다. 커넥션 폭증이 문제라면 플래그 조정보다 애플리케이션 레벨 커넥션 풀링(PgBouncer)이 근본 해결책이다.

## Query Insights

Cloud SQL의 Query Insights는 슬로우 쿼리를 찾는 가장 빠른 방법이다. 별도 설정 없이 콘솔에서 활성화하면 바로 쓸 수 있다. 내부적으로 MySQL은 `performance_schema`, PostgreSQL은 `pg_stat_statements`를 활용한다.

콘솔에서 Cloud SQL → 인스턴스 선택 → Query Insights 탭으로 들어가면 된다.

주요 지표는 세 가지다.

- **평균 실행 시간**: 가장 오래 걸리는 쿼리를 찾는 기본 지표
- **총 실행 시간 (Total time)**: 빈도 × 평균 시간. 실행이 잦은 쿼리가 전체 부하를 얼마나 차지하는지 보인다
- **반환 행 수**: 많이 반환하는데 느린 쿼리는 인덱스 문제일 가능성이 높다

쿼리 텍스트는 파라미터가 치환된 형태로 보인다. `SELECT * FROM users WHERE id = $1` 형태다. 특정 파라미터 값과 함께 실행된 플랜을 보고 싶다면 실제 DB에 접속해서 EXPLAIN을 돌려야 한다.

Query Insights에서 제공하는 실행 계획 샘플도 있는데, 이건 실제 실행 중에 캡처된 플랜이라 재현이 어려운 경우에도 확인할 수 있어서 유용하다.

## MySQL performance_schema

performance_schema는 MySQL 내부 동작을 계측하는 내장 시스템이다. Cloud SQL에서는 기본으로 활성화되어 있다.

슬로우 쿼리가 있을 때 잠금 대기 여부부터 확인한다.

```sql
-- 현재 잠금 대기 중인 쿼리
SELECT
  r.trx_id AS waiting_trx,
  r.trx_mysql_thread_id AS waiting_thread,
  r.trx_query AS waiting_query,
  b.trx_id AS blocking_trx,
  b.trx_mysql_thread_id AS blocking_thread,
  b.trx_query AS blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id;
```

쿼리 수준에서 어디서 시간이 쓰이는지 보려면 events_statements 테이블을 쓴다.

```sql
-- 특정 쿼리의 단계별 시간 (statements_with_runtimes_in_95th_percentile 뷰)
SELECT
  digest_text,
  count_star AS exec_count,
  ROUND(avg_timer_wait / 1e9, 2) AS avg_ms,
  ROUND(sum_timer_wait / 1e9, 2) AS total_ms,
  sum_rows_examined,
  sum_rows_sent,
  ROUND(sum_rows_examined / sum_rows_sent, 0) AS rows_examined_per_row_sent
FROM performance_schema.events_statements_summary_by_digest
WHERE schema_name = 'your_db'
ORDER BY sum_timer_wait DESC
LIMIT 20;
```

`rows_examined_per_row_sent`가 높다면 풀 스캔이나 불필요한 행을 많이 읽는 것이다. 이 값이 100 이상이면 인덱스를 의심한다.

임시 테이블을 디스크에 만드는 쿼리를 찾을 때는 아래를 쓴다.

```sql
SELECT
  digest_text,
  sum_created_tmp_disk_tables,
  sum_created_tmp_tables
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_created_tmp_disk_tables > 0
ORDER BY sum_created_tmp_disk_tables DESC
LIMIT 10;
```

임시 테이블이 디스크로 넘어가는 건 `tmp_table_size`나 `max_heap_table_size`가 부족하거나, GROUP BY나 ORDER BY에서 인덱스를 못 쓰는 경우다.

## PostgreSQL pg_stat_statements

pg_stat_statements는 PostgreSQL의 쿼리 통계 확장이다. Cloud SQL PostgreSQL에서는 기본 활성화되어 있다.

```sql
-- 총 실행 시간 기준 상위 쿼리
SELECT
  query,
  calls,
  ROUND(mean_exec_time::numeric, 2) AS avg_ms,
  ROUND(total_exec_time::numeric, 2) AS total_ms,
  rows,
  ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS cache_hit_pct
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

`cache_hit_pct`가 낮은 쿼리는 디스크 읽기가 많다. `shared_buffers`를 늘리거나 쿼리 자체가 너무 많은 블록을 읽는 게 원인이다.

쿼리 통계를 리셋하면 현재 시점부터 다시 쌓인다. 배포 전후 비교할 때 쓸 수 있다.

```sql
SELECT pg_stat_statements_reset();
```

버퍼 히트율이 낮은 테이블을 찾을 때는 pg_statio_user_tables를 쓴다.

```sql
SELECT
  schemaname,
  relname AS table_name,
  heap_blks_read,
  heap_blks_hit,
  ROUND(100.0 * heap_blks_hit / NULLIF(heap_blks_read + heap_blks_hit, 0), 1) AS hit_pct
FROM pg_statio_user_tables
WHERE heap_blks_read + heap_blks_hit > 0
ORDER BY heap_blks_read DESC
LIMIT 20;
```

## EXPLAIN ANALYZE 결과 해석

실행 계획은 실제 DB에 접속해서 확인한다. Cloud SQL Auth Proxy를 통해 접속하거나, Private IP를 쓴다.

```sql
-- MySQL
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 1234 AND status = 'pending';

-- PostgreSQL (버퍼 히트 정보 포함)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE user_id = 1234 AND status = 'pending';
```

MySQL EXPLAIN ANALYZE 결과에서 확인할 부분은 두 가지다.

첫째, `type` 컬럼. `ALL`이면 풀 스캔이다. `ref`, `range`, `eq_ref`는 인덱스를 쓰는 것이고, `index`는 인덱스 풀 스캔으로 풀 테이블 스캔보다는 낫지만 여전히 문제다.

둘째, `rows` vs 실제 반환 행. `rows` 추정치가 실제와 크게 차이 나면 통계 정보가 오래된 것이다.

```sql
-- MySQL 통계 갱신
ANALYZE TABLE orders;

-- PostgreSQL 통계 갱신
ANALYZE orders;
-- 또는 전체
ANALYZE;
```

PostgreSQL EXPLAIN ANALYZE에서는 추가로 확인할 게 있다.

```
Seq Scan on orders  (cost=0.00..45231.00 rows=1000 width=248)
                    (actual time=0.043..892.123 rows=987 loops=1)
  Filter: ((user_id = 1234) AND (status = 'pending'))
  Rows Removed by Filter: 2045013
  Buffers: shared hit=1023 read=21456
```

`Rows Removed by Filter` 숫자가 크면 인덱스 없이 행을 읽고 버린 것이다. `Buffers: read`가 많으면 디스크에서 읽은 것이다. 같은 쿼리를 두 번 실행했을 때 두 번째에 `hit`가 높아지면 캐시에 올라간 것이다.

실행 계획이 바뀐 게 의심될 때는 `pg_stat_plans`나 쿼리 힌트로 특정 플랜을 강제하는 방법도 있지만, Cloud SQL에서는 힌트 문법이 엔진별로 다르고 제약이 있다. PostgreSQL은 `pg_hint_plan` 확장을 써야 한다.

## 데이터베이스 플래그 튜닝

Cloud SQL에서 파라미터 변경은 플래그(flag)로만 한다. 일부 플래그는 변경 즉시 적용되고, 일부는 인스턴스 재시작이 필요하다. 콘솔에서 플래그 변경 시 재시작 필요 여부를 보여준다.

### MySQL 핵심 플래그

**innodb_buffer_pool_size**

InnoDB 버퍼 풀 크기다. 가장 중요한 파라미터다. 메모리의 70~80%를 할당하는 게 일반적이다. Cloud SQL에서는 기본값이 인스턴스 메모리의 약 75% 수준으로 설정된다. 디스크 읽기가 많고 메모리 여유가 있다면 올린다.

```bash
gcloud sql instances patch prod-mysql \
  --database-flags=innodb_buffer_pool_size=12884901888  # 12GB (bytes 단위)
```

값은 bytes 단위다. 16GB 인스턴스에서 12GB를 할당하려면 12 * 1024 * 1024 * 1024 = 12884901888이다.

**innodb_io_capacity / innodb_io_capacity_max**

InnoDB가 백그라운드에서 디스크 쓰기(플러시)에 쓸 수 있는 IOPS 한도다. 기본값이 200으로 낮다. SSD를 쓰는 경우 2000~4000으로 올려야 더티 페이지가 쌓이지 않는다. 이 값이 낮으면 체크포인트 시점에 쓰기 스파이크가 발생한다.

```bash
gcloud sql instances patch prod-mysql \
  --database-flags=innodb_io_capacity=2000,innodb_io_capacity_max=4000
```

**slow_query_log / long_query_time**

슬로우 쿼리 로그를 Cloud SQL에서 활성화하면 Cloud Logging으로 수집된다. Query Insights와 중복되지만, 파라미터 값까지 로깅된다는 차이가 있다.

```bash
gcloud sql instances patch prod-mysql \
  --database-flags=slow_query_log=on,long_query_time=1
```

### PostgreSQL 핵심 플래그

**shared_buffers**

PostgreSQL의 버퍼 캐시다. Cloud SQL PostgreSQL의 기본값은 인스턴스 메모리의 약 25%다. 전용 DB 서버라면 25%가 이론적으로 맞지만, Cloud SQL은 OS 페이지 캐시도 활용하므로 올려도 크게 나빠지지 않는다. 단, 너무 올리면 메모리 압박이 생긴다. 변경 시 재시작이 필요하다.

```bash
gcloud sql instances patch prod-postgres \
  --database-flags=shared_buffers=4096  # MB 단위 아님, 8kB 블록 수
  # 4096 * 8kB = 32MB — 이 값은 예시. 실제로는 훨씬 크게 설정
```

Cloud SQL PostgreSQL에서 `shared_buffers`는 8kB 블록 수가 아닌 MB 단위 문자열로 설정 가능하다.

```bash
gcloud sql instances patch prod-postgres \
  --database-flags=shared_buffers=4096MB
```

**work_mem**

정렬이나 해시 조인에 사용하는 메모리다. 기본값 4MB는 작다. 복잡한 쿼리가 많다면 올린다. 단, 이 값은 작업당 할당되는 크기라 커넥션이 많으면 총 메모리 사용량이 `work_mem * max_connections * 작업수`가 될 수 있다. 세션 레벨에서 필요할 때만 올리는 방법도 있다.

```sql
-- 세션 레벨에서 임시 변경
SET work_mem = '64MB';
EXPLAIN ANALYZE SELECT ...;
RESET work_mem;
```

**effective_cache_size**

플래너가 OS 페이지 캐시에 얼마나 의존할 수 있는지에 대한 힌트다. 실제로 메모리를 할당하지 않고 플래너의 인덱스 사용 여부 판단에만 영향을 준다. `shared_buffers + OS 메모리의 50%` 정도로 설정하는 게 일반적이다.

**max_connections**

기본값은 메모리 크기에 따라 다르게 설정된다. PostgreSQL은 커넥션당 약 5~10MB의 메모리를 쓰므로 무작정 올리지 않는다. 커넥션이 많이 필요하다면 `max_connections`를 올리는 대신 PgBouncer를 쓰는 게 낫다.

## 자주 만나는 상황

**갑자기 모든 쿼리가 느려진 경우**

첫 번째로 보는 게 활성 커넥션 수와 잠금 대기다. 커넥션이 한계에 찼거나, 오래된 트랜잭션이 잠금을 잡고 있으면 다른 쿼리가 줄을 선다. MySQL에서는 `SHOW PROCESSLIST`, PostgreSQL에서는 `pg_stat_activity`를 바로 확인한다.

```sql
-- PostgreSQL: 오래 실행 중인 쿼리
SELECT
  pid,
  now() - query_start AS duration,
  state,
  left(query, 100) AS query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < now() - interval '30 seconds'
ORDER BY duration DESC;

-- 필요시 종료
SELECT pg_cancel_backend(pid);  -- 쿼리만 취소
SELECT pg_terminate_backend(pid);  -- 커넥션 강제 종료
```

**특정 쿼리만 갑자기 느려진 경우**

실행 계획이 바뀐 것이다. 통계 정보가 오래됐거나, 데이터 분포가 바뀌었거나, 히스토그램이 없는 컬럼에 편향된 값이 들어간 경우다. ANALYZE를 돌리고 EXPLAIN ANALYZE를 다시 확인한다.

PostgreSQL에서는 특정 값에 대해 플래너가 인덱스 대신 시퀀셜 스캔을 선택하는 경우가 있다. 이는 통계상 해당 값이 전체 행의 많은 비율을 차지하는 것으로 추정될 때다. 실제로 그렇지 않다면 통계를 더 세밀하게 수집하는 방법이 있다.

```sql
-- 특정 컬럼의 통계 정밀도 높이기
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 500;
ANALYZE orders;
```

기본 statistics target은 100이다. 편향된 컬럼은 높여준다.

**복제 지연이 갑자기 늘어난 경우**

레플리카에서 DDL이 실행되거나 대량 DML이 복제되면 지연이 생긴다. 레플리카에서 `pg_stat_activity`나 MySQL의 `SHOW SLAVE STATUS`를 확인한다. `Seconds_Behind_Master`(MySQL) 또는 `pg_stat_replication`(PostgreSQL 프라이머리에서)로 지연 원인을 추적한다.

레플리카에서 장시간 실행되는 쿼리가 복제 SQL 스레드를 막는 경우, 그 쿼리를 종료시키면 복제가 따라간다. 레플리카에서 직접 중단시켜야 한다.
