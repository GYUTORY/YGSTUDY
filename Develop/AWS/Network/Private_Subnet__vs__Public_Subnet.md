---
title: AWS Private Subnet vs Public Subnet 심화
tags: [aws, vpc, privatesubnet, publicsubnet, internetgateway, natgateway, routetable, securitygroup, nacl, vpcendpoint, ssm, networkarchitecture]
updated: 2026-06-09
---

# AWS Private Subnet vs Public Subnet 심화

## 들어가며

VPC를 처음 설계할 때 가장 헷갈리는 게 "이 서브넷은 Public인가 Private인가"다. AWS 콘솔에는 "Public Subnet"이라는 체크박스가 없다. 콘솔에서 서브넷을 만들 때 "Auto-assign public IPv4 address" 옵션이 있을 뿐이다. 그 옵션을 켜도 인터넷은 안 된다. 서브넷에 라우팅 테이블을 붙이고, 그 라우팅 테이블에 `0.0.0.0/0 → igw-xxxx`가 있어야 비로소 Public Subnet이 된다. 즉 Public/Private은 서브넷의 속성이 아니라 라우팅의 결과다.

운영을 하다 보면 이 사실을 모르고 만든 서브넷 때문에 사고가 난다. "분명 Public Subnet으로 만들었는데 EC2가 외부 통신을 못한다", "NAT Gateway를 달았는데 외부 호출이 간헐적으로 끊긴다", "Bastion 없이 Private EC2에 접속하고 싶다", "S3 트래픽이 다 NAT를 타서 비용이 폭증했다" 같은 문제들이다. 이 문서는 이런 실무 시나리오를 중심으로 IGW, NAT GW, 라우팅 테이블, SG/NACL, VPC Endpoint, Bastion 대안, 3-Tier 격리 설계를 깊이 파고든다.

## Internet Gateway 동작 원리

### IGW가 하는 일은 1:1 NAT다

많은 사람이 IGW를 "라우터"나 "게이트웨이"라고만 알고 있는데, 실제로는 라우팅만 하지 않는다. IGW는 VPC 내부 EC2의 Private IP와 외부에 노출되는 Public IP/EIP 사이의 1:1 NAT 변환을 한다.

예를 들어 EC2 인스턴스가 Private IP `10.0.1.10`을 갖고 EIP `52.78.x.x`가 붙어 있다고 하자. 인스턴스가 `8.8.8.8`로 패킷을 보내면 다음과 같은 변환이 일어난다.

```
EC2 → ENI 출구       : SRC=10.0.1.10:54321, DST=8.8.8.8:53
IGW 통과 직전 변환    : SRC=52.78.x.x:54321, DST=8.8.8.8:53
응답 패킷 IGW 통과   : SRC=8.8.8.8:53, DST=52.78.x.x:54321
EC2 ENI 도착 전 변환 : SRC=8.8.8.8:53, DST=10.0.1.10:54321
```

NAT Gateway처럼 포트를 재할당하지 않는다. Private IP 하나당 Public IP 하나가 1:1로 매핑된다. 이게 IGW가 자체적으로 포트 한계나 동시 연결 수 제약이 없는 이유다.

### Public IP가 없으면 IGW가 있어도 외부 통신 불가

라우팅 테이블에 `0.0.0.0/0 → igw-xxxx`가 있고 SG도 허용 상태인데 외부 통신이 안 되는 경우의 99%는 인스턴스에 Public IP가 없기 때문이다. IGW는 1:1 NAT를 하므로 변환할 Public IP가 없으면 패킷을 인터넷으로 보낼 수 없다.

```bash
# EC2에 Public IP가 할당되어 있는지 확인
aws ec2 describe-instances \
  --instance-ids i-0123456789abcdef0 \
  --query 'Reservations[].Instances[].[InstanceId,PrivateIpAddress,PublicIpAddress,SubnetId]' \
  --output table
```

`PublicIpAddress`가 `None`이면 IGW를 통과할 수 없다. 해결책은 두 가지다.

1. EIP를 할당해서 ENI에 붙인다.
2. 서브넷의 "Auto-assign public IPv4 address"를 활성화하고 인스턴스를 새로 생성한다(기존 인스턴스는 재시작해도 IP가 안 바뀐다).

### IGW는 수평 확장형 컴포넌트, SPOF가 없다

NAT Gateway는 AZ에 종속된다(특정 AZ 내부에 만들어진다). IGW는 다르다. IGW는 VPC 단위 리소스이고 AWS가 내부적으로 수평 확장된 분산 시스템으로 운영한다. AZ가 하나 죽어도 IGW 자체는 영향을 받지 않는다.

그래서 IGW는 VPC에 1개만 붙일 수 있고, 사용자가 별도로 가용성/성능을 신경 쓸 필요가 없다. NAT Gateway는 AZ당 하나씩 두는 게 정석인데, IGW는 그런 고민이 필요 없다.

### Public Subnet의 정의는 결국 라우팅이다

다음 조건을 모두 만족해야 Public Subnet으로 동작한다.

1. 서브넷이 attach된 라우팅 테이블에 `0.0.0.0/0 → igw-xxxx`가 있다.
2. 인스턴스가 Public IP 또는 EIP를 갖고 있다.
3. SG와 NACL이 해당 트래픽을 허용한다.

이 중 하나라도 빠지면 Public Subnet으로 동작하지 않는다. "서브넷 이름을 public-subnet으로 지었다"는 아무 의미가 없다. 운영 중 "이게 Public인지 Private인지 확실하지 않으면" 라우팅 테이블을 직접 확인하면 된다.

```bash
# 서브넷에 연결된 라우팅 테이블 확인
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=subnet-0123456789abcdef0" \
  --query 'RouteTables[].Routes[]'
```

