---
title: 웹 캐시 포이즈닝 (Web Cache Poisoning)
tags: [security, web-cache-poisoning, cache, cdn, nginx, reverse-proxy, http-headers]
updated: 2026-06-15
---

# 웹 캐시 포이즈닝 (Web Cache Poisoning)

CDN이나 리버스 프록시를 앞에 두면 같은 응답을 캐시에 저장해 두고 여러 사용자에게 재사용한다. 이때 캐시는 "이 요청과 저 요청이 같은 요청인가"를 판단하는 기준이 필요한데, 그게 캐시 키다. 보통 메서드 + 호스트 + 경로 + 쿼리스트링으로 키를 만든다. 문제는 응답 내용에 영향을 주는데 캐시 키에는 안 들어가는 입력값이 있을 때 생긴다. 이런 값을 unkeyed input이라고 부른다.

공격자가 unkeyed 입력으로 응답을 오염시키고, 그 오염된 응답이 캐시에 저장되면, 이후 같은 키로 들어오는 정상 사용자 전부가 오염된 응답을 받는다. 한 번의 요청으로 다수 사용자를 공격하는 게 캐시 포이즈닝의 핵심이다. XSS 페이로드를 캐시에 박아두면 그 페이지를 여는 사람 전부가 스크립트를 실행당한다.

저장형 XSS와 비슷해 보이지만 저장 위치가 DB가 아니라 캐시라는 점이 다르다. 그래서 캐시가 만료되거나 비워지면 사라지고, 캐시 키 조건이 맞는 동안만 유효하다. 대신 서버 코드를 안 건드려도 되고, 캐시 한 군데만 오염시키면 그 뒤로 들어오는 트래픽을 통째로 잡는다.

## 캐시 키와 unkeyed 입력

먼저 캐시 키에 뭐가 들어가는지 봐야 한다. 일반적인 CDN 기본 캐시 키는 이렇다.

```
GET /products HTTP/1.1
Host: shop.example.com
```

여기서 키는 `GET + shop.example.com + /products` 정도다. 쿠키나 대부분의 요청 헤더는 키에 안 들어간다. 그런데 애플리케이션이 이런 헤더를 읽어서 응답에 반영하면 문제가 된다.

```
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

## 가장 흔한 시나리오: X-Forwarded-Host

애플리케이션이 절대 URL을 만들 때 요청 호스트를 쓰는 코드가 제일 많이 당한다. 예를 들어 비밀번호 재설정 메일 링크, canonical 링크, OG 태그, 리소스 절대 경로 같은 데서 호스트를 가져온다.

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

## CDN/리버스 프록시 캐시 키 설정

방어의 핵심은 캐시 키를 명확히 정의하고, 신뢰 안 되는 헤더를 애플리케이션에 그대로 넘기지 않는 것이다.

### 엣지에서 위험 헤더 제거

리버스 프록시 단에서 외부가 보낸 `X-Forwarded-*` 계열을 지우거나 덮어쓴다. 외부 클라이언트가 이 헤더를 직접 세팅해서 보내는 건 정상 상황이 아니다.

```nginx
# 외부에서 들어온 X-Forwarded-Host를 무시하고 프록시가 직접 세팅
location / {
    proxy_set_header X-Forwarded-Host $host;       # 클라이언트 값 덮어씀
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;
    proxy_pass http://backend;
}
```

`proxy_set_header`로 덮어쓰면 외부가 보낸 값은 백엔드에 도달하지 못한다. 아예 빈 값으로 지우려면 이렇게 한다.

```nginx
proxy_set_header X-Forwarded-Host "";
proxy_set_header X-Original-URL "";
proxy_set_header X-Rewrite-URL "";
```

여러 프록시를 거치는 구조라면 맨 앞 엣지에서 한 번 정리하고, 안쪽에서는 그 값을 신뢰하는 식으로 신뢰 경계를 명확히 잡는다.

### Nginx proxy_cache_key

Nginx로 직접 캐싱한다면 `proxy_cache_key`로 키 구성을 명시한다. 기본값은 보통 이렇다.

```nginx
proxy_cache_key "$scheme$proxy_host$request_uri";
```

여기엔 헤더가 안 들어가서, 호스트 헤더로 응답이 갈리는 사이트라면 `$host`를 넣어야 한다.

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m max_size=1g;

server {
    location / {
        proxy_cache app_cache;
        # 호스트와 경로를 키에 포함
        proxy_cache_key "$scheme$host$request_uri";
        proxy_cache_valid 200 5m;

        # 응답에 캐시 상태 노출 (디버깅·탐지용)
        add_header X-Cache-Status $upstream_cache_status;

        proxy_pass http://backend;
    }
}
```

