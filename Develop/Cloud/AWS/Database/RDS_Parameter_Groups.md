---
title: RDS Parameter Groups
tags: [aws, mysql, postgresql, cloud]
updated: 2026-07-25
---

# RDS Parameter Groups

RDS에서 DB 엔진 동작을 바꾸려면 파라미터 그룹을 수정해야 한다. EC2에서 직접 `my.cnf`를 편집하던 것과 달리, RDS는 파라미터 그룹이라는 레이어를 거친다. 기본 파라미터 그룹은 수정이 불가능하기 때문에, 운영 환경에서는 반드시 커스텀 파라미터 그룹을 만들어서 인스턴스에 붙여야 한다.

## Static vs Dynamic 파라미터

파라미터는 적용 방식에 따라 두 가지로 나뉜다.

**Dynamic 파라미터**는 인스턴스 재시작 없이 즉시 반영된다. 파라미터 그룹에서 값을 바꾸고 "Apply Immediately"를 선택하면 DB 엔진에 바로 반영된다.

**Static 파라미터**는 파라미터 그룹 수정 후 인스턴스를 재시작해야 반영된다. 재시작 전까지는 기존 값이 계속 적용된다. RDS 콘솔에서 수정하면 인스턴스 상태가 "pending-reboot"으로 표시된다.

운영 중에 static 파라미터를 바꿔야 한다면 Multi-AZ 환경에서 순차 재시작하거나, 점검 시간에 맞춰 작업해야 한다. 어떤 파라미터가 static인지는 AWS 콘솔의 "Apply Type" 컬럼으로 확인한다.

### 재시작 없이 적용 가능한 주요 파라미터

**MySQL Dynamic 파라미터**

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| max_connections | 자동 계산 | 최대 동시 커넥션 수 |
| slow_query_log | 0 | 슬로우 쿼리 로그 활성화 |
| long_query_time | 10 | 슬로우 쿼리 기준 시간(초) |
| innodb_lock_wait_timeout | 50 | 락 대기 타임아웃(초) |
| innodb_deadlock_detect | ON | 데드락 자동 감지 |
| innodb_print_all_deadlocks | OFF | 데드락 정보를 에러 로그에 기록 |
| read_only | 0 | 읽기 전용 모드 |

**PostgreSQL Dynamic 파라미터**

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| work_mem | 4MB | 정렬/해시 작업 메모리 |
| effective_cache_size | 계산값 | 플래너가 인식하는 캐시 크기 |
| autovacuum_vacuum_scale_factor | 0.2 | vacuum 트리거 비율 |
| autovacuum_vacuum_cost_delay | 2ms | vacuum I/O 쉬는 간격 |
| log_min_duration_statement | -1 | 슬로우 쿼리 기준 시간(ms) |

**Static 파라미터 (재시작 필요)**

| 파라미터 | 엔진 | 설명 |
|---|---|---|
| innodb_buffer_pool_size | MySQL | InnoDB 버퍼 풀 크기 |
| innodb_log_file_size | MySQL | 리두 로그 파일 크기 |
| shared_buffers | PostgreSQL | 공유 메모리 크기 |
| max_connections | PostgreSQL | 최대 커넥션 수 |
| autovacuum_max_workers | PostgreSQL | autovacuum 워커 수 |

## MySQL 핵심 파라미터

### innodb_buffer_pool_size

InnoDB 버퍼 풀 크기다. 데이터와 인덱스를 메모리에 캐싱하는 영역이라 DB 성능에 가장 큰 영향을 미친다. Static 파라미터라 변경 후 재시작이 필요하다.

인스턴스 메모리의 70~80%를 설정한다. `db.r6g.large`(16GB)라면 약 12GB, `db.r6g.xlarge`(32GB)라면 약 24GB가 출발점이다.

```sql
-- 현재 설정 확인
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- 버퍼 풀 히트율 확인
SELECT 
    (1 - (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') 
       / (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')
    ) * 100 AS buffer_pool_hit_rate;
```

