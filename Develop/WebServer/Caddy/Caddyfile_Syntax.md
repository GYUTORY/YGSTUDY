---
title: Caddyfile 문법 심화
tags: [webserver, caddy, caddyfile, syntax, matcher, snippet, placeholder, route, handle]
updated: 2026-05-03
---

# Caddyfile 문법 심화

Caddyfile이 단순해 보이는 건 처음 몇 줄까지다. `example.com { reverse_proxy localhost:3000 }` 한 줄짜리 설정에서 벗어나는 순간 매처는 어떻게 작동하는지, 디렉티브를 적은 순서대로 실행되는 게 맞는지, `handle`과 `handle_path`는 뭐가 다른지 같은 의문이 한꺼번에 쏟아진다. 이 문서는 그 의문들을 한 번에 정리한다. Caddy를 한두 번 만져본 사람이 운영 단계로 넘어갈 때 가장 발목을 잡는 부분이다.

## Caddyfile의 기본 구조

Caddyfile은 크게 세 영역으로 나뉜다. 전역 옵션 블록, snippet 정의, 그리고 사이트 블록이다. 전역 옵션 블록은 파일 맨 위에 한 번만 등장하고 중괄호로 감싼 익명 블록이다. snippet은 `(name)` 형태로 정의하고 `import name`으로 불러 쓴다. 사이트 블록은 호스트명(또는 주소)으로 시작해서 그 사이트에 적용할 디렉티브를 담는다.

```caddy
{
    # 전역 옵션 블록
    email admin@example.com
    auto_https on
    admin localhost:2019
    log {
        output file /var/log/caddy/access.log
        format json
    }
}

(common_headers) {
    # snippet 정의
    header {
        Strict-Transport-Security "max-age=31536000;"
        X-Content-Type-Options nosniff
    }
}

example.com {
    # 사이트 블록
    import common_headers
    reverse_proxy localhost:3000
}
```

여기서 헷갈리기 쉬운 게, 전역 옵션 블록은 사이트 블록과 똑같이 `{`로 열리지만 앞에 호스트명이 없다는 점이다. 호스트명 없이 중괄호만 등장하면 Caddy는 그걸 전역 블록으로 해석한다. 그래서 전역 블록은 반드시 파일 가장 위에 있어야 하고, 파일에 단 하나만 존재할 수 있다. 두 번 쓰면 파싱 에러가 나는 게 아니라 두 번째가 조용히 무시되거나 충돌이 나서 디버깅이 어려워진다.

## 사이트 블록의 주소 표기

사이트 블록의 첫 줄은 단순한 호스트명이 아니라 "주소(address)"다. 호스트명, 스킴, 포트를 조합해서 적을 수 있고, 콤마로 여러 주소를 묶을 수도 있다.

```caddy
# 가장 단순한 형태 - HTTPS 자동
example.com {
    respond "hello"
}

# 명시적 스킴과 포트
http://example.com:8080 {
    respond "plain http on 8080"
}

# 와일드카드
*.example.com {
    respond "subdomain"
}

# 여러 호스트 묶기
example.com, www.example.com, api.example.com {
    reverse_proxy localhost:3000
}

# 주소만으로 (호스트명 없이)
:8080 {
    respond "any host on port 8080"
}
```

`example.com`처럼 스킴이 없으면 Caddy는 자동으로 HTTPS(443)로 리스닝하고, 80 포트에서 HTTPS로 리다이렉트한다. `http://`를 붙이면 자동 HTTPS가 꺼지면서 평문으로 동작한다. 이 차이가 인증서 자동 발급이 켜질지 말지를 결정하기 때문에 `http://`를 함부로 붙이면 안 된다. 내부망용이라고 생각해서 `http://internal.example.com`으로 적었다가 정작 운영에서 HTTPS가 필요해지면 다시 떼야 한다.

`:8080`처럼 포트만 적으면 호스트명 매칭 없이 그 포트로 들어오는 모든 요청을 처리한다. 헬스체크 엔드포인트나 내부 메트릭 노출에 자주 쓴다. 단, 이런 사이트 블록은 자동 HTTPS가 적용되지 않는다.

## 디렉티브 순서의 함정

Caddyfile에서 가장 헷갈리는 부분이 디렉티브 순서다. 적은 순서대로 실행되지 않는다는 사실을 처음 마주치면 당황한다.

