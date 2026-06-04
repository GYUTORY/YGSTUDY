---
title: BGP — 인터넷을 굴리는 라우팅 프로토콜
tags:
  - Network
  - BGP
  - Routing
  - AS
  - eBGP
  - iBGP
  - RPKI
  - DirectConnect
updated: 2026-06-04
---

# BGP — 인터넷을 굴리는 라우팅 프로토콜

## 들어가며

서버 운영을 5년 하면서 BGP를 직접 만질 일은 사실 드물다. OSPF는 사내 네트워크에서 가끔 마주치지만, BGP는 보통 네트워크 팀이 회선 사업자랑 협의해서 세팅해놓고 끝이다. 그런데 어느 날 갑자기 "특정 리전에서만 응답이 느려진다", "Direct Connect 회선을 새로 뽑는다", "트위터에서 BGP hijack이 났다는데 우리도 영향이 있나?" 같은 질문이 날아온다. 이때 BGP를 모르면 한 발짝도 못 움직인다.

BGP는 AS(Autonomous System) 간에 도달 가능한 경로 정보를 교환하는 프로토콜이다. 인터넷이 굴러가는 골격이고, 동시에 인터넷에서 가장 신뢰가 없는 프로토콜이기도 하다. 이 문서는 AS 개념부터 시작해서 eBGP/iBGP 차이, Path Attribute로 경로를 어떻게 고르는지, Route Reflector가 왜 필요한지, 컨버전스가 왜 느린지, hijack과 leak이 실제로 어떻게 일어나는지, 그리고 AWS Direct Connect에서 BGP 세션이 어떻게 동작하는지까지 다룬다.

## AS — 인터넷의 자치 단위

인터넷은 하나의 거대한 네트워크가 아니라 수많은 AS들이 서로 연결된 구조다. AS는 하나의 관리 주체가 통제하는 라우팅 정책의 단위다. KT, SK브로드밴드, LG U+ 같은 ISP가 각각 AS이고, AWS, Google, Cloudflare 같은 큰 클라우드/CDN 사업자도 자기 AS를 운영한다. AS마다 32비트 또는 16비트짜리 ASN(AS Number)이 붙는다. KT는 4766, AWS는 16509 같은 식이다.

AS 안에서는 그 조직이 알아서 라우팅한다. OSPF를 쓰든 IS-IS를 쓰든 EIGRP를 쓰든 외부에서는 알 바가 아니다. AS와 AS 사이를 잇는 게 BGP의 역할이다. "내 AS는 이 IP 대역들을 가지고 있고, 이쪽 경로로 오면 도달 가능하다"는 정보를 이웃 AS에게 알린다. 이걸 받은 이웃 AS는 자기 라우팅 테이블에 반영하고, 또 자기 이웃에게 전달한다.

여기서 핵심은 BGP가 "최단 경로"를 찾는 프로토콜이 아니라는 점이다. OSPF는 링크 비용을 합산해서 가장 빠른 길을 계산하지만, BGP는 정책 기반이다. "이 트래픽은 KT를 거쳐 보내고, 저 트래픽은 LG를 거쳐 보낸다"같은 비즈니스 결정이 우선한다. 회선료, 트래픽 정산, 백업 회선 정책이 다 BGP 설정에 박힌다. 그래서 BGP는 path-vector 프로토콜이라고 부른다. 경로(AS 시퀀스)와 함께 그 경로에 붙은 속성(attribute)을 같이 광고한다.

```
[AS 64500] --- eBGP --- [AS 65000] --- eBGP --- [AS 65001]
   회사 A              ISP            회사 B

광고: "10.10.0.0/16, AS_PATH = [65000, 64500], next-hop = 1.1.1.1"
```

회사 A가 자기 대역을 광고하면, ISP가 받아서 자기 ASN을 prepend한 뒤 회사 B에게 전달한다. 회사 B는 AS_PATH를 보고 "이 경로로 가려면 AS 65000을 거쳐서 AS 64500까지 간다"는 걸 안다.

