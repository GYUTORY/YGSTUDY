---
title: 캐싱 전략 (Caching Strategies)
tags: [backend, cache, redis]
updated: 2026-01-18
---

# 캐싱 전략 (Caching Strategies)

## 개요

캐시는 데이터를 빠르게 조회하기 위해 메모리에 저장한다. DB 부하를 줄이고 응답 속도를 개선한다. 하지만 캐시와 DB 간 일관성 문제가 발생한다. 적절한 캐싱 전략을 선택해야 한다.

### 왜 필요한가

**문제 상황:**

**시나리오:**
상품 상세 페이지. 초당 1,000개 요청.

**캐시 없이:**
```typescript
import { Controller, Get, Param, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Product } from './product.entity';

@Controller('products')
export class ProductController {
  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
  ) {}

  @Get(':id')
  async getProduct(@Param('id') id: string): Promise<Product> {
    const product = await this.productRepository.findOneBy({ id: Number(id) });
    if (!product) throw new NotFoundException(`Product ${id} not found`);
    return product;
  }
}
```

**문제:**
- 초당 1,000개 DB 쿼리
- 같은 상품을 반복 조회
- DB 부하 증가
- 응답 시간 느림 (평균 50ms)

**캐시 적용:**
```typescript
import { Controller, Get, Param, UseInterceptors } from '@nestjs/common';
import { CacheInterceptor, CacheKey, CacheTTL } from '@nestjs/cache-manager';

@Controller('products')
@UseInterceptors(CacheInterceptor)
export class ProductController {
  constructor(private readonly productService: ProductService) {}

  @Get(':id')
  @CacheKey('product')
  @CacheTTL(600) // 10분 (초 단위)
  async getProduct(@Param('id') id: string): Promise<Product> {
    return this.productService.getProduct(Number(id));
  }
}
```

**효과:**
- 첫 요청만 DB 조회
- 이후 요청은 캐시에서 반환
- DB 쿼리: 1,000 → 10 (새 상품만)
- 응답 시간: 50ms → 1ms

**99% DB 부하 감소, 50배 속도 향상**

## 캐시 패턴

### Cache-Aside (Lazy Loading)

**가장 많이 사용하는 패턴.** 애플리케이션이 캐시를 직접 관리한다.

**읽기:**
1. 캐시 확인
2. 캐시에 있으면 반환 (Cache Hit)
3. 없으면 DB 조회 (Cache Miss)
4. DB 결과를 캐시에 저장
5. 반환

**코드:**
```typescript
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { Product } from './product.entity';

@Injectable()
export class ProductService {
  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
    @InjectRedis() private readonly redis: Redis,
  ) {}

  async getProduct(id: number): Promise<Product> {
    const cacheKey = `product:${id}`;

    // 1. 캐시 확인
    const cached = await this.redis.get(cacheKey);
    if (cached) {
      return JSON.parse(cached) as Product; // Cache Hit
    }

    // 2. DB 조회 (Cache Miss)
    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException(`Product ${id} not found`);

    // 3. 캐시 저장 (10분 = 600초)
    await this.redis.set(cacheKey, JSON.stringify(product), 'EX', 600);

    return product;
  }
}
```

**NestJS Cache Manager 추상화:**
```typescript
import { Injectable, Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';

@Injectable()
export class ProductService {
  constructor(
    @Inject(CACHE_MANAGER) private readonly cacheManager: Cache,
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
  ) {}

  async getProduct(id: number): Promise<Product> {
    const cacheKey = `products:${id}`;
    const cached = await this.cacheManager.get<Product>(cacheKey);
    if (cached) return cached;

    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException(`Product ${id} not found`);

    await this.cacheManager.set(cacheKey, product, 600_000); // 10분 (ms)
    return product;
  }
}
```

**장점:**
- 간단하다
- 필요한 데이터만 캐시 (Lazy)
- 캐시 장애 시에도 동작 (DB로 직접 조회)

**단점:**
- Cache Miss 시 두 번의 호출 (캐시 + DB)
- 초기 요청이 느리다

#### 캐시 히트와 미스는 같은 것을 돌려주지 않는다

`JSON.parse(cached) as Product` 의 `as` 는 컴파일러에게 하는 약속일 뿐 변환이 아니다. 값은 왕복하면서 실제로 바뀐다.

