---
title: 공인 IP와 사설 IP
tags: [network, vpc, aws, linux, tcp]
updated: 2026-09-11
---

# 공인 IP와 사설 IP

## RFC 1918 사설 IP 대역

인터넷에 직접 라우팅되지 않는 IP 대역을 RFC 1918에서 세 개로 정의했다.

| 대역 | CIDR 표기 | 주소 범위 | 총 주소 수 |
|------|-----------|-----------|-----------|
| 10.0.0.0/8 | A클래스 전체 | 10.0.0.0 ~ 10.255.255.255 | 약 1670만 |
| 172.16.0.0/12 | B클래스 일부 | 172.16.0.0 ~ 172.31.255.255 | 약 104만 |
| 192.168.0.0/16 | C클래스 일부 | 192.168.0.0 ~ 192.168.255.255 | 약 6만 5천 |

이 세 대역 외의 주소를 내부 네트워크에 쓰면 외부 트래픽과 충돌이 생긴다. 사내 네트워크에 1.2.3.0/24를 잘못 쓰면, 해당 대역을 실제 소유한 외부 서버로 나가는 트래픽이 내부에서 막힌다.

## 공인 IP와 사설 IP 차이

공인 IP는 IANA나 각 지역 RIR에서 할당받아 인터넷 라우팅 테이블에 올라간 주소다. 인터넷 어디서든 해당 주소로 패킷을 보낼 수 있다.

사설 IP는 RFC 1918 대역이다. 인터넷 라우터는 이 주소를 목적지로 받으면 버린다. BGP 라우팅 테이블에 없기 때문이다. 사설 IP는 내부 네트워크 안에서만 유효하다.

같은 사설 IP가 여러 네트워크에서 동시에 사용돼도 문제없다. A회사 내부 192.168.1.100과 B회사 내부 192.168.1.100은 서로 다른 네트워크에 존재하므로 충돌하지 않는다.

## 특수 목적 주소 대역

RFC 1918 외에도 라우팅되지 않거나 특수 용도로 예약된 대역들이 있다.

**루프백 (127.0.0.0/8)**

127.0.0.1이 localhost로 가장 많이 쓰이지만, 127.0.0.0/8 전체가 루프백으로 예약돼 있다. 패킷이 네트워크 카드로 나가지 않고 OS 내부에서 처리된다. 로컬 서버 테스트나 프로세스 간 통신에 쓴다.

**링크-로컬 (169.254.0.0/16)**

DHCP 서버에서 IP를 못 받았을 때 OS가 자동으로 169.254.x.x를 할당한다. Windows에서는 APIPA(Automatic Private IP Addressing)라고 부른다. 서버에서 `ip addr`로 169.254.x.x 주소가 보이면 DHCP 실패나 네트워크 구성 문제를 의심해야 한다.

AWS에서는 인스턴스 메타데이터 서버(169.254.169.254)로 링크-로컬을 쓴다. 이 주소가 라우팅되지 않는 특성을 이용해 같은 물리 호스트의 인스턴스에서만 접근 가능하게 격리한다.

**멀티캐스트 (224.0.0.0/4)**

224.0.0.0 ~ 239.255.255.255 대역이다. 특정 그룹에 가입된 호스트들에게만 패킷을 전달한다. OSPF 라우터는 224.0.0.5(AllSPFRouters)와 224.0.0.6(AllDRRouters)을 쓰고, mDNS(Bonjour)는 224.0.0.251을 쓴다. 브로드캐스트(255.255.255.255)와 달리 대역폭 낭비가 없어서 IPTV나 스트리밍 배포에 쓴다.

**CGNAT 전용 (100.64.0.0/10)**

RFC 6598에서 ISP 내부 NAT 전용으로 정의했다. 일반 사설 IP 대역(RFC 1918)과는 구분된다. 자세한 내용은 아래 CGNAT 섹션에서 다룬다.

## IP 주소 확인 명령어

서버나 로컬 환경에서 IP를 확인할 때 `ifconfig`보다 `ip` 명령이 표준이다. `ifconfig`는 `net-tools` 패키지에 포함돼 있고 최신 배포판에는 기본 설치가 안 되는 경우가 많다.

