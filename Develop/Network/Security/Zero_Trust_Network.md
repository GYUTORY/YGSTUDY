---
title: Zero Trust 네트워크
tags: [network, security, zero-trust, mtls, Microsegmentation, iam, sso, spiffe, spire, aws-identity-center, policy-drift]
updated: 2026-07-27
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

## SPIFFE/SPIRE 구현 상세

SPIFFE(Secure Production Identity Framework for Everyone)는 워크로드 신원을 표준화한 명세다. SPIRE는 그 참조 구현이다. 핵심 개념은 SVID(SPIFFE Verifiable Identity Document)인데, X.509 인증서나 JWT 토큰 형태로 발급되는 워크로드 신원 증명서다.

실무에서 SPIRE를 도입하는 이유는 서비스 어카운트 토큰이나 하드코딩된 시크릿보다 신원 증명의 생명주기를 더 타이트하게 관리할 수 있기 때문이다. SVID 만료 시간을 1시간으로 설정하면 탈취된 SVID는 길어야 1시간 후 무효가 된다.

### SVID 발급·갱신 흐름

SPIRE는 SPIRE Server와 SPIRE Agent 두 컴포넌트로 구성된다. SPIRE Server가 신뢰 루트(Trust Root)를 관리하고 SVID를 발급한다. SPIRE Agent는 각 노드(Kubernetes Node, EC2 인스턴스 등)에서 실행되며 워크로드를 대신해 SVID를 가져온다.

발급 순서는 다음과 같다. SPIRE Agent가 노드에 처음 실행될 때 Node Attestation을 수행한다. AWS 환경이면 EC2 인스턴스 메타데이터로, GCP 환경이면 GCE 인스턴스 토큰으로 자신이 신뢰할 수 있는 노드임을 SPIRE Server에 증명한다. SPIRE Server가 노드 신원을 확인하면 Node SVID를 발급한다.

워크로드가 실행되면 SPIRE Agent가 Workload Attestation을 수행한다. Kubernetes 환경이면 파드의 서비스 어카운트, 네임스페이스, 라벨 같은 정보로 워크로드를 식별한다. Workload Attestation이 성공하면 SPIRE Agent는 SPIRE Server에서 해당 워크로드 SVID를 가져와 워크로드에 전달한다.

SVID 갱신은 워크로드가 직접 관리하지 않는다. SPIRE Agent가 만료 전에 자동으로 갱신하고 Workload API를 통해 새 SVID를 워크로드에 push한다. go-spiffe 같은 SDK를 쓰면 갱신이 자동 처리된다. SDK 없이 직접 구현하면 갱신 시점을 놓쳐 인증 실패가 발생한다.

```go
// go-spiffe를 사용한 SVID 자동 갱신
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

source, err := workloadapi.NewX509Source(ctx)
if err != nil {
    log.Fatalf("SVID 소스 초기화 실패: %v", err)
}
defer source.Close()

// source가 SVID 갱신을 자동으로 처리한다
// TLS 설정에 source를 넘기면 갱신된 인증서가 자동 적용된다
tlsConfig := tlsconfig.MTLSServerConfig(source, source, tlsconfig.AuthorizeAny())
```

### spire-agent 설정

Kubernetes에서 SPIRE Agent는 DaemonSet으로 배포한다.

```hcl
agent {
  data_dir      = "/run/spire/data"
  log_level     = "INFO"
  server_address = "spire-server.spire.svc.cluster.local"
  server_port   = "8081"
  socket_path   = "/run/spire/sockets/agent.sock"
}

plugins {
  NodeAttestor "k8s_psat" {
    plugin_data {
      cluster = "production-cluster"
    }
  }

  WorkloadAttestor "k8s" {
    plugin_data {
      skip_kubelet_verification = false
    }
  }

  KeyManager "memory" {
    plugin_data {}
  }
}
```

