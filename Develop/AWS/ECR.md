
# 🐳 AWS ECR (Elastic Container Registry)

---

## 1. AWS ECR이란?
**AWS ECR (Elastic Container Registry)**는 Amazon Web Services에서 제공하는 완전관리형 **Docker 컨테이너 이미지 저장소**입니다.  
Docker 이미지를 안전하게 저장, 관리, 배포할 수 있도록 설계되었습니다.

---

### 👉🏻 ECR의 주요 특징
- **완전관리형**: 인프라 관리 없이 컨테이너 이미지를 저장할 수 있습니다.
- **보안 강화**: AWS IAM을 통한 접근 제어 및 암호화 제공.
- **고가용성**: AWS의 글로벌 인프라를 통해 고가용성을 제공.
- **CI/CD 통합 가능**: AWS CodePipeline, CodeBuild와 쉽게 통합.

---

## 2. ECR의 핵심 개념 📦
- **리포지터리(Repository)**: Docker 이미지를 저장하는 장소.
- **이미지(Image)**: 실행 가능한 애플리케이션 패키지.
- **태그(Tag)**: 이미지 버전을 구분하는 라벨.
- **레지스트리(Registry)**: 리포지터리를 포함하는 ECR 인스턴스.

---

## 3. ECR 사용 예제
### 🛠️ 사전 준비
- AWS CLI 설치 및 구성 (`aws configure`)
- Docker 설치 및 실행

---

### 📂 3.1 ECR 리포지터리 생성
```bash
aws ecr create-repository --repository-name my-app-repo
```

---

### 📦 3.2 Docker 이미지 빌드
```bash
docker build -t my-app .
```

---

### 🔑 3.3 ECR 인증 (로그인)
```bash
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com
```

---

### 🚀 3.4 Docker 이미지 ECR 푸시
```bash
docker tag my-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
```

---

### 📥 3.5 ECR에서 Docker 이미지 Pull
```bash
docker pull <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo:latest
```

---

## 4. ECR과 CI/CD 연동 🛠️
### 예시: GitHub Actions와 AWS ECR
```yaml
name: Deploy to ECR

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

      - name: Login to Amazon ECR
        run: |
          aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com

      - name: Build and Push Docker Image
        run: |
          docker build -t my-app .
          docker tag my-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
          docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
```

---

## 5. ECR 비용 및 보안
### 💰 비용
- **저장 비용**: 저장된 이미지 크기에 따라 과금
- **데이터 전송 비용**: 인터넷으로 이미지를 전송할 경우 추가 요금 발생

### 🔒 보안 모범 사례
- **IAM 정책 최소 권한 설정**
- **VPC 엔드포인트 사용**
- **이미지 스캔 활성화**

---

## 6. 결론 ✅
- **AWS ECR**은 완전관리형 Docker 컨테이너 이미지 레지스트리입니다.
- **고가용성**과 **보안 강화**를 제공하며 CI/CD와 쉽게 연동 가능합니다.
- **Docker CLI**를 사용하여 손쉽게 이미지를 Push/Pull 할 수 있습니다.
