---
title: 웹 캐시 포이즈닝 (Web Cache Poisoning)
tags: [security, cache, cdn, web-server]
updated: 2026-09-27
---

# 웹 캐시 포이즈닝 (Web Cache Poisoning)

CDN이나 리버스 프록시를 앞에 두면 같은 응답을 캐시에 저장해 두고 여러 사용자에게 재사용한다. 이때 캐시는 "이 요청과 저 요청이 같은 요청인가"를 판단하는 기준이 필요한데, 그게 캐시 키다. 보통 메서드 + 호스트 + 경로 + 쿼리스트링으로 키를 만든다. 문제는 응답 내용에 영향을 주는데 캐시 키에는 안 들어가는 입력값이 있을 때 생긴다. 이런 값을 unkeyed input이라고 부른다.

공격자가 unkeyed 입력으로 응답을 오염시키고, 그 오염된 응답이 캐시에 저장되면, 이후 같은 키로 들어오는 정상 사용자 전부가 오염된 응답을 받는다. 한 번의 요청으로 다수 사용자를 공격하는 게 캐시 포이즈닝의 핵심이다. XSS 페이로드를 캐시에 박아두면 그 페이지를 여는 사람 전부가 스크립트를 실행당한다.

저장형 XSS와 비슷해 보이지만 저장 위치가 DB가 아니라 캐시라는 점이 다르다. 그래서 캐시가 만료되거나 비워지면 사라지고, 캐시 키 조건이 맞는 동안만 유효하다. 대신 서버 코드를 안 건드려도 되고, 캐시 한 군데만 오염시키면 그 뒤로 들어오는 트래픽을 통째로 잡는다.

## 캐시 키와 unkeyed 입력

먼저 캐시 키에 뭐가 들어가는지 봐야 한다. 일반적인 CDN 기본 캐시 키는 이렇다.

```http
GET /products HTTP/1.1
Host: shop.example.com
```

여기서 키는 `GET + shop.example.com + /products` 정도다. 쿠키나 대부분의 요청 헤더는 키에 안 들어간다. 그런데 애플리케이션이 이런 헤더를 읽어서 응답에 반영하면 문제가 된다.

```http
GET /products HTTP/1.1
Host: shop.example.com
X-Forwarded-Host: evil.com
```

`X-Forwarded-Host`는 캐시 키에 안 들어간다(unkeyed). 그런데 애플리케이션이 이 헤더로 절대 URL을 만들면, 응답 안에 `evil.com`이 박힌다. 그 응답이 `/products` 키로 캐시되면, 이후 정상 사용자가 `/products`를 요청할 때 `evil.com`이 섞인 페이지를 받는다.

unkeyed 입력으로 자주 악용되는 헤더는 정해져 있다.

- `X-Forwarded-Host` — 애플리케이션이 호스트를 이걸로 잡는 경우
- `X-Forwarded-Scheme`, `X-Forwarded-Proto` — http/https 판단
- `X-Forwarded-Port`
- `X-Host`, `X-Forwarded-Server`
- `X-Original-URL`, `X-Rewrite-URL` — 일부 프레임워크가 경로를 덮어씀
- `Forwarded` (RFC 7239 표준 헤더)

공통점은 "프록시가 뒤쪽 서버에 원래 요청 정보를 전달하려고 쓰는 헤더"라는 것. 신뢰 경계 안에서만 쓰여야 하는데, 외부에서 그대로 들어와 애플리케이션까지 도달하면 오염 입력이 된다.

## Unkeyed 헤더 인젝션 원리

### X-Forwarded-Host 인젝션

애플리케이션이 절대 URL을 만들 때 요청 호스트를 쓰는 코드가 제일 많이 당한다. 비밀번호 재설정 메일 링크, canonical 링크, OG 태그, 리소스 절대 경로 같은 데서 호스트를 가져온다.

