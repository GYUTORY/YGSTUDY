---
title: NestJS 테스트 (Jest, Supertest, TestingModule)
tags: [framework, node, nestjs, test, jest, supertest]
updated: 2026-04-16
---

## NestJS 테스트를 왜 제대로 해야 하는가

처음 NestJS 프로젝트를 맡았을 때, 팀에서 작성한 테스트 코드를 보고 의문이 많이 들었다. 컨트롤러에서 서비스를 `new Service()`로 직접 생성해서 테스트한다거나, 통합 테스트에서 실제 운영 DB를 바라보고 있다거나, 심한 경우에는 `describe` 블록 안에서 모킹만 잔뜩 하고 실제 로직은 검증하지 않는 케이스도 있었다. 그 상태로 배포하다가 프로덕션에서 DI 컨테이너가 뱉는 `Nest can't resolve dependencies` 에러를 몇 번 겪고 나서야, NestJS 테스트는 일반 Node.js 테스트와 다르게 접근해야 한다는 걸 깨달았다.

NestJS는 DI 컨테이너가 중심이다. 서비스, 리포지토리, 가드, 인터셉터, 파이프가 전부 컨테이너에 등록되고 주입된다. 이 구조를 무시하고 객체를 직접 생성해서 테스트하면, 런타임 동작과 테스트 동작이 달라진다. 예를 들어 `@Inject()` 데코레이터로 주입되는 토큰 기반 의존성은 `new`로 만든 인스턴스에서는 주입되지 않는다. 그래서 NestJS는 `@nestjs/testing` 패키지의 `Test.createTestingModule()`을 제공한다. 이 API는 실제 DI 컨테이너를 테스트 환경에서 재현해주고, 원하는 프로바이더만 골라서 오버라이드할 수 있게 해준다.

테스트 피라미드 관점에서 보면, NestJS 백엔드는 일반적으로 다음 비율로 구성하는 게 좋다. 유닛 테스트 70%, 통합 테스트(TestingModule 기반) 20%, E2E 테스트(Supertest 기반) 10%. 유닛 테스트는 서비스의 비즈니스 로직만 검증하고 외부 의존성은 전부 모킹한다. 통합 테스트는 모듈 단위로 묶어서 실제 DI가 동작하는지 확인한다. E2E 테스트는 HTTP 요청부터 DB까지 전체 플로우를 검증한다. 이 비율을 뒤집어서 E2E만 잔뜩 쓰면 테스트 실행 시간이 길어지고, 반대로 유닛 테스트만 있으면 모듈 간 연결에서 생기는 버그를 못 잡는다.

## Jest 설정과 NestJS 기본 구조

NestJS CLI로 생성한 프로젝트에는 기본적으로 Jest 설정이 `package.json`에 들어있다. 보통은 이걸 그대로 쓰지 않고 `jest.config.js` 또는 `jest-e2e.config.js`로 분리한다. 유닛 테스트와 E2E 테스트는 실행 환경이 다르기 때문이다. 유닛 테스트는 빠르게 돌아야 하고, E2E는 DB나 외부 서비스를 띄워야 하므로 setup이 다르다.

```js
// jest.config.js (유닛 테스트용)
module.exports = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: 'src',
  testRegex: '.*\\.spec\\.ts$',
  transform: {
    '^.+\\.(t|j)s$': 'ts-jest',
  },
  collectCoverageFrom: ['**/*.(t|j)s'],
  coveragePathIgnorePatterns: ['.module.ts$', '.dto.ts$', 'main.ts$'],
  coverageDirectory: '../coverage',
  testEnvironment: 'node',
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/$1',
  },
};
```

```js
// jest-e2e.config.js (E2E 테스트용)
module.exports = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: '.',
  testRegex: '.e2e-spec.ts$',
  transform: {
    '^.+\\.(t|j)s$': 'ts-jest',
  },
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/test/setup.ts'],
  globalSetup: '<rootDir>/test/global-setup.ts',
  globalTeardown: '<rootDir>/test/global-teardown.ts',
  testTimeout: 30000,
};
```

