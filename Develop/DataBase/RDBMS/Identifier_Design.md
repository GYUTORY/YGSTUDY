---
title: 식별자 설계
tags: [database, identifier, uuid, ulid, snowflake, auto-increment, primary-key, surrogate-key, natural-key, mysql, innodb, binary16]
updated: 2026-07-29
---

# 식별자 설계

식별자는 설계 초반에 결정하고 나면 바꾸기가 매우 어렵다. 데이터가 수천만 건 쌓인 뒤에 PK 타입을 바꾸려면 관련된 FK 컬럼까지 전부 수정해야 한다. 처음 어떤 ID 체계를 고르느냐에 따라 단일 서버에서 분산 환경으로 확장할 때의 마이그레이션 비용이 크게 달라진다.

## auto-increment

가장 단순하다. DB가 순차적으로 증가하는 정수를 할당한다. MySQL에서는 `AUTO_INCREMENT`, PostgreSQL에서는 `SERIAL` 또는 `BIGSERIAL`을 쓴다.

```sql
-- MySQL
CREATE TABLE orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    PRIMARY KEY (id)
);

-- PostgreSQL
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY
);
```

단조 증가하므로 InnoDB 클러스터 인덱스에 최적이다. 새 행이 항상 리프 페이지 끝에 추가되어 페이지 분할이 발생하지 않는다. 크기도 8바이트로 작아 인덱스와 FK 컬럼에 유리하다.

단점도 분명하다. 단일 DB에 종속된다. 샤딩 환경에서는 서로 다른 샤드에서 같은 ID가 발급될 수 있다. 순차적이라 외부에 노출하면 총 레코드 수가 추정 가능하다. 오늘 가입한 유저 ID가 1001이면 유저가 1001명 이하라는 걸 알 수 있다.

단일 DB 환경에서 외부에 노출하지 않는 내부 식별자로는 auto-increment BIGINT가 가장 무난하다.

## UUID

### v4: 랜덤

UUID v4는 122비트가 랜덤이다. 충돌 확률이 사실상 없고, DB와 무관하게 애플리케이션에서 직접 생성할 수 있다.

```
f47ac10b-58cc-4372-a567-0e02b2c3d479
```

MySQL에서는 `UUID()` 함수, Java에서는 `UUID.randomUUID()`, Node.js에서는 `crypto.randomUUID()`로 생성한다.

문제는 InnoDB에서 PK로 쓸 때 생긴다. InnoDB는 클러스터 인덱스(PK)를 기준으로 B-Tree에 데이터를 저장한다. UUID v4는 랜덤이라 삽입 위치가 예측 불가능하다. 이미 가득 찬 리프 페이지 중간에 삽입하려면 페이지를 두 개로 분할하고 데이터를 재배치해야 한다. 이것이 페이지 분할이다.

페이지 분할이 자주 일어나면 INSERT 성능이 낮아지고, B-Tree 페이지 사용률도 낮아진다. 분할 후 각 페이지의 절반이 비어 있어 같은 데이터를 저장하는 데 더 많은 페이지가 필요해진다. 데이터가 수만 건 수준이면 체감하기 어렵지만, 일 삽입 건수가 수십만 건을 넘는 테이블에서는 눈에 띄게 느려진다.

### v1: 타임스탬프 + MAC 주소

UUID v1은 앞 60비트에 타임스탬프를 담지만, 구조상 낮은 비트가 앞에 오는 배치라 그대로 쓰면 랜덤성이 남는다. 시간이 증가해도 앞부분이 뒤섞여 단조 증가하지 않는다. MAC 주소가 노출되는 프라이버시 문제까지 있어 신규 설계에서는 거의 쓰지 않는다.

### v7: 타임스탬프 + 랜덤

UUID v7은 2022년 RFC 9562에서 표준화됐다. 앞 48비트에 밀리초 단위 Unix 타임스탬프, 나머지 74비트에 랜덤값을 담는다. 단조 증가하므로 InnoDB 페이지 분할 문제가 없다.

```
01892f61-7340-7f1a-9f5b-9e3dbf4f1a3e
└─ 타임스탬프 ─┘└─ 버전/랜덤 ──────────┘
```