```javascript
// 취약: X-Forwarded-Host를 신뢰해서 절대 URL 생성
app.get('/products', (req, res) => {
  const host = req.headers['x-forwarded-host'] || req.headers['host'];
  res.send(`
    <link rel="canonical" href="https://${host}/products">
    <script src="https://${host}/static/app.js"></script>
  `);
});
```

`X-Forwarded-Host: evil.com`으로 요청하면 응답의 `<script src>`가 `https://evil.com/static/app.js`가 된다. 이 응답이 캐시되면, 정상 사용자가 `/products`를 열 때 `evil.com`에서 자바스크립트를 불러온다. 공격자가 그 경로에 악성 스크립트를 두면 끝이다.

재현은 단순하다. 캐시되는 경로에 `X-Forwarded-Host`를 붙여 한 번 요청하고, 응답에 그 값이 반영되는지 본다. 반영된다면 다음 정상 요청에서도 같은 값이 나오는지 확인한다.

```bash
# 1) 오염 요청
curl -s https://shop.example.com/products \
  -H 'X-Forwarded-Host: evil.com' | grep evil.com

# 2) 헤더 없이 정상 요청 — 같은 응답이 나오면 캐시 오염 성공
curl -s https://shop.example.com/products | grep evil.com
```

2번에서 `evil.com`이 나오면 캐시가 오염된 것이다. 응답 헤더의 `X-Cache: HIT`(또는 CDN별 비슷한 헤더), `Age` 값으로 캐시 적중 여부를 같이 확인한다.

### X-Original-URL / X-Rewrite-URL 인젝션

Symfony나 Laravel, 일부 Spring 설정에는 `X-Original-URL`이나 `X-Rewrite-URL` 헤더를 경로 결정에 쓰는 코드가 있다. 주로 URL 재작성 레이어가 프레임워크 앞에 붙어 있을 때 원래 경로를 전달하려는 목적이다.

문제는 이 헤더가 캐시 키에 없는 상태에서 외부 요청이 그대로 프레임워크까지 도달할 때다.

```http
GET /public/home HTTP/1.1
Host: example.com
X-Original-URL: /admin/dashboard
```

캐시는 `GET /public/home`으로 키를 잡는다. 백엔드 프레임워크는 `X-Original-URL`을 보고 `/admin/dashboard`를 처리한다. 응답이 `/public/home` 키로 캐시에 들어간다. 이후 정상 사용자가 `/public/home`을 요청하면 관리자 페이지가 나온다.

Symfony의 `HttpCache`는 이 헤더를 기본적으로 신뢰하도록 설계되어 있다. 신뢰 프록시 설정을 안 하면 외부에서 온 `X-Original-URL`도 그대로 받아들인다.

```php
// Symfony — 신뢰 프록시를 명시하지 않으면 X-Original-URL을 외부에서 주입 가능
// setTrustedProxies()로 엣지 프록시 IP만 신뢰하도록 설정해야 한다
Request::setTrustedProxies(
    ['192.168.1.1', '10.0.0.0/8'],
    Request::HEADER_X_FORWARDED_ALL
);
```

Nginx에서 엣지 처리를 할 때는 헤더를 직접 제거한다.

```nginx
proxy_set_header X-Original-URL "";
proxy_set_header X-Rewrite-URL "";
```

### X-Forwarded-Scheme 인젝션

`X-Forwarded-Proto`나 `X-Forwarded-Scheme`은 프록시가 백엔드에 원래 요청이 http인지 https인지 알려주려고 쓴다. 애플리케이션이 이 헤더로 리다이렉트 응답을 만들 때 오염이 가능하다.

```http
GET /login HTTP/1.1
Host: example.com
X-Forwarded-Scheme: http
```

HTTPS 리다이렉트를 처리하는 코드가 이 헤더를 보고 "http 요청이네, https로 301 리다이렉트해야겠다"고 판단하면, 리다이렉트 응답이 캐시된다. 이후 정상 사용자의 `/login` 요청은 캐시에서 301을 받는다. `X-Forwarded-Scheme: http` + `X-Forwarded-Host: evil.com`을 조합하면 301 Location 헤더에 `http://evil.com/login`을 넣을 수 있다.

