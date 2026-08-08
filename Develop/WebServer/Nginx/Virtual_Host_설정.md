---
title: Virtual Host 설정
tags: [web-server, docker]
updated: 2026-07-27
---

# Virtual Host 설정

## 개념

Nginx의 가상 호스트는 `server` 블록 단위로 구성한다. 하나의 Nginx 프로세스가 여러 도메인을 처리하는 방식이다. 클라이언트 요청이 들어오면 Nginx는 `listen` 포트와 `server_name`을 조합해서 어떤 server 블록으로 라우팅할지 결정한다.

Apache에서 `VirtualHost` 지시자로 하던 일과 동일하지만, 설정 구조가 다르다. Nginx는 `sites-available`에 파일을 만들고 `sites-enabled`에 심링크를 거는 패턴을 많이 쓴다.

## 기본 Server 블록 구조

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    root /var/www/example;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

여러 도메인을 한 서버로 보낼 때는 `server_name`에 공백으로 구분해서 나열한다. `www.example.com`을 따로 처리하고 싶으면 별도 server 블록에서 `return 301`로 리다이렉트하는 게 낫다.

## listen 지시어 심화

기본 `listen 80;` 하나로 쓰는 경우가 많은데, listen 지시어에는 운영 환경에서 알아야 하는 옵션이 더 있다.

### IPv6 바인딩

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name example.com;
}
```

`[::]:80`은 IPv6 와일드카드 주소다. IPv4와 IPv6를 동시에 받으려면 두 줄 다 써야 한다. 일부 OS에서는 `IPV6_V6ONLY` 소켓 옵션 기본값이 달라서, `listen [::]:80`만 써도 IPv4 트래픽도 받는 경우가 있다. 동작이 OS마다 다르기 때문에 명시적으로 두 줄을 쓰는 게 안전하다.

`nginx.conf`의 `http` 블록에서 `ipv6only=off`를 쓰는 방법도 있지만, dual-stack 동작이 예상과 다르게 풀리는 경우가 있어서 권장하지 않는다.

### UNIX 도메인 소켓

```nginx
upstream backend {
    server unix:/var/run/myapp/backend.sock;
}

server {
    listen unix:/var/run/nginx/frontend.sock;
    server_name _;

    location / {
        proxy_pass http://backend;
    }
}
```

같은 호스트에서 Nginx와 애플리케이션 서버 사이 통신에 UNIX 소켓을 쓰면 TCP 오버헤드가 없다. PHP-FPM, Gunicorn, Unicorn 연동에서 자주 쓴다. 소켓 파일 권한이 맞지 않으면 `connect() to unix:/var/run/... failed (13: Permission denied)` 오류가 난다.

### backlog

```nginx
listen 80 backlog=2048;
```

커널의 accept 큐 크기를 지정한다. 기본값은 511이다. 트래픽 스파이크 때 큐가 꽉 차면 새 연결이 드롭된다. `ss -tlnp`로 실제 backlog 크기를 확인하고, `/proc/sys/net/core/somaxconn` 값도 같이 올려야 효과가 있다. Nginx 설정만 올리고 커널 파라미터를 안 올리면 커널 제한에 걸린다.

```bash
# 커널 파라미터도 같이 올린다
sysctl -w net.core.somaxconn=4096
sysctl -w net.ipv4.tcp_max_syn_backlog=4096
```

### reuseport

```nginx
listen 80 reuseport;
listen 443 ssl reuseport;
```

`SO_REUSEPORT` 소켓 옵션을 활성화한다. worker 프로세스마다 별도의 소켓을 바인딩해서 커널이 직접 accept 큐를 분산한다. 기본 동작에서는 master 프로세스가 소켓을 열고 worker가 accept를 경쟁하는데, `reuseport`를 쓰면 이 경쟁이 줄어든다. 멀티코어 서버에서 `worker_processes auto;`와 함께 쓸 때 처리량 차이가 난다.

단, `reuseport`를 켜면 reload 시 잠깐의 패킷 드롭이 발생할 수 있다. 새 worker와 구 worker가 각자 별도 소켓을 들고 있는 시점에 연결이 분산되는 과도기가 생긴다.

## default_server 동작 원리

`default_server`를 지정하지 않으면 해당 포트에서 설정 파일 로드 순서상 첫 번째 server 블록이 default가 된다. 이 동작이 예상치 못한 트래픽 처리 문제를 만든다.

```nginx
# 매칭 실패 시 이 블록이 받는다
server {
    listen 80 default_server;
    server_name _;

    return 444;  # 연결 즉시 끊기 (HTTP 응답 없음)
}
```

`server_name _`은 어떤 값과도 매칭되지 않는 특수 값이다. default_server와 함께 쓰면 "아무 도메인과도 매칭되지 않는 요청을 이 블록에서 처리"하는 패턴이 된다.

운영 환경에서는 `return 444`보다 `return 400` 또는 정적 에러 페이지를 쓰는 경우도 있다. AWS ALB 같은 로드 밸런서 앞에 Nginx가 있으면 헬스체크 요청이 `Host` 헤더 없이 들어오는 경우가 있어서 444로 끊으면 헬스체크 실패로 이어질 수 있다.

### 매칭 우선순위

1. `listen` 포트 매칭
2. `server_name` 매칭 (아래 순서로 탐색)
   - 정확한 문자열 일치
   - `*`로 시작하는 와일드카드 (`*.example.com`)
   - `*`로 끝나는 와일드카드 (`mail.*`)
   - 정규식 (`~^www\d+\.example\.com$`)
3. 위 전부 실패 → `default_server`

## server_name 매칭 방법

### 정확한 이름

```nginx
server_name example.com www.example.com api.example.com;
```

가장 우선순위가 높다. 여러 개를 공백으로 나열한다.

### 와일드카드

와일드카드는 `*`가 맨 앞이나 맨 뒤에만 올 수 있다. 중간에는 쓸 수 없다.

```nginx
# 서브도메인 전체 처리
server_name *.example.com;

