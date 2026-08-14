---
title: Abstract Factory Pattern (추상 팩토리 패턴)
tags: [design-patterns, javascript, typescript, architecture]
updated: 2026-03-30
---

# Abstract Factory Pattern (추상 팩토리 패턴)

## 한 줄 정의

관련된 객체 묶음을 한 번에 생성하되, 구체 클래스를 클라이언트가 모르게 하는 패턴이다.

Factory Method가 "하나의 객체를 어떻게 만들까"에 집중한다면, Abstract Factory는 "관련된 여러 객체를 어떤 조합으로 만들까"에 집중한다.

## Factory Method와 실무에서 헷갈리는 지점

면접에서 "Factory Method와 Abstract Factory 차이"를 물으면 대부분 "하나 vs 여러 개"라고 답한다. 틀린 말은 아닌데, 실무에서의 차이는 좀 다르다.

### Factory Method로 충분한 경우

```typescript
// 결제 수단 하나만 만들면 된다
interface PaymentProcessor {
  charge(amount: number): Promise<PaymentResult>;
}

class PaymentProcessorFactory {
  static create(type: string): PaymentProcessor {
    switch (type) {
      case 'stripe': return new StripeProcessor();
      case 'toss': return new TossProcessor();
      default: throw new Error(`Unknown type: ${type}`);
    }
  }
}

// 사용
const processor = PaymentProcessorFactory.create('stripe');
await processor.charge(10000);
```

이건 Factory Method로 충분하다. 생성할 객체가 하나이고, 그 객체만 갈아끼우면 되니까.

### Abstract Factory가 필요해지는 시점

문제는 결제 수단을 바꾸면 **연관된 다른 것들도 함께 바뀌어야 할 때** 발생한다.

```typescript
// Stripe를 쓰면 Stripe용 웹훅 핸들러, Stripe용 영수증 포맷터를 써야 한다
// Toss를 쓰면 Toss용 웹훅 핸들러, Toss용 영수증 포맷터를 써야 한다
// 이걸 Factory Method 3개로 따로 만들면?

const processor = PaymentProcessorFactory.create('stripe');
const webhook = WebhookHandlerFactory.create('toss');  // 실수로 toss
const receipt = ReceiptFormatterFactory.create('stripe');
```

Stripe 결제인데 Toss 웹훅 핸들러를 붙이는 사고가 난다. 타입이 맞으니 컴파일 에러도 안 나고, 런타임에 웹훅 검증이 실패하면서 결제 확인이 안 되는 장애로 이어진다.

Abstract Factory는 이런 **조합 불일치 사고를 구조적으로 막는 것**이 핵심이다.

```typescript
interface PaymentInfraFactory {
  createProcessor(): PaymentProcessor;
  createWebhookHandler(): WebhookHandler;
  createReceiptFormatter(): ReceiptFormatter;
}

class StripeInfraFactory implements PaymentInfraFactory {
  createProcessor() { return new StripeProcessor(); }
  createWebhookHandler() { return new StripeWebhookHandler(); }
  createReceiptFormatter() { return new StripeReceiptFormatter(); }
}

// 팩토리 하나에서 꺼내니까 조합이 꼬일 수가 없다
const factory = getPaymentFactory('stripe');
const processor = factory.createProcessor();
const webhook = factory.createWebhookHandler();
```

**정리하면:**

| 상황 | 패턴 |
|------|------|
| 타입별로 객체 하나를 갈아끼운다 | Factory Method |
| 타입별로 **연관 객체 묶음**을 갈아끼운다 | Abstract Factory |
| 묶음인데 조합이 잘못되면 런타임 장애가 난다 | Abstract Factory가 거의 필수 |

## 환경별 서비스 조합 생성

백엔드에서 Abstract Factory를 가장 자주 쓰게 되는 상황이 환경별 인프라 구성이다. dev에서는 로컬 DB + 인메모리 캐시, prod에서는 RDS + ElastiCache를 쓰는 식이다.

### 환경 설정이 엉키는 전형적 사례

