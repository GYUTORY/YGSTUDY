---
title: Kubernetes (쿠버네티스) 완벽 가이드
tags: [kubernetes, container-orchestration, devops, cloud-native, architecture]
updated: 2024-12-19
---

# Kubernetes (쿠버네티스) 완벽 가이드

## 배경

### Kubernetes의 필요성
쿠버네티스는 구글이 개발한 오픈소스 컨테이너 오케스트레이션 플랫폼입니다. 현대적인 클라우드 네이티브 애플리케이션을 운영하는데 필수적인 도구로 자리잡았습니다.

### 기본 개념
- **컨테이너 오케스트레이션**: 수십~수백 개의 컨테이너를 효율적으로 관리
- **자동화된 배포와 스케일링**: 애플리케이션의 자동 배포, 스케일링, 관리 기능 제공
- **환경 독립성**: 온프레미스 서버, 가상머신, 클라우드 등 다양한 환경에서 동작
- **선언적 구성**: "어떻게"가 아닌 "무엇을" 원하는지 정의
- **자동 복구**: 시스템이 지속적으로 현재 상태를 모니터링하고 원하는 상태로 유지

## 핵심

### 1. 쿠버네티스의 5가지 핵심 설계 원칙

#### 1. 선언적 구성 (Declarative Configuration)
쿠버네티스의 가장 큰 특징은 '명령형'이 아닌 '선언형' 접근 방식을 채택했다는 점입니다.

```yaml
# 선언적 구성 예시
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
        image: nginx:1.14.2
        ports:
        - containerPort: 80
```

#### 2. 기능 단위의 분산 (Distributed Architecture)
쿠버네티스는 마이크로서비스 아키텍처의 철학을 그대로 반영한 분산 시스템입니다.

- **독립적인 컨트롤러**: 각 기능이 독립적인 컨트롤러로 구현
- **모듈화된 구조**: Node, ReplicaSet, Deployment, Namespace 등이 각각 독립적인 컨트롤러로 구현
- **유연한 확장성**: 새로운 기능을 추가하거나 수정하기 쉬운 구조

#### 3. 클러스터 단위 중앙 제어 (Centralized Control)
쿠버네티스는 클러스터 단위로 리소스를 관리하는 중앙 집중식 제어 방식을 채택했습니다.

- **통합된 리소스 관리**: 물리적 리소스를 클러스터 단위로 추상화
- **중앙 제어 시스템**: Control Plane을 통한 일원화된 관리
- **효율적인 리소스 활용**: 클러스터 전체의 리소스를 최적화하여 사용

#### 4. 동적 그룹화 (Dynamic Grouping)
쿠버네티스는 유연한 리소스 관리와 조직화를 위한 강력한 메타데이터 시스템을 제공합니다.

- **레이블 시스템**: 키-값 쌍을 통한 리소스 분류 및 선택
- **어노테이션**: 추가 메타데이터를 통한 상세 정보 관리
- **유연한 리소스 관리**: 선택자(Selector)를 통한 동적 그룹화

#### 5. API 기반 상호작용 (API-Driven Interaction)
쿠버네티스의 모든 구성 요소는 API를 통해 통신하는 일관된 아키텍처를 가지고 있습니다.

- **중앙화된 API 서버**: 모든 통신의 중심점
- **일관된 인터페이스**: kubectl, 컨트롤 플레인, 워커 노드 모두 API 서버를 통해 통신
- **확장 가능한 구조**: 새로운 기능 추가가 용이한 API 기반 설계

### 2. 네트워킹과 보안

#### CNI(Container Network Interface) 개요
- **정의**: 컨테이너 네트워킹을 표준 방식으로 붙이는 플러그인 규격
- **구성 요소**:
  - 플러그인 바이너리: `bridge`, `calico`, `cilium`, `aws-vpc-cni` 등
  - IPAM: IP 주소 풀을 관리해 Pod에 IP를 배분
- **동작 흐름**:
  1. kubelet → CNI 호출(Add)
  2. veth 생성/브리지 연결(or ENI)
  3. IPAM에서 IP 할당
  4. 라우팅/iptables 설정
  5. kubelet에 결과 반환

