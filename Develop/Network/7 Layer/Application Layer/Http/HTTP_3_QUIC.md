---
title: HTTP/3와 QUIC
tags: [network, 7-layer, application-layer, http3, quic, udp, tls, performance, qpack]
updated: 2026-06-03
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

QUIC이 등장한 이유를 단순히 "TCP가 느려서"라고 정리하면 핵심을 놓친다. 실제 동기는 네 가지다. 각각이 왜 TCP로는 풀 수 없는 문제였는지 알아야 QUIC 설계 결정의 의미가 보인다.

### 1. Head-of-Line (HOL) 블로킹

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

TCP는 바이트 스트림 추상화를 OS 커널에서 제공한다. recv() 시스템 콜은 손실된 세그먼트가 도착할 때까지 후속 바이트를 애플리케이션에 넘기지 않는다. HTTP/2가 한 커넥션에 여러 스트림을 다중화해도 결국 단일 TCP 바이트 스트림에 얹혀 있기 때문에, 한 스트림의 패킷 손실이 다른 모든 스트림을 막는다. QUIC은 스트림 추상화를 유저스페이스로 끌어올려서 손실 영향을 해당 스트림에 가둔다.

### 2. 연결 수립 지연

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

TCP Fast Open(TFO)으로 TCP 핸드셰이크를 0 RTT로 만들려는 시도가 있었지만, 미들박스가 TFO 쿠키를 가진 SYN 패킷을 손상시키거나 차단하는 사례가 많아 실제 배포율이 한 자릿수에 머물렀다. QUIC은 전송 계층 핸드셰이크와 TLS 핸드셰이크를 한 번에 묶고 UDP 위에서 동작하기 때문에 미들박스 간섭에서 자유롭다.

### 3. 프로토콜 진화의 정체 (Ossification)

TCP 헤더 옵션을 새로 정의해도 인터넷 곳곳의 미들박스가 알 수 없는 옵션을 가진 세그먼트를 떨어뜨린다. 새 TCP 옵션이 실제 배포되기까지 10년 단위가 걸린 사례가 다수다. MPTCP, SACK 확장, TFO 모두 같은 문제를 겪었다.

```
TCP의 진화 정체 사례:
  ECN (RFC 3168, 2001) → 2020년대에도 일부 네트워크에서 비활성화
  TCP Fast Open (RFC 7413, 2014) → 모바일 캐리어 차단으로 실패
  MPTCP (RFC 6824, 2013) → 애플 외에 본격 채택 없음

QUIC의 대응:
  → 전체 헤더 외 모든 필드를 암호화
  → 미들박스가 내용을 보거나 수정할 수 없게 만듦
  → "암호화된 전송"이 핵심 설계 결정
  → 결과적으로 프로토콜이 빠르게 진화할 수 있게 됨
```

QUIC 패킷의 페이로드만 암호화하는 게 아니라, 거의 모든 헤더 필드까지 암호화해서 미들박스가 들여다보거나 수정할 수 없게 만들었다. "암호화는 보안만이 아니라 프로토콜 진화를 위해서도 필요하다"가 QUIC 설계자들이 자주 말하는 표현이다.

### 4. 커널과 분리된 구현

TCP는 OS 커널에 박혀 있어서 새 알고리즘을 도입하려면 커널 업그레이드가 필요하다. 서버는 그나마 가능해도 클라이언트(특히 모바일 디바이스)의 커널은 통제 불가능하다. QUIC은 유저스페이스 라이브러리로 구현되므로 애플리케이션 배포만으로 업그레이드가 끝난다.

```
TCP 혼잡 제어 알고리즘 배포:
  Linux 커널에 CUBIC 도입 (2.6.19, 2006)
  BBR 도입 (4.9, 2016)
  → 사용자가 커널 업데이트해야 적용

QUIC 혼잡 제어 변경:
  서버 라이브러리 업그레이드 → 즉시 적용
  Chrome 자체 QUIC 스택 업데이트 → 자동 배포로 며칠 안에 전 사용자 적용
```

이 차이는 실험과 개선 속도에서 큰 격차를 만든다. 구글은 자사 서비스에 QUIC을 배포하면서 매주 단위로 혼잡 제어 알고리즘을 실험하고 롤백할 수 있었다.

