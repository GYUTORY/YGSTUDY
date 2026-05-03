---
title: Caddy 헤더 처리와 CORS
tags:
  - WebServer
  - Caddy
  - Headers
  - CORS
  - SecurityHeaders
  - CSP
updated: 2026-05-03
---

# Caddy 헤더 처리와 CORS

`header X-Foo bar` 한 줄로 끝날 것 같지만, 실제 운영에서 헤더는 가장 자주 디버깅하게 되는 영역이다. CORS preflight가 막혀서 프론트엔드에서 API가 안 붙는다는 제보, 보안 점검에서 X-Frame-Options가 빠졌다는 지적, gzip을 켰더니 클라이언트에서 Content-Length 불일치로 응답이 잘렸다는 이슈까지 전부 헤더에서 출발한다.

Caddy의 `header` 디렉티브는 한 줄짜리 단순 형태부터 매처와 옵션이 잔뜩 붙은 블록 형태까지 폭이 넓고, 백엔드 응답을 그대로 흘려보내는 `reverse_proxy` 안에서는 또 별도의 `header_down`이 등장한다. 이 두 개가 어떻게 다르게 동작하는지, 언제 무엇을 써야 하는지 명확히 잡아두지 않으면 헤더가 두 번 붙거나 한쪽만 붙어서 한참 헤매게 된다.

이 문서는 `header` 디렉티브의 내부 동작, CORS 처리, 보안 헤더 묶음, reverse_proxy와의 관계를 운영 관점에서 정리한다. HSTS와 TLS 관련 헤더는 `SSL_TLS.md`에서 따로 다루므로 여기서는 다루지 않는다.

## header 디렉티브의 기본 형태

가장 단순한 형태는 한 줄짜리다.

```caddy
example.com {
    header X-Frame-Options DENY
    reverse_proxy localhost:3000
}
```

이렇게 쓰면 모든 응답에 `X-Frame-Options: DENY` 헤더가 추가된다. 정확히는 "추가"가 아니라 "set"이다. 같은 이름의 헤더가 이미 있다면 덮어쓴다. 이 동작 차이가 처음에 가장 헷갈리는 부분이라, set/add/del을 먼저 정리해야 한다.

## set, add, del의 차이

Caddy의 `header` 디렉티브는 헤더 이름 앞에 붙는 접두사로 동작 모드를 결정한다. 접두사가 없으면 set이고, `+`가 붙으면 add, `-`가 붙으면 del, `?`가 붙으면 default다. 이 네 가지가 실제로 다르게 동작하는 구체적인 예를 본다.

```caddy
example.com {
    header X-Custom "from-caddy"
    header +X-Custom "another"
    header -Server
    header ?X-Default "fallback-value"
    reverse_proxy localhost:3000
}
```

첫 번째 줄은 set이다. 백엔드가 `X-Custom: from-backend`를 내려주더라도 Caddy가 `X-Custom: from-caddy`로 덮어쓴다. 같은 이름의 기존 값은 사라진다.

두 번째 줄은 add다. `+`를 붙이면 기존 값을 유지한 채로 같은 이름의 헤더를 하나 더 붙인다. HTTP 헤더는 같은 이름이 여러 번 등장할 수 있고, 대부분의 클라이언트는 이를 콤마로 합쳐진 단일 값처럼 취급한다. 하지만 `Set-Cookie`처럼 절대 합치면 안 되는 헤더도 있어서, add를 쓸 때는 그 헤더가 다중 값을 허용하는지 먼저 확인해야 한다.

세 번째 줄은 del이다. `-`를 붙이면 그 이름의 헤더를 제거한다. 백엔드가 `Server: Express` 같은 정보 노출 헤더를 보낼 때 이걸로 지운다. 와일드카드도 지원한다. `header -X-Powered-By`로 한 줄 지우는 식이다.

네 번째 줄은 default다. `?`를 붙이면 그 헤더가 응답에 없을 때만 추가한다. 있으면 백엔드 값을 그대로 둔다. `Cache-Control` 같은 헤더에 기본값을 깔아두고 싶을 때 유용하다. 백엔드가 명시적으로 캐시 정책을 내려주면 그걸 따르고, 안 내려주면 Caddy가 기본값을 채운다.

