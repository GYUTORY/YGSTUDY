---
title: 대량의 API를 처리하는 방법
tags: [network, 7-layer, application-layer, http, 대량의-api를-처리하는-방법, redis, caching, load-balancing, aws, ecs, rds-proxy, elasticache, alb]
updated: 2025-12-26
---

# 대량의 API를 처리하는 방법

## 배경

현대의 웹 서비스는 초당 수만, 수십만 건의 API 요청을 처리해야 하는 상황에 직면한다.

### 실제 사례

| 서비스 유형 | 처리 규모 | 주요 도전 과제 |
|------------|----------|--------------|
| 소셜 미디어 | 수억 명 동시 접속 | 피드 조회, 실시간 알림 |
| 전자상거래 | 초당 수십만 건 요청 | 세일 기간 트래픽 급증 |
| 금융 서비스 | 실시간 거래 처리 | 정확성과 속도 동시 보장 |
| 게임 서버 | 수백만 명 동시 플레이 | 실시간 상호작용, 낮은 지연시간 |

**실무 팁:**
대용량 트래픽을 효율적으로 처리하기 위해서는 단순한 서버 증설을 넘어 아키텍처 수준의 최적화가 필요하다.

## 대용량 API 처리의 도전 과제

대규모 API 서비스를 운영할 때 직면하는 주요 문제들이다.

### 트래픽 급증 (Traffic Spike)

**문제 상황:**
```
정상 상태: 초당 1,000건 요청
   ↓
이벤트 발생 (예: 세일, 티켓팅)
   ↓
급증: 초당 100,000건 요청 (100배!)
```

**발생하는 문제:**

| 문제 | 증상 | 영향 |
|------|------|------|
| 응답 지연 | 100ms → 10,000ms | 사용자 경험 저하 |
| 연결 거부 | Connection Refused | 서비스 이용 불가 |
| 타임아웃 | Request Timeout | 사용자 이탈 증가 |
| 서버 다운 | 500 Internal Error | 전체 서비스 중단 |

**실무 팁:**
트래픽 급증에 대비해 Auto Scaling과 로드 밸런서를 구성한다.

### 데이터베이스 병목 현상

**일반적인 시나리오:**
```
사용자 요청 → API 서버 → 데이터베이스
                ↓           ↓
          응답 빠름      응답 느림 (병목!)
```

**성능 차이:**

| 저장소 타입 | 응답 시간 | 상대적 속도 |
|------------|----------|------------|
| 메모리 (RAM) | 0.1μs | 기준 |
| SSD | 0.1ms | 1,000배 느림 |
| HDD | 5-10ms | 50,000~100,000배 느림 |

**실무 팁:**
데이터베이스 병목을 해결하기 위해 캐싱과 읽기 전용 복제본을 사용한다.

### 외부 API 의존성

**발생하는 문제:**
```
내부 API → 외부 API 호출
    ↓           ↓
  빠름      느리거나 장애
    ↓
전체 서비스 지연/장애
```

**주요 리스크:**

- 네트워크 지연: 50-200ms 추가 지연
- Rate Limit: API 호출 횟수 제한
- 장애 전파: 외부 API 다운 → 전체 서비스 영향
- 비용 증가: 호출 횟수에 따른 과금

**실무 팁:**
외부 API 호출은 타임아웃과 재시도 로직을 구현한다. Circuit Breaker 패턴을 사용한다.

### 동시성 문제 (Race Condition)

**전형적인 예시:**
```
시간축 →

T1: 사용자 A가 재고 확인 (재고: 1개)
T2: 사용자 B가 재고 확인 (재고: 1개) ← 아직 A가 차감 전
T3: 사용자 A 주문 완료 (재고: 0개)
T4: 사용자 B 주문 완료 (재고: -1개) (문제 발생)
```

**해결 방법:**
- 분산 락 (Distributed Lock) 사용
- 원자적 연산 (Atomic Operation) 활용
- 낙관적 잠금 (Optimistic Locking) 구현

**실무 팁:**
Redis의 분산 락을 사용하면 동시성 문제를 해결할 수 있다.

## 클러스터 아키텍처

여러 대의 컴퓨터(노드)를 결합하여 단일 시스템처럼 동작하게 만드는 분산 시스템이다.

### 클러스터의 주요 가치

| 특징 | 설명 | 효과 |
|------|------|------|
| 고가용성 | 시스템 장애 시에도 서비스 지속 | 99.99% 가동률 |
| 확장성 | 필요에 따라 노드 추가/제거 | 유연한 리소스 관리 |
| 성능 향상 | 병렬 처리로 전체 성능 향상 | 처리량 N배 증가 |

**실무 팁:**
클러스터 구성 시 로드 밸런서와 헬스 체크를 필수로 구성한다.

---

### 고가용성 구성 방식

#### Active-Active 구성

```
          로드 밸런서
              │
    ┌─────────┼─────────┐
    │         │         │
  서버1     서버2     서버3
  (Active) (Active) (Active)
   100%     100%     100%
```

**장점:**
- 모든 서버가 동시에 트래픽 처리
- 한 서버 장애 시 다른 서버로 자동 전환
- 최대 리소스 활용 (100% 활용률)

**단점:**
- 세션 공유 필요
- 데이터 동기화 복잡

---

#### Active-Standby 구성

```
  Primary Server    Standby Server
      (Active)        (대기 중)
       100%              0%
         │                │
         └────────────────┘
       (Heartbeat 체크)
```

**장점:**
- 즉시 장애 복구
- 데이터 일관성 유지 용이
- 안정적인 Failover

**단점:**
- 리소스 낭비 (Standby 서버 유휴)
- 비용 증가

---

### 확장 전략

#### 수직 확장 vs 수평 확장

| 비교 항목 | 수직 확장 (Scale Up) | 수평 확장 (Scale Out) |
|----------|-------------------|---------------------|
| **방법** | CPU/RAM 업그레이드 | 서버 대수 증가 |
| **비용** | 비선형 증가 💰💰💰 | 선형 증가 💰 |
| **한계** | 물리적 한계 있음 | 거의 무제한 |
| **유연성** | 낮음 (교체 필요) | 높음 (추가/제거 자유) |
| **복잡도** | 낮음 | 높음 (분산 처리) |

#### 수평 확장 시나리오

```
초기:
[서버1] 
처리량: 1,000 req/s
   ↓
트래픽 3배 증가:
[서버1][서버2][서버3]
처리량: 3,000 req/s (3배)
   ↓
추가 확장:
[서버1][서버2][서버3][서버4][서버5]
처리량: 5,000 req/s (5배)
```

**결론:** 대부분의 현대 웹 서비스는 수평 확장을 선호한다.

**실무 팁:**
수평 확장은 서버를 추가하여 처리 능력을 증가시킨다. 수직 확장보다 비용 효율적이다.

---

### 샤딩 (Sharding)

데이터를 여러 노드에 분산 저장하여 부하를 분산시킨다.

**실무 팁:**
샤딩은 데이터를 여러 노드에 분산시킨다. 해시 기반 샤딩은 균등 분산에 유리하다.

```javascript
// 해시 기반 샤딩
function getShardKey(userId) {
  return userId % 4; // 4개의 샤드로 분산
}

// 사용자 ID가 123인 경우
const shardKey = 123 % 4; // = 3
// → Shard 3에 데이터 저장
```

#### 샤딩 전략 비교

| 전략 | 방식 | 장점 | 단점 | 적합한 경우 |
|------|------|------|------|------------|
| **해시 샤딩** | `userId % N` | 균등 분산 | 확장 시 재배치 | 균등한 분산이 중요한 경우 |
| **범위 샤딩** | `0-1000`, `1001-2000` | 간단한 구현 | 핫스팟 위험 | 순차적 데이터 |
| **지역 기반** | 지리적 위치 | 낮은 지연시간 | 불균등 분산 | 글로벌 서비스 |

---

## Redis 없이 직접 API 호출 시 문제점

캐싱 없이 직접 데이터베이스나 외부 API를 호출할 때 발생하는 문제들이다.

### 1. 부하 집중 및 서버 과부하

**시나리오:**
```
1,000명의 사용자가 동시에 같은 상품 정보 요청
  ↓
API 서버가 1,000번 데이터베이스 조회
  ↓
데이터베이스 연결 고갈 (Connection Pool Exhausted)
  ↓
서버 타임아웃 또는 다운
```

**실제 영향:**
- **응답 시간**: 100ms → 10,000ms (100배 증가)
- **CPU 사용률**: 30% → 100%
- **메모리 사용**: 정상 → OOM (Out of Memory)
- **연결 대기**: 수천 개의 요청이 큐에 대기

### 2. 확장성 제한

**문제:**
서버를 증설해도 데이터베이스가 병목이 되면 효과가 제한적이다.

**실무 팁:**
데이터베이스 병목을 해결하기 위해 캐싱과 읽기 전용 복제본을 사용한다.

```
AS-IS:
[API 서버 1대] → [DB] ← 병목 발생

TO-BE (비효율적):
[API 서버 10대] → [DB] ← 여전히 병목
```

**비용 증가:**
- 서버 10배 증설 → 성능은 2배만 향상
- ROI(투자 대비 효과) 급격히 감소

### 3. 데이터 불일치 문제

**동시성 문제 예시:**

