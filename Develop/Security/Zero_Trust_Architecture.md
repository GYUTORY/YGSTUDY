---
title: "Zero Trust Architecture"
tags: [Security, Zero-Trust, BeyondCorp, ZTNA, Microsegmentation, OPA, MDM, Cloudflare, Tailscale, Zscaler]
updated: 2026-07-27
---

# Zero Trust Architecture

## 경계 기반 보안이 왜 안 되는가

전통적인 네트워크 보안은 "내부는 안전하다"는 전제에서 시작한다. 방화벽으로 외부와 내부를 나누고, 내부 네트워크에 들어온 트래픽은 대체로 신뢰한다. VPN으로 접속하면 사내 네트워크 전체에 접근할 수 있는 구조다.

이 모델의 문제는 한번 뚫리면 끝이라는 것이다. 공격자가 VPN 크리덴셜을 탈취하거나, 내부 시스템 하나를 장악하면 lateral movement로 다른 시스템까지 접근할 수 있다. 내부 네트워크 안에서는 서비스 간 통신에 인증이 없으니까.

실제로 대형 보안 사고 대부분이 이 패턴이다. 피싱으로 직원 한 명의 크리덴셜을 탈취하고, VPN으로 내부 네트워크에 들어온 뒤, 횡방향으로 이동하면서 핵심 시스템에 접근한다. 방화벽은 외부→내부만 차단하지, 내부→내부는 거의 제어하지 않기 때문이다.

클라우드 환경으로 넘어오면서 경계 자체가 모호해졌다. 온프레미스 데이터센터, AWS VPC, SaaS 서비스가 섞여 있는 상태에서 "내부"와 "외부"를 어떻게 나눌 것인가. 재택근무까지 합쳐지면 사내 네트워크라는 개념 자체가 무너진다.

## Zero Trust 원칙

Zero Trust는 "Never trust, always verify"를 기본 원칙으로 한다. 네트워크 위치와 관계없이 모든 접근 요청을 검증한다. 구체적으로 세 가지 원칙이 있다.

**명시적 검증**: 모든 요청에 대해 사용자 ID, 디바이스 상태, 위치, 요청 내용을 종합적으로 검증한다. "이 네트워크에 있으니까 OK"는 허용하지 않는다.

**최소 권한**: 필요한 리소스에만, 필요한 시간 동안만 접근을 허용한다. VPN처럼 네트워크 전체에 대한 접근 권한을 한번에 부여하지 않는다.

**침해 가정**: 이미 내부 네트워크가 뚫린 상태라고 가정한다. 그래서 내부 통신에도 암호화와 인증을 적용하고, 세그멘테이션으로 피해 범위를 제한한다.

이 원칙들은 추상적으로 들리지만, 실제 구현하면 꽤 구체적인 기술 결정으로 이어진다. 서비스 간 통신에 mTLS를 적용하고(→ [mTLS 문서](../Backend/API/m_TLS_Service_Auth.md) 참고), 네트워크를 마이크로세그멘테이션으로 나누고, 모든 API 요청에 인증·인가를 붙이는 식이다.

## BeyondCorp — Google이 만든 Zero Trust 구현체

BeyondCorp는 Google이 2014년에 공개한 Zero Trust 모델이다. 발단은 2009년 Operation Aurora 사건이었다. 국가 단위 공격자가 Google 내부 네트워크에 침입했고, Google은 VPN/방화벽 기반 보안이 한계가 있다는 결론을 내렸다.

BeyondCorp의 핵심 아이디어는 간단하다. 사내 네트워크와 외부 네트워크를 동일하게 취급한다. 사무실에서 접속하든, 카페에서 접속하든 같은 인증·인가 과정을 거친다. VPN을 없앤다.

### BeyondCorp의 구성 요소

**Access Proxy**: 모든 요청이 거쳐가는 단일 진입점이다. 사용자가 내부 애플리케이션에 접근하려면 반드시 Access Proxy를 거쳐야 한다. Proxy가 사용자 인증, 디바이스 확인, 접근 정책 평가를 처리한다.

**Device Inventory**: 회사가 관리하는 모든 디바이스 목록을 유지한다. 디바이스의 OS 버전, 패치 상태, 디스크 암호화 여부 등을 추적한다. 인증된 사용자라도 관리되지 않는 디바이스에서는 접근을 제한한다.

**User/Group Database**: 사용자 ID와 그룹 정보를 관리한다. SSO와 연동되고, 각 사용자가 어떤 애플리케이션에 접근할 수 있는지 정의한다.

**Trust Engine**: 사용자 ID + 디바이스 상태 + 기타 시그널을 종합해서 "신뢰 수준"을 산출한다. 이 신뢰 수준에 따라 접근 허용/거부/제한을 결정한다.

실제 동작 흐름은 이렇다:

1. 사용자가 내부 애플리케이션(예: 사내 위키)에 접속 시도
2. Access Proxy가 요청을 가로챔
3. SSO로 사용자 인증 (ID + MFA)
4. Device Inventory에서 디바이스 상태 확인
5. Trust Engine이 사용자 + 디바이스 신뢰 수준 산출
6. 접근 정책과 비교해서 허용/거부 결정
7. 허용되면 백엔드 애플리케이션으로 요청 전달

Google 외에도 Cloudflare Access, Zscaler Private Access, Palo Alto Prisma Access 같은 상용 제품이 이 모델을 구현하고 있다. 직접 구축한다면 OAuth2 Proxy + 디바이스 인증서 + 정책 엔진 조합으로 비슷한 구조를 만들 수 있다.

## ZTNA vs 전통 VPN

VPN과 ZTNA(Zero Trust Network Access)는 둘 다 원격 접속 문제를 해결하지만, 접근 방식이 다르다.

### VPN의 구조적 문제

