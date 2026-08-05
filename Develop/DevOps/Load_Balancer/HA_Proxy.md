---
title: HAProxy
tags:
  - infra
  - load-balancer
  - haproxy
  - keepalived
  - high-availability
updated: 2026-06-16
---

# HAProxy

## HAProxy를 쓰게 되는 상황

서비스 인스턴스가 한 대일 땐 로드밸런서가 필요 없다. 두 대로 늘리는 순간부터 "둘 중 누구한테 요청을 보낼지"를 누군가 결정해야 한다. 클라우드면 ALB/NLB 같은 매니지드 LB를 쓰면 되지만, 온프레미스거나 LB 동작을 세밀하게 제어하고 싶을 때 소프트웨어 LB를 직접 올린다. 그중 오래 검증된 게 HAProxy다.

HAProxy는 단일 바이너리에 설정 파일 하나로 동작한다. nginx도 로드밸런싱을 하지만, nginx는 본질이 웹서버라 LB는 부가 기능이다. HAProxy는 처음부터 로드밸런서/프록시 전용으로 만들어져서 health check, 큐잉, 세션 유지, stats 같은 LB에 필요한 기능이 훨씬 촘촘하다. L4(TCP) 모드도 제대로 지원해서 HTTP가 아닌 트래픽(MySQL, Redis, gRPC 스트림)도 분산한다.

처음 HAProxy를 만지면 설정 구조가 낯설다. nginx의 `server`, `location` 같은 블록과 매핑이 안 된다. frontend/backend/listen 이 세 블록 개념만 잡으면 나머지는 옵션 싸움이다.

## 설정 파일 구조

`haproxy.cfg`는 보통 네 개의 섹션으로 나뉜다.

```
global      # 프로세스 전역 설정 (워커 수, 로그, 보안)
defaults    # frontend/backend가 상속받는 기본값
frontend    # 클라이언트 요청을 받는 입구
backend     # 실제 서버 풀
```

```
global
    log /dev/log local0
    maxconn 50000
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    retries 3

frontend web_in
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/site.pem
    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 10.0.1.11:8080 check
    server web2 10.0.1.12:8080 check
    server web3 10.0.1.13:8080 check
```

`frontend`는 어디서 요청을 받을지(`bind`)와 어느 백엔드로 보낼지를 정한다. `backend`는 실제 서버 목록과 분산 방식을 정한다. 둘을 묶어서 한 블록으로 쓰는 게 `listen`이다. stats 페이지나 단순한 TCP 프록시처럼 frontend/backend를 나눌 이유가 없을 때 listen을 쓴다.

```
listen mysql_proxy
    bind *:3306
    mode tcp
    balance leastconn
    server db1 10.0.2.11:3306 check
    server db2 10.0.2.12:3306 check
```

설정에서 가장 많이 실수하는 지점은 `defaults`의 상속이다. `defaults`에 `mode http`를 박아두고 TCP backend를 하나 추가하면, 그 backend는 여전히 http 모드로 동작해서 TCP 트래픽을 깨먹는다. backend 블록 안에 `mode tcp`를 명시해서 덮어써야 한다. listen/frontend/backend는 자기 위에 가장 가까운 defaults를 상속받는데, defaults 블록을 여러 개 두고 그 사이에 섹션을 끼우면 상속 대상이 갈린다. 이걸 모르고 defaults를 파일 맨 위에 하나만 두면 모든 섹션이 같은 값을 받는다.

## L4 모드와 L7 모드

`mode tcp`는 L4, `mode http`는 L7이다. 이 차이가 HAProxy 운영에서 제일 중요한 갈림길이다.

L4(TCP) 모드는 패킷을 들여다보지 않고 연결 단위로만 분산한다. 빠르고, HTTP가 아닌 프로토콜도 처리한다. 대신 HTTP 헤더를 모르니 URL 기반 라우팅, 쿠키 기반 세션 유지, 응답 코드 기반 health check 같은 건 못 한다. TLS도 그냥 통과시킨다(passthrough). 백엔드가 TLS를 직접 처리한다.

