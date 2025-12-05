---
title: Bitbucket Pipelines 가이드
tags: [devops, cicd, bitbucket, pipeline, automation, deployment]
updated: 2025-12-05
---

# Bitbucket Pipelines

## 정의

Bitbucket Pipelines는 Atlassian에서 제공하는 클라우드 기반 CI/CD 서비스입니다. Git 저장소와 통합되어 코드 변경사항을 자동으로 빌드, 테스트, 배포할 수 있습니다.

Bitbucket Cloud 저장소에서만 사용 가능하고, Bitbucket Server나 Data Center에서는 사용할 수 없다. Self-hosted runner도 지원하지 않아서 모든 빌드는 Atlassian의 클라우드 환경에서 실행된다.

### 주요 특징
- Docker 기반의 격리된 환경: 각 step은 독립적인 Docker 컨테이너에서 실행된다. 같은 파이프라인 내에서도 step 간에는 파일 시스템이 공유되지 않는다. 아티팩트를 사용해서 파일을 전달해야 한다.
- YAML 기반 설정: bitbucket-pipelines.yml 파일을 저장소 루트에 두면 자동으로 인식한다. 브랜치별로 다른 설정을 사용할 수 있다.
- Git과의 완벽한 통합: 커밋, 브랜치, PR 정보를 환경 변수로 사용할 수 있다. $BITBUCKET_COMMIT, $BITBUCKET_BRANCH, $BITBUCKET_PR_ID 등.
- 병렬 빌드 지원: parallel 블록을 사용해서 여러 step을 동시에 실행할 수 있다. 하지만 무료 플랜에서는 동시 실행 시간이 제한된다.

## 기본 구성

### 파이프라인 구조

```yaml
# bitbucket-pipelines.yml
image: node:18

definitions:
  caches:
    npm: ~/.npm
  steps:
    - step: &build-test
        name: Build and Test
        caches:
          - npm
        script:
          - npm ci
          - npm run build
          - npm run test
        artifacts:
          - dist/**

pipelines:
  default:
    - step: *build-test
  
  branches:
    develop:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - npm run deploy:staging
    
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          script:
            - npm run deploy:production
  
  pull-requests:
    '**':
      - step: *build-test
```

### YAML 앵커와 별칭

YAML 앵커(`&`)와 별칭(`*`)을 사용하면 공통 step을 재사용할 수 있다. 여러 브랜치에서 같은 빌드 step을 사용할 때 유용하다. 하지만 앵커는 definitions 안에서만 정의할 수 있고, pipelines 안에서는 사용할 수 없다.

### 이미지 버전 고정

`image: node:18`처럼 태그만 지정하면 항상 최신 18.x 버전을 사용한다. 특정 버전을 고정하려면 `node:18.17.0`처럼 전체 버전을 지정해야 한다. 프로덕션에서는 버전을 고정하는 것이 안전하다.

### 스크립트 실행 방식

script는 배열로 여러 명령을 나열할 수 있다. 각 명령은 별도의 쉘에서 실행되므로 환경 변수나 디렉토리 변경이 다음 명령에 영향을 주지 않는다. 같은 step 내에서 상태를 유지하려면 하나의 문자열로 합치거나, 파일로 만들어서 실행해야 한다.

```yaml
script:
  - |
    cd backend
    npm ci
    npm run build
    npm run test
```

## 언어별 예제

### Node.js

```yaml
image: node:18

pipelines:
  default:
    - step:
        name: Build and Test
        caches:
          - npm
        script:
          - npm ci
          - npm run lint
          - npm run build
          - npm test
        artifacts:
          - dist/**
```

npm ci는 package-lock.json을 기반으로 정확한 버전을 설치한다. npm install보다 빠르고 재현 가능하다. 프로덕션 빌드에서는 npm ci를 사용하는 것이 좋다.

### Java (Maven)

