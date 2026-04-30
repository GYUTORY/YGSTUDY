---
title: Docker BuildKit과 buildx
tags: [docker, buildkit, buildx, multi-arch, devops]
updated: 2026-04-30
---

# Docker BuildKit과 buildx

## 목차
- [BuildKit이 등장한 배경](#buildkit이-등장한-배경)
- [buildx란 무엇인가](#buildx란-무엇인가)
- [멀티 아키텍처 빌드(amd64/arm64)](#멀티-아키텍처-빌드amd64arm64)
- [M1/M2 Mac에서 amd64 빌드와 QEMU 에뮬레이션](#m1m2-mac에서-amd64-빌드와-qemu-에뮬레이션)
- [--mount=type=cache로 의존성 캐시 재사용](#--mounttypecache로-의존성-캐시-재사용)
- [--mount=type=secret으로 빌드 타임 시크릿 주입](#--mounttypesecret으로-빌드-타임-시크릿-주입)
- [--mount=type=ssh로 private repo clone](#--mounttypessh로-private-repo-clone)
- [인라인 캐시 vs registry 캐시](#인라인-캐시-vs-registry-캐시)
- [buildx bake로 다중 타겟 정의](#buildx-bake로-다중-타겟-정의)
- [GitHub Actions 캐시 연동의 함정](#github-actions-캐시-연동의-함정)

---

## BuildKit이 등장한 배경

기존의 Docker 빌더(legacy builder)는 Dockerfile을 위에서 아래로 순차 실행하는 단순한 구조였다. 이 방식은 멀티스테이지 빌드의 의존성 없는 스테이지도 직렬로 처리했고, 빌드 타임에 임시로 필요한 시크릿을 다루는 깔끔한 방법이 없었다. 그래서 SSH 키나 npm 토큰을 ARG로 받아서 빌드하다가 이미지 레이어에 그대로 박혀버리는 사고가 흔했다.

BuildKit은 이 문제들을 해결하려고 만든 새 빌더다. Docker 18.09부터 실험 기능으로 들어왔고 23.0부터는 기본 빌더가 됐다. 차이점을 짚어보면 이렇다.

- 의존성 없는 스테이지를 병렬로 빌드한다. 멀티스테이지에서 stage A와 stage B가 서로 독립이면 동시에 돌린다.
- `--mount=type=cache`, `--mount=type=secret`, `--mount=type=ssh` 같은 빌드 마운트를 지원한다. 시크릿을 레이어에 안 남기고 쓸 수 있다.
- 이미지 매니페스트 v2 schema 2 / OCI manifest list를 다룰 수 있어서 멀티 아키텍처 빌드가 자연스럽다.
- 캐시 익스포트/임포트가 분리돼 있다. CI 환경처럼 빌더가 매번 새로 뜨는 곳에서 캐시를 외부에 저장하고 끌어다 쓸 수 있다.

기존 빌더는 이제 deprecated다. 환경변수 `DOCKER_BUILDKIT=1`을 매번 붙이던 시절은 지났고, 요즘은 `docker build`가 그냥 BuildKit으로 동작한다. 다만 회사에서 오래된 Docker 버전(18 이전)이 깔린 빌드 서버를 쓴다면 명시적으로 켜줘야 할 수 있다.

---

## buildx란 무엇인가

buildx는 BuildKit을 더 잘 쓰기 위한 CLI 플러그인이다. `docker buildx`로 호출하고, 멀티 아키텍처 빌드와 다중 빌더 인스턴스 관리를 담당한다. 헷갈리기 쉬운 부분인데 정리하면 이렇다.

- BuildKit은 빌드 엔진이다. 실제로 이미지를 만든다.
- buildx는 BuildKit을 조작하는 CLI다. 빌더 인스턴스를 만들고, 멀티 플랫폼 빌드를 지시한다.
- `docker build`는 내부적으로 BuildKit을 쓰지만 단일 아키텍처 / 단일 빌더 기준의 인터페이스다. 멀티 플랫폼이 필요하면 `docker buildx build`를 써야 한다.

buildx 빌더 인스턴스는 기본 도커 데몬과 별개로 동작한다. `docker-container` 드라이버로 만들면 빌더 자체가 컨테이너로 뜬다. 이 컨테이너가 BuildKit 데몬을 실행하면서 캐시를 관리한다.

```bash
# 기본 빌더 확인 (default는 docker 드라이버)
docker buildx ls

# 멀티 플랫폼용 빌더 새로 만들기
docker buildx create --name multi --driver docker-container --use

# 부트스트랩(컨테이너 실제로 띄우기)
docker buildx inspect --bootstrap
```

`--driver docker` (기본 빌더)는 멀티 플랫폼을 지원하지 않는다. 그래서 멀티 아키텍처 빌드를 시도하면 "multiple platforms feature is currently not supported for docker driver" 에러가 뜬다. 이때 `docker-container` 드라이버 빌더를 만들고 `--use`로 활성화해야 한다.

---

## 멀티 아키텍처 빌드(amd64/arm64)

서버가 x86_64(amd64)인 경우가 대부분이지만 AWS Graviton(arm64), 사내 개발자의 M1/M2 Mac, Raspberry Pi 같은 환경이 늘면서 멀티 아키텍처 이미지 수요가 커졌다. 한 이미지 태그로 여러 아키텍처를 묶어 푸시하면 클라이언트가 자기 아키텍처에 맞는 걸 자동으로 받는다. 이걸 OCI manifest list(또는 Docker manifest list)라고 부른다.

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myregistry.io/myapp:1.0.0 \
  --push \
  .
```

여기서 주의할 점이 몇 가지 있다.

**`--load`와 `--push`의 차이**. `--load`는 빌드 결과를 로컬 도커 데몬으로 가져온다. 그런데 로컬 데몬은 manifest list를 못 다루기 때문에 멀티 플랫폼 빌드에서는 `--load`가 안 된다. 멀티 플랫폼을 빌드하려면 무조건 `--push`로 레지스트리에 올리거나 `--output type=oci,dest=...` 같은 형식으로 빼야 한다. 로컬에서 테스트하려면 단일 플랫폼으로만 `--load`해야 한다.

**베이스 이미지가 멀티 아키텍처를 지원하는지 확인**. `node:20-alpine`처럼 공식 이미지는 대부분 amd64/arm64 둘 다 있다. 하지만 사내에서 자체 빌드한 베이스 이미지가 amd64만 있다면 arm64 빌드는 실패한다. 이건 미리 `docker buildx imagetools inspect <image>` 로 매니페스트를 보면 확인 가능하다.

**아키텍처 의존 패키지**. Dockerfile에서 `apt-get install` 같은 걸 할 때는 보통 문제없지만, `RUN curl -L ... | sh` 같이 바이너리를 직접 받는 스크립트는 아키텍처를 고정해서 받는 경우가 많다. 이때는 BuildKit이 제공하는 빌드 인자 `TARGETARCH`, `TARGETPLATFORM`을 써야 한다.

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.22 AS builder
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src
COPY . .
RUN GOOS=$TARGETOS GOARCH=$TARGETARCH go build -o /out/app ./cmd/app

FROM alpine:3.19
COPY --from=builder /out/app /usr/local/bin/app
ENTRYPOINT ["/usr/local/bin/app"]
```

이 패턴이 중요한 이유는 builder 스테이지를 `$BUILDPLATFORM`(빌드 머신의 네이티브 아키텍처)에 고정해서 컴파일을 빠르게 돌리고, 결과물만 `$TARGETARCH`용으로 크로스 컴파일하는 방식이기 때문이다. Go나 Rust처럼 크로스 컴파일이 쉬운 언어에서는 QEMU 에뮬레이션 없이도 빌드가 끝난다.

---

## M1/M2 Mac에서 amd64 빌드와 QEMU 에뮬레이션

M1/M2 Mac 개발자가 운영용 amd64 이미지를 빌드해야 하는 경우가 자주 있다. buildx는 binfmt_misc + QEMU를 통해 다른 아키텍처 명령을 에뮬레이션할 수 있다.

```bash
# QEMU 에뮬레이터 등록 (한 번만)
docker run --privileged --rm tonistiigi/binfmt --install all

# arm64 머신에서 amd64 이미지 빌드
docker buildx build --platform linux/amd64 -t myapp:amd64 --load .
```

이게 동작은 하는데 성능이 끔찍하게 느리다. 실제 경험으로는 네이티브 빌드 대비 5~10배 정도 느려질 수 있다. 특히 Node.js의 `npm install`에서 native module(node-gyp 컴파일)이 끼면 더 심해진다. Python의 `pip install` 중 C 확장 빌드도 마찬가지다.

이 문제를 우회하는 방법은 몇 가지가 있다.

**언어 차원의 크로스 컴파일을 쓴다**. Go, Rust, .NET 같은 언어는 빌드 환경의 아키텍처와 무관하게 타겟 아키텍처용 바이너리를 만들 수 있다. 위에서 본 `--platform=$BUILDPLATFORM` 패턴이 그 용법이다. 컴파일은 네이티브로 돌고 결과물만 amd64여서 QEMU 부담이 없다.

**원격 빌더를 쓴다**. 회사에 amd64 빌드 서버가 있다면 buildx는 원격 BuildKit 인스턴스에 빌드를 위임할 수 있다.

```bash
# SSH로 원격 서버의 도커에 연결
docker buildx create --name remote-amd64 --driver docker-container ssh://user@build-server
docker buildx use remote-amd64
docker buildx build --platform linux/amd64 -t myapp:amd64 --push .
```

여러 아키텍처를 동시에 빌드하려면 `--append`로 빌더 노드를 추가해서 amd64는 amd64 머신이, arm64는 arm64 머신이 처리하도록 만들 수도 있다. 이게 사실상 운영급 멀티 아키텍처 빌드의 표준 패턴이다.

**CI에서 빌드한다**. 로컬에서 amd64 멀티 아키텍처 이미지를 자주 푸시하는 워크플로 자체가 의심스럽다. 보통은 CI에 맡기고 로컬에서는 단일 플랫폼만 쓴다.

---

## --mount=type=cache로 의존성 캐시 재사용

Dockerfile의 `RUN` 명령에 캐시 마운트를 붙이면 빌드 사이에 디렉토리를 보존할 수 있다. 패키지 매니저의 다운로드 캐시를 재활용하는 데 쓴다.

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline
COPY . .
```

여기서 `# syntax=docker/dockerfile:1.7` 주석이 중요하다. BuildKit은 Dockerfile의 frontend 버전을 이 주석으로 결정한다. 이걸 안 쓰면 옛날 문법으로 해석되어 `--mount` 옵션을 모른다고 에러가 난다.

캐시 마운트의 동작 원리를 알아두는 게 좋다.

- 캐시는 빌더 인스턴스에 종속된다. `docker buildx create`로 만든 빌더가 사라지면 캐시도 사라진다.
- 빌드 사이에 디렉토리를 공유하지만 이미지 레이어에는 안 들어간다. 그래서 이미지 크기가 부풀지 않는다.
- 동시에 여러 빌드가 같은 캐시를 쓰면 락이 걸린다. `id`를 다르게 주면 분리할 수 있다(`--mount=type=cache,id=npm-app1,target=...`).
- `sharing` 모드(`shared`/`private`/`locked`)로 동시성 제어가 가능한데, 기본값 `shared`는 동시 쓰기를 허용한다. npm/pip은 보통 괜찮지만 일부 패키지 매니저는 `locked`가 필요할 수 있다.

언어별 권장 마운트 위치는 이 정도다.

```dockerfile
# Node.js (npm)
RUN --mount=type=cache,target=/root/.npm npm ci

# Node.js (pnpm)
RUN --mount=type=cache,target=/root/.local/share/pnpm/store pnpm install

# Python (pip)
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Go
RUN --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=cache,target=/go/pkg/mod \
    go build -o /app ./cmd/app

# Rust
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release

# apt
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y curl
```

apt 캐시를 쓸 때 주의할 점이 있다. 도커 베이스 이미지에는 `/etc/apt/apt.conf.d/docker-clean` 파일이 있어서 패키지 설치 후 apt 캐시를 자동으로 지운다. 캐시 마운트를 효율적으로 쓰려면 이 파일을 비워주거나 `Acquire::http::Pipeline-Depth "0";` 같은 옵션을 추가해야 한다.

```dockerfile
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' \
    > /etc/apt/apt.conf.d/keep-cache
```

또 한 가지, 캐시 마운트는 빌드 결과물의 정확성을 책임지지 않는다. `package-lock.json`이 바뀌었는데 `~/.npm`만 재사용하면 의도치 않은 결과가 나올 수 있다. 그래서 `npm ci`처럼 lock 파일 기반 결정적 설치를 같이 써야 한다.

---

## --mount=type=secret으로 빌드 타임 시크릿 주입

private npm 레지스트리 토큰, AWS 자격증명, GitHub PAT처럼 빌드 타임에만 필요하고 이미지에는 절대 안 남아야 하는 값이 있다. 이걸 ARG로 받으면 `docker history`에 그대로 노출된다. 실제로 SSH 키를 ARG로 받아서 푸시했다가 사내 보안팀에 걸린 사례가 종종 보인다.

BuildKit의 secret mount는 빌드 시점에만 파일로 마운트되고 레이어에 기록되지 않는다.

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:20-alpine
WORKDIR /app
COPY package*.json .npmrc.template ./
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) \
    sed "s/__TOKEN__/$NPM_TOKEN/" .npmrc.template > .npmrc && \
    npm ci && \
    rm .npmrc
COPY . .
```

빌드 명령은 이렇게 준다.

```bash
# 파일에서 읽기
docker buildx build --secret id=npm_token,src=$HOME/.npm-token -t myapp .

# 환경변수에서 읽기
docker buildx build --secret id=npm_token,env=NPM_TOKEN -t myapp .
```

주의할 점.

- 시크릿 파일을 그대로 `COPY`하면 의미가 없다. 마운트는 `RUN` 안에서만 유효하고, 그 안에서 처리하고 끝내야 한다.
- 시크릿 값을 환경변수로 받아서 다음 `RUN`에 그대로 흘리면 그 RUN의 명령행이 캐시에 남을 수 있다. `cat /run/secrets/...` 한 번에 읽고 그 RUN 안에서 끝내는 게 안전하다.
- `.npmrc`처럼 토큰이 박힌 파일을 만들었다면 같은 RUN 안에서 지워야 한다. 다음 레이어에 넘기면 거기 박힌다.

`docker history`로 만든 이미지를 점검해서 ARG 값이나 환경변수가 남았는지 확인하는 습관을 들이는 게 좋다. 한 번 푸시한 레지스트리에서 토큰이 박힌 레이어를 빼는 건 거의 불가능하다.

---

## --mount=type=ssh로 private repo clone

`go mod download`나 `pip install`이 private GitHub 레포지토리에서 의존성을 가져와야 할 때가 있다. 이때 SSH 키를 빌드 컨텍스트에 복사하는 건 위험하다. `--mount=type=ssh`는 호스트의 ssh-agent 소켓을 빌드 컨테이너에 마운트한다.

```dockerfile
# syntax=docker/dockerfile:1.7
FROM golang:1.22-alpine
RUN apk add --no-cache git openssh-client
RUN mkdir -p ~/.ssh && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=ssh \
    --mount=type=cache,target=/go/pkg/mod \
    git config --global url."git@github.com:".insteadOf "https://github.com/" && \
    GOPRIVATE=github.com/yourorg/* go mod download
COPY . .
RUN go build -o /app ./cmd/app
```

빌드 시점에는 ssh-agent를 띄워놓고 명시적으로 전달해야 한다.

```bash
# 키 로드
ssh-add ~/.ssh/id_ed25519

# 기본 ssh-agent 소켓 사용
docker buildx build --ssh default -t myapp .

# 특정 키만 지정
docker buildx build --ssh github=$HOME/.ssh/id_ed25519 -t myapp .
```

CI 환경에서 ssh-agent가 안 떠있는 경우가 많다. GitHub Actions라면 `webfactory/ssh-agent` 같은 액션을 쓰거나, 명시적으로 `eval $(ssh-agent -s) && ssh-add - <<< "$SSH_KEY"` 같은 식으로 띄워놓고 buildx에 넘긴다. `ssh-keyscan`을 빠뜨리면 known_hosts 검증 단계에서 멈춘다. 이게 CI에서 자주 만나는 함정이다.

---

## 인라인 캐시 vs registry 캐시

빌드 캐시를 외부에 저장해서 다른 빌더(특히 CI)에서 재사용할 수 있다. 방식이 두 가지다.

**인라인 캐시(`type=inline`)**. 캐시 메타데이터를 이미지 매니페스트 안에 넣는 방식이다.

```bash
docker buildx build \
  --cache-to type=inline \
  --cache-from type=registry,ref=myregistry.io/myapp:cache \
  -t myregistry.io/myapp:latest \
  --push .
```

- 이미지와 캐시가 한 태그에 묶여서 관리가 단순하다.
- 멀티스테이지 빌드의 중간 스테이지 캐시는 못 담는다. 마지막 스테이지의 레이어만 캐시된다.
- 그래서 builder 스테이지에서 큰 의존성을 컴파일하는 패턴에서는 캐시 효과가 거의 없다.

**registry 캐시(`type=registry`)**. 캐시를 별도 매니페스트로 푸시한다.

```bash
docker buildx build \
  --cache-to type=registry,ref=myregistry.io/myapp:buildcache,mode=max \
  --cache-from type=registry,ref=myregistry.io/myapp:buildcache \
  -t myregistry.io/myapp:latest \
  --push .
```

- `mode=max`를 주면 멀티스테이지의 모든 중간 레이어 캐시를 푸시한다. `mode=min`(기본값)은 최종 이미지에 들어간 레이어만 푸시한다.
- 캐시 매니페스트가 커진다. 의존성이 많은 프로젝트는 수백 MB까지도 간다.
- 레지스트리가 OCI manifest를 제대로 지원해야 한다. ECR은 2020년 이후 지원하고, GHCR/Docker Hub/Harbor는 다 된다. 일부 사내 레지스트리(특히 옛날 Nexus)는 안 될 수 있다.

운영 경험상 빌드 시간이 오래 걸리고 의존성이 두꺼운 프로젝트(Java + Gradle, Rust + cargo)는 `type=registry,mode=max`가 필수다. 인라인은 간단한 Node.js 프로젝트나 캐시 효과가 미미한 경우에나 쓴다.

`mode=max`의 함정 하나. 한 번 푸시한 캐시 태그가 계속 누적되어 커지는데, 이게 작은 머신에서는 빌드 후반에 디스크를 다 먹어버리는 경우가 있다. 주기적으로 캐시 태그를 지우거나 새 태그로 회전시키는 운영이 필요하다.

---

## buildx bake로 다중 타겟 정의

여러 이미지를 한꺼번에 빌드해야 할 때(API 서버 + worker + 마이그레이션 컨테이너 등) 매번 build 명령을 반복하는 대신 `buildx bake`로 선언적으로 묶을 수 있다. `docker-compose`의 build 섹션과 비슷한 위치다.

`docker-bake.hcl` 파일에 이렇게 쓴다.

```hcl
variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = "myregistry.io"
}

group "default" {
  targets = ["api", "worker"]
}

target "common" {
  context = "."
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = ["type=registry,ref=${REGISTRY}/buildcache:latest"]
  cache-to = ["type=registry,ref=${REGISTRY}/buildcache:latest,mode=max"]
}

target "api" {
  inherits = ["common"]
  dockerfile = "api/Dockerfile"
  tags = ["${REGISTRY}/api:${TAG}"]
}

target "worker" {
  inherits = ["common"]
  dockerfile = "worker/Dockerfile"
  tags = ["${REGISTRY}/worker:${TAG}"]
}
```

빌드는 한 줄이다.

```bash
TAG=1.2.3 docker buildx bake --push
```

bake의 진짜 가치는 의존성 없는 타겟을 병렬로 빌드해주는 데 있다. 그리고 `docker-compose.yml`을 바로 입력으로 받을 수도 있어서 기존 compose 파일이 있으면 마이그레이션이 쉽다.

```bash
docker buildx bake -f docker-compose.yml api worker
```

HCL 변수 시스템이 꽤 강력하다. `${BAKE_GIT_SHA}` 같은 메타 변수도 있고, 함수 정의도 된다. 다만 너무 추상화하면 디버깅이 힘들어진다. 변수 두세 개와 inheritance 한 단계 정도가 무난하다.

---

## GitHub Actions 캐시 연동의 함정

GitHub Actions에서 buildx를 쓰면 가장 흔한 패턴이 GHA 캐시 백엔드(`type=gha`)를 쓰는 것이다. 작업이 끝나면 GitHub Actions 자체 캐시 스토리지에 저장된다.

```yaml
- uses: docker/setup-buildx-action@v3

- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: myregistry.io/myapp:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

여기서 발 빠지는 지점이 몇 가지 있다.

**캐시 scope 충돌**. `type=gha`는 기본적으로 워크플로 이름 + ref를 키로 쓴다. 여러 이미지를 같은 워크플로에서 빌드하면 캐시가 서로 덮어쓴다. 이미지마다 `scope`를 다르게 줘야 한다.

```yaml
cache-from: type=gha,scope=api
cache-to: type=gha,mode=max,scope=api
```

**브랜치별 캐시 격리**. PR 빌드와 main 빌드가 서로의 캐시를 못 쓰는 게 기본 동작이다. GitHub Actions 캐시는 브랜치 단위로 격리되고, 자식 브랜치는 부모(main)의 캐시를 읽기만 가능하다. PR에서 빌드한 캐시는 main이 못 본다. main에서 캐시를 만들어두는 워크플로가 따로 있어야 PR 빌드가 빨라진다.

**캐시 용량 제한**. GitHub Actions 캐시는 레포당 10GB 한도가 있다. `mode=max`로 누적되면 금방 찬다. 한도를 넘으면 LRU로 오래된 캐시가 지워지는데, 이게 멀티 아키텍처 빌드에서는 amd64 캐시는 살아있고 arm64 캐시만 잘리는 식으로 비대칭하게 사라질 수 있다. 큰 프로젝트는 `type=registry`로 자체 레지스트리에 캐시를 두는 게 안정적이다.

**`docker/build-push-action`의 동작**. 이 액션은 buildx를 한 번 더 감싼 인터페이스다. 멀티 플랫폼 빌드 결과를 로컬로 가져오려면 어차피 안 되는데, 액션이 친절하게 에러를 내주지 않고 그냥 `--load`를 시도하다 실패하는 경우가 있다. `push: true`와 `platforms: linux/amd64,linux/arm64`를 같이 쓰는 게 정석이다.

**self-hosted runner의 빌더 상태**. self-hosted runner를 쓸 때 buildx 빌더 인스턴스가 잡 사이에 살아있을지 죽을지 일관되지 않다. `setup-buildx-action`을 매번 호출해서 빌더를 보장하는 게 좋다. 그리고 캐시 디렉토리(`/var/lib/buildkit`)가 디스크를 갉아먹는 걸 모니터링해야 한다. 한 번 본 사례에서는 캐시가 200GB까지 차서 빌드 노드가 멈춘 적이 있다.

마지막으로 한 가지. CI에서 buildx 빌더가 `docker-container` 드라이버라면 빌드한 이미지를 `docker run`으로 바로 돌릴 수 없다. `--load`로 데몬에 가져오거나 `--push`로 레지스트리에 올리고 다시 pull해야 한다. CI에서 빌드 → 테스트 → 푸시 흐름을 만들 때 이 부분에서 한 번씩 막힌다.
