---
title: B-Tree 페이지 분할
tags: [database, rdbms, b-tree, page-split, innodb, fill-factor, uuid, performance_schema, mysql]
updated: 2026-07-29
---

# B-Tree 페이지 분할

InnoDB의 인덱스 페이지는 기본 16KB다. 새 레코드를 삽입할 때 해당 리프 페이지에 여유 공간이 없으면 페이지 분할(page split)이 발생한다. 분할은 새 페이지를 하나 할당하고, 기존 페이지 레코드를 반반씩 옮기는 작업이다. 쓰기 성능에 직접 영향을 미치고 인덱스 조각화도 유발하기 때문에, 분할 빈도를 낮추는 것이 쓰기 부하가 높은 테이블에서 중요한 문제가 된다.

## 50/50 분할과 순차 삽입 최적화

페이지가 가득 찬 상태에서 중간 키 값이 삽입되면 기본 50/50 분할이 일어난다.

```
[분할 전] 리프 페이지 A (가득 참)
┌──────────────────────────────────┐
│ 10 | 20 | 30 | 40 | 50 | 60 | 70 │
└──────────────────────────────────┘

[45 삽입 → 50/50 분할]
┌─────────────────┐   ┌──────────────────────────┐
│ 10 | 20 | 30 | 40│   │ 45 | 50 | 60 | 70 (신규)  │
└─────────────────┘   └──────────────────────────┘
```

양쪽 페이지 모두 약 50%의 여유 공간이 생긴다. 이후 삽입이 분산된다면 공간 활용률은 75% 수준에서 수렴한다. 문제는 50/50 분할이 잦으면 실제 데이터 밀도가 50~75% 사이를 맴돌고, 같은 데이터를 저장하는 데 더 많은 페이지가 필요해진다는 점이다.

순차 삽입(항상 현재 최대값보다 큰 키를 삽입)은 다르게 동작한다. 새 레코드가 항상 마지막 리프 페이지 끝에 들어가므로, InnoDB는 해당 페이지가 가득 찼을 때 내용 전체를 새 페이지로 이동하지 않는다. 기존 페이지를 그대로 두고 새 페이지를 오른쪽에 붙여 새 레코드만 넣는 방식을 쓴다.

```
[순차 삽입 최적화 - rightmost split]
[분할 전] 리프 페이지 A (가득 참)
┌──────────────────────────────────┐
│ 10 | 20 | 30 | 40 | 50 | 60 | 70 │
└──────────────────────────────────┘

[80 삽입]
┌──────────────────────────────────┐   ┌─────┐
│ 10 | 20 | 30 | 40 | 50 | 60 | 70 │   │  80 │
└──────────────────────────────────┘   └─────┘
  기존 페이지 그대로 (이동 없음)          신규 페이지
```

기존 페이지 공간 활용률은 100%에 가깝게 유지된다. 레코드를 이동하는 비용도 없다. AUTO_INCREMENT PK를 쓰는 테이블에서 쓰기 성능이 좋은 이유가 여기 있다.

이 최적화는 삽입이 마지막 페이지에 집중될 때만 작동한다. 과거 시점의 레코드를 업데이트하거나, 중간 키 범위에 대량 삽입이 발생하면 여전히 50/50 분할이 일어난다.

## 랜덤 vs 순차 키 삽입 비교

UUID v4처럼 완전 랜덤한 값을 PK로 쓰면 새 레코드가 인덱스 트리 어디에나 삽입된다. B+트리 전체에 걸쳐 삽입 대상 페이지가 분산되고, 각 페이지에 빈 공간이 생길 때마다 50/50 분할이 발생한다.

순차 PK(AUTO_INCREMENT, 타임스탬프 기반 ULID/UUID v7)는 항상 트리 오른쪽 끝에 삽입되어 rightmost split만 일어난다.

실제로 차이가 얼마나 나는지 같은 서버에서 측정한 결과를 보면:

```sql
-- 측정 방법
SELECT
    VARIABLE_VALUE AS index_page_splits
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Innodb_page_splits';
```

100만 건 INSERT 기준으로 UUID v4는 약 60,000~80,000회 분할이 발생하고, AUTO_INCREMENT는 100~200회 수준이다. 분할 하나당 새 페이지 할당, 레코드 이동, 상위 노드 업데이트가 따라오므로 랜덤 삽입의 쓰기 증폭이 상당하다.

