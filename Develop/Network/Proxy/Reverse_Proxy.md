---
title: 리버스 프록시 (Reverse Proxy)
tags: [network, proxy, reverse-proxy, nginx, upstream, health-check, x-forwarded-for, 502, 504, timeout, buffering]
updated: 2026-06-17
---

# 리버스 프록시 (Reverse Proxy)

리버스 프록시는 서버 앞에 서서 클라이언트의 요청을 대신 받는 서버다. 클라이언트는 리버스 프록시가 진짜 서버라고 믿고 접속하고, 뒤에 백엔드가 몇 대 있는지, 무슨 언어로 짰는지는 모른다. Nginx, HAProxy, Envoy 같은 게 이 역할을 한다.

포워드/리버스 구분과 요청이 흐르는 기본 모양은 [프록시 개요](Proxy.md)에 정리했다. 이 문서는 리버스 프록시를 실제로 운영할 때 만지는 설정과, 새벽에 알림 받고 깨는 502/504 장애에 집중한다. 백엔드를 여러 대로 늘리고 부하를 나누는 부분은 [로드 밸런싱](Load_Balancing.md)에서 더 본다.

## 포워드 프록시와 무엇이 다른가

같은 Nginx인데 설정만 바꾸면 포워드도 되고 리버스도 된다. 그래서 둘을 위치로 구분하려 하면 헷갈린다. 기준은 누가 프록시의 존재를 아느냐다.

[포워드 프록시](Forward_Proxy.md)는 클라이언트가 프록시 주소를 알고, 자기 설정에 프록시를 박아넣는다. 사내망에서 `http_proxy=http://proxy.corp:3128` 같은 환경변수를 거는 게 그거다. 목적지 서버는 누가 프록시를 거쳐 들어왔는지 모르고, 그냥 프록시 IP에서 온 요청으로 본다. 클라이언트 쪽을 대신한다.

리버스 프록시는 반대다. 클라이언트는 프록시가 있는 줄도 모르고 `https://api.example.com`에 그냥 접속한다. 그 도메인의 IP가 사실은 리버스 프록시고, 진짜 백엔드는 사설망 안에 숨어 있다. 서버 쪽을 대신한다.

| | 포워드 프록시 | 리버스 프록시 |
|---|---|---|
| 누구를 대신하나 | 클라이언트 | 서버 |
| 클라이언트가 프록시를 아나 | 안다 (직접 설정) | 모른다 |
| 어디에 두나 | 클라이언트 망 출구 | 서버 망 입구 |
| 주 용도 | 외부 접근 통제, 캐싱, 로깅 | 부하 분산, TLS 종료, 백엔드 은닉 |
| 목적지가 출발지를 보면 | 프록시 IP | 클라이언트 IP (XFF로 전달 시) |

실무에서 리버스 프록시를 쓰는 이유는 대개 이렇다. 백엔드를 여러 대 두고 한 주소로 묶는다. TLS 인증서를 프록시에서 한 번만 처리하고 백엔드는 평문 HTTP로 받게 한다(TLS termination). 정적 파일은 프록시가 직접 주고 동적 요청만 백엔드로 넘긴다. 백엔드 IP를 외부에 노출하지 않는다.

## upstream과 백엔드 분산

리버스 프록시의 핵심은 `upstream` 블록이다. 백엔드 서버 묶음에 이름을 붙이고, `proxy_pass`에서 그 이름을 가리킨다.

