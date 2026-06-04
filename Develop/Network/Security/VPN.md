---
title: VPN - IPSec, WireGuard, OpenVPN과 실무 운영
tags: [network, vpn, ipsec, wireguard, openvpn, ikev2, aws-vpn, mtu, split-tunnel]
updated: 2026-06-04
---

# VPN - IPSec, WireGuard, OpenVPN과 실무 운영

처음 회사 IDC와 AWS VPC를 연결하라는 요구를 받았을 때, 막연히 "VPN 터널 하나 뚫으면 되겠지"라고 생각했다. 결과는 처참했다. IKE 협상이 자꾸 떨어지는데 원인을 못 찾아서 사흘을 헤맸고, 겨우 연결되니까 이번엔 일부 패킷만 사라지는 현상이 생겼다. 알고 보니 MTU 문제였다. VPN은 OSI 3계층(또는 그 아래)에서 동작하는 터널인데, 단순히 "암호화된 통로" 정도로만 이해하고 있으면 실무에서 무조건 막힌다.

이 문서는 L3 레벨의 VPN — IPSec, WireGuard, OpenVPN — 에 대한 내용이다. TLS_HTTPS는 응용 계층 보안이고, 여기서 다루는 건 패킷 자체를 캡슐화해서 라우팅하는 네트워크 레벨 VPN이다. 그동안 운영하면서 마주친 문제들 — IKE 페이즈가 어느 단계에서 멈췄는지 어떻게 알아내는지, WireGuard로 옮긴 뒤 처리량이 왜 두 배가 됐는지, Site-to-Site VPN에 BGP를 붙였더니 페일오버가 어떻게 달라졌는지, 풀 터널로 잡은 클라이언트 VPN이 왜 DNS만 새는지를 정리한다.

## VPN의 본질

VPN(Virtual Private Network)은 공용 네트워크 위에 사설망처럼 보이는 가상 경로를 만드는 기술이다. 핵심은 두 가지인데, 하나는 캡슐화(encapsulation)이고 다른 하나는 암호화(encryption)다. 사실 캡슐화만 있고 암호화가 없는 VPN도 존재한다. GRE 터널이 그렇다. 다만 우리가 흔히 "VPN"이라고 부르는 건 거의 다 캡슐화 + 암호화 조합이다.

L3 VPN과 L7 VPN을 헷갈리는 경우가 많다. SSL VPN이라고 부르는 것들(예: Cisco AnyConnect, FortiClient 일부 모드)은 응용 계층에서 TCP/UDP 위에 터널을 만든다. 반면 IPSec, WireGuard, OpenVPN의 TUN 모드는 IP 패킷 자체를 다른 IP 패킷 안에 넣는 L3 터널이다. 이 차이가 중요한 이유는, L3 VPN은 라우팅 테이블을 건드릴 수 있고 임의의 프로토콜을 통과시킬 수 있지만, L7 VPN은 보통 HTTPS만 통과시키는 식으로 제한된다는 점이다. 사내 SSH 접근이나 데이터베이스 접속까지 보내야 한다면 L3 VPN을 골라야 한다.

라우터에 IP 패킷이 들어오면 일반적으로 destination IP를 보고 라우팅 결정을 한다. VPN은 이 동작에 한 단계를 추가한다. "특정 대역으로 가는 패킷은 가상 인터페이스(보통 tun0, wg0, ipsec0 같은 이름)로 보내라"는 라우팅 규칙을 OS 커널에 박아두면, 해당 패킷이 가상 인터페이스를 거치면서 캡슐화·암호화된 다음, 외부 네트워크로 나가는 실제 인터페이스에서 다시 송출된다. 받는 쪽에서는 역과정을 거친다. 이 흐름을 이해해야 MTU나 라우팅 문제를 풀 수 있다.

```mermaid
graph LR
    A[원본 IP 패킷] --> B[가상 인터페이스 tun0/wg0]
    B --> C[캡슐화 + 암호화]
    C --> D[외부 IP 헤더 추가]
    D --> E[물리 인터페이스 eth0]
    E --> F[공용 네트워크]
    F --> G[상대 측 물리 인터페이스]
    G --> H[복호화 + 디캡슐화]
    H --> I[가상 인터페이스]
    I --> J[원본 IP 패킷 복원]
```

