---
title: CDN 동작 원리와 실무 운영
tags:
  - network
  - cdn
  - cache
  - cloudfront
  - cloudflare
updated: 2026-06-04
---

# CDN 동작 원리와 실무 운영

CDN(Content Delivery Network)은 Origin 서버에 있는 콘텐츠를 전 세계 Edge 노드에 복제해두고, 사용자에게 가장 가까운 노드가 응답하게 만드는 분산 캐시 인프라다. 기본 개념은 간단하지만 실제 운영에서는 캐시 키 설계, Vary 헤더 처리, 무효화 비용, Signed URL 같은 부분에서 사고가 자주 난다. 한 번이라도 운영 환경에서 캐시 히트율이 갑자기 떨어지거나, 특정 사용자에게만 다른 응답이 캐싱돼서 사고를 친 경험이 있으면 이 문서가 도움이 될 것이다.

브라우저/HTTP 레벨의 캐싱은 [HTTP_Caching](../HTTP/HTTP_Caching.md)에서 다룬다. 여기서는 인프라 레벨에서 CDN이 어떻게 캐시를 보관하고 무효화하는지, 그리고 실제 CDN 벤더(CloudFront, Cloudflare, Fastly)를 운영할 때 부딪히는 문제들에 집중한다.

## Origin과 Edge의 관계

CDN의 구조는 단순하다. 진짜 원본 데이터를 가진 Origin이 있고, 그 사본을 전 세계 여러 지역(PoP, Point of Presence)에 분산 배치한 Edge 노드들이 있다. 사용자 요청은 DNS 또는 Anycast를 통해 가까운 Edge로 라우팅되고, Edge가 캐시를 가지고 있으면 그대로 응답하고, 없으면 Origin까지 가서 가져온다.

```
[사용자] → DNS/Anycast → [Edge PoP]
                            ↓ (캐시 없음)
                       [Origin Shield]
                            ↓
                         [Origin]
```

Edge 노드는 보통 수백 개에서 수천 개 단위로 분산돼 있다. CloudFront는 600개 이상, Cloudflare는 300개 이상의 PoP을 운영한다. 사용자 입장에서는 평균 RTT가 200ms에서 30ms로 줄어드는 효과가 가장 크다. 정적 파일을 1MB 다운로드한다고 했을 때, RTT가 줄어드는 만큼 TCP slow start 구간에서 처리량이 빠르게 올라가니까 체감 속도 차이가 훨씬 크다.

실무에서 자주 오해하는 부분이 있다. Edge가 캐시를 가지고 있다고 모든 사용자가 동일한 Edge로 가는 건 아니다. Anycast 기반 CDN은 BGP 라우팅에 따라 같은 도시 안에서도 ISP마다 다른 PoP으로 갈 수 있다. 그래서 같은 객체라도 Edge 노드 수만큼 캐시 복사본이 따로 존재한다. 이게 무효화 비용과 직결된다.

## Pull 모델과 Push 모델

CDN이 Origin에서 콘텐츠를 가져오는 방식은 크게 두 가지다.

### Pull 모델

가장 일반적이다. 사용자가 요청하면 Edge가 캐시 미스 시점에 Origin에서 끌어오는(lazy fetch) 방식이다. CloudFront, Cloudflare, Fastly 모두 기본은 Pull이다.

장점은 운영이 단순하다는 점이다. Origin에 파일을 올려두기만 하면 첫 요청 때 자동으로 캐싱된다. 정적 자산이 수십만 개 있어도 실제 요청되는 것만 캐시되므로 Edge 스토리지 효율도 좋다.

단점은 첫 요청(cache miss)이 느리다는 점이다. 신규 콘텐츠를 배포한 직후 사용자가 몰리면 모든 Edge가 동시에 Origin으로 요청을 보내는 thundering herd 현상이 발생한다. 이걸 막기 위해 Origin Shield(뒤에 설명)나 request coalescing을 쓴다.

### Push 모델

