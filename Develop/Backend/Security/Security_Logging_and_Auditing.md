---
title: 보안 감사 로깅
tags: [security, audit-log, compliance, soc2, pci-dss, iso27001, worm, incident-response]
updated: 2026-08-03
---

# 보안 감사 로깅

감사 로그는 일반 애플리케이션 로그와 다르다. 디버깅용이 아니라 "누가, 언제, 무엇을, 어디서 했는지"를 법적으로 증명할 수 있어야 한다. 컴플라이언스 심사, 보안 사고 조사, 내부 감사 모두 이 로그에 의존한다.

---

## 컴플라이언스 프레임워크별 요구사항

### SOC 2

SOC 2는 서비스 조직의 보안·가용성·처리 무결성·기밀성·개인정보 보호를 다루는 미국 감사 기준이다. SaaS 기업이 엔터프라이즈 고객에게 판매하려면 대부분 SOC 2 Type II 인증을 요구받는다.

CC6.1(논리적 접근 제어), CC7.2(이상 탐지), CC7.3(사고 대응)에서 로그 요건을 규정한다. 심사자가 요구하는 최소 이벤트는 로그인 성공/실패 이력, 권한 있는 계정(admin, root, service account)의 모든 활동, 설정 변경 이력, 사용자 프로비저닝/디프로비저닝 이력, 데이터 접근 및 다운로드 이력이다. 보존 기간은 최소 1년이며 90일 이내 데이터는 즉시 조회 가능해야 한다.

SOC 2 심사자는 로그가 존재하는지만 확인하지 않는다. 실제로 로그를 조회해서 접근 패턴이 정책과 일치하는지, 의심스러운 활동에 알람이 발생했는지 확인한다. "로그가 있음"과 "로그를 활용한 탐지 체계가 있음"은 심사에서 다르게 평가된다.

### ISO 27001

ISO 27001은 정보보안 관리 체계(ISMS)에 관한 국제 표준이다. A.12.4(로깅 및 모니터링)에서 감사 로그를 명시적으로 요구한다.

A.12.4.1은 사용자 활동, 예외 사항, 정보보안 이벤트를 기록하도록 규정한다. 시스템 접근 시도(성공/실패), 관리자 권한 사용 이력, 보안 설정 변경, 시스템 시작/종료, 보호된 데이터 접근이 해당한다.

A.12.4.2는 로그 관리자 보호를 요구한다. 로그를 관리하는 관리자가 자신의 로그를 수정할 수 없어야 한다. 이 요건 때문에 로그 시스템은 별도 분리된 인프라에서 운영해야 한다. 로그 수집 서버와 애플리케이션 서버가 같은 IAM 권한을 공유하면 이 요건을 충족하지 못한다.

A.12.4.3은 관리자 및 운영자 로그를 일반 사용자 로그와 분리 보관하도록 요구한다. 같은 Elasticsearch 인덱스에 섞어두면 심사에서 지적받는다.

### PCI DSS

PCI DSS는 카드 결제 데이터를 처리하는 시스템에 적용되는 표준이다. 요구사항 10번 전체가 감사 로그를 다룬다.

요구사항 10.2는 반드시 기록해야 하는 이벤트를 열거한다. 카드 소유자 데이터 접근, root 또는 관리자 권한 사용, 감사 로그 접근, 로그인 실패 이력, 인증 및 식별 메커니즘 사용, 감사 로그 초기화·중단·일시 정지, 시스템 수준 객체 생성/삭제가 포함된다.

요구사항 10.3은 각 로그 엔트리의 최소 필드를 규정한다. 사용자 식별자, 이벤트 유형, 날짜·시간(UTC 권장), 성공/실패 여부, 이벤트 발생 원점(컴포넌트), 영향받은 데이터·시스템·리소스 식별자가 필수다.

PCI DSS의 보존 기간은 12개월이며 최근 3개월은 즉시 분석 가능해야 한다. 요구사항 10.5는 "감사 로그를 수정하거나 삭제하지 못하도록 보호"하도록 규정하는데, WORM 스토리지가 이 요건의 직접적인 해법이다.

---

## 무엇을 기록해야 하는가

컴플라이언스 요건을 충족하는 최소 이벤트 구조다. 모든 이벤트에 공통 필드(`timestamp`, `user_id`, `source_ip`, `request_id`)가 있어야 나중에 타임라인 재구성이 가능하다.

**인증 이벤트**

