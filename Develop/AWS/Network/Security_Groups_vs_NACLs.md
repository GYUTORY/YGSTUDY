---
title: Security Groups vs NACLs
tags: [aws, security-groups, nacl, firewall, vpc, network, security]
updated: 2026-01-23
---

# Security Groups vs NACLs

## 개요

Security Groups와 NACLs는 VPC의 방화벽이다. 트래픽을 제어한다. 둘 다 인바운드와 아웃바운드 규칙을 설정한다. 하지만 동작 방식이 완전히 다르다. 언제 무엇을 사용할지 알아야 한다.

### 핵심 차이

**Security Groups (보안 그룹):**
- 인스턴스 레벨 방화벽
- Stateful (상태 유지)
- 허용 규칙만 (Deny 없음)
- 모든 규칙 평가
- ENI에 연결

**NACLs (Network ACLs):**
- 서브넷 레벨 방화벽
- Stateless (상태 없음)
- 허용과 거부 규칙
- 순서대로 평가
- 서브넷에 연결

## Security Groups

### 동작 방식

**Stateful:**
가장 중요한 특징이다. 아웃바운드 요청의 응답은 자동으로 허용된다.

**예시:**
EC2에서 외부 API를 호출한다.

**Security Group 규칙:**
```
Outbound: 0.0.0.0/0, All traffic, Allow
```

**동작:**
1. EC2가 API 서버 (1.2.3.4:443)에 요청
2. 아웃바운드 규칙 확인: 허용
3. API 서버가 응답 (1.2.3.4:443 → EC2)
4. **인바운드 규칙을 확인하지 않는다**
5. 응답이 자동으로 허용된다

연결 상태를 추적한다. 요청을 보냈으면 응답을 자동으로 받는다.

**반대 방향도 마찬가지:**
```
Inbound: 0.0.0.0/0, 80, Allow
```

클라이언트가 EC2:80에 접속한다. EC2가 응답을 보낸다. 아웃바운드 규칙을 확인하지 않는다. 자동으로 허용된다.

**따라서:**
- 웹 서버: 인바운드 80, 443만 열면 된다
- 아웃바운드는 신경 쓸 필요 없다 (응답 자동 허용)

### 규칙 작성

**인바운드 규칙:**
```
Type        Protocol  Port Range  Source
HTTP        TCP       80          0.0.0.0/0
HTTPS       TCP       443         0.0.0.0/0
SSH         TCP       22          10.0.0.0/8
Custom TCP  TCP       3306        sg-12345678
```

**설명:**
- HTTP/HTTPS: 모든 곳에서 접근 허용
- SSH: 내부 네트워크 (10.0.0.0/8)에서만
- MySQL: 다른 Security Group (sg-12345678)에서만

**Source 타입:**
- **CIDR**: 10.0.0.0/16, 0.0.0.0/0
- **Security Group**: sg-12345678
- **Prefix List**: pl-12345678 (AWS 서비스 IP 범위)

**아웃바운드 규칙:**
```
Type        Protocol  Port Range  Destination
All traffic All       All         0.0.0.0/0
```

보통 모든 트래픽을 허용한다. Stateful이라서 응답만 나간다.

**제한하려면:**
```
Type  Protocol  Port Range  Destination
HTTP  TCP       80          0.0.0.0/0
HTTPS TCP       443         0.0.0.0/0
```

EC2가 HTTP/HTTPS만 요청할 수 있다. 다른 프로토콜은 차단된다.

### Security Group 참조

다른 Security Group을 Source로 사용한다.

**예시: 3 Tier 아키텍처**

**Web Tier (sg-web):**
```
Inbound:
- HTTP (80) from 0.0.0.0/0
- HTTPS (443) from 0.0.0.0/0

Outbound:
- All traffic
```

**App Tier (sg-app):**
```
Inbound:
- Custom TCP (8080) from sg-web

Outbound:
- All traffic
```

**DB Tier (sg-db):**
```
Inbound:
- MySQL (3306) from sg-app

Outbound:
- All traffic
```

**동작:**
- 인터넷 → Web: 허용
- Web → App: 허용 (sg-web이 Source)
- App → DB: 허용 (sg-app이 Source)
- 인터넷 → App: 차단 (규칙 없음)
- 인터넷 → DB: 차단 (규칙 없음)

Security Group끼리 연결한다. IP를 하드코딩하지 않는다.

**장점:**
- 인스턴스 IP가 바뀌어도 문제없다
- Auto Scaling으로 인스턴스가 추가되어도 자동 적용
- 관리가 쉽다

### 적용

**ENI에 연결:**
Security Group은 ENI (Elastic Network Interface)에 연결된다. EC2, RDS, Lambda 등 모두 ENI를 가진다.

**여러 개 연결:**
하나의 ENI에 최대 5개 Security Group을 연결할 수 있다.

**예시:**
- sg-web: HTTP/HTTPS 허용
- sg-ssh: SSH 허용 (특정 IP만)
- sg-monitoring: CloudWatch Agent 허용

EC2에 3개를 모두 연결한다. 모든 규칙이 적용된다.

**모든 규칙 평가:**
어느 하나라도 허용하면 통과한다. OR 조건이다.