두 가지를 분리하는 이유는 실무에서 명확하다. 유닛 테스트는 CI에서 PR마다 돌아야 하므로 2분 이내에 끝나야 한다. E2E는 Docker로 Postgres, Redis 같은 의존성을 띄워야 하고, 테스트 격리를 위해 DB 초기화도 해야 하므로 느리다. 유닛 테스트 실행 명령에 E2E가 섞이면 PR 피드백 루프가 망가진다. 별도 스크립트로 `npm run test`와 `npm run test:e2e`를 분리해두고, CI 파이프라인에서도 단계를 나눈다.

`testEnvironment`는 `node`로 둔다. 기본값인 `jsdom`은 브라우저 환경을 시뮬레이션하므로 서버 테스트에서는 쓸모가 없고, 오히려 성능 저하가 생긴다. `setupFilesAfterEach`에는 각 테스트 파일이 실행되기 전 공통 초기화 코드를 넣는다. 예를 들어 환경 변수 로드, 타임존 설정, 전역 모킹이 여기 들어간다.

## TestingModule의 동작 원리

`Test.createTestingModule()`은 실제 `@Module()` 데코레이터가 만드는 것과 동일한 DI 컨테이너를 만든다. 차이는 `overrideProvider()`, `overrideGuard()`, `overrideInterceptor()` 같은 메서드로 런타임 동작을 교체할 수 있다는 점이다. 이 메커니즘이 NestJS 테스트의 핵심이다.

```ts
import { Test, TestingModule } from '@nestjs/testing';
import { UserService } from './user.service';
import { UserRepository } from './user.repository';

describe('UserService', () => {
  let service: UserService;
  let repository: jest.Mocked<UserRepository>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UserService,
        {
          provide: UserRepository,
          useValue: {
            findById: jest.fn(),
            save: jest.fn(),
            delete: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<UserService>(UserService);
    repository = module.get(UserRepository);
  });

  it('존재하지 않는 유저 조회 시 NotFoundException이 발생한다', async () => {
    repository.findById.mockResolvedValue(null);

    await expect(service.getUser(1)).rejects.toThrow('User not found');
    expect(repository.findById).toHaveBeenCalledWith(1);
  });
});
```

`useValue`에 객체를 넘기면 해당 객체가 그대로 DI 컨테이너에 등록된다. 그래서 `jest.fn()`으로 채워둔 모의 메서드를 통해 호출 여부와 인자를 검증할 수 있다. `module.get<T>()`은 컨테이너에서 인스턴스를 꺼내는 표준 방법이다. 이 때 타입 파라미터는 필수가 아니지만, 붙여두면 IDE에서 자동완성이 된다.

`module.get()`과 `module.resolve()`는 다르다. `get()`은 싱글턴 스코프 프로바이더에만 쓸 수 있고, `REQUEST` 스코프나 `TRANSIENT` 스코프 프로바이더는 `resolve()`를 써야 한다. 실수로 `get()`을 쓰면 `Error: ... is REQUEST scoped` 같은 에러가 난다. 리퀘스트 스코프 서비스를 테스트할 때 자주 겪는 함정이다.

## 유닛 테스트: 서비스 계층

서비스 계층 테스트의 목적은 비즈니스 로직 검증이다. DB 쿼리나 외부 API 호출은 전부 모킹하고, 서비스 메서드가 주어진 입력에 대해 올바른 출력과 부수효과를 만들어내는지만 본다.

```ts
// order.service.ts
@Injectable()
export class OrderService {
  constructor(
    private readonly orderRepository: OrderRepository,
    private readonly productService: ProductService,
    private readonly eventBus: EventBus,
  ) {}

  async createOrder(userId: number, productIds: number[]): Promise<Order> {
    const products = await this.productService.findByIds(productIds);

    if (products.length !== productIds.length) {
      throw new BadRequestException('일부 상품이 존재하지 않습니다');
    }

    const totalAmount = products.reduce((sum, p) => sum + p.price, 0);

    const order = await this.orderRepository.save({
      userId,
      products,
      totalAmount,
      status: OrderStatus.PENDING,
    });

    await this.eventBus.publish(new OrderCreatedEvent(order.id));
    return order;
  }
}
```

