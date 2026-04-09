---
title: Rate Limiting & Bulkhead 패턴
tags: [backend, resilience, rate-limiting, bulkhead, throttling, token-bucket, sliding-window, leaky-bucket, thread-pool-isolation]
updated: 2026-04-09
---

# Rate Limiting & Bulkhead 패턴

## 개요

**Rate Limiting**은 일정 시간 내 요청 수를 제한하여 시스템을 보호하고, **Bulkhead**는 장애를 격리하여 전체 시스템으로 전파되는 것을 방지한다. Circuit Breaker/Retry와 함께 복원력 패턴의 핵심 구성 요소이다.

```
Rate Limiting:
  요청이 너무 많으면 거절 → 서버 보호

Bulkhead (격벽):
  서비스 A 장애 → 서비스 A 전용 스레드만 영향 → 서비스 B는 정상

  ┌──────────────────────────────────┐
  │        Application Server        │
  │  ┌──────────┐ ┌──────────┐      │
  │  │ Pool: A  │ │ Pool: B  │      │
  │  │ [████  ] │ │ [██    ] │      │
  │  │ (고갈)   │ │ (정상)   │      │
  │  └──────────┘ └──────────┘      │
  └──────────────────────────────────┘
  → A가 느려져도 B는 영향 없음
```

## Rate Limiting

### 1. 알고리즘

#### Token Bucket (토큰 버킷)

버킷에 일정 속도로 토큰이 채워진다. 요청마다 토큰 1개를 소비한다. 토큰이 없으면 거절.

```
Token Bucket 동작 흐름:

  토큰 공급기 (일정 속도로 토큰 생성)
       │
       │  2개/초
       ▼
  ┌────────────────────┐
  │  Token Bucket      │  용량(capacity): 10
  │                    │
  │  ○ ○ ○ ○ ○ ○ ●    │  ○ = 사용 가능 토큰, ● = 빈 슬롯
  │                    │
  └────────┬───────────┘
           │
           │  요청 도착 시 토큰 1개 소비
           ▼
     ┌───────────┐
     │ 토큰 있음? │
     └─────┬─────┘
       예  │  아니오
       ▼   │   ▼
     허용   │  거절 (429)
           │
```

```
시간 흐름에 따른 토큰 변화 (용량: 10, 충전: 2개/초):

시간(초)  토큰 수   이벤트
─────────────────────────────────────────────────
  0       10       [○○○○○○○○○○] 버킷 가득 참
  0       5        [○○○○○●●●●●] 요청 5개 → 토큰 5개 소비
  1       7        [○○○○○○○●●●] +2 충전됨
  1       4        [○○○○●●●●●●] 요청 3개 처리
  2       6        [○○○○○○●●●●] +2 충전됨
  3       8        [○○○○○○○○●●] +2 충전됨 (요청 없음)
  4       10       [○○○○○○○○○○] +2 → 용량 초과분 버림, 10 유지
  4       0        [●●●●●●●●●●] 요청 10개 한꺼번에 → 버스트 처리
  5       2        [○○●●●●●●●●] +2 충전, 요청 없음
─────────────────────────────────────────────────

핵심: 토큰이 쌓여있으면 순간적으로 많은 요청을 한꺼번에 처리할 수 있다.
      이 버스트(burst) 허용이 Token Bucket의 가장 큰 특징이다.
```

- 장점: 버스트 트래픽 허용, 구현 간단
- 사용: API Gateway, 일반적인 Rate Limiting

#### Sliding Window Log

각 요청의 **타임스탬프를 기록**하고, 윈도우 내 요청 수를 계산한다.

```
Sliding Window Log 동작 (윈도우: 1분, 제한: 5건):

시간축 ──────────────────────────────────────────────────────▶

10:00:10  10:00:25  10:00:40  10:00:50  10:01:00  10:01:05
  req①      req②      req③      req④      req⑤     req⑥(새 요청)
   │          │         │         │         │         │
   ▼          ▼         ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│ 타임스탬프 로그:                                              │
│ [10:00:10, 10:00:25, 10:00:40, 10:00:50, 10:01:00]         │
└─────────────────────────────────────────────────────────────┘

req⑥ 도착 (10:01:05):
  윈도우 시작 = 10:01:05 - 60초 = 10:00:05
  ├── 10:00:10  → 윈도우 내 (카운트)
  ├── 10:00:25  → 윈도우 내 (카운트)
  ├── 10:00:40  → 윈도우 내 (카운트)
  ├── 10:00:50  → 윈도우 내 (카운트)
  └── 10:01:00  → 윈도우 내 (카운트)
  카운트 = 5건 → 제한(5건) 도달 → 거절

10초 뒤, req⑦ 도착 (10:01:15):
  윈도우 시작 = 10:01:15 - 60초 = 10:00:15
  ├── 10:00:10  → 윈도우 밖 (만료, 제거)
  ├── 10:00:25  → 윈도우 내 (카운트)
  ├── ...
  카운트 = 4건 → 허용
```

