---
title: ClickHouse
tags: [database, clickhouse, olap, columnar-database, distributed]
updated: 2026-03-25
---

# ClickHouse

## 정의

ClickHouse는 OLAP(Online Analytical Processing) 워크로드에 특화된 오픈소스 컬럼형 데이터베이스 관리 시스템이다.
대용량 데이터 분석에 적합하고, 단일 노드에서도 수십억 행을 초 단위로 집계한다.

### 특징
- 컬럼형 스토리지: 분석 쿼리에서 필요한 컬럼만 읽는다
- 초당 수억 행 처리: 벡터화 실행 엔진 기반
- 실시간 데이터 처리: 스트리밍 INSERT 지원
- 수평 확장: 샤딩 + 복제로 클러스터 구성

### ClickHouse vs OLTP RDBMS

| 항목 | ClickHouse (OLAP) | MySQL/PostgreSQL (OLTP) |
|------|-------------------|------------------------|
| 저장 방식 | 컬럼형 | 행형 |
| 주요 작업 | 읽기, 집계 | 트랜잭션, CRUD |
| 쿼리 유형 | 분석 쿼리 | 단순 쿼리 |
| 업데이트 | 제한적 (Mutation) | 빈번함 |
| 데이터 양 | 수 TB~PB | 수 GB~TB |

## 동작 원리

### 컬럼형 스토리지

**행형 스토리지:**
```
Row 1: [ID=1, Name=Alice, Age=25, City=Seoul]
Row 2: [ID=2, Name=Bob, Age=30, City=Busan]
```

**컬럼형 스토리지:**
```
ID:   [1, 2]
Name: [Alice, Bob]
Age:  [25, 30]
City: [Seoul, Busan]
```

컬럼형은 `SELECT avg(Age)` 같은 쿼리에서 Age 컬럼만 읽는다. 행형은 전체 행을 읽어야 하니까 I/O 차이가 크다. 같은 타입 데이터가 연속 저장되므로 압축률도 높다.

## 주요 기능

### 테이블 엔진

**1. MergeTree (기본)**
```sql
CREATE TABLE events (
    date Date,
    user_id UInt32,
    event_type String,
    value Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, date);
```

**2. ReplacingMergeTree (중복 제거)**
```sql
CREATE TABLE user_stats (
    user_id UInt32,
    last_login DateTime,
    login_count UInt32
) ENGINE = ReplacingMergeTree()
ORDER BY user_id;
```

**3. SummingMergeTree (자동 집계)**
```sql
CREATE TABLE page_views (
    date Date,
    page_id UInt32,
    views UInt64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, page_id);
```

### 데이터 타입

| 카테고리 | 타입 | 설명 |
|---------|------|------|
| 정수 | UInt8, UInt16, UInt32, UInt64 | 부호 없는 정수 |
| 정수 | Int8, Int16, Int32, Int64 | 부호 있는 정수 |
| 실수 | Float32, Float64 | 부동소수점 |
| 문자열 | String, FixedString(N) | 가변/고정 길이 |
| 날짜 | Date, DateTime, DateTime64 | 날짜/시간 |
| 배열 | Array(T) | 배열 타입 |
| Nullable | Nullable(T) | NULL 허용 (성능 오버헤드 있음) |
| LowCardinality | LowCardinality(String) | 카디널리티 낮은 문자열에 사전 인코딩 |

`Nullable`은 별도의 null mask 파일이 생기므로 꼭 필요한 컬럼에만 쓴다. `LowCardinality(String)`은 status, country 같은 값의 종류가 수천 개 이하인 컬럼에 쓰면 압축률과 쿼리 속도가 눈에 띄게 좋아진다.

## 사용법

### 데이터 삽입

```sql
-- 단일 INSERT
INSERT INTO events VALUES (today(), 123, 'click', 1.0);

-- 대량 INSERT (파일에서)
INSERT INTO events SELECT * FROM file('data.csv', CSVWithNames);

-- Buffer 테이블 없이 직접 INSERT할 때는 배치 단위를 신경 써야 한다
-- 아래 INSERT 배치 크기 섹션 참고
```