```java
// Java 21+: 표준 라이브러리에 UUID v7 없음, 외부 라이브러리 필요
// com.github.f4b6a3:uuid-creator
UUID uuid = UuidCreator.getTimeOrderedEpoch(); // UUID v7
```

```sql
-- MySQL 8.0+ 저장 예
INSERT INTO orders (id) VALUES (UUID_TO_BIN('01892f61-7340-7f1a-9f5b-9e3dbf4f1a3e'));
```

UUID 체계를 유지해야 하는 상황에서 UUID를 PK로 쓴다면 v4 대신 v7을 선택해야 한다. 전역 유일성과 단조 증가를 모두 갖는다.

## ULID

ULID(Universally Unique Lexicographically Sortable Identifier)는 128비트다. 앞 48비트에 밀리초 단위 타임스탬프, 나머지 80비트에 랜덤값을 Crockford Base32로 인코딩해 26자리 문자열로 표현된다.

```
01ARZ3NDEKTSV4RRFFQ69G5FAV
└──────────┘└──────────────┘
 타임스탬프      랜덤값
```

타임스탬프가 앞에 있어 InnoDB 페이지 분할이 거의 없다. 하이픈이 없고, Crockford Base32 알파벳은 I·L·O·U를 제외해 숫자 1·0과 혼동이 없다. 문자열 사전 순 비교가 생성 시각 순 정렬과 일치해서 Redis·Cassandra 같은 문자열 비교 기반 저장소에서 인덱스 없이 시각 범위 조회가 가능하다.

Monotonic ULID, MySQL/PostgreSQL 저장 방식, Spring/JPA 통합, UUID v7과의 비교는 [ULID](ULID.md)에서 다룬다.

## Snowflake ID

Twitter에서 설계한 분산 ID 생성 체계다. 64비트 정수로 구성된다.

```
비트 위치: 63   62        21       11      0
           ┌──┬────────────────┬─────────┬────────┐
           │0 │  타임스탬프 41b │ 워커ID 10b │ 시퀀스 12b │
           └──┴────────────────┴─────────┴────────┘
```

41비트 타임스탬프는 에포크(기준 시각)부터의 밀리초 차이를 저장한다. 약 69년간 사용 가능하다. 10비트 워커 ID는 데이터센터 ID와 머신 ID 조합으로 최대 1024개 노드를 지원한다. 12비트 시퀀스는 같은 밀리초 안에서의 순번으로, 노드당 밀리초당 최대 4096개 ID를 발급한다.

결과가 64비트 정수(BIGINT)다. auto-increment처럼 쓸 수 있고 단조 증가하므로 InnoDB에 최적이다. DB 없이 ID를 생성할 수 있다는 게 핵심이다.

```java
@Component
public class SnowflakeIdGenerator {
    private final long epoch = 1704067200000L; // 2024-01-01 기준
    private final long workerIdBits = 10L;
    private final long sequenceBits = 12L;

    private final long workerId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & 0xFFF;
            if (sequence == 0) {
                // 같은 밀리초에 4096개 초과 -> 다음 밀리초 대기
                while (timestamp <= lastTimestamp) {
                    timestamp = System.currentTimeMillis();
                }
            }
        } else {
            sequence = 0;
        }

        lastTimestamp = timestamp;
        return ((timestamp - epoch) << (workerIdBits + sequenceBits))
             | (workerId << sequenceBits)
             | sequence;
    }
}
```

Snowflake ID의 단점은 시스템 시계에 의존한다는 점이다. NTP로 인한 시계 역행이 발생하면 같은 ID가 두 번 발급될 수 있다. 이를 막으려면 시계가 역행하면 예외를 던지거나, 마지막 타임스탬프를 넘을 때까지 대기하는 방어 코드가 필요하다.

워커 ID 관리도 운영 부담이다. 새 서버를 띄울 때 유일한 워커 ID를 어떻게 할당하느냐가 문제다. Kubernetes StatefulSet에서는 Pod 이름의 숫자 부분을 파싱해서 워커 ID로 쓰고, Deployment라면 Redis나 ZooKeeper에서 발급받는 방식을 쓴다.

## ID 유형 비교

