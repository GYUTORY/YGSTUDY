---
title: Nginx Rate Limiting
tags: [webserver, nginx, rate-limiting, ddos, security, limit-req, limit-conn]
updated: 2026-04-09
---

# Nginx Rate Limiting

## 개요

Rate Limiting은 클라이언트가 일정 시간 동안 보낼 수 있는 요청 수를 제한하는 기법이다. 무차별 대입 공격, DDoS, API 남용을 방어하는 첫 번째 방어선이다.

```
Rate Limiting이 필요한 상황:
  - 로그인 엔드포인트에 brute force 공격
  - 특정 IP가 초당 수백 개 요청을 보내 서버 부하 유발
  - 외부 공개 API의 과도한 사용 제한
  - 크롤러/봇 트래픽 제어
```

---

## Leaky Bucket 알고리즘 — limit_req의 내부 동작

Nginx의 `limit_req`는 Leaky Bucket(누수 버킷) 알고리즘으로 동작한다. 요청이 버킷에 들어오고, 설정한 rate에 맞춰 일정한 속도로 빠져나간다. 버킷이 가득 차면 새 요청은 버려진다.

```
                    요청 유입 (불규칙)
                    │ │ │││  │  ││││ │
                    ▼ ▼ ▼▼▼  ▼  ▼▼▼▼ ▼
               ┌──────────────────────┐
               │    ┌──────────────┐  │
               │    │  burst 큐    │  │◄── burst=5이면 최대 5개 대기
               │    │  (대기열)    │  │
               │    └──────┬───────┘  │
               │           │          │
               │    rate에 맞춰 처리  │◄── rate=10r/s이면 100ms마다 1개
               │           │          │
               └───────────┼──────────┘
                           ▼
                      백엔드 서버
               
               버킷 초과분 → 503/429 반환
```

핵심 동작 원리:

- **rate**: 버킷에서 요청이 빠져나가는 속도. `rate=10r/s`이면 100ms 간격으로 1개씩 처리한다.
- **burst**: 버킷의 크기. 순간적으로 rate를 초과하는 요청을 담아두는 공간이다.
- burst를 넘는 요청은 즉시 거부된다. burst 내 요청은 파라미터(`nodelay` / `delay`)에 따라 처리 방식이 달라진다.

---

## limit_req — 요청 속도 제한

### 기본 구조

```nginx
# http 블록: 제한 영역 정의
http {
    # $binary_remote_addr: 클라이언트 IP (binary 형식으로 메모리 절약)
    # zone=api:10m: "api" 이름, 메모리 10MB (약 160,000개 IP 저장 가능)
    # rate=10r/s: 초당 10회 허용
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}

# server/location 블록: 적용
server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }
}
```

### burst, nodelay, delay 파라미터 비교

`rate=10r/s`, `burst=5` 기준으로 1초 안에 요청 8개가 동시에 도착한 경우를 비교한다.

```
[방식 1] burst 없음 (limit_req zone=api;)
─────────────────────────────────────────
요청:  ① ② ③ ④ ⑤ ⑥ ⑦ ⑧
결과:  ✓ × × × × × × ×       ← 1개만 즉시 처리, 나머지 전부 거부
       처리              거부

[방식 2] burst=5 (limit_req zone=api burst=5;)
─────────────────────────────────────────
요청:  ① ② ③ ④ ⑤ ⑥ ⑦ ⑧
결과:  ✓ ⏳ ⏳ ⏳ ⏳ ⏳ × ×     ← 1개 즉시 처리, 5개 큐 대기, 2개 거부
       │  └──────────┘  └┘
       즉시   100ms 간격   거부
             순차 처리
       
       시간축: 0ms  100ms  200ms  300ms  400ms  500ms
              ①    ②      ③      ④      ⑤      ⑥

[방식 3] burst=5 nodelay (limit_req zone=api burst=5 nodelay;)
─────────────────────────────────────────
요청:  ① ② ③ ④ ⑤ ⑥ ⑦ ⑧
결과:  ✓ ✓ ✓ ✓ ✓ ✓ × ×       ← 6개(1+burst) 즉시 처리, 2개 거부
       └──────────┘  └┘
       전부 즉시 처리   거부
       (burst 슬롯은 rate에 따라 회복)

[방식 4] burst=5 delay=3 (limit_req zone=api burst=5 delay=3;)
─────────────────────────────────────────
요청:  ① ② ③ ④ ⑤ ⑥ ⑦ ⑧
결과:  ✓ ✓ ✓ ✓ ⏳ ⏳ × ×     ← 4개(1+delay) 즉시, 2개 지연, 2개 거부
       └────────┘ └──┘ └┘
       즉시 처리  지연  거부
```

