---
title: EKS VPC CNI와 ENI — Pod IP 할당, warm pool, prefix delegation, Too many pods 디버깅
tags: [aws, vpc, kubernetes, network]
updated: 2026-07-22
---

# EKS VPC CNI와 ENI

## EKS.md에서 넘어간 이유

EKS.md 네트워킹 섹션에서 VPC CNI와 ENI 제한을 5~6줄로 정리하고 넘어갔다. 실제로는 이 부분에서 운영 중 문제가 가장 많이 생긴다.

흔히 겪는 상황들이 있다.

- 노드에 CPU/메모리 여유가 있는데 Pod가 Pending 상태에서 안 벗어난다
- "Too many pods" 에러가 뜨는데 원인을 모른다
- 서브넷 IP가 생각보다 빨리 소진된다
- m5.large 클러스터인데 노드당 Pod 밀도가 안 나온다

전부 VPC CNI의 ENI 할당 방식에서 비롯된 문제다.

## VPC CNI Secondary IP 모드

EKS의 기본 네트워킹 플러그인인 `amazon-vpc-cni-k8s`는 각 Pod에 VPC의 실제 IP를 직접 부여한다. overlay 네트워크(VXLAN, IPinIP 등)를 쓰지 않는다. Pod IP가 곧 VPC IP다.

### 동작 원리

노드가 시작하면 `aws-node` DaemonSet이 노드에 붙은 ENI를 파악하고, 각 ENI에서 secondary IP를 미리 할당해 둔다. Pod 생성 요청이 오면 이미 확보해 둔 IP 중 하나를 pod에 배정한다.

```
노드 시작
  └── aws-node 데몬 기동
        └── Primary ENI (eth0) 확인
              └── Secondary IP 할당 시작
                    └── 필요시 추가 ENI 생성 + secondary IP 추가 할당
```

Pod 하나가 secondary IP 하나를 소비한다. ECS awsvpc 모드처럼 Pod마다 ENI를 통째로 쓰는 게 아니라, ENI 하나의 secondary IP 여러 개를 여러 Pod가 나눠 쓴다.

### ENI와 IP의 관계

ENI는 primary IP 하나와 secondary IP 여러 개를 가진다.

| IP 종류 | 역할 |
|---------|------|
| Primary IP (eth0의 첫 번째 IP) | 노드 자체의 IP. kubelet, kube-proxy가 사용 |
| Secondary IP (ENI별 추가 IP) | Pod에 할당되는 IP 풀 |

Primary ENI의 primary IP는 노드 자체가 쓰고, 모든 ENI(primary + 추가 ENI)의 secondary IP 전부가 Pod IP 풀이 된다. 각 ENI의 primary IP는 Pod에 배정되지 않는다.

## ENI Warm Pool — 사전 할당

VPC CNI는 Pod 요청이 들어왔을 때 즉석에서 IP를 할당하지 않는다. 미리 확보해 두는 방식이다. 이걸 warm pool이라고 한다.

즉석 할당이면 Pod 생성 시점에 ENI 생성이나 secondary IP 할당 API 호출이 필요하고, 이 작업이 몇 초 걸린다. 스케일 아웃 시 Pod가 순간적으로 Pending에 걸리는 현상이 이 타이밍에서 생긴다.

### 사전 할당 제어 파라미터

`aws-node` DaemonSet의 환경 변수로 제어한다.

```yaml
env:
- name: WARM_ENI_TARGET
  value: "1"       # 미사용 ENI를 몇 개 유지할지
- name: WARM_IP_TARGET
  value: "5"       # 미할당 IP를 몇 개 유지할지
- name: MINIMUM_IP_TARGET
  value: "10"      # 노드에 최소 몇 개 IP를 유지할지
```

기본값은 `WARM_ENI_TARGET: 1`이다. ENI를 하나 여분으로 유지한다는 뜻이다. 작은 노드에서는 ENI 슬롯이 귀하기 때문에 `WARM_IP_TARGET`으로 바꾸는 게 낫다.

