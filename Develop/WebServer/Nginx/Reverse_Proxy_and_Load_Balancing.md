---
title: Nginx 리버스 프록시 & 로드밸런싱 실전 가이드
tags: [webserver, nginx, reverse-proxy, load-balancing, upstream, ssl, tls, https]
updated: 2026-03-01
---

# Nginx 리버스 프록시 & 로드밸런싱

## 배경

백엔드 서버를 직접 외부에 노출하는 대신 **Nginx를 리버스 프록시**로 앞에 두면 보안, 성능, 확장성에서 큰 이점을 얻는다. 프로덕션 환경에서 Nginx는 거의 필수적인 인프라 구성 요소이다.

### 리버스 프록시란

```
포워드 프록시 (클라이언트 측):
  Client → Proxy → Internet → Server
  (클라이언트를 숨김)

리버스 프록시 (서버 측):
  Client → Internet → Nginx → Backend Server
  (백엔드 서버를 숨김)
```

### Nginx가 리버스 프록시로 하는 일

| 역할 | 설명 |
|------|------|
| **SSL 종료** | HTTPS를 Nginx에서 처리, 백엔드는 HTTP |
| **로드밸런싱** | 여러 백엔드 서버에 트래픽 분배 |
| **정적 파일 서빙** | HTML, CSS, JS, 이미지를 Nginx가 직접 전달 |
| **캐싱** | 응답을 캐시하여 백엔드 부하 감소 |
| **요청 제한** | Rate Limiting으로 DDoS/과도한 요청 방어 |
| **보안 헤더** | HSTS, X-Frame-Options 등 보안 헤더 추가 |
| **압축** | gzip/brotli 압축으로 응답 크기 감소 |

## 핵심

### 1. 리버스 프록시 기본 설정

#### 단일 백엔드 서버

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8080;   # 백엔드 서버

        # 필수 프록시 헤더
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**프록시 헤더 설명:**

| 헤더 | 용도 |
|------|------|
| `Host` | 원본 요청의 호스트명 전달 |
| `X-Real-IP` | 실제 클라이언트 IP 전달 |
| `X-Forwarded-For` | 프록시 체인의 IP 목록 |
| `X-Forwarded-Proto` | 원본 프로토콜 (http/https) |

📌 Spring Boot에서 이 헤더를 인식하려면 `server.forward-headers-strategy=native` 설정 필요.

#### 경로별 라우팅

