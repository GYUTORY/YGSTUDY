---
title: Schema-Per-Tenant
tags: [database, postgresql, multi-tenant, schema-per-tenant, provisioning, migration, pgbouncer, flyway, liquibase, connection-pool, search-path, autovacuum]
updated: 2026-08-04
---

# Schema-Per-Tenant

테넌트마다 별도의 스키마를 두는 방식이다. 하나의 PostgreSQL 데이터베이스 안에 `tenant_001`, `tenant_002` 같은 스키마가 수십에서 수백 개 존재하고, 각 스키마는 동일한 테이블 구조를 갖는다.

공유 스키마(shared schema)와 비교하면 테넌트 간 데이터 격리가 DB 레벨에서 보장된다. `WHERE tenant_id = ?` 조건을 빠뜨려도 다른 테넌트 데이터가 노출되지 않는다. 반면 스키마 수가 늘어날수록 관리 비용이 선형으로 증가한다. 스키마 100개에 테이블 50개면 DDL 변경 하나에 5,000개 오브젝트를 건드려야 한다.

공유 스키마 방식(`tenant_id` 컬럼)과의 선택 기준은 Cross_Schema.md의 비교 섹션을 참고한다. 이 문서는 schema-per-tenant를 선택한 이후의 구현 문제를 다룬다.

---

## 스키마 프로비저닝 자동화

### 템플릿 스키마

신규 테넌트 생성 시 DDL을 코드에서 직접 나열하는 것보다, `template` 스키마를 유지하고 복사하는 방식이 관리하기 낫다. `template` 스키마는 실제 데이터 없이 테이블 정의, 인덱스, 시퀀스, 트리거, 기본 설정 데이터만 담는다.

```sql
-- template 스키마 초기 구성
CREATE SCHEMA template;

CREATE TABLE template.users (
    id         BIGSERIAL PRIMARY KEY,
    email      VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE template.orders (
    id         BIGSERIAL    PRIMARY KEY,
    user_id    BIGINT       NOT NULL REFERENCES template.users(id),
    amount     DECIMAL(12, 2) NOT NULL,
    status     VARCHAR(50)  NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user   ON template.orders (user_id);
CREATE INDEX idx_orders_status ON template.orders (status, created_at DESC);
```

PostgreSQL에서 `LIKE ... INCLUDING ALL`로 테이블 구조를 복사할 수 있다. 인덱스, 제약조건, 시퀀스 기본값까지 가져온다.

```sql
CREATE SCHEMA tenant_003;

CREATE TABLE tenant_003.users
    (LIKE template.users INCLUDING ALL);

CREATE TABLE tenant_003.orders
    (LIKE template.orders INCLUDING ALL);
```

`LIKE INCLUDING ALL`은 제약조건 이름도 복사하지만, 같은 DB 안에서 스키마가 다르므로 충돌은 없다. FK는 복사하지 않는다. `REFERENCES template.users(id)` 같은 FK는 스키마를 지정하기 때문에 `tenant_003.orders`가 `template.users`를 참조하는 형태가 된다. 프로비저닝 시 FK를 별도로 추가해야 한다.

```sql
ALTER TABLE tenant_003.orders
ADD CONSTRAINT fk_orders_user
FOREIGN KEY (user_id) REFERENCES tenant_003.users(id);
```

### 트랜잭션 처리

스키마 프로비저닝은 DDL 작업이다. PostgreSQL에서 DDL은 트랜잭션 안에서 실행할 수 있고, 중간에 실패하면 롤백된다.

```sql
BEGIN;

CREATE SCHEMA tenant_003;
CREATE TABLE tenant_003.users (LIKE template.users INCLUDING ALL);
CREATE TABLE tenant_003.orders (LIKE template.orders INCLUDING ALL);
ALTER TABLE tenant_003.orders
    ADD CONSTRAINT fk_orders_user
    FOREIGN KEY (user_id) REFERENCES tenant_003.users(id);

-- 별도 테이블에 테넌트 등록
INSERT INTO public.tenants (schema_name, created_at)
VALUES ('tenant_003', NOW());

COMMIT;
```

