---
title: NestJS LazyModuleLoader — 동적 모듈 지연 로딩
tags: [nodejs, typescript, backend, architecture]
updated: 2026-09-02
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

주의할 점은 캐싱 동작이다. `load()`는 모듈 클래스를 키로 캐싱한다. 같은 `TypeOrmModule`을 다른 설정으로 두 번 로드하면 두 번째 호출은 첫 번째 설정으로 만든 인스턴스를 반환한다. 커맨드마다 DB URL이 다른 경우처럼 같은 모듈 타입을 다른 설정으로 써야 한다면 별도 모듈 클래스를 만들어야 한다.

## DI 스코프 제약

지연 로딩으로 가져온 모듈의 프로바이더는 `REQUEST` 스코프와 `TRANSIENT` 스코프를 지원하지 않는다. `moduleRef.get()`은 싱글톤 스코프 프로바이더만 가져올 수 있다.

`REQUEST` 스코프 프로바이더를 지연 로딩된 모듈에서 꺼내려 하면 런타임에 예외가 발생한다.

```
Nest can't resolve dependencies of the RequestScopedService.
Please make sure that the argument at index [0] is available in the context.
```

CLI 앱과 워커에서는 HTTP 요청 컨텍스트가 없으므로 `REQUEST` 스코프를 쓰는 경우가 드물다. 하지만 기존 HTTP 서버용 모듈을 CLI에서 재사용할 때 이 제약에 걸리는 경우가 있다. 그럴 때는 해당 프로바이더를 `DEFAULT` 스코프(싱글톤)로 바꾸거나 CLI 전용 프로바이더를 따로 만들어야 한다.

`TRANSIENT` 스코프도 마찬가지다. `get()`으로 가져오면 항상 같은 인스턴스를 반환한다. TRANSIENT 동작이 필요하다면 직접 `new`로 인스턴스를 만들거나 팩토리 패턴으로 우회해야 한다.

## 실제로 만난 문제들

**`onModuleInit` 블로킹.** 지연 로딩된 모듈의 `onModuleInit`은 `load()`가 완료된 시점에 실행된다. 타임아웃이 긴 초기화 로직(DB 커넥션 풀 웜업, 외부 서비스 헬스체크 등)이 있으면 `load()`가 블로킹된다. CLI 커맨드에서 첫 `load()` 호출이 예상보다 오래 걸리는 원인은 대부분 이것이다.

**순환 지연 로딩.** `LazyModuleLoader`를 쓰는 모듈 A가 `LazyModuleLoader`를 쓰는 모듈 B를 로드하고, B가 다시 A에 의존하면 NestJS가 감지하지 못하는 순환이 생길 수 있다. 일반 모듈의 순환 의존성은 부트 시점에 잡히지만 지연 로딩은 런타임에서야 드러나므로 디버깅이 어렵다.

**워커 스레드에서의 사용 불가.** `LazyModuleLoader`는 메인 프로세스의 NestJS 컨테이너 안에서 동작한다. `worker_threads`로 생성한 워커 스레드 안에서는 직접 쓸 수 없다. 워커 스레드가 모듈을 초기화하려면 그 스레드 안에서 별도로 `NestFactory.createApplicationContext()`를 생성해야 한다.

**`exports` 누락.** 지연 로딩된 모듈에서 `moduleRef.get()`으로 프로바이더를 가져오려면 해당 프로바이더가 모듈의 `exports` 배열에 있어야 한다. 없으면 `Nest could not find ... in the current context` 예외가 발생한다. 기존 모듈을 지연 로딩용으로 전환할 때 `exports`를 확인하지 않아 이 오류에 걸리는 경우가 많다.