이 그림에서 주의 깊게 봐야 할 부분은 "외부 IP 헤더 추가" 단계다. 원본 패킷에 헤더가 덧붙는 만큼 패킷 크기가 커지고, 이게 MTU 문제의 출발점이다. 뒤에서 따로 다룬다.

## IPSec

IPSec은 IETF가 표준화한 L3 VPN 프로토콜 모음이다. "모음"이라고 부르는 이유는 단일 프로토콜이 아니라 여러 컴포넌트의 조합이기 때문이다. 키 교환을 담당하는 IKE(Internet Key Exchange), 실제 패킷을 보호하는 ESP(Encapsulating Security Payload)와 AH(Authentication Header), 그리고 보안 연관(SA, Security Association)을 관리하는 SAD/SPD 테이블이 함께 동작한다.

### IKE - 페이즈가 두 개라는 점이 중요하다

IKE는 키 교환과 SA 협상을 담당한다. IKEv1은 페이즈 1에서 메인 모드(6 메시지) 또는 어그레시브 모드(3 메시지)로 ISAKMP SA를 만들고, 페이즈 2에서 퀵 모드(3 메시지)로 IPSec SA를 만든다. IKEv2는 이 과정을 4 메시지로 줄였다. IKE_SA_INIT 2개와 IKE_AUTH 2개로 끝난다.

실무에서 IKE 트러블슈팅할 때 가장 먼저 보는 게 페이즈가 어디서 멈췄느냐다. strongSwan이나 Libreswan 로그에서 페이즈 1이 안 올라가면 대개 사전공유키(PSK) 또는 인증서 문제다. 페이즈 1까지 올라가는데 페이즈 2에서 멈추면 보통 양쪽의 트래픽 셀렉터(어떤 IP 대역을 보호할지 정의한 ACL)가 안 맞는 경우다.

```bash
# strongSwan에서 IKE 상태 확인
sudo ipsec statusall

# 자주 보는 출력
Connections:
  aws-vpn:  192.0.2.10...203.0.113.20  IKEv2
  aws-vpn:   local:  [192.0.2.10] uses pre-shared key authentication
  aws-vpn:   remote: [203.0.113.20] uses pre-shared key authentication
  aws-vpn:   child:  10.0.0.0/16 === 172.16.0.0/16 TUNNEL
Security Associations (1 up, 0 connecting):
  aws-vpn[3]: ESTABLISHED 12 minutes ago
  aws-vpn{2}: INSTALLED, TUNNEL, ESP in UDP SPIs: c1234567_i c7654321_o
  aws-vpn{2}:   10.0.0.0/16 === 172.16.0.0/16
```

여기서 `ESTABLISHED`는 IKE SA(페이즈 1)가 올라온 상태, `INSTALLED`는 Child SA(IPSec SA, 페이즈 2)가 커널에 박힌 상태다. `ESTABLISHED`만 보이고 `INSTALLED`가 안 보이면 페이즈 2 협상이 실패했다는 뜻이다.

IKEv1과 IKEv2의 가장 큰 차이는 NAT 감지와 재협상 로직이다. IKEv2는 NAT-T(NAT Traversal)가 표준에 포함되어 있고, MOBIKE 확장으로 클라이언트 IP가 바뀌어도 세션을 유지한다. 모바일 환경에서 LTE↔Wi-Fi 전환할 때 끊기지 않는 게 이것 때문이다. 신규 구축이라면 거의 무조건 IKEv2를 골라야 한다. IKEv1은 레거시 장비랑 붙어야 할 때나 쓴다.

### ESP와 AH

ESP는 암호화 + 무결성 + (선택적) 인증을 다 한다. AH는 무결성과 인증만 한다. 암호화가 없다. 옛날에는 미국 수출 규제 때문에 AH만 따로 두는 게 의미가 있었지만, 지금은 사실상 AH를 안 쓴다. ESP-NULL로 인증만 하는 모드가 따로 있어서 AH의 자리를 대체했고, AH는 NAT 환경에서 동작을 못 한다는 결정적 단점이 있다(AH가 IP 헤더 일부까지 인증 범위에 넣기 때문에, NAT가 IP 헤더를 바꾸면 인증이 깨진다).

ESP 패킷 구조는 대략 이렇게 생겼다.

```
[IP 헤더] [ESP 헤더] [원본 페이로드(암호화)] [ESP 트레일러] [ESP 인증 태그]
```