`k8s_psat` NodeAttestor는 Kubernetes의 Projected Service Account Token으로 노드 신원을 증명한다. 기존 `k8s_sat`보다 보안이 강화된 방식이다. PSAT은 audience와 expiry가 포함된 토큰이라 재사용 공격이 어렵다.

`skip_kubelet_verification = false`를 유지하지 않으면 워크로드 정보를 가져올 때 Kubelet API 인증서를 검증하지 않아 중간자 공격에 노출된다.

### Workload Attestation 방식

SPIRE Agent는 워크로드를 식별하기 위해 셀렉터를 사용한다. Kubernetes 환경에서 주로 쓰는 셀렉터는 `k8s:ns`(네임스페이스), `k8s:sa`(서비스 어카운트), `k8s:pod-label:{key}:{value}`(파드 라벨)이다.

```yaml
# SPIRE Server Registration Entry
# payments 워크로드의 SPIFFE ID 정의
spiffeID: spiffe://example.org/production/payments
parentID: spiffe://example.org/k8s-workload-registrar
selectors:
  - k8s:ns:production
  - k8s:sa:payments
  - k8s:pod-label:app:payments
```

이 설정으로 `production` 네임스페이스의 `payments` 서비스 어카운트를 가진 파드만 `spiffe://example.org/production/payments` SVID를 발급받는다. 라벨이 다르거나 네임스페이스가 다른 파드는 동일한 서비스 어카운트를 써도 SVID를 받지 못한다.

셀렉터를 너무 느슨하게 잡으면 의도하지 않은 워크로드가 SVID를 발급받는 경우가 생긴다. 서비스 어카운트만 지정하고 네임스페이스를 빠뜨리면 다른 네임스페이스의 같은 이름 서비스 어카운트도 해당 SVID를 받는다. 셀렉터 조합을 최대한 좁게 잡는 게 맞다.

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

이렇게 하면 payments 서비스는 orders 서비스 어카운트에서 POST /api/v1/charge로 오는 요청만 받는다. admin 서비스나 monitoring이 payments를 직접 호출하려 하면 정책 위반으로 거부된다.

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

## AWS IAM Identity Center + SCP 조합

AWS 멀티 계정 환경에서 Zero Trust를 적용할 때 IAM Identity Center(구 AWS SSO)와 SCP(Service Control Policies) 조합을 쓴다.

IAM Identity Center는 사람 ID를 관리한다. 개발자가 AWS 콘솔이나 CLI에 접근할 때 회사 IdP(Okta, Azure AD)로 인증하고, IAM Identity Center가 Permission Set을 통해 계정별 임시 크레덴셜을 발급한다. 각 개발자는 자신이 접근 가능한 계정과 역할만 볼 수 있다. 이 구조에서 개발자는 장기 IAM Access Key를 가지지 않는다. 크레덴셜이 탈취돼도 임시 토큰이라 만료 후 쓸 수 없다.

SCP는 계정 수준 가드레일이다. IAM 정책이 "무엇을 허용하는가"를 정의한다면, SCP는 "무엇을 절대 허용하지 않는가"를 정의한다. 계정 내 루트 유저나 AdministratorAccess 권한을 가진 IAM 유저도 SCP가 막으면 해당 작업을 수행할 수 없다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyOutsideApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "sts:*",
        "s3:GetBucketLocation",
        "cloudfront:*",
        "route53:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["ap-northeast-2", "us-east-1"]
        }
      }
    }
  ]
}
```

이 SCP를 OU에 연결하면 해당 OU 아래 계정들은 IAM에서 어떤 권한을 부여해도 승인된 리전 외에는 리소스를 만들 수 없다. 실수로 도쿄 리전에 EC2를 띄우거나, 탈취된 크레덴셜로 다른 리전에 인프라를 올리는 걸 막는다. `NotAction`을 써서 전역 서비스(IAM, CloudFront, Route53)는 제외한 게 포인트다. IAM까지 막으면 리전 제한 SCP 자체를 관리할 수 없다.

### 계정 간 최소 권한 적용

멀티 계정에서 계정 간 접근은 Role Chaining으로 구현한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ANALYTICS-ACCOUNT-ID:role/analytics-job-role"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "analytics-to-data-prod"
        }
      }
    }
  ]
}
```