이 네 가지를 헷갈려서 실수하는 패턴이 두 개 있다. 첫째, set으로 써야 할 자리에 add를 써서 같은 헤더가 두 번 붙는 경우. `Strict-Transport-Security`가 두 번 붙으면 일부 브라우저는 두 번째 값을 무시하고 일부는 둘 다 처리하면서 보수적인 쪽을 따른다. 둘째, del을 빼먹어서 백엔드의 `Server: Express` 같은 헤더가 그대로 노출되는 경우. 보안 점검에서 가장 먼저 지적되는 것 중 하나다.

## 매처와 함께 쓰기

`header` 디렉티브는 매처를 받는다. 특정 경로나 메서드에만 헤더를 붙일 수 있다는 뜻이다.

```caddy
example.com {
    @api path /api/*
    header @api Cache-Control "no-store"

    @static path *.css *.js *.png *.jpg *.woff2
    header @static Cache-Control "public, max-age=31536000, immutable"

    reverse_proxy localhost:3000
}
```

API 응답은 캐시하지 않게 하고, 정적 자산은 1년짜리 immutable 캐시를 건다. 이렇게 매처별로 헤더를 분리해서 쓰는 게 가장 흔한 패턴이다. 매처를 빼먹고 전역에 `Cache-Control: no-store`를 걸어두면 정적 자산까지 매번 다시 받게 되어 트래픽이 폭발한다. 반대로 정적 자산용 immutable 정책을 전역에 걸면 API 응답까지 캐싱되어 데이터 갱신이 안 보이는 사고가 난다.

매처는 named matcher 외에 named가 아닌 in-line 매처도 받는다.

```caddy
header /api/* Cache-Control "no-store"
```

이 형태는 짧은 설정에 편하지만, 같은 매처를 여러 디렉티브에서 재사용하려면 named matcher로 빼는 게 좋다.

## defer 옵션의 정체

`header` 디렉티브 블록에 `defer`를 붙이면 동작이 바뀐다. 이게 운영에서 의외로 중요한 옵션이라 별도로 짚어둔다.

```caddy
example.com {
    header {
        defer
        Cache-Control "public, max-age=3600"
    }
    reverse_proxy localhost:3000
}
```

`defer`가 없으면 Caddy는 응답을 시작하기 전에 헤더를 적용한다. 그런데 `reverse_proxy`나 `file_server` 같은 핸들러가 자기 응답에 헤더를 직접 쓰는 경우, Caddy가 먼저 세팅한 헤더가 핸들러에 의해 덮어쓰일 수 있다. 특히 `file_server`는 정적 파일의 `Last-Modified`, `ETag`, `Content-Type`을 자기가 직접 결정하기 때문에, Caddy 레벨에서 미리 세팅한 일부 헤더가 영향을 받을 여지가 있다.

`defer`는 응답 헤더를 모두 쓴 직후, 응답 본문이 클라이언트에 흘러나가기 직전에 헤더 조작을 적용하라는 지시다. 즉, 핸들러가 뭐라고 쓰든 마지막에 한 번 더 덮어쓰겠다는 뜻이다. 백엔드나 file_server가 의도와 다른 헤더를 내려줄 때 이걸로 강제로 정리한다.

체감하는 차이는 `Cache-Control`이나 `Content-Type` 같은 헤더에서 가장 크다. 백엔드가 `Cache-Control: public, max-age=60`을 내려주는데 Caddy에서 이걸 `no-store`로 바꾸려고 `header Cache-Control no-store`를 걸었을 때, defer 없이는 백엔드 값이 그대로 살아남거나 두 값이 콤마로 합쳐지는 일이 생긴다. defer를 붙이면 마지막에 강제로 덮어써서 의도대로 동작한다.

```caddy
example.com {
    header /api/* {
        defer
        Cache-Control "no-store"
        -Pragma
    }
    reverse_proxy localhost:3000
}
```

이 패턴은 백엔드를 직접 고치기 어려운 상황에서 자주 쓴다. 레거시 서비스가 잘못된 캐시 헤더를 내려주고 있을 때, Caddy가 게이트웨이에서 마지막에 정리해주는 식이다.

## CORS 처리의 본질

CORS는 Caddy 디렉티브가 따로 있는 게 아니라 `header`로 직접 짜야 한다. 이게 처음 보면 좀 당혹스러운데, 그도 그럴 것이 CORS는 단순히 헤더 한두 개를 더 붙이는 게 아니라 preflight OPTIONS 요청을 별도로 처리해야 하기 때문이다.

