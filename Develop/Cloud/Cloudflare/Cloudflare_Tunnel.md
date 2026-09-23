---
title: Cloudflare Tunnel로 서비스 외부 노출
tags: [cloud, network, security, devops, docker]
updated: 2026-09-23
---

# Cloudflare Tunnel로 서비스 외부 노출

공유기 뒤에 있거나 사설망 안에 있는 서버를 외부에서 접근 가능하게 만드는 방법은 크게 세 가지다. 포트 포워딩, VPN, 그리고 Cloudflare Tunnel. 포트 포워딩은 공유기 설정 권한이 있어야 하고 ISP가 80/443을 막으면 끝이다. VPN은 클라이언트마다 설정이 필요하다. Cloudflare Tunnel은 `cloudflared` 데몬이 Cloudflare 엣지로 아웃바운드 연결을 먼저 열고, 그 연결을 통해 외부 트래픽을 끌어당기는 방식이라 인바운드 포트가 하나도 열려 있지 않아도 된다.

## 동작 원리

`cloudflared` 가 시작되면 Cloudflare의 엣지 서버 4곳에 동시에 아웃바운드 QUIC(또는 HTTP/2) 연결을 만든다. 외부에서 터널 도메인으로 요청이 들어오면 Cloudflare가 이 연결을 통해 로컬 서비스로 프록시한다. 서버 쪽에서는 아무 포트도 열지 않는다.

```
외부 클라이언트 → Cloudflare Edge → (기존 아웃바운드 연결) → cloudflared → 로컬 서비스
```

보안상 중요한 점은 Cloudflare가 오리진 IP를 알고 있어도 DNS에 노출하지 않는다는 것이다. `dig api.example.com` 을 해도 Cloudflare 애니캐스트 IP만 나온다.

## 설치와 인증

공식 패키지로 설치하는 게 가장 간단하다.

```bash
# Debian/Ubuntu
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared.deb

# macOS
brew install cloudflare/cloudflare/cloudflared
```

설치 후 Cloudflare 계정에 로그인한다. 이 명령을 실행하면 브라우저가 열리고 인증 후 `~/.cloudflared/cert.pem` 이 생성된다.

```bash
cloudflared tunnel login
```

`cert.pem` 은 터널 생성 권한을 가진 자격증명 파일이다. 이 파일이 있어야 터널을 만들 수 있다. 서버에 복사해 두거나 Docker 볼륨으로 마운트해야 한다.

터널을 생성하면 UUID와 자격증명 파일이 하나 더 만들어진다.

```bash
cloudflared tunnel create my-tunnel
# ~/.cloudflared/<UUID>.json 생성됨
```

이 JSON 파일에는 해당 터널만 운영할 수 있는 토큰이 들어 있다. `cert.pem` 과 달리 이 파일은 배포 서버에만 있으면 된다. `cert.pem` 을 공개 서버에 올리면 다른 터널을 만들거나 삭제할 수 있게 되므로 두 파일의 용도를 구분해야 한다.

## 설정 파일 구조

`~/.cloudflared/config.yml` 이 기본 경로다. 없으면 명령행 플래그로 대신할 수 있지만 서비스가 여러 개면 파일 방식이 낫다.

```yaml
tunnel: <UUID>
credentials-file: /root/.cloudflared/<UUID>.json

ingress:
  - hostname: api.example.com
    service: http://localhost:8080
  - hostname: admin.example.com
    service: http://localhost:3000
    originRequest:
      noTLSVerify: true
  - service: http_status:404
```

`ingress` 배열은 위에서부터 순서대로 매칭한다. 마지막 항목은 `hostname` 없이 `service` 만 있어야 한다. 없으면 설정 파싱 단계에서 오류가 난다. `http_status:404` 는 일치하는 ingress가 없을 때 내보내는 응답이다.

`originRequest` 에서 자주 쓰는 옵션들이다.

| 옵션 | 설명 |
|---|---|
| `noTLSVerify` | 오리진이 자체 서명 인증서를 쓸 때 |
| `connectTimeout` | 오리진 연결 타임아웃 (기본 30초) |
| `http2Origin` | 오리진과 HTTP/2로 통신 |
| `disableChunkedEncoding` | 일부 레거시 서버에서 필요 |

## DNS 레코드 연결

터널을 만든 뒤 DNS 레코드를 연결해야 한다. 두 가지 방법이 있다.

첫 번째는 `cloudflared` 가 직접 CNAME 레코드를 만들어주는 방법이다.

```bash
cloudflared tunnel route dns my-tunnel api.example.com
```

두 번째는 Cloudflare 대시보드에서 직접 CNAME을 추가하는 방법이다. 값은 `<UUID>.cfargotunnel.com` 이다. 대시보드에서 하면 프록시 모드(오렌지 구름) 상태를 직접 확인할 수 있어서 이쪽을 더 선호한다.

CNAME이 연결된 상태에서 `cloudflared tunnel run my-tunnel` 을 실행하면 트래픽이 들어오기 시작한다.

## Docker Compose 통합

개발 환경이나 홈랩에서는 Compose로 서비스와 함께 묶어두는 방식이 편하다.

```yaml
services:
  app:
    image: my-app:latest
    networks:
      - internal

  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared:/etc/cloudflared
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

`./cloudflared/` 디렉토리에 `config.yml` 과 `<UUID>.json` 을 넣어둔다. Compose 네트워크 이름이 `internal` 이면 `config.yml` 의 service 주소를 `http://app:8080` 처럼 서비스 이름으로 쓸 수 있다.

