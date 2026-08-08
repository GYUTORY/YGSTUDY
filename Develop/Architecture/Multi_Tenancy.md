---
title: 멀티테넌시
tags: [architecture, postgresql, database, backend]
updated: 2026-08-04
---

# 멀티테넌시

## 시작하기 전에

멀티테넌시는 하나의 애플리케이션 인스턴스를 여러 고객(테넌트)이 공유하는 구조다. B2B SaaS를 만들다 보면 필연적으로 맞닥뜨린다. 고객사 A와 B가 같은 서버에서 돌아가는 같은 코드를 사용하지만, 서로의 데이터는 절대 보이면 안 된다.

문제는 이게 생각보다 까다롭다는 거다. 단순히 WHERE 절에 `tenant_id`를 붙이는 것만으로는 안 된다. 개발자가 실수로 필터를 빠뜨리면 다른 테넌트 데이터가 노출된다. 실제로 이 이유로 SaaS 서비스가 크게 터진 사례는 여럿 있다.

멀티테넌시를 제대로 구현하려면 DB 격리 모델을 결정하고, 요청마다 테넌트를 정확히 식별하고, 데이터 누출을 구조적으로 막는 것까지 세 가지가 맞물려야 한다.

---

## DB 격리 모델 3가지

격리 수준이 높을수록 운영 비용이 올라가고, 낮을수록 보안 사고 가능성이 올라간다. 세 가지 모델 각각에 대한 선택 기준을 먼저 이해해야 설계 방향을 잡을 수 있다.

### 공유 DB, 공유 스키마 (Shared Database, Shared Schema)

모든 테넌트가 같은 DB, 같은 테이블을 쓴다. 테이블마다 `tenant_id` 컬럼이 있고, 모든 쿼리에 이 컬럼을 기준으로 필터링한다.

```sql
CREATE TABLE orders (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   UUID NOT NULL,
    user_id     BIGINT NOT NULL,
    total       NUMERIC(12,2) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_orders_tenant ON orders (tenant_id);

-- 조회할 때는 반드시 tenant_id 포함
SELECT * FROM orders WHERE tenant_id = $1 AND id = $2;
```

비용이 제일 싸다. 인스턴스 하나, DB 하나로 수천 개 테넌트를 처리할 수 있다. 대신 코드 레벨에서 `tenant_id` 필터를 빠뜨리는 순간 데이터 누출이 발생한다. 이 위험을 막으려면 뒤에 설명할 PostgreSQL RLS나 미들웨어 레벨 강제 필터가 필요하다.

이 모델이 맞는 상황은 테넌트 수가 수백~수천 개이고, 테넌트별 데이터 크기가 크지 않으며, 고객이 완전한 데이터 격리를 계약상 요구하지 않을 때다.

### 공유 DB, 스키마 분리 (Shared Database, Separate Schema)

같은 DB 인스턴스를 쓰되, 테넌트마다 별도의 PostgreSQL 스키마(네임스페이스)를 만든다.

```sql
-- 테넌트 A 프로비저닝
CREATE SCHEMA tenant_a;
CREATE TABLE tenant_a.orders (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    total      NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 연결 시 search_path 설정으로 격리
SET search_path TO tenant_a;
SELECT * FROM orders; -- tenant_a.orders를 조회
```

`tenant_id` 컬럼 필터가 없어도 스키마 자체가 물리적 경계다. 쿼리를 잘못 짜도 다른 스키마에 접근하려면 명시적으로 스키마명을 붙여야 한다. 공유 스키마 모델보다 훨씬 안전하다.

단점은 테넌트 수가 늘어날수록 스키마 관리가 복잡해진다는 거다. PostgreSQL에서 스키마 수가 수천 개를 넘어가면 `pg_catalog` 조회가 눈에 띄게 느려지기 시작한다. 마이그레이션도 테넌트 수만큼 실행해야 한다. 스키마 100개면 마이그레이션 100번이다.

테넌트 수가 수십~수백 개 범위이고, 규정 준수나 감사 요건이 있어 논리적 격리가 필요할 때 선택한다.

