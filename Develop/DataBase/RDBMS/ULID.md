---
title: ULID
tags: [database, ulid, uuid, primary-key, identifier, mysql, postgresql, spring, jpa, redis, cassandra, distributed-id, monotonic, crockford-base32]
updated: 2026-07-29
---

# ULID

ULID(Universally Unique Lexicographically Sortable Identifier)는 128비트 식별자다. UUID와 같은 크기지만 앞 48비트에 밀리초 단위 타임스탬프가 들어가서 생성 시각 순 정렬이 된다. 출력 형식은 26자리 대문자 문자열이다.

UUID v4를 PK로 쓰다가 InnoDB 페이지 분할로 INSERT 성능이 무너지는 걸 경험하면 보통 ULID나 UUID v7로 넘어간다. 타임스탬프가 앞에 있어 새 행이 B+트리 인덱스의 끝 쪽에 삽입되므로 페이지 분할 빈도가 크게 줄어든다.

## 128비트 구조

```
 비트 위치: 127               79              0
           ┌────────────────────┬─────────────────────────────┐
           │   48비트 타임스탬프  │          80비트 랜덤           │
           └────────────────────┴─────────────────────────────┘
```

상위 48비트에 Unix 에포크 기준 밀리초 타임스탬프를 저장한다. 2^48밀리초는 약 8925년이라 서기 10895년까지 표현 가능하다.

하위 80비트는 암호학적으로 안전한 랜덤 값이다. 같은 밀리초에 생성된 두 ULID의 랜덤 파트가 충돌할 확률은 2^80분의 1로, 실제 운영에서 무시할 수 있는 수준이다.

26자리 문자열로 표현할 때는 Crockford Base32로 인코딩한다.

```
01HX2Y3Z4A5B6C7D8E9F0G1H2J
└─────────┘└────────────────┘
 10자리 타임스탬프   16자리 랜덤
```

문자열 그대로 사전 순 비교하면 생성 시각 순 정렬이 된다.

## Crockford Base32 인코딩

표준 Base64나 RFC 4648 Base32가 아닌 Crockford Base32를 쓴다. 사람이 읽을 때 혼동하기 쉬운 문자를 제외한 32자리 알파벳이다.

```
값:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
문자: 0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F

값: 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
문자: G  H  J  K  M  N  P  Q  R  S  T  V  W  X  Y  Z
```

I, L, O, U가 빠져 있다. I와 L은 숫자 1과 혼동되고, O는 숫자 0과 혼동된다. U는 영어 욕설 필터 우회 이슈로 제외됐다. 소문자도 수용하지만 출력은 항상 대문자다.

128비트를 5비트씩 분할하면 26자리가 된다(128 ÷ 5 = 25.6이라 첫 자리에는 3비트만 들어간다). 첫 자리가 가질 수 있는 최대값은 7(0b111)이라 ULID는 항상 `0`으로 시작하거나 최대 `7`로 시작한다.

## 언어별 생성 코드

### Node.js

```javascript
import { ulid, monotonicFactory } from 'ulid';

// 기본 ULID 생성
const id = ulid();
// '01HX2Y3Z4A5B6C7D8E9F0G1H2J'

// 특정 타임스탬프 기준 생성
const id = ulid(Date.now());

// Monotonic ULID - 같은 밀리초 내 순서 보장
const monotonicUlid = monotonicFactory();
const id1 = monotonicUlid();
const id2 = monotonicUlid(); // id1 < id2 보장
```

브라우저에서는 `Math.random()` 폴백이 동작한다. 서버 사이드에서는 `crypto.getRandomValues()`를 사용하므로 암호학적으로 안전하다.

### TypeScript (추가 예시)

