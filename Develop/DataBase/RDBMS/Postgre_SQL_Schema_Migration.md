---
title: PostgreSQL 스키마 마이그레이션
tags: [postgresql, schema-migration, ddl-lock, concurrently, pg-repack, flyway, expand-migrate-contract, pg-dump]
updated: 2026-08-06
---

# PostgreSQL 스키마 마이그레이션

MySQL과 PostgreSQL의 DDL 동작은 근본적으로 다르다. MySQL은 `ALTER TABLE` 시 내부적으로 테이블을 복사하는 방식이고, pt-osc나 gh-ost 같은 외부 도구로 락을 우회한다. PostgreSQL은 DDL이 트랜잭션 안에서 실행되고, 락 모드도 세분화돼 있다. 같은 `ALTER TABLE`이라도 어떤 변경인지에 따라 락 모드가 달라진다.

## DDL 락 모드

PostgreSQL은 락 모드를 8단계로 구분한다. 마이그레이션에서 자주 마주치는 건 `ACCESS EXCLUSIVE`와 `ShareUpdateExclusiveLock` 두 가지다.

### ACCESS EXCLUSIVE

`ALTER TABLE`의 기본 락 모드다. `SELECT`를 포함한 모든 쿼리를 차단한다. 이 모드를 잡으려면 이미 실행 중인 쿼리가 모두 끝날 때까지 기다려야 한다. 문제는 대기 자체가 뒤에 오는 쿼리들도 줄 세운다는 점이다.

장기 실행 쿼리(배치, 리포트 쿼리)가 테이블을 잡고 있는 상태에서 `ALTER TABLE`이 들어오면 락을 기다리며 블로킹된다. 그 뒤에 오는 `SELECT`들도 `ACCESS EXCLUSIVE`가 대기 중이라는 이유로 모두 대기한다. 테이블 전체가 멈추는 것처럼 보이는 상황이 생긴다.

대기열 누적을 막으려면 `lock_timeout`을 짧게 설정하고, 획득 실패 시 재시도하는 방식을 쓴다.

```sql
SET lock_timeout = '2s';
ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) NULL;
```

`lock_timeout` 초과로 실패하면 대기 중인 쿼리가 풀리고 서비스가 회복된다. 배포 스크립트에서 재시도 루프를 짜거나, 트래픽이 낮은 시간대에 재실행하면 된다.

### ShareUpdateExclusiveLock

`CREATE INDEX CONCURRENTLY`, `VACUUM`, `ANALYZE` 등이 잡는 락 모드다. `SELECT`와 `INSERT/UPDATE/DELETE`를 모두 허용한다. 다른 `ShareUpdateExclusiveLock`과만 충돌한다. `CONCURRENTLY` 인덱스 두 개를 동시에 만들 수는 없지만, 일반 DML은 계속 진행된다.

## CONCURRENTLY 인덱스 생성과 삭제

운영 중인 테이블에 인덱스를 추가할 때 `CREATE INDEX`를 그냥 쓰면 인덱스 전체를 빌드하는 동안 쓰기를 막는다. `CONCURRENTLY`를 쓰면 쓰기를 허용하면서 빌드할 수 있다.

```sql
-- 일반: 빌드 중 쓰기 차단
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- CONCURRENTLY: 쓰기 허용하면서 빌드
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

`CONCURRENTLY`는 테이블을 두 번 스캔한다. 첫 번째 스캔 후 빌드한 인덱스가 최신 상태인지 확인하기 위해 두 번째 스캔을 한다. 그래서 일반 `CREATE INDEX`보다 시간이 더 걸린다. 수천만 행 테이블이면 수십 분도 걸릴 수 있다.

중간에 `CONCURRENTLY` 빌드가 실패하면 `INVALID` 상태의 인덱스가 남는다.

```sql
-- INVALID 인덱스 확인
SELECT c.relname AS index_name, t.relname AS table_name
FROM pg_class c
JOIN pg_index i ON c.oid = i.indexrelid
JOIN pg_class t ON t.oid = i.indrelid
WHERE i.indisvalid = false;
```

`INVALID` 인덱스는 쿼리에 사용되지 않지만 `INSERT/UPDATE/DELETE` 시 업데이트 대상이 된다. 발견하면 삭제하고 다시 만들어야 한다.

```sql
DROP INDEX CONCURRENTLY idx_orders_user_id;
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

인덱스 삭제도 `CONCURRENTLY`를 쓸 수 있다. 기본 `DROP INDEX`는 `ACCESS EXCLUSIVE`를 잡기 때문에 운영 중에는 `CONCURRENTLY`가 필요하다.

