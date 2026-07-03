---
title: Caddy 인증 처리 (basic_auth, forward_auth, JWT)
tags:
  - WebServer
  - Caddy
  - Authentication
  - BasicAuth
  - ForwardAuth
  - JWT
  - OAuth2Proxy
  - Authelia
updated: 2026-05-03
---

# Caddy 인증 처리 (basic_auth, forward_auth, JWT)

Caddy로 단순 정적 사이트를 서빙할 때는 인증을 신경 쓸 일이 거의 없다. 문제는 사내 도구를 한두 개 노출시키는 순간부터 시작된다. Grafana, Prometheus, 사내 wiki, 어드민 대시보드. 자체 로그인을 다 만들기엔 과하고 그렇다고 노출시킬 수도 없는 그 애매한 영역에 Caddy의 인증 디렉티브가 들어간다.

Caddy가 제공하는 인증 방식은 크게 세 가지다. 내장된 `basic_auth`, 외부 인증 서버에 위임하는 `forward_auth`, 그리고 third-party 모듈로 들어가는 JWT 검증이다. 이 셋은 보호 수준도 다르고 운영 비용도 다르다. 잘못 고르면 매번 비밀번호를 다시 입력하게 만들거나, 정작 보호하려던 경로를 매처 순서 때문에 그대로 노출시킨다. 이 문서는 그 세 방식의 동작 원리와 실제로 운영하면서 마주치는 함정을 정리한다.

## basic_auth 디렉티브의 동작 원리

`basic_auth`는 RFC 7617의 HTTP Basic Authentication을 구현한 디렉티브다. 클라이언트가 `Authorization: Basic <base64(user:pass)>` 헤더를 보내면 Caddy가 base64를 디코딩한 뒤 비밀번호를 bcrypt로 해시해서 저장된 해시와 비교한다. 헤더가 없거나 인증이 실패하면 `401 Unauthorized`와 함께 `WWW-Authenticate: Basic realm="..."` 응답을 돌려준다. 브라우저는 이 응답을 받으면 로그인 다이얼로그를 띄운다.

여기서 가장 먼저 알아야 할 점은 base64 인코딩이 암호화가 아니라는 것이다. `dXNlcjpwYXNz` 같은 문자열은 디코딩하면 그대로 `user:pass`가 나온다. 그래서 basic_auth는 반드시 HTTPS 위에서만 써야 한다. Caddy는 기본적으로 HTTPS를 자동으로 켜주기 때문에 이 부분은 별도로 신경 쓸 일이 거의 없지만, 내부 네트워크에서 평문 HTTP로 노출시키는 경우엔 비밀번호가 그대로 흘러간다는 점을 잊지 말아야 한다.

기본 형태는 다음과 같다.

```caddy
admin.example.com {
    basic_auth {
        admin $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
        ops   $2a$14$x9z8aBcDeFgHiJkLmNoPqrSt3uV4wXyZaBcDeFgHiJkLmNoPqrSt
    }
    reverse_proxy localhost:3000
}
```

여기서 두 번째 컬럼은 평문 비밀번호가 아니라 bcrypt로 해시된 값이다. Caddy는 평문 비밀번호를 받지 않는다. Caddyfile에 평문을 그대로 적어두면 시작할 때 파싱 에러로 죽는다. 이건 의도된 설계인데, 설정 파일이 git에 올라가거나 다른 사람이 보더라도 비밀번호가 그대로 노출되지 않게 하려는 장치다.

### bcrypt 해시 생성

해시는 `caddy hash-password` 명령으로 만든다. 인자 없이 실행하면 stdin으로 비밀번호를 받고, 표준 출력으로 해시를 돌려준다.

```bash
$ caddy hash-password
Enter password:
Confirm password:
$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
```

CI 파이프라인이나 스크립트에서 비대화식으로 해시를 만들고 싶을 때는 플래그를 직접 줘야 한다.

```bash
$ caddy hash-password --plaintext "my-secret-password"
$2a$14$abcDefGhIjKlMnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWxYzA
```

