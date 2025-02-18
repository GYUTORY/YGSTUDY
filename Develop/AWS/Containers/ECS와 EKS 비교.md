# 🚀 AWS ECS vs EKS 비교 가이드

---

## 1. 개요 ✨

AWS에서 **컨테이너 오케스트레이션(Container Orchestration)**을 제공하는 두 가지 주요 서비스가 있습니다.

- **ECS (Elastic Container Service)** 👉🏻 AWS의 자체 컨테이너 관리 서비스
- **EKS (Elastic Kubernetes Service)** 👉🏻 Kubernetes 기반의 컨테이너 관리 서비스

이 두 서비스는 각각 **컨테이너 애플리케이션을 배포하고 운영**하는 데 사용되지만, **사용 방식과 특징이 다릅니다.**  
이번 가이드를 통해 **ECS와 EKS의 차이점을 이해하고, 언제 어떤 서비스를 선택하면 좋은지 알아보겠습니다.**

---

## 2. ECS (Elastic Container Service)

**ECS**는 AWS가 제공하는 **완전 관리형 컨테이너 오케스트레이션 서비스**입니다.  
사용자는 별도의 컨트롤 플레인(Control Plane)을 관리하지 않고도 **AWS Fargate** 또는 **EC2 인스턴스**에서 컨테이너를 실행할 수 있습니다.

### ✅ **ECS의 주요 특징**

1. **AWS 네이티브 서비스**로, AWS 인프라와 완벽하게 통합
2. **Fargate**를 사용하면 서버를 직접 관리하지 않고 컨테이너 실행 가능
3. EC2 기반 클러스터를 사용할 수도 있음
4. 자동 스케일링(Auto Scaling) 및 로드 밸런싱 지원
5. **IAM(Identity & Access Management)과 통합**되어 보안 및 권한 관리 가능

### 🔹 **ECS 아키텍처 개념도**

```
[사용자 요청] → [ALB (로드 밸런서)] → [ECS 클러스터] → [ECS 서비스] → [ECS 태스크 (컨테이너)]
```

---

## 3. EKS (Elastic Kubernetes Service)

**EKS**는 **AWS에서 제공하는 Kubernetes 관리 서비스**입니다.  
Kubernetes는 컨테이너를 자동으로 배포, 관리, 확장하는 오픈소스 오케스트레이션 시스템입니다.

### ✅ **EKS의 주요 특징**

1. **표준 Kubernetes API 지원**으로 멀티 클라우드 환경에서도 사용 가능
2. 클러스터 운영을 위한 **마스터 노드(Control Plane)를 AWS에서 관리**
3. EC2 노드 그룹 또는 **Fargate 기반의 서버리스 컨테이너 실행 가능**
4. Kubernetes의 **Pod, Deployment, Service 등을 활용**하여 복잡한 앱 배포 가능
5. **Helm, Istio, Prometheus 등 다양한 Kubernetes 생태계 툴과 연동 가능**

### 🔹 **EKS 아키텍처 개념도**

```
[사용자 요청] → [ALB (로드 밸런서)] → [EKS 클러스터] → [Kubernetes Deployment] → [Pod (컨테이너)]
```

---

## 4. ECS vs EKS 비교 🔍

| 비교 항목 | ECS (Elastic Container Service) | EKS (Elastic Kubernetes Service) |
|----------|--------------------------------|--------------------------------|
| **관리 방식** | AWS 자체 관리형 컨테이너 오케스트레이션 | Kubernetes 기반 오케스트레이션 |
| **컨테이너 실행 방식** | AWS Fargate 또는 EC2 기반 | EC2 노드 그룹 또는 Fargate |
| **학습 곡선** | 쉬움 (AWS 네이티브) | 어려움 (Kubernetes 개념 필요) |
| **확장성** | AWS 환경 내에서 우수 | 멀티 클라우드 및 하이브리드 가능 |
| **사용 사례** | 간단한 컨테이너 애플리케이션 | 복잡한 마이크로서비스 아키텍처 |
| **로드 밸런싱** | ALB, NLB, 서비스 디스커버리 | ALB, NLB, Ingress Controller |
| **비용** | 상대적으로 저렴 | Kubernetes 운영 비용 추가 |
| **배포 도구** | AWS CLI, CloudFormation | kubectl, Helm, Terraform |

📌 **간단한 컨테이너 실행은 ECS가 더 적합하며, 복잡한 마이크로서비스와 멀티 클라우드 환경이 필요하면 EKS를 선택하는 것이 좋습니다.**

---

## 5. ECS와 EKS 예제 코드

### **5.1 ECS에서 Fargate를 사용한 컨테이너 실행**

```json
{
  "family": "sample-task",
  "containerDefinitions": [
    {
      "name": "sample-container",
      "image": "nginx",
      "memory": 512,
      "cpu": 256,
      "essential": true
    }
  ],
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "cpu": "256",
  "memory": "512"
}
```

> 🔹 **설명**
> - `family`: 태스크 정의 이름
> - `image`: 실행할 Docker 이미지
> - `networkMode`: `awsvpc`를 사용하여 VPC 네트워크 연결
> - `requiresCompatibilities`: `FARGATE`를 지정하여 서버리스 실행

---

### **5.2 EKS에서 Kubernetes Deployment 배포**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sample
  template:
    metadata:
      labels:
        app: sample
    spec:
      containers:
        - name: sample-container
          image: nginx
          ports:
            - containerPort: 80
```

> 🔹 **설명**
> - `replicas`: 3개의 Pod을 실행
> - `selector`: 특정 라벨이 있는 Pod을 선택
> - `containers`: Nginx 컨테이너를 실행하고 80번 포트 노출

---

## 6. ECS와 EKS 선택 가이드 🎯

✅ **ECS를 선택해야 할 때**
- AWS 네이티브 서비스만 사용할 경우
- 간단한 컨테이너 배포 및 관리가 필요할 때
- Kubernetes 학습 없이 빠르게 컨테이너 운영을 원할 때

✅ **EKS를 선택해야 할 때**
- 멀티 클라우드(Kubernetes 기반 인프라)가 필요할 때
- 복잡한 마이크로서비스 아키텍처를 구축할 때
- Helm, Istio, Prometheus 등 Kubernetes 생태계를 활용하고 싶을 때

📌 **ECS는 단순성과 AWS 환경에 최적화된 서비스**이며, **EKS는 Kubernetes 생태계를 활용한 확장성이 뛰어난 서비스**입니다. 🚀