---

## QUIC 핵심 특징

### 1. 스트림 단위 독립적 흐름 제어

QUIC은 스트림을 OS 커널이 아닌 애플리케이션 레이어에서 관리한다. 패킷 손실이 해당 스트림에만 영향을 주고 다른 스트림은 독립적으로 진행된다.

흐름 제어는 두 단계로 작동한다.

```
연결 레벨 흐름 제어:
  → MAX_DATA 프레임으로 전체 연결에 흐를 수 있는 바이트 한도 지정
  → 한도를 초과하면 모든 스트림 전송 중단

스트림 레벨 흐름 제어:
  → MAX_STREAM_DATA 프레임으로 각 스트림별 한도 지정
  → 한 스트림이 정체되어도 다른 스트림은 독립적으로 진행
```

스트림 ID 자체에도 의미가 있다. 짝수 ID는 서버 개시, 홀수는 클라이언트 개시. 가장 낮은 2비트로 양방향(0x00, 0x01)과 단방향(0x02, 0x03)을 구분한다. 이 규칙 덕분에 양쪽이 동시에 스트림을 만들어도 ID 충돌이 없다.

### 2. TLS 1.3 내장

QUIC은 TLS를 별도 레이어로 추가하는 게 아니라 프로토콜 내부에 통합했다. 핸드셰이크와 암호화가 동시에 이루어지므로 왕복 횟수가 줄어든다.

```
TCP+TLS의 핸드셰이크 구조:
  [TCP 핸드셰이크: 1 RTT] → [TLS 핸드셰이크: 1 RTT] → 데이터 전송
  → 직렬화된 두 단계

QUIC의 핸드셰이크 구조:
  [QUIC 핸드셰이크 = 전송 파라미터 + TLS 핸드셰이크: 1 RTT] → 데이터 전송
  → CRYPTO 프레임에 TLS 핸드셰이크 메시지가 담겨 함께 전달
```

QUIC은 TLS 레코드 레이어를 쓰지 않고, TLS 메시지를 QUIC의 CRYPTO 프레임에 담아 전달한다. 그래서 TLS 1.2는 QUIC과 통합할 수 없다. TLS 1.3 전용이다.

---

## 0-RTT 핸드셰이크 상세

QUIC 도입의 가장 큰 동기 중 하나가 0-RTT 재연결이다. 모바일 환경에서 1 RTT(50~300ms)를 절약하는 것은 사용자 체감으로 직결된다.

### 동작 메커니즘

```
[1차 연결: 1-RTT]

  Client                                                Server
    │                                                      │
    ├──── Initial: ClientHello + transport params ────────>│
    │     (TLS 1.3 ClientHello + QUIC 파라미터)             │
    │                                                      │
    │<──── Initial: ServerHello + Certificate + ──────────│
    │      EncryptedExtensions + Finished                  │
    │      + NewSessionTicket (PSK)                        │
    │                                                      │
    ├──── Handshake: Finished ────────────────────────────>│
    │                                                      │
    ├──── 1-RTT: 실제 데이터 ──────────────────────────────>│
    │                                                      │

[2차 연결: 0-RTT]

  Client                                                Server
    │                                                      │
    ├──── Initial: ClientHello + PSK extension ───────────>│
    │     + 0-RTT 패킷: HTTP 요청                          │
    │     (이전에 받은 PSK로 0-RTT 키 유도)                 │
    │                                                      │
    │<──── Initial: ServerHello + Finished ────────────────│
    │     + 1-RTT 패킷: HTTP 응답                          │
    │                                                      │
```

핵심은 1차 연결에서 서버가 `NewSessionTicket` 메시지로 PSK(Pre-Shared Key)를 발급한다는 점이다. 클라이언트는 이 PSK를 저장해두고, 다음 연결 시 PSK로부터 0-RTT 키를 유도해서 ClientHello와 함께 암호화된 애플리케이션 데이터를 즉시 보낸다.

서버는 PSK를 받으면 같은 키 유도 과정을 거쳐서 0-RTT 데이터를 복호화한다. 핸드셰이크가 완료되기 전에 데이터 처리를 시작할 수 있다.

