---
title: Rate Limiting & Bulkhead
tags: [nodejs, performance, api, security]
updated: 2026-07-15
---

# Rate Limiting & Bulkhead

## 개요

Rate Limiting은 단위 시간당 요청 수를 제한해서 서버 과부하와 API 남용을 막는다. 인증 엔드포인트, 공개 API 할 것 없이 적용해야 하는 첫 번째 방어선이다.

Bulkhead는 하나의 서비스 장애가 전체 시스템으로 번지지 않도록 격벽을 두는 패턴이다. Rate Limiting이 클라이언트 → 서버 방향의 요청 수를 제어한다면, Bulkhead는 서버 → 외부 의존성 방향의 동시 요청 수를 제어한다. 둘은 방향이 반대지만 장애 격리라는 목적은 같다.

## express-rate-limit의 분산 환경 한계

express-rate-limit을 설치하고 기본 설정으로 쓰면 내부 저장소가 MemoryStore다. 단일 프로세스에서는 잘 동작하지만, `cluster` 모드나 PM2로 여러 인스턴스를 띄우면 문제가 생긴다.

인스턴스 3개가 라운드로빈으로 요청을 나눠받으면 각 인스턴스의 카운터가 독립적으로 돌아간다. 분당 100회 제한이 실질적으로 인스턴스 수만큼 곱해지는 효과가 난다. 분당 300회를 보낸 클라이언트가 429를 받지 않는다.

해결 방법은 Redis를 공유 저장소로 쓰는 것이다.

```javascript
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');
const { createClient } = require('redis');

const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args) => redisClient.sendCommand(args),
  }),
});
```

rate-limit-redis는 내부적으로 Lua 스크립트를 써서 카운터 조회와 증가를 원자적으로 처리한다. ioredis를 쓴다면 `rate-limit-redis`의 `sendCommand` 콜백 대신 ioredis 인스턴스를 넘기는 방식이 다르니 패키지 문서를 확인해야 한다.

## ioredis 연결 장애 시 처리

Redis가 죽으면 Rate Limiting 자체가 실패한다. 이 순간 선택해야 하는 정책이 두 가지다.

**fail-open**: Redis 장애 시 제한을 걸지 않고 요청을 통과시킨다. 서비스 가용성을 우선시한다. 일반 데이터 API에 적합하다.

**fail-closed**: Redis 장애 시 모든 요청을 거부한다. 보안을 우선시한다. 로그인, 비밀번호 재설정처럼 무차별 대입 공격이 실질적 위협인 엔드포인트에 적합하다.

```javascript
const rateLimitMiddleware = (limiter, options = {}) => async (req, res, next) => {
  const { failOpen = true } = options;

  try {
    const key = `ratelimit:${req.ip}`;
    const result = await limiter.checkLimit(key, 100, 60);

    res.setHeader('X-RateLimit-Limit', 100);
    res.setHeader('X-RateLimit-Remaining', result.remaining);
    res.setHeader('X-RateLimit-Reset', Date.now() + result.reset * 1000);

    if (!result.allowed) {
      return res.status(429).json({ error: 'Too many requests', retryAfter: result.reset });
    }

    next();
  } catch (error) {
    console.error('[rate-limit] 저장소 오류:', error.message);

    if (failOpen) {
      return next(); // Redis 장애 시 통과
    }
    return res.status(503).json({ error: 'Service temporarily unavailable' });
  }
};

// 일반 API: fail-open
app.use('/api/data', rateLimitMiddleware(limiter, { failOpen: true }));

// 인증 엔드포인트: fail-closed
app.use('/api/login', rateLimitMiddleware(limiter, { failOpen: false }));
```

ioredis 연결 설정에서 주의할 점이 있다. `enableOfflineQueue`를 기본값(true)으로 두면 Redis 연결이 끊겼을 때 명령이 큐에 쌓인다. 연결이 복구되는 순간 쌓인 명령이 한꺼번에 실행되면서 Rate Limiting 카운터가 갑자기 치솟는 상황이 생긴다.

```javascript
const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: 6379,
  maxRetriesPerRequest: 1,    // 재시도 1회만 하고 빠르게 실패
  connectTimeout: 500,
  enableOfflineQueue: false,  // 오프라인 큐 비활성화
  lazyConnect: true,
});

redis.on('error', (err) => {
  console.error('[ioredis] 연결 오류:', err.message);
});
```

`enableOfflineQueue: false` 설정 시 Redis 연결이 끊기면 명령이 큐에 쌓이지 않고 즉시 에러를 던진다. 위의 fail-open/closed 로직이 이 에러를 받아서 처리한다.

## 알고리즘

