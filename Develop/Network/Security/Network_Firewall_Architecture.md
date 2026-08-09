---
title: 네트워크 경계 방화벽 아키텍처
tags: [network, security, architecture]
updated: 2026-07-25
---

# 네트워크 경계 방화벽 아키텍처

이 문서는 L3/L4 수준의 네트워크 경계 방화벽을 다룬다. OS 커널 레벨 호스트 방화벽(iptables/nftables)은 [Firewall.md](Firewall.md)를, L7 애플리케이션 레이어 필터링은 AWS WAF 문서를 참고한다.

---

## 경계 방화벽이 필요한 이유

단일 서버에서 iptables로 인바운드 포트를 통제하는 것과, 여러 서버 묶음 앞에 경계 방화벽을 두는 것은 전혀 다른 문제다. 호스트 방화벽은 그 서버 하나를 보호하지만, 경계 방화벽은 내부 네트워크 전체를 외부와 분리한다.

서버가 수십 대를 넘어가면 각 서버마다 iptables 룰을 관리하는 게 현실적으로 어렵다. 룰 변경을 일일이 배포해야 하고, 서버 한 대가 잘못 설정되면 그 서버는 전체 내부망에서 lateral movement의 출발점이 된다. 경계 방화벽은 이 문제를 한 지점에서 해결한다.

클라우드 환경에서는 Security Group과 NACL이 이 역할을 상당 부분 담당하지만, 엔터프라이즈 수준의 요구사항(패킷 인스펙션, 위협 인텔리전스 기반 차단, 중앙 로깅)이 들어오면 AWS Network Firewall 같은 전용 서비스가 필요해진다.

---

## 방화벽 존(Zone) 설계

경계 방화벽 아키텍처의 핵심은 네트워크를 몇 개의 신뢰 구역(zone)으로 나누고, 존 간 트래픽을 방화벽이 중재하게 만드는 것이다.

**기본 3-존 구성:**

- **외부(External)**: 인터넷. 신뢰하지 않는다.
- **DMZ(Demilitarized Zone)**: 인터넷에서 직접 접근이 필요한 서버를 올리는 구간. 로드밸런서, 리버스 프록시, 배스천 호스트가 여기 위치한다.
- **내부(Internal)**: 실제 앱 서버, DB, 캐시, 내부 서비스가 있는 구간. 인터넷에서 직접 접근 불가.

존 간 트래픽 규칙은 이렇게 잡는다:

```
외부 → DMZ:      허용 (80, 443, 필요시 22)
외부 → 내부:     전면 차단
DMZ → 내부:      제한적 허용 (앱 서버 API 포트, DB 포트 등 명시적으로 허용한 것만)
내부 → DMZ:      허용 (응답 트래픽 포함)
내부 → 외부:     원칙적으로 차단, 예외(패키지 업데이트, 외부 API 호출)만 허용
```

내부 서버가 인터넷으로 직접 나가는 걸 막는 이유가 있다. 내부 서버가 침해됐을 때 공격자가 C2(Command and Control) 서버로 연결을 맺거나 데이터를 외부로 빼낼 때 아웃바운드 경로를 차단하면 피해를 제한할 수 있다. 외부 API 호출이 필요하면 NAT Gateway나 프록시를 경유하게 해서 로그를 남기고 목적지를 통제한다.

---

## DMZ 구성 실무

DMZ를 두는 이유는 공개 접점을 분리해서 침해 시 내부망 전체가 노출되는 걸 막기 위해서다. 로드밸런서가 DMZ에 있고, 그 뒤 앱 서버는 내부망에 있다면, 로드밸런서가 침해돼도 DB로 직접 접근하려면 내부망 방화벽을 한 번 더 뚫어야 한다.

실제 구성에서 흔히 보는 실수는 DMZ 서버가 내부망 서버에 너무 많은 포트로 접근할 수 있게 열어놓는 것이다. "일단 다 열고 나중에 좁히자"는 식으로 시작했다가 그 상태로 운영되는 경우가 많다. DMZ → 내부 방향은 최소 권한으로 열어야 한다. 로드밸런서가 앱 서버 8080에만 접근하면 되는데 전체 서브넷을 허용해두면 의미가 없다.