이 구조에서 ESP 헤더에 SPI(Security Parameters Index)가 들어가는데, 양쪽이 미리 협상한 SA를 식별하는 32비트 값이다. 패킷을 받은 쪽은 SPI를 보고 어떤 키로 복호화할지 결정한다.

### Transport 모드와 Tunnel 모드

이 둘은 헷갈리기 쉬운데, 캡슐화 범위가 다르다.

**Transport 모드**는 원본 IP 헤더는 그대로 두고, 페이로드만 ESP로 감싼다.

```
[원본 IP 헤더] [ESP 헤더] [원본 페이로드(암호화)] [ESP 트레일러]
```

호스트 간 직접 통신, 예를 들면 두 서버 사이의 특정 트래픽만 보호할 때 쓴다. 라우팅 정보(IP 헤더)는 노출된다.

**Tunnel 모드**는 원본 IP 패킷 전체를 ESP 페이로드로 넣고, 바깥에 새 IP 헤더를 붙인다.

```
[새 IP 헤더] [ESP 헤더] [원본 IP 헤더 + 페이로드(암호화)] [ESP 트레일러]
```

사이트 간 VPN(Site-to-Site)이나 원격 접속 VPN은 거의 다 Tunnel 모드다. 원본 IP가 사설 IP(10.0.0.0/8 같은)여서 인터넷으로 그대로 보낼 수 없기 때문에, 공인 IP로 된 새 헤더로 감싸야 한다. 실무에서 IPSec 설정할 때 99%는 Tunnel 모드라고 보면 된다.

### IPSec의 단점

직접 운영해 보면 IPSec은 설정이 끔찍하게 복잡하다. 협상해야 할 파라미터가 너무 많다. 암호화 알고리즘, 해시 알고리즘, DH 그룹, PFS 여부, SA 수명, 트래픽 셀렉터, NAT-T 모드 등등. 양쪽이 한 군데라도 어긋나면 협상이 깨진다. AWS Site-to-Site VPN을 처음 붙일 때 IKE 페이즈 1 암호화를 AES-256으로 맞춰놨는데, 라우터 쪽에서 AES-128로 응답 보내고 있어서 두 시간을 헤맨 적이 있다.

또 다른 문제는 NAT 환경이다. NAT-T가 있긴 하지만, ESP를 UDP 4500으로 캡슐화해서 보내는 추가 오버헤드가 생긴다. 그리고 일부 라우터는 NAT-T를 제대로 구현 안 한 것도 있다.

## WireGuard

IPSec을 한 번이라도 운영해 본 사람이라면 WireGuard를 처음 봤을 때 충격받는다. 설정 파일이 정말 한 화면에 들어온다.

```ini
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aA4bB=
Address = 10.10.0.1/24
ListenPort = 51820

[Peer]
PublicKey = pQ1rS2tT3uU4vV5wW6xX7yY8zZ9aA0bB1cC2dD3eE4=
AllowedIPs = 10.10.0.2/32
Endpoint = 203.0.113.20:51820
PersistentKeepalive = 25
```

이게 전부다. IPSec strongSwan 설정과 비교하면 코드 라인이 1/10도 안 된다. WireGuard의 설계 철학은 "협상하지 않는다"는 데 있다. 암호화 알고리즘이 고정이다. ChaCha20 + Poly1305로 AEAD, Curve25519로 키 교환, BLAKE2s로 해시, HKDF로 키 유도. 끝이다. 협상이 없으니 IKE 같은 복잡한 절차도 없다.

### 노이즈 프로토콜 프레임워크

WireGuard의 핸드셰이크는 Noise Protocol Framework의 IK 패턴을 기반으로 한다. 노이즈 프로토콜은 Trevor Perrin이 설계한 키 교환 프레임워크인데, Signal 메신저의 X3DH/Double Ratchet과도 같은 계열이다.

WireGuard에서 IK 패턴이 의미하는 건 "이니시에이터가 응답자의 정적 공개키를 미리 안다"는 거다. 즉, 연결을 시작하기 전에 양쪽이 서로의 PublicKey를 이미 가지고 있어야 한다. 위 설정 파일에서 `[Peer]` 섹션의 `PublicKey`가 그것이다.

