---
title: HTTP 커넥션 관리
tags:
  - HTTP
  - Connection
  - Keep-Alive
  - Connection Pool
  - TCP
  - Nginx
  - Spring
updated: 2026-03-30
---

# HTTP 커넥션 관리

HTTP 통신은 결국 TCP 커넥션 위에서 동작한다. 요청마다 TCP 3-way handshake를 하면 RTT(Round Trip Time)가 누적되고, 트래픽이 몰리면 서버 소켓이 부족해지는 상황이 생긴다. 커넥션을 어떻게 열고, 유지하고, 반환하느냐에 따라 응답 시간과 서버 안정성이 크게 달라진다.

---

## Keep-Alive

### 동작 원리

HTTP/1.0에서는 요청 하나를 보내고 응답을 받으면 TCP 커넥션을 바로 끊었다. HTTP/1.1부터는 기본적으로 Keep-Alive가 켜져 있어서, 하나의 TCP 커넥션으로 여러 요청/응답을 주고받는다.

```
# HTTP/1.1 요청 — Connection 헤더를 안 보내도 Keep-Alive가 기본
GET /api/users HTTP/1.1
Host: example.com

# 서버 응답
HTTP/1.1 200 OK
Connection: keep-alive
Keep-Alive: timeout=60, max=100
```

`timeout=60`은 유휴 상태로 60초가 지나면 서버가 커넥션을 닫겠다는 뜻이고, `max=100`은 이 커넥션으로 최대 100개 요청까지 처리하겠다는 뜻이다.

### 타임아웃 튜닝

Keep-Alive 타임아웃이 너무 길면 유휴 커넥션이 서버 메모리와 파일 디스크립터를 잡아먹는다. 너무 짧으면 커넥션을 자주 맺어서 latency가 올라간다.

실무에서 겪는 상황:

- API 서버처럼 요청이 계속 들어오는 경우: 타임아웃 60~120초 정도가 적당하다
- 간헐적으로 요청이 오는 배치 연동: 타임아웃 10~30초로 짧게 잡는다. 안 그러면 서버에 좀비 커넥션만 쌓인다
- 로드밸런서 뒤에 있는 경우: **로드밸런서의 idle timeout보다 서버의 keep-alive timeout을 길게** 설정해야 한다. 서버가 먼저 끊어버리면 로드밸런서가 이미 닫힌 커넥션으로 요청을 보내서 502 에러가 터진다

AWS ALB의 기본 idle timeout은 60초다. 그래서 Nginx의 `keepalive_timeout`을 65초 이상으로 잡는 게 일반적이다.

---

## 커넥션 풀링

매 요청마다 TCP 커넥션을 새로 맺는 건 비용이 크다. 커넥션 풀은 미리 만들어둔 커넥션을 빌려 쓰고 반환하는 방식으로 이 비용을 줄인다.

### Apache HttpClient 커넥션 풀

Java에서 외부 API를 호출할 때 가장 많이 쓰는 조합이다.

```java
PoolingHttpClientConnectionManager connManager =
    new PoolingHttpClientConnectionManager();

// 전체 커넥션 풀 최대 크기
connManager.setMaxTotal(200);

// 특정 호스트(route)당 최대 커넥션 수
connManager.setDefaultMaxPerRoute(20);

CloseableHttpClient httpClient = HttpClients.custom()
    .setConnectionManager(connManager)
    .setKeepAliveStrategy((response, context) -> {
        // 서버가 Keep-Alive 헤더를 안 보내면 30초로 설정
        HeaderElementIterator it = new BasicHeaderElementIterator(
            response.headerIterator(HTTP.CONN_KEEP_ALIVE));
        while (it.hasNext()) {
            HeaderElement he = it.nextElement();
            if ("timeout".equalsIgnoreCase(he.getName())) {
                return Long.parseLong(he.getValue()) * 1000;
            }
        }
        return 30 * 1000L;
    })
    .build();
```

`setMaxTotal(200)`으로 풀 전체 크기를 잡고, `setDefaultMaxPerRoute(20)`으로 호스트당 커넥션 수를 제한한다. 외부 API가 하나뿐이면 `MaxPerRoute`를 `MaxTotal`에 가깝게 올려도 된다. 여러 호스트를 호출하는데 `MaxPerRoute`가 작으면 특정 호스트로의 요청이 풀에서 커넥션을 못 받아서 대기하게 된다.