### 쿼리 작성

```sql
-- 기본 집계
SELECT
    toYYYYMM(date) AS month,
    count() AS total_events,
    uniq(user_id) AS unique_users
FROM events
WHERE date >= today() - INTERVAL 30 DAY
GROUP BY month;

-- 시계열 분석
SELECT
    toStartOfHour(timestamp) AS hour,
    avg(value) AS avg_value,
    quantile(0.95)(value) AS p95_value
FROM metrics
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour;
```

### 성능 최적화

**1. 파티셔닝**
```sql
PARTITION BY toYYYYMM(date)  -- 월별 파티션
```

**2. 정렬 키 (ORDER BY)**
```sql
ORDER BY (user_id, date)  -- 자주 사용하는 필터 컬럼을 앞에
```

정렬 키의 첫 번째 컬럼이 가장 중요하다. WHERE 절에서 자주 쓰는 컬럼을 앞에 놓되, 카디널리티가 너무 높은 컬럼(UUID 등)은 피한다.

**3. PREWHERE (필터 최적화)**
```sql
SELECT * FROM events
PREWHERE date = today()  -- 먼저 필터링하여 I/O 줄임
WHERE event_type = 'click';
```

ClickHouse는 `WHERE`를 자동으로 `PREWHERE`로 변환하는 경우가 많다. 명시적으로 쓸 때는 선택도가 높은(대부분의 행을 걸러내는) 조건을 `PREWHERE`에 넣는다.

## 예제

### 웹 로그 분석

```sql
CREATE TABLE web_logs (
    timestamp DateTime,
    user_id UInt32,
    url String,
    response_time UInt32,
    status_code UInt16
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp);

-- 일별 요청 분석
SELECT
    toStartOfDay(timestamp) AS day,
    count() AS requests,
    avg(response_time) AS avg_response,
    quantile(0.95)(response_time) AS p95
FROM web_logs
WHERE timestamp >= today() - INTERVAL 7 DAY
GROUP BY day
ORDER BY day;
```

### IoT 센서 데이터

```sql
CREATE TABLE sensor_data (
    timestamp DateTime64(3),
    sensor_id UInt32,
    temperature Float32,
    humidity Float32,
    location String
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (sensor_id, timestamp);

SELECT
    sensor_id,
    avg(temperature) AS avg_temp,
    max(temperature) AS max_temp
FROM sensor_data
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY sensor_id
HAVING avg_temp > 25;
```

---

## MergeTree 엔진 계열 심화

MergeTree는 ClickHouse의 핵심 엔진이다. 파생 엔진들은 백그라운드 병합(merge) 시 추가 처리를 수행한다.

### 엔진 계열 비교

| 엔진 | 병합 시 동작 | 적합한 용도 |
|------|------------|----------|
| `MergeTree` | 단순 병합 | 기본 이벤트 로그 |
| `ReplacingMergeTree` | 같은 정렬 키의 중복 행 제거 (최신 버전 유지) | 최신 상태 스냅샷 |
| `SummingMergeTree` | 같은 정렬 키의 수치 컬럼 합산 | 카운터, 누적 집계 |
| `AggregatingMergeTree` | 집계 상태(State) 병합 | Materialized View와 결합 |
| `CollapsingMergeTree` | Sign 컬럼 기반 행 취소 | 변경 이벤트 스트림 |
| `VersionedCollapsingMergeTree` | CollapsingMergeTree + 버전 관리 | 동시 업데이트 환경 |

### ReplacingMergeTree — 최신 상태 유지

```sql
CREATE TABLE user_profiles (
    user_id  UInt64,
    name     String,
    email    String,
    updated_at DateTime
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY user_id;

-- 업데이트: 새 행을 INSERT하면 병합 시 최신 행만 남음
INSERT INTO user_profiles VALUES (1, 'Alice', 'alice@old.com', '2024-01-01 00:00:00');
INSERT INTO user_profiles VALUES (1, 'Alice', 'alice@new.com', '2024-06-01 00:00:00');

-- 병합 전에는 두 행이 보일 수 있음 → FINAL로 중복 제거
SELECT * FROM user_profiles FINAL WHERE user_id = 1;
```

