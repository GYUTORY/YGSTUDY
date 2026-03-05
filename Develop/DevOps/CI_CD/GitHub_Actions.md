---
title: GitHub Actions CI/CD 가이드
tags: [devops, cicd, github-actions, workflow, automation, deployment]
updated: 2026-03-01
---

# GitHub Actions

## 개요

GitHub Actions는 GitHub에 내장된 CI/CD 플랫폼이다. 코드 push, PR, 이슈, 스케줄 등 다양한 **이벤트**에 반응하여 워크플로우를 자동 실행한다. GitHub Marketplace에 수천 개의 재사용 가능한 액션이 있어 빠르게 파이프라인을 구성할 수 있다.

### 핵심 특징

| 특징 | 설명 |
|------|------|
| **이벤트 기반** | push, PR, issue, schedule, webhook 등 다양한 트리거 |
| **매트릭스 빌드** | 여러 OS/언어 버전 조합을 병렬 테스트 |
| **재사용 가능한 액션** | Marketplace 액션 + 커스텀 액션으로 조합 |
| **Self-hosted Runner** | 자체 서버에서 실행 가능 (GPU, 특수 하드웨어) |
| **무료 크레딧** | 퍼블릭 리포: 무제한, 프라이빗: 2,000분/월 |

### CI/CD 도구 비교

| 항목 | GitHub Actions | Bitbucket Pipelines | GitLab CI | Jenkins |
|------|---------------|-------------------|-----------|---------|
| **설정 파일** | `.github/workflows/*.yml` | `bitbucket-pipelines.yml` | `.gitlab-ci.yml` | `Jenkinsfile` |
| **실행 환경** | GitHub-hosted / Self-hosted | Cloud only | Cloud / Self-hosted | Self-hosted |
| **무료 크레딧** | 2,000분/월 | 2,500분/월 | 400분/월 | 무제한 (자체 서버) |
| **Marketplace** | 수천 개 액션 | 제한적 Pipes | 제한적 | 플러그인 수천 개 |
| **매트릭스 빌드** | 네이티브 | 미지원 | 네이티브 | 플러그인 필요 |
| **컨테이너 지원** | 네이티브 | 네이티브 | 네이티브 | 플러그인 |

## 핵심 개념

### 1. 워크플로우 구조

```
Repository
└── .github/
    └── workflows/
        ├── ci.yml          ← push/PR 시 빌드+테스트
        ├── cd.yml          ← main 머지 시 배포
        └── scheduled.yml   ← 크론 스케줄 작업
```

```yaml
name: CI Pipeline          # 워크플로우 이름

on:                         # 트리거 이벤트
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:                       # 작업 정의
  build:                    # job 이름
    runs-on: ubuntu-latest  # 실행 환경
    steps:                  # 순차 실행 단계
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
```

#### 용어 정리

| 용어 | 설명 | 비유 |
|------|------|------|
| **Workflow** | 전체 자동화 파이프라인 | 공장 전체 |
| **Event** | 워크플로우를 시작하는 트리거 | 시작 버튼 |
| **Job** | 같은 러너에서 실행되는 step 그룹 | 조립 라인 |
| **Step** | job 내 개별 작업 단위 | 작업 공정 |
| **Action** | 재사용 가능한 단위 작업 | 공정 도구 |
| **Runner** | 워크플로우를 실행하는 서버 | 작업자 |

### 2. 이벤트 트리거

#### 주요 이벤트

```yaml
on:
  # 코드 변경
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'package.json'
    tags:
      - 'v*'

  # PR 이벤트
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]

  # 수동 실행
  workflow_dispatch:
    inputs:
      environment:
        description: '배포 환경'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

  # 스케줄 (UTC 기준)
  schedule:
    - cron: '0 9 * * 1-5'  # 평일 오전 9시 (UTC)

  # 다른 워크플로우 완료 시
  workflow_run:
    workflows: ["CI"]
    types: [completed]
```

#### 경로 필터링

