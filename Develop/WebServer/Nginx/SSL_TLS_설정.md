---
title: Nginx SSL/TLS 설정
tags: [webserver, nginx, ssl, tls, https, certbot, letsencrypt, hsts, ocsp]
updated: 2026-03-08
---

# Nginx SSL/TLS 설정

## 개요

SSL/TLS는 클라이언트와 서버 사이 통신을 암호화하여 도청·위변조를 방지한다. 현재 표준은 **TLS 1.2 / TLS 1.3**이며, 구버전(TLS 1.0/1.1, SSL)은 취약점이 있으므로 비활성화해야 한다.

```
HTTP  → 평문 전송, 중간자 공격 가능
HTTPS → TLS 암호화, 인증서로 서버 신원 검증
```

---

## 인증서 발급

### Let's Encrypt (무료, 권장)

```bash
# Certbot 설치 (Ubuntu)
sudo apt update
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (Nginx 자동 설정 포함)
sudo certbot --nginx -d example.com -d www.example.com

# 발급된 파일 위치
# /etc/letsencrypt/live/example.com/fullchain.pem  — 인증서 체인
# /etc/letsencrypt/live/example.com/privkey.pem    — 개인 키

# 자동 갱신 확인 (90일마다 갱신 필요)
sudo certbot renew --dry-run

# 시스템 타이머로 자동 갱신 (Ubuntu에서는 certbot 설치 시 자동 등록)
systemctl status certbot.timer
```

### 자체 서명 인증서 (개발/내부용)

```bash
# 개발 환경에서 사용. 브라우저 경고가 뜨므로 프로덕션엔 사용 금지
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/self-signed.key \
    -out /etc/ssl/certs/self-signed.crt \
    -subj "/CN=localhost"
```

---

## 기본 HTTPS 설정

```nginx
# HTTP → HTTPS 리다이렉트 (반드시 분리)
server {
    listen 80;
    server_name example.com www.example.com;

    # 301: 영구 리다이렉트 (SEO 유리)
    return 301 https://example.com$request_uri;
}

# HTTPS 메인 서버
server {
    listen 443 ssl http2;
    server_name example.com;

    # 인증서
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 버전 — 1.2, 1.3만 허용
    ssl_protocols TLSv1.2 TLSv1.3;

    # 암호화 스위트 (Mozilla Intermediate 권장)
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;  # TLS 1.3에서는 클라이언트 우선

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 성능 최적화 설정

### 세션 캐시 + OCSP Stapling

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # TLS 세션 캐시 — 재협상 비용 절감
    ssl_session_cache   shared:SSL:10m;  # 10MB = 약 40,000 세션
    ssl_session_timeout 1d;
    ssl_session_tickets off;             # 보안상 비활성화 권장

    # OCSP Stapling — 인증서 유효성 검증을 서버가 미리 처리
    # 클라이언트가 인증 기관에 직접 요청하지 않아도 됨 → 지연 감소
    ssl_stapling        on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # DH 파라미터 (DHE 암호 스위트 사용 시)
    # openssl dhparam -out /etc/nginx/dhparam.pem 2048
    ssl_dhparam /etc/nginx/dhparam.pem;
}
```

---

## 보안 헤더

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # HSTS — 브라우저가 항상 HTTPS로 접속하도록 강제
    # max-age=31536000: 1년간 유지
    # includeSubDomains: 서브도메인 포함
    # preload: 브라우저 내장 목록 등록 신청 가능
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # 클릭재킹 방지
    add_header X-Frame-Options "SAMEORIGIN" always;

    # MIME 타입 스니핑 방지
    add_header X-Content-Type-Options "nosniff" always;

    # XSS 필터 (구형 브라우저용)
    add_header X-XSS-Protection "1; mode=block" always;

    # Referrer 정책
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 권한 정책
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # CSP (Content Security Policy) — 상황에 맞게 조정 필요
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'" always;
}
```

---

## 인증서 유형 비교

| 항목 | DV (Domain Validation) | OV (Organization Validation) | EV (Extended Validation) |
|------|----------------------|----------------------------|------------------------|
| **발급 속도** | 즉시~수 분 | 수 일 | 수 주 |
| **검증 범위** | 도메인 소유권만 | 조직 실재 확인 | 법인 정보 심층 확인 |
| **비용** | 무료 (Let's Encrypt) | 유료 | 고비용 |
| **주소창 표시** | 자물쇠 아이콘 | 자물쇠 아이콘 | (이전: 녹색 바, 현재 표준과 동일) |
| **권장 용도** | 개인/스타트업 | 기업 서비스 | 금융/전자상거래 |

---

## 멀티 도메인 / 와일드카드

```nginx
# 멀티 도메인 (SAN 인증서)
server {
    listen 443 ssl http2;
    server_name example.com www.example.com api.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
}

# 와일드카드 인증서 발급 (DNS 인증 방식 필요)
# sudo certbot certonly --manual --preferred-challenges dns \
#     -d example.com -d "*.example.com"
```

```nginx
# 서브도메인별 별도 서버 블록
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://api-backend:8080;
    }
}

server {
    listen 443 ssl http2;
    server_name admin.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # 내부 IP만 접근 허용
    allow 10.0.0.0/8;
    deny all;

    location / {
        proxy_pass http://admin-backend:9000;
    }
}
```

---

## TLS 버전별 특징

| 버전 | 상태 | 핸드셰이크 | 특징 |
|------|------|-----------|------|
| SSL 3.0 | ❌ 사용 금지 | 2-RTT | POODLE 취약점 |
| TLS 1.0 | ❌ 사용 금지 | 2-RTT | BEAST 취약점, PCI DSS 비적합 |
| TLS 1.1 | ❌ 사용 금지 | 2-RTT | 2021년 브라우저 지원 종료 |
| TLS 1.2 | ✅ 사용 가능 | 2-RTT | 현재 주류, 광범위 호환 |
| TLS 1.3 | ✅ 권장 | 1-RTT | 속도 개선, 구형 암호 제거 |

---

## SSL 설정 검증

```bash
# Nginx 설정 문법 검사
sudo nginx -t

# SSL 연결 테스트
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3

# 인증서 만료일 확인
echo | openssl s_client -connect example.com:443 2>/dev/null \
    | openssl x509 -noout -dates

# 온라인 검증 도구
# https://www.ssllabs.com/ssltest/  — A+ 등급 목표
# https://securityheaders.com/      — 보안 헤더 검사
```

---

## 스니펫으로 재사용

```nginx
# /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 valid=300s;

add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

```nginx
# /etc/nginx/snippets/letsencrypt.conf
ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
```

```nginx
# 서버 블록에서 include로 재사용
server {
    listen 443 ssl http2;
    server_name example.com;

    include snippets/letsencrypt.conf;
    include snippets/ssl-params.conf;

    location / {
        proxy_pass http://backend;
    }
}
```
