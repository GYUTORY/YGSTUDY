---
title: EKS 비용 절감
tags: [aws, eks, kubernetes, Karpenter, cost, FinOps]
---

# EKS 비용 절감

EKS 청구서는 ECS보다 새는 지점이 한 층 더 많다. ECS는 태스크와 인스턴스 두 층만 보면 되지만, EKS는 컨트롤 플레인 고정비, 노드(EC2), 그 위에 뜬 Pod의 requests/limits까지 세 층이 겹친다. 그리고 이 세 층은 서로 어긋난다. Pod가 실제로 500MB를 쓰는데 requests에 2GB를 박아두면, 스케줄러는 2GB 기준으로 노드를 잡는다. 실사용은 낮은데 노드는 계속 늘어나는 상황이 여기서 생긴다.

[ECS 비용 산정과 절감](ECS_Cost_Optimization.md)이 Fargate와 EC2 모드의 태스크 단위 과금을 다뤘다면, 이 문서는 Kubernetes 레이어에서 돈이 새는 지점을 잡는다. 노드 점유율을 어떻게 올리는지, requests/limits 과다 설정을 어떻게 찾는지, Spot 노드풀을 어떻게 구성하는지가 중심이다. EKS 자체 구조는 [EKS](EKS.md)에, 컨테이너 밖의 인프라 비용은 [인프라 비용 최적화](../../../DevOps/Principles/Infrastructure_Cost_Optimization.md)에 있다.

## 컨트롤 플레인 고정비와 소규모 클러스터

EKS는 클러스터 하나당 컨트롤 플레인 요금을 시간당 $0.10 받는다. 한 달이면 $73이다. 노드가 몇 대든, Pod가 몇 개든 이 금액은 고정이다.

문제는 클러스터를 용도별로 쪼갤 때다. dev, staging, qa, 팀별 샌드박스를 각각 별도 클러스터로 만들면 클러스터 5개에 컨트롤 플레인만 월 $365다. 각 클러스터에 노드가 2~3대씩만 떠 있는 소규모라면, 컴퓨팅보다 컨트롤 플레인 고정비 비중이 더 커지는 역전이 일어난다.

소규모 비프로덕션 클러스터는 네임스페이스로 통합하는 게 싸다. dev와 staging을 한 클러스터에 네임스페이스로 나누고 RBAC와 NetworkPolicy로 격리하면 컨트롤 플레인 하나($73)로 끝난다. 프로덕션은 blast radius 때문에 따로 두더라도, 비프로덕션 클러스터 3~4개를 하나로 합치면 월 $200 안팎이 그냥 빠진다.

통합을 망설이게 하는 건 보통 격리 우려인데, 실제로는 다음 정도면 충분하다.

- 네임스페이스별 ResourceQuota로 팀이 클러스터 전체를 잡아먹지 못하게 막는다.
- NetworkPolicy로 네임스페이스 간 통신을 차단한다.
- IRSA(IAM Roles for Service Accounts)로 네임스페이스별 AWS 권한을 분리한다.

이 세 가지가 안 되는 강한 격리 요구(규제, 고객사 분리)가 있을 때만 클러스터를 나눈다. 그게 아니면 "왠지 분리해두면 안전할 것 같아서" 나눈 클러스터들이 컨트롤 플레인 고정비만 배로 물고 있는 경우가 대부분이다.

## Karpenter로 노드 점유율 올리기

EKS 비용의 대부분은 노드(EC2)다. 그리고 노드에서 새는 돈은 대부분 빈 공간이다. m5.2xlarge(8 vCPU, 32GB) 한 대를 띄웠는데 Pod가 3 vCPU, 12GB만 쓰고 있으면 나머지 절반은 돈만 내고 논다.

Karpenter는 Pod가 Pending 상태가 되면 그 Pod들의 requests를 실시간으로 보고 딱 맞는 인스턴스 타입을 골라 노드를 띄운다. Cluster Autoscaler처럼 미리 정의된 노드그룹의 인스턴스 타입에 갇히지 않고, 여러 타입 중 그 순간 가장 싸게 채울 수 있는 조합을 고른다.