```ts
// order.service.spec.ts
describe('OrderService', () => {
  let service: OrderService;
  let orderRepository: jest.Mocked<OrderRepository>;
  let productService: jest.Mocked<ProductService>;
  let eventBus: jest.Mocked<EventBus>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        OrderService,
        {
          provide: OrderRepository,
          useValue: { save: jest.fn() },
        },
        {
          provide: ProductService,
          useValue: { findByIds: jest.fn() },
        },
        {
          provide: EventBus,
          useValue: { publish: jest.fn() },
        },
      ],
    }).compile();

    service = module.get(OrderService);
    orderRepository = module.get(OrderRepository);
    productService = module.get(ProductService);
    eventBus = module.get(EventBus);
  });

  describe('createOrder', () => {
    it('모든 상품이 존재하면 주문을 생성하고 이벤트를 발행한다', async () => {
      const products = [
        { id: 1, price: 10000 },
        { id: 2, price: 20000 },
      ];
      productService.findByIds.mockResolvedValue(products as any);
      orderRepository.save.mockResolvedValue({ id: 100 } as any);

      const result = await service.createOrder(1, [1, 2]);

      expect(orderRepository.save).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 1,
          totalAmount: 30000,
          status: OrderStatus.PENDING,
        }),
      );
      expect(eventBus.publish).toHaveBeenCalledWith(
        expect.any(OrderCreatedEvent),
      );
      expect(result.id).toBe(100);
    });

    it('일부 상품이 없으면 BadRequestException을 던지고 저장하지 않는다', async () => {
      productService.findByIds.mockResolvedValue([{ id: 1, price: 10000 }] as any);

      await expect(service.createOrder(1, [1, 2])).rejects.toThrow(
        BadRequestException,
      );

      expect(orderRepository.save).not.toHaveBeenCalled();
      expect(eventBus.publish).not.toHaveBeenCalled();
    });
  });
});
```

실무에서 가장 많이 놓치는 건 "부정적 경로"의 부수효과 검증이다. 예외가 던져지는 케이스에서 DB 저장이나 이벤트 발행이 실제로 일어나지 않는지 `not.toHaveBeenCalled()`로 확인해야 한다. 이걸 안 하면 트랜잭션 없이 저장이 먼저 일어나고 이후에 예외가 터져서 데이터 정합성이 깨지는 버그를 놓친다. 내가 실제로 겪은 케이스인데, 재고 차감이 먼저 일어나고 결제 처리에서 예외가 발생하는데 롤백이 안 되는 상황이었다. 테스트에 `not.toHaveBeenCalled()`가 있었다면 PR 단계에서 잡았을 문제다.

## 컨트롤러 테스트와 파이프·가드 오버라이드

컨트롤러 테스트는 서비스를 모킹하고 HTTP 계층의 동작만 검증한다. 여기서 자주 부딪히는 문제는 가드(`AuthGuard`)나 파이프(`ValidationPipe`)가 테스트 환경에서 예상대로 동작하지 않는 경우다.

```ts
describe('UserController', () => {
  let controller: UserController;
  let service: jest.Mocked<UserService>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      controllers: [UserController],
      providers: [
        {
          provide: UserService,
          useValue: {
            findById: jest.fn(),
            create: jest.fn(),
          },
        },
      ],
    })
      .overrideGuard(JwtAuthGuard)
      .useValue({ canActivate: () => true })
      .overrideInterceptor(LoggingInterceptor)
      .useValue({ intercept: (_, next) => next.handle() })
      .compile();

    controller = module.get(UserController);
    service = module.get(UserService);
  });

  it('GET /users/:id — 유저를 반환한다', async () => {
    service.findById.mockResolvedValue({ id: 1, name: 'kyu' } as any);

    const result = await controller.findOne(1);

    expect(result).toEqual({ id: 1, name: 'kyu' });
  });
});
```

`overrideGuard()`는 가드 자체의 의존성(예: `JwtService`)을 테스트 모듈에 등록하지 않아도 되게 해준다. 가드가 `Reflector`를 주입받는다면 `Reflector`도 등록해야 하는 번거로움이 있는데, 오버라이드하면 그럴 필요가 없다. 다만 주의할 점은, 가드를 오버라이드해버리면 가드 로직 자체는 테스트되지 않는다는 점이다. 가드 로직은 별도 `*.guard.spec.ts` 파일에서 테스트하고, 컨트롤러 테스트에서는 가드를 통과했다고 가정하는 식으로 분리한다.

