---
title: TCP 혼잡 제어와 커널 파라미터 튜닝
tags:
  - Network
  - TCP
  - Linux
  - Performance
  - Kernel
updated: 2026-05-04
---

# TCP 혼잡 제어와 커널 파라미터 튜닝

## 들어가며

TCP 튜닝은 평소엔 신경 쓸 일이 별로 없다. 그러다 어느 날 갑자기 "왜 인스턴스 간 처리량이 100Mbps도 안 나오죠?", "왜 CLOSE_WAIT가 만 개씩 쌓이죠?" 같은 질문이 날아온다. 그때 가서 `tcp_window_scaling`이 뭐고 `tcp_tw_reuse`가 뭔지 검색해도 늦다. 이미 장애 한복판이다.

이 문서는 5년 동안 트래픽 많은 백엔드 서버를 운영하면서 직접 만났던 TCP 관련 문제와 그걸 풀기 위해 건드린 커널 파라미터를 정리한 글이다. 책에 나오는 일반론보다는 "이런 상황에서 이 파라미터를 이렇게 만졌더니 이렇게 됐다" 같은 구체적인 경험 위주로 썼다.

## TCP 혼잡 제어 알고리즘

### 왜 혼잡 제어가 필요한가

TCP는 두 가지 흐름을 동시에 제어한다. 하나는 받는 쪽이 처리할 수 있는 양(수신 윈도우, rwnd), 다른 하나는 네트워크 경로가 감당할 수 있는 양(혼잡 윈도우, cwnd)이다. 실제로 송신자가 한 번에 보낼 수 있는 양은 `min(rwnd, cwnd)`다.

수신 윈도우는 받는 쪽이 ACK에 명시해서 알려준다. 문제는 혼잡 윈도우다. 네트워크 중간 라우터가 얼마나 막혔는지 송신자가 직접 알 방법이 없다. 그래서 TCP는 패킷 손실(retransmit)이나 RTT 변화를 보고 간접적으로 추정한다. 이 추정 알고리즘이 혼잡 제어다.

### Reno와 그 후예

오래된 알고리즘부터 보자. Reno는 가장 고전적인 형태다. cwnd를 천천히 늘리다가(slow start, congestion avoidance) 패킷 손실을 감지하면 절반으로 깎는다(multiplicative decrease). 이 단순한 모델은 LAN처럼 손실이 거의 없는 환경에선 잘 작동한다.

문제는 Long Fat Network에서 터진다. RTT 100ms에 1Gbps 회선을 쓰는 경우, 한 번 손실이 나면 cwnd가 절반으로 떨어진 뒤 다시 원상복구 되는 데 수십 초가 걸린다. 패킷 1개 잃었다고 처리량이 50%로 주저앉는 셈이다. 클라우드 리전 간 통신이 답답한 이유 중 하나가 이거다.

NewReno, SACK 등은 Reno의 회복 속도를 개선했지만 근본적인 한계는 그대로다.

### CUBIC

리눅스 2.6.19부터 기본값이 된 알고리즘이다. 이름 그대로 cwnd 회복 곡선을 3차 함수로 그린다. 손실이 난 직후엔 빠르게 회복하다가 직전 손실 지점 근처에서는 천천히 늘리는 식이다. RTT가 길어도 회복이 빨라서 광대역 환경에서 Reno보다 훨씬 좋다.

요즘 리눅스 서버에서 `sysctl net.ipv4.tcp_congestion_control`을 찍으면 거의 다 cubic이다. 이게 표준이라고 봐도 된다.

```bash
# 현재 사용 중인 알고리즘 확인
sysctl net.ipv4.tcp_congestion_control
# net.ipv4.tcp_congestion_control = cubic

# 사용 가능한 알고리즘 목록
sysctl net.ipv4.tcp_available_congestion_control
# net.ipv4.tcp_available_congestion_control = reno cubic bbr
```

### BBR

구글이 2016년에 공개한 알고리즘이다. 패킷 손실을 신호로 쓰지 않는다는 점에서 발상이 다르다. 대신 RTT 최솟값과 대역폭 최댓값을 측정해서 BDP(Bandwidth-Delay Product)에 맞는 송신 페이스를 직접 계산한다.

