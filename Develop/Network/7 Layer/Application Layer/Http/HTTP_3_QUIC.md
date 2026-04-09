---
title: HTTP/3와 QUIC
tags: [network, 7-layer, application-layer, http3, quic, udp, tls, performance, qpack]
updated: 2026-04-09
---

# HTTP/3와 QUIC

## 개요

HTTP/3는 TCP 위에서 동작하던 이전 HTTP 버전과 달리 **QUIC** 위에서 동작하는 차세대 프로토콜이다. QUIC은 구글이 개발하고 IETF가 표준화한 UDP 기반 전송 프로토콜로, TCP의 구조적 한계를 해결한다.

```
HTTP/1.1 → TCP + TLS 1.2/1.3       → 텍스트 기반, HOL 블로킹
HTTP/2   → TCP + TLS 1.2/1.3       → 바이너리, 멀티플렉싱 (TCP HOL 블로킹 잔존)
HTTP/3   → QUIC (UDP 기반) + TLS 1.3 → HOL 블로킹 완전 제거, 0-RTT 연결
```

### 프로토콜 스택 비교

```
┌───────────┐  ┌───────────┐  ┌───────────┐
│  HTTP/1.1 │  │  HTTP/2   │  │  HTTP/3   │
├───────────┤  ├───────────┤  ├───────────┤
│           │  │  HPACK    │  │  QPACK    │
├───────────┤  ├───────────┤  ├───────────┤
│  TLS 1.2  │  │  TLS 1.3  │  │   QUIC    │
├───────────┤  ├───────────┤  │  (TLS 1.3 │
│   TCP     │  │   TCP     │  │   내장)   │
├───────────┤  ├───────────┤  ├───────────┤
│   IP      │  │   IP      │  │   UDP     │
└───────────┘  └───────────┘  ├───────────┤
                               │   IP      │
                               └───────────┘
```

HTTP/2까지는 TCP 위에 TLS를 별도 레이어로 올렸다. HTTP/3에서는 QUIC 내부에 TLS 1.3이 통합되어 있어서 레이어가 줄어든다.

---

## TCP의 한계와 QUIC의 등장

### Head-of-Line (HOL) 블로킹

```
HTTP/2의 멀티플렉싱 (TCP):
  Stream 1: [패킷 A] [패킷 B] [X 손실] [패킷 D]
  Stream 2: [패킷 E] [패킷 F]
  Stream 3: [패킷 G]

  → 패킷 C가 손실되면 TCP는 재전송될 때까지
    Stream 1뿐 아니라 Stream 2, 3도 모두 대기
    (OS 커널 레벨에서 순서 보장하기 때문)

HTTP/3 (QUIC):
  Stream 1: [패킷 A] [패킷 B] [X 손실] → Stream 1만 대기
  Stream 2: [패킷 E] [패킷 F]          → 계속 진행
  Stream 3: [패킷 G]                    → 계속 진행
```

### 연결 수립 지연

```
TCP + TLS 1.2:
  Client → Server: SYN                        (1 RTT)
  Client ← Server: SYN-ACK
  Client → Server: ACK + ClientHello          (2 RTT)
  Client ← Server: ServerHello + Certificate
  Client → Server: Finished                   (3 RTT)
  → 총 3 RTT 후 데이터 전송 시작

TCP + TLS 1.3:
  → 총 2 RTT (TLS 1.3 개선)

QUIC (HTTP/3):
  → 최초 연결: 1 RTT
  → 재연결(0-RTT): 0 RTT (이전 세션 정보 재사용)
```

---

## QUIC 핵심 특징

### 1. 스트림 단위 독립적 흐름 제어

QUIC은 스트림을 OS 커널이 아닌 **애플리케이션 레이어**에서 관리한다. 패킷 손실이 해당 스트림에만 영향을 주고 다른 스트림은 독립적으로 진행된다.

### 2. 연결 이전 (Connection Migration)

