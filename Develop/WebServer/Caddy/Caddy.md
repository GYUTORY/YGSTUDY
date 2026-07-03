---
title: Caddy
tags: [webserver, caddy, https, reverse-proxy, lets-encrypt, http3, xcaddy]
updated: 2026-04-14
---

# Caddy

## Caddy란

Go로 만든 웹 서버. 2015년 Matt Holt가 처음 만들었고, 2020년에 v2로 전면 재작성됐다. 가장 큰 특징은 HTTPS가 기본값이라는 것이다. 도메인만 지정하면 Let's Encrypt나 ZeroSSL에서 인증서를 자동으로 발급받고 갱신까지 알아서 한다. Nginx에서 certbot 설정하고 cron 걸어두던 작업이 필요 없다.

설정 파일(Caddyfile)이 단순해서 Nginx의 `nginx.conf`에 비하면 작성할 양이 확 줄어든다. 단, 고도로 세밀한 튜닝이 필요한 경우에는 Nginx가 더 나은 선택일 수 있다. Nginx와의 상세 비교는 [Nginx vs Caddy](../Nginx_vs_Caddy.md) 문서를 참고한다.

## 요청 처리 흐름

Caddy가 클라이언트 요청을 받아서 응답을 돌려주기까지의 과정이다.

```
  클라이언트
      │
      ▼
┌──────────────────────────────────────────────────┐
│  1. 리스너 (Listener)                              │
│     - TCP 연결 수락                                │
│     - 443 포트: TLS 핸드셰이크 수행                 │
│     - 443/udp 포트: QUIC 핸드셰이크 (HTTP/3)       │
│     - 80 포트: 평문 HTTP 수신                       │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  2. TLS 처리                                      │
│     - 인증서 자동 선택 (SNI 기반)                   │
│     - On-Demand TLS인 경우 여기서 인증서 발급       │
│     - OCSP 스테이플링 응답 첨부                     │
│     - HTTP 요청이면 HTTPS로 301 리다이렉트          │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  3. 호스트 매칭 (Server Matching)                  │
│     - Host 헤더 또는 SNI로 어떤 사이트 블록인지 결정 │
│     - 매칭되는 사이트가 없으면 fallback 처리         │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  4. 미들웨어 체인 (Handler Chain)                   │
│     - 라우트 매칭: path, header, method 등 조건     │
│     - 순서대로 미들웨어 실행:                        │
│       encode → header → rewrite → try_files →     │
│       reverse_proxy 또는 file_server               │
│     - 각 미들웨어가 요청을 수정하거나 다음으로 넘김   │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  5. 응답 반환                                      │
│     - 미들웨어 체인을 역순으로 거치며 응답 가공      │
│     - encode가 gzip/zstd 압축 적용                 │
│     - header 미들웨어가 응답 헤더 추가               │
│     - 로그 기록                                     │
└──────────────┬───────────────────────────────────┘
               │
               ▼
           클라이언트
```

Caddyfile에서 디렉티브를 나열하는 순서와 실제 실행 순서는 다르다. Caddy는 내부적으로 디렉티브마다 고정된 우선순위를 갖고 있다. 예를 들어 `encode`는 `reverse_proxy`보다 항상 먼저 실행된다. 이 순서를 직접 제어하려면 `route` 블록으로 감싸야 한다.

```
example.com {
    # 이 순서로 실행되는 게 아니다
    file_server
    encode gzip
    reverse_proxy localhost:8080
}

example.com {
    # route 안에서는 작성 순서대로 실행된다
    route {
        encode gzip
        reverse_proxy localhost:8080
        file_server
    }
}
```

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

Caddy의 핵심 기능이다. 도메인 이름으로 사이트를 설정하면 인증서 발급부터 갱신까지 전부 자동으로 처리된다.

### 자동 HTTPS 동작 과정

```
┌─────────────────────────────────────────────────────────┐
│  Caddy 시작 / 설정 로드                                   │
│  Caddyfile에서 도메인 목록 추출                            │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│  인증서 저장소 확인 (~/.local/share/caddy/ 또는 /data)    │
│  ├─ 유효한 인증서 있음 → 바로 사용, 만료 30일 전 갱신 예약 │
│  └─ 인증서 없음 또는 만료 → ACME 발급 시작                 │
└──────────────┬──────────────────────────────────────────┘
               │ (인증서 없는 경우)
               ▼
┌─────────────────────────────────────────────────────────┐
│  ACME 클라이언트 동작                                     │
│                                                         │
│  1) CA 선택: Let's Encrypt (기본) → 실패 시 ZeroSSL 폴백 │
│  2) 챌린지 수행 (도메인 소유 증명):                        │
│     ┌──────────────────────────────────────────────┐     │
│     │ HTTP-01 (기본)                                │     │
│     │ - 80 포트에서 /.well-known/acme-challenge/   │     │
│     │   토큰 파일 서빙                              │     │
│     │ - CA가 HTTP로 접근해서 토큰 검증               │     │
│     ├──────────────────────────────────────────────┤     │
│     │ TLS-ALPN-01                                   │     │
│     │ - 443 포트에서 특수 TLS 인증서로 검증          │     │
│     │ - 80 포트를 못 여는 환경에서 사용              │     │
│     ├──────────────────────────────────────────────┤     │
│     │ DNS-01                                        │     │
│     │ - DNS TXT 레코드로 검증                       │     │
│     │ - 와일드카드 인증서 발급 시 필수               │     │
│     │ - DNS 프로바이더 모듈 필요 (별도 빌드)         │     │
│     └──────────────────────────────────────────────┘     │
│  3) CSR 생성 → CA에 제출 → 인증서 수신                    │
│  4) 인증서 저장소에 보관                                   │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│  인증서 유지 관리 (백그라운드)                              │
│  - 만료 30일 전 자동 갱신 시도                             │
│  - 갱신 실패 시 점점 간격을 줄여가며 재시도                 │
│  - OCSP 스테이플링: OCSP 응답을 주기적으로 갱신             │
│  - 인증서 교체 시 프로세스 재시작 없이 즉시 적용            │
└─────────────────────────────────────────────────────────┘
```

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

