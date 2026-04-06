---
title: Docker 파일 마운트
tags: [docker, mount, volume, bind-mount, tmpfs, buildkit]
updated: 2026-04-06
---

# Docker 파일 마운트

컨테이너는 자체 파일시스템을 갖고 있지만, 컨테이너를 삭제하면 내부 데이터도 같이 사라진다. 호스트의 파일이나 디렉토리를 컨테이너 내부 경로에 연결하는 것이 마운트다. 개발 환경에서는 소스 코드를 바인드 마운트해서 컨테이너 재빌드 없이 변경사항을 반영하고, 프로덕션에서는 볼륨 마운트로 DB 데이터를 보존한다.

Docker는 세 가지 마운트 타입을 지원한다: **바인드 마운트**, **볼륨 마운트**, **tmpfs 마운트**.

---

## -v와 --mount 플래그

마운트를 지정하는 방법이 두 가지 있다.

### -v (--volume) 플래그

콜론으로 구분된 세 개의 필드를 받는다.

```bash
docker run -v /host/path:/container/path:옵션 이미지명
```

- 첫 번째 필드: 호스트 경로 또는 볼륨 이름
- 두 번째 필드: 컨테이너 경로
- 세 번째 필드: 옵션 (ro, rw, z, Z 등 콤마로 구분)

`-v`는 호스트 경로가 없으면 자동으로 디렉토리를 생성한다. 이게 문제가 되는 경우가 있다. 경로를 오타냈을 때 에러 없이 빈 디렉토리가 마운트되어서, 컨테이너가 설정 파일을 못 찾는 원인을 한참 추적하게 된다.

### --mount 플래그

key=value 쌍으로 명시적으로 지정한다.

```bash
docker run --mount type=bind,source=/host/path,target=/container/path,readonly 이미지명
```

주요 키:

| 키 | 설명 |
|---|---|
| `type` | bind, volume, tmpfs 중 하나 |
| `source` (src) | 호스트 경로 또는 볼륨 이름 |
| `target` (dst) | 컨테이너 경로 |
| `readonly` | 읽기 전용 |
| `bind-propagation` | 마운트 전파 옵션 |
| `volume-driver` | 볼륨 드라이버 지정 |
| `volume-opt` | 드라이버 옵션 |
| `tmpfs-size` | tmpfs 크기 제한 |
| `tmpfs-mode` | tmpfs 파일 모드 |

### 왜 --mount를 써야 하는 상황이 있는가

`-v`는 존재하지 않는 호스트 경로를 자동 생성한다. `--mount`는 경로가 없으면 에러를 뱉는다. 설정 파일이나 시크릿 파일을 마운트할 때는 `--mount`를 쓰는 게 안전하다. 파일이 실제로 존재하는지 확인하고 싶을 때 `--mount`를 써라.

```bash
# -v: /etc/myapp/config.yml이 없으면 빈 디렉토리로 자동 생성됨 (의도하지 않은 동작)
docker run -v /etc/myapp/config.yml:/app/config.yml myapp

# --mount: 파일이 없으면 에러 발생 (원하는 동작)
docker run --mount type=bind,source=/etc/myapp/config.yml,target=/app/config.yml myapp
```

Docker Compose에서도 긴 문법(long syntax)으로 `--mount`와 동일한 동작을 지정할 수 있다.

```yaml
services:
  app:
    volumes:
      # 짧은 문법 (-v와 동일)
      - ./src:/app/src

      # 긴 문법 (--mount와 동일)
      - type: bind
        source: ./config.yml
        target: /app/config.yml
        read_only: true
```

---

## 바인드 마운트 (Bind Mount)

호스트의 특정 경로를 컨테이너에 직접 연결한다. 호스트에서 파일을 수정하면 컨테이너에서 바로 보이고, 컨테이너에서 수정해도 호스트에 반영된다.

