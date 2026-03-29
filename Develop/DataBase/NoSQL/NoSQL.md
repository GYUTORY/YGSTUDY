---
title: NoSQL 데이터베이스 개요
tags: [database, nosql, cap-theorem, mongodb, redis, cassandra, hbase, neo4j, column-family, document-database, key-value, graph-database]
updated: 2026-03-29
---

# NoSQL 데이터베이스 개요

## NoSQL이 뭔가

NoSQL은 "Not Only SQL"의 약자로, 관계형 데이터베이스(RDBMS)와 다른 방식으로 데이터를 저장하고 조회하는 데이터베이스를 통칭한다.

RDBMS는 테이블 간 조인, ACID 트랜잭션, 정규화된 스키마를 기본으로 한다. 이 구조는 데이터 무결성을 보장하지만, 수평 확장이 어렵고 스키마 변경 비용이 크다. 2000년대 중반부터 웹 서비스의 트래픽이 급증하면서 RDBMS만으로는 감당이 안 되는 상황이 생겼다.

Google의 BigTable 논문(2006)과 Amazon의 Dynamo 논문(2007)이 분산 데이터베이스의 이론적 기반을 잡았고, 이후 MongoDB, Cassandra, Redis, HBase 같은 오픈소스 구현체가 등장했다.

NoSQL을 쓴다고 RDBMS를 버리는 게 아니다. 실무에서는 RDBMS와 NoSQL을 같이 쓰는 경우가 대부분이다. 결제 데이터는 PostgreSQL에, 사용자 활동 로그는 Cassandra에, 세션 캐시는 Redis에 넣는 식이다.

---

## CAP 정리와 NoSQL

### CAP 정리란

분산 시스템에서 다음 세 가지를 동시에 만족시킬 수 없다는 정리다.

- **Consistency (일관성)**: 모든 노드가 같은 시점에 같은 데이터를 반환한다
- **Availability (가용성)**: 모든 요청이 성공/실패 응답을 받는다 (타임아웃 없음)
- **Partition Tolerance (분할 허용)**: 네트워크 분할이 발생해도 시스템이 동작한다

분산 시스템에서 네트워크 분할은 반드시 발생한다. 그래서 현실적으로는 P를 포기할 수 없고, C와 A 중 하나를 선택해야 한다.

### 각 NoSQL의 CAP 위치

| 분류 | 데이터베이스 | CAP 선택 | 실무에서 의미하는 것 |
|------|-------------|---------|-------------------|
| CP | MongoDB (기본 설정) | 일관성 + 분할 허용 | Primary 노드 장애 시 새 Primary 선출 완료까지 쓰기 불가. 보통 10~30초 |
| CP | HBase | 일관성 + 분할 허용 | RegionServer 장애 시 해당 Region의 읽기/쓰기가 일시 중단 |
| AP | Cassandra | 가용성 + 분할 허용 | 노드 장애가 나도 다른 노드에서 읽기/쓰기 가능. 대신 읽은 데이터가 최신이 아닐 수 있음 |
| AP | DynamoDB | 가용성 + 분할 허용 | Eventually Consistent Read가 기본. Strongly Consistent Read 옵션도 있지만 처리량이 2배 소모 |
| CP | Redis (Cluster) | 일관성 + 분할 허용 | 마스터 노드 장애 시 failover 동안 해당 슬롯의 요청 실패 |
| CA | Neo4j (단일 인스턴스) | 일관성 + 가용성 | 분산 환경이 아닌 단일 서버에서 동작. 분할이 없으니 CA가 가능 |

주의할 점: CAP은 이분법이 아니다. Cassandra는 쿼리 단위로 일관성 레벨을 조절할 수 있다.

```cql
-- Cassandra: 쿼리별 일관성 레벨 조절
-- ONE: 노드 1개만 응답하면 OK (빠르지만 최신 데이터 아닐 수 있음)
SELECT * FROM user_events WHERE user_id = ? CONSISTENCY ONE;

-- QUORUM: 과반수 노드가 응답해야 OK (일관성과 가용성의 균형)
SELECT * FROM user_events WHERE user_id = ? CONSISTENCY QUORUM;

-- ALL: 모든 노드가 응답해야 OK (가장 느리지만 일관성 보장)
SELECT * FROM user_events WHERE user_id = ? CONSISTENCY ALL;
```

