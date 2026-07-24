---
title: Performance Insights로 RDS 성능 진단하기
tags: [aws, rds, performance-insights, aas, wait-events, slow-query, enhanced-monitoring, mysql, postgresql]
updated: 2026-07-24
---

# Performance Insights로 RDS 성능 진단하기

RDS에서 쿼리가 느려졌을 때 CloudWatch 지표만 보면 뭔가 튀긴 하는데 정확히 어디서 막히는지 알기 어렵다. CPU 사용률이 70%면 문제인 건지 아닌지도 판단하기 애매하다. Performance Insights는 DB 엔진 내부에서 어떤 쿼리가 얼마나 대기하는지를 직접 측정해서 보여준다.

---

## 1. Performance Insights 활성화

신규 인스턴스는 콘솔 기본 설정에서 Performance Insights가 활성화된 채로 만들어지는 경우가 많다. 기존 인스턴스는 직접 켜야 한다.

콘솔에서는 RDS → 인스턴스 선택 → Modify → Additional configuration → Performance Insights 섹션에서 Enable을 선택하면 된다. 수정 적용 시 재시작 없이 바로 수집이 시작된다.

CLI로 켤 때는 아래처럼 한다.

```bash
aws rds modify-db-instance \
    --db-instance-identifier mydb-instance \
    --enable-performance-insights \
    --performance-insights-retention-period 7 \
    --region ap-northeast-2
```

`--performance-insights-retention-period`는 7일이 무료 기간이다. 그 이상(31일, 93일 등)은 추가 비용이 발생한다. 장기 트렌드 분석이 필요하지 않다면 7일로 충분하다.

Aurora Serverless v1은 Performance Insights를 지원하지 않는다. Aurora Serverless v2는 지원한다. 인스턴스 클래스가 `db.t3.micro` 같은 소형 타입이면 Performance Insights를 켰을 때 엔진 오버헤드가 생길 수 있다. 프로덕션에서 쓰는 r6g나 m6g 계열은 오버헤드가 거의 없다.

---

## 2. DB Load (AAS)

Performance Insights의 핵심 지표는 DB Load다. 단위는 AAS(Average Active Sessions)로, 특정 시점에 DB 엔진에서 활성 상태인 세션의 평균 수를 나타낸다.

활성 세션이란 쿼리를 실행 중이거나 대기 중인 세션이다. 연결은 됐지만 idle 상태인 세션은 포함되지 않는다.

AAS를 해석할 때 기준이 되는 숫자가 vCPU 수다. db.r6g.2xlarge(8 vCPU)라면 AAS가 8 이하면 엔진이 CPU를 100% 사용하더라도 병렬 처리 여유가 있다는 의미다. AAS가 vCPU 수를 초과하기 시작하면 세션이 줄 서기 시작한다는 뜻이다.

```
AAS < vCPU 수     → 처리 능력 내에서 동작 중
AAS ≈ vCPU 수     → 포화 상태 진입
AAS >> vCPU 수    → 세션이 쌓이고 있음, 원인 파악 필요
```

AAS가 vCPU 수보다 낮아도 특정 대기 이벤트가 지배적이라면 문제가 될 수 있다. 전체 AAS는 3인데 그 3이 전부 lock wait이라면 실제로는 데드락 상황일 수 있다.

---

## 3. 대기 이벤트 유형별 원인

Performance Insights의 DB Load 차트는 대기 이벤트별로 색깔을 나눠서 쌓아서 보여준다. 어떤 대기 이벤트가 AAS를 구성하는지 보면 병목 유형을 바로 파악할 수 있다.

MySQL과 PostgreSQL은 대기 이벤트 분류 체계가 다르다. MySQL은 `io/file/sql/*`, `synch/mutex/*`, `wait/lock/*` 같은 형태고, PostgreSQL은 `IO`, `Lock`, `LWLock`, `Client` 같은 카테고리를 쓴다.

### 3.1 io/file 계열 (I/O 대기)

MySQL 기준으로 `io/file/sql/binlog`, `io/file/innodb/innodb_data_file` 같은 이벤트가 높다면 디스크 I/O가 병목이다.

주로 발생하는 상황은 버퍼 풀에 없는 데이터를 읽어야 할 때(cold read), 대량의 풀 테이블 스캔, binlog 쓰기가 느릴 때, 스토리지 타입이 gp2이고 IOPS 버스트 크레딧이 소진됐을 때다.

gp2 볼륨은 기준 IOPS(볼륨 크기 GB × 3)를 버스트 크레딧으로 초과할 수 있는데, 이 크레딧이 소진되면 갑자기 I/O 처리량이 떨어진다. CloudWatch의 `BurstBalance` 지표가 0에 가까워지면 이 상황이다. gp3로 전환하거나 Provisioned IOPS를 쓰면 버스트 크레딧 문제는 없어진다.

