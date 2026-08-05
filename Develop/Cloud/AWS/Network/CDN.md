---
title: AWS CloudFront — CDN & 캐싱 이해
tags: [aws, cloudfront, cdn, edge, caching, networking]
updated: 2026-01-15
---

# AWS CloudFront

CloudFront는 Amazon Web Services가 제공하는 글로벌 CDN(Content Delivery Network) 서비스로,  
정적/동적 콘텐츠, 미디어, API를 전 세계 사용자에게 더 빠르고 안전하게 전달한다.

---

## CloudFront 핵심 개념

| 키워드 | 설명 |
|--------|------|
| CDN | 전 세계에 분산된 POP(Point of Presence) 서버가 콘텐츠를 캐싱하여 가까운 곳에서 전달 |
| Origin | 콘텐츠 원본 저장 위치 — S3, ALB, EC2, API Gateway, Custom HTTP 서버 등 |
| Edge Location | 사용자 근처의 CDN 캐싱 서버 — 요청이 가장 가까운 POP으로 라우팅 |
| POP 캐시 | Origin에서 받아온 콘텐츠를 일정 기간 저장하여 재사용하는 저장 공간 |

---

## CloudFront 작동 흐름

```
사용자 → Edge Location (캐시 확인)
      ├ 히트(HIT): 캐시된 콘텐츠 즉시 반환
      └ 미스(MISS): Origin으로 요청 전달 → 캐싱 후 사용자에게 응답
```

CloudFront가 캐싱할 수 있는 주요 콘텐츠:
- 이미지, JS/CSS, HTML 파일
- 정적 웹사이트 (React build 파일)
- S3 Object
- 동적 API 응답 (단, 조건부 캐싱 필요)

---

## CloudFront 배포 구성 (Distribution)

CloudFront를 사용하려면 배포(Distribution)를 생성해야 한다.

| 구성 항목 | 설명 |
|----------|------|
| Origin | 콘텐츠 원본 (S3 / ALB / API Gateway / Custom Server) |
| Behaviors | 캐시 정책, 경로 매핑, GET/POST 허용 설정 |
| SSL 인증서 | ACM 인증서 적용, HTTPS 도메인 설정 |
| Domain (Alternate Domain Name) | `cdn.yourdomain.com` 같은 커스텀 URL 사용 |

---

## Edge Location 캐싱 방식

CloudFront는 전 세계 POP 서버 내 디스크에 캐싱한다.

CDN이 S3/Origin의 파일을 미리 가져오는 것이 아니라,  
처음 요청 시 Origin에서 가져온 뒤 POP 디스크에 저장하고 이후 요청에 재사용한다.

캐싱 저장 위치:
- Edge Location 내 디스크 기반 스토리지
- TTL 만료 시 삭제되며, 자주 요청되지 않는 항목은 자동 제거

---

## 캐시 제어 옵션 (Cache Key & TTL)

| 항목 | 설명 |
|------|------|
| TTL (Time-To-Live) | 캐시 유효 시간 |
| Cache Key | 어떤 요청을 동일한 캐시로 간주할지 결정하는 키(QueryString/Headers/Cookies 포함 여부) |
| Cache Policy | API 캐싱 조건 및 캐시 키 정책 정의 가능 |

예: GET만 캐싱 & POST는 항상 Origin으로 요청  
→ CloudFront는 기본적으로 GET, HEAD만 캐싱하고 POST는 캐싱하지 않는다.

## API 응답 캐싱

### API 캐싱의 필요성

API 응답을 캐싱하면 원본 서버 부하를 줄이고 응답 속도를 개선할 수 있다.

**캐싱의 장점:**
- 원본 서버 부하 감소
- 응답 지연 시간 감소
- 데이터 전송 비용 절감
- 사용자 경험 개선

**캐싱이 적합한 API:**
- 자주 변경되지 않는 데이터 (제품 목록, 설정 정보)
- 조회가 많은 API (인기 상품, 통계)
- 계산 비용이 높은 API (집계, 분석)
- 외부 API 프록시 (제3자 API 응답 캐싱)

**캐싱이 부적합한 API:**
- 실시간 데이터 (주식 가격, 채팅)
- 사용자별 개인화 데이터 (주문 내역, 장바구니)
- 자주 변경되는 데이터 (재고 수량)
- POST/PUT/DELETE 요청

### CloudFront API 캐싱 동작 원리

**기본 동작:**
```
1. 사용자가 API 요청 (GET /api/products)
2. CloudFront Edge Location에서 캐시 확인
3. 캐시 히트: 캐시된 응답 즉시 반환
4. 캐시 미스: Origin(API Gateway/ALB)으로 요청
5. Origin 응답을 캐시에 저장
6. 사용자에게 응답 반환
```

