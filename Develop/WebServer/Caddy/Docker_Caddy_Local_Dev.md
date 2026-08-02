---
title: Docker Caddy 로컬 개발 환경 구성
tags: [webserver, Caddy, docker, DockerCompose, tls, LocalDev]
---

# Docker Caddy 로컬 개발 환경 구성

로컬에서 Caddy를 쓰는 주된 이유는 HTTPS 환경을 흉내 내기 위해서다. 쿠키 `Secure` 플래그, `SameSite=None`, HSTS, HTTP/2 같은 것들은 HTTP에서 동작하지 않거나 다르게 동작하기 때문에, 프로덕션과 같은 프로토콜 환경을 로컬에서 맞추지 않으면 QA 때 엉뚱한 버그를 뒤늦게 발견한다.

Caddy의 `tls internal` 옵션은 Let's Encrypt 같은 외부 CA 없이 로컬 전용 인증서를 발급해 준다. 단, 브라우저는 이 인증서를 기본적으로 신뢰하지 않아서 "NET::ERR_CERT_INVALID" 경고가 뜬다. 이 인증서를 시스템 신뢰 저장소에 수동으로 등록하거나 `mkcert` 같은 도구로 로컬 CA를 심는 방식 중 하나를 골라야 한다.

## tls internal 동작 원리

Caddy가 `tls internal`을 만나면 내장된 로컬 CA로 인증서를 직접 서명한다. 이 CA의 루트 인증서는 컨테이너 내부의 `/data/caddy/pki/authorities/local/` 아래에 저장된다.

```
/data/caddy/pki/authorities/local/
├── root.crt     # 브라우저에 등록해야 하는 루트 인증서
└── root.key
```

컨테이너를 띄울 때마다 이 루트 CA가 새로 만들어지기 때문에, `/data`를 볼륨으로 마운트하지 않으면 컨테이너 재시작마다 인증서가 바뀌고 브라우저 신뢰 등록을 반복해야 한다. `/data` 볼륨 영속화가 로컬 개발에서도 필수인 이유가 여기 있다.

## 디렉토리 구조

```
project/
├── docker-compose.yml
├── caddy/
│   ├── Caddyfile            # 기본(개발) 설정
│   ├── Caddyfile.staging    # 스테이징 설정
│   └── Caddyfile.prod       # 프로덕션 설정
└── caddy-data/              # /data 볼륨 (gitignore 대상)
```

`caddy-data/`는 반드시 `.gitignore`에 넣는다. 인증서 키 파일이 포함되어 있어서 커밋되면 곤란하다.

## docker-compose.yml 기본 구성

```yaml
services:
  caddy:
    image: caddy:2.9-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"    # HTTP/3 (QUIC)
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    networks:
      - app-net

  api:
    image: my-api:latest
    networks:
      - app-net

  frontend:
    image: my-frontend:latest
    networks:
      - app-net

volumes:
  caddy-data:
  caddy-config:

networks:
  app-net:
    driver: bridge
```

`caddy-data`는 named volume으로 선언해서 Compose가 관리하게 두는 편이 낫다. 호스트 경로 마운트(`./caddy-data:/data`)로 해도 되지만 macOS에서 파일 퍼미션 문제가 생기는 경우가 있다.

## Caddyfile 로컬 개발 설정

```caddyfile
{
    # 로컬에서는 ACME 비활성화, tls internal만 쓴다
    local_certs
    auto_https off
    email ""
}

api.local.dev {
    tls internal
    reverse_proxy api:8080
}

app.local.dev {
    tls internal
    reverse_proxy frontend:3000
}

admin.local.dev {
    tls internal
    reverse_proxy api:8081 {
        header_up Host {upstream_hostport}
    }
}
```

`local_certs`를 global 옵션에 넣으면 모든 사이트에 `tls internal`이 기본 적용된다. 각 사이트 블록에 개별적으로 `tls internal`을 명시해도 동일하다.

