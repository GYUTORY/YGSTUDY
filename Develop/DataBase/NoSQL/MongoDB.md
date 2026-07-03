---
title: MongoDB 심화
tags: [database, nosql, mongodb, document-database, aggregation, index, replica-set, sharding, schema-design, transaction, change-streams, profiling, security, backup, monitoring]
updated: 2026-04-12
---

# MongoDB 심화

## 개요

MongoDB는 **문서(Document) 기반 NoSQL 데이터베이스**이다. JSON과 유사한 BSON 형태로 데이터를 저장하며, 스키마를 강제하지 않는다.

```
RDBMS                    MongoDB
─────────               ─────────
Database                Database
Table                   Collection
Row                     Document
Column                  Field
JOIN                    Embedded Document / $lookup
Primary Key             _id (자동 생성)
```

### 언제 MongoDB를 쓰는가

| 적합한 경우 | 부적합한 경우 |
|------------|-------------|
| 스키마가 자주 변경됨 | 강한 트랜잭션 무결성 필수 |
| 비정형/반정형 데이터 | 복잡한 JOIN이 많은 경우 |
| 빠른 읽기/쓰기 필요 | 데이터 관계가 복잡 |
| 수평 확장이 필요 | 정규화된 데이터 모델 |
| 프로토타이핑/MVP | 엄격한 스키마 제약 필요 |

## 핵심

### 1. 문서 구조

```javascript
// MongoDB 문서 (BSON)
{
    _id: ObjectId("65f1a2b3c4d5e6f7a8b9c0d1"),  // 자동 생성 PK
    name: "홍길동",
    email: "hong@example.com",
    age: 28,
    address: {                        // 내장 문서 (Embedded Document)
        city: "서울",
        district: "강남구",
        zipCode: "06000"
    },
    orders: [                         // 배열
        {
            productId: ObjectId("..."),
            productName: "노트북",
            amount: 1500000,
            orderedAt: ISODate("2026-02-15")
        }
    ],
    tags: ["vip", "premium"],         // 배열
    createdAt: ISODate("2026-01-01"),
    metadata: {                       // 유연한 스키마
        loginCount: 42,
        lastLogin: ISODate("2026-03-01")
    }
}
```

### 2. CRUD 연산

```javascript
// ── Create ──
db.users.insertOne({
    name: "홍길동",
    email: "hong@example.com",
    age: 28
});

db.users.insertMany([
    { name: "김철수", age: 25 },
    { name: "이영희", age: 30 }
]);

// ── Read ──
// 전체 조회
db.users.find();

// 조건 조회
db.users.find({ age: { $gte: 25 } });

// 내장 문서 조건
db.users.find({ "address.city": "서울" });

// 프로젝션 (필요한 필드만)
db.users.find(
    { age: { $gte: 25 } },
    { name: 1, email: 1, _id: 0 }
);

// 정렬, 페이지네이션
db.users.find()
    .sort({ createdAt: -1 })
    .skip(20)
    .limit(10);

// ── Update ──
db.users.updateOne(
    { _id: ObjectId("...") },
    { $set: { name: "홍길순" }, $inc: { age: 1 } }
);

// 배열에 요소 추가
db.users.updateOne(
    { _id: ObjectId("...") },
    { $push: { tags: "gold" } }
);

// 배열에서 요소 제거
db.users.updateOne(
    { _id: ObjectId("...") },
    { $pull: { tags: "vip" } }
);

// Upsert (없으면 생성)
db.users.updateOne(
    { email: "new@example.com" },
    { $set: { name: "신규 사용자" } },
    { upsert: true }
);

// ── Delete ──
db.users.deleteOne({ _id: ObjectId("...") });
db.users.deleteMany({ age: { $lt: 18 } });
```

#### 쿼리 연산자

| 연산자 | 의미 | 예시 |
|--------|------|------|
| `$eq` | 같음 | `{ age: { $eq: 25 } }` |
| `$ne` | 다름 | `{ status: { $ne: "deleted" } }` |
| `$gt / $gte` | 크다 / 이상 | `{ age: { $gte: 20 } }` |
| `$lt / $lte` | 작다 / 이하 | `{ price: { $lt: 10000 } }` |
| `$in` | 포함 | `{ status: { $in: ["active", "pending"] } }` |
| `$exists` | 필드 존재 여부 | `{ phone: { $exists: true } }` |
| `$regex` | 정규식 | `{ name: { $regex: /^홍/ } }` |
| `$and / $or` | 논리 연산 | `{ $or: [{ age: 25 }, { age: 30 }] }` |

