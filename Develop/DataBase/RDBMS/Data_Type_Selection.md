---
title: 데이터 타입 선택
tags: [database, data-type, mysql, postgresql, varchar, decimal, timestamp, enum]
updated: 2026-04-08
---

# 데이터 타입 선택

## 개요

테이블 설계에서 컬럼 타입을 잘못 고르면 나중에 바꾸기가 매우 어렵다. 데이터가 수천만 건 쌓인 뒤에 ALTER TABLE로 타입을 변경하면 테이블 락이 걸리고, 서비스 다운타임이 발생한다. 처음 설계할 때 트래픽 규모와 데이터 특성을 고려해서 타입을 정해야 한다.

MySQL과 PostgreSQL은 같은 이름의 타입이라도 내부 동작이 다른 경우가 있다. 이 문서에서는 두 DB의 차이점도 함께 다룬다.

## PK 타입: INT vs BIGINT

### INT의 한계

INT(4바이트)의 최대값은 약 21억(2,147,483,647)이다. UNSIGNED로 쓰면 약 42억까지 늘어나지만, 이것도 한계가 있다.

```sql
-- MySQL
CREATE TABLE users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,  -- 최대 4,294,967,295
    name VARCHAR(50) NOT NULL
);

-- PostgreSQL (UNSIGNED 없음)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,  -- INT 범위: -2,147,483,648 ~ 2,147,483,647
    name VARCHAR(50) NOT NULL
);
```

하루에 INSERT가 10만 건이면 약 117년을 쓸 수 있으니 INT로 충분하다. 하지만 실무에서는 단순히 레코드 수만 보면 안 된다. soft delete로 지운 데이터, 테스트 중 생성한 데이터, 배치에서 실패 후 재시도한 데이터까지 모두 PK를 소모한다.

### BIGINT 전환 시점

BIGINT(8바이트)는 최대 약 922경이다. 사실상 고갈될 일이 없다.

INT에서 BIGINT로 전환해야 하는 시점:

- AUTO_INCREMENT 값이 INT 최대값의 50% 이상에 도달했을 때
- 일 INSERT 건수가 100만 건 이상인 테이블
- 다른 테이블의 FK로 많이 참조되는 테이블 (나중에 바꾸면 연쇄 ALTER가 필요)

```sql
-- MySQL: 현재 AUTO_INCREMENT 값 확인
SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mydb' AND TABLE_NAME = 'users';

-- PostgreSQL: 현재 시퀀스 값 확인
SELECT last_value FROM users_id_seq;
```

대규모 테이블에서 INT → BIGINT 변경은 온라인 DDL로도 시간이 오래 걸린다. MySQL의 경우 pt-online-schema-change나 gh-ost를 써야 서비스 영향을 최소화할 수 있다.

```bash
# pt-online-schema-change 사용 예시
pt-online-schema-change \
  --alter "MODIFY COLUMN id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT" \
  --execute D=mydb,t=users
```

처음 설계할 때 트래픽이 많은 서비스라면 PK는 BIGINT로 시작하는 게 낫다. 저장 공간 차이는 레코드당 4바이트뿐이다.

## VARCHAR 길이 산정

### 실제 저장 방식

MySQL InnoDB에서 VARCHAR는 실제 데이터 길이 + 1~2바이트(길이 정보)만큼 저장한다. VARCHAR(255)로 선언해도 10글자만 넣으면 10글자 + 1바이트만 차지한다. 그렇다고 무조건 VARCHAR(65535)로 잡으면 문제가 생긴다.

```sql
-- MySQL: 이렇게 하면 안 된다
CREATE TABLE products (
    name VARCHAR(65535)  -- 에러 발생. InnoDB 행 최대 크기 초과
);
```

MySQL InnoDB의 행 최대 크기는 약 65,535바이트다. 한 테이블에 VARCHAR 컬럼이 여러 개면 합산 길이에 주의해야 한다.

### 길이 기준 잡기

| 항목 | 권장 길이 | 근거 |
|------|----------|------|
| 이름(한글) | VARCHAR(50) | 한글 이름 최대 5자 정도지만, 외국인 이름까지 고려 |
| 이메일 | VARCHAR(254) | RFC 5321 표준 최대 길이 |
| 전화번호 | VARCHAR(20) | 국제번호 포함 최대 15자리 + 구분자 |
| URL | VARCHAR(2048) | 브라우저별 URL 최대 길이 기준 |
| 주소 | VARCHAR(200) | 한국 주소 체계 기준 충분 |
| 사용자 입력 제목 | VARCHAR(200) | UI에서 입력 제한을 함께 걸어야 한다 |

