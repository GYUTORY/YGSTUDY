---
title: Nginx Stream 모듈
tags: [Nginx, Stream, TCP, UDP, L4, Proxy, Load-Balancing, SSL, TLS]
updated: 2026-07-27
---

# Nginx Stream 모듈

Nginx는 기본적으로 HTTP(L7) 프록시지만, `ngx_stream_core_module`을 쓰면 TCP/UDP 레벨(L4)에서도 프록시할 수 있다. MySQL, Redis, PostgreSQL처럼 HTTP를 쓰지 않는 프로토콜을 Nginx 뒤에 두고 싶을 때 쓴다.

## stream 모듈 활성화

패키지 설치 방식에 따라 모듈이 정적으로 내장되거나 동적으로 로드해야 한다.

Nginx를 직접 컴파일했거나 동적 모듈로 제공되는 경우에는 `nginx.conf` 최상단에 `load_module`을 넣어야 한다.

```nginx
# nginx.conf 최상단 (events, http 블록보다 위)
load_module modules/ngx_stream_module.so;
```

Ubuntu의 `nginx-extras` 패키지나 공식 Nginx Plus는 stream 모듈이 이미 내장되어 있어 `load_module` 없이 바로 `stream {}` 블록을 쓸 수 있다. 어느 쪽인지 확인하려면:

```bash
nginx -V 2>&1 | grep -o with-stream
# 출력되면 정적 내장, 없으면 동적 모듈 확인 필요

ls /usr/lib/nginx/modules/ | grep stream
```

`load_module`을 중복으로 넣으면 `nginx -t`에서 오류가 난다. 이미 내장된 상태에서 `.so`를 다시 로드하려 할 때 흔히 발생한다.

## stream 블록 구조

`stream {}` 블록은 `http {}` 블록과 완전히 별개다. 같은 레벨에 나란히 위치한다.

```nginx
# nginx.conf

events {
    worker_connections 1024;
}

http {
    # 일반 HTTP 설정
}

stream {
    upstream mysql_backend {
        server 10.0.0.1:3306;
        server 10.0.0.2:3306;
    }

    server {
        listen 3306;
        proxy_pass mysql_backend;
    }
}
```

## TCP 프록시 실전 설정

### MySQL 프록시

MySQL은 TCP 기반이라 stream 모듈로 바로 프록시된다. 단, SSL/TLS 핸드셰이크나 MySQL 프로토콜 파싱은 하지 않는다. 순수 L4 포워딩이다.

```nginx
stream {
    upstream mysql_cluster {
        server db1.internal:3306 weight=1;
        server db2.internal:3306 weight=1;
    }

    server {
        listen 3306;
        proxy_pass mysql_cluster;
        proxy_connect_timeout 3s;
        proxy_timeout 30s;
    }
}
```

`proxy_timeout`은 업스트림과의 연결에서 데이터가 오가지 않는 시간이 이 값을 넘으면 연결을 끊는다. MySQL 쿼리가 오래 걸리는 경우 기본값(10분)이 짧게 느껴질 수 있어 늘려두는 경우가 많다.

### Redis 프록시

Redis Sentinel이나 Cluster 앞에 Nginx stream을 두는 경우가 있다. 단순 TCP 포워딩이므로 Redis 명령 라우팅은 Nginx가 알 수 없다. Cluster 모드에서는 `MOVED`, `ASK` 리다이렉션을 클라이언트가 처리해야 한다.

```nginx
stream {
    upstream redis_nodes {
        server redis1.internal:6379;
        server redis2.internal:6379;
        server redis3.internal:6379;
    }

    server {
        listen 6379;
        proxy_pass redis_nodes;
        proxy_connect_timeout 1s;
        proxy_timeout 600s;
    }
}
```

### PostgreSQL 프록시

PostgreSQL도 TCP이므로 동일하게 쓴다. 단 PostgreSQL에는 `pgbouncer` 같은 전용 커넥션 풀러가 있어 실무에서 Nginx로 PostgreSQL을 직접 프록시하는 경우는 많지 않다.