### 고정 윈도우 (Fixed Window)

1분 단위로 카운터를 초기화한다. Redis `INCR` 한 번으로 처리 가능해서 구현이 단순하다.

단점은 윈도우 경계에서 버스트가 생긴다. 00:59에 100회, 01:00에 100회가 연속으로 들어오면 실질적으로 2초 안에 200회가 통과한다.

```javascript
async checkLimit(key, limit, windowSeconds) {
  const current = await this.redis.incr(key);

  if (current === 1) {
    await this.redis.expire(key, windowSeconds);
  }

  return {
    allowed: current <= limit,
    remaining: Math.max(0, limit - current),
    reset: await this.redis.ttl(key),
  };
}
```

### 슬라이딩 윈도우 (Sliding Window)

현재 시각 기준으로 과거 N초 동안의 요청 수를 계산한다. Redis Sorted Set을 쓰면 타임스탬프를 score로 저장하고 범위 삭제가 가능하다.

고정 윈도우보다 정확하지만 요청마다 Sorted Set 조작이 일어나서 Redis 부하가 높다. 트래픽이 많은 서비스에서는 주의가 필요하다.

```javascript
async checkLimit(key, limit, windowSeconds) {
  const now = Date.now();
  const windowStart = now - windowSeconds * 1000;

  const pipeline = this.redis.pipeline();
  pipeline.zremrangebyscore(key, 0, windowStart);
  pipeline.zcard(key);
  pipeline.zadd(key, now, `${now}-${Math.random()}`);
  pipeline.expire(key, windowSeconds);

  const results = await pipeline.exec();
  const current = results[1][1];

  if (current >= limit) {
    return { allowed: false, remaining: 0, reset: windowSeconds };
  }

  return { allowed: true, remaining: limit - current - 1, reset: windowSeconds };
}
```

파이프라인으로 묶어도 `zadd`와 `zcard` 사이에 다른 요청이 끼어들 수 있다. 정확도가 중요한 환경에서는 Lua 스크립트로 원자적 처리가 필요하다.

### Token Bucket

버킷에 토큰이 일정 속도로 채워지고 요청마다 토큰을 소비한다. 버킷이 꽉 찬 상태에서 순간적인 버스트를 허용하되 장기 평균 속도를 제한한다. 외부 API 호출처럼 단발성 트래픽 급증은 허용하고 지속적인 과부하는 막고 싶을 때 적합하다.

### Leaky Bucket

요청을 큐에 넣고 일정 속도로 처리한다. 출력 속도가 일정하게 유지된다. 결제 API처럼 초당 처리량을 정확히 제어해야 할 때 쓴다.

## Bulkhead 패턴

특정 외부 서비스가 느려지거나 장애 상태가 되면, 그 서비스를 호출하는 요청들이 계속 쌓인다. Node.js는 싱글 스레드 이벤트 루프라서 스레드 고갈은 없지만, 동시 요청 수를 제한하지 않으면 느린 외부 API 호출이 이벤트 루프에 적체되거나 메모리를 소진할 수 있다.

Bulkhead는 서비스별로 동시 실행 수와 대기 큐 크기를 제한한다. 큐가 가득 차면 즉시 503을 반환해서 다른 서비스로 장애가 번지는 것을 막는다.

```javascript
class Bulkhead {
  constructor(maxConcurrent, maxQueue = 0) {
    this.maxConcurrent = maxConcurrent;
    this.maxQueue = maxQueue;
    this.active = 0;
    this.queue = [];
  }

  async execute(fn) {
    if (this.active >= this.maxConcurrent) {
      if (this.maxQueue > 0 && this.queue.length < this.maxQueue) {
        return new Promise((resolve, reject) => {
          this.queue.push({ fn, resolve, reject });
        });
      }
      const err = new Error('Bulkhead capacity exceeded');
      err.code = 'BULKHEAD_FULL';
      throw err;
    }

    this.active++;
    try {
      return await fn();
    } finally {
      this.active--;
      this._processQueue();
    }
  }

  _processQueue() {
    if (this.queue.length > 0 && this.active < this.maxConcurrent) {
      const { fn, resolve, reject } = this.queue.shift();
      this.execute(fn).then(resolve).catch(reject);
    }
  }
}
```

외부 결제 API 호출에 적용하는 예시다.

```javascript
const paymentBulkhead = new Bulkhead(10, 50); // 동시 10개, 대기 최대 50개
const inventoryBulkhead = new Bulkhead(20, 100); // 다른 서비스는 별도 격벽

app.post('/api/payment', async (req, res, next) => {
  try {
    const result = await paymentBulkhead.execute(() => paymentService.charge(req.body));
    res.json(result);
  } catch (error) {
    if (error.code === 'BULKHEAD_FULL') {
      return res.status(503).json({ error: 'Service temporarily unavailable' });
    }
    next(error);
  }
});
```

