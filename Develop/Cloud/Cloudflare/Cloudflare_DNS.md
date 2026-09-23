---
title: Cloudflare DNS 설정 실무
tags: [cloud, network, dns, cdn, security]
updated: 2026-09-23
---

# Cloudflare DNS 설정 실무

도메인을 Cloudflare로 이전하면 DNS 관리 화면에서 레코드마다 작은 구름 아이콘이 붙는다. 주황색이면 Cloudflare 프록시를 통하는 것이고, 회색이면 DNS 조회만 한다. 이 둘의 차이를 모르고 쓰면 SSL이 예상대로 동작하지 않거나, 실제 서버 IP가 노출되거나, 특정 레코드 타입이 아예 프록시를 지원하지 않아 당황하게 된다.

## 프록시 모드(오렌지 클라우드) vs DNS-only

프록시 모드는 트래픽이 Cloudflare 엣지 서버를 경유한다. 클라이언트 입장에서는 실제 오리진 IP 대신 Cloudflare의 애니캐스트 IP를 받는다. DDoS 완화, WAF, 캐싱이 여기서 작동한다.

DNS-only(회색 구름)는 순수 DNS 레코드다. Cloudflare는 레코드를 저장하고 조회 응답만 내보내며 트래픽에는 관여하지 않는다. 오리진 IP가 그대로 노출된다.

```
클라이언트 → Cloudflare Edge(프록시) → 오리진 서버   # 오렌지
클라이언트 → DNS 조회 → 오리진 IP로 직접 연결        # 회색
```

**프록시를 쓰면 발생하는 실질적인 차이:**

- 오리진으로 들어오는 연결은 Cloudflare IP에서 온다. `X-Forwarded-For`나 `CF-Connecting-IP` 헤더를 써야 실제 클라이언트 IP를 얻는다.
- `dig` 또는 `nslookup`으로 도메인을 조회하면 오리진 IP 대신 Cloudflare IP 대역(`104.x.x.x`, `172.x.x.x`)이 나온다.
- 오리진의 SSL 인증서 설정에 따라 SSL 모드(Flexible/Full/Full Strict)를 맞춰야 한다. Flexible은 브라우저-Cloudflare 구간만 HTTPS고 오리진은 HTTP다. Full Strict는 오리진에도 유효한 인증서가 있어야 한다.

**DNS-only가 필요한 경우:**

- MX 레코드 — Cloudflare 프록시는 MX를 지원하지 않는다. 이메일 서버 레코드는 항상 DNS-only다.
- SRV, CAA, NS, TXT 레코드 — 이 타입들은 프록시 토글 자체가 없거나 회색 고정이다.
- 오리진 서버에서 Cloudflare IP가 아닌 실제 클라이언트 IP를 받아야 하는 구조 — 이 경우는 프록시를 쓰되 `CF-Connecting-IP` 헤더를 처리하는 쪽이 낫다.

## 레코드 타입별 설정

### A / AAAA

A는 IPv4, AAAA는 IPv6를 가리킨다. 루트 도메인(`@`)과 서브도메인 모두 A 레코드를 쓸 수 있다.

```
Type: A
Name: @          (루트 도메인, example.com)
IPv4: 203.0.113.10
Proxy: 오렌지 (프록시 모드)
TTL: Auto

Type: A
Name: api        (api.example.com)
IPv4: 203.0.113.10
Proxy: 오렌지
TTL: Auto
```

여러 A 레코드를 같은 이름에 붙이면 라운드로빈으로 응답한다. Cloudflare 로드밸런서 없이 간단한 부하 분산을 할 수는 있지만, 특정 IP가 죽어도 DNS TTL만큼은 클라이언트 캐시에 남는다.

### CNAME

다른 도메인을 가리킨다. `www`를 루트 도메인에 붙이는 용도로 많이 쓴다.

```
Type: CNAME
Name: www
Target: example.com
Proxy: 오렌지
TTL: Auto
```

루트 도메인(`@`)에는 CNAME을 쓸 수 없다 — RFC 표준 제약이다. Cloudflare는 CNAME Flattening으로 이를 우회한다. `@`에 CNAME을 입력하면 Cloudflare가 최종 A 레코드로 풀어서 응답한다. 다른 DNS 제공자에서는 이 기능이 없어서 루트에 CNAME을 넣으면 다른 레코드(MX 등)가 깨진다.

### MX