MongoDB도 Read Concern / Write Concern으로 일관성 수준을 조절한다.

```javascript
// MongoDB: Write Concern으로 쓰기 일관성 조절
// w: 1 — Primary에만 쓰면 OK (기본값, 빠름)
await collection.insertOne(doc, { writeConcern: { w: 1 } });

// w: "majority" — 과반수 노드에 복제 완료 후 응답 (안전)
await collection.insertOne(doc, { writeConcern: { w: "majority" } });

// Read Concern: "majority" — 과반수 노드에 커밋된 데이터만 읽기
const cursor = collection.find({}).readConcern("majority");
```

---

## NoSQL 4가지 유형

### 1. 문서형(Document) — MongoDB, CouchDB

데이터를 JSON/BSON 형태의 문서로 저장한다. 하나의 문서 안에 중첩된 구조를 넣을 수 있어서 조인 없이 관련 데이터를 한 번에 가져올 수 있다.

**데이터 구조 예시 — 주문 데이터:**

```json
{
  "_id": "order_20260329_001",
  "user_id": "u_1234",
  "items": [
    {
      "product_id": "p_100",
      "name": "무선 키보드",
      "price": 59000,
      "quantity": 1
    },
    {
      "product_id": "p_205",
      "name": "USB-C 허브",
      "price": 32000,
      "quantity": 2
    }
  ],
  "shipping": {
    "address": "서울시 강남구 테헤란로 123",
    "method": "express",
    "tracking_number": null
  },
  "total_amount": 123000,
  "status": "PAID",
  "created_at": "2026-03-29T10:30:00Z"
}
```

RDBMS였으면 orders, order_items, shipping_info 테이블 3개에 나눠 저장하고 조인해야 한다. 문서형 DB는 이걸 한 문서에 담는다.

**쿼리 예제 (MongoDB):**

```javascript
const { MongoClient } = require('mongodb');
const client = new MongoClient('mongodb://localhost:27017');
const db = client.db('shop');
const orders = db.collection('orders');

// 특정 사용자의 최근 주문 10건
const recentOrders = await orders
  .find({ user_id: 'u_1234', status: { $ne: 'CANCELLED' } })
  .sort({ created_at: -1 })
  .limit(10)
  .toArray();

// 집계: 사용자별 총 구매액
const spending = await orders.aggregate([
  { $match: { status: 'COMPLETED' } },
  { $group: {
    _id: '$user_id',
    total: { $sum: '$total_amount' },
    count: { $sum: 1 }
  }},
  { $sort: { total: -1 } },
  { $limit: 20 }
]).toArray();

// 중첩 필드 인덱스
await orders.createIndex({ 'items.product_id': 1 });
await orders.createIndex({ user_id: 1, created_at: -1 });
```

**쓸 만한 경우:** 상품 카탈로그(상품마다 속성이 다름), 사용자 프로필, CMS 콘텐츠, 주문/장바구니

**주의사항:** 문서 크기 제한이 있다(MongoDB는 16MB). 문서 안에 배열이 무한히 커지는 구조는 피해야 한다. 댓글이 수만 개 달리는 게시물이면 댓글은 별도 컬렉션으로 분리하는 게 맞다.

### 2. 키-값(Key-Value) — Redis, DynamoDB

키 하나에 값 하나를 매핑하는 가장 단순한 구조다. 값은 문자열, 숫자, JSON, 바이너리 등 뭐든 될 수 있다. 구조가 단순한 만큼 읽기/쓰기가 빠르다.

**Redis 데이터 구조별 사용 예시:**

```bash
# String — 세션 저장, 캐시
SET session:abc123 '{"user_id":"u_1234","role":"admin"}' EX 3600
GET session:abc123

# Hash — 객체를 필드 단위로 관리
HSET user:1234 name "김개발" email "kim@dev.com" login_count 42
HINCRBY user:1234 login_count 1
HGET user:1234 login_count

# Sorted Set — 실시간 랭킹
ZADD game:leaderboard 15200 player_a
ZADD game:leaderboard 18900 player_b
ZADD game:leaderboard 12100 player_c
ZREVRANGE game:leaderboard 0 9 WITHSCORES   # 상위 10명

# List — 작업 큐
RPUSH email:queue '{"to":"a@b.com","subject":"가입 완료"}'
LPOP email:queue                              # 큐에서 하나 꺼냄

# Set — 온라인 유저 추적
SADD online:users u_1234 u_5678
SISMEMBER online:users u_1234                 # 1 (온라인)
SCARD online:users                            # 현재 접속자 수
```

