---
title: Node.js 캐싱 심화 - 알고리즘, 패턴, 장애 대응
tags: [framework, node, cache, lru, lfu, ttl, stampede, distributed-cache, write-behind, stale-while-revalidate]
updated: 2026-04-17
---

# Node.js 캐싱 심화

## 문서 범위

기본 캐싱 문서(`캐싱_전략.md`)는 node-cache와 Redis 래핑, TTL/Cache-Aside 기본기를 다룬다. 이 문서는 그 다음 단계를 다룬다. 라이브러리가 내부에서 뭘 하는지 모르면 장애가 났을 때 손을 댈 수 없다. LRU/LFU/TTL을 직접 구현해보고, 4가지 읽기/쓰기 패턴의 실제 트레이드오프를 코드로 비교하고, 다중 인스턴스 환경에서 캐시 일관성이 어떻게 깨지는지, Stampede가 왜 서버를 죽이는지 살펴본다.

실무에서 Redis만 쓰면 된다고 생각하기 쉽지만, Redis 한 번 호출에 1~2ms가 깔리기 때문에 초당 수만 QPS를 받는 서비스는 L1(인메모리) + L2(Redis) 두 층으로 운영하는 경우가 많다. 이때 L1 구현을 이해하지 못하면 메모리 누수나 hit ratio가 왜 낮은지 원인을 못 찾는다.

---

## 인메모리 LRU 직접 구현

### 왜 이중연결리스트 + 해시맵인가

LRU는 "가장 오래 참조되지 않은 항목을 제거"한다. 순진하게 배열로 만들면 접근할 때마다 항목을 맨 앞으로 옮기는 데 O(n)이 든다. 캐시 크기가 10만이면 한 번 get 할 때마다 10만 번 이동이다.

이중연결리스트는 노드 하나를 끊어서 head에 붙이는 데 O(1)이면 충분하다. 해시맵은 키에서 노드 포인터로 O(1) 접근을 제공한다. 둘을 결합하면 get/set/evict 모두 O(1)이 나온다. `lru-cache` npm 패키지도 본질적으로 같은 구조를 쓴다(단, v7부터는 배열 기반 원형 버퍼로 바뀌어 캐시 지역성을 노린다).

### 구현

```typescript
// cache/LRUCache.ts
interface Node<K, V> {
  key: K;
  value: V;
  prev: Node<K, V> | null;
  next: Node<K, V> | null;
}

export class LRUCache<K, V> {
  private readonly map = new Map<K, Node<K, V>>();
  private head: Node<K, V> | null = null;
  private tail: Node<K, V> | null = null;

  constructor(private readonly capacity: number) {
    if (capacity <= 0) throw new Error('capacity must be > 0');
  }

  get(key: K): V | undefined {
    const node = this.map.get(key);
    if (!node) return undefined;
    this.moveToFront(node);
    return node.value;
  }

  set(key: K, value: V): void {
    const existing = this.map.get(key);
    if (existing) {
      existing.value = value;
      this.moveToFront(existing);
      return;
    }

    const node: Node<K, V> = { key, value, prev: null, next: this.head };
    if (this.head) this.head.prev = node;
    this.head = node;
    if (!this.tail) this.tail = node;
    this.map.set(key, node);

    if (this.map.size > this.capacity) this.evictLRU();
  }

  private moveToFront(node: Node<K, V>): void {
    if (node === this.head) return;

    // 기존 위치에서 끊기
    if (node.prev) node.prev.next = node.next;
    if (node.next) node.next.prev = node.prev;
    if (node === this.tail) this.tail = node.prev;

    // head 앞에 붙이기
    node.prev = null;
    node.next = this.head;
    if (this.head) this.head.prev = node;
    this.head = node;
  }

  private evictLRU(): void {
    if (!this.tail) return;
    const evicted = this.tail;
    this.tail = evicted.prev;
    if (this.tail) this.tail.next = null;
    else this.head = null;
    this.map.delete(evicted.key);
  }

  get size(): number {
    return this.map.size;
  }
}
```

