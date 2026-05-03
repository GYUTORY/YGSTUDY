---
title: API 멱등성 (Idempotency)
tags: [backend, api, idempotency, payment, redis, kafka, outbox, observability, distributed-systems]
updated: 2026-05-03
---

# API 멱등성 (Idempotency)

## 개요

같은 요청을 여러 번 보내도 결과가 동일하게 유지되는 성질을 멱등성이라 한다. HTTP 메서드 중 GET, PUT, DELETE는 스펙상 멱등하지만, POST는 멱등하지 않다. 결제, 주문, 포인트 차감처럼 POST로 처리하는 상태 변경 API에서 네트워크 타임아웃이나 클라이언트 재시도로 중복 요청이 들어오면 돈이 두 번 빠지거나 주문이 두 개 생기는 사고가 난다.

이 문제를 해결하는 핵심은 **Idempotency-Key**다. 클라이언트가 요청마다 고유 키를 헤더에 담아 보내고, 서버가 이 키로 중복 여부를 판단한다.

## 핵심

### 1. HTTP 메서드별 멱등성

| 메서드 | 멱등 | 안전 | 설명 |
|--------|------|------|------|
| GET | O | O | 조회만 하므로 당연히 멱등 |
| PUT | O | X | 전체 교체라 같은 요청 반복해도 결과 동일 |
| DELETE | O | X | 이미 삭제된 리소스에 다시 DELETE 해도 404일 뿐 |
| PATCH | X | X | 부분 수정이라 연산 방식에 따라 다름 (`balance += 100` 같은 상대값이면 비멱등) |
| POST | X | X | 리소스 생성이라 호출할 때마다 새 리소스 생김 |

POST가 문제다. 결제 API를 POST로 호출하는데 타임아웃이 나면, 클라이언트 입장에서는 성공했는지 실패했는지 알 수 없다. 재시도하면 결제가 두 번 될 수 있다.

### 2. Idempotency-Key 헤더 설계

Stripe, Toss Payments 등 결제 API에서 사실상 표준으로 쓰는 방식이다. 클라이언트가 UUID v4 같은 고유 키를 생성해서 `Idempotency-Key` 헤더에 담아 보낸다.

```
POST /api/v1/payments HTTP/1.1
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "orderId": "ORD-20260415-001",
  "amount": 50000,
  "method": "CARD"
}
```

서버 처리 흐름:

```
1. 요청 수신 → Idempotency-Key 추출
2. 저장소에서 해당 키 조회
   ├── 키가 없음 → 정상 처리 후 결과를 키와 함께 저장
   ├── 키가 있고, 처리 완료 상태 → 저장된 응답을 그대로 반환
   └── 키가 있고, 처리 중 상태 → 409 Conflict 반환 (동시 요청)
```

### 3. 서버 구현

#### Spring Boot + Redis 구현

```java
@Component
public class IdempotencyInterceptor implements HandlerInterceptor {

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    // TTL: 24시간. 이후에는 같은 키로 재요청 가능
    private static final Duration KEY_TTL = Duration.ofHours(24);
    private static final String KEY_PREFIX = "idempotency:";

    public IdempotencyInterceptor(StringRedisTemplate redis, ObjectMapper objectMapper) {
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                             Object handler) throws Exception {
        String idempotencyKey = request.getHeader("Idempotency-Key");

        if (idempotencyKey == null) {
            // Idempotency-Key가 없으면 일반 요청으로 처리
            return true;
        }

        String redisKey = KEY_PREFIX + idempotencyKey;

        // setIfAbsent: 키가 없을 때만 set. 원자적 연산이라 동시 요청도 하나만 통과
        Boolean isNew = redis.opsForValue()
                .setIfAbsent(redisKey, "PROCESSING", KEY_TTL);

        if (Boolean.FALSE.equals(isNew)) {
            // 이미 키가 존재
            String stored = redis.opsForValue().get(redisKey);

            if ("PROCESSING".equals(stored)) {
                // 아직 이전 요청이 처리 중
                response.setStatus(HttpServletResponse.SC_CONFLICT);
                response.setContentType("application/json");
                response.getWriter().write(
                    "{\"code\":\"CONFLICT\",\"message\":\"이전 요청이 처리 중입니다\"}"
                );
                return false;
            }

            // 처리 완료된 응답이 저장되어 있으면 그대로 반환
            response.setStatus(HttpServletResponse.SC_OK);
            response.setContentType("application/json");
            response.getWriter().write(stored);
            return false;
        }

        // 새 요청. 진행
        request.setAttribute("idempotencyKey", redisKey);
        return true;
    }
}
```

처리 완료 후 응답을 저장하는 부분:

```java
@RestController
@RequestMapping("/api/v1/payments")
public class PaymentController {

    private final PaymentService paymentService;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    private static final Duration KEY_TTL = Duration.ofHours(24);

    @PostMapping
    public ResponseEntity<PaymentResponse> createPayment(
            @RequestBody PaymentRequest request,
            HttpServletRequest httpRequest) {

        PaymentResponse result = paymentService.processPayment(request);

        // 멱등성 키가 있으면 결과를 Redis에 저장
        String redisKey = (String) httpRequest.getAttribute("idempotencyKey");
        if (redisKey != null) {
            try {
                String responseJson = objectMapper.writeValueAsString(result);
                redis.opsForValue().set(redisKey, responseJson, KEY_TTL);
            } catch (JsonProcessingException e) {
                // 직렬화 실패해도 결제 자체는 성공이므로 로그만 남김
                log.error("멱등성 응답 저장 실패: key={}", redisKey, e);
            }
        }

        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }
}
```

#### Express + Redis 구현

