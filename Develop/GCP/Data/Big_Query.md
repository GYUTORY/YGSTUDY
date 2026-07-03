---
title: "BigQuery"
tags: [GCP, BigQuery, Data Warehouse, SQL, BigQuery ML, CDC]
updated: 2026-04-12
---

# BigQuery

Google Cloud의 서버리스 데이터 웨어하우스다. 인프라 관리 없이 페타바이트 규모의 데이터를 SQL로 분석할 수 있다.

온프레미스 데이터 웨어하우스와 가장 큰 차이는 **스토리지와 컴퓨팅이 분리**되어 있다는 점이다. 데이터를 저장하는 비용과 쿼리를 실행하는 비용이 별도로 청구된다. 이 구조 때문에 데이터를 많이 저장해도 쿼리를 안 돌리면 비용이 크지 않고, 반대로 적은 데이터에 무거운 쿼리를 돌리면 컴퓨팅 비용이 올라간다.

내부적으로 Dremel 엔진 기반이고, 컬럼 기반 스토리지(Capacitor 포맷)를 사용한다. 행 기반 스토리지와 달리 필요한 컬럼만 읽기 때문에 `SELECT *`를 안 쓰는 것만으로도 비용이 크게 줄어든다.

## 아키텍처

BigQuery의 핵심 구조는 스토리지와 컴퓨팅이 완전히 분리된 형태다.

```
┌──────────────────────────────────────────────────────────┐
│                      사용자 요청                          │
│              (Console / bq CLI / REST API)                │
└──────────────┬───────────────────────────────────────────┘
               │
               v
┌──────────────────────────────────────────────────────────┐
│                   BigQuery Service                        │
│  ┌─────────────────┐    ┌────────────────────────────┐   │
│  │  Query Engine    │    │   Job Orchestrator         │   │
│  │  (Dremel)        │    │   - 쿼리 파싱/최적화       │   │
│  │                  │    │   - 실행 계획 수립          │   │
│  │  ┌────────────┐  │    │   - 슬롯 할당 요청         │   │
│  │  │ Root Server│  │    └────────────────────────────┘   │
│  │  └─────┬──────┘  │                                     │
│  │   ┌────┴────┐    │                                     │
│  │   v         v    │                                     │
│  │ ┌─────┐ ┌─────┐  │                                     │
│  │ │Mixer│ │Mixer│  │  <-- 중간 집계 (셔플, 정렬)         │
│  │ └──┬──┘ └──┬──┘  │                                     │
│  │  ┌─┴─┐  ┌─┴─┐   │                                     │
│  │  v   v  v   v    │                                     │
│  │ ┌──┐┌──┐┌──┐┌──┐ │                                     │
│  │ │S1││S2││S3││S4│ │  <-- Leaf 슬롯 (병렬 스캔/필터)     │
│  │ └──┘└──┘└──┘└──┘ │                                     │
│  └─────────┬────────┘                                     │
└────────────┼─────────────────────────────────────────────┘
             │ 네트워크 (Jupiter)
             v
┌──────────────────────────────────────────────────────────┐
│                   Colossus (분산 스토리지)                 │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │Capacitor │  │Capacitor │  │Capacitor │  ...           │
│  │(컬럼형)   │  │(컬럼형)   │  │(컬럼형)   │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└──────────────────────────────────────────────────────────┘
```

이 구조에서 중요한 포인트:

- **Dremel 트리 구조**: Root Server가 쿼리를 받아 실행 계획을 세우고, Mixer가 중간 집계를 하고, Leaf 슬롯이 실제 데이터를 스캔한다. 단계별로 병렬 처리가 일어난다.
- **Jupiter 네트워크**: Google 내부 네트워크로 스토리지와 컴퓨팅 사이를 연결한다. 1Pb/s급 대역폭 덕분에 스토리지 분리에도 불구하고 속도가 나온다.
- **Colossus**: Google의 분산 파일 시스템이다. 데이터는 Capacitor라는 컬럼 기반 포맷으로 저장되고, 자동으로 복제/압축된다.