다만 이 방법은 비밀번호가 셸 history에 남고 `ps`로 다른 사용자에게 노출될 위험이 있어서, 진짜 운영 환경에서는 stdin으로 넘기는 게 안전하다.

bcrypt cost 값은 기본 14인데, 이 숫자가 보안 수준이자 동시에 운영 비용이다. cost 14는 한 번 해시하는 데 대략 100~300ms 정도 걸린다. CPU 성능에 따라 차이가 크지만, 의도적으로 느리게 만들어서 brute force를 어렵게 하는 게 bcrypt의 설계 목적이다. 이 비용이 곧 다음 절에서 설명할 메모리 함정과 직접 연결된다.

### basic_auth의 메모리 비용 함정

basic_auth로 보호된 경로에 요청이 들어올 때마다 Caddy는 클라이언트가 보낸 평문 비밀번호를 bcrypt로 해시해서 비교한다. 매 요청마다 100~300ms씩 CPU를 갉아먹는다는 뜻이다. 이게 단순히 응답이 느려지는 문제로 끝나면 다행이다.

문제는 어느 사용자가 사내 모니터링 스크립트를 짜서 5초마다 Grafana를 폴링하기 시작했을 때다. 하나의 워커 고루틴이 100~300ms 동안 CPU를 잡고 있고, 동시에 다른 사용자 50명이 어드민 페이지를 새로고침하면 Caddy 프로세스의 CPU가 순식간에 100%로 치솟는다. 응답 지연이 길어지면 클라이언트가 재시도를 시작하고, 재시도가 또 bcrypt 큐에 쌓이고, 결국 전체 사이트가 먹통이 되는 시나리오를 실제로 본 적이 있다.

이 문제를 회피하기 위해 Caddy는 같은 (사용자, 비밀번호) 조합에 대해 검증 결과를 짧게 캐시한다. 하지만 캐시가 영원하지 않고, 또 다른 비밀번호 조합을 brute force로 시도하는 공격이 들어오면 캐시가 무력화된다. 그래서 basic_auth는 사용자가 5명 이하이고 트래픽이 거의 없는 내부 도구에만 쓰는 것을 권장한다. 그 이상 규모가 되면 forward_auth로 세션 기반 인증으로 옮겨가야 한다.

## 보호 경로 매처 패턴

`basic_auth`를 사이트 블록의 최상단에 적으면 사이트 전체가 인증으로 보호된다. 하지만 어떤 경로는 공개해야 하고 어떤 경로만 보호해야 하는 경우가 더 흔하다. 헬스체크 엔드포인트(`/healthz`)나 정적 자산(`/static/*`)은 인증 없이 통과시키고, `/admin/*` 경로만 보호하는 식이다.

```caddy
example.com {
    basic_auth /admin/* {
        admin $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
    }
    reverse_proxy localhost:3000
}
```

이렇게 디렉티브 뒤에 경로 패턴을 직접 적으면 그 경로에 한해서만 인증이 적용된다. `*`는 와일드카드라 `/admin/users`, `/admin/users/123` 모두 매칭한다.

여러 경로를 묶거나 더 복잡한 조건이 필요하면 named matcher를 써야 한다.

```caddy
example.com {
    @protected {
        path /admin/* /api/internal/*
        not path /admin/health
    }
    basic_auth @protected {
        admin $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
    }
    reverse_proxy localhost:3000
}
```

`@protected` matcher는 `/admin/*` 또는 `/api/internal/*` 경로를 보호하면서 `/admin/health`만 예외로 빼낸다. matcher 안에서 `not`을 쓰면 그 조건은 부정된다.

여기서 가장 무서운 함정이 하나 있다. matcher의 순서와 디렉티브의 순서다.

### 매처 순서로 인증을 우회당하는 함정

Caddy는 Caddyfile에 적힌 디렉티브를 위에서 아래로 실행하지 않는다. 내부적으로 정해진 디렉티브 우선순위에 따라 재정렬된다. `basic_auth`는 `reverse_proxy`보다 먼저 실행되도록 정렬되기 때문에 일반적인 경우엔 문제가 없다. 하지만 `handle`이나 `route`로 명시적으로 순서를 잡기 시작하면 얘기가 달라진다.

