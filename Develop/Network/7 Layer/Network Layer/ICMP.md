---
title: ICMP — 진단 프로토콜의 안과 밖
tags:
  - Network
  - ICMP
  - ICMPv6
  - ping
  - traceroute
  - PMTUD
updated: 2026-05-12
---

# ICMP — 진단 프로토콜의 안과 밖

## 들어가며

신입 때는 ICMP를 그냥 "ping이 쓰는 프로토콜" 정도로 알고 있었다. 그러다 어느 날 운영 서버에서 PMTUD 블랙홀을 만나고, AWS 보안 그룹의 ICMP 항목을 한참 노려보고, 방화벽 룰에서 `icmp-type 3 code 4`를 따로 빼두라는 잔소리를 받으면서 비로소 이 프로토콜의 역할이 보이기 시작했다.

ICMP는 데이터 전송용이 아니다. IP 계층에서 일어난 문제를 송신자에게 알려주는 신호 프로토콜이다. "경로가 끊겼다", "TTL이 다 됐다", "패킷이 너무 커서 못 보낸다" 같은 메시지를 IP 패킷 위에 실어 돌려준다. 그래서 ICMP가 차단된 네트워크에서는 IP가 자기 상태를 설명할 수단이 사라진다. 통신이 그냥 멈추거나 이상하게 느려지는 현상의 절반쯤은 ICMP가 어딘가에서 막혀 생긴다.

이 문서는 ICMP의 동작 원리, 자주 쓰는 메시지 타입, 진단 도구 사용법, 그리고 실무에서 만나는 문제를 정리한 글이다.

## ICMP의 위치

ICMP는 IP 위에서 동작하지만 TCP·UDP처럼 트랜스포트 계층은 아니다. IP 헤더의 Protocol 필드가 1이면 ICMP, 6이면 TCP, 17이면 UDP다. 즉 IP에 캡슐화돼 전송되지만, 역할은 IP 자신의 부속물에 가깝다. RFC 792가 ICMP를 "IP의 필수 구성 요소"라고 명시한 이유도 그래서다.

```
[Ethernet] [IPv4 헤더 protocol=1] [ICMP 헤더] [ICMP 페이로드]
```

ICMP 페이로드의 정체는 메시지 타입마다 다르다. Echo Request라면 식별자와 시퀀스 번호, 그리고 임의 데이터가 들어간다. Destination Unreachable이라면 문제를 일으킨 원본 IP 헤더와 첫 8바이트가 그대로 복사돼 들어간다. 받는 쪽은 그 원본 헤더를 보고 "아, 내가 보낸 그 패킷이 막혔구나"를 알아낸다.

ICMP에는 포트 개념이 없다. TCP·UDP처럼 5-tuple로 흐름을 구분하지 못한다는 뜻이다. 그래서 NAT가 ICMP를 다룰 때는 Echo의 Identifier 필드를 포트처럼 써서 매핑한다. 라우터의 conntrack 테이블을 보면 ICMP 엔트리가 따로 잡혀 있는 게 그래서다.

## ICMP 헤더 구조

ICMP 헤더는 단순하다. 4바이트 고정 부분 뒤에 타입별 가변 영역이 붙는다.

```
 0               1               2               3
 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7
+---------------+---------------+-------------------------------+
|    Type (1)   |   Code (1)    |        Checksum (2)           |
+---------------+---------------+-------------------------------+
|                  Rest of Header (4 bytes)                     |
+---------------------------------------------------------------+
|                  Payload (가변 길이)                           |
+---------------------------------------------------------------+
```

- **Type**: 메시지의 큰 분류. Echo Request=8, Echo Reply=0, Destination Unreachable=3, Time Exceeded=11, Redirect=5 같은 식이다.
- **Code**: 같은 Type 안에서의 세부 사유. 예를 들어 Type 3(Destination Unreachable) 안에서 Code 0은 "Network Unreachable", Code 1은 "Host Unreachable", Code 3은 "Port Unreachable", Code 4는 "Fragmentation Needed and DF set"이다.
- **Checksum**: ICMP 헤더와 페이로드 전체에 대한 16비트 체크섬. IP 헤더는 포함하지 않는다.
- **Rest of Header**: 타입에 따라 의미가 바뀌는 4바이트. Echo는 Identifier(2) + Sequence(2), Type 3 Code 4는 상위 2바이트가 0, 하위 2바이트가 next-hop MTU.