```
[miss] createdAt 타입: Date   | isNew(): false
[hit ] createdAt 타입: string | 값: 2026-08-13T00:00:00.000Z
[hit ] isNew() → TypeError: cached.isNew is not a function
[hit ] createdAt.getTime() → TypeError: cached.createdAt.getTime is not a function
[hit ] instanceof Product: false
[hit ] undefined/Set 왕복: { id: 2, tags: {} }
```

- `Date` 는 ISO 문자열이 된다. `product.createdAt.getTime()` 이 **캐시 히트일 때만** 죽는다.
- 엔티티 메서드가 사라지고 `instanceof` 검사가 실패한다.
- `undefined` 필드는 통째로 없어지고 `Set` · `Map` 은 `{}` 가 된다.

증상이 히트일 때만 나타나는 점이 고약하다. 배포 직후에는 캐시가 비어 전부 미스라 멀쩡하고, 몇 분 뒤부터 일부 요청만 500 이 난다. 재현하려고 로컬에서 부르면 거기도 미스라 재현이 안 된다.

처방은 둘 중 하나다. 캐시에 **DTO 만 담아 애초에 왕복해도 같은 모양이게 만들거나**, 읽는 쪽에서 명시적으로 되살린다.

```typescript
const cached = await this.redis.get(cacheKey);
if (cached) return this.reviveProduct(JSON.parse(cached));

private reviveProduct(raw: Record<string, unknown>): Product {
  return Object.assign(new Product(), raw, {
    createdAt: new Date(raw.createdAt as string),
  });
}
```

어느 쪽이든 요점은 **"캐시에 담을 수 있는 모양"을 타입으로 따로 두는 것**이다. 엔티티를 그대로 넣으면 나중에 엔티티에 메서드나 관계를 추가할 때마다 캐시 경로가 조용히 어긋난다.

### Write-Through

쓰기 시 캐시와 DB를 동시에 업데이트한다.

**동작:**
1. 캐시 업데이트
2. DB 업데이트
3. 성공 응답

**코드:**
```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { Product } from './product.entity';

@Injectable()
export class ProductService {
  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
    @Inject(CACHE_MANAGER) private readonly cacheManager: Cache,
  ) {}

  async updateProduct(product: Product): Promise<Product> {
    // 1. DB 업데이트
    const saved = await this.productRepository.save(product);

    // 2. 캐시 업데이트 (Write-Through)
    await this.cacheManager.set(`products:${saved.id}`, saved, 600_000);

    return saved;
  }
}
```

**수동 구현 (ioredis):**
```typescript
async updateProduct(product: Product): Promise<Product> {
  // 1. DB 저장
  const saved = await this.productRepository.save(product);

  // 2. 캐시 저장
  const cacheKey = `product:${product.id}`;
  await this.redis.set(cacheKey, JSON.stringify(saved), 'EX', 600);

  return saved;
}
```

**장점:**
- 캐시와 DB가 항상 동기화
- 읽기 성능 좋음

**단점:**
- 쓰기 성능 저하 (캐시 + DB 두 번)
- 캐시에 안 쓰는 데이터도 저장될 수 있음

### Write-Behind (Write-Back)

쓰기 시 캐시만 업데이트하고 나중에 DB에 반영한다.

**동작:**
1. 캐시 업데이트
2. 즉시 성공 응답
3. 비동기로 DB 업데이트 (배치)

**코드:**
```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { Cron } from '@nestjs/schedule';
import { Product } from './product.entity';

@Injectable()
export class ProductService {
  private readonly writeQueue: Product[] = [];

  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
    @InjectRedis() private readonly redis: Redis,
  ) {}

  async updateProduct(product: Product): Promise<Product> {
    // 1. 캐시 업데이트
    const cacheKey = `product:${product.id}`;
    await this.redis.set(cacheKey, JSON.stringify(product));

    // 2. 큐에 추가
    this.writeQueue.push(product);

    return product;
  }

  @Cron('*/5 * * * * *') // 5초마다 실행
  async flushToDatabase(): Promise<void> {
    if (this.writeQueue.length === 0) return;

    // 배치로 꺼내기 (최대 100개)
    const batch = this.writeQueue.splice(0, 100);

    if (batch.length > 0) {
      // 배치로 DB 업데이트
      await this.productRepository.save(batch);
    }
  }
}
```

