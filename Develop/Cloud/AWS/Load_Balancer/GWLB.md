---
title: Gateway Load Balancer (GWLB) 심화
tags: [aws, load-balancer, cloud]
updated: 2026-07-18
---

# Gateway Load Balancer (GWLB) 심화

GWLB는 ALB, NLB와 성격이 완전히 다르다. 애플리케이션 트래픽을 직접 처리하는 게 아니라, 그 트래픽을 제3의 보안 어플라이언스로 "통과"시키는 투명한 미들맨이다. Palo Alto, Check Point, Fortinet 같은 NGFW나 IDS/IPS 장비를 AWS 환경에 끼워 넣을 때 쓴다.

왜 GWLB가 필요한지부터 보자. 온프레미스에서 방화벽을 거쳐 가던 트래픽을 AWS로 옮기면, 그 방화벽 계층이 사라진다. Security Group과 NACL로 어느 정도 커버하지만, 패킷 내용을 DPI(Deep Packet Inspection)로 보거나 SSL을 복호화해서 내부 위협을 탐지하는 수준은 못 된다. 규제 컴플라이언스가 엄격하거나 금융권에서 의무적으로 네트워크 보안 장비를 써야 한다면 GWLB 위에 얹어야 한다.

## GENEVE 프로토콜 — 패킷이 어떻게 어플라이언스를 통과하는가

GWLB의 핵심은 GENEVE(Generic Network Virtualization Encapsulation) 프로토콜이다. RFC 8926에 정의된 UDP 기반 터널링 프로토콜인데, GWLB는 이걸로 원본 패킷 전체를 감싸서 보안 어플라이언스에 전달한다.

동작 순서는 이렇다. 클라이언트 패킷이 GWLB에 도착하면, GWLB는 그 패킷을 GENEVE 헤더로 캡슐화해서 어플라이언스 타겟 그룹으로 보낸다. GENEVE 헤더에는 원본 패킷을 식별하는 메타데이터가 담기는데, 대표적으로 VNI(Virtual Network Identifier)와 플로우 쿠키다. 어플라이언스는 GENEVE를 벗겨내고 원본 패킷을 분석한 뒤, 허용이면 다시 GENEVE로 싸서 GWLB에 돌려준다. GWLB는 원본 패킷을 꺼내서 목적지로 전달한다.

```
Client
  │
  ▼
GWLB (GENEVE 캡슐화)
  │  UDP 6081
  ▼
Security Appliance (GENEVE 해제 → DPI/검사 → GENEVE 재캡슐화)
  │
  ▼
GWLB (GENEVE 해제 → 원본 패킷 복원)
  │
  ▼
Target (EC2, ALB 등)
```

어플라이언스 입장에서 이게 "투명 프록시"다. 원본 패킷의 src/dst IP가 그대로 보이고, 변조 없이 검사만 한다. SNAT을 걸지 않기 때문에 어플라이언스 로그에 실제 클라이언트 IP가 찍힌다.

GENEVE 포트는 6081/UDP다. 어플라이언스 Security Group에서 GWLB로부터 들어오는 6081/UDP를 허용하지 않으면 아무것도 안 된다. 이걸 빠뜨리고 "트래픽이 어플라이언스를 안 거쳐간다"고 헷갈리는 경우가 있다.

VNI는 플로우 식별자로 쓰인다. 같은 5-튜플 플로우는 같은 VNI를 받는다. 어플라이언스가 상태 기반(stateful) 검사를 하려면 VNI로 플로우를 추적할 수 있어야 한다. VNI 범위는 0~16777215(24bit)이고, GWLB가 플로우별로 할당해준다.

## GWLB Endpoint와 VPC 라우팅 테이블 설정

GWLB 자체는 보안 어플라이언스를 소유한 계정(보통 Centralized Security VPC)에 올라간다. 실제 워크로드 VPC는 GWLB Endpoint(GWLBe)를 통해 GWLB에 연결한다. 이 구조가 처음에 낯설다.

GWLBe는 PrivateLink 기반이다. Interface Endpoint처럼 VPC 안에 ENI가 생기는 방식이 아니라, Gateway Endpoint처럼 라우팅 테이블의 next-hop으로 쓴다. 서브넷 단위로 연결하는 게 아니라 특정 CIDR의 next-hop으로 걸어준다.

**Ingress 트래픽 검사 구성 (인터넷 → VPC)**

IGW에 라우팅 테이블을 붙이는 방식이다(Edge Association). IGW Route Table에서 Public Subnet CIDR로 향하는 트래픽을 GWLBe로 보낸다. 인터넷에서 들어오는 패킷이 Public Subnet에 곧장 가지 않고 GWLBe → GWLB → 어플라이언스를 거쳐서 돌아온다.