```
TCP: IP + 포트로 연결 식별
  → WiFi → LTE 전환 시 IP 바뀌면 연결 끊김, 재연결 필요

QUIC: 64비트 Connection ID로 연결 식별
  → WiFi → LTE 전환해도 Connection ID 유지 → 연결 유지
  → 모바일 환경에서 큰 장점
```

### 3. TLS 1.3 내장

QUIC은 TLS를 별도 레이어로 추가하는 것이 아니라 **프로토콜 내부에 통합**했다. 핸드셰이크와 암호화가 동시에 이루어지므로 왕복 횟수가 줄어든다.

### 4. 0-RTT 재연결

```
최초 연결: 1 RTT
  Client → Server: ClientHello + QUIC 파라미터
  Client ← Server: ServerHello + 인증서 + 서버 파라미터
  → 이미 1 RTT에 데이터 전송 가능

재연결 (0-RTT):
  → 이전 세션에서 교환한 Session Ticket 재사용
  → 핸드셰이크 없이 바로 데이터 전송
  → 단, 재전송 공격(Replay Attack) 위험 있으므로 멱등 요청(GET)에만 적용
```

---

## QUIC 패킷 구조

QUIC 패킷은 크게 **Long Header**와 **Short Header** 두 가지로 나뉜다.

### Long Header (연결 수립 시)

Initial, Handshake, 0-RTT 패킷에 사용된다.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|1| Type(2) |   ← Header Form(1) = 1 (Long), Fixed Bit(1) = 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Version (32)                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DCID Len (8)  |        Destination Connection ID (0..160)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| SCID Len (8)  |         Source Connection ID (0..160)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Type-Specific Payload ...                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Header Form**: 1이면 Long Header, 0이면 Short Header
- **Type**: Initial(0x00), 0-RTT(0x01), Handshake(0x02), Retry(0x03)
- **Version**: QUIC 버전 (예: 0x00000001 = QUIC v1)
- **DCID/SCID**: Destination/Source Connection ID. 커넥션 마이그레이션의 핵심

### Short Header (데이터 전송 시)

핸드셰이크 이후 실제 데이터 전송에 사용된다. Long Header보다 오버헤드가 작다.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|0|1|S|R|R|KP|PN|  ← Header Form(1) = 0 (Short)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Destination Connection ID (0..160)              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Packet Number (8/16/24/32)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Protected Payload ...                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Spin Bit(S)**: 네트워크 지연 측정용. 서버/클라이언트가 번갈아 반전시킴
- **Key Phase(KP)**: 키 업데이트 여부 표시
- **Packet Number**: 스트림이 아닌 패킷 단위 번호. TCP의 시퀀스 넘버와 다르게 **절대 재사용하지 않는다**

### QUIC 프레임 구조

하나의 QUIC 패킷 안에 여러 프레임이 들어간다.

```
QUIC 패킷
├── Frame 1: STREAM (Stream ID=4, Offset=0, Data="GET /index.html")
├── Frame 2: ACK (Largest Ack=15, Ack Delay=3ms)
└── Frame 3: STREAM (Stream ID=8, Offset=0, Data="GET /style.css")
```

주요 프레임 타입:

| 타입 | 설명 |
|------|------|
| STREAM | 스트림 데이터 전송 |
| ACK | 수신 확인 |
| CRYPTO | TLS 핸드셰이크 데이터 |
| NEW_CONNECTION_ID | 커넥션 마이그레이션용 ID 전달 |
| CONNECTION_CLOSE | 연결 종료 |
| MAX_STREAM_DATA | 스트림별 흐름 제어 |
| PATH_CHALLENGE / PATH_RESPONSE | 경로 유효성 검증 |

TCP 세그먼트와 다른 점은, QUIC은 하나의 UDP 데이터그램 안에 서로 다른 스트림의 프레임을 섞어 넣을 수 있다는 것이다. 이게 스트림 단위 독립 흐름 제어의 기반이 된다.

