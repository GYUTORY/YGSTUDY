---
title: Nginx vs Caddy
tags: [webserver, nginx, caddy, reverse-proxy, https, docker, comparison]
updated: 2026-04-14
---

# Nginx vs Caddy

## 왜 비교하는가

리버스 프록시 서버를 고를 때 Nginx와 Caddy가 후보에 오른다. 둘 다 리버스 프록시, 정적 파일 서빙, 로드 밸런싱을 지원한다. 하지만 설정 방식, HTTPS 처리, 운영 방식에서 차이가 크다. 프로젝트 규모와 팀 상황에 따라 선택이 달라진다.

## 아키텍처 차이

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx 아키텍처                       │
│                                                         │
│  master process (root)                                  │
│    ├── worker process 1  ──┐                            │
│    ├── worker process 2  ──┼── epoll/kqueue 이벤트 루프  │
│    ├── worker process 3  ──┘   (단일 스레드, 비동기 I/O)  │
│    └── cache manager                                    │
│                                                         │
│  - C로 작성                                              │
│  - worker 수 = CPU 코어 수 맞추는 게 일반적               │
│  - 모듈은 컴파일 시점에 포함 (동적 모듈도 있지만 제한적)    │
│  - 설정 변경 시 reload → 새 worker 생성, 기존 연결 처리 후 │
│    이전 worker 종료 (graceful)                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      Caddy 아키텍처                       │
│                                                         │
│  단일 프로세스 (Go runtime)                               │
│    ├── goroutine pool ── net/http 서버                    │
│    ├── TLS 자동화 모듈 (ACME 클라이언트 내장)              │
│    ├── 인증서 저장소 (~/.local/share/caddy/)              │
│    └── Admin API (localhost:2019)                        │
│                                                         │
│  - Go로 작성                                             │
│  - goroutine 기반 동시성 (OS 스레드보다 가벼움)            │
│  - 모듈은 빌드 시 xcaddy로 추가하거나 Caddyfile에서 선언   │
│  - 설정 변경 시 Admin API로 무중단 적용 (프로세스 재시작 X) │
└─────────────────────────────────────────────────────────┘
```

Nginx는 master-worker 모델이다. master 프로세스가 worker를 관리하고, 각 worker가 이벤트 루프로 수천 개의 연결을 처리한다. C 기반이라 메모리 사용량이 적고 예측 가능하다.

Caddy는 Go 런타임 위에서 goroutine으로 요청을 처리한다. Go의 가비지 컬렉터가 메모리를 관리하므로 Nginx보다 메모리 사용량이 다소 높다. 대신 ACME 클라이언트가 내장되어 있어서 인증서 관련 외부 의존성이 없다.

## 설정 복잡도

같은 작업을 하는 설정을 비교하면 차이가 확실하다.

### 정적 파일 서빙

**Nginx:**

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
}
```

**Caddy:**

```caddyfile
example.com {
    root * /var/www/html
    file_server
    encode gzip
}
```

Nginx는 `listen`, `server_name`, `location` 블록, `try_files` 같은 지시어를 알아야 한다. Caddy는 도메인과 기본 지시어 몇 개면 된다.

### 리버스 프록시 + HTTPS

**Nginx (certbot 사용):**

```nginx
# /etc/nginx/sites-available/app.conf

# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name app.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

인증서 발급은 별도로 해야 한다:

```bash
sudo certbot certonly --nginx -d app.example.com

# 갱신 자동화 (cron 또는 systemd timer)
echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'" | sudo crontab -
```

**Caddy:**

```caddyfile
app.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

이게 전부다. HTTPS, HTTP→HTTPS 리다이렉트, 인증서 발급/갱신, HSTS 헤더, OCSP 스테이플링 전부 자동이다. 별도의 certbot이나 cron 설정이 필요 없다.

## HTTPS 자동화 상세

### Nginx의 HTTPS

Nginx 자체에는 인증서 자동 발급 기능이 없다. certbot 같은 외부 도구에 의존한다.

```bash
# certbot 설치
sudo apt install certbot python3-certbot-nginx

# 인증서 발급 (Nginx 설정 자동 수정)
sudo certbot --nginx -d example.com -d www.example.com

# 또는 설정 건드리지 않고 인증서만 발급
sudo certbot certonly --webroot -w /var/www/html -d example.com
```

certbot이 잘 동작하지만 신경 써야 할 것들이 있다:

- cron이나 systemd timer로 갱신 자동화를 직접 설정해야 한다
- 멀티 서버 환경에서 인증서 공유가 번거롭다 (NFS, S3 동기화 등)
- 와일드카드 인증서는 DNS challenge가 필요하고 DNS API 연동을 따로 해야 한다
- 갱신 실패 시 알림도 직접 구성해야 한다