`FINAL`은 쿼리 시점에 병합을 강제하므로 대량 데이터에서는 느리다. 서비스 쿼리에서 `FINAL`을 쓰기 어려우면 `argMax`를 쓴다:

```sql
SELECT
    user_id,
    argMax(name, updated_at) AS name,
    argMax(email, updated_at) AS email
FROM user_profiles
GROUP BY user_id;
```

### SummingMergeTree — 자동 집계

```sql
CREATE TABLE page_daily_views (
    date    Date,
    page_id UInt32,
    views   UInt64,
    clicks  UInt64
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, page_id);

INSERT INTO page_daily_views VALUES ('2024-01-01', 1, 100, 10);
INSERT INTO page_daily_views VALUES ('2024-01-01', 1, 200, 20);
-- 병합 후: ('2024-01-01', 1, 300, 30)

-- 병합 전에도 정확한 합계를 보려면 sum() 사용
SELECT date, page_id, sum(views), sum(clicks)
FROM page_daily_views
GROUP BY date, page_id;
```

### AggregatingMergeTree + Materialized View

```sql
-- 원본 테이블
CREATE TABLE events (
    timestamp DateTime,
    user_id   UInt64,
    event     String,
    value     Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp);

-- 집계 상태 저장 테이블
CREATE TABLE events_hourly_agg (
    hour       DateTime,
    event      String,
    cnt        AggregateFunction(count),
    avg_value  AggregateFunction(avg, Float64),
    p95_value  AggregateFunction(quantile(0.95), Float64)
) ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, event);

-- Materialized View: INSERT 시 자동으로 집계 상태 업데이트
CREATE MATERIALIZED VIEW events_hourly_mv
TO events_hourly_agg AS
SELECT
    toStartOfHour(timestamp) AS hour,
    event,
    countState()                    AS cnt,
    avgState(value)                 AS avg_value,
    quantileState(0.95)(value)      AS p95_value
FROM events
GROUP BY hour, event;

-- 조회: Merge 함수로 집계 상태 병합
SELECT
    hour,
    event,
    countMerge(cnt)              AS total_count,
    avgMerge(avg_value)          AS avg,
    quantileMerge(0.95)(p95_value) AS p95
FROM events_hourly_agg
WHERE hour >= now() - INTERVAL 24 HOUR
GROUP BY hour, event
ORDER BY hour;
```

---

## 파티셔닝 키 설계 패턴

```sql
-- 월별 파티션 (일반적인 로그)
PARTITION BY toYYYYMM(timestamp)

-- 일별 파티션 (고빈도 데이터, 짧은 보관 주기)
PARTITION BY toYYYYMMDD(timestamp)

-- 다중 파티션 (지역별 + 월별)
PARTITION BY (region, toYYYYMM(timestamp))

-- 주의: 파티션이 너무 많으면 성능 저하
-- 권장: 파티션당 최소 수백만 행, 총 파티션 수 < 1000
```

### 파티션 관리

```sql
-- 오래된 파티션 삭제 (데이터 보관 정책)
ALTER TABLE events DROP PARTITION '202301';

-- 파티션 확인
SELECT partition, rows, bytes_on_disk
FROM system.parts
WHERE table = 'events' AND active = 1
ORDER BY partition;

-- TTL로 자동 삭제
ALTER TABLE events MODIFY TTL timestamp + INTERVAL 90 DAY;
```

---

## 클러스터와 분산 테이블

단일 노드로 운영하다가 데이터가 수 TB를 넘거나 가용성이 필요해지면 클러스터 구성이 필요하다.

### 클러스터 구성 개념

ClickHouse 클러스터는 **샤드(Shard)**와 **레플리카(Replica)**로 구성된다.

```
클러스터 예시 (2샤드 x 2레플리카)

Shard 1: [node1 (replica 1), node2 (replica 2)]
Shard 2: [node3 (replica 1), node4 (replica 2)]
```