L7(HTTP) 모드는 요청을 파싱해서 헤더, 경로, 쿠키를 본다. ACL로 경로별 라우팅을 하고, 쿠키를 심어 세션을 고정하고, `httpchk`로 응답 코드를 검사한다. TLS termination(HAProxy에서 복호화)도 여기서 한다. 대신 파싱 비용이 있고, HTTP만 처리한다.

실무 판단은 단순하다. HTTP API/웹이면 L7, 그 외(DB, 메시지 브로커, 순수 TCP 스트림)면 L4. gRPC는 HTTP/2 위에서 돌지만, HAProxy가 HTTP/2 백엔드를 제대로 다루려면 버전과 설정을 신경 써야 해서 초기엔 L4 passthrough로 깔고 가는 경우가 많다.

## 로드밸런싱 알고리즘

`balance` 지시어로 정한다. 실무에서 쓰는 건 사실상 세 개다.

`roundrobin`은 순서대로 돌린다. 백엔드 서버 성능이 균일하고 요청 처리 시간이 비슷하면 이게 기본값이다. 가중치(`weight`)를 줘서 성능 좋은 서버에 더 보낼 수 있다.

```
backend web_servers
    balance roundrobin
    server web1 10.0.1.11:8080 check weight 100
    server web2 10.0.1.12:8080 check weight 50
```

`leastconn`은 현재 활성 연결이 가장 적은 서버로 보낸다. 요청별 처리 시간이 들쭉날쭉할 때(긴 쿼리, WebSocket, DB 연결 풀) roundrobin보다 낫다. roundrobin은 무거운 요청이 한 서버에 몰려도 계속 그 서버에 보내지만, leastconn은 연결 수를 보고 피한다. DB나 long-lived 연결 백엔드엔 leastconn을 기본으로 둔다.

`source`는 클라이언트 IP를 해싱해서 같은 IP를 항상 같은 서버로 보낸다. 쿠키를 못 쓰는 환경에서 세션을 고정하는 용도다. 단점은 NAT 뒤에 있는 클라이언트들이 한 IP로 묶여서 분산이 한쪽으로 쏠린다는 거다. 그래서 세션 유지가 필요하면 source보다 cookie 방식을 먼저 검토한다.

## Health check

`check` 옵션만 붙이면 HAProxy가 해당 서버의 포트로 TCP 연결을 시도해서 살아있는지 본다. 문제는 포트가 열려 있어도 애플리케이션은 죽어 있는 경우다. 프로세스는 떠 있는데 DB 커넥션이 끊겨서 503을 뱉는 상태면 TCP check는 통과시킨다.

이걸 막으려면 L7 health check를 쓴다.

```
backend web_servers
    option httpchk GET /health
    http-check expect status 200
    server web1 10.0.1.11:8080 check inter 2s fall 3 rise 2
    server web2 10.0.1.12:8080 check inter 2s fall 3 rise 2
```

`httpchk GET /health`는 헬스 엔드포인트로 HTTP 요청을 보낸다. `http-check expect status 200`으로 200이 아니면 죽은 걸로 본다. `inter 2s`는 체크 주기, `fall 3`은 연속 3번 실패하면 down, `rise 2`는 연속 2번 성공하면 다시 up으로 올린다.

`fall`을 너무 낮게(예: 1) 잡으면 일시적인 GC 멈춤이나 네트워크 흔들림에 멀쩡한 서버가 빠진다. 너무 높게 잡으면 진짜 죽은 서버를 늦게 빼서 503이 그동안 새어 나간다. 트래픽 패턴 보면서 fall 2~3, inter 2s 근처에서 조정한다.

