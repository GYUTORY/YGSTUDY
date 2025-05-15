# Bitbucket Pipelines 가이드 🚀

## 목차 📑
1. [Bitbucket Pipelines란?](#bitbucket-pipelines란)
2. [기본 개념](#기본-개념)
3. [bitbucket-pipelines.yml 설정](#bitbucket-pipelinesyml-설정)
4. [파이프라인 단계](#파이프라인-단계)
5. [자주 사용되는 기능](#자주-사용되는-기능)
6. [고급 기능](#고급-기능)
7. [모범 사례](#모범-사례)
8. [문제 해결](#문제-해결)

## Bitbucket Pipelines란? 🤔

Bitbucket Pipelines는 Bitbucket Cloud에서 제공하는 CI/CD(지속적 통합/배포) 서비스입니다. 코드 저장소에 변경사항이 발생할 때마다 자동으로 빌드, 테스트, 배포를 수행할 수 있게 해주는 도구입니다.

### 주요 특징 ✨
- Docker 기반의 격리된 환경
- YAML 파일로 간단한 설정
- Bitbucket과의 완벽한 통합
- 다양한 프로그래밍 언어 및 프레임워크 지원
- 무료 크레딧 제공 (월 2,500분)
- AWS, Google Cloud, Azure 등 주요 클라우드 서비스와의 통합

### 장점 🌟
1. **간편한 설정**: YAML 파일 하나로 전체 CI/CD 파이프라인 구성
2. **격리된 환경**: 각 빌드는 독립된 Docker 컨테이너에서 실행
3. **확장성**: 필요에 따라 파이프라인 단계 추가/수정 가능
4. **보안**: 저장소 내에서 모든 작업이 수행되어 보안성 향상
5. **통합성**: Bitbucket의 다른 기능들과 원활한 연동

## 기본 개념 📚

### 파이프라인 구성요소
1. **파이프라인(Pipeline)**: 전체 CI/CD 프로세스
   - 브랜치별 파이프라인
   - 풀 리퀘스트 파이프라인
   - 태그 파이프라인

2. **스텝(Step)**: 파이프라인의 개별 작업 단위
   - 빌드 스텝
   - 테스트 스텝
   - 배포 스텝
   - 검증 스텝

3. **스크립트(Script)**: 각 스텝에서 실행되는 명령어들
   - 쉘 명령어
   - 프로그래밍 언어 명령어
   - 커스텀 스크립트

4. **아티팩트(Artifact)**: 빌드 결과물
   - 빌드된 파일
   - 테스트 리포트
   - 로그 파일

### 파이프라인 트리거 조건
- 브랜치 푸시
- 풀 리퀘스트 생성/업데이트
- 태그 푸시
- 수동 트리거

## bitbucket-pipelines.yml 설정 ⚙️

### 기본 구조
```yaml
image: node:16

definitions:
  caches:
    npm: ~/.npm
  steps:
    - step: &build-test
        name: Build and Test
        caches:
          - npm
        script:
          - npm install
          - npm run test
        artifacts:
          - dist/**

pipelines:
  default:
    - step: *build-test
  
  branches:
    main:
      - step: *build-test
      - step:
          name: Deploy to Production
          deployment: production
          script:
            - echo "Deploying to production..."
  
  pull-requests:
    '**':
      - step: *build-test
```

### 주요 설정 항목 상세 설명
1. **image**: 파이프라인 실행 환경
   - 공식 Docker 이미지 사용
   - 커스텀 Docker 이미지 사용
   - 멀티 스테이지 빌드 지원

2. **pipelines**: 파이프라인 정의
   - default: 기본 파이프라인
   - branches: 브랜치별 파이프라인
   - pull-requests: PR별 파이프라인
   - tags: 태그별 파이프라인

3. **step**: 실행할 작업 단계
   - name: 스텝 이름
   - script: 실행할 명령어
   - caches: 캐시 설정
   - artifacts: 아티팩트 설정
   - services: 추가 서비스 설정

4. **script**: 실행할 명령어
   - 쉘 명령어
   - 프로그래밍 언어 명령어
   - 조건문과 반복문 사용 가능

5. **artifacts**: 저장할 빌드 결과물
   - 파일 패턴 지정
   - 디렉토리 지정
   - 와일드카드 사용 가능

## 파이프라인 단계 🔄

### 1. 빌드 단계
```yaml
- step:
    name: Build
    caches:
      - npm
    script:
      - npm ci
      - npm run build
    artifacts:
      - dist/**
      - build/**
```

### 2. 테스트 단계
```yaml
- step:
    name: Test
    caches:
      - npm
    script:
      - npm run test:unit
      - npm run test:integration
      - npm run test:e2e
    artifacts:
      - coverage/**
      - test-results/**
```

### 3. 린트 및 코드 품질 검사
```yaml
- step:
    name: Lint and Quality
    script:
      - npm run lint
      - npm run sonar
    artifacts:
      - sonar-report/**
```

### 4. 배포 단계
```yaml
- step:
    name: Deploy
    deployment: production
    script:
      - npm run deploy
    after-script:
      - npm run health-check
```

## 자주 사용되는 기능 🛠️

### 환경 변수
```yaml
definitions:
  steps:
    - step: &build-step
        script:
          - echo $MY_SECRET
          - echo $AWS_ACCESS_KEY
          - echo $DATABASE_URL

# 환경 변수 설정 방법
# 1. Bitbucket 저장소 설정에서 직접 설정
# 2. bitbucket-pipelines.yml에서 설정
# 3. 배포 환경별로 다른 값 설정
```

### 캐시 사용
```yaml
definitions:
  caches:
    npm: ~/.npm
    gradle: ~/.gradle
    maven: ~/.m2

- step:
    caches:
      - npm
      - gradle
    script:
      - npm install
      - ./gradlew build
```

### 병렬 실행
```yaml
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

### 조건부 실행
```yaml
- step:
    name: Conditional Step
    condition:
      changesets:
        includePaths:
          - "src/**"
          - "package.json"
    script:
      - echo "Changes detected in source files"
```

## 고급 기능 🎯

### 커스텀 Docker 이미지
```yaml
image:
  name: your-registry/custom-image:latest
  username: $DOCKER_USERNAME
  password: $DOCKER_PASSWORD
```

### 서비스 컨테이너
```yaml
definitions:
  services:
    docker:
      memory: 2048
    database:
      image: postgres:13
      variables:
        POSTGRES_DB: testdb
        POSTGRES_USER: testuser
        POSTGRES_PASSWORD: testpass
```

### 워크플로우
```yaml
pipelines:
  custom:
    build-and-deploy:
      - step:
          name: Build
          script:
            - npm run build
      - step:
          name: Deploy
          deployment: staging
          trigger: manual
          script:
            - npm run deploy
```

## 모범 사례 💡

### 1. 효율적인 캐시 사용
- 의존성 파일 캐싱
  ```yaml
  caches:
    npm: ~/.npm
    pip: ~/.cache/pip
    gradle: ~/.gradle
  ```
- 빌드 결과물 캐싱
  ```yaml
  caches:
    build: build/
    dist: dist/
  ```

### 2. 보안
- 민감한 정보는 환경 변수로 관리
  ```yaml
  script:
    - echo $AWS_ACCESS_KEY
    - echo $DATABASE_URL
  ```
- SSH 키 보안 관리
  ```yaml
  script:
    - pipe: atlassian/ssh-run:0.7.0
      variables:
        SSH_USER: $SSH_USER
        SERVER: $SERVER
        COMMAND: 'deploy.sh'
  ```

### 3. 성능 최적화
- 불필요한 단계 제거
- 병렬 실행 활용
- 캐시 전략 수립
- 이미지 크기 최적화

### 4. 모니터링
- 파이프라인 실행 상태 모니터링
- 실패 시 알림 설정
- 메트릭 수집
- 로그 분석

## 문제 해결 🔧

### 일반적인 문제
1. **빌드 실패**
   - 로그 확인
   - 환경 변수 검증
   - 의존성 문제 확인

2. **성능 이슈**
   - 캐시 활용 확인
   - 불필요한 단계 제거
   - 이미지 최적화

3. **보안 문제**
   - 환경 변수 검증
   - 권한 설정 확인
   - 시크릿 관리 확인

### 디버깅 팁
1. 로그 레벨 조정
2. 단계별 실행
3. 로컬 테스트
4. 캐시 초기화

## EC2 배포 파이프라인 구성 🚀

### 1. AWS 인증 설정
```yaml
definitions:
  steps:
    - step: &deploy-to-ec2
        name: Deploy to EC2
        script:
          # AWS 인증 설정
          - pipe: atlassian/aws-ecs-deploy:1.1.0
            variables:
              AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID
              AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
              AWS_DEFAULT_REGION: 'ap-northeast-2'
```

### 2. SSH 키 설정
```yaml
definitions:
  steps:
    - step: &deploy-to-ec2
        name: Deploy to EC2
        script:
          # SSH 키 설정
          - mkdir -p ~/.ssh
          - echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
          - chmod 600 ~/.ssh/id_rsa
          - ssh-keyscan -H $EC2_HOST >> ~/.ssh/known_hosts
```

### 3. 배포 스크립트 예제
```yaml
pipelines:
  branches:
    main:
      - step:
          name: Build and Deploy
          script:
            # 빌드
            - npm install
            - npm run build
            
            # 배포 스크립트 실행
            - pipe: atlassian/ssh-run:0.7.0
              variables:
                SSH_USER: 'ec2-user'
                SERVER: $EC2_HOST
                COMMAND: |
                  cd /home/ec2-user/app
                  git pull origin main
                  npm install
                  pm2 restart app
```

### 4. 환경 변수 설정
```yaml
# Bitbucket 저장소 설정에서 다음 환경 변수 설정 필요
# AWS_ACCESS_KEY_ID: AWS 액세스 키
# AWS_SECRET_ACCESS_KEY: AWS 시크릿 키
# EC2_HOST: EC2 인스턴스 호스트 주소
# SSH_PRIVATE_KEY: EC2 인스턴스 접속용 SSH 프라이빗 키
```

### 5. 배포 전 준비사항

#### 5.1 EC2 인스턴스 설정
1. **보안 그룹 설정**
   ```bash
   # SSH 접속 허용 (포트 22)
   # 애플리케이션 포트 허용 (예: 3000, 8080 등)
   ```

2. **Node.js 설치**
   ```bash
   # Amazon Linux 2
   curl -sL https://rpm.nodesource.com/setup_16.x | sudo bash -
   sudo yum install -y nodejs
   
   # Ubuntu
   curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

3. **PM2 설치**
   ```bash
   sudo npm install -g pm2
   ```

#### 5.2 배포 디렉토리 설정
```bash
# EC2 인스턴스에서 실행
mkdir -p /home/ec2-user/app
cd /home/ec2-user/app
git init
git remote add origin <repository-url>
```

### 6. 자동화된 배포 파이프라인

#### 6.1 기본 배포 파이프라인
```yaml
image: node:16

definitions:
  steps:
    - step: &build-and-deploy
        name: Build and Deploy
        script:
          # 빌드
          - npm install
          - npm run build
          
          # 배포
          - pipe: atlassian/ssh-run:0.7.0
            variables:
              SSH_USER: 'ec2-user'
              SERVER: $EC2_HOST
              COMMAND: |
                cd /home/ec2-user/app
                git pull origin main
                npm install
                pm2 restart app

pipelines:
  branches:
    main:
      - step: *build-and-deploy
```

#### 6.2 Blue-Green 배포 파이프라인
```yaml
image: node:16

definitions:
  steps:
    - step: &blue-green-deploy
        name: Blue-Green Deployment
        script:
          # 빌드
          - npm install
          - npm run build
          
          # Blue-Green 배포
          - pipe: atlassian/ssh-run:0.7.0
            variables:
              SSH_USER: 'ec2-user'
              SERVER: $EC2_HOST
              COMMAND: |
                # 현재 실행 중인 인스턴스 확인
                CURRENT_INSTANCE=$(pm2 list | grep "app" | awk '{print $2}')
                
                # 새 인스턴스 배포
                cd /home/ec2-user/app
                git pull origin main
                npm install
                pm2 start app.js --name "app-new"
                
                # 트래픽 전환
                sleep 10
                pm2 delete $CURRENT_INSTANCE

pipelines:
  branches:
    main:
      - step: *blue-green-deploy
```

### 7. 배포 후 검증

#### 7.1 헬스 체크
```yaml
- step:
    name: Health Check
    script:
      - pipe: atlassian/ssh-run:0.7.0
        variables:
          SSH_USER: 'ec2-user'
          SERVER: $EC2_HOST
          COMMAND: |
            curl -f http://localhost:3000/health || exit 1
```

#### 7.2 로그 확인
```yaml
- step:
    name: Check Logs
    script:
      - pipe: atlassian/ssh-run:0.7.0
        variables:
          SSH_USER: 'ec2-user'
          SERVER: $EC2_HOST
          COMMAND: |
            pm2 logs app --lines 100
```

### 8. 롤백 전략

#### 8.1 자동 롤백
```yaml
- step:
    name: Rollback if Failed
    trigger: manual
    script:
      - pipe: atlassian/ssh-run:0.7.0
        variables:
          SSH_USER: 'ec2-user'
          SERVER: $EC2_HOST
          COMMAND: |
            cd /home/ec2-user/app
            git reset --hard HEAD^
            npm install
            pm2 restart app
```

### 9. 모니터링 설정

#### 9.1 CloudWatch 통합
```yaml
- step:
    name: Setup CloudWatch
    script:
      - pipe: atlassian/aws-cloudwatch-metrics:0.3.0
        variables:
          AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID
          AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
          AWS_DEFAULT_REGION: 'ap-northeast-2'
          METRIC_NAME: 'DeploymentStatus'
          METRIC_VALUE: '1'
          METRIC_UNIT: 'Count'
```

### 10. 보안 모범 사례

1. **IAM 역할 사용**
   - EC2 인스턴스에 IAM 역할 할당
   - 최소 권한 원칙 적용

2. **시크릿 관리**
   - AWS Secrets Manager 사용
   - 환경 변수 암호화

3. **네트워크 보안**
   - VPC 설정
   - 보안 그룹 최소화

### 11. 문제 해결

#### 11.1 일반적인 문제
1. **배포 실패**
   - SSH 연결 확인
   - 권한 확인
   - 디스크 공간 확인

2. **애플리케이션 오류**
   - PM2 로그 확인
   - Node.js 버전 확인
   - 의존성 문제 확인

#### 11.2 디버깅 명령어
```bash
# PM2 상태 확인
pm2 status

# 애플리케이션 로그 확인
pm2 logs app

# 시스템 리소스 확인
htop

# 디스크 공간 확인
df -h
```

## 결론 🎯

Bitbucket Pipelines는 개발 워크플로우를 자동화하고 효율화하는 강력한 도구입니다. 적절한 설정과 모범 사례를 따르면 더욱 효과적인 CI/CD 파이프라인을 구축할 수 있습니다. 지속적인 모니터링과 최적화를 통해 안정적이고 효율적인 파이프라인을 유지하는 것이 중요합니다.
