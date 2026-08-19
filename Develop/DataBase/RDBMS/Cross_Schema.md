---
title: Cross-Schema 쿼리
tags: [database, postgresql, mysql, microservices]
updated: 2026-07-30
---

# Cross-Schema 쿼리

스키마(Schema)는 DB 오브젝트를 묶는 네임스페이스다. 하나의 DB 인스턴스 안에 여러 스키마를 두고 서로 다른 스키마의 테이블을 같은 쿼리에서 참조하는 게 cross-schema 쿼리다.

멀티테넌트 구조를 스키마로 구현하거나, 레거시 시스템을 도메인별로 스키마를 분리하면서 기존 조인을 유지해야 하거나, MSA 전환 전 DB를 먼저 논리적으로 분리할 때 이 방식을 쓴다. 단순해 보이지만 search_path 함정, FK 제약 불가, 테넌트 간 데이터 유출 위험이 있다.

---

## schema.table 직접 참조

PostgreSQL과 MySQL 모두 `스키마명.테이블명` 형태로 다른 스키마의 테이블을 직접 참조할 수 있다.

```sql
-- PostgreSQL: 다른 스키마 테이블 참조
SELECT
    o.id,
    o.amount,
    u.email
FROM billing.orders o
JOIN public.users u ON o.user_id = u.id
WHERE o.created_at >= '2024-01-01';

-- 스키마를 명시하지 않으면 search_path에 따라 해석됨
SELECT * FROM orders;          -- 어떤 스키마? search_path 의존
SELECT * FROM billing.orders;  -- 명확
```

MySQL에서는 스키마와 데이터베이스가 사실상 같은 개념이다. `database명.테이블명`으로 접근한다.

```sql
-- MySQL: 다른 database(=schema) 참조
SELECT
    o.id,
    u.email
FROM billing.orders o
JOIN app_db.users u ON o.user_id = u.id;

-- 현재 USE로 선택된 db가 아닌 곳의 테이블도 동일 문법
USE billing;
SELECT * FROM app_db.users;  -- 다른 db 테이블 참조
```

권한은 별도로 설정해야 한다. PostgreSQL에서는 스키마 USAGE 권한과 테이블 SELECT 권한이 따로 존재한다.

```sql
-- PostgreSQL 권한 설정
GRANT USAGE ON SCHEMA billing TO app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA billing TO app_user;

-- MySQL 권한 설정
GRANT SELECT ON billing.* TO 'app_user'@'%';
```

---

## PostgreSQL search_path 동작과 함정

`search_path`는 스키마명을 생략했을 때 어떤 스키마에서 오브젝트를 찾을지 순서를 정하는 설정이다. 기본값은 `"$user", public`이다. 현재 접속한 사용자명과 동일한 스키마가 있으면 그걸 먼저 찾고, 없으면 public을 본다.

```sql
-- 현재 search_path 확인
SHOW search_path;
-- "$user", public

-- 세션 단위 변경
SET search_path TO billing, public;

-- 이제 스키마 없이 쿼리하면 billing 먼저 탐색
SELECT * FROM orders;  -- billing.orders 참조
```

함정이 몇 가지 있다.

**같은 이름의 테이블이 여러 스키마에 있는 경우.** search_path 앞에 있는 스키마가 이긴다. `billing`과 `public` 모두 `orders` 테이블이 있고 search_path가 `billing, public`이면 항상 `billing.orders`를 본다. 쿼리에 스키마명이 없으면 어느 테이블을 보는지 실행 환경에 따라 달라진다.

```sql
-- 위험한 패턴: 스키마명 없이 쿼리
SELECT * FROM orders;  -- search_path에 따라 다른 테이블을 봄

-- 안전한 패턴: 항상 명시
SELECT * FROM billing.orders;
```