### DB 분리 (Separate Database)

테넌트마다 완전히 분리된 DB 인스턴스를 둔다. 물리적으로 격리되니 데이터 누출 가능성이 가장 낮다. 고객이 자기 DB 인스턴스를 직접 접근하거나, 규제 요건으로 물리적 분리가 의무일 때 쓴다.

비용이 테넌트 수에 비례해서 올라간다. 테넌트 100개면 DB 인스턴스 100개다. 연결 풀 관리도 복잡하다. 각 테넌트 DB의 연결 정보를 런타임에 동적으로 가져와서 연결해야 한다.

```python
# 테넌트별 DB 연결 동적 라우팅 예시
class TenantDatabaseRouter:
    def __init__(self, tenant_registry: TenantRegistry):
        self._registry = tenant_registry
        self._pools: dict[str, ConnectionPool] = {}

    def get_connection(self, tenant_id: str) -> Connection:
        if tenant_id not in self._pools:
            config = self._registry.get_db_config(tenant_id)
            self._pools[tenant_id] = create_pool(config)
        return self._pools[tenant_id].acquire()
```

엔터프라이즈 계약을 맺은 대형 고객에게만 이 옵션을 제공하는 게 현실적이다.

### 모델 선택 기준

| 기준 | 공유 DB/스키마 | 스키마 분리 | DB 분리 |
|------|--------------|-----------|--------|
| 테넌트 수 | 수백~수천 | 수십~수백 | 수십 이하 |
| 데이터 격리 수준 | 낮음 (코드 의존) | 중간 (논리적) | 높음 (물리적) |
| 비용 | 낮음 | 중간 | 높음 |
| 마이그레이션 복잡도 | 낮음 | 높음 | 매우 높음 |
| 컴플라이언스 | 어려움 | 가능 | 용이 |

초기 스타트업이라면 공유 DB/스키마로 시작하되, 나중에 스키마 분리나 DB 분리로 마이그레이션할 수 있는 구조를 갖춰두는 게 현실적이다.

---

## 테넌트 식별 방법

요청이 들어왔을 때 어느 테넌트인지를 파악하는 방법이 세 가지 있다.

### 서브도메인

```
acme.myapp.com → 테넌트: acme
globex.myapp.com → 테넌트: globex
```

사용자 경험이 가장 자연스럽다. 브라우저 주소창에서 어느 테넌트인지 바로 보인다. 단점은 인증서 관리다. 테넌트마다 서브도메인이 있으면 와일드카드 인증서(`*.myapp.com`)로 커버하거나, Let's Encrypt로 동적 발급해야 한다.

서버에서 처리할 때는 `Host` 헤더에서 서브도메인을 파싱한다.

```python
def extract_tenant_from_host(host: str) -> str | None:
    # host: "acme.myapp.com"
    parts = host.split('.')
    if len(parts) >= 3:
        subdomain = parts[0]
        if subdomain not in ('www', 'api', 'admin'):
            return subdomain
    return None
```

### URL 경로

```
myapp.com/acme/dashboard
myapp.com/globex/dashboard
```

모바일 앱이나 API 클라이언트에서 많이 쓴다. 서브도메인 처리가 복잡한 환경에서 대안이 된다. 라우팅 설정이 조금 더 복잡해지고, 경로 첫 번째 세그먼트가 테넌트 슬러그라는 걸 모든 API 설계에서 고려해야 한다.

### 커스텀 헤더

API 서버간 통신이나 내부 서비스에서 많이 쓴다.

```http
POST /api/orders HTTP/1.1
X-Tenant-ID: acme-corp-uuid
Authorization: Bearer eyJ...
```

사용자 대면 앱에서는 쓰기 어렵다. 브라우저가 커스텀 헤더를 자동으로 붙여주지 않으니 클라이언트 코드에서 매번 헤더를 설정해야 한다. B2B API에서 고객사 서버가 직접 호출할 때는 깔끔하다.

### 실무에서 쓰는 방식

