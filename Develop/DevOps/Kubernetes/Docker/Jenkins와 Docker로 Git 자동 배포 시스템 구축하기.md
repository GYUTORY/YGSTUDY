---
title: Jenkins, Docker, Git을 활용한 Node.js 자동 배포 시스템 구축
tags: [application-architecture, kubernetes, docker, jenkins, nodejs, ci-cd]
updated: 2025-09-22
---

# Jenkins, Docker, Git을 활용한 Node.js 자동 배포 시스템 구축

## 목차

1. [자동 배포 시스템 개요](#1-자동-배포-시스템-개요)
2. [핵심 기술 이해](#2-핵심-기술-이해)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [환경 구축](#4-환경-구축)
5. [Node.js 애플리케이션 설정](#5-nodejs-애플리케이션-설정)
6. [Jenkins 파이프라인 구성](#6-jenkins-파이프라인-구성)
7. [배포 전략 및 모니터링](#7-배포-전략-및-모니터링)
8. [문제 해결 및 최적화](#8-문제-해결-및-최적화)
9. [참조](#9-참조)

---

## 1. 자동 배포 시스템 개요

### 1.1 자동 배포의 필요성

현대 소프트웨어 개발에서 자동 배포는 필수 요소가 되었습니다. 수동 배포 방식의 한계를 극복하고 개발 생산성을 향상시키기 위해 CI/CD(Continuous Integration/Continuous Deployment) 파이프라인을 구축하는 것이 중요합니다.

**수동 배포의 문제점:**
- 배포 과정에서 발생하는 인적 오류
- 환경별 설정 차이로 인한 불일치
- 배포 시간의 비효율성
- 롤백 과정의 복잡성
- 배포 이력 추적의 어려움

**자동 배포의 이점:**
- 일관된 배포 프로세스 보장
- 배포 시간 단축 및 효율성 증대
- 자동화된 테스트를 통한 품질 보장
- 빠른 롤백 및 복구 가능
- 배포 이력의 완전한 추적성

### 1.2 CI/CD 파이프라인 개념

CI/CD는 소프트웨어 개발과 배포를 자동화하는 방법론입니다.

**Continuous Integration (CI):**
- 개발자들이 코드를 자주 통합하는 방식
- 자동화된 빌드와 테스트를 통해 코드 품질 보장
- 조기 버그 발견 및 수정 가능

**Continuous Deployment (CD):**
- 통과한 코드를 자동으로 프로덕션 환경에 배포
- 수동 개입 없이 안정적인 배포 프로세스
- 빠른 피드백 루프 제공

---

## 2. 핵심 기술 이해

### 2.1 Git - 버전 관리 시스템

Git은 분산 버전 관리 시스템으로, 소스 코드의 변경 이력을 추적하고 관리합니다.

**Git의 핵심 개념:**

- **Repository**: 프로젝트의 모든 파일과 변경 이력이 저장되는 저장소
- **Commit**: 특정 시점의 코드 상태를 기록하는 스냅샷
- **Branch**: 독립적인 개발 라인을 생성하여 병렬 개발 가능
- **Merge**: 서로 다른 브랜치의 변경사항을 통합
- **Remote**: 원격 저장소와의 동기화를 위한 연결점

**Git 워크플로우:**
```bash
# 기본 Git 워크플로우
git clone <repository-url>    # 저장소 복제
git checkout -b feature-branch # 새 브랜치 생성
git add .                     # 변경사항 스테이징
git commit -m "message"       # 커밋 생성
git push origin feature-branch # 원격 저장소에 푸시
```

### 2.2 Jenkins - 자동화 서버

Jenkins는 오픈소스 자동화 서버로, CI/CD 파이프라인을 구축하고 관리하는 데 사용됩니다.

**Jenkins의 주요 기능:**

- **빌드 자동화**: 코드 변경 시 자동 빌드 실행
- **테스트 자동화**: 단위 테스트, 통합 테스트 자동 실행
- **배포 자동화**: 다양한 환경으로의 자동 배포
- **플러그인 생태계**: 확장 가능한 플러그인 아키텍처
- **분산 빌드**: 여러 노드에서 병렬 빌드 실행

**Jenkins 파이프라인:**
- **Declarative Pipeline**: 구조화된 파이프라인 정의
- **Scripted Pipeline**: Groovy 스크립트 기반 파이프라인
- **Blue Ocean**: 시각적 파이프라인 편집기

### 2.3 Docker - 컨테이너화 플랫폼

Docker는 애플리케이션을 컨테이너로 패키징하여 일관된 실행 환경을 제공합니다.

**Docker의 핵심 개념:**

- **Image**: 애플리케이션 실행에 필요한 모든 파일이 포함된 읽기 전용 템플릿
- **Container**: 이미지를 실행한 상태로, 격리된 실행 환경 제공
- **Dockerfile**: 이미지 빌드 방법을 정의하는 텍스트 파일
- **Registry**: Docker 이미지를 저장하고 공유하는 저장소

**Docker의 장점:**
- 환경 일관성 보장
- 빠른 배포 및 확장
- 리소스 효율성
- 마이크로서비스 아키텍처 지원

### 2.4 SSH - 보안 통신 프로토콜

SSH(Secure Shell)는 네트워크를 통해 안전하게 원격 서버에 접속할 수 있게 해주는 프로토콜입니다.

**SSH의 특징:**
- 암호화된 통신 채널
- 공개키/개인키 기반 인증
- 포트 포워딩 지원
- X11 포워딩 지원

---

## 3. 시스템 아키텍처

### 3.1 전체 시스템 구조

```
개발자 로컬 환경
        ↓ (git push)
Git 저장소 (GitHub/GitLab)
        ↓ (webhook)
Jenkins 서버
        ↓ (build & test)
Docker 이미지 생성
        ↓ (deploy)
프로덕션 서버
```

### 3.2 구성 요소별 역할

**Jenkins 서버:**
- Git 저장소 모니터링
- 빌드 및 테스트 실행
- Docker 이미지 생성
- 배포 스크립트 실행

**Git 저장소:**
- 소스 코드 버전 관리
- Webhook을 통한 Jenkins 트리거
- 브랜치 전략 관리

**프로덕션 서버:**
- Docker 컨테이너 실행
- 애플리케이션 서비스 제공
- 로그 수집 및 모니터링

### 3.3 네트워크 구성

**보안 고려사항:**
- Jenkins 서버와 프로덕션 서버 간 SSH 터널링
- 방화벽 설정을 통한 포트 제한
- SSL/TLS 인증서를 통한 HTTPS 통신
- VPN을 통한 내부 네트워크 접근

---

## 4. 환경 구축

### 4.1 Jenkins 서버 설정

#### 4.1.1 시스템 요구사항

**최소 사양:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB
- OS: Ubuntu 20.04 LTS 이상

**권장 사양:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD
- OS: Ubuntu 22.04 LTS

#### 4.1.2 Java 설치

Jenkins는 Java 기반 애플리케이션이므로 Java Runtime Environment가 필요합니다.

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Java 11 설치 (LTS 버전)
sudo apt install -y openjdk-11-jdk

# Java 버전 확인
java -version

# JAVA_HOME 환경변수 설정
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

#### 4.1.3 Jenkins 설치

```bash
# Jenkins 저장소 키 추가
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo gpg --dearmor -o /usr/share/keyrings/jenkins-keyring.gpg

# Jenkins 저장소 추가
echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/ | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

# 패키지 목록 업데이트 및 Jenkins 설치
sudo apt update
sudo apt install -y jenkins

# Jenkins 서비스 시작 및 활성화
sudo systemctl start jenkins
sudo systemctl enable jenkins

# Jenkins 상태 확인
sudo systemctl status jenkins
```

#### 4.1.4 Jenkins 초기 설정

1. **웹 인터페이스 접속**
   ```bash
   # 초기 관리자 비밀번호 확인
   sudo cat /var/lib/jenkins/secrets/initialAdminPassword
   ```

2. **브라우저에서 접속**
   - URL: `http://서버IP:8080`
   - 초기 비밀번호 입력

3. **플러그인 설치**
   - "Install suggested plugins" 선택
   - 필수 플러그인:
     - Git Plugin
     - Docker Pipeline Plugin
     - SSH Agent Plugin
     - NodeJS Plugin
     - Blue Ocean Plugin

4. **관리자 계정 생성**
   - 사용자명, 비밀번호, 이메일 설정

#### 4.1.5 Docker 설치

```bash
# Docker GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# Jenkins 사용자를 docker 그룹에 추가
sudo usermod -aG docker jenkins

# Jenkins 서비스 재시작
sudo systemctl restart jenkins

# Docker 설치 확인
docker --version
docker-compose --version
```

### 4.2 Node.js 환경 설정

#### 4.2.1 Node.js 설치

```bash
# NodeSource 저장소 추가 (Node.js 18 LTS)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Node.js 설치
sudo apt install -y nodejs

# 버전 확인
node --version
npm --version
```

#### 4.2.2 Jenkins에서 Node.js 설정

1. **Jenkins 관리 → Global Tool Configuration**
2. **NodeJS 섹션에서 "Add NodeJS" 클릭**
3. **설정:**
   - Name: `NodeJS-18`
   - Version: `18.x`
   - Global npm packages to install: `npm@latest`

### 4.3 Git 설정

#### 4.3.1 SSH 키 생성

```bash
# SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "jenkins@your-server"

# 공개키 확인
cat ~/.ssh/id_rsa.pub
```

#### 4.3.2 Git 저장소에 SSH 키 추가

1. **GitHub/GitLab에서:**
   - Settings → SSH and GPG keys
   - "New SSH key" 클릭
   - 공개키 내용 복사하여 추가

2. **Jenkins에서 SSH 키 설정:**
   - Jenkins 관리 → Credentials → System → Global credentials
   - "Add Credentials" 클릭
   - Kind: "SSH Username with private key"
   - Private key 내용 입력

---

## 5. Node.js 애플리케이션 설정

### 5.1 프로젝트 구조

```
nodejs-app/
├── src/
│   ├── controllers/
│   ├── models/
│   ├── routes/
│   ├── middleware/
│   └── app.js
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
├── Dockerfile
├── .dockerignore
├── .gitignore
└── Jenkinsfile
```

### 5.2 package.json 설정

```json
{
  "name": "nodejs-ci-cd-app",
  "version": "1.0.0",
  "description": "Node.js CI/CD 애플리케이션",
  "main": "src/app.js",
  "scripts": {
    "start": "node src/app.js",
    "dev": "nodemon src/app.js",
    "test": "jest",
    "test:coverage": "jest --coverage",
    "lint": "eslint src/",
    "lint:fix": "eslint src/ --fix"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "morgan": "^1.10.0",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "jest": "^29.6.2",
    "supertest": "^6.3.3",
    "nodemon": "^3.0.1",
    "eslint": "^8.46.0"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  }
}
```

### 5.3 Dockerfile 작성

```dockerfile
# 멀티스테이지 빌드를 통한 최적화
FROM node:18-alpine AS builder

# 작업 디렉토리 설정
WORKDIR /app

# 패키지 파일 복사
COPY package*.json ./

# 의존성 설치
RUN npm ci --only=production && npm cache clean --force

# 프로덕션 이미지
FROM node:18-alpine AS production

# 보안을 위한 non-root 사용자 생성
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 작업 디렉토리 설정
WORKDIR /app

# 빌드된 의존성 복사
COPY --from=builder /app/node_modules ./node_modules

# 애플리케이션 코드 복사
COPY --chown=nodejs:nodejs . .

# 사용자 전환
USER nodejs

# 포트 노출
EXPOSE 3000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

# 애플리케이션 실행
CMD ["npm", "start"]
```

### 5.4 .dockerignore 파일

```dockerignore
node_modules
npm-debug.log
.git
.gitignore
README.md
.env
.nyc_output
coverage
.nyc_output
.coverage
.vscode
.idea
*.log
```

### 5.5 기본 Express 애플리케이션

```javascript
// src/app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어 설정
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 라우트 설정
app.get('/', (req, res) => {
  res.json({
    message: 'Node.js CI/CD 애플리케이션이 정상적으로 실행 중입니다.',
    version: process.env.npm_package_version || '1.0.0',
    environment: process.env.NODE_ENV || 'development',
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'UP',
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    timestamp: new Date().toISOString()
  });
});

// 에러 핸들링 미들웨어
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: '서버 내부 오류가 발생했습니다.',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// 404 핸들러
app.use('*', (req, res) => {
  res.status(404).json({
    error: '요청한 리소스를 찾을 수 없습니다.'
  });
});

// 서버 시작
app.listen(PORT, () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다.`);
});

module.exports = app;
```

### 5.6 테스트 코드 작성

```javascript
// tests/unit/app.test.js
const request = require('supertest');
const app = require('../../src/app');

describe('애플리케이션 테스트', () => {
  test('GET / - 기본 라우트 테스트', async () => {
    const response = await request(app)
      .get('/')
      .expect(200);

    expect(response.body).toHaveProperty('message');
    expect(response.body).toHaveProperty('version');
    expect(response.body).toHaveProperty('environment');
  });

  test('GET /health - 헬스체크 테스트', async () => {
    const response = await request(app)
      .get('/health')
      .expect(200);

    expect(response.body).toHaveProperty('status', 'UP');
    expect(response.body).toHaveProperty('uptime');
    expect(response.body).toHaveProperty('memory');
  });

  test('GET /nonexistent - 404 테스트', async () => {
    const response = await request(app)
      .get('/nonexistent')
      .expect(404);

    expect(response.body).toHaveProperty('error');
  });
});
```

---

## 6. Jenkins 파이프라인 구성

### 6.1 Jenkinsfile 작성

```groovy
pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'nodejs-app'
        DOCKER_TAG = "${BUILD_NUMBER}"
        DOCKER_REGISTRY = 'your-registry.com'
        NODE_VERSION = '18'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
            }
        }
        
        stage('Install Dependencies') {
            steps {
                script {
                    sh '''
                        echo "Node.js 버전 확인"
                        node --version
                        npm --version
                        
                        echo "의존성 설치"
                        npm ci
                    '''
                }
            }
        }
        
        stage('Lint') {
            steps {
                script {
                    sh 'npm run lint'
                }
            }
        }
        
        stage('Test') {
            steps {
                script {
                    sh 'npm run test:coverage'
                }
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'test-results.xml'
                    publishCoverage adapters: [
                        jacocoAdapter('coverage/lcov.info')
                    ], sourceFileResolver: sourceFiles('STORE_LAST_BUILD')
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    sh """
                        echo "Docker 이미지 빌드 시작"
                        docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                        docker build -t ${DOCKER_IMAGE}:latest .
                        
                        echo "이미지 태그 생성"
                        docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker tag ${DOCKER_IMAGE}:latest ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:latest
                    """
                }
            }
        }
        
        stage('Push to Registry') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh """
                        echo "Docker 레지스트리에 이미지 푸시"
                        docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:latest
                    """
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    sh """
                        echo "스테이징 환경 배포"
                        docker stop nodejs-app-staging || true
                        docker rm nodejs-app-staging || true
                        docker run -d \\
                            --name nodejs-app-staging \\
                            -p 3001:3000 \\
                            -e NODE_ENV=staging \\
                            ${DOCKER_IMAGE}:${DOCKER_TAG}
                    """
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sh """
                        echo "프로덕션 환경 배포"
                        docker stop nodejs-app-prod || true
                        docker rm nodejs-app-prod || true
                        docker run -d \\
                            --name nodejs-app-prod \\
                            -p 3000:3000 \\
                            -e NODE_ENV=production \\
                            --restart unless-stopped \\
                            ${DOCKER_IMAGE}:${DOCKER_TAG}
                    """
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    sh """
                        echo "헬스체크 수행"
                        sleep 10
                        curl -f http://localhost:3000/health || exit 1
                        echo "배포 성공!"
                    """
                }
            }
        }
    }
    
    post {
        always {
            script {
                sh '''
                    echo "정리 작업 수행"
                    docker system prune -f
                '''
            }
        }
        success {
            echo '파이프라인이 성공적으로 완료되었습니다.'
        }
        failure {
            echo '파이프라인이 실패했습니다.'
        }
        unstable {
            echo '파이프라인이 불안정한 상태입니다.'
        }
    }
}
```

### 6.2 Jenkins 파이프라인 설정

#### 6.2.1 새 파이프라인 생성

1. **Jenkins 대시보드에서 "새 작업" 클릭**
2. **"Pipeline" 선택 후 이름 입력**
3. **"Pipeline" 섹션에서 설정:**
   - Definition: "Pipeline script from SCM"
   - SCM: "Git"
   - Repository URL: Git 저장소 URL
   - Credentials: SSH 키 선택
   - Branch Specifier: `*/main`
   - Script Path: "Jenkinsfile"

#### 6.2.2 Webhook 설정

**GitHub Webhook 설정:**
1. GitHub 저장소 → Settings → Webhooks
2. "Add webhook" 클릭
3. 설정:
   - Payload URL: `http://jenkins-server:8080/github-webhook/`
   - Content type: `application/json`
   - Events: "Just the push event"

