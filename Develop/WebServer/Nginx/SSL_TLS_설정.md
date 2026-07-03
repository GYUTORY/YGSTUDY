---
title: Nginx SSL/TLS 설정
tags: [webserver, nginx, ssl, tls, https, certbot, letsencrypt, hsts, ocsp, mtls, http3, quic]
updated: 2026-05-03
---

# Nginx SSL/TLS 설정

## 개요

SSL/TLS는 클라이언트와 서버 사이 통신을 암호화해 도청·위변조를 막는다. 현재 표준은 TLS 1.2 / TLS 1.3이고, 구버전(TLS 1.0/1.1, SSL)은 취약점이 있어 비활성화한다. 운영 단계에서 자주 부딪히는 문제는 단순 발급보다 갱신 누락, 체인 누락, 만료 모니터링 부재, 그리고 reload를 빠뜨려 옛 인증서를 그대로 서빙하는 경우다.

```
HTTP  → 평문 전송, 중간자 공격 가능
HTTPS → TLS 암호화, 인증서로 서버 신원 검증
```

---

## 인증서 발급

### Let's Encrypt (무료, 가장 일반적)

```bash
# Certbot 설치 (Ubuntu)
sudo apt update
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (Nginx 자동 설정 포함)
sudo certbot --nginx -d example.com -d www.example.com

# 발급된 파일 위치
# /etc/letsencrypt/live/example.com/fullchain.pem  — 인증서 + 중간 체인
# /etc/letsencrypt/live/example.com/privkey.pem    — 개인 키
# /etc/letsencrypt/live/example.com/chain.pem      — 중간 체인만 (OCSP 검증용)

# 90일 유효, 자동 갱신은 systemd timer가 처리
systemctl status certbot.timer

# 수동 갱신 테스트 (실제 갱신은 안 함)
sudo certbot renew --dry-run
```

Let's Encrypt rate limit은 도메인 당 주당 50개 인증서다. CI/CD에서 매번 새로 발급받는 식으로 짜면 1주 만에 한도에 걸린다. 같은 cert는 재발급(`--force-renewal`) 대신 재사용한다. 테스트는 staging 환경(`--staging`)으로 검증한 뒤 프로덕션에 배포한다.

### 자체 서명 인증서 (개발/내부용)

```bash
# 개발 환경 전용. 브라우저 경고가 뜨므로 외부 노출 서비스에는 쓰지 않는다
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/self-signed.key \
    -out /etc/ssl/certs/self-signed.crt \
    -subj "/CN=localhost"
```

내부 마이크로서비스 mTLS 용도로는 자체 CA를 만들어 운영하는 게 일반적이다. mkcert나 cfssl로 사설 CA를 굴리고, 클라이언트·서버 인증서를 그 CA로 서명한다.

---

## 기본 HTTPS 설정

```nginx
# HTTP → HTTPS 리다이렉트 (반드시 분리된 서버 블록으로)
server {
    listen 80;
    server_name example.com www.example.com;

    # 301: 영구 리다이렉트 (SEO 점수 보존)
    return 301 https://example.com$request_uri;
}

# HTTPS 메인 서버
server {
    listen 443 ssl;
    http2 on;  # nginx 1.25.1+ 권장 문법
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 버전 — 1.2, 1.3만 허용
    ssl_protocols TLSv1.2 TLSv1.3;

    # Mozilla Intermediate 권장 스위트
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;  # TLS 1.3은 클라이언트 우선이 표준

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`http2` 지시어는 nginx 1.25.1부터 `listen 443 ssl http2;` 대신 별도 라인으로 쓰는 게 권장 문법이다. 옛 문법도 동작하지만 deprecation 경고가 뜬다.

---

## ECDSA vs RSA — 어떤 인증서를 쓸 것인가

ECDSA(P-256)는 RSA-2048 대비 키와 서명이 작아 핸드셰이크가 빠르고 CPU 사용량도 절반 수준이다. 모바일 환경처럼 RTT 비용이 큰 곳에서는 차이가 체감된다. 다만 매우 오래된 클라이언트(Windows XP, Android 4.x 이하 일부)는 ECDSA를 지원하지 않는다.

실무에서는 dual-cert로 두 종류를 동시에 서빙하는 방식이 안전하다. nginx는 `ssl_certificate`를 두 번 지정하면 클라이언트의 `signature_algorithms` extension을 보고 자동으로 골라 응답한다.

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;

    # ECDSA 인증서 (현대 브라우저 기본)
    ssl_certificate     /etc/letsencrypt/live/example.com-ecc/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com-ecc/privkey.pem;

    # RSA 인증서 (구형 클라이언트 fallback)
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
}
```

