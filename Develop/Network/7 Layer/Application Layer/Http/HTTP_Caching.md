---
title: HTTP 캐싱
tags:
  - HTTP
  - Cache
  - Network
  - CDN
  - Performance
updated: 2026-04-29
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

### Heuristic Caching

응답에 `Cache-Control`이나 `Expires` 헤더가 아예 없고 `Last-Modified`만 있다면, 브라우저는 자체적으로 TTL을 추정해서 캐시한다. 명시적 캐시 정책이 없는데도 브라우저가 멋대로 캐시하는 것이라, 의도치 않은 캐시 동작의 단골 원인이다.

RFC 7234 §4.2.2에서 LM-Factor라는 권장 휴리스틱을 정의한다. 보통 다음 식으로 계산한다.

```
heuristic_lifetime = (Date - Last-Modified) * 0.1
```

`Last-Modified`가 10일 전이면 약 1일 동안 캐시한다. 10% 비율은 권장값일 뿐이라 브라우저별로 구현이 약간씩 다르다. 크롬은 보통 10%를 쓰면서 상한을 두지만, 일부 구현은 더 길게 잡기도 한다.

실무에서 한 번씩 겪는 사고: 정적 파일을 서빙하는 Nginx 기본 설정에서 `Last-Modified`만 자동으로 붙고 `Cache-Control`은 빠진다. "캐시 헤더 안 줬으니 캐시 안 되겠지" 하고 배포했더니, 사용자 브라우저가 며칠 동안 이전 JS 파일을 보여주는 사건이 발생한다. 캐시 동작을 명시적으로 통제하고 싶으면 `Cache-Control`을 반드시 같이 보낸다. 캐싱을 차단하려면 `Cache-Control: no-store` 또는 `no-cache`를 명시한다.

`Last-Modified`까지 빼버려도 브라우저가 휴리스틱을 적용하지 않으므로 안전하긴 하다. 다만 조건부 요청을 활용할 수 없게 되므로, `Last-Modified`나 `ETag`를 두면서 `Cache-Control`도 같이 보내는 쪽이 낫다.

---

## 레거시 헤더: Expires, Pragma

`Cache-Control`이 표준화되기 전에는 `Expires`와 `Pragma` 헤더로 캐시를 제어했다. HTTP/1.0 시절 헤더라 지금은 거의 의미가 없지만, 호환성 때문에 일부 환경에서는 여전히 보낸다.

### Expires

응답이 만료되는 절대 시각을 GMT 형식으로 지정한다.

```
Expires: Thu, 01 Dec 2026 16:00:00 GMT
```

`Cache-Control: max-age`와 동시에 있으면 RFC 7234에 따라 `max-age`가 우선한다. 서버와 클라이언트의 시계가 어긋나면 의도와 다르게 동작하므로, 상대 시간 기반인 `max-age` 쪽이 더 안정적이다. `Expires: 0`이나 과거 시각을 넣으면 즉시 만료를 의미한다. 지금 새로 만드는 응답에 굳이 `Expires`를 추가할 이유는 없다.

### Pragma: no-cache

HTTP/1.0의 캐시 무효화 헤더다. 표준상 의미가 정의된 것은 요청 헤더로서의 `Pragma: no-cache`이고, 응답에 붙이는 경우는 비표준 관용 사용이다.

```
Pragma: no-cache
```

`Cache-Control: no-cache`와 같이 보내는 코드를 옛날 자바 프로젝트에서 자주 본다. HTTP/1.0만 지원하는 옛날 프록시 호환성을 위해 추가하는 식이다. 현실적으로 의미 있는 효과는 거의 없고, `Cache-Control`이 항상 우선한다.

레거시 시스템과 인터페이스 작업을 하다 보면 명세에 `Pragma: no-cache`를 요구하는 경우가 가끔 있다. 그럴 때만 그대로 따르고, 새로 만드는 응답에 굳이 추가할 필요는 없다.

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

### CDN-Cache-Control / Surrogate-Control

`Cache-Control` 하나로 브라우저와 CDN의 캐시 정책을 모두 표현하다 보면 충돌이 생긴다. `s-maxage`로 어느 정도는 분리할 수 있지만, "브라우저는 매번 재검증하고 CDN만 길게 캐시한다" 같은 패턴은 단일 헤더로 표현하기 까다롭다.

