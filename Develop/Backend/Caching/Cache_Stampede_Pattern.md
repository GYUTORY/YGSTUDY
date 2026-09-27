---
title: Cache Stampede 방어 패턴
tags: [cache, redis, backend, performance, architecture]
updated: 2026-09-27
---

# Cache Stampede 방어 패턴

## Stampede가 서버를 죽이는 방식

인기 상품 페이지 캐시의 TTL이 만료된다. 그 순간 대기하던 요청 800개가 동시에 캐시 미스를 확인하고 DB로 달려간다. 커넥션 풀(100개)이 순식간에 고갈되고, 대기 중인 700개는 타임아웃 에러를 받는다. 에러를 받은 클라이언트가 재시도하면 부하가 더 늘어난다. 캐시가 올라오기 전에 DB가 먼저 죽는다.

이 패턴이 반복되는 이유는 단순하다. TTL 만료 시점이 모든 요청에게 동시에 보이기 때문이다.

해결 방향은 두 갈래다. 만료 이후 DB 조회를 직렬화하거나, 만료 자체가 일어나기 전에 미리 갱신하거나. 네 가지 방어 방식이 이 두 방향에 걸쳐 있다.

---

## Single-flight — 프로세스 안에서 요청을 합친다

같은 프로세스 내에서 동일 키 요청을 하나의 Promise/Future로 합친다. 외부 의존성이 없고 구현이 단순하다.

```typescript
const inflight = new Map<string, Promise<unknown>>();

async function singleFlight<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inflight.get(key);
  if (existing) return existing as Promise<T>;

  const promise = fn().finally(() => inflight.delete(key));
  inflight.set(key, promise);
  return promise;
}

async function getProduct(id: string): Promise<Product> {
  const cached = await cache.get<Product>(`product:${id}`);
  if (cached) return cached;

  return singleFlight(`product:${id}`, async () => {
    const product = await db.products.findById(id);
    await cache.set(`product:${id}`, product, 300);
    return product;
  });
}
```

Go 표준 라이브러리에 `singleflight` 패키지로 이미 구현되어 있다. Java에서는 `ConcurrentHashMap.computeIfAbsent`에 CompletableFuture를 조합해 같은 구조를 만든다.

방어 범위는 프로세스다. 프로세스가 30대라면 DB로 가는 요청이 최대 30개로 줄어든다. 인스턴스가 적거나 DB가 이 정도 쿼리는 여유 있게 소화한다면 분산 락 없이 Single-flight만으로 충분하다.

`fn()`이 에러를 던지면 inflight 맵에서 제거되고, 그 Promise를 공유하던 모든 호출자에게 같은 에러가 전파된다. 재시도 로직을 개별 호출자가 가지고 있다면 모두가 동시에 재시도하므로, 재시도 간격에 jitter를 섞어야 한다.

---

## 분산 락 — 클러스터 전체에서 요청을 1개로 줄인다

인스턴스가 많아서 Single-flight으로도 DB 요청이 너무 많다면 분산 락으로 클러스터 전체에서 한 요청만 DB를 조회하도록 강제한다.

```typescript
async function withDistLock<T>(
  lockKey: string,
  ttlMs: number,
  fn: () => Promise<T>,
): Promise<T> {
  const token = `${process.pid}-${Date.now()}-${Math.random()}`;
  const acquired = await redis.set(lockKey, token, 'PX', ttlMs, 'NX');

  if (!acquired) {
    await sleep(50 + Math.random() * 50);
    throw new Error('lock busy');
  }

  try {
    return await fn();
  } finally {
    // 비교와 삭제는 원자적으로 처리해야 한다
    await redis.eval(
      `if redis.call("GET", KEYS[1]) == ARGV[1] then
         return redis.call("DEL", KEYS[1])
       else return 0 end`,
      1, lockKey, token,
    );
  }
}
```

Lua 스크립트로 GET + DEL을 원자적으로 처리하는 이유가 있다. GET으로 내 토큰을 확인한 뒤 DEL하기 전에 락 TTL이 만료되면, 그 사이에 다른 프로세스가 락을 잡고 DB를 조회하고 있을 수 있다. 이 상태에서 DEL을 날리면 남의 락을 해제하게 된다.

---

## 락 TTL 오산정으로 중복 실행이 발생하는 케이스

분산 락에서 가장 자주 틀리는 부분이 TTL 설정이다.

**케이스 1: TTL이 DB 쿼리 p99보다 짧다**