### 재전송 공격 (Replay Attack) 문제

0-RTT 데이터는 PSK만 알면 누구나 만들 수 있다는 약점이 있다. 공격자가 0-RTT 패킷을 캡처해서 서버에 재전송하면, 서버는 같은 요청을 두 번 처리한다.

```
공격 시나리오:
  1. 사용자가 0-RTT로 "POST /transfer {amount: 1000}" 전송
  2. 공격자가 패킷을 캡처
  3. 5초 후, 공격자가 같은 패킷을 서버에 재전송
  4. 서버가 PSK 유효성만 확인하고 다시 처리
  5. 이체가 두 번 발생
```

이 때문에 0-RTT 데이터의 사용 범위에 제약이 걸려 있다.

```
0-RTT 사용 가능:
  - GET, HEAD 등 멱등(idempotent) 요청
  - 캐싱된 정적 자원 요청
  - 인증이 필요 없거나 토큰 기반 인증

0-RTT 사용 불가:
  - POST, PUT, DELETE 등 상태 변경 요청
  - 결제, 이체, 회원가입 등 비즈니스 트랜잭션
  - 세션 기반 인증의 첫 요청
```

서버 구현 측에서도 방어 장치를 둔다.

```
RFC 9001이 권장하는 방어:
  1. Anti-Replay Window
     → 최근 받은 0-RTT 패킷 번호를 일정 시간 기록
     → 같은 번호의 패킷이 재도착하면 거부

  2. 0-RTT 데이터 크기 제한
     → max_early_data_size 파라미터로 한도 지정
     → 보통 8KB~16KB 정도

  3. 세션 티켓 일회성
     → 한 번 쓴 PSK는 무효화 (서버 측 트래킹)
     → 분산 환경에서는 Redis 등으로 사용 이력 공유

  4. PSK 만료 시간
     → 보통 1~24시간으로 짧게 설정
     → 캡처된 패킷이 재사용 가능한 시간 제한
```

### Nginx에서 0-RTT 활성화

```nginx
server {
    listen 443 quic reuseport;
    listen 443 ssl;
    http2 on;

    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols       TLSv1.3;

    # 0-RTT 활성화 (early data)
    ssl_early_data on;
    ssl_session_tickets on;
    ssl_session_timeout 1h;

    # 0-RTT 요청은 Early-Data 헤더가 붙어서 백엔드로 전달됨
    proxy_set_header Early-Data $ssl_early_data;

    location / {
        proxy_pass http://backend;
    }
}
```

백엔드 애플리케이션은 `Early-Data: 1` 헤더가 오면 0-RTT로 받은 요청임을 인지하고, 멱등이 아닌 요청은 425(Too Early) 상태 코드로 응답해서 클라이언트가 1-RTT로 재시도하게 만든다.

```python
# FastAPI 예시
from fastapi import FastAPI, Request, Response

app = FastAPI()

@app.middleware("http")
async def block_unsafe_early_data(request: Request, call_next):
    if request.headers.get("Early-Data") == "1":
        if request.method not in ("GET", "HEAD"):
            return Response(status_code=425, content="Too Early")
    return await call_next(request)
```

### 0-RTT 적용 시 체감 효과

```
조건: RTT 100ms, 50KB 정적 자원 요청

1-RTT (HTTP/3 일반): 100ms (핸드셰이크) + 100ms (응답) = 200ms
0-RTT (HTTP/3 재연결):   0ms (핸드셰이크) + 100ms (응답) = 100ms

→ 약 50% 단축. RTT가 클수록 효과 커짐
```

---

## 연결 마이그레이션 (Connection Migration)

TCP는 4-튜플(소스 IP, 소스 포트, 목적지 IP, 목적지 포트)로 연결을 식별한다. 클라이언트의 IP나 포트가 바뀌면 연결이 끊어진다. 모바일에서 WiFi와 LTE를 오갈 때 새 연결을 맺어야 하고, 진행 중이던 다운로드는 끊긴다.

QUIC은 4-튜플이 아닌 Connection ID로 연결을 식별한다. 네트워크 경로가 바뀌어도 같은 Connection ID를 쓰면 연결이 유지된다.

### Connection ID 동작

