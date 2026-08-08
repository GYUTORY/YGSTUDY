---
title: Transaction Time
tags: [database, security, rdbms]
updated: 2026-07-31
---

# Transaction Time

## Transaction Time이란

Transaction Time(System Time)은 데이터가 DB에 실제로 기록된 시점을 추적하는 시간 축이다. "이 데이터가 언제부터 언제까지 DB에 존재했는가"를 나타낸다.

Valid Time이 비즈니스 현실을 반영한다면, Transaction Time은 DB 자체의 상태 변화를 기록한다. 애플리케이션이 관리하는 게 아니라 DB가 자동으로 관리한다는 점이 핵심이다.

가장 중요한 특성은 소급 수정이 불가능하다는 것이다. 오늘 입력한 데이터의 `row_start`를 어제로 바꾸는 건 불가능하다. DB가 "이 레코드는 이 시각에 생성됐다"는 사실을 통제하기 때문이다. 이 불변성이 transaction time을 감사 로그로 신뢰할 수 있게 만드는 이유다.

---

## SQL:2011 SYSTEM_VERSIONED 테이블

SQL:2011 표준에서 transaction time을 공식 지원하는 방법이 추가됐다. SYSTEM_VERSIONED 테이블을 선언하면 DB가 자동으로 이력을 관리한다.

### MariaDB 구현

MariaDB 10.3부터 SYSTEM_VERSIONED 테이블을 지원한다. MySQL은 지원하지 않는다.

```sql
CREATE TABLE employee_salaries (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    employee_id BIGINT         NOT NULL,
    salary      DECIMAL(10,2)  NOT NULL,
    PRIMARY KEY (id)
) WITH SYSTEM VERSIONING;
```

`WITH SYSTEM VERSIONING`만 붙이면 MariaDB가 내부적으로 `ROW_START`와 `ROW_END` 컬럼을 관리한다. 직접 정의할 수도 있다.

```sql
CREATE TABLE employee_salaries (
    id          BIGINT          NOT NULL AUTO_INCREMENT,
    employee_id BIGINT          NOT NULL,
    salary      DECIMAL(10,2)   NOT NULL,
    row_start   DATETIME(6)     GENERATED ALWAYS AS ROW START,
    row_end     DATETIME(6)     GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME(row_start, row_end),
    PRIMARY KEY (id)
) WITH SYSTEM VERSIONING;
```

`DATETIME(6)`은 마이크로초 단위다. 같은 트랜잭션 안에서 여러 행이 변경될 때 동일한 타임스탬프를 갖게 된다.

### ROW_START / ROW_END 의미

`ROW_START`는 해당 버전이 DB에 기록된 시각이다. INSERT 또는 UPDATE가 발생한 시각이 여기 들어간다.

`ROW_END`는 해당 버전이 대체된 시각이다. 현재 유효한 레코드는 `ROW_END = '9999-12-31 23:59:59.999999'`다. UPDATE나 DELETE가 발생하면 이전 버전의 `ROW_END`가 그 시각으로 설정되고, 이력 테이블로 이동한다.

```
INSERT 시:
  현재 테이블: id=1, salary=5000, row_start=2024-01-01 10:00:00, row_end=9999-12-31 23:59:59

UPDATE 후 (salary=5500):
  이력 테이블: id=1, salary=5000, row_start=2024-01-01 10:00:00, row_end=2024-06-01 09:00:00
  현재 테이블: id=1, salary=5500, row_start=2024-06-01 09:00:00, row_end=9999-12-31 23:59:59

DELETE 후:
  이력 테이블: id=1, salary=5500, row_start=2024-06-01 09:00:00, row_end=2024-12-01 15:00:00
  현재 테이블: (행 없음)
```

직접 `row_start`나 `row_end` 컬럼에 값을 쓰려고 하면 오류가 발생한다. `GENERATED ALWAYS`로 선언된 컬럼이기 때문이다.