스토리지와 컴퓨팅이 분리되어 있기 때문에 저장 중인 데이터 양과 쿼리 워크로드를 독립적으로 스케일링할 수 있다. 쿼리를 안 돌리는 시간에는 컴퓨팅 비용이 0이고, 스토리지는 90일 이상 수정이 없으면 자동으로 장기 스토리지 요금(약 50% 할인)으로 전환된다.

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

파티셔닝과 클러스터링이 데이터를 나누는 방식은 근본적으로 다르다.

```
[ 파티셔닝: 물리적 분리 ]

 테이블
 ┌────────────────────────────────┐
 │ Partition: 2026-04-01          │  ← 하나의 독립된 저장 단위
 │  row1, row2, row3 ...         │
 ├────────────────────────────────┤
 │ Partition: 2026-04-02          │  ← 쿼리 시 이 파티션만 스캔 가능
 │  row4, row5, row6 ...         │
 ├────────────────────────────────┤
 │ Partition: 2026-04-03          │
 │  row7, row8, row9 ...         │
 └────────────────────────────────┘
 → WHERE date = '2026-04-02' → 해당 파티션만 읽음 (비용 1/3)


[ 클러스터링: 파티션 내부 정렬 ]

 Partition: 2026-04-02
 ┌────────────────────────────────────────────────┐
 │  CLUSTER BY event_type, region                 │
 │                                                │
 │  ┌─────────────────────┐  블록 1               │
 │  │ event_type=click     │                      │
 │  │ region=jp            │                      │
 │  └─────────────────────┘                       │
 │  ┌─────────────────────┐  블록 2               │
 │  │ event_type=click     │                      │
 │  │ region=kr            │                      │
 │  └─────────────────────┘                       │
 │  ┌─────────────────────┐  블록 3               │
 │  │ event_type=purchase  │                      │
 │  │ region=kr            │                      │
 │  └─────────────────────┘                       │
 └────────────────────────────────────────────────┘
 → WHERE event_type='purchase' AND region='kr' → 블록 3만 읽음
```

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

```
[ 슬롯 할당 흐름 — Editions 모델 ]

 ┌───────────────────────────────────────────────┐
 │              Organization                      │
 │                                                │
 │  Reservation: "analytics"   (500 기준선 슬롯)   │
 │  ┌───────────────────────────────────────────┐ │
 │  │  Autoscale: 최대 1500 슬롯까지 확장 가능    │ │
 │  │                                           │ │
 │  │  Assignment ──→ project-a (BI팀)          │ │
 │  │  Assignment ──→ project-b (DS팀)          │ │
 │  └───────────────────────────────────────────┘ │
 │                                                │
 │  Reservation: "etl"         (200 기준선 슬롯)   │
 │  ┌───────────────────────────────────────────┐ │
 │  │  Autoscale: 비활성화                       │ │
 │  │                                           │ │
 │  │  Assignment ──→ project-c (파이프라인)     │ │
 │  └───────────────────────────────────────────┘ │
 │                                                │
 │  (미할당 프로젝트 → 온디맨드 공유 풀 사용)       │
 └───────────────────────────────────────────────┘

 쿼리 실행 시:
 1. project-a에서 쿼리 제출
 2. "analytics" Reservation에서 슬롯 할당
 3. 기준선 500 슬롯 부족 시 → Autoscale로 최대 1500까지 확장
 4. 쿼리 완료 후 → 확장 슬롯 반환 (초 단위 과금)
```

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

---

## 스케줄 쿼리

BigQuery에서 쿼리를 주기적으로 실행하려면 스케줄 쿼리(Scheduled Query)를 사용한다. 내부적으로 BigQuery Data Transfer Service 위에서 돌아간다.

콘솔에서 쿼리 작성 후 "Schedule" 버튼으로 설정할 수 있고, `bq` CLI나 Terraform으로도 만든다.

```sql
-- 스케줄 쿼리 예시: 일별 집계 테이블 생성
-- 스케줄 설정에서 "매일 02:00 UTC" + "대상 테이블 덮어쓰기" 선택

SELECT
  DATE(event_timestamp) AS event_date,
  event_type,
  COUNT(*) AS event_count,
  COUNT(DISTINCT user_id) AS unique_users
FROM `project.dataset.events`
WHERE DATE(event_timestamp) = DATE_SUB(@run_date, INTERVAL 1 DAY)
GROUP BY event_date, event_type;
```

