---
title: 로드 밸런싱 심화
tags: [network, web-server, aws, monitoring]
updated: 2026-03-01
---

# 로드 밸런싱 심화

## 개요

로드 밸런싱(Load Balancing)은 들어오는 네트워크 트래픽을 **여러 서버에 분산**하여 가용성, 성능, 확장성을 확보하는 기술이다.

```
                         ┌─────────────┐
                    ┌──▶│   Server 1   │
                    │    └─────────────┘
┌────────┐    ┌────┴────┐ ┌─────────────┐
│ Client │──▶│   LB    │──▶│   Server 2   │
└────────┘    └────┬────┘ └─────────────┘
                    │    ┌─────────────┐
                    └──▶│   Server 3   │
                         └─────────────┘
```

### L4 vs L7 로드 밸런싱

```
L4 (전송 계층):
  TCP/UDP 레벨에서 분산
  IP 주소 + 포트 기반
  빠름, 단순

  Client ──TCP──▶ L4 LB ──TCP──▶ Server

L7 (응용 계층):
  HTTP 레벨에서 분산
  URL, 헤더, 쿠키 기반
  유연, 기능 풍부

  Client ──HTTP──▶ L7 LB ──HTTP──▶ Server
         (URL, 헤더 분석)
```

| 비교 | L4 (전송 계층) | L7 (응용 계층) |
|------|--------------|---------------|
| **분산 기준** | IP + 포트 | URL, 헤더, 쿠키 |
| **성능** | 매우 빠름 | 빠름 (약간의 오버헤드) |
| **SSL 종료** | 불가 (패스스루) | 가능 |
| **콘텐츠 라우팅** | 불가 | 가능 (`/api` → 서버A, `/web` → 서버B) |
| **WebSocket** | 가능 | 가능 (Upgrade 처리) |
| **헬스 체크** | TCP 연결만 | HTTP 응답 코드 확인 |
| **도구** | NLB, HAProxy(TCP), LVS | ALB, Nginx, HAProxy(HTTP), Envoy |
| **적합한 경우** | TCP/UDP 서비스, 게임 | 웹 서비스, API |

## 핵심

### 1. 분산 알고리즘

#### Round Robin

순서대로 돌아가며 분배한다.

```
요청 1 → Server A
요청 2 → Server B
요청 3 → Server C
요청 4 → Server A  (처음으로 돌아감)
...
```

```nginx
# Nginx (기본값)
upstream backend {
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
    server 10.0.1.3:8080;
}
```

- 장점: 구현 단순, 균등 분배
- 단점: 서버 성능 차이 미반영

#### Weighted Round Robin

서버에 **가중치**를 부여하여 성능 비율대로 분배한다.

```
weight 5: Server A (고성능) → 5번 중 5회
weight 3: Server B (중간)   → 5번 중 3회
weight 2: Server C (저성능) → 5번 중 2회
```

```nginx
upstream backend {
    server 10.0.1.1:8080 weight=5;   # 50%
    server 10.0.1.2:8080 weight=3;   # 30%
    server 10.0.1.3:8080 weight=2;   # 20%
}
```

#### Least Connections

**현재 연결 수가 가장 적은** 서버로 보낸다.

```
Server A: 15 active connections
Server B: 8 active connections   ← 새 요청은 여기로
Server C: 12 active connections
```

```nginx
upstream backend {
    least_conn;
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
    server 10.0.1.3:8080;
}
```

- 장점: 실시간 부하 반영
- 적합: 요청 처리 시간이 불균일한 경우

#### IP Hash

클라이언트 IP를 기반으로 **항상 같은 서버**로 라우팅한다.

```
Client 1 (IP: 10.0.0.1) → 항상 Server A
Client 2 (IP: 10.0.0.2) → 항상 Server C
Client 3 (IP: 10.0.0.3) → 항상 Server B
```

```nginx
upstream backend {
    ip_hash;
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
    server 10.0.1.3:8080;
}
```

- 장점: 세션 유지 (Sticky Session)
- 단점: 부하 불균형 가능, NAT 환경에서 편중

#### Consistent Hashing

해시 링 기반으로 분배. 서버 추가/제거 시 **재분배를 최소화**한다.

```
해시 링 (0 ~ 2^32):

      0
    /    \
  C        A       ← 서버가 링 위에 배치
  |        |
  B ──── (key)     ← 요청 키의 해시값에서 시계방향으로 가장 가까운 서버

서버 추가 시:
  A, B, C에서 D 추가 → B~D 사이의 키만 D로 이동 (나머지 영향 없음)
```

