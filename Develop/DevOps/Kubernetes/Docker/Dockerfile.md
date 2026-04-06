---
title: Dockerfile 작성법
tags: [docker, dockerfile, container, devops]
updated: 2026-04-06
---

# Dockerfile 작성법

## 목차
- [Dockerfile 기본 구조](#dockerfile-기본-구조)
- [FROM - 베이스 이미지 선택](#from---베이스-이미지-선택)
- [RUN - 명령 실행](#run---명령-실행)
- [COPY vs ADD](#copy-vs-add)
- [CMD vs ENTRYPOINT](#cmd-vs-entrypoint)
- [ARG vs ENV](#arg-vs-env)
- [.dockerignore 설정](#dockerignore-설정)
- [레이어 캐싱 원리](#레이어-캐싱-원리)
- [멀티스테이지 빌드](#멀티스테이지-빌드)
- [이미지 크기 줄이기](#이미지-크기-줄이기)
- [HEALTHCHECK 설정](#healthcheck-설정)
- [빌드 시 자주 겪는 실수와 디버깅](#빌드-시-자주-겪는-실수와-디버깅)

---

## Dockerfile 기본 구조

Dockerfile은 이미지를 만드는 스크립트다. 한 줄 한 줄이 이미지 레이어 하나에 대응되고, 위에서 아래로 순서대로 실행된다.

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

이 Dockerfile을 `docker build -t my-app .` 으로 빌드하면 각 명령어가 순차적으로 실행되면서 레이어가 쌓인다.

---

## FROM - 베이스 이미지 선택

모든 Dockerfile은 `FROM`으로 시작한다. 어떤 베이스 이미지를 고르느냐에 따라 이미지 크기, 보안, 디버깅 편의성이 달라진다.

```dockerfile
# 태그를 명시하지 않으면 latest가 붙는다
FROM node

# 버전을 고정해야 빌드가 재현 가능하다
FROM node:20.11.1-alpine3.19

# digest까지 고정하면 완전히 동일한 이미지를 보장한다
FROM node@sha256:abcdef1234567890...
```

**태그를 반드시 고정해야 하는 이유**: `FROM node:20-alpine`으로 써두면 오늘 빌드한 이미지와 한 달 뒤 빌드한 이미지가 다를 수 있다. alpine 패치 버전이 올라가면서 베이스가 바뀌기 때문이다. CI에서 갑자기 빌드가 깨지는 원인 중 하나가 이거다. 운영 환경에 배포하는 이미지라면 마이너 버전까지는 고정하는 게 좋다.

`FROM scratch`는 빈 이미지에서 시작하는 거다. Go 같은 정적 바이너리를 배포할 때 쓴다.

```dockerfile
FROM scratch
COPY myapp /myapp
CMD ["/myapp"]
```

---

## RUN - 명령 실행

`RUN`은 빌드 시점에 컨테이너 안에서 명령을 실행한다. 실행 결과가 새 레이어로 커밋된다.

```dockerfile
# shell form - /bin/sh -c 로 실행된다
RUN apt-get update && apt-get install -y curl

# exec form - 셸 없이 직접 실행한다
RUN ["apt-get", "install", "-y", "curl"]
```

shell form은 환경변수 치환이 되고, exec form은 안 된다. 대부분의 경우 shell form을 쓰면 되는데, exec form은 셸이 없는 이미지(scratch 등)에서 필요하다.

**RUN 명령은 가능하면 하나로 합쳐야 한다.** `RUN`마다 레이어가 생기는데, 패키지 설치 후 캐시를 지우는 걸 별도 `RUN`으로 하면 캐시가 이전 레이어에 남아서 이미지 크기가 줄지 않는다.

```dockerfile
# 잘못된 예 - 캐시가 첫 번째 레이어에 남아있다
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# 올바른 예 - 하나의 레이어에서 설치와 정리를 같이 한다
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
```

`--no-install-recommends`를 빼먹으면 추천 패키지까지 전부 설치돼서 이미지가 불필요하게 커진다.

---

## COPY vs ADD

둘 다 호스트의 파일을 이미지 안에 넣는 명령이다. 거의 모든 경우에 `COPY`를 쓰면 된다.

```dockerfile
# COPY - 단순 복사
COPY src/ /app/src/
COPY config.json /app/

# ADD - tar 자동 해제, URL 다운로드 기능이 있다
ADD archive.tar.gz /app/
ADD https://example.com/file.txt /app/
```

**`ADD`를 쓰면 안 되는 이유가 있다.** `ADD`는 tar 파일을 자동으로 풀고, URL에서 파일을 다운로드하는 기능이 있는데, 이게 의도치 않은 동작을 만들 수 있다. `.tar.gz` 파일을 풀지 않고 그대로 복사하고 싶은데 `ADD`를 쓰면 자동으로 풀려버린다.

URL 다운로드는 `ADD`보다 `RUN curl`이나 `RUN wget`을 쓰는 게 낫다. `ADD`로 다운로드하면 캐시가 안 되고, 다운로드 실패 시 에러 핸들링도 안 된다.

```dockerfile
# ADD 대신 이렇게
RUN curl -fsSL https://example.com/file.txt -o /app/file.txt
```

tar 자동 해제가 필요한 경우에만 `ADD`를 쓴다. 나머지는 전부 `COPY`.

**`COPY`의 `--chown` 플래그**: 파일을 복사하면서 소유자를 바꿀 수 있다.

```dockerfile
COPY --chown=node:node . /app/
```

이걸 안 쓰고 `RUN chown -R`을 별도로 실행하면 레이어가 하나 더 생기면서 이미지 크기가 늘어난다.

---

## CMD vs ENTRYPOINT

이 둘의 차이를 제대로 이해하지 않으면 컨테이너 실행 시 이상한 동작을 겪게 된다.

**CMD**: 컨테이너 시작 시 기본 명령을 지정한다. `docker run` 뒤에 명령을 붙이면 CMD가 덮어써진다.

```dockerfile
CMD ["node", "server.js"]
```

```bash
docker run my-app               # node server.js 실행
docker run my-app node repl.js  # CMD 무시, node repl.js 실행
docker run my-app sh            # CMD 무시, 셸 진입
```

**ENTRYPOINT**: 컨테이너가 실행할 바이너리를 고정한다. `docker run` 뒤에 붙이는 건 ENTRYPOINT의 인자로 들어간다.

```dockerfile
ENTRYPOINT ["node"]
CMD ["server.js"]
```

```bash
docker run my-app               # node server.js 실행
docker run my-app repl.js       # node repl.js 실행 (CMD가 덮어써짐)
```

**ENTRYPOINT + CMD 조합 패턴**: ENTRYPOINT로 실행 바이너리를 고정하고, CMD로 기본 인자를 주는 방식이다.

```dockerfile
ENTRYPOINT ["java", "-jar"]
CMD ["app.jar"]
```

실무에서 많이 쓰는 패턴은 entrypoint 스크립트를 두는 것이다.

```dockerfile
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
```

entrypoint 스크립트 안에서 환경변수 검증, 설정 파일 생성, DB 마이그레이션 대기 같은 초기화 로직을 넣고, 마지막에 `exec "$@"`로 CMD를 실행한다.

```bash
#!/bin/sh
set -e

# 환경변수 검증
if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

# CMD 실행
exec "$@"
```

`exec "$@"` 를 빼먹으면 entrypoint 스크립트가 PID 1이 되고, 실제 애플리케이션은 자식 프로세스로 뜬다. 시그널 전달이 안 되면서 `docker stop`에 graceful shutdown이 안 되는 문제가 생긴다.

**shell form vs exec form 차이**:

```dockerfile
# exec form - 프로세스가 PID 1로 직접 뜬다
CMD ["node", "server.js"]

# shell form - /bin/sh -c 가 PID 1이고, node는 자식 프로세스
CMD node server.js
```

shell form을 쓰면 SIGTERM이 node 프로세스에 전달되지 않는다. `docker stop`하면 10초 대기 후 SIGKILL로 강제 종료된다. 운영 환경에서는 exec form을 써야 한다.

---

## ARG vs ENV

빌드 시점과 런타임 시점에서의 변수 사용을 구분해야 한다.

**ARG**: 빌드 시점에만 사용 가능하다. 빌드가 끝나면 사라진다.

```dockerfile
ARG NODE_VERSION=20
FROM node:${NODE_VERSION}-alpine

ARG BUILD_ENV=production
RUN echo "Building for ${BUILD_ENV}"
```

```bash
docker build --build-arg NODE_VERSION=18 --build-arg BUILD_ENV=staging .
```

**ENV**: 빌드 시점과 런타임 모두에서 사용 가능하다. 이미지에 남는다.

```dockerfile
ENV NODE_ENV=production
ENV APP_PORT=3000
```

**주의할 점**: `ARG`로 선언한 변수를 `ENV`로 넘겨야 런타임에서도 쓸 수 있다.

```dockerfile
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}
```

**ARG에 민감한 정보를 넣으면 안 된다.** `docker history`로 이미지 레이어를 조회하면 ARG 값이 그대로 보인다.

```bash
# 이렇게 빌드하면
docker build --build-arg DB_PASSWORD=secret123 .

# 이미지 히스토리에 비밀번호가 노출된다
docker history my-app
```

비밀 정보는 빌드 시점에 `--secret` 플래그를 쓰거나, 런타임에 환경변수로 주입하는 게 맞다.

```dockerfile
# BuildKit secret mount
RUN --mount=type=secret,id=db_password \
    cat /run/secrets/db_password > /dev/null
```

**ARG는 FROM 앞뒤로 스코프가 다르다.** `FROM` 전에 선언한 ARG는 `FROM` 명령에서만 쓸 수 있다. `FROM` 뒤의 명령에서 쓰려면 다시 선언해야 한다.

```dockerfile
ARG BASE_TAG=3.19
FROM alpine:${BASE_TAG}

# 여기서 BASE_TAG를 쓰려면 다시 선언해야 한다
ARG BASE_TAG
RUN echo ${BASE_TAG}
```

이거 모르면 빌드할 때 변수가 빈 문자열로 들어가서 삽질하게 된다.

---

## .dockerignore 설정

`.dockerignore`는 빌드 컨텍스트에서 제외할 파일을 지정한다. `.gitignore`와 문법이 비슷하다.

빌드 컨텍스트란 `docker build .`에서 `.`에 해당하는 디렉토리 전체다. Docker 데몬에 이 디렉토리를 통째로 전송하기 때문에, 불필요한 파일이 있으면 빌드 시작 전 전송 시간이 길어진다.

```
# .dockerignore

# 버전 관리
.git
.gitignore

# 의존성 - 이미지 안에서 새로 설치한다
node_modules
vendor

# 빌드 산출물
dist
build
*.jar
target

# 환경 설정
.env
.env.*
docker-compose*.yml
Dockerfile*

# IDE/에디터
.idea
.vscode
*.swp

# 테스트
test
tests
__tests__
coverage

# 문서
README.md
docs
```

`.dockerignore`를 안 만들면 생기는 문제:

- **node_modules가 빌드 컨텍스트에 포함된다.** 로컬의 node_modules가 수백 MB일 수 있고, 이걸 Docker 데몬에 전송하느라 빌드가 느려진다. `COPY . .`으로 이미지에 들어가면 `RUN npm ci`로 설치한 의존성과 충돌할 수도 있다.
- **.env 파일이 이미지에 들어간다.** DB 비밀번호, API 키 같은 게 이미지에 포함되면 이미지를 레지스트리에 푸시했을 때 민감 정보가 노출된다.
- **.git 디렉토리가 포함된다.** 프로젝트에 따라 수백 MB가 넘는 경우가 있다.

빌드 컨텍스트가 뭔가 크다 싶으면 `docker build` 시작할 때 나오는 "Sending build context to Docker daemon" 메시지에서 크기를 확인할 수 있다.

---

## 레이어 캐싱 원리

Docker 빌드 성능의 핵심이다. 제대로 이해하지 않으면 매번 전체 빌드를 하게 된다.

**캐싱 규칙**: Docker는 각 명령을 실행하기 전에 동일한 명령의 캐시된 레이어가 있는지 확인한다. 캐시 히트 조건은 명령어 종류에 따라 다르다.

- `RUN`: 명령 문자열이 동일하면 캐시 사용
- `COPY`/`ADD`: 복사 대상 파일의 체크섬이 동일하면 캐시 사용

**캐시 무효화는 연쇄적이다.** 한 레이어의 캐시가 무효화되면 그 아래 모든 레이어가 재빌드된다. 이게 핵심이다.

```dockerfile
# 나쁜 예 - 소스 한 줄 바꾸면 npm ci부터 다시 실행
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci
CMD ["node", "server.js"]

# 좋은 예 - package.json이 안 바뀌면 npm ci 캐시 사용
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
CMD ["node", "server.js"]
```

이 차이가 빌드 시간을 분 단위로 바꾼다. 의존성 설치는 오래 걸리지만 자주 바뀌지 않고, 소스 코드는 자주 바뀌지만 빌드가 빠르다. 변경 빈도가 낮은 것을 위에, 높은 것을 아래에 배치하는 게 원칙이다.

**RUN 캐시의 함정**: `RUN apt-get update`의 결과가 캐시되면 패키지 목록이 오래된 상태로 고정된다. 그래서 `apt-get update`와 `apt-get install`을 반드시 같은 `RUN`에 넣어야 한다.

```dockerfile
# 위험 - apt-get update가 캐시되면 오래된 패키지 목록으로 설치한다
RUN apt-get update
RUN apt-get install -y curl=7.88.1-10

# 안전
RUN apt-get update && apt-get install -y curl
```

**캐시를 강제로 무효화하는 방법**:

```bash
# 전체 캐시 무시
docker build --no-cache .

# 특정 시점부터 캐시 무효화하는 트릭
ARG CACHE_BUST=1
RUN echo "${CACHE_BUST}" && apt-get update
# --build-arg CACHE_BUST=$(date +%s) 로 빌드하면 매번 캐시가 깨진다
```

**BuildKit 캐시 마운트**: npm, pip, maven 같은 패키지 매니저의 캐시를 빌드 간에 공유할 수 있다.

```dockerfile
RUN --mount=type=cache,target=/root/.npm \
    npm ci --production
```

이렇게 하면 `npm ci`가 매번 모든 패키지를 네트워크에서 받지 않고, 캐시된 패키지를 재사용한다. CI 환경에서 빌드 시간 단축에 쓸만하다.

---

## 멀티스테이지 빌드

하나의 Dockerfile에 여러 `FROM`을 두고, 빌드 단계와 실행 단계를 분리하는 방식이다. 빌드에 필요한 도구(컴파일러, 빌드 도구 등)가 최종 이미지에 포함되지 않아서 이미지 크기가 크게 줄어든다.

### 기본 구조

```dockerfile
# 빌드 스테이지
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 실행 스테이지
FROM node:20-alpine AS production
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY package.json ./
CMD ["node", "dist/server.js"]
```

빌드 스테이지에서 `node:20` (약 1GB)을 쓰더라도 최종 이미지는 `node:20-alpine` 기반이라 훨씬 작다.

### Go 애플리케이션의 경우

Go는 정적 바이너리를 만들 수 있어서 멀티스테이지의 효과가 극대화된다.

```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app ./cmd/server

FROM scratch
COPY --from=build /app /app
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
ENTRYPOINT ["/app"]
```

빌드 이미지가 800MB 이상이어도 최종 이미지는 바이너리 크기(보통 10~30MB)만큼만 나온다. `scratch`에는 셸도 없고 패키지 매니저도 없다.

`ca-certificates.crt`를 빼먹으면 HTTPS 호출이 전부 실패한다. 외부 API를 호출하는 서비스라면 반드시 복사해야 한다.

### Java 애플리케이션의 경우

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
```

`mvn dependency:go-offline`으로 의존성만 먼저 받아두면 소스 변경 시 의존성 다운로드를 건너뛸 수 있다.

JDK 대신 JRE만 들어있는 이미지를 쓰는 것도 중요하다. JDK는 컴파일러, 디버거 등이 포함돼서 수백 MB 더 크다.

### 스테이지를 선택적으로 빌드하기

```bash
# 빌드 스테이지만 실행 (디버깅 용도)
docker build --target build -t my-app:build .

# 테스트 스테이지만 실행
docker build --target test -t my-app:test .
```

```dockerfile
FROM node:20 AS build
# ...빌드

FROM build AS test
RUN npm test

FROM node:20-alpine AS production
COPY --from=build /app/dist ./dist
# ...
```

CI에서 테스트 스테이지까지만 돌리고, 배포할 때는 production 스테이지까지 빌드하는 식으로 쓴다.

---

## 이미지 크기 줄이기

이미지가 작으면 레지스트리 전송이 빠르고, 디스크를 덜 먹고, 보안 공격 표면도 줄어든다.

### 베이스 이미지 선택 기준

| 이미지 | 크기 (대략) | 패키지 매니저 | 셸 | 용도 |
|--------|-------------|--------------|-----|------|
| ubuntu/debian | 100~130MB | apt | bash | 개발/디버깅 환경, 시스템 라이브러리 의존성이 많을 때 |
| alpine | 5~7MB | apk | sh (busybox) | 대부분의 프로덕션 워크로드 |
| slim (debian-slim) | 70~80MB | apt | bash | alpine에서 glibc 호환 문제가 생길 때 |
| distroless | 2~20MB | 없음 | 없음 | 보안이 최우선인 프로덕션 환경 |
| scratch | 0MB | 없음 | 없음 | Go, Rust 등 정적 바이너리 |

**alpine 쓸 때 주의할 점**: alpine은 glibc 대신 musl을 쓴다. Python의 일부 C 확장 모듈이나 Node.js의 네이티브 모듈(bcrypt, sharp 등)이 musl에서 빌드가 안 되거나, 빌드 시간이 길어지는 경우가 있다. 이런 경우에 slim을 쓴다.

```dockerfile
# alpine에서 bcrypt 설치가 실패하는 경우
FROM node:20-alpine
RUN npm install bcrypt  # 빌드 에러 가능

# slim으로 바꾸면 해결
FROM node:20-slim
RUN npm install bcrypt
```

**distroless**: Google이 관리하는 이미지로, 애플리케이션 런타임만 들어있다. 셸이 없으니 `docker exec`로 컨테이너에 들어가서 디버깅하는 게 불가능하다. 운영 환경에서 보안을 강화할 때 쓴다.

```dockerfile
FROM gcr.io/distroless/java21-debian12
COPY app.jar /app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

디버깅이 필요하면 `:debug` 태그를 쓴다. busybox 셸이 포함된 버전이다.

### 이미지 크기를 줄이는 실질적인 방법

**1. 패키지 설치 후 캐시를 삭제한다.**

```dockerfile
# apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# apk
RUN apk add --no-cache curl

# pip
RUN pip install --no-cache-dir -r requirements.txt

# npm
RUN npm ci --production && npm cache clean --force
```

**2. 빌드 전용 패키지는 설치 후 삭제한다.**

```dockerfile
# alpine - 가상 패키지로 묶어서 한번에 삭제
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    pip install --no-cache-dir cryptography && \
    apk del .build-deps
```

**3. 이미지 크기를 확인한다.**

```bash
# 이미지 전체 크기
docker images my-app

# 레이어별 크기 확인
docker history my-app

# dive 도구로 시각적으로 분석 (별도 설치 필요)
dive my-app
```

`docker history`에서 어떤 레이어가 큰지 보고, 그 레이어를 만드는 `RUN` 명령을 개선하는 방식으로 접근하면 된다.

---

## HEALTHCHECK 설정

컨테이너가 정상 동작하는지 Docker가 주기적으로 확인하는 메커니즘이다. `docker ps`의 STATUS 컬럼에 healthy/unhealthy가 표시된다.

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

각 옵션의 의미:
- `--interval`: 헬스체크 간격. 기본 30초.
- `--timeout`: 타임아웃. 이 시간 안에 응답이 없으면 실패.
- `--start-period`: 컨테이너 시작 후 이 시간 동안은 실패해도 무시한다. JVM 기반 앱처럼 기동 시간이 긴 경우 넉넉하게 잡아야 한다.
- `--retries`: 연속 실패 횟수. 이만큼 연속 실패하면 unhealthy 상태가 된다.

```dockerfile
# curl 없는 이미지에서는 직접 만든 헬스체크 스크립트를 쓴다
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["node", "healthcheck.js"]
```

```javascript
// healthcheck.js
const http = require('http');
const req = http.get('http://localhost:3000/health', (res) => {
  process.exit(res.statusCode === 200 ? 0 : 1);
});
req.on('error', () => process.exit(1));
req.setTimeout(3000, () => { req.destroy(); process.exit(1); });
```

HEALTHCHECK는 Docker Compose의 `depends_on` 조건이나 Docker Swarm의 롤링 업데이트에서 사용된다. Kubernetes를 쓴다면 Dockerfile의 HEALTHCHECK 대신 Pod spec의 livenessProbe/readinessProbe를 쓰는 게 일반적이다.

---

## 빌드 시 자주 겪는 실수와 디버깅

### COPY 경로 문제

```dockerfile
# 에러: COPY failed: file not found in build context
COPY config/settings.json /app/

# 원인 1: .dockerignore에서 config/를 제외하고 있다
# 원인 2: docker build 명령의 컨텍스트 경로가 잘못됐다
# 원인 3: 파일이 실제로 없다 (오타)
```

빌드 컨텍스트 밖의 파일은 절대 복사할 수 없다. `COPY ../something /app/` 같은 건 안 된다. 상위 디렉토리 파일이 필요하면 빌드 컨텍스트를 상위로 잡아야 한다.

```bash
# 프로젝트 루트에서 빌드하되, 하위 디렉토리의 Dockerfile을 지정
docker build -f services/api/Dockerfile .
```

### 권한 문제

```dockerfile
# 이렇게 하면 애플리케이션이 root로 실행된다
FROM node:20-alpine
COPY . /app
CMD ["node", "server.js"]

# non-root 사용자로 실행해야 한다
FROM node:20-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser
CMD ["node", "server.js"]
```

`USER` 명령 이후의 `RUN`은 해당 사용자 권한으로 실행된다. 패키지 설치 같은 root 권한이 필요한 작업은 `USER` 전에 해야 한다.

node 공식 이미지에는 `node` 유저가 이미 있다. 별도로 만들 필요 없이 `USER node`를 쓰면 된다.

### 빌드 중간에 디버깅하기

```bash
# 특정 스테이지에서 멈추고 셸로 진입
docker build --target build -t debug-build .
docker run -it debug-build sh

# BuildKit 없이 빌드하면 중간 레이어 ID가 나온다 (레거시)
DOCKER_BUILDKIT=0 docker build .
# 실패 직전 레이어 ID로 컨테이너를 띄워서 확인
docker run -it <layer-id> sh
```

### 플랫폼 관련 문제

M1/M2 Mac에서 빌드한 이미지를 Linux AMD64 서버에 배포하면 실행이 안 되는 경우가 있다.

```bash
# 명시적으로 플랫폼 지정
docker build --platform linux/amd64 -t my-app .

# 멀티 플랫폼 빌드 (buildx 필요)
docker buildx build --platform linux/amd64,linux/arm64 -t my-app .
```

Dockerfile에서도 플랫폼을 지정할 수 있다.

```dockerfile
FROM --platform=linux/amd64 node:20-alpine
```

### 캐시가 안 먹는 경우

빌드할 때마다 모든 레이어가 재빌드되면 다음을 확인한다.

- `COPY . .` 가 의존성 설치보다 위에 있는지 (위에서 설명한 레이어 순서 문제)
- `docker build`할 때 컨텍스트에 자주 바뀌는 파일(로그, `.git` 등)이 포함되는지
- CI 환경에서 매번 깨끗한 환경을 쓰는지 (이 경우 캐시가 없으니 `--cache-from` 옵션으로 레지스트리 캐시를 활용한다)

```bash
# 이전 빌드 이미지를 캐시로 사용
docker build --cache-from my-app:latest -t my-app:new .
```

### EXPOSE는 실제로 포트를 열지 않는다

```dockerfile
EXPOSE 3000
```

이건 문서화 용도일 뿐이다. 실제 포트 매핑은 `docker run -p 3000:3000`으로 해야 한다. `EXPOSE`를 안 써도 `-p` 옵션으로 포트를 열 수 있고, `EXPOSE`를 써도 `-p` 없이는 외부에서 접근할 수 없다.

### WORKDIR을 안 쓰고 절대경로로 모든 걸 지정하는 실수

```dockerfile
# 읽기 어렵고 실수하기 쉽다
RUN mkdir -p /usr/src/app
COPY package.json /usr/src/app/package.json
RUN cd /usr/src/app && npm install
COPY . /usr/src/app

# WORKDIR을 쓰면 깔끔하다
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
```

`RUN cd /some/path && command` 이렇게 하면 다음 `RUN`에서는 다시 `/`로 돌아간다. `RUN`마다 새 셸이 뜨기 때문이다. `WORKDIR`을 쓰면 이후 모든 명령의 작업 디렉토리가 고정된다.
