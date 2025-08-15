---
title: Nginx 완벽 가이드
tags: [webserver, nginx, definition, web-server, reverse-proxy, load-balancer]
updated: 2025-08-10
---

# Nginx 완벽 가이드

## 배경

Nginx는 고성능 웹 서버, 리버스 프록시, 로드 밸런서로 널리 사용되는 오픈소스 소프트웨어입니다. 2004년에 Igor Sysoev가 개발했으며, 현재는 전 세계 웹사이트의 약 30% 이상에서 사용되고 있습니다.

### Nginx의 필요성
- **고성능**: 이벤트 기반 비동기 처리로 높은 동시 접속 처리
- **리소스 효율성**: 낮은 메모리 사용량과 CPU 사용률
- **확장성**: 마이크로서비스 아키텍처에 적합한 구조
- **다양한 기능**: 웹 서버, 프록시, 로드 밸런서, 캐시 등

### 기본 개념
- **웹 서버**: HTTP 요청을 처리하고 정적/동적 콘텐츠를 제공
- **리버스 프록시**: 클라이언트 요청을 백엔드 서버로 전달
- **로드 밸런서**: 여러 서버에 트래픽을 분산
- **이벤트 기반**: 비동기 I/O를 통한 효율적인 처리

## 핵심

### 1. Nginx의 주요 특징

#### 고성능 아키텍처
```nginx
# 이벤트 기반 비동기 처리
events {
    worker_connections 1024;  # 워커당 최대 연결 수
    use epoll;               # Linux에서 효율적인 이벤트 처리
    multi_accept on;         # 여러 연결 동시 수락
}
```

#### 모듈화된 구조
```nginx
# 핵심 모듈들
- ngx_core_module: 기본 기능
- ngx_http_module: HTTP 서버 기능
- ngx_stream_module: TCP/UDP 프록시
- ngx_mail_module: 메일 프록시
- ngx_upstream_module: 로드 밸런싱
```

#### 설정 파일 구조
```nginx
# nginx.conf 기본 구조
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # 로그 형식 정의
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    # 서버 블록들
    server {
        listen 80;
        server_name example.com;
        
        location / {
            root /var/www/html;
            index index.html index.htm;
        }
    }
}
```

### 2. 웹 서버 vs 리버스 프록시

#### 웹 서버 모드
```nginx
# 정적 파일 서빙
server {
    listen 80;
    server_name example.com;
    
    root /var/www/html;
    index index.html;
    
    # 정적 파일 캐싱
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # gzip 압축
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
```