타입과 코드 조합이 ICMP의 핵심이다. Type만 보고 "Destination Unreachable"이라고 단정하면 안 된다. Code 0(Network)과 Code 3(Port)은 진단상 의미가 완전히 다르다. UDP에서 "Connection refused"가 잡히는 원리도 받는 호스트가 ICMP Type 3 Code 3을 돌려주기 때문이다.

## 자주 만나는 메시지 타입

### Echo Request / Echo Reply (Type 8 / Type 0)

ping이 쓰는 두 메시지다. 송신자가 Type 8을 보내면 수신자가 Type 0으로 응답한다. 페이로드는 송신자가 채워 넣은 임의 바이트열인데, 수신자는 그것을 토씨 하나 안 바꾸고 그대로 반사해 보낸다. 그래서 송신자는 RTT를 측정할 수 있고, 페이로드 위변조 여부로 경로 무결성도 확인한다.

Identifier 필드는 같은 호스트에서 동시에 도는 여러 ping을 구분한다. 리눅스 ping은 보통 자기 PID 하위 16비트를 넣는다. Sequence는 한 번의 ping 세션에서 패킷이 몇 번째인지 매기는 값이다. 응답이 늦게 와도 어느 요청에 대한 응답인지 매칭할 수 있다.

### Destination Unreachable (Type 3)

가장 자주 만나는 에러 메시지다. Code로 사유가 갈린다.

| Code | 의미 | 발생 상황 |
|---|---|---|
| 0 | Network Unreachable | 라우터가 목적지 네트워크로 가는 경로가 없을 때 |
| 1 | Host Unreachable | 라우터까지는 갔지만 그 안의 호스트로 보낼 수 없을 때 (ARP 실패 등) |
| 2 | Protocol Unreachable | 목적지 호스트가 해당 IP 프로토콜을 모를 때 |
| 3 | Port Unreachable | UDP 패킷이 열려 있지 않은 포트로 도착했을 때 |
| 4 | Fragmentation Needed and DF set | DF 비트가 켜진 패킷이 다음 홉 MTU를 초과할 때 |
| 13 | Communication Administratively Prohibited | 방화벽이 정책으로 막을 때 |

Code 3과 Code 13의 차이는 운영 중에 의외로 중요하다. Code 3은 "그 포트에 듣는 프로세스가 없다"고 호스트 자신이 직접 알려주는 것이다. 즉 호스트까지는 도달했다. Code 13은 "중간 어딘가의 정책 장비가 차단했다"는 의미다. 호스트가 살아 있는지조차 알 수 없다.

Code 4는 PMTUD의 핵심이다. 별도 절에서 다룬다.

### Time Exceeded (Type 11)

TTL이 0이 됐을 때 라우터가 돌려주는 메시지다. Code 0은 "TTL exceeded in transit", Code 1은 "Fragment reassembly time exceeded"다. traceroute가 동작하는 원리가 바로 Code 0이다.

송신자가 TTL=1로 패킷을 보낸다 → 첫 라우터가 TTL을 1 줄여 0으로 만든 뒤 패킷을 폐기하고 Type 11 Code 0을 돌려준다 → 송신자는 그 응답의 src IP로 첫 홉을 알아낸다. TTL=2로 보내면 두 번째 라우터에서 같은 일이 일어나 두 번째 홉을 알아낸다. 이런 식으로 한 홉씩 늘려가며 경로를 더듬는다.

Code 1은 IP 단편화에서 받는 쪽이 모든 조각을 시간 내에 모으지 못했을 때 발생한다. 리눅스는 기본 30초 안에 reassembly가 끝나지 않으면 이 메시지를 돌려준다. 평소엔 거의 볼 일이 없지만 단편화가 심한 네트워크에서 가끔 잡힌다.

### Redirect (Type 5)

라우터가 송신자에게 "더 나은 경로가 있다"고 알려주는 메시지다. 같은 서브넷 안에 라우터 A와 라우터 B가 있고, 호스트의 기본 게이트웨이가 A로 잡혀 있는데 특정 목적지로는 B가 더 가까운 경우, A가 호스트에게 "다음부터는 B로 직접 보내라"고 알려준다.