### 실무에서 빠지는 함정

첫째, JavaScript의 `Map`은 삽입 순서를 보존한다. 단순 LRU는 `Map` 하나만으로 구현할 수 있다(오래된 키 삭제 후 재삽입). 하지만 이 방식은 get마다 delete + set을 호출하므로 내부적으로 엔트리 재할당이 일어난다. 소규모 캐시(~1000)에서는 괜찮지만 크면 이중연결리스트가 빠르다.

둘째, 객체를 value로 저장할 때 외부에서 그 객체를 수정하면 캐시 내용도 바뀐다. `useClones: false`(node-cache 옵션)로 성능을 올리려면 반드시 캐시에 넣은 이후에는 immutable하게 취급한다는 규칙을 팀에서 합의해야 한다. 이걸 안 지키면 디버깅이 지옥이 된다.

셋째, capacity를 메모리 용량이 아닌 "항목 개수"로 잡으면 큰 객체 하나가 힙을 먹어도 evict되지 않는다. 프로덕션에서는 `sizeCalculation` 콜백으로 바이트 기준 제한을 같이 걸어야 한다.

---

## LFU 구현과 O(1) 트릭

### LRU로 부족한 경우

LRU는 "최근성"만 본다. 그래서 가끔 대량으로 한 번만 읽히는 배치 작업이 돌면, 평소 hit ratio 높던 키들이 전부 밀려난다(이걸 scan resistance가 없다고 한다). LFU는 "빈도"를 보므로 일회성 스캔에 강하다.

하지만 순진한 LFU는 O(log n) 힙을 쓴다. Redis의 LFU도 실제로는 정확한 LFU가 아니라 확률적 근사(Morris counter + 쇠퇴)를 쓴다. 여기서는 O(1) LFU 알고리즘(Pasquale Foggia, 2010)을 단순화해 보자.

### 빈도 버킷 기반 O(1) LFU

```typescript
// cache/LFUCache.ts
interface LFUNode<K, V> {
  key: K;
  value: V;
  freq: number;
  prev: LFUNode<K, V> | null;
  next: LFUNode<K, V> | null;
}

interface FreqList<K, V> {
  head: LFUNode<K, V> | null;
  tail: LFUNode<K, V> | null;
}

export class LFUCache<K, V> {
  private readonly nodes = new Map<K, LFUNode<K, V>>();
  private readonly freqs = new Map<number, FreqList<K, V>>();
  private minFreq = 0;

  constructor(private readonly capacity: number) {}

  get(key: K): V | undefined {
    const node = this.nodes.get(key);
    if (!node) return undefined;
    this.bumpFreq(node);
    return node.value;
  }

  set(key: K, value: V): void {
    const existing = this.nodes.get(key);
    if (existing) {
      existing.value = value;
      this.bumpFreq(existing);
      return;
    }

    if (this.nodes.size >= this.capacity) this.evictLFU();

    const node: LFUNode<K, V> = { key, value, freq: 1, prev: null, next: null };
    this.appendToFreqList(node, 1);
    this.nodes.set(key, node);
    this.minFreq = 1;
  }

  private bumpFreq(node: LFUNode<K, V>): void {
    this.removeFromFreqList(node, node.freq);
    node.freq += 1;
    this.appendToFreqList(node, node.freq);

    // 최소 빈도 버킷이 비었으면 올림
    if (!this.freqs.get(this.minFreq)?.head) this.minFreq += 1;
  }

  private appendToFreqList(node: LFUNode<K, V>, freq: number): void {
    let list = this.freqs.get(freq);
    if (!list) {
      list = { head: null, tail: null };
      this.freqs.set(freq, list);
    }
    // head에 추가(같은 빈도면 최근 것을 앞에)
    node.prev = null;
    node.next = list.head;
    if (list.head) list.head.prev = node;
    list.head = node;
    if (!list.tail) list.tail = node;
  }

  private removeFromFreqList(node: LFUNode<K, V>, freq: number): void {
    const list = this.freqs.get(freq);
    if (!list) return;
    if (node.prev) node.prev.next = node.next;
    if (node.next) node.next.prev = node.prev;
    if (node === list.head) list.head = node.next;
    if (node === list.tail) list.tail = node.prev;
  }

  private evictLFU(): void {
    const list = this.freqs.get(this.minFreq);
    if (!list?.tail) return;
    const evicted = list.tail;
    this.removeFromFreqList(evicted, evicted.freq);
    this.nodes.delete(evicted.key);
  }
}
```

