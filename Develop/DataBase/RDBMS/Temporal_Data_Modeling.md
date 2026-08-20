---
title: 시간 데이터 모델링
tags: [database, backend, devops, os]
updated: 2026-07-31
---

# 시간 데이터 모델링

## 개요

시간 데이터 모델링에서 실수가 자주 나오는 이유는 단순하다. 시간은 타입 하나를 고르면 끝나는 것처럼 보이지만, 실제로는 저장 방식, 타임존 처리, 조회 인덱스, 이력 추적, 파티셔닝까지 영향을 미친다. 처음에 잘못 잡으면 나중에 데이터 마이그레이션이 필요해진다.

---

## TIMESTAMP vs DATETIME

MySQL 기준으로 두 타입의 가장 큰 차이는 타임존 처리다.

| 항목 | TIMESTAMP | DATETIME |
|------|-----------|----------|
| 저장 방식 | UTC로 변환해서 저장 | 입력값 그대로 저장 |
| 타임존 적용 | 세션 타임존으로 자동 변환 | 없음 |
| 범위 | 1970-01-01 ~ 2038-01-19 | 1000-01-01 ~ 9999-12-31 |
| 저장 크기 | 4바이트 | 8바이트 |
| NULL 허용 | 기본 NOT NULL | NULL 허용 |

TIMESTAMP는 서버의 `time_zone` 설정에 따라 조회 결과가 달라진다.

```sql
CREATE TABLE logs (
    id         BIGINT    NOT NULL AUTO_INCREMENT,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

SET time_zone = 'Asia/Seoul';
INSERT INTO logs (created_at) VALUES ('2024-01-01 10:00:00');
-- 내부에서는 UTC 2024-01-01 01:00:00 으로 저장

SET time_zone = 'UTC';
SELECT created_at FROM logs;
-- 2024-01-01 01:00:00 이 나온다 — 같은 행인데 값이 달라 보인다
```

DATETIME은 넣은 값 그대로 나온다. 타임존 변환이 없다.

```sql
CREATE TABLE events (
    id       BIGINT   NOT NULL AUTO_INCREMENT,
    start_at DATETIME NOT NULL,      -- 위 logs.created_at 은 TIMESTAMP
    PRIMARY KEY (id)
);

SET time_zone = 'Asia/Seoul';
INSERT INTO events (start_at) VALUES ('2024-01-01 10:00:00');

SET time_zone = 'UTC';
SELECT start_at FROM events;
-- 2024-01-01 10:00:00 — 그대로 나온다
```

### 어떤 걸 고르는가

`created_at`, `updated_at` 같은 시스템 메타데이터는 TIMESTAMP를 쓴다. 특정 시점을 기록하는 목적이고, 4바이트라서 공간도 적게 든다. 단, 2038년 문제가 있다. 오래 가는 서비스라면 DATETIME을 쓰거나, 애초에 애플리케이션에서 UTC로 변환해서 넣고 DATETIME으로 저장한다.

예약 시간, 이벤트 시작 시각처럼 "이 시각에 일어난다"는 의미를 가진 컬럼은 DATETIME이 더 안전하다. 타임존 설정이 바뀌어도 값이 변하지 않기 때문이다.

PostgreSQL은 이 구분이 더 명확하다. `TIMESTAMP WITH TIME ZONE`(=`TIMESTAMPTZ`)은 UTC로 저장하고 조회 시 세션 타임존으로 변환하며, `TIMESTAMP WITHOUT TIME ZONE`은 타임존 변환 없이 그대로 저장한다.

```sql
-- PostgreSQL
CREATE TABLE orders (
    id         BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- 시스템 시각
    scheduled  TIMESTAMP NOT NULL                   -- 사용자가 지정한 시각
);
```

---

## UTC 저장 원칙

서버 여러 대가 다른 타임존에 있거나, 사용자가 전 세계에 퍼져 있는 서비스에서 타임존을 섞어서 저장하면 집계 쿼리가 망가진다.

```sql
-- 나쁜 예: 서버마다 다른 타임존으로 들어온 값이 섞임
SELECT DATE(created_at), COUNT(*)
FROM orders
GROUP BY DATE(created_at);
-- 서버 A는 KST, 서버 B는 UTC로 저장했다면 하루 기준이 달라진다
```

저장은 항상 UTC로 한다. 애플리케이션에서 타임존 변환을 담당하고, DB에는 UTC만 넣는다.

```java
// Spring Boot + JPA
@Column(name = "created_at")
private Instant createdAt; // Instant는 UTC 기준이다

// DB 연결 설정
spring.datasource.url=jdbc:mysql://host/db?serverTimezone=UTC
```

MySQL에서 서버 타임존을 확인하고 강제로 UTC로 맞추는 방법이다.

```sql
SELECT @@global.time_zone, @@session.time_zone;

-- my.cnf
[mysqld]
default-time-zone = '+00:00'
```

표시는 애플리케이션에서 한다. 사용자의 타임존을 알면 UTC 값을 변환해서 보여주면 된다. DB에 저장된 UTC 값을 직접 수정하면 안 된다.

---

## UTC 기준 DATE 컬럼 설계

`created_at` 같은 컬럼이 UTC로 저장돼 있어도, "오늘 주문" 같은 날짜 경계 쿼리는 어느 타임존을 기준으로 하느냐에 따라 결과가 달라진다.