### On-Demand TLS

일반 자동 HTTPS는 Caddy 시작 시점에 Caddyfile에 적힌 도메인의 인증서를 발급한다. On-Demand TLS는 다르다. 클라이언트가 TLS 핸드셰이크를 시작하는 시점에 인증서가 없으면 그때 발급한다.

SaaS 서비스에서 고객이 커스텀 도메인을 붙이는 경우에 쓴다. 고객이 100개 도메인을 연결하든 10,000개를 연결하든 Caddyfile에 일일이 적지 않아도 된다.

```
{
    on_demand_tls {
        ask http://localhost:5555/check-domain
        interval 2m
        burst 5
    }
}

https:// {
    tls {
        on_demand
    }
    reverse_proxy localhost:8080
}
```

`ask` 엔드포인트는 반드시 설정해야 한다. Caddy가 인증서를 발급하기 전에 이 URL로 도메인을 검증한다. 응답이 200이면 발급을 진행하고, 그 외에는 거부한다. 이걸 빠뜨리면 아무 도메인이나 인증서를 발급받을 수 있어서 Let's Encrypt rate limit을 빠르게 소진하게 된다.

`ask` 엔드포인트 구현 예시:

```go
// 허용된 도메인인지 DB에서 확인
func checkDomain(w http.ResponseWriter, r *http.Request) {
    domain := r.URL.Query().Get("domain")
    if isAllowedDomain(domain) {
        w.WriteHeader(200)
        return
    }
    w.WriteHeader(403)
}
```

`interval`과 `burst`는 인증서 발급 속도를 제한한다. 위 설정은 2분 간격으로 최대 5개까지 발급을 허용한다. DDoS 등으로 대량의 미지 도메인 요청이 들어올 때 Let's Encrypt에 과도한 요청을 보내는 것을 방지한다.

On-Demand TLS를 쓸 때 주의할 점:

- 첫 번째 요청에서 인증서 발급이 일어나므로 TLS 핸드셰이크가 수 초 걸릴 수 있다
- 발급된 인증서는 캐시되므로 두 번째 요청부터는 정상 속도다
- `ask` 엔드포인트가 죽으면 새 도메인의 인증서를 발급할 수 없다

## HTTP/3

Caddy는 HTTP/3(QUIC)을 기본으로 지원한다. v2.6부터 별도 설정 없이 활성화되어 있다.

### HTTP/3이 동작하는 방식

HTTP/3은 TCP가 아니라 UDP 기반의 QUIC 프로토콜 위에서 동작한다. 기존 HTTP/2가 TCP 위에서 head-of-line blocking 문제를 겪는 것과 달리, QUIC은 스트림 단위로 독립적이라서 하나의 패킷 손실이 다른 스트림을 막지 않는다.

```
┌─────────────────────────────────────────┐
│  HTTP/2 (TCP 기반)                       │
│                                         │
│  TCP 연결 1개                            │
│  ├── 스트림 1 ──► 패킷 손실 발생!        │
│  ├── 스트림 2 ──► 대기 (블로킹)          │
│  └── 스트림 3 ──► 대기 (블로킹)          │
│                                         │
│  → 하나가 막히면 전부 대기한다            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  HTTP/3 (QUIC/UDP 기반)                  │
│                                         │
│  QUIC 연결 1개                           │
│  ├── 스트림 1 ──► 패킷 손실 → 재전송     │
│  ├── 스트림 2 ──► 정상 진행              │
│  └── 스트림 3 ──► 정상 진행              │
│                                         │
│  → 손실된 스트림만 영향받는다             │
└─────────────────────────────────────────┘
```

### Caddy에서 HTTP/3 설정

기본적으로 활성화되어 있어서 따로 할 건 없다. 비활성화하거나 세부 설정이 필요한 경우:

```
{
    servers {
        protocols h1 h2 h3
    }
}
```

HTTP/3만 끄려면:

```
{
    servers {
        protocols h1 h2
    }
}
```

### Docker에서 HTTP/3

