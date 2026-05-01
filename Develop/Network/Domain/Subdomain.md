---
title: 서브도메인 (Subdomain)
tags: [network, domain, dns, subdomain, multi-tenant, wildcard, nginx]
updated: 2026-05-01
---

# 서브도메인 (Subdomain)

## 개요

### 서브도메인이란
서브도메인은 메인 도메인 앞에 추가로 붙는 식별자다. `example.com`이 메인 도메인이라면 `api.example.com`, `blog.example.com`, `admin.example.com` 같은 것들이 서브도메인이다. 하나의 도메인을 구입하면 그 아래에 사실상 무제한으로 서브도메인을 만들 수 있고, 추가 비용도 들지 않는다.

실무에서 서브도메인은 단순히 주소를 나눠주는 도구가 아니다. 트래픽 분리, 서비스 격리, 멀티테넌트 SaaS의 테넌트 식별, CDN 분기, 인증 쿠키 스코프 제어 등 서버 아키텍처 전반에 걸쳐 영향을 준다. 도메인 한 글자 차이로 쿠키가 전송되거나 전송되지 않고, CORS가 막히거나 풀리고, 인증서가 갱신되거나 실패한다.

### 도메인 계층 구조
도메인 이름은 오른쪽에서 왼쪽으로 읽는다. 가장 오른쪽이 최상위, 가장 왼쪽이 최하위다.

```
api.staging.example.com.
│   │       │       │  │
│   │       │       │  └─ 루트 도메인 (보통 생략됨, FQDN에서만 표기)
│   │       │       └──── TLD (Top Level Domain): com
│   │       └──────────── 2차 도메인 (Second Level): example
│   └──────────────────── 3차 도메인 / 서브도메인: staging
└──────────────────────── 4차 도메인 / 서브도메인: api
```

- **루트(Root)**: 모든 도메인의 최상단. FQDN(Fully Qualified Domain Name) 표기시 끝에 점(`.`)으로 표시한다. 일반적으로 생략된다.
- **TLD**: `com`, `org`, `net`, `kr`, `co.kr` 같은 것. 등록 기관(Registry)이 관리한다.
- **2차 도메인**: 우리가 돈 주고 등록하는 부분. `example.com`의 `example`이 여기다.
- **서브도메인**: 2차 도메인 왼쪽에 붙는 모든 것. 깊이 제한은 사실상 없지만 길어지면 관리가 어려워진다.

여기서 자주 헷갈리는 게 있다. `co.kr`은 TLD인가 2차 도메인인가? 형식적으로는 `kr`이 TLD고 `co`가 2차다. 하지만 실제로는 `co.kr` 전체가 등록 단위라서 Public Suffix List에서는 효과적인 TLD(eTLD)로 취급한다. 이게 뭐가 중요하냐면 쿠키 스코프와 SameSite 정책이 eTLD+1 단위로 동작하기 때문이다. 뒤에서 자세히 다룬다.

### 서브도메인을 쓰는 이유
실무에서 서비스를 서브도메인으로 분리하는 이유는 보통 이렇다.

**서비스 격리**: API와 웹 프론트엔드를 분리하면 한쪽이 죽어도 다른 쪽은 살아있다. `api.example.com`은 백엔드 클러스터로, `www.example.com`은 CDN으로 라우팅하면 된다.

**테넌트 분리**: 멀티테넌트 SaaS에서 `tenant1.app.com`, `tenant2.app.com` 같은 식으로 테넌트마다 고유한 주소를 준다. 마케팅 효과도 있고 데이터 격리도 명확해진다.

**환경 분리**: `staging.example.com`, `dev.example.com`처럼 환경별로 분리한다. 운영과 스테이징이 같은 도메인에 있으면 쿠키가 섞여서 사고 난다.

**SEO와 캐싱**: 정적 자원을 `static.example.com`이나 `cdn.example.com`으로 분리하면 메인 도메인 쿠키가 정적 자원 요청에 따라가지 않아 캐시 히트율이 올라간다.

## DNS 레코드 설정

### A 레코드와 CNAME 레코드
서브도메인을 만들려면 DNS에 레코드를 추가해야 한다. 주로 쓰는 건 A, AAAA, CNAME이다.

```
# A 레코드: 도메인을 IPv4 주소로 매핑
api.example.com.        300     IN      A       192.0.2.10

# AAAA 레코드: IPv6
api.example.com.        300     IN      AAAA    2001:db8::1

# CNAME 레코드: 다른 도메인으로 별칭
www.example.com.        300     IN      CNAME   example.com.
cdn.example.com.        300     IN      CNAME   d1234.cloudfront.net.
```

