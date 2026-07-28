---
title: 캐싱 전략 (Caching Strategies)
tags: [backend, caching, redis, caffeine, cache-aside, write-through, write-behind, cache-invalidation]
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


