---
title: 장애 대응 패턴 (Fault Tolerance)
tags: [backend, resilience, circuit-breaker, retry, timeout, Fallback, health-check, resilience4j, graceful-shutdown, backpressure, load-shedding]
updated: 2026-03-30
---

# 장애 대응 패턴 (Fault Tolerance)

## 개요

분산 시스템에서 장애는 언제든 발생한다. 외부 API가 느려지거나 DB 연결이 끊기거나 네트워크가 불안정해진다. 이런 장애가 전체 시스템으로 전파되는 것을 막아야 한다. Circuit Breaker, Retry, Timeout, Fallback으로 장애 전파를 차단하고, Graceful Shutdown, Backpressure, Load Shedding으로 과부하 상황에서 시스템 스스로 부하를 조절한다.

### 왜 필요한가

**문제 상황:**

**시나리오:**
주문 서비스가 결제 API를 호출한다. 결제 API가 갑자기 느려진다 (응답 시간 30초).

**연쇄 장애:**
```
주문 요청 → 결제 API 호출 (30초 대기)
주문 요청 → 결제 API 호출 (30초 대기)
주문 요청 → 결제 API 호출 (30초 대기)
...
```

**결과:**
- 모든 주문 요청이 30초씩 대기
- 이벤트 루프 포화
- 새로운 주문 요청 불가
- 전체 서비스 다운

**결제 API 하나의 문제가 전체 시스템을 마비시킨다.**

**장애 대응 패턴 적용:**
- **Timeout**: 3초 내 응답 없으면 즉시 실패
- **Circuit Breaker**: 연속 실패 시 API 호출 차단
- **Retry**: 일시적 오류는 재시도
- **Fallback**: 실패 시 대체 동작

**결과:**
결제 API 문제가 있어도 주문 서비스는 정상 동작한다.

## Circuit Breaker

### 개념

전기 회로 차단기처럼 동작한다. 연속으로 실패하면 회로를 차단한다. 외부 시스템이 복구될 시간을 준다.

**3가지 상태:**

**CLOSED (정상):**
- 요청을 정상적으로 전달
- 실패율 모니터링

**OPEN (차단):**
- 모든 요청을 즉시 차단
- Fallback 실행
- 일정 시간 대기 (Wait Duration)

**HALF_OPEN (반개방):**
- 일부 요청만 전달 (테스트)
- 성공하면 CLOSED로
- 실패하면 다시 OPEN으로

### NestJS Circuit Breaker 구현

NestJS에서는 `opossum` 라이브러리를 많이 사용한다.

**패키지 설치:**
```
npm install opossum
npm install --save-dev @types/opossum
```

**설정:**
```typescript
import { Injectable } from '@nestjs/common';
import CircuitBreaker from 'opossum';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';

interface PaymentRequest {
  orderId: string;
  amount: number;
}

interface PaymentResponse {
  status: string;
  message: string;
}

@Injectable()
export class PaymentService {
  private readonly breaker: CircuitBreaker;

  constructor(private httpService: HttpService) {
    this.breaker = new CircuitBreaker(this.callPaymentApi.bind(this), {
      // 슬라이딩 윈도우 크기 (최근 N개 요청)
      rollingCountTimeout: 10000,
      // 실패율 임계값 (50%)
      errorThresholdPercentage: 50,
      // 최소 호출 수 (통계 계산 전 필요한 최소 요청 수)
      volumeThreshold: 5,
      // OPEN 상태 유지 시간 (ms)
      resetTimeout: 10000,
    });

    this.breaker.fallback((request: PaymentRequest) =>
      this.paymentFallback(request),
    );
  }

  private async callPaymentApi(request: PaymentRequest): Promise<PaymentResponse> {
    const { data } = await firstValueFrom(
      this.httpService.post<PaymentResponse>(
        'https://payment-api.com/process',
        request,
      ),
    );
    return data;
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    return this.breaker.fire(request) as Promise<PaymentResponse>;
  }

  // Fallback 메서드
  private paymentFallback(request: PaymentRequest): PaymentResponse {
    console.error('Payment failed, using fallback');
    return { status: 'PENDING', message: '결제 처리 중입니다' };
  }
}
```

### 동작 예시

**시나리오:**
```
요청 1-4: 성공 (CLOSED 상태 유지)
요청 5: 실패 (실패율 10%)
요청 6: 실패 (실패율 20%)
요청 7: 실패 (실패율 30%)
요청 8: 실패 (실패율 40%)
요청 9: 실패 (실패율 50%)
요청 10: 실패 (실패율 60%) → 임계값 초과

상태: CLOSED → OPEN

요청 11-100: 즉시 차단, Fallback 실행 (10초간)

10초 후: HALF_OPEN

요청 101-103: 테스트 요청 (3개)
  - 모두 성공 → CLOSED
  - 하나라도 실패 → 다시 OPEN
```