주의할 점: `MaxTotal`을 무작정 크게 잡으면 안 된다. 커넥션 하나당 소켓 하나이고, 소켓은 파일 디스크립터를 소비한다. `ulimit -n`으로 확인한 프로세스 최대 fd 수를 넘으면 `Too many open files` 에러가 난다.

### HikariCP (DB 커넥션 풀)

HTTP 커넥션은 아니지만, 커넥션 풀링 개념은 동일하다. DB 커넥션 풀에서 겪는 문제가 HTTP 커넥션 풀에서도 그대로 나타난다.

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      idle-timeout: 300000      # 유휴 커넥션 5분 후 제거
      max-lifetime: 1800000     # 커넥션 최대 수명 30분
      connection-timeout: 3000  # 풀에서 커넥션 못 받으면 3초 후 예외
```

`maximum-pool-size`는 생각보다 작게 잡아야 한다. HikariCP 공식 문서에서도 `connections = (core_count * 2) + effective_spindle_count` 공식을 권장한다. 풀 크기가 클수록 DB 서버의 커넥션 수도 늘어나고, DB 쪽에서 컨텍스트 스위칭 비용이 커진다.

`max-lifetime`은 DB 서버의 `wait_timeout`보다 짧게 설정한다. DB가 먼저 커넥션을 끊어버리면 애플리케이션이 끊어진 커넥션으로 쿼리를 보내서 `Connection is closed` 에러가 발생한다. MySQL 기본 `wait_timeout`이 28800초(8시간)이니까 HikariCP의 `max-lifetime`은 1800초(30분) 정도가 안전하다.

### Spring WebClient 커넥션 풀 (Reactor Netty)

```java
ConnectionProvider provider = ConnectionProvider.builder("custom")
    .maxConnections(500)            // 전체 최대 커넥션
    .maxIdleTime(Duration.ofSeconds(20))  // 유휴 커넥션 제거 시간
    .maxLifeTime(Duration.ofSeconds(60))  // 커넥션 최대 수명
    .pendingAcquireTimeout(Duration.ofSeconds(5))  // 풀에서 대기 최대 시간
    .evictInBackground(Duration.ofSeconds(30))     // 백그라운드 정리 주기
    .build();

HttpClient httpClient = HttpClient.create(provider);

WebClient webClient = WebClient.builder()
    .clientConnector(new ReactorClientHttpConnector(httpClient))
    .build();
```

`evictInBackground`를 설정하지 않으면 만료된 커넥션이 실제 요청이 올 때까지 풀에 남아 있는다. 주기적으로 정리해야 오래된 커넥션으로 요청이 나가는 걸 방지할 수 있다.

---

## 브라우저 커넥션 제한

브라우저는 동일 도메인에 대해 동시 커넥션 수를 제한한다. Chrome, Firefox, Edge 모두 **도메인당 최대 6개**다. 이 제한은 HTTP/1.1에서만 적용되고, HTTP/2에서는 하나의 커넥션으로 다중 스트림을 쓰기 때문에 의미가 달라진다.

실무에서 이게 문제되는 경우:

- 이미지, CSS, JS 등 정적 파일이 많은 페이지에서 동시 로딩이 6개로 제한된다
- API 요청과 정적 리소스 요청이 같은 도메인을 쓰면 서로 커넥션을 경쟁한다
- SSE(Server-Sent Events)나 long polling 커넥션이 열려 있으면 그만큼 가용 커넥션이 줄어든다. SSE 2개만 열어도 남은 건 4개다

대응 방법:

- 정적 파일은 CDN 도메인을 분리한다 (`static.example.com`)
- HTTP/2를 적용하면 하나의 커넥션에서 수백 개의 요청을 병렬로 처리할 수 있다
- SSE 대신 WebSocket을 쓰면 HTTP 커넥션 수에 영향을 주지 않는다 (WebSocket은 Upgrade 후 별도 프로토콜)

---

## Nginx 커넥션 설정

### 클라이언트 → Nginx

```nginx
http {
    # 클라이언트와의 Keep-Alive 설정
    keepalive_timeout 65;        # 유휴 커넥션 타임아웃 (초)
    keepalive_requests 1000;     # 하나의 커넥션으로 처리할 최대 요청 수

    # 워커 프로세스당 최대 커넥션 수
    # worker_processes * worker_connections = 동시 처리 가능한 전체 커넥션 수
    events {
        worker_connections 1024;
    }
}
```

`keepalive_requests`가 기본값 100인데, 트래픽이 많으면 이 값 때문에 커넥션이 자주 끊기고 다시 맺는 오버헤드가 생긴다. 트래픽이 많은 서비스에서는 1000 이상으로 올리는 게 일반적이다.

### Nginx → 업스트림(WAS)

```nginx
upstream backend {
    server 127.0.0.1:8080;

    # 업스트림으로의 Keep-Alive 커넥션 풀
    keepalive 32;              # 유휴 상태로 유지할 커넥션 수
    keepalive_requests 100;    # 커넥션당 최대 요청 수
    keepalive_timeout 60s;     # 유휴 커넥션 타임아웃
}