**애플리케이션 코드에서 캐시 패턴:**

```java
@Service
@RequiredArgsConstructor
public class ProductCacheService {
    private final RedisTemplate<String, String> redis;
    private final ProductRepository productRepo;

    public Product getProduct(Long id) {
        String key = "product:" + id;
        String cached = redis.opsForValue().get(key);

        if (cached != null) {
            return objectMapper.readValue(cached, Product.class);
        }

        // Cache miss — DB 조회 후 캐시 저장
        Product product = productRepo.findById(id)
            .orElseThrow(() -> new NotFoundException("상품 없음: " + id));
        redis.opsForValue().set(key, objectMapper.writeValueAsString(product),
            Duration.ofMinutes(10));
        return product;
    }

    // 상품 수정 시 캐시 무효화
    public void invalidate(Long id) {
        redis.delete("product:" + id);
    }
}
```

**쓸 만한 경우:** 세션 저장, API 응답 캐시, Rate Limiting, 실시간 랭킹, 분산 락

**주의사항:** Redis는 메모리 DB라서 메모리보다 큰 데이터를 넣으면 OOM으로 프로세스가 죽는다. maxmemory 설정과 eviction 정책(allkeys-lru 등)을 반드시 잡아야 한다. 영속성이 필요하면 AOF나 RDB 스냅샷을 켜야 하는데, AOF를 fsync=always로 쓰면 쓰기 성능이 크게 떨어진다.

### 3. 컬럼 패밀리(Column Family) — Cassandra, HBase

RDBMS의 테이블과 비슷해 보이지만 내부 구조가 다르다. 행(Row)마다 서로 다른 컬럼을 가질 수 있고, 컬럼 단위로 데이터를 저장한다. 대량 쓰기와 시계열 데이터에 적합하다.

#### Cassandra 데이터 모델

Cassandra의 핵심은 **파티션 키**와 **클러스터링 키**다.

- **파티션 키**: 데이터가 어떤 노드에 저장될지 결정한다. 같은 파티션 키를 가진 데이터는 같은 노드에 모인다.
- **클러스터링 키**: 파티션 내에서 데이터의 정렬 순서를 결정한다.

```
Partition Key: user_id = "u_1234"
┌──────────────────────────────────────────────────────┐
│ Clustering Key (event_at DESC)                       │
│                                                      │
│ 2026-03-29 10:30  │ PAGE_VIEW  │ /products/123      │
│ 2026-03-29 10:25  │ CLICK      │ /banner/spring     │
│ 2026-03-29 10:20  │ LOGIN      │ null               │
│ 2026-03-28 22:15  │ PURCHASE   │ order_001          │
│ ...                                                  │
└──────────────────────────────────────────────────────┘

Partition Key: user_id = "u_5678"
┌──────────────────────────────────────────────────────┐
│ 2026-03-29 11:00  │ LOGIN      │ null               │
│ 2026-03-29 09:45  │ PAGE_VIEW  │ /dashboard         │
│ ...                                                  │
└──────────────────────────────────────────────────────┘
```

각 파티션이 독립적이다. 파티션 키 없이 전체 스캔하는 쿼리는 모든 노드를 뒤져야 하니까 느리다.

**Cassandra CQL 예제:**

```sql
-- 키스페이스 생성 (3개 노드 복제)
CREATE KEYSPACE analytics WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'datacenter1': 3
};

-- 사용자 이벤트 테이블
-- (user_id)가 파티션 키, event_at이 클러스터링 키
CREATE TABLE analytics.user_events (
  user_id    text,
  event_at   timestamp,
  event_type text,
  payload    text,
  PRIMARY KEY (user_id, event_at)
) WITH CLUSTERING ORDER BY (event_at DESC)
  AND default_time_to_live = 7776000;  -- 90일 후 자동 삭제

-- 데이터 삽입
INSERT INTO analytics.user_events (user_id, event_at, event_type, payload)
VALUES ('u_1234', toTimestamp(now()), 'PAGE_VIEW', '{"url":"/products/123"}');

-- 특정 사용자의 최근 이벤트 조회 (파티션 키 지정 — 빠름)
SELECT * FROM analytics.user_events
WHERE user_id = 'u_1234'
  AND event_at >= '2026-03-28 00:00:00'
LIMIT 100;

-- 이벤트 타입별 필터 (파티션 키 + 클러스터링 키 + 일반 컬럼)
-- 일반 컬럼 필터는 ALLOW FILTERING 필요 (주의: 성능 나쁨)
SELECT * FROM analytics.user_events
WHERE user_id = 'u_1234'
  AND event_type = 'PURCHASE'
ALLOW FILTERING;
```