```typescript
// config/database.ts
function getDatabaseConfig() {
  if (process.env.NODE_ENV === 'production') {
    return { host: process.env.RDS_HOST, ssl: true, poolSize: 20 };
  }
  return { host: 'localhost', ssl: false, poolSize: 5 };
}

// config/cache.ts
function getCacheConfig() {
  if (process.env.NODE_ENV === 'production') {
    return { host: process.env.ELASTICACHE_HOST, cluster: true };
  }
  return { host: 'localhost', cluster: false };
}

// config/queue.ts
function getQueueConfig() {
  if (process.env.NODE_ENV === 'production') {
    return { host: process.env.SQS_ENDPOINT, region: 'ap-northeast-2' };
  }
  return { host: 'localhost', port: 6379 }; // 로컬에서는 BullMQ
}
```

파일 3개에 환경 분기가 흩어져 있다. staging 환경을 추가하면? 3개 파일을 다 고쳐야 한다. 하나라도 빠뜨리면 staging에서 prod DB를 바라보는 사고가 난다.

### Abstract Factory로 환경별 조합 묶기

```typescript
// infrastructure/types.ts
interface Database {
  query<T>(sql: string, params?: unknown[]): Promise<T[]>;
  disconnect(): Promise<void>;
}

interface CacheStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSeconds?: number): Promise<void>;
}

interface MessageQueue {
  publish(topic: string, message: unknown): Promise<void>;
  subscribe(topic: string, handler: (msg: unknown) => void): Promise<void>;
}

interface InfrastructureFactory {
  createDatabase(): Database;
  createCache(): CacheStore;
  createQueue(): MessageQueue;
}
```

```typescript
// infrastructure/local-factory.ts
class LocalDatabaseAdapter implements Database {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      host: 'localhost',
      port: 5432,
      database: 'app_dev',
      max: 5,
    });
  }

  async query<T>(sql: string, params?: unknown[]): Promise<T[]> {
    const result = await this.pool.query(sql, params);
    return result.rows as T[];
  }

  async disconnect() {
    await this.pool.end();
  }
}

class InMemoryCache implements CacheStore {
  private store = new Map<string, { value: string; expiresAt: number }>();

  async get(key: string): Promise<string | null> {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      this.store.delete(key);
      return null;
    }
    return entry.value;
  }

  async set(key: string, value: string, ttlSeconds = 3600) {
    this.store.set(key, {
      value,
      expiresAt: Date.now() + ttlSeconds * 1000,
    });
  }
}

class LocalQueueAdapter implements MessageQueue {
  private handlers = new Map<string, ((msg: unknown) => void)[]>();

  async publish(topic: string, message: unknown) {
    const topicHandlers = this.handlers.get(topic) || [];
    // 로컬에서는 동기적으로 바로 실행
    topicHandlers.forEach(h => h(message));
  }

  async subscribe(topic: string, handler: (msg: unknown) => void) {
    const existing = this.handlers.get(topic) || [];
    existing.push(handler);
    this.handlers.set(topic, existing);
  }
}

class LocalInfraFactory implements InfrastructureFactory {
  createDatabase(): Database { return new LocalDatabaseAdapter(); }
  createCache(): CacheStore { return new InMemoryCache(); }
  createQueue(): MessageQueue { return new LocalQueueAdapter(); }
}
```

```typescript
// infrastructure/production-factory.ts
class RDSDatabase implements Database {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      host: process.env.RDS_HOST,
      port: 5432,
      database: process.env.RDS_DATABASE,
      user: process.env.RDS_USER,
      password: process.env.RDS_PASSWORD,
      max: 20,
      ssl: { rejectUnauthorized: true },
    });
  }

  async query<T>(sql: string, params?: unknown[]): Promise<T[]> {
    const result = await this.pool.query(sql, params);
    return result.rows as T[];
  }

  async disconnect() {
    await this.pool.end();
  }
}

class ElastiCacheAdapter implements CacheStore {
  private client: Redis;

  constructor() {
    this.client = new Redis({
      host: process.env.ELASTICACHE_HOST,
      port: 6379,
      tls: {},
    });
  }

  async get(key: string): Promise<string | null> {
    return this.client.get(key);
  }

  async set(key: string, value: string, ttlSeconds = 3600) {
    await this.client.setex(key, ttlSeconds, value);
  }
}

class SQSQueue implements MessageQueue {
  private sqs: SQSClient;

  constructor() {
    this.sqs = new SQSClient({ region: 'ap-northeast-2' });
  }

  async publish(topic: string, message: unknown) {
    await this.sqs.send(new SendMessageCommand({
      QueueUrl: `${process.env.SQS_BASE_URL}/${topic}`,
      MessageBody: JSON.stringify(message),
    }));
  }

  async subscribe(topic: string, handler: (msg: unknown) => void) {
    // SQS 폴링 로직 — 실제로는 별도 워커에서 실행
    const poll = async () => {
      const response = await this.sqs.send(new ReceiveMessageCommand({
        QueueUrl: `${process.env.SQS_BASE_URL}/${topic}`,
        WaitTimeSeconds: 20,
      }));
      for (const msg of response.Messages || []) {
        handler(JSON.parse(msg.Body!));
      }
    };
    setInterval(poll, 1000);
  }
}

class ProductionInfraFactory implements InfrastructureFactory {
  createDatabase(): Database { return new RDSDatabase(); }
  createCache(): CacheStore { return new ElastiCacheAdapter(); }
  createQueue(): MessageQueue { return new SQSQueue(); }
}
```