```caddy
example.com {
    reverse_proxy localhost:3000
    redir /old /new permanent
    header X-Custom "hello"
}
```

이 설정에서 `/old`로 요청이 들어오면 어떻게 될까. 적힌 순서대로라면 `reverse_proxy`가 먼저 실행돼서 백엔드로 갈 것 같지만, 실제로는 `redir`이 먼저 실행돼서 `/new`로 리다이렉트된다. Caddy가 디렉티브마다 내부적으로 정해진 우선순위 번호를 가지고 있기 때문이다. 사용자가 적은 순서가 아니라 그 우선순위 순서대로 미들웨어 체인이 만들어진다.

대략적인 순서는 이렇다.

1. `tracing`, `map` (관측·변환)
2. `root` (파일 루트 설정)
3. `header` (응답 헤더 조작 - 후처리지만 미리 등록)
4. `redir` (리다이렉트)
5. `rewrite`, `uri` (URL 변경)
6. `basicauth`, `forward_auth` (인증)
7. `request_body` (요청 바디 처리)
8. `encode` (응답 압축)
9. `handle`, `handle_path`, `route` (핸들러 그룹)
10. `file_server`, `reverse_proxy`, `respond`, `php_fastcgi` (최종 응답)

이 순서를 외우려고 하지 말고, "헷갈리면 `route` 블록으로 감싼다"라고 기억하면 된다. 그래야 적은 순서대로 동작한다. 뒤에서 자세히 다룬다.

이 자동 정렬 동작 때문에 발생하는 흔한 사고 하나. `header`로 응답 헤더를 추가했는데 `reverse_proxy`가 백엔드 응답 헤더를 그대로 가져와버려서 내가 적은 헤더가 안 보인다고 느낄 수 있다. 실제로는 둘 다 적용되지만, `header`는 응답 단계에서 후처리하므로 백엔드가 같은 이름의 헤더를 내려보내면 그쪽이 우선될 수 있다. `header_up`/`header_down`이 `reverse_proxy` 안에 있는 이유가 이거다.

## 매처: 어떤 요청에 적용할지 정하기

매처(matcher)는 디렉티브를 어떤 요청에만 적용할지 거르는 조건이다. Caddyfile에는 세 종류의 매처가 있다. 와일드카드(`*`), 경로 매처(`/path`), 그리고 named matcher(`@name`)다.

```caddy
example.com {
    # 와일드카드: 모든 요청
    header * Cache-Control "no-cache"

    # 경로 매처: 특정 경로 prefix
    header /static/* Cache-Control "max-age=31536000"

    # named matcher: 복합 조건
    @api {
        path /api/*
        method POST
        header Content-Type application/json
    }
    handle @api {
        reverse_proxy localhost:3000
    }
}
```

경로 매처는 디렉티브의 두 번째 인수 자리에 슬래시로 시작하는 문자열이 오면 자동으로 인식된다. 즉, `header /static/* Cache-Control "max-age=31536000"`은 "경로가 `/static/*`인 요청에만 이 header를 적용한다"라는 뜻이다. 와일드카드 `*`는 경로 매처와 자리가 같지만 모든 요청을 의미한다.

함정 하나. 경로 매처는 prefix 매칭이 아니라 정확 매칭에 가깝다. `/api`만 적으면 정확히 `/api`만 매치되고, `/api/users`는 매치되지 않는다. prefix처럼 쓰려면 `/api*` 또는 `/api/*`로 적어야 한다. `/api*`는 `/api`와 `/api/users`를 모두 잡지만, `/api/*`는 `/api/users`만 잡고 `/api` 자체는 못 잡는다. 이 미묘한 차이로 라우팅이 한 단계 어긋나는 경우가 많다.

### named matcher의 종류

named matcher는 `@name { ... }` 블록 안에 여러 조건을 적어서 AND로 묶는다. 자주 쓰는 매처 종류는 다음과 같다.