**connection pool 환경.** SET search_path는 세션 단위 설정이다. PgBouncer 같은 풀러를 transaction mode로 쓰면 세션이 재사용되면서 이전 세션의 search_path가 남을 수 있다. 애플리케이션 코드에서 SET search_path를 쿼리 앞에 붙이는 패턴은 transaction mode에서 의도대로 동작하지 않을 수 있다.

해결 방법은 두 가지다. 하나는 search_path를 role 단위로 고정하는 것이고, 다른 하나는 쿼리에 항상 스키마명을 명시하는 것이다.

```sql
-- role 단위로 search_path 고정 (세션 풀링 영향 없음)
ALTER ROLE app_user SET search_path TO billing, public;

-- 또는 DB 단위로 고정
ALTER DATABASE mydb SET search_path TO billing, public;
```

**함수 내부 search_path.** 함수는 생성 시점의 search_path가 아니라 실행 시점의 search_path를 쓴다. 함수 안에서 스키마명 없이 테이블을 참조하면 호출하는 컨텍스트의 search_path에 따라 결과가 달라진다. 함수 생성 시 `SET search_path`를 명시적으로 고정하는 게 낫다.

```sql
CREATE OR REPLACE FUNCTION get_user_orders(p_user_id INT)
RETURNS TABLE(order_id INT, amount DECIMAL)
LANGUAGE plpgsql
SET search_path = billing, public  -- 함수 내부 search_path 고정
AS $$
BEGIN
    RETURN QUERY
    SELECT o.id, o.amount
    FROM orders o  -- billing.orders를 봄
    WHERE o.user_id = p_user_id;
END;
$$;
```

---

## schema-per-tenant vs 공유 스키마

멀티테넌트 DB 설계에서 tenant별로 스키마를 분리하는 방식(schema-per-tenant)과 단일 스키마에 tenant_id 컬럼으로 구분하는 방식(공유 스키마)을 비교한다.

### schema-per-tenant

tenant마다 독립된 스키마를 가진다.

```
app_db
├── tenant_001.orders
├── tenant_001.users
├── tenant_002.orders
├── tenant_002.users
└── shared.plans  -- 공통 데이터
```

```sql
-- tenant_001의 데이터 조회
SELECT * FROM tenant_001.orders;

-- 공통 스키마와 조인
SELECT o.*, p.name as plan_name
FROM tenant_001.orders o
JOIN shared.plans p ON o.plan_id = p.id;
```

장점은 tenant 간 데이터 격리가 DB 레벨에서 보장된다는 것이다. 쿼리에 WHERE tenant_id = ? 조건을 빠뜨려도 다른 tenant 데이터가 섞이지 않는다. tenant 단위 backup/restore, 마이그레이션이 상대적으로 간단하다.

단점은 tenant 수가 늘어날수록 스키마 관리 부담이 커진다는 것이다. 스키마 100개에 테이블 50개씩이면 DDL 변경 한 번에 5,000개 테이블을 ALTER해야 한다. PostgreSQL의 `pg_stat_activity`, `pg_locks` 같은 시스템 뷰가 무거워지고, `information_schema` 조회가 느려진다.

신규 tenant 생성 시 스키마와 테이블을 프로비저닝하는 코드가 필요하다.

```sql
-- 신규 tenant 프로비저닝 예시
CREATE SCHEMA tenant_003;

-- 템플릿 스키마에서 구조 복사 (PostgreSQL)
-- pg_dump/pg_restore나 스크립트로 DDL만 복사
CREATE TABLE tenant_003.users (LIKE template.users INCLUDING ALL);
CREATE TABLE tenant_003.orders (LIKE template.orders INCLUDING ALL);
```

### 공유 스키마

모든 tenant가 같은 테이블을 쓰고 tenant_id 컬럼으로 구분한다.

```sql
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL
);

CREATE INDEX idx_orders_tenant ON orders (tenant_id, created_at DESC);
```