### 6.3 고급 파이프라인 기능

#### 6.3.1 병렬 실행

```groovy
stage('Parallel Tests') {
    parallel {
        stage('Unit Tests') {
            steps {
                sh 'npm run test:unit'
            }
        }
        stage('Integration Tests') {
            steps {
                sh 'npm run test:integration'
            }
        }
        stage('Lint Check') {
            steps {
                sh 'npm run lint'
            }
        }
    }
}
```

#### 6.3.2 조건부 배포

```groovy
stage('Deploy') {
    when {
        anyOf {
            branch 'main'
            branch 'develop'
        }
    }
    steps {
        script {
            if (env.BRANCH_NAME == 'main') {
                // 프로덕션 배포
                sh 'deploy-to-production.sh'
            } else if (env.BRANCH_NAME == 'develop') {
                // 스테이징 배포
                sh 'deploy-to-staging.sh'
            }
        }
    }
}
```

---

## 7. 배포 전략 및 모니터링

### 7.1 배포 전략

#### 7.1.1 Blue-Green 배포

Blue-Green 배포는 두 개의 동일한 프로덕션 환경을 유지하여 무중단 배포를 구현하는 방식입니다.

```bash
#!/bin/bash
# blue-green-deploy.sh

APP_NAME="nodejs-app"
BLUE_PORT=3000
GREEN_PORT=3001
CURRENT_COLOR=$(docker inspect --format='{{.Config.Labels.color}}' ${APP_NAME}-current 2>/dev/null || echo "blue")

if [ "$CURRENT_COLOR" = "blue" ]; then
    NEW_COLOR="green"
    NEW_PORT=$GREEN_PORT
    OLD_PORT=$BLUE_PORT
else
    NEW_COLOR="blue"
    NEW_PORT=$BLUE_PORT
    OLD_PORT=$GREEN_PORT
fi

echo "현재 환경: $CURRENT_COLOR, 새 환경: $NEW_COLOR"

# 새 환경 배포
docker run -d \
    --name ${APP_NAME}-${NEW_COLOR} \
    -p ${NEW_PORT}:3000 \
    -e NODE_ENV=production \
    --label color=${NEW_COLOR} \
    ${APP_NAME}:${DOCKER_TAG}

# 헬스체크
sleep 10
if curl -f http://localhost:${NEW_PORT}/health; then
    echo "새 환경 배포 성공"
    
    # 로드밸런서 전환 (nginx 등)
    # nginx -s reload
    
    # 이전 환경 정리
    docker stop ${APP_NAME}-${CURRENT_COLOR}
    docker rm ${APP_NAME}-${CURRENT_COLOR}
    
    # 현재 환경 라벨 업데이트
    docker tag ${APP_NAME}-${NEW_COLOR} ${APP_NAME}-current
else
    echo "새 환경 배포 실패, 롤백"
    docker stop ${APP_NAME}-${NEW_COLOR}
    docker rm ${APP_NAME}-${NEW_COLOR}
    exit 1
fi
```