```bash
# 현재 디렉토리를 컨테이너의 /app에 마운트
docker run -it -v $(pwd):/app node:20

# 읽기 전용 마운트
docker run -v /etc/nginx/nginx.conf:/etc/nginx/nginx.conf:ro nginx

# --mount 사용
docker run --mount type=bind,src=$(pwd),dst=/app,readonly node:20
```

바인드 마운트는 호스트 파일시스템 구조에 의존한다. 다른 머신에서 같은 명령을 실행하면 경로가 달라서 실패할 수 있다. 프로덕션에서는 볼륨을 쓰고, 바인드 마운트는 개발 환경에서만 쓰는 게 일반적이다.

---

## 볼륨 마운트 (Volume Mount)

Docker가 관리하는 저장 영역이다. 기본적으로 호스트의 `/var/lib/docker/volumes/` 아래에 저장된다. 호스트 경로를 알 필요 없이 이름으로 관리한다.

```bash
# 볼륨 생성
docker volume create postgres-data

# 컨테이너에 마운트
docker run -d --name postgres \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=secret \
  postgres:16

# 볼륨 상세 정보
docker volume inspect postgres-data
```

`-v 볼륨이름:/경로` 형태에서 볼륨이 없으면 자동으로 생성된다. 명시적으로 만들고 싶으면 `docker volume create`를 먼저 실행해라.

### 볼륨 드라이버

기본 드라이버는 `local`이다. NFS나 CIFS 같은 네트워크 파일시스템을 볼륨으로 쓸 수 있다.

#### NFS 볼륨

```bash
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw,nfsvers=4 \
  --opt device=:/export/data \
  nfs-data
```

Compose에서는 이렇게 선언한다.

```yaml
volumes:
  nfs-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.1.100,rw,nfsvers=4
      device: ":/export/data"
```

#### CIFS (SMB) 볼륨

```bash
docker volume create --driver local \
  --opt type=cifs \
  --opt o=addr=192.168.1.200,username=user,password=pass \
  --opt device=//192.168.1.200/share \
  cifs-data
```

NFS 볼륨을 쓸 때 주의할 점: 네트워크가 끊기면 컨테이너 내부에서 I/O 행이 걸린다. 타임아웃 옵션(`timeo`, `retrans`)을 반드시 설정해라.

```bash
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw,nfsvers=4,soft,timeo=30,retrans=2 \
  --opt device=:/export/data \
  nfs-data
```

### 볼륨 백업과 복원

볼륨 데이터를 백업하려면 임시 컨테이너를 띄워서 tar로 묶는다.

```bash
# 백업: postgres-data 볼륨을 tar 파일로 추출
docker run --rm \
  -v postgres-data:/source:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz -C /source .

# 복원: tar 파일을 새 볼륨에 풀기
docker volume create postgres-data-restored
docker run --rm \
  -v postgres-data-restored:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /target
```

`/source`를 `:ro`로 마운트하는 게 중요하다. 백업 중에 데이터가 변경되는 것을 막는다.

DB 볼륨을 백업할 때는 tar보다 DB 자체 덤프 도구(`pg_dump`, `mysqldump`)를 쓰는 게 낫다. 실행 중인 DB의 데이터 파일을 그냥 tar로 묶으면 일관성이 깨질 수 있다.

---

## tmpfs 마운트

tmpfs는 메모리에만 존재하는 파일시스템이다. 디스크에 쓰지 않으므로 컨테이너가 종료되면 데이터가 사라진다.

```bash
# --tmpfs 플래그
docker run --tmpfs /tmp:rw,noexec,nosuid,size=100m 이미지명

# --mount 플래그
docker run --mount type=tmpfs,target=/tmp,tmpfs-size=104857600,tmpfs-mode=1777 이미지명
```

tmpfs를 쓰는 경우:

- **민감한 데이터**: 비밀번호 파일이나 토큰을 디스크에 남기고 싶지 않을 때
- **임시 캐시**: 애플리케이션이 /tmp에 캐시를 많이 생성하는데 디스크 I/O를 줄이고 싶을 때
- **빌드 아티팩트**: 빌드 중간 산출물이 디스크를 소모하지 않게 할 때