t3.medium(ENI 3개, ENI당 IP 6개)에서 `WARM_ENI_TARGET: 1`을 쓰면, 실제 Pod가 없어도 ENI 1개와 secondary IP 5개가 상시 예약 상태로 잡혀 있다. 클러스터 전체 노드 수가 많으면 이 unused warm pool이 서브넷 IP를 꽤 잡아먹는다.

```bash
# 현재 warm pool 설정 확인
kubectl describe daemonset aws-node -n kube-system | grep -A 30 "Environment"
```

서브넷 IP 고갈 문제가 있을 때 `WARM_IP_TARGET: 2`, `MINIMUM_IP_TARGET: 5`로 줄이면 여유가 생긴다. 스케일 아웃 반응 속도는 그만큼 느려진다.

## Pod 수 한계 계산

### 공식

```
max_pods = (max_ENI_수 × (ENI당_max_IP_수 - 1)) + 2
```

각 ENI의 primary IP는 ENI 자체가 소비하므로(노드 라우팅용), secondary IP만 Pod에 배정된다. 그래서 `IP - 1`이다. 끝의 `+2`는 kube-proxy, aws-node처럼 host network 모드로 뜨는 시스템 Pod 자리다. 이 Pod들은 secondary IP가 아니라 노드 IP를 쓰기 때문에 별도로 2자리가 더해진다.

### 인스턴스 타입별 실제 한계

| 인스턴스 | ENI 수 | ENI당 IP | 계산 | max_pods |
|---------|--------|---------|------|---------|
| t3.small | 3 | 4 | (3×3)+2 | 11 |
| t3.medium | 3 | 6 | (3×5)+2 | 17 |
| t3.large | 3 | 12 | (3×11)+2 | 35 |
| m5.large | 3 | 10 | (3×9)+2 | 29 |
| m5.xlarge | 4 | 15 | (4×14)+2 | 58 |
| m5.2xlarge | 4 | 15 | (4×14)+2 | 58 |
| m5.4xlarge | 8 | 30 | (8×29)+2 | 234 |
| c5.xlarge | 4 | 15 | (4×14)+2 | 58 |
| c5.4xlarge | 8 | 30 | (8×29)+2 | 234 |

m5.2xlarge와 m5.xlarge의 max_pods가 58로 같다. 둘 다 ENI 4개, ENI당 15 IP로 동일한 스펙이라서 그렇다. CPU/메모리가 두 배 차이나도 Pod 밀도는 똑같다. Pod당 리소스 요구가 낮고 Pod 수가 중요하다면 m5.xlarge를 여러 대 쓰는 쪽이 낫다.

### kubelet max-pods 설정

노드가 뜰 때 kubelet에 `--max-pods` 값이 설정된다. EKS 관리형 노드 그룹은 bootstrap 스크립트가 인스턴스 타입에 맞는 값을 자동으로 계산해 넣어준다.

```bash
# 노드에 설정된 max-pods 확인
kubectl get node <node-name> -o jsonpath='{.status.allocatable.pods}'

# 노드 OS에서 직접 확인
sudo cat /etc/kubernetes/kubelet/kubelet-config.json | python3 -m json.tool | grep maxPods
```

자체 관리형 노드 그룹(self-managed node group)을 쓴다면 bootstrap 스크립트에 명시적으로 값을 넣어야 한다.

```bash
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--max-pods=17'
```

실제 인스턴스 타입별 권장 값은 amazon-eks-ami 레포의 `eni-max-pods.txt`를 참조한다.

```bash
# 노드 안에서
grep "$(curl -s http://169.254.169.254/latest/meta-data/instance-type)" \
  /etc/eks/eni-max-pods.txt
```

## Prefix Delegation 모드

### 왜 필요한가

Secondary IP 모드의 한계는 명확하다. t3.medium이 17개, m5.large가 29개. 이 한계를 넘으려면 인스턴스를 키워야 한다. Pod 하나의 리소스 요구가 적은 워크로드(배치 작업, 소형 마이크로서비스)라면 비효율이 크다.

Prefix Delegation은 secondary IP 슬롯마다 단일 IP 대신 `/28` 블록(16개 IP)을 할당하는 방식이다. ENI 슬롯 하나가 IP 16개를 품는다.

### /28 블록 단위 할당 구조

