---
title: NestJS CacheModule 운영기
tags: [nestjs, cache, cache-manager, redis, caching, ttl, invalidation]
updated: 2026-05-20
---

# NestJS CacheModule 운영기

캐시는 "DB 부하 줄이려고 붙였다가 정합성 깨져서 한 시간 동안 잘못된 데이터가 노출됐다"는 사고가 가장 잦은 영역이다. NestJS의 `CacheModule`은 `cache-manager`를 감싸서 인터셉터 한 줄로 GET 응답을 캐싱할 수 있게 해주는데, 막상 실서비스에 올리면 키 충돌, TTL 미스, 다중 인스턴스 무효화 같은 문제가 줄줄이 나온다. 이 문서는 CacheModule을 서비스에 붙이면서 부딪힌 지점들과 그때 내린 결정을 정리한다.

설정 관리는 [Nest_JS_설정_관리.md](Nest_JS_설정_관리.md)와 [Type_Safe_Config_Service.md](Type_Safe_Config_Service.md)를 참고하고, 본 문서는 캐시 레이어 자체에 집중한다.


## CacheModule이 실제로 하는 일

`@nestjs/cache-manager`(NestJS 10 이후) 또는 `@nestjs/common`(구버전)의 `CacheModule`은 결국 `cache-manager` 인스턴스를 DI 컨테이너에 등록해주는 얇은 래퍼다. 기본 스토어는 메모리(`memory-cache`)고, 별도 스토어를 붙이면 Redis·Memcached로 백엔드를 바꿀 수 있다. 인터셉터(`CacheInterceptor`)는 컨트롤러 메서드의 반환값을 자동으로 캐시에 넣고 다음 요청에서 읽어 돌려준다.

문제는 "자동"이라는 단어가 주는 안도감이다. 자동 캐싱은 GET 요청, 인증 없는 글로벌 응답, 변하지 않는 데이터에만 잘 맞는다. 사용자별 응답이나 쿼리 파라미터가 다양한 엔드포인트에 그대로 붙이면 키 충돌이 나거나 캐시 적중률이 바닥을 친다.

```bash
npm install @nestjs/cache-manager cache-manager
npm install cache-manager-redis-yet  # Redis 스토어
```

NestJS 10부터 `@nestjs/common`에서 `CacheModule`이 분리됐다. 구버전 코드를 그대로 옮기면 `import` 경로에서 막힌다. `cache-manager` v5는 Promise 기반으로 바뀌어서 콜백 API를 쓰던 v4 코드는 동작하지 않는다.


## 기본 등록 — 메모리 스토어

가장 단순한 형태는 메모리 스토어다. 단일 인스턴스 개발 환경이나 자주 안 변하는 정적 데이터에만 쓴다.

```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';

@Module({
  imports: [
    CacheModule.register({
      ttl: 30_000, // ms 단위, v5부터 ms가 기본
      max: 1000,   // 메모리 스토어에서만 의미 있음
      isGlobal: true,
    }),
  ],
})
export class AppModule {}
```

`isGlobal: true`를 주면 다른 모듈에서 `imports`에 추가하지 않아도 `CACHE_MANAGER`를 주입받을 수 있다. 빼먹으면 캐시를 쓰려는 모듈마다 다시 `CacheModule.register()`를 호출해야 하고, 그러면 메모리 스토어가 모듈별로 분리돼서 캐시가 안 잡히는 것처럼 보인다.

v4와 v5의 TTL 단위가 다르다. v4는 초, v5는 밀리초가 기본이다. 업그레이드하면서 `ttl: 60`을 그대로 두면 1분이 아니라 60ms가 돼서 캐시가 거의 즉시 만료된다. 운영에서 "캐시가 동작 안 한다"는 보고가 들어왔을 때 가장 먼저 확인할 것이 이 단위 변경이다.


## Redis 스토어 연동

다중 인스턴스 환경이면 메모리 스토어는 쓸 수 없다. 인스턴스 A에서 캐시한 값을 인스턴스 B가 못 보기 때문에 캐시 적중률이 인스턴스 수에 반비례한다. Redis로 옮긴다.