```
[연결 수립]

  Client                                          Server
    │                                                │
    ├── DCID=ABC, SCID=123 ─────────────────────────>│
    │   (서버가 만들어줄 DCID를 잠시 사용)             │
    │                                                │
    │<── DCID=123, SCID=DEF ───────────────────────│
    │    (이제 클라이언트는 DEF를 DCID로 사용)         │
    │                                                │
    ├── DCID=DEF, ... ──────────────────────────────>│
    │                                                │
    │<── NEW_CONNECTION_ID: DEF2, DEF3, DEF4 ──────│
    │    (서버가 미리 여분 ID 발급)                    │
    │                                                │
```

서버는 핸드셰이크 후 `NEW_CONNECTION_ID` 프레임으로 여분의 Connection ID를 미리 발급한다. 클라이언트는 이 중에서 하나를 골라 쓰고, 마이그레이션 시 새 ID를 사용한다.

### Path Validation 절차

연결 마이그레이션이 단순히 "Connection ID만 같으면 되는" 게 아니다. 새 경로가 실제로 도달 가능한지, 그리고 그 IP가 공격자가 만든 가짜가 아닌지 검증해야 한다.

```
[마이그레이션 시 Path Validation]

WiFi 환경 (IP: 192.168.1.10)
  Client                                          Server
    │                                                │
    ├── 데이터 패킷 (DCID=DEF, 정상 통신) ────────────>│
    │                                                │

[LTE로 전환, IP: 172.16.5.20]

  Client                                          Server
    │                                                │
    ├── 데이터 패킷 (DCID=DEF2, 새 IP 172.16.5.20) ──>│
    │                                                │
    │                                                │ ← 서버: "다른 IP에서 왔다.
    │                                                │   진짜인지 확인하자"
    │                                                │
    │<── PATH_CHALLENGE (랜덤 8바이트) ──────────────│
    │                                                │
    ├── PATH_RESPONSE (받은 8바이트 그대로) ─────────>│
    │                                                │
    │                                                │ ← 서버: "응답 받음.
    │                                                │   새 경로 유효"
    │                                                │
    │<── 정상 통신 재개 (혼잡 제어는 재설정) ─────────│
    │                                                │
```

`PATH_CHALLENGE`/`PATH_RESPONSE` 프레임으로 서버가 새 경로의 도달성과 클라이언트의 신원을 확인한다. 이게 없으면 공격자가 위조된 소스 IP로 패킷을 보내서 트래픽을 다른 IP로 돌려 DoS 공격에 악용할 수 있다.

### 혼잡 제어 재설정

새 네트워크 경로의 대역폭, 지연, 손실률은 이전 경로와 다르다. WiFi에서 LTE로 옮기면 RTT가 늘고 손실률이 변할 수 있다. QUIC은 마이그레이션 후 혼잡 윈도우를 초기값으로 재설정하고 슬로우 스타트부터 다시 시작한다.

```
WiFi (RTT 5ms, BW 100Mbps) → LTE (RTT 80ms, BW 20Mbps)

마이그레이션 전: cwnd = 5MB (WiFi에 맞춰 성장)
마이그레이션 직후: cwnd = 10 * MTU ≈ 14KB (재시작)
이후 LTE 환경에 맞춰 재성장
```

처음에는 느려 보이지만 연결이 끊기는 것보다 훨씬 낫다. TCP는 같은 상황에서 연결 자체가 끊겨 처음부터 다시 시작해야 한다.

### NAT Rebinding

모바일에서 IP가 안 바뀌어도 NAT 장비가 포트 매핑을 변경하는 경우가 있다. UDP 세션은 보통 30~60초 무활동이면 만료된다.

```
NAT Rebinding 시나리오:
  1. 클라이언트가 30초간 무통신
  2. NAT 장비가 외부 포트를 재할당
  3. 클라이언트가 다음 패킷을 보내면 외부에서 보는 소스 포트가 바뀜
  4. 서버 입장에서는 "다른 4-튜플"로 보임
  5. Connection ID는 동일 → QUIC이 인지하고 Path Validation 수행
  6. 검증 후 연결 유지
```