**장점:**
- 쓰기 성능이 매우 빠름
- DB 부하 감소 (배치 쓰기)

**단점:**
- 캐시 장애 시 데이터 손실 위험
- 캐시와 DB 불일치 기간 존재
- 구현 복잡

**사용 사례:**
- 좋아요 수, 조회수 (정확성이 덜 중요)
- 로그 집계
- 실시간 랭킹

#### 큐가 프로세스 메모리에 있으면 Write-Behind 가 아니다

`private readonly writeQueue: Product[]` 는 이 인스턴스의 힙이다. 여기서 문제가 셋 나온다.

**인스턴스마다 큐가 따로 논다.** 서버가 여러 대면 같은 상품에 대한 갱신이 각 큐로 흩어지고, 5초 뒤 각자 `save` 하면서 나중에 도착한 쪽이 이긴다. 캐시에는 최신값이 있는데 DB 에는 다른 값이 남는다. 인스턴스 수가 늘수록 어긋날 확률이 올라간다.

**배포와 재시작이 곧 데이터 손실이다.** 단점에 "캐시 장애 시 손실"이라고 적혀 있지만 실제로 훨씬 자주 일어나는 건 롤링 배포다. 종료 신호를 받고 큐를 비우는 처리가 없으면 그때마다 최대 한 주기치가 사라진다.

**실패하면 되돌릴 수 없다.** `splice` 로 꺼낸 뒤 `save` 가 실패하면 그 100건은 큐에도 없고 DB 에도 없다. 예외는 `@Cron` 밖으로 나가 로그 한 줄로 끝난다. 실패분을 다시 넣거나 별도 실패 큐로 보내는 경로가 필요하다.

제대로 하려면 큐가 **프로세스 밖**에 있어야 한다 — Redis 리스트, BullMQ, 카프카 같은 것들이다. 그러면 이번에는 "그 큐가 죽으면?" 이 남는다. 조회수·좋아요에만 쓰라는 권고가 나오는 이유가 그것이다. **정확성을 어디까지 포기할지 먼저 정하고 고르는 패턴**이지, 쓰기가 빠르다는 이유로 고르는 패턴이 아니다.

### Read-Through

캐시가 DB 조회를 대신한다. 애플리케이션은 캐시만 접근한다.

**동작:**
1. 애플리케이션 → 캐시 요청
2. 캐시에 있으면 반환
3. 없으면 캐시가 DB 조회
4. 캐시에 저장 후 반환

**특징:**
- Cache-Aside와 비슷하지만 캐시가 주도
- NestJS에서는 Cache Manager 커스텀 스토어로 구현 가능
- 전용 솔루션 필요 시 Redis + 자체 캐시 로더 패턴 사용

## 로컬 캐시 vs 분산 캐시

### 로컬 캐시 (In-Memory Cache Manager)

애플리케이션 메모리에 저장.

**NestJS Cache Manager 설정 (메모리):**
```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';

@Module({
  imports: [
    CacheModule.register({
      isGlobal: true,
      ttl: 600_000,  // 10분 (ms)
      max: 10_000,   // 최대 항목 수
    }),
  ],
})
export class AppModule {}
```

**사용:**
```typescript
import { Injectable, Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';

@Injectable()
export class ProductService {
  constructor(@Inject(CACHE_MANAGER) private readonly cacheManager: Cache) {}

  async getProduct(id: number): Promise<Product> {
    const cached = await this.cacheManager.get<Product>(`products:${id}`);
    if (cached) return cached;

    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException();
    await this.cacheManager.set(`products:${id}`, product, 600_000);
    return product;
  }
}
```

**장점:**
- 매우 빠름 (네트워크 없음)
- 간단함
- 비용 없음

**단점:**
- 서버마다 다른 캐시 (불일치)
- 메모리 제한
- 서버 재시작 시 캐시 소실

**사용 사례:**
- 설정 값 (변경 없음)
- 코드 테이블
- 서버별로 달라도 되는 데이터

### 분산 캐시 (Redis)

별도 서버에 저장. 모든 애플리케이션 서버가 공유.

**Redis 설정 (NestJS Cache Manager + Redis Store):**
```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { redisStore } from 'cache-manager-ioredis-yet';

@Module({
  imports: [
    CacheModule.registerAsync({
      isGlobal: true,
      useFactory: async () => ({
        store: await redisStore({
          host: 'localhost',
          port: 6379,
        }),
        ttl: 600_000, // 10분 (ms)
      }),
    }),
  ],
})
export class AppModule {}
```

