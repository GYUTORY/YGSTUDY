---
title: Rate Limiting & Bulkhead 패턴
tags: [backend, performance]
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

```typescript
// Sliding Window Counter (Redis + NestJS)
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class RateLimiter {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async isAllowed(key: string, limit: number, windowMs: number): Promise<boolean> {
    const redisKey = 'rate:' + key;
    const now = Date.now();
    const windowStart = now - windowMs;

    // 윈도우 밖의 오래된 요청 제거
    await this.redis.zremrangebyscore(redisKey, 0, windowStart);

    // 현재 윈도우 내 요청 수
    const count = await this.redis.zcard(redisKey);

    if (count >= limit) {
      return false; // 제한 초과
    }

    // 새 요청 기록
    await this.redis.zadd(redisKey, now, String(now));
    await this.redis.pexpire(redisKey, windowMs);

    return true;
  }
}

// 사용 (NestJS Interceptor)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler, HttpException, HttpStatus } from '@nestjs/common';
import { Observable } from 'rxjs';
import { Request, Response } from 'express';

@Injectable()
export class RateLimitInterceptor implements NestInterceptor {
  constructor(private readonly rateLimiter: RateLimiter) {}

  async intercept(context: ExecutionContext, next: CallHandler): Promise<Observable<unknown>> {
    const req = context.switchToHttp().getRequest<Request>();
    const res = context.switchToHttp().getResponse<Response>();
    const clientId = this.extractClientId(req);

    const allowed = await this.rateLimiter.isAllowed(clientId, 100, 60_000);
    if (!allowed) {
      res.setHeader('Retry-After', '60');
      throw new HttpException({ error: 'Too Many Requests' }, HttpStatus.TOO_MANY_REQUESTS);
    }
    return next.handle();
  }

  private extractClientId(req: Request): string {
    return req.headers['x-api-key'] as string ?? req.ip ?? 'anonymous';
  }
}
```

#### 위 구현에는 결함이 둘 있다

**검사와 기록이 원자적이지 않다.** `zremrangebyscore` → `zcard` → `zadd` 는 세 번의 왕복이고 그 사이에 다른 요청이 끼어든다. 동시에 도착한 요청이 전부 `count >= limit` 검사를 통과한 뒤 각자 `zadd` 하므로 한도가 그대로 뚫린다. 세 번의 왕복을 그대로 흉내 낸 모형에 한도 5로 동시 20요청을 넣으면 20건이 전부 통과한다.

부하가 낮을 때는 드러나지 않고 **정확히 트래픽이 몰릴 때만** 무력해진다. 레이트 리미터로서는 최악의 실패 방식이다. 위 표에서 Sliding Window Counter 의 정확도를 "높음"으로 적었지만 그건 알고리즘의 성질이지 이 구현의 성질이 아니다.

원자성은 Lua 스크립트로 만든다. `MULTI/EXEC` 는 명령을 묶어 주기는 해도 중간 결과(`ZCARD`)를 보고 분기할 수 없어 이 용도에는 부족하다.

```lua
-- KEYS[1]=키, ARGV: now, windowStart, limit, member, windowMs
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[2])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
redis.call('PEXPIRE', KEYS[1], ARGV[5])
return 1
```

