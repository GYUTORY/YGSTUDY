---
title: AWS Transit Gateway
tags: [aws, transit-gateway, vpc, networking, routing, hybrid-cloud]
updated: 2026-01-23
---

# AWS Transit Gateway

## 개요

Transit Gateway는 여러 VPC와 온프레미스 네트워크를 연결하는 중앙 허브다. VPC Peering의 복잡성을 해결한다. 수십 개의 VPC를 하나의 Transit Gateway에 연결한다. 라우팅 테이블을 중앙에서 관리한다.

### 왜 필요한가

VPC가 많아지면 관리가 복잡해진다.

**문제 상황: VPC Peering의 한계**

**3개 VPC 연결:**
- VPC A (개발)
- VPC B (스테이징)
- VPC C (프로덕션)

**VPC Peering:**
- A ↔ B
- A ↔ C
- B ↔ C

3개 Peering이 필요하다. 관리 가능하다.

**10개 VPC 연결:**
필요한 Peering 수: 10 × 9 ÷ 2 = 45개

**100개 VPC 연결:**
필요한 Peering 수: 100 × 99 ÷ 2 = 4,950개

불가능하다. VPC Peering은 확장성이 없다.

**추가 문제:**

**1. 전이적 라우팅 불가:**
- VPC A ↔ VPC B Peering
- VPC B ↔ VPC C Peering
- VPC A는 VPC C에 접근 불가능

A → B → C 경로가 자동으로 만들어지지 않는다. A ↔ C Peering을 별도로 생성해야 한다.

**2. 온프레미스 연결:**
온프레미스 데이터센터와 10개 VPC를 연결한다.

**VPN 방식:**
- 각 VPC에 VPN Gateway 생성
- 온프레미스에서 10개 VPN 연결
- 각 VPN 설정 및 관리
- BGP 라우팅 10개 설정

복잡하고 에러 발생 가능성이 높다.

**3. 라우팅 테이블 관리:**
각 VPC마다 라우팅 테이블을 관리한다. 새 VPC를 추가하면 모든 VPC의 라우팅 테이블을 수정해야 한다.

### Transit Gateway의 해결

**중앙 허브:**
- Transit Gateway 1개 생성
- 모든 VPC를 Transit Gateway에 연결
- 온프레미스도 Transit Gateway에 연결

**연결 수:**
- VPC 100개 + 온프레미스 1개 = 101개 연결
- VPC Peering 4,950개 → Transit Gateway 연결 101개

관리가 훨씬 간단하다.

**전이적 라우팅:**
- VPC A → Transit Gateway → VPC C
- 자동으로 라우팅된다
- 추가 설정 불필요

**중앙 라우팅 관리:**
Transit Gateway의 라우팅 테이블 하나만 관리한다. 새 VPC를 추가해도 Transit Gateway에 연결만 하면 된다.

## 핵심 개념

### Transit Gateway

중앙 라우터 역할을 한다. 리전당 하나 또는 여러 개를 만들 수 있다.

**특징:**
- 최대 5,000개 Attachment 지원
- 최대 50Gbps per Attachment
- 여러 가용 영역에 자동 배포
- 고가용성 보장

### Attachment (연결)

Transit Gateway에 리소스를 연결하는 방법이다.

**종류:**
- **VPC Attachment**: VPC 연결
- **VPN Attachment**: Site-to-Site VPN 연결
- **Direct Connect Gateway Attachment**: Direct Connect 연결
- **Peering Attachment**: 다른 Transit Gateway 연결
- **Connect Attachment**: SD-WAN 연결

### Route Table (라우팅 테이블)

트래픽을 어디로 보낼지 결정한다.

**동작:**
1. 트래픽이 Transit Gateway로 들어온다
2. 목적지 IP 확인
3. 라우팅 테이블에서 매칭되는 규칙 찾기
4. 해당 Attachment로 트래픽 전송

**여러 라우팅 테이블:**
Transit Gateway는 여러 라우팅 테이블을 가질 수 있다. Attachment마다 다른 라우팅 테이블을 사용한다.

**사용 사례:**
- 개발 VPC는 개발 환경만 접근
- 프로덕션 VPC는 프로덕션 환경만 접근
- 관리 VPC는 모든 환경 접근