```caddy
example.com {
    handle /admin/* {
        basic_auth {
            admin $2a$14$...
        }
        reverse_proxy localhost:3000
    }

    handle /api/* {
        reverse_proxy localhost:3000
    }

    handle {
        reverse_proxy localhost:3000
    }
}
```

이 설정은 `/admin/*`만 인증으로 보호하고 나머지는 모두 인증 없이 백엔드로 보낸다. 의도가 명확해 보이지만, 만약 누군가 `/admin/secret-page` 같은 경로를 만들고 동시에 백엔드가 `/api/admin-bypass` 같은 라우트를 노출시키고 있다면, `/api/*` 매처가 먼저 매칭되면서 인증 없이 그대로 통과한다.

더 흔한 함정은 매처 자체를 잘못 짜는 경우다. `/admin*`과 `/admin/*`은 비슷해 보이지만 다르다. `/admin*`는 `/administrator` 같은 경로도 매칭하는 반면 `/admin/*`는 `/admin/`으로 시작하는 경로만 매칭한다. `/admin/users`만 보호하려고 `path /admin*`라고 적으면 `/administrator-bypass` 같은 경로가 의도와 다르게 보호 영역에 들어갈 수도 있고, 반대로 빠질 수도 있다.

또 하나는 path 매처가 정확히 매칭되는지 확인할 때다. `path /admin`은 정확히 `/admin`만 매칭한다. `/admin/`(끝에 슬래시)은 매칭되지 않는다. 백엔드가 `/admin`으로 들어오면 `/admin/`으로 redirect하는 경우, 첫 요청은 인증을 거쳐도 redirect된 두 번째 요청은 매처에 안 걸려서 그대로 통과한다.

이 문제를 디버깅할 때는 Caddy의 access log에서 매처가 어떻게 평가됐는지 추적해야 한다. JSON 로그 포맷에서 `request.uri` 필드와 실제로 어떤 handle 블록이 실행됐는지를 비교해 보면 매처가 의도대로 동작하는지 알 수 있다.

## forward_auth로 외부 인증 위임

basic_auth가 사용자 5명 이하 환경의 임시 방편이라면, forward_auth는 본격적인 인증 시스템과 Caddy를 연결하는 다리다. 동작 원리는 단순하다. 요청이 들어오면 Caddy가 그 요청을 백엔드로 보내기 전에 인증 서버로 먼저 보낸다. 인증 서버가 `2xx` 응답을 돌려주면 원래 요청을 백엔드로 통과시키고, `401`이나 다른 응답을 돌려주면 그대로 클라이언트에게 반환한다.

```caddy
internal.example.com {
    forward_auth localhost:4180 {
        uri /oauth2/auth
        copy_headers X-Auth-Request-User X-Auth-Request-Email X-Auth-Request-Groups
    }
    reverse_proxy localhost:3000
}
```

이 설정은 `localhost:4180`에서 돌고 있는 oauth2-proxy로 인증을 위임한다. Caddy는 클라이언트의 모든 헤더(특히 `Cookie`)를 oauth2-proxy로 전달하고, oauth2-proxy는 세션 쿠키를 검증해서 유효하면 사용자 정보가 담긴 헤더와 함께 `202 Accepted`를 돌려준다. 그러면 Caddy는 그 헤더 중에서 `copy_headers`로 지정한 것만 골라서 백엔드로 가는 원본 요청에 붙여 보낸다.

forward_auth의 진짜 가치는 인증 로직을 Caddy에서 완전히 분리한다는 점이다. Caddy는 "이 요청을 통과시켜도 되냐"만 물어보고, "어떻게 검증할지"는 oauth2-proxy나 Authelia가 알아서 한다. Google OAuth, GitHub OAuth, LDAP, TOTP, WebAuthn을 붙이고 싶을 때 Caddy 설정은 한 줄도 안 바꾸고 인증 서버 쪽만 바꾸면 된다.

### oauth2-proxy 연동

