---
title: Valid Time
tags: [database, rdbms]
updated: 2026-07-31
---

# Valid Time

## Valid Time이란

Valid Time은 데이터가 현실 세계에서 유효한 기간을 의미한다. DB에 언제 저장됐는지가 아니라, 실제로 그 값이 적용되는 시점을 다룬다.

"김철수의 연봉은 2024년 1월 1일부터 2024년 12월 31일까지 5천만원이었다"에서 `2024-01-01 ~ 2024-12-31`이 valid time이다.

Temporal_Data_Modeling.md에서 bitemporal 모델을 소개할 때 valid time과 transaction time을 구분한 바 있다. 이 문서는 valid time만 깊이 다룬다.

---

## Valid Time vs Transaction Time

실무에서 둘을 혼용하는 경우가 많다. 개념 차이를 명확히 잡지 않으면 쿼리 패턴도 잘못 설계된다.

**Valid Time (Application Time)**

현실에서 데이터가 유효한 기간이다. 과거 소급이 가능하고, 미래 예정 기간도 저장할 수 있다. 애플리케이션이 관리한다.

예: 직원 A가 팀장 직급을 `2023-06-01`부터 가졌다고 나중에 확정됐을 때, `valid_from = 2023-06-01`로 기록한다.

**Transaction Time (System Time)**

DB에 데이터가 기록된 시점이다. 과거로 소급하거나 미래를 지정할 수 없다. DB가 자동 관리한다.

예: 위 직원 정보가 실제로 DB에 INSERT된 시각이 `2023-06-15`라면 `recorded_from = 2023-06-15`다.

**쿼리 패턴 차이**

valid time 조회는 비즈니스 질문에 답한다.

```sql
-- "2023년 8월에 팀장이었던 직원은?"
SELECT employee_id
FROM employee_positions
WHERE position = 'TEAM_LEAD'
  AND valid_from <= '2023-08-31'
  AND valid_to   >  '2023-08-01';
```

transaction time 조회는 감사 질문에 답한다.

```sql
-- "2023년 6월 20일에 시스템이 알고 있던 팀장 목록은?"
SELECT employee_id
FROM employee_positions
WHERE position = 'TEAM_LEAD'
  AND recorded_from <= '2023-06-20'
  AND recorded_to   >  '2023-06-20'
  AND valid_from    <= CURDATE()
  AND valid_to      >  CURDATE();
```

두 축을 다 관리하면 bitemporal이 된다. valid time만 관리하는 게 훨씬 흔한 케이스다.

---

## valid_from / valid_to DDL 패턴

### 기본 구조

```sql
CREATE TABLE product_prices (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    product_id  BIGINT         NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    valid_from  DATE           NOT NULL,
    valid_to    DATE           NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_pp_product_period (product_id, valid_from, valid_to)
);
```

날짜 단위 유효 기간은 `DATE`를 쓴다. 시각 단위로 관리해야 하면 `DATETIME` 또는 `TIMESTAMP`를 쓴다.

### Open-ended Period 처리: NULL vs 9999-12-31

현재 유효한 레코드의 종료 시점을 어떻게 나타낼지 결정해야 한다. 두 방식이 있다.

**NULL 방식**

```sql
valid_from  DATE  NOT NULL,
valid_to    DATE  NULL,      -- NULL = 현재 유효
```

의미상 명확하다. "종료 시점이 없다"는 개념이 NULL로 표현된다. 단, `valid_to IS NULL OR valid_to >= :date` 같이 조건이 길어진다. 인덱스도 NULL 처리 방식이 DB마다 다르다.

```sql
-- NULL 방식 조회
SELECT *
FROM product_prices
WHERE product_id = 1
  AND valid_from <= '2024-06-01'
  AND (valid_to IS NULL OR valid_to > '2024-06-01');
```

**9999-12-31 방식 (Sentinel Value)**

