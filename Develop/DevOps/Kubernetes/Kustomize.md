---
title: Kustomize
tags: [devops, kubernetes, kustomize, configuration-management, gitops]
updated: 2026-04-12
---

# Kustomize

## 1. Kustomize란

Kustomize는 Kubernetes 매니페스트를 **템플릿 없이** 환경별로 다르게 구성할 수 있는 도구다. kubectl 1.14부터 내장되어 별도 설치 없이 `kubectl apply -k` 명령으로 바로 사용할 수 있다.

핵심 원칙은 **base + overlay 구조**다. 공통 설정을 base에 두고, 환경별로 달라지는 부분만 overlay에서 덮어쓴다. 원본 YAML을 직접 수정하지 않기 때문에 base 파일은 항상 그대로 유지된다.

```
Kustomize 동작 원리:

base/                         overlay/dev/
┌──────────────┐             ┌──────────────────┐
│ deployment   │             │ replica: 1       │
│ replica: 3   │  ──patch──> │ image: app:dev   │
│ image: app   │             │ resources:       │
│ service      │             │   cpu: 100m      │
└──────────────┘             └──────────────────┘
                                     │
                                     v
                             ┌──────────────────┐
                             │ 최종 결과:         │
                             │ replica: 1       │
                             │ image: app:dev   │
                             │ cpu: 100m        │
                             │ + service 그대로   │
                             └──────────────────┘
```

## 2. 디렉토리 구조

실무에서 가장 많이 쓰는 구조는 이렇다.

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch-deployment.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch-deployment.yaml
│   └── prod/
│       ├── kustomization.yaml
│       ├── patch-deployment.yaml
│       └── patch-hpa.yaml
```

`base/`에는 모든 환경에서 공통으로 사용하는 리소스를 둔다. `overlays/`에는 환경별 차이점만 넣는다. 이렇게 나누면 dev에서 뭘 바꿔도 prod base에는 영향이 없다.

### 2.1 base 구성

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml

commonLabels:
  app: my-api
```

```yaml
# base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
    spec:
      containers:
        - name: my-api
          image: my-api:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

```yaml
# base/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-api
spec:
  selector:
    app: my-api
  ports:
    - port: 80
      targetPort: 8080
```

### 2.2 overlay 구성

```yaml
# overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namePrefix: dev-
namespace: dev

patches:
  - path: patch-deployment.yaml
```

```yaml
# overlays/dev/patch-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: my-api
          image: my-api:dev-latest
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namePrefix: prod-
namespace: production

patches:
  - path: patch-deployment.yaml

replicas:
  - name: my-api
    count: 5
```

`namePrefix`를 쓰면 모든 리소스 이름 앞에 접두사가 붙는다. `dev-my-api`, `prod-my-api` 식으로 리소스가 구분된다. `namespace`도 overlay에서 지정하면 base 리소스 전체에 해당 네임스페이스가 적용된다.

## 3. Patches

Kustomize에서 base를 변경하는 방법은 크게 두 가지다.

### 3.1 Strategic Merge Patch

기존 리소스와 같은 구조로 YAML을 작성하고, 바꾸고 싶은 필드만 명시한다. 나머지 필드는 base 값이 그대로 유지된다.

```yaml
# strategic merge patch - 환경변수 추가
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  template:
    spec:
      containers:
        - name: my-api
          env:
            - name: DB_HOST
              value: "dev-db.internal"
            - name: LOG_LEVEL
              value: "debug"
```

주의할 점이 하나 있다. 리스트 타입 필드는 merge 방식이 다르다. `containers`는 `name` 필드로 매칭되어 merge되지만, `env`는 기본적으로 전체가 교체된다. base에 env가 3개 있고 patch에 env를 2개만 쓰면 최종 결과는 2개만 남는다.

### 3.2 JSON 6902 Patch

특정 경로의 값을 정확히 지정해서 변경한다. 세밀한 제어가 필요할 때 쓴다.

```yaml
# overlays/prod/kustomization.yaml
patches:
  - target:
      kind: Deployment
      name: my-api
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 5
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: ENVIRONMENT
          value: production
      - op: remove
        path: /spec/template/spec/containers/0/resources/limits
