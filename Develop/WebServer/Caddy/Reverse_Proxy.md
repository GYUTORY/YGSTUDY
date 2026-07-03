---
title: Caddy reverse_proxy 디렉티브 심화
tags:
  - WebServer
  - Caddy
  - ReverseProxy
  - LoadBalancing
  - HealthCheck
  - WebSocket
updated: 2026-05-03
---

# Caddy reverse_proxy 디렉티브 심화

`reverse_proxy localhost:8080` 한 줄로 시작하지만, 운영에 들어가면 그 한 줄로는 절대 부족하다. 백엔드가 두 대 이상이 되는 순간 어떤 정책으로 분산할지 정해야 하고, 한 대가 죽으면 트래픽을 빼야 하고, 백엔드와의 연결 자체에 timeout과 keepalive를 잡아줘야 한다. 거기다 백엔드가 Node.js 스트리밍 응답을 내보내거나 WebSocket을 쓴다면 또 다른 함정이 기다린다.

이 문서는 `reverse_proxy` 디렉티브의 옵션을 운영 관점에서 정리한다. 한 번이라도 502/504를 디버깅해 본 사람이라면 익숙한 이야기가 많을 것이다.

## reverse_proxy 디렉티브의 구조

가장 단순한 형태는 한 줄짜리지만, 중괄호를 열면 그 안에 업스트림 풀, 로드밸런싱 정책, 헬스체크, transport, 헤더 처리까지 모두 들어간다.

```caddy
example.com {
    reverse_proxy backend1:8080 backend2:8080 backend3:8080 {
        lb_policy least_conn
        lb_try_duration 5s
        lb_try_interval 250ms

        health_uri /healthz
        health_interval 10s
        health_timeout 2s
        health_status 2xx

        fail_duration 30s
        max_fails 3
        unhealthy_status 5xx
        unhealthy_latency 10s

        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_down -Server

        transport http {
            dial_timeout 3s
            response_header_timeout 30s
            keepalive 60s
            keepalive_idle_conns 100
        }
    }
}
```

이 블록 하나만 제대로 이해하면 운영에서 마주치는 대부분의 reverse proxy 이슈를 풀 수 있다. 하나씩 뜯어본다.

## 업스트림 여러 개와 로드밸런싱 정책

`reverse_proxy backend1 backend2 backend3`처럼 공백으로 나열하면 업스트림 풀이 된다. 기본 정책은 `random`이다. 명시하지 않으면 매 요청이 무작위로 한 대를 고른다는 뜻인데, 이게 의외로 많은 운영 이슈의 시작이다. 부하가 균등해 보이지만 짧은 구간에서는 한 대에 몰릴 수도 있고, sticky session이 필요한 경우엔 완전히 망가진다.

`lb_policy`로 명시하는 정책은 다음과 같다.

### round_robin

가장 기본적인 라운드 로빈이다. 백엔드를 순환하면서 한 번씩 돌린다. 백엔드 인스턴스의 처리 능력이 비슷하고 요청 무게가 균등할 때 잘 동작한다.

```caddy
reverse_proxy app1:8080 app2:8080 app3:8080 {
    lb_policy round_robin
}
```

문제는 처리 시간이 들쭉날쭉한 워크로드에서 균형이 깨진다는 점이다. app1이 무거운 요청을 처리 중인데도 다음 차례가 오면 또 보내버린다. 동기 응답이 빠른 단순 API라면 충분하지만, 응답 시간 편차가 큰 서비스라면 다음 정책을 봐야 한다.

### least_conn

현재 활성 연결이 가장 적은 백엔드로 보낸다. Caddy가 각 업스트림으로 나가는 in-flight 요청 수를 카운트하고 있다가 가장 한가한 곳을 고른다.

```caddy
reverse_proxy app1:8080 app2:8080 app3:8080 {
    lb_policy least_conn
}
```

