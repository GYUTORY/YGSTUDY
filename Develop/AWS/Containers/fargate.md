
# AWS Fargate

---

## 1. AWS Fargate란?
**AWS Fargate**는 Amazon Web Services에서 제공하는 **서버리스 컨테이너 실행 서비스**입니다.  
서버를 관리하지 않고도 **ECS**와 **EKS**를 통해 컨테이너를 배포하고 실행할 수 있습니다.

---

### 👉🏻 Fargate의 주요 특징
- **서버리스 컨테이너 서비스**: 인프라를 관리할 필요 없이 컨테이너를 실행할 수 있습니다.
- **자동 확장 지원**: 트래픽에 따라 자동으로 리소스를 조정합니다.
- **보안 강화**: AWS VPC와 IAM을 통해 보안 제어.
- **비용 효율적**: 사용한 CPU 및 메모리만큼 과금.

---

## 2. Fargate의 구성 요소 📦
- **클러스터(Cluster)**: ECS나 EKS에서 Fargate를 사용하는 경우 생성.
- **태스크(Task)**: 실행되는 컨테이너의 최소 단위.
- **태스크 정의(Task Definition)**: 태스크의 설정을 정의하는 JSON 파일.
- **서비스(Service)**: 특정 수의 태스크를 유지하고 관리하는 엔터티.

---

## 3. Fargate 사용 예제 🛠️ (ECS 기반)
### 📦 사전 준비
- AWS CLI 설치 및 구성 (`aws configure`)
- Docker 설치 및 실행
- ECR 리포지터리 생성 및 Docker 이미지 업로드 (이전 가이드 참고)

---

### 📂 3.1 ECS 클러스터 생성 (Fargate)
```bash
aws ecs create-cluster --cluster-name fargate-cluster
```

---

### 📄 3.2 태스크 정의 생성 (`task-def.json`)
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
      ]
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512"
}
```

```bash
aws ecs register-task-definition --cli-input-json file://task-def.json
```

---

### 🚀 3.3 ECS 서비스 생성 (Fargate 기반)
```bash
aws ecs create-service     --cluster fargate-cluster     --service-name fargate-service     --task-definition fargate-task     --desired-count 2     --launch-type FARGATE     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}"
```

---

### 📊 3.4 ECS 서비스 상태 확인
```bash
aws ecs describe-services --cluster fargate-cluster --services fargate-service
```

---

### 🧹 3.5 Fargate 서비스 및 클러스터 삭제
```bash
aws ecs delete-service --cluster fargate-cluster --service fargate-service --force
aws ecs delete-cluster --cluster fargate-cluster
```

---

## 4. Fargate와 CI/CD 연동 🌐
### 예제: GitHub Actions와 Fargate 배포
```yaml
name: Deploy to Fargate

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

      - name: Deploy to Fargate
        run: |
          aws ecs update-service --cluster fargate-cluster --service fargate-service --force-new-deployment
```

---

## 5. Fargate 비용 및 보안
### 💰 비용
- **CPU 및 메모리 사용량**에 따라 과금.
- **사용한 리소스만 요금 부과** (서버리스 아키텍처).

### 🔒 보안 모범 사례
- **IAM 최소 권한 부여**
- **VPC 엔드포인트 사용**
- **ECR 이미지 스캔 활성화**

---

## 6. Fargate와 ECS/EKS 비교
| **특징**                   | **Fargate**              | **ECS**                  | **EKS**                   |
|:---------------------------|:------------------------|:------------------------|:-------------------------|
| **관리 방식**              | 서버리스                | 관리형 인프라          | Kubernetes 기반 관리   |
| **사용 편의성**            | 간편함                 | 다소 복잡함            | 복잡함 (K8s 지식 필요)|
| **서버리스 지원**          | 전용                    | 선택 가능 (Fargate 지원)| 선택 가능 (Fargate 지원)|
| **주요 용도**              | 소규모, 빠른 배포        | 중간 규모, 제어 필요   | 대규모 컨테이너 관리   |
| **비용**                   | 사용량 기반 과금         | EC2 인스턴스 비용 기반 | 제어 플레인 + 워커 노드 비용 |

---

## 7. 결론 ✅
- **AWS Fargate**는 인프라를 관리하지 않고 컨테이너를 배포할 수 있는 서버리스 서비스입니다.
- **ECS 및 EKS**와 통합되어 사용할 수 있으며, **서버리스 아키텍처**에 적합합니다.
- **비용 효율적**이고 **보안 강화**가 되어 있어, 소규모 및 중간 규모의 애플리케이션에 적합합니다.