### 쇠퇴(aging)가 없으면 LFU는 굳는다

순수 LFU의 치명적인 단점은 과거에 많이 읽혔지만 지금은 안 읽히는 키가 영원히 남는 것이다. 예를 들어 오전에 1만 번 조회된 광고 페이지가 오후에 단 한 번도 안 읽혀도 freq=10000이라 계속 살아있다.

실무에서는 빈도를 주기적으로 감쇠시키는 쇠퇴를 넣는다. Redis의 LFU는 매번 접근할 때 last-access 시각을 기록해두고, 시간이 지나면 freq를 감산한다(`lfu-decay-time` 옵션). 자체 구현한다면 5~10분마다 모든 노드의 freq를 절반으로 나누는 배치 작업이 가장 간단하다.

선택 기준은 대략 이렇다. 요청 패턴이 균등하게 퍼져있고 시간 지역성이 강하면 LRU. 소수 인기 키가 계속 조회되고 배치 스캔이 끼어드는 환경이면 LFU + 쇠퇴. 대부분의 Node 앱은 LRU면 충분하지만, 제품 상세 페이지처럼 Zipfian 분포가 뚜렷하면 LFU가 hit ratio가 5~10%p 더 나온다.

---

## TTL 관리 - 만료 휠

### lazy vs eager 만료

TTL을 구현하는 방법은 두 가지다. lazy는 get할 때마다 만료 여부를 검사해서 만료된 항목을 그 자리에서 지운다. 구현이 단순하지만 한 번도 조회 안 된 만료 키는 메모리에 계속 남는다. eager는 별도 타이머가 돌며 만료된 항목을 쓸어버린다.

node-cache 기본값은 checkperiod 60초로 eager 방식인데, 키가 100만 개쯤 되면 매 60초마다 전체 순회가 이벤트 루프를 수백 ms 막는다. Redis는 lazy + 확률적 eager를 섞는다. 매 100ms마다 랜덤으로 20개를 샘플링해서 25% 이상이 만료되어 있으면 다시 20개를 샘플링한다.

### 타이머 휠

만료 시각별로 별도 타이머를 걸면(setTimeout 수만 개) libuv 타이머 힙에 부담이 간다. 타이머 휠(hashed timing wheel)은 같은 초에 만료되는 항목을 하나의 버킷에 모아두고, 1초에 한 번씩 "현재 초" 버킷만 비우는 방식이다.