#### 7.1.2 Rolling 배포

Rolling 배포는 서버를 하나씩 순차적으로 업데이트하는 방식입니다.

```bash
#!/bin/bash
# rolling-deploy.sh

APP_NAME="nodejs-app"
REPLICAS=3
NEW_IMAGE="${APP_NAME}:${DOCKER_TAG}"

for i in $(seq 1 $REPLICAS); do
    echo "인스턴스 $i 업데이트 중..."
    
    # 새 인스턴스 시작
    docker run -d \
        --name ${APP_NAME}-new-$i \
        -p $((3000 + i)):3000 \
        -e NODE_ENV=production \
        $NEW_IMAGE
    
    # 헬스체크
    sleep 10
    if curl -f http://localhost:$((3000 + i))/health; then
        echo "인스턴스 $i 업데이트 성공"
        
        # 이전 인스턴스 정리
        docker stop ${APP_NAME}-old-$i || true
        docker rm ${APP_NAME}-old-$i || true
        
        # 새 인스턴스를 현재 인스턴스로 변경
        docker rename ${APP_NAME}-new-$i ${APP_NAME}-current-$i
    else
        echo "인스턴스 $i 업데이트 실패"
        docker stop ${APP_NAME}-new-$i
        docker rm ${APP_NAME}-new-$i
        exit 1
    fi
done
```

