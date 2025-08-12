---
title: AWS ECR (Elastic Container Registry)
tags: [aws, containers, ecr, docker, registry]
updated: 2024-12-19
---

# AWS ECR (Elastic Container Registry)

## 배경

AWS ECR(Elastic Container Registry)은 Docker 컨테이너 이미지를 안전하게 저장, 관리, 배포할 수 있는 완전 관리형 Docker 컨테이너 레지스트리 서비스입니다. 개발자가 컨테이너 이미지를 쉽게 업로드하고, 팀원들과 공유하며, 프로덕션 환경에 배포할 수 있도록 도와줍니다.

## 핵심

### ECR의 기본 개념

#### 컨테이너 레지스트리
- Docker 이미지를 저장하고 관리하는 중앙 저장소
- 팀원들이 공통으로 사용할 수 있는 이미지 저장소
- 버전 관리 및 배포 자동화 지원

#### AWS 통합
- AWS IAM을 통한 접근 제어
- VPC 엔드포인트를 통한 보안 강화
- CloudWatch를 통한 모니터링
- AWS CodePipeline과의 CI/CD 연동

### ECR 구성 요소

| 구성 요소 | 설명 | 역할 |
|-----------|------|------|
| **Registry** | ECR 전체 서비스 | Docker 이미지 저장소 전체 |
| **Repository** | 이미지 저장 폴더 | 특정 애플리케이션의 이미지들을 그룹화 |
| **Image** | 실행 가능한 애플리케이션 | 컨테이너로 실행될 애플리케이션 |
| **Tag** | 이미지 버전 구분 | 이미지의 특정 버전을 식별 |
| **Layer** | 이미지 구성 요소 | Docker 이미지를 구성하는 개별 레이어 |

### ECR의 장점

#### 보안
- AWS IAM과 통합된 접근 제어
- 이미지 스캔을 통한 보안 취약점 검사
- VPC 엔드포인트를 통한 프라이빗 네트워크 통신

#### 성능
- AWS 글로벌 인프라를 활용한 빠른 이미지 전송
- 같은 리전 내 무료 데이터 전송
- CDN을 통한 전 세계 빠른 배포

#### 통합
- AWS 서비스들과의 원활한 연동
- CI/CD 파이프라인과의 자동화
- CloudWatch를 통한 모니터링

## 예시

### 기본 ECR 사용 예시

```bash
# 1. ECR 레지스트리 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

# 2. 리포지토리 생성
aws ecr create-repository --repository-name my-app --region ap-northeast-2

# 3. Docker 이미지 빌드
docker build -t my-app .

# 4. 이미지 태그 지정
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest

# 5. 이미지 푸시
docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest

# 6. 이미지 풀
docker pull 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest
```

### Python을 사용한 ECR 관리

```python
import boto3
import subprocess
import json

class ECRManager:
    def __init__(self, region='ap-northeast-2'):
        self.ecr_client = boto3.client('ecr', region_name=region)
        self.region = region
        
    def create_repository(self, repository_name):
        """ECR 리포지토리 생성"""
        try:
            response = self.ecr_client.create_repository(
                repositoryName=repository_name,
                imageScanningConfiguration={
                    'scanOnPush': True
                },
                encryptionConfiguration={
                    'encryptionType': 'AES256'
                }
            )
            return response['repository']['repositoryUri']
        except Exception as e:
            print(f"리포지토리 생성 실패: {e}")
            return None
    
    def get_login_token(self):
        """ECR 로그인 토큰 획득"""
        try:
            response = self.ecr_client.get_authorization_token()
            token = response['authorizationData'][0]['authorizationToken']
            return token
        except Exception as e:
            print(f"로그인 토큰 획득 실패: {e}")
            return None
    
    def list_images(self, repository_name):
        """리포지토리의 이미지 목록 조회"""
        try:
            response = self.ecr_client.list_images(
                repositoryName=repository_name
            )
            return response['imageIds']
        except Exception as e:
            print(f"이미지 목록 조회 실패: {e}")
            return []
    
    def delete_image(self, repository_name, image_tag):
        """이미지 삭제"""
        try:
            response = self.ecr_client.batch_delete_image(
                repositoryName=repository_name,
                imageIds=[{'imageTag': image_tag}]
            )
            return response
        except Exception as e:
            print(f"이미지 삭제 실패: {e}")
            return None

# 사용 예시
ecr_manager = ECRManager()

# 리포지토리 생성
repo_uri = ecr_manager.create_repository('my-web-app')
print(f"생성된 리포지토리 URI: {repo_uri}")

# 이미지 목록 조회
images = ecr_manager.list_images('my-web-app')
print(f"이미지 목록: {images}")
```

