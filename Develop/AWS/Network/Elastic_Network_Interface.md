---
title: ENI(Elastic Network Interface) — VPC 안의 모든 IP는 결국 여기로 모인다
tags:
  - AWS
  - VPC
  - ENI
  - Networking
  - ECS
  - Lambda
updated: 2026-05-20
---

# ENI(Elastic Network Interface)

## 왜 ENI를 따로 알아야 하나

EC2를 만들면 자동으로 IP가 붙는다. RDS를 만들면 엔드포인트 DNS가 IP로 풀린다. NAT 게이트웨이도 IP를 가진다. ALB도 마찬가지다. 이 IP들은 어디서 오는가. 답은 전부 ENI다.

ENI는 VPC 안에서 IP를 가지는 모든 리소스의 실제 네트워크 진입점이다. EC2 콘솔에서 인스턴스를 봤을 때 보이는 "Private IP"는 ENI가 가진 IP일 뿐이다. RDS 엔드포인트가 가리키는 그 IP도, 사실 RDS 서비스가 너의 VPC에 만들어 둔 ENI의 IP다. NAT 게이트웨이를 만들면 AWS 매니지드 영역에 NAT 인스턴스가 떠 있는 게 아니라, 너의 서브넷에 NAT용 ENI가 꽂혀 있는 거다.

이걸 알아야 하는 이유는 IP 고갈, ENI 한계, 서브넷 크기 계산 같은 실무 문제가 전부 ENI 수준에서 발생하기 때문이다. /28 서브넷에 ECS Fargate 태스크 20개를 띄우려고 시도하다가 IP가 모자라 배포가 멈춘 적이 있다면, 그건 ECS의 awsvpc 모드가 태스크당 ENI를 1개씩 잡아서 그렇다.

## ENI가 가지는 것들

ENI 하나에는 다음이 매달려 있다.

- Primary Private IPv4 주소 1개 (변경 불가)
- Secondary Private IPv4 주소 N개 (인스턴스 타입에 따라 한계)
- Elastic IP 1개 (Primary 또는 Secondary에 매핑)
- Public IPv4 (auto-assign 켰을 때, ENI 분리 후 재부착하면 사라짐)
- IPv6 주소 N개
- MAC 주소 (ENI 생성 시 고정, 라이선스 체크에 종종 활용됨)
- Security Group N개 (인스턴스가 아니라 ENI에 붙는다)
- 소스/대상 검사(Source/Dest Check) 플래그
- 설명(Description) 필드 — 이게 누가 만든 ENI인지 추적할 때 결정적이다

EC2 인스턴스의 "보안 그룹"이 사실 인스턴스가 아니라 그 인스턴스의 ENI에 붙어 있다는 점이 처음엔 헷갈린다. 인스턴스에 ENI를 두 개 붙이면 각 ENI마다 별도의 보안 그룹을 가질 수 있다. 한 인스턴스가 DMZ와 내부망에 동시에 발을 걸치는 구성이 가능한 이유다.

## Primary ENI와 Secondary ENI

EC2 인스턴스를 만들면 eth0에 해당하는 Primary ENI가 자동으로 생긴다. 이 Primary ENI는 인스턴스와 운명을 같이한다.

- 인스턴스 종료 시 같이 삭제된다 (delete on termination 기본값 true)
- 인스턴스에서 분리(detach) 불가능
- Primary Private IP 변경 불가

Secondary ENI는 사람이 명시적으로 만들어서 붙이는 ENI다.

- 인스턴스에서 자유롭게 분리/재부착 가능
- 인스턴스 종료해도 ENI는 남길 수 있다 (delete on termination 기본값 false)
- IP가 보존된다 — Floating IP 패턴에 쓴다

전형적인 활용은 이렇다. 라이선스를 MAC 주소나 IP에 묶어둔 레거시 소프트웨어를 EC2에 띄울 때, Secondary ENI를 만들어서 거기에 라이선스용 IP를 올린다. 인스턴스를 교체할 때 Secondary ENI만 뽑아서 새 인스턴스에 꽂으면 IP와 MAC이 그대로 따라간다. 라이선스 재발급 없이 인스턴스 교체가 끝난다.

