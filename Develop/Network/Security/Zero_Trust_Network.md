---
title: Zero Trust 네트워크
tags: [network, security, zero-trust, mtls, microsegmentation, iam, sso, private-network]
updated: 2026-07-25
---

# Zero Trust 네트워크

## 기존 경계 보안 모델의 문제

전통적인 네트워크 보안은 성벽 모델(castle-and-moat)로 불린다. 방화벽, VPN, DMZ 같은 경계 장치로 내부와 외부를 나누고, 내부망에 들어온 트래픽은 신뢰한다는 전제로 설계된다. 사내망 IP 대역에서 오는 요청은 별도 인증 없이 DB나 내부 API에 접근할 수 있다.

이 모델이 깨지는 순간은 크게 두 가지다. 첫째, 내부 직원의 계정이 탈취되거나 내부자가 악의적 행동을 하면 경계를 넘어온 뒤라 막을 방법이 없다. 둘째, 클라우드·SaaS 도입으로 트래픽이 더 이상 물리적 경계 안에만 있지 않다. 개발자가 GitHub Codespace로 작업하고, CI/CD 파이프라인이 외부 클라우드에서 돌고, 슬랙이나 노션 같은 SaaS가 내부 데이터를 처리한다. 이 상황에서 "내부망 = 안전"이라는 가정 자체가 성립하지 않는다.

실제로 2020년 SolarWinds 사태나 2021년 Colonial Pipeline 침해 모두 초기 침투 이후 내부망 횡이동(lateral movement)이 피해를 키웠다. 공격자가 경계를 뚫은 뒤 내부에서 자유롭게 이동할 수 있었던 게 문제였다.

---

## Zero Trust의 핵심 전제

Zero Trust는 위치(네트워크 위치, IP)를 신뢰 근거로 삼지 않는다. 내부망이든 외부망이든 모든 요청은 동일하게 검증한다.

구체적으로 다음 세 원칙으로 동작한다.

**항상 검증한다.** 모든 접근 요청에 대해 신원(identity), 디바이스 상태, 요청 컨텍스트를 확인한다. 한 번 로그인했다고 세션 내내 신뢰하지 않는다.

**최소 권한만 준다.** 필요한 리소스에만, 필요한 시간 동안만 접근 권한을 준다. 개발자가 프로덕션 DB에 접근할 필요가 없으면 아예 권한 자체가 없어야 한다.

**침해를 가정한다.** 어느 노드가 이미 탈취됐다고 가정하고 설계한다. 하나가 뚫려도 옆으로 퍼지지 않도록 세그먼트를 나눈다.

---

## ID 기반 접근 제어

Zero Trust에서 신뢰의 기준은 IP가 아니라 ID다. 여기서 ID는 사람(직원), 서비스(마이크로서비스), 디바이스(노트북, 서버) 세 종류를 포함한다.

사람 ID는 IdP(Identity Provider)와 SSO로 관리한다. Okta, Azure AD, Google Workspace 같은 IdP가 인증을 담당하고, 나머지 서비스들은 OIDC나 SAML을 통해 그 결과를 받아쓴다. 중요한 건 IdP가 단순히 "로그인됐는지"만 확인하는 게 아니라, 지금 접근하는 리소스에 접근할 권한이 있는지, 디바이스가 MDM 정책을 따르고 있는지, 로그인 위치가 평소와 다른지 같은 컨텍스트를 함께 본다는 점이다.

서비스 ID는 서비스 어카운트나 서비스 메시에서 발급하는 SPIFFE/SPIRE 기반 인증서로 처리한다. 서비스 A가 서비스 B를 호출할 때 "같은 클러스터 안에 있으니까 괜찮겠지"가 아니라, A가 누구인지 B가 직접 검증한다.

---

## 마이크로세그멘테이션

기존 경계 보안이 외벽 하나로 전체를 감쌌다면, 마이크로세그멘테이션은 내부를 잘게 나눠 각 세그먼트 간 통신도 허가 목록 기반으로 제어한다.

실무에서 가장 흔한 구현은 서비스 메시(Istio, Linkerd)의 NetworkPolicy 또는 AuthorizationPolicy다.

```yaml
# Istio AuthorizationPolicy 예시
# payments 서비스는 orders 서비스에서 오는 요청만 허용
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payments-allow-orders
  namespace: production
spec:
  selector:
    matchLabels:
      app: payments
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/orders"]
    to:
    - operation:
        methods: ["POST"]
        paths: ["/api/v1/charge"]
```

이렇게 하면 payments 서비스는 orders 서비스 서비스 어카운트에서 POST /api/v1/charge 로 오는 요청만 받는다. admin 서비스나 monitoring이 payments를 직접 호출하려 하면 정책 위반으로 거부된다.

Kubernetes 레벨에서는 NetworkPolicy로 Pod 간 트래픽을 제어한다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payments-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: payments
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: orders
    ports:
    - protocol: TCP
      port: 8080
