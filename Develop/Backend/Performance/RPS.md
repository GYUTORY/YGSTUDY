---
title: RPS
tags:
  - Backend
  - Performance
  - RPS
  - Load_Testing
  - Capacity_Planning
updated: 2026-05-21
---

# RPS (Requests Per Second)

서버 성능 얘기하면 거의 매번 등장하는 지표가 RPS다. 그런데 막상 "우리 서버 몇 RPS까지 받을 수 있어요?" 라는 질문을 받으면 답하기가 애매하다. 측정 방법, 측정 시점, 응답시간 분포, 트래픽 패턴에 따라 숫자가 2~3배씩 차이 나기 때문이다. 5년 정도 서비스 운영하면서 RPS 숫자 하나로 결정 내렸다가 장애 난 경험이 한두 번이 아니라, 이 문서에서는 RPS를 어떻게 봐야 하고 어떻게 측정해야 하며 어디서 함정에 빠지는지 정리한다.

## RPS가 뭔가

말 그대로 초당 처리하는 요청 수다. 1초 동안 서버가 받아서 응답까지 끝낸 HTTP 요청의 개수.

여기서 헷갈리는 게 있는데, RPS는 "받은 요청 수"가 아니라 "처리 완료한 요청 수"로 보는 게 맞다. 클라이언트가 1초에 1000번 보냈는데 서버가 800번만 응답했다면 RPS는 800이다. 200개는 큐에 쌓여 있거나 타임아웃 났거나.

### TPS, QPS, 동시접속자와의 차이

| 용어 | 의미 | 주로 쓰는 곳 |
|---|---|---|
| RPS | 초당 처리 요청 수 | HTTP 서버, API 게이트웨이 |
| TPS | 초당 트랜잭션 수 | DB, 결제, 메시지 큐 |
| QPS | 초당 쿼리 수 | 검색 엔진, DB read |
| CCU | 동시 접속자 수 | 게임, 실시간 통신 |

실무에서 자주 겪는 혼동이 있다. RPS와 TPS를 같은 의미로 쓰는 회사도 있고, 결제 시스템처럼 한 요청 안에 여러 DB 트랜잭션이 발생하면 RPS 1000인데 TPS는 3000인 경우도 흔하다. 그래서 "TPS 5000 받아야 한다"는 요구사항을 받으면 "그게 HTTP 요청 기준인지, DB 트랜잭션 기준인지"부터 다시 물어야 한다.

CCU와 RPS의 관계도 자주 잘못 잡는다. 동시접속자 1만 명이라고 RPS 1만이 아니다. 사용자가 평균 10초에 1번씩 요청 보낸다면 RPS는 1000이다. 반대로 폴링이 심한 시스템이면 CCU 100명이 RPS 500을 만들기도 한다.

## Little's Law로 보는 RPS

RPS를 진지하게 다루려면 Little's Law를 외워두는 게 좋다. 큐잉 이론에서 나온 식이지만 서버 용량 산정에 그대로 쓰인다.

```
L = λ × W
```

- L: 시스템 안에 있는 평균 요청 수 (동시 처리 중인 요청, in-flight)
- λ: 도착률 (RPS)
- W: 평균 응답시간

식 자체는 단순하지만 의미가 강력하다. 동시 처리 중인 요청 수는 RPS와 응답시간의 곱이다.

### 실무 계산 예시

평균 응답시간 200ms 서버가 RPS 1000을 처리한다고 하자.

```
L = 1000 × 0.2 = 200
```

즉 평균적으로 200개 요청이 동시에 서버 안에서 처리 중이다. 이 숫자가 의미하는 건 다음과 같다.

- 스레드풀 모델이라면 최소 200개 스레드가 필요하다 (Tomcat 기본 max-threads 200이 왜 그 값인지 짐작 가능)
- 비동기/이벤트 루프 모델이라도 200개의 in-flight 작업을 관리할 수 있어야 한다
- DB 커넥션이 1요청당 1개씩 잡힌다면 커넥션 풀 200이 필요하다

여기서 응답시간이 400ms로 늘어나면 L = 400. 갑자기 동시성이 2배로 뛰는데 서버 리소스(스레드, 커넥션)는 그대로면 큐가 쌓이기 시작한다. 이게 응답시간 증가 → 큐 적체 → 추가 응답시간 증가의 악순환이 시작되는 지점이다.

반대로 응답시간을 100ms로 줄이면 같은 RPS 1000을 처리하는 데 L = 100이면 충분하다. 동시성 부담이 절반이 된다. 그래서 "RPS 늘리려면 응답시간부터 줄여라"는 말이 나온다.

### 캐파 산정에 쓰는 법