## eBGP와 iBGP — 같은 프로토콜, 다른 동작

BGP 세션은 두 종류로 나뉜다. eBGP는 서로 다른 AS 사이에서 맺는 세션이고, iBGP는 같은 AS 안에서 맺는 세션이다. 같은 프로토콜인데 동작 방식이 미묘하게 다르다.

eBGP는 보통 직접 연결된 라우터 사이에서 맺는다. TTL이 1이라 한 홉만 건너간다. 라우터 A의 인터페이스 IP와 라우터 B의 인터페이스 IP로 TCP 179 세션을 연다. eBGP에서 광고를 받으면 next-hop을 보통 자기 자신으로 바꿔서 전달한다. 광고를 받을 때마다 자기 ASN을 AS_PATH 맨 앞에 붙인다. 그래서 AS_PATH를 보면 경로상의 모든 AS가 다 보인다.

iBGP는 같은 AS 안의 라우터끼리 맺는다. 보통 루프백 인터페이스끼리 TCP 세션을 맺어서, 물리 링크 하나가 끊겨도 다른 경로로 세션이 살아남게 한다. 여기서 중요한 규칙이 있다. **iBGP로 받은 경로는 다른 iBGP 피어에게 재광고하지 않는다.** 이걸 안 막으면 AS 내부에서 라우팅 루프가 돈다. BGP는 AS_PATH로 외부 루프는 막을 수 있지만(자기 ASN이 보이면 거른다), 같은 AS 안에서는 ASN이 안 바뀌니까 루프를 못 잡는다. 그래서 아예 재광고를 금지한다.

이 규칙 때문에 iBGP는 풀 메시(full mesh)를 요구한다. AS 안에 BGP를 도는 라우터가 N개면, 모든 라우터가 서로 1:1로 세션을 맺어야 한다. 세션 수가 N(N-1)/2개로 늘어난다. 라우터가 50개만 돼도 1225개의 세션이다. 이걸 다 손으로 관리할 수 없으니 Route Reflector가 등장한다. 뒤에서 다룬다.

iBGP는 next-hop도 그대로 전달한다. eBGP 피어에서 받은 next-hop이 외부 IP인 채로 iBGP를 타고 내부 라우터에 전달된다. 그래서 내부 라우터는 그 외부 next-hop까지 도달할 수 있는 IGP(OSPF, IS-IS) 라우트가 있어야 한다. 이게 빠지면 BGP 테이블에는 경로가 보이는데 실제로 패킷은 안 나간다. "next-hop unreachable" 상태다. 운영하다가 가장 자주 만나는 함정 중 하나다.

| 구분 | eBGP | iBGP |
|---|---|---|
| 피어 ASN | 다름 | 같음 |
| TTL | 보통 1 | 255 (루프백 사용) |
| AS_PATH 변경 | 자기 ASN prepend | 안 바꿈 |
| Next-hop 변경 | 자기로 바꿈 | 안 바꿈 |
| 재광고 | 다른 eBGP/iBGP 모두 가능 | 다른 iBGP에는 금지 |
| 토폴로지 | 점대점 | 풀 메시 또는 RR |

## Path Attribute — 경로 선택의 기준

같은 목적지로 가는 경로가 여러 개 광고되면 BGP는 그중 하나를 골라서 라우팅 테이블에 넣는다. 이 선택 과정에서 쓰는 게 Path Attribute다. 종류가 많은데 실무에서 자주 만지는 건 세 개다. LOCAL_PREF, AS_PATH, MED.

### AS_PATH

경로상의 AS들이 순서대로 나열된 리스트다. eBGP를 한 번 건널 때마다 자기 ASN이 맨 앞에 붙는다. 그래서 AS_PATH 길이는 "몇 개의 AS를 거치는가"를 의미한다. 다른 속성이 같다면 BGP는 AS_PATH가 짧은 경로를 고른다.