헬스 엔드포인트는 가볍게 만들어야 한다. `/health`가 DB, Redis, 외부 API를 전부 찔러보는 무거운 체크로 짜여 있으면, HAProxy가 2초마다 모든 서버를 두드릴 때 그게 부하가 된다. 더 위험한 건 외부 의존성 하나가 느려지면 전체 헬스 체크가 동시에 타임아웃 나면서 모든 서버가 한꺼번에 down 처리되는 상황이다. liveness(프로세스가 살아있나)와 readiness(요청 받을 준비 됐나)를 구분하고, LB가 보는 엔드포인트는 가볍게 유지한다.

## 세션 유지 (sticky session)

같은 클라이언트를 같은 백엔드로 계속 보내야 할 때가 있다. 세션을 서버 메모리에 들고 있는 레거시 앱이 대표적이다. L7 모드면 쿠키 방식이 깔끔하다.

```
backend web_servers
    balance roundrobin
    cookie SRVID insert indirect nocache
    server web1 10.0.1.11:8080 check cookie web1
    server web2 10.0.1.12:8080 check cookie web2
```

`cookie SRVID insert`는 HAProxy가 응답에 `SRVID=web1` 같은 쿠키를 심는다. 다음 요청부터 클라이언트가 그 쿠키를 보내면 해당 서버로 직행한다. `indirect`는 클라이언트가 보낸 쿠키를 백엔드로 넘기지 않고 HAProxy가 먹어버린다는 뜻이고, `nocache`는 이 응답이 캐시되지 않게 헤더를 붙인다.

sticky session은 편하지만 분산을 망친다. 한 서버에 세션이 쌓이면 그 서버만 부하가 높아지고, 그 서버가 죽으면 거기 묶인 세션이 전부 날아간다. 가능하면 세션을 Redis 같은 외부 저장소로 빼서 무상태로 만들고 sticky를 안 쓰는 방향이 맞다. 당장 못 바꾸는 레거시를 버티는 임시 수단으로 본다.

## ACL 기반 라우팅

L7 모드에서 요청 내용을 보고 백엔드를 가른다. 경로 prefix로 API와 정적 자원을 나누는 게 흔한 패턴이다.

```
frontend web_in
    bind *:80
    acl is_api      path_beg /api/
    acl is_static   path_beg /static/
    acl host_admin  hdr(host) -i admin.example.com

    use_backend api_servers    if is_api
    use_backend static_servers if is_static
    use_backend admin_servers  if host_admin
    default_backend web_servers
```

`acl`로 조건에 이름을 붙이고 `use_backend ... if`로 매칭되면 그 백엔드로 보낸다. `path_beg`는 경로 prefix, `hdr(host)`는 Host 헤더, `-i`는 대소문자 무시다. 위에서부터 순서대로 평가해서 처음 매칭되는 `use_backend`로 가고, 아무것도 안 걸리면 `default_backend`다.

ACL을 많이 쌓으면 순서 때문에 디버깅이 어려워진다. 더 구체적인 조건을 위에 두는 게 안전하고, 의도와 다르게 동작하면 `option httplog`로 어느 백엔드로 갔는지 로그를 찍어 확인한다.

## stats 페이지

HAProxy는 내장 상태 페이지를 제공한다. 각 백엔드/서버의 up/down, 현재 연결 수, 누적 요청, 에러를 한 화면에서 본다. 장애 났을 때 제일 먼저 보는 화면이다.

```
listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 5s
    stats auth admin:changeme
    stats admin if TRUE
```

`stats auth`로 기본 인증을 걸고, `stats admin if TRUE`를 주면 화면에서 서버를 수동으로 drain/disable 할 수 있다. 배포할 때 특정 서버를 미리 빼고 싶을 때 이 admin 기능이 쓸 만하다. 다만 stats 포트는 절대 외부에 노출하면 안 된다. 인증을 걸어도 내부망에만 바인딩하거나 방화벽으로 막는다.

운영 자동화엔 웹 화면 대신 Runtime API(소켓)나 Prometheus exporter를 쓴다. HAProxy 2.0 이상은 `prometheus-exporter`를 내장해서 `/metrics` 엔드포인트를 바로 뽑을 수 있다.

## timeout 튜닝

