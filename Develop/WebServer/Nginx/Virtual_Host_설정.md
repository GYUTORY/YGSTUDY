---
title: Virtual Host 설정
tags: [nginx, virtual-host, server-block, multi-domain, server-name]
updated: 2026-07-26
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

## default_server 동작 원리

`default_server`를 지정하지 않으면 해당 포트에서 **설정 파일 로드 순서상 첫 번째** server 블록이 default가 된다. 이 동작이 예상치 못한 트래픽 처리 문제를 만든다.

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

### 테넌트 구분 시 주의할 것들

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

**와일드카드 인증서 범위**: `*.example.com` 인증서는 한 단계 서브도메인만 커버한다. `tenant.api.example.com` 같은 중첩 서브도메인은 별도 인증서가 필요하다.

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

# 설정 리로드 (무중단)
nginx -s reload
# 또는
systemctl reload nginx
```

`nginx -t`는 설정 파일 문법만 검사한다. upstream 서버가 실제로 살아있는지는 확인하지 않는다. 문법 검사를 통과해도 런타임 오류가 날 수 있다.

`reload`는 기존 커넥션을 유지한 채 새 설정을 적용한다. 기존 worker 프로세스는 처리 중인 요청을 마치고 종료된다. 다운타임 없이 설정을 바꿀 수 있어서 운영 환경에서는 `restart` 대신 `reload`를 쓴다.
