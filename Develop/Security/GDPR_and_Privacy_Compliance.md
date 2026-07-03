---
title: GDPR과 개인정보 컴플라이언스
tags: [gdpr, ccpa, 개인정보보호법, privacy, consent, dpia, dpo, data-subject-rights, cross-border-transfer, breach-notification, compliance, security]
updated: 2026-06-04
---

# GDPR과 개인정보 컴플라이언스

법무팀이 "이번에 GDPR 대응해야 합니다"라고 말하는 순간 개발팀이 떠올리는 건 보통 두 가지다. 쿠키 배너 띄우고 "내 정보 삭제" 버튼 만들면 되는 거 아니냐, 아니면 우리 서비스 한국인만 쓰는데 왜 우리가 GDPR을 신경 쓰냐. 둘 다 위험한 오해다. EU 거주자가 우리 서비스에 한 명이라도 가입하는 순간 GDPR 적용 대상이 되고, 쿠키 배너는 컴플라이언스의 표면이지 본질이 아니다.

실제로 컴플라이언스가 시스템 설계를 흔드는 지점은 따로 있다. 회원 한 명이 삭제를 요청했을 때 그 사람의 데이터가 몇 개의 마이크로서비스, 몇 개의 백업 스냅샷, 몇 개의 분석 파이프라인, 몇 개의 외부 SaaS에 흩어져 있는지 답할 수 있는가. 동의를 받았다는 증거를 5년 뒤에도 제출할 수 있는가. EU에서 수집한 데이터가 미국 리전에 복제될 때 적법한 근거가 있는가. 침해가 발생했을 때 72시간 안에 감독기관에 신고할 절차가 작동하는가. 이 질문들이 GDPR의 진짜 어려움이다.

이 문서는 법 해석이 아니라 백엔드 엔지니어가 컴플라이언스를 어떻게 시스템에 녹여 넣는지를 다룬다. PII 비식별 기법 자체는 [PII 데이터 보호](./PII_Data_Protection.md)에서 다루므로 여기서는 반복하지 않고, 법적 요구를 코드와 운영 절차로 옮기는 부분에 집중한다.

## 세 가지 법의 비교 — GDPR, CCPA, 개인정보보호법

법조문을 줄줄 외울 필요는 없지만, 설계 결정을 바꾸는 차이는 알아야 한다. 같은 "삭제권"이라도 법마다 적용 대상과 예외가 달라서, 우리가 한 명의 사용자 데이터를 지우는 처리 코드가 모든 법을 동시에 만족하지 못하는 경우가 생긴다.

### 적용 범위와 역외적용

**GDPR**(EU 일반개인정보보호규정)은 EU에 사업장이 있는 컨트롤러뿐 아니라, EU 거주자에게 재화·서비스를 제공하거나 그들의 행동을 모니터링하는 모든 사업자에게 적용된다. 한국에서 운영하는 영문 사이트가 EU에서 결제를 받으면 적용 대상이다. 위반 시 과징금은 전 세계 매출의 4% 또는 2천만 유로 중 큰 금액이다.

**CCPA/CPRA**(캘리포니아 소비자 프라이버시법)는 캘리포니아 거주자에게 적용된다. 회사 단위 임계치가 있다는 점이 GDPR과 다르다. 연 매출 2,500만 달러 이상이거나, 10만 명 이상의 캘리포니아 거주자 정보를 처리하거나, 매출의 50% 이상이 개인정보 판매에서 나오는 사업자가 대상이다. CPRA(2023년 발효)는 CCPA를 강화한 개정안이고 실무에서는 보통 묶어서 부른다.

**한국 개인정보보호법**은 국내에서 개인정보를 처리하는 모든 사업자에게 적용된다. 한국 거주자의 데이터를 처리하는 해외 사업자도 일정 요건을 충족하면 적용된다. 정보통신서비스 제공자에 대한 특례 조항이 따로 있었지만 2023년 개정으로 일반 규정에 통합됐다.

### 핵심 권리와 의무 비교

| 영역 | GDPR | CCPA/CPRA | 개인정보보호법 |
|---|---|---|---|
| 처리 근거 | 6가지 법적 근거(동의·계약 이행·법적 의무·생명보호·공익·정당한 이익) | 통지 기반 — 사전 동의는 미성년자·민감정보 등 제한적 경우만 | 원칙적으로 정보주체 동의, 그 외 법령상 근거 |
| 옵트인 vs 옵트아웃 | 옵트인(사전 동의) | 옵트아웃(판매·공유 거부권) | 옵트인 |
| 열람권 | 인정(제15조) | 인정(Right to Know) | 인정(제35조) |
| 삭제권 | 인정(제17조), 예외 다수 | 인정(Right to Delete) | 인정(제36조) |
| 이동권 | 인정(제20조) | 인정(Right to Portability) | 부분 인정 — 마이데이터 도입 분야 위주 |
| 자동화된 의사결정 거부 | 인정(제22조) | 제한적 인정 | 인정(2023년 개정) |
| 침해 통지 | 72시간 내 감독기관, 고위험 시 정보주체 | 합리적 기간 내 | 72시간 내 개인정보위원회·KISA, 정보주체 통지 |
| 과징금 최고액 | 전 세계 매출 4% 또는 2천만 유로 | 위반 건당 최대 $7,500(고의) | 전체 매출 3% 이하 |
| DPO 의무 | 일정 요건 시 의무 | 의무 아님(권장) | 개인정보 보호책임자 지정 의무 |