```nginx
stream {
    upstream pg_primary {
        server pg1.internal:5432;
    }

    upstream pg_replica {
        server pg2.internal:5432;
        server pg3.internal:5432;
    }

    server {
        listen 5432;
        proxy_pass pg_primary;
    }

    server {
        listen 5433;
        proxy_pass pg_replica;
    }
}
```

## UDP 프록시

UDP는 `listen` 지시어에 `udp` 키워드를 붙인다.

```nginx
stream {
    upstream dns_servers {
        server 8.8.8.8:53;
        server 1.1.1.1:53;
    }

    server {
        listen 53 udp;
        proxy_pass dns_servers;
        proxy_responses 1;  # UDP 응답 개수 (DNS는 요청 1개당 응답 1개)
        proxy_timeout 5s;
    }
}
```

`proxy_responses`는 UDP 전용 지시어다. 업스트림에서 몇 개의 데이터그램을 받아야 클라이언트에 전달할지 결정한다. DNS는 1로 고정하면 되고, 스트리밍 프로토콜처럼 연속적인 UDP 패킷을 보내는 경우엔 설정하지 않는다.

## 로드밸런싱 방식

stream upstream도 http upstream과 동일한 방식을 지원한다.

```nginx
stream {
    # Round Robin (기본값)
    upstream rr_backend {
        server app1.internal:3306;
        server app2.internal:3306;
    }

    # least_conn: 현재 연결 수가 가장 적은 서버로 보낸다
    upstream lc_backend {
        least_conn;
        server app1.internal:3306;
        server app2.internal:3306;
    }

    # hash: 클라이언트 IP 기반 고정 라우팅
    upstream hash_backend {
        hash $remote_addr consistent;
        server app1.internal:3306;
        server app2.internal:3306;
    }
}
```

`hash $remote_addr consistent`는 클라이언트 IP가 같으면 항상 같은 업스트림으로 보낸다. 세션 상태가 있는 DB나 캐시 서버에서 sticky session이 필요할 때 쓴다.

## 헬스체크

오픈소스 Nginx의 stream 헬스체크는 소극적(passive)으로만 동작한다. 업스트림 서버에 연결이 실패했을 때 일시적으로 제외하는 방식이다.

```nginx
stream {
    upstream mysql_cluster {
        server db1.internal:3306 max_fails=3 fail_timeout=30s;
        server db2.internal:3306 max_fails=3 fail_timeout=30s;
        server db3.internal:3306 backup;
    }

    server {
        listen 3306;
        proxy_pass mysql_cluster;
        proxy_connect_timeout 2s;
    }
}
```

`max_fails=3 fail_timeout=30s`는 30초 안에 연결 실패가 3회 발생하면 해당 서버를 30초 동안 제외한다는 의미다. 30초가 지나면 다시 시도한다.

능동(active) 헬스체크는 Nginx Plus에서만 지원한다. 오픈소스에서 TCP 포트 상태를 주기적으로 확인하려면 별도 도구(Consul, HAProxy healthcheck, keepalived 등)를 써야 한다.

## SSL/TLS 종료

`ssl_preread`는 TLS를 종료하지 않고 SNI만 읽는다. stream에서 TLS를 직접 종료하려면 `listen`에 `ssl` 파라미터를 붙이고 인증서를 지정해야 한다.

```nginx
stream {
    server {
        listen 443 ssl;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;

        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        ssl_session_cache   shared:SSL_STREAM:10m;
        ssl_session_timeout 10m;

        proxy_pass mysql_backend;
    }
}
```

`ssl_session_cache`의 zone 이름(`SSL_STREAM`)은 `http {}` 블록의 ssl_session_cache와 겹치지 않게 따로 써야 한다. 같은 이름을 쓰면 Nginx가 시작은 되지만 세션 캐시가 오염된다.

클라이언트 → Nginx 구간만 TLS를 종료하고, Nginx → 백엔드는 일반 TCP로 보내는 구성이다. 백엔드까지 암호화가 필요하면 `proxy_ssl on`을 추가한다.