```sql
valid_from  DATE  NOT NULL,
valid_to    DATE  NOT NULL DEFAULT '9999-12-31',
```

조건이 단순해진다. `valid_to > :date` 하나로 끝난다. `BETWEEN`이나 범위 인덱스도 자연스럽게 동작한다.

```sql
-- 9999-12-31 방식 조회
SELECT *
FROM product_prices
WHERE product_id = 1
  AND valid_from <= '2024-06-01'
  AND valid_to   >  '2024-06-01';
```

**실무 선택 기준**

9999-12-31 방식이 쿼리가 단순하고 인덱스 처리도 일관적이다. 단, 애플리케이션 레이어에서 이 값을 "무기한"으로 해석하는 코드가 곳곳에 생긴다. 그 코드가 관리 포인트가 된다.

NULL 방식은 의미가 명확하다. DB 수준에서는 값이 없다는 표현이 자연스럽다. 하지만 OR 조건과 인덱스 처리가 번거롭다.

한 프로젝트 안에서 두 방식을 섞으면 안 된다. 어느 쪽이든 하나를 정하고 일관되게 가야 한다.

---

## 특정 시점 조회 (As-of 쿼리)

특정 시각에 유효했던 레코드를 꺼내는 패턴이다.

```sql
-- "2024년 3월 1일 기준으로 상품 1번의 가격은?"
SELECT price
FROM product_prices
WHERE product_id = 1
  AND valid_from <= '2024-03-01'
  AND valid_to   >  '2024-03-01'
ORDER BY valid_from DESC
LIMIT 1;
```

`valid_from <= :as_of AND valid_to > :as_of`가 표준 패턴이다. 종료 조건을 `>=`로 쓰면 경계값 처리에서 문제가 생긴다. 예를 들어 `valid_to = '2024-03-01'`인 레코드는 2024-03-01부터는 유효하지 않은 건데 `>=`를 쓰면 포함된다.

반개방 구간 `[valid_from, valid_to)`으로 설계하는 게 일관적이다. `valid_from`은 포함, `valid_to`는 미포함.

### 현재 유효한 레코드 조회

9999-12-31 방식이라면 `CURDATE()`로 간단히 처리된다.

```sql
SELECT *
FROM employee_salaries
WHERE employee_id = 100
  AND valid_from <= CURDATE()
  AND valid_to   >  CURDATE();
```

현재 시점 레코드가 항상 하나여야 한다면 UNIQUE 제약이 필요하다. 단순 인덱스만으론 같은 기간이 겹치는 레코드를 막지 못한다. PostgreSQL의 EXCLUDE 제약 또는 애플리케이션 레이어에서 INSERT 전 검증이 필요하다.

---

## SQL:2011 PERIOD FOR APPLICATION_TIME

SQL:2011 표준에서 valid time을 공식 지원하는 구문이 추가됐다. APPLICATION_TIME이 valid time에 해당한다.

### MariaDB 지원

MariaDB 는 10.4부터 애플리케이션 시간 기간을 지원한다. MySQL 은 지원하지 않는다.

이름은 짚고 넘어갈 게 있다. MariaDB 문법은 `PERIOD FOR <기간이름>(시작컬럼, 끝컬럼)` 형태이고 기간 이름 자리는 그냥 식별자다. `APPLICATION_TIME` 은 예약어가 아니라 관례로 쓰는 이름일 뿐이라 다른 이름을 붙여도 똑같이 동작한다. 전용 키워드로 처리되는 건 `SYSTEM_TIME` 쪽뿐이다.

```sql
-- MariaDB 10.4+
CREATE TABLE product_prices (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    product_id  BIGINT         NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    valid_from  DATE           NOT NULL,
    valid_to    DATE           NOT NULL,
    PERIOD FOR APPLICATION_TIME(valid_from, valid_to),
    PRIMARY KEY (id, valid_from, valid_to)
);
```

PERIOD FOR APPLICATION_TIME을 선언하면 SQL:2011 temporal 구문을 쓸 수 있다.