oauth2-proxy는 OAuth 2.0 / OIDC provider 앞에 세우는 인증 게이트웨이다. Google, GitHub, Keycloak 같은 provider에 위임하고 받아온 사용자 정보를 헤더로 백엔드에 전달한다.

```caddy
{
    auto_https on
}

(oauth_protected) {
    forward_auth localhost:4180 {
        uri /oauth2/auth
        copy_headers X-Auth-Request-User X-Auth-Request-Email X-Auth-Request-Groups

        @auth_redirect status 401
        handle_response @auth_redirect {
            redir https://auth.example.com/oauth2/sign_in?rd=https://{host}{uri} 302
        }
    }
}

grafana.example.com {
    import oauth_protected
    reverse_proxy localhost:3000
}

prometheus.example.com {
    import oauth_protected
    reverse_proxy localhost:9090
}

# oauth2-proxy 자체는 별도 호스트로 노출
auth.example.com {
    reverse_proxy localhost:4180
}
```

여기서 핵심은 `handle_response` 블록이다. 인증되지 않은 사용자가 보호된 경로에 접근하면 oauth2-proxy가 `401`을 돌려주는데, 그대로 클라이언트에 보내면 브라우저는 그냥 흰 화면만 본다. `handle_response`로 `401` 응답을 가로채서 oauth2-proxy의 sign-in 페이지로 redirect 시켜야 사용자가 로그인 흐름을 탈 수 있다. `rd` 쿼리 파라미터에 원래 URL을 담아서 로그인 후 원래 페이지로 돌아오게 만든다.

oauth2-proxy의 cookie domain 설정과 Caddy의 호스트가 정확히 일치하지 않으면 무한 redirect 루프에 빠진다. oauth2-proxy가 `auth.example.com`에서 쿠키를 굽고, 보호된 사이트가 `grafana.example.com`이라면 oauth2-proxy의 cookie domain은 `.example.com`(앞에 점)으로 설정해야 한다. 이걸 빼먹으면 로그인은 되는데 grafana로 redirect되는 순간 다시 로그인 페이지로 튕긴다.

### Authelia 연동

Authelia는 oauth2-proxy보다 한 단계 더 나아간 SSO 솔루션이다. 자체 사용자 DB와 RBAC, 2FA, Duo push 같은 기능을 제공한다. forward_auth 연동 방식은 oauth2-proxy와 거의 같다.

```caddy
(authelia) {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.example.com
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
}

nextcloud.example.com {
    import authelia
    reverse_proxy nextcloud:80
}

vault.example.com {
    import authelia
    reverse_proxy vault:8200
}

auth.example.com {
    reverse_proxy authelia:9091
}
```

Authelia가 돌려주는 헤더 이름이 oauth2-proxy와 다르다는 점만 주의하면 된다. `Remote-User`, `Remote-Groups`, `Remote-Name`, `Remote-Email`이 표준이다. 백엔드 애플리케이션이 어떤 헤더에서 사용자 정보를 읽는지에 따라 Caddy에서 헤더 이름을 다시 매핑해 주는 경우도 있다.

```caddy
nextcloud.example.com {
    forward_auth authelia:9091 {
        uri /api/verify
        copy_headers Remote-User>X-Forwarded-User Remote-Email>X-Forwarded-Email
    }
    reverse_proxy nextcloud:80
}
```

`Remote-User>X-Forwarded-User`는 인증 서버가 `Remote-User`라는 이름으로 돌려준 헤더를 백엔드에는 `X-Forwarded-User`로 이름을 바꿔서 전달하라는 의미다.

### forward_auth 사용 시 성능 고려

forward_auth의 장점은 인증 로직이 분리된다는 것이지만, 단점은 모든 요청마다 추가로 인증 서버에 한 번 더 hop이 발생한다는 것이다. oauth2-proxy나 Authelia가 같은 호스트의 localhost에 떠 있다면 추가 latency가 1ms 이하로 미미하지만, Kubernetes에서 별도 pod로 돌고 있으면 5~20ms씩 더 걸린다. 정적 자산까지 매번 forward_auth를 거치면 페이지 로딩이 눈에 띄게 느려진다.