```nginx
server {
    listen 80;
    server_name example.com;

    # 프론트엔드 (React/Vue SPA)
    location / {
        root /var/www/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;   # SPA 라우팅
    }

    # API 서버
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 정적 파일 (Nginx가 직접 서빙)
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 2. 로드밸런싱

여러 백엔드 서버에 트래픽을 분산한다.

#### upstream 블록

```nginx
# 백엔드 서버 그룹 정의
upstream backend {
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
    server 10.0.1.12:8080;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://backend;   # upstream 이름 사용
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 로드밸런싱 알고리즘

| 알고리즘 | 설정 | 동작 | 사용 상황 |
|---------|------|------|----------|
| **Round Robin** | (기본값) | 순서대로 분배 | 서버 성능 동일 |
| **Weighted** | `weight=3` | 가중치 기반 분배 | 서버 성능 차이 |
| **Least Connections** | `least_conn` | 연결 수 적은 서버 우선 | 요청 처리 시간 불균일 |
| **IP Hash** | `ip_hash` | 클라이언트 IP 기반 고정 | 세션 유지 필요 |
| **Hash** | `hash $request_uri` | 커스텀 키 기반 | 캐시 효율 극대화 |

```nginx
# Weighted Round Robin
upstream backend {
    server 10.0.1.10:8080 weight=3;   # 트래픽 60%
    server 10.0.1.11:8080 weight=2;   # 트래픽 40%
}

# Least Connections
upstream backend {
    least_conn;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
    server 10.0.1.12:8080;
}

# IP Hash (세션 고정)
upstream backend {
    ip_hash;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}
```

#### 헬스 체크 및 장애 대응

```nginx
upstream backend {
    server 10.0.1.10:8080 max_fails=3 fail_timeout=30s;   # 3번 실패 → 30초 제외
    server 10.0.1.11:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8080 backup;                          # 다른 서버 모두 실패 시 사용
}
```

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `max_fails` | 1 | 실패 허용 횟수 |
| `fail_timeout` | 10s | 실패 후 제외 시간 |
| `backup` | - | 백업 서버 (평상시 미사용) |
| `down` | - | 서버를 수동으로 비활성화 |

### 3. SSL/TLS (HTTPS) 설정

#### Let's Encrypt 인증서

```bash
# Certbot으로 무료 SSL 인증서 발급
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com

# 자동 갱신 (cron)
sudo certbot renew --dry-run
```

#### HTTPS 설정

```nginx
# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS 서버
server {
    listen 443 ssl http2;
    server_name example.com;

    # SSL 인증서
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS (Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OCSP Stapling (인증서 검증 가속)
    ssl_stapling on;
    ssl_stapling_verify on;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. 캐싱

Nginx에서 백엔드 응답을 캐시하면 서버 부하를 크게 줄일 수 있다.

```nginx
# 캐시 영역 정의 (http 블록)
proxy_cache_path /var/cache/nginx levels=1:2
                 keys_zone=api_cache:10m    # 캐시 키 메모리 10MB
                 max_size=1g                # 디스크 최대 1GB
                 inactive=60m               # 60분 미사용 시 삭제
                 use_temp_path=off;

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # API 응답 캐싱
    location /api/products {
        proxy_pass http://backend;
        proxy_cache api_cache;
        proxy_cache_valid 200 10m;           # 200 응답: 10분 캐시
        proxy_cache_valid 404 1m;            # 404 응답: 1분 캐시
        proxy_cache_key "$request_method$request_uri";

        add_header X-Cache-Status $upstream_cache_status;   # 캐시 HIT/MISS 확인
    }

    # 인증 API는 캐시하지 않음
    location /api/auth {
        proxy_pass http://backend;
        proxy_no_cache 1;
        proxy_cache_bypass 1;
    }
}
```

### 5. Rate Limiting

과도한 요청이나 DDoS 공격을 방어한다.

```nginx
# 요청 제한 영역 정의 (http 블록)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;    # IP당 초당 10회
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;   # 로그인: 분당 5회

server {
    # 일반 API
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        # burst=20: 순간 20개까지 허용
        # nodelay: 대기 없이 즉시 처리 (초과 시 503)

        proxy_pass http://backend;
    }

    # 로그인 API (더 엄격)
    location /api/auth/login {
        limit_req zone=login_limit burst=3;

        proxy_pass http://backend;
    }
}
```

### 6. 보안 헤더

```nginx
# 보안 헤더 모음 (include로 재사용)
add_header X-Frame-Options "SAMEORIGIN" always;           # 클릭재킹 방지
add_header X-Content-Type-Options "nosniff" always;       # MIME 스니핑 방지
add_header X-XSS-Protection "1; mode=block" always;       # XSS 필터
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

### 7. Gzip 압축

```nginx
# http 블록에 설정
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;                    # 압축 레벨 (1-9, 6이 균형)
gzip_min_length 1024;                 # 1KB 이상만 압축
gzip_types
    text/plain
    text/css
    text/javascript
    application/json
    application/javascript
    application/xml
    image/svg+xml;
```

## 예시

### 1. 프로덕션 전체 구성 예시

Spring Boot + React SPA를 Nginx로 서빙하는 실전 설정이다.

