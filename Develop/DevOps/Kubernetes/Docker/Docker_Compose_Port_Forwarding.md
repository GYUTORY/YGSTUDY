---
title: Docker Compose Port Forwarding
tags: [docker, docker-compose, port-forwarding, network, devops]
updated: 2026-04-30
---

# Docker Compose Port Forwarding

## 포트 포워딩이 컨테이너에서 왜 까다로운가

Docker 컨테이너는 기본적으로 격리된 네트워크 네임스페이스에서 동작한다. 컨테이너 안에서 80번 포트로 nginx를 띄워도, 호스트에서 `curl localhost:80`을 치면 응답이 없다. 컨테이너의 80과 호스트의 80은 완전히 다른 세계다. 이 둘을 연결해 주는 게 포트 포워딩(포트 매핑)이고, Compose에서는 `ports` 항목으로 표현한다.

`docker run -p 8080:80`이 명령어 한 줄이라면, Compose는 이걸 YAML로 선언하고 여러 서비스에 걸쳐 일관되게 관리할 수 있게 해 준다. 문제는 이 YAML이 단순해 보여서 그냥 `"8080:80"`만 적고 넘어가는 사람이 많은데, 운영에서 사고가 나는 지점이 대부분 여기다. 호스트 IP를 명시하지 않아서 외부에 노출된 DB, UFW 규칙이 우회된 줄도 모르고 운영하다가 침투당하는 사례, Docker Desktop과 Linux의 호스트 네트워크 차이로 로컬에서는 되는데 서버에서는 안 되는 케이스 등이 흔하다.

이 문서는 Compose 환경에서 포트 포워딩이 실제로 어떻게 동작하는지, 어디서 문제가 터지는지, 그리고 그걸 어떻게 디버깅하는지를 다룬다.

---

## ports 단축 문법과 장문 문법

### 단축 문법 (short syntax)

가장 흔히 보는 형태다.

```yaml
services:
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
      - "443:443"
```

`"호스트포트:컨테이너포트"` 순서다. 헷갈리지 말 것. "왼쪽이 바깥, 오른쪽이 안"이라고 외우면 편하다.

따옴표를 빼먹으면 YAML 파서가 콜론을 연산자로 해석해서 `60:60` 같은 큰 숫자를 시간(분:초)으로 잘못 읽는 경우가 있다. `"22:22"`처럼 SSH 포트를 매핑할 때 특히 주의해야 한다. 따옴표를 항상 붙이는 게 안전하다.

호스트 IP까지 지정하는 형태도 있다.

```yaml
services:
  db:
    image: postgres:16
    ports:
      - "127.0.0.1:5432:5432"
```

이건 매우 중요하다. 자세한 건 아래 보안 섹션에서 다룬다.

### 장문 문법 (long syntax)

Compose 파일 명세 v3.8 이후로는 객체 형태로도 쓸 수 있다.

```yaml
services:
  api:
    image: my-api
    ports:
      - target: 3000
        published: 8080
        host_ip: 127.0.0.1
        protocol: tcp
        mode: host
```

필드별 의미는 이렇다.

- `target`: 컨테이너 내부 포트
- `published`: 호스트에 노출할 포트
- `host_ip`: 바인딩할 호스트 IP (생략하면 0.0.0.0)
- `protocol`: tcp 또는 udp
- `mode`: ingress(Swarm 로드밸런서 경유) 또는 host(직접 바인딩). 단일 호스트 Compose에서는 host

장문 문법은 복잡해 보이지만, UDP 서비스나 IP 바인딩, 다중 프로토콜이 섞인 환경에서는 가독성이 훨씬 좋다. 단축 문법으로 `"127.0.0.1:5432:5432/tcp"` 같은 한 줄을 쓰는 것보다 명시적이다.

---

## ports vs expose, 자주 헷갈리는 차이

`expose`는 컨테이너 간 통신용으로 포트를 "선언"만 한다. 호스트에는 노출되지 않는다.

```yaml
services:
  api:
    image: my-api
    expose:
      - "3000"

  web:
    image: nginx
    ports:
      - "80:80"
```

이 구성에서 web 컨테이너는 `http://api:3000`으로 api에 접근할 수 있지만, 호스트에서 `curl localhost:3000`을 쳐도 응답이 없다.