```nginx
upstream backend {
    server 10.0.0.11:8080;
    server 10.0.0.12:8080;
    server 10.0.0.13:8080;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://backend;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

기본 분산 방식은 라운드로빈이다. 요청이 올 때마다 11 → 12 → 13 → 11 순서로 돌아가며 넘긴다. 백엔드 성능이 다르면 `weight`로 비중을 준다.

```nginx
upstream backend {
    server 10.0.0.11:8080 weight=3;  # 3배 더 받는다
    server 10.0.0.12:8080 weight=1;
    server 10.0.0.13:8080 weight=1;
}
```

세션을 메모리에 들고 있는 백엔드(로그인 상태를 서버 메모리에 저장하는 구식 구조)면 라운드로빈이 문제가 된다. 매 요청이 다른 서버로 가서 로그인이 풀린다. 이럴 때 `ip_hash`로 같은 클라이언트 IP는 같은 백엔드로 고정한다.

```nginx
upstream backend {
    ip_hash;
    server 10.0.0.11:8080;
    server 10.0.0.12:8080;
}
```

`ip_hash`는 백엔드를 한 대 빼거나 넣으면 해시 분포가 바뀌어서 상당수 클라이언트가 다른 서버로 재배치된다. 그래서 가능하면 세션을 Redis 같은 외부 저장소로 빼고 백엔드를 무상태로 만드는 게 맞다. 분산 알고리즘과 그 trade-off는 [로드 밸런싱](Load_Balancing.md)에 더 자세히 있다.

부하가 많이 몰리면 `least_conn`(연결 수가 가장 적은 서버로)도 쓴다. 요청 처리 시간이 들쭉날쭉할 때 라운드로빈보다 균형이 낫다.

## 헬스체크 — passive와 active

백엔드 한 대가 죽었는데 프록시가 모르고 계속 요청을 넘기면 그쪽으로 간 요청은 다 실패한다. 헬스체크는 죽은 백엔드를 분산 대상에서 빼는 일이다.

오픈소스 Nginx의 기본 헬스체크는 passive다. 별도 헬스체크용 요청을 보내지 않고, 실제 트래픽을 넘겼다가 실패하면 그걸로 판단한다. `max_fails`와 `fail_timeout`으로 조절한다.

```nginx
upstream backend {
    server 10.0.0.11:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.12:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.13:8080 max_fails=3 fail_timeout=30s backup;  # 평소엔 안 쓰고 다 죽으면 투입
}
```

`fail_timeout=30s` 동안 `max_fails=3`번 실패하면 그 서버를 30초간 빼둔다. 30초 지나면 다시 요청을 한 번 보내보고, 또 실패하면 다시 뺀다. 여기서 "실패"가 뭔지를 정확히 알아야 한다. 기본값으로는 연결 거부(connection refused)나 타임아웃만 실패로 친다. 백엔드가 500을 뱉는 건 기본적으로 실패가 아니다. 500도 죽은 걸로 보고 다른 서버로 넘기려면 `proxy_next_upstream`을 손봐야 한다.

```nginx
location / {
    proxy_pass http://backend;
    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 2;
    proxy_next_upstream_timeout 10s;
}
```

passive 헬스체크의 약점은 "실제 요청이 실패해야 안다"는 점이다. 백엔드가 방금 죽었는데 max_fails에 도달하기 전까지는 그쪽으로 간 사용자 요청 몇 개가 에러를 받는다. 이걸 미리 감지하려면 active 헬스체크가 필요한데, 이건 Nginx Plus(상용) 기능이다(`health_check` 지시어). 오픈소스에서 active를 원하면 `nginx_upstream_check_module` 같은 서드파티 모듈을 붙이거나, HAProxy/Envoy로 가는 선택지가 있다. HAProxy는 오픈소스에서도 active 헬스체크가 기본이라, 헬스체크가 중요하면 이쪽을 쓰는 팀이 많다.

```
# HAProxy 예시 — /health 를 2초마다 찔러본다
backend app_servers
    option httpchk GET /health
    default-server check inter 2s fall 3 rise 2
    server app1 10.0.0.11:8080
    server app2 10.0.0.12:8080