여기서 트릭이 하나 있다. AS_PATH prepending이다. 자기 AS를 광고할 때 일부러 자기 ASN을 여러 번 반복해서 붙인다. 그러면 이웃 AS들 입장에서 이 경로가 더 길어 보여서 우선순위가 떨어진다. 백업 회선을 평소엔 쓰지 않게 만들 때 흔히 쓰는 수법이다.

```
정상 광고:  AS_PATH = [64500]
prepend 3회: AS_PATH = [64500, 64500, 64500, 64500]
```

광고하는 쪽은 자기 ASN을 늘려도 손해가 없는데, 받는 쪽은 길어진 경로로 인식한다. 두 회선이 있을 때 한쪽에 prepend를 걸어두면 평소엔 prepend 없는 쪽으로 트래픽이 흐르고, 그쪽이 죽으면 prepend된 쪽으로 넘어간다.

다만 prepending이 항상 의도대로 동작하는 건 아니다. 다른 AS가 자기 LOCAL_PREF로 경로를 강제로 선택하면 AS_PATH 길이는 무시된다. 그래서 prepending은 권장 사항이지 강제력은 없다.

### LOCAL_PREF

같은 AS 안에서만 의미가 있는 속성이다. iBGP 피어들끼리 공유된다. 값이 클수록 우선한다. 기본값은 100이다.

쓰임새는 단순하다. 우리 AS에서 외부로 나가는 트래픽을 어느 회선으로 보낼지 결정한다. KT 회선과 LG 회선이 둘 다 있을 때, KT 회선에서 받은 광고에 LOCAL_PREF 200을 매기고 LG 회선 광고에는 100을 매기면, 모든 트래픽이 KT로 빠진다. 외부에서 들어오는 트래픽 방향은 LOCAL_PREF로 못 바꾸고 prepending이나 다른 수단을 써야 한다.

LOCAL_PREF는 BGP 의사결정 순서에서 AS_PATH보다 먼저 평가된다. 그래서 LOCAL_PREF만 잘 박아두면 prepending이 걸린 경로도 우선 선택할 수 있다. 회선 정책이 prepending보다 항상 강하다는 뜻이다.

### MED (Multi-Exit Discriminator)

이건 반대 방향이다. 다른 AS에게 "내 쪽으로 들어올 때는 이쪽으로 들어와줘"라고 힌트를 주는 속성이다. 값이 작을수록 우선한다.

쓰는 상황은 같은 두 AS가 여러 지점에서 연결된 경우다. 회사 A와 회사 B가 서울과 부산 두 곳에서 BGP 세션을 맺고 있다고 하자. 회사 A가 서울 회선 광고에 MED 100, 부산 회선 광고에 MED 200을 박으면, 회사 B는 서울 쪽으로 트래픽을 보낸다.

MED는 eBGP 피어 한 쌍 사이에서만 비교된다. 다른 AS로 넘어가면 보통 reset된다. 그래서 영향력이 좁다. 그리고 받는 쪽이 LOCAL_PREF로 덮어버리면 무용지물이다. MED는 어디까지나 "제안"이다.

### BGP 의사결정 순서

여러 경로가 있을 때 BGP가 고르는 순서는 대략 이렇다.

1. weight (Cisco 전용, 라우터 로컬)
2. LOCAL_PREF (큰 게 우선)
3. 자기 AS에서 originate한 경로
4. AS_PATH 길이 (짧은 게 우선)
5. ORIGIN (IGP < EGP < incomplete)
6. MED (작은 게 우선)
7. eBGP > iBGP
8. IGP 메트릭 (가장 가까운 next-hop)
9. 라우터 ID (작은 게 우선)

운영하면서 첫 두 단계, LOCAL_PREF와 originate에서 거의 결정난다. 그 아래까지 내려가는 건 흔치 않다.

## Route Reflector — iBGP 풀 메시 문제 해결

iBGP가 풀 메시를 요구한다고 했다. 라우터 10개면 45개 세션, 50개면 1225개 세션이다. 이걸 운영할 수가 없다. Route Reflector(RR)는 이 문제를 해결하려고 나온 구조다.