VPN은 네트워크 레벨 접근을 준다. VPN에 연결하면 사내 네트워크 대역 전체에 접근할 수 있다. 분할 터널링이나 ACL로 제한할 수 있긴 하지만, 기본적으로 "네트워크에 접속"하는 구조다.

운영하다 보면 이런 문제를 겪게 된다:

- **과도한 접근 범위**: 개발자가 DB 서버 하나에 접근하려고 VPN을 연결하면, 사내 네트워크 전체에 대한 경로가 열린다. 필요한 것보다 훨씬 넓은 범위다.
- **크리덴셜 탈취 시 피해 범위**: VPN 크리덴셜이 유출되면 공격자가 사내 네트워크 전체에 접근할 수 있다.
- **성능 병목**: 모든 트래픽이 VPN 집중점(concentrator)을 거쳐야 한다. 사용자가 늘면 병목이 생긴다. 재택근무가 보편화되면서 VPN 인프라가 감당 못 하는 경우가 많다.
- **관리 복잡도**: VPN 클라이언트 배포, 터널 설정, ACL 관리가 누적되면 운영 부담이 커진다.

### ZTNA의 접근 방식

ZTNA는 애플리케이션 단위로 접근을 제어한다. 네트워크에 접속하는 게 아니라, 특정 애플리케이션에 대한 접근만 허용한다.

| 비교 항목 | VPN | ZTNA |
|-----------|-----|------|
| 접근 범위 | 네트워크 레벨 | 애플리케이션 레벨 |
| 인증 시점 | 연결 시 1회 | 요청마다 지속적 검증 |
| 디바이스 검증 | 없거나 연결 시 1회 | 지속적 디바이스 상태 확인 |
| 내부 자원 노출 | 네트워크 대역 전체 | 허용된 앱만 보임 |
| 아키텍처 | 인바운드 연결 (VPN 서버 노출) | 아웃바운드 연결 (커넥터가 터널 생성) |
| 확장성 | VPN 집중점 병목 | 분산 엣지 구조 |

ZTNA에서 중요한 부분은 "아웃바운드 연결"이다. 전통 VPN은 VPN 서버가 인터넷에 노출되어야 한다. ZTNA는 내부에 설치한 커넥터가 클라우드 쪽으로 아웃바운드 연결을 만든다. 내부에서 밖으로 연결하니까, 내부 인프라를 인터넷에 노출하지 않아도 된다.

실무에서 VPN을 완전히 없애기는 어렵다. DB에 직접 접속하거나 레거시 시스템을 관리하는 경우에는 네트워크 레벨 접근이 필요하다. 보통은 일반 사용자를 ZTNA로 전환하고, 인프라 관리용으로 VPN을 남겨두는 식으로 전환한다.

## ZTNA 상용 제품 비교

Cloudflare Access, Tailscale, Zscaler Private Access(ZPA)는 각각 다른 규모와 요구사항을 겨냥한다. 이름만 보면 비슷해 보이지만, 실제로 설정하고 운영해보면 철학이 완전히 다르다.

### Cloudflare Access

Cloudflare Access는 cloudflared 터널 데몬을 서버에 설치하고, 그 데몬이 Cloudflare 엣지로 아웃바운드 연결을 맺는 구조다. 사용자가 `wiki.corp.com`에 접속하면 Cloudflare가 IdP(Google, Okta, Azure AD 등)로 리다이렉트하고, 인증 후 서버에 요청을 전달한다.

```yaml
# /etc/cloudflared/config.yml
tunnel: a1b2c3d4-e5f6-7890-abcd-ef1234567890
credentials-file: /etc/cloudflared/creds/a1b2c3d4.json

ingress:
  - hostname: wiki.corp.example.com
    service: http://localhost:8080
  - hostname: grafana.corp.example.com
    service: http://localhost:3000
  - hostname: bastion.corp.example.com
    service: ssh://localhost:22
  - service: http_status:404
```

Cloudflare Access가 통과시킨 요청에는 `Cf-Access-Jwt-Assertion` 헤더가 붙는다. 백엔드에서 이 JWT를 검증하면 Cloudflare를 거치지 않은 직접 접근을 걸러낼 수 있다.

```python
import httpx
import jwt
from functools import lru_cache

CF_TEAM_DOMAIN = "corp.cloudflareaccess.com"
CF_AUD = "your-application-aud-tag"  # Cloudflare Zero Trust 대시보드에서 확인

@lru_cache(maxsize=1)
def _get_cf_certs() -> dict:
    resp = httpx.get(f"https://{CF_TEAM_DOMAIN}/cdn-cgi/access/certs")
    resp.raise_for_status()
    return resp.json()

def verify_cf_access(token: str) -> dict:
    certs = _get_cf_certs()
    try:
        payload = jwt.decode(
            token,
            certs,
            algorithms=["RS256"],
            audience=CF_AUD,
        )
    except jwt.InvalidTokenError as exc:
        raise PermissionError(f"Invalid Cloudflare Access token: {exc}")
    # payload에 email, groups, country 등 포함
    return payload
```

Terraform으로 Access Policy를 관리하면 정책 변경 이력이 남는다.

```hcl
resource "cloudflare_access_application" "internal_wiki" {
  zone_id          = var.zone_id
  name             = "Internal Wiki"
  domain           = "wiki.corp.example.com"
  type             = "self_hosted"
  session_duration = "8h"
}

resource "cloudflare_access_policy" "corp_engineers" {
  application_id = cloudflare_access_application.internal_wiki.id
  zone_id        = var.zone_id
  name           = "Engineering team only"
  precedence     = 1
  decision       = "allow"

  include {
    email_domain = ["corp.com"]
    groups       = [cloudflare_access_group.engineering.id]
  }

  require {
    # WARP 클라이언트 + Jamf 디바이스 포스처 필수
    device_posture {
      integration_uid = cloudflare_device_posture_integration.jamf.id
    }
  }
}
```

