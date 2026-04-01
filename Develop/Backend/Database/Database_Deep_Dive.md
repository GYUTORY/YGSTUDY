---
title: 데이터베이스 심화 (Database Deep Dive)
tags: [backend, database, connection-pool, lock, n+1, query-optimization, partitioning, isolation-level, hikaricp, jpa, distributed-lock, cdc, multi-datasource]
updated: 2026-04-01
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

## 분산 락 (Distributed Lock)

### 단일 서버 Lock의 한계

앞에서 다룬 Pessimistic Lock은 DB 레벨에서 동작한다. 서버가 1대면 문제없다. 서버가 여러 대면 상황이 다르다.

```
서버 A: SELECT FOR UPDATE → Lock 획득
서버 B: SELECT FOR UPDATE → Lock 대기
```

DB Lock은 여전히 동작한다. 하지만 다음 상황을 생각해보자.

```
서버 A: 외부 API 호출 + DB 업데이트 (하나의 작업)
서버 B: 같은 작업 동시 실행
```

외부 API 호출은 DB Lock으로 보호할 수 없다. 이런 경우 분산 락이 필요하다.

### Redis 분산 락

가장 많이 쓰는 방식이다. Redis의 `SET NX` 명령을 사용한다.

**기본 원리:**

```
SET lock:order:123 "server-a" NX EX 30
```

- `NX`: 키가 없을 때만 SET (이미 있으면 실패)
- `EX 30`: 30초 후 자동 만료 (장애 시 Lock이 영원히 안 풀리는 걸 방지)

**Redisson 사용 (Spring Boot):**

```java
@Configuration
public class RedissonConfig {

    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer()
            .setAddress("redis://localhost:6379");
        return Redisson.create(config);
    }
}
```

```java
@Service
public class OrderService {

    private final RedissonClient redissonClient;

    @Transactional
    public void createOrder(Long productId, int quantity) {
        RLock lock = redissonClient.getLock("lock:product:" + productId);

        boolean acquired = false;
        try {
            // 10초 대기, 획득 후 5초 유지
            acquired = lock.tryLock(10, 5, TimeUnit.SECONDS);
            if (!acquired) {
                throw new BusinessException("락 획득 실패");
            }

            Product product = productRepository.findById(productId)
                .orElseThrow();

            if (product.getStock() < quantity) {
                throw new OutOfStockException();
            }

            product.setStock(product.getStock() - quantity);
            productRepository.save(product);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BusinessException("락 대기 중 인터럽트");
        } finally {
            if (acquired && lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

### Redisson을 쓰는 이유

직접 `SET NX`로 구현하면 문제가 많다.

**문제 1: Lock 해제 시 다른 사람의 Lock을 풀 수 있다**

```
서버 A: Lock 획득 (TTL 30초)
서버 A: 작업이 35초 걸림 → Lock 자동 만료
서버 B: Lock 획득
서버 A: 작업 완료 → DEL lock:order:123 (서버 B의 Lock을 삭제!)
```

Redisson은 Lock 소유자를 확인하고 Lua 스크립트로 원자적으로 해제한다.

**문제 2: Lock 갱신 (Watchdog)**

작업이 TTL보다 오래 걸리면 Lock이 풀린다. Redisson은 Watchdog이 자동으로 TTL을 연장한다. 기본 30초마다 갱신.

```java
// leaseTime을 지정하지 않으면 Watchdog 활성화
lock.tryLock(10, TimeUnit.SECONDS);  // Watchdog ON
lock.tryLock(10, 30, TimeUnit.SECONDS);  // Watchdog OFF (30초 후 자동 해제)
```

Watchdog을 쓸 때 주의할 점: 서버가 갑자기 죽으면 Watchdog도 죽는다. 이 경우 기본 TTL(30초) 후에 Lock이 해제된다. 서버 장애 시 30초간 Lock이 유지되는 건 감수해야 한다.

**문제 3: Redis 장애**

Redis가 단일 노드면 Redis가 죽으면 Lock도 못 건다. Redis Sentinel이나 Cluster를 쓰면 되긴 하지만, 페일오버 중에 Lock이 꼬일 수 있다.

이걸 해결하려면 Redlock 알고리즘이 있다. Redis 노드 5개에 동시에 Lock을 걸고 과반수(3개) 이상 성공하면 Lock 획득으로 본다. Redisson이 이 구현을 제공한다.

```java
RLock lock1 = redisson1.getLock("lock:order:123");
RLock lock2 = redisson2.getLock("lock:order:123");
RLock lock3 = redisson3.getLock("lock:order:123");

