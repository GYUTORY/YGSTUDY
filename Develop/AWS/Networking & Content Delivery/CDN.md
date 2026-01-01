---
title: AWS CloudFront — CDN & 캐싱 이해
tags: [aws, cloudfront, cdn, edge, caching, networking]
updated: 2026-01-01
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

- 정적 사이트는 CloudFront로 배포하면 속도와 비용 모두 최적화 가능
- 캐시 무효화를 줄이기 위해 빌드 파일 이름에 해시값 추가 (`main.[hash].js`)
- API 캐싱 시 TTL이 너무 길면 데이터 일관성 문제가 발생할 수 있으므로 주의
- 다국적 서비스의 경우 리전 + CDN 조합을 적극 활용

---

## 참고 문서

- [AWS CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)
- [AWS 가격 계산기](https://calculator.aws/#/estimate)