주의: tmpfs는 메모리를 소비한다. `size` 옵션을 안 주면 호스트 메모리의 절반까지 쓸 수 있다. 컨테이너 메모리 제한(`--memory`)과 별개이므로 반드시 크기를 지정해라.

Compose에서는 이렇게 쓴다.

```yaml
services:
  app:
    tmpfs:
      - /tmp:size=100m,mode=1777
```

---

## BuildKit 마운트 타입

`Dockerfile`의 `RUN` 명령에서 `--mount` 플래그를 사용할 수 있다. BuildKit이 활성화되어야 한다 (Docker 23.0 이상에서 기본 활성).

### cache 마운트

빌드 캐시를 유지해서 재빌드 속도를 높인다. 패키지 매니저의 캐시 디렉토리를 유지하는 데 주로 쓴다.

```dockerfile
# apt 캐시 유지
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y curl

# pip 캐시 유지
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Go 모듈 캐시 유지
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build -o /app .

# npm 캐시 유지
RUN --mount=type=cache,target=/root/.npm \
    npm ci --production
```

cache 마운트는 빌드 간에 유지되지만, 다른 빌드에서도 공유된다. `id` 옵션으로 격리할 수 있다.

```dockerfile
RUN --mount=type=cache,id=myapp-npm,target=/root/.npm \
    npm ci
```

### secret 마운트

빌드 시 필요한 시크릿을 이미지 레이어에 남기지 않고 전달한다. `.npmrc`에 private registry 토큰이 있거나, pip에 private index 인증이 필요할 때 쓴다.

```dockerfile
# Dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --production

RUN --mount=type=secret,id=aws,target=/root/.aws/credentials \
    aws s3 cp s3://my-bucket/data.tar.gz /tmp/
```

빌드 실행 시 시크릿 파일을 전달한다.

```bash
docker build --secret id=npmrc,src=$HOME/.npmrc \
             --secret id=aws,src=$HOME/.aws/credentials \
             -t myapp .
```

이전에는 `ARG`로 토큰을 넘기는 코드를 많이 봤는데, `ARG`는 이미지 히스토리에 남는다. `docker history`로 누구나 볼 수 있다. secret 마운트는 해당 `RUN` 명령 실행 중에만 파일이 존재하고, 레이어에 기록되지 않는다.

### ssh 마운트

SSH agent를 빌드 컨테이너에 전달한다. private Git 저장소에서 의존성을 가져올 때 쓴다.

```dockerfile
# Dockerfile
RUN --mount=type=ssh \
    git clone git@github.com:company/private-lib.git /tmp/lib
```

```bash
# SSH agent가 실행 중이어야 함
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519
docker build --ssh default -t myapp .
```

SSH 키 파일을 COPY로 이미지에 넣는 실수를 하면 안 된다. multi-stage로 지워도 이전 레이어에 남아 있다.

### bind 마운트 (빌드 시)

빌드 컨텍스트 외부의 파일을 빌드에서 참조할 때 쓴다.

```dockerfile
RUN --mount=type=bind,from=builder,source=/app/build,target=/static \
    cp -r /static /usr/share/nginx/html/
```

---

## 마운트 전파 (Propagation)

컨테이너 내부에서 마운트를 수행할 때(예: 컨테이너 안에서 USB를 마운트하거나, 다른 파일시스템을 붙일 때) propagation 옵션이 필요하다.

| 옵션 | 호스트 → 컨테이너 | 컨테이너 → 호스트 |
|---|---|---|
| `rprivate` (기본값) | 전파 안 됨 | 전파 안 됨 |
| `private` | 전파 안 됨 | 전파 안 됨 |
| `rslave` | 전파됨 | 전파 안 됨 |
| `slave` | 전파됨 | 전파 안 됨 |
| `rshared` | 전파됨 | 전파됨 |
| `shared` | 전파됨 | 전파됨 |

