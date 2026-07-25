---
title: CI/CD 파이프라인 인프라 설계
tags:
  - infra
  - cicd
  - pipeline
  - deployment
  - kubernetes
updated: 2026-07-25
---

# CI/CD 파이프라인 인프라 설계

## 파이프라인을 설계할 때 실제로 마주치는 문제

처음 파이프라인을 구성할 때는 "빌드 → 테스트 → 배포" 세 단계면 된다고 생각하기 쉽다. 그런데 서비스가 커지면서 진짜 문제들이 생긴다. 빌드가 20분을 넘어가면서 PR마다 기다리는 시간이 쌓이고, 테스트 1000개가 순차로 돌면서 CI가 병목이 되고, 프로덕션 배포하다가 롤백해야 하는 상황에서 정확히 어떤 트리거로 롤백할지 기준이 없어서 수동으로 개입하게 된다.

이 문서는 그런 문제들을 각각 어떻게 풀어왔는지 정리한 것이다.

## 빌드 캐시

### Docker Layer 캐시

Docker 빌드에서 캐시 히트율이 낮으면 매번 전체 이미지를 새로 빌드한다. 핵심은 레이어 순서다. 변경 빈도가 낮은 레이어를 앞쪽에, 높은 레이어를 뒤쪽에 놓아야 한다.

```dockerfile
FROM node:20-alpine AS base

# 패키지 설치는 package.json이 바뀔 때만 다시 실행
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# 소스 코드는 가장 마지막에 복사
COPY . .
RUN npm run build
```

`COPY . .`를 `RUN npm ci` 앞에 두는 실수가 흔하다. 소스 코드 한 줄만 바뀌어도 `npm ci`부터 다시 실행된다. 순서를 바꾸는 것만으로 빌드 시간이 절반으로 줄어드는 경우가 있다.

CI 환경에서 레이어 캐시를 재사용하려면 캐시를 외부에 저장해야 한다. GitHub Actions 기준으로는 `cache-from`과 `cache-to`를 활용한다.

```yaml
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ${{ env.IMAGE_TAG }}
    cache-from: type=registry,ref=${{ env.REGISTRY }}/myapp:cache
    cache-to: type=registry,ref=${{ env.REGISTRY }}/myapp:cache,mode=max
```

`mode=max`는 중간 레이어까지 모두 캐시에 저장한다. 저장 공간을 더 쓰지만 캐시 히트율이 높아진다. 레지스트리에 캐시 레이어가 쌓이므로 주기적으로 정리하지 않으면 스토리지 비용이 올라간다.

### Dependency 캐시

빌드 도구별로 의존성 캐시 경로가 다르다. 캐시 키는 lock 파일의 해시값으로 잡는다. `package.json`이 아니라 `package-lock.json`이나 `yarn.lock`으로 잡아야 실제 설치 버전이 바뀔 때만 캐시가 무효화된다.

```yaml
- name: Cache node modules
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

`restore-keys`에 prefix를 넣으면 정확한 캐시가 없을 때 가장 최근의 부분 캐시라도 복원한다. 완전히 새로 설치하는 것보다 부분 캐시에서 업데이트하는 게 빠른 경우가 많다.

Go 프로젝트는 `GOPATH/pkg/mod`를, Gradle은 `~/.gradle/caches`를 캐시 경로로 잡는다. 언어별로 캐시 위치가 다르니 각 툴의 문서를 확인해야 한다.

## 테스트 병렬화

### 파티셔닝 방식

테스트가 많아지면 단순히 여러 runner를 띄우는 것만으로는 부족하다. 각 runner가 돌리는 테스트 수가 균등하지 않으면 느린 runner 하나가 전체를 기다리게 만든다.

GitHub Actions의 `matrix` 전략으로 간단하게 파티셔닝할 수 있다.

```yaml
jobs:
  test:
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - name: Run tests
        run: |
          npx jest --shard=${{ matrix.shard }}/4
