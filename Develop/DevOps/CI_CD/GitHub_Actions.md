---
title: GitHub Actions CI/CD
tags: [devops, ci-cd, architecture, security]
updated: 2026-10-08
description: "GitHub 내장 CI/CD 플랫폼으로 이벤트 기반 워크플로우를 자동화하는 방법"
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

이벤트 하나가 실행으로 이어지는 경로는 아래 그림이 전부다. job은 `needs`로 순서가 정해지고, job마다 러너가 따로 할당되며, step은 할당된 러너 안에서 순서대로 돈다. 러너가 job마다 갈리므로 `lint`에서 만든 파일은 `test`에서 보이지 않는다. job 사이에 파일을 넘기려면 아티팩트를 쓴다.

```mermaid
flowchart TB
    EV["이벤트<br/>push, pull_request, schedule"] --> WF["워크플로 파일<br/>.github/workflows/ci.yml"]
    WF --> LINT
    subgraph JOBS["jobs, 순서는 needs가 정한다"]
        LINT["lint job"] --> TEST["test job<br/>needs lint"]
        TEST --> DEPLOY["deploy job<br/>needs lint, test"]
    end
    LINT -.->|"러너 할당"| R1["runner 1<br/>새 VM"]
    TEST -.->|"러너 할당"| R2["runner 2<br/>새 VM"]
    DEPLOY -.->|"러너 할당"| R3["runner 3<br/>새 VM"]
    R2 --> S1["step 1 checkout"] --> S2["step 2 npm ci"] --> S3["step 3 npm test"]
```

점선이 job과 러너의 연결이고, 아래로 이어지는 step 체인은 `test` job 하나만 펼친 것이다. GitHub-hosted 러너는 job이 끝나면 VM이 버려진다. self-hosted 러너는 기본 설정이면 같은 머신을 계속 쓰므로 이전 job의 파일이 남는다. 이 차이는 보안 절에서 다시 나온다.

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

위 그림의 화살표가 그대로 실행 순서다. `deploy`의 `needs: [lint, test]`에서 `lint`는 `test`가 이미 의존하므로 빼도 동작이 같다.

조용히 넘어가는 지점이 하나 있다. `needs`로 걸린 job이 실패하거나 skip되면 그 job에 의존하는 job도 skip된다. 실패는 눈에 띄지만, 앞선 job이 자기 `if` 조건 때문에 skip된 경우에는 `deploy`까지 줄줄이 skip되고 워크플로는 초록불로 끝난다. 배포가 안 나갔는데 CI는 성공으로 보이는 상황이 이렇게 생긴다. 앞 job을 조건부로 만들었다면 뒤 job의 `if`에 `!cancelled() && !failure()` 같은 조건을 명시해서 skip 전파를 끊을지 정해야 한다.

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

#### 캐시가 조용히 깨지는 지점

캐시는 실패해도 에러가 나지 않는다. 미스가 나면 빌드가 느려질 뿐이라 몇 주씩 방치된다.

아래 그림은 job이 시작될 때 캐시를 찾는 순서와, 끝날 때 저장 여부가 갈리는 지점이다. 정확히 일치하는 key를 찾으면 저장 단계 자체가 없다는 점, `restore-keys`로 복원한 경우에만 새 key로 저장된다는 점을 보면 된다.

```mermaid
flowchart TB
    START["job 시작: key 계산"] --> EXACT{"key가 정확히 일치하는 캐시가 있는가"}
    EXACT -->|"hit"| RESTORE1["그 캐시를 복원"]
    RESTORE1 --> RUN1["빌드 실행"]
    RUN1 --> NOSAVE["job 끝: 저장 건너뜀<br/>같은 key는 덮어쓰지 않는다"]
    EXACT -->|"miss"| PREFIX{"restore-keys 접두사로 일치하는 캐시가 있는가"}
    PREFIX -->|"있음"| RESTORE2["가장 최근 캐시를 복원<br/>제거한 의존성의 파일도 섞여 있다"]
    PREFIX -->|"없음"| COLD["캐시 없이 처음부터 받는다"]
    RESTORE2 --> RUN2["빌드 실행"]
    COLD --> RUN2
    RUN2 --> SAVE["job 끝: 새 key로 저장"]
```