## Retry

### 개념

일시적인 오류는 재시도하면 성공할 수 있다. 네트워크 지연, 일시적 과부하 등.

**주의:**
무한 재시도는 위험하다. 최대 횟수와 대기 시간을 설정한다.

### Exponential Backoff

재시도 간격을 지수적으로 증가시킨다.

**예시:**
- 1차 재시도: 1초 대기
- 2차 재시도: 2초 대기
- 3차 재시도: 4초 대기
- 4차 재시도: 8초 대기

**이유:**
- 외부 시스템에 부하를 주지 않음
- 복구 시간 확보
- Thundering Herd 방지

### NestJS Retry 구현

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom, retry, timer } from 'rxjs';

interface PaymentRequest {
  orderId: string;
  amount: number;
}

interface PaymentResponse {
  status: string;
  message: string;
}

@Injectable()
export class PaymentService {
  constructor(private httpService: HttpService) {}

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    const { data } = await firstValueFrom(
      this.httpService
        .post<PaymentResponse>('https://payment-api.com/process', request)
        .pipe(
          retry({
            count: 3, // 최대 재시도 횟수
            delay: (error, retryCount) => {
              // Exponential Backoff: 1s, 2s, 4s
              const delayMs = Math.min(1000 * Math.pow(2, retryCount - 1), 10000);
              console.info(`Retry attempt ${retryCount}, waiting ${delayMs}ms`);
              return timer(delayMs);
            },
            resetOnSuccess: true,
          }),
        ),
    );
    return data;
  }
}
```

### Retry + Circuit Breaker 조합

```typescript
import { Injectable } from '@nestjs/common';
import CircuitBreaker from 'opossum';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom, retry, timer } from 'rxjs';

@Injectable()
export class PaymentService {
  private readonly breaker: CircuitBreaker;

  constructor(private httpService: HttpService) {
    this.breaker = new CircuitBreaker(this.callWithRetry.bind(this), {
      errorThresholdPercentage: 50,
      resetTimeout: 30000,
    });

    this.breaker.fallback((request: PaymentRequest) =>
      this.paymentFallback(request),
    );
  }

  private async callWithRetry(request: PaymentRequest): Promise<PaymentResponse> {
    const { data } = await firstValueFrom(
      this.httpService
        .post<PaymentResponse>('https://payment-api.com/process', request)
        .pipe(retry({ count: 3, delay: (_, n) => timer(1000 * Math.pow(2, n - 1)) })),
    );
    return data;
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    return this.breaker.fire(request) as Promise<PaymentResponse>;
  }

  private paymentFallback(request: PaymentRequest): PaymentResponse {
    return { status: 'FAILED', message: '결제 실패' };
  }
}
```

**동작:**
1. Retry가 먼저 적용 (최대 3회 재시도)
2. 모두 실패하면 Circuit Breaker에 실패 카운트
3. Circuit Breaker가 OPEN 상태면 재시도하지 않고 즉시 Fallback

### Jitter (지터)

재시도 시간에 랜덤성을 추가한다.

**이유:**
여러 클라이언트가 동시에 실패하고 동시에 재시도하면 Thundering Herd 발생.

**Jitter 적용:**
```typescript
function exponentialBackoffWithJitter(retryCount: number): number {
  const base = 1000; // 1초
  const maxDelay = 10000; // 10초
  const exponential = Math.min(base * Math.pow(2, retryCount - 1), maxDelay);
  // Full Jitter: 0 ~ exponential 사이의 랜덤 값
  return Math.random() * exponential;
}
```

**효과:**
- 1초 ± 50% → 0초 ~ 1초 사이 랜덤
- 클라이언트들이 분산되어 재시도

## Timeout

### 개념

무한 대기를 방지한다. 일정 시간 내 응답이 없으면 실패로 간주한다.

**3가지 Timeout:**

**Connection Timeout:**
연결 수립 시간. 보통 짧게 설정 (1-3초).

**Response Timeout:**
응답 수신 시간. API 특성에 따라 다름 (3-30초).

**Socket Timeout:**
데이터 전송 시간. 보통 Response Timeout과 동일.

### Axios Timeout 설정

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class PaymentService {
  constructor(private httpService: HttpService) {}

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    const { data } = await firstValueFrom(
      this.httpService.post<PaymentResponse>(
        'https://payment-api.com/process',
        request,
        {
          timeout: 5000, // 5초 응답 타임아웃
          // httpsAgent: new https.Agent({ timeout: 2000 }) // 연결 타임아웃
        },
      ),
    );
    return data;
  }
}
```

