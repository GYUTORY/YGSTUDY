---
title: "BigQuery"
tags: [GCP, BigQuery, Data Warehouse, SQL]
updated: 2026-04-08
---

# BigQuery

Google Cloud의 서버리스 데이터 웨어하우스다. 인프라 관리 없이 페타바이트 규모의 데이터를 SQL로 분석할 수 있다.

온프레미스 데이터 웨어하우스와 가장 큰 차이는 **스토리지와 컴퓨팅이 분리**되어 있다는 점이다. 데이터를 저장하는 비용과 쿼리를 실행하는 비용이 별도로 청구된다. 이 구조 때문에 데이터를 많이 저장해도 쿼리를 안 돌리면 비용이 크지 않고, 반대로 적은 데이터에 무거운 쿼리를 돌리면 컴퓨팅 비용이 올라간다.

내부적으로 Dremel 엔진 기반이고, 컬럼 기반 스토리지(Capacitor 포맷)를 사용한다. 행 기반 스토리지와 달리 필요한 컬럼만 읽기 때문에 `SELECT *`를 안 쓰는 것만으로도 비용이 크게 줄어든다.

---

## 테이블 구조

### 파티셔닝

테이블을 특정 컬럼 기준으로 물리적으로 나누는 것이다. 쿼리 시 파티션 필터를 걸면 해당 파티션만 스캔하므로 비용과 속도 모두 개선된다.

파티셔닝 방식은 세 가지다:

- **시간 단위 파티셔닝**: `DATE`, `TIMESTAMP`, `DATETIME` 컬럼 기준. 가장 많이 쓴다.
- **정수 범위 파티셔닝**: 정수 컬럼을 범위로 나눈다. `user_id` 같은 컬럼에 쓸 수 있지만 실무에서는 드물다.
- **수집 시간 파티셔닝**: `_PARTITIONTIME` 의사 컬럼 기준. 데이터가 BigQuery에 들어온 시간 기준이라 원본 데이터의 날짜와 다를 수 있다.

```sql
CREATE TABLE `project.dataset.events`
(
  event_id STRING,
  user_id INT64,
  event_type STRING,
  event_timestamp TIMESTAMP,
  payload STRING
)
PARTITION BY DATE(event_timestamp)
OPTIONS (
  partition_expiration_days = 90,
  require_partition_filter = true
);
```

`require_partition_filter = true`는 반드시 설정해야 한다. 이걸 안 걸면 누군가 파티션 필터 없이 쿼리를 날려서 전체 테이블을 스캔하는 사고가 발생한다. 파티션 수 상한은 테이블당 4,000개다. 일 단위 파티셔닝이면 약 10년치다.

### 클러스터링

파티션 안에서 데이터를 특정 컬럼 기준으로 정렬해서 저장하는 것이다. 최대 4개 컬럼까지 지정할 수 있고, 순서가 중요하다. 첫 번째 컬럼 기준으로 먼저 정렬하고, 그 안에서 두 번째 컬럼으로 정렬하는 식이다.

```sql
CREATE TABLE `project.dataset.events`
(
  event_id STRING,
  user_id INT64,
  event_type STRING,
  event_timestamp TIMESTAMP,
  region STRING
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY event_type, region;
```

클러스터링은 카디널리티가 높은 컬럼에 쓰면 효과가 좋다. `WHERE event_type = 'purchase' AND region = 'kr'` 같은 쿼리에서 스캔 범위가 줄어든다.

파티셔닝과 클러스터링의 차이를 정리하면:

| 구분 | 파티셔닝 | 클러스터링 |
|------|----------|------------|
| 데이터 분리 | 물리적으로 분리 | 파티션 내 정렬 |
| 비용 예측 | 쿼리 전 정확한 바이트 수 계산 가능 | 실행 후에야 정확한 바이트 수 확인 가능 |
| 적용 컬럼 | 1개 | 최대 4개 |
| DML 영향 | 파티션 단위 관리 | 자동 재클러스터링 |

### 파티션 만료 설정

`partition_expiration_days`를 설정하면 해당 기간이 지난 파티션이 자동 삭제된다. 로그성 데이터처럼 일정 기간만 보관하면 되는 경우 필수다.

테이블 생성 후에도 변경할 수 있다:

```sql
ALTER TABLE `project.dataset.events`
SET OPTIONS (partition_expiration_days = 180);
```

