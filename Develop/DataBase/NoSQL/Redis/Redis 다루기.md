---
title: Redis 다루기 — 코드 패턴과 실무 트러블슈팅
tags: [database, nosql, redis, cache]
updated: 2026-03-27
---

# Redis 다루기

> Redis 내부 동작 원리와 아키텍처는 [Redis](Redis.md), 클러스터/센티널/분산락 심화는 [Redis 심화](Redis_Advanced.md) 참고.

---

## CLI 기본 패턴

```bash
# ── String ─────────────────────────────────────────
SET counter 0
INCR counter          # 1 (원자적 증가)
INCRBY counter 5      # 6
DECRBY counter 2      # 4
SET name "Alice" EX 60  # 60초 TTL
GETEX name EX 120       # 조회하면서 TTL 갱신

# ── Hash ───────────────────────────────────────────
HSET product:1 name "노트북" price 1500000 stock 10
HGET product:1 price          # "1500000"
HMGET product:1 name stock    # ["노트북", "10"]
HINCRBY product:1 stock -1    # 재고 감소 (원자적)
HEXISTS product:1 price       # 1

# ── List ───────────────────────────────────────────
RPUSH job:queue task1 task2 task3   # 우측 추가 (큐 IN)
LPOP job:queue                      # 좌측 제거 (큐 OUT) → "task1"
BRPOPLPUSH job:queue processing 0  # 블로킹 이동 (신뢰성 있는 큐)
LRANGE job:queue 0 -1              # 전체 조회
LLEN job:queue                     # 길이

# ── Set ────────────────────────────────────────────
SADD tags:post:1 redis nosql database
SISMEMBER tags:post:1 redis     # 1
SCARD tags:post:1               # 3
SUNION tags:post:1 tags:post:2  # 합집합
SINTER tags:post:1 tags:post:2  # 교집합

# ── Sorted Set ─────────────────────────────────────
ZADD leaderboard NX 1500 "player1"
ZADD leaderboard NX 2000 "player2"
ZINCRBY leaderboard 100 "player1"          # 1600
ZREVRANGE leaderboard 0 4 WITHSCORES      # 상위 5명 (내림차순)
ZRANK leaderboard "player1"               # 순위 (0부터)
ZRANGEBYSCORE leaderboard 1500 2000       # 스코어 범위 조회

# ── 공통 ───────────────────────────────────────────
SCAN 0 MATCH user:* COUNT 100  # 안전한 키 순회 (KEYS * 대신 사용)
TTL session:abc       # 남은 시간 (초)
PERSIST session:abc   # TTL 제거 (영구화)
TYPE product:1        # 데이터 타입 확인
OBJECT ENCODING user:1  # 내부 인코딩 확인
UNLINK large_key      # 비동기 삭제 (DEL 대신 큰 키에 사용)
```

---

## Node.js (ioredis) 패턴

```javascript
const Redis = require('ioredis');

const redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: 6379,
    password: process.env.REDIS_PASSWORD,
    db: 0,
    retryStrategy: (times) => Math.min(times * 50, 2000)
});

// ── Cache Aside ───────────────────────────────────
async function getProduct(productId) {
    const key = `product:${productId}`;
    const cached = await redis.get(key);
    if (cached) return JSON.parse(cached);

    const product = await db.findProduct(productId);
    if (product) await redis.setex(key, 300, JSON.stringify(product));
    return product;
}

async function invalidateProduct(productId) {
    await redis.del(`product:${productId}`);
}

// ── Rate Limiting (Fixed Window) ──────────────────
async function checkRateLimit(userId, limitPerMinute = 60) {
    const key = `ratelimit:${userId}:${Math.floor(Date.now() / 60000)}`;
    const count = await redis.incr(key);
    if (count === 1) await redis.expire(key, 60);
    return count <= limitPerMinute;
}

// ── Pipeline ──────────────────────────────────────
async function getUserDashboard(userId) {
    const pipeline = redis.pipeline();
    pipeline.hgetall(`user:${userId}`);
    pipeline.lrange(`user:${userId}:recent`, 0, 9);
    pipeline.zscore('leaderboard', userId);

    const results = await pipeline.exec();
    return {
        profile: results[0][1],
        recentActivity: results[1][1],
        score: results[2][1]
    };
}

// ── Pub/Sub ───────────────────────────────────────
// publisher
const pub = new Redis();
await pub.publish('order:events', JSON.stringify({
    type: 'ORDER_COMPLETED',
    orderId: 'order-001',
    userId: 'user-123'
}));

// subscriber (별도 커넥션 필수)
const sub = new Redis();
await sub.subscribe('order:events');
sub.on('message', (channel, message) => {
    const event = JSON.parse(message);
    console.log(`Received ${event.type}:`, event);
});
```

