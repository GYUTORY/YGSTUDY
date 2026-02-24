---
title: AWS ElastiCache
tags: [aws, elasticache, redis, memcached, cache, in-memory, performance]
updated: 2026-01-18
---

# AWS ElastiCache

## 개요

ElastiCache는 인메모리 캐시 서비스다. Redis와 Memcached 두 가지 엔진을 지원한다. 데이터를 메모리에 저장해서 밀리초 미만의 응답 속도를 제공한다. 데이터베이스 부하를 줄이고 애플리케이션 성능을 높인다.

### 왜 캐시가 필요한가

데이터베이스에서 매번 데이터를 읽으면 느리다.

**문제 상황:**

**상품 목록 조회:**
쇼핑몰 메인 페이지를 연다. 인기 상품 10개를 보여준다.

```javascript
// 매번 데이터베이스 조회
app.get('/products/popular', async (req, res) => {
  const products = await db.query(
    'SELECT * FROM products ORDER BY views DESC LIMIT 10'
  );
  res.json(products);
});
```

**문제:**
- 매 요청마다 데이터베이스를 조회한다
- 복잡한 쿼리를 실행한다
- 응답 시간: 50-100ms
- 초당 1,000명이 접속하면 데이터베이스에 1,000번 쿼리
- 데이터베이스가 과부하된다

**해결: 캐시 사용**
```javascript
app.get('/products/popular', async (req, res) => {
  // 캐시 확인
  let products = await redis.get('popular_products');
  
  if (products) {
    // 캐시에 있으면 바로 반환
    return res.json(JSON.parse(products));
  }
  
  // 캐시에 없으면 데이터베이스 조회
  products = await db.query(
    'SELECT * FROM products ORDER BY views DESC LIMIT 10'
  );
  
  // 캐시에 저장 (5분 유효)
  await redis.setex('popular_products', 300, JSON.stringify(products));
  
  res.json(products);
});
```

**결과:**
- 첫 요청: 데이터베이스 조회 (50ms)
- 이후 요청: 캐시에서 조회 (1-2ms)
- 5분 동안 데이터베이스 조회 1회
- 데이터베이스 부하 99% 감소
- 응답 속도 25-50배 향상

### 캐시가 유용한 경우

**자주 읽히는 데이터:**
- 상품 정보
- 사용자 프로필
- 설정 값
- 코드 테이블

**계산 비용이 높은 데이터:**
- 통계
- 집계
- 순위

**실시간성이 덜 중요한 데이터:**
- 조회수
- 좋아요 수
- 댓글 수

몇 초 또는 몇 분 지연되어도 괜찮다.

### 캐시가 적합하지 않은 경우

**자주 변경되는 데이터:**
캐시를 계속 갱신해야 한다. 오히려 성능이 나빠진다.

**정확성이 중요한 데이터:**
- 잔액
- 재고
- 결제 정보

캐시와 데이터베이스가 다를 수 있다. 직접 데이터베이스를 조회한다.

## Redis vs Memcached

ElastiCache는 Redis와 Memcached를 지원한다.

### Redis

**특징:**
- 다양한 데이터 타입 (String, List, Set, Hash, Sorted Set)
- 영구 저장 지원 (Persistence)
- 복제 지원 (Replication)
- 자동 장애 조치 (Failover)
- Pub/Sub 메시징
- Lua 스크립트
- 트랜잭션

**사용 사례:**
- 복잡한 데이터 구조
- 고가용성 필요
- 영구 저장 필요
- 실시간 순위
- 세션 스토어
- 메시지 큐

### Memcached

**특징:**
- 단순한 Key-Value
- 멀티스레드
- 수평 확장 쉬움
- 메모리 효율적

**사용 사례:**
- 단순한 캐시
- 매우 높은 처리량
- 영구 저장 불필요
- 멀티코어 활용

### 선택 기준

**Redis를 선택:**
- 복잡한 데이터 타입 필요
- 데이터 영구 저장 필요
- 자동 장애 조치 필요
- 복제 필요
- Pub/Sub 필요