주의할 점은, 이미 만료된 파티션이 있으면 설정 변경 즉시 삭제된다. 만료 기간을 줄일 때 기존 데이터가 날아갈 수 있으니 확인 후 변경해야 한다.

---

## 쿼리 비용 계산

BigQuery 과금 모델은 두 가지다:

### 온디맨드 (On-demand)

쿼리가 스캔한 바이트 수 기준으로 과금된다. 2026년 기준 1TB 스캔당 약 $6.25다. 최소 과금 단위는 10MB로, 1바이트만 스캔해도 10MB로 계산된다.

비용 계산 시 중요한 점:

- **컬럼 기반**: 선택한 컬럼의 데이터만 과금. `SELECT *`와 `SELECT user_id`의 비용 차이가 크다.
- **파티션 프루닝**: 파티션 필터가 걸리면 해당 파티션만 과금.
- **캐시**: 동일 쿼리 결과가 캐시되어 있으면 비용 0. 단 캐시 TTL은 약 24시간이고, 테이블이 변경되면 무효화된다.
- **DRY RUN**: 실행 전 비용 확인 가능.

```bash
# dry run으로 예상 스캔량 확인
bq query --dry_run --use_legacy_sql=false \
  'SELECT user_id, event_type FROM `project.dataset.events` WHERE DATE(event_timestamp) = "2026-04-01"'
```

### 용량 기반 (Capacity / Editions)

슬롯을 구매하거나 예약해서 사용하는 방식이다. 스캔량과 무관하게 슬롯 비용만 나간다.

---

## 슬롯과 예약

슬롯은 BigQuery의 컴퓨팅 단위다. 쿼리 하나가 실행될 때 여러 슬롯이 병렬로 작업을 처리한다.

온디맨드 사용자는 프로젝트당 약 2,000 슬롯을 공유한다. 이 한도는 보장이 아니라 상한이며, 피크 타임에는 슬롯이 부족해서 쿼리가 느려질 수 있다.

예약(Reservation)을 구매하면 전용 슬롯을 확보한다. Editions 모델에서는 다음과 같이 나뉜다:

- **Standard**: 자동 스케일링. 사용한 만큼 과금.
- **Enterprise**: 커밋 기간에 따른 할인. 기준선 슬롯 + 자동 스케일링.
- **Enterprise Plus**: 가장 높은 SLA와 성능.

슬롯 예약은 조직 전체에서 공유할 수 있고, Assignment를 통해 프로젝트나 폴더 단위로 할당한다.

실무에서 슬롯 모니터링은 `INFORMATION_SCHEMA.JOBS` 뷰로 한다:

```sql
SELECT
  job_id,
  total_slot_ms,
  total_bytes_processed,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) as duration_sec
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY total_slot_ms DESC
LIMIT 20;
```

---

## 외부 테이블 vs 네이티브 테이블

### 네이티브 테이블

BigQuery 내부 스토리지(Capacitor 포맷)에 데이터가 저장된다. 컬럼 기반 압축이 적용되어 있고 쿼리 성능이 가장 좋다. 파티셔닝, 클러스터링 모두 사용 가능하다.

### 외부 테이블

데이터는 Cloud Storage, Bigtable, Google Drive 등 외부에 있고, BigQuery는 메타데이터만 갖고 있다. 쿼리 시마다 외부에서 데이터를 읽어온다.

```sql
CREATE EXTERNAL TABLE `project.dataset.gcs_logs`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://my-bucket/logs/*.parquet']
);
```

외부 테이블의 문제점:

- **성능**: 네이티브 테이블 대비 느리다. 캐시도 안 된다.
- **비용**: 쿼리 비용은 동일하게 스캔량 기준인데, 외부 스토리지 읽기 비용이 추가된다.
- **파티셔닝 제한**: Hive 파티셔닝 레이아웃(`gs://bucket/dt=2026-04-01/`)만 지원한다.
- **DML 불가**: INSERT, UPDATE, DELETE를 직접 실행할 수 없다.

데이터 레이크에서 탐색용으로 잠깐 쓰기에는 괜찮지만, 반복적으로 쿼리하는 테이블이라면 네이티브로 로드하는 게 맞다.

### BigLake

외부 테이블의 확장 버전이다. Cloud Storage 위 데이터에 BigQuery의 세밀한 접근 제어(행/열 수준 보안)를 적용할 수 있다. 메타데이터 캐싱도 지원해서 일반 외부 테이블보다 성능이 낫다.