```typescript
// npm install ulid
import { ulid, monotonicFactory, decodeTime } from 'ulid';

// 기본 생성
const id = ulid(); // '01HX2Y3Z4A5B6C7D8E9F0G1H2J'

// Monotonic ULID — UUID로 변환 (저장 시)
const ulidStr = ulid();
// ULID 문자열에서 타임스탬프 추출
const epochMs = decodeTime(ulidStr);

// TypeScript에서 UUID 형식으로 변환이 필요하면 별도 변환 로직 사용
function ulidToUuidHex(ulidStr: string): string {
    // ULID Base32 → hex 128비트 → UUID 형식으로 변환
    const base32Chars = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    let n = BigInt(0);
    for (const c of ulidStr.toUpperCase()) {
        n = n * 32n + BigInt(base32Chars.indexOf(c));
    }
    const hex = n.toString(16).padStart(32, '0');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
```

### Python

```python
# pip install python-ulid
from ulid import ULID

u = ULID()
str(u)          # '01HX2Y3Z4A5B6C7D8E9F0G1H2J'
u.timestamp()   # Unix timestamp (float)
u.datetime      # datetime 객체 (UTC)

# 특정 시각 기준 생성
from datetime import datetime, timezone
u = ULID.from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc))
```

### Go

```go
// go get github.com/oklog/ulid/v2
import (
    "crypto/rand"
    "time"
    "github.com/oklog/ulid/v2"
)

// Monotonic entropy: 같은 밀리초 내 단조 증가 보장
entropy := ulid.Monotonic(rand.Reader, 0)
id := ulid.MustNew(ulid.Timestamp(time.Now()), entropy)
fmt.Println(id.String()) // '01HX2Y3Z4A5B6C7D8E9F0G1H2J'
```

Go에서 Monotonic entropy 인스턴스는 고루틴 간 공유하면 내부 뮤텍스로 직렬화된다. 처리량이 높은 경우 고루틴마다 별도 인스턴스를 써서 경합을 피할 수 있다. 단, 그러면 같은 밀리초에 고루틴 간 순서 보장은 없다.

## Monotonic ULID와 같은 밀리초 내 엣지케이스

표준 ULID는 같은 밀리초에 여러 개를 생성해도 랜덤 파트가 독립적으로 생성된다. 같은 밀리초에 만들어진 두 ULID의 사전 순서가 생성 순서와 다를 수 있다.

```
01HX2Y3Z4A5B - FFFABC... (첫 번째 생성)
01HX2Y3Z4A5B - 008XY0... (같은 밀리초, 두 번째 생성)
```

두 번째 ULID가 사전순으로 앞선다. 이벤트 로그나 타임라인처럼 삽입 순서와 정렬 순서가 일치해야 하는 경우에 문제가 된다.

Monotonic ULID는 이 문제를 해결한다. 같은 밀리초의 첫 번째 ULID에서 랜덤 80비트를 생성한 뒤, 이후 같은 밀리초에 생성하는 ULID는 직전 값의 랜덤 파트에 1을 더한다.

```
01HX2Y3Z4A5B - 00ABCD0001 (첫 번째)
01HX2Y3Z4A5B - 00ABCD0002 (두 번째, +1)
01HX2Y3Z4A5B - 00ABCD0003 (세 번째, +1)
```

엣지케이스가 있다. 같은 밀리초에 랜덤 파트가 최대값(2^80 - 1)에 닿으면 다음 증분에서 오버플로우가 난다. oklog/ulid는 이 상황에서 에러를 반환한다. ulid-creator는 밀리초를 강제로 1 올려서 오버플로우를 피한다.

초당 수십만 건을 단일 프로세스-단일 스레드에서 생성하지 않는 이상 실제로 발생하기 어렵다. 같은 1밀리초에 2^80개(약 1.2 × 10^24개)를 생성해야 오버플로우가 난다.

## MySQL 저장 방식: CHAR(26) vs BINARY(16)

### CHAR(26)

Crockford Base32 문자열을 그대로 저장한다.

```sql
CREATE TABLE events (
    id         CHAR(26)     NOT NULL,
    payload    JSON         NOT NULL,
    created_at DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id)
);

-- 삽입
INSERT INTO events (id, payload) VALUES ('01HX2Y3Z4A5B6C7D8E9F0G1H2J', '{}');

-- 조회
SELECT * FROM events WHERE id = '01HX2Y3Z4A5B6C7D8E9F0G1H2J';
```

