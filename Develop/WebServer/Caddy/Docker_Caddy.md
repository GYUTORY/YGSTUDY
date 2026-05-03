---
title: Docker 환경에서 Caddy 운영
tags:
  - WebServer
  - Caddy
  - Docker
  - DockerCompose
  - xcaddy
  - ACME
updated: 2026-05-03
---

# Docker 환경에서 Caddy 운영

Caddy를 Docker로 띄우는 건 `docker run -p 80:80 -p 443:443 caddy` 한 줄로 끝난다. 그런데 이 상태로는 컨테이너를 한 번 재시작하는 순간 Let's Encrypt 인증서가 통째로 사라지고, 다시 발급받느라 rate limit에 걸리거나 서비스가 한참 멍해진다. Caddyfile을 컨테이너 안에 어떻게 넣을지, 인증서를 어디에 영속화할지, 백엔드 컨테이너와 어떤 네트워크로 묶을지에 따라 운영 난이도가 크게 달라진다.

이 문서는 Docker 위에서 Caddy를 굴릴 때 실제로 마주치는 결정 지점들을 정리한다. 공식 이미지를 그대로 쓸지 xcaddy로 빌드할지, Caddyfile을 마운트할지 이미지에 박을지, caddy-docker-proxy로 라벨 기반 라우팅을 갈지, 그런 갈래마다 트레이드오프가 다르다.

## 공식 이미지 구조

Docker Hub의 `caddy` 이미지는 두 종류가 같이 올라온다. `caddy:2.x`는 알파인 기반 런타임 이미지고, `caddy:2.x-builder`는 xcaddy가 들어 있는 빌더 이미지다. 보통 멀티스테이지 빌드의 첫 단계에서 builder를 쓰고, 최종 단계는 런타임 이미지로 끝낸다.

런타임 이미지의 디렉토리 배치는 다음과 같다.

```
/usr/bin/caddy           실행 바이너리
/etc/caddy/Caddyfile     기본 Caddyfile 위치 (CMD가 이걸 읽음)
/data                    XDG_DATA_HOME, 인증서·OCSP·계정 키 저장
/config                  XDG_CONFIG_HOME, 자동 저장된 JSON 설정
/srv                     기본 file_server 루트 (선택)
```

기본 ENTRYPOINT는 `caddy`고 CMD는 `caddy run --config /etc/caddy/Caddyfile --adapter caddyfile`이다. 즉, `/etc/caddy/Caddyfile`만 마운트해 주면 그대로 동작한다. 그런데 Caddy가 운영 중에 자동 HTTPS로 발급받은 인증서나 ACME 계정 키, OCSP 스테이플링 캐시 같은 건 전부 `/data`에 떨어진다. 여기를 볼륨으로 빼지 않으면 컨테이너가 사라질 때 같이 사라진다.

`/config`는 좀 더 미묘하다. Caddy는 마지막으로 로드된 설정을 `/config/caddy/autosave.json`에 자동으로 저장한다. 다음 시작 때 `--resume` 플래그를 주면 이걸 읽어서 복구한다. 운영에서 Admin API로 동적으로 설정을 바꾸는 경우가 있다면 `/config`도 영속화해야 재시작 후에도 같은 상태로 돌아온다. 단순히 Caddyfile만 정적으로 쓰는 경우엔 `/config`는 무시해도 된다.

## Caddyfile 마운트 vs 이미지 빌드

설정을 컨테이너에 넣는 방식은 두 가지다. 호스트의 Caddyfile을 볼륨으로 마운트하거나, Dockerfile에서 `COPY`로 박아서 이미지를 새로 빌드하거나.

마운트 방식은 배포 사이클이 빠르다. Caddyfile만 고치고 `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`을 날리면 무중단으로 반영된다. 이미지를 다시 빌드할 필요가 없으니 CI도 안 거친다. 단점은 컨테이너 자체가 호스트의 파일 상태에 의존한다는 점이다. 호스트에서 누가 Caddyfile을 잘못 수정하고 reload를 트리거하면 그대로 깨진다. 이미지가 곧 배포 단위라는 Docker의 원칙과도 어긋나서, immutable infrastructure를 추구하는 환경에선 잘 안 맞는다.

이미지 빌드 방식은 반대다. Caddyfile이 이미지에 박혀 있으니 어느 호스트에서 이 이미지를 띄워도 같은 설정으로 뜬다. 롤백도 이전 이미지 태그로 돌리면 끝이다. 단점은 설정 한 줄만 고쳐도 이미지를 다시 빌드해서 푸시해야 한다는 것. CI/CD가 잘 갖춰진 팀이 아니면 마찰이 크다.

