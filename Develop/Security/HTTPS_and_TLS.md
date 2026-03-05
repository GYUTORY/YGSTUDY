---
title: HTTPS & TLS 핵심 개념 가이드
tags: [security, https, tls, ssl, certificate, encryption, handshake]
updated: 2026-03-01
---

# HTTPS & TLS

## 개요

**HTTPS**(HTTP over TLS)는 HTTP 통신을 **TLS(Transport Layer Security)** 프로토콜로 암호화한 것이다. 데이터 도청, 변조, 위장을 방지한다. 현대 웹에서 HTTPS는 선택이 아닌 **필수**이다.

### HTTP vs HTTPS

```
HTTP:
  Client ──── "password=1234" ────▶ Server
              (평문, 도청 가능)

HTTPS:
  Client ──── "x7Fk9#@!mZ..." ────▶ Server
              (암호화, 도청 불가)
```

| 항목 | HTTP | HTTPS |
|------|------|-------|
| **포트** | 80 | 443 |
| **암호화** | 없음 | TLS 암호화 |
| **인증** | 없음 | 인증서로 서버 신원 확인 |
| **무결성** | 없음 | 변조 감지 |
| **SEO** | 불이익 | 검색 순위 가산점 |
| **브라우저** | "주의 요함" 경고 | 자물쇠 아이콘 |

### TLS가 제공하는 3가지 보안

| 보안 | 설명 | 위협 방지 |
|------|------|----------|
| **기밀성** | 데이터를 암호화하여 제3자가 읽을 수 없음 | 도청 (Eavesdropping) |
| **무결성** | 데이터가 전송 중 변조되지 않았음을 보장 | 변조 (Tampering) |
| **인증** | 서버가 진짜임을 인증서로 증명 | 위장 (Impersonation) |

## 핵심

### 1. TLS 핸드셰이크

클라이언트와 서버가 암호화 통신을 시작하기 전 **키를 교환하는 과정**이다.

#### TLS 1.3 핸드셰이크 (현재 표준)

```
Client                                          Server
  │                                                │
  │──── ClientHello ──────────────────────────────▶│
  │     (지원 암호 스위트, 키 공유)                    │
  │                                                │
  │◀──── ServerHello + 인증서 + Finished ───────────│
  │     (선택된 암호 스위트, 서버 키, 인증서)           │
  │                                                │
  │──── Finished ─────────────────────────────────▶│
  │                                                │
  │◀═══════════ 암호화된 통신 시작 ═══════════════▶│
```

**TLS 1.3은 1-RTT** (왕복 1회)로 완료. TLS 1.2는 2-RTT 필요.

#### 단계별 설명

| 단계 | 동작 | 목적 |
|------|------|------|
| **ClientHello** | 클라이언트가 지원하는 암호 스위트/키 공유 전송 | 협상 시작 |
| **ServerHello** | 서버가 암호 스위트 선택, 인증서 전송 | 서버 인증 |
| **인증서 검증** | 클라이언트가 CA 체인으로 인증서 검증 | 신뢰 확인 |
| **키 교환** | ECDHE로 공유 비밀 생성 | 대칭키 생성 |
| **Finished** | 양쪽 핸드셰이크 검증 | 무결성 확인 |

### 2. 인증서 (Certificate)

#### 인증서 체인

```
Root CA (최상위 인증기관)
  │  ← 브라우저/OS에 미리 저장됨 (신뢰 앵커)
  ▼
Intermediate CA (중간 인증기관)
  │  ← Root CA가 서명
  ▼
서버 인증서 (End-Entity)
  │  ← Intermediate CA가 서명
  ▼
example.com  ← 이 서버가 진짜 example.com임을 증명
```

| 인증서 유형 | 검증 수준 | 비용 | 용도 |
|-----------|----------|------|------|
| **DV (Domain Validated)** | 도메인 소유 확인 | 무료~저가 | 일반 웹사이트 |
| **OV (Organization Validated)** | 조직 실체 확인 | 중간 | 기업 웹사이트 |
| **EV (Extended Validation)** | 엄격한 신원 확인 | 고가 | 금융, 전자상거래 |

📌 **실무**: Let's Encrypt(무료 DV)가 대부분의 상황에서 충분하다.

#### Let's Encrypt로 인증서 발급

```bash
# Certbot 설치 (Ubuntu)
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (Nginx 자동 설정)
sudo certbot --nginx -d example.com -d www.example.com

# 자동 갱신 확인 (90일마다)
sudo certbot renew --dry-run

# 크론탭 자동 갱신
echo "0 0 1 * * certbot renew --quiet" | sudo tee -a /etc/crontab
```

### 3. TLS 버전 비교

| 항목 | TLS 1.2 | TLS 1.3 |
|------|---------|---------|
| **핸드셰이크** | 2-RTT | 1-RTT (빠름) |
| **0-RTT 재연결** | 미지원 | 지원 (재방문 시 즉시 연결) |
| **암호 스위트** | 다수 (일부 취약) | AEAD만 (안전한 것만) |
| **키 교환** | RSA 또는 ECDHE | ECDHE만 (전방 비밀성 보장) |
| **상태** | 점진적 폐지 | **현재 표준** |

