---
title: ClickHouse - 고성능 컬럼형 분석 데이터베이스
tags: [database, rdbms, clickhouse, olap, analytics, columnar-database, sql]
updated: 2025-11-01
---

# ClickHouse

## 📋 목차

1. [ClickHouse란 무엇인가?](#clickhouse란-무엇인가)
2. [핵심 아키텍처](#핵심-아키텍처)
3. [컬럼형 스토리지의 원리](#컬럼형-스토리지의-원리)
4. [테이블 엔진](#테이블-엔진)
5. [데이터 타입과 함수](#데이터-타입과-함수)
6. [쿼리 최적화](#쿼리-최적화)
7. [분산 처리와 복제](#분산-처리와-복제)
8. [실무 활용 사례](#실무-활용-사례)
9. [성능 튜닝 전략](#성능-튜닝-전략)
10. [운영 및 모니터링](#운영-및-모니터링)
11. [참고 자료](#참고-자료)

---

## ClickHouse란 무엇인가?

ClickHouse는 **초고속 OLAP(Online Analytical Processing) 분석을 위한 오픈소스 컬럼형(Columnar) 관계형 데이터베이스**입니다. SQL을 사용하며, 수십억 건의 데이터를 실시간으로 분석하고 집계하는 데 특화되어 있습니다. 전통적인 OLTP RDBMS보다 100~1000배 빠른 쿼리 성능을 제공합니다.

### ClickHouse의 분류

**관계형 데이터베이스 (RDBMS)**
- SQL 쿼리 언어 사용
- 테이블과 컬럼 기반 스키마
- JOIN, GROUP BY 등 관계형 연산 지원
- ACID 특성 부분 지원

**하지만 전통적 OLTP RDBMS와는 다른 특징:**
- 컬럼형 스토리지 (행형이 아닌)
- OLAP에 최적화 (OLTP가 아닌)
- 배치 삽입 권장 (개별 트랜잭션 비효율적)
- UPDATE/DELETE 제한적 (권장 안 함)

### ClickHouse의 탄생 배경

**Yandex의 과제**

2016년, 러시아의 검색 엔진 기업 Yandex는 자사의 웹 분석 서비스인 **Yandex.Metrica**를 운영하면서 심각한 성능 문제에 직면했습니다:

```
문제 상황:
- 일일 200억 건 이상의 이벤트 데이터 수집
- 수조 건의 히스토리 데이터 분석 필요
- 실시간 대시보드 요구사항 (1초 이내 응답)
- 기존 RDBMS는 수십 분~수 시간 소요
```

**기존 솔루션의 한계**

- **MySQL/PostgreSQL**: 대규모 집계 쿼리에서 성능 한계
- **MongoDB**: 복잡한 분석 쿼리 지원 부족
- **Hadoop/Hive**: 배치 처리에는 적합하나 실시간 쿼리 불가
- **상용 솔루션**: 높은 라이센스 비용과 하드웨어 요구사항

**ClickHouse의 설계 목표**

```
1. 초고속 집계 쿼리 (수십억 건을 1초 이내)
2. 선형적 확장성 (서버 추가 시 성능 비례 증가)
3. 실시간 데이터 삽입 (배치 없이 즉시 쿼리 가능)
4. SQL 호환성 (학습 곡선 최소화)
5. 하드웨어 효율성 (일반 서버에서 동작)
```

### ClickHouse의 핵심 철학

**"빠름을 위한 모든 것"**

ClickHouse의 모든 설계 결정은 **성능 최우선**을 기반으로 합니다:

```
컬럼형 스토리지: 분석 쿼리에 최적화
벡터화 처리: CPU SIMD 명령어 활용
데이터 압축: I/O 최소화
병렬 처리: 모든 CPU 코어 활용
분산 처리: 수백 대 서버로 확장
```

### ClickHouse vs 전통적 OLTP RDBMS

ClickHouse는 **OLAP에 특화된 컬럼형 RDBMS**이고, MySQL/PostgreSQL은 **OLTP에 특화된 행형 RDBMS**입니다.

| 특성 | ClickHouse (OLAP) | MySQL/PostgreSQL (OLTP) |
|------|-------------------|------------------------|
| **데이터베이스 유형** | 관계형 (SQL 사용) | 관계형 (SQL 사용) |
| **저장 방식** | 컬럼형 (Columnar) | 행형 (Row-based) |
| **최적화 대상** | 읽기/분석 (OLAP) | 트랜잭션 (OLTP) |
| **쿼리 성능** | 수십억 건을 초 단위 | 수백만 건이 한계 |
| **쓰기 방식** | 배치 삽입 권장 | 개별 트랜잭션 최적화 |
| **UPDATE/DELETE** | 비효율적 (권장 안 함) | 효율적 (ACID 보장) |
| **JOIN 성능** | 제한적 | 우수 |
| **압축률** | 10:1 ~ 100:1 | 3:1 ~ 5:1 |
| **확장성** | 수평 확장 (선형) | 수직 확장 주로 |
| **트랜잭션** | 제한적 | 완전한 ACID |

**핵심 차이:**
```
OLTP (MySQL, PostgreSQL):
- 개별 행 CRUD 최적화
- 트랜잭션 보장 (ACID)
- 정규화된 스키마
- 예: 주문 처리, 사용자 관리

OLAP (ClickHouse):
- 대량 집계 최적화
- 비정규화된 스키마
- 배치 처리 중심
- 예: 로그 분석, BI 대시보드
```

### 언제 ClickHouse를 사용해야 하는가?

**✅ ClickHouse가 적합한 경우**

```
1. 대규모 로그 분석
   - 웹 서버 로그 (일 수억 건)
   - 애플리케이션 이벤트 로그
   - 보안 감사 로그

2. 실시간 대시보드
   - 비즈니스 인텔리전스 (BI)
   - 사용자 행동 분석
   - 실시간 메트릭 집계

3. 시계열 데이터
   - IoT 센서 데이터
   - 모니터링 메트릭
   - 금융 시계열 데이터

4. 대규모 데이터 웨어하우스
   - 수조 건의 히스토리 데이터
   - 복잡한 집계 쿼리
   - Ad-hoc 분석
```

**❌ ClickHouse가 부적합한 경우**

```
1. 트랜잭션 처리 (OLTP)
   - 온라인 뱅킹 시스템
   - 전자상거래 주문 처리
   - 빈번한 UPDATE/DELETE 필요

2. Key-Value 조회
   - 단일 행 조회가 주
   - 캐싱이 더 적합
   - Redis, Memcached 권장

3. 복잡한 JOIN
   - 다중 테이블 조인이 많음
   - 정규화된 스키마
   - 전통적 RDBMS 권장

4. 소규모 데이터
   - 데이터가 수백만 건 이하
   - 복잡도 대비 이점 없음
   - PostgreSQL 등으로 충분
```

---

## 핵심 아키텍처

### 컴포넌트 구조

ClickHouse는 단순하면서도 강력한 아키텍처를 가지고 있습니다:

```
┌─────────────────────────────────────┐
│         Client Applications         │
│  (JDBC, ODBC, HTTP, CLI, Python)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Query Parser & Analyzer      │
│     (SQL → AST → Logical Plan)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Query Optimizer              │
│   (Cost-based, Rule-based)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        Distributed Execution        │
│  (Parallel Processing, Sharding)    │
└─────┬──────────────────────┬────────┘
      │                      │
┌─────▼──────┐        ┌─────▼──────┐
│  Storage   │        │  Storage   │
│  Engine    │        │  Engine    │
│ (MergeTree)│   ...  │ (MergeTree)│
└────────────┘        └────────────┘
      │                      │
┌─────▼──────────────────────▼────────┐
│      Columnar Data Storage          │
│    (Compressed, Partitioned)        │
└─────────────────────────────────────┘
```

### 단일 서버 아키텍처

**프로세스 구조:**

```
clickhouse-server (단일 프로세스)
├─ TCP Handler (9000 포트)
│  └─ 네이티브 프로토콜 처리
├─ HTTP Handler (8123 포트)
│  └─ REST API, 웹 UI
├─ Query Processor
│  ├─ Parser
│  ├─ Optimizer
│  └─ Executor (멀티스레드)
├─ Storage Manager
│  ├─ Table Engines
│  └─ Parts 관리
└─ Background Tasks
   ├─ Merge (데이터 병합)
   ├─ Mutation (업데이트/삭제)
   └─ Replication (복제)
```

**메모리 구조:**

```
RAM 사용:
├─ Query Memory (쿼리 실행)
│  └─ max_memory_usage: 쿼리당 메모리 제한
├─ Mark Cache (인덱스 캐시)
│  └─ 기본값: 5GB
├─ Uncompressed Cache (데이터 캐시)
│  └─ 기본값: 0 (비활성화)
└─ Background Merge Memory
   └─ 백그라운드 작업용
```

### 데이터 저장 구조

**디렉토리 레이아웃:**

```
/var/lib/clickhouse/
├─ data/
│  └─ database_name/
│     └─ table_name/
│        ├─ 20240101_1_1_0/  (파티션)
│        │  ├─ primary.idx   (기본키 인덱스)
│        │  ├─ column1.bin   (압축된 컬럼 데이터)
│        │  ├─ column1.mrk2  (마크 파일)
│        │  ├─ column2.bin
│        │  ├─ column2.mrk2
│        │  └─ checksums.txt (체크섬)
│        ├─ 20240101_2_2_0/
│        └─ 20240102_3_3_0/
├─ metadata/
│  └─ database_name.sql
│     └─ table_name.sql
└─ tmp/
   └─ 임시 파일
```

**파티션과 파트:**

```
개념 이해:
┌──────────────────────────────────────┐
│         Table: web_logs              │
├──────────────────────────────────────┤
│  Partition: 2024-01-01               │
│  ├─ Part: 20240101_1_1_0 (100만 건) │
│  ├─ Part: 20240101_2_2_0 (100만 건) │
│  └─ Part: 20240101_3_3_0 (100만 건) │
├──────────────────────────────────────┤
│  Partition: 2024-01-02               │
│  ├─ Part: 20240102_4_4_0 (100만 건) │
│  └─ Part: 20240102_5_5_0 (100만 건) │
└──────────────────────────────────────┘

백그라운드 병합:
20240101_1_1_0 + 20240101_2_2_0
        ↓
20240101_1_2_1 (200만 건)
```

---

## 컬럼형 스토리지의 원리

### 행형 vs 컬럼형 스토리지

**행형 스토리지 (Row-based)**

전통적인 RDBMS 방식입니다:

```
디스크 저장:
Row 1: [id=1, name='Alice', age=25, city='Seoul']
Row 2: [id=2, name='Bob', age=30, city='Busan']
Row 3: [id=3, name='Charlie', age=35, city='Seoul']

쿼리: SELECT AVG(age) FROM users WHERE city = 'Seoul';

읽어야 하는 데이터:
✓ id, name, age, city (모든 컬럼)
✗ age와 city만 필요한데 전체 읽음
```

**컬럼형 스토리지 (Columnar)**

ClickHouse의 방식입니다:

```
디스크 저장:
id    컬럼: [1, 2, 3]
name  컬럼: ['Alice', 'Bob', 'Charlie']
age   컬럼: [25, 30, 35]
city  컬럼: ['Seoul', 'Busan', 'Seoul']

쿼리: SELECT AVG(age) FROM users WHERE city = 'Seoul';

읽어야 하는 데이터:
✓ age 컬럼만
✓ city 컬럼만
✗ id, name 컬럼 읽지 않음 → I/O 50% 절감
```

### 컬럼형 스토리지의 장점

**1. I/O 효율성**

```
예시: 100개 컬럼 중 5개만 조회

행형 스토리지:
- 100개 컬럼 모두 읽음
- 디스크 I/O: 100GB

컬럼형 스토리지:
- 5개 컬럼만 읽음
- 디스크 I/O: 5GB (95% 절감)
```

**2. 압축 효율성**

컬럼 데이터는 같은 타입이 연속되어 높은 압축률을 보입니다:

```
행형 압축:
[1, 'Alice', 25, 'Seoul', 2, 'Bob', 30, 'Busan', ...]
→ 압축률: 3:1

컬럼형 압축:
id:   [1, 2, 3, 4, 5, ...] → Delta 인코딩
age:  [25, 30, 35, 25, 40, ...] → 값 범위가 좁음
city: ['Seoul', 'Busan', 'Seoul', ...] → Dictionary 인코딩
→ 압축률: 10:1 ~ 100:1
```

**3. CPU 캐시 친화성**

```
벡터화 처리:
SUM(age) FROM users

컬럼형:
ages = [25, 30, 35, 25, 40, ...]
→ CPU SIMD 명령어로 한 번에 처리
→ 8개 값을 동시에 더함

행형:
각 행을 순회하며 age 추출
→ 캐시 미스 빈번
→ 하나씩 처리
```

**4. 병렬 처리**

```
각 컬럼을 독립적으로 처리:

Thread 1: age 컬럼 집계
Thread 2: city 컬럼 필터링
Thread 3: name 컬럼 정렬
...

→ 모든 CPU 코어 활용
→ 선형적 성능 향상
```

### 압축 알고리즘

ClickHouse는 데이터 특성에 따라 자동으로 최적의 압축 방식을 선택합니다:

**1. LZ4 (기본값)**

```
특징:
- 빠른 압축/해제 속도
- 중간 수준 압축률 (2:1 ~ 5:1)
- CPU 부하 낮음

적합한 경우:
- 실시간 쿼리 성능이 중요
- 일반적인 텍스트/숫자 데이터
```

**2. ZSTD**

```
특징:
- 높은 압축률 (5:1 ~ 15:1)
- 약간 느린 속도
- 압축 레벨 조정 가능

적합한 경우:
- 스토리지 비용 절감이 중요
- 콜드 데이터 (자주 조회 안 됨)
```

**3. Delta 인코딩**

```
시계열 데이터에 효과적:

원본: [1000, 1001, 1002, 1003, 1004]
Delta: [1000, +1, +1, +1, +1]
압축률: 10:1 이상

타임스탬프, 증가하는 ID에 최적
```

**4. Dictionary 인코딩**

```
카디널리티가 낮은 데이터:

원본: ['Seoul', 'Seoul', 'Busan', 'Seoul', 'Busan']
Dictionary: {1: 'Seoul', 2: 'Busan'}
Encoded: [1, 1, 2, 1, 2]
압축률: 20:1 이상

국가, 도시, 상태 코드에 최적
```

---

## 테이블 엔진

ClickHouse의 가장 독특한 특징은 **다양한 테이블 엔진**을 제공한다는 것입니다. 테이블 엔진은 데이터가 저장되고 조회되는 방식을 결정합니다.

### MergeTree 계열 (핵심)

#### 1. MergeTree - 기본 엔진

**특징:**
- 가장 많이 사용되는 범용 테이블 엔진
- 자동 데이터 정렬 및 병합
- 파티셔닝 지원
- 기본키 인덱스 지원

**생성 예시:**

```sql
CREATE TABLE web_logs
(
    event_time DateTime,
    user_id UInt32,
    page_url String,
    country String,
    duration UInt32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (country, user_id, event_time)
SETTINGS index_granularity = 8192;
```

**파티셔닝:**

```
목적: 쿼리 성능 향상 및 데이터 관리 용이

PARTITION BY toYYYYMM(event_time)
→ 월별로 데이터 분리

장점:
1. 특정 월 데이터만 조회 시 다른 파티션 무시
2. 오래된 파티션 삭제 용이 (DROP PARTITION)
3. 파티션별 독립적 병합 작업
```

**ORDER BY (정렬 키):**

```sql
ORDER BY (country, user_id, event_time)

효과:
1. 디스크에 정렬되어 저장
2. 범위 스캔 최적화
3. 압축률 향상 (같은 값들이 연속)

쿼리 최적화:
-- ✅ 빠름 (정렬 키 사용)
WHERE country = 'KR' AND user_id = 123

-- ⚠️ 느림 (정렬 키 미사용)
WHERE duration > 100
```

**인덱스 Granularity:**

```
index_granularity = 8192 (기본값)

의미:
- 8,192개 행마다 인덱스 포인트 생성
- 작을수록: 정확한 탐색, 더 많은 메모리
- 클수록: 적은 메모리, 덜 정확한 탐색

예시:
1억 건 데이터
→ 8192 granularity: 12,207개 인덱스 포인트
→ 4096 granularity: 24,414개 인덱스 포인트
```

#### 2. ReplacingMergeTree - 중복 제거

**특징:**
- 병합 시 중복된 행 제거
- 최신 버전만 유지
- UPDATE 시뮬레이션 가능

**사용 예시:**

```sql
CREATE TABLE user_profiles
(
    user_id UInt32,
    name String,
    email String,
    updated_at DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY user_id;

-- 데이터 삽입 (UPDATE 대신)
INSERT INTO user_profiles VALUES (1, 'Alice', 'alice@old.com', '2024-01-01');
INSERT INTO user_profiles VALUES (1, 'Alice', 'alice@new.com', '2024-01-02');

-- 병합 전: 두 행 모두 존재
SELECT * FROM user_profiles WHERE user_id = 1;
┌─user_id─┬─name──┬─email──────────┬─updated_at──────────┐
│  1      │ Alice │ alice@old.com  │ 2024-01-01 00:00:00 │
│  1      │ Alice │ alice@new.com  │ 2024-01-02 00:00:00 │
└─────────┴───────┴────────────────┴─────────────────────┘

-- 병합 후: 최신 행만 유지
OPTIMIZE TABLE user_profiles FINAL;

SELECT * FROM user_profiles WHERE user_id = 1;
┌─user_id─┬─name──┬─email──────────┬─updated_at──────────┐
│  1      │ Alice │ alice@new.com  │ 2024-01-02 00:00:00 │
└─────────┴───────┴────────────────┴─────────────────────┘

-- FINAL 키워드로 즉시 중복 제거 (성능 영향)
SELECT * FROM user_profiles FINAL WHERE user_id = 1;
```

**주의사항:**

```
1. 병합은 백그라운드에서 비동기적으로 실행
   → 즉시 중복 제거 안 됨

2. FINAL 사용 시 성능 저하
   → 실시간 쿼리에서는 권장 안 함

3. ORDER BY 키가 동일해야 중복으로 간주
```

#### 3. SummingMergeTree - 자동 집계

**특징:**
- 병합 시 숫자 컬럼 자동 합산
- 사전 집계 테이블에 적합
- 스토리지 절약

**사용 예시:**

```sql
CREATE TABLE page_views_summary
(
    date Date,
    page_url String,
    views UInt64,
    unique_users UInt64
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, page_url);

-- 데이터 삽입
INSERT INTO page_views_summary VALUES
    ('2024-01-01', '/home', 100, 50),
    ('2024-01-01', '/home', 200, 75);

-- 병합 전
SELECT * FROM page_views_summary WHERE page_url = '/home';
┌─date───────┬─page_url─┬─views─┬─unique_users─┐
│ 2024-01-01 │ /home    │ 100   │ 50           │
│ 2024-01-01 │ /home    │ 200   │ 75           │
└────────────┴──────────┴───────┴──────────────┘

-- 병합 후: 자동 합산
OPTIMIZE TABLE page_views_summary;

SELECT * FROM page_views_summary WHERE page_url = '/home';
┌─date───────┬─page_url─┬─views─┬─unique_users─┐
│ 2024-01-01 │ /home    │ 300   │ 125          │
└────────────┴──────────┴───────┴──────────────┘
```

**실시간 집계 쿼리:**

```sql
-- SUM 함수로 즉시 집계
SELECT 
    date,
    page_url,
    SUM(views) AS total_views,
    SUM(unique_users) AS total_users
FROM page_views_summary
WHERE date >= '2024-01-01'
GROUP BY date, page_url;
```

#### 4. AggregatingMergeTree - 고급 집계

**특징:**
- 복잡한 집계 함수 지원
- 중간 상태 저장
- 매우 효율적인 사전 집계

**사용 예시:**

```sql
CREATE TABLE user_activity_agg
(
    date Date,
    page_url String,
    views SimpleAggregateFunction(sum, UInt64),
    unique_users AggregateFunction(uniq, UInt32),
    avg_duration AggregateFunction(avg, Float32)
)
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, page_url);

-- 데이터 삽입 (집계 상태로)
INSERT INTO user_activity_agg
SELECT 
    date,
    page_url,
    sumState(views) AS views,
    uniqState(user_id) AS unique_users,
    avgState(duration) AS avg_duration
FROM user_activity
GROUP BY date, page_url;

-- 조회 (병합된 집계 값)
SELECT 
    date,
    page_url,
    sum(views) AS total_views,
    uniqMerge(unique_users) AS unique_user_count,
    avgMerge(avg_duration) AS avg_duration_sec
FROM user_activity_agg
WHERE date >= '2024-01-01'
GROUP BY date, page_url;
```

**SimpleAggregateFunction vs AggregateFunction:**

```
SimpleAggregateFunction:
- 단순 집계 (sum, min, max, any)
- 중간 상태 저장 안 함
- 빠르고 메모리 효율적

AggregateFunction:
- 복잡한 집계 (uniq, quantile, groupArray)
- 중간 상태 저장
- HyperLogLog 등 근사 알고리즘 사용
```

### Log 계열 엔진

#### TinyLog - 간단한 테이블

```sql
CREATE TABLE test_logs
(
    timestamp DateTime,
    message String
)
ENGINE = TinyLog;

-- 특징:
-- 1. 인덱스 없음
-- 2. 병렬 읽기 불가
-- 3. 작은 테스트 데이터용
-- 4. 동시 쓰기 잠금
```

### 통합 엔진

#### Kafka - 실시간 스트림 처리

```sql
CREATE TABLE kafka_source
(
    event_time DateTime,
    user_id UInt32,
    action String
)
ENGINE = Kafka()
SETTINGS 
    kafka_broker_list = 'localhost:9092',
    kafka_topic_list = 'events',
    kafka_group_name = 'clickhouse_consumer',
    kafka_format = 'JSONEachRow';

-- Materialized View로 MergeTree에 저장
CREATE MATERIALIZED VIEW events_mv TO events AS
SELECT * FROM kafka_source;
```

#### MySQL - 실시간 동기화

```sql
CREATE TABLE mysql_users
(
    id UInt32,
    name String,
    email String
)
ENGINE = MySQL('mysql-host:3306', 'database', 'users', 'username', 'password');

-- 실시간으로 MySQL 데이터 조회
SELECT * FROM mysql_users WHERE id > 1000;
```

---

## 데이터 타입과 함수

### 기본 데이터 타입

#### 정수형

```sql
-- 부호 있는 정수
Int8    -- -128 ~ 127 (1 byte)
Int16   -- -32,768 ~ 32,767 (2 bytes)
Int32   -- -2,147,483,648 ~ 2,147,483,647 (4 bytes)
Int64   -- 64비트 정수 (8 bytes)

-- 부호 없는 정수 (권장)
UInt8   -- 0 ~ 255
UInt16  -- 0 ~ 65,535
UInt32  -- 0 ~ 4,294,967,295
UInt64  -- 0 ~ 18,446,744,073,709,551,615

-- 예시
CREATE TABLE counters
(
    user_id UInt32,        -- 사용자 ID (40억까지)
    page_views UInt64,     -- 페이지뷰 (큰 숫자)
    age UInt8              -- 나이 (0-255면 충분)
)
ENGINE = MergeTree()
ORDER BY user_id;
```

#### 부동소수점

```sql
Float32  -- 단정밀도 (4 bytes)
Float64  -- 배정밀도 (8 bytes)

-- Decimal (정확한 소수점 계산)
Decimal(P, S)  -- P: 전체 자릿수, S: 소수점 자릿수
Decimal32(S)   -- 9자리
Decimal64(S)   -- 18자리
Decimal128(S)  -- 38자리

-- 예시: 금융 데이터
CREATE TABLE transactions
(
    transaction_id UInt64,
    amount Decimal(18, 2),  -- 999,999,999,999,999.99까지
    tax_rate Decimal(5, 4)  -- 99.9999%까지
)
ENGINE = MergeTree()
ORDER BY transaction_id;
```

#### 문자열

```sql
String          -- 가변 길이 문자열 (권장)
FixedString(N)  -- 고정 길이 (N 바이트)

-- 예시
CREATE TABLE users
(
    user_id UInt32,
    name String,
    country_code FixedString(2),  -- 'KR', 'US' 등
    bio String
)
ENGINE = MergeTree()
ORDER BY user_id;
```

#### 날짜/시간

```sql
Date        -- 날짜 (YYYY-MM-DD)
DateTime    -- 타임스탬프 (초 단위)
DateTime64  -- 타임스탬프 (밀리초, 마이크로초)

-- 예시
CREATE TABLE events
(
    event_time DateTime,                    -- 초 단위
    precise_time DateTime64(3),             -- 밀리초 (0.001초)
    event_date Date,                        -- 날짜만
    event_timestamp UInt32                  -- Unix 타임스탬프
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY event_time;

-- 시간대 지정
CREATE TABLE events_with_tz
(
    event_time DateTime('Asia/Seoul'),
    created_at DateTime64(3, 'UTC')
)
ENGINE = MergeTree()
ORDER BY event_time;
```

#### 배열

```sql
Array(T)  -- T 타입의 배열

-- 예시
CREATE TABLE user_tags
(
    user_id UInt32,
    tags Array(String),              -- ['sports', 'tech', 'music']
    visit_dates Array(Date),         -- [2024-01-01, 2024-01-05]
    scores Array(Float32)            -- [95.5, 87.2, 91.0]
)
ENGINE = MergeTree()
ORDER BY user_id;

-- 배열 조회
SELECT 
    user_id,
    tags,
    arrayElement(tags, 1) AS first_tag,  -- 첫 번째 태그
    length(tags) AS tag_count,            -- 태그 개수
    has(tags, 'sports') AS has_sports     -- 특정 값 포함 여부
FROM user_tags;
```

#### Nested (중첩 구조)

```sql
-- 복잡한 중첩 데이터 구조
CREATE TABLE user_actions
(
    user_id UInt32,
    actions Nested(
        timestamp DateTime,
        action_type String,
        metadata String
    )
)
ENGINE = MergeTree()
ORDER BY user_id;

-- 데이터 삽입
INSERT INTO user_actions VALUES
(
    1,
    [
        '2024-01-01 10:00:00', '2024-01-01 11:00:00'
    ],
    [
        'click', 'purchase'
    ],
    [
        '{"page": "home"}', '{"amount": 100}'
    ]
);

-- 조회
SELECT 
    user_id,
    actions.timestamp,
    actions.action_type
FROM user_actions;
```

### 고급 함수

#### 집계 함수

```sql
-- 기본 집계
SELECT
    COUNT() AS total_rows,
    COUNT(DISTINCT user_id) AS unique_users,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount,
    MIN(amount) AS min_amount,
    MAX(amount) AS max_amount
FROM transactions;

-- 고급 집계
SELECT
    -- 중앙값
    quantile(0.5)(duration) AS median_duration,
    
    -- 90번째 백분위수
    quantile(0.9)(duration) AS p90_duration,
    
    -- 여러 백분위수 동시 계산
    quantiles(0.5, 0.9, 0.95, 0.99)(duration) AS percentiles,
    
    -- 표준편차
    stddevPop(duration) AS stddev,
    
    -- 분산
    varPop(duration) AS variance
FROM page_loads
WHERE date >= today() - 7;
```

#### 날짜/시간 함수

```sql
SELECT
    -- 현재 시간
    now() AS current_time,
    today() AS current_date,
    yesterday() AS yesterday_date,
    
    -- 날짜 추출
    toYear(event_time) AS year,
    toMonth(event_time) AS month,
    toDayOfWeek(event_time) AS day_of_week,  -- 1=Monday, 7=Sunday
    toHour(event_time) AS hour,
    
    -- 날짜 변환
    toYYYYMM(event_time) AS year_month,       -- 202401
    toStartOfMonth(event_time) AS month_start, -- 2024-01-01
    toStartOfWeek(event_time) AS week_start,
    toStartOfDay(event_time) AS day_start,
    
    -- 날짜 연산
    addDays(event_time, 7) AS next_week,
    subtractHours(event_time, 1) AS hour_ago,
    
    -- 날짜 차이
    dateDiff('day', start_date, end_date) AS days_diff,
    dateDiff('hour', start_time, end_time) AS hours_diff
FROM events;
```

#### 문자열 함수

```sql
SELECT
    -- 기본 문자열 조작
    lower(name) AS lowercase,
    upper(name) AS uppercase,
    length(name) AS name_length,
    
    -- 부분 문자열
    substring(email, 1, position(email, '@') - 1) AS username,
    splitByChar('@', email)[1] AS domain,
    
    -- 패턴 매칭
    match(url, 'https://.*\\.com') AS is_com_domain,
    extract(url, '/product/([0-9]+)') AS product_id,
    
    -- 문자열 변환
    trim(both ' ' from text) AS trimmed,
    replace(text, 'old', 'new') AS replaced,
    concat(first_name, ' ', last_name) AS full_name
FROM users;
```

#### 배열 함수

```sql
SELECT
    -- 배열 생성
    [1, 2, 3] AS simple_array,
    range(10) AS numbers,  -- [0, 1, 2, ..., 9]
    
    -- 배열 조작
    arrayElement(tags, 1) AS first_tag,
    arraySlice(tags, 2, 3) AS middle_tags,
    arrayConcat(tags1, tags2) AS combined,
    
    -- 배열 검색
    has(tags, 'important') AS has_important,
    indexOf(tags, 'important') AS position,
    
    -- 배열 집계
    arraySum([1, 2, 3, 4, 5]) AS sum,
    arrayAvg([1, 2, 3, 4, 5]) AS avg,
    
    -- 배열 필터링
    arrayFilter(x -> x > 10, numbers) AS filtered,
    arrayMap(x -> x * 2, numbers) AS doubled
FROM data;
```

#### JSON 함수

```sql
SELECT
    -- JSON 파싱
    JSONExtractString(json_data, 'user', 'name') AS user_name,
    JSONExtractInt(json_data, 'user', 'age') AS user_age,
    
    -- JSON 배열
    JSONExtractArrayRaw(json_data, 'items') AS items_array,
    
    -- 전체 JSON 파싱
    JSONExtract(json_data, 'Tuple(name String, age UInt8)') AS user_tuple
FROM raw_logs;

-- JSON 타입 사용
CREATE TABLE json_logs
(
    event_time DateTime,
    data JSON  -- 실험적 기능
)
ENGINE = MergeTree()
ORDER BY event_time;
```

---

## 쿼리 최적화

### 쿼리 실행 계획 분석

```sql
-- 쿼리 실행 계획 확인
EXPLAIN PLAN
SELECT 
    country,
    COUNT() AS user_count,
    AVG(age) AS avg_age
FROM users
WHERE registration_date >= '2024-01-01'
GROUP BY country
ORDER BY user_count DESC
LIMIT 10;

-- 결과 예시:
┌─explain─────────────────────────────────┐
│ Expression (Projection)                 │
│   Limit (preliminary LIMIT)             │
│     Sorting (ORDER BY)                  │
│       Expression (Before ORDER BY)      │
│         Aggregating                     │
│           Expression (Before GROUP BY)  │
│             Filter (WHERE)              │
│               ReadFromMergeTree (users) │
└─────────────────────────────────────────┘

-- 상세 실행 계획
EXPLAIN indexes = 1, actions = 1
SELECT ...;
```

### 인덱스 활용

#### 기본키 인덱스 (Sparse Index)

ClickHouse는 희소 인덱스를 사용합니다:

```
전통적 RDBMS:
모든 행에 대한 인덱스 포인트 생성
1억 건 → 1억 개 인덱스 엔트리

ClickHouse:
일정 간격(granularity)마다 인덱스 포인트 생성
1억 건 → 12,207개 인덱스 엔트리 (granularity=8192)

메모리 절약: 99.99%
```

**인덱스 최적화:**

```sql
-- ✅ 좋은 예: ORDER BY 키 사용
SELECT * FROM users WHERE country = 'KR' AND city = 'Seoul';
-- ORDER BY (country, city, user_id)

-- ❌ 나쁜 예: ORDER BY 키 미사용
SELECT * FROM users WHERE age > 30;
-- ORDER BY (country, city, user_id) → age는 정렬 키가 아님
```

#### Skip Index (보조 인덱스)

특정 조건에서 데이터 블록을 건너뛰는 인덱스:

```sql
-- Bloom Filter Index (집합 연산)
ALTER TABLE users ADD INDEX idx_email(email) TYPE bloom_filter GRANULARITY 4;

-- 효과적인 쿼리
SELECT * FROM users WHERE email = 'user@example.com';
-- Bloom filter가 해당 블록에 이메일이 없다고 판단하면 스킵

-- MinMax Index (범위 쿼리)
ALTER TABLE orders ADD INDEX idx_amount(amount) TYPE minmax GRANULARITY 4;

-- 효과적인 쿼리
SELECT * FROM orders WHERE amount BETWEEN 1000 AND 5000;
-- MinMax 값으로 범위 밖 블록 스킵

-- Set Index (낮은 카디널리티)
ALTER TABLE logs ADD INDEX idx_status(status) TYPE set(100) GRANULARITY 4;

-- 효과적인 쿼리
SELECT * FROM logs WHERE status IN ('ERROR', 'WARNING');
-- Set index로 빠른 필터링
```

### 쿼리 최적화 패턴

#### 1. PREWHERE vs WHERE

```sql
-- ❌ 비효율적
SELECT *
FROM large_table
WHERE heavy_calculation(column1) > 100
  AND column2 = 'value';

-- ✅ 효율적
SELECT *
FROM large_table
PREWHERE column2 = 'value'  -- 먼저 필터링 (적은 데이터)
WHERE heavy_calculation(column1) > 100;  -- 이후 계산 (많은 데이터)

-- PREWHERE:
-- 1. 컬럼 일부만 읽음
-- 2. 빠른 필터링
-- 3. 결과 행에 대해서만 나머지 컬럼 읽음
```

#### 2. Projection (사전 집계)

```sql
-- Projection 정의
ALTER TABLE sales ADD PROJECTION sales_by_region
(
    SELECT 
        region,
        SUM(amount) AS total_amount,
        COUNT() AS order_count
    GROUP BY region
);

-- Projection 구체화
ALTER TABLE sales MATERIALIZE PROJECTION sales_by_region;

-- 쿼리 시 자동으로 Projection 사용
SELECT 
    region,
    SUM(amount),
    COUNT()
FROM sales
GROUP BY region;
-- → sales_by_region projection 사용 (100배 빠름)
```

#### 3. 샘플링

```sql
-- 테이블에 샘플링 키 추가
CREATE TABLE events
(
    event_time DateTime,
    user_id UInt32,
    action String
)
ENGINE = MergeTree()
ORDER BY (event_time, user_id)
SAMPLE BY user_id;

-- 10% 샘플링 쿼리
SELECT 
    action,
    COUNT() * 10 AS estimated_count  -- 샘플 크기로 보정
FROM events
SAMPLE 0.1
WHERE event_time >= today() - 7
GROUP BY action;

-- 빠른 근사 결과, 정확도는 낮음
```

#### 4. 병렬 처리 최적화

```sql
-- 설정 조정
SET max_threads = 8;                    -- 최대 스레드 수
SET max_insert_threads = 4;             -- 삽입 스레드 수
SET max_distributed_connections = 100;  -- 분산 연결 수

-- 대용량 쿼리
SELECT 
    date,
    COUNT() AS events
FROM large_table
WHERE date >= '2024-01-01'
GROUP BY date
SETTINGS max_threads = 16;  -- 쿼리별 설정
```

---

## 분산 처리와 복제

### 분산 테이블 (Distributed Table)

분산 테이블은 여러 서버의 데이터를 하나로 통합하여 조회할 수 있게 합니다:

```sql
-- 각 서버에 로컬 테이블 생성
CREATE TABLE events_local ON CLUSTER my_cluster
(
    event_time DateTime,
    user_id UInt32,
    action String
)
ENGINE = MergeTree()
ORDER BY (event_time, user_id);

-- 분산 테이블 생성
CREATE TABLE events_distributed ON CLUSTER my_cluster AS events_local
ENGINE = Distributed(
    my_cluster,      -- 클러스터 이름
    default,         -- 데이터베이스
    events_local,    -- 로컬 테이블
    rand()           -- 샤딩 키 (랜덤 분산)
);

-- 분산 테이블로 삽입 (자동으로 샤딩)
INSERT INTO events_distributed VALUES
    (now(), 123, 'click'),
    (now(), 456, 'purchase');
-- → 샤딩 키(rand())에 따라 각 서버에 분산 저장

-- 분산 테이블로 조회 (모든 서버 데이터 통합)
SELECT 
    action,
    COUNT() AS count
FROM events_distributed
WHERE event_time >= today()
GROUP BY action;
-- → 각 서버에서 부분 집계 후 최종 병합
```

**샤딩 전략:**

```sql
-- 1. 랜덤 분산 (기본)
ENGINE = Distributed(my_cluster, default, events_local, rand());
-- 장점: 균등 분산
-- 단점: 관련 데이터가 흩어짐

-- 2. 사용자 ID로 분산
ENGINE = Distributed(my_cluster, default, events_local, user_id);
-- 장점: 같은 사용자 데이터가 같은 서버에
-- 단점: 데이터 불균형 가능성

-- 3. 해시 함수 사용
ENGINE = Distributed(my_cluster, default, events_local, sipHash64(user_id));
-- 장점: 균등한 분산 + 일관된 해싱
-- 권장: 대부분의 경우
```

### 복제 (Replication)

복제는 데이터의 고가용성과 내구성을 보장합니다:

```sql
-- ReplicatedMergeTree 사용
CREATE TABLE events_replicated ON CLUSTER my_cluster
(
    event_time DateTime,
    user_id UInt32,
    action String
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events',  -- ZooKeeper 경로
    '{replica}'                            -- 복제본 이름
)
ORDER BY (event_time, user_id);

-- 복제 + 분산
CREATE TABLE events_distributed_replicated ON CLUSTER my_cluster
AS events_replicated
ENGINE = Distributed(my_cluster, default, events_replicated, sipHash64(user_id));
```

**클러스터 구성:**

```xml
<!-- /etc/clickhouse-server/config.xml -->
<remote_servers>
    <my_cluster>
        <!-- 샤드 1 -->
        <shard>
            <weight>1</weight>
            <internal_replication>true</internal_replication>
            <replica>
                <host>server1</host>
                <port>9000</port>
            </replica>
            <replica>
                <host>server2</host>
                <port>9000</port>
            </replica>
        </shard>
        
        <!-- 샤드 2 -->
        <shard>
            <weight>1</weight>
            <internal_replication>true</internal_replication>
            <replica>
                <host>server3</host>
                <port>9000</port>
            </replica>
            <replica>
                <host>server4</host>
                <port>9000</port>
            </replica>
        </shard>
    </my_cluster>
</remote_servers>
```

**아키텍처:**

```
클라이언트
    ↓
분산 테이블 (events_distributed_replicated)
    ↓
┌──────────────┬──────────────┐
│   Shard 1    │   Shard 2    │
├──────────────┼──────────────┤
│ Replica 1    │ Replica 1    │
│ (server1)    │ (server3)    │
│              │              │
│ Replica 2    │ Replica 2    │
│ (server2)    │ (server4)    │
└──────────────┴──────────────┘
    ↓              ↓
ZooKeeper (복제 조정)
```

---

## 실무 활용 사례

### 1. 웹 로그 분석 시스템

**요구사항:**
- 일 100억 건의 웹 로그 수집
- 실시간 대시보드 (1초 이내 응답)
- 사용자 행동 분석
- 트래픽 모니터링

**테이블 설계:**

```sql
-- 원시 로그 테이블
CREATE TABLE web_logs
(
    timestamp DateTime,
    user_id UInt32,
    session_id FixedString(32),
    ip String,
    user_agent String,
    url String,
    referer String,
    country FixedString(2),
    city String,
    duration UInt32,  -- 밀리초
    status_code UInt16
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (country, city, timestamp, user_id)
TTL timestamp + INTERVAL 90 DAY  -- 90일 후 자동 삭제
SETTINGS index_granularity = 8192;

-- 시간별 집계 테이블 (Materialized View)
CREATE MATERIALIZED VIEW web_logs_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (country, city, hour, url)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    country,
    city,
    url,
    COUNT() AS page_views,
    uniq(user_id) AS unique_users,
    SUM(duration) AS total_duration,
    countIf(status_code >= 500) AS error_count
FROM web_logs
GROUP BY hour, country, city, url;
```

**실시간 대시보드 쿼리:**

```sql
-- 국가별 실시간 트래픽
SELECT 
    country,
    SUM(page_views) AS total_views,
    SUM(unique_users) AS users,
    AVG(total_duration / page_views) AS avg_duration_ms
FROM web_logs_hourly
WHERE hour >= now() - INTERVAL 1 HOUR
GROUP BY country
ORDER BY total_views DESC
LIMIT 10;
-- 실행 시간: ~100ms (100억 건에서)

-- 인기 페이지 TOP 20
SELECT 
    url,
    SUM(page_views) AS views,
    SUM(unique_users) AS users,
    views / users AS views_per_user
FROM web_logs_hourly
WHERE hour >= today()
GROUP BY url
ORDER BY views DESC
LIMIT 20;
-- 실행 시간: ~50ms
```

### 2. IoT 센서 데이터 플랫폼

**요구사항:**
- 100만 개 센서에서 초당 1000만 건 데이터 수집
- 실시간 이상 탐지
- 시계열 분석 및 예측
- 장기 히스토리 저장

**테이블 설계:**

```sql
-- 센서 데이터 테이블
CREATE TABLE sensor_data
(
    timestamp DateTime64(3),  -- 밀리초 정밀도
    sensor_id UInt32,
    device_id UInt32,
    location_id UInt16,
    temperature Decimal(5, 2),
    humidity Decimal(5, 2),
    pressure Decimal(7, 2),
    battery_level UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (location_id, device_id, sensor_id, timestamp)
TTL timestamp + INTERVAL 2 YEAR  -- 2년 보관
SETTINGS index_granularity = 8192;

-- 분별 집계 (이상 탐지용)
CREATE MATERIALIZED VIEW sensor_data_1min
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(minute)
ORDER BY (location_id, device_id, sensor_id, minute)
AS SELECT
    toStartOfMinute(timestamp) AS minute,
    location_id,
    device_id,
    sensor_id,
    avgState(temperature) AS avg_temperature,
    minState(temperature) AS min_temperature,
    maxState(temperature) AS max_temperature,
    stddevPopState(temperature) AS stddev_temperature,
    avgState(humidity) AS avg_humidity,
    avgState(battery_level) AS avg_battery
FROM sensor_data
GROUP BY minute, location_id, device_id, sensor_id;
```

**이상 탐지 쿼리:**

```sql
-- 급격한 온도 변화 감지
SELECT 
    location_id,
    device_id,
    sensor_id,
    minute,
    avgMerge(avg_temperature) AS avg_temp,
    maxMerge(max_temperature) - minMerge(min_temperature) AS temp_range,
    stddevPopMerge(stddev_temperature) AS temp_stddev
FROM sensor_data_1min
WHERE minute >= now() - INTERVAL 10 MINUTE
  AND temp_range > 10  -- 10도 이상 변화
GROUP BY location_id, device_id, sensor_id, minute
ORDER BY temp_range DESC;
-- 실행 시간: ~50ms

-- 배터리 부족 센서 목록
SELECT 
    location_id,
    device_id,
    sensor_id,
    avgMerge(avg_battery) AS battery_pct
FROM sensor_data_1min
WHERE minute >= now() - INTERVAL 1 HOUR
GROUP BY location_id, device_id, sensor_id
HAVING battery_pct < 20
ORDER BY battery_pct ASC;
```

### 3. 실시간 광고 분석 시스템

**요구사항:**
- 초당 100만 건 광고 노출/클릭 이벤트
- 실시간 CTR 계산
- 캠페인 성과 분석
- 이상 트래픽 탐지

**테이블 설계:**

```sql
-- 광고 이벤트 테이블
CREATE TABLE ad_events
(
    event_time DateTime,
    event_type Enum8('impression' = 1, 'click' = 2, 'conversion' = 3),
    ad_id UInt32,
    campaign_id UInt32,
    user_id UInt64,
    device_type LowCardinality(String),
    country FixedString(2),
    placement String,
    bid_price Decimal(10, 4),
    revenue Decimal(10, 4)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(event_time)
ORDER BY (campaign_id, ad_id, event_time)
SETTINGS index_granularity = 8192;

-- 5분별 집계 (실시간 모니터링용)
CREATE MATERIALIZED VIEW ad_stats_5min
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(period)
ORDER BY (campaign_id, ad_id, device_type, period)
AS SELECT
    toStartOfFiveMinutes(event_time) AS period,
    campaign_id,
    ad_id,
    device_type,
    country,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'click') AS clicks,
    countIf(event_type = 'conversion') AS conversions,
    sumIf(bid_price, event_type = 'impression') AS total_cost,
    sumIf(revenue, event_type = 'conversion') AS total_revenue
FROM ad_events
GROUP BY period, campaign_id, ad_id, device_type, country;
```

**실시간 분석 쿼리:**

```sql
-- 실시간 캠페인 성과
SELECT 
    campaign_id,
    SUM(impressions) AS total_impressions,
    SUM(clicks) AS total_clicks,
    SUM(conversions) AS total_conversions,
    (total_clicks / total_impressions) * 100 AS ctr,  -- CTR %
    (total_conversions / total_clicks) * 100 AS cvr,  -- CVR %
    SUM(total_revenue) AS revenue,
    SUM(total_cost) AS cost,
    (revenue - cost) AS profit,
    (revenue / cost - 1) * 100 AS roi  -- ROI %
FROM ad_stats_5min
WHERE period >= now() - INTERVAL 1 HOUR
GROUP BY campaign_id
ORDER BY profit DESC
LIMIT 20;
-- 실행 시간: ~100ms

-- 디바이스별 성과
SELECT 
    device_type,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    (clicks / impressions) * 100 AS ctr,
    SUM(total_revenue) / SUM(total_cost) AS roas  -- Return on Ad Spend
FROM ad_stats_5min
WHERE period >= today()
GROUP BY device_type
ORDER BY roas DESC;
```

---

## 성능 튜닝 전략

### 하드웨어 최적화

**CPU:**
```
권장:
- 코어 수가 많을수록 유리 (16+ 코어)
- 높은 클럭 속도 (3GHz+)
- AVX2/AVX-512 지원 (벡터화 처리)

설정:
SET max_threads = <CPU 코어 수>;
```

**메모리:**
```
권장:
- 최소 32GB, 권장 64GB+
- DDR4-3200 이상
- ECC 메모리 (프로덕션)

설정:
max_memory_usage = <RAM의 80%>
max_bytes_before_external_group_by = <RAM의 50%>
```

**스토리지:**
```
권장:
- NVMe SSD (읽기/쓰기 속도 중요)
- RAID 10 (성능 + 안정성)
- 별도의 디스크로 로그 분리

디스크 레이아웃:
/data     - 메인 데이터 (NVMe)
/logs     - 로그 파일 (SATA)
/tmp      - 임시 파일 (NVMe)
```

### 쿼리 최적화 체크리스트

```sql
-- ✅ 1. PREWHERE 활용
SELECT *
FROM large_table
PREWHERE simple_filter_column = value  -- 빠른 필터링
WHERE complex_expression;              -- 느린 계산

-- ✅ 2. 필요한 컬럼만 조회
SELECT user_id, timestamp, action  -- 필요한 것만
FROM events
-- SELECT * 지양

-- ✅ 3. ORDER BY 키 활용
WHERE country = 'KR'  -- ORDER BY에 포함된 컬럼
  AND city = 'Seoul'

-- ✅ 4. 집계 최적화
SELECT
    country,
    uniq(user_id)  -- uniqExact보다 빠름 (근사치)
FROM users
GROUP BY country;

-- ✅ 5. LIMIT 사용
SELECT *
FROM large_table
WHERE condition
LIMIT 1000;  -- 필요한 만큼만

-- ✅ 6. 샘플링 활용 (근사 분석)
SELECT
    country,
    COUNT() * 10 AS estimated_count
FROM events
SAMPLE 0.1  -- 10% 샘플링
WHERE date >= today() - 7
GROUP BY country;

-- ✅ 7. Materialized View 활용
-- 자주 실행되는 집계 쿼리는 MV로 사전 계산

-- ✅ 8. 파티션 프루닝
SELECT *
FROM events
WHERE date = '2024-01-01'  -- 특정 파티션만
-- PARTITION BY toYYYYMMDD(date)
```

### 삽입 성능 최적화

```sql
-- ❌ 나쁜 예: 개별 INSERT
INSERT INTO events VALUES (1, 'data1');
INSERT INTO events VALUES (2, 'data2');
-- ... 1000회

-- ✅ 좋은 예: 배치 INSERT
INSERT INTO events VALUES
    (1, 'data1'),
    (2, 'data2'),
    ...
    (1000, 'data1000');

-- ✅ 더 좋은 예: 대용량 INSERT
INSERT INTO events
SELECT * FROM input('row UInt32, data String')
FORMAT TSV
-- STDIN으로 대용량 데이터 스트리밍

-- 비동기 INSERT (ClickHouse 21.11+)
SET async_insert = 1;
SET wait_for_async_insert = 0;

INSERT INTO events VALUES (1, 'data1');
-- 내부 버퍼에 축적 후 배치로 삽입
```

### 스토리지 최적화

```sql
-- 파티션 관리
-- 오래된 파티션 삭제
ALTER TABLE events DROP PARTITION '202301';

-- 파티션 최적화 (수동 병합)
OPTIMIZE TABLE events PARTITION '202401' FINAL;

-- TTL 설정 (자동 삭제)
ALTER TABLE events
MODIFY TTL timestamp + INTERVAL 90 DAY;

-- 압축 설정
ALTER TABLE events
MODIFY SETTING 
    min_compress_block_size = 65536,
    max_compress_block_size = 1048576;

-- 데이터 타입 최적화
-- UInt32 대신 UInt16 사용 (값 범위가 작으면)
-- String 대신 LowCardinality(String) (카디널리티 낮으면)
-- String 대신 FixedString(N) (고정 길이면)
```

---

## 운영 및 모니터링

### 주요 메트릭 모니터링

```sql
-- 시스템 메트릭
SELECT *
FROM system.metrics;

-- CPU 사용률
SELECT
    event,
    value
FROM system.events
WHERE event LIKE '%CPU%';

-- 메모리 사용량
SELECT
    formatReadableSize(value) AS memory
FROM system.metrics
WHERE metric = 'MemoryTracking';

-- 디스크 사용량
SELECT
    database,
    table,
    formatReadableSize(bytes_on_disk) AS size
FROM system.parts
WHERE active
ORDER BY bytes_on_disk DESC
LIMIT 20;

-- 실행 중인 쿼리
SELECT
    query_id,
    user,
    query,
    elapsed,
    formatReadableSize(memory_usage) AS memory,
    formatReadableSize(read_bytes) AS read_bytes
FROM system.processes
ORDER BY elapsed DESC;

-- 느린 쿼리 분석
SELECT
    query,
    query_duration_ms,
    read_rows,
    formatReadableSize(read_bytes) AS read_size,
    formatReadableSize(memory_usage) AS memory
FROM system.query_log
WHERE type = 'QueryFinish'
  AND query_duration_ms > 1000  -- 1초 이상
ORDER BY query_duration_ms DESC
LIMIT 20;
```

### 백업 및 복구

```bash
# 백업 (clickhouse-backup 도구)
clickhouse-backup create backup_20240101

# 원격 스토리지로 업로드
clickhouse-backup upload backup_20240101

# 복구
clickhouse-backup download backup_20240101
clickhouse-backup restore backup_20240101

# 파티션별 백업
clickhouse-backup create --partitions=202401,202402 backup_202401_202402
```

### 설정 튜닝

```xml
<!-- /etc/clickhouse-server/config.xml -->
<clickhouse>
    <!-- 메모리 설정 -->
    <max_server_memory_usage>64GB</max_server_memory_usage>
    <max_concurrent_queries>100</max_concurrent_queries>
    
    <!-- 병렬 처리 -->
    <max_threads>16</max_threads>
    
    <!-- 네트워크 -->
    <max_connections>4096</max_connections>
    
    <!-- 로그 -->
    <logger>
        <level>information</level>
        <log>/var/log/clickhouse-server/clickhouse-server.log</log>
        <errorlog>/var/log/clickhouse-server/clickhouse-server.err.log</errorlog>
        <size>100M</size>
        <count>10</count>
    </logger>
    
    <!-- 압축 -->
    <compression>
        <case>
            <method>lz4</method>
        </case>
    </compression>
</clickhouse>
```

### 보안 설정

```xml
<!-- users.xml -->
<clickhouse>
    <users>
        <default>
            <password_sha256_hex>hash</password_sha256_hex>
            <networks>
                <ip>127.0.0.1</ip>
                <ip>10.0.0.0/8</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
        </default>
        
        <readonly_user>
            <password_sha256_hex>hash</password_sha256_hex>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>readonly</profile>
            <quota>default</quota>
        </readonly_user>
    </users>
    
    <profiles>
        <default>
            <max_memory_usage>10000000000</max_memory_usage>
            <use_uncompressed_cache>0</use_uncompressed_cache>
            <load_balancing>random</load_balancing>
        </default>
        
        <readonly>
            <readonly>1</readonly>
        </readonly>
    </profiles>
    
    <quotas>
        <default>
            <interval>
                <duration>3600</duration>
                <queries>1000</queries>
                <errors>100</errors>
                <result_rows>1000000000</result_rows>
                <read_rows>1000000000</read_rows>
                <execution_time>3600</execution_time>
            </interval>
        </default>
    </quotas>
</clickhouse>
```

---

## 참고 자료

### 공식 문서

- **ClickHouse 공식 사이트**: https://clickhouse.com/
- **공식 문서**: https://clickhouse.com/docs/
- **GitHub 저장소**: https://github.com/ClickHouse/ClickHouse
- **릴리스 노트**: https://clickhouse.com/docs/en/whats-new/changelog/

### 커뮤니티 및 지원

- **ClickHouse Slack**: https://clickhouse.com/slack
- **Stack Overflow**: 태그 `clickhouse`
- **Reddit**: r/ClickHouse
- **Telegram**: @clickhouse_en

### 학습 자료

- **ClickHouse Academy**: https://learn.clickhouse.com/
- **YouTube 공식 채널**: https://www.youtube.com/@ClickHouseDB
- **웨비나 아카이브**: https://clickhouse.com/company/events

### 도구 및 라이브러리

**클라이언트 라이브러리:**
- Python: `clickhouse-driver`, `clickhouse-connect`
- Java: `clickhouse-jdbc`
- Go: `clickhouse-go`
- Node.js: `@clickhouse/client`

**관리 도구:**
- **Tabix**: 웹 기반 SQL 클라이언트
- **DBeaver**: 범용 데이터베이스 도구
- **Grafana**: 모니터링 및 시각화
- **clickhouse-backup**: 백업 도구

### 모범 사례 문서

- **Performance Optimization Guide**: https://clickhouse.com/docs/en/operations/optimizing-performance/
- **Best Practices**: https://clickhouse.com/docs/en/operations/best-practices/
- **Schema Design**: https://clickhouse.com/docs/en/data-modeling/schema-design/

### 실제 사례 연구

- **Cloudflare**: 로그 분석 (일 60TB)
- **Uber**: 실시간 분석 플랫폼
- **eBay**: 사용자 행동 분석
- **Spotify**: 음악 추천 시스템
- **Yandex**: 웹 분석 (Yandex.Metrica)

### 성능 벤치마크

- **ClickBench**: https://benchmark.clickhouse.com/
- **TPC-H 벤치마크 결과**
- **실시간 성능 비교**: vs PostgreSQL, vs MongoDB, vs Druid

---


