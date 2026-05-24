---
title: 프록시 (Proxy)
tags: [network, proxy, forward-proxy, reverse-proxy, squid, nginx, x-forwarded-for, http-connect]
updated: 2026-05-24
---

# 프록시 (Proxy)

프록시는 클라이언트와 서버 사이에 끼어서 요청과 응답을 대신 주고받는 서버다. 누구를 대신하느냐로 포워드와 리버스가 갈린다. 포워드 프록시는 클라이언트를 대신해서 바깥 서버에 나가고, 리버스 프록시는 서버를 대신해서 클라이언트의 요청을 받는다. 같은 프로그램(Nginx 등)이 설정에 따라 양쪽 다 될 수 있어서 처음엔 헷갈리는데, "TCP 연결을 누가 먼저 거느냐"로 보면 구분이 쉽다.

## 요청이 실제로 어떻게 흐르는가

### 포워드 프록시

사내망에서 `curl http://example.com` 을 친다고 하자. 프록시가 없으면 클라이언트가 example.com의 IP로 직접 TCP 연결을 연다. 포워드 프록시를 쓰면 흐름이 이렇게 바뀐다.

```
클라이언트 → (사내 프록시 192.168.0.10:3128) → example.com
```

1. 클라이언트가 프록시(192.168.0.10:3128)로 TCP 연결을 연다. example.com이 아니다.
2. 클라이언트는 프록시에게 절대 URL이 들어간 요청 라인을 보낸다.
   ```
   GET http://example.com/index.html HTTP/1.1
   Host: example.com
   ```
   직접 연결할 때는 `GET /index.html HTTP/1.1` 처럼 경로만 보내지만, 프록시에게는 어디로 가야 하는지 알려줘야 하므로 스킴과 호스트까지 통째로 보낸다. 이게 프록시 요청과 일반 요청의 첫 번째 차이다.
3. 프록시가 example.com에 새로 TCP 연결을 열고, 받은 요청을 전달한다. 이때 example.com 입장에서 출발지 IP는 클라이언트가 아니라 프록시다.
4. 응답을 받아 클라이언트에게 되돌려준다.

example.com은 누가 진짜로 요청했는지 모른다. 출발지 IP가 프록시로 가려지는 게 포워드 프록시의 본질이다. 그래서 사내 인터넷 통제, 접근 차단, 캐싱 용도로 쓴다.

### 리버스 프록시

이번엔 서비스를 운영하는 입장이다. 사용자는 `https://api.example.com` 하나만 알고, 뒤에 백엔드가 몇 대인지 모른다.

```
사용자 → (api.example.com:443 = Nginx) → 백엔드 10.0.0.11:8080, 10.0.0.12:8080
```

1. 사용자가 api.example.com:443으로 연결한다. 이 IP는 Nginx의 IP다. 사용자는 자기가 프록시에 붙는다는 걸 인식하지 못한다.
2. Nginx가 TLS를 끝내고(SSL 종료), 평문 HTTP로 백엔드 중 한 대를 골라 전달한다.
3. 백엔드는 응답을 Nginx에게 주고, Nginx가 다시 TLS로 감싸 사용자에게 보낸다.

여기서 백엔드 입장에서 출발지 IP는 사용자가 아니라 Nginx다. 포워드와 반대로 이번엔 서버 쪽 구조가 가려진다. 그리고 백엔드가 진짜 클라이언트 IP를 알려면 별도 헤더가 필요한데, 뒤에서 다룰 `X-Forwarded-For` 문제가 여기서 시작된다.

포워드와 리버스의 핵심 차이는 위치가 아니라 누가 프록시의 존재를 아느냐다. 포워드는 클라이언트가 프록시 주소를 알고 명시적으로 설정한다. 리버스는 클라이언트가 모른 채 그냥 정상 서버에 접속한다고 믿는다.

## Squid 포워드 프록시 최소 설정

Squid는 포워드 프록시의 대표격이다. 패키지로 깔면 `/etc/squid/squid.conf`에 기본 설정이 한가득 들어있는데, 처음 띄울 때 동작하는 최소 설정만 추리면 이 정도다.

```
# /etc/squid/squid.conf
http_port 3128

# 어느 출발지를 허용할지 정의
acl localnet src 192.168.0.0/16
acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443
acl CONNECT method CONNECT

# CONNECT는 443 외 포트로는 막는다 (포트 우회 방지)
http_access deny CONNECT !SSL_ports

# 사내망만 허용, 나머지 거부
http_access allow localnet
http_access deny all

# 캐시 디렉토리 (100MB, 디스크 캐시)
cache_dir ufs /var/spool/squid 100 16 256
```