### 3. Aggregation Pipeline

데이터를 **단계별로 변환/집계**하는 파이프라인. SQL의 GROUP BY, JOIN, 서브쿼리를 대체한다.

```javascript
// 파이프라인 구조
db.collection.aggregate([
    { $match: { ... } },      // WHERE
    { $group: { ... } },      // GROUP BY
    { $sort: { ... } },       // ORDER BY
    { $project: { ... } },    // SELECT
    { $limit: 10 },           // LIMIT
]);
```

```mermaid
flowchart LR
    A["$match<br/>조건 필터링"] --> B["$group<br/>그룹화/집계"]
    B --> C["$sort<br/>정렬"]
    C --> D["$project<br/>필드 선택"]
    D --> E["$limit<br/>결과 제한"]

    style A fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style B fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style C fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style D fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style E fill:#2d3748,stroke:#4a5568,color:#e2e8f0
```

#### 실전 예시

```javascript
// 1. 카테고리별 총 매출과 평균 가격
db.orders.aggregate([
    { $match: { status: "completed" } },
    { $unwind: "$items" },                    // 배열 펼치기
    { $group: {
        _id: "$items.category",
        totalRevenue: { $sum: "$items.price" },
        avgPrice: { $avg: "$items.price" },
        orderCount: { $sum: 1 }
    }},
    { $sort: { totalRevenue: -1 } },
    { $limit: 5 }
]);

// 2. 월별 신규 가입자 수
db.users.aggregate([
    { $group: {
        _id: {
            year: { $year: "$createdAt" },
            month: { $month: "$createdAt" }
        },
        count: { $sum: 1 }
    }},
    { $sort: { "_id.year": -1, "_id.month": -1 } }
]);

// 3. $lookup (LEFT JOIN 대체)
db.orders.aggregate([
    { $lookup: {
        from: "users",            // JOIN 대상 컬렉션
        localField: "userId",     // orders의 필드
        foreignField: "_id",      // users의 필드
        as: "user"                // 결과 필드명
    }},
    { $unwind: "$user" },
    { $project: {
        orderId: 1,
        amount: 1,
        "user.name": 1,
        "user.email": 1
    }}
]);

// 4. $facet (다중 집계를 한 번에)
db.products.aggregate([
    { $facet: {
        "priceStats": [
            { $group: {
                _id: null,
                avgPrice: { $avg: "$price" },
                maxPrice: { $max: "$price" },
                minPrice: { $min: "$price" }
            }}
        ],
        "categoryCount": [
            { $group: { _id: "$category", count: { $sum: 1 } } },
            { $sort: { count: -1 } }
        ],
        "recentProducts": [
            { $sort: { createdAt: -1 } },
            { $limit: 5 },
            { $project: { name: 1, price: 1 } }
        ]
    }}
]);
```

### 4. 인덱스

```javascript
// 단일 필드 인덱스
db.users.createIndex({ email: 1 });            // 오름차순
db.users.createIndex({ createdAt: -1 });       // 내림차순

// 복합 인덱스 (Compound Index)
db.orders.createIndex({ userId: 1, createdAt: -1 });

// 유니크 인덱스
db.users.createIndex({ email: 1 }, { unique: true });

// TTL 인덱스 (자동 만료)
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 3600 });
// → 1시간 후 자동 삭제

// 텍스트 인덱스 (전문 검색)
db.articles.createIndex({ title: "text", content: "text" });
db.articles.find({ $text: { $search: "MongoDB 성능" } });

// 쿼리 분석
db.users.find({ email: "hong@example.com" }).explain("executionStats");
// → COLLSCAN (전체 스캔) vs IXSCAN (인덱스 스캔) 확인
```

| 인덱스 유형 | 용도 |
|------------|------|
| 단일 필드 | 특정 필드 검색/정렬 |
| 복합 인덱스 | 여러 필드 조합 조건 |
| 유니크 | 중복 방지 |
| TTL | 세션, 캐시 자동 만료 |
| 텍스트 | 전문 검색 |
| 해시 | 샤딩용 균등 분배 |

### 5. 스키마 설계 패턴

#### 내장 (Embedding) vs 참조 (Referencing)

