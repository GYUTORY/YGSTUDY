---
title: Kubernetes 클러스터 아키텍처
tags: [infra, kubernetes, k8s, control-plane, etcd, scheduler, kubelet, cni, eviction]
updated: 2026-07-25
---

# Kubernetes 클러스터 아키텍처

## 1. 클러스터 구조 개요

Kubernetes 클러스터는 컨트롤 플레인(Control Plane)과 워커 노드(Worker Node)로 나뉜다. 컨트롤 플레인이 클러스터 상태를 관리하고 워커 노드가 실제 워크로드를 실행한다.

```
┌──────────────────────────────────────────────────────────┐
│                    Control Plane                         │
│                                                          │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   etcd   │  │  kube-apiserver  │  │   scheduler   │ │
│  └──────────┘  └──────────────────┘  └───────────────┘ │
│                                                          │
│  ┌──────────────────────────────┐                       │
│  │     controller-manager       │                       │
│  └──────────────────────────────┘                       │
└──────────────────────────┬───────────────────────────────┘
                           │ API 통신
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Worker Node │  │  Worker Node │  │  Worker Node │
│  ┌─────────┐ │  │  ┌─────────┐ │  │  ┌─────────┐ │
│  │ kubelet │ │  │  │ kubelet │ │  │  │ kubelet │ │
│  └─────────┘ │  │  └─────────┘ │  │  └─────────┘ │
│  ┌──────────┐│  │  ┌──────────┐│  │  ┌──────────┐│
│  │kube-proxy││  │  │kube-proxy││  │  │kube-proxy││
│  └──────────┘│  │  └──────────┘│  │  └──────────┘│
│  Pod, Pod... │  │  Pod, Pod... │  │  Pod, Pod... │
└──────────────┘  └──────────────┘  └──────────────┘
```

모든 컴포넌트는 kube-apiserver를 통해서만 통신한다. 컴포넌트끼리 직접 대화하지 않는다. 이 원칙이 클러스터 상태의 일관성을 보장하는 핵심이다.

---

## 2. 컨트롤 플레인 구성 요소

### 2.1 etcd

클러스터의 모든 상태를 저장하는 분산 키-값 저장소다. Pod, Deployment, Service, ConfigMap, Secret 등 Kubernetes 오브젝트 전체가 etcd에 저장된다.

Raft 합의 알고리즘으로 동작하기 때문에 홀수 개 노드가 필요하다. 3노드 구성이면 1대 장애를 허용하고, 5노드면 2대까지 허용한다. 짝수로 구성하면 쿼럼이 보장되지 않아서 의미가 없다.

**etcd 장애 시나리오**

etcd가 완전히 죽으면 클러스터가 읽기 전용 상태가 된다. 기존에 실행 중인 Pod는 그대로 돌아가지만 새로운 배포, 스케일, 설정 변경이 전부 막힌다. `kubectl get pods`가 응답하지 않고, 신규 Pod 스케줄링도 멈춘다.

과반수(쿼럼) 손실 상황이 더 위험하다. 3노드 중 2노드가 죽으면 쓰기가 중단되고, 경우에 따라 etcd 데이터가 롤백될 수 있다. 이 상황은 단순히 etcd를 재시작한다고 해결되지 않는다. `etcdctl snapshot restore`로 스냅샷 복구 절차가 필요하다.

```bash
# etcd 상태 확인
etcdctl endpoint status --cluster -w table \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 백업
etcdctl snapshot save /backup/etcd-$(date +%Y%m%d).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

etcd 백업은 주기적으로 해야 하는데, 실제로 복구까지 해보기 전까지는 백업이 정상인지 알 수 없다. DR 훈련을 주기적으로 해야 하는 이유다.

etcd 성능 저하는 전체 클러스터에 영향을 준다. Kubernetes의 모든 쓰기 작업이 etcd를 거치기 때문에, etcd IOPS가 낮은 디스크에 올라가면 API 응답이 느려지고 컨트롤러 루프가 지연된다. etcd 노드에는 SSD를 써야 하고, `etcd_disk_wal_fsync_duration_seconds` 메트릭이 10ms를 넘으면 디스크 교체를 검토해야 한다.

### 2.2 kube-apiserver

클러스터의 유일한 진입점이다. 모든 클라이언트(kubectl, kubelet, 컨트롤러, 외부 오퍼레이터)는 apiserver를 통해서만 클러스터에 접근한다. REST API로 제공되며, 요청마다 인증(Authentication) → 인가(Authorization) → 어드미션 컨트롤(Admission Control) → etcd 기록 순서로 처리한다.

어드미션 컨트롤러는 종종 예상치 못한 거부 원인이 된다. `PodSecurity`, `LimitRanger`, `ResourceQuota` 같은 내장 컨트롤러 외에도 ValidatingWebhook, MutatingWebhook이 붙어 있으면 외부 웹훅 서버가 응답하지 않을 때 Pod 생성 자체가 막힌다.

```bash
# 웹훅 때문에 Pod 생성이 안 될 때
kubectl describe pod <pod-name>
# "webhook.example.com" denied the request: ... 같은 메시지 확인