### NestJS HttpModule 기본 Timeout 설정

```typescript
import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';

@Module({
  imports: [
    HttpModule.register({
      timeout: 5000,          // 응답 타임아웃: 5초
      maxRedirects: 5,
    }),
  ],
})
export class PaymentModule {}
```

### Promise.race를 이용한 Timeout

```typescript
import { Injectable } from '@nestjs/common';

@Injectable()
export class PaymentService {
  async processPaymentAsync(request: PaymentRequest): Promise<PaymentResponse> {
    const timeoutMs = 5000;

    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${timeoutMs}ms`)), timeoutMs),
    );

    return Promise.race([this.callPaymentApi(request), timeoutPromise]);
  }

  private async callPaymentApi(request: PaymentRequest): Promise<PaymentResponse> {
    // 실제 API 호출
    return { status: 'OK', message: '' };
  }
}
```

## Fallback

### 개념

주 동작이 실패했을 때 대체 동작을 수행한다.

**Fallback 전략:**

**1. 기본값 반환:**
```typescript
private getUserProfileFallback(userId: string, error: Error): UserProfile {
  console.warn('Failed to fetch user profile, returning default', error);
  return {
    userId,
    name: 'Guest',
    avatar: '/images/default-avatar.webp',
  };
}
```

**2. 캐시 사용:**
```typescript
import { Injectable } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Inject } from '@nestjs/common';
import { Cache } from 'cache-manager';
import CircuitBreaker from 'opossum';

@Injectable()
export class UserService {
  private readonly breaker: CircuitBreaker;

  constructor(@Inject(CACHE_MANAGER) private cacheManager: Cache) {
    this.breaker = new CircuitBreaker(this.fetchUserProfile.bind(this), {
      errorThresholdPercentage: 50,
      resetTimeout: 30000,
    });
    this.breaker.fallback((userId: string) => this.getUserProfileFromCache(userId));
  }

  private async fetchUserProfile(userId: string): Promise<UserProfile> {
    // 외부 API 호출
    return {} as UserProfile;
  }

  private async getUserProfileFromCache(userId: string): Promise<UserProfile | null> {
    console.warn('Using cached user profile');
    return this.cacheManager.get<UserProfile>(`userProfiles:${userId}`) ?? null;
  }
}
```

**3. 다른 서비스 호출:**
```typescript
@Injectable()
export class PaymentService {
  private readonly breaker: CircuitBreaker;

  constructor(
    private primaryPaymentService: PrimaryPaymentService,
    private secondaryPaymentService: SecondaryPaymentService,
  ) {
    this.breaker = new CircuitBreaker(
      (request: PaymentRequest) => this.primaryPaymentService.process(request),
      { errorThresholdPercentage: 50, resetTimeout: 30000 },
    );
    this.breaker.fallback((request: PaymentRequest) =>
      this.useSecondaryPayment(request),
    );
  }

  private async useSecondaryPayment(request: PaymentRequest): Promise<PaymentResponse> {
    console.warn('Primary payment failed, using secondary');
    return this.secondaryPaymentService.process(request);
  }
}
```

**4. 저하된 서비스 제공:**
```typescript
@Injectable()
export class ProductService {
  private readonly breaker: CircuitBreaker;

  constructor(
    private recommendationService: RecommendationService,
    private popularProductService: PopularProductService,
  ) {
    this.breaker = new CircuitBreaker(
      (userId: string) => this.recommendationService.getPersonalized(userId),
      { errorThresholdPercentage: 50, resetTimeout: 30000 },
    );
    this.breaker.fallback((userId: string) => this.getPopularItems(userId));
  }

  async getRecommendations(userId: string): Promise<Product[]> {
    return this.breaker.fire(userId) as Promise<Product[]>;
  }

  private async getPopularItems(userId: string): Promise<Product[]> {
    console.warn('Personalized recommendations failed, returning popular items');
    // 개인화 추천 실패 시 인기 상품 반환
    return this.popularProductService.getPopularProducts();
  }
}
```

### Fallback 주의사항

**Fallback도 실패할 수 있다:**
```typescript
private async paymentFallback(request: PaymentRequest): Promise<PaymentResponse> {
  try {
    // 보조 결제 시스템 시도
    return await this.backupPaymentService.process(request);
  } catch (ex) {
    // 보조 시스템도 실패
    console.error('Both primary and backup payment failed', ex);
    return { status: 'FAILED', message: '결제 불가' };
  }
}
```

**Fallback이 주 동작보다 느리면 안 된다:**
```typescript
// Bad: Fallback이 DB 조회
private async fallback(userId: string): Promise<UserProfile | null> {
  return this.userRepository.findOne({ where: { id: userId } }); // 느릴 수 있음
}

