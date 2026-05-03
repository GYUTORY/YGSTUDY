---
title: Caddy 서브도메인 라우팅과 와일드카드 인증서 실무
tags: [webserver, caddy, subdomain, wildcard, tls, multi-tenant, on-demand-tls, dns-01]
updated: 2026-05-03
---

## 왜 Caddy에서 서브도메인이 까다로운가

Nginx에서 서브도메인은 그냥 `server_name`만 바꿔주면 끝나는 작업이다. Caddy는 HTTPS가 자동이라는 점이 오히려 서브도메인 운영에서 발목을 잡는다. 사이트 블록 하나당 인증서 한 장이 자동으로 붙는데, 와일드카드를 쓰려는 순간 갑자기 DNS 프로바이더 모듈을 직접 빌드해야 하고, 멀티테넌트 SaaS에서 고객이 자기 도메인을 붙여오면 그건 또 다른 메커니즘(On-Demand TLS)을 써야 한다. 이 세 갈래(서브도메인 정적 분기 / 와일드카드 / On-Demand)를 헷갈리면 인증서 발급이 무한 루프를 돌거나 Let's Encrypt rate limit에 걸려서 한참을 기다려야 한다.

이 문서에서는 Caddyfile에서 서브도메인을 다루는 패턴을 정적인 것부터 동적 SaaS 호스팅까지 순서대로 정리한다.

## 사이트 블록 분리와 호스트 매처

가장 단순한 패턴은 서브도메인마다 사이트 블록을 따로 만드는 것이다. 각 블록의 첫 줄에 호스트명을 적으면 그게 곧 매처가 되고, Caddy가 그 호스트로 들어온 요청만 해당 블록에서 처리한다.

```caddy
api.example.com {
    reverse_proxy localhost:3000
}

admin.example.com {
    basicauth {
        admin $2a$14$...해시값
    }
    reverse_proxy localhost:8080
}

static.example.com {
    root * /var/www/static
    file_server
    encode gzip
}
```

이 방식의 장점은 사이트별로 인증서가 자동 발급되고, 설정이 깔끔하게 분리된다는 점이다. 단점은 서브도메인이 10개, 20개 늘어나면 Caddyfile이 길어지고, 새 서브도메인을 추가할 때마다 reload가 필요하다는 것이다.

서브도메인 개수가 5~10개 수준이고 자주 바뀌지 않으면 이 패턴이 가장 안전하다. 인증서도 도메인별로 따로 관리되므로 한 도메인 발급이 실패해도 다른 도메인은 영향을 받지 않는다.

## 한 블록에서 여러 호스트 동시 처리

같은 백엔드를 가리키는 서브도메인이 여러 개라면 콤마로 묶어서 한 블록에 넣을 수 있다.

```caddy
api.example.com, api-v2.example.com, internal-api.example.com {
    reverse_proxy localhost:3000
}
```

이렇게 쓰면 Caddy는 세 도메인 각각의 인증서를 발급한다. 와일드카드 한 장을 발급해서 공유하는 게 아니라 SAN에 세 도메인이 모두 들어간 인증서 또는 도메인별 개별 인증서를 받는다(버전과 설정에 따라 다름). Let's Encrypt는 하루 발급량 제한이 있으니 도메인이 많을수록 와일드카드로 가는 게 낫다.

apex 도메인과 와일드카드를 동시에 받고 싶으면 다음처럼 쓴다.

```caddy
example.com, *.example.com {
    @api host api.example.com
    handle @api {
        reverse_proxy localhost:3000
    }

    @admin host admin.example.com
    handle @admin {
        reverse_proxy localhost:8080
    }

    handle {
        root * /var/www/landing
        file_server
    }
}
```

이렇게 쓰면 와일드카드 인증서 한 장(apex 포함하려면 SAN에 두 항목)이 발급되고, 블록 내부에서 host 매처로 분기한다. handle은 첫 매치만 실행되므로 위에서 아래로 우선순위가 정해진다. 기본 handle은 매처가 없는 마지막에 두면 모든 미매치 요청을 처리한다.

## 와일드카드 호스트 매처와 placeholder

