---
title: Collation
tags: [collation, mysql, postgresql, encoding, unicode, korean, database, index]
updated: 2026-08-05
---

# Collation

Collation은 문자열을 비교하고 정렬하는 규칙 집합이다. 문자 집합(character set)이 "어떤 문자를 표현하는가"를 정의한다면, collation은 "그 문자들을 어떤 순서로 비교하는가"를 정의한다.

'a'와 'A'가 같은가, 'é'와 'e'가 같은가, '가'가 '나'보다 앞인가. 이 질문에 대한 답이 collation마다 다르다. 개발하다 보면 collation 때문에 검색이 안 되거나, 정렬이 뒤죽박죽되거나, 두 테이블을 조인할 때 "Illegal mix of collations" 에러를 만나는 경우가 생긴다.

---

## _ci / _cs / _bin / _ai / _as 옵션

collation 이름에 붙는 접미사가 동작 방식을 결정한다.

`_ci` (case-insensitive): 대소문자를 구분하지 않는다. `'A' = 'a'`가 true다. 대부분의 애플리케이션에서 기본으로 쓴다.

`_cs` (case-sensitive): 대소문자를 구분한다. `'A' != 'a'`다. 토큰, API 키, 코드 등 정확한 매칭이 필요한 컬럼에 쓴다.

`_bin` (binary): 바이트값으로 비교한다. 'A'(0x41)는 'a'(0x61)와 다르다. 대소문자뿐 아니라 악센트도 구분한다. 가장 빠르고 예측 가능하다. 정규식 파서, 코드 저장소 같은 곳에서 쓸 만하다.

`_ai` (accent-insensitive): 악센트를 무시한다. 'e'와 'é'를 같다고 취급한다.

`_as` (accent-sensitive): 악센트를 구분한다.

MySQL의 `utf8mb4_0900_ai_ci`는 accent-insensitive, case-insensitive 조합이다. `utf8mb4_0900_as_cs`는 accent-sensitive, case-sensitive 조합이다.

---

## MySQL collation 체계

MySQL에서 `utf8mb4` 문자 집합을 쓸 때 선택할 수 있는 주요 collation이 세 개다.

### utf8mb4_general_ci

MySQL 5.x 시절 기본값이다. Unicode 표준 정렬 알고리즘(DUCET)을 완전히 따르지 않는다. 성능을 위해 단순화한 규칙을 쓴다. 독일어의 'ß'(에스체트)를 's'와 같다고 취급하지 않는 등 일부 유럽 언어 정렬이 틀리다. 레거시 프로젝트에서 그냥 굴러가고 있는 상황이 많다.

### utf8mb4_unicode_ci

Unicode Collation Algorithm(UCA) 4.0 기반이다. `general_ci`보다 언어적으로 정확하다. 독일어 'ß'를 'ss'와 동일하게 취급하고, 각종 악센트 문자도 표준에 맞게 처리한다. `general_ci`보다 약간 느리지만 그 차이가 실무에서 문제가 되는 경우는 드물다.

### utf8mb4_0900_ai_ci

MySQL 8.0부터 기본값이다. UCA 9.0 기반이다. `unicode_ci`와 비교해서 성능이 개선됐고, Unicode 최신 표준을 반영한다. MySQL 8.0 이상을 쓴다면 이걸 쓰면 된다.

한 가지 주의할 점이 있다. `utf8mb4_0900_ai_ci`는 MySQL 8.0 전용이다. MySQL 5.7, MariaDB와 호환이 안 된다. 여러 DB 버전을 같이 써야 하는 환경이라면 `utf8mb4_unicode_ci`가 안전하다.

실제 차이를 쿼리로 확인할 수 있다.

```sql
-- 세 collation 비교
SELECT 
    'ß' = 'ss' COLLATE utf8mb4_general_ci  AS general_ci,   -- 0 (다름)
    'ß' = 'ss' COLLATE utf8mb4_unicode_ci  AS unicode_ci,   -- 1 (같음)
    'ß' = 'ss' COLLATE utf8mb4_0900_ai_ci  AS ai_ci;        -- 0 (다름, UCA 9.0 변경)

SELECT 
    'cafe' = 'café' COLLATE utf8mb4_general_ci  AS general_ci,  -- 1
    'cafe' = 'café' COLLATE utf8mb4_unicode_ci  AS unicode_ci,  -- 1
    'cafe' = 'café' COLLATE utf8mb4_0900_ai_ci  AS ai_ci;       -- 1 (ai = accent-insensitive)
```

---

## PostgreSQL collation

PostgreSQL의 collation 체계는 MySQL과 다르다. OS 로케일 기반과 ICU 두 가지 방식이 있다.

### 로케일 기반 collation

PostgreSQL은 기본적으로 OS의 로케일 설정을 사용한다. DB 클러스터 초기화 시 `--locale`로 지정하거나 `initdb` 시 결정된다.