# 어드미션 웹훅 목록 확인
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

**apiserver 장애 시나리오**

apiserver가 죽으면 신규 오퍼레이션이 전부 멈추지만, 기존 Pod는 kubelet이 로컬 캐시로 관리하므로 계속 실행된다. HA 구성(2~3개 apiserver + 로드밸런서)이 없으면 단일 실패 지점이 된다.

apiserver가 느려지는 경우가 있는데, 주로 대규모 클러스터에서 watch 커넥션이 과도하게 많거나, etcd 응답이 느릴 때 발생한다. `apiserver_request_duration_seconds` 메트릭이 이 징후를 잡는다.

### 2.3 kube-scheduler

새로 생성된 Pod 중 아직 노드에 배정되지 않은 것(nodeName이 비어 있는 것)을 감지하고, 어느 노드에 배치할지 결정한다. 결정 결과를 etcd에 기록하면, kubelet이 이를 감지하고 실제로 파드를 실행한다.

스케줄링은 두 단계다. 필터링(Filtering)에서 조건을 만족하지 못하는 노드를 제거하고, 스코어링(Scoring)에서 남은 노드 중 가장 적합한 곳을 고른다.

**필터링 조건**

- 리소스 요청량(`requests`) 대비 노드의 할당 가능 자원(Allocatable) 부족
- nodeSelector, nodeAffinity 불일치
- taint/toleration 미설치
- Pod Anti-affinity 위반
- PodTopologySpreadConstraints 위반
- 볼륨 가용 여부 (예: 특정 AZ에만 있는 PVC)

노드는 충분한데 Pod가 Pending 상태로 남는다면 `kubectl describe pod`의 Events 섹션에 필터링 실패 원인이 나온다.

**스케줄러 장애 시나리오**

스케줄러가 죽으면 기존 Pod는 영향 없다. 새 Pod만 Pending 상태로 쌓인다. kube-scheduler는 leader election을 통해 HA 구성이 가능하다. 스케줄러를 여러 개 띄워도 실제로 일하는 건 리더 하나다.

### 2.4 controller-manager

Kubernetes의 반복 실행 제어 루프 집합이다. Deployment, ReplicaSet, StatefulSet, DaemonSet, Job, Namespace 등 각 리소스 타입마다 전용 컨트롤러가 있고, 이걸 하나의 바이너리로 묶어서 실행한다.

각 컨트롤러는 단순한 원칙으로 동작한다. "현재 상태(etcd에서 읽은 실제 상태)가 원하는 상태(spec)와 다르면 맞추는 작업을 한다." 이게 Kubernetes의 reconciliation loop다.

예를 들어 Deployment의 `replicas: 3`을 `replicas: 5`로 바꾸면, controller-manager의 ReplicaSet 컨트롤러가 변경을 감지하고 2개의 Pod 생성 요청을 apiserver로 보낸다.

**controller-manager 장애 시나리오**

controller-manager가 죽으면 기존 Pod는 계속 실행된다. 문제는 자동 복구가 안 된다는 점이다. Pod가 죽어도 새로 안 뜨고, 노드 장애 시 Pod를 다른 노드로 옮기지 않는다. 표면적으로는 클러스터가 정상처럼 보이지만 실제로는 운영이 안 되는 상태다.

```bash
# 컨트롤 플레인 컴포넌트 상태 확인
kubectl get componentstatuses
# 또는 컨트롤 플레인 노드에서
systemctl status kube-controller-manager
```

---

## 3. 워커 노드 컴포넌트

### 3.1 kubelet

각 노드에서 실행되는 에이전트다. kube-apiserver에서 자신에게 배정된 Pod 정보를 watch하고, 실제로 컨테이너를 실행하고 관리하는 역할을 한다.