```sql
-- AS OF 구문
SELECT * FROM product_prices
FOR APPLICATION_TIME AS OF '2024-03-01'
WHERE product_id = 1;

-- 기간 범위 조회
SELECT * FROM product_prices
FOR APPLICATION_TIME FROM '2024-01-01' TO '2024-06-30'
WHERE product_id = 1;

-- BETWEEN과 동일
SELECT * FROM product_prices
FOR APPLICATION_TIME BETWEEN '2024-01-01' AND '2024-06-30'
WHERE product_id = 1;
```

`FOR APPLICATION_TIME AS OF`는 `valid_from <= :date AND valid_to > :date`를 자동으로 처리해준다.

### PostgreSQL

PostgreSQL 18부터 application time 제약이 네이티브로 들어왔다 — temporal PK/UNIQUE 의 `WITHOUT OVERLAPS` 와 `PERIOD` 절을 쓰는 temporal FK 다. 동작 기반이 range 타입과 GiST 라, 아래에서 우회책으로 소개하는 그 조합이 그대로 표준 문법으로 승격된 셈이다. 다만 제약을 강제하는 데까지고 `FOR APPLICATION_TIME AS OF` 같은 **질의 문법은 아직 없다**. 17 이하에서는 `tsrange`/`daterange` + GiST 로 직접 구현해야 한다.

```sql
-- PostgreSQL: daterange 타입 활용
CREATE TABLE product_prices (
    id          BIGSERIAL      PRIMARY KEY,
    product_id  BIGINT         NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    valid_period DATERANGE     NOT NULL
);

CREATE INDEX idx_pp_period ON product_prices USING GIST (product_id, valid_period);

-- 특정 시점 조회
SELECT *
FROM product_prices
WHERE product_id = 1
  AND valid_period @> '2024-03-01'::DATE;

-- @> 는 "포함" 연산자
```

---

## 시간 범위 술어와 인덱스

### 범위 술어

valid time을 다룰 때 자주 쓰는 조건들이다.

**OVERLAPS (겹침)**

```sql
-- SQL:2011 표준
-- (A.valid_from, A.valid_to) OVERLAPS (B.valid_from, B.valid_to)

-- MySQL/MariaDB에서 동등한 표현
WHERE A.valid_from < B.valid_to
  AND A.valid_to   > B.valid_from
```

겹침 조건은 반대로 생각하면 쉽다. 겹치지 않는 조건은 `A.valid_to <= B.valid_from OR A.valid_from >= B.valid_to`다. NOT을 씌우면 겹침 조건이 된다.

**CONTAINS (포함)**

```sql
-- A 기간이 B 기간을 완전히 포함하는가
WHERE A.valid_from <= B.valid_from
  AND A.valid_to   >= B.valid_to
```

**PRECEDES / SUCCEEDS (선후)**

```sql
-- A가 B보다 완전히 앞서는가 (붙거나 겹치지 않음)
WHERE A.valid_to <= B.valid_from  -- PRECEDES

-- A가 B보다 완전히 뒤에 있는가
WHERE A.valid_from >= B.valid_to  -- SUCCEEDS
```

PostgreSQL의 range 타입은 이 연산자들을 내장하고 있다.

```sql
-- PostgreSQL range 연산자
&&   -- OVERLAPS
@>   -- CONTAINS
<@   -- CONTAINED BY
<<   -- STRICTLY LEFT OF (PRECEDES)
>>   -- STRICTLY RIGHT OF (SUCCEEDS)
-|-  -- ADJACENT
```

### 인덱스 전략

`(product_id, valid_from, valid_to)` 복합 인덱스를 기본으로 쓴다.

```sql
INDEX idx_pp_product_period (product_id, valid_from, valid_to)
```

