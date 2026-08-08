---
title: 크로스 테넌트 유출
tags: [security, architecture]
updated: 2026-08-04
---

# 크로스 테넌트 유출

## 어디서 터지는가

멀티테넌트 서비스에서 데이터 격리는 대부분 코드 레벨에서 구현한다. 데이터베이스 RLS나 별도 스키마를 쓰더라도 애플리케이션 레이어에서 테넌트 컨텍스트를 잘못 다루는 순간 다른 테넌트의 데이터가 그대로 노출된다. 이 문서는 실제 서비스에서 반복적으로 나오는 유출 경로와 방어 방법을 다룬다.

---

## API 레이어의 IDOR

IDOR(Insecure Direct Object Reference)는 클라이언트가 넘긴 ID 값을 서버가 그대로 신뢰할 때 발생한다. 가장 흔한 패턴은 URL 파라미터나 요청 바디에 리소스 ID를 받아서 소유권 검증 없이 조회하는 것이다.

```python
# 취약한 코드 - tenant_id 검증이 없다
@app.get("/api/reports/{report_id}")
async def get_report(report_id: int, current_user: User = Depends(get_current_user)):
    report = await db.fetch_one(
        "SELECT * FROM reports WHERE id = :id",
        {"id": report_id}
    )
    return report
```

`report_id`를 1부터 순서대로 바꿔가며 요청하면 다른 테넌트의 리포트를 전부 가져올 수 있다. 인증은 통과하지만 인가(authorization) 검사가 없다.

```python
# 소유권 검증을 쿼리에 포함한다
@app.get("/api/reports/{report_id}")
async def get_report(report_id: int, current_user: User = Depends(get_current_user)):
    report = await db.fetch_one(
        "SELECT * FROM reports WHERE id = :id AND tenant_id = :tenant_id",
        {"id": report_id, "tenant_id": current_user.tenant_id}
    )
    if not report:
        raise HTTPException(status_code=404)
    return report
```

`tenant_id` 조건이 없으면 ID만 알아내면 접근 가능하다. 쿼리에 `tenant_id` 조건을 명시하거나 조회 후 소유권을 검증한 뒤 404 처리가 최소한의 방어다. 403을 돌려주지 않고 404로 처리하는 이유는 403은 리소스 존재 여부를 간접적으로 알려주기 때문이다.

IDOR는 리소스 ID가 URL에 노출되는 REST API에서 자주 생기지만, GraphQL에서도 동일하게 발생한다. GraphQL resolver에서 `id`로 직접 조회할 때 소유권 검사를 빠뜨리는 경우가 많다.

```python
# GraphQL resolver
@strawberry.type
class Query:
    @strawberry.field
    async def invoice(self, id: int, info: strawberry.types.Info) -> Invoice:
        ctx = info.context
        invoice = await db.fetch_one(
            # 잘못된 예: id만으로 조회
            # "SELECT * FROM invoices WHERE id = :id"
            # 올바른 예: tenant_id 포함
            "SELECT * FROM invoices WHERE id = :id AND tenant_id = :tenant_id",
            {"id": id, "tenant_id": ctx.current_user.tenant_id}
        )
        if not invoice:
            raise ValueError("Not found")
        return invoice
```

---

## 순차 ID로 인한 리소스 탐색

UUID 대신 순차 정수 ID를 쓸 때 생기는 문제다. 테넌트 A가 자기 리소스 ID `10042`를 알면, `10040`, `10041`, `10043`도 시도할 수 있다. IDOR 방어가 잘 돼있어도 순차 ID는 다른 리소스의 존재 여부를 노출한다. 응답 시간 차이나 에러 코드 종류만으로도 정보를 유추할 수 있다.

UUID v4를 사용하면 ID만으로 다른 리소스를 탐색하기 어렵다. 단, UUID는 인덱스 효율이 떨어지기 때문에 UUID v7(시간 기반 정렬 UUID)를 쓰면 순차 삽입 성능을 유지하면서 예측 불가능성을 얻을 수 있다.

