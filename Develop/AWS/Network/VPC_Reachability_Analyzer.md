---
title: VPC Reachability Analyzer
tags: [aws, vpc, reachability-analyzer, network, troubleshooting, security-groups, nacl, route-table, eni]
updated: 2026-06-27
---

# VPC Reachability Analyzer

## 개요

Reachability Analyzer는 VPC 안의 두 지점 사이에 트래픽이 흐를 수 있는지를 패킷을 한 번도 보내지 않고 판정하는 정적 분석 도구다. 출발지와 목적지를 지정하면 그 경로에 걸린 보안 그룹, NACL, 라우트 테이블, ENI 설정을 전부 읽어서 "통신 가능(Reachable)" 또는 "불가(Not reachable)"를 알려준다. 막혀 있으면 어느 컴포넌트의 어떤 규칙에서 끊겼는지까지 짚어준다.

운영하다 보면 "EC2에서 RDS로 붙는데 connection timeout이 난다", "Lambda를 VPC에 넣었더니 외부 API 호출이 안 된다" 같은 일이 주기적으로 생긴다. 보통은 보안 그룹 인바운드를 확인하고, NACL을 보고, 라우트 테이블을 보고, 서브넷이 맞는지 보면서 한참을 헤맨다. 이런 작업을 손으로 하면 컴포넌트 하나를 빼먹기 쉽다. Reachability Analyzer는 그 경로 전체를 한 번에 훑어서 끊긴 지점을 찍어준다.

핵심은 정적 분석이다. 실제로 ping을 쏘거나 TCP 핸드셰이크를 시도하지 않는다. AWS가 보유한 설정 정보(보안 그룹 규칙, NACL 엔트리, 라우트, ENI 상태)만 가지고 그래프를 그려서 도달 가능성을 계산한다. 그래서 대상 인스턴스의 OS 방화벽(iptables, Windows 방화벽), 애플리케이션이 해당 포트를 실제로 LISTEN 하는지, RDS가 살아 있는지 같은 건 검사하지 못한다. 이 한계를 모르고 "Analyzer가 Reachable이라는데 왜 안 붙냐"고 하는 경우가 종종 있다.

## 무엇을 검사하고 무엇을 못 하나

검사하는 것:

- 보안 그룹 인바운드/아웃바운드 규칙
- 네트워크 ACL(NACL) 인바운드/아웃바운드 규칙
- 라우트 테이블 (서브넷 연결, 라우트 우선순위, 블랙홀 라우트)
- ENI 존재 여부와 연결 상태
- IGW, NAT Gateway, Transit Gateway, VPC Peering, VPC Endpoint 같은 게이트웨이 경로
- 출발지/목적지가 같은 VPC인지, Peering이나 TGW로 연결된 다른 VPC인지

검사하지 못하는 것:

- 인스턴스 내부 OS 방화벽 (iptables, firewalld, Windows Defender Firewall)
- 애플리케이션이 실제로 포트를 LISTEN 하는지
- 대상 서비스(RDS, ElastiCache 등)의 실제 가용성
- DNS 해석 (Reachability Analyzer는 IP/리소스 ID 기반이지 도메인 기반이 아니다)
- 동적인 상태 (Connection tracking, 세션 만료 등)

그래서 Analyzer 결과가 Reachable인데 통신이 안 되면, 그다음은 OS 방화벽과 애플리케이션 LISTEN 상태를 봐야 한다. `ss -tlnp`나 `netstat`으로 포트가 떠 있는지 확인하는 단계로 넘어가는 식이다.

## 경로 생성

경로(Network Path)는 출발지(Source)와 목적지(Destination)를 묶은 분석 단위다. 콘솔에서는 VPC > Reachability Analyzer 메뉴에서 만든다. 지정할 수 있는 리소스 타입은 다음과 같다.

- Source: Instance, Network Interface(ENI), Internet Gateway, VPC Endpoint, VPN Gateway, Transit Gateway, VPC Peering Connection 등
- Destination: 위와 동일한 타입들

