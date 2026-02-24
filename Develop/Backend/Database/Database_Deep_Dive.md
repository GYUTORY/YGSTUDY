---
title: 데이터베이스 심화 (Database Deep Dive)
tags: [backend, database, connection-pool, lock, n+1, query-optimization, partitioning, isolation-level, hikaricp, jpa]
updated: 2026-01-18
---

# 데이터베이스 심화 (Database Deep Dive)

## 개요

데이터베이스는 백엔드 애플리케이션의 핵심이다. Connection Pool 설정이 잘못되면 성능이 급격히 떨어진다. Lock을 잘못 사용하면 데드락이 발생한다. N+1 문제는 서비스 다운을 일으킨다. 이런 문제들을 해결하는 방법을 알아야 한다.

## Connection Pool

### 왜 필요한가

**문제 상황:**

DB 연결을 매번 새로 만든다.

```java
public User getUser(Long id) {
    // 매번 새 연결 생성
    Connection conn = DriverManager.getConnection(url, username, password);
    // 쿼리 실행
    // 연결 닫기
    conn.close();
}
```

**비용:**
- TCP 3-way handshake: 수 ms
- DB 인증: 수 ms
- 연결 초기화: 수 ms
- 총 10-50ms 추가 지연

초당 1,000개 요청이면 연결 생성만으로 서버 리소스 소진.

**Connection Pool:**
미리 연결을 만들어두고 재사용한다.

```java
// Pool에서 빌려옴 (0.1ms)
Connection conn = dataSource.getConnection();
// 쿼리 실행
// Pool에 반환 (닫지 않음)
conn.close();  // 실제로는 반환
```

10-50ms → 0.1ms. **100-500배 빠름.**

### HikariCP 기본 설정

Spring Boot 기본 Connection Pool.

**application.yml:**
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: user
    password: pass
    hikari:
      # Pool 크기
      minimum-idle: 10
      maximum-pool-size: 20
      
      # Timeout
      connection-timeout: 30000       # 연결 대기 시간 (30초)
      idle-timeout: 600000            # 유휴 연결 유지 시간 (10분)
      max-lifetime: 1800000           # 연결 최대 수명 (30분)
      
      # 기타
      connection-test-query: SELECT 1  # 연결 테스트 쿼리
      pool-name: HikariPool
```

### 최적 Pool 크기

**공식 (단순):**
```
최적 Pool 크기 = CPU 코어 수 × 2
```

**예시:**
- 서버 CPU: 8 코어
- Pool 크기: 16

**이유:**
DB 작업은 대부분 I/O 대기. CPU 2개당 1개 연결로 충분.

**공식 (정확):**
```
Pool 크기 = (Core 수 × 2) + 디스크 수
```

**실무:**
- 시작: CPU × 2
- 모니터링하면서 조정
- Connection Wait 발생: 늘림
- CPU Idle 높음: 줄임

**너무 많으면:**
```yaml
maximum-pool-size: 100  # Bad
```

- DB 서버 과부하
- 컨텍스트 스위칭 증가
- 메모리 낭비

**너무 적으면:**
```yaml
maximum-pool-size: 2  # Bad
```

- Connection Wait 증가
- 응답 시간 느림
- Timeout 발생

### Connection Leak 방지

**문제:**
```java
public void badMethod() {
    Connection conn = dataSource.getConnection();
    // 쿼리 실행
    // conn.close() 호출 안 함!
}
```

연결이 반환되지 않는다. Pool이 고갈된다.

**해결 1: try-with-resources**
```java
public void goodMethod() {
    try (Connection conn = dataSource.getConnection();
         PreparedStatement ps = conn.prepareStatement(sql)) {
        // 쿼리 실행
    }  // 자동으로 close() 호출
}
```

**해결 2: Spring Transaction**
```java
@Transactional
public void goodMethod() {
    // Spring이 자동으로 연결 관리
    jdbcTemplate.query(sql, rowMapper);
}
```

**Leak 탐지:**
```yaml
spring:
  datasource:
    hikari:
      leak-detection-threshold: 60000  # 1분 이상 반환 안 되면 경고