```javascript
const Redis = require('ioredis');
const redis = new Redis();

const KEY_TTL = 60 * 60 * 24; // 24시간

async function idempotencyMiddleware(req, res, next) {
    const idempotencyKey = req.headers['idempotency-key'];
    if (!idempotencyKey) return next();

    const redisKey = `idempotency:${idempotencyKey}`;

    // NX: 키가 없을 때만 set. EX: TTL 설정
    const result = await redis.set(redisKey, 'PROCESSING', 'EX', KEY_TTL, 'NX');

    if (result === null) {
        // 키가 이미 존재
        const stored = await redis.get(redisKey);

        if (stored === 'PROCESSING') {
            return res.status(409).json({
                code: 'CONFLICT',
                message: '이전 요청이 처리 중입니다'
            });
        }

        // 저장된 응답 반환
        return res.status(200).json(JSON.parse(stored));
    }

    // 원래 res.json을 감싸서 응답 저장
    const originalJson = res.json.bind(res);
    res.json = (body) => {
        redis.set(redisKey, JSON.stringify(body), 'EX', KEY_TTL);
        return originalJson(body);
    };

    next();
}
```

### 4. DB 레벨 중복 방지

Redis 기반 멱등성 체크와 별개로, DB에도 중복 방지 장치를 둬야 한다. Redis가 날아가거나, 키 저장 전에 서버가 죽는 경우를 대비하는 것이다.

#### Unique Constraint 활용

```sql
CREATE TABLE payments (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id    VARCHAR(50) NOT NULL,
    amount      DECIMAL(15, 2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    idempotency_key VARCHAR(36) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_idempotency_key (idempotency_key)
);
```

```java
@Transactional
public PaymentResponse processPayment(PaymentRequest request) {
    try {
        Payment payment = Payment.builder()
                .orderId(request.getOrderId())
                .amount(request.getAmount())
                .idempotencyKey(request.getIdempotencyKey())
                .status(PaymentStatus.PENDING)
                .build();

        paymentRepository.save(payment);

        // PG사 호출
        PgResult pgResult = pgClient.charge(payment);
        payment.complete(pgResult.getTransactionId());
        paymentRepository.save(payment);

        return PaymentResponse.from(payment);

    } catch (DataIntegrityViolationException e) {
        // UK 위반 = 같은 idempotency_key로 이미 결제 존재
        Payment existing = paymentRepository
                .findByIdempotencyKey(request.getIdempotencyKey())
                .orElseThrow();
        return PaymentResponse.from(existing);
    }
}
```

주의할 점이 있다. `DataIntegrityViolationException`을 잡아서 기존 결과를 반환하는 방식은 DB마다 동작이 다르다. MySQL은 UK 위반 시 `DuplicateKeyException`을 던지지만, PostgreSQL은 트랜잭션 전체가 abort 상태가 되어 추가 쿼리가 안 된다. PostgreSQL에서는 `ON CONFLICT` 구문을 쓰거나 별도 트랜잭션에서 조회해야 한다.

```sql
-- PostgreSQL: ON CONFLICT 활용
INSERT INTO payments (order_id, amount, idempotency_key, status)
VALUES ('ORD-001', 50000, '550e8400-...', 'PENDING')
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING *;
```

### 5. Redis 분산 락 패턴

동시에 같은 멱등성 키로 요청이 들어오는 경우를 더 정밀하게 제어하려면 분산 락을 쓴다. `SET NX`만으로도 기본적인 동시성 제어가 되지만, 처리 시간이 길어질 때 TTL이 만료되는 문제가 있다.

#### Redisson 분산 락 적용

```java
@Service
public class PaymentService {

    private final RedissonClient redisson;
    private final PaymentRepository paymentRepository;
    private final PgClient pgClient;

    public PaymentResponse processPayment(PaymentRequest request) {
        String lockKey = "lock:payment:" + request.getIdempotencyKey();
        RLock lock = redisson.getLock(lockKey);

        boolean acquired;
        try {
            // waitTime: 최대 5초 대기, leaseTime: 30초 후 자동 해제
            acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("락 획득 중 인터럽트 발생");
        }

        if (!acquired) {
            throw new ConflictException("동일 요청 처리 중");
        }

        try {
            // 이미 처리된 요청인지 확인
            return paymentRepository
                    .findByIdempotencyKey(request.getIdempotencyKey())
                    .map(PaymentResponse::from)
                    .orElseGet(() -> executePayment(request));
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    private PaymentResponse executePayment(PaymentRequest request) {
        Payment payment = Payment.create(request);
        paymentRepository.save(payment);

        PgResult pgResult = pgClient.charge(payment);
        payment.complete(pgResult.getTransactionId());
        paymentRepository.save(payment);

        return PaymentResponse.from(payment);
    }
}
```

Redisson의 `tryLock`은 내부적으로 Lua 스크립트를 써서 원자적으로 동작한다. `leaseTime`을 설정하면 서버가 죽어도 일정 시간 후 락이 자동 해제된다. 설정하지 않으면 Redisson의 watchdog이 30초마다 갱신하는데, 서버가 죽으면 watchdog도 같이 죽어서 결국 해제된다.

### 6. 멱등성 키 설계 시 고려사항

#### 키 생성 주체

클라이언트가 생성한다. 서버가 생성하면 "키를 받기 위한 요청"과 "실제 요청" 두 번을 보내야 하는데, 첫 번째 요청에서 타임아웃 나면 다시 원점이다.

```javascript
// 클라이언트 측 키 생성
const idempotencyKey = crypto.randomUUID();

const response = await fetch('/api/v1/payments', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey
    },
    body: JSON.stringify({ orderId: 'ORD-001', amount: 50000 })
});
```