운영하면서 겪은 한계가 있다. WARP 클라이언트를 설치해야만 디바이스 포스처 체크가 된다. 직원들이 WARP 설치를 거부하거나, iOS/Android에서 WARP가 배터리를 많이 소모한다는 불만이 나온다. 또한 TCP/UDP 레벨 터널링(예: DB 직접 접속)은 Cloudflare Tunnel + WARP 조합이 필요하고, 대역폭 비용이 추가된다. 50인 이하 팀에는 무료 티어로 충분하지만, 그 이상이면 비용 계산을 미리 해봐야 한다.

### Tailscale

Tailscale은 WireGuard 기반의 mesh 네트워크다. ZTNA라고 부르기보다는 "더 나은 VPN"에 가깝다. 각 노드가 Tailscale IP(100.x.x.x 대역)를 받고, 노드 간 직접 WireGuard 터널을 형성한다. 직접 연결이 안 되면 Tailscale의 DERP 릴레이 서버를 경유한다.

설치는 간단하다. `brew install tailscale && tailscale up --login-server=https://login.tailscale.com` 한 줄이면 된다. 30분 만에 팀 전체 dev 환경을 연결한 경험이 있다.

ACL 정책은 HuJSON(주석 포함 JSON) 형식으로 작성한다.

```hujson
{
  "tagOwners": {
    "tag:server":   ["autogroup:admin"],
    "tag:database": ["autogroup:admin"],
    "tag:ci":       ["autogroup:admin"]
  },

  "acls": [
    // 개발자 → 개발 서버: SSH + 앱 포트
    {
      "action": "accept",
      "src":    ["autogroup:member"],
      "dst":    ["tag:server:22", "tag:server:8080-9090"]
    },
    // 백엔드 서버 → DB: PostgreSQL만
    {
      "action": "accept",
      "src":    ["tag:server"],
      "dst":    ["tag:database:5432"]
    },
    // CI/CD → 서버 SSH (배포용)
    {
      "action": "accept",
      "src":    ["tag:ci"],
      "dst":    ["tag:server:22"]
    }
    // 나머지는 기본 차단
  ],

  // Tailscale SSH: 공개키 없이 SSO 계정으로 SSH 접속
  "ssh": [
    {
      "action": "accept",
      "src":    ["autogroup:admin"],
      "dst":    ["tag:server"],
      "users":  ["root", "ubuntu"]
    }
  ]
}
```

Subnet Router를 쓰면 온프레미스 네트워크 전체를 Tailscale 망에 연결할 수 있다. 레거시 시스템이 많은 환경에서 점진적 전환 시에 유용하다.

Tailscale의 한계는 명확하다. ACL이 L3/L4(IP/포트) 수준이라, "이 사용자가 이 API 엔드포인트를 호출할 수 있는가" 같은 L7 정책은 불가능하다. 1000명 이상 규모의 enterprise 환경에서는 정책 관리가 복잡해진다. Tailscale은 소규모~중간 규모 개발팀 내부 접속 용도에 맞다.

### Zscaler Private Access

ZPA는 App Connector를 각 데이터센터나 네트워크 세그먼트에 배포하고, 커넥터가 Zscaler 클라우드로 아웃바운드 연결을 맺는 구조다. 사용자는 Zscaler Client Connector(에이전트)를 설치하거나, 브라우저 기반 접속을 사용한다.

Terraform으로 App Segment와 Policy를 관리할 수 있다.

```hcl
# App Segment: 내부 앱을 hostname:port 단위로 정의
resource "zpa_application_segment" "internal_wiki" {
  name             = "Internal Wiki"
  enabled          = true
  health_reporting = "ON_ACCESS"
  bypass_type      = "NEVER"

  domain_names = ["wiki.internal.corp.com"]
  tcp_port_ranges = ["443", "443"]

  segment_group_id = zpa_segment_group.internal_apps.id
  server_groups    = [zpa_server_group.corp_servers.id]
}

# Access Policy: SAML attribute 기반 접근 제어
resource "zpa_policy_access_rule" "wiki_engineering" {
  name        = "Wiki - Engineering Only"
  action      = "ALLOW"
  rule_order  = "1"
  policy_type = "ACCESS_POLICY"

  conditions {
    operands {
      object_type = "APP"
      lhs         = "id"
      rhs         = zpa_application_segment.internal_wiki.id
    }
  }

  conditions {
    operands {
      object_type = "SAML"
      lhs         = "department"
      rhs         = "Engineering"
      idp_id      = data.zpa_idp_controller.okta.id
    }
  }
}
```

ZPA는 App Connector HA 구성, SAML/SCIM 완전 연동, ZIA(인터넷 트래픽 필터링)와 결합한 종합 보안 플랫폼을 원하는 enterprise에 맞다. 설정 복잡도가 높고, 도입 초기에 App Connector 배치 설계를 잘못 하면 나중에 수정 비용이 크다.

### 제품 선택 기준

| 항목 | Cloudflare Access | Tailscale | Zscaler ZPA |
|------|:-----------------:|:---------:|:-----------:|
| 규모 | 소~중 | 소~중 | 중~대 |
| 설정 난이도 | 낮음 | 매우 낮음 | 높음 |
| 정책 세밀도 | 중간 (IdP 그룹, 디바이스 포스처) | 낮음 (L3/L4) | 높음 (SAML attribute, SCIM) |
| 디바이스 포스처 | WARP 필수 | 제한적 | Client Connector 필수 |
| 레거시 연동 | 어려움 | Subnet Router로 가능 | App Connector로 가능 |
| 비용 | 중간 | 낮음 | 높음 |