---

## QPACK 헤더 압축

HTTP/2에서 HPACK을 쓰는 것처럼 HTTP/3에서는 QPACK을 쓴다. HPACK을 그대로 사용할 수 없는 이유가 있다.

### HPACK의 문제

HPACK은 동적 테이블을 순서대로 업데이트하는 구조다. 인코더가 "이 헤더를 인덱스 62에 넣었다"라고 하면, 디코더도 같은 순서로 받아야 62번에 같은 값이 들어간다.

```
HPACK (HTTP/2):

  요청 1: "content-type: application/json" → 동적 테이블 인덱스 62에 추가
  요청 2: "content-type: text/html"        → 인덱스 63에 추가
  요청 3: 인덱스 62 참조                    → "application/json" 기대

  → TCP가 순서를 보장하므로 문제 없음

QUIC에서 HPACK을 그대로 쓰면:
  요청 1, 2가 서로 다른 스트림으로 전송
  → 요청 2가 먼저 도착하면 인덱스 62에 "text/html"이 들어감
  → 요청 3이 인덱스 62를 참조하면 잘못된 값을 읽음
```

### QPACK 동작 방식

QPACK은 이 문제를 **단방향 스트림 2개**로 해결한다.

```
┌──────────────────────────────────────────────────────┐
│                    QPACK 구조                         │
│                                                       │
│  Encoder Stream (단방향, 인코더 → 디코더)              │
│  ├── "동적 테이블에 content-type: application/json 추가" │
│  ├── "동적 테이블에 authorization: Bearer xxx 추가"     │
│  └── ...                                              │
│                                                       │
│  Decoder Stream (단방향, 디코더 → 인코더)              │
│  ├── "인덱스 62까지 처리 완료"                         │
│  └── ...                                              │
│                                                       │
│  Request Streams (양방향)                              │
│  ├── Stream 4: 헤더 블록 (Required Insert Count = 1)  │
│  ├── Stream 8: 헤더 블록 (Required Insert Count = 2)  │
│  └── ...                                              │
└──────────────────────────────────────────────────────┘
```

핵심 메커니즘:

- **Encoder Stream**: 동적 테이블 업데이트 명령만 전달하는 전용 스트림. 순서가 보장된다.
- **Decoder Stream**: 디코더가 "여기까지 테이블 업데이트를 반영했다"고 인코더에 알려줌
- **Required Insert Count**: 각 헤더 블록이 "동적 테이블에 최소 N개의 엔트리가 있어야 디코딩 가능하다"고 선언
- **Blocked Stream**: 아직 테이블 업데이트가 도착하지 않아서 디코딩을 못하는 스트림. `SETTINGS_QPACK_BLOCKED_STREAMS`로 최대 개수를 제한

QPACK 정적 테이블은 HPACK보다 엔트리가 많다. HPACK이 61개인 데 비해 QPACK은 99개다. `:method: CONNECT`, `:status: 103` 등 HTTP/3에서 새로 추가된 항목이 포함된다.

---

## HTTP 버전 비교

| 항목 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------|---------|--------|--------|
| **전송 계층** | TCP | TCP | QUIC (UDP) |
| **스트림** | 없음 (파이프라이닝) | 멀티플렉싱 | 독립 멀티플렉싱 |
| **HOL 블로킹** | 있음 | TCP 레벨 잔존 | 없음 |
| **헤더 압축** | 없음 | HPACK | QPACK |
| **TLS** | 선택 | 선택 (실질적 필수) | 필수 (내장) |
| **연결 수립** | 2 RTT | 2 RTT | 1 RTT / 0 RTT |
| **연결 이전** | 불가 | 불가 | 가능 (Connection ID) |
| **표준화** | RFC 2616 (1999) | RFC 7540 (2015) | RFC 9114 (2022) |

---

## curl로 HTTP/3 테스트

### curl HTTP/3 지원 확인