```nginx
stream {
    server {
        listen 443 ssl;

        ssl_certificate     /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;

        # 백엔드 연결도 TLS
        proxy_ssl                     on;
        proxy_ssl_certificate         /etc/nginx/ssl/client.crt;
        proxy_ssl_certificate_key     /etc/nginx/ssl/client.key;
        proxy_ssl_verify              on;
        proxy_ssl_trusted_certificate /etc/nginx/ssl/ca.crt;

        proxy_pass backend_cluster;
    }
}
```

## HTTP 모듈과 혼용 시 포트 충돌

`stream {}` 블록과 `http {}` 블록에서 같은 포트를 listen하면 Nginx 시작 시 오류가 난다.

```
nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
```

아래처럼 HTTP 블록에서 80을 쓰고 stream 블록에서도 80을 쓰면 충돌한다.

```nginx
# 잘못된 예
http {
    server {
        listen 80;
    }
}

stream {
    server {
        listen 80;  # 충돌
    }
}
```

HTTP와 stream을 같은 포트에서 받고 싶다면 포트를 분리하는 수밖에 없다. TCP 프록시와 HTTP를 구분하는 프로토콜 감지(`ssl_preread`, SNI 기반 라우팅)를 쓰는 방법도 있다.

### ssl_preread를 이용한 프로토콜 분기

TLS를 쓰는 경우 SNI를 읽어서 HTTP 서버와 TCP 서버로 나눌 수 있다.

```nginx
stream {
    map $ssl_preread_server_name $upstream {
        api.example.com     http_backend;
        db.example.com      mysql_backend;
        default             http_backend;
    }

    upstream http_backend {
        server 127.0.0.1:8080;
    }

    upstream mysql_backend {
        server 10.0.0.1:3306;
    }

    server {
        listen 443;
        ssl_preread on;
        proxy_pass $upstream;
        proxy_protocol on;
    }
}
```

`ssl_preread on`은 TLS 핸드셰이크를 완료하기 전에 SNI만 읽어낸다. 실제 TLS 종료는 백엔드 서버가 한다. Nginx가 TLS를 종료하고 싶다면 `ssl_preread`가 아닌 `ssl` 모듈을 써야 한다.

## preread 버퍼 튜닝

stream 모듈은 연결 초반에 클라이언트 데이터를 일부 읽어 라우팅 결정에 쓸 수 있다. `ssl_preread`가 동작할 때 이 버퍼가 사용된다.

```nginx
stream {
    server {
        listen 443;
        ssl_preread on;

        preread_buffer_size 16k;  # 기본값: 16k
        preread_timeout     30s;  # 기본값: 30s

        proxy_pass $upstream;
    }
}
```

`preread_buffer_size`는 SNI를 읽기 위해 Nginx가 미리 읽을 수 있는 최대 크기다. TLS ClientHello 메시지는 보통 수백 바이트라 기본값 16k로 충분하다. 맞춤 프로토콜에서 preread를 쓴다면 프로토콜 헤더 크기에 맞춰야 한다.

`preread_timeout`은 preread 단계에서 데이터를 기다리는 최대 시간이다. 이 시간 안에 클라이언트가 데이터를 보내지 않으면 연결을 끊는다. 포트 스캐너나 죽은 클라이언트를 걸러낼 때 짧게 설정하는 경우가 있다.

## stream 전용 변수

stream 컨텍스트에서는 HTTP 변수(`$request`, `$http_*`)를 쓸 수 없다. 쓸 수 있는 변수가 다르다.

| 변수 | 설명 |
|------|------|
| `$bytes_sent` | 클라이언트로 전송한 바이트 수 |
| `$bytes_received` | 클라이언트에서 받은 바이트 수 |
| `$session_time` | 세션 지속 시간 (초, 밀리초 포함) |
| `$protocol` | 프로토콜 (TCP 또는 UDP) |
| `$status` | 세션 종료 상태 코드 |
| `$upstream_addr` | 선택된 업스트림 서버 주소 |
| `$upstream_bytes_sent` | 업스트림으로 전송한 바이트 수 |
| `$upstream_bytes_received` | 업스트림에서 받은 바이트 수 |
| `$upstream_connect_time` | 업스트림 연결에 걸린 시간 |
| `$upstream_session_time` | 업스트림 세션 지속 시간 |
| `$ssl_preread_server_name` | SNI로 추출한 서버 이름 |
| `$ssl_preread_protocol` | 클라이언트가 보낸 최상위 TLS 버전 |
| `$remote_addr` | 클라이언트 IP |
| `$remote_port` | 클라이언트 포트 |
| `$server_addr` | Nginx 서버 주소 |
| `$server_port` | Nginx listen 포트 |
| `$time_local` | 요청 처리 시간 (로컬 시간) |

