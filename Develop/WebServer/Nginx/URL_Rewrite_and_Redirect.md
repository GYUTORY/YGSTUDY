---
title: URL Rewrite and Redirect
tags: [Nginx, URL Rewrite, Redirect, HTTP]
updated: 2026-07-26
---

# URL Rewrite and Redirect

`return`과 `rewrite`는 둘 다 요청 경로를 바꾸거나 리디렉션한다. 이 둘을 혼용하다 보면 무한 루프에 빠지거나, 쿼리스트링이 날아가거나, 캐시가 꼬이는 상황을 만난다.

## return vs rewrite

### return

`return`은 응답을 즉시 보낸다. 내부 처리 없이 클라이언트에게 바로 HTTP 응답 코드와 URL을 반환한다.

```nginx
location /old-path {
    return 301 https://example.com/new-path;
}
```

리디렉션 용도라면 `return`이 맞다. Nginx 처리 파이프라인을 더 이상 타지 않기 때문에 예측하기 쉽고 디버깅도 단순하다.

### rewrite

`rewrite`는 내부에서 URI를 바꾼다. 클라이언트는 URL이 바뀐 사실을 모른다. 플래그 없이 쓰면 다음 location 블록 매칭부터 다시 시작한다.

```nginx
location /api/v1 {
    rewrite ^/api/v1/(.*)$ /api/v2/$1 last;
    proxy_pass http://backend;
}
```

`rewrite`는 URI를 내부적으로 변환해서 다른 location으로 넘길 때 쓴다. 클라이언트에게 리디렉션을 보내고 싶다면 `return`이 더 적합하다.

### 선택 기준

클라이언트 주소창의 URL이 바뀌어야 한다면 `return`. 내부적으로 경로를 바꾸되 클라이언트에게 숨기고 싶다면 `rewrite`.

`rewrite`를 남용하면 Nginx가 처리하는 단계가 많아져서 디버깅이 어려워진다. 단순 리디렉션은 `return`으로 처리하는 게 맞다.

## 301 / 302 / 307 / 308

HTTP 리디렉션 코드는 네 가지가 실무에서 주로 쓰인다. 각각 의미가 다르고, 잘못 선택하면 메서드가 바뀌거나 캐시 문제가 생긴다.

### 301 Moved Permanently

URL이 영구적으로 이동했다는 신호다. 브라우저와 검색 엔진 모두 캐시한다. 한 번 캐시되면 서버에 재요청을 보내지 않기 때문에, 나중에 되돌리기 어렵다.

쓰는 경우:
- HTTP → HTTPS 마이그레이션
- 구 도메인 → 신 도메인
- `/old-path` → `/new-path` (SEO 이전)

301을 잘못 설정하면 브라우저 캐시를 지워야 원상 복구된다. 개발 중에는 302를 쓰고, 배포 확인 후 301로 교체하는 게 안전하다.

### 302 Found

임시 이동이다. 브라우저가 캐시하지 않아 매번 서버에 확인한다.

쓰는 경우:
- A/B 테스트 중 일부 사용자를 다른 페이지로 보낼 때
- 로그인 후 원래 페이지로 돌려보낼 때
- 점검 페이지로 임시 전환

### 307 Temporary Redirect

302와 거의 같지만, 메서드를 유지한다. POST로 보낸 요청이 리디렉션되어도 GET이 아닌 POST로 재요청된다.

302는 오래된 브라우저에서 POST를 GET으로 바꿔버리는 경우가 있다. API 서버 이전 중에 POST 요청이 유지되어야 한다면 307을 써야 한다.

### 308 Permanent Redirect

301과 같은 영구 이동이지만, 307처럼 메서드를 유지한다.

쓰는 경우:
- API 버저닝에서 구 엔드포인트를 신 엔드포인트로 영구 이전
- POST, PUT, PATCH 요청이 유지되어야 하는 경우

## 쿼리스트링 유지 / 제거

### return에서 쿼리스트링

`return`에 URL을 명시하면 원래 쿼리스트링이 붙지 않는다.

```nginx
# 쿼리스트링 날아감
location /old {
    return 301 https://example.com/new;
}
# /old?foo=bar → https://example.com/new
```