서브도메인 슬러그를 동적으로 추출해서 백엔드에 넘기고 싶을 때 placeholder를 쓴다. Caddy는 호스트의 각 라벨을 `{labels.N}`으로 노출하는데, 인덱스는 오른쪽부터 0이다. `tenant1.example.com`이라면 `{labels.0}`은 `com`, `{labels.1}`은 `example`, `{labels.2}`는 `tenant1`이 된다.

```caddy
*.example.com {
    @tenant host_regexp tenant ^([a-z0-9-]+)\.example\.com$

    handle @tenant {
        header_up X-Tenant {labels.2}
        reverse_proxy localhost:3000
    }

    respond "Invalid tenant" 400
}
```

처음 이걸 쓸 때 인덱스 방향을 거꾸로 알고 `{labels.0}`을 썼다가 한참 디버깅한 경험이 있다. `*.api.example.com`이라면 라벨이 4개니까 와일드카드 위치가 `{labels.3}`이 된다는 점도 주의해야 한다. 헷갈리면 다음처럼 일단 응답으로 찍어보고 확인하는 게 빠르다.

```caddy
*.example.com {
    respond "labels.0={labels.0} labels.1={labels.1} labels.2={labels.2}"
}
```

`host_regexp` 매처는 정규식으로 호스트를 잡으면서 캡처 그룹을 `{re.tenant.1}` 식으로 꺼낼 수 있다. labels로 추출이 애매하거나 슬러그 형식을 검증하고 싶으면 정규식이 더 편하다.

```caddy
*.example.com {
    @valid host_regexp slug ^(?P<slug>[a-z][a-z0-9-]{2,30})\.example\.com$
    handle @valid {
        header_up X-Tenant {re.slug.slug}
        reverse_proxy localhost:3000
    }
    handle {
        respond "Invalid subdomain" 400
    }
}
```

## DNS-01 챌린지와 와일드카드 인증서

`*.example.com` 같은 와일드카드는 Let's Encrypt에서 HTTP-01 챌린지로 받을 수 없다. 와일드카드는 무조건 DNS-01이다. DNS-01은 Caddy가 ACME 서버 요청을 받아서 `_acme-challenge.example.com` TXT 레코드를 만들고, ACME 서버가 그걸 조회해서 도메인 소유권을 확인하는 방식이다.

문제는 Caddy 기본 빌드에 DNS 프로바이더 모듈이 없다는 점이다. xcaddy로 직접 빌드해야 한다.

```bash
# Cloudflare 사용 시
xcaddy build \
    --with github.com/caddy-dns/cloudflare

# Route53
xcaddy build \
    --with github.com/caddy-dns/route53

# 여러 개 동시에
xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/caddy-dns/route53
```

빌드한 바이너리로 교체한 뒤 Caddyfile에 DNS 프로바이더 설정을 넣는다.

```caddy
*.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
        propagation_timeout 2m
        propagation_delay 30s
    }
    reverse_proxy localhost:3000
}
```

`propagation_delay`는 TXT 레코드를 만든 뒤 ACME 서버가 조회하기 전에 기다리는 시간이다. 0으로 두면 DNS 캐시 때문에 발급이 실패하는 경우가 있다. Cloudflare는 보통 빠르게 전파되지만 30초 정도는 줘야 안정적이다. Route53은 더 짧아도 된다. 사내 DNS나 느린 프로바이더는 60~120초까지 늘려야 할 수도 있다.

`propagation_timeout`은 전파 대기를 포기하는 시점이다. 너무 짧으면 정상 발급도 실패로 처리되고, 너무 길면 장애 시 복구가 늦어진다. 2분이 보통 무난하다.

API 토큰 권한 설정도 까다롭다. Cloudflare의 경우 `Zone:Read`와 `DNS:Edit` 두 권한이 필요한데, 이걸 빼먹으면 발급은 시도하는데 TXT 레코드를 못 만들어서 무한히 재시도한다. 로그에 `403 Forbidden`이 찍히면 토큰 권한부터 확인해야 한다.

## 와일드카드 SAN을 여러 사이트 블록에서 공유

이게 처음에는 헷갈리는데, Caddy는 사이트 블록마다 따로 인증서를 받는 게 기본이다. 와일드카드 한 장을 발급해서 여러 블록에서 쓰고 싶으면 명시적으로 호스트 목록에 와일드카드를 포함시켜야 한다.