응답에서 `GatewayId`가 `igw-`로 시작하면 Public, `nat-`로 시작하면 Private(NAT 경유), 둘 다 없으면 완전 격리된 Private이다.

## NAT Gateway 심화

### AZ별 배치는 필수, 안 하면 Cross-AZ 비용과 SPOF 위험

NAT Gateway를 만들 때 서브넷을 선택하게 되는데, 이 서브넷이 속한 AZ에 NAT GW가 생성된다. NAT GW는 AZ에 종속된 리소스다.

만약 ap-northeast-2a, 2b, 2c 세 AZ에 Private Subnet이 있는데 NAT GW를 2a에만 만들어두면 다음 문제가 생긴다.

1. 2b, 2c의 Private EC2에서 나가는 트래픽은 전부 2a의 NAT GW를 거친다.
2. Cross-AZ 데이터 전송 요금이 발생한다(아웃바운드 0.01 USD/GB 수준이지만 트래픽이 크면 무시 못함).
3. 2a AZ에 장애가 나면 2b, 2c의 인스턴스도 외부 통신이 불가능해진다(SPOF).

해결책은 AZ당 NAT GW 하나씩 두는 것이다. 각 AZ의 Private 서브넷은 같은 AZ의 NAT GW로 라우팅한다.

```hcl
# Terraform 예시 — AZ별 NAT GW 구성
locals {
  azs = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
}

resource "aws_eip" "nat" {
  count  = length(local.azs)
  domain = "vpc"
}

resource "aws_nat_gateway" "this" {
  count         = length(local.azs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "natgw-${local.azs[count.index]}"
  }
}

resource "aws_route_table" "private" {
  count  = length(local.azs)
  vpc_id = aws_vpc.this.id
}

resource "aws_route" "private_default" {
  count                  = length(local.azs)
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[count.index].id
}
```

핵심은 `aws_route_table.private`도 AZ 수만큼 만든다는 점이다. 라우팅 테이블 하나에 NAT GW 하나만 매핑되므로, AZ별 NAT GW를 쓰려면 라우팅 테이블도 AZ별로 분리해야 한다. 같은 라우팅 테이블을 여러 서브넷이 공유하면 NAT GW가 하나로 묶이는 효과가 난다.

### Source/Destination Check 비활성화는 EC2 NAT일 때만

NAT Gateway는 AWS 관리형 서비스라 이 옵션을 신경 쓸 필요가 없다. 하지만 EC2 인스턴스를 NAT로 쓰는 경우(과거 NAT Instance 방식)에는 ENI의 Source/Destination Check를 꺼야 한다.

기본적으로 ENI는 송신/수신 패킷의 출발지나 목적지가 자신의 IP가 아니면 폐기한다. NAT 역할을 하려면 자기 IP가 아닌 패킷도 통과시켜야 하므로 이 검증을 비활성화해야 한다.

```bash
aws ec2 modify-network-interface-attribute \
  --network-interface-id eni-0123456789abcdef0 \
  --source-dest-check '{"Value": false}'
```

이 동작 원리를 이해하면 왜 NAT Gateway가 "ENI 하나당 EIP 하나"로 운영되는지가 자연스럽다.

### 포트당 55,000 동시 연결 한계와 ECONNRESET

NAT Gateway의 가장 흔한 트러블슈팅 사례가 이거다. NAT GW는 하나의 출발지 IP(EIP)와 하나의 목적지(Destination IP + Port) 조합에 대해 약 55,000개의 동시 연결을 처리할 수 있다.

특정 외부 서비스 하나에 동시에 55,000개 이상 연결을 만들면 `Connection reset` 또는 `Connection refused` 오류가 발생한다. CloudWatch의 NAT GW 메트릭에서 `ErrorPortAllocation` 값이 0보다 크면 이 문제다.

```bash
# NAT GW의 포트 할당 실패 감지
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name ErrorPortAllocation \
  --dimensions Name=NatGatewayId,Value=nat-0123456789abcdef0 \
  --start-time 2026-06-08T00:00:00Z \
  --end-time 2026-06-09T00:00:00Z \
  --period 300 \
  --statistics Sum
```

이 한계에 부딪히는 사례는 보통 다음과 같다.

1. Kinesis Firehose나 외부 SaaS API로 짧은 시간에 수만 건의 요청이 동시에 발생한다.
2. Lambda가 Provisioned Concurrency로 수천 개 동시 실행되며 같은 외부 엔드포인트를 호출한다.
3. EKS 클러스터의 모든 노드가 같은 모니터링 서비스로 outbound 연결을 만든다.

해결책은 NAT GW를 여러 개 두고 트래픽을 분산시키는 것이다. 라우팅 테이블별로 다른 NAT GW를 가리키게 하거나, 가능하면 VPC Endpoint로 우회한다. AWS 서비스 호출이라면 Interface Endpoint를 만들어 NAT GW를 거치지 않게 한다.

### 350초 idle timeout이 만드는 함정

NAT Gateway는 연결이 350초(약 5.8분) 동안 유휴 상태면 자동으로 연결 추적 테이블에서 제거한다. 그 후 클라이언트가 같은 연결로 패킷을 보내면 NAT GW는 RST를 보내고, 애플리케이션은 `ECONNRESET`을 받는다.

DB 커넥션 풀이나 keep-alive HTTPS 연결에서 자주 발생한다. 예를 들어 EC2에서 RDS Proxy로 가는 연결을 5분 이상 idle 상태로 두면 NAT GW를 거친 연결은 끊긴다(RDS Proxy를 VPC 내부에 두면 NAT GW를 안 거치니 해당 없음). 외부 SaaS API와의 연결도 마찬가지다.

해결책은 TCP keepalive를 350초보다 짧게 설정하는 것이다.