**CONCURRENTLY 제약:**
- 트랜잭션 블록 안에서 실행할 수 없다. `BEGIN` 없이 단독으로 실행해야 한다.
- 고유 인덱스를 `CONCURRENTLY`로 만드는 도중 유니크 위반 데이터가 있으면 `INVALID` 상태가 된다.

## 컬럼 추가 시 락

PostgreSQL 11 이전에는 `DEFAULT` 값이 있는 컬럼을 추가하면 전체 행을 재작성했다. 1억 행 테이블에 `DEFAULT 0`인 컬럼을 추가하면 모든 행을 업데이트하는 것과 같았다. 그동안 `ACCESS EXCLUSIVE` 락이 유지됐다.

PostgreSQL 11부터는 `NOT NULL DEFAULT` 컬럼 추가가 즉시 완료된다. 메타데이터에 기본값을 저장하고 기존 행 재작성을 생략한다.

```sql
-- PostgreSQL 11+: 즉시 완료
ALTER TABLE orders ADD COLUMN status_code SMALLINT NOT NULL DEFAULT 0;
```

PostgreSQL 10 이하에서 같은 변경을 락 없이 하려면 세 단계로 나눠야 한다.

```sql
-- 1. NULL 허용으로 컬럼 추가 (즉시 완료)
ALTER TABLE orders ADD COLUMN status_code SMALLINT NULL;

-- 2. 기존 데이터를 배치로 채움
UPDATE orders SET status_code = 0 WHERE status_code IS NULL;

-- 3. NOT NULL 제약과 기본값 추가
ALTER TABLE orders ALTER COLUMN status_code SET NOT NULL;
ALTER TABLE orders ALTER COLUMN status_code SET DEFAULT 0;
```

### NOT NULL 제약 추가

기존 컬럼에 `NOT NULL` 제약을 추가하면 PostgreSQL은 NULL인 행이 없다는 걸 확인하기 위해 전체 테이블 스캔을 한다. 이 시간 동안 `ACCESS EXCLUSIVE`가 유지된다.

PostgreSQL 12부터는 `NOT VALID` 옵션으로 락 노출 시간을 줄일 수 있다.

```sql
-- 1단계: CHECK 제약 추가. 신규 행만 검사하고 기존 행은 넘어감
--        ACCESS EXCLUSIVE이지만 즉시 완료
ALTER TABLE orders ADD CONSTRAINT orders_user_id_not_null
    CHECK (user_id IS NOT NULL) NOT VALID;

-- 2단계: 기존 행 검증. ShareUpdateExclusiveLock으로 DML은 계속 허용
ALTER TABLE orders VALIDATE CONSTRAINT orders_user_id_not_null;

-- 3단계: 실제 NOT NULL 제약으로 전환
--        이미 검증된 CHECK 제약이 있으므로 테이블 스캔 생략, 즉시 완료
ALTER TABLE orders ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE orders DROP CONSTRAINT orders_user_id_not_null;
```

## 컬럼 타입 변경

타입 변경은 락 회피가 까다롭다. PostgreSQL은 기존 값을 새 타입으로 변환할 수 없거나 변환이 필요하면 전체 행을 재작성한다.

VARCHAR 길이를 늘리는 경우(`VARCHAR(20)` → `VARCHAR(30)`)는 예외다. PostgreSQL은 VARCHAR의 최대 길이를 메타데이터에만 저장하므로 행 재작성이 없고 즉시 완료된다. 반대로 길이를 줄이거나(`VARCHAR(20)` → `VARCHAR(10)`), 타입을 바꾸거나(`VARCHAR` → `INTEGER`), `TEXT` → `VARCHAR(n)`으로 제한을 걸면 전체 재작성이 필요하다.

타입 변경을 락 없이 하려면 새 컬럼을 만들고 데이터를 이전해야 한다.

```sql
-- 1. 새 컬럼 추가
ALTER TABLE users ADD COLUMN phone_new VARCHAR(30) NULL;

-- 2. 기존 데이터 배치 복사
UPDATE users SET phone_new = phone WHERE phone IS NOT NULL;

-- 3. 복사 중 신규 변경사항을 동기화하는 트리거
CREATE OR REPLACE FUNCTION sync_phone() RETURNS TRIGGER AS $$
BEGIN
    NEW.phone_new := NEW.phone;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_phone
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION sync_phone();

-- 4. 앱 코드를 새 컬럼 기준으로 전환 후 트리거 정리
DROP TRIGGER trg_sync_phone ON users;
DROP FUNCTION sync_phone();
ALTER TABLE users DROP COLUMN phone;
ALTER TABLE users RENAME COLUMN phone_new TO phone;
```

## 컬럼 삭제