```

로그:
```
HikariPool-1 - Connection leak detection triggered for connection ...
```

## Optimistic Lock (낙관적 락)

### 개념

**충돌이 드물다고 가정**한다. 버전을 체크해서 충돌을 감지한다.

**동작:**
1. 데이터 읽기 (버전 포함)
2. 수정
3. 저장 시 버전 확인
4. 버전이 같으면 저장 + 버전 증가
5. 다르면 예외 (다른 사람이 먼저 수정함)

### JPA 구현

**Entity:**
```java
@Entity
public class Product {
    
    @Id
    @GeneratedValue
    private Long id;
    
    private String name;
    private Integer stock;
    
    @Version  // 낙관적 락
    private Long version;
}
```

**Service:**
```java
@Service
public class ProductService {
    
    @Transactional
    public void decreaseStock(Long productId, int quantity) {
        Product product = productRepository.findById(productId)
            .orElseThrow();
        
        product.setStock(product.getStock() - quantity);
        
        // 저장 시 버전 체크
        // UPDATE product SET stock = ?, version = version + 1 
        // WHERE id = ? AND version = ?
        productRepository.save(product);
    }
}
```

**충돌 처리:**
```java
@Service
public class OrderService {
    
    public void createOrder(OrderRequest request) {
        int maxRetries = 3;
        int attempt = 0;
        
        while (attempt < maxRetries) {
            try {
                productService.decreaseStock(request.getProductId(), request.getQuantity());
                break;  // 성공
            } catch (ObjectOptimisticLockingFailureException e) {
                attempt++;
                if (attempt >= maxRetries) {
                    throw new BusinessException("재고 차감 실패");
                }
                // 재시도
                Thread.sleep(100);
            }
        }
    }
}
```

**장점:**
- Lock을 잡지 않음 (성능 좋음)
- 데드락 없음

**단점:**
- 충돌 시 재시도 필요
- 충돌이 많으면 비효율적

**사용 사례:**
- 재고 관리 (충돌 적음)
- 게시글 수정
- 사용자 프로필 업데이트

## Pessimistic Lock (비관적 락)

### 개념

**충돌이 자주 발생**한다고 가정한다. 읽을 때 Lock을 잡는다.

**SELECT FOR UPDATE:**
```sql
SELECT * FROM product WHERE id = 1 FOR UPDATE;
```

다른 트랜잭션은 대기한다. 첫 트랜잭션이 커밋/롤백하면 진행.

### JPA 구현

```java
public interface ProductRepository extends JpaRepository<Product, Long> {
    
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT p FROM Product p WHERE p.id = :id")
    Optional<Product> findByIdWithLock(@Param("id") Long id);
}
```

**Service:**
```java
@Service
public class ProductService {
    
    @Transactional
    public void decreaseStock(Long productId, int quantity) {
        // Lock 획득 (다른 트랜잭션은 대기)
        Product product = productRepository.findByIdWithLock(productId)
            .orElseThrow();
        
        if (product.getStock() < quantity) {
            throw new OutOfStockException();
        }
        
        product.setStock(product.getStock() - quantity);
        productRepository.save(product);
        
        // 트랜잭션 종료 시 Lock 해제
    }
}
```

**장점:**
- 충돌 방지 (먼저 온 사람이 먼저)
- 재시도 불필요

**단점:**
- Lock 대기 시간 (성능 저하)
- 데드락 가능성

**사용 사례:**
- 포인트 차감 (정확성 중요)
- 계좌 잔액 업데이트
- 티켓팅 (선착순)

### 데드락

**시나리오:**
```
트랜잭션 A: Product 1 Lock → Product 2 Lock 시도
트랜잭션 B: Product 2 Lock → Product 1 Lock 시도
```

서로 기다린다. 데드락.

**해결 1: 순서 고정**
```java
// 항상 ID 오름차순으로 Lock
public void updateProducts(Long id1, Long id2) {
    List<Long> ids = List.of(id1, id2);
    Collections.sort(ids);
    
    for (Long id : ids) {
        Product p = productRepository.findByIdWithLock(id).orElseThrow();
        // 업데이트
    }
}
```

**해결 2: Timeout**
```yaml
spring:
  jpa:
    properties:
      javax.persistence.lock.timeout: 10000  # 10초
