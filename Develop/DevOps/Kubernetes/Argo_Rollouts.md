---
title: Argo Rollouts
tags: [kubernetes, devops]
updated: 2026-08-06
---

# Argo Rollouts

## 1. Argo Rollouts란

Kubernetes 기본 Deployment는 롤링 업데이트만 지원한다. 배포 중간에 트래픽을 얼마나 보낼지, 에러율이 높아지면 자동으로 멈출지 같은 제어는 기본 스펙에 없다.

Argo Rollouts는 `Rollout`이라는 CRD로 Deployment를 대체해서 이런 제어를 가능하게 한다. BlueGreen과 Canary 두 가지 배포 방식을 지원하고, Prometheus 같은 메트릭 소스와 연동해서 지표가 나빠지면 자동으로 롤백한다.

설치는 Helm으로 하는 게 관리하기 편하다.

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argo-rollouts argo/argo-rollouts \
  --namespace argo-rollouts \
  --create-namespace
```bash

kubectl 플러그인도 같이 설치해야 `kubectl argo rollouts` 명령을 쓸 수 있다.

```bash
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x kubectl-argo-rollouts-linux-amd64
mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
```

---

## 2. BlueGreen 배포

BlueGreen은 구버전(blue)과 신버전(green)을 동시에 띄워놓고, 검증 후 트래픽을 한 번에 전환하는 방식이다. 전환 전까지 구버전이 그대로 살아있어서 문제가 생기면 빠르게 되돌릴 수 있다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 4
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:v2
          ports:
            - containerPort: 8080
  strategy:
    blueGreen:
      activeService: my-app-active       # 실 트래픽 서비스
      previewService: my-app-preview     # 신버전 확인용 서비스
      autoPromotionEnabled: false        # 수동 승인 전까지 대기
      scaleDownDelaySeconds: 60          # 전환 후 구버전 파드 유지 시간
      previewReplicaCount: 2             # 검증 중 신버전 파드 수
```

`autoPromotionEnabled: false`로 설정하면 신버전 파드가 준비되어도 자동으로 트래픽을 넘기지 않는다. 개발팀이 `previewService`로 직접 접속해서 확인한 다음 수동으로 승인해야 전환된다.

```bash
# 배포 상태 확인
kubectl argo rollouts get rollout my-app -n production

# 신버전으로 트래픽 전환
kubectl argo rollouts promote my-app -n production

# 구버전으로 즉시 롤백
kubectl argo rollouts undo my-app -n production
```

BlueGreen에서 가장 주의할 점은 데이터베이스 스키마다. 신버전이 구버전과 다른 스키마를 쓰면 `previewService`로 테스트하는 시점에 DB가 깨진다. 배포 전에 하위 호환 마이그레이션을 먼저 적용하고, 신버전 배포는 그다음에 해야 한다.

---

## 3. Canary 배포

Canary는 신버전에 트래픽을 조금씩 늘려가면서 배포하는 방식이다. 전체 사용자 중 일부만 신버전을 보다가 문제가 없으면 비율을 높인다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:v2
          ports:
            - containerPort: 8080
  strategy:
    canary:
      stableService: my-app-stable
      canaryService: my-app-canary
      trafficRouting:
        nginx:
          stableIngress: my-app-ingress
      steps:
        - setWeight: 10        # 트래픽 10%를 신버전으로
        - pause: {duration: 5m}
        - analysis:
            templates:
              - templateName: error-rate-check
        - setWeight: 30
        - pause: {duration: 5m}
        - analysis:
            templates:
              - templateName: error-rate-check
        - setWeight: 60
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: error-rate-check
        - setWeight: 100