#### delay 파라미터 (Nginx 1.15.7+)

`nodelay`는 burst 전체를 즉시 처리하지만, `delay=N`은 처음 N개까지만 즉시 처리하고 나머지는 지연시킨다. `nodelay`와 큐 대기의 중간 지점이다.

```nginx
# delay=3: 처음 3개는 즉시, 나머지 burst 요청은 rate에 맞춰 처리
location /api/ {
    limit_req zone=api burst=10 delay=3;
    proxy_pass http://backend;
}
```

실무에서 사용하는 기준:

- `nodelay` — 클라이언트 응답 속도가 중요한 API. 백엔드가 순간 부하를 감당할 수 있을 때
- `delay=N` — 일부 요청은 빠르게 보내되, 과도한 burst는 천천히 처리하고 싶을 때
- burst만 (delay 없음) — 모든 요청을 rate에 맞춰 순차 처리. 백엔드 보호가 최우선일 때

```nginx
# 세 가지 방식 비교
location /api/strict {
    limit_req zone=api;               # burst 없음 — 초과 즉시 503
    proxy_pass http://backend;
}

location /api/queued {
    limit_req zone=api burst=20;      # burst 있음 — 대기 후 처리
    proxy_pass http://backend;
}

location /api/burst {
    limit_req zone=api burst=20 nodelay; # 즉시 처리 + 누적 제한
    proxy_pass http://backend;
}

location /api/mixed {
    limit_req zone=api burst=20 delay=5; # 5개 즉시 + 나머지 지연
    proxy_pass http://backend;
}
```

---

## limit_req_dry_run — 적용 전 테스트

실서비스에 Rate Limiting을 처음 적용하면 정상 트래픽까지 차단하는 사고가 난다. `limit_req_dry_run`은 실제로 요청을 거부하지 않으면서 로그에만 기록한다. Nginx 1.17.1부터 사용할 수 있다.

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_req_dry_run on;          # 실제 거부하지 않고 로그만 남김
        proxy_pass http://backend;
    }
}
```

dry run 상태에서 `$limit_req_status` 변수를 로그에 기록하면 어떤 요청이 제한 대상인지 확인할 수 있다.

```nginx
http {
    log_format dry_run '$remote_addr [$time_local] '
                       '"$request" $status '
                       'limit_req_status=$limit_req_status';

    access_log /var/log/nginx/dryrun.log dry_run;
}
```

`$limit_req_status` 값:

| 값 | 의미 |
|---|------|
| `PASSED` | 제한 범위 내 — 정상 통과 |
| `DELAYED` | burst 큐에서 대기 처리됨 |
| `REJECTED` | 제한 초과 — dry_run이 아니었으면 거부됨 |
| `DELAYED_DRY_RUN` | dry run 모드에서 지연 대상 |
| `REJECTED_DRY_RUN` | dry run 모드에서 거부 대상 |

```bash
# dry run 로그에서 거부 대상 확인
grep "REJECTED_DRY_RUN" /var/log/nginx/dryrun.log | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -20
```

운영 절차: dry_run on으로 배포 → 1~2일 로그 분석 → rate/burst 값 조정 → dry_run off로 전환.

---

## 다중 Zone 중첩 적용

하나의 location에 여러 `limit_req`를 동시에 적용할 수 있다. 모든 zone의 조건을 동시에 만족해야 요청이 통과한다.

```nginx
http {
    # IP당 제한
    limit_req_zone $binary_remote_addr zone=per_ip:10m rate=10r/s;
    
    # 서버 전체 제한 (전체 트래픽 상한)
    limit_req_zone $server_name zone=per_server:10m rate=1000r/s;
    
    # 사용자별 제한
    limit_req_zone $http_x_user_id zone=per_user:10m rate=50r/s;
}

server {
    location /api/ {
        # 세 개 zone 동시 적용 — 하나라도 초과하면 거부
        limit_req zone=per_ip burst=20 nodelay;
        limit_req zone=per_server burst=200 nodelay;
        limit_req zone=per_user burst=100 nodelay;
        
        proxy_pass http://backend;
    }
}
```

```
다중 Zone 처리 흐름:

요청 도착
    │
    ▼
┌─────────────────┐    초과    ┌──────────┐
│ per_ip 검사     │──────────▶│ 429 반환  │
│ (IP당 10r/s)    │           └──────────┘
└────────┬────────┘
         │ 통과
         ▼
┌─────────────────┐    초과    ┌──────────┐
│ per_server 검사 │──────────▶│ 429 반환  │
│ (서버 1000r/s)  │           └──────────┘
└────────┬────────┘
         │ 통과
         ▼
┌─────────────────┐    초과    ┌──────────┐
│ per_user 검사   │──────────▶│ 429 반환  │
│ (사용자 50r/s)  │           └──────────┘
└────────┬────────┘
         │ 통과
         ▼
    백엔드 전달
```

zone 순서에 따라 먼저 선언한 `limit_req`부터 검사한다. 자주 걸리는 조건을 위에 두면 불필요한 검사를 줄일 수 있다.

주의할 점: 중첩 zone에서 `limit_req_status` 429가 어떤 zone에서 발생했는지 로그만으로는 구분이 어렵다. zone별로 별도 로그를 남기거나 error_log의 상세 메시지를 확인해야 한다.

---

## 공유 메모리 Zone 사이징

`limit_req_zone`의 메모리 크기는 추적할 클라이언트 수에 따라 결정한다. 메모리가 부족하면 기존 항목이 제거되면서 Rate Limiting이 제대로 동작하지 않는다.

### $binary_remote_addr 기준 계산

IPv4에서 `$binary_remote_addr`는 IP당 약 64바이트를 사용한다 (red-black tree 노드 포함).

```
계산식:
  필요 메모리 = 추적할 고유 IP 수 × 64바이트

예시:
  1MB  ≈ 약 16,000개 IP
  10MB ≈ 약 160,000개 IP
  32MB ≈ 약 500,000개 IP
```

IPv6 환경에서는 `$binary_remote_addr`가 16바이트로 늘어나서 IP당 약 128바이트를 소비한다. 같은 메모리에서 저장 가능한 IP 수가 절반으로 줄어든다.

### 복합 키 사용 시

```nginx
# 복합 키: IP + URI 조합
limit_req_zone "$binary_remote_addr$uri" zone=per_ip_uri:10m rate=5r/s;
```

복합 키는 키 길이에 따라 항목당 메모리 사용량이 크게 늘어난다. `$uri`가 포함되면 URI 길이만큼 추가 메모리를 소비한다. 복합 키 zone은 넉넉하게 잡아야 한다.

### 사이징 판단 기준

```bash
# 현재 고유 IP 수 확인
awk '{print $1}' /var/log/nginx/access.log | sort -u | wc -l

# 피크 시간대 1시간 동안의 고유 IP 수 확인
awk '$4 ~ /09\/Apr\/2026:1[0-1]:/' /var/log/nginx/access.log | \
  awk '{print $1}' | sort -u | wc -l
```

실무 기준: 피크 시간대 고유 IP 수의 2배 정도를 수용하는 크기로 설정한다. 메모리가 부족하면 Nginx error log에 `"could not allocate node"` 메시지가 남는다.

---

## limit_conn — 동시 연결 수 제한

```nginx
http {
    limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;
    limit_conn_zone $server_name zone=conn_per_server:10m;
}

server {
    # IP당 동시 연결 10개 제한
    limit_conn conn_per_ip 10;

    # 서버 전체 동시 연결 1000개 제한
    limit_conn conn_per_server 1000;
}
```

---

## 엔드포인트별 차등 적용

엔드포인트의 민감도에 따라 다른 제한을 적용한다.

```nginx
http {
    # 영역 정의
    limit_req_zone $binary_remote_addr zone=general:10m  rate=30r/s;
    limit_req_zone $binary_remote_addr zone=api:10m      rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m    rate=5r/m;
    limit_req_zone $binary_remote_addr zone=register:10m rate=3r/m;
    limit_req_zone $binary_remote_addr zone=search:10m   rate=20r/s;
}