```javascript
// 내장 (Embedding): 함께 조회되는 데이터
// → 1:1 또는 1:소수 관계
{
    _id: ObjectId("..."),
    name: "홍길동",
    address: {             // 내장 문서
        city: "서울",
        district: "강남구"
    }
}

// 참조 (Referencing): 독립적인 데이터
// → 1:다수 또는 다:다 관계
{
    _id: ObjectId("..."),
    name: "홍길동",
    orderIds: [            // ID만 저장
        ObjectId("order1"),
        ObjectId("order2")
    ]
}
```

| 비교 | 내장 (Embedding) | 참조 (Referencing) |
|------|-----------------|-------------------|
| **읽기 성능** | 빠름 (1번 쿼리) | 느림 ($lookup 필요) |
| **쓰기 성능** | 느릴 수 있음 | 빠름 |
| **데이터 일관성** | 중복 가능 | 단일 소스 |
| **문서 크기** | 커질 수 있음 (16MB 제한) | 작음 |
| **적합한 경우** | 함께 조회, 소수 관계 | 독립적, 다수 관계 |

#### 설계 원칙

```
1. 함께 쓰이는 데이터는 함께 저장 (Data That Is Accessed Together Should Be Stored Together)

2. 읽기 패턴에 맞게 설계 (쓰기 < 읽기가 일반적)

3. 16MB 문서 크기 제한 주의

4. 배열이 무한정 커지지 않도록 주의 (Unbounded Arrays 피하기)

5. 중복은 허용하되 일관성 관리 방안 마련
```

### 6. Replica Set (복제 셋)

**고가용성**을 위해 데이터를 여러 노드에 복제한다.

```mermaid
flowchart TB
    Client["Client"] --> Primary

    subgraph RS["Replica Set"]
        Primary["Primary<br/>(읽기/쓰기)"]
        Secondary1["Secondary 1<br/>(읽기)"]
        Secondary2["Secondary 2<br/>(읽기)"]

        Primary -- "복제" --> Secondary1
        Primary -- "복제" --> Secondary2
    end

    Secondary1 -. "Primary 장애 시<br/>자동 승격" .-> Primary

    style Primary fill:#2d5016,stroke:#4a7c23,color:#e2e8f0
    style Secondary1 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style Secondary2 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style Client fill:#1a365d,stroke:#2a4a7f,color:#e2e8f0
```

Primary가 장애를 일으키면 나머지 Secondary 노드들이 투표를 통해 새 Primary를 선출한다. 클라이언트는 연결 문자열에 Replica Set 이름을 지정하면 자동으로 새 Primary에 연결된다.

### 7. 샤딩 (Sharding)

대용량 데이터를 **여러 서버에 분산** 저장한다.

```mermaid
flowchart TB
    Client["Client"] --> Mongos["mongos<br/>(라우터)"]

    Mongos --> Config["Config Server<br/>(메타데이터)"]

    Mongos --> Shard1["Shard 1<br/>A ~ F"]
    Mongos --> Shard2["Shard 2<br/>G ~ N"]
    Mongos --> Shard3["Shard 3<br/>O ~ Z"]

    style Client fill:#1a365d,stroke:#2a4a7f,color:#e2e8f0
    style Mongos fill:#553c9a,stroke:#6b46c1,color:#e2e8f0
    style Config fill:#744210,stroke:#975a16,color:#e2e8f0
    style Shard1 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style Shard2 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style Shard3 fill:#2d3748,stroke:#4a5568,color:#e2e8f0
```

```javascript
// 샤드 키 선택 (매우 중요!)
sh.shardCollection("mydb.orders", { userId: "hashed" });  // 해시 기반 (균등 분배)
sh.shardCollection("mydb.logs", { timestamp: 1 });         // 범위 기반 (시계열 데이터)
```

| 샤드 키 전략 | 장점 | 단점 | 적합한 경우 |
|------------|------|------|-----------|
| 해시 기반 | 균등 분배 | 범위 쿼리 느림 | 랜덤 접근 |
| 범위 기반 | 범위 쿼리 빠름 | 핫스팟 가능 | 시계열, 순차 데이터 |

### 8. 멀티 문서 트랜잭션

MongoDB 4.0부터 Replica Set, 4.2부터 샤딩 환경에서 멀티 문서 ACID 트랜잭션을 지원한다.

단일 문서 쓰기는 원래부터 원자적이다. 멀티 문서 트랜잭션은 **여러 컬렉션에 걸친 쓰기가 모두 성공하거나 모두 실패해야 하는 경우**에만 쓴다. 트랜잭션은 잠금 비용이 있어서 남발하면 성능이 떨어진다.