문자열 그대로라 MySQL Workbench, DBeaver에서 바로 읽힌다. 변환 없이 저장하고 꺼내므로 애플리케이션 코드가 단순하다. 단점은 26바이트라 BINARY(16)보다 크다.

### BINARY(16)

128비트를 바이너리로 그대로 저장한다.

```sql
CREATE TABLE events (
    id         BINARY(16)   NOT NULL,
    payload    JSON         NOT NULL,
    created_at DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id)
);
```

```typescript
// 저장: ULID → Buffer(16바이트)
import { ulid } from 'ulid';

function ulidToBuffer(ulidStr: string): Buffer {
    const base32Chars = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    let n = BigInt(0);
    for (const c of ulidStr.toUpperCase()) {
        n = n * 32n + BigInt(base32Chars.indexOf(c));
    }
    const hex = n.toString(16).padStart(32, '0');
    return Buffer.from(hex, 'hex');
}

// 조회: Buffer(16바이트) → ULID 문자열
function bufferToUlid(buf: Buffer): string {
    const base32Chars = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    let n = BigInt('0x' + buf.toString('hex'));
    let result = '';
    for (let i = 0; i < 26; i++) {
        result = base32Chars[Number(n & 31n)] + result;
        n >>= 5n;
    }
    return result;
}
```

16바이트라 PK 인덱스 크기가 CHAR(26)의 약 60%다. 데이터가 수천만 건을 넘어 인덱스가 버퍼 풀을 넘기 시작하면 이 차이가 체감된다. 조회 시 16진수 변환이 필요해서 직접 SQL로 확인하기 불편하다.

```sql
-- BINARY(16) 컬럼 직접 확인할 때
SELECT HEX(id), created_at FROM events LIMIT 10;
```

팀에서 SQL로 직접 데이터를 확인하는 빈도가 높다면 CHAR(26)이 낫다. 스토리지 효율이 중요하고 수백만 건 이상의 테이블이라면 BINARY(16)이 낫다.

InnoDB는 PK 기준 클러스터드 인덱스로 데이터를 저장한다. ULID를 PK로 쓰면 타임스탬프 선두라 새 행이 인덱스 끝 근처에 삽입된다. UUID v4의 완전 랜덤 삽입보다 페이지 분할이 훨씬 적게 발생한다.

## PostgreSQL 저장 패턴

PostgreSQL에는 UUID 타입이 있다. ULID는 128비트라 UUID와 바이트 수가 같으므로 UUID 타입에 저장할 수 있다.

### UUID 타입으로 저장

```sql
CREATE TABLE events (
    id      UUID        NOT NULL,
    payload JSONB       NOT NULL,
    PRIMARY KEY (id)
);
```

```typescript
// TypeScript에서 ULID를 UUID 형식으로 변환 후 저장
const ulidStr = ulid();
const uuidStr = ulidToUuidHex(ulidStr);
// UUID 형식: 018f7a23-4c9b-7000-8f0a-b2c3d4e5f6a7
```

UUID 타입은 내부적으로 16바이트를 저장하므로 TEXT(가변)나 BYTEA보다 효율적이다. ULID의 타임스탬프 비트가 UUID의 상위 비트에 위치하므로 UUID 기준 정렬이 시각 순 정렬과 일치한다.

```sql
-- 생성 시각 순 정렬 (ULID를 UUID로 저장한 경우)
SELECT * FROM events ORDER BY id ASC;
-- 타임스탬프 앞에 있어 사전 순 = 시각 순
```

### TEXT로 저장

ULID 문자열을 그대로 저장한다. 가장 단순하고 직관적이다.

```sql
CREATE TABLE events (
    id      TEXT  NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id)
);
```

TEXT 타입은 가변 길이라 26자리 고정 문자열에는 CHAR(26)이 낫지만, PostgreSQL에서 CHAR는 공백 패딩 처리가 있어 TEXT나 VARCHAR(26)을 더 많이 쓴다.

### BYTEA로 저장

```sql
CREATE TABLE events (
    id      BYTEA NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id)
);
```

16바이트 저장이라 효율은 좋지만, SQL로 직접 확인할 때 16진수 변환이 필요하다. PostgreSQL에서는 UUID 타입이 있어 BYTEA를 쓸 이유가 없는 경우가 많다.