// Good: Fallback은 빠르게
private fallback(userId: string): UserProfile {
  return UserProfile.DEFAULT; // 즉시 반환
}
```

## Health Check

### Liveness vs Readiness

**Liveness (살아있는지):**
- 프로세스가 실행 중인지 확인
- 실패 시: 컨테이너 재시작
- 예: 데드락, 무한 루프

**Readiness (준비됐는지):**
- 요청을 받을 준비가 됐는지 확인
- 실패 시: 트래픽 차단 (재시작 X)
- 예: DB 연결 안 됨, 캐시 워밍업 중

### NestJS 헬스체크 (Terminus)

**패키지 설치:**
```
npm install @nestjs/terminus
```

**설정:**
```typescript
import { Controller, Get } from '@nestjs/common';
import { HealthCheckService, HealthCheck, TypeOrmHealthIndicator, HttpHealthIndicator } from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
    private http: HttpHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      () => this.db.pingCheck('database'),
      () => this.http.pingCheck('payment-api', 'https://payment-api.com/health'),
    ]);
  }

  @Get('liveness')
  @HealthCheck()
  liveness() {
    return this.health.check([]);
  }

  @Get('readiness')
  @HealthCheck()
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database'),
    ]);
  }
}
```

**응답:**
```json
{
  "status": "ok",
  "info": {
    "database": {
      "status": "up"
    },
    "payment-api": {
      "status": "up"
    }
  }
}
```

### Kubernetes 설정

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  template:
    spec:
      containers:
      - name: app
        image: order-service:1.0
        ports:
        - containerPort: 3000
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

**동작:**
- **Liveness 실패 3회**: Pod 재시작
- **Readiness 실패 2회**: Service에서 제거 (트래픽 차단)

## Graceful Shutdown

### 개념

애플리케이션을 종료할 때 처리 중인 요청을 버리면 안 된다. 결제 API 호출 중에 프로세스가 죽으면 돈은 빠졌는데 주문은 실패 처리되는 상황이 생긴다.

Graceful Shutdown은 새로운 요청을 거부하면서 현재 처리 중인 요청은 끝까지 수행한 후 종료하는 방식이다.

**종료 순서:**

```
SIGTERM 수신
  → 새로운 요청 거부 (503 반환)
  → 처리 중인 요청 완료 대기
  → DB 커넥션 풀 정리
  → 메시지 큐 커넥션 종료
  → 프로세스 종료
```

### NestJS Graceful Shutdown 설정

NestJS에서는 `enableShutdownHooks()`로 SIGTERM을 처리한다.

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);

  // Graceful Shutdown 활성화
  app.enableShutdownHooks();

  await app.listen(3000);
  console.log('Application is running on: http://localhost:3000');
}
bootstrap();
```

### 커스텀 종료 처리

DB 트랜잭션이나 외부 리소스를 정리해야 하는 경우가 있다.

```typescript
import { Injectable, OnApplicationShutdown } from '@nestjs/common';

@Injectable()
export class GracefulShutdownService implements OnApplicationShutdown {
  private pendingTasks = 0;

  async onApplicationShutdown(signal?: string): Promise<void> {
    console.info(`Shutdown signal received: ${signal}`);

    // 진행 중인 비동기 작업 완료 대기
    const timeout = 25000; // 25초
    const start = Date.now();

    while (this.pendingTasks > 0) {
      if (Date.now() - start > timeout) {
        console.warn('Tasks did not finish in 25s, forcing shutdown');
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    console.info('Shutdown complete');
  }
}
```

```typescript
import { Injectable, OnApplicationShutdown } from '@nestjs/common';

@Injectable()
export class KafkaShutdownService implements OnApplicationShutdown {
  private running = true;

  async onApplicationShutdown(signal?: string): Promise<void> {
    console.info('Stopping Kafka consumer');
    // Kafka 컨슈머를 먼저 멈춘다
    // 새 메시지를 가져오지 않아야 처리 중인 것만 마무리할 수 있다
    this.running = false;
    await this.waitForInFlightMessages();
  }

  private async waitForInFlightMessages(): Promise<void> {
    // 처리 중인 메시지 완료 대기 로직
  }
}
```

### Kubernetes에서 주의할 점