### Docker Compose와 ECR 연동

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-web-app:latest
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - db
  
  db:
    image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-database:latest
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 운영 팁

### 1. 보안 설정

#### IAM 정책 최소 권한 설정
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
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "arn:aws:ecr:ap-northeast-2:123456789012:repository/my-app"
        }
    ]
}
```

#### VPC 엔드포인트 설정
```bash
# VPC 엔드포인트 생성
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.ap-northeast-2.ecr.dkr \
    --subnet-ids subnet-12345678 subnet-87654321 \
    --security-group-ids sg-12345678
```

### 2. 이미지 태깅 전략

#### 시맨틱 버저닝
```bash
# 메이저.마이너.패치 형식
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:1.2.3
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:1.2
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:1
```

#### 환경별 태깅
```bash
# 환경별 태그
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:dev
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:staging
docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:prod
```

### 3. 이미지 최적화

#### 멀티스테이지 빌드
```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

#### 이미지 크기 최적화
```bash
# 불필요한 파일 제거
docker build --no-cache -t my-app .

# 이미지 압축
docker save my-app:latest | gzip > my-app.tar.gz

# 이미지 분석
docker history my-app:latest
```

### 4. 자동화 및 CI/CD

#### GitHub Actions와 연동
```yaml
# .github/workflows/deploy.yml
name: Deploy to ECR

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2

      - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: my-app
        IMAGE_TAG: ${{ github.sha }}
        run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

#### Jenkins와 연동
```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        AWS_DEFAULT_REGION = 'ap-northeast-2'
        ECR_REPOSITORY = 'my-app'
    }
    
    stages {
        stage('Login to ECR') {
            steps {
                sh 'aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com'
            }
        }
        
        stage('Build and Push') {
            steps {
                sh 'docker build -t my-app .'
                sh 'docker tag my-app:latest 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest'
                sh 'docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest'
            }
        }
    }
}
```

### 5. 비용 최적화

#### 이미지 수명 주기 정책
```json
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 5 images",
            "selection": {
                "tagStatus": "tagged",
                "tagPrefixList": ["v"],
                "countType": "imageCountMoreThan",
                "countNumber": 5
            },
            "action": {
                "type": "expire"
            }
        },
        {
            "rulePriority": 2,
            "description": "Remove untagged images older than 1 day",
            "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
```

#### 크로스 리전 복제 최적화
```bash
# 필요한 리전에만 복제
aws ecr create-repository \
    --repository-name my-app \
    --region us-west-2

aws ecr put-image \
    --repository-name my-app \
    --image-tag latest \
    --image-manifest "$(aws ecr batch-get-image --repository-name my-app --image-ids imageTag=latest --region ap-northeast-2 --query 'images[0].imageManifest' --output text)" \
    --region us-west-2
```

## 참고

### ECR과 다른 레지스트리 비교

| 기능 | AWS ECR | Docker Hub | Google Container Registry | Azure Container Registry |
|------|---------|------------|---------------------------|--------------------------|
| **무료 티어** | 500MB/월 | 1개 리포지토리 | 0.5GB/월 | 0.5GB/월 |
| **AWS 통합** | 완전 통합 | 제한적 | 제한적 | 제한적 |
| **보안** | IAM, VPC 엔드포인트 | 기본 인증 | IAM | Azure AD |
| **CI/CD** | CodePipeline, CodeBuild | GitHub Actions | Cloud Build | Azure DevOps |

### 관련 링크

- [AWS ECR 공식 문서](https://docs.aws.amazon.com/ecr/)
- [AWS ECR 가격](https://aws.amazon.com/ecr/pricing/)
- [Docker 공식 문서](https://docs.docker.com/)
- [AWS Well-Architected Framework - 컨테이너](https://aws.amazon.com/architecture/well-architected/)