```javascript
// 사용자 A와 B가 동시에 포인트 차감
// 현재 포인트: 1000

// 사용자 A의 요청
const pointsA = await db.query('SELECT points FROM users WHERE id = 1');
// pointsA = 1000
await sleep(100); // 처리 지연
await db.query('UPDATE users SET points = ? WHERE id = 1', [pointsA - 500]);
// 최종: 500

// 사용자 B의 요청 (동시 진행)
const pointsB = await db.query('SELECT points FROM users WHERE id = 1');
// pointsB = 1000 (아직 A의 업데이트 전)
await db.query('UPDATE users SET points = ? WHERE id = 1', [pointsB - 300]);
// 최종: 700 ← B의 업데이트가 A를 덮어씀!

// 실제 결과: 700 (예상: 200)
```

### 4. 중복 호출 및 비용 낭비

**외부 API 호출 예시:**

```javascript
// 환율 정보를 외부 API에서 조회
// 100명이 동시에 USD → KRW 환율 조회

for (let i = 0; i < 100; i++) {
  const rate = await externalAPI.getExchangeRate('USD', 'KRW');
  // 동일한 데이터를 100번 조회!
}

// 문제점:
// 1. 외부 API 호출 비용: $0.001 × 100 = $0.10
// 2. 네트워크 지연: 200ms × 100 = 20초
// 3. Rate Limit 도달 위험
```

### 5. Thundering Herd 문제

캐시가 만료되는 순간 대량의 요청이 동시에 DB로 몰리는 현상:

```
T=0: 캐시 만료
T=0.001: 1000개 요청 동시 도착
         ↓
    모두 캐시 미스
         ↓
    1000개 DB 쿼리 동시 실행
         ↓
    데이터베이스 과부하!
```

---

## Redis를 활용한 해결 방법

### Redis란?

**Redis (REmote DIctionary Server)**는 인메모리 데이터 구조 저장소로, 대량 API 처리에 사용되는 솔루션이다.

**실무 팁:**
Redis는 인메모리 저장소로 매우 빠르다. 캐싱, 세션 저장, 분산 락 등에 사용한다.

---

### 주요 특징

#### 인메모리 기반 - 빠른 속도

| 저장소 | 처리량 | 응답 시간 |
|--------|--------|----------|
| **디스크 DB** | 10,000 read/s | 5-10ms |
| **Redis** | 100,000+ read/s | 0.1-1ms |

**성능 차이:** Redis는 디스크 DB보다 10배 이상 빠르다.

---

#### 다양한 데이터 구조

| 데이터 구조 | 용도 | 사용 예시 |
|-----------|------|----------|
| **String** | 단순 키-값 | 세션, 캐시 |
| **Hash** | 객체 저장 | 사용자 정보 |
| **List** | 큐, 스택 | 작업 큐, 최근 항목 |
| **Set** | 중복 제거 | 좋아요, 태그 |
| **Sorted Set** | 순위 | 리더보드, 랭킹 |
| **Bitmap** | 불린 배열 | 출석 체크, 상태 플래그 |
| **HyperLogLog** | 카디널리티 | 순 방문자 수 추정 |

---

#### 원자적 연산 (Atomic Operations)

```redis
# 동시성 문제를 원자적으로 해결
INCR counter              # 원자적 증가 (조회수, 좋아요)
DECR counter              # 원자적 감소 (재고 차감)
SETNX key value           # 존재하지 않을 때만 설정 (분산 락)
HINCRBY user:123 points 10 # 특정 필드만 증가
```

### Redis가 대량 API 처리에 적합한 이유

#### 1. 극도로 빠른 응답 속도

**성능 비교:**
```
MySQL 쿼리:     10-50ms
Redis 조회:     0.1-1ms (10배 ~ 500배 빠름)
```

**실제 영향:**
```
1,000건 조회 시:
MySQL: 10ms × 1,000 = 10,000ms (10초)
Redis: 0.1ms × 1,000 = 100ms (0.1초)
```

#### 2. 캐싱을 통한 부하 감소

**캐시 히트율에 따른 효과:**
```
캐시 히트율 90% 가정:
  100,000 요청
    ↓
  90,000 요청 → Redis (0.1ms)
  10,000 요청 → DB (10ms)
    ↓
  총 처리 시간: 90 + 100,000 = 100,090ms

캐시 없이:
  100,000 요청 → DB (10ms)
    ↓
  총 처리 시간: 1,000,000ms (10배 이상 차이!)
```

#### 3. 분산 락 (Distributed Lock)

**동시성 제어:**
```javascript
// Redis를 사용한 분산 락
const lock = await redis.set('lock:user:123', 'locked', 'NX', 'EX', 10);

if (lock) {
  try {
    // 임계 영역: 동시에 한 프로세스만 실행
    const points = await redis.get('user:123:points');
    await redis.set('user:123:points', points - 100);
  } finally {
    await redis.del('lock:user:123');
  }
}
```

#### 4. Pub/Sub를 통한 실시간 통신

**실시간 알림 시스템:**
```javascript
// Publisher
await redis.publish('notifications', JSON.stringify({
  userId: 123,
  message: '새로운 메시지가 도착했습니다'
}));

// Subscriber
await redis.subscribe('notifications', (message) => {
  const data = JSON.parse(message);
  sendPushNotification(data.userId, data.message);
});
```

#### 5. 메시지 큐로 활용

**비동기 작업 처리:**
```javascript
// 작업을 큐에 추가
await redis.lpush('job:queue', JSON.stringify({
  type: 'sendEmail',
  to: 'user@example.com',
  subject: '환영합니다'
}));

// 워커가 작업 처리
while (true) {
  const job = await redis.brpop('job:queue', 0);
  await processJob(JSON.parse(job[1]));
}
```

---

## Redis 캐싱 전략

애플리케이션의 특성에 맞는 캐싱 전략을 선택하는 것이 중요하다.

**실무 팁:**
캐싱 전략은 데이터 특성에 따라 선택한다. 읽기가 많으면 Cache-Aside, 일관성이 중요하면 Write-Through를 사용한다.

### 전략 비교표

| 전략 | 읽기 성능 | 쓰기 성능 | 일관성 | 복잡도 | 적합한 경우 |
|------|----------|----------|--------|--------|------------|
| **Cache-Aside** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | 읽기 위주 |
| **Write-Through** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | 일관성 중요 |
| **Write-Behind** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | 쓰기 많음 |
| **Refresh-Ahead** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 예측 가능 |

---

### Cache-Aside (Lazy Loading)

**개념:** 애플리케이션이 캐시를 직접 관리하는 가장 일반적인 패턴이다.

**동작 흐름:**
```javascript
async function getUser(userId) {
  // 1. 캐시 확인
  let user = await redis.get(`user:${userId}`);
  
  if (user) {
    return JSON.parse(user); // 캐시 히트
  }
  
  // 2. 캐시 미스 - DB 조회
  user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
  
  // 3. 캐시에 저장
  await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));
  
  return user;
}
```

**장점:**
- 구현이 간단하고 직관적
- 필요한 데이터만 캐시에 저장 (메모리 효율적)
- 캐시 장애 시에도 서비스 가능 (DB로 Fallback)

**단점:**
- 첫 요청은 느림 (캐시 미스)
- 캐시와 DB 간 불일치 가능성

**적합한 경우:**
- 읽기가 많은 시스템
- 데이터 변경이 자주 없는 경우
- 예: 상품 정보, 게시글 조회

---

### Write-Through

**개념:** 쓰기 시 캐시와 DB를 동시에 업데이트한다.

```javascript
async function updateUser(userId, data) {
  // 1. DB 업데이트
  await db.query('UPDATE users SET name = ? WHERE id = ?', [data.name, userId]);
  
  // 2. 캐시 업데이트
  await redis.setex(`user:${userId}`, 3600, JSON.stringify(data));
  
  return data;
}
```

**장점:**
- 캐시와 DB 일관성 유지
- 읽기 성능 최적화
- 캐시 워밍 효과

**단점:**
- 쓰기 지연 시간 증가 (두 번 저장)
- 사용하지 않는 데이터도 캐시에 저장

**적합한 경우:**
- 데이터 일관성이 중요한 시스템
- 읽기 비중이 매우 높은 경우
- 예: 설정 정보, 메타데이터

---

### Write-Behind (Write-Back)

**개념:** 캐시에만 먼저 쓰고, 나중에 비동기로 DB에 반영한다.

```javascript
async function updateUserPoints(userId, points) {
  // 1. 캐시에만 즉시 업데이트
  await redis.incrby(`user:${userId}:points`, points);
  
  // 2. 변경 내역을 큐에 추가
  await redis.lpush('update:queue', JSON.stringify({
    type: 'updatePoints',
    userId,
    points
  }));
  
  // 3. 백그라운드 워커가 주기적으로 DB 업데이트
}

// 백그라운드 워커
setInterval(async () => {
  const updates = await redis.lrange('update:queue', 0, 99);
  
  for (const update of updates) {
    const data = JSON.parse(update);
    await db.query('UPDATE users SET points = points + ? WHERE id = ?', 
                   [data.points, data.userId]);
  }
  
  await redis.ltrim('update:queue', updates.length, -1);
}, 5000); // 5초마다 실행
```

**장점:**
- 쓰기 성능 극대화
- 대량 업데이트 시 DB 부하 감소 (배치 처리)
- 즉각적인 응답

**단점:**
- 캐시 장애 시 데이터 손실 위험
- 구현 복잡도 높음
- 일시적 데이터 불일치