`$status`는 HTTP 상태코드와 다르다. TCP 세션이 정상 종료되면 200, 업스트림 연결 실패는 502, `proxy_timeout`으로 끊어지면 408이 들어온다.

## 대역폭 제한

특정 스트림의 트래픽 속도를 제한할 때 `proxy_download_rate`와 `proxy_upload_rate`를 쓴다.

```nginx
stream {
    server {
        listen 8080;
        proxy_pass backend;

        # 클라이언트 → Nginx 방향 속도 제한 (업로드)
        proxy_upload_rate   1m;  # 1MB/s

        # Nginx → 클라이언트 방향 속도 제한 (다운로드)
        proxy_download_rate 5m;  # 5MB/s
    }
}
```

방향 기준은 클라이언트 관점이다. `proxy_upload_rate`는 클라이언트가 Nginx로 보내는 속도를 제한하고, `proxy_download_rate`는 클라이언트가 받는 속도를 제한한다. `0`은 제한 없음이며 기본값이다.

## 연결 수 제한

`limit_conn`으로 IP당 동시 연결 수를 제한한다. `http {}` 블록과 설정 방법이 같다.

```nginx
stream {
    limit_conn_zone $remote_addr zone=conn_limit:10m;

    server {
        listen 3306;
        proxy_pass mysql_backend;

        limit_conn conn_limit 10;  # IP당 최대 10개 동시 연결
    }
}
```

연결 수 초과 시 연결이 거부된다. `limit_conn_log_level`로 로그 레벨을 조정할 수 있고 기본값은 `error`다.

## 동적 업스트림 (DNS 기반 라우팅)

업스트림에 고정 IP 대신 도메인을 쓰면 Nginx는 시작 시 한 번만 DNS를 조회한다. 이후 IP가 바뀌어도 반영되지 않는다.

실시간으로 DNS를 조회하게 하려면 `resolver`와 변수를 조합해야 한다.

```nginx
stream {
    resolver 8.8.8.8 valid=30s;  # DNS 결과를 30초 캐시
    resolver_timeout 5s;

    server {
        listen 3306;

        set $backend "db.internal:3306";
        proxy_pass $backend;  # 변수를 쓰면 매 연결마다 DNS 조회
    }
}
```

`upstream {}` 블록에서는 이 방법이 동작하지 않는다. 변수를 `proxy_pass`에 직접 넣어야 한다.

`resolver valid=30s`는 DNS TTL을 무시하고 30초마다 재조회한다. ECS나 Kubernetes에서 서비스 IP가 자주 바뀌는 환경에서 주로 쓰는 패턴이다. 내부 DNS 서버를 resolver로 지정하는 게 일반적이다.

```nginx
stream {
    resolver 10.0.0.2 valid=10s ipv6=off;  # 내부 DNS, IPv6 제외
    resolver_timeout 3s;

    server {
        listen 5432;
        set $pg_host "postgres.service.consul:5432";
        proxy_pass $pg_host;
    }
}
```

## half-close 동작

TCP에는 한쪽만 연결을 닫을 수 있는 half-close가 있다. 클라이언트가 FIN을 보내도 서버는 계속 데이터를 보낼 수 있는 상태다.

기본적으로 Nginx stream은 한쪽이 연결을 닫으면 반대쪽도 같이 닫는다. `proxy_half_close on`을 켜면 half-close를 허용한다.

```nginx
stream {
    server {
        listen 8080;
        proxy_pass backend;

        proxy_half_close on;
    }
}
```