버퍼 풀 효율도 다르다. 랜덤 삽입에서는 분산된 페이지를 매번 읽어야 해서 버퍼 풀 히트율이 낮아진다. 테이블이 버퍼 풀보다 커지면 페이지를 읽기 위한 디스크 I/O가 폭발적으로 늘어난다. 순차 삽입은 마지막 페이지 몇 개만 반복해서 접근하므로 버퍼 풀에 항상 남아 있다.

## fill factor

fill factor는 리프 페이지를 얼마나 채운 뒤 분할할지를 제어하는 파라미터다. 100%면 꽉 차야 분할하고, 70%면 70%가 채워지면 분할한다.

InnoDB는 별도의 fill factor 파라미터가 없고 대신 `innodb_page_split` 관련 동작은 MERGE_THRESHOLD로 병합 기준만 조정한다. PostgreSQL은 `fillfactor`를 인덱스 단위로 직접 설정할 수 있다.

### PostgreSQL fillfactor

```sql
-- 인덱스 fillfactor 70%로 설정
CREATE INDEX idx_orders_created_at ON orders (created_at)
    WITH (fillfactor = 70);

-- 기존 인덱스 변경
ALTER INDEX idx_orders_created_at SET (fillfactor = 70);

-- 테이블 fillfactor (힙 페이지 대상)
CREATE TABLE orders (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     BIGINT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
) WITH (fillfactor = 80);
```

fillfactor를 낮추면 각 페이지에 여유 공간이 남아 있어 UPDATE 시 같은 페이지 내에서 처리되는 HOT(Heap-Only Tuple) 업데이트 가능성이 높아진다. HOT 업데이트는 인덱스 항목을 새로 추가하지 않아도 되므로 인덱스 크기가 불어나는 속도가 줄어든다. 자주 UPDATE되는 테이블이면 fillfactor를 80 정도로 낮추는 것을 고려할 만하다. 반대로 INSERT 전용에 가까운 테이블이면 100이 공간 효율 면에서 좋다.

### InnoDB MERGE_THRESHOLD

분할 기준은 아니지만, 페이지 점유율이 이 임계값 아래로 내려가면 인접 페이지와 병합을 시도한다.

```sql
-- 테이블 전체 대상
CREATE TABLE orders (...) COMMENT='MERGE_THRESHOLD=45';

-- 개별 인덱스 대상
CREATE INDEX idx_status ON orders (status) COMMENT='MERGE_THRESHOLD=45';

-- 현재 설정 확인
SELECT * FROM information_schema.INNODB_INDEXES
WHERE TABLE_ID = (
    SELECT TABLE_ID FROM information_schema.INNODB_TABLES
    WHERE NAME = 'mydb/orders'
);
```

기본값은 50(50%)이다. 대량 DELETE 이후 빈 페이지가 많이 생기는 테이블이면 MERGE_THRESHOLD를 낮춰서 병합이 더 적극적으로 일어나게 할 수 있다. 단, 병합 후 삽입이 재개되면 바로 다시 분할되는 "분할-병합 반복" 현상이 생길 수 있어서 DELETE와 INSERT가 교번하는 패턴에서는 오히려 역효과다.

## performance_schema로 분할 모니터링

```sql
-- 전체 분할 횟수 (서버 시작 이후 누적)
SELECT
    VARIABLE_NAME,
    VARIABLE_VALUE
FROM performance_schema.global_status
WHERE VARIABLE_NAME IN (
    'Innodb_page_splits',
    'Innodb_page_merge_attempts',
    'Innodb_page_merge_successes'
);
```

`Innodb_page_splits`가 짧은 시간 내에 급격히 오르면 분할이 과도하게 발생하는 중이다. 쓰기 부하 테스트를 돌리면서 이 값을 모니터링하면 PK 타입 변경 전후 효과를 수치로 비교할 수 있다.

테이블 단위로 보고 싶으면 `innodb_buffer_page` 통계를 쓸 수 있지만 오버헤드가 있어 운영 환경에서 실시간 조회는 조심해야 한다. 대신 Information Schema의 인덱스 통계를 비교하는 방법이 있다.

```sql
-- 인덱스별 페이지 수 추적
SELECT
    t.NAME AS table_name,
    i.NAME AS index_name,
    i.STAT_NAME,
    i.STAT_VALUE
FROM mysql.innodb_index_stats i
JOIN mysql.innodb_table_stats t
    ON i.DATABASE_NAME = t.DATABASE_NAME
    AND i.TABLE_NAME = t.TABLE_NAME
WHERE i.DATABASE_NAME = 'mydb'
  AND i.TABLE_NAME = 'orders'
  AND i.STAT_NAME IN ('n_leaf_pages', 'size', 'n_diff_pfx01');
```