### Caddy의 HTTPS

Caddy는 도메인이 설정에 있으면 자동으로 인증서를 처리한다.

```caddyfile
# 이것만으로 HTTPS 완성
example.com {
    respond "Hello"
}

# 와일드카드 인증서 (DNS challenge 자동)
*.example.com {
    tls {
        dns cloudflare {env.CF_API_TOKEN}
    }
    reverse_proxy 127.0.0.1:3000
}
```

Caddy가 자동으로 하는 것들:

- Let's Encrypt 또는 ZeroSSL에서 인증서 발급
- 만료 30일 전 갱신 시도, 실패하면 재시도
- OCSP 스테이플링
- HTTP→HTTPS 리다이렉트
- TLS 1.2/1.3, 안전한 cipher suite 기본 적용

내부 서비스용 자체 서명 인증서도 간단하다:

```caddyfile
# 내부 CA로 자체 서명 인증서 자동 생성
https://internal.service.local {
    tls internal
    reverse_proxy 127.0.0.1:8080
}
```

## 리버스 프록시 설정 차이

### 기본 리버스 프록시

**Nginx:**

```nginx
upstream backend {
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
    server 127.0.0.1:3003;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL 설정 생략

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    # 헬스체크 (Nginx Plus에서만 active health check 가능)
    # 오픈소스 Nginx는 passive health check만 지원
    location /health {
        proxy_pass http://backend;
        access_log off;
    }
}
```

**Caddy:**

```caddyfile
api.example.com {
    reverse_proxy 127.0.0.1:3001 127.0.0.1:3002 127.0.0.1:3003 {
        lb_policy round_robin

        health_uri /health
        health_interval 10s
        health_timeout 5s

        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Nginx 오픈소스 버전은 active health check를 지원하지 않는다. upstream 서버가 응답 실패하면 일정 시간 제외하는 passive 방식만 쓸 수 있다. active health check가 필요하면 Nginx Plus(유료)를 써야 한다. Caddy는 무료 버전에서 active health check를 지원한다.

### WebSocket 프록시

**Nginx:**

```nginx
location /ws {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
}
```

Nginx에서 WebSocket 프록시할 때 `proxy_http_version 1.1`과 `Upgrade`, `Connection` 헤더를 명시해야 한다. 빠뜨리면 WebSocket 핸드셰이크가 실패한다. `proxy_read_timeout`도 늘려야 하는데, 기본값 60초가 지나면 유휴 WebSocket 연결을 끊어버린다.

**Caddy:**

```caddyfile
example.com {
    reverse_proxy /ws 127.0.0.1:3000
}
```

Caddy는 WebSocket을 자동 감지해서 별도 설정이 필요 없다. Upgrade 헤더를 알아서 전달한다.

### 경로별 분기

**Nginx:**

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    location /api/ {
        proxy_pass http://127.0.0.1:3000/;  # 끝에 /가 있으면 /api/ 제거
        proxy_set_header Host $host;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:4000/;
        proxy_set_header Host $host;
        
        # IP 제한
        allow 10.0.0.0/8;
        deny all;
    }

    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;  # SPA 라우팅
    }
}
```

`proxy_pass` 끝에 `/`를 붙이느냐 안 붙이느냐에 따라 경로 전달 방식이 달라진다. 이걸 모르면 백엔드에 잘못된 경로가 전달되는 문제가 생긴다.

- `proxy_pass http://127.0.0.1:3000;` → `/api/users` 그대로 전달
- `proxy_pass http://127.0.0.1:3000/;` → `/users`로 변환해서 전달

**Caddy:**

```caddyfile
example.com {
    handle /api/* {
        reverse_proxy 127.0.0.1:3000 {
            header_up -prefix /api
        }
    }

    handle /admin/* {
        @blocked not remote_ip 10.0.0.0/8
        respond @blocked 403

        reverse_proxy 127.0.0.1:4000
    }

    handle {
        root * /var/www/frontend
        try_files {path} /index.html
        file_server
    }
}
```

Caddy에서 경로 접두사를 제거하려면 `handle_path`를 쓰면 더 간결하다:

```caddyfile
handle_path /api/* {
    reverse_proxy 127.0.0.1:3000
}
```

`handle_path`는 매칭된 접두사를 자동으로 제거하고 백엔드에 전달한다.

## 성능 비교

### 벤치마크 수치 해석

인터넷에 떠도는 벤치마크 결과를 그대로 믿으면 안 된다. 테스트 조건에 따라 결과가 크게 달라진다.

