---
title: Nginx
tags: [webserver, nginx, reverse-proxy, load-balancer]
updated: 2026-03-25
---

# Nginx

## Nginx란

Igor Sysoev가 2004년에 만든 웹 서버. 정적 파일 서빙, 리버스 프록시, 로드 밸런서로 쓴다. Apache가 연결마다 프로세스/스레드를 만드는 것과 달리 이벤트 기반 비동기 모델로 동작해서 적은 메모리로 동시 연결을 많이 처리한다.

## 설치와 실행

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install nginx

# 버전 확인
nginx -v

# 시작/중지/재시작
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx

# 설정 변경 후 무중단 리로드 (실무에서는 restart 대신 이걸 쓴다)
sudo systemctl reload nginx
```

### macOS (Homebrew)

```bash
brew install nginx

# Homebrew로 설치하면 기본 포트가 8080이다
nginx
nginx -s reload
nginx -s stop
```

### 설정 파일 문법 검사

설정을 수정한 뒤 reload 전에 반드시 문법 검사를 해야 한다. 문법 오류가 있는 상태에서 reload하면 기존 설정으로 계속 돌아가지만, restart하면 서비스가 죽는다.

```bash
sudo nginx -t
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## 프로세스 구조: Master와 Worker

Nginx는 master 프로세스 1개와 worker 프로세스 여러 개로 돈다.

- **master**: 설정 파일 읽기, worker 관리. 실제 요청은 처리하지 않는다.
- **worker**: 실제 클라이언트 요청을 처리한다. 각 worker가 이벤트 루프를 돌면서 수천 개 연결을 동시에 처리한다.

프로세스 확인:

```bash
ps aux | grep nginx
# root      1234  ...  nginx: master process /usr/sbin/nginx
# www-data  1235  ...  nginx: worker process
# www-data  1236  ...  nginx: worker process
```

master는 root로, worker는 `nginx.conf`에서 지정한 사용자(보통 `www-data` 또는 `nginx`)로 실행된다.

### worker 프로세스 수 설정

```nginx
# /etc/nginx/nginx.conf

worker_processes auto;  # CPU 코어 수에 맞춰 자동 설정
# worker_processes 4;   # 직접 지정할 수도 있다

events {
    worker_connections 1024;  # worker 하나당 최대 동시 연결 수
    # 이론상 최대 동시 연결 = worker_processes × worker_connections
}
```

`auto`로 두면 CPU 코어 수만큼 worker를 만든다. 대부분의 경우 `auto`가 맞다. worker_connections는 기본값 512인데, 트래픽이 많으면 1024~4096 정도로 올린다.

## 설정 파일 구조

설정 파일 위치:

```bash
# Ubuntu/Debian
/etc/nginx/nginx.conf              # 메인 설정
/etc/nginx/sites-available/        # 사이트별 설정 파일
/etc/nginx/sites-enabled/          # 활성화된 사이트 (심볼릭 링크)

# CentOS/RHEL
/etc/nginx/nginx.conf
/etc/nginx/conf.d/                 # *.conf 파일을 자동으로 읽는다
```

### 기본 설정 파일 예제

```nginx
# /etc/nginx/nginx.conf

user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 로그 포맷 정의
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main;

    sendfile on;           # 커널에서 직접 파일 전송 (성능 향상)
    tcp_nopush on;         # sendfile과 같이 쓴다
    keepalive_timeout 65;
    gzip on;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

설정 파일은 `main` → `events` / `http` → `server` → `location` 순으로 중첩된다. 상위에서 설정한 값은 하위로 상속되고, 하위에서 같은 항목을 쓰면 덮어쓴다.

## 정적 파일 서빙

가장 기본적인 사용법. 정적 파일을 Nginx가 직접 서빙한다.

```nginx
# /etc/nginx/sites-available/my-site

