---
title: API 멱등성 (Idempotency)
tags: [backend, api, idempotency, payment, redis, distributed-systems]
updated: 2026-04-15
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
