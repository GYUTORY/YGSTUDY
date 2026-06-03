---
title: OSI 7 계층 모델 (OSI 7 Layer Model)
tags: [network, osi, 7-layer, protocol, encapsulation, troubleshooting, tcpdump, wireshark]
updated: 2026-06-03
---

# OSI 7 계층 모델

## 개요

OSI(Open Systems Interconnection) 모델은 ISO가 1984년에 표준화한 통신 시스템 참조 모델이다. ISO/IEC 7498-1로 등록되어 있으며, 서로 다른 벤더의 네트워크 장비와 운영체제가 통신할 수 있도록 통신 과정을 7개 계층으로 추상화했다.

1980년대 초반에는 IBM의 SNA, DEC의 DECnet, Xerox의 XNS처럼 벤더마다 독자 프로토콜을 사용했다. 같은 회사 장비끼리만 통신이 가능했고, 다른 벤더 장비를 도입하면 게이트웨이를 별도로 구축해야 했다. ISO는 이 종속성을 해결하려고 OSI 모델을 만들었다. OSI 프로토콜 스택 자체는 시장에서 외면받았지만, 7개 계층으로 통신을 분해하는 사고방식은 표준으로 남았다.

실무에서 OSI 모델을 직접 구현할 일은 없다. 하지만 장애 분석, 보안 정책 설계, 로드밸런서 선택, 방화벽 룰 작성 같은 작업은 전부 "이 문제가 어느 계층에서 발생하느냐"로 귀결된다. 5년차 정도 되면 동료가 "L7 문제야, L4 문제야?"라고 묻는 상황이 매주 발생한다. 이 문서는 모델 자체를 외우는 것보다 패킷이 각 계층을 어떻게 통과하는지, 캡처 도구로 어떻게 분해해서 보는지에 집중한다.

---

## 7개 계층 상세

응용 계층부터 물리 계층 순서로 본다. 데이터를 송신할 때는 이 순서대로 내려가면서 헤더가 붙고(캡슐화), 수신할 때는 반대로 올라가면서 헤더가 벗겨진다(디캡슐화).

### L7 - 응용 계층 (Application Layer)

사용자가 직접 사용하는 서비스가 동작하는 계층이다. 브라우저, 메일 클라이언트, SSH 클라이언트가 여기서 동작한다.

- PDU: Data 또는 Message
- 주요 프로토콜: HTTP/HTTPS, FTP, SMTP, IMAP, POP3, DNS, SSH, Telnet, gRPC
- 장비: WAF, API Gateway, L7 로드밸런서, 프록시 서버

실무에서 가장 자주 만지는 계층이다. HTTP 헤더 조작, 인증 토큰 검증, URL 라우팅이 모두 여기서 일어난다.

### L6 - 표현 계층 (Presentation Layer)

데이터의 표현 방식을 다룬다. 인코딩, 암호화, 압축이 이 계층의 책임이다.

- PDU: Data
- 주요 기술: TLS/SSL, JPEG, MPEG, ASCII, EBCDIC, MIME, gzip
- 장비: 거의 없음 (소프트웨어 라이브러리로 구현)

실제 구현에서는 응용 계층과 분리되지 않는 경우가 많다. TLS는 OSI 모델상 표현 계층이지만, 실제로는 TCP 위에 직접 얹는 형태(L4와 L7 사이)로 구현된다. 이런 부분이 "OSI 모델은 이론에 가깝다"는 평가를 받는 이유다.

### L5 - 세션 계층 (Session Layer)

통신하는 양 끝단의 세션을 관리한다. 세션 수립, 유지, 종료, 동기화가 여기서 일어난다.

- PDU: Data
- 주요 프로토콜: NetBIOS, RPC, SMB, SOCKS, PPTP
- 장비: 없음

실무에서 세션 계층은 거의 의식하지 않는다. HTTP 세션이라고 부르는 것도 사실은 응용 계층의 쿠키/토큰으로 구현된 가상 개념이다.

### L4 - 전송 계층 (Transport Layer)

종단 간(end-to-end) 데이터 전송을 책임진다. 포트 번호로 프로세스를 구분하고, 신뢰성과 흐름 제어를 담당한다.

- PDU: Segment (TCP) / Datagram (UDP)
- 주요 프로토콜: TCP, UDP, QUIC, SCTP
- 장비: L4 스위치, L4 로드밸런서, 방화벽

TCP는 3-way handshake로 연결을 수립하고, 시퀀스 번호와 ACK로 신뢰성을 보장한다. UDP는 연결 없이 데이터그램을 던진다. 포트 번호가 0~65535 범위에서 관리되는 것이 이 계층의 특징이다.

### L3 - 네트워크 계층 (Network Layer)

서로 다른 네트워크 간의 경로 결정과 전달을 담당한다. IP 주소가 등장하는 계층이다.

- PDU: Packet
- 주요 프로토콜: IPv4, IPv6, ICMP, IGMP, OSPF, BGP, ARP는 L2/L3 경계
- 장비: 라우터, L3 스위치

라우팅 테이블, 서브넷 마스크, NAT, VPN 터널링이 이 계층의 영역이다. `traceroute`로 추적하는 hop이 L3 라우터들이다.

### L2 - 데이터 링크 계층 (Data Link Layer)

같은 네트워크 세그먼트 안에서의 노드 간 전송을 담당한다. MAC 주소를 사용한다.

