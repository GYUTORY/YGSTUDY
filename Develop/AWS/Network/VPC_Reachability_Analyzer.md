---
title: VPC Reachability Analyzer
tags: [aws, vpc, reachability-analyzer, network, troubleshooting, security-groups, nacl, route-table, eni]
updated: 2026-07-03
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

CLI 워크플로우는 세 단계다. 경로를 만들고(`create-network-insights-path`), 분석을 실행하고(`start-network-insights-analysis`), 결과를 읽는다(`describe-network-insights-analyses`). 분석은 비동기라 실행 직후 바로 결과가 나오지 않는다. 상태가 `running`에서 `succeeded`로 바뀔 때까지 폴링해야 한다.

```bash
# 1) 경로 생성: EC2 인스턴스 -> RDS의 ENI, 5432 포트
PATH_ID=$(aws ec2 create-network-insights-path \
  --source i-0abc1234def567890 \
  --destination eni-0def4567abc890123 \
  --destination-port 5432 \
  --protocol tcp \
  --tag-specifications 'ResourceType=network-insights-path,Tags=[{Key=Name,Value=ec2-to-rds}]' \
  --query 'NetworkInsightsPath.NetworkInsightsPathId' --output text)
echo "$PATH_ID"   # 예: nip-0123456789abcdef0

# 2) 분석 실행 -> NetworkInsightsAnalysisId를 받는다
ANALYSIS_ID=$(aws ec2 start-network-insights-analysis \
  --network-insights-path-id "$PATH_ID" \
  --query 'NetworkInsightsAnalysis.NetworkInsightsAnalysisId' --output text)
echo "$ANALYSIS_ID" # 예: nia-0123456789abcdef0

# 3) 상태가 succeeded가 될 때까지 대기
aws ec2 wait network-insights-analysis-available \
  --network-insights-analysis-ids "$ANALYSIS_ID"

# 4) 결과 조회 - 도달 여부만 먼저 본다
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids "$ANALYSIS_ID" \
  --query 'NetworkInsightsAnalyses[0].NetworkPathFound'
```

`aws ec2 wait network-insights-analysis-available`가 없는 CLI 버전이면 `describe`를 반복 호출하면서 `Status` 필드가 `running`이 아닌지 직접 확인한다. 분석은 보통 몇 초에서 십몇 초 걸린다.

소스에 포트를 지정할 수도 있다(`--source-port`). 대부분은 목적지 포트만 지정하지만, 특정 소스 포트에서 나가는 트래픽만 따져야 하는 드문 경우에 쓴다. `--filter-at-source`, `--filter-at-destination`로 특정 IP나 포트 범위로 경로를 좁히는 옵션도 있는데, 관리형 서비스 뒤에 여러 IP가 붙은 상황에서 특정 IP만 보고 싶을 때 유용하다.

목적지를 ENI로 지정하는 점에 주의한다. RDS, ELB, ElastiCache 같은 관리형 서비스는 인스턴스 ID가 없고 ENI로 노출된다. RDS라면 해당 인스턴스의 서브넷에 붙은 ENI를 찾아서 그 ID를 목적지로 넣어야 한다. RDS 콘솔의 "Connectivity & security" 탭이나 `aws rds describe-db-instances`에서 서브넷 그룹을 확인하고, 그 서브넷의 ENI를 `aws ec2 describe-network-interfaces`로 찾는다. Multi-AZ RDS는 대기 인스턴스에도 ENI가 따로 있어서, 페일오버를 고려하면 양쪽 ENI를 각각 경로로 만들어 둬야 한 쪽만 열려 있는 상황을 잡는다.

경로는 한 번 만들면 재사용된다. 설정을 바꾼 뒤 다시 `start-network-insights-analysis`만 돌리면 그 시점 상태로 재분석한다. 보안 그룹 규칙 하나 고치고 다시 돌려서 Reachable로 바뀌는지 확인하는 식으로 쓴다.

## 분석 결과 해석

결과의 최상위 필드는 `NetworkPathFound`다. `true`면 도달 가능, `false`면 막혀 있다.