#### 키 형식

UUID v4가 무난하다. 충돌 확률이 사실상 0이고, 대부분의 언어에서 기본 제공한다. 간혹 `{userId}:{orderId}:{timestamp}` 같은 조합 키를 쓰는 경우도 있는데, 비즈니스 로직이 키 생성에 결합되는 단점이 있다.

#### TTL 설정

TTL은 비즈니스 요구사항에 따라 다르다. 결제 API라면 24시간 정도가 적당하다. 너무 짧으면 정당한 재시도를 막고, 너무 길면 Redis 메모리를 잡아먹는다.

```
결제 API: 24시간
주문 생성: 1시간
일반 리소스 생성: 10분 ~ 1시간
```

#### 같은 키, 다른 요청 본문

같은 Idempotency-Key로 다른 요청 본문을 보내면 어떻게 할 것인가? Stripe는 422 에러를 반환한다. 요청 본문의 해시를 키와 함께 저장하고, 재요청 시 해시를 비교한다.

```java
// 요청 본문 해시 비교
String bodyHash = DigestUtils.sha256Hex(objectMapper.writeValueAsString(request));
String storedHash = redis.opsForHash().get(redisKey, "bodyHash");

if (storedHash != null && !storedHash.equals(bodyHash)) {
    // 같은 키인데 다른 본문
    throw new UnprocessableEntityException(
        "동일한 Idempotency-Key로 다른 요청을 보낼 수 없습니다"
    );
}
```

### 7. 실무에서 겪는 문제들

#### PG사 호출 후 서버가 죽는 경우

결제가 PG사에서는 성공했는데, 응답을 저장하기 전에 서버가 죽으면 상태 불일치가 발생한다. 이 경우 PG사의 거래 조회 API로 상태를 확인하는 보상 로직이 필요하다.

```
1. 클라이언트 → 서버: 결제 요청
2. 서버 → PG사: 결제 실행 (성공)
3. 서버 다운 (응답 저장 실패)
4. 클라이언트 재시도 → 서버: 같은 Idempotency-Key
5. 서버: Redis에 키 없음, DB에도 없음 → 새 요청으로 판단
6. 서버 → PG사: 결제 실행 → 이중 결제 발생
```

해결 방법: 결제 전에 DB에 `PENDING` 상태로 먼저 저장하고, 재시도 시 `PENDING` 상태인 레코드가 있으면 PG사에 거래 조회를 한다.

```java
@Transactional
public PaymentResponse processPayment(PaymentRequest request) {
    Optional<Payment> existing = paymentRepository
            .findByIdempotencyKey(request.getIdempotencyKey());

    if (existing.isPresent()) {
        Payment payment = existing.get();
        if (payment.getStatus() == PaymentStatus.PENDING) {
            // PG사에서 실제 거래 상태 확인
            PgResult pgResult = pgClient.inquire(payment.getOrderId());
            if (pgResult.isSuccess()) {
                payment.complete(pgResult.getTransactionId());
                paymentRepository.save(payment);
            } else {
                payment.fail();
                paymentRepository.save(payment);
            }
        }
        return PaymentResponse.from(payment);
    }

    // PENDING 상태로 먼저 저장
    Payment payment = Payment.create(request);
    payment.setStatus(PaymentStatus.PENDING);
    paymentRepository.save(payment);

    // PG사 호출
    PgResult pgResult = pgClient.charge(payment);
    if (pgResult.isSuccess()) {
        payment.complete(pgResult.getTransactionId());
    } else {
        payment.fail();
    }
    paymentRepository.save(payment);

    return PaymentResponse.from(payment);
}
```

#### Redis 장애 시 대응

Redis가 죽으면 멱등성 체크를 못 한다. 이때 선택지는 두 가지다:

- **요청을 거부**: 안전하지만 서비스가 중단된다
- **DB로 폴백**: UK로 중복을 막되, 성능이 떨어진다

실무에서는 보통 DB 폴백을 선택하고, Redis 복구 후 다시 전환한다. Circuit Breaker 패턴을 적용하면 자동 전환이 가능하다.

```java
@Component
public class IdempotencyStore {

    private final StringRedisTemplate redis;
    private final IdempotencyKeyRepository repository;
    private final CircuitBreaker circuitBreaker;

    public boolean tryAcquire(String key) {
        try {
            return circuitBreaker.run(() -> {
                Boolean result = redis.opsForValue()
                        .setIfAbsent("idempotency:" + key, "PROCESSING",
                                Duration.ofHours(24));
                return Boolean.TRUE.equals(result);
            });
        } catch (Exception e) {
            // Redis 장애 시 DB 폴백
            try {
                repository.save(new IdempotencyRecord(key));
                return true;
            } catch (DataIntegrityViolationException ex) {
                return false;
            }
        }
    }
}
```

#### 네트워크 분단과 클라이언트 재시도가 겹친 사고

실제로 본 이중 결제 사고를 단순화한 시나리오다. 결제 트래픽이 몰리는 시간대에 PG사 응답이 느려지면서 발생했다.

```
00:00:00.000  클라이언트 → 서버: POST /payments (Idempotency-Key: K1)
00:00:00.050  서버: Redis에 K1 = PROCESSING 저장 (TTL 24h)
00:00:00.100  서버 → PG사: 결제 요청
00:00:30.000  서버 ↔ PG사 사이 네트워크 일시 단절
00:00:35.000  서버: 응답 타임아웃. 500 에러로 응답하려는 순간
00:00:35.001  서버: OOM으로 프로세스 강제 종료 (응답이 클라이언트에 도달 못함)
00:00:35.500  PG사: 결제는 사실 성공. 응답 보냈으나 받을 서버가 없음
00:00:36.000  클라이언트: 타임아웃 감지, 자동 재시도 (같은 키 K1)
00:00:36.100  새 인스턴스: Redis 조회 → K1 = PROCESSING → 409
00:00:36.200  클라이언트: 409를 일시 오류로 판단, 5초 후 재시도
              ... 영원히 PROCESSING 상태에 머무는 중 ...
01:00:00.000  운영자가 키를 수동으로 지우고 결제 상태 정합성 점검
```