실무에선 보통 이렇게 가른다. 단일 호스트, 빠른 반복이 필요한 개인 서버나 사내 툴은 마운트 방식. 멀티 호스트, Kubernetes나 Swarm 같은 오케스트레이션 환경은 이미지 빌드 방식. ConfigMap이나 Docker Configs를 쓰면 마운트 방식의 단점을 어느 정도 보완할 수 있는데, 이건 또 운영 도구가 늘어나는 비용이 든다.

```dockerfile
FROM caddy:2.8-alpine
COPY Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

이미지를 빌드한다면 위처럼 빌드 시점에 `caddy validate`를 한 번 돌려두는 게 좋다. 문법 오류로 컨테이너가 시작 직후 죽는 사고를 빌드 단계에서 차단할 수 있다.

## 데이터 볼륨 영속화

Caddy를 Docker로 운영할 때 가장 흔한 사고가 인증서 손실이다. `docker-compose down`을 한 번 했더니 다시 올렸을 때 인증서가 없어서 ACME에 다시 주문을 넣고, 그 사이에 Let's Encrypt의 주간 발급 한도(같은 도메인 50건/주)에 걸려서 며칠간 인증서를 못 받는 상황이 실제로 일어난다.

원인은 `/data`를 볼륨으로 빼지 않은 것이다. 명명 볼륨이든 바인드 마운트든 둘 다 가능한데, 백업 정책을 생각하면 명명 볼륨이 무난하다.

```yaml
services:
  caddy:
    image: caddy:2.8-alpine
    volumes:
      - caddy_data:/data
      - caddy_config:/config
      - ./Caddyfile:/etc/caddy/Caddyfile:ro

volumes:
  caddy_data:
  caddy_config:
```

`caddy_data` 안에 들어가는 핵심 데이터는 다음이다.

- `/data/caddy/certificates/`: ACME로 받아온 인증서 본체와 키
- `/data/caddy/acme/`: 각 CA별 계정 키 (이게 사라지면 같은 계정으로 갱신 못 함)
- `/data/caddy/ocsp/`: OCSP 응답 캐시
- `/data/caddy/locks/`: 인증서 발급 시 동시성 락 (클러스터 환경에서 중요)

백업 시점에 인증서만 따로 빼서 보관하고 싶다면 `/data/caddy/certificates` 디렉토리만 tar로 묶어 두면 된다. 단, 계정 키(`acme/`)도 같이 백업해야 갱신이 정상적으로 이어진다.

여러 Caddy 컨테이너를 동시에 띄워서 같은 도메인을 처리하는 경우엔 `/data`를 공유 스토리지(NFS, EFS 등)에 두고 락 메커니즘을 써야 한다. Caddy는 `caddy.storage` 모듈로 Redis나 Consul, S3 같은 외부 저장소도 쓸 수 있는데, 이건 단일 노드 운영에선 과한 선택이다.

## docker-compose 예제

리버스 프록시로 백엔드 두 개를 묶는 가장 흔한 구성이다.

```yaml
services:
  caddy:
    image: caddy:2.8-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - web
    depends_on:
      - api
      - admin

  api:
    image: myorg/api:1.4.2
    networks:
      - web
    environment:
      - DATABASE_URL=postgres://...

  admin:
    image: myorg/admin:0.9.1
    networks:
      - web

networks:
  web:
    driver: bridge

volumes:
  caddy_data:
  caddy_config:
```

대응되는 Caddyfile은 다음과 같다. Compose 네트워크 안에서는 서비스 이름이 그대로 DNS 레코드로 동작하니까 `api:8080`처럼 쓸 수 있다.

```caddy
api.example.com {
    reverse_proxy api:8080
}