막혀 있을 때는 `ExplanationCode`와 `Explanations` 배열을 본다. 여기에 어느 컴포넌트에서 왜 끊겼는지가 들어 있다. 자주 보는 코드들:

- `ENI_SG_RULES_MISMATCH` — 보안 그룹 규칙이 트래픽을 허용하지 않음
- `NETWORK_ACL_RULES_MISMATCH` — NACL이 막음
- `NO_ROUTE_TO_DESTINATION` — 라우트 테이블에 목적지로 가는 경로 없음
- `ROUTE_BLACKHOLE` — 라우트는 있는데 대상(NAT/IGW/ENI)이 죽어서 블랙홀
- `MISSING_INTERNET_GATEWAY` — 인터넷으로 나가야 하는데 IGW가 없음

도달 가능할 때는 `ForwardPathComponents`에 출발지부터 목적지까지 거치는 컴포넌트가 순서대로 나온다. ENI → 보안 그룹 → 서브넷 라우트 → IGW → ... 식으로 홉을 따라간다. 트래픽이 의도한 경로(예: NAT Gateway를 거쳐서)로 흐르는지, 아니면 엉뚱한 게이트웨이로 빠지는지를 여기서 확인한다.

## 홉별 경로 출력 읽기

`ForwardPathComponents`는 배열이고, 원소 하나가 홉 하나다. 각 원소에는 `SequenceNumber`(몇 번째 홉인지), `Component`(그 홉의 리소스 ID와 타입), 그리고 그 홉에서 트래픽에 무슨 일이 일어났는지를 설명하는 필드들이 붙는다. 홉마다 나오는 주요 필드는 이렇게 읽는다.

- `SequenceNumber` — 1부터 시작하는 홉 순서. 어디까지 갔다가 멈췄는지를 이 숫자로 센다.
- `Component` — 이 홉의 리소스. `{"Id": "eni-...", "Arn": "..."}` 형태. ENI, 서브넷, 라우트 테이블, IGW, NAT Gateway, TGW attachment 등이 여기 찍힌다.
- `SecurityGroupRule` / `AclRule` — 이 홉이 보안 그룹이나 NACL이면, 트래픽을 통과시킨 규칙이 그대로 나온다. 포트 범위, 프로토콜, CIDR 또는 참조 SG가 찍혀서 "어떤 규칙 때문에 통과했는지"를 확인할 수 있다.
- `RouteTableRoute` — 이 홉이 라우팅 결정이면, 매칭된 라우트(목적지 CIDR과 타깃)가 나온다. `0.0.0.0/0 → nat-...`처럼 실제로 어느 라우트를 탔는지 보인다.
- `Destination` / `OutboundHeader` / `InboundHeader` — 홉을 지나면서 패킷 헤더(소스/목적지 IP, 포트)가 어떻게 해석되는지. NAT를 지나면 소스 IP가 바뀌는 게 여기서 보인다.

막혔을 때는 `ForwardPathComponents`가 끊긴 홉까지만 나오고, 그 마지막 홉이 문제 지점이다. 예를 들어 3번 홉(RDS 보안 그룹)에서 멈추고 최상위 `Explanations`에 `ENI_SG_RULES_MISMATCH`가 있으면, 1~2번 홉(소스 ENI, 라우팅)까지는 정상이고 3번에서 보안 그룹이 막았다는 뜻이다. `Explanations` 배열의 각 원소에는 문제가 된 컴포넌트(`Component`), 관련 보안 그룹/NACL/라우트 테이블 ID, 그리고 `ExplanationCode`가 들어 있어서, 이 조합을 보고 정확히 어떤 리소스의 어떤 설정을 고쳐야 하는지 짚는다.

CLI로 홉만 빠르게 훑을 때 쓰는 쿼리:

```bash
# 통과한 각 홉의 순서, 리소스 ID, 타입만 뽑기
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids "$ANALYSIS_ID" \
  --query 'NetworkInsightsAnalyses[0].ForwardPathComponents[].{Seq:SequenceNumber, Id:Component.Id}' \
  --output table

# 막힌 이유(Explanations)만 뽑기
aws ec2 describe-network-insights-analyses \
  --network-insights-analysis-ids "$ANALYSIS_ID" \
  --query 'NetworkInsightsAnalyses[0].Explanations[].{Code:ExplanationCode, Component:Component.Id}' \
  --output table
```

콘솔에서는 이 경로가 시각적 다이어그램으로 그려진다. 끊긴 지점에 빨간 표시가 뜨고, 그 컴포넌트를 클릭하면 어떤 규칙이 문제인지 보여준다. 홉이 대여섯 개 이하로 짧으면 콘솔 다이어그램이 빠르고, 홉이 길거나 여러 경로를 스크립트로 반복 검사할 때는 위처럼 JMESPath 쿼리로 뽑는 게 낫다.

## Forward 경로와 Return 경로의 비대칭

Reachability Analyzer는 `ForwardPathComponents`(가는 길)와 `ReturnPathComponents`(돌아오는 길)를 따로 계산한다. 이 둘을 나눠서 보는 게 중요하다. TCP는 핸드셰이크부터 양방향이 필요해서, 가는 길만 뚫려도 응답이 못 돌아오면 실제 연결은 안 된다.

비대칭이 문제가 되는 대표 케이스:

- 서브넷 A는 라우트 테이블에 목적지로 가는 라우트가 있는데, 돌아올 서브넷 B의 라우트 테이블에는 A로 오는 라우트가 없다. `ForwardPathComponents`는 끝까지 가고 `ReturnPathComponents`가 중간에 끊긴다. Peering이나 TGW로 연결한 뒤 한쪽 라우트만 넣은 경우가 전형적이다.
- 비대칭 라우팅(asymmetric routing). 가는 트래픽은 NAT Gateway를 타고, 돌아오는 트래픽은 다른 게이트웨이나 다른 NAT를 타도록 라우트가 갈려 있으면, NACL이 stateless라서 리턴 경로에서 막힌다. 두 경로의 홉을 나란히 놓고 게이트웨이가 다른지 확인한다.

그래서 `NetworkPathFound: true`만 보고 끝내지 말고, `ReturnPathComponents`도 끝까지 갔는지를 같이 본다. 콘솔에서는 forward/return을 탭이나 방향 토글로 나눠 보여준다.

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

## Transit Gateway 경유 경로의 분석 한계

TGW로 여러 VPC를 붙인 환경에서 Analyzer를 돌리면 몇 가지 걸리는 지점이 있다.

TGW 라우트 테이블은 VPC 라우트 테이블과 별개다. Analyzer는 TGW attachment와 TGW 라우트 테이블 연결/전파(association/propagation)까지 본다. 그래서 "VPC 라우트 테이블에 TGW로 가는 라우트는 넣었는데 TGW 라우트 테이블에서 목적지 VPC로 가는 라우트가 없다" 같은 경우, TGW 홉에서 `NO_ROUTE_TO_DESTINATION` 계열로 멈춘다. 어느 라우트 테이블이 문제인지(VPC 쪽인지 TGW 쪽인지) 홉의 `Component` ID를 보고 가른다.

한계는 크로스 리전과 크로스 계정이다. TGW peering으로 다른 리전의 TGW에 붙인 경로는 리전 경계를 넘어가는 부분을 Analyzer가 끝까지 따라가지 못한다. 분석은 경로가 시작된 리전 안에서만 완결되고, 상대 리전의 라우트 테이블·보안 그룹은 그 리전에서 따로 경로를 만들어 봐야 한다. 계정이 다르면 목적지 리소스 ID를 조회할 권한 문제로 경로 생성 단계부터 막히는 경우도 있다.

