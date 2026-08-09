---
title: TCP와 OSI 7 계층
tags: [network, tcp, encryption, http]
updated: 2026-07-16
---

# TCP와 OSI 7 계층

OSI 모델 전반은 [OSI 7 계층 모델](../../OSI_7_Layer_Model.md) 문서에 정리되어 있다. 이 문서는 TCP가 OSI 7계층 전체에서 어떤 위치를 차지하는지, HTTP 요청 하나가 L7에서 L1까지 내려가고 다시 올라오는 과정을 실제 패킷 단위로 추적한다.

## HTTP 요청 하나가 7개 계층을 지나는 과정

브라우저가 `https://example.com/index.html`을 요청할 때 각 계층에서 무슨 일이 일어나는지 순서대로 쫓아본다.

### L7 → L4: 애플리케이션 데이터가 TCP 세그먼트가 되기까지

**L7 (Application): HTTP 요청 구성**

```http
GET /index.html HTTP/1.1\r\n
Host: example.com\r\n
Connection: keep-alive\r\n
\r\n
```

텍스트 약 60바이트가 애플리케이션 레이어에서 만들어진다.

**L5/L6 (Session/Presentation): TLS Record로 암호화**

HTTPS라면 이 HTTP 바이트가 그냥 내려가지 않는다. TLS Record Layer가 감싼다.

```
TLS Record Header (5바이트):
  ContentType: 0x17 (Application Data)
  Version:     0x0303 (TLS 1.2/1.3 공통 레거시 필드)
  Length:      암호화 후 페이로드 길이

암호화된 HTTP 데이터 (가변):
  AEAD 인증 태그 16B 포함, 원본 60바이트가 80~90바이트 내외로 늘어남
```

TLS Record와 TCP 세그먼트는 1:1로 대응되지 않는다. TLS Record 하나가 여러 TCP 세그먼트로 쪼개질 수도 있고, 한 TCP 세그먼트에 여러 TLS Record가 합쳐질 수도 있다. tcpdump로 보면 암호화된 덩어리들만 보이는데, TLS Record 경계와 TCP 세그먼트 경계가 다르다는 점을 항상 염두에 둬야 한다.

**L4 (Transport): TCP 세그먼트로 포장**

L4에서 TCP 헤더 20바이트(옵션 제외)가 앞에 붙는다.

```
[TCP Header 20B] [TLS Record (5B 헤더 + 암호화 데이터)]
출발지 포트: 임시 포트(예: 54321)
목적지 포트: 443
Seq:    현재 스트림 바이트 위치
ACK:    상대방에게 받은 마지막 바이트
Flags:  PSH, ACK
Window: 수신 버퍼 여유 공간
```

### L3 → L1: IP 패킷이 물리 신호가 되기까지

**L3 (Network): IP 헤더 추가**

TCP 세그먼트가 IP 페이로드가 된다. IP 헤더 20바이트(옵션 없을 때)가 앞에 붙는다.

```
[IP Header 20B] [TCP Header 20B] [TLS Record]
출발지 IP: 192.168.0.10
목적지 IP: 93.184.216.34
Protocol:  6 (TCP)
TTL:       64 (리눅스 기본값)
```

IP 헤더의 Protocol 필드가 `6`이라는 숫자 하나로 "이 패킷의 페이로드는 TCP 세그먼트"라는 L3→L4 경계를 정의한다.

**L2 (Data Link): 이더넷 프레임으로 감싸기**

목적지가 같은 서브넷이 아니면 ARP로 라우터의 MAC 주소를 알아낸 뒤 이더넷 프레임으로 감싼다.

```
[Ethernet Header 14B] [IP Header 20B] [TCP Header 20B] [TLS Record] [FCS 4B]
DST MAC: 라우터(게이트웨이)의 MAC
SRC MAC: 내 NIC의 MAC
EtherType: 0x0800 (IPv4)
```

이더넷 헤더의 MAC 주소는 홉마다 바뀐다. 패킷이 라우터를 거칠 때마다 L2 헤더는 새로 씌워지지만, L3 IP 헤더는 출발지에서 목적지까지 유지된다. end-to-end 식별자는 IP이고, L2 MAC은 다음 홉까지의 로컬 식별자다.

**L1 (Physical): 비트로 전송**