이 문제는 정적 자산은 매처로 빼고 인증이 필요한 경로만 forward_auth를 거치게 하면 풀린다.

```caddy
app.example.com {
    @assets path /static/* /favicon.ico /robots.txt
    handle @assets {
        reverse_proxy localhost:3000
    }

    handle {
        forward_auth localhost:4180 {
            uri /oauth2/auth
            copy_headers X-Auth-Request-User X-Auth-Request-Email
        }
        reverse_proxy localhost:3000
    }
}
```

다만 이 패턴을 쓸 때는 정적 자산 경로가 정말 인증 없이 노출돼도 되는지 한 번 더 확인해야 한다. `/static/internal-doc.pdf` 같은 게 섞여 있으면 우회 통로가 된다.

## JWT 검증 모듈

forward_auth는 매 요청마다 인증 서버에 물어보는 방식이라 한계가 있다. 인증 정보를 토큰에 담아서 stateless하게 검증하고 싶으면 JWT를 써야 한다. Caddy 코어에는 JWT 검증 기능이 없고 third-party 모듈을 써야 한다. 대표적인 게 `caddy-security`(구 `caddy-auth-jwt`)다.

이 모듈을 쓰려면 Caddy 바이너리를 새로 빌드해야 한다. `xcaddy`로 빌드한다.

```bash
xcaddy build \
  --with github.com/greenpau/caddy-security
```

빌드된 바이너리로 다음과 같이 설정한다.

```caddy
{
    order authenticate before respond
    order authorize before reverse_proxy

    security {
        jwt {
            token_secret "my-very-long-and-random-secret-key"
            token_lifetime 3600
        }

        authentication portal myportal {
            crypto key sign-verify from env JWT_SHARED_KEY
            cookie domain example.com
            backends {
                local_backend {
                    method local
                    path /etc/caddy/users.json
                    realm local
                }
            }
        }

        authorization policy mypolicy {
            set auth url https://auth.example.com/login
            allow roles authp/admin authp/user
            crypto key verify from env JWT_SHARED_KEY
        }
    }
}

api.example.com {
    authorize with mypolicy
    reverse_proxy localhost:8080
}

auth.example.com {
    authenticate with myportal
}
```

여기서 핵심은 `authorize` 디렉티브다. 보호하려는 경로에 이 디렉티브를 걸면 caddy-security가 요청의 `Authorization: Bearer <jwt>` 헤더 또는 cookie에서 토큰을 꺼내서 검증한다. 서명이 유효하지 않거나 토큰이 만료됐으면 인증 실패 처리한다.

JWT 검증의 장점은 stateless라는 점이다. 인증 서버에 매번 물어볼 필요 없이 토큰의 서명만 검증하면 된다. 단점은 토큰을 무효화하기 어렵다는 점이다. 사용자가 로그아웃해도 그 토큰은 만료될 때까지 유효하다. 이걸 해결하려면 별도의 blacklist를 운영해야 하는데, 그러면 다시 stateful이 된다. JWT는 짧은 lifetime(15분~1시간)에 refresh token으로 갱신하는 패턴으로 운영하는 게 일반적이다.

caddy-security 모듈이 forward_auth보다 무거운 만큼, JWT를 굳이 Caddy 레이어에서 검증할 필요가 있는지는 한 번 따져봐야 한다. 백엔드 애플리케이션이 어차피 JWT를 검증한다면 Caddy는 그냥 통과시키고 백엔드에 맡기는 게 운영 부담이 적다. Caddy에서 JWT를 검증하는 게 의미 있는 경우는 백엔드가 여러 마이크로서비스로 쪼개져 있고 각각이 같은 인증 로직을 중복 구현하기 싫을 때, 또는 인증되지 않은 요청이 백엔드에 아예 도달하지 않게 하고 싶을 때다.

## 인증 실패 시 401과 403의 차이

인증 관련 작업을 하다 보면 401과 403을 자주 헷갈린다. 표면적으로는 둘 다 "접근 거부"지만 의미가 다르고 클라이언트의 동작도 달라진다.