사용자 요청과 무관하게 Origin이 콘텐츠를 미리 Edge로 밀어 넣는 방식이다. 게임 패치, 영화 출시 같이 대규모 트래픽이 특정 시간에 몰리는 경우에 쓴다. CloudFront는 자체 Push를 지원하지 않고 S3 multi-region replication 같은 우회 방식을 쓰지만, 일부 미디어 전용 CDN(Akamai NetStorage 등)은 명시적 Push를 지원한다.

실무에서는 순수 Push만 쓰는 경우는 드물다. 대부분 Pull을 기본으로 두고, 특정 시점에 대해서만 사전 워밍(prewarm)을 수동으로 트리거한다. 예를 들어 영상 스트리밍 서비스에서 신작 공개 1시간 전에 주요 PoP에 대해 HEAD 요청을 자동으로 날려서 캐시를 채워두는 식이다.

## Cache Key 설계

Cache Key는 CDN이 "이 요청이 캐시에 있는 것과 같은 요청인지" 판단하는 기준이다. 기본값은 보통 호스트명 + 경로 + 쿼리스트링이다. 여기서 어떤 요소를 포함하고 빼느냐가 캐시 히트율을 결정한다.

### 쿼리스트링 처리

가장 골치 아픈 부분이다. 보통 다음 세 가지 옵션 중에 선택한다.

- 전체 쿼리스트링 포함: 안전하지만 캐시 히트율 떨어진다. 추적용 파라미터(`utm_source`, `gclid`, `fbclid`)가 붙으면 같은 콘텐츠인데도 캐시 키가 달라진다.
- 전체 무시: 위험하다. `?id=1`과 `?id=2`가 같은 캐시로 묶이면 사고난다.
- 화이트리스트(특정 파라미터만 키에 포함): 가장 흔히 쓴다. 콘텐츠 식별에 실제로 영향을 주는 파라미터만 키에 넣고 나머지는 무시한다.

```text
원본 요청: /article/123?utm_source=google&id=42&ref=twitter
화이트리스트: [id]
→ Cache Key: /article/123?id=42
```

CloudFront에서는 Cache Policy에서 `QueryStringsConfig`로 설정하고, Cloudflare는 Cache Rule에서 `cache_key.custom_key.query_string`을 쓴다. Fastly는 VCL에서 직접 `req.url`을 정규화한다.

### 헤더 기반 분기와 Vary

같은 URL이라도 사용자에 따라 다른 응답을 줘야 하는 경우가 있다. 모바일/데스크톱 분기, 언어별 분기, 압축 방식 분기 같은 게 대표적이다. 이때 쓰는 게 `Vary` 헤더다.

`Vary: Accept-Encoding`을 주면 CDN은 `Accept-Encoding` 헤더 값별로 별도의 캐시를 보관한다. `gzip`, `br`, `gzip, deflate` 같이 값이 조금만 달라도 캐시 키가 분리된다.

여기서 함정이 있다. `Vary: User-Agent`를 그대로 쓰면 캐시 히트율이 0에 수렴한다. User-Agent 문자열은 브라우저 버전마다 다 다르고, 같은 Chrome이라도 마이너 버전 차이로 매번 새 키가 생긴다. 실제로 운영 중인 서비스에서 캐시 히트율이 갑자기 5%로 떨어져서 봤더니, 새로 배포한 미들웨어가 `Vary: User-Agent`를 무조건 붙이고 있었던 사례가 있다.

User-Agent로 모바일/PC 분기를 하고 싶으면 두 가지 방법이 있다.

- Origin에서 User-Agent를 분석해서 `Vary: X-Device-Type` 같은 정규화된 헤더로 응답하고, CDN에서 그 헤더 기준으로 캐시 키를 만든다.
- CDN의 device detection 기능(CloudFront `CloudFront-Is-Mobile-Viewer`, Cloudflare `cf-device-type`)을 써서 정규화된 값으로 키를 만든다.