HTTP/3은 UDP를 쓰므로 Docker에서 UDP 포트를 별도로 열어야 한다.

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3용 UDP 포트
```

`443:443/udp`를 빠뜨리면 HTTP/3 연결이 성립하지 않고 HTTP/2로 폴백된다. 서비스 자체는 동작하지만 HTTP/3의 이점을 못 받는다.

### Alt-Svc 헤더

Caddy는 HTTP/2 응답에 `Alt-Svc` 헤더를 자동으로 추가한다. 브라우저는 이 헤더를 보고 다음 요청부터 HTTP/3(QUIC)으로 전환한다.

```
Alt-Svc: h3=":443"; ma=2592000
```

HTTP/3이 실제로 동작하는지 확인하려면 브라우저 개발자 도구의 네트워크 탭에서 Protocol 컬럼을 확인한다. `h3`으로 표시되면 HTTP/3으로 연결된 것이다. 첫 번째 요청은 HTTP/2이고, Alt-Svc를 받은 후 두 번째 요청부터 HTTP/3으로 전환되는 게 정상이다.

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

## xcaddy 플러그인 빌드

Caddy의 기본 바이너리에 포함되지 않는 기능(DNS 챌린지, 캐싱, rate limiting 등)은 모듈로 추가한다. `xcaddy`는 Go 모듈을 포함해서 Caddy 바이너리를 새로 컴파일하는 도구다.

### 기본 사용법

```bash
# xcaddy 설치 (Go 1.21+ 필요)
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# DNS 챌린지 모듈 포함 빌드
xcaddy build --with github.com/caddy-dns/cloudflare

# 여러 모듈을 한번에
xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/caddyserver/cache-handler \
    --with github.com/mholt/caddy-ratelimit

# 특정 Caddy 버전으로 빌드
xcaddy build v2.8.4 --with github.com/caddy-dns/cloudflare
```

빌드하면 현재 디렉토리에 `caddy` 바이너리가 생성된다. 이걸 기존 바이너리와 교체하면 된다.

```bash
# 빌드된 바이너리 교체
sudo mv caddy /usr/bin/caddy
sudo systemctl restart caddy

# 포함된 모듈 확인
caddy list-modules | grep dns
```

### Docker에서 커스텀 빌드

프로덕션에서 가장 많이 쓰는 방식이다. Multi-stage 빌드로 커스텀 Caddy 이미지를 만든다.

```dockerfile
FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/caddyserver/cache-handler

FROM caddy:2-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

`caddy:2-builder` 이미지에 xcaddy와 Go 빌드 환경이 이미 들어있다. 빌드가 끝나면 바이너리만 런타임 이미지로 복사하므로 최종 이미지 크기가 작다.

### 자주 쓰는 모듈

| 모듈 | 용도 |
|------|------|
| `github.com/caddy-dns/cloudflare` | Cloudflare DNS 챌린지 |
| `github.com/caddy-dns/route53` | AWS Route53 DNS 챌린지 |
| `github.com/caddyserver/cache-handler` | HTTP 캐싱 (Varnish 대안) |
| `github.com/mholt/caddy-ratelimit` | 요청 rate limiting |
| `github.com/mholt/caddy-webdav` | WebDAV 서버 |
| `github.com/greenpau/caddy-security` | 인증/인가 (JWT, OAuth2) |
| `github.com/mholt/caddy-l4` | TCP/UDP 레이어 4 프록시 |

### 모듈 개발

Caddy 모듈은 Go 인터페이스를 구현하는 구조체다. 간단한 미들웨어 모듈의 골격:

```go
package mymodule

import (
    "net/http"
    "github.com/caddyserver/caddy/v2"
    "github.com/caddyserver/caddy/v2/caddyhttp"
    "github.com/caddyserver/caddy/v2/modules/caddyhttp/caddyauth"
)

func init() {
    caddy.RegisterModule(MyMiddleware{})
}

type MyMiddleware struct{}

func (MyMiddleware) CaddyModule() caddy.ModuleInfo {
    return caddy.ModuleInfo{
        ID:  "http.handlers.my_middleware",
        New: func() caddy.Module { return new(MyMiddleware) },
    }
}

func (m MyMiddleware) ServeHTTP(w http.ResponseWriter, r *http.Request, next caddyhttp.Handler) error {
    // 요청 처리 로직
    return next.ServeHTTP(w, r)
}

var _ caddyhttp.MiddlewareHandler = (*MyMiddleware)(nil)
```

로컬에서 테스트할 때는 `xcaddy run`으로 모듈을 포함해서 바로 실행할 수 있다:

```bash
xcaddy run --with /path/to/my/module
```

## Docker 환경 설정

### 기본 Docker Compose

```yaml
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
      - ./site:/srv

volumes:
  caddy_data:
  caddy_config:
```

`caddy_data` 볼륨은 반드시 유지해야 한다. 여기에 인증서가 저장되는데, 볼륨을 날리면 인증서를 다시 발급받아야 하고, 짧은 시간에 반복 발급하면 Let's Encrypt rate limit에 걸린다.

### 리버스 프록시 + 앱 서버

```yaml
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