```bash
# Linux 커널 파라미터 — keepalive를 240초로 단축
sudo sysctl -w net.ipv4.tcp_keepalive_time=240
sudo sysctl -w net.ipv4.tcp_keepalive_intvl=30
sudo sysctl -w net.ipv4.tcp_keepalive_probes=3
```

영구 적용은 `/etc/sysctl.conf`에 추가한다. 애플리케이션 레벨에서는 HTTP 클라이언트의 connection pool TTL을 300초 이하로 잡거나, DB 커넥션 풀의 `idleTimeout`을 NAT GW 타임아웃보다 짧게 설정한다.

### EIP 고정으로 외부 화이트리스트 적용

NAT Gateway 생성 시 EIP를 지정하면 그 IP가 outbound 출발지로 고정된다. 외부 파트너 API가 IP 화이트리스트를 요구하는 경우 NAT GW의 EIP를 알려주면 된다.

주의할 점은 AZ별 NAT GW를 쓰면 EIP도 여러 개라는 것이다. 파트너 측에 모든 NAT GW의 EIP를 화이트리스트로 등록해야 한다. 자동 페일오버를 고려하면 NAT GW가 죽고 다시 만들 때 같은 EIP를 재사용하도록 운영 절차를 만들어야 한다.

```bash
# NAT GW와 연결된 EIP 조회
aws ec2 describe-nat-gateways \
  --filter "Name=state,Values=available" \
  --query 'NatGateways[].[NatGatewayId,NatGatewayAddresses[].PublicIp]' \
  --output table
```

## 라우팅 테이블 우선순위와 함정

### Longest Prefix Match가 최우선

라우팅 테이블에 여러 라우트가 매칭될 때 가장 긴 prefix가 이긴다. 이건 일반 네트워크 라우팅 규칙과 동일하다.

예를 들어 다음 라우팅 테이블이 있다고 하자.

```
10.0.0.0/16    → local
10.0.5.0/24    → tgw-0123 (Transit Gateway)
0.0.0.0/0      → igw-0456
```

대상 `10.0.5.10`으로 가는 패킷은 `/24` 라우트가 가장 길게 매치되므로 TGW로 간다. `10.0.10.10`은 `/16`이 매치되어 local로 가고, `8.8.8.8`은 `/0`이 매치되어 IGW로 간다.

이 규칙 때문에 흔히 발생하는 실수가 있다. on-premise CIDR이 `10.0.0.0/8`인 환경에서 VPC를 `10.0.0.0/16`으로 만들면, VPC 내부에서는 `/16` 라우트가 우선해서 local로 간다. on-premise의 `10.0.5.0/24`로 가려고 해도 local 라우트에 가로채여 도달하지 못한다. 그래서 VPC CIDR과 on-premise CIDR이 겹치면 안 된다.

### Local 라우트는 삭제도 변경도 불가

VPC의 CIDR에 해당하는 local 라우트는 시스템이 자동으로 추가하고, 사용자가 삭제할 수 없다. 즉 VPC 내부 통신은 무조건 local로 라우팅된다. 이걸 막으려면 SG, NACL, Network Firewall로 차단해야지 라우팅으로는 안 된다.

다만 2023년부터 VPC 내부의 특정 서브넷 간 통신을 Gateway Load Balancer로 강제 라우팅하는 기능이 추가됐다(MGN). 이것도 local보다 우선시되는 게 아니라 별도 메커니즘이다.

### 동일 prefix에서 라우팅 소스 우선순위

같은 prefix를 가진 라우트가 여러 소스에서 들어오면 다음 순서로 우선시된다.

1. Local (VPC CIDR)
2. Most specific static route(정적으로 추가한 라우트)
3. Direct Connect propagated route
4. VPN(VGW) propagated route
5. Transit Gateway propagated route
6. Internet Gateway, NAT Gateway 등

예를 들어 VPN과 Direct Connect로 둘 다 같은 on-premise CIDR `192.168.0.0/16`을 propagate한다면 Direct Connect가 우선시된다. DX 회선이 끊기면 자동으로 VPN으로 페일오버되도록 설계할 때 이 우선순위를 이용한다.

### Main RT와 Custom RT의 함정

VPC를 만들면 Main Route Table이 자동 생성된다. 서브넷에 명시적으로 라우팅 테이블을 연결하지 않으면 Main RT가 적용된다. 여기서 사고가 난다.

흔한 시나리오: 새로 만든 서브넷을 "Public Subnet"으로 쓰려고 EIP를 붙인 EC2를 띄웠는데 외부 통신이 안 된다. 라우팅 테이블을 확인하면 Main RT에 IGW 라우트가 없다. 새 서브넷에 명시적으로 Custom RT(IGW 라우트 있는)를 attach하지 않았기 때문이다.

운영 원칙은 명확하다. Main RT는 가능하면 비워두거나 가장 보수적인(local만 있는) 상태로 둔다. 모든 서브넷은 명시적으로 자신의 용도에 맞는 Custom RT에 attach한다. 이렇게 해야 "실수로 attach 안 한 서브넷이 Public이 되거나 NAT를 거치는" 사고를 막을 수 있다.

```bash
# 어떤 서브넷이 어떤 RT에 attach되어 있는지 일괄 확인
aws ec2 describe-route-tables \
  --query 'RouteTables[].[RouteTableId,VpcId,Associations[?SubnetId!=null].[SubnetId,Main]]' \
  --output json
```

## Security Group vs NACL 실전

### Stateful과 Stateless의 차이가 만드는 사고

Security Group은 stateful이다. inbound로 허용된 연결의 응답은 outbound 규칙과 무관하게 자동으로 허용된다. NACL은 stateless다. 요청과 응답을 양방향 모두 명시적으로 허용해야 한다.