### Association (연결)

Attachment를 라우팅 테이블에 연결한다.

**예시:**
- VPC A Attachment를 Route Table 1에 연결
- VPC A에서 나가는 트래픽은 Route Table 1 사용

### Propagation (전파)

Attachment의 CIDR을 라우팅 테이블에 자동으로 추가한다.

**예시:**
- VPC B (10.1.0.0/16)를 Route Table 1에 Propagate
- Route Table 1에 자동으로 추가: 10.1.0.0/16 → VPC B Attachment

수동으로 라우팅 규칙을 추가하지 않아도 된다.

## 기본 설정

### Transit Gateway 생성

**콘솔:**
1. VPC 콘솔 → Transit Gateways
2. "Create Transit Gateway" 클릭
3. 이름 입력
4. ASN 입력 (기본: 64512)
5. DNS 지원 활성화
6. VPN ECMP 지원 활성화
7. 기본 라우팅 테이블 연결 활성화
8. 생성

**CLI:**
```bash
aws ec2 create-transit-gateway \
  --description "Main Transit Gateway" \
  --options \
    AmazonSideAsn=64512,\
    AutoAcceptSharedAttachments=disable,\
    DefaultRouteTableAssociation=enable,\
    DefaultRouteTablePropagation=enable,\
    DnsSupport=enable,\
    VpnEcmpSupport=enable
```

**주요 옵션:**

**AmazonSideAsn:**
BGP ASN 번호. 온프레미스와 BGP를 사용하면 필요하다. 기본값 64512.

**DefaultRouteTableAssociation:**
새 Attachment를 자동으로 기본 라우팅 테이블에 연결. 간단한 구성에서는 enable.

**DnsSupport:**
DNS 쿼리가 Transit Gateway를 통과할 수 있게 한다. 대부분 enable.

### VPC 연결

**콘솔:**
1. Transit Gateway Attachments 메뉴
2. "Create Transit Gateway Attachment" 클릭
3. Transit Gateway 선택
4. Attachment type: VPC
5. VPC 선택
6. 서브넷 선택 (각 AZ에서 하나씩)
7. 생성

**CLI:**
```bash
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id tgw-12345678 \
  --vpc-id vpc-abcd1234 \
  --subnet-ids subnet-11111111 subnet-22222222 subnet-33333333
```

**서브넷 선택:**
각 가용 영역에서 서브넷을 하나씩 선택한다. 고가용성을 위해 필요하다.

보통 프라이빗 서브넷을 선택한다. Transit Gateway는 VPC 내부 리소스에만 접근한다.

### VPC 라우팅 테이블 수정

VPC에서 Transit Gateway로 트래픽을 보내려면 라우팅 규칙을 추가한다.

**예시:**
VPC A (10.0.0.0/16)에서 VPC B (10.1.0.0/16)로 트래픽을 보낸다.

**VPC A의 라우팅 테이블:**
```
Destination         Target
10.0.0.0/16        local
10.1.0.0/16        tgw-12345678
```

**CLI:**
```bash
aws ec2 create-route \
  --route-table-id rtb-abcd1234 \
  --destination-cidr-block 10.1.0.0/16 \
  --transit-gateway-id tgw-12345678
```

**모든 트래픽 전송:**
VPC 외부로 가는 모든 트래픽을 Transit Gateway로 보낸다.

```bash
aws ec2 create-route \
  --route-table-id rtb-abcd1234 \
  --destination-cidr-block 0.0.0.0/0 \
  --transit-gateway-id tgw-12345678
```

인터넷 게이트웨이가 없는 프라이빗 서브넷에서 유용하다. Transit Gateway를 통해 NAT Gateway가 있는 VPC로 트래픽을 보낸다.

## 라우팅 시나리오

### 단순 연결

모든 VPC가 서로 통신한다.

**구성:**
- VPC A (10.0.0.0/16)
- VPC B (10.1.0.0/16)
- VPC C (10.2.0.0/16)
- Transit Gateway 1개
- 라우팅 테이블 1개

**Transit Gateway 라우팅 테이블:**
```
Destination         Attachment
10.0.0.0/16        VPC A
10.1.0.0/16        VPC B
10.2.0.0/16        VPC C
```