```

`trafficRouting`에 nginx를 설정하면 Ingress 가중치를 자동으로 조정한다. Istio나 AWS ALB도 지원한다. 이 설정 없이 쓰면 파드 수 비율로만 트래픽이 분산되어서 정밀한 제어가 안 된다.

`steps` 배열이 순서대로 실행되고, `analysis` 스텝에서 메트릭을 검사한다. 지표가 기준치를 벗어나면 그 단계에서 멈추고 자동으로 이전 단계로 롤백한다.

---

## 4. AnalysisTemplate으로 자동 롤백

AnalysisTemplate은 배포 중에 메트릭을 주기적으로 검사하는 규칙이다. Prometheus와 연동하면 에러율이나 지연시간이 임계치를 넘을 때 Rollout을 자동으로 되돌린다.

### 에러율 기반 검사

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate-check
spec:
  metrics:
    - name: error-rate
      interval: 1m
      count: 5
      failureLimit: 1
      successCondition: result[0] < 0.05
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            sum(rate(http_requests_total{
              job="my-app",
              status=~"5..",
              version="{{args.canary-version}}"
            }[2m]))
            /
            sum(rate(http_requests_total{
              job="my-app",
              version="{{args.canary-version}}"
            }[2m]))
```

`count: 5`, `failureLimit: 1`이면 5번 측정 중 1번이라도 기준을 넘으면 실패로 처리한다. 프로덕션에서는 `failureLimit: 0`으로 설정하는 게 안전하다. 한 번이라도 에러율이 튀면 바로 롤백하는 쪽이 낫다.

### 지연시간 기반 검사

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-check
spec:
  metrics:
    - name: p99-latency
      interval: 1m
      count: 5
      failureLimit: 1
      successCondition: result[0] < 0.5
      provider:
        prometheus:
          address: http://prometheus.monitoring.svc.cluster.local:9090
          query: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{
                job="my-app",
                version="{{args.canary-version}}"
              }[2m])) by (le)
            )
```

p99 지연시간 0.5초 기준이다. 서비스마다 SLO가 다르니 값은 상황에 맞게 조정해야 한다.

두 템플릿을 함께 쓰려면 Rollout에서 둘 다 참조하면 된다.

```yaml
- analysis:
    templates:
      - templateName: error-rate-check
      - templateName: latency-check
    args:
      - name: canary-version
        value: v2
```

AnalysisRun 결과는 직접 확인할 수 있다.

```bash
# 현재 실행 중인 AnalysisRun 목록
kubectl get analysisrun -n production

# 특정 AnalysisRun 상세 확인
kubectl describe analysisrun my-app-canary-abc123 -n production
```

Prometheus 쿼리가 잘못됐거나 결과가 빈 배열이면 `Error` 상태로 처리된다. `inconclusiveLimit`을 설정해서 몇 번까지 불확실한 결과를 허용할지 지정하지 않으면 기본값이 0이라 쿼리 오류 한 번에 전체 배포가 실패한다.

```yaml
- name: error-rate
  interval: 1m
  count: 5
  failureLimit: 1
  inconclusiveLimit: 2    # 쿼리 오류 2번까지는 계속 진행
```

---

## 5. PodDisruptionBudget으로 최소 가용 파드 보장

Argo Rollouts가 배포 중 파드를 교체할 때, 동시에 너무 많은 파드가 내려가면 서비스가 끊긴다. PDB(PodDisruptionBudget)는 동시에 내릴 수 있는 파드 수를 제한한다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
  namespace: production
spec:
  selector:
    matchLabels:
      app: my-app
  minAvailable: 3    # 최소 3개는 항상 Running 상태 유지
```

`minAvailable` 대신 `maxUnavailable`을 써도 된다.

```yaml
spec:
  selector:
    matchLabels:
      app: my-app
  maxUnavailable: 1   # 동시에 최대 1개만 다운 허용
```

파드가 10개일 때 `maxUnavailable: 1`이면 배포 속도가 느려진다. 한 번에 하나씩만 교체하니까 10번을 순차로 해야 한다. 배포 속도와 가용성 사이에서 트레이드오프가 있다.

BlueGreen에서는 구버전 파드가 유지되는 동안 PDB가 신버전 파드에도 적용된다. `previewReplicaCount`가 PDB의 `minAvailable`보다 작으면 신버전 파드를 아예 못 띄우는 경우가 생긴다. Rollout YAML의 `previewReplicaCount`와 PDB 설정을 같이 검토해야 한다.

노드 장애나 드레인 상황에서도 PDB가 동작한다. `kubectl drain` 명령이 PDB를 위반하면 파드를 강제로 내리지 않고 대기한다. 노드 유지보수 시 PDB 때문에 드레인이 안 되는 경우가 있으니, 드레인 전에 복제본 수를 늘려두거나 PDB를 임시로 완화해야 한다.