VARCHAR(255)와 VARCHAR(256)은 MySQL에서 실질적인 차이가 있다. 255 이하면 길이 저장에 1바이트, 256 이상이면 2바이트를 쓴다. 인덱스 크기에도 영향을 주므로 가능하면 255 이하로 잡는다.

### PostgreSQL에서의 차이

PostgreSQL은 VARCHAR(n)과 TEXT의 내부 저장 방식이 동일하다. 길이 제한이 필요 없으면 TEXT를 쓰는 게 PostgreSQL에서는 더 자연스럽다.

```sql
-- PostgreSQL: 둘 다 내부 구현이 같다
CREATE TABLE articles (
    title VARCHAR(200),
    content TEXT  -- PostgreSQL에서는 TEXT가 성능 차이 없음
);
```

MySQL은 TEXT와 VARCHAR의 동작이 다르다. TEXT는 별도 페이지에 저장될 수 있고, 정렬이나 인덱스 생성 시 제약이 있다.

## DECIMAL vs FLOAT: 금액 처리

### 부동소수점의 문제

금액을 FLOAT이나 DOUBLE로 저장하면 계산 오차가 발생한다. 이건 DB 문제가 아니라 IEEE 754 부동소수점 표현의 근본적인 한계다.

```sql
-- FLOAT의 오차 (MySQL)
CREATE TABLE test_float (amount FLOAT);
INSERT INTO test_float VALUES (0.1), (0.2);
SELECT SUM(amount) FROM test_float;
-- 결과: 0.30000000447034836 (0.3이 아님)

-- DECIMAL은 정확하다
CREATE TABLE test_decimal (amount DECIMAL(10,2));
INSERT INTO test_decimal VALUES (0.1), (0.2);
SELECT SUM(amount) FROM test_decimal;
-- 결과: 0.30
```

### DECIMAL 정밀도 설정

DECIMAL(M, D)에서 M은 전체 자릿수, D는 소수점 이하 자릿수다.

```sql
-- 원화: 소수점 없음
price DECIMAL(12, 0)  -- 최대 999,999,999,999원

-- 달러: 센트 단위
price_usd DECIMAL(10, 2)  -- 최대 99,999,999.99

-- 환율: 소수점 아래 자릿수가 많다
exchange_rate DECIMAL(12, 6)  -- 1234.567890
```

실무에서 자주 하는 실수가 DECIMAL(10, 2)로 잡아놓고 나중에 할인율(0.15)이나 세율(0.075)을 같은 컬럼에 넣으려다 정밀도가 부족한 경우다. 금액과 비율은 별도 컬럼으로 분리하고, 각각에 맞는 정밀도를 설정해야 한다.

### 저장 크기

DECIMAL의 저장 크기는 자릿수에 따라 달라진다. 9자리당 4바이트를 차지한다.

| 선언 | 저장 크기 |
|------|----------|
| DECIMAL(5,2) | 3바이트 |
| DECIMAL(10,2) | 5바이트 |
| DECIMAL(18,4) | 8바이트 |
| DECIMAL(38,6) | 17바이트 |

FLOAT는 4바이트, DOUBLE은 8바이트로 고정이다. 저장 공간만 보면 부동소수점이 효율적이지만, 금액이나 수량처럼 정확한 계산이 필요한 곳에서는 반드시 DECIMAL을 써야 한다.

과학 계산이나 센서 데이터처럼 근사값이 허용되는 경우에만 FLOAT/DOUBLE을 쓴다.

## DATETIME vs TIMESTAMP

### 핵심 차이

| | DATETIME | TIMESTAMP |
|---|---------|-----------|
| 저장 크기 (MySQL) | 5바이트 | 4바이트 |
| 범위 | 1000-01-01 ~ 9999-12-31 | 1970-01-01 ~ 2038-01-19 |
| 시간대 변환 | 없음 | 있음 (UTC 저장, 조회 시 세션 시간대로 변환) |

### 2038년 문제

TIMESTAMP는 내부적으로 Unix epoch(1970-01-01 00:00:00 UTC)부터의 초 수를 4바이트 정수로 저장한다. 2038-01-19 03:14:07 UTC를 넘기면 오버플로가 발생한다.