```

Jest는 `--shard` 옵션으로 테스트를 분할한다. `1/4`는 전체 테스트 파일의 1/4를 의미한다. 파일 수 기준으로 나누기 때문에 특정 파일에 느린 테스트가 몰려 있으면 여전히 불균형이 생긴다.

더 세밀하게 제어하려면 테스트 실행 시간을 기록해두고 그 시간 기준으로 그룹을 나눠야 한다. pytest-split, jest-circus의 실행 시간 리포트를 CI 아티팩트로 저장해두고 다음 실행 때 활용하는 방식이다.

### 테스트 격리

병렬로 돌리면 공유 상태 때문에 테스트가 서로 간섭하는 문제가 생긴다. DB를 공유하는 경우가 대표적인데, 한 테스트가 데이터를 넣고 지우기 전에 다른 테스트가 읽으면 결과가 달라진다.

각 runner마다 독립된 DB 인스턴스를 띄우는 게 깔끔하다. GitHub Actions에서는 서비스 컨테이너로 해결한다.

```yaml
jobs:
  test:
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb_${{ matrix.shard }}
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
```

DB 이름에 shard 번호를 넣으면 각 runner가 격리된 DB를 쓴다. 테스트가 끝나면 컨테이너와 함께 사라지므로 정리할 필요도 없다.

## 배포 방식

### Blue-Green 배포

두 개의 동일한 환경(blue, green)을 유지하고, 트래픽을 한 번에 전환하는 방식이다. 롤백이 빠르다는 게 가장 큰 장점이다. 전환 전 환경이 그대로 살아있으므로 문제가 생기면 트래픽을 다시 바꾸면 된다.

Kubernetes에서는 Service의 selector를 바꾸는 방식으로 구현한다.

```yaml
# Blue Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: myapp
        image: myapp:v1.2.0
---
# Service (평상시 blue를 바라봄)
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # green 배포 완료 후 이 값을 green으로 바꿈
  ports:
  - port: 80
    targetPort: 8080
```

배포 절차는 이렇다. green Deployment를 새 버전으로 배포하고, 모든 파드가 Ready 상태가 되면 Service의 selector를 `green`으로 변경한다. 문제가 없으면 blue를 정리한다.

Argo Rollouts나 Flagger를 쓰면 이 과정을 선언적으로 정의하고 자동화할 수 있다. 직접 kubectl로 selector 바꾸는 스크립트 작성하다 보면 엣지 케이스가 생각보다 많다.

### Canary 배포

전체 트래픽의 일부만 새 버전으로 보내고, 문제가 없으면 점진적으로 비율을 높이는 방식이다. Blue-green처럼 전체를 한 번에 전환하지 않아서 영향 범위를 제한할 수 있다.

Argo Rollouts로 구성한 예시다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 10      # 전체 트래픽의 10%를 새 버전으로
      - pause: {duration: 5m}
      - setWeight: 30
      - pause: {duration: 5m}
      - analysis:
          templates:
          - templateName: error-rate-check
      - setWeight: 100
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v1.3.0
```

`analysis` 단계에서 에러율이나 레이턴시를 체크하고, 기준을 넘으면 자동으로 이전 버전으로 되돌린다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate-check
spec:
  metrics:
  - name: error-rate
    interval: 1m
    successCondition: result[0] < 0.05   # 에러율 5% 미만
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{status=~"5.."}[2m]))
          /
          sum(rate(http_requests_total[2m]))
```

Prometheus 쿼리로 에러율을 계산하고, 5%를 넘으면 실패로 판단한다. 3번 연속 실패하면 Rollout이 자동으로 abort된다.

## 롤백 트리거와 자동화

### 트리거 조건 정의

롤백을 수동으로 하면 판단하는 사람마다 기준이 달라진다. "에러가 좀 나는데 더 기다려야 하나"를 놓고 슬랙에서 논의하다가 시간을 허비하는 상황이 생긴다. 롤백 트리거는 코드로 명시해야 한다.

일반적으로 쓰는 기준은 세 가지다.

**에러율**: 배포 전 대비 HTTP 5xx 비율이 2배 이상이면 롤백.
**레이턴시**: p99 레이턴시가 임계값(보통 배포 전 기준 1.5배 또는 절대값)을 넘으면 롤백.
**헬스체크 실패**: 파드의 readiness probe가 일정 시간 이상 실패하면 롤백.

Kubernetes에서 Deployment 기본 동작만 써도 readiness probe 기반의 자동 롤백은 가능하다. 새 파드가 Ready 상태가 안 되면 RollingUpdate가 진행을 멈추고 이전 파드를 유지한다.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0     # 배포 중 사용 불가 파드 0개 유지
      maxSurge: 1           # 동시에 최대 1개 추가 파드 허용
  template:
    spec:
      containers:
      - name: myapp
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 3
```

`maxUnavailable: 0`으로 설정하면 새 파드가 Ready가 될 때까지 이전 파드를 내리지 않는다. 새 파드가 계속 실패하면 배포가 멈추고 이전 상태를 유지한다.

### 자동 롤백 스크립트

배포 후 일정 시간 동안 메트릭을 모니터링하고 자동으로 롤백하는 스크립트를 파이프라인에 넣는 경우도 있다.

```bash
#!/bin/bash
DEPLOYMENT=$1
NAMESPACE=$2
MONITOR_DURATION=300  # 5분
INTERVAL=30

kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=5m

for i in $(seq 1 $(($MONITOR_DURATION / $INTERVAL))); do
  ERROR_RATE=$(kubectl exec -n monitoring deploy/prometheus -- \
    promtool query instant \
    'sum(rate(http_requests_total{status=~"5.."}[2m])) / sum(rate(http_requests_total[2m]))' \
    | awk '{print $2}')

  if (( $(echo "$ERROR_RATE > 0.05" | bc -l) )); then
    echo "Error rate exceeded threshold: $ERROR_RATE"
    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
    exit 1
  fi

  sleep $INTERVAL
done

echo "Deployment stable"
```

