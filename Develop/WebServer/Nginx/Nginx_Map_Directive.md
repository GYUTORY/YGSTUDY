---
title: "Nginx map 지시어 심화"
tags: [web-server]
updated: 2026-07-20
---

# Nginx map 지시어 심화

`Location_Matching_Deep_Dive.md`의 `if is evil` 항목에서 `map`을 대안으로 언급했지만 코드 예제 없이 끝났다. 이 문서는 그 후속이다. `map`으로 처리할 수 있는 패턴, `geo`로 IP 기반 라우팅, `split_clients`로 트래픽 분산까지 실제 운영에서 쓰는 구체적인 형태를 다룬다.

## map 지시어 기본 구조

`map`은 `http` 블록에 정의하고 `server`나 `location`에서 변수로 참조하는 방식이다. 평가는 lazy하게 일어난다. 요청마다 map 표현식을 실행하는 게 아니라 변수를 실제로 참조하는 순간 한 번 계산한다.

```nginx
http {
    map $http_x_canary $backend {
        default  "stable";
        "1"      "canary";
        "true"   "canary";
    }

    upstream stable {
        server 10.0.0.1:8080;
    }

    upstream canary {
        server 10.0.0.2:8080;
    }

    server {
        location /api/ {
            proxy_pass http://$backend;
        }
    }
}
```

`map $소스변수 $결과변수`가 선언부고, 블록 안에는 소스 값 → 결과 값 매핑이 들어간다. `default`는 일치하는 항목이 없을 때 폴백값이다.

`if` 블록으로 같은 것을 구현하면 `proxy_pass`를 `if` 안에 넣게 되는데, 이 경우 암묵적 location 분리가 일어나서 바깥 location의 지시어 상속이 끊어진다. `map`은 변수만 설정하고 `proxy_pass`는 바깥에 두므로 그 문제가 없다.

### 매칭 방식

값에는 문자열 외에 정규식도 쓸 수 있다.

```nginx
map $http_user_agent $is_bot {
    default          0;
    ~*Googlebot      1;
    ~*Bingbot        1;
    ~*Slurp          1;
}
```

`~`는 대소문자 구분, `~*`는 대소문자 무시 정규식이다. 문자열 매칭이 먼저 평가되고, 이후 정규식이 등장 순서대로 평가된다. 여러 정규식이 일치할 경우 처음 일치한 것을 쓴다.

```nginx
map $http_accept_language $lang {
    default     "en";
    ~^ko        "ko";
    ~^ja        "ja";
    ~^zh        "zh";
}
```

`include`로 외부 파일에서 매핑 목록을 불러올 수 있다. 목록이 길어지면 관리하기 좋다.

```nginx
map $remote_addr $blocked {
    default 0;
    include /etc/nginx/blocked_ips.map;
}
```

`blocked_ips.map` 파일 형식.

```text
192.168.1.100  1;
10.0.0.50      1;
```

---

## if 대신 map을 써야 하는 패턴

`if`로 구현하면 동작이 깨지는 패턴들이다. 운영에서 실제로 봤던 것들만 정리했다.

### 헤더 기반 백엔드 분기

```nginx
# 안 되는 방법 - if + proxy_pass 조합
location /api/ {
    if ($http_x_env = "staging") {
        proxy_pass http://staging_backend;  # 동작 불안정
    }
    proxy_pass http://prod_backend;
}

# 되는 방법 - map으로 변수, proxy_pass는 바깥
map $http_x_env $target_backend {
    default    "prod_backend";
    "staging"  "staging_backend";
}

server {
    location /api/ {
        proxy_pass http://$target_backend;
    }
}
```

### 복수 조건 조합

단일 변수로 처리 못하는 경우, map을 중첩하거나 변수를 조합하면 된다.

```nginx
# 두 변수를 하나의 문자열로 연결한 뒤 map 적용
map "$http_x_feature:$http_x_region" $routing_key {
    default              "default_backend";
    "v2:kr"             "v2_kr_backend";
    "v2:us"             "v2_us_backend";
    ~^"v2:"             "v2_default_backend";
    ~^":kr"             "default_kr_backend";
}

server {
    location /api/ {
        proxy_pass http://$routing_key;
    }
}
```

`$http_x_feature:$http_x_region`처럼 변수를 이어 붙인 문자열 자체를 소스 변수로 쓰는 방식이다. 복잡한 조건 분기를 `if` 없이 처리할 때 쓴다.

### add_header 분기 문제 해결

