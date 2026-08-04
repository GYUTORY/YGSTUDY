---
title: 아카이브 테이블
tags: [database, archive, retention-policy, batch, partitioning, index, union-all, deadlock, replication-lag, mysql, postgresql]
updated: 2026-08-04
---

# 아카이브 테이블

운영 테이블에서 오래된 데이터를 분리해서 별도 테이블에 보관하는 패턴이다. 목적은 하나다. 운영 테이블을 작게 유지해서 쿼리 성능을 일정하게 가져간다.

소프트 삭제와 혼동하는 경우가 있는데, 두 패턴은 해결하는 문제가 다르다. 소프트 삭제는 "행을 지우지 않고 삭제 표시만 남기는 것"이고, 아카이브 테이블은 "데이터를 물리적으로 다른 테이블로 옮기는 것"이다. 소프트 삭제와 아카이브를 함께 쓰는 경우도 많다. `deleted_at`이 일정 기간 지난 행을 아카이브 테이블로 이동하고, 운영 테이블에서는 물리 삭제하는 식이다. [소프트 삭제](Soft_Delete.md)에서 다룬 내용과 중복되는 부분은 생략한다.

---

## 소프트 삭제와의 차이

소프트 삭제는 운영 테이블에 데이터가 계속 쌓인다. `deleted_at IS NULL` 조건이 있어도 테이블 전체 크기는 줄지 않는다. 시간이 지나면서 삭제 비율이 높아지면 인덱스 효율이 떨어지고 VACUUM(PostgreSQL)이나 purge(MySQL InnoDB) 부하가 늘어난다.

아카이브 테이블은 데이터를 물리적으로 분리한다. 운영 테이블은 최근 N개월 데이터만 남고, 그 이전 데이터는 아카이브 테이블에 있다. 운영 테이블 크기가 일정하게 유지되므로 인덱스 크기도 일정하고, 캐시 히트율도 안정적이다.

단점은 명확하다. 쿼리가 두 테이블을 대상으로 해야 할 때 복잡해진다. 특정 기간을 가로질러 조회하면 운영과 아카이브를 모두 봐야 한다.

---

## 스키마 설계

### 동일 스키마 vs 컬럼 축소

아카이브 테이블 스키마를 어떻게 가져갈지는 보존 목적에 따라 달라진다.

**동일 스키마**는 운영 테이블과 완전히 같은 구조를 유지한다.

```sql
CREATE TABLE orders_archive LIKE orders;
```

장점은 이관이 단순하다. `INSERT INTO orders_archive SELECT * FROM orders WHERE ...`로 끝난다. 필요하면 아카이브 테이블에서 복구도 쉽다. 단점은 운영에서 불필요한 컬럼(실시간 상태 컬럼, 캐시성 컬럼 등)까지 보존된다.

**컬럼 축소**는 보존이 필요한 컬럼만 남긴다.

```sql
CREATE TABLE orders_archive (
  id           BIGINT        NOT NULL,
  user_id      BIGINT        NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL,
  status       VARCHAR(20)   NOT NULL,
  created_at   TIMESTAMP     NOT NULL,
  completed_at TIMESTAMP,
  archived_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);
```

`archived_at`을 추가하는 건 필수에 가깝다. 언제 아카이브됐는지 기록해야 데이터 수명 주기 추적이 가능하다.

컬럼 축소 방식은 테이블 크기가 작아지지만, 운영 테이블 스키마가 변경될 때마다 아카이브 테이블도 같이 관리해야 한다. 마이그레이션이 두 배로 늘어나는 셈이다. 실무에서는 동일 스키마로 시작하고, 스토리지나 성능 문제가 생겼을 때 컬럼 축소를 검토하는 게 현실적이다.

---

## 배치 이관과 락 최소화

### 기본 이관 패턴의 문제

```sql
BEGIN;

INSERT INTO orders_archive
  SELECT * FROM orders
  WHERE created_at < NOW() - INTERVAL 1 YEAR
    AND status IN ('COMPLETED', 'CANCELLED');

DELETE FROM orders
  WHERE created_at < NOW() - INTERVAL 1 YEAR
    AND status IN ('COMPLETED', 'CANCELLED');

COMMIT;
```

