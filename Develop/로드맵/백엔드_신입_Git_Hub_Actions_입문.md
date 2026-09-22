---
title: 백엔드 신입 GitHub Actions 입문
tags: [ci-cd, devops, aws, docker, backend]
updated: 2026-09-22
---

# 백엔드 신입 GitHub Actions 입문

Docker 입문 문서에서 이미지를 직접 빌드해봤다면, 이제 그 과정을 Push 한 번으로 자동화할 차례다. 이 문서는 테스트 → 빌드 → Docker 이미지 빌드 → ECR 푸시 → ECS 배포까지 이어지는 파이프라인을 실제로 돌아가는 YAML로 설명한다.

GitHub Actions는 선언적 구조라 처음 보면 이해하기 쉬운 것 같은데, 막상 파이프라인이 실패하면 어디가 문제인지 찾는 데 시간을 많이 쓴다. 그 부분을 중점적으로 다룬다.

---

## 파이프라인 전체 구조

파이프라인은 `main` 브랜치에 Push하거나 PR을 열 때 자동으로 동작한다. Job 단위로 분리하면 실패한 단계만 명확히 보인다.

```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: my-app
  ECS_SERVICE: my-app-service
  ECS_CLUSTER: my-cluster
  CONTAINER_NAME: my-app

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Cache Gradle packages
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
          restore-keys: |
            ${{ runner.os }}-gradle-

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Run tests
        run: ./gradlew test

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: build/reports/tests/

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    outputs:
      image: ${{ steps.build-image.outputs.image }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Cache Gradle packages
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
          restore-keys: |
            ${{ runner.os }}-gradle-

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Build with Gradle
        run: ./gradlew bootJar -x test

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ env.ECS_SERVICE }} \
            --query taskDefinition > task-definition.json

      - name: Fill in the new image ID in the ECS task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ needs.build-and-push.outputs.image }}

      - name: Deploy Amazon ECS task definition
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

Job이 세 개(`test`, `build-and-push`, `deploy`)로 나뉘는 이유가 있다. `needs` 키로 의존 관계를 걸어두면 테스트가 실패하면 이미지를 빌드하지 않고, 이미지 빌드가 실패하면 배포하지 않는다. 실패 원인이 어느 Job인지 Actions 탭에서 바로 보인다.

---

## 트리거 설정

`on` 블록이 파이프라인이 언제 실행될지를 결정한다.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

이 설정으로 동작하는 범위가 다르다.

- `push`(`main`): 테스트 → 빌드 → ECR 푸시 → ECS 배포까지 전체 파이프라인
- `pull_request`(`main`): 테스트 Job만 동작. `build-and-push` Job에 `if: github.ref == 'refs/heads/main' && github.event_name == 'push'` 조건이 있어서 PR에서는 빌드·배포가 생략된다

PR에서도 빌드 산출물을 확인하고 싶다면 `build-and-push` Job의 `if` 조건에서 `event_name` 체크를 제거하고, `deploy` Job에만 조건을 남기면 된다.

브랜치 패턴을 좀 더 정밀하게 쓸 수 있다.

```yaml
on:
  push:
    branches:
      - main
      - 'release/**'
    paths:
      - 'src/**'
      - 'build.gradle'
      - 'Dockerfile'
```

`paths` 필터를 쓰면 문서(`docs/`)만 바꿨을 때 불필요한 빌드가 돌지 않는다. 단, `paths` 필터를 쓰면 해당 경로에 변경이 없는 PR은 Actions 체크 자체가 스킵되므로, GitHub Branch Protection Rule에서 "required status checks"로 등록해두었다면 PR이 블락될 수 있다.

---

## Secrets 주입

AWS 자격증명처럼 코드에 하드코딩하면 안 되는 값은 GitHub Secrets에 등록하고 `${{ secrets.KEY_NAME }}`으로 참조한다.

**등록 위치**: Repository → Settings → Secrets and variables → Actions → New repository secret

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ap-northeast-2
```

Secrets 값은 Actions 로그에서 자동으로 마스킹된다. `echo ${{ secrets.AWS_SECRET_ACCESS_KEY }}`를 실행해도 로그에는 `***`으로 표시된다.

`environment`를 사용하면 환경별로 Secrets를 분리할 수 있다. `production` 환경에만 실제 AWS 자격증명을 넣고, `staging` 환경에는 별도 계정 자격증명을 넣는 식이다.