```sql
-- PostgreSQL에서 UUID v7 생성 (pg_uuidv7 확장 사용)
CREATE TABLE reports (
    id UUID DEFAULT uuid_generate_v7() PRIMARY KEY,
    tenant_id UUID NOT NULL,
    ...
);
```

순차 ID를 변경하기 어려운 상황이면, 외부 노출용 ID와 내부 DB PK를 분리한다. 클라이언트에는 UUID나 해시를 노출하고, 내부에서는 정수 PK를 사용한다.

```python
# 외부 ID로 조회 후 내부 처리
@app.get("/api/reports/{external_id}")
async def get_report(external_id: str, current_user: User = Depends(get_current_user)):
    report = await db.fetch_one(
        "SELECT * FROM reports WHERE external_id = :external_id AND tenant_id = :tenant_id",
        {"external_id": external_id, "tenant_id": current_user.tenant_id}
    )
    if not report:
        raise HTTPException(status_code=404)
    return report
```

---

## Redis/Memcached 캐시 키 오염

캐시 레이어에서 테넌트 격리를 빠뜨리는 경우가 있다. 캐시 키에 테넌트 식별자를 포함하지 않으면, 다른 테넌트가 먼저 캐시해둔 데이터를 그대로 받게 된다.

```python
# 취약한 캐시 패턴 - user_id만으로 키를 만든다
async def get_user_settings(user_id: int) -> dict:
    cache_key = f"user_settings:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    settings = await db.fetch_one(
        "SELECT * FROM user_settings WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    await redis.setex(cache_key, 300, json.dumps(settings))
    return settings
```

`user_id`가 테넌트 간에 고유하지 않거나 (예: 각 테넌트 내부에서 1부터 시작하는 경우), 캐시 키 네임스페이스가 분리되지 않으면 다른 테넌트의 설정 데이터가 반환된다.

```python
# 테넌트 ID를 캐시 키에 포함한다
async def get_user_settings(tenant_id: str, user_id: int) -> dict:
    cache_key = f"tenant:{tenant_id}:user_settings:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    settings = await db.fetch_one(
        "SELECT * FROM user_settings WHERE user_id = :user_id AND tenant_id = :tenant_id",
        {"user_id": user_id, "tenant_id": tenant_id}
    )
    await redis.setex(cache_key, 300, json.dumps(settings))
    return settings
```

Redis DB 번호로 테넌트를 분리하는 방법도 있지만 DB 수가 최대 16개(0~15)라서 확장에 한계가 있다. 키 프리픽스 방식이 현실적이다.

또 다른 문제는 캐시 무효화다. 테넌트의 데이터가 변경될 때 해당 테넌트의 캐시 키만 무효화해야 한다. 테넌트 ID 없이 만든 캐시 키는 정확히 어떤 키를 무효화해야 하는지 알 수 없어서 전체 플러시를 하거나 TTL만 믿게 된다.

Memcached는 Redis와 달리 패턴으로 키를 조회하거나 삭제하는 기능이 없다. 테넌트 컨텍스트가 포함된 명시적인 키 설계가 더 중요하다.

---

## 비동기 작업에서의 테넌트 컨텍스트 누락

요청-응답 사이클에서는 미들웨어가 테넌트 컨텍스트를 세션이나 헤더에서 추출해서 주입하는 구조가 보통 잘 작동한다. 문제는 Celery, RQ 같은 비동기 작업 큐나 이벤트 리스너에서 이 컨텍스트가 전달되지 않는 경우다.

```python
# 취약한 Celery 태스크 - 테넌트 컨텍스트가 없다
@celery.task
def generate_monthly_report():
    # 어느 테넌트의 데이터를 처리하는가?
    all_users = db.query("SELECT * FROM users")
    for user in all_users:
        # 테넌트 구분 없이 전체 유저 처리
        process_user(user)
```

스케줄러에서 정기적으로 실행되는 태스크가 테넌트 필터 없이 전체 데이터를 조회하면, 한 테넌트의 처리 결과가 다른 테넌트 데이터에 영향을 미치거나, 잘못된 테넌트에게 이메일이 전송되는 일이 생긴다.

비동기 태스크에 테넌트 컨텍스트를 전달하는 방법은 태스크 파라미터로 명시적으로 넘기는 것이다.