RR은 자기에게 들어온 iBGP 광고를 다른 iBGP 피어에게 재광고할 수 있는 라우터다. 일반적인 iBGP 규칙을 깬다. 대신 루프를 막기 위해 CLUSTER_LIST와 ORIGINATOR_ID라는 속성을 추가한다.

```
[RR1] --- iBGP --- [Client1]
  |
  +------ iBGP --- [Client2]
  |
  +------ iBGP --- [Client3]
```

Client들은 RR하고만 세션을 맺는다. Client1이 광고하면 RR이 받아서 Client2, Client3에게 뿌린다. 풀 메시 없이도 모든 라우터가 정보를 공유한다. 세션 수가 O(N²)에서 O(N)으로 줄어든다.

큰 ISP나 대기업 데이터센터에서는 RR을 이중화한다. RR 하나가 죽으면 그 클러스터 전체가 라우팅 정보를 못 받으니까. 두 RR을 두고 모든 Client가 양쪽에 세션을 맺는다. 이때 CLUSTER_ID를 같게 맞춰서 두 RR이 같은 클러스터임을 알린다.

RR을 도입할 때 가장 흔한 사고는 next-hop 문제다. RR은 광고를 reflect할 뿐이지 next-hop을 자기로 바꾸지 않는다. 그래서 Client는 원래 광고한 라우터의 next-hop을 그대로 받는다. IGP가 그 next-hop을 알고 있어야 패킷이 흐른다. RR을 가운데 두고 통신이 안 되면 십중팔구 next-hop reachability 문제다.

또 하나, RR 자체가 트래픽 경로에 끼어들 수도 있고 안 낄 수도 있다. RR이 단순히 컨트롤 플레인에서만 정보를 뿌리고 패킷은 다른 경로로 흐르는 게 일반적이지만, 토폴로지에 따라 RR 자체가 포워딩 경로에 들어가기도 한다. 설계할 때 RR을 어디에 둘지가 트래픽 패턴에 영향을 준다.

## BGP 컨버전스 — 왜 이렇게 느린가

OSPF는 LSA가 퍼지면 수초 안에 모든 라우터가 새 경로를 안다. BGP는 다르다. 경로 하나가 바뀌면 인터넷 전체가 안정 상태로 돌아오는 데 수십 초에서 수 분이 걸린다. 심한 경우는 십수 분 이상도 간다.

이유는 몇 가지가 겹친다.

**MRAI(Minimum Route Advertisement Interval).** BGP는 같은 prefix에 대한 업데이트를 너무 자주 보내지 않게 제한한다. eBGP는 기본 30초, iBGP는 5초가 일반적이다. 경로가 깜빡거리면 매번 광고하지 않고 모아서 보낸다. 이게 안정성에는 좋은데 컨버전스 속도는 늦춘다.

**Path Hunting.** 어떤 경로가 사라지면 BGP는 곧장 "도달 불가"라고 광고하지 않는다. 대신 다른 AS에게 받은 대체 경로를 시도해본다. 그 경로도 사실은 이미 죽은 경로일 수 있는데, BGP 입장에서는 알 수 없다. 그래서 "이 경로로 가봐도 안 되네, 그럼 저 경로로 가봐야지"를 반복하면서 시간을 보낸다. AS 토폴로지가 복잡할수록 path hunting 시간이 길어진다.

**TCP 기반 세션.** BGP는 TCP 179 위에서 동작한다. 세션이 끊기면 TCP keepalive와 BGP keepalive(기본 60초, hold timer 180초)가 만료될 때까지 끊긴 걸 모른다. BFD(Bidirectional Forwarding Detection)를 곁들이면 수백 ms 안에 감지할 수 있는데, 도입 안 한 곳도 많다.

**다단계 광고.** AS 사이를 광고가 건너갈 때마다 처리 시간이 쌓인다. 한 AS에서 받아서, BGP 의사결정을 돌리고, 정책 필터를 거치고, 다음 AS로 다시 광고한다. 이게 글로벌하게 퍼지려면 수십 AS를 건너야 한다.