> `SQSQueue.subscribe` 의 폴링 부분은 그대로 쓰면 안 된다. `WaitTimeSeconds: 20` 짜리 롱폴링을 `setInterval(poll, 1000)` 으로 돌리는데, `setInterval` 은 앞 실행이 끝나기를 기다리지 않는다. 폴 하나가 20초 걸리면 그동안 19번이 더 시작돼 요청이 중첩 누적된다. 200ms 걸리는 작업을 20ms 간격으로 돌려 보면 300ms 만에 동시 실행이 10개까지 올라간다. 폴링은 앞 실행이 끝난 뒤 다음을 예약하는 형태(`while` 루프 + `await`, 또는 `setTimeout` 재귀)로 쓴다.

```typescript
// infrastructure/index.ts
function createInfraFactory(): InfrastructureFactory {
  switch (process.env.NODE_ENV) {
    case 'production':
      return new ProductionInfraFactory();
    case 'staging':
      return new StagingInfraFactory(); // staging은 prod DB + 인메모리 큐 조합 등
    default:
      return new LocalInfraFactory();
  }
}
```

staging을 추가할 때 `StagingInfraFactory` 하나만 만들면 된다. 환경 분기가 한 곳에 모여 있으니 "staging에서 prod DB를 바라보는" 실수가 구조적으로 안 생긴다.

## 멀티 테넌트 인프라 구성

SaaS를 만들다 보면 테넌트(고객사)마다 다른 인프라 조합이 필요한 경우가 생긴다. Enterprise 고객은 전용 DB, Free 고객은 공유 DB 같은 식이다.

```typescript
// tenant/types.ts
interface TenantInfraFactory {
  createDatabase(): Database;
  createStorage(): FileStorage;
  createNotifier(): Notifier;
}

// tenant/shared-factory.ts — Free/Basic 플랜
class SharedInfraFactory implements TenantInfraFactory {
  constructor(private tenantId: string) {}

  createDatabase(): Database {
    // 공유 DB에 테넌트 ID로 row-level isolation
    return new SharedDatabase(this.tenantId);
  }

  createStorage(): FileStorage {
    // 공유 S3 버킷, prefix로 테넌트 구분
    return new SharedS3Storage(`tenants/${this.tenantId}`);
  }

  createNotifier(): Notifier {
    return new EmailNotifier(); // 이메일만 지원
  }
}

// tenant/dedicated-factory.ts — Enterprise 플랜
class DedicatedInfraFactory implements TenantInfraFactory {
  constructor(private tenantConfig: TenantConfig) {}

  createDatabase(): Database {
    // 전용 DB 인스턴스
    return new DedicatedDatabase({
      host: this.tenantConfig.dbHost,
      database: this.tenantConfig.dbName,
    });
  }

  createStorage(): FileStorage {
    // 전용 S3 버킷
    return new DedicatedS3Storage(this.tenantConfig.bucketName);
  }

  createNotifier(): Notifier {
    // Slack + 이메일 + 웹훅 다 지원
    return new MultiChannelNotifier(this.tenantConfig.notificationChannels);
  }
}
```