- PDU: Frame
- 주요 프로토콜: Ethernet, Wi-Fi(802.11), PPP, HDLC, VLAN(802.1Q), STP
- 장비: 스위치, 브리지, 무선 AP

MAC 주소는 NIC(네트워크 카드)에 하드코딩된 48비트 주소다. 같은 LAN에서는 IP가 아닌 MAC으로 직접 통신한다. ARP는 IP를 MAC으로 변환하는 프로토콜이며, L2와 L3의 경계에 걸쳐 있다.

### L1 - 물리 계층 (Physical Layer)

비트를 전기 신호, 광 신호, 무선 신호로 변환해서 전송 매체로 보낸다.

- PDU: Bit
- 주요 규격: RJ-45, 광섬유, 동축케이블, RS-232, USB, Bluetooth 무선
- 장비: 케이블, 허브, 리피터, 트랜시버

링크 LED가 안 들어오는 문제, 케이블 단선, SFP 모듈 불량 같은 것이 L1 문제다. 데이터센터에서 회선 교체 작업이 L1 작업이다.

---

## 패킷이 보내지기 전 - ARP 해석부터

`curl http://192.168.1.50:8080/` 한 줄을 쳤다고 하자. 실제로 첫 SYN이 와이어로 나가기 전에 일이 꽤 많이 일어난다.

1. **라우팅 테이블 조회 (L3)**: 커널은 `ip route show`의 결과를 기준으로 목적지 IP가 같은 서브넷인지 확인한다. 같은 서브넷이면 직접 ARP, 다른 서브넷이면 게이트웨이 MAC으로 ARP를 보낸다.
2. **ARP 캐시 확인 (L2/L3)**: `ip neigh`에 해당 IP의 MAC이 캐시되어 있는지 본다. 캐시가 없으면 ARP 요청을 브로드캐스트한다.
3. **ARP 요청 송출 (L2 브로드캐스트)**: `FF:FF:FF:FF:FF:FF`로 "192.168.1.50 누구야?" 프레임을 보낸다. 답이 돌아오면 캐시에 저장하고 다음부터는 캐시를 쓴다.
4. **소스 포트 할당 (L4)**: 커널이 사용 가능한 ephemeral port(보통 32768~60999)에서 하나를 골라 소스 포트로 쓴다.
5. **TCP SYN 송신 (L4)**: 그제야 첫 SYN 세그먼트가 IP 헤더와 Ethernet 헤더를 달고 나간다.

ARP가 안 풀리면 IP는 정상이라도 통신이 안 된다. `arping -I eth0 192.168.1.50`으로 L2까지 도달 가능한지 직접 확인할 수 있다. ARP 패킷은 L2 프레임이지 IP 패킷이 아니라서 라우터를 넘지 못한다는 사실이 중요하다. 다른 서브넷의 호스트는 ARP로 직접 못 찾고 반드시 게이트웨이를 거친다.

```bash
# 현재 ARP 캐시
ip neigh show
# 192.168.1.1 dev eth0 lladdr 00:50:56:c0:00:08 REACHABLE
# 192.168.1.50 dev eth0 lladdr 00:1a:2b:3c:4d:5e STALE

# ARP 요청만 캡처
sudo tcpdump -i eth0 -nn arp

# 강제로 ARP 갱신
sudo ip neigh del 192.168.1.50 dev eth0
ping -c 1 192.168.1.50
```

IPv6는 ARP 대신 NDP(Neighbor Discovery Protocol)를 쓴다. ICMPv6 메시지로 동작하므로 ARP보다 IP 계층에 가깝다.

---

## 캡슐화와 디캡슐화

송신측은 응용 계층에서 만든 데이터를 아래로 내려보내면서 각 계층의 헤더를 붙인다. 수신측은 반대로 올라가면서 헤더를 벗긴다. 실제 패킷의 바이트 구조를 보면 어느 계층의 헤더가 어디서부터 시작하는지 명확해진다.

```mermaid
graph TD
    A[L7 Data: HTTP 요청 38B] --> B[L4 TCP 헤더 20B 부착]
    B --> C[L3 IP 헤더 20B 부착]
    C --> D[L2 Ethernet 헤더 14B + FCS 4B]
    D --> E[L1 비트 스트림으로 변환]
    E --> F[전송 매체로 송출]
```

HTTP GET 요청을 예시로 보자. `GET / HTTP/1.1\r\nHost: example.com\r\n\r\n`은 약 38바이트의 페이로드다. 여기에 헤더가 차례로 붙는다.

```
[Ethernet 헤더 14B][IP 헤더 20B][TCP 헤더 20B][HTTP 페이로드 38B][FCS 4B]
0                  14            34            54                  92  96바이트
```

각 헤더의 주요 필드를 바이트 단위로 보면 이렇다.