```

JSON 6902 patch는 `op`으로 `add`, `remove`, `replace`, `move`, `copy`를 지정할 수 있다. 리스트의 특정 인덱스를 정확히 지정해야 해서, base 구조가 바뀌면 patch가 깨지는 경우가 있다. Strategic merge patch로 해결 안 되는 경우에만 쓰는 게 낫다.

### 3.3 inline patch

파일을 따로 만들지 않고 kustomization.yaml 안에 직접 작성할 수도 있다.

```yaml
# kustomization.yaml
patches:
  - target:
      kind: Deployment
      name: my-api
    patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: my-api
      spec:
        replicas: 3
```

파일이 하나 줄어서 편하지만, patch가 길어지면 kustomization.yaml이 비대해진다. 2~3줄짜리 간단한 변경에만 쓴다.

## 4. Generators

매번 ConfigMap이나 Secret YAML을 직접 작성하는 대신, Kustomize가 자동으로 생성해주는 기능이다.

### 4.1 ConfigMapGenerator

```yaml
# kustomization.yaml
configMapGenerator:
  # 리터럴 값으로 생성
  - name: app-config
    literals:
      - DB_HOST=localhost
      - DB_PORT=5432
      - CACHE_TTL=300

  # 파일로 생성
  - name: nginx-config
    files:
      - nginx.conf
      - mime.types

  # env 파일로 생성
  - name: env-config
    envs:
      - config.env
```

Generator로 만든 ConfigMap은 이름 뒤에 해시 suffix가 붙는다. `app-config-h2b8k5` 같은 식이다. ConfigMap 내용이 바뀌면 해시도 바뀌고, Deployment가 참조하는 ConfigMap 이름도 자동으로 업데이트된다. 결과적으로 ConfigMap이 바뀌면 Pod가 재시작된다.

이게 중요한 이유가 있다. 일반적으로 ConfigMap을 수정해도 이미 실행 중인 Pod에는 반영되지 않는다. 수동으로 rollout restart를 해야 하는데, Kustomize generator를 쓰면 ConfigMap 변경 시 자동으로 새 Pod가 뜬다.

해시 suffix가 싫으면 끌 수 있다.

```yaml
generatorOptions:
  disableNameSuffixHash: true
```

다만 이렇게 하면 ConfigMap 변경 시 자동 rollout이 안 된다.

### 4.2 SecretGenerator

```yaml
secretGenerator:
  - name: db-credentials
    literals:
      - username=admin
      - password=s3cret123
    type: Opaque

  - name: tls-secret
    files:
      - tls.crt
      - tls.key
    type: kubernetes.io/tls
```

Secret도 ConfigMap과 동일하게 해시 suffix가 붙는다. 다만 secret 값을 kustomization.yaml에 평문으로 넣는 건 Git에 올리기 곤란하다. 실무에서는 SealedSecret이나 External Secrets Operator와 조합해서 쓰거나, CI/CD 파이프라인에서 주입하는 방식을 쓴다.

## 5. Helm과의 차이

Helm과 Kustomize는 "환경별 설정을 다르게 한다"는 목적은 같지만, 접근 방식이 다르다.

```
Helm:
  template + values → 렌더링 → 최종 YAML
  
  deployment.yaml:
    replicas: {{ .Values.replicas }}     # Go 템플릿
    image: {{ .Values.image.tag }}
  
  values-prod.yaml:
    replicas: 5
    image:
      tag: v1.2.3

Kustomize:
  base YAML + patch → merge → 최종 YAML

  base/deployment.yaml:
    replicas: 2                          # 순수 YAML
    image: my-api:latest
  
  overlays/prod/patch.yaml:
    replicas: 5
    image: my-api:v1.2.3
