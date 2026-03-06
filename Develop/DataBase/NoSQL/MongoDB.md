---
title: MongoDB 심화 가이드
tags: [database, nosql, mongodb, document-database, aggregation, index, replica-set, sharding, schema-design]
updated: 2026-03-01
---

# MongoDB 심화

## 개요

MongoDB는 **문서(Document) 기반 NoSQL 데이터베이스**이다. JSON과 유사한 BSON 형태로 데이터를 저장하며, 유연한 스키마, 수평 확장, 강력한 쿼리/집계 기능을 제공한다.

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

```
┌─────────────┐
│   Primary   │  ← 모든 쓰기 처리
│  (읽기/쓰기) │
└──────┬──────┘
       │ 복제
  ┌────┴────┐
  │         │
┌─┴───────┐ ┌─┴───────┐
│Secondary│ │Secondary│  ← 읽기 분산 가능
│ (읽기)  │ │ (읽기)  │
└─────────┘ └─────────┘

Primary 장애 시 → Secondary가 자동 승격 (Automatic Failover)
```

### 7. 샤딩 (Sharding)

대용량 데이터를 **여러 서버에 분산** 저장한다.

```
┌──────────┐
│  mongos   │  ← 라우터 (클라이언트 접점)
└────┬─────┘
     │
┌────┴──────────────────────────┐
│         Config Server          │  ← 메타데이터 (어떤 데이터가 어디 있는지)
└────────────────────────────────┘
     │
  ┌──┴──────┬──────────┐
┌─┴──────┐ ┌┴──────┐ ┌─┴──────┐
│ Shard 1│ │Shard 2│ │ Shard 3│
│ A ~ F  │ │ G ~ N │ │ O ~ Z  │  ← 데이터 분산
└────────┘ └───────┘ └────────┘
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

### 8. Spring Data MongoDB

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
