---
title: NestJS LazyModuleLoader — 동적 모듈 지연 로딩
tags: [nodejs, typescript, backend, architecture]
updated: 2026-09-15
---

# NestJS LazyModuleLoader — 동적 모듈 지연 로딩

NestJS 애플리케이션을 처음 띄울 때 `AppModule`에 등록된 모든 모듈이 한 번에 초기화된다. HTTP 서버라면 1~2초짜리 부트 타임이 별문제 없지만 CLI 앱이나 워커 프로세스는 다르다. `nestjs-cli` 기반 CLI 커맨드를 실행하면 실제 작업과 무관한 TypeORM 커넥션, Redis 클라이언트, 외부 API 모듈이 전부 초기화되고 나서야 커맨드 핸들러가 실행된다. 부트 타임이 4~5초에 달하면 간단한 DB 마이그레이션 커맨드 하나 실행하는 데 사용자는 5초를 기다려야 한다.

`LazyModuleLoader`는 이 문제를 해결하기 위해 NestJS 8에서 추가됐다. 모듈을 애플리케이션 부트 시점이 아니라 처음 필요한 시점에 초기화한다.

## 작동 방식

NestJS의 일반 모듈 초기화는 `ApplicationContext` 생성 시점에 전체 의존성 그래프를 순회하면서 모든 프로바이더를 인스턴스화한다. `LazyModuleLoader`는 이 과정을 분리해서, 특정 모듈의 컨테이너를 요청 시점에 별도로 생성한다.

```typescript
import { Injectable } from '@nestjs/common';
import { LazyModuleLoader } from '@nestjs/core';

@Injectable()
export class AppService {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}

  async doHeavyWork() {
    const { HeavyModule } = await import('./heavy/heavy.module');
    const moduleRef = await this.lazyModuleLoader.load(() => HeavyModule);

    const service = moduleRef.get(HeavyService);
    return service.process();
  }
}
```

`load()`는 `LazyModuleRef`를 반환한다. 이 레퍼런스로 해당 모듈 안의 프로바이더를 꺼내 쓴다. 한 번 로드된 모듈은 내부적으로 캐싱되므로 두 번째 `load()` 호출부터는 재초기화하지 않는다.

`LazyModuleLoader`는 `@nestjs/core`에서 제공하는 내장 서비스다. `ModuleRef`나 `Reflector`처럼 별도로 `providers`에 등록하지 않아도 주입받을 수 있다.

## CLI 앱에서 선택적 모듈 초기화

NestJS CLI 앱은 보통 `createApplicationContext`로 시작한다.

```typescript
async function bootstrap() {
  const app = await NestFactory.createApplicationContext(AppModule, {
    logger: false,
  });

  const command = app.get(CommandRunner);
  await command.run(process.argv.slice(2));
  await app.close();
}
```

`AppModule`에 모든 모듈을 올려두면 커맨드와 무관한 것까지 초기화된다. `LazyModuleLoader`를 쓰면 `AppModule`을 최소화하고 각 커맨드 핸들러가 필요한 모듈만 그 시점에 로드한다.

```typescript
// AppModule — 의존성을 최소로 유지
@Module({
  providers: [MigrateCommand, SeedCommand],
})
export class AppModule {}

// MigrateCommand — TypeORM 커넥션만 지연 로딩
@Injectable()
export class MigrateCommand implements CommandRunner {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}

  async run(): Promise<void> {
    const { TypeOrmModule } = await import('@nestjs/typeorm');
    const moduleRef = await this.lazyModuleLoader.load(() =>
      TypeOrmModule.forRoot(typeOrmConfig),
    );

    const dataSource = moduleRef.get(DataSource);
    await dataSource.runMigrations();
  }
}

// SeedCommand — TypeORM + Redis 둘 다 필요
@Injectable()
export class SeedCommand implements CommandRunner {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}

  async run(): Promise<void> {
    const { TypeOrmModule } = await import('@nestjs/typeorm');
    const { RedisModule } = await import('./redis/redis.module');

    const dbRef = await this.lazyModuleLoader.load(() =>
      TypeOrmModule.forRoot(typeOrmConfig),
    );
    const redisRef = await this.lazyModuleLoader.load(() => RedisModule);

    const dataSource = dbRef.get(DataSource);
    const redisClient = redisRef.get(REDIS_CLIENT);
    // ...
  }
}
```

