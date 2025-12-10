---
title: GitOps 전략
tags: [devops, gitops, argocd, flux, declarative-deployment, continuous-deployment, kubernetes]
updated: 2025-12-10
---

# GitOps 전략

## 정의

GitOps는 Git을 단일 소스 오브 트루스(Single Source of Truth)로 사용하여 인프라와 애플리케이션 배포를 관리하는 운영 패러다임입니다.

### 핵심 원칙
- 선언적 구성: Git이 단일 소스
- 자동화: 자동 동기화 및 배포
- 관찰 가능성: 상태 모니터링 및 변경 추적

## 주요 도구

### ArgoCD

**설치:**
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

**애플리케이션 정의:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nodejs-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/example/nodejs-app
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

### Flux

**설치:**
```bash
# Flux CLI 설치
curl -s https://fluxcd.io/install.sh | sudo bash

# Flux 부트스트랩
flux bootstrap github \
  --owner=example \
  --repository=gitops-repo \
  --branch=main \
  --path=clusters/production \
  --personal
```

**Kustomization 정의:**
```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1beta2
kind: Kustomization
metadata:
  name: nodejs-app
  namespace: flux-system
spec:
  interval: 5m
  path: ./apps/nodejs-app
  prune: true
  sourceRef:
    kind: GitRepository
    name: gitops-repo
  validation: client
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: nodejs-deployment
      namespace: production
```

## 배포 전략

### 자동 동기화

**ArgoCD:**
```yaml
spec:
  syncPolicy:
    automated:
      prune: true      # 미사용 리소스 자동 삭제
      selfHeal: true   # 변경사항 자동 복구
```

**Flux:**
```yaml
spec:
  interval: 5m  # 5분마다 동기화
  prune: true
  wait: true
```

### 롤백

**ArgoCD:**
```bash
# 이전 버전으로 롤백
argocd app rollback nodejs-app <revision-hash>
```

**Flux:**
```bash
# Git에서 이전 커밋으로 롤백
git revert HEAD
git push origin main
```

## 모니터링

### ArgoCD 알림

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
  trigger.on-sync-succeeded: |
    - send:
      - slack
```

### Flux 알림

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta2
kind: Alert
metadata:
  name: nodejs-app-alert
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: info
  eventSources:
    - kind: Kustomization
      name: nodejs-app
```

## 참고

### ArgoCD vs Flux

| 항목 | ArgoCD | Flux |
|------|--------|------|
| UI | 웹 UI 제공 | CLI 중심 |
| 설정 | CRD 기반 | Git 기반 |
| 동기화 | Pull 기반 | Pull 기반 |
| 복잡도 | 중간 | 낮음 |
| 생태계 | 강력 | CNCF 프로젝트 |

### 모범 사례

1. 환경별 브랜치/디렉토리 분리
2. 자동 동기화 활성화
3. 헬스 체크 설정
4. 알림 시스템 구성
5. 롤백 테스트 수행

### 관련 문서
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Flux Documentation](https://fluxcd.io/docs/)
- [GitOps Principles](https://opengitops.dev/)