```

헬스체크 엔드포인트(`/health`)는 백엔드에서 가볍게 만들어야 한다. DB 커넥션까지 다 확인하는 무거운 헬스체크를 2초마다 때리면 그게 부하가 된다. 반대로 단순히 200만 반환하면 프로세스는 살았는데 DB가 끊긴 상태를 못 잡는다. 보통 얕은 헬스체크(프로세스 생존)와 깊은 헬스체크(의존성 확인)를 엔드포인트로 나눠두고, 분산용에는 얕은 쪽을 쓴다.

## X-Forwarded-For와 Host 헤더 전달

리버스 프록시를 거치면 백엔드가 보는 출발지 IP는 전부 프록시 IP가 된다. TCP 연결을 프록시가 다시 맺기 때문이다. 백엔드에서 클라이언트 IP로 로그를 남기거나 IP 기반 차단을 하려면, 프록시가 원래 클라이언트 IP를 헤더에 실어 넘겨야 한다.

```nginx
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Host              $host;
```

`$proxy_add_x_forwarded_for`는 들어온 요청에 이미 XFF가 있으면 거기에 `$remote_addr`를 콤마로 덧붙이고, 없으면 새로 만든다. 그래서 프록시가 여러 단 겹치면 `X-Forwarded-For: 실제클라이언트, 1단프록시, 2단프록시` 식으로 IP가 쌓인다. 백엔드는 보통 맨 앞을 클라이언트로 본다. 단, XFF는 그냥 HTTP 헤더라 클라이언트가 위조할 수 있다. 신뢰 경계 밖에서 들어온 XFF를 그대로 믿으면 IP 차단을 우회당한다. 위조 처리와 `set_real_ip_from` 신뢰 설정은 [프록시 개요](Proxy.md)의 XFF 절에 정리했다.

`Host` 헤더를 빠뜨리는 게 리버스 프록시 초보가 가장 자주 밟는 지뢰다. `proxy_set_header Host $host`를 안 적으면 Nginx는 기본적으로 `proxy_pass`에 적힌 upstream 이름(`backend`)을 Host로 넣는다. 그러면 백엔드 입장에서 들어온 Host가 `backend`라, 도메인으로 vhost를 구분하는 백엔드(Spring의 `@RequestMapping`에 host 조건을 걸었거나, 멀티 테넌트로 도메인을 보는 앱)가 엉뚱하게 라우팅한다. 증상은 "브라우저로는 되는데 프록시 뒤에서만 404/엉뚱한 응답"이다.

`X-Forwarded-Proto`도 비슷하게 중요하다. 프록시에서 TLS를 끝내고 백엔드에는 평문 HTTP로 넘기면, 백엔드는 자기가 HTTP로 서비스되는 줄 안다. 그래서 리다이렉트 URL을 `http://`로 만들고, 브라우저는 HTTPS 페이지에서 HTTP로 리다이렉트하다가 무한 루프나 mixed content 경고를 띄운다. `$scheme`로 원래 프로토콜을 넘겨주고, 백엔드 프레임워크에서 이 헤더를 신뢰하도록 설정해야 한다(Spring이면 `server.forward-headers-strategy=framework`).

## 타임아웃과 버퍼링

리버스 프록시의 타임아웃은 두 종류를 구분해야 한다. 프록시-백엔드 사이의 타임아웃과, 클라이언트-프록시 사이의 타임아웃이다. 504가 나는 건 거의 항상 앞쪽이다.

```nginx
location / {
    proxy_pass http://backend;

    proxy_connect_timeout 5s;    # 백엔드에 TCP 연결 맺기까지
    proxy_send_timeout    60s;   # 백엔드로 요청 본문을 다 보내기까지
    proxy_read_timeout    60s;   # 백엔드 응답을 기다리는 시간 (이게 504의 주범)
}
```

`proxy_read_timeout`은 "백엔드가 데이터를 한 글자라도 더 보내올 때까지 기다리는 최대 시간"이다. 전체 응답 시간이 아니라 침묵 시간이라는 점이 중요하다. 백엔드가 60초마다 찔끔찔끔 데이터를 보내면 타임아웃에 안 걸린다. 기본값 60초인데, 무거운 리포트 생성이나 대용량 다운로드처럼 오래 걸리는 API는 이 값을 늘려야 한다. 단, 전역으로 늘리지 말고 해당 location에만 늘린다. 전역으로 600초를 걸면 진짜로 죽은 백엔드를 붙잡고 10분을 기다린다.

버퍼링은 응답 처리 방식이다. 기본값(`proxy_buffering on`)이면 Nginx가 백엔드 응답을 먼저 버퍼에 다 받아두고 클라이언트에게 전달한다. 백엔드는 응답을 빨리 던지고 연결을 끊을 수 있어서 백엔드 워커가 느린 클라이언트에 묶이지 않는다. 대부분 이게 맞다.