| 항목 | auto-increment | UUID v4 | UUID v7 | ULID | Snowflake |
|------|---------------|---------|---------|------|-----------|
| 크기 | 8바이트 | 16바이트 | 16바이트 | 16바이트 | 8바이트 |
| 단조 증가 | O | X | O | O | O |
| DB 의존성 | 있음 | 없음 | 없음 | 없음 | 없음 |
| 분산 환경 | X | O | O | O | O |
| InnoDB 적합성 | 최적 | 나쁨 | 좋음 | 좋음 | 최적 |
| 외부 노출 시 순서 추정 | 전체 | 불가 | 시간 단위 | 시간 단위 | 시간+워커 |
| 구현 복잡도 | 낮음 | 낮음 | 낮음 | 낮음 | 높음 |

## Surrogate Key vs Natural Key

### Natural Key

실제 도메인에 존재하는 고유 식별자를 PK로 쓰는 방법이다.

```sql
-- 이메일을 PK로
CREATE TABLE users (
    email VARCHAR(254) PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
```

Natural Key의 핵심 문제는 변경 가능성이다. 이메일 주소는 바뀔 수 있다. 이메일이 PK면 이메일이 바뀔 때 이를 참조하는 모든 FK 컬럼도 UPDATE해야 한다. `ON UPDATE CASCADE`를 걸어두더라도 수백만 건의 FK 업데이트는 부하가 크다.

Natural Key가 복합 키인 경우 FK를 여러 컬럼으로 정의해야 해서 인덱스 크기와 조인 조건이 복잡해진다.

```sql
-- 복합 Natural Key를 FK로 참조하는 예
CREATE TABLE orders (
    user_email VARCHAR(254) NOT NULL,
    -- email 변경 시 여기도 UPDATE 필요
    FOREIGN KEY (user_email) REFERENCES users(email)
);
```

자주 변경되지 않고 외부 시스템과 연동 기준이 되는 값에만 Natural Key를 고려한다. 국가 코드(CHAR(2)), 통화 코드(CHAR(3)) 같은 ISO 표준값은 사실상 변경되지 않으므로 Natural Key도 무방하다.

### Surrogate Key

DB가 생성하는 인위적인 식별자를 PK로 쓰는 방법이다. auto-increment, UUID, Snowflake ID 모두 Surrogate Key다.

```sql
CREATE TABLE users (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE, -- UNIQUE 제약으로 중복 방지
    name VARCHAR(50) NOT NULL
);
```

email은 UNIQUE 제약으로 중복을 막되 PK는 별도 Surrogate Key로 분리한다. 이메일이 바뀌어도 PK는 그대로고, 이를 참조하는 다른 테이블에 영향이 없다.

도메인 의미가 없어 데이터만 보면 연결 관계를 알기 어렵다는 단점이 있지만, 변경 내성이 있고 FK 관리가 단순하다.

### 선택 기준

| 상황 | 선택 |
|------|------|
| 값이 절대 변하지 않고 이미 전역 유일한 경우 (국가코드, 통화코드) | Natural Key |
| 값이 변할 가능성이 있는 경우 (이메일, 전화번호, 사용자명) | Surrogate Key |
| 외부 시스템과 교환하는 기준 키가 필요한 경우 | Natural Key를 UNIQUE, Surrogate Key를 PK |
| 복합 키가 되는 경우 | Surrogate Key |

## MySQL InnoDB UUID PK 페이지 분할

InnoDB에서 데이터는 PK를 기준으로 정렬된 B-Tree(클러스터 인덱스)에 저장된다. 리프 페이지 기본 크기는 16KB다.

UUID v4 PK를 쓰면 새 행의 삽입 위치가 기존 페이지 중간이 된다. 해당 페이지가 가득 찬 상태라면 페이지를 두 개로 분할하고 기존 데이터를 절반씩 재배치한다.

페이지 분할은 두 가지 비용을 만든다. 분할 자체의 I/O 비용이 생기고, 분할 후 각 페이지의 절반이 비어 있어 공간 효율이 떨어진다. 같은 양의 데이터를 저장하는 데 약 두 배의 페이지가 필요해질 수 있다.

### 대응 방법

**UUID v7 또는 ULID로 교체**

가장 깔끔하다. 타임스탬프 선두 ID는 단조 증가하므로 새 행이 항상 리프 페이지 끝에 추가된다. 페이지 분할이 발생하지 않는다.

