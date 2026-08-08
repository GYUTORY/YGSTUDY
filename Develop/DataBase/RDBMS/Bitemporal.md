---
title: Bitemporal
tags: [database, security, rdbms]
updated: 2026-07-31
---

# Bitemporal

## 두 시간 축이 동시에 필요해지는 지점

Valid Time만 관리하면 "이 데이터가 현실에서 언제 유효했는가"는 알 수 있다. Transaction Time만 관리하면 "DB에 언제 기록됐는가"는 알 수 있다. 두 질문 중 하나만 답하면 되는 도메인에서는 각 축 하나로 충분하다.

문제는 소급 수정이 발생했을 때다.

직원 A의 급여 인상이 5월에 결재됐지만 효력은 1월로 소급 적용됐다. DB에는 5월에 입력된다. 나중에 "5월 수정 전에 시스템이 알고 있던 1월 급여"와 "현재 시스템이 알고 있는 1월 급여"를 구분해서 조회해야 하는 요건이 생긴다.

- "현재 알고 있는 1월 급여"는 Valid Time AS OF로 답할 수 있다.
- "수정 전에 알고 있던 1월 급여"는 두 축을 동시에 써야 답할 수 있다.

이게 bitemporal이 필요한 지점이다. 두 시각이 따로 움직이고, 그 조합으로 쿼리해야 하는 상황.

---

## 도입 판단 기준

Bitemporal 모델을 잘못 도입하면 구현 복잡도만 올라가고 쓰이지 않는 이력 레코드만 쌓인다.

**실제로 필요한 조건:**

소급 수정이 도메인 특성상 반복적으로 발생해야 한다. 급여 소급 인상, 보험료 정정, 세금 재산정, 공공기관 재직 기록 수정이 대표적이다. 잘못 입력한 데이터를 수정하는 일이 가끔 발생하는 수준이라면 bitemporal이 아니라 별도 감사 로그로 충분하다.

소급 수정 후 "수정 전 시스템이 보고했던 값"을 재현해야 하는 요건이 있어야 한다. 이 재현이 필요 없다면 Valid Time 하나로 소급 적용을 처리할 수 있다.

**대안이 되는 경우:**

소급 적용은 있지만 수정 전/후 비교가 없다면, Valid Time만 관리하면서 valid_from을 과거로 설정해 INSERT하는 것으로 충분하다.

데이터 변경 이력 추적이 목적이고 소급 적용이 없다면, Transaction Time 단독이나 감사 로그 테이블로 충분하다.

소급 수정이 드물고 "수정 이전 값이 뭐였는지"만 파악하면 된다면, 감사 로그에 수정 전/후 값, 수정 시각, 수정자를 남기는 방식이 낫다. 두 시간 축을 독립적으로 조회하지는 못하지만 구현이 훨씬 단순하다.

---

## 테이블 구조

### 수동 구현

두 시간 축을 모두 담는 기본 구조다.

```sql
CREATE TABLE employee_salaries (
    id            BIGINT         NOT NULL AUTO_INCREMENT,
    employee_id   BIGINT         NOT NULL,
    salary        DECIMAL(10,2)  NOT NULL,

    -- Valid Time: 현실에서 이 급여가 유효한 기간 (애플리케이션이 관리)
    valid_from    DATE           NOT NULL,
    valid_to      DATE           NOT NULL DEFAULT '9999-12-31',

    -- Transaction Time: DB에 이 레코드가 기록된 기간 (애플리케이션이 관리)
    recorded_from DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    recorded_to   DATETIME(6)    NOT NULL DEFAULT '9999-12-31 23:59:59.999999',

    PRIMARY KEY (id),
    INDEX idx_es_valid    (employee_id, valid_from, valid_to),
    INDEX idx_es_recorded (employee_id, recorded_from, recorded_to)
);
```

Valid Time은 날짜(`DATE`) 단위, Transaction Time은 시각(`DATETIME(6)`) 단위로 쓰는 경우가 많다. Valid Time은 "1월 1일부터"처럼 날짜 개념이고, Transaction Time은 DB가 기록한 정확한 시각이라서다.