```

---

## mTLS 전사 적용 시 실제로 겪는 문제

Zero Trust 문서에서 mTLS를 "모든 서비스 간 통신에 적용하면 된다"고 쉽게 쓰는데, 전사 적용은 생각보다 복잡하다.

**인증서 수명 관리.** 서비스 메시가 자동으로 인증서를 발급·갱신해주지만, 만료 시점이 겹치면 한꺼번에 여러 서비스가 인증 실패를 낸다. Istio의 기본 인증서 수명이 24시간인데, 트래픽이 많은 시간대에 갱신이 몰리면 간헐적 연결 오류가 난다. `PILOT_CERT_PROVIDER`, `CITADEL_SELF_SIGNED_CA_CERT_TTL` 같은 설정을 환경에 맞게 조정해야 한다.

**레거시 서비스 연동.** mTLS를 강제하기 전에 permissive 모드로 전환해 평문도 허용하면서 점진적으로 전환하는 게 일반적이다. 문제는 permissive 기간이 길어질수록 "전환하려다 잊어버린" 서비스들이 쌓인다는 점이다. 전환 완료 시점을 추적하는 별도 작업이 필요하다.

**디버깅이 어려워진다.** 평문 TCP 시절에는 tcpdump로 바로 패킷을 볼 수 있었는데, mTLS 이후에는 암호화된 페이로드만 보인다. Envoy 사이드카의 access log, `istioctl proxy-config` 명령, Kiali 같은 관측 도구 없이는 연결 문제를 추적하기 어렵다.

---

## SSO 연동 복잡도

Zero Trust 도입에서 SSO 연동은 가장 시간이 많이 드는 작업이다. 모든 내부 서비스와 SaaS가 동일한 IdP를 바라봐야 하는데, 실제 조직에는 수십 개의 내부 툴이 있고 각각의 인증 방식이 다르다.

SAML을 지원하는 서비스는 IdP에서 메타데이터 XML을 받아 설정하면 되는데, 문제는 SAML assertion의 attribute 이름이 서비스마다 다르다는 점이다. 어떤 서비스는 `email`, 어떤 서비스는 `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` 를 기대한다. IdP에서 attribute mapping을 서비스별로 따로 설정해야 하고, 설정 실수 시 로그인 자체가 안 되기 때문에 스테이징에서 반드시 검증해야 한다.

OIDC는 SAML보다 단순하지만 콜백 URL 화이트리스트 관리가 번거롭다. 개발/스테이징/프로덕션마다 콜백 URL이 다르고, 도메인이 바뀌거나 새 환경이 생길 때마다 IdP 설정을 업데이트해야 한다. 자동화 없이 손으로 관리하면 "왜 로그인이 안 되지?"라는 문의가 계속 들어온다.

레거시 서비스 중 LDAP만 지원하는 경우가 있다. IdP 대부분이 LDAP 게이트웨이를 제공하지만, 그 게이트웨이가 단일 장애 지점이 된다. 게이트웨이가 내려가면 LDAP 의존 서비스 전체 로그인이 막힌다. 이중화 구성이 필수다.

---

## 정책 관리 부담

마이크로세그멘테이션과 최소 권한 원칙을 동시에 적용하면 관리해야 할 정책 수가 기하급수적으로 늘어난다.

서비스가 30개라면 서비스 간 허용 통신 매트릭스를 관리해야 한다. 새 서비스가 추가될 때마다 "이 서비스는 어디에 접근해야 하는가"를 검토하고 정책을 업데이트해야 한다. 이걸 수동으로 하면 실수가 생긴다. 허용해야 할 통신을 빠뜨리면 프로덕션 장애가 나고, 반대로 불필요한 허용이 남아 있으면 Zero Trust의 의미가 없다.

실무에서 이 문제를 다루는 방식은 정책을 코드로 관리(Policy as Code)하는 것이다. OPA(Open Policy Agent)나 Terraform을 써서 정책을 버전 관리하고 변경 시 리뷰 프로세스를 거치게 한다.

```rego
# OPA 정책 예시: orders 서비스만 payments에 POST 가능
package istio.authz

import future.keywords.if

default allow := false

allow if {
    input.source.principal == "cluster.local/ns/production/sa/orders"
    input.request.http.method == "POST"
    startswith(input.request.http.path, "/api/v1/charge")
}
```

정책을 코드로 관리해도 "어떤 서비스가 어떤 리소스에 접근해야 하는지"를 처음부터 정확히 정의하기가 어렵다. 이 작업은 개발팀과 인프라팀이 함께 해야 하는데, 개발팀 입장에서는 왜 이런 걸 일일이 신청해야 하는지 불만이 나온다. 도입 초기에 이 프로세스를 어떻게 설계하느냐가 실제 운영 가능 여부를 결정한다.

---

## 단계적 전환

Zero Trust를 한 번에 전사 적용하는 건 현실적으로 어렵다. 일반적으로 쓰는 순서는 다음과 같다.

먼저 IdP와 SSO부터 표준화한다. 모든 서비스가 같은 IdP를 바라보게 만드는 게 기반이다. 이 단계 없이 마이크로세그멘테이션을 먼저 하면 나중에 ID 기반 정책으로 전환할 때 다시 다 뜯어야 한다.

다음으로 서비스 메시를 도입해 서비스 간 트래픽을 가시화한다. permissive 모드로 운영하면서 실제로 어떤 서비스가 어디에 통신하는지 파악한다. 이 데이터 없이 정책을 짜면 허용해야 할 통신을 막는 실수가 생긴다.

가시화가 끝난 뒤 트래픽 패턴을 바탕으로 마이크로세그멘테이션 정책을 작성하고 단계적으로 strict 모드로 전환한다. 한 번에 전체를 바꾸지 말고 낮은 위험도 서비스부터 시작해 문제를 좁은 범위에서 잡는다.
