---
title: Node.js 다층 캐시 - L1(인메모리) + L2(Redis) 아키텍처
tags: [framework, node, cache, multi-level, lru-cache, ioredis, redis, pubsub, negative-cache, prefix-versioning]
updated: 2026-04-30
---

# Node.js 다층 캐시 (Multi-Level Cache)

## 다층 캐시가 필요한 순간

Redis 한 번 호출에 LAN 환경이라도 0.5~2ms가 깔린다. 같은 인스턴스 내에서 초당 수만 번 같은 키를 읽는 워크로드라면 Redis만으로는 CPU의 절반이 직렬화/네트워크 대기에 묶인다. 실제로 1코어 Node 프로세스가 Redis만 사용해서 처리할 수 있는 한계는 대략 2~3만 RPS인데, 이 중 캐시 조회가 전부라면 Redis 호출만으로 이벤트 루프가 포화된다.

L1(인메모리) + L2(Redis) 두 층으로 운영하면 핫 키는 L1에서 1µs 이내에 응답이 나가고, 콜드 키만 L2를 친다. Redis 부하가 한 자릿수 % 수준으로 떨어지고, 같은 하드웨어에서 처리량이 5~10배 늘어나는 경우가 흔하다. 대신 캐시 일관성이 깨지는 지점이 늘어나고, 메모리 누수와 stale read를 동시에 감당해야 한다. 이 문서는 그 트레이드오프를 어떻게 다룰지에 집중한다.

기본 캐싱 문서(`캐싱_전략.md`)는 L1/L2를 따로 다루고, 심화 문서(`Node_Cache_Advanced.md`)는 LRU/LFU 알고리즘과 Stampede 방어를 다룬다. 이 문서는 두 층을 결합했을 때 새로 생기는 문제 — 양방향 동기화, pub/sub 무효화, 키 버전 관리, 메트릭 분리 — 를 중점으로 다룬다.

---

## 계층별 역할 분리

### L1: 핫 데이터, 휘발성, 인스턴스 로컬

L1은 자주 조회되는 소수의 키만 담는 작은 캐시다. 용량은 보통 5천~5만 항목 정도. 최근 본 사용자 프로필, 자주 조회되는 카테고리 목록, 인증 토큰 검증 결과 같은 것들이 L1에 산다. 휘발성이라 프로세스가 죽으면 사라지고, 인스턴스 간 공유가 안 된다. TTL은 짧게(30초~5분) 잡는다. 길게 잡으면 인스턴스마다 stale 데이터가 다르게 쌓여 디버깅이 곤란해진다.

### L2: 공유 캐시, 영속성 있음, 클러스터 단위

L2는 모든 Node 인스턴스가 공유하는 Redis 같은 외부 캐시다. 용량은 수GB~수십GB. TTL은 길게(수 분~수 시간) 잡는다. L1에서 미스가 나면 L2를 조회하고, L2에서도 미스면 그제야 DB로 간다. L2는 인스턴스 재시작이나 배포에도 살아있어야 의미가 있다. Redis persistence(RDB/AOF)는 보통 끄지만, 워밍업 시간이 길거나 DB 부하가 크면 켜둔다.

### 어떤 데이터를 어디 두는가

| 데이터 특성 | L1 | L2 | DB |
|------------|----|----|-----|
| 초당 수천 회 조회되는 인기 키 | 핵심 | 백업 | 백업 |
| 분당 수십 회 조회 | 미적용 | 핵심 | 백업 |
| 거의 안 바뀌는 설정값 | 핵심 | 핵심 | 원본 |
| 사용자별 데이터 | 선택적 | 핵심 | 원본 |
| 실시간성이 중요한 잔액/재고 | 미적용 | 미적용 | 직접 |

L1에 모든 데이터를 다 담으면 메모리가 터지고, 데이터마다 L1 hit ratio가 낮아져 L1을 두는 의미가 사라진다. L1은 hit ratio 80% 이상 나오는 키만 담는 게 원칙이다. 그러려면 액세스 로그를 분석해 상위 1~5% 키만 추리거나, LRU eviction에 맡기되 capacity를 작게 잡아 자연스럽게 핫 키만 남게 한다.

---

## 양방향 동기화 구현

### get 흐름: L1 → L2 → DB