수동 구현의 위험은 `recorded_from`을 과거 시각으로 직접 INSERT할 수 있다는 점이다. 애플리케이션에서 실수로 잘못된 시각을 넣으면 Transaction Time의 신뢰성이 깨진다. 수정 메서드를 엄격히 통제하거나, 트리거로 `recorded_from`을 강제 덮어쓰는 방식을 써야 한다.

### MariaDB: SYSTEM_VERSIONED + APPLICATION_TIME 조합

MariaDB 10.4+에서 Transaction Time을 DB가 자동 관리하게 하면서 Valid Time은 애플리케이션이 관리하는 방식이 가능하다.

```sql
CREATE TABLE employee_salaries (
    id            BIGINT         NOT NULL AUTO_INCREMENT,
    employee_id   BIGINT         NOT NULL,
    salary        DECIMAL(10,2)  NOT NULL,

    -- Valid Time: 애플리케이션이 관리
    valid_from    DATE           NOT NULL,
    valid_to      DATE           NOT NULL DEFAULT '9999-12-31',

    -- Transaction Time: DB가 자동 관리
    row_start     DATETIME(6)    GENERATED ALWAYS AS ROW START,
    row_end       DATETIME(6)    GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME(row_start, row_end),
    PERIOD FOR APPLICATION_TIME(valid_from, valid_to),

    PRIMARY KEY (id, valid_from, valid_to)
) WITH SYSTEM VERSIONING;
```

`GENERATED ALWAYS AS ROW START/END`는 직접 수정할 수 없다. 수동 구현에서 `recorded_from`을 과거로 넣는 실수가 DB 레벨에서 차단된다. Transaction Time의 불변성이 DB가 보장하는 구조다.

MariaDB의 `FOR SYSTEM_TIME` 절과 `FOR APPLICATION_TIME` 절을 조합하면 SQL:2011 표준 문법으로 bitemporal 조회를 할 수 있다.

```sql
-- MariaDB: 특정 valid time과 transaction time을 동시에 지정
SELECT *
FROM employee_salaries
FOR SYSTEM_TIME AS OF '2024-03-01 00:00:00'
FOR APPLICATION_TIME AS OF '2024-02-01'
WHERE employee_id = 100;
```

MySQL은 이 기능을 지원하지 않는다. MySQL에서 bitemporal을 구현하려면 수동 방식으로 가야 한다.

---

## 소급 수정 시나리오

Bitemporal에서 데이터를 어떻게 관리하는지, 구체적인 흐름으로 보자.

**상황:** 직원 100번의 급여가 2024년 1월 1일부터 5,000만 원으로 등록됐다. 5월 15일에 사실 4월 1일부터 5,500만 원으로 올랐어야 했다는 소급 수정 요청이 들어왔다.

**1단계: 초기 데이터 입력 (1월 1일)**

```sql
INSERT INTO employee_salaries (employee_id, salary, valid_from, valid_to)
VALUES (100, 50000000, '2024-01-01', '9999-12-31');
-- recorded_from = 2024-01-01 09:00:00.000000 (자동)
-- recorded_to   = 9999-12-31 23:59:59.999999 (기본값)
```

이 시점 테이블 상태:

```
id=1, salary=5000만, valid=[2024-01-01, 9999-12-31)
      recorded=[2024-01-01 09:00:00, 9999-12-31 23:59:59)  ← 현재 유효
```

**2단계: 소급 수정 (5월 15일)**

기존 레코드를 UPDATE로 고치지 않는다. 기존 레코드의 `recorded_to`를 현재 시각으로 닫고, 수정된 내용을 새 레코드로 추가한다.