실무에서는 PostgreSQL + ULID 조합이면 UUID 타입에 저장하는 패턴이 가장 무난하다.

## TypeORM 통합

### CHAR(26) 저장 방식

```typescript
import { ulid, monotonicFactory } from 'ulid';
import { Entity, PrimaryColumn, Column, BeforeInsert } from 'typeorm';

const monotonicUlid = monotonicFactory();

@Entity('events')
export class Event {
    @PrimaryColumn({ type: 'char', length: 26 })
    id: string;

    @Column({ nullable: false })
    payload: string;

    @BeforeInsert()
    generateId(): void {
        if (!this.id) {
            this.id = monotonicUlid();
        }
    }
}
```

`@PrimaryGeneratedColumn`을 쓰지 않고 `@BeforeInsert()`에서 직접 할당한다. INSERT 전에 id가 결정되므로 TypeORM의 배치 INSERT가 동작한다.

```typescript
// TypeORM 배치 INSERT — @BeforeInsert()로 id 직접 할당 시 정상 동작
await manager.insert(Event, events);
// 내부적으로 INSERT ... VALUES (...), (...), ... 로 실행
```

### BINARY(16) 저장 방식 — ValueTransformer

Buffer 타입을 엔티티에서 직접 다루면 불편하다. TypeORM의 `transformer` 옵션으로 ULID 문자열과 바이트 배열 사이 자동 변환을 걸어두는 편이 낫다.

```typescript
import { ValueTransformer } from 'typeorm';

const ulidToBytesTransformer: ValueTransformer = {
    to(ulidStr: string | null): Buffer | null {
        if (ulidStr == null) return null;
        return ulidToBuffer(ulidStr);
    },
    from(dbData: Buffer | null): string | null {
        if (dbData == null) return null;
        return bufferToUlid(dbData);
    },
};

@Entity('events')
export class Event {
    @PrimaryColumn({ type: 'binary', length: 16, transformer: ulidToBytesTransformer })
    id: string;

    @BeforeInsert()
    generateId(): void {
        if (!this.id) {
            this.id = monotonicUlid();
        }
    }
}
```

엔티티에서는 string으로 다루고, DB에는 16바이트로 저장된다.

### Repository에서 ULID 기반 범위 쿼리

ULID의 타임스탬프를 이용하면 created_at 컬럼 없이도 PK 인덱스로 시각 범위 조회를 할 수 있다.

```typescript
// TypeORM Repository에서 ULID 범위 쿼리
const fromUlid = buildMinUlid(new Date('2024-01-01T00:00:00Z').getTime());
const events = await eventRepository
    .createQueryBuilder('e')
    .where('e.id >= :fromUlid', { fromUlid })
    .orderBy('e.id', 'ASC')
    .getMany();

// 특정 밀리초의 최솟값 ULID (랜덤 파트를 0으로 채운 값)
function buildMinUlid(epochMs: number): string {
    const base32Chars = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    // 48비트 타임스탬프를 앞에, 80비트 랜덤을 0으로
    let n = BigInt(epochMs) << 80n;
    let result = '';
    for (let i = 0; i < 26; i++) {
        result = base32Chars[Number(n & 31n)] + result;
        n >>= 5n;
    }
    return result;
}
```

별도 created_at 컬럼에 인덱스를 만들지 않아도 PK 인덱스 하나로 시각 범위 쿼리가 된다. 단, ULID PK가 클러스터드 인덱스일 때만 효율적이다. MySQL InnoDB는 PK가 클러스터드 인덱스라 해당한다.

## 타임스탬프 역산과 디버깅 활용

ULID에서 생성 시각을 꺼내는 방법은 간단하다.

```typescript
// Node.js (TypeScript)
import { decodeTime } from 'ulid';
const epochMs = decodeTime('01HX2Y3Z4A5B6C7D8E9F0G1H2J');
const date = new Date(epochMs);
const kstOffset = 9 * 60 * 60 * 1000;
const kstDate = new Date(epochMs + kstOffset);
```