```yaml
on:
  push:
    paths:
      - 'src/**'
      - '!src/**/*.test.js'   # 테스트 파일은 제외
    paths-ignore:
      - 'docs/**'
      - '*.md'
```

### 3. Job과 의존성

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    needs: lint              # lint 완료 후 실행
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  deploy:
    runs-on: ubuntu-latest
    needs: [lint, test]      # 둘 다 완료 후 실행
    if: github.ref == 'refs/heads/main'
    steps:
      - run: echo "Deploying..."
```

```
lint ──→ test ──→ deploy
         ↗
(lint과 test가 모두 성공해야 deploy 실행)
```

### 4. 매트릭스 빌드

여러 환경 조합을 병렬로 테스트한다.

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node-version: [18, 20, 22]
        exclude:
          - os: windows-latest
            node-version: 18
        include:
          - os: ubuntu-latest
            node-version: 22
            experimental: true
      fail-fast: false        # 하나 실패해도 나머지 계속 실행

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
```

이 설정으로 `3 OS × 3 Node = 9개` 조합 중 exclude 1개를 뺀 **8개 빌드**가 병렬 실행된다.

### 5. 환경 변수와 시크릿

```yaml
env:                              # 워크플로우 레벨
  NODE_ENV: production

jobs:
  build:
    runs-on: ubuntu-latest
    env:                          # job 레벨
      DATABASE_URL: postgres://localhost:5432/test

    steps:
      - name: Build
        env:                      # step 레벨
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "Node env: $NODE_ENV"
          npm run build
```

#### 시크릿 관리

```
GitHub Repository > Settings > Secrets and variables > Actions

Repository secrets:  모든 워크플로우에서 사용
Environment secrets: 특정 환경(staging, production)에서만 사용
```

| 레벨 | 범위 | 용도 |
|------|------|------|
| **Repository secret** | 전체 워크플로우 | API 키, 토큰 |
| **Environment secret** | 특정 환경 | DB 비밀번호, 배포 키 |
| **Organization secret** | 조직 전체 리포 | 공통 자격증명 |

#### 기본 제공 환경 변수

```yaml
steps:
  - run: |
      echo "커밋: ${{ github.sha }}"
      echo "브랜치: ${{ github.ref_name }}"
      echo "이벤트: ${{ github.event_name }}"
      echo "리포: ${{ github.repository }}"
      echo "PR 번호: ${{ github.event.pull_request.number }}"
      echo "액터: ${{ github.actor }}"
```

## 실전 워크플로우

### Spring Boot CI/CD

```yaml
# .github/workflows/ci.yml
name: Spring Boot CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  JAVA_VERSION: '17'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─── 빌드 & 테스트 ───
  build:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: JDK 설정
        uses: actions/setup-java@v4
        with:
          java-version: ${{ env.JAVA_VERSION }}
          distribution: 'temurin'
          cache: 'gradle'

      - name: Gradle 빌드
        run: ./gradlew build
        env:
          SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb
          SPRING_DATASOURCE_USERNAME: test
          SPRING_DATASOURCE_PASSWORD: test
          SPRING_REDIS_HOST: localhost

      - name: 테스트 리포트
        uses: dorny/test-reporter@v1
        if: always()
        with:
          name: Test Results
          path: build/test-results/test/*.xml
          reporter: java-junit

      - name: 빌드 결과물 업로드
        uses: actions/upload-artifact@v4
        with:
          name: app-jar
          path: build/libs/*.jar
          retention-days: 1

  # ─── Docker 이미지 빌드 & 푸시 ───
  docker:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: 빌드 결과물 다운로드
        uses: actions/download-artifact@v4
        with:
          name: app-jar
          path: build/libs

      - name: Docker 메타데이터
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - name: GHCR 로그인
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker 빌드 & 푸시
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─── 배포 ───
  deploy:
    needs: docker
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: K8s 배포
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            kubectl set image deployment/myapp \
              app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
              -n production
            kubectl rollout status deployment/myapp -n production
```