ExternalId를 필수로 요구하면 혼동된 대리인(confused deputy) 공격을 방어한다. ExternalId 없이 신뢰 정책만 설정하면 신뢰 관계를 가진 어떤 계정에서든 그 역할을 assume할 수 있는 상황이 생긴다.

### ABAC으로 태그 기반 접근 제어

계정이 많아질수록 역할별 정책을 일일이 관리하기 어려워진다. ABAC(Attribute-Based Access Control)을 쓰면 태그 기반으로 접근을 제어해 정책 수를 줄인다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:StartInstances", "ec2:StopInstances"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/team": "${aws:PrincipalTag/team}"
        }
      }
    }
  ]
}
```

payments 팀 개발자는 `team: payments` 태그가 붙은 EC2만 조작할 수 있다. 태그를 바꾸지 않는 한 다른 팀 리소스는 건드릴 수 없다. IAM Identity Center의 Permission Set에서 PrincipalTag를 세션 태그로 전달하면 이 정책이 사람 ID와 연동된다.

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

## Zero Trust 이벤트 로깅 구성

### 수집해야 할 이벤트

**접근 거부 이벤트.** 정책이 요청을 막은 순간의 기록이다. 단순히 "거부됐다"가 아니라 어떤 정책이, 어떤 이유로 거부했는지가 담겨야 한다. Istio 환경에서는 Envoy access log가 이를 담당한다.

Envoy가 남기는 `response_flags` 필드에서 접근 거부 원인을 구분할 수 있다. `UAEX`는 AuthorizationPolicy에 의한 거부, `UMSDR`은 upstream 연결 실패다. 403과 함께 `UAEX`가 나오면 어떤 서비스 어카운트가 허용되지 않은 경로를 호출했는지 즉시 특정할 수 있다.

JSON 형태로 Envoy access log를 구성하면 CloudWatch Logs Insights나 Elasticsearch에서 쿼리하기 편하다.

```json
{
  "start_time": "%START_TIME%",
  "method": "%REQ(:METHOD)%",
  "path": "%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%",
  "response_code": "%RESPONSE_CODE%",
  "response_flags": "%RESPONSE_FLAGS%",
  "upstream_cluster": "%UPSTREAM_CLUSTER%",
  "source_principal": "%CONNECTION_TERMINATION_DETAILS%",
  "request_id": "%REQ(X-REQUEST-ID)%"
}
```

**인증 실패 이벤트.** mTLS 핸드셰이크 실패, JWT 검증 실패, OIDC 토큰 만료 등이다. 인증 실패는 접근 거부와 다르다. 인증 실패는 신원 자체를 확인하지 못한 경우고, 접근 거부는 신원은 확인됐지만 권한이 없는 경우다. 둘을 구분해야 대응 방식이 달라진다. mTLS 핸드셰이크 실패가 반복된다면 인증서 만료나 신뢰 체인 문제를 먼저 확인한다.

**권한 상승 시도.** AssumeRole 실패, sudo 시도, 서비스 어카운트 토큰 직접 사용 등이다. AWS 환경에서는 CloudTrail의 `AssumeRole` 이벤트 중 `errorCode`가 `AccessDenied`인 것들을 따로 수집해야 한다.

**비정상 접근 패턴.** 평소에 없던 시간대의 접근, 평소보다 많은 요청량, 새로운 소스 IP 등이다. 이건 단순 임계값 규칙으로는 false positive가 많다. 처음엔 임계값을 높게 잡고 운영하면서 점점 좁혀가는 방식이 현실적이다.

### 이상 탐지 규칙

로그를 쌓는 것 자체는 의미가 없다. 탐지 규칙 없이 로그만 있으면 사고가 난 뒤에야 유용하다.

같은 서비스 어카운트에서 짧은 시간 안에 403이 폭발적으로 발생하면, 그 서비스가 공격 당하거나 잘못된 배포가 나간 상황일 가능성이 높다.

```
# CloudWatch Logs Insights 쿼리
# 5분 window 안에 403을 50회 이상 낸 서비스 어카운트 탐지
fields @timestamp, source_principal, response_code
| filter response_code = 403
| stats count(*) as deny_count by source_principal, bin(5m)
| filter deny_count > 50
| sort deny_count desc
```

서비스 메시 텔레메트리에서 이전에 없던 서비스 쌍의 트래픽이 나타나면 즉시 확인한다. 새 배포라면 의도된 변경인지 확인하고, 배포가 없었다면 lateral movement를 의심한다.

AWS에서 AssumeRole AccessDenied 이벤트가 몰리면 알림을 낸다.

```json
{
  "filterPattern": "{ ($.eventName = AssumeRole) && ($.errorCode = AccessDenied) }",
  "metricName": "AssumeRoleAccessDenied",
  "metricNamespace": "SecurityMetrics",
  "metricValue": "1"
}
```

이 메트릭에 Alarm을 걸어 5분 내 10회를 넘으면 SNS로 알림을 보낸다. 공격자가 탈취한 크레덴셜로 여러 역할을 assume 시도하는 패턴이 이 규칙에 걸린다.

크레덴셜 사용 위치 변화도 탐지 대상이다. CloudTrail 이벤트의 `sourceIPAddress`와 평소 접근 IP 목록을 비교해 새로운 IP 대역에서 접근이 오면 경보를 낸다. 개인 개발자 IP는 가변적이라 false positive가 많지만, CI/CD 시스템이나 서버 크레덴셜은 IP 범위가 고정적이라 탐지 정확도가 높다.

---

## 정책 drift 탐지

정책 drift는 코드로 정의한 정책과 실제 적용된 정책이 달라지는 현상이다. 누군가 콘솔에서 직접 IAM 정책을 수정했거나, 긴급 대응 중에 임시로 권한을 열어놓고 되돌리는 걸 잊었거나, Terraform state와 실제 인프라가 sync를 잃은 경우가 해당한다.

drift가 문제인 이유는 조용하기 때문이다. 배포가 실패하거나 서비스가 죽는 게 아니라, 정책이 의도보다 넓게 열린 채로 운영이 계속된다.

### Terraform drift 탐지

`terraform plan`의 종료 코드가 drift 여부를 나타낸다. 종료 코드 0은 변경 없음, 2는 변경 있음이다. 변경이 없어야 하는 환경에서 2가 나오면 코드 외부에서 누군가 인프라를 손댄 것이다.

```bash
# GitHub Actions에서 drift 감지 예시
- name: Terraform Plan (drift detection)
  run: |
    terraform plan -detailed-exitcode -out=tfplan
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 2 ]; then
      echo "DRIFT_DETECTED=true" >> $GITHUB_ENV
    fi