읽기는 항상 L1 → L2 → DB 순으로 fallback한다. 핵심은 L2 hit 시 그 값을 L1에도 채워두는 것(promotion)이다. 그래야 다음 요청이 L1에서 끝난다.

```typescript
// cache/MultiLevelCache.ts
import Redis from 'ioredis';
import { LRUCache } from 'lru-cache';

interface MultiLevelOptions {
  l1Max: number;
  l1TtlMs: number;
  l2TtlSeconds: number;
  redis: Redis;
}

export class MultiLevelCache {
  private readonly l1: LRUCache<string, unknown>;
  private readonly redis: Redis;
  private readonly l2TtlSeconds: number;

  constructor(opts: MultiLevelOptions) {
    this.l1 = new LRUCache<string, unknown>({
      max: opts.l1Max,
      ttl: opts.l1TtlMs,
      ttlAutopurge: false,
    });
    this.redis = opts.redis;
    this.l2TtlSeconds = opts.l2TtlSeconds;
  }

  async get<T>(key: string): Promise<T | null> {
    // L1 히트
    const l1Hit = this.l1.get(key);
    if (l1Hit !== undefined) return l1Hit as T;

    // L2 조회
    const raw = await this.redis.get(key);
    if (raw === null) return null;

    const parsed = JSON.parse(raw) as T;
    // L2 히트 → L1 채우기 (promotion)
    this.l1.set(key, parsed);
    return parsed;
  }

  async set<T>(key: string, value: T): Promise<void> {
    // L2 먼저 쓰기 (영속성 있는 쪽이 진실의 원천)
    await this.redis.setex(key, this.l2TtlSeconds, JSON.stringify(value));
    // L1도 갱신
    this.l1.set(key, value);
  }

  async getOrLoad<T>(key: string, loader: () => Promise<T>): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached !== null) return cached;

    const fresh = await loader();
    await this.set(key, fresh);
    return fresh;
  }
}
```

`lru-cache` v10은 ttl과 max 두 축을 동시에 지원한다. `ttlAutopurge: false`는 별도 타이머 없이 get 시점에 만료 검사를 한다(lazy expiration). 인스턴스가 많을수록 타이머 누적 오버헤드가 커지므로 lazy가 보통 더 좋다.

### set 시 순서 — L2 먼저, L1 나중

순서가 중요하다. L1을 먼저 쓰고 L2 쓰기가 실패하면 L1만 새 값을 갖고 L2는 옛날 값을 갖는 split brain이 된다. 다른 인스턴스가 L2에서 읽어 자기 L1에 옛 값을 채우면 무효화 신호가 와야 풀린다. 반대로 L2를 먼저 쓰고 L1 쓰기가 실패할 일은 거의 없다(메모리 작업이라). L2 → L1 순서가 안전하다.

### 쓰기 후 무효화 vs 갱신

set 시 L1에 새 값을 직접 박는 대신 L1 키를 삭제만 하는 방식도 있다. 다음 read에서 L2를 한 번 더 거치게 되어 L1 hit ratio가 살짝 떨어지지만, 인스턴스 간 일관성이 더 단순해진다. 아래에서 다룰 pub/sub 무효화와 결합하면 후자가 코드가 간결해진다.

```typescript
async invalidate(key: string): Promise<void> {
  this.l1.delete(key);
  await this.redis.del(key);
  // 다른 인스턴스의 L1도 비워야 함 → pub/sub로 브로드캐스트
}
```

---

## L1 히트율과 L2 부하의 트레이드오프

### capacity가 작으면 L1 의미가 없다

L1 capacity를 100으로 잡고 100만 종류의 키를 가진 서비스라면 L1 hit ratio는 0%에 수렴한다. 매 요청마다 다른 키가 들어와 즉시 evict되기 때문이다. L1은 "조회 분포가 한쪽으로 쏠려있을 때만" 의미가 있다.

실제 측정 방법은 단순하다. 일정 기간(예: 24시간) 액세스 로그에서 키별 빈도를 구해 누적 분포를 그려본다. 상위 1% 키가 전체 조회의 80%를 차지하는 Zipfian 분포라면 L1 capacity를 그 1%로 잡으면 hit ratio 80%가 보장된다. 분포가 평평하면(롱테일) L1은 포기하고 L2만 쓴다.