설정 후 `squid -k parse`로 문법을 검사하고, `systemctl restart squid`로 띄운다. 클라이언트는 이렇게 붙는다.

```bash
curl -x http://192.168.0.10:3128 http://example.com
```

처음 운영하면서 가장 자주 막히는 게 `http_access deny all` 위치다. Squid는 위에서 아래로 규칙을 평가하고 처음 매칭되는 줄에서 멈춘다. `allow localnet`보다 `deny all`을 위에 두면 사내망 요청도 전부 막힌다. 403이 뜨면 access.log부터 본다.

```bash
tail -f /var/log/squid/access.log
# 1716500000.123  0 192.168.0.55 TCP_DENIED/403 ... GET http://example.com/
```

`TCP_DENIED/403`이면 acl 매칭이 안 된 거고, `TCP_MISS/200`이면 정상적으로 원서버에서 받아온 것, `TCP_HIT/200`이면 캐시에서 응답한 것이다. 캐시가 도는지 확인하려면 같은 URL을 두 번 치고 MISS가 HIT으로 바뀌는지 본다.

## Nginx 리버스 프록시 최소 설정

```nginx
# /etc/nginx/conf.d/api.conf
upstream backend {
    server 10.0.0.11:8080;
    server 10.0.0.12:8080;
}

server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate     /etc/nginx/certs/api.crt;
    ssl_certificate_key /etc/nginx/certs/api.key;

    location / {
        proxy_pass http://backend;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`proxy_set_header`를 빼먹으면 백엔드가 받는 정보가 망가진다. `Host`를 안 넘기면 백엔드에는 `backend`(upstream 이름)나 IP가 Host로 찍혀서, 가상 호스트로 도메인을 구분하는 백엔드가 엉뚱한 vhost로 라우팅한다. `X-Forwarded-Proto`를 안 넘기면 백엔드가 평문 HTTP로 받았으니 자기가 HTTP인 줄 알고, 리다이렉트 URL을 `http://`로 만들어서 무한 리다이렉트가 나는 경우가 있다.

`$proxy_add_x_forwarded_for`는 들어온 요청에 이미 `X-Forwarded-For`가 있으면 거기에 `$remote_addr`를 콤마로 이어붙이고, 없으면 새로 만든다. 프록시를 여러 단 거칠 때 IP가 누적되도록 하는 변수다.

설정 바꾸면 항상 `nginx -t`로 검사하고 `nginx -s reload`로 무중단 반영한다. `restart`는 연결을 끊으니 운영 중엔 reload를 쓴다.

## HTTPS는 프록시를 어떻게 통과하는가 (HTTP CONNECT)

포워드 프록시 설정에서 평문 HTTP는 프록시가 요청을 읽고 전달한다고 했다. 그런데 HTTPS는 프록시가 내용을 읽을 수 없다. 읽으려면 프록시가 중간에서 인증서를 위조해야 하는데(MITM), 일반적인 포워드 프록시는 그렇게 하지 않는다. 대신 `CONNECT` 메서드로 터널을 뚫는다.

```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

클라이언트가 프록시에게 "example.com:443으로 TCP 통로만 열어달라"고 요청한다. 프록시는 그 목적지에 TCP를 연결하고 성공하면 이렇게 답한다.

```
HTTP/1.1 200 Connection Established
```

이 200이 떨어진 다음부터 프록시는 양쪽 바이트를 그대로 펌프질만 한다. TLS 핸드셰이크와 암호화된 데이터는 프록시를 그냥 통과하고, 프록시는 안을 못 본다. 도착지 호스트와 포트, 그리고 오가는 바이트 양만 안다.

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant P as 포워드 프록시
    participant S as example.com:443

    C->>P: CONNECT example.com:443
    P->>S: TCP 연결 시도
    S-->>P: TCP 연결됨
    P-->>C: 200 Connection Established
    Note over C,S: 이후 프록시는 바이트만 중계
    C->>S: TLS ClientHello (프록시 통과)
    S-->>C: TLS ServerHello (프록시 통과)
    C->>S: 암호화된 HTTP 요청
    S-->>C: 암호화된 HTTP 응답
```

Squid 설정에서 `http_access deny CONNECT !SSL_ports`를 넣은 이유가 여기 있다. CONNECT는 임의 포트로 TCP 터널을 열 수 있어서, 막지 않으면 SSH(22)나 다른 포트로 우회 통로를 뚫는 데 악용된다. 그래서 보통 443만 허용한다.