TCP였다면 같은 상황에서 RST가 발생하거나 응답이 안 와서 타임아웃됐을 것이다. QUIC은 이걸 자동으로 처리한다.

### Preferred Address

서버가 클라이언트에게 "다음부터는 이 주소로 연결하라"고 안내할 수 있다. 핸드셰이크 시 전송 파라미터로 `preferred_address`를 보낸다.

```
사용 예시:
  - 글로벌 로드밸런서가 사용자를 가까운 리전으로 유도
  - 임시 IP에서 영구 IP로 마이그레이션
  - 로드 분산을 위해 다른 서버 인스턴스로 이동
```

이건 서버 주도 마이그레이션이다. 클라이언트가 새 주소로 Path Validation을 거친 후 통신을 전환한다.

### 마이그레이션이 안 되는 경우

```
disable_active_migration 파라미터:
  → 서버가 이 옵션을 보내면 클라이언트는 마이그레이션을 시도하지 않음
  → 5-튜플과 connection state를 강하게 묶는 미들박스가 있는 환경에서 사용

미들박스 문제:
  → 일부 NAT는 Connection ID를 모르고 4-튜플만 봐서 마이그레이션 패킷을 차단
  → 통신사 중간 게이트웨이가 새 5-튜플의 첫 패킷을 SYN처럼 다루려다 실패
  → 실제 마이그레이션 성공률은 환경에 따라 70~95% 수준
```

마이그레이션은 좋아 보이지만 모든 네트워크에서 매끄럽게 작동하지는 않는다. 실패 시 폴백 동작(재연결)도 함께 설계해야 한다.

### 모바일 클라이언트에서의 효과

```
실측 사례 (구글 발표 기준):
  YouTube 모바일 앱에서 QUIC 도입 후
  - 비디오 재생 중 네트워크 전환 시 끊김 빈도 30% 감소
  - 재버퍼링 발생율 9% 감소
  - 모바일 페이지 로딩 시간 8% 감소
```

웹사이트보다 모바일 앱에서 효과가 더 큰 이유가 여기 있다. 모바일은 네트워크 변화가 잦고, 사용자가 백그라운드에서 복귀할 때 NAT 매핑이 만료되어 있는 경우가 많다.

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
# OpenSSL 3.x 또는 BoringSSL로 빌드되어야 함

server {
    # HTTP/2 (TCP 443)
    listen 443 ssl;
    http2 on;

    # HTTP/3 (UDP 443) - reuseport로 워커 간 부하 분산
    listen 443 quic reuseport;

    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # QUIC은 TLS 1.3만 지원
    ssl_protocols TLSv1.3;
    ssl_prefer_server_ciphers off;

    # 0-RTT (Early Data) 활성화
    ssl_early_data on;

    # 세션 티켓 - 0-RTT용 PSK 발급
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1h;
    ssl_session_tickets on;

    # HTTP/3 지원 알림 헤더 (브라우저가 다음 요청부터 HTTP/3 사용)
    add_header Alt-Svc 'h3=":443"; ma=86400' always;

    # QUIC 관련 튜닝
    quic_retry on;                    # Retry 패킷으로 DDoS 방어
    quic_gso on;                      # Generic Segmentation Offload (커널 4.18+)
    quic_active_connection_id_limit 4; # 연결 마이그레이션용 여분 CID

    location / {
        proxy_pass http://backend;
        proxy_set_header Early-Data $ssl_early_data;
    }
}
```

Nginx 1.25.1부터 `http2` 지시자가 `listen` 파라미터에서 분리됐다. `listen 443 ssl http2;`가 아니라 `listen 443 ssl;` + `http2 on;`으로 쓴다.

### Nginx 빌드 시 주의

```bash
# Nginx 공식 패키지가 QUIC을 포함하는지 확인
nginx -V 2>&1 | grep -o 'with-http_v3_module'

# 없으면 직접 빌드
./configure \
    --with-http_v3_module \
    --with-stream_quic_module \
    --with-openssl=/path/to/openssl-3.x \
    ...
