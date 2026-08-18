---
title: AWS CloudFront — CDN & 캐싱 이해
tags: [aws, cdn, cache, network]
updated: 2026-08-18
---

# AWS CloudFront

CloudFront는 전 세계 POP(Point of Presence) 서버에 콘텐츠를 캐싱해 가까운 곳에서 전달하는 AWS CDN 서비스다.

---

## 작동 흐름

```
사용자 → Edge Location (캐시 확인)
      ├ 히트(HIT): 캐시된 콘텐츠 즉시 반환
      └ 미스(MISS): Origin으로 요청 전달 → 캐싱 후 사용자에게 응답
```

첫 요청 시 Origin에서 받아온 응답을 POP 디스크에 저장한다. 이후 요청은 TTL이 남아있는 동안 Origin 없이 응답한다. TTL 만료 또는 Invalidation이 발생하면 다음 요청에서 Origin을 다시 호출한다.

응답 헤더에서 `X-Cache`로 히트 여부를 바로 확인할 수 있다.

```
X-Cache: Hit from cloudfront    # 캐시 히트
X-Cache: Miss from cloudfront   # 캐시 미스, Origin 호출
X-Cache: RefreshHit from cloudfront  # TTL 만료 후 Origin 재검증 통과 (304)
```

---

## Cache Policy 실제 설정

Cache Policy는 두 가지를 정의한다: 캐시 키 구성과 TTL.

### TTL 우선순위

| 조건 | 적용되는 TTL |
|------|-------------|
| Origin이 `Cache-Control: max-age=N` 반환 | min(N, Max TTL) |
| Origin이 `Cache-Control: s-maxage=N` 반환 | min(N, Max TTL) (CDN 전용 지시어, max-age보다 우선) |
| Origin이 Cache-Control 헤더 없음 | Default TTL |
| Origin이 `Cache-Control: no-cache` | Min TTL 적용 |

Cache Policy의 Max TTL이 Origin 헤더보다 강제 제한이다. Origin이 `max-age=86400`을 보내도 Max TTL이 3600이면 3600초 후에 재검증한다.

### AWS CLI로 커스텀 Cache Policy 생성

```bash
aws cloudfront create-cache-policy \
  --cache-policy-config '{
    "Name": "ProductsAPIPolicy",
    "DefaultTTL": 3600,
    "MinTTL": 0,
    "MaxTTL": 86400,
    "ParametersInCacheKeyAndForwardedToOrigin": {
      "EnableAcceptEncodingGzip": true,
      "EnableAcceptEncodingBrotli": true,
      "HeadersConfig": {
        "HeaderBehavior": "none"
      },
      "CookiesConfig": {
        "CookieBehavior": "none"
      },
      "QueryStringsConfig": {
        "QueryStringBehavior": "whitelist",
        "QueryStrings": {
          "Quantity": 2,
          "Items": ["page", "limit"]
        }
      }
    }
  }'
```

AWS 관리 콘솔에서는 CloudFront → Policies → Cache → Create cache policy 경로로 동일한 설정을 GUI로 만들 수 있다.

### 기본 제공 정책

`CachingDisabled` — 모든 요청을 Origin으로 전달한다. 동적 API, 인증 필요 엔드포인트에 쓴다.

`CachingOptimized` — 쿼리 스트링, 헤더, 쿠키를 캐시 키에서 제외한다. URL 경로만으로 캐시를 구분하므로 정적 파일에 적합하다.

`CachingOptimizedForUncompressedObjects` — gzip/brotli 협상 없이 캐시한다. 이미 압축된 파일(jpg, mp4 등)에 쓴다.

---

## Cache-Control 헤더 동작 방식

Origin 서버가 내려보내는 `Cache-Control` 헤더가 CloudFront 동작에 영향을 준다. 헤더 종류별로 동작이 다르다.