응답 시간이 들쭉날쭉한 서비스에서 round_robin보다 훨씬 안정적이다. 무거운 요청을 처리 중인 백엔드에는 자연스럽게 새 요청이 덜 들어간다. 단, 요청을 받은 직후의 카운터 증가에 약간의 race가 있을 수 있어서 동시에 여러 요청이 같은 백엔드로 몰릴 수 있다는 점은 알고 있어야 한다. 실무적으론 큰 문제는 안 되지만 트래픽이 몰리는 burst 상황에서 미세한 불균형이 보인다.

### ip_hash

클라이언트 IP를 해시해서 같은 IP는 항상 같은 백엔드로 보낸다. sticky session이 필요한 레거시 앱에서 쓴다.

```caddy
reverse_proxy app1:8080 app2:8080 app3:8080 {
    lb_policy ip_hash
}
```

NAT 뒤에 있는 사용자들이 모두 같은 IP로 보이면 한 백엔드에 몰릴 수 있다. CDN이나 로드밸런서를 앞단에 두면 X-Forwarded-For를 봐야 하는데, ip_hash는 TCP 단의 remote IP를 본다는 점을 주의해야 한다. 앞단에 프록시가 있으면 모든 요청이 같은 IP(앞단 프록시 IP)로 들어와서 ip_hash가 무력화된다.

세션 sticky가 정말 필요한 경우라면 ip_hash보다 `cookie` 정책이 더 안전하다. Caddy는 `lb_policy cookie [<name>] [<fallback>]` 형태도 지원한다.

```caddy
reverse_proxy app1:8080 app2:8080 {
    lb_policy cookie lb least_conn
}
```

이렇게 쓰면 첫 요청에서 fallback 정책으로 백엔드를 고르고 `lb` 쿠키를 심은 다음, 그 이후 요청부터는 쿠키 값으로 같은 백엔드를 유지한다. NAT 환경에서도 안정적이다.

### random

기본값이다. 매번 무작위로 고른다. 정책을 고민하기 싫을 때 쓰지만, 운영에서는 명시적으로 round_robin이나 least_conn으로 바꾸는 게 낫다. 무엇이 동작하고 있는지 명확해진다.

가중치 기반 분산은 `random_choose <N>`으로 N개를 뽑아서 그중 가장 한가한 걸 고르는 식의 변형이 있다. 백엔드가 많을 때(수십 대 이상) 모든 후보를 다 비교하지 않아도 되니까 least_conn보다 가벼우면서 random보다 균등하다.

## active health check

`health_uri`를 지정하면 Caddy가 주기적으로 백엔드에 GET 요청을 보내서 살아있는지 확인한다. 죽은 걸로 판정된 업스트림은 LB 풀에서 자동으로 빠진다.

```caddy
reverse_proxy app1:8080 app2:8080 {
    health_uri /healthz
    health_interval 10s
    health_timeout 2s
    health_status 2xx
    health_body "ok"
}
```

각 옵션의 의미를 짚어본다.

- `health_uri`: 헬스체크용 경로. 보통 `/healthz`나 `/health`를 쓰는데, 이 엔드포인트는 인증 없이 200을 빠르게 반환해야 한다. DB 연결 체크 같은 무거운 검사를 넣으면 헬스체크 자체가 백엔드를 쥐어짠다.
- `health_interval`: 체크 주기. 너무 짧으면 백엔드 로그가 헬스체크로 도배된다. 10~30초 사이가 무난하다.
- `health_timeout`: 한 번의 체크 응답 대기 시간. 이 시간 안에 응답이 없으면 실패로 간주된다.
- `health_status`: 성공으로 인정할 응답 코드. `2xx`처럼 패턴으로 쓸 수 있다.
- `health_body`: 응답 본문에 특정 문자열이 있어야 성공으로 인정. 정규식도 된다.

active 체크는 백엔드를 미리 빼는 데 유용하지만, 체크 자체가 백엔드에 부하를 준다. 백엔드 수가 많거나 헬스체크 비용이 비싸다면 interval을 길게 잡고 passive 체크를 같이 쓰는 게 낫다.

한 가지 함정. health_uri가 `/healthz`인데 백엔드가 인증 미들웨어로 모든 요청을 막고 있으면 헬스체크가 401/403을 받고 모든 백엔드가 unhealthy로 빠진다. 그러면 502가 나오기 시작한다. 백엔드 코드에서 헬스체크 경로는 인증 미들웨어 위쪽에 두거나 화이트리스트에 넣어야 한다.