📌 **설정 권장**: `ssl_protocols TLSv1.2 TLSv1.3;` — TLS 1.2 이상만 허용. TLS 1.0/1.1은 반드시 비활성화.

### 4. 암호 스위트 (Cipher Suite)

TLS 통신에 사용할 알고리즘 조합이다.

```
TLS_AES_256_GCM_SHA384
 │    │       │    │
 │    │       │    └── 무결성 확인 (해시)
 │    │       └─────── 인증된 암호화 모드
 │    └─────────────── 대칭키 암호화 알고리즘
 └──────────────────── TLS 프로토콜
```

**TLS 1.3 지원 암호 스위트 (3개만):**
- `TLS_AES_256_GCM_SHA384` — 가장 강력
- `TLS_AES_128_GCM_SHA256` — 성능/보안 균형
- `TLS_CHACHA20_POLY1305_SHA256` — 모바일 최적화

### 5. 전방 비밀성 (Forward Secrecy)

서버의 개인키가 유출되더라도 **과거 통신 내용을 복호화할 수 없는** 성질이다.

```
RSA 키 교환 (전방 비밀성 없음):
  개인키 유출 → 과거 모든 통신 복호화 가능 ❌

ECDHE 키 교환 (전방 비밀성 있음):
  개인키 유출 → 과거 통신 복호화 불가 ✅
  (매 세션마다 임시 키를 생성하므로)
```

📌 TLS 1.3은 ECDHE만 사용하므로 **자동으로 전방 비밀성이 보장**된다.

### 6. HSTS (HTTP Strict Transport Security)

브라우저에게 **항상 HTTPS를 사용하라**고 지시하는 보안 헤더이다.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

| 파라미터 | 의미 |
|---------|------|
| `max-age=31536000` | 1년간 HTTPS만 사용 |
| `includeSubDomains` | 서브도메인도 적용 |
| `preload` | 브라우저 사전 로드 목록에 등록 |

```
HSTS 없이:
  사용자 → http://example.com → 301 리다이렉트 → https://example.com
  (첫 요청이 HTTP로 가서 중간자 공격 가능)

HSTS 있으면:
  사용자 → 브라우저가 자동으로 https://example.com 접속
  (HTTP 요청 자체가 발생하지 않음)
```

## 예시

### Nginx HTTPS 보안 설정 (프로덕션)

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # 인증서
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 버전
    ssl_protocols TLSv1.2 TLSv1.3;

    # 암호 스위트
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling (인증서 상태 확인 가속)
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;

    # 세션 캐시 (핸드셰이크 재사용)
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
}
```

### Spring Boot HTTPS 설정

```yaml
# application.yml
server:
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-type: PKCS12
    key-store-password: ${SSL_PASSWORD}
    key-alias: myapp
  port: 8443
```

📌 **실무에서는** Spring Boot에 직접 SSL을 설정하기보다 **Nginx에서 SSL을 처리**(SSL Termination)하고, Spring Boot는 HTTP로 통신하는 것이 일반적이다.

### SSL 점검 도구

```bash
# 인증서 정보 확인
openssl s_client -connect example.com:443 -servername example.com

# 인증서 만료일 확인
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# SSL Labs 점수 확인 (웹)
# https://www.ssllabs.com/ssltest/
```

## 운영 팁

### HTTPS 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| TLS 1.2+ 만 허용 | TLS 1.0/1.1 비활성화 | ✅ |
| HSTS 헤더 설정 | HTTP → HTTPS 강제 | ✅ |
| 인증서 자동 갱신 | Let's Encrypt 크론탭 | ✅ |
| HTTP → HTTPS 리다이렉트 | 301 리다이렉트 | ✅ |
| SSL Labs A+ 등급 | 보안 설정 검증 | ⭐ |
| OCSP Stapling | 인증서 검증 가속 | ⭐ |
| CAA 레코드 | 인증서 발급 제한 DNS | 선택 |

### 흔한 실수

| 실수 | 결과 | 해결 |
|------|------|------|
| Mixed Content | HTTPS 페이지에서 HTTP 리소스 로드 → 경고 | 모든 리소스를 HTTPS로 |
| 인증서 만료 | 사이트 접근 불가 | 자동 갱신 크론 설정 |
| 자체 서명 인증서 | 브라우저 경고 | Let's Encrypt 사용 |
| TLS 1.0 허용 | 보안 취약 | `ssl_protocols TLSv1.2 TLSv1.3;` |

## 참고

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/) — Nginx/Apache SSL 설정 자동 생성
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/) — SSL 보안 점검
- [Let's Encrypt](https://letsencrypt.org/)
- [AES 암호화](AES.md) — TLS에서 사용하는 대칭키 암호화
- [RSA 암호화](RSA.md) — 인증서 서명에 사용
- [Nginx 리버스 프록시](../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — SSL Termination 설정