```

10초 대기 후 예외.

**해결 3: DB 자동 감지**
MySQL은 데드락을 자동으로 감지하고 하나를 롤백한다.

```java
try {
    updateProducts(id1, id2);
} catch (CannotAcquireLockException e) {
    log.warn("Deadlock detected, retrying");
    // 재시도
}
```

## N+1 문제

### 문제

**시나리오:**
게시글 목록 + 작성자 이름 표시.

```java
@Entity
public class Post {
    @Id
    private Long id;
    private String title;
    
    @ManyToOne(fetch = FetchType.LAZY)
    private User author;
}

// Service
public List<PostResponse> getPosts() {
    List<Post> posts = postRepository.findAll();  // Query 1
    
    return posts.stream()
        .map(post -> new PostResponse(
            post.getTitle(),
            post.getAuthor().getName()  // Query N (각 post마다)
        ))
        .collect(Collectors.toList());
}
```

**SQL:**
```sql
-- 1개 쿼리
SELECT * FROM post;

-- N개 쿼리 (post가 100개면 100개 쿼리)
SELECT * FROM user WHERE id = 1;
SELECT * FROM user WHERE id = 2;
SELECT * FROM user WHERE id = 3;
...
SELECT * FROM user WHERE id = 100;
```

**총 101개 쿼리.** 엄청난 성능 저하.

### 해결 1: Fetch Join

```java
public interface PostRepository extends JpaRepository<Post, Long> {
    
    @Query("SELECT p FROM Post p JOIN FETCH p.author")
    List<Post> findAllWithAuthor();
}
```

**SQL:**
```sql
SELECT p.*, u.* 
FROM post p 
INNER JOIN user u ON p.author_id = u.id;
```

**1개 쿼리로 해결.**

### 해결 2: @EntityGraph

```java
public interface PostRepository extends JpaRepository<Post, Long> {
    
    @EntityGraph(attributePaths = {"author"})
    List<Post> findAll();
}
```

Fetch Join과 같은 효과. 더 간단.

### 해결 3: Batch Size

```yaml
spring:
  jpa:
    properties:
      hibernate.default_batch_fetch_size: 100
```

```sql
-- N개 쿼리 대신 1개 쿼리
SELECT * FROM user WHERE id IN (1, 2, 3, ..., 100);
```

101개 → 2개 쿼리.

### 해결 4: QueryDSL

```java
public List<PostResponse> getPosts() {
    return queryFactory
        .select(new QPostResponse(
            post.title,
            post.author.name
        ))
        .from(post)
        .join(post.author)
        .fetch();
}
```

**Projection:** 필요한 필드만 조회. 더 빠름.

### N+1 탐지

**Hibernate Statistics:**
```yaml
spring:
  jpa:
    properties:
      hibernate.generate_statistics: true
logging:
  level:
    org.hibernate.stat: DEBUG
```

로그에 쿼리 개수 표시:
```
HibernateStatisticsManager: 
  Query count: 101
```

101개면 N+1 의심.

## Query 최적화

### EXPLAIN ANALYZE

쿼리 실행 계획 확인.

```sql
EXPLAIN ANALYZE
SELECT * FROM orders 
WHERE user_id = 123 
AND created_at >= '2026-01-01';
```

**출력:**
```
-> Filter: (orders.created_at >= '2026-01-01')  (cost=100.00 rows=50)
    -> Index lookup on orders using idx_user_id (user_id=123)  (cost=10.00 rows=100)
```

**분석:**
- `Index lookup`: 인덱스 사용 (빠름)
- `cost`: 예상 비용
- `rows`: 예상 행 수

### 느린 쿼리

**Full Table Scan:**
```sql
EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';

-> Table scan on users  (cost=10000.00 rows=50000)
```

`Table scan` = 전체 테이블 읽기. 매우 느림.

**인덱스 추가:**
```sql
CREATE INDEX idx_email ON users(email);

EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';

-> Index lookup on users using idx_email  (cost=1.00 rows=1)
```

10000 → 1. **10,000배 빠름.**

### 복합 인덱스

**쿼리:**
```sql
SELECT * FROM orders 
WHERE user_id = 123 
  AND status = 'PENDING'