`r` 접두사는 재귀(recursive)를 의미한다. 하위 마운트까지 같은 규칙을 적용한다.

```bash
# 호스트의 마운트 변경이 컨테이너에 보이게
docker run -v /mnt/usb:/mnt/usb:rslave 이미지명

# --mount 사용
docker run --mount type=bind,src=/mnt/usb,dst=/mnt/usb,bind-propagation=rslave 이미지명
```

대부분의 경우 기본값(`rprivate`)으로 충분하다. Docker-in-Docker를 실행하거나, 컨테이너가 NFS/FUSE 마운트를 수행하는 특수한 경우에만 propagation을 변경해야 한다.

---

## SELinux 라벨 (:z, :Z)

RHEL, CentOS, Fedora 같은 SELinux가 활성화된 시스템에서 바인드 마운트하면 Permission denied가 발생하는 경우가 있다. 컨테이너 프로세스의 SELinux 컨텍스트가 호스트 파일의 라벨과 맞지 않기 때문이다.

```bash
# 공유 라벨 - 여러 컨테이너가 동시에 접근 가능
docker run -v /host/data:/data:z 이미지명

# 전용 라벨 - 해당 컨테이너만 접근 가능
docker run -v /host/data:/data:Z 이미지명
```

- `:z` (소문자): 호스트 디렉토리에 `svirt_sandbox_file_t` 라벨을 설정한다. 여러 컨테이너가 공유할 수 있다.
- `:Z` (대문자): 컨테이너 전용 라벨을 설정한다. 다른 컨테이너나 호스트 프로세스가 접근할 수 없게 된다.

**`:Z`를 시스템 디렉토리에 절대 쓰지 마라.** `/etc`나 `/var/log` 같은 경로에 `:Z`를 쓰면 호스트 시스템 자체가 해당 파일에 접근할 수 없게 되어 시스템이 망가질 수 있다.

```bash
# 이런 거 하면 안 된다
docker run -v /etc:/etc:Z 이미지명   # 호스트 시스템 파손 가능

# SELinux를 일시적으로 permissive 모드로 전환해서 원인 확인
# (디버깅 용도로만 사용)
sudo setenforce 0
docker run -v /host/data:/data 이미지명
# 문제가 해결되면 SELinux 라벨 문제가 맞다
sudo setenforce 1
```

Ubuntu, Debian, macOS에서는 SELinux가 기본 비활성이므로 `:z`, `:Z` 옵션이 필요 없다.

---

## macOS 바인드 마운트 성능 문제

macOS에서 Docker Desktop을 사용할 때 바인드 마운트 성능이 Linux 대비 크게 떨어진다. Docker Desktop은 Linux VM 위에서 돌아가기 때문에, 바인드 마운트가 호스트(macOS) → VM → 컨테이너를 거친다.

### 파일시스템 드라이버 변천

- **osxfs** (구버전): 초기 Docker for Mac에서 사용. node_modules 같은 대량 파일 접근 시 체감될 정도로 느렸다.
- **gRPC FUSE**: osxfs 대체로 등장. 약간 개선되었지만 여전히 느렸다.
- **VirtioFS** (현재 기본): Docker Desktop 4.15+에서 기본 파일시스템. 이전 대비 큰 폭의 성능 향상.

Docker Desktop 설정에서 `VirtioFS`가 선택되어 있는지 확인해라. Settings > General > "Choose file sharing implementation for your containers"에서 볼 수 있다.

### consistency 옵션 (deprecated)

과거에는 `-v` 플래그에 consistency 옵션을 쓸 수 있었다.

```bash
# 과거에 사용하던 옵션 (현재는 무시됨)
docker run -v $(pwd):/app:delegated node:20
docker run -v $(pwd):/app:cached node:20
docker run -v $(pwd):/app:consistent node:20
```

