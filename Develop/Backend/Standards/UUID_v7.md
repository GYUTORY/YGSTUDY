---
title: UUIDv7 — 타임스탬프 기반 UUID로 전환하는 이유와 방법
tags: [uuid, UUIDv7, RFC9562, backend, database, innodb]
updated: 2026-08-02
---

# UUIDv7 — 타임스탬프 기반 UUID로 전환하는 이유와 방법

UUIDv4를 PK로 쓰다가 테이블에 데이터가 수천만 건 쌓이면 슬로우 쿼리가 나타나기 시작한다. EXPLAIN으로 보면 인덱스를 타는데도 느리고, SHOW ENGINE INNODB STATUS에서 page split이 자꾸 찍힌다. 그 시점에 UUIDv7 전환을 진지하게 검토하게 된다.

## RFC 9562 128-bit 구조

UUIDv7은 2024년 5월 RFC 9562로 표준화됐다. RFC 4122를 대체하는 문서다.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           unix_ts_ms                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          unix_ts_ms           |  ver  |       rand_a          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|var|                        rand_b                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            rand_b                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

필드를 순서대로 보면:

- **unix_ts_ms** (48비트): Unix epoch 기준 밀리초 타임스탬프. 현재 시각 기준으로 10889년까지 표현된다.
- **ver** (4비트): 버전 필드. 항상 `0111` (=7).
- **rand_a** (12비트): 랜덤 또는 단조성 보장용 카운터.
- **var** (2비트): variant 필드. RFC 9562 규격은 `10`.
- **rand_b** (62비트): 완전 랜덤.

총 128비트 중 타임스탬프 48비트, 고정 6비트(ver+var), 랜덤 74비트다. 랜덤 엔트로피는 UUIDv4(122비트)보다 작지만, 동일 밀리초 안에서 충돌을 걱정해야 하는 상황은 단조성 카운터로 해결한다.

텍스트 표현은 UUIDv4와 동일한 포맷이다.

```
018f4b3c-9f1a-7d3e-8b2a-4c5e6f7a8b9c
         ↑    ↑
         ts   ver=7
```

세 번째 블록 첫 자리가 `7`이면 UUIDv7이다.

## UUIDv4, ULID, UUIDv7 비교

세 가지가 자주 비교된다. 선택 기준은 보통 "기존 UUID 컬럼과 호환이 필요한가"와 "정렬 가능한 ID가 필요한가" 두 가지다.

| 항목 | UUIDv4 | UUIDv7 | ULID |
|---|---|---|---|
| 정렬 가능 | X | O | O |
| UUID 포맷 | O | O | X |
| 길이 | 36자 | 36자 | 26자 |
| 타임스탬프 | 없음 | 48-bit ms | 48-bit ms |
| 랜덤 엔트로피 | 122비트 | 74비트 | 80비트 |
| 표준 | RFC 4122 | RFC 9562 | 비공식 |

ULID는 UUID 포맷이 아니라 기존 `CHAR(36)` 컬럼과 호환이 안 된다. UUID 타입을 사용하는 PostgreSQL, 또는 UUID를 검증하는 API 게이트웨이나 클라이언트 SDK가 있다면 UUIDv7이 낫다. 반대로 UUID 포맷에 의존하는 곳이 없고 짧은 문자열이 필요하다면 ULID도 선택지다.

인덱스 정렬 성능 면에서는 UUIDv7과 ULID가 비슷하다. 둘 다 앞 48비트가 밀리초 타임스탬프라 단조증가하는 특성이 같다.

## InnoDB 페이지 분할 억제

InnoDB 클러스터드 인덱스는 PK 순서로 레코드를 물리적으로 배치한다. AUTO_INCREMENT는 항상 마지막 페이지에 데이터가 쌓이므로 페이지 분할이 거의 없다. UUIDv4는 완전 랜덤이라 새 레코드가 기존 레코드들 사이 어딘가에 끼어든다.

페이지가 꽉 찬 상태에서 중간에 삽입이 생기면 InnoDB는 페이지를 절반으로 쪼개고, 인접한 페이지들의 포인터를 재조정한다. 이 작업이 INSERT마다 반복되면 단편화가 심해지고 버퍼 풀 효율이 떨어진다.