**캐시 키 생성:**
- URL 경로
- 쿼리 스트링 (설정에 따라)
- 헤더 (설정에 따라)
- 쿠키 (설정에 따라)

**예시:**
- `GET /api/products?page=1` → 캐시 키: `/api/products?page=1`
- `GET /api/products?page=2` → 캐시 키: `/api/products?page=2` (다른 캐시)

### Cache Policy 설정

Cache Policy는 캐시 키와 TTL을 정의한다.

**주요 설정 항목:**

**1. TTL (Time-To-Live):**
- 최소 TTL: 캐시 최소 유지 시간
- 최대 TTL: 캐시 최대 유지 시간
- 기본 TTL: Origin에서 Cache-Control 헤더가 없을 때 사용

**2. Cache Key 구성:**
- 쿼리 스트링 포함 여부
- 헤더 포함 여부
- 쿠키 포함 여부

**3. 기본 Cache Policy:**

**CachingDisabled:**
- 캐싱 비활성화
- 모든 요청을 Origin으로 전달
- 동적 API에 사용

**CachingOptimized:**
- 최적화된 캐싱
- 쿼리 스트링, 헤더, 쿠키 무시
- 정적 콘텐츠에 적합

**CachingOptimizedForUncompressedObjects:**
- 압축되지 않은 객체 최적화
- Accept-Encoding 헤더 포함

**ElementalMediaPackage:**
- 미디어 스트리밍용

**4. 커스텀 Cache Policy 생성:**

**예시: 쿼리 스트링 기반 캐싱:**
```
Cache Key:
  - URL 경로: 포함
  - 쿼리 스트링: 포함 (모든 쿼리 스트링)
  - 헤더: 제외
  - 쿠키: 제외

TTL:
  - 최소: 1초
  - 최대: 86400초 (24시간)
  - 기본: 3600초 (1시간)
```

**예시: 헤더 기반 캐싱:**
```
Cache Key:
  - URL 경로: 포함
  - 쿼리 스트링: 포함
  - 헤더: Accept-Language 포함 (다국어 지원)
  - 쿠키: 제외
```

### Origin Request Policy 설정

Origin Request Policy는 Origin으로 전달되는 요청을 제어한다.

**주요 설정:**
- 헤더 포함/제외
- 쿼리 스트링 포함/제외
- 쿠키 포함/제외

**사용 사례:**
- Authorization 헤더는 Origin에만 전달 (캐시 키에는 포함 안 함)
- 특정 헤더만 Origin에 전달해 Origin 부하 감소

### API 캐싱 구현 방법

#### 방법 1: 기본 Cache Policy 사용

**CachingOptimized Policy:**
- 쿼리 스트링, 헤더 무시
- URL 경로만으로 캐시 키 생성
- 정적 API 응답에 적합

**예시:**
```
GET /api/products
GET /api/products?page=1  (같은 캐시 사용)
GET /api/products?page=2  (같은 캐시 사용)
```

#### 방법 2: 쿼리 스트링 기반 캐싱

**커스텀 Cache Policy:**
- 쿼리 스트링을 캐시 키에 포함
- 페이지네이션, 필터링 API에 적합

**예시:**
```
GET /api/products?page=1&limit=10  (캐시 키 1)
GET /api/products?page=2&limit=10  (캐시 키 2)
GET /api/products?category=electronics  (캐시 키 3)
```

**구현:**
1. Cache Policy 생성
2. 쿼리 스트링: "Include all" 선택
3. Behavior에 Policy 적용

#### 방법 3: 헤더 기반 캐싱

**커스텀 Cache Policy:**
- Accept-Language 헤더 포함
- 다국어 API 응답 캐싱

**예시:**
```
GET /api/products
  Header: Accept-Language: ko-KR  (캐시 키 1)

GET /api/products
  Header: Accept-Language: en-US  (캐시 키 2)
```

**구현:**
1. Cache Policy 생성
2. 헤더: "Include specified headers" 선택
3. Accept-Language 헤더 추가
4. Behavior에 Policy 적용

#### 방법 4: 경로별 다른 캐싱 정책

**Behavior 설정:**
- 경로 패턴별로 다른 Cache Policy 적용
- 정적 API와 동적 API 구분

**예시:**
```
Path Pattern: /api/products/*
  Cache Policy: CachingOptimized (TTL: 1시간)

Path Pattern: /api/user/*
  Cache Policy: CachingDisabled (캐싱 안 함)

Path Pattern: /api/stats/*
  Cache Policy: Custom (TTL: 5분)
```