`auto_https off`는 HTTP로 들어온 요청을 HTTPS로 자동 리다이렉트하는 기능을 끈다. 로컬에서 백엔드끼리 HTTP로 통신할 때 의도치 않은 리다이렉트 루프가 생기는 경우가 있어서 끄는 편이 편하다.

## /etc/hosts 설정

`api.local.dev`같은 커스텀 도메인을 쓰려면 호스트 머신의 `/etc/hosts`에 등록해야 한다. macOS/Linux 기준으로 `/etc/hosts` 파일에 다음을 추가한다.

```
127.0.0.1   api.local.dev
127.0.0.1   app.local.dev
127.0.0.1   admin.local.dev
```

Windows는 `C:\Windows\System32\drivers\etc\hosts`를 관리자 권한으로 수정한다.

도메인이 많아지면 dnsmasq를 로컬에 띄우고 `.local.dev` 같은 서픽스 전체를 `127.0.0.1`로 리졸브하도록 설정하는 방법도 있다. macOS는 `/etc/resolver/` 디렉토리에 파일 하나 만드는 것으로 끝난다.

```bash
# macOS에서 *.local.dev 전체를 127.0.0.1로 리졸브
sudo mkdir -p /etc/resolver
echo "nameserver 127.0.0.1" | sudo tee /etc/resolver/local.dev
```

dnsmasq까지 설정하면 팀원이 추가될 때마다 `/etc/hosts`를 수정할 필요 없어져서, 개발자가 여럿인 프로젝트에서는 이 방식이 낫다.

## 브라우저 신뢰 저장소 등록

컨테이너가 올라가고 `/data` 볼륨 안에 루트 인증서가 생성되면, 그 인증서를 꺼내서 시스템에 등록한다.

```bash
# 컨테이너에서 루트 인증서 추출
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
```

**macOS**

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ./caddy-root.crt
```

Keychain Access 앱에서 "System" 키체인에서 "Caddy Local Authority"를 찾아 "항상 신뢰"로 설정해도 된다. GUI가 더 빠를 때가 많다.

**Ubuntu/Debian**

```bash
sudo cp ./caddy-root.crt /usr/local/share/ca-certificates/caddy-local.crt
sudo update-ca-certificates
```

크롬과 엣지는 NSS 데이터베이스를 따로 갖기 때문에 시스템 CA 등록만으로는 부족하다.

```bash
# NSS 데이터베이스 등록 (크롬/엣지)
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," \
  -n "Caddy Local Authority" -i ./caddy-root.crt
```

파이어폭스는 브라우저 자체 CA 스토어를 쓰기 때문에 `about:preferences#privacy` > "인증서 보기"에서 직접 임포트해야 한다.

루트 인증서 등록 후 브라우저를 완전히 종료하고 다시 열어야 반영된다. 탭만 닫는 걸로는 안 된다.

## Caddyfile 핫 리로드

Caddyfile을 수정할 때마다 컨테이너를 재시작하는 건 번거롭다. Caddy는 `caddy reload` 명령으로 무중단 리로드를 지원한다.

```bash
# Caddyfile 수정 후 리로드
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile

# 문법 검사만 할 때
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
```

Caddyfile을 `:ro` 볼륨으로 마운트했기 때문에 호스트에서 파일을 수정하는 즉시 컨테이너 내부에 반영된다. 그 다음 `caddy reload`를 실행하면 끝이다. `watch` 명령으로 파일 변경을 자동 감지하게 할 수도 있다.

```bash
# 파일 변경 감지 자동 리로드 (fswatch 필요, macOS)
fswatch -o ./caddy/Caddyfile | xargs -n1 \
  docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

리로드 중에도 기존 연결은 유지된다. 개발 중 API를 잡아두고 Caddyfile을 고쳐야 할 때 연결이 끊기지 않아서 편하다.

## 여러 백엔드 서비스 구성 예제

실제 프로젝트에서는 백엔드가 여러 개인 경우가 많다. 아래는 프론트엔드, REST API, gRPC-Gateway, WebSocket 서버를 함께 운영하는 예제다.

```caddyfile
{
    local_certs
    auto_https off
}