`ALLOW FILTERING`은 가급적 쓰지 않는다. 필요하면 별도 테이블을 만들어서 쿼리 패턴에 맞게 비정규화한다.

```sql
-- 이벤트 타입별 조회가 자주 필요하면 별도 테이블
CREATE TABLE analytics.events_by_type (
  user_id    text,
  event_type text,
  event_at   timestamp,
  payload    text,
  PRIMARY KEY ((user_id, event_type), event_at)
) WITH CLUSTERING ORDER BY (event_at DESC);
```

같은 데이터를 2개 테이블에 넣는다. Cassandra에서는 이게 정상이다. "쿼리 먼저, 테이블은 쿼리에 맞춰 설계한다"가 기본 원칙이다.

#### HBase 데이터 모델

HBase는 Hadoop 위에서 동작하는 컬럼 패밀리 DB다. Google BigTable의 오픈소스 구현이다.

```
Row Key: "u_1234#20260329103000"
┌─────────────────────────────────────────────────┐
│ Column Family: info                             │
│   info:event_type = "PAGE_VIEW"                 │
│   info:url = "/products/123"                    │
│                                                 │
│ Column Family: meta                             │
│   meta:device = "mobile"                        │
│   meta:ip = "192.168.1.100"                     │
└─────────────────────────────────────────────────┘
```

HBase에서는 Row Key 설계가 성능의 대부분을 결정한다. Row Key가 순차적이면(예: 타임스탬프만 사용) 특정 Region에 쓰기가 몰리는 핫스팟 문제가 생긴다. `user_id#timestamp` 형태로 Row Key를 잡으면 사용자 단위로 데이터가 분산된다.

**Cassandra vs HBase 비교:**

| 항목 | Cassandra | HBase |
|------|-----------|-------|
| 아키텍처 | 마스터 없는 P2P 링 구조 | Master-Slave (HMaster + RegionServer) |
| 쓰기 성능 | 매우 높음 (모든 노드가 쓰기 가능) | 높음 (단, RegionServer 단위) |
| 읽기 성능 | 쓰기보다는 느림 | 랜덤 읽기가 빠름 (BloomFilter 활용) |
| 일관성 | Tunable (ONE ~ ALL) | Strong Consistency |
| 운영 복잡도 | 상대적으로 낮음 | Hadoop/ZooKeeper 의존으로 높음 |
| 적합한 곳 | 쓰기 많은 시계열, 이벤트 로그 | Hadoop 에코시스템과 통합, 배치 분석 |

Cassandra는 단독으로 돌릴 수 있고, HBase는 Hadoop(HDFS) + ZooKeeper가 필요하다. 이미 Hadoop 클러스터가 있으면 HBase가 자연스럽고, 없으면 Cassandra가 운영 부담이 적다.

### 4. 그래프(Graph) — Neo4j, Amazon Neptune

노드(엔티티)와 엣지(관계)로 데이터를 표현한다. "A가 B를 팔로우한다", "사용자 X가 상품 Y를 구매했다" 같은 관계를 직접 저장한다.

RDBMS에서 관계를 표현하려면 중간 테이블(join table)을 만들고 조인해야 한다. 3단계 이상의 관계(친구의 친구의 친구)를 탐색하면 조인이 기하급수적으로 늘어난다. 그래프 DB는 이런 다단계 관계 탐색에 특화되어 있다.

**Neo4j Cypher 쿼리 예제:**