```bash
# Secondary ENI 만들기
aws ec2 create-network-interface \
  --subnet-id subnet-0a1b2c3d \
  --description "license-floating-eni" \
  --groups sg-0123456789 \
  --private-ip-address 10.0.1.50

# 인스턴스에 부착 (device-index 1번 = eth1)
aws ec2 attach-network-interface \
  --network-interface-id eni-aabbccdd \
  --instance-id i-0123456789 \
  --device-index 1
```

## Secondary IP — ALB target type=ip와 ECS awsvpc의 비밀

ENI 하나는 IP를 여러 개 가질 수 있다. 이걸 Secondary IP라고 한다. ENI에 IP를 추가로 할당하면 그 IP들은 같은 ENI를 통해 흐른다.

이 메커니즘이 두 가지 흔한 패턴의 기반이다.

### ALB target type=ip

ALB 타겟 그룹의 target type을 `instance`가 아니라 `ip`로 만들면, 타겟이 인스턴스 ID가 아닌 IP 주소가 된다. 이때 ALB는 그 IP가 같은 VPC 안의 ENI 어딘가에 있다고 가정하고 라우팅한다. 한 인스턴스에서 여러 컨테이너를 돌리면서 각 컨테이너에 Secondary IP를 부여하면, ALB가 인스턴스가 아니라 컨테이너 단위로 트래픽을 보낼 수 있다.

### ECS awsvpc 네트워크 모드

ECS의 awsvpc 모드는 태스크마다 전용 ENI를 부여한다. 정확히는 태스크의 각 컨테이너가 호스트 ENI의 Secondary IP를 빌려 쓰는 게 아니라, 태스크 단위로 새 ENI를 통째로 받는다. 그래서 태스크마다 보안 그룹을 다르게 줄 수 있고, VPC Flow Logs에 태스크 단위 IP가 그대로 찍힌다.

이게 편한 대신 비용이 있다. /24 서브넷(가용 IP 약 251개)에 ECS Fargate 태스크를 251개까지밖에 못 띄운다. ALB target type=ip로 ECS를 붙이는 구성에서는 서브넷 크기 산정이 처음부터 빠듯하게 잡혀야 한다. 운영 중 스케일 아웃 시점에 "DescribeNetworkInterfaces 응답에 ENI가 안 보임 + 태스크가 PENDING에서 멈춤"이 나오면 90% 확률로 서브넷 IP 고갈이다.

## 인스턴스 타입별 ENI/IP 한계

이게 실무에서 가장 자주 부딪히는 벽이다. ENI 개수와 ENI당 IP 개수가 인스턴스 타입마다 다르다.

| 인스턴스 타입 | 최대 ENI | ENI당 IPv4 | 총 IPv4 |
|---|---|---|---|
| t3.nano | 2 | 2 | 4 |
| t3.micro | 2 | 2 | 4 |
| t3.small | 3 | 4 | 12 |
| t3.medium | 3 | 6 | 18 |
| t3.large | 3 | 12 | 36 |
| t3.xlarge | 4 | 15 | 60 |
| m5.large | 3 | 10 | 30 |
| m5.xlarge | 4 | 15 | 60 |
| m5.2xlarge | 4 | 15 | 60 |
| m5.4xlarge | 8 | 30 | 240 |
| c5.large | 3 | 10 | 30 |
| c5.xlarge | 4 | 15 | 60 |
| c5.4xlarge | 8 | 30 | 240 |

표를 보면 같은 vCPU/메모리 대역인데도 t3 계열이 c5/m5 계열보다 ENI와 IP 한계가 빡빡하다. 비용 줄이려고 t3.small에 ECS EC2 모드로 awsvpc 태스크를 띄우려 하면, 태스크 2개(태스크 ENI 2개) 띄우자마자 한계에 닿는다. ECS는 호스트 자체 ENI 1개도 점유하니까 실제로는 더 빠르게 차오른다.

ECS EC2 모드를 진지하게 운영할 거면 m5/c5 계열 또는 더 큰 인스턴스가 답이다. 아니면 다음에 나올 ENI Trunking을 켠다.

확인은 다음 명령으로 한다.

```bash
aws ec2 describe-instance-types \
  --instance-types t3.medium m5.large c5.large \
  --query 'InstanceTypes[].[InstanceType,NetworkInfo.MaximumNetworkInterfaces,NetworkInfo.Ipv4AddressesPerInterface]' \
  --output table
```

