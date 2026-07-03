---
title: "Nginx location 매칭과 설정 구조"
tags: [nginx, location, configuration, web-server]
updated: 2026-03-25
---

# Nginx location 매칭과 설정 구조

## location 블록이란

Nginx가 요청 URI를 보고 어떤 설정을 적용할지 결정하는 단위다. `server` 블록 안에 여러 개의 `location` 블록을 두고, 요청이 들어오면 매칭 규칙에 따라 하나를 선택한다.

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        # 기본 매칭
    }

    location /api/ {
        # /api/로 시작하는 요청
    }

    location = /health {
        # 정확히 /health인 요청만
    }
}
```

## 매칭 우선순위

이 순서를 모르면 의도와 다른 location이 선택되는 상황이 반복된다.

### 1순위: exact match (`=`)

URI가 정확히 일치해야 한다. 일치하면 즉시 선택하고 다른 location은 검사하지 않는다.

```nginx
location = /login {
    proxy_pass http://auth_backend;
}
```

`/login`은 매칭되지만 `/login/oauth`는 매칭되지 않는다.

### 2순위: preferential prefix (`^~`)

URI 앞부분이 일치하면 regex 검사를 건너뛰고 바로 이 location을 사용한다. 정적 파일 경로처럼 regex가 끼어들면 안 되는 곳에 쓴다.

```nginx
location ^~ /static/ {
    root /var/www;
}
```

`/static/js/app.js` 요청이 들어오면 아래에 `~ \.js$` 같은 regex location이 있어도 무시하고 이 블록을 쓴다.

### 3순위: regex (`~`, `~*`)

`~`는 대소문자 구분, `~*`는 대소문자 무시. 설정 파일에 나온 순서대로 검사하고, 처음 매칭되는 것을 사용한다.

```nginx
# 대소문자 구분
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php-fpm.sock;
}

# 대소문자 무시 - .jpg, .JPG 모두 매칭
location ~* \.(jpg|png|gif|ico)$ {
    expires 30d;
}
```

regex location은 선언 순서가 곧 우선순위다. 의도와 다르게 동작하면 순서부터 확인해야 한다.

### 4순위: prefix (접두사 매칭)

아무 수식어 없이 쓰는 일반 prefix 매칭이다. 여러 개가 매칭되면 가장 긴 것을 선택한다.

```nginx
location / {
    # 모든 요청의 fallback
}

location /api/ {
    # /api/users, /api/posts 등
}

location /api/internal/ {
    # /api/internal/metrics 등 - /api/보다 더 구체적이므로 우선
}
```

### 매칭 과정 정리

실제로 Nginx가 location을 선택하는 흐름은 이렇다:

1. `=` 매칭을 먼저 검사. 일치하면 바로 사용
2. prefix 매칭 중 가장 긴 것을 찾아 기억해둔다
3. 그 기억해둔 prefix가 `^~`이면 바로 사용
4. regex location을 위에서 아래로 검사. 처음 매칭되면 사용
5. regex가 하나도 안 맞으면 2번에서 기억해둔 prefix를 사용

```nginx
# 이 설정에서 /static/style.css 요청이 들어오면?
location /static/ {          # prefix 매칭됨, 기억
    root /var/www;
}

location ~ \.css$ {           # regex 매칭됨 -> 이걸 사용!
    add_header X-Type css;
}
```

`/static/style.css`는 prefix `/static/`에 매칭되지만, regex `\.css$`에도 매칭된다. regex가 우선이므로 두 번째 블록이 선택된다. 이게 의도한 게 아니라면 `^~`를 써야 한다.

## 자주 겪는 실수

### trailing slash 문제

```nginx
# /api로 요청하면 매칭되지만 /api/users는 매칭 안 됨
location = /api {
    # ...
}

# /api, /api/, /api/users 모두 매칭됨
location /api {
    # ...
}

# /api/는 매칭되지만 /api는 매칭 안 됨
location /api/ {
    # ...
}
```

`proxy_pass`에서도 trailing slash가 중요하다:

```nginx
# /api/users -> backend에 /api/users로 전달
location /api/ {
    proxy_pass http://backend;
}

# /api/users -> backend에 /users로 전달 (경로 재작성)
location /api/ {
    proxy_pass http://backend/;
}
```

`proxy_pass`에 URI(`/`)를 붙이면 location에서 매칭된 부분을 잘라내고 나머지만 전달한다. 이 차이를 모르면 404가 나는 원인을 한참 찾게 된다.

### nested location

location 안에 location을 넣을 수 있지만, 필요한 경우가 거의 없다. 대부분 더 구체적인 location을 같은 레벨에 추가하는 게 낫다.

```nginx
# 이렇게 하지 말고
location /api/ {
    location ~ \.json$ {
        # ...
    }
}

# 이렇게 하는 게 관리하기 쉽다
location /api/ {
    # ...
}