개발팀 내부 접속 정도면 Tailscale로 빠르게 시작하고, 직원 전체 대상 SaaS 접근 제어가 필요하면 Cloudflare Access, 대규모 enterprise에 SAML/SCIM 완전 연동과 컴플라이언스가 필요하면 ZPA를 선택한다.

## 마이크로세그멘테이션

마이크로세그멘테이션은 네트워크를 작은 단위로 나눠서 서비스 간 통신을 제어하는 것이다. 전통적인 VLAN 기반 세그멘테이션이 "서브넷 단위"로 나누는 거라면, 마이크로세그멘테이션은 "워크로드 단위"로 나눈다.

쿠버네티스 환경에서는 NetworkPolicy가 마이크로세그멘테이션의 기본 수단이다.

### 기본 정책: 기본 차단

쿠버네티스 NetworkPolicy의 기본 동작은 "모든 트래픽 허용"이다. NetworkPolicy를 하나도 만들지 않으면, 모든 Pod가 모든 Pod에 접근할 수 있다. Zero Trust를 적용하려면 기본 차단(deny-all) 정책을 먼저 적용해야 한다.

```yaml
# 네임스페이스 내 모든 인그레스 트래픽 차단
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}    # 빈 셀렉터 = 네임스페이스 내 모든 Pod
  policyTypes:
  - Ingress
---
# 이그레스도 차단 (DNS는 허용해야 Pod가 서비스 이름으로 통신 가능)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

기본 차단 정책을 적용하면 DNS 외에는 아무 통신도 안 된다. 여기서부터 필요한 통신만 하나씩 열어주는 방식으로 진행한다.

### 서비스 간 통신 허용

예를 들어 `order-service`가 `payment-service`에만 접근해야 하는 경우:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-order-to-payment
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: payment-service
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: order-service
    ports:
    - protocol: TCP
      port: 8080
```

이 정책은 payment-service Pod에 대해, order-service Pod에서 오는 8080 포트 TCP 트래픽만 허용한다. 다른 서비스에서 payment-service에 접근하려 하면 패킷이 드롭된다.

### Calico NetworkPolicy

쿠버네티스 기본 NetworkPolicy는 기능이 제한적이다. 예를 들어 L7(HTTP 경로, 메서드) 기반 필터링이 안 되고, 글로벌 정책을 정의할 수 없다. Calico를 CNI로 쓰면 추가 기능을 사용할 수 있다.

```yaml
# Calico GlobalNetworkPolicy — 클러스터 전체에 적용
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: deny-all-default
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress:
  - action: Deny
  egress:
  - action: Deny
```

Calico는 네임스페이스를 넘나드는 정책을 하나로 관리할 수 있다. 기본 NetworkPolicy는 네임스페이스 단위로만 정책을 정의하기 때문에, 네임스페이스가 많아지면 정책이 흩어진다.

HTTP 레벨 정책도 지원한다 (Calico Enterprise 또는 Istio 연동 시):

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-order-to-payment-http
  namespace: production
spec:
  selector: app == 'payment-service'
  ingress:
  - action: Allow
    source:
      selector: app == 'order-service'
    http:
      methods: ["POST"]
      paths:
      - exact: /api/v1/payments
```

이렇게 하면 order-service에서 payment-service로 보내는 `POST /api/v1/payments` 요청만 허용된다. GET 요청이나 다른 경로는 차단된다.

### 세그멘테이션 적용 시 주의사항

기존 운영 환경에 기본 차단 정책을 바로 적용하면 서비스가 끊어진다. 단계적으로 적용해야 한다.

1. 모니터링 모드로 시작한다. Calico의 경우 `action: Log`로 트래픽 흐름을 기록만 한다.
2. 로그를 분석해서 실제 트래픽 패턴을 파악한다. 어떤 서비스가 어떤 서비스와 통신하는지 매핑한다.
3. 허용 정책을 먼저 만든다. 확인된 통신 경로에 대해 Allow 정책을 작성한다.
4. 기본 차단 정책을 적용한다. 허용 정책이 다 들어간 뒤에 차단을 켠다.

순서를 바꾸면 사고가 난다. 특히 서비스 디스커버리, 헬스체크, 메트릭 수집 같은 인프라 통신을 빠뜨리기 쉽다. Prometheus가 메트릭을 못 긁어가거나, kube-probe 헬스체크가 차단돼서 Pod가 재시작되는 일이 생긴다.

## OPA/Envoy 기반 정책 적용

NetworkPolicy는 L3/L4 수준의 통신 제어다. "누가 어디로 연결할 수 있는가"를 결정한다. 하지만 실제 서비스 간 인가는 더 세밀해야 한다. "이 사용자의 이 요청이 이 리소스에 접근할 수 있는가"를 판단하려면 L7 수준의 정책 엔진이 필요하다.

OPA(Open Policy Agent)는 범용 정책 엔진이다. Rego라는 언어로 정책을 작성하고, JSON 입력에 대해 허용/거부를 판단한다. Envoy의 External Authorization 필터와 결합하면 모든 HTTP 요청에 대해 정책을 적용할 수 있다.

### 구조

```
Client → Envoy Sidecar → [ext_authz] → OPA → 정책 평가
                                              ↓
                                         Allow / Deny
                                              ↓
                              Envoy → Backend Service
```

Envoy가 모든 요청을 가로채고, OPA에 인가 결정을 질의한다. OPA가 Allow를 반환하면 요청이 백엔드로 전달되고, Deny면 403을 반환한다.

### Envoy 설정

```yaml
# Envoy ext_authz 필터 설정
http_filters:
- name: envoy.filters.http.ext_authz
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
    grpc_service:
      envoy_grpc:
        cluster_name: opa-authz
      timeout: 0.5s
    failure_mode_allow: false    # OPA 응답 없으면 차단
    with_request_body:
      max_request_bytes: 8192
      allow_partial_message: true
- name: envoy.filters.http.router
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