`Vary: Cookie`도 위험하다. 쿠키 값은 사용자마다 다르므로 사실상 캐시가 무력화된다. 인증된 사용자 콘텐츠는 캐싱하지 말거나, 특정 쿠키 키만 화이트리스트로 키에 포함시키는 방식을 쓴다.

### Vary 헤더 함정 정리

- `Vary: *`는 절대 캐시하지 말라는 의미가 된다. 실수로 붙이면 모든 캐시가 비활성화된다.
- `Vary` 헤더에 나열한 헤더 이름은 대소문자 구분하지 않지만, 값은 정확히 일치해야 한다. `gzip, deflate`와 `deflate, gzip`은 다른 키가 된다.
- Origin이 응답마다 다른 `Vary` 값을 주면 캐시가 깨질 수 있다. 일관되게 같은 헤더 목록을 유지해야 한다.

## Cache-Control과 stale-while-revalidate

CDN이 콘텐츠를 얼마나 오래 캐싱할지는 Origin이 보내는 `Cache-Control` 헤더로 결정된다. CDN 자체 TTL 설정도 있지만, 보통은 Origin 헤더가 우선이다(설정에 따라 강제 오버라이드 가능).

### 주요 디렉티브

- `max-age=N`: 브라우저와 모든 캐시에 N초간 신선하다고 선언.
- `s-maxage=N`: CDN과 같은 공유 캐시에만 적용되는 TTL. `max-age`보다 우선.
- `public`: 공유 캐시 가능.
- `private`: 브라우저 캐시만 허용, CDN 캐시 금지.
- `no-cache`: 캐시는 하되 매번 Origin에 재검증 요청.
- `no-store`: 캐시 자체 금지.

실무에서 정적 자산(JS, CSS, 이미지)은 보통 빌드 시점에 파일명에 해시를 박고(`app.a3f2b1.js`) `Cache-Control: public, max-age=31536000, immutable`로 1년 캐싱한다. HTML은 짧게 잡거나(`max-age=60`) `no-cache`로 두고 ETag 검증에 의존한다.

### stale-while-revalidate

가장 실무에서 유용한 디렉티브 중 하나다. `Cache-Control: max-age=60, stale-while-revalidate=600`을 주면, 캐시는 60초간 fresh로 응답하고, 60초가 지난 다음 600초까지는 "일단 stale 응답을 즉시 주고, 백그라운드에서 Origin에 가서 갱신"한다.

장점이 명확하다. 사용자는 60초마다 한 번씩 느려지는 게 아니라, 항상 캐시 응답을 받는다. Origin 갱신은 비동기로 진행되므로 사용자 응답 시간에 영향이 없다. Origin 부하도 줄어든다.

```
Cache-Control: public, max-age=60, stale-while-revalidate=600
```

CloudFront는 2020년부터 지원하고, Cloudflare는 일부 플랜에서 지원한다. Fastly는 `stale-while-revalidate`와 별도로 `stale-if-error`도 같이 활용해서 Origin 장애 시에도 캐시 응답을 유지하는 패턴을 자주 쓴다.

### TTL 설정 실수

가장 흔한 실수는 Origin이 `Cache-Control` 헤더를 빼먹는 경우다. 헤더가 없으면 CDN은 자체 기본 TTL을 적용하는데, 벤더마다 기본값이 다르다. CloudFront는 24시간이 기본이고, Cloudflare는 파일 확장자별로 자체 휴리스틱을 쓴다. 이러면 같은 코드가 배포 환경마다 다르게 캐싱된다.

운영 중인 API 서버를 CDN 뒤에 뒀는데 `Cache-Control`을 안 보내서 응답이 24시간 캐싱되는 사고를 본 적이 있다. POST 요청은 캐싱 안 되지만 GET API는 캐싱 가능 응답으로 분류돼서 다른 사용자의 데이터가 응답으로 나가는 상황까지 갔다. API 서버 앞에 CDN을 둘 때는 반드시 `Cache-Control: no-store` 또는 `private`을 명시적으로 보내야 한다.