이 차이가 가장 큰 문제를 일으키는 곳이 NACL의 ephemeral port range다. 클라이언트가 서버의 80번 포트에 연결하면 클라이언트는 ephemeral port(1024~65535 중 하나)를 사용한다. 서버는 80에서 응답을 보내고 클라이언트는 ephemeral port로 받는다.

NACL이 stateless이므로 outbound에 ephemeral port range가 열려 있어야 응답이 나갈 수 있다. 마찬가지로 클라이언트 측 NACL의 inbound에도 ephemeral port range가 열려 있어야 응답이 들어올 수 있다.

이걸 모르고 NACL을 강하게 잠그면 발생하는 증상이 "TCP 연결은 SYN/SYN-ACK까지 가는데 데이터가 안 흐른다", "ALB는 healthy인데 응답이 timeout 난다" 같은 패턴이다.

NACL 설정 예시:

```
Inbound Rules:
100 ALLOW TCP 443 0.0.0.0/0      (HTTPS 인바운드)
110 ALLOW TCP 80 0.0.0.0/0       (HTTP 인바운드)
120 ALLOW TCP 1024-65535 0.0.0.0/0  (ephemeral port, outbound 응답용)

Outbound Rules:
100 ALLOW TCP 1024-65535 0.0.0.0/0  (클라이언트 ephemeral port로 응답)
110 ALLOW TCP 443 0.0.0.0/0      (outbound HTTPS)
```

Linux 커널의 ephemeral port range는 `/proc/sys/net/ipv4/ip_local_port_range`로 확인할 수 있다. 보통 `32768-60999`다. Windows는 `1025-5000`이 기본이다. 클라이언트가 어떤 OS인지 모르면 안전하게 `1024-65535` 전체를 여는 게 보통이다.

### SG는 ALLOW만, NACL은 DENY 가능

Security Group은 화이트리스트 방식이다. 명시적으로 허용한 트래픽만 통과하고, 명시적으로 거부하는 규칙은 만들 수 없다. NACL은 ALLOW와 DENY 규칙을 모두 만들 수 있다. 번호가 작은 규칙부터 평가하고 매치되면 즉시 결정한다.

특정 IP만 차단하고 싶을 때 SG로는 불가능하다. NACL의 DENY 규칙으로만 가능하다.

```
Inbound NACL (위에서부터 평가):
90  DENY TCP 22 1.2.3.4/32        (특정 IP만 SSH 차단)
100 ALLOW TCP 22 0.0.0.0/0        (나머지는 SSH 허용)
*   DENY ALL                       (암묵적 거부)
```

실무에서는 DDoS나 침해 사고 시 특정 IP 대역을 빠르게 차단할 때 NACL DENY를 쓴다. AWS WAF의 IP Set도 같은 역할을 하지만 ALB/CloudFront 앞단이고, EC2 직접 차단은 NACL이 맞다.

### 규칙 평가 순서와 우선순위 충돌

NACL은 번호 순으로 평가한다. 같은 트래픽에 매치되는 규칙이 여러 개면 가장 작은 번호의 규칙이 결정한다. 그래서 번호를 100, 110, 120 같이 띄워두는 게 관례다. 나중에 105, 115를 끼워 넣을 수 있어서다.

SG는 모든 규칙이 OR로 평가된다(허용 규칙 중 하나라도 매치되면 통과). 순서 개념이 없다.

SG와 NACL이 둘 다 적용될 때는 AND다. SG가 허용해도 NACL이 거부하면 차단되고, NACL이 허용해도 SG가 거부하면 차단된다. 양쪽 모두 허용해야 패킷이 통과한다.

운영 관점에서 권장하는 분담은 이렇다. SG는 인스턴스/서비스 단위로 세밀하게 작성한다(예: app-sg는 db-sg에서 오는 5432만 허용). NACL은 서브넷 단위로 거친 정책만 둔다(예: 내부망 외부에서 SSH 차단, 특정 국가 IP 차단). NACL을 너무 세밀하게 쓰면 ephemeral port 문제로 사고가 잦다.

```bash
# 특정 EC2의 SG와 서브넷의 NACL을 한 번에 조회
INSTANCE_ID=i-0123456789abcdef0
SUBNET_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SubnetId' --output text)
SG_IDS=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SecurityGroups[].GroupId' --output text)

echo "Subnet: $SUBNET_ID"
echo "SGs: $SG_IDS"

aws ec2 describe-network-acls \
  --filters "Name=association.subnet-id,Values=$SUBNET_ID" \
  --query 'NetworkAcls[].Entries' --output json
```

### SG 체인으로 3-Tier 격리하기

SG는 다른 SG를 source/destination으로 지정할 수 있다. IP 대역 대신 SG ID로 참조하면 인스턴스가 늘어나고 줄어도 자동으로 따라간다. 이게 SG 체인이다.

```
[Internet] → alb-sg (443 from 0.0.0.0/0)
[ALB]     → app-sg (8080 from alb-sg)
[App EC2] → db-sg (5432 from app-sg)
[RDS]
```

이 구조에서 app-sg의 inbound는 `8080 from alb-sg`로만 열어둔다. App 인스턴스가 어느 IP를 받든 ALB에서만 받을 수 있다. db-sg의 inbound는 `5432 from app-sg`로만 열어둔다. App 외에는 DB 접근이 불가능하다.

Terraform 예시:

```hcl
resource "aws_security_group" "alb" {
  name   = "alb-sg"
  vpc_id = aws_vpc.this.id
}

resource "aws_security_group_rule" "alb_ingress_https" {
  type              = "ingress"
  security_group_id = aws_security_group.alb.id
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = aws_vpc.this.id
}

resource "aws_security_group_rule" "app_ingress_from_alb" {
  type                     = "ingress"
  security_group_id        = aws_security_group.app.id
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = aws_vpc.this.id
}

resource "aws_security_group_rule" "db_ingress_from_app" {
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app.id
}
```

