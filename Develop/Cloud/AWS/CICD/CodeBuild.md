---
title: AWS CodeBuild
tags: [aws, codebuild, build, docker, ci, test, compile]
updated: 2026-01-18
---

# AWS CodeBuild

## 개요

CodeBuild는 빌드 서비스다. 소스 코드를 컴파일하고 테스트한다. Docker 이미지를 만든다. 서버 관리가 필요 없다. 빌드할 때만 비용을 낸다. 병렬 빌드를 지원한다.

### 왜 필요한가

Jenkins는 서버 관리가 필요하다.

**문제 상황:**

**Jenkins 운영:**
- EC2 인스턴스 관리
- 플러그인 업데이트
- 디스크 용량 관리
- 빌드 에이전트 확장
- 보안 패치

시간과 비용이 든다.

**CodeBuild의 해결:**
- 서버리스
- 자동 스케일링
- 사용한 시간만 과금
- AWS 서비스와 통합

## buildspec.yml

빌드 명령을 정의한다. 프로젝트 루트에 위치한다.

### 기본 구조

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
    commands:
      - npm install -g yarn
  pre_build:
    commands:
      - echo Installing dependencies...
      - yarn install
  build:
    commands:
      - echo Build started on `date`
      - yarn build
  post_build:
    commands:
      - echo Build completed on `date`

artifacts:
  files:
    - '**/*'
  base-directory: dist

cache:
  paths:
    - 'node_modules/**/*'
```

### Phases (단계)

**install:**
런타임과 도구를 설치한다.

```yaml
phases:
  install:
    runtime-versions:
      python: 3.11
      nodejs: 18
    commands:
      - pip install awscli
      - npm install -g typescript
```

**pre_build:**
빌드 전 준비 작업.

```yaml
pre_build:
  commands:
    - echo Logging in to Docker Hub...
    - docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
```

**build:**
실제 빌드.

```yaml
build:
  commands:
    - mvn clean package
    - docker build -t my-app .
```

**post_build:**
빌드 후 정리.

```yaml
post_build:
  commands:
    - echo Pushing Docker image...
    - docker push my-registry/my-app:latest
```

### Artifacts

빌드 결과물을 정의한다. S3에 업로드된다.

```yaml
artifacts:
  files:
    - target/my-app.jar
    - Dockerfile
  name: MyAppBuild
  discard-paths: yes
```

**여러 Artifact:**
```yaml
artifacts:
  secondary-artifacts:
    artifact1:
      files:
        - target/*.jar
      name: JavaApp
    artifact2:
      files:
        - dist/**/*
      name: FrontendApp
```

### Cache

의존성을 캐시한다. 빌드 시간을 단축한다.

```yaml
cache:
  paths:
    - '/root/.m2/**/*'       # Maven
    - '/root/.gradle/**/*'   # Gradle
    - 'node_modules/**/*'    # npm
```

**로컬 캐시:**
```yaml
cache:
  paths:
    - 'node_modules/**/*'
```

**S3 캐시:**
CodeBuild 프로젝트 설정에서 S3 버킷 지정.

## 실무 buildspec

### Node.js 앱 빌드

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
  pre_build:
    commands:
      - echo Installing dependencies...
      - npm ci
  build:
    commands:
      - echo Running tests...
      - npm test
      - echo Building application...
      - npm run build
  post_build:
    commands:
      - echo Build completed

artifacts:
  files:
    - '**/*'
  base-directory: dist

cache:
  paths:
    - 'node_modules/**/*'
```

### Docker 이미지 빌드 + ECR 푸시

```yaml
version: 0.2

env:
  variables:
    AWS_REGION: us-west-2
    ECR_REGISTRY: 123456789012.dkr.ecr.us-west-2.amazonaws.com
    IMAGE_REPO: my-app

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
  build:
    commands:
      - echo Building Docker image...
      - docker build -t $ECR_REGISTRY/$IMAGE_REPO:$IMAGE_TAG .
      - docker tag $ECR_REGISTRY/$IMAGE_REPO:$IMAGE_TAG $ECR_REGISTRY/$IMAGE_REPO:latest
  post_build:
    commands:
      - echo Pushing Docker image...
      - docker push $ECR_REGISTRY/$IMAGE_REPO:$IMAGE_TAG
      - docker push $ECR_REGISTRY/$IMAGE_REPO:latest
      - printf '[{"name":"my-container","imageUri":"%s"}]' $ECR_REGISTRY/$IMAGE_REPO:$IMAGE_TAG > imagedefinitions.json

artifacts:
  files:
    - imagedefinitions.json
```