`401 Unauthorized`는 "당신이 누구인지 모르겠다"는 뜻이다. 인증 정보(credentials)가 없거나 잘못됐을 때 돌려준다. RFC에 따르면 401 응답에는 반드시 `WWW-Authenticate` 헤더가 함께 와야 한다. 브라우저는 이 헤더를 보고 어떤 인증 방식이 필요한지 판단한다. `WWW-Authenticate: Basic realm="Admin"`이 오면 로그인 다이얼로그를 띄우고, `Bearer` 같은 게 오면 자체적인 처리는 하지 않는다.

`403 Forbidden`은 "당신이 누구인지는 알겠는데 이 리소스에 접근할 권한이 없다"는 뜻이다. 인증은 됐지만 인가(authorization)가 안 된 경우다. 예를 들어 일반 사용자로 로그인한 사람이 `/admin/*` 경로에 접근하면 401이 아니라 403을 돌려줘야 맞다.

Caddy의 `basic_auth`는 인증 실패 시 401을 돌려준다. `WWW-Authenticate: Basic realm="restricted"` 헤더를 함께 보내기 때문에 브라우저가 로그인 다이얼로그를 자동으로 띄운다. 만약 API 클라이언트라면 401을 받으면 토큰을 갱신하거나 재로그인 흐름을 타게 만들어야 한다.

forward_auth의 경우 401 vs 403은 인증 서버가 결정한다. oauth2-proxy는 보통 401을 돌려주고 Caddy의 `handle_response`로 sign-in 페이지로 redirect하는 패턴을 쓴다. Authelia도 비슷하다. 인가 정책에 걸려서 거부되는 경우엔 403을 돌려주는 게 정석인데, 이건 클라이언트가 재로그인해도 해결되지 않으니 사용자에게 "권한이 없다"는 메시지를 보여줘야 한다.

가끔 보는 잘못된 패턴은 모든 인증 실패를 403으로 돌려주는 경우다. 그러면 토큰이 만료됐을 뿐인데 클라이언트가 "권한 없음"으로 처리해서 재로그인 시도조차 안 하는 일이 생긴다. 401과 403은 의미상 분명히 다르고, 클라이언트 SDK들도 보통 이 둘을 구분해서 처리하기 때문에 정확히 돌려주는 게 중요하다.

## X-Forwarded-User와 식별 헤더 전달

forward_auth로 인증된 요청을 백엔드로 보낼 때, 백엔드는 누가 요청을 보냈는지 어떻게 알까. 답은 헤더다. Caddy가 인증 서버로부터 받은 사용자 정보를 헤더로 백엔드에 전달하면 백엔드는 그 헤더를 신뢰하고 사용자를 식별한다.

가장 흔한 헤더 이름은 `X-Forwarded-User`(또는 `X-Auth-User`, `Remote-User`)다. 인증 서버에 따라 이름이 다르다. oauth2-proxy는 `X-Auth-Request-User`, Authelia는 `Remote-User`다. 백엔드가 기대하는 이름이 따로 있다면 Caddy에서 매핑해 줘야 한다.

```caddy
internal.example.com {
    forward_auth localhost:4180 {
        uri /oauth2/auth
        copy_headers X-Auth-Request-User>X-Forwarded-User \
                     X-Auth-Request-Email>X-Forwarded-Email \
                     X-Auth-Request-Groups>X-Forwarded-Groups
    }

    reverse_proxy localhost:3000 {
        header_up X-Forwarded-User {http.request.header.X-Forwarded-User}
        header_up X-Forwarded-Email {http.request.header.X-Forwarded-Email}
    }
}
```

여기서 한 가지 절대 잊으면 안 되는 보안 원칙이 있다. 백엔드가 `X-Forwarded-User` 헤더를 신뢰한다면, 클라이언트가 그 헤더를 직접 보낼 수 없도록 Caddy가 항상 덮어써야 한다는 점이다. 만약 클라이언트가 보낸 `X-Forwarded-User: admin` 헤더가 그대로 백엔드까지 도달한다면, 인증 자체를 우회하고 다른 사용자로 행세할 수 있다.