```sql
-- MySQL: 서버가 UTC 기준일 때
SELECT COUNT(*) FROM orders
WHERE DATE(created_at) = '2024-01-01';
-- 2024-01-01 00:00:00 UTC ~ 2024-01-01 23:59:59 UTC 구간을 집계한다
-- KST 기준으로는 2024-01-01 09:00:00 ~ 2024-01-02 08:59:59 구간이 됨
```

한국 서비스에서 "1월 1일 주문"을 KST 자정부터 다음날 자정까지로 정의한다면, UTC 기준 범위로 변환해서 쿼리해야 한다.

```sql
-- KST 2024-01-01 00:00:00 ~ 23:59:59 에 해당하는 UTC 범위
SELECT COUNT(*) FROM orders
WHERE created_at >= '2023-12-31 15:00:00'  -- UTC
  AND created_at <  '2024-01-01 15:00:00'; -- UTC
```

이 변환은 애플리케이션에서 처리하는 게 가장 안전하다. DB에서 함수를 씌워 날짜를 추출하면 인덱스를 못 탄다.

날짜만 저장하는 컬럼(생일, 이벤트 날짜, 약속일 등)은 `DATE` 타입을 쓰되, 이 날짜가 어느 타임존 기준인지 명확히 정해야 한다. 대부분은 사용자 로컬 타임존 기준이고, 글로벌 서비스라면 타임존 컬럼을 함께 두는 방법이 있다.

```sql
CREATE TABLE events (
    id              BIGINT      NOT NULL AUTO_INCREMENT,
    user_id         BIGINT      NOT NULL,
    event_date      DATE        NOT NULL,   -- 사용자 현지 날짜
    user_timezone   VARCHAR(50) NOT NULL,   -- 'Asia/Seoul', 'America/New_York' 등
    created_at      DATETIME    NOT NULL,   -- UTC
    PRIMARY KEY (id)
);
```

`event_date`는 UTC 변환 없이 그대로 쓴다. "2024-01-01에 이벤트가 있다"는 건 사용자가 어디 있든 그 날짜 자체가 의미를 갖는 경우다. 시작 시각이 중요하면 DATETIME으로 바꾸고 UTC로 저장한다.

---

## TIMESTAMP WITH TIME ZONE 주의사항

PostgreSQL의 `TIMESTAMPTZ`는 타임존 정보를 함께 저장하는 게 아니다. UTC로만 저장하고, 조회 시 세션 타임존으로 변환해서 보여준다.

```sql
SET TIME ZONE 'Asia/Seoul';
INSERT INTO logs (created_at) VALUES ('2024-01-01 10:00:00+09');
-- 내부 저장값: 2024-01-01 01:00:00 UTC

SET TIME ZONE 'UTC';
SELECT created_at FROM logs;
-- 2024-01-01 01:00:00+00

SET TIME ZONE 'America/New_York';
SELECT created_at FROM logs;
-- 2023-12-31 20:00:00-05
```

저장된 값이 하나인데 어느 타임존으로 조회하느냐에 따라 다르게 보인다. DB 클라이언트로 직접 조회할 때 혼란스러운 이유가 여기에 있다.

### AT TIME ZONE 연산자

`AT TIME ZONE`은 타입에 따라 동작 방향이 반대다.

```sql
-- TIMESTAMPTZ AT TIME ZONE -> 해당 타임존의 로컬 TIMESTAMP (TZ 없음)
SELECT NOW() AT TIME ZONE 'Asia/Seoul';
-- 반환 타입: TIMESTAMP WITHOUT TIME ZONE

-- TIMESTAMP (without TZ) AT TIME ZONE -> TIMESTAMPTZ
SELECT '2024-01-01 10:00:00'::TIMESTAMP AT TIME ZONE 'Asia/Seoul';
-- 반환 타입: TIMESTAMPTZ (Asia/Seoul 기준 10시로 해석해서 UTC 변환)
```

이미 TIMESTAMPTZ인 값에 `AT TIME ZONE`을 붙이면 TZ 없는 TIMESTAMP가 나온다. 이걸 다시 TIMESTAMPTZ 컬럼과 비교하면 암묵적 형변환이 일어난다.

```sql
-- 의도와 다르게 동작할 수 있다
SELECT *
FROM orders
WHERE created_at AT TIME ZONE 'Asia/Seoul' > '2024-01-01 00:00:00';
-- created_at AT TIME ZONE 'Asia/Seoul'은 TIMESTAMP (without TZ)를 반환
-- '2024-01-01 00:00:00'와 비교 시 현재 세션 타임존 기준으로 해석됨
```

범위 조건은 TIMESTAMPTZ 값끼리 비교하는 방식이 안전하다.

```sql
-- 권장: 범위 경계를 TIMESTAMPTZ로 명시
SELECT *
FROM orders
WHERE created_at >= '2024-01-01 00:00:00+09:00'
  AND created_at <  '2024-01-02 00:00:00+09:00';
```

### DST 전환 구간

한국(Asia/Seoul)은 1988년 이후 DST가 없어서 KST는 항상 UTC+9다. 미국, 유럽 타임존을 다루면 DST 전환 구간에서 문제가 생긴다.