## passive health check

passive는 실제 트래픽 응답을 보고 판정한다. active처럼 별도 체크 요청을 보내지 않고, 정상 요청에 대한 응답이 안 좋으면 그 백엔드를 빼버린다.

```caddy
reverse_proxy app1:8080 app2:8080 {
    fail_duration 30s
    max_fails 3
    unhealthy_status 5xx
    unhealthy_latency 10s
    unhealthy_request_count 100
}
```

핵심은 `fail_duration`과 `max_fails`의 조합이다.

- `fail_duration`: 실패 카운트가 살아있는 시간. 30초로 잡으면 30초 슬라이딩 윈도우 안의 실패만 누적된다.
- `max_fails`: 윈도우 안에서 이 횟수만큼 실패하면 백엔드를 빼버린다.

위 설정은 30초 윈도우 안에 5xx 응답이 3번 나오면 그 백엔드를 unhealthy로 마킹한다는 뜻이다. unhealthy로 마킹된 후 얼마나 오래 빼두는지는 별도 옵션이 없고, fail_duration이 지나서 카운트가 자연스럽게 0이 되면 다시 후보에 들어간다. 즉 fail_duration은 "실패 카운트의 수명"이자 "복구까지의 최소 시간"이기도 하다.

`unhealthy_latency`는 응답이 이 시간 이상 걸리면 실패로 간주한다. 백엔드가 죽지는 않았지만 느려진 상황을 잡아낸다. `unhealthy_request_count`는 동시 진행 요청이 이 수를 넘으면 unhealthy로 보는 옵션이다. 큐가 쌓이는 백엔드를 일찍 빼는 데 쓴다.

passive는 active와 달리 트래픽이 흐르지 않으면 판정이 안 된다는 한계가 있다. 새벽에 트래픽이 거의 없는 서비스라면 active 체크를 같이 켜둬야 한다. 둘은 배타적이지 않고 같이 쓰는 게 정석이다.

## lb_try_duration으로 retry 제어

업스트림 한 대가 실패했을 때 다른 업스트림으로 재시도하는 동작을 제어하는 옵션이다.

```caddy
reverse_proxy app1:8080 app2:8080 app3:8080 {
    lb_try_duration 5s
    lb_try_interval 250ms
    lb_retries 3
}
```

- `lb_try_duration`: 클라이언트 요청 한 건에 대해 LB가 retry를 계속 시도하는 최대 시간. 0이면 retry 없음. 5s로 잡으면 5초 동안 다른 백엔드를 돌면서 재시도한다.
- `lb_try_interval`: retry 사이의 간격. 250ms 정도면 충분하다. 너무 짧으면 백엔드가 회복할 틈이 없다.
- `lb_retries`: 최대 재시도 횟수. duration과 함께 조건으로 동작한다.

retry는 양날의 칼이다. 일시적인 네트워크 끊김에는 좋지만, 백엔드가 진짜로 망가져서 모든 업스트림이 같은 에러를 내는 상황에서는 클라이언트 응답을 5초씩 늦추면서 백엔드에 부하만 가중시킨다. retry 조건을 좁히려면 매처를 같이 쓴다.

```caddy
reverse_proxy app1:8080 app2:8080 {
    lb_try_duration 3s
    lb_try_interval 250ms

    @5xx status 5xx
    handle_response @5xx {
        # 5xx면 다음 백엔드로
    }
}
```

또 한 가지 중요한 점. `lb_try_duration`이 동작하려면 요청 본문이 buffering 되거나 GET처럼 본문이 없어야 한다. POST/PUT 요청은 본문이 한 번 백엔드로 흘러가면 stream이 소진되어 다음 백엔드로 다시 보낼 수 없다. Caddy는 retry가 가능한 요청에 대해서만 자동으로 retry 한다. POST 요청 retry가 동작하지 않는 것 같다고 의심된다면 이게 원인일 가능성이 크다.

## transport 블록으로 백엔드 연결 제어