PostgreSQL에서 `IO:DataFileRead`가 높다면 shared_buffers에 없어서 디스크를 읽는다는 뜻이다. 이 경우 `pg_statio_user_tables`로 어느 테이블에서 heap_blks_read가 집중되는지 확인한다.

### 3.2 lock 계열 (잠금 대기)

MySQL에서 `wait/lock/table/sql/handler` 또는 InnoDB 행 잠금 대기가 높으면 트랜잭션 간 잠금 충돌이 발생하고 있다.

```sql
-- MySQL InnoDB 잠금 현황 확인
SELECT
    r.trx_id waiting_trx_id,
    r.trx_mysql_thread_id waiting_thread,
    r.trx_query waiting_query,
    b.trx_id blocking_trx_id,
    b.trx_mysql_thread_id blocking_thread,
    b.trx_query blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;
```

잠금 대기가 많은 패턴은 주로 두 가지다. 트랜잭션이 길어서 잠금을 오래 들고 있거나, 같은 행을 여러 트랜잭션이 동시에 업데이트하려는 경우다. 후자는 애플리케이션 로직에서 같은 레코드를 동시에 쓰는 상황을 피하거나, 배치 업데이트를 줄을 세워서 실행하도록 바꿔야 한다.

PostgreSQL에서 `Lock:relation`이 높다면 테이블 수준 잠금이 걸리고 있다는 뜻이다. DDL 작업(`ALTER TABLE`, `VACUUM FULL`)이나 명시적 `LOCK TABLE`이 원인인 경우가 많다. `pg_locks`와 `pg_stat_activity`를 조인해서 잠금 보유 쿼리를 찾는다.

```sql
-- PostgreSQL 잠금 대기 쿼리 확인
SELECT
    pid,
    query,
    state,
    wait_event_type,
    wait_event,
    pg_blocking_pids(pid) AS blocked_by
FROM pg_stat_activity
WHERE wait_event_type = 'Lock'
ORDER BY query_start;
```

### 3.3 CPU 대기

AAS 차트에서 CPU 항목이 높다면 쿼리 자체의 연산이 많다는 뜻이다. 인덱스를 타지 않고 풀 스캔을 하거나, 정렬이 메모리를 초과해서 디스크 sort를 쓰거나, 복잡한 집계 쿼리가 CPU를 많이 쓰는 경우다.

MySQL에서 `innodb_buffer_pool_reads` 지표가 낮은데 CPU가 높다면 연산 자체가 많은 것이다. `innodb_buffer_pool_reads`가 높다면 캐시 미스가 원인이라 CPU보다 I/O 문제에 가깝다. 이 두 지표를 같이 보면 CPU 대기인지 I/O 대기인지 구분하는 데 도움이 된다.

---

## 4. CPU wait vs IO wait 튜닝 접근

Performance Insights에서 CPU와 IO 대기는 차트에서 다른 색으로 구분되지만, 실제 진단 없이 둘을 혼동하면 엉뚱한 방향으로 가게 된다.

CPU 대기가 높을 때 먼저 확인할 것은 Top SQL에서 해당 쿼리의 EXPLAIN 결과다. `type=ALL`이면 풀 스캔이고, `Using filesort`나 `Using temporary`가 있으면 인덱스 없이 정렬이나 임시 테이블을 쓰는 것이다. 이 경우 인덱스를 추가하거나 쿼리를 인덱스를 탈 수 있는 형태로 바꾸는 것이 먼저다. 인스턴스 사이즈를 올리는 건 그 다음 선택지다.

IO 대기가 높을 때는 다른 접근이 필요하다. EXPLAIN에서 풀 스캔이 아닌데 IO가 높다면 데이터 자체의 볼륨 문제다. 자주 읽히는 데이터가 버퍼 풀 크기를 초과하거나, 인덱스가 메모리에 다 못 올라가 있거나, 스토리지 IOPS 한계에 도달한 상황이다.

```sql
-- MySQL: 버퍼 풀 히트율 확인 (90% 이하면 주의)
SELECT
    (1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)) * 100 AS hit_rate
FROM (
    SELECT
        VARIABLE_VALUE AS Innodb_buffer_pool_reads
    FROM performance_schema.global_status
    WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads'
) r,
(
    SELECT
        VARIABLE_VALUE AS Innodb_buffer_pool_read_requests
    FROM performance_schema.global_status
    WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'
) rr;
```

버퍼 풀 히트율이 90% 이하로 떨어지면 데이터가 메모리에 충분히 올라가 있지 않다는 신호다. 이때는 `innodb_buffer_pool_size`를 늘리거나(파라미터 그룹에서 가용 메모리의 70~80% 수준으로 설정), 인스턴스를 메모리가 더 큰 타입으로 올리는 것을 검토한다.