문제는 두 단계로 나뉜다.

첫째, `PROCESSING` 상태에 24시간 TTL을 그대로 걸어 두면 서버가 죽었을 때 영원히 그 상태에 갇힌다. `PROCESSING` 단계는 짧은 TTL(예: 60초)로 두고, 정상 처리가 끝나면 응답과 함께 긴 TTL로 갱신한다.

```java
// 처리 시작: 60초 TTL
redis.opsForValue().setIfAbsent(key, "PROCESSING", Duration.ofSeconds(60));

// 처리 완료: 응답 본문 저장 + 24시간 TTL로 덮어쓰기
redis.opsForValue().set(key, responseJson, Duration.ofHours(24));
```

둘째, PG사에는 결제가 됐는데 우리 쪽 흔적이 사라졌다. 클라이언트 재시도가 새 요청으로 인식되면 두 번째 결제가 나간다. 막으려면 두 가지를 병행한다.

- PG 호출 전에 DB에 `PENDING` 상태로 먼저 INSERT 한다. UK는 `idempotency_key`에 건다.
- 재시도가 들어왔을 때 `PENDING` 레코드가 있으면 PG사 거래 조회 API를 호출해서 실제 상태를 동기화한다.

복구 후에는 `PENDING` 상태가 일정 시간 이상 지속된 결제 건을 배치로 정리한다. PG 거래 조회로 상태를 맞추는 잡을 분당 단위로 따로 돌린다. 결제 도메인에서 멱등성 키 하나로 모든 걸 막을 수 있다고 믿으면 이런 사고를 피하기 어렵다. Redis, DB UK, PG 조회 보상까지 3중 방어선을 깔아야 한다.

## GET 요청의 캐시 키와 Idempotency-Key 구분

GET이 멱등하니까 캐시 키와 멱등성 키가 같지 않냐는 질문이 많다. 다르다.

캐시 키는 같은 입력에 같은 출력을 빠르게 돌려주려는 목적이다. ETag, `Cache-Control`, CDN 캐시가 모두 이 범주다. 키는 보통 URL, 쿼리 파라미터, 일부 헤더(Vary)로 만든다. 응답 변경이 즉시 반영될 필요가 없다.

Idempotency-Key는 상태 변경 요청이 중복 실행되지 않도록 막는 락이다. POST, PATCH 같은 비멱등 메서드에 붙는다. 키는 클라이언트가 매 요청마다 새로 만들고, 서버는 이 키로 "이전 처리 결과가 있나"를 확인한다.

| 구분 | 캐시 키 | Idempotency-Key |
|------|---------|-----------------|
| 목적 | 응답 재사용 | 중복 실행 방지 |
| 적용 메서드 | GET 위주 | POST, PATCH |
| 키 생성 주체 | 서버, CDN | 클라이언트 |
| 키 구성 | URL + 쿼리 + 헤더 | UUID 등 임의 값 |
| TTL | 분~시간 | 시간~일 |
| 키 충돌 의미 | 캐시 히트 | 중복 요청 |

매번 다른 결과를 줘야 하는 GET(예: `/api/orders?status=PENDING` 실시간 조회)은 캐시도 멱등성 키도 안 쓴다. 비결정적 GET을 무리하게 캐시하면 같은 요청에 다른 응답이 나가서 멱등성이 깨진다.

같은 엔드포인트에 두 개념이 동시에 필요한 경우는 거의 없다. 결제 API에 캐시를 걸고 싶다는 요구가 들어오면 십중팔구 잘못 짠 설계다.

## 응답 직렬화 시 시간 의존적 필드 주의

저장된 멱등 응답을 그대로 돌려줄 때 시간 의존적 필드가 들어 있으면 문제가 생긴다.

```json
{
  "paymentId": "pay_abc123",
  "amount": 50000,
  "status": "COMPLETED",
  "processedAt": "2026-04-15T10:30:00Z",
  "responseTime": "2026-04-15T10:30:01.234Z"
}
```

`processedAt`은 실제 결제 처리 시각이라 저장된 값을 그대로 돌려줘야 한다. 문제는 `responseTime`처럼 응답 직렬화 시점에 `Instant.now()`로 채우는 필드다. 첫 요청과 재시도 응답이 다른 시각을 갖게 된다.

클라이언트 SDK가 응답 해시로 무결성 검증을 한다면 이 지점에서 검증이 깨진다. "재시도했더니 응답이 다르다"는 버그가 올라오면 대부분 이 패턴이다.

```java
// 잘못된 패턴
public class PaymentResponse {
    private String paymentId;
    private Long amount;
    private String status;

    @JsonProperty("responseTime")
    public Instant getResponseTime() {
        return Instant.now(); // 직렬화마다 새 값
    }
}

// 올바른 패턴
public class PaymentResponse {
    private final String paymentId;
    private final Long amount;
    private final String status;
    private final Instant processedAt; // 결제 처리 시점에 한 번 결정
}
```

응답 객체를 만들 때 시각을 한 번만 정하고, 직렬화 단계에서는 새로 만들지 않는다. Redis에 저장되는 JSON과 처음 응답으로 나간 JSON이 정확히 같아야 한다.