브라우저가 cross-origin 요청을 보낼 때, 단순 GET/POST(form-urlencoded)는 바로 본 요청을 보내지만, JSON body나 커스텀 헤더가 들어가면 먼저 OPTIONS 메서드로 preflight를 보낸다. 이 preflight에 서버가 200/204로 응답하면서 어떤 origin/method/header를 허용하는지 알려줘야 본 요청이 나간다.

```caddy
api.example.com {
    @cors_preflight {
        method OPTIONS
        header Origin *
    }

    handle @cors_preflight {
        header Access-Control-Allow-Origin "https://app.example.com"
        header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"
        header Access-Control-Max-Age "86400"
        respond 204
    }

    handle {
        header Access-Control-Allow-Origin "https://app.example.com"
        header Access-Control-Allow-Credentials "true"
        reverse_proxy localhost:3000
    }
}
```

이 구조가 핵심이다. preflight 매처를 하나 만들고, 그 매처에 걸린 요청은 백엔드로 보내지 않고 Caddy가 204로 직접 답한다. 그 외 요청만 reverse_proxy로 흘러간다. 백엔드까지 OPTIONS가 들어가게 두면 백엔드 프레임워크에서 405 Method Not Allowed를 돌려주는 일이 자주 생기고, 그러면 브라우저는 본 요청을 시도조차 하지 않는다.

`Access-Control-Max-Age`는 preflight 결과를 클라이언트가 캐시해도 되는 시간을 초 단위로 알려준다. 86400(24시간)이면 같은 origin/method/header 조합의 preflight를 24시간 동안 다시 보내지 않는다. 짧게 잡으면 매 요청마다 preflight가 두 번씩 가는 꼴이라 응답 속도가 두 배로 늘어난다.

### Origin을 동적으로 처리하기

서비스가 단일 origin만 허용한다면 위처럼 하드코딩하면 끝이지만, 여러 도메인에서 접근해야 하는 경우엔 Origin을 동적으로 검증해야 한다. 브라우저는 `Access-Control-Allow-Origin`에 정확한 origin 한 개만 들어 있어야 받아들이고, 와일드카드 `*`는 credentials와 같이 못 쓴다.

```caddy
api.example.com {
    @allowed_origin {
        header_regexp Origin ^https://(app|admin|staging)\.example\.com$
    }

    @cors_preflight {
        method OPTIONS
        header Origin *
    }

    handle @cors_preflight {
        header @allowed_origin Access-Control-Allow-Origin "{header.Origin}"
        header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        header Access-Control-Allow-Headers "Content-Type, Authorization"
        header Access-Control-Allow-Credentials "true"
        header Access-Control-Max-Age "86400"
        header Vary "Origin"
        respond 204
    }

    handle {
        header @allowed_origin Access-Control-Allow-Origin "{header.Origin}"
        header @allowed_origin Access-Control-Allow-Credentials "true"
        header @allowed_origin Vary "Origin"
        reverse_proxy localhost:3000
    }
}
```

`{header.Origin}` 플레이스홀더로 요청의 Origin 헤더 값을 그대로 응답에 넣는다. 단, `@allowed_origin` 매처를 통과한 요청에만 넣는다. 매처를 통과 못 한 요청은 `Access-Control-Allow-Origin`이 아예 안 붙어서 브라우저가 거부한다.

여기서 `Vary: Origin` 헤더가 같이 붙는 점에 주의해야 한다. CDN이나 중간 캐시가 응답을 캐싱할 때 Origin이 다른 요청을 같은 응답으로 돌려주면 보안 문제가 생긴다. `Vary: Origin`이 있어야 캐시가 Origin별로 응답을 분리해서 저장한다. 이걸 빠뜨리면 사내 도메인용 응답이 외부 도메인 요청에 그대로 캐시된 채로 흘러나가는 사고가 난다.

### credentials와 와일드카드 충돌

`Access-Control-Allow-Credentials: true`를 쓰면 `Access-Control-Allow-Origin`에 와일드카드 `*`를 못 쓴다. 명시적으로 origin 하나를 적어야 한다. 이 규칙은 브라우저가 강제하는 거라 우회할 방법이 없다.

```caddy
header Access-Control-Allow-Origin "*"
header Access-Control-Allow-Credentials "true"
```

이렇게 써두면 브라우저 콘솔에 "The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'" 에러가 뜬다. 쿠키나 Authorization 헤더를 쓰는 API라면 무조건 Origin을 명시적으로 검증해서 echo 하는 방식으로 가야 한다.