이 방식은 하나의 트랜잭션에서 대량 DELETE를 실행한다. rows가 수십만 건이면 트랜잭션이 수 분간 락을 잡고, 운영 테이블에 대한 다른 쿼리가 대기 상태에 걸린다. MySQL InnoDB에서는 언두 로그가 폭발적으로 쌓이고, 롤백 시 비용도 크다.

### 청크 단위 이관

```sql
-- 임시 테이블로 이관 대상 ID 관리 후 청크 처리
CREATE TEMPORARY TABLE tmp_archive_ids (id BIGINT PRIMARY KEY);

-- 루프: 1000건씩 반복
INSERT INTO tmp_archive_ids
  SELECT id FROM orders
  WHERE created_at < NOW() - INTERVAL 1 YEAR
    AND status IN ('COMPLETED', 'CANCELLED')
  ORDER BY id
  LIMIT 1000;

INSERT INTO orders_archive
  SELECT o.* FROM orders o
  JOIN tmp_archive_ids t ON o.id = t.id;

DELETE o FROM orders o
  JOIN tmp_archive_ids t ON o.id = t.id;

DROP TEMPORARY TABLE tmp_archive_ids;

-- 청크 간 딜레이 (복제 지연 완화)
DO SLEEP(0.1);
```

저장 프로시저보다 애플리케이션 코드(배치 Job)에서 루프를 제어하는 경우가 더 많다. 진행 상황을 로그로 남기고, 실패 시 이어서 실행하기 쉬운 구조를 만들기 위해서다.

청크 간 `SLEEP(0.1)` 딜레이는 마스터에서 대량 write가 발생할 때 슬레이브 복제가 따라오지 못하는 문제를 줄이기 위한 것이다. 배치 중에 복제 지연이 10초 이상 벌어지면 슬레이브를 읽는 쿼리에 영향이 생긴다.

### pt-archiver 활용 (MySQL)

Percona Toolkit의 `pt-archiver`는 청크 단위 이관을 자동으로 처리한다.

```bash
pt-archiver \
  --source  h=localhost,D=mydb,t=orders \
  --dest    h=localhost,D=mydb,t=orders_archive \
  --where   "created_at < NOW() - INTERVAL 1 YEAR AND status IN ('COMPLETED','CANCELLED')" \
  --limit   1000 \
  --sleep   0.1 \
  --no-check-charset \
  --progress 5000 \
  --statistics
```

`--limit 1000`이 청크 크기고, `--sleep 0.1`이 청크 간 딜레이다. `--statistics`를 추가하면 이관 속도와 총 rows 수를 마지막에 출력한다. 직접 배치를 짜는 것보다 안정적이고, 복제 지연 감지 옵션(`--check-slave-lag`)도 지원한다.

---

## 데드락 문제

배치 이관 중 데드락이 생기는 패턴은 대부분 두 가지다.

첫 번째는 배치가 orders 테이블을 범위 락으로 잡고 있는 상황에서 애플리케이션 트랜잭션이 같은 범위의 rows를 업데이트하려 할 때다.

```
배치 트랜잭션:  LOCK rows 100~2000 (INSERT + DELETE)
앱 트랜잭션:    UPDATE orders SET status='CANCELLED' WHERE id=1500
→ 데드락 또는 락 대기 타임아웃
```

청크를 작게 가져가고 트랜잭션 시간을 짧게 유지하면 충돌 확률이 줄어든다. 배치를 트래픽이 적은 새벽 시간대에 실행하는 것도 방법이다.

두 번째는 FK 참조 관계가 있을 때다. orders를 삭제하기 전에 order_items 같은 자식 테이블도 아카이브해야 한다. 순서가 잘못되면 FK 제약으로 삭제가 막히거나, 자식을 먼저 지우면 부모 측 트랜잭션과 교착이 생길 수 있다.

