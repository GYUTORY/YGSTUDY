---
title: Connection Limit
tags: [backend, resilience, connection, ulimit, file-descriptor, somaxconn, ephemeral-port, max-connections, hikaricp, pgbouncer, rds-proxy]
updated: 2026-05-08
---

# Connection Limit

## 개요

커넥션 한도는 한 곳에서 정해지지 않는다. OS의 파일 디스크립터, 커널의 소켓 큐, 웹서버 워커, DB max_connections, 앱의 풀 사이즈가 모두 각자 상한을 들고 있다. 어느 한 군데가 가장 낮으면 그 값이 시스템 전체의 실효 상한이 된다.

운영 중 "Too many connections" 같은 에러가 떴을 때 자주 헷갈리는 이유가 여기 있다. 앱 풀 사이즈만 보고 충분하다고 판단했는데 실제로는 OS의 ulimit이 1024여서 막힌 경우, DB max_connections는 2000인데 앞단 PgBouncer가 200으로 잡혀 있어서 막힌 경우, 컨테이너 안에서 ulimit이 호스트와 다르게 적용되어 운영에서만 터지는 경우가 흔하다.

```
요청 흐름 위에 깔린 커넥션 상한 레이어

Client
  │
  │ (1) ephemeral port 범위 (32768-60999) — 클라이언트 측 한도
  ▼
LB / Nginx
  │ (2) worker_connections × workers, worker_rlimit_nofile
  ▼
App (Java/Node/Python)
  │ (3) Pool max (HikariCP 10, pg pool 10 등) × 인스턴스 수
  ▼
PgBouncer / RDS Proxy
  │ (4) max_client_conn / max_db_connections
  ▼
PostgreSQL / MySQL / Redis
  │ (5) max_connections / maxclients

각 레이어 어디든 가장 낮은 값이 실효 상한
```

## OS·커널 레벨

### file descriptor 와 ulimit -n

리눅스에서 소켓은 파일 디스크립터다. 커넥션 1개당 fd 1개가 들어간다. ulimit -n 값이 곧 한 프로세스가 동시에 열 수 있는 소켓 수의 상한이다.

기본값이 1024인 배포판이 많다. 일반 웹 서비스에서 1024는 너무 낮다. 평소엔 멀쩡하다가 트래픽이 살짝만 튀면 `accept: too many open files` 같은 에러가 나면서 새 커넥션을 못 받는다. 이미 맺힌 커넥션은 멀쩡한데 신규 accept만 실패하니까 로드밸런서 헬스체크는 통과하면서 사용자 에러만 늘어나는 골치 아픈 양상이 된다.

```bash
# 현재 셸의 한도
ulimit -n          # soft limit (실제 적용값)
ulimit -Hn         # hard limit (root만 올릴 수 있는 천장)

# 특정 프로세스의 한도 확인
cat /proc/$(pgrep -f myapp)/limits | grep "Max open files"

# 현재 프로세스가 열고 있는 fd 수
ls /proc/$(pgrep -f myapp)/fd | wc -l
```

쉘에서 `ulimit -n 65536` 으로 올려도 그 셸에서만 유효하다. 데몬으로 띄운 프로세스에는 적용 안 된다. 영구 적용은 systemd unit 또는 `/etc/security/limits.conf`로 한다.

### LimitNOFILE — systemd 단위 적용

systemd로 띄우는 서비스는 unit 파일에서 직접 지정해야 한다. `/etc/security/limits.conf`는 PAM을 거치는 로그인 세션에만 적용되기 때문에 systemd 데몬에는 안 먹는다. 이걸 모르고 limits.conf만 고쳐놓고 "왜 안 되지" 하는 경우가 많다.

```ini
# /etc/systemd/system/myapp.service
[Service]
LimitNOFILE=65536
LimitNPROC=4096
```

수정 후 `systemctl daemon-reload && systemctl restart myapp`. 적용됐는지는 `cat /proc/$(pgrep -f myapp)/limits` 로 확인한다. 재시작 없이는 절대 반영 안 된다.