배스천 호스트(Bastion Host)는 별도의 접근 포인트다. 운영자가 내부 서버에 SSH로 들어가야 할 때 DMZ의 배스천을 경유한다. 인터넷에서 배스천의 22번 포트에 특정 IP(운영자 사무실 또는 VPN IP)만 허용하고, 배스천에서 내부 서버로의 SSH만 추가로 허용한다. 인터넷에서 내부 서버로 직접 SSH가 열려 있는 구성은 배스천의 의미가 없다.

---

## 인바운드·아웃바운드 트래픽 흐름

트래픽 흐름을 설계할 때 상태 추적(stateful) 여부가 중요하다. 방화벽이 stateful이면 허용된 인바운드 연결의 응답은 아웃바운드 룰 없이도 자동으로 통과된다. stateless라면 양방향을 명시적으로 열어야 한다.

AWS Security Group은 stateful, NACL은 stateless다. 이 차이 때문에 NACL에서는 인바운드 룰과 함께 아웃바운드 임시 포트(ephemeral port, 1024-65535)를 반드시 열어야 한다. 안 열면 요청은 들어오는데 응답이 나가지 못한다. NACL 설정 후 HTTPS가 동작하지 않는 문제의 대부분은 이 때문이다.

**인바운드 흐름 예시 (HTTP 요청):**

```
클라이언트
  → 인터넷 게이트웨이
  → NACL 인바운드 룰 (443 허용)
  → Security Group 인바운드 룰 (443 허용)
  → ALB (DMZ 서브넷)
  → Security Group 인바운드 룰 (8080 허용, 출발지: ALB SG)
  → 앱 서버 (내부 서브넷)
```

**아웃바운드 흐름 예시 (외부 API 호출):**

```
앱 서버 (내부 서브넷)
  → Security Group 아웃바운드 룰 (443 허용)
  → NACL 아웃바운드 룰 (443 허용)
  → NAT Gateway (퍼블릭 서브넷)
  → 인터넷 게이트웨이
  → 외부 API
```

내부 서버에서 NAT Gateway를 경유하지 않고 직접 나가는 구성은 의도치 않게 퍼블릭 IP가 붙어있는 인스턴스에서만 가능하다. 프라이빗 서브넷의 인스턴스는 NAT 없이 인터넷으로 나가는 경로가 없다. 이게 의도한 설계라면 라우팅 테이블을 확인해서 프라이빗 서브넷의 기본 경로가 NAT Gateway를 향하는지 검증한다.

---

## AWS 클라우드 환경의 방화벽 층위

AWS에서는 방화벽 역할을 하는 것이 Security Group, NACL, Network Firewall 세 가지다. 세 가지가 완전히 다른 층위에서 동작하기 때문에 역할을 명확히 구분해야 한다.

### Security Group

EC2 인스턴스 레벨에서 작동하는 가상 방화벽이다. 인스턴스 네트워크 인터페이스(ENI)에 붙는다. Stateful이라 허용된 인바운드 연결의 응답은 아웃바운드 룰 없이 나간다.

Security Group끼리 참조하는 방식이 실무에서 가장 자주 쓰인다. IP 대역 대신 "이 Security Group에서 온 트래픽"으로 허용하면, 서버 IP가 바뀌거나 오토스케일링으로 인스턴스가 추가돼도 룰을 수정할 필요가 없다.

```bash
# ALB Security Group: 인터넷 443 허용
# App Security Group: ALB Security Group에서 8080 허용
# DB Security Group: App Security Group에서 5432 허용
```

이 방식의 단점은 Security Group이 너무 많아지면 관계가 복잡해진다는 것이다. "어떤 SG가 이 SG에 접근 가능한지" 추적이 어렵다. AWS Config나 별도 도구로 SG 관계를 시각화하지 않으면 유지보수가 힘들어진다.

### NACL (Network Access Control List)

서브넷 레벨에서 작동한다. 서브넷으로 들어오고 나가는 트래픽을 필터링한다. Stateless라 인바운드와 아웃바운드를 각각 명시해야 한다.

NACL은 룰 번호 순서로 평가되고 첫 매칭에서 끝난다. 100번 룰에서 DENY, 200번 룰에서 ALLOW면 100번에서 끝나서 200번은 평가 안 한다. iptables와 같은 방식이다.

NACL이 Security Group보다 먼저 평가된다. 인터넷에서 들어오는 패킷이 먼저 NACL을 통과한 뒤 Security Group에서 다시 필터링된다. 이 순서 때문에 Security Group에서 허용해도 NACL이 막으면 안 통한다.