실패하면 ROLLBACK으로 반쯤 만들어진 스키마가 남지 않는다. MySQL에서는 DDL이 묵시적 커밋을 유발하므로 이 방식이 동작하지 않는다.

애플리케이션 코드로 구현할 때는 테넌트 레코드 INSERT와 스키마 생성을 하나의 트랜잭션으로 묶어야 한다. 테넌트 레코드만 생기고 스키마 생성이 실패한 채로 남으면, 나중에 어느 테넌트가 완전히 프로비저닝됐는지 알 수 없다.

```python
def provision_tenant(conn, tenant_id: str) -> None:
    schema_name = f"tenant_{tenant_id}"
    with conn.transaction():
        conn.execute(f'CREATE SCHEMA "{schema_name}"')
        _copy_template_tables(conn, schema_name)
        _add_fk_constraints(conn, schema_name)
        conn.execute(
            "INSERT INTO public.tenants (schema_name) VALUES ($1)",
            schema_name
        )
```

### DDL 스크립트 관리

템플릿 스키마를 코드로 관리하지 않으면 `template` 스키마와 기존 테넌트 스키마가 점점 어긋난다. `template`에 컬럼을 추가했는데 기존 테넌트에 적용하지 않으면, 신규 테넌트와 구 테넌트가 다른 구조를 갖는다. seed SQL 파일로 `template` 스키마를 관리하고, 변경 시 마이그레이션으로 기존 테넌트에도 일괄 적용하는 방식이 현실적이다.

---

## 마이그레이션 관리

### Flyway per-schema 설정

Flyway는 기본적으로 단일 스키마를 대상으로 동작한다. 스키마 여러 개에 적용하려면 각 스키마를 별도 datasource로 구성하거나, Flyway를 프로그래밍 방식으로 호출해야 한다.

```java
// Spring Boot에서 프로그래밍 방식으로 스키마별 Flyway 실행
@Component
public class TenantMigrationRunner {

    @Autowired
    private DataSource dataSource;

    @Autowired
    private TenantRepository tenantRepository;

    public void migrateAll() {
        List<String> schemas = tenantRepository.findAllSchemaNames();

        for (String schema : schemas) {
            Flyway flyway = Flyway.configure()
                .dataSource(dataSource)
                .schemas(schema)
                .locations("classpath:db/migration")
                .table("flyway_schema_history")
                .load();

            flyway.migrate();
        }
    }
}
```

`flyway_schema_history` 테이블이 각 스키마 안에 생기므로 어느 테넌트가 어느 버전까지 적용됐는지 스키마별로 독립적으로 추적된다. 특정 테넌트만 마이그레이션에 실패해도 다른 테넌트에 영향을 주지 않는다.

### Liquibase per-schema 설정

```java
public void migrateSchema(Connection connection, String schemaName) throws Exception {
    Database database = DatabaseFactory.getInstance()
        .findCorrectDatabaseImplementation(new JdbcConnection(connection));
    database.setDefaultSchemaName(schemaName);

    Liquibase liquibase = new Liquibase(
        "db/changelog/db.changelog-master.yaml",
        new ClassLoaderResourceAccessor(),
        database
    );
    liquibase.update(new Contexts(), new LabelExpression());
}
```

Liquibase의 `DATABASECHANGELOG` 테이블도 각 스키마 안에 생성된다.

### 병렬 vs 순차 실행

스키마 100개에 마이그레이션을 순차로 돌리면 각 마이그레이션이 1초씩만 걸려도 1분 40초다. 무거운 DDL(대용량 테이블 컬럼 추가, 인덱스 생성)이면 훨씬 길어진다.

병렬로 돌릴 수 있지만 DB 서버에 동시 DDL 부하가 집중된다. autovacuum이 방해받거나 lock contention이 발생할 수 있다.

```python
import concurrent.futures
from typing import List

def migrate_all_tenants(schemas: List[str], max_workers: int = 5):
    failed = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_schema = {
            executor.submit(migrate_schema, schema): schema
            for schema in schemas
        }

        for future in concurrent.futures.as_completed(future_to_schema):
            schema = future_to_schema[future]
            try:
                future.result()
                print(f"Migrated: {schema}")
            except Exception as e:
                print(f"Failed: {schema} — {e}")
                failed.append(schema)

    if failed:
        with open("migration_failures.txt", "w") as f:
            f.writelines(f"{s}\n" for s in failed)
```