ORDER BY created_at DESC;
```

**인덱스:**
```sql
CREATE INDEX idx_user_status_created 
ON orders(user_id, status, created_at DESC);
```

**순서 중요:**
1. WHERE 절에 자주 사용
2. Cardinality 높은 것 먼저
3. ORDER BY/GROUP BY 마지막

### 커버링 인덱스

인덱스만으로 쿼리 완료 (테이블 접근 X).

**쿼리:**
```sql
SELECT user_id, status, created_at 
FROM orders 
WHERE user_id = 123;
```

**인덱스:**
```sql
CREATE INDEX idx_covering 
ON orders(user_id, status, created_at);
```

**EXPLAIN:**
```
-> Covering index scan on orders using idx_covering
```

`Covering` = 테이블 안 봄. 더 빠름.

### 인덱스 주의사항

**너무 많으면:**
- 쓰기 성능 저하
- 디스크 공간 낭비
- 메모리 사용 증가

**권장:**
테이블당 5-7개 이하.

**사용 안 하는 인덱스 찾기:**
```sql
SELECT *
FROM information_schema.statistics
WHERE table_schema = 'mydb'
  AND table_name = 'orders'
  AND cardinality IS NULL;
```

## 파티셔닝

### 왜 필요한가

테이블이 너무 크다.

**문제:**
- orders 테이블: 1억 행
- 쿼리 느림
- 백업 오래 걸림
- 인덱스 비대

**파티셔닝:**
테이블을 작은 단위로 나눈다.

### Range Partitioning

범위로 나눔.

```sql
CREATE TABLE orders (
    id BIGINT,
    user_id BIGINT,
    created_at DATE,
    amount DECIMAL
)
PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027)
);
```

**쿼리:**
```sql
SELECT * FROM orders 
WHERE created_at >= '2026-01-01';
```

2026 파티션만 검색. 빠름.

### List Partitioning

목록으로 나눔.

```sql
CREATE TABLE orders (
    id BIGINT,
    region VARCHAR(10),
    amount DECIMAL
)
PARTITION BY LIST (region) (
    PARTITION p_seoul VALUES IN ('SEOUL'),
    PARTITION p_busan VALUES IN ('BUSAN'),
    PARTITION p_etc VALUES IN ('ETC')
);
```

### Hash Partitioning

해시로 균등 분산.

```sql
CREATE TABLE orders (
    id BIGINT,
    user_id BIGINT
)
PARTITION BY HASH (user_id)
PARTITIONS 4;
```

**장점:**
데이터 균등 분배.

**단점:**
특정 파티션만 조회 불가 (전체 검색).

### 파티셔닝 주의사항

**Primary Key 포함:**
파티션 키는 PK에 포함되어야 함.

```sql
-- Bad
PRIMARY KEY (id)
PARTITION BY RANGE (created_at)

-- Good
PRIMARY KEY (id, created_at)
PARTITION BY RANGE (created_at)
```

**자동 파티션 추가:**
```sql
-- 매달 새 파티션 추가 (프로시저)
CREATE EVENT add_partition
ON SCHEDULE EVERY 1 MONTH
DO
  ALTER TABLE orders 
  ADD PARTITION (
    PARTITION p2026_02 VALUES LESS THAN ('2026-03-01')
  );
