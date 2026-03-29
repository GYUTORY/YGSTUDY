---
title: HTTP 캐싱
tags:
  - HTTP
  - Cache
  - Network
  - CDN
  - Performance
updated: 2026-03-29
---

# HTTP 캐싱

HTTP 캐싱은 동일한 리소스에 대한 반복 요청을 줄이는 메커니즘이다. 서버가 응답에 캐시 관련 헤더를 포함하면, 클라이언트나 중간 프록시가 해당 응답을 저장하고 재사용한다.

캐싱이 없으면 매번 서버까지 요청이 도달하고, 같은 데이터를 반복해서 전송한다. 대역폭 낭비이고 응답 시간도 늘어난다.

---

## Cache-Control 디렉티브

`Cache-Control` 헤더는 캐싱 동작을 제어하는 핵심 헤더다. 여러 디렉티브를 조합해서 사용한다.

### 주요 디렉티브

| 디렉티브 | 의미 |
|---------|------|
| `max-age=N` | 응답을 N초 동안 캐시로 사용한다 |
| `s-maxage=N` | 공유 캐시(프록시, CDN)에만 적용되는 max-age |
| `no-cache` | 캐시에 저장은 하지만, 사용 전 반드시 서버에 재검증한다 |
| `no-store` | 어디에도 캐시하지 않는다. 응답을 저장 자체를 금지한다 |
| `must-revalidate` | max-age가 만료되면 반드시 서버에 재검증한다. 만료된 캐시를 그냥 쓰는 것을 금지한다 |
| `private` | 브라우저 캐시에만 저장한다. 공유 캐시(프록시, CDN)는 저장 불가 |
| `public` | 공유 캐시에도 저장 가능하다 |
| `immutable` | 리소스가 변경되지 않으므로, 만료 전에는 재검증 요청도 보내지 않는다 |

### no-cache vs no-store vs must-revalidate

이 세 가지를 혼동하는 경우가 많다.

**no-cache**: 캐시에 저장한다. 하지만 매번 서버에 "이거 아직 유효한가요?"라고 물어본다. 서버가 304를 주면 캐시된 데이터를 쓰고, 200을 주면 새 데이터로 교체한다. 이름이 "no-cache"라서 캐시를 안 하는 것처럼 보이지만, 실제로는 "항상 재검증"이라는 뜻이다.

```
Cache-Control: no-cache
```

**no-store**: 진짜로 캐시를 안 한다. 브라우저도, 프록시도, CDN도 응답을 저장하지 않는다. 민감한 정보(개인정보, 결제 정보)에 사용한다.

```
Cache-Control: no-store
```

**must-revalidate**: `max-age`와 함께 사용한다. max-age 기간 동안은 서버에 물어보지 않고 캐시를 쓴다. 만료되면 반드시 서버에 재검증한다. 네트워크가 끊겨서 재검증이 불가능하면 504를 반환한다. must-revalidate가 없으면 브라우저가 만료된 캐시를 임의로 사용하는 경우가 있다.

```
Cache-Control: max-age=3600, must-revalidate
```

실무에서 흔한 실수: "캐시 안 되게 하고 싶다"고 `no-cache`만 설정하는 경우다. `no-cache`는 캐시를 저장하되 매번 검증하는 것이라 의도와 다르다. 캐시 자체를 막으려면 `no-store`를 써야 한다. 보수적으로 가려면 `no-store, no-cache, must-revalidate`를 같이 쓴다.

---

## 조건부 요청

캐시가 만료되었거나 `no-cache`가 설정되어 있으면, 클라이언트는 서버에 재검증 요청을 보낸다. 이때 전체 리소스를 다시 받는 대신, "변경되었는지만" 확인하는 것이 조건부 요청이다.

### ETag / If-None-Match

ETag는 리소스의 특정 버전을 식별하는 값이다. 해시값이나 버전 번호를 쓴다.

**흐름:**

1. 클라이언트가 처음 리소스를 요청한다
2. 서버가 `ETag: "abc123"` 헤더를 포함해서 응답한다
3. 클라이언트가 캐시에 저장한다
4. 다음 요청 시 `If-None-Match: "abc123"` 헤더를 보낸다
5. 서버가 현재 ETag와 비교한다
6. 같으면 `304 Not Modified` (본문 없음), 다르면 `200 OK`와 새 데이터

```
# 첫 번째 요청
GET /api/users/1 HTTP/1.1

# 서버 응답
HTTP/1.1 200 OK
ETag: "a1b2c3d4"
Cache-Control: no-cache
Content-Type: application/json

{"id": 1, "name": "홍길동"}

# 두 번째 요청 (재검증)
GET /api/users/1 HTTP/1.1
If-None-Match: "a1b2c3d4"

# 변경 없으면
HTTP/1.1 304 Not Modified
ETag: "a1b2c3d4"
```