실무 영향은 분명하다. BGP가 흔들리는 사이에는 경로가 잠시 사라지거나 비최적 경로로 트래픽이 흐른다. CDN이 한 리전을 빼버렸을 때 다른 리전으로 트래픽이 옮겨갈 때까지 30초~수 분 동안 응답이 느리거나 죽는다. 이걸 단축하려고 Anycast, BFD, 짧은 timer, 그리고 graceful restart 같은 기능을 조합해서 쓴다.

## Route Leak과 Hijack — BGP의 근본 결함

BGP는 신뢰 기반 프로토콜이다. 어떤 AS가 "이 IP는 내 거야"라고 광고하면, 이웃 AS는 그걸 그대로 믿는다. 검증 메커니즘이 프로토콜 자체에 없다. 이게 사고의 근원이다.

### Route Hijack

소유하지 않은 IP 대역을 자기 것이라고 광고하는 경우다. 의도적이든 실수든 똑같이 위험하다. BGP는 longest prefix match로 경로를 고르기 때문에 더 작은 prefix를 광고하면 트래픽을 끌어올 수 있다.

2008년 파키스탄 텔레콤 사건이 교과서적이다. 정부의 YouTube 차단 명령을 실행하려고 ISP가 YouTube의 IP 대역(208.65.153.0/24)을 자기 AS 안에서만 blackhole로 광고했는데, 이 광고가 실수로 외부에까지 새어 나갔다. YouTube가 원래 광고하던 건 더 큰 prefix(208.65.152.0/22)였고, 파키스탄에서 광고한 /24가 더 구체적이라 전 세계 ISP가 그쪽으로 트래픽을 보냈다. YouTube가 전 세계에서 2시간 동안 죽었다.

2018년 Amazon Route 53 사건도 비슷하다. 어떤 AS가 Amazon이 광고하던 IP 대역을 자기 것이라고 BGP로 광고했다. 트래픽이 그쪽으로 쏠리면서 Route 53 DNS 질의가 가로채졌고, MyEtherWallet 사용자들이 가짜 사이트로 유도돼서 약 15만 달러가 털렸다.

### Route Leak

소유권은 맞는데 광고하면 안 되는 곳에 광고가 새는 경우다. 보통 BGP에는 비즈니스 관계가 묻혀 있다. 고객(customer)에서 받은 광고는 모든 피어와 transit에게 전달하지만, 피어(peer)에서 받은 광고는 transit에게 전달하면 안 된다. transit이 자기 비용으로 그 트래픽을 옮겨야 하기 때문이다. 이 규칙이 깨지면 leak이다.

2017년 Google Japan 사건이 대표적이다. 일본의 한 ISP가 다른 AS에서 받은 Google 광고를 잘못된 방향으로 재광고해서, 일본 사용자의 Google 트래픽이 일본 내 작은 ISP를 거쳐가게 됐다. 회선 용량이 부족해서 일본 전역에서 Google 서비스가 한 시간 가까이 죽었다.

Leak은 hijack보다 탐지가 어렵다. IP 소유권은 정상이라 단순 검증으로는 안 잡힌다. 비즈니스 관계 위반인데, 그건 BGP 메시지에 안 적혀 있다.

## RPKI — BGP에 신뢰의 닻을 박는다

RPKI(Resource Public Key Infrastructure)는 IP 대역의 소유권을 암호학적으로 검증하는 체계다. BGP의 근본 결함 중 hijack 쪽은 어느 정도 막을 수 있다.

핵심 개념은 ROA(Route Origin Authorization)다. IP 대역의 진짜 소유자가 RIR(Regional Internet Registry — APNIC, ARIN 등)을 통해 "이 prefix는 이 ASN만 광고할 수 있다"는 서명된 선언문을 발급한다. 라우터가 BGP 광고를 받으면 그 광고가 ROA와 맞는지 확인한다. 결과는 셋 중 하나다.