curl 7.88 이상에서 HTTP/3를 지원한다. 단, 빌드 시 QUIC 라이브러리가 포함되어야 한다.

```bash
# curl이 HTTP/3를 지원하는지 확인
curl --version
# 출력에 HTTP3 또는 alt-svc가 포함되어 있어야 함
# Features: ... HTTP3 ...

# macOS에서 HTTP/3 지원 curl 설치
brew install curl
# Homebrew curl은 보통 HTTP/3 지원이 포함됨
# 시스템 curl(/usr/bin/curl)은 미지원인 경우가 있으니 확인 필요
```

### 기본 테스트

```bash
# HTTP/3로 요청
curl --http3 -I https://www.google.com
# HTTP/3 연결이 실패하면 에러 발생 (폴백하지 않음)

# HTTP/3 우선 시도, 실패 시 HTTP/2로 폴백
curl --http3-only -I https://www.cloudflare.com  # HTTP/3만 사용 (폴백 없음)
curl --http3 -I https://www.cloudflare.com       # HTTP/3 우선, 폴백 가능

# 상세 연결 정보 확인 (-v)
curl --http3 -v https://www.cloudflare.com 2>&1 | head -30
# * using HTTP/3
# * QUIC connection 0x... connected to 104.16.132.229
# *   CApath: /etc/ssl/certs
# * [QUIC] params: max_idle_timeout=30000ms ...
```

### 성능 측정

```bash
# 연결 시간 상세 측정
curl --http3 -o /dev/null -w "\
  DNS:        %{time_namelookup}s\n\
  Connect:    %{time_connect}s\n\
  TLS:        %{time_appconnect}s\n\
  TTFB:       %{time_starttransfer}s\n\
  Total:      %{time_total}s\n\
  Protocol:   %{http_version}\n" \
  -s https://www.cloudflare.com

# HTTP/2와 비교
curl -o /dev/null -w "HTTP/2 TTFB: %{time_starttransfer}s Total: %{time_total}s\n" \
  -s https://www.cloudflare.com

curl --http3 -o /dev/null -w "HTTP/3 TTFB: %{time_starttransfer}s Total: %{time_total}s\n" \
  -s https://www.cloudflare.com
```

### Alt-Svc 헤더 확인

브라우저가 HTTP/3를 사용하려면 서버가 `Alt-Svc` 헤더를 보내야 한다.

```bash
# Alt-Svc 헤더 확인 (HTTP/2로 요청해서 HTTP/3 지원 여부 확인)
curl -sI https://www.cloudflare.com | grep -i alt-svc
# alt-svc: h3=":443"; ma=86400

# h3=":443"  → HTTP/3를 443 포트에서 지원
# ma=86400   → 이 정보를 86400초(24시간) 동안 캐싱
```

---

## CDN/로드밸런서 HTTP/3 지원 현황

### Cloudflare

- 2019년부터 HTTP/3 지원. 가장 먼저 대규모로 배포한 CDN
- 대시보드에서 클릭 한 번으로 활성화: **Speed → Optimization → Protocol Optimization → HTTP/3**
- 별도 설정 없이 `Alt-Svc` 헤더 자동 추가
- QUIC 버전: RFC 9000 (QUIC v1)

```bash
# Cloudflare HTTP/3 확인
curl -sI https://your-domain.com | grep -i alt-svc
# alt-svc: h3=":443"; ma=86400
```

### AWS CloudFront

- 2022년 8월부터 HTTP/3 지원
- 배포(Distribution) 설정에서 활성화: **Supported HTTP versions → HTTP/3 체크**
- 원본(Origin)과의 통신은 HTTP/1.1 또는 HTTP/2만 지원. CloudFront → Origin 구간은 HTTP/3를 쓰지 않는다
- ALB(Application Load Balancer)는 2026년 현재 HTTP/3 미지원. CloudFront를 앞에 두는 구성이 필요하다