```sql
-- America/New_York, 2024년 3월 10일 02:00에 시계를 03:00으로 앞당김
-- 이 구간의 시각은 존재하지 않는다
SELECT '2024-03-10 02:30:00'::TIMESTAMP AT TIME ZONE 'America/New_York';
-- PostgreSQL은 이를 03:30 EDT로 처리한다 (비존재 시각 처리)

-- 11월 3일 02:00에 01:00으로 되돌림
-- 01:00~02:00 구간이 두 번 생긴다 (EDT와 EST 모두 해당)
SELECT '2024-11-03 01:30:00'::TIMESTAMP AT TIME ZONE 'America/New_York';
-- 어떤 01:30인지 모호하다 — PostgreSQL은 첫 번째(EDT)로 처리
```

DST가 있는 타임존의 로컬 시각을 UTC로 저장할 때, 모호한 구간의 처리 방식을 애플리케이션에서 명확히 정해야 한다. JDBC 드라이버와 ORM이 DST 처리를 내부적으로 하는데, 드라이버 버전마다 동작이 다를 수 있다.

---

## 인덱스 설계와 타임존

타임존 변환 함수를 WHERE 조건에 쓰면 인덱스를 못 탄다는 건 알고 있어도, 실제 쿼리 작성 시 놓치는 경우가 많다.

```sql
-- 인덱스 못 탐 (MySQL)
SELECT * FROM orders
WHERE DATE(created_at) = '2024-01-01';

-- 인덱스 못 탐 (PostgreSQL)
SELECT * FROM orders
WHERE (created_at AT TIME ZONE 'Asia/Seoul')::DATE = '2024-01-01';
```

두 쿼리 모두 `created_at` 인덱스를 쓰지 못하고 전체 테이블 스캔을 한다.

### 범위 조건으로 변환

인덱스를 타려면 범위 조건으로 바꿔야 한다.

```sql
-- KST 2024-01-01 기준으로 UTC 범위를 애플리케이션에서 계산
-- KST 00:00:00 = UTC 2023-12-31 15:00:00
-- KST 23:59:59 = UTC 2024-01-01 14:59:59

SELECT * FROM orders
WHERE created_at >= '2023-12-31 15:00:00'
  AND created_at <  '2024-01-01 15:00:00';
-- created_at 인덱스를 정상적으로 탄다
```

이 범위 계산을 애플리케이션에서 책임진다. 타임존 변환 로직이 여러 곳에 분산되지 않도록 유틸리티 함수나 레이어를 하나 정해서 처리하는 게 낫다.

### MySQL 8.0+ 생성 컬럼 인덱스

매번 범위 계산을 애플리케이션에서 하기 어려운 상황이라면 생성 컬럼(Generated Column)으로 KST 날짜를 저장해두는 방법이 있다.

```sql
ALTER TABLE orders
  ADD COLUMN created_date_kst DATE
    GENERATED ALWAYS AS (DATE(CONVERT_TZ(created_at, '+00:00', '+09:00'))) STORED;

CREATE INDEX idx_orders_created_date_kst ON orders(created_date_kst);

-- 이제 이 쿼리가 인덱스를 탄다
SELECT * FROM orders WHERE created_date_kst = '2024-01-01';
```

`STORED`로 지정하면 디스크에 저장되고 인덱스를 만들 수 있다. `VIRTUAL`은 디스크에 저장하지 않아 공간은 아끼지만 인덱스를 못 만든다.

`CONVERT_TZ` 함수는 MySQL의 타임존 테이블이 로드돼 있어야 한다. 설치 후 로드하지 않으면 NULL을 반환한다.

```bash
# 타임존 테이블 로드
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql
```

로드 여부는 `SELECT CONVERT_TZ('2024-01-01 00:00:00', '+00:00', 'Asia/Seoul');`로 확인한다. NULL이 나오면 테이블이 없는 것이다. named timezone 대신 offset('+09:00')을 쓰면 테이블 없이도 동작한다.

### PostgreSQL 함수형 인덱스

```sql
CREATE INDEX idx_orders_created_date_kst
  ON orders ((created_at AT TIME ZONE 'Asia/Seoul')::DATE);

-- 이 쿼리가 인덱스를 탄다
SELECT * FROM orders
WHERE (created_at AT TIME ZONE 'Asia/Seoul')::DATE = '2024-01-01';
```

함수형 인덱스는 인덱스 생성 후 `ANALYZE orders;`를 실행해야 플래너가 실행 계획에 반영한다. WHERE 절에서 정확히 같은 표현식을 써야 인덱스를 탄다. `(created_at AT TIME ZONE 'Asia/Seoul')::DATE`와 `date(timezone('Asia/Seoul', created_at))`는 동일한 결과지만 표현식이 달라서 인덱스를 못 타는 경우가 있다.

---

## 레거시 로컬타임 마이그레이션

서버 타임존이 KST였던 시절에 `DATETIME` 컬럼에 KST 시각을 저장했다가, UTC로 바꿔야 하는 상황이 생긴다. 마이그레이션 자체보다 범위를 파악하고 검증하는 과정이 더 어렵다.

### 현황 파악