- 장점: 정확한 제한
- 단점: 메모리 사용 높음 (모든 타임스탬프 저장)

#### Sliding Window Counter

**고정 윈도우 + 가중 평균**으로 메모리 효율적으로 구현한다.

```
Sliding Window Counter 동작 (윈도우: 1분, 제한: 100건):

      이전 윈도우              현재 윈도우
     10:00 ~ 10:01            10:01 ~ 10:02
  ┌───────────────────┐  ┌───────────────────┐
  │    80건 처리       │  │    30건 처리       │
  │    (카운터: 80)    │  │    (카운터: 30)    │
  └───────────────────┘  └─────────┬─────────┘
                                   │
                            현재 시점: 10:01:40
                            (현재 윈도우 66.7% 경과)

  슬라이딩 윈도우 (10:00:40 ~ 10:01:40):
  ◄─────────────────── 1분 ──────────────────►
  ┌────────┬──────────────────────────────────┐
  │이전33% │        현재 윈도우 전체            │
  │        │                                   │
  └────────┴──────────────────────────────────┘

  가중 카운트 = 이전 × (1 - 경과율) + 현재
             = 80 × 0.333 + 30
             = 26.64 + 30 = 56.64건
  → 100건 미만이므로 허용
```

Sliding Window Log와 달리 개별 타임스탬프를 저장하지 않고, 윈도우 단위 카운터 2개만 유지한다. 메모리를 거의 쓰지 않으면서 Fixed Window의 경계 버스트 문제를 완화한다.

- 장점: 메모리 효율 + 합리적 정확도
- 사용: Redis 기반 Rate Limiting에서 가장 많이 사용

#### Fixed Window Counter

가장 단순하지만 **윈도우 경계에서 버스트** 문제가 있다.

```
윈도우: 1분, 제한: 100건

10:00:00 ~ 10:00:59: 0건 → ... → 99건 (마지막 1초에 집중)
10:01:00 ~ 10:01:59: 100건 (첫 1초에 집중)

→ 경계 시점에서 실질적으로 2초 내 199건 처리 (의도한 100건/분 초과)
```

#### 알고리즘 비교

| 알고리즘 | 정확도 | 메모리 | 버스트 허용 | 적합한 경우 |
|---------|--------|--------|-----------|-----------|
| Token Bucket | 보통 | 낮음 | O | API GW, 일반 용도 |
| Leaky Bucket | 보통 | 낮음 | X (균일 처리) | Nginx limit_req |
| Sliding Window Log | 높음 | 높음 | X | 정밀한 제한 필요 |
| Sliding Window Counter | 높음 | 낮음 | X | **프로덕션 권장** |
| Fixed Window | 낮음 | 낮음 | X | 단순한 경우만 |

### Leaky Bucket vs Token Bucket — 무엇이 다른가

Nginx의 `limit_req`는 Leaky Bucket 알고리즘을 사용한다. 애플리케이션 레벨에서 자주 쓰는 Token Bucket과 이름이 비슷하지만 동작 방식이 근본적으로 다르다.

```
Leaky Bucket (Nginx limit_req):

  요청 유입 (불규칙)
  │ ││ │  │││ │ │
  ▼ ▼▼ ▼  ▼▼▼ ▼ ▼
  ┌──────────────┐
  │   버킷(큐)    │ ← burst 크기만큼 대기 가능
  │  req req req │
  │  req req     │
  └──────┬───────┘
         │  일정한 속도로 유출 (rate)
         │  100ms마다 1개 (10r/s 기준)
         ▼
    백엔드 서버        출력이 항상 균일하다


Token Bucket (애플리케이션 레벨):

  토큰 공급 (일정 속도)
         │
         ▼
  ┌──────────────┐
  │   토큰 저장소  │ ← capacity만큼 토큰 보관
  │  ○ ○ ○ ○ ○  │
  └──────┬───────┘
         │  요청 도착 시 토큰 소비
         │  토큰 있으면 즉시 통과
         ▼
    백엔드 서버        토큰 쌓여있으면 버스트 가능
```

**핵심 차이**:

| 구분 | Leaky Bucket | Token Bucket |
|------|-------------|-------------|
| **제어 대상** | 출력 속도 (유출률) | 입력 허용 여부 (토큰 잔량) |
| **버스트 처리** | 큐에 넣고 천천히 처리 | 쌓인 토큰만큼 즉시 처리 |
| **백엔드 부하** | 항상 균일 | 순간 부하 발생 가능 |
| **대기 시간** | 큐 대기 발생 (클라이언트 느려짐) | 토큰 있으면 대기 없음 |
| **사용처** | 인프라 레벨 (Nginx, 네트워크) | 애플리케이션 레벨 (API GW, SDK) |