`failure_mode_allow: false`가 중요하다. OPA가 응답하지 않으면 요청을 차단한다. true로 설정하면 OPA 장애 시 모든 요청이 허용돼서 보안이 무너진다. 대신 OPA의 가용성을 반드시 보장해야 한다.

### OPA 정책 (Rego)

```rego
package envoy.authz

import input.attributes.request.http as http_request

default allow := false

# JWT에서 사용자 정보 추출
token := payload {
    auth_header := http_request.headers.authorization
    startswith(auth_header, "Bearer ")
    encoded := substring(auth_header, 7, -1)
    [_, payload, _] := io.jwt.decode(encoded)
}

# 서비스 역할 기반 접근 제어
allow {
    http_request.method == "GET"
    glob.match("/api/v1/orders/*", ["/"], http_request.path)
    token.role == "order-reader"
}

allow {
    http_request.method == "POST"
    http_request.path == "/api/v1/orders"
    token.role == "order-writer"
}

# payment-service는 order-service에서만 호출 가능
allow {
    http_request.path == "/api/v1/payments"
    http_request.method == "POST"
    http_request.headers["x-source-service"] == "order-service"
    token.role == "payment-caller"
}

# 관리자 API — 특정 IP 대역 + admin 역할만 허용
allow {
    glob.match("/admin/*", ["/"], http_request.path)
    token.role == "admin"
    net.cidr_contains("10.0.100.0/24", http_request.headers["x-forwarded-for"])
}
```

Rego 정책에서 주의할 점이 있다. `default allow := false`를 반드시 선언해야 한다. 이 선언이 없으면, 어떤 allow 규칙에도 해당하지 않는 요청에 대해 `undefined`가 반환된다. Envoy가 이걸 어떻게 처리하느냐에 따라 허용이 될 수도 있다.

정책을 테스트하는 것도 중요하다. OPA는 내장 테스트 프레임워크가 있다:

```rego
# authz_test.rego
package envoy.authz

test_allow_order_read {
    allow with input as {
        "attributes": {
            "request": {
                "http": {
                    "method": "GET",
                    "path": "/api/v1/orders/123",
                    "headers": {
                        "authorization": "Bearer eyJ..."
                    }
                }
            }
        }
    }
}

test_deny_payment_from_unknown_service {
    not allow with input as {
        "attributes": {
            "request": {
                "http": {
                    "method": "POST",
                    "path": "/api/v1/payments",
                    "headers": {
                        "x-source-service": "unknown-service",
                        "authorization": "Bearer eyJ..."
                    }
                }
            }
        }
    }
}
```

```bash
# 정책 테스트 실행
opa test . -v
```

### OPA를 사이드카로 배포하는 이유

OPA를 중앙 서버 하나에 두면 단일 장애점이 된다. OPA가 죽으면 전체 서비스의 인가가 멈춘다. 사이드카로 각 Pod에 OPA를 같이 띄우면 이 문제를 피할 수 있다. 정책은 OPA의 Bundle API로 중앙에서 배포하고, 각 사이드카 OPA가 주기적으로 가져간다.

```yaml
# OPA 사이드카가 포함된 Pod 스펙
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  template:
    spec:
      containers:
      - name: order-service
        image: order-service:latest
        ports:
        - containerPort: 8080
      - name: opa
        image: openpolicyagent/opa:latest
        args:
        - "run"
        - "--server"
        - "--addr=0.0.0.0:8181"
        - "--set=services.authz.url=https://opa-bundle-server"
        - "--set=bundles.authz.service=authz"
        - "--set=bundles.authz.resource=bundles/order-service"
        - "--set=decision_logs.console=true"
        ports:
        - containerPort: 8181
```

## API Gateway에서의 요청별 인증·인가

API Gateway는 Zero Trust 아키텍처에서 외부 → 내부 경계의 정책 적용 지점이다. 모든 외부 요청이 API Gateway를 거치도록 하고, 여기서 인증과 인가를 처리한다.

### 요청 단위 검증 흐름

Gateway에서 처리하는 검증 순서:

1. **TLS 종료**: 클라이언트와의 TLS 연결을 Gateway에서 종료한다.
2. **토큰 검증**: Authorization 헤더의 JWT를 검증한다. 서명, 만료, issuer를 확인한다.
3. **Rate Limiting**: 클라이언트/사용자별 요청 제한을 적용한다.
4. **정책 평가**: 요청 경로, 메서드, 사용자 역할을 기반으로 접근 허용 여부를 판단한다.
5. **요청 변환**: 내부 서비스에 전달할 때 필요한 헤더(사용자 ID, 역할 등)를 추가한다.

Kong Gateway로 구현하면 이런 설정이 된다:

```yaml
# Kong 서비스 및 라우트
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
plugin: jwt
config:
  claims_to_verify:
  - exp
  - nbf
  key_claim_name: iss
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: rate-limit
plugin: rate-limiting
config:
  minute: 100
  policy: redis
  redis_host: redis.infrastructure
---
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: opa-authz
plugin: opa
config:
  opa_host: "http://localhost:8181"
  opa_path: "/v1/data/gateway/allow"
  include_consumer_in_opa_input: true
  include_route_in_opa_input: true
```

Gateway에서 인증(authentication)은 처리하되, 세밀한 인가(authorization)는 각 서비스에서 처리하는 구조가 보통이다. Gateway가 "이 토큰이 유효한 사용자인가"를 확인하고, 백엔드 서비스가 "이 사용자가 이 리소스에 접근할 수 있는가"를 결정한다.

Gateway에서 모든 인가를 처리하려고 하면 Gateway가 모든 서비스의 비즈니스 로직을 알아야 하게 된다. 이러면 Gateway가 비대해지고, 서비스 배포와 Gateway 정책 업데이트가 결합된다. 서비스가 새 API를 추가할 때마다 Gateway 설정도 같이 바꿔야 하는 상황은 피해야 한다.