### 기본 동작

**기본값:**
- 인바운드: 모두 차단
- 아웃바운드: 모두 허용

새 Security Group을 만들면 들어오는 트래픽은 모두 차단된다. 나가는 트래픽은 모두 허용된다.

**허용만 가능:**
거부 규칙을 만들 수 없다. 허용 규칙만 추가한다. 규칙에 없으면 자동으로 차단된다.

## NACLs (Network ACLs)

### 동작 방식

**Stateless:**
연결 상태를 추적하지 않는다. 요청과 응답을 별개로 처리한다.

**예시:**
EC2에서 외부 API를 호출한다.

**NACL 규칙:**
```
Outbound:
Rule #100: Allow, TCP, 443, 0.0.0.0/0

Inbound:
Rule #100: Allow, TCP, 1024-65535, 0.0.0.0/0
```

**동작:**
1. EC2가 API 서버 (1.2.3.4:443)에 요청
2. Outbound 규칙 확인: Rule #100 매칭, 허용
3. API 서버가 응답 (1.2.3.4:443 → EC2:임시포트)
4. **Inbound 규칙을 다시 확인한다**
5. 임시 포트 (1024-65535) 허용 필요
6. Rule #100 매칭, 허용

요청과 응답을 별개로 처리한다. 양방향 규칙이 모두 필요하다.

**임시 포트 (Ephemeral Ports):**
클라이언트가 사용하는 임시 포트다. OS마다 범위가 다르다.

- **Linux**: 32768-60999
- **Windows**: 49152-65535
- **Elastic Load Balancing**: 1024-65535

안전하게 1024-65535를 허용한다.

### 규칙 작성

**인바운드 규칙:**
```
Rule #  Type      Protocol  Port Range  Source       Allow/Deny
100     HTTP      TCP       80          0.0.0.0/0    Allow
110     HTTPS     TCP       443         0.0.0.0/0    Allow
120     SSH       TCP       22          10.0.0.0/8   Allow
130     Custom    TCP       1024-65535  0.0.0.0/0    Allow
200     All       All       All         192.0.2.0/24 Deny
*       All       All       All         0.0.0.0/0    Deny
```

**설명:**
- Rule #100-120: 특정 포트 허용
- Rule #130: 임시 포트 허용 (응답용)
- Rule #200: 특정 IP 차단
- Rule #*: 나머지 모두 차단 (기본 규칙)

**아웃바운드 규칙:**
```
Rule #  Type      Protocol  Port Range  Destination  Allow/Deny
100     HTTP      TCP       80          0.0.0.0/0    Allow
110     HTTPS     TCP       443         0.0.0.0/0    Allow
120     Custom    TCP       1024-65535  0.0.0.0/0    Allow
*       All       All       All         0.0.0.0/0    Deny
```

**설명:**
- Rule #100-110: 외부 요청 허용
- Rule #120: 임시 포트 허용 (응답용)

### 순서대로 평가

**규칙 번호:**
낮은 번호부터 평가한다. 매칭되면 즉시 적용한다. 나머지 규칙은 무시한다.

**예시:**
```
Rule #100: Allow, TCP, 22, 10.0.0.0/16
Rule #110: Deny, TCP, 22, 10.0.1.0/24
```

10.0.1.5에서 SSH 접속 시도.

**평가:**
1. Rule #100 확인: 10.0.0.0/16 매칭, 허용
2. Rule #110은 확인하지 않는다
3. 접속 허용

**잘못된 순서다.** 10.0.1.0/24를 차단하려면:

```
Rule #100: Deny, TCP, 22, 10.0.1.0/24
Rule #110: Allow, TCP, 22, 10.0.0.0/16
```

Deny를 먼저 평가한다.

**규칙 번호 간격:**
10, 20, 30... 또는 100, 110, 120... 으로 설정한다. 나중에 중간에 규칙을 추가할 수 있다.

### 기본 NACL

VPC를 만들면 기본 NACL이 생성된다.

**기본 규칙:**
```
Inbound:
Rule #*: Allow, All, All, 0.0.0.0/0

Outbound:
Rule #*: Allow, All, All, 0.0.0.0/0
```

모든 트래픽을 허용한다. 제한이 없다.

**새 NACL:**
커스텀 NACL을 만들면 기본 규칙이 다르다.

```
Inbound:
Rule #*: Deny, All, All, 0.0.0.0/0

Outbound:
Rule #*: Deny, All, All, 0.0.0.0/0
```

모든 트래픽을 차단한다. 명시적으로 규칙을 추가해야 한다.

### 서브넷 연결

NACL은 서브넷에 연결된다.

**하나의 서브넷 = 하나의 NACL:**
서브넷은 하나의 NACL만 가진다. NACL을 변경하면 이전 NACL과의 연결이 끊어진다.

**하나의 NACL = 여러 서브넷:**
NACL은 여러 서브넷에 연결할 수 있다.

**기본 연결:**
서브넷을 만들면 기본 NACL에 자동으로 연결된다.

## 비교표

