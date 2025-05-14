# 🚀 Jenkins, Docker, Git, CI/CD, SSH 자동 배포 가이드

---

## 1. 개요 ✨

이 문서는 **Jenkins**, **Docker**, **Git**, **CI/CD**, **SSH**를 이용한 자동 배포(Deployment) 시스템 구축에 대해 상세히 설명합니다.

### 1.1 자동 배포의 장점
- **시간 절약**: 수동 배포 과정을 자동화하여 개발자의 시간을 절약
- **인적 오류 감소**: 배포 과정에서 발생할 수 있는 실수를 최소화
- **일관성**: 모든 환경(개발, 테스트, 운영)에서 동일한 방식으로 배포
- **빠른 롤백**: 문제 발생 시 이전 버전으로 즉시 복구 가능
- **배포 이력 관리**: 모든 배포 과정이 기록되어 추적 가능

### 1.2 시스템 아키텍처
```
[개발자] → [Git Repository] → [Jenkins Server] → [Docker Registry] → [Production Server]
   ↑            ↓                    ↓                    ↓                    ↓
   └────────────┴────────────────────┴────────────────────┴────────────────────┘
                    자동화된 CI/CD 파이프라인
```

---

## 2. 주요 기술 소개

### 2.1 Jenkins 👉🏻

Jenkins는 **CI/CD(Continuous Integration / Continuous Deployment) 자동화 도구**입니다.

#### 2.1.1 Jenkins의 주요 기능
- **빌드 자동화**: 코드 변경 시 자동으로 빌드 수행
- **테스트 자동화**: 단위 테스트, 통합 테스트 자동 실행
- **배포 자동화**: 테스트 통과 시 자동으로 서버에 배포
- **모니터링**: 빌드/배포 상태 실시간 모니터링
- **알림**: Slack, Email 등을 통한 빌드/배포 상태 알림

