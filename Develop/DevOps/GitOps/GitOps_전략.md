---
title: GitOps 전략 가이드
tags: [devops, gitops, argocd, flux, declarative-deployment, continuous-deployment, kubernetes, helm]
updated: 2026-03-01
---

# GitOps 전략

## 개요

GitOps는 **Git을 단일 진실 소스(Single Source of Truth)로 사용**하여 인프라와 애플리케이션 배포를 관리하는 운영 패러다임이다. 선언적 구성 파일을 Git에 저장하고, 자동화된 도구가 실제 환경을 Git 상태와 일치시킨다.

```
전통적 배포 (Push 기반):
  개발자 → CI 빌드 → kubectl apply → 클러스터
  (외부에서 클러스터로 밀어넣음)

GitOps (Pull 기반):
  개발자 → Git Push → GitOps Agent가 감지 → 클러스터에 적용
  (클러스터 내부에서 Git 상태를 끌어와 동기화)
```

### GitOps 4대 원칙 (OpenGitOps)

| 원칙 | 설명 |
|------|------|
| **선언적 (Declarative)** | 시스템의 원하는 상태를 선언적으로 정의 |
| **버전 관리 (Versioned)** | 원하는 상태를 Git에 불변으로 저장 |
| **자동 적용 (Automated)** | 승인된 변경은 자동으로 시스템에 적용 |
| **자동 복구 (Self-healing)** | 실제 상태가 선언과 다르면 자동 교정 |

### CI/CD와 GitOps의 차이

```
CI/CD (Push):
  Code → Build → Test → Deploy(push) → Cluster
  ✅ 빌드/테스트 자동화
  ❌ 클러스터 외부에서 배포 (보안 위험: kubectl 권한 필요)

GitOps (Pull):
  Code → Build → Test → Git Push(매니페스트) → Agent(pull) → Cluster
  ✅ 빌드/테스트 자동화
  ✅ 클러스터 내부에서 배포 (보안: 최소 권한)
  ✅ 감사 로그 = Git 히스토리
```

## 핵심

### 1. 레포지토리 전략

#### 앱 레포 vs 설정 레포 분리 (권장)

```
앱 레포 (source code):
  app-service/
  ├── src/
  ├── Dockerfile
  ├── pom.xml
  └── .github/workflows/ci.yaml   ← CI: 빌드 + 이미지 푸시

설정 레포 (GitOps manifests):
  gitops-config/
  ├── apps/
  │   ├── app-service/
  │   │   ├── base/                ← Kustomize base
  │   │   │   ├── deployment.yaml
  │   │   │   ├── service.yaml
  │   │   │   └── kustomization.yaml
  │   │   └── overlays/
  │   │       ├── dev/
  │   │       │   └── kustomization.yaml
  │   │       ├── staging/
  │   │       │   └── kustomization.yaml
  │   │       └── prod/
  │   │           └── kustomization.yaml
  │   └── another-service/
  └── infra/
      ├── cert-manager/
      ├── ingress-nginx/
      └── monitoring/
```

| 전략 | 장점 | 단점 |
|------|------|------|
| **분리 (권장)** | 관심사 분리, 권한 분리, 명확한 이력 | 레포 2개 관리 |
| **통합** | 간단, 한 곳에서 관리 | CI/CD 커밋과 배포 커밋 혼재 |

#### 환경별 디렉토리 구조 (Kustomize)

```yaml
# base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app-service
  template:
    metadata:
      labels:
        app: app-service
    spec:
      containers:
        - name: app
          image: registry.example.com/app-service:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi

# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: production
resources:
  - ../../base
patches:
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: app-service
      spec:
        replicas: 3           # 프로덕션은 3개
    target:
      kind: Deployment
images:
  - name: registry.example.com/app-service
    newTag: v1.2.3            # 고정 태그
```

### 2. ArgoCD

Kubernetes 네이티브 GitOps 도구. **웹 UI**와 CLI를 제공한다.

#### 설치 및 초기 설정

```bash
# ArgoCD 설치
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# CLI 설치 (macOS)
brew install argocd

# 초기 비밀번호 확인
argocd admin initial-password -n argocd

# 로그인
argocd login argocd.example.com
```

#### Application 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app-service-prod
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/org/gitops-config
    targetRevision: main
    path: apps/app-service/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true          # Git에서 삭제된 리소스 제거
      selfHeal: true       # 수동 변경 자동 복구
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

#### ApplicationSet (다중 환경 자동 생성)