`curl -v`로 HTTPS를 프록시 경유시키면 이 과정이 그대로 보인다.

```bash
curl -v -x http://192.168.0.10:3128 https://example.com 2>&1 | head -20
# * Establish HTTP proxy tunnel to example.com:443
# > CONNECT example.com:443 HTTP/1.1
# < HTTP/1.1 200 Connection established
# * CONNECT phase completed
# * SSL connection using TLSv1.3 ...
```

`CONNECT`가 200을 못 받으면 프록시가 그 목적지를 막은 것이고, 200은 받았는데 TLS 단계에서 실패하면 프록시 문제가 아니라 원서버 인증서 문제다. 이 경계를 알면 장애 원인을 절반으로 좁힐 수 있다.

## X-Forwarded-For는 믿을 수 없다

리버스 프록시 뒤 백엔드가 클라이언트 IP를 알려면 `X-Forwarded-For`(XFF)를 본다. 문제는 이 헤더가 그냥 HTTP 헤더라서 누구나 위조할 수 있다는 점이다.

### IP 스푸핑

클라이언트가 직접 가짜 XFF를 박아서 보내면 이렇게 된다.

```bash
curl -H "X-Forwarded-For: 1.2.3.4" https://api.example.com
```

백엔드가 XFF를 그대로 믿고 접근 제어나 로그에 쓰면, 공격자는 자기 IP를 1.2.3.4로 위장한다. IP 화이트리스트로 관리자 페이지를 막아놨는데 XFF만 보고 통과시키면 그대로 뚫린다. XFF는 인증 수단이 아니다.

### 프록시 체인

CDN → 회사 LB → Nginx → 백엔드처럼 프록시를 여러 단 거치면 XFF가 콤마로 쌓인다.

```
X-Forwarded-For: 203.0.113.10, 70.41.3.18, 10.0.0.5
```

맨 왼쪽이 원래 클라이언트, 오른쪽으로 갈수록 가까운 프록시다. 그런데 맨 왼쪽 값(`203.0.113.10`)은 클라이언트가 직접 넣었을 수도 있어서 위조 가능하다. 신뢰할 수 있는 건 "내가 직접 통제하는 프록시가 추가한 값"뿐이다. 그래서 "오른쪽에서부터 내가 믿는 프록시 IP를 건너뛰고, 처음 만나는 믿지 못하는 IP가 진짜 클라이언트"라는 식으로 거꾸로 세어야 한다. 무작정 맨 앞 값을 클라이언트 IP로 쓰면 안 된다.

### Forwarded 헤더 (RFC 7239)

XFF는 사실상 표준일 뿐 RFC로 정해진 게 아니라 `X-Forwarded-Host`, `X-Forwarded-Proto`가 따로 노는 문제가 있다. RFC 7239의 `Forwarded`는 이걸 한 헤더로 묶는다.

```
Forwarded: for=203.0.113.10;proto=https;host=api.example.com, for=70.41.3.18
```

의도는 좋은데 실제로는 아직 XFF가 압도적으로 많이 쓰인다. 백엔드 프레임워크나 라이브러리가 `Forwarded`를 안 읽는 경우도 흔해서, 새로 만드는 시스템이 아니면 XFF로 맞추는 게 현실적이다.

### nginx real_ip 모듈로 원본 IP 복원

백엔드가 매번 XFF를 파싱해서 진짜 IP를 골라내는 건 번거롭고 실수가 잦다. Nginx의 `ngx_http_realip_module`을 쓰면 Nginx 단에서 `$remote_addr` 자체를 진짜 클라이언트 IP로 바꿔준다.

```nginx
server {
    listen 443 ssl;

    # 이 IP/대역에서 온 요청의 XFF만 신뢰한다
    set_real_ip_from 10.0.0.0/8;       # 내부 LB 대역
    set_real_ip_from 173.245.48.0/20;  # 예: CDN 대역

    # XFF를 거꾸로 훑어 신뢰 대역을 건너뛰고 진짜 IP를 $remote_addr에 넣는다
    real_ip_header    X-Forwarded-For;
    real_ip_recursive on;

    location / {
        proxy_pass http://backend;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

핵심은 `set_real_ip_from`이다. 여기 적은 대역에서 온 요청의 XFF만 믿고, 그 외 출발지가 보낸 XFF는 무시한다. `real_ip_recursive on`은 XFF를 오른쪽부터 훑으면서 신뢰 대역에 속한 IP를 건너뛰고, 처음 만나는 신뢰 밖 IP를 진짜 클라이언트로 잡는다. 이게 위의 "거꾸로 세기"를 자동으로 해주는 옵션이다.

`set_real_ip_from`을 0.0.0.0/0 같은 걸로 넣거나 아예 안 막으면, 외부에서 위조한 XFF를 그대로 믿어버려서 스푸핑 방어가 무너진다. 신뢰 대역은 내가 실제로 통제하는 프록시/LB/CDN의 IP만 좁게 적어야 한다.

## curl로 프록시 경유 디버깅하기

프록시 문제는 "어디까지 갔다가 막혔는지"를 모르면 추측만 하게 된다. curl 몇 개 옵션이면 단계를 나눠 확인할 수 있다.

프록시를 거쳐 나가기:

```bash
# HTTP 프록시 지정
curl -x http://192.168.0.10:3128 http://example.com