```caddy
example.com {
    # host - Host 헤더 매칭 (서브도메인 분기)
    @api host api.example.com
    handle @api {
        reverse_proxy localhost:3001
    }

    # path - 경로 매칭 (여러 패턴 OR)
    @assets path /static/* /images/* /css/*
    handle @assets {
        root * /var/www
        file_server
    }

    # path_regexp - 정규식 경로 매칭
    @uuid path_regexp ^/items/[a-f0-9-]{36}$
    handle @uuid {
        reverse_proxy localhost:3002
    }

    # method - HTTP 메서드
    @write method POST PUT DELETE PATCH
    handle @write {
        reverse_proxy localhost:3003
    }

    # header - 요청 헤더 매칭
    @json header Content-Type application/json
    handle @json {
        reverse_proxy localhost:3004
    }

    # query - 쿼리 파라미터
    @debug query debug=true
    handle @debug {
        reverse_proxy localhost:3005
    }

    # protocol - HTTP 버전, TLS 등
    @http2 protocol http/2
    handle @http2 {
        respond "you are on h2"
    }

    # remote_ip - 클라이언트 IP CIDR
    @internal remote_ip 10.0.0.0/8 192.168.0.0/16
    handle @internal {
        reverse_proxy localhost:3006
    }

    # not - 부정 조건
    @notapi not path /api/*
    handle @notapi {
        file_server
    }

    # expression - CEL 표현식
    @afterhours expression `{time.now.hour} >= 22 || {time.now.hour} < 6`
    handle @afterhours {
        respond "service unavailable" 503
    }
}
```

매처를 한 줄로 쓰는 단축형도 있다. `@api host api.example.com`처럼 매처 종류와 인수를 같은 줄에 적으면 블록을 열 필요가 없다. 조건이 하나일 때 깔끔하다.

### expression 매처와 CEL

`expression` 매처는 CEL(Common Expression Language)로 임의의 조건을 평가한다. 다른 매처로 표현이 안 되는 복잡한 조건을 처리할 때 쓴다.

```caddy
example.com {
    @blocked expression `{header.User-Agent}.contains("BadBot") && {path}.startsWith("/admin")`
    handle @blocked {
        respond 403
    }

    @cookie_test expression `{cookie.session} != "" && {query.test} == "1"`
    handle @cookie_test {
        reverse_proxy localhost:3000
    }
}
```

CEL 표현식 안에서는 placeholder를 `{...}` 그대로 쓸 수 있고, 문자열 메서드(`contains`, `startsWith`, `endsWith`, `matches`)와 비교 연산자(`==`, `!=`, `>=`, `&&`, `||`)를 조합할 수 있다. 정규식 매칭은 `matches`를 쓴다. expression이 강력한 만큼 매 요청마다 평가 비용이 들기 때문에, 다른 매처로 표현 가능한 조건은 그쪽을 쓰는 게 낫다.

### named matcher 재사용

같은 매처를 여러 디렉티브에 쓰고 싶으면 named matcher로 정의해두고 참조한다.

```caddy
example.com {
    @api path /api/*

    handle @api {
        reverse_proxy localhost:3000
    }

    log @api {
        output file /var/log/caddy/api.log
    }

    header @api X-API-Version "v2"
}
```

매처를 한 번만 정의하고 여러 디렉티브에서 재사용할 수 있다. 매처 정의가 길어지면 더 가치가 커진다.

## handle vs handle_path 차이

이 둘의 차이를 모르면 라우팅이 미묘하게 어긋난다. 자주 마주치는 함정이다.

`handle`은 요청 경로를 그대로 내부 핸들러에 전달한다. `handle_path`는 매처에서 매치된 prefix를 잘라낸 뒤 전달한다.

```caddy
example.com {
    # handle: 경로 그대로
    handle /api/* {
        reverse_proxy localhost:3000
        # 백엔드는 /api/users 그대로 받음
    }

    # handle_path: prefix 제거 후 전달
    handle_path /api/* {
        reverse_proxy localhost:3000
        # 백엔드는 /users만 받음 (/api 잘림)
    }
}
```

언제 어떤 걸 쓰느냐는 백엔드가 그 prefix를 알고 있느냐로 결정된다. 백엔드 라우터가 `/api/users`로 등록돼 있으면 `handle`을 쓴다. 백엔드는 자기가 `/users`만 안다고 생각하고, prefix는 Caddy에서 떼주길 원하면 `handle_path`를 쓴다. 마이크로서비스에서 게이트웨이 역할을 할 때 후자가 많다.

