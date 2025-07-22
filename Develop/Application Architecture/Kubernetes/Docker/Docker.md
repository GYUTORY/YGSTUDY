# 🐳 Docker 완전 가이드

> **Docker란?**  
> 애플리케이션을 독립적인 환경에서 실행할 수 있게 해주는 컨테이너 기술입니다.

---

## 📋 목차
- [Docker가 필요한 이유](#-docker가-필요한-이유)
- [Docker의 핵심 개념](#-docker의-핵심-개념)
- [가상머신 vs Docker](#-가상머신-vs-docker)
- [Docker 설치 및 기본 사용법](#-docker-설치-및-기본-사용법)
- [Dockerfile 작성하기](#-dockerfile-작성하기)
- [Docker Compose 사용하기](#-docker-compose-사용하기)
- [실무 활용 팁](#-실무-활용-팁)

---

## 🤔 Docker가 필요한 이유

### 기존 개발 환경의 문제점

#### 1. **"내 컴퓨터에서는 잘 되는데..." 문제**
```
개발자 A: "내 로컬에서는 정상 작동하는데요?"
운영자: "서버에서는 오류가 발생하고 있습니다."
```

**문제 상황:**
- 개발자의 PC: Windows + Node.js 16 + MySQL 8.0
- 서버 환경: Linux + Node.js 14 + MySQL 5.7
- 결과: 환경 차이로 인한 오류 발생

#### 2. **의존성 충돌 문제**
```
프로젝트 A: React 18.0.0 필요
프로젝트 B: React 17.0.0 필요
→ 같은 PC에서 두 프로젝트를 동시에 개발하기 어려움
```

#### 3. **배포 과정의 복잡성**
```
기존 배포 과정:
1. 서버에 Node.js 설치
2. MySQL 설치 및 설정
3. 환경 변수 설정
4. 애플리케이션 코드 업로드
5. 의존성 설치
6. 서비스 시작
→ 각 단계마다 오류 가능성 존재
```

---

## 🧠 Docker의 핵심 개념

### 📦 컨테이너(Container)란?

**간단한 비유:**  
컨테이너는 **"이동식 집"**과 같습니다. 필요한 모든 것(가구, 전자제품, 생활용품)을 집 안에 넣어두고, 어디든 옮겨서 바로 살 수 있게 만든 것입니다.

**기술적 정의:**
- 애플리케이션과 그 실행에 필요한 모든 파일을 하나로 묶은 패키지
- 운영체제와 독립적으로 실행되는 격리된 환경

### 🖼️ 이미지(Image)란?

**간단한 비유:**  
이미지는 **"집 설계도"**와 같습니다. 설계도를 보고 실제 집(컨테이너)을 지을 수 있습니다.

**기술적 정의:**
- 컨테이너를 만들기 위한 템플릿
- 애플리케이션 코드, 런타임, 라이브러리, 설정 파일 등을 포함한 읽기 전용 파일

### 🔄 이미지와 컨테이너의 관계

```
이미지 (설계도) → 컨테이너 (실제 집)
     ↓                    ↓
정적인 파일          동적으로 실행 중인 인스턴스
```

**예시:**
```bash
# nginx 이미지로부터 컨테이너 생성
docker run nginx

# 같은 이미지로 여러 컨테이너 생성 가능
docker run nginx  # 컨테이너 1
docker run nginx  # 컨테이너 2
docker run nginx  # 컨테이너 3
```

---

## ⚖️ 가상머신 vs Docker

### 가상머신(VM)의 구조
```
┌─────────────────────────────────────┐
│           애플리케이션 A            │
├─────────────────────────────────────┤
│           게스트 OS A               │
├─────────────────────────────────────┤
│           하이퍼바이저              │
├─────────────────────────────────────┤
│           호스트 OS                 │
├─────────────────────────────────────┤
│           하드웨어                  │
└─────────────────────────────────────┘
```

### Docker 컨테이너의 구조
```
┌─────────────────────────────────────┐
│    컨테이너 A    │    컨테이너 B    │
├─────────────────────────────────────┤
│           Docker Engine             │
├─────────────────────────────────────┤
│           호스트 OS                 │
├─────────────────────────────────────┤
│           하드웨어                  │
└─────────────────────────────────────┘
```

### 비교표

| 구분 | 가상머신 | Docker 컨테이너 |
|------|----------|-----------------|
| **크기** | 수 GB ~ 수십 GB | 수 MB ~ 수백 MB |
| **시작 시간** | 수 분 | 수 초 |
| **리소스 사용량** | 높음 | 낮음 |
| **격리 수준** | 완전 격리 | 프로세스 레벨 격리 |
| **이미지 크기** | 크다 | 작다 |
| **성능** | 상대적으로 느림 | 빠름 |

---

## 🛠️ Docker 설치 및 기본 사용법

### 1. Docker 설치

#### Windows
1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop) 다운로드
2. 설치 파일 실행
3. WSL 2 설치 (필요시)
4. 재부팅 후 Docker Desktop 실행

#### macOS
1. [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop) 다운로드
2. 설치 파일 실행
3. Docker Desktop 실행

#### Linux (Ubuntu)
```bash
# 패키지 업데이트
sudo apt update

# 필요한 패키지 설치
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Docker GPG 키 추가
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가 (sudo 없이 사용하기 위해)
sudo usermod -aG docker $USER
```

### 2. 기본 명령어

#### 이미지 관련
```bash
# 이미지 검색
docker search nginx

# 이미지 다운로드
docker pull nginx

# 이미지 목록 확인
docker images

# 이미지 삭제
docker rmi nginx
```

#### 컨테이너 관련
```bash
# 컨테이너 실행
docker run nginx

# 백그라운드에서 컨테이너 실행
docker run -d nginx

# 포트 매핑 (호스트:컨테이너)
docker run -d -p 8080:80 nginx

# 컨테이너 이름 지정
docker run -d --name my-nginx nginx

# 실행 중인 컨테이너 목록
docker ps

# 모든 컨테이너 목록 (종료된 것 포함)
docker ps -a

# 컨테이너 중지
docker stop <컨테이너_ID>

# 컨테이너 삭제
docker rm <컨테이너_ID>

# 컨테이너 로그 확인
docker logs <컨테이너_ID>

# 컨테이너 내부 접속
docker exec -it <컨테이너_ID> /bin/bash
```

### 3. 실습 예제

#### 웹 서버 실행하기
```bash
# 1. nginx 이미지 다운로드
docker pull nginx

# 2. nginx 컨테이너 실행 (포트 8080으로 접근)
docker run -d -p 8080:80 --name my-web nginx

# 3. 브라우저에서 http://localhost:8080 접속
# 4. nginx 기본 페이지 확인

# 5. 컨테이너 상태 확인
docker ps

# 6. 컨테이너 중지 및 삭제
docker stop my-web
docker rm my-web
```

---

## 📝 Dockerfile 작성하기

### Dockerfile이란?
컨테이너 이미지를 만들기 위한 **설정 파일**입니다. 마치 요리 레시피처럼 "어떤 재료를 사용하고, 어떤 순서로 조리할지"를 정의합니다.

### 기본 문법

#### FROM
```dockerfile
FROM node:16
```
**의미:** "Node.js 16 버전을 기반으로 시작하겠다"

#### WORKDIR
```dockerfile
WORKDIR /app
```
**의미:** "컨테이너 내부에서 작업할 디렉토리를 /app으로 설정하겠다"

#### COPY
```dockerfile
COPY . .
```
**의미:** "현재 디렉토리의 모든 파일을 컨테이너의 현재 디렉토리로 복사하겠다"

#### RUN
```dockerfile
RUN npm install
```
**의미:** "컨테이너를 빌드할 때 이 명령어를 실행하겠다"

#### CMD
```dockerfile
CMD ["node", "app.js"]
```
**의미:** "컨테이너가 시작될 때 이 명령어를 실행하겠다"

### 실제 예제

#### Node.js 애플리케이션용 Dockerfile
```dockerfile
# 1. 베이스 이미지 선택
FROM node:16-alpine

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. package.json과 package-lock.json 복사
COPY package*.json ./

# 4. 의존성 설치
RUN npm ci --only=production

# 5. 애플리케이션 코드 복사
COPY . .

# 6. 포트 노출
EXPOSE 3000

# 7. 애플리케이션 실행
CMD ["node", "app.js"]
```

#### Python 애플리케이션용 Dockerfile
```dockerfile
# 1. 베이스 이미지 선택
FROM python:3.9-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. requirements.txt 복사
COPY requirements.txt .

# 4. 의존성 설치
RUN pip install -r requirements.txt

# 5. 애플리케이션 코드 복사
COPY . .

# 6. 포트 노출
EXPOSE 5000

# 7. 애플리케이션 실행
CMD ["python", "app.py"]
```

### 이미지 빌드 및 실행
```bash
# 이미지 빌드
docker build -t my-app .

# 컨테이너 실행
docker run -d -p 3000:3000 my-app
```

---

## 🚀 Docker Compose 사용하기

### Docker Compose란?
여러 컨테이너를 **하나의 파일로 관리**할 수 있게 해주는 도구입니다. 웹 애플리케이션, 데이터베이스, 캐시 서버 등을 함께 실행할 때 유용합니다.

### 기본 문법

#### version
```yaml
version: '3.8'
```
**의미:** "Docker Compose 파일 형식의 버전을 지정"

#### services
```yaml
services:
  web:
    # 웹 서비스 설정
  db:
    # 데이터베이스 서비스 설정
```
**의미:** "실행할 서비스들을 정의"

#### image
```yaml
image: nginx:latest
```
**의미:** "사용할 Docker 이미지를 지정"

#### ports
```yaml
ports:
  - "8080:80"
```
**의미:** "호스트의 8080 포트를 컨테이너의 80 포트와 연결"

#### volumes
```yaml
volumes:
  - ./data:/var/lib/mysql
```
**의미:** "호스트의 ./data 디렉토리를 컨테이너의 /var/lib/mysql과 연결"

#### environment
```yaml
environment:
  - MYSQL_ROOT_PASSWORD=password
  - MYSQL_DATABASE=myapp
```
**의미:** "환경 변수를 설정"

### 실제 예제

#### 웹 애플리케이션 + MySQL
```yaml
# docker-compose.yml
version: '3.8'

services:
  # 웹 애플리케이션
  web:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=db
      - DB_USER=root
      - DB_PASSWORD=password
      - DB_NAME=myapp
    depends_on:
      - db

  # MySQL 데이터베이스
  db:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=myapp
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

#### 실행 방법
```bash
# 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs web
```

---

## 💡 실무 활용 팁

### 1. 멀티 스테이지 빌드
```dockerfile
# 빌드 스테이지
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 실행 스테이지
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. 환경별 설정
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
    volumes:
      - .:/app
      - /app/node_modules
```

### 3. 데이터 영속성
```yaml
volumes:
  - ./logs:/app/logs          # 로그 파일
  - ./uploads:/app/uploads    # 업로드 파일
  - postgres_data:/var/lib/postgresql/data  # 데이터베이스
```

### 4. 네트워크 설정
```yaml
networks:
  frontend:
  backend:

services:
  web:
    networks:
      - frontend
      - backend
  db:
    networks:
      - backend
```

---

## 🔍 자주 묻는 질문

### Q1: Docker와 가상머신의 차이점은?
**A:** 가상머신은 전체 운영체제를 가상화하지만, Docker는 애플리케이션 레벨에서 격리합니다. 따라서 더 가볍고 빠릅니다.

### Q2: 컨테이너를 삭제하면 데이터가 사라지나요?
**A:** 기본적으로는 사라집니다. 데이터를 보존하려면 볼륨(volume)을 사용해야 합니다.

### Q3: Docker Hub는 무엇인가요?
**A:** Docker 이미지를 공유하고 다운로드할 수 있는 공개 저장소입니다. GitHub와 비슷한 개념입니다.

### Q4: 컨테이너가 너무 많아지면 어떻게 관리하나요?
**A:** Docker Compose, Docker Swarm, Kubernetes 등을 사용하여 컨테이너 오케스트레이션을 할 수 있습니다.

---
## 🎯 마무리

Docker는 현대 개발에서 **필수적인 기술**입니다. 처음에는 복잡해 보일 수 있지만, 기본 개념을 이해하고 실습을 통해 익숙해지면 개발 효율성을 크게 향상시킬 수 있습니다.