location ~ ^/api/.*\.json$ {
    # ...
}
```

## 설정 파일 구조

### 기본 디렉토리 구조

```
/etc/nginx/
├── nginx.conf              # 메인 설정 (건드릴 일 거의 없음)
├── conf.d/                 # 추가 설정 파일 (*.conf 자동 로드)
├── sites-available/        # 사이트별 설정 파일
├── sites-enabled/          # sites-available의 심볼릭 링크
├── snippets/               # 재사용 가능한 설정 조각
└── mime.types              # MIME 타입 정의
```

### nginx.conf의 기본 구조

```nginx
# 전역 설정
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 로그 포맷
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # conf.d 아래 .conf 파일 전부 로드
    include /etc/nginx/conf.d/*.conf;

    # sites-enabled 아래 설정 로드
    include /etc/nginx/sites-enabled/*;
}
```

`include`는 해당 경로의 파일 내용을 그 자리에 그대로 삽입한다. 와일드카드를 쓸 수 있고, 매칭되는 파일이 없으면 에러 없이 넘어간다.

### sites-available / sites-enabled 패턴

Debian/Ubuntu에서 쓰는 방식이다. CentOS/RHEL은 기본적으로 `conf.d/`만 사용한다.

```bash
# 새 사이트 설정 생성
vi /etc/nginx/sites-available/myapp.conf

# 활성화 (심볼릭 링크 생성)
ln -s /etc/nginx/sites-available/myapp.conf /etc/nginx/sites-enabled/

# 비활성화 (링크만 삭제, 원본은 유지)
rm /etc/nginx/sites-enabled/myapp.conf

# 설정 검증 후 적용
nginx -t && systemctl reload nginx
```

이 패턴의 장점은 설정을 삭제하지 않고 비활성화할 수 있다는 것이다. 장애 상황에서 빠르게 롤백할 때 유용하다.

주의할 점: `sites-enabled/default`가 남아있으면 의도하지 않은 default server가 잡히는 경우가 있다. 새 사이트를 추가할 때 default 파일이 간섭하는지 확인해야 한다.

### conf.d/ 패턴

```bash
# conf.d 안에 .conf 확장자로 파일을 만들면 자동 로드
/etc/nginx/conf.d/
├── default.conf
├── myapp.conf
├── upstream.conf          # upstream 정의만 모아둘 수도 있다
└── ssl-params.conf        # SSL 공통 설정
```

`sites-available/enabled` 패턴보다 단순하다. 비활성화하려면 확장자를 `.conf.disabled` 같은 걸로 바꾸면 된다.

## include와 snippets

### snippets 활용

반복되는 설정 조각을 파일로 분리해서 `include`로 가져온다.

```nginx
# /etc/nginx/snippets/ssl-params.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

```nginx
# /etc/nginx/snippets/proxy-headers.conf
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

```nginx
# 사이트 설정에서 가져다 쓴다
server {
    listen 443 ssl;
    server_name myapp.com;

    ssl_certificate /etc/letsencrypt/live/myapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.com/privkey.pem;
    include snippets/ssl-params.conf;

    location /api/ {
        include snippets/proxy-headers.conf;
        proxy_pass http://api_backend;
    }

    location /admin/ {
        include snippets/proxy-headers.conf;
        proxy_pass http://admin_backend;
    }
}
```

`proxy_set_header`를 매번 복사해서 붙이면 하나를 빠뜨리거나, 나중에 헤더를 추가할 때 일부 location만 업데이트하는 실수가 생긴다. snippet으로 분리하면 한 곳만 고치면 된다.

### 설정 파일 분리 실전 예시

규모가 커지면 하나의 server 블록도 파일을 나눠야 읽을 수 있다.

```nginx
# /etc/nginx/conf.d/myapp.conf
upstream api_backend {
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
}

server {
    listen 443 ssl http2;
    server_name myapp.com;

    ssl_certificate /etc/letsencrypt/live/myapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.com/privkey.pem;
    include snippets/ssl-params.conf;

    # location 블록을 별도 파일로 분리
    include /etc/nginx/locations/myapp/*.conf;
}
```

```nginx
# /etc/nginx/locations/myapp/api.conf
location /api/ {
    include snippets/proxy-headers.conf;
    proxy_pass http://api_backend;
    proxy_read_timeout 30s;
}
```

```nginx
# /etc/nginx/locations/myapp/static.conf
location ^~ /static/ {
    root /var/www/myapp;
    expires 7d;
    add_header Cache-Control "public, immutable";
}
```

## 설정 변경 시 확인 순서

설정을 변경할 때마다 반드시 이 순서로 진행한다.

```bash
# 1. 문법 검사
nginx -t

# 2. 어떤 설정이 적용되는지 확인 (디버그용)
nginx -T | grep -A 5 "location"

# 3. reload (프로세스 재시작 없이 설정만 다시 읽음)
systemctl reload nginx

# 4. 매칭 확인 - 의도한 location이 선택되는지 테스트
curl -I http://localhost/api/test
```

`nginx -T`는 모든 include를 펼쳐서 최종 설정을 보여준다. 여러 파일에 분산된 설정이 어떻게 합쳐지는지 확인할 때 쓴다.

`nginx -t`를 건너뛰고 `reload`하면 문법 에러가 있을 때 Nginx가 이전 설정을 유지한다. 서비스가 죽지는 않지만, 변경이 적용되지 않은 상태에서 "적용했는데 안 바뀌었다"며 시간을 낭비하는 경우가 있다. 항상 `-t`를 먼저 실행하는 습관이 필요하다.