```sql
-- MySQL: 현재 서버 타임존 확인
SELECT @@global.time_zone, @@session.time_zone;

-- 데이터 범위 확인
SELECT
    MIN(created_at),
    MAX(created_at),
    COUNT(*)
FROM orders;

-- TIMESTAMP 컬럼은 UTC로 자동 저장됐으므로
-- DATETIME 컬럼만 마이그레이션 대상이다
SHOW CREATE TABLE orders\G
```

어느 시점에 서버 타임존이 바뀌었는지 알면, 그 시점 전후로 데이터를 다르게 처리해야 할 수도 있다. 서버 설정 이력이 없으면 데이터 값의 분포나 서비스 런칭 날짜와 비교해서 추정해야 한다.

### MySQL CONVERT_TZ 마이그레이션

```sql
-- 마이그레이션 전 백업
CREATE TABLE orders_backup_20240101 AS SELECT * FROM orders;

-- KST(+09:00)로 저장된 값을 UTC로 변환
-- CONVERT_TZ(값, 원래_타임존, 변환할_타임존)
UPDATE orders
SET created_at = CONVERT_TZ(created_at, '+09:00', '+00:00'),
    updated_at = CONVERT_TZ(updated_at, '+09:00', '+00:00')
WHERE created_at IS NOT NULL;
```

`CONVERT_TZ`에 Named timezone('Asia/Seoul')을 쓰려면 타임존 테이블이 로드돼 있어야 한다. 로드 여부가 불확실하면 offset('+09:00')을 쓰는 게 안전하다. 한국은 DST가 없으므로 +09:00 고정 offset을 쓰면 된다.

행이 많으면 한 번에 전체를 UPDATE하지 않는다. 락이 오래 잡히고 언두 로그가 쌓인다.

```sql
-- 배치 업데이트 (id 기준으로 범위 분할)
UPDATE orders
SET created_at = CONVERT_TZ(created_at, '+09:00', '+00:00'),
    updated_at = CONVERT_TZ(updated_at, '+09:00', '+00:00')
WHERE id BETWEEN 1 AND 100000;

UPDATE orders
SET created_at = CONVERT_TZ(created_at, '+09:00', '+00:00'),
    updated_at = CONVERT_TZ(updated_at, '+09:00', '+00:00')
WHERE id BETWEEN 100001 AND 200000;
-- 반복
```

### PostgreSQL TIMESTAMP → TIMESTAMPTZ 마이그레이션

```sql
-- 1단계: 새 컬럼 추가
ALTER TABLE orders ADD COLUMN created_at_new TIMESTAMPTZ;

-- 2단계: 기존 TIMESTAMP 값을 Asia/Seoul 기준으로 해석해서 UTC 변환
-- created_at은 TIMESTAMP (without TZ)
-- AT TIME ZONE 'Asia/Seoul'은 이 시각을 서울 기준 로컬 시각으로 해석
-- 결과는 TIMESTAMPTZ (UTC 저장)
UPDATE orders
SET created_at_new = created_at AT TIME ZONE 'Asia/Seoul';

-- 3단계: NULL 없는지 확인
SELECT COUNT(*) FROM orders WHERE created_at_new IS NULL AND created_at IS NOT NULL;

-- 4단계: 컬럼 교체
BEGIN;
ALTER TABLE orders RENAME COLUMN created_at TO created_at_old;
ALTER TABLE orders RENAME COLUMN created_at_new TO created_at;
ALTER TABLE orders ALTER COLUMN created_at SET NOT NULL;
COMMIT;

-- 5단계: 검증 후 구 컬럼 삭제
ALTER TABLE orders DROP COLUMN created_at_old;
```

### 무중단 마이그레이션 순서

서비스 중단 없이 진행할 때는 컬럼을 추가하고 애플리케이션이 두 컬럼에 동시에 쓰는 기간을 둔다.

```
1. 새 UTC 컬럼 추가 (nullable)
2. 애플리케이션 배포: 두 컬럼에 동시 쓰기, 읽기는 기존 컬럼에서
3. 과거 데이터 배치 백필 (범위 분할 UPDATE)
4. 애플리케이션 배포: 읽기를 새 컬럼으로 전환
5. 기존 컬럼 쓰기 중단
6. 기존 컬럼 삭제
```

백필 중에 신규 데이터가 들어오는 구간이 있다. 신규 데이터는 처음부터 UTC로 들어오니, 백필 범위를 고정(마이그레이션 시작 시점의 최대 id나 시각)해두고 그 범위만 처리한다.

### 검증

```sql
-- 특정 날짜의 집계 결과를 마이그레이션 전후로 비교
-- 마이그레이션 전 (KST 기준 DATE로 집계)
SELECT DATE(created_at) AS day, COUNT(*)
FROM orders
WHERE created_at >= '2024-01-01' AND created_at < '2024-01-08'
GROUP BY day;

-- 마이그레이션 후 (UTC 저장, KST 기준으로 집계)
SELECT DATE(CONVERT_TZ(created_at, '+00:00', '+09:00')) AS day, COUNT(*)
FROM orders
WHERE created_at >= '2023-12-31 15:00:00' AND created_at < '2024-01-07 15:00:00'
GROUP BY day;
-- 집계 숫자가 일치해야 한다
```

레코드 수가 같아도 집계가 다르면 DST 전환 구간 데이터가 있거나, 마이그레이션 도중 신규 데이터가 섞인 경우다.

---

## 감사 컬럼 설계