```

OpenSSL 3.x는 QUIC API를 부분적으로만 지원하기 때문에, 더 완전한 QUIC 지원이 필요하면 BoringSSL이나 quictls를 사용한다.

---

## Caddy에서 HTTP/3

Caddy는 기본적으로 HTTP/3가 활성화되어 있다. 별도 설정이 거의 필요 없다.

```caddyfile
example.com {
    reverse_proxy localhost:3000
}
```

이 한 줄로 끝난다. TLS 인증서 자동 발급, HTTP/3, 0-RTT가 모두 켜진다. 명시적으로 끄려면 다음과 같이 한다.

```caddyfile
example.com {
    servers {
        protocols h1 h2  # h3 제외
    }
    reverse_proxy localhost:3000
}
```

상세 설정이 필요한 경우.

```caddyfile
{
    servers :443 {
        protocols h1 h2 h3
        listener_wrappers {
            http_redirect
        }
    }
}

example.com {
    tls {
        protocols tls1.3
    }
    
    header Alt-Svc "h3=\":443\"; ma=86400"
    
    reverse_proxy localhost:3000 {
        header_up Early-Data {http.request.tls.early_data}
    }
}
```

Caddy는 운영 측면에서 가장 간단한 선택이지만, 트래픽이 큰 환경에서는 Nginx 대비 처리량이 낮을 수 있어 벤치마크 후 결정하는 게 좋다.

---

## OS 레벨 튜닝

QUIC은 UDP 위에서 동작하므로 TCP와 다른 커널 파라미터에 민감하다. 기본 설정 그대로면 패킷 손실이나 성능 저하가 발생한다.

### UDP 버퍼 크기

QUIC은 UDP 소켓의 수신/송신 버퍼를 적극적으로 활용한다. 기본값(보통 200KB)은 너무 작다.

```bash
# 현재 값 확인 (Linux)
sysctl net.core.rmem_max     # UDP 수신 버퍼 최대값
sysctl net.core.wmem_max     # UDP 송신 버퍼 최대값
sysctl net.core.rmem_default # 기본값
sysctl net.core.wmem_default # 기본값

# 권장 값으로 변경 (영구 적용은 /etc/sysctl.conf)
sudo sysctl -w net.core.rmem_max=7500000
sudo sysctl -w net.core.wmem_max=7500000
sudo sysctl -w net.core.rmem_default=2500000
sudo sysctl -w net.core.wmem_default=2500000

# UDP 메모리 압박 확인
cat /proc/net/snmp | grep -A1 "^Udp:"
# Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors ...
# RcvbufErrors가 증가하면 버퍼 부족 → 패킷 손실 발생 중
```

`RcvbufErrors`가 늘어나면 QUIC 연결이 패킷 손실로 인식하고 혼잡 제어가 작동해서 처리량이 떨어진다. 실제 네트워크에 손실이 없어도 서버 측 버퍼 부족으로 같은 효과가 난다.

### GSO/GRO 활용

```bash
# 네트워크 카드의 GSO/GRO 지원 확인
ethtool -k eth0 | grep -E "generic-(segmentation|receive)-offload"

# 활성화 (대부분 기본값으로 켜져 있음)
sudo ethtool -K eth0 gso on
sudo ethtool -K eth0 gro on
```

GSO(Generic Segmentation Offload)는 큰 UDP 패킷을 하드웨어/드라이버 레벨에서 분할한다. QUIC 서버는 한 번의 sendmmsg 호출로 여러 패킷을 보내는데, GSO가 있으면 CPU 부하가 크게 줄어든다. Nginx의 `quic_gso on` 옵션과 짝이다.

### 파일 디스크립터 한도

```bash
# 한 프로세스당 열 수 있는 FD 수 확인
ulimit -n