CDN 전용 헤더를 별도로 두면 정책이 깔끔하게 분리된다.

#### CDN-Cache-Control

비교적 최근에 표준화된 헤더다(RFC 9213). CDN만 이 헤더를 따르고, 브라우저나 일반 프록시는 무시한다.

```
Cache-Control: max-age=0, no-cache
CDN-Cache-Control: max-age=600
```

브라우저는 매번 재검증하지만 CDN은 10분간 캐시한다. SSR로 렌더링한 페이지에서 자주 쓰는 패턴이다. 사용자에게는 항상 최신 응답이 가는 것처럼 보이지만 오리진 부하는 거의 없다.

#### Surrogate-Control

Fastly가 오래전부터 사용해온 헤더다. CDN-Cache-Control과 비슷한 역할이지만 비표준이다.

```
Cache-Control: max-age=60
Surrogate-Control: max-age=86400
```

`Surrogate-Control`이 있으면 Fastly는 그것을 따르고, 클라이언트로 응답을 보낼 때 이 헤더를 제거한다. 클라이언트는 `Cache-Control`만 본다.

#### CDN별 차이

- **Fastly**: `Surrogate-Control`을 우선 인식. 없으면 `Cache-Control`을 따른다. CDN-Cache-Control도 최근에는 인식한다.
- **Cloudflare**: `CDN-Cache-Control`을 인식한다. 없으면 `Cache-Control`을 따른다. 다만 대시보드의 Cache Rules가 응답 헤더보다 우선하는 경우가 많아, 헤더만 보고 동작을 단정하기는 어렵다.
- **CloudFront**: 표준 `Cache-Control`만 본다. 헤더 분리가 필요하면 Lambda@Edge나 CloudFront Functions로 응답을 변환한다.
- **Akamai**: `Edge-Control`이라는 자체 헤더를 쓴다.

CDN을 여러 개 운영하거나 교체할 때, 같은 응답이 다르게 캐시될 수 있다는 점을 항상 의식한다. CDN을 바꿨더니 캐시 정책이 그대로 동작할 거라고 가정하면 안 된다.

### 계층별 Cache-Control 동작 요약

| 디렉티브 | 브라우저 | 프록시/CDN |
|---------|---------|-----------|
| `private` | 캐시 가능 | 캐시 불가 |
| `public` | 캐시 가능 | 캐시 가능 |
| `max-age` | 적용 | `s-maxage` 없으면 적용 |
| `s-maxage` | 무시 | 적용 (`max-age` 대신) |
| `no-store` | 저장 안 함 | 저장 안 함 |

---

## Authorization 헤더가 포함된 요청의 캐싱

요청에 `Authorization` 헤더가 들어가면 공유 캐시(프록시, CDN)는 기본적으로 응답을 캐싱하지 않는다. RFC 7234 §3.2 규정이다. 한 사용자의 인증된 응답이 다른 사용자에게 전달되는 사고를 막기 위한 안전장치다.

이 제한을 풀려면 응답에 다음 디렉티브 중 하나가 명시되어 있어야 한다.

- `public`: 공유 캐시도 저장 가능. 응답 본문이 진짜 모든 사용자에게 동일할 때만 안전하다.
- `must-revalidate`: 만료된 캐시는 항상 재검증한다.
- `s-maxage=N`: 공유 캐시 전용 TTL이 명시되면 캐싱이 허용된다.

```http
GET /api/products HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1...

HTTP/1.1 200 OK
Cache-Control: public, max-age=300
Content-Type: application/json
```

API 응답에 `public, max-age=...`를 무심코 붙였다가 사고가 나는 사례가 있다. 토큰 기반으로 사용자별 응답을 만드는 API에 `public`을 붙이면 CDN이 한 사용자 응답을 다른 사용자에게 그대로 돌려준다. 마이페이지 응답이 다른 사용자에게 보이는 식이다. 사용자별로 다른 응답이 나오는 엔드포인트는 절대 `public`이나 `s-maxage`를 쓰지 말고 `private` 또는 `no-store`를 쓴다.