**ioredis 직접 사용:**
```typescript
import { Module } from '@nestjs/common';
import { RedisModule } from '@nestjs-modules/ioredis';

@Module({
  imports: [
    RedisModule.forRoot({
      type: 'single',
      url: 'redis://localhost:6379',
    }),
  ],
})
export class AppModule {}
```

**장점:**
- 모든 서버가 공유 (일관성)
- 메모리 확장 가능
- 영속성 (AOF/RDB)

**단점:**
- 네트워크 지연 (0.5-2ms)
- 비용 (인프라)
- 장애 시 영향 큼

**사용 사례:**
- 세션
- 사용자 데이터
- 여러 서버에서 접근하는 데이터

### 2단계 캐시 (L1 + L2)

로컬 캐시 (L1)와 분산 캐시 (L2)를 함께 사용.

**구조:**
```
요청 → L1 (메모리) → L2 (Redis) → DB
       0.01ms          1ms          50ms
```

**코드:**
```typescript
import { Injectable, Inject, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { Product } from './product.entity';

@Injectable()
export class ProductService {
  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
    @InjectRedis() private readonly redis: Redis,     // L2 (Redis)
    @Inject(CACHE_MANAGER) private readonly l1Cache: Cache, // L1 (메모리)
  ) {}

  async getProduct(id: number): Promise<Product> {
    const l1Key = `products:${id}`;
    const l2Key = `product:${id}`;

    // L1 캐시 조회
    const l1Cached = await this.l1Cache.get<Product>(l1Key);
    if (l1Cached) return l1Cached;

    // L2 캐시 (Redis) 조회
    const l2Raw = await this.redis.get(l2Key);
    if (l2Raw) {
      const product = JSON.parse(l2Raw) as Product;
      // L1에 저장 (1분)
      await this.l1Cache.set(l1Key, product, 60_000);
      return product;
    }

    // DB 조회
    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException(`Product ${id} not found`);

    // L2 캐시 저장 (10분)
    await this.redis.set(l2Key, JSON.stringify(product), 'EX', 600);
    // L1 캐시 저장 (1분)
    await this.l1Cache.set(l1Key, product, 60_000);

    return product;
  }

  async updateProduct(product: Product): Promise<void> {
    // DB 업데이트
    await this.productRepository.save(product);

    // L2 캐시 업데이트
    const l2Key = `product:${product.id}`;
    await this.redis.set(l2Key, JSON.stringify(product), 'EX', 600);

    // L1 캐시 무효화
    await this.l1Cache.del(`products:${product.id}`);
  }
}
```

**효과:**
- 대부분 L1에서 처리 (매우 빠름)
- L1 Miss 시 L2에서 처리 (빠름)
- 서버 간 일관성 유지 (L2 공유)

## 캐시 일관성

### 문제

캐시와 DB가 다른 값을 가질 수 있다.

**시나리오:**
```
서버 A: 상품 가격 변경 (10,000원 → 15,000원)
  1. DB 업데이트 (15,000원)
  2. 캐시 무효화 (삭제)

서버 B: 동시에 상품 조회
  1. 캐시 확인 (없음)
  2. DB 조회 (15,000원)
  3. 캐시 저장 (15,000원)

서버 C: 상품 조회
  1. 캐시 확인 (10,000원) ← 오래된 캐시
```

### 해결 1: Cache Invalidation