### capacity가 크면 메모리가 터진다

반대로 L1 capacity를 너무 크게 잡으면 한 항목당 평균 크기 × capacity 만큼 힙을 먹는다. Node 기본 힙은 1.5GB(64bit는 더 크지만 V8 default는 ~4GB)다. 항목 평균이 2KB이고 capacity 100만이면 2GB로 OOM이 난다. 게다가 GC가 큰 Map을 스캔하느라 STW가 길어져 p99 레이턴시가 망가진다.

경험상 L1은 전체 힙의 10~20% 이내로 제한해야 GC 영향이 작다. 1GB 힙이면 L1은 100~200MB가 상한이다. 이걸 넘기면 L1을 늘리는 대신 인스턴스를 늘려야 한다.

### L2 부하 측면

L1 hit ratio가 90%면 L2 트래픽은 10분의 1이 된다. Redis 1대로 처리하던 트래픽을 같은 1대로 10배 받을 수 있다. 반대로 L1 hit ratio가 30%에 그치면 L2 호출 + L1 갱신 비용이 추가되어 오히려 손해다. L1 hit ratio가 60% 미만이면 L1을 두지 않는 편이 단순하고 빠르다.

---

## 케이스 비교: L1만 / L2만 / L1+L2

### L1만 적용

소규모 단일 인스턴스 서비스 또는 인스턴스 간 공유가 필요 없는 데이터에 쓴다. 정적 설정값(JWT 공개키, 라우트 매핑, 환경변수에서 파생된 권한 매트릭스)이 대표적이다. 인스턴스마다 같은 값을 메모리에 들고 있어도 무방하고, 변경 빈도가 매우 낮다.

장점은 외부 의존성이 없어 Redis 장애에도 영향이 없다. 단점은 인스턴스 수만큼 메모리가 중복되고, 쓰기 동기화가 복잡하다(아래 pub/sub 무효화 섹션 참조).

### L2만 적용

다수 인스턴스가 공유해야 하지만 초고빈도 조회가 아닌 경우. 사용자 세션, 분당 수십~수백 회 조회되는 사용자 프로필, 장바구니, 권한 정보가 여기 해당한다. Redis 호출 1~2ms는 충분히 감내할 만하고, 일관성이 단순하다.

장점은 모든 인스턴스가 같은 값을 본다는 것. 단점은 Redis가 단일 장애점이고, 호출 비용이 일정하게 깔린다.

### L1 + L2 적용

초고빈도 + 다수 인스턴스 + 일관성 허용 범위가 있는 경우. 상품 카탈로그, 카테고리 목록, 추천 결과, 피처 플래그가 대표 사례다. 핫 키는 L1에서 처리하고, 콜드 키와 인스턴스 간 동기화는 L2가 맡는다.

장점은 처리량과 응답 속도. 단점은 stale read 가능성과 무효화 복잡도. 무효화를 누락하면 최대 L1 TTL만큼 옛 값을 보여주므로 TTL을 짧게 잡거나 pub/sub 무효화를 반드시 붙여야 한다.

### 비교표

| 항목 | L1만 | L2만 | L1+L2 |
|------|------|------|-------|
| 평균 응답 (캐시 히트) | <1µs | 0.5~2ms | 90% <1µs, 10% 1~2ms |
| 인스턴스 간 공유 | 불가 | 가능 | L2만 공유 |
| Redis 부하 | 0 | 100% | 5~20% |
| 메모리 사용 (per instance) | 큼 | 작음 | 작음~중간 |
| 무효화 복잡도 | 높음(pub/sub 필수) | 낮음 | 높음 |
| 적합한 데이터 | 정적 설정 | 세션/프로필 | 핫 카탈로그 |

---

## pub/sub 기반 L1 무효화

### 왜 필요한가

3대 인스턴스 A/B/C가 각자 L1을 갖고 있다고 하자. A에서 사용자 123의 프로필을 업데이트했다. A는 자기 L1과 L2를 갱신하지만, B와 C의 L1에는 옛 값이 남아있다. B/C의 L1 TTL이 만료될 때까지 옛 값이 응답된다. TTL을 30초로 잡았다면 30초간 stale read.

해결법은 L1 무효화 신호를 모든 인스턴스에 브로드캐스트하는 것. Redis pub/sub이 가장 흔한 선택이다.