## 디바이스 신뢰도 평가와 MDM API 연동

Zero Trust에서는 사용자 인증만으로는 부족하다. 인증된 사용자라도 감염된 디바이스에서 접속하면 위험하다. 디바이스 상태를 지속적으로 평가하고, 신뢰 수준에 따라 접근 범위를 조절한다.

### 디바이스 신뢰도 평가 항목

- **디바이스 등록 여부**: 회사 MDM(Mobile Device Management)에 등록된 디바이스인가. 개인 디바이스면 접근 범위를 제한한다.
- **OS 패치 수준**: 최신 보안 패치가 적용되어 있는가. 알려진 취약점이 있는 OS 버전에서의 접속은 제한한다.
- **디스크 암호화**: FileVault(macOS), BitLocker(Windows)가 활성화되어 있는가. 암호화되지 않은 디바이스는 분실 시 데이터가 노출된다.
- **보안 소프트웨어**: EDR(Endpoint Detection and Response) 에이전트가 실행 중인가.
- **탈옥/루팅**: 모바일 디바이스의 경우 탈옥/루팅 여부를 확인한다.

### 신뢰 수준에 따른 접근 제어

모든 디바이스를 허용/거부 이진으로 판단하면 운영이 어렵다. 신뢰 수준을 등급으로 나눠서, 등급에 따라 접근 가능한 리소스를 달리한다.

```
신뢰 수준 높음 (회사 관리 디바이스 + 최신 패치 + EDR 활성)
  → 모든 내부 시스템 접근 가능

신뢰 수준 중간 (회사 관리 디바이스 + 패치 지연)
  → 이메일, 문서 접근 가능. 프로덕션 시스템 접근 불가

신뢰 수준 낮음 (개인 디바이스)
  → 웹 기반 SaaS만 접근 가능. 내부 시스템 접근 불가
```

### Jamf Pro API 연동

macOS/iOS MDM으로 Jamf Pro를 쓰는 환경에서 실제 디바이스 컴플라이언스 상태를 조회하는 코드다. Jamf Pro API v2는 OAuth2 client credentials 방식으로 인증한다.

```python
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# OS별 최소 허용 버전 — 보안팀과 합의해서 주기적으로 업데이트
OS_MIN_VERSIONS = {
    "macOS": "14.0",
    "Windows": "10.0.19041",  # 20H1 이상
    "iOS": "17.0",
    "Android": "13",
}


@dataclass
class DeviceTrustResult:
    device_id: str
    serial_number: str
    is_corp_managed: bool
    os_version: str
    patch_compliant: bool
    disk_encrypted: bool
    edr_active: bool
    last_checkin: Optional[datetime]
    trust_score: int = field(init=False)
    allowed_scopes: list[str] = field(init=False)

    def __post_init__(self):
        self.trust_score = self._calc_score()
        self.allowed_scopes = self._derive_scopes()

    def _calc_score(self) -> int:
        if not self.is_corp_managed:
            return 0
        score = 40
        if self.patch_compliant:
            score += 25
        if self.disk_encrypted:
            score += 20
        if self.edr_active:
            score += 15
        return score

    def _derive_scopes(self) -> list[str]:
        if self.trust_score >= 90:
            return ["internal:*", "production:read", "production:write"]
        if self.trust_score >= 65:
            return ["internal:read", "saas:*"]
        if self.trust_score >= 40:
            return ["saas:*"]
        return []


class JamfProClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self._base = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None

    async def _refresh_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            f"{self._base}/api/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]

    async def get_device_trust(self, serial_number: str) -> Optional[DeviceTrustResult]:
        async with httpx.AsyncClient(timeout=10) as client:
            if not self._token:
                await self._refresh_token(client)

            headers = {"Authorization": f"Bearer {self._token}"}
            params = {
                "filter": f"hardware.serialNumber=={serial_number}",
                "section": ["HARDWARE", "OPERATING_SYSTEM", "DISK_ENCRYPTION", "GENERAL"],
            }

            resp = await client.get(
                f"{self._base}/api/v1/computers-inventory",
                params=params,
                headers=headers,
            )
            if resp.status_code == 401:
                await self._refresh_token(client)
                headers["Authorization"] = f"Bearer {self._token}"
                resp = await client.get(
                    f"{self._base}/api/v1/computers-inventory",
                    params=params,
                    headers=headers,
                )
            resp.raise_for_status()

            results = resp.json().get("results", [])
            if not results:
                return None

            computer = results[0]
            os_info = computer.get("operatingSystem", {})
            disk_enc = computer.get("diskEncryption", {})
            general = computer.get("general", {})

            os_version = os_info.get("version", "0.0")

            # bootPartitionFileVault2State: ENCRYPTED / NOT_ENCRYPTED / INELIGIBLE
            fv_state = disk_enc.get("bootPartitionFileVault2State", "NOT_ENCRYPTED")

            # EDR 활성 여부: Jamf Extension Attribute로 CrowdStrike/SentinelOne 상태를 별도 수집하는 게 정석.
            # 여기서는 MDM supervised 상태로 대체 — 실제 환경에서는 EA 쿼리를 추가한다.
            edr_active = general.get("supervised", False)

            last_contact = general.get("lastContactTime")
            last_checkin = None
            if last_contact:
                last_checkin = datetime.fromisoformat(
                    last_contact.replace("Z", "+00:00")
                )

            return DeviceTrustResult(
                device_id=computer["id"],
                serial_number=serial_number,
                is_corp_managed=True,
                os_version=os_version,
                patch_compliant=_version_gte(os_version, OS_MIN_VERSIONS["macOS"]),
                disk_encrypted=(fv_state == "ENCRYPTED"),
                edr_active=edr_active,
                last_checkin=last_checkin,
            )


def _version_gte(version: str, minimum: str) -> bool:
    def to_tuple(v: str) -> tuple:
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    try:
        return to_tuple(version) >= to_tuple(minimum)
    except (ValueError, AttributeError):
        return False
```