`max_workers`는 DB 서버 스펙과 마이그레이션 성격에 따라 조정한다. DDL 위주면 낮게(3~5), 단순한 DML이면 더 높게 설정할 수 있다.

### 실패 시 롤백 전략

스키마별로 독립적으로 마이그레이션이 실행되므로 특정 스키마에서 실패해도 다른 스키마는 영향을 받지 않는다. 문제는 실패한 스키마가 중간 상태에 머문다는 것이다. 컬럼을 추가하는 마이그레이션이 실패하면 해당 스키마에는 컬럼이 없는 상태로 남는다. 애플리케이션이 그 컬럼을 필요로 하는 코드를 배포했다면 해당 테넌트에서 런타임 에러가 난다.

대응 방법은 두 가지다. 하나는 실패한 스키마 목록을 로깅해두고 마이그레이션 완료 후 수동으로 처리하는 것이다. 다른 하나는 expand-contract 패턴을 쓰는 것이다. 새 컬럼이 없어도 동작하게 코드를 먼저 배포하고, 마이그레이션 완료 후 새 컬럼만 쓰는 코드로 전환하면 마이그레이션 실패가 있어도 서비스 중단 없이 처리할 수 있다.

---

## 연결 라우팅

### 애플리케이션에서 search_path 설정

테넌트별 스키마를 쓰려면 각 요청에서 올바른 스키마를 참조해야 한다. PostgreSQL에서는 `search_path`를 설정하는 방법이 흔하다.

```sql
SET search_path TO tenant_001, shared, public;

-- 이후 스키마 없이 쿼리 가능
SELECT * FROM orders;  -- tenant_001.orders 참조
```

애플리케이션에서는 요청 처리 시작 시점에 search_path를 설정한다.

```python
# FastAPI middleware 예시
@app.middleware("http")
async def set_tenant_schema(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(400, "Tenant ID required")

    schema = f"tenant_{tenant_id}"

    async with get_connection() as conn:
        await conn.execute(f'SET search_path TO "{schema}", shared, public')
        request.state.db = conn
        response = await call_next(request)

    return response
```

`search_path`에 `shared`와 `public`을 뒤에 추가하면 공통 테이블(플랜, 설정 등)을 스키마명 없이 참조할 수 있다.

### PgBouncer session mode vs transaction mode

`search_path`는 세션 단위 설정이다. PgBouncer를 쓸 때 이 점이 문제가 된다.

**transaction mode**에서는 트랜잭션이 끝나면 커넥션이 풀에 반환된다. 다음 요청은 다른 세션을 가져올 수 있다. 이전 세션에서 `SET search_path`를 했어도 다른 세션에는 적용되지 않는다. 요청마다 search_path를 재설정해야 하는데, `SET`이 트랜잭션 외부에서 실행되면 transaction mode에서 허용되지 않는다.

```
ERROR: SET not allowed in transaction mode
```

**session mode**에서는 하나의 세션이 하나의 클라이언트에 고정된다. `search_path`를 설정하면 세션이 닫힐 때까지 유지된다. 하지만 커넥션 수가 늘어나고 PgBouncer의 멀티플렉싱 이점이 줄어든다.

schema-per-tenant를 `search_path`로 구현할 때는 session mode를 쓰거나, 모든 쿼리에 스키마를 명시하는 방식을 택한다.

```python
# 스키마를 직접 지정하는 방식 (transaction mode 호환)
async def get_orders(conn, tenant_id: str):
    schema = f"tenant_{tenant_id}"
    return await conn.fetch(
        f'SELECT * FROM "{schema}".orders WHERE created_at > $1',
        cutoff_date
    )
```

이 방식은 SQL에 스키마 이름이 하드코딩되므로 ORM과 함께 쓰기 어렵다. ORM을 쓴다면 session mode + `search_path` 설정이 더 현실적이다.

PgBouncer에서 `server_reset_query`를 설정해서 커넥션 반환 시 `search_path`를 초기화할 수도 있다.

```ini
# pgbouncer.ini
server_reset_query = DISCARD ALL
```