---

## DML 제한사항

BigQuery의 DML(INSERT, UPDATE, DELETE, MERGE)은 OLTP 데이터베이스와 다르게 동작한다.

### 쿼터 제한

- 테이블당 DML 문은 **하루 1,500개**가 기본 한도다. 파티션별이 아니라 테이블 단위다.
- 단일 DML 문의 최대 처리량은 제한이 있고, 트랜잭션 충돌 시 재시도가 필요하다.
- `MERGE` 문도 DML 쿼터에 포함된다.

### 동시성

같은 테이블에 여러 DML을 동시에 실행하면 충돌이 난다. BigQuery는 스냅샷 격리를 사용하는데, 동일 테이블에 대한 DML은 직렬화된다. 여러 작업이 동시에 같은 테이블을 수정하려고 하면 일부가 실패한다.

```
Error: Could not serialize access to table project:dataset.table
due to concurrent update
```

이 에러가 나면 재시도 로직을 넣어야 한다. 실시간으로 빈번하게 수정해야 하는 워크로드라면 BigQuery가 적합하지 않다. Cloud Spanner나 Cloud SQL을 고려해야 한다.

### UPDATE/DELETE 비용

UPDATE나 DELETE는 내부적으로 전체 테이블(또는 파티션)을 다시 쓴다. 1건만 수정해도 해당 파티션 전체를 재작성하기 때문에 비용이 크다. 파티셔닝이 되어 있으면 해당 파티션만 재작성하니 파티션 필터를 반드시 걸어야 한다.

---

## 데이터 적재: 스트리밍 Insert vs Storage Write API

### 스트리밍 Insert (Legacy)

`tabledata.insertAll` API다. 실시간에 가까운 데이터 적재가 가능하지만 비용이 비싸다. 스캔 비용과 별도로 적재 바이트당 과금이 있다.

제한사항:

- 적재 직후 데이터가 스트리밍 버퍼에 들어가는데, 이 버퍼의 데이터는 UPDATE/DELETE가 안 된다.
- 버퍼에서 일반 스토리지로 옮겨지는 데 최대 90분 정도 걸릴 수 있다.
- 중복 제거를 위한 `insertId`를 넣어도 best-effort 수준이라 완벽하지 않다.

### Storage Write API

스트리밍 Insert의 후속 API다. gRPC 기반으로 더 빠르고 저렴하다.

세 가지 모드가 있다:

- **Default stream**: at-least-once 전달. 가장 간단하지만 중복 가능성이 있다.
- **Committed**: exactly-once 보장. 오프셋 관리를 직접 해야 한다.
- **Pending**: 배치로 모아서 한 번에 커밋. 대량 적재에 적합하다.

```python
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types, writer
from google.protobuf import descriptor_pb2
import events_pb2  # protobuf 스키마 컴파일 결과

client = bigquery_storage_v1.BigQueryWriteClient()
parent = client.table_path("my-project", "my_dataset", "events")

# Default stream 사용
write_stream = types.WriteStream(type_=types.WriteStream.Type.DEFAULT)
stream = client.create_write_stream(
    parent=parent, write_stream=write_stream
)

request = types.AppendRowsRequest()
request.write_stream = stream.name

proto_rows = types.ProtoRows()
row = events_pb2.EventRow()
row.event_id = "evt_001"
row.user_id = 12345
row.event_type = "purchase"
proto_rows.serialized_rows.append(row.SerializeToString())

proto_data = types.AppendRowsRequest.ProtoData()
proto_data.rows = proto_rows

# 스키마 descriptor 설정
proto_schema = types.ProtoSchema()
descriptor = descriptor_pb2.DescriptorProto()
events_pb2.EventRow.DESCRIPTOR.CopyToProto(descriptor)
proto_schema.proto_descriptor = descriptor
proto_data.writer_schema = proto_schema

request.proto_rows = proto_data

response = client.append_rows(iter([request]))
```

실무에서는 대부분의 신규 프로젝트에서 Storage Write API를 쓴다. 스트리밍 Insert 대비 비용이 절반 이하이고, 처리량도 높다.

---

## 쿼리 최적화

### SELECT * 금지

BigQuery에서 가장 흔한 비용 낭비다. 컬럼 기반 스토리지라서 불필요한 컬럼을 선택하면 그만큼 과금된다.