히트율이 95% 아래로 떨어지면 버퍼 풀 크기를 늘려야 한다는 신호다. RDS에서는 `{DBInstanceClassMemory*3/4}` 수식으로 인스턴스 메모리에 비례한 값을 설정할 수 있다.

### max_connections

동시 허용 최대 커넥션 수다. Dynamic 파라미터라 재시작 없이 바꿀 수 있다.

RDS MySQL 기본값은 인스턴스 메모리에 따라 자동 계산된다. `{DBInstanceClassMemory/12582880}` 수식이 기본값 계산에 쓰인다. 이 공식대로 나온 값이 실제 서비스 커넥션 수보다 작은 경우가 있다. 그럴 때는 직접 값을 올려야 한다.

커넥션 풀 없이 운영하면 max_connections에 금방 걸린다. RDS Proxy를 앞에 두면 실제 DB 커넥션 수를 줄일 수 있다.

```sql
-- 현재 커넥션 상태 확인
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';
SHOW PROCESSLIST;
```

### 데드락 관련 파라미터 조합

운영에서 데드락 문제가 생겼을 때 건드리게 되는 파라미터 조합이다.

**innodb_deadlock_detect**

기본값 `ON`. MySQL이 데드락을 자동으로 감지하고 롤백 대상 트랜잭션을 결정한다.

높은 동시성 환경에서 이 기능이 오히려 성능 병목이 되는 경우가 있다. 데드락 감지를 위해 내부적으로 잠금 목록을 순회하는데, 커넥션이 많을수록 이 비용이 커진다. 초당 수천 TPS 수준의 워크로드에서 `innodb_deadlock_detect=OFF`로 끄고 `innodb_lock_wait_timeout`을 짧게 잡아 타임아웃으로 처리하는 방식을 쓰기도 한다.

단, 이 조합을 쓰면 데드락 발생 시 자동 롤백 대신 타임아웃 에러가 클라이언트에 전달된다. 애플리케이션에 재시도 로직이 있어야 한다.

**innodb_print_all_deadlocks**

기본값 `OFF`. `ON`으로 설정하면 데드락 발생 시마다 MySQL 에러 로그에 상세 정보를 기록한다. Dynamic 파라미터라 재시작 없이 켤 수 있다.

`SHOW ENGINE INNODB STATUS`는 마지막 데드락 정보만 보여줘서 간헐적으로 발생하는 데드락을 놓치는 경우가 있다. 이 파라미터를 켜두고 CloudWatch Logs로 수집하면 데드락 패턴을 분석할 수 있다.

**innodb_lock_wait_timeout**

기본값 `50`초. 락 획득 대기 시간이 이 값을 초과하면 에러를 반환한다. Dynamic 파라미터다.

OLTP 환경에서 50초는 너무 길다. 대부분 운영 환경에서 3~10초로 낮춰서 쓴다. 너무 짧게 잡으면 정상적인 트랜잭션도 에러가 날 수 있으니 서비스 특성에 맞는 값을 찾아야 한다.

```sql
-- 현재 설정 확인
SHOW VARIABLES LIKE 'innodb_deadlock_detect';
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';

-- 현재 락 대기 상태 확인
SELECT * FROM information_schema.INNODB_TRX ORDER BY trx_started;

-- 데드락 발생 이력 확인 (마지막 데드락만 보임)
SHOW ENGINE INNODB STATUS\G
```

### slow_query_log / long_query_time

둘 다 Dynamic 파라미터다. `slow_query_log` 기본값은 `0`(비활성화). `long_query_time` 기본값은 `10`초인데, 운영에서는 `1`초 또는 `0.5`초로 낮춰서 쓴다.

```ini
# 파라미터 그룹 설정
slow_query_log = 1
long_query_time = 1
log_output = FILE
```