### Node.js CI

```yaml
name: Node.js CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        node-version: [18, 20]

    steps:
      - uses: actions/checkout@v4

      - name: Node.js ${{ matrix.node-version }} 설정
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run build
      - run: npm test

      - name: 커버리지 업로드
        if: matrix.node-version == 20
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

### Docker 이미지 → AWS ECR → ECS 배포

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: myapp
  ECS_CLUSTER: production
  ECS_SERVICE: myapp-service

jobs:
  deploy:
    runs-on: ubuntu-latest

    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: AWS 자격증명 설정 (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: ECR 로그인
        id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Docker 빌드 & ECR 푸시
        env:
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: ECS 태스크 정의 업데이트
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: myapp
          image: ${{ steps.ecr-login.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}

      - name: ECS 서비스 배포
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### MkDocs 자동 배포 (이 사이트에서 사용 중)

```yaml
name: Deploy MkDocs

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - run: pip install mkdocs-material mkdocs-awesome-pages-plugin

      - run: mkdocs gh-deploy --force
        working-directory: ./Develop
```

## 고급 기능

### 1. 캐싱

빌드 시간을 크게 단축하는 핵심 기능이다.

```yaml
# setup-* 액션의 내장 캐시 (권장)
- uses: actions/setup-node@v4
  with:
    node-version: 20
    cache: 'npm'

# 커스텀 캐시
- uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: gradle-${{ runner.os }}-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
    restore-keys: |
      gradle-${{ runner.os }}-
```

| 패키지 매니저 | 캐시 경로 | setup 액션 캐시 |
|-------------|----------|----------------|
| npm | `~/.npm` | `cache: 'npm'` |
| Gradle | `~/.gradle/caches` | `cache: 'gradle'` |
| Maven | `~/.m2/repository` | `cache: 'maven'` |
| pip | `~/.cache/pip` | `cache: 'pip'` |

### 2. 아티팩트

Job 간 파일을 전달하거나 빌드 결과를 보존한다.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
          retention-days: 5

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/

      - run: ls -la dist/
```

### 3. 재사용 가능한 워크플로우

공통 로직을 별도 워크플로우로 분리하여 재사용한다.

```yaml
# .github/workflows/reusable-build.yml (재사용 워크플로우)
name: Reusable Build

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
    secrets:
      npm-token:
        required: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci
      - run: npm test
```

```yaml
# .github/workflows/ci.yml (호출하는 워크플로우)
name: CI

on:
  push:
    branches: [main]

jobs:
  call-build:
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'
    secrets:
      npm-token: ${{ secrets.NPM_TOKEN }}
```

### 4. 컨테이너 서비스

테스트에 필요한 DB, 캐시 등을 서비스 컨테이너로 실행한다.

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - run: npm test
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
```

### 5. 조건부 실행

```yaml
steps:
  # 특정 브랜치에서만
  - run: npm run deploy
    if: github.ref == 'refs/heads/main'

  # PR에서만
  - run: npm run preview
    if: github.event_name == 'pull_request'

  # 이전 step 실패해도 실행
  - run: npm run cleanup
    if: always()

  # 이전 step 성공했을 때만
  - run: echo "Success!"
    if: success()

  # 커밋 메시지에 특정 키워드
  - run: npm run deploy
    if: contains(github.event.head_commit.message, '[deploy]')

  # 특정 파일 변경 시 (dorny/paths-filter 액션)
  - uses: dorny/paths-filter@v3
    id: changes
    with:
      filters: |
        backend:
          - 'src/**'
        frontend:
          - 'web/**'

  - run: npm run test:backend
    if: steps.changes.outputs.backend == 'true'
```

### 6. Environment와 승인 프로세스

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging           # staging 환경
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production             # production 환경 (승인 필요)
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

```
GitHub Repository > Settings > Environments > production
  → Required reviewers: 팀 리드, 시니어 개발자
  → Wait timer: 5분
  → Deployment branches: main only