## Fat GET 파라미터 공격

Fat GET은 GET 메서드 요청에 HTTP 바디를 같이 보내는 기법이다. RFC 7231에서 GET에 바디를 넣는 걸 금지하지는 않는다. 의미가 없다고 명시했기 때문에 서버마다 처리가 다르다.

CDN 또는 캐시 레이어는 GET 요청의 바디를 무시하고 URL만으로 캐시 키를 만든다. 그런데 일부 백엔드 프레임워크는 GET 바디를 파싱해서 쿼리 파라미터처럼 처리한다. 이 불일치가 공격 지점이 된다.

```bash
# Fat GET — 바디에 파라미터를 넣어 전송
curl -X GET https://api.example.com/search \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'callback=<script>alert(1)</script>'
```

캐시 레이어는 `GET /search`로만 키를 잡는다. 백엔드는 바디에서 `callback` 파라미터를 읽어 응답에 JSONP 콜백으로 반영한다. 오염된 응답이 `/search` 키로 캐시에 저장되면 이후 정상 요청 전부에 XSS 페이로드가 실린다.

Rails나 Django 같은 프레임워크는 GET 바디를 기본적으로 파싱하지 않는다. 그러나 커스텀 미들웨어나 레거시 서블릿 컨테이너, 일부 API 게이트웨이가 이를 처리하는 경우가 있다.

```python
# Django — GET 바디를 수동으로 파싱하는 잘못된 패턴
def search(request):
    if request.method == 'GET':
        # 취약: request.body를 직접 파싱
        import urllib.parse
        body_params = urllib.parse.parse_qs(request.body.decode())
        callback = body_params.get('callback', [''])[0]
        # callback을 응답에 반영하면 Fat GET 포이즈닝 가능
```

또 다른 변형은 `X-HTTP-Method-Override` 헤더다. CDN은 GET으로 처리해서 캐시하는데, 백엔드는 이 헤더를 보고 POST로 처리한다. 캐시 키는 GET 기준이지만 응답 내용은 POST 처리 결과다.

```http
GET /api/update HTTP/1.1
Host: example.com
X-HTTP-Method-Override: POST
Content-Type: application/json

{"admin": true}
```

백엔드가 이 요청을 POST `/api/update`처럼 처리하면, 부작용이 있는 응답이 GET `/api/update` 키로 캐시된다. 방어는 백엔드에서 GET 바디와 메서드 오버라이드 헤더를 무시하고, CDN 단에서 `X-HTTP-Method-Override` 헤더를 제거하는 것이다.

## 캐시가 응답을 저장하는 조건

오염을 시도하기 전에 그 경로가 애초에 캐시되는지부터 봐야 한다. 캐시 안 되는 경로는 포이즈닝 대상이 아니다. 응답 헤더에서 이런 걸 확인한다.

```
Cache-Control: public, max-age=300
Age: 42
X-Cache: HIT
```

- `Cache-Control: public`이고 `max-age`가 0보다 크면 공유 캐시가 저장한다.
- `Age`가 0보다 크면 캐시에서 나온 응답이다.
- `X-Cache`, `CF-Cache-Status`, `X-Served-By` 같은 헤더로 적중 여부를 본다(CDN마다 이름이 다르다).

`Cache-Control: private`, `no-store`, `no-cache`면 공유 캐시는 저장 안 한다. 다만 CDN 설정이 이걸 무시하고 강제로 캐싱하도록 잡혀 있는 경우가 있어서, 헤더만 믿지 말고 실제로 `Age`가 올라가는지 확인하는 게 정확하다.

정적 자원(`/static/...`)이나 `.js`, `.css`, 이미지 확장자는 CDN이 기본적으로 적극 캐싱한다. 동적 HTML 페이지를 캐싱하는 경우가 진짜 위험한데, 마케팅 페이지나 상품 목록처럼 사용자별로 안 바뀌는 페이지를 성능 때문에 캐싱해 두는 곳이 흔하다.

