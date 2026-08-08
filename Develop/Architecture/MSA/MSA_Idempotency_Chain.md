---
title: MSA 서비스 체인 멱등성
tags: [microservices, architecture]
updated: 2026-08-06
---

# MSA 서비스 체인 멱등성

단일 서비스에서 멱등성을 구현하는 건 어렵지 않다. DB에 멱등성 키 테이블 하나 만들고, 요청이 들어올 때마다 키를 확인하면 된다. 문제는 서비스가 체인으로 엮이는 순간부터 시작된다.

주문 서비스 → 재고 서비스 → 결제 서비스 → 배송 서비스 순으로 호출이 이어질 때, 어느 지점에서 타임아웃이 발생하거나 네트워크 오류가 나면 재시도가 들어온다. 이때 각 서비스가 독립적으로 멱등성을 처리하지 않으면 중복 결제가 발생하거나, 재고가 두 번 차감되거나, 배송이 두 번 생성된다.

## 멱등성 키 전파 방식

서비스 체인에서 멱등성 키를 어떻게 전달할지는 두 가지 방식이 있다.

### 상위 키 재사용

클라이언트가 생성한 멱등성 키를 체인 전체에서 그대로 사용하는 방식이다.

```
Client → 주문서비스(key=abc123) → 결제서비스(key=abc123) → 포인트서비스(key=abc123)
```

단순하다는 게 장점이다. 어느 서비스에서 문제가 생겨도 재시도 시 동일한 키로 멱등성 검사를 통과한다.

단점은 키가 여러 서비스 컨텍스트에 걸쳐 쓰이면서 충돌 가능성이 생긴다는 점이다. 포인트 서비스와 쿠폰 서비스가 같은 키 `abc123`을 받으면, 각 서비스 DB에서 키를 분리해서 관리해야 한다. 키 자체에 서비스 prefix를 붙이는 방법으로 해결한다.

```java
// 멱등성 키 저장 시 서비스 범위를 키에 포함
String idempotencyKey = "payment:" + upstreamKey;  // payment:abc123
String idempotencyKey = "point:" + upstreamKey;     // point:abc123
```

### 파생 키 생성

각 서비스가 상위 키에서 하위 키를 파생시키는 방식이다.

```
Client(key=abc123) → 주문서비스 → 결제서비스(derived=payment:abc123) → 포인트서비스(derived=point:abc123)
```

HMAC이나 단순 해시로 파생 키를 생성한다.

```java
String deriveKey(String parentKey, String serviceScope) {
    return HmacUtils.hmacSha256Hex(serviceScope, parentKey);
}

// 주문 서비스에서 결제 서비스 호출 시
String paymentKey = deriveKey(incomingKey, "payment-service");
httpClient.post("/payment")
    .header("Idempotency-Key", paymentKey)
    .execute();
```

파생 키의 핵심은 동일한 입력이 항상 동일한 출력을 만든다는 것이다. 재시도가 들어오면 상위 서비스가 같은 입력으로 같은 파생 키를 생성하고, 하위 서비스는 이미 처리한 키라는 걸 인식한다.

### 방식 선택 기준

두 서비스가 완전히 다른 팀이 관리하고 키 네임스페이스 충돌이 없다면 상위 키 재사용이 더 간단하다. 체인이 깊거나 외부 시스템을 호출할 때는 파생 키를 만드는 편이 낫다.

현실적으로는 두 방식을 섞어 쓰는 경우가 많다. 같은 도메인 내 서비스끼리는 키를 그대로 전파하고, 외부 결제 게이트웨이나 타 팀 서비스를 호출할 때는 파생 키를 만들어서 보낸다.

## Saga 단계별 멱등 처리

Saga 패턴에서 각 단계는 독립적으로 멱등성을 보장해야 한다. 오케스트레이터가 실패한 단계를 재시도할 때 이미 성공한 단계를 다시 실행하는 경우가 생기기 때문이다.

### 상태 기반 멱등성 테이블

각 Saga 단계를 별도의 멱등성 레코드로 관리한다.

```sql
CREATE TABLE saga_idempotency (
    saga_id         VARCHAR(64)  NOT NULL,
    step_name       VARCHAR(64)  NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    status          VARCHAR(16)  NOT NULL,  -- PROCESSING, COMPLETED, FAILED
    response        TEXT,
    created_at      TIMESTAMP    NOT NULL,
    completed_at    TIMESTAMP,
    PRIMARY KEY (saga_id, step_name)
);
```

단계 실행 전에 `(saga_id, step_name)` 쌍으로 레코드를 확인한다. `COMPLETED`면 저장된 응답을 그대로 반환한다. `PROCESSING`이면 실행 중이라는 응답을 돌려주거나 잠시 대기한다.

