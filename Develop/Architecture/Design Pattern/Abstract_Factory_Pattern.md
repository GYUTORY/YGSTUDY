---
title: Abstract Factory Pattern (추상 팩토리 패턴)
tags: [design-pattern, abstract-factory, creational-pattern, javascript, typescript, architecture]
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
