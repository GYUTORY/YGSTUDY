---
title: Shared Table
tags: [database, multi-tenant, postgresql, mysql, shared-table, tenant-id, rls, row-level-security, index, partitioning, migration, repository-pattern, contextvars]
updated: 2026-08-04
---

# Shared Table

하나의 테이블에 모든 테넌트 데이터를 넣고 `tenant_id` 컬럼으로 구분하는 방식이다. 세 가지 멀티테넌시 패턴(Shared Database / Shared Schema / Separate Database) 중 가장 단순하고 DB 자원을 가장 적게 쓴다.

스키마 분리(Schema-Per-Tenant)와 비교하면 테이블 수가 훨씬 적어서 DDL 관리가 단순하고 시스템 카탈로그 비대화 문제가 없다. 반면 테넌트 격리는 전적으로 애플리케이션 레이어에 의존한다. `WHERE tenant_id = ?` 조건 하나를 빠뜨리면 모든 테넌트 데이터가 노출된다.

---

## 기본 설계

### tenant_id 컬럼 위치

`tenant_id`는 모든 테이블에 있어야 한다. 예외를 두면 cross-tenant 쿼리가 불가능해지거나 조인할 때 테넌트 경계가 무너진다.

```sql
CREATE TABLE orders (
    tenant_id   UUID           NOT NULL,
    id          BIGSERIAL      NOT NULL,
    user_id     BIGINT         NOT NULL,
    amount      DECIMAL(12, 2) NOT NULL,
    status      VARCHAR(50)    NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE users (
    tenant_id   UUID         NOT NULL,
    id          BIGSERIAL    NOT NULL,
    email       VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, email)
);
```

PK를 `(tenant_id, id)` 복합키로 잡으면 동일한 `id` 값이 여러 테넌트에 존재해도 충돌이 없다. `id`만 PK로 쓸 경우 `BIGSERIAL`이 전역 시퀀스를 공유하므로 충돌 자체는 없지만, 나중에 파티셔닝을 도입하면 어차피 PK에 `tenant_id`를 포함해야 한다.

FK 참조는 같은 테넌트 내로 제한한다. `orders.user_id`가 `users.id`를 참조할 때 다른 테넌트의 user를 가리키지 않도록 FK를 `(tenant_id, user_id)` → `(tenant_id, id)` 형태로 잡는다.

```sql
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (tenant_id, user_id) REFERENCES users(tenant_id, id);
```

### tenant_id 타입 선택

UUID를 많이 쓰지만 BIGINT도 괜찮다. UUID는 외부 노출 식별자와 내부 DB 식별자를 일치시킬 수 있어서 사용이 단순하다. BIGINT는 저장 공간이 8바이트로 UUID(16바이트)의 절반이다. `tenant_id`가 선두 컬럼으로 모든 인덱스에 포함되므로 테이블이 클수록 인덱스 크기 차이가 난다. 내부 처리에 BIGINT를 쓰고 외부 식별자는 별도 UUID 컬럼을 두는 팀도 있다.

---

## 인덱스 설계

### tenant_id 선두 원칙

모든 인덱스의 첫 번째 컬럼은 `tenant_id`여야 한다. 모든 쿼리 조건에 `tenant_id`가 포함되기 때문이다.

```sql
-- 잘못된 설계
CREATE INDEX idx_orders_status ON orders (status, created_at DESC);

-- 올바른 설계
CREATE INDEX idx_orders_status ON orders (tenant_id, status, created_at DESC);
```

`status`만으로 인덱스를 만들면 쿼리 플래너가 해당 인덱스를 선택하더라도, tenant_id 조건이 인덱스 스캔 후 별도 필터로 처리된다. 테넌트 수가 많고 특정 status 값이 전체 데이터에 넓게 분포한다면 불필요한 행을 대량으로 읽게 된다.

### 쿼리 패턴별 인덱스

```sql
-- 이메일 조회 (로그인, 중복 체크)
CREATE UNIQUE INDEX uidx_users_email ON users (tenant_id, email);

-- 주문 상태별 목록 (관리자 화면)
CREATE INDEX idx_orders_status_created ON orders (tenant_id, status, created_at DESC);

-- 사용자별 주문 목록
CREATE INDEX idx_orders_user_created ON orders (tenant_id, user_id, created_at DESC);

-- 기간 조회 (정산, 리포트)
CREATE INDEX idx_orders_created ON orders (tenant_id, created_at DESC);
```