실무에서 가장 자주 마주치는 함정은 동의의 방향이 반대라는 점이다. GDPR과 한국법은 "동의 받기 전엔 안 됨"이고, CCPA는 "거부 안 했으면 됨"이다. 한 시스템에서 두 법을 동시에 만족시키려면 사용자 지역(jurisdiction)을 식별해서 동의 플로우를 분기해야 한다.

```python
from enum import Enum

class Jurisdiction(Enum):
    EU_EEA = "eu_eea"           # GDPR 옵트인
    UK = "uk"                   # UK GDPR 옵트인
    CALIFORNIA = "ca"           # CCPA 옵트아웃
    KOREA = "kr"                # 옵트인
    OTHER = "other"             # 회사 기본 정책

def resolve_consent_mode(jurisdiction: Jurisdiction, purpose: str) -> str:
    # purpose: marketing, analytics, personalization, essential
    if purpose == "essential":
        return "no_consent_required"  # 서비스 제공에 필수

    if jurisdiction in (Jurisdiction.EU_EEA, Jurisdiction.UK, Jurisdiction.KOREA):
        return "opt_in_required"      # 동의 받기 전엔 처리 금지
    if jurisdiction == Jurisdiction.CALIFORNIA:
        # CCPA는 판매·공유 거부권 — 기본은 처리 가능, 거부 시 중단
        return "opt_out_available"
    return "opt_in_recommended"
```

이 함수가 단순해 보이지만 실제로는 jurisdiction을 어떻게 판정하느냐가 어렵다. IP 기반 GeoIP만으로 결정하면 VPN 사용자는 잘못 분류되고, 회원가입 시 자가 신고한 국가만으로는 거주지 변경을 못 따라간다. 결제 정보의 청구 주소, 디바이스 언어 설정, 회원 프로필 국가를 조합해 우선순위를 정하는 게 일반적이다.

## 동의 관리 — 받는 것보다 증명하는 것이 어렵다

GDPR이 요구하는 유효한 동의는 네 가지 조건을 모두 만족해야 한다. 자유롭게(freely given), 구체적으로(specific), 정보에 입각해서(informed), 명확하게(unambiguous). 한 줄로 정리하면 "회원가입 약관에 묻혀 있는 체크박스로 받은 동의는 동의가 아니다".

실무에서 자주 보이는 안티패턴부터 짚자.

- 회원가입 동의 체크박스 하나로 마케팅 이메일, 행동 분석, 광고 쿠키, 위치 추적을 한꺼번에 받는다 — specific 위반.
- 체크박스가 기본으로 체크되어 있다 — unambiguous 위반. GDPR은 "pre-ticked box is not consent"를 명시한다.
- "동의하지 않으면 서비스를 이용할 수 없습니다"로 강제한다 — freely given 위반. 서비스 제공에 필수 목적이 아닌 처리는 거부할 수 있어야 한다.
- 동의 받은 시점, 받은 내용, 동의서 버전을 기록하지 않는다 — 입증 불가. 감독기관 조사에서 동의를 받았다는 사실을 컨트롤러가 입증해야 한다(제7조 1항).

### 동의 레코드 스키마

동의는 "받은 사실"보다 "어떤 조건으로 받았는지"를 기록하는 게 핵심이다. 약관이 개정되면 새 동의가 필요한지 판단하려면 동의 시점의 약관 버전을 알아야 한다.

```sql
CREATE TABLE consent_records (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    purpose         VARCHAR(64) NOT NULL,        -- marketing_email, analytics, ad_targeting 등
    granted         BOOLEAN NOT NULL,            -- true=동의, false=거부·철회
    legal_basis     VARCHAR(32) NOT NULL,        -- consent, contract, legitimate_interest, legal_obligation
    policy_version  VARCHAR(32) NOT NULL,        -- 동의 시점의 약관 버전 — privacy_policy_v3.2 등
    consent_text_hash CHAR(64) NOT NULL,         -- 표시한 동의 문구의 sha256
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,                 -- 동의 유효기간 — 한국법은 정기 갱신 권장
    revoked_at      TIMESTAMPTZ,                 -- 철회 시각 — 레코드를 새로 쌓지 않고 갱신하는 경우
    source          VARCHAR(32) NOT NULL,        -- signup, settings_page, banner, mobile_app
    ip_addr         INET,
    user_agent      TEXT,
    request_id      UUID NOT NULL                -- 감사용 — 동의 시점의 요청을 역추적
);

CREATE INDEX idx_consent_user_purpose ON consent_records (user_id, purpose, collected_at DESC);
```

