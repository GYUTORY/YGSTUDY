---
title: QoS와 트래픽 셰이핑 (Traffic Shaping)
tags: [network, qos, traffic-shaping, dscp, tc, bandwidth]
updated: 2026-06-22
---

# QoS와 트래픽 셰이핑

대역폭은 유한한데 트래픽은 종류가 다양하다. VoIP 패킷은 200ms만 늦어도 통화가 끊긴 것처럼 들리고, 백업 트래픽은 30분 늦게 끝나도 아무도 모른다. 이 둘이 같은 회선을 쓸 때 누구를 먼저 보낼지 정하는 게 QoS(Quality of Service)다. 트래픽 셰이핑은 그 QoS를 구현하는 방법 중 하나로, 패킷이 나가는 속도 자체를 인위적으로 조절한다.

백엔드 개발자가 라우터 QoS를 직접 설정할 일은 많지 않다. 그런데 컨테이너 네트워크 대역폭을 제한하거나, 사내 회선에서 특정 서비스가 대역폭을 다 먹는 문제를 추적하거나, API 게이트웨이에서 rate limit을 거는 순간 여기서 다루는 개념과 똑같은 문제를 만난다. Token Bucket이 왜 burst를 허용하는지 모르면 rate limiter 튜닝도 감으로 하게 된다.

---

## QoS가 건드리는 4가지 지표

QoS는 결국 네 가지 숫자를 조정하는 일이다.

- **대역폭(bandwidth)**: 초당 보낼 수 있는 양. Mbps.
- **지연(latency)**: 패킷이 출발해서 도착할 때까지 걸리는 시간. ms.
- **지터(jitter)**: 지연이 들쭉날쭉한 정도. 패킷마다 도착 간격이 일정하지 않으면 지터가 크다.
- **패킷 손실(loss)**: 큐가 꽉 차서 버려지는 비율.

서비스마다 민감한 지표가 다르다. VoIP는 지연과 지터에 예민하지만 대역폭은 적게 쓴다(코덱에 따라 64kbps 수준). 대용량 파일 전송은 지연이 좀 길어도 상관없지만 대역폭을 많이 요구한다. QoS 설계의 출발점은 "어떤 트래픽이 어떤 지표에 민감한가"를 분류하는 것이다.

---

## DSCP/ToS 마킹 — 패킷에 우선순위를 적는다

라우터가 패킷을 차별하려면 어떤 패킷이 중요한지 알아야 한다. IP 헤더에는 이걸 적는 칸이 있다. 원래 IPv4의 ToS(Type of Service) 필드였는데, 지금은 DSCP(Differentiated Services Code Point)로 재정의됐다.

IP 헤더 두 번째 바이트 8비트를 이렇게 쓴다.

```
원래 ToS:   [ Precedence(3) | ToS(4) | unused(1) ]
현재 DSCP:  [    DSCP(6)              | ECN(2)     ]
```

DSCP 6비트로 0~63 값을 표현한다. 자주 쓰는 값에는 이름이 붙어 있다.

| DSCP 이름 | 값(10진) | 용도 |
|---|---|---|
| EF (Expedited Forwarding) | 46 | VoIP 등 지연에 민감한 실시간 트래픽 |
| AF41 | 34 | 영상 회의 |
| AF21 | 18 | 우선순위 있는 데이터 |
| CS0 / Default | 0 | 일반 트래픽(best effort) |

중요한 건, **마킹 자체는 아무 일도 하지 않는다는 점이다**. 패킷에 EF(46)라고 적어도 라우터가 그 값을 보고 우선 처리하도록 설정돼 있지 않으면 일반 패킷과 똑같이 취급된다. 마킹은 "이 패킷은 이런 등급이다"라는 라벨일 뿐이고, 실제 차별은 각 라우터의 큐잉 정책이 한다.

또 하나 자주 빠지는 함정. DSCP는 라우터 경계를 넘으면 리셋되는 경우가 많다. 사내망에서 EF로 마킹해도 ISP 라우터에 들어가는 순간 0으로 덮어쓰여 나온다. 인터넷 구간 전체에 QoS를 기대하면 안 되고, 내가 제어하는 구간(사내망, 데이터센터 내부) 안에서만 의미가 있다.