- name: Notify on drift
  if: env.DRIFT_DETECTED == 'true'
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Terraform drift detected in production. Review the plan output."
      }
```

이 파이프라인을 cron으로 매 시간 실행하면 drift를 발생 직후 잡아낼 수 있다. `terraform plan` 결과를 S3에 저장해두면 어떤 리소스가 얼마나 변경됐는지 이력을 추적할 수 있다.

### Kubernetes 정책 drift

ArgoCD를 쓰면 `OutOfSync` 상태가 drift를 나타낸다. auto-sync 설정이 아닌 경우 OutOfSync 알림을 Slack이나 PagerDuty로 받아야 한다. 설정 없이 두면 OutOfSync 상태가 쌓여도 모른다.

OPA Gatekeeper나 Kyverno를 쓰면 drift가 발생하기 전에 막는다.

```yaml
# Kyverno 정책: 모든 파드에 서비스 어카운트 명시 강제
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-explicit-service-account
spec:
  validationFailureAction: Enforce
  rules:
  - name: check-service-account
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "서비스 어카운트를 명시해야 한다."
      pattern:
        spec:
          serviceAccountName: "?*"
          automountServiceAccountToken: false
```

`automountServiceAccountToken: false`를 강제하면 기본 서비스 어카운트 토큰이 파드에 자동 마운트되는 걸 막는다. 필요하지 않은 토큰은 파드에 있으면 안 된다. 이 정책 없이 운영하면 default 서비스 어카운트 토큰이 모든 파드에 마운트되는 상태가 오래 방치되는 경우가 많다.

### AWS Config로 drift 탐지

AWS Config는 리소스 설정 변경을 지속적으로 추적한다. 관리형 규칙과 커스텀 규칙으로 원하는 상태를 정의하고, 실제 상태가 다를 때 NonCompliant로 표시한다.

```python
# AWS Config 커스텀 규칙: MFA 없는 IAM 유저 탐지
import json
import boto3

