# AWS Fargate 🚀

> **서버리스 컨테이너 실행 서비스로 인프라 관리 없이 컨테이너를 배포하고 실행할 수 있는 AWS 서비스**

---

## 📋 목차
- [1. AWS Fargate란?](#1-aws-fargate란)
- [2. 핵심 용어 정리](#2-핵심-용어-정리)
- [3. Fargate의 구성 요소](#3-fargate의-구성-요소)
- [4. Fargate 사용 예제](#4-fargate-사용-예제)
- [5. Fargate와 CI/CD 연동](#5-fargate와-cicd-연동)
- [6. 비용 및 보안](#6-비용-및-보안)
- [7. Fargate vs ECS vs EKS 비교](#7-fargate-vs-ecs-vs-eks-비교)
- [8. 결론](#8-결론)

---

## 1. AWS Fargate란? 🤔

### 1.1 기본 개념
**AWS Fargate**는 Amazon Web Services에서 제공하는 **서버리스 컨테이너 실행 서비스**입니다.

> 💡 **서버리스(Serverless)란?**
> - 서버를 직접 관리하지 않아도 되는 서비스
> - 사용한 만큼만 비용을 지불하는 방식
> - 인프라 관리 부담 없이 애플리케이션에만 집중 가능

### 1.2 Fargate의 핵심 가치
- ✅ **서버 관리 불필요**: EC2 인스턴스를 직접 관리할 필요 없음
- ✅ **자동 확장**: 트래픽에 따라 자동으로 리소스 조정
- ✅ **보안 강화**: AWS VPC와 IAM을 통한 보안 제어
- ✅ **비용 효율**: 사용한 CPU 및 메모리만큼 과금

---

## 2. 핵심 용어 정리 📚

### 2.1 컨테이너 관련 용어
| 용어 | 설명 |
|------|------|
| **컨테이너(Container)** | 애플리케이션과 그 실행에 필요한 모든 파일을 포함한 패키지 |
| **Docker** | 컨테이너를 만들고 실행하는 플랫폼 |
| **이미지(Image)** | 컨테이너를 만들기 위한 템플릿 |
| **컨테이너화(Containerization)** | 애플리케이션을 컨테이너로 패키징하는 과정 |

### 2.2 AWS 서비스 관련 용어
| 용어 | 설명 |
|------|------|
| **ECS (Elastic Container Service)** | AWS의 관리형 컨테이너 오케스트레이션 서비스 |
| **EKS (Elastic Kubernetes Service)** | AWS의 관리형 Kubernetes 서비스 |
| **ECR (Elastic Container Registry)** | AWS의 Docker 이미지 저장소 |
| **VPC (Virtual Private Cloud)** | AWS 클라우드 내의 격리된 네트워크 환경 |

### 2.3 서버리스 관련 용어
| 용어 | 설명 |
|------|------|
| **서버리스(Serverless)** | 서버를 직접 관리하지 않는 컴퓨팅 모델 |
| **함수형 서비스** | Lambda처럼 함수 단위로 실행되는 서비스 |
| **컨테이너형 서비스** | Fargate처럼 컨테이너 단위로 실행되는 서비스 |

---

## 3. Fargate의 구성 요소 📦

### 3.1 클러스터(Cluster) 🏢
> **정의**: ECS나 EKS에서 Fargate를 사용할 때 생성되는 논리적 그룹

**특징:**
- 여러 컨테이너를 논리적으로 그룹화
- 리소스 관리 및 모니터링의 단위
- 보안 및 네트워크 설정을 공유

### 3.2 태스크(Task) 📋
> **정의**: 실행되는 컨테이너의 최소 단위

**특징:**
- 하나 이상의 컨테이너로 구성 가능
- 독립적인 실행 환경
- 고유한 IP 주소와 리소스 할당

### 3.3 태스크 정의(Task Definition) ⚙️
> **정의**: 태스크의 설정을 정의하는 JSON 파일

**주요 설정 항목:**
```json
{
  "family": "태스크 패밀리명",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "컨테이너명",
      "image": "Docker 이미지 URI",
      "memory": 512,
      "cpu": 256,
      "portMappings": [
        {
          "containerPort": 80,
          "hostPort": 80
        }
      ]
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512"
}
```

### 3.4 서비스(Service) 🔄
> **정의**: 특정 수의 태스크를 유지하고 관리하는 엔터티

**기능:**
- 원하는 태스크 수 유지
- 자동 확장/축소
- 로드 밸런싱
- 헬스 체크

---

## 4. Fargate 사용 예제 🛠️

### 4.1 사전 준비 체크리스트 ✅
- [ ] AWS CLI 설치 및 구성 (`aws configure`)
- [ ] Docker 설치 및 실행
- [ ] ECR 리포지터리 생성
- [ ] Docker 이미지 빌드 및 ECR 업로드

### 4.2 단계별 실습 가이드

#### 📂 Step 1: ECS 클러스터 생성 (Fargate)
```bash
# Fargate 전용 클러스터 생성
aws ecs create-cluster --cluster-name fargate-cluster
```

**명령어 설명:**
- `aws ecs create-cluster`: ECS 클러스터를 생성하는 명령어
- `--cluster-name`: 생성할 클러스터의 이름 지정

#### 📄 Step 2: 태스크 정의 생성
**파일명**: `task-definition.json`

```json
{
  "family": "fargate-task",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "my-app-container",
      "image": "<AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo:latest",
      "memory": 512,
      "cpu": 256,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 80,
          "hostPort": 80
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/fargate-task",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<AWS_ACCOUNT_ID>:role/ecsTaskExecutionRole"
}
```

**주요 설정 항목 설명:**
- `family`: 태스크 정의의 고유 이름
- `networkMode`: 네트워크 모드 (awsvpc는 Fargate에서 필수)
- `memory`: 메모리 할당량 (MB)
- `cpu`: CPU 할당량 (CPU 단위, 1024 = 1 vCPU)
- `essential`: 태스크에서 필수 컨테이너 여부
- `portMappings`: 포트 매핑 설정

```bash
# 태스크 정의 등록
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 🚀 Step 3: ECS 서비스 생성 (Fargate 기반)
```bash
aws ecs create-service \
  --cluster fargate-cluster \
  --service-name fargate-service \
  --task-definition fargate-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}"
```

**명령어 매개변수 설명:**
- `--cluster`: 서비스를 생성할 클러스터명
- `--service-name`: 생성할 서비스의 이름
- `--task-definition`: 사용할 태스크 정의
- `--desired-count`: 유지할 태스크 수
- `--launch-type`: FARGATE 지정
- `--network-configuration`: 네트워크 설정 (서브넷, 보안그룹 등)

#### 📊 Step 4: 서비스 상태 확인
```bash
# 서비스 상태 조회
aws ecs describe-services \
  --cluster fargate-cluster \
  --services fargate-service

# 태스크 상태 조회
aws ecs list-tasks \
  --cluster fargate-cluster \
  --service-name fargate-service
```

#### 🧹 Step 5: 리소스 정리
```bash
# 서비스 삭제
aws ecs delete-service \
  --cluster fargate-cluster \
  --service fargate-service \
  --force

# 클러스터 삭제
aws ecs delete-cluster \
  --cluster fargate-cluster
```

---

## 5. Fargate와 CI/CD 연동 🌐

### 5.1 CI/CD 파이프라인 구성도
```
코드 변경 → GitHub → GitHub Actions → ECR → Fargate 배포
```

### 5.2 GitHub Actions 워크플로우 예제
**파일명**: `.github/workflows/deploy-fargate.yml`

```yaml
name: Deploy to Fargate

on:
  push:
    branches:
      - main

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: my-app-repo
  ECS_CLUSTER: fargate-cluster
  ECS_SERVICE: fargate-service
  ECS_TASK_DEFINITION: fargate-task

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
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

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment
```

### 5.3 CI/CD 설정 시 주의사항 ⚠️
- **보안**: AWS 자격 증명을 GitHub Secrets에 안전하게 저장
- **권한**: ECS, ECR, IAM 권한이 적절히 설정되어야 함
- **롤백**: 배포 실패 시 이전 버전으로 되돌릴 수 있는 전략 필요

---

## 6. 비용 및 보안 💰🔒

### 6.1 비용 구조 💰
**Fargate 비용 = CPU 비용 + 메모리 비용 + 네트워킹 비용**

#### CPU 및 메모리 비용 (ap-northeast-2 기준)
| 리소스 | 비용 |
|--------|------|
| CPU (vCPU) | $0.04048 per vCPU per hour |
| 메모리 (GB) | $0.004445 per GB per hour |

#### 예시 계산
```
2 vCPU + 4GB 메모리 사용 시:
- CPU: 2 × $0.04048 = $0.08096/hour
- 메모리: 4 × $0.004445 = $0.01778/hour
- 총 비용: $0.09874/hour ≈ $72.89/month
```

### 6.2 보안 모범 사례 🔒

#### IAM 보안
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

#### 네트워크 보안
- **VPC 엔드포인트 사용**: AWS 서비스와의 통신을 VPC 내부에서 처리
- **보안 그룹 최소 권한**: 필요한 포트만 열어두기
- **Private 서브넷 사용**: 외부 직접 접근 차단

#### 컨테이너 보안
- **ECR 이미지 스캔 활성화**: 취약점 자동 검사
- **최신 베이스 이미지 사용**: 보안 패치 적용
- **루트 사용자 비활성화**: 컨테이너 내에서 최소 권한 사용

---

## 7. Fargate vs ECS vs EKS 비교 📊

### 7.1 상세 비교표

| **특징** | **Fargate** | **ECS (EC2)** | **EKS** |
|:---------|:------------|:--------------|:--------|
| **관리 방식** | 🟢 서버리스 | 🟡 관리형 인프라 | 🔴 Kubernetes 기반 |
| **사용 편의성** | 🟢 매우 간편 | 🟡 보통 | 🔴 복잡 (K8s 지식 필요) |
| **서버리스 지원** | 🟢 전용 | 🟡 선택 가능 | 🟡 선택 가능 |
| **제어 수준** | 🟡 제한적 | 🟢 높음 | 🟢 매우 높음 |
| **비용 효율성** | 🟢 사용량 기반 | 🟡 인스턴스 기반 | 🔴 제어 플레인 + 워커 비용 |
| **학습 곡선** | 🟢 낮음 | 🟡 보통 | 🔴 높음 |
| **대규모 운영** | 🟡 적합 | 🟢 매우 적합 | 🟢 매우 적합 |

### 7.2 Fargate, ECS, EKS 중 선택하는 방법 🎯

#### Fargate 선택 시기 ✅
- **소규모 ~ 중간 규모** 애플리케이션
- **빠른 배포**가 필요한 경우
- **인프라 관리**를 원하지 않는 경우
- **비용 효율성**을 중시하는 경우

#### ECS (EC2) 선택 시기 ✅
- **세밀한 제어**가 필요한 경우
- **기존 EC2 인프라**와 통합이 필요한 경우
- **비용 최적화**를 위해 스팟 인스턴스 사용이 필요한 경우

#### EKS 선택 시기 ✅
- **대규모 컨테이너 관리**가 필요한 경우
- **Kubernetes 생태계** 활용이 필요한 경우
- **멀티 클라우드 전략**을 고려하는 경우

---

## 8. 결론 ✅

### 8.1 Fargate의 장점 🌟
- ✅ **인프라 관리 불필요**: 서버 프로비저닝, 패치, 보안 관리 자동화
- ✅ **자동 확장**: 트래픽에 따른 자동 스케일링
- ✅ **비용 효율**: 사용한 만큼만 과금
- ✅ **보안 강화**: AWS 보안 서비스와 통합
- ✅ **빠른 배포**: 몇 분 내에 컨테이너 배포 가능

### 8.2 적합한 사용 사례 🎯
- **웹 애플리케이션**: React, Vue, Angular 등 SPA
- **API 서비스**: REST API, GraphQL 서비스
- **마이크로서비스**: 작은 규모의 독립적인 서비스
- **배치 작업**: 주기적으로 실행되는 작업
- **개발/테스트 환경**: 빠른 프로토타이핑