브라우저(Private cache)는 이 제한을 받지 않는다. `Authorization` 헤더가 있어도 `Cache-Control`에 따라 정상적으로 캐싱한다. 단일 사용자 환경에서 같은 사람이 같은 토큰으로 같은 응답을 다시 받는 경우는 안전하다고 본다.

실무 팁: 인증이 필요한 API에 캐시를 적용하고 싶으면 응답을 사용자에 종속되지 않게 설계한 다음 `private, max-age=N`으로 브라우저 캐시만 활용하는 쪽이 안전하다. CDN 레벨 캐싱이 꼭 필요하면 인증 토큰 자체를 캐시 키에 포함시켜 사용자별로 분리된 캐시를 두거나, 인증 검증 후 토큰 없는 내부 URL로 다시 요청하는 식의 분리가 필요하다.

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

## POST/PUT 응답 캐싱과 PRG 패턴

GET 외 메서드의 응답은 일반적으로 캐싱되지 않는다. POST는 사이드이펙트가 있는 요청이라 같은 URL로 다시 요청해도 결과가 다를 수 있고, PUT/DELETE/PATCH도 마찬가지다. 브라우저와 대부분의 CDN은 GET과 HEAD만 캐시 대상으로 다룬다.

RFC 9111은 POST 응답도 캐싱이 가능한 조건을 정의하긴 한다. `Cache-Control`에 명시적인 `max-age`나 `s-maxage`가 있고 응답에 `Content-Location` 헤더가 있으면, 그 URL의 캐시로 저장될 수 있다. 다만 실제로 이 동작을 구현한 캐시는 거의 없으니 POST 응답 캐싱을 시도하지는 말자.

### POST 후 GET — PRG 패턴과 캐시

폼을 POST로 제출하고 결과 페이지로 리다이렉트하는 PRG(Post-Redirect-Get) 패턴은 캐시와 자주 엮인다.

```
POST /orders HTTP/1.1
Content-Type: application/x-www-form-urlencoded

productId=123&quantity=1

HTTP/1.1 303 See Other
Location: /orders/9876
```

브라우저는 303 응답을 받고 `Location`이 가리키는 URL로 GET 요청을 보낸다. 이때 GET 응답이 공유 캐시에 그대로 저장되면 다음 사용자가 같은 URL을 열었을 때 다른 사람의 주문 결과가 보일 수 있다. `/orders/9876` 같은 개인화된 페이지는 반드시 `Cache-Control: private, no-store`를 명시한다.

POST 직후 새로고침했을 때 "양식 다시 제출" 경고가 뜨는 이유도 PRG 미적용 때문이다. POST 응답을 그대로 렌더링하면 새로고침 시 POST가 재전송된다. 결제처럼 부수효과가 있는 처리는 PRG로 항상 GET 페이지로 넘긴다.

### POST 응답 자체에 대한 캐시

REST API에서 POST가 자원 생성이 아닌 조회에 가깝게 쓰이는 경우가 있다. GraphQL의 단일 엔드포인트 POST나 검색 조건이 너무 길어서 POST로 받는 검색 API 같은 경우다. 이런 응답을 HTTP 캐시로 처리하기는 어렵다. `Cache-Control`을 설정해도 브라우저가 알아서 POST 응답을 캐싱하지는 않기 때문이다.

대안으로는,

- 클라이언트 라이브러리 자체 메모리 캐시(Apollo Client, React Query, SWR 등)를 활용한다.
- GraphQL의 경우 `GET` 메서드와 Persisted Query를 조합해서 CDN 캐시를 활용한다.
- 검색 키를 정규화해 GET URL로 바꾸는 식의 우회를 고려한다.

---

## Service Worker Cache와 HTTP 캐시 우선순위

PWA를 만들 때 Service Worker의 Cache API를 쓰면 HTTP 캐시와는 다른 별도의 캐시 계층이 생긴다. 같은 URL에 대한 응답이 두 캐시에 동시에 존재할 수 있어 동작이 헷갈린다.

요청은 다음 순서로 처리된다.