### 구현

```typescript
// cache/InvalidationBus.ts
import Redis from 'ioredis';
import { LRUCache } from 'lru-cache';

const CHANNEL = 'cache:l1:invalidate';

interface InvalidateMessage {
  source: string;
  keys: string[];
}

export class InvalidationBus {
  private readonly pub: Redis;
  private readonly sub: Redis;
  private readonly instanceId: string;

  constructor(
    redisUrl: string,
    private readonly l1: LRUCache<string, unknown>,
  ) {
    this.pub = new Redis(redisUrl);
    this.sub = new Redis(redisUrl);
    this.instanceId = `${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    this.sub.subscribe(CHANNEL);
    this.sub.on('message', (_ch, raw) => {
      try {
        const msg = JSON.parse(raw) as InvalidateMessage;
        if (msg.source === this.instanceId) return; // 자기 발행 메시지 무시
        for (const key of msg.keys) this.l1.delete(key);
      } catch {
        // 손상된 메시지는 그냥 버림
      }
    });
  }

  async publishInvalidate(...keys: string[]): Promise<void> {
    if (keys.length === 0) return;
    // 자기 L1은 즉시 삭제
    for (const key of keys) this.l1.delete(key);
    // 나머지 인스턴스에 신호
    await this.pub.publish(
      CHANNEL,
      JSON.stringify({ source: this.instanceId, keys } satisfies InvalidateMessage),
    );
  }

  async close(): Promise<void> {
    await this.sub.unsubscribe(CHANNEL);
    this.sub.disconnect();
    this.pub.disconnect();
  }
}
```

쓰기 흐름은 이렇게 바뀐다.

```typescript
async function updateUserProfile(id: string, patch: ProfilePatch): Promise<Profile> {
  const updated = await db.profiles.update(id, patch);
  await redis.setex(`profile:${id}`, 600, JSON.stringify(updated));
  await invalidationBus.publishInvalidate(`profile:${id}`); // 모든 L1에서 제거
  return updated;
}
```

### pub/sub의 한계

pub/sub은 at-most-once다. Redis와의 연결이 잠깐 끊기는 동안 발행된 메시지는 영영 사라진다. 메시지 유실에 대비해 TTL을 짧게 잡는 안전장치를 같이 쓴다. L1 TTL을 60초로 잡으면 무효화 신호가 누락되어도 60초 후에는 자연 만료된다.

더 강한 보장이 필요하면 pub/sub 대신 Redis Streams(XADD/XREAD)나 Kafka를 쓴다. 다만 복잡도와 지연이 늘어나므로 대부분의 경우는 pub/sub + 짧은 TTL로 충분하다.

### 자기 메시지 필터링

publish한 인스턴스 자신도 subscribe 채널로 같은 메시지를 받는다. 발행 직전에 이미 자기 L1을 비웠으니 한 번 더 비우는 게 큰 문제는 아니지만, 로그가 두 번 찍히고 메트릭이 부풀려진다. `instanceId`로 자기 발행 메시지는 무시하는 게 깔끔하다.

---

## Negative Caching (미스 결과 캐싱)

### 왜 필요한가

존재하지 않는 키를 매번 조회하면 L1 미스 → L2 미스 → DB 조회 → 결과 없음의 풀 코스를 매번 돈다. 악의적인 사용자가 무작위 ID로 요청을 퍼붓는 캐시 페너트레이션(cache penetration) 공격이 대표 케이스다. DB가 단순 조회만으로 마비된다.

존재하지 않는다는 사실 자체를 캐시에 박아두면 두 번째 조회부터는 L1/L2에서 끝난다. 이걸 negative caching이라 한다.

### 구현 방식

`null`을 그대로 저장하면 "캐시 미스"와 "결과가 null"을 구분할 수 없다. 보초값(sentinel)을 두는 게 안전하다.

```typescript
const NEGATIVE_SENTINEL = '__cache_negative__';

export class MultiLevelCacheWithNegative {
  // ... 기본 필드들