서버 헤더(`Date`, `X-Request-Id`)는 매 응답마다 다르게 나가도 된다. 헤더는 멱등성 비교 대상이 아니라는 점을 클라이언트와 미리 합의해 둔다. 응답 본문 내부에 `traceId`나 `requestId`를 박는 관행이 있다면, 그건 첫 요청의 값을 저장해서 그대로 돌려줘야 한다.

랜덤 값도 마찬가지다. 응답에 `nonce`나 임의 토큰이 들어간다면, 응답 객체가 만들어질 때 결정해서 저장하고 재시도 시 그대로 반환한다. 매번 새로 생성하면 안 된다.

## 메시지 큐의 멱등성

API 호출만 멱등성을 따지면 안 된다. 비동기 처리에서도 같은 메시지가 두 번 처리되는 일이 자주 생긴다. Kafka는 기본이 at-least-once 보장이라, 컨슈머가 메시지 처리 후 오프셋 커밋 전에 죽으면 같은 메시지를 다시 받는다.

### Producer 측: Kafka Idempotent Producer

```properties
# producer.properties
enable.idempotence=true
acks=all
retries=2147483647
max.in.flight.requests.per.connection=5
```

`enable.idempotence=true`를 켜면 프로듀서가 PID(Producer ID)와 시퀀스 번호를 메시지에 붙인다. 브로커는 이 조합으로 중복을 거른다. 프로듀서 내부 재시도로 같은 메시지가 두 번 가도 브로커에는 한 번만 적재된다.

주의할 점: 이건 프로듀서 세션 내 멱등성만 보장한다. 프로듀서가 재시작하면 PID가 바뀌어서 같은 메시지를 또 보낼 수 있다. 재시작에도 멱등성을 유지하려면 트랜잭셔널 프로듀서를 쓴다.

```java
Properties props = new Properties();
props.put("bootstrap.servers", "kafka:9092");
props.put("enable.idempotence", "true");
props.put("transactional.id", "payment-producer-1"); // 인스턴스별 고유
props.put("key.serializer", StringSerializer.class.getName());
props.put("value.serializer", StringSerializer.class.getName());

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.initTransactions();

try {
    producer.beginTransaction();
    producer.send(new ProducerRecord<>("payment-events", paymentId, eventJson));
    producer.commitTransaction();
} catch (KafkaException e) {
    producer.abortTransaction();
    throw e;
}
```

`transactional.id`는 프로듀서 인스턴스별로 고유해야 한다. 쿠버네티스 환경에서 파드 이름으로 만들거나, 정적 ID를 부여한다. 같은 ID를 쓰는 새 인스턴스가 뜨면 이전 트랜잭션을 fence(차단)한다.

### Consumer 측: processed_messages 테이블 패턴

브로커 멱등성만으로는 컨슈머 중복 처리를 막지 못한다. 컨슈머는 자기가 처리한 메시지의 식별자를 별도 테이블에 저장해서 중복을 거른다.

```sql
CREATE TABLE processed_messages (
    message_id   VARCHAR(64) PRIMARY KEY,
    topic        VARCHAR(100) NOT NULL,
    partition_id INT NOT NULL,
    offset_val   BIGINT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_processed_at (processed_at)
);
```

```java
@KafkaListener(topics = "payment-events")
@Transactional
public void handlePaymentEvent(ConsumerRecord<String, String> record) {
    Header msgIdHeader = record.headers().lastHeader("messageId");
    String messageId = msgIdHeader != null
            ? new String(msgIdHeader.value())
            : record.topic() + "-" + record.partition() + "-" + record.offset();

    try {
        ProcessedMessage processed = ProcessedMessage.builder()
                .messageId(messageId)
                .topic(record.topic())
                .partitionId(record.partition())
                .offsetVal(record.offset())
                .build();
        processedMessageRepository.save(processed);
    } catch (DataIntegrityViolationException e) {
        // 이미 처리한 메시지. 비즈니스 로직 건너뛰고 오프셋만 진행
        log.info("중복 메시지 스킵: messageId={}", messageId);
        return;
    }

    // 비즈니스 로직은 같은 트랜잭션 안에서 실행
    PaymentEvent event = objectMapper.readValue(record.value(), PaymentEvent.class);
    paymentService.handleEvent(event);
}
```

`processed_messages` INSERT와 비즈니스 로직을 같은 트랜잭션에 묶는 게 핵심이다. 비즈니스 로직 실패 시 INSERT도 롤백되어야 재시도가 동작한다. INSERT만 성공하고 비즈니스 로직이 실패한 채 커밋되면 메시지가 유실된다.

오래된 레코드는 주기적으로 삭제한다. Kafka `retention.ms`보다 길게만 유지하면 된다. 7일이면 대부분 충분하다. 1년치를 쌓으면 PK 인덱스가 무거워져서 INSERT 자체가 느려진다.

`message_id` 식별자는 프로듀서 측에서 비즈니스 식별자(주문번호, 결제ID)로 부여하는 게 가장 안정적이다. `topic-partition-offset`은 Kafka 리밸런싱이나 토픽 이전 시 식별자 의미가 달라질 수 있다.

## Outbox 패턴과의 결합

결제 완료 시 외부 시스템(정산, 알림)에 이벤트를 보내야 한다고 하자. 단순하게 짜면 이렇다.

```java
@Transactional
public PaymentResponse processPayment(PaymentRequest request) {
    Payment payment = paymentRepository.save(Payment.create(request));
    pgClient.charge(payment);
    payment.complete();
    paymentRepository.save(payment);

    // 이벤트 발행
    kafkaProducer.send("payment-completed", payment.toEvent());

    return PaymentResponse.from(payment);
}
```

