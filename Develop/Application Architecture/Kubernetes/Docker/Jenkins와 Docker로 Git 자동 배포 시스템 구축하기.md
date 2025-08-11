---
title: Jenkins, Docker, Git
tags: [application-architecture, kubernetes, docker, jenkins와-docker로-git-자동-배포-시스템-구축하기]
updated: 2025-08-10
---
# Jenkins, Docker, Git을 활용한 자동 배포 시스템 구축 가이드

## 배경
- [1. 자동 배포 시스템이란?](#1-자동-배포-시스템이란)
- [2. 필요한 기술들](#2-필요한-기술들)
- [3. 시스템 구축 단계](#3-시스템-구축-단계)
- [4. 실제 설정 방법](#4-실제-설정-방법)
- [5. 문제 해결](#5-문제-해결)

---

sudo apt update
sudo apt upgrade -y

sudo apt remove docker docker-engine docker.io containerd runc

sudo apt update
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

cat ~/.ssh/id_rsa.pub
```

**Git 저장소에 SSH 키 추가:**
1. GitHub/GitLab에서 Settings → SSH Keys
2. 위에서 확인한 공개키 내용을 추가

**Jenkins에서 SSH 키 설정:**
1. Jenkins 관리 → Credentials → System → Global credentials
2. "Add Credentials" 클릭
3. Kind에서 "SSH Username with private key" 선택
4. Private key 내용 입력

### 4.4 배포 스크립트 작성

#### 4.4.1 deploy.sh

```bash

APP_NAME="myapp"
DOCKER_IMAGE="myapp"
DOCKER_TAG=$(git rev-parse --short HEAD)

echo "배포 시작: $DOCKER_TAG"

echo "기존 컨테이너 정리 중..."
docker stop $APP_NAME 2>/dev/null || true
docker rm $APP_NAME 2>/dev/null || true

echo "Docker 이미지 빌드 중..."
docker build -t $DOCKER_IMAGE:$DOCKER_TAG .

echo "새 컨테이너 실행 중..."
docker run -d \
    --name $APP_NAME \
    -p 8080:8080 \
    -e SPRING_PROFILES_ACTIVE=prod \
    $DOCKER_IMAGE:$DOCKER_TAG

echo "애플리케이션 상태 확인 중..."
for i in {1..30}; do
    if curl -s http://localhost:8080/actuator/health | grep -q "UP"; then
        echo "배포 성공! 애플리케이션이 정상 실행 중입니다."
        exit 0
    fi
    echo "대기 중... ($i/30)"
    sleep 2
done

echo "배포 실패! 애플리케이션이 정상 실행되지 않았습니다."
exit 1
```

### 4.5 원격 서버 배포 설정

#### 4.5.1 SSH 키 설정

**원격 서버에 SSH 키 복사:**
```bash

ssh-copy-id -i ~/.ssh/id_rsa.pub user@remote-server

REMOTE_SERVER="remote-server"
REMOTE_PATH="/opt/applications"
APP_NAME="myapp"

echo "원격 서버 배포 시작..."

ssh $REMOTE_SERVER << EOF
    echo "원격 서버에서 작업 시작..."
    
    # 작업 디렉토리로 이동
    cd $REMOTE_PATH
    
    # 최신 코드 가져오기
    echo "최신 코드 다운로드 중..."
    git pull origin main
    
    # 이전 컨테이너 정리
    echo "기존 컨테이너 정리 중..."
    docker stop $APP_NAME 2>/dev/null || true
    docker rm $APP_NAME 2>/dev/null || true
    
    # 새 이미지 빌드
    echo "새 이미지 빌드 중..."
    docker build -t $APP_NAME:latest .
    
    # 새 컨테이너 실행
    echo "새 컨테이너 실행 중..."
    docker run -d \
        --name $APP_NAME \
        -p 8080:8080 \
        -e SPRING_PROFILES_ACTIVE=prod \
        $APP_NAME:latest
    
    echo "배포 완료!"
    
    # 컨테이너 상태 확인
    docker ps | grep $APP_NAME
EOF

echo "원격 배포 완료!"
```

---











---





## 5. 문제 해결

### 5.1 자주 발생하는 문제들

#### 5.1.1 Jenkins 관련 문제

**빌드가 실패하는 경우:**
- 로그 확인: Jenkins 대시보드 → 빌드 → Console Output
- 권한 문제: 파일 권한이나 디렉토리 권한 확인
- 메모리 부족: JVM 힙 메모리 설정 조정

**플러그인 오류:**
- 플러그인 재설치
- Jenkins 재시작
- 플러그인 버전 호환성 확인

#### 5.1.2 Docker 관련 문제

**이미지 빌드 실패:**
- Dockerfile 문법 오류 확인
- 필요한 파일이 올바른 위치에 있는지 확인
- 네트워크 연결 상태 확인

**컨테이너 실행 오류:**
- 포트 충돌 확인: `netstat -tulpn | grep 8080`
- 리소스 부족 확인: `docker stats`
- 로그 확인: `docker logs 컨테이너명`

#### 5.1.3 Git 관련 문제

**SSH 연결 오류:**
- SSH 키가 올바르게 설정되었는지 확인
- Git 저장소 URL이 SSH 형식인지 확인
- 방화벽 설정 확인

### 5.2 로그 확인 방법

#### 5.2.1 Jenkins 로그
```bash

docker logs -f 컨테이너명

docker exec -it 컨테이너명 tail -f /app/logs/application.log
```

### 5.3 성능 최적화

#### 5.3.1 Jenkins 최적화
- JVM 힙 메모리 설정 조정
- 불필요한 빌드 기록 정리
- 빌드 에이전트 추가

#### 5.3.2 Docker 최적화
- 멀티스테이지 빌드 사용
- .dockerignore 파일 활용
- 이미지 레이어 최적화

---

## 6. 실제 운영 팁

### 6.1 배포 전략

**Blue-Green 배포:**
- 새 버전을 별도 환경에서 먼저 테스트
- 문제없으면 트래픽을 새 환경으로 전환
- 문제 발생 시 즉시 이전 환경으로 복구

**Rolling 배포:**
- 서버를 하나씩 순차적으로 업데이트
- 서비스 중단 없이 배포 가능
- 문제 발생 시 즉시 중단 가능

### 6.2 모니터링

**시스템 모니터링:**
- CPU, 메모리, 디스크 사용량 확인
- 네트워크 트래픽 모니터링
- 로그 파일 크기 관리

**애플리케이션 모니터링:**
- 애플리케이션 응답 시간 확인
- 에러율 모니터링
- 사용자 활동 추적

### 6.3 백업 및 복구

**정기 백업:**
- Jenkins 설정 백업
- Docker 이미지 백업
- 데이터베이스 백업

**재해 복구 계획:**
- 백업에서 복구 절차 문서화
- 복구 시간 목표 설정
- 정기적인 복구 테스트 수행

---

## 7. 마무리

이 가이드를 따라하면 Jenkins, Docker, Git을 활용한 자동 배포 시스템을 구축할 수 있습니다. 처음에는 복잡해 보일 수 있지만, 한 번 설정해두면 개발 효율성이 크게 향상됩니다.

**다음 단계:**
- 실제 프로젝트에 적용해보기
- 팀원들과 함께 사용해보기
- 필요에 따라 추가 기능 구현하기

## 1. 자동 배포 시스템이란?

### 1.1 기존 배포 방식의 문제점

**수동 배포**를 할 때 겪는 불편함들:
- 코드를 수정할 때마다 서버에 직접 접속해서 파일을 업로드해야 함
- 배포 과정에서 실수로 잘못된 파일을 올리거나 설정을 놓칠 수 있음
- 팀원들이 각자 다른 방식으로 배포해서 환경이 달라질 수 있음
- 배포 중에 서비스가 중단될 수 있음

### 1.2 자동 배포의 장점

**자동 배포**를 사용하면:
- 코드를 Git에 올라가면 자동으로 서버에 배포됨
- 배포 과정이 표준화되어 실수 가능성이 줄어듦
- 언제든지 이전 버전으로 되돌릴 수 있음
- 배포 과정을 추적하고 기록할 수 있음

### 1.3 전체 시스템 구조

```
개발자가 코드를 수정
        ↓
    Git 저장소에 업로드
        ↓
    Jenkins가 변경사항 감지
        ↓
    자동으로 빌드 및 테스트
        ↓
    Docker 이미지 생성
        ↓
    서버에 자동 배포
```

---

## 2. 필요한 기술들

### 2.1 Git (깃)

**Git이란?**
- 코드의 버전을 관리하는 도구
- 여러 사람이 함께 작업할 때 코드 충돌을 방지
- 이전 버전으로 언제든지 되돌릴 수 있음

**Git의 기본 개념:**
- **Repository (저장소)**: 프로젝트 코드가 저장되는 곳
- **Commit (커밋)**: 코드 변경사항을 저장하는 행위
- **Branch (브랜치)**: 독립적인 작업 공간
- **Push (푸시)**: 로컬 변경사항을 원격 저장소에 업로드

### 2.2 Jenkins (젠킨스)

**Jenkins란?**
- 자동화 도구 (CI/CD 도구)
- Git에 코드가 올라가면 자동으로 감지
- 설정한 작업들을 순서대로 자동 실행

**Jenkins가 하는 일:**
- 코드 변경 감지
- 자동 빌드 (컴파일, 패키징)
- 자동 테스트 실행
- 자동 배포

### 2.3 Docker (도커)

**Docker란?**
- 애플리케이션을 컨테이너로 패키징하는 도구
- "어디서든 동일하게 실행되는 환경"을 만들어줌

**Docker의 핵심 개념:**
- **Image (이미지)**: 애플리케이션 실행에 필요한 모든 파일이 담긴 패키지
- **Container (컨테이너)**: 이미지를 실행한 상태
- **Dockerfile**: 이미지를 만드는 방법을 정의한 파일

**Docker를 사용하는 이유:**
- 개발 환경과 운영 환경의 차이로 인한 문제 해결
- 서버 설정을 코드로 관리 가능
- 빠른 배포와 확장 가능

### 2.4 SSH (에스에스에이치)

**SSH란?**
- Secure Shell의 약자
- 원격 서버에 안전하게 접속하는 방법
- 비밀번호 대신 키를 사용해서 더 안전함

---

## 3. 시스템 구축 단계

### 3.1 준비 단계

**필요한 것들:**
- Ubuntu 서버 (20.04 LTS 이상 권장)
- 최소 2GB RAM, 10GB 디스크 공간
- 인터넷 연결

**서버 역할 분담:**
- **Jenkins 서버**: 자동화 작업을 처리하는 서버
- **배포 대상 서버**: 실제 애플리케이션이 실행될 서버

### 3.2 설치 순서

1. **Jenkins 서버 설정**
   - Java 설치
   - Jenkins 설치
   - Docker 설치

2. **Git 저장소 설정**
   - 프로젝트 코드 준비
   - Git 저장소 생성

3. **배포 대상 서버 설정**
   - Docker 설치
   - SSH 키 설정

---

## 4. 실제 설정 방법

### 4.1 Jenkins 서버 설정

#### 4.1.1 Java 설치

```bash
# Java 11 설치
sudo apt install -y openjdk-11-jdk

# Java 버전 확인
java -version
```

#### 4.1.2 Jenkins 설치

```bash
# Jenkins 저장소 키 추가
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -

# Jenkins 저장소 추가
sudo sh -c 'echo "deb http://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list'

# Jenkins 설치
sudo apt update
sudo apt install -y jenkins

# Jenkins 서비스 시작
sudo systemctl start jenkins
sudo systemctl enable jenkins

# Jenkins 상태 확인
sudo systemctl status jenkins
```

#### 4.1.3 Jenkins 초기 설정

1. **브라우저에서 접속**
   - `http://서버IP:8080` 으로 접속

2. **초기 비밀번호 확인**
   ```bash
   sudo cat /var/lib/jenkins/secrets/initialAdminPassword
   ```

3. **필수 플러그인 설치**
   - Git Integration
   - Docker Pipeline
   - SSH Agent
   - Pipeline

4. **관리자 계정 생성**
   - 사용자명과 비밀번호 설정

#### 4.1.4 Docker 설치

```bash
# Docker GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# Jenkins 사용자도 docker 그룹에 추가
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

### 4.2 Git 저장소 설정

#### 4.2.1 프로젝트 준비

**Dockerfile 생성:**
```dockerfile
# Spring Boot 애플리케이션 예시
FROM openjdk:11-jdk-slim

WORKDIR /app

COPY target/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

**Jenkinsfile 생성:**
```groovy
pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'myapp'
        DOCKER_TAG = "${BUILD_NUMBER}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
        
        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }
        
        stage('Docker Build') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} ."
            }
        }
        
        stage('Deploy') {
            steps {
                sh """
                    docker stop ${DOCKER_IMAGE} || true
                    docker rm ${DOCKER_IMAGE} || true
                    docker run -d -p 8080:8080 --name ${DOCKER_IMAGE} ${DOCKER_IMAGE}:${DOCKER_TAG}
                """
            }
        }
    }
}
```

### 4.3 Jenkins 파이프라인 설정

#### 4.3.1 새 파이프라인 생성

1. **Jenkins 대시보드에서 "새 작업" 클릭**
2. **"Pipeline" 선택 후 이름 입력**
3. **"Pipeline" 섹션에서 "Pipeline script from SCM" 선택**
4. **SCM에서 "Git" 선택**
5. **Repository URL 입력**
6. **Script Path에 "Jenkinsfile" 입력**

#### 4.3.2 Git 연동 설정

**SSH 키 생성:**
```bash
# SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "jenkins@server"

#!/bin/bash

# SSH 설정 파일 생성
cat > ~/.ssh/config << EOF
Host remote-server
    HostName remote-server-ip
    User username
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF
```

#### 4.5.2 원격 배포 스크립트

```bash
#!/bin/bash

# Jenkins 로그 확인
sudo tail -f /var/log/jenkins/jenkins.log

# Jenkins 시스템 로그
sudo journalctl -u jenkins -f
```

#### 5.2.2 Docker 로그
```bash
# Docker 데몬 로그
sudo journalctl -u docker -f
```

#### 5.2.3 애플리케이션 로그
```bash