```nginx
upstream backend {
    hash $request_uri consistent;
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
    server 10.0.1.3:8080;
}
```

- 장점: 서버 증감 시 캐시 무효화 최소화
- 적합: 캐시 서버 앞단, CDN

#### 알고리즘 선택 가이드

| 알고리즘 | 세션 유지 | 균등 분배 | 성능 반영 | 캐시 친화 | 적합한 경우 |
|---------|---------|---------|---------|---------|-----------|
| Round Robin | ❌ | ✅ | ❌ | ❌ | 무상태 API |
| Weighted RR | ❌ | ⭐ | ✅ | ❌ | 이기종 서버 |
| Least Conn | ❌ | ⭐ | ✅ | ❌ | 긴 요청 처리 |
| IP Hash | ✅ | ❌ | ❌ | ⭐ | 세션 기반 앱 |
| Consistent Hash | ✅ | ❌ | ❌ | ✅ | 캐시 서버 |
| Random | ❌ | ✅ | ❌ | ❌ | 대규모 클러스터 |

### 2. 헬스 체크

비정상 서버를 자동으로 제외하고 복구 시 다시 포함한다.

#### Passive Health Check

실제 요청의 실패를 감지한다.

```nginx
# Nginx Passive Health Check
upstream backend {
    server 10.0.1.1:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.2:8080 max_fails=3 fail_timeout=30s;
    server 10.0.1.3:8080 max_fails=3 fail_timeout=30s;
}

# 30초 이내에 3번 실패하면 해당 서버를 30초간 제외
```

#### Active Health Check

주기적으로 **헬스 체크 요청**을 보내 서버 상태를 확인한다.

```
HAProxy Health Check 흐름:

매 5초마다:
  LB ──GET /health──▶ Server A → 200 OK (정상)
  LB ──GET /health──▶ Server B → 503     (비정상) → 제외
  LB ──GET /health──▶ Server C → 200 OK (정상)
```

```haproxy
# HAProxy Active Health Check
backend app_servers
    option httpchk GET /health
    http-check expect status 200

    server web1 10.0.1.1:8080 check inter 5s fall 3 rise 2
    server web2 10.0.1.2:8080 check inter 5s fall 3 rise 2
    server web3 10.0.1.3:8080 check inter 5s fall 3 rise 2

# inter 5s: 5초 간격으로 체크
# fall 3: 3번 연속 실패 시 비정상 판정
# rise 2: 2번 연속 성공 시 정상 복귀
```

#### 헬스 체크 엔드포인트 설계

```java
// Spring Boot Actuator
// GET /actuator/health → {"status": "UP"}
@Component
public class CustomHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        boolean dbOk = checkDatabase();
        boolean cacheOk = checkRedis();

        if (dbOk && cacheOk) {
            return Health.up()
                .withDetail("db", "connected")
                .withDetail("cache", "connected")
                .build();
        }
        return Health.down()
            .withDetail("db", dbOk ? "connected" : "disconnected")
            .withDetail("cache", cacheOk ? "connected" : "disconnected")
            .build();
    }
}
```

### 3. 세션 관리

#### Sticky Session (세션 고정)

동일 클라이언트의 요청을 **항상 같은 서버**로 라우팅한다.

```nginx
# Nginx: 쿠키 기반 Sticky Session
upstream backend {
    sticky cookie srv_id expires=1h domain=.example.com path=/;
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
}
```

```haproxy
# HAProxy: 쿠키 기반
backend app_servers
    cookie SERVERID insert indirect nocache
    server web1 10.0.1.1:8080 cookie s1
    server web2 10.0.1.2:8080 cookie s2
```

- 장점: 기존 세션 유지 간단
- 단점: 서버 장애 시 세션 유실, 부하 불균형

#### 세션 외부화 (권장)

세션을 서버 외부(Redis 등)에 저장하여 **어떤 서버로 라우팅되든 동일 세션 접근**.

```
Client → LB → Server A ─┐
Client → LB → Server B ─┤── Redis (세션 저장소)
Client → LB → Server C ─┘

→ 어느 서버로 가든 같은 세션 사용
→ Sticky Session 불필요
→ 서버 장애 시에도 세션 유지
```

```yaml
# Spring Boot + Redis Session
spring:
  session:
    store-type: redis
  data:
    redis:
      host: redis.example.com
      port: 6379
```