# systemd 서비스 파일에서 (Nginx 예시)
[Service]
LimitNOFILE=65535
LimitNPROC=65535
```

HTTP/2는 한 TCP 연결에 여러 요청을 다중화하지만, QUIC도 마찬가지로 한 UDP 소켓이 여러 연결을 처리하는 구조라 FD 자체는 적게 쓴다. 단, 워커별 reuseport 사용 시 워커 수만큼 FD가 필요하다.

### CPU 친화도

QUIC 처리는 유저스페이스에서 일어나기 때문에 CPU 의존도가 높다. SO_REUSEPORT로 여러 워커가 같은 포트를 듣게 하고, 워커별로 CPU를 고정한다.

```bash
# Nginx 워커 프로세스 수와 CPU 친화도 (nginx.conf)
worker_processes auto;
worker_cpu_affinity auto;
```

---

## CDN/로드밸런서 0-RTT 설정

### Cloudflare

대시보드에서 **Speed → Optimization → Protocol Optimization** 메뉴에 0-RTT 토글이 있다. 기본 활성화 상태다. 0-RTT 데이터를 받은 백엔드 요청에는 `cf-0rtt: 1` 헤더가 붙는다.

```bash
# 0-RTT가 들어왔는지 확인
curl --http3 -H "X-Test: 0rtt" https://your-domain.com -v 2>&1 | grep -i "cf-0rtt"
```

### AWS CloudFront

2024년부터 0-RTT 지원. **Edit distribution → Supported HTTP versions**에서 HTTP/3 활성화 시 0-RTT도 함께 켜진다. 별도 토글이 없다. 백엔드까지 0-RTT 헤더를 전파하려면 Custom Header 정책을 추가한다.

### 직접 운영 시 주의

```
다중 서버 환경에서 0-RTT가 동작하려면:
  1. 세션 티켓 키를 서버 간 공유 (Nginx: ssl_session_ticket_key)
  2. 또는 외부 세션 캐시 (Redis 등)
  3. 그러지 않으면 LB가 다른 서버로 라우팅한 경우 0-RTT 실패

세션 티켓 키 로테이션:
  → 키가 유출되면 과거 모든 0-RTT 데이터 복호화 가능 (Forward Secrecy 깨짐)
  → 매일 자동 로테이션 필수
  → Nginx는 ssl_session_ticket_key 디렉티브로 여러 키 파일 지정 가능
```

---

## Node.js에서 HTTP/3

Node.js의 HTTP/3 지원은 실험적이다. 실무에서는 Nginx/Caddy 등 웹서버에서 HTTP/3를 종료하고 백엔드와는 HTTP/1.1 또는 HTTP/2로 통신하는 구조가 일반적이다.

```
                 [HTTP/3 (UDP 443)]
   Browser ───────────────────────────> Nginx/Caddy
                                            │
                                            │ [HTTP/1.1 (TCP)]
                                            ▼
                                       Node.js (Express)
                                            │
                                            ▼
                                       Database
```

이 구조의 장점은 백엔드 코드를 건드릴 필요가 없다는 점이다. Nginx 설정만으로 HTTP/3 도입이 끝난다. 단점은 백엔드까지 HTTP/3의 이점(연결 마이그레이션 등)이 전달되지 않는다는 것인데, 보통 백엔드와 LB 사이는 안정적인 데이터센터 네트워크라 의미가 크지 않다.

---

## QUIC 혼잡 제어

QUIC은 전송 계층 프로토콜이므로 혼잡 제어 알고리즘을 자체적으로 구현한다. RFC 9002가 기본 알고리즘(NewReno 변형)을 제시하지만, 구현체마다 다른 알고리즘을 쓸 수 있다.

### TCP와 다른 점

```
TCP 혼잡 제어:
  - 커널의 단일 알고리즘 (Linux 기본 CUBIC, BBR 옵션)
  - 한 연결의 cwnd가 패킷 손실 시 절반으로 감소
  - 손실을 혼잡 신호로 해석

QUIC 혼잡 제어:
  - 유저스페이스 라이브러리에서 구현 → 알고리즘 교체 용이
  - 스트림별 흐름 제어 + 연결 레벨 혼잡 제어 분리
  - 패킷 번호 재사용 안 함 → 손실 감지 정확도 향상
  - ACK 프레임에 ACK 지연(ACK Delay) 명시 → RTT 측정 정확
```

### 손실 감지 정확도

TCP는 같은 시퀀스 번호를 재전송에도 쓰기 때문에 ACK를 받아도 그게 원본인지 재전송본인지 알 수 없다(애매한 ACK 문제). QUIC은 패킷 번호를 절대 재사용하지 않는다. 재전송할 때 새 패킷 번호를 부여한다.

```
TCP:
  원본 패킷: seq=1000 (loss)
  재전송:    seq=1000 (같은 번호)
  ACK 받음:  ack=1001
  → 어느 쪽 ACK인지 모름 → RTT 측정 부정확

