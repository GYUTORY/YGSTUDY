---
title: "Zero Trust Architecture"
tags: [Security, Zero-Trust, BeyondCorp, ZTNA, Microsegmentation, OPA]
updated: 2026-04-08
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

## 디바이스 신뢰도 평가와 지속적 검증

Zero Trust에서는 사용자 인증만으로는 부족하다. 인증된 사용자라도 감염된 디바이스에서 접속하면 위험하다. 그래서 디바이스 상태를 지속적으로 평가하고, 신뢰 수준에 따라 접근 범위를 조절한다.

### 디바이스 신뢰도 평가 항목

디바이스를 평가할 때 보는 항목:

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

### 지속적 검증

인증 시점에만 디바이스를 확인하면 안 된다. 세션 유지 중에 디바이스 상태가 바뀔 수 있다. EDR이 종료되거나, 네트워크가 변경되거나, 의심스러운 프로세스가 실행될 수 있다.

지속적 검증을 구현하는 방법:

**짧은 토큰 수명**: Access Token의 수명을 5~15분으로 짧게 설정한다. 토큰 갱신 시마다 디바이스 상태를 재평가한다. 디바이스 상태가 변경되었으면 갱신을 거부한다.

**디바이스 상태 이벤트 구독**: MDM/EDR에서 디바이스 상태 변경 이벤트를 받아서, 해당 디바이스의 세션을 즉시 무효화한다. 예를 들어 EDR이 맬웨어를 탐지하면 해당 디바이스의 모든 활성 세션을 끊는다.

```python
# 의사 코드 — 토큰 갱신 시 디바이스 상태 재검증
def refresh_token(refresh_token, device_id):
    user = validate_refresh_token(refresh_token)
    device = get_device_state(device_id)

    if device.compliance_status != "COMPLIANT":
        revoke_all_sessions(user.id, device_id)
        raise AccessDenied("디바이스가 정책을 충족하지 않음")

    if device.risk_score > RISK_THRESHOLD:
        # 완전 차단 대신 접근 범위 축소
        scopes = get_reduced_scopes(device.risk_score)
        return issue_token(user, scopes, ttl=300)

    return issue_token(user, user.default_scopes, ttl=900)
```

디바이스 신뢰도 평가를 직접 구축하려면 MDM API 연동, 디바이스 인증서 발급, 상태 수집 에이전트 개발 등이 필요하다. 규모가 작은 조직이라면 Google BeyondCorp Enterprise, Microsoft Entra ID + Intune, Cloudflare Access + WARP 같은 SaaS를 쓰는 게 현실적이다.

## 정리

Zero Trust는 "경계를 없앤다"는 게 아니라, "경계에 의존하지 않는다"는 것이다. 방화벽이나 네트워크 분리를 없애는 게 아니고, 그것만으로는 부족하니 추가 계층을 둔다.

실제 적용은 한번에 되지 않는다. 보통 이런 순서로 진행한다:

1. 서비스 간 통신에 mTLS 적용 (서비스 메시 도입)
2. 기본 차단 NetworkPolicy 적용 + 필요한 통신만 허용
3. API Gateway에서 요청별 인증·인가 적용
4. OPA 같은 정책 엔진으로 세밀한 접근 제어
5. 디바이스 신뢰도 평가 도입
6. VPN → ZTNA 전환

각 단계마다 모니터링을 먼저 붙이고, 차단은 나중에 켜야 한다. 모니터링 없이 차단부터 하면 정상 트래픽을 막아서 장애가 난다. 한번에 전환하려고 하면 실패한다. 기존 환경에서 점진적으로 전환하는 게 핵심이다.