```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { redisStore } from 'cache-manager-redis-yet';
import { ConfigModule, ConfigService } from '@nestjs/config';

@Module({
  imports: [
    CacheModule.registerAsync({
      isGlobal: true,
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: async (config: ConfigService) => ({
        store: await redisStore({
          socket: {
            host: config.get<string>('REDIS_HOST'),
            port: config.get<number>('REDIS_PORT'),
            reconnectStrategy: (retries) => Math.min(retries * 100, 3000),
          },
          password: config.get<string>('REDIS_PASSWORD'),
          database: config.get<number>('REDIS_DB', 0),
          ttl: 60_000,
        }),
      }),
    }),
  ],
})
export class AppModule {}
```

여기서 자주 놓치는 게 세 가지 있다.

첫째, `redisStore`는 비동기로 연결을 만든다. `registerAsync`의 `useFactory`가 `async`여야 하고, 안에서 `await`로 스토어를 만들어 반환해야 한다. 동기로 두면 캐시 호출 시점에 "store is not connected"가 뜬다.

둘째, `reconnectStrategy`를 안 넣으면 Redis가 잠깐 끊겼을 때 무한 재시도를 돌면서 이벤트 루프를 점유한다. 지수 백오프를 명시적으로 줘야 운영에서 Redis 장애가 앱 전체를 멈추는 사고로 번지지 않는다.

셋째, `database` 선택을 빼먹으면 다른 서비스(세션 스토어, BullMQ 등)와 키를 공유하게 된다. 키 prefix를 따로 안 쓰면 다른 서비스의 키를 캐시 무효화 스크립트가 지워버리는 사고가 난다. DB 인덱스나 prefix 둘 중 하나는 반드시 분리한다.


## 캐시 키 prefix와 충돌 방지

Redis를 여러 용도로 쓰면 키 prefix는 필수다. `cache-manager-redis-yet`은 옵션으로 `keyPrefix`를 받지 않는다. 대신 키를 만들 때 직접 붙여주거나 래퍼 서비스를 둔다.

```typescript
import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';

@Injectable()
export class CacheService {
  constructor(@Inject(CACHE_MANAGER) private readonly cache: Cache) {}

  private prefix(key: string): string {
    return `app:v1:${key}`;
  }

  get<T>(key: string): Promise<T | undefined> {
    return this.cache.get<T>(this.prefix(key));
  }

  set<T>(key: string, value: T, ttl?: number): Promise<void> {
    return this.cache.set(this.prefix(key), value, ttl);
  }

  del(key: string): Promise<void> {
    return this.cache.del(this.prefix(key));
  }
}
```

prefix에 버전(`v1`)을 넣어두면 캐시 포맷을 바꿔야 할 때 prefix만 올려서 자연스럽게 교체한다. 기존 `v1` 키들은 TTL이 지나면 알아서 사라지고, 신규 요청은 `v2`로 새로 쌓인다. 캐시 스키마 마이그레이션을 위한 대규모 `DEL`을 안 돌려도 된다.


## CacheInterceptor 자동 캐싱

가장 빠른 적용 방법이지만 가장 사고가 잦은 방법이기도 하다.

```typescript
import { CacheInterceptor, CacheKey, CacheTTL } from '@nestjs/cache-manager';
import { Controller, Get, UseInterceptors } from '@nestjs/common';

@Controller('products')
@UseInterceptors(CacheInterceptor)
export class ProductsController {
  @Get()
  @CacheTTL(30_000)
  list() {
    return this.productsService.findAll();
  }

  @Get('popular')
  @CacheKey('products:popular')
  @CacheTTL(60_000)
  popular() {
    return this.productsService.findPopular();
  }
}
```

`CacheInterceptor`는 기본적으로 GET 요청 URL을 키로 쓴다. `/products?page=1`과 `/products?page=2`는 서로 다른 키가 된다. `@CacheKey()`를 명시하면 URL 무시하고 그 키로 고정된다.

여기서 사용자별 응답에 인터셉터를 그대로 붙이면 큰 사고가 난다. `/users/me`에 인터셉터를 붙이면 첫 번째 사용자의 응답이 모든 사용자에게 노출된다. URL 기반 키 생성은 인증 컨텍스트를 모르기 때문이다. 사용자별 캐시가 필요하면 인터셉터를 확장한다.