```bash
# 네트워크 인터페이스와 할당된 IP 전체 목록
ip addr show

# 특정 인터페이스만 (eth0, ens3, enp0s3 등)
ip addr show eth0

# 라우팅 테이블 전체
ip route show

# 기본 게이트웨이만
ip route show default
```

`ip addr show` 출력 예시:
```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN
    inet 127.0.0.1/8 scope host lo

2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9001 qdisc mq state UP
    inet 10.0.1.45/24 brd 10.0.1.255 scope global dynamic eth0
```

`inet` 다음에 나오는 주소가 할당된 IP다. `scope global`이면 일반 통신에 쓰이는 주소고, `scope host`는 루프백이다. `scope link`가 나오면 링크-로컬 주소다.

외부에서 실제로 보이는 공인 IP는 내부 명령어로는 알 수 없다. NAT 뒤에 있으면 `ip addr`에는 사설 IP만 나온다.

```bash
# 외부에서 보이는 공인 IP 확인
curl ifconfig.me

# 또는 JSON 응답이 필요한 경우
curl -s https://api.ipify.org?format=json
```

CGNAT 환경(LTE, 공유기 여러 단)에서는 `curl ifconfig.me`로 나오는 IP와 `ip addr`로 보이는 IP가 다르다. 중간에 NAT 레이어가 하나 이상 끼어 있는 상태다.

## 사설 IP로 인터넷 통신이 불가능한 이유

인터넷 백본 라우터는 RFC 1918 대역으로 오는 패킷을 포워딩하지 않는다. 관행이 아니라 RFC 1918 자체의 요구사항이다.

192.168.1.100에서 google.com으로 요청을 보내는 경우를 따라가 보면:

1. 사설 IP 192.168.1.100에서 구글 서버(142.250.x.x)로 패킷이 나간다
2. 구글 서버는 192.168.1.100으로 응답을 보내려 한다
3. 인터넷에 192.168.0.0/16을 소유한 AS(Autonomous System)가 없으므로 응답 패킷이 어디로 가야 할지 모른다
4. 패킷이 드롭된다

요청은 나가더라도 응답이 돌아오는 경로 자체가 없다.

## NAT 의존 구조

이 문제를 해결하는 방법이 NAT(Network Address Translation)다. 라우터가 출발지 IP를 사설 IP에서 공인 IP로 바꿔서 내보낸다.

```
내부 PC: 192.168.1.100:51234 → google.com:443
                    ↓ NAT
라우터 공인 IP: 203.0.113.45:51234 → google.com:443
```

응답이 돌아오면 라우터는 NAT 테이블을 보고 203.0.113.45:51234를 내부 192.168.1.100:51234로 변환해서 전달한다.

NAT 테이블 엔트리 예시:

```
사설 IP:포트              공인 IP:포트              목적지:포트               상태
192.168.1.100:51234    203.0.113.45:51234    142.250.10.100:443    ESTABLISHED
192.168.1.101:50123    203.0.113.45:50123    172.217.5.4:80        ESTABLISHED
```

NAT의 핵심은 이 상태 테이블이다. 연결은 항상 내부에서 외부로 시작해야 테이블 엔트리가 생긴다. 외부에서 먼저 시작되는 연결은 엔트리가 없어서 어느 내부 호스트로 보내야 할지 판단할 수 없다. 이 때문에 사설 IP 뒤의 서버에 외부에서 직접 접근하려면 포트 포워딩을 따로 설정해야 한다.

## NAT 엔트리 고갈 트러블슈팅

Linux 커널은 NAT 연결 추적에 `nf_conntrack` 모듈을 쓴다. 추적 가능한 최대 연결 수가 정해져 있고, 이걸 넘으면 새로운 연결이 안 된다.

고갈 징후는 커널 로그에 나타난다:

```bash
dmesg | grep nf_conntrack
# nf_conntrack: table full, dropping packet 가 반복되면 고갈 상태
```

현재 상태 확인:

```bash
# 현재 추적 중인 연결 수
cat /proc/sys/net/nf_conntrack_count

# 최대 허용 연결 수
cat /proc/sys/net/nf_conntrack_max

# 연결 추적 테이블 전체 덤프 (conntrack 패키지 필요)
conntrack -L

# 특정 소스 IP의 연결만 필터링
conntrack -L --src 192.168.1.100

# 상태별 연결 수 집계
conntrack -L | awk '{print $4}' | sort | uniq -c | sort -rn
```