```json
{
  "event_type": "auth.login",
  "timestamp": "2026-08-03T04:12:33.421Z",
  "user_id": "usr_a1b2c3",
  "username": "alice@example.com",
  "source_ip": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "success": true,
  "mfa_used": true,
  "session_id": "sess_xyz789",
  "geo": { "country": "KR", "city": "Seoul" }
}
```

**권한 변경 이벤트**

```json
{
  "event_type": "iam.role.assigned",
  "timestamp": "2026-08-03T05:00:00.000Z",
  "actor_id": "usr_admin01",
  "target_user_id": "usr_a1b2c3",
  "role_before": ["viewer"],
  "role_after": ["viewer", "admin"],
  "approved_by": "usr_manager01",
  "expires_at": "2026-08-04T05:00:00.000Z"
}
```

`role_before` / `role_after` 양쪽을 모두 기록해야 한다. 변경 후 상태만 남기면 "어디서 왔는지"를 알 수 없어서 권한 상승 여부 판단이 어려워진다.

**데이터 접근 이벤트**

```json
{
  "event_type": "data.access",
  "timestamp": "2026-08-03T06:15:00.000Z",
  "user_id": "usr_a1b2c3",
  "resource_type": "customer_pii",
  "resource_id": "cust_123456",
  "action": "read",
  "fields_accessed": ["email", "phone", "address"],
  "request_id": "req_abc123"
}
```

---

## 권한 상승 탐지

권한 상승은 두 가지 유형으로 나타난다. 정상 계정이 관리자 권한을 획득하는 수평 이동, 낮은 권한 계정이 높은 권한 계정의 작업을 실행하는 수직 상승이다.

사고가 발생했을 때 로그를 분석해보면 대부분 다음 패턴 중 하나를 따른다.

**패턴 1: 권한 부여 후 즉각적인 민감 데이터 접근**

권한이 부여된 직후 수 분 내에 대량의 민감 데이터를 조회하면 의심스럽다. 정상 업무 흐름에서는 권한을 받자마자 대량 조회할 이유가 없다.

```python
from datetime import datetime, timedelta

def detect_privilege_escalation(events: list[dict]) -> list[dict]:
    alerts = []
    role_assignments = {}

    for event in sorted(events, key=lambda e: e["timestamp"]):
        if event["event_type"] == "iam.role.assigned":
            user_id = event["target_user_id"]
            role_assignments[user_id] = {
                "timestamp": datetime.fromisoformat(event["timestamp"]),
                "new_roles": event["role_after"],
                "actor": event["actor_id"]
            }

        elif event["event_type"] == "data.access":
            user_id = event["user_id"]
            if user_id not in role_assignments:
                continue

            assignment = role_assignments[user_id]
            access_time = datetime.fromisoformat(event["timestamp"])
            time_since_assignment = access_time - assignment["timestamp"]

            if time_since_assignment < timedelta(minutes=10):
                if event.get("resource_type") in ["customer_pii", "payment_data", "credentials"]:
                    alerts.append({
                        "alert_type": "privilege_escalation_suspicious",
                        "user_id": user_id,
                        "role_assigned_at": assignment["timestamp"].isoformat(),
                        "assigned_by": assignment["actor"],
                        "data_accessed_at": event["timestamp"],
                        "resource": f"{event['resource_type']}/{event['resource_id']}",
                        "time_gap_seconds": time_since_assignment.seconds
                    })

    return alerts
```

**패턴 2: 관리자 API 사용 급증**

평소에 관리자 명령을 거의 쓰지 않던 계정이 갑자기 대량 실행하는 경우다. 단위 시간당 관리자 작업 수를 슬라이딩 윈도우로 집계해서 임계값을 초과하면 알람을 발생시킨다.

```python
from collections import defaultdict

def detect_admin_abuse(events: list[dict], window_minutes: int = 60, threshold: int = 50) -> list[dict]:
    user_admin_timestamps = defaultdict(list)
    alerts = []

    for event in events:
        if event.get("requires_admin") or event["event_type"].startswith("admin."):
            user_id = event["user_id"]
            user_admin_timestamps[user_id].append(
                datetime.fromisoformat(event["timestamp"])
            )

    for user_id, timestamps in user_admin_timestamps.items():
        timestamps.sort()
        for i, ts in enumerate(timestamps):
            window_end = ts + timedelta(minutes=window_minutes)
            count_in_window = sum(1 for t in timestamps[i:] if t <= window_end)

            if count_in_window > threshold:
                alerts.append({
                    "alert_type": "admin_activity_spike",
                    "user_id": user_id,
                    "window_start": ts.isoformat(),
                    "admin_actions_count": count_in_window,
                    "window_minutes": window_minutes
                })
                break  # 같은 사용자 중복 알람 방지

    return alerts
```