```python
# 태스크 파라미터에 tenant_id를 명시한다
@celery.task
def generate_monthly_report(tenant_id: str):
    users = db.query(
        "SELECT * FROM users WHERE tenant_id = :tenant_id",
        {"tenant_id": tenant_id}
    )
    for user in users:
        process_user(user, tenant_id=tenant_id)

# 스케줄러에서 테넌트별로 태스크를 생성한다
def schedule_monthly_reports():
    tenants = db.query("SELECT id FROM tenants WHERE active = true")
    for tenant in tenants:
        generate_monthly_report.apply_async(args=[tenant.id])
```

이벤트 드리븐 아키텍처에서는 이벤트 페이로드에 `tenant_id`를 포함하는 것이 표준이다. 이벤트 발행 시점에 테넌트 컨텍스트를 잃어버리면 이벤트 소비자 쪽에서 복구할 방법이 없다.

```python
# 이벤트 페이로드에 tenant_id 포함
event = {
    "event_type": "order.created",
    "tenant_id": current_tenant_id,  # 반드시 포함
    "payload": {
        "order_id": order.id,
        "user_id": user.id,
    },
    "timestamp": datetime.utcnow().isoformat(),
}
await event_bus.publish("orders", event)
```

Python의 `contextvars`를 사용하면 비동기 컨텍스트에서 테넌트 정보를 thread-safe하게 전파할 수 있다. 단, `asyncio` 컨텍스트 내에서만 유효하고 Celery worker 프로세스로는 자동으로 전달되지 않는다.

```python
from contextvars import ContextVar

current_tenant_id: ContextVar[str] = ContextVar('current_tenant_id')

# FastAPI 미들웨어에서 설정
@app.middleware("http")
async def set_tenant_context(request: Request, call_next):
    tenant_id = extract_tenant_from_request(request)
    token = current_tenant_id.set(tenant_id)
    try:
        response = await call_next(request)
    finally:
        current_tenant_id.reset(token)
    return response

# 서비스 레이어에서 사용
def get_current_tenant() -> str:
    try:
        return current_tenant_id.get()
    except LookupError:
        raise RuntimeError("Tenant context not set - this code must be called within a request context")
```

비동기 태스크에서 `contextvars`를 믿고 구현하면 태스크가 요청 컨텍스트 밖에서 실행될 때 `LookupError`가 발생하거나 잘못된 컨텍스트를 참조한다. 태스크 파라미터로 명시적으로 전달하는 게 더 안전하다.

---

## S3/파일 스토리지 경로 분리 실패

S3에서 멀티테넌트 파일을 저장할 때 경로 설계가 잘못되면 테넌트 간 파일 접근이 가능해진다.

```
# 취약한 경로 구조 - 테넌트 ID가 없거나 예측 가능하다
s3://my-bucket/uploads/profile.webp
s3://my-bucket/uploads/2024/01/report.pdf
s3://my-bucket/tenant1/uploads/file.pdf  # 테넌트명이 추측 가능
```

경로에 테넌트 ID가 없으면 Presigned URL이나 버킷 정책이 있더라도 경로를 추측해서 접근할 수 있다. 특히 테넌트명이 서브도메인이나 URL에 노출되는 경우 경로 구성이 자명해진다.

```
# 안전한 경로 구조
s3://my-bucket/{tenant_uuid}/uploads/{file_uuid}.pdf
s3://my-bucket/{tenant_uuid}/reports/2024/01/{report_uuid}.pdf
```

UUID 기반 경로로 바꾸면 경로를 추측하기 어렵다. 여기에 Presigned URL의 만료 시간을 짧게 가져가면 URL 노출 시 피해 범위를 줄인다.

