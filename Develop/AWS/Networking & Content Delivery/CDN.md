
# 🌐 AWS CDN (CloudFront) 설정 가이드

---

## 1. AWS CDN (CloudFront)란?
**AWS CloudFront**는 Amazon Web Services에서 제공하는 **콘텐츠 전송 네트워크(Content Delivery Network, CDN)** 서비스입니다.  
전 세계 여러 엣지 로케이션(Edge Location)을 활용하여 웹 콘텐츠, 비디오, 애플리케이션 데이터를 **저지연**으로 배포할 수 있습니다.

---

### 👉🏻 CloudFront의 주요 특징
- **고속 데이터 전송**: 글로벌 엣지 로케이션을 통해 데이터 전송 가속.
- **보안 강화**: AWS Shield, WAF, SSL/TLS 지원.
- **비용 효율적**: 사용량 기반 과금.
- **S3와 연동**: S3와 쉽게 통합 가능.

---

## 2. CDN의 구성 요소 📦
- **오리진(Origin)**: 콘텐츠의 원본 위치 (예: S3 버킷, EC2 인스턴스).
- **엣지 로케이션(Edge Location)**: 사용자와 가까운 데이터 센터.
- **배포(Distribution)**: CloudFront에서 생성한 콘텐츠 제공 단위.
- **캐싱 정책(Cache Policy)**: 콘텐츠의 캐싱 방식 정의.

---

## 3. CloudFront 설정 가이드 🛠️
### 📦 사전 준비
- AWS 계정
- S3 버킷 (정적 웹사이트 호스팅)
- AWS CLI (선택 사항)

---

### 📂 3.1 CloudFront 배포 생성 (S3 버킷 연결)
1. **AWS 콘솔 접속:** [https://aws.amazon.com/](https://aws.amazon.com/)
2. **CloudFront 서비스 검색 및 진입**
3. **배포 생성 시작**
4. **오리진 설정:**
   - 오리진 도메인: `my-website-bucket.s3.amazonaws.com`
   - 오리진 액세스 제어: 퍼블릭 접근 허용 (또는 OAI 사용)
5. **캐싱 정책 선택:**
   - 기본 캐싱 정책 사용
6. **보안 설정:**
   - HTTPS만 사용
7. **배포 생성 완료**

---

### 📄 3.2 S3 버킷 구성 (정적 웹사이트 호스팅)
1. **S3 버킷 생성**
2. **정적 웹사이트 호스팅 활성화**
3. **퍼블릭 접근 허용**
4. **버킷 정책 설정 (선택 사항)**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::my-website-bucket/*"
        }
    ]
}
```

---

### 🚀 3.3 CloudFront 도메인과 연결
- CloudFront에서 제공하는 **배포 도메인 이름** 사용.
- 예시: `d1234.cloudfront.net`

---

### 🌐 3.4 사용자 지정 도메인 연결 (Route 53)
1. **Route 53에서 호스팅 존 생성**
2. **새 A 레코드 추가:**
   - 레코드 이름: `www.mywebsite.com`
   - 레코드 유형: **A 레코드 (Alias)**
   - 타겟: CloudFront 배포 도메인 선택

---

## 4. 캐싱 및 최적화 설정 📊
### ✅ 캐싱 정책
- **기본 캐싱 정책(Default Cache Policy)**: CloudFront 기본 제공.
- **사용자 정의 캐싱 정책(Custom Cache Policy)**:
   - TTL (Time To Live) 설정
   - 특정 파일 형식 캐싱

```bash
aws cloudfront create-cache-policy --cache-policy-config file://cache-policy.json
```

---

### ✅ 압축 및 성능 최적화
- **Gzip 및 Brotli 압축 사용**
- **HTTP/2 및 HTTP/3 지원**
- **오리진 보호를 위한 OAI 사용**

---

## 5. CloudFront와 CI/CD 연동 🌐
### GitHub Actions로 CloudFront 배포 업데이트 자동화
```yaml
name: Deploy to CloudFront

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      - name: Deploy to S3
        run: |
          aws s3 sync ./public s3://my-website-bucket --delete

      - name: Invalidate CloudFront Cache
        run: |
          aws cloudfront create-invalidation --distribution-id <DISTRIBUTION_ID> --paths "/*"
```

---

## 6. CloudFront 비용 및 보안
### 💰 비용
- **데이터 전송 비용**: 지역별 데이터 전송량 기준
- **요청 수**: HTTP 요청 수 기준 과금
- **오리진 요청 비용**: 원본 서버 요청 기준 과금

### 🔒 보안 모범 사례
- **IAM 최소 권한 부여**
- **OAI (Origin Access Identity) 사용**
- **SSL/TLS 활성화 (HTTPS 보장)**

---

## 7. CloudFront의 장단점
| **장점**                          | **단점**                   |
|:----------------------------------|:--------------------------|
| ✅ 글로벌 콘텐츠 전송             | ❗ 캐시 무효화 비용 발생   |
| ✅ 빠른 데이터 전송               | ❗ 구성 복잡성 있음       |
| ✅ S3, EC2, Lambda와 완벽 연동   | ❗ 데이터 전송 비용 발생  |

---

## 8. 결론 ✅
- **AWS CloudFront**는 글로벌 엣지 로케이션을 활용한 **빠르고 안전한 CDN 서비스**입니다.
- **정적 웹사이트, 비디오 스트리밍, API 가속화** 등 다양한 용도로 사용 가능합니다.
- **S3, Route 53**과 완벽하게 연동되며, **HTTPS 및 보안 강화** 기능을 제공합니다.
