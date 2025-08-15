---
title: Bitbucket Pipelines 완벽 가이드
tags: [devops, cicd, bitbucket, pipeline, automation, deployment]
updated: 2025-08-15
---

# Bitbucket Pipelines

## 배경

Bitbucket Pipelines는 Atlassian에서 제공하는 클라우드 기반 CI/CD 서비스입니다. Git 저장소와 통합되어 코드 변경사항을 자동으로 빌드, 테스트, 배포할 수 있으며, Docker 기반의 격리된 환경에서 안전하고 일관된 빌드 프로세스를 제공합니다.

### Bitbucket Pipelines의 필요성
- **자동화**: 수동 빌드/배포 과정의 자동화로 개발 효율성 향상
- **품질 보장**: 코드 변경 시 자동 테스트 실행으로 품질 관리
- **빠른 피드백**: 개발자에게 즉각적인 피드백 제공
- **일관성**: 모든 환경에서 동일한 빌드 프로세스 보장
- **통합**: Bitbucket과의 완벽한 통합으로 개발 워크플로우 최적화

### 기본 개념
- **파이프라인**: 전체 CI/CD 프로세스를 정의하는 최상위 개념
- **스텝**: 파이프라인의 개별 작업 단위
- **스크립트**: 각 스텝에서 실행되는 명령어들
- **아티팩트**: 빌드 결과물로 다음 스텝에서 사용
- **캐시**: 빌드 속도 향상을 위한 의존성 캐싱

## 핵심

### 1. 파이프라인 구성요소

#### 기본 파이프라인 구조
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
            - echo "Deploying to staging environment"
  pull-requests:
    '**':
      - step: *build-test