### bin-packing과 consolidation

Karpenter의 핵심은 두 동작이다. 하나는 스케줄 시점의 bin-packing이고, 하나는 운영 중의 consolidation이다.

bin-packing은 Pending Pod들을 모아서 가장 적은 노드에 빽빽하게 채우는 것이다. 작은 Pod 10개가 뜰 때 작은 노드 10대를 띄우는 대신 큰 노드 1대에 몰아넣는 쪽이 싸면 그렇게 한다.

consolidation은 이미 떠 있는 노드를 주기적으로 다시 보고, "이 노드의 Pod들을 다른 노드로 옮기면 이 노드를 없앨 수 있는가", "이 노드를 더 싼 인스턴스로 바꿀 수 있는가"를 판단해 실제로 재배치한다. Cluster Autoscaler에는 없는 동작이다. 트래픽이 빠져서 Pod가 줄면, Karpenter가 남은 Pod를 몇 대에 모으고 빈 노드를 종료한다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-cpu
          operator: In
          values: ["4", "8", "16"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: 1000
```

`consolidationPolicy: WhenEmptyOrUnderutilized`가 저활용 노드까지 정리 대상에 넣는 설정이다. `WhenEmpty`로 두면 완전히 빈 노드만 없애고 저활용 노드는 그대로 둔다. 비용을 줄이려면 `WhenEmptyOrUnderutilized`를 쓴다. 대신 consolidation은 Pod를 재배치하므로 짧은 순간 Pod가 다시 뜬다. 상태를 가진 워크로드나 재시작에 민감한 서비스는 PodDisruptionBudget으로 동시에 내려가는 Pod 수를 제한해야 한다.

`requirements`에 인스턴스 타입을 넓게 열어두는 게 중요하다. c/m/r 패밀리에 4/8/16 vCPU를 다 허용하면 Karpenter가 그 순간 Pending Pod들을 가장 싸게 담을 조합을 고른다. 타입을 좁게 잠그면 bin-packing 여지가 줄어든다.

### Cluster Autoscaler와 비용 관점 비교

둘 다 노드를 늘리고 줄이지만 비용 관점에서 갈리는 지점이 있다.

Cluster Autoscaler는 미리 만든 노드그룹(ASG) 단위로 동작한다. 노드그룹의 인스턴스 타입이 고정이라, 작은 Pod 하나가 Pending이어도 그 노드그룹의 정해진 타입(예: m5.2xlarge)을 통째로 띄운다. Pod가 0.5 vCPU만 필요해도 8 vCPU 노드가 뜨는 낭비가 생긴다. 여러 크기를 대응하려면 노드그룹을 크기별로 여러 개 만들어야 하는데, 관리가 늘고 여전히 딱 맞진 않는다.

Karpenter는 노드그룹 개념 없이 Pending Pod의 실제 requests를 보고 인스턴스를 고른다. 작은 Pod면 작은 노드, 큰 Pod면 큰 노드를 그때그때 띄운다. 여기에 consolidation까지 있어서, 시간이 지나며 어긋난 배치를 스스로 조인다.

정리하면 이렇다.

- 워크로드 크기가 일정하고 종류가 적다 → Cluster Autoscaler로도 충분하다. 노드그룹 몇 개면 낭비가 크지 않다.
- Pod 크기가 제각각이고 트래픽 변동이 크다 → Karpenter. 인스턴스 선택 유연성과 consolidation에서 오는 절감폭이 크다.
- Spot을 적극 쓰고 싶다 → Karpenter. 여러 인스턴스 타입을 한 풀에서 섞어 Spot 회수 위험을 분산하기 쉽다.

Cluster Autoscaler에서 Karpenter로 옮긴 뒤 노드 대수가 20~30% 줄어드는 경우를 자주 본다. 대부분 consolidation이 그동안 방치돼 있던 저활용 노드를 정리한 결과다.

## Spot 노드풀과 동시 회수 확률 낮추기

Spot 인스턴스는 온디맨드 대비 60~70% 싸다. EKS에서 Spot을 쓰는 핵심 주의점은 동시 회수다. 한 인스턴스 타입에만 의존하면, 그 타입의 Spot 풀이 회수될 때 그 타입으로 뜬 노드가 한꺼번에 사라진다.

방어는 인스턴스 타입 다양화다. Karpenter NodePool의 `requirements`에 여러 패밀리와 여러 크기를 열어두면, Karpenter가 서로 다른 Spot 풀에서 노드를 가져온다. c5.2xlarge 풀이 회수돼도 m5.2xlarge, r5.xlarge 노드는 살아 있다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["4"]
      taints:
        - key: spot
          value: "true"
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
```

`instance-generation > 4`로 최신 세대만 허용하되, 카테고리는 c/m/r을 다 열었다. 이렇게 하면 Karpenter가 선택할 수 있는 Spot 풀이 수십 개로 늘어난다. 동시에 전부 회수될 확률이 급격히 떨어진다. 인스턴스 타입을 하나로 고정하는 건 Spot에서 가장 하지 말아야 할 설정이다.

taints를 걸어둔 이유는 워크로드를 골라 받기 위해서다. Spot 노드에는 회수를 견딜 수 있는 워크로드만 tolerations로 올린다. 상태를 가진 DB, 회수되면 곤란한 결제 서비스는 온디맨드 NodePool에 두고, 무상태 웹/배치는 Spot NodePool에 태운다. 이 분리를 안 하면 Spot 회수 때마다 중요한 서비스가 같이 흔들린다.

온디맨드와 Spot을 섞는 실전 구성은 이렇다.

- 온디맨드 NodePool: 상태 있는 워크로드, 최소 보장이 필요한 baseline Pod. taint 없음.
- Spot NodePool: 무상태·재시작 견디는 워크로드. taint로 명시적 opt-in만 받음.
- 각 Deployment의 tolerations와 nodeAffinity로 어느 풀에 태울지 결정.

Karpenter는 Spot 회수 알림(2분 전)을 받으면 해당 노드를 cordon하고 Pod를 다른 노드로 미리 옮긴다. 이 동작 덕에 회수 충격이 줄지만, 옮길 곳이 있어야 한다. Spot 풀을 넓게 열어두는 게 여기서도 효과를 낸다.

## requests/limits 과다 설정이 노드 수를 부풀린다

EKS에서 가장 흔하고 가장 크게 새는 구멍이다. Kubernetes 스케줄러는 Pod의 실사용이 아니라 **requests**를 기준으로 노드에 배치한다. requests에 2 vCPU, 4GB를 박아둔 Pod가 실제로는 0.3 vCPU, 800MB만 쓰고 있어도, 스케줄러는 노드에서 2 vCPU와 4GB를 이 Pod 몫으로 예약한다.

Pod마다 이렇게 과하게 잡으면 노드가 금방 "가득 찬" 것으로 계산되고, Karpenter든 Cluster Autoscaler든 새 노드를 띄운다. 실제 CPU/메모리는 30%만 쓰는데 노드는 계속 늘어난다. 청구서는 실사용이 아니라 requests 합에 비례한다.

### over-provisioned requests 찾기

먼저 실제 사용량과 requests의 격차를 눈으로 본다. metrics-server가 깔려 있으면 `kubectl top`으로 실사용을 본다.

```bash
# Pod별 실제 CPU/메모리 사용량
kubectl top pods -A --sort-by=memory

# 노드별 실사용
kubectl top nodes
```

그다음 requests와 비교한다. 아래는 Pod의 이름, CPU requests, 메모리 requests를 뽑는다.

```bash
kubectl get pods -A -o custom-columns=\
'NS:.metadata.namespace,POD:.metadata.name,\
CPU_REQ:.spec.containers[*].resources.requests.cpu,\
MEM_REQ:.spec.containers[*].resources.requests.memory'
```

`kubectl top`의 실사용과 이 requests를 나란히 놓으면, requests가 실사용의 3~5배인 Pod가 드러난다. 그게 노드를 부풀리는 주범이다.

노드 관점에서 예약과 실사용의 격차를 한 번에 보려면 `kubectl describe node`의 Allocated resources를 본다.

```bash
kubectl describe node <node-name> | grep -A 8 "Allocated resources"
```

여기서 CPU Requests가 90%인데 `kubectl top node`의 실 CPU가 25%라면, 그 노드는 requests상으로만 꽉 찬 것이다. 실제로는 Pod를 더 담을 수 있는데 requests 때문에 새 노드가 뜨고 있다는 신호다.

### VPA recommendation 모드로 실측 기반 조정

requests를 감으로 내리면 위험하다. 너무 내리면 실제 스파이크 때 CPU throttling이나 OOM이 난다. Vertical Pod Autoscaler(VPA)를 recommendation 모드로 돌리면, VPA가 실제 사용량을 관찰해서 적정 requests 값을 계산해준다.

`updateMode: "Off"`가 핵심이다. 이 모드에서 VPA는 Pod를 건드리지 않고 권장값만 계산한다. 자동으로 Pod를 재시작(`updateMode: Auto`)하지 않으므로 프로덕션에서도 안전하게 관찰만 할 수 있다.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
```

며칠 돌린 뒤 권장값을 본다.

```bash
kubectl describe vpa my-app-vpa
```

출력의 `Recommendation` 섹션에 Target(권장 requests), Lower Bound, Upper Bound가 나온다. Target을 새 requests의 출발점으로 삼되, 메모리는 Upper Bound에 가깝게 둔다. 메모리는 CPU와 달리 부족하면 throttling이 아니라 OOM으로 Pod가 죽기 때문이다. CPU는 Target 근처로 내려도 부족하면 느려질 뿐 죽지 않으니 더 공격적으로 내릴 수 있다.

VPA 권장값을 반영해 requests를 실측 기준으로 맞추면, 노드에 담기는 Pod 밀도가 올라가고 노드 대수가 줄어든다. requests 과다가 노드를 부풀리던 구조가 여기서 풀린다.

주의할 점이 있다. VPA `Auto` 모드는 requests를 바꾸려고 Pod를 재시작한다. 프로덕션에서 이걸 켜두면 예고 없이 Pod가 재시작되니, 관찰은 `Off`로 하고 값 반영은 배포 파이프라인에서 사람이 확인한 뒤 하는 게 안전하다. 그리고 VPA와 HPA를 같은 지표(CPU/메모리)로 동시에 걸면 서로 싸운다. HPA를 CPU로 걸었다면 VPA는 메모리만 조정하도록 분리한다.

## HPA 최소 replica 과다 설정 찾기

requests가 Pod 하나의 크기를 부풀린다면, HPA의 `minReplicas`는 Pod 개수를 바닥부터 부풀린다. 트래픽이 없는 새벽에도 minReplicas만큼은 항상 떠 있고, 그만큼 노드도 유지된다.

```bash
kubectl get hpa -A -o custom-columns=\
'NS:.metadata.namespace,NAME:.metadata.name,\
MIN:.spec.minReplicas,MAX:.spec.maxReplicas,\
CURRENT:.status.currentReplicas,TARGET:.spec.metrics[0].resource.target.averageUtilization'
```

여기서 `CURRENT`가 항상 `MIN`과 같고 며칠째 안 올라가는 HPA가 있으면, minReplicas가 실제 필요보다 높게 잡힌 것이다. 처음 만들 때 불안해서 minReplicas를 4로 잡았는데 트래픽은 1~2개면 충분한 경우가 흔하다.

새벽 트래픽 바닥에 맞춰 minReplicas를 1~2로 내리고, maxReplicas로 낮 스파이크를 받게 둔다. 내부 서비스처럼 밤에 트래픽이 0에 가깝다면 minReplicas를 1로 두는 것만으로 야간 노드 유지비가 빠진다.

단, minReplicas를 내릴 때 콜드 스타트를 본다. minReplicas 1에서 트래픽이 갑자기 몰리면 스케일 아웃이 따라잡기 전까지 남은 Pod에 부하가 걸린다. 스케일 아웃이 느린 워크로드(JVM 워밍업 등)는 minReplicas를 바닥까지 내리지 말고 baseline을 남긴다.

## Fargate profile vs 관리형 노드그룹 실비용

EKS도 Fargate를 쓸 수 있다. Fargate profile에 매칭되는 Pod는 노드 없이 뜨고, Pod당 vCPU·메모리를 초 단위로 과금한다. 관리형 노드그룹은 EC2 인스턴스 요금을 통째로 낸다.

어느 쪽이 싼지는 [ECS의 Fargate vs EC2 계산](ECS_Cost_Optimization.md)과 같은 논리다. 노드를 얼마나 빽빽하게 채우느냐가 갈림길이다.

Pod가 적고 띄엄띄엄 뜨는 워크로드는 Fargate가 싸다. 노드를 띄우면 그 위에 Pod 하나만 올라가도 인스턴스 요금을 다 내는데, Fargate는 그 Pod 몫만 낸다. 배치 잡, 가끔 도는 크론 잡, 트래픽이 드문 내부 도구가 여기 해당한다.

반대로 Pod가 많고 노드를 80% 이상 채울 수 있으면 관리형 노드그룹이 싸다. Fargate는 Pod마다 약간의 오버헤드(요청한 크기보다 조금 큰 단위로 올림)가 붙고, Spot이나 Savings Plans, Graviton 같은 추가 절감 수단을 붙이기 어렵다. Karpenter로 노드를 빽빽하게 채우고 Spot·Graviton을 섞으면 노드그룹 쪽 단가가 더 내려간다.

실전 구성은 섞는 쪽이 많다.

- 시스템 컴포넌트(CoreDNS 등 소수 상시 Pod), 가끔 도는 배치 → Fargate profile. 이걸 위해 노드를 상시 띄울 이유가 없다.
- 트래픽 받는 주력 워크로드 → Karpenter가 관리하는 Spot/온디맨드 노드. 밀도를 올려 단가를 낮춘다.

컨트롤 플레인이 클러스터당 고정이라, Fargate만 쓰든 노드그룹만 쓰든 $73은 똑같이 든다는 점은 기억한다.

## 유휴 dev 네임스페이스 야간 스케일 다운

개발·스테이징 워크로드는 업무 시간에만 필요한 경우가 대부분인데, 밤과 주말에도 그대로 떠서 노드를 붙잡고 있다. 24시간 × 7일 중 실제 쓰는 건 주 40시간 남짓이니, 나머지 130시간 가까이가 낭비다.

CronJob으로 밤에 Deployment를 0으로 스케일 인하고 아침에 되돌린다.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-down-dev
  namespace: dev
spec:
  schedule: "0 20 * * 1-5"   # 평일 20시 (KST면 cluster 타임존 확인)
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: scaler
          containers:
            - name: kubectl
              image: bitnami/kubectl
              command:
                - /bin/sh
                - -c
                - kubectl scale deployment --all --replicas=0 -n dev
          restartPolicy: OnFailure
```

아침 스케일 업은 같은 형태로 `schedule: "0 8 * * 1-5"`에 `--replicas=1`(또는 원래 값)로 만든다. Pod가 0이 되면 Karpenter가 빈 노드를 consolidation으로 정리하니, Deployment만 0으로 내려도 노드 비용까지 같이 빠진다. 이게 노드 스케일 다운과 맞물리는 지점이다. Pod만 0으로 만들고 노드 정리가 안 되면 절반만 아끼는 것이다.

serviceAccount에는 해당 네임스페이스의 Deployment를 scale할 수 있는 RBAC만 준다. 전체 클러스터 권한을 주면 사고 위험이 커진다.

스케일 대상 replica 원값을 기억해야 아침에 제대로 복구된다. `--replicas=0` 전에 annotation에 원래 replica 수를 저장해두거나, 되돌릴 때 고정값을 쓰는 식으로 처리한다. Deployment마다 원 replica가 다르면 이 부분을 스크립트로 챙겨야 한다.

## Graviton 노드로 전환

Graviton(ARM 기반, c7g·m7g·r7g 등)은 같은 성능의 x86 인스턴스보다 대략 20% 싸고, 워크로드에 따라 성능당 가격이 더 낫다. EKS에서 Graviton으로 옮기는 건 노드 타입만 바꾸는 게 아니라 컨테이너 이미지가 ARM64를 지원해야 한다는 조건이 붙는다.

이미지가 멀티아키(linux/amd64 + linux/arm64) manifest로 빌드돼 있으면, 노드가 ARM이든 x86이든 알아서 맞는 이미지를 당긴다. 대부분의 공식 베이스 이미지(Alpine, Debian, 언어 런타임)는 이미 멀티아키를 제공한다. 문제는 사내 이미지다. `docker buildx`로 arm64를 같이 빌드해두지 않으면 Graviton 노드에서 `exec format error`가 난다.

```yaml
# Karpenter NodePool에서 arm64 허용
requirements:
  - key: kubernetes.io/arch
    operator: In
    values: ["arm64"]
```

전환 순서는 이렇게 잡는다.

- 이미지 빌드 파이프라인에서 `docker buildx build --platform linux/amd64,linux/arm64`로 멀티아키 이미지를 만든다.
- 워크로드 하나를 Graviton NodePool에 태워 정상 동작을 확인한다. 네이티브 의존성(특정 C 라이브러리, JNI)이 있으면 여기서 걸린다.
- 문제없으면 무상태 워크로드부터 순차 전환한다.

x86과 ARM을 한 클러스터에 섞을 수 있으니 한 번에 다 옮길 필요는 없다. 검증된 워크로드부터 Graviton NodePool로 넘기고, 아직 ARM 이미지가 없는 것들은 x86 NodePool에 남긴다. Karpenter는 Pod의 nodeAffinity(`kubernetes.io/arch`)를 보고 맞는 노드를 띄운다.

## 실사용량을 어디서 확인하나

절감 작업은 실측으로 시작해서 실측으로 검증한다. 감으로 requests를 내리거나 노드를 줄이면 장애로 돌아온다.

- **Container Insights**: EKS 클러스터·노드·Pod 단위 CPU/메모리 사용률을 CloudWatch로 보낸다. 노드 점유율과 Pod requests 대비 실사용을 시계열로 본다. right-sizing 전후 비교의 근거가 된다.
- **kubecost (또는 OpenCost)**: 네임스페이스·Deployment·라벨 단위로 비용을 쪼개준다. Kubernetes는 기본적으로 "어느 팀이 얼마 쓰는지"를 AWS 청구서에서 못 나누는데(다 같은 노드 EC2 요금으로 뭉쳐 나온다), kubecost가 requests·실사용 기준으로 비용을 배분한다. 어느 네임스페이스가 노드를 잡아먹는지 여기서 드러난다.
- **kubectl top + describe node**: 지금 이 순간의 실사용과 requests 격차를 즉석에서 본다. 위에서 쓴 쿼리들이 여기 해당한다.
- **Cost Explorer**: 클러스터 전체 EC2·EKS 비용의 월 추이. 태그로 클러스터를 구분해두면 클러스터 단위 비용이 분해된다.

kubecost를 안 깔면 "노드 비용이 줄었다"까지는 알아도 "어느 워크로드 덕에 줄었는지"를 못 짚는다. 네임스페이스별 비용을 봐야 다음에 어디를 손댈지가 보인다. 먼저 깔아두는 게 낫다.

## 참고

- [ECS 비용 산정과 절감](ECS_Cost_Optimization.md) — Fargate/EC2 모드 태스크 단위 과금
- [EKS](EKS.md) — 클러스터 구조와 핵심 개념
- [인프라 비용 최적화](../../../DevOps/Principles/Infrastructure_Cost_Optimization.md) — 컨테이너 밖 인프라 비용
- [Karpenter 공식 문서](https://karpenter.sh/)
- [Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [kubecost / OpenCost](https://www.opencost.io/)