### /proc/sys/fs/file-max — 시스템 전역 한도

ulimit -n이 프로세스당 한도라면 `fs.file-max` 는 시스템 전체에서 동시에 열 수 있는 fd 총합이다. 보통 메모리에 비례해 자동 설정되는데, 컨테이너 호스트나 DB 서버는 이 값을 명시적으로 올려놓는 편이 안전하다.

```bash
# 현재 시스템 전역 한도
cat /proc/sys/fs/file-max

# 현재 사용 중 / 미사용 / 최대
cat /proc/sys/fs/file-nr
# 출력: 5024  0  9223372036854775807
#       사용중 미사용 최대
```

영구 적용은 `/etc/sysctl.d/99-custom.conf`에 `fs.file-max = 2097152` 같은 형태로 넣고 `sysctl -p`. `/etc/sysctl.conf`에 직접 넣는 것보단 `/etc/sysctl.d/` 디렉토리에 별도 파일로 넣는 게 패키지 업그레이드 충돌이 적다.

### somaxconn — accept 큐 길이

TCP 3-way handshake가 완료된 커넥션이 앱이 `accept()` 호출하기 전까지 기다리는 큐가 있다. 이 큐의 최대 길이가 `net.core.somaxconn` 이다.

리눅스 5.4 이전 기본값이 128이었다. 짧은 burst 트래픽에 앱이 accept를 빨리 못 가져가면 큐가 차서 새 커넥션이 RST로 떨어진다. 클라이언트는 connection refused로 본다. 앱 로그에는 아무것도 안 남는다 — 커널이 거절했기 때문에 앱은 그 사건이 있었는지조차 모른다.

```bash
sysctl net.core.somaxconn
sysctl -w net.core.somaxconn=4096

# 큐 오버플로우 카운터
nstat -az TcpExtListenOverflows TcpExtListenDrops
```

앱 쪽에서 `listen(fd, backlog)` 호출 시 backlog 인자도 영향을 준다. 실제 적용값은 `min(backlog, somaxconn)`. Nginx는 `listen ... backlog=N` 옵션이 있고 Node.js의 `server.listen(port, backlog)` 도 마찬가지. 양쪽 다 올려야 의미가 있다.

### ephemeral port — net.ipv4.ip_local_port_range

클라이언트가 outbound 커넥션을 맺을 때마다 임시 포트(ephemeral port)를 하나씩 잡아 쓴다. 기본 범위는 보통 32768–60999, 약 28000개. (목적지 IP, 목적지 포트, 출발지 IP, 출발지 포트) 4-tuple이 유일해야 하므로, 한 클라이언트가 같은 (목적지 IP, 목적지 포트)로 동시에 맺을 수 있는 커넥션 수가 약 28000개로 묶인다.

이게 한도에 가까워지면 `EADDRNOTAVAIL` 또는 `connect: cannot assign requested address` 가 뜬다. 마이크로서비스에서 한 앱이 다른 앱 하나에 대해 short-lived HTTP를 미친듯이 날리거나, 백엔드가 외부 API에 동기 호출을 폭발적으로 보내면 이 패턴에 걸린다.

```bash
# 현재 범위
sysctl net.ipv4.ip_local_port_range
# 출력: 32768  60999

# 범위 확장 (잘 쓰지 않는 1024~32767 일부까지)
sysctl -w net.ipv4.ip_local_port_range="10000 65535"
```

대처는 보통 두 갈래다. 첫째, keep-alive 켜서 커넥션을 재사용한다. 단발 HTTP 호출로 매번 새 포트를 잡지 않게 한다. 둘째, ephemeral port 범위를 넓힌다. 셋째 — `tcp_tw_reuse` 를 켠다.

### tcp_tw_reuse 와 TIME_WAIT

커넥션을 닫으면 송신 측에 TIME_WAIT 상태가 60초(2 × MSL) 남는다. TIME_WAIT 상태인 4-tuple은 재사용 못 한다. 단발성 outbound가 많으면 ephemeral port가 TIME_WAIT으로 다 묶여서 신규 커넥션이 안 나간다.