admin.example.com {
    reverse_proxy admin:3000
}
```

여기서 자주 놓치는 부분이 `443/udp` 포트 매핑이다. HTTP/3는 UDP 기반의 QUIC을 쓰기 때문에 TCP 443만 열어두면 클라이언트가 HTTP/3로 협상할 수 없다. 자동 HTTPS는 80번도 필요하다. ACME HTTP-01 챌린지가 80번을 쓰기 때문이다. DNS-01 챌린지로 바꿨다면 80번은 닫아도 되지만, 그땐 `tls` 블록에 DNS provider 모듈을 넣어야 한다.

`depends_on`은 의존성 순서만 보장할 뿐 백엔드의 헬스체크까지 기다리진 않는다. Caddy가 먼저 떠서 백엔드를 찾으면 502가 잠깐 나는 게 정상이다. `reverse_proxy`의 `lb_try_duration`을 길게 잡거나, 백엔드에 `health_uri`를 걸어두면 자연스럽게 회복된다.

## caddy-docker-proxy로 라벨 기반 자동 라우팅

`lucaslorentz/caddy-docker-proxy`는 Traefik의 동작 방식을 Caddy에 가져온 서드파티 빌드다. 컨테이너에 라벨만 붙이면 Caddyfile을 자동으로 생성해서 Caddy를 재로드한다. 마이크로서비스가 늘어날수록 Caddyfile을 손으로 관리하기 귀찮아지는데, 그럴 때 쓴다.

```yaml
services:
  caddy:
    image: lucaslorentz/caddy-docker-proxy:2.9
    ports:
      - "80:80"
      - "443:443"
    environment:
      - CADDY_INGRESS_NETWORKS=web
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - caddy_data:/data
    networks:
      - web

  api:
    image: myorg/api:1.4.2
    networks:
      - web
    labels:
      caddy: api.example.com
      caddy.reverse_proxy: "{{upstreams 8080}}"

  admin:
    image: myorg/admin:0.9.1
    networks:
      - web
    labels:
      caddy: admin.example.com
      caddy.reverse_proxy: "{{upstreams 3000}}"
```

Caddy 컨테이너가 Docker 소켓을 읽어서 라벨이 붙은 컨테이너를 발견하면 그에 맞는 Caddyfile 블록을 만들어 메인 Caddy에 던져 넣는다. 새 컨테이너가 뜨거나 죽을 때마다 자동 reload가 일어난다.

운영에서 주의할 점이 몇 가지 있다. Docker 소켓을 컨테이너에 마운트하는 건 사실상 호스트 root 권한을 컨테이너에 주는 것과 같다. 이 컨테이너가 침해당하면 호스트 전체가 위험해진다. 가능하면 socket-proxy 같은 중계 컨테이너를 두고 read-only 권한만 노출하는 게 안전하다.

또 라벨이 잘못 붙으면 자동 reload가 깨진 Caddyfile을 만들어내고, 그 순간 모든 사이트가 동시에 죽는다. 라벨을 추가할 때마다 적어도 스테이징에서 한 번 검증하는 흐름을 만들어 두는 게 좋다. 그리고 라벨 기반 라우팅은 단순 `reverse_proxy`엔 잘 맞지만, 복잡한 matcher나 중첩된 라우트가 필요한 경우엔 표현력이 떨어진다. 그럴 땐 차라리 일반 Caddy로 돌아가서 Caddyfile을 직접 쓰는 편이 유지보수가 쉽다.

`CADDY_INGRESS_NETWORKS` 환경변수는 어느 Docker 네트워크의 컨테이너만 라우팅 대상으로 삼을지 지정한다. 이걸 안 잡으면 Caddy가 호스트의 모든 네트워크를 뒤지면서 동작이 예측 불가능해진다.

## ACME 인증서 컨테이너 재시작 보존

앞에서 `/data`를 볼륨으로 빼라고 했는데, 그것만으로 끝나는 게 아니다. 실제로 인증서가 컨테이너 재시작 시 보존되려면 몇 가지가 더 맞아야 한다.

가장 흔한 함정이 컨테이너 안의 시간이다. Caddy는 인증서 만료 30일 전부터 갱신을 시도하는데, 컨테이너의 시계가 호스트와 어긋나 있으면 갱신 타이밍이 이상해지거나, 발급 직후 인증서가 "이미 만료됨"으로 보이는 경우도 있다. Docker는 보통 호스트 커널의 시계를 그대로 쓰지만, 호스트의 시간대가 UTC가 아닌데 컨테이너는 UTC인 경우 로그 해석이 꼬이는 정도의 문제가 생긴다.

두 번째 함정은 ACME 계정 키다. `/data/caddy/acme/<ca>/users/default/<email>/account.json`과 같은 경로에 계정 정보가 저장된다. 이걸 잃어버리면 같은 이메일로도 새 계정이 만들어지고, Let's Encrypt는 그걸 별개의 계정으로 본다. 짧은 시간에 같은 도메인에서 여러 번 신규 발급이 일어나면 발급 한도에 걸린다.

세 번째는 클러스터 환경에서의 동시 발급이다. Caddy 컨테이너 두 대가 같은 `/data`를 공유 스토리지로 보고 있는데 락이 제대로 안 걸리면, 둘이 동시에 같은 도메인의 인증서를 주문해서 한쪽이 실패한다. 단일 호스트에서 한 컨테이너만 띄우는 경우엔 신경 안 써도 된다.

복구 시나리오 하나를 시뮬레이션해 보자. `caddy_data` 볼륨이 통째로 사라진 상황이라면, 컨테이너가 다시 뜨면서 새 ACME 계정을 만들고 처음부터 모든 도메인의 인증서를 다시 주문한다. 도메인 수가 적으면 몇 분 안에 끝나지만, 50개를 넘으면 Let's Encrypt의 rate limit에 걸려서 일부 도메인은 며칠간 발급이 안 된다. 이런 사고를 막으려면 `caddy_data`를 주기적으로 백업하거나, 스테이징에서 미리 발급해 둔 인증서 묶음을 항상 갖고 있는 게 안전하다.

```bash
docker run --rm \
  -v caddy_data:/data \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/caddy_data_$(date +%Y%m%d).tar.gz -C /data .