```

#### 파이프라인 트리거 조건
```yaml
pipelines:
  # 기본 브랜치 (main/master)
  default:
    - step:
        name: Build and Test
        script:
          - npm ci
          - npm run build
          - npm run test
  
  # 특정 브랜치
  branches:
    develop:
      - step:
          name: Build and Test
          script:
            - npm ci
            - npm run build
            - npm run test
      - step:
          name: Deploy to Staging
          script:
            - echo "Deploying to staging"
    
    feature/*:
      - step:
          name: Build and Test
          script:
            - npm ci
            - npm run build
            - npm run test
  
  # 풀 리퀘스트
  pull-requests:
    '**':
      - step:
          name: Build and Test
          script:
            - npm ci
            - npm run build
            - npm run test
  
  # 태그
  tags:
    'v*':
      - step:
          name: Build and Test
          script:
            - npm ci
            - npm run build
            - npm run test
      - step:
          name: Deploy to Production
          script:
            - echo "Deploying to production"
```

### 2. 다양한 언어별 파이프라인

#### Node.js 프로젝트
```yaml
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
          - npm run lint
          - npm run build
          - npm run test
          - npm run test:coverage
        artifacts:
          - dist/**
          - coverage/**

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
```

#### Java 프로젝트 (Maven)
```yaml
image: maven:3.8-openjdk-17

definitions:
  caches:
    maven: ~/.m2
  steps:
    - step: &build-test
        name: Build and Test
        caches:
          - maven
        script:
          - mvn clean install
          - mvn test
          - mvn jacoco:report
        artifacts:
          - target/**

pipelines:
  default:
    - step: *build-test
  branches:
    develop:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - mvn spring-boot:run -Dspring.profiles.active=staging
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          script:
            - mvn spring-boot:run -Dspring.profiles.active=production
```

#### Python 프로젝트
```yaml
image: python:3.11

definitions:
  caches:
    pip: ~/.cache/pip
  steps:
    - step: &build-test
        name: Build and Test
        caches:
          - pip
        script:
          - pip install -r requirements.txt
          - pip install -r requirements-dev.txt
          - python -m pytest tests/
          - python -m flake8 src/
          - python -m black --check src/

pipelines:
  default:
    - step: *build-test
  branches:
    develop:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - pip install -r requirements.txt
            - python manage.py migrate
            - python manage.py runserver
```

### 3. 고급 파이프라인 기능

#### 조건부 실행
```yaml
pipelines:
  default:
    - step:
        name: Build and Test
        script:
          - npm ci
          - npm run build
          - npm run test
        condition:
          changesets:
            includePaths:
              - "src/**"
              - "package.json"
              - "package-lock.json"
    
    - step:
        name: Deploy
        script:
          - npm run deploy
        condition:
          changesets:
            includePaths:
              - "src/**"
            excludePaths:
              - "src/docs/**"
```

#### 병렬 실행
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
    
    - step:
        name: Deploy
        script:
          - npm run deploy
```

#### 환경 변수와 시크릿
```yaml
definitions:
  services:
    docker:
      memory: 2048
  steps:
    - step: &build-test
        name: Build and Test
        script:
          - echo $DATABASE_URL
          - echo $API_KEY
          - npm ci
          - npm run build
          - npm run test

pipelines:
  default:
    - step: *build-test
  branches:
    develop:
      - step:
          <<: *build-test
          name: Build and Deploy to Staging
          script:
            - echo $STAGING_DATABASE_URL
            - npm ci
            - npm run build
            - npm run test
            - npm run deploy:staging
```

## 예시

### 1. 실제 사용 사례

#### React 애플리케이션 파이프라인
```yaml
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
          - npm run lint
          - npm run build
          - npm run test
          - npm run test:coverage
        artifacts:
          - build/**
          - coverage/**

pipelines:
  default:
    - step: *build-test
  
  branches:
    develop:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - npm install -g aws-cli
            - aws s3 sync build/ s3://staging-bucket --delete
            - aws cloudfront create-invalidation --distribution-id $STAGING_DISTRIBUTION_ID --paths "/*"
    
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          script:
            - npm install -g aws-cli
            - aws s3 sync build/ s3://production-bucket --delete
            - aws cloudfront create-invalidation --distribution-id $PRODUCTION_DISTRIBUTION_ID --paths "/*"
  
  pull-requests:
    '**':
      - step: *build-test
```

#### Node.js API 서버 파이프라인
```yaml
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
          - npm run lint
          - npm run build
          - npm run test
          - npm run test:coverage
        artifacts:
          - dist/**
          - coverage/**

pipelines:
  default:
    - step: *build-test
  
  branches:
    develop:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - npm install -g pm2
            - pm2 deploy ecosystem.config.js staging
            - pm2 restart api-staging
    
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          script:
            - npm install -g pm2
            - pm2 deploy ecosystem.config.js production
            - pm2 restart api-production
  
  pull-requests:
    '**':
      - step: *build-test
```

### 2. 고급 패턴

#### 마이크로서비스 파이프라인
```yaml
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
          - npm run lint
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
          name: Deploy User Service
          script:
            - docker build -t user-service:$BITBUCKET_COMMIT .
            - docker push user-service:$BITBUCKET_COMMIT
            - kubectl set image deployment/user-service user-service=user-service:$BITBUCKET_COMMIT
    
    main:
      - step: *build-test
      - step:
          name: Deploy All Services
          script:
            - docker build -t user-service:$BITBUCKET_COMMIT .
            - docker push user-service:$BITBUCKET_COMMIT
            - kubectl set image deployment/user-service user-service=user-service:$BITBUCKET_COMMIT
            - kubectl rollout status deployment/user-service
```

#### 다중 환경 배포
```yaml
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
          - npm run lint
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
          name: Deploy to Development
          script:
            - echo "Deploying to development environment"
            - npm run deploy:dev
    
    staging:
      - step: *build-test
      - step:
          name: Deploy to Staging
          script:
            - echo "Deploying to staging environment"
            - npm run deploy:staging
    
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          script:
            - echo "Deploying to production environment"
            - npm run deploy:production
```

## 운영 팁

### 성능 최적화

#### 캐시 활용
```yaml
definitions:
  caches:
    npm: ~/.npm
    node_modules: node_modules
    build: build
  steps:
    - step: &build-test
        name: Build and Test
        caches:
          - npm
          - node_modules
          - build
        script:
          - npm ci --cache .npm --prefer-offline
          - npm run build
          - npm run test
```

#### 병렬 처리
```yaml
pipelines:
  default:
    - parallel:
        - step:
            name: Lint
            script:
              - npm run lint
        - step:
            name: Unit Tests
            script:
              - npm run test:unit
        - step:
            name: Integration Tests
            script:
              - npm run test:integration
    
    - step:
        name: Build
        script:
          - npm run build
```

### 에러 처리

#### 재시도 로직
```yaml
pipelines:
  default:
    - step:
        name: Build and Test
        script:
          - npm ci
          - npm run build
          - npm run test
        retry:
          automatic:
            - limit: 2
              reason: retry_on_retry
```

#### 조건부 배포
```yaml
pipelines:
  branches:
    main:
      - step:
          name: Build and Test
          script:
            - npm ci
            - npm run build
            - npm run test
      
      - step:
          name: Deploy to Production
          script:
            - npm run deploy:production
          condition:
            changesets:
              includePaths:
                - "src/**"
              excludePaths:
                - "src/docs/**"
```

## 참고

### Bitbucket Pipelines vs 다른 CI/CD 도구

| 측면 | Bitbucket Pipelines | GitHub Actions | GitLab CI | Jenkins |
|------|-------------------|----------------|-----------|---------|
| **통합** | Bitbucket 완벽 통합 | GitHub 완벽 통합 | GitLab 완벽 통합 | 독립적 |
| **설정** | YAML | YAML | YAML | Groovy |
| **무료 크레딧** | 2,500분/월 | 2,000분/월 | 400분/월 | 무제한 |
| **Docker 지원** | 네이티브 | 네이티브 | 네이티브 | 플러그인 |
| **클라우드 서비스** | 제한적 | 풍부 | 풍부 | 제한적 |

### 파이프라인 모범 사례

| 항목 | 권장사항 | 이유 |
|------|----------|------|
| **캐시 사용** | 의존성 캐싱 | 빌드 속도 향상 |
| **병렬 처리** | 독립적인 작업 병렬화 | 전체 실행 시간 단축 |
| **조건부 실행** | 변경된 파일에만 실행 | 불필요한 빌드 방지 |
| **아티팩트 관리** | 필요한 파일만 저장 | 저장 공간 절약 |
| **보안** | 환경 변수 사용 | 민감한 정보 보호 |

### 결론
Bitbucket Pipelines는 Git 저장소와의 완벽한 통합을 통해 효율적인 CI/CD 파이프라인을 구축할 수 있는 강력한 도구입니다.
YAML 기반의 간단한 설정으로 다양한 프로그래밍 언어와 프레임워크를 지원합니다.
캐시와 병렬 처리를 활용하여 빌드 성능을 최적화하세요.
조건부 실행과 에러 처리를 통해 안정적이고 효율적인 파이프라인을 구축하세요.