리눅스에서 소켓에 DSCP를 찍으려면 `IP_TOS` 옵션을 쓴다.

```c
int tos = 46 << 2;  // DSCP 46(EF). DSCP는 상위 6비트라 2비트 시프트
setsockopt(fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos));
```

여기서 `<< 2`를 빼먹는 실수가 흔하다. `IP_TOS`는 8비트 전체를 받는데 DSCP는 상위 6비트라서 값을 2칸 왼쪽으로 밀어야 한다. 46을 그대로 넣으면 DSCP 11이 찍힌다.

---

## 큐잉 규율 — 패킷을 내보내는 순서

라우터나 호스트의 네트워크 인터페이스에는 보낼 패킷을 잠깐 쌓아두는 큐가 있다. 회선이 보낼 수 있는 속도보다 패킷이 빨리 들어오면 큐에 쌓이고, 큐가 꽉 차면 버린다. 이 큐에서 어떤 순서로 꺼낼지 정하는 규칙이 큐잉 규율(queuing discipline)이다.

### FIFO

들어온 순서대로 내보낸다. 단순하고 빠르지만 차별이 없다. 큰 파일 다운로드 패킷이 큐를 가득 채우면 그 뒤에 도착한 VoIP 패킷은 앞 패킷들이 다 나갈 때까지 기다린다. QoS가 필요 없는 환경의 기본값이다.

### WFQ (Weighted Fair Queuing)

플로우(출발지/목적지 IP와 포트 조합)별로 큐를 나누고, 각 큐에서 번갈아 꺼낸다. 한 플로우가 대역폭을 독점하지 못한다. 가중치를 주면 특정 플로우에 더 많은 몫을 배분한다. 대용량 다운로드 한 개가 VoIP 한 개와 회선을 나눠 쓸 때, FIFO면 다운로드가 거의 다 먹지만 WFQ면 둘이 공평하게(또는 가중치대로) 나눈다.

### CBQ / HTB (Class-Based Queuing)

트래픽을 클래스로 나누고 각 클래스에 대역폭을 할당한다. "웹 트래픽 40%, VoIP 10%, 나머지 50%" 같은 식이다. 한 클래스가 자기 몫을 안 쓰면 다른 클래스가 빌려 쓸 수 있게(borrowing) 설정하는 게 보통이다. 리눅스 `tc`에서는 CBQ보다 HTB(Hierarchical Token Bucket)를 주로 쓴다. CBQ는 계산 방식이 복잡하고 부정확해서 사실상 HTB로 대체됐다.

실무에서 계층 구조를 이렇게 짠다.

```
            전체 1Gbps
           /     |      \
        VoIP   웹(API)   백업
        100M    600M     300M
```

VoIP가 100M를 다 안 쓰면 웹과 백업이 그 여유분을 빌려 쓰고, VoIP 트래픽이 들어오면 다시 회수한다. 이 "빌려주되 필요하면 회수"가 HTB의 핵심이고, 고정 할당만 하는 단순 셰이핑과의 차이다.

---

## Token Bucket vs Leaky Bucket

속도를 제한하는 알고리즘은 크게 두 가지다. 이름이 비슷해서 헷갈리는데 동작이 다르다.

### Leaky Bucket (누수 버킷)

밑에 구멍 뚫린 양동이를 떠올린다. 패킷이 위에서 들어와 양동이에 고이고, 구멍으로 일정한 속도로만 빠져나간다. 양동이가 넘치면 들어온 패킷을 버린다.

핵심은 **출력 속도가 항상 일정하다는 것**이다. 입력이 아무리 몰려도 나가는 건 초당 정해진 양뿐이다. burst를 흡수하지 않고 평탄하게 만든다. 출력이 일정해야 하는 곳, 예를 들어 일정한 비트레이트로 내보내야 하는 미디어 스트림에 맞는다.

### Token Bucket (토큰 버킷)

이쪽은 토큰을 담는 양동이다. 일정한 속도로 토큰이 양동이에 채워진다(초당 r개). 패킷을 보내려면 토큰을 하나 써야 한다. 토큰이 있으면 즉시 보내고, 없으면 기다리거나 버린다. 양동이 크기는 b로, 최대 b개까지 토큰이 쌓인다.