# TLD 무관하게 처리
server_name example.*;
```

`*.example.com`은 `www.example.com`은 매칭되지만 `example.com` 자체는 매칭하지 않는다. 루트 도메인과 와일드카드 서브도메인을 함께 처리하려면 둘 다 써야 한다.

```nginx
server_name example.com *.example.com;
```

### 정규식

`~`로 시작하면 정규식으로 인식한다.

```nginx
server_name ~^(www\.)?example\.com$;
```

정규식에서 캡처 그룹을 쓰면 `$1`, `$2`로 참조할 수 있다. 멀티 테넌트 구성에서 많이 쓴다.

```nginx
server_name ~^(?<tenant>[a-z0-9-]+)\.example\.com$;

location / {
    proxy_pass http://$tenant-backend;
}
```

정규식 매칭은 문자열 매칭보다 느리다. 서브도메인 수가 수백 개를 넘어가면 성능 차이가 날 수 있다.

## add_header 상속 규칙 함정

Nginx의 `add_header` 지시어는 상속 방식이 직관적이지 않다. server 블록에 헤더를 선언하고 location 블록에서 헤더를 하나 추가하면, server 블록의 헤더가 전부 사라진다.

```nginx
server {
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";

    location / {
        try_files $uri $uri/ =404;
    }

    location /api {
        # 이 location에 add_header를 추가하는 순간
        # 위의 X-Frame-Options, X-Content-Type-Options 둘 다 응답에서 사라진다
        add_header Cache-Control "no-store";
        proxy_pass http://backend;
    }
}
```

Nginx는 `add_header`를 상속이 아닌 재정의로 처리한다. 현재 블록에 `add_header`가 하나라도 있으면 상위 블록의 `add_header`를 전부 무시한다. 보안 헤더를 server 블록에 모아두고 특정 location에 Cache-Control 하나 추가했다가 보안 헤더가 통째로 빠지는 상황이 생긴다.

해결 방법은 두 가지다.

**방법 1: location 블록마다 헤더 전부 반복**

```nginx
server {
    location / {
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        try_files $uri $uri/ =404;
    }

    location /api {
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header Cache-Control "no-store";
        proxy_pass http://backend;
    }
}
```

반복이 많아서 유지보수가 불편하다.

**방법 2: headers_more 모듈 또는 include 파일**

```nginx
# /etc/nginx/snippets/security-headers.conf
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