```bash
sysctl -w net.ipv4.tcp_tw_reuse=1
```

`tcp_tw_reuse=1` 은 TIME_WAIT 상태인 포트라도 timestamp가 새것이면 재사용을 허용한다. outbound 측에만 영향을 주고, 보안상 큰 문제는 없다. 반면 과거에 자주 권장되던 `tcp_tw_recycle` 은 NAT 환경에서 정상 패킷을 떨구는 부작용 때문에 커널 4.12부터 아예 제거됐다. 옛날 블로그 글 보고 이거 켜려 들지 마라. 옵션 자체가 없다.

## 웹서버 레벨

### Nginx worker_connections / worker_rlimit_nofile

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 10240;
}
```

Nginx의 동시 처리 가능 커넥션 수는 `worker_processes × worker_connections` 다. 다만 reverse proxy로 쓰면 클라이언트 1명당 (클라이언트 → Nginx) + (Nginx → upstream) 으로 커넥션 2개를 쓰므로 실효 동시 사용자는 절반이 된다.

`worker_connections` 는 fd를 잡는다. 그래서 `worker_rlimit_nofile` 이 충분히 크지 않으면 `worker_connections` 만 올려도 무용지물이다. Nginx 자체의 `worker_rlimit_nofile` 은 systemd `LimitNOFILE` 보다 우선순위가 높지 않다. 둘 다 맞춰놔야 한다.

설정 후 `nginx -T | grep worker` 로 실제 적용값을 확인하고, `/proc/$(pgrep -f "nginx: worker")/limits` 로 워커 프로세스의 실제 한도를 본다.

## DB 레벨

### PostgreSQL max_connections

```sql
SHOW max_connections;        -- 보통 100 (기본값)
SELECT count(*) FROM pg_stat_activity;
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
```

기본값 100은 사실상 어떤 운영 환경에도 부족하다. 그렇다고 무작정 1만으로 올리면 안 된다. PostgreSQL은 커넥션당 프로세스 1개를 띄우는 구조라 커넥션 자체가 비싸다. 커넥션 1개당 메모리 10–15MB 정도가 들고, work_mem이 크면 더 든다.

운영 PostgreSQL에서 max_connections를 함부로 올리면 commit latency가 튀고 lock contention이 심해진다. 차라리 max_connections는 200~500 선에서 묶고, 앞단에 PgBouncer를 두는 게 일반적이다.

설정 변경은 `postgresql.conf` 수정 후 재시작이 필요하다. RDS는 파라미터 그룹에서 변경한다. 디폴트 파라미터 그룹은 못 고치니 커스텀 파라미터 그룹을 만들어야 한다.

### MySQL max_connections

```sql
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';
```

MySQL은 PostgreSQL과 달리 스레드 풀 기반이어서 커넥션이 비교적 가볍다. 그래도 1만 단위로 올리면 메모리·컨텍스트 스위칭 비용이 누적된다. `Max_used_connections` 가 max_connections에 근접하면 한도를 올리든 풀러를 두든 결정해야 한다.

런타임에서도 `SET GLOBAL max_connections = 500;` 로 변경 가능. 다만 이미 재시작 직후 my.cnf 값으로 다시 돌아가니 영구 적용은 my.cnf에 명시한다.

### Redis maxclients

```
CONFIG GET maxclients      -- 기본 10000
CONFIG SET maxclients 20000
INFO clients               -- 현재 connected_clients
```

Redis는 커넥션당 비용이 매우 작다. 기본값 10000도 대부분 충분하다. 다만 Redis도 fd를 쓰니 호스트의 ulimit이 더 낮으면 그게 실효 상한이 된다. Redis는 시작할 때 `maxclients` 만큼 fd를 잡으려 하다가 ulimit이 낮으면 자동으로 maxclients를 ulimit-32 정도로 낮춘다. 로그에 경고가 찍힌다. 이걸 못 보고 넘어가면 운영 중 `max number of clients reached` 가 뜬다.

## 앱 레벨

### HikariCP maximumPoolSize

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 10
      connection-timeout: 3000
      max-lifetime: 1800000
      idle-timeout: 600000
```