모든 쿼리에 `WHERE tenant_id = ?`가 들어가야 한다. 이 조건을 빠뜨리면 전체 tenant 데이터가 노출된다. Row Level Security(RLS)로 이를 강제할 수 있다.

```sql
-- PostgreSQL RLS로 tenant 격리 강제
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant_id')::INT);

-- 애플리케이션에서 쿼리 전에 설정
SET LOCAL app.current_tenant_id = '42';
SELECT * FROM orders;  -- tenant_id = 42인 row만 반환
```

tenant 수가 많아져도 스키마 관리 부담이 없다. 대신 인덱스 설계를 잘못하면 특정 tenant의 대용량 데이터가 다른 tenant 쿼리 성능에 영향을 준다(noisy neighbor).

실무에서는 두 방식을 혼합하기도 한다. 대형 tenant는 전용 스키마(또는 전용 DB 인스턴스), 소형 tenant는 공유 스키마로 운영하는 방식이다.

---

## Foreign Data Wrapper로 원격 스키마 접근

FDW(Foreign Data Wrapper)는 외부 데이터 소스를 로컬 테이블처럼 쿼리하는 PostgreSQL 기능이다. 다른 PostgreSQL 인스턴스, MySQL, CSV 파일, S3 등을 대상으로 쓸 수 있다. `postgres_fdw`가 가장 많이 쓰인다.

```sql
-- 원격 서버 등록
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER remote_billing
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host '10.0.1.5', port '5432', dbname 'billing_db');

-- 원격 서버 접속 자격증명
CREATE USER MAPPING FOR app_user
    SERVER remote_billing
    OPTIONS (user 'billing_reader', password 'secret');

-- 원격 테이블을 로컬처럼 import
IMPORT FOREIGN SCHEMA billing
    FROM SERVER remote_billing
    INTO local_billing;

-- 이제 로컬 쿼리처럼 사용 가능
SELECT
    o.id,
    o.amount,
    u.email
FROM local_billing.orders o
JOIN public.users u ON o.user_id = u.id;
```

FDW는 편리하지만 주의해야 할 점이 있다.

**조인 푸시다운.** 로컬 테이블과 원격 테이블을 조인하면 기본적으로 원격 테이블 전체를 로컬로 가져온 후 조인한다. `enable_pushdown` 옵션이 켜져 있으면 WHERE 조건 일부를 원격으로 밀어내지만, 완벽하지 않다. 원격 테이블이 대용량이면 네트워크 전송 비용이 크다.

```sql
-- EXPLAIN으로 푸시다운 여부 확인
EXPLAIN SELECT o.id FROM local_billing.orders o WHERE o.amount > 1000;
-- Foreign Scan on orders가 나오면 원격에서 필터링
-- Seq Scan 후 Filter가 나오면 로컬에서 필터링 (비효율)
```

**네트워크 장애 전파.** 원격 서버가 다운되면 FDW를 참조하는 모든 쿼리가 실패한다. 로컬 테이블 쿼리와 같은 트랜잭션에 FDW 쿼리가 섞여 있으면 원격 장애가 로컬 트랜잭션도 롤백시킨다. FDW를 쓰는 쿼리는 가능하면 별도 트랜잭션으로 분리하고, 타임아웃을 짧게 설정한다.

```sql
-- FDW 서버 타임아웃 설정
ALTER SERVER remote_billing
    OPTIONS (connect_timeout '3', query_timeout '10000');
```

**트랜잭션 일관성.** FDW 쿼리는 2PC(two-phase commit)로 원자성을 보장할 수 있지만 기본적으로 비활성화되어 있다. 로컬과 원격 데이터를 동시에 수정하는 작업에서 원자성이 필요하면 직접 처리해야 한다.

---

## 크로스 스키마 FK 제약 없는 설계에서 정합성 관리