CloudWatch Logs에서 슬로우 쿼리를 수집하려면 `log_output`을 `FILE`로 설정하고, RDS 콘솔에서 "Export logs to CloudWatch"를 활성화해야 한다.

## PostgreSQL 핵심 파라미터

### shared_buffers

PostgreSQL이 데이터 캐싱에 사용하는 공유 메모리 크기다. Static 파라미터라 변경 후 재시작이 필요하다.

PostgreSQL 공식 권고는 전체 메모리의 25% 정도다. MySQL과 달리 PostgreSQL은 OS 페이지 캐시에도 의존하기 때문에 너무 크게 잡으면 오히려 OS 캐시를 압박한다.

```sql
-- 현재 설정 확인
SHOW shared_buffers;

-- 버퍼 캐시 히트율 확인
SELECT 
    sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) AS cache_hit_ratio
FROM pg_statio_user_tables;
```

RDS에서는 `{DBInstanceClassMemory/32768}` 수식으로 메모리에 비례한 값을 쓸 수 있다.

### work_mem

정렬, 해시 조인, 비트맵 스캔에 사용하는 메모리 크기다. Dynamic 파라미터다. 세션당, 작업당으로 적용된다. 커넥션이 100개고 쿼리 하나에 정렬 작업이 5개 있으면 이론상 `work_mem * 500`만큼의 메모리가 필요하다.

기본값 4MB는 복잡한 분석 쿼리 환경에서 작아서 임시 파일을 쓰게 된다. 무조건 크게 잡으면 OOM이 발생하니 OLTP 환경에서는 4~8MB를 유지하고, 분석 쿼리는 세션 레벨로 필요할 때만 높게 설정한다.

```sql
-- 임시 파일 사용 여부 확인 (값이 높으면 work_mem 부족)
SELECT sum(temp_bytes) FROM pg_stat_database;

-- 세션 레벨 임시 변경 (재시작 불필요)
SET work_mem = '64MB';
```

### autovacuum 관련 파라미터

autovacuum은 PostgreSQL에서 가장 자주 문제가 되는 영역이다. 잘못 설정하면 테이블이 부풀거나(table bloat), 트랜잭션 ID 감싸기(transaction ID wraparound) 문제로 DB가 읽기 전용이 되는 최악의 상황까지 간다.

**autovacuum_vacuum_scale_factor**

기본값 `0.2`. 테이블에 dead tuple이 전체 행의 20% 이상 쌓이면 vacuum을 실행한다는 뜻이다. 소규모 테이블에서는 괜찮지만 수천만 건 이상의 대형 테이블에서는 문제가 된다. 행이 5000만 건이면 1000만 건의 dead tuple이 쌓여야 vacuum이 실행된다.

대형 테이블이 많은 환경에서는 `0.01` 이하로 낮춰야 한다. RDS 파라미터 그룹에서 전역으로 설정하거나, 테이블별 스토리지 파라미터로 개별 설정할 수 있다.

```sql
-- 테이블 레벨로 개별 설정
ALTER TABLE large_table SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

-- dead tuple 현황 확인
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup * 100.0 / nullif(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

**autovacuum_vacuum_cost_delay**

기본값 `2ms`. vacuum 작업이 I/O를 사용하다가 쉬는 간격이다. Dynamic 파라미터다. 값을 높이면 vacuum이 서버 I/O에 미치는 영향이 줄어들지만 vacuum 속도도 느려진다.

피크 타임에 vacuum이 I/O를 많이 잡아먹는다면 이 값을 높이고, dead tuple이 빠르게 쌓이는 테이블이 있다면 낮추는 쪽으로 조정한다. `0`으로 설정하면 딜레이 없이 최대 속도로 실행된다.

**autovacuum_max_workers**

기본값 `3`. 동시에 실행할 수 있는 autovacuum 워커 수다. Static 파라미터라 변경 후 재시작이 필요하다.

테이블이 많고 vacuum이 뒤처지는 상황이라면 워커 수를 늘릴 수 있다. 각 워커가 `maintenance_work_mem`만큼 메모리를 쓰기 때문에 무조건 늘린다고 좋은 게 아니다.

```sql
-- 현재 실행 중인 autovacuum 확인
SELECT pid, query, state, wait_event_type, wait_event, query_start
FROM pg_stat_activity
WHERE query LIKE 'autovacuum%';

