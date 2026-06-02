---
title: Docker 환경에서 Caddy 운영 심화
tags:
  - WebServer
  - Caddy
  - Docker
  - Kubernetes
  - Swarm
  - CertMagic
  - Production
updated: 2026-06-03
---

# Docker 환경에서 Caddy 운영 심화

기존 `Docker_Caddy.md`가 공식 이미지 구조, Caddyfile 마운트, `/data` 볼륨 영속화 같은 단일 컨테이너 운영의 기초를 다뤘다면, 이 문서는 그 다음 단계의 이야기다. Caddy 인스턴스가 한 대일 때는 보이지 않던 문제가, 컨테이너를 두 대 이상 띄우거나 Kubernetes/Swarm에 올리는 순간부터 줄줄이 터진다. 인증서 락 충돌, 종료 시그널 처리, rootless 운영, admin API 노출 사고, 메트릭 파이프라인, 멀티 아키텍처 빌드, zero-downtime 배포, 시크릿 주입, OOMKilled 디버깅 같은 주제를 실제 production 코드와 함께 짚는다.

## 분산 스토리지 모듈로 인증서 공유

Caddy 인스턴스가 한 대일 때는 `/data`만 볼륨으로 빼면 끝난다. 그런데 Swarm이나 Kubernetes에 replica 3개로 띄우면 문제가 시작된다. 각 인스턴스가 같은 도메인에 대해 ACME 주문을 동시에 넣고, Let's Encrypt 입장에서는 같은 도메인에 대한 중복 발급으로 보인다. 운이 좋으면 한 인스턴스만 성공하고 나머지는 실패한 채 재시도하고, 운이 나쁘면 rate limit에 걸려서 전체가 멈춘다.

해결책은 CertMagic이 제공하는 분산 스토리지 모듈이다. 인증서·계정 키·발급 락을 외부 스토리지에 저장하면, 여러 인스턴스가 같은 상태를 보고 한 인스턴스만 발급을 수행한다. 공식적으로 지원되는 스토리지는 Redis, Consul, etcd, DynamoDB, S3, GCS, Azure Blob 등이고 커뮤니티 모듈로도 다수 존재한다.

Redis 기반 구성 예시. `caddy-storage-redis` 모듈을 xcaddy로 빌드해서 이미지에 포함시킨다.

```dockerfile
FROM caddy:2.8-builder AS builder
RUN xcaddy build \
    --with github.com/pberkel/caddy-storage-redis

FROM caddy:2.8-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Caddyfile의 global 옵션에 storage 설정을 박는다.

```caddyfile
{
    storage redis {
        host           redis.internal
        port           6379
        password       {env.REDIS_PASSWORD}
        db             0
        key_prefix     caddy
        timeout        5
        tls_enabled    true
        tls_insecure   false
    }
    email ops@example.com
}

example.com {
    reverse_proxy backend:8080
}
```

핵심은 `key_prefix`다. 같은 Redis를 다른 용도로 쓰는 경우 키 충돌을 막아야 하고, 멀티 환경(staging/production)을 한 Redis로 처리한다면 환경별로 prefix를 분리해야 한다. 같은 prefix를 공유하면 staging이 production 인증서를 덮어쓰는 사고가 난다.

S3 기반은 비용이 가장 싸지만 발급 락의 latency가 높다. CertMagic은 락 획득 시 5초 간격으로 폴링하는데, S3의 strong consistency가 보장되더라도 실제 락 진입 지연이 누적된다. 대규모 클러스터에서는 Redis나 Consul이 무난하다.

분산 스토리지를 쓰더라도 발급 폭주를 완전히 막지는 못한다. 인스턴스가 부팅 시 일제히 같은 도메인을 요청하면, 락을 한 인스턴스만 잡지만 나머지는 대기 큐에 쌓인다. 부팅을 staggered로 하거나, 초기 인증서를 미리 발급해 두고 갱신만 분산 처리하는 패턴이 안전하다.

## SIGTERM 처리와 graceful shutdown

Docker가 컨테이너를 종료할 때의 시그널 시퀀스는 단순하다. 먼저 STOPSIGNAL로 지정된 시그널(기본 SIGTERM)을 PID 1에 보내고, `--stop-timeout`(기본 10초) 안에 종료되지 않으면 SIGKILL을 보낸다. Kubernetes도 동일한 흐름이지만 `terminationGracePeriodSeconds`(기본 30초)가 타임아웃이 된다.

Caddy는 SIGTERM을 받으면 `caddy stop`과 동일하게 동작한다. 새 연결 수신을 멈추고, 기존 연결의 in-flight 요청이 끝날 때까지 기다린다. HTTP/2 stream과 WebSocket이 살아 있으면 그 연결도 정상 종료를 기다린다. 문제는 stop timeout이다. 10초가 짧다. 백엔드가 30초짜리 응답을 만들고 있으면 SIGKILL이 떨어지면서 연결이 끊긴다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    stop_grace_period: 60s
    stop_signal: SIGTERM
    ports:
      - "80:80"
      - "443:443"
```