```
IGW Route Table:
  Destination: 10.0.1.0/24 (Public Subnet CIDR)
  Target: vpce-xxxxxxxx (GWLBe)

  Destination: 10.0.2.0/24 (Private Subnet CIDR, 필요 시)
  Target: vpce-xxxxxxxx (GWLBe)
```

Public Subnet의 라우팅 테이블에서는 반환 트래픽도 GWLBe를 거치게 설정한다.

```
Public Subnet Route Table:
  Destination: 0.0.0.0/0
  Target: vpce-xxxxxxxx (GWLBe)
```

어플라이언스가 패킷을 허용하면 GWLB가 원본 next-hop으로 복원해서 보낸다. 이걸 "bump-in-the-wire" 방식이라고 부른다. 패킷이 GWLB를 두 번 통과하는데(inbound, outbound 각각) 라우팅 테이블 설계가 잘못되면 루프가 생긴다.

**GWLBe 배치 위치**

GWLBe를 어느 서브넷에 두느냐가 중요하다. 전용 "Inspection Subnet"을 따로 만들어서 거기에 배치하는 게 관례다. Public Subnet이나 Private Subnet에 섞어두면 라우팅 루프가 생길 수 있다.

```
VPC 레이아웃:
  ├── Inspection Subnet (10.0.0.0/28)  ← GWLBe 배치
  ├── Public Subnet    (10.0.1.0/24)   ← ALB, NAT GW
  └── Private Subnet   (10.0.2.0/24)   ← 애플리케이션
```

## East-West와 North-South 트래픽 검사 구성

North-South는 인터넷↔VPC 사이 트래픽이고, East-West는 VPC 내부 서브넷 간 또는 VPC 간 트래픽이다. 두 패턴의 라우팅 구성이 상당히 다르다.

**North-South (인터넷 진입 트래픽)**

위에서 설명한 IGW Edge Association 방식이 여기 해당한다. ALB나 NLB를 Public Subnet에 두고 그 앞에 GWLB를 끼우는 게 일반적이다. 인터넷에서 들어오는 패킷이 `IGW → GWLBe → 어플라이언스 → GWLBe → ALB` 순으로 흐른다.

Egress(아웃바운드) 검사도 필요하다면 NAT Gateway 앞에 GWLBe를 끼운다. Private Subnet → GWLBe → 어플라이언스 → GWLBe → NAT GW → IGW 순서가 된다. 이 경우 Private Subnet의 기본 경로를 GWLBe로 잡고, 어플라이언스 통과 후 NAT GW로 향하도록 Inspection Subnet 라우팅 테이블을 설정한다.

**East-West (VPC 간 트래픽, Transit Gateway 경유)**

여러 VPC를 TGW로 엮는 환경에서 많이 쓴다. Centralized Inspection VPC를 TGW에 연결하고, Spoke VPC들의 TGW Route Table에서 inter-VPC 트래픽을 Inspection VPC 쪽으로 보내는 방식이다.

```
TGW Route Table (Spoke VPC 용):
  Destination: 10.1.0.0/16 (다른 Spoke VPC)
  Attachment: Inspection VPC의 TGW Attachment

Inspection VPC 내부 흐름:
  TGW Attachment Subnet
    → GWLBe
    → GWLB
    → 어플라이언스 (검사)
    → GWLB
    → GWLBe
    → TGW Attachment Subnet
    → 목적지 Spoke VPC
```

TGW에서 Appliance Mode를 반드시 활성화해야 한다. 활성화하지 않으면 비대칭 라우팅이 발생한다. A VPC → Inspection VPC → B VPC로 패킷이 가면서, B VPC → Inspection VPC로 돌아오는 경로가 다른 AZ의 TGW 어태치먼트를 타면 어플라이언스가 세션을 맞추지 못한다. Appliance Mode는 동일 어태치먼트로 양방향이 유지되도록 TGW가 고정해준다.

**분산 배포 vs 중앙 집중 배포**

분산 배포는 각 VPC마다 GWLB를 두는 방식이다. 각 워크로드 팀이 독립적으로 보안 장비를 운영하고 싶을 때 쓰지만, 장비 라이선스 비용과 관리 부담이 VPC 수만큼 늘어난다.

중앙 집중 배포는 Inspection VPC 하나에 GWLB와 어플라이언스를 두고, 다른 VPC들이 GWLBe로 붙는 구조다. 라이선스 통합과 운영 단일화가 장점이다. GWLB 자체는 Multi-AZ HA를 지원하니까 GWLB가 병목이 되지는 않는다. 어플라이언스 클러스터를 어떻게 설계하느냐가 핵심이다.