Certbot에서 ECDSA 인증서를 발급받으려면 `--key-type ecdsa --elliptic-curve secp256r1` 옵션을 추가한다. 별도 디렉토리(`example.com-ecc`)로 분리해서 관리하는 게 갱신 시 헷갈리지 않는다.

서비스 트래픽이 모두 IE11/구형 안드로이드를 거의 안 쓰는 자체 앱이라면 ECDSA 단일로도 충분하다. 공개 웹사이트면 dual-cert를 권장한다.

---

## 성능 최적화

### 세션 캐시 + OCSP Stapling

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # TLS 세션 캐시 — 재협상 비용 절감
    ssl_session_cache   shared:SSL:10m;  # 10MB ≈ 약 40,000 세션
    ssl_session_timeout 1d;

    # 세션 티켓은 비활성화 (이유는 아래 별도 절 참고)
    ssl_session_tickets off;

    # OCSP Stapling — 서버가 미리 인증서 유효성 응답을 가져와 첨부
    # 클라이언트가 CA에 직접 묻는 RTT가 사라진다
    ssl_stapling        on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
}
```

### ssl_session_tickets를 끄는 이유

`ssl_session_tickets on`이면 nginx는 메모리 안에 세션 티켓 암호화 키를 들고 있고, 이 키로 클라이언트 세션 정보를 암호화해 티켓으로 발급한다. 문제는 nginx 기본 동작이 이 키를 자동으로 회전하지 않는다는 점이다. 프로세스가 며칠~몇 주씩 떠 있으면 같은 키가 계속 쓰인다. 그 키가 메모리 덤프 등으로 유출되면 과거 모든 세션이 복호화될 수 있다 — Forward Secrecy가 깨진다.

`ssl_session_ticket_key`로 키 파일을 명시하고 cron으로 매일 회전하는 운영도 가능하지만, 멀티 노드 환경에서 키 동기화까지 신경써야 한다. 작은 서비스라면 그냥 `off`로 두고 세션 캐시만 쓰는 쪽이 단순하고 안전하다.

---

## HTTP/3 (QUIC) 활성화

HTTP/3은 UDP 위에서 동작하는 QUIC 프로토콜을 사용한다. TCP의 head-of-line blocking 문제가 없어 모바일이나 패킷 손실이 잦은 네트워크에서 체감 속도가 좋다. nginx는 1.25.0부터 정식 지원한다.

```nginx
server {
    # 기존 TCP 443 (HTTP/2)
    listen 443 ssl;
    http2 on;

    # QUIC/HTTP/3 — UDP 443
    listen 443 quic reuseport;

    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.3;  # HTTP/3은 TLS 1.3 전용

    # 클라이언트에게 "이 서비스는 HTTP/3도 가능" 광고
    add_header Alt-Svc 'h3=":443"; ma=86400' always;
}
```

`reuseport`는 워커 프로세스마다 별도 UDP 소켓을 만들어 분산 처리한다. 한 워커에 트래픽이 쏠리는 걸 막는다.

운영에서 빼먹기 쉬운 부분이 방화벽이다. HTTP/3은 UDP 443을 쓰므로 보안 그룹·iptables·CDN 앞단까지 UDP 443을 열어줘야 한다. 회사 내부 망이나 일부 통신사에서 UDP를 차단하면 클라이언트는 자동으로 TCP로 fallback하는데, 그 fallback이 의외로 비싸서 첫 요청이 느려진다.

CDN(Cloudflare, Fastly 등) 뒤에 nginx를 두면 CDN 단에서 HTTP/3을 종료하고 origin과는 HTTP/2로 통신하는 게 일반적이다. origin 서버 자체에 HTTP/3을 켜는 건 직접 노출되는 경우만 의미 있다.

---

## 0-RTT (TLS 1.3 Early Data)

TLS 1.3의 0-RTT는 재방문 클라이언트가 핸드셰이크 완료 전에 데이터를 미리 보내는 기능이다. 첫 요청 RTT가 사라지므로 모바일에서 체감 효과가 크다.

```nginx
server {
    listen 443 ssl;
    http2 on;
    listen 443 quic reuseport;

    ssl_protocols TLSv1.3;
    ssl_early_data on;

    # early data로 들어온 요청을 백엔드에 알려주는 헤더
    proxy_set_header Early-Data $ssl_early_data;
}
```

문제는 replay 공격이다. 0-RTT 데이터는 재전송돼도 서버가 거부할 방법이 없다. 공격자가 캡처한 요청을 다시 보내면 같은 처리가 두 번 일어난다. GET 같은 멱등 요청이면 큰 문제가 아니지만, POST로 결제·주문이 들어오면 두 번 청구될 수 있다.

운영 권장 패턴은 두 가지다.
- 백엔드에서 `Early-Data: 1`이 붙은 요청은 GET만 허용하고, POST/PUT/DELETE는 425 Too Early로 응답해 클라이언트가 핸드셰이크 완료 후 재시도하게 만든다.
- 또는 nginx 단에서 위치별로 분기:

```nginx
location /api/ {
    if ($ssl_early_data) {
        return 425;
    }
    proxy_pass http://backend;
}
```

`if`는 nginx에서 일반적으로 권장되지 않지만 early data 차단 용도로는 공식 문서에서도 등장한다.

성능 이득이 크지 않거나 멱등성 보장이 어려운 서비스라면 그냥 끄는 것도 합리적이다.

---

## mTLS — 클라이언트 인증서 검증

내부 API, 파트너사 연동, IoT 디바이스 통신에서 비밀번호 대신 클라이언트 인증서로 신원을 검증하는 패턴이다.

```nginx
server {
    listen 443 ssl;
    server_name api-internal.example.com;

    ssl_certificate     /etc/letsencrypt/live/api-internal.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api-internal.example.com/privkey.pem;

    # 클라이언트 인증서를 검증할 CA 번들
    ssl_client_certificate /etc/nginx/ssl/client-ca.pem;

    # on    — 반드시 검증 통과
    # optional — 제출되면 검증, 없어도 통과 (수동 분기)
    # optional_no_ca — 제출만 받고 CA 검증은 하지 않음
    ssl_verify_client on;

    # 체인 깊이 (중간 CA가 끼어 있으면 늘려야 한다)
    ssl_verify_depth 2;

    location / {
        # 검증 결과와 클라이언트 정보를 백엔드로 전달
        proxy_set_header X-SSL-Client-Verify  $ssl_client_verify;
        proxy_set_header X-SSL-Client-DN      $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial  $ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint $ssl_client_fingerprint;

        proxy_pass http://internal-api;
    }
}
```

백엔드는 `X-SSL-Client-DN` 같은 헤더를 보고 어느 클라이언트인지 식별한다. DN 예시: `CN=service-a,O=Internal,C=KR`. CN을 user ID처럼 쓰는 게 흔한 패턴이다.

주의할 점이 두 개 있다.

첫째, 클라이언트가 헤더를 위조하면 안 되므로 `X-SSL-*` 헤더는 nginx가 매 요청마다 덮어써야 한다. `proxy_set_header`로 명시적으로 세팅하면 클라이언트가 보낸 같은 이름의 헤더는 덮어써지지만, 다른 위치에서 if 분기 등으로 누락되지 않는지 확인한다.

둘째, 인증서 폐기(revocation) 처리다. CRL이나 OCSP로 폐기 여부까지 검증하려면 `ssl_crl` 지시어를 추가하거나, 폐기된 시리얼 번호 목록을 nginx 설정에 박아 매번 갱신하는 식으로 운영한다. 일반적으로 사설 CA를 굴린다면 단기 인증서(예: 7일)를 자동 발급하는 쪽이 폐기 관리보다 단순하다.

---

## CAA 레코드

CAA(Certification Authority Authorization)는 어떤 CA가 내 도메인 인증서를 발급할 수 있는지 DNS에 명시하는 레코드다. 잘못된 CA가 발급한 인증서가 신뢰되는 사고를 막는다.

```bash
# DNS에 등록할 CAA 레코드 예시
example.com.  IN  CAA  0 issue "letsencrypt.org"
example.com.  IN  CAA  0 issuewild "letsencrypt.org"
example.com.  IN  CAA  0 iodef "mailto:security@example.com"
```

- `issue` — 일반 인증서 발급 허용 CA
- `issuewild` — 와일드카드 인증서 발급 허용 CA
- `iodef` — 정책 위반 시 통보받을 연락처

확인 명령:

```bash
dig CAA example.com +short
# 0 issue "letsencrypt.org"
```

CAA 레코드 누락이 흔한 사고 패턴 중 하나다. CAA에 `digicert.com`만 등록한 상태로 Let's Encrypt 자동 갱신을 돌리면 갱신이 실패한다. 인증서 만료 임박해서야 알아차리는 경우가 많다. CA를 변경하거나 추가할 때는 DNS 먼저 업데이트하고 발급을 시도한다.

---

## 와일드카드 인증서 자동 발급 (DNS-01)

`*.example.com` 같은 와일드카드는 HTTP-01 챌린지를 쓸 수 없다. DNS-01만 가능하다. 즉 발급할 때마다 DNS에 `_acme-challenge` TXT 레코드를 잠깐 등록해야 한다.

수동으로 매번 등록할 수는 없으니 DNS provider API와 연동되는 Certbot 플러그인을 쓴다.

### Cloudflare

```bash
# 플러그인 설치
sudo apt install python3-certbot-dns-cloudflare