이 패턴의 장점은 명확하다. App EC2의 IP가 바뀌어도 DB SG를 수정할 필요가 없다. App Auto Scaling Group이 새 인스턴스를 만들어도 자동으로 DB 접근 권한이 부여된다.

## Bastion Host 대안 비교

### 전통적 Bastion의 문제

전통적인 Bastion Host는 Public Subnet에 EC2를 두고 SSH 22번을 외부에 노출한다. Private EC2에 접근할 때 Bastion을 거쳐 SSH로 점프한다.

이 방식의 문제는 다음과 같다.

1. SSH 22번 포트가 인터넷에 열려 있어 brute-force 공격 대상이 된다.
2. SSH 키를 관리해야 한다(키 분실, 유출, 회수 관리 부담).
3. 누가 언제 어디로 점프했는지 추적이 어렵다(별도 로깅 구성 필요).
4. Bastion 자체의 가용성을 신경 써야 한다(Auto Scaling, 패치 등).
5. 사용자별 OS 계정 관리가 필요하다.

### SSM Session Manager가 표준이 됐다

AWS Systems Manager Session Manager는 SSH 없이 EC2 셸 접속을 제공한다. 동작 원리는 다음과 같다.

1. EC2에 SSM Agent가 설치되어 있다(Amazon Linux 2/2023, Ubuntu 18.04+ 기본 설치).
2. EC2의 IAM Instance Profile에 `AmazonSSMManagedInstanceCore` 정책이 붙어 있다.
3. EC2가 SSM 서비스 엔드포인트로 outbound 연결을 만들어 long-poll한다.
4. 사용자가 콘솔/CLI로 세션을 시작하면 SSM이 EC2 측에 명령을 전달한다.

이 구조에서 22번 포트는 닫혀 있어도 된다. inbound가 전혀 필요 없다. 모든 연결은 EC2에서 outbound로만 만들어진다.

```bash
# SSM Session Manager로 Private EC2 접속
aws ssm start-session --target i-0123456789abcdef0

# SSH 포워딩 — 로컬에서 RDS로 터널링
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["db.cluster-xxx.ap-northeast-2.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

이 방식의 장점은 압도적이다.

1. 22번 포트 노출 없음(SG에 SSH inbound가 필요 없다).
2. IAM 기반 인증(SSH 키 관리 불필요).
3. 모든 세션이 CloudTrail에 기록된다. 명령어까지 S3/CloudWatch Logs에 저장 가능.
4. 사용자별 IAM 권한으로 접근 제어한다.
5. 기존 EC2 키 페어 분실해도 SSM으로 접속 가능.

전제 조건은 EC2가 SSM 서비스 엔드포인트에 도달할 수 있어야 한다는 것이다. Private Subnet에 있는 EC2가 SSM을 쓰려면 NAT GW를 통해 인터넷으로 나가거나, Interface Endpoint로 SSM 엔드포인트를 VPC 내부에 만들어야 한다. 후자가 더 격리된 방식이다.

```bash
# SSM을 위한 Interface Endpoint 3개 생성
for svc in ssm ssmmessages ec2messages; do
  aws ec2 create-vpc-endpoint \
    --vpc-id vpc-0123456789abcdef0 \
    --vpc-endpoint-type Interface \
    --service-name "com.amazonaws.ap-northeast-2.${svc}" \
    --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
    --security-group-ids sg-ssm-endpoint \
    --private-dns-enabled
done
```

`ssm`, `ssmmessages`, `ec2messages` 세 엔드포인트가 모두 필요하다. 하나라도 빠지면 Session Manager가 동작하지 않는다. 처음 구성할 때 자주 빠뜨리는 부분이다.

### EC2 Instance Connect Endpoint(EICE)

2023년 출시된 EC2 Instance Connect Endpoint는 Private Subnet의 EC2에 별도 Bastion 없이 SSH 접속을 제공한다. 동작은 SSM과 비슷하지만 SSH 프로토콜을 그대로 쓴다는 차이가 있다.

```bash
# EICE 생성
aws ec2 create-instance-connect-endpoint \
  --subnet-id subnet-0123456789abcdef0 \
  --security-group-ids sg-eice

# EICE 통한 SSH 접속
aws ec2-instance-connect ssh \
  --instance-id i-0123456789abcdef0 \
  --connection-type eice