### 7.2 모니터링 설정

#### 7.2.1 애플리케이션 모니터링

```javascript
// src/middleware/monitoring.js
const prometheus = require('prom-client');

// 메트릭 수집기 초기화
const register = new prometheus.Registry();

// 기본 메트릭 수집
prometheus.collectDefaultMetrics({ register });

// 커스텀 메트릭 정의
const httpRequestDuration = new prometheus.Histogram({
    name: 'http_request_duration_seconds',
    help: 'HTTP 요청 처리 시간',
    labelNames: ['method', 'route', 'status_code'],
    buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10]
});

const httpRequestTotal = new prometheus.Counter({
    name: 'http_requests_total',
    help: '총 HTTP 요청 수',
    labelNames: ['method', 'route', 'status_code']
});

const activeConnections = new prometheus.Gauge({
    name: 'active_connections',
    help: '현재 활성 연결 수'
});

// 메트릭 등록
register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestTotal);
register.registerMetric(activeConnections);

// 모니터링 미들웨어
const monitoringMiddleware = (req, res, next) => {
    const start = Date.now();
    
    res.on('finish', () => {
        const duration = (Date.now() - start) / 1000;
        const labels = {
            method: req.method,
            route: req.route ? req.route.path : req.path,
            status_code: res.statusCode
        };
        
        httpRequestDuration.observe(labels, duration);
        httpRequestTotal.inc(labels);
    });
    
    next();
};

// 메트릭 엔드포인트
const metricsEndpoint = (req, res) => {
    res.set('Content-Type', register.contentType);
    res.end(register.metrics());
};

module.exports = {
    monitoringMiddleware,
    metricsEndpoint,
    register
};
```