`handle_path`는 매처가 path 형태일 때만 의미가 있다. host 매처에는 잘라낼 prefix가 없으니 의미가 없고, path가 정확 매칭이거나 단순 prefix가 아니면 자르는 동작이 모호해진다. 그래서 `handle_path /api/*` 같은 단순한 형태에서만 쓰는 게 안전하다.

또 하나, `handle`(과 `handle_path`)은 첫 매치만 실행되는 mutually exclusive 핸들러다. 같은 사이트 블록에 여러 `handle`을 적으면 그 중 하나만 실행되고 나머지는 건너뛴다. 이 점이 다음에 다룰 `route`와 결정적으로 다르다.

```caddy
example.com {
    handle /api/* {
        reverse_proxy localhost:3000
    }
    handle /admin/* {
        reverse_proxy localhost:3001
    }
    handle {
        # 위 두 매처에 안 걸린 모든 요청
        file_server
    }
}
```

`handle` 끼리는 적힌 순서대로 매칭을 시도하다가 첫 매치에서 멈춘다. 마지막에 매처 없는 `handle`을 두면 fallback이 된다. switch-case를 떠올리면 정확하다.

## route 블록으로 순서 강제하기

앞에서 언급한 디렉티브 자동 정렬을 무시하고 적은 순서대로 실행하고 싶을 때 `route`를 쓴다.

```caddy
example.com {
    route {
        rewrite * /index.html
        reverse_proxy localhost:3000
    }
}
```

`route` 블록 안에서는 디렉티브가 적힌 순서대로 미들웨어 체인이 만들어진다. SPA처럼 모든 경로를 `/index.html`로 rewrite하고 그걸 백엔드로 보내는 패턴에서 자주 쓴다. `route` 없이 똑같이 적으면 `rewrite`가 자동 정렬에 따라 어디서 실행될지 보장되지 않는다.

`handle`과 `route`의 차이를 정리하면 이렇다. `handle`은 매처에 따라 분기하는 switch-case 같은 것이고, 매처별로 정확히 하나만 실행된다. `route`는 그냥 미들웨어를 적은 순서대로 줄세우는 것이고, 모든 미들웨어가 차례로 실행된다(하나가 응답을 만들면 거기서 끝나지만).

실무에서는 둘을 섞어 쓴다. `handle`로 큰 분기를 하고, 각 `handle` 내부에서 순서가 중요한 디렉티브가 있으면 `route`로 감싼다.

```caddy
example.com {
    handle /api/* {
        route {
            rewrite * {http.request.uri.path}
            header X-API-Gateway "caddy"
            reverse_proxy localhost:3000
        }
    }
    handle {
        file_server
    }
}
```

## snippet과 import

같은 설정을 여러 사이트 블록에 반복해서 적게 되는 경우가 생긴다. 보안 헤더, 로깅 설정, 공통 미들웨어 같은 것들이다. snippet으로 묶어두면 한 곳에서 관리할 수 있다.

```caddy
(security_headers) {
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}

(json_logging) {
    log {
        output file /var/log/caddy/{args.0}.log
        format json
    }
}

example.com {
    import security_headers
    import json_logging example
    reverse_proxy localhost:3000
}

api.example.com {
    import security_headers
    import json_logging api
    reverse_proxy localhost:3001
}
```

snippet은 `(name)` 형태로 정의하고 `import name`으로 불러온다. 인수를 넘길 수 있는데, snippet 안에서 `{args.0}`, `{args.1}`로 받는다. 위 예제에서 `import json_logging example`이 호출되면 snippet 내부의 `{args.0}`이 `example`로 치환돼서 `/var/log/caddy/example.log`가 된다.

`import`는 다른 파일을 포함시키는 용도로도 쓴다.

```caddy
import /etc/caddy/sites/*.caddy
```

이렇게 쓰면 해당 디렉토리의 모든 `.caddy` 파일을 합친다. 사이트가 많아지면 도메인별로 파일을 쪼개고 main Caddyfile에서 import하는 패턴을 쓴다. 글롭이 매치하는 파일이 없어도 에러가 안 나기 때문에, 아직 사이트가 없는 환경에서도 같은 설정을 쓸 수 있다.

함정 하나. snippet은 사이트 블록 외부에서 정의해야 한다. 사이트 블록 안에서 `(name)`을 정의하면 그 사이트 안에서만 보이는 게 아니라 그냥 파싱 에러가 난다.