## Vary 헤더

`Vary`는 "이 헤더 값이 다르면 다른 응답으로 취급해서 따로 캐시하라"고 캐시에 알려주는 헤더다. 캐시 키에 헤더를 추가하는 수단이라고 보면 된다.

```
Vary: Accept-Encoding, X-Forwarded-Host
```

이렇게 응답하면 캐시는 `X-Forwarded-Host` 값별로 응답을 따로 저장한다. 공격자가 `evil.com`으로 오염시켜도 그 응답은 `X-Forwarded-Host: evil.com`인 요청에만 제공되고, 헤더 없는 정상 요청에는 안 나간다. unkeyed였던 입력을 keyed로 바꿔서 오염 전파를 막는 셈이다.

다만 `Vary`는 양날이다. unkeyed 입력을 `Vary`에 넣으면 안전해지지만, 너무 많이 넣으면 캐시 적중률이 떨어진다. `Vary: User-Agent`로 잡으면 User-Agent 종류만큼 캐시가 쪼개져서 사실상 캐시가 안 된다. 그래서 근본 해법은 애플리케이션이 신뢰 안 되는 헤더를 응답에 반영하지 않는 것이고, `Vary`는 보조 수단이다.

자주 보는 실수는 `Vary: Cookie`를 빼먹는 것이다. 사용자별로 다른 내용을 쿠키 기반으로 내려주면서 캐시는 쿠키를 키에 안 넣으면, A 사용자의 개인화된 응답이 캐시되어 B 사용자에게 나간다. 이건 공격 없이도 터지는 정보 노출이다.

## 캐시 포이즈닝 vs 캐시 디셉션

둘 다 캐시를 악용하는 공격이지만 방향이 반대다.

| | 캐시 포이즈닝 | 캐시 디셉션 |
|---|---|---|
| 공격 방향 | 공격자 → 캐시 → 피해자 | 피해자 → 캐시 → 공격자 |
| 무엇을 저장하나 | 공격자가 만든 악성 응답 | 피해자의 개인정보 응답 |
| 목적 | XSS, 리다이렉트 등 피해자 공격 | 피해자 데이터 탈취 |
| 전제 조건 | unkeyed 입력이 응답에 반영됨 | 애플리케이션이 존재하지 않는 경로를 정상 처리 |
| 공격 진입점 | 공격자가 직접 오염 요청 전송 | 피해자가 조작된 URL을 열도록 유도 |

캐시 디셉션은 캐시가 경로의 확장자를 보고 "정적 자원이네" 판단해서 캐싱하는 동작을 악용한다. 공격자가 피해자에게 이런 링크를 클릭하게 만든다.

```
https://example.com/my-account/profile.css
```

실제로 `profile.css`라는 파일은 없다. 그런데 애플리케이션 라우팅이 뒤쪽 경로를 무시하고 `/my-account`로 처리해서 피해자의 개인정보 페이지를 응답하는 경우가 있다. 동시에 CDN은 `.css` 확장자를 보고 "정적 파일이니 캐싱"한다. 결과적으로 피해자의 개인정보가 든 응답이 `/my-account/profile.css` 키로 캐시에 저장된다.

피해자가 로그인한 상태로 그 링크를 열면 자기 정보가 캐시에 박힌다. 그다음 공격자가 로그인 없이 같은 URL을 요청하면, 캐시에서 피해자의 개인정보 응답이 그대로 나온다.

방어 포인트는 두 군데다.

- 애플리케이션: 존재하지 않는 하위 경로를 상위 라우트로 흡수해서 200을 내리면 안 된다. 매칭 안 되는 경로는 404를 내야 한다.
- 캐시: 확장자만 보고 캐싱하지 말고, 실제 응답의 `Content-Type`과 `Cache-Control`을 확인한다. origin이 `Cache-Control: private`을 내렸으면 확장자가 `.css`여도 캐싱 안 한다.

