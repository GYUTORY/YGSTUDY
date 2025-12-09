---
title: ClickHouse
tags: [database, clickhouse, olap, columnar-database]
updated: 2025-12-09
---

# ClickHouse

## 정의

ClickHouse는 OLAP(Online Analytical Processing) 워크로드에 특화된 오픈소스 컬럼형 데이터베이스 관리 시스템이다.

**실무 팁:**
ClickHouse는 분석 쿼리에 특화된 컬럼형 데이터베이스다. 대용량 데이터 분석에 적합하다.

### 특징
- 컬럼형 스토리지: 분석 쿼리에 최적화
- 빠른 쿼리 속도: 초당 수억 개의 행 처리
- 실시간 데이터 처리: 스트리밍 데이터 지원
- 확장성: 수평적 확장 가능

### ClickHouse vs OLTP RDBMS

| 항목 | ClickHouse (OLAP) | MySQL/PostgreSQL (OLTP) |
|------|-------------------|------------------------|
| 저장 방식 | 컬럼형 | 행형 |
| 주요 작업 | 읽기, 집계 | 트랜잭션, CRUD |
| 쿼리 유형 | 분석 쿼리 | 단순 쿼리 |
| 업데이트 | 제한적 | 빈번함 |
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

**장점:**
- I/O 최적화: 필요한 컬럼만 읽음
- 압축 효율: 같은 타입 데이터가 연속으로 저장
- 캐시 효율: CPU 캐시 활용도 증가

**실무 팁:**
컬럼형 스토리지는 분석 쿼리에 효율적이다. 필요한 컬럼만 읽어서 I/O를 줄인다.

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

## 사용법

### 데이터 삽입

```sql
-- 단일 INSERT
INSERT INTO events VALUES (today(), 123, 'click', 1.0);

-- 대량 INSERT
INSERT INTO events SELECT * FROM csv_file;

-- 비동기 INSERT
INSERT INTO events ASYNC SELECT * FROM source;
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
ORDER BY (user_id, date)  -- 자주 사용하는 필터 컬럼
```

**3. PREWHERE (필터 최적화)**
```sql
SELECT * FROM events
PREWHERE date = today()  -- 먼저 필터링
WHERE event_type = 'click';
```

## 예제

### 웹 로그 분석

**실무 팁:**
ClickHouse는 대용량 로그 분석에 적합하다. 파티셔닝과 정렬 키를 적절히 설정한다.

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

-- 분석 쿼리
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

-- 실시간 모니터링
SELECT 
    sensor_id,
    avg(temperature) AS avg_temp,
    max(temperature) AS max_temp
FROM sensor_data
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY sensor_id
HAVING avg_temp > 25;
```

## 참고

### ClickHouse vs 다른 OLAP

| 항목 | ClickHouse | Apache Druid | Apache Pinot |
|------|------------|--------------|--------------|
| 속도 | 매우 빠름 | 빠름 | 빠름 |
| 실시간 | 준실시간 | 실시간 | 실시간 |
| SQL 지원 | 완전 지원 | 제한적 | 제한적 |
| 운영 복잡도 | 낮음 | 중간 | 중간 |
| 확장성 | 높음 | 높음 | 높음 |

### 사용 사례
- 웹 분석 및 로그 분석
- 실시간 대시보드
- IoT 데이터 수집 및 분석

**실무 팁:**
ClickHouse는 OLAP 워크로드에 특화되어 있다. 대용량 데이터 분석, 집계 쿼리에 적합하다.
- 광고 네트워크 분석
- 금융 데이터 분석

### 공식 문서
- [ClickHouse Official Documentation](https://clickhouse.com/docs/)
- [ClickHouse GitHub](https://github.com/ClickHouse/ClickHouse)