```yaml
ingress:
  - hostname: api.example.com
    service: http://app:8080
  - service: http_status:404
```

`cert.pem` 은 여기 필요 없다. 터널 생성은 이미 끝났고, `<UUID>.json` 만 있으면 터널을 운영할 수 있다.

### Compose에서 자주 겪는 문제

컨테이너 이름 대신 서비스 이름을 써야 한다. `container_name` 을 지정했더라도 Compose 네트워크 내부에서는 서비스 이름(`app`, `db` 등)으로 접근하는 게 안정적이다.

`cloudflared` 컨테이너가 app보다 먼저 뜨면 연결 실패 로그가 나온다. `restart: unless-stopped` 가 있으면 재시도하다가 app이 올라오면 알아서 연결된다. `depends_on` 을 써도 되지만 healthcheck를 제대로 구성하지 않으면 큰 의미가 없다.

## 복수 서비스 ingress 라우팅

하나의 터널로 여러 서비스를 라우팅할 때 호스트명 외에 경로 기반도 가능하다.

```yaml
ingress:
  - hostname: example.com
    path: /api/.*
    service: http://api-server:8080
  - hostname: example.com
    path: /static/.*
    service: http://static-server:9000
  - hostname: example.com
    service: http://frontend:3000
  - service: http_status:404
```

경로는 정규식으로 매칭한다. 순서가 중요하다. `/api/v1/users` 요청이 들어오면 위에서부터 내려가다가 `/api/.*` 에 걸린다. 일반 경로를 위에 두고 와일드카드를 아래에 두지 않으면 의도대로 라우팅되지 않는다.

경로 매칭은 호스트명이 같은 ingress들 사이에서만 동작한다. 호스트명이 다른 ingress끼리는 상관없다.

TCP/UDP 서비스도 라우팅할 수 있다. 데이터베이스나 SSH 같은 경우다.

```yaml
ingress:
  - hostname: db.example.com
    service: tcp://localhost:5432
  - service: http_status:404
```

TCP 라우팅은 클라이언트 쪽에서도 `cloudflared access tcp` 명령으로 로컬 포트를 열어야 한다. SSH는 `cloudflared access ssh` 서브커맨드가 따로 있다.

## 서비스로 등록

서버에 직접 설치한 경우 systemd 서비스로 등록하면 재부팅 후에도 자동 실행된다.

```bash
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
```

이 명령은 `/etc/cloudflared/config.yml` 을 읽는 서비스 유닛을 만든다. 설정 파일을 홈 디렉토리가 아니라 `/etc/cloudflared/` 에 두는 게 이 경우에는 맞다.

## 트러블슈팅

**터널은 연결됐는데 서비스에 접근이 안 될 때**

`cloudflared tunnel run` 로그에서 `ERR` 줄을 먼저 본다. 오리진 서비스가 아직 안 떴거나, 잘못된 포트를 가리키고 있는 경우가 대부분이다.

```bash
cloudflared tunnel run --loglevel debug my-tunnel
```

`debug` 레벨로 실행하면 각 요청이 어떤 ingress에 매칭됐는지, 오리진 응답 코드가 뭔지 다 나온다.

**SSL 오류**

오리진이 `https://localhost` 를 쓰는데 자체 서명 인증서라면 `noTLSVerify: true` 가 없으면 연결이 끊긴다. 오리진이 HTTP라면 `http://` 를 명시해야 한다. `service: localhost:8080` 처럼 프로토콜을 빼면 `cloudflared` 가 HTTP로 가정하긴 하지만 명시하는 게 낫다.

**터널 연결이 끊겼다가 다시 붙을 때**

`cloudflared` 는 연결이 끊기면 자동으로 재연결한다. Cloudflare 엣지 4곳에 동시 연결을 유지하는 이유가 여기 있다. 한 엣지 서버에 문제가 생겨도 나머지 세 개로 트래픽이 흐른다. `systemctl status cloudflared` 로 재연결 횟수를 보면 네트워크 상태를 간접적으로 알 수 있다.

**동일 UUID로 두 인스턴스를 띄웠을 때**

같은 터널 자격증명으로 두 개의 `cloudflared` 를 실행하면 로드 밸런싱이 된다. 의도한 경우라면 괜찮지만 실수로 두 개가 떠있으면 요청이 절반씩 나뉘어가 한 쪽만 실제 서비스를 보고 있을 때 간헐적 오류처럼 보인다. `cloudflared tunnel connections my-tunnel` 로 현재 연결된 인스턴스 수를 확인할 수 있다.

**`cert.pem` 없이 터널을 실행할 때**

터널 실행에는 `<UUID>.json` 만 필요하다. `cert.pem` 이 없어도 `tunnel run` 은 된다. `cert.pem` 이 필요한 작업은 터널 생성(`tunnel create`), 삭제(`tunnel delete`), DNS 라우팅 변경(`tunnel route dns`) 이다. CI/CD 파이프라인에서 배포 서버에 `cert.pem` 을 올리지 않고 UUID JSON만 주입하는 방식이 더 안전하다.

**Zero Trust 대시보드에서 터널이 Inactive로 보일 때**

`cloudflared` 데몬이 안 떠있거나, 뜨더라도 Cloudflare 엣지에 연결을 못 만든 상태다. 443/UDP(QUIC)가 방화벽에 막혀 있으면 자동으로 443/TCP HTTP/2로 폴백한다. QUIC도 TCP도 막혀 있으면 연결이 안 된다. 아웃바운드 443이 열려있는지 확인한다.