`DROP COLUMN`은 내부적으로 컬럼을 실제로 제거하지 않는다. 시스템 카탈로그에서 해당 컬럼을 "삭제됨"으로 표시만 하므로 빠르다. 삭제된 컬럼의 공간은 테이블에 그대로 남고, `VACUUM FULL`이나 `pg_repack`을 실행해야 회수된다.

```sql
ALTER TABLE users DROP COLUMN old_column;  -- 즉시 완료, 공간은 나중에 회수
```

## pg_repack으로 테이블 Bloat 제거

PostgreSQL MVCC는 업데이트된 행을 제자리에 수정하지 않고 새 버전을 만들고 구 버전을 죽은 투플(dead tuple)로 남긴다. `VACUUM`은 죽은 투플을 정리하지만 테이블 파일 크기는 줄이지 않는다. 이 상태를 bloat라고 한다.

`VACUUM FULL`은 bloat를 제거하고 공간을 OS에 반환한다. `ACCESS EXCLUSIVE`를 잡고 실행되므로 서비스 중에 쓸 수 없다.

`pg_repack`은 `ACCESS EXCLUSIVE` 없이 테이블을 재구성한다. 내부적으로 새 테이블을 만들고 데이터를 복사하면서 복사 중 변경사항을 로그 테이블로 추적한다. 복사 완료 후 짧은 락으로 교체하는 방식이다.

```bash
# 특정 테이블 재구성
pg_repack -h localhost -p 5432 -U myuser -d mydb -t orders

# DB 전체 재구성
pg_repack -h localhost -p 5432 -U myuser -d mydb
```

pg_repack 실행 전 bloat 수준을 확인한다.

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    n_dead_tup,
    n_live_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY dead_ratio DESC;
```

dead_ratio가 20% 이상이거나 테이블 크기가 예상보다 크게 크면 pg_repack을 고려한다.

**pg_repack 주의사항:**
- 테이블에 `PRIMARY KEY` 또는 `NOT NULL UNIQUE` 인덱스가 없으면 실행이 거부된다.
- 실행 중 테이블 크기만큼 디스크 공간을 추가로 사용한다. 100GB 테이블이면 100GB 여유 공간이 필요하다.
- `pg_repack` 버전과 PostgreSQL 버전을 맞춰야 한다. 버전 불일치 시 실패한다.

## Expand-Migrate-Contract 단계별 실행

`name → first_name + last_name` 컬럼 분리 시나리오로 각 단계를 설명한다. 단계 사이에는 서비스 배포가 완료된 상태여야 하고, 각 단계 끝은 독립적으로 stable한 상태다.

### Phase 1: Expand

기존 컬럼을 건드리지 않고 새 컬럼을 추가한다.

```sql
-- V10__expand_name_columns.sql
SET lock_timeout = '2s';
ALTER TABLE users ADD COLUMN first_name VARCHAR(100) NULL;
ALTER TABLE users ADD COLUMN last_name  VARCHAR(100) NULL;
```

`NOT NULL`을 걸지 않는다. 구 버전 서비스는 `first_name`/`last_name`을 채우지 않는다. Expand 직후에는 새 컬럼이 전부 NULL이고, 구 코드가 INSERT/UPDATE를 해도 오류가 나지 않아야 한다.

Expand 완료 후 컬럼이 추가됐는지 확인:

```sql
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('name', 'first_name', 'last_name')
ORDER BY ordinal_position;
```

이 단계에서 서비스 배포가 없다면 언제든 롤백 가능하다:

```sql
-- Expand 롤백 (서비스 배포 전에만 무조건 안전)
SET lock_timeout = '2s';
ALTER TABLE users DROP COLUMN IF EXISTS first_name;
ALTER TABLE users DROP COLUMN IF EXISTS last_name;
```

### Phase 2: Migrate

두 가지를 동시에 진행한다. 신규 쓰기가 새 컬럼을 채우도록 트리거를 걸고, 기존 데이터를 배치로 마이그레이션한다.

**이중 쓰기 트리거:**

```sql
CREATE OR REPLACE FUNCTION sync_name_split()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.name IS NOT NULL THEN
        NEW.first_name := split_part(TRIM(NEW.name), ' ', 1);
        NEW.last_name  := NULLIF(TRIM(split_part(TRIM(NEW.name), ' ', 2)), '');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_name_split
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION sync_name_split();
```

트리거가 걸리면 서비스가 `name`을 업데이트할 때마다 `first_name`/`last_name`도 자동으로 채워진다. 서비스 코드를 바꾸지 않아도 새 컬럼이 채워지는 장점이 있다.

트리거를 쓰지 않는다면 서비스 코드에서 이중 쓰기를 구현해야 한다. 그 경우 모든 서비스 인스턴스가 이중 쓰기 버전으로 배포될 때까지 새 컬럼이 NULL인 레코드가 계속 생긴다.

**배치 마이그레이션:**

```sql
-- 배치 단위로 반복 실행. start_id와 end_id는 외부에서 주입
UPDATE users
SET
    first_name = split_part(TRIM(name), ' ', 1),
    last_name  = NULLIF(TRIM(split_part(TRIM(name), ' ', 2)), '')