프로토콜은 TCP 또는 UDP를 고르고, 목적지 포트를 지정할 수 있다. 포트를 지정하면 그 포트에 대한 보안 그룹/NACL 규칙까지 정확히 따져준다. 포트를 비우면 프로토콜 레벨까지만 본다. RDS 디버깅이면 5432(PostgreSQL)나 3306(MySQL)을 반드시 넣는 게 정확하다.

CLI로 경로를 만들고 바로 분석까지 돌리는 예시:

```bash
# 경로 생성: EC2 인스턴스 -> RDS의 ENI, 5432 포트
aws ec2 create-network-insights-path \
  --source i-0abc1234def567890 \
  --destination eni-0def4567abc890123 \
  --destination-port 5432 \
  --protocol tcp \
  --tag-specifications 'ResourceType=network-insights-path,Tags=[{Key=Name,Value=ec2-to-rds}]'

# 출력에서 NetworkInsightsPathId를 받는다 (예: nip-0123456789abcdef0)

# 분석 실행
aws ec2 start-network-insights-analysis \
  --network-insights-path-id nip-0123456789abcdef0

# 분석 결과 조회 (NetworkInsightsAnalysisId로)
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids nia-0123456789abcdef0
```

목적지를 ENI로 지정하는 점에 주의한다. RDS, ELB, ElastiCache 같은 관리형 서비스는 인스턴스 ID가 없고 ENI로 노출된다. RDS라면 해당 인스턴스의 서브넷에 붙은 ENI를 찾아서 그 ID를 목적지로 넣어야 한다. RDS 콘솔의 "Connectivity & security" 탭이나 `aws rds describe-db-instances`에서 서브넷 그룹을 확인하고, 그 서브넷의 ENI를 `aws ec2 describe-network-interfaces`로 찾는다.

경로는 한 번 만들면 재사용된다. 설정을 바꾼 뒤 다시 `start-network-insights-analysis`만 돌리면 그 시점 상태로 재분석한다. 보안 그룹 규칙 하나 고치고 다시 돌려서 Reachable로 바뀌는지 확인하는 식으로 쓴다.

## 분석 결과 해석

결과의 최상위 필드는 `NetworkPathFound`다. `true`면 도달 가능, `false`면 막혀 있다.

막혀 있을 때는 `ExplanationCode`와 `Explanations` 배열을 본다. 여기에 어느 컴포넌트에서 왜 끊겼는지가 들어 있다. 자주 보는 코드들:

- `ENI_SG_RULES_MISMATCH` — 보안 그룹 규칙이 트래픽을 허용하지 않음
- `NETWORK_ACL_RULES_MISMATCH` — NACL이 막음
- `NO_ROUTE_TO_DESTINATION` — 라우트 테이블에 목적지로 가는 경로 없음
- `ROUTE_BLACKHOLE` — 라우트는 있는데 대상(NAT/IGW/ENI)이 죽어서 블랙홀
- `MISSING_INTERNET_GATEWAY` — 인터넷으로 나가야 하는데 IGW가 없음

도달 가능할 때는 `ForwardPathComponents`에 출발지부터 목적지까지 거치는 컴포넌트가 순서대로 나온다. ENI → 보안 그룹 → 서브넷 라우트 → IGW → ... 식으로 홉을 따라간다. 트래픽이 의도한 경로(예: NAT Gateway를 거쳐서)로 흐르는지, 아니면 엉뚱한 게이트웨이로 빠지는지를 여기서 확인한다. 비대칭 라우팅이 의심될 때 `ReturnPathComponents`(돌아오는 경로)까지 같이 보면 인바운드는 되는데 응답이 못 돌아오는 케이스를 잡을 수 있다.