Kubernetes는 Pod 종료 시 SIGTERM을 보낸 후 `terminationGracePeriodSeconds`(기본 30초) 동안 기다린다. 이 시간이 지나면 SIGKILL로 강제 종료한다.

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["sh", "-c", "sleep 5"]
```

`preStop`에서 5초 대기하는 이유가 있다. SIGTERM과 Service 엔드포인트 제거가 동시에 일어나는데, 타이밍에 따라 이미 종료 중인 Pod에 새 요청이 들어올 수 있다. 5초 정도 기다리면 엔드포인트 제거가 먼저 완료된다.

**주의:** `terminationGracePeriodSeconds`는 `preStop` 시간 + 애플리케이션 종료 시간을 합친 것보다 커야 한다. preStop 5초 + 종료 대기 30초라면 최소 40초 이상으로 설정한다.

## Backpressure (배압)

### 개념

생산자가 소비자보다 빠르면 문제가 생긴다. 요청이 처리 속도보다 빨리 들어오면 메모리가 계속 쌓이다가 OOM(Out Of Memory)으로 터진다.

Backpressure는 소비자가 처리할 수 있는 만큼만 데이터를 받겠다고 생산자에게 알려주는 메커니즘이다.

```
[Backpressure 없는 경우]
Producer → 1000 req/s → Buffer(무한 증가) → Consumer(100 req/s) → OOM

[Backpressure 있는 경우]
Producer → 1000 req/s → Consumer: "100개만 보내" → Producer 속도 조절
```

### NestJS에서의 Backpressure (RxJS)

NestJS는 RxJS를 기반으로 하며, `bufferCount`, `throttleTime` 등으로 Backpressure를 제어한다.

```typescript
import { Controller, Get, Sse } from '@nestjs/common';
import { Observable, from, bufferCount } from 'rxjs';
import { MessageEvent } from '@nestjs/common';

@Controller('events')
export class EventController {
  @Sse('stream')
  streamEvents(): Observable<MessageEvent> {
    return from(this.getEventStream()).pipe(
      // 한 번에 256개씩만 처리
      bufferCount(256),
    ) as unknown as Observable<MessageEvent>;
  }

  private getEventStream(): AsyncIterable<MessageEvent> {
    // 이벤트 스트림 구현
    return {
      [Symbol.asyncIterator]: async function* () {
        // yield events...
      },
    };
  }
}
```

**Backpressure 처리 방법:**

```typescript
import { bufferCount, throttleTime } from 'rxjs/operators';
import { Subject } from 'rxjs';

// 1. 버퍼에 쌓기 (제한적)
// 버퍼가 N개 채워지면 배열로 방출
const buffered$ = source$.pipe(bufferCount(1024));

// 2. 최신 데이터만 유지 (이전 데이터 버림)
// 실시간 모니터링 같은 경우에 적합
const latest$ = source$.pipe(throttleTime(100)); // 100ms마다 최신 값만

// 3. 초과분 버리기 — 처리 못하는 데이터는 그냥 버림
const subject = new Subject<Event>();
// Subject에 backpressure가 쌓이면 구독자가 느린 경우 메시지 유실 가능
```

어떤 방식을 쓸지는 데이터 성격에 따라 다르다. 결제 데이터는 버리면 안 되니 버퍼를 쓰고, 실시간 주가 데이터는 최신 값만 중요하니 throttle을 쓴다.

### Kafka에서의 Backpressure

Kafka 컨슈머는 `max.poll.records`로 한 번에 가져오는 메시지 수를 조절한다.

```yaml
# KafkaJS 설정 예시 (nestjs/microservices)
kafka:
  consumer:
    maxInFlightRequests: 1
    sessionTimeout: 30000
    heartbeatInterval: 3000
```

처리 속도가 느린데 `maxInFlightRequests`가 크면 메시지를 너무 많이 가져와서 처리를 못 끝낼 수 있다.

```typescript
import { Injectable } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';

@Injectable()
export class OrderEventConsumer {
  // 동시 처리량 제어를 위한 세마포어
  private readonly maxConcurrent = 50;
  private currentConcurrent = 0;

  @EventPattern('orders')
  async handleOrder(@Payload() data: OrderEvent): Promise<void> {
    if (this.currentConcurrent >= this.maxConcurrent) {
      // 처리 용량 초과 — 잠시 대기하거나 에러를 던져 재시도 처리
      throw new Error('Processing capacity exceeded');
    }

    this.currentConcurrent++;
    try {
      await this.processOrder(data);
    } finally {
      this.currentConcurrent--;
    }
  }