`transport http { ... }` 블록은 Caddy가 백엔드와 맺는 HTTP 연결의 세부를 잡는다. 운영에서 가장 자주 만지는 블록이다.

```caddy
reverse_proxy backend:8080 {
    transport http {
        dial_timeout 3s
        dial_fallback_delay 300ms
        response_header_timeout 30s
        read_timeout 60s
        write_timeout 60s
        keepalive 60s
        keepalive_idle_conns 100
        keepalive_idle_conns_per_host 10
        compression off
        versions h2c 2
    }
}
```

각 옵션의 실무적 의미.

- `dial_timeout`: TCP 연결 수립 대기 시간. 백엔드가 같은 데이터센터라면 1~3초로 충분하다. 외부 API를 프록시한다면 5초 정도로 늘린다.
- `response_header_timeout`: 백엔드가 응답 헤더를 다 보낼 때까지의 시간. 본문 timeout이 아니라 헤더만이다. 긴 처리가 필요한 API라면 이 값을 늘려야 504가 안 난다.
- `read_timeout`/`write_timeout`: 백엔드와의 read/write 단위 timeout. 스트리밍 응답을 받는다면 이 값을 길게 잡거나 0(무제한)으로 둬야 한다.
- `keepalive`: idle 커넥션 유지 시간. 60초가 보통이다. 백엔드의 keepalive 설정과 맞춰야 한다. 백엔드가 30초에 끊는데 Caddy는 60초까지 들고 있으면 끊긴 커넥션을 재사용하다 502가 난다.
- `keepalive_idle_conns_per_host`: 호스트당 유지하는 idle 커넥션 수. 트래픽이 많은데 이 값이 작으면 매번 새 연결을 만드느라 latency가 튄다.

### HTTP/2 백엔드 연결

백엔드가 HTTP/2를 지원하면 `versions h2c 2`로 명시할 수 있다. `h2c`는 평문 HTTP/2, `2`는 TLS 위의 HTTP/2다.

```caddy
reverse_proxy https://backend:8443 {
    transport http {
        versions 2
        tls
    }
}
```

gRPC 백엔드를 프록시한다면 HTTP/2가 거의 필수다. gRPC는 HTTP/2의 trailer와 streaming에 의존하기 때문에 HTTP/1.1로는 동작하지 않는다.

### 백엔드 HTTPS 연결

업스트림 주소를 `https://`로 시작하면 자동으로 TLS가 켜진다. 또는 명시적으로 `tls` 서브디렉티브를 쓴다.

```caddy
reverse_proxy https://internal-api.example.com {
    transport http {
        tls
        tls_server_name internal-api.example.com
        tls_trusted_ca_certs /etc/ssl/internal-ca.pem
    }
}
```

`tls_server_name`은 SNI에 들어갈 호스트명이다. IP로 연결하지만 인증서는 도메인명으로 검증해야 할 때 쓴다. `tls_trusted_ca_certs`는 사내 CA로 발급받은 인증서를 검증하기 위한 root CA 번들 경로다.

### tls_insecure_skip_verify의 함정

백엔드가 self-signed 인증서를 쓰는 경우 일단 동작시키려고 `tls_insecure_skip_verify`를 켜는 경우가 많다.

```caddy
reverse_proxy https://internal:8443 {
    transport http {
        tls_insecure_skip_verify
    }
}
```

이건 운영 환경에서 절대 그대로 두면 안 되는 옵션이다. 인증서 검증을 통째로 끈다는 뜻이라 MITM 공격에 그대로 노출된다. 같은 호스트에서 백엔드와 통신한다 해도, 컨테이너 환경에서 네트워크 정책이 잘못 설정되면 다른 컨테이너가 백엔드 IP를 가로챌 수 있다.

올바른 방법은 다음 중 하나다.

1. 사내 CA를 만들어서 백엔드 인증서를 거기서 발급하고, Caddy에 `tls_trusted_ca_certs`로 CA 번들을 등록한다.
2. 사내 도메인에 대해 Caddy에서 자동 발급받은 인증서를 사용하고 백엔드를 그 도메인으로 호출한다.
3. 백엔드와의 통신을 평문 HTTP로 하되 네트워크 단(VPC, 서비스 메시)에서 암호화한다.