**같은 key로는 덮어쓸 수 없다.** key가 정확히 일치해서 hit하면 job 끝의 저장 단계는 건너뛴다. key를 `gradle-cache` 같은 고정 문자열로 두면 첫 실행에서 저장된 내용이 영원히 복원된다. 의존성을 올려도 캐시는 그대로고, 매 빌드가 부족한 부분을 새로 받아오기만 한다.

**`hashFiles`는 일치하는 파일이 없으면 에러 없이 빈 문자열을 돌려준다.** key가 `gradle-Linux-`로 고정되어 위와 똑같은 상태가 된다. Gradle 버전 카탈로그를 쓰는 프로젝트에서 `gradle/libs.versions.toml`을 해시 대상에 넣지 않으면, 라이브러리 버전을 바꿔도 key가 그대로다. 로그의 `Cache restored from key:` 줄에서 해시 부분이 비어 있거나 PR마다 같은 값인지 한 번은 확인한다.

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: gradle-${{ runner.os }}-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties', '**/libs.versions.toml') }}
    restore-keys: |
      gradle-${{ runner.os }}-
```

**`restore-keys`는 접두사로 옛 캐시를 복원한 뒤 새 key로 저장한다.** 빌드는 빨라지지만 의존성을 제거해도 캐시 안의 파일은 빠지지 않고 쌓인다. 캐시가 커질수록 복원과 저장 시간이 늘어서, 어느 시점부터는 캐시가 없는 쪽이 빠른 경우도 있다.

**저장소 전체 캐시 용량은 10GB이고 7일간 접근이 없으면 지워진다.** 매트릭스 조합마다 key가 갈리면 금방 찬다. 용량이 차면 오래된 것부터 삭제되는데, 이것도 에러 없이 미스로만 나타난다.

**PR은 자기 브랜치와 base 브랜치의 캐시만 복원할 수 있다.** PR A가 저장한 캐시를 PR B는 읽지 못한다. main에서 한 번도 같은 key로 저장하지 않았다면 PR마다 캐시 없이 처음부터 받는다. push to main에서도 같은 job이 돌아야 PR들이 그 캐시를 공유한다.

캐시를 쓰면 안 되는 경우도 있다. `~/.docker/config.json`, `~/.aws`, `.env`처럼 자격증명이 들어 있는 경로는 캐시 path에 넣지 않는다. 캐시 내용은 같은 범위의 다른 워크플로가 복원할 수 있고, 오염된 캐시를 복원한 job이 그 안의 파일을 실행하는 공격이 실제로 있다. 캐시 대상은 의존성 다운로드물까지만 두고 빌드 결과물이나 설정 파일은 넣지 않는다.

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

공통 로직을 별도 워크플로우로 분리하여 재사용한다. job 단위로 호출되므로 호출할 때마다 러너가 새로 할당된다.

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
    outputs:
      artifact-name:
        description: "업로드한 아티팩트 이름"
        value: ${{ jobs.build.outputs.artifact-name }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      artifact-name: ${{ steps.meta.outputs.name }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci
        env:
          NODE_AUTH_TOKEN: ${{ secrets.npm-token }}
      - run: npm test
      - id: meta
        run: echo "name=dist-node-${{ inputs.node-version }}" >> "$GITHUB_OUTPUT"
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

  report:
    needs: call-build
    runs-on: ubuntu-latest
    steps:
      - run: echo "artifact=${ARTIFACT}"
        env:
          ARTIFACT: ${{ needs.call-build.outputs.artifact-name }}
```

#### 쓰면 안 되는 경우와 조용히 깨지는 지점

호출하는 쪽이 하나뿐이거나 공유할 것이 step 서너 줄이면 재사용 워크플로를 쓸 이유가 없다. 같은 job 안에서 도는 composite action(아래 "커스텀 액션 만들기")이 러너를 새로 받지 않아 빠르고, 호출 쪽에서 파일 시스템을 그대로 이어 쓴다. 재사용 워크플로는 job 전체를 통째로 공유해야 하거나 여러 저장소가 같은 파이프라인을 써야 할 때 고른다.

`outputs`는 두 군데 모두 선언해야 한다. 호출되는 워크플로의 job에서 `outputs`를 만들고, 다시 `on.workflow_call.outputs`에서 그 값을 받아 내보내야 한다. 한 군데라도 빠지면 호출하는 쪽의 `needs.call-build.outputs.artifact-name`은 에러 없이 빈 문자열이다.