# 프론트엔드 (Next.js 개발 서버)
app.local.dev {
    tls internal

    # WebSocket 핫 리로드 경로는 프론트엔드 개발 서버로 직접 보낸다
    handle /_next/webpack-hmr {
        reverse_proxy frontend:3000
    }

    handle {
        reverse_proxy frontend:3000
    }
}

# REST API
api.local.dev {
    tls internal

    @cors_preflight method OPTIONS
    handle @cors_preflight {
        header Access-Control-Allow-Origin "https://app.local.dev"
        header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        header Access-Control-Allow-Headers "Authorization, Content-Type"
        respond 204
    }

    reverse_proxy api:8080
}

# gRPC
grpc.local.dev {
    tls internal
    reverse_proxy h2c://grpc-server:9090
}

# WebSocket 서버
ws.local.dev {
    tls internal
    reverse_proxy ws-server:4000 {
        header_up Connection {http.request.header.Connection}
        header_up Upgrade {http.request.header.Upgrade}
    }
}
```

gRPC는 HTTP/2 cleartext(`h2c://`)로 업스트림에 연결한다. `grpc-server`가 TLS 없이 gRPC를 서빙할 때 이 설정이 맞다. 업스트림이 TLS를 요구하면 `h2c://` 대신 그냥 주소를 쓴다.

WebSocket은 `Upgrade`, `Connection` 헤더를 업스트림에 그대로 전달해야 한다. Caddy 2.8부터는 WebSocket 프록시 시 헤더를 자동으로 처리하는 경우도 있지만, 명시적으로 쓰는 게 안전하다.

## Docker Desktop 포트 바인딩 주의사항

macOS와 Windows의 Docker Desktop에서는 컨테이너가 Linux VM 안에서 돌기 때문에 몇 가지 동작이 다르다.

**포트 1024 미만 바인딩**: Linux에서 1024 미만 포트는 root 권한이 필요하다. Docker Desktop은 내부적으로 처리해 주기 때문에 80, 443 포트 바인딩이 대부분 된다. 하지만 시스템 방화벽이나 AirPlay Receiver 같은 다른 프로세스가 443을 먼저 잡고 있는 경우가 있다.

```bash
# 443 포트를 잡고 있는 프로세스 확인 (macOS)
sudo lsof -i :443
```

macOS에서 AirPlay Receiver가 443을 점유하는 경우, "시스템 설정 > 일반 > AirDrop 및 핸드오프"에서 AirPlay Receiver를 끄면 해결된다.

**Docker Desktop VM 내부 IP**: `host.docker.internal`은 Docker Desktop에서만 동작하는 특수 DNS다. Linux 환경(CI, 서버)에서는 이 도메인이 없다. Caddyfile에서 `host.docker.internal`을 쓰면 Linux 서버에 그대로 올렸을 때 깨진다. 로컬 전용 설정임을 명확히 표시해 두거나, 환경 변수로 분리하는 편이 낫다.

**ACME 트래픽 차단**: Let's Encrypt는 80포트로 HTTP-01 챌린지를 하고 443포트로 TLS-ALPN-01 챌린지를 한다. 로컬 개발 환경은 퍼블릭 IP가 없어서 이 챌린지가 무조건 실패한다. `tls internal`이나 수동 인증서를 써야 하는 이유가 여기 있고, 실수로 `tls` 지시어만 쓰고 `internal`을 빠뜨리면 Let's Encrypt 발급 시도 실패 로그가 쌓이다가 rate limit에 걸릴 수 있다.

```caddyfile
# 잘못된 설정 - 로컬에서 Let's Encrypt 발급 시도
app.local.dev {
    tls admin@company.com
    reverse_proxy frontend:3000
}

# 올바른 설정
app.local.dev {
    tls internal
    reverse_proxy frontend:3000
}
```