-- 오래된 트랜잭션 ID 확인 (wraparound 위험 체크)
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

xid_age가 20억에 가까워지면 wraparound 위험 상태다. RDS는 이 상태가 되면 강제 vacuum을 실행하는데, 이 과정에서 성능이 급격히 떨어질 수 있다.

### effective_cache_size

쿼리 플래너가 총 캐시 크기를 추정할 때 쓰는 힌트 값이다. 실제 메모리를 할당하지 않는다. Dynamic 파라미터다.

이 값이 크면 플래너가 인덱스 스캔을 더 선호한다. 전체 메모리의 50~75%를 잡는다. 잘못된 값을 넣으면 플래너가 비효율적인 실행 계획을 선택한다.

```sql
-- 파라미터 소스 확인 (어디서 설정됐는지)
SELECT name, setting, source
FROM pg_settings
WHERE name IN ('shared_buffers', 'work_mem', 'effective_cache_size', 'autovacuum_vacuum_scale_factor');
```

## 파라미터 그룹 diff 비교

환경별로 파라미터 그룹 설정이 다를 때, 어떤 값이 다른지 확인하는 방법이다.

```bash
# prod 파라미터 그룹 추출
aws rds describe-db-parameters \
  --db-parameter-group-name prod-mysql-params \
  --query 'Parameters[].[ParameterName,ParameterValue]' \
  --output text | sort > /tmp/prod_params.txt

# staging 파라미터 그룹 추출
aws rds describe-db-parameters \
  --db-parameter-group-name staging-mysql-params \
  --query 'Parameters[].[ParameterName,ParameterValue]' \
  --output text | sort > /tmp/staging_params.txt

# 차이 확인
diff /tmp/prod_params.txt /tmp/staging_params.txt
```

기본값 파라미터는 값이 `None`으로 나온다. 커스텀으로 설정한 파라미터만 보려면 `--source user` 옵션을 추가한다.

```bash
# 커스텀 설정된 파라미터만 확인
aws rds describe-db-parameters \
  --db-parameter-group-name prod-mysql-params \
  --source user \
  --query 'Parameters[].[ParameterName,ParameterValue]' \
  --output text
```

페이지네이션이 있어서 파라미터가 많으면 결과가 잘릴 수 있다. `--max-items`를 조정하거나 `NextToken`으로 전체를 가져와야 한다.

특정 파라미터만 골라서 확인할 때는 `--query`로 필터링한다.

```bash
# 특정 파라미터만 확인
aws rds describe-db-parameters \
  --db-parameter-group-name prod-mysql-params \
  --query 'Parameters[?ParameterName==`innodb_buffer_pool_size` || ParameterName==`max_connections` || ParameterName==`slow_query_log`].[ParameterName,ParameterValue,ApplyType]' \
  --output table
```

## 파라미터 변경 롤백

파라미터를 잘못 설정했을 때 되돌리는 방법이다.

### Dynamic 파라미터 롤백

재시작 없이 값만 되돌리면 된다. 파라미터 그룹에서 해당 파라미터를 이전 값으로 수정하고 "Apply Immediately"를 선택한다.

```bash
# AWS CLI로 파라미터 값 되돌리기
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --parameters "ParameterName=innodb_lock_wait_timeout,ParameterValue=50,ApplyMethod=immediate"
```

`ApplyMethod=immediate`를 써야 즉시 반영된다. `pending-reboot`으로 설정하면 다음 재시작 때 반영된다.