kubelet이 하는 일은 이렇다.

- apiserver에서 자신의 노드로 배정된 PodSpec을 가져옴
- CRI(Container Runtime Interface)를 통해 컨테이너 런타임(containerd, CRI-O)에 컨테이너 실행 요청
- CNI를 통해 네트워크 인터페이스 설정
- CSI를 통해 볼륨 마운트
- liveness/readiness probe 주기적 실행
- 노드 상태와 파드 상태를 주기적으로 apiserver에 보고

kubelet은 `/etc/kubernetes/manifests/` 디렉토리도 감시한다. 여기 있는 YAML 파일은 static pod로 취급되어, apiserver 없이도 kubelet이 직접 실행한다. 컨트롤 플레인 컴포넌트들(apiserver, scheduler, controller-manager, etcd)이 이 방식으로 실행된다.

**kubelet 장애 시나리오**

특정 노드의 kubelet이 죽으면 해당 노드의 Pod가 관리되지 않는다. 죽어있는 컨테이너가 재시작되지 않고, liveness probe 실패가 감지되지 않는다. controller-manager는 kubelet의 응답이 없으면(`node.kubernetes.io/not-ready` taint) 해당 노드의 Pod를 Terminating 상태로 바꾸고 다른 노드에 새로 스케줄링한다. 기본 대기 시간은 5분이다.

```bash
# 노드 상태 확인
kubectl get nodes
kubectl describe node <node-name>  # Conditions 섹션 확인

# kubelet 로그
journalctl -u kubelet -f --no-pager
```

### 3.2 kube-proxy

각 노드에서 DaemonSet으로 실행된다. Service → Pod IP 변환 규칙을 노드에 설정하는 게 주 역할이다.

기본 모드는 iptables다. Service가 생성되면 kube-proxy가 ClusterIP와 해당 Service의 엔드포인트(Pod IP:Port)를 매핑하는 iptables 규칙을 노드마다 추가한다.

```bash
# 서비스 ClusterIP로 연결될 때 iptables에서 DNAT 되는 과정 확인
iptables-save | grep <service-name>
```

IPVS 모드는 iptables보다 성능이 좋지만, 추가 커널 모듈이 필요하다. 서비스 수가 수천 개가 넘으면 iptables 규칙이 수만 개로 늘어나 성능 저하가 생기는데, IPVS 모드가 이 문제를 해결한다.

Cilium 같은 CNI를 쓰면 kube-proxy 없이 eBPF로 처리할 수 있다(`kube-proxy replacement` 기능). 오버헤드가 줄어드는 대신 관찰성 도구도 eBPF 기반으로 바꿔야 한다.

---

## 4. Pod 스케줄링 흐름

Pod가 생성 요청을 받고 실제로 컨테이너가 실행되기까지 이 순서로 진행된다.

```
kubectl apply -f pod.yaml
       │
       ▼
kube-apiserver: 인증 → 인가 → 어드미션
       │
       ▼
etcd: Pod 오브젝트 저장 (nodeName = "")
       │
       ▼
kube-scheduler: watch로 nodeName 없는 Pod 감지
       │  필터링 → 스코어링
       ▼
etcd: Pod의 nodeName 업데이트
       │
       ▼
kubelet: 자신의 노드에 배정된 Pod watch로 감지
       │  이미지 풀 → CNI 네트워크 설정 → 컨테이너 실행
       ▼
Pod: Running 상태
```

각 단계는 비동기로 이어진다. `kubectl apply` 명령이 성공했다는 건 apiserver가 etcd에 오브젝트를 저장했다는 뜻이지, Pod가 실행됐다는 뜻이 아니다.

스케줄링이 완료되어도 실제 컨테이너 시작까지 이미지 풀 시간이 걸린다. 첫 배포 시 이미지가 노드에 없으면 수 분이 걸릴 수 있다. 이미지를 미리 캐싱(DaemonSet으로 이미지 풀 + 로컬 레지스트리 미러)하거나, 배포 시간이 중요한 경우 이미지 크기를 줄이는 것이 현실적인 해결책이다.

### 4.1 리소스 요청과 실제 배치

스케줄러는 `requests`를 기준으로 노드를 선택한다. `limits`는 런타임에 강제되는 제한이지, 스케줄링 기준이 아니다.

