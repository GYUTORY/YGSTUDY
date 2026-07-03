---
title: AWS CloudFront 캐시 무효화(Cache Invalidation) 정책
tags: [aws, cloudfront, cdn, cache, invalidation, terraform, github-actions]
updated: 2026-04-24
---

# CDN 캐시 무효화 정책 (AWS CloudFront 중심)

CloudFront 같은 CDN은 엣지 로케이션(POP)에 콘텐츠를 캐싱해두고 요청 시 빠르게 제공한다.
콘텐츠가 변경되었을 때, 캐시된 오래된 파일을 어떻게 갱신할 것인가가 관건이다. 이 작업을 **Cache Invalidation(무효화)** 이라고 한다.

---

## 1. 캐시 무효화란?

CDN에 이미 저장된 캐시를 강제로 지워버리는 작업이다.
무효화 이후 다음 요청부터는 오리진 서버(S3, EC2 등)에서 새로운 콘텐츠를 가져온다.

무효화는 캐시 만료(Expiration)와 다르다. 만료는 TTL이나 Cache-Control 헤더에 의해 자연스럽게 캐시가 사라지는 것이고, 무효화는 TTL과 무관하게 수동으로 즉시 제거하는 것이다.

---

## 2. 무효화가 필요한 시점

- 정적 파일(HTML, JS, CSS, 이미지 등)을 배포했는데 변경사항이 반영되지 않을 때
- 긴 TTL로 캐싱해놨지만 긴급하게 파일을 바꿔야 할 때
- 앱 업데이트 후 웹 클라이언트가 구버전 JS 파일을 계속 받을 때
- 동일한 URL 경로에 다른 콘텐츠가 업로드됐을 때

---

## 3. 무효화 방법

### 3.1 AWS Console에서 수동 무효화

1. CloudFront 콘솔 접속
2. 배포 ID 클릭 → "Invalidations" 탭
3. "Create Invalidation" 클릭
4. 무효화 경로 입력

```
/index.html
/main.js
/images/*
```

`*` 와일드카드를 지원한다. 예: `/static/*`

### 3.2 AWS CLI로 무효화

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/index.html" "/main.js"
```

여러 경로를 한 번에 지정할 수 있다. 공식 한도는 경로 3,000개(요청당)지만, 실무에서는 와일드카드 하나가 경로 1개로 카운트된다는 점을 알아야 한다.

---

## 4. CI/CD 파이프라인 연동

배포할 때마다 수동으로 무효화를 실행하면 빠뜨리는 경우가 생긴다. GitHub Actions에 무효화 단계를 추가해두면 배포 직후 자동으로 실행된다.

### 4.1 GitHub Actions + AWS CLI

```yaml
name: Deploy to S3 and Invalidate CloudFront

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      - name: Build
        run: npm ci && npm run build

      - name: Upload to S3
        run: |
          aws s3 sync ./dist s3://${{ secrets.S3_BUCKET }} \
            --delete \
            --cache-control "max-age=31536000,immutable" \
            --exclude "index.html"
          aws s3 cp ./dist/index.html s3://${{ secrets.S3_BUCKET }}/index.html \
            --cache-control "no-cache,no-store,must-revalidate"

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DIST_ID }} \
            --paths "/index.html"
```

여기서 핵심은 JS/CSS 파일에는 장기 캐시를 적용하고, `index.html`만 무효화하는 구조다. JS/CSS는 빌드 시 파일명에 해시가 붙으므로 URL 자체가 바뀐다.

### 4.2 GitHub Actions + AWS SDK (Node.js)

CLI 대신 SDK를 써야 하는 경우(빌드 결과에서 변경된 파일만 선별해서 무효화하는 등)에는 스크립트를 직접 작성한다.

```javascript
// scripts/invalidate-cloudfront.mjs
import {
  CloudFrontClient,
  CreateInvalidationCommand,
} from "@aws-sdk/client-cloudfront";

const client = new CloudFrontClient({ region: "ap-northeast-2" });

async function invalidate(distributionId, paths) {
  const command = new CreateInvalidationCommand({
    DistributionId: distributionId,
    InvalidationBatch: {
      CallerReference: `deploy-${Date.now()}`,
      Paths: {
        Quantity: paths.length,
        Items: paths,
      },
    },
  });

  const response = await client.send(command);
  console.log(
    "Invalidation ID:",
    response.Invalidation.Id,
    "Status:",
    response.Invalidation.Status
  );
}