손실 기반 알고리즘은 큐가 꽉 차서 패킷이 떨어져야 비로소 cwnd를 줄인다. 라우터 버퍼가 큰 환경에선 이게 buffer bloat을 일으킨다. 큐가 잔뜩 쌓여서 RTT가 100ms에서 500ms로 늘어나도 손실은 안 나니까 TCP는 계속 밀어 넣는다. 결과적으로 처리량은 안 늘고 지연만 폭증한다.

BBR은 RTT가 늘어나는 순간을 감지하고 송신을 줄인다. 그래서 큐를 최소한으로 유지하면서 가용 대역폭을 거의 다 쓴다. 유튜브가 이걸로 해외 처리량 14% 끌어올렸다는 게 유명한 사례다.

```bash
# BBR 활성화 (qdisc도 fq로 바꿔야 한다)
echo 'net.core.default_qdisc=fq' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.conf
sysctl -p

# 모듈이 없으면 로드
modprobe tcp_bbr
```

BBR이 만능은 아니다. 같은 링크에서 CUBIC과 섞이면 BBR이 대역을 더 가져간다(공정성 문제). 사내망처럼 같은 알고리즘으로 통일된 환경에선 좋지만, 인터넷에 노출된 서버에서 무지성으로 켰다가 ISP나 CDN과 충돌이 생기는 경우도 있다. 실제로 한 번 사내 mTLS 게이트웨이에 BBR 켰다가 특정 통신사 회선에서만 처리량이 떨어지는 현상을 봤다. 결국 도로 CUBIC으로 돌렸다.

### 어떤 걸 써야 하나

판단 기준은 단순하다.

- LAN, 사내망 위주 → CUBIC 그대로
- 리전 간, 해외 향, 모바일 클라이언트 → BBR 검토
- 임베디드, 오래된 커널 → Reno (선택의 여지가 없음)

## BDP와 윈도우 크기

### BDP 계산

Bandwidth-Delay Product는 "이 회선에 한 번에 띄울 수 있는 데이터 양"이다.

```
BDP (bytes) = Bandwidth (bps) / 8 × RTT (sec)
```

예를 들어 1Gbps에 RTT 50ms 회선이라면:

```
BDP = 1,000,000,000 / 8 × 0.05 = 6,250,000 bytes ≈ 6 MB
```

송신 버퍼와 수신 윈도우가 6MB보다 작으면 회선을 절대 다 못 쓴다. 송신자는 ACK 받기 전에 버퍼만큼만 보낼 수 있는데, 6MB 보내고 멈춰 있으면 그 동안 회선이 노는 것이다.

리전 간(서울-도쿄, RTT 30ms 정도)에 EBS 백업을 보내는데 처리량이 50MB/s에서 안 올라가는 일이 있었다. 회선은 5Gbps인데 이상했다. BDP 계산해보면 5Gbps × 0.03s / 8 = 약 19MB다. 윈도우가 작아서 회선의 1/4도 못 쓰고 있었던 것이다. `net.core.rmem_max`를 32MB로 올리고 애플리케이션에서 SO_RCVBUF를 16MB로 설정하니 처리량이 4배 가까이 뛰었다.

### 윈도우 스케일링

원래 TCP 헤더의 윈도우 필드는 16비트라 최대 64KB다. 1Gbps에 RTT 1ms만 돼도 BDP가 125KB라 64KB로는 부족하다. 그래서 RFC 1323에서 윈도우 스케일링 옵션이 나왔다. SYN 단계에서 양쪽이 합의해 실제 윈도우 = 광고 윈도우 × 2^scale 형태로 확장한다.

요즘 커널은 기본으로 켜져 있다.

```bash
sysctl net.ipv4.tcp_window_scaling
# net.ipv4.tcp_window_scaling = 1
```

이걸 끄면 안 된다. 옛날 NAT 장비 때문에 끄라는 글이 가끔 있는데 2026년 환경에선 의미가 없다.

## 송수신 버퍼 튜닝

### 시스템 전역 설정

리눅스에는 두 종류의 버퍼 한도가 있다.

```bash
# 코어 네트워크 버퍼 (모든 소켓 타입에 적용되는 hard limit)
sysctl net.core.rmem_max
sysctl net.core.wmem_max

# TCP 자동 튜닝 범위 (min, default, max)
sysctl net.ipv4.tcp_rmem
# net.ipv4.tcp_rmem = 4096 131072 6291456
sysctl net.ipv4.tcp_wmem
# net.ipv4.tcp_wmem = 4096 16384 4194304
```