요즘은 거의 안 쓴다. 호스트 라우팅 테이블을 외부에서 마음대로 수정하게 두면 보안상 위험하다. 리눅스는 기본적으로 `net.ipv4.conf.all.accept_redirects=0`으로 받는다. 받지도 보내지도 않는 게 정상이다.

### Source Quench (Type 4) — 폐기됨

옛날에는 라우터가 송신자에게 "너무 빠르다, 좀 늦춰라"고 보내는 Type 4가 있었다. RFC 6633에서 폐기됐다. 혼잡 제어는 TCP에 맡기는 게 표준이 된 지 오래다. 옛 문서를 읽다 보면 가끔 언급되는데, 실 장비가 보내는 일은 없다고 봐도 된다.

## ping의 동작 원리

```
[Client]                                      [Server]
   |                                              |
   |  ICMP Echo Request (Type 8, id=PID, seq=1)   |
   |--------------------------------------------->|
   |                                              |
   |  ICMP Echo Reply   (Type 0, id=PID, seq=1)   |
   |<---------------------------------------------|
   |                                              |
   |  ICMP Echo Request (Type 8, id=PID, seq=2)   |
   |--------------------------------------------->|
   |                ...                           |
```

표면적으로는 단순하지만 실제 동작에는 신경 쓸 점이 몇 가지 있다.

리눅스 ping은 두 가지 소켓 중 하나로 동작한다. setuid root 바이너리로 깔린 옛 ping은 raw socket을 직접 열어 ICMP 헤더를 손수 만든다. 요즘 배포판은 `net.ipv4.ping_group_range`로 지정된 그룹의 사용자에게 unprivileged ICMP 소켓을 허용한다. 후자가 동작하면 ping 바이너리에 setuid가 안 붙어 있어도 일반 사용자가 ping을 쓸 수 있다.

```bash
# 일반 사용자가 ping을 쓸 수 있는 그룹 범위 확인
sysctl net.ipv4.ping_group_range
# net.ipv4.ping_group_range = 0 2147483647
```

ping이 RTT를 측정하는 방법은 페이로드 안에 송신 시각을 기록해 두는 방식이다. 응답 페이로드가 그대로 돌아오므로 시각 부분을 꺼내 현재 시각과 빼면 RTT가 나온다. NTP가 어긋나도 송신·수신이 같은 호스트라 영향이 없다.

ping을 응답하지 않는 호스트가 다 죽은 것은 아니다. 운영체제 단에서 `net.ipv4.icmp_echo_ignore_all=1`로 끄거나, 방화벽에서 Type 8을 막거나, 클라우드 보안 그룹의 ICMP 인바운드를 막아둔 경우다. 그래서 운영 환경에서 "ping이 안 되니까 죽었다"는 단정은 위험하다. TCP 핸드셰이크가 되는지, HTTP 응답이 오는지를 같이 봐야 한다.

## traceroute와 mtr

### traceroute의 두 변종

리눅스의 `traceroute`는 기본적으로 UDP 패킷을 쓴다. 33434번부터 시작해 한 홉마다 포트 번호를 늘려가며 보낸다. 목적지에 도착하면 그 포트가 닫혀 있어서 호스트가 ICMP Type 3 Code 3(Port Unreachable)을 돌려준다. 이걸로 도착을 인지한다. 중간 홉은 TTL 만료로 Type 11 Code 0을 돌려준다.

`traceroute -I`는 UDP 대신 ICMP Echo Request를 쓴다. 윈도우의 `tracert`도 ICMP 방식이다. UDP 방식은 임의 포트로 들어가 방화벽에 막히기 쉽고, ICMP 방식은 ICMP가 막힌 네트워크에서 죽는다. 환경에 따라 둘을 번갈아 시도하는 게 실무다.

`traceroute -T`는 TCP SYN을 쓴다. 80, 443 같이 열려 있을 법한 포트로 SYN을 보내고 중간 홉은 Type 11로 받는다. 방화벽이 다른 트래픽은 막고 80/443만 허용하는 환경에서 유일하게 통하는 변종이다.

```bash
# UDP 기반 (기본)
traceroute api.example.com

# ICMP Echo 기반
traceroute -I api.example.com

# TCP SYN 기반 (443 포트)
traceroute -T -p 443 api.example.com

# 첫 홉부터 보고 싶을 때
traceroute -f 1 api.example.com
```