```
클라이언트 ──HTTP/3──→ CloudFront ──HTTP/2──→ ALB ──HTTP/1.1──→ EC2
                       (QUIC)                 (TCP)            (TCP)
```

### Google Cloud CDN / Cloud Load Balancing

- 외부 HTTP(S) 로드밸런서에서 HTTP/3 자동 지원 (기본 활성화)
- `Alt-Svc` 헤더를 자동으로 응답에 추가
- 비활성화하려면 커스텀 헤더로 `Alt-Svc` 값을 비워야 함

### Akamai

- 2023년부터 HTTP/3 지원
- Ion, Dynamic Site Accelerator 등 주요 제품에서 활성화 가능
- Property Manager에서 HTTP/3 behavior 추가

### Nginx (직접 운영)

- 1.25.0부터 공식 HTTP/3 지원 (이전에는 quiche 패치 필요)
- OpenSSL 3.x 이상 또는 BoringSSL 필요
- UDP 443 포트 방화벽 오픈 필수 — 이걸 빠뜨리는 경우가 많다

### 주의사항

| 항목 | 내용 |
|------|------|
| **UDP 방화벽** | 기업 네트워크에서 UDP 443을 차단하는 경우가 있음. 이 경우 HTTP/3 연결이 타임아웃되고 HTTP/2로 폴백 |
| **로드밸런서 구간** | CDN → Origin 구간은 대부분 TCP(HTTP/2 또는 HTTP/1.1). 엔드 투 엔드 HTTP/3는 아님 |
| **비용** | Cloudflare는 무료 플랜에서도 HTTP/3 제공. AWS는 CloudFront 요금에 포함 |
| **QUIC 버전** | 서비스마다 지원하는 QUIC 버전이 다를 수 있음. RFC 9000 (v1)을 지원하는지 확인 |

---

## Nginx에서 HTTP/3 활성화

```nginx
# Nginx 1.25+ 또는 quiche 패치 버전 필요
server {
    # HTTP/2 (TCP 443)
    listen 443 ssl;
    http2 on;

    # HTTP/3 (UDP 443)
    listen 443 quic reuseport;

    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # QUIC은 TLS 1.3만 지원
    ssl_protocols TLSv1.3;

    # HTTP/3 지원 알림 헤더 (브라우저가 다음 요청부터 HTTP/3 사용)
    add_header Alt-Svc 'h3=":443"; ma=86400';

    location / {
        proxy_pass http://backend;
    }
}
```

참고: Nginx 1.25.1부터 `http2` 지시자가 `listen` 파라미터에서 분리됐다. `listen 443 ssl http2;`가 아니라 `listen 443 ssl;` + `http2 on;`으로 쓴다.

---

## Node.js에서 HTTP/3

```typescript
// Node.js 22+ 실험적 HTTP/3 지원 (node:http3 모듈)
// 현재 실무에서는 Nginx/Caddy 등 웹서버에서 HTTP/3를 처리하고
// 백엔드는 HTTP/1.1 또는 HTTP/2로 통신하는 것이 일반적

// Caddy (자동 HTTPS + HTTP/3)
// Caddyfile:
// example.com {
//   reverse_proxy localhost:3000
// }
// → Caddy는 기본적으로 HTTP/3 활성화
```

---

## 실무 트러블슈팅

### HTTP/3 연결이 안 될 때 확인 순서

```
1. UDP 443 포트 열려 있는가?
   → 서버 방화벽, 보안 그룹, 네트워크 장비 모두 확인
   → TCP 443만 열고 UDP 443을 안 여는 실수가 흔함

2. TLS 1.3이 설정되어 있는가?
   → QUIC은 TLS 1.3만 지원. TLS 1.2 설정만 있으면 실패

3. Alt-Svc 헤더가 응답에 포함되는가?
   → curl -sI https://your-domain.com | grep alt-svc

4. 클라이언트가 HTTP/3를 지원하는가?
   → 사내 프록시가 QUIC을 차단하는 경우 있음
   → 일부 기업 방화벽은 UDP 트래픽을 전면 차단
```