```sql
-- 이관 순서: 부모 먼저
INSERT INTO orders_archive SELECT * FROM orders WHERE ...;
INSERT INTO order_items_archive
  SELECT oi.* FROM order_items oi
  JOIN orders_archive oa ON oi.order_id = oa.id
  WHERE oa.archived_at >= NOW() - INTERVAL 1 MINUTE;

-- 삭제 순서: 자식 먼저
DELETE oi FROM order_items oi
  JOIN orders_archive oa ON oi.order_id = oa.id
  WHERE oa.archived_at >= NOW() - INTERVAL 1 MINUTE;

DELETE o FROM orders o
  JOIN orders_archive oa ON o.id = oa.id
  WHERE oa.archived_at >= NOW() - INTERVAL 1 MINUTE;
```

---

## 파티셔닝과 아카이브 혼용

파티셔닝을 이미 적용한 테이블에 아카이브 전략을 추가하면 관리 포인트가 두 곳이 된다.

MySQL에서 RANGE 파티셔닝으로 월별로 파티션을 나눈 테이블은 오래된 파티션을 `ALTER TABLE ... DROP PARTITION`으로 제거하는 방식이 가장 빠르다. DDL이므로 `DELETE`보다 훨씬 빠르고 락 범위도 파티션 단위다.

```sql
-- 2023년 1월 파티션 제거 (즉시, 메타데이터 변경만)
ALTER TABLE orders DROP PARTITION p_2023_01;
```

파티션 드롭이 가능한 경우, 별도 아카이브 테이블로 이관하는 것보다 이 방법이 훨씬 단순하다. 단, 파티션을 드롭하기 전에 데이터를 보존해야 한다면 먼저 아카이브 테이블로 복사한 뒤 드롭해야 한다.

```sql
-- 파티션 데이터를 아카이브 테이블로 복사 후 파티션 드롭
INSERT INTO orders_archive
  SELECT * FROM orders PARTITION (p_2023_01);

ALTER TABLE orders DROP PARTITION p_2023_01;
```

파티셔닝과 아카이브를 함께 쓸 때의 실제 문제는 파티션 키와 이관 조건이 일치하지 않을 때다. 파티션 키가 `created_at`인데 이관 조건이 `status = 'COMPLETED' AND completed_at < ...`이면, 특정 파티션 안에서도 조건을 만족하지 않는 row가 섞여 있어서 파티션 단위 드롭을 쓸 수 없다. 이 경우 파티셔닝의 이점이 반감된다.

파티셔닝을 도입할 때 처음부터 이관 조건을 파티션 키로 맞춰두는 게 나중에 편하다.

---

## 인덱스 전략

운영 테이블과 아카이브 테이블의 조회 패턴이 다르므로 인덱스 설계도 달라야 한다.

운영 테이블은 최신 데이터 중심의 포인트 조회, 범위 조회, 정렬이 많다. `user_id + status`, `created_at DESC` 같은 복합 인덱스가 필요하다.

아카이브 테이블은 특정 기간이나 특정 ID 기반의 조회가 대부분이다. "2023년 1분기 주문 통계", "특정 사용자의 과거 전체 이력" 같은 패턴이다. 카디널리티가 높은 컬럼(id, user_id)과 날짜 범위를 중심으로 인덱스를 구성한다.

```sql
-- 아카이브 테이블 인덱스: 운영보다 단순하게
CREATE TABLE orders_archive (
  id           BIGINT        NOT NULL,
  user_id      BIGINT        NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL,
  status       VARCHAR(20)   NOT NULL,
  created_at   TIMESTAMP     NOT NULL,
  archived_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_user_created (user_id, created_at),
  INDEX idx_archived_at  (archived_at)
);
```

운영 테이블에 있던 `status` 기반 인덱스는 아카이브에서 불필요한 경우가 많다. 아카이브된 데이터는 대부분 완료 상태이므로 status 필터의 선택성이 낮다.

아카이브 테이블에 인덱스를 너무 많이 만들면 이관 INSERT 속도가 느려진다. 청크당 1000건을 INSERT할 때마다 인덱스 업데이트 비용이 발생한다. 인덱스를 최소한으로 유지하고, 특정 조회 패턴이 생겼을 때 인덱스를 추가하는 게 맞다.

---

## 데이터 보존 정책 구현

보존 정책(retention policy)은 얼마나 오래 보관할 것인지를 정하고 그것을 자동으로 실행하는 것이다.

