---
title: 망분리와 네트워크 세그멘테이션
tags: [network, security, segmentation, DMZ, VLAN, vpc, Microsegmentation]
updated: 2026-08-02
---

# 망분리와 네트워크 세그멘테이션

망분리는 네트워크를 목적과 신뢰 수준에 따라 물리적 또는 논리적으로 나누는 것이다. 공격자가 한 구간을 뚫더라도 다른 구간으로 자유롭게 이동하지 못하도록 막는 게 핵심이다. 방화벽 하나 세워두고 끝내는 방식과 달리, 구간마다 트래픽 허용 정책을 별도로 정의해야 한다.

## DMZ 3티어 구조

가장 고전적인 형태다. 외부망, DMZ, 내부망 세 구간으로 나눈다.

```
인터넷
  |
[외부 방화벽]
  |
DMZ (비무장지대)
  - 웹 서버
  - 리버스 프록시
  - 메일 서버
  |
[내부 방화벽]
  |
내부망
  - DB 서버
  - 내부 API 서버
  - 관리자 시스템
```

**외부망 → DMZ**: 인터넷에서 DMZ로 들어오는 트래픽은 80, 443 포트만 허용한다. DMZ의 웹 서버가 직접 인터넷에 노출된다.

**DMZ → 내부망**: DMZ에 있는 웹 서버가 DB에 접근할 때는 내부 방화벽을 거친다. 허용 규칙은 최소화한다. 예를 들어 웹 서버 IP에서 DB 서버 IP의 3306 포트만 허용하는 식이다.

**내부망 → DMZ**: 내부에서 DMZ 쪽으로 나가는 것도 통제한다. 관리자가 SSH로 DMZ 서버에 붙을 때 22 포트를 열어두는데, 이 방향 규칙을 빠뜨리는 경우가 많다.

DMZ 설계에서 자주 빠지는 부분이 있다. DMZ 서버가 소프트웨어 업데이트나 외부 API를 호출할 때 외부망으로 나가는 Egress 정책이다. Ingress만 막아두고 Egress는 전부 허용해두면 공격자가 DMZ를 뚫은 뒤 외부 C2 서버로 데이터를 빼낼 수 있다.

## VLAN 기반 망분리

물리 스위치를 여러 대 두지 않고 하나의 스위치에서 논리적으로 구간을 나눈다. 각 VLAN은 별개의 브로드캐스트 도메인이라 서로 통신하려면 L3 라우터나 L3 스위치를 거쳐야 한다.

```
스위치 (트렁크 포트)
  |
  ├── VLAN 10 (개발망): 192.168.10.0/24
  ├── VLAN 20 (운영망): 192.168.20.0/24
  ├── VLAN 30 (DB망):   192.168.30.0/24
  └── VLAN 40 (관리망): 192.168.40.0/24
```

VLAN 간 라우팅은 L3 스위치의 ACL로 제어한다. 개발망에서 운영망 DB로 직접 붙지 못하게 막는 식이다.

```
! Cisco IOS ACL 예시
ip access-list extended BLOCK_DEV_TO_PROD_DB
 deny   ip 192.168.10.0 0.0.0.255 192.168.30.0 0.0.0.255
 permit ip any any
```

VLAN 기반 분리의 단점은 스위치 설정이 복잡해질수록 관리하기 어렵다는 점이다. VLAN ID 할당, 트렁크 설정, ACL이 뒤섞이면 규칙 충돌이 생긴다. 운영하다 보면 "왜 이 VLAN이 저 VLAN에 접근이 되지?"라는 질문이 나오는 순간이 있는데, ACL 순서 문제인 경우가 대부분이다.

## 클라우드에서의 망분리

클라우드는 물리 장비를 건드리지 않아도 되지만 개념 자체는 동일하다. AWS 기준으로 설명한다.

### VPC 분리

목적이 완전히 다른 환경은 VPC 자체를 나눈다.

```
Production VPC (10.0.0.0/16)
  ├── Public Subnet  (10.0.1.0/24) - ALB, NAT GW
  ├── Private Subnet (10.0.2.0/24) - App Server
  └── DB Subnet      (10.0.3.0/24) - RDS

Development VPC (10.1.0.0/16)
  ├── Public Subnet  (10.1.1.0/24)
  └── Private Subnet (10.1.2.0/24)
```

VPC 간 통신이 필요하면 VPC Peering이나 Transit Gateway를 쓴다. Peering은 두 VPC 사이만 연결되고 전이적 라우팅이 안 된다는 점을 주의해야 한다. A↔B, B↔C가 연결돼 있어도 A에서 C로 B를 경유해서 갈 수 없다.

### Security Group

인스턴스 단위로 붙는 상태 기반(stateful) 방화벽이다. Inbound를 허용하면 해당 세션의 Outbound는 자동으로 허용된다.

```hcl
# App Server Security Group
resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.db.id]
  }
}

# DB Security Group
resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
```

IP를 하드코딩하지 않고 Security Group ID를 참조하는 게 맞다. IP로 걸어두면 인스턴스가 교체될 때마다 규칙을 바꿔야 한다.

### NACL

서브넷 단위로 붙는 상태 비저장(stateless) 방화벽이다. Inbound와 Outbound를 각각 명시해야 한다. Security Group보다 우선순위가 높은 게 아니라 먼저 평가된다.