호출하는 워크플로의 `env`는 넘어가지 않는다. 최상단 `env:`에 `NODE_ENV`를 두고 재사용 워크플로를 불렀는데 안에서 비어 있다면 이 때문이다. 값은 `with:`의 `inputs`로 넘겨야 한다. 시크릿도 명시적으로 `secrets:`에 나열하거나 `secrets: inherit`를 써야 하고, `inherit`는 호출되는 쪽이 같은 조직 안에 있을 때만 된다.

`permissions`는 호출하는 쪽보다 넓힐 수 없다. 호출된 워크플로 안에서 `packages: write`를 선언해도 호출하는 쪽이 `contents: read`뿐이면 `GITHUB_TOKEN`은 읽기만 가능하고, 푸시 단계에서 권한 오류가 난다.

위 네 가지가 호출 경계를 어떻게 건너는지 한 그림으로 정리하면 아래와 같다. 점선은 넘어가지 않는 것이고, 실선은 명시해야 넘어가는 것이다.

```mermaid
flowchart LR
    subgraph CALLER["호출하는 워크플로 ci.yml"]
        CENV["최상단 env"]
        CWITH["with"]
        CSEC["secrets"]
        CPERM["permissions"]
        CNEEDS["report job<br/>needs.call-build.outputs"]
    end
    subgraph CALLED["호출되는 워크플로 reusable-build.yml"]
        INP["inputs"]
        SEC["secrets"]
        TOKEN["GITHUB_TOKEN 권한"]
        JOBOUT["jobs.build.outputs"]
        WCOUT["on.workflow_call.outputs"]
    end
    CENV -.->|"넘어가지 않음"| EMPTY["안에서는 빈 값"]
    CWITH -->|"inputs로 전달"| INP
    CSEC -->|"나열하거나 inherit"| SEC
    CPERM -->|"상한, 넓힐 수 없음"| TOKEN
    JOBOUT --> WCOUT
    WCOUT -->|"두 군데 모두 선언해야 도달"| CNEEDS
```

호출 체인은 4단계까지만 허용된다. 그리고 재사용 워크플로로 바꾸는 순간 브랜치 보호의 required check 이름이 `build`에서 `call-build / build`로 바뀐다. 기존 규칙에 `build`가 등록되어 있으면 새 이름의 체크는 아무도 요구하지 않고, 옛 이름의 체크는 영원히 보고되지 않아 PR이 머지되지 않는다.

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

승인 게이트는 job 시작 직전에 걸린다. 승인이 나기 전까지 `deploy` job은 러너를 잡지 않고, environment 시크릿도 주입되지 않는다. 아래 그림은 build를 통과한 뒤 승인을 거쳐 AWS 역할을 수임하는 흐름이다. 승인 대기 구간과 OIDC 토큰을 받는 구간이 각각 어디인지 보면 된다.

```mermaid
sequenceDiagram
    participant Dev as 개발자
    participant GH as GitHub
    participant Build as build job
    participant Rev as Required reviewers
    participant Deploy as deploy job
    participant OIDC as GitHub OIDC 발급자
    participant STS as AWS STS

    Dev->>GH: main에 push
    GH->>Build: 러너 할당
    Build-->>GH: 빌드 성공, 아티팩트 업로드
    GH->>Rev: production 배포 승인 요청
    Note over GH,Rev: deploy job은 대기 상태, 러너와 environment 시크릿 없음
    Rev-->>GH: 승인
    GH->>Deploy: 러너 할당, environment 시크릿 주입
    Deploy->>OIDC: ID 토큰 요청 (id-token write 필요)
    OIDC-->>Deploy: JWT, sub 클레임에 environment 이름 포함
    Deploy->>STS: AssumeRoleWithWebIdentity
    STS-->>Deploy: 임시 자격증명
    Deploy->>Deploy: aws s3 cp 로 배포
```

```yaml
name: Deploy

on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew bootJar
      - uses: actions/upload-artifact@v4
        with:
          name: app-jar
          path: build/libs/*.jar

  deploy:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment:
      name: production
      url: https://example.com
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: app-jar
          path: build/libs
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy-production
          aws-region: ap-northeast-2
      - run: aws s3 cp build/libs/ s3://my-deploy-bucket/releases/ --recursive
```

