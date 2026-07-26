---
title: Nginx Stream 모듈
tags: [Nginx, Stream, TCP, UDP, L4, Proxy, Load-Balancing]
updated: 2026-07-26
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
    upstream backend {
        # Round Robin (기본값)
        server app1.internal:3306;
        server app2.internal:3306;

        # 또는 least_conn
        least_conn;
        server app1.internal:3306;
        server app2.internal:3306;

        # 또는 hash (클라이언트 IP 기반 고정 라우팅)
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