IOPS가 한계에 달한 경우라면 Enhanced Monitoring의 `diskIO.readIOsPS`와 `diskIO.writeIOsPS`를 같이 본다. gp2라면 gp3로 전환하면서 IOPS를 별도로 지정하는 것이 비용 대비 빠른 해결책이다. Provisioned IOPS(io1/io2)는 일관된 I/O가 필요한 경우에 쓴다.

CPU 대기와 IO 대기가 동시에 높을 때는 풀 스캔이 대량 데이터를 읽으면서 CPU 연산도 많은 상황이 많다. 이 경우 인덱스 추가가 두 가지를 한 번에 해결한다.

---

## 5. Top SQL로 병목 쿼리 식별

DB Load 차트 아래에 Top SQL 목록이 있다. 현재 시간 범위에서 DB Load에 가장 많이 기여한 쿼리 순으로 정렬된다. 쿼리 다이제스트(리터럴 값을 `?`로 치환한 형태) 기준으로 묶인다.

각 쿼리 항목에서 볼 수 있는 지표는 해당 쿼리가 차지한 DB Load, 초당 실행 횟수(Executions/sec), 평균 실행 시간(Avg latency), 스캔한 행 수와 반환한 행 수(Rows examined/returned)다.

Rows examined가 Rows returned보다 훨씬 크다면 인덱스가 없거나 인덱스 선택이 잘못된 경우다. 10만 행을 스캔해서 10개를 반환하는 쿼리는 분명히 인덱스 문제다.

특정 쿼리를 클릭하면 해당 쿼리의 대기 이벤트 분포를 볼 수 있다. 쿼리가 어디서 시간을 쓰는지 — I/O 대기인지 잠금 대기인지 CPU 연산인지 — 바로 나온다. 이 정보를 보고 EXPLAIN을 돌리는 방향을 잡는다.

```sql
-- MySQL: 의심 쿼리 실행 계획 확인
EXPLAIN FORMAT=JSON
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';
```

`type`이 `ALL`이면 풀 스캔이다. `key`가 NULL이면 인덱스를 안 타는 것이다. `rows` 값이 실제 반환 행 수에 비해 크게 높다면 인덱스 카디널리티 문제나 통계 오래됨 문제일 수 있다.

---

## 6. Performance Insights vs Enhanced Monitoring

Performance Insights와 Enhanced Monitoring은 모니터링하는 대상 자체가 다르다.

| | Performance Insights | Enhanced Monitoring |
|---|---|---|
| 수집 위치 | DB 엔진 내부 | 인스턴스 OS |
| 주요 지표 | DB Load, 대기 이벤트, SQL 통계 | CPU, 메모리, 디스크 I/O, 네트워크, 프로세스 목록 |
| 최소 간격 | 1초 | 1초 |
| 목적 | 쿼리 레벨 병목 진단 | 인프라 자원 사용 현황 |

Enhanced Monitoring은 CloudWatch Logs로 데이터를 보내고, RDS Process List 항목에서 OS 레벨 프로세스 목록도 볼 수 있다. 하지만 "어떤 쿼리가 문제인가"는 Performance Insights 없이는 알기 어렵다.

실제 진단 순서는 이렇게 흐른다. CloudWatch에서 CPU나 IOPS가 튀는 걸 먼저 보고, Performance Insights에서 그 시점의 AAS와 대기 이벤트를 확인해서 병목 유형을 좁힌 다음, Top SQL에서 원인 쿼리를 특정한다.

Enhanced Monitoring의 os 메트릭 중 `diskIO.writeKbps`나 `diskIO.readKbps`가 높은데 Performance Insights에서 I/O 대기가 높지 않다면, 백그라운드 작업(VACUUM, binlog flush 등)이 I/O를 쓰고 있는 경우다.

---

## 7. 슬로우 쿼리 추적 플로우

슬로우 쿼리 민원이 들어왔을 때 Performance Insights로 파악하는 흐름이다.

애플리케이션 로그나 APM에서 응답 시간이 튄 정확한 시간대를 먼저 특정한다. Performance Insights 콘솔에서 해당 시간 범위를 선택하고 AAS가 올라가 있는지 본다. AAS가 평소와 비슷한데 응답이 느렸다면 DB 문제가 아닐 수 있다. 이 경우 애플리케이션 서버나 네트워크 지연을 본다.

AAS가 올라가 있다면 어떤 대기 이벤트가 AAS를 채우는지 확인한다. I/O면 스토리지 상태를 같이 보고, lock이면 잠금 대기 쿼리를 찾는다. CPU면 연산 집중 쿼리를 의심한다.