```
m5.large (3 ENI, ENI당 IP 슬롯 10개)

Secondary IP 모드:
  secondary IP 슬롯: (10-1) × 3 = 27 → max_pods = 29

Prefix Delegation 모드:
  secondary IP 슬롯: (10-1) × 3 = 27 슬롯
  각 슬롯에 /28 할당: 27 × 16 = 432 IPs
  (kubelet max-pods 상한이 별도로 적용됨)
```

VPC에서 /28 내의 IP는 모두 사용 가능하다. 일반 서브넷 블록과 달리 prefix 내부에서 reserved IP가 없다. 16개 전부 pod에 배정할 수 있다.

### 활성화

Nitro 기반 인스턴스에서만 동작한다. t3는 Nitro이므로 가능하다. t2는 Xen 기반이라 불가능.

```bash
# VPC CNI에서 prefix delegation 활성화
kubectl set env daemonset aws-node \
  -n kube-system \
  ENABLE_PREFIX_DELEGATION=true \
  WARM_PREFIX_TARGET=1
```

활성화 후 새로 생성되는 노드부터 적용된다. 기존 노드는 재기동이 필요하다.

kubelet의 `--max-pods`도 함께 올려야 한다. Prefix Delegation으로 IP가 많아져도 max-pods 설정이 낮으면 소용이 없다.

```bash
# launch template이나 user data에서 bootstrap 호출 시
/etc/eks/bootstrap.sh my-cluster \
  --use-max-pods false \
  --kubelet-extra-args '--max-pods=110'
```

EKS 관리형 노드 그룹은 launch template에서 user data를 커스터마이징하거나, `eks:compute-type` 관련 설정을 통해 max-pods를 재정의한다.

### 서브넷 크기 주의

Prefix Delegation을 쓰면 서브넷에서 /28 블록 단위로 IP를 소비한다.

/24 서브넷(실사용 251 IP)에 Prefix Delegation 노드를 10대 붙이는 경우다.
- 노드당 /28 프리픽스를 27개 슬롯에 잡으면 노드당 최대 432 IP 소비
- 10대면 수천 IP → /24로는 절대 모자란다

Prefix Delegation 도입 전에 서브넷을 /20 이상으로 재설계해야 한다. 기존 /24 서브넷에서 바로 켜면 노드가 뜨자마자 IP 고갈이 날 수 있다.

## Too many pods 디버깅

### 증상

Pod가 Pending 상태이고 이벤트에 이런 메시지가 찍힌다.

```
0/3 nodes are available: 3 Too many pods.
```

또는:

```
node "ip-10-0-1-100.ec2.internal" has 17 out of 17 pods.
```

### 진단 절차

노드별 Pod 현황부터 확인한다.

```bash
# 노드별 할당 가능한 Pod 수와 현재 사용량
kubectl describe nodes | grep -E "Name:|Non-terminated Pods:|pods:"

# 한눈에 비교
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
MAX_PODS:.status.allocatable.pods,\
CPU:.status.allocatable.cpu,\
MEM:.status.allocatable.memory
```

max-pods에 걸린 노드를 찾았다면 원인은 두 가지 중 하나다.

첫째, max-pods 값 자체가 낮게 설정된 경우다. bootstrap 설정이 잘못됐거나, 인스턴스 타입에 맞지 않는 값이 하드코딩된 경우다. 이때는 노드를 올바른 max-pods 값으로 교체한다.

둘째, 인스턴스 타입의 ENI/IP 한계 자체가 낮은 경우다. t3.medium에 Pod를 17개 넘게 올리려 한다면 인스턴스 타입을 바꾸거나 Prefix Delegation을 도입해야 한다.

```bash
# 노드의 인스턴스 타입 확인
kubectl get node <node> -o jsonpath='{.metadata.labels.node\.kubernetes\.io/instance-type}'

# 해당 인스턴스의 ENI/IP 스펙 확인
aws ec2 describe-instance-types \
  --instance-types t3.medium \
  --query 'InstanceTypes[].[InstanceType,NetworkInfo.MaximumNetworkInterfaces,NetworkInfo.Ipv4AddressesPerInterface]' \
  --output table
```

### ENI/IP 고갈과 Pod Pending 구분