사실 `expose`는 거의 형식적인 항목이다. Compose가 만들어 주는 기본 네트워크 안에서는 같은 네트워크에 속한 컨테이너끼리 모든 포트로 통신할 수 있기 때문에, `expose` 없이도 컨테이너 간 호출은 다 된다. `expose`를 쓰는 실질적 이유는 두 가지 정도다.

1. 문서화 목적. "이 컨테이너는 3000 포트로 서비스한다"는 의도를 YAML에 남긴다.
2. `docker network inspect` 결과나 일부 서비스 디스커버리 도구에서 expose된 포트만 등록하는 경우.

내부 통신용 DB나 백엔드 API는 `ports`로 호스트에 뚫지 말고 같은 네트워크에 두는 게 원칙이다. 호스트에 안 뚫어도 같은 Compose 프로젝트 안의 다른 서비스는 다 접근할 수 있다는 사실을 자주 놓친다.

---

## 호스트 IP 바인딩과 보안

### 0.0.0.0이 기본값이라는 함정

`ports: ["5432:5432"]`로 적으면 `0.0.0.0:5432`에 바인딩된다. 즉 호스트의 모든 네트워크 인터페이스에서 5432 포트로 접근할 수 있다는 뜻이다. 클라우드 인스턴스 같은 공인 IP가 붙은 머신이라면 인터넷 어디서든 DB에 접근 시도가 날아온다.

```yaml
services:
  db:
    image: postgres:16
    ports:
      - "5432:5432"  # 위험. 외부 노출됨
    environment:
      POSTGRES_PASSWORD: hunter2
```

운영 사고의 단골 패턴이다. 개발자가 로컬에서 DB에 접속하려고 ports를 뚫었는데, 그 설정이 그대로 운영으로 올라간다. 클라우드 보안 그룹(AWS Security Group, GCP firewall 등)이 막아 주면 다행이지만, 그 보호 막을 신뢰하지 말고 Compose 레벨에서도 막아야 한다.

### 127.0.0.1로 바인딩

내부에서만 접근할 거라면 명시적으로 루프백 IP에 바인딩한다.

```yaml
services:
  db:
    image: postgres:16
    ports:
      - "127.0.0.1:5432:5432"
```

이러면 호스트의 다른 서비스(예: SSH 터널을 통해 접속한 개발자 도구)는 접근할 수 있지만, 외부 IP로는 들어올 수 없다.

운영 환경에서 굳이 호스트 노출이 필요하다면 reverse proxy(nginx, Traefik) 컨테이너만 외부 노출하고, 나머지는 내부 네트워크로 두는 게 정석이다.

### 특정 인터페이스에 바인딩

머신에 여러 NIC가 있고 특정 인터페이스로만 노출하고 싶다면 그 IP를 직접 적는다.

```yaml
services:
  internal-api:
    image: my-api
    ports:
      - "10.0.1.5:8080:8080"  # 사설망 인터페이스
```

이건 Bare metal 서버나 멀티 NIC 환경에서 유용하다.

---

## TCP/UDP 명시

기본은 TCP다. UDP 서비스를 띄울 때는 반드시 명시해야 한다.

```yaml
services:
  dns:
    image: my-dns
    ports:
      - "53:53/udp"
      - "53:53/tcp"  # DNS는 둘 다 필요
```

DNS, NTP, syslog, WireGuard, RTP 같은 UDP 기반 서비스는 `/udp`를 빠뜨리면 패킷이 안 들어온다. 가장 자주 보는 사고는 DNS 컨테이너에서 TCP만 매핑하고 "DNS 쿼리가 안 되네?" 하고 한참 헤매는 케이스다.

장문 문법으로 쓰면 더 명확하다.

```yaml
ports:
  - target: 53
    published: 53
    protocol: udp
  - target: 53
    published: 53
    protocol: tcp
```

---

## IPv6

IPv6 주소를 호스트 IP로 지정할 때는 대괄호를 써야 한다.

```yaml
services:
  web:
    ports:
      - "[::1]:8080:80"
```

다만 Docker daemon에서 IPv6가 켜져 있어야 한다. `/etc/docker/daemon.json`에 `"ipv6": true`와 `"fixed-cidr-v6"` 설정이 필요하다. 기본 설치 상태에서는 IPv6 매핑이 동작하지 않는 경우가 많아서, 운영에서 IPv6 트래픽을 받으려면 daemon 설정부터 점검해야 한다.