1. **Service Worker `fetch` 핸들러**: 등록된 SW가 있으면 모든 네트워크 요청이 일단 여기를 거친다.
2. **SW Cache API**: SW 안에서 `caches.match()`로 조회. 히트하면 즉시 응답이 반환된다. 이 시점에 HTTP 캐시는 아직 보이지 않는다.
3. **HTTP 캐시(브라우저 캐시)**: SW가 `fetch(request)`를 호출할 때 브라우저는 평소처럼 HTTP 캐시를 먼저 본다.
4. **네트워크**: HTTP 캐시도 미스면 실제 서버까지 간다.

```javascript
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      // fetch는 HTTP 캐시 → 네트워크 순서로 동작
      return fetch(event.request);
    })
  );
});
```

여기서 `fetch(event.request)`가 HTTP 캐시를 한 번 더 통과한다는 점이 중요하다. SW Cache에 없어도 HTTP 캐시에 있으면 네트워크 요청이 발생하지 않는다. 강제로 네트워크에서 가져오려면 `fetch(event.request, { cache: 'no-store' })`를 명시한다.

### 캐시 갱신 타이밍 함정

배포 시 자주 겪는 문제: HTML은 SW가 캐시하고 있고, JS/CSS는 HTTP 캐시에 남아 있어 새 버전이 안 보인다.

- SW 캐시는 `caches.delete()`나 SW 버전 업그레이드 시점에만 비워진다. `Cache-Control` 헤더와는 무관하다.
- 새 SW를 배포해도 `skipWaiting()`을 명시하지 않으면 모든 탭이 닫혔다 다시 열려야 활성화된다.
- 사용자가 브라우저를 종료하지 않고 계속 쓰면 새 SW가 영영 활성화되지 않는 경우도 있다.

운영하다 보면 "분명히 배포했는데 일부 사용자만 이전 버전을 본다"는 제보가 들어온다. 십중팔구 SW 캐시 문제다. 배포 직후 클라이언트 측 버그가 발견되면 SW 코드를 같이 업데이트하거나, 최악의 경우 SW를 unregister하는 코드를 잠시 배포하는 수밖에 없다. SW를 도입할 때 `unregister`로 빠져나갈 비상 경로를 미리 코드에 넣어두는 편이 안전하다.

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

## 캐시 키 정규화 함정

CDN과 프록시는 URL을 그대로 캐시 키로 쓴다. 의미상 같은 리소스라도 URL 문자열이 조금 다르면 별개의 캐시 항목으로 저장된다.

### 쿼리 스트링 순서 차이

```
/api/search?lang=ko&page=1
/api/search?page=1&lang=ko
```

서버 입장에서는 같은 결과지만 캐시는 두 항목으로 저장한다. 캐시 히트율이 떨어지고 오리진 부하가 늘어난다. 클라이언트 코드 한쪽에서 파라미터 순서를 바꿔서 요청을 보내면, 첫 사용자는 항상 캐시 미스를 겪는다.

### 의미 없는 파라미터 차이

UTM 트래킹, 인앱 브라우저가 붙이는 파라미터, fingerprint 회피 목적의 timestamp 등이 모두 캐시 항목을 늘린다.

```
/products/100
/products/100?utm_source=email
/products/100?fbclid=IwAR...
/products/100?_=1709999999
```

같은 페이지에 대해 캐시가 여러 벌 생긴다. 트래픽이 많은 서비스라면 CDN 비용이 의외로 빠르게 늘어나고, 더 큰 문제는 오리진 서버 요청 폭증이다. 마케팅 캠페인을 시작하자마자 오리진 부하가 평소의 5배가 되는 경우가 있다.

### 해결 방법

CDN별로 캐시 키 정규화 옵션을 제공한다.

- **CloudFront**: Cache Policy의 Query string에서 화이트리스트만 캐시 키에 포함하도록 설정
- **Cloudflare**: Cache Rules에서 "Ignore query string" 또는 특정 파라미터만 키로 사용
- **Fastly**: VCL에서 `req.url`을 직접 정규화. `std.querystring.filter_except`로 화이트리스트 운영
- **Varnish**: `vmod_querystring`으로 정렬 및 필터링