```

SSM과 비교한 EICE의 장점은 기존 SSH 워크플로(rsync, scp, SSH tunneling 등)를 그대로 쓸 수 있다는 점이다. 단점은 SSM Agent가 제공하는 세션 로깅이 없고, IAM 정책이 SSM보다 거칠다는 점이다.

선택 기준은 명확하다. 단순 셸 접속과 감사가 중요하면 SSM Session Manager, 기존 SSH 도구 호환성이 필요하면 EICE다. 둘 다 깔아두고 상황에 맞게 쓰는 곳도 많다.

### Client VPN과의 비교

AWS Client VPN은 사용자 디바이스가 VPC에 직접 연결되는 방식이다. OpenVPN 기반이고 클라이언트 앱을 설치해야 한다. VPC 전체 네트워크에 접근할 수 있어 여러 인스턴스, RDS, ElastiCache까지 한 번에 접근 가능하다.

비용은 비싸다. 연결당 시간 요금과 엔드포인트 자체 시간 요금이 동시에 붙는다(2026년 6월 기준 시간당 0.10 USD/엔드포인트, 0.05 USD/활성 연결). 사용자가 많고 VPC 전체 접근이 필요한 환경에 적합하다. 개발자 몇 명의 트러블슈팅 접근용으로는 SSM이 더 싸고 간단하다.

| 항목 | 전통적 Bastion | SSM Session Manager | EC2 Instance Connect Endpoint | Client VPN |
|---|---|---|---|---|
| SSH 포트 노출 | 필요 | 불필요 | 불필요 | 불필요 |
| 키 관리 | 필요 | 불필요 | 단기 키 자동 | 인증서 필요 |
| 세션 로깅 | 별도 구성 | 자동 | 별도 구성 | 연결 로그만 |
| IAM 통합 | 없음 | 있음 | 있음 | 일부 |
| 기존 SSH 도구 호환 | 가능 | 제한적 | 가능 | 가능 |
| 비용 | EC2 비용 | 없음 | 시간당 0.10 USD | 시간당 0.10+0.05 USD |
| VPC 전체 접근 | 가능(점프) | 인스턴스 단위 | 인스턴스 단위 | 가능 |

## VPC Endpoint를 활용한 트래픽 격리

### Gateway Endpoint와 Interface Endpoint의 차이

VPC Endpoint는 두 종류다. Gateway Endpoint와 Interface Endpoint(PrivateLink)다.

**Gateway Endpoint**는 라우팅 테이블 기반이다. S3와 DynamoDB 두 서비스만 지원한다. 비용이 무료다. 동작 방식은 다음과 같다.

1. Gateway Endpoint를 만들면 prefix list `pl-xxxx`가 생긴다.
2. 라우팅 테이블에 `pl-xxxx → vpce-xxxx`가 자동 추가된다.
3. S3로 가는 패킷은 IGW/NAT GW를 거치지 않고 Endpoint를 통해 AWS 백본으로 직접 간다.

```bash
# S3 Gateway Endpoint 생성 (Private RT에 자동 attach)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.ap-northeast-2.s3 \
  --route-table-ids rtb-private-a rtb-private-b rtb-private-c \
  --vpc-endpoint-type Gateway
```

라우팅 테이블 우선순위 규칙(Longest Prefix Match)을 다시 떠올리면, prefix list가 `0.0.0.0/0`보다 길게 매치되므로 S3 트래픽은 항상 Endpoint로 간다.

**Interface Endpoint**는 ENI 기반이다. 서브넷에 ENI를 만들고 PrivateLink로 서비스에 연결한다. 대부분의 AWS 서비스(SSM, SQS, SNS, KMS, Secrets Manager, ECR, CloudWatch 등)와 일부 SaaS 파트너 서비스가 지원된다.

```bash
# SQS Interface Endpoint 생성
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.ap-northeast-2.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --security-group-ids sg-vpce-sqs \
  --private-dns-enabled
```

`--private-dns-enabled`를 켜면 SQS 도메인(`sqs.ap-northeast-2.amazonaws.com`)이 VPC 내부 DNS에서 Endpoint의 Private IP로 해석된다. 애플리케이션 코드를 바꾸지 않아도 SQS 호출이 자동으로 Endpoint로 간다.

비용은 발생한다. 시간당 약 0.01 USD/AZ + 0.01 USD/GB 수준이다. 그래서 AZ가 3개면 시간당 0.03 USD가 기본으로 든다.

### Endpoint Policy로 IAM 외 추가 제어

Endpoint에 정책을 붙여 어떤 작업/리소스만 통과시킬지 추가 제한할 수 있다. IAM 정책과 별개의 평가 계층이다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ]
    }
  ]
}
```

이 정책을 S3 Gateway Endpoint에 붙이면 해당 VPC 내부에서는 `my-app-bucket` 외의 S3 버킷에 접근할 수 없다. IAM 권한이 있어도 Endpoint 정책이 거부하면 차단된다.

활용 시나리오는 데이터 유출 방지다. 사내 데이터가 VPC 내부에서 외부 계정의 S3 버킷으로 빠져나가는 것을 막는다. 다른 계정의 S3는 Endpoint Policy로 차단하고, NAT GW로의 outbound 라우트도 막아두면 데이터가 VPC 밖으로 나가는 경로가 사실상 없다.

### NAT Gateway 비용 절감 효과

NAT Gateway 비용은 시간당 0.045 USD + 처리 데이터 0.045 USD/GB 수준이다(서울 리전 기준). 트래픽이 많으면 비용이 폭증한다.

예를 들어 한 달에 10TB의 S3 트래픽이 NAT GW를 거쳐 나간다고 하자.

```
NAT GW 처리 비용: 10,000 GB × 0.045 USD = 450 USD/월
NAT GW 시간당 비용: 0.045 × 24 × 30 = 32.4 USD/월
총: 약 482 USD/월
```

S3 Gateway Endpoint로 바꾸면:

```
Gateway Endpoint 비용: 0 USD (S3는 Gateway Endpoint 무료)
S3 데이터 전송: 같은 리전 내 무료
총: 0 USD/월
```

월 480 USD를 아낀다. Gateway Endpoint는 S3/DynamoDB만 지원하지만 보통 트래픽의 대부분이 이 두 서비스다. EKS 클러스터에서 ECR 이미지를 매번 풀하는 환경에서는 ECR Interface Endpoint도 비슷한 효과를 낸다(ECR 이미지 풀이 S3 백엔드를 거치므로 S3 Gateway Endpoint와 함께 써야 효과적이다).

CloudWatch Logs도 큰 비용원이다. EC2가 로그를 다 NAT GW로 보내면 처리 비용이 커진다. CloudWatch Logs Interface Endpoint를 만들면 비용이 크게 줄어든다.