비슷한 문제가 `Access-Control-Allow-Headers`와 `Access-Control-Allow-Methods`에서도 일어난다. credentials가 켜져 있으면 이 둘도 와일드카드를 못 쓴다. 허용할 헤더와 메서드를 명시적으로 나열해야 한다.

### Vary 헤더가 여럿일 때

CORS 응답에 `Vary: Origin`을 붙였는데 Caddy가 다른 곳에서 `Vary: Accept-Encoding`을 또 붙인다면 둘 다 살려야 한다. set으로 쓰면 한쪽이 덮인다.

```caddy
header +Vary "Origin"
```

이렇게 add로 추가하면 Caddy가 자동으로 콤마로 합쳐서 `Vary: Accept-Encoding, Origin`처럼 만들어준다. CDN과 함께 쓸 때 이걸 놓치면 캐시 분리가 의도대로 안 일어난다.

## 보안 헤더 묶음

보안 점검 도구를 한 번이라도 돌려본 사람은 익숙한 헤더 목록이 있다. X-Frame-Options, X-Content-Type-Options, Content-Security-Policy, Referrer-Policy, Permissions-Policy. 이 다섯 개는 거의 모든 사이트에 들어가야 한다.

HSTS(`Strict-Transport-Security`)도 이 묶음에 들어가지만, TLS 자동화와 강하게 엮여 있어서 `SSL_TLS.md`에서 별도로 다룬다. 여기서는 나머지 다섯 개만 본다.

```caddy
example.com {
    header {
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        Content-Security-Policy "default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.example.com; frame-ancestors 'none'"
    }
    reverse_proxy localhost:3000
}
```

각각이 어떤 의미를 갖는지 짧게 짚는다.

### X-Frame-Options

다른 사이트가 우리 페이지를 iframe으로 임베드하는 걸 막는다. `DENY`는 어떤 사이트도 임베드 못 하게 하고, `SAMEORIGIN`은 같은 origin에서만 허용한다. 이 헤더의 후속 표준이 CSP의 `frame-ancestors` 디렉티브인데, 최신 브라우저는 둘 다 보지만 충돌하면 `frame-ancestors`가 우선한다. 두 개를 같이 두는 게 가장 안전하다.

### X-Content-Type-Options

값은 `nosniff` 하나뿐이다. 브라우저가 응답의 Content-Type을 무시하고 본문을 보고 타입을 추측하는 동작(MIME sniffing)을 막는다. 이 동작이 켜져 있으면 사용자가 업로드한 텍스트 파일을 브라우저가 HTML로 해석해서 XSS가 터질 수 있다. 정적 자산을 서빙하는 모든 응답에 무조건 붙인다.

### Content-Security-Policy

CSP는 가장 강력하고 동시에 가장 까다로운 헤더다. 어떤 도메인에서 스크립트를 로드할 수 있는지, 인라인 스크립트를 허용할지, 이미지/폰트/미디어를 어디서 가져올 수 있는지 전부 명시한다.

위 예제에서 `script-src 'self' 'unsafe-inline'`을 보면 알 수 있듯이, 인라인 스크립트를 허용하지 않으려면 `'unsafe-inline'`을 빼야 한다. 그런데 React/Vue 같은 SPA가 빌드 시 인라인 스크립트를 만드는 경우가 많아서, nonce나 hash 기반 CSP로 바꿔야 한다. 운영에서 본격적으로 도입하려면 먼저 `Content-Security-Policy-Report-Only`로 violation을 모아본 다음 점진적으로 강화해야 한다. 처음부터 strict하게 잡으면 페이지가 통째로 깨진다.

```caddy
header Content-Security-Policy-Report-Only "default-src 'self'; report-uri /csp-report"
```

이렇게 report-only로 시작하면 위반이 일어나도 차단하지 않고 리포트만 보낸다. 며칠 모아본 뒤 실제 정책을 잡는다.

`frame-ancestors 'none'`은 X-Frame-Options DENY와 같은 효과다. 둘 다 두면 신구 브라우저 모두 커버한다.

### Referrer-Policy

다른 사이트로 이동할 때 Referer 헤더에 우리 사이트 URL을 얼마나 포함시킬지 결정한다. `strict-origin-when-cross-origin`이 기본값으로 가장 무난하다. 같은 origin 내에서는 전체 URL을 보내고, cross-origin으로 나갈 때는 origin만 보낸다. 토큰이나 민감 정보가 URL 쿼리에 들어가는 경우 이 정책이 없으면 외부 사이트 로그에 그대로 찍힌다.