**자동 전파:**
각 VPC Attachment를 라우팅 테이블에 Propagate한다. 자동으로 규칙이 추가된다.

**결과:**
- VPC A → VPC B: 가능
- VPC A → VPC C: 가능
- VPC B → VPC C: 가능

모든 VPC가 서로 통신한다.

### 격리된 환경

개발과 프로덕션을 분리한다.

**요구사항:**
- 개발 VPC끼리만 통신
- 프로덕션 VPC끼리만 통신
- 개발과 프로덕션은 통신 불가
- 관리 VPC는 모든 VPC와 통신

**구성:**
- VPC Dev1 (10.0.0.0/16)
- VPC Dev2 (10.1.0.0/16)
- VPC Prod1 (10.10.0.0/16)
- VPC Prod2 (10.11.0.0/16)
- VPC Mgmt (10.100.0.0/16)
- Transit Gateway 1개
- 라우팅 테이블 3개

**Route Table: Dev**
```
Destination         Attachment
10.0.0.0/16        VPC Dev1
10.1.0.0/16        VPC Dev2
10.100.0.0/16      VPC Mgmt
```

**Route Table: Prod**
```
Destination         Attachment
10.10.0.0/16       VPC Prod1
10.11.0.0/16       VPC Prod2
10.100.0.0/16      VPC Mgmt
```

**Route Table: Mgmt**
```
Destination         Attachment
10.0.0.0/16        VPC Dev1
10.1.0.0/16        VPC Dev2
10.10.0.0/16       VPC Prod1
10.11.0.0/16       VPC Prod2
```

**Association:**
- VPC Dev1, Dev2 → Route Table Dev
- VPC Prod1, Prod2 → Route Table Prod
- VPC Mgmt → Route Table Mgmt

**결과:**
- Dev1 → Dev2: 가능 (같은 라우팅 테이블)
- Prod1 → Prod2: 가능 (같은 라우팅 테이블)
- Dev1 → Prod1: 불가능 (Route Table Dev에 Prod1 규칙 없음)
- Mgmt → Dev1, Prod1: 모두 가능 (Route Table Mgmt에 모든 규칙 있음)

### 온프레미스 연결

데이터센터와 VPC를 연결한다.

**구성:**
- 온프레미스 (192.168.0.0/16)
- VPC A (10.0.0.0/16)
- VPC B (10.1.0.0/16)
- Transit Gateway
- Site-to-Site VPN

**VPN 연결:**
```bash
# Customer Gateway 생성 (온프레미스 라우터 IP)
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.1 \
  --bgp-asn 65000

# VPN Connection 생성
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id cgw-12345678 \
  --transit-gateway-id tgw-12345678
```

**Transit Gateway 라우팅 테이블:**
```
Destination         Attachment
10.0.0.0/16        VPC A
10.1.0.0/16        VPC B
192.168.0.0/16     VPN
```

**VPC 라우팅 테이블:**
각 VPC의 라우팅 테이블에 온프레미스로 가는 경로를 추가한다.

```
Destination         Target
10.0.0.0/16        local
192.168.0.0/16     tgw-12345678
```

**결과:**
- VPC A → 온프레미스: 가능
- VPC B → 온프레미스: 가능
- 온프레미스 → VPC A, B: 가능

### 인터넷 접근 (Egress VPC)

프라이빗 VPC에서 인터넷에 접근한다.

**배경:**
프라이빗 VPC는 NAT Gateway가 없다. 인터넷에 접근할 수 없다. 모든 VPC에 NAT Gateway를 만들면 비용이 증가한다.

**해결:**
하나의 VPC에만 NAT Gateway를 만든다. 다른 VPC는 Transit Gateway를 통해 NAT Gateway VPC로 트래픽을 보낸다.

**구성:**
- VPC Egress (10.100.0.0/16): NAT Gateway 있음
- VPC A (10.0.0.0/16): NAT Gateway 없음
- VPC B (10.1.0.0/16): NAT Gateway 없음
- Transit Gateway