server {
    # 일반 정적 자원
    location / {
        limit_req zone=general burst=50 nodelay;
    }

    # API 전반
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }

    # 로그인 — 가장 엄격
    location /api/auth/login {
        limit_req zone=login burst=3;
        limit_req_status 429;          # 429 Too Many Requests 반환
        proxy_pass http://backend;
    }

    # 회원가입
    location /api/auth/register {
        limit_req zone=register burst=2;
        limit_req_status 429;
        proxy_pass http://backend;
    }

    # 검색 API
    location /api/search {
        limit_req zone=search burst=30 nodelay;
        proxy_pass http://backend;
    }
}
```

---

## 커스텀 키 — IP 외 기준으로 제한

```nginx
http {
    # 인증된 사용자 기준 (JWT에서 추출한 사용자 ID)
    limit_req_zone $http_x_user_id zone=per_user:10m rate=100r/s;

    # API 키 기준
    limit_req_zone $http_x_api_key zone=per_apikey:10m rate=1000r/m;

    # IP + URI 조합
    limit_req_zone "$binary_remote_addr:$uri" zone=per_ip_uri:10m rate=5r/s;
}
```

---

## 화이트리스트 (특정 IP 제외)

```nginx
http {
    geo $limit {
        default 1;              # 기본: 제한 적용
        127.0.0.1 0;            # 로컬호스트: 제외
        10.0.0.0/8 0;           # 내부망: 제외
        203.0.113.100 0;        # 특정 파트너 IP: 제외
    }

    map $limit $limit_key {
        0 "";                   # 화이트리스트: 빈 키 → 제한 미적용
        1 $binary_remote_addr;  # 나머지: IP 기준 제한
    }

    limit_req_zone $limit_key zone=api:10m rate=10r/s;
}

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }
}
```

---

## 초과 시 응답 커스터마이징

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_status 429;    # 기본 503 대신 429 사용
    limit_conn_status 429;
}

server {
    # 429 에러 페이지 커스터마이징
    error_page 429 /rate_limit.json;

    location = /rate_limit.json {
        internal;
        default_type application/json;
        return 429 '{"error":"Too Many Requests","retryAfter":60}';
    }

    # Retry-After 헤더 추가
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        # 제한 초과 시 헤더 추가
        add_header Retry-After 60 always;
        add_header X-RateLimit-Limit 10 always;

        proxy_pass http://backend;
    }
}
```

---

## 로그로 Rate Limit 모니터링

```nginx
http {
    # Rate Limit 로그 포맷
    log_format rate_limit '$remote_addr [$time_local] '
                          '"$request" $status '
                          'limit_req=$limit_req_status '
                          'limit_conn=$limit_conn_status';

    # 429 응답만 별도 로그 파일에 기록
    map $status $is_rate_limited {
        429     1;
        default 0;
    }

    access_log /var/log/nginx/rate_limit.log rate_limit if=$is_rate_limited;
}
```

```bash
# Rate Limit 발생 IP 상위 10개 확인
awk '$9 == 429 {print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# 분당 429 발생 건수 추이
awk '$9 == 429 {print substr($4,2,17)}' /var/log/nginx/access.log | uniq -c
```

---

## fail2ban 연동 — 반복 위반 IP 자동 차단

Rate Limiting만으로는 429를 계속 때리는 IP를 막지 못한다. 요청은 거부되지만 Nginx가 계속 처리해야 하므로 리소스를 소비한다. fail2ban을 연동하면 반복 위반 IP를 iptables/nftables 레벨에서 차단한다.

### fail2ban 필터 설정

```ini
# /etc/fail2ban/filter.d/nginx-limit-req.conf
[Definition]
failregex = limiting requests, excess: .* by zone .*, client: <HOST>
ignoreregex =
```

Nginx error log에 남는 rate limit 메시지를 파싱한다. `client: <HOST>` 부분에서 IP를 추출한다.

### fail2ban jail 설정

```ini
# /etc/fail2ban/jail.d/nginx-limit-req.conf
[nginx-limit-req]
enabled  = true
filter   = nginx-limit-req
logpath  = /var/log/nginx/error.log
maxretry = 10          # 10회 위반 시 차단
findtime = 60          # 60초 이내
bantime  = 3600        # 1시간 차단
action   = iptables-multiport[name=nginx-limit-req, port="http,https", protocol=tcp]
```

### 동작 흐름

```
클라이언트 요청
      │
      ▼
┌──────────────┐     통과      ┌──────────────┐
│  iptables    │──────────────▶│   Nginx      │
│  (fail2ban)  │               │  limit_req   │
└──────────────┘               └──────┬───────┘
      ▲                               │
      │                          429 반환 + 
      │                          error.log 기록
      │                               │
      │         10회 초과 시           ▼
      └───────────────────────  fail2ban 감지
         IP를 iptables에 추가         
         → 패킷 레벨에서 DROP
```