`if` 안에 `add_header`를 두면 바깥의 `add_header`가 사라진다. map 변수로 값을 뽑고 `add_header`는 바깥에 두면 해결된다.

```nginx
map $http_origin $cors_origin {
    default "";
    ~^https://(.+\.)?example\.com$ $http_origin;
    ~^https://(.+\.)?partner\.io$  $http_origin;
}

server {
    location /api/ {
        add_header Access-Control-Allow-Origin  $cors_origin;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header X-Content-Type-Options       "nosniff";
        proxy_pass http://backend;
    }
}
```

`$cors_origin`이 빈 문자열이면 `Access-Control-Allow-Origin` 헤더가 비어서 나가는 게 문제가 될 수 있다. `if ($cors_origin)` 조건 없이 쓸 때는 헤더 값이 빈 문자열인 경우 헤더 자체가 출력되지 않는 nginx의 동작에 기대게 된다. 실제로는 빈 문자열 헤더가 나가는 버전이 있기 때문에 허용하지 않는 origin에서 빈 헤더를 받는 상황을 클라이언트가 어떻게 처리하는지 확인해야 한다.

---

## geo 모듈로 IP 기반 라우팅

`ngx_http_geo_module`은 별도 설치 없이 nginx 기본 빌드에 포함되어 있다. `map`과 비슷하지만 소스 변수가 IP 주소로 고정되어 있고 CIDR 표기를 지원한다.

```nginx
geo $remote_addr $client_zone {
    default          "public";
    10.0.0.0/8       "internal";
    172.16.0.0/12    "internal";
    192.168.0.0/16   "internal";
    203.0.113.5      "partner";
}

upstream internal_backend {
    server 10.0.0.10:8080;
}

upstream public_backend {
    server 10.0.0.20:8080;
}

upstream partner_backend {
    server 10.0.0.30:8080;
}

map $client_zone $backend_pool {
    default    "public_backend";
    "internal" "internal_backend";
    "partner"  "partner_backend";
}

server {
    location /api/ {
        proxy_pass http://$backend_pool;
    }
}
```

`geo`를 직접 upstream 이름에 연결하려면 중간에 `map`을 하나 더 두는 식으로 구성한다.

### X-Forwarded-For 처리

로드밸런서 뒤에 있는 경우 `$remote_addr`이 LB의 IP가 되어서 geo가 의미 없어진다. `geo` 지시어에 소스 주소를 명시할 수 있다.

```nginx
geo $http_x_real_ip $client_zone {
    default    "public";
    10.0.0.0/8 "internal";
}
```

`$http_x_real_ip`는 LB가 설정해준 원본 IP를 보는 변수다. 신뢰하는 LB가 헤더를 조작할 수 있다는 전제 아래서만 써야 한다. 외부 사용자가 직접 `X-Real-IP` 헤더를 설정할 수 없는 구조인지 확인이 먼저다.

`set_real_ip_from`과 `real_ip_header`를 조합하는 방식도 있다.

```nginx
set_real_ip_from 10.0.0.0/8;
real_ip_header   X-Forwarded-For;
real_ip_recursive on;
```

이렇게 설정하면 `$remote_addr` 자체가 원본 IP로 바뀐다. geo를 별도 변수 없이 쓸 수 있다.

### geo로 접근 제어

백엔드 분기가 아닌 접근 차단용으로도 자주 쓴다.

```nginx
geo $blocked_ip {
    default         0;
    192.0.2.0/24    1;
    198.51.100.5    1;
}

server {
    location / {
        if ($blocked_ip) {
            return 403;
        }
        proxy_pass http://backend;
    }
}
```

여기서는 `if ($blocked_ip)` 형태를 쓰는 게 안전하다. `return` 지시어만 쓰고 `proxy_pass`는 바깥에 있기 때문에 `if is evil`이 말하는 문제 상황이 아니다.

---

## split_clients로 트래픽 분산

`ngx_http_split_clients_module`은 A/B 테스트나 카나리 배포에서 요청을 비율로 나눌 때 쓴다. MurmurHash2로 키를 해시해서 0~100% 범위에 매핑한다.

```nginx
split_clients "${remote_addr}${http_user_agent}" $variant {
    20%    "canary";
    *      "stable";
}

upstream stable {
    server 10.0.0.1:8080;
}

upstream canary {
    server 10.0.0.2:8080;
}

server {
    location /api/ {
        proxy_pass http://$variant;
    }
}
```