**적합한 경우:**
- 쓰기가 매우 많은 시스템
- 예: 조회수, 좋아요 수, 실시간 통계
- 일시적 데이터 손실을 허용할 수 있는 경우

---

### Refresh-Ahead

**개념:** 캐시 만료 전에 미리 갱신하여 항상 최신 데이터를 제공한다.

```javascript
async function getProductWithRefresh(productId) {
  const cacheKey = `product:${productId}`;
  const ttl = await redis.ttl(cacheKey);
  
  let product = await redis.get(cacheKey);
  
  // TTL이 5분 미만이면 백그라운드에서 갱신
  if (ttl < 300) {
    // 비동기로 갱신 (요청은 즉시 반환)
    refreshCache(productId).catch(console.error);
  }
  
  if (!product) {
    product = await db.query('SELECT * FROM products WHERE id = ?', [productId]);
    await redis.setex(cacheKey, 3600, JSON.stringify(product));
  }
  
  return JSON.parse(product);
}

async function refreshCache(productId) {
  const product = await db.query('SELECT * FROM products WHERE id = ?', [productId]);
  await redis.setex(`product:${productId}`, 3600, JSON.stringify(product));
}
```

**장점:**
- Thundering Herd 문제 방지
- 항상 최신 데이터 제공
- 예측 가능한 성능

**단점:**
- 예측 로직 필요 (어떤 데이터를 미리 갱신할지)
- 불필요한 갱신 가능성
- 추가 리소스 사용

**적합한 경우:**
- 예측 가능한 액세스 패턴
- 캐시 만료로 인한 지연을 피해야 하는 경우
- 예: 인기 상품, 실시간 랭킹

---

### Cache Stampede 방지 전략

**Stampede 문제:**
```
캐시 만료 시점에 1000개 요청 동시 도착
  ↓
모두 DB 접근 시도
  ↓
DB 과부하!
```

**해결 방법: 분산 락 사용**
```javascript
async function getDataWithLock(key) {
  let data = await redis.get(key);
  
  if (data) {
    return JSON.parse(data);
  }
  
  // 락 획득 시도
  const lockKey = `lock:${key}`;
  const lockAcquired = await redis.set(lockKey, '1', 'NX', 'EX', 10);
  
  if (lockAcquired) {
    try {
      // 락을 획득한 프로세스만 DB 조회
      data = await db.query('SELECT ...');
      await redis.setex(key, 3600, JSON.stringify(data));
      return data;
    } finally {
      await redis.del(lockKey);
    }
  } else {
    // 다른 프로세스가 데이터를 가져올 때까지 대기
    await sleep(100);
    return getDataWithLock(key); // 재시도
  }
}
```

---

## Redis 클러스터 구성

### Redis 클러스터의 필요성

**단일 Redis 인스턴스의 한계:**
- **메모리 제한**: 단일 서버의 RAM 용량에 제한
- **단일 장애점**: Redis 다운 시 전체 서비스 영향
- **처리량 한계**: 단일 인스턴스의 처리 능력 한계

### 1. Master-Slave 복제 (Replication)

**아키텍처:**
```
    Master (쓰기)
       │
   ┌───┴───┐
   │       │
Slave1  Slave2 (읽기)
```

**설정:**
```bash
# redis-master.conf
port 6379
bind 0.0.0.0

# redis-slave1.conf
port 6380
bind 0.0.0.0
replicaof 127.0.0.1 6379

# redis-slave2.conf
port 6381
bind 0.0.0.0
replicaof 127.0.0.1 6379
```

**애플리케이션 코드:**
```javascript
const Redis = require('ioredis');

// 쓰기는 Master로
const masterClient = new Redis({
  host: 'redis-master',
  port: 6379
});

// 읽기는 Slave로 (Round Robin)
const slaves = [
  new Redis({ host: 'redis-slave1', port: 6380 }),
  new Redis({ host: 'redis-slave2', port: 6381 })
];

let slaveIndex = 0;

async function set(key, value) {
  await masterClient.set(key, value);
}

async function get(key) {
  const slave = slaves[slaveIndex];
  slaveIndex = (slaveIndex + 1) % slaves.length;
  return await slave.get(key);
}
```

**장점:**
- 읽기 성능 향상 (부하 분산)
- 데이터 백업 (Slave가 Master 복제)
- 고가용성 (Slave를 Master로 승격 가능)

**단점:**
- Master 장애 시 수동 개입 필요 (자동 Failover 없음)
- 쓰기는 여전히 단일 지점

### 2. Redis Sentinel (자동 Failover)

**Sentinel이 하는 일:**
- Master 상태 모니터링
- Master 장애 감지
- 자동으로 Slave를 Master로 승격
- 클라이언트에게 새로운 Master 주소 알림

**설정:**
```bash
# sentinel.conf
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
```

**애플리케이션 코드:**
```javascript
const Redis = require('ioredis');

const client = new Redis({
  sentinels: [
    { host: 'sentinel1', port: 26379 },
    { host: 'sentinel2', port: 26379 },
    { host: 'sentinel3', port: 26379 }
  ],
  name: 'mymaster'
});

// 자동으로 현재 Master에 연결
await client.set('key', 'value');
```

### 3. Redis Cluster (분산 저장)

**데이터 샤딩으로 메모리 제한 극복:**

```
슬롯 0-5460    슬롯 5461-10922    슬롯 10923-16383
    │               │                   │
  Node 1          Node 2              Node 3
  (Master)        (Master)            (Master)
     │               │                   │
  Replica 1       Replica 2           Replica 3
```

**설정:**
```bash
# 클러스터 생성
redis-cli --cluster create \
  127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
  127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1
```

**애플리케이션 코드:**
```javascript
const Redis = require('ioredis');

const cluster = new Redis.Cluster([
  { host: '127.0.0.1', port: 7000 },
  { host: '127.0.0.1', port: 7001 },
  { host: '127.0.0.1', port: 7002 }
]);

// 자동으로 올바른 노드로 라우팅
await cluster.set('user:123', 'data');
```

**슬롯 계산:**
```javascript
function getSlot(key) {
  const crc16 = require('crc').crc16xmodem;
  return crc16(key) % 16384;
}

// 예시
getSlot('user:123');  // → 슬롯 번호
// 해당 슬롯을 담당하는 노드로 자동 전송
```

**장점:**
- 메모리 제한 극복 (수평 확장)
- 처리량 증가 (여러 노드가 동시 처리)
- 자동 Failover
- 고가용성

**단점:**
- 멀티키 연산 제한 (다른 슬롯의 키는 함께 연산 불가)
- 구성 및 운영 복잡도 증가

---

## API Rate Limiting

### Rate Limiting의 필요성

**문제 상황:**
- 악의적인 사용자의 과도한 API 호출
- 버그로 인한 무한 루프 API 호출
- DDoS 공격

**해결:**
특정 사용자/IP의 API 호출을 제한하여 시스템 보호

### 1. 고정 윈도우 카운터 (Fixed Window Counter)

**개념:**
일정 시간 동안의 요청 수를 카운트한다.

**실무 팁:**
Fixed Window는 구현이 간단하지만 경계에서 트래픽이 급증할 수 있다.

```javascript
async function checkRateLimit(userId, limit = 100) {
  const key = `rate_limit:${userId}:${Math.floor(Date.now() / 60000)}`;
  const current = await redis.incr(key);
  
  if (current === 1) {
    await redis.expire(key, 60); // 1분 후 만료
  }
  
  return current <= limit;
}

// 사용 예시
app.get('/api/data', async (req, res) => {
  const allowed = await checkRateLimit(req.userId, 100);
  
  if (!allowed) {
    return res.status(429).json({ error: 'Too Many Requests' });
  }
  
  // 정상 처리
});
```

**장점:**
- 구현이 매우 간단
- 메모리 효율적

**단점:**
- 윈도우 경계에서 burst 트래픽 발생 가능

```
09:59:30 - 100 requests
10:00:30 - 100 requests
→ 1분 안에 200 requests 가능!
```

### 2. 슬라이딩 윈도우 로그 (Sliding Window Log)

정확한 rate limiting을 제공한다.

**실무 팁:**
Sliding Window는 Fixed Window보다 정확하다. Redis의 Sorted Set을 사용하여 구현한다.

```javascript
async function checkRateLimitSliding(userId, limit = 100, windowMs = 60000) {
  const key = `rate_limit:${userId}`;
  const now = Date.now();
  const windowStart = now - windowMs;
  
  // 만료된 로그 삭제
  await redis.zremrangebyscore(key, 0, windowStart);
  
  // 현재 요청 수 확인
  const count = await redis.zcard(key);
  
  if (count < limit) {
    // 현재 요청 추가
    await redis.zadd(key, now, `${now}-${Math.random()}`);
    await redis.expire(key, Math.ceil(windowMs / 1000));
    return true;
  }
  
  return false;
}
```

**장점:**
- 정확한 rate limiting
- burst 방지

**단점:**
- 메모리 사용량 증가 (모든 요청 타임스탬프 저장)
- 고트래픽에서 성능 저하 가능

### 3. 토큰 버킷 (Token Bucket)

**개념:**
일정 속도로 토큰을 생성하고, 요청 시 토큰을 소비한다.

**실무 팁:**
Token Bucket은 버스트 트래픽을 허용한다. 토큰이 있으면 즉시 처리할 수 있다.