```hcl
# Terraform — 비용 절감용 Endpoint 묶음
locals {
  interface_endpoints = [
    "ecr.api",
    "ecr.dkr",
    "logs",
    "monitoring",
    "secretsmanager",
    "ssm",
    "ssmmessages",
    "ec2messages",
    "kms",
    "sqs",
    "sns",
  ]
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id
}

resource "aws_vpc_endpoint" "interface" {
  for_each            = toset(local.interface_endpoints)
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}
```

## 3-Tier 트래픽 격리 설계

### 서브넷 분리 구조

표준적인 3-Tier 구성은 다음과 같다.

```
VPC: 10.0.0.0/16

ap-northeast-2a
├── Public Subnet         : 10.0.0.0/24    (ALB, NAT GW, EICE)
├── Private App Subnet    : 10.0.10.0/24   (애플리케이션 EC2/ECS/EKS)
└── Private DB Subnet     : 10.0.20.0/24   (RDS, ElastiCache)

ap-northeast-2b
├── Public Subnet         : 10.0.1.0/24
├── Private App Subnet    : 10.0.11.0/24
└── Private DB Subnet     : 10.0.21.0/24

ap-northeast-2c
├── Public Subnet         : 10.0.2.0/24
├── Private App Subnet    : 10.0.12.0/24
└── Private DB Subnet     : 10.0.22.0/24
```

CIDR 설계 원칙은 다음과 같다.

1. VPC는 `/16`(65,536 IP)으로 넉넉히 잡는다. 처음에 작게 잡으면 나중에 IPv4 부족으로 고생한다.
2. 같은 AZ의 서브넷은 인접 CIDR로 묶지 말고 용도별로 멀리 떨어진 CIDR을 쓴다(`/24` 단위로 끊고 두 번째 옥텟으로 용도 구분). 이렇게 해야 Network Firewall에서 CIDR 기반 정책을 만들기 쉽다.
3. 같은 용도의 서브넷은 AZ별로 인접 CIDR(`/24` 단위 연속)을 쓴다. CIDR을 보면 어느 AZ인지 구분된다.
4. `/24`(256 IP)는 보통 충분하다. EKS 클러스터처럼 Pod IP를 서브넷에서 가져오는 경우 `/22`(1024 IP) 이상으로 늘려야 한다.

### 라우팅 테이블 구성

이 구조에서 라우팅 테이블은 다음과 같이 분리된다.

| RT 이름 | 매핑 서브넷 | 라우트 |
|---|---|---|
| rtb-public | Public 서브넷 3개 | `0.0.0.0/0 → igw-xxx` |
| rtb-private-app-2a | App 2a | `0.0.0.0/0 → nat-2a` |
| rtb-private-app-2b | App 2b | `0.0.0.0/0 → nat-2b` |
| rtb-private-app-2c | App 2c | `0.0.0.0/0 → nat-2c` |
| rtb-private-db | DB 서브넷 3개 | 로컬만 |

DB 서브넷은 NAT GW도 IGW도 없다. 외부와 완전히 격리된다. 패치는 SSM Patch Manager로 한다(SSM 엔드포인트만 닿으면 됨).

App 서브넷은 AZ별로 RT를 분리해야 한다. AZ별 NAT GW를 쓰려면 어쩔 수 없다. 같은 RT에 여러 AZ의 서브넷을 묶으면 NAT GW가 하나로 묶여 Cross-AZ 비용/SPOF 문제가 생긴다.

### SG 체인 구성

3-Tier에서 SG 체인은 다음과 같이 만든다.

```
alb-sg:
  inbound: 443 from 0.0.0.0/0

app-sg:
  inbound: 8080 from alb-sg

db-sg:
  inbound: 5432 from app-sg

cache-sg:
  inbound: 6379 from app-sg

vpce-sg:
  inbound: 443 from VPC CIDR (Endpoint들 공통 사용)
```

App SG에는 NAT GW outbound나 외부 통신을 위한 outbound 규칙도 둔다(기본 outbound는 all open이지만 보수적으로 운영하려면 명시 제한). 외부 결제 API를 호출한다면 outbound에 `443 to 결제사 IP/도메인`만 열어둔다.

### IPv6와 Egress-Only Internet Gateway

VPC에 IPv6를 활성화하면 IPv6는 기본적으로 Public이다. NAT 개념이 없어서다. Private 서브넷 인스턴스에 IPv6 주소가 붙으면 외부에서 직접 접근 가능하다.

IPv6에서 outbound는 허용하되 inbound는 차단하려면 Egress-Only Internet Gateway(EIGW)를 쓴다. IPv4의 NAT GW와 비슷한 역할이지만 NAT 변환 없이 stateful filtering만 한다(IPv6는 NAT가 필요 없음).

```bash
# EIGW 생성
aws ec2 create-egress-only-internet-gateway \
  --vpc-id vpc-0123456789abcdef0

# Private RT에 IPv6 default route 추가
aws ec2 create-route \
  --route-table-id rtb-private-app-2a \
  --destination-ipv6-cidr-block ::/0 \
  --egress-only-internet-gateway-id eigw-0123456789abcdef0
```

IPv6를 안 쓴다면 SG outbound에서 `::/0`을 막거나, 서브넷에 IPv6 CIDR 자체를 할당하지 않으면 된다.

### VPC Flow Logs로 격리 검증

설계대로 격리가 되고 있는지는 VPC Flow Logs로 검증한다. Flow Logs는 ENI 단위로 트래픽 메타데이터를 수집한다.

```bash
# VPC 전체에 Flow Logs 활성화
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-0123456789abcdef0 \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flow-logs \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/FlowLogsRole
```

검증 쿼리 예시(CloudWatch Logs Insights):

```sql
# DB 서브넷으로 들어오는 트래픽 중 App SG에서 오지 않은 게 있나
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action
| filter dstAddr like /^10\.0\.2[0-2]\./
| filter action = "ACCEPT"
| stats count() by srcAddr, dstAddr, dstPort
| sort count desc
```