`20%`는 해시 공간의 20%를 카나리에, 나머지는 stable에 할당한다. `*`은 나머지 전체를 의미한다. 퍼센트 합이 100을 초과하면 설정 로드 시 에러가 난다.

### 해시 키 선택

키 구성이 분산의 일관성을 결정한다.

```nginx
# 같은 IP에서 온 요청은 항상 같은 variant
split_clients "$remote_addr" $variant { ... }

# 요청마다 다를 수 있음 (세션 없는 경우 일관성 없음)
split_clients "${remote_addr}${request_uri}" $variant { ... }

# 쿠키 기반 (로그인 사용자에게 일관성 필요한 경우)
split_clients "$cookie_session_id" $variant { ... }

# User-Agent 포함하면 같은 IP도 다른 variant 가능
split_clients "${remote_addr}${http_user_agent}" $variant { ... }
```

운영에서 카나리를 쓸 때 가장 중요한 건 같은 사용자가 요청마다 다른 variant를 받는 상황이다. 로그인된 사용자면 세션 쿠키를 키로 쓰고, 아니면 IP를 기반으로 하는 게 낫다.

### 비율 조정

nginx reload 없이 비율을 바꿀 수는 없다. 설정 파일을 바꾸고 `nginx -s reload`를 해야 한다. 비율 조정이 잦은 경우 Lua 모듈이나 외부 서비스를 쓰는 방향을 고려해야 한다.

```nginx
# 단계적 카나리 배포 예시
# 초기
split_clients "$remote_addr" $variant {
    5%   "canary";
    *    "stable";
}

# 검증 후 확대
split_clients "$remote_addr" $variant {
    50%  "canary";
    *    "stable";
}
```

---

## $request_uri, $host, $http_* 변수 활용

nginx 내장 변수를 map 소스로 쓸 때 각 변수의 정확한 의미를 모르면 의도와 다른 결과가 나온다.

### $uri vs $request_uri

```nginx
# $request_uri: 원본 그대로 (query string 포함, 디코딩 안 됨)
# /api/search?q=hello%20world → /api/search?q=hello%20world

# $uri: rewrite 이후의 경로 (query string 없음, 디코딩됨)
# /api/search?q=hello%20world → /api/search
```

map 소스로 `$uri`를 쓰면 query string이 없는 경로만 비교한다. query string 포함 매칭이 필요하면 `$request_uri`를 쓴다.

```nginx
map $request_uri $cache_bypass {
    default       0;
    ~\?nocache    1;
    ~^/admin/     1;
}

server {
    location / {
        proxy_cache_bypass $cache_bypass;
        proxy_pass http://backend;
    }
}
```

### $host 기반 멀티 도메인 라우팅

```nginx
map $host $site_root {
    default              "/var/www/default";
    "example.com"        "/var/www/main";
    "blog.example.com"   "/var/www/blog";
    "api.example.com"    "/var/www/api";
    ~^(.+)\.example\.com "/var/www/subdomains/$1";
}

server {
    server_name *.example.com example.com;

    location / {
        root $site_root;
        try_files $uri $uri/ =404;
    }
}
```

`$host`는 request의 `Host` 헤더 값이다. 포트 번호가 포함된 경우에는 `$http_host`를 쓴다. `$server_name`과 혼동하지 말 것. `$server_name`은 server 블록의 첫 번째 server_name 지시어 값이다.

### 멀티 도메인을 backend로 연결

```nginx
map $host $upstream {
    default          "default_backend";
    "api.service.io" "api_backend";
    "gw.service.io"  "gateway_backend";
    ~^admin\.         "admin_backend";
}

server {
    server_name _;

    location / {
        proxy_pass http://$upstream;
        proxy_set_header Host $host;
    }
}
```

`proxy_set_header Host $host`를 빠뜨리면 백엔드가 `Host` 헤더로 `$upstream` (예: `api_backend`)을 받는다. 백엔드가 가상 호스트 기반이면 이 헤더를 보고 잘못된 응답을 줄 수 있다.

### $http_* 변수

요청 헤더는 `$http_` 접두사로 접근한다. 헤더 이름의 대시(`-`)는 언더스코어(`_`)로 바꾸고 소문자로 읽는다.

```text
X-Request-ID   → $http_x_request_id
Authorization  → $http_authorization
Content-Type   → $http_content_type
Accept         → $http_accept
```