```yaml
image: maven:3.8-openjdk-17

pipelines:
  default:
    - step:
        name: Build and Test
        caches:
          - maven
        script:
          - mvn clean install -DskipTests
          - mvn test
        artifacts:
          - target/**
```

Maven은 기본적으로 테스트를 실행하면서 컴파일한다. `-DskipTests`로 테스트 실행은 건너뛰고 컴파일만 하거나, `-Dmaven.test.skip=true`로 테스트 컴파일 자체를 건너뛸 수 있다. 빌드와 테스트를 분리하면 테스트 실패 시 빌드 결과물은 얻을 수 있다.

### Python

```yaml
image: python:3.11

pipelines:
  default:
    - step:
        name: Build and Test
        caches:
          - pip
        script:
          - pip install -r requirements.txt
          - pytest tests/
          - flake8 src/
```

pip 캐시는 기본적으로 제공되지만, 가상환경을 사용하는 경우 캐시가 제대로 작동하지 않을 수 있다. requirements.txt에 버전을 명시하지 않으면 최신 버전을 설치해서 빌드가 불안정해질 수 있다.

### Docker Compose와 함께 사용

로컬 개발 환경과 동일하게 Docker Compose를 사용하는 경우:

```yaml
image: docker:latest

pipelines:
  default:
    - step:
        name: Test with Docker Compose
        services:
          - docker
        script:
          - apk add --no-cache docker-compose
          - docker-compose up -d
          - docker-compose exec -T app npm test
          - docker-compose down
```

services에 docker를 추가하면 Docker-in-Docker가 가능하다. docker-compose는 기본 이미지에 포함되어 있지 않아서 별도로 설치해야 한다.

## 고급 기능

### 병렬 실행

```yaml
pipelines:
  default:
    - parallel:
        - step:
            name: Unit Tests
            script:
              - npm run test:unit
        - step:
            name: Integration Tests
            script:
              - npm run test:integration
        - step:
            name: E2E Tests
            script:
              - npm run test:e2e
```

병렬 실행은 시간을 단축시킬 수 있지만, 각 step이 독립적으로 실행되므로 아티팩트를 공유할 수 없다. 빌드 step의 결과물을 여러 테스트 step에서 사용하려면 빌드를 먼저 실행하고, 그 결과물을 병렬 테스트에서 사용해야 한다.

```yaml
pipelines:
  default:
    - step:
        name: Build
        script:
          - npm run build
        artifacts:
          - dist/**
    - parallel:
        - step:
            name: Unit Tests
            script:
              - npm run test:unit
        - step:
            name: Integration Tests
            script:
              - npm run test:integration
```

### 조건부 실행

```yaml
pipelines:
  default:
    - step:
        name: Build
        script:
          - npm run build
        condition:
          changesets:
            includePaths:
              - "src/**"
              - "package.json"
```

조건부 실행은 해당 경로의 파일이 변경되었을 때만 step을 실행한다. 하지만 PR의 경우 base 브랜치와 비교하기 때문에, 이미 머지된 변경사항은 감지하지 못할 수 있다. 모든 브랜치에서 실행되도록 하는 것이 더 안전할 수도 있다.

excludePaths로 특정 경로를 제외할 수도 있다. 문서나 설정 파일만 변경된 경우 빌드를 건너뛸 수 있다.

```yaml
condition:
  changesets:
    excludePaths:
      - "docs/**"
      - "*.md"
```

### Docker 이미지 빌드

```yaml
pipelines:
  default:
    - step:
        name: Build Docker Image
        services:
          - docker
        script:
          - docker build -t myapp:$BITBUCKET_COMMIT .
          - docker push myapp:$BITBUCKET_COMMIT
```

Docker 이미지를 빌드하고 푸시할 때는 인증이 필요하다. Docker Hub나 ECR, GCR 등에 푸시하려면 로그인해야 한다. 환경 변수에 자격증명을 저장하고 사용한다.