```
Ethernet 헤더 (14 bytes)
  Destination MAC: 6 bytes  (예: 00:1a:2b:3c:4d:5e)
  Source MAC:      6 bytes
  EtherType:       2 bytes  (0x0800 = IPv4, 0x86DD = IPv6, 0x0806 = ARP)

IPv4 헤더 (20 bytes, 옵션 없을 때)
  Version+IHL:     1 byte   (상위 4비트 버전, 하위 4비트 헤더 길이/4)
  TOS/DSCP:        1 byte   (QoS 우선순위)
  Total Length:    2 bytes  (IP 헤더 + 페이로드 전체 길이)
  Identification:  2 bytes  (Fragmentation 시 같은 패킷 식별)
  Flags+Fragment:  2 bytes  (DF/MF 플래그, Fragment Offset)
  TTL:             1 byte   (hop 카운트 다운, 0이 되면 폐기)
  Protocol:        1 byte   (6=TCP, 17=UDP, 1=ICMP, 50=ESP)
  Header Checksum: 2 bytes
  Source IP:       4 bytes
  Destination IP:  4 bytes

TCP 헤더 (20 bytes, 옵션 없을 때)
  Source Port:      2 bytes
  Destination Port: 2 bytes
  Sequence Number:  4 bytes  (이 세그먼트의 첫 바이트 번호)
  ACK Number:       4 bytes  (다음에 받을 시퀀스 번호)
  Data Offset+Flags: 2 bytes (상위 4비트 헤더 길이/4, 하위 9비트 플래그)
  Window Size:      2 bytes  (수신 가능한 버퍼 크기)
  Checksum:         2 bytes
  Urgent Pointer:   2 bytes
```

수신측 NIC는 와이어에서 비트 스트림을 받아 프레임 단위로 읽고, EtherType이 0x0800이면 IP 모듈에 전달한다. IP 모듈은 Protocol 필드가 6이면 TCP 스택에 넘기고, TCP는 Destination Port를 보고 해당 포트를 listen 중인 프로세스에게 페이로드를 전달한다. 이 흐름을 머릿속에 그리고 있어야 패킷 캡처를 읽을 수 있다.

### 수신측 디캡슐화 순서

송신측 캡슐화를 거꾸로 뒤집은 게 디캡슐화다. NIC가 프레임을 받으면 커널 내부에서 이 단계가 순차적으로 일어난다.

1. **L1**: NIC가 와이어의 전기/광 신호를 비트 시퀀스로 복원한다. 프리앰블·SFD로 프레임 시작을 인식한다.
2. **L2**: NIC가 FCS(CRC32)를 검증하고 깨진 프레임은 그 자리에서 drop한다. 카운터는 `ip -s link show eth0`의 RX errors로 잡힌다. 목적지 MAC이 자기 NIC가 아니면 promiscuous 모드가 아닐 때 폐기한다.
3. **EtherType 분기**: 0x0800이면 IPv4 모듈, 0x86DD면 IPv6 모듈, 0x0806이면 ARP 모듈로 페이로드를 넘긴다.
4. **L3**: IP 헤더 체크섬을 검증하고 TTL을 1 감소시킨다. 목적지 IP가 자기 IP가 아니면 라우팅 대상이거나 폐기한다. Fragmentation된 패킷이면 재조립 큐에 모은다.
5. **Protocol 분기**: 6이면 TCP, 17이면 UDP, 1이면 ICMP로 페이로드를 넘긴다.
6. **L4**: TCP는 시퀀스 번호로 순서를 맞추고 ACK를 돌려보낸다. Destination Port로 소켓을 찾아 페이로드를 read 큐에 쌓는다.
7. **L7**: 프로세스가 `read()`/`recv()`로 페이로드를 꺼낸다.

장애 분석 시 어느 단계에서 패킷이 사라졌는지 추적하는 게 핵심이다. 와이어샤크에서 SYN은 보이는데 SYN-ACK가 안 보이면 L2까지는 도달했지만 L3 또는 L4에서 drop된 것이다. `iptables -L -v`의 패킷 카운터, `nstat`의 `TcpExtListenDrops` 같은 통계가 어느 단계에서 사라졌는지 알려준다.

---

## tcpdump로 각 계층 헤더 분석

운영 서버에서 가장 자주 쓰는 도구가 tcpdump다. 옵션을 어떻게 주느냐에 따라 어느 계층까지 보여줄지 결정된다.

```bash
# L2부터 전부 16진수로 출력 (-e: Ethernet 헤더 포함, -X: hex+ascii)
sudo tcpdump -i eth0 -e -X -c 1 'tcp port 80'

# 출력 예시
10:23:45.123456 00:1a:2b:3c:4d:5e > 00:50:56:c0:00:08, ethertype IPv4 (0x0800), length 74:
192.168.1.10.54321 > 93.184.216.34.80: Flags [S], seq 1234567890, win 64240, length 0
        0x0000:  4500 003c 1c46 4000 4006 b1e6 c0a8 010a  E..<.F@.@.......
        0x0010:  5db8 d822 d431 0050 4996 02d2 0000 0000  ]..".1.PI.......
        0x0020:  a002 faf0 91e0 0000 0204 05b4 0402 080a  ................
```

이 출력을 직접 디코드해보자.

```
4500     IP 버전=4, IHL=5 (20바이트), TOS=00
003c     Total Length = 60바이트 (= IP 20 + TCP 40)
1c46     Identification
4000     Flags=010 (Don't Fragment), Fragment Offset=0
4006     TTL=64, Protocol=6 (TCP)
b1e6     Header Checksum
c0a8010a Source IP = 192.168.1.10 (c0=192, a8=168, 01=1, 0a=10)
5db8d822 Destination IP = 93.184.216.34

여기까지가 IP 헤더 20바이트. 이후 TCP 헤더 시작.

d431     Source Port = 54321
0050     Destination Port = 80
499602d2 Sequence Number = 1234567890
00000000 ACK Number = 0 (SYN이라 아직 ACK 없음)
a002     Data Offset=10 (40바이트, TCP 옵션 포함), Flags=000000010 (SYN)
faf0     Window Size = 64240
91e0     Checksum
0000     Urgent Pointer
0204 05b4   TCP Option: MSS = 1460
0402     SACK Permitted
080a ...   Timestamps
```