## Origin Shield

대규모 CDN에서 자주 쓰는 중간 계층이다. Edge 노드가 수백 개라서 캐시 미스가 나면 수백 개가 동시에 Origin을 때린다. 이걸 막기 위해 Edge와 Origin 사이에 하나의 중앙 캐시 계층을 두는 게 Origin Shield다.

```
[Edge PoP 1] ─┐
[Edge PoP 2] ─┼→ [Origin Shield] → [Origin]
[Edge PoP N] ─┘
```

모든 Edge의 미스 트래픽이 Shield로 집중되고, Shield가 캐시 미스일 때만 Origin에 요청한다. Origin 입장에서는 동시 요청이 수백 분의 일로 줄어든다.

CloudFront는 Origin Shield를 명시적으로 활성화할 수 있는 옵션이 있다. 특정 리전을 Shield로 지정하면 모든 Edge가 그 리전을 거친다. Cloudflare는 Argo Smart Routing 또는 Tiered Cache로 비슷한 기능을 제공한다. Fastly는 Origin Shielding 옵션을 PoP 단위로 설정한다.

실무 팁: Origin이 한국에 있으면 Shield도 가까운 리전(서울, 도쿄)에 두는 게 일반적이다. Shield와 Origin 간 거리가 멀면 캐시 미스 시 latency가 더 늘어난다. 멀티 리전 Origin을 쓴다면 Shield도 리전별로 분리하거나 가장 가까운 리전 단위로 묶는다.

## 캐시 무효화의 비용

CDN의 가장 어려운 부분이 캐시 무효화다. 분산된 수백 개 PoP에서 동일한 객체를 한 번에 지우는 건 비용이 든다. 무효화 방식은 크게 세 가지다.

### Purge (즉시 무효화)

특정 URL 패턴을 모든 PoP에서 즉시 삭제한다. CloudFront에서는 Invalidation, Cloudflare에서는 Purge API, Fastly에서는 Instant Purge라고 부른다.

비용이 다르다. CloudFront는 월 1000개 path까지 무료, 그 이상은 path당 $0.005. wildcard(`/images/*`)도 1개로 카운트된다. Cloudflare는 무제한이지만 한 번에 보낼 수 있는 URL 수에 제한(Enterprise 외 30개)이 있다. Fastly는 Instant Purge가 무료고 150ms 이내에 전 세계 전파를 보장하는 게 가장 큰 장점이다.

대량 배포 후 전체 무효화(`/*`)는 가능은 하지만 비용도 크고 캐시 히트율이 즉시 0으로 떨어지므로 Origin이 트래픽을 다 받아야 한다. 그래서 실무에서는 가급적 안 쓴다.

### Versioning (캐시 키 자체를 바꾸기)

가장 안전한 방식이다. 파일명이나 경로에 버전 식별자를 박는다. `/static/app.js`가 아니라 `/static/app.v123.js` 또는 `/static/app.a3f2b1.js`로 빌드 시점에 해시를 박는다. 새 버전을 배포해도 URL이 다르므로 기존 캐시는 그대로 두고, HTML만 새 URL로 바꿔서 배포한다.

이러면 무효화 자체가 필요 없다. 기존 캐시는 TTL 만료될 때까지 그냥 두고, 새 콘텐츠는 다른 키로 캐싱된다. 정적 자산은 이 방식을 기본으로 가는 게 맞다.

### Surrogate Key / Cache Tag (그룹 무효화)

Fastly와 Cloudflare Enterprise에서 지원하는 기능. Origin이 응답에 `Surrogate-Key: article-123 user-456` 같은 태그를 붙여서 보내고, 나중에 `article-123` 태그가 붙은 모든 캐시를 한 번에 무효화할 수 있다.

블로그 시스템에서 카테고리 페이지가 100개 있고 글 하나 수정될 때 관련 페이지만 무효화하고 싶을 때 유용하다. 일일이 URL을 추적할 필요 없이 태그만 잘 관리하면 된다.