### 출력 읽기

```
 1  10.0.0.1                0.412 ms   0.395 ms   0.389 ms
 2  10.20.0.1               1.234 ms   1.198 ms   1.245 ms
 3  * * *
 4  203.0.113.1             5.678 ms   5.643 ms   5.612 ms
 5  198.51.100.42           12.34 ms !H * 12.21 ms
```

기본적으로 한 홉마다 3번 시도한다. RTT 세 값이 표시되는 게 그래서다. `*`는 응답이 안 왔다는 뜻이다. 한 홉이 전부 `* * *`로 나오면 그 라우터가 ICMP 응답을 안 보내거나 응답이 다른 경로로 가서 잡히지 않는 경우다. 보안상 일부러 응답을 끈 경우도 많다. 한두 홉이 `*`라고 해서 경로가 끊긴 건 아니다.

`!H`, `!N`, `!P` 같은 표기는 ICMP Type 3의 Code를 글자로 풀어준 것이다. `!H`=Host Unreachable, `!N`=Network Unreachable, `!P`=Protocol Unreachable, `!X`=Communication Administratively Prohibited. 이게 붙어 있으면 그 홉에서 명시적 거부가 일어났다는 뜻이다.

### MPLS 환경의 hop 누락

ISP 백본을 거치면 traceroute 결과 중간에 갑자기 RTT가 큰 점프를 보이거나 hop이 통째로 사라지는 경우가 있다. MPLS 라벨 스위칭을 쓰는 백본은 IP 라우팅을 거치지 않고 라벨로 포워딩하기 때문에 중간 LSR(Label Switching Router)이 TTL을 줄이지 않는 경우가 있다. 이걸 "MPLS hop hiding"이라고 부른다.

RFC 4950으로 ICMP 확장이 정의되어 있어서, 일부 라우터는 Type 11 응답에 MPLS 라벨 정보를 같이 실어 보낸다. modern traceroute는 이걸 해석해서 출력해준다.

```
 5  10.10.10.10  20.5 ms  MPLS Label=12345 Exp=0 TTL=1 S=1
```

이런 줄이 보이면 MPLS 구간이 있다는 신호다. 백본 ISP를 거치는 경로에서 흔히 보인다. 단순히 "hop이 빠졌다"가 아니라 "라벨 스위칭 구간을 지나는 중이다"라고 읽어야 한다.

### mtr

`mtr`은 traceroute와 ping을 합친 도구다. 경로의 모든 홉을 향해 동시에 ping을 계속 돌려서 hop별 손실률과 평균/최대 RTT를 실시간으로 보여준다. 간헐적 손실의 원인 홉을 찾을 때 쓴다.

```bash
mtr --report --report-cycles 100 api.example.com
```

```
HOST: client                      Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- 10.0.0.1                   0.0%   100    0.4    0.4   0.3   0.7   0.1
  2.|-- 10.20.0.1                  0.0%   100    1.2    1.3   1.1   2.4   0.2
  3.|-- 203.0.113.1                0.0%   100    5.6    5.7   5.4   8.1   0.4
  4.|-- 203.0.113.5               12.0%   100   18.4   19.2  17.8  35.6   3.2
  5.|-- 198.51.100.42              0.0%   100   12.3   12.5  12.1  14.3   0.3
```

4번 홉에서 12% 손실이 잡혔는데 5번 홉은 손실이 0이라면 4번 홉 라우터가 자기에게 온 ICMP에 일부만 응답하는 것이지 경로 자체가 끊긴 건 아니다. 진짜 손실 구간은 마지막 홉까지 손실률이 같이 올라가야 한다. mtr 결과를 읽을 때 가장 자주 헷갈리는 부분이다.

방향성도 잊으면 안 된다. mtr은 forward path를 본다. return path가 다른 경로로 가는 경우, 손실이 return 쪽에서 일어나도 mtr은 그것을 직접 측정하지 못한다. 양쪽에서 동시에 mtr을 돌려야 보인다.

## PMTUD에서 ICMP의 역할

PMTUD(Path MTU Discovery)는 ICMP Type 3 Code 4 "Fragmentation Needed and Don't Fragment was Set"에 전적으로 의존한다. 송신자가 DF 비트를 켠 큰 패킷을 보내면, 다음 홉 MTU를 초과하는 라우터가 이 메시지를 돌려주면서 자기 출력 인터페이스 MTU 값을 알려준다. 송신자는 그 값을 받아 PMTU 캐시를 갱신하고 세그먼트를 줄여 재전송한다.