Nginx 리버스 프록시도 비슷하게 처리한다.

```nginx
# 특정 파라미터만 캐시 키로 사용
map $args $cache_key_args {
    ~(?:^|&)(lang=[^&]+) $1;
    default "";
}

server {
    location /products/ {
        proxy_cache my_cache;
        proxy_cache_key "$scheme$host$uri?$cache_key_args";
        proxy_pass http://backend;
    }
}
```

캐시 정책 도입 직후에는 정상이다가 트래픽이 늘면서 히트율이 떨어진다. CDN 대시보드에서 캐시 키 다양성(unique cache keys)을 모니터링하고, 평소보다 갑자기 많아지면 정규화 룰부터 점검한다.

쿠키도 동일한 함정이 있다. CDN이 쿠키 값을 캐시 키에 포함하도록 설정되어 있으면 사용자별로 캐시가 분리된다. 의도한 동작인지 정확히 확인한다.

---

## 캐시 포이즈닝(Cache Poisoning)

공유 캐시가 사용자별로 달라야 할 응답을 일률적으로 저장해서, 다른 사용자에게 잘못된 응답이 전달되는 보안 사고다. 헤더 설정 실수가 곧 보안 취약점이 된다.

### 전형적 사례: Vary 누락

서버가 `User-Agent`나 `X-Forwarded-Proto`에 따라 다른 응답을 만들면서 `Vary`를 명시하지 않는 경우다.

```
GET /home HTTP/1.1
Host: example.com
X-Forwarded-Proto: http

HTTP/1.1 200 OK
Cache-Control: public, max-age=300
# Vary 헤더 없음
```

CDN이 이 응답을 캐시 키 `/home`으로 저장한다. 이후 누군가 `X-Forwarded-Proto: https`로 요청해도 같은 응답이 돌아간다. 서버가 HTTP 요청에 대해 본문이나 리다이렉트 URL에 HTTP 스킴을 박았다면, HTTPS 사용자에게도 HTTP 링크가 그대로 노출된다.

### Unkeyed 헤더 인젝션

공격자는 캐시 키에 포함되지 않는 헤더(unkeyed)를 조작해 응답에 영향을 주는 방식을 쓴다. 대표적으로 `X-Forwarded-Host`, `X-Original-URL`, `X-Host` 등이 있다.

```
GET /home HTTP/1.1
Host: example.com
X-Forwarded-Host: evil.com
```

서버가 응답 본문이나 리다이렉트 URL에 `X-Forwarded-Host` 값을 그대로 박아 넣고, CDN이 이 응답을 일반 `/home` 캐시로 저장하면 다음 사용자들에게 `evil.com` 링크가 전달된다. James Kettle이 PortSwigger 블로그에 정리한 Practical Web Cache Poisoning 시리즈가 이 패턴의 출발점이다.

### 방어 방법

- 응답에 영향을 주는 헤더는 모두 `Vary`에 명시한다. `Vary: Accept-Encoding, Accept-Language` 같은 식으로.
- 신뢰하지 않는 헤더는 응답에 사용하지 않는다. `X-Forwarded-Host`, `X-Original-URL` 같은 헤더는 프록시 단에서 검증한 것만 받아들인다. 외부에서 임의로 들어온 헤더가 백엔드까지 그대로 도달하면 안 된다.
- 에러 응답은 캐싱하지 않거나 짧게 캐싱한다. 공격자가 의도적으로 깨진 요청을 보내 에러 응답을 캐시에 박아 넣는 패턴이 있다.
- 캐시 가능한 엔드포인트와 그렇지 않은 엔드포인트를 명확히 분리한다. 사용자별 콘텐츠가 섞인 페이지를 통째로 CDN에 캐시하지 않는다.
- 모니터링: CDN 응답 시간이나 본문 크기에 갑자기 이상한 분포가 나타나면 포이즈닝 가능성을 의심한다.

CDN 캐시는 한 번 오염되면 TTL이 끝날 때까지 모든 사용자에게 영향을 준다. 발견 즉시 무효화 API로 강제 삭제하고, 어느 헤더 때문에 발생했는지 파악해서 같은 사고가 반복되지 않게 한다.

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