이더넷 프레임의 바이트들이 전기 신호(구리 케이블), 광 신호(광케이블), 또는 전파(무선)로 변환되어 전송된다. 1Gbps 이더넷이면 1비트당 1ns. L1은 프로토콜이라기보다 물리 매체와 신호 스펙이다.

전체 오버헤드를 합산하면:

```
L2 이더넷 헤더:    14B
L3 IP 헤더:        20B
L4 TCP 헤더:       20~40B (옵션 포함 시)
L5/L6 TLS:         5B 헤더 + AEAD 태그 16B
---------------------------------
HTTP 60B에 오버헤드 최소 75~95B
```

작은 요청일수록 헤더 오버헤드 비율이 높다. HTTP/2가 헤더 압축(HPACK)을 도입한 이유 중 하나다.

## tcpdump로 계층 경계 추적하기

`-e` 플래그를 붙이면 L2 이더넷 헤더까지 출력된다.

```bash
sudo tcpdump -i eth0 -nn -e -X 'host 93.184.216.34 and port 443' -c 10
```

**SYN 패킷 (TCP 연결 시작, L2/L3/L4)**

```
14:32:11.234567 aa:bb:cc:11:22:33 > 00:1a:2b:3c:4d:5e, ethertype IPv4 (0x0800), length 78:
  192.168.0.10.54321 > 93.184.216.34.443: Flags [S], seq 3916014290, win 64240,
  options [mss 1460,sackOK,TS val 4294944 ecr 0,nop,wscale 7], length 0

  0x0000:  4500 003c 1c46 4000 4006 f4f5 c0a8 000a   E..<.F@.@.......
  0x0010:  5db8 d822 d431 01bb e940 0fd2 0000 0000   ]..".1...@......
  0x0020:  a002 faf0 50f4 0000 0204 05b4 0402 080a   ....P...........
  0x0030:  0041 ae60 0000 0000 0103 0307             .A.`.......
```

줄별로 읽으면:
- 맨 앞 줄: L2. `aa:bb:cc:11:22:33 > 00:1a:2b:3c:4d:5e`가 이더넷 헤더의 출발지/목적지 MAC. `0x0800`이 EtherType(IPv4).
- `192.168.0.10.54321 > 93.184.216.34.443`: tcpdump가 L3 IP 주소와 L4 포트를 파싱해서 보여준 것.
- `Flags [S]`: TCP SYN 플래그만 켜진 상태.
- 바이트 덤프 첫 바이트 `45`: `4`는 IPv4, `5`는 헤더 길이 5×4=20바이트.
- `0x0006` 위치(IP 헤더 9번째 바이트): Protocol=6, TCP를 의미.
- `d431 01bb`: TCP 헤더 시작. `0xd431`=54321(출발지 포트), `0x01bb`=443(목적지 포트).
- `a002`: Data Offset=10(헤더 40바이트, 옵션 포함), Flags=0x02(SYN만 켜짐).

**TLS ClientHello (L5/L6 레이어)**

TCP 3-way handshake가 끝난 뒤 클라이언트가 TLS 핸드셰이크를 시작한다.

```
14:32:11.356789 aa:bb:cc:11:22:33 > 00:1a:2b:3c:4d:5e, ethertype IPv4 (0x0800), length 583:
  192.168.0.10.54321 > 93.184.216.34.443: Flags [P.], seq 1:530, ack 1, win 502, length 529

  0x0000:  4500 024b 1c48 4000 4006 f2a0 c0a8 000a   E..K.H@.@.......
  0x0010:  5db8 d822 d431 01bb e940 0fd3 ...         ]..".1...@......
  ...
  0x0036:  1603 0101 0204 ...                        ................
```

- `0x0036` 오프셋(이더넷 14B + IP 20B + TCP 20B = 54B 뒤)부터 TLS Record가 시작된다.
- `16`: TLS ContentType=0x16=Handshake.
- `03 01`: TLS 레코드 레이어의 레거시 버전 필드(TLS 1.3도 이 자리에 0x0303을 넣는다).
- 이후 바이트: ClientHello 핸드셰이크 메시지(지원 cipher suite, SNI 등).

tcpdump는 L4까지만 파싱한다. TLS(L5/L6) 이상은 바이트 덤프로만 보인다. TLS 내용을 보려면 `ssldump`나 Wireshark에 세션 키를 주입해야 한다.

**HTTP Application Data (L7, TLS 암호화 상태)**

TLS 핸드셰이크 완료 후 실제 HTTP 요청이 암호화되어 전송된다.

```
14:32:11.892345 aa:bb:cc:11:22:33 > 00:1a:2b:3c:4d:5e, ethertype IPv4 (0x0800), length 140:
  192.168.0.10.54321 > 93.184.216.34.443: Flags [P.], seq 530:616, ack 4192, win 501, length 86

  0x0000:  4500 008c ...
  ...
  0x0036:  1703 0300 51 ...                          ....Q...