문제: DB 트랜잭션과 Kafka 발행이 다른 시스템이라 원자적 처리가 안 된다. DB 커밋 성공 후 Kafka 발행 실패, 또는 Kafka 발행 후 DB 커밋 실패가 가능하다. 멱등성 키로 결제 자체는 한 번만 일어나게 막아도 이벤트 발행은 여전히 별개 문제다.

Outbox 패턴은 이벤트를 같은 DB 트랜잭션 안의 `outbox` 테이블에 INSERT 하고, 별도 워커가 그 테이블을 읽어 메시지 큐로 내보낸다.

```sql
CREATE TABLE outbox (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    aggregate_id VARCHAR(64) NOT NULL,
    event_type   VARCHAR(50) NOT NULL,
    payload      TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    INDEX idx_unpublished (published_at, created_at)
);
```

```java
@Transactional
public PaymentResponse processPayment(PaymentRequest request) {
    Payment payment = paymentRepository.save(Payment.create(request));
    pgClient.charge(payment);
    payment.complete();
    paymentRepository.save(payment);

    // 같은 트랜잭션 안에서 outbox INSERT
    OutboxEvent event = OutboxEvent.builder()
            .aggregateId(payment.getId().toString())
            .eventType("PaymentCompleted")
            .payload(objectMapper.writeValueAsString(payment.toEvent()))
            .build();
    outboxRepository.save(event);

    return PaymentResponse.from(payment);
}
```

별도 워커:

```java
@Scheduled(fixedDelay = 1000)
public void publishOutboxEvents() {
    List<OutboxEvent> unpublished = outboxRepository
            .findTop100ByPublishedAtIsNullOrderByCreatedAt();

    for (OutboxEvent event : unpublished) {
        try {
            ProducerRecord<String, String> record = new ProducerRecord<>(
                "payment-events",
                event.getAggregateId(),
                event.getPayload()
            );
            // 컨슈머 멱등성용 메시지 ID 헤더
            record.headers().add("messageId",
                String.valueOf(event.getId()).getBytes());

            producer.send(record).get();
            outboxRepository.markPublished(event.getId());
        } catch (Exception e) {
            log.error("Outbox 이벤트 발행 실패: id={}", event.getId(), e);
            // 다음 주기에 재시도
        }
    }
}
```

워커가 Kafka 발행 후 `published_at` 갱신 전에 죽으면 같은 이벤트를 다시 보낸다. 그래서 컨슈머 측은 앞에서 본 `processed_messages` 테이블로 멱등성을 다시 보장해야 한다. Outbox는 발행 누락 없음(at-least-once)을, 컨슈머 멱등성은 처리 중복 없음을 책임진다. 둘이 합쳐져야 effectively-once에 가까워진다.

Debezium 같은 CDC 도구를 써서 outbox 테이블의 변경을 직접 Kafka로 흘려보내는 방식도 있다. 자체 워커 운영 부담은 줄지만, Debezium 운영 부담이 새로 생긴다. 트래픽이 어느 수준 이상이면 Debezium 쪽이 유리하고, 그 미만이면 단순 폴링 워커로 충분하다.

결제와 이벤트 발행을 동시에 멱등으로 처리하려면, 결제 멱등성 키와 outbox INSERT가 모두 같은 DB 트랜잭션 안에 있어야 한다. 결제 멱등성 키 검사 → DB INSERT(결제 + outbox) → 커밋, 이 순서를 깨면 결제는 한 번인데 이벤트가 두 번 나가거나, 그 반대 상황이 생긴다.

## API Gateway 레벨 멱등성

애플리케이션 코드에 멱등성 처리를 일일이 박지 않고 게이트웨이 레이어에서 처리하는 방법도 있다. 마이크로서비스가 많을 때 같은 코드를 반복하지 않아도 된다.

### AWS API Gateway

REST API에는 기본 멱등성 기능이 없다. Lambda 통합이나 Lambda Authorizer로 직접 구현하거나, 앞단에 CloudFront + Lambda@Edge를 둬서 키를 검증한다. AWS SDK 일부(예: Step Functions의 `StartExecution`, SQS의 `SendMessage`에서 `MessageDeduplicationId`)는 `clientToken` 또는 별도 파라미터로 멱등성을 자체 지원한다.

DynamoDB를 키 저장소로 쓰는 패턴이 흔하다. 조건부 PUT(`attribute_not_exists`)으로 SET-NX 흉내를 내고, TTL 속성으로 자동 만료를 건다.

```python
# Lambda Authorizer 예시
import boto3
import time

ddb = boto3.client('dynamodb')

def lambda_handler(event, context):
    key = event['headers'].get('Idempotency-Key')
    if not key:
        return generate_policy('Allow', event['methodArn'])

    try:
        ddb.put_item(
            TableName='idempotency_keys',
            Item={
                'key': {'S': key},
                'status': {'S': 'PROCESSING'},
                'ttl': {'N': str(int(time.time()) + 86400)}
            },
            ConditionExpression='attribute_not_exists(#k)',
            ExpressionAttributeNames={'#k': 'key'}
        )
        return generate_policy('Allow', event['methodArn'])
    except ddb.exceptions.ConditionalCheckFailedException:
        # 이미 처리 중이거나 처리 완료된 키
        return generate_policy('Deny', event['methodArn'])
```

### Kong Idempotency Plugin

Kong은 커뮤니티 플러그인으로 멱등성을 지원한다. 라우트나 서비스 단위로 활성화한다.

```yaml
plugins:
  - name: idempotency
    route: payment-route
    config:
      header_name: Idempotency-Key
      ttl: 86400
      storage: redis
      redis_host: redis.internal
      redis_port: 6379
```