```yaml
script:
  - echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
  - docker build -t myapp:$BITBUCKET_COMMIT .
  - docker push myapp:$BITBUCKET_COMMIT
```

ECR의 경우 AWS CLI를 사용해서 로그인한다.

```yaml
script:
  - apk add --no-cache aws-cli
  - $(aws ecr get-login --no-include-email --region ap-northeast-2)
  - docker build -t $ECR_REPO:$BITBUCKET_COMMIT .
  - docker push $ECR_REPO:$BITBUCKET_COMMIT
```

### 커스텀 서비스

MySQL, Redis 같은 서비스를 step에서 사용할 수 있다. services 섹션에 추가하면 해당 step에서 접근 가능하다.

```yaml
pipelines:
  default:
    - step:
        name: Integration Tests
        services:
          - postgres
          - redis
        script:
          - npm run test:integration
        variables:
          POSTGRES_HOST: postgres
          POSTGRES_PORT: 5432
          REDIS_HOST: redis
          REDIS_PORT: 6379
```

서비스 이름은 호스트명으로 사용된다. 포트는 기본 포트를 사용하거나, variables로 설정할 수 있다. 하지만 서비스의 환경 변수는 제한적이어서, 복잡한 설정이 필요하면 docker-compose를 사용하는 것이 낫다.

## 환경 변수 관리

### 시크릿 사용

Bitbucket 설정 > Repository variables에서 설정:

```yaml
pipelines:
  default:
    - step:
        name: Deploy
        script:
          - echo $DATABASE_URL
          - echo $API_KEY
          - npm run deploy
```

환경 변수는 Repository variables와 Deployment variables 두 가지가 있다. Repository variables는 모든 파이프라인에서 접근 가능하고, Deployment variables는 특정 환경(스테이징, 프로덕션 등)에만 적용된다. 민감한 정보는 반드시 Secured로 설정해야 한다.

Deployment variables는 환경별로 다른 값을 설정할 수 있어서 유용하다. 예를 들어 스테이징은 테스트 DB를, 프로덕션은 실제 DB를 가리키도록 할 수 있다.

### 기본 제공 환경 변수

Bitbucket Pipelines는 자동으로 여러 환경 변수를 제공한다:

- `$BITBUCKET_COMMIT`: 현재 커밋 해시
- `$BITBUCKET_BRANCH`: 현재 브랜치 이름
- `$BITBUCKET_TAG`: 태그 이름 (태그가 있는 경우)
- `$BITBUCKET_PR_ID`: PR 번호 (PR인 경우)
- `$BITBUCKET_REPO_SLUG`: 저장소 이름
- `$BITBUCKET_REPO_OWNER`: 저장소 소유자
- `$BITBUCKET_BUILD_NUMBER`: 빌드 번호

이 변수들을 사용해서 Docker 이미지 태그나 배포 버전을 만들 수 있다.

```yaml
script:
  - docker build -t myapp:$BITBUCKET_COMMIT .
  - docker tag myapp:$BITBUCKET_COMMIT myapp:$BITBUCKET_BRANCH
```

### step별 환경 변수

각 step에서 variables를 설정하면 해당 step에서만 사용할 수 있다. 다른 step과 격리되어 있다.

```yaml
pipelines:
  default:
    - step:
        name: Build
        variables:
          NODE_ENV: production
        script:
          - npm run build
```

하지만 같은 step 내의 여러 명령어 간에는 환경 변수가 공유된다.

## 실제 사용 시 주의사항

### 타임아웃 처리

기본적으로 각 step은 10분 타임아웃이 있다. 긴 작업을 수행할 때는 명시적으로 타임아웃을 늘려야 한다.

```yaml
pipelines:
  default:
    - step:
        name: Long Running Test
        max-time: 30
        script:
          - npm run test:integration
```

### 캐시 무효화