- **Valid**: 광고된 prefix와 origin AS가 ROA와 일치
- **Invalid**: prefix는 맞는데 origin AS가 ROA와 다름, 또는 prefix가 ROA보다 더 구체적
- **NotFound**: 해당 prefix에 ROA가 없음

운영자는 보통 Invalid를 drop하고, NotFound와 Valid는 받는다. NotFound까지 drop하려면 전 세계가 ROA를 발급해야 하는데, 아직 그 단계는 아니다. 2025년 기준으로 인터넷 prefix의 절반 정도가 ROA로 커버된다.

AWS, Google, Cloudflare 같은 큰 사업자는 진작에 RPKI를 도입했다. Cloudflare는 isbgpsafeyet.com이라는 사이트를 만들어서 "당신의 ISP는 RPKI를 검증하는가"를 보여준다. 한국 ISP들도 KT, LG, SKB 모두 도입한 상태다.

RPKI의 한계도 분명하다. 첫째, origin만 검증한다. AS_PATH 자체는 검증 못 한다. 누군가 정상 origin을 가져와서 그 뒤에 자기 ASN을 끼워 넣은 가짜 AS_PATH를 만들어 광고하면 RPKI는 못 잡는다. 이건 BGPsec이라는 후속 표준이 풀려고 했는데 보급이 거의 안 됐다. 둘째, leak은 못 막는다. 셋째, ROA를 잘못 발급하면 자기 prefix를 자기가 못 광고하게 만드는 실수가 가능하다. 자기 발에 자기 총 쏘는 사례가 매년 몇 건씩 보고된다.

## AWS Direct Connect와 BGP 세션

Direct Connect는 AWS와 자기 데이터센터/사무실을 전용 회선으로 잇는 서비스다. 이 회선 위에서 BGP 세션을 맺어서 라우팅 정보를 교환한다. 백엔드 개발자가 BGP를 가장 가깝게 만지는 지점이다.

세션 구성은 이렇다. Direct Connect를 신청하면 AWS가 두 개의 BGP 피어 IP를 준다. 보통 /30 또는 /31 서브넷에서 양쪽 IP가 할당된다. 고객 쪽 라우터(자기 장비)와 AWS 쪽 라우터(가상 인터페이스, VIF)가 그 IP로 eBGP 세션을 맺는다.

VIF는 두 종류다.

- **Private VIF**: VPC와 연결한다. VPC의 CIDR을 BGP로 받고, 자기 온프레미스 대역을 광고한다. Direct Connect Gateway를 끼면 여러 리전의 VPC를 한 세션으로 묶을 수 있다.
- **Public VIF**: AWS 퍼블릭 서비스(S3, DynamoDB 등) IP 대역을 받는다. 인터넷을 안 거치고 S3에 접근하고 싶을 때 쓴다. 광고받는 prefix 수가 수천 개 단위라 라우터 메모리를 생각해야 한다.

ASN은 AWS 쪽이 7224(고정)이고, 고객 쪽은 보통 64512~65534 범위의 private ASN을 쓰거나 자기 공인 ASN을 쓴다. Direct Connect Gateway를 쓸 때는 ASN을 잘 골라야 한다. 같은 ASN을 여러 VIF에서 쓰면 AS_PATH 루프 방지 로직에 걸려서 광고가 막힌다.

운영에서 만나는 함정 몇 가지를 적는다.

**광고 prefix 수 제한.** Direct Connect는 한 BGP 세션당 광고받을 수 있는 prefix 수에 상한이 있다. Private VIF는 100개, Public VIF는 1000개가 기본이다. 회사 네트워크가 복잡해서 자기 쪽 prefix가 100개를 넘으면 summary route로 묶거나 한도 상향을 신청해야 한다. 한도를 넘으면 BGP 세션이 그냥 끊긴다.

**BFD.** Direct Connect는 BFD를 지원한다. 안 켜면 BGP keepalive(기본 30초/90초)가 만료되기 전까지 회선 끊김을 감지 못 한다. 90초 동안 트래픽이 블랙홀로 빠진다. BFD를 켜면 보통 300ms 안에 감지하고 두 번째 회선으로 페일오버한다. 신규 구축 시 거의 무조건 켠다.