**일반적인 경향:**

| 항목 | Nginx | Caddy |
|------|-------|-------|
| 정적 파일 서빙 (RPS) | 높음 | Nginx 대비 80~90% |
| 리버스 프록시 처리량 | 높음 | Nginx 대비 85~95% |
| 메모리 사용량 (idle) | 2~5MB | 10~30MB |
| 메모리 사용량 (부하) | 10~50MB | 30~100MB |
| CPU 사용률 | 낮음 | Nginx 대비 약간 높음 |
| TLS 핸드셰이크 | 빠름 | 비슷하거나 약간 느림 |

Nginx가 raw 성능에서 앞서지만, 대부분의 서비스에서 웹 서버 자체가 병목이 되는 경우는 거의 없다. 백엔드 애플리케이션이나 DB가 병목인 상황에서 웹 서버 성능 차이 10~15%는 의미가 없다.

**성능이 중요한 경우:**

- 일 수천만 요청 이상의 대규모 트래픽
- CDN 오리진 서버처럼 정적 파일 서빙이 핵심인 경우
- 마이크로초 단위 레이턴시가 중요한 경우

이런 경우가 아니면 Caddy의 성능으로 충분하다.

### 직접 벤치마크할 때

```bash
# wrk로 테스트
wrk -t4 -c100 -d30s http://localhost:8080/

# 또는 hey로 테스트
hey -n 10000 -c 100 http://localhost:8080/
```

벤치마크 시 주의할 점:

- 같은 하드웨어에서 테스트한다
- OS 수준 튜닝(`ulimit`, TCP 커널 파라미터)을 동일하게 맞춘다
- TLS 유무를 통일한다 (TLS 있으면 성능 차이 패턴이 달라진다)
- 워밍업 후 측정한다 (Caddy는 Go 런타임 특성상 초기 요청에서 약간 느릴 수 있다)

## Docker 환경 운용

### Nginx Docker 구성

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - app
    restart: unless-stopped

  # certbot 컨테이너가 별도로 필요하다
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

  app:
    build: .
    expose:
      - "3000"
```

Nginx Docker 환경의 번거로운 점:

- certbot 컨테이너를 따로 띄워야 한다
- 인증서 볼륨을 Nginx와 certbot이 공유해야 한다
- 초기 인증서 발급 시 Nginx가 아직 인증서 없이 시작해야 하는 닭-달걀 문제가 있다 (HTTP 전용 설정으로 먼저 시작 → certbot 실행 → HTTPS 설정으로 교체하는 과정 필요)
- 인증서 갱신 후 Nginx에 reload 시그널을 보내야 한다

### Caddy Docker 구성

```yaml
# docker-compose.yml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3 (QUIC)
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data      # 인증서 저장
      - caddy_config:/config  # 설정 캐시
    depends_on:
      - app
    restart: unless-stopped

  app:
    build: .
    expose:
      - "3000"

volumes:
  caddy_data:
  caddy_config:
```

```caddyfile
# Caddyfile
app.example.com {
    reverse_proxy app:3000
}
```

Caddy는 인증서를 `/data` 디렉토리에 자동 저장한다. Docker named volume으로 잡아두면 컨테이너를 재생성해도 인증서가 유지된다. 별도의 certbot 컨테이너가 필요 없고, 닭-달걀 문제도 없다.

### Docker 내부 서비스 간 통신

Docker Compose 환경에서 서비스 간 통신은 서비스명으로 한다. 컨테이너 IP가 바뀔 수 있으므로 IP를 하드코딩하면 안 된다.

**Nginx:**

```nginx
# Docker 내부 DNS resolver 지정이 필요한 경우가 있다
resolver 127.0.0.11 valid=30s;