---

## Spring Boot 설정 및 패턴

### 기본 설정

```yaml
# application.yml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: 6379
      password: ${REDIS_PASSWORD:}
      timeout: 2000ms
      lettuce:
        pool:
          max-active: 10
          max-idle: 5
          min-idle: 2
```

### ioredis 설정

```typescript
import Redis from 'ioredis';

// ioredis 클라이언트 (기본 JSON 직렬화는 수동으로 처리)
const redis = new Redis({
    host: 'localhost',
    port: 6379,
    retryDelayOnFailover: 100,
    maxRetriesPerRequest: 3,
});

// 헬퍼: JSON 직렬화/역직렬화
export async function cacheGet<T>(redis: Redis, key: string): Promise<T | null> {
    const raw = await redis.get(key);
    return raw ? (JSON.parse(raw) as T) : null;
}

export async function cacheSet(redis: Redis, key: string, value: unknown, ttlSeconds: number): Promise<void> {
    await redis.set(key, JSON.stringify(value), 'EX', ttlSeconds);
}
```

### 캐시 패턴 및 Sorted Set 직접 사용

```typescript
@Injectable()
export class ProductService {
    constructor(
        private readonly redis: Redis,
        private readonly productRepository: ProductRepository,
    ) {}

    async getProduct(id: number): Promise<Product | null> {
        const key = `products:${id}`;
        const cached = await this.redis.get(key);
        if (cached) return JSON.parse(cached) as Product;

        const product = await this.productRepository.findById(id);
        if (product) {
            await this.redis.set(key, JSON.stringify(product), 'EX', 600); // 10분 TTL
        }
        return product ?? null;
    }

    async updateProduct(product: Product): Promise<Product> {
        const saved = await this.productRepository.save(product);
        await this.redis.del(`products:${product.id}`); // 캐시 무효화
        return saved;
    }

    // Sorted Set 직접 사용
    async addScore(userId: string, score: number): Promise<void> {
        await this.redis.zadd('leaderboard', score, userId);
    }

    async getTopRankers(count: number): Promise<string[]> {
        return this.redis.zrevrange('leaderboard', 0, count - 1);
    }
}
```

### 분산 락 (SET NX EX 패턴)

```typescript
// npm install ioredis
// Redis SET NX EX로 분산 락 구현 (Redlock 라이브러리도 사용 가능)

@Injectable()
export class OrderService {
    constructor(private readonly redis: Redis) {}

    async processOrder(orderId: string): Promise<void> {
        const lockKey = `order:lock:${orderId}`;
        const lockValue = crypto.randomUUID();

        // 최대 10초 대기, 30초 후 자동 해제
        const acquired = await this.acquireLock(lockKey, lockValue, 30, 10_000);
        if (!acquired) {
            throw new Error('주문 처리 중');
        }

        try {
            await this.doProcessOrder(orderId);
        } finally {
            await this.releaseLock(lockKey, lockValue);
        }
    }

    private async acquireLock(key: string, value: string, ttlSeconds: number, waitMs: number): Promise<boolean> {
        const deadline = Date.now() + waitMs;
        while (Date.now() < deadline) {
            const result = await this.redis.set(key, value, 'EX', ttlSeconds, 'NX');
            if (result === 'OK') return true;
            await new Promise((res) => setTimeout(res, 50));
        }
        return false;
    }

    private async releaseLock(key: string, value: string): Promise<void> {
        // Lua 스크립트로 값 확인 후 원자적 삭제 (다른 요청의 락을 실수로 해제하지 않기 위해)
        const script = `if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end`;
        await this.redis.eval(script, 1, key, value);
    }
}
```