| 비교 | Sticky Session | 세션 외부화 (Redis) |
|------|---------------|-------------------|
| **구현 복잡도** | 낮음 | 중간 |
| **부하 분산** | 불균형 가능 | 균등 |
| **장애 대응** | 세션 유실 | 세션 유지 |
| **스케일 아웃** | 제한적 | 자유로움 |
| **적합한 경우** | 소규모, 레거시 | **프로덕션 권장** |

### 4. Nginx 설정

```nginx
# /etc/nginx/nginx.conf

http {
    # ─── 업스트림 정의 ───
    upstream api_servers {
        least_conn;
        server 10.0.1.1:8080 weight=3 max_fails=3 fail_timeout=30s;
        server 10.0.1.2:8080 weight=2 max_fails=3 fail_timeout=30s;
        server 10.0.1.3:8080 weight=1 backup;  # 백업 서버
    }

    upstream static_servers {
        server 10.0.2.1:80;
        server 10.0.2.2:80;
    }

    server {
        listen 443 ssl;
        server_name api.example.com;

        ssl_certificate /etc/ssl/cert.pem;
        ssl_certificate_key /etc/ssl/key.pem;

        # ─── L7 라우팅 ───
        # API 요청 → api_servers
        location /api/ {
            proxy_pass http://api_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 타임아웃
            proxy_connect_timeout 5s;
            proxy_read_timeout 60s;
            proxy_send_timeout 60s;

            # 버퍼링
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # 정적 파일 → static_servers
        location /static/ {
            proxy_pass http://static_servers;
            proxy_cache static_cache;
            proxy_cache_valid 200 1d;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://api_servers;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400s;
        }
    }
}
```

### 5. HAProxy 설정

```haproxy
# /etc/haproxy/haproxy.cfg

global
    maxconn 50000
    log stdout format raw local0

defaults
    mode http
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    option httplog
    option dontlognull

# ─── 프론트엔드 (클라이언트 접점) ───
frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/cert.pem

    # HTTP → HTTPS 리다이렉트
    http-request redirect scheme https unless { ssl_fc }

    # L7 라우팅: URL 기반
    acl is_api path_beg /api
    acl is_static path_beg /static

    use_backend api_back if is_api
    use_backend static_back if is_static
    default_backend api_back

# ─── 백엔드 (서버 그룹) ───
backend api_back
    balance leastconn
    option httpchk GET /health
    http-check expect status 200

    server api1 10.0.1.1:8080 check inter 5s fall 3 rise 2 weight 3
    server api2 10.0.1.2:8080 check inter 5s fall 3 rise 2 weight 2
    server api3 10.0.1.3:8080 check inter 5s fall 3 rise 2 backup

backend static_back
    balance roundrobin
    server static1 10.0.2.1:80 check
    server static2 10.0.2.2:80 check

# ─── 통계 대시보드 ───
frontend stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 10s
    stats auth admin:password
```

### 6. AWS 로드 밸런서

| 비교 | ALB (L7) | NLB (L4) | CLB (Classic) |
|------|---------|---------|---------------|
| **계층** | L7 (HTTP) | L4 (TCP/UDP) | L4 + L7 |
| **프로토콜** | HTTP, HTTPS, gRPC | TCP, UDP, TLS | HTTP, TCP |
| **라우팅** | 경로, 호스트, 헤더 | IP, 포트 | 기본 |
| **성능** | 높음 | **매우 높음** | 보통 |
| **고정 IP** | ❌ | ✅ | ❌ |
| **WebSocket** | ✅ | ✅ | ❌ |
| **적합한 경우** | 웹 API, MSA | 게임, IoT, TCP 서비스 | 레거시 |

```yaml
# CloudFormation: ALB + Target Group
Resources:
  ALB:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup

  TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Protocol: HTTP
      Port: 8080
      VpcId: !Ref VPC
      HealthCheckPath: /health
      HealthCheckIntervalSeconds: 15
      HealthyThresholdCount: 2
      UnhealthyThresholdCount: 3
      TargetType: ip

  Listener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref ALB
      Protocol: HTTPS
      Port: 443
      Certificates:
        - CertificateArn: !Ref Certificate
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref TargetGroup
```

### 7. 고가용성 패턴

#### Active-Passive (주-대기)

```
                    ┌──────────┐
Client ──────────▶│ Active LB │──▶ Servers
                    └────┬─────┘
                  Heartbeat│
                    ┌────┴─────┐
                    │Passive LB │  (대기, 장애 시 전환)
                    └──────────┘

→ Active 장애 시 VIP(가상 IP)가 Passive로 이동
→ VRRP(keepalived) 또는 AWS HA 사용
```

#### Active-Active (이중화)