콘솔에서는 이 경로가 시각적 다이어그램으로 그려진다. 끊긴 지점에 빨간 표시가 뜨고, 그 컴포넌트를 클릭하면 어떤 규칙이 문제인지 보여준다. CLI 결과의 JSON을 읽는 것보다 콘솔 다이어그램이 디버깅엔 빠르다.

## 실제 디버깅 시나리오

### 시나리오 1: EC2에서 RDS 연결 timeout

애플리케이션 서버에서 RDS로 붙는데 timeout이 난다. 흔한 원인은 RDS 보안 그룹이 EC2 보안 그룹을 인바운드로 안 받는 경우다. Analyzer를 EC2 인스턴스 → RDS ENI, 5432로 돌린다.

결과가 `ENI_SG_RULES_MISMATCH`로 나오면 보안 그룹 문제다. RDS 보안 그룹 인바운드에 EC2 보안 그룹(소스를 SG ID로) 또는 EC2 서브넷 CIDR을 5432로 허용했는지 확인한다. 이 케이스의 자세한 보안 그룹/NACL 동작 차이는 [Security Groups vs NACLs](Security_Groups_vs_NACLs.md)를 본다.

여기서 Analyzer가 Reachable이라고 나오는데도 timeout이면, 보안 그룹은 정상이고 RDS 자체나 OS 레벨 문제다. RDS가 다른 가용영역으로 페일오버됐거나, 파라미터 그룹/Max connection 한도에 걸렸거나 하는 식이다. Analyzer는 네트워크 경로까지만 보장한다는 걸 기억한다.

### 시나리오 2: 프라이빗 서브넷 인스턴스가 외부로 못 나감

프라이빗 서브넷의 EC2가 외부 API(예: 패키지 다운로드)를 못 받는다. Analyzer를 EC2 인스턴스 → Internet Gateway로 돌리거나, 외부 IP를 목적지로 지정한다.

- `NO_ROUTE_TO_DESTINATION` 또는 `MISSING_NAT_GATEWAY` 류가 나오면 라우트 문제다. 프라이빗 서브넷 라우트 테이블에 `0.0.0.0/0 → NAT Gateway`가 있는지 확인한다.
- `ROUTE_BLACKHOLE`가 나���면 라우트는 있는데 NAT Gateway가 삭제됐거나 다른 서브넷으로 잘못 연결된 상태다. NAT Gateway를 지웠다가 다시 만들면서 ID가 바뀌었는데 라우트 테이블을 안 고친 경우가 대표적이다.

라우트 우선순위와 블랙홀에 대한 상세는 [Route Table](Route_Table.md)을 참고한다. 프라이빗 서브넷이 NAT를 거쳐 나가는 구조 자체가 헷갈리면 [Private Subnet vs Public Subnet](Private_Subnet__vs__Public_Subnet.md)을 본다.

### 시나리오 3: VPC Peering 너머의 인스턴스에 안 붙음

A VPC의 인스턴스가 Peering으로 연결된 B VPC의 인스턴스에 못 붙는다. Peering은 양쪽 라우트 테이블과 양쪽 보안 그룹을 모두 맞춰야 해서 빠뜨리기 쉽다. Analyzer를 A의 인스턴스 → B의 인스턴스 ENI로 돌린다.

- `NO_ROUTE_TO_DESTINATION`이 A쪽 컴포넌트에서 나오면 A 라우트 테이블에 B의 CIDR → Peering Connection 라우트가 없다.
- `ForwardPathComponents`는 끝까지 갔는데 `ReturnPathComponents`에서 끊기면, B쪽 라우트 테이블에 A로 돌아오는 라우트가 없는 거다. 인바운드만 뚫고 리턴 경로를 빠뜨린 전형적인 케이스다.
- 보안 그룹에서 끊기면, Peering 너머 보안 그룹은 상대 SG ID로 참조가 안 되고(같은 VPC가 아니므로) CIDR로 열어야 한다는 점을 놓친 경우가 많다.

