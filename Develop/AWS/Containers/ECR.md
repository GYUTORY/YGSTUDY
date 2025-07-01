# 🐳 AWS ECR (Elastic Container Registry)

> **📖 이 문서는 AWS ECR을 처음 접하는 분들을 위해 작성되었습니다.**

---

## 📋 목차
- [1. AWS ECR이란?](#1-aws-ecr이란)
- [2. 기본 용어 정리](#2-기본-용어-정리)
- [3. ECR의 핵심 개념](#3-ecr의-핵심-개념)
- [4. ECR 사용 예제](#4-ecr-사용-예제)
- [5. ECR과 CI/CD 연동](#5-ecr과-cicd-연동)
- [6. ECR 비용 및 보안](#6-ecr-비용-및-보안)
- [7. 결론](#7-결론)

---

## 1. AWS ECR이란? 🤔

### 💡 ECR이 무엇인가요?
**AWS ECR (Elastic Container Registry)**는 Amazon Web Services에서 제공하는 완전관리형 **Docker 컨테이너 이미지 저장소**입니다.

### 🏠 쉽게 비유하면...
ECR은 **"Docker 이미지들을 보관하는 아마존 창고"**라고 생각하시면 됩니다.
- 🏪 **일반 창고**: 물건을 보관하는 곳
- 🐳 **ECR**: Docker 이미지를 보관하는 곳

### 🎯 ECR이 필요한 이유
1. **개발한 애플리케이션을 어디에 보관할까?**
2. **팀원들과 어떻게 공유할까?**
3. **배포할 때 어떻게 가져올까?**

이 모든 문제를 ECR이 해결해줍니다!

---

## 2. 기본 용어 정리 📚

### 🐳 Docker란?
- **컨테이너 기술**: 애플리케이션을 독립적인 환경에서 실행할 수 있게 해주는 기술
- **이미지**: 애플리케이션과 실행 환경을 패키지로 만든 것
- **컨테이너**: 이미지를 실행한 상태

### 🏗️ CI/CD란?
- **CI (Continuous Integration)**: 코드를 지속적으로 통합하는 과정
- **CD (Continuous Deployment)**: 코드를 지속적으로 배포하는 과정

### 🔐 IAM이란?
- **AWS Identity and Access Management**: AWS에서 사용자 권한을 관리하는 서비스

---

## 3. ECR의 핵심 개념 📦

### 🏢 레지스트리 (Registry)
- **정의**: ECR의 전체 서비스 인스턴스
- **비유**: 아마존 창고 전체 건물

### 📁 리포지터리 (Repository)
- **정의**: Docker 이미지를 저장하는 폴더
- **비유**: 창고 안의 특정 구역 (예: 전자제품 구역, 의류 구역)

### 🖼️ 이미지 (Image)
- **정의**: 실행 가능한 애플리케이션 패키지
- **비유**: 창고에 보관되는 상품

### 🏷️ 태그 (Tag)
- **정의**: 이미지 버전을 구분하는 라벨
- **비유**: 상품의 모델명이나 버전 (예: iPhone 14, iPhone 15)

### 📋 용어 정리 표
| 용어 | 설명 | 비유 |
|------|------|------|
| Registry | ECR 전체 서비스 | 창고 전체 건물 |
| Repository | 이미지 저장 폴더 | 창고 내 특정 구역 |
| Image | 실행 가능한 애플리케이션 | 창고에 보관되는 상품 |
| Tag | 이미지 버전 구분 | 상품의 모델명/버전 |

---

## 4. ECR 사용 예제 🛠️

### 🎯 목표
간단한 웹 애플리케이션을 ECR에 업로드하고 다운로드하는 과정을 단계별로 설명합니다.

### 📋 사전 준비사항
1. **AWS 계정**이 필요합니다
2. **AWS CLI** 설치 및 구성
3. **Docker** 설치 및 실행

> **💡 AWS CLI란?**
> AWS 서비스를 명령줄에서 사용할 수 있게 해주는 도구입니다.

> **💡 Docker란?**
> 컨테이너 기술로, 애플리케이션을 독립적인 환경에서 실행할 수 있게 해주는 도구입니다.

---

### 📂 4.1 ECR 리포지터리 생성
```bash
aws ecr create-repository --repository-name my-app-repo
```

**🤔 이 명령어가 하는 일:**
- ECR에 "my-app-repo"라는 이름의 저장소를 만듭니다
- 마치 창고에 새로운 구역을 만드는 것과 같습니다

**📝 결과:**
- 리포지터리가 생성됩니다
- 리포지터리 URI가 반환됩니다 (예: `123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo`)

---

### 📦 4.2 Docker 이미지 빌드
```bash
docker build -t my-app .
```

**🤔 이 명령어가 하는 일:**
- 현재 디렉토리의 코드를 Docker 이미지로 만듭니다
- `-t my-app`: 이미지 이름을 "my-app"으로 지정
- `.`: 현재 디렉토리를 빌드 컨텍스트로 사용

**📝 결과:**
- 로컬에 "my-app"이라는 Docker 이미지가 생성됩니다

---

### 🔑 4.3 ECR 인증 (로그인)
```bash
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com
```

**🤔 이 명령어가 하는 일:**
- AWS ECR에 로그인합니다
- 마치 창고에 들어가기 전에 출입증을 받는 것과 같습니다

**📝 주의사항:**
- `<AWS_ACCOUNT_ID>`를 실제 AWS 계정 ID로 바꿔야 합니다
- `ap-northeast-2`는 서울 리전입니다

---

### 🚀 4.4 Docker 이미지 ECR 푸시
```bash
# 1단계: 이미지에 태그 지정
docker tag my-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo

# 2단계: ECR에 이미지 업로드
docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
```

**🤔 이 과정이 하는 일:**
1. **태그 지정**: 로컬 이미지에 ECR 주소를 붙입니다
2. **업로드**: ECR에 이미지를 보냅니다

**📝 비유:**
- 창고에 상품을 보낼 때 주소를 붙이고 배송하는 것과 같습니다

---

### 📥 4.5 ECR에서 Docker 이미지 Pull
```bash
docker pull <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo:latest
```

**🤔 이 명령어가 하는 일:**
- ECR에서 이미지를 다운로드합니다
- 마치 창고에서 상품을 가져오는 것과 같습니다

---

## 5. ECR과 CI/CD 연동 🛠️

### 🎯 CI/CD란?
**CI/CD**는 개발자가 코드를 작성하면 자동으로 테스트하고 배포하는 과정입니다.

### 📋 CI/CD의 장점
1. **자동화**: 수동 작업을 줄일 수 있습니다
2. **일관성**: 항상 같은 방식으로 배포됩니다
3. **빠른 배포**: 코드 변경 시 즉시 반영됩니다

---

### 🔄 GitHub Actions와 AWS ECR 연동 예제

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
      # 1단계: 코드 가져오기
      - name: Checkout repository
        uses: actions/checkout@v2

      # 2단계: AWS 인증 설정
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      # 3단계: ECR 로그인
      - name: Login to Amazon ECR
        run: |
          aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com

      # 4단계: 이미지 빌드 및 업로드
      - name: Build and Push Docker Image
        run: |
          docker build -t my-app .
          docker tag my-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
          docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
```

**🤔 이 과정이 하는 일:**
1. **코드 변경 감지**: GitHub에 코드가 올라오면 자동으로 시작
2. **AWS 인증**: ECR에 접근할 수 있는 권한 설정
3. **ECR 로그인**: ECR에 로그인
4. **빌드 및 업로드**: Docker 이미지를 만들고 ECR에 업로드

---

## 6. ECR 비용 및 보안 💰🔒

### 💰 비용 구조
ECR의 비용은 크게 두 가지로 나뉩니다:

#### 📦 저장 비용
- **과금 기준**: 저장된 이미지의 크기
- **비용**: GB당 월 요금
- **예시**: 1GB 이미지를 1개월 보관하면 약 $0.10

#### 📡 데이터 전송 비용
- **과금 기준**: 인터넷으로 이미지를 전송할 때
- **비용**: GB당 전송 요금
- **예시**: 1GB 이미지를 다운로드하면 약 $0.09

> **💡 팁: 같은 리전 내에서는 데이터 전송 비용이 무료입니다!**

---

### 🔒 보안 모범 사례

#### 1️⃣ IAM 정책 최소 권한 설정
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        }
    ]
}
```

#### 2️⃣ VPC 엔드포인트 사용
- **목적**: 인터넷을 거치지 않고 AWS 내부에서만 통신
- **장점**: 보안 강화 및 비용 절약

#### 3️⃣ 이미지 스캔 활성화
- **목적**: 보안 취약점 자동 검사
- **장점**: 안전한 이미지 보장

---

## 7. 결론 ✅

### 🎯 ECR의 핵심 가치
1. **완전관리형**: 인프라 관리 없이 사용 가능
2. **고가용성**: AWS의 글로벌 인프라 활용
3. **보안 강화**: IAM 기반 접근 제어
4. **CI/CD 통합**: 자동화된 배포 파이프라인 구축