NACL을 주로 쓰는 상황은 특정 IP 대역을 서브넷 레벨에서 완전히 차단할 때다. Security Group은 인스턴스마다 붙여야 하지만 NACL은 서브넷 하나에 설정하면 그 서브넷의 모든 인스턴스에 적용된다. 대규모 IP 차단이나 서브넷 격리에 NACL이 적합하다.

### AWS Network Firewall

VPC 레벨에서 작동하는 L3/L4 상태 기반 방화벽이다. Security Group과 NACL로 해결 못 하는 요구사항을 처리한다:

- 도메인 이름 기반 필터링 (특정 FQDN만 허용)
- Suricata 기반의 IPS/IDS 룰 (패턴 매칭, 시그니처 기반 탐지)
- 중앙화된 트래픽 로그 (패킷 헤더, 플로우 로그)
- 위협 인텔리전스 피드 통합

Network Firewall은 트래픽이 물리적으로 통과하는 구간에 두어야 한다. VPC 라우팅 테이블을 수정해서 인터넷 게이트웨이와 서브넷 사이 경로를 Network Firewall Endpoint를 거치게 만든다.

---

## AWS Network Firewall 실무 구성

### 기본 아키텍처

Network Firewall을 VPC 엣지(edge)에 두는 방식이 일반적이다. 방화벽 서브넷을 별도로 만들고, 거기에 Firewall Endpoint를 배치한다.

```
인터넷 게이트웨이
  → 라우팅: 0.0.0.0/0 → Firewall Endpoint
  → Network Firewall (방화벽 서브넷)
  → 라우팅: 0.0.0.0/0 → 인터넷 게이트웨이
  → 퍼블릭 서브넷 (ALB 등)
  → 프라이빗 서브넷 (앱 서버, DB)
```

라우팅 테이블을 두 곳 수정해야 한다. 하나는 인터넷 게이트웨이 라우팅 테이블(IGW route table)로, 퍼블릭 서브넷으로 가는 트래픽을 Firewall Endpoint로 보낸다. 다른 하나는 퍼블릭 서브넷의 라우팅 테이블로, 아웃바운드 기본 경로(0.0.0.0/0)를 Firewall Endpoint로 보낸다. 이 두 곳이 맞지 않으면 트래픽이 비대칭 경로를 타게 되고 방화벽에서 TCP 세션 상태가 깨진다.

비대칭 라우팅은 stateful 방화벽에서 치명적이다. SYN은 방화벽을 통과했는데 SYN-ACK가 다른 경로로 돌아오면 방화벽 상태 테이블에 SYN-ACK에 해당하는 세션이 없어서 DROP된다. 연결이 안 되는 증상이 나타나면 먼저 라우팅 테이블을 봐야 한다.

### 방화벽 정책(Firewall Policy) 구성

Network Firewall의 정책은 상태 비저장(Stateless) 룰 그룹과 상태 저장(Stateful) 룰 그룹으로 나뉜다.

**Stateless 룰**: 패킷 하나하나를 독립적으로 본다. PASS/DROP/FORWARD(stateful으로 넘김)를 결정한다. 우선순위가 낮은 숫자가 먼저 평가된다. 성능이 중요하고 컨텍스트 없이 판단할 수 있는 룰(알려진 악성 IP 차단, 특정 프로토콜 전면 차단)을 여기 넣는다.

```json
{
  "Priority": 1,
  "RuleDefinition": {
    "Actions": ["aws:drop"],
    "MatchAttributes": {
      "Sources": [
        {"AddressDefinition": "203.0.113.0/24"}
      ]
    }
  }
}
```

**Stateful 룰**: TCP 연결 상태를 추적하면서 패킷을 본다. Suricata 룰 언어를 쓰거나 도메인 기반 룰, 5-튜플 룰을 설정할 수 있다.

도메인 기반 아웃바운드 필터링은 프라이빗 서브넷에서 외부로 나가는 HTTPS를 특정 도메인만 허용할 때 쓴다:

```
# 허용: api.github.com, registry-1.docker.io 등
# 나머지 HTTPS 아웃바운드 차단
```

Suricata 룰로 L7 시그니처 기반 탐지를 추가할 수 있다:

```
alert http $HOME_NET any -> $EXTERNAL_NET any (
  msg:"Outbound HTTP to non-standard port";
  flow:established,to_server;
  http.method; content:"GET";
  sid:100001;
)
```

### 로깅 설정

Network Firewall의 로그는 S3, CloudWatch Logs, Kinesis Data Firehose 중 하나로 보낼 수 있다. 두 가지 로그 타입이 있다:

- **Flow Log**: 5-튜플(출발지IP, 목적지IP, 출발지포트, 목적지포트, 프로토콜)과 허용/차단 여부만 기록한다. 양이 많다.
- **Alert Log**: Stateful 룰에서 action이 alert인 룰에 매칭된 패킷만 기록한다. 보안 이벤트 탐지용.

운영에서 Flow Log를 S3에 쌓아두고 Athena로 쿼리하는 방식이 비용 대비 실용적이다. CloudWatch에 넣으면 실시간 알림은 쉬운데 저장 비용이 빠르게 올라간다.

---

## 클라우드 환경 층위 구분 정리

클라우드에서 방화벽 역할을 하는 것들을 층위별로 정리하면:

| 층위 | 서비스 | 적용 범위 | 상태 추적 | 주 사용 목적 |
|------|--------|-----------|-----------|-------------|
| L7 (애플리케이션) | AWS WAF | CloudFront, ALB, API GW | Stateful | SQL인젝션, XSS, 봇 차단 |
| L4 (경계 네트워크) | AWS Network Firewall | VPC 전체 | Stateful | IPS, 도메인 필터링, 중앙 로깅 |
| L4 (서브넷) | NACL | 서브넷 | Stateless | 서브넷 레벨 IP 차단 |
| L4 (인스턴스) | Security Group | ENI | Stateful | 인스턴스 레벨 포트 통제 |
| L4 (호스트) | iptables/nftables | OS 커널 | Stateful | 호스트 자체 보호 |

이 층위들은 중복처럼 보이지만 실제로 각각 독립적으로 동작한다. Security Group에서 허용해도 NACL이 막으면 안 통한다. 두 곳 다 허용해도 Network Firewall 정책이 차단하면 안 된다. 트래픽 흐름 문제를 디버깅할 때 어느 층위에서 막히는지 순서대로 확인해야 한다.

**디버깅 순서:**
1. Network Firewall 플로우 로그 확인 (허용됐는지)
2. NACL 인바운드/아웃바운드 룰 확인 (임시 포트 포함)
3. Security Group 인바운드/아웃바운드 룰 확인
4. 인스턴스 내 iptables 확인
5. 애플리케이션 레벨 확인

---

## 운영 중 자주 마주치는 문제

**Security Group 드리프트**: 처음에는 최소 권한으로 설계했다가, 장애 대응하면서 임시로 "0.0.0.0/0 허용"을 추가하고 그게 정리 안 된 채 남는 경우가 많다. AWS Config의 `restricted-ssh` 같은 관리형 룰로 정기적으로 감사하거나, 인프라를 코드로 관리해서 변경 내역을 추적해야 한다.

**NACL 임시 포트 미설정**: 프라이빗 서브넷에 NACL을 적용했는데 아웃바운드 임시 포트(1024-65535)를 안 열면, 외부에서 들어오는 요청의 응답이 나가지 못한다. Security Group은 stateful이라 자동으로 처리되지만 NACL은 수동으로 열어야 한다. HTTPS가 단방향으로만 동작하는 이상한 증상이 나오면 여기를 먼저 본다.

**Network Firewall 비대칭 라우팅**: 라우팅 테이블을 잘못 구성해서 인바운드와 아웃바운드가 다른 경로를 타면 stateful 세션이 성립되지 않는다. VPC 라우팅을 수정할 때 양방향 경로가 같은 Firewall Endpoint를 거치는지 반드시 확인한다. AZ별로 Endpoint가 따로 있기 때문에 AZ를 섞으면 비대칭이 생긴다.

**서브넷 간 트래픽 누락**: 같은 VPC 안에서 서브넷 간 트래픽은 기본적으로 Security Group만 통과하면 된다. NACL도 서브넷을 나갈 때 적용된다는 걸 잊고 같은 VPC 내부 통신도 안 되는 경우가 있다. NACL을 기본값(전체 허용)에서 수정했다면 VPC 내부 대역도 허용 룰에 포함했는지 확인한다.