#### 2.1.2 Jenkins 파이프라인
```groovy
pipeline {
    agent any
    stages {
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
        stage('Deploy') {
            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

### 2.2 Docker

Docker는 **컨테이너 기반 가상화 기술**입니다.

#### 2.2.1 Docker의 핵심 개념
- **이미지(Image)**: 애플리케이션 실행에 필요한 모든 파일이 포함된 템플릿
- **컨테이너(Container)**: 이미지를 실행한 인스턴스
- **Dockerfile**: 이미지 생성 방법을 정의한 파일
- **Docker Hub**: 공개 Docker 이미지 저장소

#### 2.2.2 Dockerfile 예시
```dockerfile
# 베이스 이미지 선택
FROM openjdk:11-jdk-slim

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션 파일 복사
COPY target/*.jar app.jar

# 포트 설정
EXPOSE 8080

# 실행 명령
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### 2.3 Git

Git은 **분산형 버전 관리 시스템(VCS)**입니다.

#### 2.3.1 Git 워크플로우
1. **Feature Branch Workflow**
   ```
   main
     ├── feature/login
     ├── feature/payment
     └── feature/user-profile
   ```

2. **Git Flow**
   ```
   main
     ├── develop
     │   ├── feature/login
     │   └── feature/payment
     ├── release/v1.0
     └── hotfix/security-patch
   ```

### 2.4 CI/CD

CI/CD는 **소프트웨어 개발과 배포를 자동화하는 방법론**입니다.

#### 2.4.1 CI(Continuous Integration) 프로세스
1. 코드 커밋
2. 자동 빌드
3. 단위 테스트
4. 통합 테스트
5. 코드 품질 검사

#### 2.4.2 CD(Continuous Deployment) 프로세스
1. 테스트 통과 확인
2. 스테이징 환경 배포
3. 자동화된 테스트
4. 프로덕션 환경 배포
5. 모니터링 및 알림

### 2.5 SSH

SSH는 **안전한 원격 접속 프로토콜**입니다.

#### 2.5.1 SSH 주요 기능
- **암호화된 통신**: 모든 데이터가 암호화되어 전송
- **키 기반 인증**: 비밀번호 대신 SSH 키로 인증
- **포트 포워딩**: 안전한 터널링 제공
- **X11 포워딩**: GUI 애플리케이션 원격 실행

---

## 3. Jenkins 설치 및 설정

### 3.1 Jenkins 설치

#### 3.1.1 시스템 요구사항
- **하드웨어**: 최소 2GB RAM, 10GB 디스크 공간
- **운영체제**: Ubuntu 20.04 LTS 이상
- **Java**: OpenJDK 11 이상

#### 3.1.2 설치 과정
```sh
# 시스템 업데이트
sudo apt update
sudo apt upgrade -y

# Java 설치
sudo apt install -y openjdk-11-jdk

# Jenkins 저장소 추가
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
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

#### 3.1.3 방화벽 설정
```sh
# Jenkins 포트(8080) 개방
sudo ufw allow 8080/tcp
sudo ufw status
```

### 3.2 Jenkins 초기 설정

#### 3.2.1 초기 접속
1. 브라우저에서 `http://<서버 IP>:8080` 접속
2. 초기 비밀번호 확인
   ```sh
   sudo cat /var/lib/jenkins/secrets/initialAdminPassword
   ```

#### 3.2.2 필수 플러그인 설치
- **Git Integration**: Git 저장소 연동
- **Docker Pipeline**: Docker 컨테이너 빌드/배포
- **SSH Agent**: SSH를 통한 원격 서버 접속
- **Pipeline**: 파이프라인 스크립트 작성
- **Blue Ocean**: 시각적 파이프라인 편집기

#### 3.2.3 관리자 계정 설정
1. 사용자 이름 설정
2. 비밀번호 설정 (최소 8자, 특수문자 포함)
3. 이메일 주소 입력

---

## 4. Docker 설정

### 4.1 Docker 설치

#### 4.1.1 Docker 설치 과정
```sh
# 이전 버전 제거
sudo apt remove docker docker-engine docker.io containerd runc

# 필수 패키지 설치
sudo apt update
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Docker 공식 GPG 키 추가
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
```

#### 4.1.2 Docker 권한 설정
```sh
# Jenkins 사용자를 docker 그룹에 추가
sudo usermod -aG docker jenkins

# Jenkins 서비스 재시작
sudo systemctl restart jenkins
```

### 4.2 Docker 기본 명령어

#### 4.2.1 이미지 관리
```sh
# 이미지 목록 확인
docker images

# 이미지 빌드
docker build -t myapp:1.0 .

# 이미지 삭제
docker rmi myapp:1.0
```

#### 4.2.2 컨테이너 관리
```sh
# 컨테이너 실행
docker run -d -p 8080:8080 --name myapp myapp:1.0

# 컨테이너 목록 확인
docker ps -a

# 컨테이너 중지
docker stop myapp

# 컨테이너 삭제
docker rm myapp
```

---

## 5. Git 자동 배포 파이프라인 구축

### 5.1 Git 저장소 준비

#### 5.1.1 Git 저장소 초기화
```sh
# 새 저장소 생성
git init

# 원격 저장소 추가
git remote add origin https://github.com/username/repository.git

# 기본 브랜치 설정
git branch -M main
```

#### 5.1.2 .gitignore 설정
```gitignore
# IDE 설정 파일
.idea/
.vscode/

# 빌드 결과물
target/
build/
dist/

# 환경 설정 파일
.env
application-*.properties

# 로그 파일
*.log
```

### 5.2 Jenkins 파이프라인 설정

#### 5.2.1 파이프라인 스크립트
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
    
    post {
        always {
            cleanWs()
        }
        success {
            echo '배포 성공!'
        }
        failure {
            echo '배포 실패!'
        }
    }
}
```

### 5.3 배포 스크립트

#### 5.3.1 deploy.sh
```bash
#!/bin/bash

# 환경 변수 설정
APP_NAME="myapp"
DOCKER_IMAGE="myapp"
DOCKER_TAG=$(git rev-parse --short HEAD)

# 이전 컨테이너 정리
echo "Cleaning up previous containers..."
docker stop $APP_NAME || true
docker rm $APP_NAME || true

# 새 이미지 빌드
echo "Building new Docker image..."
docker build -t $DOCKER_IMAGE:$DOCKER_TAG .

# 새 컨테이너 실행
echo "Starting new container..."
docker run -d \
    --name $APP_NAME \
    -p 8080:8080 \
    -e SPRING_PROFILES_ACTIVE=prod \
    $DOCKER_IMAGE:$DOCKER_TAG

# 헬스 체크
echo "Performing health check..."
for i in {1..30}; do
    if curl -s http://localhost:8080/actuator/health | grep -q "UP"; then
        echo "Application is up and running!"
        exit 0
    fi
    sleep 2
done

echo "Health check failed!"
exit 1
```

---

## 6. SSH를 통한 원격 배포

### 6.1 SSH 키 설정

#### 6.1.1 SSH 키 생성
```sh
# SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "jenkins@server"

# 키 권한 설정
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

#### 6.1.2 원격 서버 설정
```sh
# 원격 서버에 SSH 키 복사
ssh-copy-id -i ~/.ssh/id_rsa.pub user@remote-server

# SSH 설정 파일 생성
cat > ~/.ssh/config << EOF
Host remote-server
    HostName remote-server-ip
    User username
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF
```

### 6.2 원격 배포 스크립트

#### 6.2.1 remote-deploy.sh
```bash
#!/bin/bash

# 환경 변수
REMOTE_SERVER="remote-server"
REMOTE_PATH="/opt/applications"
APP_NAME="myapp"

# 원격 서버에 배포
ssh $REMOTE_SERVER << EOF
    # 작업 디렉토리로 이동
    cd $REMOTE_PATH

    # 최신 코드 가져오기
    git pull origin main

    # 이전 컨테이너 정리
    docker stop $APP_NAME || true
    docker rm $APP_NAME || true

    # 새 이미지 빌드
    docker build -t $APP_NAME:latest .

    # 새 컨테이너 실행
    docker run -d \
        --name $APP_NAME \
        -p 8080:8080 \
        -e SPRING_PROFILES_ACTIVE=prod \
        $APP_NAME:latest

    # 배포 로그 확인
    docker logs -f $APP_NAME
EOF
```

### 6.3 모니터링 및 알림

#### 6.3.1 Slack 알림 설정
```groovy
pipeline {
    // ... 기존 파이프라인 설정 ...
    
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
}
```

---

## 7. 문제 해결 및 모니터링

### 7.1 일반적인 문제 해결

#### 7.1.1 Jenkins 문제
- **빌드 실패**: 로그 확인 및 권한 문제 체크
- **플러그인 오류**: 플러그인 재설치 및 버전 호환성 확인
- **메모리 부족**: JVM 힙 메모리 설정 조정

#### 7.1.2 Docker 문제
- **이미지 빌드 실패**: Dockerfile 문법 및 의존성 확인
- **컨테이너 실행 오류**: 포트 충돌 및 리소스 제한 확인
- **네트워크 문제**: Docker 네트워크 설정 확인

### 7.2 모니터링 도구

#### 7.2.1 시스템 모니터링
- **Prometheus**: 메트릭 수집
- **Grafana**: 시각화 대시보드
- **ELK Stack**: 로그 분석

#### 7.2.2 애플리케이션 모니터링
- **Spring Boot Actuator**: 애플리케이션 상태 모니터링
- **New Relic**: APM(Application Performance Monitoring)
- **Datadog**: 통합 모니터링

---

## 8. 보안 고려사항

### 8.1 Jenkins 보안
- **역할 기반 접근 제어(RBAC)** 설정
- **API 토큰** 사용
- **보안 플러그인** 설치

### 8.2 Docker 보안
- **이미지 스캔** 도구 사용
- **보안 베이스 이미지** 사용
- **컨테이너 리소스 제한** 설정

### 8.3 Git 보안
- **SSH 키** 관리
- **접근 권한** 설정
- **시크릿 관리** 도구 사용

---

## 9. 결론

이 가이드를 통해 Jenkins, Docker, Git을 활용한 자동 배포 시스템을 구축할 수 있습니다. 각 단계를 따라 설정하고, 필요에 따라 커스터마이징하여 사용하시기 바랍니다.

### 9.1 추가 학습 자료
- [Jenkins 공식 문서](https://www.jenkins.io/doc/)
- [Docker 공식 문서](https://docs.docker.com/)
- [Git 공식 문서](https://git-scm.com/doc)

### 9.2 참고 사항
- 정기적인 백업 수행
- 보안 업데이트 적용
- 모니터링 시스템 구축
- 문서화 유지