```

위 같은 식으로 볼륨 단위 백업을 cron에 걸어두면 최소한의 보험이 된다.

## 네트워크 모드 트레이드오프

Docker 네트워크 모드는 Caddy 운영에 의외로 큰 영향을 준다. 기본은 bridge 모드인데, 호스트와 격리된 가상 네트워크를 만들고 포트 매핑을 통해 외부와 통신한다. 격리가 깔끔한 대신 클라이언트의 실제 IP가 바뀐다.

bridge 모드에서 백엔드가 받는 `X-Forwarded-For`는 정상적으로 클라이언트 IP를 갖고 있다. 그런데 Caddy 자체의 `{remote_host}` 변수도 docker-proxy를 거친 가짜 IP가 아니라 진짜 클라이언트 IP다. Docker가 이걸 잘 처리하기 때문에 일반적으로는 문제없다. 단, 트래픽이 매우 많으면 docker-proxy 프로세스가 CPU를 꽤 먹는다는 보고가 있다.

host 모드는 컨테이너가 호스트의 네트워크 스택을 그대로 쓴다. 포트 매핑 자체가 없고, 컨테이너 안에서 80번을 열면 호스트의 80번이 그대로 열린다. docker-proxy를 안 거치니 성능이 약간 더 좋고, 클라이언트 IP가 변환 없이 그대로 들어온다. 트래픽이 많은 환경, 특히 HTTP/3의 UDP 트래픽이 많은 경우에는 host 모드가 유리하다.

```yaml
services:
  caddy:
    image: caddy:2.8-alpine
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
```

host 모드의 단점은 격리가 사라진다는 것이다. 같은 호스트에 Caddy 외에 80/443을 쓰는 다른 프로세스를 띄울 수 없다. 또 host 모드에서는 같은 docker-compose 네트워크의 백엔드 컨테이너 이름으로 접근하는 게 안 된다. `api`라는 서비스 이름 대신 `localhost:8080`이나 `127.0.0.1:8080`으로 가야 한다. 다른 컨테이너들도 어떻게든 호스트에 포트를 노출시켜야 하니, 결국 모든 백엔드를 host 모드로 돌리거나 명시적인 포트 매핑을 해야 한다. macOS와 Windows의 Docker Desktop에서는 host 모드의 동작이 리눅스와 다르다는 점도 주의해야 한다.

요약하면, 일반적인 웹 서비스 규모라면 bridge 모드가 무난하고, 초당 수만 건 이상의 요청을 받거나 HTTP/3 UDP 트래픽이 핵심인 경우에 host 모드를 검토한다.

## 멀티스테이지 xcaddy 빌드

기본 Caddy 이미지에는 들어 있지 않은 모듈을 쓰고 싶을 때가 있다. Cloudflare DNS 프로바이더, Redis 스토리지, geoip 매처, 이런 것들은 별도 빌드가 필요하다. xcaddy로 빌드하는데, 멀티스테이지 Dockerfile로 만드는 게 표준 패턴이다.

```dockerfile
FROM caddy:2.8-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/caddyserver/cache-handler \
    --with github.com/mholt/caddy-l4

FROM caddy:2.8-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