## CDN별 방어 설정

### Nginx — 취약한 설정과 안전한 proxy_cache_key

Nginx로 직접 캐싱할 때 제일 많이 보는 취약한 설정이다.

```nginx
# 취약한 설정
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m max_size=1g;

server {
    listen 80;

    location / {
        proxy_cache app_cache;
        # $proxy_host는 upstream 서버 주소다
        # 멀티 도메인 사이트에서 $host가 빠지면 교차 도메인 오염이 난다
        proxy_cache_key "$scheme$proxy_host$request_uri";
        proxy_cache_valid 200 5m;

        # 외부에서 들어온 X-Forwarded-Host를 그대로 백엔드에 넘김
        proxy_pass http://backend;
    }
}
```

두 가지 문제가 있다. 첫째, `proxy_cache_key`에 `$host` 대신 `$proxy_host`를 썼다. `$proxy_host`는 `proxy_pass`에 명시한 upstream 주소라서, 여러 도메인을 같은 backend로 라우팅하면 도메인 구분이 안 된다. 한 도메인의 응답이 다른 도메인 요청에 나갈 수 있다. 둘째, `X-Forwarded-Host`를 백엔드에 그대로 넘기면 백엔드가 그걸 신뢰하는 순간 포이즈닝이 가능하다.

```nginx
# 안전한 설정
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m max_size=1g;

server {
    listen 443 ssl;
    server_name example.com;

    location / {
        proxy_cache app_cache;

        # 실제 요청 호스트($host)를 캐시 키에 포함
        # 멀티 도메인·멀티 테넌트라면 반드시 필요
        proxy_cache_key "$scheme$host$request_uri";

        proxy_cache_valid 200 5m;
        proxy_cache_valid 404 1m;

        # 세션 쿠키가 있으면 캐시 우회
        proxy_cache_bypass $cookie_sessionid $cookie_auth_token;
        proxy_no_cache $cookie_sessionid $cookie_auth_token;

        # 외부 클라이언트가 보낸 위험 헤더를 엣지에서 덮어씀
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;   # 클라이언트 값 덮어씀
        proxy_set_header X-Forwarded-Proto $scheme;

        # 경로 재작성 헤더 제거
        proxy_set_header X-Original-URL "";
        proxy_set_header X-Rewrite-URL "";
        proxy_set_header X-HTTP-Method-Override "";

        # 캐시 상태를 응답 헤더에 노출 (모니터링용)
        add_header X-Cache-Status $upstream_cache_status always;

        proxy_pass http://backend;
    }

    # 인증된 경로는 캐시에서 완전히 제외
    location ~* ^/(api/user|account|admin) {
        proxy_cache off;
        proxy_pass http://backend;
    }
}
```

`proxy_cache_key`에 응답을 가르는 입력이 하나라도 빠지면 오염 경로가 된다. 반대로 너무 많이 넣으면 캐시 적중률이 내려간다. 응답에 영향을 주는 입력이 뭔지를 먼저 정리하고 키를 설계한다.

### CloudFront Managed Headers

CloudFront는 캐시 키에 들어가는 요소를 Cache Policy로 관리한다. AWS가 미리 만들어둔 Managed Cache Policy가 있고, `CachingOptimized`가 기본으로 많이 쓰인다.

```json
{
  "CachePolicyConfig": {
    "DefaultTTL": 86400,
    "HeadersConfig": { "HeaderBehavior": "none" },
    "CookiesConfig": { "CookieBehavior": "none" },
    "QueryStringsConfig": { "QueryStringBehavior": "all" }
  }
}
```

헤더가 캐시 키에 안 들어가는 기본 상태에서 오리진이 `X-Forwarded-Host`를 신뢰하면 포이즈닝이 된다. CloudFront는 기본적으로 `X-Forwarded-For`는 추가하지만 `X-Forwarded-Host`는 그대로 통과시킨다.

