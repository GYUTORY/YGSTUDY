---
title: Kubernetes
tags: [application-architecture, kubernetes]
updated: 2025-08-10
---
# 쿠버네티스(Kubernetes) 완벽 가이드: 컨테이너 오케스트레이션의 핵심

## 배경
- 더 자세한 내용은 [Kubernetes Q&A](./Kubernetes_Q&A.md)를 참고해주세요.


쿠버네티스는 구글이 개발한 오픈소스 컨테이너 오케스트레이션 플랫폼입니다. 현대적인 클라우드 네이티브 애플리케이션을 운영하는데 필수적인 도구로 자리잡았습니다.

### 주요 특징
- **컨테이너 오케스트레이션**: 수십~수백 개의 컨테이너를 효율적으로 관리
- **자동화된 배포와 스케일링**: 애플리케이션의 자동 배포, 스케일링, 관리 기능 제공
- **환경 독립성**: 온프레미스 서버, 가상머신, 클라우드 등 다양한 환경에서 동작

- **컨테이너 오케스트레이션**: 수십~수백 개의 컨테이너를 효율적으로 관리
- **자동화된 배포와 스케일링**: 애플리케이션의 자동 배포, 스케일링, 관리 기능 제공
- **환경 독립성**: 온프레미스 서버, 가상머신, 클라우드 등 다양한 환경에서 동작

- **원하는 상태 선언**: "어떻게"가 아닌 "무엇을" 원하는지 정의
- **자동 복구**: 시스템이 지속적으로 현재 상태를 모니터링하고 원하는 상태로 유지
- **자동 최적화**: 리소스 상황에 맞춰 최적의 배치 자동 수행

- **독립적인 컨트롤러**: 각 기능이 독립적인 컨트롤러로 구현
- **모듈화된 구조**: Node, ReplicaSet, Deployment, Namespace 등이 각각 독립적인 컨트롤러로 구현
- **유연한 확장성**: 새로운 기능을 추가하거나 수정하기 쉬운 구조


- **통합된 리소스 관리**: 물리적 리소스를 클러스터 단위로 추상화
- **중앙 제어 시스템**: Control Plane을 통한 일원화된 관리
- **효율적인 리소스 활용**: 클러스터 전체의 리소스를 최적화하여 사용

![클러스터 단위 중앙 제어.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%ED%81%B4%EB%9F%AC%EC%8A%A4%ED%84%B0%20%EB%8B%A8%EC%9C%84%20%EC%A4%91%EC%95%99%20%EC%A0%9C%EC%96%B4.png)

- **레이블 시스템**: 키-값 쌍을 통한 리소스 분류 및 선택
- **어노테이션**: 추가 메타데이터를 통한 상세 정보 관리
- **유연한 리소스 관리**: 선택자(Selector)를 통한 동적 그룹화

- **중앙화된 API 서버**: 모든 통신의 중심점
- **일관된 인터페이스**: kubectl, 컨트롤 플레인, 워커 노드 모두 API 서버를 통해 통신
- **확장 가능한 구조**: 새로운 기능 추가가 용이한 API 기반 설계



-## 네트워킹·보안 심화