Nginx `limit_req`에서 `nodelay` 옵션을 쓰면 burst 범위 내 요청을 즉시 처리하므로 Token Bucket과 비슷하게 동작한다. 다만 burst 슬롯이 rate에 따라 천천히 회복되는 점은 Leaky Bucket의 특성을 그대로 따른다.

```
실무에서의 선택 기준:

Nginx (Leaky Bucket)
  → 인프라 레벨에서 백엔드를 균일하게 보호하는 용도
  → 서버가 감당할 수 있는 처리량 이상이 넘어오지 않게 막는다
  → 단일 서버 또는 Pod 단위로 동작 (분산 환경에서 한계 있음)

애플리케이션 레벨 (Token Bucket / Sliding Window)
  → 사용자별, API 키별, 플랜별 세밀한 제한
  → Redis 같은 공유 저장소로 여러 서버에서 카운터 공유
  → 비즈니스 로직에 맞춘 제한 (과금 기준, 요금제별 할당량)

실제 운영에서는 둘 다 쓴다:
  클라이언트 → Nginx(Leaky Bucket, 인프라 보호)
           → 애플리케이션(Token Bucket/Sliding Window, 비즈니스 제한)
           → 백엔드 로직
```

### 2. Redis 기반 구현

```java
// Sliding Window Counter (Redis + Spring)
@Component
public class RateLimiter {

    private final StringRedisTemplate redis;

    public boolean isAllowed(String key, int limit, Duration window) {
        String redisKey = "rate:" + key;
        long now = System.currentTimeMillis();
        long windowStart = now - window.toMillis();

        // 윈도우 밖의 오래된 요청 제거
        redis.opsForZSet().removeRangeByScore(redisKey, 0, windowStart);

        // 현재 윈도우 내 요청 수
        Long count = redis.opsForZSet().zCard(redisKey);

        if (count != null && count >= limit) {
            return false;  // 제한 초과
        }

        // 새 요청 기록
        redis.opsForZSet().add(redisKey, String.valueOf(now), now);
        redis.expire(redisKey, window);

        return true;
    }
}

// 사용 (Spring Interceptor)
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                             Object handler) {
        String clientId = extractClientId(request);

        if (!rateLimiter.isAllowed(clientId, 100, Duration.ofMinutes(1))) {
            response.setStatus(429);
            response.setHeader("Retry-After", "60");
            response.getWriter().write("{\"error\": \"Too Many Requests\"}");
            return false;
        }
        return true;
    }
}
```

### 3. 다중 계층 Rate Limiting

```
1단계: API Gateway (전체 보호)
  - IP당 1000 req/min
  - 전체 10,000 req/min

2단계: 서비스 레벨 (서비스별 보호)
  - 주문 API: 유저당 60 req/min
  - 검색 API: 유저당 300 req/min

3단계: 비즈니스 레벨 (기능별 보호)
  - 결제: 유저당 10 req/min
  - 비밀번호 변경: 유저당 3 req/hour
```

### 4. 응답 헤더

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1709280000

{
    "error": "Too Many Requests",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retryAfter": 60
}
```

## Bulkhead (격벽 패턴)

### 1. 개념

선박의 격벽(Bulkhead)처럼, 시스템을 **격리된 구획**으로 나누어 한 구획의 장애가 전체에 영향을 주지 않도록 한다.

```
[문제] 격벽 없이 (공유 스레드 풀):
  Thread Pool: [결제, 결제, 결제, 배송, 결제, 결제, 결제, 재고, 결제, 결제]
  → 결제 API 느려짐 → 스레드 모두 점유 → 배송/재고도 처리 불가

[해결] 격벽 적용 (분리된 스레드 풀):
  결제 Pool:  [결제, 결제, 결제, 결제, 결제]  ← 느려져도 여기만 영향
  배송 Pool:  [배송, 배송, 배송]              ← 정상
  재고 Pool:  [재고, 재고]                    ← 정상
```

### 2. 유형

#### Thread Pool Isolation (스레드 풀 격리)

각 외부 서비스 호출에 **별도 스레드 풀**을 할당한다.

```java
// Resilience4j Thread Pool Bulkhead
resilience4j:
  thread-pool-bulkhead:
    instances:
      paymentService:
        maxThreadPoolSize: 10     # 최대 스레드 수
        coreThreadPoolSize: 5     # 기본 스레드 수
        queueCapacity: 20         # 대기 큐 크기
        keepAliveDuration: 60s    # 유휴 스레드 생존 시간
      deliveryService:
        maxThreadPoolSize: 5
        coreThreadPoolSize: 3
        queueCapacity: 10
```

```java
@Service
public class OrderService {