---

## 이상 접근 패턴 탐지

규칙 기반 탐지는 알려진 패턴에는 유효하지만, 처음 보는 패턴은 놓친다. 두 가지를 병행해야 한다.

**시간대 이상 탐지**

사용자별 정상 접근 시간대 프로필을 만들고 벗어나는 접근을 탐지한다. 야간 접근 자체가 문제는 아니지만, 해당 계정이 평생 업무 시간에만 접근했다면 새벽 4시 접근은 조사 대상이다.

```python
from collections import Counter

def build_user_time_profile(events: list[dict], user_id: str) -> dict:
    hour_counts = Counter()

    for event in events:
        if event["user_id"] != user_id:
            continue
        ts = datetime.fromisoformat(event["timestamp"])
        hour_counts[ts.hour] += 1

    total = sum(hour_counts.values())
    if total == 0:
        return {}

    return {
        "active_hours": [h for h, count in hour_counts.items() if count / total > 0.02]
    }

def is_anomalous_time(profile: dict, access_hour: int) -> bool:
    if not profile:
        return False
    return access_hour not in profile.get("active_hours", [])
```

**불가능한 여행 탐지**

같은 사용자가 물리적으로 이동할 수 없는 두 위치에서 짧은 시간 내에 접근하면 계정 탈취를 의심해야 한다. 서울에서 로그인한 계정이 10분 후 뉴욕에서 접근하는 경우다.

```python
import math

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def detect_impossible_travel(events: list[dict], max_speed_kmh: float = 900) -> list[dict]:
    user_last_access = {}
    alerts = []

    for event in sorted(events, key=lambda e: e["timestamp"]):
        if "geo_lat" not in event or "geo_lon" not in event:
            continue

        user_id = event["user_id"]
        current_time = datetime.fromisoformat(event["timestamp"])
        current_lat, current_lon = event["geo_lat"], event["geo_lon"]

        if user_id in user_last_access:
            prev_time, prev_lat, prev_lon = user_last_access[user_id]
            time_diff_hours = (current_time - prev_time).total_seconds() / 3600
            distance_km = haversine_distance_km(prev_lat, prev_lon, current_lat, current_lon)

            if time_diff_hours > 0:
                required_speed = distance_km / time_diff_hours
                if required_speed > max_speed_kmh and distance_km > 100:
                    alerts.append({
                        "alert_type": "impossible_travel",
                        "user_id": user_id,
                        "location_1": {"lat": prev_lat, "lon": prev_lon, "time": prev_time.isoformat()},
                        "location_2": {"lat": current_lat, "lon": current_lon, "time": current_time.isoformat()},
                        "distance_km": round(distance_km, 1),
                        "implied_speed_kmh": round(required_speed, 0)
                    })

        user_last_access[user_id] = (current_time, current_lat, current_lon)

    return alerts
```

---

## 감사 로그 위변조 방지

감사 로그가 위변조되면 모든 보안 투자가 무의미해진다. 사고 발생 시 "로그가 조작됐을 수 있다"는 주장이 나오면 조사 자체가 흔들린다.

### 체인 해시

각 로그 엔트리가 이전 엔트리의 해시를 포함하는 방식이다. 중간 엔트리를 수정하면 이후 모든 엔트리의 해시가 깨진다.

```python
import hashlib
import json
from typing import Optional

class AuditLogChain:
    def __init__(self, prev_hash: str = "0" * 64):
        self.prev_hash = prev_hash

    def add_entry(self, entry: dict) -> dict:
        entry_with_prev = {**entry, "prev_hash": self.prev_hash}
        # sort_keys 없으면 JSON 직렬화 순서가 달라져 해시가 불일치한다
        canonical = json.dumps(entry_with_prev, sort_keys=True, ensure_ascii=False)
        entry_hash = hashlib.sha256(canonical.encode()).hexdigest()
        signed_entry = {**entry_with_prev, "entry_hash": entry_hash}
        self.prev_hash = entry_hash
        return signed_entry

    @staticmethod
    def verify_chain(entries: list[dict]) -> tuple[bool, Optional[int]]:
        if not entries:
            return True, None

        prev_hash = entries[0].get("prev_hash", "0" * 64)

        for i, entry in enumerate(entries):
            if i > 0 and entry.get("prev_hash") != prev_hash:
                return False, i

            stored_hash = entry.pop("entry_hash", None)
            canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
            entry["entry_hash"] = stored_hash  # 복원

            if computed_hash != stored_hash:
                return False, i

            prev_hash = stored_hash

        return True, None
```