```
[Host A] --1500-- [R1] --1500-- [R2] --1400-- [R3] --1500-- [Host B]

A → B: IP DF=1, length=1500
R2가 R3로 보내려는 순간 1500 > 1400 인지
R2 → A: ICMP Type 3 Code 4, next-hop MTU=1400
A: PMTU 캐시 갱신 후 1400 이하로 재전송
```

문제는 ICMP Type 3 Code 4 한 줄이 어디선가 막히는 순간 발생한다. AWS 보안 그룹, 회사 방화벽, 일부 ISP의 보수적 ICMP 정책이 흔한 원인이다. 송신자는 큰 패킷을 계속 보내고, 라우터는 계속 버리고, ICMP 응답은 안 돌아온다. TCP 재전송 타임아웃이 누적되다 끝내 RST로 끊긴다. 이 현상을 PMTUD 블랙홀이라고 부른다.

증상은 일관된다. 작은 응답은 잘 오고 큰 응답에서만 멈춘다. SSH 비밀번호 입력까지는 되는데 키 교환 패킷이 큰 시점에서 멈춘다. TLS ClientHello는 가는데 인증서 체인이 큰 ServerHello에서 멈춘다.

회피 수단은 두 가지다. 첫째는 ICMP Type 3 Code 4를 명시적으로 허용하는 것. 모든 ICMP를 막더라도 이 한 종류는 통과시켜야 한다.

```bash
# iptables에서 Type 3 Code 4 허용
iptables -A INPUT -p icmp --icmp-type fragmentation-needed -j ACCEPT
```

둘째는 PLPMTUD(RFC 4821)다. ICMP에 의존하지 않고 TCP 자체가 재전송 패턴으로 PMTU를 추정한다. 리눅스는 `tcp_mtu_probing`으로 켠다.

```bash
# 0=비활성, 1=블랙홀 감지 시 활성, 2=항상 활성
sysctl -w net.ipv4.tcp_mtu_probing=1
```

값을 1로 두는 게 운영상 무난하다. 평소엔 PMTUD로 동작하다가 블랙홀 패턴이 잡히면 PLPMTUD로 fallback한다. 자세한 내용은 [MTU·MSS와 PMTUD](MTU_MSS_PMTUD.md) 문서에 따로 정리해 두었다.

## ICMPv6 — 다른 프로토콜이라고 봐도 된다

IPv6의 ICMPv6(RFC 4443)는 IPv4 ICMP와 이름만 같다. 메시지 번호 체계가 다르고, IPv6 동작의 핵심 부품들이 ICMPv6에 들어가 있다. IPv4에서는 ARP가 하던 일을 IPv6에서는 ICMPv6 NDP(Neighbor Discovery Protocol)가 한다. SLAAC로 주소를 자동 할당받는 것도 ICMPv6 Router Solicitation/Router Advertisement이다.

| 타입 | 이름 | 역할 |
|---|---|---|
| 1 | Destination Unreachable | IPv4 Type 3에 대응 |
| 2 | Packet Too Big | IPv4 Type 3 Code 4에 대응 (별도 Type) |
| 3 | Time Exceeded | IPv4 Type 11에 대응 |
| 4 | Parameter Problem | 헤더 필드 오류 |
| 128 | Echo Request | ping6용 |
| 129 | Echo Reply | ping6용 |
| 133 | Router Solicitation | NDP |
| 134 | Router Advertisement | NDP, SLAAC |
| 135 | Neighbor Solicitation | NDP, ARP 대체 |
| 136 | Neighbor Advertisement | NDP, ARP 대체 |
| 137 | Redirect | IPv4 Type 5에 대응 |

128번 이상이 Informational(요청/응답 같은 정보성), 0~127이 Error 메시지다. 이 구분도 IPv4와 다른 부분이다.

실무에서 가장 중요한 차이가 두 가지다.

첫째, IPv6에서는 IP 단편화를 라우터가 못 한다. 송신 호스트만 단편화할 수 있다. 그래서 PMTUD가 사실상 강제다. Path MTU를 모르고 보낸 큰 패킷은 그냥 막힌다. ICMPv6 Type 2 "Packet Too Big"이 돌아와야 송신자가 PMTU를 갱신한다. IPv6 네트워크에서 ICMPv6를 차단하면 통신이 거의 동작하지 않는다.