차이는 여기다. 한동안 트래픽이 없었으면 토큰이 b개까지 차 있다가, 트래픽이 갑자기 몰리면 **쌓인 토큰만큼 한꺼번에 보낼 수 있다**. 즉 burst를 허용한다. 평균 속도는 r로 제한되지만 순간적으로는 b만큼 튀는 걸 봐준다.

```
Leaky Bucket:  입력 [||||  ||||]  →  출력 [| | | | | | | |]   (항상 평탄)
Token Bucket:  입력 [||||  ||||]  →  출력 [|||| _ _ |||| ]    (burst 허용, 평균은 제한)
```

대부분의 rate limiter(API 게이트웨이, nginx `limit_req`의 burst 옵션, 클라우드 API 쿼터)는 Token Bucket이다. 사용자가 평소엔 조용하다가 가끔 몰아서 요청하는 패턴을 자연스럽게 받아주기 때문이다. 평균 RPS만 제한하고 짧은 burst는 허용하고 싶다면 Token Bucket을 쓰는 게 맞다.

이걸 모르고 rate limit을 설계하면 "평균은 안 넘었는데 왜 막혔지" 또는 "burst를 막고 싶은데 왜 통과되지" 같은 혼란을 겪는다. burst 허용 여부가 두 알고리즘을 가르는 기준이다.

---

## 폴리싱과 셰이핑의 차이

둘 다 속도를 제한하는데, 한도를 초과한 트래픽을 어떻게 처리하느냐가 다르다.

- **폴리싱(Policing)**: 한도 초과분을 **버린다**(또는 DSCP를 낮춰서 재마킹). 큐에 쌓지 않으므로 지연이 늘지 않는다. 대신 손실이 생긴다.
- **셰이핑(Shaping)**: 한도 초과분을 **큐에 쌓았다가 천천히 내보낸다**. 버리지 않으니 손실은 적지만, 큐에서 기다리는 만큼 지연이 늘고 버퍼 메모리를 쓴다.

```
원본 트래픽:  __/‾‾\__/‾‾\__   (튀는 burst)

폴리싱:       __/‾|__/‾|__     (한도 위는 잘라서 버림)
셰이핑:       __/‾‾‾‾‾‾‾\__    (큐에 담아 평탄하게, 시간 지연됨)
```

TCP 트래픽에는 셰이핑이 보통 낫다. 폴리싱으로 패킷을 버리면 TCP가 재전송하면서 혼잡 윈도우를 줄이고, 결과적으로 처리량이 톱니처럼 출렁인다. 셰이핑은 패킷을 버리지 않고 늦출 뿐이라 TCP가 자연스럽게 속도를 맞춘다.

반대로 폴리싱은 입력단에서 빠르게 처리해야 하거나(셰이핑용 버퍼를 둘 수 없는 곳), 초과 트래픽을 확실히 끊어야 할 때 쓴다. ISP가 고객 회선 속도를 강제할 때 흔히 폴리싱을 쓴다.

---

## Linux tc 실무 예제

리눅스에서 트래픽 제어는 `tc`(traffic control) 명령으로 한다. 개념은 qdisc(큐잉 규율) → class(클래스) → filter(필터) 세 단계다. qdisc를 인터페이스에 붙이고, 그 안에 클래스로 대역폭을 나누고, 필터로 어떤 패킷을 어느 클래스에 넣을지 정한다.

주의할 점부터. `tc`는 기본적으로 **나가는(egress) 트래픽만** 제어한다. 들어오는 트래픽은 이미 회선을 통과한 뒤라 셰이핑할 수 없고, 폴리싱(초과분 폐기)만 제한적으로 가능하다. 다운로드 속도를 제한하고 싶으면 송신 쪽 장비에서 걸거나 ifb(중간 가상 디바이스)로 우회해야 한다.

### 단순 대역폭 제한 (TBF)

eth0의 송신 속도를 1Mbps로 제한한다. TBF는 Token Bucket Filter다.

```bash
tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms
```

- `rate 1mbit`: 평균 속도 1Mbps
- `burst 32kbit`: 토큰 버킷 크기. 한 번에 튈 수 있는 양
- `latency 400ms`: 패킷이 큐에서 최대 기다리는 시간. 이걸 넘으면 버린다