이 한 번을 직접 손으로 풀어보면 패킷 캡처를 보는 눈이 달라진다. 와이어샤크가 자동으로 보여주는 트리 구조의 의미가 비로소 와닿는다.

자주 쓰는 BPF 필터 패턴:

```bash
# TCP 핸드셰이크만 (SYN 또는 SYN-ACK)
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0'

# RST 패킷만 (연결 끊김 추적)
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-rst != 0'

# DNS 쿼리만
sudo tcpdump -i eth0 -nn 'udp port 53'

# 특정 호스트의 HTTP 요청 페이로드 ASCII로
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and host example.com'

# pcap 파일로 저장 후 Wireshark로 분석
sudo tcpdump -i eth0 -w capture.pcap 'host 10.0.0.5'

# 링 버퍼로 100MB 파일 10개 순환 (장기 캡처)
sudo tcpdump -i eth0 -w cap_%Y%m%d_%H%M%S.pcap -G 3600 -W 24 -Z root

# VLAN 태그를 포함한 패킷 (L2 트래픽 분석)
sudo tcpdump -i eth0 -nn -e vlan
```

`-s 0`이 중요하다. 기본 snaplen은 OS마다 다르고 응용 페이로드가 잘리는 경우가 있어서 풀 캡처 시 명시한다. 운영 환경에서 trace 떠줄 때 잘린 파일 받으면 답이 없다.

---

## Wireshark로 계층별 분석

GUI로 패킷을 깊게 분석할 때는 Wireshark다. tcpdump가 잡은 pcap을 그대로 열어서 본다.

### 디스플레이 필터 (캡처 필터와 다름)

tcpdump의 BPF 필터는 캡처 시점에 걸리지만, Wireshark의 디스플레이 필터는 잡은 패킷을 사후에 거른다. 문법이 다르다는 점을 처음에 헷갈린다.

```
# HTTP 응답 코드가 500 이상
http.response.code >= 500

# 특정 호스트로 가는 HTTP 요청
http.host == "api.example.com"

# TLS 핸드셰이크의 SNI
tls.handshake.extensions_server_name == "api.example.com"

# TCP 재전송만
tcp.analysis.retransmission

# TCP RST 또는 ZeroWindow
tcp.flags.reset == 1 or tcp.analysis.zero_window

# 특정 출발지 포트 범위
tcp.srcport >= 32768 and tcp.srcport <= 60999

# 지연이 큰 패킷 (이전 패킷 대비 1초 이상 차이)
frame.time_delta > 1.0

# 페이로드에 특정 문자열 (대소문자 무시)
frame contains "Authorization"
```

### Follow Stream

특정 TCP 연결의 전체 대화를 한 번에 보고 싶을 때는 오른쪽 클릭 → Follow → TCP Stream. HTTP 요청/응답 페이로드를 텍스트로 한 화면에 펼쳐준다. TLS면 평문이 안 보이지만, `SSLKEYLOGFILE` 환경변수를 브라우저에 설정하고 그 로그를 Wireshark에 등록하면 복호화해서 보여준다.

### Expert Information

`Analyze → Expert Information` 메뉴에 비정상 패턴을 자동으로 분류해 놓는다.

- Warnings: 재전송, 중복 ACK, ZeroWindow
- Errors: 체크섬 오류, malformed packet
- Notes: 정상 동작이지만 주목할 만한 것 (Window 업데이트, Keep-Alive)

처음 pcap을 받으면 Expert Information부터 본다. 거기서 재전송이 많이 보이면 L3 경로 문제, ZeroWindow가 많으면 수신측 처리 지연을 의심한다.

### IO Graph

`Statistics → I/O Graph`로 시간 축에 패킷/바이트/특정 이벤트를 그래프로 그린다. "어느 순간부터 트래픽이 뚝 떨어졌는가"를 시각적으로 확인할 때 쓴다. 디스플레이 필터를 그래프 시리즈에 걸 수 있어서 RST 발생 시점, 500 응답 발생 시점을 동시에 비교할 수 있다.

### Conversations와 Endpoints

`Statistics → Conversations` (TCP 탭)에서 어떤 IP 쌍이 가장 많은 바이트를 주고받았는지, 어느 연결의 지연이 큰지 정렬해서 본다. 어떤 호스트가 트래픽을 독점하고 있는지 빠르게 찾을 때 유용하다.

### tshark - CLI 동등 기능

서버에 GUI를 띄울 수 없을 때는 tshark를 쓴다. Wireshark의 분석 엔진을 그대로 명령행에서 쓰는 도구다.

```bash
# pcap 파일에서 HTTP 요청 라인만 추출
tshark -r capture.pcap -Y 'http.request' -T fields \
    -e ip.src -e http.request.method -e http.host -e http.request.uri

# TLS SNI 통계 (어떤 도메인으로 가장 많이 접속했나)
tshark -r capture.pcap -Y 'tls.handshake.type == 1' -T fields \
    -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn

# TCP 재전송 발생한 연결의 4-tuple
tshark -r capture.pcap -Y 'tcp.analysis.retransmission' -T fields \
    -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport | sort -u

# 라이브 캡처도 가능
sudo tshark -i eth0 -Y 'http.response.code >= 500' -T fields \
    -e ip.src -e http.host -e http.response.code -e http.request.uri
```