```sql
-- 나쁜 예: 전체 컬럼 스캔
SELECT * FROM `project.dataset.events`
WHERE DATE(event_timestamp) = '2026-04-01';

-- 좋은 예: 필요한 컬럼만 지정
SELECT event_id, user_id, event_type
FROM `project.dataset.events`
WHERE DATE(event_timestamp) = '2026-04-01';
```

### 파티션 필터 강제

앞서 언급한 `require_partition_filter = true` 옵션이다. 이미 생성된 테이블이라면:

```sql
ALTER TABLE `project.dataset.events`
SET OPTIONS (require_partition_filter = true);
```

### WHERE 절에서 함수 사용 주의

파티션 컬럼에 함수를 씌우면 파티션 프루닝이 안 될 수 있다.

```sql
-- 파티션 프루닝 안 됨
WHERE EXTRACT(YEAR FROM event_timestamp) = 2026

-- 파티션 프루닝 됨
WHERE event_timestamp BETWEEN '2026-01-01' AND '2026-12-31'
```

### JOIN 최적화

- 큰 테이블을 왼쪽에 두고 작은 테이블을 오른쪽에 둔다. BigQuery는 오른쪽 테이블을 각 슬롯에 브로드캐스트한다.
- JOIN 전에 필터링을 먼저 한다. 서브쿼리로 필요한 데이터만 줄인 뒤 JOIN하면 셔플 양이 줄어든다.

```sql
-- 비효율: 전체 테이블 JOIN 후 필터
SELECT a.user_id, b.name
FROM `project.dataset.events` a
JOIN `project.dataset.users` b ON a.user_id = b.user_id
WHERE DATE(a.event_timestamp) = '2026-04-01';

-- 개선: 서브쿼리로 먼저 필터링
SELECT a.user_id, b.name
FROM (
  SELECT user_id
  FROM `project.dataset.events`
  WHERE DATE(event_timestamp) = '2026-04-01'
) a
JOIN `project.dataset.users` b ON a.user_id = b.user_id;
```

### 기타 팁

- `APPROX_COUNT_DISTINCT`는 `COUNT(DISTINCT)`보다 빠르고 슬롯을 적게 쓴다. 정확도 오차 약 1%.
- 임시 결과가 자주 쓰이면 `CREATE TEMP TABLE`이나 CTE(`WITH`)를 쓴다.
- `ORDER BY`는 최종 결과에만 걸고, 서브쿼리 안에서는 제거한다.
- `LIMIT`은 비용을 줄여주지 않는다. BigQuery는 전체를 스캔한 뒤 결과만 자른다.

---

## 클라이언트 코드

### Java

```java
import com.google.cloud.bigquery.*;

public class BigQueryExample {

    public static void main(String[] args) {
        BigQuery bigquery = BigQueryOptions.getDefaultInstance().getService();

        String query = "SELECT event_id, user_id, event_type "
            + "FROM `my-project.my_dataset.events` "
            + "WHERE DATE(event_timestamp) = '2026-04-01' "
            + "LIMIT 100";

        QueryJobConfiguration queryConfig = QueryJobConfiguration.newBuilder(query)
            .setUseLegacySql(false)
            .build();

        try {
            TableResult result = bigquery.query(queryConfig);
            for (FieldValueList row : result.iterateAll()) {
                String eventId = row.get("event_id").getStringValue();
                long userId = row.get("user_id").getLongValue();
                String eventType = row.get("event_type").getStringValue();
                System.out.printf("event=%s user=%d type=%s%n", eventId, userId, eventType);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Query interrupted", e);
        }
    }
}
```

Gradle 의존성:

```groovy
implementation 'com.google.cloud:google-cloud-bigquery:2.40.1'
```

### Python

```python
from google.cloud import bigquery

client = bigquery.Client()

query = """
SELECT event_id, user_id, event_type
FROM `my-project.my_dataset.events`
WHERE DATE(event_timestamp) = '2026-04-01'
LIMIT 100
"""

# dry run으로 스캔량 확인
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
dry_run_job = client.query(query, job_config=job_config)
print(f"예상 스캔량: {dry_run_job.total_bytes_processed / 1024 / 1024:.1f} MB")

# 실행
query_job = client.query(query)
rows = query_job.result()

for row in rows:
    print(f"event={row.event_id} user={row.user_id} type={row.event_type}")
```