급하게 데모 띄우거나 로컬 개발에서만 `tls_insecure_skip_verify`를 켜고, 운영 배포 직전에 반드시 제거해야 한다. 한번 켜두면 잊혀져서 한참 후에 보안 감사에서 발견되는 패턴이 정말 많다.

## header_up과 header_down

`header_up`은 Caddy가 백엔드로 보낼 요청에 헤더를 추가/수정한다. `header_down`은 백엔드가 응답한 헤더를 클라이언트로 보내기 전에 손본다.

```caddy
reverse_proxy backend:8080 {
    header_up X-Real-IP {remote_host}
    header_up X-Forwarded-For {remote_host}
    header_up X-Forwarded-Proto {scheme}
    header_up X-Forwarded-Host {host}
    header_up Host {upstream_hostport}

    header_down -Server
    header_down -X-Powered-By
    header_down Strict-Transport-Security "max-age=31536000"
}
```

### X-Forwarded-* 헤더의 자동 처리

사실 Caddy는 기본적으로 `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`를 자동으로 추가한다. 그래서 위 예제에서 `header_up X-Forwarded-*`는 명시적인 재선언이다. 기본 동작을 알고 있으면 굳이 적을 필요는 없다.

다만 한 가지 주의할 점이 있다. Caddy는 클라이언트가 이미 `X-Forwarded-For`를 보낸 경우 그것을 신뢰하고 그 뒤에 자기가 본 IP를 append 한다. CDN 같은 신뢰할 수 있는 앞단을 거쳤다면 이게 맞지만, 인터넷에서 직접 들어오는 트래픽이라면 클라이언트가 보낸 X-Forwarded-For는 위조 가능하다. 백엔드에서 진짜 클라이언트 IP가 필요하다면 다음처럼 명시적으로 덮어쓴다.

```caddy
header_up X-Forwarded-For {remote_host}
```

이렇게 하면 Caddy 입장에서 본 직접 클라이언트 IP만 들어간다. 클라이언트가 보낸 헤더는 무시된다.

`X-Real-IP`는 Caddy가 자동으로 넣어주지 않는다. 백엔드 코드가 `X-Real-IP`를 본다면(많은 Node.js, Python 프레임워크가 그렇다) 명시적으로 넣어줘야 한다.

### Host 헤더 처리

기본적으로 Caddy는 클라이언트가 보낸 Host 헤더를 그대로 백엔드로 전달한다. `example.com`으로 들어온 요청은 백엔드도 `Host: example.com`을 받는다. 이게 문제가 되는 경우는 백엔드가 Host 기반으로 라우팅하는데 외부 도메인과 내부 도메인이 다를 때다.

```caddy
reverse_proxy https://internal-api.cloud.example.com {
    header_up Host {upstream_hostport}
    transport http {
        tls
    }
}
```

`{upstream_hostport}`는 현재 선택된 업스트림의 호스트:포트다. 이렇게 하면 Host가 `internal-api.cloud.example.com`으로 백엔드에 전달된다. SaaS의 내부 API를 프록시할 때 자주 쓴다.

반대로 백엔드 라우터에서 Host에 따라 가상호스트를 분기한다면 클라이언트의 Host를 그대로 두는 게 맞다. 케이스마다 다르므로 백엔드가 Host를 어떻게 보는지 먼저 확인해야 한다.

### 응답 헤더 정리

`header_down -Server`로 백엔드가 노출한 `Server` 헤더를 제거한다. `Server: nginx/1.21.4` 같은 정보를 외부에 노출하지 않는 게 보안상 낫다. Caddy 자신도 `Server: Caddy` 헤더를 붙이는데, 이것도 같은 방식으로 제거할 수 있다.

```caddy
header_down -Server
```

## WebSocket과 streaming 응답

`reverse_proxy`는 WebSocket을 자동으로 처리한다. Upgrade 헤더를 보고 알아서 raw TCP로 전환하기 때문에 별도 설정이 필요 없다.

```caddy
ws.example.com {
    reverse_proxy localhost:6001
}
```