WHERE first_name IS NULL
  AND id BETWEEN :start_id AND :end_id;
```

`id` 범위를 1000~5000건 단위로 나눠 반복한다. 한 트랜잭션에 수십만 건을 처리하면 dead tuple이 대량 생성되고 autovacuum이 따라가지 못한다. 중간에 멈춰도 `WHERE first_name IS NULL` 조건으로 재시작할 수 있다.

잠긴 레코드로 인한 배치 실패를 막으려면 `SKIP LOCKED`를 쓴다:

```sql
-- 잠긴 레코드는 건너뛰고 나중에 재처리
WITH batch AS (
    SELECT id FROM users
    WHERE first_name IS NULL
      AND id BETWEEN :start_id AND :end_id
    ORDER BY id
    FOR UPDATE SKIP LOCKED
)
UPDATE users u
SET
    first_name = split_part(TRIM(u.name), ' ', 1),
    last_name  = NULLIF(TRIM(split_part(TRIM(u.name), ' ', 2)), '')
FROM batch
WHERE u.id = batch.id;
```

**진행률 모니터링:**

```sql
SELECT
    COUNT(*)                                                              AS total,
    COUNT(*) FILTER (WHERE first_name IS NOT NULL)                       AS migrated,
    COUNT(*) FILTER (WHERE first_name IS NULL)                           AS remaining,
    ROUND(COUNT(*) FILTER (WHERE first_name IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0), 2) AS pct
FROM users;
```

`pct`가 100%이고 `remaining`이 0건이면 Phase 3으로 넘어갈 수 있다.

### Phase 3: Contract

구 버전 서비스가 완전히 내려간 후 실행한다.

`NOT NULL`을 바로 걸면 전체 테이블 스캔 동안 `ACCESS EXCLUSIVE`가 유지된다. `NOT VALID`로 분리하면 락 노출 시간을 줄인다:

```sql
-- V15__contract_name_column.sql

-- 1. 신규 행만 검사하는 CHECK 제약 추가 (즉시 완료)
ALTER TABLE users ADD CONSTRAINT users_first_name_not_null
    CHECK (first_name IS NOT NULL) NOT VALID;

ALTER TABLE users ADD CONSTRAINT users_last_name_not_null
    CHECK (last_name IS NOT NULL) NOT VALID;

-- 2. 기존 행 검증 (ShareUpdateExclusiveLock, DML 허용)
ALTER TABLE users VALIDATE CONSTRAINT users_first_name_not_null;
ALTER TABLE users VALIDATE CONSTRAINT users_last_name_not_null;

-- 3. NOT NULL 제약 전환 (CHECK 제약이 있으므로 테이블 스캔 생략, 즉시 완료)
ALTER TABLE users ALTER COLUMN first_name SET NOT NULL;
ALTER TABLE users ALTER COLUMN last_name SET NOT NULL;
ALTER TABLE users DROP CONSTRAINT users_first_name_not_null;
ALTER TABLE users DROP CONSTRAINT users_last_name_not_null;

-- 4. 트리거 정리
DROP TRIGGER IF EXISTS trg_sync_name_split ON users;
DROP FUNCTION IF EXISTS sync_name_split();

-- 5. 구 컬럼 제거
ALTER TABLE users DROP COLUMN name;
```

PostgreSQL은 DDL이 트랜잭션 안에서 실행된다. Flyway가 이 파일을 하나의 트랜잭션으로 감싸므로 중간에 실패해도 전체가 롤백된다. 단, `VALIDATE CONSTRAINT`는 각각 별도 트랜잭션에서 실행하는 것이 안전하다 - 검증 도중 실패하면 제약 자체가 롤백되기 때문이다.

### 컬럼 분리 데이터 정합성

Phase 3 진입 전에 분리 결과를 점검한다.

**NULL 잔존 확인:**

```sql
-- 반드시 0건이어야 함
SELECT COUNT(*) FROM users WHERE first_name IS NULL OR last_name IS NULL;
```

**분리 결과 불일치 확인:**

```sql
-- 분리 후 원본과 재조합한 결과가 다른 레코드
SELECT id, name, first_name, last_name
FROM users
WHERE name IS NOT NULL
  AND TRIM(name) != CONCAT(
      first_name,
      CASE WHEN last_name IS NOT NULL THEN ' ' || last_name ELSE '' END
  )
