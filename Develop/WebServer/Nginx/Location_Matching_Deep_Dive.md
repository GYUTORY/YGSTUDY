---
title: "Nginx location 매칭 우선순위 심화"
tags: [nginx, location, rewrite, try_files, named-location, proxy_pass]
updated: 2026-06-07
---

# Nginx location 매칭 우선순위 심화

기존 location 문서가 5가지 매칭자의 우선순위를 다뤘다면 이 문서는 그 다음 단계를 본다. 실제 운영에서 마주치는 문제는 매칭 규칙 자체보다 `last`/`break`가 일으키는 재매칭, `@name`으로 점프하는 흐름, `try_files`가 마지막 인자를 어떻게 해석하는지, `proxy_pass`에 URI를 붙였는지 안 붙였는지에 따라 백엔드로 가는 경로가 달라지는 지점이다. 이 차이를 모르면 nginx -T로 본 설정과 실제 동작이 다른 상황이 반복된다.

## 매칭 평가 알고리즘 trace

Nginx가 location을 고르는 과정은 단순한 if-else 체인이 아니다. 두 단계로 나뉜다. prefix 매칭 단계와 regex 매칭 단계.

### 단계별 흐름

```text
요청 URI: /api/v1/users/42

1. exact match (=) 검사
   - location = /health 있으면 비교 → 불일치
   - location = /api/v1/users/42 있으면 즉시 종료
   - 일치 없으면 다음 단계

2. prefix 매칭 전수 검사 (longest-prefix를 기억)
   - location /          → 일치 (길이 1)
   - location /api/      → 일치 (길이 5)
   - location /api/v1/   → 일치 (길이 8)  ← 가장 김, 기억
   - location /static/   → 불일치
   - location /docs      → 불일치

3. 최장 prefix가 ^~ 수식어를 가졌는가
   - YES → regex 단계 건너뛰고 그 location 선택, 종료
   - NO  → 그 prefix를 임시 후보로 보관하고 regex 단계로

4. regex 매칭을 설정 파일 등장 순서대로 검사
   - location ~ \.php$   → 불일치
   - location ~ ^/api/v1 → 일치 ← 즉시 선택, 종료
   - (대소문자 무시는 ~*)

5. regex가 하나도 일치하지 않으면
   - 3단계에서 보관해둔 prefix 후보 선택
```

핵심은 prefix는 전수 검사하고 그중 가장 긴 것을 기억하지만, regex는 등장 순서대로 검사하다가 처음 일치하는 순간 끝낸다는 것이다. regex 순서를 바꾸면 동작이 달라진다.

### regex 평가가 스킵되는 조건

regex 단계로 가지 않는 경우는 세 가지다.

```nginx
# 케이스 1: exact match 일치
location = /health { return 200; }   # 여기서 끝, regex 검사 안 함

# 케이스 2: 최장 prefix가 ^~
location ^~ /static/ { root /var/www; }
location ~ \.css$    { add_header X-Regex on; }
# /static/main.css 요청 → ^~ 때문에 regex 검사 안 함, /static/ 선택

# 케이스 3: regex location이 아예 정의되어 있지 않다
# (이 경우 매칭 비용이 가장 싸다)
```

`^~`는 prefix 매칭 단계의 일부지 별도 단계가 아니다. 가장 긴 prefix를 골랐는데 그 prefix에 `^~`가 붙어 있으면 regex를 스킵한다. 길이가 짧은 prefix에 `^~`가 붙어 있어도 더 긴 일반 prefix가 있으면 그 일반 prefix가 이긴다.

```nginx
location ^~ /api/    { return 200 "short"; }
location    /api/v1/ { return 200 "long";  }
location ~  ^/api/v1/users { return 200 "regex"; }

# /api/v1/users 요청 → "regex"
# 최장 prefix는 /api/v1/ (^~ 아님), regex 검사 진행, 일치하므로 regex 선택
```

## rewrite의 last vs break

`rewrite` 지시어 뒤에 붙는 `last`와 `break`는 한 글자 차이지만 phase 동작이 완전히 다르다. 둘 다 ngx_http_rewrite_module이 처리한다.

### phase 관점에서의 차이