#### 7.2.2 로그 관리

```javascript
// src/utils/logger.js
const winston = require('winston');

const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    defaultMeta: { service: 'nodejs-app' },
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.simple()
            )
        })
    ]
});

module.exports = logger;
```

### 7.3 알림 설정

#### 7.3.1 Slack 알림

```groovy
// Jenkinsfile에 추가
post {
    success {
        slackSend(
            channel: '#deployments',
            color: 'good',
            message: "배포 성공: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        )
    }
    failure {
        slackSend(
            channel: '#deployments',
            color: 'danger',
            message: "배포 실패: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        )
    }
}
```

#### 7.3.2 이메일 알림

```groovy
// Jenkinsfile에 추가
post {
    always {
        emailext (
            subject: "빌드 결과: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                빌드 결과: ${currentBuild.result}
                프로젝트: ${env.JOB_NAME}
                빌드 번호: ${env.BUILD_NUMBER}
                Git 커밋: ${env.GIT_COMMIT}
                빌드 URL: ${env.BUILD_URL}
            """,
            to: 'dev-team@company.com'
        )
    }
}
```

---

## 8. 문제 해결 및 최적화

### 8.1 일반적인 문제 해결

#### 8.1.1 Jenkins 관련 문제

**빌드 실패 문제:**
```bash
# Jenkins 로그 확인
sudo tail -f /var/log/jenkins/jenkins.log

# 시스템 로그 확인
sudo journalctl -u jenkins -f

# 메모리 사용량 확인
free -h
ps aux | grep jenkins
```

