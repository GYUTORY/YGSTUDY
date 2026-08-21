---
title: UUIDv4 — 실무에서 쓰다 보면 생기는 문제들
tags: [backend, database, security]
updated: 2026-08-02
---

# UUIDv4 — 실무에서 쓰다 보면 생기는 문제들

UUID를 처음 쓸 때는 "그냥 `UUID.randomUUID()` 하면 되는 거 아닌가"로 시작한다. 그러다 DB 인덱스 성능이 이상하거나, IDOR 취약점을 지적받거나, 로그에서 요청 추적이 안 돼서 뒤늦게 제대로 알게 된다.

## RFC 4122 포맷과 랜덤 구조

UUIDv4는 RFC 4122에서 정의한 128비트 식별자다. 텍스트로 표현하면 `550e8400-e29b-41d4-a716-446655440000` 형태다.

```
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
```

- 세 번째 블록의 첫 자리는 항상 `4` (버전 표시)
- 네 번째 블록의 첫 자리는 `8`, `9`, `a`, `b` 중 하나 (variant 표시)
- 나머지 122비트가 랜덤

128비트 중 버전 4비트와 variant 2비트가 고정이라 실제 랜덤 엔트로피는 122비트다. 이 정도면 충돌 확률이 현실적으로 무시할 수 있는 수준이다. 10억 개를 생성해도 충돌 확률이 10^-18 수준이다.

주의할 점은 `Math.random()`처럼 시드 기반 PRNG를 쓰면 안 된다는 것이다. 반드시 암호학적으로 안전한 난수 생성기(CSPRNG)를 써야 한다. 언어별 표준 라이브러리는 대부분 이걸 기본으로 쓰지만, 직접 구현하거나 오래된 써드파티 라이브러리를 쓸 때는 확인이 필요하다.

## 언어별 생성

**Java**

```java
import java.util.UUID;

UUID uuid = UUID.randomUUID();
String uuidStr = uuid.toString(); // "550e8400-e29b-41d4-a716-446655440000"
```

Java의 `UUID.randomUUID()`는 내부적으로 `SecureRandom`을 쓴다. 별도 설정 없이 그냥 쓰면 된다. Spring 환경에서 엔티티 ID로 쓸 때는 `@GeneratedValue(strategy = GenerationType.AUTO)`와 함께 쓰면 Hibernate가 알아서 처리하지만, `@GeneratedValue` 없이 직접 할당하는 쪽이 제어하기 편하다.

```java
@Entity
public class Order {
    @Id
    private String id;

    @PrePersist
    private void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }
}
```

**Node.js**

```javascript
import { randomUUID } from 'crypto';

const uuid = randomUUID();
// '550e8400-e29b-41d4-a716-446655440000'
```

Node.js 14.17.0부터 `crypto.randomUUID()`를 기본 제공한다. 이전에는 `uuid` 패키지를 많이 썼는데, 신규 프로젝트라면 표준 모듈을 쓰는 게 낫다. `uuid` 패키지를 써야 한다면 `v4()` 함수를 쓰면 된다.

```javascript
import { v4 as uuidv4 } from 'uuid';
const uuid = uuidv4();
```

**Python**

```python
import uuid

uid = uuid.uuid4()
print(str(uid))  # 매번 다른 값 — 예: 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
```

Python 표준 라이브러리의 `uuid.uuid4()`는 OS의 `/dev/urandom`이나 `CryptGenRandom`을 쓴다. 별도 설치 없이 쓸 수 있다.

## DB 저장 방식 — CHAR(36) vs BINARY(16)

UUID를 DB에 저장할 때 두 가지 방식이 있다.

**CHAR(36)**: 하이픈 포함 문자열 그대로 저장. 눈으로 읽을 수 있고, 쿼리 작성이 간단하다. 대신 36바이트를 쓰고, 문자열 비교라 인덱스 성능이 숫자 타입보다 떨어진다.