### Permissions-Policy

브라우저 API 사용 권한을 통제한다. 위치 정보, 마이크, 카메라, 결제 API, 가속도계 같은 기능들을 우리 사이트와 임베드된 iframe에서 쓸 수 있는지 결정한다. 안 쓰는 기능은 명시적으로 막아두는 게 안전하다.

```caddy
header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
```

빈 괄호는 어디서도 쓸 수 없다는 의미다. `geolocation=(self)`라고 쓰면 우리 사이트만 쓸 수 있고, `geolocation=(self "https://maps.example.com")`이면 우리 사이트와 maps.example.com에서 쓸 수 있다.

## Server 헤더 숨기기

Caddy는 기본적으로 응답에 `Server: Caddy` 헤더를 붙인다. 백엔드가 `Server: Express`나 `Server: nginx/1.24` 같은 헤더를 내려주는 경우도 있다. 보안 관점에서 이런 정보 노출 헤더는 모두 지우는 게 정석이다.

```caddy
example.com {
    header {
        -Server
        -X-Powered-By
    }
    reverse_proxy localhost:3000
}
```

여기서 한 가지 함정이 있다. `header -Server`는 응답이 만들어진 시점의 Server 헤더를 지우지만, Caddy 자체가 응답 직전에 다시 `Server: Caddy`를 붙이는 경우가 있다. 그래서 완전히 지우려면 `defer`와 함께 써야 한다.

```caddy
header {
    defer
    -Server
}
```

defer를 붙이면 응답 헤더가 모두 결정된 마지막 단계에서 지우기 때문에 확실하게 빠진다. 운영에서 `curl -I`로 응답 헤더를 찍어봤는데 Server가 계속 붙어 있다면 defer를 빠뜨린 경우가 대부분이다.

`X-Powered-By`는 PHP나 Express 같은 백엔드가 자동으로 붙이는 헤더다. 이것도 같이 지운다. 공격자에게 백엔드 스택과 버전을 알려주는 건 첫 단추부터 잘못 끼우는 셈이다.

## reverse_proxy 안의 header_up과 header_down

지금까지 본 `header` 디렉티브는 클라이언트로 나가는 응답 헤더를 다룬다. `reverse_proxy` 블록 안에는 또 다른 헤더 디렉티브가 두 개 있다. `header_up`은 백엔드로 나가는 요청 헤더를, `header_down`은 백엔드에서 받은 응답 헤더를 조작한다.

```caddy
example.com {
    reverse_proxy localhost:8080 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}

        header_down -Server
        header_down -X-Powered-By
        header_down Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}
```

`header_up`은 백엔드에 도달하기 전에 추가/변경/삭제할 요청 헤더다. 클라이언트 IP를 백엔드에 알려주는 `X-Real-IP`나 `X-Forwarded-For`, 원래 프로토콜을 알려주는 `X-Forwarded-Proto`가 대표적이다. 자세한 내용은 `Reverse_Proxy.md`에서 다룬다.

`header_down`은 백엔드 응답이 클라이언트로 나가기 전에 조작할 응답 헤더다. 그러면 위에서 본 `header` 디렉티브와 무엇이 다른가? 적용 시점이 다르다.

### header와 header_down의 차이

`header_down`은 reverse_proxy 핸들러 안에서 백엔드 응답을 받자마자 적용된다. 그 이후에 다른 미들웨어를 거쳐 클라이언트로 나간다. `header`는 응답 파이프라인 전체를 통과한 마지막 단계에서 적용된다(특히 defer가 붙어 있다면).

대부분의 경우 둘 중 어느 쪽을 써도 결과가 같지만, 차이가 드러나는 시나리오가 있다.

```caddy
example.com {
    reverse_proxy localhost:8080 {
        header_down Cache-Control "public, max-age=300"
    }

    header Cache-Control "no-store"
}
```

이 설정에서 백엔드 응답은 어떻게 될까? `header_down`이 먼저 `Cache-Control: public, max-age=300`으로 세팅하지만, 그 다음 `header` 디렉티브가 `no-store`로 덮어쓴다. 그래서 클라이언트가 받는 값은 `no-store`다.