서브도메인 + JWT 조합이 제일 흔하다. 서브도메인으로 테넌트를 1차 식별하고, JWT 페이로드에 `tenant_id`를 넣어서 서버 내부에서는 JWT를 신뢰한다. 서브도메인과 JWT의 `tenant_id`가 일치하는지 검증하는 미들웨어를 인증 레이어에 추가한다.

```python
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        tenant_id = self._resolve_tenant(request)
        if tenant_id is None:
            return Response(status_code=400, content="테넌트를 식별할 수 없습니다")

        token_tenant = request.state.jwt_payload.get("tenant_id")
        if token_tenant != tenant_id:
            return Response(status_code=403, content="테넌트 불일치")

        request.state.tenant_id = tenant_id
        return await call_next(request)
```

---

## PostgreSQL Row-Level Security

RLS는 공유 DB/스키마 모델에서 데이터 누출을 막는 가장 확실한 방법이다. DB 레벨에서 강제하기 때문에 애플리케이션 코드가 `tenant_id` 필터를 빠뜨려도 다른 테넌트 데이터가 조회되지 않는다.

### 설정 방법

```sql
-- 1. orders 테이블에 RLS 활성화
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- 2. 정책 생성: 현재 tenant_id와 일치하는 행만 접근 허용
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- 3. 애플리케이션 DB 유저에게는 슈퍼유저 권한 부여 금지
-- (슈퍼유저는 RLS를 우회함)
GRANT SELECT, INSERT, UPDATE, DELETE ON orders TO app_user;
```

애플리케이션에서 DB 연결을 맺은 뒤 요청마다 세션 변수를 설정한다.

```sql
-- 쿼리 실행 전 테넌트 설정
SET LOCAL app.current_tenant_id = 'acme-corp-uuid';

-- 이후 조회는 자동으로 필터링됨
SELECT * FROM orders; -- tenant_id = 'acme-corp-uuid' 인 행만 반환
```

`SET LOCAL`은 트랜잭션 범위에서만 유효하다. 트랜잭션이 끝나면 자동으로 해제된다. `SET`은 세션 전체에 유효하니 커넥션 풀 환경에서 세션이 재사용될 때 문제가 될 수 있다. 반드시 `SET LOCAL`이나 트랜잭션 블록 안에서 설정해야 한다.

### ORM 연동 (SQLAlchemy 예시)

```python
from sqlalchemy import event, text

@event.listens_for(Session, "after_begin")
def set_tenant_context(session, transaction, connection):
    tenant_id = get_current_tenant_id()  # 컨텍스트 변수에서 가져옴
    if tenant_id:
        connection.execute(
            text("SET LOCAL app.current_tenant_id = :tid"),
            {"tid": str(tenant_id)}
        )
```

트랜잭션 시작 직후 자동으로 테넌트 컨텍스트를 설정한다. 이렇게 하면 개발자가 쿼리마다 `tenant_id`를 신경 쓸 필요가 없다.

### RLS 주의사항

슈퍼유저나 `BYPASSRLS` 권한을 가진 유저는 RLS를 무시한다. 마이그레이션 도구나 DBA 작업용 유저는 이 권한이 필요할 수 있는데, 애플리케이션 서비스 계정과 분리해야 한다.

`SECURITY DEFINER` 함수를 조심해야 한다. 이 함수 안에서 실행되는 쿼리는 함수를 정의한 유저의 권한으로 실행된다. 함수 소유자가 RLS를 우회할 수 있는 권한이 있으면 정책이 적용되지 않는다.

---

## 테넌트 간 데이터 누출 방지

RLS 하나로 다 해결되면 좋겠지만, 실제로는 여러 레이어에서 방어해야 한다.

### 코드 레벨: 컨텍스트 전파

스레드나 코루틴 로컬 변수에 현재 테넌트를 저장하고, 모든 리포지토리에서 이 컨텍스트를 강제로 참조하게 만든다.