```yaml
resources:
  requests:
    cpu: "200m"    # 스케줄러가 노드 선택 시 기준
    memory: "256Mi"
  limits:
    cpu: "1000m"   # 컨테이너 런타임이 cgroup으로 강제
    memory: "512Mi"
```

`requests`를 설정하지 않으면 `0`으로 간주되어 어느 노드에나 배치될 수 있다. 이 상태에서 메모리 경쟁이 발생하면 노드가 OOM으로 불안정해진다. 실무에서 requests를 설정하지 않은 Pod는 eviction 우선순위가 가장 높아서 먼저 퇴거된다.

---

## 5. CNI 플러그인 비교: Flannel, Calico, Cilium

CNI(Container Network Interface)는 Pod에 네트워크를 붙여주는 플러그인이다. 선택에 따라 기능, 성능, 운영 복잡도가 달라진다.

### 5.1 Flannel

가장 단순한 CNI다. VXLAN 오버레이로 노드 간 Pod 통신을 구성한다. 네트워크 정책(NetworkPolicy)을 지원하지 않는다.

쓰는 경우는 명확하다. 테스트 환경, 소규모 클러스터, 네트워크 정책이 필요 없는 상황. 운영 환경에서 Flannel만 쓰면 Pod 간 접근 제어가 없어서 보안 문제가 생긴다.

```
노드 A (10.244.1.0/24)          노드 B (10.244.2.0/24)
┌─────────────────────┐         ┌─────────────────────┐
│  Pod: 10.244.1.10   │──VXLAN──│  Pod: 10.244.2.10   │
│  Pod: 10.244.1.11   │  (UDP   │  Pod: 10.244.2.11   │
└─────────────────────┘  8472)  └─────────────────────┘
```

### 5.2 Calico

NetworkPolicy를 완전히 지원한다. BGP로 라우팅을 구성하는 방식과 VXLAN 오버레이 방식을 선택할 수 있다. BGP 모드는 오버레이 없이 직접 라우팅이라 성능이 좋지만, BGP를 이해하고 네트워크 장비와 연동할 수 있어야 한다.

운영 환경에서 네트워크 정책이 필요하다면 Calico가 가장 무난한 선택이다. 문서가 많고, 대부분의 관리형 쿠버네티스(EKS, GKE, AKS)에서 공식 지원된다.

```yaml
# NetworkPolicy 예시: default-deny-ingress + allow 특정 레이블
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-app
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - port: 5432
```

Calico에서 자주 생기는 문제는 BGP 피어링 장애다. 노드가 추가될 때 BGP 피어가 제대로 설정되지 않으면 해당 노드의 Pod가 다른 노드 Pod와 통신이 안 된다.

```bash
# Calico BGP 피어 상태 확인
calicoctl node status
# 노드별 라우팅 테이블 확인
ip route show
```

### 5.3 Cilium

eBPF 기반이다. iptables 대신 커널 내 eBPF 프로그램으로 네트워크 처리를 해서 성능이 좋다. NetworkPolicy 외에도 L7 정책(HTTP 메서드, 경로 기반 제어)이 가능하고, Hubble로 파드 간 네트워크 흐름을 실시간 관찰할 수 있다.

요구 커널 버전이 있다. 기능에 따라 다르지만 일반적으로 5.10+이 권장된다. 커널이 낮거나 클라우드 관리형 노드 이미지가 지원하지 않으면 설치 자체가 안 된다.

kube-proxy를 대체하는 기능(`kubeProxyReplacement: true`)을 활성화하면 iptables 규칙 없이 eBPF만으로 Service 처리를 한다. 대규모 클러스터에서 iptables 관련 CPU 스파이크가 사라지는 효과가 있다.

Hubble UI를 통해 네트워크 트래픽을 시각화할 수 있어서, 장애 시 어느 Pod에서 어느 Pod로 트래픽이 차단되는지 바로 확인된다. 이 관찰성 기능 때문에 Cilium을 선택하는 팀이 늘고 있다.

**선택 기준 정리**

| 상황 | 선택 |
|---|---|
| 테스트/개발 환경, 빠른 구성 | Flannel |
| 운영 환경, 네트워크 정책 필요 | Calico |
| 대규모 클러스터, eBPF, 상세 네트워크 관찰 | Cilium |
| 커널 5.10+ 보장 불가 | Calico (Cilium 제외) |

---

## 6. 노드 리소스 압박과 Eviction