tshark는 텍스트 파이프라인과 잘 어울려서 `sort | uniq -c | sort -rn` 같은 집계가 자연스럽다. 와이어샤크 GUI로 사람이 보는 분석과, tshark로 스크립트로 거르는 자동화를 같이 쓰는 게 실무 패턴이다.

---

## Python raw socket으로 패킷 캡처

직접 NIC에서 바이트를 읽어서 헤더를 파싱하는 코드다. Linux에서 root 권한으로 실행해야 한다.

```python
import socket
import struct

# AF_PACKET은 Linux 전용. ETH_P_ALL=0x0003은 모든 EtherType
ETH_P_ALL = 0x0003
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))

def parse_ethernet(data):
    dest, src, ether_type = struct.unpack('!6s6sH', data[:14])
    return {
        'dest_mac': ':'.join(f'{b:02x}' for b in dest),
        'src_mac': ':'.join(f'{b:02x}' for b in src),
        'ether_type': hex(ether_type),
    }, data[14:]

def parse_ipv4(data):
    version_ihl = data[0]
    ihl = (version_ihl & 0x0F) * 4
    ttl, protocol = data[8], data[9]
    src_ip = socket.inet_ntoa(data[12:16])
    dst_ip = socket.inet_ntoa(data[16:20])
    return {
        'src_ip': src_ip,
        'dst_ip': dst_ip,
        'ttl': ttl,
        'protocol': protocol,  # 6=TCP, 17=UDP, 1=ICMP
    }, data[ihl:]

def parse_tcp(data):
    src_port, dst_port, seq, ack, offset_flags = struct.unpack('!HHIIH', data[:14])
    data_offset = (offset_flags >> 12) * 4
    flags = offset_flags & 0x01FF
    return {
        'src_port': src_port,
        'dst_port': dst_port,
        'seq': seq,
        'ack': ack,
        'flags': {
            'SYN': bool(flags & 0x02),
            'ACK': bool(flags & 0x10),
            'FIN': bool(flags & 0x01),
            'RST': bool(flags & 0x04),
            'PSH': bool(flags & 0x08),
        },
    }, data[data_offset:]

while True:
    raw_data, _ = sock.recvfrom(65535)
    eth, payload = parse_ethernet(raw_data)
    print(f"L2: {eth['src_mac']} -> {eth['dest_mac']} ({eth['ether_type']})")

    if eth['ether_type'] != '0x800':
        continue

    ip, payload = parse_ipv4(payload)
    print(f"L3: {ip['src_ip']} -> {ip['dst_ip']} TTL={ip['ttl']} Proto={ip['protocol']}")

    if ip['protocol'] != 6:
        continue

    tcp, app_data = parse_tcp(payload)
    print(f"L4: :{tcp['src_port']} -> :{tcp['dst_port']} flags={tcp['flags']}")

    if app_data:
        print(f"L7 payload (first 80B): {app_data[:80]}")
    print('-' * 60)
```

이 코드를 한 번 돌려보면 캡슐화 구조가 머릿속에 박힌다. struct.unpack의 포맷 문자열(`!6s6sH`, `!HHIIH`)이 헤더 필드 길이를 그대로 반영한다. 권한이 없으면 `PermissionError: [Errno 1] Operation not permitted`가 나오는데, `setcap cap_net_raw=eip $(which python3)`로 권한을 부여하면 일반 사용자로도 실행할 수 있다.

macOS는 AF_PACKET이 없어서 BPF 디바이스(`/dev/bpf*`)를 직접 열거나 scapy를 써야 한다. 운영 서버는 대부분 Linux라 위 코드가 그대로 동작한다.

---

## OSI 7 계층 vs TCP/IP 4 계층

실무에서 진짜 쓰이는 모델은 TCP/IP 4 계층이다. RFC 1122에서 정의한 인터넷 표준 모델이다. OSI는 너무 이론적이라 실제 구현이 잘 맞지 않는다.

| OSI 7 계층 | TCP/IP 4 계층 | 주요 프로토콜 |
|-----------|--------------|--------------|
| L7 응용 | 응용 (Application) | HTTP, FTP, DNS, SSH |
| L6 표현 | 응용 | TLS, MIME |
| L5 세션 | 응용 | (응용 계층 내부에서 처리) |
| L4 전송 | 전송 (Transport) | TCP, UDP |
| L3 네트워크 | 인터넷 (Internet) | IP, ICMP |
| L2 데이터 링크 | 네트워크 액세스 (Link) | Ethernet, Wi-Fi |
| L1 물리 | 네트워크 액세스 | 케이블, 광섬유 |

TCP/IP가 실무를 지배하게 된 이유는 단순하다. 1) ARPANET에서 실전 검증을 거쳤다. 2) BSD Unix에 socket API로 구현되어 무료로 배포됐다. 3) OSI 표준화 작업이 진행되는 동안 TCP/IP는 이미 동작하고 있었다. 표준을 기다리느니 동작하는 걸 쓰자는 흐름이 됐다.

지금도 면접에서는 OSI 7계층을 묻지만 코드는 TCP/IP로 짠다. 둘 다 알고 있어야 한다.

---

## L4 vs L7 로드밸런서