A 레코드는 직접 IP를 박는 거고 CNAME은 다른 도메인 이름으로 위임하는 거다. 실무에서 가장 많이 실수하는 게 `apex 도메인(루트 도메인)에 CNAME을 박는 것`이다. RFC 1034에 따르면 `example.com` 같은 apex 레코드에는 CNAME을 사용할 수 없다. SOA, NS 레코드와 충돌하기 때문이다. 그래서 AWS Route53의 ALIAS, Cloudflare의 CNAME Flattening 같은 우회 기능이 등장했다.

### ALIAS와 ANAME
ALIAS 레코드는 표준 DNS 스펙에는 없는 비표준 확장이다. Route53, DNSimple, Cloudflare 같은 매니지드 DNS 서비스에서 제공한다. 동작은 CNAME과 비슷하지만 apex 도메인에서도 쓸 수 있고, 응답할 때는 A 레코드처럼 IP를 직접 돌려준다.

```
# Route53 콘솔에서 (Hosted Zone)
example.com.    A       ALIAS d1234.cloudfront.net.    (apex에 alb/cloudfront 연결)
www.example.com. CNAME  d1234.cloudfront.net.          (서브도메인은 그냥 CNAME)
```

ALIAS는 DNS 서버 내부에서 타깃의 IP를 미리 해석해서 응답하기 때문에 클라이언트는 한 번의 조회로 IP를 받는다. CNAME은 클라이언트가 다시 한 번 조회를 해야 한다. 그래서 응답 속도 면에서 ALIAS가 약간 유리하다.

### 와일드카드 레코드
서브도메인이 동적으로 늘어나는 멀티테넌트 서비스에서는 와일드카드 레코드를 쓴다.

```
# 와일드카드 A 레코드
*.example.com.          300     IN      A       192.0.2.10

# 와일드카드 CNAME
*.tenants.example.com.  300     IN      CNAME   app.example.com.
```

`*.example.com`은 `foo.example.com`, `bar.example.com` 등 명시적으로 등록되지 않은 모든 1단계 서브도메인에 매칭된다. 다만 와일드카드는 한 단계만 커버한다. `*.example.com`은 `a.b.example.com`에 매칭되지 않는다. 깊은 단계까지 커버하려면 `*.b.example.com`을 따로 추가해야 한다.

또 명시적으로 등록된 레코드가 있으면 와일드카드보다 우선한다. 예를 들어 `*.example.com`과 `api.example.com`이 둘 다 있으면 `api.example.com`은 명시 레코드를 따른다.

와일드카드의 함정 중 하나는 메일이다. 와일드카드 A를 박아두면 `존재하지않는주소@nonexist.example.com`으로 메일을 보낼 때 메일 서버가 SPF나 MX 조회 결과를 이상하게 받아들일 수 있다. MX 와일드카드도 함께 관리하지 않으면 스팸 발송지로 악용될 가능성도 있다.

### TTL 설정
서브도메인 추가나 IP 변경시 TTL은 중요하다. TTL이 86400(1일)인 레코드를 변경하면 전 세계 리졸버 캐시가 만료될 때까지 하루 가까이 기다려야 한다. 마이그레이션 며칠 전에 TTL을 60~300초로 낮춰두고, 마이그레이션이 끝나고 안정화되면 다시 올리는 패턴이 일반적이다.

```
# 마이그레이션 1주일 전: TTL 낮추기
api.example.com.        86400   IN      A       192.0.2.10
                          ↓
api.example.com.        300     IN      A       192.0.2.10

# 마이그레이션 당일: IP 변경
api.example.com.        300     IN      A       198.51.100.20

# 안정화 후: TTL 복원
api.example.com.        86400   IN      A       198.51.100.20
```

## Nginx server_name과 가상 호스트

### server_name 매칭 규칙
Nginx에서 서브도메인 라우팅은 `server_name` 지시어로 한다. 같은 80/443 포트로 들어온 요청을 Host 헤더로 구분해서 다른 server 블록으로 보낸다.

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://api_backend;
    }
}