캐시가 잘못된 경우가 종종 있다. 특히 package.json이나 requirements.txt가 변경되었는데도 이전 캐시를 사용하는 경우. 이런 경우 캐시 키에 파일 해시를 포함시키는 것이 좋다.

```yaml
definitions:
  caches:
    npm: 
      key:
        files:
          - package-lock.json
```

### Docker 레이어 캐싱

Docker 이미지를 빌드할 때 레이어 캐싱을 활용하면 빌드 시간을 크게 줄일 수 있다.

```yaml
pipelines:
  default:
    - step:
        name: Build Docker Image
        services:
          - docker
        caches:
          - docker
        script:
          - docker build --cache-from myapp:latest -t myapp:$BITBUCKET_COMMIT .
          - docker tag myapp:$BITBUCKET_COMMIT myapp:latest
          - docker push myapp:$BITBUCKET_COMMIT
          - docker push myapp:latest
```

### 아티팩트 크기 제한

아티팩트는 최대 1GB까지 저장 가능하다. 큰 파일을 저장하면 다음 step으로 전달하는데 시간이 오래 걸린다. 필요한 파일만 저장하고, 큰 파일은 S3나 다른 스토리지에 업로드하는 것이 좋다.

```yaml
artifacts:
  - dist/**/*.js
  - dist/**/*.css
  # node_modules는 제외
```

### 병렬 실행 시 리소스 경쟁

병렬로 여러 step을 실행할 때 같은 리소스(DB, 외부 API 등)에 동시에 접근하면 문제가 생길 수 있다. 테스트 환경을 격리하거나 순차 실행을 고려해야 한다.

```yaml
pipelines:
  default:
    - step:
        name: Setup Test DB
        script:
          - docker-compose up -d postgres
          - npm run migrate
    - parallel:
        - step:
            name: Unit Tests
            script:
              - npm run test:unit
        - step:
            name: Integration Tests
            script:
              - npm run test:integration
```

## 디버깅

### 로그 확인

파이프라인이 실패하면 로그를 자세히 봐야 한다. 특히 스크립트에서 에러가 발생했는데 exit code가 0이면 파이프라인은 성공으로 표시되지만 실제로는 실패한 경우가 있다. `set -e`를 사용하면 명령이 실패하면 즉시 중단된다.

```yaml
script:
  - set -e
  - npm ci
  - npm run build
```

### 로컬에서 테스트

bitbucket-pipelines-runner를 사용하면 로컬에서 파이프라인을 실행해볼 수 있다. 하지만 완전히 동일한 환경은 아니므로 주의해야 한다.

```bash
docker run --rm -v $(pwd):/workspace -w /workspace atlassian/default-image:latest /bin/sh -c "npm ci && npm test"
```

### 환경 변수 확인

디버깅할 때 환경 변수가 제대로 전달되는지 확인해야 한다. 하지만 민감한 정보는 로그에 출력하지 않도록 주의해야 한다.

```yaml
script:
  - echo "DB_HOST is set: $([ -n "$DB_HOST" ] && echo 'yes' || echo 'no')"
  # 실제 값은 출력하지 않음
```

## 성능 최적화

### 불필요한 step 건너뛰기

변경된 파일에 따라 다른 step을 실행하도록 하면 불필요한 빌드를 줄일 수 있다.

```yaml
pipelines:
  default:
    - step:
        name: Build Frontend
        condition:
          changesets:
            includePaths:
              - "frontend/**"
        script:
          - cd frontend && npm ci && npm run build
    - step:
        name: Build Backend
        condition:
          changesets:
            includePaths:
              - "backend/**"
        script:
          - cd backend && npm ci && npm run build
```

### 캐시 전략

npm, maven, pip 등 패키지 매니저 캐시는 기본 제공되지만, 커스텀 캐시도 만들 수 있다. 빌드 결과물을 캐시하면 다음 빌드에서 재사용할 수 있다.