`DISCARD ALL`은 세션 설정, 임시 테이블, prepared statements를 모두 초기화한다. 비용이 있으므로 상황에 따라 `RESET search_path`만 실행하는 게 나을 수 있다.

---

## 성능 문제

### 시스템 카탈로그 비대화

PostgreSQL은 모든 테이블, 컬럼, 인덱스, 시퀀스 정보를 `pg_class`, `pg_attribute`, `pg_index` 등의 시스템 카탈로그에 저장한다. 스키마 100개에 테이블 50개씩이면 `pg_class`에 5,000개 이상의 row가 생기고, `pg_attribute`는 컬럼 수만큼 더 커진다.

`information_schema.columns` 같은 뷰는 내부적으로 `pg_class`와 `pg_attribute`를 조인한다. 스키마가 많을수록 이 조회가 느려진다.

```sql
-- information_schema.columns 조회 (스키마 많으면 느림)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'tenant_001' AND table_name = 'orders';

-- pg_catalog 직접 조회 (더 빠름)
SELECT a.attname                                            AS column_name,
       pg_catalog.format_type(a.atttypid, a.atttypmod)     AS data_type
FROM   pg_catalog.pg_attribute  a
JOIN   pg_catalog.pg_class      c ON c.oid = a.attrelid
JOIN   pg_catalog.pg_namespace  n ON n.oid = c.relnamespace
WHERE  n.nspname     = 'tenant_001'
  AND  c.relname     = 'orders'
  AND  a.attnum      > 0
  AND  NOT a.attisdropped;
```

마이그레이션 도구가 스키마 구조를 확인할 때 `information_schema`를 쓰면 스키마가 많아질수록 검증 단계만으로도 시간이 길어진다. Flyway는 내부적으로 `information_schema`를 쓰는 경우가 있어서, 스키마가 50개를 넘어서면 체감할 만큼 느려지기 시작한다.

### autovacuum worker 증가

PostgreSQL의 autovacuum은 테이블 단위로 동작한다. 스키마 100개에 테이블 50개면 잠재적으로 5,000개 테이블을 관리해야 한다. 기본 autovacuum 설정으로는 처리 속도가 부족할 수 있다. INSERT/UPDATE가 활발한 테넌트가 많을 때 autovacuum이 따라가지 못하면 테이블 bloat이 쌓이고 쿼리가 느려진다.

```sql
-- autovacuum 지연 현황 확인
SELECT schemaname, relname, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

`postgresql.conf`에서 `autovacuum_max_workers`를 늘리는 것을 검토한다(기본값 3). 활성 테넌트의 테이블에는 개별 설정으로 vacuum을 더 적극적으로 돌릴 수 있다.

```sql
ALTER TABLE tenant_001.orders SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);
```

### information_schema 조회 느려지는 시점

스키마 50개를 넘어서면 `information_schema` 기반 도구가 눈에 띄게 느려지기 시작한다. 스키마 200개 이상에서는 Flyway의 스키마 검증 단계만으로 수십 초가 걸리는 경우도 있다.

이 시점에 검토할 방법은 두 가지다. 마이그레이션 시 `information_schema` 대신 `pg_catalog` 뷰를 직접 쿼리하도록 도구를 커스터마이징하거나, 마이그레이션을 오프-피크 시간에 배치로 실행하면서 병렬도를 조절하는 것이다.

---

## 테넌트 오프보딩

### 데이터 내보내기

스키마를 삭제하기 전에 데이터를 내보내야 한다. `pg_dump`로 스키마 단위 백업이 가능하다.

```bash
# 특정 스키마만 덤프
pg_dump \
    --schema=tenant_003 \
    --format=custom \
    --file=tenant_003_backup.dump \
    dbname

# 복원 시
pg_restore \
    --schema=tenant_003 \
    --dbname=target_db \
    tenant_003_backup.dump