```javascript
async function checkRateLimitTokenBucket(userId, capacity = 100, refillRate = 10) {
  const key = `token_bucket:${userId}`;
  
  const bucket = await redis.hgetall(key);
  const now = Date.now() / 1000; // 초 단위
  
  let tokens = bucket.tokens ? parseFloat(bucket.tokens) : capacity;
  let lastRefill = bucket.lastRefill ? parseFloat(bucket.lastRefill) : now;
  
  // 토큰 리필
  const timePassed = now - lastRefill;
  tokens = Math.min(capacity, tokens + timePassed * refillRate);
  
  if (tokens >= 1) {
    // 토큰 소비
    tokens -= 1;
    await redis.hset(key, 'tokens', tokens.toString(), 'lastRefill', now.toString());
    await redis.expire(key, 3600);
    return true;
  }
  
  return false;
}
```

**장점:**
- burst 트래픽 허용 (버킷에 토큰이 쌓여 있으면)
- 유연한 rate limiting

**단점:**
- 구현 복잡도 높음

### 4. Leaky Bucket (누출 버킷)

**개념:**
요청을 버킷에 넣고, 일정 속도로 처리한다.

**실무 팁:**
Leaky Bucket은 일정 속도로 처리한다. 버스트 트래픽을 제한한다.

```javascript
// Redis List를 큐로 사용
async function addRequest(userId, request) {
  const key = `leaky_bucket:${userId}`;
  const queueLength = await redis.lpush(key, JSON.stringify(request));
  await redis.expire(key, 3600);
  
  const maxQueueSize = 100;
  if (queueLength > maxQueueSize) {
    await redis.rpop(key); // 가장 오래된 요청 제거
    return false; // 거부
  }
  
  return true; // 수락
}

// 워커가 일정 속도로 처리
setInterval(async () => {
  const users = await redis.keys('leaky_bucket:*');
  
  for (const key of users) {
    const request = await redis.rpop(key);
    if (request) {
      await processRequest(JSON.parse(request));
    }
  }
}, 100); // 100ms마다 처리
```

---

## 배치 처리 방법

### 배치 처리의 필요성

**대량 데이터 처리 시나리오:**
- 100만 명의 사용자에게 이메일 발송
- 전체 상품 정보 업데이트
- 대량 데이터 마이그레이션

**문제:**
- 한 번에 처리 시 메모리 부족
- 데이터베이스 과부하
- 타임아웃 발생

### 1. 페이지네이션 기반 배치 처리

```javascript
async function batchProcessUsers(batchSize = 1000) {
  let offset = 0;
  let hasMore = true;
  
  while (hasMore) {
    // 배치 단위로 조회
    const users = await db.query(
      'SELECT * FROM users LIMIT ? OFFSET ?',
      [batchSize, offset]
    );
    
    if (users.length === 0) {
      hasMore = false;
      break;
    }
    
    // 배치 처리
    for (const user of users) {
      await processUser(user);
    }
    
    offset += batchSize;
    
    // 메모리 정리 및 부하 분산을 위한 지연
    await sleep(100);
  }
}
```

### 2. 커서 기반 배치 처리

**대량 데이터에서 더 효율적:**

```javascript
async function batchProcessWithCursor(batchSize = 1000) {
  let lastId = 0;
  let hasMore = true;
  
  while (hasMore) {
    const users = await db.query(
      'SELECT * FROM users WHERE id > ? ORDER BY id LIMIT ?',
      [lastId, batchSize]
    );
    
    if (users.length === 0) {
      hasMore = false;
      break;
    }
    
    for (const user of users) {
      await processUser(user);
    }
    
    lastId = users[users.length - 1].id;
  }
}
```

**장점:**
- OFFSET 사용 시 발생하는 성능 저하 방지
- 처리 중 새 데이터 추가에도 안정적

### 3. Redis를 활용한 배치 작업 큐

```javascript
// 작업을 큐에 추가
async function enqueueBatchJobs(userIds) {
  const pipeline = redis.pipeline();
  
  for (const userId of userIds) {
    pipeline.lpush('batch:jobs', JSON.stringify({
      type: 'processUser',
      userId,
      timestamp: Date.now()
    }));
  }
  
  await pipeline.exec();
}

// 워커가 작업 처리
async function batchWorker(workerId, concurrency = 10) {
  while (true) {
    // 한 번에 여러 작업 가져오기
    const jobs = await redis.rpop('batch:jobs', concurrency);
    
    if (jobs.length === 0) {
      await sleep(1000);
      continue;
    }
    
    // 병렬 처리
    await Promise.all(jobs.map(job => {
      const data = JSON.parse(job);
      return processJob(data);
    }));
  }
}

// 여러 워커 실행
for (let i = 0; i < 5; i++) {
  batchWorker(i).catch(console.error);
}
```

### 4. Bull Queue를 사용한 고급 배치 처리

```javascript
const Queue = require('bull');

const batchQueue = new Queue('batch-processing', {
  redis: {
    host: 'localhost',
    port: 6379
  }
});

// 작업 추가
async function addBatchJobs(users) {
  const jobs = users.map(user => ({
    name: 'processUser',
    data: { userId: user.id },
    opts: {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 2000
      }
    }
  }));
  
  await batchQueue.addBulk(jobs);
}

// 작업 처리
batchQueue.process('processUser', 10, async (job) => {
  const { userId } = job.data;
  
  // 진행률 업데이트
  await job.progress(50);
  
  await processUser(userId);
  
  await job.progress(100);
  
  return { userId, status: 'completed' };
});

// 이벤트 리스너
batchQueue.on('completed', (job, result) => {
  console.log(`Job ${job.id} completed:`, result);
});

batchQueue.on('failed', (job, err) => {
  console.error(`Job ${job.id} failed:`, err);
});
```

---

## 실제 구현 예시

### 사례 1: 전자상거래 상품 조회 API

**시나리오:**
- 상품 정보는 자주 변경되지 않음
- 동일한 상품을 수천 명이 동시에 조회
- 빠른 응답 속도가 중요

**구현:**

```javascript
const express = require('express');
const Redis = require('ioredis');
const mysql = require('mysql2/promise');

const app = express();
const redis = new Redis();
const db = await mysql.createPool({
  host: 'localhost',
  user: 'root',
  database: 'ecommerce'
});

// 상품 조회 API
app.get('/api/products/:id', async (req, res) => {
  const productId = req.params.id;
  const cacheKey = `product:${productId}`;
  
  try {
    // 1. 캐시 확인
    let product = await redis.get(cacheKey);
    
    if (product) {
      console.log('Cache HIT');
      return res.json({
        data: JSON.parse(product),
        cached: true
      });
    }
    
    console.log('Cache MISS');
    
    // 2. DB 조회
    const [rows] = await db.query(
      'SELECT * FROM products WHERE id = ?',
      [productId]
    );
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Product not found' });
    }
    
    product = rows[0];
    
    // 3. 캐시에 저장 (1시간 TTL)
    await redis.setex(cacheKey, 3600, JSON.stringify(product));
    
    return res.json({
      data: product,
      cached: false
    });
    
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// 상품 정보 업데이트 시 캐시 무효화
app.put('/api/products/:id', async (req, res) => {
  const productId = req.params.id;
  const updates = req.body;
  
  try {
    // DB 업데이트
    await db.query(
      'UPDATE products SET name = ?, price = ? WHERE id = ?',
      [updates.name, updates.price, productId]
    );
    
    // 캐시 무효화
    await redis.del(`product:${productId}`);
    
    return res.json({ success: true });
    
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

### 사례 2: 소셜 미디어 피드 시스템

**시나리오:**
- 사용자별로 맞춤 피드 제공
- 실시간 업데이트 필요
- 높은 읽기 성능 요구

**구현:**

```javascript
// 피드 생성 (Fanout on Write 방식)
async function publishPost(userId, post) {
  const postId = await savePostToDB(post);
  
  // 팔로워 목록 조회
  const followers = await db.query(
    'SELECT follower_id FROM follows WHERE user_id = ?',
    [userId]
  );
  
  // 각 팔로워의 피드에 추가
  const pipeline = redis.pipeline();
  
  for (const follower of followers) {
    // Sorted Set 사용 (점수는 타임스탬프)
    pipeline.zadd(
      `feed:${follower.follower_id}`,
      Date.now(),
      JSON.stringify({ postId, userId, content: post.content })
    );
    
    // 피드 크기 제한 (최근 1000개만 유지)
    pipeline.zremrangebyrank(`feed:${follower.follower_id}`, 0, -1001);
  }
  
  await pipeline.exec();
  
  return postId;
}

// 피드 조회
app.get('/api/feed', async (req, res) => {
  const userId = req.userId;
  const page = parseInt(req.query.page) || 1;
  const pageSize = 20;
  
  const start = (page - 1) * pageSize;
  const end = start + pageSize - 1;
  
  // Redis에서 피드 조회 (최신순)
  const feedItems = await redis.zrevrange(
    `feed:${userId}`,
    start,
    end
  );
  
  const posts = feedItems.map(item => JSON.parse(item));
  
  return res.json({
    posts,
    page,
    hasMore: posts.length === pageSize
  });
});
```

### 사례 3: 실시간 순위 시스템 (리더보드)

**시나리오:**
- 게임 점수 실시간 업데이트
- 순위 조회가 빈번
- 정확한 순위 계산 필요

**구현:**

```javascript
// 점수 업데이트
app.post('/api/score', async (req, res) => {
  const { userId, score } = req.body;
  
  // Sorted Set에 점수 저장 (높은 점수가 우선)
  await redis.zadd('leaderboard', score, userId);
  
  // 사용자 정보 캐시
  await redis.hset(`user:${userId}`, 'score', score, 'updated', Date.now());
  
  // 현재 순위 조회
  const rank = await redis.zrevrank('leaderboard', userId);
  
  return res.json({
    score,
    rank: rank + 1 // 0-based이므로 +1
  });
});