    @Bulkhead(name = "paymentService", type = Bulkhead.Type.THREADPOOL)
    public CompletableFuture<PaymentResult> processPayment(Order order) {
        return CompletableFuture.supplyAsync(() ->
            paymentClient.charge(order.getAmount())
        );
    }

    @Bulkhead(name = "deliveryService", type = Bulkhead.Type.THREADPOOL)
    public CompletableFuture<DeliveryResult> requestDelivery(Order order) {
        return CompletableFuture.supplyAsync(() ->
            deliveryClient.schedule(order)
        );
    }
}
```

#### Semaphore Isolation (세마포어 격리)

별도 스레드 없이 **동시 호출 수만 제한**한다. 오버헤드가 적다.

```java
// Resilience4j Semaphore Bulkhead
resilience4j:
  bulkhead:
    instances:
      paymentService:
        maxConcurrentCalls: 10    # 최대 동시 호출 수
        maxWaitDuration: 500ms    # 대기 시간 (초과 시 거절)
```

```java
@Service
public class OrderService {

    @Bulkhead(name = "paymentService")  // 기본: SEMAPHORE
    public PaymentResult processPayment(Order order) {
        return paymentClient.charge(order.getAmount());
    }
}
```

| 비교 | Thread Pool | Semaphore |
|------|-----------|-----------|
| **격리 수준** | 완전 격리 (별도 스레드) | 동시 호출 수만 제한 |
| **오버헤드** | 높음 (스레드 생성) | 낮음 |
| **타임아웃 제어** | 가능 (스레드 인터럽트) | 불가 (호출자 스레드) |
| **반환 타입** | `CompletableFuture` | 동기 반환 |
| **적합한 경우** | 외부 API, 느린 호출 | 내부 서비스, 빠른 호출 |

### 3. 패턴 조합

실전에서는 여러 패턴을 **조합**하여 사용한다.

```
요청 → Rate Limiter → Bulkhead → Circuit Breaker → Retry → Timeout → 외부 API

적용 순서:
  1. Rate Limiter: 과도한 요청 차단
  2. Bulkhead: 격리된 스레드 풀에서 실행
  3. Circuit Breaker: 연속 실패 시 차단
  4. Retry: 일시적 오류 재시도
  5. Timeout: 응답 대기 시간 제한
```

```java
@Service
public class PaymentService {

    @RateLimiter(name = "paymentApi")
    @Bulkhead(name = "paymentApi")
    @CircuitBreaker(name = "paymentApi", fallbackMethod = "paymentFallback")
    @Retry(name = "paymentApi")
    @TimeLimiter(name = "paymentApi")
    public CompletableFuture<PaymentResult> processPayment(PaymentRequest request) {
        return CompletableFuture.supplyAsync(() ->
            paymentClient.charge(request)
        );
    }

    private CompletableFuture<PaymentResult> paymentFallback(
            PaymentRequest request, Throwable t) {
        return CompletableFuture.completedFuture(
            PaymentResult.pending("결제 시스템 점검 중. 잠시 후 처리됩니다.")
        );
    }
}
```

```yaml
# application.yml (전체 설정)
resilience4j:
  ratelimiter:
    instances:
      paymentApi:
        limitForPeriod: 50
        limitRefreshPeriod: 1s
        timeoutDuration: 500ms

  bulkhead:
    instances:
      paymentApi:
        maxConcurrentCalls: 20
        maxWaitDuration: 500ms

  circuitbreaker:
    instances:
      paymentApi:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 3

  retry:
    instances:
      paymentApi:
        maxAttempts: 3
        waitDuration: 1s
        retryExceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException

  timelimiter:
    instances:
      paymentApi:
        timeoutDuration: 3s
```

### 4. 모니터링

```yaml
# Resilience4j + Actuator 메트릭
management:
  endpoints:
    web:
      exposure:
        include: health, metrics
  health:
    circuitbreakers:
      enabled: true
    ratelimiters:
      enabled: true
```

```
핵심 메트릭:
  resilience4j_circuitbreaker_state           # CLOSED/OPEN/HALF_OPEN
  resilience4j_circuitbreaker_failure_rate     # 실패율 (%)
  resilience4j_bulkhead_available_concurrent_calls  # 사용 가능한 동시 호출 수
  resilience4j_ratelimiter_available_permissions    # 남은 허용 요청 수
  resilience4j_retry_calls_total               # 재시도 횟수
```

## 참고

- [Resilience4j Documentation](https://resilience4j.readme.io/)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [장애 대응 패턴](Fault_Tolerance.md) — Circuit Breaker, Retry, Timeout, Fallback
- [메시지 큐](../Messaging/Message_Queue.md) — 비동기 처리로 부하 분산
- [캐싱 전략](../Caching/Caching_Strategies.md) — 캐시로 외부 호출 감소