### WORM 스토리지

Write Once Read Many 스토리지는 쓴 데이터를 삭제하거나 수정할 수 없다. AWS S3 Object Lock, Azure Immutable Blob Storage, GCP Bucket Lock이 클라우드에서 주로 쓰는 구현체다.

```python
import boto3

def create_immutable_audit_bucket(bucket_name: str, retention_days: int = 365) -> str:
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket=bucket_name)

    # Object Lock은 버킷 생성 시에만 활성화 가능하다
    s3.put_object_lock_configuration(
        Bucket=bucket_name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {
                "DefaultRetention": {
                    # GOVERNANCE 모드는 특권 계정이 삭제 가능해서 컴플라이언스 목적에 부적합하다
                    "Mode": "COMPLIANCE",
                    "Days": retention_days
                }
            }
        }
    )
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"}
    )
    return bucket_name

def write_audit_log_immutable(bucket_name: str, log_entry: dict) -> str:
    s3 = boto3.client("s3")
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc)
    # 날짜 기반 파티셔닝으로 쿼리 성능 확보
    key = f"audit/{ts.year}/{ts.month:02d}/{ts.day:02d}/{ts.strftime('%H%M%S%f')}.json"

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(log_entry, ensure_ascii=False),
        ContentType="application/json"
    )
    return key
```

COMPLIANCE 모드를 사용하면 AWS root 계정도 보존 기간 중에는 삭제할 수 없다. 이 설정은 버킷 생성 이후 변경이 불가능하기 때문에 처음 설계할 때 신중하게 결정해야 한다.

### 외부 매니페스트 검증

로그를 쓸 때만 검증하지 말고 정기적으로 저장된 로그의 무결성을 검사해야 한다. 저장소 자체가 침해됐을 때를 대비한 외부 검증 포인트가 필요하다.

```python
import hmac
from datetime import datetime, timezone

def generate_daily_manifest(entries: list[dict], secret_key: bytes) -> dict:
    entry_hashes = [e["entry_hash"] for e in entries]
    manifest_content = json.dumps({
        "date": datetime.now(timezone.utc).date().isoformat(),
        "entry_count": len(entries),
        "entry_hashes": entry_hashes
    }, sort_keys=True)

    mac = hmac.new(secret_key, manifest_content.encode(), hashlib.sha256).hexdigest()
    return {
        "manifest": json.loads(manifest_content),
        "hmac": mac,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def verify_daily_manifest(manifest_doc: dict, secret_key: bytes) -> bool:
    manifest_content = json.dumps(manifest_doc["manifest"], sort_keys=True)
    expected_mac = hmac.new(secret_key, manifest_content.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_mac, manifest_doc["hmac"])
```

매니페스트 파일 자체는 로그 스토리지와 다른 위치에 보관해야 한다. 같은 버킷에 두면 버킷이 침해됐을 때 매니페스트도 같이 수정될 수 있다.

---

## 사고 조사 시 감사 로그 활용

사고가 발생하면 시간이 촉박하다. 로그가 있어도 어디서 어떻게 찾아야 하는지 모르면 수 시간을 낭비한다.

### 타임라인 재구성

첫 번째 작업은 항상 공격자가 최초 진입한 시점을 찾는 것이다. 탐지된 시점이 공격 시작 시점이 아니다. 탐지 시점 몇 시간, 심할 경우 며칠 전부터 흔적이 있는 경우가 많다.

```python
def reconstruct_timeline(
    events: list[dict],
    suspect_user_id: str = None,
    suspect_ip: str = None,
    start_time: datetime = None,
    end_time: datetime = None
) -> list[dict]:
    filtered = []

    for event in events:
        ts = datetime.fromisoformat(event["timestamp"])
        if start_time and ts < start_time:
            continue
        if end_time and ts > end_time:
            continue

        matches = False
        if suspect_user_id and event.get("user_id") == suspect_user_id:
            matches = True
        if suspect_ip and event.get("source_ip") == suspect_ip:
            matches = True
        if not suspect_user_id and not suspect_ip:
            matches = True

        if matches:
            filtered.append(event)

    return sorted(filtered, key=lambda e: e["timestamp"])
```

