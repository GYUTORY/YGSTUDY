---
title: NoSQL (Not Only SQL) 완벽 가이드
tags: [database, nosql, mongodb, redis, cassandra, neo4j, document-database, key-value, graph-database]
updated: 2024-12-19
---

# NoSQL (Not Only SQL) 완벽 가이드

## 배경

### NoSQL이란?
NoSQL은 "Not Only SQL" 또는 "Non-Relational Database"로 불리는 데이터베이스 시스템입니다. 기존 관계형 데이터베이스(RDBMS)의 한계를 극복하기 위해 등장했으며, 대용량 데이터 처리, 분산 시스템, 실시간 웹 애플리케이션에 특화되어 있습니다.

### NoSQL 등장 배경
1. **데이터 폭증**
   - 소셜 미디어의 급성장으로 인한 사용자 생성 데이터의 폭증
   - IoT 기기에서 생성되는 대량의 센서 데이터
   - 로그 데이터, 이벤트 데이터의 기하급수적 증가

2. **RDBMS의 한계**
   - 수직적 확장(Scale-up)의 한계
   - 스키마 변경의 어려움
   - 복잡한 조인 연산의 성능 저하
   - 높은 라이선스 비용

3. **클라우드 컴퓨팅의 발전**
   - 분산 시스템의 필요성 증가
   - 탄력적인 리소스 확장 요구
   - 비용 효율적인 인프라 구축 필요

### NoSQL의 발전 과정
1. **초기 단계 (2000년대 초)**
   - Google의 BigTable, Amazon의 Dynamo 논문 발표
   - 분산 시스템의 기반 이론 확립

2. **성장 단계 (2000년대 중반)**
   - MongoDB, Cassandra 등 주요 NoSQL DB 출시
   - 웹 스케일 애플리케이션의 등장

3. **성숙 단계 (2010년대 이후)**
   - 엔터프라이즈급 기능 추가
   - 하이브리드 데이터베이스 시스템 등장
   - 클라우드 네이티브 솔루션으로 발전

## 핵심

### 1. NoSQL의 주요 특징

#### 스키마리스(Schema-less) 구조
RDBMS와 달리 고정된 스키마가 없어 데이터 구조를 유연하게 변경할 수 있습니다.

```json
// MongoDB에서의 문서 구조 예시
{
    "user_id": "123",
    "name": "John Doe",
    "age": 30,
    "address": {
        "street": "123 Main St",
        "city": "New York",
        "zipcode": "10001",
        "country": "USA"
    },
    "interests": ["coding", "reading", "gaming"],
    "social_media": {
        "twitter": "@johndoe",
        "github": "johndoe",
        "linkedin": "john-doe"
    },
    "preferences": {
        "theme": "dark",
        "notifications": true,
        "language": "en"
    },
    "created_at": ISODate("2024-01-01T00:00:00Z"),
    "last_login": ISODate("2024-03-15T10:30:00Z")
}
```

#### 수평적 확장성(Horizontal Scalability)
샤딩(Sharding)을 통해 데이터를 여러 서버에 분산 저장합니다.

```javascript
// MongoDB 해시 샤딩 예시
sh.shardCollection("mydb.users", { "user_id": "hashed" })

// MongoDB 범위 샤딩 예시
sh.shardCollection("mydb.orders", { "order_date": 1 })

// MongoDB 지역 샤딩 예시
sh.shardCollection("mydb.customers", { "region": 1, "customer_id": 1 })
```

#### 고가용성(High Availability)
복제(Replication)를 통한 데이터 중복 저장과 자동 페일오버(Failover)를 지원합니다.

```javascript
// MongoDB 복제셋 예시
rs.initiate({
  _id: "myReplicaSet",
  members: [
    { _id: 0, host: "server1:27017" },
    { _id: 1, host: "server2:27017" },
    { _id: 2, host: "server3:27017" }
  ]
})
```

### 2. NoSQL 데이터 모델

#### 문서형(Document)
MongoDB, CouchDB 등이 해당하며, JSON/BSON 형식의 문서를 저장합니다.

```javascript
// MongoDB 문서 예시
db.products.insertOne({
  name: "Laptop",
  price: 999.99,
  specs: {
    cpu: "Intel i7",
    ram: "16GB",
    storage: "512GB SSD"
  },
  categories: ["Electronics", "Computers"],
  in_stock: true,
  ratings: [
    { user: "user1", score: 5, comment: "Great product!" },
    { user: "user2", score: 4, comment: "Good but expensive" }
  ]
})
```

#### 키-값(Key-Value)
Redis, DynamoDB 등이 해당하며, 단순한 데이터 구조로 캐싱, 세션 관리에 최적화되어 있습니다.

```python
# Redis 키-값 예시
redis.set("user:123:session", "session_token_xyz", ex=3600)
redis.hset("user:123:profile", mapping={
    "name": "John Doe",
    "email": "john@example.com",
    "last_login": "2024-03-15"
})
```

#### 컬럼 패밀리(Column Family)
Cassandra, HBase 등이 해당하며, 대용량 데이터 처리에 특화되어 있습니다.

```sql
-- Cassandra 테이블 생성 예시
CREATE TABLE sensor_data (
    sensor_id text,
    timestamp timestamp,
    temperature double,
    humidity double,
    pressure double,
    PRIMARY KEY (sensor_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);
```

#### 그래프(Graph)
Neo4j, ArangoDB 등이 해당하며, 관계 중심 데이터 모델로 소셜 네트워크, 추천 시스템에 적합합니다.