서버 한 대가 RPS 500을 처리하고 응답시간 평균 100ms라고 하면, 동시 처리 50개. 만약 목표 RPS가 5000이라면 단순 계산으로 서버 10대. 그런데 실무에선 이 숫자 그대로 안 잡는다. 이유는 뒤에서 설명한다.

## 측정 방법별 함정

RPS 측정에 쓰는 도구가 여러 개인데 같은 서버에 같은 시나리오 돌려도 결과가 다르다.

### k6, wrk, ab, vegeta 차이

| 도구 | 특징 | 측정값이 다른 이유 |
|---|---|---|
| ab (Apache Bench) | 오래된 도구, 단일 스레드 | HTTP/1.0 기본, keep-alive 옵션 안 주면 매번 새 연결 |
| wrk | C로 작성, epoll 기반, 빠름 | 멀티 스레드 + 비동기, keep-alive 기본 |
| k6 | Go 기반, 시나리오 작성 편함 | VU(virtual user) 모델, 사용자 행동 시뮬레이션 |
| vegeta | constant rate 부하 생성에 강함 | 정해진 RPS로 일정하게 보내는 데 특화 |

같은 서버에 ab로 측정하면 RPS 2000, wrk로 측정하면 RPS 8000 나오는 경우가 있다. 이건 서버 성능 차이가 아니라 측정 방식 차이다.

### Connection reuse와 keep-alive

HTTP keep-alive를 안 쓰면 매 요청마다 TCP handshake + TLS handshake가 추가된다. TLS handshake는 RTT 2~3번이 더 든다. 로컬에서 RTT 1ms라면 무시할 수준이지만, 실제 환경에서 클라이언트와 서버가 다른 리전에 있으면 RTT 100ms씩 추가된다. 이 상태에서 측정한 RPS는 서버의 처리 능력이 아니라 핸드셰이크 비용에 묶인 숫자다.

```bash
# ab는 keep-alive를 명시해야 한다
ab -n 10000 -c 100 -k https://api.example.com/users
#                  ^^ keep-alive 켜기

# wrk는 기본이 keep-alive
wrk -t 4 -c 100 -d 30s https://api.example.com/users
```

실제로 운영 환경 RPS 검증할 때 ab만 쓰다가 "이 정도면 충분히 받겠네" 하고 배포했다가, 실제 사용자 트래픽(브라우저는 대부분 keep-alive 사용)과는 패턴이 달라서 다른 병목이 터지는 경우를 본 적 있다.

### 클라이언트 병목

측정 자체가 잘못된 경우가 의외로 많다. 부하 생성기가 못 따라가는 거다.

- 단일 머신에서 wrk 돌렸는데 ephemeral port 고갈 (기본 28k개)
- file descriptor 한도 (`ulimit -n`)에 막힘
- 부하 생성기 CPU가 100% 찍힘
- TCP TIME_WAIT 누적

서버 RPS를 측정한다고 했지만 실제로는 클라이언트가 한계에 부딪힌 거다. RPS 그래프가 평평하게 천장 치는데 서버 CPU는 30%면 거의 100% 클라이언트 병목이다. 부하 생성기를 여러 대로 분산시키거나 (k6의 cloud, vegeta의 distributed mode) 측정 머신 자체 튜닝부터 해야 한다.

```bash
# 측정 머신 사전 체크
ulimit -n 65535
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.ip_local_port_range="1024 65535"
```

## 평균 RPS vs 피크 RPS

운영하다 보면 "우리 서비스 평균 RPS 500이에요" 같은 말을 자주 듣는데, 이 숫자만 보고 캐파 정하면 거의 항상 부족하다.

### 트래픽은 피크가 결정한다

이커머스 푸시 알림 보내는 순간 5초 동안 RPS가 평소의 30배로 튀는 경우가 있다. 24시간 평균은 500이지만 피크는 15000인 거다. 평균 기준으로 서버 잡으면 푸시 보낼 때마다 장애.

피크 RPS를 보는 단위도 중요하다.

- 1분 평균 피크
- 10초 평균 피크
- 1초 spike

1분 평균으로는 평탄해 보여도 1초 단위로 보면 burst가 있는 경우가 흔하다. 그래서 Prometheus에서 `rate()` 윈도우를 짧게 잡고 보는 게 진짜 피크를 잡는 방법이다.

### Latency 분포와 함께 봐야 하는 이유

RPS 1000을 처리한다고 했을 때 응답시간이 어떻게 분포돼 있는지 모르면 의미가 없다.

- 케이스 A: p50 50ms, p95 100ms, p99 150ms — 안정적
- 케이스 B: p50 50ms, p95 200ms, p99 3000ms — 위험