운영에서 의도와 다른 헤더가 붙는 이슈를 디버깅할 때, 이 적용 순서를 모르면 한참 헤맨다. 일반적으로는 다음 기준을 따른다.

- 백엔드 응답에서 특정 헤더를 지우거나 백엔드 응답에만 붙이고 싶다면 `header_down`을 쓴다.
- 모든 응답(reverse_proxy든 file_server든 respond든)에 일괄 적용하고 싶다면 최상위 `header`를 쓴다.
- 백엔드 응답을 강제로 덮어써야 한다면 `header` + `defer`를 쓴다.

세 번째가 가장 강력하다. defer가 모든 핸들러 이후에 마지막으로 한 번 더 적용되기 때문에, 백엔드가 뭐라고 내려주든, header_down이 뭘 했든 무시하고 강제로 덮는다.

### 백엔드 응답 헤더를 그대로 흘리고 싶을 때

기본적으로 `reverse_proxy`는 백엔드 응답 헤더를 거의 그대로 클라이언트에 전달한다. 다만 hop-by-hop 헤더(Connection, Keep-Alive, Transfer-Encoding 등)는 HTTP 표준에 따라 제거되고, Caddy가 자기 헤더(Server 등)를 덧붙일 수 있다.

가끔 백엔드가 자체 CORS 헤더를 내려주는데 Caddy에서 또 CORS 헤더를 붙여서 두 번 들어가는 사고가 난다. 이때는 `header_down -Access-Control-Allow-Origin` 식으로 백엔드 헤더를 먼저 지우고 Caddy가 새로 세팅하는 흐름으로 가야 한다.

```caddy
api.example.com {
    reverse_proxy localhost:8080 {
        header_down -Access-Control-Allow-Origin
        header_down -Access-Control-Allow-Credentials
        header_down -Access-Control-Allow-Methods
        header_down -Access-Control-Allow-Headers
    }

    header @allowed_origin Access-Control-Allow-Origin "{header.Origin}"
    header Access-Control-Allow-Credentials "true"
}
```

CORS 정책을 게이트웨이 레벨에서 통일하는 패턴이다. 백엔드는 자기 일만 하고, Caddy가 모든 CORS를 책임진다. 백엔드가 마이크로서비스 여러 개로 분산된 환경에서 특히 깔끔하게 동작한다.

## 자주 빠지는 함정

운영에서 헤더 관련해 반복적으로 만나는 문제 몇 가지를 정리한다.

### 같은 헤더가 두 번 붙는 경우

가장 흔한 케이스다. 백엔드가 이미 보낸 헤더를 Caddy가 add(`+`)로 또 붙여서 클라이언트에서 콤마로 합쳐진 이상한 값을 받는다.

```
HSTS: max-age=31536000, max-age=63072000; includeSubDomains; preload
```

이런 응답을 보면 백엔드와 Caddy 양쪽에서 HSTS를 붙이고 있다는 뜻이다. 한쪽을 끄거나, set으로 바꿔서 한 값만 남게 해야 한다. set 대신 add로 헤더를 다루는 습관을 들이면 이런 사고가 잦아진다.

`Access-Control-Allow-Origin`이 두 번 붙는 경우도 마찬가지다. 브라우저는 이걸 invalid로 판단하고 CORS를 거부한다. 한 번에 한 개만 붙어야 한다.

### gzip 인코딩 후 Content-Length 누락

`encode gzip`이나 `encode zstd` 같은 압축을 켜면 Caddy는 응답 본문을 압축해서 내보낸다. 이때 원래 백엔드가 보낸 `Content-Length`는 압축 전 크기라서, 압축 후의 실제 바이트 수와 맞지 않게 된다. Caddy는 이 경우 `Content-Length`를 제거하고 `Transfer-Encoding: chunked`로 바꿔서 내보낸다.

이게 정상 동작인데, 어떤 클라이언트(특히 일부 IoT 디바이스나 오래된 HTTP 라이브러리)는 chunked를 제대로 처리하지 못해서 응답이 잘리거나 멈춘다.

```caddy
example.com {
    @no_compress {
        path /firmware/*
        header User-Agent *Embedded*
    }

    @compress not match @no_compress

    encode @compress gzip zstd
    reverse_proxy localhost:8080
}
```

이런 식으로 압축에서 제외할 경로나 클라이언트를 명시한다. 압축이 빠지면 Content-Length가 그대로 살아남아서 chunked 처리를 못 하는 클라이언트도 정상 동작한다.