- 샤드: 데이터를 수평 분할한다. 각 샤드는 전체 데이터의 일부를 갖는다
- 레플리카: 같은 샤드의 데이터를 복제한다. 장애 시 다른 레플리카가 대신 응답한다

### config.xml 클러스터 설정

```xml
<clickhouse>
  <remote_servers>
    <my_cluster>
      <shard>
        <replica>
          <host>node1</host>
          <port>9000</port>
        </replica>
        <replica>
          <host>node2</host>
          <port>9000</port>
        </replica>
      </shard>
      <shard>
        <replica>
          <host>node3</host>
          <port>9000</port>
        </replica>
        <replica>
          <host>node4</host>
          <port>9000</port>
        </replica>
      </shard>
    </my_cluster>
  </remote_servers>
</clickhouse>
```

### ReplicatedMergeTree — 복제 엔진

로컬 테이블을 각 노드에 만들 때 `ReplicatedMergeTree`를 쓴다. ZooKeeper(또는 ClickHouse Keeper)가 복제 메타데이터를 관리한다.

```sql
-- 각 노드에서 실행 (매크로로 노드별 값 자동 치환)
CREATE TABLE events_local ON CLUSTER my_cluster (
    timestamp DateTime,
    user_id   UInt64,
    event     String,
    value     Float64
) ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events',  -- ZooKeeper 경로
    '{replica}'                            -- 레플리카 식별자
)
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp);
```

`{shard}`와 `{replica}`는 각 노드의 `macros` 설정에서 치환된다:

```xml
<!-- node1의 config -->
<macros>
    <shard>01</shard>
    <replica>node1</replica>
</macros>
```

### Distributed 테이블 — 분산 쿼리 라우팅

`Distributed` 엔진은 데이터를 직접 저장하지 않는다. 쿼리를 각 샤드의 로컬 테이블로 분산하고 결과를 합친다.

```sql
CREATE TABLE events_distributed ON CLUSTER my_cluster (
    timestamp DateTime,
    user_id   UInt64,
    event     String,
    value     Float64
) ENGINE = Distributed(
    'my_cluster',          -- 클러스터 이름
    'default',             -- 데이터베이스
    'events_local',        -- 로컬 테이블
    sipHash64(user_id)     -- 샤딩 키
);
```

**INSERT 경로:**

```sql
-- Distributed 테이블에 INSERT → 내부적으로 샤딩 키 기반 라우팅
INSERT INTO events_distributed VALUES (now(), 123, 'click', 1.0);
```

Distributed INSERT는 중간에 비동기 전송 큐를 거친다. 대량 INSERT에서는 각 노드의 로컬 테이블에 직접 INSERT하는 것이 안정적이다. Distributed INSERT 중 노드 장애가 나면 큐에 쌓인 데이터가 유실될 수 있다.

**샤딩 키 선택 시 주의:**

- `rand()`를 쓰면 데이터가 골고루 분산되지만, 같은 user_id의 데이터가 여러 샤드에 흩어진다
- `sipHash64(user_id)`를 쓰면 같은 사용자 데이터가 한 샤드에 모인다. JOIN이나 GROUP BY에서 유리하다
- 핫스팟을 만드는 키(날짜, 특정 ID)는 피한다

---

## JOIN 주의사항과 Dictionary

### JOIN이 느린 이유

ClickHouse의 기본 JOIN은 오른쪽 테이블 전체를 메모리에 올린다(hash join). 오른쪽 테이블이 크면 `Memory limit exceeded`가 뜬다.

```sql
-- 오른쪽 테이블이 작을 때는 문제 없음
SELECT e.*, u.name
FROM events e
JOIN users u ON e.user_id = u.user_id;

-- 오른쪽 테이블이 수천만 행이면 메모리 부족
SELECT a.*, b.amount
FROM large_table_a a
JOIN large_table_b b ON a.order_id = b.order_id;
```

### JOIN 메모리 문제 대응