둘째, NDP가 ICMPv6 위에 올라가 있어서 ICMPv6를 막으면 같은 서브넷의 노드를 찾지도 못한다. IPv4에서 ARP를 막는 것과 비슷한 효과다. 보안 정책으로 ICMPv6를 통째로 막으면 IPv6 자체가 안 돈다.

RFC 4890이 어떤 ICMPv6 타입을 허용하고 어떤 걸 막아도 되는지를 정리해 둔 문서다. 운영 방화벽 룰을 짤 때 참고하면 도움이 된다. 최소한 Type 1(Destination Unreachable), Type 2(Packet Too Big), Type 3(Time Exceeded), Type 4(Parameter Problem), 그리고 NDP 관련 Type 133~137은 허용해야 한다.

## 보안 — ICMP를 이용한 공격

### ICMP Flood

가장 단순한 형태다. 대상 호스트에 Echo Request를 초당 수십만 개씩 쏟아붓는다. 응답 처리에 CPU와 대역폭이 소모돼 정상 트래픽이 처리되지 않는다. 요즘은 NIC와 커널이 잘 견디지만 대역폭 자체를 다 채우면 결국 끊긴다.

리눅스에서는 ICMP rate limit이 기본으로 켜져 있다. `net.ipv4.icmp_ratelimit`과 `net.ipv4.icmp_ratemask`로 조절한다. 호스트가 보내는 ICMP 응답의 빈도를 제한하는 값인데, 호스트 자체가 ICMP를 무한히 토해내며 다운되는 일을 막아준다.

```bash
# 기본값: 1000ms 윈도우에서 같은 종류의 응답을 1개만 보냄
sysctl net.ipv4.icmp_ratelimit
# net.ipv4.icmp_ratelimit = 1000
```

### Smurf 공격

브로드캐스트 주소를 악용하는 옛 공격이다. 공격자가 src IP를 피해자 IP로 위조한 Echo Request를 어떤 네트워크의 브로드캐스트 주소로 보낸다. 그 네트워크의 모든 호스트가 Echo Reply를 피해자에게 돌려준다. 1대가 보낸 패킷 1개가 수백 개의 응답으로 증폭되어 피해자에게 쏟아진다.

지금은 거의 사라진 공격이다. 라우터가 외부에서 들어온 패킷을 브로드캐스트 주소로 포워딩하는 동작이 RFC 2644(BCP 34)로 금지됐고, 대부분의 OS도 브로드캐스트 Echo에 응답하지 않는다. 리눅스는 `net.ipv4.icmp_echo_ignore_broadcasts=1`이 기본값이다. 그래도 옛 장비가 섞인 환경에서는 가끔 잡힌다.

### Ping of Death

옛 OS의 IP reassembly 버그를 이용한 공격이다. ICMP 페이로드를 단편화해서 보내되 마지막 조각이 IP 패킷 최대 길이 65535바이트를 넘기게 한다. 받는 쪽이 reassemble하면서 버퍼 오버플로가 일어나 커널이 죽는다. 1990년대 후반 이슈였고 현재 OS는 다 막혀 있다. 역사적 사례로 알아두는 정도면 된다.

### ICMP Tunneling

ICMP 페이로드는 송신자가 채우는 임의 데이터다. 공격자가 이 페이로드에 명령어나 데이터를 실어 보내고, 침투한 호스트가 같은 방식으로 응답하면 ICMP를 C2 채널로 쓸 수 있다. 방화벽이 TCP·UDP는 깐깐히 막아도 ICMP는 진단 목적으로 열어두는 경우가 많아 빠져나가기 쉽다.

운영 측에서는 ICMP 페이로드 크기와 패턴을 모니터링하는 게 1차 방어다. 정상 ping은 페이로드가 56바이트 안팎으로 작고 패턴이 단조롭다. 비정상적으로 큰 ICMP가 한 호스트에서 지속적으로 발생하면 의심해야 한다.

## tcpdump로 ICMP 분석

운영 중에 ICMP 문제를 진단할 때 가장 자주 쓰는 게 tcpdump다. ICMP만 잡는 필터는 단순하다.

