---
title: MTU·MSS와 Path MTU Discovery 블랙홀
tags:
  - Network
  - MTU
  - MSS
  - PMTUD
  - VPN
  - IPsec
updated: 2026-05-04
---

# MTU·MSS와 Path MTU Discovery 블랙홀

## 들어가며

운영 중인 서비스가 어느 날부터 특정 응답에서만 멈춘다. 작은 GET은 잘 도는데 파일 업로드만 하면 10초 정도 멈춘 뒤 RST가 떨어진다. 패킷 캡처를 떠 보면 클라이언트가 큰 패킷을 보내고 서버는 받지 못한 채 재전송만 반복한다. 라우터 어딘가에서 패킷이 통째로 사라지고 있는 것이다. 처음 이 현상을 본 건 사내 VPN 너머의 ALB로 빌드 아티팩트를 올리던 때였다. 범인은 PMTUD 블랙홀이었다.

MTU와 MSS는 평소엔 신경 쓸 일이 없다. 이더넷 1500바이트, MSS 1460바이트, 그게 끝이다. 그런데 한 번 이게 어긋나기 시작하면 증상이 묘하다. ping은 되는데 SSH는 멈춘다. HTTP GET은 되는데 POST는 끊긴다. 작은 응답은 오는데 큰 응답은 안 온다. 알고 나면 단순한 문제지만 모르면 며칠을 헤맨다.

이 문서는 MTU·MSS·PMTUD를 둘러싸고 실제로 만났던 문제와 풀어낸 방법을 정리한 글이다.

## MTU와 MSS는 무엇이 다른가

### MTU

Maximum Transmission Unit. 한 링크가 한 번에 실어 나를 수 있는 IP 패킷의 최대 크기다. 이더넷에서는 거의 1500바이트로 고정돼 있다. 여기서 1500바이트는 IP 헤더와 페이로드를 모두 포함한 크기다. 이더넷 프레임의 헤더(14바이트)와 FCS(4바이트)는 별개로 붙는다.

링크별로 MTU 값이 다르다. PPPoE는 1492, IPsec 터널은 보통 1400~1438, GRE는 1476, WireGuard는 1420 근처다. 출발지와 목적지 사이에 여러 링크가 있으면 그중 가장 작은 값이 그 경로의 PMTU(Path MTU)다. 1500-1500-1400-1500 식으로 중간에 좁은 구간이 하나라도 끼면 전체 경로의 MTU는 1400이 된다.

### MSS

Maximum Segment Size. TCP 세그먼트의 페이로드 최대 크기다. TCP 헤더와 IP 헤더를 뺀 순수 데이터 부분만 본다. 표준 이더넷 기준으로 계산하면 `1500 - 20(IP) - 20(TCP) = 1460`바이트가 된다. TCP 옵션이 붙으면 더 줄어든다. 타임스탬프 옵션이 켜져 있으면 12바이트가 더 빠져서 1448이 되기도 한다.

MSS는 TCP가 3-way handshake할 때 SYN과 SYN/ACK에 옵션으로 실어 보낸다. 양쪽이 광고한 값 중 작은 쪽을 따른다. 한쪽이 1460을 광고하고 다른 쪽이 1380을 광고하면 그 연결의 MSS는 1380이 된다.

### 둘의 관계

MTU는 IP 계층, MSS는 TCP 계층의 개념이다. 하지만 결국 같은 한계를 다른 시점에서 다루는 것이다. MTU가 1500이면 그 위에서 돌아가는 TCP는 MSS를 1460으로 잡는다. MTU가 1400이면 MSS는 1360이 된다. 둘 사이의 고정 차이는 IPv4 기준 40바이트(IP 20 + TCP 20)다.

여기서 중요한 점이 하나 있다. MSS는 송신자가 한 세그먼트에 담는 데이터 양을 결정하지만, 그게 그대로 IP 패킷 하나가 된다는 보장은 없다. UDP나 다른 프로토콜은 MSS 같은 게 없다. 그래서 UDP 큰 패킷은 IP 단편화를 거쳐 쪼개져 나간다. TCP가 단편화를 거의 겪지 않는 이유는 MSS로 미리 크기를 맞추기 때문이다.

## IP 단편화는 왜 피해야 하는가

IP 헤더에는 단편화를 위한 필드가 있다. Identification, Flags(DF, MF), Fragment Offset이다. 송신 IP가 자기 MTU보다 큰 패킷을 만들거나, 중간 라우터가 다음 홉의 MTU를 넘는 패킷을 받으면 쪼개서 보낸다. 받는 쪽 IP 계층에서 다시 합친다. 동작 자체는 표준이다.