```sql
-- 기존 레코드를 transaction time 기준으로 종료
UPDATE employee_salaries
SET recorded_to = CURRENT_TIMESTAMP(6)
WHERE employee_id = 100
  AND recorded_to  = '9999-12-31 23:59:59.999999';

-- 1월~3월: 기존 급여 유지, 새 recorded 기간으로 추가
INSERT INTO employee_salaries (employee_id, salary, valid_from, valid_to)
VALUES (100, 50000000, '2024-01-01', '2024-03-31');

-- 4월~현재: 인상된 급여
INSERT INTO employee_salaries (employee_id, salary, valid_from, valid_to)
VALUES (100, 55000000, '2024-04-01', '9999-12-31');
```

수정 후 테이블 상태:

```
id=1, salary=5000만, valid=[2024-01-01, 9999-12-31)
      recorded=[2024-01-01 09:00:00, 2024-05-15 14:30:00)  ← 종료됨

id=2, salary=5000만, valid=[2024-01-01, 2024-03-31)
      recorded=[2024-05-15 14:30:00, 9999-12-31 23:59:59)  ← 현재 유효

id=3, salary=5500만, valid=[2024-04-01, 9999-12-31)
      recorded=[2024-05-15 14:30:00, 9999-12-31 23:59:59)  ← 현재 유효
```

id=1은 삭제되지 않고 남아 있다. "5월 15일 수정 전에 시스템이 알고 있던 데이터"를 재현하는 데 쓰인다.

---

## 4가지 쿼리 패턴

### 1. 현재 기준 / 현재 유효

지금 시스템이 알고 있는, 지금 유효한 값을 조회한다. 가장 흔한 패턴이다.

```sql
SELECT salary
FROM employee_salaries
WHERE employee_id  = 100
  AND valid_from   <= CURDATE()
  AND valid_to     >  CURDATE()
  AND recorded_from <= NOW()
  AND recorded_to   >  NOW();
```

소급 수정 이후 오늘이 5월 15일 이후라면 id=3(salary=5500만)이 반환된다.

### 2. Valid Time AS OF

"현재 시스템이 알고 있는 데이터 중, 특정 날짜에 유효했던 값은 무엇인가."

수정 적용 후 과거 특정 시점의 값을 조회하는 패턴이다. 소급 수정이 이미 반영된 결과가 나온다.

```sql
-- 현재 시스템 기준으로 2024년 2월 1일에 유효했던 급여
SELECT salary
FROM employee_salaries
WHERE employee_id  = 100
  AND valid_from   <= '2024-02-01'
  AND valid_to     >  '2024-02-01'
  AND recorded_from <= NOW()
  AND recorded_to   >  NOW();
```

소급 수정 이후에 실행하면 id=2(salary=5000만, valid=[2024-01-01, 2024-03-31))가 결과로 나온다. 수정 후 시스템 기준으로 "2월에 5,000만 원이었다"는 걸 알고 있다.

### 3. Transaction Time AS OF

"특정 시각에 DB에 존재했던 데이터 기준으로 조회하면 무엇이 나오는가."

과거 특정 시점의 DB 스냅샷을 재현하는 패턴이다. "그 당시 보고서를 실행했다면 어떤 값이 나왔을까"를 검증할 때 쓴다.

```sql
-- 2024년 3월 1일 당시 DB 기준으로 현재 유효한 급여
SELECT salary
FROM employee_salaries
WHERE employee_id  = 100
  AND recorded_from <= '2024-03-01 00:00:00'
  AND recorded_to   >  '2024-03-01 00:00:00'
  AND valid_from    <= '2024-03-01'
  AND valid_to      >  '2024-03-01';
```

3월 1일에는 소급 수정이 없었으니, id=1(salary=5000만, valid=[2024-01-01, 9999-12-31))이 반환된다. 그 당시 DB에는 3월도 5,000만 원으로 기록돼 있었다.

### 4. 양축 AS OF (Bitemporal AS OF)

"특정 시각의 DB 상태에서, 특정 날짜에 유효했던 값은 무엇인가."

Valid Time이나 Transaction Time 어느 한 축으로만은 답할 수 없는 질문이다. 소급 수정이 반영된 지금 기준의 과거 값과, 수정 전 시스템이 알고 있던 값을 비교하는 감사·검증 시나리오에서 쓴다.