# API 토큰 파일 생성 (Zone:DNS:Edit 권한만)
sudo tee /etc/letsencrypt/cloudflare.ini <<EOF
dns_cloudflare_api_token = your-scoped-token-here
EOF
sudo chmod 600 /etc/letsencrypt/cloudflare.ini

# 와일드카드 발급
sudo certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
    -d example.com -d "*.example.com"
```

### Route53

```bash
sudo apt install python3-certbot-dns-route53

# AWS credentials는 ~/.aws/credentials나 IAM role로 주입
sudo certbot certonly \
    --dns-route53 \
    -d example.com -d "*.example.com"
```

API 토큰은 반드시 권한 최소화한다. Cloudflare는 Zone:DNS:Edit, Route53은 Route53FullAccess가 아니라 특정 hosted zone에 대한 ChangeResourceRecordSets만 부여한다. 토큰이 유출되면 DNS 전체가 공격자 손에 들어간다.

---

## 자동 갱신 + deploy-hook

Certbot은 갱신 자체는 잘 하지만, 갱신 후 nginx에 반영되지 않으면 의미가 없다. 옛 인증서를 그대로 서빙하다가 만료되는 사고가 흔하다.

`/etc/letsencrypt/renewal-hooks/deploy/`에 스크립트를 두면 갱신이 실제로 발생한 인증서마다 호출된다(갱신 안 된 건 호출 안 됨, 그래서 매일 reload되지 않는다).

```bash
# /etc/letsencrypt/renewal-hooks/deploy/01-reload-nginx.sh
#!/bin/bash
set -euo pipefail