### Wireshark로 QUIC 트래픽 분석

```
# Wireshark 캡처 필터 (캡처 시)
udp port 443

# Wireshark 디스플레이 필터 (분석 시)
quic                              # 모든 QUIC 패킷
quic.connection.number == 0       # 특정 커넥션
quic.frame_type == 0x06           # STREAM 프레임만
quic.frame_type == 0x02           # ACK 프레임만
quic.long.packet_type == 0        # Initial 패킷
quic.long.packet_type == 2        # Handshake 패킷
quic.version                      # QUIC 버전별 필터
```

QUIC은 페이로드가 암호화되어 있어서 Wireshark에서 내용을 보려면 **TLS 키 로그**가 필요하다.

```bash
# 브라우저에서 TLS 키 로그 파일 생성
export SSLKEYLOGFILE=~/quic_keylog.txt

# Chrome 실행 (키 로그 파일 자동 기록)
# macOS
open -a "Google Chrome"

# Wireshark 설정
# Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename
# → ~/quic_keylog.txt 지정
# 이후 QUIC 패킷의 복호화된 내용 확인 가능
```

### qlog을 이용한 디버깅

qlog은 QUIC/HTTP/3 전용 로깅 포맷이다. Wireshark보다 QUIC 내부 동작을 상세하게 볼 수 있다.

```bash
# curl에서 qlog 활성화 (curl 8.6+, quiche 빌드)
QLOGDIR=/tmp/qlogs curl --http3 https://www.cloudflare.com

# qlog 시각화
# https://qvis.quictools.info/ 에서 qlog 파일 업로드
# 스트림별 타임라인, 패킷 손실, 혼잡 제어 그래프 확인 가능
```

### 자주 겪는 문제

**문제: HTTP/3 연결 후 간헐적 타임아웃**

```
원인: 중간 네트워크 장비(NAT, 방화벽)가 UDP 세션을 빠르게 만료시킴
  → TCP는 보통 300초 이상 유지하지만
  → UDP는 30초 정도에 만료하는 장비가 있음

대응:
  → QUIC의 idle timeout을 짧게 설정 (서버 설정)
  → 주기적으로 PING 프레임 전송
  → Nginx: quic_timeout 설정 확인
```

**문제: 특정 클라이언트에서만 HTTP/3 안 됨**

```
원인 후보:
  1. 기업 방화벽/프록시가 UDP 차단
  2. 오래된 공유기의 NAT 테이블이 QUIC Connection ID를 못 다룸
  3. 클라이언트 OS의 UDP 버퍼 크기 부족

확인 방법:
  # 해당 클라이언트에서
  curl --http3 -v https://your-domain.com 2>&1 | grep -i quic
  # "connection refused" → UDP 포트 차단
  # "handshake failed"  → TLS 문제 또는 QUIC 버전 불일치
```

**문제: HTTP/3 활성화 후 전체적으로 느려짐**

```
원인 후보:
  1. 서버의 UDP 수신 버퍼가 작음
  2. CPU 사용량 증가 (QUIC은 유저스페이스 처리, TCP는 커널)
  3. GSO(Generic Segmentation Offload) 미지원 NIC

대응:
  # UDP 버퍼 크기 확인 및 조정 (Linux)
  sysctl net.core.rmem_max
  sysctl net.core.wmem_max

  # 권장 설정
  sysctl -w net.core.rmem_max=2500000
  sysctl -w net.core.wmem_max=2500000
```

---

## 성능 벤치마크 비교

### 연결 수립 시간