`@run_date`는 스케줄 쿼리 전용 파라미터다. 실행 시점의 날짜가 자동으로 들어간다. `@run_time`은 TIMESTAMP 타입이다.

Terraform으로 관리하면 코드 리뷰가 가능하고, 환경별 배포도 된다:

```hcl
resource "google_bigquery_data_transfer_config" "daily_agg" {
  display_name   = "daily_event_aggregation"
  location       = "US"
  data_source_id = "scheduled_query"
  schedule       = "every day 02:00"

  destination_dataset_id = "my_dataset"

  params = {
    destination_table_name_template = "daily_events_{run_date}"
    write_disposition               = "WRITE_TRUNCATE"
    query                           = <<-SQL
      SELECT
        DATE(event_timestamp) AS event_date,
        event_type,
        COUNT(*) AS event_count
      FROM `project.dataset.events`
      WHERE DATE(event_timestamp) = DATE_SUB(@run_date, INTERVAL 1 DAY)
      GROUP BY event_date, event_type
    SQL
  }

  service_account_name = "bq-scheduler@project.iam.gserviceaccount.com"
}
```

스케줄 쿼리 운영 시 주의사항:

- **실패 알림 설정 필수**: 기본적으로 실패해도 알림이 없다. Cloud Monitoring이나 Pub/Sub 연동으로 알림을 걸어야 한다.
- **서비스 계정 권한**: 스케줄 쿼리는 생성자의 권한이 아니라 지정된 서비스 계정 권한으로 실행된다. 서비스 계정에 필요한 데이터셋 접근 권한이 있는지 확인해야 한다.
- **@run_date 기준 날짜 사용**: 앞서 비용 폭탄 사례에서 언급했듯이, 고정 날짜 대신 `@run_date` 기준 상대 날짜를 써야 스캔 범위가 계속 커지는 문제를 방지한다.
- **백필(backfill)**: 특정 날짜 범위를 다시 실행해야 하면 콘솔에서 "Manual Transfer" 또는 API로 백필 요청을 보낸다.

---

## Materialized View

Materialized View(MV)는 쿼리 결과를 물리적으로 저장해두는 뷰다. 일반 View와 달리 매번 쿼리를 실행하지 않고 미리 계산된 결과를 읽는다.

```sql
CREATE MATERIALIZED VIEW `project.dataset.mv_daily_events`
AS
SELECT
  DATE(event_timestamp) AS event_date,
  event_type,
  COUNT(*) AS event_count,
  SUM(revenue) AS total_revenue
FROM `project.dataset.events`
GROUP BY event_date, event_type;
```

MV는 원본 테이블이 변경되면 자동으로 갱신된다. 갱신 주기는 BigQuery가 판단하며, 수동으로 `CALL BQ.REFRESH_MATERIALIZED_VIEW('project.dataset.mv_daily_events')`를 실행할 수도 있다.

MV를 직접 조회하지 않아도 원본 테이블에 대한 쿼리를 BigQuery가 자동으로 MV로 라우팅하는 경우가 있다. 이걸 **자동 리라이팅(Smart Tuning)**이라고 한다. 쿼리 실행 계획에서 `materialized_view_statistics`를 확인하면 MV가 사용됐는지 볼 수 있다.

MV를 쓸 때 알아야 할 제약:

- **지원 함수 제한**: `GROUP BY` + 집계 함수(`COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, `COUNT DISTINCT` 등)만 된다. `JOIN`은 단일 테이블과의 inner join만 된다.
- **파티셔닝 필수 아님이지만 권장**: 원본 테이블이 파티셔닝되어 있으면 MV도 같은 기준으로 파티셔닝된다. 증분 갱신 비용이 줄어든다.
- **갱신 비용**: 자동 갱신은 스캔 비용이 발생한다. 원본 테이블에 데이터가 빈번하게 들어오면 갱신도 자주 일어나서 비용이 늘어날 수 있다. `max_staleness` 옵션으로 갱신 빈도를 제어한다.

```sql
-- 최대 30분까지 stale 데이터 허용 (갱신 빈도 제한)
CREATE MATERIALIZED VIEW `project.dataset.mv_daily_events`
OPTIONS (enable_refresh = true, refresh_interval_minutes = 30, max_staleness = INTERVAL 30 MINUTE)
AS
SELECT
  DATE(event_timestamp) AS event_date,
  event_type,
  COUNT(*) AS event_count
FROM `project.dataset.events`
GROUP BY event_date, event_type;
```

MV와 스케줄 쿼리를 비교하면:

| 구분 | Materialized View | 스케줄 쿼리 |
|------|-------------------|-------------|
| 갱신 방식 | 자동(증분) | 수동(전체 또는 파티션 단위) |
| 실시간성 | 원본 변경 후 자동 반영 | 스케줄 주기에 의존 |
| 쿼리 제약 | 집계 + 단일 테이블 JOIN만 | 제약 없음 |
| 비용 구조 | 증분 갱신 비용 + 스토리지 | 쿼리 실행 비용 + 스토리지 |

집계 쿼리가 반복적으로 호출되는 대시보드라면 MV가 적합하다. 복잡한 다중 JOIN이나 비정형 변환이 필요하면 스케줄 쿼리를 써야 한다.

---

## IAM과 행/열 수준 보안

### 기본 IAM 역할

BigQuery의 IAM 역할은 세 단계로 나뉜다:

- **프로젝트 수준**: `roles/bigquery.admin`, `roles/bigquery.dataEditor`, `roles/bigquery.dataViewer`, `roles/bigquery.jobUser`
- **데이터셋 수준**: 데이터셋에 직접 역할을 부여한다. 특정 데이터셋만 접근 가능하게 제한할 때 쓴다.
- **테이블/뷰 수준**: 개별 테이블에 역할을 부여한다.

실무에서 자주 쓰는 조합은 `bigquery.jobUser`(쿼리 실행 권한) + 데이터셋 수준 `dataViewer`다. 쿼리는 돌릴 수 있지만 접근 가능한 데이터셋을 제한하는 패턴이다.

### 열 수준 보안 (Column-level Security)

특정 컬럼에 Policy Tag를 걸어서 접근을 제한한다. Data Catalog의 Policy Tag Taxonomy를 사용한다.

```
 설정 흐름:

 Data Catalog                   BigQuery 테이블
 ┌──────────────────┐           ┌──────────────────────┐
 │ Taxonomy:         │           │ users                │
 │  "PII"           │           │ ├─ user_id           │
 │  ├─ email_tag  ──┼──────────→│ ├─ email   [PII:email]│
 │  ├─ phone_tag  ──┼──────────→│ ├─ phone   [PII:phone]│
 │  └─ ssn_tag      │           │ ├─ name              │
 └──────────────────┘           │ └─ created_at        │
                                └──────────────────────┘

 → email_tag에 Fine-Grained Reader 역할이 없는 사용자는
   SELECT email FROM users 실행 시 "Access Denied" 발생
```

설정 순서:

1. Data Catalog에서 Policy Tag Taxonomy 생성
2. Taxonomy 아래에 개별 Tag 생성 (예: `email`, `phone`)
3. BigQuery 테이블 스키마에서 컬럼에 Policy Tag 연결
4. Tag별로 `roles/datacatalog.categoryFineGrainedReader` 역할을 부여

Policy Tag가 걸린 컬럼은 해당 역할이 없는 사용자가 `SELECT *`를 하면 에러가 난다. 해당 컬럼을 제외한 쿼리는 정상 실행된다.

### 행 수준 보안 (Row-level Security)

테이블의 특정 행만 볼 수 있게 제한한다. 행 액세스 정책(Row Access Policy)을 테이블에 추가하는 방식이다.

```sql
-- region이 'kr'인 행만 볼 수 있는 정책
CREATE ROW ACCESS POLICY korea_only
ON `project.dataset.events`
GRANT TO ('group:kr-team@company.com')
FILTER USING (region = 'kr');

-- 관리자는 모든 행 접근 가능
CREATE ROW ACCESS POLICY admin_all
ON `project.dataset.events`
GRANT TO ('group:admin@company.com')
FILTER USING (TRUE);
```

행 수준 보안이 걸린 테이블에서 정책이 하나라도 존재하면, 정책에 포함되지 않은 사용자는 **아무 행도 볼 수 없다**. 이 점을 모르고 정책을 추가했다가 기존 사용자가 갑자기 데이터를 못 읽게 되는 사고가 발생할 수 있다. 항상 관리자용 `FILTER USING (TRUE)` 정책을 함께 만들어야 한다.

---

## Data Transfer Service

BigQuery Data Transfer Service(DTS)는 외부 데이터 소스에서 BigQuery로 데이터를 자동 적재하는 서비스다.

지원하는 소스:

- **SaaS**: Google Ads, Google Analytics, YouTube, Campaign Manager 등 Google 서비스
- **클라우드 스토리지**: Cloud Storage(GCS)에서 주기적 로드
- **Cross-region 복사**: 다른 리전의 BigQuery 데이터셋 복사
- **서드파티**: Amazon S3, Azure Blob Storage에서 직접 적재

GCS에서 주기적으로 데이터를 로드하는 설정:

```bash
bq mk --transfer_config \
  --project_id=my-project \
  --target_dataset=my_dataset \
  --display_name='daily_gcs_load' \
  --data_source=google_cloud_storage \
  --schedule='every day 03:00' \
  --params='{
    "data_path_template": "gs://my-bucket/data/{run_date}/*.parquet",
    "destination_table_name_template": "raw_events_{run_date}",
    "file_format": "PARQUET",
    "write_disposition": "WRITE_TRUNCATE"
  }'