문제는 streaming 응답이다. SSE(Server-Sent Events), 청크 응답, 긴 polling 같은 케이스에서 Caddy가 응답을 버퍼링하면 클라이언트가 데이터를 늦게 받게 된다. 기본 동작에서 Caddy는 백엔드 응답을 일정 시간/크기 단위로 버퍼링한 다음 클라이언트로 내보낸다. 일반 API에서는 이게 더 효율적이지만 스트리밍에서는 치명적이다.

해결은 `flush_interval`이다.

```caddy
sse.example.com {
    reverse_proxy localhost:8080 {
        flush_interval -1
    }
}
```

`flush_interval -1`은 받자마자 즉시 flush 하라는 뜻이다. 양수 값(예: `100ms`)을 주면 그 간격으로 flush 한다. SSE나 Server Push가 필요하면 `-1`로 두는 게 정석이다.

WebSocket도 사실 `flush_interval`을 명시적으로 켜주는 게 안전하다. Caddy가 내부적으로 처리하긴 하지만 일부 클라이언트에서 메시지가 묶여서 도착하는 현상이 보고된 적이 있다.

```caddy
@websocket {
    header Connection *Upgrade*
    header Upgrade websocket
}
handle @websocket {
    reverse_proxy localhost:6001 {
        flush_interval -1
    }
}

handle {
    reverse_proxy localhost:8080
}
```

WebSocket을 분기해서 처리할 때는 timeout도 같이 손본다. WebSocket 연결은 분 단위, 시간 단위로 살아있는데 transport의 read/write timeout이 짧으면 중간에 끊긴다.

```caddy
@websocket {
    header Connection *Upgrade*
    header Upgrade websocket
}
handle @websocket {
    reverse_proxy localhost:6001 {
        flush_interval -1
        transport http {
            read_timeout 0
            write_timeout 0
        }
    }
}
```

`read_timeout 0`과 `write_timeout 0`은 무제한이다. WebSocket용 라우트에만 적용하고, 일반 HTTP 라우트는 분리해서 timeout을 살려둬야 좀비 연결을 자동으로 정리할 수 있다.

## 실전 조합 예제

지금까지의 옵션을 조합한 실제 운영용 설정 예시다. 백엔드 3대를 least_conn으로 분산하고, active+passive 헬스체크를 같이 켜고, retry는 짧게 잡고, 백엔드는 self-signed가 아닌 사내 CA로 발급받은 인증서를 검증한다.

```caddy
api.example.com {
    reverse_proxy https://app1:8443 https://app2:8443 https://app3:8443 {
        lb_policy least_conn
        lb_try_duration 3s
        lb_try_interval 250ms

        health_uri /healthz
        health_interval 15s
        health_timeout 2s
        health_status 200

        fail_duration 30s
        max_fails 3
        unhealthy_status 5xx
        unhealthy_latency 8s

        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Request-ID {http.request.uuid}
        header_down -Server
        header_down -X-Powered-By

        transport http {
            tls
            tls_trusted_ca_certs /etc/ssl/internal-ca.pem
            dial_timeout 2s
            response_header_timeout 30s
            keepalive 60s
            keepalive_idle_conns_per_host 20
            versions 2
        }
    }
}

stream.example.com {
    @sse path /events*
    handle @sse {
        reverse_proxy localhost:8080 {
            flush_interval -1
            transport http {
                read_timeout 0
                response_header_timeout 5s
            }
        }
    }

    @ws {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    handle @ws {
        reverse_proxy localhost:6001 {
            flush_interval -1
            transport http {
                read_timeout 0
                write_timeout 0
            }
        }
    }

    handle {
        reverse_proxy localhost:8080
    }
}
```

이 정도면 운영 환경에서 reverse proxy로 마주치는 기본적인 시나리오는 거의 커버된다. 502/504가 나기 시작하면 위 옵션들을 하나씩 의심하면서 조정하면 된다. 먼저 의심해야 할 것은 keepalive 불일치, response_header_timeout 부족, 헬스체크 경로의 인증 미들웨어, 그리고 streaming 응답의 flush_interval 누락 순이다.