---

## Cache Stampede 대응

캐시 만료 시점에 수백 개 요청이 동시에 DB를 치는 현상이다. 트래픽이 높은 서비스에서는 반드시 대비해야 한다.

### 뮤텍스 락 방식

캐시가 없으면 락을 잡고, 락을 잡은 하나의 요청만 DB를 조회한다. 나머지 요청은 대기하거나 stale 데이터를 반환한다.

```typescript
@Injectable()
export class CacheService {
    constructor(private readonly redis: Redis) {}

    async getWithMutex(
        key: string,
        loader: () => Promise<string>,
        ttlSeconds: number,
        attempt = 0,
    ): Promise<string> {
        const value = await this.redis.get(key);
        if (value !== null) return value;

        const lockKey = `lock:${key}`;
        // SET NX EX: 키가 없을 때만 설정 + 만료시간 (락 획득)
        const locked = await this.redis.set(lockKey, '1', 'EX', 5, 'NX');

        if (locked === 'OK') {
            try {
                // 락 획득 후 다시 확인 (다른 인스턴스가 이미 갱신했을 수 있음)
                const recheck = await this.redis.get(key);
                if (recheck !== null) return recheck;

                const loaded = await loader();
                await this.redis.set(key, loaded, 'EX', ttlSeconds);
                return loaded;
            } finally {
                await this.redis.del(lockKey);
            }
        }

        // 락 획득 실패: 짧게 대기 후 재시도
        await new Promise((res) => setTimeout(res, 50));
        return this.getWithMutex(key, loader, ttlSeconds, attempt + 1);
    }
}
```

재귀 호출이 깊어지면 문제가 되므로, 실제로는 최대 재시도 횟수를 두거나 stale 데이터를 반환하는 방식을 섞는다.

### 확률적 조기 갱신 (Probabilistic Early Recomputation)

TTL이 완전히 만료되기 전에 확률적으로 미리 갱신한다. "XFetch" 알고리즘이라고도 부른다.

```typescript
/**
 * 캐시 값과 함께 실제 만료 시간을 저장한다.
 * 남은 시간이 짧을수록 갱신 확률이 높아진다.
 */
async getWithEarlyRefresh(
    key: string,
    loader: () => Promise<string>,
    ttlSeconds: number,
): Promise<string> {
    const raw = await this.redis.get(key);
    if (raw !== null) {
        const entry: { value: string; expireAt: number } = JSON.parse(raw);
        const remaining = entry.expireAt - Date.now();
        // delta: DB 조회에 걸리는 예상 시간(ms)
        const delta = 200;
        const beta = 1.0;
        // remaining이 적을수록 갱신 확률이 높아짐
        const shouldRefresh = remaining > 0
            && (delta * beta * -Math.log(Math.random())) >= remaining;

        if (!shouldRefresh) return entry.value;
    }

    const value = await loader();
    const entry = { value, expireAt: Date.now() + ttlSeconds * 1000 };
    await this.redis.set(key, JSON.stringify(entry), 'EX', ttlSeconds + 30);
    return value;
}
```

Redis TTL보다 논리적 만료 시간을 앞당겨 저장하는 게 핵심이다. Redis TTL은 논리적 만료 + 여유 시간(위 예제에서 30초)으로 설정해서, 갱신 중에도 stale 데이터를 제공할 수 있게 한다.

뮤텍스 락 vs 확률적 조기 갱신:
- 뮤텍스 락은 구현이 단순하고 DB 부하를 확실히 막는다. 대신 락 경합이 생기면 응답 지연이 발생한다.
- 확률적 조기 갱신은 락 없이 동작하므로 응답이 빠르다. 대신 간헐적으로 동시 갱신이 발생할 수 있다.
- 트래픽이 매우 높은 키에는 두 방식을 조합하는 경우도 있다.