UUIDv7은 밀리초 타임스탬프가 앞에 있어서 시간이 지날수록 새 레코드가 항상 기존 레코드보다 뒤에 온다. AUTO_INCREMENT와 같은 추가 패턴이다.

실제로 어느 정도 차이인지 수치로 보면, 10만 건 기준 벤치마크에서 UUIDv4 대비 UUIDv7의 INSERT 처리량이 2~3배 높게 나오는 경우가 일반적이다. 데이터가 많을수록 차이가 커진다. `INFORMATION_SCHEMA.INNODB_METRICS`에서 `index_page_splits` 카운터를 모니터링하면 실제 운영 환경에서 페이지 분할 빈도를 확인할 수 있다.

```sql
SELECT NAME, COUNT
FROM INFORMATION_SCHEMA.INNODB_METRICS
WHERE NAME = 'index_page_splits';
```

## MySQL BINARY(16) 저장

UUID를 MySQL에 저장할 때 CHAR(36)보다 BINARY(16)이 공간과 인덱스 성능 면에서 유리하다. CHAR(36)은 UTF8MB4 기준 실제 36~144바이트를 쓰고, BINARY(16)은 정확히 16바이트다.

MySQL 8.0부터 `UUID_TO_BIN()` 함수가 두 번째 인자로 swap_flag를 받는다. `UUID_TO_BIN(uuid, 1)`을 쓰면 타임스탬프 바이트를 앞으로 재배치해서 시간 순 정렬을 맞춰준다. UUIDv7은 이미 타임스탬프가 앞에 있으므로 swap_flag 없이 쓰면 된다.

```sql
CREATE TABLE orders (
    id      BINARY(16) NOT NULL DEFAULT (UUID_TO_BIN(UUID(), 1)),
    -- UUIDv7 사용 시: id BINARY(16) NOT NULL
    PRIMARY KEY (id)
);

-- UUIDv7 삽입 (애플리케이션에서 생성한 값)
INSERT INTO orders (id, user_id, amount)
VALUES (UUID_TO_BIN('018f4b3c-9f1a-7d3e-8b2a-4c5e6f7a8b9c'), 1001, 50000);

-- 조회
SELECT BIN_TO_UUID(id) AS id, user_id, amount
FROM orders
WHERE id = UUID_TO_BIN('018f4b3c-9f1a-7d3e-8b2a-4c5e6f7a8b9c');
```

BINARY(16) 컬럼에 인덱스를 걸면 CHAR(36)보다 인덱스 크기가 작아서 버퍼 풀에 더 많은 인덱스 페이지가 올라간다. 랜덤 읽기가 많은 워크로드에서 효과가 크다.

## PostgreSQL에서 사용

PostgreSQL 13까지는 `gen_random_uuid()`가 UUIDv4를 반환한다. PostgreSQL에는 아직 UUIDv7 네이티브 함수가 없어서 확장 모듈이나 애플리케이션에서 생성해야 한다.

`pg_uuidv7` 확장을 쓰면 DB 수준에서 생성할 수 있다.

```sql
-- pg_uuidv7 확장 설치 후
CREATE EXTENSION IF NOT EXISTS pg_uuidv7;

CREATE TABLE orders (
    id      UUID NOT NULL DEFAULT uuid_generate_v7(),
    user_id BIGINT NOT NULL,
    PRIMARY KEY (id)
);
```

PostgreSQL의 UUID 타입은 16바이트 바이너리로 내부 저장하고, 텍스트 변환은 필요할 때만 한다. MySQL처럼 BINARY(16)으로 별도 처리할 필요 없이 그냥 `UUID` 컬럼 타입을 쓰면 된다.

`gen_random_uuid()`를 UUIDv7로 교체하는 경우, 기존 UUIDv4 데이터와 혼재하더라도 컬럼 타입은 동일하게 유지된다. 다만 정렬 시 기존 UUIDv4 레코드는 타임스탬프 기반 정렬이 되지 않으므로 마이그레이션 시점 이전 데이터는 별도 처리가 필요하다.

## 언어별 생성 코드

### Java — java-uuid-generator

Java 표준 라이브러리 `java.util.UUID`는 UUIDv7을 지원하지 않는다. `com.fasterxml.uuid:java-uuid-generator` 라이브러리를 쓴다.

```xml
<dependency>
    <groupId>com.fasterxml.uuid</groupId>
    <artifactId>java-uuid-generator</artifactId>
    <version>5.1.0</version>
</dependency>
```