```typescript
import { ExecutionContext, Injectable } from '@nestjs/common';
import { CacheInterceptor } from '@nestjs/cache-manager';

@Injectable()
export class UserScopedCacheInterceptor extends CacheInterceptor {
  protected trackBy(context: ExecutionContext): string | undefined {
    const req = context.switchToHttp().getRequest();
    if (req.method !== 'GET') return undefined;
    const userId = req.user?.id;
    if (!userId) return undefined;
    return `user:${userId}:${req.url}`;
  }
}
```

`trackBy`가 `undefined`를 반환하면 캐싱하지 않는다. 인증되지 않은 요청을 캐싱에서 빼는 안전장치다. POST·PUT·DELETE는 절대 캐싱하면 안 되므로 메서드 체크도 여기서 같이 한다.

자동 캐싱은 다음 조건이 모두 맞을 때만 쓴다. 응답이 사용자별로 다르지 않거나(혹은 사용자 ID를 키에 명시적으로 넣었거나), 쿼리 파라미터의 조합이 폭발적으로 늘지 않고(Redis 메모리 폭증), 무효화가 단순한 경우다. 셋 중 하나라도 안 맞으면 수동 캐싱이 안전하다.


## 수동 캐싱 패턴 — cache-aside

자동 캐싱이 안 맞는 영역에서는 `CACHE_MANAGER`를 직접 주입받아 cache-aside 패턴을 쓴다. 읽을 때 캐시 먼저 보고, 없으면 DB에서 가져와 캐시에 채우고 반환한다.

```typescript
import { Inject, Injectable, Logger } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';

@Injectable()
export class ProductService {
  private readonly logger = new Logger(ProductService.name);

  constructor(
    @Inject(CACHE_MANAGER) private readonly cache: Cache,
    private readonly productRepo: ProductRepository,
  ) {}

  async findById(id: string): Promise<Product | null> {
    const key = `product:${id}`;
    const cached = await this.cache.get<Product>(key);
    if (cached) return cached;

    const product = await this.productRepo.findOne(id);
    if (product) {
      await this.cache.set(key, product, 60_000);
    }
    return product;
  }
}
```

이 코드에는 두 가지 함정이 있다.

첫째, `null`이나 `undefined`를 캐시에 넣지 않는 점이다. 존재하지 않는 ID로 요청이 폭주하면 매번 DB까지 내려간다(캐시 관통, cache penetration). 대응은 `null`도 짧은 TTL로 캐시하는 것이다. 다만 키를 무한정 만들면 Redis 메모리가 터지므로 ID 형식 검증을 컨트롤러 단에서 먼저 한다.

```typescript
async findById(id: string): Promise<Product | null> {
  const key = `product:${id}`;
  const cached = await this.cache.get<Product | 'NULL'>(key);
  if (cached === 'NULL') return null;
  if (cached) return cached as Product;

  const product = await this.productRepo.findOne(id);
  await this.cache.set(key, product ?? 'NULL', product ? 60_000 : 10_000);
  return product;
}
```

둘째, 동시에 같은 키로 요청이 몰리면 캐시가 비어있는 짧은 순간에 DB 쿼리가 N개 동시에 나간다(thundering herd). 트래픽이 큰 키에는 in-flight 요청을 묶어준다.

```typescript
private readonly inflight = new Map<string, Promise<Product | null>>();

async findById(id: string): Promise<Product | null> {
  const key = `product:${id}`;
  const cached = await this.cache.get<Product>(key);
  if (cached) return cached;

  const pending = this.inflight.get(key);
  if (pending) return pending;

  const promise = this.productRepo.findOne(id).then(async (product) => {
    if (product) await this.cache.set(key, product, 60_000);
    this.inflight.delete(key);
    return product;
  });
  this.inflight.set(key, promise);
  return promise;
}
```

이 `inflight` 맵은 프로세스 로컬이라 인스턴스가 여러 개면 인스턴스 수만큼 DB 쿼리가 나갈 수 있다. 더 강한 보장이 필요하면 Redis 분산 락(`SET NX EX`)으로 캐시 채우기를 직렬화한다. 락 비용이 만만치 않으므로 정말 무거운 쿼리에만 쓴다.


## TTL 전략

TTL은 데이터 특성과 무효화 가능성에 따라 다르게 잡는다.