`conntrack -L` 출력 예시:

```
tcp      6 86400 ESTABLISHED src=192.168.1.100 dst=142.250.10.100 sport=51234 dport=443 \
  src=142.250.10.100 dst=203.0.113.45 sport=443 dport=51234 [ASSURED] mark=0 use=1
tcp      6 60 TIME_WAIT src=192.168.1.101 dst=172.217.5.4 sport=50123 dport=80 \
  src=172.217.5.4 dst=203.0.113.45 sport=80 dport=50123 [ASSURED] mark=0 use=1
```

`TIME_WAIT` 상태가 대량으로 쌓여 있으면 연결은 끝났지만 엔트리가 아직 남아 있는 상태다. HTTP 단기 연결이 많은 서버에서 자주 발생한다.

최대값을 늘리는 방법:

```bash
# 현재 세션에서만 적용 (재부팅 시 초기화)
sysctl -w net.nf_conntrack_max=131072

# 영구 적용
echo "net.nf_conntrack_max = 131072" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

적절한 최대값은 RAM에 따라 다르다. 엔트리 하나당 약 300바이트를 쓴다. 131072개면 약 38MB다. 무작정 크게 잡으면 메모리 압박이 생긴다.

`TIME_WAIT` 축적 문제는 타임아웃도 줄일 수 있다:

```bash
# TIME_WAIT 타임아웃 확인
cat /proc/sys/net/netfilter/nf_conntrack_tcp_timeout_time_wait
# 기본값 120초