kubelet은 노드 리소스 사용량을 주기적으로 모니터링하고, 임계치를 넘으면 Pod를 퇴거(eviction)시킨다. 퇴거 대상 선정에는 우선순위가 있다.

### 6.1 퇴거 임계치

기본 설정에서 사용하는 임계치다.

- 메모리: `memory.available < 100Mi`
- 디스크: `nodefs.available < 10%` 또는 `imagefs.available < 15%`

이 값을 넘으면 **soft eviction**이 시작된다. soft eviction은 `eviction-soft-grace-period` 동안 조건이 유지되면 퇴거를 시작한다. 더 급하면 **hard eviction**이 즉시 퇴거를 실행한다.

```bash
# 노드 리소스 현황
kubectl describe node <node-name> | grep -A10 "Allocated resources"
kubectl top nodes
```

### 6.2 퇴거 우선순위

kubelet이 퇴거할 Pod를 고르는 기준은 QoS 클래스다.

**BestEffort**: `requests`, `limits` 모두 설정 안 된 파드. 가장 먼저 퇴거된다.

**Burstable**: `requests`는 있는데 `limits`보다 낮거나, CPU/메모리 중 하나만 설정된 파드. 중간 우선순위.

**Guaranteed**: `requests == limits`로 동일하게 설정된 파드. 마지막에 퇴거된다.

같은 QoS 클래스 내에서는 요청량 대비 실제 사용량이 많은 파드가 먼저 퇴거된다.

```yaml
# Guaranteed QoS
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "500m"    # requests와 동일
    memory: "512Mi"
```

운영에서 중요한 Pod를 BestEffort로 실행하고 있다가 노드 리소스 부족 시 먼저 퇴거되는 사고가 자주 발생한다. 중요한 서비스는 Guaranteed 또는 Burstable로 명시적으로 설정해야 한다.

### 6.3 PodDisruptionBudget

퇴거나 노드 드레인 시 최소 Pod 수를 보장한다. Deployment의 replicas가 3인데 PDB 없이 노드를 드레인하면 동시에 여러 Pod가 퇴거되어 서비스가 다운될 수 있다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: backend-pdb
spec:
  minAvailable: 2     # 항상 최소 2개는 실행 유지
  selector:
    matchLabels:
      app: backend
```

`minAvailable: 2`면 3개 중 1개씩만 퇴거된다. 드레인이 오래 걸리는 이유가 대부분 PDB 때문이다. `kubectl drain` 명령이 PDB를 위반하면 멈추고 대기한다.

---

## 7. 실제 운영에서 겪는 장애: ImagePullBackOff와 CrashLoopBackOff

### 7.1 ImagePullBackOff

컨테이너 이미지를 pull하지 못했을 때 나타난다. 원인은 생각보다 다양하다.

**이미지가 존재하지 않음**

가장 단순한 경우다. 태그가 잘못됐거나 이미지가 레지스트리에 없는 경우다.

```bash
kubectl describe pod <pod-name>
# Events에서 확인:
# Failed to pull image "myapp:v1.2.3": ...manifest unknown...
```

**프라이빗 레지스트리 인증 실패**

`imagePullSecrets`가 설정되지 않았거나, 시크릿이 만료된 경우다.

```bash
# docker-registry 타입 시크릿 생성
kubectl create secret docker-registry my-registry-secret \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=password \
  --namespace=production

# Deployment에 적용
spec:
  template:
    spec:
      imagePullSecrets:
        - name: my-registry-secret
```

ECR처럼 토큰이 12시간마다 만료되는 레지스트리는 시크릿을 주기적으로 갱신해야 한다. 이를 자동화하지 않으면 자정쯤 배포가 실패한다.

**네트워크 문제**

노드가 레지스트리에 접근하지 못하는 경우다. 노드의 DNS, 방화벽, 프록시 설정을 확인해야 한다.

```bash
# 노드에서 직접 이미지 pull 테스트
ssh <node>
crictl pull registry.example.com/myapp:v1.2.3
```

**ImagePullBackOff vs ErrImagePull**

둘 다 이미지 pull 실패지만 다르다. `ErrImagePull`은 최초 실패 상태고, `ImagePullBackOff`는 여러 번 실패 후 kubelet이 재시도 간격을 늘리고 있는 상태다. 재시도 간격은 5초에서 시작해서 최대 5분까지 늘어난다. 이미지 문제를 고쳤는데도 바로 안 뜨면 `kubectl delete pod`로 파드를 다시 만드는 게 빠르다.

### 7.2 CrashLoopBackOff

컨테이너가 시작됐다가 바로 죽는 것을 반복할 때 나타난다. 컨테이너가 종료 코드 0이 아닌 값으로 끝나거나 liveness probe가 실패할 때 발생한다.

**컨테이너가 즉시 종료되는 경우**

보통 두 가지다. 애플리케이션이 시작 중 에러가 나서 죽거나, 설정 파일/환경변수 누락으로 초기화에 실패하는 경우다.

```bash
# 최근 종료된 컨테이너 로그 확인 (--previous 플래그)
kubectl logs <pod-name> --previous