`migrate` 커맨드를 실행하면 TypeORM 커넥션만 열리고 Redis는 건드리지 않는다. `seed` 커맨드는 둘 다 필요하므로 둘 다 로드한다. 실측 기준으로 Redis, S3, 외부 HTTP 모듈이 빠지면 부트 타임이 4.2초에서 0.8초로 줄었다.

## HTTP 서버에서의 사용

HTTP 서버에서 LazyModuleLoader를 쓰는 경우는 드물지만 두 가지 상황에서 의미가 있다.

첫 번째는 AWS Lambda 같은 서버리스 환경이다. 콜드스타트에서 모듈 초기화 비용이 타임아웃으로 이어질 수 있다. 전체 트래픽 중 일부 경로만 사용하는 무거운 모듈(PDF 생성, 동영상 처리, 대용량 리포트 등)을 분리하면 콜드스타트 시간을 줄일 수 있다.

두 번째는 트래픽의 극히 일부만 사용하는 기능이다. 관리자 전용 배치 실행, 월 1회 수동 발송하는 대량 이메일 처리 같은 경우다.

```typescript
@Controller('reports')
export class ReportController {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}

  @Post('generate')
  async generate(@Body() dto: ReportDto) {
    const { ReportModule } = await import('./report/report.module');
    const moduleRef = await this.lazyModuleLoader.load(() => ReportModule);
    const generator = moduleRef.get(ReportGeneratorService);
    return generator.generate(dto);
  }
}
```

주의해야 할 점은 첫 번째 요청에서 모듈 초기화 비용이 그 요청의 응답 시간에 직접 더해진다는 것이다. DB 커넥션 풀 초기화까지 포함된 모듈이면 첫 요청 응답 시간이 수 초가 될 수 있다. 두 번째 요청부터는 캐시에서 꺼내므로 비용이 없다. 처음 요청한 사용자 한 명이 초기화 비용을 전부 부담하는 구조다.

애플리케이션 시작 시점에 warm-up 요청을 보내는 방식으로 이를 피할 수 있지만, 그러면 지연 로딩의 의미가 없어진다. HTTP 서버에서 대부분의 모듈은 앱 부트 시점에 올리는 게 낫다. LazyModuleLoader는 CLI, 워커 프로세스, 서버리스 환경에서 효과가 가장 크다.

## 동적 모듈과의 조합 패턴

`load()`는 팩토리 함수를 받고, 팩토리가 `DynamicModule`을 반환하면 된다.

```typescript
const moduleRef = await this.lazyModuleLoader.load(() => ({
  module: PaymentModule,
  providers: [
    {
      provide: PAYMENT_CONFIG,
      useValue: { apiKey: process.env.PAYMENT_API_KEY },
    },
  ],
}));
```

환경 변수를 읽어 설정을 주입하는 이 패턴은 CLI 앱에서 자주 쓴다. HTTP 서버처럼 부트 시점에 전체 설정을 검증하지 않아도 되고, 커맨드가 실행될 때 그 커맨드에 필요한 설정만 읽는다.

`forRootAsync`를 쓰는 모듈도 같은 방식으로 조합된다.

```typescript
const moduleRef = await this.lazyModuleLoader.load(() =>
  TypeOrmModule.forRootAsync({
    useFactory: () => ({
      type: 'postgres',
      url: process.env.DATABASE_URL,
      entities: [User, Order],
      synchronize: false,
    }),
  }),
);
```