- [초보자를 위한 쿠버네티스 안내서](https://subicura.com/2019/05/19/kubernetes-basic-1.html)
- [쿠버네티스 핵심 개념](https://seongjin.me/kubernetes-core-concepts/)
```
출처 
https://subicura.com/2019/05/19/kubernetes-basic-1.html
https://seongjin.me/kubernetes-core-concepts/






> 이 글은 쿠버네티스의 기본 개념과 핵심 설계 원칙에 대해 다룹니다. 컨테이너 오케스트레이션의 대표주자 쿠버네티스의 세계로 함께 떠나볼까요?

- **컨테이너 오케스트레이션**: 수십~수백 개의 컨테이너를 효율적으로 관리
- **자동화된 배포와 스케일링**: 애플리케이션의 자동 배포, 스케일링, 관리 기능 제공
- **환경 독립성**: 온프레미스 서버, 가상머신, 클라우드 등 다양한 환경에서 동작

- **컨테이너 오케스트레이션**: 수십~수백 개의 컨테이너를 효율적으로 관리
- **자동화된 배포와 스케일링**: 애플리케이션의 자동 배포, 스케일링, 관리 기능 제공
- **환경 독립성**: 온프레미스 서버, 가상머신, 클라우드 등 다양한 환경에서 동작

- **원하는 상태 선언**: "어떻게"가 아닌 "무엇을" 원하는지 정의
- **자동 복구**: 시스템이 지속적으로 현재 상태를 모니터링하고 원하는 상태로 유지
- **자동 최적화**: 리소스 상황에 맞춰 최적의 배치 자동 수행

- **독립적인 컨트롤러**: 각 기능이 독립적인 컨트롤러로 구현
- **모듈화된 구조**: Node, ReplicaSet, Deployment, Namespace 등이 각각 독립적인 컨트롤러로 구현
- **유연한 확장성**: 새로운 기능을 추가하거나 수정하기 쉬운 구조


- **통합된 리소스 관리**: 물리적 리소스를 클러스터 단위로 추상화
- **중앙 제어 시스템**: Control Plane을 통한 일원화된 관리
- **효율적인 리소스 활용**: 클러스터 전체의 리소스를 최적화하여 사용

![클러스터 단위 중앙 제어.png](..%2F..%2F..%2Fetc%2Fimage%2FApplication%20Architecture%2FKubernetes%2F%ED%81%B4%EB%9F%AC%EC%8A%A4%ED%84%B0%20%EB%8B%A8%EC%9C%84%20%EC%A4%91%EC%95%99%20%EC%A0%9C%EC%96%B4.png)

- **레이블 시스템**: 키-값 쌍을 통한 리소스 분류 및 선택
- **어노테이션**: 추가 메타데이터를 통한 상세 정보 관리
- **유연한 리소스 관리**: 선택자(Selector)를 통한 동적 그룹화

- **중앙화된 API 서버**: 모든 통신의 중심점
- **일관된 인터페이스**: kubectl, 컨트롤 플레인, 워커 노드 모두 API 서버를 통해 통신
- **확장 가능한 구조**: 새로운 기능 추가가 용이한 API 기반 설계



-## 네트워킹·보안 심화

- [초보자를 위한 쿠버네티스 안내서](https://subicura.com/2019/05/19/kubernetes-basic-1.html)
- [쿠버네티스 핵심 개념](https://seongjin.me/kubernetes-core-concepts/)
```
출처 
https://subicura.com/2019/05/19/kubernetes-basic-1.html
https://seongjin.me/kubernetes-core-concepts/






> 이 글은 쿠버네티스의 기본 개념과 핵심 설계 원칙에 대해 다룹니다. 컨테이너 오케스트레이션의 대표주자 쿠버네티스의 세계로 함께 떠나볼까요?





## 💡 쿠버네티스의 5가지 핵심 설계 원칙

### 1. 선언적 구성 (Declarative Configuration)

쿠버네티스의 가장 큰 특징은 '명령형'이 아닌 '선언형' 접근 방식을 채택했다는 점입니다.

### 2. 기능 단위의 분산 (Distributed Architecture)

쿠버네티스는 마이크로서비스 아키텍처의 철학을 그대로 반영한 분산 시스템입니다.

### 3. 클러스터 단위 중앙 제어 (Centralized Control)

쿠버네티스는 클러스터 단위로 리소스를 관리하는 중앙 집중식 제어 방식을 채택했습니다.

### 4. 동적 그룹화 (Dynamic Grouping)

쿠버네티스는 유연한 리소스 관리와 조직화를 위한 강력한 메타데이터 시스템을 제공합니다.

### 5. API 기반 상호작용 (API-Driven Interaction)

쿠버네티스의 모든 구성 요소는 API를 통해 통신하는 일관된 아키텍처를 가지고 있습니다.

### CNI(Container Network Interface) 개요
- 정의: 컨테이너 네트워킹을 표준 방식으로 붙이는 플러그인 규격. kubelet이 Pod를 띄울 때 CNI 플러그인을 호출해 IP를 할당하고 인터페이스를 붙인다.
- 구성 요소
  - 플러그인 바이너리: `bridge`, `calico`, `cilium`, `aws-vpc-cni` 등
  - IPAM: IP 주소 풀을 관리해 Pod에 IP를 배분한다.
- 동작 흐름(요약)
  1) kubelet → CNI 호출(Add)  2) veth 생성/브리지 연결(or ENI)  3) IPAM에서 IP 할당  4) 라우팅/iptables 설정  5) kubelet에 결과 반환
- 참고(클라우드)
  - EKS의 `aws-vpc-cni`: Pod가 VPC 사설 IP를 직접 받아 VPC 라우팅을 그대로 활용. ENI 용량/서브넷 IP 여유가 부족하면 스케줄링이 막힐 수 있어 서브넷 IP 관리가 중요하다.

### 네트워크 정책(NetworkPolicy)
- 정의: Pod 간 트래픽을 화이트리스트 방식으로 제한하는 규칙. 적용되면 명시적으로 허용된 트래픽만 통과한다.
- 전제: 네트워크 정책을 실제로 강제할 수 있는 CNI(예: Calico, Cilium)가 필요하다.
- 기본 차단 + 특정 앱만 허용 예시
```yaml
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

### RBAC 기본 롤 설계
- 용어
  - Role/ClusterRole: 권한 묶음(네임스페이스 한정/클러스터 전역)
  - RoleBinding/ClusterRoleBinding: 권한을 주체(ServiceAccount, 사용자, 그룹)에 연결
- 원칙: 최소 권한. 네임스페이스별 `viewer`/`editor` 구분, 클러스터 전역은 꼭 필요한 항목만 `ClusterRole`로 분리.
- 예시(네임스페이스 뷰어 + 바인딩)
```yaml
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

### Pod Security(PSA) 개요와 적용
- 정의: Pod 보안 표준을 네임스페이스 라벨로 강제하는 기능. 레거시 PSP는 deprecated/제거되었고, PSA가 기본.
- 레벨
  - privileged: 거의 제한 없음(운영 환경에서 지양)
  - baseline: 일반 워크로드에 적합한 기본 보호
  - restricted: 루트 미사용, 특권 금지 등 강한 제한
- 네임스페이스에 레벨 적용 예시
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
```
- 대표 제한 사항(예: restricted)
  - privileged: false, hostPID/hostNetwork: 금지, root로 실행 금지(MustRunAsNonRoot)
  - 쓰기 가능한 hostPath 금지, Capabilities 추가 제한

> 팁: 초기엔 `baseline`으로 시작해서 워크로드 호환성을 확인한 뒤 `restricted`로 상향하면 충격을 줄일 수 있다.