server {
    listen 80;
    server_name www.example.com example.com;

    root /var/www/main;
}
```

`server_name` 매칭 우선순위는 다음과 같다.

1. 정확히 일치하는 이름 (`api.example.com`)
2. 가장 긴 와일드카드 (앞쪽 `*`): `*.example.com`
3. 가장 긴 와일드카드 (뒤쪽 `*`): `mail.*`
4. 정규식 (등장 순서대로)
5. 매칭되는 게 없으면 `default_server` 또는 처음 정의된 server 블록

### 와일드카드 서브도메인 처리
멀티테넌트 환경에서 테넌트 서브도메인을 한 server 블록으로 받아서 애플리케이션에서 분기 처리하는 패턴.

```nginx
server {
    listen 443 ssl http2;
    server_name ~^(?<tenant>[a-z0-9-]+)\.app\.example\.com$;

    ssl_certificate     /etc/letsencrypt/live/wildcard/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wildcard/privkey.pem;

    location / {
        proxy_set_header X-Tenant $tenant;
        proxy_set_header Host $host;
        proxy_pass http://app_backend;
    }
}
```

정규식 캡처 그룹으로 테넌트 이름을 뽑아 헤더로 넘겨주면 백엔드에서 굳이 Host 헤더를 다시 파싱할 필요가 없다. 테넌트 이름에 허용되는 문자를 `[a-z0-9-]`로 제한하는 건 보안 측면에서 중요하다. 검증 안 된 호스트명을 그대로 백엔드에 넘기면 호스트 헤더 인젝션 공격에 노출된다.

### default_server의 함정
서버에 등록되지 않은 호스트로 요청이 오면 첫 번째 server 블록이나 `default_server`로 라우팅된다. 그래서 의도하지 않은 도메인이 우리 서버 IP로 향하는 경우 우리 메인 사이트가 응답할 수 있다. 검색 엔진에서 잘못된 도메인이 우리 사이트로 인덱싱되거나, SEO에 안 좋은 영향을 줄 수 있다.

방어를 위해 catch-all default 블록을 명시적으로 만든다.

```nginx
server {
    listen 80 default_server;
    listen 443 ssl default_server;
    server_name _;

    ssl_certificate     /etc/ssl/dummy.crt;
    ssl_certificate_key /etc/ssl/dummy.key;

    return 444;  # 응답 없이 연결 종료
}
```

`return 444`는 Nginx 전용 비표준 코드로 응답 없이 그냥 커넥션을 끊는다. 이렇게 하면 우리 서비스에 등록되지 않은 호스트로 들어오는 요청은 모두 차단된다.

## TLS 인증서와 SAN

### Subject Alternative Name (SAN)
하나의 인증서로 여러 도메인을 보호하려면 SAN(Subject Alternative Name) 확장을 사용한다. CN(Common Name)은 사실상 deprecated 됐고 모든 브라우저가 SAN을 본다.

```
Certificate:
    Subject: CN=example.com
    X509v3 Subject Alternative Name:
        DNS:example.com
        DNS:www.example.com
        DNS:api.example.com
        DNS:admin.example.com
```

SAN에 명시된 도메인만 인증서가 유효하다. `api.example.com`이 SAN에 없는데 그 도메인으로 HTTPS 접속하면 브라우저가 NET::ERR_CERT_COMMON_NAME_INVALID를 띄운다.

### 와일드카드 인증서
서브도메인이 동적으로 늘어나는 환경에서는 와일드카드 인증서를 발급받는다.

```
Subject Alternative Name:
    DNS:example.com
    DNS:*.example.com
```

와일드카드 인증서 발급시 알아둘 점.

**한 단계만 커버한다**: `*.example.com` 인증서는 `api.example.com`에는 유효하지만 `v1.api.example.com`에는 유효하지 않다. 깊은 서브도메인까지 커버하려면 `*.api.example.com`을 별도로 SAN에 추가해야 한다.

**Apex 도메인은 커버 안 한다**: `*.example.com`은 `example.com` 자체에는 매칭되지 않는다. 둘 다 보호하려면 SAN에 `example.com`을 명시적으로 추가해야 한다.

**DNS-01 챌린지가 필수**: Let's Encrypt에서 와일드카드 인증서를 받으려면 HTTP-01 챌린지로는 안 되고 DNS-01 챌린지만 가능하다. 자동화하려면 DNS API에 접근할 수 있는 ACME 클라이언트가 필요하다.

```bash
# Certbot으로 와일드카드 인증서 받기 (Cloudflare DNS API 예시)
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
  -d "example.com" \
  -d "*.example.com"
```

**갱신시 DNS 전파 시간 주의**: TXT 레코드를 추가하고 전 세계 DNS 서버에 전파되기를 기다려야 한다. 보통 60~120초 정도면 되는데 가끔 더 걸린다. ACME 클라이언트에 적절한 propagation delay를 설정해두지 않으면 갱신이 실패한다.

### 다중 도메인 SAN과 와일드카드 조합
실무에서는 와일드카드 SAN과 일반 SAN을 섞어서 쓴다.

```
SAN:
    DNS:example.com
    DNS:*.example.com
    DNS:*.app.example.com
    DNS:*.api.example.com