**캐싱 키 결정 방식**

`load()`는 팩토리가 반환한 모듈의 클래스를 캐싱 키로 쓴다. DynamicModule이면 `module` 프로퍼티, 일반 클래스면 클래스 자체가 키다. 팩토리가 매번 새 객체를 반환해도 캐싱 키는 모듈 클래스이므로, 두 번째 `load()` 호출부터는 팩토리 실행 결과를 무시하고 캐시를 반환한다.

```typescript
// 첫 번째 load() — TypeOrmModule 키로 캐시에 저장된다
const ref1 = await loader.load(() =>
  TypeOrmModule.forRoot({ url: 'postgres://primary' }),
);

// 두 번째 load() — 팩토리는 실행되지만 TypeOrmModule 키가 이미 캐시에 있다
// 두 번째 설정은 무시되고 ref1과 같은 인스턴스를 반환한다
const ref2 = await loader.load(() =>
  TypeOrmModule.forRoot({ url: 'postgres://replica' }),
);
// ref1 === ref2
```

"팩토리가 다르니까 다른 인스턴스가 만들어질 것"이라고 기대하다가 이 함정에 걸린다. 같은 모듈 클래스를 다른 설정으로 동시에 써야 한다면 래퍼 클래스를 별도로 만들어야 한다.

```typescript
@Module({})
class PrimaryDbModule {}

@Module({})
class ReadReplicaModule {}

const primaryRef = await loader.load(() => ({
  module: PrimaryDbModule,
  imports: [TypeOrmModule.forRoot({ url: env.DB_PRIMARY })],
  exports: [TypeOrmModule],
}));

const replicaRef = await loader.load(() => ({
  module: ReadReplicaModule,
  imports: [TypeOrmModule.forRoot({ url: env.DB_REPLICA })],
  exports: [TypeOrmModule],
}));
```

`PrimaryDbModule`과 `ReadReplicaModule`은 다른 클래스라서 캐싱 키가 달리 잡히고, 각각 독립적으로 초기화된다.

## DI 스코프 제약

지연 로딩으로 가져온 모듈의 프로바이더는 `REQUEST` 스코프와 `TRANSIENT` 스코프를 지원하지 않는다. `moduleRef.get()`은 싱글톤 스코프 프로바이더만 가져올 수 있다.

`REQUEST` 스코프 프로바이더를 지연 로딩된 모듈에서 꺼내려 하면 런타임에 예외가 발생한다.

```
Nest can't resolve dependencies of the RequestScopedService.
Please make sure that the argument at index [0] is available in the context.
```

CLI 앱과 워커에서는 HTTP 요청 컨텍스트가 없으므로 `REQUEST` 스코프를 쓰는 경우가 드물다. 하지만 기존 HTTP 서버용 모듈을 CLI에서 재사용할 때 이 제약에 걸리는 경우가 있다. 그럴 때는 해당 프로바이더를 `DEFAULT` 스코프(싱글톤)로 바꾸거나 CLI 전용 프로바이더를 따로 만들어야 한다.

`TRANSIENT` 스코프도 마찬가지다. `get()`으로 가져오면 항상 같은 인스턴스를 반환한다. TRANSIENT 동작이 필요하다면 직접 `new`로 인스턴스를 만들거나 팩토리 패턴으로 우회해야 한다.

## load() 실패와 에러 처리

`load()`가 던지는 예외는 두 종류다. 팩토리 함수 실행 중 발생하는 것(모듈 파일 import 실패, 설정값 검증 실패 등)과 모듈 초기화 중 발생하는 것(`onModuleInit` 예외, 의존성 해결 실패 등)이다.

try/catch 없이 예외가 터지면:

- CLI: 프로세스가 unhandled rejection으로 종료된다. 종료 코드 1, 스택 트레이스가 stderr에 찍힌다.
- HTTP 서버: 컨트롤러에서 터지면 NestJS 예외 필터가 잡아 500을 반환한다. 인터셉터나 가드 안에서 `load()`를 호출하다 예외가 나면 NestJS 예외 파이프라인이 이를 잡지 못하는 경우도 있다.