쿼리스트링을 유지하려면 `$query_string` 또는 `$args`를 명시해야 한다.

```nginx
# 쿼리스트링 유지
location /old {
    return 301 https://example.com/new?$query_string;
}
# /old?foo=bar → https://example.com/new?foo=bar
```

`$request_uri`를 쓰면 경로와 쿼리스트링을 모두 포함한 원본 URI가 그대로 붙는다.

```nginx
# 경로 + 쿼리스트링 전체 유지
server {
    server_name old-domain.com;
    return 301 https://new-domain.com$request_uri;
}
```

### 쿼리스트링 제거

특정 파라미터만 제거할 때는 `rewrite`를 쓴다. `$uri?`에서 `?` 뒤에 아무것도 없으면 쿼리스트링이 제거된다.

```nginx
# utm 파라미터 포함 요청의 쿼리스트링 전체 제거
location / {
    if ($query_string ~* "utm_") {
        rewrite ^ $uri? permanent;
    }
}
```

전체 쿼리스트링 제거가 아니라 일부 파라미터만 제거하는 경우는 Nginx만으로는 복잡하다. Lua 모듈이나 애플리케이션 레이어에서 처리하는 편이 낫다.

### rewrite에서의 쿼리스트링

`rewrite`는 기본적으로 기존 쿼리스트링을 유지한다. 제거하려면 패턴 끝에 `?`를 붙인다.

```nginx
# 쿼리스트링 유지 (기본 동작)
rewrite ^/old/(.*)$ /new/$1 last;

# 쿼리스트링 제거
rewrite ^/old/(.*)$ /new/$1? last;
```

## 도메인 마이그레이션 redirect 처리

도메인을 이전할 때 가장 많이 하는 실수는 www 여부와 HTTPS를 한꺼번에 처리하지 않는 것이다. HTTP로 들어오는 요청, HTTPS로 들어오는 요청, www가 붙은 요청, 안 붙은 요청 — 네 가지 조합을 모두 잡아야 한다.

### 전형적인 마이그레이션 패턴

```nginx
# 구 도메인의 모든 요청을 신 도메인으로
server {
    listen 80;
    listen 443 ssl;
    server_name old-domain.com www.old-domain.com;

    ssl_certificate /etc/letsencrypt/live/old-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/old-domain.com/privkey.pem;

    return 301 https://new-domain.com$request_uri;
}
```

### www/non-www 통일

```nginx
# www → non-www
server {
    listen 80;
    listen 443 ssl;
    server_name www.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    return 301 https://example.com$request_uri;
}

# HTTP → HTTPS
server {
    listen 80;
    server_name example.com;

    return 301 https://example.com$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com;
    # 실제 처리
}
```

도메인 마이그레이션에서 구 도메인의 SSL 인증서 만료 시점을 주의해야 한다. HTTPS로 들어오는 요청은 인증서 핸드쉐이크를 먼저 하기 때문에, 인증서가 만료되면 301 리디렉션 자체를 처리할 수 없다. 마이그레이션 기간 동안은 두 도메인의 인증서를 모두 유지해야 한다.

## rewrite 플래그 동작 차이

`rewrite` 디렉티브는 네 가지 플래그를 지원한다. 플래그 없이 쓰면 생각대로 동작하지 않는 경우가 많다.

### last

URI를 바꾼 뒤 location 블록 매칭을 처음부터 다시 시작한다. 현재 location 블록의 남은 설정은 무시된다.

```nginx
location /api {
    rewrite ^/api/v1/(.*)$ /api/v2/$1 last;
    proxy_pass http://legacy-backend;  # 이 줄은 실행 안 됨
}

location /api/v2 {
    proxy_pass http://new-backend;
}
```

`/api/v1/users` 요청이 들어오면 `/api/v2/users`로 바뀐 뒤 location 매칭을 다시 한다. `/api/v2` location이 잡아서 `new-backend`로 프록시된다.

### break

URI를 바꾼 뒤 location 재매칭 없이 현재 location 블록에서 계속 처리된다.

```nginx
location /files {
    rewrite ^/files/(.*)$ /data/$1 break;
    root /var/www;
    # /var/www/data/... 에서 파일을 찾음
}
```