```typescript
// tenant/factory-registry.ts
class TenantInfraRegistry {
  private factories = new Map<string, TenantInfraFactory>();

  async getFactory(tenantId: string): Promise<TenantInfraFactory> {
    if (this.factories.has(tenantId)) {
      return this.factories.get(tenantId)!;
    }

    const tenantConfig = await this.loadTenantConfig(tenantId);
    const factory = this.createFactoryForPlan(tenantId, tenantConfig);
    this.factories.set(tenantId, factory);
    return factory;
  }

  private createFactoryForPlan(
    tenantId: string,
    config: TenantConfig
  ): TenantInfraFactory {
    switch (config.plan) {
      case 'enterprise':
        return new DedicatedInfraFactory(config);
      case 'free':
      case 'basic':
        return new SharedInfraFactory(tenantId);
      default:
        return new SharedInfraFactory(tenantId);
    }
  }

  private async loadTenantConfig(tenantId: string): Promise<TenantConfig> {
    // DB나 설정 서비스에서 테넌트 정보 로드
    // 실제로는 캐싱도 해야 한다
  }
}
```

```typescript
// middleware/tenant-context.ts — Express 미들웨어 예시
async function tenantMiddleware(req: Request, res: Response, next: NextFunction) {
  const tenantId = req.headers['x-tenant-id'] as string;
  if (!tenantId) {
    return res.status(400).json({ error: 'x-tenant-id header required' });
  }

  const factory = await tenantRegistry.getFactory(tenantId);
  const infra = {
    db: factory.createDatabase(),
    storage: factory.createStorage(),
    notifier: factory.createNotifier(),
  };

  req.tenantInfra = infra;
  next();
}

// routes/documents.ts
router.post('/documents', async (req, res) => {
  const { db, storage, notifier } = req.tenantInfra;

  const doc = await db.query('INSERT INTO documents ...');
  await storage.upload(req.file.buffer, `docs/${doc.id}`);
  await notifier.send('document.created', { documentId: doc.id });

  res.json(doc);
});
```

핵심은 `router.post` 핸들러가 테넌트의 플랜이 뭔지 전혀 모른다는 점이다. Enterprise든 Free든 같은 코드가 동작하고, 실제 인프라 차이는 팩토리가 결정한다.

### 테넌트별 팩토리에서 조심할 점

팩토리를 요청마다 새로 만들면 DB 커넥션 풀이 요청 수만큼 생긴다. 팩토리 자체는 캐싱하고, 커넥션 같은 리소스는 팩토리 내부에서 재사용해야 한다.

```typescript
class DedicatedDatabase implements Database {
  private static pools = new Map<string, Pool>();

  constructor(private config: { host: string; database: string }) {}

  private getPool(): Pool {
    const key = `${this.config.host}:${this.config.database}`;
    if (!DedicatedDatabase.pools.has(key)) {
      DedicatedDatabase.pools.set(key, new Pool({
        host: this.config.host,
        database: this.config.database,
        max: 10,
      }));
    }
    return DedicatedDatabase.pools.get(key)!;
  }

  async query<T>(sql: string, params?: unknown[]): Promise<T[]> {
    const result = await this.getPool().query(sql, params);
    return result.rows as T[];
  }
}
```

`DedicatedDatabase` 는 이 처리를 해 뒀다. 그런데 같은 문서의 다른 어댑터들은 그렇지 않다 — `LocalDatabaseAdapter` 와 `RDSDatabase` 는 **생성자에서** `new Pool(...)` 을 하고, `ElastiCacheAdapter` 는 생성자에서 Redis 연결을 연다. 위 `tenantMiddleware` 는 요청마다 `createDatabase()` / `createStorage()` / `createNotifier()` 를 부르므로, 팩토리를 캐싱해도 **커넥션은 요청 수만큼 생긴다.**

**팩토리 캐싱과 리소스 캐싱은 다른 문제다.** 재사용해야 할 대상은 팩토리가 아니라 팩토리가 만드는 것이다.

여기서 이름이 함정으로 작용한다. `createXxx()` 는 "부를 때마다 새로 만든다"로 읽히고 패턴의 원래 정의도 그렇다. 하지만 인프라 어댑터는 대개 프로세스당 하나여야 한다. 이 어긋남은 어딘가에서 흡수해야 하고 선택지는 셋이다.