키에 들어가야 하는데 빠진 입력이 없는지, 응답에 영향을 주는데 키에 없는 헤더가 없는지를 한 줄씩 따져봐야 한다. 멀티테넌트(호스트별 다른 사이트)인데 `$host`를 키에서 빼면, 한 테넌트 응답이 다른 테넌트에게 캐시되어 나가는 사고가 난다.

### 쿠키·인증된 응답은 캐싱 제외

로그인 사용자에게 내려가는 개인화 응답은 공유 캐시에 절대 들어가면 안 된다. 쿠키가 있으면 캐싱을 끄거나, 인증 응답은 `Cache-Control: private`을 확실히 붙인다.

```nginx
# 세션 쿠키가 있으면 캐시 우회
proxy_cache_bypass $cookie_sessionid;
proxy_no_cache $cookie_sessionid;
```

CDN 쪽에서도 쿠키가 붙은 요청은 origin으로 패스스루하도록 잡는 게 안전하다. CloudFront라면 캐시 정책에서 캐시 키에 포함할 헤더·쿠키·쿼리스트링을 화이트리스트로 명시하고, 나머지는 키에서 빼되 오리진으로는 전달 여부를 따로 정한다.

## 캐시 디셉션 공격 (Web Cache Deception)

포이즈닝과 방향이 반대인 공격이 캐시 디셉션이다. 포이즈닝은 "공격자가 캐시를 오염시켜 피해자에게 먹인다"인데, 디셉션은 "피해자의 개인 정보가 든 응답을 캐시에 저장시켜 공격자가 꺼내 본다"이다.

원리는 캐시가 경로의 확장자나 특정 패턴을 보고 "정적 자원이네" 판단해서 캐싱하는 동작을 악용한다. 공격자가 피해자에게 이런 링크를 클릭하게 만든다.

```
https://example.com/my-account/profile.css
```

실제로 `profile.css`라는 파일은 없다. 그런데 애플리케이션 라우팅이 뒤쪽 경로를 무시하고 `/my-account`로 처리해서 피해자의 개인정보 페이지를 응답하는 경우가 있다. 동시에 CDN은 `.css` 확장자를 보고 "정적 파일이니 캐싱"한다. 결과적으로 피해자의 개인정보가 든 응답이 `/my-account/profile.css` 키로 캐시에 저장된다.

피해자가 로그인한 상태로 그 링크를 열면 자기 정보가 캐시에 박힌다. 그다음 공격자가 로그인 없이 같은 URL을 요청하면, 캐시에서 피해자의 개인정보 응답이 그대로 나온다.

```bash
# 피해자가 로그인 상태로 이 URL을 열게 유도 → 응답이 캐시됨
https://example.com/my-account/profile.css

# 공격자가 인증 없이 같은 URL 요청 → 피해자 정보가 캐시에서 나옴
curl https://example.com/my-account/profile.css
```

방어 포인트는 두 군데다.

- 애플리케이션: `/my-account/profile.css`처럼 존재하지 않는 하위 경로를 상위 라우트로 흡수해서 200을 내리면 안 된다. 매칭 안 되는 경로는 404를 내야 한다.
- 캐시: 확장자만 보고 캐싱하지 말고, 실제 응답의 `Content-Type`과 `Cache-Control`을 확인한다. origin이 `Cache-Control: private`을 내렸으면 확장자가 `.css`여도 캐싱 안 한다.