Kong이 Redis에 키와 응답을 저장하고, 같은 키 재요청에는 저장된 응답을 그대로 돌려준다. 업스트림 서비스는 멱등성 코드를 안 가져도 된다.

게이트웨이 레벨 처리의 한계도 있다. 응답 본문 전체를 Redis에 쌓으므로 응답이 큰 API에서 메모리 부담이 커진다. 게이트웨이가 응답을 저장하기 전에 업스트림이 비동기 처리를 시작했다면, 게이트웨이 입장에서는 처리 완료 여부를 정확히 모른다. 결제처럼 정합성이 중요한 도메인은 게이트웨이만 믿지 말고 애플리케이션 레이어에도 멱등성 코드를 둬야 안전하다.

게이트웨이 레벨은 보조 방어선으로, 애플리케이션 레벨이 주 방어선이다. 게이트웨이만 통과하고 업스트림이 실패하면 게이트웨이가 저장한 "성공 응답"이 잘못된 정보가 된다.

## 관찰성 (메트릭)

운영하다 보면 멱등성 동작이 의도대로 되고 있는지 메트릭으로 확인해야 한다. 사고 전에 이상 징후를 잡으려면 다음 지표를 본다.

### 핵심 메트릭

| 메트릭 | 설명 | 이상 신호 |
|--------|------|-----------|
| `idempotency_key_hits_total` | 같은 키로 재요청이 들어와 캐시 응답을 돌려준 횟수 | 평소 대비 급증 시 클라이언트 재시도 폭주 |
| `idempotency_key_conflicts_total` | 처리 중 키에 재요청이 들어와 409 반환한 횟수 | 증가 시 처리 시간이 길어졌거나 클라이언트가 너무 빨리 재시도 |
| `idempotency_lock_wait_seconds` | 분산 락 획득까지 대기한 시간 | P99 상승 시 처리 지연 의심 |
| `idempotency_key_missing_total` | Idempotency-Key 헤더 없이 들어온 비멱등 요청 수 | 일부 클라이언트가 키를 안 보냄 |
| `idempotency_body_mismatch_total` | 같은 키로 다른 본문이 온 횟수 | 클라이언트 버그 또는 의도적 공격 |

Micrometer로는 이렇게 기록한다.

```java
@Component
public class IdempotencyMetrics {

    private final Counter hitCounter;
    private final Counter conflictCounter;
    private final Counter bodyMismatchCounter;
    private final Timer lockWaitTimer;

    public IdempotencyMetrics(MeterRegistry registry) {
        this.hitCounter = Counter.builder("idempotency_key_hits_total")
                .description("멱등 키 캐시 히트")
                .register(registry);
        this.conflictCounter = Counter.builder("idempotency_key_conflicts_total")
                .description("멱등 키 충돌 (처리 중)")
                .register(registry);
        this.bodyMismatchCounter = Counter.builder("idempotency_body_mismatch_total")
                .description("같은 키, 다른 본문")
                .register(registry);
        this.lockWaitTimer = Timer.builder("idempotency_lock_wait_seconds")
                .description("분산 락 대기 시간")
                .register(registry);
    }

    public void recordHit() { hitCounter.increment(); }
    public void recordConflict() { conflictCounter.increment(); }
    public void recordBodyMismatch() { bodyMismatchCounter.increment(); }
    public Timer.Sample startLockWait() { return Timer.start(); }
    public void stopLockWait(Timer.Sample sample) { sample.stop(lockWaitTimer); }
}
```

### 알림 임계치

서비스마다 다르지만 출발점은 이 정도다.

- 충돌율(`conflicts / total_requests`) 5분 평균 1% 초과 → 경고
- 락 대기 P99가 2초 초과 → 경고
- 본문 불일치 1분에 10건 이상 → 클라이언트 측 버그 가능성, 보안팀 통보
- 키 누락율(`missing / total_requests`) 5% 초과 → 클라이언트 SDK 점검

충돌율이 갑자기 오르는 건 보통 두 가지 원인이다. PG사 응답이 느려져 처리 시간이 늘었거나, 클라이언트 측 재시도 정책이 너무 공격적으로 바뀌었다. PG 응답 시간 메트릭과 함께 봐야 원인을 좁힐 수 있다.

### 로깅 시 민감정보 주의

키 자체는 로그에 남기지만 요청 본문을 통째로 남기면 카드번호 같은 민감정보가 새기 쉽다. 멱등성 디버깅에는 키, 상태, 처리 시각, 결과 코드만 있으면 충분하다.

```java
log.info("idempotency key={} status={} action={} duration_ms={}",
    idempotencyKey, status, action, durationMs);
```

본문 해시 비교를 한다면 해시 값만 남긴다. 원본 본문이나 해시 입력값은 로그에 남기지 않는다.

## 멱등성 테스트 전략

코드 짠다고 끝이 아니다. 동시 요청과 재시도 시나리오를 자동화 테스트로 검증해 둬야 한다. 멱등성 버그는 부하 테스트나 운영에서 처음 발견되면 이미 사고다.

### 동시 요청 테스트 (JUnit + ExecutorService)