**Transit Gateway 라우팅 테이블:**
```
Destination         Attachment
10.0.0.0/16        VPC A
10.1.0.0/16        VPC B
10.100.0.0/16      VPC Egress
0.0.0.0/0          VPC Egress
```

**VPC A, B 라우팅 테이블:**
```
Destination         Target
10.0.0.0/16        local
0.0.0.0/0          tgw-12345678
```

**VPC Egress 라우팅 테이블 (프라이빗 서브넷):**
```
Destination         Target
10.100.0.0/16      local
10.0.0.0/16        tgw-12345678
10.1.0.0/16        tgw-12345678
0.0.0.0/0          nat-12345678
```

**흐름:**
1. VPC A의 인스턴스가 인터넷 요청
2. Transit Gateway로 전송
3. VPC Egress로 라우팅
4. NAT Gateway 통과
5. 인터넷 게이트웨이 통과
6. 인터넷 도달

**비용 절감:**
NAT Gateway 1개만 사용. 비용이 절감된다.

## 리전 간 연결

다른 리전의 Transit Gateway를 연결한다.

**사용 사례:**
- 글로벌 네트워크
- 재해 복구
- 데이터 복제

**설정:**
```bash
# us-west-2의 Transit Gateway
TGW_WEST=tgw-12345678

# us-east-1의 Transit Gateway
TGW_EAST=tgw-87654321

# Peering Attachment 생성 (us-west-2에서)
aws ec2 create-transit-gateway-peering-attachment \
  --transit-gateway-id $TGW_WEST \
  --peer-transit-gateway-id $TGW_EAST \
  --peer-region us-east-1 \
  --region us-west-2

# Peering Attachment 수락 (us-east-1에서)
aws ec2 accept-transit-gateway-peering-attachment \
  --transit-gateway-attachment-id tgw-attach-12345678 \
  --region us-east-1
```

**라우팅 설정:**

**us-west-2 Transit Gateway:**
```
Destination         Attachment
10.0.0.0/16        VPC West
172.16.0.0/16      Peering (to us-east-1)
```

**us-east-1 Transit Gateway:**
```
Destination         Attachment
172.16.0.0/16      VPC East
10.0.0.0/16        Peering (to us-west-2)
```

**결과:**
- us-west-2 VPC → us-east-1 VPC: 가능
- 리전 간 프라이빗 네트워크

**비용:**
리전 간 데이터 전송 비용이 발생한다. $0.02/GB (리전에 따라 다름).

## 모니터링

### CloudWatch 메트릭

**주요 메트릭:**
- **BytesIn**: Transit Gateway로 들어오는 바이트
- **BytesOut**: Transit Gateway에서 나가는 바이트
- **PacketsIn**: 들어오는 패킷 수
- **PacketsOut**: 나가는 패킷 수
- **PacketDropCountBlackhole**: Blackhole 라우팅으로 삭제된 패킷
- **PacketDropCountNoRoute**: 라우팅 규칙이 없어서 삭제된 패킷

**PacketDropCountNoRoute:**
이 메트릭이 0이 아니면 라우팅 설정을 확인한다. 목적지로 가는 경로가 없다.

### Flow Logs

Transit Gateway를 통과하는 트래픽을 로그로 남긴다.

**활성화:**
```bash
aws ec2 create-flow-logs \
  --resource-type TransitGateway \
  --resource-ids tgw-12345678 \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/transitgateway/flowlogs
```

**로그 내용:**
- 소스 IP
- 목적지 IP
- 소스 포트
- 목적지 포트
- 프로토콜
- 패킷 수
- 바이트 수
- Action (ACCEPT/REJECT)

**사용:**
- 트래픽 패턴 분석
- 보안 이슈 파악
- 트러블슈팅

## 트러블슈팅

### 연결이 안 된다

**1. 라우팅 테이블 확인:**

**VPC 라우팅 테이블:**
목적지로 가는 경로가 Transit Gateway로 설정되어 있는지 확인한다.

```bash
aws ec2 describe-route-tables --route-table-ids rtb-12345678
```

**Transit Gateway 라우팅 테이블:**
목적지 VPC로 가는 경로가 있는지 확인한다.

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id tgw-rtb-12345678 \
  --filters "Name=type,Values=static,propagated"