`WHERE product_id = ? AND valid_from <= ? AND valid_to > ?` 쿼리에서 `product_id`로 먼저 필터한 뒤 `valid_from`의 범위 스캔이 동작한다. `valid_to` 조건은 인덱스 스캔 후 필터로 처리된다.

`valid_from`만으로 필터가 충분히 선택적이면 이 인덱스가 잘 동작한다. 특정 시점에 유효한 레코드가 전체 데이터의 상당 비율이라면(예: 대부분이 현재 유효) 인덱스 선택도가 낮아진다.

현재 유효한 레코드 조회가 압도적으로 많다면 partial index를 고려한다.

```sql
-- PostgreSQL: 현재 유효한 레코드만 인덱싱
CREATE INDEX idx_pp_current
ON product_prices (product_id, valid_from)
WHERE valid_to = '9999-12-31';
```

MariaDB에서 PERIOD를 선언하면 내부적으로 temporal 전용 인덱스를 쓴다.

---

## Period Normalization

같은 대상에 대한 기간 레코드가 쌓이다 보면 인접하거나 겹치는 구간이 생긴다. 이를 하나로 합치는 작업이 period normalization(또는 period consolidation)이다.

### 발생 원인

```
[2024-01-01, 2024-03-31) price=19900
[2024-04-01, 2024-06-30) price=19900   -- 인접, 같은 값
[2024-07-01, 9999-12-31) price=19900   -- 인접, 같은 값
```

세 레코드를 `[2024-01-01, 9999-12-31) price=19900` 하나로 합칠 수 있다.

겹침은 더 문제다.

```
[2024-01-01, 2024-06-30) price=19900
[2024-04-01, 2024-12-31) price=19900   -- 4~6월이 겹침
```

데이터 정합성이 깨진 상태다. INSERT 시 겹침을 막는 제약이 없으면 이런 상황이 생긴다.

### 인접 기간 병합 쿼리

같은 값을 가진 인접 기간을 합치는 건 gaps-and-islands 문제다.

```sql
-- 같은 product_id, price를 가진 인접/겹치는 기간을 병합
WITH ordered AS (
    SELECT
        product_id,
        price,
        valid_from,
        valid_to,
        LAG(valid_to) OVER (PARTITION BY product_id, price ORDER BY valid_from) AS prev_to
    FROM product_prices
    WHERE product_id = 1
),
grouped AS (
    SELECT
        product_id,
        price,
        valid_from,
        valid_to,
        SUM(CASE WHEN prev_to IS NULL OR prev_to < valid_from THEN 1 ELSE 0 END)
            OVER (PARTITION BY product_id, price ORDER BY valid_from) AS grp
    FROM ordered
)
SELECT
    product_id,
    price,
    MIN(valid_from) AS valid_from,
    MAX(valid_to)   AS valid_to
FROM grouped
GROUP BY product_id, price, grp
ORDER BY valid_from;
```

`LAG(valid_to)`로 이전 레코드의 종료 시점을 가져와서, 현재 시작이 이전 종료보다 뒤에 있으면 새 그룹으로 분류하는 방식이다.

실제 병합을 적용할 때는 원본을 삭제하고 병합 결과를 INSERT하는 방식으로 처리한다. 트랜잭션 안에서 한다.

```sql
START TRANSACTION;

-- 임시 테이블에 병합 결과 저장
CREATE TEMPORARY TABLE merged_prices AS
SELECT product_id, price, MIN(valid_from) AS valid_from, MAX(valid_to) AS valid_to
FROM ( ... -- 위의 gaps-and-islands 쿼리 ... ) t
GROUP BY product_id, price, grp;

-- 기존 레코드 삭제
DELETE FROM product_prices WHERE product_id = 1;

-- 병합 결과 INSERT
INSERT INTO product_prices (product_id, price, valid_from, valid_to)
SELECT product_id, price, valid_from, valid_to FROM merged_prices;

COMMIT;
```

---

## 실무 사용 케이스

### 가격 이력