기본 defaults의 timeout이 운영 사고로 직결되는 경우가 많다. 세 개를 구분해야 한다.

`timeout connect`는 HAProxy가 백엔드 서버에 TCP 연결을 맺는 데 허용하는 시간이다. 같은 데이터센터 안이면 보통 5초면 넉넉하다. 이게 길면 죽은 서버에 연결 시도하다가 응답이 늦어진다.

`timeout client`는 클라이언트가 데이터를 보내거나 받는 사이 idle 허용 시간이다. `timeout server`는 백엔드가 응답하는 동안의 idle 허용 시간이다. 이 둘이 핵심이다.

흔한 사고는 `timeout server`를 30초로 박아뒀는데 실제로는 60초 걸리는 무거운 리포트 API가 있을 때다. HAProxy가 30초에 504를 끊어버려서 백엔드는 멀쩡히 처리 중인데 클라이언트는 504를 받는다. 이런 엔드포인트는 backend 단위로 timeout을 따로 늘린다.

```
backend report_api
    timeout server 120s
    server report1 10.0.3.11:8080 check
```

반대로 timeout을 무작정 길게 잡으면 죽은 연결이 오래 살아남아 커넥션 슬롯을 잡아먹는다. WebSocket이나 SSE 같은 long-lived 연결은 `timeout tunnel`로 따로 관리한다. 일반 HTTP는 짧게, 스트리밍은 tunnel로 길게 가른다.

타임아웃을 단위 없이 숫자만 쓰면(`timeout server 30`) 밀리초로 해석된다. `30`은 30초가 아니라 30밀리초다. 반드시 `s`, `m` 같은 단위를 붙인다. 단위를 빠뜨려서 모든 요청이 즉시 끊기는 사고가 종종 난다.

## reload 무중단 처리

설정을 바꾸고 적용할 때 `restart`를 쓰면 안 된다. 프로세스를 죽였다 띄우는 동안 들어오는 연결이 끊긴다. `reload`를 쓰면 HAProxy가 새 설정으로 새 프로세스를 띄우고, 기존 프로세스는 처리 중인 연결을 마저 끝낼 때까지 살려둔다(graceful).