PostgreSQL 에서는 같은 DB 안의 서로 다른 스키마 간 FK 를 걸 수 있다. MySQL 도 같은 인스턴스 안이라면 다른 database(MySQL 에서는 이게 곧 스키마다)의 테이블을 참조하는 FK 를 걸 수 있다. `information_schema.KEY_COLUMN_USAGE` 에 `REFERENCED_TABLE_SCHEMA` 가 `TABLE_SCHEMA` 와 별개 컬럼으로 있고 그 설명이 '참조되는 데이터베이스 이름' 인 것도 그래서다. 넘지 못하는 건 스키마 경계가 아니라 인스턴스 경계다. FDW 로 연결한 원격 스키마나 물리적으로 분리된 다른 서버의 테이블은 FK 대상이 되지 못한다.

```sql
-- PostgreSQL: 크로스 스키마 FK 가능
ALTER TABLE billing.orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES public.users(id);

-- MySQL: 같은 인스턴스라면 cross-database FK 가능
ALTER TABLE billing.orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES app.users(id);

-- 인스턴스가 다르면(FDW·원격 서버) FK 자체가 성립하지 않는다
```

DB 를 물리적으로 쪼갰다면 FK 를 못 쓰니 정합성을 다른 방법으로 유지해야 한다.

**애플리케이션 레이어 검증.** INSERT/UPDATE 전에 참조 대상 존재 여부를 확인한다. 단, 확인과 INSERT 사이에 참조 대상이 삭제되는 TOCTOU 문제가 있다. 고빈도 환경에서는 고아 데이터가 생길 수 있다.

```python
# 애플리케이션 검증 예시
def create_order(user_id: int, amount: Decimal) -> Order:
    user = db.query("SELECT id FROM users WHERE id = %s", (user_id,))
    if not user:
        raise ValueError(f"User {user_id} not found")
    # TOCTOU: 이 사이에 user가 삭제될 수 있음
    return db.execute("INSERT INTO billing.orders (user_id, amount) VALUES (%s, %s)", ...)
```

**트리거로 강제.** 참조 무결성 검사를 트리거로 구현한다. 애플리케이션 레이어보다 DB에 가깝지만, 크로스 스키마 참조는 외부 DB에서는 어차피 불가능하고 성능 비용이 있다.

```sql
-- PostgreSQL 트리거로 크로스 스키마 검증
CREATE OR REPLACE FUNCTION check_user_exists()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.users WHERE id = NEW.user_id) THEN
        RAISE EXCEPTION 'User % does not exist', NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_billing_orders_user_check
BEFORE INSERT OR UPDATE ON billing.orders
FOR EACH ROW EXECUTE FUNCTION check_user_exists();
```

**이벤트 기반 정합성 검증.** 정합성 검사를 동기가 아닌 비동기로 처리한다. INSERT는 허용하되 주기적으로 고아 데이터를 찾아서 처리한다. 일시적인 불일치를 허용하는 eventual consistency 모델이다.

```sql
-- 고아 데이터 탐지 쿼리
SELECT o.id, o.user_id
FROM billing.orders o
LEFT JOIN public.users u ON o.user_id = u.id
WHERE u.id IS NULL;

-- 주기적 실행으로 고아 데이터 모니터링
```

실무에서 세 방법을 혼합해서 쓰는 경우가 많다. 중요한 참조는 트리거나 애플리케이션 검증으로 즉시 막고, 나머지는 주기적 스캔으로 사후 처리한다.

---

## 마이크로서비스 환경에서 스키마 경계와 조인 문제

MSA에서는 서비스별로 DB를 분리하는 게 원칙이다. 서로 다른 서비스의 DB를 직접 조인하는 건 서비스 간 결합도를 높이기 때문에 지양한다. 하지만 현실에서는 완전 분리가 어려운 경우가 있다.

### 문제 상황

`orders` 서비스와 `users` 서비스가 각각 독립된 DB를 갖는다. 주문 목록 조회 시 사용자 이름과 이메일을 함께 보여줘야 한다. 단일 DB라면 JOIN 한 줄이지만, 분리된 DB에서는 조인이 불가능하다.