자주 안 변하고 변해도 즉시 반영할 필요가 없는 데이터(카테고리, 상품 메타)는 길게(5분~1시간). 변경 시 명시적으로 무효화한다.

자주 변하지만 정합성이 중요한 데이터(재고, 가격)는 짧게(10~30초) 또는 캐시 안 함. 짧은 TTL은 thundering herd가 더 자주 일어난다.

자주 변하고 정합성이 별로 안 중요한 데이터(인기 상품 랭킹, 추천)는 중간(1~5분). TTL 만료가 트래픽 집중 시점과 겹치지 않게 약간의 jitter를 준다.

```typescript
function ttlWithJitter(baseMs: number, jitterRatio = 0.1): number {
  const jitter = baseMs * jitterRatio * (Math.random() * 2 - 1);
  return Math.round(baseMs + jitter);
}

await this.cache.set(key, value, ttlWithJitter(60_000));
```

같은 TTL로 한 번에 캐시된 키들이 동시에 만료되면 만료 직후 트래픽이 DB로 한꺼번에 몰린다. ±10% 정도의 랜덤 변동을 주면 만료 시점이 분산된다.

TTL을 영원으로 두는 건 권장하지 않는다. 무효화 로직에 버그가 있을 때 잘못된 캐시가 영구히 살아남는다. 최대값을 두고 백그라운드 잡으로 주기적으로 다시 채우는 패턴이 더 안전하다.


## 캐시 무효화 — write-through vs 명시적 삭제

쓰기 발생 시 캐시를 어떻게 다룰지는 두 가지 선택지가 있다.

write-through는 DB 업데이트와 동시에 캐시도 새 값으로 덮어쓴다. 다음 읽기에서 DB를 안 거치고 캐시에서 바로 응답한다. 단점은 캐시가 절대 안 읽힐 값까지 계속 채워진다는 점이다.

명시적 삭제(write-invalidate)는 DB 업데이트 후 캐시 키를 삭제만 한다. 다음 읽기에서 캐시 미스가 나면 그때 DB에서 가져와 채운다. 자주 안 읽히는 값은 캐시에 절대 안 올라간다. 대부분의 경우 이게 더 낫다.

```typescript
async update(id: string, dto: UpdateProductDto): Promise<Product> {
  const updated = await this.productRepo.update(id, dto);
  await this.cache.del(`product:${id}`);
  // 이 상품이 들어가는 리스트 캐시도 같이 무효화
  await this.invalidateListCaches();
  return updated;
}

private async invalidateListCaches(): Promise<void> {
  // cache-manager는 SCAN을 직접 안 노출하므로 Redis 클라이언트로 직접 호출
  await this.cache.del('products:list:page:1');
  await this.cache.del('products:list:page:2');
  // 페이지가 많으면 prefix 무효화 패턴이 필요하다 (아래 참고)
}
```

리스트 캐시 무효화가 까다롭다. `/products?page=1`, `?page=2` 같은 페이지 캐시가 수십 개 있는데 상품 하나 바뀌었다고 전부 지우는 건 비용이 크다. 두 가지 방법이 있다.

첫째, 리스트 캐시에 짧은 TTL(10~30초)을 줘서 명시적 무효화를 포기한다. 글로벌 통계, 인기 상품처럼 약간 늦게 반영돼도 되는 데이터에 적합하다.

둘째, prefix별로 버전 키를 둔다. 리스트 캐시 키에 버전을 포함시키고, 무효화가 필요하면 버전만 올린다.

```typescript
async getListVersion(): Promise<number> {
  return (await this.cache.get<number>('products:list:version')) ?? 1;
}

async invalidateList(): Promise<void> {
  const v = await this.getListVersion();
  await this.cache.set('products:list:version', v + 1, 0);
}

async findAll(page: number): Promise<Product[]> {
  const v = await this.getListVersion();
  const key = `products:list:v${v}:page:${page}`;
  const cached = await this.cache.get<Product[]>(key);
  if (cached) return cached;
  const list = await this.productRepo.findPage(page);
  await this.cache.set(key, list, 60_000);
  return list;
}
```

버전 키를 올리면 기존 캐시 키들은 TTL이 지나면 알아서 사라진다. `SCAN`으로 일괄 삭제하는 비용이 사라진다.