```cypher
// 노드 생성
CREATE (alice:User {name: 'Alice', age: 30})
CREATE (bob:User {name: 'Bob', age: 28})
CREATE (product:Product {name: '무선 키보드', price: 59000})

// 관계 생성
CREATE (alice)-[:FOLLOWS]->(bob)
CREATE (alice)-[:PURCHASED {date: '2026-03-29', amount: 59000}]->(product)
CREATE (bob)-[:PURCHASED {date: '2026-03-28', amount: 59000}]->(product)

// 2단계 팔로우 관계 탐색 (친구의 친구)
MATCH (me:User {name: 'Alice'})-[:FOLLOWS]->()-[:FOLLOWS]->(suggestion)
WHERE suggestion <> me
  AND NOT (me)-[:FOLLOWS]->(suggestion)
RETURN DISTINCT suggestion.name

// 같은 상품을 구매한 사용자 찾기 (협업 필터링)
MATCH (me:User {name: 'Alice'})-[:PURCHASED]->(p:Product)<-[:PURCHASED]-(other:User)
WHERE other <> me
RETURN other.name, count(p) AS common_purchases
ORDER BY common_purchases DESC
LIMIT 10

// 최단 경로 탐색
MATCH path = shortestPath(
  (a:User {name: 'Alice'})-[:FOLLOWS*..6]-(b:User {name: 'Charlie'})
)
RETURN path
```

**쓸 만한 경우:** 소셜 네트워크(팔로우, 차단, 추천), 사기 탐지(계좌 간 거래 패턴), 지식 그래프, 조직도/권한 체계

**주의사항:** 그래프 DB는 수평 확장이 어렵다. Neo4j의 클러스터링은 읽기 확장만 가능하고, 쓰기는 단일 리더에서 처리한다. 데이터가 수십억 노드를 넘어가면 Neo4j보다는 분산 그래프 DB(JanusGraph, Neptune)를 검토해야 한다.

---

## RDBMS에서 NoSQL로 전환할 때 겪는 문제

### 1. 조인을 제거해야 한다

NoSQL은 기본적으로 조인을 지원하지 않거나 성능이 나쁘다. RDBMS에서 정규화된 테이블 3~4개를 조인하던 쿼리를 NoSQL에서는 **비정규화(Denormalization)**로 풀어야 한다.

**RDBMS 구조:**

```sql
-- 정규화된 테이블 3개
SELECT o.id, o.total, u.name, u.email, p.name, oi.quantity
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.user_id = 1234;
```

**MongoDB로 전환한 구조:**

```json
{
  "_id": "order_001",
  "user": {
    "id": "u_1234",
    "name": "김개발",
    "email": "kim@dev.com"
  },
  "items": [
    {
      "product_id": "p_100",
      "product_name": "무선 키보드",
      "quantity": 1,
      "price": 59000
    }
  ],
  "total": 59000
}
```

사용자 이름과 상품명을 주문 문서 안에 복사해 넣었다. 조회는 빨라지지만, 사용자가 이름을 바꾸면 과거 주문의 이름도 업데이트할지 결정해야 한다. 대부분의 경우 주문 시점의 이름을 유지하는 게 맞으니까 비정규화가 자연스럽다. 하지만 항상 최신 데이터를 보여줘야 하는 경우에는 별도 조회가 필요하고, 이건 추가 네트워크 호출이다.

### 2. 트랜잭션을 포기해야 할 수 있다

RDBMS에서는 여러 테이블에 걸친 트랜잭션을 당연히 쓴다. NoSQL에서는 이게 제한적이다.

**MongoDB 4.0+**: 멀티 도큐먼트 트랜잭션을 지원한다. 하지만 성능 오버헤드가 있고, 샤딩된 클러스터에서는 더 느리다. 트랜잭션이 필요 없게 데이터 모델을 설계하는 게 우선이다.

```javascript
// MongoDB 트랜잭션 — 계좌 이체
const session = client.startSession();
try {
  session.startTransaction();

  await accounts.updateOne(
    { _id: 'from_account', balance: { $gte: 50000 } },
    { $inc: { balance: -50000 } },
    { session }
  );
  await accounts.updateOne(
    { _id: 'to_account' },
    { $inc: { balance: 50000 } },
    { session }
  );

  await session.commitTransaction();
} catch (e) {
  await session.abortTransaction();
  throw e;
} finally {
  session.endSession();
}
```

**Cassandra**: 멀티 파티션 트랜잭션이 없다. Lightweight Transaction(LWT)이 있지만 성능이 나빠서 메인 흐름에 쓰기 어렵다.

```sql
-- Cassandra LWT: Compare-and-Set
-- 이메일 중복 체크 같은 간단한 경우에만 사용
INSERT INTO users (email, name) VALUES ('kim@dev.com', '김개발')
IF NOT EXISTS;
```