또 한 가지, 백엔드가 직접 압축한 응답을 보낼 때(`Content-Encoding: gzip`이 백엔드에서 이미 붙어 있을 때) Caddy가 그걸 다시 압축하지는 않는다. 그래서 압축이 두 번 되는 사고는 잘 안 나지만, 백엔드가 압축을 하면서 Content-Length를 잘못 계산해서 보내는 경우가 있다. 이때는 Caddy에서 잡을 수 있는 게 없고 백엔드를 고쳐야 한다.

### Set-Cookie를 set으로 다룰 때

`header Set-Cookie "..."` 식으로 쿠키를 set으로 쓰면, 백엔드가 보낸 모든 Set-Cookie 헤더가 한 번에 덮어써진다. 백엔드가 세션 쿠키 두 개와 인증 쿠키 한 개를 보내고 있었다면 모두 사라지고 Caddy가 쓴 한 개만 남는다.

쿠키 헤더를 다룰 때는 add(`+`)로만 쓰거나 아예 안 건드리는 게 안전하다. 쿠키 도메인이나 path를 바꾸고 싶다면 백엔드에서 처리하든가, 아니면 쿠키를 파싱해서 다시 조립해주는 별도 로직이 필요하다. Caddy의 `header` 디렉티브로는 쿠키 속성만 부분 변경할 수 없다.

### CSP의 nonce를 정적 헤더로 쓰려고 하는 경우

CSP에 nonce를 쓸 때, nonce는 매 요청마다 달라야 한다. Caddy의 `header` 디렉티브로는 매 요청마다 새 nonce를 생성하는 기능이 없다. 백엔드에서 nonce를 만들어서 응답 본문에 inject하고, 같은 nonce를 응답 헤더의 CSP에 넣어야 한다.

Caddy 레벨에서는 hash 기반 CSP나 strict-dynamic이 더 다루기 쉽다. nonce가 꼭 필요하다면 백엔드에서 처리하는 쪽으로 설계해야 한다.

### 매처 순서로 헤더가 안 붙는 경우

`handle`과 `handle_path` 같은 라우팅 디렉티브 안에 `header`가 들어가면 그 매처에 걸린 요청에만 헤더가 붙는다. 매처를 통과하지 못한 요청은 헤더가 안 붙는다.

```caddy
example.com {
    handle /api/* {
        header X-API-Version "v2"
        reverse_proxy localhost:8080
    }

    handle {
        header X-Frame-Options "DENY"
        file_server
    }
}
```

이 설정에서 `/api/*`로 들어온 요청에는 `X-Frame-Options`가 안 붙는다. 보안 헤더처럼 모든 응답에 공통으로 붙어야 하는 것들은 `handle` 블록 바깥, 사이트 블록 최상위에 두어야 한다.

```caddy
example.com {
    header X-Frame-Options "DENY"
    header X-Content-Type-Options "nosniff"

    handle /api/* {
        header X-API-Version "v2"
        reverse_proxy localhost:8080
    }

    handle {
        file_server
    }
}
```

이렇게 빼면 모든 응답에 보안 헤더가 들어간다. 운영하다가 보안 점검에서 일부 경로만 헤더가 빠져 있다는 지적을 받으면 이 매처 구조를 의심해봐야 한다.

## 디버깅 팁

응답 헤더가 의도대로 안 붙을 때 가장 빠른 디버깅 방법은 `curl -I`로 직접 찍어보는 것이다.

```bash
curl -I https://example.com/api/users

curl -I -X OPTIONS https://example.com/api/users \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

첫 줄은 일반 GET 응답의 헤더를, 두 번째 줄은 CORS preflight 응답의 헤더를 보여준다. preflight를 디버깅할 때는 반드시 `Origin`, `Access-Control-Request-Method`, `Access-Control-Request-Headers` 세 개를 같이 보내야 실제 브라우저 동작과 같아진다.

Caddy의 access log를 켜두면 어떤 헤더가 들어와서 어떤 매처에 걸렸는지 추적할 수 있다. 자세한 로깅 설정은 `Logging_Monitoring.md`에서 다룬다.

헤더 관련 이슈는 대부분 적용 순서, 매처 범위, set/add 혼동 이 세 가지 안에 들어간다. 응답이 이상하게 나오면 먼저 이 세 가지를 의심해보면 답이 빨리 나온다.