---

## FOR SYSTEM_TIME 쿼리 패턴

SYSTEM_VERSIONED 테이블에서 과거 상태를 조회하는 방법이다.

### AS OF — 특정 시점 조회

```sql
-- 2024년 3월 1일 정오에 DB에 존재했던 급여 데이터
SELECT *
FROM employee_salaries
FOR SYSTEM_TIME AS OF '2024-03-01 12:00:00'
WHERE employee_id = 100;
```

`AS OF`는 `row_start <= :ts AND row_end > :ts`를 자동으로 처리한다. 해당 시점에 현재 테이블과 이력 테이블에 걸쳐 유효했던 버전을 찾아준다.

"어제 오전 DB에 뭐가 있었지?"를 디버깅할 때 쓰는 패턴이다.

### ALL — 전체 이력

```sql
-- 직원 100번의 급여 변경 전체 이력
SELECT employee_id, salary, row_start, row_end
FROM employee_salaries
FOR SYSTEM_TIME ALL
WHERE employee_id = 100
ORDER BY row_start;
```

`FOR SYSTEM_TIME ALL`은 현재 데이터와 이력 데이터를 모두 합쳐서 반환한다. 변경 이력을 시간순으로 볼 때 쓴다.

### BETWEEN / FROM TO — 기간 범위

```sql
-- 2024년 1분기에 유효했던 버전들
SELECT *
FROM employee_salaries
FOR SYSTEM_TIME BETWEEN '2024-01-01' AND '2024-03-31'
WHERE employee_id = 100;

-- FROM ... TO (BETWEEN과 경계값 처리가 다름)
SELECT *
FROM employee_salaries
FOR SYSTEM_TIME FROM '2024-01-01' TO '2024-03-31'
WHERE employee_id = 100;
```

`BETWEEN`은 양 경계를 포함한다. `FROM ... TO`는 시작은 포함하고 종료는 제외한다. 실무에서 두 구문의 경계값 차이로 예상과 다른 결과가 나오는 경우가 있으니 주의해야 한다.

### PostgreSQL에서의 대안

PostgreSQL은 SQL:2011 SYSTEM_VERSIONED를 네이티브로 지원하지 않는다. 이력 관리는 수동으로 구현해야 한다.

---

## MySQL에서의 이력 테이블 + 트리거 구현

MySQL에서 transaction time을 직접 구현해야 한다면 이력 테이블과 트리거 조합이 표준 방식이다.

### 테이블 구조

```sql
-- 현재 데이터 테이블
CREATE TABLE employee_salaries (
    id          BIGINT         NOT NULL AUTO_INCREMENT,
    employee_id BIGINT         NOT NULL,
    salary      DECIMAL(10,2)  NOT NULL,
    row_start   DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    INDEX idx_es_employee (employee_id)
);

-- 이력 테이블: 현재 테이블 + row_end 추가
CREATE TABLE employee_salaries_history (
    id          BIGINT         NOT NULL,
    employee_id BIGINT         NOT NULL,
    salary      DECIMAL(10,2)  NOT NULL,
    row_start   DATETIME(6)    NOT NULL,
    row_end     DATETIME(6)    NOT NULL,
    PRIMARY KEY (id, row_start),
    INDEX idx_esh_employee_period (employee_id, row_start, row_end)
);
```

이력 테이블은 현재 테이블과 동일한 컬럼에 `row_end`를 추가한 구조다. `PRIMARY KEY (id, row_start)`로 같은 `id`의 여러 버전을 저장한다.

### 트리거 구현