```

**Helm이 나은 경우:**

- 외부 차트 의존성 관리가 필요할 때 (nginx-ingress, cert-manager 같은 공개 차트)
- 조건 분기가 많을 때 (`if`, `range` 같은 로직이 필요한 경우)
- 패키지로 배포해야 할 때 (차트 레지스트리에 올려서 여러 팀이 공유)

**Kustomize가 나은 경우:**

- 자체 서비스 배포에서 환경별 설정만 다를 때
- YAML을 그대로 유지하고 싶을 때 (kubectl apply로 바로 확인 가능)
- 별도 도구 설치 없이 kubectl만으로 처리하고 싶을 때
- Helm 차트의 values로 커버 안 되는 부분을 추가 커스터마이징할 때

실무에서는 둘을 같이 쓰는 경우가 많다. 외부 차트는 Helm으로 설치하고, 자체 서비스는 Kustomize로 관리하는 조합이다. Helm으로 렌더링한 결과물 위에 Kustomize patch를 덧씌우는 것도 가능하다.

```yaml
# Helm 차트 위에 Kustomize 적용
# kustomization.yaml
helmCharts:
  - name: ingress-nginx
    repo: https://kubernetes.github.io/ingress-nginx
    version: 4.7.1
    releaseName: ingress
    namespace: ingress-nginx
    valuesFile: values.yaml

patches:
  - target:
      kind: Deployment
      name: ingress-ingress-nginx-controller
    patch: |-
      - op: add
        path: /spec/template/spec/containers/0/args/-
        value: --default-ssl-certificate=ingress-nginx/default-tls
```

## 6. 자주 쓰는 기능

### 6.1 commonLabels / commonAnnotations

```yaml
# kustomization.yaml
commonLabels:
  team: backend
  env: production

commonAnnotations:
  managed-by: kustomize
```

모든 리소스에 label과 annotation을 일괄 추가한다. `commonLabels`는 selector에도 자동으로 들어가기 때문에, 이미 배포된 리소스에 나중에 추가하면 selector mismatch로 에러가 난다. 처음부터 넣거나, 아예 `labels` transformer를 쓰는 게 안전하다.

```yaml
# labels transformer (selector에 영향 안 줌)
labels:
  - pairs:
      team: backend
    includeSelectors: false
```

### 6.2 images

이미지 태그를 overlay에서 변경할 때 patch 파일을 만들 필요 없이 간단하게 처리할 수 있다.

```yaml
# kustomization.yaml
images:
  - name: my-api
    newName: registry.example.com/my-api
    newTag: v1.2.3

  # digest로 고정하는 것도 가능
  - name: my-api
    newName: registry.example.com/my-api
    digest: sha256:abc123...
```

CI/CD에서 빌드 후 이미지 태그를 변경할 때 유용하다. `kustomize edit set image my-api=registry.example.com/my-api:v1.2.3` 명령으로 자동화할 수 있다.

### 6.3 vars (deprecated) → replacements

Kustomize v5부터 `vars`는 deprecated되었다. 대신 `replacements`를 쓴다.

```yaml
# kustomization.yaml
replacements:
  - source:
      kind: Service
      name: my-api
      fieldPath: metadata.name
    targets:
      - select:
          kind: Deployment
          name: my-api
        fieldPaths:
          - spec.template.spec.containers.0.env.[name=SERVICE_NAME].value
```

Service 이름을 Deployment의 환경변수로 주입하는 예제다. 리소스 간 값을 참조해야 할 때 쓰지만, 복잡해지면 가독성이 떨어진다. 꼭 필요한 경우가 아니면 직접 값을 넣는 게 읽기 편하다.

## 7. kubectl apply -k 워크플로우

### 7.1 기본 명령어

```bash
# 변경 사항 미리 확인 (dry-run)
kubectl apply -k overlays/dev --dry-run=client -o yaml

# 실제 적용
kubectl apply -k overlays/dev