해당 시간대 Top SQL 목록에서 평소와 다른 쿼리, 또는 Avg latency가 갑자기 높아진 쿼리를 찾는다. Executions/sec가 낮은데 latency가 높다면 단발성 무거운 쿼리다. Executions/sec가 높은데 latency도 높다면 자주 실행되는 쿼리가 한 번에 느려진 것이다.

Top SQL에서 해당 쿼리를 클릭해서 대기 이벤트 분포를 확인하고 EXPLAIN을 돌려서 실행 계획을 본다. Rows examined 대비 Rows returned 비율이 클수록 인덱스 문제일 가능성이 높다. 인덱스 문제라면 인덱스를 추가하거나 쿼리를 인덱스를 탈 수 있는 형태로 바꾼다. 잠금 문제라면 트랜잭션 범위를 줄이거나 업데이트 순서를 정렬한다.

---

## 8. Performance Insights API 활용

콘솔에서 수동으로 확인하는 것 외에 API를 써서 주기적으로 수집하거나 알람을 만들 수 있다.

```python
import boto3

client = boto3.client('pi', region_name='ap-northeast-2')

response = client.get_resource_metrics(
    ServiceType='RDS',
    Identifier='db:mydb-instance-id',
    MetricQueries=[
        {
            'Metric': 'db.load.avg',
            'GroupBy': {
                'Group': 'db.wait_event',
                'Dimensions': ['db.wait_event.name', 'db.wait_event.type'],
                'Limit': 5
            }
        }
    ],
    StartTime='2026-07-24T10:00:00Z',
    EndTime='2026-07-24T10:30:00Z',
    PeriodInSeconds=60
)

for result in response['MetricList']:
    print(result['Key'])
    for dp in result['DataPoints']:
        print(f"  {dp['Timestamp']}: {dp.get('Value', 0):.2f}")
```

Top SQL을 API로 가져오려면 `describe_dimension_keys`를 쓴다.

```python
response = client.describe_dimension_keys(
    ServiceType='RDS',
    Identifier='db:mydb-instance-id',
    StartTime='2026-07-24T10:00:00Z',
    EndTime='2026-07-24T10:30:00Z',
    Metric='db.load.avg',
    GroupBy={
        'Group': 'db.sql_tokenized',
        'Dimensions': ['db.sql_tokenized.statement'],
        'Limit': 10
    },
    PeriodInSeconds=3600
)

for key in response['Keys']:
    stmt = key['Dimensions'].get('db.sql_tokenized.statement', 'N/A')
    load = key['Total']
    print(f"Load: {load:.2f} | SQL: {stmt[:100]}")
```

이 API를 써서 AAS가 임계값을 초과할 때 Slack으로 알림을 보내거나, 일별 Top SQL 리포트를 자동으로 생성하는 식으로 활용한다.

---

## 9. 주의할 점

Performance Insights 데이터는 실시간에 가깝지만 완전한 실시간은 아니다. 1초 해상도로 보더라도 수 초의 지연이 있을 수 있다. 장애 대응 중에 현재 상황을 보려면 콘솔의 실시간 뷰를 쓰되, 이 지연을 감안해야 한다.

Multi-AZ 환경에서 failover가 일어나면 스탠바이 인스턴스가 프라이머리가 되고 Performance Insights 데이터가 새 인스턴스 기준으로 수집된다. failover 전후 지표가 연속적으로 이어지지 않을 수 있다.

쿼리 다이제스트는 `?`로 리터럴을 치환해서 묶는다. `WHERE id = 1`과 `WHERE id = 2`는 같은 다이제스트로 묶인다. 특정 파라미터 값 때문에 느려지는 경우(파라미터 스니핑, 실행 계획 캐시 오염)는 다이제스트 레벨에서는 보이지 않는다. 특정 값에서만 느리다는 제보가 있다면 실제 쿼리를 슬로우 쿼리 로그에서 찾아봐야 한다.

MySQL의 경우 `slow_query_log`와 `long_query_time`을 파라미터 그룹에서 설정하면 슬로우 쿼리 로그가 CloudWatch Logs로 올라간다. Performance Insights Top SQL에서 특정한 쿼리의 실제 파라미터 값은 여기서 찾는다.

```
# 파라미터 그룹 설정
slow_query_log = 1
long_query_time = 1
log_queries_not_using_indexes = 1
```

Performance Insights가 보여주는 건 엔진 내부의 대기 상태다. 여기서 잡히지 않는 느린 응답은 커넥션 풀 고갈, 네트워크 지연, 애플리케이션 레벨 문제다. DB가 문제가 아닌데 DB를 계속 들여다보는 건 시간 낭비다. Performance Insights에서 AAS가 정상이라면 DB 밖을 봐야 한다.
