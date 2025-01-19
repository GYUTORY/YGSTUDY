
# ☁️ AWS EKS (Elastic Kubernetes Service) 완벽 가이드

---

## 1. AWS EKS란?
**AWS EKS (Elastic Kubernetes Service)**는 Amazon Web Services에서 제공하는 **완전관리형 Kubernetes 서비스**입니다.  
EKS를 사용하면 사용자가 직접 Kubernetes 클러스터를 설치하고 관리할 필요 없이,  
AWS가 인프라를 관리해주며, 사용자는 Kubernetes 리소스만 집중적으로 관리할 수 있습니다.

---

### 👉🏻 EKS의 주요 특징
- **완전관리형 Kubernetes**: Kubernetes 컨트롤 플레인을 AWS에서 관리.
- **고가용성 및 확장성**: 멀티 AZ 아키텍처 제공.
- **네이티브 Kubernetes 지원**: `kubectl`, Helm과 같은 표준 도구 지원.
- **다양한 런타임 지원**: EC2와 Fargate 기반의 클러스터 지원.
- **통합 보안**: IAM, VPC, Security Groups 통합.

---

## 2. EKS의 구성 요소 📦
- **EKS 클러스터**: Kubernetes 클러스터의 컨트롤 플레인을 관리.
- **노드 그룹(Node Group)**: EC2 또는 Fargate 기반의 워커 노드 그룹.
- **Pod**: Kubernetes에서 배포되는 최소 실행 단위.
- **서비스(Service)**: Pod의 네트워크 접근을 관리.
- **로드 밸런서(Load Balancer)**: 외부 트래픽을 관리.

---

## 3. EKS 사용 예제 🛠️
### 📦 사전 준비
- AWS CLI, `eksctl` 설치 및 구성 (`aws configure`)
- `kubectl` 설치 및 구성
- AWS 계정 및 IAM 권한 설정

---

### 📂 3.1 EKS 클러스터 생성
```bash
eksctl create cluster --name my-eks-cluster --region ap-northeast-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3
```

---

### 📥 3.2 `kubectl` 클러스터 연결 확인
```bash
aws eks --region ap-northeast-2 update-kubeconfig --name my-eks-cluster
kubectl get nodes
```

---

### 📄 3.3 Kubernetes 애플리케이션 배포 (nginx 예제)
```yaml
# nginx-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
```

```bash
kubectl apply -f nginx-deployment.yaml
kubectl get pods
```

---

### 🌐 3.4 서비스 생성 (로드 밸런서 포함)
```yaml
# nginx-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 80
  selector:
    app: nginx
```

```bash
kubectl apply -f nginx-service.yaml
kubectl get svc
```

---

### 🧹 3.5 EKS 클러스터 삭제
```bash
eksctl delete cluster --name my-eks-cluster
```

---

## 4. EKS와 CI/CD 연동 🌐
### 예제: GitHub Actions와 AWS EKS 배포
```yaml
name: Deploy to EKS

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

      - name: Configure kubectl
        run: |
          aws eks --region ap-northeast-2 update-kubeconfig --name my-eks-cluster

      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f nginx-deployment.yaml
          kubectl apply -f nginx-service.yaml
```

---

## 5. EKS 비용 및 보안
### 💰 비용
- **제어 플레인 요금**: 클러스터당 시간당 비용 발생
- **노드 요금**: EC2 및 Fargate 사용량에 따른 요금 발생

### 🔒 보안 모범 사례
- **IAM 최소 권한 원칙 적용**
- **Pod 보안 정책 활용**
- **네트워크 정책 적용 (VPC 및 Security Group)**

---

## 6. EKS와 ECS의 비교
| **특징**                   | **EKS**                  | **ECS**                |
|:---------------------------|:-------------------------|:-----------------------|
| **관리 방식**              | Kubernetes 기반 관리     | AWS 자체 관리형       |
| **사용 편의성**            | 복잡함 (쿠버네티스 필요) | 간편함                |
| **서버리스 지원**          | Fargate 사용 가능        | Fargate 사용 가능      |
| **주요 용도**              | 대규모 컨테이너 관리      | 단순 컨테이너 배포     |
| **커뮤니티**               | 글로벌 오픈소스 커뮤니티 | AWS 중심 커뮤니티      |

---

## 7. 결론 ✅
- **AWS EKS**는 완전관리형 **Kubernetes 서비스**로, 대규모 컨테이너 관리에 적합합니다.
- **EC2 및 Fargate** 기반으로 다양한 배포 방식을 지원합니다.
- **CI/CD 파이프라인**과 연동하여 Kubernetes 기반 애플리케이션을 손쉽게 배포할 수 있습니다.