이커머스에서 가장 흔한 valid time 케이스다. 특정 날짜의 가격을 알아야 반품/환불 처리에서 당시 가격을 참조할 수 있다.

```sql
CREATE TABLE product_prices (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    product_id  BIGINT         NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    valid_from  DATE           NOT NULL,
    valid_to    DATE           NOT NULL DEFAULT '9999-12-31',
    PRIMARY KEY (id),
    INDEX idx_pp_lookup (product_id, valid_from, valid_to)
);

-- 주문 시점의 가격 조회 (order_date를 기준으로)
SELECT pp.price
FROM orders o
JOIN product_prices pp
  ON pp.product_id = o.product_id
 AND pp.valid_from <= DATE(o.created_at)
 AND pp.valid_to   >  DATE(o.created_at)
WHERE o.id = 12345;
```

주문 테이블에 `price_at_order`를 스냅샷으로 저장하는 방식도 많이 쓴다. 이 경우 가격 이력 테이블 없이도 당시 가격을 알 수 있지만, "그 상품의 가격이 언제 얼마였는지"를 조회하려면 결국 이력 테이블이 필요하다.

### 직원 재직 기간 / 직급 이력

```sql
CREATE TABLE employee_positions (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    employee_id   BIGINT       NOT NULL,
    department_id BIGINT       NOT NULL,
    position      VARCHAR(50)  NOT NULL,
    valid_from    DATE         NOT NULL,
    valid_to      DATE         NOT NULL DEFAULT '9999-12-31',
    PRIMARY KEY (id),
    INDEX idx_ep_employee_period (employee_id, valid_from, valid_to)
);

-- 특정 날짜의 전체 팀 구성
SELECT e.name, ep.position
FROM employee_positions ep
JOIN employees e ON e.id = ep.employee_id
WHERE ep.department_id = 10
  AND ep.valid_from <= '2024-06-30'
  AND ep.valid_to   >  '2024-06-30';

-- 직원의 전체 직급 변경 이력
SELECT position, valid_from, valid_to
FROM employee_positions
WHERE employee_id = 100
ORDER BY valid_from;
```

퇴직 처리는 `valid_to`를 퇴직일로 업데이트한다. 9999-12-31이 현재 재직 중을 의미한다.

### 계약 유효 기간

계약은 명시적인 시작일과 종료일을 갖는다. valid time이 가장 자연스럽게 맞는 케이스다.

```sql
CREATE TABLE contracts (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    customer_id  BIGINT       NOT NULL,
    plan_id      BIGINT       NOT NULL,
    valid_from   DATE         NOT NULL,
    valid_to     DATE         NOT NULL,   -- 계약은 종료일이 명시적
    status       VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE',
    PRIMARY KEY (id),
    INDEX idx_c_customer_period (customer_id, valid_from, valid_to)
);

-- 오늘 기준으로 만료 예정 계약 (30일 이내)
SELECT *
FROM contracts
WHERE valid_to BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
  AND status = 'ACTIVE';

-- 특정 날짜에 유효한 계약
SELECT *
FROM contracts
WHERE customer_id = 500
  AND valid_from <= '2024-09-01'
  AND valid_to   >  '2024-09-01';
```

계약은 open-ended가 아니라서 NULL이나 9999-12-31 문제가 없다. 자동 갱신 계약이라면 갱신 시마다 새 레코드를 추가하거나 `valid_to`를 연장하는 방식 중 하나를 정해야 한다.

### 보험료 / 요금 테이블

보험료는 가입자 특성(나이, 위험군 등)과 시기에 따라 다르고, 소급 적용이 발생하는 경우가 있다.