#### mongo shell에서 트랜잭션

```javascript
const session = db.getMongo().startSession();
session.startTransaction({
    readConcern: { level: "snapshot" },
    writeConcern: { w: "majority" }
});

try {
    const accounts = session.getDatabase("bank").accounts;

    // 출금
    accounts.updateOne(
        { _id: "account_A", balance: { $gte: 100000 } },
        { $inc: { balance: -100000 } },
        { session }
    );

    // 입금
    accounts.updateOne(
        { _id: "account_B" },
        { $inc: { balance: 100000 } },
        { session }
    );

    // 이체 내역 기록
    session.getDatabase("bank").transfers.insertOne({
        from: "account_A",
        to: "account_B",
        amount: 100000,
        timestamp: new Date()
    }, { session });

    session.commitTransaction();
} catch (error) {
    session.abortTransaction();
    throw error;
} finally {
    session.endSession();
}
```

#### Spring Data MongoDB 트랜잭션

```java
@Configuration
public class MongoConfig {

    @Bean
    MongoTransactionManager transactionManager(MongoDatabaseFactory dbFactory) {
        return new MongoTransactionManager(dbFactory);
    }
}

@Service
@RequiredArgsConstructor
public class TransferService {

    private final MongoTemplate mongoTemplate;

    @Transactional
    public void transfer(String fromId, String toId, long amount) {
        // 출금 계좌 잔액 확인 후 차감
        UpdateResult debit = mongoTemplate.updateFirst(
            Query.query(Criteria.where("_id").is(fromId)
                                .and("balance").gte(amount)),
            new Update().inc("balance", -amount),
            Account.class
        );
        if (debit.getModifiedCount() == 0) {
            throw new InsufficientBalanceException(fromId);
        }

        // 입금
        mongoTemplate.updateFirst(
            Query.query(Criteria.where("_id").is(toId)),
            new Update().inc("balance", amount),
            Account.class
        );

        // 이체 내역
        mongoTemplate.insert(new Transfer(fromId, toId, amount, Instant.now()));
    }
}
```

트랜잭션 사용 시 주의할 점:

- 기본 타임아웃은 60초. 이 시간 안에 커밋되지 않으면 자동 abort된다.
- 트랜잭션 내에서 DDL(컬렉션 생성, 인덱스 생성)은 불가하다.
- 트랜잭션은 Replica Set 환경에서만 동작한다. standalone에서는 안 된다.
- `readConcern: "snapshot"`을 쓰면 트랜잭션 시작 시점의 일관된 스냅샷을 읽는다.

### 9. Change Streams

컬렉션, 데이터베이스, 전체 배포 단위에서 **실시간 변경 이벤트를 구독**한다. Replica Set의 oplog를 기반으로 동작하며, 폴링 없이 변경 사항을 받을 수 있다.

```mermaid
flowchart LR
    App["애플리케이션"] -- "watch()" --> CS["Change Stream"]
    CS -- "oplog tail" --> Oplog["Replica Set oplog"]

    CS -- "insert/update/delete 이벤트" --> Handler["이벤트 핸들러"]

    style App fill:#1a365d,stroke:#2a4a7f,color:#e2e8f0
    style CS fill:#553c9a,stroke:#6b46c1,color:#e2e8f0
    style Oplog fill:#2d3748,stroke:#4a5568,color:#e2e8f0
    style Handler fill:#2d5016,stroke:#4a7c23,color:#e2e8f0
```

#### mongo shell

```javascript
// 컬렉션 단위 감시
const changeStream = db.orders.watch([
    { $match: { "fullDocument.status": "cancelled" } }
]);

changeStream.on("change", (event) => {
    print("변경 타입:", event.operationType);
    print("문서:", JSON.stringify(event.fullDocument));
    print("resume token:", event._id);
});
```

변경 이벤트 구조:

```javascript
{
    _id: { ... },                    // resume token (재시작 지점)
    operationType: "update",         // insert, update, replace, delete, drop, ...
    fullDocument: { ... },           // 변경 후 전체 문서 (옵션)
    ns: { db: "mydb", coll: "orders" },
    updateDescription: {             // update일 때만
        updatedFields: { status: "shipped" },
        removedFields: []
    },
    clusterTime: Timestamp(...)
}
```

#### Spring Data MongoDB