```typescript
// cache/TTLWheel.ts
type ExpiryCallback<K> = (key: K) => void;

export class TTLWheel<K> {
  private readonly buckets = new Map<number, Set<K>>();
  private readonly keyToBucket = new Map<K, number>();
  private readonly tickInterval: NodeJS.Timeout;

  constructor(
    private readonly onExpire: ExpiryCallback<K>,
    tickMs = 1000,
  ) {
    this.tickInterval = setInterval(() => this.tick(), tickMs);
    this.tickInterval.unref(); // 프로세스 종료 막지 않음
  }

  schedule(key: K, ttlSeconds: number): void {
    const existing = this.keyToBucket.get(key);
    if (existing !== undefined) {
      this.buckets.get(existing)?.delete(key);
    }
    const expireAt = Math.floor(Date.now() / 1000) + ttlSeconds;
    let bucket = this.buckets.get(expireAt);
    if (!bucket) {
      bucket = new Set();
      this.buckets.set(expireAt, bucket);
    }
    bucket.add(key);
    this.keyToBucket.set(key, expireAt);
  }

  cancel(key: K): void {
    const bucketKey = this.keyToBucket.get(key);
    if (bucketKey === undefined) return;
    this.buckets.get(bucketKey)?.delete(key);
    this.keyToBucket.delete(key);
  }

  private tick(): void {
    const now = Math.floor(Date.now() / 1000);
    for (const [bucketKey, keys] of this.buckets) {
      if (bucketKey > now) continue;
      for (const key of keys) {
        this.onExpire(key);
        this.keyToBucket.delete(key);
      }
      this.buckets.delete(bucketKey);
    }
  }

  close(): void {
    clearInterval(this.tickInterval);
  }
}
```

프로덕션에서는 `buckets.entries()` 순회가 부담이 되면 링 버퍼(고정 크기 배열의 인덱스로 circular 동작)로 바꾸면 된다. 하지만 Node 앱 대부분은 Map 순회로도 충분히 빠르다.

---

## 4가지 패턴 비교

### Cache-Aside (Lazy Loading)

가장 흔하게 쓰는 방식. 애플리케이션이 캐시를 직접 제어한다.

```typescript
async function getUser(id: string): Promise<User> {
  const cached = await cache.get<User>(`user:${id}`);
  if (cached) return cached;

  const user = await db.users.findById(id);
  await cache.set(`user:${id}`, user, 600);
  return user;
}

async function updateUser(id: string, patch: UpdateDto): Promise<User> {
  const user = await db.users.update(id, patch);
  await cache.del(`user:${id}`); // 무효화만
  return user;
}
```

장점은 캐시 장애가 DB 조회를 막지 않는 것이다. 단점은 첫 요청이 항상 캐시 미스라 느리고(cold cache), 업데이트 직후 다른 인스턴스에서 stale 데이터를 잠깐 읽을 수 있다는 점이다. 대부분의 읽기 위주 워크로드에 맞는다.

### Read-Through

캐시 계층이 DB 조회까지 책임진다. 앱은 캐시만 호출하고, 캐시 미스 시 캐시가 직접 DB를 읽는다.

```typescript
// 캐시 라이브러리 자체가 loader를 내장
class ReadThroughCache<V> {
  constructor(
    private readonly loader: (key: string) => Promise<V>,
    private readonly store: CacheStore,
  ) {}

  async get(key: string): Promise<V> {
    const cached = await this.store.get<V>(key);
    if (cached) return cached;
    const data = await this.loader(key);
    await this.store.set(key, data, 600);
    return data;
  }
}

const userCache = new ReadThroughCache(
  (id) => db.users.findById(id),
  redisStore,
);

// 앱 코드는 단순해짐
const user = await userCache.get('user:123');
```

Cache-Aside와 동작은 거의 같지만 "누가 로드 책임을 갖느냐"가 다르다. Read-Through는 로딩 로직을 캐시 계층으로 몰아 앱 코드를 단순화한다. DataLoader가 이 패턴의 변형이다.

### Write-Through

쓸 때 캐시와 DB에 동시에 쓴다.

```typescript
async function setConfig(name: string, value: string): Promise<void> {
  await db.config.upsert(name, value);
  await cache.set(`config:${name}`, value, 3600);
}
```

단순하고 캐시와 DB가 항상 일치한다. 문제는 쓰기 레이턴시에 캐시 쓰기 시간까지 더해지고, 캐시 장애 시 쓰기 자체가 실패할 수 있다. 또 "한 번 쓰고 절대 안 읽히는" 데이터도 캐시에 들어가 메모리를 낭비한다.

### Write-Behind (Write-Back)

쓰기를 버퍼에 모았다가 배치로 DB에 반영한다.