`ValidationPipe`가 컨트롤러 테스트에서 동작하지 않는 것도 흔한 함정이다. NestJS에서 `ValidationPipe`는 `main.ts`의 `app.useGlobalPipes()`로 등록되는데, `Test.createTestingModule()`에서는 이게 자동으로 적용되지 않는다. 컨트롤러 메서드를 직접 호출하는 방식으로는 DTO 검증을 테스트할 수 없다. 이런 경우는 E2E 테스트로 HTTP 요청을 보내거나, 유닛 테스트에서는 수동으로 `new ValidationPipe().transform()`을 호출해서 검증한다.

## Repository 계층 테스트 (TypeORM)

Repository 테스트는 "진짜 DB를 써야 하는가, 모킹해야 하는가"라는 논쟁이 있다. 내 경험으로는 둘 다 필요하다. Repository 메서드 중에 커스텀 쿼리가 있다면 실제 DB에서 돌려봐야 한다. 반면 단순한 `save()`, `findOne()` 래핑 정도는 모킹으로 충분하다.

TypeORM Repository를 모킹하는 표준적인 방법은 `getRepositoryToken()`을 쓰는 것이다.

```ts
import { getRepositoryToken } from '@nestjs/typeorm';
import { Repository } from 'typeorm';

describe('UserRepository', () => {
  let repository: UserRepository;
  let ormRepository: jest.Mocked<Repository<User>>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        UserRepository,
        {
          provide: getRepositoryToken(User),
          useValue: {
            findOne: jest.fn(),
            save: jest.fn(),
            createQueryBuilder: jest.fn(() => ({
              where: jest.fn().mockReturnThis(),
              andWhere: jest.fn().mockReturnThis(),
              getMany: jest.fn(),
            })),
          },
        },
      ],
    }).compile();

    repository = module.get(UserRepository);
    ormRepository = module.get(getRepositoryToken(User));
  });

  it('findActiveUsers — QueryBuilder로 활성 유저를 조회한다', async () => {
    const qb = ormRepository.createQueryBuilder() as any;
    qb.getMany.mockResolvedValue([{ id: 1 }]);

    const result = await repository.findActiveUsers();

    expect(qb.where).toHaveBeenCalledWith('user.isActive = :isActive', {
      isActive: true,
    });
    expect(result).toHaveLength(1);
  });
});
```

`createQueryBuilder` 모킹은 체이닝 때문에 까다롭다. 각 메서드가 `this`를 반환하도록 `mockReturnThis()`를 써야 한다. 이게 누락되면 `where(...).andWhere(...)` 같은 체이닝이 `undefined`에서 메서드 호출이 되어 `TypeError`가 난다. 복잡한 QueryBuilder 체인을 모킹하다 보면 테스트 코드가 프로덕션 코드보다 길어지는 지점이 온다. 그 시점에는 모킹을 포기하고 실제 DB를 띄우는 통합 테스트로 전환하는 게 낫다.

## 테스트 DB 구성

실제 DB를 쓰는 통합 테스트와 E2E 테스트는 DB 격리가 핵심이다. 한 테스트의 데이터가 다른 테스트에 영향을 주면 플래키 테스트가 된다. 격리 방법은 세 가지가 있다.

첫째, 트랜잭션 롤백. 각 테스트를 트랜잭션으로 감싸고 끝날 때 롤백한다. 가장 빠르지만, 테스트 대상 코드 자체가 트랜잭션을 시작하면 쓰기 어렵다. NestJS에서는 `DataSource`의 `transaction()` 메서드를 써서 테스트 코드에서 트랜잭션을 관리한다.

둘째, 스키마 재생성. 각 테스트 전에 `DROP SCHEMA` 후 `CREATE SCHEMA`를 하고 마이그레이션을 다시 실행한다. 가장 확실하지만 느리다. 마이그레이션이 많으면 테스트 하나에 수 초씩 걸린다.

셋째, 테이블 `TRUNCATE`. 각 테스트 전에 모든 테이블을 `TRUNCATE CASCADE`한다. 실무에서 가장 많이 쓰는 방식이다. 스키마는 유지한 채 데이터만 지우므로 빠르고, 트랜잭션 충돌도 없다.