LIMIT 100;
```

레코드가 나오면 이름에 공백이 두 개 이상이거나 앞뒤 공백이 있는 케이스다. `split_part`는 두 번째 공백 이후를 버리기 때문에 "Mary Jane Watson" 같은 이름은 last_name이 "Jane"이 된다. 비즈니스 요구사항에 맞게 split 로직을 조정해야 한다.

**이중 쓰기 도중 누락된 레코드 확인:**

트리거 없이 서비스 코드로 이중 쓰기를 했다면, 이중 쓰기 배포 전에 업데이트된 레코드는 새 컬럼이 NULL일 수 있다. 배치가 `WHERE first_name IS NULL` 조건만 보기 때문에, `first_name`이 채워졌지만 `name`과 불일치하는 레코드가 생길 수 있다:

```sql
-- 이중 쓰기 불일치 감지
SELECT COUNT(*)
FROM users
WHERE first_name IS NOT NULL
  AND name IS NOT NULL
  AND TRIM(name) != CONCAT(
      first_name,
      CASE WHEN last_name IS NOT NULL THEN ' ' || last_name ELSE '' END
  );
```

불일치가 있으면 배치를 다시 돌려서 보정한다:

```sql
UPDATE users
SET
    first_name = split_part(TRIM(name), ' ', 1),
    last_name  = NULLIF(TRIM(split_part(TRIM(name), ' ', 2)), '')
WHERE name IS NOT NULL
  AND TRIM(name) != CONCAT(
      first_name,
      CASE WHEN last_name IS NOT NULL THEN ' ' || last_name ELSE '' END
  );
```

### 컬럼 통합 정합성

`first_name + last_name → full_name`처럼 여러 컬럼을 하나로 합치는 경우도 방향만 반대고 절차는 같다.

**Phase 1 Expand:**

```sql
SET lock_timeout = '2s';
ALTER TABLE users ADD COLUMN full_name VARCHAR(200) NULL;
```

**Phase 2 Migrate — 배치:**

```sql
UPDATE users
SET full_name = TRIM(
    CONCAT(
        COALESCE(first_name, ''),
        CASE WHEN last_name IS NOT NULL AND last_name != '' THEN ' ' || last_name ELSE '' END
    )
)
WHERE full_name IS NULL
  AND id BETWEEN :start_id AND :end_id;