`created_at DESC`를 인덱스에 포함하는 이유는 목록 쿼리 대부분이 최신순 정렬을 요구하기 때문이다. PostgreSQL에서 내림차순을 인덱스에 명시하면 `ORDER BY created_at DESC` 쿼리에서 별도 정렬 없이 인덱스 스캔으로 처리된다.

### 클러스터링 인덱스

MySQL InnoDB에서는 PK가 클러스터링 인덱스다. `(tenant_id, id)`를 PK로 쓰면 같은 테넌트의 데이터가 물리적으로 인접하게 저장된다. 테넌트 범위 스캔이 연속된 페이지를 읽으므로 I/O가 줄어든다. PostgreSQL에서도 `CLUSTER` 명령으로 클러스터링할 수 있지만, 이후 INSERT/UPDATE로 순서가 흐트러지면 주기적으로 재클러스터링해야 한다.

---

## Hot Tenant 문제

### 데이터 쏠림이 발생하는 상황

테넌트 규모가 균일하지 않을 때 발생한다. 전체 데이터의 70%가 3개 테넌트에 집중되는 상황은 B2B SaaS에서 흔하다. 이 테넌트들의 쿼리가 특정 인덱스 페이지를 반복적으로 읽으면서 버퍼 풀을 독점한다. 다른 테넌트 쿼리가 느려지는 건 물론이고, hot tenant 자체도 전체 테이블 통계를 기반으로 한 쿼리 플랜이 자신의 데이터 분포에 맞지 않을 수 있다.

```sql
-- 테넌트별 데이터 분포 확인
SELECT tenant_id,
       COUNT(*) AS row_count,
       pg_size_pretty(SUM(pg_column_size(orders.*))) AS estimated_size
FROM orders
GROUP BY tenant_id
ORDER BY row_count DESC
LIMIT 20;
```

### 파티셔닝으로 대응

PostgreSQL 선언적 파티셔닝을 `tenant_id` 기준으로 적용할 수 있다. hot tenant를 별도 파티션으로 분리하면 해당 파티션만 독립적으로 인덱스를 갖고 vacuum이 실행된다.

```sql
CREATE TABLE orders (
    tenant_id   UUID           NOT NULL,
    id          BIGSERIAL      NOT NULL,
    user_id     BIGINT         NOT NULL,
    amount      DECIMAL(12, 2) NOT NULL,
    status      VARCHAR(50)    NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
) PARTITION BY LIST (tenant_id);

-- 대형 테넌트는 전용 파티션
CREATE TABLE orders_tenant_abc PARTITION OF orders
    FOR VALUES IN ('11111111-1111-1111-1111-111111111111');

CREATE TABLE orders_tenant_def PARTITION OF orders
    FOR VALUES IN ('22222222-2222-2222-2222-222222222222');

-- 나머지 테넌트는 기본 파티션
CREATE TABLE orders_default PARTITION OF orders DEFAULT;
```

`WHERE tenant_id = ?` 쿼리에서 파티션 프루닝이 동작한다. 해당 파티션만 스캔하므로 다른 테넌트 데이터를 읽지 않는다. hot tenant 파티션에는 vacuum 파라미터를 개별 설정할 수 있다.

```sql
-- hot tenant 파티션에 더 적극적인 vacuum 설정
ALTER TABLE orders_tenant_abc SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);
```

기본 파티션에 테넌트가 계속 추가되다가 나중에 특정 테넌트가 커졌을 때 별도 파티션으로 분리하는 작업은 데이터 이동을 수반한다. 초기에 파티션 수용 계획을 세워두는 게 낫다.

---

## 애플리케이션 레이어 강제 필터

### 문제

`WHERE tenant_id = ?` 조건을 빠뜨리면 다른 테넌트 전체 데이터가 노출된다. ORM을 쓰면 쿼리 조건을 코드로 다루므로 조건 누락이 컴파일 타임에 잡히지 않는다. 런타임에서도 잡히지 않고 그냥 실행된다.

### ContextVar 패턴 (Python)

요청 처리 시작 시점에 현재 테넌트를 컨텍스트에 설정하고, DB 쿼리에서 이를 읽어 `tenant_id` 조건을 자동으로 붙인다.