## placeholder

placeholder는 `{...}` 형태로 요청 정보나 환경 정보를 동적으로 끼워넣는 메커니즘이다. 자주 쓰는 것들은 외워두면 매번 문서를 뒤지지 않아도 된다.

```caddy
example.com {
    log {
        format json
    }

    # 요청 정보
    header X-Request-Method {method}
    header X-Request-Path {path}
    header X-Request-Host {host}
    header X-Client-IP {remote_host}
    header X-Forwarded-For-Original {http.request.header.X-Forwarded-For}

    # 호스트 라벨 (오른쪽부터 0)
    @tenant header_regexp X-Tenant {labels.2}

    # placeholder를 사용한 백엔드 분기
    reverse_proxy backend-{labels.2}.internal:8080
}
```

자주 쓰는 placeholder는 다음과 같다.

| placeholder | 의미 |
|---|---|
| `{host}` | Host 헤더 (포트 제외) |
| `{port}` | 요청이 들어온 포트 |
| `{path}` | 요청 경로 (쿼리 제외) |
| `{query}` | 쿼리 문자열 |
| `{method}` | HTTP 메서드 |
| `{scheme}` | http 또는 https |
| `{remote_host}` | 클라이언트 IP |
| `{remote_port}` | 클라이언트 포트 |
| `{labels.N}` | 호스트 라벨 (오른쪽부터 0) |
| `{header.X-Foo}` | 요청 헤더 X-Foo |
| `{cookie.session}` | 쿠키 session |
| `{query.q}` | 쿼리 파라미터 q |
| `{re.name.N}` | path_regexp 캡처 그룹 |
| `{time.now.unix}` | 현재 시각 (유닉스 타임) |
| `{system.hostname}` | 서버 호스트명 |

전체 형태는 `{http.request.host}`처럼 namespace가 붙은 정식 이름이다. `{host}`는 그 약식이다. 길게 적은 이름이 더 명확해서 디버깅할 때 도움이 된다.

placeholder는 reverse_proxy 백엔드 주소에서도 평가된다. 위 예제처럼 멀티테넌트 라우팅에서 호스트 라벨로 백엔드를 분기시키는 데 자주 쓴다. 다만 매 요청마다 DNS 조회가 발생할 수 있으니 백엔드가 너무 많거나 빈번히 바뀌면 부하가 된다.

## 환경변수 치환

Caddyfile 안에서 환경변수를 읽으려면 `{$VAR_NAME}` 형태를 쓴다. placeholder의 `{...}`와 비슷해 보이지만 앞에 `$`가 붙는다는 점이 다르다.

```caddy
{
    email {$ACME_EMAIL}
}

example.com {
    reverse_proxy {$BACKEND_HOST}:{$BACKEND_PORT}

    basicauth {
        admin {$ADMIN_PASSWORD_HASH}
    }
}
```

기본값을 지정할 수도 있다.

```caddy
example.com {
    reverse_proxy {$BACKEND_HOST:localhost}:{$BACKEND_PORT:3000}
}
```

환경변수가 없으면 콜론 뒤의 값을 쓴다. Docker나 Kubernetes에서 같은 Caddyfile 이미지를 여러 환경에 배포할 때 유용하다.

중요한 차이 하나. 환경변수는 Caddy가 시작할 때 한 번만 읽힌다. placeholder는 매 요청마다 평가되지만 `{$VAR}`은 파일 파싱 시점에 치환되고 그게 끝이다. 환경변수를 바꾸고 싶으면 Caddy를 reload해야 한다(`caddy reload`).

또 하나, placeholder와 환경변수가 같이 쓰일 수 있는 자리에서는 dollar sign 한 글자 차이로 동작이 완전히 달라진다. `{remote_host}`는 매 요청의 클라이언트 IP이고, `{$REMOTE_HOST}`는 환경변수 REMOTE_HOST의 값이다. 오타로 인한 디버깅이 길어지기 쉽다.

## 전역 옵션 블록의 주요 옵션

전역 옵션 블록은 Caddy 인스턴스 전체에 적용되는 설정이다. 사이트별로 다르게 둘 수 없는 것들이 모인다.