`docker compose ps` 결과에서 IPv6 포트가 표시되지 않는다고 IPv6가 안 되는 게 아니라, 표시 자체가 빈약한 경우도 많다. `ss -tlnp | grep <포트>`로 실제 바인딩을 확인하는 게 정확하다.

---

## 동적 포트 할당

호스트 포트를 비워 두면 Docker가 임시 포트(보통 32768~60999 범위)를 자동 배정한다.

```yaml
services:
  api:
    image: my-api
    ports:
      - "3000"  # 호스트 포트는 랜덤
```

CI 환경에서 여러 빌드가 동시에 돌 때 포트 충돌을 피하려고 자주 쓴다. 배정된 포트는 `docker compose port` 명령으로 확인한다.

```bash
$ docker compose port api 3000
0.0.0.0:49154
```

테스트 스크립트는 이 명령의 출력을 파싱해서 동적으로 엔드포인트를 잡는다. 하드코딩한 포트로 테스트하면 충돌이 나거나 다른 빌드의 컨테이너에 잘못 붙는다.

---

## 포트 범위 매핑

연속된 포트 여러 개를 한 번에 매핑할 수 있다.

```yaml
services:
  rtp-server:
    image: my-rtp
    ports:
      - "10000-10100:10000-10100/udp"
```

WebRTC, SIP, 게임 서버처럼 여러 포트를 동시에 쓰는 서비스에서 유용하다. 단 매핑할 포트가 많을수록 iptables 규칙이 그만큼 늘어나서, 컨테이너 시작 시간이 눈에 띄게 느려질 수 있다. 1000개 이상 포트를 매핑하면 `docker compose up`이 수십 초 걸리는 경우도 봤다. 그런 경우는 차라리 `network_mode: host`를 검토하는 게 낫다.

호스트 측 포트만 범위로 두고 컨테이너 포트는 단일로 둘 수도 있는데, 이 조합은 동작 방식이 헷갈리기 쉬워서 잘 안 쓴다.

---

## 환경별 포트 분리 (dev/prod)

같은 서비스라도 개발과 운영에서 다른 포트를 쓰고 싶은 경우가 많다. Compose의 override 메커니즘을 활용한다.

### 베이스 파일

`docker-compose.yml`에는 운영에 가까운 기본값을 둔다.

```yaml
# docker-compose.yml
services:
  web:
    image: my-web
    ports:
      - "80:8080"
  db:
    image: postgres:16
    # ports를 아예 두지 않음. 내부 통신만
```

### 개발용 override

`docker-compose.override.yml`은 `docker compose up` 시 자동으로 병합된다.

```yaml
# docker-compose.override.yml
services:
  web:
    ports:
      - "8080:8080"  # 80은 sudo 없이 못 쓰니까
  db:
    ports:
      - "127.0.0.1:5432:5432"  # 로컬에서 DB 클라이언트로 접속하려고
```

### 운영용 별도 파일

운영에서는 override를 끄거나 다른 파일을 명시한다.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

이때 주의할 점이 하나 있다. `ports`는 병합이 아니라 "추가"된다. 베이스에서 `"80:8080"`을 정의하고 override에서 `"8080:8080"`을 정의하면 두 매핑이 모두 적용된다. 한쪽만 적용되길 원한다면 override에서 `!reset` 또는 `!override` 태그를 써야 한다(Compose v2.20 이후).

```yaml
# docker-compose.override.yml
services:
  web:
    ports: !override
      - "8080:8080"
```

이 기능을 모르면 "분명 dev에서는 80 안 쓰는데 왜 80이 떠 있지?" 하고 헷갈린다.

---

## 같은 호스트에 여러 Compose 프로젝트

한 머신에 여러 프로젝트를 동시에 띄우면 가장 흔한 이슈가 포트 충돌이다.

```
프로젝트 A: web에 8080 매핑
프로젝트 B: web에 8080 매핑
→ 두 번째 프로젝트의 up이 "port already allocated" 에러로 실패
```

해결 방법은 몇 가지가 있다.

### 환경변수로 포트 외부 주입

```yaml
services:
  web:
    image: my-web
    ports:
      - "${WEB_PORT:-8080}:8080"
```

```bash
# 프로젝트 A
WEB_PORT=8080 docker compose up -d

# 프로젝트 B
WEB_PORT=8081 docker compose up -d
```

`.env` 파일을 프로젝트별로 다르게 두면 자연스럽다.