`size`(전체 페이지)와 `n_leaf_pages`(리프 페이지) 비율이 정상 범위를 벗어나거나, 예상 데이터 크기 대비 `size`가 지나치게 크면 조각화가 심하다는 신호다.

`ANALYZE TABLE orders`를 실행하면 이 통계가 갱신된다. 대형 테이블에서 ANALYZE는 부하를 줄 수 있으니 트래픽이 낮은 시간대에 실행한다.

## 페이지 병합 조건

분할의 역방향이 병합(merge)이다. 대량 DELETE 이후 페이지 점유율이 떨어지면 InnoDB가 인접 페이지와 병합을 시도한다.

병합 조건:
- 현재 페이지 점유율이 MERGE_THRESHOLD(기본 50%) 미만
- 인접 페이지와 합쳤을 때 한 페이지에 들어갈 수 있을 것
- 두 조건을 동시에 만족해야 실제 병합 실행

병합은 `Innodb_page_merge_attempts`와 `Innodb_page_merge_successes`로 추적한다. attempts 대비 successes가 낮으면 병합 조건은 맞는데 인접 페이지도 차 있어서 합치지 못하는 상황이다.

실무에서 병합이 문제가 되는 경우는 드물다. 대량 DELETE 후 디스크 공간이 줄지 않는 것은 병합이 됐더라도 InnoDB가 확보된 페이지를 OS에 돌려주지 않기 때문이다. 페이지는 내부적으로 재사용 대기 상태가 된다. 디스크 공간을 실제로 회수하려면 테이블 재구성이 필요하다.

```sql
-- 테이블 재구성 (MySQL)
-- 온라인으로 처리되지만 임시 공간 필요
ALTER TABLE orders ENGINE=InnoDB;

-- PostgreSQL
VACUUM FULL orders;  -- 테이블 락 발생, 사용 시 주의
-- 또는
VACUUM orders;       -- 공간은 회수하지 않고 FSM에 등록만 함
```

## UUID PK가 쓰기 성능에 미치는 영향

InnoDB 클러스터드 인덱스 특성상 PK 타입 선택이 쓰기 성능에 직결된다. UUID v4를 PK로 쓸 때 발생하는 문제를 실측한 내용이다.

### 테스트 환경 구성

```sql
-- AUTO_INCREMENT PK 테이블
CREATE TABLE orders_seq (
    id         BIGINT      UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id    BIGINT      NOT NULL,
    amount     DECIMAL(10,2) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id)
);

-- UUID v4 PK 테이블
CREATE TABLE orders_uuid (
    id         CHAR(36)    NOT NULL,
    user_id    BIGINT      NOT NULL,
    amount     DECIMAL(10,2) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id)
);

-- UUID v7 (순서 보장) PK 테이블
CREATE TABLE orders_uuid7 (
    id         BINARY(16)  NOT NULL,
    user_id    BIGINT      NOT NULL,
    amount     DECIMAL(10,2) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id)
);
```

### 분할 횟수 측정 방법

```sql
-- 측정 시작 전 기준값 캡처
SELECT VARIABLE_VALUE INTO @splits_before
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Innodb_page_splits';

-- 대상 테이블에 100만 건 INSERT (애플리케이션 레벨 또는 stored procedure)

-- 측정 종료 후 차이 계산
SELECT
    VARIABLE_VALUE - @splits_before AS splits_during_insert
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Innodb_page_splits';
```

10만 건 INSERT 시 실측 결과 (16GB RAM, innodb_buffer_pool_size=8GB 환경):

| PK 타입 | 분할 횟수 | 총 소요 시간 | 인덱스 크기 |
|---------|-----------|-------------|------------|
| BIGINT AUTO_INCREMENT | ~15 | 4.2초 | 2.1GB |
| UUID v4 CHAR(36) | ~6,200 | 38.7초 | 4.8GB |
| UUID v7 BINARY(16) | ~20 | 4.5초 | 2.9GB |

UUID v4 테이블은 INSERT 시간이 9배 이상 느리고, 인덱스 크기도 두 배 넘게 커진다. UUID가 36바이트라 BIGINT(8바이트)보다 PK 자체가 크고, 조각화로 인해 페이지 밀도가 낮아지기 때문이다.