핸드셰이크는 1-RTT다. 이니시에이터가 첫 메시지(initiation)를 보내고, 응답자가 응답 메시지(response)를 보내면 끝이다. 이후 데이터 패킷은 즉시 보낼 수 있다. IKEv2가 4 메시지(2-RTT)인 것과 비교하면 절반이다.

### 키 관리의 실무

WireGuard는 협상이 없는 대신 키 관리를 사용자가 직접 해야 한다. 새 클라이언트를 추가하려면 서버 설정 파일에 `[Peer]` 섹션을 하나 더 추가하고, `wg syncconf`로 다시 로드해야 한다.

```bash
# 클라이언트 키 쌍 생성
wg genkey | tee client_private.key | wg pubkey > client_public.key

# 서버에 피어 추가 (재시작 없이)
wg set wg0 peer <client_public_key> allowed-ips 10.10.0.5/32

# 영구 저장하려면 설정 파일에도 추가
```

소규모 팀이면 수동으로 관리해도 되지만, 직원이 50명 넘어가면 자동화가 필요하다. Tailscale이나 Headscale 같은 서비스가 이 부분을 자동화해 준 거다. Tailscale은 WireGuard 위에 컨트롤 플레인을 얹어서 키 교환·라우팅·인증을 다 자동화한다. 직접 운영하기 부담스러우면 Tailscale을 고려할 만하다.

### 성능 차이

WireGuard가 IPSec보다 빠르다는 얘기를 많이 듣는데, 실제로 측정해 봐도 그렇다. 같은 c5.large EC2 인스턴스 두 대를 띄워서 iperf3로 측정했을 때, strongSwan IPSec이 1.2Gbps 나오는 환경에서 WireGuard는 2.4Gbps가 나왔다. 차이가 나는 이유는 여러 가지인데, 핵심은 두 가지다.

첫째, WireGuard는 커널 모듈로 동작한다(Linux 5.6 이상). 패킷 처리가 유저스페이스로 올라가지 않는다. strongSwan은 IKE 협상은 유저스페이스에서 하지만, ESP 처리는 커널의 XFRM 프레임워크가 한다. 사실 이 부분만 보면 큰 차이는 없어야 하는데, WireGuard는 처음부터 커널 네이티브로 설계되어 코드 경로가 짧다.

둘째, ChaCha20-Poly1305는 AES-NI 명령어가 없는 CPU(예: 일부 ARM 임베디드)에서 AES보다 훨씬 빠르다. 모바일 디바이스나 라즈베리파이 같은 환경에서는 이 차이가 더 크게 난다. 다만 최신 인텔/AMD CPU에서는 AES-GCM도 AES-NI로 가속되니까 ChaCha20-Poly1305와 거의 비슷하다.

### WireGuard의 단점

만능은 아니다. 직접 운영하면서 답답했던 점이 몇 가지 있다.

먼저 동적 IP 할당이 없다. IPSec은 IKE 페이즈 2에서 클라이언트에 IP를 할당하는 메커니즘(IKEv2 CFG_REQUEST/CFG_REPLY)이 있는데, WireGuard는 각 피어의 AllowedIPs를 미리 정해 두는 방식이라 동적 풀에서 IP를 뽑아주는 게 불가능하다. 대규모 원격 접속 VPN에 그대로 쓰기는 어렵다.

다음으로 사용자 인증이 없다. WireGuard는 키 페어만으로 인증한다. RADIUS, LDAP, OAuth 같은 외부 인증 시스템과의 연동이 빌트인으로 없다. 회사에서 직원 입퇴사에 따라 VPN 접근을 관리하려면 별도의 컨트롤 플레인을 만들거나 Tailscale/Headscale 같은 것을 써야 한다.

마지막으로 로깅이 거의 없다. 보안 관점에서는 익명성이 강점이지만, 운영 관점에서는 누가 언제 접속했는지 추적하기 어렵다. 감사 로그가 필요한 조직에는 부담이 된다.

## OpenVPN

OpenVPN은 2001년에 나온 오픈소스 VPN이다. TLS 기반이라는 점이 IPSec/WireGuard와 다르다. 정확히는 TLS 위에서 키 교환과 컨트롤 채널을 만들고, 별도의 데이터 채널로 실제 패킷을 주고받는다. 데이터 채널은 UDP 또는 TCP를 쓸 수 있다.