캐시를 삭제한다. 다음 조회 시 DB에서 가져온다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class ProductService {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async updateProduct(id: number, product: Partial<Product>): Promise<void> {
    await this.productRepository.save({ id, ...product });

    // 캐시 삭제
    await this.redis.del(`product:${id}`);
  }

  // 전체 삭제 (패턴 기반)
  async updateAllProducts(): Promise<void> {
    const keys = await this.redis.keys('product:*');
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }
}
```

**문제:**
삭제와 새로운 캐시 저장 사이에 짧은 불일치 기간 존재.

**`KEYS` 는 운영 Redis 에서 쓰지 않는다.** `redis.keys('product:*')` 는 전체 키스페이스를 훑는다. Redis 는 명령 하나를 처리하는 동안 다른 요청을 받지 않으므로, 키가 많으면 그 시간만큼 **Redis 를 쓰는 모든 서비스가 함께 멈춘다.** 순회가 필요하면 `SCAN` 으로 커서를 돌리고, 더 나은 방법은 지워야 할 키를 집합(Set)으로 따로 모아 두고 그것만 지우는 것이다. 이어지는 `del(...keys)` 도 같은 문제를 갖는다 — 수만 개를 스프레드로 넘기면 명령 하나가 지나치게 커지고 인자 개수 한계에 걸린다.

**삭제 순서에는 경쟁이 남는다.** 위 코드는 DB 저장 후 캐시 삭제인데, 아래 순서로 얽히면 오래된 값이 캐시에 자리 잡는다.

```
읽기 R: 캐시 미스 → DB 조회 (10,000원을 읽는다)
쓰기 W: DB 갱신 (15,000원) → 캐시 삭제
읽기 R: 캐시에 저장 (10,000원)      ← 삭제보다 나중에 도착한다
```

이후 TTL 이 끝날 때까지 모두가 10,000원을 본다. 삭제가 아무 일도 하지 않은 셈이고, 로그에는 아무것도 남지 않는다. 문서 앞의 시나리오가 그리려던 것이 실제로는 이 모양이다.

완전히 막는 방법은 없고 확률을 낮추는 방법들만 있다.

| 방법 | 남는 문제 |
|---|---|
| 쓰기 전후로 두 번 삭제 | 두 번째 삭제를 언제 할지 정할 근거가 없다 |
| 삭제 대신 갱신 | 동시 쓰기끼리 다시 순서 경쟁이 생긴다 |
| 저장 시 버전·타임스탬프 비교 | 읽기 경로가 복잡해진다 (아래 Versioning) |
| TTL 을 짧게 | 불일치 기간의 상한만 정할 뿐 없애지는 못한다 |

**어떤 방법도 불일치를 0 으로 만들지 못한다.** 그래서 캐시를 붙이기 전에 "이 값이 몇 초 낡아도 되는가"를 먼저 답해야 한다. 답이 "1초도 안 된다"면 그 값은 캐시 대상이 아니다.

### 해결 2: Pub/Sub으로 캐시 동기화

업데이트 시 모든 서버에 알림.

**Redis Pub/Sub:**
```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';

@Injectable()
export class ProductService implements OnModuleInit {
  // Pub/Sub용 별도 Redis 클라이언트 (subscriber는 전용 커넥션 필요)
  private readonly subscriber: Redis;

  constructor(
    @InjectRedis() private readonly redis: Redis,
    @Inject(CACHE_MANAGER) private readonly localCache: Cache,
  ) {
    this.subscriber = new Redis({ host: 'localhost', port: 6379 });
  }

  async onModuleInit(): Promise<void> {
    // product-updates 채널 구독
    await this.subscriber.subscribe('product-updates');
    this.subscriber.on('message', (_channel: string, productId: string) => {
      this.handleProductUpdate(productId);
    });
  }

  async updateProduct(product: Product): Promise<void> {
    // 1. DB 업데이트
    await this.productRepository.save(product);

    // 2. Redis 캐시 업데이트
    await this.redis.set(
      `product:${product.id}`,
      JSON.stringify(product),
      'EX',
      600,
    );

    // 3. 모든 서버에 알림
    await this.redis.publish('product-updates', String(product.id));
  }

  private handleProductUpdate(productId: string): void {
    // 로컬 캐시 무효화
    void this.localCache.del(`products:${productId}`);
  }
}
```

### 해결 3: Versioning

캐시에 버전을 포함한다.

```typescript
interface CachedProduct {
  id: number;
  name: string;
  price: number;
  version: number;  // 버전
  updatedAt: string;
}

@Injectable()
export class ProductService {
  async getProduct(id: number): Promise<Product> {
    const key = `product:${id}`;
    const raw = await this.redis.get(key);

    if (raw) {
      const cached = JSON.parse(raw) as CachedProduct;

      // DB 버전 확인
      const dbVersion = await this.productRepository
        .createQueryBuilder('p')
        .select('p.version')
        .where('p.id = :id', { id })
        .getOne();

      if (dbVersion && cached.version === dbVersion.version) {
        return cached as unknown as Product; // 최신
      }
      // 버전 불일치, DB 재조회
    }

    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException();
    await this.redis.set(key, JSON.stringify(product), 'EX', 600);
    return product;
  }
}
```

## 캐시 무효화

### TTL (Time To Live)

시간 기반 만료.

```typescript
// ioredis: 10분 후 만료
await this.redis.set(key, JSON.stringify(value), 'EX', 600);

