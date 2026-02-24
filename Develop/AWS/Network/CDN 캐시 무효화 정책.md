---
title: AWS CloudFront 캐시 무효화(Cache Invalidation) 정책
tags: [aws, cloudfront, cdn, cache, invalidation]
updated: 2026-01-02
---

# CDN 캐시 무효화 정책 (AWS CloudFront 중심)

CloudFront 같은 CDN은 성능 향상을 위해 콘텐츠를 **엣지 로케이션(POP)** 에 캐싱해두고 요청 시 빠르게 제공한다.  
하지만 콘텐츠가 변경되었을 경우, **캐시된 오래된 파일을 어떻게 갱신할 것인가?** 가 관건이다. 이를 **Cache Invalidation (무효화)** 이라고 한다.

---

## 1. 캐시 무효화란?

CDN에 이미 저장된 캐시를 강제로 **지워버리는 작업**이다.  
그 결과, 다음 요청부터는 **오리진 서버(S3, EC2 등)** 에서 새로운 콘텐츠를 가져오게 된다.

---

## 2. 캐시 무효화가 필요한 시점

- 정적 파일(HTML, JS, CSS, 이미지 등)을 배포했는데 변경사항이 반영되지 않을 때
- 긴 TTL로 캐싱해놨지만, 긴급하게 파일을 바꿔야 할 때
- 앱 업데이트 후 웹 클라이언트가 구버전 JS 파일을 계속 받을 때
- 동일한 URL 경로에 다른 콘텐츠가 업로드됐을 때

---

## 3. 무효화 방법 (CloudFront 기준)

### 3.1 AWS Console에서 수동으로 무효화

1. CloudFront 콘솔 접속
2. 배포 ID 클릭 → "Invalidations" 탭
3. "Create Invalidation" 클릭
4. 무효화 경로 입력

**예시:**
```
/index.html
/main.js
/images/*
```

> `*` 와일드카드 지원. 예: `/static/*`

### 3.2 AWS CLI로 무효화

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/index.html" "/main.js"
```

> 여러 경로를 한 번에 지정 가능 (최대 1000개)

---

## 4. 무효화의 단점과 비용

| 항목 | 설명 |
|------|------|
| 지연 시간 | Invalidation 요청 후 최대 수 분까지 반영 지연 가능 |
| 과금 | 매월 기본 1,000개는 무료, 그 이후부터 건당 과금 발생 |
| 부하 | 너무 많은 invalidation은 CloudFront 엣지에 부담 |

---

## 5. 대체 전략: 버전 태깅 / 해시 캐싱

### 5.1 해시 기반 파일명 사용

```text
main.9f2a84a.js
style.d43dc0c.css
```

파일이 변경되면 **파일명 자체가 바뀌므로 무효화가 불필요**하다.

### 5.2 빌드시 해시 자동 추가

Webpack, Vite, Create React App 등은 빌드 시 자동으로 해시를 붙여준다.  
이런 정적 빌드 시스템에서는 일반적으로 **무효화를 하지 않고 캐싱 지속** 전략을 쓴다.

### 5.3 HTML만 무효화하고 나머지는 버전 태그

- `/index.html` → 변경 시 무효화 필요
- `/static/js/*.js` → 파일명에 해시 포함 → 무효화 불필요

---

## 6. TTL (캐시 수명) 전략

CloudFront는 TTL을 통해 콘텐츠의 **캐시 수명**을 조절할 수 있다.

| 설정 항목 | 의미 |
|-----------|------|
| MinTTL | 최소 TTL. 이 시간 이전에는 오리진 재검사하지 않음 |
| DefaultTTL | 기본 TTL. 오리진에서 Cache-Control 헤더가 없을 때 사용 |
| MaxTTL | 최대 TTL. 오리진에서 너무 긴 TTL을 지정하더라도 이 값을 넘지 못함 |

**예시:**
```text
DefaultTTL: 86400 (1일)
MinTTL: 0
MaxTTL: 31536000 (1년)
```

---

## 7. 캐시 무효화 vs 캐시 만료

| 구분 | 의미 |
|------|------|
| 무효화 (Invalidation) | 수동으로 캐시를 즉시 제거 |
| 만료 (Expiration) | TTL이나 헤더에 의해 자연스럽게 캐시가 만료됨 |

실무에서는 두 가지를 함께 사용하며, **정기 배포 + 버전 태깅 + 긴 TTL + 무효화 최소화** 전략이 가장 효과적이다.

---

## 8. 실무 전략 요약

| 상황 | 전략 |
|------|------|
| 정적 파일 빌드 | 파일명에 해시 포함 → 무효화 없이도 안정 |
| HTML만 변경 | `/index.html` 만 무효화 요청 |
| 긴급 수정 | `aws cloudfront create-invalidation` 사용 |
| 자주 배포 | 버전 디렉토리 분리 (`/v1.2.3/`) 또는 해시 전략 |
| 비용 최소화 | 무효화는 최소화하고 TTL/Cache-Control 관리 |

---

## 참고 자료

- [CloudFront Invalidation 공식 문서](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- [CloudFront 가격 정책](https://aws.amazon.com/cloudfront/pricing/)
- [웹 정적 리소스 캐싱 전략](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)