# 설정 문법 검증부터 (실패하면 reload하지 않는다)
nginx -t

# graceful reload — 기존 연결 유지
systemctl reload nginx

# 슬랙 알림
DOMAIN=$(basename "$RENEWED_LINEAGE")
EXPIRES=$(openssl x509 -in "$RENEWED_LINEAGE/cert.pem" -noout -enddate | cut -d= -f2)

curl -X POST -H 'Content-Type: application/json' \
    -d "{\"text\": \"[cert-renew] $DOMAIN 갱신 완료. 다음 만료: $EXPIRES\"}" \
    "$SLACK_WEBHOOK_URL"
```

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/01-reload-nginx.sh
```

`RENEWED_LINEAGE`, `RENEWED_DOMAINS` 환경변수는 Certbot이 deploy hook을 호출할 때 자동으로 채워준다. 여러 도메인을 굴리면 도메인별로 분기 처리할 수 있다.

`pre-hook`/`post-hook`/`deploy-hook` 차이를 헷갈리는 경우가 많다.
- `pre-hook` — 갱신 시도 직전 1회 (실제 갱신 여부와 무관)
- `post-hook` — 갱신 시도 직후 1회 (실제 갱신 여부와 무관)
- `deploy-hook` — 실제로 갱신된 인증서마다 1회 (갱신 안 됐으면 호출 안 됨)