```sql
-- "5월 15일 수정 전 시스템이 알고 있던, 4월 1일 기준 급여는?"
SELECT salary
FROM employee_salaries
WHERE employee_id  = 100
  AND valid_from   <= '2024-04-01'
  AND valid_to     >  '2024-04-01'
  AND recorded_from <= '2024-05-14 23:59:59'
  AND recorded_to   >  '2024-05-14 23:59:59';
-- 결과: id=1, salary=5000만 (수정 전에는 4월도 5,000만으로 알고 있었음)
```

```sql
-- "현재 시스템이 알고 있는, 4월 1일 기준 급여는?"
SELECT salary
FROM employee_salaries
WHERE employee_id  = 100
  AND valid_from   <= '2024-04-01'
  AND valid_to     >  '2024-04-01'
  AND recorded_from <= NOW()
  AND recorded_to   >  NOW();
-- 결과: id=3, salary=5500만 (수정 후에는 4월이 5,500만으로 반영됨)
```

두 쿼리의 차이가 소급 수정으로 달라진 값이다.

---

## 인덱스 전략

두 시간 축을 독립적으로 조회하기 때문에 축별로 인덱스를 분리하는 게 기본이다.

```sql
-- Valid Time 기준 조회용 (패턴 1, 2)
INDEX idx_es_valid (employee_id, valid_from, valid_to)

-- Transaction Time 기준 조회용 (패턴 3)
INDEX idx_es_recorded (employee_id, recorded_from, recorded_to)
```

패턴 1·2는 `idx_es_valid`를 타고 `recorded` 조건은 추가 필터로 처리된다. 패턴 3은 `idx_es_recorded`를 타고 `valid` 조건은 추가 필터로 처리된다.

패턴 4(양축 AS OF)는 두 인덱스 중 선택도가 높은 쪽을 옵티마이저가 고른다. `employee_id`로 필터된 후 남은 레코드 수가 충분히 적으면 어느 쪽이든 잘 동작한다. EXPLAIN으로 확인하는 게 낫다.

패턴 1처럼 "현재 레코드만 조회"가 압도적으로 많다면 PostgreSQL에서 partial index를 활용한다.

```sql
-- PostgreSQL: recorded_to가 최대값인 행(현재 레코드)만 인덱싱
CREATE INDEX idx_es_current
ON employee_salaries (employee_id, valid_from, valid_to)
WHERE recorded_to = '9999-12-31 23:59:59.999999';
```

현재 유효한 레코드 비율이 낮을수록(이력이 많이 쌓일수록) partial index 효과가 커진다.

---

## 수정 트랜잭션 처리

소급 수정은 반드시 트랜잭션 안에서 처리한다. 기존 레코드 종료와 새 레코드 삽입 사이에 정합성이 깨지면 안 된다.

```java
@Transactional
public void applyRetroactiveCorrection(
        Long employeeId,
        BigDecimal newSalary,
        LocalDate effectiveFrom) {

    LocalDateTime now = LocalDateTime.now();

    // 1. 현재 recorded_to가 최대값인 레코드 전체 조회
    List<EmployeeSalary> current = repository.findCurrentRecorded(employeeId, now);

    // 2. 기존 레코드 recorded_to 종료
    current.forEach(r -> r.setRecordedTo(now));
    repository.saveAll(current);

    // 3. effectiveFrom 이전 기간: 기존 급여 그대로, 새 recorded 기간으로 복사
    current.stream()
        .filter(r -> r.getValidFrom().isBefore(effectiveFrom))
        .forEach(r -> {
            LocalDate splitTo = effectiveFrom.minusDays(1);
            LocalDate newValidTo = r.getValidTo().isBefore(splitTo) ? r.getValidTo() : splitTo;
            repository.save(
                r.copyWithPeriod(r.getValidFrom(), newValidTo, now)
            );
        });

    // 4. effectiveFrom 이후: 새 급여로 추가
    EmployeeSalary updated = EmployeeSalary.builder()
        .employeeId(employeeId)
        .salary(newSalary)
        .validFrom(effectiveFrom)
        .validTo(LocalDate.of(9999, 12, 31))
        .recordedFrom(now)
        .recordedTo(LocalDateTime.of(9999, 12, 31, 23, 59, 59, 999_999_000))
        .build();
    repository.save(updated);
}
```