```java
SagaIdempotency record = sagaIdempotencyRepo.findBySagaIdAndStep(sagaId, "payment");

if (record != null && record.getStatus().equals("COMPLETED")) {
    return deserialize(record.getResponse());
}

// 실제 처리
Result result = paymentService.process(command);

// 결과 저장
sagaIdempotencyRepo.save(sagaId, "payment", "COMPLETED", serialize(result));
return result;
```

`PROCESSING` 상태를 두는 이유는 같은 단계가 동시에 실행되는 경우를 막기 위해서다. 멱등성 레코드 삽입 시 `INSERT ... ON CONFLICT DO NOTHING`을 쓰고, 삽입 실패 시 기존 레코드 상태를 확인하는 방식으로 처리한다.

### 이벤트 기반 Saga에서의 멱등성

코레오그래피 방식에서는 이벤트 소비 자체를 멱등으로 만들어야 한다.

```java
@KafkaListener(topics = "order-created")
public void handleOrderCreated(OrderCreatedEvent event) {
    String messageId = event.getMessageId();

    if (processedMessageRepo.exists(messageId)) {
        log.info("Duplicate message, skipping: {}", messageId);
        return;
    }

    reserveInventory(event);

    // TTL 설정 필수 — 메시지 큐의 최대 재전달 기간보다 길게
    processedMessageRepo.save(messageId, Duration.ofDays(7));
}
```

`processedMessageRepo`에는 Redis를 쓰는 경우가 많다. TTL이 너무 짧으면 재시도 시 멱등성 보장이 깨지므로 메시지 큐의 최대 재전달 기간을 기준으로 충분히 여유 있게 설정한다.

## 보상 트랜잭션 멱등성

보상 트랜잭션은 일반 트랜잭션보다 멱등성이 더 중요하다. 이미 롤백된 작업을 한 번 더 롤백하면 데이터가 망가진다.

### 보상 트랜잭션이 처리해야 하는 두 가지 경우

원래 트랜잭션이 성공했고 이를 되돌리는 경우가 있다. 이미 차감된 재고를 원복하거나, 이미 승인된 결제를 취소한다. 반면 원래 트랜잭션이 실패했거나 아예 실행되지 않아서 보상 자체가 무의미한 경우도 있다. 이걸 `No-Op 보상`이라고 부른다. 원래 작업이 없었으니 보상할 것도 없다.

```java
public CompensationResult compensatePayment(String sagaId, String orderId) {
    Optional<PaymentRecord> payment = paymentRepo.findBySagaId(sagaId);

    if (payment.isEmpty()) {
        // 결제 자체가 실행된 적 없음 - No-Op
        return CompensationResult.NO_OP;
    }

    if (payment.get().getStatus() == REFUNDED) {
        // 이미 환불 완료 - 멱등 처리
        return CompensationResult.ALREADY_COMPENSATED;
    }

    refund(payment.get());
    return CompensationResult.SUCCESS;
}
```

### 보상 멱등성 키

보상 트랜잭션도 별도의 멱등성 키를 가져야 한다. 원본 트랜잭션 키와 구분하기 위해 접두사를 붙인다.

```java
String compensationKey = "compensate:" + originalSagaId + ":" + stepName;
```

보상 트랜잭션 실행 전에 이 키를 확인하고, 이미 실행됐으면 캐싱된 결과를 반환한다.

### 외부 시스템 보상

외부 결제 게이트웨이 같은 서비스의 보상이 멱등하지 않을 수 있다. 이때는 보상 실행 결과를 로컬 DB에 저장하고, 이후 재시도 시 외부 API를 호출하지 않고 로컬 결과를 반환한다.

```java
String compensationKey = "pg:refund:" + paymentId;

Optional<RefundResult> cachedResult = idempotencyStore.get(compensationKey);
if (cachedResult.isPresent()) {
    return cachedResult.get();
}

RefundResult result = paymentGateway.refund(paymentId, amount);

// TTL은 충분히 길게
idempotencyStore.save(compensationKey, result, Duration.ofDays(30));
return result;
```

## 클라이언트 SDK 재시도 키 영속화

모바일 앱이나 웹 클라이언트에서 요청을 보낼 때 네트워크가 끊기거나 앱이 종료되면 재시도 시 새로운 멱등성 키를 생성하는 실수를 저지른다. 그러면 서버가 중복 요청을 막지 못한다.

### 로컬 저장소 기반 영속화

요청을 보내기 전에 멱등성 키를 로컬 저장소에 저장하고, 성공 응답을 받은 후에 삭제한다.