### 동적 포트로 두고 reverse proxy로 묶기

각 프로젝트는 호스트 포트를 빈 값으로 두고, 별도의 nginx나 Traefik 컨테이너가 도메인 기반으로 라우팅한다. 로컬 개발에서 여러 프로젝트를 동시에 돌릴 때 권장하는 패턴이다.

### Compose 프로젝트 이름 분리

`COMPOSE_PROJECT_NAME` 또는 `-p` 옵션으로 프로젝트 이름을 분리하면 컨테이너/네트워크 이름 충돌은 피할 수 있지만, 호스트 포트 충돌 자체는 막아 주지 않는다. 이건 흔한 오해다.

---

## depends_on과 포트 가용성

`depends_on`은 컨테이너가 "시작"되기를 기다릴 뿐, 안의 애플리케이션이 포트를 열고 요청을 받을 준비가 되었는지는 보장하지 않는다.

```yaml
services:
  api:
    depends_on:
      - db
```

이 설정으로 api가 db보다 먼저 죽어 버리는 일은 막을 수 있지만, db 컨테이너가 막 시작된 직후 PostgreSQL이 아직 초기화 중일 때 api가 connection을 시도하면 실패한다.

이걸 해결하는 정석은 `condition: service_healthy`다.

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    depends_on:
      db:
        condition: service_healthy
```

healthcheck가 통과해야 api가 시작된다. 포트 매핑과 직접 관련은 없지만, "포트 매핑은 됐는데 요청이 안 된다"는 증상의 절반은 이 readiness 문제다.

애플리케이션 자체가 재시도 로직을 갖추는 게 더 견고한 방법이다. healthcheck는 외부에서 보는 신호이고, 진짜 안전망은 클라이언트의 백오프 재연결이다.

---

## UFW/firewalld 우회 문제

이건 운영에서 진짜 사고가 자주 나는 지점이다.

Docker는 컨테이너 포트를 노출할 때 iptables의 `nat` 테이블에 직접 규칙을 추가한다. 이 규칙은 UFW나 firewalld의 `INPUT` 체인보다 먼저 매칭된다. 결과적으로 UFW에서 5432를 막아 두었더라도, Compose에서 `"5432:5432"`로 매핑한 순간 외부에서 5432로 들어오는 트래픽이 컨테이너까지 도달한다.

```bash
$ ufw status
Status: active
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
# 5432는 명시적으로 허용한 적 없음