```

이렇게 하면 `example.com`, `www.example.com`, `tenant1.app.example.com`, `v1.api.example.com` 모두 커버할 수 있다. 단, Let's Encrypt는 한 인증서당 100개의 SAN까지 허용한다. 또한 SAN이 많아지면 인증서 파일 자체가 커지고 TLS 핸드셰이크 페이로드도 커진다.

## 멀티테넌트 SaaS 패턴

### 테넌트별 서브도메인 라우팅
B2B SaaS에서 가장 흔한 패턴은 테넌트마다 서브도메인을 할당하는 것이다.

```
acme.app.example.com      → ACME 회사 테넌트
globex.app.example.com    → Globex 회사 테넌트
initech.app.example.com   → Initech 회사 테넌트
```

DNS 설정은 와일드카드 한 줄로 끝난다.

```
*.app.example.com.      300     IN      A       192.0.2.10
```

애플리케이션 레이어에서 Host 헤더 또는 Nginx에서 캡처한 테넌트 이름으로 요청 컨텍스트에 테넌트 ID를 매핑한다.

```typescript
// Express.js 예시
app.use((req, res, next) => {
  const host = req.hostname;  // acme.app.example.com
  const match = host.match(/^([a-z0-9-]+)\.app\.example\.com$/);

  if (!match) {
    return res.status(400).send('Invalid host');
  }

  const tenantSlug = match[1];
  const tenant = await TenantRepo.findBySlug(tenantSlug);

  if (!tenant) {
    return res.status(404).send('Tenant not found');
  }

  req.tenant = tenant;
  next();
});
```

### 테넌트 식별과 격리
서브도메인을 그냥 라우팅 키로만 쓰지 말고 인증/인가 컨텍스트에 묶어야 한다. 예를 들어 `acme.app.example.com`에서 받은 JWT가 `globex.app.example.com`에서도 통하면 큰일이다. 토큰에 테넌트 ID를 박고 미들웨어에서 토큰의 테넌트와 호스트의 테넌트가 일치하는지 검증한다.

```typescript
function verifyTenantContext(req, res, next) {
  const hostTenantId = req.tenant.id;
  const tokenTenantId = req.user.tenantId;

  if (hostTenantId !== tokenTenantId) {
    return res.status(403).send('Tenant mismatch');
  }

  next();
}
```

### 커스텀 도메인 지원
대부분의 SaaS는 어느 시점부터 고객이 자기 도메인(`app.acme.com`)을 쓰고 싶다고 요구한다. 이때 패턴은 두 가지다.

첫 번째는 고객이 자기 DNS에 CNAME을 박고 우리 시스템에 등록하는 방식이다.

```
# 고객 측 DNS
app.acme.com.    CNAME    customers.example.com.