`break`는 같은 location 안에서 경로만 바꾸고 계속 처리하고 싶을 때 쓴다.

### redirect / permanent

`redirect`는 302, `permanent`는 301 리디렉션을 클라이언트에게 보낸다.

```nginx
rewrite ^/old$ /new redirect;    # 302
rewrite ^/old$ /new permanent;   # 301
```

이 두 플래그는 `return 301/302`와 동작이 같다. 단순 리디렉션이라면 `return`을 쓰는 게 더 명확하다.

### last vs break — proxy_pass와 함께 쓸 때

`last`와 `break`의 차이가 가장 크게 드러나는 상황은 `proxy_pass`와 함께 쓸 때다.

```nginx
location / {
    rewrite ^/v1/(.*)$ /v2/$1 last;
    proxy_pass http://backend;  # last면 이 줄 실행 안 됨
}
```

`last`는 location 재매칭을 하기 때문에 `proxy_pass`가 실행되지 않는다. URI를 바꾼 뒤 같은 `proxy_pass`로 보내려면 `break`를 써야 한다.

```nginx
location / {
    rewrite ^/v1/(.*)$ /v2/$1 break;
    proxy_pass http://backend;  # /v2/... URI로 프록시됨
}
```

## 무한 rewrite 루프

무한 루프는 Nginx가 URI를 계속 바꾸다 "rewrite or internal redirection cycle" 에러를 내는 상황이다. 기본적으로 내부 리디렉션이 10회를 넘으면 500 에러를 반환한다.

### 원인

**패턴이 변환된 URI에도 매칭될 때**

```nginx
# 루프 발생
location / {
    rewrite ^/(.*)$ /$1/index last;
}
# /foo → /foo/index → /foo/index/index → ...
```

**last 플래그로 자기 자신으로 돌아오는 경우**

```nginx
location /app {
    rewrite ^/app/(.*)$ /app/$1 last;  # 자기 자신으로 돌아옴
}
```

변환 전후 URI가 같으면 같은 location에 계속 떨어진다.

**if 블록 안의 rewrite**

```nginx
location / {
    if ($uri !~ "^/login") {
        rewrite ^ /login last;
    }
}
```

`/login`이 아닌 요청은 `/login`으로 바뀌고, `/login`으로 바뀐 요청이 다시 location `/`에 매칭되어 `if` 조건을 평가한다. 조건이 `false`가 되어 루프는 끊기지만, 의도치 않은 요청 흐름이 생긴다. `if` 안에서 `last`가 아닌 `break`를 쓰거나, `return`으로 교체해야 한다.

### 방지 방법

**변환 전후 URI 접두사를 다르게 설계**

```nginx
# 루프 없음: /app/* → /v2/*
location /app {
    rewrite ^/app/(.*)$ /v2/$1 last;
}

location /v2 {
    proxy_pass http://backend;
}
```

변환된 URI가 원래 location에 다시 매칭되지 않도록 경로 접두사를 바꿔야 한다.

**break 사용**

```nginx
location /app {
    rewrite ^/app/(.*)$ /static/$1 break;
    root /var/www;
}
```

`break`는 location 재매칭을 하지 않기 때문에 루프가 발생하지 않는다.

**if 대신 별도 location 분리**

```nginx
# if 대신 별도 location
location = /login {
    # 로그인 페이지 처리
}

location / {
    auth_request /auth;
}
```

Nginx에서 `if`는 기대와 다르게 동작하는 경우가 많다. 특히 `if` 블록 안에서 `rewrite`와 `proxy_pass`를 섞으면 예상 밖의 동작을 한다. "if is evil"이라는 Nginx 공식 문서의 경고가 괜히 있는 게 아니다.

### 디버깅

에러 로그를 debug 레벨로 설정하면 rewrite 처리 흐름을 볼 수 있다.

```nginx
error_log /var/log/nginx/error.log debug;
```

로그에서 "rewrite or internal redirection cycle" 메시지가 보이면 무한 루프다. 메시지 앞 줄에 어느 location에서 rewrite가 발생했는지 나오기 때문에, 루프 진입점을 찾는 데 도움이 된다. 운영 환경에서는 debug 레벨 로그가 매우 많이 생성되므로 확인 후 반드시 원복해야 한다.