```typescript
// cache/WriteBehindBuffer.ts
export class WriteBehindBuffer<T> {
  private readonly buffer = new Map<string, T>();
  private flushTimer: NodeJS.Timeout | null = null;

  constructor(
    private readonly flushFn: (entries: Map<string, T>) => Promise<void>,
    private readonly flushIntervalMs = 5000,
    private readonly maxSize = 1000,
  ) {}

  write(key: string, value: T): void {
    this.buffer.set(key, value);
    if (this.buffer.size >= this.maxSize) {
      void this.flush();
    } else {
      this.scheduleFlush();
    }
  }

  private scheduleFlush(): void {
    if (this.flushTimer) return;
    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      void this.flush();
    }, this.flushIntervalMs);
  }

  private async flush(): Promise<void> {
    if (this.buffer.size === 0) return;
    const snapshot = new Map(this.buffer);
    this.buffer.clear();
    try {
      await this.flushFn(snapshot);
    } catch (err) {
      // 실패한 엔트리를 다시 버퍼에 되돌림(순서 뒤집힘 주의)
      for (const [k, v] of snapshot) {
        if (!this.buffer.has(k)) this.buffer.set(k, v);
      }
      throw err;
    }
  }

  async shutdown(): Promise<void> {
    if (this.flushTimer) clearTimeout(this.flushTimer);
    await this.flush();
  }
}

// 사용
const viewCountBuffer = new WriteBehindBuffer<number>(
  async (entries) => {
    await db.query(
      `INSERT INTO view_counts(page_id, count) VALUES ${
        [...entries].map(() => '(?, ?)').join(',')
      } ON DUPLICATE KEY UPDATE count = count + VALUES(count)`,
      [...entries].flat(),
    );
  },
);
```

조회수, 카운터, 로그처럼 개별 쓰기의 레이턴시가 중요하지 않고 데이터 유실을 어느 정도 허용할 수 있을 때 쓴다. 치명적인 약점은 flush 전에 프로세스가 죽으면 데이터가 날아간다는 점이다. SIGTERM 핸들러에서 반드시 `shutdown()`으로 비워야 하고, 그래도 유실될 가능성이 있다면 WAL(파일 기반 저널)을 함께 두어야 한다.

### 트레이드오프 요약

| 패턴 | 읽기 미스 시 | 쓰기 시 | 일관성 | 쓰기 레이턴시 | 장애 내성 |
|------|-------------|---------|--------|--------------|----------|
| Cache-Aside | 앱이 DB 조회 | 캐시 무효화 | 약함 | DB만 | 캐시 죽어도 읽기 가능 |
| Read-Through | 캐시가 DB 조회 | 캐시 무효화 | 약함 | DB만 | 캐시 장애 시 읽기 실패 |
| Write-Through | 앱이 DB 조회 | DB+캐시 | 강함 | DB+캐시 | 캐시 장애 시 쓰기 실패 |
| Write-Behind | 캐시/DB 조회 | 버퍼만 | 매우 약함 | 낮음 | 프로세스 다운 시 유실 |

대부분은 Cache-Aside로 시작한다. 쓰기 직후 바로 읽는 패턴이 많으면 Write-Through로 전환한다. 카운터/통계처럼 정확도를 희생해도 되면 Write-Behind를 쓴다. Read-Through는 Cache-Aside를 라이브러리화한 것이라 크게 구별하지 않아도 된다.

---

## 분산 캐시 일관성

### 인스턴스 간 L1 캐시 불일치

Node 앱을 3대 띄우면 각 프로세스의 인메모리 캐시는 서로 독립적이다. 서버 A에서 `user:123`을 업데이트하고 캐시를 갱신해도, 서버 B/C의 캐시는 옛날 데이터를 들고 있다. 이걸 "local cache coherency" 문제라고 한다.

해결법은 크게 세 가지다.