---

## Hot Key 분산

특정 키에 읽기가 몰리면 해당 Redis 노드만 과부하가 걸린다. 클러스터 환경에서 특히 문제가 된다.

### 로컬 캐시 조합

Hot Key는 애플리케이션 로컬 캐시에 올려서 Redis 요청 자체를 줄인다.

```typescript
import LRU from 'lru-cache';

@Injectable()
export class HotKeyService {
    constructor(private readonly redis: Redis) {}

    // 로컬 LRU 캐시 — Redis 앞단에 둔다
    private readonly localCache = new LRU<string, string>({
        max: 1000,
        ttl: 5_000, // 5초 TTL
    });

    async get(key: string): Promise<string | null> {
        // 1차: 로컬 캐시
        const localValue = this.localCache.get(key);
        if (localValue !== undefined) return localValue;

        // 2차: Redis
        const value = await this.redis.get(key);
        if (value !== null) {
            this.localCache.set(key, value);
        }
        return value;
    }
}
```

주의할 점이 있다. 로컬 캐시 TTL이 길면 인스턴스마다 다른 데이터를 보여줄 수 있다. 일관성이 중요한 데이터에는 TTL을 1~5초 수준으로 짧게 잡아야 한다. Pub/Sub으로 캐시 무효화를 전파하는 방식도 있지만 복잡도가 올라간다.

### 키 샤딩 (Read Replica Spreading)

같은 데이터를 여러 키에 복제해서 읽기를 분산한다.

```typescript
async getSharded(key: string, replicaCount: number): Promise<string | null> {
    // 요청마다 랜덤으로 레플리카 키를 선택
    const shard = Math.floor(Math.random() * replicaCount);
    const shardKey = `${key}:shard:${shard}`;
    return this.redis.get(shardKey);
}

/**
 * 원본 키를 갱신할 때 모든 샤드도 같이 갱신한다.
 * Pipeline으로 묶어서 RTT를 줄인다.
 */
async setSharded(key: string, value: string, replicaCount: number, ttlSeconds: number): Promise<void> {
    const pipeline = this.redis.pipeline();
    for (let i = 0; i < replicaCount; i++) {
        pipeline.set(`${key}:shard:${i}`, value, 'EX', ttlSeconds);
    }
    await pipeline.exec();
}
```

샤드 수를 3~5개로 잡으면 읽기 부하가 그만큼 분산된다. 쓰기 비용은 샤드 수만큼 늘어나므로 읽기 비율이 높은 키에만 쓴다.

---

## Big Key 분리

Hash가 수만 필드, List가 수십만 건이면 DEL 한 번에 수백 ms 블로킹이 발생한다. `MEMORY USAGE` 명령으로 확인해서 10MB 이상이면 분리를 고려한다.

### 진단

```bash
# 특정 키의 메모리 사용량
redis-cli MEMORY USAGE big:hash SAMPLES 0

# 큰 키 찾기 (--bigkeys)
redis-cli --bigkeys
# WARNING: 프로덕션에서는 부하가 있으므로 레플리카에서 실행한다
redis-cli -h replica-host --bigkeys
```

### Hash 분리

필드가 많은 Hash는 prefix로 분리한다.

```typescript
/**
 * user:profile 하나에 100개 필드가 있으면
 * user:profile:0, user:profile:1, ... 으로 나눈다.
 * 필드 이름의 해시값으로 버킷을 결정한다.
 */
function fieldHash(field: string): number {
    let hash = 0;
    for (const ch of field) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
    return Math.abs(hash);
}

async hsetBucketed(key: string, field: string, value: string, bucketCount: number): Promise<void> {
    const bucket = fieldHash(field) % bucketCount;
    await this.redis.hset(`${key}:${bucket}`, field, value);
}

async hgetBucketed(key: string, field: string, bucketCount: number): Promise<string | null> {
    const bucket = fieldHash(field) % bucketCount;
    return this.redis.hget(`${key}:${bucket}`, field);
}
```