TGW 어플라이언스 모드(appliance mode)를 켜서 방화벽 어플라이언스로 트래픽을 흘리는 구조도 정적 분석으로는 검증 범위가 좁다. Analyzer는 라우팅과 SG/NACL까지만 보고, 어플라이언스 안에서 트래픽을 실제로 통과시키는지(방화벽 정책)는 검사하지 못한다. TGW를 낀 경로가 Reachable로 나와도 그건 AWS 네트워크 계층까지의 도달성이고, 중간 어플라이언스의 정책은 별도로 확인해야 한다. TGW 자체 구성은 [Transit Gateway](Transit_Gateway.md)를 본다.

## Reachable인데 실제 연결이 안 될 때

Analyzer가 `NetworkPathFound: true`인데도 애플리케이션에서 붙지 못하는 경우가 있다. 정적 분석의 범위 밖에서 막히는 것이라 원인을 나눠서 봐야 한다.

가장 흔한 건 대상 쪽 문제다. 앞에서 말한 OS 방화벽(iptables, security-enhanced Linux, Windows 방화벽), 애플리케이션이 그 포트를 LISTEN 안 하는 상태, 대상 서비스 자체의 장애다. 대상에 SSH로 들어가 `ss -tlnp | grep :5432`로 포트가 떠 있는지부터 본다.

정적 분석의 특성 때문에 놓치는 두 가지가 특히 헷갈린다.

첫째, 보안 그룹은 stateful, NACL은 stateless라는 차이다. Analyzer는 보안 그룹의 상태 추적(반환 트래픽 자동 허용)을 반영해서 판정한다. 그래서 보안 그룹만 있으면 인바운드만 열어도 응답은 자동으로 나가는 걸로 계산해 Reachable을 준다. 문제는 NACL이다. NACL은 stateless라서 반환 트래픽을 별도 규칙으로 열어야 한다. 인바운드로 5432를 받았으면, 응답이 나갈 때 아웃바운드 NACL에서 소스가 요청했던 ephemeral 포트로 나가는 걸 허용해야 한다. Analyzer는 이 NACL 반환 규칙까지 계산에 넣으므로, NACL 반환이 막혀 있으면 대개 Not reachable로 잡아준다. 그런데도 Reachable로 나왔는데 안 붙는다면, NACL이 아니라 그 아래(OS·앱) 계층을 의심하는 게 맞다.

둘째, ephemeral 포트 범위다. 클라이언트가 서버로 붙을 때 목적지 포트는 고정(5432)이지만 소스 포트는 OS가 ephemeral 범위(리눅스 기본 32768–60999, 일부 환경 1024–65535)에서 임의로 잡는다. 응답 패킷은 이 ephemeral 포트를 목적지로 삼아 돌아온다. NACL로 인바운드/아웃바운드를 좁게 잠근 서브넷에서는 이 반환용 ephemeral 포트 범위를 아웃바운드(서버 쪽)와 인바운드(클라이언트 쪽)에 열어줘야 한다. 범위를 잘못 잡으면(예: 32768–61000만 열었는데 클라이언트가 그 밖의 포트를 쓰는 OS) 일부 연결만 간헐적으로 실패한다. Analyzer의 경로 지정에서 목적지 포트만 넣고 소스 포트를 비워두면 Analyzer는 반환 경로의 ephemeral을 표준 범위로 가정해서 본다. 실제 OS의 ephemeral 범위가 그와 다르면, Analyzer는 Reachable이라는데 특정 연결만 실패하는 상황이 생긴다. `cat /proc/sys/net/ipv4/ip_local_port_range`로 실제 범위를 확인하고 NACL 규칙과 맞는지 대조한다.

정리하면, Reachable인데 안 붙을 때 확인 순서는 이렇다. 대상 포트 LISTEN 여부 → OS 방화벽 → (NACL 쓰는 서브넷이면) ephemeral 반환 포트 범위 → 대상 서비스 자체 상태. 보안 그룹만 쓰는 서브넷이면 stateful이라 반환 트래픽은 신경 쓸 필요가 없고, 대상 계층부터 본다. 보안 그룹과 NACL의 stateful/stateless 차이는 [Security Groups vs NACLs](Security_Groups_vs_NACLs.md)에 자세히 있다.

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