```

Amazon S3에서 직접 가져오는 것도 가능하다:

```bash
bq mk --transfer_config \
  --project_id=my-project \
  --target_dataset=my_dataset \
  --display_name='s3_import' \
  --data_source=amazon_s3 \
  --schedule='every day 04:00' \
  --params='{
    "data_path": "s3://source-bucket/data/*.csv",
    "destination_table_name_template": "s3_data",
    "file_format": "CSV",
    "access_key_id": "AKIA...",
    "secret_access_key": "..."
  }'
```

S3 적재 시 주의할 점은 네트워크 전송 비용이다. AWS에서 나가는 데이터 전송(egress) 비용은 AWS 쪽에서 과금된다. 대량 데이터를 매일 전송하면 비용이 상당하니 전송량을 계산해야 한다.

DTS는 스케줄 쿼리의 인프라이기도 하다. 스케줄 쿼리를 만들면 내부적으로 DTS의 `scheduled_query` 데이터 소스로 등록된다. 그래서 DTS 콘솔에서 스케줄 쿼리도 함께 관리할 수 있다.

---

## MERGE 패턴: CDC와 SCD Type 2

### MERGE 기본 문법

`MERGE`는 원본(source)과 대상(target) 테이블을 비교해서 INSERT, UPDATE, DELETE를 한 번에 실행하는 SQL 문이다.

```sql
MERGE `project.dataset.users` AS target
USING `project.dataset.users_staging` AS source
ON target.user_id = source.user_id

WHEN MATCHED AND source.is_deleted = true THEN
  DELETE

WHEN MATCHED THEN
  UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.updated_at = source.updated_at

WHEN NOT MATCHED THEN
  INSERT (user_id, name, email, created_at, updated_at)
  VALUES (source.user_id, source.name, source.email, source.created_at, source.updated_at);
```

### CDC(Change Data Capture) 패턴

외부 시스템(MySQL, PostgreSQL 등)의 변경 사항을 BigQuery에 반영하는 일반적인 패턴이다. Debezium이나 Datastream 같은 CDC 도구가 변경 이벤트를 스테이징 테이블에 넣으면, MERGE로 최종 테이블에 반영한다.

```
 CDC 흐름:

 ┌─────────┐    CDC 도구     ┌──────────────┐   MERGE    ┌──────────────┐
 │ MySQL   │ ──(binlog)───→ │ staging      │ ────────→  │ target       │
 │ (원본DB) │    Datastream  │ (변경 이벤트) │            │ (최종 테이블)  │
 └─────────┘               └──────────────┘            └──────────────┘

 staging 테이블 레코드 예시:
 ┌──────────┬──────┬─────────┬─────────────────────┐
 │ user_id  │ name │ op_type │ change_timestamp     │
 ├──────────┼──────┼─────────┼─────────────────────┤
 │ 101      │ Kim  │ INSERT  │ 2026-04-12 10:00:00 │
 │ 102      │ Lee  │ UPDATE  │ 2026-04-12 10:01:00 │
 │ 103      │ Park │ DELETE  │ 2026-04-12 10:02:00 │
 └──────────┴──────┴─────────┴─────────────────────┘