이 스키마의 핵심은 동의 레코드를 갱신하지 않고 append-only로 쌓는다는 점이다. 사용자가 마케팅 동의를 받았다가 6개월 뒤 철회했다가 다시 동의하면 레코드가 세 개 쌓인다. 가장 최근 레코드의 `granted` 값이 현재 상태고, 이전 레코드는 감사 증거다. UPDATE로 덮어쓰면 "언제 동의 철회했는지" 같은 질문에 답할 수 없다.

### 동의 조회는 캐시가 함정

동의 상태를 매 요청마다 DB에서 읽으면 부하가 크다. 그렇다고 캐시하면 철회가 즉시 반영 안 된다. 마케팅 메일을 발송하는 배치가 30분짜리 캐시를 보면, 사용자가 방금 거부했어도 그 배치는 메일을 보낸다.

```python
import redis
from datetime import datetime

class ConsentService:
    def __init__(self, db, cache: redis.Redis):
        self.db = db
        self.cache = cache

    def is_granted(self, user_id: int, purpose: str) -> bool:
        # 캐시 — 짧은 TTL로 부하 줄이되 철회 지연을 받아들임
        key = f"consent:{user_id}:{purpose}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached == b"1"

        granted = self._read_from_db(user_id, purpose)
        # TTL은 길게 잡지 마라 — 마케팅 발송 직전엔 캐시 무시 필수
        self.cache.setex(key, 60, "1" if granted else "0")
        return granted

    def revoke(self, user_id: int, purpose: str, request_id: str):
        # 철회 시 캐시 즉시 무효화
        self._append_record(user_id, purpose, granted=False, request_id=request_id)
        self.cache.delete(f"consent:{user_id}:{purpose}")

    def is_granted_strict(self, user_id: int, purpose: str) -> bool:
        # 마케팅 발송·광고 송출 직전엔 캐시 우회
        return self._read_from_db(user_id, purpose)
```

캐시 TTL은 동의 철회를 얼마나 빠르게 반영해야 하는지에 따라 결정한다. UI에서는 1분 캐시도 괜찮지만, 외부로 데이터를 전송하는 배치는 항상 DB를 직접 읽게 만든다. 실수로 캐시 결과를 보고 메일을 보내면 그 한 통이 GDPR 위반 사실이 된다.

### 동의 문구 변경 — 재동의가 필요한가

약관을 바꿀 때마다 전 회원에게 재동의를 받으면 사용자 경험이 망가지고, 안 받으면 컴플라이언스 리스크가 생긴다. 판단 기준은 "동의의 본질이 바뀌었는가"다.

- 처리 목적 추가(예: 분석 → 분석 + 광고 타게팅) → 재동의 필요
- 처리 주체 변경(컨트롤러 또는 수탁자 변경) → 재동의 필요
- 표현 명확화·오탈자 수정 → 재동의 불필요, 정책 버전만 올림
- 보유 기간 연장 → 재동의 필요

코드 관점에선 `policy_version` 컬럼을 두고, 정책 변경 시 버전 번호와 함께 "재동의 필요 여부" 플래그를 같이 관리하는 게 깔끔하다.

```python
class PolicyVersion:
    def __init__(self, version: str, purposes_added: list[str], reconsent_required: bool):
        self.version = version
        self.purposes_added = purposes_added
        self.reconsent_required = reconsent_required

def needs_reconsent(user_consent_version: str, current_version: PolicyVersion) -> bool:
    # 이전 동의 버전과 비교해 재동의가 필요한 변경이 있었는지 판단
    if user_consent_version == current_version.version:
        return False
    return current_version.reconsent_required
```

## 데이터 주체 권리 — 열람, 삭제, 이동의 실제 구현

법은 "사용자가 요청하면 응해야 한다"고 말하지만, 그 응답을 만드는 건 엔지니어다. 한 사용자의 데이터가 30개 마이크로서비스, 5개 데이터 웨어하우스, 3개 외부 SaaS, 6개월치 로그에 흩어져 있을 때 이 요청에 응답하는 게 컴플라이언스의 진짜 난도다.

### 열람권 — 데이터 인벤토리가 없으면 답할 수 없다

사용자가 "내 데이터 다 보여달라"고 요청하면 우리가 그 사람에 대해 보관하는 모든 항목을 모아 제공해야 한다. GDPR은 1개월 안에 응답하라고 한다. 한 달이라는 시간이 길어 보이지만, 데이터가 어디에 있는지 모르면 한 달도 부족하다.

선행 작업은 데이터 인벤토리다. 모든 PII 컬럼이 어느 테이블, 어느 서비스, 어느 외부 시스템에 있는지 카탈로그로 정리해두지 않으면 매 요청마다 인력으로 추적해야 한다.