```text
응답 헤더:
  Surrogate-Key: article-123 category-tech homepage

무효화 API 호출:
  PURGE /service/{id}/purge/article-123
  → article-123 태그가 붙은 모든 캐시 무효화
```

CloudFront는 이 기능이 없다. 대신 Lambda@Edge로 비슷한 로직을 구현하거나, 무효화 path 패턴을 잘 설계해서 우회한다.

## Signed URL과 Signed Cookie

비공개 콘텐츠를 CDN으로 서빙할 때 쓰는 인증 방식이다. Origin이 미리 서명된 URL을 발급하면, CDN이 서명을 검증하고 통과한 요청만 캐시/응답한다.

### Signed URL

URL 자체에 만료 시간, 서명, 정책을 쿼리스트링으로 박는다.

```text
https://cdn.example.com/private/video.mp4?
  Expires=1717488000&
  Signature=xY9z...
  &Key-Pair-Id=APKA...
```

장점: 객체 단위로 권한 제어 가능. 단점: 서명 만료가 짧으면 URL을 자주 재발급해야 하고, URL이 다르면 캐시 키가 분리될 수 있다.

캐시 키와 충돌하는 부분에 주의해야 한다. 서명 파라미터가 캐시 키에 포함되면 사용자마다 다른 캐시가 생긴다. CloudFront는 자동으로 `Signature`, `Expires`, `Key-Pair-Id`, `Policy`를 캐시 키에서 제외한다. 직접 만들 때는 이 점을 신경 써야 한다.

### Signed Cookie

여러 객체를 한 번에 보호할 때 쓴다. 사용자가 로그인하면 Origin이 서명된 쿠키를 설정하고, 이후 같은 도메인의 모든 요청에서 쿠키로 인증한다. HLS 스트리밍처럼 .m3u8 + 수십 개 .ts 세그먼트를 한 번에 보호할 때 유용하다.

쿠키 기반은 URL이 깔끔하게 유지되니까 캐시 키 문제가 없다. 다만 쿠키는 도메인 단위라서 cross-domain 시나리오에는 안 맞는다.

실무에서 영상 스트리밍 서비스는 보통 Signed Cookie를 쓴다. 광고 트래커, 임시 다운로드 링크 같은 건 Signed URL을 쓴다.

## CloudFront, Cloudflare, Fastly 실무 차이

세 벤더 모두 기본 CDN 기능은 비슷하지만 운영 관점에서 차이가 크다.

### CloudFront

AWS 생태계와 통합이 가장 강점. S3, ALB, Lambda@Edge, WAF가 모두 한 콘솔에서 묶인다. Origin이 AWS에 있으면 데이터 전송 비용이 저렴하고(같은 리전 무료), IAM 기반 보안이 자연스럽게 적용된다.

단점은 설정 변경 전파가 느리다. Distribution을 수정하면 몇 분에서 십수 분까지 걸린다. 무효화도 보통 30초에서 1분 정도. 빠르게 반복 배포하는 환경에서는 답답하다.

캐시 정책이 2020년 개편 후 깔끔해졌다. Cache Policy, Origin Request Policy, Response Headers Policy로 분리돼서 재사용 가능한 컴포넌트로 관리할 수 있다.

### Cloudflare

DNS, DDoS 방어, WAF, Workers(엣지 컴퓨팅)를 패키지로 묶어서 제공한다. 무료 플랜이 강력해서 개인 프로젝트나 소규모 서비스에 많이 쓴다. Workers는 V8 isolate 기반이라 Lambda@Edge보다 cold start가 거의 없고 응답 속도가 빠르다.

캐시 제어가 Page Rules 또는 Cache Rules로 가는데, 무료 플랜은 룰 수가 제한된다. Enterprise로 가면 캐시 키 커스터마이징, Tiered Cache, Argo Smart Routing 같은 고급 기능을 쓸 수 있다.