```sql
-- UPDATE 트리거: 변경 전 버전을 이력 테이블로 이동
DELIMITER //
CREATE TRIGGER trg_es_before_update
BEFORE UPDATE ON employee_salaries
FOR EACH ROW
BEGIN
    INSERT INTO employee_salaries_history
        (id, employee_id, salary, row_start, row_end)
    VALUES
        (OLD.id, OLD.employee_id, OLD.salary, OLD.row_start, CURRENT_TIMESTAMP(6));

    SET NEW.row_start = CURRENT_TIMESTAMP(6);
END//

-- DELETE 트리거: 삭제 전 버전을 이력 테이블로 이동
CREATE TRIGGER trg_es_before_delete
BEFORE DELETE ON employee_salaries
FOR EACH ROW
BEGIN
    INSERT INTO employee_salaries_history
        (id, employee_id, salary, row_start, row_end)
    VALUES
        (OLD.id, OLD.employee_id, OLD.salary, OLD.row_start, CURRENT_TIMESTAMP(6));
END//
DELIMITER ;
```

UPDATE가 발생하면 OLD 버전을 이력 테이블에 `row_end = CURRENT_TIMESTAMP(6)`으로 기록하고, 현재 테이블의 `row_start`를 현재 시각으로 갱신한다.

### 이력 조회 쿼리

MariaDB의 `FOR SYSTEM_TIME`이 없으니 조건을 직접 써야 한다.

```sql
-- AS OF 동등 쿼리: 특정 시점에 유효했던 레코드
-- 현재 테이블 (row_end = 무한대)
SELECT id, employee_id, salary, row_start, NULL AS row_end
FROM employee_salaries
WHERE employee_id = 100
  AND row_start <= '2024-03-01 12:00:00'

UNION ALL

-- 이력 테이블
SELECT id, employee_id, salary, row_start, row_end
FROM employee_salaries_history
WHERE employee_id = 100
  AND row_start <= '2024-03-01 12:00:00'
  AND row_end   >  '2024-03-01 12:00:00';
```

```sql
-- ALL 동등 쿼리: 전체 이력
SELECT id, employee_id, salary, row_start, NULL AS row_end, 'CURRENT' AS version_status
FROM employee_salaries
WHERE employee_id = 100

UNION ALL

SELECT id, employee_id, salary, row_start, row_end, 'HISTORY' AS version_status
FROM employee_salaries_history
WHERE employee_id = 100

ORDER BY row_start;
```

이 UNION ALL 패턴은 쿼리가 길어지는 단점이 있다. 뷰로 감싸두면 조금 낫다.

```sql
CREATE VIEW v_employee_salaries_all AS
SELECT id, employee_id, salary, row_start,
       CAST('9999-12-31 23:59:59.999999' AS DATETIME(6)) AS row_end
FROM employee_salaries

UNION ALL

SELECT id, employee_id, salary, row_start, row_end
FROM employee_salaries_history;
```

---

## 소급 수정 불가 특성과 실무 함의

Transaction time의 핵심은 과거를 바꿀 수 없다는 것이다. `row_start`는 DB가 채워주고, 직접 수정할 수 없다.

이 특성이 실무에서 어떻게 드러나는지 보자.

### 잘못 입력한 데이터의 처리

직원 A의 급여를 5000으로 입력했는데 실제로는 5500이어야 했다. 이미 DB에 기록됐다.

```
2024-01-01 09:00:00: INSERT salary=5000
  → row_start=2024-01-01 09:00:00
```

수정을 하면 이력이 남는다.

```
2024-01-01 09:05:00: UPDATE salary=5500
  → 이력: row_start=2024-01-01 09:00:00, row_end=2024-01-01 09:05:00, salary=5000
  → 현재: row_start=2024-01-01 09:05:00, salary=5500
```

"5000으로 입력된 적이 있었다"는 사실이 transaction time 이력에 영구적으로 남는다. 이 점을 이용해서 "언제, 어떤 값이 DB에 있었는가"를 재구성할 수 있다.

### 감사 로그와의 차이

transaction time 이력은 감사 로그와 비슷해 보이지만 다르다.

감사 로그는 "누가 변경했는가", "어떤 이유로"를 기록하는 데 집중한다. 별도 audit_log 테이블에 user_id, action, reason 같은 컬럼을 추가한다.