### 우회 방법 1: API 조합

각 서비스 API를 호출해서 애플리케이션 레이어에서 데이터를 합친다.

```python
# BFF(Backend for Frontend) 또는 API Gateway에서 조합
async def get_orders_with_users(user_ids: list[int]) -> list[dict]:
    orders = await order_service.get_orders(user_ids)
    
    unique_user_ids = {o["user_id"] for o in orders}
    users = await user_service.get_users(list(unique_user_ids))  # batch 조회
    user_map = {u["id"]: u for u in users}
    
    return [
        {**order, "user": user_map.get(order["user_id"])}
        for order in orders
    ]
```

N+1 문제를 피하려면 users를 batch로 조회해야 한다. user_ids를 한 번에 넘겨서 IN 쿼리로 처리한다.

### 우회 방법 2: 데이터 복제 (읽기 전용 사본)

읽기 전용 목적으로 필요한 컬럼만 로컬 DB에 복제한다. CDC(Change Data Capture)나 이벤트 스트림으로 동기화한다.

```sql
-- orders DB에 users 읽기 전용 사본 유지
CREATE TABLE user_snapshots (
    user_id BIGINT PRIMARY KEY,
    email VARCHAR(255),
    display_name VARCHAR(100),
    synced_at TIMESTAMP DEFAULT NOW()
);

-- orders와 로컬에서 조인 가능
SELECT o.id, o.amount, us.email, us.display_name
FROM orders o
JOIN user_snapshots us ON o.user_id = us.user_id;
```

복제 지연이 발생하면 최신 데이터가 아닐 수 있다. 이름/이메일처럼 변경이 드문 데이터는 허용 가능한 수준이다. 결제 금액이나 재고 수량 같은 실시간 정확도가 필요한 데이터는 이 방식을 쓰면 안 된다.

### 우회 방법 3: CQRS + 읽기 모델

쓰기 모델은 서비스별로 완전 분리하고, 읽기용으로 별도 저장소를 둔다. 여러 서비스의 데이터를 비정규화해서 하나의 읽기 모델에 저장한다.

```sql
-- 읽기 전용 집계 DB (Elasticsearch나 별도 RDB)
CREATE TABLE order_view (
    order_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    user_email VARCHAR(255),
    user_name VARCHAR(100),
    amount DECIMAL(10, 2),
    status VARCHAR(50),
    created_at TIMESTAMP
);
-- 이벤트 소비해서 비동기 업데이트
```

조인 없이 단일 테이블에서 읽으므로 읽기 성능이 가장 좋다. 대신 쓰기 이벤트 처리 로직이 복잡하고, 데이터 불일치 시 재처리 메커니즘이 필요하다.

### 스키마 경계를 언제 분리할지

서비스 경계와 DB 경계가 항상 일치해야 하는 건 아니다. 서비스가 항상 같이 배포되고, 같은 팀이 관리하고, 트랜잭션 원자성이 필요한 경우라면 같은 DB에 스키마만 분리하는 게 현실적이다. 완전히 독립적인 팀이 운영하고 장애 격리가 중요한 경우에만 DB 레벨 분리를 고려한다.

```sql
-- 같은 DB, 스키마만 분리 (점진적 MSA 전환 중)
-- FK도 걸 수 있고, 조인도 가능, 트랜잭션도 하나
-- 나중에 DB를 분리할 때 cross-schema 접근을 API 호출로 교체

SELECT o.id, u.email
FROM orders.orders o
JOIN users.accounts u ON o.user_id = u.id;
```

DB를 분리하기 전에 스키마를 먼저 분리하는 것은 나중의 DB 분리를 위한 준비 작업이다. 이 시점에 cross-schema 조인이 얼마나 많이 발생하는지 파악해두면 DB 분리 비용을 미리 가늠할 수 있다.