단점은 Origin이 AWS에 있으면 Egress 비용이 별도로 청구된다는 점이다. 트래픽 규모가 크면 비용 분석이 필요하다.

### Fastly

VCL(Varnish Configuration Language)로 캐시 동작을 코드로 정의할 수 있는 게 가장 큰 강점이다. 다른 CDN은 정해진 옵션만 조합하는 식이라면, Fastly는 요청/응답 단계마다 임의 로직을 넣을 수 있다. A/B 테스트, 복잡한 헤더 정규화, 동적 라우팅 같은 게 자유롭다.

Instant Purge가 150ms 이내 보장이라 자주 무효화가 필요한 뉴스/미디어 사이트에서 강점이 있다. NYT, Vox Media 같은 곳이 Fastly를 쓰는 이유다.

단점은 학습 곡선이 가파르다. VCL을 모르면 다른 CDN보다 어렵게 느껴진다. 그리고 무료 플랜이 없어서 진입 장벽이 높다.

### 벤더 선택 기준

- AWS 생태계 안에서 모든 인프라가 돌아가면 CloudFront.
- 트래픽이 적거나 빠른 시작이 필요하면 Cloudflare 무료/Pro.
- 캐시 무효화가 빈번하고 복잡한 로직이 필요하면 Fastly.
- 글로벌 미디어 스트리밍은 Akamai, Limelight 같은 전용 CDN도 검토 대상.

## 캐시 히트율 디버깅

캐시 히트율(Cache Hit Ratio, CHR)은 CDN 운영의 가장 중요한 지표다. 90% 이상이면 보통 정상, 70% 이하면 뭔가 잘못된 거다.

### 응답 헤더로 확인

대부분 CDN은 응답 헤더에 캐시 상태를 표시한다.

- CloudFront: `X-Cache: Hit from cloudfront` / `Miss from cloudfront` / `RefreshHit from cloudfront`
- Cloudflare: `CF-Cache-Status: HIT` / `MISS` / `EXPIRED` / `BYPASS` / `DYNAMIC`
- Fastly: `X-Cache: HIT` / `MISS`, 그리고 `X-Served-By`로 어느 PoP에서 응답했는지 확인

```bash
curl -I https://cdn.example.com/static/app.js
# HTTP/2 200
# x-cache: Hit from cloudfront
# x-amz-cf-pop: ICN51-P1
# age: 1234
```

`Age` 헤더는 캐시된 후 얼마나 시간이 지났는지를 초 단위로 알려준다. 무효화 직후 들어온 요청인지, 한참 묵은 캐시인지 확인할 때 쓴다.

### 캐시 미스 원인 분석

캐시 히트율이 낮으면 보통 다음 중 하나다.

1. **TTL이 너무 짧다**: `Cache-Control: max-age=10` 같이 짧으면 만료가 잦다.
2. **캐시 키가 너무 잘게 쪼개진다**: 쿼리스트링, 헤더, 쿠키 중 불필요한 게 키에 포함된 경우.
3. **Vary 헤더가 잘못 설정됐다**: 특히 `Vary: User-Agent`, `Vary: Cookie`가 의심.
4. **응답에 `Set-Cookie`가 있다**: 기본적으로 CDN은 `Set-Cookie`가 붙은 응답을 캐싱하지 않는다(private 응답으로 간주). Origin이 정적 자산에 `Set-Cookie`를 실수로 붙이는 경우가 있다.
5. **Origin이 `Cache-Control: private`, `no-store`를 보낸다**: 의도와 다르게 캐시 비활성화.
6. **요청 메서드가 GET/HEAD가 아니다**: POST, PUT 등은 기본 캐시 안 됨.

실제 디버깅할 때는 캐시 미스가 나는 URL을 찾아서 응답 헤더를 전부 dump 떠보고, Origin 응답과 CDN 응답을 비교한다. CloudFront는 Real-time Logs, Cloudflare는 Logpush, Fastly는 Real-time Analytics로 캐시 미스 비율이 높은 URL을 찾을 수 있다.

### 캐시 워밍