  async get<T>(key: string): Promise<T | null | typeof NEGATIVE_SENTINEL> {
    const l1Hit = this.l1.get(key);
    if (l1Hit !== undefined) return l1Hit as T | typeof NEGATIVE_SENTINEL;

    const raw = await this.redis.get(key);
    if (raw === null) return null; // 캐시 미스 (모름)
    if (raw === NEGATIVE_SENTINEL) {
      this.l1.set(key, NEGATIVE_SENTINEL);
      return NEGATIVE_SENTINEL; // 캐시된 negative
    }

    const parsed = JSON.parse(raw) as T;
    this.l1.set(key, parsed);
    return parsed;
  }

  async setNegative(key: string, ttlSeconds: number): Promise<void> {
    await this.redis.setex(key, ttlSeconds, NEGATIVE_SENTINEL);
    this.l1.set(key, NEGATIVE_SENTINEL);
  }

  async getOrLoad<T>(
    key: string,
    loader: () => Promise<T | null>,
    negativeTtl = 60,
  ): Promise<T | null> {
    const cached = await this.get<T>(key);
    if (cached === NEGATIVE_SENTINEL) return null;
    if (cached !== null) return cached;

    const fresh = await loader();
    if (fresh === null) {
      await this.setNegative(key, negativeTtl);
      return null;
    }
    await this.set(key, fresh);
    return fresh;
  }
}
```

### TTL을 짧게 잡는 게 핵심

negative cache의 TTL은 positive보다 짧게 잡는다. 양수 캐시 TTL이 10분이라면 negative는 30~60초 정도. 데이터가 새로 생성됐는데 캐시에 "없음"이 박혀있으면 그 TTL 동안 신규 데이터가 안 보인다. 사용자가 회원가입한 직후 자기 프로필이 안 보이는 사고가 흔하게 난다.

생성 시점에 negative 캐시를 명시적으로 무효화하는 패턴이 더 안전하다.

```typescript
async function createUser(data: CreateUserDto): Promise<User> {
  const user = await db.users.insert(data);
  await invalidationBus.publishInvalidate(`user:${user.id}`); // negative 박혀있을 수 있음
  return user;
}
```

### Bloom filter와의 조합

키 공간이 매우 커서 negative cache에 모든 미스를 박으면 메모리가 터지는 경우가 있다. 이때는 bloom filter로 "확실히 존재하지 않음"을 빠르게 거른다. RedisBloom 모듈이나 `bloom-filters` npm 패키지로 만든다. False positive(있다고 잘못 판단)는 가능하지만 false negative는 없으므로 캐시 페너트레이션을 막기에 충분하다. 이 글의 범위는 넘어가지만 키워드만 알아두면 된다.

---

## Prefix Versioning으로 일괄 무효화

### 패턴 매칭 삭제의 문제

상품 목록 캐시 키가 `product:list:category:5:page:1`, `product:list:category:5:page:2` 등 수백 개라고 하자. 카테고리 5의 상품이 추가되어 모든 페이지 캐시를 무효화해야 한다. 직관적으로는 `SCAN MATCH product:list:category:5:*`로 키를 찾아 `DEL`하는 방식이지만 문제가 많다.

첫째, SCAN이 클러스터에서 전체 슬롯을 순회하느라 느리다(키 100만 개면 수십 초). 둘째, SCAN 도중 추가된 키는 못 찾을 수 있다. 셋째, L1까지 동시에 비우려면 모든 인스턴스에 패턴을 브로드캐스트해야 하는데, 패턴 매칭이 L1 LRU 구조와 안 맞는다(전체 키 순회 필요).

### prefix versioning 아이디어

키에 버전 번호를 박아둔다. 무효화는 버전을 1 올리는 것으로 갈음한다. 옛 버전 키들은 TTL로 자연 소멸한다.

```
v1: product:list:category:5:page:1
v2: product:list:category:5:page:1
```

이전 버전 키는 새 버전이 발행된 순간 누구도 조회하지 않으므로 메모리에 잠시 남아있다 사라진다. 한 번의 INCR로 수백~수만 키가 일괄 무효화된다.

### 구현

```typescript
// cache/VersionedKeys.ts
import Redis from 'ioredis';

export class VersionedKeyBuilder {
  private readonly versionCache = new Map<string, { version: number; expiresAt: number }>();
  private readonly versionTtlMs = 5_000; // 버전 자체도 짧게 캐시

  constructor(private readonly redis: Redis) {}

  async build(namespace: string, suffix: string): Promise<string> {
    const version = await this.getVersion(namespace);
    return `${namespace}:v${version}:${suffix}`;
  }