```typescript
// 락 TTL: 100ms
// DB 쿼리 평균 소요: 80ms, p99: 350ms
const acquired = await redis.set(lockKey, token, 'PX', 100, 'NX');

// p99 케이스에서 실제로 일어나는 일:
// t=0ms   프로세스 A가 락 획득
// t=100ms 락 TTL 만료 → Redis가 자동으로 락 삭제
// t=100ms 프로세스 B가 락 획득, DB 조회 시작
// t=350ms 프로세스 A 쿼리 완료, 캐시에 쓰기
// t=370ms 프로세스 B 쿼리 완료, 캐시에 덮어쓰기
//         → DB를 두 번 조회했고 캐시도 두 번 덮어써졌다
//
// Lua 없이 DEL만 사용하는 경우 추가 문제:
// t=350ms 프로세스 A의 finally 블록이 DEL(lockKey) 실행
//         → B가 잡고 있던 락이 풀림
//         → C가 바로 락을 잡고 또 DB 조회 시작
```

TTL은 DB 쿼리 p99의 최소 3배로 잡는다. p99가 100ms라면 락 TTL은 300~500ms다. 여기서 주의할 점은 모니터링의 p99는 평상시 수치라는 것이다. DB 부하가 몰리면 쿼리 시간 자체가 늘어난다. 락 경쟁이 심해질수록 TTL을 더 여유 있게 잡아야 하는 악순환이 생기므로, DB 쿼리 자체를 최적화하는 게 근본 해결이다.

**케이스 2: 락 실패 시 재시도가 무한하다**

```typescript
async function getWithLock(id: string, retries = 3): Promise<Product> {
  const cached = await cache.get(`product:${id}`);
  if (cached) return cached;

  try {
    return await withDistLock(`lock:product:${id}`, 500, async () => {
      // 락 획득 후 캐시를 한 번 더 확인한다 (Double-check)
      // 락을 기다리는 동안 앞선 요청이 캐시를 이미 채웠을 수 있다
      const cached2 = await cache.get(`product:${id}`);
      if (cached2) return cached2;

      const product = await db.products.findById(id);
      await cache.set(`product:${id}`, product, 600);
      return product;
    });
  } catch (err) {
    if (err.message === 'lock busy' && retries > 0) {
      await sleep(50 + Math.random() * 100);
      return getWithLock(id, retries - 1);  // 재시도 횟수 제한
    }
    throw err;
  }
}
```

재시도 횟수를 제한하지 않으면 락 경쟁이 심할 때 요청 처리가 수 초씩 늘어난다. 제한 횟수를 모두 소진한 뒤에는 stale 캐시를 반환하거나, 에러를 반환하는 fallback을 명확히 정의해야 한다.

Double-check도 빠뜨리기 쉽다. 락을 기다리는 10~50ms 동안 먼저 락을 잡은 요청이 캐시를 채웠는데, Double-check 없이 바로 DB를 조회하면 불필요한 쿼리가 나간다.

---

## XFetch — 만료 전에 미리 갱신한다

락 기반 방어는 만료가 발생한 뒤에 수습한다. XFetch(Probabilistic Early Expiration)는 방향이 다르다. 실제 TTL이 끝나기 전에 "만료에 가까울수록 높아지는 확률"로 캐시를 미리 갱신해서 만료 자체가 일어나지 않게 한다.

```typescript
interface CachedEntry<T> {
  value: T;
  expiresAt: number;  // epoch ms
  delta: number;      // 마지막 재계산 소요 시간 (ms)
}

const BETA = 1.0;  // 클수록 더 이른 시점부터 갱신을 시작한다

function shouldEarlyRecompute(entry: CachedEntry<unknown>, now: number): boolean {
  if (entry.expiresAt - now <= 0) return true;
  // random()이 작을수록 음수 절대값이 커져 갱신 확률이 올라간다
  const xfetch = entry.delta * BETA * Math.log(Math.random());
  return now - xfetch >= entry.expiresAt;
}

async function getWithXFetch<T>(
  key: string,
  ttlMs: number,
  loader: () => Promise<T>,
): Promise<T> {
  const raw = await cache.getRaw<CachedEntry<T>>(key);
  const now = Date.now();

  if (raw && !shouldEarlyRecompute(raw, now)) {
    return raw.value;
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

`delta * log(random())` 수식에서 delta가 클수록 더 이른 시점부터 갱신을 시작한다. 10ms짜리 쿼리보다 500ms짜리 쿼리가 훨씬 일찍 갱신을 준비한다. 재계산 비용이 클수록 더 보수적으로 동작한다는 뜻이다.

구현 전에 확인해야 할 것이 있다. 캐시 항목에 `expiresAt`과 `delta`를 같이 저장해야 하므로, 캐시 라이브러리가 직렬화 구조를 커스텀할 수 있어야 한다. Redis에서는 `PTTL` 커맨드로 남은 TTL을 가져올 수 있지만, 그것만으로는 부족하고 `delta`를 저장하는 구조가 필요하다. 기존 캐시 레이어에 끼워넣으려면 마이그레이션 비용이 있다.

---

## Stale-While-Revalidate — 만료 구간을 숨긴다

XFetch가 "만료 직전 갱신"이라면, SWR은 "만료 후에도 stale을 반환하고 백그라운드에서 갱신"이다. 사용자 관점에서 캐시 미스로 인한 레이턴시 증가가 사라진다.

```typescript
interface SWREntry<T> {
  value: T;
  freshUntil: number;  // 이 시각 전까지는 fresh
  staleUntil: number;  // 이 시각까지는 stale이지만 반환 가능
}