server {
    listen 80;
    server_name example.com;

    root /var/www/my-site;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # CSS, JS, 이미지는 캐시 헤더를 붙인다
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

`try_files $uri $uri/ =404`는 요청 URI에 해당하는 파일을 찾고, 없으면 디렉토리를 찾고, 그래도 없으면 404를 반환한다.

## 리버스 프록시

백엔드 서버 앞에 Nginx를 두는 구성. 실무에서 가장 많이 쓰는 패턴이다.

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;

        # 백엔드에 클라이언트 정보 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 주의할 점

**proxy_set_header를 빠뜨리면 안 된다.** 백엔드 애플리케이션에서 클라이언트 IP를 찍을 때 `X-Real-IP`나 `X-Forwarded-For`가 없으면 전부 `127.0.0.1`로 찍힌다. 로그 분석이나 IP 기반 제한이 먹히지 않는다.

**proxy_pass 끝에 슬래시(/) 유무가 동작을 바꾼다:**

```nginx
# /api/users 요청이 들어올 때

location /api/ {
    proxy_pass http://backend;
    # → 백엔드에 /api/users 그대로 전달
}

location /api/ {
    proxy_pass http://backend/;
    # → 백엔드에 /users 로 전달 (/api/ 가 잘린다)
}
```

이걸 모르고 설정하면 백엔드에서 404가 나오는데, Nginx 로그에는 정상으로 찍혀서 찾기 어렵다.

## 로드 밸런싱

여러 백엔드 서버에 요청을 분산한다.

```nginx
upstream backend_servers {
    # 기본은 라운드 로빈
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080 weight=2;  # 가중치 - 이 서버에 2배 더 보낸다

    # server 10.0.0.4:8080 backup;  # 다른 서버가 전부 죽으면 이 서버 사용
    # server 10.0.0.5:8080 down;    # 점검 중 - 요청 안 보냄
}

server {
    listen 80;

    location / {
        proxy_pass http://backend_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 분산 방식

```nginx
upstream backend {
    # 라운드 로빈 (기본값) - 순서대로 돌아가며 보낸다
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}

upstream backend {
    least_conn;  # 현재 연결이 가장 적은 서버로 보낸다
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}

upstream backend {
    ip_hash;  # 같은 클라이언트 IP는 같은 서버로 보낸다 (세션 유지에 사용)
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
}
```

`ip_hash`는 세션을 서버 메모리에 저장하는 레거시 애플리케이션에서 쓴다. Redis 같은 외부 세션 스토어를 쓰면 `ip_hash`가 필요 없다.

### 헬스 체크

```nginx
upstream backend {
    server 10.0.0.1:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.2:8080 max_fails=3 fail_timeout=30s;
}
```

30초 안에 3번 실패하면 해당 서버를 30초간 제외한다. 30초 후 다시 요청을 보내서 정상이면 복귀시킨다. 기본값은 `max_fails=1`, `fail_timeout=10s`다.

## HTTPS 설정

```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;  # HTTP → HTTPS 리다이렉트
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 1.2 이상만 허용
    ssl_protocols TLSv1.2 TLSv1.3;

    # SSL 세션 캐시 - 같은 클라이언트가 재접속할 때 핸드셰이크 생략
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Let's Encrypt로 인증서를 발급받으면 certbot이 Nginx 설정까지 자동으로 잡아준다:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

## SPA(React, Vue 등) 서빙

SPA는 클라이언트 사이드 라우팅을 쓰기 때문에 `/about`, `/users/123` 같은 경로로 직접 접근하면 Nginx가 파일을 못 찾는다. 모든 경로를 `index.html`로 보내야 한다.

```nginx
server {
    listen 80;
    server_name app.example.com;
    root /var/www/app/dist;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 요청은 백엔드로 프록시
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

`try_files $uri $uri/ /index.html`에서 마지막 `/index.html`이 핵심이다. 파일도 디렉토리도 없으면 `index.html`을 반환해서 SPA 라우터가 처리하게 한다.

## gzip 압축

```nginx
http {
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml text/javascript;
    gzip_min_length 1000;   # 1KB 미만은 압축 안 함 (오히려 느려질 수 있다)
    gzip_comp_level 6;      # 1~9, 6이면 압축률과 CPU 사이 적당한 지점
    gzip_vary on;            # Vary: Accept-Encoding 헤더 추가
}
```

이미지(png, jpg)나 이미 압축된 파일(woff2)은 `gzip_types`에 넣지 않는다. 압축 효과가 거의 없고 CPU만 쓴다.

## 자주 쓰는 보안 헤더

```nginx
server {
    # 클릭재킹 방지
    add_header X-Frame-Options "SAMEORIGIN" always;

    # MIME 타입 스니핑 방지
    add_header X-Content-Type-Options "nosniff" always;

    # 서버 버전 정보 숨기기
    server_tokens off;

    # Nginx 기본 에러 페이지에서 버전이 노출되는 걸 막는다
    # 응답 헤더의 "Server: nginx/1.x.x" → "Server: nginx"
}
```

`server_tokens off`는 반드시 설정한다. 버전 정보가 노출되면 해당 버전의 알려진 취약점을 이용한 공격 대상이 된다.

## 트러블슈팅

### 로그 확인

문제가 생기면 로그부터 본다:

```bash
# 에러 로그
tail -f /var/log/nginx/error.log

# 접근 로그
tail -f /var/log/nginx/access.log

# 특정 도메인 로그 (설정에서 분리한 경우)
tail -f /var/log/nginx/api.example.com.access.log
```

### 자주 만나는 문제

**502 Bad Gateway**: 백엔드가 안 떠있거나 연결이 안 된다. `proxy_pass` 주소와 포트를 확인하고, 백엔드 프로세스가 실행 중인지 본다.

```bash
# 백엔드가 떠있는지 확인
curl -I http://127.0.0.1:8080

# 포트가 열려있는지 확인
ss -tlnp | grep 8080
```

**403 Forbidden**: 파일 권한 문제가 대부분이다. Nginx worker 프로세스 사용자가 해당 디렉토리를 읽을 수 있는지 확인한다.

```bash
# Nginx worker 사용자 확인
grep "^user" /etc/nginx/nginx.conf

# 파일 권한 확인
ls -la /var/www/my-site/
namei -l /var/www/my-site/index.html  # 경로의 모든 디렉토리 권한을 보여준다
```

**413 Request Entity Too Large**: 파일 업로드 크기 제한에 걸린 것이다.

```nginx
client_max_body_size 50m;  # 기본값 1m, 필요한 만큼 올린다
```

**upstream timed out**: 백엔드 응답이 너무 느리다. 타임아웃 값을 조정하거나 백엔드 성능을 개선한다.

```nginx
location / {
    proxy_pass http://backend;
    proxy_connect_timeout 10s;   # 백엔드 연결 타임아웃 (기본 60s)
    proxy_read_timeout 60s;      # 백엔드 응답 대기 타임아웃 (기본 60s)
    proxy_send_timeout 60s;      # 백엔드로 요청 전송 타임아웃 (기본 60s)
}
```

## Apache와 비교

|  | Nginx | Apache |
|---|---|---|
| 동작 방식 | 이벤트 기반 비동기 | 프로세스/스레드 기반 |
| 메모리 사용 | 적다 | 연결 수에 비례해서 늘어난다 |
| 정적 파일 | 빠르다 | 상대적으로 느리다 |
| 동적 처리 | 직접 못 한다 (FastCGI, 프록시로 넘긴다) | mod_php 등으로 직접 처리 가능 |
| 설정 방식 | 중앙 집중 (nginx.conf) | 분산 가능 (.htaccess) |
| 설정 반영 | reload 필요 | .htaccess는 즉시 반영 |

Apache의 `.htaccess`는 디렉토리별로 설정을 덮어쓸 수 있어서 공유 호스팅에서 편하다. 대신 요청마다 `.htaccess` 파일을 읽어서 성능이 떨어진다. Nginx는 `.htaccess`를 지원하지 않고 설정 파일을 직접 수정해야 한다.

## 참조

- Nginx 공식 문서: https://nginx.org/en/docs/
- Nginx 설정 디렉티브 목록: https://nginx.org/en/docs/dirindex.html
- C10K 문제: https://en.wikipedia.org/wiki/C10k_problem