```java
@Component
@RequiredArgsConstructor
public class OrderChangeListener {

    private final MongoTemplate mongoTemplate;

    @PostConstruct
    public void watchOrders() {
        // fullDocument: "updateLookup" → update 이벤트에 변경 후 전체 문서 포함
        ChangeStreamOptions options = ChangeStreamOptions.builder()
            .filter(Aggregation.newAggregation(
                Aggregation.match(Criteria.where("operationType").in("insert", "update"))
            ))
            .fullDocumentLookup(FullDocument.UPDATE_LOOKUP)
            .build();

        Flux<ChangeStreamEvent<Order>> flux = mongoTemplate
            .changeStream("orders", options, Order.class);

        flux.subscribe(event -> {
            Order order = event.getBody();
            // 주문 상태 변경 알림, 캐시 갱신, 외부 시스템 연동 등
            log.info("Order changed: id={}, status={}", order.getId(), order.getStatus());
        });
    }
}
```

resume token을 저장해두면, 애플리케이션 재시작 후에도 마지막으로 처리한 이벤트 이후부터 이어서 받을 수 있다. 프로덕션에서는 반드시 resume token을 별도 컬렉션에 저장해야 한다.

### 10. 성능 프로파일링

#### explain() 분석

쿼리가 인덱스를 타는지, 얼마나 많은 문서를 스캔하는지 확인하는 데 `explain()`을 쓴다.

```javascript
db.orders.find({ userId: "user_123", status: "completed" })
    .sort({ createdAt: -1 })
    .explain("executionStats");
```

결과에서 확인할 항목:

```javascript
{
    "executionStats": {
        "executionTimeMillis": 23,           // 실행 시간 (ms)
        "totalDocsExamined": 15000,          // 스캔한 문서 수
        "totalKeysExamined": 150,            // 스캔한 인덱스 키 수
        "nReturned": 150,                    // 반환한 문서 수
    },
    "queryPlanner": {
        "winningPlan": {
            "stage": "FETCH",
            "inputStage": {
                "stage": "IXSCAN",           // 인덱스 스캔 (좋음)
                "indexName": "userId_1_createdAt_-1"
            }
        }
    }
}
```

**핵심 지표**: `totalDocsExamined`와 `nReturned`의 비율을 본다. 이 비율이 크면 불필요한 문서를 많이 스캔하고 있다는 뜻이다.

| stage | 의미 | 대응 |
|-------|------|------|
| `COLLSCAN` | 컬렉션 풀스캔 | 인덱스가 없거나 못 타고 있음. 인덱스 추가 필요 |
| `IXSCAN` | 인덱스 스캔 | 정상 |
| `SORT` | 메모리 정렬 | 인덱스에 정렬 필드를 포함시키면 제거 가능 |
| `SORT_KEY_GENERATOR` | 정렬 키 생성 | `SORT`와 같은 맥락 |
| `FETCH` | 문서 가져오기 | `IXSCAN` 이후 정상적인 단계 |

#### Slow Query 로그

MongoDB는 기본적으로 100ms 이상 걸리는 쿼리를 로그에 남긴다. 프로파일러를 켜면 `system.profile` 컬렉션에 저장된다.

```javascript
// 프로파일러 레벨 설정
// 0: 끔, 1: 느린 쿼리만, 2: 모든 쿼리
db.setProfilingLevel(1, { slowms: 50 });   // 50ms 이상인 쿼리만 기록

// 현재 프로파일러 상태 확인
db.getProfilingStatus();

// 느린 쿼리 조회
db.system.profile.find({ millis: { $gt: 100 } })
    .sort({ ts: -1 })
    .limit(10);
```

`system.profile`에 기록되는 내용:

```javascript
{
    "op": "query",
    "ns": "mydb.orders",
    "command": {
        "find": "orders",
        "filter": { "userId": "user_123" },
        "sort": { "createdAt": -1 }
    },
    "keysExamined": 0,
    "docsExamined": 150000,            // 인덱스 없이 15만 건 풀스캔
    "nreturned": 50,
    "millis": 340,                     // 340ms 소요
    "planSummary": "COLLSCAN",         // 풀스캔
    "ts": ISODate("2026-04-12T10:30:00Z")
}
```

프로파일러는 쓰기 부하가 있다. 프로덕션에서는 레벨 1(느린 쿼리만)로 설정하고, `slowms` 값을 적절히 조정한다. 레벨 2는 개발/테스트 환경에서만 쓴다.