**트랜잭션 없이 일관성을 유지하는 방법:**

- **단일 문서/파티션 설계**: 관련 데이터를 한 문서에 넣으면 단일 쓰기 연산으로 원자성 확보
- **이벤트 소싱**: 상태 변경을 이벤트로 기록하고, 이벤트를 순서대로 재생하여 상태 복원
- **Saga 패턴**: 분산 트랜잭션을 여러 로컬 트랜잭션으로 쪼개고, 실패 시 보상 트랜잭션 실행

금융 거래처럼 강한 일관성이 필요한 부분은 RDBMS에 남겨두는 게 현실적이다.

### 3. 쿼리 패턴을 먼저 정해야 한다

RDBMS는 데이터를 정규화해서 넣어두면 어떤 쿼리든 조인으로 만들 수 있다. NoSQL(특히 Cassandra, DynamoDB)은 쿼리 패턴을 먼저 정하고 거기에 맞춰 테이블을 설계한다.

"나중에 이런 쿼리도 필요하겠지?"하고 대충 설계하면, 운영 중에 새로운 조회 요구사항이 나왔을 때 테이블을 새로 만들고 기존 데이터를 마이그레이션해야 한다. 이건 RDBMS에서 인덱스 하나 추가하는 것과 차원이 다른 작업이다.

### 4. 데이터 정합성을 애플리케이션에서 관리해야 한다

RDBMS에서는 외래 키 제약, 유니크 제약, CHECK 제약으로 DB 레벨에서 데이터 정합성을 보장한다. NoSQL은 이런 제약이 대부분 없다.

- 존재하지 않는 user_id로 주문을 생성해도 DB는 모른다
- 같은 이메일로 사용자가 2명 생겨도 DB가 막아주지 않는다(일부 DB에서 유니크 인덱스를 지원하지만)
- 카테고리가 삭제돼도 해당 카테고리를 참조하는 상품 데이터는 그대로 남는다

이런 검증을 애플리케이션 코드에서 처리해야 한다. 코드 레벨 검증은 버그가 들어갈 여지가 DB 제약보다 크다.

---

## NoSQL 선택 기준

추상적으로 "대용량이면 NoSQL"이라고 말하면 아무 도움이 안 된다. 구체적인 수치와 패턴으로 판단해야 한다.

### 읽기/쓰기 비율

| 패턴 | 비율 | 적합한 DB | 이유 |
|------|------|----------|------|
| 읽기 집중 | 읽기:쓰기 = 90:10 이상 | MongoDB, Redis(캐시) | MongoDB는 인덱스 기반 읽기가 빠르고, Redis는 인메모리 읽기 |
| 쓰기 집중 | 쓰기:읽기 = 70:30 이상 | Cassandra | LSM-Tree 기반이라 쓰기가 append-only, 디스크 seek 없음 |
| 읽기/쓰기 균형 | 50:50 부근 | MongoDB, DynamoDB | 범용적으로 양쪽 다 무난 |

### 데이터 크기와 증가율

| 규모 | 범위 | 적합한 DB |
|------|------|----------|
| 소규모 | 수 GB 이하 | RDBMS로 충분. NoSQL을 쓸 이유가 없다 |
| 중규모 | 수십 GB ~ 수 TB | MongoDB (샤딩 없이도 가능), DynamoDB |
| 대규모 | 수 TB ~ 수백 TB | Cassandra, HBase |
| 시계열/로그 | 하루 수 GB씩 계속 쌓임 | Cassandra (TTL로 자동 삭제), 전용 TSDB(InfluxDB) |

데이터가 10GB 이하인데 NoSQL을 쓰겠다는 건 대부분 과잉 설계다. PostgreSQL의 JSONB 타입으로도 유연한 스키마를 처리할 수 있다.

### 일관성 요구사항

| 요구사항 | 예시 | 적합한 DB |
|---------|------|----------|
| 강한 일관성 필수 | 결제, 재고 차감, 포인트 적립 | RDBMS (포기하지 마라) |
| 최종 일관성 허용 | 타임라인, 좋아요 수, 추천 목록 | Cassandra, DynamoDB |
| 읽기 시 최신 데이터 필요하지만 트랜잭션은 불필요 | 사용자 프로필, 설정 | MongoDB (Read Concern: majority) |

### 쿼리 복잡도