half-close가 필요한 경우는 드물다. 일부 프로토콜(특정 FTP passive mode, SSH subsystem)이 EOF 신호를 통해 전송 완료를 알리는 방식을 쓸 때 half-close가 없으면 동작이 깨진다. 일반 MySQL/Redis 프록시에서는 기본값(off)으로 두면 된다.

## 주의사항

**접근 로그 형식이 다르다.** `stream {}` 안에서 `access_log`를 쓰려면 `log_format`도 stream용으로 따로 정의해야 한다. HTTP의 `$request`, `$status` 같은 변수는 stream에서 없다.

```nginx
stream {
    log_format stream_log '$remote_addr [$time_local] '
                          '$protocol $status '
                          '$bytes_sent $bytes_received '
                          '$session_time';

    access_log /var/log/nginx/stream_access.log stream_log;
}
```

**`proxy_protocol`을 켜면 백엔드도 PROXY protocol을 이해해야 한다.** 클라이언트 실제 IP를 백엔드에 전달하고 싶어서 `proxy_protocol on`을 켰는데 백엔드 MySQL이 이를 모르면 첫 바이트에서 연결이 끊긴다. PROXY protocol을 지원하는 서버(HAProxy, 일부 PostgreSQL 설정)에서만 켜야 한다.

**stream 모듈은 `include` 경로도 분리하는 게 낫다.** `http {}` 설정과 `stream {}` 설정이 같은 파일에 섞이면 관리하기 어렵다.

```nginx
# nginx.conf
http {
    include /etc/nginx/conf.d/*.conf;
}

stream {
    include /etc/nginx/stream.d/*.conf;
}
```

`/etc/nginx/stream.d/` 디렉토리를 만들고 각 서비스별 TCP 설정 파일을 분리해두면 HTTP 설정과 충돌 없이 관리할 수 있다.

## 실무 트러블슈팅

### 연결은 되는데 데이터가 안 오는 경우

TCP 3-way handshake는 성공했는데 클라이언트가 응답을 못 받는 경우, 대부분 `proxy_timeout` 문제다.

```bash
# 업스트림 서버가 실제로 응답하는지 직접 확인
nc -v db.internal 3306

# Nginx 측에서 연결 상태 확인
ss -tnp | grep nginx
```

업스트림 서버가 직접 연결에서는 응답하는데 Nginx를 거치면 안 온다면, `proxy_connect_timeout`이 너무 짧거나 방화벽이 Nginx → 업스트림 연결을 차단하는 경우다.

연결이 맺어지고 일정 시간 후 갑자기 끊어지는 패턴이라면 `proxy_timeout`이 원인이다. stream access 로그의 `$session_time`이 정확히 `proxy_timeout` 값 근처에서 끊어지면 확정이다.

```nginx
stream {
    server {
        listen 3306;
        proxy_pass mysql_backend;
        proxy_timeout 3600s;  # 긴 쿼리가 있는 환경이면 늘려야 한다
    }
}
```

### 로그로 디버깅하는 법

stream 전용 log_format을 만들고 디버깅에 필요한 변수를 넣어둔다.

```nginx
stream {
    log_format stream_debug '$remote_addr [$time_local] '
                            '$protocol $status '
                            'sent=$bytes_sent recv=$bytes_received '
                            'session=$session_time '
                            'upstream=$upstream_addr '
                            'upstream_connect=$upstream_connect_time '
                            'upstream_session=$upstream_session_time';

    access_log /var/log/nginx/stream_access.log stream_debug;
}
```

`$upstream_connect_time`이 크면 업스트림 서버가 느리거나 네트워크 레이턴시 문제다. `$session_time`이 짧고 `$status`가 500번대면 업스트림 연결 자체가 실패하는 것이다.

에러 로그 레벨을 높이면 더 자세한 정보를 볼 수 있다.

```nginx
# nginx.conf (전역)
error_log /var/log/nginx/error.log debug;
```

`debug` 레벨은 로그 양이 매우 많아 운영 환경에서는 쓰기 어렵다. 문제가 있을 때 잠깐 켜고, 재현 후 다시 `warn`이나 `error`로 내린다.

Nginx 재시작 없이 로그 레벨만 바꾸고 싶다면 reload로 충분하다.

```bash
nginx -s reload
```