## ENI Trunking으로 ECS 태스크 밀도 늘리기

ENI Trunking은 ECS EC2 런치 타입에서 한 인스턴스에 태스크 ENI를 더 많이 꽂을 수 있게 해주는 기능이다. 일반 모드에서는 awsvpc 태스크 하나가 ENI 한 슬롯을 통째로 먹지만, Trunking을 켜면 트렁크 ENI 1개에 여러 개의 브랜치 ENI를 가상으로 매단다.

m5.large 기준으로 비교하면 이렇다.

- Trunking 비활성: 태스크 ENI 2개 → 태스크 2개 한계 (호스트 ENI 1개 점유)
- Trunking 활성: 브랜치 ENI 10개 → 태스크 10개 한계

활성화는 ECS 계정 설정에서 한다.

```bash
aws ecs put-account-setting \
  --name awsvpcTrunking \
  --value enabled
```

주의할 점이 있다. Trunking 지원 인스턴스 타입이 제한된다. 너모브 새로 만들어진 nitro 기반 인스턴스(c5/m5/r5 이상, t3는 제외)만 지원한다. 그리고 계정 설정을 켠 뒤 새로 띄우는 인스턴스부터 적용된다. 기존에 떠 있던 EC2는 재기동해야 트렁크 ENI가 생긴다.

운영 중에 "왜 Trunking을 켰는데 여전히 태스크가 한계에서 멈추지" 하면 보통 다음 중 하나다.

- 인스턴스가 Trunking 활성화 이전에 떠 있던 것
- 인스턴스 타입이 미지원 (t3 계열에서 자주 겪는다)
- ECS 에이전트 버전이 낮음

## Lambda-in-VPC와 Hyperplane ENI

Lambda를 VPC에 붙이는 구성을 한 번이라도 운영해본 사람은 옛날의 콜드 스타트 악몽을 기억할 거다. 2019년 이전에는 Lambda가 VPC에 붙을 때 호출 시점에 ENI를 만들고 거기 attach하는 구조였다. ENI 생성 자체가 수십 초가 걸리는 작업이라 첫 호출이 10초가 넘어가는 게 흔했다.

지금은 hyperplane ENI로 바뀌었다. Lambda 함수가 VPC에 처음 붙을 때 AWS 내부에서 공유 ENI(hyperplane)를 함수의 VPC/서브넷/보안 그룹 조합당 하나 만들어둔다. 함수가 호출되면 이 공유 ENI를 통해 트래픽이 흐른다. 함수당 ENI가 아니라 (VPC × 서브넷 × 보안 그룹) 조합당 ENI다.

실무에서 이 변화의 의미는 두 가지다.

- 콜드 스타트가 일반 Lambda 수준으로 회복됐다. ENI 생성을 호출 경로에서 빼냈으니까.
- 같은 VPC/서브넷/SG를 공유하는 Lambda 함수들이 ENI를 공유한다. 함수 100개를 같은 구성으로 띄워도 ENI는 손에 꼽는다.

부작용도 있다. VPC 안에서 Lambda가 호출하는 트래픽이 어떤 ENI에서 오는지 정확히 매칭하기 어려워졌다. VPC Flow Logs에 잡히는 IP가 "이 Lambda 함수의 IP"가 아니라 "이 VPC×서브넷×SG 조합 hyperplane ENI의 IP"여서, 누가 호출한 트래픽인지 함수 단위로 식별이 안 된다. 추적이 필요하면 Lambda 안에서 X-Ray나 컨텍스트 로깅으로 푼다.

확인 방법.

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=AWS Lambda VPC ENI*" \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Description,PrivateIpAddress]' \
  --output table
