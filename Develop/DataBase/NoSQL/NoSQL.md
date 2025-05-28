# NoSQL (Not Only SQL)

## 1. NoSQL의 정의와 배경
- "Not Only SQL" 또는 "Non-Relational Database"로 불리는 NoSQL은 기존 관계형 데이터베이스(RDBMS)의 한계를 극복하기 위해 등장한 데이터베이스 시스템입니다.
- 대용량 데이터 처리, 분산 시스템, 실시간 웹 애플리케이션의 등장으로 인해 기존 RDBMS의 확장성과 성능 한계가 드러나면서 NoSQL이 주목받게 되었습니다.
- 특히 빅데이터, 소셜 미디어, IoT, 실시간 분석 등에서 NoSQL이 효과적으로 활용되고 있습니다.

### 1.1 NoSQL 등장 배경
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

### 1.2 NoSQL의 발전 과정
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

## 2. NoSQL의 주요 특징

### 2.1 스키마리스(Schema-less) 구조
- RDBMS와 달리 고정된 스키마가 없어 데이터 구조를 유연하게 변경할 수 있습니다.
- 예시: MongoDB에서의 문서 구조
```json
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

#### 2.1.1 스키마리스의 장점
1. **유연한 데이터 모델링**
   - 새로운 필드 추가가 자유로움
   - 중첩된 구조 지원
   - 다양한 데이터 타입 수용

2. **개발 생산성 향상**
   - 스키마 마이그레이션 불필요
   - 빠른 프로토타이핑 가능
   - 유지보수 용이성

3. **데이터 모델 진화**
   - 비즈니스 요구사항 변화에 대응 용이
   - 점진적인 기능 확장 가능
   - 실험적 기능 구현 용이

### 2.2 수평적 확장성(Horizontal Scalability)
- 샤딩(Sharding)을 통해 데이터를 여러 서버에 분산 저장
- 예시: MongoDB의 샤딩 구조
  - 데이터를 여러 샤드로 분할
  - 각 샤드는 독립적인 서버에서 실행
  - 샤드 키를 기준으로 데이터 분배

#### 2.2.1 샤딩 전략
1. **해시 기반 샤딩**
```javascript
// MongoDB 해시 샤딩 예시
sh.shardCollection("mydb.users", { "user_id": "hashed" })
```

2. **범위 기반 샤딩**
```javascript
// MongoDB 범위 샤딩 예시
sh.shardCollection("mydb.orders", { "order_date": 1 })
```

3. **지역 기반 샤딩**
```javascript
// MongoDB 지역 샤딩 예시
sh.shardCollection("mydb.customers", { "region": 1, "customer_id": 1 })
```

#### 2.2.2 샤딩 고려사항
1. **샤드 키 선택**
   - 데이터 분포 고려
   - 쿼리 패턴 분석
   - 확장성 요구사항

2. **샤드 밸런싱**
   - 자동 밸런싱 설정
   - 수동 밸런싱 전략
   - 밸런싱 임계값 조정

3. **장애 대응**
   - 샤드 서버 장애 처리
   - 데이터 재분배
   - 복구 전략

### 2.3 고가용성(High Availability)
- 복제(Replication)를 통한 데이터 중복 저장
- 마스터-슬레이브 구조 또는 피어-투-피어 구조 사용
- 장애 발생 시 자동 페일오버(Failover) 지원

#### 2.3.1 복제 구성
1. **MongoDB 복제셋 예시**
```javascript
// 복제셋 초기화
rs.initiate({
  _id: "myReplicaSet",
  members: [
    { _id: 0, host: "server1:27017" },
    { _id: 1, host: "server2:27017" },
    { _id: 2, host: "server3:27017" }
  ]
})
```

2. **Redis 센티널 구성**
```conf
# sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
```

#### 2.3.2 고가용성 전략
1. **자동 페일오버**
   - 마스터 노드 장애 감지
   - 새로운 마스터 선출
   - 클라이언트 리다이렉션

2. **데이터 동기화**
   - 실시간 복제
   - 지연 시간 모니터링
   - 동기화 상태 확인

3. **백업 전략**
   - 스냅샷 백업
   - 증분 백업
   - 지리적 분산 백업

### 2.4 다양한 데이터 모델
1. **문서형(Document)**
   - MongoDB, CouchDB
   - JSON/BSON 형식의 문서 저장
   - 복잡한 계층 구조 데이터 처리에 적합

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

2. **키-값(Key-Value)**
   - Redis, DynamoDB
   - 단순한 데이터 구조
   - 캐싱, 세션 관리에 최적화

   ```python
   # Redis 키-값 예시
   redis.set("user:123:session", "session_token_xyz", ex=3600)
   redis.hset("user:123:profile", mapping={
       "name": "John Doe",
       "email": "john@example.com",
       "last_login": "2024-03-15"
   })
   ```

3. **컬럼 패밀리(Column Family)**
   - Cassandra, HBase
   - 대용량 데이터 처리에 특화
   - 시계열 데이터 처리에 적합

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

4. **그래프(Graph)**
   - Neo4j, ArangoDB
   - 관계 중심 데이터 모델
   - 소셜 네트워크, 추천 시스템에 적합

   ```cypher
   // Neo4j 그래프 쿼리 예시
   CREATE (john:Person {name: 'John'})
   CREATE (mary:Person {name: 'Mary'})
   CREATE (john)-[:FRIENDS_WITH]->(mary)
   CREATE (john)-[:WORKS_AT]->(company:Company {name: 'Tech Corp'})
   ```

## 3. NoSQL의 장단점

### 3.1 장점
1. **확장성**
   - 수평적 확장이 용이
   - 클라우드 환경에 최적화
   - 대용량 데이터 처리 가능

2. **성능**
   - 단순한 쿼리 구조로 빠른 응답 시간
   - 메모리 기반 연산 가능
   - 분산 처리로 높은 처리량

3. **유연성**
   - 스키마 변경이 자유로움
   - 다양한 데이터 타입 지원
   - 개발 속도 향상

4. **비용 효율성**
   - 오픈소스 솔루션 다수
   - 상용 하드웨어 사용 가능
   - 관리 비용 절감

### 3.2 단점
1. **데이터 일관성**
   - ACID 트랜잭션 보장 어려움
   - 최종적 일관성(Eventual Consistency) 모델
   - 데이터 정합성 관리 필요

2. **쿼리 기능**
   - 복잡한 조인 연산 제한
   - SQL과 같은 표준화된 쿼리 언어 부재
   - 특정 NoSQL에 맞는 쿼리 언어 학습 필요

3. **운영 관리**
   - 분산 시스템 관리 복잡성
   - 백업/복구 전략 필요
   - 모니터링 도구 구축 필요

## 4. NoSQL 사용 사례

### 4.1 적합한 사용 사례
1. **소셜 미디어 플랫폼**
   - 사용자 프로필, 관계 데이터
   - 실시간 피드 처리
   - 대규모 사용자 기반 관리

   ```javascript
   // 소셜 미디어 피드 처리 예시 (MongoDB)
   db.posts.find({
     author_id: "user123",
     created_at: { $gte: new Date(Date.now() - 24*60*60*1000) }
   }).sort({ created_at: -1 }).limit(20)
   ```

2. **IoT 애플리케이션**
   - 센서 데이터 수집
   - 시계열 데이터 처리
   - 실시간 분석

   ```sql
   -- IoT 데이터 저장 예시 (Cassandra)
   INSERT INTO sensor_readings (
       sensor_id, timestamp, temperature, humidity
   ) VALUES (
       'sensor001', '2024-03-15 10:00:00', 25.5, 60.0
   );
   ```

3. **컨텐츠 관리 시스템**
   - 다양한 형식의 컨텐츠 저장
   - 메타데이터 관리
   - 검색 기능 구현

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

### 4.2 부적합한 사용 사례
1. **금융 트랜잭션**
   - 높은 데이터 일관성 요구
   - 복잡한 트랜잭션 처리
   - 감사 추적 필요

2. **전통적 ERP 시스템**
   - 복잡한 관계형 데이터
   - 정형화된 비즈니스 로직
   - 보고서 생성 기능

## 5. 주요 NoSQL 데이터베이스 비교

| 데이터베이스 | 타입 | 주요 특징 | 사용 사례 | 장점 | 단점 |
|------------|------|----------|-----------|------|------|
| MongoDB | 문서형 | JSON 문서, 인덱싱, 집계 | 컨텐츠 관리, 사용자 데이터 | 유연한 스키마, 강력한 쿼리 | 메모리 사용량 높음 |
| Redis | 키-값 | 인메모리, Pub/Sub | 캐싱, 세션 관리 | 빠른 성능, 다양한 데이터 타입 | 메모리 제한 |
| Cassandra | 컬럼 패밀리 | 분산, 고가용성 | 시계열 데이터, 로그 | 선형 확장성, 고가용성 | 복잡한 쿼리 제한 |
| Neo4j | 그래프 | 관계 쿼리, ACID | 소셜 네트워크, 추천 | 관계 처리 최적화 | 대용량 데이터 처리 제한 |

### 5.1 성능 비교
1. **읽기 성능**
   - Redis > MongoDB > Cassandra > Neo4j
   - 인메모리 처리 vs 디스크 기반 처리
   - 캐싱 전략의 영향

2. **쓰기 성능**
   - Cassandra > MongoDB > Redis > Neo4j
   - 분산 쓰기 처리
   - 일관성 수준의 영향

3. **확장성**
   - Cassandra > MongoDB > Redis > Neo4j
   - 수평적 확장 용이성
   - 분산 시스템 복잡성

## 6. NoSQL 선택 가이드

### 6.1 선택 기준
1. **데이터 모델**
   - 데이터 구조의 복잡성
   - 관계의 중요성
   - 스키마 변경 빈도

2. **확장성 요구사항**
   - 예상 데이터 양
   - 읽기/쓰기 비율
   - 지리적 분산 필요성

3. **일관성 요구사항**
   - 데이터 정확성 중요도
   - 실시간 업데이트 필요성
   - 트랜잭션 지원 필요성

### 6.2 마이그레이션 고려사항
1. **데이터 전환**
   - 데이터 변환 전략
   - 마이그레이션 도구
   - 다운타임 관리

2. **애플리케이션 변경**
   - 코드 리팩토링
   - 새로운 쿼리 패턴 학습
   - 테스트 전략

3. **운영 관리**
   - 모니터링 설정
   - 백업/복구 전략
   - 성능 튜닝

## 7. 결론
- NoSQL은 특정 사용 사례에 최적화된 다양한 데이터베이스 솔루션을 제공합니다.
- 프로젝트의 요구사항을 정확히 분석하여 적절한 NoSQL 솔루션을 선택하는 것이 중요합니다.
- 하이브리드 접근 방식(RDBMS + NoSQL)도 고려할 수 있습니다.

## 8. 참고 자료
- https://www.mongodb.com/nosql-explained
- https://www.couchbase.com/resources/why-nosql
- https://neo4j.com/developer/graph-database-vs-rdbms/
- https://www.datastax.com/nosql-databases
- https://redis.io/documentation
- https://cassandra.apache.org/doc/latest/