304 응답은 본문이 없으므로 네트워크 전송량이 크게 줄어든다. 이미지나 큰 JSON 응답에서 차이가 크다.

ETag에는 Strong ETag와 Weak ETag가 있다.

- Strong ETag(`"abc123"`): 바이트 단위로 동일할 때만 매칭
- Weak ETag(`W/"abc123"`): 의미적으로 동일하면 매칭. 공백이나 포맷 차이는 무시

### Last-Modified / If-Modified-Since

시간 기반 검증이다. ETag보다 정밀도가 낮다(초 단위).

```
# 서버 응답
HTTP/1.1 200 OK
Last-Modified: Sat, 29 Mar 2026 10:00:00 GMT

# 재검증 요청
GET /style.css HTTP/1.1
If-Modified-Since: Sat, 29 Mar 2026 10:00:00 GMT

# 변경 없으면
HTTP/1.1 304 Not Modified
```

**ETag vs Last-Modified 비교:**

| 항목 | ETag | Last-Modified |
|------|------|---------------|
| 정밀도 | 콘텐츠 기반 (정확함) | 초 단위 시간 (1초 내 변경 감지 불가) |
| 부하 | 해시 계산 필요 | 파일 시스템 타임스탬프 사용 |
| 적합한 경우 | API 응답, 동적 콘텐츠 | 정적 파일 |

둘 다 있으면 `ETag`가 우선한다. 서버에서 두 가지를 모두 보내고, 클라이언트도 `If-None-Match`와 `If-Modified-Since`를 함께 보내는 것이 일반적이다.

---

## Vary 헤더

같은 URL이라도 요청 헤더에 따라 다른 응답을 줄 수 있다. `Vary` 헤더는 캐시에게 "이 헤더가 다르면 별도의 캐시 항목으로 저장해라"고 알려준다.

```
Vary: Accept-Encoding
```

이 경우 `Accept-Encoding: gzip`과 `Accept-Encoding: br`에 대해 각각 다른 캐시 항목을 유지한다. gzip 요청에 br 캐시를 돌려주면 클라이언트가 디코딩에 실패한다.

```
Vary: Accept-Language, Accept-Encoding
```

여러 헤더를 지정하면 조합별로 캐시 항목이 생긴다. 조합이 많아지면 캐시 히트율이 급격히 떨어지므로, 필요한 헤더만 지정한다.

주의할 점: `Vary: *`로 설정하면 사실상 캐시가 불가능하다. 모든 요청이 고유한 것으로 취급된다.

CDN에서 `Vary` 관련 문제가 잘 발생한다. CDN이 `Vary`를 지원하지 않거나 무시하는 경우, `Accept-Encoding`에 따른 분기가 안 돼서 깨진 응답이 나갈 수 있다. CloudFront는 `Vary`를 지원하지만, 화이트리스트에 등록한 헤더만 캐시 키에 포함한다.

---

## 캐시 계층: 브라우저 → 프록시 → CDN

HTTP 캐싱은 여러 계층에서 동작한다. 요청이 서버에 도달하기 전에 어떤 계층에서든 캐시 히트가 발생하면 거기서 응답이 돌아온다.

### 브라우저 캐시 (Private Cache)

사용자의 브라우저에 저장되는 캐시다. `Cache-Control: private` 또는 별도 지정 없이 `max-age`만 설정하면 브라우저에 캐시된다.

- 해당 사용자만 사용한다
- 개인화된 응답(로그인 후 마이페이지 등)을 캐싱하기에 적합하다
- 브라우저 탭을 닫으면 메모리 캐시는 사라지고, 디스크 캐시는 남는다
- Chrome DevTools > Network 탭에서 `(disk cache)`, `(memory cache)`로 확인 가능

### 프록시 캐시 (Shared Cache)

회사 내부 프록시나 ISP 프록시에서 동작하는 캐시다. 여러 사용자가 공유한다. 요즘은 HTTPS가 기본이라 ISP 프록시 캐시의 의미가 줄었지만, 리버스 프록시(Nginx, Varnish) 형태로 여전히 많이 쓴다.

```nginx
# Nginx 리버스 프록시 캐시 설정
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g;

server {
    location /api/ {
        proxy_cache my_cache;
        proxy_cache_valid 200 10m;
        proxy_cache_valid 404 1m;
        proxy_pass http://backend;
        add_header X-Cache-Status $upstream_cache_status;
    }
}
```

`X-Cache-Status` 헤더로 `HIT`, `MISS`, `EXPIRED`, `BYPASS` 상태를 확인할 수 있다. 디버깅할 때 유용하다.

### CDN 캐시

CloudFront, Cloudflare, Fastly 같은 CDN은 전 세계 엣지 서버에 캐시를 분산 저장한다.