### List 분리

시계열 데이터나 로그를 List에 쌓는 경우, 시간 단위로 키를 나눈다.

```typescript
/**
 * log:events에 무한정 쌓는 대신
 * log:events:2026-03-27 같이 날짜별로 분리한다.
 */
async appendLog(baseKey: string, entry: string): Promise<void> {
    const dateKey = `${baseKey}:${new Date().toISOString().slice(0, 10)}`;
    await this.redis.rpush(dateKey, entry);
    // 7일 후 자동 삭제
    await this.redis.expire(dateKey, 7 * 24 * 3600);
}
```

Big Key를 삭제해야 할 때는 반드시 `UNLINK`를 쓴다. `DEL`은 메인 스레드에서 동기적으로 메모리를 해제하므로 그 시간 동안 모든 요청이 멈춘다. `UNLINK`는 백그라운드 스레드에서 해제한다.

---

## 직렬화 패턴

Node.js/ioredis에서는 JSON.stringify/parse를 직접 사용하므로 Spring의 직렬화 이슈가 없다. 단, 타입 안전성과 호환성은 직접 관리해야 한다.

### 타입 안전 캐시 헬퍼

```typescript
// JSON.parse는 추가 필드를 자동으로 무시하므로 필드 추가는 안전하다
// 필드 삭제/타입 변경 시에는 캐시 키 버전을 올린다

export class SimpleCache {
    constructor(private readonly redis: Redis) {}

    async get<T>(key: string): Promise<T | null> {
        const json = await this.redis.get(key);
        if (json === null) return null;
        try {
            return JSON.parse(json) as T;
        } catch {
            // 역직렬화 실패 시 캐시 삭제
            await this.redis.del(key);
            return null;
        }
    }

    async set(key: string, value: unknown, ttlSeconds: number): Promise<void> {
        await this.redis.set(key, JSON.stringify(value), 'EX', ttlSeconds);
    }
}
```

이 방식은 `redis-cli GET`으로 바로 읽을 수 있고, 타입 정보를 JSON에 포함하지 않으므로 구조가 단순하다.

배포 시 주의사항:
1. 새 필드를 추가할 때: JSON.parse가 추가 필드를 무시하므로 안전하다.
2. 기존 필드를 삭제할 때: 코드 배포 후 TTL이 지나면 자연 만료된다. 즉시 무효화가 필요하면 키 버전을 올린다.
3. 필드 타입을 변경하는 경우(number → string 등): 캐시 키 버전을 올리거나 전체 무효화한다.

---

## 모니터링 명령어

```bash
# 서버 상태
redis-cli INFO server | grep redis_version
redis-cli INFO memory | grep -E "used_memory_human|mem_fragmentation_ratio"
redis-cli INFO stats | grep -E "total_commands_processed|instantaneous_ops_per_sec"
redis-cli INFO clients | grep connected_clients

# 슬로우 로그 (10ms 이상)
redis-cli CONFIG SET slowlog-log-slower-than 10000
redis-cli SLOWLOG GET 10

# 실시간 모니터링
redis-cli --stat          # 초당 명령어 통계
redis-cli MONITOR         # 실시간 명령어 스트림 (프로덕션 주의: 부하 발생)

# 키 만료 통계
redis-cli INFO keyspace
# db0:keys=1234,expires=567,avg_ttl=300000

# 큰 키 탐지
redis-cli --bigkeys       # 레플리카에서 실행 권장
```

---

---

## 위 패턴에서 실제로 걸리는 곳

Redis는 명령 하나하나가 원자적이라 안전해 보이는데, **명령 두 개를 이어 붙이는 순간 그 보장이 사라진다.** 위 코드들이 걸리는 지점은 대부분 여기다. 아래는 로컬 Redis 8.2.1 + ioredis에서 확인한 것이다.

### 두 명령 사이에서 프로세스가 죽으면 TTL이 없는 키가 남는다