def lambda_handler(event, context):
    iam = boto3.client('iam')
    config = boto3.client('config')

    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event['configurationItem']

    if configuration_item['resourceType'] != 'AWS::IAM::User':
        return

    user_name = configuration_item['resourceName']
    mfa_devices = iam.list_mfa_devices(UserName=user_name)
    compliance = 'COMPLIANT' if mfa_devices['MFADevices'] else 'NON_COMPLIANT'

    config.put_evaluations(
        Evaluations=[{
            'ComplianceResourceType': 'AWS::IAM::User',
            'ComplianceResourceId': user_name,
            'ComplianceType': compliance,
            'Annotation': 'MFA 디바이스 없는 IAM 유저',
            'OrderingTimestamp': configuration_item['configurationItemCaptureTime']
        }],
        ResultToken=event['resultToken']
    )
```

NonCompliant 리소스가 나오면 EventBridge로 Security Hub나 Slack에 알림을 보낸다. 콘솔에서 직접 수정한 IAM 정책, 허용 범위를 넘어선 보안 그룹 변경 같은 것들을 실시간으로 잡아낸다.

drift 탐지에서 중요한 건 탐지 후 대응 절차다. 탐지만 하고 되돌리는 프로세스가 없으면 drift 목록만 쌓인다. 발견된 drift는 PR로 코드에 반영하거나 즉시 원상 복구하는 두 경로 중 하나를 타야 한다. 어느 쪽도 아닌 "일단 알겠다"는 상태가 쌓이면 drift 탐지 시스템 자체를 신뢰하기 어려워진다.

---

## 단계적 전환

Zero Trust를 한 번에 전사 적용하는 건 현실적으로 어렵다. 일반적으로 쓰는 순서는 다음과 같다.

먼저 IdP와 SSO부터 표준화한다. 모든 서비스가 같은 IdP를 바라보게 만드는 게 기반이다. 이 단계 없이 마이크로세그멘테이션을 먼저 하면 나중에 ID 기반 정책으로 전환할 때 다시 다 뜯어야 한다.

다음으로 서비스 메시를 도입해 서비스 간 트래픽을 가시화한다. permissive 모드로 운영하면서 실제로 어떤 서비스가 어디에 통신하는지 파악한다. 이 데이터 없이 정책을 짜면 허용해야 할 통신을 막는 실수가 생긴다.

가시화가 끝난 뒤 트래픽 패턴을 바탕으로 마이크로세그멘테이션 정책을 작성하고 단계적으로 strict 모드로 전환한다. 한 번에 전체를 바꾸지 말고 낮은 위험도 서비스부터 시작해 문제를 좁은 범위에서 잡는다.