```python
from contextvars import ContextVar

_current_tenant: ContextVar[str | None] = ContextVar('current_tenant', default=None)

def set_tenant(tenant_id: str):
    _current_tenant.set(tenant_id)

def get_tenant() -> str:
    tid = _current_tenant.get()
    if tid is None:
        raise RuntimeError("테넌트 컨텍스트가 설정되지 않았습니다")
    return tid

class OrderRepository:
    def find_by_id(self, order_id: int) -> Order | None:
        tenant_id = get_tenant()  # 컨텍스트에서 강제로 가져옴
        return self.db.query(Order).filter(
            Order.tenant_id == tenant_id,
            Order.id == order_id
        ).first()
```

이렇게 짜면 `find_by_id`를 호출하는 코드는 `tenant_id`를 인자로 넘기지 않아도 된다. 컨텍스트에서 자동으로 읽으니 누락될 가능성이 줄어든다.

### 파일 스토리지 격리

S3 버킷에 파일을 저장할 때 테넌트 ID를 경로 prefix로 쓴다.

```
s3://my-bucket/tenants/{tenant_id}/uploads/{file_id}
```

파일 다운로드 URL을 생성할 때 현재 테넌트와 파일 경로의 테넌트가 일치하는지 반드시 검증해야 한다.

```python
def generate_presigned_url(file_key: str, tenant_id: str) -> str:
    # 경로에서 테넌트 추출
    path_tenant = file_key.split('/')[1]  # tenants/{tenant_id}/...
    if path_tenant != tenant_id:
        raise PermissionError("다른 테넌트의 파일에 접근할 수 없습니다")
    return s3_client.generate_presigned_url(...)
```

### 캐시 격리

Redis 캐시에 테넌트별 데이터를 저장할 때 키에 테넌트 ID를 포함시킨다.

```python
def cache_key(tenant_id: str, entity: str, entity_id: int) -> str:
    return f"tenant:{tenant_id}:{entity}:{entity_id}"

# "tenant:acme-corp:order:42"
```

캐시 무효화도 테넌트 범위로 한정한다. `FLUSHDB`를 쓰면 모든 테넌트 캐시가 날아간다.

### 백그라운드 작업

비동기 작업 큐(Celery, Worker 등)에 태스크를 등록할 때 `tenant_id`를 태스크 인자에 명시적으로 포함시켜야 한다. 컨텍스트 변수는 태스크 실행 환경까지 전파되지 않는다.

```python
@celery_app.task
def generate_report(tenant_id: str, report_type: str):
    set_tenant(tenant_id)  # 작업 시작 시 컨텍스트 복구
    # ... 이후 로직
```

---

## 온보딩과 프로비저닝

신규 테넌트가 가입했을 때 데이터 구조를 만들고 초기 설정을 완료하는 과정이다. 격리 모델에 따라 복잡도가 달라진다.

### 공유 스키마 모델의 프로비저닝

`tenants` 테이블에 레코드를 하나 추가하는 게 전부다.

```sql
INSERT INTO tenants (id, slug, name, plan, created_at)
VALUES (gen_random_uuid(), 'acme-corp', 'ACME Corp', 'starter', now())
RETURNING id;
```

이후 해당 `tenant_id`를 외래키로 참조하는 테이블에 데이터가 쌓이기 시작한다.

### 스키마 분리 모델의 프로비저닝

스키마 생성, 테이블 생성, 초기 데이터 삽입이 순서대로 일어나야 한다.

```python
async def provision_tenant(tenant_id: str, slug: str) -> None:
    schema_name = f"tenant_{slug.replace('-', '_')}"
    
    async with db.transaction():
        # 1. 스키마 생성
        await db.execute(f"CREATE SCHEMA {schema_name}")
        
        # 2. 스키마에 테이블 생성 (마이그레이션 실행)
        await run_migrations(schema=schema_name)
        
        # 3. 테넌트 레지스트리에 등록
        await db.execute(
            "INSERT INTO tenant_registry (id, slug, schema_name) VALUES ($1, $2, $3)",
            tenant_id, slug, schema_name
        )
        
        # 4. 기본 설정 데이터 삽입
        await db.execute(
            f"INSERT INTO {schema_name}.settings (key, value) VALUES ('plan', 'starter')"
        )
```