| 쿼리 패턴 | 적합한 DB | 부적합한 DB |
|----------|----------|------------|
| 키 기반 단건 조회 | Redis, DynamoDB | - |
| 다양한 조건 검색 + 정렬 + 페이징 | MongoDB | Cassandra (파티션 키 필수) |
| 특정 키 기준 범위 스캔 | Cassandra, HBase | Redis |
| 다단계 관계 탐색 | Neo4j | 나머지 전부 |
| 복잡한 집계/분석 | MongoDB (Aggregation), RDBMS | Redis, Cassandra |

### 판단 흐름

```
데이터가 10GB 이하인가?
  → Yes: RDBMS를 쓴다. 끝.
  → No: 계속 진행

트랜잭션이 핵심 요구사항인가?
  → Yes: 핵심 데이터는 RDBMS, 나머지만 NoSQL 검토
  → No: 계속 진행

데이터 구조가 어떤가?
  → JSON 같은 중첩 구조: MongoDB
  → 키-값 단순 조회: Redis, DynamoDB
  → 시계열/이벤트 로그: Cassandra
  → 엔티티 간 관계 중심: Neo4j

초당 요청 수는?
  → 1만 이하: 단일 인스턴스로 충분
  → 1만~10만: 레플리카 + 샤딩 구성
  → 10만 이상: Cassandra, DynamoDB 같은 분산 네이티브 DB
```

---

## 운영 시 주의사항

### 인덱스 관리

MongoDB에서 인덱스 없이 쿼리하면 컬렉션 풀 스캔이 발생한다. 문서 수가 100만 건만 넘어도 응답 시간이 수 초로 늘어난다.

```javascript
// explain으로 쿼리 실행 계획 확인
const plan = await orders
  .find({ status: 'PAID' })
  .explain('executionStats');

// totalDocsExamined vs totalKeysExamined 비교
// totalDocsExamined이 훨씬 크면 인덱스가 제대로 안 타고 있는 것
```

인덱스를 많이 만들면 쓰기 성능이 떨어진다. 쓸 때마다 모든 인덱스를 업데이트해야 하니까. 인덱스는 실제 쿼리 패턴에 맞춰 필요한 것만 만든다.

### Cassandra 파티션 크기

Cassandra에서 하나의 파티션이 100MB를 넘으면 성능이 나빠지기 시작한다. 시계열 데이터를 저장할 때 user_id만 파티션 키로 쓰면, 활동이 많은 사용자의 파티션이 비대해진다.

```sql
-- 파티션 키에 날짜를 추가해서 파티션 크기 제한
CREATE TABLE analytics.user_events_daily (
  user_id    text,
  event_date date,
  event_at   timestamp,
  event_type text,
  payload    text,
  PRIMARY KEY ((user_id, event_date), event_at)
) WITH CLUSTERING ORDER BY (event_at DESC);
```

이렇게 하면 파티션이 사용자+날짜 단위로 쪼개진다. 대신 "지난 7일간 이벤트 조회"를 하려면 7개 파티션을 각각 조회해야 한다.

### 백업

MongoDB는 `mongodump`로 논리 백업을 뜰 수 있고, Percona Server for MongoDB는 핫 백업을 지원한다. 레플리카셋에서는 Secondary 노드에서 백업하면 Primary 성능에 영향이 없다.

Cassandra는 `nodetool snapshot`으로 SSTable 단위 스냅샷을 뜬다. 각 노드에서 개별적으로 실행해야 하고, 전체 클러스터 복원 시 토큰 범위를 맞춰야 하니까 복원 절차가 복잡하다.

---

## 관련 문서

- [Redis 다루기](./Redis/Redis%20다루기.md) — Redis 실전 활용
- [데이터베이스 성능 튜닝](../RDBMS/데이터베이스_성능_튜닝.md) — RDBMS 성능 비교 관점
- [데이터베이스 복제 전략](../RDBMS/복제_전략.md) — 고가용성 구성

---

**참고 자료:**

- "Designing Data-Intensive Applications" — Martin Kleppmann
- "NoSQL Distilled" — Martin Fowler, Pramod Sadalage
- Apache Cassandra 공식 문서: https://cassandra.apache.org/doc/
- MongoDB 공식 문서: https://docs.mongodb.com/
- Neo4j Cypher Manual: https://neo4j.com/docs/cypher-manual/
