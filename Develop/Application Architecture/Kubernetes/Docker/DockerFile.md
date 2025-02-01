

## 1. Dockerfile 개요 ✨

Dockerfile은 **텍스트 기반의 명령어 스크립트**로서, **Docker 이미지**를 빌드하는 데 사용됩니다.  
각 명령어는 하나의 **레이어(Layer)** 를 형성하며, 이러한 레이어를 조합하여 최종 Docker 이미지를 만듭니다.

✅ **Dockerfile을 사용하면 얻을 수 있는 장점**
- 개발 환경과 배포 환경의 **일관성 유지** 🚀
- 의존성을 포함하여 배포가 쉬워짐
- **CI/CD 자동화**와 연계 가능
- 컨테이너를 활용하여 **가볍고 빠른 배포 가능**

---

## 2. Dockerfile 주요 명령어 정리 📌

| 명령어 | 설명 |
|--------|------|
| **FROM** | 베이스 이미지를 설정합니다. |
| **RUN** | 컨테이너 내에서 명령어를 실행합니다. |
| **CMD** | 컨테이너가 실행될 때 수행할 명령을 지정합니다. |
| **LABEL** | 이미지에 메타데이터를 추가합니다. |
| **EXPOSE** | 컨테이너가 사용할 포트를 지정합니다. |
| **ENV** | 환경 변수를 설정합니다. |
| **ADD / COPY** | 호스트 시스템에서 컨테이너 내부로 파일을 복사합니다. |
| **ENTRYPOINT** | 컨테이너 실행 시 항상 수행할 명령을 지정합니다. |
| **WORKDIR** | 작업 디렉터리를 지정합니다. |

---

## 3. 예제 Dockerfile 🚀

아래는 **Node.js 기반 웹 애플리케이션**을 위한 Dockerfile 예제입니다.  
각 명령어에 대한 상세한 설명을 주석으로 달았습니다.

```dockerfile
# 1️⃣ Node.js 16 버전을 기반으로 컨테이너를 생성합니다.
FROM node:16

# 2️⃣ 유지보수자를 명시하여 Docker 이미지 정보에 포함시킵니다.
LABEL maintainer="your-email@example.com"

# 3️⃣ 컨테이너 내부에서 작업할 디렉터리를 생성 및 설정합니다.
WORKDIR /usr/src/app

# 4️⃣ 패키지 파일(package.json, package-lock.json)만 먼저 복사하여 캐싱을 활용합니다.
COPY package*.json ./

# 5️⃣ npm을 사용하여 의존성을 설치합니다.
RUN npm install

# 6️⃣ 현재 디렉터리의 모든 파일을 컨테이너 내부로 복사합니다.
COPY . .

# 7️⃣ 애플리케이션이 실행될 포트를 설정합니다.
EXPOSE 8080

# 8️⃣ 컨테이너 실행 시 서버를 실행하는 명령어를 지정합니다.
CMD [ "node", "server.js" ]
```

✅ **위의 예제에서 핵심 포인트**
- `FROM node:16` → 최신 Node.js 버전보다 안정적인 특정 버전을 선택하는 것이 좋습니다.
- `WORKDIR /usr/src/app` → 작업 디렉터리를 설정하여 파일 복사가 깔끔하게 이루어집니다.
- `COPY package*.json ./` → 패키지 파일만 먼저 복사하여 **캐싱(Cache) 효과**를 극대화합니다.
- `RUN npm install` → 의존성 설치 후 **새로운 레이어를 생성**하여 재사용성을 높입니다.
- `CMD [ "node", "server.js" ]` → 컨테이너가 실행될 때 Node.js 서버를 자동으로 실행합니다.

---

## 4. Dockerfile 작성 시 고려해야 할 사항

### ✅ **1) Docker 캐시(Cache) 활용하기**
Docker는 각 명령어를 실행한 후 **캐시를 생성**합니다.  
이를 활용하면 **불필요한 재빌드**를 줄일 수 있습니다.

**✔️ 잘못된 예시**
```dockerfile
COPY . .
RUN npm install  # ❌ 모든 파일을 먼저 복사한 후 npm install을 실행하면 캐시가 무효화됨
```

**✔️ 올바른 예시**
```dockerfile
COPY package*.json ./
RUN npm install  # ✅ 먼저 패키지 파일만 복사 후 설치하면 캐시를 재사용할 수 있음
COPY . .  # 이후에 전체 파일을 복사
```

---

### ✅ **2) 이미지 크기를 줄이기**
- **경량화된 이미지** 사용 (`node:16-alpine` 같은 경량 이미지 활용)
- `.dockerignore` 파일을 사용하여 **불필요한 파일 제외**
  ```
  node_modules
  npm-debug.log
  .git
  ```

---

### ✅ **3) 멀티스테이지 빌드 활용하기 (Multi-stage Builds)**
Docker에서 **빌드 과정과 실행 환경을 분리**하여, **최소한의 용량**으로 실행할 수 있습니다.

```dockerfile
# 빌드 단계
FROM node:16 as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 실행 단계
FROM node:16-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
CMD ["node", "dist/server.js"]
```
✅ **이점**:
- 불필요한 개발 도구 제거 → **최종 컨테이너의 용량 감소**
- 실행에 필요한 파일만 포함 → **보안성 증가**

---

## 5. Dockerfile을 활용한 컨테이너 실행 방법 🚀

### **1️⃣ Docker 이미지 빌드**
```sh
docker build -t my-node-app .
```
> `-t` 옵션을 사용하여 **이미지에 태그**를 지정합니다.

---

### **2️⃣ Docker 컨테이너 실행**
```sh
docker run -p 8080:8080 my-node-app
```
> `-p` 옵션을 사용하여 **포트 매핑**을 설정합니다.

---

### **3️⃣ 실행 중인 컨테이너 확인**
```sh
docker ps
```

---

### **4️⃣ 실행 중인 컨테이너 종료**
```sh
docker stop <컨테이너_ID>
```

---

## 6. 결론

Dockerfile을 사용하면 애플리케이션을 **환경에 구애받지 않고 실행**할 수 있습니다.  
또한, CI/CD와 결합하면 배포 자동화가 가능해지고, **일관된 환경**을 유지할 수 있습니다.

✅ **이 문서에서 배운 핵심 사항**
1. `FROM`, `WORKDIR`, `COPY`, `RUN`, `CMD` 등 **기본적인 Dockerfile 명령어 정리**
2. **효율적인 Dockerfile 작성법** (캐싱 활용, 다단계 빌드, `.dockerignore` 활용)
3. Docker 이미지를 빌드하고 실행하는 실전 명령어 🚀

이 문서를 통해 Dockerfile을 더욱 쉽게 이해하고 활용할 수 있길 바랍니다!

---

🔹 **이 문서는 언제든지 다운로드하여 참조할 수 있습니다.**