  async bump(namespace: string): Promise<number> {
    const newVersion = await this.redis.incr(`version:${namespace}`);
    this.versionCache.delete(namespace);
    return newVersion;
  }

  private async getVersion(namespace: string): Promise<number> {
    const cached = this.versionCache.get(namespace);
    const now = Date.now();
    if (cached && cached.expiresAt > now) return cached.version;

    const versionKey = `version:${namespace}`;
    const raw = await this.redis.get(versionKey);
    let version: number;
    if (raw === null) {
      version = 1;
      await this.redis.setnx(versionKey, '1');
    } else {
      version = parseInt(raw, 10);
    }
    this.versionCache.set(namespace, { version, expiresAt: now + this.versionTtlMs });
    return version;
  }
}

// 사용
const vkeys = new VersionedKeyBuilder(redis);

async function getCategoryProducts(catId: number, page: number) {
  const key = await vkeys.build(`product:list:category:${catId}`, `page:${page}`);
  return cache.getOrLoad(key, () => db.products.findByCategory(catId, page));
}

async function onProductChanged(catId: number) {
  await vkeys.bump(`product:list:category:${catId}`); // 카테고리 캐시 일괄 무효화
}
```

### 버전 캐싱이 핵심

버전 자체를 매 요청마다 Redis에서 읽으면 그게 곧 새로운 병목이다. 위 코드는 versionCache로 5초간 로컬 캐시한다. 무효화 후 최대 5초 stale을 허용하는 셈이다. 더 짧게 가져가려면 pub/sub로 버전 변경 신호를 받아 즉시 비우면 된다.

### L1과의 결합

L1 키도 버전이 박혀있으면 옛 버전 키는 자연스럽게 LRU evict된다. 별도 무효화 브로드캐스트가 필요 없다. pub/sub은 버전 변경 신호 하나만 보내면 된다. 키 단위 무효화 메시지 수천 개를 브로드캐스트하는 것보다 훨씬 가볍다.

단점은 L1에 옛 버전 키가 evict될 때까지 메모리를 차지한다는 것. capacity가 충분히 작으면 금방 밀려나지만, capacity가 크면 무효화 직후 L1의 절반이 dead key가 될 수 있다. 이때는 버전 변경 신호를 받아 prefix가 옛 버전인 키를 수동으로 비우는 작업이 필요하다(L1 라이브러리에 prefix scan 기능이 있어야 함).

---

## L1 메모리 한계 측정

### 항목 개수 기반 capacity의 함정

`new LRUCache({ max: 10000 })`처럼 항목 개수로 잡으면 항목 크기 변동을 못 본다. 평균 1KB라면 10MB지만, 가끔 한 항목이 1MB짜리 JSON이면 그 하나가 100배다. 실제 메모리는 예측 불가능하게 변한다.

### sizeCalculation으로 바이트 기준 제한

`lru-cache` v7+는 `maxSize`와 `sizeCalculation`을 지원한다. 항목별 바이트 수를 계산해 합산하고, 합이 maxSize를 넘으면 evict한다.

```typescript
import { LRUCache } from 'lru-cache';

const l1 = new LRUCache<string, unknown>({
  maxSize: 100 * 1024 * 1024, // 100MB 상한
  sizeCalculation: (value, key) => {
    // 대략적 크기 추정 (JSON 직렬화 길이)
    const serialized = JSON.stringify(value);
    return Buffer.byteLength(serialized, 'utf8') + Buffer.byteLength(key, 'utf8');
  },
  ttl: 60_000,
});

l1.set('user:123', { name: 'Alice', email: 'alice@example.com' });
console.log(l1.calculatedSize); // 누적 바이트
```

`sizeCalculation`이 매 set마다 JSON.stringify를 호출하는 비용이 부담스러울 수 있다. 핫 패스라면 set이 초당 수만 번 일어나고, stringify가 ms 단위로 깔린다. 절충책으로는 다음과 같다.

- 모든 항목이 비슷한 크기면 max(개수)만 쓰고 평균 크기로 추정
- 크기가 큰 객체만 골라 별도 캐시로 분리
- 미리 직렬화된 Buffer를 value로 저장 (set 시 한 번만 stringify)

### 실측 방법

`process.memoryUsage().heapUsed`를 캐시 채우기 전후로 비교하면 실제 힙 증가량이 나온다. 단 V8 GC가 비동기이므로 직후 측정값은 부정확하다. `--expose-gc` 플래그로 띄우고 `global.gc()` 호출 후 재면 안정적이다.

```typescript
// scripts/measure-l1-size.ts
function measureMemory(): number {
  if (global.gc) global.gc();
  return process.memoryUsage().heapUsed;
}