`bantime`을 점진적으로 늘리려면 fail2ban의 `bantime.increment` 옵션을 사용한다. 재범 IP는 1시간 → 6시간 → 24시간으로 차단 시간이 늘어난다.

```bash
# fail2ban 상태 확인
fail2ban-client status nginx-limit-req

# 수동 차단 해제
fail2ban-client set nginx-limit-req unbanip 192.168.1.100
```

---

## 컨테이너 환경에서의 Rate Limiting 주의사항

Docker, Kubernetes 환경에서 Nginx Rate Limiting을 적용하면 온프레미스와 다른 문제가 발생한다.

### 클라이언트 IP 식별 문제

컨테이너 환경에서는 로드밸런서, Ingress Controller, Service Mesh가 앞에 있어서 `$remote_addr`가 실제 클라이언트 IP가 아닌 프록시 IP가 된다. 모든 요청이 같은 IP로 들어오면 Rate Limiting은 무용지물이다.

```nginx
# 잘못된 설정 — 프록시 IP로 제한하면 모든 클라이언트가 rate를 공유
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# 올바른 설정 — X-Forwarded-For에서 실제 IP 추출
set_real_ip_from 10.0.0.0/8;       # 프록시 대역
set_real_ip_from 172.16.0.0/12;    # Docker 내부 대역
real_ip_header X-Forwarded-For;
real_ip_recursive on;              # 여러 프록시를 거칠 때

limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

`real_ip_recursive on`은 X-Forwarded-For 체인에서 신뢰할 수 있는 프록시 IP를 제거하고 가장 마지막 비신뢰 IP를 클라이언트 IP로 사용한다.

### 공유 메모리와 컨테이너 수명

Nginx 컨테이너가 재시작되면 `limit_req_zone`의 공유 메모리가 초기화된다. Rate Limiting 상태가 날아가면서 재시작 직후 burst 트래픽이 그대로 백엔드로 전달될 수 있다.

```
컨테이너 재시작 시:
  1. 공유 메모리 초기화 → 모든 IP의 rate 카운터 리셋
  2. 제한이 걸려 있던 IP도 다시 full burst 사용 가능
  3. 배포 시 rolling update로 여러 Pod가 순차 재시작하면
     각 Pod마다 독립적인 rate 카운터 운영
```

여러 Nginx Pod가 있으면 각 Pod가 독립적인 메모리를 가지므로 Pod 수만큼 rate가 배로 허용된다. Pod가 3개이면 실질적으로 `rate=30r/s`가 되는 셈이다.

### Kubernetes 환경 대응

```
해결 방법:

1. Ingress Controller 레벨에서 Rate Limiting
   → 개별 Pod가 아닌 Ingress에서 통합 관리
   → NGINX Ingress Controller의 annotation 사용:
     nginx.ingress.kubernetes.io/limit-rps: "10"
     nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"

2. 외부 Rate Limiter 사용
   → Redis 기반 Rate Limiting (애플리케이션 레벨)
   → Envoy + Global Rate Limit Service
   → API Gateway (Kong, Ambassador)에 위임

3. Pod 수를 고려한 rate 설정
   → Pod가 N개이면 rate를 1/N로 설정
   → HPA로 Pod 수가 변하면 rate도 달라지는 문제가 있어 권장하지 않음
```

### Docker Compose에서의 설정

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:1.25
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    # tmpfs로 공유 메모리 크기 확보 (기본 64MB)
    shm_size: '256m'
```

`shm_size`가 부족하면 zone 할당에 실패한다. 여러 zone을 사용할 때는 전체 zone 크기의 합보다 넉넉하게 설정해야 한다.

---

## 선택 기준

| 엔드포인트 | 권장 rate | burst | 이유 |
|----------|-----------|-------|------|
| 로그인 / 비밀번호 재설정 | `5r/m` | 3 | brute force 방어 |
| 회원가입 | `3r/m` | 2 | 계정 생성 남용 방지 |
| 일반 API | `10r/s` | 20 | 정상 트래픽 허용 |
| 검색 | `20r/s` | 30 | 자동완성 등 빠른 연속 요청 |
| 파일 다운로드 | `5r/s` | 5 | 대역폭 보호 |
| Webhook / 콜백 | 제한 없음 | - | 외부 서비스 IP 화이트리스트 처리 |