```

**Phase 2 Migrate — 이중 쓰기 트리거:**

```sql
CREATE OR REPLACE FUNCTION sync_full_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_name := TRIM(
        CONCAT(
            COALESCE(NEW.first_name, ''),
            CASE WHEN NEW.last_name IS NOT NULL AND NEW.last_name != ''
                 THEN ' ' || NEW.last_name
                 ELSE ''
            END
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_full_name
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION sync_full_name();
```

**정합성 확인:**

```sql
-- 통합 결과 불일치 확인
SELECT id, first_name, last_name, full_name,
       TRIM(CONCAT(first_name, CASE WHEN last_name IS NOT NULL AND last_name != '' THEN ' ' || last_name ELSE '' END)) AS expected
FROM users
WHERE full_name IS NOT NULL
  AND full_name != TRIM(CONCAT(
      COALESCE(first_name, ''),
      CASE WHEN last_name IS NOT NULL AND last_name != '' THEN ' ' || last_name ELSE '' END
  ))
LIMIT 50;
```

**Phase 3 Contract:**

```sql
DROP TRIGGER IF EXISTS trg_sync_full_name ON users;
DROP FUNCTION IF EXISTS sync_full_name();

ALTER TABLE users ADD CONSTRAINT users_full_name_not_null
    CHECK (full_name IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_full_name_not_null;
ALTER TABLE users ALTER COLUMN full_name SET NOT NULL;
ALTER TABLE users DROP CONSTRAINT users_full_name_not_null;

ALTER TABLE users DROP COLUMN first_name;
ALTER TABLE users DROP COLUMN last_name;
```

### 외래키 추가

외래키 추가도 `NOT VALID`로 락을 분리할 수 있다.

```sql
-- 기존 행 검증 생략. 신규 행만 검사. ACCESS EXCLUSIVE이지만 즉시 완료
ALTER TABLE orders ADD CONSTRAINT fk_orders_users
    FOREIGN KEY (user_id) REFERENCES users(id) NOT VALID;

-- 기존 행 검증. ShareUpdateExclusiveLock으로 DML 허용
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_users;
```

`VALIDATE CONSTRAINT`는 `ShareUpdateExclusiveLock`을 잡는다. 전체 테이블 스캔이 필요하지만 서비스를 멈추지 않는다.

## 락 충돌 처리

### lock_timeout 재시도 패턴

`lock_timeout`이 만료되면 에러가 발생한다:

```
ERROR:  canceling statement due to lock timeout
```

이 에러가 발생하면 대기 중이던 DDL이 취소되고, 뒤에 줄 서 있던 쿼리들이 풀린다. 배포 스크립트에서 재시도 루프를 넣어 처리한다:

```sql
DO $$
DECLARE
    attempt     INTEGER := 0;
    max_retries INTEGER := 10;
BEGIN
    LOOP
        BEGIN
            SET LOCAL lock_timeout = '2s';
            ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) NULL;
            EXIT;
        EXCEPTION WHEN lock_not_available THEN
            attempt := attempt + 1;
            IF attempt >= max_retries THEN
                RAISE EXCEPTION 'lock 획득 실패: % 회 시도 후 포기', max_retries;
            END IF;
            PERFORM pg_sleep(1);
        END;
    END LOOP;
END;
$$;
```

재시도 간격은 트래픽 패턴에 따라 조정한다. 피크 시간대라면 늘리고, 새벽 배포라면 줄여도 된다.

### 블로킹 쿼리 식별과 종료

`lock_timeout` 실패가 반복되면 블로킹 쿼리를 찾아야 한다.

```sql
-- 현재 블로킹 관계 확인
SELECT
    blocking.pid                         AS blocking_pid,
    LEFT(blocking.query, 100)            AS blocking_query,
    now() - blocking.query_start         AS blocking_duration,
    blocking.state                       AS blocking_state,
    blocked.pid                          AS blocked_pid,
    LEFT(blocked.query, 100)             AS blocked_query
FROM pg_stat_activity blocking
JOIN pg_stat_activity blocked
    ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
ORDER BY blocking_duration DESC;
```

블로커를 찾았을 때 종료 방법:

```sql
-- 쿼리만 취소 (연결 유지, 앱이 재시도 가능)
SELECT pg_cancel_backend(:blocking_pid);

-- 연결까지 강제 종료 (롤백 발생, 앱이 connection reset 수신)
SELECT pg_terminate_backend(:blocking_pid);
```

`pg_cancel_backend`는 현재 실행 중인 쿼리에 취소 신호를 보낸다. 쿼리가 응답 가능한 상태면 에러로 종료되고 트랜잭션이 롤백된다. 연결은 살아있으므로 앱이 재시도한다. `pg_terminate_backend`는 연결 자체를 끊는다.

배치 쿼리나 리포트 쿼리가 블로커면 `pg_cancel_backend`를 먼저 시도한다. 쿼리가 이미 롤백 중이거나 cancel에 응답하지 않으면 `pg_terminate_backend`를 쓴다.

### 락 대기열 누적 방지

DDL 실행 전에 장기 실행 쿼리가 없는지 확인한다:

```sql
-- 5분 이상 실행 중인 쿼리 확인
SELECT pid, LEFT(query, 100) AS query, now() - query_start AS duration, state
FROM pg_stat_activity
WHERE state != 'idle'
  AND now() - query_start > interval '5 minutes'
  AND pid != pg_backend_pid()
ORDER BY duration DESC;
```

장기 실행 쿼리가 있으면 DDL 실행을 미룬다. 배치 쿼리라면 재시작 가능한지, 서비스 쿼리라면 롤백해도 괜찮은지 확인 후 종료 여부를 판단한다.

## 롤백 트리거 조건

### Expand 단계

컬럼 추가 후 서비스 배포 전이면 데이터 손실 없이 롤백 가능하다.

```sql
-- Expand 롤백: 언제든 실행 가능
SET lock_timeout = '2s';
ALTER TABLE users DROP COLUMN IF EXISTS first_name;
ALTER TABLE users DROP COLUMN IF EXISTS last_name;
```

서비스 배포가 이미 된 상태에서 롤백하려면 서비스 코드부터 이전 버전으로 내리고 컬럼을 삭제해야 한다.

### Migrate 단계

이중 쓰기 중에 문제가 생기면 서비스를 이전 버전으로 롤백하고 트리거를 제거한다. DB는 Expand 상태 그대로 두면 된다.

**롤백이 필요한 신호 — 이중 쓰기 실패:**

```sql
-- remaining이 줄지 않거나 늘고 있으면 이중 쓰기 실패 의심
SELECT
    COUNT(*) FILTER (WHERE first_name IS NULL)  AS remaining_null,
    COUNT(*) FILTER (WHERE first_name IS NOT NULL) AS filled
FROM users;
```

배치가 실행 중인데 `remaining_null`이 줄지 않거나 늘고 있다면, 트리거가 동작하지 않거나 서비스 일부 인스턴스가 이중 쓰기를 하지 않는 것이다.

**롤백이 필요한 신호 — 불일치 급증:**

```sql
-- 불일치 건수가 늘고 있으면 이중 쓰기 로직에 버그 의심
SELECT COUNT(*)
FROM users
WHERE first_name IS NOT NULL
  AND name IS NOT NULL
  AND TRIM(name) != CONCAT(
      first_name,
      CASE WHEN last_name IS NOT NULL THEN ' ' || last_name ELSE '' END
  );
```

**롤백이 필요한 신호 — 복제 지연 급증:**

```sql
-- 배치 부하로 인한 복제 지연 확인
SELECT client_addr, state, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

`replay_lag`이 수 분 이상 벌어지면 배치 사이즈를 줄이거나 실행을 일시 중단한다. 복제 지연이 계속 커지면 배치를 멈추고 지연이 해소된 후 재시작한다.

**Migrate 롤백 실행:**

```sql
-- 트리거 제거
DROP TRIGGER IF EXISTS trg_sync_name_split ON users;
DROP FUNCTION IF EXISTS sync_name_split();
```

서비스를 이전 버전으로 롤백하면 구 버전이 `name`만 쓰기 때문에 `first_name`/`last_name`은 NULL이 돼도 괜찮다. DB는 Expand 상태로 남겨두고 나중에 Migrate를 재시도할 수 있다.

### Contract 전 게이트 조건

Contract는 되돌릴 수 없다. `DROP COLUMN` 실행 후에는 DB 백업 복원 외에 방법이 없다. 진입 전에 반드시 확인한다:

```sql
-- 1. 새 컬럼에 NULL이 없는지
SELECT COUNT(*) FROM users WHERE first_name IS NULL OR last_name IS NULL;
-- 반드시 0건

-- 2. 분리 결과 불일치 레코드 없는지
SELECT COUNT(*)
FROM users
WHERE name IS NOT NULL
  AND TRIM(name) != CONCAT(
      first_name,
      CASE WHEN last_name IS NOT NULL THEN ' ' || last_name ELSE '' END
  );
-- 반드시 0건

-- 3. 구 컬럼 name을 참조하는 뷰나 함수가 없는지
SELECT viewname, definition
FROM pg_views
WHERE schemaname = 'public'
  AND definition ILIKE '%users.name%';
```

코드 레벨에서도 확인해야 한다. APM 또는 slow query log에서 `SELECT name`, `UPDATE ... SET name` 같은 패턴이 최근 1주일 이상 보이지 않아야 한다. 배포 로그로 구 버전 인스턴스가 없는지도 확인한다.

이 조건이 모두 충족된 후에만 Contract를 실행한다.

## pg_dump/pg_restore로 스키마 버전 관리

Flyway나 Liquibase와 별도로 pg_dump를 활용해 스키마 스냅샷을 관리할 수 있다.

### 스키마만 덤프

```bash
# 데이터 제외, 스키마만 덤프
pg_dump -h localhost -U myuser -d mydb \
    --schema-only \
    --no-owner \
    --no-privileges \
    -f schema_$(date +%Y%m%d_%H%M%S).sql
```

이 스냅샷을 git에 커밋하면 PR 리뷰 시 스키마 변경사항을 diff로 확인할 수 있다. Flyway 파일은 변경사항만 담지만 스키마 스냅샷은 전체 현재 상태를 담기 때문에 검토하기 쉽다.

```bash
# custom 포맷: 압축되고 병렬 복원 가능
pg_dump -h localhost -U myuser -d mydb \
    --schema-only \
    --format=custom \
    -f schema.dump

# 병렬 복원
pg_restore -h localhost -U myuser -d newdb \
    --jobs=4 \
    schema.dump
```

### CI에서 스키마 스냅샷 비교

```yaml
# .github/workflows/schema-check.yml
- name: Apply migrations
  run: ./mvnw flyway:migrate

- name: Dump schema after migration
  run: |
    pg_dump $DATABASE_URL --schema-only --no-owner > schema_after.sql

- name: Compare with committed schema
  run: |
    diff schema_committed.sql schema_after.sql || (echo "Schema drift detected" && exit 1)
```

마이그레이션을 적용한 후 현재 스키마와 커밋된 스냅샷을 비교한다. 누군가 스키마를 직접 수정했거나 마이그레이션 파일이 누락된 경우를 감지한다.

## Flyway와 PostgreSQL 트랜잭션 DDL

MySQL에서는 DDL이 트랜잭션을 암묵적으로 커밋하지만, PostgreSQL은 DDL도 트랜잭션 안에서 실행된다. Flyway가 이 특성과 결합할 때 주의할 상황이 생긴다.

### 기본 동작

Flyway는 기본적으로 각 마이그레이션 파일을 하나의 트랜잭션으로 감싼다. PostgreSQL에서는 `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX` 모두 트랜잭션 안에서 실행된다. 파일 중간에 에러가 나면 전체가 롤백된다.

MySQL에서는 DDL이 암묵적으로 커밋되기 때문에 이런 롤백이 안 된다. MySQL용 마이그레이션을 PostgreSQL에서 쓰면 동작 방식이 달라진다.

**실패 시 차이:**

```
MySQL: V5__add_columns.sql에서 두 번째 ALTER TABLE이 실패
  → 첫 번째 ALTER TABLE은 이미 커밋된 상태
  → flyway_schema_history에 failed로 기록
  → 수동으로 첫 번째 ALTER를 되돌리거나 파일을 수정해야 함

PostgreSQL: V5__add_columns.sql에서 두 번째 ALTER TABLE이 실패
  → 전체 트랜잭션 롤백. DB 상태는 마이그레이션 전과 동일
  → flyway_schema_history에 기록 안 됨
  → 원인 수정 후 동일 파일로 재실행
```

### CONCURRENTLY는 트랜잭션 안에서 실행 불가

`CREATE INDEX CONCURRENTLY`와 `DROP INDEX CONCURRENTLY`는 트랜잭션 블록 안에서 실행하면 에러가 난다.

```
ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block
```

Flyway 마이그레이션 파일에 `CREATE INDEX CONCURRENTLY`를 넣으면 기본 트랜잭션 래핑 때문에 실패한다. 해결 방법은 두 가지다.

**방법 1: `disableTransactionHandling` 주석 (Flyway 10+)**

```sql
-- V6__add_idx_orders_user_id.sql
-- flyway:disableTransactionHandling

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id);
```

**방법 2: Java 마이그레이션으로 분리**

```java
// V6__AddIdxOrdersUserId.java
import org.flywaydb.core.api.migration.BaseJavaMigration;
import org.flywaydb.core.api.migration.Context;

public class V6__AddIdxOrdersUserId extends BaseJavaMigration {

    @Override
    public boolean canExecuteInTransaction() {
        return false;  // 트랜잭션 없이 실행
    }

    @Override
    public void migrate(Context context) throws Exception {
        try (var stmt = context.getConnection().createStatement()) {
            stmt.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders(user_id)"
            );
        }
    }
}
```

`IF NOT EXISTS`를 붙여두면 실패 후 재실행할 때 이미 만들어진 인덱스를 무시한다.

### lock_timeout을 Flyway에 적용

서비스 중 마이그레이션을 실행할 때 Flyway 콜백으로 타임아웃을 설정한다.

```java
@Component
public class FlywayLockTimeoutCallback implements Callback {

    @Override
    public boolean supports(Event event, Context context) {
        return event == Event.BEFORE_EACH_MIGRATE;
    }

    @Override
    public void handle(Event event, Context context) {
        try (var stmt = context.getConnection().createStatement()) {
            stmt.execute("SET lock_timeout = '3s'");
            stmt.execute("SET statement_timeout = '60s'");
        } catch (SQLException e) {
            throw new FlywayException("타임아웃 설정 실패", e);
        }
    }
}
```

`lock_timeout`은 세션 단위라서 트랜잭션이 끝나도 유지된다. 파일별로 설정하는 게 안전하다. `statement_timeout`은 오래 걸리는 마이그레이션이 서버를 점유하는 것을 막는다.

## 운영 시 현재 락 상태 확인

서비스 지연이 발생할 때 먼저 확인하는 쿼리다.

```sql
-- 락 대기 현황
SELECT
    blocked.pid AS blocked_pid,
    blocked.query AS blocked_query,
    blocking.pid AS blocking_pid,
    blocking.query AS blocking_query,
    now() - blocked.query_start AS blocked_duration
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
    ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE cardinality(pg_blocking_pids(blocked.pid)) > 0;
```

```sql
-- DDL 락 감지 (ACCESS EXCLUSIVE 대기)
SELECT
    pid,
    query,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS duration
FROM pg_stat_activity
WHERE wait_event_type = 'Lock'
ORDER BY duration DESC;
```

`ACCESS EXCLUSIVE`를 기다리는 쿼리가 보이면, 그 앞에 있는 장기 실행 쿼리를 찾아서 종료할지 판단한다.

```sql
-- 장기 실행 쿼리 종료 (5분 이상)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 minutes'
  AND pid != pg_backend_pid();
```

`pg_terminate_backend`는 쿼리를 강제로 종료한다. 실행 중인 트랜잭션이 롤백되므로 신중하게 써야 한다.