  private async processOrder(event: OrderEvent): Promise<void> {
    // 주문 처리 로직
  }
}
```

### 동시성 제한 기반 Backpressure

NestJS에서 동시 요청 수를 제한하여 간접적인 Backpressure를 구현할 수 있다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class ConcurrencyLimitMiddleware implements NestMiddleware {
  private readonly maxConcurrent: number;
  private readonly queueLimit: number;
  private currentConcurrent = 0;
  private queue: Array<() => void> = [];

  constructor() {
    this.maxConcurrent = 20; // 최대 동시 처리
    this.queueLimit = 100;  // 큐 제한 (이 이상이면 503)
  }

  use(req: Request, res: Response, next: NextFunction): void {
    if (this.currentConcurrent < this.maxConcurrent) {
      this.currentConcurrent++;
      res.on('finish', () => {
        this.currentConcurrent--;
        if (this.queue.length > 0) {
          const resolve = this.queue.shift()!;
          resolve();
        }
      });
      next();
    } else if (this.queue.length < this.queueLimit) {
      this.queue.push(() => {
        this.currentConcurrent++;
        next();
      });
    } else {
      res.status(503).send('Service overloaded, try again later');
    }
  }
}
```

큐가 가득 차면 요청을 거부해서 자연스럽게 유입 속도가 줄어든다.

## Load Shedding (부하 제거)

### 개념

시스템이 감당할 수 있는 수준 이상의 트래픽이 들어오면 일부 요청을 의도적으로 거부해서 나머지 요청이라도 정상 처리하는 방식이다.

Rate Limiting과 다른 점이 있다. Rate Limiting은 "초당 N개"처럼 고정 비율로 제한하지만, Load Shedding은 현재 시스템 상태(CPU, 메모리, 응답 시간)를 보고 동적으로 결정한다.

```
[Load Shedding 없음]
1000 req/s 유입 → 서버 과부하 → 모든 요청 응답 10초 → 전부 실패

[Load Shedding 적용]
1000 req/s 유입 → 300개 즉시 거부(503) → 700개 정상 처리(200ms)
```

300개를 빠르게 거부하는 게 1000개를 느리게 처리하는 것보다 낫다.

### 동시 요청 수 기반 Load Shedding

현재 동시 요청 수가 한계를 넘으면 요청을 거부한다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoadSheddingMiddleware implements NestMiddleware {
  private activeRequests = 0;
  private readonly maxConcurrentRequests: number;

  constructor() {
    this.maxConcurrentRequests = parseInt(
      process.env.MAX_CONCURRENT_REQUESTS ?? '500',
      10,
    );
  }

  use(req: Request, res: Response, next: NextFunction): void {
    this.activeRequests++;

    res.on('finish', () => {
      this.activeRequests--;
    });

    if (this.activeRequests > this.maxConcurrentRequests) {
      this.activeRequests--;
      res.status(503).json({
        message: 'Service overloaded, try again later',
      });
      return;
    }

    next();
  }
}
```

동시 요청 수를 기준으로 단순하게 제한하는 방식이다. 실무에서는 이것만으로 충분한 경우가 많다.

### 우선순위 기반 Load Shedding

모든 요청을 동등하게 취급하면 안 되는 경우가 있다. 결제 요청은 살리고 상품 목록 조회는 거부하는 식이다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

enum Priority {
  HIGH = 'HIGH',
  LOW = 'LOW',
}

@Injectable()
export class PriorityLoadSheddingMiddleware implements NestMiddleware {
  private activeRequests = 0;

  // 전체 허용 한도
  private static readonly MAX_TOTAL = 500;
  // 높은 우선순위는 전체 한도까지, 낮은 우선순위는 절반까지
  private static readonly LOW_PRIORITY_LIMIT = 250;

  use(req: Request, res: Response, next: NextFunction): void {
    const priority = this.resolvePriority(req);
    this.activeRequests++;

    res.on('finish', () => {
      this.activeRequests--;
    });

    const limit =
      priority === Priority.HIGH
        ? PriorityLoadSheddingMiddleware.MAX_TOTAL
        : PriorityLoadSheddingMiddleware.LOW_PRIORITY_LIMIT;

    if (this.activeRequests > limit) {
      this.activeRequests--;
      res.status(503).setHeader('Retry-After', '5').json({
        message: 'Service overloaded',
      });
      return;
    }

    next();
  }

  private resolvePriority(request: Request): Priority {
    const path = request.path;

    // 결제, 주문 생성은 높은 우선순위
    if (path.startsWith('/api/payments') || path.startsWith('/api/orders')) {
      return Priority.HIGH;
    }
    // 조회성 API는 낮은 우선순위
    return Priority.LOW;
  }
}
```

**Retry-After 헤더를 꼭 넣어야 한다.** 클라이언트가 이 값을 보고 재시도 시점을 결정한다. 넣지 않으면 클라이언트가 즉시 재시도해서 부하가 더 심해진다.

### 시스템 리소스 기반 Load Shedding

Node.js에서 CPU 사용률을 확인해서 판단하는 방식이다.

