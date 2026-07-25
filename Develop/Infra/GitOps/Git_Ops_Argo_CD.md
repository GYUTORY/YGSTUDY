---
title: ArgoCD 기반 GitOps
tags: [argocd, gitops, kubernetes, helm, kustomize, cd]
updated: 2026-07-25
---

# ArgoCD 기반 GitOps

GitOps는 Git 저장소를 단일 진실 공급원으로 두고, 클러스터 상태를 거기에 맞추는 방식이다. ArgoCD는 이 방식을 Kubernetes에 적용한 대표적인 도구다. ArgoCD를 몇 년 운영하면서 초기 설계 실수가 나중에 얼마나 큰 문제를 만드는지 직접 겪었다. Application과 AppProject 구조를 처음부터 잘 잡아야 한다.

## Application과 AppProject 설계

AppProject는 ArgoCD 내에서 Application들을 묶는 논리적 단위다. 팀별로, 또는 서비스 도메인별로 나눈다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: payment-team
  namespace: argocd
spec:
  description: Payment 팀 전용 프로젝트
  sourceRepos:
    - 'https://github.com/company/payment-service'
    - 'https://charts.company.internal/*'
  destinations:
    - namespace: payment-*
      server: https://kubernetes.default.svc
    - namespace: payment-*
      server: https://prod-cluster.company.internal
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
  namespaceResourceBlacklist:
    - group: ''
      kind: ResourceQuota
  roles:
    - name: developer
      description: 개발자 읽기 및 sync 권한
      policies:
        - p, proj:payment-team:developer, applications, get, payment-team/*, allow
        - p, proj:payment-team:developer, applications, sync, payment-team/*, allow
      groups:
        - payment-dev
```

`sourceRepos`는 화이트리스트 방식이라 등록하지 않은 저장소의 매니페스트는 배포할 수 없다. 와일드카드(`*`)를 쓰면 모든 저장소를 허용하는데, 프로덕션에서는 피하는 게 맞다. 한 번은 이 설정을 `*`로 열어두었다가 보안 감사에서 지적받았다.

Application은 실제 배포 단위다. 하나의 Git 경로와 하나의 클러스터 네임스페이스를 연결한다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payment-api
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: payment-team
  source:
    repoURL: https://github.com/company/payment-service
    targetRevision: main
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: payment
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - RespectIgnoreDifferences=true
```

`finalizers`에 `resources-finalizer.argocd.argoproj.io`를 붙이면 Application을 삭제할 때 클러스터의 실제 리소스도 같이 지운다. 붙이지 않으면 Application만 ArgoCD에서 사라지고 클러스터에는 리소스가 남는다. 운영 클러스터에서는 finalizer를 붙이지 않는 경우도 많다. 실수로 Application을 지웠을 때 클러스터 리소스까지 날아가는 상황을 막기 위해서다.

## Sync Policy: Auto vs Manual

Auto sync는 Git에 변경이 감지되면 자동으로 배포한다. Manual sync는 UI나 CLI에서 사람이 직접 트리거해야 한다.

프로덕션에서 auto sync를 쓸 때 `prune`과 `selfHeal` 설정이 핵심이다.

- `prune: true` — Git에서 삭제된 리소스를 클러스터에서도 삭제한다. 기본값은 false다. false면 Git에서 지워도 클러스터에는 남는다.
- `selfHeal: true` — 클러스터 상태가 Git과 달라지면 자동으로 되돌린다. kubectl로 직접 수정한 내용이 있으면 ArgoCD가 덮어쓴다.

`selfHeal`이 켜져 있으면 kubectl로 임시 수정이 불가능하다. 장애 상황에서 빠르게 수동 조치가 필요할 때 이 점이 발목을 잡는다. 이런 경우를 대비해 특정 필드만 무시하도록 설정하거나, Application sync를 일시 중단하는 방식으로 대응한다.

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: ""
      kind: ConfigMap
      name: feature-flags
      jsonPointers:
        - /data
```

`ignoreDifferences`를 쓰면 HPA가 레플리카 수를 조절해도 ArgoCD가 Git 값으로 되돌리지 않는다. 이 설정 없이 HPA와 ArgoCD를 함께 운영하면 서로 레플리카 수를 두고 충돌하는 상황이 생긴다.

환경별 sync 정책은 다르게 가져간다. 개발 환경은 auto sync + prune + selfHeal, 스테이징은 auto sync + prune만, 프로덕션은 manual sync가 실무에서 많이 쓰는 구성이다.

## PreSync/PostSync Hook

ArgoCD Hook은 sync 전후에 Job을 실행하는 기능이다. DB 마이그레이션이나 배포 후 smoke test에 쓴다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  template:
    spec:
      containers:
        - name: migration
          image: company/payment-api:20240715-abc1234
          command: ["python", "manage.py", "migrate", "--noinput"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: payment-db-secret
                  key: url
      restartPolicy: Never
  backoffLimit: 0
```

`hook-delete-policy`는 세 가지다.

- `BeforeHookCreation` — 다음 sync 때 같은 이름의 Hook이 있으면 기존 것을 먼저 지운다.
- `HookSucceeded` — Hook이 성공하면 즉시 삭제한다.
- `HookFailed` — Hook이 실패하면 삭제한다. 디버깅할 때는 이 정책을 쓰지 않는 게 낫다. 실패한 Job의 로그를 봐야 하니까.

PostSync Hook은 배포 후 검증에 쓴다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: test
          image: curlimages/curl:latest
          command:
            - /bin/sh
            - -c
            - |
              for i in $(seq 1 5); do
                STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://payment-api/health)
                if [ "$STATUS" = "200" ]; then
                  echo "Health check passed"
                  exit 0
                fi
                sleep 5
              done
              echo "Health check failed"
              exit 1
      restartPolicy: Never
```

Hook 실패 시 sync 자체가 실패로 처리된다. PreSync Hook이 실패하면 실제 매니페스트 적용이 안 된다. 그래서 Hook의 안정성이 중요하다.

SyncFail Hook도 있다. sync가 실패했을 때 알림을 보내거나 롤백 작업을 실행할 때 쓴다.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: SyncFail
```

## Helm과 Kustomize 연동

ArgoCD는 Helm chart와 Kustomize를 기본으로 지원한다. 별도 플러그인 설치 없이 `source`에 설정만 넣으면 된다.

### Helm

```yaml
spec:
  source:
    repoURL: https://charts.company.internal
    chart: payment-api
    targetRevision: 1.2.3
    helm:
      releaseName: payment-api
      values: |
        replicaCount: 3
        image:
          tag: "20240715-abc1234"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      valueFiles:
        - values-production.yaml
      parameters:
        - name: image.tag
          value: "20240715-abc1234"
```

`values`와 `valueFiles`를 같이 쓸 때 우선순위는 `parameters` > `values` > `valueFiles` 순이다. CI에서 이미지 태그를 `parameters`로 주입하면 values 파일을 수정하지 않아도 된다.

외부 Helm 저장소를 쓸 때는 ArgoCD의 `repositories` 설정에 미리 추가해야 한다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: company-helm-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  url: https://charts.company.internal
  username: robot-account
  password: token-value
```

### Kustomize

Kustomize는 overlays 구조로 환경별 설정을 분리할 때 쓴다.

```
k8s/
  base/
    deployment.yaml
    service.yaml
    kustomization.yaml
  overlays/
    development/
      kustomization.yaml
      replica-patch.yaml
    production/
      kustomization.yaml
      replica-patch.yaml
      resource-patch.yaml
```

```yaml
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: company/payment-api
    newTag: "20240715-abc1234"
patchesStrategicMerge:
  - replica-patch.yaml
  - resource-patch.yaml
commonLabels:
  env: production
```

ArgoCD Application에서는 이 경로만 지정한다.

```yaml
spec:
  source:
    repoURL: https://github.com/company/payment-service
    targetRevision: main
    path: k8s/overlays/production
    kustomize:
      images:
        - company/payment-api:20240715-abc1234
```

`kustomize.images`로 이미지 태그를 덮어쓸 수 있다. kustomization.yaml에 태그를 직접 커밋하지 않아도 CI에서 ArgoCD Application을 수정하는 방식으로 배포 파이프라인을 구성할 수 있다.

## 멀티 클러스터 배포

여러 클러스터에 같은 서비스를 배포할 때 클러스터 등록부터 시작한다.

```bash
argocd cluster add production-cluster --name production
argocd cluster add staging-cluster --name staging
argocd cluster list
```

CLI를 쓰지 않고 Secret으로 직접 등록하는 방법도 있다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: production-cluster-secret
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: production
  server: https://prod-k8s.company.internal:6443
  config: |
    {
      "bearerToken": "eyJhbGciOi...",
      "tlsClientConfig": {
        "insecure": false,
        "caData": "LS0tLS1CRUdJTi..."
      }
    }
```

ApplicationSet을 쓰면 여러 클러스터에 Application을 자동으로 생성할 수 있다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: payment-api-multicluster
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            env: production
  template:
    metadata:
      name: '{{name}}-payment-api'
    spec:
      project: payment-team
      source:
        repoURL: https://github.com/company/payment-service
        targetRevision: main
        path: k8s/overlays/production
      destination:
        server: '{{server}}'
        namespace: payment
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

클러스터에 `env: production` 레이블이 붙어 있으면 ApplicationSet이 자동으로 각 클러스터에 Application을 만든다. 클러스터를 추가할 때마다 Application을 수동으로 만들 필요가 없어진다.

환경별로 다른 값을 써야 할 때는 Matrix generator를 쓴다.

```yaml
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  env: production
          - list:
              elements:
                - region: ap-northeast-2
                  replicaCount: "3"
                - region: us-east-1
                  replicaCount: "5"
  template:
    metadata:
      name: '{{name}}-{{region}}-payment-api'
    spec:
      source:
        helm:
          parameters:
            - name: replicaCount
              value: '{{replicaCount}}'
            - name: region
              value: '{{region}}'
```

## Sync Wave로 배포 순서 제어

여러 리소스를 배포할 때 순서가 중요한 경우가 있다. ConfigMap이 먼저 생성되어야 Deployment가 마운트할 수 있는 상황이 대표적이다.

Sync Wave는 `argocd.argoproj.io/sync-wave` 어노테이션으로 지정한다. 낮은 숫자가 먼저 배포된다. 기본값은 0이다.

```yaml
# 1단계: 네임스페이스 (-5)
apiVersion: v1
kind: Namespace
metadata:
  name: payment
  annotations:
    argocd.argoproj.io/sync-wave: "-5"
---
# 2단계: ConfigMap과 Secret (-3)
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-config
  annotations:
    argocd.argoproj.io/sync-wave: "-3"
---
# 3단계: Deployment (기본값 0)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
---
# 4단계: Service와 Ingress (1, 2)
apiVersion: v1
kind: Service
metadata:
  name: payment-api
  annotations:
    argocd.argoproj.io/sync-wave: "1"
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: payment-ingress
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

같은 wave 내에서는 순서가 보장되지 않는다. 의존 관계가 있는 리소스는 반드시 다른 wave에 둬야 한다.

Wave 간 전환 조건은 현재 wave의 모든 리소스가 Healthy 상태가 되는 것이다. Deployment의 경우 모든 Pod가 Ready 상태여야 다음 wave로 넘어간다. wave가 많을수록 전체 배포 시간이 늘어난다.

PreSync Hook은 모든 wave보다 먼저 실행된다. PostSync Hook은 모든 wave가 완료된 후 실행된다. Hook에도 sync-wave를 붙일 수 있어서 같은 타입의 Hook 간 순서도 제어된다.

## Drift 감지와 자동 복구

ArgoCD는 기본적으로 3분마다 클러스터 상태를 Git과 비교한다. 차이가 있으면 OutOfSync 상태로 표시된다.

`selfHeal: true`가 켜져 있으면 OutOfSync 감지 즉시 sync를 실행한다. 꺼져 있으면 사람이 수동으로 sync해야 한다.

자동 복구 없이 drift만 감지하고 알림을 받고 싶으면 `selfHeal`을 끄고 Notification을 설정한다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
  template.app-out-of-sync: |
    message: |
      Application {{.app.metadata.name}}이 OutOfSync 상태입니다.
      클러스터: {{.app.spec.destination.server}}
      변경 사항을 확인하고 sync 여부를 결정해 주세요.
  trigger.on-out-of-sync: |
    - when: app.status.sync.status == 'OutOfSync'
      send: [app-out-of-sync]
```

특정 리소스는 drift를 무시하고 싶을 때 `ignoreDifferences`를 쓴다. 외부 시스템이 자동으로 어노테이션을 추가하거나 HPA가 레플리카 수를 바꾸는 경우가 해당된다.

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: ""
      kind: Service
      jsonPointers:
        - /spec/clusterIP
        - /spec/clusterIPs
```

`clusterIP`와 `clusterIPs`는 Service가 생성될 때 자동으로 할당되므로 반드시 무시해야 한다. 빠뜨리면 ArgoCD가 Service를 계속 OutOfSync로 표시한다.

## RBAC 구성

ArgoCD RBAC는 Casbin 기반이다. 정책은 `argocd-rbac-cm` ConfigMap에 정의한다.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    # 읽기 전용 역할 (기본값)
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, clusters, get, *, allow
    p, role:readonly, repositories, get, *, allow

    # 개발자 역할: sync까지 가능
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, */*, allow
    p, role:developer, applications, action/*, */*, allow
    p, role:developer, logs, get, */*, allow

    # 팀 리더: 특정 프로젝트에서 모든 작업 가능
    p, role:team-lead, applications, *, payment-team/*, allow
    p, role:team-lead, repositories, *, *, allow

    # 플랫폼 팀 관리자
    p, role:admin, *, *, *, allow

    # SSO 그룹 매핑
    g, company-github-org:payment-dev, role:developer
    g, company-github-org:payment-lead, role:team-lead
    g, company-github-org:platform-team, role:admin
  scopes: '[groups, email]'
```

`policy.default: role:readonly`로 설정하면 명시적으로 권한을 부여받지 않은 사용자는 읽기만 된다. `role:''`로 설정하면 인증된 사용자에게 권한이 없어 아무것도 볼 수 없다.

RBAC 정책 검증은 CLI로 할 수 있다.

```bash
argocd admin settings rbac can user@company.com sync applications 'payment-team/payment-api' --policy-file policy.csv

argocd admin settings rbac validate --policy-file policy.csv
```

AppProject 레벨의 역할과 전역 RBAC를 함께 쓸 때 주의할 점이 있다. AppProject의 `roles`에 정의된 권한은 해당 프로젝트 내에서만 유효하다. 전역 RBAC에서 `role:admin`이어도 AppProject의 `destinations` 제한은 그대로 적용된다.

Dex를 통한 SSO 연동이 보편적이다. GitHub Organization이나 GitLab Group을 ArgoCD 역할에 매핑하면 팀 구성원 변경이 자동으로 반영된다.

```yaml
# argocd-cm ConfigMap
data:
  url: https://argocd.company.internal
  dex.config: |
    connectors:
      - type: github
        id: github
        name: GitHub
        config:
          clientID: $dex-github-client-id
          clientSecret: $dex-github-client-secret
          orgs:
            - name: company-github-org
              teams:
                - payment-dev
                - payment-lead
                - platform-team
```

GitHub 팀에서 구성원을 제거하면 ArgoCD 권한도 즉시 사라진다. 별도로 ArgoCD 설정을 수정할 필요가 없어서 팀 규모가 클수록 관리 부담이 줄어든다.