이메일 수신을 담당하는 레코드. 여러 MX를 등록할 수 있고 우선순위가 낮을수록 먼저 시도한다.

```
Type: MX
Name: @
Mail server: aspmx.l.google.com
Priority: 1

Type: MX
Name: @
Mail server: alt1.aspmx.l.google.com
Priority: 5
```

MX는 프록시 불가다. Cloudflare DNS 화면에서 자동으로 DNS-only로 고정된다. MX 레코드의 대상이 되는 서버도 A/CNAME으로 별도 등록해야 하는데, 그 레코드를 프록시로 설정하면 SMTP 연결이 막힌다. 메일 서버 레코드는 DNS-only로 유지한다.

### TXT

도메인 소유권 확인, SPF, DKIM, DMARC에 쓰인다.

```
Type: TXT
Name: @
Content: "v=spf1 include:_spf.google.com ~all"

Type: TXT
Name: _dmarc
Content: "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
```

TXT 레코드에 큰따옴표를 입력칸에 직접 넣을 필요는 없다. Cloudflare 대시보드가 자동으로 처리한다. API로 생성할 때도 마찬가지다.

## API 토큰으로 레코드 자동화

Cloudflare API를 쓰면 레코드 생성·수정·삭제를 코드로 관리할 수 있다. DDNS 갱신, CI/CD에서 배포 직후 레코드 업데이트 같은 용도에 쓴다.

**토큰 생성 순서:**

대시보드 오른쪽 위 프로필 → API Tokens → Create Token → "Edit zone DNS" 템플릿 선택. Zone Resource를 특정 도메인으로 제한하는 게 낫다. 전체 계정 권한을 주면 토큰 하나 유출로 모든 도메인이 위험해진다.

**Zone ID 확인:**

도메인 대시보드 오른쪽 사이드바에 Zone ID가 있다. API 호출 URL에 이 값이 들어간다.

**레코드 생성:**

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records" \
  -H "Authorization: Bearer {API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "api",
    "content": "203.0.113.10",
    "ttl": 1,
    "proxied": true
  }'
```

`ttl: 1`은 Cloudflare에서 Auto TTL을 의미한다. 프록시 모드에서는 TTL이 자동으로 300초로 고정되기 때문에 실제로 입력한 TTL 값은 무시된다.

**기존 레코드 업데이트 (PUT):**

레코드 ID를 먼저 조회해야 한다.

```bash
# 레코드 조회
curl "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records?type=A&name=api.example.com" \
  -H "Authorization: Bearer {API_TOKEN}"

# 응답에서 id 추출 후 업데이트
curl -X PUT "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{RECORD_ID}" \
  -H "Authorization: Bearer {API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "api",
    "content": "203.0.113.20",
    "ttl": 1,
    "proxied": true
  }'
```

PATCH를 쓰면 변경할 필드만 넘겨도 된다. PUT은 레코드 전체를 교체하므로 `name`, `type`, `content`를 전부 넣어야 한다.

**Python으로 DDNS 갱신:**

```python
import httpx
import json

CF_TOKEN = "your_token"
ZONE_ID = "your_zone_id"
RECORD_NAME = "home.example.com"

def get_public_ip() -> str:
    return httpx.get("https://api.ipify.org").text.strip()

def get_record_id(name: str) -> tuple[str, str]:
    resp = httpx.get(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
        params={"type": "A", "name": name},
        headers={"Authorization": f"Bearer {CF_TOKEN}"},
    )
    result = resp.json()["result"]
    if not result:
        return "", ""
    return result[0]["id"], result[0]["content"]

def update_record(record_id: str, ip: str, name: str) -> None:
    httpx.put(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}",
        headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"},
        content=json.dumps({"type": "A", "name": name, "content": ip, "ttl": 1, "proxied": False}),
    )

current_ip = get_public_ip()
record_id, existing_ip = get_record_id(RECORD_NAME)

if current_ip != existing_ip:
    update_record(record_id, current_ip, RECORD_NAME)