```cypher
// Neo4j 그래프 쿼리 예시
CREATE (john:Person {name: 'John'})
CREATE (mary:Person {name: 'Mary'})
CREATE (john)-[:FRIENDS_WITH]->(mary)
CREATE (john)-[:WORKS_AT]->(company:Company {name: 'Tech Corp'})
```

## 예시

### 1. 실제 사용 사례

#### 소셜 미디어 플랫폼
사용자 프로필, 관계 데이터, 실시간 피드 처리에 적합합니다.

```javascript
// 소셜 미디어 피드 처리 예시 (MongoDB)
db.posts.find({
  author_id: "user123",
  created_at: { $gte: new Date(Date.now() - 24*60*60*1000) }
}).sort({ created_at: -1 }).limit(20)
```

#### IoT 애플리케이션
센서 데이터 수집, 시계열 데이터 처리에 적합합니다.

```sql
-- IoT 데이터 저장 예시 (Cassandra)
INSERT INTO sensor_readings (
    sensor_id, timestamp, temperature, humidity
) VALUES (
    'sensor001', '2024-03-15 10:00:00', 25.5, 60.0
);
```

#### 컨텐츠 관리 시스템
다양한 형식의 컨텐츠 저장, 메타데이터 관리에 적합합니다.

```javascript
// 컨텐츠 저장 예시 (MongoDB)
db.articles.insertOne({
  title: "NoSQL Overview",
  content: "NoSQL databases are...",
  metadata: {
    author: "John Doe",
    category: "Technology",
    tags: ["database", "nosql", "mongodb"],
    published: true,
    publish_date: new Date()
  },
  version: 1
})
```

### 2. 부적합한 사용 사례
1. **금융 트랜잭션**: 높은 데이터 일관성 요구
2. **전통적 ERP 시스템**: 복잡한 관계형 데이터
3. **복잡한 보고서 생성**: 다중 테이블 조인 필요

## 운영 팁

### 1. NoSQL 선택 가이드

#### 데이터 모델 기준
- **문서형**: 복잡한 계층 구조, 스키마 변경이 빈번한 경우
- **키-값**: 단순한 데이터 구조, 빠른 읽기/쓰기가 필요한 경우
- **컬럼 패밀리**: 대용량 데이터, 시계열 데이터 처리
- **그래프**: 복잡한 관계 분석, 추천 시스템

#### 확장성 요구사항
- **수평적 확장**: MongoDB, Cassandra
- **수직적 확장**: Redis, Neo4j
- **지리적 분산**: DynamoDB, Cassandra

#### 일관성 요구사항
- **강한 일관성**: MongoDB (단일 문서), Neo4j
- **최종적 일관성**: Cassandra, DynamoDB
- **세션 일관성**: MongoDB (복제셋)

### 2. 성능 최적화

#### 인덱싱 전략
```javascript
// MongoDB 인덱스 생성
db.users.createIndex({ "email": 1 }, { unique: true })
db.orders.createIndex({ "customer_id": 1, "order_date": -1 })
db.products.createIndex({ "category": 1, "price": 1 })
```

#### 쿼리 최적화
```javascript
// MongoDB 집계 파이프라인
db.orders.aggregate([
  { $match: { status: "completed" } },
  { $group: { _id: "$customer_id", total: { $sum: "$amount" } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
])
```

### 3. 모니터링 및 관리

#### 성능 모니터링
```javascript
// MongoDB 성능 통계 확인
db.stats()
db.collection.stats()
db.currentOp()
```

#### 백업 전략
```bash
# MongoDB 백업
mongodump --db mydb --out /backup/

# Redis 백업
redis-cli BGSAVE

# Cassandra 백업
nodetool snapshot mykeyspace
```

## 참고

### 주요 NoSQL 데이터베이스 비교

| 데이터베이스 | 타입 | 주요 특징 | 사용 사례 | 장점 | 단점 |
|------------|------|----------|-----------|------|------|
| **MongoDB** | 문서형 | JSON 문서, 인덱싱, 집계 | 컨텐츠 관리, 사용자 데이터 | 유연한 스키마, 강력한 쿼리 | 메모리 사용량 높음 |
| **Redis** | 키-값 | 인메모리, Pub/Sub | 캐싱, 세션 관리 | 빠른 성능, 다양한 데이터 타입 | 메모리 제한 |
| **Cassandra** | 컬럼 패밀리 | 분산, 고가용성 | 시계열 데이터, 로그 | 선형 확장성, 고가용성 | 복잡한 쿼리 제한 |
| **Neo4j** | 그래프 | 관계 쿼리, ACID | 소셜 네트워크, 추천 | 관계 처리 최적화 | 대용량 데이터 처리 제한 |

### 성능 비교

#### 읽기 성능
Redis > MongoDB > Cassandra > Neo4j

#### 쓰기 성능
Cassandra > MongoDB > Redis > Neo4j

#### 확장성
Cassandra > MongoDB > Redis > Neo4j

### NoSQL vs RDBMS

| 특징 | NoSQL | RDBMS |
|------|-------|-------|
| **스키마** | 유연함 | 고정됨 |
| **확장성** | 수평적 확장 | 수직적 확장 |
| **일관성** | 최종적 일관성 | ACID |
| **쿼리** | 특화된 언어 | SQL |
| **트랜잭션** | 제한적 | 완전 지원 |

### 결론
NoSQL은 특정 사용 사례에 최적화된 다양한 데이터베이스 솔루션을 제공합니다. 프로젝트의 요구사항을 정확히 분석하여 적절한 NoSQL 솔루션을 선택하는 것이 중요하며, 하이브리드 접근 방식(RDBMS + NoSQL)도 고려할 수 있습니다.