`environment: production`을 붙인 job의 OIDC 토큰은 `sub`가 `repo:my-org/my-repo:environment:production` 형태로 발급된다. IAM 역할의 신뢰 정책이 이 값을 조건으로 걸어야 승인 게이트가 AWS 쪽까지 이어진다. 조건이 `repo:my-org/my-repo:*`처럼 느슨하면 승인 없이 도는 다른 job이나 다른 브랜치의 워크플로도 같은 역할을 수임한다. 게이트는 워크플로 안에만 있고 AWS는 그걸 모르기 때문이다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:environment:production"
        }
      }
    }
  ]
}
```

승인 설정에서 자주 놓치는 것이 둘 있다. Required reviewers에 push한 본인이 들어 있으면 스스로 승인할 수 있으므로 "Prevent self-review"를 켠다. 그리고 Deployment branches를 `main`으로 제한하지 않으면 `workflow_dispatch`로 feature 브랜치에서 production 배포를 돌릴 수 있다.

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

Actions 보안 사고는 대부분 워크플로가 외부 입력을 받는 자리, 외부 코드를 실행하는 자리에서 난다. 사고 사례는 [GitHub 보안사고](../../Security/Git_Hub_Security_Incidents.md)와 [CI/CD 파이프라인 공격](../../Security/CI_CD_Pipeline_Attacks.md)에 정리되어 있고, 이 절은 워크플로를 쓸 때 바로 적용할 설정만 다룬다.

### 시크릿과 GITHUB_TOKEN이 보이는 범위

같은 시크릿이라도 워크플로를 누가 어떤 트리거로 돌렸느냐에 따라 보이는 범위가 다르다. 아래 그림에서 `pull_request_target`만 외부인이 만든 코드와 시크릿이 같은 자리에 놓인다.

```mermaid
flowchart LR
    Q["워크플로가 도는 자리"] --> A["같은 저장소 브랜치의 PR<br/>pull_request"]
    Q --> B["포크 PR<br/>pull_request"]
    Q --> C["포크 PR<br/>pull_request_target"]
    Q --> D["job 안의 서드파티 액션"]
    A --> A1["secrets 주입<br/>GITHUB_TOKEN은 permissions 선언대로"]
    B --> B1["secrets 없음<br/>GITHUB_TOKEN 읽기 전용"]
    C --> C1["secrets 주입<br/>GITHUB_TOKEN 쓰기 가능<br/>PR 코드를 실행하면 외부인이 시크릿을 쓰는 것과 같다"]
    D --> D1["with, env로 넘긴 값은 받는다<br/>같은 러너라 job env, 파일, 프로세스 메모리도 읽을 수 있다"]
```

| 자리 | secrets | GITHUB_TOKEN | 주의할 점 |
|------|---------|--------------|-----------|
| 같은 저장소 PR | 주입됨 | `permissions` 선언대로 | 협업자 권한이면 워크플로 파일을 고쳐서 시크릿을 꺼낼 수 있다 |
| 포크 PR (`pull_request`) | 주입 안 됨 | 읽기 전용 | 외부 기여 PR에서만 CI가 깨지면 이 차이부터 의심한다 |
| 포크 PR (`pull_request_target`) | 주입됨 | 쓰기 가능 | base 브랜치의 워크플로가 실행된다. PR head를 체크아웃해 실행하면 끝이다 |
| Dependabot PR | Dependabot 전용 시크릿만 | 읽기 전용 | Actions 시크릿이 없다고 당황하지 말고 Dependabot secrets에 따로 넣는다 |
| 서드파티 액션 | 넘긴 것 + 같은 러너에서 접근 가능한 것 | 체크아웃이 남긴 자격증명 포함 | job 레벨 `env`에 둔 시크릿은 모든 step에 보인다 |

서드파티 액션 행이 가장 자주 간과된다. 시크릿은 `with`나 `env`로 넘긴 것만 액션에 전달된다고 생각하기 쉽지만, 액션은 러너에서 임의 코드를 실행하는 주체다. `env:`를 job 레벨에 두면 그 job의 모든 액션에 시크릿이 보이고, tj-actions 사건처럼 액션이 러너 프로세스 메모리에서 시크릿을 긁어 로그로 내보낸 사례도 있다. 시크릿은 필요한 step의 `env`에만 둔다.

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      persist-credentials: false   # 이후 step이 .git/config에서 토큰을 읽지 못하게 한다
  - name: 배포
    env:
      DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}   # 이 step에서만 보인다
    run: ./deploy.sh
```