# 종료 코드 확인
kubectl describe pod <pod-name>
# Last State의 Exit Code 확인
```

종료 코드는 원인을 힌트로 준다. `exit code 1`은 일반 에러, `exit code 137`은 SIGKILL(보통 OOMKill), `exit code 143`은 SIGTERM, `exit code 127`은 명령어 없음(CMD가 잘못된 경우)이다.

```bash
# OOMKill 여부 확인
kubectl describe pod <pod-name> | grep -i "oom\|memory"
# 또는 노드에서
dmesg | grep -i "oom\|killed"
```

**OOMKill로 인한 CrashLoopBackOff**

메모리 limits가 너무 낮거나, 메모리 누수가 있는 경우다. `kubectl describe pod`에서 `OOMKilled: true`가 보이면 limits를 올리거나 메모리 누수를 찾아야 한다.

**liveness probe 실패**

애플리케이션이 실행 중이지만 probe가 실패해서 kubelet이 컨테이너를 재시작하는 경우다.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30  # 시작 후 30초 대기
  periodSeconds: 10
  failureThreshold: 3
```

`initialDelaySeconds`가 너무 짧으면 애플리케이션이 완전히 뜨기 전에 probe가 실패해서 재시작 루프가 된다. Spring Boot처럼 시작 시간이 긴 앱은 `startupProbe`를 별도로 설정해서 초기 시작 시간을 길게 허용하고, 그 이후에 liveness probe를 적용하는 게 낫다.

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30   # 최대 300초(30 * 10초) 동안 대기
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 10
  failureThreshold: 3
```

**ConfigMap/Secret 마운트 실패**

존재하지 않는 ConfigMap이나 Secret을 마운트하려고 하면 Pod가 아예 시작되지 않는다. `kubectl describe pod`에서 `MountVolume.SetUp failed` 메시지가 나온다.

```bash
kubectl describe pod <pod-name>
# Warning  Failed  MountVolume.SetUp failed for volume "config" :
# configmap "app-config" not found
```

ConfigMap을 먼저 배포하지 않은 채로 Deployment를 배포했을 때 자주 발생한다.

---

## 8. 컨트롤 플레인 고가용성

프로덕션에서 단일 컨트롤 플레인 노드는 위험하다. 컨트롤 플레인 HA 구성은 보통 이렇다.

```
                    ┌──────────────────┐
                    │  Load Balancer   │
                    │  (HAProxy/NLB)   │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐
│  Control Plane 1 ││  Control Plane 2 ││  Control Plane 3 │
│  apiserver       ││  apiserver       ││  apiserver       │
│  scheduler       ││  scheduler       ││  scheduler       │
│  ctrl-manager    ││  ctrl-manager    ││  ctrl-manager    │
│  etcd            ││  etcd            ││  etcd            │
└──────────────────┘└──────────────────┘└──────────────────┘
         etcd 클러스터 (쿼럼 유지)
```

scheduler와 controller-manager는 리더 선출(leader election)을 통해 3개 중 1개만 실제로 동작한다. apiserver는 로드밸런서 뒤에서 3개 모두 동작한다. etcd는 3노드가 모두 Raft로 합의한다.

```bash
# 현재 scheduler 리더 확인
kubectl get lease -n kube-system kube-scheduler -o yaml
# holderIdentity 필드에 현재 리더 노드 이름이 있음
```

kubeadm으로 HA 클러스터를 구성할 때 etcd를 컨트롤 플레인과 같이 두는 stacked etcd 방식과 별도 노드에 두는 external etcd 방식이 있다. stacked는 관리가 단순하지만, 컨트롤 플레인 노드 장애 시 etcd도 같이 잃는다. 요구 SLA가 높으면 external etcd가 낫다.