```sql
-- 1. join_algorithm 변경 (메모리 초과 시 디스크 사용)
SET join_algorithm = 'partial_merge';

-- 2. 오른쪽 테이블을 서브쿼리로 축소
SELECT e.*, u.name
FROM events e
JOIN (
    SELECT user_id, name FROM users WHERE active = 1
) u ON e.user_id = u.user_id;

-- 3. max_bytes_in_join 설정
SET max_bytes_in_join = 10000000000;  -- 10GB
SET join_overflow_mode = 'throw';     -- 초과 시 에러 (기본값)
```

### Dictionary — JOIN 대체

조회용 작은 테이블(사용자 정보, 코드 매핑 등)은 Dictionary로 만들면 JOIN 없이 함수 호출로 조회한다. 메모리에 올려두고 주기적으로 갱신한다.

```sql
-- Dictionary 생성 (MySQL 원본)
CREATE DICTIONARY user_dict (
    user_id UInt64,
    name    String,
    country String
) PRIMARY KEY user_id
SOURCE(MYSQL(
    host 'mysql-host' port 3306
    user 'reader' password 'pass'
    db 'mydb' table 'users'
))
LAYOUT(HASHED())              -- 메모리에 해시맵으로 적재
LIFETIME(MIN 300 MAX 600);    -- 5~10분마다 갱신

-- ClickHouse 테이블에서 조회
CREATE DICTIONARY user_dict (
    user_id UInt64,
    name    String,
    country String
) PRIMARY KEY user_id
SOURCE(CLICKHOUSE(
    host 'localhost' port 9000
    db 'default' table 'users'
))
LAYOUT(HASHED())
LIFETIME(MIN 300 MAX 600);
```

```sql
-- Dictionary 사용: JOIN 대신 dictGet 함수
SELECT
    user_id,
    event,
    dictGet('user_dict', 'name', user_id) AS user_name,
    dictGet('user_dict', 'country', user_id) AS country
FROM events
WHERE timestamp >= today();
```

Dictionary의 장점:
- JOIN보다 빠르다 (이미 메모리에 올라와 있으니까)
- 쿼리가 단순해진다
- 여러 테이블에서 같은 Dictionary를 재사용한다

Dictionary의 제약:
- 원본 데이터가 수천만 행 이상이면 메모리 사용량이 크다
- `LAYOUT(HASHED())`는 전체를 메모리에 올리고, `LAYOUT(CACHE(SIZE_IN_CELLS 1000000))`은 LRU 캐시 방식이다
- 원본이 변경되어도 `LIFETIME` 주기까지는 반영되지 않는다

---

## UPDATE/DELETE 제약 — Mutation

ClickHouse에서 `UPDATE`와 `DELETE`는 OLTP DB와 완전히 다르게 동작한다. Mutation이라는 비동기 백그라운드 작업으로 처리되며, 파트 전체를 다시 쓴다.

### 기본 문법

```sql
-- DELETE
ALTER TABLE events DELETE WHERE date < '2023-01-01';

-- UPDATE
ALTER TABLE events UPDATE value = 0 WHERE event_type = 'test';
```

### Mutation이 느린 이유

Mutation은 해당 파티션의 모든 파트를 다시 쓴다. 1억 행 테이블에서 1행을 UPDATE해도 파트 전체가 재작성된다. 빈번한 UPDATE/DELETE가 필요하면 ClickHouse는 적합하지 않다.

### Mutation 상태 확인

```sql
SELECT
    database,
    table,
    mutation_id,
    command,
    create_time,
    is_done,
    latest_fail_reason
FROM system.mutations
WHERE is_done = 0;
```

`is_done = 0`인 Mutation이 쌓이면 디스크 I/O가 치솟는다. Mutation을 취소하려면:

```sql
KILL MUTATION WHERE mutation_id = 'mutation_0000000001';
```

### Mutation 대신 쓸 수 있는 방법

- **데이터 삭제**: `ALTER TABLE DROP PARTITION`이 훨씬 빠르다. 파티셔닝을 잘 설계해두면 Mutation 없이 오래된 데이터를 지울 수 있다
- **데이터 갱신**: `ReplacingMergeTree`로 새 행을 INSERT하고 병합 시 이전 행을 제거한다
- **논리 삭제**: `is_deleted` 컬럼을 두고 쿼리에서 필터링한다