### 1. pub/sub로 무효화 브로드캐스트

Redis pub/sub을 이벤트 버스로 써서 한 인스턴스가 캐시를 변경하면 나머지에 알린다.

```typescript
// cache/DistributedInvalidator.ts
import Redis from 'ioredis';
import { LRUCache } from './LRUCache';

const CHANNEL = 'cache:invalidate';

export class DistributedInvalidator {
  private readonly pub = new Redis();
  private readonly sub = new Redis();
  private readonly instanceId = `${process.pid}-${Date.now()}`;

  constructor(private readonly localCache: LRUCache<string, unknown>) {
    this.sub.subscribe(CHANNEL);
    this.sub.on('message', (_ch, raw) => {
      const { source, keys } = JSON.parse(raw) as { source: string; keys: string[] };
      if (source === this.instanceId) return; // 자기 자신 이벤트 무시
      for (const key of keys) this.localCache.set(key, undefined as never);
      // 실제로는 delete 메서드를 별도로 두는 게 낫다
    });
  }

  async invalidate(...keys: string[]): Promise<void> {
    for (const key of keys) this.localCache.set(key, undefined as never);
    await this.pub.publish(
      CHANNEL,
      JSON.stringify({ source: this.instanceId, keys }),
    );
  }
}
```

장점은 지연이 수 ms 수준으로 짧다는 점. 단점은 pub/sub이 "at-most-once"라 네트워크 블립에 메시지가 유실될 수 있다. 중요 데이터는 TTL을 짧게(30~60초) 두는 안전장치를 같이 써야 한다.

### 2. Redis Keyspace Notifications

Redis 6.2부터 client-side caching(RESP3 tracking)이 생겼다. 클라이언트가 읽은 키를 Redis가 추적해뒀다가 변경 시 해당 클라이언트에만 무효화 신호를 보낸다. pub/sub보다 정밀하지만 ioredis 기본 지원이 아직 부족해 Jedis/Lettuce 쓰는 자바 생태계에서 더 많이 쓴다.

### 3. TTL 지터

완벽한 일관성을 포기하고 TTL만으로 처리하는 방식. 대신 모든 인스턴스가 동시에 만료되어 Stampede가 나지 않도록 TTL에 랜덤 지터를 섞는다.

```typescript
function ttlWithJitter(baseSeconds: number, jitterRatio = 0.1): number {
  const jitter = baseSeconds * jitterRatio;
  return Math.floor(baseSeconds + (Math.random() * 2 - 1) * jitter);
}

// 600초 TTL에 ±10% (540~660초 사이 랜덤)
await cache.set(key, value, ttlWithJitter(600, 0.1));
```

지터가 없으면 같은 시각에 캐시 워밍업된 인스턴스들이 정확히 같은 시각에 만료되어 동시에 DB를 때린다. 10%만 섞어도 만료 시각이 분산되어 부하가 평탄화된다.

### 선택 기준

사용자 프로필처럼 "최신이 중요하지만 1~2초 stale은 허용"되는 데이터는 pub/sub + 짧은 TTL 조합이 가장 실용적이다. 상품 가격처럼 "수 분 stale도 치명적"이면 pub/sub을 쓰되 쓰기 직후 재확인(double-check)을 넣는다. 공지사항이나 카테고리 목록처럼 stale 허용도가 높으면 그냥 TTL 지터면 충분하다.

---

## Stampede 방어

### 왜 문제가 되는가

인기 키의 TTL이 만료된 순간 수백~수천 요청이 동시에 캐시 미스를 맞고 모두 DB로 달려간다. DB는 같은 쿼리를 수천 번 처리하다가 connection pool이 고갈되고 응답이 느려지며, 그 사이 요청이 더 쌓여 서비스 전체가 연쇄 다운된다. 트래픽 많은 서비스에서 장애 원인 1~2위를 다투는 현상이다.

### 1. 분산 락 (Mutex)

