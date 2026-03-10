---
title: Nginx Rate Limiting
tags: [webserver, nginx, rate-limiting, ddos, security, limit-req, limit-conn]
updated: 2026-03-08
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

### burst와 nodelay

```
rate=10r/s 단독 사용:
  → 정확히 100ms마다 1개씩만 허용. 한꺼번에 오면 지연/거절

burst=20:
  → 순간 20개까지 큐에 쌓아두고 처리. 초과분은 503 반환

burst=20 nodelay:
  → 큐에 넣되 지연 없이 즉시 처리. 순간 트래픽 허용하되 누적 제한
```

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
```

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

## 선택 기준

| 엔드포인트 | 권장 rate | burst | 이유 |
|----------|-----------|-------|------|
| 로그인 / 비밀번호 재설정 | `5r/m` | 3 | brute force 방어 |
| 회원가입 | `3r/m` | 2 | 계정 생성 남용 방지 |
| 일반 API | `10r/s` | 20 | 정상 트래픽 허용 |
| 검색 | `20r/s` | 30 | 자동완성 등 빠른 연속 요청 |
| 파일 다운로드 | `5r/s` | 5 | 대역폭 보호 |
| Webhook / 콜백 | 제한 없음 | - | 외부 서비스 IP 화이트리스트 처리 |