```

테넌트에게 데이터를 제공해야 하는 경우 CSV로도 내보낼 수 있다.

```sql
-- psql에서 CSV 내보내기
\copy tenant_003.orders TO 'tenant_003_orders.csv' CSV HEADER
\copy tenant_003.users  TO 'tenant_003_users.csv'  CSV HEADER
```

### DROP SCHEMA CASCADE 위험성

`DROP SCHEMA CASCADE`는 해당 스키마 안의 모든 오브젝트를 함께 삭제한다. 실행 즉시 되돌릴 수 없다.

```sql
-- 실행하면 테이블과 데이터가 모두 사라짐
DROP SCHEMA tenant_003 CASCADE;
```

오프보딩 프로세스에서 잘못된 스키마를 삭제하는 사고가 실제로 발생한다. 삭제 전에 스키마 이름을 변경해서 격리하는 방식이 안전하다.

```sql
-- 삭제 전 규모 확인
SELECT table_name,
       pg_size_pretty(pg_total_relation_size(
           quote_ident('tenant_003') || '.' || quote_ident(table_name)
       )) AS size
FROM information_schema.tables
WHERE table_schema = 'tenant_003';

-- 스키마 이름 변경으로 격리 (바로 삭제하지 않음)
ALTER SCHEMA tenant_003 RENAME TO tenant_003_offboarded_20260804;

-- 일정 기간 후 최종 백업 뜨고 삭제
-- pg_dump --schema=tenant_003_offboarded_20260804 ...
-- DROP SCHEMA tenant_003_offboarded_20260804 CASCADE;
```

스키마 이름을 바꿔두면 애플리케이션에서 해당 테넌트 접근이 즉시 실패하므로 격리 효과가 있고, 잘못된 삭제인지 확인할 시간도 생긴다.

---

## 관리용 cross-tenant 쿼리

### 모든 스키마에 걸친 집계

전체 테넌트의 데이터를 집계해야 할 때(전체 매출 합산, 활성 테넌트 현황 등)는 각 스키마를 순회해서 UNION ALL로 합치는 쿼리를 동적으로 생성한다.

```sql
DO $$
DECLARE
    v_schema TEXT;
    v_query  TEXT := '';
    v_first  BOOLEAN := TRUE;
BEGIN
    FOR v_schema IN
        SELECT schema_name
        FROM public.tenants
        WHERE status = 'active'
        ORDER BY schema_name
    LOOP
        IF NOT v_first THEN
            v_query := v_query || ' UNION ALL ';
        END IF;

        v_query := v_query || format(
            'SELECT %L AS tenant, COUNT(*) AS order_count, SUM(amount) AS total
             FROM %I.orders
             WHERE created_at >= CURRENT_DATE - INTERVAL ''30 days''',
            v_schema, v_schema
        );

        v_first := FALSE;
    END LOOP;

    EXECUTE 'CREATE TEMP TABLE _tenant_summary AS ' || v_query;
END $$;

SELECT tenant, order_count, total
FROM _tenant_summary
ORDER BY total DESC;
```

스키마 수가 많을수록 쿼리 계획이 커지고 실행 시간이 늘어난다. 실시간 조회보다는 배치 집계 작업에 쓰는 게 적합하다.

### 집계 전용 denormalized 테이블 유지

cross-tenant 집계가 자주 필요하다면, 각 테넌트의 통계를 별도 테이블에 모아두는 방식이 낫다. 테넌트별 이벤트 발생 시 또는 주기적 배치로 집계 테이블을 갱신한다.

```sql
CREATE TABLE public.tenant_stats (
    tenant_id    VARCHAR(100) NOT NULL,
    date         DATE         NOT NULL,
    order_count  INT          NOT NULL DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, date)
);

-- 일별 배치로 갱신
INSERT INTO public.tenant_stats (tenant_id, date, order_count, total_amount)
SELECT 'tenant_001',
       CURRENT_DATE,
       COUNT(*),
       SUM(amount)
FROM tenant_001.orders
WHERE created_at::DATE = CURRENT_DATE
ON CONFLICT (tenant_id, date) DO UPDATE
    SET order_count  = EXCLUDED.order_count,
        total_amount = EXCLUDED.total_amount,
        updated_at   = NOW();
```

cross-tenant 집계 쿼리가 단순해지고 각 테넌트 스키마에 부하를 주지 않는다. 각 테넌트 스키마에 배치 잡을 따로 실행해야 한다는 운영 비용이 추가된다.
