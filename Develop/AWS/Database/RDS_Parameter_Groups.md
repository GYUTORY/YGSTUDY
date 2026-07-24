---
title: RDS Parameter Groups
tags: [AWS, RDS, Parameter Groups, MySQL, PostgreSQL]
updated: 2026-07-24
---

# RDS Parameter Groups

RDS에서 DB 엔진의 동작 방식을 바꾸려면 파라미터 그룹을 수정해야 한다. EC2에서 직접 `my.cnf`를 편집하던 것과 달리, RDS는 파라미터 그룹이라는 레이어를 통해 설정을 관리한다. 기본 파라미터 그룹은 수정이 불가능하기 때문에, 운영 환경에서는 반드시 커스텀 파라미터 그룹을 만들어서 인스턴스에 붙여야 한다.

## Static vs Dynamic 파라미터

파라미터는 적용 방식에 따라 두 가지로 나뉜다.

**Dynamic 파라미터**는 인스턴스 재시작 없이 즉시 반영된다. 파라미터 그룹에서 값을 바꾸고 적용하면 바로 DB 엔진에 반영된다. `max_connections`, `slow_query_log`, `long_query_time` 같은 것들이 여기에 해당한다.

**Static 파라미터**는 파라미터 그룹을 수정한 후 인스턴스를 재시작해야 반영된다. 재시작 전까지는 기존 값이 계속 적용된다. `innodb_buffer_pool_size`처럼 메모리 구조에 관여하는 파라미터가 대표적이다. RDS 콘솔에서 파라미터를 수정하면 인스턴스 상태가 "pending-reboot"으로 표시되는데, 이 상태에서는 재시작 전까지 새 값이 적용되지 않는다.

운영 중에 static 파라미터를 바꿔야 하는 상황이라면 Multi-AZ 환경에서 순차 재시작하거나, 점검 시간에 맞춰 작업해야 한다. 어떤 파라미터가 static인지는 AWS 문서나 콘솔에서 "Apply Type" 컬럼으로 확인할 수 있다.

## MySQL 핵심 파라미터

### innodb_buffer_pool_size

InnoDB의 버퍼 풀 크기를 결정한다. 데이터와 인덱스를 메모리에 캐싱하는 영역이라 DB 성능에 가장 큰 영향을 미치는 파라미터다. Static 파라미터라 변경 후 재시작이 필요하다.

일반적으로 인스턴스 메모리의 70~80%를 설정한다. `db.r6g.large`(16GB)라면 약 12GB, `db.r6g.xlarge`(32GB)라면 약 24GB 정도가 출발점이다.

```sql
-- 현재 설정 확인
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- 버퍼 풀 히트율 확인
SELECT 
    (1 - (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') 
       / (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')
    ) * 100 AS buffer_pool_hit_rate;
```

히트율이 95% 아래로 떨어지면 버퍼 풀 크기를 늘려야 한다는 신호다. RDS에서는 `{DBInstanceClassMemory*3/4}` 같은 수식으로 파라미터 값을 인스턴스 메모리에 비례해서 설정할 수 있다.

### max_connections

동시에 허용할 최대 커넥션 수다. Dynamic 파라미터라 재시작 없이 바꿀 수 있다.

RDS MySQL의 기본값은 인스턴스 메모리에 따라 자동으로 계산된다. `{DBInstanceClassMemory/12582880}` 수식이 기본값 계산에 쓰인다. 이 공식대로 나온 값이 실제 서비스 커넥션 수보다 훨씬 작은 경우가 있는데, 그럴 때는 직접 값을 올려줘야 한다.

커넥션 풀 없이 애플리케이션을 운영하면 max_connections에 금방 걸린다. RDS Proxy를 앞에 두면 실제 DB 커넥션 수를 크게 줄일 수 있다.

```sql
-- 현재 커넥션 상태 확인
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';

-- 커넥션 상세 보기
SHOW PROCESSLIST;
```

### slow_query_log

지정한 시간을 초과하는 쿼리를 슬로우 쿼리 로그에 기록한다. Dynamic 파라미터이며, `0`(비활성화) 또는 `1`(활성화)로 설정한다. 기본값은 `0`이다.

운영 초기에는 슬로우 쿼리 로그를 켜두는 게 낫다. CloudWatch Logs와 연동하면 느린 쿼리를 실시간으로 모니터링할 수 있다.

### long_query_time

슬로우 쿼리로 분류할 기준 시간(초)이다. Dynamic 파라미터다. 기본값은 `10`초인데, 이 값은 너무 느슨하다. 보통 `1`초로 설정하고, 더 촘촘하게 보고 싶으면 `0.5`나 `0.1`로 낮춘다.

```ini
# 파라미터 그룹 설정 예시
slow_query_log = 1
long_query_time = 1
log_output = FILE
```