**Memcached를 선택:**
- 단순한 Key-Value만 필요
- 멀티코어를 최대한 활용
- 수평 확장
- 메모리 효율

**대부분의 경우 Redis를 사용한다.** Redis가 기능이 많고 안정적이다.

## Redis 기본 사용

### 연결

```javascript
const Redis = require('ioredis');

const redis = new Redis({
  host: 'my-cluster.cache.amazonaws.com',
  port: 6379,
  password: 'my-password',  // Auth 설정한 경우
  db: 0
});

redis.on('connect', () => {
  console.log('Connected to Redis');
});

redis.on('error', (err) => {
  console.error('Redis error:', err);
});
```

### 기본 명령

**SET / GET:**
```javascript
// 저장
await redis.set('user:123:name', '김철수');

// 조회
const name = await redis.get('user:123:name');
console.log(name);  // '김철수'
```

**만료 시간 설정:**
```javascript
// 10초 후 자동 삭제
await redis.setex('session:abc', 10, 'session_data');

// 또는
await redis.set('session:abc', 'session_data', 'EX', 10);
```

**삭제:**
```javascript
await redis.del('user:123:name');
```

**존재 확인:**
```javascript
const exists = await redis.exists('user:123:name');
console.log(exists);  // 1 (존재) 또는 0 (없음)
```

**TTL 확인:**
```javascript
const ttl = await redis.ttl('session:abc');
console.log(ttl);  // 남은 초 수, -1 (만료 없음), -2 (키 없음)
```

## Redis 데이터 타입

### String

가장 기본적인 타입이다. 문자열이나 숫자를 저장한다.

**숫자 증가/감소:**
```javascript
// 조회수 증가
await redis.incr('product:123:views');

// 10씩 증가
await redis.incrby('product:123:views', 10);

// 감소
await redis.decr('product:123:views');
```

원자적으로 실행된다. 동시에 여러 요청이 와도 정확하다.

### Hash

객체를 저장한다. 필드별로 접근할 수 있다.

```javascript
// 사용자 정보 저장
await redis.hset('user:123', {
  name: '김철수',
  email: 'kim@example.com',
  age: 30
});

// 전체 조회
const user = await redis.hgetall('user:123');
console.log(user);
// { name: '김철수', email: 'kim@example.com', age: '30' }

// 특정 필드 조회
const name = await redis.hget('user:123', 'name');
console.log(name);  // '김철수'

// 필드 하나만 수정
await redis.hset('user:123', 'age', 31);
```

**장점:**
- 객체 전체를 가져오지 않고 필드만 조회 가능
- 메모리 효율적

### List

배열을 저장한다. 양쪽 끝에서 추가/제거할 수 있다.

```javascript
// 오른쪽에 추가 (append)
await redis.rpush('logs', 'log1');
await redis.rpush('logs', 'log2', 'log3');

// 왼쪽에서 제거 (pop)
const log = await redis.lpop('logs');
console.log(log);  // 'log1'

// 범위 조회
const logs = await redis.lrange('logs', 0, -1);
console.log(logs);  // ['log2', 'log3']

// 길이
const len = await redis.llen('logs');
console.log(len);  // 2
```

**사용 사례:**
- 최근 활동 내역
- 작업 큐
- 타임라인

### Set

중복 없는 집합을 저장한다.

```javascript
// 추가
await redis.sadd('tags:123', 'javascript', 'nodejs', 'aws');
await redis.sadd('tags:123', 'javascript');  // 중복, 추가 안 됨

// 조회
const tags = await redis.smembers('tags:123');
console.log(tags);  // ['javascript', 'nodejs', 'aws']

// 포함 확인
const exists = await redis.sismember('tags:123', 'nodejs');
console.log(exists);  // 1 (포함) 또는 0 (미포함)

// 삭제
await redis.srem('tags:123', 'aws');

// 개수
const count = await redis.scard('tags:123');
console.log(count);  // 2
```

**집합 연산:**
```javascript
// 교집합
const common = await redis.sinter('tags:123', 'tags:456');

// 합집합
const all = await redis.sunion('tags:123', 'tags:456');

// 차집합
const diff = await redis.sdiff('tags:123', 'tags:456');
```