`paymentBulkhead`와 `inventoryBulkhead`를 분리하는 것이 핵심이다. 결제 서비스가 느려져서 10개의 동시 요청이 모두 점유되더라도 재고 서비스 호출은 `inventoryBulkhead`의 별도 격벽으로 돌아가기 때문에 영향을 받지 않는다.

## 계층별 Rate Limiting

로그인, 회원가입, 비밀번호 재설정은 일반 데이터 API와 제한값이 달라야 한다. 같은 IP에서 분당 100회 로그인 시도를 허용하면 무차별 대입 공격과 다를 게 없다.

```javascript
const endpointLimits = {
  '/api/login':           { limit: 5,   window: 15 * 60 }, // 15분에 5회
  '/api/register':        { limit: 3,   window: 60 * 60 }, // 1시간에 3회
  '/api/password-reset':  { limit: 3,   window: 60 * 60 }, // 1시간에 3회
  '/api/data':            { limit: 100, window: 60 },       // 1분에 100회
};

app.use(async (req, res, next) => {
  const config = endpointLimits[req.path];
  if (!config) return next();

  const key = `ratelimit:${req.path}:${req.ip}`;
  const result = await limiter.checkLimit(key, config.limit, config.window);

  res.setHeader('X-RateLimit-Limit', config.limit);
  res.setHeader('X-RateLimit-Remaining', result.remaining);
  res.setHeader('X-RateLimit-Reset', Date.now() + result.reset * 1000);

  if (!result.allowed) {
    return res.status(429).json({ error: 'Too many requests', retryAfter: result.reset });
  }

  next();
});
```

인증된 사용자와 비인증 사용자는 키를 분리한다. IP 기반만 쓰면 NAT 뒤에 여러 사용자가 몰릴 때 억울하게 차단되고, 사용자 ID 기반만 쓰면 계정을 여러 개 만들어서 우회하는 경우가 생긴다.

```javascript
function getRateLimitConfig(req) {
  if (req.user) {
    const limits = { free: 100, premium: 1000, enterprise: Infinity };
    return {
      key: `ratelimit:user:${req.user.id}`,
      limit: limits[req.user.plan] ?? 100,
    };
  }
  return {
    key: `ratelimit:ip:${req.ip}`,
    limit: 20,
  };
}
```

## IP 기반 자동 차단

반복적으로 429를 유발하는 IP는 블랙리스트로 올려서 Redis 조회 전에 차단한다.

```javascript
// 블랙리스트 확인 미들웨어 (Rate Limit 미들웨어보다 앞에 위치)
app.use(async (req, res, next) => {
  const blocked = await redis.get(`blacklist:ip:${req.ip}`);
  if (blocked) {
    return res.status(403).json({ error: 'Access denied' });
  }
  next();
});

// Rate Limit 초과 시 위반 횟수 추적
async function trackViolation(ip) {
  const key = `violations:${ip}`;
  const count = await redis.incr(key);
  await redis.expire(key, 3600);

  if (count >= 10) {
    // IP별 키로 관리해야 TTL을 각자 걸 수 있다
    // Set에 sadd로 관리하면 전체 Set에만 expire를 걸 수 있어서 개별 TTL이 안 된다
    await redis.set(`blacklist:ip:${ip}`, '1', 'EX', 3600);
  }
}
```

`blacklist:ips` 같은 Set에 `SADD`로 IP를 모아두는 방식은 개별 TTL을 걸 수 없다. IP마다 `blacklist:ip:{ip}` 키를 별도로 만들고 `EXPIRE`를 거는 방식이 실무에서 더 유연하다.

## 주의사항

express-rate-limit 기본 설정은 단일 프로세스에서만 동작한다. 분산 환경에서는 Redis Store가 필수고, Redis 장애 처리 정책(fail-open/fail-closed)을 엔드포인트 성격에 맞게 결정해야 한다.

ioredis `enableOfflineQueue`는 기본값이 true라서 의도치 않게 큐에 명령이 쌓일 수 있다. Rate Limiting처럼 응답 속도가 중요한 경우 `false`로 설정하고 즉시 실패를 유도하는 것이 낫다.

Bulkhead는 Rate Limiting과 함께 써야 장애 격리가 완성된다. Rate Limiting 없이 Bulkhead만 쓰면 외부에서 오는 요청 폭탄에 무방비이고, Bulkhead 없이 Rate Limiting만 쓰면 내부 서비스 간 장애 전파를 막지 못한다.