```sql
CREATE TABLE insurance_rates (
    id           BIGINT         NOT NULL AUTO_INCREMENT,
    plan_id      BIGINT         NOT NULL,
    age_group    VARCHAR(20)    NOT NULL,   -- '20-29', '30-39' 등
    monthly_rate DECIMAL(10,2)  NOT NULL,
    valid_from   DATE           NOT NULL,
    valid_to     DATE           NOT NULL DEFAULT '9999-12-31',
    PRIMARY KEY (id),
    INDEX idx_ir_lookup (plan_id, age_group, valid_from, valid_to)
);

-- 가입 시점의 요금 조회
SELECT rate.monthly_rate
FROM insurance_rates rate
WHERE rate.plan_id    = 3
  AND rate.age_group  = '30-39'
  AND rate.valid_from <= '2024-02-15'
  AND rate.valid_to   >  '2024-02-15';
```

소급 변경이 일어나면 valid time만으로는 부족하다. "언제 그 정보가 입력됐는지"도 기록해야 할 때 transaction time을 추가해서 bitemporal 모델이 된다.

---

## 애플리케이션 레이어에서 valid time 관리

### 신규 기간 추가 시 기존 기간 종료

새 가격을 등록할 때 이전 레코드의 `valid_to`를 자동으로 닫는 패턴이다.

```java
@Transactional
public void updatePrice(Long productId, BigDecimal newPrice, LocalDate effectiveFrom) {
    // 현재 유효한 레코드 조회
    ProductPrice current = productPriceRepository
        .findCurrentPrice(productId, effectiveFrom)
        .orElse(null);

    if (current != null && current.getValidFrom().isBefore(effectiveFrom)) {
        // 기존 레코드 종료: valid_to를 새 시작일로 설정
        current.setValidTo(effectiveFrom);
        productPriceRepository.save(current);
    }

    // 새 레코드 추가
    ProductPrice newRecord = new ProductPrice();
    newRecord.setProductId(productId);
    newRecord.setPrice(newPrice);
    newRecord.setValidFrom(effectiveFrom);
    newRecord.setValidTo(LocalDate.of(9999, 12, 31));
    productPriceRepository.save(newRecord);
}
```

`effectiveFrom`이 현재 레코드의 `valid_from`과 같으면 기존 레코드를 업데이트하는 방식과 새 레코드를 추가하는 방식 중 어느 것을 택할지 정책을 정해야 한다.

### 미래 기간 예약

가격을 미리 등록해두는 케이스다.

```java
// 현재 날짜가 2024-06-01일 때
// 2024-09-01부터 적용될 가격을 미리 등록
productPriceService.updatePrice(productId, newPrice, LocalDate.of(2024, 9, 1));
```

이 경우 `[현재, 2024-09-01)` 구간의 기존 레코드는 그대로 두고, `[2024-09-01, 9999-12-31)` 레코드를 추가한다. 조회 쿼리에서 `valid_from <= CURDATE()`를 넣으면 미래 예약 레코드는 자동으로 제외된다.

미래 기간까지 포함해서 "이 상품의 앞으로 가격 변동 계획"을 보여주는 관리 화면이라면 `valid_from`으로 정렬해서 전체를 보여주면 된다.

### 겹침 방지 검증

애플리케이션에서 INSERT 전에 겹치는 기간이 있는지 확인한다.

```java
public void validateNoOverlap(Long productId, LocalDate from, LocalDate to) {
    boolean hasOverlap = productPriceRepository.existsOverlapping(
        productId, from, to
    );
    if (hasOverlap) {
        throw new IllegalStateException("기간이 겹치는 가격 레코드가 있습니다.");
    }
}
```

```sql
-- Repository 쿼리
SELECT COUNT(*) > 0
FROM product_prices
WHERE product_id = :productId
  AND valid_from < :to
  AND valid_to   > :from;
```

동시성이 있는 환경에서는 이 검증이 레이스 컨디션에 취약하다. PostgreSQL에서는 EXCLUDE 제약으로 DB 레벨에서 보장한다.

```sql
-- PostgreSQL
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE product_prices (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT    NOT NULL,
    price       DECIMAL(10,2),
    valid_period DATERANGE NOT NULL,
    EXCLUDE USING GIST (
        product_id   WITH =,
        valid_period WITH &&
    )
);
```