#### 리버스 프록시 모드
```nginx
# 백엔드 서버로 요청 전달
upstream backend {
    server 127.0.0.1:3000;
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}

server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 정적 콘텐츠 vs 동적 콘텐츠

#### 정적 콘텐츠 처리
```nginx
# 정적 파일 서빙 최적화
server {
    listen 80;
    server_name static.example.com;
    
    root /var/www/static;
    
    # 캐시 설정
    location ~* \.(css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary Accept-Encoding;
    }
    
    location ~* \.(png|jpg|jpeg|gif|ico|svg)$ {
        expires 1M;
        add_header Cache-Control "public";
    }
    
    # gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;
}
```

#### 동적 콘텐츠 처리
```nginx
# PHP 애플리케이션 처리
server {
    listen 80;
    server_name dynamic.example.com;
    
    root /var/www/dynamic;
    index index.php;
    
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
    
    # 캐시 비활성화
    location / {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
}
```

## 예시

### 1. 실제 사용 사례

#### 단일 페이지 애플리케이션 (SPA)
```nginx
# React/Vue/Angular SPA 설정
server {
    listen 80;
    server_name spa.example.com;
    
    root /var/www/spa;
    index index.html;
    
    # 모든 라우트를 index.html로 전달 (클라이언트 라우팅)
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 요청은 백엔드로 전달
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # 정적 자산 캐싱
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 마이크로서비스 아키텍처
```nginx
# 여러 서비스로 요청 분산
upstream user_service {
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}

upstream product_service {
    server 127.0.0.1:3003;
    server 127.0.0.1:3004;
}

upstream order_service {
    server 127.0.0.1:3005;
    server 127.0.0.1:3006;
}

server {
    listen 80;
    server_name api.example.com;
    
    # 사용자 서비스
    location /api/users/ {
        proxy_pass http://user_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 상품 서비스
    location /api/products/ {
        proxy_pass http://product_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 주문 서비스
    location /api/orders/ {
        proxy_pass http://order_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 고급 패턴

#### 로드 밸런싱 전략
```nginx
# 다양한 로드 밸런싱 방법
upstream backend {
    # 라운드 로빈 (기본값)
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
    
    # 가중치 기반
    server 127.0.0.1:3003 weight=3;
    server 127.0.0.1:3004 weight=1;
    
    # 최소 연결 수 기반
    server 127.0.0.1:3005;
    server 127.0.0.1:3006;
    
    # IP 해시 기반 (세션 유지)
    ip_hash;
    server 127.0.0.1:3007;
    server 127.0.0.1:3008;
    
    # 헬스 체크
    server 127.0.0.1:3009 max_fails=3 fail_timeout=30s;
}
```

#### 캐싱 전략
```nginx
# 프록시 캐싱
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=10g inactive=60m use_temp_path=off;

server {
    listen 80;
    server_name cache.example.com;
    
    location / {
        proxy_cache my_cache;
        proxy_cache_use_stale error timeout http_500 http_502 http_503 http_504;
        proxy_cache_valid 200 1h;
        proxy_cache_valid 404 1m;
        
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
    
    # 캐시 무효화
    location ~ /purge(/.*) {
        allow 127.0.0.1;
        deny all;
        proxy_cache_purge my_cache "$scheme$request_method$host$1";
    }
}
```

## 운영 팁

### 성능 최적화

#### 워커 프로세스 설정
```nginx
# CPU 코어 수에 맞춘 워커 프로세스
worker_processes auto;

# 워커당 연결 수 최적화
events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

# 버퍼 크기 최적화
http {
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
}
```

#### gzip 압축 설정
```nginx
# gzip 압축 최적화
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/json
    application/javascript
    application/xml+rss
    application/atom+xml
    image/svg+xml;
```

### 보안 설정

#### 기본 보안 헤더
```nginx
# 보안 헤더 추가
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

#### 접근 제어
```nginx
# IP 기반 접근 제어
location /admin/ {
    allow 192.168.1.0/24;
    allow 10.0.0.0/8;
    deny all;
}

# 기본 인증
location /private/ {
    auth_basic "Restricted Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

### 모니터링

#### 로그 설정
```nginx
# 상세한 로그 형식
log_format detailed '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

access_log /var/log/nginx/access.log detailed;
error_log /var/log/nginx/error.log warn;
```

## 참고

### Nginx vs Apache 비교

| 측면 | Nginx | Apache |
|------|-------|--------|
| **아키텍처** | 이벤트 기반 | 프로세스/스레드 기반 |
| **메모리 사용량** | 낮음 | 높음 |
| **동시 연결 처리** | 우수 | 제한적 |
| **정적 파일 처리** | 매우 빠름 | 빠름 |
| **동적 콘텐츠** | 외부 프로세스 필요 | 내장 모듈 |
| **설정 복잡도** | 중간 | 높음 |
| **모듈 생태계** | 제한적 | 풍부 |

### Nginx 사용 권장사항

| 사용 사례 | 권장도 | 이유 |
|----------|--------|------|
| **정적 파일 서빙** | ⭐⭐⭐⭐⭐ | 매우 빠른 성능 |
| **리버스 프록시** | ⭐⭐⭐⭐⭐ | 효율적인 로드 밸런싱 |
| **API 게이트웨이** | ⭐⭐⭐⭐⭐ | 라우팅과 캐싱 |
| **웹 애플리케이션** | ⭐⭐⭐⭐ | 설정이 간단 |
| **마이크로서비스** | ⭐⭐⭐⭐⭐ | 서비스 디스커버리 |
| **레거시 시스템** | ⭐⭐⭐ | 마이그레이션 필요 |

### 결론
Nginx는 고성능 웹 서버이자 강력한 리버스 프록시로, 현대적인 웹 아키텍처의 핵심 구성 요소입니다.
이벤트 기반 비동기 처리로 높은 동시 접속을 효율적으로 처리할 수 있습니다.
정적 콘텐츠 캐싱과 gzip 압축을 통해 성능을 최적화하세요.
보안 헤더와 접근 제어를 통해 안전한 웹 서비스를 제공하세요.