```java
import com.fasterxml.uuid.Generators;
import com.fasterxml.uuid.impl.TimeBasedEpochGenerator;
import java.util.UUID;

public class UuidUtil {
    // 싱글턴으로 쓴다. 내부에 단조성 카운터를 유지한다.
    private static final TimeBasedEpochGenerator GENERATOR =
        Generators.timeBasedEpochGenerator();

    public static UUID generateV7() {
        return GENERATOR.generate();
    }
}
```

`TimeBasedEpochGenerator`는 스레드 안전하다. 애플리케이션 전역에서 인스턴스 하나를 공유해서 써도 된다. 인스턴스를 여러 개 만들면 각 인스턴스가 독립적인 카운터를 가져서 단조성이 인스턴스 범위 안에서만 보장된다.

### Node.js

Node.js 21부터 `crypto.randomUUID()`가 UUIDv4만 반환한다. UUIDv7은 `uuidv7` 패키지를 쓴다.

```typescript
import { uuidv7 } from 'uuidv7';

const id = uuidv7();
// '018f4b3c-9f1a-7000-8b2a-4c5e6f7a8b9c'
```

또는 `uuid` 패키지 5.0부터 v7을 지원한다.

```typescript
import { v7 as uuidv7 } from 'uuid';

const id = uuidv7();
```

두 패키지 모두 동일 밀리초 안에서 시퀀스를 증가시켜 단조성을 보장한다. 분산 환경에서 여러 서버 인스턴스가 독립적으로 생성하는 경우 단조성은 인스턴스 단위로만 보장된다.

### Go

Go 표준 라이브러리에는 UUID가 없다. `github.com/google/uuid` 패키지가 사실상 표준이다. v1.6.0부터 UUIDv7을 지원한다.

```go
import "github.com/google/uuid"

func main() {
    id, err := uuid.NewV7()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(id.String())
    // 018f4b3c-9f1a-7d3e-8b2a-4c5e6f7a8b9c
}
```

`uuid.NewV7()`은 내부적으로 단조성 카운터를 쓴다. 같은 고루틴에서 연속 호출하면 밀리초가 같아도 카운터가 증가해서 정렬이 유지된다.

## JPA @GeneratedValue 커스텀 전략

Hibernate 6.x부터 UUIDv7을 지원하는 `UuidGenerator`를 쓸 수 있다. 그 전 버전이나 세밀한 제어가 필요하면 `IdentifierGenerator`를 직접 구현한다.

```java
import com.fasterxml.uuid.Generators;
import com.fasterxml.uuid.impl.TimeBasedEpochGenerator;
import org.hibernate.engine.spi.SharedSessionContractImplementor;
import org.hibernate.id.IdentifierGenerator;

public class UuidV7Generator implements IdentifierGenerator {

    private static final TimeBasedEpochGenerator GENERATOR =
        Generators.timeBasedEpochGenerator();

    @Override
    public Object generate(SharedSessionContractImplementor session, Object object) {
        return GENERATOR.generate();
    }
}
```

엔티티에 적용:

```java
import org.hibernate.annotations.GenericGenerator;
import java.util.UUID;

@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(generator = "uuid-v7")
    @GenericGenerator(name = "uuid-v7", type = UuidV7Generator.class)
    @Column(columnDefinition = "BINARY(16)")
    private UUID id;

    // ...
}
```

Hibernate 6.2 이상이면 `@UuidGenerator`에 `style = UuidGenerator.Style.TIME`을 줘서 UUIDv7을 쓸 수 있다. 단, 이때 내부 구현이 java-uuid-generator와 다를 수 있어서 단조성 동작을 확인해야 한다.

```java
import org.hibernate.annotations.UuidGenerator;

@Entity
public class Order {

    @Id
    @GeneratedValue
    @UuidGenerator(style = UuidGenerator.Style.TIME)
    private UUID id;
}
```

`UuidGenerator.Style.TIME`은 UUIDv7 RFC 9562 구현이 아닐 수 있다. 라이브러리 버전마다 다르므로 생성된 UUID를 직접 확인해서 세 번째 블록이 `7`로 시작하는지 체크한다.

## 동일 밀리초 내 단조성 보장

UUIDv7의 rand_a 필드 12비트를 단조성 카운터로 쓰는 방식이 RFC 9562 Method 2로 권장된다.