둘 다 RPS 1000이지만 케이스 B는 1%의 사용자가 3초씩 기다리고 있다. 이게 GC pause, lock contention, slow query 같은 문제의 흔적이다. p99가 튀는 RPS는 지속 가능하지 않다. 부하가 조금만 더 늘면 p99가 timeout 영역으로 들어가고 거기서부터 RPS 자체가 무너진다.

p99 또는 p99.9까지 보는 게 실무 감각이다. p95까지만 보고 "괜찮네" 했다가 1만 명 중 100명이 비명 지르는 상황이 자주 생긴다.

### 측정 그래프 예시

```
RPS    p50    p95    p99
500    30ms   60ms   90ms     ← 여유 있음
1000   40ms   80ms   120ms    ← 정상 운영 구간
1500   60ms   200ms  500ms    ← 슬슬 위험
2000   100ms  800ms  3000ms   ← saturation, 더 올리면 무너짐
2200   timeout 발생, RPS가 오히려 감소
```

이 그래프를 그려보는 게 캐파 산정의 출발점이다. 단순히 "RPS 2000까지 나왔다"가 아니라 "p99 200ms 유지하면서 받을 수 있는 RPS가 1000이다"가 의미 있는 숫자다.

## 서버 대수 산정

목표 RPS가 정해졌다면 서버를 몇 대 둘지 계산해야 한다. 단순 나눗셈으로는 부족하다.

### 기본 계산

피크 RPS 10000, 서버 한 대가 안전하게 처리하는 RPS 1000 (p99 SLA 안에서). 그러면 10대?

아니다. 여유율(headroom)을 둬야 한다.

### 여유율 계산

```
필요 서버 대수 = (피크 RPS / 서버당 안전 RPS) × (1 + 여유율) + N+1 redundancy
```

여유율을 얼마로 잡냐는 회사마다 다른데, 일반적으로

- 30%~50% 여유율: 갑작스러운 트래픽 증가, 서버 일부 장애 대응
- N+1 또는 N+2: 한 대 빠져도 SLA 유지
- 배포 중 일시 감소분: rolling deploy면 한 대씩 빠지니까

피크 10000 RPS면 실제로는 15~20대로 운영하는 게 정상이다. 평균 부하가 50% 정도로 유지되는 게 안정적이다. CPU 사용률 80% 넘기면 응답시간이 비선형적으로 늘어나기 시작한다.

### 흔히 빠뜨리는 부분

서버 대수만 늘리면 RPS가 선형으로 늘 거라고 생각하지만 거의 그렇지 않다. 병목이 다른 데로 옮겨가서다.

**GC pause**

JVM 기반이면 G1, ZGC 같은 GC가 돌 때 STW(Stop The World)가 생긴다. 짧게는 10ms, 길게는 수백 ms. 이 시간 동안 그 서버는 요청을 못 받는다. RPS 1000 서버 10대를 두면 통계적으로 어느 한 대는 GC 중일 확률이 있다. 그래서 GC tuning을 안 하면 p99 latency가 GC pause에 묶인다.

**DB connection pool 한계**

서버 늘려도 DB는 한 대다. 서버 10대가 각각 connection pool 50개씩 잡으면 DB는 500 connection을 받는다. PostgreSQL 기본 max_connections가 100인데 이걸 모르고 서버 증설하면 DB가 connection 거절하기 시작한다. pgbouncer 같은 connection pooler를 앞에 두거나 max_connections를 올려야 한다.

**외부 API rate limit**

결제 API, SMS, OAuth 같은 외부 의존성에 rate limit이 걸려 있는 경우. 우리 서버 RPS는 늘릴 수 있어도 외부 API가 RPS 100으로 제한하면 거기서 막힌다. 이건 서버 증설로 해결 안 되고 큐잉, 캐싱, 외부 API 계약 변경 같은 다른 접근이 필요하다.

## RPS가 안 오르는 전형적 병목

부하 테스트 돌리는데 RPS가 어느 선에서 더 안 오르는 상황. 원인을 빠르게 식별하는 방법.

### CPU saturation

가장 단순한 경우. `top`, `htop`, `mpstat`로 확인.

```bash
mpstat -P ALL 1
```

코어가 골고루 100% 찍히면 CPU bound. 이때는 코드 최적화나 수직 스케일링.
한 코어만 100% 찍히면 싱글 스레드 병목. Node.js의 메인 이벤트 루프, 잘못된 GIL 잠금 같은 거. 멀티 프로세스 전략 필요.

### Lock contention

CPU는 안 찼는데 RPS가 안 오른다. 응답시간만 늘어난다. Java면 `jstack`으로 스레드 덤프 떠서 BLOCKED 상태 스레드 확인. `synchronized` 메소드에 모든 스레드가 몰려 있으면 거기가 병목.