```python
# Python
from ulid import ULID
u = ULID.from_str("01HX2Y3Z4A5B6C7D8E9F0G1H2J")
print(u.datetime)  # 2024-05-20 13:45:22.738000+00:00
```

```javascript
// Node.js
import { decodeTime } from 'ulid';
const epochMs = decodeTime('01HX2Y3Z4A5B6C7D8E9F0G1H2J');
new Date(epochMs); // Mon May 20 2024 13:45:22.738 GMT
```

이게 실무에서 쓸모 있는 상황이 있다. 에러 로그에 ULID만 남아 있어도 생성 시각을 바로 뽑아낼 수 있다. UUID v4라면 타임스탬프가 없어서 created_at 컬럼을 별도로 조회해야 한다.

```
에러 로그: "payment 01HX2Y3Z4A5B6C7D8E9F0G1H2J 처리 실패"
-> ULID에서 타임스탬프 추출 -> 2024-05-20 22:45:22.738 KST
-> 이 시각 전후의 외부 API 로그, DB 슬로우쿼리 로그 검색
```

CHAR(26)으로 저장했다면 SQL에서도 시각 범위 필터링이 가능하다.

```sql
-- 특정 날짜 범위의 이벤트 조회 (created_at 컬럼 없이)
SELECT * FROM events
WHERE id >= '01HWQD0000000000000000000'  -- 2024-05-20 00:00:00.000 기준 최솟값
  AND id <  '01HWRDM000000000000000000'; -- 2024-05-21 00:00:00.000 기준 최솟값
```

Monotonic ULID의 랜덤 파트가 단조 증가하더라도, 타임스탬프는 상위 48비트(10자리)에 고정돼 있다. 역산 시 항상 상위 10자리를 기준으로 한다.

## ULID vs UUID v7 실무 선택 기준

UUID v7도 ULID처럼 타임스탬프 기반 정렬 가능한 식별자다. 둘 다 128비트, 48비트 밀리초 타임스탬프, 단조 증가 특성을 갖는다.

차이는 형식이다.

```
ULID:     01HX2Y3Z4A5B6C7D8E9F0G1H2J     (26자리, Crockford Base32)
UUID v7:  018f7a23-4c9b-7e1d-8f0a-b2c3d4  (36자리, 16진수 + 대시)
```

UUID v7은 DB와 프레임워크 지원이 앞선다. PostgreSQL의 UUID 타입, MySQL의 `UUID_TO_BIN()`, Hibernate 6.2의 `@GeneratedValue(strategy = GenerationType.UUID)` 설정으로 UUID v7을 생성할 수 있다(별도 라이브러리 설정 필요). 기존 UUID v4 스택을 유지한 채 전환하기 쉽다.

ULID는 사람이 읽기 편한 형식이라는 게 주요 장점이다. 대시 없이 26자리 대문자라 복사-붙여넣기 실수가 적다. Crockford Base32 알파벳이 혼동하기 쉬운 문자를 제외해서 손으로 옮겨 쓸 때 I/1, O/0 같은 오타가 없다. URL에 그대로 넣어도 인코딩 문제가 없다.

| 항목 | ULID | UUID v7 |
|------|------|---------|
| 형식 | 26자리 Crockford Base32 | 36자리 UUID 형식 |
| DB 타입 지원 | CHAR(26), BINARY(16) | UUID, BINARY(16) |
| 프레임워크 지원 | 라이브러리 필요 | Hibernate 6.2+ 지원 |
| 가독성 | 높음 (혼동 문자 제외) | 낮음 (16진수 + 대시) |
| URL 안전 | 안전 | 대시 때문에 인코딩 필요할 수 있음 |
| 타임스탬프 정밀도 | 48비트 밀리초 | 48비트 밀리초 |

PostgreSQL + Spring 스택에서 UUID 타입 컬럼과 기존 호환성이 중요하면 UUID v7을 선택한다.

Redis 키, 로그 식별자, 외부 API로 노출하는 ID처럼 사람이 직접 다루는 맥락에서는 ULID가 편하다.

MySQL에서는 둘 다 BINARY(16)으로 저장하는 것이 공통이고, 선택은 주로 팀 컨벤션과 프레임워크 지원 편의성에 따라 갈린다.