방어는 두 레이어로 잡는다. 첫째, CloudFront Functions 또는 Lambda@Edge에서 위험 헤더를 오리진으로 보내기 전 제거한다.

```javascript
// CloudFront Functions — viewer request 이벤트
function handler(event) {
  var request = event.request;

  delete request.headers['x-forwarded-host'];
  delete request.headers['x-original-url'];
  delete request.headers['x-rewrite-url'];
  delete request.headers['x-http-method-override'];

  return request;
}
```

둘째, Origin Request Policy에서 오리진으로 전달할 헤더를 화이트리스트로만 허용한다. `AllViewer` 정책은 모든 헤더를 오리진으로 넘겨서 위험하다. 커스텀 Origin Request Policy를 만들어 필요한 헤더만 명시한다.

캐시 정책 확인은 이렇게 한다.

```bash
aws cloudfront get-distribution-config --id DISTRIBUTION_ID \
  | jq '.DistributionConfig.DefaultCacheBehavior.CachePolicyId'

aws cloudfront get-cache-policy --id CACHE_POLICY_ID \
  | jq '.CachePolicy.CachePolicyConfig'
```

### Cloudflare Cache Rules

Cloudflare는 기본적으로 정적 확장자(`.css`, `.js`, `.png` 등)를 캐시한다. HTML은 기본적으로 캐시하지 않는다. 그런데 성능 때문에 HTML도 캐시하도록 Cache Rules를 추가하면 포이즈닝 위험이 생긴다.

```
# Cache Rule — HTML 캐싱 활성화 (위험 설정 예)
When: URI path ends with "/"
Then: Cache Status = Cache Everything, Edge TTL = 5 minutes
```

이 규칙이 있으면 메인 페이지가 캐시된다. 백엔드가 `X-Forwarded-Host`를 신뢰하면 포이즈닝이 된다.

안전하게 설정하려면 Transform Rules에서 위험 헤더를 오리진으로 보내기 전 제거한다.

```
# HTTP Request Header Modification Rule (Transform Rules)
Remove: X-Forwarded-Host
Remove: X-Original-URL
Remove: X-Rewrite-URL
Set: X-Forwarded-Host = <origin hostname>
```

Cache Key Rules에서 헤더를 캐시 키에 포함할 때는 명시적으로만 추가한다. `X-Forwarded-Host`를 캐시 키에 포함하면 공격자가 임의 값을 넣어 캐시를 무한히 쪼갤 수 있다(캐시 버스팅 공격). 응답 헤더 `CF-Cache-Status`로 캐시 상태를 확인한다.

```
CF-Cache-Status: HIT     — 캐시에서 서빙
CF-Cache-Status: MISS    — 오리진에서 가져옴
CF-Cache-Status: BYPASS  — 캐싱 건너뜀
CF-Cache-Status: EXPIRED — 캐시 만료, 재검증
```

### Varnish VCL

Varnish는 VCL(Varnish Configuration Language)로 캐시 동작을 제어한다. 캐시 키는 `vcl_hash` 서브루틴에서 정의한다.

```vcl
# 취약한 VCL — X-Forwarded-Host가 캐시 키에 안 들어가는데 백엔드로 그대로 전달
sub vcl_recv {
    return (hash);
}

sub vcl_hash {
    hash_data(req.url);
    hash_data(req.http.Host);
    return (lookup);
}
```

`vcl_hash`에 `req.http.Host`만 넣고 `req.http.X-Forwarded-Host`를 캐시 키에 안 넣었는데, `vcl_recv`에서 이 헤더를 백엔드로 그대로 넘기면 문제다. 백엔드가 `X-Forwarded-Host`를 신뢰하면 응답 내용이 달라지는데 캐시 키는 같아서 오염이 된다.