로드밸런서가 어느 계층에서 동작하느냐는 운영 비용과 기능을 가른다.

L4 로드밸런서는 IP 주소와 포트만 보고 분산한다. 패킷 페이로드를 들여다보지 않는다. TCP 연결을 그대로 백엔드에 전달하거나(DSR), 종단 처리한다.

L7 로드밸런서는 HTTP 헤더, URL, 쿠키, JWT 클레임까지 본다. 그래서 URL 경로 기반 라우팅, 쿠키 기반 sticky session, gRPC 메서드별 분산이 가능하다. 단점은 TLS 종단 처리와 헤더 파싱 비용 때문에 L4보다 처리량이 낮고 지연이 크다는 점이다.

HAProxy로 두 모드를 비교하면 차이가 명확하다.

```haproxy
# L4 모드 (TCP)
frontend mysql_front
    bind *:3306
    mode tcp
    default_backend mysql_back

backend mysql_back
    mode tcp
    balance roundrobin
    server db1 10.0.0.10:3306 check
    server db2 10.0.0.11:3306 check
```

```haproxy
# L7 모드 (HTTP)
frontend api_front
    bind *:443 ssl crt /etc/ssl/api.pem
    mode http
    # URL 경로로 백엔드 분기
    use_backend users_back if { path_beg /api/users }
    use_backend orders_back if { path_beg /api/orders }
    default_backend default_back

backend users_back
    mode http
    balance leastconn
    # 쿠키 기반 sticky session
    cookie SRV insert indirect nocache
    server u1 10.0.1.10:8080 check cookie u1
    server u2 10.0.1.11:8080 check cookie u2
```

nginx도 비슷한 패턴이다.

```nginx
# L7 (http 블록)
upstream api_users {
    least_conn;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/api.crt;

    location /api/users {
        proxy_pass http://api_users;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
    }
}
```

```nginx
# L4 (stream 블록, nginx 1.9 이상)
stream {
    upstream mysql_cluster {
        server 10.0.0.10:3306;
        server 10.0.0.11:3306;
    }

    server {
        listen 3306;
        proxy_pass mysql_cluster;
    }
}
```

DB나 Redis처럼 텍스트 프로토콜이 아닌 경우는 L4를 쓴다. HTTP API는 L7을 쓴다. gRPC는 HTTP/2 위에서 동작하므로 L7이지만 nginx의 기본 HTTP 프록시가 HTTP/2 백엔드를 잘 처리하지 못해 Envoy를 쓰는 경우가 많다.

---

## 계층별 트러블슈팅 시나리오

장애가 났을 때 가장 먼저 하는 일은 "어느 계층 문제냐"를 좁히는 것이다. 위에서 아래로 내려가는 게 빠를 때도 있고, 아래에서 위로 올라가는 게 빠를 때도 있다.

### L1 - 케이블 단선, SFP 불량

증상: 인터페이스가 down 상태. 핑이 자기 자신만 가고 게이트웨이에 안 간다.

```bash
# 인터페이스 상태 확인
ip link show eth0
# state UP / state DOWN을 확인

# 링크 속도와 협상 상태
ethtool eth0
# Link detected: yes / no가 핵심

# 자기 자신은 가지만 게이트웨이는 안 가는 상황
ping -c 3 127.0.0.1   # OK
ping -c 3 192.168.1.1 # 100% packet loss

# CRC 에러, drop 카운터 - 케이블 품질 의심
ip -s link show eth0
ethtool -S eth0 | grep -i 'err\|drop\|crc'
```

데이터센터에서는 SFP 광 모듈의 송수신 강도까지 본다. `ethtool -m eth0`로 광 레벨을 확인할 수 있다. RX power가 너무 낮으면 광 케이블 청소나 SFP 교체를 검토한다.

### L2 - ARP 충돌, VLAN 미스매치

증상: 같은 IP가 두 호스트에 있어 통신이 간헐적으로 끊긴다. 또는 다른 VLAN에 있어 같은 서브넷인데도 통신이 안 된다.

```bash
# ARP 테이블 확인
arp -a
ip neigh show

# 비정상 출력 예시: 같은 IP가 두 MAC에 매핑
# 192.168.1.100 dev eth0 lladdr 00:1a:2b:3c:4d:5e REACHABLE
# 192.168.1.100 dev eth0 lladdr 00:50:56:c0:00:08 STALE

# VLAN 태그 확인 (스위치 포트가 VLAN 10에 속하는지)
ip -d link show eth0.10

# 의심되는 호스트의 MAC을 강제로 갱신
sudo arp -d 192.168.1.100
ping 192.168.1.100
arp -a | grep 192.168.1.100

# ARP 패킷 캡처로 누가 응답하는지 확인
sudo tcpdump -i eth0 -nn -e arp host 192.168.1.100
# 응답이 두 MAC에서 오면 IP 충돌
```

### L3 - 라우팅 루프, 잘못된 게이트웨이

증상: 핑은 가는데 응답이 늦거나, traceroute에서 같은 hop이 반복된다.

```bash
# 라우팅 테이블
ip route show
# default via 192.168.1.1 dev eth0 가 있는지

# 특정 목적지가 어느 라우트를 탈지 확인
ip route get 8.8.8.8

# hop 추적 - 라우팅 루프가 있으면 같은 IP가 반복됨
traceroute -n 8.8.8.8
# 1  192.168.1.1
# 2  10.0.0.1
# 3  10.0.0.5
# 4  10.0.0.1   <-- 루프
# 5  10.0.0.5

# TTL 변화 보기 (루프면 TTL이 0이 되어 ICMP TTL exceeded 반환)
ping -c 1 -t 5 8.8.8.8

# MTR로 지속적인 hop별 손실률 측정
mtr -n -c 100 8.8.8.8
```