JVM 진영의 사실상 표준 풀러. 주의할 부분은 풀 사이즈를 키운다고 처리량이 비례해서 늘지 않는다는 점이다. HikariCP 공식 문서가 권장하는 공식이 `connections = ((core_count * 2) + effective_spindle_count)` 인데, 보통 코어 8개짜리 DB에서 풀 사이즈는 인스턴스당 10–20 정도가 합리적이다.

운영에서 자주 보는 패턴은 이렇다. 트래픽 증가 → 응답 느려짐 → "풀이 부족한가?" 추측 → 풀 사이즈 50으로 올림 → DB가 더 느려짐 → 더 올림 → DB가 죽음. 풀이 부족한 게 아니라 DB가 처리할 수 있는 동시 작업 수가 한계인 경우가 대부분이다. 풀 사이즈는 DB가 견딜 수 있는 동시 쿼리 수의 상한으로 작용해 오히려 보호 장치 역할을 한다.

### Node pg pool max

```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'db.internal',
  database: 'app',
  max: 10,                    // 풀 최대 커넥션
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

Node.js는 단일 이벤트 루프라 풀 사이즈가 너무 크면 의미가 없다. 보통 인스턴스당 5–20 사이. PM2 cluster 모드를 쓰면 워커마다 별도 풀을 잡는다는 점을 잊으면 안 된다. workers=4, max=10 이면 인스턴스당 실제로는 40개 커넥션을 잡는다.

### 곱셈으로 폭발하는 패턴

운영에서 가장 흔한 사고가 곱셈을 잊는 것이다.

```
ECS task 50개 × HikariCP 10
  = DB 커넥션 500개 요구

K8s pod 30개 × pg pool 20
  = DB 커넥션 600개 요구

추가로 분석용 파드, 배치, Lambda까지 같은 DB를 쓰면
  → 1000개 넘는 건 순식간
```

PostgreSQL max_connections가 200인데 위처럼 띄우면, HPA가 trigger 되는 순간 일부 task가 `FATAL: too many connections for role` 로 죽기 시작한다. 죽은 task의 트래픽이 살아있는 task로 몰리면서 도미노로 무너진다. CPU도 메모리도 멀쩡한데 서비스가 죽는다.

이걸 방지하려면 두 가지 중 하나다. 하나는 pool size를 작게 잡고 인스턴스 수만 늘린다 (예: pool 5, max 100 인스턴스 = 500). 다른 하나는 앞단에 풀러를 둔다.

## 커넥션 풀러 (PgBouncer / RDS Proxy)

```
풀러 없는 구조:
  App pool 10 × 50 instance = DB connections 500
  ↓ DB max_connections 200 → 폭발

풀러 두는 구조:
  App pool 10 × 50 instance = 500 client connection (PgBouncer)
                              ↓ PgBouncer max_db_connections 100
  PgBouncer ─────────────────→ DB 100 actual connections
```

PgBouncer는 transaction pooling 모드에서 한 트랜잭션 단위로 백엔드 커넥션을 빌려준다. 클라이언트 커넥션 5000개를 받아서 실제 DB로는 100개만 쓰는 식. PostgreSQL처럼 커넥션이 비싼 DB에는 거의 필수다.

다만 함정이 있다. transaction pooling 모드에서는 prepared statement, advisory lock, `SET LOCAL` 외의 세션 상태가 트랜잭션 경계에서 끊긴다. 앱에서 prepared statement를 캐싱하는 드라이버(예: 일부 ORM)가 있으면 깨진다. JDBC라면 `prepareThreshold=0`, Node-postgres라면 prepared statement 직접 사용 회피 등의 조치가 필요하다.

RDS Proxy도 같은 컨셉. AWS가 관리하므로 직접 운영 부담이 없다. Lambda 같이 인스턴스 수가 폭발적으로 늘어나는 워크로드에서 특히 효과가 크다. Lambda 동시 실행 1000개가 그대로 DB 커넥션 1000개로 가면 DB가 즉사하는데, 앞에 RDS Proxy를 두면 DB 측 커넥션은 30~50개로 묶인다.

## 컨테이너의 함정

컨테이너 안의 ulimit은 호스트의 ulimit과 별개로 docker/containerd 설정으로 정해진다. Docker 기본은 nofile=1024:524288 (soft:hard). 호스트는 65535로 잘 잡혀 있는데 컨테이너 안에서 `ulimit -n` 찍으면 1024가 나오는 경우가 많다.

```bash
# 컨테이너 안에서 확인
docker exec -it myapp ulimit -n