CloudWatch Logs에서 슬로우 쿼리를 수집하려면 `log_output`을 `FILE`로 설정하고, RDS 콘솔에서 "Export logs to CloudWatch"를 활성화해야 한다.

```sql
-- 슬로우 쿼리 로그 상태 확인
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';
```

## PostgreSQL 핵심 파라미터

### shared_buffers

PostgreSQL이 데이터 캐싱에 사용하는 공유 메모리 크기다. MySQL의 `innodb_buffer_pool_size`에 해당한다. Static 파라미터라 변경 후 재시작이 필요하다.

PostgreSQL 공식 권고는 전체 메모리의 25% 정도다. MySQL과 달리 PostgreSQL은 OS 페이지 캐시에도 많이 의존하기 때문에 너무 크게 잡으면 오히려 OS 캐시를 압박한다.

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

정렬, 해시 조인, 비트맵 스캔에 사용하는 메모리 크기다. Dynamic 파라미터다. 여기서 중요한 점은 이 값이 세션당, 작업당으로 적용된다는 것이다. 커넥션이 100개고 쿼리 하나에 정렬 작업이 5개 있으면 이론상 `work_mem * 500`만큼의 메모리가 필요하다.

기본값은 4MB인데, 복잡한 분석 쿼리가 많은 환경에서는 이 값이 너무 작아서 임시 파일을 쓰게 된다. 무조건 크게 잡으면 메모리 부족으로 OOM이 발생하니 주의해야 한다. 일반적인 OLTP 환경에서는 4~8MB, 분석 쿼리가 많으면 세션 레벨로 필요할 때만 높게 설정하는 방식을 쓴다.

```sql
-- 현재 설정 확인
SHOW work_mem;

-- 세션 레벨로 임시 변경 (재시작 불필요)
SET work_mem = '64MB';

-- 임시 파일 사용 여부 확인 (값이 높으면 work_mem 부족)
SELECT sum(temp_bytes) FROM pg_stat_database;
```

### effective_cache_size

쿼리 플래너가 OS 페이지 캐시까지 포함한 총 캐시 크기를 추정할 때 쓰는 값이다. 실제로 메모리를 할당하지 않고 플래너 힌트로만 사용된다. Dynamic 파라미터다.

이 값이 크면 플래너가 인덱스 스캔을 더 선호한다. 보통 전체 메모리의 50~75%를 잡는다. 잘못된 값을 넣으면 플래너가 비효율적인 실행 계획을 선택할 수 있다.

```sql
-- 현재 설정 확인
SHOW effective_cache_size;
```

## 파라미터 변경 후 적용 확인

### 변경이 반영됐는지 확인하는 방법

파라미터 그룹을 수정한 뒤 실제로 DB 엔진에 반영됐는지 반드시 확인해야 한다.

**RDS 콘솔에서 확인**

인스턴스 상세 페이지의 "Configuration" 탭에서 현재 적용된 파라미터 그룹을 볼 수 있다. Static 파라미터를 변경했다면 인스턴스 상태가 "pending-reboot"으로 표시된다.

**DB 엔진에서 직접 확인**

```sql
-- MySQL: 특정 파라미터 확인
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'slow_query_log';

-- MySQL: 전체 파라미터 목록
SHOW VARIABLES;

-- PostgreSQL: 특정 파라미터 확인
SHOW shared_buffers;
SHOW work_mem;
SHOW effective_cache_size;

-- PostgreSQL: 재시작이 필요한 파라미터 변경 사항 확인
SELECT name, setting, pending_restart 
FROM pg_settings 
WHERE pending_restart = true;
```

`pg_settings`의 `pending_restart` 컬럼이 `true`인 파라미터가 있으면 재시작이 필요한 static 파라미터가 변경된 상태다.

**AWS CLI로 확인**

```bash
# 파라미터 그룹의 현재 설정 확인
aws rds describe-db-parameters \
  --db-parameter-group-name my-parameter-group \
  --query 'Parameters[?ParameterName==`innodb_buffer_pool_size`]'

# 인스턴스의 pending-reboot 상태 확인
aws rds describe-db-instances \
  --db-instance-identifier my-rds-instance \
  --query 'DBInstances[0].DBParameterGroups'
```

### 변경 후 주의사항

Static 파라미터 변경 후 재시작을 잊는 경우가 꽤 있다. 파라미터 그룹을 수정했는데 효과가 없다고 느낀다면 먼저 `pending_restart` 상태를 확인하는 게 맞다.

Dynamic 파라미터도 파라미터 그룹에서 값을 바꾼 뒤 "Apply Immediately" 옵션을 선택해야 즉시 반영된다. 선택하지 않으면 다음 유지 관리 기간에 적용된다.

파라미터를 잘못 설정하면 DB가 시작되지 않거나 성능이 오히려 떨어질 수 있다. 변경 전에 기존 파라미터 그룹을 복사해서 스테이징 환경에서 먼저 검증하는 게 안전하다.