```sql
-- 현재 DB의 collation 확인
SELECT datname, datcollate, datctype FROM pg_database;

-- 사용 가능한 collation 목록
SELECT collname, collprovider, colllocale FROM pg_collation LIMIT 20;
```

`collprovider`가 'c'면 libc 기반, 'i'면 ICU 기반이다.

### ICU collation (PostgreSQL 10+)

ICU(International Components for Unicode) 라이브러리 기반 collation이다. 로케일 기반보다 언어별 정렬이 정확하다. 한국어, 일본어, 중국어 같은 CJK 문자 처리에서 차이가 생긴다.

```sql
-- ICU collation 생성
CREATE COLLATION ko_kr_icu (
    provider = icu,
    locale = 'ko-KR'
);

-- 컬럼에 ICU collation 적용
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT COLLATE ko_kr_icu
);
```

ICU collation을 쓰려면 PostgreSQL이 ICU 라이브러리와 함께 컴파일된 환경이어야 한다. `pg_collation` 뷰에서 `collprovider = 'i'`인 항목이 있으면 ICU를 지원하는 것이다.

### 표현식 단위 collation 지정

PostgreSQL에서는 쿼리 단위로 collation을 지정할 수 있다.

```sql
-- 대소문자 무시 정렬
SELECT name FROM users ORDER BY name COLLATE "en-US-x-icu";

-- 특정 컬럼만 collation 변경
SELECT * FROM products 
WHERE name COLLATE "ko-KR-x-icu" = '사과';
```

---

## 한국어 정렬 이슈

한국어 정렬은 가나다순(사전순)과 코드포인트순이 다르다.

유니코드에서 완성형 한글(가~힣)은 U+AC00부터 U+D7A3에 순서대로 배치돼 있다. 코드포인트 순서가 곧 가나다순이 된다. 이 부분은 운이 좋게 일치한다.

문제는 한글이 아닌 다른 문자와 섞일 때 생긴다. 영문자, 숫자, 특수문자가 섞인 목록을 정렬할 때 collation마다 순서가 달라진다.

```sql
-- MySQL에서 한글-영문 혼합 정렬
SELECT name FROM products ORDER BY name;
-- utf8mb4_unicode_ci 기준:
-- 숫자 → 영문 → 한글 순으로 정렬
-- (실제 순서는 UCA 가중치 테이블 기준)
```

자모(ㄱ, ㄴ, ㅏ, ㅓ 등)는 완성형 한글과 다른 코드포인트 범위에 있다. 자모(U+1100~U+11FF)는 완성형 한글(U+AC00~)보다 코드포인트가 앞이다. `_bin` collation이나 코드포인트 정렬에서 자모가 완성형 한글보다 앞에 온다.

MySQL에서 한국어 정렬이 이상하게 나오는 상황 대부분은 collation 설정이 잘못됐거나 `_bin`으로 설정된 컬럼에서 정렬했을 때다.

PostgreSQL에서 한국어 가나다순 정렬이 필요하면 ICU collation을 써야 한다. OS 로케일 기반 collation은 한국어 정렬이 기대대로 동작하지 않는 경우가 있다.

```sql
-- PostgreSQL: ICU 기반 한국어 정렬
SELECT name 
FROM products 
ORDER BY name COLLATE "ko-KR-x-icu";
```

---

## collation 불일치로 인한 인덱스 미사용·오류

### Illegal mix of collations (MySQL)

두 값의 collation이 다르면 MySQL이 비교를 거부한다.

```sql
-- 에러 발생 상황
SELECT u.name, o.product_name
FROM users u
JOIN orders o ON u.name = o.customer_name;
-- ERROR 1267: Illegal mix of collations (utf8mb4_unicode_ci,IMPLICIT)
-- and (utf8mb4_general_ci,IMPLICIT) for operation '='
```

`users.name`이 `utf8mb4_unicode_ci`고 `orders.customer_name`이 `utf8mb4_general_ci`면 이 에러가 난다. 테이블을 DB 레벨 collation 기본값이 다른 환경에서 각각 만들었을 때 생기는 경우가 많다.

임시 해결은 쿼리에 COLLATE를 명시하는 것이다.

```sql
SELECT u.name, o.product_name
FROM users u
JOIN orders o ON u.name = o.customer_name COLLATE utf8mb4_unicode_ci;
```

근본 해결은 컬럼 collation을 일치시키는 것이다.

```sql
ALTER TABLE orders 
MODIFY COLUMN customer_name VARCHAR(100) 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 인덱스 미사용

쿼리의 collation과 인덱스의 collation이 다르면 인덱스를 못 쓴다.

```sql
-- name 컬럼이 utf8mb4_unicode_ci로 인덱스가 만들어진 상황
SELECT * FROM users WHERE name = '홍길동' COLLATE utf8mb4_general_ci;
-- EXPLAIN 하면 type=ALL, 풀스캔
```

함수나 표현식으로 감싸도 인덱스를 못 쓴다.

```sql
-- 인덱스 미사용
SELECT * FROM users WHERE LOWER(name) = 'admin';