문제는 SSE(Server-Sent Events)나 스트리밍 응답이다. 버퍼링이 켜져 있으면 Nginx가 응답을 모았다가 한꺼번에 주려고 해서, 실시간으로 흘려야 할 이벤트가 버퍼에 갇혀 클라이언트에 안 도착한다. 스트리밍 엔드포인트는 버퍼링을 꺼야 한다.

```nginx
location /stream {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 1h;   # 스트림은 오래 열려 있으니 타임아웃을 길게
}
```

버퍼 크기도 가끔 문제가 된다. 백엔드가 큰 헤더(긴 쿠키, 많은 Set-Cookie, 큰 JWT)를 보내면 `upstream sent too big header` 에러로 502가 난다. 이건 응답 헤더가 버퍼보다 커서 나는 거라, 헤더 버퍼를 키운다.

```nginx
proxy_buffer_size       16k;   # 첫 청크(헤더 포함) 버퍼
proxy_buffers           8 16k; # 본문 버퍼 개수와 크기
proxy_busy_buffers_size 32k;
```

## 502와 504 디버깅

리버스 프록시를 운영하면 502 Bad Gateway와 504 Gateway Timeout을 제일 자주 본다. 둘은 원인이 다르니 먼저 구분해야 한다.

504는 "백엔드가 시간 안에 응답을 안 줬다"다. 연결은 됐는데 응답이 안 온다. 502는 "백엔드한테 연결을 못 했거나, 받은 응답이 깨졌다"다. 연결 자체가 안 되거나, 백엔드가 도중에 연결을 끊거나, 응답이 HTTP로 파싱이 안 되는 경우다.

### 504가 날 때

대부분 백엔드가 느려서다. 순서대로 확인한다.

먼저 진짜 백엔드가 느린지 본다. 프록시를 건너뛰고 백엔드에 직접 요청해서 시간을 잰다.

```bash
# 프록시 뒤 백엔드에 직접 (프록시 서버에서 실행)
curl -o /dev/null -s -w 'time_total=%{time_total}\n' http://10.0.0.11:8080/slow-api
```

직접 호출도 60초를 넘으면 백엔드 문제다. 느린 쿼리, 외부 API 대기, DB 커넥션 풀 고갈 같은 걸 백엔드 쪽에서 잡아야 한다. 이때 프록시에서 `proxy_read_timeout`만 늘리는 건 증상 가리기다. 정말 오래 걸리는 게 정상인 API(리포트, 대용량 처리)라면 해당 location에만 타임아웃을 늘리는 게 맞고, 그게 아니면 백엔드를 고쳐야 한다.

Nginx 에러 로그를 보면 어느 단계에서 끊겼는지 나온다.

```bash
tail -f /var/log/nginx/error.log
# upstream timed out (110: Connection timed out) while reading response header from upstream
```

`while reading response header`면 `proxy_read_timeout`이고, `while connecting to upstream`이면 `proxy_connect_timeout`이다. 후자면 백엔드가 연결조차 늦게 받는 거라 백엔드 프로세스가 막혀 있거나 listen 백로그가 꽉 찬 상황이다.

### 502가 날 때

502는 케이스가 많다. 에러 로그 메시지로 갈래를 잡는다.

`connect() failed (111: Connection refused)`면 백엔드가 그 포트에서 안 떠 있다. 백엔드 프로세스가 죽었거나, 포트가 틀렸거나, 방화벽이 막은 거다. 백엔드 서버에서 `ss -tlnp | grep 8080`으로 진짜 떠 있는지부터 본다. 배포 중에 백엔드가 잠깐 내려가는 시점에 502가 몰리면, 무중단 배포(헬스체크 빠진 뒤 교체)가 안 된 거다.