```
NACL (DB Subnet)
Inbound:
  100  Allow  TCP  10.0.2.0/24  3306   (App Subnet에서 들어오는 것만)
  *    Deny   ALL  ALL

Outbound:
  100  Allow  TCP  10.0.2.0/24  1024-65535  (응답 포트 허용)
  *    Deny   ALL  ALL
```

NACL에서 Outbound에 Ephemeral Port(1024-65535)를 빠뜨리는 실수가 흔하다. TCP 응답 패킷이 임시 포트를 사용하는데 이걸 허용 안 하면 연결 자체는 맺혀도 데이터가 안 온다.

## 마이크로세그멘테이션

컨테이너 환경에서는 서비스 단위로 더 잘게 나눈다. 같은 VPC, 같은 서브넷 안에 있어도 서비스마다 통신 정책을 별도로 적용한다.

Kubernetes에서는 NetworkPolicy로 Pod 간 트래픽을 제어한다.

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
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: order-service
      ports:
        - protocol: TCP
          port: 8080
```

이 정책은 payment-service로 들어오는 트래픽 중 order-service에서 오는 것만 허용한다. Namespace 단위 격리가 필요하면 `namespaceSelector`를 함께 쓴다.

NetworkPolicy는 CNI 플러그인이 구현체다. Calico, Cilium 같은 CNI를 쓰지 않으면 정책을 만들어도 실제로 적용되지 않는다. kube-proxy 기본 설정으로는 NetworkPolicy가 작동하지 않는다.

서비스 메시(Istio, Linkerd)를 쓰면 L7 수준까지 제어할 수 있다. 특정 HTTP 메서드나 경로만 허용하는 식이다.

```yaml
# Istio AuthorizationPolicy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payment-access
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/production/sa/order-service"]
      to:
        - operation:
            methods: ["POST"]
            paths: ["/api/v1/payment/*"]
```

## 망분리 설계 실수와 트러블슈팅

### 케이스 1: Security Group 체인 실수

운영 중 주문 서비스에서 결제 서비스 호출이 안 된다는 장애가 들어왔다. 인스턴스는 멀쩡하고 서비스도 뜨는데 연결이 안 됐다.

확인해보니 결제 서비스 Security Group의 Inbound 규칙에 주문 서비스 Security Group을 참조하는 대신 주문 서비스 인스턴스 IP를 직접 박아뒀다. 그날 오전 주문 서비스 인스턴스를 교체하면서 IP가 바뀐 게 원인이었다.

Security Group 참조 방식으로 바꾸고 해결했다. IP를 직접 쓰는 규칙은 결국 어느 시점에 터진다.

### 케이스 2: NACL Outbound 누락

새 DB 서브넷을 만들고 NACL을 별도로 설정했다. 연결 테스트는 됐는데 쿼리 결과가 안 돌아왔다.

Inbound에 3306 허용은 있었고 Security Group도 맞았다. NACL Outbound 규칙을 보니 Ephemeral Port 범위가 없었다. TCP 3-way handshake는 맺혔지만 응답 데이터가 나가지 못한 것이었다.

NACL을 수정할 때는 반드시 Outbound에 1024-65535 범위를 같이 추가해야 한다.

### 케이스 3: VPC Peering 라우트 테이블 누락

두 VPC를 Peering으로 연결했는데 A VPC의 인스턴스에서 B VPC 인스턴스에 ping이 안 됐다.

VPC Peering은 연결만 하면 끝이 아니다. 각 VPC의 라우트 테이블에 상대방 CIDR로 가는 경로를 Peering Connection을 통해 가도록 추가해야 한다.

```
A VPC 라우트 테이블:
  10.1.0.0/16  →  pcx-xxxxxxxxx  (Peering Connection)

B VPC 라우트 테이블:
  10.0.0.0/16  →  pcx-xxxxxxxxx  (Peering Connection)
```

양쪽 모두 추가해야 한다. 한쪽만 하면 단방향이라 응답이 안 온다.

### 케이스 4: Kubernetes NetworkPolicy 미적용

클러스터에 NetworkPolicy를 배포했는데 아무 서비스나 다 접근이 됐다.

확인해보니 CNI가 Flannel이었다. Flannel은 NetworkPolicy를 지원하지 않는다. 정책 오브젝트는 생성되지만 아무 효력이 없다. Calico나 Cilium으로 CNI를 교체하고 나서야 정책이 적용됐다.

NetworkPolicy 도입 전에 클러스터가 어떤 CNI를 쓰는지 반드시 확인해야 한다.

### 케이스 5: DMZ Egress 미제어

DMZ 웹 서버에서 Outbound 트래픽을 전혀 막지 않았다. 공격자가 업로드 취약점을 통해 웹쉘을 올리고 외부 서버로 데이터를 전송했다.

DMZ Egress 정책은 필요한 목적지만 화이트리스트로 열어야 한다. 소프트웨어 업데이트 서버, 외부 API 서버처럼 실제로 나가야 하는 대상만 허용하고 나머지는 Deny로 막는다.

외부 방화벽이나 NAT GW 수준에서 Egress를 제어하거나, 프록시 서버를 두고 모든 외부 통신을 프록시를 통해서만 나가게 하는 방식을 쓰기도 한다.