### Lightweight Delete (23.3+)

```sql
-- 비동기 Mutation이 아닌, 마스크 기반 삭제
DELETE FROM events WHERE event_type = 'test';
```

Lightweight Delete는 실제 데이터를 즉시 지우지 않고 삭제 마스크를 남긴다. 쿼리 시 마스크된 행을 건너뛴다. 기존 Mutation DELETE보다 빠르지만 디스크 공간은 병합 후에 회수된다.

---

## Buffer 테이블과 INSERT 배치 크기

### INSERT 배치 크기가 중요한 이유

ClickHouse는 INSERT마다 새 파트(part)를 만든다. 1행짜리 INSERT를 초당 수백 번 하면 파트 수가 폭증하고, `Too many parts` 에러가 발생한다.

**권장 배치 크기:**
- 최소 1,000행 이상, 이상적으로는 10,000~100,000행 단위
- INSERT 주기는 1초에 1번 이하

```sql
-- 나쁜 예: 행 하나씩 INSERT
INSERT INTO events VALUES (now(), 1, 'click', 1.0);  -- 파트 1개 생성
INSERT INTO events VALUES (now(), 2, 'click', 1.0);  -- 파트 1개 생성
-- ... 반복하면 파트 폭증

-- 좋은 예: 배치 INSERT
INSERT INTO events VALUES
    (now(), 1, 'click', 1.0),
    (now(), 2, 'click', 1.0),
    (now(), 3, 'view', 2.0);
```

### Buffer 테이블

애플리케이션에서 배치 처리가 어려울 때 Buffer 테이블이 중간 버퍼 역할을 한다.

```sql
CREATE TABLE events_buffer AS events
ENGINE = Buffer(
    'default',       -- 데이터베이스
    'events',        -- 대상 테이블
    16,              -- num_layers (병렬 버퍼 수)
    10, 100,         -- min_time, max_time (초)
    10000, 100000,   -- min_rows, max_rows
    10000000, 100000000  -- min_bytes, max_bytes
);
```

Buffer 테이블에 INSERT하면 메모리에 버퍼링되다가 조건(시간, 행 수, 바이트)을 만족하면 대상 테이블에 플러시한다.

**Buffer 테이블의 함정:**
- 서버 재시작 시 버퍼에 있던 데이터가 유실된다
- 대상 테이블의 스키마를 변경하면 Buffer 테이블을 다시 만들어야 한다
- Materialized View는 Buffer 테이블의 플러시를 트리거로 인식하지 않는 경우가 있다
- Buffer에 있는 데이터는 `system.parts`에 안 보이므로 모니터링에서 빠진다

실무에서는 Buffer 테이블보다 애플리케이션 레벨에서 배치를 모아서 INSERT하는 것이 안정적이다. Kafka 엔진을 사용해 Kafka consumer가 배치 단위로 가져오는 방식도 많이 쓴다.

### async_insert (21.11+)

Buffer 테이블의 대안으로, 서버 레벨에서 INSERT를 모아서 처리한다.

```sql
-- 서버 설정 또는 세션 레벨
SET async_insert = 1;
SET wait_for_async_insert = 1;      -- INSERT 응답을 플러시까지 대기
SET async_insert_max_data_size = 10000000;  -- 10MB마다 플러시
SET async_insert_busy_timeout_ms = 1000;    -- 1초마다 플러시
```

Buffer 테이블과 달리 WAL이 있어서 서버 재시작 시 데이터 유실 위험이 적다. 신규 구성이라면 Buffer 테이블보다 `async_insert`를 쓴다.

---

## system 테이블 기반 모니터링

ClickHouse는 내부 상태를 `system.*` 테이블로 노출한다. 별도 모니터링 에이전트 없이도 SQL로 확인 가능하다.

### 파트 상태 확인