문제는 실무에서 단편화가 거의 항상 손해라는 것이다.

첫째, 조각 중 하나만 잃어버려도 전체 패킷이 무용지물이 된다. 4개로 쪼갠 패킷이 있는데 그중 두 번째 조각이 떨어지면, 나머지 3개가 다 도착해도 받는 쪽은 원본을 복원하지 못한다. TCP라면 결국 원본 세그먼트 전체를 재전송해야 한다. 손실률이 1%여도 단편화된 큰 패킷의 실제 손실률은 4~5%로 뛴다.

둘째, 받는 쪽이 조각을 모으는 동안 메모리에 들고 있어야 한다. 누군가 일부러 조각을 흘리면 받는 쪽 메모리가 차오른다. 이게 옛날부터 알려진 단편화 기반 공격이다. 그래서 요즘 방화벽과 보안 장비는 단편화된 패킷을 보수적으로 다룬다. 일부는 그냥 버린다.

셋째, ECMP나 LAG 같은 부하분산 환경에서 첫 조각과 나머지 조각이 다른 경로로 가는 경우가 있다. 5-tuple 해시가 첫 조각에만 적용 가능하기 때문이다. 결과적으로 어떤 조각은 빠르고 어떤 조각은 느려져서 받는 쪽에서 reassembly 타임아웃이 터진다.