```

같은 키에 대해 여러 변경 이벤트가 쌓일 수 있으니, 가장 최신 이벤트만 MERGE에 사용해야 한다:

```sql
MERGE `project.dataset.users` AS target
USING (
  -- 같은 user_id에 대해 가장 최근 이벤트만 선택
  SELECT * FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY change_timestamp DESC) AS rn
    FROM `project.dataset.users_staging`
    WHERE DATE(change_timestamp) = CURRENT_DATE()
  )
  WHERE rn = 1
) AS source
ON target.user_id = source.user_id

WHEN MATCHED AND source.op_type = 'DELETE' THEN
  DELETE

WHEN MATCHED AND source.op_type = 'UPDATE' THEN
  UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.updated_at = source.change_timestamp

WHEN NOT MATCHED AND source.op_type IN ('INSERT', 'UPDATE') THEN
  INSERT (user_id, name, email, created_at, updated_at)
  VALUES (source.user_id, source.name, source.email, source.change_timestamp, source.change_timestamp);
```

### SCD Type 2 (Slowly Changing Dimension)

변경 이력을 보존해야 하는 경우 사용한다. 기존 행을 업데이트하는 대신, 기존 행을 "종료" 처리하고 새 행을 INSERT한다.

```sql
-- SCD Type 2 테이블 구조
CREATE TABLE `project.dataset.users_scd2` (
  user_id INT64,
  name STRING,
  email STRING,
  effective_from TIMESTAMP,
  effective_to TIMESTAMP,       -- NULL이면 현재 유효한 레코드
  is_current BOOL
)
PARTITION BY DATE(effective_from)
CLUSTER BY user_id;
```

SCD Type 2 MERGE는 두 단계로 진행한다. BigQuery의 MERGE는 같은 target 행에 대해 INSERT와 UPDATE를 동시에 수행할 수 없기 때문이다:

```sql
-- Step 1: 기존 현재 레코드 종료 처리
MERGE `project.dataset.users_scd2` AS target
USING `project.dataset.users_staging` AS source
ON target.user_id = source.user_id
   AND target.is_current = true

WHEN MATCHED AND (target.name != source.name OR target.email != source.email) THEN
  UPDATE SET
    target.effective_to = source.change_timestamp,
    target.is_current = false;

-- Step 2: 신규 레코드 삽입 (변경된 것만)
INSERT INTO `project.dataset.users_scd2`
  (user_id, name, email, effective_from, effective_to, is_current)
SELECT
  s.user_id,
  s.name,
  s.email,
  s.change_timestamp,
  NULL,
  true
FROM `project.dataset.users_staging` s
INNER JOIN `project.dataset.users_scd2` t
  ON s.user_id = t.user_id
WHERE t.effective_to = s.change_timestamp  -- Step 1에서 종료 처리된 행만
  AND t.is_current = false;