Caddy의 `reverse_proxy`는 기본적으로 클라이언트 헤더를 백엔드로 그대로 전달한다. forward_auth가 설정해 주는 헤더는 인증된 요청에 한해 덮어쓰지만, 클라이언트가 같은 이름의 헤더를 미리 보냈을 때 그게 어떻게 처리되는지는 항상 확인해야 한다. 안전하게 가려면 `header_up`으로 인증되지 않은 헤더를 명시적으로 제거한다.

```caddy
internal.example.com {
    # 들어오는 클라이언트 헤더 제거
    request_header -X-Forwarded-User
    request_header -X-Forwarded-Email
    request_header -X-Forwarded-Groups

    forward_auth localhost:4180 {
        uri /oauth2/auth
        copy_headers X-Auth-Request-User>X-Forwarded-User \
                     X-Auth-Request-Email>X-Forwarded-Email
    }

    reverse_proxy localhost:3000
}
```

`request_header -X-Forwarded-User`는 클라이언트가 보낸 그 헤더를 무조건 제거한다. 그 다음에 forward_auth가 인증된 사용자 정보로 새 헤더를 박는다. 이 순서가 보장돼야 헤더 spoofing 공격을 막을 수 있다.

또 하나 자주 빠뜨리는 부분은 `X-Forwarded-For`와 `X-Real-IP` 같은 클라이언트 IP 헤더다. Caddy의 `reverse_proxy`는 기본적으로 이 두 헤더를 자동으로 채워준다. 하지만 Caddy 앞에 또 다른 reverse proxy(예: AWS ALB)가 있다면 `trusted_proxies` 설정을 통해 어디까지 신뢰할지 명시해야 한다. 그렇지 않으면 클라이언트가 위조한 `X-Forwarded-For` 헤더를 그대로 받아서 누가 진짜 요청자인지 모르게 된다.

```caddy
{
    servers {
        trusted_proxies static private_ranges 10.0.0.0/8
    }
}
```

`trusted_proxies`로 신뢰할 수 있는 프록시 IP 대역을 명시하면 그 대역에서 들어오는 요청의 `X-Forwarded-*` 헤더는 신뢰하고, 그 외에는 무시한다.

## 어떤 인증 방식을 고를 것인가

세 가지 방식을 정리하면 선택 기준이 보인다.

basic_auth는 사용자 5명 이하, 트래픽 거의 없음, 임시 보호용. 사내 wiki나 staging 환경에 빠르게 자물쇠를 거는 용도다. 이 이상으로 가면 bcrypt CPU 비용이 발목을 잡는다.

forward_auth는 본격적인 인증이 필요한 모든 경우. oauth2-proxy나 Authelia를 한 번 세팅해 두면 사이트별로 디렉티브 한 줄만 추가하면 된다. SSO, 2FA, OIDC 같은 요구사항이 모두 인증 서버 쪽에서 처리된다. 운영 부담은 인증 서버를 추가로 운영해야 한다는 점인데, 이미 사내에 Keycloak이나 Okta가 있다면 그 앞에 oauth2-proxy만 붙이면 된다.

JWT 모듈은 마이크로서비스 환경에서 인증 로직을 게이트웨이에 통합하고 싶을 때. Caddy 빌드를 커스텀해야 하는 부담이 있고 토큰 무효화 문제가 항상 남아 있다. 백엔드가 어차피 JWT를 검증한다면 Caddy 레이어에서 중복 검증할 이유가 별로 없다.

마지막으로 매처 순서로 인한 우회는 어느 방식을 쓰든 항상 따라다니는 함정이다. 보호하려는 경로의 매처를 짠 뒤에는 반드시 의도한 경로만 보호되는지, 의도하지 않은 경로가 통과하지 않는지를 실제 요청을 보내서 확인해야 한다. `curl -v`로 401이 떨어지는지 200이 떨어지는지 한 번씩 찔러보는 게, 운영에 올린 뒤에 우회 사고를 보는 것보다 훨씬 싸게 먹힌다.