## 보안 어플라이언스 통합 패턴

**Palo Alto Networks VM-Series**

GWLB 타겟 그룹에 Palo Alto VM-Series 인스턴스를 등록한다. VM-Series는 GENEVE를 지원하는 PAN-OS 10.0 이상을 써야 한다. 이전 버전은 VXLAN을 써야 했는데 GWLB는 GENEVE만 지원하므로 버전 확인이 먼저다.

Palo Alto 측에서 GENEVE 터널 인터페이스를 만들고, 그걸 방화벽 정책 처리 경로에 태워야 한다. AWS 마켓플레이스의 Palo Alto CloudFormation 템플릿을 쓰면 대부분 자동으로 잡히지만, 인터페이스 매핑은 직접 확인한다.

헬스체크 포트를 따로 잡아야 한다. GWLB 타겟 그룹 헬스체크는 어플라이언스 관리 포트나 별도 포트로 TCP를 확인한다. Palo Alto는 22(SSH)나 443(관리 웹)을 쓰거나, 커스텀 포트로 HTTP 헬스체크 핸들러를 만들어두는 쪽이 낫다.

**Check Point CloudGuard**

Check Point는 GWLB와 통합하는 Auto Scale 그룹 템플릿을 제공한다. Gateway Security Management Server(SMS)가 중앙에서 정책을 관리하고, Auto Scale로 늘어나는 인스턴스가 SMS에 자동 등록된다.

Check Point의 주의사항은 라이선스 모델이다. BYOL과 PAYG가 있는데, Auto Scale 환경에서는 PAYG가 운영이 간단하지만 시간당 과금이 생각보다 크다. 인스턴스가 스케일 아웃되면 라이선스가 자동으로 붙는데, 스케일 인될 때 반납이 제대로 되는지 확인하지 않으면 과금이 남는다.

**어플라이언스 공통 주의사항**

어플라이언스 인스턴스에서 Source/Dest Check를 반드시 꺼야 한다. AWS 인스턴스는 기본적으로 자신이 src나 dst가 아닌 패킷을 드롭한다. GWLB에서 캡슐화된 패킷이 도착하면 IP가 원본 클라이언트/서버 IP라서 인스턴스가 버린다. Source/Dest Check 비활성화를 빠뜨리면 "GWLB까지는 도달하는데 어플라이언스에서 사라진다"는 증상이 나온다.

## Terraform 예제

Centralized Inspection 패턴 기준이다.