```bash
# 모든 ICMP 캡처
tcpdump -i any -n icmp

# 특정 호스트와 주고받는 ICMP만
tcpdump -i any -n 'icmp and host 10.0.0.42'

# Type 3 Code 4 (Fragmentation Needed)만
tcpdump -i any -n 'icmp[icmptype]==3 and icmp[icmpcode]==4'

# Echo Request만
tcpdump -i any -n 'icmp[icmptype]==icmp-echo'

# Time Exceeded만 (traceroute 진단 시)
tcpdump -i any -n 'icmp[icmptype]==icmp-timxceed'
```

IPv6는 별도 필터를 써야 한다.

```bash
# 모든 ICMPv6
tcpdump -i any -n icmp6

# NDP만 (NS/NA/RS/RA)
tcpdump -i any -n 'icmp6 and (ip6[40]==135 or ip6[40]==136 or ip6[40]==133 or ip6[40]==134)'
```

읽는 법은 출력을 보면 감이 잡힌다.

```
12:34:56.123456 IP 10.0.1.5 > 10.0.2.7: ICMP echo request, id 12345, seq 1, length 64
12:34:56.123890 IP 10.0.2.7 > 10.0.1.5: ICMP echo reply,   id 12345, seq 1, length 64
12:34:56.234567 IP 10.20.0.1 > 10.0.1.5: ICMP 10.0.2.7 unreachable - need to frag (mtu 1400), length 36
12:34:56.345678 IP 10.50.0.1 > 10.0.1.5: ICMP time exceeded in-transit, length 36
```

세 번째 줄이 PMTUD 메시지다. `need to frag (mtu 1400)` 부분이 다음 홉 MTU 값을 알려준다. 운영 중 PMTUD가 동작하는지 확인하려면 이 패턴이 잡히는지를 본다.

`-vv` 옵션을 붙이면 원본 IP 헤더와 처음 8바이트가 같이 출력된다. ICMP가 어떤 패킷에 대한 응답인지 매칭하는 데 쓴다.

```bash
tcpdump -i any -nvv icmp
```

```
ICMP 10.0.2.7 unreachable - need to frag (mtu 1400),
  length 556
    IP (tos 0x0, ttl 64, id 12345, offset 0, flags [DF],
        proto TCP (6), length 1500)
    10.0.1.5.45678 > 10.0.2.7.443: Flags [.], seq 1:1449, ack 200, win 502
```

답이 보인다. 송신자가 1500바이트 TCP 패킷에 DF 비트를 켜고 보냈고, 어떤 라우터가 MTU 1400을 알려주며 막은 상황이다. 송신자는 이 ICMP를 받자마자 PMTU를 1400으로 갱신해야 한다. 만약 ICMP가 송신자까지 도달하지 못한다면 송신자는 같은 1500바이트로 재전송을 반복한다. 이 패턴이 보이면 PMTUD 블랙홀이다.

## ICMP를 무작정 차단하지 마라

신입에게 자주 하는 말이 하나 있다. ICMP를 통째로 막는 보안 정책을 마주치면 정말로 모든 ICMP를 막아야 하는지 다시 한 번 확인해라. 막아도 되는 건 Echo Request 정도다. Type 3, Type 11은 살려두는 게 운영상 거의 항상 옳다.

특히 Type 3 Code 4(Fragmentation Needed)를 막으면 PMTUD 블랙홀이 터진다. Type 11(Time Exceeded)를 막으면 traceroute가 안 되어 장애 진단이 어려워진다. Type 3 Code 3(Port Unreachable)을 막으면 UDP 기반 서비스의 "연결 실패" 진단이 안 된다. 다 정상 운영에 필요한 신호다.

IPv6라면 더하다. NDP가 ICMPv6라서 ICMPv6 차단은 IPv6 자체를 끄는 것과 같다. AWS Security Group에서 IPv6를 쓰는 인스턴스라면 ICMPv6 인바운드를 충분히 허용해야 정상 동작한다.

운영에서 ICMP 정책을 짤 때 기준이 되는 건 RFC 4890(IPv6용)과 SANS·NIST의 보안 가이드다. 통째로 막는 정책은 보안에도 별 도움이 안 되면서 운영만 망가뜨린다. 필요한 타입만 살리고 나머지를 막는 게 정공법이다.
