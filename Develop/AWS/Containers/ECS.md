
# AWS ECS (Elastic Container Service)

---

## 1. AWS ECS란?
**Amazon ECS (Elastic Container Service)**는 **완전관리형 컨테이너 오케스트레이션 서비스**로,  
Docker 컨테이너를 실행, 관리, 스케일링할 수 있도록 도와주는 AWS의 서비스입니다.

---

### 👉🏻 ECS의 주요 특징
- **서버리스 방식 지원**: `Fargate` 모드를 통해 서버리스로 컨테이너를 실행할 수 있습니다.
- **고가용성 및 확장성**: 컨테이너를 자동으로 확장하고 관리.
- **다중 배포 옵션**: EC2 및 Fargate를 통한 배포 지원.
- **다양한 통합**: ECR, CloudWatch, IAM, CodePipeline과의 원활한 통합.

---

## 2. ECS의 구성 요소 📦
- **클러스터(Cluster)**: 컨테이너를 실행하는 인프라의 논리적 그룹.
- **태스크(Task)**: 하나 이상의 컨테이너로 구성된 실행 단위.
- **태스크 정의(Task Definition)**: 태스크를 설명하는 JSON 기반의 템플릿.
- **서비스(Service)**: 특정 태스크를 일정 수량 유지 및 배포를 관리.
- **런타임 모드**:
   - **Fargate**: 서버리스 방식, 인프라 관리 불필요.
   - **EC2**: 사용자가 직접 EC2 인스턴스를 관리.

---

## 3. ECS 사용 예제 🛠️
### 📦 사전 준비
- AWS CLI 설치 및 구성 (`aws configure`)
- Docker 설치 및 실행

---

### 📂 3.1 ECS 클러스터 생성
```bash
aws ecs create-cluster --cluster-name my-ecs-cluster
```

---

### 📄 3.2 태스크 정의 생성 (`task-def.json`)
```json
{
  "family": "my-task",
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
      ]
    }
  ]
}
```

```bash
aws ecs register-task-definition --cli-input-json file://task-def.json
```

---

### 🚀 3.3 ECS 서비스 생성 (Fargate)
```bash
aws ecs create-service     --cluster my-ecs-cluster     --service-name my-ecs-service     --task-definition my-task     --desired-count 2     --launch-type FARGATE     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}"
```

---

### 📊 3.4 ECS 서비스 상태 확인
```bash
aws ecs describe-services --cluster my-ecs-cluster --services my-ecs-service
```

---

### 📥 3.5 서비스 삭제
```bash
aws ecs delete-service --cluster my-ecs-cluster --service my-ecs-service --force
```

---

## 4. ECS와 CI/CD 연동 🌐
### 예제: GitHub Actions와 ECS 배포
```yaml
name: Deploy to ECS

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

      - name: Build and Push Docker Image to ECR
        run: |
          aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com
          docker build -t my-app .
          docker tag my-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo
          docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/my-app-repo

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster my-ecs-cluster --service my-ecs-service --force-new-deployment
```

---

## 5. ECS 비용 및 보안
### 💰 비용
- **Fargate 요금**: 사용한 CPU 및 메모리 시간에 따라 과금
- **EC2 요금**: EC2 인스턴스 크기 및 사용량에 따라 과금

### 🔒 보안 모범 사례
- **IAM 최소 권한 원칙 적용**
- **VPC 및 프라이빗 서브넷 사용**
- **ECR 이미지 스캔 활성화**

---

## 6. ECS와 EKS의 비교
| **특징**                   | **ECS**                   | **EKS**                |
|:---------------------------|:--------------------------|:-----------------------|
| **관리 방식**              | AWS 자체 관리형          | Kubernetes 기반 관리 |
| **사용 편의성**            | 간편함                   | 복잡함 (쿠버네티스 지식 필요)|
| **서버리스 지원**          | Fargate 사용 가능         | Fargate 사용 가능     |
| **주요 용도**              | 단순 컨테이너 배포        | 대규모 컨테이너 오케스트레이션 |
| **커뮤니티**               | AWS 중심                 | 글로벌 오픈소스 커뮤니티 |

---

## 7. 결론 ✅
- **AWS ECS**는 간편하고 강력한 **컨테이너 오케스트레이션 서비스**입니다.
- **Fargate**를 사용하면 서버리스 방식으로 컨테이너를 실행할 수 있습니다.
- **CI/CD 파이프라인**과 쉽게 통합할 수 있어 개발과 배포를 자동화할 수 있습니다.