라우팅 루프는 보통 OSPF/BGP 컨버전스가 안 된 상태에서 발생한다. 임시 조치로 정적 라우트를 추가하기도 한다. MTR은 traceroute + ping의 결합으로, 어느 hop에서 손실이 시작되는지 지속적으로 보여준다.

### L4 - 포트 차단, 방화벽 룰, TCP 상태

증상: 호스트는 핑이 가는데 특정 포트로 접속이 안 된다. 또는 연결은 되는데 곧바로 끊어진다.

```bash
# 포트가 listen 중인지
ss -tlnp | grep :8080
netstat -tlnp | grep :8080

# 원격 포트 접속 테스트
nc -zv 10.0.0.5 8080
# Connection to 10.0.0.5 port 8080 [tcp/*] succeeded!  <-- OK
# nc: connect to 10.0.0.5 port 8080 (tcp) failed: Connection refused  <-- 프로세스 down
# nc: connect to 10.0.0.5 port 8080 (tcp) failed: Connection timed out <-- 방화벽

# 현재 TCP 연결 상태별 카운트 - L4 문제 진단의 핵심
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c
# ESTAB이 많이 쌓여있으면 정상
# TIME-WAIT이 수만 개면 단명 연결 폭주
# CLOSE-WAIT이 쌓이면 응용이 close()를 안 한 것
# SYN-SENT가 많으면 SYN-ACK이 안 옴 → 방화벽이나 백엔드 down

# iptables 룰 확인 (패킷 카운터로 drop되는지 추적)
sudo iptables -L -n -v --line-numbers
sudo iptables -L INPUT -n -v | grep 8080

# conntrack 테이블 full 여부
sudo conntrack -C
sudo cat /proc/sys/net/netfilter/nf_conntrack_max

# Security Group이나 클라우드 방화벽도 의심
# AWS면 aws ec2 describe-security-groups
```

`Connection refused`와 `Connection timed out`은 원인이 다르다. refused는 호스트에는 도달했는데 그 포트에 listen 중인 프로세스가 없다는 뜻이고, timed out은 방화벽이 SYN을 drop했거나 호스트 자체에 도달하지 못했다는 뜻이다.

CLOSE-WAIT이 응용 서버에 누적되면 응용이 소켓을 close하지 않은 것이다. 보통 코드 버그(DB connection 누수, finally의 close 누락)다. 재시작으로 풀리지만 근본 원인은 코드다.

### L7 - HTTP 5xx, 인증 실패

증상: 네트워크는 정상인데 응답이 500/502/503/504로 돌아온다.

```bash
# 헤더와 상태 코드 확인
curl -v https://api.example.com/users
# > GET /users HTTP/2
# > Host: api.example.com
# > Authorization: Bearer xxx
# < HTTP/2 502
# < server: nginx
# < x-upstream: backend-3

# 백엔드 응답 시간 측정 - 어느 단계가 느린지 분해
curl -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTLS: %{time_appconnect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
     -o /dev/null -s https://api.example.com/

# nginx upstream 에러 로그
tail -f /var/log/nginx/error.log
# 2026/06/03 10:23:45 [error] upstream timed out (110: Connection timed out)
# while connecting to upstream, client: 1.2.3.4, server: api.example.com,
# request: "GET /users HTTP/2.0", upstream: "http://10.0.1.10:8080/users"

# TLS 핸드셰이크만 확인 (인증서 문제 의심 시)
openssl s_client -connect api.example.com:443 -servername api.example.com </dev/null
```

502는 업스트림 응답이 잘못된 경우, 504는 업스트림이 타임아웃 안에 응답하지 못한 경우다. 503은 업스트림이 의도적으로 거부한 경우(rate limit, maintenance)가 많다. curl의 `-w` 옵션으로 어느 단계가 느린지 분해해보면 DNS인지, TCP인지, TLS인지, 백엔드 처리인지 한눈에 보인다.

---

## 방화벽, IDS, 프록시의 동작 계층

같은 보안 장비라도 어느 계층에서 동작하느냐에 따라 기능과 한계가 결정된다.

| 장비/기능 | 동작 계층 | 판단 기준 |
|----------|----------|----------|
| 패킷 필터 방화벽 | L3-L4 | IP, 포트, 프로토콜 |
| Stateful 방화벽 | L4 | TCP 연결 상태 추적 |
| WAF (Web Application Firewall) | L7 | HTTP 메서드, 헤더, 페이로드 |
| Next-Gen Firewall (NGFW) | L3-L7 | DPI로 응용 식별 |
| 시그니처 IDS (Snort, Suricata) | L3-L7 | 패킷 페이로드 패턴 매칭 |
| 포워드 프록시 (Squid) | L7 | URL, HTTP 헤더 |
| 리버스 프록시 (nginx) | L7 | URL, Host 헤더 |
| SOCKS 프록시 | L5 | 포트와 호스트만 |