```yaml
# data_inventory.yaml — 데이터 카탈로그 일부
users:
  service: account-service
  storage: postgres.users
  pii_fields:
    - { name: email, classification: identifier, retention_days: until_deletion }
    - { name: phone, classification: identifier, retention_days: until_deletion }
    - { name: birth_date, classification: quasi, retention_days: until_deletion }
  exported_to:
    - { destination: data-warehouse.dim_users, sync: daily }
    - { destination: mailchimp, sync: realtime, controller_type: processor }

orders:
  service: order-service
  storage: postgres.orders
  pii_fields:
    - { name: shipping_address, classification: identifier, retention_days: 1825 }  # 5년 보관(전자상거래법)
  retention_reason: ecommerce_act_article_6
```

인벤토리가 있으면 열람권 응답을 자동화할 수 있다. 사용자 ID 하나로 모든 서비스를 돌면서 데이터를 모은다.

```python
class DataSubjectAccessService:
    def __init__(self, inventory, service_clients):
        self.inventory = inventory
        self.clients = service_clients

    async def build_access_report(self, user_id: int) -> dict:
        report = {"user_id": user_id, "collected_at": datetime.utcnow().isoformat(), "data": {}}

        for entity_name, meta in self.inventory.items():
            service = meta["service"]
            client = self.clients[service]
            try:
                data = await client.fetch_user_data(user_id, entity_name)
                if data:
                    report["data"][entity_name] = {
                        "fields": data,
                        "source": meta["storage"],
                        "retention": meta.get("retention_reason", "until_deletion"),
                    }
            except ServiceUnavailable:
                # 한 서비스가 죽었다고 전체 응답을 못 만들면 안 됨 — 부분 응답 후 재시도
                report["data"][entity_name] = {"error": "temporarily_unavailable"}

        return report
```

외부 SaaS(메일침프, 인터콤, 세그먼트 등)에 보낸 데이터도 포함해야 한다는 점을 놓치면 안 된다. 우리가 컨트롤러이고 그 SaaS가 프로세서면, 프로세서가 보유한 데이터도 우리 책임 범위다.

### 삭제권 — soft delete만으론 부족하다

이게 가장 어렵다. "사용자를 지운다"는 게 단순히 `users.deleted_at = now()`를 찍는 게 아니기 때문이다. GDPR 제17조 삭제권은 "지체 없이 삭제"를 요구하고, 한국법도 비슷하다. 동시에 법적 보관 의무가 있는 데이터(전자상거래법상 거래 기록 5년 등)는 지우면 안 된다.

설계는 데이터 항목별 보관 의무를 명확히 분리하는 데서 출발한다.

```python
from enum import Enum

class DeletionPolicy(Enum):
    PURGE = "purge"                        # 완전 삭제
    ANONYMIZE = "anonymize"                # 식별자만 제거, 통계용 비식별 데이터로 보존
    RETAIN = "retain"                      # 법적 의무로 보존
    CRYPTO_SHRED = "crypto_shred"          # 암호화 키 파기로 사실상 삭제

DELETION_RULES = {
    "users.email":            DeletionPolicy.PURGE,
    "users.name":             DeletionPolicy.PURGE,
    "users.birth_date":       DeletionPolicy.PURGE,
    "orders.user_id":         DeletionPolicy.ANONYMIZE,    # 거래 기록은 보존, 사용자 연결만 끊음
    "orders.shipping_addr":   DeletionPolicy.RETAIN,       # 전자상거래법 5년
    "audit_logs.actor_id":    DeletionPolicy.ANONYMIZE,
    "backup_snapshots.*":     DeletionPolicy.CRYPTO_SHRED, # 백업은 키 폐기로 무력화
}
```

여러 마이크로서비스에 흩어진 데이터를 동시에 지우려면 분산 트랜잭션이 필요한데, 실무에서는 보통 이벤트 기반으로 처리한다. 삭제 요청을 이벤트로 발행하고, 각 서비스가 자기 데이터를 지운 뒤 완료 이벤트를 회신한다.

```python
class DeletionOrchestrator:
    def __init__(self, event_bus, inventory):
        self.event_bus = event_bus
        self.inventory = inventory

    async def request_deletion(self, user_id: int, request_id: str):
        # 삭제 요청을 영구 레코드로 남김 — 감사 증거
        await self._record_request(user_id, request_id)

        # 인벤토리상 사용자 데이터를 가진 모든 서비스에 이벤트 발행
        services = self._find_services_with_user_data(user_id)
        for service in services:
            await self.event_bus.publish(
                topic="user.deletion.requested",
                key=str(user_id),
                payload={
                    "user_id": user_id,
                    "request_id": request_id,
                    "deadline": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                },
            )

    async def on_service_completed(self, event: dict):
        # 각 서비스가 완료 이벤트를 회신하면 진행률 갱신
        await self._mark_service_done(event["request_id"], event["service"])

        if await self._all_services_done(event["request_id"]):
            await self._finalize_deletion(event["request_id"])
```

이 패턴의 핵심은 멱등성이다. 한 서비스가 이벤트를 두 번 받아도 같은 결과가 나와야 한다. 이미 삭제된 사용자에 대한 삭제 이벤트가 와도 에러 없이 "이미 처리됨"으로 응답해야 한다.