에러 처리는 `load()` 호출 주변에 둔다. 모듈 초기화 실패와 이후 프로바이더 실행 실패를 구분해서 처리하는 게 낫다.

```typescript
@Injectable()
export class HeavyFeatureService {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}

  async process(): Promise<Result> {
    let moduleRef;
    try {
      const { HeavyModule } = await import('./heavy/heavy.module');
      moduleRef = await this.lazyModuleLoader.load(() => HeavyModule);
    } catch (err) {
      // 컨트롤러의 예외 필터가 처리하도록 던진다
      throw new ServiceUnavailableException('기능을 초기화할 수 없습니다');
    }

    const processor = moduleRef.get(HeavyProcessor);
    return processor.run();
  }
}
```

`load()`가 한 번 실패하면 해당 모듈은 캐시에 올라가지 않는다. 다음 호출에서 팩토리를 다시 실행한다. DB 연결 실패 같은 일시적인 오류라면 재시도가 자연스럽게 동작한다.

## 단위 테스트

`Test.createTestingModule`은 `LazyModuleLoader`를 자동으로 제공하지 않는다. 직접 mock을 만들어 주입해야 한다.

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { LazyModuleLoader } from '@nestjs/core';
import { ServiceUnavailableException } from '@nestjs/common';

describe('HeavyFeatureService', () => {
  let service: HeavyFeatureService;
  let mockLoad: jest.Mock;

  beforeEach(async () => {
    mockLoad = jest.fn();

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        HeavyFeatureService,
        { provide: LazyModuleLoader, useValue: { load: mockLoad } },
      ],
    }).compile();

    service = module.get(HeavyFeatureService);
  });

  it('모듈 로드 후 프로세서를 실행한다', async () => {
    const mockProcessor = { run: jest.fn().mockResolvedValue({ result: 'ok' }) };
    const mockModuleRef = { get: jest.fn().mockReturnValue(mockProcessor) };

    mockLoad.mockResolvedValue(mockModuleRef);

    const result = await service.process();

    expect(mockLoad).toHaveBeenCalledTimes(1);
    expect(mockModuleRef.get).toHaveBeenCalledWith(HeavyProcessor);
    expect(result).toEqual({ result: 'ok' });
  });

  it('모듈 로드 실패 시 ServiceUnavailableException을 던진다', async () => {
    mockLoad.mockRejectedValue(new Error('Connection refused'));

    await expect(service.process()).rejects.toThrow(ServiceUnavailableException);
  });
});
```

`mockModuleRef.get`이 어떤 토큰으로 호출됐는지 검증하면(`toHaveBeenCalledWith(HeavyProcessor)`) 서비스 내부가 올바른 프로바이더를 꺼내는지 확인할 수 있다.

실제로 모듈을 올려서 테스트해야 한다면 `Test.createTestingModule`에서 `LazyModuleLoader`를 실제로 제공하는 방법은 없다. 통합 테스트는 `NestFactory.createApplicationContext`로 실제 컨텍스트를 만들거나, 테스트 대상 모듈을 직접 imports에 등록하고 `LazyModuleLoader` 없이 테스트하는 방식으로 설계하는 게 낫다.

## 대안 비교

비슷해 보이지만 용도가 다른 세 가지가 있다.

**forwardRef()**

순환 의존성을 해결하기 위한 것이다. 모듈 A가 모듈 B를, B가 A를 imports에 등록할 때 어느 쪽을 먼저 초기화할지 결정하지 못하는 문제를 푼다. 지연 로딩이 아니라 선언 순서 해결책이다. 부트 시점에 양쪽 다 초기화된다.

```typescript
// 순환 참조 해결 — 지연 로딩이 아니다
@Module({
  imports: [forwardRef(() => BModule)],
})
export class AModule {}
```

**조건부 모듈 등록**

앱 부트 시점에 어떤 모듈을 올릴지 결정하는 방식이다. 환경 변수나 설정에 따라 `AppModule`의 `imports` 배열을 동적으로 구성한다. 등록된 모듈은 부트 시점에 전부 초기화된다.

```typescript
@Module({
  imports: [
    process.env.ENABLE_PAYMENT === 'true' ? PaymentModule : [],
    ...(process.env.NODE_ENV === 'production' ? [MonitoringModule] : []),
  ],
})
export class AppModule {}
```

런타임에 새 모듈을 로드하는 게 아니라 부트 전에 모듈 조합을 결정하는 것이다. 조건이 앱 실행 전에 확정된다면 이 방식이 더 단순하다.

**ModuleRef.resolve()**

이미 올라와 있는 모듈에서 프로바이더를 꺼낼 때 쓴다. REQUEST 스코프나 TRANSIENT 스코프 프로바이더를 컨텍스트를 지정해 꺼낼 수 있다.

```typescript
// 이미 등록된 모듈에서 TRANSIENT 프로바이더 꺼내기
const contextId = ContextIdFactory.create();
const service = await this.moduleRef.resolve(TransientService, contextId);
```

`LazyModuleLoader`는 등록되지 않은 모듈을 런타임에 새로 초기화하는 것이고, `ModuleRef.resolve()`는 이미 등록된 모듈에서 프로바이더를 꺼내는 것이다. `LazyModuleLoader`로 꺼낸 `LazyModuleRef`는 싱글톤만 지원하므로, REQUEST/TRANSIENT 프로바이더가 필요하다면 `ModuleRef.resolve()`를 써야 한다.

| 상황 | 선택 |
|---|---|
| 런타임에 새 모듈을 초기화, 싱글톤만 필요 | LazyModuleLoader |
| 등록된 모듈에서 REQUEST/TRANSIENT 프로바이더 꺼내기 | ModuleRef.resolve() |
| 순환 의존성 해결 | forwardRef() |
| 부트 전에 모듈 조합 결정 | 조건부 imports |

## 실제로 만난 문제들

**`onModuleInit` 블로킹.** 지연 로딩된 모듈의 `onModuleInit`은 `load()`가 완료된 시점에 실행된다. 타임아웃이 긴 초기화 로직(DB 커넥션 풀 웜업, 외부 서비스 헬스체크 등)이 있으면 `load()`가 블로킹된다. CLI 커맨드에서 첫 `load()` 호출이 예상보다 오래 걸리는 원인은 대부분 이것이다.

**순환 지연 로딩.** `LazyModuleLoader`를 쓰는 모듈 A가 `LazyModuleLoader`를 쓰는 모듈 B를 로드하고, B가 다시 A에 의존하면 NestJS가 감지하지 못하는 순환이 생길 수 있다. 일반 모듈의 순환 의존성은 부트 시점에 잡히지만 지연 로딩은 런타임에서야 드러나므로 디버깅이 어렵다.

**워커 스레드에서의 사용 불가.** `LazyModuleLoader`는 메인 프로세스의 NestJS 컨테이너 안에서 동작한다. `worker_threads`로 생성한 워커 스레드 안에서는 직접 쓸 수 없다. 워커 스레드가 모듈을 초기화하려면 그 스레드 안에서 별도로 `NestFactory.createApplicationContext()`를 생성해야 한다.

**`exports` 누락.** 지연 로딩된 모듈에서 `moduleRef.get()`으로 프로바이더를 가져오려면 해당 프로바이더가 모듈의 `exports` 배열에 있어야 한다. 없으면 `Nest could not find ... in the current context` 예외가 발생한다. 기존 모듈을 지연 로딩용으로 전환할 때 `exports`를 확인하지 않아 이 오류에 걸리는 경우가 많다.