```python
import boto3
from uuid import uuid4

s3 = boto3.client('s3')

def upload_tenant_file(tenant_id: str, file_content: bytes, filename: str) -> str:
    file_uuid = str(uuid4())
    # 파일명에서 경로 순회(path traversal) 방어
    safe_extension = Path(filename).suffix.lstrip('.')[:10]
    object_key = f"{tenant_id}/uploads/{file_uuid}.{safe_extension}"

    s3.put_object(
        Bucket='my-bucket',
        Key=object_key,
        Body=file_content,
        Metadata={'tenant_id': tenant_id},
    )
    return object_key


def generate_download_url(tenant_id: str, object_key: str, expires_in: int = 300) -> str:
    # 요청한 테넌트의 경로인지 검증
    if not object_key.startswith(f"{tenant_id}/"):
        raise PermissionError(f"Object {object_key} does not belong to tenant {tenant_id}")

    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'my-bucket', 'Key': object_key},
        ExpiresIn=expires_in,
    )
    return url
```

`object_key.startswith(f"{tenant_id}/")`로 경로 소유권을 검증하는 부분이 중요하다. 이 검증이 없으면 클라이언트가 다른 테넌트의 `object_key`를 넘겨서 Presigned URL을 발급받을 수 있다.

S3 버킷 정책으로 추가 방어를 넣을 수도 있다. IAM 조건 키로 특정 경로 프리픽스에만 접근을 허용하는 방식이다.

```json
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::123456789012:role/AppRole"},
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::my-bucket/${aws:PrincipalTag/TenantId}/*",
  "Condition": {
    "StringEquals": {
      "aws:PrincipalTag/TenantId": "${aws:PrincipalTag/TenantId}"
    }
  }
}
```

실제로 이 방식은 IAM 역할에 `TenantId` 태그를 붙이는 방식이라서, 단일 역할로 모든 테넌트를 처리하는 구조에서는 적용하기 어렵다. 테넌트별 역할을 생성하거나 STS Assume Role을 조합해야 하는데, 그 자체로 관리 복잡도가 올라간다.

---

## 공통 방어 패턴

각 유출 경로를 막는 방어 기법은 다르지만, 공통적으로 지켜야 하는 원칙이 있다.

테넌트 소유권 검증은 항상 서버 사이드에서 수행한다. 클라이언트가 넘긴 `tenant_id`를 그대로 신뢰하지 않는다. 세션이나 JWT에서 테넌트를 추출하고, 요청 파라미터의 테넌트 ID와 대조한다.

```python
# JWT에서 테넌트를 추출하고 요청 파라미터와 대조
@app.get("/api/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    request_tenant_id: str = Query(...),  # 클라이언트가 보낸 값
    current_user: User = Depends(get_current_user),  # JWT에서 추출
):
    # 클라이언트가 보낸 tenant_id는 무시하거나 검증용으로만 사용
    if request_tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403)

    # 실제 쿼리는 JWT 기반 tenant_id 사용
    invoice = await get_invoice_by_id(invoice_id, current_user.tenant_id)
    ...
```

DB 레벨에서 Row Level Security를 활성화하면 애플리케이션 버그로 테넌트 필터를 빠뜨렸을 때 최후의 방어선이 된다. 애플리케이션이 RLS를 맹신해서 소유권 검사를 생략하는 것은 별개의 문제이기 때문에, RLS는 보완재이지 대체재가 아니다.

침투 테스트에서 크로스 테넌트 유출을 테스트할 때는 두 테넌트 계정을 만들고, 테넌트 A로 생성한 리소스 ID를 테넌트 B 세션으로 조회하는 것이 기본이다. 이 테스트를 CI/CD에 포함시키는 것이 효과적이다.

```python
# pytest 기반 크로스 테넌트 격리 테스트
async def test_report_cross_tenant_isolation(client, tenant_a_token, tenant_b_token):
    # 테넌트 A로 리포트 생성
    response = await client.post(
        "/api/reports",
        json={"title": "Tenant A Report"},
        headers={"Authorization": f"Bearer {tenant_a_token}"},
    )
    report_id = response.json()["id"]

    # 테넌트 B 세션으로 동일 리포트 접근 시도
    response = await client.get(
        f"/api/reports/{report_id}",
        headers={"Authorization": f"Bearer {tenant_b_token}"},
    )
    assert response.status_code == 404  # 403도 아닌 404여야 한다
```

이 테스트 패턴을 핵심 리소스 엔드포인트마다 작성해두면, IDOR 취약점이 릴리즈 전에 걸린다.