```yaml
deploy:
  needs: build-and-push
  runs-on: ubuntu-latest
  environment: production   # 이 환경의 Secrets를 사용
```

`environment`에 필요한 Secrets가 없으면 해당 스텝에서 빈 값이 들어가고, AWS SDK가 자격증명을 못 찾아 `No credentials found` 오류를 낸다. Secrets 이름 오타인지 등록된 Secrets 목록을 먼저 확인한다.

---

## Gradle 빌드 캐싱

캐시 설정을 안 하면 매번 Gradle 의존성을 새로 내려받는다. Spring Boot 프로젝트 기준으로 의존성 다운로드에만 1~2분이 걸리는 경우가 있다. 캐시가 히트하면 이 시간이 몇 초로 줄어든다.

```yaml
- name: Cache Gradle packages
  uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
    restore-keys: |
      ${{ runner.os }}-gradle-
```

`key`가 캐시 히트 여부를 결정한다. `hashFiles('**/*.gradle*')`는 `build.gradle`, `settings.gradle` 등 Gradle 설정 파일의 해시값을 포함한다. 의존성이 바뀌면 파일 해시가 달라져서 캐시 미스가 나고, 새로 받은 뒤 캐시를 다시 저장한다.

`restore-keys`는 정확히 일치하는 캐시가 없을 때 prefix로 매칭되는 가장 최근 캐시를 찾는다. `${{ runner.os }}-gradle-`로 시작하는 캐시가 있으면 완전히 새로 내려받는 대신 그 캐시를 복원한 후 변경된 의존성만 추가로 내려받는다.

캐시 크기가 너무 크면 오히려 복원하는 시간이 더 걸린다. `~/.gradle/caches` 디렉토리가 수 GB로 불어나는 경우가 있어서, `~/.gradle/caches/modules-2/files-2.1`만 캐시하는 방식으로 범위를 좁히기도 한다.

---

## Docker 이미지 빌드와 ECR 푸시

ECR에 이미지를 올리려면 ECR 로그인 → 빌드 → 태그 → 푸시 순서로 진행한다.

```yaml
- name: Login to Amazon ECR
  id: login-ecr
  uses: aws-actions/amazon-ecr-login@v2

- name: Build, tag, and push image to ECR
  id: build-image
  env:
    ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
    IMAGE_TAG: ${{ github.sha }}
  run: |
    docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
```

이미지 태그로 `${{ github.sha }}`(커밋 해시)를 쓰는 게 일반적이다. `latest`만 쓰면 어느 커밋으로 배포된 건지 추적이 안 된다. 운영 중에 롤백해야 할 때 이전 태그를 모르면 재배포가 불가능하다.

`echo "image=..." >> $GITHUB_OUTPUT`은 이 스텝의 결과를 후속 Job에서 참조할 수 있게 저장한다. `deploy` Job에서 `${{ needs.build-and-push.outputs.image }}`로 받아서 Task Definition에 넣는다.

ECR 푸시 전에 리포지토리가 없으면 `RepositoryNotFoundException`이 난다. ECR 리포지토리는 배포 파이프라인과 별개로 미리 만들어두거나 Terraform으로 관리한다.

---

## ECS 배포

Task Definition의 이미지 태그를 새 것으로 교체하고 서비스를 업데이트하는 방식이다.

```yaml
- name: Download task definition
  run: |
    aws ecs describe-task-definition \
      --task-definition ${{ env.ECS_SERVICE }} \
      --query taskDefinition > task-definition.json

- name: Fill in the new image ID in the ECS task definition
  id: task-def
  uses: aws-actions/amazon-ecs-render-task-definition@v1
  with:
    task-definition: task-definition.json
    container-name: ${{ env.CONTAINER_NAME }}
    image: ${{ needs.build-and-push.outputs.image }}

- name: Deploy Amazon ECS task definition
  uses: aws-actions/amazon-ecs-deploy-task-definition@v1
  with:
    task-definition: ${{ steps.task-def.outputs.task-definition }}
    service: ${{ env.ECS_SERVICE }}
    cluster: ${{ env.ECS_CLUSTER }}
    wait-for-service-stability: true
```

`wait-for-service-stability: true`를 쓰면 새 Task가 정상적으로 실행될 때까지 Actions가 기다린다. 기본 대기 시간이 30분인데, 앱 시작이 느리면 타임아웃으로 배포 Job이 실패할 수 있다. 실제 배포는 완료된 상황이므로 ECS 콘솔에서 직접 확인해야 한다.