OpenVPN의 강점은 두 가지였다. 하나는 방화벽 통과력이다. TCP/443으로 운영하면 HTTPS와 구분이 거의 안 되어서, 검열이 심한 지역이나 까다로운 방화벽 환경에서 유리하다. 다른 하나는 사용자 인증의 유연성이다. 인증서, 사용자명/비밀번호, MFA, LDAP, RADIUS, PAM 모듈 등을 자유롭게 조합할 수 있다.

단점은 성능이다. 사용자 공간(유저스페이스)에서 동작하기 때문에 패킷마다 컨텍스트 스위치가 발생하고, 멀티스레드 처리도 잘 안 된다. 같은 환경에서 측정해 보면 WireGuard 대비 1/3 수준 처리량이 나오는 경우도 흔하다. OpenVPN DCO(Data Channel Offload)라는 커널 모듈 프로젝트가 진행 중이라서 향후 개선될 여지는 있다.

또 다른 문제는 TCP 모드의 성능 함정이다. OpenVPN을 TCP로 돌리면 외부 TCP 위에 내부 TCP가 또 올라가는 "TCP-over-TCP" 상황이 된다. 한쪽 TCP 레이어가 패킷 손실 재전송을 하는데, 다른 쪽 TCP도 동시에 재전송을 시도하면서 의도와 달리 지연이 폭발하는 현상(TCP meltdown)이 발생한다. 가능하면 UDP로 운영하고, TCP는 정말 방화벽 통과가 안 될 때만 써야 한다.

실무 비중으로 보면, 신규 구축에서 OpenVPN을 적극적으로 고를 이유는 점점 줄고 있다. 기존에 OpenVPN을 쓰던 조직이 그대로 유지하는 경우는 많지만, 새로 시작한다면 WireGuard 또는 IPSec(IKEv2)을 고르는 게 보통이다.

## AWS Site-to-Site VPN과 BGP

AWS Site-to-Site VPN을 처음 붙일 때 가장 헷갈리는 게 BGP 부분이다. AWS는 정적 라우팅(static routing)과 동적 라우팅(BGP)을 둘 다 지원하는데, 동적 라우팅이 기본값이고 권장 방식이다.

AWS Site-to-Site VPN은 각 연결당 IPSec 터널 2개를 만든다. 같은 가상 프라이빗 게이트웨이(VGW)에 두 개의 AWS 엔드포인트가 다른 AZ에 배치되어 있다. 이 둘 중 하나가 죽어도 다른 하나로 트래픽이 흐르도록 페일오버를 구성해야 하는데, 정적 라우팅으로는 양쪽 터널을 능동적으로 전환하는 게 어렵다. BGP를 쓰면 BGP keepalive로 터널 상태를 감지하고, 하나가 죽으면 자동으로 다른 터널의 경로를 활성화한다.

실제 구성 흐름은 이렇다. 온프레미스 라우터(또는 strongSwan이 깔린 EC2)와 AWS VGW가 IPSec 터널을 맺으면, 그 터널 안에서 BGP 세션을 맺는다. AWS는 169.254.x.x/30 대역으로 터널 내부 IP를 할당하는데, 이걸 BGP 피어링 주소로 쓴다. 온프레미스 쪽에서 자신의 사내망 대역(예: 10.0.0.0/16)을 advertise하면 AWS 쪽 라우팅 테이블에 그게 들어가고, AWS도 VPC 대역(예: 172.16.0.0/16)을 advertise한다.

```bash
# VyOS 또는 Cisco IOS 같은 라우터에서 BGP 설정 예시 (개념적)
router bgp 65000
 neighbor 169.254.10.1 remote-as 64512
 neighbor 169.254.10.1 timers 10 30
 address-family ipv4 unicast
  network 10.0.0.0/16
  neighbor 169.254.10.1 activate
```

BGP timer를 짧게(10/30 정도) 잡는 이유는 페일오버 시간을 줄이기 위해서다. 기본값(60/180)이면 라우터가 죽었다는 걸 3분 동안 모를 수도 있다. 다만 너무 짧게(예: 1/3) 잡으면 일시적인 네트워크 흔들림에도 BGP 세션이 죽었다 살아나면서 라우팅이 불안정해진다.