이 방식의 한계는 Prometheus 쿼리가 배포된 서비스 하나만 보지 않는다는 점이다. 다른 서비스의 에러와 뒤섞이면 오탐이 생긴다. 레이블 필터를 정확히 넣어야 한다.

## 환경별 파이프라인 분리

### 브랜치 전략과 환경 매핑

환경을 구분하지 않고 파이프라인을 하나로 쓰면 개발 중인 코드가 실수로 프로덕션에 배포되는 사고가 난다. 브랜치와 환경을 1:1로 매핑하는 게 기본이다.

```
feature/* → 빌드 + 테스트만
develop   → dev 환경 자동 배포
main      → staging 환경 자동 배포, prod는 수동 승인 후 배포
```

GitHub Actions에서 환경별로 분기하는 방식이다.

```yaml
jobs:
  deploy-dev:
    if: github.ref == 'refs/heads/develop'
    environment: dev
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to dev
        run: ./deploy.sh dev ${{ env.IMAGE_TAG }}

  deploy-staging:
    if: github.ref == 'refs/heads/main'
    environment: staging
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: ./deploy.sh staging ${{ env.IMAGE_TAG }}

  deploy-prod:
    if: github.ref == 'refs/heads/main'
    needs: deploy-staging
    environment:
      name: production
      url: https://myapp.example.com
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./deploy.sh prod ${{ env.IMAGE_TAG }}
```

`environment: production`을 지정하면 GitHub의 환경 보호 규칙이 적용된다. 특정 리뷰어 승인이 있어야만 다음 단계로 진행하도록 설정할 수 있다.

### 환경별 설정 관리

환경마다 다른 설정값(DB 주소, 리소스 제한, 레플리카 수 등)을 어떻게 관리할지도 정해야 한다.

Kustomize를 쓰면 base 설정을 공유하고 환경별 오버레이만 따로 관리한다.

```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml        # dev: replicas=1, resources 낮게
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml        # staging: replicas=2
│   └── prod/
│       ├── kustomization.yaml
│       └── patch.yaml        # prod: replicas=5, resources 높게
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
patches:
  - patch.yaml
images:
  - name: myapp
    newTag: v1.3.0
```

이미지 태그는 배포 시점에 `kustomize edit set image` 명령으로 업데이트한다. 이 방식을 쓰면 환경별 차이가 명시적으로 버전 관리된다.

## Secret 주입 방법

### 환경 변수 방식

가장 단순하다. CI 시스템의 시크릿 저장소(GitHub Secrets, GitLab CI Variables)에 넣고 환경 변수로 주입한다.

```yaml
# GitHub Actions
- name: Deploy
  env:
    DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
    API_KEY: ${{ secrets.API_KEY }}
  run: ./deploy.sh
```

Kubernetes에 배포할 때는 Secret 리소스로 만들어서 파드에 주입한다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
type: Opaque
stringData:
  db_password: "..."
---
spec:
  containers:
  - name: myapp
    env:
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: myapp-secrets
          key: db_password
```

환경 변수 방식의 문제는 시크릿 회전이 불편하다는 점이다. 값을 바꾸면 파드를 재시작해야 반영된다. 또 `kubectl describe pod`나 로그에서 환경 변수가 노출될 수 있다.

### Vault Agent 방식

Vault Agent를 사이드카로 파드에 붙이면 Vault에서 시크릿을 가져와서 파일로 마운트한다. 애플리케이션은 환경 변수 대신 파일에서 시크릿을 읽는다.

```yaml
spec:
  serviceAccountName: myapp-sa
  initContainers:
  - name: vault-agent-init
    image: vault:1.15
    args:
    - agent
    - -config=/vault/config/agent-config.hcl
    volumeMounts:
    - name: vault-config
      mountPath: /vault/config
    - name: secrets
      mountPath: /vault/secrets
  containers:
  - name: myapp
    image: myapp:latest
    volumeMounts:
    - name: secrets
      mountPath: /app/secrets
      readOnly: true
```

```hcl
# agent-config.hcl
vault {
  address = "https://vault.internal:8200"
}

auto_auth {
  method "kubernetes" {
    mount_path = "auth/kubernetes"
    config = {
      role = "myapp-role"
    }
  }
}

