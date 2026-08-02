---
title: Nginx WebSocket 프록시
tags: [nginx, websocket, proxy, ssl, Socket.IO, SockJS]
updated: 2026-07-26
---

# Nginx WebSocket 프록시

## WebSocket과 HTTP 프록시의 차이

HTTP는 요청-응답 사이클로 끝나지만, WebSocket은 초기 HTTP Upgrade 핸드셰이크 이후 TCP 연결을 그대로 유지한다. Nginx가 일반 HTTP를 프록시할 때와 달리, WebSocket에서는 이 TCP 연결을 닫지 않고 양방향으로 데이터를 흘려야 한다.

문제는 Nginx가 기본 동작으로 `Connection: keep-alive`를 upstream에 전달하지 않는다는 점이다. HTTP/1.1 프록시 표준(RFC 7230)에서 hop-by-hop 헤더는 다음 노드에 전달하지 않는 것이 원칙이다. `Connection`, `Upgrade`가 여기에 해당한다. 그래서 명시적으로 두 헤더를 추가해줘야 한다.

```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

`$http_upgrade`는 클라이언트가 보낸 `Upgrade` 헤더 값을 그대로 담는다. 클라이언트가 WebSocket 핸드셰이크를 보내면 `websocket`이 들어간다. `Connection: upgrade`를 고정값으로 써도 되고, 아래처럼 조건부로 처리해도 된다.

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }
}
```

일반 HTTP 요청과 WebSocket을 같은 location에서 처리해야 할 때 map 방식이 낫다. `Upgrade` 헤더가 없는 요청은 `Connection: close`로 처리해서 불필요한 연결 유지를 막는다.

## proxy_read_timeout을 올려야 하는 이유

WebSocket 연결은 수분~수시간 동안 idle 상태가 유지될 수 있다. 기본 `proxy_read_timeout`은 60초인데, 이 시간 동안 upstream에서 데이터가 오지 않으면 Nginx가 연결을 끊는다.

채팅 앱에서 유저가 아무 말도 안 하고 창을 켜놓으면 60초 후 연결이 끊긴다. 클라이언트에서는 reconnect 로직이 돌아서 금방 재연결되는 것처럼 보이지만, 서버 로그를 보면 `upstream timed out (110: Connection timed out)` 에러가 쌓인다.

```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_connect_timeout 10s;
}
```

`proxy_connect_timeout`은 upstream과 TCP 연결 수립 시간이라 짧게 유지해도 된다. `proxy_read_timeout`과 `proxy_send_timeout`만 늘린다. 1시간(3600s)이 일반적이지만, 서비스 특성에 따라 조정한다.

timeout을 늘리면 좀비 연결이 쌓일 수 있다. 클라이언트가 비정상 종료했을 때 서버가 이를 감지하지 못하면 연결이 그대로 남는다. WebSocket keepalive ping을 애플리케이션 레벨에서 구현하거나, TCP keepalive를 설정해서 죽은 연결을 정리해야 한다.

```nginx
# upstream과의 TCP keepalive
proxy_socket_keepalive on;
```

## WSS: SSL termination 설정