// NestJS Cache Manager
await this.cacheManager.set(key, value, 600_000); // ms 단위
```

**환경 변수 / 모듈 설정:**
```typescript
CacheModule.register({
  ttl: 600_000, // 10분 (ms)
})
```

**장점:**
- 자동
- 간단

**단점:**
- 만료 전까지 오래된 데이터
- 적절한 TTL 설정 어려움

### 수동 무효화

업데이트 시 명시적으로 삭제.

```typescript
// 단일 키 삭제
await this.redis.del(`product:${id}`);

// Cache Manager로 삭제
await this.cacheManager.del(`products:${id}`);

// 패턴으로 전체 삭제
const keys = await this.redis.keys('product:*');
if (keys.length > 0) {
  await this.redis.del(...keys);
}
```

### 태그 기반 무효화

관련 캐시를 그룹으로 삭제.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class ProductService {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async getProduct(id: number): Promise<Product> {
    const key = `product:${id}`;
    const raw = await this.redis.get(key);

    if (raw) return JSON.parse(raw) as Product;

    const product = await this.productRepository.findOneBy({ id });
    if (!product) throw new NotFoundException();

    // 캐시 저장 + 태그 (카테고리 → 상품 키 매핑)
    await this.redis.set(key, JSON.stringify(product), 'EX', 600);
    await this.redis.sadd(`category:${product.categoryId}`, key);

    return product;
  }

  async updateCategory(categoryId: number): Promise<void> {
    // 해당 카테고리의 모든 상품 캐시 삭제
    const keys = await this.redis.smembers(`category:${categoryId}`);
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
    await this.redis.del(`category:${categoryId}`);
  }
}
```

## 캐시 스탬피드 방지

### 문제

인기 있는 데이터의 캐시가 만료되면 동시에 많은 요청이 DB로 몰린다.

**시나리오:**
```
캐시 만료 (인기 상품)
  ↓
동시에 1,000개 요청
  ↓
1,000개 DB 쿼리 (동일한 상품)
  ↓
DB 과부하
```

### 해결 1: 단일 프로세스 Mutex Lock

첫 요청만 DB 조회, 나머지는 대기.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class ProductService {
  // 키별 Promise를 보관해 단일 프로세스 내 중복 요청 방지
  private readonly inflight = new Map<string, Promise<Product>>();

  constructor(
    @InjectRedis() private readonly redis: Redis,
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
  ) {}

  async getProduct(id: number): Promise<Product> {
    const key = `product:${id}`;

    // 캐시 확인
    const cached = await this.redis.get(key);
    if (cached) return JSON.parse(cached) as Product;

    // 이미 진행 중인 요청이 있으면 동일 Promise 반환 (Double-check 효과)
    const existing = this.inflight.get(key);
    if (existing) return existing;

    const loadPromise = (async (): Promise<Product> => {
      try {
        // Double-check after acquiring
        const rechecked = await this.redis.get(key);
        if (rechecked) return JSON.parse(rechecked) as Product;

        // DB 조회
        const product = await this.productRepository.findOneBy({ id });
        if (!product) throw new NotFoundException(`Product ${id} not found`);

        // 캐시 저장
        await this.redis.set(key, JSON.stringify(product), 'EX', 600);
        return product;
      } finally {
        this.inflight.delete(key);
      }
    })();

    this.inflight.set(key, loadPromise);
    return loadPromise;
  }
}
```

### 해결 2: Redis 분산 Lock

분산 환경에서 Lock.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { randomUUID } from 'crypto';

@Injectable()
export class ProductService {
  constructor(
    @InjectRedis() private readonly redis: Redis,
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
  ) {}

  async getProduct(id: number): Promise<Product> {
    const key = `product:${id}`;
    const cached = await this.redis.get(key);
    if (cached) return JSON.parse(cached) as Product;

    const lockKey = `lock:product:${id}`;
    const lockValue = randomUUID();

    // Redis 분산 Lock (NX: 없을 때만 설정, EX: 5초 자동 해제)
    const acquired = await this.redis.set(lockKey, lockValue, 'NX', 'EX', 5);

    if (acquired === 'OK') {
      try {
        // Double-check
        const rechecked = await this.redis.get(key);
        if (rechecked) return JSON.parse(rechecked) as Product;

        // DB 조회
        const product = await this.productRepository.findOneBy({ id });
        if (!product) throw new NotFoundException(`Product ${id} not found`);

        await this.redis.set(key, JSON.stringify(product), 'EX', 600);
        return product;
      } finally {
        // 본인 Lock만 해제 (Lua 스크립트로 원자적 처리)
        const releaseLua = `
          if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
          else return 0 end`;
        await this.redis.eval(releaseLua, 1, lockKey, lockValue);
      }
    }

    // Lock 획득 실패 시 DB 직접 조회
    const fallback = await this.productRepository.findOneBy({ id });
    if (!fallback) throw new NotFoundException(`Product ${id} not found`);
    return fallback;
  }
}
```