### 측면 이동 추적

공격자가 하나의 계정을 탈취하면 다른 계정이나 시스템으로 이동한다. 초기 침해 계정 하나에서 시작해 권한 변경 이벤트를 따라가면 영향받은 계정 전체를 파악할 수 있다.

```python
from collections import Counter

def trace_lateral_movement(events: list[dict], initial_user_id: str) -> dict:
    affected_accounts = {initial_user_id}
    movement_chain = []

    for event in sorted(events, key=lambda e: e["timestamp"]):
        actor_id = event.get("actor_id") or event.get("user_id")
        if actor_id not in affected_accounts:
            continue

        if event["event_type"] in ["iam.role.assigned", "iam.permission.granted"]:
            target = event.get("target_user_id")
            if target and target not in affected_accounts:
                affected_accounts.add(target)
                movement_chain.append({
                    "from_user": actor_id,
                    "to_user": target,
                    "action": event["event_type"],
                    "timestamp": event["timestamp"]
                })

        if event["event_type"] in ["api_key.created", "service_account.created"]:
            new_identity = event.get("created_entity_id")
            if new_identity:
                affected_accounts.add(new_identity)
                movement_chain.append({
                    "from_user": actor_id,
                    "new_identity": new_identity,
                    "action": event["event_type"],
                    "timestamp": event["timestamp"]
                })

    accessed_resources = Counter()
    sensitive_exposed = set()

    for event in events:
        if event.get("user_id") not in affected_accounts:
            continue
        if event["event_type"] == "data.access":
            accessed_resources[event["resource_type"]] += 1
            if event["resource_type"] in ["customer_pii", "payment_data", "credentials"]:
                sensitive_exposed.add(f"{event['resource_type']}/{event['resource_id']}")

    return {
        "affected_accounts": list(affected_accounts),
        "movement_chain": movement_chain,
        "resource_breakdown": dict(accessed_resources),
        "sensitive_data_exposed": list(sensitive_exposed)
    }
```

조사가 끝난 후에는 타임라인, 피해 범위, 증거 무결성 확인 결과를 문서화해야 한다. 컴플라이언스 심사나 법적 분쟁에서 "로그를 어떻게 분석했는지"를 설명해야 하는 경우가 생긴다. 로그 원본을 그대로 제출하는 것만으로는 부족하다.

---

## 운영상 주의사항

**로그 볼륨 관리**

모든 이벤트를 동일한 디테일로 기록하면 스토리지 비용이 빠르게 증가한다. 읽기 전용 API는 5~10% 샘플링하고, 쓰기·삭제·권한 변경은 100% 기록하는 것이 현실적인 선택이다.

**타임스탬프 동기화**

분산 시스템에서 각 서버의 시계가 다르면 타임라인 재구성이 불가능해진다. 모든 서버에 NTP를 강제하고 로그는 항상 UTC를 사용해야 한다. 로컬 타임존이 섞이면 DST 변경 시점에 이벤트 순서가 뒤집히는 상황이 생긴다.

**개인정보 마스킹**

감사 로그에 개인정보가 원문으로 들어가면 GDPR/개인정보보호법 위반이 될 수 있다. 이메일, 전화번호, 카드 번호는 로그 수집 시점에 마스킹하거나 의사 식별자로 치환해야 한다.

```python
import re
import hashlib

def mask_pii(text: str) -> str:
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        lambda m: m.group()[:2] + "***@" + m.group().split("@")[1],
        text
    )
    text = re.sub(
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        lambda m: "****-****-****-" + m.group().replace(" ", "").replace("-", "")[-4:],
        text
    )
    return text

def pseudonymize(identifier: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", identifier.encode(), salt, 100000, dklen=16).hex()
```

**로그 시스템 가용성**

로그 시스템이 다운되면 감사 로그 기록이 멈춘다. 이 자체가 PCI DSS 위반이다. 로그 시스템은 주 애플리케이션과 독립적으로 배포하고, 쓰기 실패 시 재시도 큐를 두어야 한다. 로그 손실은 단순 운영 문제가 아니라 컴플라이언스 위반이다.