거의 모든 테이블에 들어가는 `created_at`, `updated_at`, `deleted_at`는 설계 방식에 따라 인덱스 효율이 크게 달라진다.

### 기본 DDL

```sql
CREATE TABLE orders (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    user_id    BIGINT       NOT NULL,
    status     VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    created_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                     ON UPDATE CURRENT_TIMESTAMP(6),
    deleted_at DATETIME(6)  NULL,
    PRIMARY KEY (id)
);
```

`DATETIME(6)`은 마이크로초까지 저장한다. 같은 밀리초에 들어온 레코드를 구분해야 하는 감사 로그나 이벤트 테이블에서 필요하다. 일반적인 트랜잭션 데이터는 `DATETIME` 또는 `DATETIME(3)`(밀리초)으로 충분하다.

### Soft Delete와 인덱스

`deleted_at IS NULL` 조건을 거의 모든 쿼리에 붙인다면 인덱스를 어떻게 만드느냐가 성능에 직결된다.

```sql
-- 자주 하는 실수: 단일 인덱스
CREATE INDEX idx_orders_user ON orders(user_id);

-- 이 쿼리에서 위 인덱스는 deleted_at 조건을 커버하지 못한다
SELECT * FROM orders WHERE user_id = 100 AND deleted_at IS NULL;
```

`deleted_at`을 인덱스에 포함해야 한다.

```sql
-- user_id로 필터하고 deleted_at IS NULL을 추가 필터로 쓰는 복합 인덱스
CREATE INDEX idx_orders_user_active ON orders(user_id, deleted_at);
```

MySQL에서 `deleted_at IS NULL` 조건은 `deleted_at = NULL`이 아니다. `IS NULL`은 NULL 값을 가진 행을 찾는다. MySQL의 B-Tree 인덱스는 NULL을 저장하기 때문에 위 인덱스로 효율적으로 처리된다.

PostgreSQL은 partial index를 쓰면 더 명확하다.

```sql
-- 삭제되지 않은 행만 인덱싱
CREATE INDEX idx_orders_user_active ON orders(user_id)
WHERE deleted_at IS NULL;

-- 이 쿼리가 위 인덱스를 탄다
SELECT * FROM orders WHERE user_id = 100 AND deleted_at IS NULL;
```

삭제된 행이 전체 데이터의 30% 이상이면 partial index 효과가 크다. 삭제 비율이 낮으면 일반 인덱스와 차이가 별로 없다.

### updated_at ON UPDATE 주의사항

MySQL의 `ON UPDATE CURRENT_TIMESTAMP`는 해당 행의 어떤 컬럼이든 변경되면 자동으로 업데이트된다. 의도치 않게 `updated_at`이 바뀌는 상황이 생긴다.

```sql
-- status만 바꾸려 했는데 updated_at도 바뀐다
UPDATE orders SET status = 'SHIPPED' WHERE id = 1;

-- deleted_at을 SET하면 updated_at도 함께 바뀐다
UPDATE orders SET deleted_at = NOW() WHERE id = 1;
```

감사 목적으로 "언제 어느 컬럼이 바뀌었는지" 추적해야 하면 `ON UPDATE` 자동 갱신보다 애플리케이션에서 명시적으로 설정하는 게 낫다.

---

## SQL:2011 Temporal Tables

SQL:2011 표준에서 temporal tables 개념이 도입됐다. DB가 자동으로 행의 유효 기간을 관리해준다.

### System-Versioned Tables

행이 언제 생성되고 언제 삭제(또는 갱신)됐는지를 DB가 자동으로 기록한다. 과거 특정 시점의 데이터를 조회하는 게 가능해진다.

```sql
-- MariaDB 10.3+ 에서 지원
CREATE TABLE products (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    price       DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id)
) WITH SYSTEM VERSIONING;

-- 데이터 변경
UPDATE products SET price = 19900 WHERE id = 1;
UPDATE products SET price = 24900 WHERE id = 1;

-- 현재 데이터
SELECT * FROM products WHERE id = 1;
-- price = 24900

-- 과거 특정 시점 조회
SELECT * FROM products
FOR SYSTEM_TIME AS OF '2024-06-01 00:00:00'
WHERE id = 1;
-- 그 시점의 price가 나온다

-- 전체 이력 조회
SELECT *, ROW_START, ROW_END
FROM products
FOR SYSTEM_TIME ALL
WHERE id = 1
ORDER BY ROW_START;
```

`ROW_START`와 `ROW_END`는 DB가 관리하는 컬럼이다. 직접 수정할 수 없다.

PostgreSQL은 SQL:2011 temporal tables를 네이티브로 지원하지 않는다. 트리거나 `temporal_tables` 확장을 써야 한다.

### 이력 테이블 분리 패턴

표준 temporal tables 지원이 없거나, 이력 데이터를 별도로 관리하고 싶을 때 쓰는 방식이다.

```sql
CREATE TABLE products (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)   NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    updated_at  DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id)
);

CREATE TABLE products_history (
    history_id  BIGINT         NOT NULL AUTO_INCREMENT,
    product_id  BIGINT         NOT NULL,
    name        VARCHAR(100)   NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    valid_from  DATETIME(6)    NOT NULL,
    valid_to    DATETIME(6)    NOT NULL,
    PRIMARY KEY (history_id),
    INDEX idx_ph_product_time (product_id, valid_from, valid_to)
);

-- 트리거로 자동 이력 적재
DELIMITER $$
CREATE TRIGGER trg_products_after_update
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    INSERT INTO products_history (product_id, name, price, valid_from, valid_to)
    VALUES (OLD.id, OLD.name, OLD.price, OLD.updated_at, NEW.updated_at);
END$$
DELIMITER ;
```