`burst`를 너무 작게 잡으면 토큰 보충이 패킷 속도를 못 따라가 실제 throughput이 설정값보다 낮게 나온다. 고속 회선일수록 burst를 키워야 한다. 1Mbps에 burst를 1kbit로 잡으면 제대로 안 나온다.

### HTB로 클래스 나누기

위에서 본 계층 구조를 실제로 구성한다. 전체 1Gbps를 VoIP/API/백업으로 나눈다.

```bash
# 루트 qdisc를 HTB로
tc qdisc add dev eth0 root handle 1: htb default 30

# 부모 클래스: 전체 1Gbps
tc class add dev eth0 parent 1: classid 1:1 htb rate 1000mbit

# 자식 클래스 3개. rate=보장값, ceil=빌려서 최대 쓸 수 있는 값
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 100mbit ceil 1000mbit  # VoIP
tc class add dev eth0 parent 1:1 classid 1:20 htb rate 600mbit ceil 1000mbit  # API
tc class add dev eth0 parent 1:1 classid 1:30 htb rate 300mbit ceil 1000mbit  # 백업(default)

# 필터: DSCP EF(46)는 VoIP 클래스로
tc filter add dev eth0 parent 1: protocol ip prio 1 \
    u32 match ip tos 0xb8 0xfc flowid 1:10

# 필터: TCP 8080 포트(API)는 API 클래스로
tc filter add dev eth0 parent 1: protocol ip prio 2 \
    u32 match ip dport 8080 0xffff flowid 1:20
```

`rate`와 `ceil`의 관계가 HTB의 전부다. `rate`는 그 클래스가 항상 보장받는 대역폭이고, `ceil`은 다른 클래스가 놀고 있을 때 빌려서 쓸 수 있는 상한이다. VoIP는 100M를 보장받지만 회선이 한가하면 1000M까지 끌어 쓴다. 모든 클래스의 `rate` 합은 부모의 `rate`를 넘으면 안 된다(넘으면 보장이 깨진다).

DSCP 필터의 `match ip tos 0xb8 0xfc`가 헷갈리는데, EF(46)를 2비트 시프트하면 0xb8이고, 마스크 0xfc는 하위 2비트(ECN)를 무시하고 DSCP 6비트만 비교하라는 뜻이다.

### 인위적으로 지연/손실 넣기 (netem)

QoS 설정 자체는 아니지만, 네트워크 장애 상황을 재현할 때 같은 `tc`로 한다. 백엔드 테스트에서 자주 쓴다.

```bash
# 100ms 지연 + 10ms 지터 + 0.1% 패킷 손실
tc qdisc add dev eth0 root netem delay 100ms 10ms loss 0.1%
```

해외 리전과 통신하는 서비스의 타임아웃 설정이 맞는지, 패킷 손실 상황에서 재시도 로직이 도는지 로컬에서 확인할 때 쓴다. 테스트 끝나면 반드시 `tc qdisc del dev eth0 root`로 지운다. 안 지우면 그 장비의 모든 트래픽이 계속 느려진다.

### 설정 확인과 삭제

```bash
tc qdisc show dev eth0        # 적용된 qdisc 확인
tc class show dev eth0        # 클래스별 상태
tc -s class show dev eth0     # 통계 포함(전송량, 드롭 수)
tc qdisc del dev eth0 root    # 전부 제거
```

`tc -s class show`의 드롭 카운터를 봐야 한다. 셰이핑이 의도대로 도는지, 어느 클래스에서 패킷이 버려지는지 여기서 드러난다.

---

## 우선순위 보장이 필요한 상황

### VoIP / 영상 통화

지연과 지터에 가장 민감하다. 음성 패킷이 150ms 안에 도착하지 못하면 통화 품질이 떨어지고, 도착 간격이 들쭉날쭉하면(지터) 끊긴 것처럼 들린다. 대역폭 자체는 적게 쓰니까(통화당 수십 kbps) EF로 마킹해서 큐 맨 앞으로 보내는 게 정석이다. 대용량 백업이 회선을 채워도 VoIP 패킷은 먼저 나가야 한다.

### 실시간 스트리밍