RedissonMultiLock multiLock = new RedissonRedLock(lock1, lock2, lock3);
multiLock.tryLock(10, 30, TimeUnit.SECONDS);
```

실무에서 Redlock까지 쓰는 경우는 많지 않다. 대부분 Redis Sentinel + Redisson이면 충분하다.

### 분산 락 사용 시 주의사항

**Lock과 트랜잭션 순서:**

```java
// 잘못된 순서
@Transactional  // 트랜잭션 시작
public void process() {
    lock.tryLock();  // Lock 획득
    // 작업
    lock.unlock();  // Lock 해제
}  // 트랜잭션 커밋
```

Lock을 해제한 후 트랜잭션이 아직 커밋되지 않았다. 다른 서버가 Lock을 획득하면 커밋 전 데이터를 볼 수 있다.

```java
// 올바른 순서
public void process() {
    lock.tryLock();  // Lock 먼저
    try {
        processWithTransaction();  // 트랜잭션은 안에서
    } finally {
        lock.unlock();  // 트랜잭션 커밋 후 Lock 해제
    }
}

@Transactional
public void processWithTransaction() {
    // 작업
}
```

Lock 획득 → 트랜잭션 시작 → 작업 → 트랜잭션 커밋 → Lock 해제. 이 순서를 지켜야 한다.

**Lock 키 설계:**

```java
// 너무 넓은 범위
"lock:product"  // 모든 상품에 Lock → 병목

// 적절한 범위
"lock:product:" + productId  // 상품별 Lock

// 더 세밀한 범위
"lock:product:" + productId + ":stock"  // 재고 변경에만 Lock
```

범위가 넓으면 병목이 생기고, 좁으면 Lock 수가 많아진다. 비즈니스 요구사항에 맞게 정하면 된다.

## CDC (Change Data Capture)

### CDC가 뭔가

DB 변경 사항을 감지해서 다른 시스템에 전달하는 패턴이다.

예를 들어 주문 테이블에 INSERT가 발생하면:
- 검색 엔진(Elasticsearch)에 인덱싱
- 데이터 웨어하우스에 동기화
- 다른 마이크로서비스에 이벤트 전달

이걸 애플리케이션 코드에서 하면 문제가 생긴다.

```java
@Transactional
public void createOrder(OrderRequest request) {
    Order order = orderRepository.save(new Order(request));

    // 검색 인덱싱
    elasticsearchClient.index(order);  // 실패하면?

    // 이벤트 발행
    kafkaTemplate.send("order-created", order);  // 실패하면?
}
```

DB 저장은 됐는데 Kafka 전송이 실패하면 데이터 불일치가 발생한다. 트랜잭션 안에 넣으면 외부 시스템 장애가 DB 트랜잭션에 영향을 준다.

### Debezium을 이용한 CDC

Debezium은 DB의 변경 로그(binlog, WAL)를 읽어서 Kafka로 전달한다. 애플리케이션 코드를 건드리지 않는다.

**동작 방식:**

```
MySQL binlog → Debezium Connector → Kafka Topic → Consumer
```

MySQL은 모든 변경을 binlog에 기록한다. Debezium은 MySQL 레플리카처럼 binlog를 구독한다. 변경이 생기면 Kafka 토픽으로 보낸다.

**MySQL 설정:**

```ini
# my.cnf
[mysqld]
server-id=1
log-bin=mysql-bin
binlog-format=ROW
binlog-row-image=FULL
```

`binlog-format=ROW`가 중요하다. STATEMENT 모드면 SQL 문만 기록하기 때문에 변경 전후 값을 알 수 없다.

**Debezium Connector 등록 (Kafka Connect REST API):**

```json
{
  "name": "mysql-connector",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "mysql-host",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "password",
    "database.server.id": "1",
    "topic.prefix": "myapp",
    "database.include.list": "mydb",
    "table.include.list": "mydb.orders",
    "schema.history.internal.kafka.bootstrap.servers": "kafka:9092",
    "schema.history.internal.kafka.topic": "schema-changes"
  }
}
```

이렇게 등록하면 `myapp.mydb.orders` 토픽에 변경 이벤트가 들어온다.

**Kafka 메시지 구조:**

```json
{
  "before": null,
  "after": {
    "id": 1,
    "user_id": 100,
    "amount": 50000,
    "status": "CREATED"
  },
  "op": "c",
  "ts_ms": 1711929600000
}
```

- `op`: 연산 타입. `c`(create), `u`(update), `d`(delete), `r`(snapshot read)
- `before`: 변경 전 값 (INSERT면 null)
- `after`: 변경 후 값 (DELETE면 null)

**Consumer 구현:**

```java
@Component
public class OrderCdcConsumer {