$ docker compose up -d   # postgres에 ports: ["5432:5432"]
$ # 외부에서 접속이 됨
```

해결책은 둘 중 하나다.

1. 호스트 IP를 명시해서 외부 노출을 막는다. `"127.0.0.1:5432:5432"`.
2. `/etc/docker/daemon.json`에 `"iptables": false`로 두고 직접 NAT 규칙을 관리한다. 이건 운영 부담이 커서 잘 안 쓴다.

가장 안전한 패턴은 "운영에서 외부 노출이 필요한 컨테이너는 reverse proxy 한 대뿐, 나머지는 내부 네트워크"다. 이 원칙을 지키면 UFW 우회 문제는 거의 안 만난다.

---

## Docker Desktop(macOS/Windows)에서의 차이

Linux에서는 호스트와 컨테이너가 같은 커널을 공유한다. `127.0.0.1:8080:80`으로 매핑하면 호스트의 lo 인터페이스에 바로 바인딩된다.

Docker Desktop은 다르다. 안에서 가상머신(LinuxKit 또는 WSL2)을 돌리고, Docker daemon은 그 VM 안에 있다. 컨테이너 포트는 일단 VM의 IP에 바인딩되고, Docker Desktop의 vpnkit(또는 wsl-relay)이 호스트 OS와 VM 사이를 프록시한다.

이 구조 때문에 생기는 차이가 몇 가지 있다.

### 호스트의 다른 서비스 접근

Linux에서는 컨테이너 안에서 호스트의 다른 서비스에 접근하려면 호스트 IP를 알아야 하지만, Docker Desktop은 `host.docker.internal`이라는 특수 호스트명을 제공한다. 컨테이너에서 `host.docker.internal:5432`로 호스트의 PostgreSQL에 접근할 수 있다.

Linux에서도 Compose v2.x에서는 `extra_hosts: ["host.docker.internal:host-gateway"]`를 추가하면 같은 동작을 흉내 낼 수 있다.

### network_mode: host의 동작 차이

Linux에서 `network_mode: host`는 컨테이너가 호스트 네트워크 네임스페이스를 그대로 쓴다. ports 매핑이 무의미해지고, 컨테이너 안의 서비스가 호스트 인터페이스에 바로 바인딩된다.

Docker Desktop에서는 다르다. macOS/Windows에서 host 모드를 쓰면 호스트가 아니라 VM의 네트워크에 바인딩된다. 즉 호스트 OS에서는 그 포트로 접근이 안 될 수 있다. 최근 버전에서 이게 일부 개선되었지만 여전히 Linux와 동일하지 않다. "Linux 서버에서는 host 모드로 잘 되는데 맥에서는 안 된다"는 증상은 거의 항상 이 문제다.

### 성능

Docker Desktop의 포트 포워딩은 vpnkit 프록시를 거치기 때문에 고처리량 환경에서 병목이 된다. 부하 테스트를 macOS Docker Desktop에서 돌리면 Linux 서버 결과와 다르다는 걸 인지하고 있어야 한다.

---

## 컨테이너 내부 애플리케이션의 0.0.0.0 바인딩

Compose에서 ports 매핑을 정확히 설정해도, 컨테이너 안의 애플리케이션이 `127.0.0.1`에만 바인딩하고 있으면 외부에서 접근할 수 없다.

```python
# Flask 예시. 이건 잘못된 설정
app.run(host="127.0.0.1", port=3000)
```

컨테이너 입장에서 `127.0.0.1`은 컨테이너 자기 자신만 접근할 수 있는 주소다. 호스트에서 `8080:3000`으로 매핑해도, Docker가 패킷을 컨테이너의 eth0으로 전달하지만 애플리케이션은 lo만 듣고 있어서 응답이 없다.

```python
# 이렇게 해야 한다
app.run(host="0.0.0.0", port=3000)
```

Node.js Express의 `app.listen(3000)`은 기본적으로 모든 인터페이스에 바인딩하지만, 명시적으로 `app.listen(3000, "127.0.0.1")`로 적어 두면 같은 함정에 빠진다. Spring Boot도 마찬가지로 `server.address`가 설정되어 있으면 의도와 다르게 동작할 수 있다.

증상은 비슷하다. `docker compose ps`에는 포트 매핑이 잘 떠 있고, `docker compose port`도 정상 출력하는데, `curl localhost:8080`만 응답이 없다. 이때는 컨테이너 내부에서 직접 확인해야 한다.

```bash
docker compose exec api ss -tlnp
# 또는
docker compose exec api netstat -tlnp
```

`127.0.0.1:3000`으로 떠 있다면 애플리케이션 설정 문제다.

---

## healthcheck로 포트 readiness 확인

healthcheck는 컨테이너 안에서 실행되는 명령으로 컨테이너 상태를 판단한다. 포트가 실제로 응답하는지 확인하는 용도로 자주 쓴다.

```yaml
services:
  api:
    image: my-api
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 30s
```

여기서 `localhost`는 컨테이너 자기 자신을 가리킨다. 호스트 포트(예: 외부에서 보이는 8080)가 아니라 컨테이너 내부 포트로 체크해야 한다.

`start_period`는 초기 부팅 시간이 긴 애플리케이션(JVM 기반 등)에서 중요하다. 이 기간 동안의 실패는 카운트되지 않는다. 안 두면 컨테이너가 시작 직후 healthcheck 실패로 unhealthy 상태가 되고, 다른 서비스의 `condition: service_healthy`가 영원히 통과하지 못한다.

healthcheck로 포트가 살아 있는지 확인하는 건 좋지만, "포트가 열렸다"와 "비즈니스 로직이 정상"은 다르다. `/health` 같은 엔드포인트를 만들 때 DB 연결까지 검사할지 단순히 200만 반환할지는 트레이드오프다. DB까지 검사하면 DB가 일시적으로 끊어졌을 때 모든 API 컨테이너가 unhealthy가 되고, 트래픽이 다 끊긴다. 보통은 liveness(프로세스가 살아 있는가)와 readiness(트래픽 받을 준비가 됐는가)를 분리하는 게 안전하다. Compose의 healthcheck 하나로는 둘을 분리할 수 없어서, 운영 환경에서는 별도의 LB 헬스체크를 두는 경우가 많다.

---

## 포트 매핑이 적용되지 않을 때 디버깅 절차

증상은 다양하지만 진단 순서는 거의 정해져 있다. 위에서 아래로 순서대로 확인한다.

### 1단계: Compose가 포트를 어떻게 인식하는지

```bash
docker compose config
```

YAML 파싱 결과를 출력한다. `.env`나 override가 적용된 최종 형태다. 의도한 포트가 정말 적용되었는지 우선 여기서 확인한다.

### 2단계: 컨테이너에 어떤 포트 매핑이 붙어 있는지

```bash
docker compose ps
docker compose port <service> <container_port>
```

`docker compose ps`는 매핑을 요약해서 보여 주고, `docker compose port`는 정확한 호스트 IP:Port를 출력한다. 동적 포트일 때 특히 유용하다.

```bash
$ docker compose port api 3000
0.0.0.0:8080
```

### 3단계: 호스트에서 실제로 바인딩되었는지

```bash
ss -tlnp | grep 8080
# 또는 macOS/BSD라면
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