`tcp_rmem`의 세 값은 각각 최소, 초기, 최대 크기다. 커널이 메모리 압박 정도에 따라 이 범위 내에서 자동으로 조정한다. 기본 max가 6MB(rmem) / 4MB(wmem)인데, 광대역 환경에선 너무 작다.

리전 간 트래픽이 많은 서버라면 이 정도까진 올린다.

```bash
# /etc/sysctl.d/99-network.conf
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
```

주의: `tcp_rmem`의 max가 `net.core.rmem_max`보다 크면 의미가 없다. 둘 다 같이 올려야 한다. 이거 모르고 tcp_rmem만 올렸다가 효과 없다고 한참 헤맨 적이 있다.

### 애플리케이션 레벨 SO_RCVBUF/SO_SNDBUF

애플리케이션에서 setsockopt으로 직접 설정할 수도 있다. 다만 명시적으로 SO_RCVBUF를 호출하면 커널의 자동 튜닝이 꺼진다. 그래서 함부로 건드리는 게 더 위험하다.

```c
int recv_buf = 16 * 1024 * 1024;  // 16MB
setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &recv_buf, sizeof(recv_buf));

int send_buf = 16 * 1024 * 1024;
setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &send_buf, sizeof(send_buf));
```

리눅스는 요청한 값의 2배까지 할당한다(커널 부기 정보 공간). 그리고 `net.core.rmem_max` 한도에 걸린다. root가 아니면 한도를 못 넘는다.

자바라면 이런 식이다.

```java
ServerSocket server = new ServerSocket();
server.setReceiveBufferSize(16 * 1024 * 1024);
server.bind(new InetSocketAddress(8080));

Socket client = new Socket();
client.setSendBufferSize(16 * 1024 * 1024);
```

대부분의 웹 서버, RPC 프레임워크는 자동 튜닝에 맡기는 게 낫다. 직접 건드릴 때는 BDP 계산해서 명확한 근거가 있을 때만 한다. 무지성으로 키우면 메모리만 잡아먹고 효과는 없다. C10K 환경에서 소켓당 32MB씩 잡으면 만 개 연결만 돼도 320GB다.

## Nagle, Delayed ACK, TCP_NODELAY

### Nagle 알고리즘

작은 패킷을 모아서 보내려는 알고리즘이다. 이전에 보낸 패킷이 ACK를 못 받았으면 새 데이터를 큐에 쌓고 기다린다. 텔넷 같은 한 글자씩 보내는 환경에서 헤더 오버헤드를 줄이려고 만들어졌다.

문제는 요즘 워크로드와 안 맞는다는 거다. HTTP 요청 같은 게 헤더 + 바디로 두 번 write 되는 경우, Nagle은 첫 패킷 ACK를 기다리느라 두 번째를 못 보낸다.

### Delayed ACK

받는 쪽도 비슷한 짓을 한다. ACK를 즉시 보내지 않고 200ms 정도 기다린다. 그 사이에 보낼 데이터가 생기면 ACK를 piggyback 해서 같이 보낸다. 따로 ACK 패킷 만드는 비용을 아끼는 것이다.

### 둘이 만나면

Nagle은 ACK를 기다리고, Delayed ACK는 데이터를 기다린다. 서로 상대를 기다리는 데드락 비슷한 상황이 만들어진다. 결과적으로 작은 메시지 두 번 보내는 데 200ms씩 깎이는 일이 벌어진다.

Redis나 Memcached 클라이언트가 응답이 왜 이렇게 느리지 싶을 때 십중팔구 이 조합이다.

해결은 단순하다. 송신 쪽에서 TCP_NODELAY를 켠다.

```c
int flag = 1;
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));
```

자바.

```java
socket.setTcpNoDelay(true);
```

Go는 더 간단하다. net.TCPConn은 기본적으로 NODELAY가 켜져 있다.

대부분의 RPC 프레임워크(gRPC, Thrift), 메시지 브로커 클라이언트, Redis 클라이언트는 NODELAY가 기본이다. 직접 소켓 다룰 때만 신경 쓰면 된다.

다만 짧은 메시지를 빈도 높게 보내는 워크로드에서 NODELAY를 켜면 패킷 수가 폭증한다. 1만 RPS에 평균 메시지 100바이트면 패킷도 1만 개 + 헤더 오버헤드가 그대로다. 이 경우 애플리케이션 레벨에서 배치 묶음을 직접 구현하는 편이 낫다.