// 순위 조회
app.get('/api/leaderboard', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const pageSize = 100;
  
  const start = (page - 1) * pageSize;
  const end = start + pageSize - 1;
  
  // 상위 랭커 조회 (점수 포함)
  const leaderboard = await redis.zrevrange(
    'leaderboard',
    start,
    end,
    'WITHSCORES'
  );
  
  // 결과 포맷팅
  const results = [];
  for (let i = 0; i < leaderboard.length; i += 2) {
    const userId = leaderboard[i];
    const score = leaderboard[i + 1];
    
    results.push({
      rank: start + (i / 2) + 1,
      userId,
      score: parseInt(score)
    });
  }
  
  return res.json({ leaderboard: results });
});

// 특정 사용자 주변 순위 조회
app.get('/api/leaderboard/around/:userId', async (req, res) => {
  const { userId } = req.params;
  const range = 5; // 위아래 5명씩
  
  // 현재 순위 확인
  const rank = await redis.zrevrank('leaderboard', userId);
  
  if (rank === null) {
    return res.status(404).json({ error: 'User not found' });
  }
  
  // 주변 순위 조회
  const start = Math.max(0, rank - range);
  const end = rank + range;
  
  const nearbyPlayers = await redis.zrevrange(
    'leaderboard',
    start,
    end,
    'WITHSCORES'
  );
  
  const results = [];
  for (let i = 0; i < nearbyPlayers.length; i += 2) {
    const playerId = nearbyPlayers[i];
    const score = nearbyPlayers[i + 1];
    
    results.push({
      rank: start + (i / 2) + 1,
      userId: playerId,
      score: parseInt(score),
      isCurrentUser: playerId === userId
    });
  }
  
  return res.json({ leaderboard: results });
});
```

---

## AWS 인프라를 활용한 대량 API 처리

AWS의 관리형 서비스를 활용하여 인프라 레벨에서 대량 API 처리를 최적화한다.

**실무 팁:**
AWS 관리형 서비스를 사용하면 인프라 관리 부담을 줄일 수 있다. ECS, RDS Proxy, ElastiCache 등을 활용한다.

### AWS 서비스 구성 개요

| 서비스 | 역할 | 주요 기능 |
|--------|------|----------|
| **ECS** | 컨테이너 오케스트레이션 | Auto Scaling, 배포 관리 |
| **RDS Proxy** | DB 연결 풀링 | Connection 관리, Failover |
| **ElastiCache** | 인메모리 캐싱 | Redis 클러스터, 고가용성 |
| **ALB** | 로드 밸런싱 | L7 라우팅, Rate Limiting |

---

### Amazon ECS (Elastic Container Service)

**개요:** 컨테이너화된 애플리케이션을 쉽게 배포하고 관리하는 관리형 서비스다.

#### ECS의 주요 개념

**실무 팁:**
ECS는 컨테이너 오케스트레이션 서비스다. Fargate를 사용하면 서버 관리 없이 컨테이너를 실행할 수 있다.

**아키텍처:**
```
                 ALB
                  │
            ┌─────┴─────┐
            │           │
      ECS Service   ECS Service
            │           │
    ┌───────┼───────┐   │
    │       │       │   │
  Task1  Task2  Task3  Task4
  (컨테이너) (컨테이너) (컨테이너) (컨테이너)
```

**주요 구성 요소:**
- **클러스터 (Cluster)**: 태스크가 실행되는 논리적 그룹
- **서비스 (Service)**: 태스크의 복사본을 원하는 개수만큼 유지
- **태스크 (Task)**: 하나 이상의 컨테이너 그룹
- **태스크 정의 (Task Definition)**: 컨테이너 설정의 블루프린트

#### ECS Auto Scaling 설정

**1. Task Definition 작성:**

```json
{
  "family": "api-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api-container",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/api-service:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        },
        {
          "name": "REDIS_HOST",
          "value": "redis.abc123.ng.0001.use1.cache.amazonaws.com"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/api-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**2. Service 정의 (Terraform 예시):**

```hcl
resource "aws_ecs_service" "api_service" {
  name            = "api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 3
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnets
    security_groups = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api-container"
    container_port   = 3000
  }

  # Auto Scaling 설정
  depends_on = [aws_lb_listener.api]
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 10
  min_capacity       = 3
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# CPU 기반 Auto Scaling
resource "aws_appautoscaling_policy" "ecs_cpu_policy" {
  name               = "cpu-auto-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# 메모리 기반 Auto Scaling
resource "aws_appautoscaling_policy" "ecs_memory_policy" {
  name               = "memory-auto-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80.0
  }
}

# 요청 수 기반 Auto Scaling
resource "aws_appautoscaling_policy" "ecs_request_policy" {
  name               = "request-count-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }
    target_value = 1000.0  # 타겟당 1000 requests
  }
}
```

#### ECS 실전 배포 전략

**Blue-Green 배포:**

```hcl
resource "aws_ecs_service" "api_service" {
  # ... 기본 설정 ...

  deployment_controller {
    type = "CODE_DEPLOY"
  }
}

resource "aws_codedeploy_app" "api" {
  name             = "api-service"
  compute_platform = "ECS"
}

resource "aws_codedeploy_deployment_group" "api" {
  app_name               = aws_codedeploy_app.api.name
  deployment_group_name  = "api-deployment-group"
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.ECSAllAtOnce"

  blue_green_deployment_config {
    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }

    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.api_service.name
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [aws_lb_listener.api.arn]
      }

      target_group {
        name = aws_lb_target_group.blue.name
      }

      target_group {
        name = aws_lb_target_group.green.name
      }
    }
  }
}
```

**Rolling Update:**

```hcl
resource "aws_ecs_service" "api_service" {
  # ... 기본 설정 ...

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }

  # 배포 중 헬스 체크 실패 시 자동 롤백
}
```

#### ECS 성능 최적화

**1. Task Placement 전략:**

```hcl
resource "aws_ecs_service" "api_service" {
  # ... 기본 설정 ...

  ordered_placement_strategy {
    type  = "spread"
    field = "attribute:ecs.availability-zone"
  }

  ordered_placement_strategy {
    type  = "binpack"
    field = "memory"
  }

  placement_constraints {
    type       = "memberOf"
    expression = "attribute:instance-type =~ t3.*"
  }
}
```

**2. Task 크기 최적화:**

```javascript
// 벤치마크를 통한 최적 리소스 결정
const resourceConfigurations = [
  { cpu: 256,  memory: 512  },  // 소형
  { cpu: 512,  memory: 1024 },  // 중형
  { cpu: 1024, memory: 2048 },  // 대형
  { cpu: 2048, memory: 4096 }   // 특대형
];

// 부하 테스트로 최적값 결정
// - 요청당 평균 CPU 사용량
// - 요청당 평균 메모리 사용량
// - 동시 처리 가능한 요청 수
```

**3. Connection Pooling:**

```javascript
// ECS Task에서 실행되는 애플리케이션
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: process.env.RDS_PROXY_ENDPOINT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,     // Task당 10개 연결
  queueLimit: 0,
  enableKeepAlive: true,
  keepAliveInitialDelay: 0
});

// Task 10개 × 10 연결 = 100개 연결
// RDS Proxy가 이를 효율적으로 관리
```

---

### Amazon RDS Proxy

**개요:** 데이터베이스 연결을 관리하고 풀링하여 애플리케이션의 확장성과 복원력을 향상시킨다.

#### RDS Proxy가 해결하는 문제

**문제 상황 (RDS Proxy 없이):**

```
┌─────────────────────────────────────┐
│ Lambda/ECS Task 100개 동시 실행      │
└──────┬──────────────────────────────┘
       │ 각각 DB 연결 생성
       ↓
┌─────────────────────────────────────┐
│ RDS: max_connections = 100           │
│ 연결 수 초과 (오류)                   │
│ ERROR: Too many connections          │
└─────────────────────────────────────┘
```

**해결 방법 (RDS Proxy 사용):**

```
┌─────────────────────────────────────┐
│ Lambda/ECS Task 100개 동시 실행      │
└──────┬──────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────┐
│ RDS Proxy (Connection Pooling)      │
│ - 연결 재사용                         │
│ - 지능적 라우팅                       │
└──────┬──────────────────────────────┘
       │ 실제 DB 연결은 10개만 사용
       ↓
┌─────────────────────────────────────┐
│ RDS: 연결 수 10개                    │
│ 정상 동작                             │
└─────────────────────────────────────┘
```

**주요 효과:**
- 100개 요청 → 10개 DB 연결로 처리
- DB 부하 90% 감소
- 연결 에러 방지

#### RDS Proxy 구성

**Terraform 설정:**

```hcl
# RDS Proxy 생성
resource "aws_db_proxy" "main" {
  name                   = "api-rds-proxy"
  engine_family          = "MYSQL"
  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_secretsmanager_secret.db_credentials.arn
  }
  
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_subnet_ids         = var.private_subnets
  require_tls            = true

  # Connection Pool 설정
  max_connections_percent         = 100
  max_idle_connections_percent    = 50
  connection_borrow_timeout       = 120

  tags = {
    Name = "api-rds-proxy"
  }
}

# Target Group (실제 RDS 인스턴스)
resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    connection_borrow_timeout    = 120
    init_query                   = "SET time_zone = '+00:00'"
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    session_pinning_filters      = ["EXCLUDE_VARIABLE_SETS"]
  }
}

# RDS 인스턴스 연결
resource "aws_db_proxy_target" "main" {
  db_proxy_name          = aws_db_proxy.main.name
  target_group_name      = aws_db_proxy_default_target_group.main.name
  db_instance_identifier = aws_db_instance.main.id
}

# IAM Role for RDS Proxy
resource "aws_iam_role" "rds_proxy" {
  name = "rds-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "rds.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "rds_proxy_secrets" {
  role = aws_iam_role.rds_proxy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.db_credentials.arn
      ]
    }]
  })
}
```

#### 애플리케이션 연동

**IAM 인증 사용:**

```javascript
const mysql = require('mysql2/promise');
const AWS = require('aws-sdk');

class RDSProxyConnection {
  constructor() {
    this.signer = new AWS.RDS.Signer({
      region: process.env.AWS_REGION,
      hostname: process.env.RDS_PROXY_ENDPOINT,
      port: 3306,
      username: process.env.DB_USER
    });
  }

  async getConnection() {
    // IAM 인증 토큰 생성 (15분 유효)
    const token = this.signer.getAuthToken({
      username: process.env.DB_USER
    });

    const connection = await mysql.createConnection({
      host: process.env.RDS_PROXY_ENDPOINT,
      user: process.env.DB_USER,
      password: token,  // IAM 토큰을 비밀번호로 사용
      database: process.env.DB_NAME,
      ssl: 'Amazon RDS',
      authPlugins: {
        mysql_clear_password: () => () => token
      }
    });

    return connection;
  }

  async createPool() {
    const pool = mysql.createPool({
      host: process.env.RDS_PROXY_ENDPOINT,
      user: process.env.DB_USER,
      database: process.env.DB_NAME,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
      // IAM 인증 활성화
      ssl: 'Amazon RDS',
      // 토큰 갱신 로직
      before: async (connection) => {
        const token = this.signer.getAuthToken({
          username: process.env.DB_USER
        });
        connection.password = token;
      }
    });

    return pool;
  }
}

// 사용 예시
const rdsProxy = new RDSProxyConnection();
const pool = await rdsProxy.createPool();

// 쿼리 실행
const [rows] = await pool.query('SELECT * FROM users WHERE id = ?', [userId]);
```

**Secrets Manager 사용:**

```javascript
const AWS = require('aws-sdk');
const mysql = require('mysql2/promise');

const secretsManager = new AWS.SecretsManager({
  region: process.env.AWS_REGION
});

async function getDBCredentials() {
  const secret = await secretsManager.getSecretValue({
    SecretId: process.env.DB_SECRET_ARN
  }).promise();

  return JSON.parse(secret.SecretString);
}

async function createConnection() {
  const credentials = await getDBCredentials();

  const connection = await mysql.createConnection({
    host: process.env.RDS_PROXY_ENDPOINT,
    user: credentials.username,
    password: credentials.password,
    database: credentials.database,
    ssl: 'Amazon RDS'
  });

  return connection;
}
```

#### RDS Proxy Failover 처리

**자동 Failover:**

```javascript
const pool = mysql.createPool({
  host: process.env.RDS_PROXY_ENDPOINT,
  // ... 기타 설정 ...
});

async function executeQueryWithRetry(query, params, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const [rows] = await pool.query(query, params);
      return rows;
    } catch (error) {
      console.error(`Attempt ${attempt} failed:`, error.message);

      // Failover 감지
      if (error.code === 'PROTOCOL_CONNECTION_LOST' || 
          error.code === 'ECONNREFUSED') {
        
        if (attempt < maxRetries) {
          // 지수 백오프
          const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000);
          console.log(`Waiting ${delay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
      }

      throw error;
    }
  }
}