transaction time은 "DB에 어떤 상태가 언제 존재했는가"만 추적한다. 변경자 정보나 이유는 없다.

두 가지 요구사항이 모두 있다면 transaction time 이력 + 별도 감사 로그를 같이 운영한다. 실무에서는 SYSTEM_VERSIONED 테이블로 버전 이력을 관리하고, 중요한 변경에는 애플리케이션 레벨에서 감사 로그를 별도 기록하는 패턴을 많이 쓴다.

### 소급 적용 요건이 생기면

"이 직원의 급여는 사실 3개월 전부터 올랐어야 했다"는 요건이 오면, transaction time만으로는 해결이 안 된다. DB에 3개월 전에 기록하는 건 불가능하다.

이 상황이 valid time이 필요한 이유다. valid time으로 `valid_from = 3개월 전`을 기록하고, transaction time으로 "지금 이 시각에 DB에 입력됐다"는 사실을 별도로 추적한다. 이게 bitemporal 모델의 출발점이다.

---

## 이력 데이터 보존·삭제 전략

SYSTEM_VERSIONED 테이블의 이력 데이터는 계속 쌓인다. 보존 정책이 없으면 이력 테이블이 운영 테이블보다 훨씬 커진다.

### MariaDB: 이력 보존 기간 설정

```sql
-- 1년치 이력만 보존
ALTER TABLE employee_salaries
    MODIFY HISTORY LIMIT INTERVAL 1 YEAR;

-- 최대 1000개 버전만 보존
ALTER TABLE employee_salaries
    MODIFY HISTORY LIMIT 1000 ROWS;
```

MariaDB는 이 설정으로 오래된 이력을 자동 삭제한다. 단, 자동 삭제 시점은 INSERT/UPDATE/DELETE 발생 시 트리거된다. 조회만 하는 테이블이라면 삭제가 실행되지 않는다.

### MySQL 트리거 방식: 수동 삭제

MySQL에서 직접 구현한 경우 배치 잡으로 오래된 이력을 정리해야 한다.

```sql
-- 1년 이상 지난 이력 삭제
DELETE FROM employee_salaries_history
WHERE row_end < DATE_SUB(NOW(), INTERVAL 1 YEAR)
LIMIT 10000;
```

`LIMIT`을 걸지 않으면 대량 삭제로 락이 길어진다. 배치 잡에서 루프로 나눠서 삭제하는 게 안전하다.

```sql
-- 반복 삭제 패턴 (애플리케이션에서 루프)
DELETE FROM employee_salaries_history
WHERE row_end < DATE_SUB(NOW(), INTERVAL 1 YEAR)
  AND employee_id BETWEEN :start_id AND :end_id
LIMIT 5000;
```

### 이력 테이블 파티셔닝

이력 데이터가 많다면 `row_end`로 파티셔닝해서 오래된 데이터를 파티션 단위로 드롭할 수 있다.

```sql
CREATE TABLE employee_salaries_history (
    id          BIGINT      NOT NULL,
    employee_id BIGINT      NOT NULL,
    salary      DECIMAL(10,2) NOT NULL,
    row_start   DATETIME(6) NOT NULL,
    row_end     DATETIME(6) NOT NULL
)
PARTITION BY RANGE (YEAR(row_end)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 2022년 이력 전체 삭제 (파티션 드롭은 빠름)
ALTER TABLE employee_salaries_history DROP PARTITION p2022;
```

파티션 드롭은 DELETE보다 훨씬 빠르다. 대신 파티션 키(`YEAR(row_end)`)가 조회 조건에 있어야 파티션 프루닝이 동작한다.

### 이력 아카이브

삭제 대신 콜드 스토리지로 이동하는 방식도 있다. 규정상 5년치 이력을 보관해야 하지만 자주 조회하지 않는 경우에 쓴다.