백업 처리는 별도 영역이다. 매일 찍는 DB 스냅샷을 한 사용자 때문에 매번 재구성할 수는 없다. 두 가지 접근이 있다.

첫째, **암호 파쇄(crypto-shredding)**. 사용자별 데이터 암호화 키를 따로 두고, 삭제 요청 시 그 키만 파기한다. 백업에 데이터가 남아 있어도 키가 없으니 복호화 불가능, 사실상 삭제로 인정받는다. GDPR 가이드라인에서도 이 방식을 수용한다.

둘째, **백업 격리와 보존 기간 단축**. 운영 데이터는 즉시 삭제, 백업은 최대 보존 기간(예: 30일) 안에 자연 소멸. 그동안 백업에 접근할 수 있는 사람을 엄격히 제한하고 접근 로그를 남긴다. 삭제 요청자에게는 "운영 데이터는 즉시 삭제됐고, 백업은 N일 안에 사이클 종료"라고 안내한다.

### 이동권 — 기계가 읽을 수 있는 형식

이동권(GDPR 제20조)은 사용자가 자기 데이터를 "구조화되고, 일반적으로 사용되며, 기계가 읽을 수 있는 형식"으로 받아 다른 컨트롤러로 옮길 수 있게 하라는 권리다. JSON이나 CSV가 일반적이다. 열람권과 다른 점은 "다른 시스템으로 옮길 수 있어야" 한다는 부분 — PDF나 캡처 이미지로는 안 된다.

```python
def export_user_data_portable(user_id: int) -> dict:
    return {
        "schema_version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "profile": {
            "email": fetch_email(user_id),
            "name": fetch_name(user_id),
            "created_at": fetch_signup_date(user_id).isoformat(),
        },
        "orders": [
            {
                "order_id": o.id,
                "ordered_at": o.created_at.isoformat(),
                "items": [{"sku": i.sku, "name": i.name, "price": str(i.price)} for i in o.items],
            }
            for o in fetch_orders(user_id)
        ],
        "preferences": fetch_preferences(user_id),
    }
```

이동권은 "사용자가 직접 입력했거나 활동으로 생성한 데이터"에만 적용되고, 회사가 분석·추론으로 만들어낸 데이터(예: 추천 점수, 신용 등급)는 대상이 아니라는 점을 정확히 짚어야 한다. 모든 걸 다 내보내면 영업비밀 노출 리스크가 생긴다.

## DPO와 거버넌스

**DPO(Data Protection Officer, 개인정보 보호책임자)**는 컴플라이언스의 단일 책임자다. GDPR 제37조는 공공기관, 대규모 민감정보 처리, 대규모 감시 활동을 하는 사업자에게 DPO 지정을 의무화한다. 한국법은 모든 개인정보처리자에게 개인정보 보호책임자 지정을 요구한다.

DPO가 엔지니어링에 미치는 실질적 영향은 두 가지다.

첫째, **사전 검토 프로세스**. 신규 기능이 개인정보 처리 방식을 바꿀 때(새로운 데이터 항목 수집, 새 외부 처리자 추가, 처리 목적 변경) DPO 검토를 받는 게 일반적이다. 코드 리뷰처럼 PR에 "privacy review" 체크포인트를 두는 회사도 많다.

둘째, **감독기관과의 단일 창구**. 침해 신고, 정보주체 민원, 감독기관 조사에 회사를 대표해 응대한다. 엔지니어 입장에서는 침해 의심 사고가 났을 때 누구한테 첫 보고를 해야 하는지 명확해진다는 의미다.

DPO는 독립성이 요구된다 — 처리 활동에 대한 결정권을 가진 사람(예: 마케팅 임원)이 DPO를 겸직하면 이해 충돌이다. 외부 위탁(외부 로펌이나 컨설팅사의 DPO 서비스)도 GDPR이 인정한다.

## DPIA — 개인정보 영향평가

**DPIA(Data Protection Impact Assessment)**는 GDPR 제35조가 요구하는 사전 위험평가다. "고위험" 처리를 시작하기 전에 위험을 분석하고 완화 조치를 문서로 남겨야 한다. 한국에는 공공기관 대상으로 비슷한 개인정보 영향평가 제도가 있다.

고위험으로 자동 분류되는 케이스가 있다.

- 자동화된 의사결정으로 개인에 법적·중대한 영향을 미치는 경우(신용평가, 채용 자동 스크리닝)
- 민감정보의 대규모 처리(병원 진료 기록, 종교·정치 성향)
- 공개 장소의 대규모 체계적 모니터링(CCTV 분석, 도시 단위 위치 추적)
- 새로운 기술 도입(생체 인식, 대규모 AI 프로파일링)

DPIA는 양식이 정해진 건 아니지만 GDPR 제35조 7항이 최소 포함 항목을 정한다. 처리의 목적과 방법 기술, 필요성과 비례성 평가, 위험 분석, 위험 완화 대책. 이걸 엔지니어가 작성해야 할 때는 다음 구조가 실용적이다.

