# 🚀 Jenkins, Docker, Git, CI/CD, SSH 자동 배포 가이드

---

## 1. 개요 ✨

이 문서는 **Jenkins**, **Docker**, **Git**, **CI/CD**, **SSH**를 이용한 자동 배포(Deployment)에 대해 설명합니다.

자동 배포를 설정하면 코드 변경이 발생할 때마다 서버에 자동으로 적용되므로 **배포의 효율성과 안정성을 극대화**할 수 있습니다.

---

## 2. 주요 기술 소개

### 2.1 Jenkins 👉🏻

Jenkins는 **CI/CD(Continuous Integration / Continuous Deployment) 자동화 도구**입니다.
- **코드 변경 사항을 감지**하고, **자동으로 테스트와 배포를 수행**합니다.
- 플러그인을 통해 **Docker와 SSH를 활용한 배포 자동화**가 가능합니다.

### 2.2 Docker

Docker는 **컨테이너 기반 가상화 기술**로, 애플리케이션을 어디서든 실행할 수 있도록 해줍니다.
- 한 번 빌드하면 개발/테스트/운영 환경에서 동일하게 동작합니다.

### 2.3 Git

Git은 **분산형 버전 관리 시스템(VCS)**으로, 코드의 변경 사항을 효과적으로 관리할 수 있습니다.
- Jenkins와 함께 사용하면 **코드 변경 사항을 자동으로 감지**하고 배포할 수 있습니다.

### 2.4 CI/CD

CI/CD는 **소프트웨어 개발과 배포를 자동화하는 방법론**입니다.
- **CI(Continuous Integration)**: 코드 변경 사항을 자동으로 빌드 & 테스트
- **CD(Continuous Deployment/Delivery)**: 검증된 코드가 자동으로 서버에 배포

### 2.5 SSH

SSH(Secure Shell)는 원격 서버에 안전하게 접속하기 위한 프로토콜입니다.
- Jenkins가 **원격 서버에 SSH를 통해 접속하여 자동으로 배포**할 수 있습니다.

---

## 3. Jenkins 설치 및 설정

### 3.1 Jenkins 설치

```sh
# Jenkins 설치 (Ubuntu 기준)
sudo apt update
sudo apt install -y openjdk-11-jdk

# Jenkins 다운로드 및 설치
wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
sudo sh -c 'echo "deb http://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list'
sudo apt update
sudo apt install -y jenkins

# Jenkins 실행
sudo systemctl start jenkins
sudo systemctl enable jenkins
```

> 🔹 **설명**
> - `openjdk-11-jdk` : Jenkins는 Java 기반이므로 JDK가 필요합니다.
> - `wget` 및 `apt-key`를 이용해 Jenkins 패키지를 설치합니다.
> - `systemctl`을 이용해 Jenkins를 실행하고 자동 시작되도록 설정합니다.

### 3.2 Jenkins 초기 설정

1. **Jenkins 웹 인터페이스 접속**
    - 브라우저에서 `http://<서버 IP>:8080` 으로 접속합니다.

2. **초기 비밀번호 확인**
   ```sh
   sudo cat /var/lib/jenkins/secrets/initialAdminPassword
   ```
    - 위 명령어 실행 후 표시된 비밀번호를 입력합니다.

3. **플러그인 설치 및 관리자 계정 생성**
    - "Install suggested plugins"를 선택하여 필수 플러그인 설치
    - 관리자 계정(username/password) 생성

---

## 4. Docker 설정

### 4.1 Docker 설치

```sh
# Docker 패키지 설치
sudo apt update
sudo apt install -y docker.io

# Docker 서비스 실행 및 자동 실행 설정
sudo systemctl start docker
sudo systemctl enable docker

# Jenkins가 Docker 명령어를 실행할 수 있도록 추가
sudo usermod -aG docker jenkins
```

> 🔹 **설명**
> - `docker.io` 패키지를 설치하여 Docker를 사용 가능하도록 합니다.
> - `usermod -aG docker jenkins` 를 실행하여 Jenkins가 Docker를 실행할 수 있도록 권한을 부여합니다.

---

## 5. Git 자동 배포 파이프라인 구축

### 5.1 Git 저장소 준비

```sh
# 로컬에 Git 저장소 클론
git clone https://github.com/your-repo/sample-project.git

# Jenkins에서 Git 사용을 위한 플러그인 설치 (웹 UI에서)
# "Manage Jenkins" -> "Plugins Manager" -> "Git Plugin" 설치
```

> 🔹 **설명**
> - Jenkins가 Git 저장소를 추적하여 변경 사항을 감지합니다.

### 5.2 Jenkins에서 Git 연동

1. **Jenkins 웹 UI 접속**
    - `http://<서버 IP>:8080`

2. **새로운 프로젝트 생성**
    - "New Item" 클릭 → "Freestyle Project" 선택

3. **Git 저장소 연동**
    - "Source Code Management" → "Git" 선택
    - Repository URL 입력 (`https://github.com/your-repo/sample-project.git`)

4. **빌드 트리거 설정**
    - "Build Triggers" → "Poll SCM" 활성화 (`H/5 * * * *` 설정 → 5분마다 변경 사항 확인)

### 5.3 배포 스크립트 설정

```sh
#!/bin/bash

# 최신 코드 가져오기
git pull origin main

# Docker 컨테이너 빌드 및 실행
docker build -t sample-app .
docker stop sample-app || true
docker rm sample-app || true
docker run -d --name sample-app -p 8080:8080 sample-app

echo "🚀 배포 완료!"
```

> 🔹 **설명**
> - `git pull` : 최신 코드 가져오기
> - `docker build -t sample-app .` : 새로운 Docker 이미지 빌드
> - 기존 컨테이너를 중지 및 삭제 후 새로운 컨테이너 실행

---

## 6. SSH를 통한 원격 배포

### 6.1 SSH 키 생성

```sh
# SSH 키 생성 (Jenkins 서버에서 실행)
ssh-keygen -t rsa -b 4096 -C "jenkins@server"
```

> 🔹 **설명**
> - SSH 키를 생성하여 원격 서버에 자동으로 로그인 가능하게 설정

### 6.2 원격 서버에 공개 키 추가

```sh
cat ~/.ssh/id_rsa.pub | ssh user@remote-server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

> 🔹 **설명**
> - Jenkins 서버의 SSH 키를 원격 서버에 등록하여 비밀번호 없이 접근 가능하도록 설정

### 6.3 Jenkins에서 SSH 실행

```sh
# 배포 스크립트 실행 (Jenkins에서)
ssh user@remote-server "cd /path/to/project && git pull && ./deploy.sh"
```

> 🔹 **설명**
> - Jenkins가 원격 서버에 SSH 접속하여 배포 스크립트를 실행합니다.