```kotlin
class IdempotentApiClient(private val prefs: SharedPreferences) {

    fun placeOrder(orderRequest: OrderRequest): OrderResponse {
        val operationKey = "place_order:${orderRequest.cartId}"

        // 기존 키 조회 또는 새 키 생성
        val idempotencyKey = prefs.getString(operationKey, null)
            ?: UUID.randomUUID().toString().also {
                prefs.edit().putString(operationKey, it).apply()
            }

        return try {
            val response = api.placeOrder(orderRequest, idempotencyKey)
            prefs.edit().remove(operationKey).apply()
            response
        } catch (e: NetworkException) {
            // 네트워크 오류 - 키 유지, 재시도 시 같은 키 사용
            throw e
        } catch (e: HttpException) {
            if (e.code() in 400..499) {
                // 클라이언트 오류 - 요청이 잘못됐으니 키 삭제
                prefs.edit().remove(operationKey).apply()
            }
            throw e
        }
    }
}
```

### 멱등성 키 생명주기

멱등성 키를 언제 삭제할지가 핵심이다.

2xx 응답이 왔을 때는 키를 삭제한다. 다음에 같은 작업을 하면 새로운 요청으로 처리해야 한다. 4xx 응답이 왔을 때도 키를 삭제하고 수정된 요청으로 재시도해야 한다. 같은 키로 재시도하면 서버가 캐싱된 4xx를 그대로 반환해버린다. 5xx나 네트워크 오류의 경우는 키를 유지하고 동일 키로 재시도한다. 서버가 요청을 처리했는지 알 수 없기 때문이다.

```kotlin
fun handleResponse(response: Response, operationKey: String) {
    when {
        response.isSuccessful    -> deleteKey(operationKey)
        response.code in 400..499 -> deleteKey(operationKey)
        // 5xx, 타임아웃 - 키 유지
    }
}
```

### 앱 재시작 후 미완료 요청 처리

앱이 재시작되면 이전에 실행 중이던 요청의 상태를 알 수 없다. 로컬 저장소에 키가 남아있으면 해당 요청이 완료되지 않았다고 보고 재시도한다.

```kotlin
class PendingRequestRecovery(private val prefs: SharedPreferences) {

    fun recoverOnAppStart() {
        val pendingKeys = prefs.all.filter { it.key.startsWith("place_order:") }

        pendingKeys.forEach { (operationKey, idempotencyKey) ->
            val result = queryRequestStatus(idempotencyKey as String)

            when (result) {
                is Success    -> prefs.edit().remove(operationKey).apply()
                is NotFound   -> retryRequest(operationKey, idempotencyKey)
                is InProgress -> scheduleRetry(operationKey, idempotencyKey)
            }
        }
    }
}
```

일부 서버는 멱등성 키로 요청 상태를 조회하는 별도 API를 제공한다. 이 API가 없으면 재시도 자체가 멱등 처리를 하므로 단순히 재요청해도 된다.

### 네트워크 변경 대응

Wi-Fi에서 LTE로 전환되거나 VPN이 끊길 때 진행 중인 요청이 실패한다. 재시도 큐에 멱등성 키와 함께 요청을 넣고, 네트워크가 복구되면 자동으로 재시도하는 방식으로 처리한다.

```kotlin
class RetryQueue(private val db: LocalDatabase) {

    fun enqueue(request: PendingRequest) {
        db.insert(PendingRequestEntity(
            idempotencyKey = request.idempotencyKey,
            requestBody    = serialize(request),
            retryCount     = 0,
            nextRetryAt    = Instant.now()
        ))
    }

    fun processQueue() {
        db.getPendingRequests(before = Instant.now()).forEach { entity ->
            try {
                execute(deserialize(entity.requestBody), entity.idempotencyKey)
                db.delete(entity)
            } catch (e: Exception) {
                db.updateRetry(entity, nextRetryAt = exponentialBackoff(entity.retryCount))
            }
        }
    }
}
```

로컬 DB에 요청을 저장하면 앱이 강제 종료되거나 기기가 꺼져도 미완료 요청이 유실되지 않는다. 재시도 횟수와 다음 재시도 시간을 함께 저장해서 지수 백오프를 구현한다.

## 주의사항

**멱등성 키 TTL**: 서버에서 멱등성 키를 영구 보존하면 안 된다. 주문의 경우 최소 24시간에서 7일 정도가 일반적이다. TTL이 너무 짧으면 재시도 시 멱등성 보장이 깨진다.

**분산 환경에서의 키 저장소**: 여러 서버 인스턴스가 멱등성 키를 공유해야 한다. 로컬 캐시만 쓰면 다른 인스턴스로 요청이 라우팅될 때 중복 처리가 발생한다. Redis나 DB를 공유 저장소로 써야 한다.

**응답 캐싱 크기**: 서버가 멱등성 키에 매핑된 응답을 캐싱할 때, 응답 크기가 크면 저장 비용이 늘어난다. 응답을 압축하거나 응답의 핵심 식별자만 저장하는 방법을 고려한다.

**Saga 오케스트레이터 장애**: 오케스트레이터 자체가 죽으면 Saga 상태를 복구해야 한다. Saga 상태와 멱등성 키를 같은 DB 트랜잭션에 저장하면 일관성을 유지할 수 있다.
