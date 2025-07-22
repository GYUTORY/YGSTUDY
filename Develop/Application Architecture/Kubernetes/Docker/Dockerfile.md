# Dockerfile 완전 가이드

## Dockerfile이란?

Dockerfile은 Docker 이미지를 만들기 위한 **설명서**입니다. 마치 요리 레시피처럼, 어떤 재료(베이스 이미지)를 사용하고, 어떤 순서로 작업(명령어)을 수행할지 단계별로 작성합니다.

### Docker 이미지와 컨테이너의 관계

- **Docker 이미지**: 애플리케이션과 그 실행에 필요한 모든 파일들이 담긴 패키지
- **Docker 컨테이너**: 이미지를 실행한 상태 (실제로 동작하는 애플리케이션)
- **Dockerfile**: 이미지를 만드는 방법을 정의한 텍스트 파일

### 왜 Dockerfile을 사용할까?

1. **환경 일관성**: 개발자의 컴퓨터와 서버에서 동일한 환경으로 실행
2. **배포 간편성**: 애플리케이션과 필요한 모든 것을 하나의 패키지로 묶어서 배포
3. **확장성**: 같은 이미지로 여러 개의 컨테이너를 쉽게 실행
4. **버전 관리**: 애플리케이션의 실행 환경까지 코드로 관리

---

## Dockerfile 기본 명령어

### FROM - 시작점 설정
```dockerfile
FROM node:16
```
- 어떤 이미지를 기반으로 시작할지 정합니다
- 마치 "이미 만들어진 도구상자에서 시작하겠다"는 의미

### WORKDIR - 작업 폴더 설정
```dockerfile
WORKDIR /usr/src/app
```
- 컨테이너 안에서 작업할 폴더를 지정합니다
- 이후의 모든 명령어는 이 폴더에서 실행됩니다

### COPY - 파일 복사
```dockerfile
COPY package*.json ./
COPY . .
```
- 호스트(내 컴퓨터)의 파일을 컨테이너 안으로 복사합니다
- `package*.json`은 package.json과 package-lock.json을 의미합니다

### RUN - 명령어 실행
```dockerfile
RUN npm install
```
- 컨테이너 안에서 명령어를 실행합니다
- 주로 패키지 설치나 파일 생성에 사용됩니다

### EXPOSE - 포트 설정
```dockerfile
EXPOSE 8080
```
- 이 컨테이너가 어떤 포트를 사용할지 알려줍니다
- 실제 포트 연결은 `docker run`에서 설정합니다

### CMD - 실행 명령어
```dockerfile
CMD ["node", "server.js"]
```
- 컨테이너가 시작될 때 실행할 명령어를 지정합니다
- 애플리케이션을 시작하는 명령어를 여기에 작성합니다

---

## 실제 예제로 이해하기

Node.js 웹 애플리케이션을 위한 Dockerfile을 단계별로 살펴보겠습니다.

```dockerfile
# 1단계: Node.js 16 버전을 기반으로 시작
FROM node:16

# 2단계: 작업할 폴더를 설정
WORKDIR /usr/src/app

# 3단계: 패키지 정보 파일만 먼저 복사
COPY package*.json ./

# 4단계: 필요한 패키지들을 설치
RUN npm install

# 5단계: 애플리케이션 코드를 모두 복사
COPY . .

# 6단계: 8080번 포트를 사용한다고 알림
EXPOSE 8080

# 7단계: 컨테이너 시작 시 서버 실행
CMD ["node", "server.js"]
```

### 각 단계의 의미

1. **FROM node:16**: Node.js 16 버전이 설치된 환경에서 시작
2. **WORKDIR /usr/src/app**: 컨테이너 안의 작업 폴더를 `/usr/src/app`으로 설정
3. **COPY package*.json ./**: package.json과 package-lock.json을 먼저 복사
4. **RUN npm install**: 필요한 npm 패키지들을 설치
5. **COPY . .**: 현재 폴더의 모든 파일을 컨테이너로 복사
6. **EXPOSE 8080**: 이 애플리케이션은 8080번 포트를 사용한다고 표시
7. **CMD ["node", "server.js"]**: 컨테이너가 시작되면 `node server.js` 명령어 실행

---

## 효율적인 Dockerfile 작성법

### 1. 캐시를 활용한 빌드 최적화

Docker는 각 명령어를 실행한 결과를 캐시에 저장합니다. 다음 빌드 시 변경되지 않은 부분은 캐시를 재사용하여 빌드 시간을 단축할 수 있습니다.

**잘못된 방법:**
```dockerfile
COPY . .           # 모든 파일을 먼저 복사
RUN npm install    # 그 다음에 패키지 설치
```

**올바른 방법:**
```dockerfile
COPY package*.json ./  # 패키지 파일만 먼저 복사
RUN npm install        # 패키지 설치 (캐시 가능)
COPY . .               # 나머지 파일 복사
```

이렇게 하면 소스 코드가 변경되어도 `npm install` 단계는 캐시를 재사용할 수 있습니다.

### 2. 이미지 크기 줄이기

**Alpine Linux 사용:**
```dockerfile
FROM node:16-alpine  # 일반 node:16보다 훨씬 작음
```

**불필요한 파일 제외:**
`.dockerignore` 파일을 만들어서 복사하지 않을 파일들을 지정합니다.
```
node_modules
npm-debug.log
.git
.env
```

### 3. 다단계 빌드 (Multi-stage Build)

빌드 과정과 실행 환경을 분리하여 최종 이미지 크기를 줄일 수 있습니다.

```dockerfile
# 빌드 단계
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 실행 단계
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/server.js"]
```

이 방법의 장점:
- 빌드 도구들이 최종 이미지에 포함되지 않음
- 최종 이미지 크기가 작아짐
- 보안상 더 안전함

---

## Dockerfile 사용하기

### 1. 이미지 빌드
```bash
docker build -t my-app .
```
- `-t my-app`: 이미지 이름을 'my-app'으로 지정
- `.`: 현재 폴더의 Dockerfile 사용

### 2. 컨테이너 실행
```bash
docker run -p 3000:8080 my-app
```
- `-p 3000:8080`: 호스트의 3000번 포트를 컨테이너의 8080번 포트와 연결
- `my-app`: 실행할 이미지 이름

### 3. 실행 중인 컨테이너 확인
```bash
docker ps
```

### 4. 컨테이너 중지
```bash
docker stop [컨테이너_ID]
```

---

## 주의사항과 팁

### 1. 보안 고려사항
- 최신 버전의 베이스 이미지 사용
- 불필요한 패키지 설치 금지
- 민감한 정보는 환경 변수로 관리

### 2. 성능 최적화
- 레이어 수를 최소화
- 캐시를 활용한 빌드 최적화
- 적절한 베이스 이미지 선택

### 3. 디버깅
- `docker logs [컨테이너_ID]`: 컨테이너 로그 확인
- `docker exec -it [컨테이너_ID] /bin/bash`: 컨테이너 내부 접속

---

## 마무리

Dockerfile은 처음에는 복잡해 보일 수 있지만, 기본 개념을 이해하면 매우 유용한 도구입니다. 

주요 포인트:
- Dockerfile은 이미지를 만드는 레시피
- 각 명령어는 하나의 레이어를 생성
- 캐시를 활용하여 빌드 시간 단축
- 보안과 성능을 고려한 작성

실습을 통해 익숙해지면, 애플리케이션 배포가 훨씬 간편해질 것입니다.