async function getSWR<T>(
  key: string,
  freshMs: number,   // 예: 60_000 (1분)
  staleMs: number,   // 예: 300_000 (5분)
  loader: () => Promise<T>,
): Promise<T> {
  const now = Date.now();
  const entry = await cache.getRaw<SWREntry<T>>(key);

  if (entry && now < entry.freshUntil) {
    return entry.value;  // fresh
  }

  if (entry && now < entry.staleUntil) {
    // stale 범위 → stale 반환, 백그라운드에서 갱신
    void singleFlight(key, () => revalidate(key, freshMs, staleMs, loader));
    return entry.value;
  }

  // 완전 만료 → 동기 재로딩
  return singleFlight(key, () => revalidate(key, freshMs, staleMs, loader));
}

async function revalidate<T>(
  key: string,
  freshMs: number,
  staleMs: number,
  loader: () => Promise<T>,
): Promise<T> {
  const value = await loader();
  const now = Date.now();
  await cache.setRaw(key, {
    value,
    freshUntil: now + freshMs,
    staleUntil: now + freshMs + staleMs,
  });
  return value;
}
```

Next.js ISR, Vercel Edge, Cloudflare Cache가 이 방식을 쓴다. HTTP `Cache-Control: stale-while-revalidate` 헤더도 같은 개념이다.

staleUntil 동안 백그라운드 갱신이 계속 실패하면 영원히 stale을 반환한다. 백그라운드 갱신 실패 횟수를 카운팅해서 N회 연속 실패 시 알람을 올리는 장치가 있어야 한다. 실패 누적을 방치하면 사용자가 며칠 된 데이터를 보게 된다.

---

## 네 방식 트레이드오프

| 방식 | 방어 범위 | 갱신 시점 | 레이턴시 영향 | 구현 복잡도 | 주요 함정 |
|------|----------|----------|--------------|------------|----------|
| Single-flight | 프로세스 내 | 만료 후 | 동일 (한 번만 DB 조회) | 낮음 | 프로세스 간 중복은 막지 못함 |
| 분산 락 | 클러스터 전체 | 만료 후 | 락 대기 레이턴시 추가 | 중간 | 락 TTL 오산정 시 중복 실행 |
| XFetch | 만료 자체를 방지 | 만료 전 선제 갱신 | 없음 | 높음 | delta 계측 필요, 캐시 구조 변경 |
| SWR | 만료 구간을 숨김 | 만료 후 백그라운드 | 없음 (stale 반환) | 중간 | 백그라운드 갱신 실패 시 stale 누적 |

---

## 조합 판단 기준

세 가지 질문으로 고른다.

**stale을 허용할 수 있는가?**

뉴스 피드, 추천 목록, 배너처럼 수 분 오래된 데이터도 사용자가 인지하지 못한다면 SWR이 가장 단순하다. 가격처럼 stale이 치명적이라면 SWR은 쓸 수 없다.

**DB 쿼리 비용이 얼마나 큰가?**

쿼리 p99가 500ms 이상이거나 외부 API를 호출하는 경우, 락 경쟁 중 타임아웃이 나기 쉽다. 이 경우 XFetch로 만료 전에 미리 갱신하는 쪽이 낫다. 쿼리가 10ms 수준이면 락 경쟁이 짧게 끝나므로 분산 락 + Single-flight 조합이 더 단순하다.

**인스턴스가 몇 개인가?**

인스턴스가 5개 이하라면 Single-flight만으로 DB 요청을 5개로 줄일 수 있다. 대부분의 DB가 이 정도는 여유 있게 소화한다. 인스턴스가 수십 개거나 캐시 미스 시 DB가 실제로 죽은 이력이 있다면 분산 락을 추가한다.

실전에서 자주 쓰는 조합:

- 일반 조회 캐시: Single-flight + 분산 락. DB 요청을 1개로 줄인다.
- 트래픽이 집중되는 인기 키: Single-flight + XFetch. 만료 자체가 일어나지 않게 한다.
- 레이턴시가 최우선인 조회 데이터: SWR + Single-flight. 항상 캐시에서 반환한다.
- 카운터/조회수: Write-Behind. Stampede와 무관하게 쓰기 자체를 지연시킨다.

어떤 조합이든 `cache_hits_total`, `cache_misses_total`, DB 쿼리 p99를 함께 모니터링한다. hit ratio가 90% 이상이어도 나머지 10%에서 Stampede가 나면 장애다.