reload는 deploy-hook에 두는 게 맞다. post-hook에 두면 매일 불필요하게 reload된다.

---

## 인증서 만료 모니터링

자동 갱신을 믿더라도 모니터링은 별도로 둔다. CAA 누락, DNS 변경, 디스크 풀, deploy-hook 오타 등으로 갱신이 조용히 실패하는 케이스가 있다.

### Prometheus blackbox_exporter

```yaml
# blackbox.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      method: GET
      tls_config:
        insecure_skip_verify: false
```

```yaml
# prometheus.yml — 만료 임박 알람
groups:
  - name: ssl
    rules:
      - alert: SSLCertExpiringSoon
        expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.instance }} 인증서 14일 이내 만료"

      - alert: SSLCertExpiringCritical
        expr: probe_ssl_earliest_cert_expiry - time() < 86400 * 3
        for: 10m
        labels:
          severity: critical
```

`probe_ssl_earliest_cert_expiry`는 Unix timestamp다. `time()`을 빼서 잔여 초를 계산한다.

### cron + openssl (Prometheus 없는 환경)

```bash
#!/bin/bash
# /usr/local/bin/cert-expiry-check.sh
DOMAINS=("example.com" "api.example.com" "admin.example.com")
THRESHOLD_DAYS=14

for DOMAIN in "${DOMAINS[@]}"; do
    EXPIRY=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null \
        | openssl x509 -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    if [ "$DAYS_LEFT" -lt "$THRESHOLD_DAYS" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -d "{\"text\": \"[cert-warn] $DOMAIN — $DAYS_LEFT일 남음\"}"
    fi
done
```

```cron
# 매일 오전 9시 실행
0 9 * * * /usr/local/bin/cert-expiry-check.sh
```

`-servername` 옵션은 SNI 지정용이다. 같은 IP에서 여러 도메인을 서빙하는 경우 빠뜨리면 엉뚱한 인증서를 잡는다.

---