MariaDB에서는 PERIOD FOR APPLICATION_TIME을 쓰면 `WITHOUT OVERLAPS` 제약을 지원한다.

```sql
-- MariaDB 10.5+
CREATE TABLE product_prices (
    id          BIGINT        NOT NULL AUTO_INCREMENT,
    product_id  BIGINT        NOT NULL,
    price       DECIMAL(10,2) NOT NULL,
    valid_from  DATE          NOT NULL,
    valid_to    DATE          NOT NULL,
    PERIOD FOR APPLICATION_TIME(valid_from, valid_to),
    PRIMARY KEY (id, valid_from, valid_to),
    UNIQUE KEY uq_pp_no_overlap (product_id, APPLICATION_TIME WITHOUT OVERLAPS)
);
```

---

## Soft Delete와 Valid Time을 함께 쓸 때

soft delete(`deleted_at`)와 valid time을 같이 쓰면 "현재 유효하고 삭제되지 않은 레코드"를 찾는 조건이 복잡해진다.

```sql
-- valid time + soft delete
CREATE TABLE employee_positions (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    employee_id   BIGINT      NOT NULL,
    position      VARCHAR(50) NOT NULL,
    valid_from    DATE        NOT NULL,
    valid_to      DATE        NOT NULL DEFAULT '9999-12-31',
    deleted_at    DATETIME    NULL,
    PRIMARY KEY (id)
);

-- 현재 유효하고 삭제되지 않은 레코드
SELECT *
FROM employee_positions
WHERE employee_id = 100
  AND valid_from <= CURDATE()
  AND valid_to   >  CURDATE()
  AND deleted_at IS NULL;
```

### 겹치는 개념 주의

valid time의 `valid_to`를 현재 시점으로 설정하는 방식은 soft delete와 혼동을 일으킨다.

```sql
-- 잘못된 패턴: valid_to 업데이트를 삭제처럼 쓰면
UPDATE employee_positions SET valid_to = CURDATE() WHERE id = 99;
-- 이게 "이 기간이 오늘부로 끝났다"는 건지 "삭제됐다"는 건지 모호하다
```

비즈니스 종료(계약 만료, 직급 변경으로 인한 이전 기록 닫기)는 `valid_to` 업데이트로, 데이터 삭제(잘못 입력)는 `deleted_at` 설정으로 구분해야 한다.

### 이력 조회에서 soft delete 처리

삭제된 레코드를 이력 조회에서 포함할지 말지 결정해야 한다.

감사 목적이라면 삭제된 레코드도 보여야 한다. 비즈니스 조회라면 `deleted_at IS NULL`로 제외한다.

```sql
-- 감사용: 삭제 포함 전체 이력
SELECT *, CASE WHEN deleted_at IS NOT NULL THEN 'DELETED' ELSE 'ACTIVE' END AS record_status
FROM employee_positions
WHERE employee_id = 100
ORDER BY valid_from, deleted_at NULLS LAST;

-- 비즈니스 조회: 삭제 제외
SELECT *
FROM employee_positions
WHERE employee_id = 100
  AND deleted_at IS NULL
ORDER BY valid_from;
```

### 인덱스 설계

valid time + soft delete 조합에서 자주 쓰는 인덱스다.

```sql
-- MySQL: 현재 유효하고 삭제되지 않은 레코드 조회용
INDEX idx_ep_employee_active (employee_id, valid_from, valid_to, deleted_at)

-- PostgreSQL: partial index로 현재 유효한 삭제되지 않은 레코드만
CREATE INDEX idx_ep_current_active
ON employee_positions (employee_id, valid_from)
WHERE valid_to = '9999-12-31' AND deleted_at IS NULL;
```

partial index는 조회 패턴이 명확할 때 쓴다. 조회 조건이 다양하면 일반 복합 인덱스가 낫다.