**사용 사례:**
- 태그
- 팔로워/팔로잉
- 중복 제거

### Sorted Set

점수와 함께 저장되는 집합이다. 점수 순으로 정렬된다.

```javascript
// 추가 (점수, 값)
await redis.zadd('leaderboard', 1000, 'user_123');
await redis.zadd('leaderboard', 800, 'user_456');
await redis.zadd('leaderboard', 1200, 'user_789');

// 점수 높은 순 (내림차순)
const top = await redis.zrevrange('leaderboard', 0, 2, 'WITHSCORES');
console.log(top);
// ['user_789', '1200', 'user_123', '1000', 'user_456', '800']

// 점수 조회
const score = await redis.zscore('leaderboard', 'user_123');
console.log(score);  // '1000'

// 순위 조회 (0부터 시작)
const rank = await redis.zrevrank('leaderboard', 'user_123');
console.log(rank);  // 1 (2등)

// 점수 증가
await redis.zincrby('leaderboard', 50, 'user_123');
```

**사용 사례:**
- 게임 순위
- 인기 게시물
- 우선순위 큐
- 시간순 정렬

## 캐싱 전략

### Cache-Aside (Lazy Loading)

애플리케이션이 캐시를 직접 관리한다.

**동작:**
1. 캐시에서 조회
2. 있으면 반환
3. 없으면 데이터베이스 조회
4. 캐시에 저장
5. 반환

**코드:**
```javascript
async function getUser(userId) {
  // 1. 캐시 확인
  const cached = await redis.get(`user:${userId}`);
  if (cached) {
    return JSON.parse(cached);
  }
  
  // 2. 데이터베이스 조회
  const user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
  
  // 3. 캐시에 저장 (1시간)
  await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));
  
  return user;
}
```

**장점:**
- 구현이 간단하다
- 캐시가 없어도 동작한다
- 필요한 데이터만 캐시된다

**단점:**
- 첫 요청은 느리다
- 캐시 미스 시 지연
- 데이터 갱신이 느리다

**사용 사례:**
- 읽기 위주 데이터
- 데이터 변경이 적음

### Write-Through

데이터를 쓸 때 캐시도 함께 갱신한다.

**동작:**
1. 데이터베이스에 쓰기
2. 캐시에도 쓰기

**코드:**
```javascript
async function updateUser(userId, userData) {
  // 1. 데이터베이스 업데이트
  await db.query('UPDATE users SET ? WHERE id = ?', [userData, userId]);
  
  // 2. 캐시 업데이트
  const user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
  await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));
  
  return user;
}
```

**장점:**
- 캐시가 항상 최신 상태
- 읽기 성능이 일정함

**단점:**
- 쓰기가 느려진다
- 읽히지 않는 데이터도 캐시됨
- 구현이 복잡하다

### Write-Behind (Write-Back)

캐시에 먼저 쓰고 나중에 데이터베이스에 쓴다.

**동작:**
1. 캐시에 쓰기
2. 비동기로 데이터베이스에 쓰기

**장점:**
- 쓰기가 매우 빠르다
- 데이터베이스 부하 감소

**단점:**
- 데이터 손실 가능 (캐시만 쓰고 서버 죽으면)
- 구현이 복잡하다
- 일관성 문제

**사용 사례:**
- 쓰기가 매우 많음
- 약간의 데이터 손실 허용
- 통계, 로그

### Cache Invalidation (캐시 무효화)

데이터가 변경되면 캐시를 삭제한다.

**코드:**
```javascript
async function updateUser(userId, userData) {
  // 1. 데이터베이스 업데이트
  await db.query('UPDATE users SET ? WHERE id = ?', [userData, userId]);
  
  // 2. 캐시 삭제
  await redis.del(`user:${userId}`);
}
```

다음 조회 시 캐시 미스가 발생한다. 데이터베이스에서 읽고 캐시에 저장한다.

**장점:**
- 구현이 간단하다
- 항상 최신 데이터

**단점:**
- 캐시 미스 증가
- 첫 요청이 느리다

## 세션 스토어

사용자 세션을 Redis에 저장한다.