**BINARY(16) + UUID_TO_BIN 스왑 비트**

UUID를 문자열(CHAR(36))로 저장하면 36바이트, BINARY(16)으로 저장하면 16바이트다. MySQL 8.0에서 `UUID_TO_BIN(uuid, 1)` 형태로 두 번째 인자에 1을 넘기면 UUID v1의 타임스탬프 비트를 재정렬해서 단조 증가 특성을 갖게 만든다. UUID v4에는 효과가 없으므로, v4를 계속 쓴다면 이 옵션은 공간 절약 효과만 있다.

```sql
-- UUID v1의 타임스탬프 비트 스왑 적용 (UUID v4에는 효과 없음)
CREATE TABLE sessions (
    id BINARY(16) NOT NULL DEFAULT (UUID_TO_BIN(UUID(), 1)),
    PRIMARY KEY (id)
);
```

**innodb_fill_factor 조정**

이미 UUID v4를 PK로 쓰고 있고 마이그레이션이 어려운 상황에서 단기 완화책으로 쓴다. 페이지를 미리 덜 채워두면 분할 빈도가 낮아지지만 공간 효율이 희생된다.

```sql
SET GLOBAL innodb_fill_factor = 80; -- 기본값 100
```

## BINARY(16) 저장 방식

UUID를 문자열 CHAR(36)으로 저장하면 36바이트, BINARY(16)으로 저장하면 16바이트다. 크기가 절반 이하로 줄고 인덱스 크기도 함께 줄어 버퍼 풀 캐시 효율이 높아진다.

```sql
CREATE TABLE sessions (
    id BINARY(16) NOT NULL,
    user_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id)
);

-- 삽입
INSERT INTO sessions (id, user_id)
VALUES (UUID_TO_BIN('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 42);

-- 조회 시 문자열로 변환
SELECT BIN_TO_UUID(id) AS session_id, user_id
FROM sessions
WHERE user_id = 42;

-- WHERE 조건에서도 변환 필요
SELECT * FROM sessions
WHERE id = UUID_TO_BIN('f47ac10b-58cc-4372-a567-0e02b2c3d479');
```

애플리케이션에서 변환하는 방법도 있다.

```java
public static byte[] uuidToBytes(UUID uuid) {
    ByteBuffer bb = ByteBuffer.wrap(new byte[16]);
    bb.putLong(uuid.getMostSignificantBits());
    bb.putLong(uuid.getLeastSignificantBits());
    return bb.array();
}

public static UUID bytesToUuid(byte[] bytes) {
    ByteBuffer bb = ByteBuffer.wrap(bytes);
    long high = bb.getLong();
    long low = bb.getLong();
    return new UUID(high, low);
}
```

JPA에서 BINARY(16) UUID를 매핑할 때는 Hibernate 6부터 제공하는 어노테이션으로 처리한다.

```java
@Entity
public class Session {
    @Id
    @JdbcTypeCode(SqlTypes.BINARY)
    @GeneratedValue(generator = "uuid")
    private UUID id;
}
```

주의할 점은 MySQL Workbench나 DBeaver 같은 GUI 툴에서 BINARY(16) 컬럼을 조회하면 바이너리 그대로 보인다는 것이다. 디버깅할 때 `BIN_TO_UUID(id)`를 SELECT에 포함해야 읽을 수 있다.

## 분산 환경 ID 생성

분산 환경에서 ID 생성의 핵심 요구사항은 세 가지다. 전역 유일성, DB 없이 생성 가능, 단조 증가(InnoDB 적합성).

### DB 시퀀스 배치 발급

별도 시퀀스 테이블을 두고 여러 서비스 인스턴스가 ID를 배치로 가져가는 방식이다.

```sql
CREATE TABLE id_sequences (
    name VARCHAR(50) PRIMARY KEY,
    current_value BIGINT NOT NULL DEFAULT 0,
    step INT NOT NULL DEFAULT 1000
);

-- 각 인스턴스가 1000개씩 예약
UPDATE id_sequences
SET current_value = current_value + step
WHERE name = 'orders';

SELECT current_value FROM id_sequences WHERE name = 'orders';
```