## 보안 헤더

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;

    # HSTS — 브라우저가 항상 HTTPS로 접속하도록 강제
    # max-age=31536000: 1년
    # includeSubDomains: 모든 서브도메인까지 강제 (의미는 아래 별도 설명)
    # preload: 브라우저 내장 목록 등재 신청 가능
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # 클릭재킹 방지
    add_header X-Frame-Options "SAMEORIGIN" always;

    # MIME 타입 스니핑 방지
    add_header X-Content-Type-Options "nosniff" always;

    # Referrer 정책
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 권한 정책
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # CSP — 서비스 특성에 맞게 조정
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'" always;
}
```

`X-XSS-Protection`은 현대 브라우저에서 deprecated됐다(오히려 새 취약점을 만들기도 했다). CSP로 대체한다.

### HSTS preload와 includeSubDomains의 함정

HSTS preload 등재 요건에 `includeSubDomains`가 포함된다. 즉 메인 도메인에 preload를 걸면 모든 서브도메인이 영구적으로 HTTPS 전용이 된다.

문제가 되는 케이스: `internal.example.com`이 인트라넷 자체 서명 인증서로 HTTP만 서빙하던 상황에서 `example.com`을 preload 등재하는 경우. preload된 브라우저는 `internal.example.com`도 HTTPS로 접속하려 하고, 자체 서명 인증서면 사용자가 우회할 방법조차 사라진다(no-bypass 정책).

preload 등재 전에 반드시 모든 서브도메인 목록을 점검한다. 한 번 등재되면 제거 신청해도 브라우저 반영까지 수개월 걸린다. 우선 `max-age`를 짧게(예: 300초) 두고 모든 서브도메인이 HTTPS로 정상 동작하는지 확인한 뒤, 점진적으로 `max-age`를 늘리고 마지막에 `preload`를 추가하는 순서를 권장한다.

---

## 멀티 도메인 / 비표준 포트

```nginx
# SAN 인증서 — 한 인증서에 여러 도메인
server {
    listen 443 ssl;
    http2 on;
    server_name example.com www.example.com api.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
}
```

비표준 포트(예: 8443)에 SSL을 붙이는 건 동일하게 `listen 8443 ssl;`이면 된다. 단 포트가 다른 경우 클라이언트 측에서 문제가 생길 수 있는 부분이 있다.

```nginx
server {
    listen 8443 ssl;
    http2 on;
    server_name admin.example.com;

    ssl_certificate     /etc/letsencrypt/live/admin.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.example.com/privkey.pem;

    # HSTS는 호스트 단위라 포트와 무관하게 적용된다
    # admin.example.com:8443에서 헤더를 발급해도
    # 브라우저는 admin.example.com 호스트 전체를 HTTPS-only로 기억한다
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

비표준 포트로 발급된 HSTS가 의외의 곳까지 영향을 준다. 같은 도메인을 80/8080에서 HTTP로도 쓰던 페이지가 갑자기 안 되는 사례가 있다. HSTS는 호스트(scheme + host)에 묶이고 포트와 무관하다는 점을 기억한다.

### 서브도메인별 별도 서버 블록

```nginx
server {
    listen 443 ssl;
    http2 on;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://api-backend:8080;
    }
}

server {
    listen 443 ssl;
    http2 on;
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

| 버전 | 상태 | 핸드셰이크 | 비고 |
|------|------|-----------|------|
| SSL 3.0 | 사용 금지 | 2-RTT | POODLE 취약점 |
| TLS 1.0 | 사용 금지 | 2-RTT | BEAST 취약점, PCI DSS 비적합 |
| TLS 1.1 | 사용 금지 | 2-RTT | 2021년 주요 브라우저 지원 종료 |
| TLS 1.2 | 사용 가능 | 2-RTT | 광범위 호환성 |
| TLS 1.3 | 권장 | 1-RTT | 속도 개선, 0-RTT 옵션, 구형 암호 제거 |

---

## 인증서 유형 비교

| 항목 | DV | OV | EV |
|------|----|----|----|
| 발급 속도 | 즉시~수 분 | 수 일 | 수 주 |
| 검증 범위 | 도메인 소유권 | 조직 실재 확인 | 법인 정보 심층 확인 |
| 비용 | 무료 (Let's Encrypt) | 유료 | 고비용 |
| 브라우저 표시 | 자물쇠 | 자물쇠 | 자물쇠 (옛 녹색 바는 제거됨) |
| 권장 용도 | 일반 웹 | 기업 서비스 | 금융 등 일부 |

EV의 시각적 차별화(녹색 주소창)는 Chrome 77, Firefox 70 이후 사라졌다. 사용자 체감상 DV와 EV의 차이가 거의 없어 EV 채택률은 계속 떨어지는 추세다.

---

## 트러블슈팅

### `SSL_ERROR_RX_RECORD_TOO_LONG`

브라우저에서 이 오류가 뜨면 거의 100% HTTPS로 와야 할 곳에 HTTP 응답이 가고 있다. 클라이언트가 TLS 핸드셰이크를 기대하는데 평문 HTTP 헤더가 돌아온 것이다. 발생 원인:

- `listen 443;`인데 `ssl` 키워드를 빠뜨림 → 평문 HTTP가 443에서 응답한다
- 리버스 프록시가 잘못된 backend로 라우팅 (HTTP 백엔드를 HTTPS인 줄 알고 노출)
- 로드밸런서에서 SSL 종료한 뒤 origin도 HTTPS인 줄 알고 다시 HTTPS로 전송

```nginx
# 잘못된 예
server {
    listen 443;        # ssl 키워드 누락
    server_name example.com;
}

# 올바른 예
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;
}
```

### `unable to get local issuer certificate`

OCSP stapling 검증에서 자주 본다. `ssl_trusted_certificate`에 중간 체인을 명시하지 않았거나, `fullchain.pem`이 아닌 `cert.pem`만 `ssl_certificate`에 지정했을 때 발생한다.

```nginx
# fullchain.pem = cert.pem + chain.pem
ssl_certificate         /etc/letsencrypt/live/example.com/fullchain.pem;
ssl_certificate_key     /etc/letsencrypt/live/example.com/privkey.pem;
ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;  # OCSP 검증용
```

curl로 검증할 때:

```bash
curl -vI https://example.com 2>&1 | grep -i "issuer\|subject"
# Issuer 항목이 비어있거나 Self-signed로 나오면 체인 누락
```

### Let's Encrypt rate limit

도메인 당 주당 50개 인증서, 동일 도메인 세트 중복 발급은 주당 5개. 흔한 사고:

- CI/CD에서 매 빌드마다 새 인증서 발급 — 1주 못 가서 한도 초과
- staging/production 같은 도메인에서 발급 — 환경별로 별도 도메인 쓰거나 staging 환경(`--staging`) 사용
- 와일드카드 발급 실패가 누적 — 발급은 실패해도 시도 자체가 카운트된다(7일간 5회 실패 한도 별도)

한도 초과 시 1주 기다리는 것 외에 방법이 없다. 운영 도메인을 묶어 하나의 SAN 인증서로 발급하면 카운트를 줄일 수 있다.

### 갱신은 됐는데 옛 인증서가 서빙되는 문제

`certbot renew`는 디스크에 새 파일을 썼지만 nginx가 reload되지 않으면 메모리에 옛 파일이 그대로 남는다. `nginx -s reload`나 `systemctl reload nginx`가 필요하다. deploy-hook에서 처리하는 게 표준이다(위 절 참고).

빠른 진단:

```bash
# 디스크 인증서 만료일
openssl x509 -in /etc/letsencrypt/live/example.com/cert.pem -noout -enddate