Peering 라우팅 구성은 [VPC Peering](VPC_Peering.md)에서 다룬다. Analyzer는 양방향을 한 번에 보여줘서 어느 쪽 VPC 설정이 빠졌는지를 빠르게 가른다.

### 시나리오 4: ENI가 사라진 경우

가끔 `ROUTE_BLACKHOLE`나 ENI 관련 코드가 뜨는데 원인이 라우트가 가리키는 ENI가 삭제된 거다. NAT 인스턴스를 직접 운영하거나, ENI를 라우트 타깃으로 쓰는 구조에서 인스턴스를 교체하면 ENI ID가 바뀐다. 라우트 타깃을 안 고치면 블랙홀이 된다. ENI 자체의 동작은 [Elastic Network Interface](Elastic_Network_Interface.md)를 본다.

## Network Access Analyzer와의 차이

이름이 비슷해서 헷갈리는데 용도가 다르다.

| 구분 | Reachability Analyzer | Network Access Analyzer |
|------|----------------------|------------------------|
| 질문 | "이 A에서 저 B로 갈 수 있나?" | "외부에서 내 DB로 들어올 수 있는 경로가 있나?" |
| 입력 | 출발지 1개 + 목적지 1개 (점대점) | Scope 정의 (조건 기반, 다대다) |
| 용도 | 연결 안 되는 원인 디버깅 | 의도하지 않은 접근 경로 감사 |
| 결과 | Reachable / Not reachable + 경로 | 매칭되는 모든 경로 목록 |

Reachability Analyzer는 점대점이다. "EC2 한 대에서 RDS 한 대로"처럼 구체적인 두 지점을 찍어서 통신 가능 여부를 본다. 디버깅용이다.

Network Access Analyzer는 범위(Scope) 기반이다. "인터넷에서 데이터베이스 서브넷으로 도달 가능한 모든 경로를 찾아라" 같은 조건을 주면, 그 조건에 맞는 경로를 전부 찾아준다. 보안 감사용이다. "프라이빗으로 둬야 할 DB가 어딘가 잘못 뚫려 있나"를 점검할 때 쓴다.

연결이 안 되는 걸 고칠 때는 Reachability Analyzer, 의도치 않게 뚫린 걸 찾을 때는 Network Access Analyzer라고 보면 된다.

## 비용과 운영 시 주의

Reachability Analyzer는 분석 1회 실행당 과금된다(리전별 단가는 변동하므로 콘솔/요금 페이지를 확인한다). 경로를 만들어 두는 것 자체는 과금되지 않고, `start-network-insights-analysis`를 돌릴 때 비용이 붙는다. 그래서 경로를 잔뜩 만들어 두는 건 괜찮지만, CI/CD에서 매 배포마다 수십 개씩 자동 분석을 돌리면 비용이 쌓인다.

분석 결과는 분석 시점의 설정 스냅샷이다. 분석 후에 보안 그룹을 바꿨으면 결과는 더 이상 유효하지 않다. 설정을 고쳤으면 다시 분석을 돌려야 한다. 오래된 분석 결과를 보고 "Reachable이라는데 왜 안 되냐"고 하는 경우가 있는데, 타임스탬프를 먼저 확인한다.

리전과 계정 경계도 본다. Reachability Analyzer는 같은 리전 안에서 동작한다. 크로스 리전 Peering이나 다른 계정 리소스가 끼면 분석 범위가 제한될 수 있어서, 그런 토폴로지는 각 리전/계정에서 따로 봐야 하는 경우가 있다.

마지막으로, Analyzer가 Not reachable이라고 짚어준 컴포넌트만 고치고 끝내지 말고 경로 전체를 본다. 보안 그룹 하나 막혀서 거기서 분석이 멈췄을 뿐, 그 뒤에 NACL이나 라우트에 또 다른 문제가 있을 수 있다. 첫 번째 막힌 지점을 뚫으면 그다음 막힌 지점이 드러난다. 한 번 고치고 다시 분석을 돌려서 Reachable이 될 때까지 반복하는 게 정석이다.