```
Cache-Control: public, max-age=3600
  → CloudFront 캐시 O, 브라우저 캐시 O (1시간)

Cache-Control: private, max-age=300
  → CloudFront 캐시 X, 브라우저 캐시 O (5분)

Cache-Control: no-cache
  → 저장은 하되 매번 Origin에 재검증 요청 (ETag 활용)
  → CloudFront는 Min TTL만큼 캐시 후 재검증

Cache-Control: no-store
  → CloudFront 캐시 X, 브라우저 캐시 X

Cache-Control: s-maxage=7200, max-age=3600
  → CloudFront 2시간 캐시, 브라우저 1시간 캐시
  → s-maxage는 CDN(공유 캐시) 전용. 브라우저는 max-age를 본다
```

`s-maxage`는 CDN에만 적용되는 지시어라 브라우저와 CDN의 TTL을 다르게 가져가야 할 때 유용하다. API 응답을 CDN에서 10분 캐시하면서 브라우저에는 30초만 캐시하려면 `s-maxage=600, max-age=30`으로 설정한다.

`ETag`와 `If-None-Match`를 함께 쓰면 콘텐츠가 바뀌지 않았을 때 304 응답으로 데이터 전송을 줄인다. CloudFront는 304를 받으면 캐시의 TTL을 갱신하고 기존 데이터를 계속 서빙한다.

---

## Origin Request Policy

Cache Policy와 별개로 Origin Request Policy가 있다. Cache Policy는 캐시 키를 정의하고, Origin Request Policy는 Origin에 전달할 헤더·쿠키·쿼리 스트링을 정의한다.

캐시 키에는 포함하지 않지만 Origin에는 전달해야 하는 경우에 쓴다.

```
사용자 요청: Accept-Language: ko-KR, User-Agent: Mozilla/...

Cache Policy:    캐시 키 = URL + page 파라미터만
Origin Request Policy: Accept-Language, CloudFront-Viewer-Country 전달
```

이 구성에서 CloudFront는 URL + page 파라미터 조합으로 캐시를 찾는다. 캐시 미스 시 Origin에는 Accept-Language와 CloudFront-Viewer-Country 헤더까지 붙여 전달한다.

### AWS CLI로 Origin Request Policy 생성

```bash
aws cloudfront create-origin-request-policy \
  --origin-request-policy-config '{
    "Name": "ForwardLanguage",
    "HeadersConfig": {
      "HeaderBehavior": "whitelist",
      "Headers": {
        "Quantity": 2,
        "Items": ["Accept-Language", "CloudFront-Viewer-Country"]
      }
    },
    "CookiesConfig": {
      "CookieBehavior": "none"
    },
    "QueryStringsConfig": {
      "QueryStringBehavior": "all"
    }
  }'
```

### 기본 제공 정책

`AllViewer` — 사용자의 모든 헤더, 쿠키, 쿼리 스트링을 그대로 Origin에 전달한다.

`AllViewerExceptHostHeader` — Host 헤더만 빼고 전달한다. Origin이 CloudFront 도메인 대신 원래 도메인 헤더가 필요한 경우에 쓴다.

`CORS-S3Origin` — S3 Origin에 CORS 관련 헤더를 전달한다.

주의할 점은 Origin Request Policy에 캐시 키에 없는 헤더를 넣어도 히트율에 영향을 주지 않는다는 것이다. 캐시 키는 Cache Policy만 결정한다. Origin Request Policy는 캐시 미스 때 Origin에 뭘 보낼지만 제어한다.

---

## 캐시 키 설계와 히트율

캐시 키에 무엇을 포함하는지가 히트율을 결정한다. 키가 복잡할수록 같은 캐시를 재사용하는 요청이 줄어든다.

### 쿼리 스트링 순서 문제

CloudFront는 캐시 키를 문자열 비교로 처리한다. `?page=1&limit=10`과 `?limit=10&page=1`은 다른 캐시 키다.

```
GET /api/products?page=1&limit=10&sort=price   (캐시 키 A)
GET /api/products?sort=price&page=1&limit=10   (캐시 키 B — 미스)
GET /api/products?limit=10&sort=price&page=1   (캐시 키 C — 미스)
```

세 요청 모두 동일한 Origin 응답을 받지만 CloudFront에서는 세 번의 Origin 요청이 발생한다.

Cache Policy에서 Query strings를 `All`로 설정하고 `Sort query strings`를 활성화하면 CloudFront가 쿼리 파라미터를 알파벳순으로 정렬한 뒤 캐시 키를 만들어 순서에 관계없이 동일 캐시로 처리한다.