# 프록시 인증이 필요할 때
curl -x http://user:pass@192.168.0.10:3128 http://example.com

# 환경변수로도 됨 (대문자/소문자 둘 다 인식되는 경우가 많음)
export http_proxy=http://192.168.0.10:3128
export https_proxy=http://192.168.0.10:3128
curl http://example.com
```

백엔드가 받는 헤더를 직접 확인하려면, 받은 헤더를 그대로 돌려주는 서비스로 쏴본다.

```bash
curl -x http://192.168.0.10:3128 https://httpbin.org/headers
# {
#   "headers": {
#     "Host": "httpbin.org",
#     "X-Forwarded-For": "203.0.113.10",
#     ...
#   }
# }
```

리버스 프록시 뒤 백엔드가 XFF를 제대로 받는지 확인할 때는, 프록시를 건너뛰고 백엔드에 직접 요청한 결과와 프록시 경유 결과를 비교한다.

```bash
# 1. 프록시(Nginx) 경유 — XFF에 내 IP가 들어있어야 정상
curl https://api.example.com/debug/headers

# 2. 백엔드 직접 (사내망에서) — XFF가 없어야 정상
curl http://10.0.0.11:8080/debug/headers
```

2번에 XFF가 이미 들어있다면, 백엔드가 외부에 직접 노출됐거나 누군가 위조 헤더를 박은 것이다. 헤더만 보고 동작을 확인하고 싶으면 `-v`로 요청/응답 헤더를 모두 펼친다.

```bash
curl -v -x http://192.168.0.10:3128 https://example.com 2>&1 | grep -E '^[<>]'
# > CONNECT example.com:443 HTTP/1.1
# < HTTP/1.1 200 Connection established
# > GET / HTTP/2
# < HTTP/2 200
```

`>`는 보낸 것, `<`는 받은 것이다. CONNECT 줄까지만 나오고 200 Connection established가 안 보이면 프록시-원서버 사이가 막힌 것이고, 그 뒤 GET까지 갔는데 응답이 5xx면 원서버 문제다. 프록시를 의심할지 서버를 의심할지를 이 출력으로 가른다.

## 자주 부딪히는 문제

도메인은 되는데 IP로는 안 될 때: 리버스 프록시가 `Host` 헤더로 vhost를 고르는데, IP로 접속하면 Host가 IP라 매칭되는 server 블록이 없어서 기본 블록으로 빠진다. `curl -H "Host: api.example.com" http://10.0.0.11` 처럼 Host를 강제로 넣어 확인한다.

무한 리다이렉트: 백엔드가 HTTPS인지 판단을 못 해서 매번 https로 리다이렉트한다. `proxy_set_header X-Forwarded-Proto $scheme` 가 빠졌거나, 백엔드 프레임워크에서 이 헤더를 신뢰하도록 설정하지 않은 경우다.

로그에 전부 프록시 IP만 찍힐 때: real_ip 모듈을 안 걸었거나 `set_real_ip_from`에 LB 대역이 빠진 것이다. XFF는 들어오는데 `$remote_addr`가 안 바뀐다면 거의 이 케이스다.

CONNECT가 403일 때: 포워드 프록시가 그 포트나 목적지를 막았다. Squid라면 access.log에서 `TCP_DENIED`와 acl 규칙을 확인한다.

## 참고

- [RFC 7239 - Forwarded HTTP Extension](https://datatracker.ietf.org/doc/html/rfc7239)
- [RFC 9110 - HTTP Semantics (CONNECT 메서드)](https://datatracker.ietf.org/doc/html/rfc9110#section-9.3.6)
- [Nginx - ngx_http_proxy_module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Nginx - ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html)
- [Squid 공식 문서](http://www.squid-cache.org/Doc/)