    @KafkaListener(topics = "myapp.mydb.orders")
    public void handleOrderChange(ConsumerRecord<String, String> record) {
        JsonNode value = objectMapper.readTree(record.value());
        String op = value.get("op").asText();
        JsonNode after = value.get("after");

        switch (op) {
            case "c":  // INSERT
                elasticsearchService.index(toOrderDocument(after));
                break;
            case "u":  // UPDATE
                elasticsearchService.update(toOrderDocument(after));
                break;
            case "d":  // DELETE
                JsonNode before = value.get("before");
                elasticsearchService.delete(before.get("id").asLong());
                break;
        }
    }
}
```

### Outbox 패턴

CDC의 변형이다. 이벤트를 별도 테이블(outbox)에 저장하고, CDC가 이 테이블을 읽어서 Kafka로 보낸다.

**왜 필요한가:**

binlog CDC는 DB의 물리적 변경을 그대로 전달한다. 비즈니스 이벤트와 DB 변경이 1:1로 매핑되지 않는 경우가 있다.

```java
// 주문 생성 시 orders 테이블 INSERT + order_items 테이블 INSERT
// CDC는 두 개의 이벤트를 별도로 보낸다
// Consumer 입장에서는 이게 하나의 주문인지 알기 어렵다
```

**Outbox 테이블:**

```sql
CREATE TABLE outbox (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**애플리케이션 코드:**

```java
@Transactional
public void createOrder(OrderRequest request) {
    Order order = orderRepository.save(new Order(request));
    orderItemRepository.saveAll(createItems(order, request));

    // 비즈니스 이벤트를 outbox에 저장 (같은 트랜잭션)
    outboxRepository.save(new Outbox(
        "Order",
        order.getId().toString(),
        "OrderCreated",
        objectMapper.writeValueAsString(OrderCreatedEvent.from(order))
    ));
}
```

DB 트랜잭션과 이벤트 발행이 원자적으로 처리된다. 트랜잭션이 롤백되면 outbox INSERT도 롤백된다.

Debezium에는 Outbox Event Router가 내장되어 있다. outbox 테이블의 변경을 감지해서 aggregate_type 기반으로 토픽을 라우팅하고, 처리된 레코드를 자동 삭제하는 것까지 설정할 수 있다.

### CDC 운영 시 주의사항

**binlog 보관 기간:**

Debezium이 다운됐다가 복구되면 마지막으로 읽은 위치부터 다시 읽는다. 그 사이 binlog가 삭제됐으면 스냅샷을 다시 찍어야 한다. 데이터가 많으면 수 시간 걸린다.

```ini
# my.cnf
expire_logs_days=7  # 최소 7일 유지
```

**스키마 변경:**

ALTER TABLE로 컬럼을 추가/삭제하면 Debezium이 이를 감지하고 스키마를 업데이트한다. 하지만 Consumer 쪽 역직렬화가 깨질 수 있다. 스키마 레지스트리(Confluent Schema Registry)를 사용해서 호환성을 관리하는 게 낫다.

**순서 보장:**

같은 레코드의 변경은 순서가 보장된다 (같은 Kafka 파티션). 다른 레코드 간의 순서는 보장되지 않는다. 파티션 키를 적절히 설정해야 한다.

## 멀티 데이터소스 라우팅

### 필요한 상황

**Read/Write 분리:**

쓰기는 Primary DB, 읽기는 Replica DB로 보내서 부하를 분산한다. 트래픽이 늘면 Replica만 추가하면 된다.

```
쓰기 → Primary (1대)
읽기 → Replica (여러 대)
```

**서비스별 DB 분리:**

마이크로서비스 전환 중이라 아직 모놀리스에서 여러 DB에 접근해야 하는 경우.

```
주문 관련 → order-db
회원 관련 → member-db
```

### Spring Boot Read/Write 분리

**DataSource 설정:**

```java
@Configuration
public class DataSourceConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.primary")
    public DataSource primaryDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    @ConfigurationProperties("spring.datasource.replica")
    public DataSource replicaDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    public DataSource routingDataSource(
            @Qualifier("primaryDataSource") DataSource primary,
            @Qualifier("replicaDataSource") DataSource replica) {

        ReadWriteRoutingDataSource routing = new ReadWriteRoutingDataSource();

        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put("primary", primary);
        targetDataSources.put("replica", replica);

        routing.setTargetDataSources(targetDataSources);
        routing.setDefaultTargetDataSource(primary);

        return routing;
    }

    @Bean
    @Primary
    public DataSource dataSource(@Qualifier("routingDataSource") DataSource routing) {
        return new LazyConnectionDataSourceProxy(routing);
    }
}
```

`LazyConnectionDataSourceProxy`를 감싸야 한다. 이게 없으면 트랜잭션 시작 시점에 DataSource가 결정되는데, 그때는 아직 `@Transactional(readOnly)` 정보를 모른다. Lazy로 감싸면 실제 쿼리 실행 시점에 DataSource를 결정한다.

**라우팅 구현:**

```java
public class ReadWriteRoutingDataSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        boolean readOnly = TransactionSynchronizationManager
            .isCurrentTransactionReadOnly();
        return readOnly ? "replica" : "primary";
    }
}
```

**사용:**

```java
@Service
public class OrderService {

    @Transactional  // readOnly 기본값 false → Primary
    public void createOrder(OrderRequest request) {
        orderRepository.save(new Order(request));
    }

    @Transactional(readOnly = true)  // → Replica
    public List<Order> getOrders(Long userId) {
        return orderRepository.findByUserId(userId);
    }
}
```

### 복제 지연 문제

Primary에 쓰고 바로 Replica에서 읽으면 데이터가 아직 없을 수 있다. MySQL 복제는 비동기라 수 ms ~ 수 초 지연이 생긴다.

**시나리오:**

```
1. 주문 생성 (Primary에 INSERT)
2. 주문 상세 페이지로 리다이렉트
3. 주문 조회 (Replica에서 SELECT) → 아직 없음!
```

**해결 1: 쓰기 직후 읽기는 Primary에서**

```java
@Service
public class OrderService {

    @Transactional
    public OrderResponse createAndReturn(OrderRequest request) {
        Order order = orderRepository.save(new Order(request));
        // 같은 트랜잭션이라 Primary에서 읽음
        return OrderResponse.from(order);
    }
}
```

**해결 2: 강제 Primary 라우팅**

```java
public class DataSourceContext {
    private static final ThreadLocal<String> CONTEXT = new ThreadLocal<>();

    public static void setForcePrimary() {
        CONTEXT.set("primary");
    }

    public static String get() {
        return CONTEXT.get();
    }

    public static void clear() {
        CONTEXT.remove();
    }
}

public class ReadWriteRoutingDataSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        String forced = DataSourceContext.get();
        if (forced != null) {
            return forced;
        }
        boolean readOnly = TransactionSynchronizationManager
            .isCurrentTransactionReadOnly();
        return readOnly ? "replica" : "primary";
    }
}
```

```java
// 주문 생성 직후 조회가 필요한 API
public OrderResponse getOrder(Long orderId) {
    DataSourceContext.setForcePrimary();
    try {
        return orderQueryService.getOrder(orderId);
    } finally {
        DataSourceContext.clear();
    }
}
```

### 여러 DB 접근 (서비스별 분리)

```yaml
spring:
  datasource:
    order:
      url: jdbc:mysql://order-db:3306/orders
      username: order_user
      password: pass
    member:
      url: jdbc:mysql://member-db:3306/members
      username: member_user
      password: pass
```

```java
@Configuration
@EnableJpaRepositories(
    basePackages = "com.example.order.repository",
    entityManagerFactoryRef = "orderEntityManagerFactory",
    transactionManagerRef = "orderTransactionManager"
)
public class OrderDataSourceConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.order")
    public DataSource orderDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    public LocalContainerEntityManagerFactoryBean orderEntityManagerFactory(
            @Qualifier("orderDataSource") DataSource dataSource,
            EntityManagerFactoryBuilder builder) {
        return builder
            .dataSource(dataSource)
            .packages("com.example.order.entity")
            .persistenceUnit("order")
            .build();
    }

    @Bean
    public PlatformTransactionManager orderTransactionManager(
            @Qualifier("orderEntityManagerFactory") EntityManagerFactory emf) {
        return new JpaTransactionManager(emf);
    }
}
```

Member도 같은 방식으로 설정한다. 패키지를 기준으로 어떤 Repository가 어떤 DataSource를 쓸지 결정된다.

**주의사항:**

서로 다른 DB에 걸친 트랜잭션은 `@Transactional` 하나로 보장되지 않는다. 주문 DB INSERT 성공 후 회원 DB UPDATE가 실패하면 주문만 남는다. 이런 경우 Saga 패턴이나 보상 트랜잭션을 고려해야 한다. 단순한 경우에는 한쪽 실패 시 수동으로 롤백하는 로직을 넣는 것도 현실적인 방법이다.

## 참고

- HikariCP GitHub: https://github.com/brettwooldridge/HikariCP
- JPA 스펙: https://jakarta.ee/specifications/persistence/
- MySQL 공식 문서: https://dev.mysql.com/doc/
- PostgreSQL 공식 문서: https://www.postgresql.org/docs/
- Redisson GitHub: https://github.com/redisson/redisson
- Debezium 공식 문서: https://debezium.io/documentation/