const before = measureMemory();
for (let i = 0; i < 100_000; i += 1) {
  l1.set(`user:${i}`, { id: i, name: `User ${i}`, score: Math.random() });
}
const after = measureMemory();
console.log(`per item: ${((after - before) / 100_000).toFixed(0)} bytes`);
```

V8 객체 헤더, 히든 클래스, 문자열 internalization 때문에 객체 하나당 실제 점유는 JSON 직렬화 크기보다 1.5~3배 크다. JSON으로 100바이트면 힙에서 200~300바이트라고 봐야 한다.

### OOM 방어선

maxSize를 잡았어도 한 항목이 maxSize보다 크면 들어가지 못하고 set이 실패한다. 이걸 모르고 캐시에 의존하다가 특정 키만 영구 미스하는 사고가 난다. set 시 크기를 검사해 너무 크면 L1 우회(L2만 쓰기)하는 방어가 필요하다.

```typescript
const MAX_ITEM_BYTES = 1 * 1024 * 1024; // 1MB

async set<T>(key: string, value: T): Promise<void> {
  await this.redis.setex(key, this.l2TtlSeconds, JSON.stringify(value));
  const size = Buffer.byteLength(JSON.stringify(value), 'utf8');
  if (size <= MAX_ITEM_BYTES) {
    this.l1.set(key, value);
  }
  // size 초과면 L1 skip — 다음 read에서 L2 hit으로 만족
}
```

---

## 다층 hit ratio 메트릭 분리

### 단일 hit ratio가 가리는 진실

캐시 hit ratio 한 숫자만 찍으면 L1 hit인지 L2 hit인지 모른다. 90% hit ratio가 L1 80% + L2 10%인지, L1 0% + L2 90%인지에 따라 응답 분포가 완전히 다르다. 전자는 p99가 1ms 이내지만 후자는 p99가 10ms를 넘는다.

세 갈래로 나눠서 카운트한다.

- L1 hit: L1에서 끝남
- L2 hit: L1 미스, L2에서 끝남
- miss: 둘 다 미스, DB로 갔음

### 구현

```typescript
// cache/Metrics.ts
import client from 'prom-client';

export const cacheCounter = new client.Counter({
  name: 'cache_lookups_total',
  help: 'Multi-level cache lookup outcomes',
  labelNames: ['namespace', 'outcome'] as const,
});