```

홈 서버처럼 유동 IP를 가진 환경에서 쓸 수 있다. DDNS 용도라면 `proxied: false`가 맞다 — 프록시를 켜면 Cloudflare IP로 응답하기 때문에 IP 변경 감지 로직이 의미 없어진다.

## TTL 주의사항

TTL은 DNS 캐시 유효 시간이다. 값이 클수록 레코드 변경이 전파되는 데 시간이 걸린다.

프록시 모드에서는 TTL을 직접 설정해도 Cloudflare가 외부에 300초로 고정해서 응답한다. 레코드를 바꾸면 5분 안에 반영된다.

DNS-only 모드에서는 설정한 TTL이 실제로 적용된다. Cloudflare 무료 플랜에서 최소 60초로 설정할 수 있다. 도메인 이전이나 레코드 변경을 앞두고 있다면 며칠 전에 TTL을 낮춰두는 게 낫다. 기존 TTL이 86400(24시간)이면 변경해도 24시간이 지나야 전파가 완료된다.

**실제로 겪은 문제:** 새 서버로 이전하면서 A 레코드를 바꿨는데, 일부 사용자가 몇 시간 뒤에도 옛 서버로 접속하는 경우가 있었다. DNS-only 상태에서 TTL이 3600이었고, 각 ISP와 중간 DNS 서버가 TTL까지 캐시를 유지하기 때문이다. 이전 작업 전에 TTL을 60초로 낮추고 적어도 기존 TTL 시간만큼 기다린 뒤 레코드를 변경해야 이런 일이 줄어든다.

## 도메인 이전 절차

타 레지스트라에서 Cloudflare로 도메인을 이전하는 경우와, 기존 DNS 서버만 Cloudflare로 바꾸는 경우는 다르다.

### DNS 서버만 변경

레지스트라는 유지하고 네임서버만 Cloudflare로 바꾸는 방법이다. 레지스트라 잠금을 해제하거나 이전 요청 없이 할 수 있다.

```
1. Cloudflare 대시보드에서 "Add a Site" → 도메인 입력
2. Cloudflare가 기존 레코드를 자동 스캔해서 가져옴 (빠진 레코드 있는지 확인)
3. Cloudflare가 할당해준 네임서버 두 개를 메모
   (예: ada.ns.cloudflare.com, ken.ns.cloudflare.com)
4. 현재 레지스트라 관리 화면에서 네임서버를 위 두 개로 교체
5. 전파 완료까지 24~48시간 대기
```

네임서버 전파 전까지 Cloudflare 대시보드에 "Pending" 상태가 뜬다. 전파가 완료되면 "Active"로 바뀐다.

자동 스캔이 모든 레코드를 가져오지는 않는다. 특히 DNSSEC 관련 레코드, 일부 TXT 레코드는 빠지는 경우가 있다. 기존 레지스트라에서 레코드 목록을 수출하거나 직접 비교해서 확인해야 한다.

### 레지스트라 이전 (Transfer)

도메인 자체를 Cloudflare Registrar로 옮기는 것이다. ICANN 규정상 최근 60일 이내 등록 또는 이전한 도메인은 이전할 수 없다.

```
1. 현재 레지스트라에서 도메인 잠금 해제 (Registrar Lock 비활성화)
2. 이전 인증 코드(Auth Code, EPP Code) 발급
3. Cloudflare 대시보드 → Registrar → Transfer 탭 → 도메인 입력
4. Auth Code 입력 → 이전 비용 결제 (연장 포함)
5. 현재 레지스트라에서 이전 승인 이메일 확인 후 승인
6. 완료까지 최대 5~7일
```

이전 중에는 도메인 운영이 중단되지 않는다. 네임서버는 그대로 유지되기 때문에 DNS는 계속 동작한다.

이전 후 첫 갱신 시점이 헷갈리는 경우가 있다. Cloudflare는 이전 시 1년 연장을 포함하므로, 기존 만료일에 1년이 추가된 시점이 다음 갱신일이다. 만료 임박한 도메인을 이전하면 실질적으로 2년치가 되는 셈이다.

## API 토큰 관리

토큰을 코드에 하드코딩하지 않는다. 환경 변수나 시크릿 관리 도구를 쓴다.

토큰에 Zone 범위를 명확하게 제한한다. "Edit zone DNS" 권한을 전체 계정이 아닌 특정 Zone에만 부여하면 유출 피해 범위가 줄어든다.

오래된 토큰은 주기적으로 만료시킨다. 대시보드에서 토큰별로 마지막 사용 시각을 확인할 수 있다. 90일 이상 사용하지 않은 토큰은 삭제하는 게 낫다.

CI/CD 파이프라인에서 쓰는 토큰은 GitHub Actions Secrets, AWS Secrets Manager 같은 곳에 저장하고, 파이프라인 로그에 값이 출력되지 않는지 확인한다.