---

## Bitemporal 모델링

Bitemporal은 두 개의 시간 축을 가진다.

- **Valid Time**: 데이터가 현실 세계에서 유효한 기간 ("이 가격은 2024년 1월부터 3월까지 적용됐다")
- **Transaction Time**: DB에 기록된 기간 ("이 정보는 2024년 1월 5일에 입력됐다")

둘을 같이 관리하면 "2024년 2월 기준으로, 3월에 수정 전의 데이터가 어땠는지"를 조회할 수 있다.

### 언제 필요한가

- 보험료, 세금, 급여처럼 소급 적용이 가능한 데이터
- 잘못 입력한 데이터를 수정하되 수정 이력도 남겨야 하는 경우
- 금융 규제에서 요구하는 완전한 감사 추적

### DDL

```sql
CREATE TABLE product_prices (
    id              BIGINT         NOT NULL AUTO_INCREMENT,
    product_id      BIGINT         NOT NULL,
    price           DECIMAL(10,2)  NOT NULL,

    -- Valid Time: 현실 세계에서 이 가격이 유효한 기간
    valid_from      DATE           NOT NULL,
    valid_to        DATE           NOT NULL DEFAULT '9999-12-31',

    -- Transaction Time: DB에 기록된 기간
    recorded_from   DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    recorded_to     DATETIME(6)    NOT NULL DEFAULT '9999-12-31 23:59:59.999999',

    PRIMARY KEY (id),
    INDEX idx_pp_product_valid (product_id, valid_from, valid_to),
    INDEX idx_pp_product_recorded (product_id, recorded_from, recorded_to)
);
```

### 데이터 삽입과 수정

```sql
-- 1월 1일: 2024년 1월부터 6월까지 가격이 19900원이라고 입력
INSERT INTO product_prices (product_id, price, valid_from, valid_to)
VALUES (1, 19900, '2024-01-01', '2024-06-30');
-- recorded_from = NOW(), recorded_to = '9999-12-31...'

-- 3월 1일: 실은 2월부터 가격이 24900원이었다고 수정 요청이 들어옴
-- 기존 레코드를 닫는다 (transaction time 종료)
UPDATE product_prices
SET recorded_to = CURRENT_TIMESTAMP(6)
WHERE product_id = 1
  AND valid_from = '2024-01-01'
  AND recorded_to = '9999-12-31 23:59:59.999999';

-- 수정된 정보를 새 레코드로 삽입
-- 1월 유효 기간 (2월 이전)
INSERT INTO product_prices (product_id, price, valid_from, valid_to)
VALUES (1, 19900, '2024-01-01', '2024-01-31');

-- 2월부터 6월 유효 기간
INSERT INTO product_prices (product_id, price, valid_from, valid_to)
VALUES (1, 24900, '2024-02-01', '2024-06-30');
```

### 조회 패턴

```sql
-- 현재 기준으로 현재 유효한 가격
SELECT price
FROM product_prices
WHERE product_id = 1
  AND valid_from <= CURDATE()
  AND valid_to >= CURDATE()
  AND recorded_from <= NOW()
  AND recorded_to > NOW();

-- 2월 1일 기준 유효한 가격 (과거 시점 조회)
SELECT price
FROM product_prices
WHERE product_id = 1
  AND valid_from <= '2024-02-01'
  AND valid_to >= '2024-02-01'
  AND recorded_from <= NOW()
  AND recorded_to > NOW();
-- 24900이 나온다 (3월에 수정된 결과가 반영됨)

-- 3월 1일 수정 전에 시스템이 알고 있던 2월 1일 기준 가격
SELECT price
FROM product_prices
WHERE product_id = 1
  AND valid_from <= '2024-02-01'
  AND valid_to >= '2024-02-01'
  AND recorded_from <= '2024-02-28 23:59:59'
  AND recorded_to > '2024-02-28 23:59:59';
-- 19900이 나온다 (수정 전에는 1월~6월 내내 19900으로 알고 있었음)
```

---

## 시간 기반 파티셔닝

시간 컬럼으로 파티셔닝하는 경우는 주로 두 가지다. 첫째, 조회 범위가 항상 특정 기간에 한정될 때. 둘째, 오래된 데이터를 파티션 단위로 삭제해야 할 때.

### RANGE 파티셔닝

```sql
CREATE TABLE access_logs (
    id         BIGINT       NOT NULL,
    user_id    BIGINT       NOT NULL,
    path       VARCHAR(500) NOT NULL,
    created_at DATETIME     NOT NULL,
    PRIMARY KEY (id, created_at)  -- 파티션 키가 PK에 포함돼야 한다
)
PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
    PARTITION p202401 VALUES LESS THAN (202402),
    PARTITION p202402 VALUES LESS THAN (202403),
    PARTITION p202403 VALUES LESS THAN (202404),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

파티션 프루닝이 되려면 WHERE 조건에 파티션 키가 있어야 한다.

```sql
-- 파티션 프루닝 동작: p202401 파티션만 스캔
SELECT * FROM access_logs
WHERE created_at >= '2024-01-01' AND created_at < '2024-02-01';