```vcl
# 안전한 VCL
sub vcl_recv {
    # 외부에서 들어온 위험 헤더 제거
    unset req.http.X-Forwarded-Host;
    unset req.http.X-Original-URL;
    unset req.http.X-Rewrite-URL;
    unset req.http.X-HTTP-Method-Override;

    # Varnish가 직접 X-Forwarded-Host를 서버 호스트로 세팅
    set req.http.X-Forwarded-Host = req.http.Host;

    # GET/HEAD 외 메서드, Authorization 헤더, 세션 쿠키가 있으면 캐시 패스
    if (req.method != "GET" && req.method != "HEAD") {
        return (pass);
    }
    if (req.http.Authorization) {
        return (pass);
    }
    if (req.http.Cookie ~ "session|auth|token") {
        return (pass);
    }

    return (hash);
}

sub vcl_hash {
    hash_data(req.url);

    if (req.http.Host) {
        hash_data(req.http.Host);
    } else {
        hash_data(server.ip);
    }

    # Accept-Encoding은 캐시 키에 넣어야 gzip/br 응답이 섞이지 않는다
    if (req.http.Accept-Encoding) {
        if (req.http.Accept-Encoding ~ "br") {
            hash_data("br");
        } elsif (req.http.Accept-Encoding ~ "gzip") {
            hash_data("gzip");
        }
    }

    return (lookup);
}

sub vcl_backend_response {
    # 백엔드가 Cache-Control: private을 내리면 캐싱 안 함
    if (beresp.http.Cache-Control ~ "private|no-store") {
        set beresp.uncacheable = true;
        return (deliver);
    }
}
```

VCL에서 `return (pass)`는 해당 요청을 캐시 없이 직접 백엔드로 보내고, 응답도 캐시에 저장하지 않는다. `return (hash)`는 캐시 키를 계산하고 캐시를 사용하는 경로로 보낸다. `pass`와 `hash` 분기를 명확히 잡는 게 Varnish 캐시 포이즈닝 방어의 핵심이다.

## 탐지와 모니터링

### 수동 탐지

unkeyed 입력 후보부터 하나씩 찔러본다. 캐시되는 경로에 의심 헤더를 넣어 보내고 응답에 반영되는지 확인한다. 반영된다면 캐시 키에 그 헤더가 들어가는지(`Vary`에 있는지, 헤더값 바꿔 보낸 두 요청이 따로 캐시되는지)를 본다.

```bash
# X-Forwarded-Host가 응답에 반영되는지
curl -sv https://target.com/path \
  -H 'X-Forwarded-Host: canary-12345.test' \
  2>&1 | grep -i canary

# 캐시 키에 안 들어가면 헤더 없는 요청에도 canary가 남는다
curl -s https://target.com/path | grep canary-12345
```

테스트할 때 실제 도메인 대신 canary 문자열을 쓰는 건 내 요청이 캐시를 오염시켰는지 확인하기 위해서다. `evil.com`을 직접 쓰면 운영 캐시가 실제로 오염된다.

운영 캐시를 건드리지 않으려면 쿼리스트링에 고유값을 붙여 별도 캐시 키로 격리한다.

```bash
# 고유 쿼리스트링으로 별도 캐시 키 생성 — 다른 사용자에게 영향 없음
NONCE=$(date +%s%N)
curl -s "https://target.com/path?_test=${NONCE}" \
  -H 'X-Forwarded-Host: canary-12345.test' | grep canary

# 같은 키로 재요청 — 캐시에서 나오면 오염 확인
curl -s "https://target.com/path?_test=${NONCE}" | grep canary
```

두 번째 요청에 canary가 남으면 `X-Forwarded-Host`가 unkeyed이고 응답에 반영되는 것이다. 권한이 있는 환경에서 진행하고, 테스트 후 해당 캐시 키를 purge한다.

자동화는 Burp Suite의 Param Miner 확장이 대표적이다. 알려진 unkeyed 헤더·파라미터 목록을 대량으로 넣어 보고 응답 차이를 비교해서 후보를 추려준다. 운영 캐시에서 돌리면 실제 오염이 발생하므로 격리 환경이 있어야 한다.

### 운영 모니터링