**LOCAL_PREF/MED로 회선 우선순위.** Direct Connect 회선을 둘 이상 뽑으면 평소 어느 회선으로 트래픽이 흐를지 정해야 한다. 들어오는 트래픽(AWS → 온프레미스) 방향은 MED와 AS_PATH prepending으로 조절한다. AWS는 받은 광고 중 AS_PATH가 짧고 MED가 작은 쪽을 우선한다. 나가는 트래픽(온프레미스 → AWS) 방향은 자기 라우터의 LOCAL_PREF로 조절한다.

**VPN 백업과의 경합.** Direct Connect가 죽었을 때 IPsec VPN으로 자동 페일오버하는 구성이 흔하다. AWS는 일반적으로 Direct Connect 광고를 VPN보다 우선한다. 그런데 prefix 길이가 다르거나 양쪽에서 prepending이 걸려 있으면 의도와 다르게 동작할 수 있다. 페일오버 테스트는 실제로 회선을 끊어보고 확인해야 한다. BGP 시뮬레이션만 보면 안 된다.

## 트러블슈팅에서 자주 보는 패턴

운영하면서 자주 마주치는 BGP 관련 증상 몇 가지를 정리한다.

**경로는 보이는데 ping이 안 됨.** BGP 테이블에는 prefix가 들어와 있는데 실제 트래픽은 안 흐른다. 95% 확률로 next-hop reachability 문제다. iBGP나 RR 환경에서 자주 본다. `show ip bgp` 한 다음 next-hop IP를 보고, 그 IP가 IGP 라우팅 테이블에 있는지 확인한다.

**비대칭 라우팅.** 가는 길과 오는 길이 다르다. 보안 장비가 stateful이면 한쪽만 보고 패킷을 떨군다. 양쪽 AS의 BGP 정책을 같이 봐야 한다. 한 쪽에서 LOCAL_PREF로 한 회선을 우선하는데 반대쪽은 prepending에 걸려서 다른 회선을 고르면 비대칭이 난다.

**flap detection으로 인한 차단.** BGP는 너무 자주 깜빡이는 prefix를 차단하는 dampening 기능이 있다. 회선이 불안정해서 prefix가 몇 분 사이 수십 번 광고/철회되면, 그 prefix가 한동안 광고에서 제외된다. 광고가 안 들어와서 이상하다 싶을 때 dampening 상태를 확인해야 한다.

**ASN 충돌.** Private ASN을 여러 곳에서 같은 번호로 쓰다 보면 AS_PATH에 자기 ASN이 보여서 광고가 거부된다. 멀티 클라우드 환경에서 의외로 자주 본다. `allowas-in` 같은 옵션으로 풀 수 있지만 루프 위험이 따라온다.

## 정리

BGP는 인터넷의 라우팅 골격이다. AS 사이를 잇는 path-vector 프로토콜이고, 정책 기반으로 경로를 고른다. eBGP는 AS 간 세션이고 iBGP는 AS 내부 세션인데, iBGP는 루프 방지 때문에 풀 메시를 요구해서 Route Reflector로 우회한다. 경로 선택은 LOCAL_PREF, AS_PATH, MED 같은 attribute로 제어한다. 컨버전스는 MRAI와 path hunting 때문에 느리고, 신뢰 기반 설계 때문에 hijack과 leak이 끊이지 않는다. RPKI가 origin 검증을 풀고 있고 AWS Direct Connect 같은 클라우드 연동에서 BGP를 실제로 만지게 된다.

백엔드 개발자가 BGP를 처음부터 끝까지 설정할 일은 드물지만, Direct Connect나 멀티 클라우드 환경에서 페일오버가 의도대로 안 동작할 때, CDN 트래픽이 이상한 경로로 흐를 때, 인터넷 어딘가에서 hijack 사고가 났을 때 — 이때 BGP를 알면 원인을 짚을 수 있다.