**권한 문제 해결:**
```bash
# Jenkins 사용자 권한 확인
sudo -u jenkins whoami
sudo -u jenkins groups

# Docker 권한 확인
sudo -u jenkins docker ps

# 파일 권한 수정
sudo chown -R jenkins:jenkins /var/lib/jenkins/workspace/
```

#### 8.1.2 Docker 관련 문제

**이미지 빌드 실패:**
```bash
# Docker 데몬 상태 확인
sudo systemctl status docker

# Docker 로그 확인
sudo journalctl -u docker -f

# 디스크 공간 확인
df -h
docker system df

# 불필요한 리소스 정리
docker system prune -a
```

**컨테이너 실행 오류:**
```bash
# 컨테이너 로그 확인
docker logs <container-name>

# 컨테이너 상태 확인
docker ps -a
docker inspect <container-name>

# 포트 충돌 확인
netstat -tulpn | grep :3000
```

#### 8.1.3 Node.js 관련 문제

**의존성 설치 실패:**
```bash
# npm 캐시 정리
npm cache clean --force

# node_modules 삭제 후 재설치
rm -rf node_modules package-lock.json
npm install

# Node.js 버전 확인
node --version
npm --version
```

**메모리 부족 문제:**
```bash
# Node.js 메모리 제한 설정
export NODE_OPTIONS="--max-old-space-size=4096"

# 또는 package.json에서
"scripts": {
    "start": "node --max-old-space-size=4096 src/app.js"
}
```