```

- `0x0036`부터 TLS Record.
- `17`: ContentType=0x17=Application Data. 이 시점부터 HTTP 데이터가 암호화되어 들어있다.
- `03 03`: TLS 1.2/1.3 레코드 레이어 버전.
- 이후는 완전히 암호화된 페이로드. `GET /index.html HTTP/1.1`이라는 내용은 여기서 보이지 않는다.

L7이 L4 아래에서 완전히 불투명해지는 지점이 여기다.

## 수신 측: 헤더를 벗겨내는 역방향 과정

서버 측에서는 반대 순서로 처리한다.

NIC가 비트를 받아 이더넷 프레임으로 조립(L1→L2). L2에서 EtherType `0x0800`을 보고 IP 스택으로 올린다(L2→L3). L3에서 Protocol 필드 `6`을 보고 TCP 스택으로 올린다(L3→L4). L4 TCP에서 목적지 포트 443을 보고 해당 소켓에 데이터를 전달한다(L4→L5). L5/L6 TLS Record Layer가 복호화한다. L7 HTTP 파서가 메서드, 경로, 헤더를 파싱한다.

각 계층이 자기 헤더만 보고 판단한 뒤 상위 계층으로 올린다. L3는 L4의 내용을 모르고, L4는 L7의 내용을 모른다. 계층 간 결합이 헤더 필드 몇 바이트로만 이루어진다는 점이 OSI 모델의 실제 의미다.

## L4가 담당하는 것과 TCP가 그것을 어떻게 푸는가

OSI 4계층의 책임은 **프로세스 간 종단간(end-to-end) 연결**을 만드는 것이다. L3(IP)는 호스트까지만 데이터를 가져다주고, "이 데이터가 어떤 프로세스에 가야 하는지"는 모른다. 거기서부터가 L4의 일이다.

TCP는 이 책임을 구체적인 메커니즘으로 구현한 프로토콜이다. 네 가지를 동시에 처리한다.

**포트 다중화(Multiplexing/Demultiplexing)**
한 호스트의 IP는 하나지만 그 위에 수천 개의 프로세스가 동시에 통신할 수 있다. 16비트 포트 번호가 이를 가능하게 한다. 같은 80번 포트로 들어오는 패킷이라도 (출발지 IP, 출발지 포트, 목적지 IP, 목적지 포트, 프로토콜)이라는 5-tuple로 각 연결이 구분된다. 5-tuple이 같으면 같은 TCP 연결이고, 하나라도 다르면 다른 연결이다. 같은 클라이언트가 같은 서버의 같은 포트로 여러 번 연결해도 클라이언트 측 임시 포트(ephemeral port)가 달라서 별개의 연결이 된다.

**바이트 스트림 추상화**
애플리케이션 입장에서 TCP는 "양방향 바이트 스트림"이다. `write`한 바이트 100개가 그대로 `read`에서 100바이트로 나오는 것처럼 보이지만, 실제로는 IP 패킷 단위로 잘려서 가다가 순서가 뒤바뀌거나 일부가 유실될 수 있다. TCP는 모든 바이트에 시퀀스 번호를 붙이고, 받은 쪽이 ACK 번호로 "이 바이트까지 받았다"를 알려주면서 누락된 구간을 재전송한다. L4 세그먼트는 L3 패킷과 1:1 대응이 아니다. 한 세그먼트가 IP에서 단편화될 수도 있고, 애플리케이션이 보낸 데이터 1개가 여러 세그먼트로 쪼개질 수도 있다.

**흐름 제어(Flow Control)**
수신자가 처리할 수 있는 속도보다 빠르게 보내면 수신 버퍼가 넘친다. TCP 헤더의 Window 필드로 "지금 내 버퍼에 X바이트만큼 더 받을 수 있다"를 매번 알려주고, 송신자는 그 한도를 넘지 않게 보낸다.

**혼잡 제어(Congestion Control)**
흐름 제어가 수신자를 보호하는 거라면, 혼잡 제어는 네트워크 자체를 보호한다. 네트워크 어딘가가 막히면 패킷 유실로 나타나고, TCP는 이를 감지해서 송신 속도를 줄인다. CUBIC, BBR 같은 알고리즘이 여기에 해당한다. UDP는 L4지만 혼잡 제어를 하지 않는다.

암호화나 메시지 경계는 TCP가 하지 않는다. 그건 위 계층의 일이다.

## TCP 헤더를 L4 PDU로 분해하기

L4의 PDU(Protocol Data Unit)는 **세그먼트(Segment)**다. TCP 세그먼트는 TCP 헤더 + 페이로드로 구성되고, 헤더는 옵션 없이도 최소 20바이트다.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |  0~3
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |  4~7
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |  8~11
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  DO |Rsv|U|A|P|R|S|F|         Window Size           |          12~15
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |        Urgent Pointer         |  16~19
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (가변, 0~40바이트)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            Payload                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

L4의 책임과 매핑해서 보면 어떤 필드가 어떤 일을 하는지 분명해진다.

- **Source/Destination Port (0~3바이트)**: 포트 다중화. IP 헤더에는 포트가 없다. L4에서 비로소 프로세스 단위 식별이 가능해진다.
- **Sequence Number (4~7바이트)**: 이 세그먼트의 첫 페이로드 바이트가 전체 스트림에서 몇 번째 바이트인지. 32비트라서 약 4GB마다 한 바퀴 돈다. 고대역폭 환경에서 이 문제 때문에 PAWS(Protect Against Wrapped Sequences)가 옵션으로 들어왔다.
- **Acknowledgment Number (8~11바이트)**: "이 번호 직전 바이트까지 받았다." ACK 플래그가 켜져 있을 때만 유효하다.
- **Data Offset(DO, 4비트)**: TCP 헤더 길이를 32비트 워드 단위로 표현. 옵션 필드가 가변 길이라서 헤더 끝이 어디인지 알려줘야 한다. 최댓값 15면 60바이트, 그래서 옵션은 최대 40바이트.
- **Flags**: 연결 상태 전이를 만드는 비트들. 3-way handshake도 4-way termination도 결국 이 비트 조합이다.
- **Window Size (14~15바이트)**: 흐름 제어. 수신 가능 바이트. 16비트라 65535가 최대지만, Window Scale 옵션으로 최대 1GB 가까이 늘릴 수 있다. 1Gbps 이상 회선에서 이 옵션 없으면 throughput이 안 나온다.
- **Checksum (16~17바이트)**: TCP 헤더+페이로드+IP pseudo-header에 대한 체크섬. L2 이더넷에도 FCS가 있지만 그건 다음 홉까지의 검증이고, end-to-end 검증은 여기서 한다.
- **Options**: MSS, SACK Permitted, Window Scale, Timestamp 같은 협상 항목들. SYN과 SYN+ACK에서 주로 교환된다.

## L5~L7: TLS와 HTTP가 TCP 위에 얹히는 방식

OSI 모델은 L5(세션), L6(표현), L7(응용)을 깔끔하게 분리하지만, 실제 인터넷 프로토콜에서는 이 셋이 거의 합쳐져 있다. TCP/IP 4계층 모델이 L5~L7을 그냥 "Application"으로 묶어버리는 이유다.

**TLS의 계층 위치**

TLS는 L4 위에서 동작하지만 OSI L5/L6에 걸쳐있다. 핸드셰이크 단계에서는 세션을 협상(L5)하고, 이후에는 암호화와 무결성을 제공(L6)한다.

```
TLS Record 구조:
ContentType (1B):  Handshake(0x16), Alert(0x15), ApplicationData(0x17)
Version (2B):      0x0303 (TLS 1.2/1.3 공통)
Length (2B):       이 Record의 페이로드 길이
Payload:           암호화된 데이터 또는 핸드셰이크 메시지
```

TLS Record와 TCP 세그먼트 경계가 맞지 않는 경우가 자주 발생한다. 16KB TLS Record(TLS 최대 Record 크기)는 MTU 1500바이트 기준으로 약 11개의 TCP 세그먼트로 쪼개진다. 첫 번째 세그먼트만 TLS Record 헤더를 포함하고 나머지는 페이로드만 담는다. 수신 측은 TCP 스트림에서 TLS Record를 재조립한 뒤에야 복호화할 수 있다.

이 구조 때문에 TLS 위에서 패킷 유실이 발생하면 단순 재전송 지연보다 더 큰 문제가 생긴다. TLS Record 하나를 완성하지 못하면 복호화 자체가 블락된다. HTTP/3(QUIC)이 스트림 단위 재전송으로 이 head-of-line blocking을 피하려는 이유가 여기 있다.

**HTTP의 계층 위치**

교과서적으로 HTTP는 L7이지만, HTTP/1.1의 keep-alive와 Connection 헤더는 세션 관리(L5)에 가깝다. Content-Type, Content-Encoding은 데이터 표현(L6)이다. HTTP 하나가 L5/L6/L7을 다 한다. OSI로 정확히 자르려고 하면 답이 안 나오는 이유다.

**L4 LB가 TLS 트래픽을 다룰 수 있는가**

L4 LB(NLB, LVS 등)는 TCP 헤더까지만 본다. TLS 핸드셰이크 내용은 읽지 못한다. SNI 기반으로 도메인별 라우팅을 하려면 L7 LB(Nginx, ALB, Envoy)로 올라가거나, TLS Passthrough 상태에서 ClientHello의 SNI 확장 필드만 읽는 형태(L4와 L7 사이 어딘가)가 된다.

**TLS 트래픽 트러블슈팅**

서버 측에서 TLS termination을 하지 않으면 중간에서 HTTP 요청/응답을 볼 방법이 없다. 클라이언트 측에서 세션 키를 덤프(`SSLKEYLOGFILE` 환경변수 설정)하거나, L7 LB에서 TLS를 종료한 뒤 내부망은 HTTP로 통신하는 방식을 쓴다.

```bash
# 클라이언트 세션 키 덤프 (curl 예시)
SSLKEYLOGFILE=/tmp/keylog.txt curl https://example.com