```

SCD Type 2 운영 시 주의사항:

- **쿼리 시 항상 `WHERE is_current = true`**: 이걸 빠뜨리면 과거 이력까지 전부 집계에 포함된다. 뷰를 하나 만들어서 현재 레코드만 노출하는 게 안전하다.
- **MERGE DML 쿼터**: 하루 1,500개 제한이 있으니 너무 잦은 주기로 돌리면 쿼터에 걸린다. 보통 시간 단위나 일 단위로 배치 처리한다.
- **파티셔닝 기준**: `effective_from`으로 파티셔닝하면 이력 조회 시 파티션 프루닝이 된다.

---

## BigQuery ML 기초

BigQuery ML(BQML)은 SQL로 머신러닝 모델을 학습하고 예측하는 기능이다. 데이터를 BigQuery 밖으로 꺼내지 않고 SQL만으로 모델을 만들 수 있다.

### 지원 모델 타입

| 모델 타입 | SQL 키워드 | 용도 |
|-----------|-----------|------|
| 선형 회귀 | `LINEAR_REG` | 연속값 예측 (매출, 가격) |
| 로지스틱 회귀 | `LOGISTIC_REG` | 이진/다중 분류 |
| K-Means | `KMEANS` | 클러스터링 |
| XGBoost | `BOOSTED_TREE_CLASSIFIER` / `BOOSTED_TREE_REGRESSOR` | 정형 데이터 분류/회귀 |
| DNN | `DNN_CLASSIFIER` / `DNN_REGRESSOR` | 딥러닝 (Vertex AI 연동) |
| ARIMA+ | `ARIMA_PLUS` | 시계열 예측 |
| 가져온 TensorFlow 모델 | `TENSORFLOW` | 커스텀 모델 서빙 |

### 모델 학습 → 평가 → 예측

```sql
-- 1. 모델 학습: 사용자 이탈 예측
CREATE OR REPLACE MODEL `project.dataset.churn_model`
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['is_churned'],
  auto_class_weights = true,         -- 클래스 불균형 보정
  max_iterations = 20
) AS
SELECT
  total_orders,
  days_since_last_order,
  avg_order_value,
  support_ticket_count,
  is_churned
FROM `project.dataset.user_features`
WHERE signup_date < '2026-01-01';     -- 학습 데이터 범위 지정
```

```sql
-- 2. 모델 평가
SELECT *
FROM ML.EVALUATE(MODEL `project.dataset.churn_model`,
  (
    SELECT
      total_orders,
      days_since_last_order,
      avg_order_value,
      support_ticket_count,
      is_churned
    FROM `project.dataset.user_features`
    WHERE signup_date >= '2026-01-01'    -- 평가용 데이터는 학습과 분리
  )
);
-- 결과: precision, recall, accuracy, f1_score, log_loss, roc_auc 등
```

```sql
-- 3. 예측
SELECT
  user_id,
  predicted_is_churned,
  predicted_is_churned_probs
FROM ML.PREDICT(MODEL `project.dataset.churn_model`,
  (
    SELECT user_id, total_orders, days_since_last_order,
           avg_order_value, support_ticket_count
    FROM `project.dataset.user_features`
    WHERE is_churned IS NULL              -- 아직 이탈하지 않은 사용자
  )
);
```

### 시계열 예측 (ARIMA+)

```sql
-- 일별 매출 시계열 예측
CREATE OR REPLACE MODEL `project.dataset.revenue_forecast`
OPTIONS (
  model_type = 'ARIMA_PLUS',
  time_series_timestamp_col = 'date',
  time_series_data_col = 'daily_revenue',
  auto_arima = true,
  data_frequency = 'DAILY',
  horizon = 30                          -- 30일 예측
) AS
SELECT
  DATE(order_timestamp) AS date,
  SUM(amount) AS daily_revenue
FROM `project.dataset.orders`
WHERE DATE(order_timestamp) BETWEEN '2025-01-01' AND '2026-04-11'
GROUP BY date;

-- 예측 결과 조회
SELECT *
FROM ML.FORECAST(MODEL `project.dataset.revenue_forecast`,
  STRUCT(30 AS horizon, 0.9 AS confidence_level)
);
```

BQML 사용 시 알아야 할 점:

- **비용**: 모델 학습은 온디맨드 기준 스캔 비용 + 학습 비용(모델 타입에 따라 다름)이 발생한다. `LINEAR_REG`와 `LOGISTIC_REG`는 스캔 비용의 일부 수준이지만, `BOOSTED_TREE`나 `DNN`은 학습 비용이 높다.
- **데이터 전처리**: `TRANSFORM` 절로 학습 시 전처리를 정의하면 예측 시에도 같은 전처리가 자동 적용된다. 학습/서빙 간 전처리 불일치(skew) 문제를 방지한다.
- **모델 내보내기**: 학습된 모델을 `ML.EXPORT_MODEL`로 Cloud Storage에 내보내서 Vertex AI나 다른 환경에서 서빙할 수 있다.
- **한계**: BQML은 프로토타이핑이나 간단한 모델에 적합하다. 복잡한 피처 엔지니어링이나 커스텀 아키텍처가 필요하면 Vertex AI Training을 쓰는 게 낫다.