# 우리 시스템 데이터베이스
custom_domains 테이블에 app.acme.com → tenant_id 매핑 저장
```

들어오는 요청의 Host 헤더로 매핑 테이블을 조회해서 테넌트를 결정한다. 이 방식의 어려운 점은 인증서다. 고객 도메인마다 인증서가 필요하다. ACME `HTTP-01` 챌린지를 쓰면 우리 인프라에서 자동 발급할 수 있는데, Cloudflare for SaaS, AWS ACM, Caddy 같은 솔루션이 이걸 자동화해준다.

두 번째는 CNAME 대신 SOA 위임을 받는 방식이다. 고객이 `app.acme.com`의 NS 레코드를 우리 네임서버로 위임하면 우리가 그 도메인의 DNS를 통째로 관리한다. 자유도는 높지만 고객 입장에서 동의하기 어려운 경우가 많다.

## 쿠키 도메인 스코프

### Domain 속성과 동작 방식
쿠키의 `Domain` 속성은 어떤 호스트로 보낼 때 이 쿠키를 첨부할지 결정한다. 이게 서브도메인을 다룰 때 가장 자주 사고 나는 부분이다.

```
Set-Cookie: session=abc123; Domain=example.com; Path=/; Secure; HttpOnly
```

Domain을 `example.com`으로 설정하면 `example.com`, `www.example.com`, `api.example.com`, `nested.foo.example.com` 모두에 이 쿠키가 전송된다. 즉 도메인과 모든 서브도메인을 커버한다.

```
Set-Cookie: session=abc123; Domain=app.example.com; Path=/; Secure; HttpOnly
```

Domain을 `app.example.com`으로 설정하면 `app.example.com`과 그 서브도메인(`a.app.example.com`, `b.app.example.com`)에는 가지만 `api.example.com`이나 `example.com`에는 가지 않는다.

Domain 속성을 아예 생략하면 쿠키를 설정한 정확한 호스트에만 전송된다. `example.com`에서 Domain 없이 쿠키를 발급하면 `www.example.com`에는 안 간다. 이걸 host-only 쿠키라고 한다.

### 옛날 점 표기법(.example.com)
RFC 6265 이전 명세에서는 `Domain=.example.com`처럼 앞에 점을 붙여서 서브도메인 포함을 명시했다. RFC 6265에서는 점 유무에 상관없이 동일하게 처리하도록 표준화됐다. 실무에서는 점 없이 쓰는 게 일반적이지만 옛날 코드베이스에서 점 붙은 표기를 종종 본다.

### 멀티테넌트에서 쿠키가 새는 문제
멀티테넌트 SaaS에서 쿠키 도메인을 잘못 설정하면 테넌트 간 정보가 새어나간다.

```
# 잘못된 설정
Set-Cookie: session=acme_user_token; Domain=app.example.com
```

이렇게 하면 `acme.app.example.com`에서 발급한 쿠키가 `globex.app.example.com`으로 가는 모든 요청에 포함된다. 다른 테넌트 사용자가 자기 도메인에서 우리 백엔드로 요청을 보내면 ACME 사용자의 세션 쿠키가 그쪽으로도 간다는 얘기다.

해결 방법은 쿠키 Domain을 설정하지 않거나(host-only) 테넌트 도메인에 정확히 매칭시키는 것이다.

```
# 올바른 설정 - host-only 쿠키
Set-Cookie: session=acme_user_token; Path=/; Secure; HttpOnly; SameSite=Lax
# Domain 속성 없음 → acme.app.example.com에서만 유효
```

### SameSite 속성
SameSite는 크로스 사이트 요청에서 쿠키 전송 여부를 제어한다. 값은 `Strict`, `Lax`, `None` 세 가지가 있다.

- **Strict**: 같은 사이트에서 시작한 요청에만 쿠키 전송. 외부 링크 클릭으로 들어와도 쿠키 안 감.
- **Lax**: top-level navigation(주소창 입력, 링크 클릭)에는 쿠키 전송. iframe, AJAX, 이미지 로드 같은 서브 요청에는 안 감. 2020년부터 크롬 기본값.
- **None**: 모든 요청에 쿠키 전송. 단 `Secure` 속성이 있어야 한다(HTTPS 전용).

여기서 "같은 사이트(same-site)"의 정의가 중요하다. 브라우저는 eTLD+1 단위로 같은 사이트를 판단한다. 즉 `api.example.com`에서 `app.example.com`으로 요청을 보내면 같은 사이트로 본다. 둘 다 eTLD+1인 `example.com` 아래에 있기 때문이다. 반면 `example.com`에서 `another.com`으로 가는 요청은 cross-site다.

### 서브도메인 간 요청과 SameSite
서브도메인 분리 아키텍처(`app.example.com` 프론트엔드 + `api.example.com` 백엔드)에서 쿠키 동작은 이렇다.

```
# 프론트엔드에서 백엔드로 fetch
fetch('https://api.example.com/data', { credentials: 'include' })
```

쿠키 설정이 `Domain=example.com; SameSite=Lax`이면 same-site 요청이라 쿠키가 전송된다. 만약 백엔드가 다른 eTLD+1 도메인이면(`example.com` → `api.somewhere.com`) cross-site가 되고, 그러면 SameSite=None; Secure이 필요하다.

## CORS와 서브도메인 간 통신

### Same-Origin 정책의 도메인 단위
SOP(Same-Origin Policy)에서 origin은 protocol + host + port 조합이다. 호스트는 정확히 일치해야 한다. `example.com`과 `api.example.com`은 서로 cross-origin이다. 같은 사이트(same-site)지만 같은 출처(same-origin)는 아니다.

이 차이를 헷갈리는 경우가 많은데 정리하면 이렇다.

```
example.com            ↔ api.example.com         : cross-origin, same-site
example.com            ↔ example.com:8080        : cross-origin, same-site
http://example.com     ↔ https://example.com     : cross-origin, same-site
example.com            ↔ another.com             : cross-origin, cross-site
```

### CORS 헤더 설정
서브도메인 간 통신에서 CORS 헤더는 필수다. 백엔드에서 응답할 때 이렇게 보낸다.

```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
```

여기서 가장 자주 실수하는 게 `Access-Control-Allow-Origin: *`와 `Access-Control-Allow-Credentials: true`를 같이 쓰려다가 안 되는 거다. 자격증명(쿠키 포함) 요청에는 와일드카드를 쓸 수 없다. 명시적인 origin을 돌려줘야 한다.

```typescript
// Express.js에서 동적으로 origin 허용
const allowedOrigins = [
  'https://app.example.com',
  'https://admin.example.com',
];