#### currentOp으로 실행 중인 쿼리 확인

```javascript
// 5초 이상 실행 중인 쿼리 찾기
db.currentOp({
    "active": true,
    "secs_running": { $gte: 5 },
    "op": { $ne: "none" }
});

// 특정 쿼리 강제 종료
db.killOp(opId);
```

### 11. 보안

#### 인증 (Authentication)

MongoDB는 기본적으로 인증 없이 시작된다. 프로덕션에서는 반드시 인증을 켜야 한다.

```yaml
# mongod.conf
security:
  authorization: enabled
```

```javascript
// 관리자 계정 생성
use admin
db.createUser({
    user: "adminUser",
    pwd: "securePassword123!",
    roles: [{ role: "userAdminAnyDatabase", db: "admin" }]
});

// 애플리케이션 계정 (특정 DB에만 접근)
use mydb
db.createUser({
    user: "appUser",
    pwd: "appPass456!",
    roles: [
        { role: "readWrite", db: "mydb" }
    ]
});
```

#### 인가 (Authorization) — 역할 기반 접근 제어

| 역할 | 권한 |
|------|------|
| `read` | 읽기만 |
| `readWrite` | 읽기/쓰기 |
| `dbAdmin` | 인덱스, 통계 등 DB 관리 |
| `userAdmin` | 사용자/역할 관리 |
| `clusterAdmin` | Replica Set, 샤딩 관리 |
| `root` | 전체 권한 (프로덕션에서 사용 자제) |

커스텀 역할도 만들 수 있다:

```javascript
db.createRole({
    role: "orderReadOnly",
    privileges: [{
        resource: { db: "mydb", collection: "orders" },
        actions: ["find", "aggregate"]
    }],
    roles: []
});
```

#### TLS/SSL 설정

클라이언트-서버 간 통신을 암호화한다.

```yaml
# mongod.conf
net:
  tls:
    mode: requireTLS
    certificateKeyFile: /etc/ssl/mongodb.pem
    CAFile: /etc/ssl/ca.pem
```

```bash
# TLS로 접속
mongosh --tls \
    --tlsCertificateKeyFile /etc/ssl/client.pem \
    --tlsCAFile /etc/ssl/ca.pem \
    --host mongodb.example.com
```

Spring Boot 연결 문자열:

```properties
spring.data.mongodb.uri=mongodb://appUser:appPass456!@mongodb.example.com:27017/mydb\
  ?tls=true\
  &tlsCertificateKeyFile=/etc/ssl/client.pem\
  &tlsCAFile=/etc/ssl/ca.pem
```

#### 네트워크 접근 제한

```yaml
# mongod.conf — 특정 IP만 바인딩
net:
  bindIp: 127.0.0.1,10.0.1.100
  port: 27017
```

프로덕션 환경에서 `bindIp: 0.0.0.0`은 절대 쓰면 안 된다. 외부 네트워크에서 직접 접근할 수 없도록 VPC 내부에서만 바인딩하고, 방화벽으로 27017 포트를 제한해야 한다.

### 12. 백업과 복구

#### mongodump / mongorestore

논리적 백업 도구. BSON 형태로 덤프하고 복원한다.

```bash
# 전체 데이터베이스 백업
mongodump --uri="mongodb://user:pass@host:27017" \
    --db=mydb \
    --out=/backup/2026-04-12 \
    --gzip

# 특정 컬렉션만 백업
mongodump --uri="mongodb://user:pass@host:27017" \
    --db=mydb \
    --collection=orders \
    --out=/backup/orders \
    --gzip

# 복원
mongorestore --uri="mongodb://user:pass@host:27017" \
    --db=mydb \
    --gzip \
    /backup/2026-04-12/mydb

# 특정 컬렉션 복원 (기존 데이터 유지하면서)
mongorestore --uri="mongodb://user:pass@host:27017" \
    --db=mydb \
    --collection=orders \
    --gzip \
    /backup/orders/mydb/orders.bson.gz

# 기존 컬렉션을 지우고 복원
mongorestore --drop \
    --uri="mongodb://user:pass@host:27017" \
    --db=mydb \
    --gzip \
    /backup/2026-04-12/mydb
```

`mongodump`는 실행 시점의 스냅샷이 아니라, 덤프하는 동안 데이터가 변경될 수 있다. Replica Set에서는 Secondary에서 `--oplog` 옵션으로 일관된 백업을 받을 수 있다.