- `s-maxage`가 있으면 CDN은 `max-age` 대신 `s-maxage`를 따른다
- CDN은 `private` 응답을 캐싱하지 않는다
- 캐시 무효화(Invalidation) API를 제공한다. 하지만 전파에 시간이 걸린다

```
Cache-Control: public, max-age=60, s-maxage=600
```

이 설정이면 브라우저는 60초간 캐시하고, CDN은 600초간 캐시한다. 브라우저 캐시가 만료되어도 CDN에서 응답하므로 오리진 서버까지 요청이 가지 않는다.

### 계층별 Cache-Control 동작 요약

| 디렉티브 | 브라우저 | 프록시/CDN |
|---------|---------|-----------|
| `private` | 캐시 가능 | 캐시 불가 |
| `public` | 캐시 가능 | 캐시 가능 |
| `max-age` | 적용 | `s-maxage` 없으면 적용 |
| `s-maxage` | 무시 | 적용 (`max-age` 대신) |
| `no-store` | 저장 안 함 | 저장 안 함 |

---

## stale-while-revalidate

캐시가 만료된 직후, 재검증하는 동안 오래된(stale) 캐시를 일단 제공하는 패턴이다.

```
Cache-Control: max-age=300, stale-while-revalidate=60
```

이 설정의 동작:

- 0~300초: 캐시를 그대로 사용한다 (fresh)
- 300~360초: 오래된 캐시를 일단 응답으로 준다. 동시에 백그라운드에서 서버에 새 데이터를 요청한다 (stale-while-revalidate 구간)
- 360초 이후: 캐시를 사용하지 않고 서버에 직접 요청한다

사용자 입장에서는 캐시 만료 직후에도 즉시 응답을 받으므로 체감 속도가 빠르다. 대신 stale-while-revalidate 구간에서는 약간 오래된 데이터를 볼 수 있다. 실시간성이 중요하지 않은 리소스(뉴스 피드, 상품 목록 등)에 적합하다.

비슷한 디렉티브로 `stale-if-error`가 있다:

```
Cache-Control: max-age=300, stale-if-error=86400
```

서버가 에러(5xx)를 반환하거나 네트워크 장애가 발생하면, 24시간(86400초)까지 오래된 캐시를 사용한다. 서버 장애 시 완전한 에러 페이지 대신 이전 데이터라도 보여줄 수 있다.

---

## 캐시 무효화 (Cache Busting)

캐시의 가장 큰 문제는 "코드를 배포했는데 사용자에게 이전 버전이 보이는 것"이다. 캐시 무효화는 이 문제를 해결하는 방법이다.

### 파일명에 해시 포함

가장 확실한 방법이다. 빌드 시 파일 내용의 해시를 파일명에 포함한다.

```
# 빌드 결과
app.a1b2c3d4.js
style.e5f6g7h8.css
```

Webpack, Vite 같은 번들러가 자동으로 해준다.

```javascript
// webpack.config.js
module.exports = {
  output: {
    filename: '[name].[contenthash].js',
  },
};
```

이렇게 하면 파일 내용이 바뀔 때 파일명도 바뀌므로, 캐시된 이전 파일과 충돌하지 않는다. 이 파일들에는 긴 max-age를 설정해도 안전하다.

```
Cache-Control: public, max-age=31536000, immutable
```

1년(31536000초)동안 캐시하고, `immutable`로 재검증 요청도 보내지 않게 한다. 파일 내용이 바뀌면 해시가 바뀌어 새 URL이 되므로 문제없다.

### 쿼리 스트링 방식

```html
<script src="/app.js?v=1.2.3"></script>
<link rel="stylesheet" href="/style.css?v=abc123">
```

파일명은 그대로 두고 쿼리 스트링으로 버전을 구분한다. 간단하지만 문제가 있다:

- 일부 CDN과 프록시가 쿼리 스트링이 있는 URL을 캐시하지 않는다
- 같은 파일을 두 번 다운로드하게 될 수 있다

해시 파일명 방식이 더 안정적이므로, 가능하면 해시 파일명을 쓴다.

### HTML 파일의 캐시

JavaScript, CSS는 해시 파일명으로 장기 캐싱이 가능하지만, HTML 파일(`index.html`)은 URL이 고정되어 있어 해시 파일명을 쓸 수 없다. HTML에서 새 해시 파일명의 JS/CSS를 참조하려면, HTML 자체가 최신이어야 한다.

```
# index.html에 대한 캐시 설정
Cache-Control: no-cache
```

HTML은 `no-cache`로 설정해서 매번 재검증하게 한다. 304 응답이 오면 네트워크 비용은 작다. HTML 파일 크기 자체도 JS/CSS에 비해 작으므로, 매번 받아도 큰 부담이 아니다.

### API 응답 캐시 무효화