-- _ci collation이면 그냥 이렇게 쓰면 인덱스를 탄다
SELECT * FROM users WHERE name = 'admin';
```

`_ci` collation 컬럼에서는 대소문자 구분 없는 검색 시 LOWER()를 쓸 필요가 없다. 오히려 쓰면 인덱스를 못 쓴다.

---

## 컬럼·연결·DB 레벨 collation 설정

### MySQL: 레벨별 설정

MySQL은 서버 → DB → 테이블 → 컬럼 순서로 collation이 상속된다. 하위 레벨에서 명시하면 상위 설정을 무시한다.

```sql
-- DB 레벨 설정
CREATE DATABASE myapp
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 테이블 레벨 설정 (DB 설정 무시)
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 컬럼 레벨 설정 (테이블 설정 무시)
CREATE TABLE products (
    id INT PRIMARY KEY,
    name VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    code VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin
);
```

`code` 컬럼에 `_bin`을 적용하면 대소문자 구분 검색이 된다. 상품 코드나 UUID처럼 정확한 매칭이 필요한 컬럼에 유용하다.

MySQL 클라이언트 연결 시 `character_set_connection`과 `collation_connection`이 설정된다. 쿼리 내 리터럴 문자열의 collation이 이 값에 따른다.

```sql
-- 연결 설정 확인
SHOW VARIABLES LIKE 'collation%';

-- 연결 레벨 설정
SET collation_connection = utf8mb4_unicode_ci;
```

Spring Boot에서 HikariCP를 쓰는 경우 datasource URL에 connectionInitSql로 설정하거나, MySQL JDBC URL에 `connectionCollation=utf8mb4_unicode_ci`를 추가한다.

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/myapp?characterEncoding=UTF-8&connectionCollation=utf8mb4_unicode_ci
```

### PostgreSQL: DB 레벨 설정

```sql
-- DB 생성 시 collation 설정
CREATE DATABASE myapp
    ENCODING 'UTF8'
    LC_COLLATE 'ko_KR.UTF-8'
    LC_CTYPE 'ko_KR.UTF-8';
```

PostgreSQL은 DB 생성 후 `LC_COLLATE`를 변경할 수 없다. 처음부터 정하거나, 새 DB를 만들어서 데이터를 이전해야 한다.

컬럼 단위로는 변경 가능하다.

```sql
ALTER TABLE products 
ALTER COLUMN name TYPE TEXT COLLATE "ko-KR-x-icu";
```

---

## collation 변경 시 인덱스 재구성

컬럼 collation을 변경하면 해당 컬럼에 걸린 인덱스를 재구성해야 한다. MySQL은 `ALTER TABLE ... MODIFY COLUMN`으로 collation을 변경하면 인덱스도 자동으로 재구성된다. 테이블 크기에 따라 시간이 오래 걸린다.

```sql
-- MySQL: 컬럼 collation 변경 (테이블 재구성 발생)
ALTER TABLE users 
MODIFY COLUMN name VARCHAR(100) 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 진행 상황 확인 (다른 세션에서)
SELECT * FROM information_schema.INNODB_SESSION_TEMP_TABLE_INFO;
SHOW PROCESSLIST;
```

대형 테이블에서 이 작업을 운영 중에 하면 테이블 락이 걸린다. `pt-online-schema-change`나 `gh-ost` 같은 무중단 스키마 변경 도구를 써야 한다.

PostgreSQL에서 컬럼 collation을 변경하면 해당 컬럼 인덱스를 수동으로 재생성해야 한다.

```sql
-- PostgreSQL: 컬럼 collation 변경 후 인덱스 재생성
ALTER TABLE users 
ALTER COLUMN name TYPE TEXT COLLATE "ko-KR-x-icu";

-- 기존 인덱스 삭제 후 재생성
DROP INDEX idx_users_name;
CREATE INDEX idx_users_name ON users (name COLLATE "ko-KR-x-icu");
```

PostgreSQL 12+에서는 `REINDEX CONCURRENTLY`로 서비스 중단 없이 인덱스를 재구성할 수 있다.

```sql
REINDEX INDEX CONCURRENTLY idx_users_name;
```

collation 불일치를 나중에 고치는 비용이 크다. 프로젝트 초기에 DB 레벨 collation을 정하고, 테이블·컬럼 생성 시 명시적으로 지정하는 습관을 들이는 게 낫다. 특히 여러 사람이 개발 환경을 각자 세팅하면 개발 DB와 운영 DB의 collation이 달라지는 경우가 생긴다. `CREATE DATABASE` 스크립트나 마이그레이션 파일에 collation을 명시해서 환경 차이를 막아야 한다.