`false`로 바꾸면 Task Definition 등록과 서비스 업데이트 명령만 날리고 바로 완료된다. 배포 성공 여부를 파이프라인에서 확인하고 싶다면 `true`로 두는 게 낫다.

---

## 실패 로그에서 원인 찾기

파이프라인이 실패하면 Actions 탭에서 실패한 Job 이름이 빨간색으로 표시된다. 클릭하면 스텝별 로그가 나온다.

**테스트 실패**

```
> Task :test FAILED

SomethingServiceTest > someMethod_whenCondition_thenExpect() FAILED
    java.lang.AssertionError: expected: <200> but was: <500>
        at SomethingServiceTest.someMethod_whenCondition_thenExpect(SomethingServiceTest.java:42)
```

어느 테스트가 실패했는지 클래스명과 라인 번호가 나온다. 전체 스택 트레이스를 보려면 `Upload test results` 스텝에서 아티팩트를 다운로드한다. `build/reports/tests/test/index.html`을 브라우저에서 열면 실패한 테스트의 상세 내용이 보인다.

**Gradle 빌드 실패**

```
> Task :compileJava FAILED
error: cannot find symbol
  symbol:   class SomeClass
  location: class SomethingService
```

로컬에서는 됐는데 CI에서 실패하는 경우는 대부분 두 가지다. 로컬에 있는데 `.gitignore`에 걸려 커밋이 안 된 파일이 있거나, Lombok 같은 어노테이션 프로세서 설정이 빠진 경우다. Lombok을 쓰면 `build.gradle`에 `annotationProcessor` 의존성이 있어야 한다.

```groovy
dependencies {
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```

**ECR 푸시 실패**

```
Error response from daemon: no basic auth credentials
```

ECR 로그인 스텝이 제대로 됐는지 확인한다. `configure-aws-credentials` 스텝이 실패해도 다음 스텝이 계속 진행되는 경우가 있다. Secrets 이름이 실제 등록된 것과 다르면 AWS 자격증명이 빈 값으로 들어간다.

**ECS 배포 실패**

```
Error: Service was unable to start a task successfully for a sustained period of time.
```

이 메시지만 보면 원인을 알 수 없다. ECS 콘솔 → 클러스터 → 서비스 → Events 탭에서 실제 실패 이유를 확인해야 한다. 대부분 컨테이너가 시작되다 죽는 건데, CloudWatch Logs에서 앱 로그를 보면 실제 에러가 나온다.

---

## 승인 게이트

`production` 같은 중요 환경에 자동으로 배포되는 걸 막으려면 `environment`에 Required Reviewers를 설정한다.

**등록 위치**: Repository → Settings → Environments → production → Required reviewers

승인자를 지정하면 `deploy` Job이 시작되기 전에 승인 대기 상태로 멈춘다. 지정된 사람이 Actions 탭에서 승인해야 배포가 진행된다.

```yaml
deploy:
  needs: build-and-push
  runs-on: ubuntu-latest
  environment: production   # Required reviewers가 설정된 환경
  steps:
    # ...
```

워크플로 YAML에서 추가 설정이 필요 없다. Environment에 설정한 보호 규칙이 자동으로 적용된다.

승인 대기 상태는 최대 30일간 유지된다. 만료되면 재실행해야 한다. 승인이 필요 없는 환경(스테이징 등)은 `environment`를 다른 이름으로 분리하거나 Required Reviewers 없이 환경만 만들어서 Secrets만 분리한다.

---

## PR 단계에서 배포 차단

`build-and-push` Job에 조건을 걸어두면 PR에서는 배포 단계가 실행되지 않는다.

```yaml
build-and-push:
  needs: test
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

PR을 올리면 `test` Job만 돌고 빌드·배포는 건너뛴다. PR 체크로는 테스트 통과만 확인하고, `main`에 머지된 후 실제 배포가 일어나는 흐름이다.

팀에서 feature 브랜치마다 스테이징 환경에 자동 배포하고 싶다면 조건을 바꾼다.

```yaml
build-and-push:
  needs: test
  if: |
    (github.ref == 'refs/heads/main' && github.event_name == 'push') ||
    (github.event_name == 'pull_request')

deploy-staging:
  needs: build-and-push
  if: github.event_name == 'pull_request'
  environment: staging

deploy-production:
  needs: build-and-push
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  environment: production
```

이렇게 나누면 PR은 스테이징으로, `main` Push는 프로덕션으로 각각 배포된다.