API 응답은 같은 URL에서 데이터가 바뀌므로, 파일 해시 방식을 쓸 수 없다.

- `ETag`로 조건부 요청을 사용한다
- 데이터가 자주 바뀌면 `max-age`를 짧게 잡는다 (10초~60초)
- 데이터가 거의 안 바뀌면 `stale-while-revalidate`를 활용한다
- 데이터 변경 시 CDN Invalidation API를 호출한다 (CloudFront `CreateInvalidation`, Cloudflare `Purge`)

---

## 실무 캐시 설정 예제

### Spring Boot

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 정적 리소스: 해시 파일명 사용, 1년 캐시
        registry.addResourceHandler("/static/**")
                .addResourceLocations("classpath:/static/")
                .setCacheControl(CacheControl.maxAge(365, TimeUnit.DAYS)
                        .cachePublic());
    }
}
```

```java
@RestController
@RequestMapping("/api")
public class UserController {

    @GetMapping("/users/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        User user = userService.findById(id);
        String etag = Integer.toHexString(user.hashCode());

        return ResponseEntity.ok()
                .eTag(etag)
                .cacheControl(CacheControl.maxAge(0).mustRevalidate())
                .body(user);
    }
}
```

Spring에서 `ShallowEtagHeaderFilter`를 등록하면 응답 본문의 MD5 해시로 ETag를 자동 생성한다. 단, 응답을 버퍼링해야 해서 스트리밍 응답에는 적합하지 않다.

```java
@Bean
public FilterRegistrationBean<ShallowEtagHeaderFilter> etagFilter() {
    FilterRegistrationBean<ShallowEtagHeaderFilter> registration
            = new FilterRegistrationBean<>(new ShallowEtagHeaderFilter());
    registration.addUrlPatterns("/api/*");
    return registration;
}
```

주의: `ShallowEtagHeaderFilter`는 304를 반환해서 네트워크 전송량은 줄이지만, 서버에서 응답 본문을 매번 생성하는 것은 동일하다. DB 조회 비용을 줄이려면 직접 ETag를 관리해야 한다.

### Express.js

```javascript
const express = require('express');
const app = express();

// 정적 파일: 1년 캐시 (해시 파일명 사용 전제)
app.use('/static', express.static('public', {
  maxAge: '365d',
  immutable: true,
}));

// API 응답에 ETag와 Cache-Control 설정
app.get('/api/products/:id', async (req, res) => {
  const product = await db.findProduct(req.params.id);

  const etag = `"${product.updatedAt.getTime()}"`;

  if (req.headers['if-none-match'] === etag) {
    return res.status(304).end();
  }

  res.set({
    'ETag': etag,
    'Cache-Control': 'private, max-age=0, must-revalidate',
  });
  res.json(product);
});
```

Express는 기본적으로 `ETag`를 자동 생성한다(`etag` 옵션). 하지만 동적 API에서는 위 예제처럼 직접 관리하는 것이 더 정확하다.

### 자주 사용하는 Cache-Control 패턴

```
# 정적 리소스 (해시 파일명)
Cache-Control: public, max-age=31536000, immutable

# HTML 파일
Cache-Control: no-cache

# 개인화된 API 응답 (마이페이지 등)
Cache-Control: private, no-cache

# 민감한 데이터 (결제, 개인정보)
Cache-Control: no-store

# 자주 안 바뀌는 공개 API
Cache-Control: public, max-age=60, s-maxage=300, stale-while-revalidate=30

# 이미지, 폰트
Cache-Control: public, max-age=604800
```

---

## 디버깅

캐시 문제가 발생했을 때 확인하는 방법:

**Chrome DevTools**: Network 탭에서 각 요청의 `Size` 컬럼을 확인한다. `(disk cache)`, `(memory cache)`로 표시되면 캐시에서 로드된 것이다. 요청을 클릭하면 Response Headers에서 `Cache-Control`, `ETag`, `Age` 헤더를 확인할 수 있다.

**curl로 헤더 확인**:

```bash
curl -I https://example.com/api/data

# 조건부 요청 테스트
curl -H "If-None-Match: \"abc123\"" -I https://example.com/api/data
```

**CDN 캐시 상태 확인**: 대부분의 CDN이 `X-Cache`, `X-Cache-Hit`, `cf-cache-status` 같은 헤더를 응답에 포함한다.

```bash
# CloudFront
curl -I https://cdn.example.com/image.png
# X-Cache: Hit from cloudfront

# Cloudflare
curl -I https://example.com/style.css
# cf-cache-status: HIT
```

**Age 헤더**: CDN이 캐시한 시점부터 경과한 시간(초)을 나타낸다. `Age: 120`이면 2분 전에 캐시된 응답이다. `max-age`에서 `Age`를 빼면 남은 유효 시간을 알 수 있다.