### Java Maven 빌드

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      java: corretto17
  pre_build:
    commands:
      - echo Running unit tests...
      - mvn test
  build:
    commands:
      - echo Building JAR file...
      - mvn clean package -DskipTests
  post_build:
    commands:
      - echo Build completed
      - mv target/*.jar app.jar

artifacts:
  files:
    - app.jar
    - Dockerfile
    - appspec.yml

cache:
  paths:
    - '/root/.m2/**/*'
```

### Python Lambda 함수

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.11
  build:
    commands:
      - echo Installing dependencies...
      - pip install -r requirements.txt -t .
      - echo Packaging Lambda function...
      - zip -r function.zip .

artifacts:
  files:
    - function.zip
```

### 멀티스테이지 빌드

```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
  pre_build:
    commands:
      # 프론트엔드 빌드
      - cd frontend
      - npm ci
      - npm run build
      - cd ..
      # 백엔드 빌드
      - cd backend
      - npm ci
      - npm run build
      - cd ..
  build:
    commands:
      # Docker 이미지 빌드
      - docker build -t my-app .
  post_build:
    commands:
      - docker push my-registry/my-app:latest

artifacts:
  files:
    - imagedefinitions.json
```

## 환경 변수

### 기본 환경 변수

CodeBuild가 자동으로 제공한다.

**자주 사용:**
- `CODEBUILD_BUILD_ID`: 빌드 ID
- `CODEBUILD_BUILD_NUMBER`: 빌드 번호
- `CODEBUILD_SOURCE_VERSION`: Git 커밋 해시
- `CODEBUILD_SOURCE_REPO_URL`: Git 저장소 URL
- `CODEBUILD_RESOLVED_SOURCE_VERSION`: 전체 커밋 해시

**예시:**
```yaml
build:
  commands:
    - echo Build Number: $CODEBUILD_BUILD_NUMBER
    - echo Commit: $CODEBUILD_SOURCE_VERSION
    - docker build -t my-app:$CODEBUILD_BUILD_NUMBER .
```

### 커스텀 환경 변수

**buildspec에서 정의:**
```yaml
env:
  variables:
    NODE_ENV: production
    API_URL: https://api.example.com
  parameter-store:
    DB_PASSWORD: /prod/db/password
  secrets-manager:
    API_KEY: prod/api:key
```

**Parameter Store:**
```bash
aws ssm put-parameter \
  --name /prod/db/password \
  --value "my-secret-password" \
  --type SecureString
```

**Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name prod/api \
  --secret-string '{"key":"my-api-key-12345"}'
```

**사용:**
```yaml
build:
  commands:
    - echo Connecting to database...
    - psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PASSWORD
```

## 프로젝트 생성

### 콘솔

1. CodeBuild 콘솔
2. "Create project"
3. 이름: my-app-build
4. Source provider: GitHub
5. Repository: my-org/my-app
6. Environment:
   - Image: aws/codebuild/standard:7.0
   - OS: Ubuntu
   - Runtime: Standard
   - Compute: 3 GB RAM, 2 vCPU
7. Service role: 새로 생성
8. Buildspec: buildspec.yml 사용
9. Artifacts: S3 또는 No artifacts
10. 생성

### CLI

```bash
aws codebuild create-project \
  --name my-app-build \
  --source type=GITHUB,location=https://github.com/my-org/my-app.git \
  --artifacts type=S3,location=my-build-bucket \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL \
  --service-role arn:aws:iam::123456789012:role/codebuild-service-role
```

### CloudFormation

```yaml
Resources:
  BuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Name: my-app-build
      ServiceRole: !GetAtt BuildRole.Arn
      Artifacts:
        Type: S3
        Location: !Ref ArtifactBucket
      Environment:
        Type: LINUX_CONTAINER
        ComputeType: BUILD_GENERAL1_SMALL
        Image: aws/codebuild/standard:7.0
        PrivilegedMode: true  # Docker 빌드 시 필요
        EnvironmentVariables:
          - Name: AWS_REGION
            Value: !Ref AWS::Region
          - Name: ECR_REGISTRY
            Value: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com
      Source:
        Type: GITHUB
        Location: https://github.com/my-org/my-app.git
        BuildSpec: buildspec.yml