```python
from contextvars import ContextVar
from typing import Optional
import uuid

_current_tenant: ContextVar[Optional[uuid.UUID]] = ContextVar(
    'current_tenant', default=None
)

def set_tenant(tenant_id: uuid.UUID) -> None:
    _current_tenant.set(tenant_id)

def get_tenant() -> uuid.UUID:
    tenant_id = _current_tenant.get()
    if tenant_id is None:
        raise RuntimeError("Tenant context not set")
    return tenant_id
```

FastAPI 미들웨어에서 JWT나 헤더에서 tenant_id를 꺼내 컨텍스트에 설정한다.

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = self._extract_tenant(request)
        set_tenant(tenant_id)
        return await call_next(request)

    def _extract_tenant(self, request: Request) -> uuid.UUID:
        token_data = verify_jwt(request.headers.get("Authorization"))
        return uuid.UUID(token_data["tenant_id"])
```

`ContextVar`는 asyncio 태스크 단위로 격리된다. 동시 요청이 들어와도 서로 다른 태스크가 서로 다른 컨텍스트를 갖는다. 스레드 풀에서 동기 코드를 실행할 때는 `contextvars.copy_context().run(fn)`으로 컨텍스트를 전파해야 한다.

### Repository 패턴

Repository 클래스가 `tenant_id` 조건을 자동으로 붙이면 서비스 레이어에서 tenant_id를 직접 다루지 않아도 된다.

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

class OrderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _tenant_filter(self, query):
        return query.where(Order.tenant_id == get_tenant())

    async def find_by_id(self, order_id: int) -> Optional[Order]:
        stmt = self._tenant_filter(
            select(Order).where(Order.id == order_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_status(self, status: str) -> list[Order]:
        stmt = self._tenant_filter(
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
```

서비스 레이어에서 tenant_id를 빠뜨려도 Repository가 강제로 붙인다. Repository를 우회해서 직접 세션을 쓰는 코드가 있으면 의미가 없다. 코드 리뷰에서 세션 직접 접근을 막는 컨벤션이 함께 있어야 한다.

### 관리자 쿼리 처리

테넌트 컨텍스트 없이 전체 데이터를 조회해야 하는 관리자 기능은 별도 Repository로 분리한다.

```python
class AdminOrderRepository:
    """테넌트 필터 없이 전체 조회. 관리자 API에서만 사용한다."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_all_tenants_summary(self) -> list[TenantSummary]:
        stmt = (
            select(
                Order.tenant_id,
                func.count().label('order_count'),
                func.sum(Order.amount).label('total_amount')
            )
            .group_by(Order.tenant_id)
        )
        result = await self._session.execute(stmt)
        return result.all()
```

`AdminOrderRepository`와 `OrderRepository`를 타입으로 구분하면 코드 리뷰에서 의도치 않은 전체 조회가 눈에 띈다.

---

## RLS (Row Level Security)

### 기본 설정

PostgreSQL의 RLS는 테이블에 정책을 붙여 DB 레벨에서 행 접근을 제어한다. 애플리케이션이 `tenant_id` 조건을 빠뜨려도 DB가 차단한다.

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

커넥션을 얻은 후 쿼리 실행 전에 세션 변수를 설정한다.

```python
async def set_tenant_context(conn, tenant_id: uuid.UUID) -> None:
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, TRUE)",
        str(tenant_id)
    )
```

`set_config`의 세 번째 인자 `TRUE`는 트랜잭션 범위로 설정을 한정한다. 트랜잭션이 끝나면 설정이 초기화된다. 커넥션 풀에서 다음 트랜잭션이 다른 테넌트 설정을 이어받는 문제를 막는다. `FALSE`로 두면 세션 전체에 설정이 유지되어 커넥션 풀 환경에서 위험하다.

### superuser와 BYPASSRLS

`superuser`와 `BYPASSRLS` 권한을 가진 역할은 RLS를 통과한다. 애플리케이션 DB 접속에 superuser를 쓰면 RLS 설정이 아무 의미 없다.

```sql
-- 애플리케이션 전용 역할 생성 (superuser 아님)
CREATE ROLE app_user LOGIN PASSWORD 'secret';
GRANT SELECT, INSERT, UPDATE, DELETE ON orders TO app_user;

-- 마이그레이션·관리 작업은 별도 역할
CREATE ROLE admin_user LOGIN PASSWORD 'admin_secret' BYPASSRLS;
```