```bash
# oplog 포함 백업 (point-in-time 복원 가능)
mongodump --uri="mongodb://user:pass@host:27017" \
    --oplog \
    --out=/backup/2026-04-12 \
    --gzip

# oplog 포함 복원
mongorestore --oplogReplay \
    --gzip \
    /backup/2026-04-12
```

#### 대용량 데이터 백업

수십 GB 이상이면 `mongodump`는 느리다. 이 경우 파일시스템 스냅샷(LVM, EBS Snapshot 등)이나 MongoDB Atlas의 자동 백업을 쓰는 게 낫다.

| 방법 | 데이터 크기 | 일관성 | 속도 |
|------|-----------|--------|------|
| `mongodump` | 수 GB 이하 | `--oplog`으로 보장 | 느림 |
| 파일시스템 스냅샷 | 수십 GB 이상 | journaling 켜져있으면 보장 | 빠름 |
| Atlas 자동 백업 | 제한 없음 | point-in-time 복원 | 관리형 |

### 13. 모니터링

#### mongostat

실시간으로 MongoDB 인스턴스의 상태를 보여준다. `vmstat`이나 `iostat`과 비슷하다.

```bash
# 1초 간격으로 상태 출력
mongostat --uri="mongodb://user:pass@host:27017" --rowcount=0

# 주요 출력 항목
# insert  query  update  delete  getmore  command  dirty  used  flushes
#    *0     12      *0      *0        0      3|0   0.1%  45.2%        0
#    *0    156      23      *0        5     12|0   0.3%  47.8%        1
```

| 항목 | 의미 | 주의 기준 |
|------|------|----------|
| `insert/query/update/delete` | 초당 연산 수 | 갑자기 급증하면 확인 필요 |
| `dirty` | WiredTiger 캐시 중 변경된 비율 | 20% 이상이면 쓰기 부하 심함 |
| `used` | WiredTiger 캐시 사용률 | 80% 이상이면 메모리 부족 |
| `qrw` / `arw` | 큐에 대기 중인 읽기/쓰기 | 0이 아니면 병목 |
| `conn` | 현재 연결 수 | 커넥션 풀 설정과 비교 |

#### mongotop

컬렉션별 읽기/쓰기 시간 비중을 보여준다.

```bash
# 5초 간격으로 컬렉션별 사용 시간 출력
mongotop 5 --uri="mongodb://user:pass@host:27017"

#                    ns    total    read    write
# mydb.orders        45ms   40ms     5ms
# mydb.users         12ms   10ms     2ms
# mydb.sessions       3ms    1ms     2ms
```

특정 컬렉션에 읽기/쓰기가 집중되면 인덱스 최적화나 샤딩을 검토한다.

#### db.serverStatus()

메모리, 연결, 잠금, 캐시 등 전반적인 서버 상태를 확인한다.

```javascript
// 커넥션 상태
db.serverStatus().connections
// { current: 45, available: 51155, totalCreated: 1230 }

// WiredTiger 캐시 상태
db.serverStatus().wiredTiger.cache
// "bytes currently in the cache": 2147483648
// "maximum bytes configured": 4294967296

// 잠금 상태
db.serverStatus().globalLock
// { currentQueue: { total: 0, readers: 0, writers: 0 } }
```

### 14. 커넥션 풀 설정

MongoDB 드라이버는 커넥션 풀을 관리한다. 커넥션을 매번 새로 만들면 TCP 핸드셰이크 + 인증 비용이 든다.

#### 연결 문자열 옵션

```
mongodb://user:pass@host1:27017,host2:27017/mydb
    ?replicaSet=rs0
    &maxPoolSize=100          # 최대 커넥션 수 (기본 100)
    &minPoolSize=10           # 최소 유지 커넥션 수 (기본 0)
    &maxIdleTimeMS=60000      # 유휴 커넥션 제거 시간 (기본: 없음)
    &waitQueueTimeoutMS=5000  # 커넥션 대기 타임아웃 (기본: 120초)
    &connectTimeoutMS=10000   # 연결 타임아웃
    &socketTimeoutMS=0        # 소켓 타임아웃 (0 = 무제한)
```

#### Spring Boot 설정

```yaml
# application.yml
spring:
  data:
    mongodb:
      uri: mongodb://user:pass@host1:27017,host2:27017/mydb?replicaSet=rs0
      # 또는 개별 설정
      host: host1
      port: 27017
      database: mydb
      auto-index-creation: false   # 프로덕션에서는 false 권장

# MongoClient 직접 설정이 필요한 경우
mongock:
  migration-scan-package: com.example.migration
```