### 경로별 정책 분리

단일 CloudFront 배포에서 경로마다 다른 Cache Policy를 적용하는 것이 일반적인 구성이다.

```
Path Pattern: /static/*
  Cache Policy: CachingOptimized (TTL: 86400초)

Path Pattern: /api/products/*
  Cache Policy: Custom (쿼리스트링 포함, TTL: 3600초)

Path Pattern: /api/user/*
  Cache Policy: CachingDisabled

Path Pattern: /api/stats/*
  Cache Policy: Custom (TTL: 300초)
```

Default(`*`) Behavior가 가장 낮은 우선순위다. 명시적 경로 패턴이 먼저 매칭된다.

---

## Authorization 헤더와 캐시 — 데이터 혼용 사고

Authorization 헤더가 있는 응답에 `Cache-Control: public, max-age=3600`을 붙이면 CloudFront가 그 응답을 캐시에 저장한다. 이 상태에서 다른 사용자가 같은 URL로 요청하면 첫 번째 사용자의 응답이 그대로 반환된다.

```
GET /api/cart
Authorization: Bearer <user-A-token>
→ Cache-Control: public, max-age=300  ← Origin 실수
→ CloudFront가 캐시 저장

GET /api/cart
Authorization: Bearer <user-B-token>
→ Cache Key: /api/cart (Authorization 미포함)
→ user-A의 장바구니 데이터 반환
```

방어법은 두 가지다.

첫째, Origin에서 사용자별 데이터를 반환하는 엔드포인트에는 `Cache-Control: private, no-store`를 명시한다. CloudFront는 `private` 또는 `no-store`가 붙은 응답을 캐시하지 않는다.

둘째, CloudFront Behavior에서 해당 경로(`/api/user/*`, `/api/cart/*`)에 `CachingDisabled` 정책을 적용한다. Origin의 헤더 설정과 무관하게 캐시가 동작하지 않는다.

Origin 서버가 Cache-Control을 제대로 내려보낸다 해도, 미들웨어나 프레임워크 기본 설정이 `public`을 붙이는 경우가 있다. 두 방어선을 모두 쓰는 편이 안전하다.

---

## Invalidation — 비용과 주의사항

데이터가 바뀌었는데 TTL이 남아있을 때 강제로 캐시를 삭제한다.

```bash
# 전체 무효화
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"

# 특정 경로만
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/api/products/*" "/images/banner.jpg"
```

### 비용 구조

월 1,000 invalidation path까지 무료다. 이후 path당 $0.005다.

`/*`는 와일드카드 하나지만 path 1건으로 계산한다. `/images/*`와 `/api/*`를 별도로 넣으면 2건이다. 와일드카드를 쓰면 건수를 줄일 수 있다.

주의할 점은 와일드카드(`*`)가 단일 경로 레벨에서만 동작한다는 것이다. `/api/*`는 `/api/products/list`는 무효화하지만 `/api/v2/products/list`는 무효화하지 않는다. 경로 구조가 깊으면 `/*`로 전체 무효화가 필요할 수 있다.

### 전파 시간

Invalidation은 요청 즉시 적용되지 않는다. 전 세계 POP에 전파되는 데 통상 10초~2분이 걸린다. `aws cloudfront wait invalidation-completed` 명령으로 완료를 기다릴 수 있다.

```bash
aws cloudfront wait invalidation-completed \
  --distribution-id E1234567890 \
  --id INVALIDATION_ID
```

### Invalidation 대신 버전 URL

정적 파일에는 빌드 시 파일명에 해시를 넣어(`main.a3f1c2.js`) Invalidation 없이 캐시를 갱신하는 방법을 쓴다. URL이 바뀌면 자동으로 새 캐시가 생기고 이전 파일은 TTL까지 유지된다.

배포를 자주 하는 프론트엔드 빌드라면 Invalidation 비용과 전파 지연을 피하면서 즉각적인 캐시 갱신이 가능하다.

동적 데이터(API 응답)는 버전 URL 방식을 쓰기 어렵기 때문에 애초에 짧은 TTL을 설정하거나 Invalidation을 쓴다.