```javascript
// Rate Limiting (Fixed Window)
const count = await redis.incr(key);
if (count === 1) await redis.expire(key, 60);
```

`INCR` 직후 `EXPIRE` 전에 프로세스가 죽거나 커넥션이 끊기면 그 키는 만료 없이 남는다.

```
INCR 만 하고 EXPIRE 전 TTL = -1   (-1 = 만료 없음)
```

그 사용자는 카운터가 한도를 넘은 채 **영구히 429를 받는다.** 서비스 전체는 멀쩡하고 특정 사용자만 안 되므로 제보가 들어와도 재현이 안 된다. `ProductService`의 `saveAsHash`(HSET → EXPIRE)도 같은 구조고, 이쪽은 캐시가 영구히 남아 만료 갱신이 영영 안 되는 형태가 된다.

두 명령을 하나로 만든다.

```javascript
// 원자적으로: 없으면 만들고 TTL 을 붙인 뒤 증가
const [count] = await redis.eval(
  `local c = redis.call('INCR', KEYS[1])
   if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
   return {c}`,
  1, key, 60
);
```

Hash라면 `HSET` 대신 `HSET` + `EXPIRE`를 파이프라인이 아니라 Lua로 묶는다. 파이프라인은 왕복만 줄일 뿐 원자성을 주지 않는다.

### 파이프라인은 실패를 던지지 않는다

```
results = [
  [0] err= null                                          | val= { f: 'v' }
  [1] err= WRONGTYPE Operation against a key holding...  | val= undefined
  [2] err= WRONGTYPE Operation against a key holding...  | val= undefined
]
```

`getUserDashboard`는 `results[0][1]`, `results[1][1]`, `results[2][1]`만 읽는다. 명령이 실패하면 그 자리가 `undefined`가 되어 **에러 없이 빈 대시보드가 나간다.** `exec()`는 예외를 던지지 않으므로 try/catch로도 안 잡힌다.

```javascript
const results = await pipeline.exec();
const failed = results.filter(([err]) => err);
if (failed.length) logger.warn('pipeline 일부 실패', { count: failed.length, first: failed[0][0].message });
```

`setSharded`처럼 여러 샤드에 같은 값을 쓰는 파이프라인은 특히 중요하다. 일부만 성공하면 샤드마다 다른 값이 남아, 랜덤 선택 결과에 따라 **읽을 때마다 다른 데이터가 나오는** 상태가 된다.

### 분산 락은 TTL보다 오래 걸리는 작업을 막지 못한다

`OrderService.processOrder`는 30초 TTL로 락을 잡는다. `doProcessOrder`가 35초 걸리면 이렇게 된다.

```
t=0    A 락 획득 (TTL 30s)
t=30   락 자동 만료
t=31   B 락 획득 → A 와 B 가 동시에 같은 주문을 처리
t=35   A 종료. releaseLock 의 Lua 가 값을 비교 → B 의 락이라 안 지움 (여기까진 맞다)
```

Lua 해제는 **남의 락을 지우는 것**만 막는다. 두 워커가 겹쳐 도는 것 자체는 못 막는다. 락이 상호 배제를 보장한다고 가정한 로직(재고 차감, 결제 승인)이 그 사이에 두 번 실행된다.

TTL은 "작업이 이 시간 안에 끝난다"는 약속이 아니라 "이 시간이 지나면 죽은 것으로 간주한다"는 선언이다. 세 가지 중 하나를 골라야 한다.

- 작업 시간을 측정해서 TTL을 p99보다 충분히 길게 잡는다
- 작업 중 주기적으로 TTL을 연장한다(watchdog). 단 연장 스레드가 멈추면 같은 문제로 돌아온다
- 락에 의존하지 않고 **최종 쓰기에 조건을 건다** — `UPDATE ... WHERE status = 'PENDING'`처럼. 두 번째 실행이 0 rows affected로 걸러진다

세 번째가 가장 튼튼하다. 락은 경합을 줄이는 최적화로 쓰고, 정합성은 DB 조건으로 지킨다.