```

## 커스텀 액션 만들기

### Composite Action

```yaml
# .github/actions/setup-project/action.yml
name: 'Setup Project'
description: '프로젝트 공통 설정'

inputs:
  node-version:
    description: 'Node.js 버전'
    required: false
    default: '20'

runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - name: 의존성 설치
      shell: bash
      run: npm ci

    - name: 환경 검증
      shell: bash
      run: |
        node --version
        npm --version
```

```yaml
# 워크플로우에서 사용
steps:
  - uses: actions/checkout@v4
  - uses: ./.github/actions/setup-project
    with:
      node-version: '20'
  - run: npm test
```

## 보안

### OIDC로 클라우드 인증 (시크릿 없이)

기존 방식은 AWS Access Key를 시크릿에 저장했지만, **OIDC**를 사용하면 임시 자격증명으로 인증하여 더 안전하다.

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789012:role/github-actions
      aws-region: ap-northeast-2
      # Access Key 불필요!
```

### 권한 최소화

```yaml
# 워크플로우 레벨에서 권한 제한
permissions:
  contents: read      # 코드 읽기만
  packages: write     # 패키지 쓰기 필요 시
  pull-requests: write # PR 코멘트 필요 시
```

### Dependabot 자동 업데이트

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

## 운영 팁

### 워크플로우 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| 캐시 설정 | npm/gradle 캐시로 빌드 시간 단축 | ✅ |
| 시크릿 관리 | 민감 정보는 반드시 Secrets 사용 | ✅ |
| 타임아웃 설정 | `timeout-minutes`로 무한 실행 방지 | ✅ |
| 권한 최소화 | `permissions`로 필요한 권한만 부여 | ✅ |
| 브랜치 보호 | main 브랜치 CI 통과 필수 설정 | ✅ |
| 매트릭스 빌드 | 여러 환경에서 테스트 | ⭐ |
| Environment 승인 | 프로덕션 배포 전 승인 프로세스 | ⭐ |
| OIDC 인증 | 클라우드 인증은 OIDC 사용 | ⭐ |

### 흔한 실수

| 실수 | 결과 | 해결 |
|------|------|------|
| 시크릿을 로그에 출력 | 자격증명 노출 | `add-mask` 사용, echo 금지 |
| `fail-fast: true` (기본값) | 하나 실패 시 전체 중단 | `fail-fast: false` 설정 |
| 타임아웃 미설정 | 무한 실행으로 크레딧 소진 | `timeout-minutes: 30` |
| 캐시 키 미설정 | 매번 의존성 재설치 | lock 파일 해시 기반 캐시 키 |
| `actions/checkout` 누락 | 코드 없이 실행 | 첫 step에 반드시 추가 |

### 디버깅

```yaml
steps:
  # 디버그 로깅 활성화
  - run: echo "ACTIONS_STEP_DEBUG=true" >> $GITHUB_ENV

  # 컨텍스트 정보 출력
  - run: echo '${{ toJSON(github) }}'

  # SSH 접속으로 디버깅 (tmate)
  - uses: mxschmitt/action-tmate@v3
    if: failure()
    timeout-minutes: 15
```

### 비용 최적화

```yaml
# 1. 불필요한 빌드 건너뛰기
on:
  push:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.gitignore'

# 2. 동시 실행 제한 (같은 브랜치 중복 빌드 방지)
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# 3. 타임아웃 설정
jobs:
  build:
    timeout-minutes: 15
```

## 참고

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [워크플로우 문법 레퍼런스](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Bitbucket Pipelines](Bitbucket_Pipeline.md) — Bitbucket CI/CD
- [GitOps 전략](../GitOps/GitOps_전략.md) — Git 기반 배포 전략
- [Kubernetes](../Kubernetes/Kubernetes.md) — 컨테이너 오케스트레이션
- [Docker](../Kubernetes/Docker/Docker_Compose.md) — 컨테이너 빌드
