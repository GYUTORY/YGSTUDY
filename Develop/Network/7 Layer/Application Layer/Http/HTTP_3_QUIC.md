---
title: HTTP/3와 QUIC
tags: [network, 7-layer, application-layer, http3, quic, udp, tls, performance]
updated: 2026-03-08
---

# HTTP/3와 QUIC

## 개요

HTTP/3는 TCP 위에서 동작하던 이전 HTTP 버전과 달리 **QUIC** 위에서 동작하는 차세대 프로토콜이다. QUIC은 구글이 개발하고 IETF가 표준화한 UDP 기반 전송 프로토콜로, TCP의 구조적 한계를 해결한다.

```
HTTP/1.1 → TCP + TLS 1.2/1.3       → 텍스트 기반, HOL 블로킹
HTTP/2   → TCP + TLS 1.2/1.3       → 바이너리, 멀티플렉싱 (TCP HOL 블로킹 잔존)
HTTP/3   → QUIC (UDP 기반) + TLS 1.3 → HOL 블로킹 완전 제거, 0-RTT 연결
```

---

## TCP의 한계와 QUIC의 등장

### Head-of-Line (HOL) 블로킹

```
HTTP/2의 멀티플렉싱 (TCP):
  Stream 1: [패킷 A] [패킷 B] ❌ 손실 [패킷 D]
  Stream 2: [패킷 E] [패킷 F]
  Stream 3: [패킷 G]

  → 패킷 C가 손실되면 TCP는 재전송될 때까지
    Stream 1뿐 아니라 Stream 2, 3도 모두 대기!
    (OS 커널 레벨에서 순서 보장하기 때문)

HTTP/3 (QUIC):
  Stream 1: [패킷 A] [패킷 B] ❌ 손실 → Stream 1만 대기
  Stream 2: [패킷 E] [패킷 F]     → 계속 진행 ✅
  Stream 3: [패킷 G]               → 계속 진행 ✅
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

## Nginx에서 HTTP/3 활성화

```nginx
# Nginx 1.25+ 또는 quiche 패치 버전 필요
server {
    # HTTP/2 (TCP 443)
    listen 443 ssl http2;

    # HTTP/3 (UDP 443)
    listen 443 quic reuseport;

    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # QUIC 활성화
    ssl_protocols TLSv1.3;   # QUIC은 TLS 1.3만 지원

    # HTTP/3 지원 알림 헤더 (브라우저가 다음 요청부터 HTTP/3 사용)
    add_header Alt-Svc 'h3=":443"; ma=86400';
    add_header QUIC-Status $quic;

    location / {
        proxy_pass http://backend;
    }
}
```

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

## 브라우저 지원 현황 (2026 기준)

| 브라우저 | HTTP/3 지원 |
|--------|------------|
| Chrome | ✅ 87+ |
| Firefox | ✅ 88+ |
| Safari | ✅ 14+ |
| Edge | ✅ 87+ |

전 세계 HTTP/3 트래픽 비율: 약 30% (2024 기준, 지속 증가 중)

---

## 언제 HTTP/3가 유리한가

```
HTTP/3가 효과적인 환경:
  ✅ 모바일 네트워크 (WiFi ↔ LTE 전환 잦음)
  ✅ 패킷 손실률이 높은 환경 (무선, 약한 신호)
  ✅ 지연이 높은 원거리 연결 (글로벌 서비스)
  ✅ 다수의 소규모 리소스 요청 (SPA, 마이크로프론트엔드)

HTTP/2로 충분한 환경:
  ✅ 안정적인 유선 네트워크 (데이터센터 내부)
  ✅ 내부 서비스 간 통신 (gRPC 등)
  ✅ 대용량 단일 파일 전송
```