### Express Session

```javascript
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const Redis = require('ioredis');

const redis = new Redis({
  host: 'my-cluster.cache.amazonaws.com',
  port: 6379
});

app.use(session({
  store: new RedisStore({ client: redis }),
  secret: 'my-secret',
  resave: false,
  saveUninitialized: false,
  cookie: {
    maxAge: 1000 * 60 * 60 * 24  // 1일
  }
}));

// 세션 사용
app.get('/profile', (req, res) => {
  if (!req.session.userId) {
    return res.status(401).json({ error: 'Not authenticated' });
  }
  
  res.json({ userId: req.session.userId });
});

app.post('/login', async (req, res) => {
  const user = await authenticateUser(req.body);
  req.session.userId = user.id;
  res.json({ success: true });
});
```

**장점:**
- 여러 서버에서 세션 공유
- 빠른 조회
- 자동 만료

## 고가용성

### Replication (복제)

Primary 노드의 데이터를 Replica 노드에 복제한다.

**구성:**
- Primary 1개
- Replica 1-5개

**동작:**
- 쓰기: Primary에만
- 읽기: Primary 또는 Replica

**장애 조치:**
Primary가 죽으면 Replica 중 하나가 Primary로 승격된다. 자동으로 처리된다.

### Cluster Mode

데이터를 여러 노드에 분산한다. 샤딩이다.

**샤드:**
데이터를 나누는 단위다. 각 샤드는 Primary와 Replica를 가진다.

**예시:**
- 샤드 3개
- 각 샤드에 Primary 1개 + Replica 1개
- 총 6개 노드

**데이터 분산:**
Key를 해시해서 샤드를 결정한다. 자동으로 분산된다.

**장점:**
- 메모리 용량 증가
- 처리량 증가
- 수평 확장

**단점:**
- 멀티 키 연산 제약
- 트랜잭션 제약

### Multi-AZ

여러 가용 영역에 노드를 배치한다.

**구성:**
- Primary: us-west-2a
- Replica: us-west-2b

가용 영역 하나가 죽어도 서비스가 유지된다.

## 모니터링

### CloudWatch 메트릭

**주요 메트릭:**
- **CPUUtilization**: CPU 사용률
- **EngineCPUUtilization**: Redis 프로세스 CPU
- **DatabaseMemoryUsagePercentage**: 메모리 사용률
- **CacheHits**: 캐시 히트 수
- **CacheMisses**: 캐시 미스 수
- **Evictions**: 메모리 부족으로 삭제된 키 수

**캐시 히트율:**
```
Hit Rate = CacheHits / (CacheHits + CacheMisses)
```

80% 이상이 좋다. 50% 미만이면 캐시가 제대로 동작하지 않는다.

**Evictions:**
메모리가 부족해서 키를 삭제한다. 0이 좋다. 증가하면 메모리를 늘려야 한다.

### 알람 설정