```sql
# Public에서 직접 Private DB로 들어가려는 시도(REJECT만 보면 됨)
fields @timestamp, srcAddr, dstAddr, dstPort
| filter dstAddr like /^10\.0\.2[0-2]\./
| filter action = "REJECT"
| stats count() by srcAddr, dstPort
```

격리가 잘 됐다면 두 번째 쿼리에서 의미 있는 트래픽이 안 잡혀야 한다. 정상 트래픽 외에 REJECT가 쌓이고 있다면 NACL이나 SG 규칙이 누락된 게 있거나 누군가 잘못된 클라이언트를 만들었거나, 침해 시도일 수 있다.

Flow Logs는 패킷 페이로드는 안 본다. 메타데이터(IP, 포트, 바이트 수, action)만 수집한다. 페이로드 분석이 필요하면 VPC Traffic Mirroring을 써야 한다.

### 자주 만나는 격리 사고

3-Tier 구성에서 격리가 깨지는 패턴을 몇 가지 정리한다.

**케이스 1: DB SG에 0.0.0.0/0이 열려 있다.**
누군가 트러블슈팅하면서 임시로 열어두고 안 닫은 경우다. SG는 변경 이력이 CloudTrail에 남는다. AWS Config Rules의 `restricted-common-ports` 룰로 자동 감지/알림을 걸어두면 좋다.

**케이스 2: Public Subnet에 RDS가 있다.**
RDS 생성 시 "Publicly accessible: Yes"로 만들면 RDS 엔드포인트에 Public IP가 붙는다. SG에서 막아도 패스워드만 알면 외부에서 접근 가능한 상태가 된다. 운영 DB는 무조건 "Publicly accessible: No"로 만든다.

```bash
# Public RDS 인스턴스 감지
aws rds describe-db-instances \
  --query 'DBInstances[?PubliclyAccessible==`true`].[DBInstanceIdentifier,Endpoint.Address]' \
  --output table
```

**케이스 3: NAT GW가 한 AZ에만 있다.**
운영 중인 시스템에서 그 AZ가 장애 나면 다른 AZ의 App도 외부 통신 불가가 되어 장애가 확산된다. NAT GW 비용을 아끼려고 한 AZ에만 두는 경우가 많은데, 운영 환경에서는 AZ별로 두는 게 표준이다. 비용 절감은 NAT GW 줄이기보다 VPC Endpoint로 트래픽 자체를 줄이는 게 효과적이다.

**케이스 4: 같은 VPC 내 SG가 너무 많아 관리 불가.**
서비스가 늘어나면 SG도 늘어나고, 누가 어떤 SG에서 어디로 가는지 추적이 어려워진다. SG 이름 규칙을 정해두고(`<service>-<tier>-sg` 같은 식), SG 간 참조를 Reachability Analyzer로 정기 점검한다.

```bash
# SG A에서 SG B로 도달 가능한지 확인
aws ec2 create-network-insights-path \
  --source <source-sg-instance-id> \
  --destination <dest-sg-instance-id> \
  --protocol tcp \
  --destination-port 443
```

**케이스 5: Endpoint Policy가 비어 있어서 다른 계정 S3에 접근 가능.**
S3 Gateway Endpoint를 만들고 정책을 따로 안 주면 기본 정책이 "허용 all"이다. 사내 데이터를 Endpoint를 통해 외부 계정 버킷으로 옮길 수 있다. 보안이 중요한 환경에서는 Endpoint Policy로 자기 계정 또는 화이트리스트한 계정만 허용하도록 제한한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        }
      }
    }
  ]
}
```

`aws:ResourceAccount` 조건은 대상 리소스가 자기 계정 소유일 때만 허용한다. 이 한 줄로 데이터 유출 경로를 크게 줄인다.

## 정리

Public/Private Subnet의 본질은 라우팅이다. 이름이나 콘솔 옵션이 아니라 라우팅 테이블의 default route가 IGW를 가리키는지 NAT GW를 가리키는지가 결정한다. 이걸 이해하면 "Public Subnet인데 인터넷이 안 된다" 류의 사고를 안 만든다.

NAT Gateway는 AZ별로 두고, 라우팅 테이블도 AZ별로 분리한다. 포트 한계(목적지당 55,000), idle timeout(350초), Cross-AZ 비용을 알고 있어야 한다. AWS 서비스 호출은 VPC Endpoint로 우회해서 NAT GW 비용과 부하를 줄인다.

SG와 NACL은 역할이 다르다. SG는 인스턴스 단위 stateful 화이트리스트, NACL은 서브넷 단위 stateless 정책(DENY 가능)이다. 두 가지를 동시에 강하게 쓰면 ephemeral port 누락으로 사고가 잦으니, SG로 세밀하게, NACL은 보수적인 거친 정책만 운영하는 게 안전하다.

Bastion은 더 이상 표준이 아니다. SSM Session Manager가 IAM 기반 인증, 자동 로깅, 22번 포트 미노출 등 모든 면에서 우수하다. 기존 SSH 도구 호환이 필요하면 EC2 Instance Connect Endpoint를 함께 둔다.

3-Tier 격리는 서브넷 분리 + SG 체인 + Endpoint + Flow Logs 검증의 조합으로 완성된다. 설계만 잘하는 게 아니라 운영 중에도 격리가 유지되는지 정기적으로 점검해야 한다.

## 참고

- AWS VPC User Guide: https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- NAT Gateway 한계와 트러블슈팅: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- VPC Endpoint 종류와 가격: https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- Systems Manager Session Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- EC2 Instance Connect Endpoint: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-using-eice.html
- VPC Flow Logs: https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