`effectiveFrom`이 기존 레코드의 `valid_from`과 같은 경우, 기존 valid 기간 경계에 걸치는 경우, 여러 레코드에 걸쳐 수정되는 경우를 각각 처리해야 한다. 이 분기 처리가 bitemporal 수정 로직에서 가장 까다로운 부분이다.

ORM을 쓸 때 주의할 점이 있다. `save()`로 엔티티를 저장하면 JPA가 내부적으로 UPDATE를 칠 수 있다. bitemporal에서 기존 레코드 `recorded_to` 업데이트 외의 UPDATE는 이력이 꼬이는 원인이 된다. 수정 로직을 별도 서비스 레이어로 격리하고, 일반 save 경로에서 bitemporal 레코드를 건드리지 못하게 막아야 한다.

---

## 이력 데이터 관리

소급 수정이 반복되면 같은 엔티티에 대한 레코드가 계속 쌓인다. 보존 정책 없이 두면 이력 레코드가 현재 레코드보다 훨씬 많아진다.

`recorded_to`가 최대값이 아닌 레코드는 더 이상 "현재 유효한 버전"이 아니다. 오래된 이력 레코드는 별도 아카이브 테이블로 이동하거나, 규정상 보존 기간이 지난 것은 삭제 처리한다.

```sql
-- 2년 이상 지난 이력 레코드 아카이브로 이동
INSERT INTO employee_salaries_archive
SELECT * FROM employee_salaries
WHERE recorded_to < DATE_SUB(NOW(), INTERVAL 2 YEAR)
  AND recorded_to != '9999-12-31 23:59:59.999999';

DELETE FROM employee_salaries
WHERE recorded_to < DATE_SUB(NOW(), INTERVAL 2 YEAR)
  AND recorded_to != '9999-12-31 23:59:59.999999'
LIMIT 10000;
```

삭제는 LIMIT를 걸고 루프로 처리한다. 한 번에 대량 삭제하면 락이 오래 잡힌다.

---

## 구현 복잡도와 트레이드오프

**복잡해지는 부분:**

쓰기 로직이 늘어난다. UPDATE 하나로 끝나던 수정이 기존 레코드 종료 + 새 레코드 N개 삽입으로 바뀐다. 분기 케이스를 빠뜨리면 이력에 구멍이 생기거나 중복이 발생한다.

조회 쿼리에 조건이 4개 늘어난다. `recorded_to = '9999-12-31...'` 같은 "현재 레코드" 필터를 빠뜨리는 실수가 잦다. 빠뜨리면 종료된 이력 레코드까지 포함돼서 중복 결과가 나온다. 이 조건을 뷰나 레포지토리 메서드로 강제하는 편이 낫다.

ORM 연동이 까다롭다. 일반 `save()`와 bitemporal 수정 경로를 구분하지 않으면 이력이 꼬인다.

데이터 볼륨이 커진다. 자주 수정되는 엔티티는 이력 레코드가 현재 레코드보다 훨씬 많을 수 있다.

**도입이 합리적인 시점:**

"X 시점에 DB에 기록된 데이터 기준으로 Y 날짜의 유효값이 무엇이었는가"라는 질문을 실제로 서비스에서 처리해야 할 때다. 보험 감사, 금융 정산, 공공기관 급여 시스템이 해당된다.

그 외에서는 Valid Time 단독으로 시작하는 게 낫다. "수정 전 값 재현" 요건이 실제로 생겼을 때 bitemporal로 전환하는 게 현실적이다. 처음부터 bitemporal을 넣어두고 나중에 쓰는 구조는 복잡도만 미리 올려두는 꼴이다.