L3-L4에서 동작하는 패킷 필터 방화벽은 빠르지만 SQL injection 같은 응용 계층 공격을 막지 못한다. 그래서 L7에서 동작하는 WAF를 같이 쓴다. WAF는 페이로드를 파싱하므로 처리 비용이 크고, 정규식 룰이 잘못 작성되면 정상 트래픽까지 차단한다.

TLS 트래픽은 L7 장비가 페이로드를 못 본다. 그래서 SSL termination(TLS를 풀어서 평문으로 만든 뒤 검사)을 하거나, 해시 기반의 SNI/JA3 핑거프린트로만 판단한다. 이 부분이 보안 정책 설계에서 자주 나오는 트레이드오프다.

---

## MTU, MSS, Fragmentation

L2(Ethernet)의 페이로드 최대 크기가 MTU(Maximum Transmission Unit)다. 표준 Ethernet은 1500바이트다. 점보 프레임을 활성화하면 9000바이트까지 가능하다.

L4(TCP)에서 한 세그먼트에 담을 수 있는 페이로드 최대 크기가 MSS(Maximum Segment Size)다. 기본값은 `MTU - IP헤더(20) - TCP헤더(20) = 1460`바이트다. TCP 핸드셰이크의 SYN 패킷에서 양 끝단이 서로의 MSS를 광고하고 작은 쪽으로 맞춘다.

```bash
# MTU 확인
ip link show eth0 | grep mtu
# mtu 1500

# MTU 변경
sudo ip link set eth0 mtu 9000

# MSS는 tcpdump의 SYN 패킷에서 mss 1460 식으로 표시됨
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0' -v

# 특정 경로에서 실제로 통과 가능한 MTU 측정
ping -M do -s 1472 8.8.8.8   # 1472 + 8(ICMP) + 20(IP) = 1500
# Frag needed and DF set이 나오면 더 작은 값으로 시도
```

Fragmentation은 L3(IP) 계층에서 발생한다. IP 패킷이 다음 hop의 MTU보다 크면 라우터가 잘게 쪼갠다. 쪼개진 조각은 수신측 IP 계층에서 재조립한다. TCP는 fragmentation을 피하려고 PMTUD(Path MTU Discovery)로 경로 전체의 최소 MTU를 찾는다.

실무에서 자주 만나는 문제는 PMTUD가 깨지는 경우다. ICMP "Fragmentation Needed" 메시지가 방화벽에서 차단되면 송신측은 MTU가 작은 구간이 있다는 사실을 모르고 큰 패킷을 계속 보낸다. 작은 요청은 가는데 큰 응답이 안 오는 증상이 나타난다. 해결책은 MSS clamping이다.

```bash
# 모든 SYN의 MSS를 PMTU에 맞게 강제로 깎음
sudo iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
    -j TCPMSS --clamp-mss-to-pmtu
```

VPN 터널에서는 추가 헤더 때문에 실효 MTU가 1500보다 작아진다. IPsec이면 1438 정도, WireGuard면 1420 정도가 보통이다. VPN 도입 후 일부 사이트만 안 열린다는 신고가 들어오면 90% MTU 문제다.

---

## 계층 독립성의 실무적 의미

OSI 모델의 핵심 사상은 각 계층이 독립적이라는 점이다. 한 계층의 구현이 바뀌어도 다른 계층은 영향을 받지 않는다.

구체적인 예시:

L1을 구리선에서 광섬유로 바꿔도 IP나 TCP는 그대로 동작한다. 회선만 교체하면 끝난다.

L2를 Ethernet에서 Wi-Fi로 바꿔도 HTTP 요청은 동일하게 처리된다. 노트북에서 유선/무선 전환 시 IP가 바뀔 뿐 응용은 무관하다.

L3를 IPv4에서 IPv6로 바꿔도 nginx 설정은 `listen 80`만 `listen [::]:80`으로 바꾸면 된다. HTTP 자체는 변경 없다.

L4를 TCP에서 QUIC로 바꿔도 HTTP/3로 동작한다. 응용 코드는 거의 그대로다.

L7만 HTTP에서 gRPC로 바꿔도 IP, TCP, Ethernet은 영향을 받지 않는다.

이 독립성 덕분에 각 팀이 자기 계층에만 집중할 수 있다. 인프라 팀은 L1-L3, 시스템 엔지니어는 L3-L4, 백엔드 개발자는 L7을 본다. 장애가 발생했을 때도 "이건 우리 계층 문제가 아니다"라고 빠르게 판단할 수 있어야 회의가 길어지지 않는다.

다만 추상화는 새는 곳이 있다. TCP 위에서 동작하는 HTTP라도 TCP slow start나 Nagle 알고리즘 때문에 짧은 요청이 느려지는 경우가 있다. TLS는 L6이지만 TCP 위에 직접 얹혀서 계층 경계가 모호하다. QUIC는 UDP 위에서 신뢰성과 흐름 제어를 직접 구현하므로 L4 계층을 응용 계층 라이브러리에서 다시 만든 셈이다. 모델은 모델일 뿐, 실제 구현은 실용성 때문에 종종 경계를 넘는다.

5년 정도 일하다 보면 이 모델을 외우는 게 아니라 패킷 캡처를 보면서 자연스럽게 계층을 분해하게 된다. tcpdump 출력을 보고 "이 SYN이 안 가니까 L4 이하 문제고, ARP 테이블이 정상이니까 L2는 정상이다, 그럼 L3 라우팅이나 방화벽이다"라는 추론이 자동으로 나오면 OSI 모델을 제대로 익힌 것이다.