MySQL 8.0.28부터는 TIMESTAMP 범위를 확장하는 작업이 진행 중이지만, 아직은 주의가 필요하다. 생년월일, 계약 만료일 같은 미래 날짜를 저장해야 하면 DATETIME을 써야 한다.

### 시간대 처리

TIMESTAMP의 시간대 자동 변환이 편리해 보이지만, 실무에서 혼란을 일으키는 경우가 많다.

```sql
-- MySQL: 세션 시간대에 따라 조회 결과가 달라진다
SET time_zone = 'Asia/Seoul';
INSERT INTO events (event_time) VALUES ('2026-04-08 15:00:00');

SET time_zone = 'UTC';
SELECT event_time FROM events;
-- 결과: 2026-04-08 06:00:00 (9시간 차이)
```

서버가 여러 시간대에 배포되어 있으면 TIMESTAMP의 자동 변환이 도움이 된다. 하지만 대부분의 서비스에서는 DATETIME에 UTC로 통일하고 애플리케이션 레벨에서 시간대를 변환하는 방식이 더 예측 가능하다.

```sql
-- 실무에서 권장하는 방식
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### PostgreSQL의 경우

PostgreSQL은 TIMESTAMP WITH TIME ZONE(timestamptz)과 TIMESTAMP WITHOUT TIME ZONE을 구분한다. timestamptz는 입력 시 UTC로 변환해서 저장하고, 조회 시 클라이언트 시간대로 변환한다.

```sql
-- PostgreSQL: timestamptz 권장
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

PostgreSQL 공식 문서에서도 대부분의 경우 timestamptz를 쓰라고 권장한다. MySQL의 TIMESTAMP처럼 동작하지만, 2038년 문제가 없다(8바이트 저장).

## ENUM 타입

### MySQL ENUM의 함정

ENUM은 코드에서 상수 값을 관리하기 편하다는 이유로 많이 쓰이지만, 운영 환경에서 값 추가가 필요하면 ALTER TABLE이 필요하다.

```sql
-- 초기 설계
CREATE TABLE orders (
    status ENUM('pending', 'paid', 'shipped', 'delivered') NOT NULL
);

-- 반품 상태 추가 → ALTER TABLE 필요
ALTER TABLE orders MODIFY COLUMN status 
    ENUM('pending', 'paid', 'shipped', 'delivered', 'returned') NOT NULL;
```

MySQL 8.0에서는 ENUM 끝에 값을 추가하는 ALTER TABLE이 INSTANT 알고리즘으로 처리되어 빠르게 완료된다. 하지만 중간에 값을 삽입하거나 기존 값을 변경하면 테이블 재구성이 필요하다.

ENUM에 값이 5개 이상이 되거나, 값이 자주 변경될 가능성이 있으면 별도 참조 테이블이나 VARCHAR + CHECK 제약조건으로 대체하는 게 낫다.

```sql
-- 대안 1: 참조 테이블
CREATE TABLE order_status (
    code VARCHAR(20) PRIMARY KEY,
    label VARCHAR(50) NOT NULL
);

CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    status_code VARCHAR(20) NOT NULL,
    FOREIGN KEY (status_code) REFERENCES order_status(code)
);

-- 대안 2: VARCHAR + CHECK (MySQL 8.0.16+)
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    CHECK (status IN ('pending', 'paid', 'shipped', 'delivered', 'returned'))
);
```

### PostgreSQL ENUM

PostgreSQL의 ENUM은 별도 타입으로 생성하며, 값 추가가 ALTER TYPE으로 가능하다.

```sql
-- PostgreSQL: 타입 생성
CREATE TYPE order_status AS ENUM ('pending', 'paid', 'shipped', 'delivered');

-- 값 추가 (테이블 잠금 없음)
ALTER TYPE order_status ADD VALUE 'returned';
```

PostgreSQL에서는 ENUM 값 추가가 테이블 락 없이 처리되므로 MySQL보다 부담이 적다. 하지만 값 삭제나 이름 변경은 여전히 까다롭다.

## TEXT/BLOB 분리 저장

### 왜 분리해야 하는가

TEXT나 BLOB 컬럼이 있는 테이블에서 SELECT *를 하면 대용량 데이터까지 모두 읽어온다. MySQL InnoDB에서 TEXT/BLOB 데이터가 일정 크기를 초과하면 overflow 페이지에 저장되는데, 이 페이지를 읽는 I/O가 추가로 발생한다.