```caddy
*.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }

    @api host api.example.com
    handle @api {
        reverse_proxy localhost:3000
    }

    @admin host admin.example.com
    handle @admin {
        reverse_proxy localhost:8080
    }

    handle {
        respond "Unknown subdomain" 404
    }
}
```

이렇게 한 블록 안에서 와일드카드로 받은 인증서를 모든 서브도메인이 공유한다. 발급 횟수가 1회로 끝나고 Let's Encrypt rate limit에서 자유롭다. 단점은 블록 하나가 거대해지고, 한 서브도메인에만 특수한 설정(별도 미들웨어, 다른 timeout 등)을 넣기 어렵다는 점이다.

서브도메인별로 블록을 분리하면서도 와일드카드 인증서를 공유하고 싶으면 글로벌 옵션 블록에서 자동 HTTPS 정책을 잡거나, 각 블록에 동일한 `tls` 지시어를 반복해서 넣는다. 같은 와일드카드 호스트를 가진 여러 블록은 Caddy가 인증서를 공유하도록 동작한다.

## On-Demand TLS — 고객 커스텀 도메인

SaaS를 운영하다 보면 고객이 자기 도메인(`shop.customer.com`)을 우리 서비스에 연결하고 싶다는 요구가 들어온다. 우리는 그 도메인이 뭐가 들어올지 미리 모르고, Caddyfile에 박아둘 수도 없다. 이때 쓰는 게 On-Demand TLS다.

```caddy
{
    on_demand_tls {
        ask http://localhost:9000/check-domain
        interval 2m
        burst 5
    }
}

https:// {
    tls {
        on_demand
    }
    reverse_proxy localhost:3000
}
```

동작 흐름은 이렇다. 어떤 도메인으로 TLS 핸드셰이크가 들어오면 Caddy는 먼저 `ask` 엔드포인트에 `GET /check-domain?domain=shop.customer.com`을 보낸다. 200을 받으면 그 도메인으로 Let's Encrypt 발급을 시도하고, 200이 아니면 발급을 거부한다. `interval`과 `burst`는 발급 시도 간격과 동시 발급 한도다.

`ask` 엔드포인트는 우리 백엔드에서 직접 구현해야 한다. 보통은 DB에 등록된 고객 도메인 목록을 조회해서 매치되면 200, 아니면 404를 반환한다.

```javascript
// Express 예시
app.get('/check-domain', async (req, res) => {
    const domain = req.query.domain;
    if (!domain) return res.status(400).send('missing domain');

    const exists = await db.customerDomains.exists({ domain });
    if (!exists) return res.status(404).send('not registered');

    res.status(200).send('ok');
});
```

`ask`를 절대 빼면 안 된다. 빼면 누구나 임의의 도메인으로 핸드셰이크를 시도해서 우리 Caddy가 그 도메인으로 발급을 시도하게 만들 수 있다. Let's Encrypt는 IP당, 계정당 발급 한도가 있어서 공격자가 무작위 도메인 수천 개로 핸드셰이크를 던지면 우리 계정이 rate limit에 걸려 정상 고객 도메인도 발급이 막힌다. 한번 막히면 일주일 가까이 풀리지 않는다.

첫 핸드셰이크는 발급 대기 때문에 5~30초 지연된다. 이게 사용자 입장에서는 "사이트가 멈췄다"로 느껴진다. 운영에서는 고객이 도메인을 등록하는 시점에 백엔드에서 먼저 핸드셰이크를 시뮬레이션해서 인증서를 미리 받아두는 워밍업 작업을 하는 게 좋다. `curl https://shop.customer.com -k`만 백엔드에서 한 번 쳐도 Caddy가 발급을 시작한다.

## ask 엔드포인트가 죽으면 어떻게 되는가

운영하다가 한 번씩 마주치는 상황인데, `ask` 엔드포인트가 5xx를 뱉거나 응답이 없으면 Caddy는 기본적으로 발급을 거부한다. 즉 새 도메인의 첫 핸드셰이크가 모두 실패한다. 이미 발급받은 인증서로 들어오는 기존 트래픽은 영향이 없다.