```nginx
# /etc/nginx/nginx.conf

user nginx;
worker_processes auto;                  # CPU 코어 수에 맞춤
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # 로그 포맷
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # 성능
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;

    # 버퍼
    client_max_body_size 10m;           # 업로드 최대 크기
    client_body_buffer_size 128k;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml image/svg+xml;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # 캐시
    proxy_cache_path /var/cache/nginx levels=1:2
                     keys_zone=static_cache:10m max_size=1g inactive=7d;

    # 업스트림
    upstream api_backend {
        least_conn;
        server 10.0.1.10:8080 max_fails=3 fail_timeout=30s;
        server 10.0.1.11:8080 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # HTTP → HTTPS 리다이렉트
    server {
        listen 80;
        server_name example.com www.example.com;
        return 301 https://example.com$request_uri;
    }

    # HTTPS 메인 서버
    server {
        listen 443 ssl http2;
        server_name example.com;

        # SSL
        ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;

        # 보안 헤더
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # 프론트엔드 SPA
        location / {
            root /var/www/frontend/dist;
            index index.html;
            try_files $uri $uri/ /index.html;

            # 정적 파일 캐시
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
                expires 30d;
                add_header Cache-Control "public, immutable";
            }
        }

        # API
        location /api/ {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # 로그인 (엄격한 Rate Limit)
        location /api/auth/login {
            limit_req zone=login burst=3;

            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400s;
        }

        # 헬스 체크 (외부 접근 차단)
        location /actuator/ {
            deny all;
        }
    }
}
```

### 2. Docker Compose와 Nginx

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/var/www/frontend/dist:ro
    depends_on:
      - api
    restart: unless-stopped

  api:
    image: my-api:latest
    expose:
      - "8080"            # 외부 미노출, Nginx에서만 접근
    environment:
      - SPRING_PROFILES_ACTIVE=prod
    restart: unless-stopped
```

```nginx
# Docker 환경에서의 upstream (서비스 이름 사용)
upstream api_backend {
    server api:8080;      # Docker 서비스 이름으로 접근
}
```

## 운영 팁

### 설정 검증 및 관리

```bash
# 설정 문법 검사 (반드시 reload 전에 실행)
sudo nginx -t

# 설정 리로드 (무중단)
sudo nginx -s reload

# 상태 확인
sudo systemctl status nginx

# 로그 실시간 확인
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 성능 튜닝 체크리스트

| 항목 | 설정 | 효과 |
|------|------|------|
| `worker_processes auto` | CPU 코어 수 자동 | CPU 활용 극대화 |
| `worker_connections 4096` | 워커당 연결 수 | 동시 처리 능력 |
| `keepalive 32` | upstream keepalive | 연결 재사용 |
| `gzip on` | 응답 압축 | 전송량 60~80% 감소 |
| `proxy_cache` | 응답 캐싱 | 백엔드 부하 감소 |
| `sendfile on` | 커널 레벨 파일 전송 | 정적 파일 성능 향상 |

### Nginx vs Apache 비교

| 항목 | Nginx | Apache |
|------|-------|--------|
| **아키텍처** | 이벤트 기반, 비동기 | 프로세스/스레드 기반 |
| **동시 연결** | 수만 개 | 수천 개 |
| **메모리** | 매우 효율적 | 연결당 메모리 소비 |
| **정적 파일** | 매우 빠름 | 보통 |
| **동적 컨텐츠** | 외부 프로세서 필요 | mod_php 내장 가능 |
| **설정** | 중앙 집중식 | .htaccess 분산 가능 |
| **사용 추세** | 증가 중 | 감소 중 |

📌 **결론**: 리버스 프록시/로드밸런서로는 Nginx가 사실상 표준. 레거시 PHP 호스팅 외에는 Nginx를 선택하는 것이 일반적이다.

## 참고

- [Nginx 공식 문서](https://nginx.org/en/docs/)
- [Nginx 리버스 프록시 가이드](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Nginx 기본 개념](Definition.md)
- [CORS 설정](CORS.md)