`stop_grace_period`를 백엔드 응답의 p99보다 크게 잡는다. 60초가 보통이다. Kubernetes에서는 다음 형태로 매핑된다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caddy
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: caddy
        image: my-caddy:1.0
        lifecycle:
          preStop:
            exec:
              command:
                - sh
                - -c
                - "sleep 10 && caddy stop --config /etc/caddy/Caddyfile"
```

preStop 훅의 `sleep 10`은 Endpoints에서 Pod가 빠지기까지의 전파 시간을 흡수하기 위한 것이다. kube-proxy가 iptables 규칙을 업데이트하기 전에 Caddy가 먼저 새 연결을 거부하면, 그 사이 들어온 트래픽이 502를 받는다. sleep으로 그 간극을 메우고, 그 다음에 명시적으로 `caddy stop`을 호출한다. preStop이 끝난 뒤에 컨테이너로 SIGTERM이 들어가지만, 이미 caddy가 종료 단계에 있으니 중복 처리는 문제 없다.

Dockerfile에서 STOPSIGNAL을 직접 지정할 수도 있다.

```dockerfile
FROM caddy:2.8-alpine
COPY Caddyfile /etc/caddy/Caddyfile
STOPSIGNAL SIGTERM
```

Caddy는 SIGTERM과 SIGINT 모두 같은 종료 핸들러를 탄다. SIGQUIT은 즉시 종료다. 따라서 graceful 종료를 원한다면 SIGQUIT을 쓰면 안 된다.

drain 동작의 한계는 한 가지 있다. WebSocket 같은 장수명 연결은 graceful 종료가 무의미하다. Caddy는 클라이언트가 자발적으로 끊지 않는 한 무한정 기다린다. 결국 stop_grace_period 만료 시 SIGKILL로 끊긴다. WebSocket 서비스라면 백엔드에서 reconnect 로직을 보장해야 한다.

## Rootless 운영과 최소 권한

기본 `caddy` 이미지는 root로 실행된다. 80/443 포트가 1024 미만이라 바인딩을 위해 root가 필요하다는 게 통념이지만, Linux의 `CAP_NET_BIND_SERVICE` capability만 주면 non-root 유저로도 가능하다.

```dockerfile
FROM caddy:2.8-alpine

RUN addgroup -S caddy && adduser -S -G caddy caddy && \
    setcap cap_net_bind_service=+ep /usr/bin/caddy && \
    mkdir -p /data /config && \
    chown -R caddy:caddy /data /config /etc/caddy