# 실제 서빙 중인 인증서 만료일
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null \
    | openssl x509 -noout -enddate
```

두 값이 다르면 reload 누락이다.

### 인증서 발급 후 즉시 안 먹히는 문제

DNS 전파, OCSP 응답 캐시, CDN 캐시 등 여러 레이어가 있다. 발급 직후 `ssl_stapling on`이 켜져 있으면 nginx가 첫 OCSP 응답을 가져오기 전 몇 분간 stapling 없이 응답한다(client-side는 정상 동작). 갱신 직후 SSL Labs 점수가 일시적으로 떨어져 보이는 경우도 같은 이유다.

---

## 검증

```bash
# nginx 설정 문법 검사 (reload 전 필수)
sudo nginx -t

# 특정 TLS 버전으로 연결 테스트
openssl s_client -connect example.com:443 -tls1_2
openssl s_client -connect example.com:443 -tls1_3

# SNI 명시 (multi-tenant 환경 필수)
openssl s_client -servername example.com -connect example.com:443

# 체인 전체 출력
openssl s_client -showcerts -connect example.com:443 </dev/null

# OCSP stapling 응답 확인
openssl s_client -connect example.com:443 -status </dev/null 2>&1 | grep -A 5 "OCSP Response"

# HTTP/3 응답 확인 (curl 7.66+ HTTP/3 빌드)
curl --http3 -I https://example.com

# 외부 검증 도구
# https://www.ssllabs.com/ssltest/  — A+ 등급 목표
# https://securityheaders.com/      — 보안 헤더 검사
# https://hstspreload.org/          — HSTS preload 등재 상태 조회
```

---

## 스니펫으로 재사용

설정이 길어지면 스니펫으로 분리해 여러 서버 블록에서 include하는 게 편하다.

```nginx
# /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

```nginx
# /etc/nginx/snippets/letsencrypt.conf
ssl_certificate         /etc/letsencrypt/live/example.com/fullchain.pem;
ssl_certificate_key     /etc/letsencrypt/live/example.com/privkey.pem;
ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
```

```nginx
# 서버 블록에서 include로 재사용
server {
    listen 443 ssl;
    http2 on;
    server_name example.com;

    include snippets/letsencrypt.conf;
    include snippets/ssl-params.conf;

    location / {
        proxy_pass http://backend;
    }
}
```

스니펫 안에서 `add_header`를 정의했더라도 server 블록 안에서 다시 `add_header`를 쓰면 스니펫의 헤더는 모두 무효화된다(nginx의 `add_header` 상속 규칙). HSTS 등이 갑자기 빠진 것 같으면 server 블록에 추가 헤더가 있는지부터 확인한다.