클라이언트-Nginx 구간은 HTTPS(WSS), Nginx-backend 구간은 HTTP(WS)로 처리하는 게 일반적인 패턴이다. SSL을 Nginx에서 끊고 내부 네트워크는 평문으로 통신한다.

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/example.com.crt;
    ssl_certificate_key /etc/nginx/ssl/example.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location /ws {
        proxy_pass http://127.0.0.1:8080;  # backend는 ws://
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

# HTTP를 HTTPS로 리다이렉트
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

클라이언트는 `wss://example.com/ws`로 연결한다. Nginx가 TLS를 처리하고, backend는 `ws://127.0.0.1:8080`으로 전달받는다.

backend가 클라이언트 실제 IP를 알아야 할 때는 `X-Forwarded-For`와 `X-Real-IP`를 헤더로 넘긴다. 또한 backend가 프로토콜을 구분해야 할 때(HTTP vs HTTPS 분기)는 `X-Forwarded-Proto`도 추가한다.

## 연결 끊김 디버깅

WebSocket 연결이 예상보다 빨리 끊기면 원인이 여러 곳에 있다.

**Nginx error 로그 확인부터 시작한다.**

```bash
tail -f /var/log/nginx/error.log | grep -E "upstream|timeout|WebSocket"
```

자주 보이는 에러와 원인:

`upstream timed out (110: Connection timed out) while reading response header`
— proxy_read_timeout이 짧거나, backend가 초기 HTTP 101 응답을 제때 보내지 못한 경우다.

`upstream prematurely closed connection while reading response header`
— backend가 WebSocket 핸드셰이크 전에 연결을 닫았다. backend 로그를 봐야 한다.

`no live upstreams while connecting to upstream`
— upstream이 전부 다운됐거나 health check에서 탈락했을 때다.

**debug 로그로 핸드셰이크 과정을 추적할 수 있다.**

```nginx
error_log /var/log/nginx/error.log debug;
```

다만 debug 로그는 트래픽이 많으면 디스크를 순식간에 채우므로, 운영 환경에서 잠깐 켰다가 바로 끈다.

**access 로그에서 101 응답 코드를 확인한다.**

WebSocket 핸드셰이크가 성공하면 HTTP 101 Switching Protocols가 로그에 찍힌다. 101이 아니라 400, 502 같은 코드가 보이면 핸드셰이크 자체가 실패한 것이다.

```nginx
log_format ws_log '$remote_addr - $remote_user [$time_local] '
                  '"$request" $status $body_bytes_sent '
                  '"$http_upgrade" "$http_connection"';

access_log /var/log/nginx/ws_access.log ws_log;
```

**로드밸런서가 앞에 있을 때 주의사항**

AWS ALB나 GCP Load Balancer 뒤에 Nginx가 있으면, 로드밸런서 자체의 idle timeout도 확인해야 한다. ALB 기본 idle timeout은 60초다. Nginx timeout을 1시간으로 늘려도 ALB가 60초 만에 연결을 끊으면 소용없다. ALB timeout도 맞춰서 올려야 한다.

## Socket.IO 프록시 특이사항

Socket.IO는 순수 WebSocket이 아니다. 연결 초기에 HTTP long-polling으로 시작해서 WebSocket으로 업그레이드하는 과정을 거친다. 이 때문에 일반 WebSocket 프록시 설정만으로는 부족할 때가 있다.

```nginx
upstream socket_io_backend {
    ip_hash;  # sticky session 필수
    server 127.0.0.1:3000;
    server 127.0.0.1:3001;
}

server {
    location /socket.io/ {
        proxy_pass http://socket_io_backend;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;

        # polling 요청에 대한 버퍼링 설정
        proxy_buffering off;
    }
}
```

`ip_hash`가 중요하다. Socket.IO는 long-polling 단계에서 여러 HTTP 요청을 보내는데, 이 요청들이 서로 다른 backend 서버로 가면 세션을 찾지 못해 연결이 실패한다. 스케일아웃 환경에서는 반드시 sticky session을 써야 한다.

`proxy_buffering off`도 설정한다. 버퍼링이 켜져 있으면 Nginx가 backend 응답을 모아서 클라이언트에게 전달하는데, 실시간 스트리밍 특성상 응답이 지연된다.

Socket.IO 4.x 이후 버전에서는 서버 측에서 `transports: ['websocket']`으로 고정하면 polling 없이 바로 WebSocket만 쓸 수 있다. backend가 이 설정을 지원한다면 프록시 설정이 단순해진다.

## SockJS 프록시 특이사항

SockJS도 Socket.IO와 비슷하게 WebSocket을 지원하지 않는 환경에서 HTTP streaming, long-polling 등으로 폴백한다. 하지만 SockJS는 `/info` 엔드포인트로 서버 정보를 먼저 조회하는 과정이 있다.

```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # SockJS iframe transport 지원
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout 3600s;
    proxy_buffering off;
}
```

SockJS iframe transport를 쓸 때 `X-Forwarded-Proto`가 없으면 mixed-content 오류가 생길 수 있다. HTTPS 환경에서 SockJS가 HTTP로 폴백 요청을 보내는 경우다.

Spring에서 STOMP + SockJS를 쓸 때 `/ws/info?t=...` 요청이 먼저 날아온다. 이 요청이 프록시를 통과하지 못하면 연결 자체가 시작되지 않는다. location prefix가 정확히 매칭되는지 확인해야 한다.

## 실무에서 자주 빠지는 함정

**`proxy_set_header Host` 누락**

backend가 virtual host 기반으로 동작하면 `Host` 헤더가 없을 때 요청을 거부한다. WebSocket 설정에서 누락되는 경우가 잦다.

**HTTP/1.0으로 동작하는 경우**

`proxy_http_version 1.1`을 빠뜨리면 Nginx가 HTTP/1.0으로 upstream에 요청한다. HTTP/1.0은 WebSocket Upgrade를 지원하지 않아서 핸드셰이크가 실패한다. 에러 로그에 101 대신 400이 찍힌다.

**다중 서버 환경에서 세션 공유**

Redis를 통한 세션 공유나 sticky session 없이 다중 backend를 쓰면, 클라이언트가 재연결할 때 다른 서버로 붙어서 기존 연결 상태를 잃는다. Socket.IO는 adapter(redis-adapter)로 해결하고, 직접 구현한 WebSocket은 Redis pub/sub으로 메시지를 라우팅하는 방식을 주로 쓴다.