"Too many pods"가 아니라 ENI나 IP 고갈로 Pod가 Pending에 걸리는 경우도 있다. 이때는 이벤트 메시지가 다르다.

```
Failed to create pod sandbox:
  rpc error: code = Unknown
  desc = failed to set up sandbox container network:
  add cmd: failed to assign an IP address to container
```

이 에러는 max-pods 설정은 여유 있는데 실제 secondary IP가 소진된 경우다. 원인은 세 가지가 흔하다.

warm pool이 IP를 과다하게 예약한 경우, 서브넷이 작아 IP 자체가 부족한 경우, ENI 생성이 계속 실패하는 경우(IAM 권한 문제가 가장 많다)다.

```bash
# 서브넷의 가용 IP 확인
aws ec2 describe-subnets \
  --subnet-ids subnet-xxxx \
  --query 'Subnets[].AvailableIpAddressCount'

# 노드의 ENI 상태 확인
aws ec2 describe-network-interfaces \
  --filters "Name=attachment.instance-id,Values=i-xxxxx" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,IPs:PrivateIpAddressCount,Status:Status}'

# VPC CNI 로그에서 에러 확인
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100 | grep -i error
```

IAM 권한 문제인지 확인하려면 `aws-node` Pod 로그에서 `failed to create` 또는 `UnauthorizedOperation`을 찾는다. `aws-node`는 노드 role에 `AmazonEKS_CNI_Policy`가 붙어 있어야 ENI를 생성할 수 있다.

### 빠른 조치

서브넷 IP 고갈이면 EKS 노드 그룹 설정에 서브넷을 하나 더 추가한다. 새 노드는 여유 있는 서브넷을 쓴다.

warm pool이 IP를 너무 많이 잡는 경우 `WARM_ENI_TARGET`을 줄이고 노드를 rolling update한다.

max-pods 값이 잘못 설정된 경우 인스턴스 타입에 맞는 값을 bootstrap에 명시적으로 넣고 노드를 교체한다.

## EKS ENI Trunking — Security Groups for Pods

ECS의 ENI Trunking과 이름이 같지만 목적이 다르다. EKS ENI Trunking은 Pod에 독립적인 보안 그룹을 붙이기 위한 기능이다.

기본 VPC CNI에서는 Pod가 노드의 보안 그룹을 공유한다. 결제 서비스 Pod와 공통 API Pod가 같은 노드에 있으면 보안 그룹 수준에서 인바운드/아웃바운드를 분리할 수 없다. Pod 단위 보안 그룹이 필요한 경우에 이 기능을 쓴다.

### 동작 방식

트렁크 ENI 하나가 노드에 붙고, 보안 그룹이 지정된 Pod는 branch ENI를 받아 자신만의 보안 그룹을 가진다.

```
노드 (m5.large)
├── Primary ENI (eth0) — 노드 자체
├── Trunk ENI — Security Groups for Pods 전용
│   ├── Branch ENI → Pod A (SG: sg-payment-service)
│   ├── Branch ENI → Pod B (SG: sg-internal-api)
│   └── Branch ENI → Pod C (SG: sg-data-processor)
└── 일반 secondary IP → SecurityGroupPolicy 없는 Pod들 (노드 SG 공유)
```

### 활성화와 설정

Nitro 기반 인스턴스에서만 동작한다.

```bash
# VPC CNI에서 Pod ENI 활성화
kubectl set env daemonset aws-node \
  -n kube-system \
  ENABLE_POD_ENI=true
```

`SecurityGroupPolicy` 리소스로 특정 Pod에 보안 그룹을 지정한다.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: payment-service-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: payment-service
  securityGroups:
    groupIds:
    - sg-0abc123def456789