`ss` 결과에 `docker-proxy` 또는 dockerd 관련 프로세스가 떠 있으면 정상이다. 안 뜨면 Docker가 매핑을 만들지 못한 거다. 이 경우 dockerd 로그(`journalctl -u docker`)를 확인한다.

### 4단계: iptables 규칙 확인

```bash
sudo iptables -t nat -L DOCKER -n
```

`DNAT` 규칙으로 호스트 포트가 컨테이너 IP로 포워딩되는 게 보여야 한다. 규칙이 없거나 이상하면 dockerd 재시작이 필요할 수 있다.

iptables 규칙이 다른 도구(쿠버네티스, kube-proxy, 네트워크 보안 도구 등)에 의해 덮어쓰여지는 경우도 있다. 같은 호스트에 docker와 다른 컨테이너 런타임이 섞여 있으면 의심해야 한다.

### 5단계: 컨테이너 내부 애플리케이션 확인

```bash
docker compose exec <service> ss -tlnp
```

컨테이너 안에서 애플리케이션이 `0.0.0.0` 또는 `::`에 바인딩되어 있는지 본다. `127.0.0.1`이면 애플리케이션 코드를 고쳐야 한다.

### 6단계: 호스트에서 직접 요청 보내기

```bash
curl -v http://127.0.0.1:8080/
```

여기서 응답이 정상이면 매핑은 잘 된 거고, 외부에서 안 되는 건 방화벽이나 클라우드 보안 그룹 문제다.

### 7단계: 외부에서 요청

다른 머신에서 `curl -v http://<호스트IP>:8080/`을 친다. timeout이면 방화벽, "Connection refused"면 호스트가 그 IP에 바인딩하지 않은 것(예: 127.0.0.1에만 바인딩됨), "Connection reset"이면 애플리케이션이 응답을 거부하는 상황(인증, CORS, 등)이다.

이 7단계로 거의 모든 포트 매핑 문제를 좁혀 낼 수 있다. 한두 단계만 보고 추측으로 넘어가지 말 것. 시간 더 든다.

---

## 실전 예제: 일반적인 웹 서비스 구성

마지막으로 실무에서 자주 쓰는 형태를 한 덩어리로 정리한다.

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      api:
        condition: service_healthy
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro

  api:
    build: ./api
    expose:
      - "3000"
    environment:
      DB_HOST: db
      DB_PORT: 5432
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/health"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 30s

  db:
    image: postgres:16
    ports:
      - "127.0.0.1:5432:5432"  # 개발자가 로컬 클라이언트로 접속하려고
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  db-data:
```

핵심 포인트.

- nginx만 외부에 노출(80, 443). 이게 유일한 진입점이다.
- api는 `expose`만 두고 호스트에 노출하지 않는다. nginx와 같은 네트워크에 있으므로 `http://api:3000`으로 접근 가능하다.
- db는 `127.0.0.1`에만 바인딩해서 외부 노출을 막는다. 운영에서는 이 매핑조차 빼는 게 더 안전하다.
- depends_on에 `condition: service_healthy`를 걸어서 시작 순서뿐 아니라 readiness까지 보장한다.
- DB 비밀번호 같은 민감 정보는 `.env`나 외부 시크릿으로 분리한다.

이 정도 골격을 기본으로 깔고, 필요에 따라 override 파일에서 환경별로 포트와 노출 정책을 조정하면 대부분의 케이스를 커버할 수 있다.