`upstream prematurely closed connection`은 백엔드가 응답 도중에 연결을 끊었다는 거다. 백엔드 워커가 처리 중에 죽거나(OOM, 패닉), 백엔드의 keep-alive 타임아웃이 프록시보다 짧아서 프록시가 재사용하려던 연결을 백엔드가 먼저 닫은 경우다. 후자는 의외로 흔하다. Nginx가 upstream에 keepalive를 쓰는데 백엔드(예: gunicorn, puma)의 keepalive timeout이 더 짧으면, 백엔드가 닫은 연결로 프록시가 요청을 보내다 502가 난다. 백엔드의 keepalive timeout을 프록시보다 길게 잡아야 한다.

```nginx
upstream backend {
    server 10.0.0.11:8080;
    keepalive 32;   # 백엔드와 연결 재사용
}
location / {
    proxy_pass http://backend;
    proxy_http_version 1.1;       # keepalive는 1.1 필요
    proxy_set_header Connection "";  # 기본 'close' 헤더 제거
}
```

`upstream sent too big header`는 앞에서 본 헤더 버퍼 부족이다. 백엔드가 보내는 헤더가 커진 거니 `proxy_buffer_size`를 키운다. 갑자기 502가 나기 시작했고 마침 인증/세션 구조를 바꿔서 쿠키나 토큰이 커졌다면 이걸 의심한다.

`SSL_do_handshake() failed`는 백엔드와 HTTPS로 통신하는데(`proxy_pass https://...`) TLS 핸드셰이크가 깨진 거다. 백엔드 인증서 만료, SNI 불일치, 프로토콜 버전 안 맞음 등이다.

### 디버깅 순서를 정리하면

502/504가 나면 추측하지 말고 이 순서로 좁힌다.

먼저 Nginx 에러 로그를 본다. 거의 모든 답이 거기 한 줄로 적혀 있다. 추측으로 설정을 이것저것 바꾸기 전에 로그 메시지를 정확히 읽는 게 제일 빠르다.

그 다음 프록시를 빼고 백엔드에 직접 요청해 본다. 직접 호출이 정상이면 프록시 설정(헤더, 타임아웃, 버퍼) 문제고, 직접 호출도 실패하면 백엔드 문제다. 이 한 번의 비교로 범위가 절반으로 준다.

마지막으로 access 로그에서 `$upstream_addr`와 `$upstream_response_time`을 본다. 어느 백엔드로 갔고 거기서 얼마나 걸렸는지 나온다. 로그 포맷에 미리 넣어두면 장애 때 큰 도움이 된다.

```nginx
log_format upstream_log '$remote_addr - $upstream_addr '
                        'status=$status req_time=$request_time '
                        'upstream_time=$upstream_response_time '
                        '"$request"';
```

`$request_time`(클라이언트가 보낸 전체 시간)과 `$upstream_response_time`(백엔드가 쓴 시간)을 비교하면, 느린 게 백엔드인지 네트워크/클라이언트인지 갈린다. 둘이 비슷하면 백엔드가 느린 거고, `$request_time`만 크면 클라이언트가 느리게 받아간 거다(느린 회선, 모바일).

## 정리

리버스 프록시는 서버를 대신해 요청을 받고, 그 뒤에서 부하 분산·TLS 종료·백엔드 은닉을 한다. 운영하면서 손대는 건 결국 몇 가지로 좁혀진다. upstream으로 백엔드를 묶고 분산 방식을 고르는 것, 헬스체크로 죽은 백엔드를 빼는 것, XFF·Host·X-Forwarded-Proto 헤더를 제대로 넘기는 것, 타임아웃과 버퍼링을 워크로드에 맞추는 것. 그리고 502/504가 나면 에러 로그부터 읽고 프록시를 건너뛴 직접 호출로 범위를 좁히는 것. 이 흐름만 몸에 익혀도 새벽 장애의 절반은 빨리 끝난다.

관련 문서:

- [프록시 개요](Proxy.md) — 포워드/리버스 구분, XFF 위조 처리, 기본 흐름
- [포워드 프록시](Forward_Proxy.md) — 클라이언트 쪽 프록시, Squid, ACL
- [로드 밸런싱](Load_Balancing.md) — 분산 알고리즘, L4/L7, 세션 유지