```
                    ┌──────────┐
Client ──DNS──▶   │  LB 1    │──▶ Servers
          │        └──────────┘
          │        ┌──────────┐
          └──────▶│  LB 2    │──▶ Servers
                    └──────────┘

→ DNS 라운드 로빈 또는 Global LB로 양쪽에 분산
→ 두 LB 모두 활성 상태
```

### 8. 트러블슈팅

| 증상 | 가능한 원인 | 해결 |
|------|-----------|------|
| 502 Bad Gateway | 백엔드 서버 다운 | 헬스 체크 확인, 서버 상태 점검 |
| 503 Service Unavailable | 모든 서버 비정상 | 서버 로그 확인, 수동 복구 |
| 504 Gateway Timeout | 백엔드 응답 지연 | `proxy_read_timeout` 증가, 백엔드 최적화 |
| 불균등 분배 | Sticky Session 또는 Keep-Alive | 알고리즘 변경, 연결 제한 |
| 간헐적 연결 끊김 | LB 유휴 타임아웃 > 백엔드 keep-alive 타임아웃 | 백엔드 keep-alive를 LB보다 길게 (아래 참조) |
| WebSocket 끊김 | `proxy_read_timeout` 짧음 | 86400s로 증가, Upgrade 헤더 확인 |

### 9. 타임아웃 두 종류를 구분한다

"타임아웃을 정렬한다"는 말이 두 개의 반대 방향 규칙을 뭉뚱그린다. 섞으면 한쪽을 고치면서 다른 쪽을 만든다.

**응답 대기 타임아웃 — LB가 더 길어야 한다.** 백엔드가 30초 걸리는 작업을 하는데 LB의 read timeout이 10초면 504가 나간다. 백엔드는 정상적으로 일을 마치고 응답을 쓰려는데 상대가 이미 끊은 상태다.

**유휴 keep-alive 타임아웃 — 백엔드가 더 길어야 한다.** 이쪽이 반대다. LB는 커넥션을 재사용하려고 유휴 상태로 잡아두는데, 백엔드가 먼저 그 커넥션을 닫으면 LB가 이미 죽은 커넥션에 요청을 실어 보낸다. 결과는 502다.

```
LB 유휴 타임아웃 60s,  백엔드 keep-alive 5s

t=0    요청 처리 완료. 커넥션 유지.
t=5s   백엔드가 FIN 전송 → 커넥션 종료
t=12s  LB 가 "아직 60초 안 지났으니 살아 있다"고 판단하고 재사용
       → 이미 닫힌 소켓에 write → 502

트래픽이 한산할수록 잘 터진다. 요청이 촘촘하면 5초 유휴가 안 생기기 때문이다.
```

Node.js 기본값이 여기에 딱 걸린다. `http.createServer()`의 `keepAliveTimeout`은 5,000ms다(Node v22.21.1 실측). AWS ALB의 기본 유휴 타임아웃은 60초다. 아무 설정도 안 하고 ALB 뒤에 Node 서버를 두면 **평소엔 멀쩡하고 트래픽이 적은 새벽에만 502가 몇 건씩 찍히는** 상태가 된다. 재현이 안 되고 백엔드 로그에는 아무것도 안 남는다.

```javascript
const server = http.createServer(app);
server.keepAliveTimeout = 65_000;   // LB 유휴 타임아웃(60s)보다 길게
server.headersTimeout   = 70_000;   // keepAliveTimeout 보다 길어야 한다
server.listen(8080);
```

`headersTimeout`을 같이 올리지 않으면 헤더 대기 중에 끊기는 다른 증상이 생긴다. 기본값은 60,000ms다.

**확인 방법**: 502가 특정 시간대·저트래픽 구간에 몰리는지 본다. 몰린다면 유휴 타임아웃 문제고, 부하가 올라갈 때 몰린다면 백엔드 용량이나 커넥션 한계 문제다.

### 10. 헬스 체크가 전체 장애를 만드는 경우

위 `CustomHealthIndicator`는 DB와 Redis를 확인하고 하나라도 실패하면 `DOWN`을 반환한다. 이 엔드포인트를 LB의 헬스 체크에 그대로 물리면, **DB가 잠깐 흔들리는 순간 모든 인스턴스가 동시에 unhealthy가 된다.** 모든 인스턴스가 빠지면 LB에는 보낼 대상이 없고, 503이 나간다. DB가 5초 만에 회복돼도 `rise 2` 조건 때문에 인스턴스가 돌아오는 데 더 걸린다.

