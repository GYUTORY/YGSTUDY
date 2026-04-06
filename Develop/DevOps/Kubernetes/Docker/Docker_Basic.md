---
title: Docker 핵심 개념
tags: [docker, container, devops]
updated: 2026-04-06
---

# Docker 핵심 개념

## 목차
- [컨테이너와 VM의 차이](#컨테이너와-vm의-차이)
- [Docker 아키텍처](#docker-아키텍처)
- [이미지와 컨테이너](#이미지와-컨테이너)
- [컨테이너 라이프사이클](#컨테이너-라이프사이클)
- [기본 명령어](#기본-명령어)
- [리소스 제한](#리소스-제한)
- [로그 관리](#로그-관리)
- [디스크 정리](#디스크-정리)

---

## 컨테이너와 VM의 차이

VM은 하이퍼바이저 위에 게스트 OS를 통째로 올린다. Ubuntu VM 하나 띄우면 커널, systemd, 패키지 매니저까지 전부 포함된 이미지를 부팅하는 거다. 그래서 VM 하나가 수 GB 메모리를 먹고, 부팅에 수십 초가 걸린다.

컨테이너는 호스트 OS의 커널을 공유한다. 프로세스 격리만 하는 거라서 별도의 OS 부팅이 없다. `docker run` 하면 1초 안에 프로세스가 뜬다. 메모리도 해당 프로세스가 실제로 쓰는 만큼만 잡힌다.

```
VM 구조                          컨테이너 구조
┌──────────┐ ┌──────────┐       ┌──────┐ ┌──────┐ ┌──────┐
│   App A  │ │   App B  │       │App A │ │App B │ │App C │
├──────────┤ ├──────────┤       ├──────┴─┴──────┴─┴──────┤
│ Guest OS │ │ Guest OS │       │     Docker Engine       │
├──────────┴─┴──────────┤       ├─────────────────────────┤
│     Hypervisor        │       │       Host OS           │
├───────────────────────┤       ├─────────────────────────┤
│     Hardware          │       │       Hardware          │
└───────────────────────┘       └─────────────────────────┘
```

실무에서 중요한 차이:

- **격리 수준**: VM은 커널까지 분리되니까 보안이 더 강하다. 컨테이너는 커널을 공유하기 때문에 커널 취약점이 터지면 호스트까지 영향받을 수 있다. 금융권이나 멀티테넌트 환경에서 이 부분을 신경 쓴다.
- **성능 오버헤드**: 컨테이너는 하이퍼바이저 계층이 없어서 네이티브에 가까운 성능이 나온다. VM은 I/O에서 체감할 수 있는 오버헤드가 있다.
- **이미지 크기**: 베이스 이미지 기준으로 alpine 리눅스 컨테이너 이미지가 5MB 정도다. Ubuntu VM 이미지는 최소 수백 MB.

컨테이너가 VM을 대체하는 게 아니다. 커널 격리가 필요하면 VM을 쓰고, 애플리케이션 배포 단위로 격리하려면 컨테이너를 쓴다. 실제로 클라우드에서는 VM 안에 Docker를 깔고 컨테이너를 돌리는 구조가 일반적이다.

---

## Docker 아키텍처

Docker는 클라이언트-서버 구조다.

### Docker Daemon (dockerd)

백그라운드에서 돌아가는 프로세스다. 이미지 빌드, 컨테이너 실행, 네트워크 관리 등 실제 작업을 전부 처리한다. 기본적으로 Unix 소켓(`/var/run/docker.sock`)으로 통신한다.

이 소켓 파일의 권한이 중요하다. 컨테이너 안에서 이 소켓을 마운트하면(Docker-in-Docker 방식) 호스트의 Docker를 직접 제어할 수 있게 되니까, CI/CD 파이프라인에서 쓸 때 보안 리스크를 인지하고 있어야 한다.

### Docker Client (docker)

`docker` 커맨드를 치면 실행되는 CLI 도구다. 명령어를 Docker Daemon에 API로 전달한다. 클라이언트와 데몬이 같은 머신에 있을 필요는 없다. `DOCKER_HOST` 환경변수로 원격 데몬에 연결할 수 있다.

```bash
# 원격 Docker 데몬에 연결
export DOCKER_HOST=tcp://192.168.1.100:2375
docker ps  # 원격 서버의 컨테이너 목록이 나온다
```

### Docker Registry

이미지를 저장하고 배포하는 저장소다. Docker Hub가 기본 퍼블릭 레지스트리이고, 사내에서는 Harbor나 AWS ECR 같은 프라이빗 레지스트리를 쓴다.

`docker pull nginx` 하면 Docker Hub에서 이미지를 내려받고, `docker push` 하면 레지스트리에 올린다. 프라이빗 레지스트리를 쓸 때는 이미지 이름 앞에 레지스트리 주소를 붙인다.

```bash
# Docker Hub (기본)
docker pull nginx

# 프라이빗 레지스트리
docker pull registry.company.com/my-app:1.0.0
```

---

## 이미지와 컨테이너

### 이미지

이미지는 읽기 전용 파일 시스템 스냅샷이다. Dockerfile에 정의한 명령어가 한 줄씩 실행되면서 레이어가 쌓이는 구조다.

```dockerfile
FROM openjdk:17-slim          # 레이어 1: 베이스 이미지
COPY build/libs/app.jar /app/ # 레이어 2: JAR 복사
EXPOSE 8080                   # 메타데이터 (레이어 아님)
CMD ["java", "-jar", "/app/app.jar"]  # 메타데이터 (레이어 아님)
```

각 레이어는 이전 레이어와의 diff(차이분)만 저장한다. 같은 베이스 이미지를 쓰는 컨테이너가 10개 있어도 베이스 레이어는 디스크에 한 벌만 존재한다.

Dockerfile 작성할 때 레이어 캐시를 의식해야 한다. 자주 바뀌는 내용(소스코드 COPY)은 아래쪽에, 잘 안 바뀌는 내용(의존성 설치)은 위쪽에 놓는다. 순서가 바뀌면 캐시가 깨지고 빌드 시간이 늘어난다.

```dockerfile
# 나쁜 예: 소스코드가 바뀔 때마다 의존성도 다시 설치됨
COPY . /app
RUN pip install -r requirements.txt

# 좋은 예: 의존성 레이어가 캐시됨
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
```

### 컨테이너

컨테이너는 이미지 위에 쓰기 가능한 레이어를 하나 올린 것이다. 컨테이너 안에서 파일을 수정하면 이 쓰기 레이어에 기록된다(Copy-on-Write). 원본 이미지는 변하지 않는다.

컨테이너를 삭제하면 쓰기 레이어도 같이 사라진다. 데이터를 보존하려면 볼륨이나 바인드 마운트를 써야 한다. 이 부분은 [File Mount 문서](../Docker/File_Mount.md)에서 다룬다.

---

## 컨테이너 라이프사이클

```
Created → Running → Paused → Running → Stopped → Removed
   │                                       ↑
   └───────────────────────────────────────┘
                    (restart)
```

각 상태에 대응하는 명령어:

| 상태 전환 | 명령어 |
|-----------|--------|
| 생성 | `docker create` |
| 실행 | `docker start` 또는 `docker run` (create + start) |
| 일시정지 | `docker pause` |
| 재개 | `docker unpause` |
| 중지 | `docker stop` (SIGTERM → 10초 후 SIGKILL) |
| 강제 중지 | `docker kill` (즉시 SIGKILL) |
| 삭제 | `docker rm` |

`docker stop`은 먼저 SIGTERM을 보내고, 기본 10초 동안 프로세스가 종료되지 않으면 SIGKILL을 보낸다. 애플리케이션에서 SIGTERM 핸들러를 제대로 구현해 놓지 않으면 graceful shutdown이 안 되고 강제 종료당한다.

Spring Boot의 경우 `server.shutdown=graceful` 설정을 켜 놓고, `docker stop`의 타임아웃을 애플리케이션의 종료 타임아웃보다 길게 잡아야 한다.

```bash
# 종료 대기 시간을 30초로 변경
docker stop --time 30 my-container
```

---

## 기본 명령어

### docker run

컨테이너를 만들고 바로 실행한다. 가장 많이 쓰는 명령어.

```bash
# 기본 실행
docker run nginx

# 백그라운드 실행 + 이름 지정 + 포트 매핑
docker run -d --name my-nginx -p 8080:80 nginx

# 환경변수 전달
docker run -d --name my-app \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  my-app:1.0.0

# 컨테이너 종료 시 자동 삭제 (테스트용으로 유용)
docker run --rm -it ubuntu bash
```

`-p 8080:80`은 호스트의 8080 포트를 컨테이너의 80 포트에 연결하는 것이다. 순서가 헷갈리면 `호스트:컨테이너`로 외운다.

`-d`는 detached 모드(백그라운드), `-it`는 interactive + TTY(터미널 접속). 이 두 개는 같이 쓸 일이 거의 없다.

### docker exec

실행 중인 컨테이너에 명령어를 보낸다. 디버깅할 때 자주 쓴다.

```bash
# 컨테이너 안에서 bash 쉘 열기
docker exec -it my-nginx bash

# 특정 명령어만 실행
docker exec my-nginx cat /etc/nginx/nginx.conf

# 다른 유저로 실행
docker exec -u root my-app whoami
```

컨테이너에 bash가 없는 경우가 있다. alpine 기반 이미지는 `sh`만 있으니까 `bash` 대신 `sh`를 써야 한다.

### docker logs

컨테이너의 stdout/stderr 출력을 본다.

```bash
# 전체 로그
docker logs my-app

# 마지막 100줄만
docker logs --tail 100 my-app

# 실시간 로그 (tail -f처럼)
docker logs -f my-app

# 타임스탬프 포함
docker logs -t my-app

# 특정 시간 이후 로그
docker logs --since 2024-01-01T10:00:00 my-app
docker logs --since 30m my-app  # 최근 30분
```

### docker inspect

컨테이너나 이미지의 상세 정보를 JSON으로 출력한다. 네트워크 설정, 마운트 포인트, 환경변수 등을 확인할 때 쓴다.

```bash
# 전체 정보
docker inspect my-app

# IP 주소만 뽑기
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' my-app

# 마운트 정보 확인
docker inspect -f '{{json .Mounts}}' my-app | jq

# 이미지의 레이어 확인
docker inspect nginx --format '{{json .RootFS.Layers}}' | jq
```

`-f` (format) 옵션에 Go 템플릿 문법을 쓴다. 자주 쓰는 건 외워두면 편하다.

### docker ps

실행 중인 컨테이너 목록을 본다.

```bash
# 실행 중인 컨테이너
docker ps

# 전체 (중지된 것 포함)
docker ps -a

# 특정 상태만 필터
docker ps -f status=exited

# 컨테이너 ID만 출력 (스크립트에서 유용)
docker ps -q
```

---

## 리소스 제한

아무 제한 없이 컨테이너를 띄우면 호스트의 리소스를 전부 먹을 수 있다. 운영 환경에서는 반드시 제한을 건다.

### 메모리 제한

```bash
# 메모리 최대 512MB
docker run -d --memory 512m my-app

# 메모리 + swap 제한
docker run -d --memory 512m --memory-swap 1g my-app
```

`--memory`만 설정하면 swap도 같은 크기만큼 할당된다 (총 메모리 = memory * 2). swap을 아예 안 쓰게 하려면 `--memory-swap`을 `--memory`와 같은 값으로 설정한다.

컨테이너가 메모리 제한을 초과하면 OOM Killer가 프로세스를 죽인다. `docker inspect`로 OOM 발생 여부를 확인할 수 있다.

```bash
docker inspect -f '{{.State.OOMKilled}}' my-app
```

Java 애플리케이션을 돌릴 때 주의할 점이 있다. JVM의 힙 메모리를 컨테이너 메모리 제한에 맞게 설정해야 한다. JDK 10 이후부터는 `-XX:MaxRAMPercentage` 옵션으로 컨테이너 메모리의 비율로 힙을 잡을 수 있다.

```bash
docker run -d --memory 1g \
  -e JAVA_OPTS="-XX:MaxRAMPercentage=75.0" \
  my-java-app
```

### CPU 제한

```bash
# CPU 코어 수 제한
docker run -d --cpus 1.5 my-app  # 1.5코어까지 사용

# CPU 가중치 (상대적)
docker run -d --cpu-shares 512 my-app  # 기본값 1024 대비 절반
```

`--cpus`는 절대적 제한이고, `--cpu-shares`는 CPU 경합이 있을 때의 상대적 가중치다. CPU가 남아돌면 `--cpu-shares`는 의미가 없다.

---

## 로그 관리

Docker는 기본적으로 컨테이너의 stdout/stderr를 JSON 파일로 저장한다. 이 파일이 무한히 커지는 게 운영에서 디스크를 채우는 주범 중 하나다.

### 로그 드라이버 설정

```bash
# 컨테이너별 로그 크기 제한
docker run -d \
  --log-opt max-size=100m \
  --log-opt max-file=3 \
  my-app
```

이렇게 하면 100MB짜리 로그 파일 3개까지만 유지된다. 가장 오래된 파일부터 삭제된다.

전체 Docker 데몬에 기본값을 설정하려면 `/etc/docker/daemon.json`에 적는다.

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

이 설정을 변경한 후에는 Docker 데몬을 재시작해야 하고, 기존에 떠 있던 컨테이너에는 적용되지 않는다. 새로 만드는 컨테이너부터 적용된다.

### 로그 파일 위치 확인

```bash
# 컨테이너 로그 파일 경로
docker inspect -f '{{.LogPath}}' my-app
# 출력 예: /var/lib/docker/containers/<id>/<id>-json.log
```

디스크가 갑자기 차면 이 경로부터 확인한다.

---

## 디스크 정리

Docker를 오래 쓰면 사용하지 않는 이미지, 중지된 컨테이너, 안 쓰는 볼륨이 디스크를 잡아먹는다.

### docker system prune

사용하지 않는 리소스를 한 번에 정리한다.

```bash
# 중지된 컨테이너 + 사용하지 않는 네트워크 + dangling 이미지
docker system prune

# 위 항목 + 사용하지 않는 이미지 전부 + 볼륨까지
docker system prune -a --volumes
```

`-a` 옵션을 붙이면 실행 중인 컨테이너가 참조하지 않는 이미지까지 전부 삭제한다. 개발 환경에서는 편하지만, 운영 환경에서 무심코 치면 다음 배포 때 이미지를 처음부터 다시 받아야 한다.

### 개별 정리

```bash
# 중지된 컨테이너 삭제
docker container prune

# dangling 이미지 삭제 (태그가 없는 이미지)
docker image prune

# 사용하지 않는 볼륨 삭제
docker volume prune

# 현재 디스크 사용량 확인
docker system df
```

`docker system df`로 현재 상태를 먼저 확인하고 정리하는 습관을 들이면 실수를 줄일 수 있다.

```bash
$ docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          45        5         12.3GB    10.1GB (82%)
Containers      12        3         256MB     198MB (77%)
Local Volumes   8         4         1.2GB     800MB (66%)
Build Cache     -         -         3.5GB     3.5GB
```

RECLAIMABLE이 높으면 정리할 게 많다는 뜻이다.

---

## 자주 겪는 문제

### 포트 충돌

```
Error: Bind for 0.0.0.0:8080 failed: port is already allocated
```

호스트에서 이미 해당 포트를 쓰고 있다는 뜻이다. `lsof -i :8080`으로 누가 쓰고 있는지 확인한다. 중지된 컨테이너가 포트를 물고 있는 경우도 있으니 `docker ps -a`도 확인한다.

### 컨테이너가 바로 종료됨

`docker run`으로 실행했는데 바로 종료되는 경우. 컨테이너는 메인 프로세스(PID 1)가 종료되면 같이 종료된다. `docker logs`로 에러 메시지를 확인하고, Dockerfile의 `CMD`나 `ENTRYPOINT`가 제대로 설정됐는지 본다.

```bash
# 종료 코드 확인
docker inspect -f '{{.State.ExitCode}}' my-app
# 0: 정상 종료, 1: 에러, 137: OOM 또는 SIGKILL, 143: SIGTERM
```

### 컨테이너 안에서 호스트 접근

컨테이너에서 호스트 머신의 서비스에 접근하려면 `host.docker.internal`을 쓴다 (Docker Desktop 기준). Linux에서는 `--network host` 옵션을 쓰거나, 호스트의 docker0 브릿지 IP를 직접 쓴다.

```bash
# Docker Desktop (Mac/Windows)
docker run --rm -it alpine ping host.docker.internal

# Linux
docker run --rm -it --network host alpine ping localhost
```

---

## 참고자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Dockerfile 레퍼런스](https://docs.docker.com/engine/reference/builder/)
- [Docker CLI 레퍼런스](https://docs.docker.com/engine/reference/commandline/cli/)