---

## 6. kubectl-argo-rollouts 실무 명령어

배포 현황을 실시간으로 보는 게 기본이다.

```bash
# 배포 상태 실시간 확인 (watch 모드)
kubectl argo rollouts get rollout my-app -n production --watch

# 모든 Rollout 목록
kubectl argo rollouts list rollouts -n production
```

출력 예시:

```
Name:            my-app
Namespace:       production
Status:          ॥ Paused
Message:         CanaryPauseStep
Strategy:        Canary
  Step:          2/8
  SetWeight:     10
  ActualWeight:  10
Images:          my-app:v1 (stable)
                 my-app:v2 (canary)
Replicas:
  Desired:       10
  Current:       10
  Updated:       1
  Ready:         10
  Available:     10
```

Paused 상태에서 다음 단계로 수동 진행하거나 전체를 바로 승인할 수 있다.

```bash
# pause된 배포 다음 단계로 진행
kubectl argo rollouts promote my-app -n production

# 모든 남은 단계 건너뛰고 전체 배포 완료
kubectl argo rollouts promote my-app -n production --full

# 현재 배포 중단하고 이전 버전으로 롤백
kubectl argo rollouts undo my-app -n production

# 배포 중단 (트래픽은 현재 상태 유지)
kubectl argo rollouts pause my-app -n production

# 중단된 배포 재개
kubectl argo rollouts resume my-app -n production
```

이미지만 빠르게 바꿀 때는 Rollout을 직접 수정하지 않고 set image를 쓴다.

```bash
kubectl argo rollouts set image my-app my-app=my-app:v3 -n production
```

배포 히스토리를 보면 이전에 어떤 버전들을 썼는지 확인할 수 있다.

```bash
kubectl argo rollouts history rollout my-app -n production
```

---

## 7. Argo CD 연동 시 auto-sync 충돌 처리

Argo CD와 함께 쓸 때 가장 자주 겪는 문제가 auto-sync 충돌이다.

Argo Rollouts는 배포 중에 Rollout 리소스의 `status`와 `spec.template`을 계속 수정한다. Argo CD의 auto-sync는 Git 상태와 클러스터 상태가 다르면 무조건 Git으로 덮어쓴다. 배포 중간에 Argo CD가 끼어들어서 Rollout을 Git 상태로 되돌려버리는 상황이 생긴다.

이걸 막으려면 Argo CD Application에 `ignoreDifferences` 설정을 추가해야 한다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/repo
    targetRevision: HEAD
    path: k8s/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
  ignoreDifferences:
    - group: argoproj.io
      kind: Rollout
      jsonPointers:
        - /spec/replicas          # Rollout이 scale 조정 시 무시
        - /spec/paused            # pause 상태 무시
    - group: argoproj.io
      kind: AnalysisRun
      jsonPointers:
        - /status                 # AnalysisRun status 변경 무시
```

`/spec/replicas`를 무시해야 하는 이유가 있다. Rollout은 배포 단계에 따라 파드 수를 동적으로 조정하는데, HPA가 replicas를 변경하거나 Rollout 자체가 canary/stable 비율로 replicas를 바꾸면 Git에 있는 값과 달라진다. 이때 auto-sync가 Git 값으로 덮어쓰면 배포 흐름이 깨진다.

`selfHeal: true`는 유지하면서 `ignoreDifferences`로 예외 처리하는 게 맞다. `selfHeal`을 끄면 Argo CD가 드리프트를 방치해서 다른 문제가 생긴다.

배포 중에 Argo CD Application 상태가 `OutOfSync`로 표시되는 경우가 있다. Rollout 진행 중에는 정상이니 놀라지 않아도 된다. 배포가 완료되면 다시 `Synced`로 돌아온다. 단, 배포 완료 후에도 계속 `OutOfSync`면 `ignoreDifferences` 설정이 빠진 필드가 있는 것이다.

Argo CD UI에서 Rollout 상태를 보려면 Argo Rollouts 대시보드를 별도로 띄우는 게 편하다.

```bash
kubectl argo rollouts dashboard
```

기본 포트 3100으로 접속하면 전체 Rollout 목록과 배포 현황을 웹에서 볼 수 있다.