```markdown
## DPIA — 추천 시스템 도입

### 1. 처리 개요
- 목적: 개인화 콘텐츠 추천
- 처리 데이터: 시청 이력, 검색어, 위치(국가 단위), 디바이스 정보
- 처리 근거: 정당한 이익(legitimate interest)
- 보유 기간: 12개월 rolling window
- 처리자: 사내 ML 팀, AWS SageMaker(프로세서)

### 2. 필요성·비례성
- 더 적은 데이터로 동일 목적 달성 불가 여부: 위치는 국가 단위로 충분, 시 단위 수집 불필요
- 데이터 최소화 조치: 검색어는 30일 후 해시화

### 3. 위험 분석
| 위험 | 가능성 | 영향 | 등급 |
|---|---|---|---|
| 모델 추론으로 민감 속성 노출(종교·정치 성향) | 중 | 고 | 고 |
| 데이터 유출 시 시청 패턴 노출 | 저 | 중 | 중 |
| 자동 추천으로 인한 필터 버블 | 고 | 저 | 저 |

### 4. 완화 조치
- 모델 입력에서 검색어 hashing
- 민감 카테고리(종교·정치) 추천 제외 룰
- 추천 거부 옵션(opt-out) UI 제공
- 추천 근거 설명 기능(Article 22 대응)

### 5. 잔여 위험 평가
- 잔여 위험 수준: 중
- 감독기관 사전 협의 필요 여부: 불필요(GDPR 제36조 임계 미만)
```

DPIA는 한 번 쓰고 끝이 아니라 처리 방식이 바뀔 때마다 갱신해야 한다. 추천 모델에 새로운 피처를 넣을 때, 새 데이터 소스를 붙일 때, 보유 기간을 연장할 때 모두 재평가 대상이다.

## 데이터 위치 제약과 국외이전

EU에서 수집한 데이터를 미국 리전에 저장하면 그게 국외이전이다. GDPR은 EEA(EU+노르웨이·아이슬란드·리히텐슈타인) 밖으로의 이전을 원칙적으로 제한하고, 적법한 근거가 있을 때만 허용한다.

### 적법한 이전 근거

**적정성 결정(adequacy decision)**이 있는 국가로의 이전이 가장 간단하다. EU 집행위원회가 "그 나라 법이 GDPR 수준의 보호를 제공한다"고 인정한 국가다. 영국, 일본, 한국, 캐나다, 스위스 등이 포함된다. 미국은 EU-US Data Privacy Framework(2023년 발효)에 가입한 사업자에 한해 적정성이 인정된다.

적정성 결정이 없는 국가로 이전하려면 **표준계약조항(SCCs, Standard Contractual Clauses)**을 체결한다. EU 집행위가 공개한 표준 계약 문안을 컨트롤러와 데이터 수입자가 서명하는 방식이다. 거기에 더해 **보충 조치(supplementary measures)**가 필요할 수 있다 — 수입 국가의 감시 법령 등을 평가한 뒤(TIA, Transfer Impact Assessment) 암호화·가명화 같은 기술 조치를 추가하는 식이다.

엔지니어가 결정에 직접 관여하는 부분은 보충 조치다. SCC가 깔려 있어도 미국 정부의 정보 접근 권한 같은 리스크가 남으면 "이전 자체를 막거나, 추가 기술 조치로 보완하라"는 결론이 난다. 실무에서는 다음 조치가 자주 동원된다.

- **이전 전 가명화**: 식별자를 EU 안에서 제거한 뒤 비식별 데이터만 이전
- **이전 데이터 암호화 + 키 EU 보관**: 데이터는 미국 클라우드에, 키는 EU 안의 KMS에. 미국 정부가 데이터에 접근해도 키가 없어 복호화 불가
- **데이터 잔류(data residency) 강제**: EU 사용자 데이터는 EU 리전에서 떠나지 않게 강제. 클라우드 서비스 선택과 멀티 리전 구성으로 강제

```hcl
# Terraform — AWS RDS를 EU 리전에 강제 배치, 복제도 EU 안에서만
resource "aws_db_instance" "eu_users" {
  identifier          = "users-eu"
  engine              = "postgres"
  region              = "eu-central-1"
  multi_az            = true
  backup_retention_period = 7

  # 백업 복사 대상도 EU 리전으로 한정
  replicate_source_db = aws_db_instance.eu_users_replica.identifier
}

resource "aws_db_instance" "eu_users_replica" {
  identifier = "users-eu-replica"
  region     = "eu-west-1"   # 같은 EEA 안
}
```

### 데이터 위치 강제는 코드 레벨에서도 점검해야 한다

인프라 레벨로 리전을 분리해도, 애플리케이션 코드가 실수로 EU 데이터를 글로벌 캐시·로그·메트릭으로 흘릴 수 있다. 이게 컴플라이언스 실패의 흔한 경로다.

