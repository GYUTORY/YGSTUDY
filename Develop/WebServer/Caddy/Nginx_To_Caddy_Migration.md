---
title: Nginx에서 Caddy로 마이그레이션
tags:
  - WebServer
  - Caddy
  - Nginx
  - Migration
  - ReverseProxy
  - PHP-FPM
updated: 2026-05-03
---

# Nginx에서 Caddy로 마이그레이션

Nginx로 5년 굴려온 설정을 Caddy로 옮기는 작업은 단순한 문법 변환이 아니다. 디렉티브 이름이 다른 건 시작에 불과하고, 두 서버가 같은 입력을 다르게 해석하는 부분이 곳곳에 있다. URL 정규화 규칙, 후행 슬래시 처리, 매처가 대소문자를 보는 방식, proxy 헤더 자동 처리 같은 것들이다. 이 차이를 모르고 그냥 옮기면 옮긴 다음 날부터 운영팀이 이상한 404 리포트를 보내기 시작한다.

이 문서는 실제로 Nginx 설정을 Caddy로 옮길 때 마주치는 변환 패턴과 함정을 정리한다. 한 줄 한 줄 매핑표를 외우는 게 목적이 아니라, 두 서버의 모델 차이를 이해하고 옮긴 후에 깨질 만한 동작을 미리 잡는 게 목적이다.

## 두 서버의 설정 모델 차이

먼저 가장 큰 모델 차이부터 짚는다. Nginx는 `server` 블록 안에 `location` 블록을 중첩하고, 요청이 들어오면 가장 잘 맞는 `location` 하나가 골라진다. 매칭 규칙은 prefix(`location /api/`), 정확히(`=`), 정규식(`~`, `~*`) 등이 섞여 있고 우선순위가 정해져 있다. 같은 URL에 디렉티브가 여러 군데 흩어져 있어도 마지막에 한 location만 적용된다.

Caddy는 다르다. 사이트 블록 안의 디렉티브는 기본적으로 모두 평가되고, 선언 순서가 아니라 디렉티브별로 정의된 우선순위 순으로 실행된다. 매처(`@name`)로 조건을 묶어서 각 디렉티브에 붙이는 식이고, 한 번에 한 핸들러만 골라야 할 때는 `handle` 또는 `route`로 묶는다. Nginx의 `location`처럼 "이 블록 안에서만 디렉티브 적용"을 원하면 `handle`을 써야 한다.