문제는 인스턴스가 아니라 DB인데, 인스턴스를 전부 빼는 것으로 대응한 셈이다. 캐시로 응답할 수 있던 요청까지 같이 죽는다.

체크를 두 개로 나눈다.

- **liveness / LB 헬스 체크**: 프로세스가 요청을 받을 수 있는가만 본다. 의존성을 타지 않는다. `return 200 OK` 수준.
- **readiness / 상세 진단**: DB·캐시 상태를 담되, **LB가 이 값으로 인스턴스를 빼지 않게 한다.** 모니터링과 알림이 소비한다.

```java
// LB 가 때리는 경로 — 의존성 확인 없음
@GetMapping("/health")
public ResponseEntity<String> health() {
    return ResponseEntity.ok("ok");
}

// 모니터링이 때리는 경로 — 의존성 상태 노출
@GetMapping("/health/deep")
public Map<String, Object> deepHealth() { ... }
```

헬스 체크 자체가 부하가 되는 것도 흔하다. `inter 5s`로 3대가 각각 체크하면 인스턴스당 초당 0.6회씩 들어온다. 여기서 매번 DB를 치면 인스턴스가 늘어날수록 DB 커넥션이 헬스 체크에 먹힌다. 액세스 로그에서 헬스 체크 경로를 빼두면 로그 용량과 지표 왜곡도 같이 줄어든다.

### 11. `ip_hash`가 한 서버로 몰리는 경우

`ip_hash`는 nginx가 보는 소스 IP로 해시한다. **CDN이나 다른 프록시 뒤에 있으면 그 IP는 전부 프록시의 IP다.** 사용자가 몇 명이든 후보 IP가 몇 개뿐이라 트래픽이 한두 서버로 쏠린다. "분산이 안 된다"의 흔한 원인이다.

앞단이 `X-Forwarded-For`를 넣어준다면 그 값으로 해시해야 한다.

```nginx
upstream backend {
    hash $http_x_forwarded_for consistent;
    server 10.0.1.1:8080;
    server 10.0.1.2:8080;
}
```

다만 `X-Forwarded-For`는 클라이언트가 위조할 수 있는 헤더다. 신뢰할 수 있는 프록시가 앞에 있고 그 프록시가 값을 덮어쓴다는 전제에서만 쓴다. `set_real_ip_from`으로 신뢰 대역을 지정하고 `$remote_addr`를 교정하는 쪽이 더 안전하다.

NAT 환경(사무실 전체가 하나의 공인 IP)에서도 같은 편중이 생긴다. 세션 유지가 목적이라면 IP 대신 쿠키 기반 sticky나, 애초에 세션 외부화 쪽이 낫다.

### 12. 배포할 때 커넥션이 끊기는 이유

인스턴스를 내릴 때 LB가 즉시 트래픽을 끊는다고 가정하면 안 된다. **헬스 체크가 실패로 바뀌기까지, 그리고 이미 진행 중인 요청이 끝나기까지 시간이 필요하다.**

- HAProxy의 `fall 3 inter 5s`는 비정상 판정까지 최대 15초가 걸린다. 그동안 들어온 요청은 죽어가는 인스턴스로 간다.
- ALB의 `deregistration_delay`(기본 300초) 동안은 새 요청을 안 보내되 진행 중인 요청은 끝날 때까지 기다린다. 이 값이 0이면 처리 중이던 요청이 끊긴다.

순서는 이렇다. **트래픽에서 먼저 빼고 → 진행 중 요청이 끝날 때까지 기다리고 → 그 다음에 프로세스를 내린다.**

```
1. 애플리케이션이 헬스 체크에 실패를 반환하기 시작 (SIGTERM 수신 시)
2. LB 가 unhealthy 로 판정해 새 요청 중단   (fall × inter 만큼 걸림)
3. 진행 중이던 요청 처리 완료               (deregistration_delay 안에)
4. 프로세스 종료
```

2번 시간만큼 애플리케이션이 SIGTERM을 받고도 계속 요청을 받아줘야 한다. 바로 종료하면 그 구간의 요청이 502가 된다. `preStop` 훅이나 종료 지연이 필요한 이유다.

## 참고

- [Nginx Load Balancing](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/)
- [HAProxy Documentation](https://docs.haproxy.org/)
- [AWS Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/)
- [프록시](Proxy.md) — Forward/Reverse Proxy 개요
- [Nginx 리버스 프록시](../../WebServer/Nginx/Reverse_Proxy_and_Load_Balancing.md) — Nginx 설정 상세
- [API Gateway](../GateWay/API_Gateway.md) — API 레벨 로드 밸런싱