### TCP_QUICKACK

받는 쪽에서 Delayed ACK를 끄는 옵션이다. 다만 영구 설정이 아니라 매 read마다 다시 켜야 한다. 커널이 알아서 토글한다.

```c
int flag = 1;
setsockopt(fd, IPPROTO_TCP, TCP_QUICKACK, &flag, sizeof(flag));
```

요청-응답이 명확하게 핑퐁 식으로 도는 워크로드에서 가끔 쓴다. 실제로 효과 본 경우는 많지 않다.

## TIME_WAIT 누적

### 왜 쌓이는가

TCP를 능동적으로 종료한 쪽(먼저 FIN 보낸 쪽)은 마지막에 TIME_WAIT 상태로 들어간다. 2 × MSL(보통 60초) 동안 포트를 점유한다. 늦게 도착한 패킷이 다음 연결과 섞이지 않게 하기 위함이다.

문제는 부하 테스트나 Healthcheck 폭격 같은 시나리오다. 짧은 연결을 초당 수천 개씩 만들고 끊으면 TIME_WAIT가 만 단위로 쌓인다.

```bash
ss -tan state time-wait | wc -l
# 28491
```

`net.ipv4.ip_local_port_range`가 32768-60999면 가용 포트는 약 28000개다. TIME_WAIT가 그만큼 쌓이면 새 outbound 연결이 안 만들어진다. `connect: cannot assign requested address` 에러가 그거다.

### 해결 순서

먼저 의심해야 할 건 애플리케이션이다. HTTP 클라이언트를 매 요청마다 새로 만들고 있진 않은가, 커넥션 풀이 너무 작거나 keep-alive가 꺼져 있진 않은가. 대부분 여기서 잡힌다.

```python
# 매번 새 세션 만드는 안티 패턴
def call_api():
    return requests.get("http://internal/api")  # TIME_WAIT 폭탄

# 세션 재사용
session = requests.Session()
def call_api():
    return session.get("http://internal/api")
```

그래도 누적이 잡히지 않으면 커널 파라미터를 본다.

### tcp_tw_reuse

TIME_WAIT 상태인 소켓을 새 outbound 연결에 재활용한다. 타임스탬프(RFC 1323)가 켜져 있어야 안전하게 동작한다. 클라이언트 쪽에서 효과 본다.

```bash
sysctl -w net.ipv4.tcp_tw_reuse=1
```

이건 옛날부터 안전하다고 평가받는 옵션이다. 마음 편히 켤 수 있다.

### tcp_tw_recycle (사용 금지)

이름이 비슷해서 같이 켜는 사람이 있는데, 이건 절대 켜면 안 된다. 4.12 커널부터 아예 제거됐다. NAT 뒤에 있는 클라이언트들의 타임스탬프가 섞여서 SYN이 무작위로 드랍되는 문제가 있었다. 사내 NAT 환경에서 이거 켰다가 반쯤 죽은 사례가 인터넷에 차고 넘친다.

### 포트 범위 확장

```bash
sysctl -w net.ipv4.ip_local_port_range="10000 65535"
```

가용 포트를 약 두 배로 늘린다. tw_reuse와 같이 쓴다.

### tcp_max_tw_buckets

TIME_WAIT 상태 소켓의 최대 개수다. 이걸 넘으면 그냥 즉시 RST로 끊어버린다. 메모리 보호용이다.

```bash
sysctl net.ipv4.tcp_max_tw_buckets
# net.ipv4.tcp_max_tw_buckets = 65536
```

기본값으로도 보통 충분하다. 너무 작게 잡으면 정상 종료가 RST로 바뀌어서 다른 문제가 생긴다.

## CLOSE_WAIT 누적

### TIME_WAIT와 다른 문제

CLOSE_WAIT는 상대가 FIN을 보냈는데 우리 쪽이 close()를 안 한 상태다. 타임아웃이 없다. close 호출하기 전까지 영원히 그 상태다.

```bash
ss -tan state close-wait
```

CLOSE_WAIT가 쌓인다는 건 100% 애플리케이션 버그다. 커널 파라미터로 풀 수 없다. 코드를 봐야 한다.

흔한 패턴.

```java
// 예외 났을 때 close 안 함
Socket s = new Socket(host, port);
InputStream in = s.getInputStream();
process(in);  // 여기서 예외 → s.close() 호출 못 함
s.close();
```

