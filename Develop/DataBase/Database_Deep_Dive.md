---
title: 데이터베이스 심화 (Database Deep Dive)
tags: [backend, database, rdbms, java]
updated: 2026-04-01
---

# 데이터베이스 심화 (Database Deep Dive)

## 개요

데이터베이스는 백엔드 애플리케이션의 핵심이다. Connection Pool 설정이 잘못되면 성능이 급격히 떨어진다. Lock을 잘못 사용하면 데드락이 발생한다. N+1 문제는 서비스 다운을 일으킨다. 이런 문제들을 해결하는 방법을 알아야 한다.

## Connection Pool

### 왜 필요한가

**문제 상황:**

DB 연결을 매번 새로 만든다.

```typescript
async function getUser(id: number): Promise<User> {
    // 매번 새 연결 생성
    const client = new Client({ connectionString: url });
    await client.connect();
    // 쿼리 실행
    // 연결 닫기
    await client.end();
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

```typescript
// Pool에서 빌려옴 (0.1ms)
const client = await pool.connect();
// 쿼리 실행
// Pool에 반환 (닫지 않음)
client.release();  // 실제로는 반환
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
```typescript
async function badMethod(): Promise<void> {
    const client = await pool.connect();
    // 쿼리 실행
    // client.release() 호출 안 함!
}
```

연결이 반환되지 않는다. Pool이 고갈된다.

**해결 1: try-finally로 반환 보장**
```typescript
async function goodMethod(): Promise<void> {
    const client = await pool.connect();
    try {
        await client.query(sql);
    } finally {
        client.release();  // 항상 반환
    }
}
```

**해결 2: pool.query() 사용 (자동 관리)**
```typescript
async function goodMethod(): Promise<void> {
    // pg Pool이 자동으로 연결 대여/반환 관리
    await pool.query(sql);
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
```typescript
import { Entity, PrimaryGeneratedColumn, Column, VersionColumn } from 'typeorm';

@Entity()
export class Product {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    name: string;

    @Column()
    stock: number;

    @VersionColumn()  // 낙관적 락
    version: number;
}
```

**Service:**
```typescript
async function decreaseStock(productId: number, quantity: number): Promise<void> {
    await dataSource.transaction(async (manager) => {
        const product = await manager.findOneByOrFail(Product, { id: productId });

        product.stock -= quantity;

        // 저장 시 버전 체크
        // UPDATE product SET stock = ?, version = version + 1
        // WHERE id = ? AND version = ?
        await manager.save(product);
    });
}
```

**충돌 처리:**
```typescript
import { OptimisticLockVersionMismatchError } from 'typeorm';