**구현:**
1. 여러 Behavior 생성
2. 경로 패턴 지정
3. 각 Behavior에 다른 Cache Policy 적용

### Origin에서 캐시 제어

Origin 서버에서 HTTP 헤더로 캐시를 제어할 수 있다.

**Cache-Control 헤더:**

**캐싱 허용:**
```
Cache-Control: public, max-age=3600
```
- public: 공개 캐시 가능
- max-age=3600: 3600초(1시간) 캐시

**캐싱 금지:**
```
Cache-Control: no-cache
```
- 캐시하지 않음

**조건부 캐싱:**
```
Cache-Control: private, max-age=300
```
- private: 브라우저만 캐시, CDN은 캐시 안 함

**ETag 활용:**
```
ETag: "abc123"
If-None-Match: "abc123"
```
- ETag가 같으면 304 Not Modified 반환
- 데이터 전송량 절감

### API 캐싱 활용 시나리오

#### 시나리오 1: 제품 목록 API 캐싱

**요구사항:**
- 제품 목록은 자주 변경되지 않음
- 페이지네이션 지원
- 1시간 캐시

**구현:**
```
Cache Policy:
  - 쿼리 스트링: 포함 (page, limit)
  - TTL: 최소 1초, 최대 3600초, 기본 3600초

Behavior:
  - Path: /api/products/*
  - Cache Policy: 위에서 생성한 Policy
```

**결과:**
- `/api/products?page=1` → 1시간 캐시
- `/api/products?page=2` → 별도 캐시
- Origin 부하 감소

#### 시나리오 2: 다국어 API 캐싱

**요구사항:**
- 언어별로 다른 응답
- Accept-Language 헤더 기반 캐싱

**구현:**
```
Cache Policy:
  - 헤더: Accept-Language 포함
  - TTL: 1시간

Origin Request Policy:
  - 헤더: Accept-Language 포함 (Origin에 전달)
```

**결과:**
- 한국어 요청과 영어 요청이 별도 캐시
- 각 언어별로 최적화된 응답 제공

#### 시나리오 3: 통계 API 캐싱

**요구사항:**
- 통계는 5분마다 업데이트
- 짧은 TTL 필요

**구현:**
```
Cache Policy:
  - TTL: 최소 1초, 최대 300초, 기본 300초

Behavior:
  - Path: /api/stats/*
  - Cache Policy: 위에서 생성한 Policy
```

**결과:**
- 5분간 캐시된 응답 제공
- Origin 부하 감소
- 최신성 유지

#### 시나리오 4: 사용자별 API는 캐싱 안 함

**요구사항:**
- 사용자별 데이터는 캐싱하면 안 됨
- Authorization 헤더로 구분

**구현:**
```
Cache Policy:
  - CachingDisabled 사용

또는

Cache Policy:
  - 헤더: Authorization 포함
  - TTL: 0초 (캐싱 안 함)
```

**결과:**
- 모든 요청이 Origin으로 전달
- 사용자별 개인화 데이터 보장

### 캐시 무효화 (Invalidation)

캐시를 강제로 삭제해야 할 때 Invalidation을 사용한다.

**사용 시나리오:**
- 데이터가 업데이트되었을 때
- 긴급한 변경사항 반영
- 테스트 중 캐시 클리어

**방법:**

**1. 전체 캐시 무효화:**
```bash
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"
```

**2. 특정 경로 무효화:**
```bash
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/api/products/*"
```

**3. 특정 파일 무효화:**
```bash
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/api/products/123"
```

**비용:**
- 처음 1,000건/월: 무료
- 이후: $0.005/건

**주의사항:**
- Invalidation은 비용이 발생한다
- 너무 자주 사용하지 않는다
- 버전 관리로 대체하는 것이 좋다 (예: `/api/v1/products`, `/api/v2/products`)

### API 캐싱 모니터링

**CloudWatch 메트릭:**
- Cache Hit Rate: 캐시 적중률
- Requests: 총 요청 수
- Origin Requests: Origin으로 전달된 요청 수
- Data Transfer: 데이터 전송량

**캐시 적중률 계산:**
```
Cache Hit Rate = (Total Requests - Origin Requests) / Total Requests × 100
```

**목표:**
- 정적 API: 80% 이상
- 동적 API: 50% 이상

### API 캐싱 주의사항

**1. 데이터 일관성:**
- TTL이 길면 오래된 데이터를 제공할 수 있음
- 중요 데이터는 짧은 TTL 사용
- Invalidation으로 즉시 반영