### 8.2 성능 최적화

#### 8.2.1 Docker 이미지 최적화

```dockerfile
# 멀티스테이지 빌드로 이미지 크기 최적화
FROM node:18-alpine AS dependencies
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

FROM node:18-alpine AS production
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .
USER nodejs
EXPOSE 3000
CMD ["npm", "start"]
```

#### 8.2.2 Jenkins 성능 최적화

```bash
# Jenkins JVM 설정 최적화
sudo nano /etc/default/jenkins

# 다음 설정 추가
JENKINS_JAVA_OPTIONS="-Xmx2048m -Xms1024m -XX:+UseG1GC"
```

#### 8.2.3 Node.js 애플리케이션 최적화

```javascript
// 클러스터 모드로 멀티프로세싱 활용
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
    console.log(`마스터 프로세스 ${process.pid} 실행 중`);
    
    // 워커 프로세스 생성
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }
    
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 프로세스 ${worker.process.pid} 종료`);
        cluster.fork(); // 자동 재시작
    });
} else {
    // 워커 프로세스에서 애플리케이션 실행
    require('./src/app');
    console.log(`워커 프로세스 ${process.pid} 시작`);
}
```

### 8.3 보안 강화

#### 8.3.1 Docker 보안

```dockerfile
# 보안 강화된 Dockerfile
FROM node:18-alpine AS production

# 보안 업데이트
RUN apk update && apk upgrade

# non-root 사용자 생성
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 작업 디렉토리 설정
WORKDIR /app

# 파일 권한 설정
COPY --chown=nodejs:nodejs . .

# 사용자 전환
USER nodejs

# 포트 노출
EXPOSE 3000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

# 실행
CMD ["npm", "start"]
```

#### 8.3.2 애플리케이션 보안

```javascript
// 보안 미들웨어
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

// Helmet 설정
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
            imgSrc: ["'self'", "data:", "https:"]
        }
    }
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15분
    max: 100, // 최대 100 요청
    message: '너무 많은 요청이 발생했습니다.'
});
app.use(limiter);
```

---

## 9. 참조

### 9.1 공식 문서

- [Jenkins 공식 문서](https://www.jenkins.io/doc/)
- [Docker 공식 문서](https://docs.docker.com/)
- [Node.js 공식 문서](https://nodejs.org/docs/)
- [Express.js 공식 문서](https://expressjs.com/)
- [Git 공식 문서](https://git-scm.com/doc)

### 9.2 추가 학습 자료

- [CI/CD 모범 사례](https://docs.github.com/en/actions/learn-github-actions)
- [Docker 보안 모범 사례](https://docs.docker.com/develop/security-best-practices/)
- [Node.js 성능 최적화](https://nodejs.org/en/docs/guides/simple-profiling/)
- [Express.js 보안 모범 사례](https://expressjs.com/en/advanced/best-practice-security.html)

### 9.3 도구 및 플러그인

- [Jenkins Blue Ocean](https://plugins.jenkins.io/blueocean/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Prometheus 모니터링](https://prometheus.io/)
- [Grafana 대시보드](https://grafana.com/)

### 9.4 관련 기술

- [Kubernetes 오케스트레이션](https://kubernetes.io/docs/)
- [Terraform 인프라 관리](https://www.terraform.io/docs)
- [Ansible 자동화](https://docs.ansible.com/)
- [Nginx 리버스 프록시](https://nginx.org/en/docs/)

---