---

## 캐시 히트율 측정과 트러블슈팅

### CloudWatch 메트릭

CloudFront 배포당 CloudWatch에 `CacheHitRate` 메트릭이 쌓인다.

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=E1234567890 \
              Name=Region,Value=Global \
  --start-time 2026-08-18T00:00:00Z \
  --end-time 2026-08-18T23:59:00Z \
  --period 3600 \
  --statistics Average
```

히트율이 갑자기 내려가는 경우 확인할 것들:

**캐시 키에 불필요한 값이 포함된 경우** — 헤더 하나가 캐시 키에 들어가면 그 헤더 값이 다른 모든 요청이 별도 캐시를 만든다. Cache Policy에서 헤더 구성을 점검한다.

**쿼리 스트링 정렬 미적용** — 위에서 설명한 순서 문제다. CloudFront Access Log에서 `cs-uri-query` 필드를 보면 실제로 어떤 쿼리 스트링이 캐시 키로 들어갔는지 확인된다.

**TTL이 너무 짧은 경우** — 로그에서 `RefreshHit`와 `Miss` 비율을 보면 TTL 만료 빈도를 알 수 있다.

**배포 직후 히트율 급락** — Cache Policy를 변경하면 기존 캐시 키와 새 캐시 키가 달라져 한동안 전부 미스가 난다. 의도된 현상이므로 시간이 지나면 회복된다.

### Access Log 활성화

S3 버킷에 접근 로그를 남기면 `x-edge-result-type` 필드로 히트/미스를 분석할 수 있다.

```bash
aws cloudfront update-distribution \
  --id E1234567890 \
  --distribution-config '{
    "Logging": {
      "Enabled": true,
      "Bucket": "my-cf-logs.s3.amazonaws.com",
      "Prefix": "cloudfront/"
    }
  }'
```

`x-edge-result-type` 값:

| 값 | 의미 |
|----|------|
| `Hit` | 캐시 히트 |
| `Miss` | 캐시 미스, Origin 호출 |
| `RefreshHit` | TTL 만료 후 Origin 재검증 통과 |
| `Error` | Origin 오류 |
| `LimitExceeded` | 요청 한도 초과 |

### Origin Shield

Origin Shield는 POP와 Origin 사이에 추가 캐시 계층을 넣는다. 여러 리전의 POP에서 미스가 나더라도 Origin Shield에서 히트나면 Origin 호출이 줄어든다. Origin이 단일 리전에 있을 때 글로벌 트래픽을 받는 경우에 효과적이다.

```bash
# Origin 설정에서 Origin Shield 활성화
"OriginShield": {
  "Enabled": true,
  "OriginShieldRegion": "ap-northeast-2"
}
```

Origin Shield 추가 비용이 발생하므로 Origin 부하가 병목인 경우에만 켠다.

---

## Origin 유형

| Origin | 용도 |
|--------|------|
| S3 | 정적 웹사이트, 이미지, 빌드 산출물 |
| ALB | 백엔드 API, 서버 기반 웹서비스 |
| EC2 | 커스텀 서버 직접 연결 |
| API Gateway | Lambda 기반 서버리스 API |

---

## SSL 및 커스텀 도메인

HTTPS를 쓰려면 ACM 인증서가 필요하다. CloudFront용 인증서는 반드시 `us-east-1` 리전에서 발급해야 한다.

```bash
aws acm request-certificate \
  --domain-name "cdn.example.com" \
  --validation-method DNS \
  --region us-east-1
```

DNS 설정:

```
cdn.example.com   A(ALIAS)   d1234abcd.cloudfront.net
```

---

## 비용 구조

| 항목 | 과금 기준 |
|------|-----------|
| Data Transfer Out | POP에서 사용자로 나가는 데이터량 |
| Requests | CDN 요청 수 |
| Invalidation | 1,000 path/월 무료, 이후 path당 $0.005 |
| Origin Shield | 추가 캐시 계층 사용 시 별도 과금 |

캐시 히트 시에는 Origin 요청 비용이 발생하지 않는다. 히트율이 높을수록 Origin 인프라 비용이 줄어든다.