이게 무서운 이유는 `ask` 백엔드가 단일 장애점이 된다는 것이다. 백엔드 하나가 죽으면 신규 고객 온보딩이 막힌다. 그래서 `ask` 엔드포인트는 보통 별도의 가벼운 서비스로 빼거나, 메인 백엔드와 분리된 readonly DB 복제본을 보게 만든다. 캐시도 적극적으로 쓴다.

```javascript
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 300 });

app.get('/check-domain', async (req, res) => {
    const domain = req.query.domain;
    const cached = cache.get(domain);
    if (cached !== undefined) {
        return res.status(cached ? 200 : 404).send();
    }

    const exists = await db.customerDomains.exists({ domain });
    cache.set(domain, exists);
    res.status(exists ? 200 : 404).send();
});
```

5분 캐시면 발급 시도 빈도와 DB 부하가 적당히 균형이 맞는다. 고객 도메인 등록/해제 시 캐시 무효화 처리만 잘 해두면 된다.

## On-Demand 무한 발급 사고 사례

한 번은 `ask` 엔드포인트의 검증 로직이 잘못 짜여서 모든 도메인에 200을 돌려주게 한 적이 있다. 그 사이에 봇이 임의 도메인으로 핸드셰이크를 던지기 시작했고, Caddy가 1시간 동안 수백 건의 발급 시도를 했다. 결과는 Let's Encrypt 계정 rate limit. 정상 고객이 새로 도메인을 등록해도 발급이 안 됐다.

이걸 방지하려면 `ask` 엔드포인트에서 화이트리스트 검증을 엄격하게 해야 하고, On-Demand 사용 시 글로벌 옵션의 `interval`과 `burst`를 보수적으로 잡아야 한다. `burst 5`는 동시 발급 5개라는 뜻인데, 정상 SaaS라면 분당 5개도 많은 편이다. 본인 트래픽 패턴을 보고 조정하면 된다.

추가로 ZeroSSL을 fallback으로 묶어두면 한 CA가 막혀도 다른 CA로 발급을 시도한다. Caddy 기본 설정이 이미 Let's Encrypt → ZeroSSL 순으로 fallback 한다.

## 멀티테넌트 라우팅과 X-Tenant 헤더

서브도메인으로 테넌트를 식별하는 SaaS 패턴에서는 보통 백엔드가 같고, 호스트만 보고 어느 테넌트의 데이터를 가져올지 정한다. Caddy에서 placeholder로 슬러그를 뽑아 헤더에 넣어주면 백엔드는 단순히 `X-Tenant` 헤더만 읽으면 된다.

```caddy
*.app.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }

    @valid host_regexp tenant ^(?P<slug>[a-z][a-z0-9-]{2,30})\.app\.example\.com$

    handle @valid {
        reverse_proxy localhost:3000 {
            header_up X-Tenant {re.tenant.slug}
            header_up X-Original-Host {host}
        }
    }

    handle {
        respond "Invalid tenant slug" 400
    }
}
```

`header_up`은 Caddy가 백엔드로 요청을 보낼 때 추가하는 헤더다. 클라이언트가 보낸 헤더는 그대로 통과하므로, 클라이언트가 `X-Tenant: admin`을 직접 보내서 권한 우회를 노릴 수도 있다. `header_up X-Tenant`는 클라이언트가 보낸 같은 이름의 헤더를 덮어쓴다. 그래도 백엔드 코드에서는 항상 `X-Tenant`를 신뢰할 수 있는 출처(Caddy)에서만 받는다고 가정해야 한다. 외부 노출된 다른 경로로도 백엔드에 도달할 수 있다면 위험하다.

```caddy
handle @valid {
    request_header -X-Tenant
    reverse_proxy localhost:3000 {
        header_up X-Tenant {re.tenant.slug}
    }
}
```

`request_header -X-Tenant`로 클라이언트가 보낸 헤더를 먼저 제거한 뒤 우리가 다시 추가하면 더 안전하다.

## Apex와 서브도메인 동시 처리

apex 도메인(`example.com`)은 와일드카드 `*.example.com`에 매칭되지 않는다. 와일드카드는 정확히 한 라벨만 매치한다. 따라서 두 패턴을 모두 다루려면 명시적으로 둘 다 적어야 한다.