```

## 컴퓨팅 타입

### 선택 가이드

| 타입 | vCPU | RAM | 디스크 | 가격/분 | 사용 |
|------|------|-----|--------|---------|------|
| SMALL | 2 | 3 GB | 50 GB | $0.005 | 작은 프로젝트 |
| MEDIUM | 4 | 7 GB | 100 GB | $0.01 | 일반 프로젝트 |
| LARGE | 8 | 15 GB | 150 GB | $0.02 | 큰 프로젝트 |
| 2X_LARGE | 72 | 145 GB | 824 GB | $0.10 | 매우 큰 프로젝트 |

**선택 기준:**
- Node.js, Python: SMALL
- Java, .NET: MEDIUM
- Docker 멀티스테이지: MEDIUM-LARGE
- 대규모 테스트: LARGE

### ARM vs x86

**ARM (Graviton2):**
- 저렴 (약 20% 절감)
- 성능 유사
- 일부 도구 미지원

**x86:**
- 호환성 좋음
- 모든 도구 지원

**선택:**
호환성 문제 없으면 ARM 추천.

## 로컬 테스트

CodeBuild 로컬 에이전트로 테스트한다.

**설치:**
```bash
docker pull public.ecr.aws/codebuild/local-builds:latest
```

**실행:**
```bash
./codebuild_build.sh \
  -i aws/codebuild/standard:7.0 \
  -a /tmp/artifacts \
  -s $(pwd) \
  -b buildspec.yml
```

로컬에서 빌드를 테스트한다. 실패 원인을 빠르게 파악한다.

## VPC 연동

프라이빗 서브넷의 리소스에 접근한다.

**사용 사례:**
- RDS 접근 (테스트 DB)
- ElastiCache 접근
- 프라이빗 ECR

**설정:**
```yaml
VpcConfig:
  VpcId: vpc-12345678
  Subnets:
    - subnet-11111111
    - subnet-22222222
  SecurityGroupIds:
    - sg-12345678
```

**보안 그룹:**
```
Outbound:
- Type: All traffic
- Destination: 0.0.0.0/0
```

**주의:**
VPC 연동 시 빌드 시작 시간이 증가한다 (수십 초).

## 병렬 빌드

여러 브랜치를 동시에 빌드한다.

**Batch Build:**
```yaml
batch:
  fast-fail: true
  build-list:
    - identifier: test
      buildspec: buildspec-test.yml
    - identifier: lint
      buildspec: buildspec-lint.yml
    - identifier: build
      buildspec: buildspec-build.yml
      depend-on:
        - test
        - lint
```

**동작:**
1. test와 lint 병렬 실행
2. 둘 다 성공하면 build 실행
3. 하나라도 실패하면 중단 (fast-fail)

## 비용

### 기본 요금

**리눅스 (x86):**
- SMALL: $0.005/분
- MEDIUM: $0.01/분
- LARGE: $0.02/분

**리눅스 (ARM):**
- SMALL: $0.004/분 (20% 저렴)
- MEDIUM: $0.008/분
- LARGE: $0.016/분

### 계산 예시

**Node.js 앱 (SMALL, 5분):**
- 빌드 1회: 5 × $0.005 = $0.025
- 하루 10회: 10 × $0.025 = $0.25
- 월 (20일): 20 × $0.25 = $5

**Java 앱 (MEDIUM, 10분):**
- 빌드 1회: 10 × $0.01 = $0.10
- 하루 5회: 5 × $0.10 = $0.50
- 월 (20일): 20 × $0.50 = $10

### 최적화

**캐시 활용:**
```yaml
cache:
  paths:
    - 'node_modules/**/*'
    - '/root/.m2/**/*'
```

빌드 시간: 10분 → 3분 (70% 단축)

**작은 컴퓨팅 타입:**
MEDIUM → SMALL로 변경.
비용: $0.01/분 → $0.005/분 (50% 절감)

**ARM 사용:**
x86 → ARM.
비용: $0.005/분 → $0.004/분 (20% 절감)

## GitHub Actions와 비교

### GitHub Actions

**장점:**
- 무료 티어 많음 (Public 무제한, Private 2,000분)
- 설정 간단 (YAML 파일)
- Marketplace 액션 풍부

**단점:**
- AWS 통합 수동
- 긴 빌드는 비쌈 ($0.008/분, Private)

### CodeBuild

**장점:**
- AWS 서비스 네이티브 통합
- IAM 권한 관리
- VPC 접근 간편

**단점:**
- 무료 티어 없음
- 짧은 빌드도 과금

### 선택 가이드

**GitHub Actions:**
- Public 프로젝트
- 짧은 빌드 (< 10분)
- AWS 외 서비스 사용

**CodeBuild:**
- Private 프로젝트 (빌드 많음)
- AWS 서비스만 사용
- VPC 내 리소스 접근

## 참고

- CodeBuild 개발자 가이드: https://docs.aws.amazon.com/codebuild/
- buildspec 레퍼런스: https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html
- CodeBuild 요금: https://aws.amazon.com/codebuild/pricing/
- 로컬 빌드: https://github.com/aws/aws-codebuild-docker-images