확장자 기반 캐싱 규칙(`\.(css|js|png|jpg)$`은 무조건 캐시)을 쓰는 CDN 설정이 흔한데, 이게 디셉션의 발판이 된다. origin 응답의 캐시 지시를 존중하도록 바꾸는 게 맞다.

## 탐지

운영 중인 서비스에서 캐시 포이즈닝 흔적을 찾으려면 몇 가지를 본다.

unkeyed 입력 후보부터 하나씩 찔러본다. 캐시되는 경로에 의심 헤더를 넣어 보내고 응답에 반영되는지 확인한다. 반영되면 캐시 키에 그 헤더가 들어가는지(`Vary`에 있는지, 헤더값 바꿔 보낸 두 요청이 따로 캐시되는지)를 본다.

```bash
# X-Forwarded-Host가 응답에 반영되는지
curl -s https://target/path -H 'X-Forwarded-Host: canary12345.com' | grep canary12345

# 캐시 키에 안 들어가면 헤더 없는 요청에도 canary가 남는다
curl -s https://target/path | grep canary12345
```

테스트할 땐 실제 도메인 대신 절대 안 겹치는 고유 문자열(canary)을 써서, 정말 내 요청이 캐시를 오염시켰는지 다른 요청과 구분한다. 운영 캐시에 실제로 오염을 남기면 다른 사용자에게 영향이 가므로, 권한이 있는 환경에서 짧은 TTL 경로나 별도 캐시 키(쿼리스트링에 고유값을 붙여 격리)로 테스트하고 끝나면 캐시를 비운다.

자동화는 Param Miner(Burp 확장)가 대표적이다. 알려진 unkeyed 헤더·파라미터 목록을 대량으로 넣어 보고 응답 차이를 비교해서 후보를 추려준다. 다만 운영 캐시를 건드리니 권한 없이 돌리면 안 된다.

로그 쪽에서는 같은 캐시 키로 들어온 요청들 사이에서 응답 본문이 갑자기 달라지는 구간, 특정 경로에서 외부 도메인이 박힌 응답이 캐시 HIT로 반복해서 나가는 패턴을 본다. CDN 로그에 캐시 상태(HIT/MISS)와 응답 크기를 같이 남겨두면 이상 구간을 찾기 쉽다.

## 정리

- 캐시 포이즈닝은 응답에 영향을 주지만 캐시 키엔 안 들어가는 입력(unkeyed)을 악용해, 오염된 응답을 캐시에 저장시켜 다수 사용자에게 먹이는 공격이다.
- `X-Forwarded-Host`류 헤더로 절대 URL이나 리소스 경로를 만들면 제일 잘 터진다. 신뢰 안 되는 헤더를 응답에 반영하지 않는 게 근본 해법이다.
- 엣지 프록시에서 외부가 보낸 `X-Forwarded-*`를 `proxy_set_header`로 덮어쓰거나 지워서 백엔드에 안 넘긴다.
- `proxy_cache_key`에 응답을 가르는 입력(특히 `$host`)을 빠짐없이 넣고, 쿠키·인증 응답은 공유 캐시에서 제외한다.
- `Vary`로 unkeyed 입력을 keyed로 바꿀 수 있지만 적중률과 트레이드오프다. 보조 수단으로 쓴다.
- 캐시 디셉션은 확장자 기반 캐싱을 악용해 피해자 개인정보를 캐시에 저장시키는 반대 방향 공격이다. 매칭 안 되는 경로는 404를 내고, 캐시는 확장자가 아니라 origin의 `Cache-Control`을 존중하게 한다.
- 탐지는 고유 canary 문자열을 unkeyed 후보 헤더에 넣어 응답 반영·캐시 전파를 확인하고, 운영 캐시를 오염시키지 않도록 격리된 환경에서 한다.