**메모리 사용률:**
```json
{
  "MetricName": "DatabaseMemoryUsagePercentage",
  "Threshold": 80,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

80%를 넘으면 알림을 받는다. 메모리를 늘리거나 불필요한 키를 삭제한다.

**Evictions:**
```json
{
  "MetricName": "Evictions",
  "Threshold": 1000,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

1,000개 이상 삭제되면 알림을 받는다.

## 실무 주의사항

### 만료 시간 설정

모든 키에 TTL을 설정한다. 메모리 누수를 방지한다.

```javascript
// Bad
await redis.set('user:123', userData);

// Good
await redis.setex('user:123', 3600, userData);
```

만료 시간이 없으면 메모리가 계속 증가한다.

### Key 네이밍

일관된 패턴을 사용한다.

```javascript
// 좋은 예
'user:{id}:profile'
'product:{id}:views'
'session:{sessionId}'

// 나쁜 예
'user_123'
'product-views-456'
'sess_abc'
```

콜론(`:`)으로 구분한다. 계층 구조를 만든다. 디버깅이 쉽다.

### 큰 값 저장 피하기

Redis는 단일 스레드다. 큰 값을 읽고 쓰면 다른 요청이 블록된다.

**권장:**
- 값 크기: 100KB 이하
- 큰 데이터는 S3에 저장하고 URL만 캐시

### 동시성 문제

여러 요청이 동시에 캐시를 갱신할 수 있다.

**문제:**
```javascript
// 두 요청이 동시에 실행
const value = await redis.get('counter');
await redis.set('counter', parseInt(value) + 1);
```

동시에 실행되면 값이 잘못된다.

**해결: Atomic 연산**
```javascript
await redis.incr('counter');
```

원자적으로 실행된다. 동시성 문제가 없다.

### Thundering Herd

캐시가 만료되는 순간 수천 개의 요청이 데이터베이스로 간다.

**문제:**
- 캐시 TTL: 1시간
- 오후 3시에 캐시 생성
- 오후 4시에 캐시 만료
- 동시에 1,000개 요청이 데이터베이스로

**해결 1: TTL 랜덤화**
```javascript
const ttl = 3600 + Math.floor(Math.random() * 300);  // 1시간 ± 5분
await redis.setex(key, ttl, value);
```

캐시 만료 시간을 분산한다.

**해결 2: Locking**
```javascript
async function getWithLock(key, fetchFn) {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);
  
  // 락 획득 시도
  const lockKey = `lock:${key}`;
  const locked = await redis.set(lockKey, '1', 'EX', 10, 'NX');
  
  if (locked) {
    // 락을 획득한 요청만 데이터베이스 조회
    const value = await fetchFn();
    await redis.setex(key, 3600, JSON.stringify(value));
    await redis.del(lockKey);
    return value;
  } else {
    // 락을 획득하지 못한 요청은 대기
    await sleep(100);
    return getWithLock(key, fetchFn);
  }
}
```

한 요청만 데이터베이스를 조회한다. 나머지는 대기한다.

## 비용 최적화

### 적절한 인스턴스 타입

**노드 타입:**
- **cache.t4g.micro**: 개발/테스트 (0.5GB)
- **cache.t4g.small**: 소규모 (1.5GB)
- **cache.r7g.large**: 중규모 (13GB)
- **cache.r7g.xlarge**: 대규모 (26GB)

처음에는 작은 타입으로 시작한다. 메모리 사용률을 확인하고 필요하면 확장한다.

### Reserved Nodes

1년 또는 3년 예약하면 할인을 받는다.

**할인율:**
- 1년: 약 30-40% 할인
- 3년: 약 50-60% 할인

프로덕션 환경에서는 Reserved Nodes를 구매한다.

### Eviction Policy

메모리가 부족할 때 어떤 키를 삭제할지 정한다.

**정책:**
- **allkeys-lru**: 가장 오래 사용하지 않은 키 삭제 (권장)
- **volatile-lru**: TTL이 있는 키 중 LRU 삭제
- **allkeys-random**: 무작위 삭제
- **noeviction**: 삭제 안 함 (쓰기 거부)

보통 `allkeys-lru`를 사용한다.

## Memcached 사용

Memcached는 더 단순하다.

### 기본 사용

```javascript
const Memcached = require('memcached');

const memcached = new Memcached('my-cluster.cache.amazonaws.com:11211');

// 저장 (키, 값, 만료 시간)
memcached.set('user:123', { name: '김철수' }, 3600, (err) => {
  if (err) console.error(err);
});

// 조회
memcached.get('user:123', (err, data) => {
  if (err) console.error(err);
  console.log(data);
});

// 삭제
memcached.del('user:123', (err) => {
  if (err) console.error(err);
});
```

### 차이점

**Memcached:**
- String만 지원
- 영구 저장 없음
- 복제 없음
- 자동 장애 조치 없음
- 최대 1MB per item

**사용 사례:**
- 단순한 캐시
- 일시적인 데이터
- 손실되어도 괜찮은 데이터

## 참고

- AWS ElastiCache 개발자 가이드: https://docs.aws.amazon.com/elasticache/
- Redis 명령어: https://redis.io/commands/
- ElastiCache 요금: https://aws.amazon.com/elasticache/pricing/
- 캐싱 전략: https://aws.amazon.com/caching/best-practices/