Nginx 요청 처리는 11개 phase로 진행되는데 rewrite 모듈이 관여하는 phase는 `SERVER_REWRITE`와 `REWRITE` 두 곳이다. location 선택 후의 REWRITE phase에서 rewrite 지시어가 실행된다.

- `last`: 현재 location의 rewrite phase를 끝내고 새 URI로 **location 매칭을 다시 한다**. 즉 internal redirect가 일어난다.
- `break`: 현재 location의 rewrite phase만 끝내고 location 재매칭을 하지 않는다. 같은 location 안에서 content phase로 넘어간다.

```nginx
location /old/ {
    rewrite ^/old/(.*)$ /new/$1 last;
    # 여기 아래는 실행 안 됨, /new/$1로 location 재매칭
}

location /new/ {
    proxy_pass http://backend;
}
```

`/old/abc` 요청 → `/new/abc`로 URI가 바뀌고 location 매칭을 다시 한다 → `location /new/`가 선택되어 백엔드로 프록시.

같은 상황을 `break`로 바꾸면 동작이 다르다.

```nginx
location /old/ {
    rewrite ^/old/(.*)$ /new/$1 break;
    proxy_pass http://backend;
    # URI는 /new/abc로 바뀌었지만 location은 그대로 /old/
    # proxy_pass가 /new/abc를 백엔드로 보냄
}
```

`break`는 location 재매칭을 막기 때문에 그 자리에서 content를 처리해야 한다. proxy_pass나 root 같은 content handler가 같은 블록 안에 있어야 의미가 있다.

### internal redirect 횟수 제한

`last`로 location 재매칭을 일으키는 패턴은 무한루프 가능성이 있다. Nginx는 internal redirect를 최대 10회로 제한한다. 초과하면 error.log에 다음이 찍힌다.

```text
2026-06-07 14:23:11 [error] 1234#0: *567 rewrite or internal redirection cycle while processing "/loop", client: 1.2.3.4
```

실제로 본 사례.

```nginx
location /a/ {
    rewrite ^/a/(.*)$ /b/$1 last;
}
location /b/ {
    rewrite ^/b/(.*)$ /a/$1 last;   # /a/와 /b/가 핑퐁
}
```

`error_page`로 점프하는 경우에도 카운트가 올라가기 때문에 try_files → @fallback → try_files 패턴을 잘못 짜면 같은 에러가 난다. 디버깅할 때는 `error_log` 레벨을 `debug`로 올리고 'using configuration' 로그를 추적하면 어느 location이 몇 번 선택됐는지 보인다.

### 추가 함정: rewrite 외 지시어와의 상호작용

`if` 블록 안에서 `set`이나 `rewrite`를 쓰는 경우 phase 순서가 헷갈리기 시작한다. `if`는 rewrite phase에서 평가되기 때문에 다음 코드는 의도대로 동작하지 않는다.

```nginx
location / {
    set $backend "default";
    if ($http_x_canary = "1") {
        set $backend "canary";
    }
    proxy_pass http://$backend;
}
```

이 정도는 잘 작동하지만 `if` 안에 `proxy_pass`를 넣으면 location 블록이 암묵적으로 생성되어 동작이 망가진다. 뒤의 if 블록 항목에서 다시 다룬다.

## named location (@name)

`@`로 시작하는 location은 URI 매칭에 참여하지 않는다. 클라이언트가 `/@fallback` 같은 URI로 요청을 보내도 매칭되지 않고 404가 떨어진다. 내부에서만 점프할 수 있는 라벨이다.

### 점프 가능한 지시어

- `try_files` 마지막 인자
- `error_page` 점프 대상
- `X-Accel-Redirect` 응답 헤더 (백엔드가 보내면 nginx가 내부 리다이렉트)

### SPA fallback 패턴

React/Vue처럼 클라이언트 라우팅을 쓰는 SPA에서 가장 자주 보는 패턴이다.

```nginx
server {
    root /var/www/spa;
    index index.html;

    location / {
        try_files $uri $uri/ @fallback;
    }

    location @fallback {
        rewrite ^.*$ /index.html last;
    }
}
```

`/dashboard/settings` 같은 URL이 들어오면 파일이 없으므로 try_files가 `@fallback`으로 점프하고 거기서 `/index.html`로 rewrite한다.