// 변경된 파일 경로만 골라서 무효화
const changedPaths = process.argv.slice(2);
await invalidate(process.env.CLOUDFRONT_DIST_ID, changedPaths);
```

```yaml
# GitHub Actions 단계에서 호출
- name: Invalidate changed files
  run: |
    CHANGED=$(git diff --name-only HEAD~1 HEAD -- dist/ | sed 's|^dist||')
    node scripts/invalidate-cloudfront.mjs $CHANGED
```

변경된 파일만 무효화하는 방식은 비용 측면에서 유리하지만, 빌드 아티팩트와 Git diff를 맞추는 게 까다롭다. 단순히 `index.html`만 무효화하는 게 실수할 여지가 적다.

---

## 5. Terraform으로 자동 무효화

인프라를 Terraform으로 관리하는 경우, `null_resource`와 `local-exec`를 조합해서 배포 시 무효화를 자동으로 실행할 수 있다.

```hcl
resource "null_resource" "invalidate_cloudfront" {
  # S3 버킷에 파일이 업로드될 때마다 트리거
  triggers = {
    s3_etag = aws_s3_object.frontend.etag
  }

  provisioner "local-exec" {
    command = <<EOT
      aws cloudfront create-invalidation \
        --distribution-id ${aws_cloudfront_distribution.main.id} \
        --paths "/index.html"
    EOT
  }

  depends_on = [aws_s3_object.frontend]
}
```

`triggers`의 `s3_etag` 값이 바뀔 때만 실행된다. S3 파일이 그대로면 무효화도 실행하지 않는다.

`local-exec`는 Terraform을 실행하는 머신에서 AWS CLI가 설치되어 있고 적절한 권한이 있어야 동작한다. CI/CD 파이프라인에서 Terraform을 실행한다면 파이프라인 IAM 역할에 `cloudfront:CreateInvalidation` 권한을 추가해야 한다.

---

## 6. 무효화 비용과 경로 범위

CloudFront 무효화는 매월 기본 1,000개 경로가 무료다. 그 이후부터 경로 1개당 $0.005가 과금된다.

### 비용이 예상보다 많이 나오는 경우

와일드카드(`/*`)로 무효화를 요청하면 경로 1개로 카운트된다. 그런데 팀에서 이 사실을 모르고 배포 스크립트마다 `/*`를 쓰면 경로 개수는 적지만 실제 무효화 범위가 전체가 된다.

반대로 배포 스크립트에서 변경된 파일 경로를 하나씩 나열하면 경로 수가 늘어난다. 예를 들어 파일 200개를 개별 경로로 무효화하면 무료 한도(1,000개)가 하루 5번 배포만 해도 소진된다.

실무에서 자주 겪는 패턴:
- 매 배포마다 `/static/*`, `/assets/*`를 각각 무효화하도록 스크립트 작성
- 하루 배포 10회 × 경로 2개 = 20개/일 → 월 600개 (무료 범위 내)
- 배포 빈도가 올라가면 어느 순간 무료 한도를 초과하기 시작

무효화 경로는 변경이 발생한 디렉토리 단위로 범위를 제한하는 게 낫다. `/static/*` 대신 `/static/js/*`와 `/static/css/*`로 나누거나, `index.html` 하나만 무효화하고 나머지는 파일명 해시에 의존하는 구조가 비용 측면에서 안정적이다.

---

## 7. 무효화 전파 지연 문제

`create-invalidation`을 실행했다고 해서 즉시 모든 엣지에 반영되는 게 아니다. CloudFront는 전 세계 수백 개의 엣지 로케이션에 무효화 명령을 전파하는데, 이 과정이 보통 수 초에서 수 분 걸린다.

### 실제로 겪는 상황

- 배포 완료 후 `index.html` 무효화 요청을 보냄
- 서울 엣지에서는 즉시 반영됨
- 도쿄, 싱가포르 엣지에서는 1~3분 동안 구버전 HTML을 계속 응답
- 이 사이에 도쿄에서 접속한 사용자는 구버전 HTML + 신버전 JS를 받아서 앱이 깨짐

### 대응 방법

**방법 1: 파일명 해시로 JS/CSS 버전 관리**

`index.html`을 제외한 모든 정적 파일은 빌드 시 해시를 붙인다.
`main.abc123.js`로 파일명이 바뀌면 구버전 HTML이 `main.abc123.js`를 요청해도 문제가 없다. 신버전 HTML이 배포되기 전까지 구버전 HTML은 구버전 JS 파일명을 참조하기 때문이다.

**방법 2: 배포 완료 후 일정 시간 대기**

무효화 요청 후 모든 엣지에 전파가 완료되었는지 상태를 확인한다.

```bash
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/index.html" \
  --query 'Invalidation.Id' \
  --output text)

# 전파 완료될 때까지 대기 (보통 30초~3분)
aws cloudfront wait invalidation-completed \
  --distribution-id $DIST_ID \
  --id $INVALIDATION_ID

echo "Invalidation completed"
```

`aws cloudfront wait invalidation-completed`는 완료될 때까지 폴링하다가 완료 시 반환한다.

**방법 3: HTML에서 JS 경로를 절대 경로로 참조**

`index.html`이 항상 최신 해시가 붙은 파일명을 참조하므로, 구버전 HTML과 신버전 HTML이 동시에 서비스되더라도 각자 자신의 JS/CSS 버전을 정확히 참조한다.

---

## 8. 캐시 계층별 무효화 순서

CloudFront 무효화만 해도 충분한 경우가 많지만, 앱 서버 자체에 로컬 캐시나 Redis 캐시가 있다면 순서대로 무효화해야 한다.

```
CDN(CloudFront) → 앱 로컬 캐시 → Redis
```

이 순서를 거꾸로 하면 문제가 생긴다. Redis 캐시를 먼저 지워도 CDN이 여전히 구버전을 캐싱하고 있으면 Redis까지 요청이 도달하지 않는다.

### 계층별 무효화 예제

```bash
#!/bin/bash

DIST_ID=$1
APP_ENDPOINT=$2
CACHE_KEY_PATTERN=$3

echo "1. Invalidating CloudFront..."
aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/api/*"

echo "2. Clearing app local cache..."
curl -X POST "$APP_ENDPOINT/internal/cache/clear" \
  -H "Authorization: Bearer $INTERNAL_TOKEN"

echo "3. Clearing Redis cache..."
redis-cli -h "$REDIS_HOST" -p 6379 \
  --scan --pattern "$CACHE_KEY_PATTERN" | xargs redis-cli DEL
```

실무에서는 앱 로컬 캐시(예: Guava Cache, Caffeine)를 별도로 지우는 API를 만들어두는 경우가 있다. 이 API에 CDN 무효화 완료 이후 순차적으로 호출하는 방식이다.

---

## 9. 버전 태깅으로 무효화 최소화

무효화를 자주 실행하는 구조 자체를 피하는 방법이 있다.

### 해시 기반 파일명

```text
main.9f2a84a.js
style.d43dc0c.css
```

파일이 변경되면 파일명 자체가 바뀌므로 무효화가 불필요하다. Webpack, Vite, Create React App은 빌드 시 자동으로 해시를 붙여준다.

이 구조에서는 `index.html`만 무효화하면 된다. JS/CSS 파일은 URL이 달라지므로 기존 캐시와 충돌하지 않는다.

```yaml
# S3 업로드 시 파일 유형별로 다른 Cache-Control 적용
- name: Upload assets (hashed, long cache)
  run: |
    aws s3 sync ./dist/assets s3://$BUCKET/assets \
      --cache-control "max-age=31536000,immutable"

- name: Upload index.html (no cache)
  run: |
    aws s3 cp ./dist/index.html s3://$BUCKET/index.html \
      --cache-control "no-cache,no-store,must-revalidate"
```

`index.html`을 `no-cache`로 설정하면 브라우저와 CDN이 매번 오리진에서 검증한다. 이렇게 하면 CloudFront 무효화 없이도 새로운 `index.html`을 빠르게 반영할 수 있다.

---

## 10. TTL 설정

CloudFront는 TTL을 통해 콘텐츠의 캐시 수명을 조절한다.

- **MinTTL**: 최소 TTL. 이 시간 이전에는 오리진 재검사하지 않음
- **DefaultTTL**: 기본 TTL. 오리진에서 Cache-Control 헤더가 없을 때 사용
- **MaxTTL**: 최대 TTL. 오리진에서 너무 긴 TTL을 지정하더라도 이 값을 넘지 못함

```text
DefaultTTL: 86400 (1일)
MinTTL: 0
MaxTTL: 31536000 (1년)
```

오리진의 `Cache-Control` 헤더가 있으면 그 값을 우선 사용한다. S3에서 파일별로 `Cache-Control` 메타데이터를 다르게 설정하면 CloudFront 배포 설정과 무관하게 파일 단위로 TTL을 조절할 수 있다.

---

## 참고 자료

- [CloudFront Invalidation 공식 문서](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- [CloudFront 가격 정책](https://aws.amazon.com/cloudfront/pricing/)
- [웹 정적 리소스 캐싱](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