systemd 환경이면 보통 이렇게 동작한다.

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg   # 먼저 문법 검사
systemctl reload haproxy
```

`-c`로 문법을 먼저 검사하는 습관이 중요하다. 잘못된 설정으로 reload 하면 새 프로세스가 못 뜨고, 운영 중인 서비스가 영향받는다. 문법 검사를 통과한 뒤에만 reload 한다.

graceful reload가 진짜 무중단이 되려면 커널 옵션도 받쳐줘야 한다. 오래된 방식에선 reload 순간 새 프로세스가 같은 포트에 bind 하는 찰나에 SYN 패킷이 떨어지는 일이 있었다. HAProxy 1.8 이상은 이걸 처리하는 메커니즘이 들어가 있지만, 트래픽이 많은 환경이면 reload 직후 짧은 에러 스파이크가 stats에 잡히는지 확인한다. 처리 중이던 long-lived 연결은 옛 프로세스에 남아 있다가, 그 연결이 다 끝나야 옛 프로세스가 죽는다. WebSocket이 잔뜩 붙어 있으면 옛 프로세스가 한참 안 죽고 메모리에 쌓이는 걸 볼 수 있다.

## Keepalived + VRRP로 이중화

여기까지는 HAProxy 한 대로 여러 백엔드를 분산하는 얘기다. 그런데 HAProxy 자신이 죽으면? 백엔드가 다 살아있어도 입구가 막혀서 전체 서비스가 내려간다. 로드밸런서가 단일 장애점(SPOF)이 된다.

HAProxy를 두 대 올리고 그 앞에 Keepalived로 VRRP를 깔아서 푼다. VRRP는 두 노드가 가상 IP(VIP) 하나를 공유하고, 평소엔 MASTER가 VIP를 들고 트래픽을 받는다. MASTER가 죽으면 BACKUP이 VIP를 가져와서 트래픽을 이어받는다. 클라이언트는 VIP만 보고 있으니 뒤에서 누가 바뀌든 모른다.

```
# keepalived.conf (MASTER 노드)
vrrp_script chk_haproxy {
    script "killall -0 haproxy"
    interval 2
    weight -20
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 110
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass secret123
    }
    virtual_ipaddress {
        10.0.0.100
    }
    track_script {
        chk_haproxy
    }
}
```

`vrrp_script`로 HAProxy 프로세스가 살아있는지 검사한다. `killall -0 haproxy`는 실제로 죽이는 게 아니라 프로세스 존재만 확인하는 트릭이다. HAProxy가 죽으면 `weight -20`만큼 priority가 깎여서 BACKUP(priority 100)보다 낮아지고, VIP가 BACKUP으로 넘어간다.

BACKUP 노드는 같은 설정에서 `state BACKUP`, `priority 100`으로 둔다. `virtual_router_id`는 두 노드가 같아야 짝이 맺어진다. 한 네트워크에 VRRP 그룹이 여러 개면 이 ID가 겹치지 않게 한다.

운영하면서 겪는 함정 두 가지가 있다. 하나는 split-brain이다. 두 노드 사이 통신이 끊기면 양쪽 다 자기가 MASTER라고 믿고 둘 다 VIP를 들어버린다. 같은 IP가 두 곳에 있으면 트래픽이 엉킨다. VRRP 통신 경로를 데이터 트래픽과 분리하고, 가능하면 이중화된 경로로 둔다.

다른 하나는 priority만 보고 chk_haproxy의 검사 방식을 대충 짜는 경우다. `killall -0`은 프로세스 존재만 본다. HAProxy 프로세스는 떠 있는데 설정이 깨져서 실제로 트래픽을 못 받는 상태면 failover가 안 일어난다. 더 정확히 하려면 VIP:포트로 실제 HTTP 요청을 던져보는 스크립트로 바꾼다.

## Nginx, Caddy와 역할 비교

세 도구 다 리버스 프록시를 한다. 그래서 "뭘 써야 하나"를 자주 묻는다.

HAProxy는 로드밸런서/프록시 전용이다. 정적 파일 서빙, 자체 웹서버 기능은 없다(없다고 봐도 된다). 대신 LB 기능이 가장 깊다. L4/L7 둘 다 제대로 하고, health check, 큐잉, 백엔드 상태 관리, stats가 촘촘하다. DB나 TCP 트래픽 분산, 대규모 트래픽 앞단 LB엔 HAProxy가 1순위다.

Nginx는 웹서버가 본진이고 리버스 프록시/LB는 부가 기능이다. 정적 파일 서빙, FastCGI(PHP), 캐싱이 강하다. 하나의 인스턴스에서 정적 자원도 주고 백엔드 프록시도 하는 구성이면 nginx가 편하다. LB 기능은 HAProxy만큼 세밀하진 않지만 웬만한 HTTP 분산엔 충분하다. L4 스트림 모듈도 있긴 하다.

Caddy는 자동 HTTPS가 본진이다. Let's Encrypt 인증서를 알아서 발급/갱신해준다. 설정 파일(Caddyfile)이 짧고 직관적이다. 소규모 서비스나 개발 환경에서 TLS를 신경 안 쓰고 빨리 띄우고 싶을 때 좋다. 대규모 LB 기능이나 세밀한 백엔드 제어는 HAProxy/Nginx에 못 미친다.

정리하면, 순수 LB가 목적이고 TCP까지 다루거나 health check를 정밀하게 제어해야 하면 HAProxy, 정적 서빙과 프록시를 한 인스턴스에서 같이 하면 Nginx, 인증서 자동화가 제일 급하고 설정을 단순하게 가져가고 싶으면 Caddy다. 실제로는 섞어 쓴다. 앞단에 HAProxy로 분산하고, 각 노드에 nginx를 두어 정적 자원과 앱 프록시를 처리하는 식이다.