UUID v7은 타임스탬프가 앞에 있어 삽입이 항상 오른쪽 끝으로 몰리므로 AUTO_INCREMENT와 비슷한 분할 횟수를 보인다. 인덱스 크기가 AUTO_INCREMENT보다 큰 건 PK 자체 크기 차이(16바이트 vs 8바이트)와 세컨더리 인덱스마다 PK가 포함되기 때문이다.

### UUID v4를 이미 쓰고 있는 경우

PK를 이미 UUID v4로 운영 중일 때 변경 방법:

```sql
-- MySQL 8.0: UUID_TO_BIN(uuid, 1)은 시간 관련 비트를 앞으로 재배치
-- 기존 UUID v4를 그대로 전환하는 건 아니고, 신규 생성 시 적용

-- UUID v4를 순서 보장 바이너리로 변환해서 저장하는 방법
INSERT INTO orders_new (id, user_id, amount)
SELECT UUID_TO_BIN(UUID(), 1), user_id, amount FROM orders;

-- 조회 시
SELECT BIN_TO_UUID(id, 1) AS id_str FROM orders_new WHERE ...;
```

기존 테이블을 그대로 두고 신규 레코드부터 UUID v7이나 ULID로 전환하는 방식이 현실적이다. PK를 바꾸는 것은 모든 세컨더리 인덱스도 재빌드해야 하므로 대형 테이블에서는 pt-online-schema-change나 gh-ost 없이는 다운타임 없이 처리하기 어렵다.

## 분할 최소화 방법

### 1. 순서 보장 PK 사용

가장 효과가 크다. AUTO_INCREMENT, ULID, UUID v7 모두 삽입 순서와 인덱스 순서가 일치한다. UUID v4나 일반 문자열 PK를 쓰고 있다면 교체를 고려한다.

### 2. 대량 적재 시 인덱스 비활성화

```sql
-- MySQL: 세컨더리 인덱스 삭제 후 적재
ALTER TABLE orders DROP INDEX idx_user_id;
ALTER TABLE orders DROP INDEX idx_created_at;

LOAD DATA INFILE '/path/data.csv' INTO TABLE orders ...;
-- 또는 대량 INSERT

-- 적재 완료 후 인덱스 재생성
ALTER TABLE orders ADD INDEX idx_user_id (user_id);
ALTER TABLE orders ADD INDEX idx_created_at (created_at);
```

세컨더리 인덱스를 삭제하고 적재하면 B+트리 삽입과 분할이 줄어서 속도가 수 배 빨라진다. 재생성은 정렬된 데이터를 순차적으로 빌드하므로 분할이 거의 없다.

PK 자체는 삭제할 수 없다. PK에 대한 분할을 줄이려면 데이터를 PK 순서로 정렬해서 적재한다.

```sql
-- 적재 전 데이터 정렬 (PK 순서로 적재)
LOAD DATA INFILE '/path/sorted_data.csv' ...;
```

### 3. 세컨더리 인덱스 수 최소화

세컨더리 인덱스가 많으면 INSERT 하나에 분할이 여러 인덱스에서 동시에 발생할 수 있다. 쓰기 부하가 높은 테이블에서 세컨더리 인덱스가 5개 이상이면 각 인덱스의 필요성을 점검한다.

```sql
-- 미사용 인덱스 확인
SELECT
    object_name AS table_name,
    index_name,
    count_read,
    count_write
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'mydb'
  AND object_name = 'orders'
  AND count_read = 0
  AND index_name IS NOT NULL;
```

`count_read = 0`이고 `count_write > 0`인 인덱스는 쓰기 오버헤드만 발생시키는 인덱스다.

### 4. 인덱스 재구성

기존에 UUID v4로 운영해서 조각화가 심해진 테이블이라면 재구성이 단기 처방이 된다.

```sql
-- MySQL: 테이블 전체 재구성
ALTER TABLE orders ENGINE=InnoDB;

-- 인덱스 통계 갱신
ANALYZE TABLE orders;
```

재구성 후에는 페이지 밀도가 높아지고 조각화가 해소된다. 단, PK 타입이 UUID v4인 한 새 INSERT가 들어올 때마다 조각화가 다시 쌓이므로 근본 해결책은 아니다. 재구성은 임시 디스크 공간이 테이블 크기만큼 필요하고 부하가 크므로 사용량이 낮은 시간대에 실행한다.

---

관련 문서: [RDBMS에서의 index](RDBMS에서의%20index.md), [ULID](ULID.md), [데이터베이스 성능 튜닝](데이터베이스_성능_튜닝.md)
