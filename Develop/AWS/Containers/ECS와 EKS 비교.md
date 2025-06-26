# 🚀 AWS ECS vs EKS 비교 가이드

> 💡 **이 가이드를 읽기 전에 알아야 할 기본 개념**
> 
> **컨테이너(Container)**: 애플리케이션과 그 실행에 필요한 모든 파일을 포함한 패키지
> **오케스트레이션(Orchestration)**: 여러 컨테이너를 효율적으로 관리하고 배포하는 과정
> **클러스터(Cluster)**: 여러 서버를 하나의 그룹으로 묶어서 관리하는 시스템

---

## 📋 목차

1. [개요](#1-개요-)
2. [ECS (Elastic Container Service)](#2-ecs-elastic-container-service)
3. [EKS (Elastic Kubernetes Service)](#3-eks-elastic-kubernetes-service)
4. [ECS vs EKS 비교](#4-ecs-vs-eks-비교-)
5. [실제 예제 코드](#5-실제-예제-코드)
6. [선택 가이드](#6-선택-가이드-)

---

## 1. 개요 ✨

### 🎯 **이 가이드에서 배울 것**

AWS에서 **컨테이너 오케스트레이션(Container Orchestration)**을 제공하는 두 가지 주요 서비스에 대해 알아보겠습니다.

- **ECS (Elastic Container Service)** 👉🏻 AWS의 자체 컨테이너 관리 서비스
- **EKS (Elastic Kubernetes Service)** 👉🏻 Kubernetes 기반의 컨테이너 관리 서비스

### 🤔 **왜 컨테이너 오케스트레이션이 필요한가?**

> **전통적인 방식의 문제점:**
> - 서버마다 다른 환경 설정
> - 애플리케이션 배포 시 환경 차이로 인한 오류
> - 확장성 부족
> - 관리 복잡성

> **컨테이너 오케스트레이션의 장점:**
> - 일관된 환경에서 애플리케이션 실행
> - 자동 확장 및 복구
> - 효율적인 리소스 관리
> - 쉬운 배포 및 롤백

---

## 2. ECS (Elastic Container Service)

### 📖 **ECS란?**

**ECS**는 AWS가 제공하는 **완전 관리형 컨테이너 오케스트레이션 서비스**입니다.

> 💡 **완전 관리형이란?**
> AWS가 서버 관리, 패치, 보안 업데이트 등을 자동으로 처리해주는 서비스를 의미합니다.

### 🏗️ **ECS 아키텍처 구성 요소**

```
┌─────────────────────────────────────────────────────────────┐
│                    ECS 아키텍처 구조                          │
├─────────────────────────────────────────────────────────────┤
│  [사용자 요청]                                               │
│         ↓                                                   │
│  [ALB (Application Load Balancer)]                          │
│         ↓                                                   │
│  [ECS 클러스터]                                             │
│  ├── ECS 서비스 1                                           │
│  │   ├── 태스크 1 (컨테이너)                                │
│  │   ├── 태스크 2 (컨테이너)                                │
│  │   └── 태스크 3 (컨테이너)                                │
│  └── ECS 서비스 2                                           │
│      ├── 태스크 1 (컨테이너)                                │
│      └── 태스크 2 (컨테이너)                                │
└─────────────────────────────────────────────────────────────┘
```

### ✅ **ECS의 주요 특징**

| 특징 | 설명 |
|------|------|
| **AWS 네이티브 서비스** | AWS 인프라와 완벽하게 통합되어 최적화된 성능 제공 |
| **Fargate 지원** | 서버를 직접 관리하지 않고 컨테이너만 실행 가능 |
| **EC2 기반 실행** | 기존 EC2 인스턴스에서도 컨테이너 실행 가능 |
| **자동 스케일링** | 트래픽에 따라 자동으로 컨테이너 수 조절 |
| **IAM 통합** | AWS의 권한 관리 시스템과 완벽 통합 |

### 🔧 **ECS 실행 방식**

#### **1. Fargate 방식 (서버리스)**
> 💡 **서버리스란?**
> 서버를 직접 관리하지 않고, 사용한 만큼만 비용을 지불하는 방식

```json
{
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512"
}
```

#### **2. EC2 방식 (서버 관리)**
```json
{
  "requiresCompatibilities": ["EC2"],
  "cpu": "256",
  "memory": "512"
}
```

---

## 3. EKS (Elastic Kubernetes Service)

### 📖 **EKS란?**

**EKS**는 **AWS에서 제공하는 Kubernetes 관리 서비스**입니다.

> 💡 **Kubernetes란?**
> 구글이 개발한 오픈소스 컨테이너 오케스트레이션 플랫폼으로, 
> 컨테이너를 자동으로 배포, 관리, 확장하는 시스템입니다.

### 🏗️ **EKS 아키텍처 구성 요소**

```
┌─────────────────────────────────────────────────────────────┐
│                    EKS 아키텍처 구조                          │
├─────────────────────────────────────────────────────────────┤
│  [사용자 요청]                                               │
│         ↓                                                   │
│  [ALB (Application Load Balancer)]                          │
│         ↓                                                   │
│  [EKS 클러스터]                                             │
│  ├── Control Plane (AWS 관리)                               │
│  └── Worker Nodes                                           │
│      ├── Pod 1 (컨테이너 그룹)                              │
│      │   ├── 컨테이너 1                                     │
│      │   └── 컨테이너 2                                     │
│      ├── Pod 2 (컨테이너 그룹)                              │
│      └── Pod 3 (컨테이너 그룹)                              │
└─────────────────────────────────────────────────────────────┘
```

### ✅ **EKS의 주요 특징**

| 특징 | 설명 |
|------|------|
| **표준 Kubernetes API** | 멀티 클라우드 환경에서도 동일한 방식으로 사용 가능 |
| **AWS 관리형 Control Plane** | 마스터 노드 관리는 AWS가 담당 |
| **Fargate 지원** | 서버리스 방식으로 Pod 실행 가능 |
| **풍부한 생태계** | Helm, Istio, Prometheus 등 다양한 도구 활용 가능 |
| **고급 기능** | Pod, Deployment, Service 등 Kubernetes 고급 기능 사용 |

### 🔧 **Kubernetes 핵심 개념**

#### **1. Pod**
> 💡 **Pod란?**
> Kubernetes에서 관리하는 가장 작은 단위로, 하나 이상의 컨테이너를 포함합니다.

#### **2. Deployment**
> 💡 **Deployment란?**
> Pod의 배포와 관리를 담당하는 리소스로, 롤링 업데이트, 롤백 등을 지원합니다.

#### **3. Service**
> 💡 **Service란?**
> Pod에 대한 네트워크 접근을 제공하는 추상화 계층입니다.

---

## 4. ECS vs EKS 비교 🔍

### 📊 **상세 비교표**

| 비교 항목 | ECS (Elastic Container Service) | EKS (Elastic Kubernetes Service) |
|----------|--------------------------------|--------------------------------|
| **관리 방식** | AWS 자체 관리형 컨테이너 오케스트레이션 | Kubernetes 기반 오케스트레이션 |
| **컨테이너 실행 방식** | AWS Fargate 또는 EC2 기반 | EC2 노드 그룹 또는 Fargate |
| **학습 곡선** | ⭐⭐ 쉬움 (AWS 네이티브) | ⭐⭐⭐⭐ 어려움 (Kubernetes 개념 필요) |
| **확장성** | AWS 환경 내에서 우수 | 멀티 클라우드 및 하이브리드 가능 |
| **사용 사례** | 간단한 컨테이너 애플리케이션 | 복잡한 마이크로서비스 아키텍처 |
| **로드 밸런싱** | ALB, NLB, 서비스 디스커버리 | ALB, NLB, Ingress Controller |
| **비용** | 💰💰 상대적으로 저렴 | 💰💰💰 Kubernetes 운영 비용 추가 |
| **배포 도구** | AWS CLI, CloudFormation | kubectl, Helm, Terraform |

### 🎯 **언제 어떤 것을 선택할까?**

#### **ECS를 선택해야 할 때** ✅
- 🏠 **AWS 네이티브 서비스만 사용할 경우**
- 🚀 **간단한 컨테이너 배포 및 관리가 필요할 때**
- 📚 **Kubernetes 학습 없이 빠르게 컨테이너 운영을 원할 때**
- 💰 **비용 효율성이 중요할 때**

#### **EKS를 선택해야 할 때** ✅
- 🌍 **멀티 클라우드(Kubernetes 기반 인프라)가 필요할 때**
- 🏗️ **복잡한 마이크로서비스 아키텍처를 구축할 때**
- 🛠️ **Helm, Istio, Prometheus 등 Kubernetes 생태계를 활용하고 싶을 때**
- 📈 **장기적인 확장성을 고려할 때**

---

## 5. 실제 예제 코드

### **5.1 ECS에서 Fargate를 사용한 컨테이너 실행**

```json
{
  "family": "sample-task",
  "containerDefinitions": [
    {
      "name": "sample-container",
      "image": "nginx:latest",
      "memory": 512,
      "cpu": 256,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sample-task",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "cpu": "256",
  "memory": "512"
}
```

> 🔹 **코드 설명**
> - `family`: 태스크 정의의 고유 이름
> - `image`: 실행할 Docker 이미지 (Nginx 웹서버)
> - `memory`, `cpu`: 컨테이너에 할당할 리소스
> - `networkMode`: `awsvpc`를 사용하여 VPC 네트워크 연결
> - `requiresCompatibilities`: `FARGATE`를 지정하여 서버리스 실행
> - `portMappings`: 컨테이너 포트를 호스트에 노출
> - `logConfiguration`: CloudWatch 로그 설정

---

### **5.2 EKS에서 Kubernetes Deployment 배포**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  labels:
    app: sample
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
          image: nginx:latest
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "250m"
            limits:
              memory: "128Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sample-service
spec:
  selector:
    app: sample
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: LoadBalancer
```

> 🔹 **코드 설명**
> - `replicas`: 3개의 Pod을 실행하여 고가용성 보장
> - `selector`: 특정 라벨이 있는 Pod을 선택
> - `containers`: Nginx 컨테이너를 실행하고 80번 포트 노출
> - `resources`: 컨테이너에 할당할 CPU와 메모리 리소스
> - `livenessProbe`: 컨테이너가 살아있는지 확인하는 헬스체크
> - `readinessProbe`: 컨테이너가 요청을 받을 준비가 되었는지 확인
> - `Service`: Pod에 대한 네트워크 접근을 제공하는 로드밸런서

---

## 6. 선택 가이드 🎯

### 🎯 **결정 트리**

```
시작
  ↓
AWS만 사용하나요?
  ↓ 예 → ECS 선택
  ↓ 아니오
멀티 클라우드를 고려하나요?
  ↓ 예 → EKS 선택
  ↓ 아니오
팀에 Kubernetes 경험이 있나요?
  ↓ 예 → EKS 선택
  ↓ 아니오
빠른 배포가 우선순위인가요?
  ↓ 예 → ECS 선택
  ↓ 아니오
복잡한 마이크로서비스가 필요하나요?
  ↓ 예 → EKS 선택
  ↓ 아니오 → ECS 선택
```

### 📋 **체크리스트**

#### **ECS 선택 체크리스트** ✅
- [ ] AWS 환경에서만 운영 예정
- [ ] 간단한 컨테이너 애플리케이션
- [ ] 빠른 배포가 필요
- [ ] Kubernetes 학습 시간이 부족
- [ ] 비용 효율성이 중요

#### **EKS 선택 체크리스트** ✅
- [ ] 멀티 클라우드 환경 고려
- [ ] 복잡한 마이크로서비스 아키텍처
- [ ] Kubernetes 생태계 활용 계획
- [ ] 팀에 Kubernetes 경험자 보유
- [ ] 장기적인 확장성 고려

### 💡 **추천 시나리오**

| 시나리오 | 추천 서비스 | 이유 |
|----------|-------------|------|
| **스타트업 초기** | ECS | 빠른 배포, 낮은 비용, 쉬운 관리 |
| **기존 AWS 사용자** | ECS | AWS 네이티브 통합, 학습 곡선 완만 |
| **대규모 엔터프라이즈** | EKS | 확장성, 표준화, 멀티 클라우드 지원 |
| **마이크로서비스 전환** | EKS | 고급 기능, 생태계 활용 가능 |
| **개발/테스트 환경** | ECS | 간단함, 빠른 프로토타이핑 |

---

## 📚 **추가 학습 자료**

### **ECS 관련**
- [AWS ECS 공식 문서](https://docs.aws.amazon.com/ecs/)
- [ECS Workshop](https://ecsworkshop.com/)
- [Fargate 시작하기](https://aws.amazon.com/ko/fargate/)

### **EKS 관련**
- [AWS EKS 공식 문서](https://docs.aws.amazon.com/eks/)
- [Kubernetes 공식 튜토리얼](https://kubernetes.io/docs/tutorials/)
- [EKS Workshop](https://www.eksworkshop.com/)

### **도구 및 리소스**
- [Docker 공식 문서](https://docs.docker.com/)
- [Helm 차트 가이드](https://helm.sh/docs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)