### 서드파티 액션은 커밋 SHA로 고정

`uses: some/action@v1`의 `v1`은 태그이고, 태그는 저장소 주인이 다른 커밋으로 옮길 수 있다. 계정이 탈취되면 워크플로 파일은 한 글자도 안 바뀌었는데 실행되는 코드가 바뀐다. 커밋 SHA는 옮길 수 없다.

```yaml
steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

SHA만 적으면 어느 버전인지 알 수 없으므로 뒤에 주석으로 버전을 단다. 아래 Dependabot의 `github-actions` 생태계가 SHA와 주석을 함께 올려주므로 고정한다고 업데이트가 멈추지는 않는다. `actions/*` 공식 액션까지 고정할지는 팀이 정하되, 개인이나 소규모 조직이 관리하는 액션은 예외 없이 고정한다. 일괄 고정 스크립트와 사고 경위는 [CI/CD 파이프라인 공격](../../Security/CI_CD_Pipeline_Attacks.md)에 있다.

### 포크 PR과 pull_request_target

외부 기여를 받는 저장소는 `pull_request`만 쓰면 시크릿이 차단되므로 기본값이 안전하다. 문제는 "포크 PR에도 라벨을 붙이고 코멘트를 달고 싶다"는 요구가 들어와서 `pull_request_target`으로 옮길 때 생긴다. 이 트리거는 쓰기 권한 토큰과 시크릿을 주기 때문에 PR 제목, 브랜치명, 본문을 셸에 그대로 넣거나 PR head를 체크아웃해 빌드하면 외부인이 코드를 실행하는 구조가 된다.

```yaml
# 위험: 제목에 $(curl ...) 이 들어 있으면 그대로 실행된다
- run: echo "${{ github.event.pull_request.title }}"

# 안전: 값을 환경 변수로 받아서 셸이 문자열로만 다루게 한다
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "$PR_TITLE"
```

`${{ }}`는 셸이 실행되기 전에 문자열로 치환되므로, 입력에 따옴표나 `$(...)`가 있으면 명령어가 된다. 환경 변수로 넘기면 치환 결과가 데이터로 남는다. 두 방식에서 PR 제목이 어디에 들어가는지가 다르다.

```mermaid
flowchart LR
    subgraph BAD["위험: run 안에 직접 삽입"]
        B1["PR 제목<br/>$(curl ...) 포함"] --> B2["Actions가 ${{ }}를 문자열로 치환"]
        B2 --> B3["셸 스크립트 텍스트에 제목이 박힘"]
        B3 --> B4["셸이 $(curl ...)을 명령으로 실행"]
    end
    subgraph SAFE["안전: env로 전달"]
        S1["PR 제목<br/>$(curl ...) 포함"] --> S2["환경 변수 PR_TITLE에 값만 저장"]
        S2 --> S3["셸 시작, 스크립트 텍스트는 그대로"]
        S3 --> S4["echo 가 PR_TITLE을 문자열로 출력"]
    end
```

설정 쪽에서는 Settings > Actions > General에서 외부 기여자의 워크플로 실행에 승인을 요구하게 해둔다. `pull_request_target` 인젝션으로 토큰이 나간 실제 사고(Ultralytics, Nx)는 [GitHub 보안사고](../../Security/Git_Hub_Security_Incidents.md)에 있다.

### 공개 저장소에 self-hosted runner를 붙일 때

GitHub-hosted 러너는 job마다 새 VM이 만들어지고 끝나면 버려진다. self-hosted 러너는 기본 설정이면 같은 머신이 다음 job을 받는다. 공개 저장소에 붙이면 누구나 포크 PR로 그 머신에서 임의 코드를 실행할 수 있고, 앞 job이 남긴 파일, 캐시, 러너 계정 자격증명, 러너가 속한 내부망의 다른 서버까지 닿는다. 한 번 심어진 백도어는 다음 job에도 남는다.

두 러너 방식에서 연속된 두 job이 어떻게 이어지는지 비교하면 아래와 같다. 오른쪽에서는 포크 PR의 job이 남긴 흔적이 다음 job으로 그대로 넘어간다.

```mermaid
flowchart LR
    subgraph HOSTED["GitHub-hosted 러너"]
        HA["job A"] --> HVM1["새 VM"]
        HVM1 --> HDEL["job 종료 후 VM 폐기"]
        HDEL --> HB["job B"]
        HB --> HVM2["또 다른 새 VM<br/>A의 흔적 없음"]
    end
    subgraph SELF["self-hosted 러너, 기본 설정"]
        SA["job A, 포크 PR"] --> SM["같은 머신"]
        SM --> SLEFT["파일, 캐시, 러너 계정 자격증명, 백도어가 남음"]
        SLEFT --> SB["job B"]
        SB --> SNET["같은 머신에서 실행<br/>내부망의 다른 서버에 닿음"]
    end
```

공개 저장소에는 self-hosted 러너를 붙이지 않는 것이 원칙이다. GPU처럼 어쩔 수 없이 써야 하면 네 가지를 함께 건다. 러너를 `./config.sh --ephemeral`로 등록해서 job 하나만 받고 사라지게 하고, 러너 그룹으로 허용할 저장소와 워크플로를 제한하고, 외부 기여자의 워크플로 실행에 승인을 요구하고, 러너 머신을 내부망과 분리해 클라우드 인스턴스 메타데이터 접근을 막는다. 하나라도 빠지면 나머지가 막아주지 못한다. ephemeral만 걸고 내부망 분리를 안 하면 job 하나 동안 내부망이 열려 있는 셈이다.

### OIDC로 클라우드 인증 (시크릿 없이)

기존 방식은 AWS Access Key를 시크릿에 저장했지만, **OIDC**를 사용하면 임시 자격증명으로 인증하여 더 안전하다. 역할의 신뢰 정책에서 `sub`를 어떻게 제한하느냐가 실제 안전성을 정한다. environment 단위로 제한하는 예는 위 "Environment와 승인 프로세스"에 있다.

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

## 운영하면서 겪는 문제와 비용

### 실제로 겪는 실패와 원인

**머지 버튼이 영원히 회색이다.** 브랜치 보호에 required check를 걸어둔 상태에서 `paths-ignore: ['docs/**']`로 워크플로 자체가 뜨지 않으면, 문서만 고친 PR은 체크가 보고되지 않아 "Expected — Waiting for status to be reported"에서 멈춘다. 워크플로 레벨 경로 필터를 걷어내고, job 안에서 `dorny/paths-filter`로 판단해 step을 건너뛰게 한다. 매트릭스 값을 바꾸거나 재사용 워크플로로 옮겨서 job 이름이 달라질 때도 같은 증상이 나므로, required check는 이름이 바뀌지 않는 최종 job 하나(`ci-ok` 같은)에만 건다.

**테스트 하나가 멈춰서 6시간을 먹는다.** `timeout-minutes`를 안 쓰면 job 기본 제한은 360분이다. 데드락이 난 통합 테스트가 러너를 6시간 붙잡고 무료 분량을 쓴다. job마다 평소 소요 시간의 2~3배로 걸어둔다. 평소 8분 걸리는 빌드면 20분이 적당하다.

**`fail-fast` 기본값 때문에 원인을 못 찾는다.** 매트릭스 한 조합이 실패하면 나머지 진행 중인 조합은 취소된다. 취소된 조합과 실제로 실패한 조합이 로그에서 비슷하게 보여서, Windows 조합이 가끔 깨지는 프로젝트에서는 매번 어느 쪽이 원인인지부터 가려야 한다. 조합별 결과가 필요하면 `fail-fast: false`를 둔다. 대신 실패한 조합이 있어도 나머지가 끝까지 도므로 분 사용량은 늘어난다.

**마스킹이 되어 있는데도 시크릿이 로그에 보인다.** 로그 마스킹은 등록된 값과 글자 그대로 일치할 때만 동작한다. 시크릿을 base64로 인코딩해 출력하거나, 일부만 잘라 출력하거나, JSON 한 덩어리를 시크릿으로 저장하고 안의 필드를 꺼내 쓰면 마스킹되지 않는다. 런타임에 만들어진 값은 `echo "::add-mask::$VALUE"`로 직접 등록해야 한다. 시크릿에 JSON을 통째로 넣는 습관 자체를 버리고 필드별로 나눠 저장한다.

**`git describe`나 `git diff origin/main...HEAD`가 실패한다.** `actions/checkout`은 기본이 커밋 하나만 가져오는 얕은 클론이다. 태그 기반 버전 계산, 변경 파일 비교, 수정일 플러그인은 모두 전체 히스토리가 필요하므로 `fetch-depth: 0`을 줘야 한다. 에러 메시지는 "unknown revision" 같은 git 쪽 문구로 나와서 Actions 설정 문제라는 걸 알아채기 어렵다.

### 디버깅

디버그 로그는 저장소의 시크릿이나 변수에 `ACTIONS_STEP_DEBUG=true`를 넣거나, 실패한 실행에서 Re-run jobs의 "Enable debug logging"을 체크해서 켠다. 컨텍스트 값은 `${{ }}`를 `run`에 직접 넣지 말고 환경 변수로 받아서 출력한다.

```yaml
steps:
  - name: 컨텍스트 출력
    env:
      GITHUB_CONTEXT: ${{ toJSON(github) }}
    run: echo "$GITHUB_CONTEXT"

  # SSH 접속으로 디버깅 (tmate)
  - uses: mxschmitt/action-tmate@v3
    if: failure()
    timeout-minutes: 15
    with:
      limit-access-to-actor: true
```

`limit-access-to-actor`를 빼면 공개 저장소에서는 세션 주소를 아는 누구나 러너에 접속할 수 있다.

### 비용 줄이기

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

## 초록불인데 나간 결과물이 다른 경우

CI가 잡아주지 못하는 부류가 있다. **검증 스텝과 배포 스텝의 설정이 다른 경우**다. 두 스텝이 서로 다른 빌드를 만들면 검증은 통과하고 배포물만 망가진다. 에러가 안 나므로 몇 달을 방치하게 된다.

아래 그림에서 CI의 초록불은 위쪽 검증 빌드의 결과일 뿐이고, 실제로 나가는 사이트는 아래쪽 배포 빌드가 만든다. 두 빌드가 같은 환경변수·의존성으로 도는지가 갈림길이다.

```mermaid
flowchart LR
    C["같은 커밋"] --> V["검증 스텝<br/>FULL_BUILD=true, 플러그인 전체"]
    C --> D["배포 스텝<br/>env 누락, 플러그인 일부"]
    V --> G["CI 초록불"]
    D --> P["gh-pages에 올라간 사이트<br/>minify, rss, 최종 수정일 없음"]
    G -.->|"여기까지만 확인하면 놓친다"| P
```

### 위의 MkDocs 예제는 이 사이트의 실제 워크플로가 아니다

"이 사이트에서 사용 중"이라고 적어뒀지만, `.github/workflows/deploy-docs.yml`과 대조하면 네 군데가 다르고 **차이 하나하나가 전부 과거에 사고를 냈던 지점**이다.

| 위 예제 | 실제 워크플로 | 예제대로 하면 |
|---|---|---|
| `actions/checkout@v4` (기본 얕은 클론) | `with: fetch-depth: 0` | `git-revision-date-localized`가 히스토리를 못 읽어 문서마다 최종 수정일이 사라진다 |
| `pip install mkdocs-material mkdocs-awesome-pages-plugin` | `pip install -r requirements-docs.txt` (7개) | redirects·rss·minify·git-revision-date 플러그인이 없다 |
| 배포 스텝에 env 없음 | `env: FULL_BUILD: "true"` | minify·rss·git-revision-date가 꺼진 채로 배포된다 |
| `working-directory: ./Develop` | 저장소 루트에서 실행 | `mkdocs.yml`은 루트에 있고 `docs_dir: Develop`이다. Develop 안에는 설정 파일이 없다 |

`FULL_BUILD`를 검증 스텝에만 붙여놨던 시기의 결과는 CLAUDE.md §5-1에 남아 있다 — 1,349개 페이지가 존재하지 않는 RSS 피드를 광고하고(404), HTML은 비압축(2,864줄 vs 136줄)이었으며, 최종 수정일이 전부 없었다. **CI는 계속 초록불이었다.**

배포 워크플로를 손볼 때 확인할 것은 하나다. 검증에 쓴 명령과 배포에 쓴 명령이 같은 환경변수·같은 의존성·같은 작업 디렉토리에서 도는가.

### `cancel-in-progress: true`는 배포에서 의미가 다르다

"비용 줄이기" 항목의 `concurrency`는 테스트 워크플로에서는 낭비를 줄이지만, **배포 워크플로에 붙이면 진행 중인 배포를 중간에 끊는다.** 정적 사이트나 `gh-deploy`처럼 커밋이 누적되는 방식은 마지막 실행이 전부 반영하므로 손실이 없다. 반대로 `kubectl set image` → `rollout status`처럼 단계가 있는 배포는 이미지만 바꾸고 롤아웃 확인 없이 취소될 수 있다. 취소 로그를 보고 놀라기 전에, **이 배포가 중간에 끊겨도 되는 종류인지** 먼저 정한다.

이 저장소는 정적 사이트라 `cancel-in-progress: true`가 맞는 선택이고, 배포는 10~14분 걸린다(CLAUDE.md §5-3).

### `permissions`는 선언한 순간 나머지가 사라진다

```yaml
jobs:
  docker:
    permissions:
      contents: read
      packages: write     # 이 job 은 이 두 개만 갖는다
  deploy:
    # permissions 미선언 → 저장소 기본값을 그대로 받는다
```

`permissions` 블록은 더하는 게 아니라 **그 범위의 권한 집합을 통째로 대체한다.** job 하나에만 붙이면 다른 job은 기본값을 쓰므로 워크플로 안에서 권한이 들쭉날쭉해진다. 최소 권한을 의도했다면 워크플로 최상단에 `permissions: contents: read`를 두고, 필요한 job에서만 넓힌다.

OIDC(`aws-actions/configure-aws-credentials`)를 쓰는 job에 `id-token: write`를 빠뜨리면 "Credentials could not be loaded" 계열로 실패한다. 이 권한은 상속되지 않는다.

### 아티팩트와 시크릿

- `actions/upload-artifact@v4`는 같은 이름으로 두 번 올릴 수 없다. 매트릭스 빌드에서 이름을 고정해두면 첫 조합만 성공하고 나머지가 실패한다. `name: app-jar-${{ matrix.os }}-${{ matrix.node-version }}`처럼 조합을 이름에 넣는다.
- 시크릿은 **로그에서만** 마스킹된다. 아티팩트로 올린 파일, 빌드 결과물에 박힌 값, `toJSON(github)` 출력은 마스킹 대상이 아니다. "디버깅" 항목의 `echo '${{ toJSON(github) }}'`는 PR 본문·브랜치명 같은 사용자 입력을 그대로 찍으므로 상시로 켜두지 않는다.
- 포크에서 온 `pull_request` 이벤트에는 시크릿이 주입되지 않고 `GITHUB_TOKEN`도 읽기 전용이다. 외부 기여 PR에서만 CI가 깨지면 이걸 먼저 의심한다.

### 스케줄 워크플로는 조용히 멈춘다

`schedule` 트리거는 정시에 돈다는 보장이 없고(러너 부하에 따라 밀린다), **공개 저장소에서 60일간 커밋이 없으면 자동으로 비활성화된다.** 주간 보안 스캔 같은 걸 걸어놨다면 "언제부터 안 돌았는지"를 Actions 탭에서 주기적으로 확인하거나, 실패·미실행을 외부에서 감시해야 한다.

## 참고

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [워크플로우 문법 레퍼런스](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Bitbucket Pipelines](Bitbucket_Pipeline.md) — Bitbucket CI/CD
- [GitOps](../GitOps/GitOps_전략.md) — Git 기반 배포
- [Kubernetes](../Kubernetes/Kubernetes.md) — 컨테이너 오케스트레이션
- [Docker](../Kubernetes/Docker/Docker_Compose.md) — 컨테이너 빌드
- [CI/CD 파이프라인 공격](../../Security/CI_CD_Pipeline_Attacks.md) — tj-actions, SHA 고정, 시크릿 회전
- [GitHub 보안사고](../../Security/Git_Hub_Security_Incidents.md) — GitHub가 입구였던 사고 모음