```sql
-- 나쁜 설계: 본문을 같은 테이블에 저장
CREATE TABLE articles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author_id BIGINT NOT NULL,
    content LONGTEXT,           -- 본문이 수 MB일 수 있음
    thumbnail MEDIUMBLOB,       -- 이미지 바이너리
    created_at DATETIME NOT NULL
);

-- 목록 조회할 때 content와 thumbnail까지 불필요하게 읽힘
SELECT * FROM articles ORDER BY created_at DESC LIMIT 20;
```

```sql
-- 개선된 설계: 대용량 데이터 분리
CREATE TABLE articles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE article_contents (
    article_id BIGINT PRIMARY KEY,
    content LONGTEXT NOT NULL,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

목록 조회는 articles 테이블만 읽고, 상세 조회 시에만 article_contents를 JOIN한다. 쿼리에서 필요한 컬럼만 SELECT하면 된다고 생각할 수 있지만, 테이블 분리는 버퍼 풀 효율에도 영향을 준다. TEXT가 섞인 테이블은 페이지당 담을 수 있는 행 수가 적어지므로, 같은 양의 데이터를 캐시하려면 더 많은 메모리가 필요하다.

### 이미지/파일은 DB에 넣지 않는다

BLOB으로 이미지를 저장하는 건 특수한 경우가 아니면 피해야 한다. DB 백업 크기가 불필요하게 커지고, DB 서버의 네트워크 대역폭을 소모한다. 파일은 S3 같은 오브젝트 스토리지에 저장하고, DB에는 URL만 저장한다.

```sql
CREATE TABLE user_profiles (
    user_id BIGINT PRIMARY KEY,
    -- avatar MEDIUMBLOB,  -- 이렇게 하지 않는다
    avatar_url VARCHAR(500),  -- S3 URL만 저장
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## CHAR vs VARCHAR

### 저장 방식 차이

CHAR(n)은 고정 길이로, 항상 n바이트를 차지한다. VARCHAR(n)은 가변 길이로, 실제 데이터 길이만큼만 차지한다.

```sql
-- CHAR: 고정 길이 (값이 짧으면 공백으로 패딩)
country_code CHAR(2)      -- 항상 2바이트: 'KR', 'US', 'JP'
gender CHAR(1)             -- 항상 1바이트: 'M', 'F'

-- VARCHAR: 가변 길이
name VARCHAR(50)           -- 실제 길이 + 1바이트
```

### 언제 CHAR를 써야 하는가

CHAR가 VARCHAR보다 나은 경우는 값의 길이가 항상 같을 때다.

| 데이터 | 타입 | 이유 |
|--------|------|------|
| 국가 코드 | CHAR(2) | ISO 3166-1 alpha-2, 항상 2자리 |
| 통화 코드 | CHAR(3) | ISO 4217, 항상 3자리 |
| UUID (하이픈 제거) | CHAR(32) | 항상 32자 hex |
| MD5 해시 | CHAR(32) | 항상 32자 |
| Y/N 플래그 | CHAR(1) | 항상 1자 |

고정 길이 데이터에 CHAR를 쓰면 MySQL InnoDB에서 행 크기를 예측할 수 있어 페이지 분할이 줄어든다. 하지만 이 차이가 체감될 정도의 성능 향상을 가져오는 경우는 드물다. UUID를 CHAR(36)으로 저장하는 것보다 BINARY(16)으로 저장하는 게 공간 효율이 2배 이상 좋다.

```sql
-- UUID 저장: CHAR(36)보다 BINARY(16)
CREATE TABLE sessions (
    id BINARY(16) PRIMARY KEY DEFAULT (UUID_TO_BIN(UUID())),
    user_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 조회 시 변환
SELECT BIN_TO_UUID(id) AS session_id FROM sessions WHERE user_id = 123;
```

### PostgreSQL에서는 CHAR를 쓸 이유가 거의 없다

PostgreSQL에서 CHAR(n)은 내부적으로 공백 패딩 후 저장하지만, 비교 시 trailing space를 무시하는 등 예상과 다르게 동작한다. PostgreSQL 공식 문서에서도 VARCHAR나 TEXT를 권장한다.

## MySQL과 PostgreSQL 타입별 저장 크기 비교

### 정수

| 타입 | MySQL 크기 | PostgreSQL 타입 | PostgreSQL 크기 |
|------|-----------|----------------|----------------|
| TINYINT | 1바이트 | SMALLINT으로 대체 | 2바이트 |
| SMALLINT | 2바이트 | SMALLINT | 2바이트 |
| MEDIUMINT | 3바이트 | INTEGER로 대체 | 4바이트 |
| INT | 4바이트 | INTEGER | 4바이트 |
| BIGINT | 8바이트 | BIGINT | 8바이트 |

MySQL의 TINYINT, MEDIUMINT는 PostgreSQL에 없다. PostgreSQL로 마이그레이션할 때 TINYINT → SMALLINT, MEDIUMINT → INTEGER로 매핑해야 한다.

MySQL에서 INT(11) 같은 표시 너비 지정은 저장 크기와 무관하다. MySQL 8.0.17부터는 표시 너비가 deprecated되었다.

### 문자열

| 타입 | MySQL | PostgreSQL |
|------|-------|-----------|
| CHAR(n) | 고정 n바이트 | 고정 n바이트 (공백 패딩) |
| VARCHAR(n) | 가변 + 1~2바이트 | 가변 + 4바이트 (varlena 헤더) |
| TEXT | max 65,535바이트 | 무제한 (TOAST) |
| MEDIUMTEXT | max 16MB | TEXT로 대체 |
| LONGTEXT | max 4GB | TEXT로 대체 |

PostgreSQL은 TEXT 크기 제한이 없고, TOAST 메커니즘으로 자동 압축/분리 저장한다. MySQL처럼 TINYTEXT, MEDIUMTEXT, LONGTEXT를 구분할 필요가 없다.

### 날짜/시간

| 타입 | MySQL 크기 | PostgreSQL 크기 |
|------|-----------|----------------|
| DATE | 3바이트 | 4바이트 |
| DATETIME | 5바이트 | 해당 없음 (TIMESTAMP 사용) |
| TIMESTAMP | 4바이트 | 8바이트 |
| TIME | 3바이트 | 8바이트 |

PostgreSQL의 TIMESTAMP는 8바이트로 MySQL보다 크지만, 마이크로초 정밀도를 지원하고 2038년 문제가 없다.

## 실무에서 자주 발생하는 실수

### BOOLEAN 타입

MySQL에는 진짜 BOOLEAN이 없다. BOOLEAN은 TINYINT(1)의 alias다. 저장 시 0과 1로 들어가지만, 2나 -1 같은 값도 넣을 수 있다.

```sql
-- MySQL: BOOLEAN = TINYINT(1)
CREATE TABLE users (
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO users (is_active) VALUES (2);  -- 에러 안 남
SELECT * FROM users WHERE is_active = TRUE;  -- is_active = 1인 것만 조회 (2는 안 나옴)
```

PostgreSQL은 진짜 BOOLEAN 타입이 있어서 TRUE, FALSE, NULL만 허용한다.

### JSON 타입

MySQL 5.7부터 JSON 타입을 지원한다. TEXT에 JSON 문자열을 넣는 것보다 JSON 타입이 낫다. 유효성 검사를 DB 레벨에서 해주고, 내부적으로 바이너리 형태로 저장해서 개별 키 접근 시 전체 파싱이 필요 없다.

```sql
-- MySQL: JSON 타입 사용
CREATE TABLE products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    attributes JSON NOT NULL
);

-- 특정 키로 조회
SELECT id, attributes->>'$.color' AS color
FROM products
WHERE attributes->>'$.size' = 'L';

-- 가상 컬럼 + 인덱스로 JSON 필드 검색 성능 개선
ALTER TABLE products
    ADD COLUMN color VARCHAR(20) GENERATED ALWAYS AS (attributes->>'$.color') STORED,
    ADD INDEX idx_color (color);
```

PostgreSQL은 JSON과 JSONB 두 가지를 지원한다. JSONB는 바이너리 형태로 저장되어 읽기가 빠르고 GIN 인덱스를 지원한다. 대부분의 경우 JSONB를 쓴다.

```sql
-- PostgreSQL: JSONB + GIN 인덱스
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    attributes JSONB NOT NULL
);

CREATE INDEX idx_attributes ON products USING GIN (attributes);

-- JSONB 연산자로 조회
SELECT id FROM products WHERE attributes @> '{"color": "red"}';
```

JSON 컬럼은 스키마가 유동적인 데이터에 적합하지만, 정형화된 데이터를 JSON에 넣으면 쿼리가 복잡해지고 인덱스 활용이 어려워진다. 컬럼으로 분리할 수 있는 데이터는 컬럼으로 분리한다.