#### 네트워크 정책(NetworkPolicy)
```yaml
# 기본 차단 + 특정 앱만 허용 예시
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-and-allow-web
  namespace: prod
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress: []           # 기본 Ingress 차단
  egress:               # DNS 등 필요한 아웃바운드만 열 수도 있음
  - to:
    - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
    ports:
    - protocol: UDP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-web
  namespace: prod
spec:
  podSelector:
    matchLabels: { app: api }
  ingress:
  - from:
    - podSelector: { matchLabels: { app: web } }
    ports:
    - protocol: TCP
      port: 8080
```

### 3. RBAC과 보안

#### RBAC 기본 롤 설계
- **용어**:
  - Role/ClusterRole: 권한 묶음(네임스페이스 한정/클러스터 전역)
  - RoleBinding/ClusterRoleBinding: 권한을 주체(ServiceAccount, 사용자, 그룹)에 연결
- **원칙**: 최소 권한. 네임스페이스별 `viewer`/`editor` 구분, 클러스터 전역은 꼭 필요한 항목만 `ClusterRole`로 분리

```yaml
# 네임스페이스 뷰어 + 바인딩 예시
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: viewer
  namespace: prod
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "services", "deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: web-sa
  namespace: prod
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: viewer-binding
  namespace: prod
subjects:
- kind: ServiceAccount
  name: web-sa
  namespace: prod
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: viewer
```

#### Pod Security(PSA) 개요와 적용
- **정의**: Pod 보안 표준을 네임스페이스 라벨로 강제하는 기능
- **레벨**:
  - privileged: 거의 제한 없음(운영 환경에서 지양)
  - baseline: 일반 워크로드에 적합한 기본 보호
  - restricted: 루트 미사용, 특권 금지 등 강한 제한

```yaml
# 네임스페이스에 레벨 적용 예시
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
```

## 예시

### 1. 기본 배포 예시

#### Deployment와 Service
```yaml
# nginx-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
        image: nginx:1.14.2
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

#### ConfigMap과 Secret
```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgresql://localhost:5432/mydb"
  api_version: "v1"
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQ=  # base64 encoded "password"
```

### 2. 고급 패턴

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nginx-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nginx-deployment
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

#### Ingress 리소스
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nginx-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nginx-service
            port:
              number: 80
```

## 운영 팁

### 1. 모니터링과 로깅
```yaml
# Prometheus ServiceMonitor 예시
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nginx-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nginx
  endpoints:
  - port: http
    interval: 30s
```

### 2. 리소스 관리
```yaml
# ResourceQuota 예시
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: prod
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "10"
```

### 3. 백업과 복구
```yaml
# Velero 백업 예시
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: daily-backup
  namespace: velero
spec:
  includedNamespaces:
  - prod
  - staging
  storageLocation: default
  volumeSnapshotLocations:
  - default
```

## 참고

### 쿠버네티스 vs 다른 오케스트레이션 도구

| 측면 | Kubernetes | Docker Swarm | Apache Mesos |
|------|------------|--------------|--------------|
| **복잡성** | 높음 | 낮음 | 중간 |
| **기능성** | 매우 풍부 | 기본적 | 중간 |
| **커뮤니티** | 매우 활발 | 활발 | 제한적 |
| **학습 곡선** | 가파름 | 완만 | 중간 |
| **엔터프라이즈 지원** | 우수 | 보통 | 제한적 |

### 쿠버네티스 도입 단계

| 단계 | 내용 | 목표 |
|------|------|------|
| **1단계** | 개발 환경 구축 | Minikube 또는 Docker Desktop |
| **2단계** | 기본 개념 학습 | Pod, Service, Deployment 이해 |
| **3단계** | 애플리케이션 배포 | 실제 애플리케이션 배포 및 관리 |
| **4단계** | 고급 기능 적용 | HPA, Ingress, RBAC 등 |
| **5단계** | 운영 환경 구축 | 프로덕션 클러스터 운영 |

### 결론
쿠버네티스는 현대적인 클라우드 네이티브 애플리케이션을 운영하는데 필수적인 도구입니다. 선언적 구성과 자동화된 관리 기능을 통해 복잡한 컨테이너 환경을 효율적으로 관리할 수 있습니다. 다만 학습 곡선이 가파르므로 단계적 접근이 중요합니다.