```yaml
definitions:
  caches:
    custom-build: .build-cache

pipelines:
  default:
    - step:
        caches:
          - custom-build
        script:
          - if [ -d .build-cache ]; then cp -r .build-cache/node_modules .; fi
          - npm ci
          - npm run build
          - mkdir -p .build-cache && cp -r node_modules .build-cache/
```

### 이미지 선택

가벼운 이미지를 사용하면 빌드 시작 시간이 빨라진다. node:18-alpine 같은 alpine 이미지가 일반 이미지보다 작다. 하지만 alpine은 glibc 대신 musl을 사용해서 네이티브 모듈 빌드 시 문제가 생길 수 있다.

## 비용 관리

무료 플랜은 월 2,500분이 제공된다. 1분 단위로 과금되므로 불필요한 빌드를 줄이는 것이 중요하다. PR마다 자동으로 빌드가 실행되도록 설정하면 비용이 빠르게 증가한다.

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Quick Check
          script:
            - npm run lint
            - npm run test:unit
          # 전체 빌드는 PR 머지 후에만
```

또는 특정 브랜치나 태그에만 파이프라인을 실행하도록 제한할 수 있다.

```yaml
pipelines:
  branches:
    develop:
      - step: *build-test
    main:
      - step: *build-test
      - step: *deploy-prod
  # 다른 브랜치는 파이프라인 실행 안 함
```

## 실제 배포 패턴

### Blue-Green 배포

Blue-Green 배포를 구현하려면 두 개의 환경을 준비하고 트래픽을 전환해야 한다. Bitbucket Pipelines에서는 step을 순차적으로 실행해서 배포를 제어할 수 있다.

```yaml
pipelines:
  branches:
    main:
      - step:
          name: Build
          script:
            - docker build -t myapp:$BITBUCKET_COMMIT .
            - docker push myapp:$BITBUCKET_COMMIT
      - step:
          name: Deploy to Blue
          deployment: production-blue
          script:
            - kubectl set image deployment/myapp app=myapp:$BITBUCKET_COMMIT -n blue
            - kubectl rollout status deployment/myapp -n blue
      - step:
          name: Smoke Test
          script:
            - ./scripts/smoke-test.sh blue.example.com
      - step:
          name: Switch Traffic to Blue
          deployment: production
          script:
            - kubectl patch service/myapp -p '{"spec":{"selector":{"version":"blue"}}}'
```

### 롤백 처리

배포 후 문제가 발견되면 롤백해야 한다. 이전 버전의 이미지 태그를 저장해두거나, Git 태그를 사용해서 롤백할 수 있다.

```yaml
pipelines:
  branches:
    main:
      - step:
          name: Build and Tag
          script:
            - docker build -t myapp:$BITBUCKET_COMMIT .
            - docker tag myapp:$BITBUCKET_COMMIT myapp:latest
            - docker push myapp:$BITBUCKET_COMMIT
            - docker push myapp:latest
            - echo $BITBUCKET_COMMIT > .last-deployed-commit
          artifacts:
            - .last-deployed-commit
```

### 데이터베이스 마이그레이션

데이터베이스 마이그레이션은 배포 전에 실행해야 한다. 마이그레이션 실패 시 배포를 중단해야 한다.

```yaml
pipelines:
  branches:
    main:
      - step:
          name: Run Migrations
          deployment: production
          script:
            - npm run migrate:up
            - if [ $? -ne 0 ]; then exit 1; fi
      - step:
          name: Deploy Application
          deployment: production
          script:
            - npm run deploy
```

## 알림 설정

파이프라인 실패 시 슬랙이나 이메일로 알림을 받을 수 있다. Bitbucket의 기본 알림 설정을 사용하거나, step에서 직접 웹훅을 호출할 수 있다.

```yaml
pipelines:
  branches:
    main:
      - step:
          name: Deploy
          script:
            - npm run deploy
            - |
              if [ $? -eq 0 ]; then
                curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"Deployment succeeded"}'
              else
                curl -X POST $SLACK_WEBHOOK_URL -d '{"text":"Deployment failed"}'
                exit 1
              fi