```caddy
{
    # ACME 이메일 (인증서 발급 알림용)
    email admin@example.com

    # ACME CA 변경 (기본 Let's Encrypt)
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory

    # 자동 HTTPS 끄기
    auto_https off

    # 디버그 로그
    debug

    # Admin API 주소
    admin localhost:2019

    # HTTP 포트 변경 (기본 80, 443)
    http_port 8080
    https_port 8443

    # 기본 SNI
    default_sni example.com

    # On-Demand TLS 정책
    on_demand_tls {
        ask https://api.example.com/check-domain
        interval 1m
        burst 5
    }

    # 서버 옵션
    servers {
        protocols h1 h2 h3
        listener_wrappers {
            proxy_protocol
        }
        max_header_size 1MB
        timeouts {
            read_body 10s
            read_header 5s
            write 30s
            idle 120s
        }
    }
}
```

운영 환경에서 자주 건드리는 건 `email`, `admin`, `servers` 정도다. `email`은 ACME 등록할 때 필요하고, 이걸 안 적으면 처음 인증서 발급할 때 익명 등록이 되는데 일부 CA는 익명을 안 받는다. `admin`은 Admin API의 listen 주소를 바꾸는 옵션인데, 컨테이너 환경에서 외부 노출을 막기 위해 `localhost:2019`로 잠그거나 `off`로 완전히 끄는 경우가 많다.

`acme_ca`는 인증서 발급을 staging으로 돌릴 때 쓴다. 운영 발급 직전에 staging으로 한 번 돌려보면 rate limit을 안 까먹고 안전하게 검증할 수 있다. staging 인증서는 브라우저가 신뢰하지 않는 가짜 CA로 서명되지만, 발급 흐름 자체를 검증하는 데는 충분하다.

`servers` 블록의 timeouts는 백엔드 응답이 오래 걸리는 서비스에서 502/504를 방지하기 위해 늘리는 경우가 많다. 단 `idle`을 너무 길게 잡으면 connection이 누적돼서 메모리를 먹는다. 1분~2분 정도가 보통이다.

## 실수하기 쉬운 패턴 정리

마지막으로 운영하면서 실제로 디버깅에 시간을 많이 쓰게 되는 패턴 몇 가지를 정리한다.

첫째, `redir`과 `reverse_proxy`를 같이 쓸 때 자동 정렬 때문에 의도와 다르게 동작하는 경우가 많다. 특히 `redir`이 와일드카드로 모든 경로를 잡으면 `reverse_proxy`까지 도달하지 못한다. 의도한 동작이 명확히 보이지 않으면 `route`로 감싸서 순서를 강제하는 게 안전하다.

둘째, `handle` 안에서 매처를 또 쓰는 건 가능하지만 헷갈린다. `handle /api/*` 안에서 `header @json ...`처럼 또 매처를 쓰면 두 단계 매칭이 적용된다. 차라리 named matcher를 미리 정의하고 `handle @api`로 분기하는 게 깔끔하다.

셋째, `handle_path`는 prefix가 정확히 매치되는 경우만 자른다. `handle_path /api`는 정확히 `/api`만 잘라내고 `/api/users`는 매치조차 안 된다. `handle_path /api/*`로 적어야 의도대로 동작한다.

넷째, snippet에 인수를 넘길 때 `{args.0}` placeholder가 동작하지 않는 경우는 보통 snippet 내부에서 그게 placeholder가 평가되는 자리가 아니기 때문이다. 디렉티브 인수 자리에서는 평가되지만, 디렉티브 이름 자리에서는 평가되지 않는다. 코드 예제를 보면서 snippet이 어디서 어떻게 펼쳐지는지 머릿속에서 시뮬레이션해보는 습관이 필요하다.

다섯째, 환경변수 `{$VAR}`의 기본값 문법(`{$VAR:default}`)은 Caddyfile 어댑터에서만 동작한다. JSON 설정으로 넘어가면 환경변수 치환이 다르게 처리되니 마이그레이션할 때 확인해야 한다.

## 관련 문서

- [Caddy 개요](Caddy.md)
- [reverse_proxy 디렉티브 심화](Reverse_Proxy.md)
- [서브도메인 라우팅과 와일드카드](Subdomain_Routing.md)
- [SSL/TLS 자동 발급](SSL_TLS.md)
- [Admin API](Admin_API.md)