USER caddy
EXPOSE 80 443
ENTRYPOINT ["/usr/bin/caddy"]
CMD ["run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
```

`setcap`은 바이너리에 capability를 영구적으로 부여한다. 컨테이너 런타임에서 capability를 떨어뜨리면 무용지물이 되니, docker run 시 `--cap-drop=ALL --cap-add=NET_BIND_SERVICE` 형태로 명시적으로 부여해야 한다.

```yaml
services:
  caddy:
    image: my-caddy-rootless:1.0
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    security_opt:
      - no-new-privileges:true
```

`read_only: true`는 루트 파일시스템을 읽기 전용으로 마운트한다. Caddy가 임시 파일을 쓰는 경로가 있다면 tmpfs로 마운트해줘야 한다. 보통 `/tmp` 정도면 충분하다. `/data`와 `/config`는 별도 볼륨으로 쓰기 가능한 상태가 되어야 한다.

seccomp 프로파일은 Docker의 기본 프로파일이 이미 대부분의 위험한 syscall을 차단한다. 더 좁히려면 Caddy가 실제로 호출하는 syscall만 허용하는 커스텀 프로파일을 만들어야 하는데, 운영 부담이 크다. 보통 기본 프로파일 + no-new-privileges 조합으로 충분하다.

AppArmor는 Debian/Ubuntu 호스트에서 추가로 적용 가능하다. Docker는 기본적으로 `docker-default` AppArmor 프로파일을 적용하는데, Caddy 전용 프로파일을 만들고 싶다면 `/etc/apparmor.d/docker-caddy` 같은 위치에 정의하고 `security_opt: ["apparmor=docker-caddy"]`로 지정한다. RHEL 계열에서는 SELinux 컨텍스트가 같은 역할을 한다.

User namespace remapping(`/etc/docker/daemon.json`의 `userns-remap`)을 함께 쓰면 컨테이너 내부의 root조차 호스트에서는 비특권 유저로 매핑된다. 다만 volume 권한 관리가 까다로워지므로 단일 호스트가 아닌 경우 추천하지 않는다.

## 리소스 제한과 GOMAXPROCS

cgroup으로 CPU/메모리 제한을 거는 건 production의 기본이다. 그런데 Go 런타임의 GOMAXPROCS는 cgroup CPU 제한을 자동으로 인식하지 못한다. 호스트가 32코어인데 컨테이너에 `cpus: 2`를 줬다면, Go는 여전히 GOMAXPROCS=32로 동작한다. 결과적으로 스케줄러 컨텍스트 스위칭이 과다해지고 GC 정지 시간이 길어진다.

Caddy 2.7부터는 `automaxprocs`가 자동 적용되지 않는다. 직접 환경변수로 박아야 한다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 512M
        reservations:
          cpus: "1"
          memory: 256M
    environment:
      GOMAXPROCS: "2"
      GOMEMLIMIT: "450MiB"
```

`GOMEMLIMIT`는 Go 1.19+의 soft memory limit이다. 컨테이너 memory limit보다 약간 낮게 잡으면 OOMKilled 직전에 GC가 더 공격적으로 동작한다. limit이 512MB라면 GOMEMLIMIT은 450MB 정도가 적당하다. 너무 빡빡하게 잡으면 GC가 폭주해서 CPU를 다 먹는다.

File descriptor 제한도 자주 놓치는 부분이다. Alpine 이미지의 기본 ulimit은 1024로, 동시 연결 1000건만 받아도 fd가 고갈된다. Caddy는 클라이언트 연결 + 백엔드 연결 + 로그 파일 + 인증서 파일 등으로 fd를 소비하므로 실질 한도는 더 낮다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

Kubernetes에서는 노드 레벨의 `/etc/security/limits.conf`나 systemd 유닛의 LimitNOFILE을 조정해야 Pod에도 반영된다. containerd는 Pod의 ulimit을 직접 지정하는 옵션이 없어서 노드 설정이 그대로 상속된다.

연결 수 한계의 또 다른 변수는 conntrack 테이블이다. 호스트의 `nf_conntrack_max`가 작으면 동시 연결이 한도에 닿아 새 연결이 SYN_RECV에서 막힌다. `sysctl net.netfilter.nf_conntrack_max=1048576` 같은 형태로 노드 레벨에서 늘려둬야 한다.

## Admin API 노출 사고 방지

Caddy의 admin API(기본 포트 2019)는 인증이 없다. 누구든 접근 가능하면 Caddyfile을 통째로 바꾸거나 Caddy를 종료시킬 수 있다. 그런데 컨테이너 운영 중 admin API를 외부에 노출시키는 사고가 의외로 흔하다.

위험한 패턴.

```yaml
services:
  caddy:
    image: caddy:2.8-alpine
    ports:
      - "80:80"
      - "443:443"
      - "2019:2019"
```

`2019:2019` 한 줄로 인터넷에서 admin API가 접근 가능해진다. Shodan에 그대로 노출된다. 절대 이렇게 하면 안 된다.

기본적으로 Caddy는 admin API를 `localhost:2019`에만 바인딩한다. 컨테이너 내부의 localhost는 컨테이너 안에서만 접근 가능하므로 안전하다. 그런데 외부에서 caddy reload를 트리거하고 싶어서 위처럼 호스트 포트로 빼는 사례가 생긴다.

올바른 패턴은 두 가지다. 첫째, Unix socket으로 바인딩.

```caddyfile
{
    admin unix//var/run/caddy/admin.sock
}
```

```yaml
services:
  caddy:
    image: my-caddy:1.0
    volumes:
      - caddy_admin_sock:/var/run/caddy

  deploy-controller:
    image: my-controller:1.0
    volumes:
      - caddy_admin_sock:/var/run/caddy:ro
```

같은 socket 볼륨을 공유하는 컨테이너만 admin API에 접근할 수 있다. 외부 노출이 원천 차단된다.

둘째, 내부 네트워크 전용 바인딩.

```caddyfile
{
    admin caddy:2019 {
        origins caddy admin.internal
    }
}
```

```yaml
services:
  caddy:
    image: my-caddy:1.0
    networks:
      public:
      internal:
        aliases:
          - admin.internal
    ports:
      - "80:80"
      - "443:443"

networks:
  public:
  internal:
    internal: true
```

`internal: true` 네트워크는 Docker가 외부 라우팅을 차단한다. admin API가 이 네트워크에만 떠 있으면 같은 internal 네트워크에 연결된 컨테이너만 호출할 수 있다. `origins` 디렉티브로 Host 헤더 검증까지 추가하면 잘못된 호출도 막힌다.

reload 자동화가 필요하면 `caddy reload` 명령은 admin API를 호출하므로, 같은 컨테이너 안에서 `docker exec`로 실행하는 게 가장 안전하다.

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

## Prometheus 메트릭과 로그 파이프라인

Caddy는 `metrics` 디렉티브를 켜면 Prometheus 포맷 메트릭을 admin API와 같은 포트에 노출한다.

```caddyfile
{
    servers {
        metrics
    }
    admin :2019
}

:80 {
    metrics /metrics
    reverse_proxy backend:8080
}
```

여기에 함정이 있다. `metrics` 디렉티브를 별도 사이트 블록에 두면 admin API와 같은 포트를 쓰지 않고도 노출할 수 있다. 그래도 별도 사이트로 분리하는 게 운영상 깔끔하다.

```caddyfile
{
    servers {
        metrics
    }
}

:9090 {
    metrics /metrics
}

example.com {
    reverse_proxy backend:8080
}
```

`:9090`은 내부 메트릭 전용 포트로 쓴다. Prometheus가 스크랩하고, 외부엔 노출하지 않는다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    expose:
      - "9090"
    ports:
      - "80:80"
      - "443:443"
    networks:
      - public
      - monitoring

  prometheus:
    image: prom/prometheus:v2.55
    networks:
      - monitoring
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
```

`expose`는 컨테이너 간 노출이고 호스트엔 매핑되지 않는다. Prometheus 컨테이너가 같은 `monitoring` 네트워크에 있으면 `caddy:9090/metrics`로 스크랩한다.

Caddy 메트릭은 시계열당 카디널리티가 꽤 높다. HTTP 메서드, status code, 호스트별로 라벨이 붙어서 호스트 수가 많으면 메트릭 폭증이 일어난다. 도메인 1000개를 처리하는 Caddy 인스턴스라면 Prometheus에서 별도 federation이나 recording rule을 고려해야 한다.

cAdvisor + node-exporter 조합은 컨테이너 단위 자원 사용량과 노드 시스템 메트릭을 함께 본다. cAdvisor가 Caddy 컨테이너의 메모리·CPU·네트워크 I/O를, node-exporter가 호스트의 conntrack 카운트나 fd 사용량을 보여준다. Caddy 자체 메트릭만으로는 OOMKilled 원인 분석이 어렵다.

로그는 JSON 포맷으로 stdout에 떨어뜨리고, 로그 드라이버로 외부로 보낸다.

```caddyfile
{
    log {
        output stdout
        format json
        level INFO
    }
}
```

Loki로 보내는 경우 docker 로그 드라이버를 쓴다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-batch-size: "400"
        loki-retries: "5"
        loki-max-backoff: "800ms"
        max-size: "50m"
        max-file: "3"
```

`loki-url`이 Caddy 컨테이너 시작 시점에 응답하지 못하면 컨테이너 시작이 막힐 수 있다. Loki가 같은 compose에 있다면 `depends_on`으로 순서를 잡고, 다른 호스트에 있다면 `loki-retries`로 버틴다.

기본 `json-file` 로그 드라이버의 한계는 명확하다. `max-size`와 `max-file`로 회전을 걸어도 디스크에 누적된다. 트래픽이 큰 서비스에서는 하루 만에 수십 GB가 쌓인다. 운영 초기엔 json-file로 시작했다가 트래픽이 늘면 Loki/Fluentd로 옮기는 패턴이 흔한데, 옮기는 시점에 누적된 로그 파일이 호스트 디스크를 점령한 상태로 발견되는 경우가 많다. 운영 초기부터 외부 파이프라인으로 빼는 게 낫다.

## Multi-arch 빌드와 xcaddy CGO 이슈

ARM 기반 인스턴스(AWS Graviton, GCP Tau T2A)가 비용 면에서 매력적이라 amd64/arm64 양쪽을 지원하는 이미지가 필요한 경우가 많다. Docker buildx로 빌드한다.

```bash
docker buildx create --name multi --use
docker buildx inspect --bootstrap

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag registry.internal/my-caddy:1.0 \
    --push \
    .
```

QEMU 에뮬레이션으로 cross 빌드가 가능하지만, xcaddy가 들어가는 빌드 단계는 함정이 있다. xcaddy는 내부적으로 `go build`를 호출하는데, 일부 플러그인은 CGO에 의존한다. 멀티 아키텍처 빌드 시 CGO를 켜면 cross-compile용 C 툴체인이 필요해지고, Alpine 베이스에서는 musl 헤더 충돌까지 겹친다.

해결책은 CGO를 비활성화하는 것이다.

```dockerfile
FROM --platform=$BUILDPLATFORM caddy:2.8-builder AS builder
ARG TARGETOS
ARG TARGETARCH

ENV CGO_ENABLED=0
ENV GOOS=$TARGETOS
ENV GOARCH=$TARGETARCH

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/pberkel/caddy-storage-redis

FROM caddy:2.8-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

`CGO_ENABLED=0`이면 순수 Go 빌드가 되어 cross-compile이 단순해진다. `--platform=$BUILDPLATFORM`은 빌더 이미지를 호스트 아키텍처로 가져와서 빌드 자체는 네이티브로 돌리고, 결과물만 타겟 아키텍처로 출력하라는 의미다. QEMU로 builder를 통째로 에뮬레이션하면 빌드가 10배 이상 느려진다.

CGO를 끄면 일부 DNS resolver의 동작이 달라진다. Go의 netgo resolver는 `/etc/resolv.conf`를 직접 파싱하는데, glibc의 resolver와 처리 방식이 미묘하게 다르다. 대부분의 운영 환경에서는 문제가 안 되지만, search domain이 복잡하게 얽혀 있는 환경에서는 DNS 조회 결과가 달라질 수 있다.

xcaddy로 빌드한 바이너리는 빌드 정보를 포함하므로 검증이 쉽다.

```bash
docker run --rm registry.internal/my-caddy:1.0 caddy list-modules --versions
```

## Zero-downtime 배포 패턴

Caddy 인스턴스를 교체할 때 인증서 락 충돌이 가장 골치 아프다. 분산 스토리지를 안 쓰는 환경에서 같은 도메인을 가진 새 인스턴스가 뜨면 이전 인스턴스와 동시에 ACME 주문을 시도하고, Let's Encrypt에 "pending order"가 두 개 쌓인다.

Rolling update에서 발생하는 또 다른 문제는 ACME 계정 키 공유다. `/data/caddy/acme/`에 저장된 계정 키는 인스턴스가 처음 부팅할 때 생성된다. 새 인스턴스가 빈 `/data`로 뜨면 새 계정을 만들고, 그 계정은 기존 발급 이력과 분리된다. 결과적으로 ACME에서는 같은 도메인에 대한 첫 발급으로 처리되어 rate limit이 다르게 적용된다.

Blue-green 패턴에서는 두 풀이 같은 도메인을 서비스하므로 같은 계정 키와 인증서 스토리지를 공유해야 한다. 분산 스토리지가 정답이다.

```yaml
services:
  caddy-blue:
    image: my-caddy:1.0
    environment:
      DEPLOY_COLOR: blue
      REDIS_HOST: redis.internal
    networks:
      - public
      - storage

  caddy-green:
    image: my-caddy:1.1
    environment:
      DEPLOY_COLOR: green
      REDIS_HOST: redis.internal
    networks:
      - public
      - storage
```

두 풀이 같은 Redis를 보고 있으면 인증서 발급이 한 번만 일어나고 양쪽이 같은 인증서를 쓴다.

Rolling update의 경우 Kubernetes에서 RollingUpdateStrategy로 처리한다.

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    spec:
      containers:
      - name: caddy
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
```

`maxUnavailable: 0`이 핵심이다. 새 Pod가 readiness probe를 통과하기 전까지는 기존 Pod를 죽이지 않는다. Caddy가 부팅하면서 ACME에 인증서를 요청하는 동안 readiness가 false면 트래픽이 안 들어온다. 분산 스토리지가 있으면 이미 발급된 인증서를 그대로 로드해서 즉시 ready 상태가 된다.

ACME 발급이 부팅 시 일어나면 startupProbe로 분리한다. readinessProbe는 부팅 후 짧은 주기로 health check만 하고, 부팅 자체의 긴 대기는 startupProbe가 흡수한다.

```yaml
        startupProbe:
          httpGet:
            path: /health
            port: 80
          failureThreshold: 30
          periodSeconds: 10
```

이렇게 분리하면 부팅 시 최대 300초까지 ACME 발급을 기다릴 수 있고, 그 동안 readinessProbe는 발동하지 않아서 의도치 않은 재시작이 방지된다.

## Docker Secrets로 DNS Provider 토큰 주입

DNS-01 challenge를 쓰는 경우 Cloudflare, Route53 같은 DNS provider의 API 토큰을 Caddy가 알아야 한다. 환경변수로 주입하는 게 가장 간단하지만 보안 측면에서 약하다. `docker inspect`나 `/proc/<pid>/environ`으로 토큰이 그대로 노출된다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    environment:
      CF_API_TOKEN: "${CF_API_TOKEN}"
```

이 패턴은 `.env` 파일이 호스트에 평문으로 남고, 컨테이너 환경변수로도 평문이 박힌다. 누구든 호스트에 접근 가능한 사람이 토큰을 볼 수 있다.

Docker secrets 또는 Kubernetes secrets로 파일 마운트하는 게 낫다.

```yaml
services:
  caddy:
    image: my-caddy:1.0
    secrets:
      - cf_api_token
    environment:
      CF_API_TOKEN_FILE: /run/secrets/cf_api_token

secrets:
  cf_api_token:
    file: ./secrets/cf_api_token.txt
```

Caddy 2.7부터는 `{file./run/secrets/cf_api_token}` 형태로 Caddyfile에서 직접 파일을 읽을 수 있다.

```caddyfile
example.com {
    tls {
        dns cloudflare {file./run/secrets/cf_api_token}
    }
    reverse_proxy backend:8080
}
```

`/run/secrets/` 아래는 tmpfs로 마운트되어 디스크에 절대 쓰이지 않는다. 컨테이너가 죽으면 메모리에서 사라진다. `docker inspect`로도 파일 내용은 보이지 않는다.

Swarm에서는 `docker secret create`로 생성한 secret이 자동으로 같은 경로에 마운트된다.

```bash
echo "your-cloudflare-token" | docker secret create cf_api_token -
```

Kubernetes에서는 Secret 리소스를 volumeMount로 마운트한다.

```yaml
spec:
  template:
    spec:
      containers:
      - name: caddy
        volumeMounts:
        - name: dns-secrets
          mountPath: /run/secrets
          readOnly: true
      volumes:
      - name: dns-secrets
        secret:
          secretName: caddy-dns-secrets
          defaultMode: 0400
```

`defaultMode: 0400`은 read-only로 owner만 읽을 수 있게 한다. Caddy가 non-root로 도는 경우 secret의 owner를 caddy 유저로 맞춰주는 fsGroup 설정이 추가로 필요하다.

환경변수 방식이 꼭 필요하다면, secret 마운트 + entrypoint 스크립트에서 환경변수로 export하는 패턴도 있다. 다만 process listing(`/proc/<pid>/environ`)에 노출되는 위험은 그대로 남는다.

## Production 트러블슈팅

운영 중 마주치는 실제 사고와 진단 절차를 모았다.

### 메모리 누수 의심 시 pprof

Caddy 메모리가 시간이 지나면서 계속 증가한다면 pprof로 heap profile을 떠야 한다. admin API에 pprof endpoint가 노출된다.

```bash
docker exec caddy wget -O /tmp/heap.pprof http://localhost:2019/debug/pprof/heap
docker cp caddy:/tmp/heap.pprof ./heap.pprof
go tool pprof -http=:8080 heap.pprof
```

브라우저에서 flame graph를 보고 어느 모듈이 메모리를 잡고 있는지 추적한다. 주로 의심해야 할 곳은 reverse_proxy의 keepalive pool, log buffer, TLS session cache다.

profile을 받을 admin API가 localhost로만 바인딩되어 있다면 컨테이너 안에서 wget으로 받아야 한다. 외부에서 pprof를 호출하는 건 admin API 노출 사고와 같은 위험이다.

### 인증서 갱신 실패 진단

운영 중 가장 짜증나는 사고가 인증서 갱신 실패다. 만료 30일 전부터 Caddy가 자동 갱신을 시도하는데, 실패하면 알림 없이 만료까지 갈 수 있다.

진단 순서.

1. `docker logs caddy 2>&1 | grep -i acme` — ACME 관련 에러 메시지 확인
2. `docker exec caddy caddy list-certificates` — 현재 보유 인증서와 만료일 확인
3. `docker exec caddy ls -la /data/caddy/locks/` — 락 파일이 stale 상태로 남아 있는지 확인
4. 분산 스토리지를 쓴다면 Redis/Consul의 락 키 직접 조회

stale lock이 가장 흔한 원인이다. 이전 발급 시도 중 컨테이너가 SIGKILL로 죽으면 락이 해제되지 않은 채 남는다. CertMagic은 락 lifetime을 보고 만료된 락은 무시하는데, 클러스터 시간 동기화가 안 맞으면 활성 락으로 오인한다. NTP가 정상 동작하는지 확인하고, 명백히 stale이면 락 키를 수동으로 삭제한다.

DNS 전파 지연도 흔한 원인이다. DNS-01 challenge는 `_acme-challenge` 레코드를 만들고 검증하는데, DNS provider의 전파가 느리면 검증 전에 Caddy가 polling을 시작해서 실패한다. Caddyfile에서 propagation_timeout을 늘린다.

```caddyfile
example.com {
    tls {
        dns cloudflare {file./run/secrets/cf_api_token} {
            propagation_timeout 5m
            propagation_delay 30s
        }
    }
}
```

`propagation_delay`는 레코드 생성 후 polling 시작까지의 최소 대기 시간, `propagation_timeout`은 polling 전체 타임아웃이다.

### OOMKilled 분석

컨테이너가 갑자기 종료되고 `docker ps -a`에서 exit code 137이 보이면 OOMKilled다. SIGKILL을 받았다는 의미이고, 대부분 메모리 limit 초과다.

원인 분석 절차.

1. `dmesg | grep -i 'killed process'` — 호스트의 OOM killer 로그
2. `docker inspect caddy --format '{{.State.OOMKilled}}'` — OOMKilled 플래그 확인
3. cAdvisor/Prometheus의 `container_memory_working_set_bytes` 시계열 — 종료 직전 메모리 패턴
4. pprof heap profile을 종료 직전에 수집해뒀다면 원인 모듈 식별

장수명 운영에서 메모리가 점진적으로 차오르는 경우는 보통 다음 중 하나다.

- TLS session ticket cache가 너무 큼 — 동시 접속자가 많을 때
- access log buffer가 디스크 I/O보다 빠르게 쌓임 — 로그 드라이버 응답 지연
- reverse_proxy의 max_idle_conns이 너무 큼 — 백엔드가 많을 때

`GOMEMLIMIT`를 설정하면 GC가 더 공격적으로 동작해서 OOMKilled를 늦출 수 있지만, 근본 원인을 찾아 limit을 올리거나 cache 크기를 줄이는 게 정답이다.

순간적인 메모리 스파이크로 OOMKilled가 나는 경우는 보통 대용량 응답을 한 번에 버퍼링하는 패턴 때문이다. file_server가 큰 파일을 응답할 때 streaming이 아니라 메모리에 올리는 모듈이 끼어 있거나, header transformation 미들웨어가 응답 본문을 통째로 읽는 경우다. 미들웨어 체인을 단순화하고 streaming response를 보장해야 한다.

production에서 같은 사고를 두 번 겪지 않으려면 PromQL alert로 메모리 사용률 80% 도달 시 경보를 미리 잡는 게 좋다. OOMKilled가 일어난 다음 알림을 받으면 이미 서비스가 끊긴 뒤다.