| 방법 | 대가 |
|---|---|
| 팩토리 내부에서 인스턴스를 메모이즈 | `create` 라는 이름이 거짓이 된다 — 호출자가 매번 새 객체로 착각한다 |
| 클래스 static 풀 (위 `DedicatedDatabase`) | 전역 상태라 테스트 격리가 깨지고 종료 시 정리 지점이 흩어진다 |
| 앱 시작 때 한 번만 `create*` 하고 결과를 주입 | 런타임에 조합을 바꾸는 능력을 포기한다 |

세 번째가 가장 무난하지만 그걸 택하면 이 패턴이 필요했던 이유(테넌트별 런타임 전환)가 사라진다. 멀티 테넌트라면 첫 번째나 두 번째를 쓰되 메서드 이름을 `getDatabase()` 로 바꿔 재사용이 의도임을 드러내는 편이 사고가 적다.

### 레지스트리에 남는 세 가지

**캐시가 무한히 자란다.** `TenantInfraRegistry.factories` 는 삭제 경로가 없는 Map 이다. 테넌트가 늘면 팩토리와 그 팩토리가 잡은 커넥션이 그대로 쌓인다. 상한이나 TTL 을 두면 이번엔 "축출된 팩토리의 커넥션은 누가 닫는가" 가 따라온다.

**동시에 들어오면 팩토리가 여러 개 만들어진다.** `getFactory` 는 `await this.loadTenantConfig(...)` 에서 제어를 놓는다. 같은 테넌트로 요청 3개가 동시에 들어오면 셋 다 캐시 미스로 판정하고 셋 다 팩토리를 만든다. 실제로 돌려 보면 생성 3회, 반환된 객체 3개가 서로 다르고, Map 에는 마지막 것만 남는다. 유실된 두 개가 이미 커넥션을 열었다면 그대로 새는 것이다. 처방은 **완성된 값이 아니라 Promise 를 캐싱**하는 것이다.

```typescript
private factories = new Map<string, Promise<TenantInfraFactory>>();

getFactory(tenantId: string): Promise<TenantInfraFactory> {
  let pending = this.factories.get(tenantId);
  if (!pending) {
    pending = this.loadTenantConfig(tenantId)
      .then(cfg => this.createFactoryForPlan(tenantId, cfg));
    this.factories.set(tenantId, pending);          // await 이전에 등록한다
    pending.catch(() => this.factories.delete(tenantId));  // 실패는 캐싱하지 않는다
  }
  return pending;
}
```

`set` 을 `await` **앞**에 두는 것이 요점이다. 실패한 Promise 를 지우지 않으면 일시적 장애가 영구 장애가 된다.

**플랜이 바뀌어도 캐시는 모른다.** 고객이 Free 에서 Enterprise 로 올라가도 캐싱된 `SharedInfraFactory` 가 계속 나온다. 재배포 전까지 결제한 기능이 안 켜진다. 플랜 변경 시 해당 키를 지우는 경로가 없다면 이 구조는 "거의 안 바뀌는 설정" 에만 쓸 수 있다.

## DI 컨테이너와의 관계

실무에서 Abstract Factory를 직접 구현하는 경우는 점점 줄어든다. NestJS, tsyringe 같은 DI 프레임워크가 사실상 Abstract Factory 역할을 대신하기 때문이다.

### DI 컨테이너가 Abstract Factory를 대체하는 구조

```typescript
// NestJS 모듈로 환경별 인프라 구성
@Module({})
class InfrastructureModule {
  static forEnvironment(): DynamicModule {
    const env = process.env.NODE_ENV;

    const providers = env === 'production'
      ? [
          { provide: 'Database', useClass: RDSDatabase },
          { provide: 'Cache', useClass: ElastiCacheAdapter },
          { provide: 'Queue', useClass: SQSQueue },
        ]
      : [
          { provide: 'Database', useClass: LocalDatabaseAdapter },
          { provide: 'Cache', useClass: InMemoryCache },
          { provide: 'Queue', useClass: LocalQueueAdapter },
        ];

    return {
      module: InfrastructureModule,
      providers,
      exports: providers.map(p => p.provide),
    };
  }
}
```