// 사용
try {
  const users = await executeQueryWithRetry(
    'SELECT * FROM users WHERE active = ?',
    [true]
  );
} catch (error) {
  console.error('Query failed after all retries:', error);
}
```

#### RDS Proxy 모니터링

**CloudWatch 메트릭:**

```javascript
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

async function monitorRDSProxy() {
  const metrics = [
    'DatabaseConnections',
    'DatabaseConnectionsCurrentlyBorrowed',
    'DatabaseConnectionsCurrentlySessionPinned',
    'DatabaseConnectionsSetupSucceeded',
    'DatabaseConnectionsSetupFailed',
    'QueryDatabaseResponseLatency'
  ];

  const params = {
    Namespace: 'AWS/RDS',
    MetricName: 'DatabaseConnections',
    Dimensions: [
      {
        Name: 'DBProxyName',
        Value: 'api-rds-proxy'
      }
    ],
    StartTime: new Date(Date.now() - 3600000), // 1시간 전
    EndTime: new Date(),
    Period: 300, // 5분
    Statistics: ['Average', 'Maximum']
  };

  const data = await cloudwatch.getMetricStatistics(params).promise();
  
  console.log('RDS Proxy Metrics:', data.Datapoints);
  
  // 경고 임계값 체크
  const maxConnections = Math.max(...data.Datapoints.map(d => d.Maximum));
  if (maxConnections > 80) {
    console.warn('High connection count detected:', maxConnections);
    // 알림 발송 또는 Auto Scaling 트리거
  }
}

setInterval(monitorRDSProxy, 300000); // 5분마다
```

#### RDS Proxy 실무 고려사항

**1. Connection Pinning 최소화:**

```javascript
// 나쁜 예: Session 변수 사용으로 Pinning 발생
await connection.query('SET @user_id = ?', [userId]);
await connection.query('SELECT * FROM orders WHERE user_id = @user_id');

// 좋은 예: 파라미터로 직접 전달
await connection.query(
  'SELECT * FROM orders WHERE user_id = ?',
  [userId]
);
```

**2. Connection Pool 크기 조정:**

```javascript
// ECS Task 개수에 따라 동적 조정
const taskCount = parseInt(process.env.ECS_TASK_COUNT) || 10;
const connectionsPerTask = Math.ceil(100 / taskCount);

const pool = mysql.createPool({
  host: process.env.RDS_PROXY_ENDPOINT,
  connectionLimit: connectionsPerTask,
  // ...
});
```

**3. 쿼리 최적화:**

```javascript
// 준비된 명령문 사용
const prepared = await pool.prepare(
  'SELECT * FROM users WHERE email = ? AND active = ?'
);

const [rows] = await prepared.execute(['user@example.com', true]);

// 재사용
const [rows2] = await prepared.execute(['another@example.com', true]);

// 정리
await prepared.close();
```

---

### 3. Application Load Balancer (ALB)

ALB는 Layer 7에서 동작하며 HTTP/HTTPS 트래픽을 여러 대상으로 분산한다.

**실무 팁:**
ALB는 경로 기반 라우팅을 지원한다. 여러 서비스를 하나의 ALB로 관리할 수 있다.

#### ALB 고급 라우팅

**경로 기반 라우팅:**

```hcl
resource "aws_lb" "main" {
  name               = "api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnets

  enable_deletion_protection = true
  enable_http2              = true
  enable_cross_zone_load_balancing = true
}

# API v1 Target Group
resource "aws_lb_target_group" "api_v1" {
  name     = "api-v1-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  deregistration_delay = 30

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
}

# API v2 Target Group
resource "aws_lb_target_group" "api_v2" {
  name     = "api-v2-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  # ... health check 설정 ...
}

# Admin Target Group
resource "aws_lb_target_group" "admin" {
  name     = "admin-tg"
  port     = 4000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  # ... health check 설정 ...
}

# Listener Rules
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_v2.arn
  }
}