```python
# 위험한 패턴 — 모든 사용자 데이터를 글로벌 캐시에 넣음
def get_user(user_id: int):
    key = f"user:{user_id}"
    cached = global_redis.get(key)   # 글로벌 Redis — 위치 모름
    if cached:
        return cached
    user = db.fetch(user_id)
    global_redis.setex(key, 300, user)
    return user

# 개선 — 사용자 거주 리전 기반으로 캐시 라우팅
def get_user(user_id: int):
    region = resolve_user_region(user_id)
    redis = REGIONAL_REDIS[region]   # eu-central-1, us-east-1 별 분리
    cached = redis.get(f"user:{user_id}")
    if cached:
        return cached
    user = regional_db[region].fetch(user_id)
    redis.setex(f"user:{user_id}", 300, user)
    return user
```

로그도 마찬가지다. EU 사용자의 요청 로그가 미국 데이터독에 흘러가면 그것도 이전이다. 로그 수집기를 리전별로 분리하거나, 로그에서 PII를 마스킹한 뒤 전송하는 게 표준 패턴이다.

## 침해 통지 — 72시간의 의미

GDPR 제33조는 개인정보 침해를 알게 된 시점부터 72시간 안에 감독기관에 신고하라고 정한다. 한국 개인정보보호법도 1,000명 이상 유출 시 72시간 안에 개인정보위원회와 KISA에 신고하고 정보주체에 통지하라고 한다. 침해 사실을 사용자에게도 알려야 한다(고위험인 경우, 지체 없이).

이 72시간을 압박으로 만드는 건 시간 자체보다 "알게 된 시점"이다. 보안팀이 의심 활동을 탐지한 순간인지, 침해가 확인된 순간인지가 모호하다. 보수적으로는 의심 시점부터 카운트다운이 시작된다고 봐야 한다.

### 침해 사고 대응 절차

침해 통지를 실제 72시간 안에 해내려면 사전 정비된 절차가 있어야 한다. 사고 터지고 절차 만들기 시작하면 늦는다. [Incident Response](./Incident_Response.md)에서 일반 사고 대응을 다루지만, 컴플라이언스 통지 트랙은 별도다.

```python
from datetime import datetime, timedelta

class BreachIncident:
    def __init__(self, incident_id: str, detected_at: datetime):
        self.incident_id = incident_id
        self.detected_at = detected_at
        self.notification_deadline = detected_at + timedelta(hours=72)
        self.status = "investigating"

    def assess_notifiable(self) -> dict:
        # GDPR 제33조 — 정보주체의 권리·자유에 위험이 있는지
        return {
            "supervisory_authority": True,                  # 원칙적으로 신고
            "data_subjects": self._is_high_risk(),          # 고위험일 때만 직접 통지
            "rationale": self._risk_assessment(),
        }

    def _is_high_risk(self) -> bool:
        # 식별자 + 민감정보, 또는 금융정보, 또는 대규모일 때 고위험
        return (
            "sensitive_category" in self.affected_data_types
            or "payment_card" in self.affected_data_types
            or self.affected_user_count >= 10000
        )
```

신고 내용은 GDPR 제33조 3항이 정한다. 침해의 성격, 영향 받은 정보주체 범주와 수, 영향 받은 기록의 종류와 수, DPO 연락처, 가능한 결과, 대응 조치. 72시간 안에 모든 정보를 갖추지 못해도 일단 신고하고 추가 정보는 단계적으로 제공할 수 있다(제33조 4항).

### 사용자 통지의 예외

모든 침해를 사용자에게 알려야 하는 건 아니다. GDPR 제34조 3항은 세 가지 예외를 둔다.

1. 침해 당시 적절한 보호 조치(예: 강한 암호화)가 적용되어 있어서 권리 침해 가능성이 낮은 경우
2. 사후 조치로 위험이 더 이상 존재하지 않게 된 경우
3. 개별 통지가 과도한 노력을 요구하는 경우(이때는 공개 통지로 대체)

여기서 "강한 암호화"가 면제 사유로 인정받으려면 침해 시점에 키가 침해자 손에 들어가지 않았다는 게 입증돼야 한다. DB 덤프가 유출됐는데 데이터가 AES-256으로 암호화되어 있고 키는 별도 HSM에 있었다면, 사용자 통지 의무가 면제될 수 있다. 키 관리를 분리해두는 게 단순한 보안 모범이 아니라 침해 발생 시 실질적 면책이 되는 이유다.

### 침해 통지 양식과 채널

감독기관별로 신고 양식이 정해져 있다. 한국은 개인정보위원회의 침해 신고 시스템(privacy.go.kr)으로 접수하고, 1,000명 이상 유출이면 KISA에도 동시 신고한다. EU는 각국 감독기관(아일랜드 DPC, 프랑스 CNIL 등)이 별도로 양식을 운영한다. 사고 터지고 양식 찾는 건 늦으니까, 각 관할 감독기관의 신고 채널과 양식 위치를 사전에 문서화해둔다.