```hcl
# GWLB 생성
resource "aws_lb" "gwlb" {
  name               = "central-gwlb"
  load_balancer_type = "gateway"

  subnet_mapping {
    subnet_id = aws_subnet.inspection_az1.id
  }
  subnet_mapping {
    subnet_id = aws_subnet.inspection_az2.id
  }
}

# 타겟 그룹 — 어플라이언스 인스턴스를 GENEVE로 묶음
resource "aws_lb_target_group" "appliance" {
  name        = "gwlb-appliance-tg"
  port        = 6081
  protocol    = "GENEVE"
  vpc_id      = aws_vpc.inspection.id
  target_type = "instance"

  health_check {
    protocol = "TCP"
    port     = "80"
  }

  # 스케일 인 시 기존 세션 드레이닝
  deregistration_delay = 300
}

# 리스너 — GWLB는 포트/프로토콜 설정 없이 forward만
resource "aws_lb_listener" "gwlb" {
  load_balancer_arn = aws_lb.gwlb.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.appliance.arn
  }
}

# 어플라이언스 인스턴스 타겟 등록
resource "aws_lb_target_group_attachment" "appliance" {
  for_each         = toset(aws_instance.appliance[*].id)
  target_group_arn = aws_lb_target_group.appliance.arn
  target_id        = each.value
}

# Endpoint Service — 다른 VPC에서 GWLBe로 연결할 수 있게
resource "aws_vpc_endpoint_service" "gwlb" {
  acceptance_required        = false
  gateway_load_balancer_arns = [aws_lb.gwlb.arn]

  allowed_principals = [
    "arn:aws:iam::${var.spoke_account_id}:root"
  ]
}

# 워크로드 VPC에 GWLBe 생성
resource "aws_vpc_endpoint" "gwlbe" {
  vpc_id            = aws_vpc.workload.id
  service_name      = aws_vpc_endpoint_service.gwlb.service_name
  vpc_endpoint_type = "GatewayLoadBalancer"
  subnet_ids        = [aws_subnet.inspection_workload.id]
}

# IGW Edge Association — 인터넷 인바운드를 GWLBe 경유로
resource "aws_route_table" "igw_edge" {
  vpc_id = aws_vpc.workload.id
}

resource "aws_route_table_association" "igw_edge" {
  gateway_id     = aws_internet_gateway.workload.id
  route_table_id = aws_route_table.igw_edge.id
}

resource "aws_route" "igw_to_gwlbe" {
  route_table_id         = aws_route_table.igw_edge.id
  destination_cidr_block = var.public_subnet_cidr
  vpc_endpoint_id        = aws_vpc_endpoint.gwlbe.id
}

# Public Subnet 아웃바운드도 GWLBe 경유
resource "aws_route" "public_to_gwlbe" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  vpc_endpoint_id        = aws_vpc_endpoint.gwlbe.id
}

# 어플라이언스 인스턴스 — Source/Dest Check 반드시 끄기
resource "aws_instance" "appliance" {
  count                  = 2
  ami                    = var.appliance_ami
  instance_type          = var.appliance_instance_type
  subnet_id              = element([aws_subnet.appliance_az1.id, aws_subnet.appliance_az2.id], count.index)
  source_dest_check      = false   # 반드시 false

  vpc_security_group_ids = [aws_security_group.appliance.id]
}

# 어플라이언스 Security Group — GENEVE 포트 허용
resource "aws_security_group" "appliance" {
  name   = "appliance-sg"
  vpc_id = aws_vpc.inspection.id

  ingress {
    from_port   = 6081
    to_port     = 6081
    protocol    = "udp"
    cidr_blocks = [aws_vpc.inspection.cidr_block]
  }

  # 헬스체크 포트
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.inspection.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

## 운영 시 주의사항

**비대칭 라우팅**

GWLB는 기본적으로 Cross-Zone Load Balancing이 꺼져 있다. 켜면 비용도 발생하고 비대칭 라우팅도 생긴다. AZ-a로 들어온 요청이 AZ-b의 어플라이언스를 통과하고, 응답이 AZ-a의 어플라이언스로 돌아오면 stateful 어플라이언스가 세션을 못 맞춘다. Cross-Zone은 끈 채로 두고 AZ별로 어플라이언스를 고루 배치하는 게 낫다. TGW 구성이라면 Appliance Mode를 켜는 것으로 비대칭을 막는다.

**어플라이언스 스케일 인 타이밍**

타겟 그룹에서 인스턴스를 해제하면 드레이닝이 시작된다. stateful 어플라이언스라 세션 테이블이 있으므로 Deregistration Delay를 충분히 줘야 한다. 기본값 300초는 대부분의 경우 적당하지만, long-lived TCP 세션이 많은 환경이라면 늘려야 한다. Auto Scaling 그룹으로 어플라이언스를 관리한다면 Lifecycle Hook을 걸어서 드레이닝이 끝난 뒤 인스턴스가 종료되도록 설정해야 한다. 이걸 빠뜨리면 드레이닝 중에 인스턴스가 강제 종료되면서 기존 세션이 끊긴다.

**MTU와 GENEVE 오버헤드**

GENEVE 캡슐화가 붙으면 패킷이 커진다. 외부 UDP/IP 헤더와 GENEVE 헤더 합쳐서 최소 50바이트 이상 오버헤드가 생긴다. AWS Jumbo Frame MTU 9001 환경에서도 어플라이언스 인터페이스 MTU를 맞추지 않으면 단편화가 발생한다. 단편화가 일어나면 DPI가 제대로 안 되거나 성능이 급격히 떨어진다. 어플라이언스 인스턴스의 인터페이스 MTU를 8951 이하로 설정하는 게 일반적이다.

**로그에서 IP 혼동**

VPC Flow Log에 찍히는 GWLB 관련 트래픽의 src/dst는 GWLB와 어플라이언스 사이 IP다. 원본 클라이언트 IP를 추적하려면 어플라이언스 자체 로그를 봐야 한다. "Flow Log에서 이상한 IP가 찍힌다"는 증상이 여기서 나온다. 운영팀이 처음에 이걸 모르면 장애 시 원인 추적에 시간을 많이 쓴다.

**어플라이언스 세션 테이블 한계**

NGFW는 세션 테이블을 메모리에 들고 있다. 트래픽이 갑자기 몰리면 인스턴스 타입 대비 세션 수가 한계를 넘는다. 어플라이언스 벤더마다 인스턴스 타입별 세션 수 한계가 다르므로, 예상 동시 세션 수를 계산하고 인스턴스 사이즈를 골라야 한다. 모니터링에서 세션 테이블 사용률을 보지 않으면 "갑자기 연결이 거부된다"는 장애로 이어진다. CloudWatch Custom Metrics로 어플라이언스 세션 수를 뽑거나, 어플라이언스 벤더 콘솔에서 제공하는 메트릭을 활용한다.