운영 중인 서비스에서 캐시 포이즈닝 징후를 찾을 때 보는 것들이다.

**응답 본문 이상**: 같은 캐시 키로 들어온 요청들 사이에서 응답 본문이 갑자기 달라지는 구간을 본다. 정상적인 경우 캐시 HIT 응답은 TTL 내에 내용이 일정하다.

**외부 도메인 참조**: 캐시 HIT로 나가는 HTML 응답에 알려지지 않은 외부 도메인이 포함된 패턴을 탐지한다.

```bash
# 특정 경로의 캐시 응답에서 외부 도메인 참조 확인
curl -s https://example.com/products \
  | grep -oP 'https?://[^/"]+' \
  | grep -v 'example.com\|trusted-cdn.com'
```

**CDN 로그 패턴**: CDN 로그에 캐시 상태(HIT/MISS)와 응답 크기를 같이 남겨두면, 평소와 다른 응답 크기가 HIT로 반복해서 나가는 구간을 이상 징후로 잡을 수 있다. CloudFront라면 `x-edge-result-type`, Cloudflare라면 `CF-Cache-Status` 필드를 활용한다.

**응답 해시 비교**: APM이나 synthetic monitoring으로 주기적으로 캐시 경로를 호출하고 응답 본문의 해시를 비교한다. 해시가 바뀌었을 때 알림을 보내면 조기 탐지가 된다.

이상이 탐지되면 즉시 해당 경로의 캐시를 purge하고, CDN 로그에서 오염된 캐시 키가 언제부터 나갔는지 역추적한다.

```bash
# CloudFront 특정 경로 캐시 무효화
aws cloudfront create-invalidation \
  --distribution-id DIST_ID \
  --paths "/products" "/products/*"

# Varnish 캐시 purge (PURGE 메서드 활성화된 경우)
curl -X PURGE https://cache.internal/products

# Nginx proxy_cache_purge 모듈 사용 시
curl -X PURGE https://nginx.internal/products
```

## 정리

- 캐시 포이즈닝은 응답에 영향을 주지만 캐시 키엔 안 들어가는 입력(unkeyed)을 악용해, 오염된 응답을 캐시에 저장시켜 다수 사용자에게 먹이는 공격이다.
- `X-Forwarded-Host`류 헤더로 절대 URL이나 리소스 경로를 만들면 제일 잘 터진다. 신뢰 안 되는 헤더를 응답에 반영하지 않는 게 근본 해법이다.
- `X-Original-URL` / `X-Rewrite-URL`은 Symfony·Laravel 계열 프레임워크에서 경로 자체를 바꿀 수 있다. 엣지에서 빈 값으로 덮어쓰거나 제거하고, 프레임워크의 신뢰 프록시 설정을 반드시 명시한다.
- Fat GET은 CDN과 백엔드의 GET 바디 처리 불일치를 이용한다. 백엔드에서 GET 바디를 파싱하지 않도록 하고, `X-HTTP-Method-Override` 헤더를 엣지에서 제거한다.
- `proxy_cache_key`에 응답을 가르는 입력을 빠짐없이 넣는다. 멀티 도메인 구조에서 `$host` 대신 `$proxy_host`를 쓰면 교차 도메인 오염이 난다.
- CloudFront는 Functions로 위험 헤더를 제거하고, Origin Request Policy를 화이트리스트로 관리한다. Cloudflare는 Transform Rules로 헤더를 제거하고 Cache Key Rules를 명시적으로 설정한다. Varnish는 `vcl_recv`에서 위험 헤더를 unset하고, `pass`/`hash` 분기를 명확히 잡는다.
- 캐시 디셉션은 존재하지 않는 경로를 404로 처리하고, 캐시가 확장자가 아니라 origin의 `Cache-Control`을 존중하게 설정하면 막힌다.
- 탐지 테스트는 고유 canary 문자열과 격리된 쿼리스트링으로 운영 캐시를 오염시키지 않고 진행하고, 테스트 후 해당 캐시 키를 purge한다.