**member 가 밀리초 문자열이라 같은 밀리초의 요청이 1건으로 합쳐진다.** `zadd(redisKey, now, String(now))` 에서 member 는 `String(now)` 다. ZSET 의 member 는 유일하므로, 이미 있는 member 로 ZADD 하면 원소가 추가되지 않고 score 만 갱신된다([ZADD 문서](https://redis.io/docs/latest/commands/zadd/)). 같은 밀리초에 들어온 요청 20건이 ZSET 에 원소 하나로 남는다. 초당 수백 건이 오는 API 라면 세는 값 자체가 실제보다 작아진다. member 에는 충돌하지 않는 값을 넣는다.

```typescript
await this.redis.zadd(redisKey, now, `${now}:${randomUUID()}`);
```

**클라이언트 식별에도 함정이 있다.** `extractClientId` 는 `x-api-key` 헤더를 검증 없이 키로 쓴다. 이 헤더는 클라이언트가 아무 값이나 넣을 수 있으니, 요청마다 다른 값을 보내면 제한이 통째로 무력해진다. **인증을 통과한 뒤 서버가 확인한 신원**으로 키를 만들어야 한다. 폴백인 `req.ip` 도 프록시·로드밸런서 뒤에서는 프록시 주소가 되어 모든 사용자가 카운터 하나를 공유한다 — 한 명이 한도를 채우면 전원이 함께 429 를 받는다. Express 라면 `trust proxy` 를 설정하고, 그 앞단이 신뢰할 수 있는 경로인지 먼저 확인한다.

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

```typescript
// NestJS Thread Pool Bulkhead — 서비스별 동시 실행 풀 분리
// p-limit 패키지로 동시 실행 수 제어
import pLimit from 'p-limit';

// 서비스별 concurrency 제한 (스레드 풀 격리와 유사한 효과)
const paymentPool = pLimit(10);  // 최대 동시 실행 10개
const deliveryPool = pLimit(5);  // 최대 동시 실행 5개
```

```typescript
import { Injectable } from '@nestjs/common';
import pLimit from 'p-limit';

@Injectable()
export class OrderService {
  private readonly paymentPool = pLimit(10);
  private readonly deliveryPool = pLimit(5);

  async processPayment(order: { amount: number }): Promise<PaymentResult> {
    // paymentPool로 동시 실행 수 제한 (격리)
    return this.paymentPool(() =>
      this.paymentClient.charge(order.amount),
    );
  }

  async requestDelivery(order: Order): Promise<DeliveryResult> {
    // deliveryPool로 동시 실행 수 제한 (격리)
    return this.deliveryPool(() =>
      this.deliveryClient.schedule(order),
    );
  }
}
```

#### Semaphore Isolation (세마포어 격리)

별도 스레드 없이 **동시 호출 수만 제한**한다. 오버헤드가 적다.

```typescript
// NestJS Semaphore Bulkhead — 동시 호출 수만 제한
// async-semaphore 또는 직접 구현
import { Injectable } from '@nestjs/common';

@Injectable()
export class SemaphoreBulkhead {
  private running = 0;
  constructor(
    private readonly maxConcurrentCalls: number,
    private readonly maxWaitMs: number,
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.running >= this.maxConcurrentCalls) {
      // 대기 시간(maxWaitMs) 초과 시 거절
      await this.waitForSlot();
    }
    this.running++;
    try {
      return await fn();
    } finally {
      this.running--;
    }
  }

  private waitForSlot(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Bulkhead full')), this.maxWaitMs);
      const interval = setInterval(() => {
        if (this.running < this.maxConcurrentCalls) {
          clearInterval(interval);
          clearTimeout(timeout);
          resolve();
        }
      }, 10);
    });
  }
}
```

```typescript
import { Injectable } from '@nestjs/common';

@Injectable()
export class OrderService {
  private readonly paymentBulkhead = new SemaphoreBulkhead(10, 500); // 기본: Semaphore 방식

  async processPayment(order: { amount: number }): Promise<PaymentResult> {
    return this.paymentBulkhead.execute(() =>
      this.paymentClient.charge(order.amount),
    );
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

### 위 Bulkhead 가 과부하에서 하는 일

`waitForSlot()` 은 폴링용 `setInterval` 과 타임아웃용 `setTimeout` 두 개를 만든다. 슬롯이 나면 둘 다 정리하지만 **타임아웃으로 거절될 때는 interval 을 정리하지 않는다.** 그래서 거절된 요청 하나마다 10ms 폴링 타이머가 하나씩 남는다.

```
슬롯 1개를 점유한 채 100건을 거절시키면
  거절 처리 직후 살아있는 타이머 = 101   (점유 중 작업 1 + 누수 100)
  0.4초 뒤에도                    = 101   ← 슬롯이 안 비면 계속 폴링한다
```

남은 interval 은 슬롯이 빌 때 스스로 정리된다. 그런데 **하필 슬롯이 안 비는 상황이 곧 거절이 쏟아지는 상황**이다. 과부하일수록 폴링 타이머가 쌓이니 방향이 반대다. `reject` 쪽에서도 `clearInterval` 을 부르는 것이 최소 수정이고, 폴링 자체를 없애고 대기자 큐를 두는 편이 낫다.

```typescript
private waiters: Array<() => void> = [];

private release() {
  this.running--;
  this.waiters.shift()?.();   // 폴링 없이 한 명만 깨운다
}
```

### "Thread Pool Isolation" 은 Node 에 그대로 옮겨지지 않는다

위 비교표의 "완전 격리(별도 스레드)", "반환 타입 `CompletableFuture`", "타임아웃 제어: 스레드 인터럽트" 는 JVM(Hystrix·Resilience4j) 이야기다. 예시로 든 `p-limit` 은 스레드를 만들지 않는다 — **진행 중인 Promise 개수를 세는 것뿐이라 사실상 아래 세마포어와 같다.** Node 에서 두 방식의 차이는 표에 적힌 만큼 크지 않다.

그래서 Node 에서 Bulkhead 를 붙일 때는 **무엇을 격리하려는 것인지**를 다시 물어야 한다. 동시 실행 수를 제한해도 아래는 여전히 공유 자원이다.

| 공유 자원 | 동시 실행 수 제한으로 격리되나 | 실제로 나눠야 하는 것 |
|---|---|---|
| HTTP 소켓 | 안 됨 | 서비스별 `http.Agent` 와 `maxSockets` |
| DB 커넥션 | 안 됨 | 용도별 커넥션 풀 분리 |
| 이벤트 루프 | 안 됨 | 무거운 동기 작업은 `worker_threads` 로 |
| 메모리 | 안 됨 | 프로세스 분리 |

느린 외부 API 하나가 소켓을 다 붙들면 `p-limit` 상한과 무관하게 다른 호출이 소켓을 기다린다. **동시 호출 수 제한은 격리의 일부일 뿐이고, 진짜 격리는 자원을 물리적으로 나누는 데서 온다.** 프로세스가 하나인 Node 에서 완전한 격리를 원하면 결국 프로세스를 나눠야 하고, 그러면 배포 단위와 운영 부담이 늘어난다. 그게 이 패턴의 대가다.

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

```typescript
// NestJS 패턴 조합 — Rate Limiting + Bulkhead + Circuit Breaker + Retry + Timeout
// 각 패턴을 직접 구성하여 조합 (@nestjs/axios, p-limit, opossum, async-retry 사용)
import { Injectable, Logger } from '@nestjs/common';
import pLimit from 'p-limit';
import CircuitBreaker from 'opossum';
import retry from 'async-retry';

export interface PaymentRequest {
  orderId: string;
  amount: number;
  currency: string;
}

export interface PaymentResult {
  status: 'success' | 'pending' | 'failed';
  message: string;
  transactionId?: string;
}

@Injectable()
export class PaymentService {
  private readonly logger = new Logger(PaymentService.name);

  // Bulkhead: 동시 호출 수 20개 제한
  private readonly bulkhead = pLimit(20);

  // Circuit Breaker: 10회 중 50% 실패 시 OPEN, 30초 후 HALF-OPEN
  private readonly circuitBreaker: CircuitBreaker<[PaymentRequest], PaymentResult>;

  constructor(private readonly paymentClient: PaymentClient) {
    this.circuitBreaker = new CircuitBreaker(
      (req: PaymentRequest) => this.paymentClient.charge(req),
      {
        volumeThreshold: 10,       // 최소 요청 수
        errorThresholdPercentage: 50,
        resetTimeout: 30_000,      // 30초 후 HALF-OPEN
        timeout: 3_000,            // Timeout: 3초
      },
    );

    this.circuitBreaker.fallback((_req: PaymentRequest) =>
      this.paymentFallback(),
    );

    this.circuitBreaker.on('open', () =>
      this.logger.warn('Circuit OPEN: paymentApi'),
    );
    this.circuitBreaker.on('halfOpen', () =>
      this.logger.log('Circuit HALF-OPEN: paymentApi'),
    );
    this.circuitBreaker.on('close', () =>
      this.logger.log('Circuit CLOSED: paymentApi'),
    );
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResult> {
    // Rate Limiting은 RateLimitInterceptor 또는 Guard에서 처리
    // Bulkhead (pLimit) → Circuit Breaker (opossum) 순으로 실행
    return this.bulkhead(async () => {
      // Retry: 최대 3회, 1초 간격
      return retry(
        async () => {
          return this.circuitBreaker.fire(request);
        },
        {
          retries: 3,
          minTimeout: 1_000,
          onRetry: (err: Error, attempt: number) => {
            this.logger.warn(`Retry ${attempt} for paymentApi: ${err.message}`);
          },
        },
      );
    });
  }

  private paymentFallback(): PaymentResult {
    return {
      status: 'pending',
      message: '결제 시스템 점검 중. 잠시 후 처리됩니다.',
    };
  }
}
```

```yaml
# .env / ConfigModule 기반 설정 (application.yml → NestJS 환경 변수)
# PAYMENT_RATE_LIMIT_COUNT=50          # 1초 내 최대 요청 수
# PAYMENT_RATE_LIMIT_WINDOW_MS=1000

# PAYMENT_BULKHEAD_MAX_CONCURRENT=20   # 최대 동시 호출 수
# PAYMENT_BULKHEAD_MAX_WAIT_MS=500

# PAYMENT_CB_SLIDING_WINDOW=10         # Circuit Breaker 슬라이딩 윈도우 크기
# PAYMENT_CB_FAILURE_THRESHOLD=50      # 실패율 임계값 (%)
# PAYMENT_CB_WAIT_OPEN_MS=30000        # OPEN 유지 시간
# PAYMENT_CB_HALF_OPEN_CALLS=3        # HALF-OPEN 허용 호출 수

# PAYMENT_RETRY_MAX_ATTEMPTS=3        # 최대 재시도 횟수
# PAYMENT_RETRY_WAIT_MS=1000          # 재시도 대기 시간

# PAYMENT_TIMEOUT_MS=3000             # 응답 타임아웃
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