app.use((req, res, next) => {
  const origin = req.headers.origin;

  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Vary', 'Origin');
  }

  next();
});
```

`Vary: Origin` 헤더를 빼먹으면 CDN이 한 응답을 캐시해서 다른 origin에 그대로 돌려주는 사고가 난다.

### 멀티테넌트에서의 CORS
테넌트마다 서브도메인이 다른 SaaS에서는 origin이 동적이다. 정규식으로 검증해서 와일드카드 식으로 허용한다.

```typescript
const tenantOriginPattern = /^https:\/\/[a-z0-9-]+\.app\.example\.com$/;

app.use((req, res, next) => {
  const origin = req.headers.origin;

  if (origin && tenantOriginPattern.test(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Vary', 'Origin');
  }

  next();
});
```

정규식을 너무 느슨하게 짜면 `evil.app.example.com.attacker.com` 같은 우회가 가능하다. 끝부분 앵커(`$`)를 반드시 붙여야 한다.

## 서브도메인 테이크오버 취약점

### 어떻게 발생하는가
서브도메인 테이크오버는 DNS에는 서브도메인이 등록돼 있는데 그 서브도메인이 가리키는 외부 서비스(Heroku, S3, GitHub Pages, Azure 등)는 더 이상 사용되지 않을 때 발생한다. 공격자가 그 외부 서비스에 동일한 이름으로 신규 등록하면 우리 도메인을 통째로 가져갈 수 있다.

```
# 회사 DNS에 남아있는 dangling 레코드
old-marketing.example.com.    CNAME    abandoned-app.herokuapp.com.

# Heroku에서는 abandoned-app이 이미 삭제됨
# 공격자가 Heroku에 abandoned-app 이름으로 새 앱 생성
# → 공격자가 old-marketing.example.com 호스팅 권한 획득
```

이 상태에서 공격자가 만든 페이지가 `old-marketing.example.com`에서 서비스되면 신뢰할 수 있는 도메인으로 위장한 피싱이 가능하다. 또 쿠키 Domain이 `example.com`으로 풀려있으면 공격자 페이지에서 우리 메인 사이트의 쿠키도 읽거나 쓸 수 있다.

### 방어 방법
**DNS 레코드 정기 감사**: 외부 서비스로 향하는 CNAME을 주기적으로 점검한다. 해당 외부 서비스에 실제로 우리 리소스가 살아있는지 확인한다.

**서비스 해지 순서**: 외부 서비스를 해지하기 전에 DNS 레코드를 먼저 삭제한다. 순서를 바꾸면 잠깐이라도 dangling 상태가 생긴다.

**자동화 스캔**: `subzy`, `subjack`, `aquatone` 같은 오픈소스 도구로 자동 스캔한다. 외부 서비스마다 take-over 가능 여부 시그니처가 정리돼 있다.

**SPF/DKIM 레코드도 확인**: A/CNAME뿐 아니라 SPF, DKIM, MX 같은 레코드의 외부 의존성도 같이 봐야 한다. 메일 서비스 해지 후 SPF에 빠진 도메인이 남아있으면 메일 스푸핑 위험이 있다.

## eTLD+1과 Public Suffix List

### eTLD의 정의
eTLD(effective TLD)는 사용자가 직접 도메인을 등록할 수 있는 가장 깊은 단계다. `com`은 eTLD다. `co.kr`도 eTLD다. 사용자가 `com`이나 `co.kr` 자체를 살 순 없고 그 아래에 `example.com`, `example.co.kr`을 등록한다. eTLD+1은 eTLD에서 한 단계 더 들어간 단위, 즉 등록 가능한 가장 짧은 도메인이다.

이걸 정확히 알아야 하는 이유는 브라우저가 보안 결정을 eTLD+1 단위로 하기 때문이다.

- 쿠키 Domain 속성: eTLD까지 좁힐 수는 없다. `Domain=com`은 거부된다.
- SameSite 정책의 same-site 판단: eTLD+1이 같으면 same-site.
- localStorage, IndexedDB 격리: origin 단위지만 일부 정책은 eTLD+1 단위.

### Public Suffix List
Public Suffix List(PSL)는 Mozilla가 관리하는 eTLD 목록이다. 어떤 도메인 접미사가 effective TLD로 취급되어야 하는지 명시돼 있다. 브라우저, OS, 보안 도구가 이 리스트를 참고한다.

```
# PSL 일부 예시
com
co.kr
ne.kr
github.io
appspot.com
herokuapp.com
```

`github.io`나 `herokuapp.com`이 PSL에 들어있는 게 흥미롭다. GitHub Pages는 사용자마다 `username.github.io`를 발급한다. 만약 `github.io`가 PSL에 없으면 `userA.github.io`에서 발급한 쿠키가 `userB.github.io`로 흘러들어가서 사용자 간 정보가 새어버린다. 그래서 PaaS 회사들은 자기 도메인을 PSL에 등록한다.

우리도 멀티테넌트 SaaS를 운영하면서 테넌트마다 서브도메인을 발급하는 구조라면 `app.example.com`을 PSL에 등록하는 걸 검토해야 한다. 등록되면 `tenant1.app.example.com`과 `tenant2.app.example.com`은 cross-site로 간주되고, 한쪽 쿠키가 다른 쪽으로 흘러갈 가능성이 차단된다.

## AWS Route53과 CloudFront 위임

### Route53 호스티드 존
AWS Route53에서 도메인을 관리하면 호스티드 존(Hosted Zone)이라는 단위로 작업한다. 도메인 하나당 하나의 호스티드 존을 만들고, 그 안에 레코드를 넣는다.

```
Hosted Zone: example.com
├── example.com           A      ALIAS d1234.cloudfront.net.
├── www.example.com       CNAME  d1234.cloudfront.net.
├── api.example.com       A      192.0.2.10
└── *.app.example.com     A      198.51.100.20
```

서브도메인을 별도의 호스티드 존으로 분리할 수도 있다. 예를 들어 `app.example.com`을 별도 팀이 관리한다면, `app.example.com` 호스티드 존을 만들고 부모 존(`example.com`)에서 NS 레코드로 위임한다.

```
# example.com 호스티드 존
app.example.com.    NS    ns-1234.awsdns-12.org.
app.example.com.    NS    ns-5678.awsdns-34.com.
app.example.com.    NS    ns-9012.awsdns-56.net.
app.example.com.    NS    ns-3456.awsdns-78.co.uk.

# app.example.com 호스티드 존 (별도 존)
app.example.com.        A      192.0.2.50
api.app.example.com.    A      192.0.2.51
```

이렇게 위임하면 `app.example.com` 존을 관리하는 팀은 부모 존을 건드리지 않고 자기 서브도메인 안에서 자유롭게 레코드를 추가/변경할 수 있다. 권한 분리에도 좋다.

### CloudFront와 alternate domain name
CloudFront 배포에 커스텀 도메인을 붙이려면 두 가지가 필요하다. CloudFront 측의 Alternate Domain Name(CNAME) 등록과 ACM 인증서다.

```
1. ACM에서 인증서 발급: example.com, *.example.com
   (단 ACM 와일드카드 인증서는 us-east-1에서 발급해야 CloudFront에 붙일 수 있음)

2. CloudFront 배포 설정:
   - Alternate Domain Names: example.com, *.example.com
   - Custom SSL Certificate: 위에서 발급한 ACM 인증서

3. Route53에서 ALIAS 레코드:
   example.com.        A    ALIAS d1234.cloudfront.net.
   *.example.com.      A    ALIAS d1234.cloudfront.net.
```

CloudFront는 같은 alternate domain name을 여러 배포에 동시 등록하지 못한다. 다른 계정에서 누군가 우리 도메인을 자기 배포에 박아두면 우리는 그 도메인을 등록 못 하는데 이게 호스트네임 도용 시나리오다. CloudFront는 이를 방지하기 위해 도메인 소유 검증을 추가한 SSL Certificate 또는 DNS 검증을 요구한다.

### 서브도메인 위임의 한계
부모 존(`example.com`)이 다른 서비스에 있고 자식 존(`app.example.com`)이 Route53에 있다면, 부모 측 DNS에 NS 레코드를 박아야 한다. 이걸 깜빡하고 자식 존의 레코드만 수정하면 외부에서는 변경 사항이 보이지 않는다. NS 레코드의 TTL과 리졸버 캐시 때문에 위임이 반영되는 데 시간이 걸리는 것도 자주 보는 문제다.

## 로컬 개발 환경에서 서브도메인 테스트

### /etc/hosts
가장 단순한 방법은 hosts 파일에 직접 등록하는 거다.

```
# /etc/hosts (Linux/macOS)
127.0.0.1   acme.app.localhost
127.0.0.1   globex.app.localhost
127.0.0.1   api.localhost
```

테넌트가 추가될 때마다 손으로 hosts를 수정해야 해서 동적인 환경에서는 한계가 있다. 와일드카드를 지원하지 않는다.

### dnsmasq
dnsmasq를 로컬에 설치하면 와일드카드 도메인을 한 줄로 처리할 수 있다.

```bash
# macOS에서 brew 설치
brew install dnsmasq

# 설정 (/usr/local/etc/dnsmasq.conf)
address=/.test/127.0.0.1
address=/.local.dev/127.0.0.1
```

이 설정은 `.test`로 끝나는 모든 호스트, `.local.dev`로 끝나는 모든 호스트를 127.0.0.1로 보낸다. `acme.app.test`, `foo.bar.test`, `whatever.local.dev` 모두 로컬로 향한다.

macOS에서는 추가로 `/etc/resolver/test` 파일을 만들어서 `.test` 도메인 조회시 dnsmasq를 사용하도록 지정한다.

```
# /etc/resolver/test
nameserver 127.0.0.1
```

### lvh.me와 nip.io
hosts 수정도 dnsmasq 설치도 귀찮다면 공개 와일드카드 DNS 서비스를 쓴다.

**lvh.me**: 모든 서브도메인이 127.0.0.1로 매핑된다. `acme.lvh.me`, `globex.app.lvh.me` 모두 로컬을 가리킨다.

```bash
curl http://acme.lvh.me:3000
curl http://globex.app.lvh.me:3000
```

**nip.io**: 도메인 안에 IP를 넣을 수 있다. `192.168.1.10.nip.io`는 192.168.1.10으로 매핑된다. 팀원과 같은 네트워크에서 개발할 때 유용하다.

```bash
# 같은 네트워크의 다른 머신에서 내 노트북에 접속
curl http://192-168-1-10.nip.io:3000
curl http://acme.192-168-1-10.nip.io:3000
```

이런 서비스의 단점은 외부 DNS 의존성이다. 인터넷이 끊기거나 해당 서비스가 죽으면 로컬 개발이 안 된다. 보안 관점에서도 외부에 도메인 조회 패턴이 노출된다는 점이 있다. 개인 개발용으로는 괜찮지만 회사 환경에서는 dnsmasq나 사내 DNS 서버를 쓰는 게 낫다.

### .localhost와 .test 도메인
RFC 6761은 특정 TLD를 특수 용도로 예약했다.

- `.localhost`: 항상 루프백을 가리켜야 한다. 모던 브라우저는 `*.localhost`를 자동으로 127.0.0.1로 해석한다.
- `.test`: 테스트용으로만 쓰도록 예약. 실제 인터넷에 등록되지 않는다.
- `.example`: 문서 예시용으로 예약.
- `.invalid`: 항상 무효한 도메인.

`.localhost`는 hosts 파일이나 별도 DNS 설정 없이도 바로 동작하는 경우가 많다. 다만 와일드카드가 모든 클라이언트에서 보장되진 않아서 hosts나 dnsmasq를 백업으로 두는 게 안전하다.

```bash
# 모던 브라우저/Node.js에서 바로 동작
curl http://api.localhost:3000
curl http://acme.app.localhost:3000
```

### 로컬 HTTPS와 와일드카드
서브도메인 라우팅을 쿠키와 함께 테스트하려면 HTTPS가 필요하다(특히 SameSite=None; Secure 케이스). `mkcert`로 로컬 와일드카드 인증서를 만든다.

```bash
# mkcert 설치 후 로컬 CA 등록
mkcert -install

# 와일드카드 인증서 생성
mkcert "*.app.localhost" "*.localhost" localhost 127.0.0.1
```

생성된 `*-cert.pem`과 `*-key.pem`을 로컬 Nginx나 개발 서버에 붙이면 브라우저에서 인증서 경고 없이 HTTPS로 서브도메인 테스트가 가능하다.

## 마무리

서브도메인은 단순히 주소를 나누는 도구처럼 보이지만 DNS, 인증서, 쿠키, CORS, 보안 정책이 얽혀있는 영역이다. 와일드카드 한 줄 추가하면서 "이러면 다 되겠지" 했다가 인증서 갱신 실패, 쿠키 누수, 테이크오버 취약점으로 사고 나는 케이스를 자주 본다. 서비스 도메인 구조를 설계할 때 다음 질문에 답할 수 있어야 한다.

이 서브도메인은 어느 인증서로 보호되는가. 와일드카드 인증서가 커버하는 단계가 맞는가. 이 서브도메인에서 발급한 쿠키는 다른 어떤 서브도메인으로 흘러가는가. 이 서브도메인은 Public Suffix List 등록이 필요한가. 외부 서비스로 향하는 CNAME이 더 이상 살아있지 않은 리소스를 가리키고 있지는 않은가. CORS 정규식은 끝 앵커가 제대로 붙어있는가.

이 질문들에 자신 있게 답할 수 있다면 서브도메인을 안전하게 다루고 있는 거다.