보존 기간을 테이블로 관리하면 코드 변경 없이 정책을 수정할 수 있다.

```sql
CREATE TABLE retention_policies (
  table_name        VARCHAR(64) NOT NULL PRIMARY KEY,
  online_months     INT         NOT NULL,
  archive_months    INT,                   -- NULL이면 영구 보존
  archive_condition TEXT        NOT NULL,  -- 이관 조건 SQL 조각
  last_archived_at  TIMESTAMP,
  last_purged_at    TIMESTAMP
);

INSERT INTO retention_policies VALUES
  ('orders',    12, 84,   "status IN ('COMPLETED','CANCELLED') AND created_at < NOW() - INTERVAL 12 MONTH", NULL, NULL),
  ('audit_log',  6, NULL, "created_at < NOW() - INTERVAL 6 MONTH", NULL, NULL);
```

배치 Job은 이 테이블을 읽어서 각 테이블의 이관과 정리를 처리한다. `online_months`가 지난 데이터는 아카이브로 이관하고, `archive_months`가 지난 데이터는 아카이브에서도 삭제한다.

```sql
-- 아카이브에서 물리 삭제 (보존 기간 초과 데이터)
DELETE FROM orders_archive
WHERE archived_at < NOW() - INTERVAL 84 MONTH
LIMIT 1000;
-- 반복 실행 필요
```

삭제도 청크 단위로 처리해야 한다. 아카이브 테이블이라도 수백만 건을 한 번에 DELETE하면 락과 복제 지연 문제가 생긴다.

---

## UNION ALL 통합 조회

특정 기간을 가로질러 조회해야 할 때는 운영 테이블과 아카이브 테이블을 UNION ALL로 합친다.

```sql
-- 특정 사용자의 전체 주문 이력 (운영 + 아카이브)
SELECT id, user_id, total_amount, status, created_at, 'online' AS source
FROM orders
WHERE user_id = 123

UNION ALL

SELECT id, user_id, total_amount, status, created_at, 'archive' AS source
FROM orders_archive
WHERE user_id = 123

ORDER BY created_at DESC;
```

`source` 컬럼을 추가하면 어느 테이블에서 온 데이터인지 구분할 수 있다. 디버깅 때 유용하다.

UNION은 중복 제거를 위해 정렬과 비교 연산을 한다. 두 테이블에 같은 id가 없다면 반드시 UNION ALL을 써야 한다. 불필요한 정렬 비용이 없어서 훨씬 빠르다.

### 성능 트레이드오프

UNION ALL 자체는 비싸지 않지만, 두 테이블을 각각 인덱스 없이 스캔하면 비용이 두 배가 된다.

```sql
-- EXPLAIN으로 양쪽 서브쿼리 실행 계획 확인
EXPLAIN
SELECT id, user_id, total_amount, status, created_at
FROM orders WHERE user_id = 123
UNION ALL
SELECT id, user_id, total_amount, status, created_at
FROM orders_archive WHERE user_id = 123;
```

각 SELECT 블록이 인덱스를 타는지 확인해야 한다. 아카이브 테이블에 `user_id` 인덱스가 없으면 전체 아카이브 테이블 스캔이 발생한다. 아카이브 테이블이 커질수록 이 비용이 크다.

통합 조회가 잦은 경우 뷰로 감싸는 경우가 있다.

```sql
CREATE VIEW orders_all AS
  SELECT *, 'online'  AS source FROM orders
  UNION ALL
  SELECT *, 'archive' AS source FROM orders_archive;
```

뷰는 쿼리를 단순하게 만들지만, 뷰 자체가 인덱스를 갖지는 않는다. MySQL 옵티마이저가 뷰를 펼쳐서 실행하므로, 각 서브쿼리가 인덱스를 잘 타는지 확인해야 한다. 뷰를 쓴다고 인덱스 설계를 느슨하게 해도 된다는 의미가 아니다.

---

## 복제 지연 문제

MySQL 바이너리 로그 기반 복제 환경에서 배치 이관은 슬레이브 복제 지연의 주요 원인이다.