server {
    location /api/ {
        proxy_pass http://backend;

        # 업스트림 Keep-Alive를 쓰려면 반드시 아래 두 줄이 필요하다
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

여기서 가장 많이 하는 실수가 `proxy_http_version 1.1`과 `proxy_set_header Connection ""`을 빠뜨리는 것이다. 이걸 안 넣으면 Nginx가 업스트림으로 HTTP/1.0으로 요청을 보내서 매번 커넥션을 새로 맺는다. `keepalive 32`를 설정해놓고 왜 안 되지 하는 경우가 대부분 이것 때문이다.

`keepalive 32`에서 32는 풀 크기가 아니라 **유휴 상태로 캐시해둘 커넥션 수**다. 실제로는 이보다 더 많은 커넥션이 열릴 수 있다.

---

## Spring Boot 커넥션 설정

### 내장 Tomcat

```yaml
server:
  tomcat:
    max-connections: 8192       # 서버가 수락할 최대 커넥션 수
    accept-count: 100           # max-connections 초과 시 대기 큐 크기
    threads:
      max: 200                  # 요청 처리 스레드 수
    keep-alive-timeout: 60000   # Keep-Alive 타임아웃 (ms)
    max-keep-alive-requests: 100  # 커넥션당 최대 요청 수
  connection-timeout: 20000     # 커넥션 수립 후 첫 데이터 대기 시간 (ms)
```

`max-connections`와 `threads.max`의 관계를 이해해야 한다. `max-connections`는 TCP 레벨에서 수락할 커넥션 수이고, `threads.max`는 실제 요청을 처리할 워커 스레드 수다. 커넥션이 8192개 열려 있어도 동시에 처리되는 요청은 200개뿐이다. 나머지는 대기한다.

### Spring WebFlux (Reactor Netty 서버)

```yaml
server:
  netty:
    connection-timeout: 20000
    idle-timeout: 60000
```

Netty 기반이라 스레드 모델이 다르다. 이벤트 루프가 커넥션을 논블로킹으로 처리하기 때문에 동시 커넥션 수가 훨씬 많아도 버틸 수 있다. 다만 블로킹 호출(JDBC 등)이 섞이면 이벤트 루프가 막히면서 전체 성능이 급격히 떨어진다.

---

## 커넥션 누수 디버깅

커넥션 누수는 커넥션을 빌려 쓰고 반환하지 않는 상황이다. 풀의 커넥션이 고갈되면 새 요청이 대기하다가 타임아웃으로 실패한다.

### 증상

- `ConnectionPoolTimeoutException` 또는 `PoolAcquireTimeoutException` 발생
- 애플리케이션 시작 후 시간이 지나면서 점점 느려지다가 먹통이 됨
- 서버를 재시작하면 잠시 괜찮다가 다시 느려짐

### 원인과 해결

**Apache HttpClient에서 응답 스트림을 닫지 않는 경우:**

```java
// 잘못된 코드 — response를 닫지 않으면 커넥션이 풀에 반환되지 않는다
CloseableHttpResponse response = httpClient.execute(new HttpGet(url));
String body = EntityUtils.toString(response.getEntity());
// response.close()를 안 하면 커넥션 누수

// 올바른 코드
try (CloseableHttpResponse response = httpClient.execute(new HttpGet(url))) {
    String body = EntityUtils.toString(response.getEntity());
}
```

**RestTemplate에서 응답을 완전히 소비하지 않는 경우:**

```java
// ClientHttpResponse의 body를 일부만 읽고 버리면 커넥션이 제대로 반환되지 않는다
// RestTemplate을 쓸 때는 exchange()보다 getForObject(), getForEntity()를 쓰는 게 안전하다
```

**HikariCP 커넥션 누수 탐지:**

```yaml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 5000  # 5초 이상 반환 안 되면 경고 로그
```

이 설정을 켜면 커넥션을 체크아웃한 지 5초가 넘도록 반환하지 않으면 스택 트레이스와 함께 경고 로그가 찍힌다. 어디서 커넥션을 물고 있는지 바로 찾을 수 있다.

### 모니터링

```java
// Apache HttpClient 커넥션 풀 상태 확인
PoolingHttpClientConnectionManager cm = ...;
PoolStats stats = cm.getTotalStats();
log.info("Leased: {}, Pending: {}, Available: {}, Max: {}",
    stats.getLeased(),    // 현재 사용 중인 커넥션
    stats.getPending(),   // 대기 중인 요청
    stats.getAvailable(), // 풀에서 쉬고 있는 커넥션
    stats.getMax());      // 최대 커넥션 수
```

`Leased`가 계속 올라가고 `Available`이 0에 가까우면 누수를 의심해야 한다.

---

## TIME_WAIT 문제

### TIME_WAIT란

TCP 커넥션을 먼저 끊는 쪽(active close)에서 `TIME_WAIT` 상태로 일정 시간 대기한다. Linux에서 기본 60초(2 * MSL)다. 이 시간 동안 같은 소스 IP:포트 → 목적지 IP:포트 조합을 재사용하지 못한다.

### 문제 상황

서버가 짧은 시간에 외부 API를 대량으로 호출하면 로컬 포트가 고갈된다. 리눅스의 ephemeral port 범위가 기본 `32768~60999`이니까 약 28000개다. 초당 500건씩 외부 호출을 하면 60초 만에 30000개의 포트가 `TIME_WAIT`에 걸린다.

```bash
# TIME_WAIT 상태 커넥션 수 확인
ss -s | grep -i time-wait

# 특정 목적지로의 TIME_WAIT 확인
ss -tan state time-wait | grep "10.0.1.50"
```

### 해결 방법

**1. 커넥션 풀 사용 (근본적인 해결)**

커넥션을 재사용하면 새 커넥션을 맺고 끊는 빈도 자체가 줄어든다. 위에서 설명한 HttpClient 커넥션 풀이나 Nginx upstream keepalive가 여기에 해당한다.

**2. 커널 파라미터 튜닝**

```bash
# /etc/sysctl.conf

# TIME_WAIT 상태의 소켓을 새 커넥션에 재사용
net.ipv4.tcp_tw_reuse = 1

# ephemeral port 범위 확장
net.ipv4.ip_local_port_range = 1024 65535

# FIN_WAIT 타임아웃 단축 (기본 60초)
net.ipv4.tcp_fin_timeout = 15
```

`tcp_tw_reuse`는 클라이언트 측(outgoing connection)에서만 동작한다. 서버가 외부 API를 호출하는 경우에 해당한다. `tcp_tw_recycle`은 NAT 환경에서 패킷 드롭을 일으키기 때문에 쓰면 안 된다. Linux 4.12부터는 아예 제거됐다.

**3. SO_LINGER 설정 (주의 필요)**

```java
// 커넥션을 RST로 즉시 끊어서 TIME_WAIT를 건너뛴다
// 데이터 유실 가능성이 있으므로 신중하게 써야 한다
socket.setSoLinger(true, 0);
```

이 방법은 TCP 정상 종료(FIN) 대신 RST 패킷을 보내서 커넥션을 즉시 종료한다. `TIME_WAIT` 자체가 생기지 않지만, 전송 중인 데이터가 유실될 수 있다. 로그 수집이나 메트릭 전송처럼 일부 유실이 허용되는 경우에만 쓴다.

---

## 정리

커넥션 관리에서 문제가 생기면 대부분 이 패턴이다:

1. **타임아웃 불일치**: 로드밸런서, 웹서버, WAS, DB 각 레이어의 타임아웃이 안 맞아서 한쪽이 먼저 끊고 다른 쪽이 끊어진 커넥션에 요청을 보낸다
2. **풀 크기 부적절**: 풀이 작으면 대기가 길어지고, 크면 리소스를 낭비하거나 대상 서버에 부담을 준다
3. **커넥션 미반환**: try-with-resources를 안 쓰거나 예외 경로에서 close를 빠뜨려서 풀이 고갈된다
4. **TIME_WAIT 누적**: 커넥션 풀 없이 대량 호출을 하면 로컬 포트가 고갈된다

트래픽이 적을 때는 기본 설정으로도 문제없지만, 트래픽이 늘면서 하나씩 터지기 시작한다. `ss`, `netstat`, 커넥션 풀 메트릭을 주기적으로 확인하는 습관이 필요하다.