**2. 사용자별 데이터:**
- Authorization 헤더를 캐시 키에 포함하면 사용자별 캐시 생성
- 캐시 효율이 떨어짐
- 사용자별 데이터는 캐싱하지 않는 것이 좋음

**3. POST 요청:**
- CloudFront는 기본적으로 POST를 캐싱하지 않음
- POST는 항상 Origin으로 전달됨

**4. 쿼리 스트링 순서:**
- 쿼리 스트링 순서가 다르면 다른 캐시로 인식
- 예: `?a=1&b=2`와 `?b=2&a=1`은 다른 캐시
- 정규화 필요

**5. 비용:**
- 캐시 히트 시 데이터 전송 비용만 발생
- 캐시 미스 시 Origin 요청 비용 + 데이터 전송 비용
- 캐시 적중률을 높이면 비용 절감

### API 캐싱 모범 사례

**1. 경로별 정책 분리:**
- 정적 API: 긴 TTL
- 동적 API: 짧은 TTL
- 사용자별 API: 캐싱 안 함

**2. 버전 관리:**
- API 버전을 URL에 포함 (`/api/v1/products`)
- 새 버전 배포 시 자동으로 새 캐시 사용
- Invalidation 불필요

**3. ETag 활용:**
- Origin에서 ETag 반환
- 304 Not Modified로 데이터 전송량 절감

**4. 캐시 키 최적화:**
- 불필요한 헤더/쿼리 스트링 제외
- 캐시 키를 단순하게 유지
- 캐시 적중률 향상

**5. 모니터링:**
- 캐시 적중률 정기 확인
- Origin 부하 모니터링
- 비용 추적

---

## Origin 유형 및 적용 예시

| Origin | 사용 목적 |
|--------|-----------|
| S3 | 정적 웹사이트, 이미지, 정적 자원 |
| ALB | 백엔드 API 또는 서버 기반 웹서비스 |
| EC2 | 커스텀 서버 직접 연결 |
| API Gateway | Lambda 기반 서버리스 API |

---

## SSL 및 HTTPS 설정

CloudFront에서 HTTPS를 사용하려면 AWS Certificate Manager(ACM)를 통해 인증서를 발급받아야 하며,  
ACM은 반드시 `us-east-1` 리전에 있어야 한다.

예시 (AWS CLI):

```bash
aws acm request-certificate \
  --domain-name "cdn.example.com" \
  --validation-method DNS \
  --region us-east-1
```

---

## 커스텀 도메인 연결 흐름

```
Route 53 (CNAME / Alias)
       ↓
cdn.example.com
       ↓
CloudFront Distribution
       ↓
Origin (S3 / ALB / EC2 / API Gateway)
```

DNS 예시:

```
cdn.example.com   A(ALIAs)   d1234abcd.cloudfront.net
```

---

## React 정적 파일 배포 예시

```
[사용자] 
   ↓
[CloudFront CDN]
   ↓
[S3 Bucket (정적 React build files)]
   ↓
(optional) API 요청 → API Gateway / ALB / Lambda
```

`npm run build` 또는 `yarn build`로 생성된 React 앱은 완전한 정적 파일이며, 캐싱에 적합하다.

---

## 비용 구조

| 항목 | 과금 방식 |
|------|-----------|
| Data Transfer Out | POP → 사용자 전송 데이터 기준 |
| Requests | CDN 요청 수 기준 |
| Invalidation | 캐시 삭제 요청 1,000건당 비용 발생 (약 $0.005) |

주의: `aws cloudfront create-invalidation`를 반복적으로 사용하면 불필요한 비용이 발생할 수 있다.

---

## 실무 팁

**정적 콘텐츠:**
- 정적 사이트는 CloudFront로 배포하면 속도와 비용 모두 최적화 가능
- 캐시 무효화를 줄이기 위해 빌드 파일 이름에 해시값 추가 (`main.[hash].js`)
- S3와 CloudFront 조합으로 비용 절감

**API 캐싱:**
- API 캐싱 시 TTL이 너무 길면 데이터 일관성 문제가 발생할 수 있으므로 주의
- 사용자별 데이터는 캐싱하지 않는다
- 경로별로 다른 캐싱 정책을 적용한다
- 캐시 적중률을 모니터링한다

**성능 최적화:**
- 다국적 서비스의 경우 리전 + CDN 조합을 적극 활용
- Origin에서 Cache-Control 헤더를 적절히 설정한다
- ETag를 활용해 데이터 전송량을 절감한다

---

## 참고 문서

- [AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)
- [AWS 가격 계산기](https://calculator.aws/#/estimate)