### Microsoft Intune (Graph API) 연동

Windows/Android 환경에서 Intune을 쓰는 경우 Microsoft Graph API로 디바이스 컴플라이언스를 조회한다.

```python
class IntuneClient:
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: Optional[str] = None

    async def _refresh_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]

    async def get_device_trust(self, aad_device_id: str) -> Optional[DeviceTrustResult]:
        select_fields = ",".join([
            "id", "serialNumber", "managedDeviceOwnerType",
            "osVersion", "operatingSystem", "complianceState",
            "isEncrypted", "lastSyncDateTime", "deviceRegistrationState",
        ])

        async with httpx.AsyncClient(timeout=10) as client:
            if not self._token:
                await self._refresh_token(client)

            headers = {"Authorization": f"Bearer {self._token}"}
            params = {
                "$filter": f"azureADDeviceId eq '{aad_device_id}'",
                "$select": select_fields,
            }

            resp = await client.get(
                f"{self.GRAPH_BASE}/deviceManagement/managedDevices",
                params=params,
                headers=headers,
            )
            if resp.status_code == 401:
                await self._refresh_token(client)
                headers["Authorization"] = f"Bearer {self._token}"
                resp = await client.get(
                    f"{self.GRAPH_BASE}/deviceManagement/managedDevices",
                    params=params,
                    headers=headers,
                )
            resp.raise_for_status()

            results = resp.json().get("value", [])
            if not results:
                return None

            device = results[0]
            os_type = device.get("operatingSystem", "Windows")
            os_version = device.get("osVersion", "0")
            min_ver = OS_MIN_VERSIONS.get(os_type, "0")

            # complianceState: compliant / noncompliant / unknown / notApplicable
            # Intune 컴플라이언스 정책이 설정되어 있어야 의미 있는 값이 나온다.
            patch_compliant = device.get("complianceState") == "compliant"

            last_sync = device.get("lastSyncDateTime", "")
            last_checkin = None
            if last_sync and last_sync != "0001-01-01T00:00:00Z":
                last_checkin = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))

            return DeviceTrustResult(
                device_id=device["id"],
                serial_number=device.get("serialNumber", ""),
                is_corp_managed=(device.get("managedDeviceOwnerType") == "company"),
                os_version=os_version,
                patch_compliant=patch_compliant,
                disk_encrypted=device.get("isEncrypted", False),
                edr_active=(device.get("deviceRegistrationState") == "registered"),
                last_checkin=last_checkin,
            )
```

### 토큰 갱신 시 디바이스 재평가

```python
class DeviceTrustService:
    def __init__(self, jamf: JamfProClient, intune: IntuneClient):
        self._jamf = jamf
        self._intune = intune

    async def evaluate(self, platform: str, device_identifier: str) -> DeviceTrustResult:
        if platform in ("macOS", "iOS"):
            result = await self._jamf.get_device_trust(device_identifier)
        elif platform in ("Windows", "Android"):
            result = await self._intune.get_device_trust(device_identifier)
        else:
            result = None

        if result is None:
            # MDM에 없는 디바이스 = 비관리 디바이스로 처리
            return DeviceTrustResult(
                device_id="unregistered",
                serial_number=device_identifier,
                is_corp_managed=False,
                os_version="0",
                patch_compliant=False,
                disk_encrypted=False,
                edr_active=False,
                last_checkin=None,
            )

        return result


# Access Token 갱신 엔드포인트
async def handle_token_refresh(
    refresh_token: str,
    device_id: str,
    platform: str,
) -> TokenResponse:
    user = validate_refresh_token(refresh_token)
    trust = await device_trust_service.evaluate(platform, device_id)

    if trust.trust_score < 40:
        # 심각한 미준수 상태 — 해당 디바이스의 세션 전체 종료
        await revoke_all_sessions(user.id, device_id)
        raise HTTPException(403, "Device does not meet security requirements")

    return issue_token(user, trust.allowed_scopes, ttl=900)
```

디바이스 신뢰도 평가를 직접 구축하는 게 부담스럽다면 Google BeyondCorp Enterprise, Microsoft Entra ID + Intune, Cloudflare Access + WARP처럼 통합된 SaaS를 쓰는 게 현실적이다. 특히 소규모 팀에서 MDM API 연동을 직접 개발하고 유지하는 비용이 생각보다 크다.

## Zero Trust 전환 실패 원인

Zero Trust는 기술 문제보다 운영과 조직 문제로 실패하는 경우가 더 많다. 몇 가지 패턴을 반복해서 보게 된다.

### 정책 과잉으로 생산성이 무너진다

Zero Trust 초기 도입 팀이 자주 저지르는 실수는 처음부터 정책을 너무 세밀하게 설정하는 것이다. Access Token TTL을 5분으로 설정하면, 개발자가 IDE에서 작업 중에 토큰이 만료돼서 재인증 팝업이 뜬다. `terraform apply`가 실행 도중에 크리덴셜이 만료되어 중단되는 경우도 생긴다.

서비스 간 통신에 mTLS를 적용하면서 인증서 갱신 주기를 너무 짧게 설정하면(24시간 이하), 인증서 갱신이 배포 사이클과 겹쳐서 서비스가 간헐적으로 실패한다. CertManager가 인증서를 갱신하는 타이밍에 트래픽이 짧게 끊기는 현상이 나온다.

NetworkPolicy를 기본 차단으로 설정한 직후, 개발팀이 "이거 왜 안 되냐"는 티켓을 쏟아내는 상황이 며칠간 이어질 수 있다. 관리자가 정책을 되돌리거나, 예외를 너무 많이 허용하면서 원래 목적이 흐려진다.