```

### 주의사항

인스턴스 타입마다 trunk에 붙을 수 있는 branch ENI 수가 다르다. m5.large는 최대 54개 branch ENI를 지원한다. 실제로는 max-pods 값이 branch ENI 한계보다 먼저 병목이 되므로, 수치 자체보다 "Nitro 기반인가"가 더 중요한 선택 기준이다.

`SecurityGroupPolicy`가 없는 Pod는 기존 secondary IP 방식으로 동작한다. 두 방식이 한 노드에서 혼재할 수 있다.

branch ENI 할당에 몇 초가 걸린다. 보안 그룹 정책이 붙은 Pod는 일반 Pod보다 시작이 약간 느리다.

## 인스턴스 타입 선택 기준

### Pod 밀도 중심 선택

Pod 밀도만 본다면 m5/c5 계열이 t3보다 유리하다. 같은 ENI 수여도 ENI당 IP가 많기 때문이다.

| 인스턴스 | vCPU | 메모리 | max_pods | Nitro |
|---------|------|--------|---------|-------|
| t2.medium | 2 | 4GB | 17 | X |
| t3.medium | 2 | 4GB | 17 | O |
| t3.large | 2 | 8GB | 35 | O |
| m5.large | 2 | 8GB | 29 | O |
| m5.xlarge | 4 | 16GB | 58 | O |
| m5.2xlarge | 8 | 32GB | 58 | O |
| m5.4xlarge | 16 | 64GB | 234 | O |
| c5.xlarge | 4 | 8GB | 58 | O |
| c5.4xlarge | 16 | 32GB | 234 | O |

t3.large(max 35)가 m5.large(max 29)보다 Pod 밀도가 높다. t3.large는 ENI당 IP가 12개인 반면 m5.large는 10개라서 그렇다. 비용이 중요하고 Prefix Delegation을 안 쓴다면 t3.large가 Pod 밀도 측면에서 더 나은 선택이다.

m5.2xlarge와 m5.xlarge의 max_pods가 동일하다는 점이 실무에서 자주 놓치는 부분이다. CPU/메모리는 두 배 차이지만 ENI 스펙이 같아 Pod 밀도는 같다. Pod당 CPU 요청이 낮고 Pod 수가 중요하다면 m5.xlarge를 여러 대 쓰는 게 낫다.

### Nitro 기반이어야 하는 이유

Nitro 기반이 아닌 인스턴스(주로 t2 계열)는 다음 기능을 쓸 수 없다.

- Prefix Delegation
- Security Groups for Pods (ENI Trunking)
- ENA 기반 고성능 네트워킹 일부

t2로 시작한 클러스터를 나중에 t3로 마이그레이션하면서 이 기능들을 도입하려 할 때 문제가 된다. 처음부터 t3 이상이나 m5/c5 계열을 쓰는 게 맞다.

```bash
# Nitro 여부 확인
aws ec2 describe-instance-types \
  --instance-types t3.medium m5.large t2.medium \
  --query 'InstanceTypes[].[InstanceType,Hypervisor]' \
  --output table

# 출력 예시
# t3.medium   nitro
# m5.large    nitro
# t2.medium   xen   ← Prefix Delegation, ENI Trunking 불가
```

### Prefix Delegation 도입 시 선택 기준

Prefix Delegation을 쓰면 max_pods 한계가 대폭 올라가 인스턴스 선택 기준이 달라진다.

```
m5.large + Prefix Delegation:
  secondary IP 슬롯: (3 ENI × 9슬롯) = 27슬롯
  prefix당 16 IP: 27 × 16 = 432 IPs
  실제: kubelet max-pods를 110으로 설정 → m5.large 한 대에 100개 이상 수용 가능
```

이 모드에서는 CPU/메모리가 먼저 병목이 되므로, 인스턴스 타입 선택은 Pod의 리소스 요구에 맞춰 한다. ENI 한계는 더 이상 주요 변수가 아니다.

서브넷 크기가 대신 병목이 된다. /28 단위로 IP를 소비하므로 서브넷을 /20 이상으로 잡아야 여유가 생긴다. Prefix Delegation을 도입하기로 했다면 서브넷 재설계를 먼저 한다.

## 참조

- [VPC CNI GitHub](https://github.com/aws/amazon-vpc-cni-k8s)
- [EKS max-pods 값 표](https://github.com/awslabs/amazon-eks-ami/blob/master/files/eni-max-pods.txt)
- [Security Groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Prefix Delegation 설정](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [VPC CNI 환경 변수 레퍼런스](https://github.com/aws/amazon-vpc-cni-k8s/blob/master/README.md#cni-configuration-variables)