## Redis SCAN으로 패턴 삭제

prefix 단위 일괄 삭제가 정말 필요한 경우는 `cache-manager` API로는 부족하다. Redis 클라이언트를 직접 주입받아 `SCAN`으로 키를 찾아 `DEL`한다.

```typescript
import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import type { RedisClientType } from 'redis';

@Injectable()
export class CacheInvalidator {
  constructor(@Inject(CACHE_MANAGER) private readonly cache: Cache) {}

  async deleteByPrefix(prefix: string): Promise<number> {
    const client = (this.cache.store as any).client as RedisClientType;
    let cursor = 0;
    let deleted = 0;
    do {
      const result = await client.scan(cursor, {
        MATCH: `${prefix}*`,
        COUNT: 500,
      });
      cursor = result.cursor;
      if (result.keys.length > 0) {
        await client.del(result.keys);
        deleted += result.keys.length;
      }
    } while (cursor !== 0);
    return deleted;
  }
}
```

`KEYS *`는 절대 쓰지 않는다. Redis는 싱글 스레드라서 `KEYS`가 도는 동안 다른 명령이 전부 블로킹된다. 키가 수만 개 있는 운영 Redis에서 `KEYS`를 돌리면 서비스 전체가 잠깐 멈춘다. `SCAN`은 커서 기반으로 조금씩 훑기 때문에 안전하다.


## 분산 환경에서 정합성 문제

캐시와 DB가 분리된 시스템에서 일관성을 100% 보장하는 방법은 없다. 다음 시나리오는 cache-aside 패턴에서 실제로 일어난다.

1. 스레드 A가 키 K를 읽어 캐시 미스. DB에서 값 V1을 가져온다.
2. 스레드 B가 V1을 V2로 업데이트하고 캐시 키 K를 삭제한다.
3. 스레드 A가 V1을 캐시에 쓴다.
4. 이후 읽기는 K에서 V1을 본다(잘못된 값).

이 race를 완전히 막으려면 분산 락이 필요한데, 락 비용이 캐시 이득을 까먹는다. 현실적인 대응은 두 가지를 조합한다.

첫째, TTL을 짧게 둬서 잘못된 값이 살아있는 시간을 제한한다. 5분 TTL이면 최악의 경우에도 5분 안에 자동으로 정정된다.

둘째, 쓰기 후 캐시 삭제를 두 번 한다(double delete). 한 번은 DB 업데이트 직후, 또 한 번은 약간의 지연 후(예: 500ms). 두 번째 삭제가 race에서 늦게 들어온 stale write를 정리한다.

```typescript
async update(id: string, dto: UpdateProductDto): Promise<Product> {
  const updated = await this.productRepo.update(id, dto);
  const key = `product:${id}`;
  await this.cache.del(key);

  setTimeout(() => {
    this.cache.del(key).catch((err) =>
      this.logger.warn(`delayed cache del failed: ${err.message}`),
    );
  }, 500);

  return updated;
}
```

`setTimeout`은 프로세스가 죽으면 같이 사라진다. 더 강한 보장이 필요하면 BullMQ 같은 큐에 지연 작업으로 등록한다. 다만 대부분의 경우 짧은 TTL + 즉시 삭제로 충분하다.


## 캐시 미스와 폭증 모니터링

캐시는 적중률(hit rate)이 보이지 않으면 운영할 수 없다. `cache-manager`의 `get` 결과로 직접 계측해도 되지만 인터셉터 단에서 같이 잡는 게 편하다.

```typescript
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { Observable, from, of } from 'rxjs';
import { tap, switchMap } from 'rxjs/operators';

@Injectable()
export class MeteredCacheInterceptor implements NestInterceptor {
  constructor(
    @Inject(CACHE_MANAGER) private readonly cache: Cache,
    private readonly metrics: MetricsService,
  ) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    if (req.method !== 'GET') return next.handle();

    const key = `route:${req.route?.path}:${req.url}`;
    return from(this.cache.get(key)).pipe(
      switchMap((cached) => {
        if (cached !== undefined && cached !== null) {
          this.metrics.increment('cache.hit', { route: req.route?.path });
          return of(cached);
        }
        this.metrics.increment('cache.miss', { route: req.route?.path });
        return next.handle().pipe(
          tap((value) => {
            if (value !== undefined) {
              this.cache.set(key, value, 60_000).catch(() => {});
            }
          }),
        );
      }),
    );
  }
}
```