| 특징 | Security Groups | NACLs |
|------|----------------|-------|
| **레벨** | 인스턴스 (ENI) | 서브넷 |
| **Stateful/Stateless** | Stateful | Stateless |
| **규칙** | 허용만 | 허용과 거부 |
| **평가** | 모든 규칙 | 순서대로 |
| **기본 동작** | 인바운드 차단, 아웃바운드 허용 | 커스텀: 모두 차단 |
| **규칙 수** | ENI당 60개 | NACL당 20개 |
| **적용** | 즉시 | 즉시 |
| **응답 트래픽** | 자동 허용 | 명시적 규칙 필요 |

## 실무 사용

### Security Groups 우선

대부분의 경우 Security Groups만 사용한다.

**이유:**
- 관리가 쉽다
- Stateful이라 응답 규칙 불필요
- 인스턴스별로 세밀하게 제어
- Security Group 참조로 연결

**기본 구성:**
- NACL: 기본 설정 (모두 허용)
- Security Groups: 세밀하게 설정

### NACL을 사용하는 경우

**1. 특정 IP 차단:**
Security Groups는 거부 규칙이 없다. NACL로 차단한다.

**예시:**
공격자 IP를 차단한다.

```
Rule #50: Deny, All, All, 203.0.113.5/32
```

서브넷 레벨에서 차단한다. 어떤 인스턴스에도 도달하지 못한다.

**2. 서브넷 단위 방어:**
퍼블릭 서브넷에 추가 방어층을 둔다.

```
Public Subnet NACL:
- Allow HTTP/HTTPS from anywhere
- Allow SSH from office IP only
- Allow ephemeral ports
- Deny all others
```

**3. 컴플라이언스:**
규정에서 네트워크 레벨 방화벽을 요구한다. NACL로 충족한다.

**4. 디버깅:**
서브넷 전체의 트래픽을 일시적으로 차단한다.

```
Rule #10: Deny, All, All, 0.0.0.0/0
```

모든 트래픽이 차단된다. 문제를 격리한다.

### 계층적 방어

두 가지를 함께 사용한다.

**구조:**
```
Internet → NACL (서브넷) → Security Group (인스턴스) → EC2
```

**NACL:**
- 넓은 범위 제어
- 악의적인 IP 차단
- 프로토콜 레벨 필터링

**Security Groups:**
- 세밀한 제어
- 애플리케이션 레벨 필터링
- 인스턴스 간 통신 제어

**예시:**

**NACL (Public Subnet):**
```
Inbound:
Rule #50: Deny, All, All, 198.51.100.0/24  # 공격자 IP 차단
Rule #100: Allow, TCP, 80, 0.0.0.0/0
Rule #110: Allow, TCP, 443, 0.0.0.0/0
Rule #120: Allow, TCP, 22, 10.0.0.0/8
Rule #130: Allow, TCP, 1024-65535, 0.0.0.0/0
Rule #*: Deny, All, All, 0.0.0.0/0
```

**Security Group (Web Server):**
```
Inbound:
- HTTP (80) from 0.0.0.0/0
- HTTPS (443) from 0.0.0.0/0
- SSH (22) from sg-bastion

Outbound:
- All traffic
```

이중 방어다. NACL이 첫 번째 장벽, Security Group이 두 번째 장벽이다.

## 트러블슈팅

### 연결이 안 된다

**1. Security Groups 확인:**
가장 먼저 확인한다.

**인바운드:**
- 필요한 포트가 열려있는지
- Source가 올바른지

**아웃바운드:**
- 제한했다면 필요한 포트가 열려있는지

**2. NACL 확인:**
Security Groups이 맞는데도 안 되면 NACL을 확인한다.

**인바운드:**
- 필요한 포트 허용
- 임시 포트 (1024-65535) 허용

**아웃바운드:**
- 필요한 포트 허용
- 임시 포트 허용

**3. 규칙 순서:**
NACL의 규칙 순서가 올바른지 확인한다. Deny가 Allow보다 앞에 있으면 차단된다.

**4. VPC Flow Logs:**
트래픽이 어디서 차단되는지 확인한다.

```bash
aws ec2 create-flow-logs \
  --resource-type NetworkInterface \
  --resource-ids eni-12345678 \
  --traffic-type REJECT \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs
```

거부된 트래픽만 로그로 남긴다. Security Group인지 NACL인지 확인한다.

### 임시 포트 문제

클라이언트가 임시 포트로 응답을 받는다. NACL에서 임시 포트를 열어야 한다.

**문제:**
```
NACL Inbound:
Rule #100: Allow, TCP, 80, 0.0.0.0/0
Rule #*: Deny, All, All, 0.0.0.0/0
```

HTTP 요청은 들어온다. 하지만 응답이 나가지 못한다. 임시 포트가 차단된다.

**해결:**
```
NACL Inbound:
Rule #100: Allow, TCP, 80, 0.0.0.0/0
Rule #110: Allow, TCP, 1024-65535, 0.0.0.0/0
Rule #*: Deny, All, All, 0.0.0.0/0
```

임시 포트를 허용한다. 응답이 나간다.

## 참고

- Security Groups: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html
- NACLs: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- 비교: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Security.html
- VPC Flow Logs: https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html