# 컨테이너 띄울 때 지정
docker run --ulimit nofile=65536:65536 myapp

# K8s에서는 securityContext나 sysctl로 일부 제어 가능
# 다만 nofile은 보통 노드 레벨 containerd config 또는
# initContainer로 조정해야 한다
```

K8s에서 `securityContext.sysctls` 로 일부 sysctl은 변경 가능하지만 `fs.file-max` 같은 namespaced 아닌 sysctl은 unsafe로 분류돼 kubelet 설정 없이는 못 건드린다. 노드 자체의 limit을 올리고, containerd/CRI-O 의 default ulimits 설정을 손보는 게 표준 접근이다.

EKS 노드라면 `/etc/eks/bootstrap.sh` 가 호출하는 kubelet 설정에서 podPidsLimit이나 노드 시작 user data에 sysctl 적용을 추가한다. 이걸 안 해두고 단순 yaml만 보면 "왜 운영만 ulimit이 1024냐"는 질문에 답을 못 한다.

## 운영 명령어

### 현재 커넥션 수 보기

```bash
# 가장 빠르고 가벼움 (요즘 표준)
ss -s                           # 전체 socket 통계
ss -tan                         # TCP all
ss -tan state established       # ESTABLISHED만
ss -tan | awk '{print $1}' | sort | uniq -c   # 상태별 카운트

# 특정 포트로 들어오는 커넥션
ss -tan dport = :5432           # outbound to 5432
ss -tan sport = :443            # inbound on 443

# 프로세스 단위
lsof -i -P -n | grep myapp
lsof -i :5432

# netstat은 비추 (느리고 deprecated). 그래도 익숙한 사람용:
netstat -ant | awk '{print $6}' | sort | uniq -c
```

운영 디버깅에서는 `ss` 가 압도적으로 빠르다. `netstat` 은 `/proc/net/tcp` 를 통째로 읽어서 커넥션 수만 명이 넘으면 몇 초씩 걸리고 그 사이 메트릭이 묻힌다.

### TIME_WAIT 진단

```bash
ss -tan state time-wait | wc -l

# TIME_WAIT 상위 (peer 별)
ss -tan state time-wait | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head
```

TIME_WAIT이 수만 개 쌓여 있다면 short-lived outbound가 너무 많다는 신호다. keep-alive 적용 여부, 풀러 사용 여부를 점검한다.

### fd 사용량

```bash
# 프로세스가 열고 있는 fd 수
ls /proc/$(pgrep -f myapp)/fd | wc -l

# fd 한도와 비교
cat /proc/$(pgrep -f myapp)/limits | grep "Max open files"

# 어떤 종류의 fd가 많은지
ls -la /proc/$(pgrep -f myapp)/fd | awk '{print $11}' | sort | uniq -c | sort -rn | head
```

fd가 한도의 80% 넘기 시작하면 알람을 걸어두는 게 안전하다. 100% 찍으면 새 커넥션은 물론 새 파일 열기, 새 스레드 생성까지 다 막혀서 앱이 좀비처럼 살아 있는 상태가 된다.

## 영구 적용 정리

```bash
# 1. 시스템 전역 sysctl
cat > /etc/sysctl.d/99-network.conf <<'EOF'
fs.file-max = 2097152
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 10000 65535
net.ipv4.tcp_tw_reuse = 1
EOF
sysctl -p /etc/sysctl.d/99-network.conf