```java
// try-with-resources로 보장
try (Socket s = new Socket(host, port)) {
    process(s.getInputStream());
}
```

DB 커넥션 풀, HTTP 클라이언트 풀에서 health check가 실패해서 풀이 소켓을 못 회수하는 경우도 있다. 풀 라이브러리(HikariCP, Apache HttpClient 등)의 `validation`, `evictionInterval` 설정을 다시 본다.

조사할 때 `lsof -i -nP | grep CLOSE_WAIT`로 어떤 프로세스가 들고 있는지 본 다음 그 프로세스의 코드를 따라간다.

## 자주 건드리는 net.ipv4.tcp_* 파라미터

### tcp_fin_timeout

FIN_WAIT_2 상태 타임아웃. 우리가 close 했는데 상대가 ACK만 보내고 FIN을 안 보낼 때 그 상태로 머문다. 기본 60초.

```bash
sysctl -w net.ipv4.tcp_fin_timeout=15
```

좀비 클라이언트가 많은 환경에서 줄여둔다.

### tcp_keepalive_*

```bash
sysctl net.ipv4.tcp_keepalive_time     # 7200 (2시간)
sysctl net.ipv4.tcp_keepalive_intvl    # 75
sysctl net.ipv4.tcp_keepalive_probes   # 9
```

기본 keep-alive는 2시간 동안 트래픽이 없으면 그제서야 프로브를 시작한다. LB나 NAT가 5분 만에 세션을 끊는 환경에선 쓸모가 없다. 그래서 보통 애플리케이션 레벨에서 더 짧게 설정한다.

```bash
# 사내 LB 타임아웃이 5분이면
sysctl -w net.ipv4.tcp_keepalive_time=240
sysctl -w net.ipv4.tcp_keepalive_intvl=30
sysctl -w net.ipv4.tcp_keepalive_probes=3
```

이러면 4분에 첫 프로브, 30초마다 3번 시도, 6분 안에 죽은 연결을 정리한다.

### tcp_syncookies

SYN flood 방어용. 백로그 큐가 꽉 차면 쿠키 기반으로 SYN+ACK를 만들어 보낸다. 합법 클라이언트의 ACK가 돌아오면 그제서야 진짜 소켓을 만든다.

```bash
sysctl -w net.ipv4.tcp_syncookies=1
```

요즘 배포판은 기본으로 켜져 있다. 끌 이유가 없다.

### tcp_max_syn_backlog, somaxconn

```bash
sysctl net.ipv4.tcp_max_syn_backlog
sysctl net.core.somaxconn
```

`tcp_max_syn_backlog`은 SYN_RECV 상태 큐 크기. `somaxconn`은 ESTABLISHED 후 accept() 대기 큐 크기. 둘 다 부하 큰 서버에선 기본 4096이 작다.

```bash
sysctl -w net.core.somaxconn=32768
sysctl -w net.ipv4.tcp_max_syn_backlog=32768
```

다만 listen() 시점에 backlog 인자를 같이 키워야 한다. 자바의 ServerSocket(port, backlog) 같은 거다. 커널 값만 키워도 애플리케이션이 작은 backlog로 listen 했으면 작은 쪽이 적용된다.

```java
// 기본값 50으로 listen 하면 somaxconn=32768도 의미 없음
new ServerSocket(8080, 32768);
```

### tcp_slow_start_after_idle

연결이 잠시 idle 상태였다가 다시 데이터를 보낼 때 cwnd를 초기화하고 slow start부터 다시 한다. 장수명 keep-alive 연결이 많은 환경(HTTP/2, gRPC 스트림)에선 처리량을 갉아먹는다.

```bash
sysctl -w net.ipv4.tcp_slow_start_after_idle=0
```

이거 끄면 idle 후에도 cwnd가 유지된다. 트래픽 패턴이 burst 한 API 게이트웨이에서 효과 본 적이 있다.

### tcp_notsent_lowat

송신 큐에 sent되지 않고 쌓일 수 있는 양의 상한이다. 기본은 무제한(uint max). HTTP/2 같은 멀티플렉싱 프로토콜에서 한 스트림이 송신 큐를 다 차지하는 head-of-line blocking을 줄이려고 작게 잡는다.

```bash
sysctl -w net.ipv4.tcp_notsent_lowat=131072
```