```caddy
example.com {
    redir https://www.example.com{uri} permanent
}

www.example.com, *.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }

    @www host www.example.com
    handle @www {
        root * /var/www/landing
        file_server
    }

    @app host_regexp tenant ^(?P<slug>[a-z][a-z0-9-]+)\.example\.com$
    handle @app {
        reverse_proxy localhost:3000 {
            header_up X-Tenant {re.tenant.slug}
        }
    }
}
```

apex는 따로 처리해서 www로 리다이렉트하고, www와 와일드카드를 한 블록에 묶어서 와일드카드 인증서 한 장을 받는다. 이 패턴이 SaaS에서 가장 흔하다.

반대로 www를 apex로 합치고 싶으면 방향만 바꾸면 된다.

```caddy
www.example.com {
    redir https://example.com{uri} permanent
}

example.com, *.example.com {
    # ...
}
```

이때 한 가지 함정이 있다. apex와 와일드카드가 동시에 들어가면 SAN 두 개짜리 인증서가 필요한데, DNS-01 챌린지가 두 도메인 모두에 대해 통과해야 한다. Cloudflare 같은 프로바이더는 보통 문제가 없지만, apex만 다른 DNS 운영사에 맡기고 서브도메인은 자체 운영하는 식으로 분리되어 있으면 한쪽만 발급에 실패해서 전체가 안 된다. 발급 로그를 보면 어느 도메인에서 막혔는지 나온다.

## 로컬 개발에서 와일드카드 자체 서명 인증서

운영에서 `*.example.com`을 쓰면 로컬에서 테스트할 때도 비슷한 환경을 만들고 싶다. `*.localhost`는 모든 OS에서 자동으로 127.0.0.1로 해석되므로 hosts 파일 수정 없이 와일드카드 도메인을 흉내낼 수 있다.

```caddy
*.localhost {
    tls internal

    @tenant host_regexp slug ^(?P<slug>[a-z0-9-]+)\.localhost$
    handle @tenant {
        header_up X-Tenant {re.slug.slug}
        reverse_proxy localhost:3000
    }
}
```

`tls internal`은 Caddy가 자체 CA를 만들어서 사인한다는 뜻이다. 첫 실행 시 운영체제 신뢰 저장소에 Caddy CA를 등록하라고 sudo 권한을 요청한다. 한 번 등록해두면 브라우저에서 `https://tenant1.localhost`로 접속해도 인증서 경고가 안 뜬다.

curl이나 다른 클라이언트는 시스템 신뢰 저장소를 안 보는 경우가 있어서 별도로 CA를 신뢰시키거나 `-k` 옵션으로 검증을 끄고 써야 한다. Caddy CA 위치는 `caddy environ` 명령으로 확인할 수 있다.

이 패턴으로 로컬에서 멀티테넌트 라우팅을 그대로 테스트할 수 있다. 운영 Caddyfile에서 호스트 부분만 `*.example.com` → `*.localhost`로 바꾸면 동일한 라우팅 로직이 동작한다.

## www ↔ apex 리다이렉트

검색엔진 SEO 관점이나 일관성 측면에서 한쪽으로 정리하는 게 일반적이다. Caddy는 `redir`로 간단히 처리한다.

```caddy
# www → apex
www.example.com {
    redir https://example.com{uri} permanent
}

example.com {
    reverse_proxy localhost:3000
}
```

`{uri}`는 path와 query string을 모두 포함한다. `permanent`는 301로 응답하라는 뜻이고, 임시 리다이렉트는 `temporary`(302)다. 처음에는 무조건 `temporary`로 시작해서 동작 확인 후 `permanent`로 바꾸는 게 안전하다. 301은 브라우저가 캐시해서 잘못 설정하면 한참 동안 안 풀린다.

서브도메인 통째로 다른 도메인으로 옮길 때도 같은 패턴이다.

```caddy
old-api.example.com {
    redir https://api.example.com{uri} permanent
}
```

## Cloudflare 프록시 모드와 챌린지 충돌

Cloudflare를 DNS 프로바이더로 쓰면서 동시에 프록시 모드(주황색 구름)를 켜둔 도메인에서 자주 막힌다. 상황별로 정리하면 이렇다.