# 줄이기
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_time_wait=60
```

클라우드 환경에서 NAT Gateway를 쓰는 경우 EC2 인스턴스 커널 수준이 아니라 AWS 관리형 NAT에서 엔트리 관리가 이뤄진다. 이 경우 `conntrack` 명령으로 직접 확인이 안 되고, CloudWatch의 `ErrorPortAllocation` 메트릭으로 포트 고갈 여부를 확인한다.

## 홈 라우터에서 사설 IP 할당 동작 방식

홈 라우터는 DHCP 서버를 내장해서 내부 기기에 사설 IP를 배포한다.

기기를 연결하면 아래 순서로 진행된다:

1. 기기가 255.255.255.255로 DHCP Discover 브로드캐스트를 보낸다
2. 라우터 DHCP 서버가 192.168.1.100/24, 게이트웨이 192.168.1.1, DNS 정보를 담은 DHCP Offer를 돌려준다
3. 기기가 DHCP Request로 수락한다
4. 라우터가 DHCP ACK로 확정한다

라우터는 대부분 192.168.0.0/24나 192.168.1.0/24를 기본으로 쓴다. 이 대역의 첫 번째 주소(.1)를 게이트웨이로, 나머지를 풀로 배포한다.

기기는 할당받은 IP로 내부 통신은 직접 처리하고, 외부로 나가는 트래픽은 게이트웨이(라우터)로 보낸다. 라우터가 NAT를 수행해서 공인 IP로 바꿔 내보낸다.

## VPC CIDR 설계 실수로 사설 IP 고갈

클라우드 환경에서 VPC를 처음 만들 때 CIDR를 너무 작게 잡는 실수가 흔하다.

AWS에서 VPC를 192.168.0.0/24로 잡으면 총 256개 주소 중 실제 쓸 수 있는 건 251개다(AWS가 5개 예약). 서브넷을 나누면 더 줄어든다.

```
VPC: 192.168.0.0/24 (총 251개 사용 가능)
├── 퍼블릭 서브넷 A: 192.168.0.0/27  (27개)
├── 퍼블릭 서브넷 B: 192.168.0.32/27 (27개)
├── 프라이빗 서브넷 A: 192.168.0.64/27 (27개)
└── 프라이빗 서브넷 B: 192.168.0.96/27 (27개)
```

각 서브넷에 27개밖에 없는데 Auto Scaling으로 인스턴스 40개를 띄우려 하면 IP가 부족해서 새 인스턴스가 뜨지 않는다. AWS 콘솔에서 아래 에러가 나온다:

```
Failed to create instance: The specified subnet does not have enough free IP addresses
to create new network interface(s). Requested count: 1, available: 0.
```

Terraform으로 ECS 태스크나 EC2를 배포할 때도 같은 상황이 된다:

```
Error: InvalidSubnet.InsufficientFreeAddresses: There aren't enough free addresses
in the subnet to run 3 instances. Try launching an instance in a different subnet.
```

VPC CIDR는 생성 후 변경이 안 된다. AWS는 보조 CIDR 추가를 지원하지만 기본 CIDR 수정은 불가능하다.

VPC 피어링을 연결할 때 CIDR가 겹치면 아예 연결 자체가 거부된다:

```
Error: InvalidVpcPeerConnection.NotAllowed: The CIDR range of the VPC you are
connecting to is overlapping with the CIDR range of your VPC. CIDR block
10.0.0.0/16 conflicts with existing CIDR block 10.0.0.0/16.
```

AWS CLI로 시도하면:

```
An error occurred (InvalidVpcPeerConnection.NotAllowed) when calling the
CreateVpcPeeringConnection operation: The CIDR block of the VPC you are peering
with conflicts with the CIDR block of your VPC.
```

피어링 수락 후 라우팅 테이블에 추가하려 할 때 겹치는 CIDR가 이미 있으면:

```
An error occurred (RouteAlreadyExists) when calling the CreateRoute operation:
The route identified by 10.0.0.0/16 already exists.
```

실무에서 보통 쓰는 VPC CIDR:

```
본사 VPC:      10.0.0.0/16
개발 VPC:      10.1.0.0/16
스테이징 VPC:  10.2.0.0/16
온프레미스:    10.100.0.0/16
```

처음부터 전체 IP 계획을 잡고 /16 단위로 잘라 쓰면 피어링이나 Transit Gateway 연결 시 충돌을 피할 수 있다. 192.168.0.0/16 같은 흔한 대역은 온프레미스 네트워크와 겹칠 가능성이 높아서 클라우드 VPC에는 10.0.0.0/8 대역을 쓰는 게 낫다.

## CGNAT 이슈

CGNAT(Carrier-Grade NAT)는 ISP가 고객에게도 사설 IP를 주는 구조다. IPv4 주소가 고갈되면서 나온 방식이다.

일반 NAT는 사설 IP를 공인 IP로 바꾸지만, CGNAT는 사설 IP를 ISP 내부 IP로 바꾸고 그다음에 다시 공인 IP로 바꾼다.

RFC 6598에서 CGNAT용으로 100.64.0.0/10 대역을 정의했다. RFC 1918과 달리 ISP용 NAT에만 쓰라고 예약한 대역이다.

```
휴대폰: 192.168.x.x (기기 로컬 IP)
  ↓ (기지국)
CGNAT: 100.64.x.x (통신사 내부 IP)
  ↓
인터넷: 203.0.x.x (공인 IP, 여러 가입자가 공유)
```

CGNAT 환경에서 생기는 실질적인 문제들이 있다.

**포트 포워딩 불가**: 공인 IP를 여러 가입자가 공유하므로 특정 가입자에게 포트를 포워딩할 방법이 없다. 집에서 서버를 운영하려 해도 외부에서 접근할 수 없다.

**P2P 연결 어려움**: WebRTC나 게임에서 피어 간 직접 연결을 시도할 때, CGNAT가 두 겹으로 쌓이면 STUN으로도 뚫기 어렵다. TURN 릴레이 서버로 우회해야 한다.

**로그 추적 문제**: 공인 IP 하나를 수백 명이 공유하면 특정 시점에 어떤 가입자가 그 IP를 썼는지 ISP 로그 없이는 알 수 없다. 보안 인시던트 추적이 복잡해진다.

**소켓 포트 고갈**: 하나의 공인 IP에서 쓸 수 있는 포트는 65535개인데, 수백 명이 공유하면 포트가 부족해질 수 있다. 세션이 많은 환경에서 간헐적으로 연결 실패가 생긴다.

LTE/5G 환경에서 `curl ifconfig.me`로 공인 IP를 확인하면 같은 기지국의 다른 사람과 동일한 IP가 나오는 경우가 있다. `ip addr`로 확인되는 로컬 IP와 외부에서 보이는 IP가 다르고, 중간에 CGNAT 레이어가 끼어 있는 상황이다.