```typescript
// 서비스에서는 인터페이스에만 의존
@Injectable()
class OrderService {
  constructor(
    @Inject('Database') private db: Database,
    @Inject('Cache') private cache: CacheStore,
    @Inject('Queue') private queue: MessageQueue,
  ) {}

  async createOrder(data: CreateOrderDto) {
    const order = await this.db.query('INSERT INTO orders ...');
    await this.cache.set(`order:${order.id}`, JSON.stringify(order));
    await this.queue.publish('order.created', order);
    return order;
  }
}
```

이 코드는 Abstract Factory를 직접 만들지 않았지만, DI 컨테이너가 `InfrastructureModule.forEnvironment()`에서 환경에 따라 구체 클래스 묶음을 결정하고, 서비스에는 인터페이스만 주입한다. Abstract Factory의 역할을 프레임워크가 대신하는 것이다.

### 그래서 Abstract Factory를 직접 쓸 때는 언제인가

DI 컨테이너가 있어도 Abstract Factory를 직접 구현해야 하는 경우가 있다.

**1. 런타임에 팩토리가 바뀌는 경우**

DI 컨테이너는 보통 앱 시작 시점에 바인딩이 결정된다. 테넌트 요청이 올 때마다 다른 인프라 조합을 써야 하는 상황에서는 DI 컨테이너만으로 해결이 어렵다.

```typescript
// DI로 팩토리 레지스트리 자체를 주입하고,
// 런타임에 적절한 팩토리를 선택하는 방식
@Injectable()
class TenantService {
  constructor(
    @Inject('TenantInfraRegistry') private registry: TenantInfraRegistry,
  ) {}

  async handleRequest(tenantId: string) {
    // 요청 시점에 팩토리가 결정됨
    const factory = await this.registry.getFactory(tenantId);
    const db = factory.createDatabase();
    const result = await db.query('SELECT ...');
    return result;
  }
}
```

**2. 팩토리 자체에 생성 로직이 복잡한 경우**

DI 컨테이너의 `useFactory`로도 가능하지만, 팩토리 내부에서 여러 객체를 생성하면서 서로 참조를 엮거나, 생성 순서에 의존성이 있는 경우에는 명시적인 팩토리 클래스가 가독성이 낫다.

```typescript
class MonitoredInfraFactory implements InfrastructureFactory {
  createDatabase(): Database {
    const db = new RDSDatabase();
    const monitor = new DatabaseMonitor(db);
    monitor.startHealthCheck(30000); // 30초마다 헬스체크
    return new MonitoredDatabaseProxy(db, monitor);
  }

  createCache(): CacheStore {
    const cache = new ElastiCacheAdapter();
    const fallback = new InMemoryCache();
    // 캐시 장애 시 인메모리로 폴백
    return new CacheWithFallback(cache, fallback);
  }

  createQueue(): MessageQueue {
    const queue = new SQSQueue();
    const dlq = new SQSQueue(); // Dead Letter Queue
    return new QueueWithDLQ(queue, dlq);
  }
}
```

이런 생성 로직을 DI 컨테이너의 `useFactory` 콜백에 넣으면, 모듈 설정 파일이 지나치게 커지면서 관심사가 섞인다.

## 주의사항

### 제품군에 새 제품을 추가하기 어렵다

Abstract Factory의 가장 큰 단점이다. 인터페이스에 메서드를 추가하면 모든 구체 팩토리를 수정해야 한다.

```typescript
// 여기에 createMetrics()를 추가하면?
interface InfrastructureFactory {
  createDatabase(): Database;
  createCache(): CacheStore;
  createQueue(): MessageQueue;
  createMetrics(): MetricsCollector;  // 추가
}

// LocalInfraFactory도 수정
// StagingInfraFactory도 수정
// ProductionInfraFactory도 수정
// MonitoredInfraFactory도 수정
// ... 팩토리가 5개면 5곳을 다 고쳐야 한다
```

팩토리가 3개 이하면 감당할 만하다. 그 이상이면 팩토리 인터페이스를 분리하거나, 제품 추가가 잦은 부분은 다른 방식(맵 기반 동적 등록 등)을 고려해야 한다.

### 구현체가 늘어나면 "같은 인터페이스, 다른 동작"을 떠안는다