QUIC:
  원본 패킷: PN=42 (loss)
  재전송:    PN=58 (같은 데이터, 새 번호)
  ACK 받음:  PN=58
  → 재전송본이 도달한 것으로 정확히 식별
  → RTT 측정과 손실 감지가 모두 정확해짐
```

### 알고리즘 선택

```
Cloudflare quiche: CUBIC 기본, BBR2 옵션
Google QUICHE:     BBR/BBRv2 기본
Microsoft msquic:  CUBIC 기본
ngtcp2:            NewReno 기본, CUBIC/BBR 옵션
```

BBR은 대역폭이 큰 경로에서 CUBIC보다 처리량이 높고, 모바일/위성 등 변동성 큰 환경에서 안정적이다. 다만 BBR이 CUBIC 트래픽과 공정성을 해친다는 보고가 있어, 일반 인터넷 트래픽에는 BBRv2가 권장된다.

---

## 모니터링과 메트릭

HTTP/3 도입 후 무엇을 모니터링해야 하는지가 실무의 핵심이다.

### 서버 측 메트릭

```
필수 메트릭:
  - HTTP/3 vs HTTP/2 연결 비율
  - 0-RTT 시도 수 / 0-RTT 거부 수
  - 패킷 손실률 (서버 관점)
  - Connection Migration 발생 수 / 성공률
  - UDP 버퍼 오버플로 (RcvbufErrors)
  - 평균 RTT (QUIC 자체 측정값)

부가 메트릭:
  - 핸드셰이크 실패율
  - 0-RTT Replay 방어 트리거 수
  - QPACK 인코딩 효율 (압축률)
```

### Prometheus 메트릭 예시 (Nginx)

```nginx
# Nginx Plus 또는 nginx-module-vts 사용
http {
    vhost_traffic_status_zone;
    
    server {
        listen 8080;
        location /status {
            vhost_traffic_status_display;
            vhost_traffic_status_display_format prometheus;
        }
    }
}
```

```
# 주요 메트릭
nginx_http_requests_total{protocol="HTTP/3.0"}
nginx_http_request_duration_seconds{protocol="HTTP/3.0"}
nginx_quic_connections_active
nginx_quic_handshakes_completed_total
```

### 클라이언트 측 측정

Chrome/Firefox는 개발자 도구에서 HTTP/3 사용 여부를 표시한다.

```
Chrome DevTools → Network → 응답 헤더 → Protocol 컬럼
  h3 → HTTP/3로 응답
  h2 → HTTP/2로 응답 (HTTP/3 시도 실패 또는 미지원)
```

실제 사용자 환경에서 측정하려면 Web Performance API를 활용한다.

```javascript
// 페이지 로드 시 사용된 프로토콜 측정
const entries = performance.getEntriesByType('navigation');
entries.forEach(entry => {
  console.log({
    url: entry.name,
    protocol: entry.nextHopProtocol,  // "h3", "h2", "http/1.1"
    connectTime: entry.connectEnd - entry.connectStart,
    tlsTime: entry.secureConnectionStart > 0 
      ? entry.connectEnd - entry.secureConnectionStart 
      : 0,
    ttfb: entry.responseStart - entry.requestStart
  });
});

// Real User Monitoring(RUM)으로 수집해서 분석
// → 실제 사용자 환경에서 HTTP/2 vs HTTP/3 성능 비교 가능
```

### qlog 기반 상세 분석

qlog은 RFC 9114와 함께 정의된 QUIC 전용 로깅 표준이다. JSON-Lines 형식으로 모든 패킷, ACK, 손실, 혼잡 제어 이벤트가 기록된다.

```bash
# Nginx에서 qlog 활성화
# nginx-quic 빌드 옵션이 필요하며, 보통 디버깅용으로만 사용
quic_log /var/log/nginx/quic.qlog;

# qvis에 업로드해서 시각화
# https://qvis.quictools.info/
```

qlog은 데이터 양이 매우 많아서 프로덕션 상시 활성화는 어렵다. 특정 연결만 샘플링하거나 문제 재현 시에만 켠다.

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