AS_PATH prepending은 트래픽 분산을 제어할 때 쓴다. 두 터널 중 한쪽이 우선(active)이고 다른 쪽이 백업(passive)이 되도록 하려면, 백업 쪽 광고에 AS_PATH를 한두 번 더 prepend해서 경로 길이를 늘린다. BGP는 짧은 경로를 선호하니까 active 쪽으로 트래픽이 몰린다.

Transit Gateway가 등장한 이후로는 VGW를 직접 쓰는 빈도가 줄었다. Transit Gateway는 여러 VPC와 여러 VPN 연결을 한 군데로 모을 수 있어서, 여러 리전 / 여러 사무실을 연결하는 hub-and-spoke 토폴로지를 만들기에 편하다. 다만 비용이 더 든다. 단일 VPC 단일 VPN이면 그냥 VGW로 충분하다.

## Split Tunnel과 Full Tunnel

클라이언트 VPN을 구성할 때 라우팅을 어떻게 잡을지가 핵심이다. 두 가지 모델이 있다.

**Full Tunnel(전체 터널)**은 모든 트래픽을 VPN으로 보낸다. 클라이언트의 기본 게이트웨이가 VPN 인터페이스가 된다. 사용자가 유튜브를 보든, 사내 시스템에 접속하든, 전부 다 회사 VPN을 거쳐서 나간다.

**Split Tunnel(분할 터널)**은 특정 대역(예: 사내망 10.0.0.0/8, 172.16.0.0/12)으로 가는 트래픽만 VPN으로 보내고, 나머지(인터넷)는 클라이언트의 일반 인터넷 회선으로 나간다.

각각의 장단점이 있다. 풀 터널은 보안 관점에서 강하다. 모든 트래픽이 회사 방화벽을 거치니까 DLP(데이터 유출 방지), 콘텐츠 필터링, 로그 수집을 적용할 수 있다. 또 클라이언트가 카페 와이파이 같은 신뢰할 수 없는 네트워크에 있을 때 전체 트래픽이 암호화되어 보호된다. 단점은 회사 VPN 게이트웨이의 대역폭이 직원 수만큼 곱해진다는 점이다. 100명이 다 유튜브 보면 회사 인터넷이 마비된다.

스플릿 터널은 회사 인프라 부담이 적다. 사내 시스템 접근에 필요한 트래픽만 VPN으로 가니까 게이트웨이 부하가 적다. 사용자 경험도 좋다(인터넷 속도가 회사 회선이 아니라 본인 회선 속도다). 단점은 보안 가시성이 낮아진다는 점이다. 직원이 어떤 사이트를 가는지 회사에서 알 수 없고, 멀웨어가 직접 인터넷으로 C&C 통신해도 보이지 않는다.

코로나 시기에 많은 회사가 풀 터널에서 스플릿 터널로 전환했다. 갑자기 전 직원이 재택근무를 하면서 VPN 부하가 폭증했기 때문이다. 보안팀과 협의해서 스플릿 터널로 바꾼 곳이 많다.

### DNS 누수

스플릿 터널에서 자주 발생하는 문제가 DNS 누수(DNS leak)다. 사내 도메인 `intranet.company.local`을 분명히 VPN으로 보내야 하는데, 클라이언트 OS가 외부 DNS(예: 1.1.1.1)로 먼저 질의하면서 사내 도메인이 NXDOMAIN으로 떨어진다. 해결책은 DNS 분할 라우팅이다. VPN 연결 시 사내 도메인에 대해서는 사내 DNS 서버를 쓰도록 systemd-resolved 또는 NetworkManager에 명시해야 한다.

```bash
# Linux에서 systemd-resolved 사용 시 (resolvectl)
resolvectl dns wg0 10.0.0.53
resolvectl domain wg0 ~company.local
```

`~`가 붙은 도메인은 "이 도메인은 wg0 인터페이스의 DNS로만 질의하라"는 의미다. 이걸 빼먹으면 와이드 매칭이 되면서 외부 도메인도 사내 DNS로 가는 역방향 누수가 생긴다.

## MTU 문제

VPN을 운영하면서 가장 자주 마주치는 함정이 MTU(Maximum Transmission Unit)다. VPN은 캡슐화 때문에 패킷이 항상 커진다. 이게 어떻게 문제가 되는지 알아두지 않으면 "왜 SSH는 되는데 큰 파일 다운로드만 멈추지?" 같은 미스터리를 풀 수 없다.

