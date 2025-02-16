# 🐳 Docker 명령어 가이드

## 🎯 Docker란?
Docker는 **컨테이너 기반 가상화 기술**로, 애플리케이션을 **가볍고, 이식성이 뛰어난 컨테이너 환경**에서 실행할 수 있도록 도와줍니다.

---

## 🚀 Docker 기본 명령어
Docker를 사용할 때 자주 사용되는 기본적인 명령어들을 살펴보겠습니다.

---

## 🏗 **Docker 이미지 관련 명령어**
### 📌 `docker build`
```bash
docker build -t myapp:latest .
```
> 🔹 `-t myapp:latest` : 이미지에 `myapp:latest` 태그를 부여  
> 🔹 `.` : 현재 디렉토리에 있는 `Dockerfile`을 사용하여 빌드

Docker 이미지를 **생성(Build)**하는 명령어입니다.

---

### 📌 `docker images`
```bash
docker images
```
> 🔹 현재 로컬에 저장된 모든 Docker 이미지를 출력

| REPOSITORY | TAG  | IMAGE ID | CREATED | SIZE |
|------------|------|----------|---------|------|
| myapp      | latest | 1a2b3c4d5e | 2 days ago | 150MB |

---

### 📌 `docker rmi`
```bash
docker rmi myapp:latest
```
> 🔹 `myapp:latest` 이미지를 삭제  
> 🔹 사용 중인 컨테이너가 있을 경우 삭제되지 않음

강제로 삭제하려면 `-f` 옵션을 추가합니다.
```bash
docker rmi -f myapp:latest
```

---

## 🛠 **Docker 컨테이너 관련 명령어**
### 📌 `docker run`
```bash
docker run -d -p 8080:80 --name mycontainer myapp:latest
```
> 🔹 `-d` : 백그라운드에서 실행  
> 🔹 `-p 8080:80` : 호스트의 8080 포트를 컨테이너의 80 포트와 연결  
> 🔹 `--name mycontainer` : 컨테이너 이름을 `mycontainer`로 지정

이 명령어는 `myapp:latest` 이미지를 기반으로 **새로운 컨테이너를 실행**합니다.

---

### 📌 `docker ps`
```bash
docker ps
```
> 🔹 현재 실행 중인 컨테이너 목록을 출력

모든 컨테이너(중지된 컨테이너 포함)를 확인하려면 `-a` 옵션을 사용합니다.
```bash
docker ps -a
```

---

### 📌 `docker stop`
```bash
docker stop mycontainer
```
> 🔹 실행 중인 `mycontainer` 컨테이너를 중지

---

### 📌 `docker start`
```bash
docker start mycontainer
```
> 🔹 중지된 `mycontainer` 컨테이너를 다시 실행

---

### 📌 `docker restart`
```bash
docker restart mycontainer
```
> 🔹 컨테이너를 **중지 후 다시 시작**

---

### 📌 `docker rm`
```bash
docker rm mycontainer
```
> 🔹 컨테이너 `mycontainer`를 삭제  
> 🔹 컨테이너가 실행 중이면 삭제되지 않음

실행 중인 컨테이너를 강제로 삭제하려면 `-f` 옵션 추가
```bash
docker rm -f mycontainer
```

---

## 📦 **Docker 볼륨 및 네트워크**
### 📌 `docker volume`
Docker 볼륨은 컨테이너 간 **데이터를 공유**하거나 **영속성을 유지**하는 데 사용됩니다.

#### 1️⃣ 볼륨 생성
```bash
docker volume create myvolume
```
> 🔹 `myvolume`이라는 이름의 볼륨을 생성

#### 2️⃣ 볼륨 목록 확인
```bash
docker volume ls
```

#### 3️⃣ 볼륨 삭제
```bash
docker volume rm myvolume
```

---

### 📌 `docker network`
Docker는 기본적으로 여러 네트워크 모드를 제공합니다.

#### 1️⃣ 네트워크 목록 확인
```bash
docker network ls
```

#### 2️⃣ 새로운 네트워크 생성
```bash
docker network create mynetwork
```

#### 3️⃣ 컨테이너를 네트워크에 연결
```bash
docker network connect mynetwork mycontainer
```

#### 4️⃣ 네트워크 삭제
```bash
docker network rm mynetwork
```

---

## 📂 **Docker Compose**
Docker Compose는 여러 개의 컨테이너를 관리할 때 사용됩니다.

### 📌 `docker-compose up`
```bash
docker-compose up -d
```
> 🔹 `docker-compose.yml` 파일을 기반으로 컨테이너 실행  
> 🔹 `-d` 옵션으로 백그라운드 실행

---

### 📌 `docker-compose down`
```bash
docker-compose down
```
> 🔹 `docker-compose.yml`로 실행한 모든 컨테이너 중지 및 삭제

---

## 🔄 **Docker 이미지 저장 및 배포**
### 📌 `docker tag`
```bash
docker tag myapp:latest myrepo/myapp:v1.0
```
> 🔹 로컬 이미지를 `myrepo/myapp:v1.0` 태그로 변경

---

### 📌 `docker push`
```bash
docker push myrepo/myapp:v1.0
```
> 🔹 `myrepo/myapp:v1.0` 이미지를 Docker Hub에 업로드

---

### 📌 `docker pull`
```bash
docker pull myrepo/myapp:v1.0
```
> 🔹 Docker Hub에서 `myrepo/myapp:v1.0` 이미지를 다운로드