```ts
// test/setup.ts
import { DataSource } from 'typeorm';

let dataSource: DataSource;

beforeAll(async () => {
  dataSource = new DataSource({
    type: 'postgres',
    host: process.env.TEST_DB_HOST || 'localhost',
    port: parseInt(process.env.TEST_DB_PORT || '5433'),
    username: 'test',
    password: 'test',
    database: 'test',
    entities: ['src/**/*.entity.ts'],
    synchronize: true,
    dropSchema: true,
  });
  await dataSource.initialize();
});

beforeEach(async () => {
  const entities = dataSource.entityMetadatas;
  const tableNames = entities
    .map((entity) => `"${entity.tableName}"`)
    .join(', ');
  await dataSource.query(`TRUNCATE TABLE ${tableNames} CASCADE;`);
});

afterAll(async () => {
  await dataSource.destroy();
});
```

테스트 DB는 반드시 운영과 분리된 별도 인스턴스여야 한다. 포트를 다르게 주거나(위 예시에서 5433), Docker Compose로 테스트 전용 컨테이너를 띄운다. 실수로 `TEST_DB_HOST` 설정이 빠져서 운영 DB를 TRUNCATE하는 사고는 실제로 일어난다. 방어적으로 `if (process.env.NODE_ENV === 'production') throw new Error()` 같은 가드를 setup 파일에 넣어두는 게 좋다.

```yaml
# docker-compose.test.yml
services:
  postgres-test:
    image: postgres:15
    ports:
      - '5433:5432'
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test
    tmpfs:
      - /var/lib/postgresql/data
```

`tmpfs`를 쓰면 DB 데이터가 메모리에 저장되어 디스크 I/O가 없어진다. 테스트 DB에 영속성은 필요 없으므로 이게 훨씬 빠르다. 로컬에서 테스트 수백 개 돌릴 때 체감 속도 차이가 크다.

## E2E 테스트와 Supertest

E2E 테스트는 실제 HTTP 요청을 보내서 전체 플로우를 검증한다. `supertest`를 쓰는 게 표준이다. `app.getHttpServer()`로 Express 인스턴스를 꺼내서 Supertest에 넘긴다.

```ts
import { Test } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';

describe('UserController (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleRef.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('POST /users', () => {
    it('올바른 입력이면 201을 반환한다', () => {
      return request(app.getHttpServer())
        .post('/users')
        .send({ email: 'test@example.com', name: 'kyu', age: 30 })
        .expect(201)
        .expect((res) => {
          expect(res.body.id).toBeDefined();
          expect(res.body.email).toBe('test@example.com');
        });
    });

    it('email 필드가 없으면 400을 반환한다', () => {
      return request(app.getHttpServer())
        .post('/users')
        .send({ name: 'kyu', age: 30 })
        .expect(400)
        .expect((res) => {
          expect(res.body.message).toContain('email');
        });
    });

    it('JWT 토큰 없이 보호된 엔드포인트 접근 시 401을 반환한다', () => {
      return request(app.getHttpServer())
        .get('/users/me')
        .expect(401);
    });
  });
});
```

E2E 테스트에서는 `main.ts`에 있던 전역 설정을 반드시 재현해야 한다. `ValidationPipe`, 전역 필터, 인터셉터, CORS 설정 등이 여기 해당한다. 이걸 빼먹으면 "운영에서는 400이 나오는데 테스트에서는 201이 나오는" 상황이 생긴다. 실무에서는 `main.ts`의 bootstrap 로직을 별도 함수로 빼서 테스트에서도 재사용한다.

```ts
// src/bootstrap.ts
export function configureApp(app: INestApplication): void {
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.useGlobalFilters(new HttpExceptionFilter());
  app.useGlobalInterceptors(new LoggingInterceptor());
  app.enableCors({ origin: true });
}
```

이 함수를 `main.ts`와 E2E 테스트 setup에서 모두 호출하면 환경 차이가 없어진다.

## 모킹 전략: 무엇을 모킹하고 무엇을 쓰지 않을 것인가