```nginx
server {
    listen 80;
    server_name example.com;

    location /api/ {
        proxy_pass http://backend:8080;
    }

    location /static/ {
        root /var/www;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

이걸 Caddy로 옮기면 이렇게 된다.

```caddy
example.com {
    handle /api/* {
        reverse_proxy backend:8080
    }

    handle /static/* {
        root * /var/www
        file_server
    }

    handle {
        root * /var/www/html
        try_files {path} {path}/ /index.html
        file_server
    }
}
```

Nginx에서는 `location /` 가 default fallback 역할을 했다면, Caddy에서는 매처 없는 `handle`이 그 자리를 차지한다. `handle`은 처음 매칭되는 하나만 실행된다는 점이 핵심이다. `route`로 바꾸면 매칭된 후에도 다른 디렉티브가 계속 평가되니, "Nginx의 location처럼 한 번에 하나만"을 원한다면 `handle`을 쓴다.

## server/location 블록 매핑

자주 쓰는 Nginx 디렉티브를 Caddy 등가물로 정리하면 이렇다.

| Nginx | Caddy | 비고 |
|---|---|---|
| `server { listen 443 ssl; server_name example.com; }` | `example.com {}` | Caddy는 호스트명만 적으면 자동 HTTPS |
| `listen 80; return 301 https://$host$request_uri;` | 자동 | Caddy가 80에서 443으로 자동 리다이렉트 |
| `location /api/ { ... }` | `handle /api/* { ... }` | 후행 와일드카드 주의 |
| `location = /healthz { ... }` | `handle /healthz { ... }` (정확 매칭) | 또는 `@health path /healthz` |
| `location ~ \.php$ { ... }` | `@php path_regexp \.php$` | 정규식 매처 |
| `location ~* \.(jpg|png)$` | `@img path_regexp -i \.(jpg|png)$` | `-i` 플래그로 대소문자 무시 |
| `proxy_pass http://upstream;` | `reverse_proxy upstream` | 헤더 자동 처리 차이 있음 |
| `try_files $uri $uri/ /index.html;` | `try_files {path} {path}/ /index.html` | 변수 표기만 다름 |
| `rewrite ^/old/(.*)$ /new/$1 last;` | `@old path /old/* / rewrite @old /new{path}` | 또는 `redir`로 외부 리다이렉트 |
| `return 301 /new;` | `redir /new 301` | |
| `return 404;` | `respond 404` | |
| `add_header X-Foo bar;` | `header X-Foo bar` | |
| `gzip on;` | `encode gzip zstd` | Caddy는 zstd도 기본 지원 |
| `client_max_body_size 100m;` | `request_body { max_size 100MB }` | |
| `access_log /var/log/access.log;` | `log { output file /var/log/access.log }` | |

이 표를 그냥 외워서 옮기면 70%는 동작한다. 나머지 30%가 운영 사고를 만든다.

## try_files / rewrite / return 변환

Nginx의 `try_files`는 Caddy에도 똑같은 이름으로 있어서 옮기기 쉬운 편이다. 단, Caddy의 `try_files`는 디렉티브가 아니라 매처를 구성하는 도우미라는 점이 다르다. Caddy의 `try_files`는 내부적으로 `rewrite`를 발생시키고, 그 뒤에 오는 `file_server`나 다른 핸들러가 새 경로로 처리한다.

```nginx
location / {
    try_files $uri $uri/ /index.html =404;
}
```

```caddy
handle {
    try_files {path} {path}/ /index.html
    file_server
}
```

Nginx의 `=404`처럼 마지막 fallback을 코드로 지정하는 옵션은 Caddy `try_files`엔 없다. 대신 모든 시도가 실패하면 그냥 다음 디렉티브로 흐르고, `file_server`가 파일이 없으면 자체적으로 404를 낸다.

`rewrite`는 Nginx에서 두 가지 의미로 쓰였다. 하나는 내부 재작성(`last`, `break`), 또 하나는 외부 리다이렉트(`permanent`, `redirect`). Caddy는 이 둘이 서로 다른 디렉티브다.

```nginx
# 내부 재작성
rewrite ^/api/v1/(.*)$ /api/v2/$1 last;

# 외부 리다이렉트 (301)
rewrite ^/old/(.*)$ /new/$1 permanent;
```

```caddy
# 내부 재작성
@v1 path_regexp v1 ^/api/v1/(.+)$
rewrite @v1 /api/v2/{re.v1.1}

# 외부 리다이렉트
@old path_regexp old ^/old/(.+)$
redir @old /new/{re.old.1} 301
```

`path_regexp`로 잡은 그룹은 `{re.<name>.1}` 형태로 참조한다. Nginx의 `$1`과 같지만 매처 이름을 명시적으로 적어야 한다는 점이 다르다.

`return`은 단순하다. 200/301/302/404 같은 상태 코드만 던지는 경우 Caddy는 `respond`나 `redir`로 나뉜다.

```nginx
location /maintenance { return 503; }
location /old        { return 301 /new; }
```

```caddy
handle /maintenance { respond 503 }
handle /old { redir /new 301 }
```

## proxy_pass와 reverse_proxy의 차이

이 부분이 마이그레이션에서 가장 자주 사고가 나는 곳이다. 같아 보이지만 헤더 처리, 슬래시 처리, 호스트 헤더 동작이 다르다.

### 헤더 자동 처리

Nginx의 `proxy_pass`는 기본적으로 `Host` 헤더만 업스트림으로 넘기고, 그것도 `proxy_pass`에 적힌 호스트로 바꿔서 보낸다. `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` 같은 건 직접 `proxy_set_header`로 적어줘야 한다.

```nginx
location /api/ {
    proxy_pass http://backend:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Caddy의 `reverse_proxy`는 이 헤더들을 자동으로 채운다. 원본 `Host` 헤더를 그대로 보내고, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`를 자동으로 추가한다. 그래서 위 Nginx 설정은 Caddy에서 한 줄이다.

```caddy
handle /api/* {
    reverse_proxy backend:8080
}
```

문제는 반대 방향이다. Nginx에서는 명시적으로 안 보냈던 헤더가 Caddy에서는 자동으로 추가되어, 백엔드가 `X-Forwarded-Proto`를 보고 https 리다이렉트를 도는 식의 회로가 새로 생길 수 있다. 옮긴 직후엔 백엔드 액세스 로그를 한 번 들여다보고 어떤 헤더가 새로 들어오는지 확인해야 한다.

`X-Real-IP`는 자동 추가되지 않는다. 백엔드가 이 이름을 기대하고 있다면 명시해야 한다.

```caddy
reverse_proxy backend:8080 {
    header_up X-Real-IP {remote_host}
}
```

### 슬래시 처리

이게 진짜 함정이다. Nginx의 `proxy_pass`는 URL에 슬래시가 있느냐 없느냐에 따라 동작이 완전히 달라진다.

```nginx
# 슬래시 없음: 클라이언트 경로 그대로 전달
location /api/ {
    proxy_pass http://backend:8080;
}
# /api/users → backend:8080/api/users

# 슬래시 있음: location 매칭 부분을 잘라내고 나머지만 전달
location /api/ {
    proxy_pass http://backend:8080/;
}
# /api/users → backend:8080/users
```

Caddy의 `reverse_proxy`는 이런 슬래시 기반 분기가 없다. 기본적으로 클라이언트 경로를 그대로 백엔드로 보낸다.

```caddy
handle /api/* {
    reverse_proxy backend:8080
}
# /api/users → backend:8080/api/users
```

prefix를 떼고 백엔드로 보내고 싶으면 `handle_path`를 쓰거나 `uri strip_prefix`를 명시한다.

```caddy
# /api/users → backend:8080/users
handle_path /api/* {
    reverse_proxy backend:8080
}
```

`handle_path`는 매칭된 prefix를 자동으로 떼고 나머지로 백엔드 요청을 만든다. Nginx에서 `proxy_pass http://backend/`(슬래시 포함)을 쓰던 자리는 십중팔구 `handle_path`로 옮겨야 한다.

prefix를 떼지 않고 그대로 보내야 하는데 (Nginx에서 슬래시 없는 `proxy_pass`) 이미 `handle_path`로 옮겨버렸다면, 백엔드는 갑자기 `/api/`가 사라진 요청을 받게 되어 라우팅이 전부 깨진다. 마이그레이션할 때 한 location씩 슬래시 유무를 확인하고 매핑해야 한다.

## 자동 HTTPS와 인증서 이전

Nginx에서는 인증서 파일을 직접 관리한다. certbot이 갱신해서 `/etc/letsencrypt/live/example.com/`에 깔아두면, Nginx는 그 경로를 `ssl_certificate`/`ssl_certificate_key`로 참조하고, certbot이 cron으로 갱신하면 reload만 받는다.

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
}
```

Caddy는 이걸 통째로 자기가 한다. 도메인을 사이트 블록에 적으면 ACME 챌린지를 직접 돌려 인증서를 받아오고, `~/.local/share/caddy/`(또는 데이터 디렉토리)에 저장하고, 만료 30일 전에 자동 갱신한다. 옮길 때 보통 두 가지 선택지가 있다.

**옵션 A: 기존 인증서 버리고 Caddy가 새로 받게 한다.** 가장 깔끔하고 권장하는 방법이다. 단, 새 인증서를 받는 동안 Let's Encrypt rate limit에 걸리지 않게 도메인 수와 시도 횟수를 신경 써야 한다. 또 도메인의 80/443 포트가 외부에서 닿아야 HTTP-01 챌린지가 통과한다. 사내 도메인이라면 DNS-01 챌린지로 갈아타야 한다.

**옵션 B: 기존 certbot 인증서를 그대로 사용한다.** Caddy의 자동 HTTPS를 끄고 수동으로 지정한다. 운영 일정이 빡빡해서 인증서 발급 부담을 다음 갱신 주기로 미루고 싶을 때 쓴다.

```caddy
example.com {
    tls /etc/letsencrypt/live/example.com/fullchain.pem /etc/letsencrypt/live/example.com/privkey.pem

    reverse_proxy backend:8080
}
```

이러면 Caddy는 ACME를 안 돌리고 그 파일만 읽어서 쓴다. 단, Caddy 프로세스가 그 경로를 읽을 권한이 있어야 한다. certbot이 만든 파일은 root 소유에 0600 권한이라 Caddy를 다른 사용자로 띄우면 못 읽는다. 보통 Caddy는 `caddy` 시스템 유저로 도는데, 이 유저를 `letsencrypt` 그룹에 넣거나 인증서 디렉토리 권한을 풀어줘야 한다.

옵션 B로 시작했다가 나중에 A로 옮기는 흐름이 가장 안전하다. 일단 인증서를 그대로 들고 와서 트래픽이 정상인지 확인하고, 다음 갱신 시점에 `tls` 디렉티브를 지워서 Caddy 자동 발급으로 넘긴다.

자동 HTTPS와 함께 따라오는 변화 중 하나는 80 포트 자동 리다이렉트다. Nginx에서 `listen 80; return 301 https://...;` 블록을 따로 적었다면, Caddy에서는 그 블록이 필요 없다. 호스트명만 적으면 80 포트로 들어온 요청을 자동으로 443으로 보낸다. 옛날 설정을 그대로 옮기다가 80 포트 리다이렉트 사이트 블록을 따로 만들면 충돌이 난다.

## PHP-FPM: fastcgi에서 php_fastcgi로

Nginx + PHP-FPM 조합은 fastcgi_pass와 여러 줄의 fastcgi_param으로 이루어진다.

```nginx
location ~ \.php$ {
    fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    fastcgi_index index.php;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
}
```

Caddy는 이 패턴을 통째로 묶어 `php_fastcgi` 한 줄로 처리한다.

```caddy
example.com {
    root * /var/www/html
    php_fastcgi unix//run/php/php8.2-fpm.sock
    file_server
}
```

`unix//run/...`처럼 슬래시 두 개로 시작해야 유닉스 소켓으로 인식한다는 점만 헷갈린다. TCP라면 `php_fastcgi 127.0.0.1:9000` 식으로 쓴다.

`php_fastcgi`는 내부적으로 try_files로 `index.php`까지 fallback 처리하고, `SCRIPT_FILENAME`, `PATH_INFO` 같은 fastcgi 파라미터도 알아서 채운다. 정확한 동작이 마음에 안 들면 `expanded` 옵션으로 풀어볼 수 있다.

```caddy
php_fastcgi unix//run/php/php8.2-fpm.sock {
    try_files {path} {path}/index.php =404
    env APP_ENV production
}
```

WordPress, Laravel, Drupal 같은 프레임워크는 보통 이 한 줄로 끝난다. 옛날 Nginx 설정에서 `if (!-e $request_filename)`로 분기 치던 부분이 깔끔하게 사라진다.

## 액세스 로그 포맷 맞추기

운영팀이 ELK나 Loki로 access log를 파싱하고 있으면, 로그 포맷을 그대로 옮기는 게 마이그레이션의 숨은 작업이다. Nginx의 `log_format`은 보통 이런 식이다.

```nginx
log_format combined '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';

access_log /var/log/nginx/access.log combined;
```

Caddy의 기본 로그 포맷은 JSON이다. 이걸 그대로 두면 기존 파서가 다 망가진다. 두 가지 선택지가 있다.

**기존 combined 포맷을 흉내낸다.** Caddy 2의 `transform-encoder` 모듈을 쓰면 임의의 텍스트 포맷을 만들 수 있다. 단, 표준 빌드에는 없어서 `xcaddy`로 빌드해야 한다.

**파서를 JSON으로 옮긴다.** 장기적으로는 이 방향이 낫다. JSON 로그는 필드별로 구조화되어 파싱이 안정적이고 누락도 적다. Loki, Promtail, Vector 모두 JSON을 잘 다룬다. Caddy의 기본 JSON 로그는 이런 모습이다.

```json
{
  "level": "info",
  "ts": 1714720000.123,
  "logger": "http.log.access",
  "msg": "handled request",
  "request": {
    "remote_ip": "1.2.3.4",
    "method": "GET",
    "uri": "/api/users",
    "headers": {"User-Agent": ["curl/8.0"]}
  },
  "duration": 0.012,
  "size": 1024,
  "status": 200
}
```

Nginx 시절 `$body_bytes_sent`였던 게 `size`, `$request_time`이었던 게 `duration`처럼 이름이 바뀌어서, 파서 룰을 한 번 갈아엎어야 한다. 마이그레이션 일정에 이 작업을 넣지 않으면 옮긴 다음 날 모니터링 대시보드가 비어 보인다.

```caddy
{
    log default {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 10
        }
        format json
    }
}
```

## 단계적 전환: Caddy를 Nginx 앞단에 두기

운영 중인 Nginx를 통째로 Caddy로 바꾸는 건 위험하다. 트래픽 한 번에 다 받는 진입점을 갑자기 갈아엎으면 어디서 깨졌는지 추적이 어렵다. 안전한 패턴은 Caddy를 Nginx 앞단에 두고, 도메인이나 경로 단위로 점진적으로 옮기는 것이다.

```
[Client] → [Caddy:443] → [Nginx:8080] → [App]
                     ↘
                       [App:9000]  (직접 옮긴 경로)
```

Caddy는 자동 HTTPS만 담당하고, 나머지는 그대로 Nginx로 흘려보낸다. 옮길 준비가 된 경로만 Caddy가 직접 핸들링하게 떼어낸다.

```caddy
example.com {
    # 새 경로는 Caddy가 직접 처리
    handle /api/v2/* {
        reverse_proxy app-v2:9000
    }

    # 나머지는 기존 Nginx로
    handle {
        reverse_proxy localhost:8080
    }
}
```

이 구조는 두 가지 이점이 있다. 첫째, 인증서 관리를 한 번에 Caddy로 옮길 수 있다. Nginx는 이제 평문 80/8080으로만 받으면 된다. 둘째, 경로별로 카나리하기 쉽다. 한 경로가 깨지면 그 `handle` 블록만 되돌리면 된다.

주의할 점은 X-Forwarded-* 체인이다. Caddy가 한 번 헤더를 붙이고, 그 뒤에 Nginx가 또 한 번 붙이면 `X-Forwarded-For`에 IP가 두 번 적히는 식의 일이 생긴다. 안쪽 Nginx에서 `set_real_ip_from`으로 Caddy를 신뢰 프록시로 등록하고, `real_ip_header X-Forwarded-For`로 클라이언트 IP를 복원해야 한다.

```nginx
set_real_ip_from 127.0.0.1;
real_ip_header X-Forwarded-For;
real_ip_recursive on;
```

이 단계가 익숙해지면 Nginx의 location 블록을 하나씩 Caddy의 `handle`로 옮겨가다가, 마지막 fallback `handle`까지 비울 수 있는 시점에 Nginx 프로세스를 내린다.

## 옮기면서 자주 깨지는 동작

이론은 됐고, 실제로 옮기면 어디서 깨지는지가 중요하다. 같은 운영 시나리오에서 반복적으로 만나는 것들을 모았다.

### URL 정규화 차이

Nginx는 들어오는 URL을 정규화한다. `/api//users`, `/api/./users`, `/api/x/../users` 같은 요청은 모두 `/api/users`로 정규화되어 location 매칭을 거친다. Caddy도 정규화를 하지만 기본 동작이 미묘하게 다르다. Caddy 2.7부터는 `merge_slashes`, `clean_path` 같은 옵션이 도입되어 명시적으로 켤 수 있다.

```caddy
{
    servers {
        protocols h1 h2 h3
    }
}

example.com {
    @bad path_regexp /\.\.|//
    respond @bad 400
    reverse_proxy backend:8080
}
```

옮기고 나서 정상 트래픽엔 문제가 없다가, 어느 봇이 `/api//x/../y` 같은 요청을 보내고 백엔드가 처음 보는 형태에 500을 내는 경우가 있다. 옮기기 전에 access log에서 `//`나 `..`이 들어간 경로의 비율을 확인하고, 어떻게 처리할지 정해야 한다.

### 후행 슬래시 처리

이게 진짜 짜증난다. Nginx에서 `location /api/`로 잡으면 `/api/`로 끝나는 요청과 `/api/...` 하위 경로가 모두 매칭된다. `/api`(슬래시 없음)는 매칭되지 않는다. 보통 Nginx는 디렉토리에 대해 자동으로 `/api → /api/` 리다이렉트를 발생시키는 경우가 있는데, 이게 try_files나 다른 디렉티브와 엮여 있어서 동작이 미묘하다.

Caddy의 `handle /api/*`도 `/api/`로 끝나는 prefix만 매칭한다. `/api`만 따로 들어오면 매칭 안 된다. 후행 슬래시 자동 추가는 `file_server`가 디렉토리 인덱스를 줄 때 자동으로 한다. reverse_proxy 시나리오라면 슬래시가 안 붙은 요청을 따로 처리해야 한다.

```caddy
# /api → /api/로 리다이렉트
@api_no_slash path /api
redir @api_no_slash /api/ 301

handle /api/* {
    reverse_proxy backend:8080
}
```

옮긴 직후 `/api`(슬래시 없음) 요청이 404로 떨어지는 사고가 자주 난다. 검색 엔진 봇, 옛날 북마크, 잘못 만들어진 클라이언트는 슬래시를 자주 빼먹는다. 운영 전환 전에 access log에서 슬래시 없는 prefix 요청이 얼마나 들어오는지 봐야 한다.

### 매처의 대소문자 처리

Nginx의 `location` 매칭은 기본 대소문자 구분이다. `~*` 정규식이 대소문자 무시이고 prefix 매칭은 항상 구분한다. 그런데 운영 서버에서 막상 `/Static/foo.css` 같은 요청이 들어와도 파일 시스템이 대소문자를 구분 안 하면(macOS, 일부 Linux 설정) 그냥 동작해버린다. 옮기면서 운영체제까지 바뀌면 드러난다.

Caddy의 매처도 기본 대소문자 구분이다. `path_regexp`에 `-i` 플래그를 주면 대소문자 무시가 된다.

```caddy
@css path_regexp -i \.css$
header @css Cache-Control "public, max-age=3600"
```

`path` 매처에는 `-i` 플래그가 없다. 대소문자 무시 prefix 매칭이 필요하면 `path_regexp`로 풀어야 한다.

```caddy
@api path_regexp -i ^/api/
handle @api {
    reverse_proxy backend:8080
}
```

이 부분은 마이그레이션 후 한참 지나서야 발견되는 경향이 있다. 정상 트래픽은 lowercase로 잘 들어오는데, 어느 클라이언트가 우연히 `/API/`로 보낸 요청만 404가 되는 식이다.

### 빈 응답 vs 명시적 응답

Nginx에서 `location /healthz { return 200; }`은 빈 본문에 200을 돌려준다. Caddy의 `respond 200`도 마찬가지다. 그런데 헬스체크 받는 쪽이 본문을 파싱하려 하면 빈 응답에서 `Content-Type` 처리가 다를 수 있다. Nginx는 `Content-Type`을 안 붙이고 보낼 수 있는 반면, Caddy는 `text/plain; charset=utf-8`을 자동으로 붙이는 경우가 있다. 헬스체크가 strict한 검증을 하고 있다면 명시적으로 헤더와 본문을 같이 적어야 한다.

```caddy
handle /healthz {
    respond "ok" 200 {
        close
    }
}
```

### 에러 페이지

Nginx의 `error_page 404 /404.html;`은 Caddy에서 `handle_errors`로 옮긴다.

```caddy
example.com {
    root * /var/www/html
    file_server

    handle_errors {
        @404 expression {http.error.status_code} == 404
        rewrite @404 /404.html
        file_server
    }
}
```

`handle_errors` 블록은 다른 핸들러에서 에러가 났을 때만 실행된다. 안에서 다시 매처를 걸어 상태 코드별로 다른 페이지를 줄 수 있다. Nginx에서 여러 줄로 늘어놓던 `error_page`를 하나의 블록으로 묶을 수 있어 깔끔해지는 부분이다.

## 마이그레이션 진행 순서

다른 글에서 이미 다룬 내용이지만 한 번 더 정리하면, 이 순서로 옮기는 게 가장 사고가 적다.

먼저 기존 Nginx 설정을 location 블록 단위로 쪼개고, 각 블록에서 어떤 일을 하는지 한 줄로 적는다. 그다음 위의 매핑표를 보면서 1:1 변환 초안을 만든다. 이때 슬래시 처리, X-Forwarded-* 헤더, ssl_certificate 경로, fastcgi 설정처럼 함정이 많은 부분을 따로 표시해 둔다.

Caddy를 Nginx 앞단에 두는 단계적 전환 패턴으로 일단 띄운다. 모든 트래픽은 그대로 Nginx로 흘러가지만, TLS 종료만 Caddy가 한다. 이 상태로 며칠 운영하면서 인증서, 로그, 기본 동작이 정상인지 확인한다.

그다음에 한 번에 한 location씩 Caddy의 `handle`로 옮긴다. 옮긴 직후 access log를 보면서 4xx/5xx 비율이 평소 수준인지 확인하고, 헤더가 제대로 들어가는지 백엔드에서 검증한다. 이 단계에서 위에서 정리한 깨지는 동작들이 하나씩 발견된다.

마지막에 Nginx로 가던 fallback `handle`을 비우고 Nginx 프로세스를 내린다. 이 시점에 access log 포맷 변경, certbot 정리, 옛날 nginx.conf 백업까지 마무리한다.

옮기는 데 주말 한 번이면 끝날 것 같은 작업이지만, 운영 사이트라면 보통 2~3주짜리 일이라고 보는 게 맞다. 매핑이 단순한 것에 비해 두 서버의 모델 차이에서 오는 동작 변화가 곳곳에 숨어 있고, 그게 다 운영 트래픽에서 드러나기 때문이다.
