
## 1. Docker Compose 개념 ✨

Docker Compose는 **docker-compose.yml** 파일을 사용하여 여러 개의 컨테이너를 한 번에 정의하고 실행할 수 있습니다.

✅ **Docker Compose를 사용하면 좋은 이유**
- 여러 개의 컨테이너를 **하나의 설정 파일**로 관리 가능
- **docker-compose up** 한 줄 명령어로 모든 컨테이너 실행 🚀
- 네트워크 설정, 볼륨 마운트, 환경 변수 관리가 쉬움
- **개발 환경과 배포 환경을 동일하게 유지**할 수 있음

---

## 2. Docker Compose 주요 개념 📌

| 키워드 | 설명 |
|--------|------|
| **version** | Docker Compose 파일의 버전을 지정 |
| **services** | 여러 개의 컨테이너를 정의하는 섹션 |
| **image** | 컨테이너가 사용할 Docker 이미지를 지정 |
| **build** | Dockerfile을 이용해 이미지를 직접 빌드 |
| **ports** | 컨테이너 내부와 외부 포트 매핑 |
| **volumes** | 데이터를 지속적으로 유지하기 위한 볼륨 |
| **environment** | 환경 변수를 설정 |
| **depends_on** | 컨테이너 간 실행 순서를 설정 |

---

## 3. 예제: Node.js + MongoDB 애플리케이션 🛠️

아래는 **Node.js 웹 서버와 MongoDB 데이터베이스**를 함께 실행하는 Docker Compose 파일 예제입니다.

📌 **파일명: docker-compose.yml**
```yaml
version: '3.8'  # ✅ 사용 가능한 최신 Docker Compose 버전 지정

services:
  app:  # ✅ Node.js 애플리케이션 서비스 정의
    build: .  # 현재 디렉토리의 Dockerfile을 사용하여 빌드
    ports:
      - "3000:3000"  # 호스트의 3000 포트를 컨테이너의 3000 포트에 연결
    depends_on:
      - mongodb  # MongoDB 컨테이너가 먼저 실행된 후 app 실행
    environment:
      MONGO_URL: "mongodb://mongodb:27017/mydatabase"  # MongoDB 연결 URL

  mongodb:  # ✅ MongoDB 서비스 정의
    image: "mongo:latest"  # 공식 MongoDB 최신 이미지 사용
    ports:
      - "27017:27017"  # 호스트의 27017 포트를 컨테이너의 27017 포트에 연결
    volumes:
      - mongo-data:/data/db  # 데이터 저장을 위한 볼륨 설정

volumes:
  mongo-data:  # ✅ MongoDB 데이터를 유지할 볼륨 설정
```

✅ **설명**:
- `services` 아래 `app`과 `mongodb` 두 개의 컨테이너를 정의
- `app` 서비스는 현재 디렉터리의 `Dockerfile`을 사용하여 빌드
- `depends_on`을 이용하여 **MongoDB가 먼저 실행된 후 Node.js 애플리케이션이 실행**됨
- `environment`를 사용하여 **MongoDB 연결 주소**를 환경 변수로 설정
- `volumes`를 이용하여 **MongoDB 데이터를 영구적으로 저장**

---

## 4. Docker Compose 사용 방법 🏗️

### ✅ **1) Docker Compose 실행**
```sh
docker-compose up -d
```
> `-d` 옵션을 추가하면 **백그라운드에서 실행**됩니다.

---

### ✅ **2) 실행 중인 컨테이너 확인**
```sh
docker-compose ps
```
> 실행 중인 모든 서비스의 상태를 확인할 수 있습니다.

---

### ✅ **3) 컨테이너 로그 확인**
```sh
docker-compose logs -f
```
> `-f` 옵션을 사용하면 **실시간 로그를 확인**할 수 있습니다.

---

### ✅ **4) 실행 중인 컨테이너 중지**
```sh
docker-compose down
```
> 모든 컨테이너를 중지하고 네트워크, 볼륨을 삭제합니다.

---

## 5. Docker Compose 활용 꿀팁 🎯

### ✅ **1) 환경 변수 파일 (.env) 사용**
- **docker-compose.yml** 파일 내에서 환경 변수 파일을 사용할 수 있습니다.

📌 **파일명: .env**
```
MONGO_USER=admin
MONGO_PASSWORD=secret
```

📌 **docker-compose.yml 수정**
```yaml
version: '3.8'

services:
  mongodb:
    image: "mongo:latest"
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
```

✅ **장점**:
- 환경 변수를 **별도의 파일로 관리 가능**
- **보안 강화** (비밀번호나 API 키를 직접 docker-compose.yml에 저장하지 않음)

---

### ✅ **2) 특정 서비스만 실행**
```sh
docker-compose up app
```
> 특정 서비스(`app`)만 실행할 수 있습니다.

---

### ✅ **3) 볼륨 데이터 유지하면서 컨테이너 재시작**
```sh
docker-compose down
docker-compose up -d
```
> `down` 명령어를 사용하면 **컨테이너만 삭제되고 볼륨 데이터는 유지됨**

---

## 6. Docker Compose를 이용한 CI/CD 연동

Docker Compose는 CI/CD 환경에서도 유용하게 활용됩니다.  
예를 들어, GitHub Actions에서 다음과 같이 자동화할 수 있습니다.

📌 **.github/workflows/deploy.yml**
```yaml
name: Deploy

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout 코드
        uses: actions/checkout@v2

      - name: Docker Compose 실행
        run: |
          docker-compose down
          docker-compose up -d --build
```

✅ **이점**:
- GitHub에 코드가 푸시되면 **자동으로 컨테이너를 재시작**
- `--build` 옵션을 추가하여 최신 코드로 이미지 빌드

---

## 7. 결론

Docker Compose를 사용하면 여러 개의 컨테이너를 쉽게 **정의하고 실행**할 수 있습니다.  
또한, 환경 변수를 활용하여 **유지보수가 쉽고 유연한 설정이 가능**합니다.

✅ **이 문서에서 배운 핵심 사항**
1. Docker Compose를 사용하면 **여러 개의 컨테이너를 쉽게 실행**할 수 있음
2. **`docker-compose.yml` 파일을 사용하여 컨테이너 설정**
3. **볼륨, 네트워크, 환경 변수를 활용하여 효율적인 컨테이너 관리**
4. **실전에서 Docker Compose를 활용하는 방법과 CI/CD 연동** 🚀

이제 Docker Compose를 활용하여 **효율적인 컨테이너 환경을 구성**해보세요!