# Wireshark에서 keylog 파일을 주입하면 암호화된 TLS 트래픽 복호화 가능
# Edit > Preferences > Protocols > TLS > (Pre)-Master-Secret log filename
```

tcpdump로 덤프한 패킷 캡처 파일과 keylog를 Wireshark에서 함께 열면, 암호화된 Application Data 패킷 안에 있던 HTTP 요청/응답 내용까지 평문으로 볼 수 있다.

## TCP 소켓 API와 L4 추상화

L4의 추상화는 결국 BSD 소켓 API로 노출된다.

```c
int sock = socket(AF_INET, SOCK_STREAM, 0);  // SOCK_STREAM = TCP
bind(sock, ...);    // 자기 측 포트 점유 - 포트 다중화 등록
listen(sock, 511);  // accept queue 깊이 결정
accept(sock, ...);  // 완성된 5-tuple 연결을 가져옴
read(sock, buf, n); // 바이트 스트림에서 n바이트 읽기
write(sock, buf, n);// 바이트 스트림에 n바이트 쓰기
close(sock);        // FIN 전송, 4-way termination 시작
```

`read()`로 받은 바이트 수가 한 번의 `write()`와 일치할 거라는 보장이 없다. TCP는 메시지 경계를 보존하지 않는다. 송신 측이 1000바이트를 한 번에 write했어도 수신 측은 300바이트, 700바이트로 나눠서 read할 수 있고, 반대로 두 번의 write가 한 번의 read에서 합쳐져 올 수도 있다. TCP를 처음 다룰 때 가장 많이 실수하는 지점이다. 메시지 단위 통신을 하려면 위 계층에서 길이 prefix나 delimiter로 경계를 따로 만들어야 한다.

`SO_KEEPALIVE`, `TCP_NODELAY`, `SO_LINGER` 같은 소켓 옵션들도 L4 내부 동작을 켜고 끄는 노브다. `TCP_NODELAY`로 Nagle 알고리즘을 끄는 것은 "작은 write를 모아서 한 번에 보내는 L4 최적화"를 포기하는 결정이고, 실시간성이 중요한 프로토콜에서 자주 쓴다.

OSI 모델 전체와 다른 계층은 [OSI 7 계층 모델](../../OSI_7_Layer_Model.md) 문서, TCP의 구체적인 동작 메커니즘(handshake, 상태 전이, 재전송 등)은 [TCP 프로토콜 동작 메커니즘](TCP.md) 문서를 참고한다.