```

## 매니지드 서비스의 ENI를 description으로 찾기

AWS 매니지드 서비스가 VPC에 만든 ENI는 보통 description 필드에 일관된 문자열이 들어간다. IP 고갈 디버깅이나 "이 ENI 누가 쓰는 거지" 같은 상황에서 결정적인 단서다.

| 서비스 | Description 패턴 |
|---|---|
| RDS | `RDSNetworkInterface` |
| ElastiCache | `ElastiCache <cluster-name>` |
| Lambda | `AWS Lambda VPC ENI-<function>` |
| NAT Gateway | `Interface for NAT Gateway nat-xxxxxxxx` |
| VPC Endpoint (Interface) | `VPC Endpoint Interface vpce-xxxxxxxx` |
| Transit Gateway | `Network interface for Transit Gateway Attachment tgw-attach-xxxxxxxx` |
| ECS Fargate | `arn:aws:ecs:...:task/...` (description이 태스크 ARN을 포함) |
| EFS | `EFS mount target for fs-xxxxxxxx` |
| WorkSpaces | `WorkSpaces` |
| ALB/NLB | `ELB app/<name>` 또는 `ELB net/<name>` |

서브넷 IP가 어디로 새고 있는지 확인할 때 자주 쓰는 쿼리.

```bash
# 특정 서브넷에서 누가 ENI를 점유하고 있는지
aws ec2 describe-network-interfaces \
  --filters "Name=subnet-id,Values=subnet-0a1b2c3d" \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Description,Status,PrivateIpAddress,InterfaceType]' \
  --output table