```yaml
# 하나의 정의로 dev/staging/prod Application 자동 생성
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: app-service
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            cluster: https://dev-cluster.example.com
            revision: develop
          - env: staging
            cluster: https://staging-cluster.example.com
            revision: main
          - env: prod
            cluster: https://prod-cluster.example.com
            revision: main
  template:
    metadata:
      name: 'app-service-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/gitops-config
        targetRevision: '{{revision}}'
        path: 'apps/app-service/overlays/{{env}}'
      destination:
        server: '{{cluster}}'
        namespace: '{{env}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

#### Sync Wave (배포 순서 제어)

```yaml
# 0단계: ConfigMap/Secret 먼저
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  annotations:
    argocd.argoproj.io/sync-wave: "0"

# 1단계: DB 마이그레이션 Job
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    argocd.argoproj.io/sync-wave: "1"
    argocd.argoproj.io/hook: PreSync

# 2단계: 애플리케이션 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-service
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

### 3. Flux CD

CNCF Graduated 프로젝트. **Git 네이티브**하고 CLI 중심.

#### 부트스트랩

```bash
# Flux CLI 설치
curl -s https://fluxcd.io/install.sh | sudo bash

# GitHub 레포에 Flux 부트스트랩
flux bootstrap github \
  --owner=org \
  --repository=gitops-config \
  --branch=main \
  --path=clusters/production \
  --personal

# 부트스트랩 결과: Flux 컨트롤러가 클러스터에 설치되고
# gitops-config 레포의 clusters/production/ 경로를 감시
```

#### Flux 리소스 정의

```yaml
# GitRepository: Git 소스 정의
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: gitops-config
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/org/gitops-config
  ref:
    branch: main
  secretRef:
    name: git-credentials

# Kustomization: 배포 대상 정의
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app-service
  namespace: flux-system
spec:
  interval: 5m
  path: ./apps/app-service/overlays/prod
  prune: true
  sourceRef:
    kind: GitRepository
    name: gitops-config
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: app-service
      namespace: production
  timeout: 3m
```

#### 이미지 자동 업데이트

```yaml
# ImageRepository: 레지스트리 감시
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: app-service
  namespace: flux-system
spec:
  image: registry.example.com/app-service
  interval: 5m

# ImagePolicy: 태그 필터링
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: app-service
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: app-service
  policy:
    semver:
      range: '>=1.0.0'    # 시맨틱 버전 1.0.0 이상

# ImageUpdateAutomation: 자동 커밋
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: app-service
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: gitops-config
  git:
    commit:
      author:
        name: flux-bot
        email: flux@example.com
      messageTemplate: 'chore: update {{.AutomationObject}} images'
    push:
      branch: main
  update:
    path: ./apps/app-service
    strategy: Setters
```

### 4. ArgoCD vs Flux 비교

| 항목 | ArgoCD | Flux CD |
|------|--------|---------|
| **프로젝트** | Argo Project (CNCF) | Flux (CNCF Graduated) |
| **UI** | ✅ 웹 대시보드 | ❌ CLI/API만 |
| **멀티 클러스터** | 중앙 집중 관리 | 각 클러스터에 설치 |
| **Helm 지원** | ✅ (네이티브) | ✅ (HelmRelease CRD) |
| **Kustomize** | ✅ | ✅ |
| **이미지 자동 업데이트** | Argo Image Updater | ✅ (내장) |
| **알림** | Argo Notifications | ✅ (내장) |
| **학습 곡선** | 중간 (UI 있어서 쉬움) | 중간 (CLI 중심) |
| **적합한 경우** | 팀 규모 크고 UI 필요 | 순수 GitOps, 자동화 중심 |

### 5. 시크릿 관리

Git에 시크릿을 평문으로 저장하면 안 된다.

| 솔루션 | 동작 | 장점 | 단점 |
|--------|------|------|------|
| **Sealed Secrets** | 공개키로 암호화 → Git 저장 → 클러스터에서 복호화 | 간단 | 키 관리 필요 |
| **External Secrets** | 외부 저장소(AWS SM, Vault)에서 실시간 동기화 | 중앙 관리 | 외부 의존 |
| **SOPS** | 파일 내 값만 암호화 | Git diff 가능 | 키 관리 |

```yaml
# Sealed Secrets
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  encryptedData:
    password: AgBy3i4OJSWK+PiTySYZZA9rO...  # 암호화됨
    username: AgBu7s2OKJK+PiTySYZZA9rO...

# External Secrets (AWS Secrets Manager 연동)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
  data:
    - secretKey: password
      remoteRef:
        key: prod/db-credentials
        property: password
```