한 요청만 DB를 조회하게 하고, 나머지는 그 결과를 기다린다.

```typescript
// cache/DistLock.ts
import Redis from 'ioredis';

const redis = new Redis();

export async function withDistLock<T>(
  lockKey: string,
  ttlMs: number,
  fn: () => Promise<T>,
): Promise<T> {
  const token = `${process.pid}-${Date.now()}-${Math.random()}`;
  const acquired = await redis.set(lockKey, token, 'PX', ttlMs, 'NX');

  if (!acquired) {
    // 락 실패 → 재시도 또는 대기
    await sleep(50);
    throw new Error('lock busy');
  }

  try {
    return await fn();
  } finally {
    // 내가 건 락인지 확인하고 삭제 (Lua 스크립트가 안전)
    await redis.eval(
      `if redis.call("GET", KEYS[1]) == ARGV[1] then
         return redis.call("DEL", KEYS[1])
       else return 0 end`,
      1,
      lockKey,
      token,
    );
  }
}
```

락 TTL을 쿼리 예상 시간보다 넉넉히 잡아야 한다. 짧게 잡으면 락이 풀린 뒤 다른 인스턴스가 똑같이 DB를 때려 락의 의미가 없어진다. Redlock(redlock 알고리즘)은 마스터-레플리카 구조의 race를 고려한 고급 버전인데, 단일 Redis로도 대부분 충분하다.

### 2. Single-flight (in-process)

한 프로세스 내에서 같은 키 요청을 하나의 Promise로 합친다. 외부 락보다 가볍고, L1 캐시와 짝을 이루면 분산 락 없이도 많은 케이스를 막는다.

```typescript
// cache/singleFlight.ts
const inflight = new Map<string, Promise<unknown>>();

export async function singleFlight<T>(
  key: string,
  fn: () => Promise<T>,
): Promise<T> {
  const existing = inflight.get(key);
  if (existing) return existing as Promise<T>;

  const promise = fn().finally(() => inflight.delete(key));
  inflight.set(key, promise);
  return promise;
}

// 사용
async function getProduct(id: string): Promise<Product> {
  const cached = await cache.get<Product>(`product:${id}`);
  if (cached) return cached;

  return singleFlight(`product:${id}`, async () => {
    // 동일 프로세스 내 동시 요청은 이 블록을 한 번만 실행
    const product = await db.products.findById(id);
    await cache.set(`product:${id}`, product, 300);
    return product;
  });
}
```

Go 표준 라이브러리 `singleflight`와 같은 개념이다. Node 프로세스가 30대라면 DB로 가는 요청이 최대 30개로 줄어든다. 분산 락을 더하면 1개까지 줄지만, 30개 정도면 대부분의 DB가 충분히 견딘다.

### 3. Probabilistic Early Expiration (XFetch)

TTL이 끝나기 전에 확률적으로 먼저 재갱신한다. 만료 시점에 몰리는 Stampede를 시간축으로 분산시킨다. "XFetch" 알고리즘으로 알려진 방식이다.

```typescript
// cache/probabilisticRefresh.ts
interface CachedEntry<T> {
  value: T;
  expiresAt: number; // epoch ms
  delta: number;     // 마지막 재계산에 걸린 시간 (ms)
}

const BETA = 1.0; // 값이 클수록 더 일찍 갱신

function shouldEarlyRecompute(entry: CachedEntry<unknown>, now: number): boolean {
  const ttlRemaining = entry.expiresAt - now;
  if (ttlRemaining <= 0) return true;
  const xfetch = entry.delta * BETA * Math.log(Math.random());
  return now - xfetch >= entry.expiresAt;
}

export async function getWithXFetch<T>(
  key: string,
  ttlMs: number,
  loader: () => Promise<T>,
): Promise<T> {
  const raw = await cache.getRaw(key);
  const now = Date.now();

  if (raw && !shouldEarlyRecompute(raw, now)) {
    return raw.value as T;
  }

  return singleFlight(key, async () => {
    const start = Date.now();
    const value = await loader();
    const delta = Date.now() - start;
    await cache.setRaw(key, {
      value,
      expiresAt: now + ttlMs,
      delta,
    });
    return value;
  });
}
```