`caddy:2.8-builder`는 Go 컴파일러와 xcaddy가 같이 들어 있는 이미지다. 여기서 필요한 모듈을 `--with`로 지정하면 그 모듈을 컴파일해서 새 caddy 바이너리를 만든다. 두 번째 스테이지에서 알파인 런타임 이미지를 베이스로 두고, 빌드된 바이너리만 복사한다. 최종 이미지 크기가 50~60MB 수준으로 작게 유지된다.

`--with` 뒤에는 Go 모듈 경로를 그대로 쓴다. 특정 버전을 고정하고 싶으면 `--with github.com/caddy-dns/cloudflare@v0.0.5` 형태로 적는다. 운영에선 버전 고정을 추천한다. 모듈 메인 브랜치가 바뀌면서 빌드 결과물이 미묘하게 달라지면 디버깅이 까다롭다.

빌드한 이미지가 정상인지 확인하는 가장 간단한 방법은 `caddy list-modules`를 돌려보는 것이다.

```bash
docker run --rm myorg/caddy:custom caddy list-modules | grep cloudflare
```

추가한 모듈이 출력에 나오면 빌드가 제대로 된 것이다. 안 나오면 `--with`에 적은 경로가 잘못됐거나, 빌드 단계에서 에러가 났는데 Dockerfile이 그걸 무시하고 통과했을 가능성이 있다. xcaddy는 빌드 실패 시 비-제로 종료 코드를 반환하니, Dockerfile에서 `RUN xcaddy build ...`가 실패하면 이미지 빌드도 같이 실패한다. 그래서 사실 거의 발생하지 않는 케이스인데, 가끔 빌드 캐시가 꼬여서 이상한 상황이 생긴다. 그럴 땐 `--no-cache`로 다시 빌드한다.

xcaddy 빌드는 매번 Go 의존성을 새로 받기 때문에 인터넷이 느린 환경에선 시간이 꽤 걸린다. CI에서 자주 빌드한다면 Go 모듈 캐시를 BuildKit 캐시 마운트로 살려두는 게 좋다.

```dockerfile
FROM caddy:2.8-builder AS builder

RUN --mount=type=cache,target=/root/go/pkg/mod \
    xcaddy build \
    --with github.com/caddy-dns/cloudflare
```

이러면 두 번째 빌드부터는 의존성 다운로드를 건너뛰니 빌드 시간이 절반 이하로 떨어진다.

## 운영에서 자주 보는 사고

마지막으로 Docker로 Caddy를 운영하면서 한 번씩 부딪히는 사고를 정리한다.

컨테이너가 자꾸 재시작되는데 로그엔 별 게 없는 경우가 있다. 십중팔구 헬스체크가 잘못된 것이다. Caddy 공식 이미지엔 기본 HEALTHCHECK가 없으니 사용자가 추가했을 텐데, `/` 경로가 401을 돌려주는 사이트라면 헬스체크가 unhealthy로 떨어지고 Docker가 컨테이너를 다시 죽인다. `/health` 같은 별도 엔드포인트를 만들어서 거기에 200을 돌려주거나, 아예 헬스체크를 빼버린다.

또 하나는 reload와 restart를 헷갈리는 것이다. Caddyfile만 바꿨다면 `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`이 정답이고, 이건 무중단이다. `docker compose restart caddy`는 컨테이너를 죽였다 다시 띄우는 거라 잠깐 다운타임이 생긴다. 운영 환경에서 reload를 쓰는 습관을 들여야 한다.

마지막은 Docker Desktop에서만 발생하는 이슈다. Docker Desktop은 가상 머신 위에서 돌아가는 구조라 호스트의 포트와 컨테이너의 포트 사이에 한 단계가 더 끼어 있다. 그 결과 80/443 자동 HTTPS가 잘 안 되는 경우가 있다. 로컬 개발에선 어차피 자기서명 인증서를 쓰거나 `tls internal` 디렉티브로 Caddy의 내부 CA를 쓰는 게 편하다.

```caddy
local.test {
    tls internal
    respond "hello"
}
```

`tls internal`을 쓰면 Caddy가 자기 CA로 인증서를 발급한다. 브라우저에서 신뢰하려면 `/data/caddy/pki/authorities/local/root.crt`를 호스트로 빼서 시스템 신뢰 저장소에 추가해야 한다. 이 흐름은 로컬 개발 환경에서만 쓰고, 프로덕션에선 절대 쓰지 않는다.