`@fallback` 안에서 `last`를 쓴 이유는 다시 location 매칭으로 보내 `/index.html` 파일을 서빙하기 위해서다. `break`를 쓰면 named location에는 content handler가 없으므로 빈 응답이 나간다.

### 인증 실패 처리 패턴

`auth_request`가 401/403을 받았을 때 로그인 페이지로 보내는 패턴.

```nginx
location /private/ {
    auth_request /auth;
    error_page 401 = @login_redirect;
    proxy_pass http://backend;
}

location = /auth {
    internal;
    proxy_pass http://auth_service/verify;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
}

location @login_redirect {
    return 302 /login?return=$request_uri;
}
```

`error_page 401 = @login_redirect`에서 `=` 기호가 핵심이다. 이게 없으면 응답 상태가 401 그대로 유지되고, 있으면 named location의 응답 상태로 바뀐다.

## try_files 분기 동작

`try_files`는 인자를 왼쪽에서 오른쪽으로 순서대로 평가하다가 존재하는 첫 파일을 서빙한다. 마지막 인자만 특별 취급된다.

### 마지막 인자의 종류

```nginx
# 형태 1: 마지막 인자가 =코드  → 그 상태 코드로 종료
try_files $uri /index.html =404;

# 형태 2: 마지막 인자가 URI    → 그 URI로 internal redirect
try_files $uri $uri/ /index.html;

# 형태 3: 마지막 인자가 @name  → named location으로 점프
try_files $uri @backend;
```

세 형태의 차이를 정확히 알아야 한다. 형태 2는 마지막 인자도 파일 존재 여부를 확인하지 않고 무조건 internal redirect를 일으킨다. 그 결과 location 재매칭이 일어난다. 형태 3은 named location으로 곧장 점프하므로 매칭 비용이 없다.

### $uri 평가 시점

`try_files`의 `$uri`는 try_files가 평가되는 그 시점의 URI다. rewrite로 URI가 바뀐 뒤에 try_files가 실행되면 바뀐 URI를 본다.

```nginx
location /img/ {
    rewrite ^/img/(.*)$ /static/img/$1 break;
    try_files $uri =404;
    # $uri는 /static/img/foo.png (rewrite 결과)
    root /var/www;
}
```

`break`로 location 재매칭을 막았기 때문에 같은 location 안의 try_files가 실행된다. `$uri`는 변경된 값이다.

### 디렉토리 인덱스 처리

`$uri/`처럼 슬래시를 붙이면 디렉토리가 존재하는지 확인하고 존재하면 `index` 지시어의 파일을 찾는다.

```nginx
location / {
    try_files $uri $uri/ @fallback;
    index index.html index.htm;
}
```

`/docs/` 요청이 들어오면 `$uri`(=`/docs/`)는 파일이 아니므로 실패하고, `$uri/`(=`/docs//`)에서 디렉토리 존재 확인 후 `/docs/index.html`을 서빙한다.

### 정적/동적 분기 패턴

정적 자산은 파일로 서빙하고 없으면 동적 백엔드로 넘기는 패턴이 흔하다.

```nginx
location / {
    try_files $uri @app;
}

location @app {
    proxy_pass http://app_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

정적 파일이 디스크에 있으면 nginx가 직접 서빙하고, 없으면 백엔드로 위임한다. 운영에서 가장 흔한 형태다.

## proxy_pass의 URI 유무

`proxy_pass` 뒤에 URI 경로를 붙였는지 안 붙였는지에 따라 백엔드로 가는 경로가 달라진다. 이걸 모르고 설정하면 백엔드가 받는 path가 의도와 다른 일이 흔하다.

### URI 없음: 원본 path 그대로 전달

```nginx
location /api/ {
    proxy_pass http://backend;
}
```

`/api/users/42` 요청 → 백엔드는 `/api/users/42`를 받는다.

### URI 있음: location prefix를 잘라내고 URI 부분으로 교체

```nginx
location /api/ {
    proxy_pass http://backend/;
}
```

`/api/users/42` 요청 → 백엔드는 `/users/42`를 받는다. `/api/`가 `/`로 치환된다.

```nginx
location /api/ {
    proxy_pass http://backend/v2/;
}
```

`/api/users/42` 요청 → 백엔드는 `/v2/users/42`를 받는다.

### regex location에서는 URI 사용 불가

이 차이는 prefix location에서만 적용된다. regex location은 prefix 길이가 정해져 있지 않기 때문에 nginx가 어디까지 잘라낼지 결정할 수 없다. 그래서 다음은 설정 로드 시점에 에러가 난다.

```nginx
location ~ ^/api/ {
    proxy_pass http://backend/;
}