```

**2. 보안 그룹 / NACL:**
보안 그룹과 NACL이 트래픽을 허용하는지 확인한다.

**소스 VPC의 보안 그룹:**
아웃바운드 규칙이 목적지 IP를 허용하는지 확인.

**목적지 VPC의 보안 그룹:**
인바운드 규칙이 소스 IP를 허용하는지 확인.

**3. Attachment 상태:**
Attachment가 "available" 상태인지 확인한다.

```bash
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids tgw-attach-12345678
```

"pending" 또는 "failed" 상태면 문제가 있다.

**4. Association / Propagation:**
Attachment가 올바른 라우팅 테이블에 연결되어 있는지 확인한다.

```bash
aws ec2 get-transit-gateway-attachment-propagations \
  --transit-gateway-attachment-id tgw-attach-12345678
```

### 성능이 느리다

**대역폭 확인:**
Transit Gateway는 Attachment당 최대 50Gbps를 제공한다. 초과하면 제한된다.

**CloudWatch 메트릭:**
BytesIn/BytesOut을 확인한다. 50Gbps에 가까우면 Attachment를 추가하거나 트래픽을 분산한다.

**MTU 크기:**
Transit Gateway는 8500 바이트 MTU를 지원한다. EC2 인스턴스의 MTU를 확인한다.

```bash
# MTU 확인
ip link show eth0

# MTU 변경
sudo ip link set dev eth0 mtu 8500
```

큰 MTU는 성능을 향상시킨다.

### 비용이 많이 나온다

**데이터 전송 비용:**
Transit Gateway는 데이터 전송량에 따라 비용이 발생한다.

**요금:**
- Attachment: $0.05/시간
- 데이터 처리: $0.02/GB

**예시:**
- VPC 10개
- 각 VPC당 10TB/월 전송

**비용:**
- Attachment: 10 × $0.05 × 730시간 = $365/월
- 데이터: 10 × 10TB × 1024GB × $0.02 = $2,048/월
- 합계: $2,413/월

**최적화:**

**불필요한 Attachment 삭제:**
사용하지 않는 VPC는 연결을 해제한다.

**데이터 전송 최소화:**
- 같은 VPC 내에서 통신
- S3 Gateway Endpoint 사용 (Transit Gateway 우회)
- 캐싱으로 반복 전송 줄이기

## 비용

### Attachment 비용

**시간당 요금:**
$0.05/시간 per Attachment

**월 비용:**
$0.05 × 730시간 = $36.50/Attachment

**예시:**
VPC 5개 연결 = $36.50 × 5 = $182.50/월

### 데이터 전송 비용

**AZ 내:**
$0.02/GB

**리전 간:**
$0.02/GB (같은 리전의 다른 AZ)
$0.02/GB ~ $0.09/GB (다른 리전)

**예시:**
100TB/월 전송 = 100 × 1024GB × $0.02 = $2,048/월

### VPC Peering과 비교

**VPC Peering:**
- 연결 비용: 무료
- 데이터 전송: 같은 AZ 무료, 다른 AZ $0.01/GB

**Transit Gateway:**
- Attachment: $36.50/월
- 데이터 전송: $0.02/GB

**VPC 2개, 10GB/월:**
- Peering: $0.10/월
- Transit Gateway: $73 + $0.20 = $73.20/월

Peering이 저렴하다.

**VPC 10개, 100GB/월:**
- Peering: 45개 연결, $45/월 (데이터 전송)
- Transit Gateway: $365 + $200 = $565/월

Peering이 여전히 저렴하다. 하지만 관리가 복잡하다.

**선택 기준:**
- VPC 3개 이하: VPC Peering
- VPC 4개 이상: Transit Gateway
- 온프레미스 연결: Transit Gateway
- 복잡한 라우팅: Transit Gateway

## 참고

- AWS Transit Gateway 개발자 가이드: https://docs.aws.amazon.com/vpc/latest/tgw/
- Transit Gateway 요금: https://aws.amazon.com/transit-gateway/pricing/
- Transit Gateway vs VPC Peering: https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-peering.html
- 모범 사례: https://docs.aws.amazon.com/vpc/latest/tgw/tgw-best-design-practices.html