```java
@SpringBootTest
@AutoConfigureMockMvc
class PaymentIdempotencyTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private PaymentRepository paymentRepository;

    @Test
    void 동일_멱등성_키로_동시_100건_요청해도_결제는_한_건만() throws Exception {
        String idempotencyKey = UUID.randomUUID().toString();
        String requestBody = """
            {"orderId": "ORD-TEST-001", "amount": 50000}
            """;

        int threadCount = 100;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch readyLatch = new CountDownLatch(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);
        AtomicInteger successCount = new AtomicInteger();
        AtomicInteger conflictCount = new AtomicInteger();

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                readyLatch.countDown();
                try {
                    startLatch.await();
                    MvcResult result = mockMvc.perform(post("/api/v1/payments")
                            .header("Idempotency-Key", idempotencyKey)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(requestBody))
                            .andReturn();

                    int status = result.getResponse().getStatus();
                    if (status == 200 || status == 201) successCount.incrementAndGet();
                    else if (status == 409) conflictCount.incrementAndGet();
                } catch (Exception e) {
                    // 테스트 외 예외는 카운팅에서 제외
                }
            });
        }

        readyLatch.await();
        startLatch.countDown(); // 100개 스레드 동시 출발
        executor.shutdown();
        executor.awaitTermination(30, TimeUnit.SECONDS);

        // DB 결제 레코드는 정확히 1건
        long paymentCount = paymentRepository
                .countByIdempotencyKey(idempotencyKey);
        assertThat(paymentCount).isEqualTo(1);

        // 성공 + 충돌 = 100
        assertThat(successCount.get() + conflictCount.get()).isEqualTo(100);
    }
}
```

`CountDownLatch`로 모든 스레드가 준비될 때까지 기다렸다가 동시에 출발시키는 게 핵심이다. `executor.submit`만 100번 호출하면 스레드가 순차적으로 시작돼서 진짜 동시성 테스트가 안 된다. 두 개의 latch(준비, 시작)를 쓰는 패턴은 동시성 테스트의 정석이다.

### 재시도 시나리오 테스트 (Jest + supertest)

```javascript
const request = require('supertest');
const app = require('../app');
const redis = require('../redis');
const pgClient = require('../pgClient');

describe('결제 API 멱등성', () => {
    afterEach(async () => {
        await redis.flushdb();
        jest.restoreAllMocks();
    });

    test('타임아웃 후 재시도 시 같은 응답을 반환한다', async () => {
        const idempotencyKey = crypto.randomUUID();
        const payload = { orderId: 'ORD-001', amount: 50000 };

        const first = await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send(payload)
            .expect(201);

        const second = await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send(payload)
            .expect(200);

        expect(second.body.paymentId).toBe(first.body.paymentId);
        expect(second.body.amount).toBe(first.body.amount);
    });

    test('같은 키로 다른 본문 보내면 422', async () => {
        const idempotencyKey = crypto.randomUUID();

        await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send({ orderId: 'ORD-001', amount: 50000 })
            .expect(201);

        await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send({ orderId: 'ORD-001', amount: 99999 }) // 금액 변경
            .expect(422);
    });

    test('PG 호출 실패 후 재시도 시 PENDING 복구 경로를 탄다', async () => {
        const idempotencyKey = crypto.randomUUID();
        const payload = { orderId: 'ORD-002', amount: 30000 };

        // 첫 호출에서 PG가 타임아웃 → PENDING 상태로 남음
        jest.spyOn(pgClient, 'charge').mockRejectedValueOnce(
            new Error('Network timeout')
        );

        await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send(payload)
            .expect(500);

        // 재시도: PG 조회 API는 SUCCESS 응답
        jest.spyOn(pgClient, 'inquire').mockResolvedValueOnce({
            success: true,
            transactionId: 'tx_123'
        });

        const retry = await request(app)
            .post('/api/v1/payments')
            .set('Idempotency-Key', idempotencyKey)
            .send(payload)
            .expect(200);

        expect(retry.body.status).toBe('COMPLETED');
        expect(retry.body.transactionId).toBe('tx_123');
    });
});
```

### 부하 테스트로 키 충돌 검증

k6로 같은 멱등성 키를 가진 요청을 초당 수백 건씩 던져 본다. 결제는 한 건만 일어나야 하고, 나머지는 캐시 히트나 409여야 한다. CI에 매번 돌리지는 못하더라도 큰 변경 후에는 한 번씩 돌려본다.

```javascript
// k6 script
import http from 'k6/http';
import { check } from 'k6';

const idempotencyKey = '550e8400-e29b-41d4-a716-446655440000';

export const options = {
    vus: 200,
    duration: '30s',
};

export default function () {
    const res = http.post('http://localhost:8080/api/v1/payments',
        JSON.stringify({ orderId: 'ORD-001', amount: 50000 }),
        {
            headers: {
                'Content-Type': 'application/json',
                'Idempotency-Key': idempotencyKey,
            },
        }
    );
    check(res, {
        'status 200/201/409': (r) =>
            r.status === 200 || r.status === 201 || r.status === 409,
    });
}
```

테스트 종료 후 DB에서 해당 키로 만들어진 결제 레코드가 정확히 1건인지 확인한다. 2건 이상이면 멱등성 코드에 버그가 있다는 뜻이다.

### Redis 장애 시뮬레이션

Testcontainers로 Redis 컨테이너를 띄우고 테스트 중간에 stop 해서 폴백 경로를 확인한다.

```java
@SpringBootTest
@Testcontainers
class IdempotencyFallbackTest {

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
            .withExposedPorts(6379);

    @Test
    void Redis_장애_시_DB_폴백으로_중복_차단() throws Exception {
        // 정상 요청 1건
        sendPayment("key-1");

        // Redis 강제 종료
        redis.stop();

        // 같은 키로 재요청 → DB UK로 차단되어야 함
        try {
            sendPayment("key-1");
            fail("중복이 차단되지 않음");
        } catch (DataIntegrityViolationException expected) {
            // 정상
        }
    }
}
```

이런 테스트들이 한 번 깔리면 다음 리팩터링 때도 멱등성이 안 깨진다는 보장이 생긴다. 결제 도메인은 회귀 테스트의 가치가 특히 크다. 사고 한 번이면 전사적으로 영향이 가니까.