export const cacheLatency = new client.Histogram({
  name: 'cache_lookup_duration_seconds',
  help: 'Lookup duration by outcome',
  labelNames: ['namespace', 'outcome'] as const,
  buckets: [0.0001, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
});

type Outcome = 'l1_hit' | 'l2_hit' | 'miss' | 'l2_negative' | 'l1_negative';

export class InstrumentedCache {
  constructor(
    private readonly base: MultiLevelCache,
    private readonly namespace: string,
  ) {}

  async getOrLoad<T>(key: string, loader: () => Promise<T | null>): Promise<T | null> {
    const start = process.hrtime.bigint();
    let outcome: Outcome = 'miss';

    try {
      const l1Hit = (this.base as any).l1.get(key);
      if (l1Hit !== undefined) {
        outcome = l1Hit === NEGATIVE_SENTINEL ? 'l1_negative' : 'l1_hit';
        return l1Hit === NEGATIVE_SENTINEL ? null : (l1Hit as T);
      }

      const raw = await (this.base as any).redis.get(key);
      if (raw === NEGATIVE_SENTINEL) {
        outcome = 'l2_negative';
        return null;
      }
      if (raw !== null) {
        outcome = 'l2_hit';
        const parsed = JSON.parse(raw) as T;
        (this.base as any).l1.set(key, parsed);
        return parsed;
      }

      const fresh = await loader();
      if (fresh === null) {
        await (this.base as any).setNegative(key, 60);
      } else {
        await this.base.set(key, fresh);
      }
      return fresh;
    } finally {
      const elapsedMs = Number(process.hrtime.bigint() - start) / 1e6;
      cacheCounter.labels(this.namespace, outcome).inc();
      cacheLatency.labels(this.namespace, outcome).observe(elapsedMs / 1000);
    }
  }
}
```

### Grafana 쿼리 예시

PromQL로 다음 세 라인을 띄워두면 캐시 동작이 한눈에 보인다.

```
# L1 hit ratio (전체 대비)
sum(rate(cache_lookups_total{namespace="product",outcome="l1_hit"}[5m]))
  / sum(rate(cache_lookups_total{namespace="product"}[5m]))

# L2 hit ratio
sum(rate(cache_lookups_total{namespace="product",outcome="l2_hit"}[5m]))
  / sum(rate(cache_lookups_total{namespace="product"}[5m]))

# miss ratio (DB로 간 비율)
sum(rate(cache_lookups_total{namespace="product",outcome=~"miss|l1_negative|l2_negative"}[5m]))
  / sum(rate(cache_lookups_total{namespace="product"}[5m]))
```

### 진단 패턴

L1 hit ratio가 10% 미만이면 L1 capacity가 작거나 키 분포가 평평한 것. capacity를 늘리거나 L1을 빼는 결정이 필요하다.

L2 hit ratio가 갑자기 떨어지면 Redis OOM에 의한 eviction이 일어났을 가능성. `INFO memory`로 `evicted_keys` 추세를 본다.

miss ratio가 평소 대비 튀면 캐시 무효화 폭주(prefix versioning bump 너무 잦음)나 TTL 오설정. namespace별로 분리해두면 어느 영역이 문제인지 즉시 보인다.

negative ratio가 비정상적으로 높으면 캐시 페너트레이션 공격 가능성. 비정상 IP 차단이나 bloom filter 도입을 검토한다.

---

## 운영 시 주의사항

### 배포 시 L1 워밍업

새 인스턴스가 뜨면 L1이 텅 비어있다. 부하가 큰 시간대에 카나리 배포를 하면 새 인스턴스가 잠시 L1 0% hit으로 동작해 L2 트래픽이 튄다. 트래픽이 매우 크면 L2까지 휘청인다. 사전 워밍업으로 자주 조회되는 상위 N개 키를 시작 시 채워두는 부트스트랩 코드를 두면 안전하다.

### 직렬화 일관성

L1은 객체 그대로, L2는 JSON 문자열로 저장한다. promotion 시(L2 → L1) JSON.parse를 한 번 해야 한다. 깜빡하고 문자열 그대로 L1에 박으면 다음 read에서 다른 인스턴스와 타입이 안 맞는 사고가 난다. 가능하면 위 코드처럼 set/get 시 직렬화 책임을 한 곳에 모아둔다.

### 클로닝 비용

`useClones: true`(node-cache)나 깊은 복사를 하면 GC 압력이 커진다. L1은 immutable로 취급하기로 합의하고 clone을 끄는 편이 빠르다. 단 캐시에서 받은 객체를 코드에서 직접 수정하는 실수가 있으면 캐시에 그 변경이 반영되어 디버깅이 지옥이 된다. 팀 규약과 lint rule(`no-param-reassign` 등)로 막는다.

### Redis 클러스터에서의 pub/sub

Redis 클러스터 모드에서 pub/sub은 모든 노드에 브로드캐스트되지만(sharded pub/sub은 7.0+), publish 시 슬롯이 맞는 노드로 가지 않으면 동작이 다르다. ioredis Cluster 클라이언트는 자동 처리하지만, 메시지 순서나 누락이 단일 노드보다 더 잦다. 중요한 무효화는 항상 짧은 TTL과 병행한다.

---

## 참고

- ioredis 공식 문서: https://github.com/redis/ioredis
- lru-cache npm: https://github.com/isaacs/node-lru-cache
- Caffeine(자바) 디자인 문서 — 다층 캐시 설계 참고: https://github.com/ben-manes/caffeine/wiki/Efficiency
- Redis pub/sub 한계와 Streams 비교: https://redis.io/docs/latest/develop/interact/pubsub/
- prom-client(Node Prometheus exporter): https://github.com/siimon/prom-client
