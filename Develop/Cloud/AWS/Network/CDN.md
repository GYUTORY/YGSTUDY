---
title: AWS CloudFront — CDN & 캐싱 이해
tags: [aws, cdn, cache, network]
updated: 2026-08-17
---

# AWS CloudFront

CloudFront는 Amazon Web Services가 제공하는 글로벌 CDN(Content Delivery Network) 서비스다.
정적/동적 콘텐츠, 미디어, API를 전 세계 POP(Point of Presence) 서버에 캐싱해 가까운 곳에서 전달한다.

---

## 핵심 개념

| 키워드 | 설명 |
|--------|------|
| CDN | 전 세계에 분산된 POP 서버가 콘텐츠를 캐싱하여 가까운 곳에서 전달 |
| Origin | 콘텐츠 원본 저장 위치 — S3, ALB, EC2, API Gateway, Custom HTTP 서버 등 |
| Edge Location | 사용자 근처의 CDN 캐싱 서버 — 요청이 가장 가까운 POP으로 라우팅 |
| Cache Key | 어떤 요청을 동일 캐시로 판단할지 결정하는 값 (URL + 쿼리스트링 + 헤더 + 쿠키 조합) |

---

## 작동 흐름

```
사용자 → Edge Location (캐시 확인)
      ├ 히트(HIT): 캐시된 콘텐츠 즉시 반환
      └ 미스(MISS): Origin으로 요청 전달 → 캐싱 후 사용자에게 응답
```

첫 요청 시 Origin에서 받아온 응답을 POP 디스크에 저장한다. 이후 요청은 TTL이 남아있는 동안 Origin 없이 응답한다. TTL 만료 또는 Invalidation이 발생하면 다음 요청에서 Origin을 다시 호출한다.

---

## Cache Policy와 Cache Key

Cache Policy는 두 가지를 정의한다: 캐시 키 구성과 TTL.

캐시 키에 무엇을 포함하는지가 히트율을 결정한다. 키가 복잡할수록 같은 캐시를 재사용하는 요청이 줄어든다.

TTL 설정 항목:

- 최소 TTL: 캐시 최소 유지 시간
- 최대 TTL: 캐시 최대 유지 시간
- 기본 TTL: Origin에서 Cache-Control 헤더가 없을 때 사용

AWS가 제공하는 기본 정책:

`CachingDisabled` — 모든 요청을 Origin으로 전달한다. 동적 API, 인증이 필요한 엔드포인트에 쓴다.

`CachingOptimized` — 쿼리 스트링, 헤더, 쿠키를 캐시 키에서 제외한다. URL 경로만으로 캐시를 구분하므로 정적 파일에 적합하다.

커스텀 정책을 만들면 쿼리 스트링 일부만, 또는 특정 헤더만 캐시 키에 포함할 수 있다.

---

## Authorization 헤더와 캐시 — 데이터 혼용 사고

Authorization 헤더가 있는 응답에 `Cache-Control: public, max-age=3600`을 붙이면 CloudFront가 그 응답을 캐시에 저장한다. 이 상태에서 다른 사용자가 같은 URL로 요청하면 첫 번째 사용자의 응답이 그대로 반환된다.

장바구니 API, 주문 내역 API 같은 곳에서 Origin 서버가 응답에 `public` 캐시를 달아두면 CloudFront는 Cache Key에 Authorization이 없는 한 사용자를 구분하지 않는다.

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

```
Cache-Control: private, no-store
```

둘째, CloudFront Behavior에서 해당 경로(`/api/user/*`, `/api/cart/*`)에 `CachingDisabled` 정책을 적용한다. Origin의 헤더 설정과 무관하게 캐시가 동작하지 않는다.

Origin 서버가 Cache-Control을 제대로 내려보낸다 해도, 미들웨어나 프레임워크 기본 설정이 `public`을 붙이는 경우가 있다. 두 방어선을 모두 쓰는 편이 안전하다.

---

## 쿼리 스트링 순서와 캐시 히트율

CloudFront는 캐시 키를 문자열 비교로 처리한다. `?page=1&limit=10`과 `?limit=10&page=1`은 다른 캐시 키다.

프론트엔드에서 API 요청을 만들 때 쿼리 스트링 순서가 호출 경로마다 달라지면 캐시 히트율이 급격히 낮아진다.

```
GET /api/products?page=1&limit=10&sort=price   (캐시 키 A)
GET /api/products?sort=price&page=1&limit=10   (캐시 키 B — 미스)
GET /api/products?limit=10&sort=price&page=1   (캐시 키 C — 미스)
```

세 요청 모두 동일한 Origin 응답을 받지만 CloudFront에서는 세 번의 Origin 요청이 발생한다.

CloudFront Cache Policy에서 쿼리 스트링을 `All` + `Sort query strings` 조합으로 설정하면 해결된다. CloudFront가 쿼리 파라미터를 알파벳순으로 정렬한 뒤 캐시 키를 만들어 순서에 관계없이 동일 캐시로 처리한다.

커스텀 Cache Policy 설정 위치: `Query strings` → `All` 선택 후 `Sort query strings` 활성화.

이미 운영 중인 배포라면 Cache Policy 변경 후 CloudWatch의 `CacheHitRate` 메트릭을 확인한다. 변경 직후 기존 캐시가 유효하지 않아 히트율이 일시적으로 내려갈 수 있다.

---

## 경로별 캐싱 정책 분리

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

## Origin에서 캐시 제어

Origin 서버가 내려보내는 `Cache-Control` 헤더가 CloudFront 동작에 영향을 준다. Cache Policy의 TTL 범위 안에서 Origin 헤더가 우선한다.

```
Cache-Control: public, max-age=3600   # 1시간 캐시, CDN 포함
Cache-Control: private, max-age=300   # 브라우저만 캐시, CDN은 캐시 안 함
Cache-Control: no-cache               # 재검증 후 사용
Cache-Control: no-store               # 캐시에 저장 자체를 금지
```

`ETag`와 `If-None-Match`를 함께 쓰면 콘텐츠가 바뀌지 않았을 때 304 응답으로 데이터 전송을 줄인다.

---

## 캐시 무효화 (Invalidation)

데이터가 바뀌었는데 TTL이 남아있을 때 강제로 캐시를 삭제한다.

```bash
# 전체 무효화
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"

# 특정 경로만
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/api/products/*"
```

월 1,000건까지 무료, 이후 건당 $0.005다. 정적 파일에는 빌드 시 파일명에 해시를 넣어(`main.[hash].js`) Invalidation 없이 캐시를 갱신하는 방법을 쓴다.

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
| Invalidation | 1,000건/월 무료, 이후 건당 $0.005 |

캐시 히트 시에는 Origin 요청 비용이 발생하지 않는다. 히트율이 높을수록 Origin 인프라 비용이 줄어든다.