개발 편의를 위해 superuser로 접속하다가 RLS를 설정해도 적용이 안 된다고 혼란스러워하는 경우가 있다. 애플리케이션 접속 역할은 처음부터 superuser가 아닌 전용 역할로 분리한다.

### 성능 영향

RLS 정책은 모든 쿼리에 조건을 붙인다. `tenant_id` 선두 인덱스가 있는 상태에서 RLS가 `tenant_id = ?` 조건을 추가하면 인덱스 스캔이 동일하게 동작하므로 추가 비용이 거의 없다.

문제가 생기는 경우는 정책이 복잡하거나 함수 호출이나 서브쿼리를 포함할 때다.

```sql
-- 느릴 수 있는 정책 (서브쿼리 포함)
CREATE POLICY tenant_plan_check ON orders
    USING (
        tenant_id = current_setting('app.current_tenant_id')::UUID
        AND EXISTS (
            SELECT 1 FROM tenant_plans
            WHERE tenant_plans.tenant_id = orders.tenant_id
              AND tenant_plans.plan = 'enterprise'
        )
    );
```

쿼리마다 `tenant_plans` 테이블을 확인하므로 성능이 나빠진다. 이런 로직은 애플리케이션 레이어에서 처리하고 RLS는 단순한 tenant_id 매칭만 담당하게 한다.

```sql
SET app.current_tenant_id = '11111111-1111-1111-1111-111111111111';

EXPLAIN ANALYZE
SELECT * FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```

RLS가 적용된 쿼리는 실행 계획에 `Filter: (tenant_id = ...)` 또는 `Recheck Cond`로 나타난다. tenant_id 인덱스를 제대로 쓰고 있는지 실행 계획으로 확인한다.

### PgBouncer와 RLS

`set_config(..., TRUE)` (트랜잭션 범위)를 쓰면 PgBouncer transaction mode에서 안전하다. 트랜잭션이 끝날 때 설정이 초기화되므로 다음 트랜잭션에서 커넥션을 재사용해도 이전 테넌트 설정이 남지 않는다.

하나의 요청이 여러 트랜잭션을 사용한다면 각 트랜잭션 시작 시 `set_config`를 다시 호출해야 한다.

---

## 기존 테이블에 tenant_id 추가하기

### 마이그레이션 순서

단일 테넌트로 운영하다가 멀티테넌트로 전환할 때 가장 흔한 작업이다. 운영 중인 테이블에 `tenant_id` 컬럼을 추가하고 기존 데이터에 값을 채워야 한다.

대용량 테이블에서 `ALTER TABLE ADD COLUMN NOT NULL DEFAULT`는 PostgreSQL 11 이후 테이블 재작성 없이 동작하지만, 인덱스 생성은 여전히 시간이 걸린다.

```sql
-- 1단계: nullable로 컬럼 추가 (빠름)
ALTER TABLE orders ADD COLUMN tenant_id UUID;

-- 2단계: 기존 데이터에 값 채우기
-- 기존 데이터 전체가 단일 테넌트에 속한다면
UPDATE orders
SET tenant_id = '11111111-1111-1111-1111-111111111111'
WHERE tenant_id IS NULL;

-- 3단계: NOT VALID CHECK로 새 행만 검증 (기존 행 스캔 안 함)
ALTER TABLE orders
ADD CONSTRAINT orders_tenant_id_not_null
CHECK (tenant_id IS NOT NULL) NOT VALID;

-- 4단계: 기존 데이터 검증 (AccessShareLock — DML 차단 없음)
ALTER TABLE orders VALIDATE CONSTRAINT orders_tenant_id_not_null;

-- 5단계: 인덱스 추가 (CONCURRENTLY로 락 없이)
CREATE INDEX CONCURRENTLY idx_orders_tenant_created
ON orders (tenant_id, created_at DESC);

-- 6단계: NOT NULL 설정 (CHECK로 이미 검증됐으므로 빠름)
ALTER TABLE orders ALTER COLUMN tenant_id SET NOT NULL;

-- 7단계: CHECK 제약 제거 (선택)
ALTER TABLE orders DROP CONSTRAINT orders_tenant_id_not_null;
```