운영에서 봐야 하는 지표는 세 가지다. 적중률(hit / (hit + miss))이 50% 미만이면 캐시가 일을 안 하는 것이다. 키 개수 증가율이 비정상적으로 빠르면 키 설계에 문제가 있는 것(예: UUID를 키에 그대로 박는 경우). Redis 메모리 사용량은 maxmemory 정책과 같이 본다. `allkeys-lru`가 아니라 `noeviction`이면 메모리가 차는 순간 `SET`이 실패한다.


## 인증·인가 캐시는 따로 다룬다

JWT 검증 결과나 권한 정보를 캐시할 때는 일반 데이터 캐시와 다른 원칙이 적용된다.

권한이 회수되면 즉시 반영돼야 한다. 5분 TTL은 너무 길다. 30초 이하나, 아예 안 캐시하고 메모리 LRU로 핫 데이터만 잡는 게 안전하다.

블랙리스트 토큰은 캐시가 아니라 권위 있는 저장소(Redis 영구 키)로 다룬다. TTL은 토큰 만료 시각으로 맞춘다.

세션 데이터를 cache-manager로 다루면 안 된다. cache-manager는 캐시 의도라서 메모리 압박 시 evict 될 수 있다. 세션은 `connect-redis` 같은 전용 라이브러리로 별도 키스페이스에 둔다.


## 흔히 마주치는 함정 정리

`set`이 동작 안 한다. `cache-manager` v5는 객체를 JSON으로 직렬화하는데, 순환 참조가 있으면 조용히 실패한다. TypeORM 엔티티에 `@ManyToOne` 양방향 관계가 있으면 직렬화에서 막힌다. DTO로 변환한 뒤 캐시에 넣는다.

`get` 결과가 항상 `undefined`다. TTL 단위(ms vs s) 착각이 가장 흔하고, 그 다음으로 키 prefix 차이(set 쪽과 get 쪽이 다른 prefix를 쓰는 경우)다. 한 곳에 prefix 헬퍼를 두고 양쪽에서 같이 쓴다.

배포 후 응답이 이전 버전 그대로 나간다. CacheInterceptor가 컨트롤러 메서드의 응답 스키마가 바뀐 걸 모른다. 응답 포맷이 바뀌는 배포에서는 prefix 버전을 같이 올려서 강제로 캐시를 새로 만들게 한다.

특정 키만 자주 미스가 난다. Redis maxmemory와 eviction 정책 확인. `allkeys-lru`인데도 미스가 나면 그 키가 자주 안 읽혀서 LRU에서 빨리 쫓겨났을 가능성이 높다. 해당 키 TTL을 길게 주거나 별도 핫 캐시(메모리)에 따로 둔다.

Redis 장애 시 앱이 죽는다. cache-manager는 스토어 에러를 던지는 게 기본이다. 캐시는 실패해도 서비스가 살아있어야 하므로 wrapper에서 에러를 잡고 폴백한다.

```typescript
async safeGet<T>(key: string): Promise<T | undefined> {
  try {
    return await this.cache.get<T>(key);
  } catch (err) {
    this.logger.warn(`cache get failed: ${err.message}`);
    return undefined;
  }
}
```

캐시 실패가 잦으면 그것 자체가 알람이다. 폴백으로 묵살하고 끝내지 말고 메트릭으로 별도 카운트한다.


## 마무리

CacheModule은 30분이면 붙일 수 있지만 운영하면서 30번은 데인다. 자동 캐싱은 매력적이지만 사용자별 응답·정합성 민감 데이터에는 함정이 많다. 수동 cache-aside가 코드는 길어도 통제할 지점이 명확해서 운영이 쉽다. TTL 설계, 키 prefix·버전, 무효화 시점 이 세 가지를 결정하고 시작하면 사고가 훨씬 줄어든다. 적중률·메모리·에러 메트릭은 처음부터 같이 깔아두는 게 좋다. 캐시는 보이지 않으면 곧 거짓말을 시작한다.