async function createOrder(request: OrderRequest): Promise<void> {
    const maxRetries = 3;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            await decreaseStock(request.productId, request.quantity);
            return;  // 성공
        } catch (e) {
            if (e instanceof OptimisticLockVersionMismatchError) {
                if (attempt >= maxRetries - 1) {
                    throw new Error('재고 차감 실패');
                }
                // 재시도
                await new Promise((r) => setTimeout(r, 100));
            } else {
                throw e;
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

### TypeORM 구현

```typescript
// 비관적 락 조회 (SELECT FOR UPDATE)
async function findByIdWithLock(manager: EntityManager, productId: number): Promise<Product> {
    const product = await manager.findOne(Product, {
        where: { id: productId },
        lock: { mode: 'pessimistic_write' },
    });
    if (!product) throw new Error('상품 없음');
    return product;
}
```

**Service:**
```typescript
async function decreaseStock(productId: number, quantity: number): Promise<void> {
    await dataSource.transaction(async (manager) => {
        // Lock 획득 (다른 트랜잭션은 대기)
        const product = await findByIdWithLock(manager, productId);

        if (product.stock < quantity) {
            throw new Error('재고 부족');
        }

        product.stock -= quantity;
        await manager.save(product);

        // 트랜잭션 종료 시 Lock 해제
    });
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
```typescript
// 항상 ID 오름차순으로 Lock
async function updateProducts(id1: number, id2: number): Promise<void> {
    const ids = [id1, id2].sort((a, b) => a - b);

    await dataSource.transaction(async (manager) => {
        for (const id of ids) {
            const p = await findByIdWithLock(manager, id);
            // 업데이트
        }
    });
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

```typescript
try {
    await updateProducts(id1, id2);
} catch (e: any) {
    // PostgreSQL deadlock error code: 40P01
    if (e.code === '40P01') {
        console.warn('Deadlock detected, retrying');
        // 재시도
    } else {
        throw e;
    }
}
```

## N+1 문제

### 문제

**시나리오:**
게시글 목록 + 작성자 이름 표시.

```typescript
@Entity()
export class Post {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    title: string;

    @ManyToOne(() => User, { lazy: true })
    @JoinColumn({ name: 'author_id' })
    author: Promise<User>;  // lazy → Promise 타입
}

// Service
async function getPosts(): Promise<PostResponse[]> {
    const posts = await postRepository.find();  // Query 1

    return Promise.all(posts.map(async (post) => ({
        title: post.title,
        authorName: (await post.author).name,  // Query N (각 post마다)
    })));
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

### 해결 1: 관계 Eager 로드 (relations 옵션)

```typescript
// TypeORM - relations 옵션으로 JOIN
async function findAllWithAuthor(): Promise<Post[]> {
    return postRepository.find({ relations: ['author'] });
}
```

**SQL:**
```sql
SELECT p.*, u.* 
FROM post p 
INNER JOIN user u ON p.author_id = u.id;
```

**1개 쿼리로 해결.**

### 해결 2: createQueryBuilder로 JOIN

```typescript
// TypeORM QueryBuilder로 JOIN (Fetch Join과 같은 효과)
async function findAll(): Promise<Post[]> {
    return dataSource
        .getRepository(Post)
        .createQueryBuilder('post')
        .leftJoinAndSelect('post.author', 'author')
        .getMany();
}
```

관계 엔티티를 SELECT에 포함. 더 유연.

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

### 해결 4: Raw SQL / 선택 필드 조회

```typescript
// 필요한 필드만 SELECT (Projection)
async function getPosts(): Promise<{ title: string; authorName: string }[]> {
    const rows = await dataSource.query(`
        SELECT p.title, u.name AS "authorName"
        FROM post p
        JOIN "user" u ON p.author_id = u.id
    `);
    return rows;
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

### TypeORM 설정

```typescript
// TypeORM - isolation level 설정
async function transfer(fromId: number, toId: number, amount: number): Promise<void> {
    await dataSource.transaction('READ COMMITTED', async (manager) => {
        const from = await manager.findOneByOrFail(Account, { id: fromId });
        const to = await manager.findOneByOrFail(Account, { id: toId });

        from.balance -= amount;
        to.balance += amount;

        await manager.save([from, to]);
    });
}
```

### 실무 선택

**대부분: READ COMMITTED**
- 성능과 일관성 균형
- Dirty Read만 방지하면 충분

**정확성 중요: REPEATABLE READ + Lock**
```typescript
async function decreasePoint(userId: number, point: number): Promise<void> {
    await dataSource.transaction('REPEATABLE READ', async (manager) => {
        const user = await manager.findOne(User, {
            where: { id: userId },
            lock: { mode: 'pessimistic_write' },
        });
        if (!user) throw new Error('User not found');
        user.point -= point;
        await manager.save(user);
    });
}
```

**절대 일관성: SERIALIZABLE**
은행, 금융 등. 하지만 성능 희생.

## 실무 패턴

### 재고 차감 (Optimistic)

```typescript
import { OptimisticLockVersionMismatchError } from 'typeorm';

async function createOrder(request: OrderRequest): Promise<void> {
    const maxRetries = 5;

    for (let i = 0; i < maxRetries; i++) {
        try {
            await dataSource.transaction(async (manager) => {
                const product = await manager.findOneByOrFail(Product, { id: request.productId });

                if (product.stock < request.quantity) {
                    throw new Error('재고 부족');
                }

                product.stock -= request.quantity;
                await manager.save(product);

                const order = manager.create(Order, request);
                await manager.save(order);
            });
            return;  // 성공
        } catch (e) {
            if (e instanceof OptimisticLockVersionMismatchError) {
                if (i === maxRetries - 1) throw new Error('주문 실패');
                await new Promise((r) => setTimeout(r, 50 * (i + 1)));  // Exponential Backoff
            } else {
                throw e;
            }
        }
    }
}
```

### 포인트 차감 (Pessimistic)

```typescript
async function usePoint(userId: number, point: number): Promise<void> {
    await dataSource.transaction(async (manager) => {
        const user = await manager.findOne(User, {
            where: { id: userId },
            lock: { mode: 'pessimistic_write' },
        });
        if (!user) throw new Error('User not found');

        if (user.point < point) {
            throw new Error('포인트 부족');
        }

        user.point -= point;
        await manager.save(user);

        // Point 사용 이력 저장
        const history = manager.create(PointHistory, { userId, amount: -point });
        await manager.save(history);
    });
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

```typescript
import { Pool } from 'pg';

const pool = new Pool({
    host: 'localhost',
    database: 'mydb',
    max: 20,         // 최대 연결 수
    idleTimeoutMillis: 600000,
    connectionTimeoutMillis: 30000,
});

// 1분마다 Pool 상태 로깅
setInterval(() => {
    console.info(
        `Connection Pool - Total: ${pool.totalCount}, Idle: ${pool.idleCount}, Waiting: ${pool.waitingCount}`
    );
}, 60_000);
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

**ioredis 분산 락 사용:**

```typescript
// npm install ioredis
import Redis from 'ioredis';
import { randomUUID } from 'crypto';

const redis = new Redis({ host: 'localhost', port: 6379 });

const unlockScript = `
  if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
  else
    return 0
  end
`;

async function acquireLock(key: string, leaseSec: number, waitSec: number): Promise<string | null> {
    const token = randomUUID();
    const deadline = Date.now() + waitSec * 1000;
    while (Date.now() < deadline) {
        const ok = await redis.set(key, token, 'NX', 'EX', leaseSec);
        if (ok === 'OK') return token;
        await new Promise((r) => setTimeout(r, 100));
    }
    return null;
}

async function releaseLock(key: string, token: string): Promise<void> {
    await redis.eval(unlockScript, 1, key, token);
}

async function createOrder(productId: number, quantity: number): Promise<void> {
    const lockKey = `lock:product:${productId}`;
    // 10초 대기, 획득 후 5초 유지
    const token = await acquireLock(lockKey, 5, 10);
    if (!token) throw new Error('락 획득 실패');

    try {
        await dataSource.transaction(async (manager) => {
            const product = await manager.findOneByOrFail(Product, { id: productId });

            if (product.stock < quantity) {
                throw new Error('재고 부족');
            }

            product.stock -= quantity;
            await manager.save(product);
        });
    } finally {
        await releaseLock(lockKey, token);
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

```typescript
// leaseSec를 지정하면 자동 만료 (EX), 지정 안 하면 직접 갱신 필요
await acquireLock(lockKey, 30, 10);   // 획득 후 30초 유지 (EX 30)
// Node.js는 Watchdog 대신 작업 완료 후 releaseLock으로 즉시 해제
// 장애 시 EX로 설정된 TTL 후 자동 해제
```

Watchdog을 쓸 때 주의할 점: 서버가 갑자기 죽으면 Watchdog도 죽는다. 이 경우 기본 TTL(30초) 후에 Lock이 해제된다. 서버 장애 시 30초간 Lock이 유지되는 건 감수해야 한다.

**문제 3: Redis 장애**

Redis가 단일 노드면 Redis가 죽으면 Lock도 못 건다. Redis Sentinel이나 Cluster를 쓰면 되긴 하지만, 페일오버 중에 Lock이 꼬일 수 있다.

이걸 해결하려면 Redlock 알고리즘이 있다. Redis 노드 5개에 동시에 Lock을 걸고 과반수(3개) 이상 성공하면 Lock 획득으로 본다. Redisson이 이 구현을 제공한다.

```typescript
// Redlock: 독립된 Redis 노드 3개에 SET NX 시도, 과반수 성공 시 획득
const nodes = [redis1, redis2, redis3];

async function acquireRedlock(key: string, leaseSec: number, waitSec: number): Promise<string | null> {
    const token = randomUUID();
    const deadline = Date.now() + waitSec * 1000;

    while (Date.now() < deadline) {
        const results = await Promise.allSettled(
            nodes.map((r) => r.set(key, token, 'NX', 'EX', leaseSec))
        );
        const acquired = results.filter((r) => r.status === 'fulfilled' && r.value === 'OK').length;
        if (acquired >= Math.floor(nodes.length / 2) + 1) return token;
        // 과반수 실패 시 획득한 락 해제
        await Promise.allSettled(nodes.map((r) => r.eval(unlockScript, 1, key, token)));
        await new Promise((r) => setTimeout(r, 100));
    }
    return null;
}
```

실무에서 Redlock까지 쓰는 경우는 많지 않다. 대부분 Redis Sentinel + ioredis이면 충분하다.

### 분산 락 사용 시 주의사항

**Lock과 트랜잭션 순서:**

```typescript
// 잘못된 순서 - Lock 해제 후 트랜잭션이 아직 커밋되지 않음
async function processBad(): Promise<void> {
    const token = await acquireLock(lockKey, 30, 10);
    if (!token) throw new Error('락 획득 실패');

    // 작업 (트랜잭션 없음, 또는 트랜잭션 시작이 늦음)
    await releaseLock(lockKey, token);  // Lock 해제
    // 이후 DB 커밋 → 다른 서버가 커밋 전 데이터를 볼 수 있음
}
```

Lock을 해제한 후 트랜잭션이 아직 커밋되지 않았다. 다른 서버가 Lock을 획득하면 커밋 전 데이터를 볼 수 있다.

```typescript
// 올바른 순서 - Lock 안에서 트랜잭션 실행
async function processCorrect(): Promise<void> {
    const token = await acquireLock(lockKey, 30, 10);  // Lock 먼저
    if (!token) throw new Error('락 획득 실패');

    try {
        await dataSource.transaction(async (manager) => {
            // 트랜잭션은 Lock 안에서
            await processWithManager(manager);
        });  // 트랜잭션 커밋
    } finally {
        await releaseLock(lockKey, token);  // 트랜잭션 커밋 후 Lock 해제
    }
}
```

Lock 획득 → 트랜잭션 시작 → 작업 → 트랜잭션 커밋 → Lock 해제. 이 순서를 지켜야 한다.

**Lock 키 설계:**

```typescript
// 너무 넓은 범위
`lock:product`  // 모든 상품에 Lock → 병목

// 적절한 범위
`lock:product:${productId}`  // 상품별 Lock

// 더 세밀한 범위
`lock:product:${productId}:stock`  // 재고 변경에만 Lock
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

```typescript
async function createOrder(request: OrderRequest): Promise<void> {
    await dataSource.transaction(async (manager) => {
        const order = manager.create(Order, request);
        await manager.save(order);

        // 검색 인덱싱
        await elasticsearchClient.index(order);  // 실패하면?

        // 이벤트 발행
        await kafkaProducer.send({ topic: 'order-created', messages: [{ value: JSON.stringify(order) }] });  // 실패하면?
    });
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

```typescript
// npm install kafkajs
import { Kafka } from 'kafkajs';

const kafka = new Kafka({ brokers: ['kafka:9092'] });
const consumer = kafka.consumer({ groupId: 'order-cdc-consumer' });

await consumer.connect();
await consumer.subscribe({ topic: 'myapp.mydb.orders', fromBeginning: false });

await consumer.run({
    eachMessage: async ({ message }) => {
        const value = JSON.parse(message.value!.toString());
        const op: string = value.op;
        const after = value.after;

        switch (op) {
            case 'c':  // INSERT
                await elasticsearchService.index(toOrderDocument(after));
                break;
            case 'u':  // UPDATE
                await elasticsearchService.update(toOrderDocument(after));
                break;
            case 'd':  // DELETE
                await elasticsearchService.delete(value.before.id as number);
                break;
        }
    },
});
```

### Outbox 패턴

CDC의 변형이다. 이벤트를 별도 테이블(outbox)에 저장하고, CDC가 이 테이블을 읽어서 Kafka로 보낸다.

**왜 필요한가:**

binlog CDC는 DB의 물리적 변경을 그대로 전달한다. 비즈니스 이벤트와 DB 변경이 1:1로 매핑되지 않는 경우가 있다.

```typescript
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

```typescript
async function createOrder(request: OrderRequest): Promise<void> {
    await dataSource.transaction(async (manager) => {
        const order = manager.create(Order, request);
        await manager.save(order);

        const items = createItems(order, request);
        await manager.save(items);

        // 비즈니스 이벤트를 outbox에 저장 (같은 트랜잭션)
        await manager.query(
            `INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload)
             VALUES ($1, $2, $3, $4)`,
            ['Order', String(order.id), 'OrderCreated', JSON.stringify(OrderCreatedEvent.from(order))]
        );
    });
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

### Node.js Read/Write 분리

**Pool 설정:**

```typescript
import { Pool } from 'pg';

// 쓰기 → Primary
const primaryPool = new Pool({
    host: process.env.DB_PRIMARY_HOST,
    database: 'mydb',
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    max: 10,
});

// 읽기 → Replica
const replicaPool = new Pool({
    host: process.env.DB_REPLICA_HOST,
    database: 'mydb',
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    max: 20,
});

// 라우팅 헬퍼
function getPool(readOnly: boolean): Pool {
    return readOnly ? replicaPool : primaryPool;
}
```

쿼리 실행 시점에 Pool을 선택한다. readOnly 플래그를 명시적으로 넘기거나 AsyncLocalStorage로 컨텍스트에서 결정한다.

**라우팅 구현:**

```typescript
import { AsyncLocalStorage } from 'async_hooks';

const dbContextStorage = new AsyncLocalStorage<{ readOnly: boolean }>();

function getRoutedPool(): Pool {
    const ctx = dbContextStorage.getStore();
    return getPool(ctx?.readOnly ?? false);
}
```

**사용:**

```typescript
// 쓰기 → Primary
async function createOrder(request: OrderRequest): Promise<void> {
    await dbContextStorage.run({ readOnly: false }, async () => {
        const pool = getRoutedPool();
        await pool.query('INSERT INTO orders ...', [...]);
    });
}

// 읽기 → Replica
async function getOrders(userId: number): Promise<Order[]> {
    return dbContextStorage.run({ readOnly: true }, async () => {
        const pool = getRoutedPool();
        const { rows } = await pool.query('SELECT * FROM orders WHERE user_id = $1', [userId]);
        return rows;
    });
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

```typescript
async function createAndReturn(request: OrderRequest): Promise<OrderResponse> {
    // primaryPool을 명시적으로 사용 → 같은 Pool에서 읽음
    const { rows } = await primaryPool.query(
        'INSERT INTO orders (...) VALUES (...) RETURNING *',
        [...]
    );
    return OrderResponse.from(rows[0]);
}
```

**해결 2: 강제 Primary 라우팅**

```typescript
// AsyncLocalStorage로 강제 Primary 설정
async function withForcePrimary<T>(fn: () => Promise<T>): Promise<T> {
    return dbContextStorage.run({ readOnly: false }, fn);
}

function getRoutedPool(): Pool {
    const ctx = dbContextStorage.getStore();
    return getPool(ctx?.readOnly ?? false);
}
```

```typescript
// 주문 생성 직후 조회가 필요한 API
async function getOrderAfterCreate(orderId: number): Promise<OrderResponse> {
    return withForcePrimary(async () => {
        return orderQueryService.getOrder(orderId);
    });
}
```

### 여러 DB 접근 (서비스별 분리)

```typescript
import { Pool } from 'pg';
import { DataSource } from 'typeorm';

// 주문 DB
const orderPool = new Pool({
    host: 'order-db',
    database: 'orders',
    user: 'order_user',
    password: process.env.ORDER_DB_PASSWORD,
});

// 회원 DB
const memberPool = new Pool({
    host: 'member-db',
    database: 'members',
    user: 'member_user',
    password: process.env.MEMBER_DB_PASSWORD,
});

// TypeORM DataSource (서비스별)
const orderDataSource = new DataSource({
    type: 'postgres',
    host: 'order-db',
    database: 'orders',
    entities: [Order, OrderItem],
});

const memberDataSource = new DataSource({
    type: 'postgres',
    host: 'member-db',
    database: 'members',
    entities: [Member],
});

await orderDataSource.initialize();
await memberDataSource.initialize();
```

Member도 같은 방식으로 설정한다. DataSource 인스턴스를 서비스에 주입해서 어떤 DataSource를 쓸지 결정한다.

**주의사항:**

서로 다른 DB에 걸친 트랜잭션은 `@Transactional` 하나로 보장되지 않는다. 주문 DB INSERT 성공 후 회원 DB UPDATE가 실패하면 주문만 남는다. 이런 경우 Saga 패턴이나 보상 트랜잭션을 고려해야 한다. 단순한 경우에는 한쪽 실패 시 수동으로 롤백하는 로직을 넣는 것도 현실적인 방법이다.

## 참고

- HikariCP GitHub: https://github.com/brettwooldridge/HikariCP
- JPA 스펙: https://jakarta.ee/specifications/persistence/
- MySQL 공식 문서: https://dev.mysql.com/doc/
- PostgreSQL 공식 문서: https://www.postgresql.org/docs/
- Redisson GitHub: https://github.com/redisson/redisson
- Debezium 공식 문서: https://debezium.io/documentation/

---
이 문서는 [인덱스와 쿼리 성능 허브](../_hub/인덱스와_쿼리_성능.md)의 일부입니다.

이 문서는 [트랜잭션과 동시성 허브](../_hub/트랜잭션과_동시성.md)의 일부입니다.