일반적인 이더넷 MTU는 1500바이트다. IPSec ESP는 헤더와 트레일러로 50~70바이트 정도를 추가한다. WireGuard는 60바이트(IPv4 기준)를 추가한다. 그러니까 VPN 인터페이스의 MTU는 일반적으로 1380~1440바이트 정도로 잡는 게 안전하다.

문제는 MTU 설정을 안 하면 어떻게 되느냐다. 클라이언트가 1500바이트짜리 패킷을 만들어서 tun0로 보내면, 캡슐화 후에는 1560바이트가 된다. 그런데 실제 물리 인터페이스의 MTU가 1500바이트라서, 이 패킷은 못 보낸다. 두 가지 경로가 있다.

첫째, IP 단편화(fragmentation). 라우터가 이 패킷을 두 조각으로 나눠 보내고, 받는 쪽이 재조립한다. 동작은 하지만 성능이 떨어지고, 일부 환경에서는 단편화된 패킷이 중간 라우터에서 drop된다.

둘째, ICMP "Fragmentation Needed" 메시지. 라우터가 "이 패킷이 너무 커서 못 보내겠고, DF(Don't Fragment) 플래그가 세팅되어 있으니까, MTU 1440 이하로 줄여서 보내라"고 ICMP 메시지를 보낸다. 이걸 받은 발신자는 PMTUD(Path MTU Discovery)에 따라 패킷 크기를 줄인다.

문제는 많은 방화벽이 ICMP를 막아 둔다. ICMP가 죽으면 PMTUD가 깨지고(이걸 PMTU black hole이라 한다), 결과적으로 발신자는 자기 패킷이 도달하는지 못 하는지 알 수가 없다. TCP 연결은 SYN 같은 작은 패킷은 잘 가는데, 데이터 전송 시작하면 큰 패킷이 사라지면서 stall이 걸린다. 정확히 "SSH 로그인은 되는데 명령어 실행하면 멈춤" 같은 증상이 이거다.

해결책은 두 가지를 동시에 쓰는 게 일반적이다.

첫째, VPN 인터페이스 MTU를 명시적으로 줄인다.

```bash
# WireGuard 설정 파일에서
[Interface]
MTU = 1420
```

둘째, TCP MSS clamping. TCP 핸드셰이크의 SYN 패킷이 통과할 때 MSS(Maximum Segment Size) 값을 강제로 줄인다. iptables에서 한 줄로 가능하다.

```bash
sudo iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
  -o wg0 -j TCPMSS --clamp-mss-to-pmtu
```

이렇게 하면 TCP 양쪽이 처음부터 작은 세그먼트로 통신하기 때문에 단편화 자체가 발생하지 않는다. UDP 트래픽에는 적용 안 된다(MSS는 TCP 개념이라). UDP는 애플리케이션이 직접 MTU에 맞는 크기로 패킷을 만들어야 한다.

### MTU 디버깅

증상을 보고 MTU 문제인지 판단하는 방법이 있다. `ping`으로 큰 패킷에 DF 플래그를 세팅해서 보낸다.

```bash
# Linux: 1472바이트 페이로드 + 28바이트 헤더 = 1500바이트, DF 세팅
ping -M do -s 1472 <대상 IP>

# 같은 명령을 사이즈를 줄여가면서 반복
ping -M do -s 1420 <대상 IP>
ping -M do -s 1400 <대상 IP>
```

`-M do`가 DF 플래그를 세팅하라는 옵션이다. 어느 사이즈에서 통과하고 어느 사이즈에서 실패하는지 보면 path MTU를 추정할 수 있다. 실패할 때 "Frag needed and DF set" 메시지가 나오면 ICMP가 정상 동작한다는 뜻이고, 그냥 100% 손실로 나오면 ICMP가 어딘가에서 막혔다는 뜻이다.

## 클라이언트 VPN 실무 장애 사례

마지막으로 그동안 직접 겪은 클라이언트 VPN 장애 몇 가지를 정리한다. 대부분 이론으로는 알아도 실제 마주치면 한참 헤맨 것들이다.

### 케이스 1: 카페 와이파이에서만 VPN이 안 됨