# nginx: [emerg] "proxy_pass" cannot have URI part in location given by regular expression
```

regex location에서 백엔드 경로를 바꾸려면 rewrite를 쓴다.

```nginx
location ~ ^/api/(.*)$ {
    rewrite ^/api/(.*)$ /$1 break;
    proxy_pass http://backend;
}
```

`break`를 써야 location 재매칭이 일어나지 않고 같은 블록의 proxy_pass가 변경된 URI를 본다.

### 변수가 들어간 proxy_pass

`proxy_pass`에 변수가 포함되면 nginx는 자동 URI 처리를 하지 않는다. 즉 URI를 명시적으로 붙여야 한다.

```nginx
location /service/ {
    set $upstream "http://backend";
    proxy_pass $upstream;
    # 이렇게 하면 백엔드는 빈 path를 받는다. 의도와 다름.
}

# 정상 형태
location /service/ {
    set $upstream "http://backend";
    proxy_pass $upstream$request_uri;
}
```

DNS 동적 해상도를 위해 변수형 proxy_pass를 쓰는 경우가 많은데, `$request_uri` 또는 `$uri`를 명시적으로 붙이는 것을 잊으면 path가 사라진다. 운영에서 흔하게 보는 실수다.

## limit_except와 if 블록

### limit_except

특정 HTTP 메서드에만 다른 처리를 하고 싶을 때 사용한다. 안에 적은 지시어가 **그 메서드 외**의 요청에 적용된다는 점이 헷갈린다.

```nginx
location /api/ {
    limit_except GET POST {
        deny all;
    }
    proxy_pass http://backend;
}
```

GET, POST는 통과하고 PUT/DELETE/PATCH는 거부된다. `limit_except GET POST` 블록 내부의 `deny all`이 GET/POST가 아닌 메서드에 적용되는 구조다.

### if is evil

Nginx 공식 위키에 'If is evil... when used in location context'라는 문서가 있다. `if`가 location 안에서 쓰일 때 발생하는 문제는 두 가지다.

첫째, `if` 블록은 암묵적으로 새 location을 만든다. 그래서 바깥 location의 지시어가 `if` 안에서 일부만 상속된다.

```nginx
location /api/ {
    add_header X-From-Outer "yes";
    if ($http_x_test) {
        add_header X-From-Inner "yes";
        # 이 안에서는 X-From-Outer 헤더가 추가되지 않을 수 있다
    }
}
```

`add_header`는 같은 컨텍스트에 다른 `add_header`가 있으면 상속이 끊어진다. `if` 안에 `add_header`를 두면 바깥의 `add_header`가 사라진다.

둘째, `if` 안에 `proxy_pass`나 `rewrite`를 두면 phase 순서가 어긋나서 의도하지 않은 동작이 일어난다.

```nginx
# 안전하지 않은 패턴
location /api/ {
    if ($request_method = POST) {
        proxy_pass http://write_backend;
    }
    proxy_pass http://read_backend;
}
```

이 코드는 POST에서도 read_backend로 가거나 양쪽 다 호출되거나 nginx 버전에 따라 동작이 갈린다.

### 안전한 대체 패턴

- 메서드 분기는 `limit_except`로
- 헤더 기반 분기는 `map` 지시어로
- 정말 조건 분기가 필요하면 named location + try_files 조합으로

```nginx
# map으로 변수 분기
map $http_x_canary $backend {
    default "stable_backend";
    "1"     "canary_backend";
}