**HTTP-01 챌린지의 경우**: Cloudflare 프록시가 켜져 있으면 ACME 챌린지 요청이 Cloudflare를 거쳐서 오는데, Cloudflare가 자기 인증서로 응답하므로 Caddy가 받기 전에 끝난다. 이 경우 발급은 되지만 Caddy가 받은 인증서는 Cloudflare ↔ origin 구간에서 안 쓰이고, 외부에서 보이는 건 Cloudflare 인증서다. 운영상 문제는 없지만 직관적이지 않다.

**DNS-01 챌린지의 경우**: 프록시 모드와 무관하게 동작한다. Caddy가 Cloudflare API로 TXT 레코드를 만들고 ACME 서버가 그걸 조회하는 방식이라 트래픽 경로와 상관없다. 그래서 Cloudflare를 쓰면 DNS-01이 가장 안전하다.

**On-Demand TLS와 프록시 모드 충돌**: 고객 커스텀 도메인을 받는 SaaS에서, 고객이 자기 도메인을 Cloudflare 프록시 모드로 우리 origin에 연결하면 Caddy가 받는 SNI는 고객 도메인이지만 인증서는 Cloudflare가 처리한다. 이 경우 우리 Caddy는 인증서를 발급할 필요가 없고, On-Demand가 동작하면 안 된다. 고객에게는 "DNS only"(회색 구름)로 우리 origin을 가리키도록 안내해야 한다. 안 그러면 발급 시도가 계속 일어나서 rate limit 위험이 있다.

## 트러블슈팅 — 발급 실패 진단

DNS-01 발급 실패는 보통 다음 패턴이다.

**ACME 서버가 TXT 레코드를 못 봄**: `propagation_delay`가 너무 짧다. 30초에서 시작해서 60초, 120초로 늘려본다. Cloudflare는 30초로 충분한 경우가 많지만 최근에 zone 변경이 있었으면 더 걸린다.

**API 토큰 권한 부족**: 로그에 `403 Forbidden` 또는 `Authentication error`가 찍힌다. Cloudflare는 `Zone:Read`와 `DNS:Edit` 두 권한이 zone 단위로 필요하다. "All zones"에 부여하든 특정 zone에만 부여하든 둘 다 있어야 한다.

**Rate limit**: `too many certificates already issued`. Let's Encrypt는 같은 도메인 세트로 주당 5회 발급, 같은 등록 도메인에 대해 주당 50개 인증서 한도가 있다. On-Demand에서 ask 검증이 느슨해서 무한 발급이 일어났거나, 설정 변경으로 인증서를 자주 재발급했을 때 걸린다. 일단 걸리면 일주일 가까이 풀리지 않는다. 테스트 중이라면 staging endpoint를 써야 한다.

```caddy
{
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
}
```

staging은 발급량 제한이 훨씬 느슨하다. 인증서 자체는 브라우저가 신뢰하지 않아서 경고가 뜨지만, 발급 흐름이 동작하는지 확인하는 용도로는 충분하다. 운영 전환 시 옵션을 빼면 된다.

**On-Demand 발급이 즉시 실패**: ask 엔드포인트가 5xx나 timeout인지 확인한다. ask 자체에 짧은 timeout(2~3초)을 걸어두면 백엔드가 느려도 발급 흐름이 멈추지 않는다.

```caddy
{
    on_demand_tls {
        ask http://localhost:9000/check-domain
    }
}
```

ask URL은 반드시 HTTP로 두는 게 좋다. HTTPS로 두면 자기 자신의 인증서 발급을 ask가 가로막는 닭과 달걀 문제가 생긴다.

## 정리

서브도메인 처리 방식은 결국 세 가지로 나뉜다.

미리 알고 있는 고정 서브도메인이 적으면 사이트 블록 분리가 가장 안전하고 단순하다. 서브도메인이 많거나 동적으로 추가되지만 도메인은 우리 거면 와일드카드 + DNS-01이다. 고객이 자기 도메인을 들고 오는 SaaS면 On-Demand TLS이고 ask 엔드포인트 설계가 핵심이다.

이 세 패턴을 섞어 쓸 수도 있다. 예를 들어 메인 SaaS 도메인은 와일드카드 + DNS-01로 처리하고, 고객 커스텀 도메인은 별도 사이트 블록에서 On-Demand로 처리하는 식이다. 핵심은 인증서가 어디서 발급되고 누가 책임지는지 명확하게 구분하는 것이다.