한 직원이 특정 카페에서만 VPN 연결이 안 된다고 했다. 같은 노트북, 같은 설정인데 다른 곳에서는 잘 된다. 원인은 두 가지였다. 그 카페 와이파이가 캡티브 포털을 쓰고 있어서 처음 HTTP 응답을 가로채는데, VPN 클라이언트가 자동 연결을 시도하면서 캡티브 포털 페이지를 못 보고 그냥 실패로 처리됐다. 그리고 카페가 UDP 트래픽을 일부 막고 있어서 WireGuard(UDP 51820)가 안 됐다. 해결책으로 OpenVPN을 TCP/443으로 백업 채널로 깔아 뒀다.

### 케이스 2: VPN 연결 후 사내 시스템만 느려짐

분명 회사 사무실에서는 사내 시스템이 빠른데, VPN으로 접속하면 같은 시스템이 답답할 정도로 느려졌다. 디버깅해 보니 MTU 문제였다. VPN 인터페이스 MTU가 기본 1500으로 잡혀 있어서, 큰 응답 패킷이 단편화되고 있었다. MTU를 1420으로 줄이고 TCP MSS clamping을 켜니까 정상으로 돌아왔다.

### 케이스 3: 풀 터널인데 일부 도메인만 인터넷으로 샘

풀 터널로 잡아둔 VPN인데, Spotify나 Slack 같은 일부 앱이 회사 방화벽 로그에 안 보였다. 알고 보니 macOS의 일부 시스템 프로세스와 일부 앱이 ScopedRoutes를 우회해서 직접 인터페이스로 트래픽을 보내고 있었다. mDNS, Bonjour, 특정 시스템 데몬이 그렇다. 완벽한 풀 터널은 OS 레벨 지원이 없으면 어렵다는 걸 그때 알았다. 보안팀에는 "100% 차단은 어렵고, 정책 위반 탐지로 보완해야 한다"고 설명했다.

### 케이스 4: 일부 사용자만 IKE 협상 실패

전 직원에게 같은 설정 파일을 배포했는데, 특정 사용자 몇 명만 연결이 안 됐다. 로그를 보니 IKE_SA_INIT에서 응답이 안 오는 패턴이었다. 공통점을 찾아보니 다 같은 통신사 모바일 라우터를 쓰고 있었다. 그 라우터의 NAT 구현이 UDP 4500(NAT-T) 포트를 짧은 시간 후에 닫아버려서, 핸드셰이크가 깨지고 있었다. 해결책으로 PersistentKeepalive(WireGuard) 또는 DPD(Dead Peer Detection, IPSec) 간격을 짧게 잡아서 NAT 매핑을 유지하도록 했다.

### 케이스 5: 클라이언트 IP 충돌

직원이 집에서 VPN을 연결하니까 사내 시스템 일부 IP에 접근이 안 됐다. 알고 보니 직원의 홈 네트워크 대역이 10.0.0.0/24인데, 회사 사내망 대역도 10.0.0.0/24 였다. VPN이 사내망으로 가는 라우팅을 박아도, 우선순위에서 직접 연결된 인터페이스(홈 LAN)가 이기는 경우가 있어서 일부 IP는 홈 네트워크로 빠졌다. 회사 사내망을 다른 대역(예: 10.100.0.0/16)으로 재설계하는 게 근본 해결책이지만, 임시로는 직원에게 홈 라우터의 LAN 대역을 192.168.x.x로 바꾸도록 안내했다. 사내망 대역을 사설 IP 표준 대역 중에서도 흔하지 않은 곳으로 잡는 게 좋다는 교훈을 얻었다.

## 마무리

VPN은 단순한 "암호화 통로"가 아니다. 라우팅, MTU, NAT, 인증, 페일오버까지 네트워크 전반의 이해가 필요한 분야다. IPSec은 표준성과 호환성이 강점이지만 복잡하고, WireGuard는 단순함과 성능이 강점이지만 사용자 관리에 빈틈이 있고, OpenVPN은 유연성이 강점이지만 성능이 떨어진다. 어느 하나가 절대적으로 좋다고 말하기는 어렵고, 환경에 맞춰 골라야 한다.

새로 구축한다면 사이트 간 VPN은 IPSec IKEv2(특히 클라우드와 연결할 때), 직원 원격 접속은 WireGuard 기반(Tailscale 포함)을 우선 검토하는 게 요즘 흐름이다. 다만 어떤 솔루션을 골라도 MTU와 DNS는 항상 신경 써야 한다. 이 두 가지는 프로토콜이 뭐든 똑같이 나오는 문제다.