```
테스트 조건: 서울 → 미국 서부 (RTT ~150ms)

TCP + TLS 1.2 (HTTP/1.1):
  SYN/ACK:     150ms (1 RTT)
  TLS:         300ms (2 RTT)
  합계:        450ms (3 RTT)

TCP + TLS 1.3 (HTTP/2):
  SYN/ACK:     150ms (1 RTT)
  TLS:         150ms (1 RTT)
  합계:        300ms (2 RTT)

QUIC (HTTP/3):
  최초 연결:   150ms (1 RTT)
  재연결:        0ms (0 RTT)
```

RTT가 높을수록 HTTP/3의 연결 수립 시간 이점이 커진다. 한국-미국 간처럼 RTT가 100ms 이상인 경우 체감 차이가 크다.

### 패킷 손실 환경에서의 비교

```
테스트: 100개의 이미지(각 50KB)를 동시 요청
네트워크: RTT 100ms

패킷 손실 0%:
  HTTP/2:  1.2초
  HTTP/3:  1.1초
  → 차이 미미

패킷 손실 1%:
  HTTP/2:  2.8초  (TCP HOL 블로킹 발생)
  HTTP/3:  1.5초  (손실된 스트림만 영향)
  → HTTP/3가 약 46% 빠름

패킷 손실 3%:
  HTTP/2:  5.1초
  HTTP/3:  2.3초
  → HTTP/3가 약 55% 빠름

패킷 손실 5%:
  HTTP/2:  8.7초
  HTTP/3:  3.8초
  → HTTP/3가 약 56% 빠름
```

패킷 손실이 없으면 HTTP/2와 HTTP/3의 성능 차이는 거의 없다. 패킷 손실이 1%만 넘어가도 차이가 벌어지기 시작한다. 모바일 네트워크에서 패킷 손실률이 1~5% 정도인 경우가 흔하기 때문에 모바일 서비스에서 HTTP/3의 체감 효과가 크다.

### 서버 리소스 비교

```
동시 접속 10,000건 기준 (Nginx, 동일 하드웨어):

             HTTP/2 (TCP)    HTTP/3 (QUIC)
CPU 사용률:    35%              48%
메모리:        1.2GB            1.8GB
처리량:        45,000 req/s     42,000 req/s
```

QUIC은 유저스페이스에서 동작하기 때문에 TCP보다 CPU와 메모리를 더 쓴다. 서버 입장에서는 HTTP/3가 반드시 유리한 것은 아니다. 클라이언트 체감 속도(특히 모바일, 고지연 환경)와 서버 리소스 사이에서 트레이드오프가 발생한다.

---

## 브라우저 지원 현황 (2026 기준)

| 브라우저 | HTTP/3 지원 |
|--------|------------|
| Chrome | 87+ (2020.11~) |
| Firefox | 88+ (2021.04~) |
| Safari | 14+ (2020.09~) |
| Edge | 87+ (2020.11~) |

전 세계 HTTP/3 트래픽 비율: 약 35% (2025 기준, 지속 증가 중)

---

## 언제 HTTP/3가 유리한가

```
HTTP/3 도입이 의미 있는 환경:
  - 모바일 네트워크 (WiFi ↔ LTE 전환 잦음)
  - 패킷 손실률이 높은 환경 (무선, 약한 신호)
  - 지연이 높은 원거리 연결 (글로벌 서비스)
  - 다수의 소규모 리소스 요청 (SPA, 마이크로프론트엔드)

HTTP/2로 충분한 환경:
  - 안정적인 유선 네트워크 (데이터센터 내부)
  - 내부 서비스 간 통신 (gRPC 등)
  - 대용량 단일 파일 전송
  - 서버 CPU/메모리 리소스가 제한된 환경
```

---

## 참고 RFC

| 문서 | 내용 |
|------|------|
| RFC 9000 | QUIC: A UDP-Based Multiplexed and Secure Transport |
| RFC 9001 | Using TLS to Secure QUIC |
| RFC 9002 | QUIC Loss Detection and Congestion Control |
| RFC 9114 | HTTP/3 |
| RFC 9204 | QPACK: Field Compression for HTTP/3 |