upstream app {
    server app:3000;
}
```

Nginx는 upstream을 시작 시점에 DNS resolve하고 캐시한다. 컨테이너가 재시작되어 IP가 바뀌면 Nginx가 이전 IP로 계속 요청을 보내는 문제가 있다. `resolver` 지시어로 Docker 내부 DNS를 지정하고, 변수에 서버 주소를 넣는 우회법을 써야 한다:

```nginx
location / {
    resolver 127.0.0.11 valid=10s;
    set $upstream http://app:3000;
    proxy_pass $upstream;
}
```

**Caddy:**

```caddyfile
example.com {
    reverse_proxy app:3000
}
```

Caddy는 요청마다 DNS를 resolve한다. 컨테이너가 재시작되어 IP가 바뀌어도 자동으로 새 IP를 찾는다. 별도의 resolver 설정이 필요 없다.

## 마이그레이션 시 주의사항

### Nginx에서 Caddy로

1. **설정 변환은 수동으로 한다.** 자동 변환 도구가 있지만 100% 변환은 안 된다. `location` 블록의 정규식 매칭, `if` 조건문, 복잡한 `rewrite` 규칙은 직접 변환해야 한다.

2. **포트 충돌을 확인한다.** Nginx와 Caddy를 같은 서버에서 동시에 테스트하려면 포트가 겹치지 않게 해야 한다.

```bash
# Nginx가 80, 443을 쓰고 있는 상태에서 Caddy 테스트
# Caddy를 다른 포트로 실행
caddy run --config Caddyfile.test --adapter caddyfile &
# Caddyfile.test에서 :8080, :8443 등 다른 포트 사용
```

3. **Nginx 전용 기능 확인.** 아래 기능들은 Caddy에서 동일하게 동작하지 않거나 방식이 다르다:

```
Nginx                          Caddy 대응
─────────────────────────────  ────────────────────────────
if ($host)                     host matcher (요청 매칭 방식이 다름)
map $uri $backend              map 지시어 또는 CEL 표현식
limit_req_zone                 rate_limit 모듈 (별도 빌드 필요)
proxy_cache                    cache-handler 모듈 (별도 빌드 필요)
auth_basic                     basicauth 지시어
sub_filter                     templates 또는 replace 모듈
nginx -t (문법 검사)            caddy validate --config Caddyfile
```

4. **모듈 의존성을 확인한다.** Nginx에서 서드파티 모듈(lua-nginx-module, headers-more 등)을 쓰고 있다면 Caddy에서 대응하는 모듈이 있는지 확인한다. 없으면 `xcaddy`로 커스텀 빌드를 해야 한다.

```bash
# Caddy 커스텀 빌드 (추가 모듈 포함)
xcaddy build \
    --with github.com/caddyserver/cache-handler \
    --with github.com/mholt/caddy-ratelimit
```

5. **로그 포맷이 다르다.** Nginx의 `access_log` 포맷과 Caddy의 로그 포맷이 다르다. 로그 파싱 파이프라인(ELK, Loki 등)을 쓰고 있다면 파서를 수정해야 한다.

```caddyfile
# Caddy 로그 설정 (JSON 포맷이 기본)
example.com {
    log {
        output file /var/log/caddy/access.log
        format json
    }
    reverse_proxy 127.0.0.1:3000
}
```

Caddy 로그는 기본이 JSON이다. 구조화된 로그라서 파싱은 편하지만, 기존에 Nginx combined 포맷에 맞춘 파이프라인이 있다면 변경이 필요하다.

### Caddy에서 Nginx로

Caddy에서 Nginx로 옮기는 경우는 드물지만, 성능 한계에 부딪히거나 조직에서 Nginx를 표준으로 정한 경우에 생긴다.

1. **인증서를 수동으로 관리해야 한다.** Caddy가 자동으로 해주던 인증서 발급/갱신을 certbot이나 다른 도구로 직접 설정해야 한다.

2. **Caddy가 자동으로 넣어주던 보안 헤더를 명시적으로 추가해야 한다.**

```nginx
# Caddy가 자동으로 처리하던 것들을 직접 설정
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

3. **WebSocket, HTTP/2 설정을 수동으로 해야 한다.** Caddy가 자동 감지하던 것들을 Nginx에서는 명시적으로 설정한다.

## 어떤 상황에서 무엇을 쓸 것인가

**Nginx가 맞는 경우:**

- 대규모 트래픽을 처리하는 프로덕션 환경에서 검증된 안정성이 필요할 때
- `limit_req`, `proxy_cache`, lua 스크립팅 등 세밀한 제어가 필요할 때
- 팀에 Nginx 운영 경험이 충분하고, 인프라 자동화(Ansible, Terraform)가 갖춰져 있을 때
- 이미 Nginx 기반 인프라가 크게 구축되어 있을 때

**Caddy가 맞는 경우:**

- 소규모~중규모 서비스에서 빠르게 HTTPS를 적용해야 할 때
- 인프라 전담 인력 없이 개발자가 직접 서버를 관리할 때
- Docker 환경에서 인증서 관리를 단순화하고 싶을 때
- 사이드 프로젝트나 MVP 단계에서 설정에 시간을 쓰고 싶지 않을 때

둘 다 프로덕션에서 쓸 수 있다. "Caddy는 장난감"이라는 인식은 v1 시절 얘기고, v2는 충분히 안정적이다. 다만 트래픽이 일 수천만 요청을 넘어가는 규모라면 Nginx의 성능 여유가 의미 있어진다.