## Redis/Cassandra에서 ULID 정렬 활용

### Redis

ULID 문자열 자체가 시각 순 정렬이 되므로, Sorted Set에서 score 없이 ZRANGEBYLEX로 시각 범위 조회를 할 수 있다.

```javascript
// ZSET에 score를 0으로 균일하게, member를 ULID로 저장
await redis.zadd('user:events:123', {
    score: 0,
    member: `${ulid()}:${JSON.stringify(eventData)}`
});

// 사전 순 = 시각 순 조회
const items = await redis.zrangebylex('user:events:123', '-', '+');
```

score에 타임스탬프를 저장하는 방식이 더 직관적인 경우도 있다.

```javascript
const now = Date.now();
const id = ulid(now);

await redis.zadd('feed:global', {
    score: now,  // 타임스탬프 score
    member: id   // ULID member
});

// 특정 시간대 이벤트 조회
const from = new Date('2024-01-01').getTime();
const to   = new Date('2024-01-02').getTime();
const ids  = await redis.zrangebyscore('feed:global', from, to);
```

ULID를 캐시 키로 쓸 때 생성 시각에서 TTL을 계산하는 패턴도 있다.

```javascript
import { decodeTime } from 'ulid';

const id = ulid();
await redis.hset(`session:${id}`, { userId, data: JSON.stringify(sessionData) });

// ULID에서 생성 시각 추출 -> TTL 계산
const createdAt = decodeTime(id);
const expiresAt = createdAt + 24 * 60 * 60 * 1000; // 24시간 후
await redis.pexpireat(`session:${id}`, expiresAt);
```

### Cassandra

Cassandra는 클러스터링 키 기준으로 파티션 내 데이터를 정렬한다. ULID를 클러스터링 키로 쓰면 삽입 순서 = 정렬 순서가 된다.

```cql
CREATE TABLE user_events (
    user_id    UUID,
    event_id   TEXT,   -- ULID
    event_type TEXT,
    payload    TEXT,
    PRIMARY KEY (user_id, event_id)
) WITH CLUSTERING ORDER BY (event_id ASC);
```

파티션 내에서 event_id(ULID) 기준 오름차순 정렬이 생성 시각 순 정렬과 일치한다.

```cql
-- 특정 시각 이후의 이벤트 조회
SELECT * FROM user_events
WHERE user_id = ?
  AND event_id >= '01HWQD0000000000000000000'
ORDER BY event_id ASC;
```

활성 사용자의 파티션이 무한히 커지는 문제가 있다. Cassandra는 파티션 크기를 수백 MB 이하로 유지하는 것을 권고하므로, 기간별로 파티션을 나누는 패턴을 쓴다.

```cql
CREATE TABLE user_events_partitioned (
    user_id     UUID,
    month       TEXT,   -- '2024-05' 형식
    event_id    TEXT,   -- ULID
    payload     TEXT,
    PRIMARY KEY ((user_id, month), event_id)
) WITH CLUSTERING ORDER BY (event_id ASC);
```

파티션 키를 `(user_id, month)` 복합으로 구성하면 특정 사용자의 특정 월 데이터가 하나의 파티션에 모인다. ULID 클러스터링으로 파티션 내 시각 순 정렬이 유지된다.

### DynamoDB

ULID를 Sort Key로 쓰면 시각 순 조회가 된다.

```
PK: USER#userId
SK: EVENT#01HX2Y3Z4A5B6C7D8E9F0G1H2J
```

```javascript
const result = await dynamodb.query({
    TableName: 'Events',
    KeyConditionExpression: 'PK = :pk AND SK >= :fromSk',
    ExpressionAttributeValues: {
        ':pk':    { S: `USER#${userId}` },
        ':fromSk': { S: `EVENT#01HWQD0000000000000000000` } // 2024-05-20 이후
    },
    ScanIndexForward: true  // SK 오름차순 = 시각 순
});
```

SK begins_with 패턴과 함께 쓰면 특정 사용자의 이벤트를 시각 순으로 효율적으로 조회할 수 있다.