```

## 트랜잭션 격리 수준

### 문제들

**Dirty Read (더티 리드):**
커밋 안 된 데이터를 읽음.

```
트랜잭션 A: UPDATE balance = 1000
트랜잭션 B: SELECT balance (1000 읽음)
트랜잭션 A: ROLLBACK (다시 500으로)
```

B가 잘못된 값(1000)을 읽었다.

**Non-Repeatable Read (반복 불가능 읽기):**
같은 쿼리가 다른 결과.

```
트랜잭션 A: SELECT balance (500)
트랜잭션 B: UPDATE balance = 1000, COMMIT
트랜잭션 A: SELECT balance (1000)
```

A가 같은 트랜잭션에서 다른 값을 읽었다.

**Phantom Read (팬텀 리드):**
없던 행이 생김.

```
트랜잭션 A: SELECT COUNT(*) WHERE age > 20 (결과: 10)
트랜잭션 B: INSERT age=25, COMMIT
트랜잭션 A: SELECT COUNT(*) WHERE age > 20 (결과: 11)
```

### 격리 수준

**READ UNCOMMITTED (레벨 0):**
- 커밋 안 된 데이터도 읽음
- Dirty Read 발생
- 거의 사용 안 함

**READ COMMITTED (레벨 1):**
- 커밋된 데이터만 읽음
- Dirty Read 방지
- Non-Repeatable Read 발생
- **PostgreSQL, Oracle 기본**

**REPEATABLE READ (레벨 2):**
- 같은 트랜잭션에서 같은 결과
- Non-Repeatable Read 방지
- Phantom Read 발생 (일부)
- **MySQL 기본**

**SERIALIZABLE (레벨 3):**
- 완전히 순차 실행처럼
- 모든 문제 방지
- 성능 최악
- 거의 사용 안 함

### Spring 설정

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public void transfer(Long fromId, Long toId, BigDecimal amount) {
    Account from = accountRepository.findById(fromId).orElseThrow();
    Account to = accountRepository.findById(toId).orElseThrow();
    
    from.setBalance(from.getBalance().subtract(amount));
    to.setBalance(to.getBalance().add(amount));
    
    accountRepository.saveAll(List.of(from, to));
}
```

### 실무 선택

**대부분: READ COMMITTED**
- 성능과 일관성 균형
- Dirty Read만 방지하면 충분

**정확성 중요: REPEATABLE READ + Lock**
```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void decreasePoint(Long userId, int point) {
    User user = userRepository.findByIdWithLock(userId).orElseThrow();
    user.setPoint(user.getPoint() - point);
}
```

**절대 일관성: SERIALIZABLE**
은행, 금융 등. 하지만 성능 희생.

## 실무 패턴

### 재고 차감 (Optimistic)

```java
@Service
public class OrderService {
    
    @Transactional
    public void createOrder(OrderRequest request) {
        int maxRetries = 5;
        
        for (int i = 0; i < maxRetries; i++) {
            try {
                Product product = productRepository.findById(request.getProductId())
                    .orElseThrow();
                
                if (product.getStock() < request.getQuantity()) {
                    throw new OutOfStockException();
                }
                
                product.setStock(product.getStock() - request.getQuantity());
                productRepository.save(product);
                
                Order order = new Order(request);
                orderRepository.save(order);
                
                return;  // 성공
            } catch (ObjectOptimisticLockingFailureException e) {
                if (i == maxRetries - 1) {
                    throw new BusinessException("주문 실패");
                }
                Thread.sleep(50 * (i + 1));  // Exponential Backoff
            }
        }
    }
}
```

### 포인트 차감 (Pessimistic)

```java
@Service
public class PointService {
    
    @Transactional
    public void usePoint(Long userId, int point) {
        User user = userRepository.findByIdWithLock(userId)
            .orElseThrow();
        
        if (user.getPoint() < point) {
            throw new InsufficientPointException();
        }
        
        user.setPoint(user.getPoint() - point);
        userRepository.save(user);
        
        // Point 사용 이력 저장
        pointHistoryRepository.save(new PointHistory(userId, -point));
    }
}
```

## 모니터링

### Slow Query Log

```sql
-- MySQL
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  # 1초 이상
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
```

### Connection Pool Metrics

```java
@Component
public class HikariMetrics {
    
    @Autowired
    private HikariDataSource hikariDataSource;
    
    @Scheduled(fixedRate = 60000)
    public void logMetrics() {
        HikariPoolMXBean pool = hikariDataSource.getHikariPoolMXBean();
        
        log.info("Connection Pool - Active: {}, Idle: {}, Total: {}, Waiting: {}",
            pool.getActiveConnections(),
            pool.getIdleConnections(),
            pool.getTotalConnections(),
            pool.getThreadsAwaitingConnection());
    }
}
```

### JPA Statistics

```yaml
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.type.descriptor.sql.BasicBinder: TRACE
    org.hibernate.stat: INFO
```

## 참고

- HikariCP GitHub: https://github.com/brettwooldridge/HikariCP
- JPA 스펙: https://jakarta.ee/specifications/persistence/
- MySQL 공식 문서: https://dev.mysql.com/doc/
- PostgreSQL 공식 문서: https://www.postgresql.org/docs/