라이브 방송 송출처럼 일정한 비트레이트를 유지해야 하는 경우, 출력을 평탄하게 만드는 셰이핑(또는 Leaky Bucket류)이 맞는다. VOD 다운로드는 버퍼가 있으니 지연에 관대하지만, 라이브는 버퍼를 짧게 가져가야 해서 안정적인 대역폭이 더 중요하다.

### 회선을 공유하는 사무실

화상회의 중에 누군가 대용량 파일을 올리면 회의가 끊긴다. HTB로 회의 트래픽에 대역폭을 보장하고 백업/업로드를 나머지로 묶으면 해결된다. 사내 회선에서 가장 흔한 QoS 적용 사례다.

---

## 백엔드에서 마주치는 throttling

QoS의 패킷 레벨 개념이 애플리케이션 레벨에서 그대로 반복된다. 이름만 rate limiting, throttling으로 바뀐다.

### API rate limiting

API 게이트웨이나 nginx의 rate limit이 사실상 Token Bucket이다. nginx 예시.

```nginx
# 평균 10req/s, zone 메모리 10MB
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
    }
}
```

`rate=10r/s`가 토큰 보충 속도, `burst=20`이 버킷 크기다. 평소 10req/s를 넘지 않게 하되 순간적으로 20개까지 몰리는 건 받아준다. `nodelay`를 빼면 셰이핑처럼 동작해서 burst를 큐에 쌓아 천천히 처리하고, `nodelay`를 붙이면 burst를 즉시 통과시키되 그만큼 토큰을 미리 당겨 쓴다. 이 차이가 폴리싱 vs 셰이핑과 정확히 같은 구조다.

### 메시지 큐 / 외부 API 호출

외부 결제 API가 "초당 50건"으로 제한을 걸면 우리 쪽에서 호출 속도를 맞춰야 한다. 안 그러면 429를 맞고 재시도가 쌓여 상황이 더 나빠진다. 이때 애플리케이션 안에 Token Bucket을 두고 토큰이 있을 때만 호출한다. Guava의 `RateLimiter`, Resilience4j의 `RateLimiter`가 이 구현이다.

```java
// Guava RateLimiter: 초당 50건
RateLimiter limiter = RateLimiter.create(50.0);

public PaymentResult call() {
    limiter.acquire();  // 토큰 없으면 블록
    return paymentApi.charge(...);
}
```

여러 인스턴스가 같은 외부 API를 호출하면 인스턴스마다 로컬 RateLimiter를 두는 것으로는 부족하다. 전체 호출량의 합이 한도를 넘기 때문이다. 이 경우 Redis에 토큰 버킷을 두고 분산 rate limiter를 만들거나, 한도를 인스턴스 수로 나눠 배분한다.

### 커넥션 풀과 동시성 제한

DB 커넥션 풀의 max size, 스레드 풀의 크기, 세마포어로 거는 동시 처리 제한도 결국 같은 문제다. 자원은 유한하고, 초과 요청을 버릴지(폴리싱: 즉시 실패 반환) 대기시킬지(셰이핑: 큐에 넣고 기다림)를 정하는 것이다. HikariCP에서 커넥션을 못 받으면 `connectionTimeout` 후 예외를 던지는 게 폴리싱에 가깝고, 큐에 무한정 쌓아두면 셰이핑인데 메모리가 터진다. 어느 쪽이든 "초과분을 버릴지 대기시킬지, 대기시킨다면 얼마나"를 정해야 하는 건 라우터 QoS와 똑같다.

---

## 실무에서 헷갈리지 않으려면

마킹(DSCP)은 라벨일 뿐이고 실제 차별은 큐잉 정책이 한다. 마킹만 하고 큐잉 설정을 안 하면 아무 효과가 없다. burst 허용 여부로 Token Bucket과 Leaky Bucket이 갈리고, 초과분을 버리는지 대기시키는지로 폴리싱과 셰이핑이 갈린다. 이 두 축만 잡으면 라우터 QoS든 API rate limiter든 같은 틀로 이해된다. 리눅스에서 직접 실험할 때는 `tc`로 걸고 `tc -s class show`로 드롭을 확인하되, netem 같은 임시 설정은 끝나고 꼭 지운다.