동작 방식은 이렇다. 같은 밀리초에 UUID를 연속으로 생성하면 타임스탬프 48비트는 동일하다. 이때 rand_a 12비트를 카운터로 써서 1씩 증가시킨다. 카운터가 4095(0xFFF)에 도달하면 다음 밀리초로 타임스탬프를 앞당기거나, 오버플로 처리를 한다.

```
동일 ms 내 연속 생성:
018f4b3c-9f1a-7000-8b2a-4c5e6f7a8b9c  (카운터: 0)
018f4b3c-9f1a-7001-8b2a-4c5e6f7a8b9d  (카운터: 1)
018f4b3c-9f1a-7002-8b2a-4c5e6f7a8b9e  (카운터: 2)
```

이 방식으로 동일 밀리초에 최대 4096개의 UUID가 정렬 순서를 유지한다. 초당 4,096,000개 이상을 단일 노드에서 생성하는 경우가 아니면 카운터 오버플로는 실제로 거의 발생하지 않는다.

주의할 점은 단조성이 단일 프로세스(또는 단일 `TimeBasedEpochGenerator` 인스턴스) 안에서만 보장된다는 것이다. 서버 두 대에서 동시에 생성하면 동일 ms 내 UUID 간 정렬 순서가 보장되지 않는다. 그래도 타임스탬프 기반이라 UUIDv4보다 훨씬 정렬 친화적이고, DB INSERT 패턴도 단조증가에 가까워서 InnoDB 페이지 분할은 억제된다.

## 분산 노드 충돌 확률

UUIDv7의 랜덤 부분은 rand_a 12비트 + rand_b 62비트 = 74비트다. 단조성 카운터를 rand_a에 쓰는 경우 실질 랜덤 엔트로피는 rand_b 62비트가 된다.

동일 밀리초에 n개의 노드가 각각 UUID를 생성할 때 충돌 확률 근사:

```
P ≈ n² / (2 × 2^62)
```

노드 100개가 동시에 생성한다고 가정하면:

```
P ≈ 100² / (2 × 4.6 × 10^18) ≈ 1.08 × 10^-15
```

10^-15 수준이면 현실적으로 무시 가능한 수준이다. UUIDv4의 122비트 랜덤과 비교하면 엔트로피가 48비트 줄었지만, 동일 밀리초에 수천 개 노드가 동시 생성하는 극단적 상황이 아니면 충돌 위험은 없다.

노드 간 충돌을 더 확실히 막으려면 rand_b 앞부분에 노드 식별자(MAC 주소 하위 바이트나 pod ID 해시 등)를 박는 방식도 있다. RFC 9562에서 Method 3으로 언급한다. 다만 이 경우 rand_b 일부를 고정값으로 쓰므로 랜덤 엔트로피가 더 줄어든다.

## UUIDv4에서 UUIDv7으로 전환 시 주의사항

**기존 데이터와 혼재 문제**

컬럼 타입은 동일하게 유지되지만, 마이그레이션 기준 시점 이전 데이터는 UUIDv4(랜덤)고 이후 데이터는 UUIDv7(타임스탬프 기반)이다. 타임스탬프로 정렬하거나 최신 레코드를 효율적으로 조회하는 쿼리는 마이그레이션 이전 데이터에서는 기대한 동작을 하지 않는다.

**DB 기본값 교체**

MySQL에서 `DEFAULT (UUID())`를 쓰던 컬럼은 애플리케이션에서 UUIDv7을 생성해서 삽입하는 방식으로 바꿔야 한다. MySQL 내장 `UUID()` 함수는 UUIDv1을 반환한다. DB 수준 기본값을 유지하고 싶다면 저장 프로시저나 트리거로 UUIDv7 생성 로직을 구현해야 하는데, 관리 부담이 커서 보통 애플리케이션에서 생성하는 쪽을 택한다.

**외부 시스템과 호환**

UUID를 외부 API로 주고받는다면 UUIDv7도 동일한 포맷이라 파싱 문제는 없다. 단, 상대 시스템이 UUID 버전을 검증하는 경우(ver 필드가 4인지 체크) 문제가 생긴다. 실제로 이런 검증을 하는 경우는 드물지만, 연동 시스템 코드를 확인해두는 게 안전하다.