`delta * log(random)`은 만료가 가까울수록 재계산 확률이 기하적으로 올라간다. 수식이 복잡해보이지만 핵심은 "비싼 쿼리(delta 큼)일수록 더 일찍 갱신"하는 것이다. 구현이 조금 까다롭지만 Stampede가 잦은 인기 키에 강력하다.

### 4. Stale-While-Revalidate (SWR)

캐시가 만료되어도 stale 값을 일단 반환하고 백그라운드에서 갱신한다. HTTP Cache-Control 헤더의 `stale-while-revalidate`와 같은 개념이다.

```typescript
// cache/swr.ts
interface SwrEntry<T> {
  value: T;
  freshUntil: number;
  staleUntil: number;
}

export async function getSWR<T>(
  key: string,
  freshMs: number,
  staleMs: number,
  loader: () => Promise<T>,
): Promise<T> {
  const now = Date.now();
  const entry = await cache.getRaw<SwrEntry<T>>(key);

  if (entry && now < entry.freshUntil) {
    return entry.value; // 신선
  }

  if (entry && now < entry.staleUntil) {
    // stale이지만 허용 범위 → 백그라운드로 갱신하고 stale 반환
    void singleFlight(key, async () => {
      const fresh = await loader();
      await cache.setRaw(key, {
        value: fresh,
        freshUntil: Date.now() + freshMs,
        staleUntil: Date.now() + freshMs + staleMs,
      });
      return fresh;
    });
    return entry.value;
  }

  // 완전 만료 → 동기 재로딩
  return singleFlight(key, async () => {
    const fresh = await loader();
    await cache.setRaw(key, {
      value: fresh,
      freshUntil: Date.now() + freshMs,
      staleUntil: Date.now() + freshMs + staleMs,
    });
    return fresh;
  });
}
```

사용자 관점에서는 캐시가 "만료되는 구간"이 없어 응답 레이턴시가 균일하다. 뉴스 피드나 추천 목록처럼 stale이 치명적이지 않은 데이터에 최고의 선택이다. Next.js의 ISR, Vercel Edge가 이 방식을 쓴다. 주의할 점은 staleUntil 동안 백그라운드 재갱신이 계속 실패하면 영원히 stale이 될 수 있으므로, 최대 stale 시간을 짧게 잡거나 별도 알림을 걸어두어야 한다.

### 방어 기법 조합

혼자 쓰기보다 조합이 보통이다. 실전 구성은 이런 식이다.

- 중요한 키: 분산 락 + 짧은 TTL + pub/sub 무효화
- 트래픽 많은 인기 키: Single-flight + XFetch
- 레이턴시가 중요한 조회성 데이터: SWR + Single-flight
- 카운터/조회수: Write-Behind + 정기 flush

어떤 조합이든 항상 캐시 hit ratio, 미스 시 DB 쿼리 시간, p99 레이턴시를 동시에 모니터링해야 한다. hit ratio 90% 넘어도 나머지 10%에서 Stampede가 나면 장애다. Prometheus + Grafana로 `cache_hits_total`, `cache_misses_total`, `cache_inflight_gauge` 세 메트릭만 찍어도 대부분 감이 잡힌다.

---

## 참고

- Redis 공식 문서: [LRU vs LFU eviction policies](https://redis.io/docs/latest/develop/reference/eviction/)
- Pasquale Foggia et al., "An O(1) algorithm for implementing the LFU cache eviction scheme" (2010)
- Andrei Broder, "Optimal Probabilistic Cache Stampede Prevention" (XFetch 알고리즘, 2015)
- IETF RFC 5861: HTTP Cache-Control Extensions for Stale Content