프로비저닝 실패 시 정리가 중요하다. 스키마는 만들어졌는데 레지스트리 등록이 실패하면, 다음 번 재시도 때 이미 존재하는 스키마를 처리해야 한다. `IF NOT EXISTS`와 멱등성을 염두에 두고 짜야 한다.

### 느린 프로비저닝 처리

스키마 분리나 DB 분리 모델에서는 프로비저닝이 수 초 이상 걸릴 수 있다. 사용자가 가입 버튼을 눌렀을 때 즉시 완료되길 기대한다면 비동기 처리가 필요하다.

```python
@router.post("/tenants/register")
async def register_tenant(data: TenantRegisterRequest):
    tenant_id = uuid4()
    
    # 테넌트 레코드를 "provisioning" 상태로 먼저 저장
    await tenant_repo.create(id=tenant_id, status="provisioning")
    
    # 비동기 작업 큐에 프로비저닝 태스크 등록
    provision_tenant.delay(str(tenant_id), data.slug)
    
    return {"tenant_id": str(tenant_id), "status": "provisioning"}
```

프론트엔드에서 폴링하거나 웹소켓으로 완료 이벤트를 받는 방식으로 처리한다.

---

## 실무 트러블슈팅 사례

### 커넥션 풀에서 테넌트 컨텍스트 오염

`SET app.current_tenant_id`를 트랜잭션이 아닌 세션 레벨로 설정하면, 커넥션이 풀에 반환된 후 다음 요청에서도 이전 테넌트 설정이 남아있다. 증상은 간헐적으로 다른 테넌트 데이터가 섞여 나오는 거다.

해결은 `SET LOCAL`을 트랜잭션 블록 안에서만 쓰는 거다. ORM 이벤트 훅으로 트랜잭션 시작 시 설정하고, 커넥션 반환 시 `RESET app.current_tenant_id`를 실행해서 정리한다.

### 마이그레이션 실수

스키마 분리 모델에서 새 컬럼을 추가하는 마이그레이션을 실행할 때, 모든 테넌트 스키마에 순서대로 적용해야 한다. 중간에 실패하면 스키마마다 컬럼 유무가 달라진다.

```python
async def run_migration_all_tenants(migration_fn):
    tenants = await tenant_registry.list_all()
    failed = []
    
    for tenant in tenants:
        try:
            await migration_fn(schema=tenant.schema_name)
        except Exception as e:
            failed.append((tenant.id, str(e)))
            logger.error(f"마이그레이션 실패 tenant={tenant.id}: {e}")
    
    if failed:
        raise MigrationPartialFailure(failed_tenants=failed)
```

실패한 테넌트만 재시도할 수 있도록 실패 목록을 남겨야 한다.

### N+1 쿼리와 테넌트 수

공유 스키마에서 테넌트가 1000개 넘어갔을 때 관리자 대시보드에서 테넌트 목록과 각 테넌트의 주문 수를 같이 보여주는 화면이 문제가 된다. 리포지토리 코드가 단건 조회를 루프로 돌리면 DB 쿼리가 1001번 나간다. 집계 쿼리 한 번으로 끝내야 한다.

```sql
SELECT t.id, t.name, COUNT(o.id) AS order_count
FROM tenants t
LEFT JOIN orders o ON o.tenant_id = t.id
GROUP BY t.id, t.name;
```

### RLS 성능

RLS 정책이 붙은 테이블은 `EXPLAIN ANALYZE`를 돌려봤을 때 실행 계획에 필터가 추가되는 걸 확인해야 한다. 대용량 테이블에서 `tenant_id` 인덱스가 없으면 풀 스캔이 발생한다.

```sql
-- tenant_id 단독 인덱스 또는 복합 인덱스
CREATE INDEX idx_orders_tenant_created ON orders (tenant_id, created_at DESC);
```

쿼리 패턴에 맞게 복합 인덱스를 만들되, `tenant_id`는 항상 첫 번째 컬럼에 둬야 인덱스를 제대로 탄다.