-- 파티션 프루닝 미동작: 전체 스캔
SELECT * FROM access_logs
WHERE MONTH(created_at) = 1;  -- 함수를 씌우면 프루닝이 안 된다
```

### 파티션 추가와 삭제

```sql
-- 새 달 파티션 추가 (p_future 이전에 넣어야 한다)
ALTER TABLE access_logs REORGANIZE PARTITION p_future INTO (
    PARTITION p202404 VALUES LESS THAN (202405),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 오래된 파티션 삭제 (DROP보다 빠르다 — 파티션 단위로 처리)
ALTER TABLE access_logs DROP PARTITION p202401;
```

파티션을 `DROP`하는 건 행 단위 `DELETE`보다 훨씬 빠르다. 파티션 자체의 데이터 파일을 삭제하기 때문이다. 로그 테이블에서 N개월 이상 된 데이터를 정기적으로 지워야 한다면 파티셔닝이 적합하다.

### 주의사항

MySQL에서 파티션 테이블의 PK는 파티션 키를 포함해야 한다.

```sql
-- 오류: created_at이 PK에 없으면 파티셔닝 불가
CREATE TABLE logs (
    id         BIGINT   NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id)        -- 여기에 created_at이 없으면 에러
) PARTITION BY RANGE (...);

-- 올바른 방식
PRIMARY KEY (id, created_at)
```

PK에 `created_at`이 포함되면 단순 `id`로 조회하는 쿼리도 파티션 키를 명시하지 않으면 전체 파티션을 스캔한다. 이 경우 글로벌 인덱스(MySQL은 미지원)나 애플리케이션 레벨에서 파티션 키를 같이 전달하는 방식으로 처리해야 한다.

---

## 예약과 반복 스케줄 모델링

예약 시스템과 반복 일정은 시간 데이터에서 모델링이 가장 까다로운 부분이다.

### 단순 예약

시작 시각과 종료 시각이 있는 단건 예약이다.

```sql
CREATE TABLE reservations (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    resource_id BIGINT       NOT NULL,  -- 예약 대상 (회의실, 장비 등)
    user_id     BIGINT       NOT NULL,
    start_at    DATETIME     NOT NULL,
    end_at      DATETIME     NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'CONFIRMED',
    created_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    deleted_at  DATETIME(6)  NULL,
    PRIMARY KEY (id),
    INDEX idx_res_resource_time (resource_id, start_at, end_at)
);

-- 겹치는 예약 확인
SELECT id FROM reservations
WHERE resource_id = 5
  AND deleted_at IS NULL
  AND start_at < '2024-03-15 14:00:00'  -- 새 예약 종료 시각
  AND end_at   > '2024-03-15 13:00:00'  -- 새 예약 시작 시각
LIMIT 1;
-- 결과가 있으면 충돌
```

겹침 조건을 잘못 쓰는 경우가 있다. `A.start < B.end AND A.end > B.start`가 맞다. NOT으로 뒤집으면 `A.start >= B.end OR A.end <= B.start` — 겹치지 않는 조건이다.

### 반복 일정 모델링

매주 월요일 오전 10시처럼 반복되는 일정을 어떻게 저장할지는 크게 두 가지 방향이 있다.

**방향 1: 규칙만 저장하고 인스턴스는 동적으로 생성**

```sql
CREATE TABLE schedules (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    title           VARCHAR(200) NOT NULL,
    recurrence_rule TEXT         NOT NULL,  -- iCalendar RRULE 형식
    start_time      TIME         NOT NULL,
    duration_min    INT          NOT NULL,
    effective_from  DATE         NOT NULL,
    effective_to    DATE         NULL,       -- NULL이면 무기한
    PRIMARY KEY (id)
);

-- 예시: 매주 월·수·금 오전 10시, 60분
INSERT INTO schedules (title, recurrence_rule, start_time, duration_min, effective_from)
VALUES (
    '주간 팀 미팅',
    'FREQ=WEEKLY;BYDAY=MO,WE,FR',
    '10:00:00',
    60,
    '2024-01-01'
);
```

iCalendar의 RRULE을 그대로 저장하고, 실제 발생 시각은 라이브러리(rrule.js, python-dateutil 등)로 계산한다. DB 조회만으로 "다음 N개 인스턴스"를 뽑기 어렵다. 특정 날짜에 어떤 일정이 있는지 알려면 전체 규칙을 메모리에 올려서 계산해야 한다.

**방향 2: 인스턴스를 테이블에 미리 생성**

```sql
CREATE TABLE schedule_rules (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    title           VARCHAR(200) NOT NULL,
    recurrence_rule TEXT         NOT NULL,
    start_time      TIME         NOT NULL,
    duration_min    INT          NOT NULL,
    effective_from  DATE         NOT NULL,
    effective_to    DATE         NULL,
    PRIMARY KEY (id)
);