```java
@Configuration
public class MongoConfig {

    @Bean
    public MongoClientSettings mongoClientSettings() {
        return MongoClientSettings.builder()
            .applyConnectionString(
                new ConnectionString("mongodb://host1:27017,host2:27017/mydb?replicaSet=rs0"))
            .applyToConnectionPoolSettings(pool -> pool
                .maxSize(100)
                .minSize(10)
                .maxWaitTime(5, TimeUnit.SECONDS)
                .maxConnectionIdleTime(60, TimeUnit.SECONDS)
            )
            .applyToSocketSettings(socket -> socket
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
            )
            .readPreference(ReadPreference.secondaryPreferred())   // 읽기는 Secondary 우선
            .writeConcern(WriteConcern.MAJORITY)                   // 과반수 노드에 쓰기 확인
            .build();
    }
}
```

커넥션 풀 설정에서 자주 실수하는 부분:

- `maxPoolSize`를 너무 크게 잡으면 MongoDB 서버의 `maxIncomingConnections`(기본 65536)를 넘길 수 있다. 애플리케이션 인스턴스 수 x `maxPoolSize`가 서버 한도를 넘지 않는지 확인해야 한다.
- `minPoolSize`를 0으로 두면 트래픽이 없는 동안 커넥션이 모두 정리되고, 갑자기 트래픽이 들어오면 커넥션 생성 지연이 발생한다.
- `waitQueueTimeoutMS`가 너무 길면 커넥션 부족 상황에서 요청이 계속 쌓인다. 적절한 값으로 설정하고 타임아웃 발생 시 빠르게 실패하도록 한다.

### 15. Spring Data MongoDB

```java
@Document(collection = "users")
public class User {
    @Id
    private String id;

    @Indexed(unique = true)
    private String email;

    private String name;
    private int age;

    @Field("addr")
    private Address address;        // 내장 문서

    private List<String> tags;

    @CreatedDate
    private LocalDateTime createdAt;
}

// Repository
public interface UserRepository extends MongoRepository<User, String> {

    Optional<User> findByEmail(String email);

    List<User> findByAgeBetween(int min, int max);

    @Query("{ 'address.city': ?0, age: { $gte: ?1 } }")
    List<User> findByCityAndMinAge(String city, int minAge);

    @Aggregation(pipeline = {
        "{ $group: { _id: '$address.city', count: { $sum: 1 } } }",
        "{ $sort: { count: -1 } }"
    })
    List<CityCount> countByCity();
}

// MongoTemplate (복잡한 쿼리)
@Service
public class UserService {

    private final MongoTemplate mongoTemplate;

    public List<User> searchUsers(UserSearchCriteria criteria) {
        Query query = new Query();

        if (criteria.getName() != null) {
            query.addCriteria(Criteria.where("name").regex(criteria.getName(), "i"));
        }
        if (criteria.getMinAge() != null) {
            query.addCriteria(Criteria.where("age").gte(criteria.getMinAge()));
        }

        query.with(Sort.by(Sort.Direction.DESC, "createdAt"));
        query.with(PageRequest.of(criteria.getPage(), criteria.getSize()));

        return mongoTemplate.find(query, User.class);
    }
}
```

## RDBMS vs MongoDB 비교

| 항목 | RDBMS (PostgreSQL) | MongoDB |
|------|-------------------|---------|
| **스키마** | 고정 (ALTER TABLE) | 유연 (스키마리스) |
| **조인** | SQL JOIN | $lookup (비효율적) |
| **트랜잭션** | 강력 (ACID) | 4.0+ 멀티문서 ACID |
| **스케일링** | 수직 확장 주로 | **수평 확장 (샤딩)** |
| **데이터 모델** | 정규화된 테이블 | 비정규화된 문서 |
| **적합한 경우** | 복잡한 관계, 정합성 | 유연한 스키마, 대용량 |

## 참고

- [MongoDB Documentation](https://www.mongodb.com/docs/)
- [MongoDB University](https://university.mongodb.com/)
- [NoSQL 개요](NoSQL.md) — NoSQL 데이터베이스 분류
- [Redis](Redis/Redis 다루기.md) — Key-Value 스토어
- [데이터베이스 샤딩](../RDBMS/데이터베이스_샤딩.md) — 샤딩 전략 비교