server {
    location /api/ {
        proxy_pass http://$backend;
    }
}
```

`map`은 server 블록 밖에서 정의하고 변수를 참조만 한다. phase 순서 문제가 없다.

## 실전 트러블슈팅

### nginx -T로 최종 머지 결과 확인

include로 분산된 설정이 많은 경우 실제 nginx가 보는 통합 설정을 확인해야 한다.

```bash
sudo nginx -T 2>&1 | less
```

`-t`는 문법 검사만, `-T`는 문법 검사 + 머지된 전체 설정 출력이다. server_name 충돌이나 중복 location 정의를 찾을 때 가장 빠르다.

특정 server 블록만 보고 싶을 때.

```bash
sudo nginx -T 2>&1 | awk '/server {/,/^}/' | less
```

### error_log debug 레벨 추적

매칭 과정을 직접 보려면 debug 레벨이 필요하다. 다만 nginx가 `--with-debug` 옵션으로 빌드되어 있어야 한다. apt나 brew로 설치한 패키지는 보통 포함되어 있다.

```nginx
error_log /var/log/nginx/debug.log debug;
```

debug.log에 찍히는 항목 중 location 매칭과 관련된 핵심 라인.

```text
test location: "/api/"
using configuration "/api/"
rewrite phase: 0
http script copy: "/v2/users/42"
http proxy_pass: "/v2/users/42"
```

`test location`이 prefix 매칭 후보 검사, `using configuration`이 최종 선택된 location, `rewrite phase`가 phase 진입, `http proxy_pass`가 백엔드로 보내는 최종 URI다. 의도와 다른 location이 선택되면 이 로그에서 즉시 찾을 수 있다.

debug 로그는 양이 많기 때문에 운영 환경에 켜둘 수는 없다. 특정 IP만 디버그 로그를 남기는 방법이 있다.

```nginx
events {
    debug_connection 192.168.1.100;
    debug_connection 10.0.0.0/24;
}
```

지정한 IP에서 온 연결만 debug 로그를 남기고 나머지는 정상 레벨로 기록한다. 운영 서버에서 특정 클라이언트의 요청만 추적할 때 쓴다.

### alias vs root trailing slash 문제

`root`와 `alias`는 비슷해 보이지만 path 계산 방식이 다르다.

```nginx
# root: location prefix를 포함한 경로
location /static/ {
    root /var/www;
    # /static/main.css → /var/www/static/main.css
}

# alias: location prefix를 잘라낸 경로
location /static/ {
    alias /var/www/assets/;
    # /static/main.css → /var/www/assets/main.css
}
```

`alias`를 쓸 때 trailing slash가 location과 alias 양쪽 모두에 일관되게 있어야 한다. 한쪽만 있으면 path가 깨진다.

```nginx
# 잘못된 형태 1: location에는 슬래시, alias에는 없음
location /static/ {
    alias /var/www/assets;
    # /static/main.css → /var/www/assetsmain.css (파일 못 찾음)
}

# 잘못된 형태 2: 둘 다 슬래시 없음
location /static {
    alias /var/www/assets;
    # /static/main.css → /var/www/assets/main.css (우연히 동작)
    # /staticmain.css → /var/www/assetsmain.css (URI 일부로 매칭됨)
}
```

규칙은 단순하다. `alias`를 쓰면 location prefix와 alias path의 trailing slash를 똑같이 맞춘다. 둘 다 슬래시로 끝나게 하는 쪽이 안전하다.

regex location에서 `alias`를 쓰는 경우는 더 까다롭다. 캡처 그룹을 alias path에 직접 박아야 한다.

```nginx
location ~ ^/files/(.+)$ {
    alias /var/www/storage/$1;
}
```

`$1`을 alias path 안에서 사용하는 게 핵심이다. root는 이런 식으로 못 쓴다.

### 매칭 디버깅 체크 순서

매칭이 의도와 다르게 동작할 때 확인 순서.

1. `nginx -T`로 머지된 설정을 보고 location이 몇 개 정의되어 있는지 센다. include 안의 중복 정의가 가장 흔한 원인이다.
2. exact match(`=`)와 `^~` prefix가 있는지 본다. 이 둘이 regex 매칭을 차단한다.
3. regex location은 등장 순서대로 검사되므로 설정 파일 안 순서를 확인한다.
4. debug 로그에서 `using configuration` 라인을 찾는다. 거기 적힌 location이 최종 선택된 것이다.
5. rewrite/proxy_pass가 있다면 internal redirect 횟수와 최종 URI를 확인한다.

매칭 자체보다 매칭 이후의 rewrite, try_files, proxy_pass URI 처리에서 문제가 생기는 경우가 더 많다. 매칭 규칙만 외우지 말고 phase 단위로 요청이 어디까지 진행됐는지 추적하는 습관이 필요하다.