`acquireLock`의 재시도 루프도 손볼 곳이 있다. `setTimeout(res, 50)`으로 고정 간격 폴링을 하면 대기 중인 요청들이 같은 타이밍에 몰린다. `50 + Math.random() * 50`처럼 흔들어준다.

### `SCAN`은 중복을 반환할 수 있다

`KEYS` 대신 `SCAN`을 쓰라는 건 맞지만, 두 명령의 결과가 같지는 않다.

- 순회 내내 존재한 키는 **최소 한 번** 반환된다 — 여러 번 나올 수 있다
- 순회 중 생기거나 사라진 키는 나올 수도, 안 나올 수도 있다
- `COUNT`는 힌트라 그 개수를 보장하지 않고, 0건이 돌아와도 커서가 0이 아니면 끝난 게 아니다

그래서 `SCAN` 결과로 개수를 세면 실제보다 많이 나올 수 있다. 삭제 대상을 모을 때도 중복이 섞이므로 Set으로 받는다.

```javascript
const found = new Set();
let cursor = '0';
do {
  const [next, keys] = await redis.scan(cursor, 'MATCH', 'user:*', 'COUNT', 100);
  keys.forEach((k) => found.add(k));
  cursor = next;          // keys 가 비어도 cursor 가 '0' 이 될 때까지 계속한다
} while (cursor !== '0');
```

키 개수를 정확히 알아야 한다면 스캔이 아니라 별도의 Set이나 카운터로 관리한다.

### 진단 명령이 프로덕션을 멈춘다

- `MEMORY USAGE key SAMPLES 0`은 샘플링 없이 **전부** 계산한다. 필드가 수만 개인 Hash에 걸면 그 시간 동안 서버가 멈춘다. Big Key를 찾으려는 명령이 Big Key에서 가장 위험하다. 기본 샘플링(`SAMPLES 5`)으로 먼저 대략을 본다
- `--bigkeys`와 `--hotkeys`는 내부적으로 전체 키를 순회한다. 문서에 적힌 대로 레플리카에서 돌린다
- `MONITOR`는 모든 명령을 스트리밍한다. 처리량이 높은 인스턴스에서는 이것만으로 지연이 올라간다. 붙였다면 반드시 끊는다

`SLOWLOG`에도 한계가 있다. **기록되는 시간은 명령 실행 시간뿐이고, 앞선 명령을 기다린 대기 시간은 포함되지 않는다.** 앞에서 누가 `KEYS *`를 돌리면 뒤의 `GET`들은 실제로 수백 ms를 기다렸는데 슬로우 로그에는 안 남는다. 클라이언트는 느린데 슬로우 로그가 깨끗하다면 이 경우다. 원인 명령 하나(`KEYS`, 큰 `HGETALL`, 무거운 Lua)를 찾으면 나머지가 같이 풀린다.

### 로컬 캐시가 인스턴스마다 다른 값을 보여준다

`HotKeyService`의 LRU 캐시는 TTL 5초다. 인스턴스가 4대면 같은 키에 대해 **최대 5초 동안 서로 다른 값을 응답할 수 있다.** 새로고침할 때마다 값이 왔다 갔다 하는 화면이 여기서 나온다.

가격, 재고, 잔액처럼 사용자가 즉시 확인하는 값에는 쓰지 않는다. 카테고리 목록, 설정값, 배너처럼 몇 초 늦어도 되는 것에만 건다. 무효화 전파(Pub/Sub, Redis Client-side Caching)를 붙일 수는 있지만, 전파 자체가 유실될 수 있으므로 TTL은 여전히 필요하다.

## 참조

- [Redis 명령어 레퍼런스](https://redis.io/commands/)
- [Redis 데이터 타입](https://redis.io/docs/data-types/)
- [ioredis GitHub](https://github.com/redis/ioredis)
- [Spring Data Redis 문서](https://docs.spring.io/spring-data/redis/reference/)
- [Redisson GitHub](https://github.com/redisson/redisson)