```typescript
import { Injectable } from '@nestjs/common';
import * as os from 'os';

@Injectable()
export class ResourceAwareLoadShedding {
  shouldShed(): boolean {
    const cpuUsage = os.loadavg()[0] / os.cpus().length; // 1분 평균 로드
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const memoryUsage = (totalMemory - freeMemory) / totalMemory;

    // CPU 로드 0.8 이상이거나 메모리 90% 이상이면 부하 제거
    return cpuUsage > 0.8 || memoryUsage > 0.9;
  }
}
```

이 방식은 OS 수준 메트릭을 보는 거라 GC나 일시적 스파이크에 민감할 수 있다. 실제 운영에서는 이 값을 일정 기간 평균내서 판단하거나, Prometheus 메트릭과 결합해서 사용한다.

### 실무 적용 시 주의사항

**503 응답은 모니터링해야 한다.** Load Shedding이 작동한다는 건 시스템이 한계에 가깝다는 신호다. Grafana에서 503 비율이 일정 수준을 넘으면 알림을 보내야 한다.

**클라이언트 쪽 처리도 필요하다.** 서버가 503을 주면 클라이언트는 Exponential Backoff로 재시도해야 한다. 즉시 재시도하면 Load Shedding의 의미가 없다.

**Load Shedding 임계값은 부하 테스트로 정한다.** 서버가 실제로 몇 개의 동시 요청을 처리할 수 있는지 모르면 임계값을 정할 수 없다. k6나 Artillery로 부하 테스트를 돌려서 응답 시간이 급격히 늘어나는 지점을 찾는다.

## 실무 패턴

### 패턴 1: 외부 API 호출

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom, retry, timer, timeout } from 'rxjs';
import CircuitBreaker from 'opossum';

interface PaymentRequest {
  orderId: string;
  amount: number;
}

interface PaymentResponse {
  status: string;
  message: string;
}

@Injectable()
export class PaymentService {
  private readonly breaker: CircuitBreaker;
  private readonly paymentQueue: PaymentRequest[] = [];

  constructor(private httpService: HttpService) {
    this.breaker = new CircuitBreaker(this.callPaymentApiWithRetry.bind(this), {
      errorThresholdPercentage: 50,
      resetTimeout: 30000,
      timeout: 5000, // 5초 타임아웃
    });

    this.breaker.fallback((request: PaymentRequest) =>
      this.paymentFallback(request),
    );
  }

  private async callPaymentApiWithRetry(
    request: PaymentRequest,
  ): Promise<PaymentResponse> {
    const { data } = await firstValueFrom(
      this.httpService
        .post<PaymentResponse>(process.env.PAYMENT_API_URL!, request)
        .pipe(
          timeout(5000),
          retry({ count: 3, delay: (_, n) => timer(1000 * Math.pow(2, n - 1)) }),
        ),
    );
    return data;
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    return this.breaker.fire(request) as Promise<PaymentResponse>;
  }

  private paymentFallback(request: PaymentRequest): PaymentResponse {
    console.error('Payment failed, using fallback');
    // 결제 정보를 큐에 저장 (나중에 재시도)
    this.paymentQueue.push(request);
    return { status: 'PENDING', message: '결제 처리 중' };
  }
}
```

### 패턴 2: DB 조회

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Inject } from '@nestjs/common';
import { Cache } from 'cache-manager';
import CircuitBreaker from 'opossum';
import { UserEntity } from './user.entity';

@Injectable()
export class UserService {
  private readonly breaker: CircuitBreaker;

  constructor(
    @InjectRepository(UserEntity)
    private userRepository: Repository<UserEntity>,
    @Inject(CACHE_MANAGER) private cacheManager: Cache,
  ) {
    this.breaker = new CircuitBreaker(this.queryUser.bind(this), {
      errorThresholdPercentage: 50,
      resetTimeout: 30000,
      timeout: 5000,
    });

    this.breaker.fallback((userId: string) => this.getUserFromCache(userId));
  }

  private async queryUser(userId: string): Promise<UserEntity> {
    const user = await this.userRepository.findOne({ where: { id: userId } });
    if (!user) throw new Error(`User not found: ${userId}`);
    return user;
  }

  async getUser(userId: string): Promise<UserEntity> {
    const cached = await this.cacheManager.get<UserEntity>(`users:${userId}`);
    if (cached) return cached;

    const user = await (this.breaker.fire(userId) as Promise<UserEntity>);
    await this.cacheManager.set(`users:${userId}`, user, 300);
    return user;
  }

  private async getUserFromCache(userId: string): Promise<UserEntity | null> {
    console.warn('DB query failed, checking cache');
    return this.cacheManager.get<UserEntity>(`users:${userId}`) ?? null;
  }
}
```