CREATE TABLE schedule_instances (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    rule_id     BIGINT       NOT NULL,
    occurs_at   DATETIME     NOT NULL,  -- 이 인스턴스의 시작 시각
    ends_at     DATETIME     NOT NULL,
    is_modified TINYINT(1)   NOT NULL DEFAULT 0,  -- 단건 수정 여부
    is_deleted  TINYINT(1)   NOT NULL DEFAULT 0,  -- 단건 삭제 여부
    PRIMARY KEY (id),
    INDEX idx_si_occurs (occurs_at),
    INDEX idx_si_rule (rule_id, occurs_at),
    FOREIGN KEY (rule_id) REFERENCES schedule_rules(id)
);
```

배치로 미래 N주치 인스턴스를 미리 생성해 두면 날짜 범위 조회가 단순 인덱스 스캔으로 끝난다.

```sql
-- 특정 날의 일정 조회
SELECT si.*, sr.title
FROM schedule_instances si
JOIN schedule_rules sr ON si.rule_id = sr.id
WHERE si.occurs_at >= '2024-03-15 00:00:00'
  AND si.occurs_at <  '2024-03-16 00:00:00'
  AND si.is_deleted = 0;
```

단건 수정(이 인스턴스만 제목 변경)과 단건 삭제는 인스턴스 행에 플래그를 세우는 방식으로 처리한다. 규칙 전체를 건드리지 않는다.

**방향 1 vs 2 선택 기준**

방향 1은 관리가 단순하다. 규칙 하나만 수정하면 되고, 저장 공간도 적다. 단, 기간 내 조회 쿼리를 DB로 처리할 수 없다. 방향 2는 기간 조회, 충돌 검사, 알림 스케줄링 같은 작업을 DB 레벨에서 처리할 수 있다. 인스턴스를 미리 생성하는 배치가 필요하고, 규칙 변경 시 기존 인스턴스 처리 방식을 정해야 한다.

서비스에서 달력 뷰나 기간 검색이 필요하다면 방향 2가 낫다.

### 예외 처리 — 이 회차만 다르게

Google 캘린더에서 반복 일정 중 하나만 시간을 바꾸는 것처럼, 특정 인스턴스만 다르게 처리해야 하는 경우가 있다.

```sql
CREATE TABLE schedule_exceptions (
    id              BIGINT       NOT NULL AUTO_INCREMENT,
    rule_id         BIGINT       NOT NULL,
    original_date   DATE         NOT NULL,  -- 원래 발생 날짜 (식별자)
    occurs_at       DATETIME     NULL,       -- NULL이면 해당 인스턴스 삭제
    ends_at         DATETIME     NULL,
    title_override  VARCHAR(200) NULL,       -- NULL이면 원래 제목 사용
    PRIMARY KEY (id),
    UNIQUE KEY uq_se_rule_date (rule_id, original_date),
    FOREIGN KEY (rule_id) REFERENCES schedule_rules(id)
);
```

인스턴스를 조회할 때 예외 테이블을 LEFT JOIN해서 오버라이드된 값을 적용한다. 규칙 기반 계산과 예외를 합쳐서 최종 결과를 만든다.

---

## 시간 범위 겹침 방지 — DB 제약으로

애플리케이션에서 겹침을 검사해도 동시에 두 요청이 들어오면 레이스 컨디션이 생긴다. DB 레벨에서 막는 방법이 있다.

### PostgreSQL — EXCLUDE CONSTRAINT

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE reservations (
    id          BIGINT        NOT NULL GENERATED ALWAYS AS IDENTITY,
    resource_id BIGINT        NOT NULL,
    during      TSRANGE       NOT NULL,  -- 시간 범위 타입
    PRIMARY KEY (id),
    EXCLUDE USING GIST (
        resource_id WITH =,
        during WITH &&    -- &&는 겹침 연산자
    )
);

-- 겹치는 예약을 시도하면 오류
INSERT INTO reservations (resource_id, during)
VALUES (5, '[2024-03-15 13:00, 2024-03-15 14:00)');

INSERT INTO reservations (resource_id, during)
VALUES (5, '[2024-03-15 13:30, 2024-03-15 15:00)');
-- ERROR: conflicting key value violates exclusion constraint
```

`TSRANGE`는 시간 범위 타입이다. 포함(`[`)과 미포함(`(`)을 경계에서 구분한다. GIST 인덱스를 사용하기 때문에 btree_gist 확장이 필요하다.

### MySQL — 애플리케이션 + 배타 잠금

MySQL은 EXCLUDE CONSTRAINT를 지원하지 않는다. SELECT FOR UPDATE로 잠금을 걸고 검사하는 방식을 쓴다.

```sql
START TRANSACTION;

-- 겹치는 예약이 있는지 잠금을 걸고 확인
SELECT id FROM reservations
WHERE resource_id = 5
  AND start_at < '2024-03-15 14:00:00'
  AND end_at   > '2024-03-15 13:00:00'
  AND deleted_at IS NULL
FOR UPDATE;

-- 결과가 없으면 INSERT
INSERT INTO reservations (resource_id, user_id, start_at, end_at)
VALUES (5, 100, '2024-03-15 13:00:00', '2024-03-15 14:00:00');

COMMIT;
```

`FOR UPDATE`는 조회된 행에 배타 잠금을 건다. 결과가 없는 경우에는 잠금 대상이 없다. Gap lock이 작동하면 인서트가 블로킹될 수 있으니 InnoDB의 잠금 동작을 이해하고 사용해야 한다.