```bash
# Java
jstack <pid> | grep -A 5 "BLOCKED"

# Go
go tool pprof http://localhost:6060/debug/pprof/block
```

### DB connection 부족

`HikariPool-1 - Connection is not available, request timed out after 30000ms` 같은 로그가 뜬다. connection pool이 꽉 차서 새 요청이 connection을 못 받는 상태. pool 크기를 늘리거나 (DB max_connection도 같이) 쿼리 시간을 줄여야 한다.

여기서 자주 하는 실수가 connection pool을 무작정 키우는 거다. pool 200으로 늘리면 DB가 더 빨라질 것 같지만, DB CPU가 한정돼 있으면 동시 쿼리만 늘어나서 오히려 전체 처리량이 떨어진다. HikariCP 문서에서도 connection 수는 `((core_count × 2) + effective_spindle_count)` 정도를 권장한다.

### Network bandwidth

대용량 응답을 보내는 API. 응답 1개당 1MB면 RPS 1000은 1GB/s가 나간다. 1Gbps NIC는 125MB/s. 여기서 RPS는 100을 넘을 수 없다. 이런 경우 응답 압축(gzip), 페이지네이션, CDN으로 빼는 게 답이지 서버 증설은 무의미하다.

```bash
# 네트워크 사용량 확인
sar -n DEV 1
ifstat 1
```

### TLS handshake 비용

HTTPS 트래픽에서 새 connection이 많으면 TLS handshake CPU가 무시 못 한다. 특히 RSA 키 기반이면 핸드셰이크당 수 ms의 CPU 시간이 든다. CPU 프로파일링 했는데 OpenSSL 함수들이 상위에 보이면 keep-alive 설정 확인하고, ECDSA 키로 바꾸거나, TLS terminator를 별도 서버(L7 LB, nginx)로 분리하는 걸 고려한다.

## 모니터링 시 RPS 메트릭 함정

Prometheus + Grafana로 RPS 보는 건 흔한데 여기서도 함정이 있다.

### rate() 윈도우 크기

```promql
rate(http_requests_total[1m])
rate(http_requests_total[5m])
```

`rate()`는 윈도우 안의 평균이다. 5분 윈도우로 보면 burst가 평탄해진다. 30초짜리 spike는 1분 윈도우로도 거의 안 보인다.

운영 모니터링이면 1m, 알람용이면 30s 이하로 잡는 게 좋다. 단, 너무 짧게 잡으면 (10s 이하) 데이터 포인트 부족으로 그래프가 noisy해진다.

### 평균과 분포의 차이

대시보드에 RPS 평균만 띄워놓으면 piece-wise 동작을 놓친다. 가능하면 percentile도 같이 보는 게 좋다. 예를 들어 1초 단위 RPS의 p99를 보면 burst가 보인다.

```promql
# 평균 RPS (5분)
rate(http_requests_total[5m])

# 1초 burst 보려면 짧은 윈도우
rate(http_requests_total[15s])

# 분포로 보려면 histogram_quantile
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m]))
```

### 라벨 카디널리티

`status_code`, `endpoint`, `method` 같은 라벨로 RPS를 쪼개 보는 건 유용하지만, 라벨이 너무 많으면 Prometheus 메모리 폭발한다. URL path를 그대로 라벨에 넣어버리는 실수가 흔하다. `/users/123`, `/users/124` 처럼 ID마다 라벨이 생기면 카디널리티가 폭증한다. 반드시 path 템플릿(`/users/:id`)으로 정규화해야 한다.

### counter 재시작 처리

`rate()`는 counter가 리셋되면 (서버 재시작) 자동으로 감지하지만, 짧은 시간에 두 번 리셋되거나 scrape interval보다 짧게 살아있다 죽으면 데이터가 누락된다. 배포 직후 RPS 그래프가 잠깐 0으로 떨어진다면 이게 원인일 수 있다.

## 정리하면서

RPS는 숫자 하나로 끝나는 지표가 아니다. 측정 방법, 응답시간 분포, 트래픽 패턴, 어떤 병목이 먼저 터지는지를 같이 봐야 의미 있는 숫자가 나온다. 부하 테스트로 RPS 5000 뽑아냈다는 결과를 봤다면, 그 옆에 p99 latency가 같이 적혀 있는지, keep-alive를 썼는지, 클라이언트가 충분히 분산돼 있었는지, 한 줄짜리 인증 API였는지 결제 같은 무거운 API였는지 같이 확인해야 한다. 단일 숫자만 보고 캐파를 잡으면 실제 트래픽이 들어왔을 때 다른 데서 터진다.