정책은 처음부터 엄격하게 짜는 게 아니라, 허용 범위를 파악한 뒤 점진적으로 좁혀가야 한다.

### 레거시 시스템 연동이 끊어진다

이것이 실제로 Zero Trust 전환을 막는 가장 큰 원인이다. 사내에는 반드시 OIDC/SAML을 지원하지 않는 레거시 시스템이 있다.

흔히 마주치는 케이스:
- 구형 Java EE 애플리케이션이 LDAP 직접 조회로 인증한다. ZTNA 정책 엔진을 거치지 않는다.
- Windows 환경의 NTLMv1/v2 기반 서비스. Kerberos로 전환해야 하는데, 연동된 시스템이 너무 많아서 일정이 계속 밀린다.
- DB 클라이언트 툴(DBeaver, DataGrip 등)이 직접 DB 포트에 연결해야 한다. ZTNA로 이걸 처리하려면 L4 TCP 터널이 필요한데, 제품마다 지원 방식이 다르다.
- 사내 CI/CD 시스템이 배포 스크립트에서 하드코딩된 내부 IP로 직접 SSH 접속한다.

보통 "레거시 시스템 10개 중 9개 전환 완료" 상태에서 프로젝트가 멈춘다. 나머지 1개가 너무 복잡하거나, 다른 우선순위 작업에 밀리기 때문이다. 결국 그 1개를 위해 VPN이 계속 남아있게 되고, "Zero Trust 전환 완료"가 아닌 "Zero Trust와 VPN 공존" 상태가 된다.

레거시 시스템 목록을 먼저 전수 조사하고, 연동 불가 시스템은 교체 일정을 확정해야 전환 계획이 현실적이 된다.

### 가시성 없이 차단부터 적용한다

모니터링 없이 기본 차단 정책을 바로 적용하면 어디서 무엇이 막히는지 알 수 없다. 서비스가 이상하게 동작할 때 "NetworkPolicy 때문인가, 코드 버그인가"를 구분하는 데 시간이 걸린다.

Calico의 경우 `action: Log` 모드, Istio의 경우 `AUDIT` 모드로 먼저 트래픽을 기록하고, 실제 차단 전에 최소 2주는 로그를 분석해야 한다. Prometheus가 8080 포트를 scrape하는 트래픽, Kubernetes liveness probe가 사용하는 포트, 서비스 메시의 헬스체크 경로 등 개발자가 인지하지 못하는 내부 통신이 반드시 있다.

### 사용자 마찰이 쌓인다

보안팀이 WARP 클라이언트 설치를 강제하면, 직원들이 "배터리가 빨리 닳는다", "속도가 느려졌다", "이상한 소프트웨어를 왜 설치해야 하냐"는 반응을 보인다. MFA 피로(너무 잦은 인증 요청)도 비슷한 문제다.

마찰이 쌓이면 직원들이 보안 정책을 우회하는 방법을 찾기 시작한다. 회사 계정 대신 개인 Google Drive에 파일을 올리거나, 사내 시스템 대신 외부 서비스를 쓰는 shadow IT가 늘어난다. 이러면 보안 통제 범위 밖에서 데이터가 유통된다.

사용자 경험을 최대한 투명하게 만들어야 한다. 정상적인 업무 흐름에서는 추가 인증이 발생하지 않아야 한다. 추가 마찰은 고위험 상황(새 디바이스, 비정상적 위치, 민감한 리소스 접근)에서만 발생하도록 설계해야 한다.

### 성능 비용을 과소평가한다

모든 요청이 정책 엔진을 거치면 레이턴시가 추가된다. OPA ext_authz를 Envoy 사이드카로 붙이면 요청당 5~20ms가 추가된다. API가 초당 수천 건 처리하는 서비스라면 이게 누적되어 P99 레이턴시에 영향을 준다.

mTLS handshake도 마찬가지다. 서비스 간 통신이 많은 환경에서 커넥션을 재사용하지 않으면 handshake 비용이 무시할 수 없다. Istio를 도입한 뒤 CPU 사용량이 20~30% 올라가는 경우가 흔하다. 사이드카 프록시가 모든 트래픽을 가로채고 처리하기 때문이다.

도입 전에 부하 테스트를 반드시 해야 한다. "현재 레이턴시 P99 = 50ms, 정책 엔진 추가 후 P99 = 65ms, 허용 범위인가"를 확인해야 한다. 허용 범위를 벗어나면 OPA 정책 캐싱, 커넥션 풀링, 또는 eBPF 기반 정책 적용(Cilium)으로 오버헤드를 줄이는 방법을 검토해야 한다.

## 정리

Zero Trust는 "경계를 없앤다"는 게 아니라, "경계에 의존하지 않는다"는 것이다. 방화벽이나 네트워크 분리를 없애는 게 아니고, 그것만으로는 부족하니 추가 계층을 둔다.

실제 적용은 한번에 되지 않는다. 보통 이런 순서로 진행한다:

1. 서비스 간 통신에 mTLS 적용 (서비스 메시 도입)
2. 기본 차단 NetworkPolicy 적용 + 필요한 통신만 허용
3. API Gateway에서 요청별 인증·인가 적용
4. OPA 같은 정책 엔진으로 세밀한 접근 제어
5. 디바이스 신뢰도 평가 도입
6. VPN → ZTNA 전환

각 단계마다 모니터링을 먼저 붙이고, 차단은 나중에 켜야 한다. 전환 과정에서 레거시 시스템 목록을 미리 파악하지 않으면 중간에 막힌다. 정책은 처음부터 엄격하게 짜지 않고, 트래픽 패턴을 파악한 뒤 좁혀가는 방식이 현실적이다.