```nginx
map $http_authorization $auth_type {
    default         "none";
    ~^Bearer\s      "jwt";
    ~^Basic\s       "basic";
    ~^ApiKey\s      "apikey";
}

map $auth_type $auth_backend {
    default   "public_backend";
    "jwt"     "jwt_backend";
    "basic"   "basic_backend";
    "apikey"  "apikey_backend";
}

server {
    location /api/ {
        proxy_pass http://$auth_backend;
    }
}
```

map을 두 단계로 나눠서 첫 번째 map이 인증 타입을 분류하고 두 번째 map이 backend를 선택한다. 하나의 map에 모든 로직을 넣으면 정규식 패턴이 복잡해진다.

---

## 실전 패턴

### 카나리 + 특정 사용자 강제 라우팅 조합

```nginx
# 특정 쿠키로 강제 지정, 없으면 split_clients 결과 사용
split_clients "$remote_addr" $split_variant {
    10%  "canary";
    *    "stable";
}

map $cookie_force_variant $variant {
    default  $split_variant;
    "canary" "canary";
    "stable" "stable";
}

server {
    location /api/ {
        proxy_pass http://$variant;
        add_header X-Variant $variant;
    }
}
```

`$cookie_force_variant`가 있으면 그걸 우선하고 없으면 split_clients 결과를 쓴다. QA가 특정 variant에 고정해서 테스트할 때 쿠키를 직접 설정하면 된다.

### 유지보수 모드 전환

```nginx
geo $maintenance_bypass {
    default    0;
    10.0.0.0/8 1;  # 내부 IP는 유지보수 무시
}

map $maintenance_bypass $upstream {
    default "maintenance_page";
    1       "real_backend";
}

# 유지보수 모드 여부는 파일로 제어
map $uri $maintenance_active {
    default 0;
}

server {
    set $maintenance 0;
    # 파일 존재 여부로 유지보수 모드 판단
    if (-f /etc/nginx/maintenance.flag) {
        set $maintenance 1;
    }

    location / {
        if ($maintenance = 1) {
            return 503;
        }
        proxy_pass http://real_backend;
    }

    error_page 503 /maintenance.html;
    location = /maintenance.html {
        root /var/www;
        internal;
    }
}
```

여기서 `if (-f ...)` 형태는 파일 존재 여부 체크만 하고 `return`만 실행하므로 `if is evil`의 문제 패턴에 해당하지 않는다. 내부 IP는 geo로 판별해서 유지보수 중에도 통과시킨다.

### rate limiting 예외 처리

```nginx
geo $rate_limit_key {
    default          $binary_remote_addr;
    10.0.0.0/8       "";  # 내부 IP는 rate limit 제외
    192.168.0.0/16   "";
}

limit_req_zone $rate_limit_key zone=api:10m rate=100r/m;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }
}
```

`limit_req_zone`의 키 변수에 빈 문자열이 들어오면 rate limit이 적용되지 않는다. 내부 서비스 간 트래픽을 rate limit에서 제외할 때 이 방법을 쓴다.

---

## 주의사항

**map 정의 위치**: `http` 블록에만 정의할 수 있다. `server`나 `location` 안에 두면 설정 로드 에러가 난다.

**변수 참조 전 선언**: map으로 정의한 변수를 upstream 이름으로 쓸 때 해당 upstream이 실제로 정의되어 있어야 한다. `$backend`가 `"canary_backend"`인데 upstream 이름이 다르면 502가 난다.

**정규식 성능**: map 블록에 정규식이 많으면 첫 참조 시 컴파일 비용이 있다. 수백 개 정규식을 한 map에 넣는 경우 nginx 시작 시간이 늘어나고 변수 참조 시마다 비용이 발생한다. 이 규모라면 lua 모듈이나 외부 설정 시스템이 맞다.

**split_clients 재현성**: 같은 키로 같은 variant가 나오는 건 MurmurHash2 결과가 동일하기 때문이다. nginx 버전이 바뀌어도 알고리즘이 바뀌지 않는 한 일관성이 유지된다. 다만 비율 자체를 바꾸면 이전에 stable을 받던 사용자가 canary로 이동할 수 있다.

**geo vs map 선택 기준**: 소스가 IP 주소고 CIDR 범위 매칭이 필요하면 geo, 그 외에는 map을 쓴다. geo도 내부적으로 Patricia trie를 써서 CIDR 매칭이 빠르다. 단순 IP 문자열 비교는 map에서 정규식으로도 할 수 있지만 CIDR 표기는 geo만 지원한다.