### 6. 프로모션 전략

환경 간 배포 승격(dev → staging → prod) 패턴.

```
방법 1: 브랜치 기반
  develop 브랜치 → dev 환경
  main 브랜치 → staging/prod 환경
  PR 머지로 승격

방법 2: 디렉토리 기반 (권장)
  overlays/dev/kustomization.yaml     ← 이미지 태그: v1.2.3
  overlays/staging/kustomization.yaml ← 이미지 태그: v1.2.2
  overlays/prod/kustomization.yaml    ← 이미지 태그: v1.2.1
  → dev에서 검증 후 staging/prod 태그를 업데이트하는 PR 생성

방법 3: 자동화된 프로모션
  CI가 dev 배포 성공 → 자동으로 staging PR 생성
  staging 테스트 통과 → 자동으로 prod PR 생성
```

### 7. CI/CD 통합 워크플로

```yaml
# GitHub Actions: 빌드 → 이미지 푸시 → GitOps 설정 업데이트
name: CI/CD
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build & Push Image
        run: |
          docker build -t $REGISTRY/app:${{ github.sha }} .
          docker push $REGISTRY/app:${{ github.sha }}

      - name: Update GitOps Config
        run: |
          git clone https://github.com/org/gitops-config.git
          cd gitops-config
          # Kustomize 이미지 태그 업데이트
          cd apps/app-service/overlays/dev
          kustomize edit set image $REGISTRY/app=$REGISTRY/app:${{ github.sha }}
          git add .
          git commit -m "chore: update app-service to ${{ github.sha }}"
          git push
```

```
전체 흐름:
  1. 개발자가 앱 레포에 코드 Push
  2. CI가 빌드 → 테스트 → 이미지 Push
  3. CI가 설정 레포의 이미지 태그를 업데이트
  4. ArgoCD/Flux가 설정 레포 변경 감지
  5. 클러스터에 자동 배포
  6. 헬스 체크 → 성공/실패 알림
```

### 8. 모니터링 & 알림

```yaml
# ArgoCD Notifications (Slack)
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
  trigger.on-sync-succeeded: |
    - description: Application synced successfully
      send: [slack-message]
      when: app.status.operationState.phase in ['Succeeded']
  trigger.on-sync-failed: |
    - description: Application sync failed
      send: [slack-message]
      when: app.status.operationState.phase in ['Error', 'Failed']
  template.slack-message: |
    message: |
      {{if eq .app.status.operationState.phase "Succeeded"}}✅{{else}}❌{{end}}
      *{{.app.metadata.name}}*: {{.app.status.operationState.phase}}
      Revision: {{.app.status.sync.revision}}

# Flux Notification (Slack)
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: deployments
  secretRef:
    name: slack-webhook

apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: deployment-alerts
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: info
  eventSources:
    - kind: Kustomization
      name: '*'
```

### 9. 롤백

```bash
# ArgoCD 롤백
argocd app history app-service-prod        # 배포 이력 확인
argocd app rollback app-service-prod 5     # 5번 리비전으로 롤백

# Git 롤백 (모든 GitOps 도구 공통)
git revert HEAD          # 마지막 커밋 되돌리기
git push origin main     # GitOps Agent가 감지 → 자동 롤백

# Flux 일시 중지/재개
flux suspend kustomization app-service    # 동기화 중지
flux resume kustomization app-service     # 동기화 재개
```

## 운영 팁

### 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| 앱/설정 레포 분리 | 관심사 분리, 권한 분리 | ✅ |
| 자동 동기화 활성화 | `selfHeal: true`, `prune: true` | ✅ |
| 시크릿 암호화 | Sealed Secrets 또는 External Secrets | ✅ |
| 헬스 체크 설정 | 배포 성공/실패 자동 감지 | ✅ |
| 알림 설정 | Slack/Teams 배포 알림 | ✅ |
| 환경별 디렉토리 분리 | Kustomize overlays | ✅ |
| RBAC 설정 | ArgoCD 프로젝트별 권한 | ⭐ |
| 정기 드리프트 확인 | 수동 변경 감지 | ⭐ |

## 참고

- [OpenGitOps Principles](https://opengitops.dev/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Flux CD Documentation](https://fluxcd.io/docs/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [Kubernetes](../Kubernetes/Kubernetes.md) — K8s 기초
- [GitHub Actions](../CI_CD/GitHub_Actions.md) — CI 파이프라인
- [Terraform](../Infrastructure_as_Code/Terraform_기초.md) — 인프라 IaC