# /api/v1/* → API v1
resource "aws_lb_listener_rule" "api_v1" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_v1.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/*"]
    }
  }
}

# /admin/* → Admin
resource "aws_lb_listener_rule" "admin" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.admin.arn
  }

  condition {
    path_pattern {
      values = ["/admin/*"]
    }
  }

  condition {
    source_ip {
      values = ["10.0.0.0/8"]  # 내부 IP만 허용
    }
  }
}

# Rate Limiting using AWS WAF
resource "aws_wafv2_web_acl" "rate_limit" {
  name  = "api-rate-limit"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit-rule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "ApiWebACL"
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.rate_limit.arn
}
```

#### 가중치 기반 라우팅 (Canary 배포)

```hcl
resource "aws_lb_listener_rule" "canary" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 50

  action {
    type = "forward"
    
    forward {
      target_group {
        arn    = aws_lb_target_group.api_v2.arn
        weight = 90  # 90%
      }

      target_group {
        arn    = aws_lb_target_group.api_v3_canary.arn
        weight = 10  # 10%
      }

      stickiness {
        enabled  = true
        duration = 3600
      }
    }
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}
```

---

### 4. Amazon ElastiCache (관리형 Redis)

AWS의 관리형 Redis 서비스로 운영 부담을 줄이면서 Redis의 성능을 활용할 수 있다.

**실무 팁:**
ElastiCache는 Redis 클러스터를 자동으로 관리한다. 백업, Failover, 모니터링이 자동화되어 있다.

#### ElastiCache 클러스터 구성

```hcl
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "api-redis-cluster"
  replication_group_description = "Redis cluster for API caching"
  
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = "cache.r6g.large"
  number_cache_clusters      = 3
  
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.redis.name
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  
  # 자동 Failover 활성화
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  # 백업 설정
  snapshot_retention_limit   = 5
  snapshot_window           = "03:00-05:00"
  
  # 유지보수 윈도우
  maintenance_window        = "sun:05:00-sun:07:00"
  
  # 전송 중 암호화
  transit_encryption_enabled = true
  auth_token_enabled        = true
  auth_token                = random_password.redis_auth.result
  
  # 저장 시 암호화
  at_rest_encryption_enabled = true
  kms_key_id                = aws_kms_key.redis.arn
  
  # 알림 설정
  notification_topic_arn    = aws_sns_topic.redis_alerts.arn
  
  # Auto Scaling
  auto_minor_version_upgrade = true

  tags = {
    Name        = "api-redis-cluster"
    Environment = "production"
  }
}

# Parameter Group
resource "aws_elasticache_parameter_group" "redis" {
  name   = "redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "redis-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors redis cpu utilization"
  alarm_actions       = [aws_sns_topic.redis_alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "redis-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "90"
  alarm_description   = "This metric monitors redis memory usage"
  alarm_actions       = [aws_sns_topic.redis_alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}
```

#### 애플리케이션 연동

```javascript
const Redis = require('ioredis');

// ElastiCache Cluster 연결
const redis = new Redis.Cluster([
  {
    host: process.env.ELASTICACHE_CONFIG_ENDPOINT,
    port: 6379
  }
], {
  dnsLookup: (address, callback) => callback(null, address),
  redisOptions: {
    tls: {
      checkServerIdentity: () => undefined
    },
    password: process.env.REDIS_AUTH_TOKEN,
    db: 0
  },
  clusterRetryStrategy: (times) => {
    return Math.min(100 * times, 2000);
  },
  enableReadyCheck: true,
  maxRetriesPerRequest: 3
});

redis.on('error', (err) => {
  console.error('Redis error:', err);
});

redis.on('connect', () => {
  console.log('Connected to ElastiCache');
});

module.exports = redis;
```

---

### 5. 전체 아키텍처 통합 예시

**대량 API 처리를 위한 AWS 인프라:**

```
                    CloudFront (CDN)
                          │
                          ↓
                   Route 53 (DNS)
                          │
                          ↓
                    AWS WAF (Rate Limiting)
                          │
                          ↓
              Application Load Balancer
                    │         │
          ┌─────────┴─────────┴──────────┐
          │                               │
    ECS Service (API)             ECS Service (Admin)
      │   │   │                         │
    Task Task Task                     Task
      │   │   │                         │
      └───┼───┴──────────┬──────────────┘
          │              │
          ↓              ↓
    ElastiCache      RDS Proxy
       (Redis)           │
                         ↓
                    RDS Primary
                         │
                    ┌────┴────┐
                    │         │
              Read Replica  Read Replica
```

**환경 변수 관리:**

```javascript
// config/aws.js
module.exports = {
  rds: {
    proxyEndpoint: process.env.RDS_PROXY_ENDPOINT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER
  },
  elasticache: {
    configEndpoint: process.env.ELASTICACHE_CONFIG_ENDPOINT,
    authToken: process.env.REDIS_AUTH_TOKEN
  },
  ecs: {
    taskCount: parseInt(process.env.ECS_TASK_COUNT) || 3
  }
};
```

---

## 모니터링 및 성능 최적화

### Redis 모니터링 지표

#### 1. 핵심 성능 지표

```javascript
// Redis INFO 명령어로 모니터링
async function getRedisMetrics() {
  const info = await redis.info();
  
  return {
    // 메모리 사용량
    usedMemory: info.used_memory_human,
    usedMemoryRss: info.used_memory_rss_human,
    memFragmentationRatio: info.mem_fragmentation_ratio,
    
    // 연결 정보
    connectedClients: info.connected_clients,
    rejectedConnections: info.rejected_connections,
    
    // 처리량
    opsPerSec: info.instantaneous_ops_per_sec,
    
    // 캐시 히트율
    keyspaceHits: info.keyspace_hits,
    keyspaceMisses: info.keyspace_misses,
    hitRate: (info.keyspace_hits / (info.keyspace_hits + info.keyspace_misses) * 100).toFixed(2) + '%',
    
    // 지연 시간
    latency: info.latest_fork_usec / 1000 + 'ms'
  };
}

// 주기적 모니터링
setInterval(async () => {
  const metrics = await getRedisMetrics();
  console.log('Redis Metrics:', metrics);
  
  // 경고 임계값 체크
  if (parseFloat(metrics.hitRate) < 80) {
    console.warn('Low cache hit rate:', metrics.hitRate);
  }
  
  if (metrics.connectedClients > 10000) {
    console.warn('High number of connections:', metrics.connectedClients);
  }
}, 60000); // 1분마다
```

#### 2. 슬로우 로그 모니터링

```bash
# Redis 설정
CONFIG SET slowlog-log-slower-than 10000  # 10ms 이상 소요되는 명령어 로깅
CONFIG SET slowlog-max-len 128

# 슬로우 로그 조회
SLOWLOG GET 10
```

```javascript
// 애플리케이션에서 슬로우 로그 확인
async function checkSlowQueries() {
  const slowLog = await redis.slowlog('get', 10);
  
  for (const entry of slowLog) {
    console.log({
      id: entry[0],
      timestamp: entry[1],
      duration: entry[2] + 'μs',
      command: entry[3]
    });
  }
}
```

### 성능 최적화 기법

#### 1. Pipeline 사용

**문제:** 여러 명령어를 순차적으로 실행하면 네트워크 왕복 시간이 누적된다.

**실무 팁:**
파이프라인은 여러 명령어를 한 번에 전송한다. 네트워크 왕복 시간을 줄일 수 있다.

```javascript
// 비효율적
for (let i = 0; i < 1000; i++) {
  await redis.set(`key:${i}`, `value${i}`);
}
// 소요 시간: 1ms × 1000 = 1000ms

// Pipeline 사용
const pipeline = redis.pipeline();
for (let i = 0; i < 1000; i++) {
  pipeline.set(`key:${i}`, `value${i}`);
}
await pipeline.exec();
// 소요 시간: ~50ms (20배 빠름!)
```

#### 2. 적절한 데이터 구조 선택

```javascript
// 비효율적: String으로 JSON 저장
await redis.set('user:123', JSON.stringify({
  name: 'John',
  email: 'john@example.com',
  age: 30
}));

const user = JSON.parse(await redis.get('user:123'));

// 효율적: Hash 사용
await redis.hset('user:123', {
  name: 'John',
  email: 'john@example.com',
  age: 30
});

// 특정 필드만 조회 가능
const name = await redis.hget('user:123', 'name');
```

#### 3. 만료 시간 설정

**메모리 누수 방지:**

```javascript
// 모든 캐시 키에 TTL 설정
await redis.setex('temp:data', 3600, data); // 1시간 후 자동 삭제

// 세션 데이터
await redis.setex(`session:${sessionId}`, 86400, sessionData); // 24시간

// 임시 잠금
await redis.set(`lock:${resourceId}`, '1', 'EX', 30, 'NX'); // 30초 후 자동 해제
```

#### 4. 메모리 최적화

```bash
# Redis 설정
maxmemory 2gb
maxmemory-policy allkeys-lru  # 메모리 초과 시 LRU 정책으로 키 삭제

# 압축 설정 (작은 데이터는 압축하여 저장)
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
```

---

## 실무 사례 및 패턴

### 패턴 1: 캐시 워밍 (Cache Warming)

**개념:** 서비스 시작 시 미리 캐시를 채워서 초기 요청의 성능 저하를 방지한다.

**실무 팁:**
캐시 워밍업은 서비스 시작 시 자주 사용되는 데이터를 미리 로드한다. 초기 요청의 지연을 줄일 수 있다.

```javascript
async function warmupCache() {
  console.log('Starting cache warmup...');
  
  // 인기 상품 미리 캐싱
  const popularProducts = await db.query(
    'SELECT * FROM products ORDER BY view_count DESC LIMIT 100'
  );
  
  const pipeline = redis.pipeline();
  
  for (const product of popularProducts) {
    pipeline.setex(
      `product:${product.id}`,
      3600,
      JSON.stringify(product)
    );
  }
  
  await pipeline.exec();
  
  console.log('Cache warmup completed');
}

// 서버 시작 시 실행
warmupCache().catch(console.error);
```

### 패턴 2: 캐시 스탬피드 방지 (Cache Stampede Prevention)

**Probabilistic Early Expiration:**

```javascript
async function getWithProbabilisticEarlyExpiration(key, fetchFunction, ttl = 3600) {
  const data = await redis.get(key);
  
  if (data) {
    const parsed = JSON.parse(data);
    const expiresAt = parsed.expiresAt;
    const now = Date.now();
    
    // 만료 시간이 가까워지면 확률적으로 갱신
    const delta = expiresAt - now;
    const beta = 1; // 조정 가능한 파라미터
    
    if (delta * Math.random() < beta) {
      // 백그라운드에서 갱신
      fetchAndCache(key, fetchFunction, ttl).catch(console.error);
    }
    
    return parsed.value;
  }
  
  // 캐시 미스
  return await fetchAndCache(key, fetchFunction, ttl);
}

async function fetchAndCache(key, fetchFunction, ttl) {
  const value = await fetchFunction();
  
  await redis.setex(key, ttl, JSON.stringify({
    value,
    expiresAt: Date.now() + (ttl * 1000)
  }));
  
  return value;
}
```

### 패턴 3: 세션 스토어

```javascript
const session = require('express-session');
const RedisStore = require('connect-redis')(session);

app.use(session({
  store: new RedisStore({ client: redis }),
  secret: 'your-secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: {
    maxAge: 86400000, // 24시간
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production'
  }
}));

// 세션 사용
app.get('/api/profile', (req, res) => {
  if (!req.session.userId) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  res.json({ userId: req.session.userId });
});
```

### 패턴 4: 분산 락을 이용한 중복 방지

```javascript
class RedisLock {
  constructor(redis, key, ttl = 10) {
    this.redis = redis;
    this.key = `lock:${key}`;
    this.ttl = ttl;
    this.lockValue = null;
  }
  
  async acquire() {
    this.lockValue = Math.random().toString(36);
    const result = await this.redis.set(
      this.key,
      this.lockValue,
      'NX',
      'EX',
      this.ttl
    );
    return result === 'OK';
  }
  
  async release() {
    // Lua 스크립트로 원자적으로 삭제
    const script = `
      if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
      else
        return 0
      end
    `;
    
    return await this.redis.eval(script, 1, this.key, this.lockValue);
  }
}

// 사용 예시: 중복 결제 방지
app.post('/api/payment', async (req, res) => {
  const { orderId, amount } = req.body;
  const lock = new RedisLock(redis, `payment:${orderId}`);
  
  try {
    // 락 획득
    const acquired = await lock.acquire();
    if (!acquired) {
      return res.status(409).json({ error: 'Payment already in progress' });
    }
    
    // 결제 처리
    await processPayment(orderId, amount);
    
    return res.json({ success: true });
    
  } finally {
    // 락 해제
    await lock.release();
  }
});
```

---

## 주의사항 및 실무 고려사항

### 1. 캐시 무효화 전략

**문제:** 데이터가 변경되었을 때 캐시를 어떻게 업데이트할 것인가?

**방법 1: Cache Invalidation (캐시 무효화)**
```javascript
async function updateProduct(productId, data) {
  // DB 업데이트
  await db.query('UPDATE products SET ... WHERE id = ?', [productId]);
  
  // 캐시 삭제
  await redis.del(`product:${productId}`);
  
  // 다음 요청 시 DB에서 새로 읽어서 캐시에 저장
}
```

**방법 2: Cache Update (캐시 업데이트)**
```javascript
async function updateProduct(productId, data) {
  // DB 업데이트
  await db.query('UPDATE products SET ... WHERE id = ?', [productId]);
  
  // 캐시 즉시 업데이트
  await redis.setex(`product:${productId}`, 3600, JSON.stringify(data));
}
```

### 2. Thundering Herd 대응

**문제:** 캐시 만료 시 동시 다발적인 DB 접근

**해결 방법:**
```javascript
async function getDataSafe(key, fetchFunction, ttl = 3600) {
  // 1차 캐시 확인
  let data = await redis.get(key);
  if (data) return JSON.parse(data);
  
  // 락 획득 시도
  const lockKey = `lock:${key}`;
  const lockAcquired = await redis.set(lockKey, '1', 'NX', 'EX', 10);
  
  if (lockAcquired) {
    try {
      // 더블 체크 (다른 프로세스가 이미 업데이트했을 수 있음)
      data = await redis.get(key);
      if (data) return JSON.parse(data);
      
      // DB 조회 및 캐시 업데이트
      data = await fetchFunction();
      await redis.setex(key, ttl, JSON.stringify(data));
      
      return data;
    } finally {
      await redis.del(lockKey);
    }
  } else {
    // 락을 획득하지 못한 경우 대기 후 재시도
    await sleep(50);
    return getDataSafe(key, fetchFunction, ttl);
  }
}
```

### 3. 메모리 관리

```javascript
// 정기적으로 메모리 사용량 체크
setInterval(async () => {
  const info = await redis.info('memory');
  const usedMemory = parseInt(info.used_memory);
  const maxMemory = parseInt(info.maxmemory);
  
  const usage = (usedMemory / maxMemory * 100).toFixed(2);
  
  console.log(`Redis memory usage: ${usage}%`);
  
  if (usage > 90) {
    console.warn('High memory usage! Consider:');
    console.warn('1. Increasing maxmemory');
    console.warn('2. Adjusting TTL values');
    console.warn('3. Implementing eviction policies');
  }
}, 60000);
```

### 4. 연결 풀 관리

```javascript
const Redis = require('ioredis');

// 연결 풀 설정
const redis = new Redis({
  host: 'localhost',
  port: 6379,
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  lazyConnect: true,
  // 재연결 전략
  retryStrategy(times) {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  // 재연결 시 에러 처리
  reconnectOnError(err) {
    const targetError = 'READONLY';
    if (err.message.includes(targetError)) {
      return true; // 재연결
    }
    return false;
  }
});

// 연결 이벤트 처리
redis.on('connect', () => {
  console.log('Redis connected');
});

redis.on('error', (err) => {
  console.error('Redis error:', err);
});

redis.on('close', () => {
  console.log('Redis connection closed');
});
```

### 5. 데이터 일관성 보장

```javascript
// 트랜잭션 사용 (MULTI/EXEC)
async function transferPoints(fromUserId, toUserId, points) {
  const multi = redis.multi();
  
  multi.hincrby(`user:${fromUserId}`, 'points', -points);
  multi.hincrby(`user:${toUserId}`, 'points', points);
  
  const results = await multi.exec();
  
  // 결과 확인
  for (const [err, result] of results) {
    if (err) {
      throw new Error('Transaction failed');
    }
  }
}
```

---

## 참고 자료

### Redis 관련

| 번호 | 제목 | 유형 | 설명 |
|------|------|------|------|
| 1 | [Redis 공식 문서](https://redis.io/documentation) | 공식 문서 | Redis 전반적인 개요 |
| 2 | [Redis 명령어 레퍼런스](https://redis.io/commands) | 레퍼런스 | 모든 명령어 상세 설명 |
| 3 | [ioredis](https://github.com/luin/ioredis) | 라이브러리 | Node.js Redis 클라이언트 |
| 4 | [Caching Strategies](https://codeahoy.com/2017/08/11/caching-strategies-and-how-to-choose-the-right-one/) | 아티클 | 캐싱 전략 선택 |
| 5 | [Redis Best Practices](https://redis.io/topics/best-practices) | 실무 가이드 | Redis 사용 시 주의사항 |
| 6 | [Scaling Redis](https://redis.io/topics/cluster-tutorial) | 튜토리얼 | 고가용성 및 클러스터링 |
| 7 | [Performance Optimization](https://redis.io/topics/optimization) | 최적화 | 성능 튜닝 방법 |
| 8 | [Rate Limiting Patterns](https://redis.io/commands/incr#pattern-rate-limiter) | 패턴 | Rate Limiting 구현 |
| 9 | [Distributed Locks](https://redis.io/topics/distlock) | 패턴 | 분산 락 구현 |

---

### AWS 관련

| 번호 | 제목 | 서비스 | 설명 |
|------|------|--------|------|
| 10 | [Amazon ECS 개발자 가이드](https://docs.aws.amazon.com/ecs/) | ECS | 컨테이너 오케스트레이션 |
| 11 | [RDS Proxy 사용 설명서](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html) | RDS Proxy | DB 연결 관리 |
| 12 | [ElastiCache for Redis](https://docs.aws.amazon.com/elasticache/) | ElastiCache | 관리형 Redis |
| 13 | [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/) | ALB | L7 로드 밸런싱 |
| 14 | [AWS WAF 개발자 가이드](https://docs.aws.amazon.com/waf/) | WAF | 웹 방화벽 |
| 15 | [ECS Auto Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html) | ECS | 오토 스케일링 설정 |
| 16 | [RDS Proxy와 Lambda](https://aws.amazon.com/blogs/compute/using-amazon-rds-proxy-with-aws-lambda/) | 통합 | Serverless 연동 |
| 17 | [Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html) | CloudWatch | ECS 모니터링 |

---

### 실무 사례

| 번호 | 기업 | 주제 | 핵심 내용 |
|------|------|------|----------|
| 18 | [Twitter](https://blog.twitter.com/engineering/en_us/topics/infrastructure/2017/the-infrastructure-behind-twitter-scale) | Redis 활용 | 대규모 Redis 운영 사례 |
| 19 | [Instagram](https://instagram-engineering.com/storing-hundreds-of-millions-of-simple-key-value-pairs-in-redis-1091ae80f74c) | Redis 사용 | 수억 건 데이터 저장 |
| 20 | [Stack Overflow](https://nickcraver.com/blog/2019/08/06/stack-overflow-how-we-do-app-caching/) | 캐싱 전략 | 실제 캐싱 아키텍처 |
| 21 | [Netflix](https://netflixtechblog.com/tagged/microservices) | MSA | 마이크로서비스 아키텍처 |
| 22 | [Airbnb](https://medium.com/airbnb-engineering/building-services-at-airbnb-part-1-c4c1d8fa811b) | MSA 전환 | 모놀리스에서 MSA로 |
| 23 | [Uber](https://eng.uber.com/microservice-architecture/) | 확장성 | 대규모 확장 아키텍처 |

---