인스턴스는 `(current_value - step + 1)` 부터 `current_value`까지의 ID를 메모리에 캐싱하고 소진되면 다시 DB에서 가져간다. DB 의존성이 있지만 단순하고 BIGINT를 그대로 쓸 수 있다.

인스턴스가 죽으면 캐싱한 ID 범위가 낭비되어 ID에 구멍이 생기는데, PK는 연속일 필요가 없으므로 실제 문제는 아니다.

### Snowflake: 워커 ID 관리

워커 ID 할당이 핵심이다. 같은 워커 ID를 두 인스턴스가 쓰면 충돌한다.

Kubernetes StatefulSet이라면 Pod 이름의 숫자를 파싱한다.

```java
@Value("${HOSTNAME:unknown}")
private String hostname; // order-service-0, order-service-1, ...

private long extractWorkerId(String hostname) {
    String[] parts = hostname.split("-");
    return Long.parseLong(parts[parts.length - 1]);
}
```

Deployment(랜덤 Pod 이름)라면 Redis에서 발급받는다.

```lua
-- Redis Lua 스크립트 (원자적)
local key = "worker_id_pool"
local id = redis.call("SPOP", key)
if id then
    return id
else
    error("worker id pool exhausted")
end
```

시작 시 Redis에서 ID를 받아 메모리에 저장하고, 종료 시 `SADD`로 반납한다.

### UUID v7 / ULID

워커 ID 관리 없이 분산 ID를 생성하는 방법이다. 랜덤 비트가 충분히 커서 충돌 가능성이 사실상 없고, 타임스탬프 선두라 단조 증가한다. 구현이 단순하다.

다만 16바이트라 BIGINT(8바이트)보다 2배 크다. 수억 건 테이블에서 인덱스 크기 차이가 누적된다. 스토리지 비용보다 구현 단순성을 우선하는 상황에 적합하다.

## API에서 내부 ID 노출 여부

내부 DB PK를 API 응답에 그대로 노출하면 여러 문제가 생긴다.

총 레코드 수 추정이 가능하다. `GET /orders/10043`이면 주문이 약 1만 건임을 알 수 있다. 순차 스캔도 쉬워진다. `id=1`부터 하나씩 올리며 다른 사용자 데이터에 접근 시도를 자동화하기 쉽다. 이것이 IDOR(Insecure Direct Object Reference) 취약점이다. 경쟁사에 비즈니스 정보가 노출되는 문제도 있다. 특정 시간대의 주문 ID 증가 폭으로 주문량을 역산할 수 있다.

해결 방법은 내부 ID는 내부 연산에만 쓰고, 외부 노출 ID를 별도로 관리하는 것이다.

```sql
CREATE TABLE orders (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, -- 내부 ID
    external_id CHAR(26) NOT NULL,                -- 외부 노출용 ULID
    user_id BIGINT NOT NULL,
    UNIQUE INDEX idx_external_id (external_id)
);
```

```java
@PostMapping("/orders")
public OrderResponse createOrder(@RequestBody OrderRequest req) {
    Order order = orderService.create(req);
    return OrderResponse.builder()
        .id(order.getExternalId()) // ULID 노출
        // .id(order.getId()) -- 내부 PK 노출 금지
        .build();
}
```

external_id로 ULID나 UUID v4를 쓰면 순차 스캔이 불가능하고 총 건수도 알 수 없다.

HashIds 같은 라이브러리로 숫자 ID를 가역적으로 인코딩하는 방법도 있다.

```javascript
import Hashids from 'hashids';
const hashids = new Hashids('my-secret-salt', 8);

hashids.encode(1234);   // 'NkK9'
hashids.decode('NkK9'); // [1234]
```

HashIds는 암호학적으로 안전하지 않다. salt가 유출되면 역산 가능하다. 레코드 수 추정 방지 목적으로는 충분하지만, 보안이 중요한 리소스에는 쓰지 않는다.

**노출해도 되는 경우:**

내부 관리 도구나 B2B API처럼 파트너가 DB 규모를 알아도 무관한 경우, 또는 external_id 관리가 오히려 과도한 복잡도를 만드는 경우에는 내부 ID를 노출해도 된다. 결제나 사용자 개인정보 같은 민감한 도메인은 항상 분리한다.