대규모 배포 직후 캐시가 비어 있는 상태로 트래픽이 몰리면 Origin이 부담을 받는다. 미리 주요 URL에 HEAD 요청을 날려서 캐시를 채우는 워밍 스크립트를 자주 쓴다.

```bash
# 인기 URL 목록을 미리 워밍
cat top-urls.txt | xargs -P 50 -I {} curl -s -o /dev/null -I "https://cdn.example.com{}"
```

PoP이 수백 개라서 한 곳에서 워밍해도 다른 PoP은 캐시가 비어 있다는 점을 기억해야 한다. 완벽한 워밍은 어렵고, 보통은 인기 PoP 몇 개에 대해 분산 워밍을 돌린다. AWS의 경우 Lambda를 여러 리전에서 실행해서 각 리전 PoP에 워밍을 날리는 식으로 한다.

## 운영 중에 부딪히는 함정

마지막으로 실무에서 자주 겪는 사례 몇 개.

### CORS 헤더 누락

`Access-Control-Allow-Origin` 헤더가 응답에 없는 상태로 캐싱되면, 이후 다른 Origin에서 요청해도 CDN이 캐시된 응답(헤더 없는)을 그대로 돌려준다. CORS 헤더는 Origin이 요청 헤더(`Origin`)를 보고 동적으로 결정해야 하는데, 캐시되면 그게 깨진다.

해결책: `Vary: Origin`을 응답에 포함시키거나, 와일드카드(`*`)로 설정해서 모든 요청에 동일하게 응답하게 한다. 후자가 더 안전하다.

### 압축 응답과 Accept-Encoding

대부분 CDN은 자체적으로 압축을 처리하지만, Origin이 이미 압축된 응답을 보내면 그 압축 방식이 캐싱된다. 클라이언트가 `Accept-Encoding: br`를 보내도 캐시에 `gzip`만 있으면 `gzip`이 응답된다.

Origin은 가급적 압축하지 않은 응답을 보내고 CDN이 알아서 압축하게 두거나, `Vary: Accept-Encoding`을 정확히 보내야 한다.

### Origin Failover

Origin이 죽으면 CDN도 5xx를 그대로 사용자에게 돌려준다. 5xx 응답이 캐시되면 더 큰 문제가 된다. 기본적으로 5xx는 캐시하지 않지만, `Cache-Control`로 짧게(예: 10초) 캐싱하면 Origin 장애 시 트래픽 폭주를 막을 수 있다.

CloudFront는 Origin Failover로 secondary origin을 지정할 수 있다. 한 곳이 5xx면 자동으로 다른 곳으로 라우팅한다. Cloudflare는 Load Balancer로 비슷하게 구성한다. Fastly는 VCL에서 backend 분기 로직을 직접 짠다.

### 캐시된 리다이렉트

`Location` 헤더가 있는 301/302 응답도 캐싱된다. 잘못된 리다이렉트 응답이 캐싱되면 무한 루프나 잘못된 페이지로 사용자가 계속 보내진다. 리다이렉트 응답은 짧은 TTL(`max-age=60`)로 캐싱하거나, 도메인 마이그레이션 같은 중요한 변경 직후에는 의도적으로 무효화한다.

### 모니터링 지표

운영 중인 CDN에서 매일 봐야 하는 지표:

- 캐시 히트율(전체, URL 패턴별)
- Origin 트래픽 (CDN에서 못 막은 트래픽)
- 4xx, 5xx 비율 (Origin 장애나 잘못된 캐시 키 신호)
- PoP별 응답 시간 (특정 지역만 느린지 확인)
- 무효화 API 호출 빈도와 비용

CloudFront는 CloudWatch Metrics, Cloudflare는 Analytics 탭, Fastly는 Real-time Stats에서 다 볼 수 있다. 직접 운영하는 메트릭 시스템(Datadog, Grafana)에 CDN 메트릭을 import해두면 다른 시스템과 같이 추적할 수 있어서 편하다.