### 패턴 3: 마이크로서비스 간 통신

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { firstValueFrom, timeout } from 'rxjs';
import CircuitBreaker from 'opossum';
import { OrderEntity } from './order.entity';

interface OrderRequest {
  productId: string;
  quantity: number;
  paymentInfo: PaymentInfo;
}

interface PaymentInfo {
  method: string;
  amount: number;
}

interface OrderResponse {
  orderId: string;
  status: string;
}

@Injectable()
export class OrderService {
  private readonly inventoryBreaker: CircuitBreaker;
  private readonly paymentBreaker: CircuitBreaker;
  private readonly paymentRetryQueue: Array<{ orderId: string; paymentInfo: PaymentInfo }> = [];

  constructor(
    private httpService: HttpService,
    @InjectRepository(OrderEntity)
    private orderRepository: Repository<OrderEntity>,
    private dataSource: DataSource,
  ) {
    this.inventoryBreaker = new CircuitBreaker(
      this.checkInventoryApi.bind(this),
      { errorThresholdPercentage: 50, resetTimeout: 10000 },
    );
    this.inventoryBreaker.fallback(() => true); // 재고 확인 실패 시 일단 주문 접수

    this.paymentBreaker = new CircuitBreaker(
      this.processPaymentApi.bind(this),
      { errorThresholdPercentage: 50, resetTimeout: 30000 },
    );
    this.paymentBreaker.fallback(
      (orderId: string, paymentInfo: PaymentInfo) => {
        this.paymentRetryQueue.push({ orderId, paymentInfo });
        return { status: 'PENDING', message: '결제 처리 중' };
      },
    );
  }

  async createOrder(request: OrderRequest): Promise<OrderResponse> {
    return this.dataSource.transaction(async (manager) => {
      // 1. 재고 확인 (Circuit Breaker 적용)
      const hasStock = await this.inventoryBreaker.fire(
        request.productId,
        request.quantity,
      ) as boolean;

      if (!hasStock) throw new Error('재고 부족');

      // 2. 주문 생성
      const order = manager.create(OrderEntity, {
        productId: request.productId,
        quantity: request.quantity,
        status: 'PENDING',
      });
      await manager.save(order);

      // 3. 결제 처리 (비동기 + Fallback)
      this.paymentBreaker
        .fire(order.id, request.paymentInfo)
        .catch((e) => {
          console.error(`Payment failed for order: ${order.id}`, e);
          order.status = 'PAYMENT_PENDING';
          this.orderRepository.save(order);
        });

      return { orderId: order.id, status: order.status };
    });
  }

  private async checkInventoryApi(
    productId: string,
    quantity: number,
  ): Promise<boolean> {
    const { data } = await firstValueFrom(
      this.httpService
        .get<boolean>(
          `/inventory/${productId}/check?quantity=${quantity}`,
        )
        .pipe(timeout(3000)),
    );
    return data;
  }

  private async processPaymentApi(
    orderId: string,
    paymentInfo: PaymentInfo,
  ): Promise<{ status: string }> {
    const { data } = await firstValueFrom(
      this.httpService.post<{ status: string }>('/payments', paymentInfo).pipe(
        timeout(5000),
      ),
    );
    return data;
  }
}
```

## 모니터링

### Prometheus 메트릭

```typescript
import { Injectable } from '@nestjs/common';
import { InjectMetric } from '@willsoto/nestjs-prometheus';
import { Counter, Gauge } from 'prom-client';

@Injectable()
export class ResilienceMetricsService {
  constructor(
    @InjectMetric('circuit_breaker_state') private cbStateGauge: Gauge<string>,
    @InjectMetric('retry_attempts_total') private retryCounter: Counter<string>,
  ) {}

  recordCircuitBreakerState(name: string, state: string): void {
    const stateValue = state === 'CLOSED' ? 0 : state === 'OPEN' ? 1 : 0.5;
    this.cbStateGauge.set({ circuit_breaker: name }, stateValue);
  }

  recordRetryAttempt(serviceName: string): void {
    this.retryCounter.inc({ service: serviceName });
  }
}
```

**Grafana 대시보드:**
- Circuit Breaker 상태 (OPEN/CLOSED/HALF_OPEN)
- 실패율
- 재시도 횟수
- 평균 응답 시간

## 참고

- opossum (Circuit Breaker): https://nodeshift.dev/opossum/
- NestJS Terminus (Health Check): https://docs.nestjs.com/recipes/terminus
- Martin Fowler - Circuit Breaker: https://martinfowler.com/bliki/CircuitBreaker.html
- AWS Well-Architected Framework: https://aws.amazon.com/architecture/well-architected/