```sql
-- 테이블별 파트 수, 행 수, 디스크 사용량
SELECT
    database,
    table,
    count() AS parts,
    sum(rows) AS total_rows,
    formatReadableSize(sum(bytes_on_disk)) AS disk_size
FROM system.parts
WHERE active = 1
GROUP BY database, table
ORDER BY parts DESC;
```

파트 수가 테이블당 수백 개를 넘어가면 쿼리 성능이 떨어지고 `Too many parts` 위험이 생긴다.

### 쿼리 로그 분석

```sql
-- 최근 느린 쿼리 Top 10
SELECT
    query_id,
    user,
    query_duration_ms,
    read_rows,
    formatReadableSize(read_bytes) AS read_size,
    formatReadableSize(memory_usage) AS memory,
    query
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_date = today()
  AND query_duration_ms > 1000
ORDER BY query_duration_ms DESC
LIMIT 10;
```

### 복제 상태 확인

```sql
-- 레플리카 지연 확인
SELECT
    database,
    table,
    replica_name,
    is_leader,
    absolute_delay,       -- 복제 지연 (초)
    queue_size,           -- 대기 중인 복제 작업
    inserts_in_queue,
    merges_in_queue,
    last_queue_update
FROM system.replicas
WHERE absolute_delay > 0 OR queue_size > 0
ORDER BY absolute_delay DESC;
```

`absolute_delay`가 수십 초 이상이면 복제가 밀리고 있다는 뜻이다. ZooKeeper/Keeper 상태와 네트워크를 확인한다.

### 현재 실행 중인 쿼리

```sql
SELECT
    query_id,
    user,
    elapsed,
    formatReadableSize(memory_usage) AS memory,
    query
FROM system.processes
ORDER BY elapsed DESC;

-- 문제 쿼리 강제 종료
KILL QUERY WHERE query_id = 'xxx';
```

### Merge 작업 확인

```sql
SELECT
    database,
    table,
    elapsed,
    progress,
    num_parts,
    formatReadableSize(total_size_bytes_compressed) AS size
FROM system.merges;
```

---

## 자주 겪는 에러와 트러블슈팅

### Too many parts (300 error)

**증상:** `DB::Exception: Too many parts (600). Merges are processing significantly slower than inserts`

**원인:** INSERT가 너무 잦거나 배치가 너무 작아서 파트가 쌓인다. 백그라운드 병합이 INSERT 속도를 따라가지 못한다.

**확인:**
```sql
SELECT
    database,
    table,
    count() AS active_parts,
    max(modification_time) AS last_modified
FROM system.parts
WHERE active = 1
GROUP BY database, table
HAVING active_parts > 200
ORDER BY active_parts DESC;
```

**해결:**
1. INSERT 배치 크기를 키운다 (최소 수천 행 단위)
2. INSERT 빈도를 줄인다 (초당 1회 이하)
3. `async_insert`를 켠다
4. `parts_to_delay_insert`, `parts_to_throw_insert` 임계값을 확인한다
5. 급한 경우 수동 병합을 실행한다:
```sql
OPTIMIZE TABLE events FINAL;
-- FINAL은 모든 파트를 하나로 합침. 대용량 테이블에서는 수 시간 걸릴 수 있음
-- 파티션 단위로 하는 게 안전함
OPTIMIZE TABLE events PARTITION '202403';
```

### Memory limit exceeded

**증상:** `DB::Exception: Memory limit (for query) exceeded: would use 10.00 GiB (attempt to allocate chunk of 4194304 bytes), maximum: 9.31 GiB`

**원인:** JOIN에서 오른쪽 테이블이 크거나, GROUP BY의 카디널리티가 높거나, 정렬 대상이 너무 많다.

**확인:**
```sql
-- 어떤 쿼리가 메모리를 많이 쓰는지
SELECT
    query_id,
    formatReadableSize(memory_usage) AS peak_memory,
    query
FROM system.query_log
WHERE type = 'ExceptionWhileProcessing'
  AND event_date = today()
ORDER BY memory_usage DESC
LIMIT 10;
```