마스터에서 `INSERT ... SELECT`로 10만 건을 이관하면, 바이너리 로그에 10만 건의 INSERT 이벤트가 기록된다. 슬레이브는 이 이벤트를 순서대로 재생하면서 같은 INSERT를 수행한다. 슬레이브 I/O와 SQL 스레드 성능이 마스터를 따라가지 못하면 복제 지연이 생긴다.

복제 지연이 벌어지면 슬레이브를 읽는 애플리케이션에서 오래된 데이터를 읽는 문제가 생긴다. Read After Write 일관성이 필요한 기능에서 버그로 나타난다.

대응 방법은 두 가지다.

청크 간 딜레이를 늘린다. `SLEEP(0.5)`로 여유를 주면 슬레이브가 따라올 시간이 생긴다. 이관 속도가 느려지는 트레이드오프가 있다.

`pt-archiver`의 `--check-slave-lag` 옵션을 쓴다. 슬레이브 지연이 설정한 임계값을 초과하면 배치를 일시 중단한다.

```bash
pt-archiver \
  --source  h=master,D=mydb,t=orders \
  --dest    h=master,D=mydb,t=orders_archive \
  --where   "..." \
  --limit   500 \
  --sleep   0.2 \
  --check-slave-lag h=slave1 \
  --max-lag 5
```

`--max-lag 5`는 슬레이브 지연이 5초를 넘으면 대기하다가 5초 이하로 떨어지면 재개한다.

ROW 포맷 바이너리 로그를 쓰는 경우 STATEMENT 포맷보다 로그 크기가 훨씬 크다. 대량 이관 중에 바이너리 로그 크기와 복제 대역폭을 모니터링해야 한다.

---

## 슬로우 쿼리 문제

배치 이관 중 자주 나타나는 슬로우 쿼리 패턴이 있다.

### INSERT INTO ... SELECT에서 풀스캔

WHERE 조건에 인덱스가 없으면 매 청크마다 운영 테이블 풀스캔이 발생한다. `created_at` 범위 조건이라면 `created_at` 인덱스가 있어야 한다.

```sql
-- 인덱스 없으면 매번 풀스캔
SELECT * FROM orders
WHERE created_at < '2023-01-01'
  AND status IN ('COMPLETED', 'CANCELLED')
LIMIT 1000;

-- (status, created_at) 복합 인덱스가 있을 때 범위 스캔으로 처리
```

### DELETE 서브쿼리 성능 문제

`DELETE ... WHERE id IN (SELECT id FROM ...)`에서 서브쿼리가 매번 실행되면 느리다. 이관된 ID를 임시 테이블에 저장하고 조인으로 삭제하는 방법이 빠르다.

```sql
-- 임시 테이블로 이관 대상 ID 관리
CREATE TEMPORARY TABLE tmp_archived_ids (id BIGINT PRIMARY KEY);

INSERT INTO tmp_archived_ids
  SELECT id FROM orders WHERE created_at < '2023-01-01' LIMIT 1000;

INSERT INTO orders_archive
  SELECT o.* FROM orders o JOIN tmp_archived_ids t ON o.id = t.id;

DELETE o FROM orders o JOIN tmp_archived_ids t ON o.id = t.id;

DROP TEMPORARY TABLE tmp_archived_ids;
```

### 이관 진행 상황 확인 시 COUNT 풀스캔

배치 배포 전후 row count를 확인할 때 `SELECT COUNT(*) FROM orders`를 쓰면 InnoDB에서 풀스캔이 발생한다. 정확도가 낮아도 괜찮으면 `INFORMATION_SCHEMA.TABLES`의 `TABLE_ROWS`를 쓰는 게 빠르다. 이관 진행 상황 모니터링 용도라면 충분하다.

```sql
SELECT TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mydb' AND TABLE_NAME = 'orders';
```

---

## 관련 문서

- Soft_Delete.md — 소프트 삭제 패턴, 아카이브와의 조합
- 데이터베이스_샤딩.md — 대용량 테이블 수평 분산
- 읽기_전용_복제본.md — 복제 지연 관리
- CDC_Pipeline.md — 변경 데이터 캡처로 아카이브 대체하는 경우