**BINARY(16)**: UUID를 바이트 배열로 변환해서 저장. 16바이트로 저장 공간이 절반 이하고, 바이너리 비교라 인덱스 비교가 빠르다. 대신 읽을 때 변환 과정이 필요하고, 직접 SQL을 칠 때 불편하다.

MySQL에서 BINARY(16)으로 저장하는 코드:

```sql
-- 저장
INSERT INTO orders (id, ...) VALUES (UUID_TO_BIN(UUID()), ...);
-- 조회
SELECT BIN_TO_UUID(id) as id, ... FROM orders WHERE id = UUID_TO_BIN('550e8400-e29b-41d4-a716-446655440000');
```

JPA에서는 `@Column(columnDefinition = "BINARY(16)")`으로 지정하고, AttributeConverter로 변환 로직을 구현한다.

```java
@Converter(autoApply = true)
public class UUIDConverter implements AttributeConverter<UUID, byte[]> {

    @Override
    public byte[] convertToDatabaseColumn(UUID uuid) {
        if (uuid == null) return null;
        ByteBuffer bb = ByteBuffer.wrap(new byte[16]);
        bb.putLong(uuid.getMostSignificantBits());
        bb.putLong(uuid.getLeastSignificantBits());
        return bb.array();
    }

    @Override
    public UUID convertToEntityAttribute(byte[] bytes) {
        if (bytes == null) return null;
        ByteBuffer bb = ByteBuffer.wrap(bytes);
        return new UUID(bb.getLong(), bb.getLong());
    }
}
```

트래픽이 크지 않고 개발 편의성이 중요하면 CHAR(36)으로 시작해도 무방하다. 실제로 CHAR(36)과 BINARY(16)의 성능 차이가 병목으로 나타나려면 인덱스가 많이 걸린 테이블에 수천만 건 이상이 들어가야 한다.

## MySQL InnoDB 페이지 분할 문제

UUIDv4가 DB에서 성능 문제를 일으키는 주된 원인은 랜덤성 때문이다.

MySQL InnoDB는 PK를 기준으로 B-Tree 인덱스를 구성하고, 클러스터드 인덱스 구조상 PK 순서로 데이터를 물리적으로 정렬해서 저장한다. AUTO_INCREMENT처럼 단조증가하는 값이면 항상 마지막 페이지에 데이터가 추가되므로 페이지 분할이 거의 없다.

UUIDv4는 완전 랜덤이라 새로운 UUID가 기존 UUID들 사이 어딘가에 끼어들어가야 한다. 그 위치의 페이지가 꽉 차 있으면 페이지 분할이 발생한다. 페이지 분할은 I/O가 늘어나고, 페이지 단편화가 생기고, 결국 읽기 성능도 떨어지는 연쇄 효과로 이어진다.

**언제 전환을 고려해야 하는가**

테이블에 수백만 건 이상 데이터가 쌓이고, 해당 테이블에 초당 수백 건 이상 INSERT가 발생하고, PK로 범위 조회나 정렬이 자주 일어난다면 UUIDv7이나 ULID로 전환할 이유가 생긴다.

UUIDv7은 RFC 9562에서 정의한 타임스탬프 기반 UUID다. 앞 48비트가 밀리초 단위 타임스탬프라 단조증가하고, 뒤쪽은 랜덤으로 채운다. InnoDB 페이지 분할 문제가 거의 없고, UUID 포맷을 그대로 유지한다는 점에서 기존 UUID를 쓰던 코드 변경이 적다.

ULID는 26자리 Crockford Base32 인코딩 문자열이다. `01ARZ3NDEKTSV4RRFFQ69G5FAV` 형태다. 앞 10자리가 타임스탬프, 뒤 16자리가 랜덤이다. 정렬 가능하고 대소문자 구분이 없어서 URL에 그대로 쓰기 좋다. UUID 표준 포맷이 아니라 기존 UUID 컬럼과 호환이 안 되는 게 단점이다.

트래픽이 낮거나 UUID를 PK로 쓰지 않고 보조 컬럼으로만 쓴다면 굳이 전환할 필요 없다.