```nginx
server {
    location / {
        include snippets/security-headers.conf;
        try_files $uri $uri/ =404;
    }

    location /api {
        include snippets/security-headers.conf;
        add_header Cache-Control "no-store";
        proxy_pass http://backend;
    }
}
```

include로 묶으면 수정할 곳이 한 파일로 줄어든다. `headers_more_set_header` 모듈을 쓸 수 있으면 이 상속 문제 자체가 없어지지만, 외부 모듈이라 패키지 설치가 따로 필요하다.

`add_header`에 `always` 옵션을 붙이면 4xx/5xx 응답에도 헤더가 붙는다. 없으면 200, 201, 204, 206, 301, 302, 303, 304, 307, 308에만 붙는다.

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
```

## server 블록 매칭 트러블슈팅

### nginx -T로 전체 설정 덤프

`nginx -t`는 문법만 검사하지만, `nginx -T`는 전체 설정을 stdout으로 출력한다. 파일 분산 구조에서 어떤 설정이 실제로 로드되는지 한눈에 볼 수 있다.

```bash
nginx -T 2>/dev/null | grep -A 5 "server_name"
```

include로 분산된 설정을 하나로 합쳐서 보여주기 때문에, 중복 server_name이나 의도치 않은 블록이 끼어든 경우를 찾기 쉽다.

### 설정 파일 로드 순서 충돌

`include /etc/nginx/conf.d/*.conf;`로 여러 파일을 불러올 때, 파일 이름 알파벳 순서로 로드된다. `default_server`를 명시하지 않으면 알파벳 첫 번째 파일의 첫 번째 server 블록이 default가 된다.

```
conf.d/
  a-admin.conf      # 이 파일이 가장 먼저 로드된다
  b-api.conf
  z-example.conf
```

`a-admin.conf`의 server 블록이 80 포트의 default_server가 되어버린다. 나중에 파일을 추가했는데 예상과 다른 블록이 기본으로 동작하는 현상이 이 로드 순서 문제다.

`default_server`를 명시적으로 지정하는 것이 안전하다.

```nginx
# 00-default.conf 처럼 알파벳 앞에 오도록 이름 짓거나
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 444;
}
```

### 예상 외 블록 매칭 디버깅

어떤 요청이 어느 server 블록으로 들어가는지 확인할 때 `debug_connection`을 쓴다.

```nginx
events {
    debug_connection 203.0.113.10;  # 디버그할 클라이언트 IP
}
```

Nginx 디버그 빌드가 필요하다. 패키지 설치 시 `nginx-debug` 패키지가 따로 있는 경우가 많다.

빠르게 확인하려면 로그 포맷에 `$server_name`을 추가한다.

```nginx
log_format debug_vhost '$remote_addr - $server_name [$time_local] '
                       '"$request" $status $body_bytes_sent';

access_log /var/log/nginx/debug_access.log debug_vhost;
```

요청 로그를 보면 어떤 server_name으로 매칭됐는지 바로 알 수 있다.

### 같은 server_name 중복 선언

두 server 블록이 같은 `server_name`과 `listen`을 가지면, 설정 파일 로드 순서에서 먼저 나오는 블록이 우선한다. Nginx는 경고 없이 둘 다 로드하고 첫 번째 것을 쓴다.

```bash
# 중복 server_name 찾기
nginx -T 2>/dev/null | grep "server_name" | sort | uniq -d
```

## IP 기반 vs 이름 기반 가상 호스팅

### IP 기반

```nginx
server {
    listen 192.168.1.10:80;
    server_name example.com;
}

server {
    listen 192.168.1.20:80;
    server_name other.com;
}
```

서버에 IP가 여러 개 할당되어 있을 때 IP로 구분하는 방식이다. 요즘은 거의 쓰지 않는다. IP 하나에 여러 도메인을 올리는 이름 기반 방식이 일반적이다.

SSL 초창기에는 IP 기반이 필요했다. SNI가 없으면 TLS handshake 시점에 어떤 인증서를 써야 할지 알 수 없어서 도메인마다 IP가 따로 있어야 했다. 지금은 SNI가 보편화되어서 이 제약이 없다.

### 이름 기반

```nginx
server {
    listen 80;
    server_name example.com;
}

server {
    listen 80;
    server_name other.com;
}
```

같은 IP, 같은 포트에서 `Host` 헤더로 구분한다. 현재 대부분의 가상 호스팅이 이 방식이다.

## 다중 도메인 구성 패턴

### sites-available / sites-enabled 패턴

```bash
# 각 도메인별 파일 생성
/etc/nginx/sites-available/example.com
/etc/nginx/sites-available/other.com

# 활성화할 것만 심링크
ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/
```

`nginx.conf`에서 `include /etc/nginx/sites-enabled/*;`로 불러온다. Ubuntu 패키지 설치 시 기본으로 이 구조다.

### conf.d 패턴

```bash
/etc/nginx/conf.d/example.com.conf
/etc/nginx/conf.d/other.com.conf
```

`nginx.conf`에서 `include /etc/nginx/conf.d/*.conf;`로 불러온다. 파일 삭제로 비활성화한다. 컨테이너 환경에서 많이 쓰는 패턴이다.

### 실제 다중 도메인 설정 예시

```nginx
# /etc/nginx/sites-available/example.com
server {
    listen 80;
    server_name example.com www.example.com;

    # www → non-www 리다이렉트
    if ($host = www.example.com) {
        return 301 https://example.com$request_uri;
    }

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    root /var/www/example;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## 컨테이너/Docker 환경에서의 Virtual Host

컨테이너에서 Nginx를 운영하면 설정 관리 방식이 달라진다. 이미지 빌드 시점에 설정을 굽거나, 런타임에 환경변수로 설정을 주입하는 두 가지 방식을 주로 쓴다.

### conf.d 동적 마운트

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
```

호스트의 `conf.d` 디렉토리를 마운트하면 컨테이너 재시작 없이 파일을 추가하거나 삭제할 수 있다. 설정을 변경한 뒤에는 컨테이너 내부에서 reload를 해야 한다.

```bash
docker exec nginx-container nginx -s reload
```

reload 전에 문법 검사를 먼저 하는 게 낫다.

```bash
docker exec nginx-container nginx -t && docker exec nginx-container nginx -s reload
```

### envsubst 템플릿

환경별로 도메인이나 upstream 주소가 다를 때 envsubst로 템플릿을 렌더링한다.

```nginx
# /etc/nginx/templates/default.conf.template
server {
    listen 80;
    server_name ${NGINX_HOST};

    location / {
        proxy_pass http://${BACKEND_HOST}:${BACKEND_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

nginx 공식 이미지는 `/etc/nginx/templates/` 디렉토리의 `*.template` 파일을 컨테이너 시작 시 자동으로 envsubst 처리해서 `/etc/nginx/conf.d/`에 놓는다.

```bash
docker run -e NGINX_HOST=example.com \
           -e BACKEND_HOST=app \
           -e BACKEND_PORT=8080 \
           nginx:alpine
```

직접 envsubst를 쓸 때는 Nginx 변수와 쉘 변수가 충돌하지 않게 주의해야 한다. Nginx 변수 `$host`, `$remote_addr` 같은 것들이 envsubst에 의해 빈 문자열로 치환되는 문제가 생긴다.

```bash
# 치환할 변수를 명시적으로 지정해서 Nginx 변수를 보호한다
envsubst '${NGINX_HOST} ${BACKEND_HOST} ${BACKEND_PORT}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf
```

### 멀티 스테이지 빌드로 설정 굽기

```dockerfile
FROM nginx:alpine

COPY nginx/conf.d/ /etc/nginx/conf.d/
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# 문법 검사를 빌드 시점에 확인
RUN nginx -t
```

빌드 시 `nginx -t`를 실행하면 설정 오류를 이미지 빌드 단계에서 잡을 수 있다. 잘못된 설정이 프로덕션에 배포되는 것을 막는다.

### Docker 환경에서 흔한 문제

**DNS resolver 설정**: 컨테이너 네트워크에서 upstream에 서비스 이름을 쓸 때 resolver를 설정해야 한다.

```nginx
http {
    resolver 127.0.0.11 valid=10s;  # Docker 내부 DNS

    server {
        location / {
            set $backend "app-service";
            proxy_pass http://$backend:8080;
        }
    }
}
```

`resolver`가 없으면 Nginx 시작 시점에 `app-service`를 resolve하려 하고, 해당 서비스가 아직 안 떠 있으면 시작 자체가 실패한다. 변수에 담아서 `proxy_pass`에 쓰면 런타임에 resolve하므로 이 문제를 피할 수 있다.

**default.conf 덮어쓰기**: nginx 공식 이미지는 `/etc/nginx/conf.d/default.conf`가 기본으로 들어있다. 커스텀 설정 파일을 마운트할 때 이 파일과 충돌하는 경우가 있다.

```bash
# default.conf가 있는지 확인
docker exec nginx-container ls /etc/nginx/conf.d/

# 필요하면 삭제
docker exec nginx-container rm /etc/nginx/conf.d/default.conf
```

Dockerfile에서 아예 삭제해두는 게 깔끔하다.

```dockerfile
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY conf.d/ /etc/nginx/conf.d/
```

## 멀티 테넌트 구성 시 주의사항

SaaS 서비스에서 `tenant.example.com` 패턴으로 테넌트를 구분할 때의 설정이다.

```nginx
server {
    listen 443 ssl;
    server_name ~^(?<tenant>[a-z0-9-]+)\.example\.com$;

    ssl_certificate /etc/nginx/ssl/wildcard.example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/wildcard.example.com.key;

    location / {
        proxy_pass http://backend;
        proxy_set_header X-Tenant $tenant;
        proxy_set_header Host $host;
    }
}
```

**캡처 그룹 이름 충돌**: 여러 server 블록에서 같은 이름의 캡처 그룹을 쓰면 예상치 못한 동작이 생길 수 있다. 각 블록에서 고유한 변수명을 쓴다.

**예약된 서브도메인 처리**: `www`, `api`, `admin` 같은 서브도메인을 테넌트 이름으로 쓰지 못하게 해야 한다. Nginx 레벨에서 막으려면 이 서브도메인들을 와일드카드보다 앞에 배치한다.

```nginx
# 이 블록이 먼저 매칭된다 (정확한 이름 > 정규식)
server {
    listen 443 ssl;
    server_name api.example.com admin.example.com;
    # ...
}

# 나머지 서브도메인은 여기로
server {
    listen 443 ssl;
    server_name ~^(?<tenant>[a-z0-9-]+)\.example\.com$;
    # ...
}
```

**upstream 동적 라우팅**: 테넌트마다 별도 백엔드 서버로 라우팅하려면 `map`이나 `lua` 모듈을 써야 한다. 단순 변수 치환으로 `proxy_pass http://$tenant-backend`처럼 쓸 수 있지만, `$tenant-backend`가 실제로 resolver에 의해 resolving되어야 한다. DNS resolver 설정이 없으면 Nginx 시작 시점에 오류가 난다.

```nginx
http {
    resolver 127.0.0.1 valid=30s;

    server {
        listen 443 ssl;
        server_name ~^(?<tenant>[a-z0-9-]+)\.example\.com$;

        set $backend "${tenant}-service.internal";

        location / {
            proxy_pass http://$backend;
        }
    }
}
```

`resolver` 없이 변수를 `proxy_pass`에 쓰면 "no resolver defined" 오류가 난다. 컨테이너 환경이면 `127.0.0.11`이 Docker DNS다.

## 설정 검증과 리로드

```bash
# 문법 검사
nginx -t

# 전체 설정 덤프 (include 파일 포함)
nginx -T

# 설정 리로드 (무중단)
nginx -s reload
# 또는
systemctl reload nginx
```

`nginx -t`는 설정 파일 문법만 검사한다. upstream 서버가 실제로 살아있는지는 확인하지 않는다. 문법 검사를 통과해도 런타임 오류가 날 수 있다.

`reload`는 기존 커넥션을 유지한 채 새 설정을 적용한다. 기존 worker 프로세스는 처리 중인 요청을 마치고 종료된다. 다운타임 없이 설정을 바꿀 수 있어서 운영 환경에서는 `restart` 대신 `reload`를 쓴다.