pip 설치:

```bash
pip install google-cloud-bigquery
```

Python 클라이언트에서 주의할 점은, `client.query()`가 비동기로 Job을 생성한다는 것이다. `.result()`를 호출해야 완료를 기다린다. 대량 데이터를 가져올 때는 `to_dataframe()`으로 pandas DataFrame으로 변환하는 게 편하다.

```python
df = client.query(query).to_dataframe()
```

이때 `pyarrow`와 `pandas`가 설치되어 있어야 한다.

---

## 비용 폭탄 사례와 대응

### 사례 1: SELECT * + 파티션 필터 누락

가장 흔한 케이스다. 데이터 엔지니어가 탐색 목적으로 `SELECT * FROM big_table` 쿼리를 날렸는데, 파티션 필터가 없어서 수 TB를 풀스캔한 경우.

**대응**: `require_partition_filter = true` 옵션을 모든 파티션 테이블에 건다. 조직 정책(Organization Policy)으로 강제할 수도 있다.

### 사례 2: 스케줄 쿼리의 대상 테이블 성장

매일 돌아가는 스케줄 쿼리가 처음에는 100GB 테이블을 스캔했는데, 1년 뒤에는 1TB가 된 경우. 파티션 필터를 넣어뒀어도 `WHERE date >= '2025-01-01'` 같이 고정 날짜를 쓰면 시간이 지날수록 스캔 범위가 넓어진다.

**대응**: 스케줄 쿼리에는 `CURRENT_DATE()` 기준 상대 날짜를 써야 한다.

```sql
-- 나쁜 예: 고정 날짜
WHERE DATE(event_timestamp) >= '2025-01-01'

-- 좋은 예: 상대 날짜
WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

### 사례 3: 뷰(View) 중첩

뷰 A가 뷰 B를 참조하고, 뷰 B가 뷰 C를 참조하는 구조. 사용자는 뷰 A에서 컬럼 2개만 조회한다고 생각하지만, 내부적으로 뷰 C의 `SELECT *`가 실행되면서 전체 테이블을 스캔한다.

**대응**: 뷰를 만들 때 `SELECT *`를 절대 쓰지 않는다. `INFORMATION_SCHEMA.JOBS`에서 정기적으로 고비용 쿼리를 모니터링한다.

### 사례 4: 스트리밍 Insert 과금

실시간 파이프라인에서 스트리밍 Insert를 쓰고 있었는데, 적재량이 늘어나면서 월 수천 달러가 나온 경우. 적재 비용이 GB당 $0.01인데 하루 수 TB씩 넣으면 금방 쌓인다.

**대응**: Storage Write API의 Default stream으로 전환하면 비용이 크게 줄어든다. 실시간성이 필요 없는 경우라면 배치 로드(`bq load`)는 무료다.

### 사례 5: Cross-region 쿼리

US 리전 데이터셋과 EU 리전 데이터셋을 JOIN하려고 하면 실패한다. 이걸 우회하려고 한쪽을 복사하는데, 대량 데이터 복사 비용과 네트워크 전송 비용이 발생한다.

**대응**: 데이터셋 리전을 처음부터 통일한다. BigQuery 데이터셋은 생성 후 리전 변경이 불가능하니 초기 설계가 중요하다.

### 비용 모니터링 설정

BigQuery 비용을 모니터링하는 가장 간단한 방법은 커스텀 쿼터 설정이다.

프로젝트 수준에서 하루 최대 스캔량을 제한할 수 있다:

```bash
# 사용자별 일일 쿼리 사용량 제한 (1TB)
bq update --project_id=my-project \
  --default_query_job_timeout_ms=300000
```

Cloud Monitoring에서 BigQuery 슬롯 사용량과 바이트 스캔량에 대한 알림을 설정하는 것도 필수다. `INFORMATION_SCHEMA.JOBS`를 주기적으로 조회하는 대시보드를 만들어두면 비용 급증을 빠르게 감지할 수 있다.

```sql
-- 최근 7일간 사용자별 비용 추정
SELECT
  user_email,
  SUM(total_bytes_processed) / POW(1024, 4) as total_tb_scanned,
  SUM(total_bytes_processed) / POW(1024, 4) * 6.25 as estimated_cost_usd
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY user_email
ORDER BY total_tb_scanned DESC;
```