### Static 파라미터 롤백

값을 수정해도 재시작 전까지 기존 값이 유지된다. 값을 되돌리고 재시작해야 한다.

```bash
# Static 파라미터 롤백
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --parameters "ParameterName=innodb_buffer_pool_size,ParameterValue=8589934592,ApplyMethod=pending-reboot"

# 인스턴스 재시작
aws rds reboot-db-instance \
  --db-instance-identifier prod-rds-instance
```

Multi-AZ 환경에서 재시작하면 페일오버가 발생한다. `--force-failover` 옵션 없이 재시작하면 인플레이스 재시작이 일어나면서 다운타임이 짧게 발생한다. 점검 시간을 잡거나 트래픽이 낮은 시간대에 작업해야 한다.

### 파라미터를 기본값으로 리셋

커스텀 설정을 지우고 엔진 기본값으로 돌리려면 `reset-db-parameter-group` 명령을 쓴다.

```bash
# 특정 파라미터만 기본값으로 리셋
aws rds reset-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --parameters "ParameterName=innodb_lock_wait_timeout,ApplyMethod=immediate"

# 전체 파라미터 그룹 리셋 (모든 파라미터를 기본값으로)
aws rds reset-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --reset-all-parameters
```

전체 리셋은 신중하게 써야 한다. 의도하지 않은 파라미터까지 기본값으로 돌아간다.

### 파라미터 그룹 교체 방식

파라미터 변경 전에 기존 그룹을 복사해두면 롤백이 쉽다. 문제가 된 파라미터 그룹 자체를 안전한 버전으로 교체하는 방식이다.

```bash
# 파라미터 그룹 복사 (변경 전 백업)
aws rds copy-db-parameter-group \
  --source-db-parameter-group-identifier prod-mysql-params \
  --target-db-parameter-group-identifier prod-mysql-params-backup-20260725 \
  --target-db-parameter-group-description "Backup before innodb_buffer_pool_size change"

# 롤백: 백업 파라미터 그룹으로 인스턴스 연결 변경
aws rds modify-db-instance \
  --db-instance-identifier prod-rds-instance \
  --db-parameter-group-name prod-mysql-params-backup-20260725 \
  --apply-immediately
```

파라미터 그룹 교체 자체는 Dynamic 파라미터만 있으면 재시작 없이 반영된다. Static 파라미터가 포함되어 있으면 교체 후에도 재시작이 필요하다.

## 파라미터 변경 후 적용 확인

파라미터 그룹을 수정한 뒤 실제 DB 엔진에 반영됐는지 반드시 확인해야 한다.

```sql
-- MySQL: 특정 파라미터 현재 값 확인
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'innodb_deadlock_detect';
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';

-- PostgreSQL: 재시작이 필요한 파라미터 변경 사항 확인
SELECT name, setting, pending_restart 
FROM pg_settings 
WHERE pending_restart = true;

-- PostgreSQL: 파라미터 소스 확인
SELECT name, setting, source
FROM pg_settings
WHERE name IN ('shared_buffers', 'work_mem', 'autovacuum_vacuum_scale_factor');
```

`pg_settings`의 `pending_restart` 컬럼이 `true`인 파라미터가 있으면 재시작이 필요한 상태다.

```bash
# AWS CLI로 pending-reboot 상태 확인
aws rds describe-db-instances \
  --db-instance-identifier prod-rds-instance \
  --query 'DBInstances[0].DBParameterGroups'
```

`ParameterApplyStatus`가 `pending-reboot`이면 static 파라미터 변경이 아직 반영되지 않은 상태다. `in-sync`이면 모두 적용된 상태다.

Static 파라미터 변경 후 재시작을 잊는 경우가 꽤 있다. 파라미터 그룹을 수정했는데 효과가 없다고 느낀다면 먼저 `pending_restart` 상태를 확인하는 게 맞다.