요즘 리눅스 커널은 TCP 패킷에 IP DF(Don't Fragment) 비트를 기본으로 켠다. 단편화 자체를 막고 PMTUD에 의존한다. 그래서 PMTUD가 깨지면 통신이 그냥 멈추는 일이 벌어진다.

## Path MTU Discovery

### 동작 원리

PMTUD는 아주 단순한 메커니즘이다. 송신자가 IP DF 비트를 켠 채로 큰 패킷을 보낸다. 중간 라우터가 자기 출력 인터페이스 MTU보다 큰 DF 패킷을 받으면 단편화를 못 한다. 그래서 패킷을 버리고 송신자에게 ICMP 메시지를 돌려준다.

이 ICMP 메시지가 ICMP Type 3, Code 4 — "Destination Unreachable: Fragmentation Needed and Don't Fragment was Set"이다. 이름 그대로다. 이 메시지에는 다음 홉의 MTU 값이 적혀 있다. 송신자는 그 값을 보고 자기 라우팅 캐시에 PMTU를 갱신한 뒤, TCP 세그먼트 크기를 줄여서 다시 보낸다.

```
[Host A] --1500-- [R1] --1500-- [R2] --1400-- [R3] --1500-- [Host B]

A가 1500바이트 DF 패킷 송신
R2가 R3로 보내려다 1400 MTU 초과 인지
R2 → A로 ICMP Type 3 Code 4 (next-hop MTU=1400)
A가 PMTU=1400으로 갱신, 1400 이하로 재전송
```

리눅스에서는 `ip route get <대상>`으로 현재 경로의 PMTU 추정값을 볼 수 있다. `mtu`로 표시되는 값이 그것이다.

```bash
ip route get 10.20.30.40
# 10.20.30.40 via 10.0.0.1 dev eth0 src 10.0.1.5 mtu 1400
```

### 캐시와 만료

PMTU는 라우팅 캐시에 일정 시간 유지된다. 리눅스는 기본 10분이다. 만료되면 다시 1500으로 되돌리고 PMTUD를 다시 시작한다. 그래서 가끔씩 한 번 끊겼다가 회복되는 패턴이 나타난다. 캐시 만료 직후 큰 패킷을 보내고, 어딘가에서 막히고, ICMP를 받아 다시 갱신하는 사이클이다.

```bash
# 라우팅 캐시 보기
ip route show cache

# 캐시 비우기 (디버깅 시)
ip route flush cache
```

## PMTUD 블랙홀

### 무엇이 문제인가

PMTUD가 동작하려면 두 가지가 필요하다. 송신자가 DF 비트를 켜고 큰 패킷을 보낼 수 있어야 하고, 라우터가 보내는 ICMP Type 3 Code 4가 송신자까지 돌아와야 한다. 둘 중 하나라도 깨지면 PMTUD는 동작하지 않는다.

실제 환경에서 자주 깨지는 건 두 번째다. 보안 장비, 방화벽, 클라우드 보안 그룹, 일부 라우터에서 ICMP를 통째로 막는 경우가 흔하다. "ICMP는 ping이고 ping은 보안에 안 좋으니까 다 막자"는 식이다. 이게 PMTUD를 죽인다.

증상은 일관된다. 작은 패킷은 다 통한다. 핸드셰이크도 잘 끝난다. 그러다 큰 데이터를 주고받기 시작하는 순간 통신이 멈춘다. 송신자는 큰 패킷을 보낸다 → 중간 라우터가 버린다 → ICMP는 차단되어 돌아오지 않는다 → 송신자는 PMTU를 갱신하지 못한 채 같은 크기로 재전송한다 → 또 버려진다 → 무한 반복이다. TCP 재전송 타임아웃이 누적되다가 결국 RST로 끝난다.

이 현상을 PMTUD 블랙홀이라고 부른다. 패킷이 검은 구멍에 빨려 들어간 것처럼 흔적도 없이 사라지기 때문이다.

### 진단

블랙홀을 의심해야 할 정황은 분명하다.

- HTTP GET처럼 응답 크기가 작은 요청은 잘 되는데, POST나 큰 응답이 오는 요청만 멈춘다.
- ping은 잘 되는데 SSH 로그인은 비밀번호 입력 후 멈춘다(키 교환 패킷이 큰 시점).
- TLS 핸드셰이크의 ClientHello는 가는데 ServerHello에서 멈춘다(인증서 체인이 큰 경우).

진단할 때 쓰는 건 결국 패킷 크기를 바꿔가며 보내는 방법이다. ping에 DF 비트를 켜고 크기를 늘려가며 어디서 끊기는지 본다.

```bash
# 리눅스에서 DF 켜고 큰 패킷 보내기
ping -M do -s 1472 대상호스트
# 1472 + 8(ICMP 헤더) + 20(IP 헤더) = 1500
# 성공하면 "100% packet loss" 없이 응답이 옴

ping -M do -s 1500 대상호스트
# 보통 여기서 막힘
# "Frag needed and DF set (mtu = 1400)" 메시지가 나오면 PMTUD는 정상
# 아무 응답 없이 100% 손실이면 블랙홀 의심

# 이분탐색으로 실제 PMTU 찾기
ping -M do -s 1372 대상호스트   # 1372 + 28 = 1400
ping -M do -s 1373 대상호스트   # 1401, 막히면 PMTU=1400
```

`tracepath`도 유용하다. 경로를 따라가며 어느 홉에서 PMTU가 줄어드는지 보여준다.

```bash
tracepath 대상호스트
# 1?: [LOCALHOST]                        pmtu 1500
# 1:  10.0.0.1                           1.234ms
# 2:  10.10.0.1                          asymm  3   2.456ms pmtu 1400
# 2:  10.10.0.1                          3.123ms
# ...
```

### 회피 수단

이상적인 해법은 ICMP Type 3 Code 4를 허용하는 것이다. 보안상 모든 ICMP를 막더라도 이 한 종류는 통과시켜야 한다. AWS Security Group 같은 곳에서도 ICMP의 "destination unreachable - fragmentation required" 항목을 인바운드 허용으로 추가하는 게 정석이다.

```
# iptables에서 ICMP Type 3 Code 4만 허용
iptables -A INPUT -p icmp --icmp-type fragmentation-needed -j ACCEPT
```

ICMP를 어떻게 해도 풀 수 없는 환경이라면(타사 네트워크 너머라거나, 정책상 절대 안 된다거나) 차선책이 PLPMTUD와 MSS Clamping이다.

PLPMTUD(Packetization Layer Path MTU Discovery, RFC 4821)는 ICMP에 의존하지 않고 PMTU를 추정한다. TCP가 큰 세그먼트를 보내고 응답이 없으면 PMTU 문제로 의심해 세그먼트 크기를 줄여 재시도하는 방식이다. 리눅스에서는 `net.ipv4.tcp_mtu_probing`으로 켤 수 있다.

```bash
# 0=비활성, 1=PMTUD 실패 시에만 활성, 2=항상 활성
sysctl -w net.ipv4.tcp_mtu_probing=1
```

값을 1로 두면 평소엔 PMTUD에 의존하다가 블랙홀 패턴(재전송 누적)이 감지되면 PLPMTUD로 전환한다. 운영 서버에서 안전하게 쓸 수 있는 값이다. 2로 두면 처음부터 PLPMTUD로 동작하는데, 정상 환경에서는 약간의 throughput 손해가 있다.

## VPN·터널 환경에서 MTU가 줄어드는 이유

### 캡슐화 오버헤드

VPN과 터널은 원래 IP 패킷을 다른 IP 패킷의 페이로드로 감싸서 보낸다. 이 과정에서 헤더가 추가로 붙는다. 헤더만큼 페이로드 자리가 줄어든다.

| 터널 종류 | 추가 오버헤드 | 일반적인 내부 MTU |
|---|---|---|
| GRE | 24바이트 (IP 20 + GRE 4) | 1476 |
| GRE + IPsec Transport | 56바이트 안팎 | 1438 |
| IPsec ESP Transport (AES-CBC) | 50~73바이트 | 1438 |
| IPsec ESP Tunnel (AES-CBC) | 73~118바이트 | 1400 근처 |
| WireGuard | 60바이트 | 1420 |
| OpenVPN UDP | 50~60바이트 | 1450 근처 |
| PPPoE | 8바이트 | 1492 |

IPsec ESP Tunnel 모드는 변동폭이 크다. 외부 IP 헤더 20, ESP 헤더 8, IV 16(AES-CBC), 패딩 0~15, 패드 길이 1, 다음 헤더 1, 무결성 ICV 12, 그리고 내부 IP 헤더 20이 다 들어간다. 거기에 AES-GCM이냐 AES-CBC냐, NAT-T가 끼어 UDP 캡슐(8바이트)이 더 붙느냐에 따라 또 달라진다. 상수 값을 외워봐야 환경마다 어긋나니, 실제 환경에서 측정하는 게 빠르다.

```bash
# IPsec 터널 인터페이스 MTU 보기
ip link show ipsec0
# mtu 1400 ...
```

### NAT-T가 끼면 더 줄어든다

IPsec ESP는 IP 프로토콜 50번을 쓴다. NAT 장비를 통과할 때 포트가 없는 IP 프로토콜은 NAT 매핑이 안 된다. 그래서 IPsec은 NAT-T(NAT Traversal)를 통해 ESP 패킷을 UDP 4500 안에 한 번 더 감싼다. 여기서 UDP 헤더 8바이트와 NAT-T 마커 4바이트가 더 붙는다.

집에서 회사 VPN을 쓸 때 MTU가 1380쯤으로 잡히는 게 보통 이 조합 때문이다. 이더넷 1500에서 ESP Tunnel 오버헤드를 빼고 NAT-T까지 더 빼면 1380이 된다. 클라우드 VPC 간 Site-to-Site VPN도 비슷한 값이 나온다. AWS의 가상 사설 게이트웨이 권장 MTU가 1436이고, 그 안에서 SSH 패킷이 통과하려면 클라이언트 측에서 또 한 번 마진을 둬야 한다.

### 외부 MTU와 내부 MTU

VPN 인터페이스의 MTU가 1400이라는 건 그 인터페이스 위에서 동작하는 IP 패킷이 1400을 넘으면 안 된다는 뜻이다. 1400을 넘는 IP 패킷이 들어오면 VPN은 단편화하거나(DF 비트가 없을 때), DF가 있으면 내부적으로 ICMP Type 3 Code 4를 만들어서 송신자에게 알린다. 이 ICMP가 NAT나 방화벽에서 막히면 VPN 안쪽에서 PMTUD 블랙홀이 발생한다.

문제는 VPN을 쓰는 사용자가 보통 ICMP 차단 환경 너머에 있다는 것이다. 사내망 보안 정책, ISP 차원의 ICMP rate limit, 클라우드 SG의 기본 설정 등이 다 ICMP를 막는다. 그래서 VPN 환경에서는 PMTUD에 기대지 말고 처음부터 MSS를 줄여 박는 게 운영의 지혜다.

## MSS Clamping

### 무엇을 하는가

MSS Clamping은 라우터나 게이트웨이가 통과하는 TCP SYN 패킷의 MSS 옵션을 강제로 낮춰 쓰는 기법이다. 핸드셰이크 시점에 양쪽이 광고하는 MSS를 라우터가 가로채서 자기가 원하는 값으로 깎아 버린다. 결과적으로 그 연결은 깎인 MSS로 동작하고, 이후로 큰 패킷이 발생하지 않으니 PMTUD가 필요 없어진다.

이게 VPN/터널 환경의 사실상 표준 회피책이다. 모든 클라우드 VPN 가이드에 등장한다. AWS Direct Connect, Azure VNet Gateway, GCP Cloud VPN 모두 MSS Clamping을 권장하거나 자동 적용한다.

### 리눅스 iptables 설정

가장 흔한 설정이다. TCPMSS 타깃과 `--clamp-mss-to-pmtu`를 함께 쓰는 게 표준이다.

```bash
# 출구 인터페이스 PMTU에 맞춰 자동으로 MSS 깎기
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
    -j TCPMSS --clamp-mss-to-pmtu

# 또는 고정 값으로 깎기 (PMTU를 못 믿을 때)
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
    -o ipsec0 -j TCPMSS --set-mss 1360
```

`--clamp-mss-to-pmtu`가 더 깔끔해 보이지만 함정이 있다. 출구 인터페이스의 MTU만 고려한다. 그 너머의 PMTU는 모른다. VPN 인터페이스가 1400이고 그 안쪽 경로 어딘가에 1380 구간이 있으면 여전히 PMTUD에 의존하게 된다. 이런 경우엔 `--set-mss`로 명시적인 값을 박는 게 안전하다.

값을 정할 때는 보수적으로 잡는 게 좋다. VPN 인터페이스 MTU에서 40바이트(IPv4+TCP)를 뺀 값에서 추가로 20~40바이트 정도 마진을 둔다. 1400 MTU라면 MSS는 1320이나 1340 정도다. 약간 비효율적이지만 블랙홀보다는 낫다.

### 방향성에 주의

TCPMSS는 SYN과 SYN/ACK 양쪽 다 잡아야 한다. 한쪽만 잡으면 그 방향의 광고 MSS만 낮아지고 반대 방향은 그대로다. TCP MSS는 광고한 쪽이 받을 패킷 크기를 의미하기 때문에, 양쪽이 다 작은 MSS를 광고해야 양방향이 다 작은 패킷으로 흐른다. iptables FORWARD 체인에 `--tcp-flags SYN,RST SYN` 매칭으로 걸면 SYN과 SYN/ACK 둘 다 잡힌다(RST가 없는 모든 SYN 변종 매칭).

### Nginx와 ALB 같은 L7 종단점

요즘은 종단점이 라우터가 아닌 경우가 많다. ALB, NLB, CloudFront, Nginx 같은 곳이다. 여기서 MSS Clamping을 어떻게 거는지가 환경마다 다르다.

Nginx 자체는 MSS를 직접 조절하는 옵션이 없다. 호스트 OS의 TCP_MAXSEG socket option을 통해 설정해야 한다. 일반적으로는 OS 레벨의 라우팅 테이블에 advmss를 박는 방법을 쓴다.

```bash
# 특정 게이트웨이로 가는 경로에 MSS 광고 값 강제
ip route add 10.0.0.0/8 via 10.20.0.1 advmss 1360

# 기존 경로 수정
ip route change default via 10.20.0.1 advmss 1360
```

이렇게 하면 그 경로로 나가는 모든 TCP 연결이 MSS 1360으로 광고한다. AWS의 EC2 인스턴스에서 Direct Connect를 통해 온프레미스로 나가는 경로가 있고 그 경로의 PMTU가 1380이라면, advmss 1340 정도를 박는다.

### 검증

설정 후 실제 MSS가 깎이는지 확인해야 한다. tcpdump로 SYN을 떠 보면 된다.

```bash
tcpdump -i eth0 -n -nn 'tcp[tcpflags] & tcp-syn != 0' -v
# Flags [S], ... options [mss 1360,sackOK,TS val ...]
#                                  ^^^^
#                              여기 값이 깎인 값으로 나와야 함
```

실제 데이터 흐름이 작은 패킷으로 흐르는지도 확인하는 게 좋다.

```bash
# 큰 데이터 전송 후 패킷 크기 분포 보기
tcpdump -i eth0 -n -nn 'host 대상호스트 and tcp' -ttt
# length 1360 같은 값으로 일정하게 나오면 정상
# length 1500이 섞여 있으면 어딘가에서 clamp가 안 먹은 것
```

## 실제로 만났던 사례

### 사례 1: Site-to-Site VPN 너머 깃 푸시 멈춤

본사와 자회사 망을 IPsec Site-to-Site VPN으로 연결한 환경이었다. 자회사 개발자가 본사 GitLab으로 푸시하면 작은 변경은 잘 가는데 큰 브랜치를 푸시하면 50% 진행 후 멈춘다고 했다.

`tracepath`를 떠 보니 자회사 내부에서는 1500이 잡히는데 VPN 통과 후 1400이 됐다. 그런데 자회사 측 송신자는 PMTU를 1500으로 알고 큰 패킷을 보내고 있었다. ICMP는 클라우드 측 SG에서 막혀 있었다. 정확히 PMTUD 블랙홀이었다.

자회사 게이트웨이에 `iptables -t mangle ... TCPMSS --set-mss 1340`을 박아서 해결했다. ICMP 차단 정책은 그대로 두고 MSS Clamping으로만 우회했다. 그 뒤로 같은 종류의 문의가 사라졌다.

### 사례 2: Kubernetes Pod에서 외부 API 호출 멈춤

CNI로 Calico를 쓰는 클러스터에서 일부 외부 API 호출이 멈춘다는 이슈였다. 그것도 응답 본문이 큰 호출만. Calico의 IP-in-IP 모드를 쓰고 있었고, 그 환경의 Pod 인터페이스 MTU가 1480(1500 - 20 IP-in-IP)이었다.

문제는 Pod 안의 애플리케이션이 호스트 인터페이스의 MTU 1500을 인식해서 MSS 1460을 광고했다는 점이다. 외부 응답이 1460 페이로드로 돌아오면 IP 헤더 포함 1480이 되는데, 이게 IP-in-IP 캡슐로 감싸지면 1500이 돼서 호스트 출력 인터페이스를 통과는 했다. 하지만 일부 외부 망 구간에서 이미 1500을 못 받는 상태였다. 그쪽에서 ICMP를 보내도 클러스터 외부로는 갔지만 Pod까지 전달되지 않았다.

Calico의 `mtu` 설정값을 1450으로 명시하고 노드들을 재시작한 뒤 해결됐다. Calico는 그 값을 Pod 인터페이스에 적용하고, Pod의 MSS도 1410으로 광고하게 된다. 외부 망의 어떤 구간이 좁아도 단편화나 블랙홀이 발생하지 않는다.

### 사례 3: WireGuard 위에서 DB 마이그레이션 행

원격에서 WireGuard로 사내망에 붙어 DB 마이그레이션을 돌리는데, 큰 SQL 파일을 적용하는 도중에 클라이언트가 멈춘다는 문제였다. 작은 쿼리는 다 잘 되는데 길이가 긴 쿼리에서 hang이 걸렸다.

WireGuard 인터페이스 MTU는 1420으로 잡혀 있었다. 그런데 클라이언트가 모바일 핫스팟을 쓰는 환경이었고, 그 너머 PMTU는 1380이었다. WireGuard는 PMTUD 정보를 자기 안쪽으로 전달하지 못한다. WG 위로 올라온 IP 패킷이 1420 이하면 WG는 자기가 알아서 외부 UDP 패킷을 만든다. 그게 1500을 넘으면 WG의 외부 송신부가 단편화하거나 ICMP를 받게 되는데, 모바일 망 ICMP가 신뢰할 만한 게 못 됐다.

해결은 WireGuard 인터페이스의 MTU를 1280으로 낮추는 것이었다. IPv6 최소 MTU와 같은 값이라 어디서든 통한다. 처리량이 약간 줄지만 마이그레이션이 안 끝나는 것보단 낫다.

```ini
# wg0.conf
[Interface]
MTU = 1280
```

## 정리하며 챙길 것

MTU·MSS 문제의 90%는 두 가지로 줄어든다. PMTUD 블랙홀과 터널 캡슐화 오버헤드다. 그리고 둘 다 MSS Clamping 한 줄로 대부분 해결된다.

새 환경을 설계하거나 인계받았을 때 한 번쯤 확인해야 할 것들이 있다. 출구로 나가는 모든 경로의 실제 PMTU를 `tracepath`나 `ping -M do`로 측정해 본다. VPN/터널 인터페이스의 MTU가 합리적인지 본다. 보안 그룹이나 방화벽이 ICMP Type 3 Code 4를 통과시키는지 본다. 통과시키지 못하는 구간이 있다면 그 출입구에 MSS Clamping을 박는다.

평소에는 정말 신경 쓸 일이 없는 영역이지만, 한 번 어긋나면 며칠을 잡아먹는다. 패킷 캡처에 큰 패킷이 무한 재전송되는 패턴이 보이면 가장 먼저 의심해야 할 것이 이쪽이다.