모킹은 테스트 격리의 수단이지 목적이 아니다. 잘못된 모킹은 테스트를 무의미하게 만든다. 예를 들어 `jest.mock()`으로 전체 모듈을 모킹하고 그 모듈의 모든 메서드를 `jest.fn()`으로 대체하면, 실제 로직은 전혀 검증되지 않는다.

내가 쓰는 기준은 이렇다. 외부 시스템(DB, HTTP API, 메시지 큐, 파일 시스템)은 유닛 테스트에서 반드시 모킹한다. 내부 서비스끼리의 호출은 테스트 대상에 따라 다르다. 서비스 A가 서비스 B를 호출할 때, A의 유닛 테스트에서는 B를 모킹한다. 하지만 A와 B를 함께 테스트하는 통합 테스트에서는 둘 다 실제 인스턴스를 쓴다.

시간에 의존하는 로직(`new Date()`, `setTimeout`)은 `jest.useFakeTimers()`를 쓴다. 이걸 안 쓰고 `Date.now()`를 모킹하지 않으면 "내일 실행하면 깨지는 테스트"가 생긴다.

```ts
describe('TokenService', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('1시간 후 만료되는 토큰을 생성한다', () => {
    const token = service.createToken();
    expect(token.expiresAt).toEqual(new Date('2026-01-01T01:00:00Z'));
  });
});
```

외부 HTTP 호출은 `nock` 같은 라이브러리로 HTTP 레이어를 가로채거나, `HttpService`를 주입받는 경우 `HttpService` 자체를 모킹한다. 후자가 더 간단하다.

## 테스트 가독성을 위한 팩토리 패턴

테스트 데이터를 매번 `{ id: 1, email: 'a@b.com', ... }`으로 만들면 테스트 의도가 흐려진다. 엔티티 생성을 팩토리 함수로 추출하면 테스트가 훨씬 읽기 쉬워진다.

```ts
// test/factories/user.factory.ts
export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: 'default@example.com',
    name: 'default',
    age: 25,
    isActive: true,
    createdAt: new Date('2026-01-01'),
    ...overrides,
  } as User;
}
```

```ts
it('비활성 유저는 조회되지 않는다', async () => {
  repository.findAll.mockResolvedValue([
    createUser({ id: 1, isActive: true }),
    createUser({ id: 2, isActive: false }),
  ]);

  const result = await service.getActiveUsers();
  expect(result).toHaveLength(1);
});
```

팩토리를 쓰면 테스트마다 중요한 필드만 `overrides`로 넘기고 나머지는 기본값을 쓴다. 테스트 코드를 읽을 때 "이 테스트에서 중요한 건 `isActive`구나"가 바로 보인다. `faker` 라이브러리를 팩토리 안에서 쓰면 랜덤 데이터도 쉽게 만들 수 있지만, 랜덤성은 플래키 테스트의 원인이 될 수 있으니 주의해야 한다. 시드를 고정하거나, 꼭 필요한 경우에만 쓴다.

## 커버리지의 함정

`--coverage` 플래그로 나오는 숫자에 집착하면 안 된다. 커버리지 80%를 달성하기 위해 의미 없는 테스트를 추가하면, 오히려 리팩토링을 방해하는 테스트가 생긴다. 내가 본 최악의 케이스는 `service.method()`를 호출하고 `expect(service.method).toBeDefined()`만 검증하는 테스트였다. 커버리지는 찍히지만 아무것도 검증하지 않는다.

내가 쓰는 기준은 "변경 시 깨지는 테스트가 있는가"다. 비즈니스 로직이 바뀌면 테스트가 깨져야 한다. 깨지지 않으면 그 테스트는 로직을 검증하지 않는 것이다. 커버리지 리포트는 "테스트가 안 된 영역"을 찾는 용도로만 쓰고, 숫자 자체를 목표로 삼지 않는다. DTO, 엔티티, 모듈 파일은 커버리지에서 제외한다(`coveragePathIgnorePatterns`).

CI에서 커버리지 임계값을 걸 거라면 라인 커버리지보다 브랜치 커버리지가 더 의미 있다. 분기(if-else)가 모두 테스트됐는지 보는 게, 단순히 라인이 실행됐는지 보는 것보다 버그를 잘 잡는다.