- `consistent`: 완전 동기화 (기본값, 가장 느림)
- `cached`: 호스트 → 컨테이너 방향에서 지연 허용
- `delegated`: 컨테이너 → 호스트 방향에서 지연 허용 (가장 빠름)

VirtioFS에서는 이 옵션들이 무시된다. 쓰더라도 에러는 안 나지만 효과가 없다.

### 실제 대응 방법

node_modules처럼 파일 수가 많고 자주 접근하는 디렉토리는 바인드 마운트에서 제외하고 named volume을 쓴다.

```yaml
services:
  app:
    build: .
    volumes:
      - .:/app                      # 소스 코드는 바인드 마운트
      - node_modules:/app/node_modules  # node_modules는 볼륨으로 분리

volumes:
  node_modules:
```

이렇게 하면 소스 코드 변경은 즉시 반영되면서, node_modules 접근 성능은 네이티브 수준을 유지한다.

---

## UID/GID 불일치 문제

컨테이너 내부의 사용자와 호스트 사용자의 UID/GID가 다르면 권한 문제가 생긴다. 흔한 시나리오: 컨테이너가 root(UID 0)로 실행되면서 바인드 마운트된 디렉토리에 파일을 생성하면, 호스트에서 해당 파일이 root 소유로 나타난다.

```bash
# 컨테이너에서 파일 생성
docker run -v $(pwd):/app alpine sh -c "echo hello > /app/test.txt"

# 호스트에서 확인하면 root 소유
ls -la test.txt
# -rw-r--r-- 1 root root 6 Apr  6 10:00 test.txt
# 일반 사용자로 수정/삭제가 안 될 수 있다
```

### 해결 방법 1: --user 플래그

```bash
# 현재 사용자의 UID/GID로 컨테이너 실행
docker run --user $(id -u):$(id -g) -v $(pwd):/app node:20 npm run build
```

이 방법은 간단하지만, 컨테이너 내부에 해당 UID의 사용자가 없어서 `whoami`가 실패하거나, 홈 디렉토리가 없어서 npm/pip 캐시가 동작하지 않는 경우가 있다.

### 해결 방법 2: Dockerfile에서 사용자 생성

```dockerfile
FROM node:20

# 호스트 사용자와 동일한 UID/GID로 사용자 생성
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} appuser && \
    useradd -u ${UID} -g ${GID} -m appuser

USER appuser
WORKDIR /home/appuser/app
```

```bash
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) -t myapp .
docker run -v $(pwd):/home/appuser/app myapp
```

### 해결 방법 3: fixuid 같은 엔트리포인트 스크립트

컨테이너 시작 시 UID/GID를 동적으로 맞추는 방법이다.

```bash
#!/bin/sh
# entrypoint.sh
# 마운트된 디렉토리의 소유자 UID로 앱 사용자의 UID를 변경
if [ -d "/app" ]; then
    HOST_UID=$(stat -c '%u' /app)
    HOST_GID=$(stat -c '%g' /app)
    usermod -u $HOST_UID appuser 2>/dev/null
    groupmod -g $HOST_GID appuser 2>/dev/null
fi
exec gosu appuser "$@"
```

이 스크립트는 root로 시작해서 UID를 바꾼 다음 `gosu`로 권한을 내려서 프로세스를 실행한다.

---

## inotify와 바인드 마운트

webpack-dev-server, nodemon, React HMR 같은 도구들은 파일 변경을 감지해서 자동 리로드한다. 이 도구들은 Linux의 inotify를 사용하는데, 바인드 마운트 환경에서 inotify 이벤트가 전달되지 않는 경우가 있다.

### 문제가 발생하는 상황

macOS나 Windows에서 Docker Desktop을 쓸 때, 호스트에서 파일을 수정해도 컨테이너 내부의 inotify에 이벤트가 도달하지 않는다. Docker Desktop이 VM을 통해 파일을 중계하기 때문이다. VirtioFS가 inotify를 지원하긴 하지만, 이벤트 전달이 누락되거나 지연되는 경우가 여전히 있다.