```sql
-- 오래된 이력을 아카이브 테이블로 이동
INSERT INTO employee_salaries_history_archive
SELECT * FROM employee_salaries_history
WHERE row_end < DATE_SUB(NOW(), INTERVAL 2 YEAR);

DELETE FROM employee_salaries_history
WHERE row_end < DATE_SUB(NOW(), INTERVAL 2 YEAR);
```

아카이브 테이블은 별도 DB나 오브젝트 스토리지에 두기도 한다. 드물게 조회하는 이력이라면 CSV로 내보내서 S3에 저장하고 Athena로 조회하는 방식도 실무에서 쓴다.

---

## Bitemporal 모델과의 연계

Transaction time과 valid time을 동시에 관리하는 게 bitemporal 모델이다.

```sql
-- Bitemporal 테이블: valid time + transaction time
CREATE TABLE employee_salaries_bitemporal (
    id            BIGINT         NOT NULL AUTO_INCREMENT,
    employee_id   BIGINT         NOT NULL,
    salary        DECIMAL(10,2)  NOT NULL,
    -- valid time (애플리케이션이 관리)
    valid_from    DATE           NOT NULL,
    valid_to      DATE           NOT NULL DEFAULT '9999-12-31',
    -- transaction time (DB가 관리)
    row_start     DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    INDEX idx_esb_employee (employee_id, valid_from, valid_to)
);

-- 이력 테이블
CREATE TABLE employee_salaries_bitemporal_history (
    id            BIGINT         NOT NULL,
    employee_id   BIGINT         NOT NULL,
    salary        DECIMAL(10,2)  NOT NULL,
    valid_from    DATE           NOT NULL,
    valid_to      DATE           NOT NULL,
    row_start     DATETIME(6)    NOT NULL,
    row_end       DATETIME(6)    NOT NULL,
    PRIMARY KEY (id, row_start)
);
```

### Bitemporal 쿼리 패턴

두 축을 동시에 쓰는 쿼리는 복잡하다.

```sql
-- "2024-03-01 기준으로 시스템이 알고 있던, 2024-02-01에 유효했던 급여"
-- transaction time AS OF 2024-03-01
-- valid time AS OF 2024-02-01
SELECT *
FROM (
    -- 2024-03-01 시점의 transaction time 기준 스냅샷
    SELECT *
    FROM employee_salaries_bitemporal
    WHERE row_start <= '2024-03-01 00:00:00'
    UNION ALL
    SELECT id, employee_id, salary, valid_from, valid_to, row_start, NULL AS row_end
    FROM employee_salaries_bitemporal_history
    WHERE row_start <= '2024-03-01 00:00:00'
      AND row_end   >  '2024-03-01 00:00:00'
) AS system_snapshot
WHERE employee_id = 100
  AND valid_from  <= '2024-02-01'
  AND valid_to    >  '2024-02-01';
```

이 쿼리가 답하는 질문은 "2024년 3월 1일 당시 우리가 알고 있던 데이터에 따르면, 직원 100번의 2024년 2월 1일 급여는 얼마였나"다.

소급 수정이 자주 일어나는 도메인에서 이 질문이 필요해진다. 보험료 정산, 공공기관 급여 소급 인상, 회계 정정 처리가 대표적인 사례다.

### 연계 지점 정리

transaction time만 관리하면 "DB에 언제 무엇이 기록됐는가"를 추적할 수 있다. 하지만 소급 수정이 발생했을 때 "언제 적용됐어야 하는가"는 추적하지 못한다.

valid time만 관리하면 "현실에서 언제 유효했는가"를 모델링할 수 있다. 하지만 "이 정보가 언제 입력됐는가"를 추적하지 못한다.

두 축이 모두 필요한 시점은 소급 수정 후 "그 당시 시스템이 알고 있던 값"과 "실제로 유효했던 값"을 구분해야 할 때다. 그 전까지는 valid time 하나만 관리하는 게 구현 복잡도를 낮춘다.