사용자 통지는 명확하고 평이한 언어로 한다(GDPR 제34조 2항). 무슨 일이 일어났는지, 어떤 데이터가 영향받았는지, 사용자가 취할 수 있는 조치(비밀번호 변경 등), 회사가 취한 조치, 연락처를 포함한다.

## 실무 구현 패턴 정리

지금까지 다룬 요구들을 실제 시스템에 녹이려면 몇 가지 횡단 패턴이 필요하다.

### 데이터 분류 메타데이터의 강제

PII가 어느 컬럼·필드·로그에 있는지를 메타데이터로 강제하면 컴플라이언스 대응이 자동화된다. DB 컬럼 코멘트, 코드 어노테이션, 카탈로그 시스템 어디든 좋다.

```java
// Spring Boot — 필드에 PII 분류를 어노테이션으로 부착
public class User {
    @PII(category = "identifier", retention = "until_deletion")
    private String email;

    @PII(category = "identifier", sensitive = true, retention = "until_deletion")
    private String residentRegNo;

    @PII(category = "quasi", retention = "until_deletion")
    private LocalDate birthDate;

    // 비식별 — 어노테이션 없음
    private String displayName;
}
```

어노테이션이 붙은 필드는 로그 출력 시 자동 마스킹, 직렬화 시 별도 처리, 감사 로그 기록 등 횡단 관심사를 한꺼번에 처리한다. 새 필드를 추가했는데 분류 어노테이션이 없으면 빌드 단계에서 경고를 띄우는 식으로 강제할 수 있다.

### 삭제 가능성을 처음부터 설계

새 테이블을 만들 때 "이 데이터는 어떻게 지우는가"를 같이 정의한다. 외래 키 캐스케이드, 비식별화 로직, 백업 처리, 외부 시스템 전파를 미리 결정해두면 사용자가 삭제 요청했을 때 추적할 게 없다.

```sql
-- 새 테이블 — 삭제 정책 명시
CREATE TABLE user_activity_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    activity_type VARCHAR(64) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 컬럼 코멘트로 삭제 정책 명시
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE user_activity_logs IS
  'deletion_policy: anonymize_on_user_deletion, retention: 365 days';
COMMENT ON COLUMN user_activity_logs.user_id IS
  'pii:identifier, on_user_deletion: set_null';
```

### 동의·삭제 이벤트 표준화

마이크로서비스 환경에서 동의 변경과 삭제 요청은 도메인 이벤트로 표준화한다. 새 서비스가 추가될 때 이 이벤트만 구독하면 자동으로 컴플라이언스 흐름에 합류한다.

```json
{
  "event_type": "user.consent.revoked",
  "schema_version": "1.0",
  "user_id": 12345,
  "purpose": "marketing_email",
  "revoked_at": "2026-06-04T03:21:00Z",
  "request_id": "req_a8f3c2",
  "jurisdiction": "eu_eea"
}
```

새 마이크로서비스가 user.deletion.requested, user.consent.revoked 두 이벤트를 구독하지 않으면 운영 환경 배포를 막는 정책을 두는 회사도 있다.

### 감사 로그는 컴플라이언스의 증거

개인정보 처리 활동에 대한 감사 로그는 컴플라이언스의 증거다. 누가 언제 어떤 PII에 접근했는지, 동의는 언제 받았는지, 삭제는 언제 처리됐는지를 기록하지 않으면 "처리했다"는 사실을 입증할 방법이 없다. 감사 로그 자체가 PII를 포함할 수 있으니, 로그도 데이터 분류 대상이고 보관 기간 관리 대상이다.

상세는 [Security_Logging_and_Auditing](./Security_Logging_and_Auditing.md)에서 다룬다.

### 컴플라이언스 자동 점검

릴리스마다 컴플라이언스 체크를 수동으로 돌리는 건 지속 가능하지 않다. CI에 다음 점검을 박아두면 회귀를 잡는다.

- PII 분류 어노테이션 누락 검출
- 데이터 인벤토리에 없는 새 PII 컬럼 추가 차단
- 글로벌 캐시·로그에 PII 필드 직렬화 금지
- 동의 없이 수집되는 새 필드 추가 시 검토 게이트
- 외부 SaaS 신규 통합 시 DPA(Data Processing Agreement) 체결 여부 확인

자동화가 어려운 부분(DPIA, DPA 체결)은 수작업으로 남되, 자동화 가능한 부분을 코드 게이트로 막아두면 사람이 해야 할 일이 훨씬 줄어든다.

---

컴플라이언스는 보통 "법무팀 일"로 분류되지만, 실제로 코드와 데이터 구조를 바꾸는 건 엔지니어다. 동의 시점을 기록하는 스키마, 삭제 이벤트가 마이크로서비스를 가로지르는 토폴로지, 백업의 암호 파쇄, 리전 격리된 캐시 — 이런 게 GDPR 컴플라이언스의 실체다. 법조문은 결과를 정의하고, 구현은 우리가 한다.
