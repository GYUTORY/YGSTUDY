---
title: UUIDv4 — 실무에서 쓰다 보면 생기는 문제들
tags: [backend, database, security]
updated: 2026-09-06
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

128비트 중 버전 4비트와 variant 2비트가 고정이라 실제 랜덤 엔트로피는 122비트다. 10억 개를 생성해도 충돌 확률이 10^-18 수준이다.

## CSPRNG와 컨테이너 환경 엔트로피

`Math.random()`처럼 시드 기반 PRNG를 UUID 생성에 쓰면 안 된다. 반드시 암호학적으로 안전한 난수 생성기(CSPRNG)를 써야 한다. 언어별 표준 라이브러리는 대부분 이걸 기본으로 쓰지만, 컨테이너 환경에서는 의도치 않게 CSPRNG가 제대로 동작하지 않는 경우가 있다.

문제는 엔트로피 풀이다. Linux에서 `/dev/random`은 OS가 수집한 엔트로피가 충분할 때만 값을 반환하고, 부족하면 블로킹한다. 새로 기동한 컨테이너는 하드웨어 이벤트, 디스크 I/O, 네트워크 패킷 같은 엔트로피 소스가 부족해서 UUID 생성 첫 시도에서 수 초간 멈추는 현상이 나온다.

Java의 `SecureRandom`은 기본적으로 `NativePRNG` 알고리즘을 쓰는데, JVM 옵션에 따라 `/dev/random`을 시드 소스로 쓸 수 있다. Java 컨테이너라면 이 옵션을 명시적으로 지정해야 한다.

```bash
# Dockerfile이나 JVM 기동 옵션에 추가
-Djava.security.egd=file:/dev/./urandom
```

`/dev/./urandom`처럼 우회 경로를 쓰는 이유가 있다. `/dev/urandom`을 직접 명시하면 일부 JVM 버전에서 무시하고 다른 소스를 택하는 경우가 있어서, 이 형태가 관행이 됐다.

Node.js의 `crypto.randomUUID()`는 OpenSSL CSPRNG를 쓰고, Python도 `os.urandom()`을 쓴다. 두 언어는 이 문제가 거의 없다. Go의 `crypto/rand`도 `/dev/urandom`을 직접 쓴다.

더 주의해야 하는 상황은 VM 스냅샷 복제다. 동일한 AMI나 VMware 클론으로 여러 인스턴스를 동시에 기동하면 `/dev/urandom`의 시드 상태가 동일할 수 있다. 이론적으로 동일한 UUID 시퀀스가 나올 수 있는 상황이다. 대응은 기동 시 엔트로피를 추가로 주입하거나(`rngd`, `haveged`), 클론 후 강제로 엔트로피 풀을 리셋하는 방식이다. 커널 5.18 이후부터는 `/dev/random`과 `/dev/urandom`이 동일한 풀을 쓰도록 바뀌어서 블로킹 문제 자체가 없지만, 운영 환경의 커널 버전을 항상 통제할 수 없다.

## 언어별 생성

**Java**

```java
import java.util.UUID;

UUID uuid = UUID.randomUUID();
String uuidStr = uuid.toString(); // "550e8400-e29b-41d4-a716-446655440000"
```

Java의 `UUID.randomUUID()`는 내부적으로 `SecureRandom`을 쓴다. Spring 환경에서 엔티티 ID로 쓸 때는 `@GeneratedValue(strategy = GenerationType.AUTO)`와 함께 쓰면 Hibernate가 처리하지만, `@GeneratedValue` 없이 직접 할당하는 쪽이 제어하기 편하다.

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

Python 표준 라이브러리의 `uuid.uuid4()`는 OS의 `/dev/urandom`이나 `CryptGenRandom`을 쓴다.

**Go**

Go 표준 라이브러리에는 UUID 패키지가 없다. `github.com/google/uuid`가 사실상 표준으로 쓰인다.

```go
import "github.com/google/uuid"

id := uuid.New() // 내부적으로 crypto/rand 사용
fmt.Println(id.String()) // "550e8400-e29b-41d4-a716-446655440000"
```

직접 `crypto/rand`로 만들 수도 있다.

```go
import (
    "crypto/rand"
    "fmt"
)

func newUUIDv4() string {
    b := make([]byte, 16)
    if _, err := rand.Read(b); err != nil {
        panic(err)
    }
    b[6] = (b[6] & 0x0f) | 0x40 // version 4
    b[8] = (b[8] & 0x3f) | 0x80 // variant
    return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
        b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}
```

버전·variant 비트를 직접 셋팅하는 코드가 낯설게 보이지만, RFC 4122 스펙 그대로다. 프로덕션 코드에서는 `google/uuid`를 쓰는 게 실수를 줄인다.

## UUID 유효성 검증

외부에서 UUID를 받아서 처리할 때, 형식 검사를 건너뛰면 불필요한 DB 조회가 발생하거나 하위 서비스에 잘못된 값이 전달된다.

UUIDv4를 정확히 검증하는 정규식은 버전과 variant 비트까지 확인한다.

```
^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$
```

소문자만 허용한다. 대소문자 무관하게 받으려면 대문자도 포함한다.

```
^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$
```

네 번째 블록의 첫 자리가 `[89ab]`인 이유: RFC 4122 variant 필드는 최상위 2비트가 `10`이어야 한다. `8`(1000), `9`(1001), `a`(1010), `b`(1011)가 이 조건을 만족한다.