## 개발/스테이징/프로덕션 Caddyfile 분기 관리

환경별로 Caddyfile을 완전히 분리하는 방법과, 공통 부분을 `import`로 공유하는 방법 두 가지를 조합해서 쓴다.

**방법 1: 환경별 파일 분리**

```
caddy/
├── Caddyfile.dev        # 로컬 개발
├── Caddyfile.staging    # 스테이징
├── Caddyfile.prod       # 프로덕션
└── snippets/
    ├── security.caddy   # 공통 보안 헤더
    └── logging.caddy    # 공통 로그 설정
```

docker-compose에서 `CADDY_ENV` 환경 변수로 어떤 파일을 마운트할지 제어한다.

```yaml
services:
  caddy:
    image: caddy:2.9-alpine
    volumes:
      - ./caddy/Caddyfile.${CADDY_ENV:-dev}:/etc/caddy/Caddyfile:ro
      - ./caddy/snippets:/etc/caddy/snippets:ro
      - caddy-data:/data
      - caddy-config:/config
```

```bash
# 개발 환경 (기본값)
docker compose up

# 스테이징 환경
CADDY_ENV=staging docker compose up
```

**Caddyfile.dev** (로컬 개발)

```caddyfile
{
    local_certs
    auto_https off
    debug
}

import /etc/caddy/snippets/*.caddy

api.local.dev {
    tls internal
    import security
    reverse_proxy api:8080
}

app.local.dev {
    tls internal
    reverse_proxy frontend:3000
}
```

**Caddyfile.staging** (스테이징)

```caddyfile
{
    email ops@company.com
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
}

import /etc/caddy/snippets/*.caddy

api-staging.company.com {
    import security
    reverse_proxy api:8080
}

app-staging.company.com {
    reverse_proxy frontend:3000
}
```

스테이징에서는 Let's Encrypt staging CA를 쓴다. 프로덕션 CA와 rate limit를 공유하지 않아서 발급 실패를 반복해도 안전하다. 브라우저에서 "안전하지 않은 사이트" 경고가 뜨는 건 감수해야 한다.

**Caddyfile.prod** (프로덕션)

```caddyfile
{
    email ops@company.com
}

import /etc/caddy/snippets/*.caddy

api.company.com {
    import security
    reverse_proxy api:8080
}

app.company.com {
    reverse_proxy frontend:3000
}
```

**snippets/security.caddy**

```caddyfile
(security) {
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }
}
```

스니펫 파일은 `(이름) { ... }` 형태로 정의하고, Caddyfile에서 `import 이름`으로 불러 쓴다. 보안 헤더, 로그 포맷, 공통 rate limit 같은 것들을 스니펫으로 분리하면 세 파일에 동일한 블록을 복붙하지 않아도 된다.

## 인증서 갱신 주기와 로컬 CA 수명

`tls internal`로 발급된 인증서의 기본 유효 기간은 1주일이다. Caddy는 만료 전에 자동으로 갱신하기 때문에 대부분은 신경 쓰지 않아도 된다. 단, `/data` 볼륨을 지우면 로컬 CA 자체가 새로 만들어져서 이전에 브라우저에 등록한 루트 인증서가 무효화된다. 브라우저에서 갑자기 인증서 오류가 뜬다면 대부분 이 경우다.

```bash
# /data 볼륨 확인
docker volume ls | grep caddy

# 볼륨 내용 확인
docker run --rm -v caddy-data:/data alpine ls -la /data/caddy/pki/authorities/local/

# 볼륨을 지우면 로컬 CA가 새로 생성되고 브라우저 재등록이 필요하다
docker volume rm project_caddy-data   # 신중하게
```

팀 단위로 개발한다면 루트 인증서를 공유 폴더나 Vault에 보관하고, 신규 개발자 온보딩 시 이 인증서를 등록하는 과정을 런북에 포함시키는 게 낫다.