**Lock 획득에 실패한 요청이 DB 로 직행하면 스탬피드는 그대로다.** 위 코드의 마지막 세 줄이 그렇다. 동시 1,000 요청 중 하나가 Lock 을 잡고 나머지 999 는 곧장 DB 를 친다 — 막으려던 그림 그대로다. 실패한 쪽은 짧게 기다렸다가 캐시를 다시 보는 형태여야 한다.

```typescript
for (let i = 0; i < 10; i++) {
  await sleep(50);
  const filled = await this.redis.get(key);
  if (filled) return JSON.parse(filled) as Product;
}
// 여기까지 왔으면 그때 DB 로 내려가거나 503 을 준다
```

대기에도 대가가 있다. Lock 을 쥔 요청이 느리면 나머지가 다 같이 느려지고, 그 요청이 죽으면 Lock TTL 만큼 아무도 진행하지 못한다. **스탬피드 방지란 "많은 요청을 DB 로 보내는 것"과 "많은 요청을 기다리게 하는 것" 중 후자를 고르는 일이다.** 응답 시간 상한이 빡빡한 API 라면 오히려 전자가 나을 수도 있다.

Lock TTL 도 임의로 정하면 안 된다. DB 조회가 TTL 보다 오래 걸리면 Lock 이 먼저 풀려 두 번째 요청이 들어오고, 첫 번째가 뒤늦게 끝나며 오래된 값을 캐시에 덮어쓴다. Lua 로 본인 Lock 만 지우게 해 뒀으니 남의 Lock 을 삭제하는 사고는 없지만, **중복 실행 자체는 막지 못한다.** TTL 은 조회 시간의 최악값보다 넉넉해야 하고, 그러면 이번엔 장애 시 정지 시간이 길어진다.

### 해결 3: Probabilistic Early Expiration

만료 전에 미리 갱신.

```typescript
async getProduct(id: number): Promise<Product> {
  const key = `product:${id}`;
  const ttl = await this.redis.ttl(key); // 남은 TTL (초)

  // 만료까지 1분 미만이고 랜덤으로 선택되면 비동기 갱신
  if (ttl !== null && ttl < 60 && Math.random() < 0.1) {
    // 비동기로 갱신 (현재 요청은 캐시 반환)
    void (async () => {
      const product = await this.productRepository.findOneBy({ id });
      if (product) {
        await this.redis.set(key, JSON.stringify(product), 'EX', 600);
      }
    })();
  }

  const raw = await this.redis.get(key);
  if (raw) return JSON.parse(raw) as Product;

  // 캐시 없으면 DB 조회
  const product = await this.productRepository.findOneBy({ id });
  if (!product) throw new NotFoundException(`Product ${id} not found`);
  await this.redis.set(key, JSON.stringify(product), 'EX', 600);
  return product;
}
```