template {
  source      = "/vault/templates/secrets.tpl"
  destination = "/vault/secrets/app.env"
  command     = "kill -HUP $(pidof myapp)"  # 시크릿 갱신 시 애플리케이션에 시그널
}
```

Vault Agent 방식은 설정이 복잡하지만 시크릿 회전이 파드 재시작 없이 된다. TTL 기반으로 시크릿을 자동 갱신하고, 갱신 후 애플리케이션에 시그널을 보내서 재로드하게 만들 수 있다.

Kubernetes에서 Vault를 쓸 때 Vault Agent Injector를 도입하면 어노테이션만 추가해도 사이드카를 자동으로 주입해준다.

```yaml
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "myapp-role"
    vault.hashicorp.com/agent-inject-secret-config: "secret/data/myapp/prod"
```

### 선택 기준

시크릿 수가 적고 회전 주기가 길다면 환경 변수 방식으로 충분하다. 동적 자격증명(DB, cloud credentials)이 필요하거나 세밀한 접근 제어가 필요하다면 Vault를 쓴다. 처음부터 Vault를 도입하는 건 운영 부담이 크므로, 먼저 CI 시스템의 시크릿 저장소로 시작하고 문제가 생길 때 전환하는 게 현실적이다.

## 파이프라인 실패 알림과 원인 추적

### 알림 채널 설정

파이프라인이 실패했을 때 담당자가 빠르게 인지하지 못하면 배포가 늦어진다. 알림은 실패한 단계와 브랜치 정보를 함께 보내야 누가 무엇을 봐야 하는지 바로 알 수 있다.

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "파이프라인 실패",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*${{ github.workflow }}* 실패\n브랜치: `${{ github.ref_name }}`\n실패 단계: `${{ github.job }}`\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|로그 보기>"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

`if: failure()`는 앞선 단계 중 하나라도 실패하면 실행된다. 성공/실패 모두 알림을 보내면 슬랙이 노이즈로 가득 차서 결국 알림을 무시하게 된다. 실패만 알리는 게 낫다.

### 원인 추적

빌드 로그가 길면 어디서 실패했는지 찾는 데 시간이 걸린다. 테스트 결과를 별도 아티팩트로 저장하면 로그 전체를 뒤지지 않아도 된다.

```yaml
- name: Run tests
  run: npx jest --json --outputFile=test-results.json || true

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: test-results.json

- name: Publish test report
  if: always()
  uses: dorny/test-reporter@v1
  with:
    name: Jest Tests
    path: test-results.json
    reporter: jest-json
```

`if: always()`는 테스트가 실패해도 아티팩트를 업로드하도록 강제한다. 테스트 명령 뒤에 `|| true`를 붙이면 테스트 실패가 파이프라인을 즉시 중단시키지 않고 리포트를 저장하도록 한다.

배포 실패의 경우 Kubernetes 이벤트와 파드 로그를 자동으로 수집해서 알림에 첨부하면 원인 파악이 빨라진다.

```bash
#!/bin/bash
NAMESPACE=$1
DEPLOYMENT=$2

# 최근 이벤트 수집
kubectl get events -n $NAMESPACE \
  --field-selector involvedObject.name=$DEPLOYMENT \
  --sort-by='.lastTimestamp' | tail -20

# 실패한 파드 로그 수집
FAILED_PODS=$(kubectl get pods -n $NAMESPACE \
  -l app=$DEPLOYMENT \
  --field-selector status.phase=Failed \
  -o jsonpath='{.items[*].metadata.name}')

for pod in $FAILED_PODS; do
  echo "=== Logs for $pod ==="
  kubectl logs -n $NAMESPACE $pod --previous 2>/dev/null | tail -50
done
```

배포 파이프라인 실패 시 이 스크립트를 실행하고 결과를 슬랙 메시지에 붙여서 보내면, 문제가 생겼을 때 클러스터에 직접 접근하지 않아도 초기 진단이 가능하다.

### 파이프라인 메트릭 수집

시간이 지나면서 어떤 단계가 느려지고 있는지 추적하려면 파이프라인 실행 시간을 메트릭으로 수집해야 한다. GitHub Actions 자체 인사이트 화면도 있지만 팀 내부 대시보드로 통합하려면 직접 수집해야 한다.

Prometheus Pushgateway에 메트릭을 밀어넣는 방식이 있다.

```yaml
- name: Push pipeline metrics
  if: always()
  run: |
    BUILD_DURATION=${{ steps.build.outputs.duration }}
    cat <<EOF | curl --data-binary @- http://pushgateway:9091/metrics/job/cicd/instance/${{ github.repository }}
    # HELP cicd_build_duration_seconds CI/CD build duration
    # TYPE cicd_build_duration_seconds gauge
    cicd_build_duration_seconds{branch="${{ github.ref_name }}",status="${{ job.status }}"} $BUILD_DURATION
    EOF
```

빌드 시간이 특정 브랜치에서 갑자기 길어지면 Grafana 알림을 통해 파악할 수 있다. 대부분 캐시 미스가 원인인 경우가 많다.