`NOT VALID` CHECK 제약은 기존 데이터를 검증하지 않고 추가된다. `VALIDATE CONSTRAINT`는 검증만 하고 `AccessShareLock`을 잡아 다른 DML을 막지 않는다. 이 순서를 지키면 운영 중에도 테이블 락 없이 작업할 수 있다.

### 대용량 UPDATE 배치 처리

수백만 건 이상이면 한 번에 UPDATE하면 트랜잭션이 길어지고 락 충돌 가능성이 높다.

```python
import asyncio
import asyncpg

async def backfill_tenant_id(
    pool: asyncpg.Pool,
    tenant_id: str,
    batch_size: int = 1000
) -> None:
    last_id = 0

    while True:
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE orders
                SET tenant_id = $1
                WHERE id > $2
                  AND id <= $2 + $3
                  AND tenant_id IS NULL
                """,
                tenant_id, last_id, batch_size
            )
            updated = int(result.split()[-1])

        if updated == 0:
            break

        last_id += batch_size
        await asyncio.sleep(0.05)  # autovacuum과 다른 쿼리에 여유를 줌
```

배치 크기와 대기 시간은 DB 부하 상태에 따라 조정한다. 배치 처리 중간에 실패해도 WHERE 조건이 있어서 재시작이 가능하다.

### 마이그레이션 검증

UPDATE 완료 후 모든 행에 `tenant_id`가 채워졌는지 확인한다.

```sql
-- NULL 행이 없어야 함
SELECT COUNT(*) FROM orders WHERE tenant_id IS NULL;

-- 테넌트별 분포 확인
SELECT tenant_id, COUNT(*) FROM orders GROUP BY tenant_id;
```

NULL 행이 없다는 걸 확인한 후 NOT NULL 제약을 추가한다.

---

## Cross-Tenant 집계 쿼리

### 운영 집계

시스템 관리자가 전체 테넌트를 대상으로 집계할 때 공유 테이블 방식은 스키마 분리보다 쿼리가 단순하다.

```sql
-- 전체 테넌트 현황 (관리자 대시보드)
SELECT
    tenant_id,
    COUNT(*)                                     AS order_count,
    SUM(amount)                                  AS total_revenue,
    MAX(created_at)                              AS last_order_at
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY tenant_id
ORDER BY total_revenue DESC;
```

이 쿼리는 `tenant_id` 인덱스를 쓰지 않고 전체 테이블을 스캔한다. 대용량 테이블에서는 실시간 집계보다 별도 집계 테이블을 유지하는 방식이 낫다.

### 집계 테이블 유지

```sql
CREATE TABLE tenant_daily_stats (
    tenant_id    UUID           NOT NULL,
    stat_date    DATE           NOT NULL,
    order_count  INT            NOT NULL DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, stat_date)
);

-- 매일 자정 배치 실행
INSERT INTO tenant_daily_stats (tenant_id, stat_date, order_count, total_amount)
SELECT
    tenant_id,
    CURRENT_DATE - 1 AS stat_date,
    COUNT(*),
    SUM(amount)
FROM orders
WHERE created_at::DATE = CURRENT_DATE - 1
GROUP BY tenant_id
ON CONFLICT (tenant_id, stat_date) DO UPDATE
    SET order_count  = EXCLUDED.order_count,
        total_amount = EXCLUDED.total_amount,
        updated_at   = NOW();
```

집계 쿼리를 배치로 내리면 관리자 대시보드가 집계 테이블만 읽으므로 운영 테이블에 부하를 주지 않는다. 배치 실패 시 재계산 범위를 명확히 해두어야 한다.

### 특정 테넌트 비교

A/B 테스트나 플랜 비교처럼 특정 테넌트들을 비교할 때는 `ANY` 조건으로 처리한다.

```sql
SELECT
    tenant_id,
    COUNT(*)        AS order_count,
    AVG(amount)     AS avg_order_value
FROM orders
WHERE tenant_id = ANY(ARRAY[
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333'
]::UUID[])
  AND created_at >= '2026-01-01'
GROUP BY tenant_id;
```

파티셔닝이 적용된 경우 각 tenant_id에 해당하는 파티션만 스캔한다.

---

## 관련 문서

- Cross_Schema.md — 공유 테이블, Schema-Per-Tenant, Separate DB 비교
- Schema_Per_Tenant.md — 스키마 분리 방식 구현
- 데이터베이스_샤딩.md — 수평 확장