언어별로 표준 라이브러리가 파싱을 제공하는 경우가 많아서, 정규식보다 그쪽을 쓰는 게 낫다.

```java
// Java — 잘못된 형식이면 IllegalArgumentException
try {
    UUID parsed = UUID.fromString(input);
    if (parsed.version() != 4) {
        throw new IllegalArgumentException("UUIDv4가 아닙니다");
    }
} catch (IllegalArgumentException e) {
    throw new BadRequestException("유효하지 않은 UUID입니다");
}
```

```python
import uuid

try:
    parsed = uuid.UUID(input_str, version=4)
except ValueError:
    raise ValueError("유효하지 않은 UUIDv4입니다")
```

```go
import "github.com/google/uuid"

parsed, err := uuid.Parse(input)
if err != nil {
    return errors.New("유효하지 않은 UUID")
}
if parsed.Version() != uuid.Version(4) {
    return errors.New("UUIDv4가 아닙니다")
}
```

Node.js는 표준 라이브러리에 파싱 함수가 없어서 정규식을 쓴다.

```javascript
const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isValidUUIDv4(value) {
    return UUID_V4_REGEX.test(value);
}
```

버전까지 검증하느냐는 상황에 따라 다르다. 외부 시스템에서 들어오는 값이라면 "UUID 형식인지"만 보는 게 충분한 경우도 많다. 내부에서 UUIDv4임을 보장해야 한다면 버전 비트까지 확인한다.

## DB 저장 방식

**MySQL: CHAR(36) vs BINARY(16)**

MySQL에서 UUID를 저장할 때 두 가지 방식이 있다.

CHAR(36)은 하이픈 포함 문자열 그대로 저장한다. 눈으로 읽을 수 있고, 쿼리 작성이 간단하다. 36바이트를 쓰고, 문자열 비교라 인덱스 성능이 숫자 타입보다 떨어진다.

BINARY(16)은 UUID를 바이트 배열로 변환해서 저장한다. 16바이트로 저장 공간이 절반 이하고, 바이너리 비교라 인덱스 비교가 빠르다. 읽을 때 변환 과정이 필요하고, 직접 SQL을 칠 때 불편하다.

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

트래픽이 크지 않고 개발 편의성이 중요하면 CHAR(36)으로 시작해도 무방하다. CHAR(36)과 BINARY(16)의 성능 차이가 병목으로 나타나려면 인덱스가 많이 걸린 테이블에 수천만 건 이상이 들어가야 한다.

**PostgreSQL: 네이티브 uuid 타입**

PostgreSQL은 `uuid` 타입을 기본으로 지원한다. 내부적으로 16바이트로 저장하고, 텍스트 표현과 바이너리 표현을 자동으로 처리한다. MySQL처럼 별도 변환 함수가 필요 없다.

```sql
CREATE TABLE orders (
    id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);

-- 비교할 때 타입 변환 없이 그냥 문자열로 쓴다
SELECT * FROM orders WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

`gen_random_uuid()`는 PostgreSQL 13부터 기본 제공한다. 13 이전 버전이라면 `uuid-ossp` 확장을 설치하고 `uuid_generate_v4()`를 쓴다.

```sql
-- PostgreSQL 12 이하
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE orders (
    id   uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    ...
);
```

JPA에서 PostgreSQL의 `uuid` 타입을 쓸 때는 Hibernate 6 기준으로 이렇게 한다.

```java
@Entity
public class Order {
    @Id
    @UuidGenerator(style = UuidGenerator.Style.RANDOM)
    @Column(columnDefinition = "uuid")
    private UUID id;
}
```

`@UuidGenerator`는 Spring Data JPA 3.0 / Hibernate 6.0부터 사용 가능하다. 이전 버전은 `@GeneratedValue(generator = "uuid2")`와 `@GenericGenerator`를 조합해서 쓴다.

PostgreSQL에서 UUID 컬럼 인덱스를 걸 때 기본 B-Tree는 uuid 타입을 지원한다. 해시 인덱스를 쓰면 동등 비교 쿼리가 더 빠르지만, 범위 조회나 정렬이 필요하면 B-Tree를 유지해야 한다.

```sql
-- 동등 비교만 쓰는 외부 노출 ID 컬럼이라면
CREATE INDEX CONCURRENTLY idx_orders_public_id ON orders USING hash(public_id);
```

## MySQL InnoDB 페이지 분할 문제

UUIDv4가 DB에서 성능 문제를 일으키는 주된 원인은 랜덤성 때문이다.

MySQL InnoDB는 PK를 기준으로 B-Tree 인덱스를 구성하고, 클러스터드 인덱스 구조상 PK 순서로 데이터를 물리적으로 정렬해서 저장한다. AUTO_INCREMENT처럼 단조증가하는 값이면 항상 마지막 페이지에 데이터가 추가되므로 페이지 분할이 거의 없다.

UUIDv4는 완전 랜덤이라 새로운 UUID가 기존 UUID들 사이 어딘가에 끼어들어가야 한다. 그 위치의 페이지가 꽉 차 있으면 페이지 분할이 발생한다. 페이지 분할은 I/O가 늘어나고, 페이지 단편화가 생기고, 읽기 성능도 떨어지는 연쇄 효과로 이어진다.

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
