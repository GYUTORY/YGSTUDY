---
title: Caddy
tags: [webserver, caddy, https, reverse-proxy, lets-encrypt]
updated: 2026-04-07
---

# Caddy

## Caddy란

Go로 만든 웹 서버. 2015년 Matt Holt가 처음 만들었고, 2020년에 v2로 전면 재작성됐다. 가장 큰 특징은 HTTPS가 기본값이라는 것이다. 도메인만 지정하면 Let's Encrypt나 ZeroSSL에서 인증서를 자동으로 발급받고 갱신까지 알아서 한다. Nginx에서 certbot 설정하고 cron 걸어두던 작업이 필요 없다.

설정 파일(Caddyfile)이 단순해서 Nginx의 `nginx.conf`에 비하면 작성할 양이 확 줄어든다. 단, 고도로 세밀한 튜닝이 필요한 경우에는 Nginx가 더 나은 선택일 수 있다.

## 설치

### Ubuntu/Debian

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### macOS (Homebrew)

```bash
brew install caddy
```

### 바이너리 직접 다운로드

Go 단일 바이너리라서 의존성 없이 바로 실행할 수 있다. [공식 다운로드 페이지](https://caddyserver.com/download)에서 플랫폼별 바이너리를 받는다.

```bash
# 버전 확인
caddy version

# 시작 (포그라운드)
caddy run

# 백그라운드 실행
caddy start

# 중지
caddy stop

# 설정 리로드 (무중단)
caddy reload
```

### systemd 등록

패키지 매니저로 설치하면 systemd 서비스가 자동 등록된다. 바이너리로 직접 설치한 경우 수동 등록이 필요하다.

```bash
sudo systemctl enable caddy
sudo systemctl start caddy
sudo systemctl status caddy

# 설정 변경 후
sudo systemctl reload caddy
```

## Caddyfile 문법

Caddyfile은 `/etc/caddy/Caddyfile`에 위치한다. Nginx 설정과 비교하면 작성량이 절반 이하다.

### 기본 구조

```
사이트주소 {
    디렉티브 인자
}
```

실제 예시:

```
example.com {
    respond "Hello, World!"
}
```

이것만으로 example.com에 대해 HTTPS 인증서 발급, HTTP→HTTPS 리다이렉트, 응답 처리가 전부 된다.

### 여러 사이트 설정

```
example.com {
    root * /var/www/example
    file_server
}

api.example.com {
    reverse_proxy localhost:8080
}

:8888 {
    respond "dev server"
}
```

포트만 지정하면(`localhost:8888` 또는 `:8888`) HTTPS를 적용하지 않는다. 도메인을 쓰면 자동으로 HTTPS가 켜진다.

### 주요 디렉티브

| 디렉티브 | 설명 |
|-----------|------|
| `file_server` | 정적 파일 서빙 |
| `reverse_proxy` | 리버스 프록시 |
| `root` | 문서 루트 디렉토리 |
| `encode` | 압축 (gzip, zstd) |
| `log` | 액세스 로그 |
| `header` | 응답 헤더 설정 |
| `basicauth` | 기본 인증 |
| `tls` | TLS 세부 설정 |
| `redir` | 리다이렉트 |
| `rewrite` | URL 재작성 |
| `handle` | 요청 처리 그룹 |
| `handle_path` | 경로 prefix 제거 후 처리 |

### 매처(Matcher)

특정 경로나 조건에만 디렉티브를 적용할 때 사용한다.

```
example.com {
    # /api/*로 오는 요청만 프록시
    reverse_proxy /api/* localhost:8080

    # 나머지는 정적 파일
    root * /var/www/site
    file_server
}
```

이름 있는 매처를 쓰면 복잡한 조건을 표현할 수 있다.

```
example.com {
    @websocket {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket localhost:6001

    @static {
        path *.css *.js *.png *.jpg *.gif *.svg *.woff2
    }
    header @static Cache-Control "public, max-age=31536000"

    reverse_proxy localhost:8080
}
```

### 환경 변수 사용

```
{$DOMAIN:localhost} {
    reverse_proxy {$BACKEND_HOST:localhost}:{$BACKEND_PORT:8080}
}
```

`{$변수명:기본값}` 형식이다. 환경 변수가 없으면 기본값을 쓴다.

### 전역 옵션

Caddyfile 맨 위에 중괄호로 감싸서 전역 옵션을 설정한다.

```
{
    email admin@example.com  # ACME 계정 이메일
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory  # 스테이징 CA
    admin off  # 관리 API 비활성화
}
```

## 자동 HTTPS

Caddy의 핵심 기능이다. 도메인 이름으로 사이트를 설정하면 다음이 자동으로 일어난다:

1. Let's Encrypt(기본) 또는 ZeroSSL에서 TLS 인증서 발급
2. HTTP → HTTPS 301 리다이렉트
3. 인증서 만료 전 자동 갱신
4. OCSP 스테이플링

### 동작 조건

자동 HTTPS가 작동하려면 두 가지가 필요하다:

- 도메인의 DNS A/AAAA 레코드가 서버 IP를 가리킬 것
- 80, 443 포트가 열려 있을 것 (HTTP-01 챌린지용)

80 포트를 열 수 없는 환경이면 DNS 챌린지를 써야 한다.

### DNS 챌린지 설정

Cloudflare 예시:

```
{
    acme_dns cloudflare {env.CF_API_TOKEN}
}

example.com {
    reverse_proxy localhost:8080
}
```

DNS 챌린지용 플러그인은 기본 바이너리에 포함되지 않는다. [Caddy 다운로드 페이지](https://caddyserver.com/download)에서 DNS 모듈을 포함해 빌드하거나, `xcaddy`로 직접 빌드해야 한다.

```bash
# xcaddy로 Cloudflare DNS 모듈 포함 빌드
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
xcaddy build --with github.com/caddy-dns/cloudflare
```

### 내부 인증서 (로컬 개발용)

로컬 개발 환경에서 HTTPS가 필요하면 내부 CA로 자체 서명 인증서를 쓸 수 있다.

```
{
    local_certs
}

localhost {
    reverse_proxy localhost:3000
}
```

또는 사이트 단위로:

```
localhost {
    tls internal
    reverse_proxy localhost:3000
}
```

처음 실행하면 시스템 trust store에 루트 인증서를 등록하는데, 이때 sudo 비밀번호를 물어본다.

### Nginx와의 HTTPS 설정 비교

Nginx에서 Let's Encrypt를 쓰려면 이런 과정이 필요하다:

```bash
# Nginx: certbot 설치, 인증서 발급, cron 등록
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
# 갱신 cron 별도 설정 필요
```

```nginx
# Nginx: ssl 관련 설정을 직접 작성
server {
    listen 443 ssl;
    server_name example.com;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    # ... 추가 보안 헤더 설정
}
```

Caddy에서는:

```
example.com {
    reverse_proxy localhost:8080
}
```

이게 전부다.

## 리버스 프록시

### 기본 설정

```
example.com {
    reverse_proxy localhost:8080
}
```

### 경로별 라우팅

```
example.com {
    handle /api/* {
        reverse_proxy localhost:8080
    }

    handle /admin/* {
        reverse_proxy localhost:9090
    }

    handle {
        root * /var/www/frontend
        file_server
    }
}
```

`handle`과 `handle_path`의 차이를 알아야 한다. `handle`은 원래 경로를 그대로 백엔드에 전달하고, `handle_path`는 매칭된 prefix를 제거한다.

```
example.com {
    # /api/users → 백엔드에 /api/users로 전달
    handle /api/* {
        reverse_proxy localhost:8080
    }

    # /app/dashboard → 백엔드에 /dashboard로 전달 (prefix /app 제거)
    handle_path /app/* {
        reverse_proxy localhost:3000
    }
}
```

### 로드 밸런싱

```
example.com {
    reverse_proxy localhost:8001 localhost:8002 localhost:8003 {
        lb_policy round_robin
        health_uri /health
        health_interval 10s
        health_timeout 5s
    }
}
```

지원하는 로드 밸런싱 정책:

- `round_robin` — 순서대로 분배 (기본값)
- `least_conn` — 연결 수가 가장 적은 서버로
- `random` — 랜덤
- `first` — 첫 번째 정상 서버로
- `ip_hash` — 클라이언트 IP 기반 고정
- `uri_hash` — URI 기반 고정
- `header` — 특정 헤더 값 기반

### 헤더 전달

```
example.com {
    reverse_proxy localhost:8080 {
        header_up Host {upstream_hostport}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Caddy는 `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`를 기본으로 설정한다. 별도 설정 없이도 백엔드에서 클라이언트 정보를 받을 수 있다.

### WebSocket 프록시

별도 설정이 필요 없다. `reverse_proxy`가 WebSocket 업그레이드를 자동으로 처리한다.

```
example.com {
    reverse_proxy /ws localhost:6001
    reverse_proxy localhost:8080
}
```

Nginx에서는 WebSocket마다 `proxy_set_header Upgrade`, `proxy_set_header Connection` 설정을 추가해야 하는데, Caddy에서는 그냥 된다.

## 정적 파일 서빙

### 기본 설정

```
example.com {
    root * /var/www/site
    file_server
}
```

### 디렉토리 목록 표시

```
example.com {
    root * /var/www/files
    file_server browse
}
```

### SPA(Single Page Application) 설정

React, Vue 같은 SPA는 모든 경로를 `index.html`로 보내야 한다.

```
example.com {
    root * /var/www/app
    try_files {path} /index.html
    file_server
}
```

### 압축

```
example.com {
    root * /var/www/site
    encode gzip zstd
    file_server
}
```

`zstd`를 `gzip`보다 앞에 쓰면 zstd를 우선한다. 클라이언트가 zstd를 지원하지 않으면 gzip으로 폴백한다.

### 캐시 헤더

```
example.com {
    root * /var/www/site

    @static {
        path *.css *.js *.png *.jpg *.gif *.svg *.woff2
    }
    header @static Cache-Control "public, max-age=31536000, immutable"

    @html {
        path *.html
    }
    header @html Cache-Control "no-cache"

    file_server
}
```

## Nginx와의 비교

| 항목 | Caddy | Nginx |
|------|-------|-------|
| HTTPS 설정 | 자동 (도메인만 지정) | certbot + 수동 설정 |
| 설정 문법 | Caddyfile (간결) | nginx.conf (장황) |
| WebSocket | 자동 처리 | 헤더 설정 필요 |
| 언어 | Go | C |
| 메모리 사용량 | 상대적으로 많음 | 적음 |
| 성능 (정적 파일) | 충분히 빠름 | 약간 더 빠름 |
| 모듈 생태계 | 작음 | 매우 큼 |
| 설정 복잡도 | 낮음 | 높음 |
| 실무 채택률 | 점점 늘어나는 중 | 압도적 |

Caddy를 쓰면 좋은 경우:

- 소규모~중규모 서비스에서 빠르게 HTTPS를 적용해야 할 때
- 복잡한 Nginx 설정을 관리할 인력이 부족할 때
- 사이드 프로젝트나 내부 도구에서 간단하게 리버스 프록시를 띄울 때
- Docker 환경에서 인증서 관리를 자동화하고 싶을 때

Nginx를 쓰면 좋은 경우:

- 대규모 트래픽을 처리해야 할 때
- 세밀한 성능 튜닝이 필요할 때
- 이미 Nginx 기반 인프라가 구축되어 있을 때
- OpenResty 같은 확장이 필요할 때

## Docker 환경 설정

### 기본 Docker Compose

```yaml
version: "3.9"

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data      # 인증서 저장
      - caddy_config:/config  # 설정 캐시
      - ./site:/srv           # 정적 파일

volumes:
  caddy_data:
  caddy_config:
```

`caddy_data` 볼륨은 반드시 유지해야 한다. 여기에 인증서가 저장되는데, 볼륨을 날리면 인증서를 다시 발급받아야 하고, 짧은 시간에 반복 발급하면 Let's Encrypt rate limit에 걸린다.

### 리버스 프록시 + 앱 서버

```yaml
version: "3.9"

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - web

  app:
    build: .
    restart: unless-stopped
    expose:
      - "8080"
    networks:
      - web

networks:
  web:

volumes:
  caddy_data:
  caddy_config:
```

Caddyfile:

```
example.com {
    reverse_proxy app:8080
}
```

Docker Compose에서 서비스 이름(`app`)을 호스트명으로 쓸 수 있다. `localhost` 대신 서비스 이름을 써야 한다.

### DNS 챌린지용 커스텀 이미지

80 포트를 열 수 없는 환경에서 DNS 챌린지를 쓰려면 플러그인이 포함된 이미지를 빌드해야 한다.

```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

```yaml
services:
  caddy:
    build: .
    environment:
      - CF_API_TOKEN=your-cloudflare-api-token
    # ... 나머지 동일
```

## JSON 설정 (API 기반)

Caddyfile은 내부적으로 JSON 설정으로 변환된다. 프로그래밍 방식으로 설정을 관리해야 하면 JSON API를 직접 쓸 수 있다.

```bash
# 현재 설정을 JSON으로 확인
caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile

# API로 설정 변경
curl localhost:2019/config/ -H "Content-Type: application/json" -d @caddy.json

# 특정 경로만 수정
curl localhost:2019/config/apps/http/servers/srv0/routes \
  -X PATCH \
  -H "Content-Type: application/json" \
  -d '[...]'
```

관리 API는 기본적으로 `localhost:2019`에서 동작한다. 외부에서 접근할 수 없게 기본값이 localhost로 바인딩되어 있다. 프로덕션에서 관리 API가 필요 없으면 전역 옵션에서 `admin off`로 꺼두는 게 안전하다.

## 트러블슈팅

### 인증서 발급 실패

가장 흔한 문제다. 원인별로 확인할 것:

**DNS가 서버를 가리키지 않음**

```bash
# DNS 확인
dig +short example.com
# 서버 IP가 나와야 한다

nslookup example.com
```

DNS 전파에 시간이 걸릴 수 있다. 도메인을 방금 설정했으면 몇 분 기다려야 한다.

**80/443 포트가 막혀 있음**

```bash
# 포트 확인
sudo ss -tlnp | grep -E ':80|:443'

# 방화벽 확인
sudo ufw status
sudo iptables -L -n
```

클라우드 환경이면 보안 그룹(AWS), 방화벽 규칙(GCP)도 확인해야 한다.

**Rate limit 초과**

Let's Encrypt는 동일 도메인에 대해 주당 5회까지 인증서를 발급한다. 테스트할 때는 반드시 스테이징 CA를 쓴다.

```
{
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
}
```

스테이징에서 정상 동작하면 이 줄을 제거하고 프로덕션으로 전환한다.

### 포트 충돌

Caddy를 실행했는데 `bind: address already in use` 에러가 나면 해당 포트를 다른 프로세스가 쓰고 있는 것이다.

```bash
# 80 포트를 쓰는 프로세스 확인
sudo lsof -i :80
sudo lsof -i :443

# Apache가 돌고 있는 경우가 많다
sudo systemctl stop apache2
sudo systemctl disable apache2
```

### 로그 확인

```bash
# systemd 로그
sudo journalctl -u caddy --no-pager -f

# Caddyfile에 로그 설정 추가
```

```
example.com {
    log {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 5
        }
        format json
    }
    reverse_proxy localhost:8080
}
```

JSON 형식이 기본이다. 로그를 파싱하거나 모니터링 시스템에 보낼 때 편하다.

### 설정 검증

```bash
# Caddyfile 문법 검사
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# 어떤 JSON으로 변환되는지 확인
caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile --pretty
```

설정을 수정한 뒤에는 `caddy validate`로 먼저 검증하고, 문제가 없으면 `caddy reload`를 실행한다.

### caddy_data 볼륨 관련

Docker 환경에서 `docker-compose down -v`를 실행하면 볼륨이 전부 삭제된다. `caddy_data`에 저장된 인증서도 같이 날아간다. 볼륨을 삭제하면 인증서를 다시 발급받아야 하고, 반복하면 rate limit에 걸린다.

```bash
# 볼륨을 유지하면서 컨테이너만 중지/삭제
docker-compose down  # -v 옵션 없이

# 볼륨 확인
docker volume ls | grep caddy
```

### 업스트림 연결 실패

`reverse_proxy`로 백엔드에 연결할 수 없으면 `502 Bad Gateway`가 발생한다.

```bash
# 백엔드가 실제로 동작하는지 확인
curl -v localhost:8080

# Docker 환경이면 네트워크 확인
docker network ls
docker network inspect <network_name>
```

Docker Compose에서 `localhost`가 아니라 서비스 이름을 써야 한다. `reverse_proxy localhost:8080`이 아니라 `reverse_proxy app:8080`이다. 컨테이너 안에서 localhost는 컨테이너 자신을 가리킨다.