### 대응 방법

#### polling 모드 사용

대부분의 도구가 polling fallback을 지원한다.

```bash
# webpack
WATCHPACK_POLLING=true webpack serve

# nodemon
nodemon --legacy-watch app.js

# Create React App / Vite
CHOKIDAR_USEPOLLING=true npm start
```

Compose에서 환경 변수로 넘기면 편하다.

```yaml
services:
  app:
    volumes:
      - .:/app
    environment:
      - CHOKIDAR_USEPOLLING=true
      - WATCHPACK_POLLING=true
```

polling은 CPU를 더 쓴다. `CHOKIDAR_INTERVAL`을 늘려서(기본 100ms → 1000ms 등) 부하를 줄일 수 있다.

#### Linux 호스트에서도 안 되는 경우

Linux에서 바인드 마운트한 경우에는 inotify가 정상 동작해야 한다. 안 된다면 inotify watcher 제한에 걸린 것일 수 있다.

```bash
# 현재 watcher 제한 확인
cat /proc/sys/fs/inotify/max_user_watches

# 제한 늘리기 (임시)
sudo sysctl fs.inotify.max_user_watches=524288

# 영구 적용
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

node_modules처럼 감시할 필요 없는 디렉토리는 도구 설정에서 제외해라. 불필요한 watcher가 제한을 소모한다.

---

## Docker Compose 마운트 예시

실제 프로젝트에서 여러 마운트 타입을 조합해서 쓰는 패턴이다.

```yaml
services:
  app:
    build:
      context: .
      args:
        UID: ${UID:-1000}
        GID: ${GID:-1000}
    volumes:
      # 소스 코드 바인드 마운트
      - .:/app

      # 의존성은 named volume으로 분리 (macOS 성능)
      - node_modules:/app/node_modules

      # 설정 파일 읽기 전용
      - type: bind
        source: ./config/production.yml
        target: /app/config/production.yml
        read_only: true
    tmpfs:
      - /tmp:size=100m

  db:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    environment:
      POSTGRES_PASSWORD: secret

volumes:
  node_modules:
  postgres-data:
```

---

## 트러블슈팅 정리

| 증상 | 원인 | 해결 |
|---|---|---|
| Permission denied (RHEL/CentOS) | SELinux 라벨 불일치 | `-v /path:/path:z` 사용 |
| 컨테이너가 생성한 파일이 호스트에서 root 소유 | UID/GID 불일치 | `--user $(id -u):$(id -g)` |
| 바인드 마운트 경로 오타인데 에러 없음 | `-v`가 자동 디렉토리 생성 | `--mount`로 변경 |
| Hot reload가 안 됨 (macOS) | inotify 이벤트 미전달 | polling 모드 활성화 |
| Hot reload가 안 됨 (Linux) | inotify watcher 제한 초과 | `max_user_watches` 증가 |
| macOS에서 npm install이 느림 | 바인드 마운트 I/O 오버헤드 | node_modules를 named volume으로 분리 |
| NFS 볼륨에서 I/O 행 | 네트워크 끊김 + hard mount | `soft,timeo=30` 옵션 추가 |
| 빌드 시 시크릿이 이미지에 남음 | ARG/COPY로 시크릿 전달 | BuildKit secret 마운트 사용 |

---

## 참조

- [Docker 공식 문서 - Volumes](https://docs.docker.com/storage/volumes/)
- [Docker 공식 문서 - Bind mounts](https://docs.docker.com/storage/bind-mounts/)
- [Docker 공식 문서 - tmpfs mounts](https://docs.docker.com/storage/tmpfs/)
- [Docker 공식 문서 - BuildKit](https://docs.docker.com/build/buildkit/)
- [Dockerfile reference - RUN --mount](https://docs.docker.com/reference/dockerfile/#run---mount)
- [Docker Desktop - VirtioFS](https://docs.docker.com/desktop/settings/#general)