# kustomize로 빌드만 (적용 안 함)
kubectl kustomize overlays/dev

# 빌드 결과를 파일로 저장
kubectl kustomize overlays/prod > rendered-prod.yaml

# diff 확인 (현재 클러스터 상태와 비교)
kubectl diff -k overlays/dev
```

`kubectl kustomize`로 먼저 빌드 결과를 확인하고, 문제가 없으면 `kubectl apply -k`로 적용하는 순서를 따르는 게 안전하다.

### 7.2 CI/CD 파이프라인에서

```yaml
# GitHub Actions 예시
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set image tag
        run: |
          cd k8s/overlays/prod
          kustomize edit set image my-api=registry.example.com/my-api:${{ github.sha }}

      - name: Validate
        run: |
          kubectl kustomize k8s/overlays/prod | kubeval --strict

      - name: Deploy
        run: |
          kubectl apply -k k8s/overlays/prod
          kubectl rollout status deployment/prod-my-api -n production --timeout=300s
```

`kustomize edit set image` 명령으로 커밋 해시를 이미지 태그로 설정하면, 어떤 커밋이 어떤 배포에 해당하는지 추적할 수 있다.

### 7.3 ArgoCD와 함께 쓰는 경우

ArgoCD는 Kustomize를 네이티브로 지원한다. Git 레포에 Kustomize 구조를 푸시하면 ArgoCD가 자동으로 감지하고 배포한다.

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-api-prod
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

ArgoCD Application의 `path`에 overlay 경로만 지정하면 된다. kustomization.yaml을 인식해서 자동으로 빌드하고 적용한다.

## 8. 실무에서 주의할 점

**namespace 충돌 문제**

overlay에서 `namespace`를 지정하면 모든 리소스에 적용되는데, ClusterRole이나 ClusterRoleBinding 같은 클러스터 스코프 리소스에도 namespace가 들어가면 에러가 난다. 이런 리소스는 별도로 분리하거나 patch로 제외해야 한다.

```yaml
# 클러스터 스코프 리소스는 namespace 적용 제외
namespace: production

# kustomization.yaml에서 특정 리소스를 namespace 적용에서 제외하는 방법은
# 공식적으로 지원되지 않는다. 클러스터 스코프 리소스는 별도 kustomization으로 분리한다.
```

**kustomize 버전 차이**

kubectl 내장 kustomize와 standalone kustomize의 버전이 다를 수 있다. kubectl v1.27에 내장된 kustomize는 v5.0.1인데, standalone으로 설치하면 최신 버전을 쓸 수 있다. `helmCharts` 같은 기능은 standalone에서만 동작하는 경우가 있으니 확인해야 한다.

```bash
# kubectl 내장 버전 확인
kubectl version --client -o json | jq '.kustomizeVersion'

# standalone 설치
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
```

**base 변경 시 모든 overlay 확인**

base를 수정하면 모든 overlay에 영향이 간다. base에서 container 이름을 바꾸면 patch에서 매칭이 안 되고, 필드를 제거하면 patch의 replace가 실패한다. base를 변경할 때는 모든 overlay를 빌드해서 확인하는 스크립트를 돌리는 게 좋다.

```bash
#!/bin/bash
# 모든 overlay 빌드 확인
for overlay in k8s/overlays/*/; do
  echo "Building $overlay..."
  if ! kubectl kustomize "$overlay" > /dev/null 2>&1; then
    echo "FAIL: $overlay"
    kubectl kustomize "$overlay"
    exit 1
  fi
  echo "OK: $overlay"
done
echo "All overlays build successfully"
```

**리소스 정리**

`kubectl apply -k`는 기본적으로 리소스를 추가/수정만 하고, base에서 리소스를 삭제해도 클러스터에서 자동으로 삭제되지 않는다. `--prune` 옵션을 쓰면 되지만, 잘못 쓰면 의도치 않은 리소스가 삭제될 수 있다. ArgoCD의 prune 기능이 이 부분을 더 안전하게 처리한다.