**해결:**
```sql
-- 1. 쿼리별 메모리 제한 조정
SET max_memory_usage = 20000000000;  -- 20GB

-- 2. GROUP BY 시 디스크 스필 허용
SET max_bytes_before_external_group_by = 10000000000;  -- 10GB 초과 시 디스크 사용

-- 3. ORDER BY 시 디스크 스필 허용
SET max_bytes_before_external_sort = 10000000000;

-- 4. JOIN 알고리즘 변경
SET join_algorithm = 'partial_merge';  -- 메모리 초과 시 디스크 사용
```

근본적으로는 쿼리를 개선한다. 불필요한 컬럼을 빼고, 서브쿼리에서 미리 필터링하고, GROUP BY 키의 카디널리티를 줄인다.

### ZooKeeper/Keeper 관련 에러

**증상:** `Code: 999. Coordination::Exception: Connection loss` 또는 복제 지연이 계속 증가

**원인:** ZooKeeper/Keeper 노드 장애, 네트워크 문제, 또는 znode 수 초과

**확인:**
```sql
-- ZooKeeper 연결 상태
SELECT * FROM system.zookeeper WHERE path = '/';

-- 복제 큐 확인
SELECT
    database,
    table,
    type,
    create_time,
    source_replica,
    num_tries,
    last_exception
FROM system.replication_queue
WHERE num_tries > 0
ORDER BY create_time;
```

**해결:**
- Keeper/ZooKeeper 노드의 메모리, 디스크, 네트워크 상태 확인
- `jute.maxbuffer` 크기 확인 (대용량 znode 전송 실패 시)
- 오래된 테이블의 znode가 쌓여 있으면 정리
- ClickHouse Keeper는 ZooKeeper보다 운영이 간단하고, ClickHouse 23.x 이후로는 Keeper 사용을 권장

### Distributed 테이블 INSERT 실패

**증상:** `DB::Exception: Shard is not available` 또는 `Too many pending inserts`

**원인:** 대상 샤드 노드가 다운되었거나 비동기 전송 큐가 가득 찼다.

**확인:**
```sql
-- Distributed 전송 큐 확인
SELECT * FROM system.distribution_queue;
```

**해결:**
- 대상 노드 상태 확인
- `distributed_directory_monitor_batch_inserts = 1` 설정으로 전송 효율 개선
- 안정적인 INSERT가 필요하면 Distributed 테이블 대신 로컬 테이블에 직접 INSERT

### Merge가 끝나지 않음

**증상:** `system.merges`에 merge 작업이 오래 걸림. 디스크 I/O 100%.

**확인:**
```sql
SELECT
    database,
    table,
    elapsed,
    progress,
    num_parts,
    formatReadableSize(total_size_bytes_compressed) AS size,
    formatReadableSize(memory_usage) AS memory
FROM system.merges
WHERE elapsed > 600;  -- 10분 이상
```

**해결:**
- `OPTIMIZE TABLE FINAL`을 운영 중에 돌리면 이런 상황이 생긴다. 파티션 단위로 나눠서 실행
- `max_bytes_to_merge_at_max_space_in_pool` 값을 확인 (기본 150GB)
- 디스크 여유 공간 확인. 병합 시 원본 + 결과 파트 양만큼 공간이 필요하다

---

## 참고

### ClickHouse vs 다른 OLAP

| 항목 | ClickHouse | Apache Druid | Apache Pinot |
|------|------------|--------------|--------------|
| 속도 | 매우 빠름 | 빠름 | 빠름 |
| 실시간 | 준실시간 | 실시간 | 실시간 |
| SQL 지원 | 완전 지원 | 제한적 | 제한적 |
| 운영 복잡도 | 낮음 (단일 노드) ~ 중간 (클러스터) | 중간 | 중간 |
| 확장성 | 높음 | 높음 | 높음 |

### 사용 사례
- 웹 분석 및 로그 분석
- 실시간 대시보드
- IoT 데이터 수집 및 분석
- 광고 네트워크 분석
- 금융 데이터 분석

### 공식 문서
- [ClickHouse Official Documentation](https://clickhouse.com/docs/)
- [ClickHouse GitHub](https://github.com/ClickHouse/ClickHouse)
