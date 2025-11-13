---
title: AWS ECR (Elastic Container Registry)
tags: [aws, containers, ecr, docker, registry]
updated: 2025-11-01
---

# AWS ECR (Elastic Container Registry)

## 개요

AWS ECR은 Docker 컨테이너 이미지를 저장하고 관리하는 완전 관리형 레지스트리 서비스입니다. AWS 생태계와 통합되어 ECS, EKS, Lambda 등에서 바로 사용할 수 있습니다.

## 기본 구조

```
Registry (AWS 계정)
  └── Repository (이미지 저장소)
      └── Image (컨테이너 이미지)
          └── Tag (버전 라벨)
              └── Layer (이미지 레이어)
```

## 기본 사용법

### 리포지토리 생성

```bash
# AWS CLI로 리포지토리 생성
aws ecr create-repository \
  --repository-name my-app \
  --region ap-northeast-2

# 이미지 스캔 활성화
aws ecr create-repository \
  --repository-name my-app \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

### 이미지 푸시

```bash
# 1. ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com

# 2. 이미지 빌드
docker build -t my-app:latest .

# 3. 이미지 태깅
docker tag my-app:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest

# 4. 이미지 푸시
docker push 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest
```

### 이미지 풀

```bash
# ECR에서 이미지 가져오기
docker pull 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest
```

## 태깅 전략

### 시맨틱 버저닝

```bash
# 메이저.마이너.패치 형식
docker tag my-app:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:1.2.3

# 환경별 태그
docker tag my-app:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:prod-1.2.3
```

### Git 커밋 해시 태깅

```bash
# CI/CD 파이프라인에서 자동 태깅
COMMIT_SHA=$(git rev-parse --short HEAD)
docker tag my-app:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:${COMMIT_SHA}
```

### 빌드 번호 태깅

```bash
BUILD_NUMBER=123
docker tag my-app:latest \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:build-${BUILD_NUMBER}
```

## 이미지 관리

### 이미지 목록 조회

```bash
# 리포지토리 목록
aws ecr describe-repositories

# 특정 리포지토리의 이미지 목록
aws ecr list-images \
  --repository-name my-app \
  --region ap-northeast-2
```

### 이미지 태그 조회

```bash
# 특정 이미지의 모든 태그
aws ecr describe-images \
  --repository-name my-app \
  --image-ids imageTag=latest
```

### 이미지 삭제

```bash
# 특정 태그 삭제
aws ecr batch-delete-image \
  --repository-name my-app \
  --image-ids imageTag=old-version

# 여러 이미지 일괄 삭제
aws ecr batch-delete-image \
  --repository-name my-app \
  --image-ids \
    imageTag=v1.0.0 \
    imageTag=v1.0.1 \
    imageTag=v1.0.2
```

## 수명 주기 정책

### 자동 삭제 정책 설정

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "최신 10개 이미지만 유지",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "30일 이상 된 이미지 삭제",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

```bash
# 정책 적용
aws ecr put-lifecycle-policy \
  --repository-name my-app \
  --lifecycle-policy-text file://lifecycle-policy.json
```

## 보안

### IAM 정책 예제

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

### 이미지 스캔

```bash
# 수동 스캔 시작
aws ecr start-image-scan \
  --repository-name my-app \
  --image-id imageTag=latest

# 스캔 결과 조회
aws ecr describe-image-scan-findings \
  --repository-name my-app \
  --image-id imageTag=latest
```

### VPC 엔드포인트 설정

```bash
# VPC 엔드포인트 생성 (프라이빗 네트워크 접근)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.ap-northeast-2.ecr.dkr \
  --subnet-ids subnet-12345678 \
  --security-group-ids sg-12345678
```

## CI/CD 통합

### GitHub Actions 예제

```yaml
name: Build and Push to ECR

on:
  push:
    branches: [ main ]

jobs:
  build:
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

### Jenkins Pipeline 예제

```groovy
pipeline {
    agent any
    
    environment {
        AWS_REGION = 'ap-northeast-2'
        ECR_REGISTRY = '123456789012.dkr.ecr.ap-northeast-2.amazonaws.com'
        IMAGE_NAME = 'my-app'
    }
    
    stages {
        stage('Build') {
            steps {
                script {
                    sh '''
                        aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        
                        docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} \
                          ${ECR_REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} \
                          ${ECR_REGISTRY}/${IMAGE_NAME}:latest
                        
                        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }
    }
}
```

## ECS/EKS 연동

### ECS Task Definition에서 사용

```json
{
  "family": "my-app",
  "containerDefinitions": [
    {
      "name": "my-app",
      "image": "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest",
      "cpu": 256,
      "memory": 512,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ]
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512"
}
```

### EKS Deployment에서 사용

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:latest
        ports:
        - containerPort: 80
```

## 비용 최적화

### 이미지 레이어 최적화

```dockerfile
# 멀티스테이지 빌드로 이미지 크기 최소화
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### 크로스 리전 복제

```bash
# 리전 복제 설정 (필요한 리전에만)
aws ecr create-repository \
  --repository-name my-app \
  --region us-east-1 \
  --replication-configuration \
    '{"rules":[{"destinations":[{"region":"us-west-2","registryId":"123456789012"}]}]}'
```

## 모니터링

### CloudWatch 메트릭

```bash
# 리포지토리 메트릭 조회
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECR \
  --metric-name RepositorySize \
  --dimensions Name=RepositoryName,Value=my-app \
  --start-time 2025-11-01T00:00:00Z \
  --end-time 2025-11-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

## 주요 명령어 정리

```bash
# 리포지토리 생성
aws ecr create-repository --repository-name <name>

# 로그인
aws ecr get-login-password | docker login --username AWS --password-stdin <registry-url>

# 이미지 목록
aws ecr list-images --repository-name <name>

# 이미지 삭제
aws ecr batch-delete-image --repository-name <name> --image-ids imageTag=<tag>

# 수명 주기 정책 설정
aws ecr put-lifecycle-policy --repository-name <name> --lifecycle-policy-text file://policy.json

# 이미지 스캔
aws ecr start-image-scan --repository-name <name> --image-id imageTag=<tag>
```

## 참고 자료

- **공식 문서**: https://docs.aws.amazon.com/ecr/
- **가격**: https://aws.amazon.com/ecr/pricing/
- **모범 사례**: https://docs.aws.amazon.com/ecr/latest/userguide/best-practices.html
