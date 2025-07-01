# 🐳 AWS ECS (Elastic Container Service)

---

## 📋 목차
- [1. ECS란 무엇인가?](#1-ecs란-무엇인가)
- [2. 컨테이너 기초 개념](#2-컨테이너-기초-개념)
- [3. ECS 핵심 구성 요소](#3-ecs-핵심-구성-요소)
- [4. ECS 실행 모드](#4-ecs-실행-모드)
- [5. 실습: ECS로 애플리케이션 배포하기](#5-실습-ecs로-애플리케이션-배포하기)
- [6. CI/CD 파이프라인 구축](#6-cicd-파이프라인-구축)
- [7. 비용 및 보안](#7-비용-및-보안)
- [8. ECS vs EKS 비교](#8-ecs-vs-eks-비교)
- [9. 자주 묻는 질문 (FAQ)](#9-자주-묻는-질문-faq)

---

## 1. ECS란 무엇인가? 🤔

### 1.1 ECS의 정의
**Amazon ECS (Elastic Container Service)**는 AWS에서 제공하는 **완전관리형 컨테이너 오케스트레이션 서비스**입니다.

> 💡 **완전관리형이란?**
> - AWS가 인프라 관리, 패치, 보안 업데이트를 자동으로 처리
> - 사용자는 애플리케이션에만 집중할 수 있음
> - 서버 관리에 대한 부담이 없음

### 1.2 ECS가 해결하는 문제
| **문제점** | **ECS 솔루션** |
|------------|----------------|
| 서버 관리 복잡성 | 서버리스 방식으로 자동 관리 |
| 애플리케이션 확장 어려움 | 자동 스케일링 지원 |
| 배포 프로세스 복잡 | 간단한 명령어로 배포 |
| 리소스 낭비 | 사용한 만큼만 과금 |

### 1.3 ECS의 주요 특징
- ✅ **서버리스 지원**: Fargate 모드로 인프라 관리 불필요
- ✅ **고가용성**: 여러 가용영역에 자동 배포
- ✅ **자동 확장**: 트래픽에 따라 자동으로 컨테이너 수 조절
- ✅ **AWS 통합**: ECR, CloudWatch, IAM 등과 원활한 연동
- ✅ **다중 배포 옵션**: EC2, Fargate 선택 가능

---

## 2. 컨테이너 기초 개념 📦

### 2.1 컨테이너란?
> **컨테이너**는 애플리케이션과 그 실행에 필요한 모든 파일을 포함한 패키지입니다.

**컨테이너의 장점:**
- 🚀 **빠른 배포**: 몇 초 내에 애플리케이션 실행
- 🔄 **일관성**: 개발/테스트/운영 환경 동일
- 📦 **이식성**: 어디서든 동일하게 실행
- 🎯 **격리**: 다른 애플리케이션과 독립적 실행

### 2.2 컨테이너 vs 가상머신 비교

| **구분** | **가상머신 (VM)** | **컨테이너** |
|----------|-------------------|--------------|
| **크기** | 수 GB ~ 수십 GB | 수 MB ~ 수백 MB |
| **시작 시간** | 수 분 | 수 초 |
| **리소스 사용** | 높음 | 낮음 |
| **격리 수준** | 하드웨어 레벨 | OS 레벨 |
| **이식성** | 제한적 | 높음 |

### 2.3 Docker와 컨테이너의 관계
```
Docker = 컨테이너 기술
ECS = 컨테이너 관리 서비스
```

**Docker의 역할:**
- 컨테이너 이미지 생성
- 컨테이너 실행 환경 제공
- 이미지 저장소 관리

**ECS의 역할:**
- 여러 컨테이너를 효율적으로 관리
- 자동 스케일링 및 배포
- 고가용성 보장

### 2.4 ECS의 역할
```
개발자 → Docker 이미지 생성 → ECR에 업로드 → ECS가 컨테이너 실행
```

---

## 3. ECS 핵심 구성 요소 🧩

### 3.1 클러스터 (Cluster) 🏢
> **클러스터**는 컨테이너를 실행하는 인프라의 논리적 그룹입니다.

**클러스터의 역할:**
- 여러 컨테이너를 논리적으로 그룹화
- 리소스 관리 및 모니터링
- 보안 경계 설정

```bash
# 클러스터 생성 예시
aws ecs create-cluster --cluster-name my-production-cluster
```

### 3.2 태스크 정의 (Task Definition) 📋
> **태스크 정의**는 컨테이너 실행 방법을 정의하는 JSON 템플릿입니다.

**주요 설정 항목:**
- 🖼️ **이미지**: 실행할 Docker 이미지
- 💾 **메모리**: 컨테이너에 할당할 메모리
- ⚡ **CPU**: 컨테이너에 할당할 CPU
- 🔌 **포트**: 외부와 통신할 포트
- 🔑 **환경변수**: 애플리케이션 설정값

```json
{
  "family": "web-app-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "web-container",
      "image": "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/web-app:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/web-app-task",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 3.3 태스크 (Task) 🎯
> **태스크**는 태스크 정의에 따라 실행되는 하나 이상의 컨테이너입니다.

**태스크의 특징:**
- 태스크 정의의 인스턴스
- 독립적인 실행 단위
- 자체 IP 주소와 리소스 할당

### 3.4 서비스 (Service) 🔄
> **서비스**는 특정 태스크를 일정 수량 유지하고 배포를 관리합니다.

**서비스의 기능:**
- 📊 **자동 스케일링**: 트래픽에 따라 태스크 수 조절
- 🔄 **무중단 배포**: 새 버전 배포 시 서비스 중단 없음
- 🛡️ **헬스체크**: 비정상 태스크 자동 교체
- ⚖️ **로드밸런싱**: 여러 태스크에 트래픽 분산

### 3.5 ECS 구성 요소 관계도
```
클러스터 (Cluster)
├── 서비스 (Service)
│   ├── 태스크 (Task) - 태스크 정의 기반
│   ├── 태스크 (Task) - 태스크 정의 기반
│   └── 태스크 (Task) - 태스크 정의 기반
└── 서비스 (Service)
    ├── 태스크 (Task) - 다른 태스크 정의 기반
    └── 태스크 (Task) - 다른 태스크 정의 기반
```

---

## 4. ECS 실행 모드 🚀

### 4.1 Fargate 모드 (서버리스) ☁️
> **Fargate**는 서버를 관리하지 않고도 컨테이너를 실행할 수 있는 서버리스 방식입니다.

**Fargate의 장점:**
- 🎯 **서버 관리 불필요**: EC2 인스턴스 관리 안함
- 💰 **사용한 만큼만 과금**: 실제 사용 시간만 요금
- 🔒 **보안**: AWS가 패치 및 보안 관리
- ⚡ **빠른 시작**: 몇 분 내에 컨테이너 실행

**Fargate의 단점:**
- 💸 **비용**: EC2보다 상대적으로 비쌈
- 🔧 **제한사항**: 일부 고급 기능 제한
- 📊 **모니터링**: 세부적인 시스템 메트릭 접근 제한

### 4.2 EC2 모드 (서버 관리) 🖥️
> **EC2 모드**는 사용자가 직접 EC2 인스턴스를 관리하는 방식입니다.

**EC2 모드의 장점:**
- 💰 **비용 효율성**: 대용량 워크로드에서 경제적
- 🔧 **완전한 제어**: 모든 시스템 리소스 접근 가능
- 📊 **상세 모니터링**: 시스템 레벨 메트릭 확인 가능
- 🎛️ **커스터마이징**: 인스턴스 타입, 설정 자유롭게 선택

**EC2 모드의 단점:**
- 🛠️ **관리 복잡성**: 서버 관리 필요
- 🔒 **보안 책임**: 패치, 보안 업데이트 직접 관리
- ⏰ **시작 시간**: 인스턴스 시작 시간 필요

### 4.3 모드 선택 가이드 📝

| **상황** | **권장 모드** | **이유** |
|----------|---------------|----------|
| 소규모 프로젝트 | Fargate | 관리 부담 없음 |
| 대용량 트래픽 | EC2 | 비용 효율성 |
| 빠른 프로토타이핑 | Fargate | 빠른 시작 |
| 특별한 시스템 요구사항 | EC2 | 완전한 제어 |
| 예산 제약 | EC2 | 장기적으로 경제적 |

---

## 5. 실습: ECS로 애플리케이션 배포하기 🛠️

### 5.1 사전 준비사항 ✅

**필요한 도구:**
- AWS CLI 설치 및 구성
- Docker 설치 및 실행
- AWS 계정 및 적절한 권한

```bash
# AWS CLI 설치 (macOS)
brew install awscli

# AWS 자격 증명 설정
aws configure
```

### 5.2 단계별 배포 과정 📋

#### 1단계: ECR 리포지토리 생성
```bash
# ECR 리포지토리 생성
aws ecr create-repository --repository-name my-web-app

# 로그인 토큰 가져오기
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 123456789.dkr.ecr.ap-northeast-2.amazonaws.com
```

#### 2단계: Docker 이미지 빌드 및 푸시
```bash
# Dockerfile 생성
cat > Dockerfile << EOF
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# index.html 생성
echo "<h1>Hello ECS!</h1>" > index.html

# 이미지 빌드 및 푸시
docker build -t my-web-app .
docker tag my-web-app:latest 123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-web-app:latest
docker push 123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-web-app:latest
```

#### 3단계: ECS 클러스터 생성
```bash
aws ecs create-cluster --cluster-name my-web-cluster
```

#### 4단계: 태스크 정의 생성
```json
{
  "family": "web-app-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "web-container",
      "image": "123456789.dkr.ecr.ap-northeast-2.amazonaws.com/my-web-app:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/web-app-task",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

```bash
# 태스크 정의 등록
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 5단계: ECS 서비스 생성
```bash
aws ecs create-service \
  --cluster my-web-cluster \
  --service-name web-service \
  --task-definition web-app-task:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678],assignPublicIp=ENABLED}"
```

#### 6단계: 서비스 상태 확인
```bash
# 서비스 상태 확인
aws ecs describe-services --cluster my-web-cluster --services web-service

# 태스크 상태 확인
aws ecs list-tasks --cluster my-web-cluster --service-name web-service
```

### 5.3 배포 후 확인사항 ✅

**확인해야 할 항목:**
- ✅ 서비스가 정상적으로 실행 중인지
- ✅ 태스크가 원하는 수만큼 실행 중인지
- ✅ 로그가 정상적으로 출력되는지
- ✅ 외부에서 접근 가능한지

---

## 6. CI/CD 파이프라인 구축 🔄

### 6.1 GitHub Actions와 ECS 연동

```yaml
name: Deploy to ECS

on:
  push:
    branches:
      - main

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: my-web-app
  ECS_CLUSTER: my-web-cluster
  ECS_SERVICE: web-service
  ECS_TASK_DEFINITION: web-app-task

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
        
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
          
      - name: Download task definition
        run: |
          aws ecs describe-task-definition --task-definition ${{ env.ECS_TASK_DEFINITION }} \
          --query taskDefinition > task-definition.json
          
      - name: Update task definition
        run: |
          sed -i "s|<IMAGE>|${{ steps.build-image.outputs.image }}|g" task-definition.json
          
      - name: Register new task definition
        run: |
          aws ecs register-task-definition --cli-input-json file://task-definition.json
          
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster ${{ env.ECS_CLUSTER }} --service ${{ env.ECS_SERVICE }} --force-new-deployment
```

### 6.2 배포 전략 🎯

#### Blue-Green 배포
- 새 버전을 별도 환경에 배포
- 테스트 후 트래픽 전환
- 롤백이 쉬움

#### Rolling 배포
- 점진적으로 새 버전으로 교체
- 서비스 중단 없음
- 리소스 효율적

---

## 7. 비용 및 보안 💰🔒

### 7.1 비용 구조

#### Fargate 요금
- **CPU**: vCPU 시간당 요금
- **메모리**: GB 시간당 요금
- **예시**: 1 vCPU, 2GB 메모리 = 약 $0.04/시간

#### EC2 요금
- **인스턴스 타입**: 선택한 EC2 인스턴스 요금
- **스토리지**: EBS 볼륨 요금
- **네트워크**: 데이터 전송 요금

### 7.2 비용 최적화 팁 💡

| **최적화 방법** | **설명** |
|----------------|----------|
| **리소스 최적화** | 실제 사용량에 맞게 CPU/메모리 설정 |
| **예약 인스턴스** | 장기 사용 시 예약 인스턴스 활용 |
| **Spot 인스턴스** | EC2 모드에서 Spot 인스턴스 사용 |
| **자동 스케일링** | 트래픽에 따라 자동으로 스케일링 |

### 7.3 보안 모범 사례 🔐

#### IAM 보안
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:UpdateService"
      ],
      "Resource": "arn:aws:ecs:region:account:service/cluster-name/service-name"
    }
  ]
}
```

#### 네트워크 보안
- ✅ **VPC 사용**: 프라이빗 서브넷에 배포
- ✅ **보안 그룹**: 최소 권한 원칙 적용
- ✅ **NACL**: 네트워크 액세스 제어
- ✅ **VPC 엔드포인트**: AWS 서비스 접근 최적화

#### 컨테이너 보안
- ✅ **이미지 스캔**: ECR 이미지 취약점 스캔
- ✅ **최신 이미지**: 정기적으로 베이스 이미지 업데이트
- ✅ **비밀번호 관리**: AWS Secrets Manager 사용
- ✅ **런타임 보안**: 컨테이너 내부 보안 모니터링

---

## 8. ECS vs EKS 비교 ⚖️

### 8.1 상세 비교표

| **구분** | **ECS** | **EKS** |
|----------|---------|---------|
| **관리 복잡성** | 🟢 낮음 | 🔴 높음 |
| **학습 곡선** | 🟢 완만함 | 🔴 가파름 |
| **AWS 통합** | 🟢 완벽함 | 🟡 부분적 |
| **커뮤니티** | 🟡 AWS 중심 | 🟢 글로벌 |
| **확장성** | 🟡 중간 | 🟢 높음 |
| **비용** | 🟢 낮음 | 🔴 높음 |
| **기능** | 🟡 기본적 | 🟢 풍부함 |

### 8.2 ECS와 EKS중 선택하는 방법

#### ECS를 선택하는 경우 ✅
- AWS 생태계에 집중
- 빠른 배포가 필요
- 쿠버네티스 지식이 부족
- 비용 효율성 중요
- 간단한 컨테이너 워크로드

#### EKS를 선택하는 경우 ✅
- 쿠버네티스 생태계 활용
- 복잡한 마이크로서비스
- 멀티 클라우드 전략
- 고급 오케스트레이션 기능 필요
- 대규모 팀 운영

---

## 9. 자주 묻는 질문 (FAQ) ❓

### Q1: ECS와 Docker의 차이점은?
**A:** Docker는 컨테이너 기술이고, ECS는 컨테이너를 관리하는 오케스트레이션 서비스입니다.

### Q2: Fargate와 EC2 중 어떤 것을 선택해야 할까요?
**A:** 
- **Fargate**: 서버 관리가 싫고, 빠른 시작이 필요할 때
- **EC2**: 비용 효율성과 완전한 제어가 필요할 때

### Q3: ECS에서 데이터베이스를 실행해도 될까요?
**A:** 개발/테스트 환경에서는 가능하지만, 프로덕션에서는 RDS 같은 관리형 서비스를 권장합니다.

### Q4: 컨테이너가 갑자기 중단되면 어떻게 되나요?
**A:** ECS 서비스가 자동으로 새로운 컨테이너를 시작하여 서비스 가용성을 유지합니다.

### Q5: 비용을 어떻게 모니터링할 수 있나요?
**A:** AWS Cost Explorer와 CloudWatch를 통해 상세한 비용 분석이 가능합니다.


---

## 🎯 결론

AWS ECS는 **컨테이너 기반 애플리케이션을 쉽고 효율적으로 배포할 수 있는 강력한 서비스**입니다. 

**주요 장점:**
- 🚀 **간편한 배포**: 복잡한 인프라 관리 없이 컨테이너 실행
- 🔄 **자동 관리**: 스케일링, 헬스체크, 배포 자동화
- 💰 **비용 효율성**: 사용한 만큼만 과금
- 🔒 **보안**: AWS의 보안 인프라 활용