```

## 트러블슈팅

### 빌드가 갑자기 실패하는 경우

이전에는 성공했던 빌드가 갑자기 실패하는 경우가 있다. 대부분 의존성 버전 문제나 외부 서비스 장애 때문이다. package-lock.json을 커밋하고, 외부 의존성은 버전을 고정하는 것이 좋다.

### 메모리 부족

큰 프로젝트를 빌드할 때 메모리 부족으로 실패하는 경우가 있다. Node.js의 경우 `NODE_OPTIONS=--max-old-space-size=4096`을 설정해서 힙 메모리를 늘릴 수 있다.

```yaml
script:
  - export NODE_OPTIONS=--max-old-space-size=4096
  - npm run build
```

### 네트워크 타임아웃

npm install이나 pip install 중에 네트워크 타임아웃이 발생할 수 있다. 재시도 로직을 추가하거나, 타임아웃을 늘려야 한다.

```yaml
script:
  - npm ci --prefer-offline --no-audit || npm ci --prefer-offline --no-audit
```

### 파일 권한 문제

스크립트를 실행할 때 실행 권한이 없어서 실패하는 경우가 있다. chmod로 권한을 부여하거나, 명시적으로 쉘로 실행해야 한다.

```yaml
script:
  - chmod +x scripts/deploy.sh
  - ./scripts/deploy.sh
  # 또는
  - sh scripts/deploy.sh
```

### Git 서브모듈

Git 서브모듈을 사용하는 경우, 기본적으로 체크아웃되지 않는다. 명시적으로 초기화하고 업데이트해야 한다.

```yaml
script:
  - git submodule update --init --recursive
```

### 큰 파일 처리

아티팩트로 큰 파일을 전달하면 시간이 오래 걸린다. 압축해서 전달하거나, S3 같은 외부 스토리지에 업로드하는 것이 좋다.

```yaml
script:
  - tar czf build.tar.gz dist/
  - aws s3 cp build.tar.gz s3://my-bucket/builds/$BITBUCKET_COMMIT.tar.gz
artifacts:
  - build.tar.gz
```

### 의존성 설치 실패

의존성 설치가 간헐적으로 실패하는 경우가 있다. 네트워크 문제나 레지스트리 장애 때문일 수 있다. 재시도 로직을 추가하거나, 다른 레지스트리를 사용할 수 있다.

```yaml
script:
  - npm config set registry https://registry.npmjs.org/
  - npm ci || (sleep 5 && npm ci)
```

### 환경별 설정 파일

환경별로 다른 설정 파일을 사용해야 하는 경우, step에서 파일을 복사하거나 심볼릭 링크를 만들어야 한다.

```yaml
script:
  - cp config/$BITBUCKET_DEPLOYMENT_ENVIRONMENT.json config.json
  - npm run build
```

또는 환경 변수로 설정을 주입할 수도 있다.

```yaml
script:
  - echo "{\"apiUrl\":\"$API_URL\"}" > config.json
  - npm run build
```

## 참고

### CI/CD 도구 비교

| 항목 | Bitbucket Pipelines | GitHub Actions | GitLab CI |
|------|-------------------|----------------|-----------|
| 통합 | Bitbucket | GitHub | GitLab |
| 무료 크레딧 | 2,500분/월 | 2,000분/월 | 400분/월 |
| Docker 지원 | 네이티브 | 네이티브 | 네이티브 |
| Self-hosted | 불가능 | 가능 | 가능 |

### 관련 문서
- [Bitbucket Pipelines Documentation](https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/)
- [YAML Configuration Reference](https://support.atlassian.com/bitbucket-cloud/docs/configure-bitbucket-pipelinesyml/)