128KB 정도가 흔히 쓰는 값이다. 구글이 HTTP/2 운영 가이드에서 추천한 적 있다.

## 진단할 때 보는 것들

### 현재 상태 한눈에 보기

```bash
# 상태별 소켓 개수
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c

# 재전송 카운터
nstat -z | grep -i retrans
# TcpExtTCPLostRetransmit  142
# TcpRetransSegs           58291

# 혼잡 윈도우 / RTT를 소켓별로
ss -tin
```

`ss -tin`이 의외로 쓸 만하다. cwnd, rtt, rto, retrans 횟수를 연결별로 보여준다.

```
ESTAB  0  0  10.0.1.5:8080  10.0.2.7:53124
    cubic wscale:8,8 rto:204 rtt:1.234/0.567 ato:40
    mss:1448 cwnd:23 ssthresh:11 bytes_sent:1234567
    bytes_acked:1234500 segs_out:891 segs_in:445
```

### sysctl 한꺼번에 보기

```bash
sysctl -a 2>/dev/null | grep -E '^net\.(ipv4\.tcp_|core\.[rw]mem)' | sort
```

### 패킷 손실 확인

```bash
nstat -z TcpRetransSegs TcpInSegs
# 이 둘의 비율이 1% 넘으면 의심
```

## 실무 튜닝 사례 정리

### 사례 1: 리전 간 백업 처리량 부족

증상: 서울→도쿄 EBS 스냅샷 복사가 50MB/s에서 정체. 회선은 5Gbps.

원인: BDP 19MB인데 송수신 버퍼 max가 6MB.

처방:
```bash
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
```

결과: 200MB/s까지 상승. BBR도 같이 켰으면 더 올랐을 텐데 당시엔 검증이 안 됐어서 보류했다.

### 사례 2: API 게이트웨이 TIME_WAIT 폭주

증상: 피크 시간에 outbound 연결이 안 만들어지면서 502 에러 폭증.

원인: 백엔드 호출용 HTTP 클라이언트가 keep-alive를 안 쓰고 있었다. 매 요청마다 새 connection.

1차 처방: 클라이언트 keep-alive + 커넥션 풀 도입. 90% 해결.

2차 처방:
```bash
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 10000 65535
```

이걸로 잔여분도 안전 마진 안에 들어갔다.

### 사례 3: WebSocket 서버 CLOSE_WAIT 누적

증상: 서비스 시작 후 며칠 지나면 CLOSE_WAIT가 수천 개. 결국 파일 디스크립터 한도 도달하고 OOM.

원인: 클라이언트가 비정상 종료할 때(모바일 백그라운드 등) FIN이 와도 애플리케이션 핸들러가 여전히 read()에 블록되어 있었다. 핸들러 종료 후에야 close() 호출.

처방: read 타임아웃 추가, 주기적으로 idle connection 정리, keep-alive ping 추가. 커널 파라미터로 풀 수 없는 문제였다.

### 사례 4: gRPC 스트리밍 지연 spike

증상: 평소엔 1ms RTT인데 가끔 200ms씩 튀는 응답.

원인: gRPC 클라이언트가 Nagle은 안 켜져 있었지만 서버 쪽 Delayed ACK가 작동. 작은 메시지 응답에서 ACK 200ms 지연.

처방: 양쪽 다 TCP_NODELAY 명시적 설정. 라이브러리에 따라 기본값이 달라서 확인이 필요했다.

## 마지막으로

네트워크 튜닝의 첫 번째 원칙은 "측정 없이 만지지 마라"다. CUBIC을 BBR로 바꾸는 건 한 줄이지만 그게 효과 있는지, 부작용 없는지는 측정해야 안다. `ss -tin`으로 cwnd 보고, `nstat`으로 재전송률 보고, `tcpdump`로 실제 패킷 흐름 보고 나서 결정한다.

두 번째는 "애플리케이션 먼저, 커널 나중에"다. CLOSE_WAIT 누적을 sysctl로 풀 수 없듯이, 대부분의 TCP 문제는 코드에서 시작된다. 커넥션 풀 설정, keep-alive, 타임아웃, 에러 핸들링을 점검한 다음에 커널을 본다.

세 번째는 "기본값을 의심하라"다. 리눅스 기본값은 90년대 다이얼업 환경에 맞춰진 게 많다. 1Gbps 회선에서 윈도우 max가 6MB인 게 그런 잔재다. 환경에 맞게 다시 잡는다.