시그니처는 컴파일러가 맞춰 주지만 **동작은 아무도 맞춰 주지 않는다.** 이 문서의 `MessageQueue` 가 그 예다.

| | `LocalQueueAdapter` | `SQSQueue` |
|---|---|---|
| publish 후 핸들러 실행 | 같은 틱에 동기 실행 | 다른 프로세스에서 나중에 |
| 전달 보장 | 정확히 1회 | 최소 1회 (중복 가능) |
| 순서 | 등록 순서 그대로 | 표준 큐는 보장 없음 |
| 구독자가 없을 때 | 메시지 소멸 | 큐에 남았다가 나중에 전달 |
| 핸들러가 던진 예외 | publish 호출자에게 전파 | 호출자와 무관 |

`publish(topic, message): Promise<void>` 라는 타입은 이 차이를 하나도 표현하지 못한다. 그래서 "발행하고 곧바로 결과를 조회" 하는 코드가 로컬에서 통과하고 운영에서 깨진다. 핸들러 예외를 publish 쪽 `try/catch` 로 잡는 코드도 마찬가지다.

캐시도 같다. `InMemoryCache` 는 프로세스 로컬이라 워커를 두 개 띄우면 각자 다른 값을 본다. 만료 항목은 `get` 할 때만 지워지므로 **읽히지 않는 키는 TTL 이 지나도 계속 메모리에 남는다** — 이미 만료된 항목 1,000개를 넣고 `get` 을 부르지 않으면 내부 Map 크기는 1,000 그대로다. Redis 라면 서버가 회수하는 부분이다.

**Abstract Factory 를 도입하면 인터페이스 하나당 구현이 N개로 늘고, 그 N개가 같게 동작하는지는 사람이 지켜야 한다.** 이게 이 패턴의 가장 비싼 대가다. 줄이는 방법은 둘이다.

- **같은 테스트를 모든 구현에 돌린다.** 계약 테스트를 하나 쓰고 `LocalQueueAdapter` 와 `SQSQueue` 에 똑같이 적용한다.
- **인터페이스를 가장 약한 구현에 맞춘다.** SQS 가 순서를 보장하지 않으면 로컬 구현도 일부러 섞는다. 로컬이 더 관대하면 그 관대함에 기대는 코드가 반드시 생긴다.

### 과도한 추상화 징후

- 팩토리가 생성하는 객체가 1~2개뿐이다 -> Factory Method로 충분하다
- 생성되는 객체 조합이 한 가지뿐이다 -> 팩토리 없이 직접 생성해도 된다
- 조합이 잘못돼도 큰 문제가 없다 -> 팩토리의 이점이 거의 없다

Abstract Factory를 도입하기 전에 "조합 불일치가 실제로 장애를 일으킬 수 있는가"를 먼저 따져봐야 한다. 그렇지 않다면 단순한 설정 파일이나 Factory Method로 해결하는 편이 낫다.

### 테스트에서의 활용

Abstract Factory는 테스트에서 인프라를 통째로 교체하기 좋다.

```typescript
class TestInfraFactory implements InfrastructureFactory {
  createDatabase(): Database {
    return new SQLiteDatabase(':memory:');
  }

  createCache(): CacheStore {
    return new InMemoryCache();
  }

  createQueue(): MessageQueue {
    return new InMemoryQueue(); // 발행된 메시지를 배열에 저장
  }
}

// 테스트 코드
describe('OrderService', () => {
  let orderService: OrderService;
  let testQueue: InMemoryQueue;

  beforeEach(() => {
    const factory = new TestInfraFactory();
    testQueue = factory.createQueue() as InMemoryQueue;
    orderService = new OrderService(
      factory.createDatabase(),
      factory.createCache(),
      testQueue,
    );
  });

  it('주문 생성 시 이벤트를 발행한다', async () => {
    await orderService.createOrder({ itemId: 'item-1', quantity: 2 });

    // 인메모리 큐에 저장된 메시지를 직접 검증
    expect(testQueue.getMessages('order.created')).toHaveLength(1);
  });
});
```

외부 의존성 없이 통합 테스트 수준의 검증이 가능하다. Mock 라이브러리로 개별 메서드를 일일이 스텁하는 것보다 팩토리를 통째로 교체하는 방식이 테스트 코드가 깔끔하다.
