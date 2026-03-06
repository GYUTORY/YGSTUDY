---
title: Rate Limiting & Bulkhead 패턴 가이드
tags: [backend, resilience, rate-limiting, bulkhead, throttling, token-bucket, sliding-window, thread-pool-isolation]
updated: 2026-03-01
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
버킷 용량: 10, 충전 속도: 2개/초

시간 0: [██████████] 10개 → 요청 5개 처리 → [█████] 5개 남음
시간 1: [███████] 7개 (5 + 2충전) → 요청 3개 처리 → [████] 4개
시간 2: [██████] 6개 (4 + 2충전)
...

버스트(burst) 허용: 토큰이 쌓여있으면 순간적으로 많은 요청 처리 가능
```

- 장점: 버스트 트래픽 허용, 구현 간단
- 사용: API Gateway, 일반적인 Rate Limiting

#### Sliding Window Log

각 요청의 **타임스탬프를 기록**하고, 윈도우 내 요청 수를 계산한다.

```
윈도우: 1분, 제한: 100건

요청 기록: [10:00:01, 10:00:15, 10:00:30, ..., 10:00:59]

새 요청 (10:01:05) 도착 시:
  → 10:00:05 이후의 요청만 카운트
  → 100건 미만이면 허용
```

- 장점: 정확한 제한
- 단점: 메모리 사용 높음 (모든 타임스탬프 저장)

#### Sliding Window Counter

**고정 윈도우 + 가중 평균**으로 메모리 효율적으로 구현한다.

```
윈도우: 1분, 제한: 100건

이전 윈도우 (10:00~10:01): 80건
현재 윈도우 (10:01~10:02): 30건
현재 시점: 10:01:40 (현재 윈도우의 66.7% 경과)

가중 카운트 = 이전 × (1 - 0.667) + 현재
            = 80 × 0.333 + 30
            = 26.64 + 30 = 56.64건

→ 100건 미만이므로 허용
```

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
| Token Bucket | 보통 | 낮음 | ✅ | API GW, 일반 용도 |
| Sliding Window Log | 높음 | 높음 | ❌ | 정밀한 제한 필요 |
| Sliding Window Counter | 높음 | 낮음 | ❌ | **프로덕션 권장** |
| Fixed Window | 낮음 | 낮음 | ❌ | 단순한 경우만 |

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
❌ 격벽 없이 (공유 스레드 풀):
  Thread Pool: [결제, 결제, 결제, 배송, 결제, 결제, 결제, 재고, 결제, 결제]
  → 결제 API 느려짐 → 스레드 모두 점유 → 배송/재고도 처리 불가

✅ 격벽 적용 (분리된 스레드 풀):
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