## 실무 사용 패턴

**세션 ID**

세션 ID로 UUIDv4를 쓰는 건 흔한 패턴이다. 랜덤 122비트는 세션 토큰 충돌 방지로 충분하다. 다만 세션 ID를 쿠키에 직접 담는다면 HttpOnly, Secure 설정은 별개로 챙겨야 한다. UUID를 쓴다고 세션이 안전해지는 게 아니다.

**멱등성 키**

결제 API나 메시지 발행처럼 중복 요청을 막아야 하는 경우, 클라이언트가 요청마다 고유한 키를 생성해서 헤더에 담아 보낸다.

```
POST /payments
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

서버는 이 키를 받아서 Redis나 DB에 저장하고, 같은 키로 중복 요청이 오면 첫 번째 요청의 결과를 그대로 반환한다. 클라이언트가 이 키를 UUIDv4로 생성해서 보내면 충돌 확률이 사실상 없다.

**요청 추적**

서비스 간 요청 흐름을 추적할 때 correlation ID(trace ID)로 UUIDv4를 쓴다. 요청이 들어오면 UUID를 하나 생성해서 로그에 남기고, 하위 서비스 호출 시 헤더에 담아 전파한다.

```java
// 필터나 인터셉터에서
String traceId = UUID.randomUUID().toString();
MDC.put("traceId", traceId);
request.setAttribute("traceId", traceId);

// 하위 서비스 호출 시
restTemplate.exchange(url, method, entityWithHeader("X-Trace-Id", traceId), ...);
```

로그에 `traceId`가 찍히면 Kibana나 CloudWatch에서 필터링해서 요청 흐름 전체를 볼 수 있다.

## IDOR 취약점 대응

IDOR(Insecure Direct Object Reference)는 공격자가 URL의 리소스 ID를 바꿔서 다른 사용자의 데이터에 접근하는 취약점이다.

AUTO_INCREMENT로 생성한 숫자 ID를 API에 그대로 노출하면 `/orders/1001`, `/orders/1002`처럼 추측이 가능하다. UUIDv4를 외부 노출 ID로 쓰면 추측이 불가능해져서 IDOR를 방어하는 첫 단계가 된다.

그런데 UUID를 쓴다고 IDOR가 자동으로 해결되는 게 아니다. ID를 알아도 권한 검사를 하지 않으면 여전히 취약하다. UUID는 "추측을 어렵게 할 뿐"이고, 실제 방어는 서버에서 요청한 사용자가 해당 리소스에 접근 권한이 있는지 반드시 검증해야 한다.

**외부 노출 ID 분리**

내부적으로 숫자 PK를 쓰고, 외부에 노출하는 ID는 별도 UUID 컬럼을 두는 방식을 쓰는 경우가 많다.

```sql
CREATE TABLE orders (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    public_id  CHAR(36) NOT NULL UNIQUE DEFAULT (UUID()),
    user_id    BIGINT NOT NULL,
    ...
);
```

```java
// API 응답에는 public_id만 노출
{
    "orderId": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PENDING"
}

// 내부 처리에서는 id(BIGINT)로 조회
Order order = orderRepository.findByPublicId(publicId)
    .orElseThrow(() -> new NotFoundException("주문을 찾을 수 없습니다"));

// 권한 검사는 별도로
if (!order.getUserId().equals(currentUserId)) {
    throw new ForbiddenException("접근 권한이 없습니다");
}
```

이렇게 분리하면 내부 인덱스 성능은 BIGINT PK로 유지하면서, 외부 노출 ID는 UUID로 추측 불가능하게 만들 수 있다. UUID 컬럼에는 반드시 UNIQUE 인덱스를 걸어야 한다.

PK 자체를 UUID로 하느냐, 별도 컬럼으로 두느냐는 팀마다 다르다. 조인이 많은 구조라면 BIGINT PK가 유리하고, 분산 환경에서 여러 DB 인스턴스가 충돌 없이 ID를 생성해야 한다면 UUID PK가 유리하다.