**`ttl` 의 반환값을 확인하지 않고 있다.** Redis 의 `TTL` 은 키가 없으면 `-2`, 만료 시간이 설정돼 있지 않으면 `-1` 을 돌려준다([TTL 명령 문서](https://redis.io/docs/latest/commands/ttl/)). `ttl !== null && ttl < 60` 은 이 둘을 전부 통과시킨다. 그래서 **캐시가 아예 없을 때도 백그라운드 갱신이 돌고**, 바로 아래 미스 경로가 다시 DB 를 조회한다. 같은 상품을 두 번 읽는 것이다. 조건을 아래처럼 좁힌다.

```typescript
if (ttl > 0 && ttl < 60 && Math.random() < 0.1) { /* 미리 갱신 */ }
```

백그라운드 갱신에 예외 처리가 없는 것도 문제다. `void (async () => { ... })()` 안에서 DB 가 던지면 처리되지 않은 거부가 되고, 최근 Node 는 기본값으로 프로세스를 종료한다. 이 형태를 쓸 거면 `.catch()` 를 반드시 붙인다.

읽기 한 번에 Redis 왕복이 `ttl` + `get` 두 번이라는 점도 감안한다. 원래 목적이 DB 부하를 줄이는 것인데 캐시 부하를 두 배로 만들면 손익이 애매해진다. 값과 만료 시각을 함께 저장해 한 번의 `get` 으로 둘 다 얻는 편이 흔한 구성이다.

## 실무 패턴

### 사용자 세션

**Redis (ioredis):**
```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

interface UserSession {
  userId: number;
  email: string;
  roles: string[];
}

@Injectable()
export class SessionService {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async saveSession(token: string, session: UserSession): Promise<void> {
    await this.redis.set(
      `session:${token}`,
      JSON.stringify(session),
      'EX',
      7200, // 2시간 만료
    );
  }

  async getSession(token: string): Promise<UserSession | null> {
    const raw = await this.redis.get(`session:${token}`);
    if (!raw) return null;

    // 활동 시 TTL 갱신 (Sliding Window)
    await this.redis.expire(`session:${token}`, 7200);

    return JSON.parse(raw) as UserSession;
  }
}
```

### API 응답 캐싱

```typescript
import { Controller, Get, Param, UseInterceptors, Header } from '@nestjs/common';
import { CacheInterceptor, CacheKey, CacheTTL } from '@nestjs/cache-manager';

@Controller('api/products')
@UseInterceptors(CacheInterceptor)
export class ProductController {
  constructor(private readonly productService: ProductService) {}

  @Get(':id')
  @CacheKey('api:product')
  @CacheTTL(600_000) // 10분 (ms)
  @Header('Cache-Control', 'max-age=600, public')
  async getProduct(@Param('id') id: string): Promise<ProductResponse> {
    const product = await this.productService.getProduct(Number(id));
    return ProductResponse.from(product);
  }
}
```

### 랭킹/리더보드

**Redis Sorted Set:**
```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class LeaderboardService {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  async updateScore(userId: string, score: number): Promise<void> {
    await this.redis.zadd('leaderboard', score, userId);
  }

  async getTopUsers(count: number): Promise<string[]> {
    // ZREVRANGE: 높은 점수 순으로 반환
    return this.redis.zrevrange('leaderboard', 0, count - 1);
  }

  async getRank(userId: string): Promise<number | null> {
    const rank = await this.redis.zrevrank('leaderboard', userId);
    return rank; // null이면 순위 없음
  }
}
```

## 모니터링

### Cache Manager 통계

```typescript
import { Injectable, Inject } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { Cron } from '@nestjs/schedule';
import { Logger } from '@nestjs/common';

@Injectable()
export class CacheMonitoringService {
  private readonly logger = new Logger(CacheMonitoringService.name);

  constructor(@Inject(CACHE_MANAGER) private readonly cacheManager: Cache) {}

  @Cron('0 * * * * *') // 매분 실행
  async logCacheStats(): Promise<void> {
    // cache-manager v5는 store 접근으로 통계 확인 가능
    const store = this.cacheManager.store as Record<string, unknown>;
    this.logger.log(`Cache store type: ${store?.constructor?.name ?? 'unknown'}`);
    // Redis store의 경우 INFO 명령으로 통계 확인
  }
}
```

### Redis Monitoring

```bash
# Redis 정보
redis-cli INFO stats

# 키 개수
redis-cli DBSIZE

# 메모리 사용량
redis-cli INFO memory

# 느린 쿼리
redis-cli SLOWLOG GET 10
```

## 참고

- NestJS Cache Manager: https://docs.nestjs.com/techniques/caching
- cache-manager: https://github.com/node-cache-manager/node-cache-manager
- ioredis: https://github.com/luin/ioredis
- @nestjs-modules/ioredis: https://github.com/nest-modules/ioredis

---
이 문서는 [캐싱 허브](../../_hub/캐싱.md)의 일부입니다.