# description으로 매니지드 서비스 ENI만 추리기
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*NAT Gateway*" \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Description,SubnetId]'
```

InterfaceType 필드도 유용하다. 값은 `interface`, `natGateway`, `efa`, `trunk`, `branch`, `gateway_load_balancer`, `gateway_load_balancer_endpoint`, `vpc_endpoint`, `lambda` 등이 있다. `branch`로 필터링하면 ECS Trunking으로 만들어진 ENI만 따로 볼 수 있다.

## ENI 분리 실패 — 가장 짜증나는 운영 이슈

ENI 작업 중 가장 골치 아픈 경우는 분리(detach)가 안 될 때다. 시나리오는 보통 이렇다. 인스턴스를 종료하려는데 Secondary ENI의 delete-on-termination이 false라 ENI가 남는다. 다른 인스턴스에 붙이려고 detach 시도하면 응답은 성공인데 status가 `detaching`에서 멈춘 채 몇 분이 지나도 `available`로 안 떨어진다.

### 원인

- 인스턴스 OS에서 ENI 디바이스를 잡고 있는 프로세스가 있음
- ENI에 매달린 Elastic IP가 어딘가에서 활성 트래픽을 처리 중
- 인스턴스가 stop 상태가 아니라 running인데 ENI가 부팅 시 자동 설정된 인터페이스라 OS가 놓지 않음
- AWS 백엔드 자체 지연 (드물지만 있음)

### 해결 순서

1. 인스턴스에서 OS 레벨로 인터페이스 내리기

   ```bash
   # 인스턴스 안에서
   sudo ip link set dev eth1 down
   ```

2. 다시 detach 시도

   ```bash
   aws ec2 detach-network-interface \
     --attachment-id eni-attach-xxxxxxxx
   ```

3. 그래도 안 되면 force detach

   ```bash
   aws ec2 detach-network-interface \
     --attachment-id eni-attach-xxxxxxxx \
     --force
   ```

### Force detach의 함정

`--force`를 쓰면 무조건 떨어지긴 한다. 다만 운영 환경에서 함부로 쓰면 안 되는 이유가 있다.

- 인스턴스 OS는 ENI가 사라진 걸 모른다. 그 인터페이스를 통해 통신하던 프로세스는 행이 걸리거나 SIGPIPE를 받는다.
- 인스턴스의 네트워크 스택이 깨질 수 있다. 특히 eth0(Primary ENI)을 force detach 시도하면 AWS가 막지만, eth1 이상의 Secondary ENI를 force detach하면 OS 입장에서는 디바이스가 갑자기 사라진 거라 ifconfig/ip 명령이 한동안 응답하지 않는 경우가 있다.
- 결과적으로 인스턴스 재기동이 필요한 경우가 많다. force detach로 ENI를 빼냈는데 인스턴스 자체가 정상 동작하지 않으면 결국 EC2를 stop/start 해야 한다.

운영 중인 인스턴스에서 force detach는 마지막 수단이다. 보통은 1) OS 안에서 인터페이스를 먼저 내리고 2) detach 시도하는 순서를 지킨다. 정 안 되면 인스턴스를 stop한 뒤 detach한다. stop된 인스턴스의 ENI는 거의 항상 깨끗하게 떨어진다.

### "Network interface is currently in use" 에러

ENI를 삭제하려는데 위 에러가 뜨는 경우가 있다. 십중팔구 매니지드 서비스가 잡고 있다. RDS를 삭제했는데 RDS ENI가 남아 있거나, VPC Endpoint를 지웠는데 ENI는 남는 경우. AWS 측에서 정리하는 데 5~15분 정도 걸리는 게 정상이다. 그래도 안 사라지면 description으로 어떤 서비스인지 확인하고, 해당 서비스 콘솔에서 의존성을 정리해야 한다.

가장 흔한 경우: ALB/NLB를 삭제했는데 ELB ENI가 남는다. 이건 ELB가 비동기로 정리되니까 10분 정도 기다리면 자동으로 사라진다. 안 사라지면 보안 그룹이나 EIP 같은 의존성이 남아 있을 가능성이 높다.

## ENI 상태 머신

ENI의 상태 값은 운영 중 자주 본다.

- `available` — 분리되어 있고 부착 가능한 상태
- `attaching` — 부착 중
- `in-use` — 인스턴스/서비스에 부착된 상태
- `detaching` — 분리 중. 이 상태에서 오래 머물면 위에서 다룬 문제다.

상태 전환 중에는 보안 그룹 변경 같은 일부 작업이 막힌다. CloudFormation/Terraform으로 ENI 관련 변경을 자동화할 때 `detaching` 상태에서 실패하는 경우가 종종 있어서, 재시도 로직을 넣어두는 게 안전하다.

## ENI와 보안 그룹의 미묘한 관계

보안 그룹은 ENI 단위로 붙는다. 한 ENI에 최대 5개의 보안 그룹을 붙일 수 있다(쿼터 상향 가능). 한 인스턴스에 ENI가 2개 있고 각각 다른 SG가 붙으면, 그 인스턴스는 사실상 두 개의 다른 방화벽 규칙을 동시에 가지는 거다.

특이한 케이스 하나. ECS awsvpc 모드에서는 태스크 정의의 networkConfiguration에 보안 그룹을 지정하는데, 이 보안 그룹은 태스크 ENI에 붙는다. 호스트 EC2의 보안 그룹과는 완전히 분리된다. 그래서 호스트 EC2에는 ECS 에이전트가 통신하는 데 필요한 outbound만 열고, 실제 애플리케이션의 inbound는 태스크 ENI 단의 SG에서 제어하는 게 표준 구성이다.

## 정리하면서 — 실무에서 마주치는 ENI 관련 사고

마지막으로 자주 보는 사고 유형을 압축해서 적어둔다.

서브넷 IP 고갈로 ECS 태스크가 PENDING에서 멈춘다. 이건 거의 100% 서브넷 크기 부족이다. `aws ec2 describe-subnets`로 `AvailableIpAddressCount`를 확인한다. 빠른 처방은 다른 서브넷을 ECS 서비스에 추가하는 거고, 근본 처방은 /24 이상으로 서브넷을 다시 자르는 거다.

인스턴스 타입을 t3에서 m5로 바꿨는데 ENI 한계가 늘어난 건지 모르겠다. `describe-instance-types`로 확인한다. 사양표를 외울 필요 없다.

NAT 게이트웨이를 삭제했는데 ENI가 안 사라진다. 보통 10분 안에 정리된다. 그 이상 남아 있으면 NAT 게이트웨이 상태가 `deleting`에서 멈춘 거다. 이때는 CloudFormation/Terraform 스택에서 의존성이 남아 있는 경우가 많다.

Lambda VPC 함수의 IP가 매번 달라 보인다. hyperplane ENI가 여러 개일 수 있다. (VPC × 서브넷 × SG) 조합마다 하나, 그리고 부하가 늘면 같은 조합 내에서도 추가 ENI가 만들어진다. 화이트리스트 기반 외부 호출이 필요하면 NAT 게이트웨이 + EIP로 송신 IP를 고정하는 게 정석이다.

ENI는 보이지 않는 인프라처럼 다뤄지지만, VPC 안에서 IP가 흐르는 모든 길이 ENI에서 시작한다. IP가 모자라거나, 보안 그룹이 의도대로 안 먹거나, 인스턴스가 detach 안 되거나 하는 문제는 결국 ENI 한 칸 한 칸을 들여다봐야 풀린다.