# 2. 로그인 세션 한도 (PAM 경유)
cat > /etc/security/limits.d/99-nofile.conf <<'EOF'
*       soft    nofile  65536
*       hard    nofile  65536
root    soft    nofile  65536
root    hard    nofile  65536
EOF

# 3. systemd 서비스 한도 (PAM 안 거침)
mkdir -p /etc/systemd/system/myapp.service.d
cat > /etc/systemd/system/myapp.service.d/limits.conf <<'EOF'
[Service]
LimitNOFILE=65536
EOF
systemctl daemon-reload
systemctl restart myapp
```

세 군데(`sysctl.d`, `limits.d`, `systemd unit`)를 모두 손보는 이유는 적용 경로가 각각 다르기 때문이다. 어느 한 군데만 고치고 끝났다고 생각하면 어딘가에서 1024 그대로 적용되고 있는 프로세스가 반드시 나온다.

## 트러블슈팅 사례 정리

**증상 1: `accept4: too many open files`**
앱이 신규 커넥션을 못 받는다. 기존 커넥션은 정상. fd가 ulimit -n 한도에 닿았다. `ls /proc/PID/fd | wc -l` 로 확인. 한도 올리고 데몬 재시작.

**증상 2: `FATAL: too many connections for role "app"`**
PostgreSQL이 연결을 거부한다. `pg_stat_activity` 카운트가 max_connections와 비슷하면 확실하다. 단기적으론 max_connections 올리거나 인스턴스 수 줄이고, 중장기적으론 PgBouncer 도입.

**증상 3: `connect: cannot assign requested address` (EADDRNOTAVAIL)**
outbound 커넥션이 안 나간다. ephemeral port 고갈. `ss -tan | wc -l` 로 전체 커넥션 보고, TIME_WAIT 비율 확인. keep-alive 적용 또는 ip_local_port_range 확장 또는 tcp_tw_reuse 켜기.

**증상 4: 트래픽 burst 시 connection refused 가 클라이언트에 뜨는데 앱 로그엔 흔적 없음**
somaxconn / accept queue overflow. `nstat -az TcpExtListenOverflows` 가 증가하는지 확인. `net.core.somaxconn` 올리고 앱의 listen backlog도 같이 올리기.

**증상 5: 컨테이너에서만 ulimit이 1024**
docker --ulimit 또는 K8s 노드의 containerd default ulimits 설정. dockerfile이나 entrypoint에서 ulimit 명령 자체는 hard limit 못 넘기니 무의미하다. 호스트/런타임 설정으로 풀어야 한다.

**증상 6: HPA로 pod 늘었더니 DB 죽음**
pod 수 × pool max 가 DB max_connections 넘은 케이스. 풀러를 도입하거나, 앱 풀 사이즈를 줄이고, HPA max replicas로 곱셈 결과의 상한을 강제로 묶는다.

## 마무리 관점

커넥션 한도는 단일 숫자가 아니라 OS, 커널, 웹서버, 풀러, DB, 앱이 각자 들고 있는 상한들의 최소값이다. 어느 한 레이어에서 "올렸다"고 해서 끝이 아니다. 위아래로 다 따라 올라가야 그 변경이 의미가 있다.

운영 표준은 단순하다. 첫째, 모든 레이어의 현재 한도와 사용량을 메트릭으로 노출한다 (HikariCP active/idle, PgBouncer cl_active, DB pg_stat_activity, fd 사용률, ephemeral port 사용률). 둘째, 한도의 70~80%에서 알람. 셋째, 곱셈을 의식한다 — 인스턴스 수가 변하는 환경에선 풀 사이즈와 인스턴스 max replicas를 함께 본다. 넷째, 풀러는 옵션이 아니라 기본값으로 본다. 인스턴스 수가 가변이면 더더욱 그렇다.
