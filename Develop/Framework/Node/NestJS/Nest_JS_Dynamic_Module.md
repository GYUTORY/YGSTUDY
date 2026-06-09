---
title: NestJS Dynamic Module 심화
tags: [nestjs, dynamic-module, forroot, forfeature, configurable-module-builder, module-ref, async-providers, library-module, node]
updated: 2026-06-09
---

# NestJS Dynamic Module 심화

NestJS에서 `@Module({ ... })` 데코레이터로 선언된 모듈은 정적(static)이다. import 시점에 메타데이터가 이미 확정되어 있어서 외부에서 설정값을 주입할 여지가 없다. 그런데 `TypeOrmModule.forRoot({ ... })`, `JwtModule.register({ secret: ... })`, `ConfigModule.forRoot({ envFilePath: '.env' })`처럼 import할 때 인자를 받는 모듈이 있다. 이게 Dynamic Module이다. 외부에서 받은 옵션으로 프로바이더를 만들고, `Module` 객체 자체를 런타임에 생성해서 반환한다.

라이브러리 형태의 모듈(설정 모듈, 인증 모듈, DB 모듈, 외부 API 클라이언트 모듈)을 작성하려면 Dynamic Module 패턴을 거의 반드시 써야 한다. 처음에는 `forRoot` 하나만 만들었다가 비동기 설정이 필요해서 `forRootAsync`를 추가하고, 이어서 `forFeature`로 토큰을 분리하면서 모듈 간 의존성이 꼬이기 시작한다. 이 문서는 그런 경험을 정리한다. 모듈 시스템 기본은 [Nest_JS_부트스트랩_및_모듈_시스템.md](Nest_JS_부트스트랩_및_모듈_시스템.md)에서 다뤘으니 여기서는 dynamic module 작성 쪽에 집중한다.


## Dynamic Module의 정체

정적 모듈은 `@Module` 데코레이터가 메타데이터를 클래스에 박아두면 끝이다. 컴파일 시점에 imports/providers/exports가 결정된다. Dynamic Module은 그 메타데이터 객체를 코드로 만들어 반환한다.

```typescript
import { DynamicModule, Module } from '@nestjs/common';

@Module({})
export class ConfigModule {
  static forRoot(options: { envPath: string }): DynamicModule {
    return {
      module: ConfigModule,
      providers: [
        {
          provide: 'CONFIG_OPTIONS',
          useValue: options,
        },
        ConfigService,
      ],
      exports: [ConfigService],
    };
  }
}
```

`forRoot`가 반환하는 객체는 평범한 `DynamicModule`이고, `module`에 자기 자신 클래스를 박는다. NestJS는 이 객체를 받아서 마치 정적 `@Module` 메타데이터처럼 처리한다. 핵심은 외부에서 받은 `options`를 `useValue`로 프로바이더에 박아두면 같은 모듈 안의 다른 프로바이더가 `@Inject('CONFIG_OPTIONS')`로 받아 쓸 수 있다는 점이다. 옵션 전달 통로가 DI 토큰이 된다.

import 쪽은 그냥 메서드 호출 결과를 imports에 넣는다.

```typescript
@Module({
  imports: [ConfigModule.forRoot({ envPath: '.env.production' })],
})
export class AppModule {}
```

이 한 줄을 가능하게 하려고 `forRoot`라는 정적 메서드를 만든다. 메서드 이름은 관습이지 강제가 아니다. `forRoot`, `register`, `forFeature`, `forRootAsync`, `registerAsync` 모두 NestJS 생태계의 합의된 이름일 뿐이다.


## forRoot vs register vs forFeature

세 이름이 다 같은 정적 메서드인데 의미가 다르다. NestJS 공식 컨벤션이 있다.

| 메서드 | 호출 위치 | 호출 빈도 | 용도 |
|--------|-----------|-----------|------|
| `forRoot` | 루트 AppModule | 1회 | 전역 설정. DB 연결, 인증 설정, 로거 |
| `register` | 사용 모듈 | N회 | 모듈마다 독립 설정. HTTP 클라이언트 인스턴스 |
| `forFeature` | feature 모듈 | N회 | forRoot로 만든 공통 자원에 feature별 토큰 등록 |

`TypeOrmModule.forRoot({...})`로 DB 연결을 한 번 만들고, `TypeOrmModule.forFeature([UserEntity])`로 각 도메인 모듈에서 엔티티 레포지토리 토큰을 받는 구조가 전형적이다. `forRoot`가 만든 공통 인프라(Connection, Sequelize 인스턴스)를 `forFeature`가 참조해서 feature별 레포지토리를 등록한다.

`register`는 호출할 때마다 별도 인스턴스를 만든다. `HttpModule.register({ baseURL: 'A' })`와 `HttpModule.register({ baseURL: 'B' })`를 서로 다른 모듈에서 호출하면 두 개의 HTTP 클라이언트가 만들어진다. 이름이 햇갈리면 "공유되는 자원이 있냐"로 구분하면 된다. 있으면 `forRoot`, 없으면 `register`다.

직접 작성하는 dynamic module도 같은 컨벤션을 따라야 한다. 라이브러리로 배포할 때 사용자가 이름만 보고 "아 이건 한 번만 부르는 거구나"를 예측할 수 있어야 한다.


## forRootAsync — 비동기 설정 주입

`forRoot`는 인자로 옵션을 즉시 받는다. 그런데 옵션 자체가 다른 모듈에서 와야 하는 경우가 많다. 예를 들어 JWT secret이 `ConfigService`에 있는 경우.

```typescript
JwtModule.forRoot({
  secret: ???,  // ConfigService.get('JWT_SECRET') — 어떻게 받지?
})
```

`forRoot` 호출 시점에 `ConfigService`는 아직 인스턴스화되지 않았다. 모듈 메타데이터를 만드는 시점은 DI 컨테이너가 부트되기 전이다. 그래서 옵션을 비동기로 만들 통로가 필요하다. 이게 `forRootAsync`다.

```typescript
@Module({})
export class JwtModule {
  static forRootAsync(options: {
    imports?: any[];
    useFactory: (...args: any[]) => Promise<JwtOptions> | JwtOptions;
    inject?: any[];
  }): DynamicModule {
    return {
      module: JwtModule,
      imports: options.imports ?? [],
      providers: [
        {
          provide: 'JWT_OPTIONS',
          useFactory: options.useFactory,
          inject: options.inject ?? [],
        },
        JwtService,
      ],
      exports: [JwtService],
    };
  }
}
```

사용하는 쪽은 useFactory에서 ConfigService를 주입받아 옵션을 만든다.

```typescript
@Module({
  imports: [
    ConfigModule.forRoot(),
    JwtModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: async (config: ConfigService) => ({
        secret: config.get<string>('JWT_SECRET'),
        signOptions: { expiresIn: '1h' },
      }),
      inject: [ConfigService],
    }),
  ],
})
export class AppModule {}
```

핵심은 옵션 프로바이더(`JWT_OPTIONS`)를 `useValue`가 아니라 `useFactory`로 만든다는 점이다. `useFactory`는 DI 컨테이너가 부트되면서 호출되므로, 그 시점에는 `ConfigService`가 이미 인스턴스화돼 있다. `inject`로 의존성을 받아서 factory 함수의 인자로 넣어준다.

`imports`를 따로 받는 이유는 `useFactory`에서 주입받을 프로바이더가 있는 모듈을 dynamic module 내부 imports에 넣어줘야 하기 때문이다. 부모 AppModule에서 `ConfigModule`을 import해놨다고 해서 자식 `JwtModule`이 자동으로 보는 건 아니다. 자식 모듈이 자기 imports에 명시해야 DI 그래프가 연결된다. 이 점을 빼먹고 `Nest can't resolve dependencies of the JWT_OPTIONS (?)` 에러를 만나는 게 dynamic module 디버깅의 절반이다.

`@Global()`로 표시된 모듈(예: `@nestjs/config`의 `ConfigModule.forRoot({ isGlobal: true })`)이면 imports를 생략해도 된다. 글로벌 모듈은 한 번 import되면 어디서나 보이기 때문이다. 단, 이때도 명시적으로 imports에 넣어주는 게 디버깅에 유리하다. "이 dynamic module이 어떤 의존성을 쓰는지" 코드만 보고 알 수 있어야 한다.


## useClass와 useExisting — factory 외 옵션 주입

`forRootAsync`를 만들 때 `useFactory`만 지원하면 사용자가 옵션 만드는 코드를 매번 inline으로 써야 한다. 옵션이 복잡해지면 별도 클래스로 빼고 싶어진다. 그래서 `useClass`와 `useExisting`을 지원하는 패턴이 표준이 됐다.

```typescript
interface JwtOptionsFactory {
  createJwtOptions(): Promise<JwtOptions> | JwtOptions;
}

interface JwtModuleAsyncOptions {
  imports?: any[];
  useExisting?: Type<JwtOptionsFactory>;
  useClass?: Type<JwtOptionsFactory>;
  useFactory?: (...args: any[]) => Promise<JwtOptions> | JwtOptions;
  inject?: any[];
}

@Module({})
export class JwtModule {
  static forRootAsync(options: JwtModuleAsyncOptions): DynamicModule {
    return {
      module: JwtModule,
      imports: options.imports ?? [],
      providers: [
        ...this.createAsyncProviders(options),
        JwtService,
      ],
      exports: [JwtService],
    };
  }

  private static createAsyncProviders(options: JwtModuleAsyncOptions): Provider[] {
    if (options.useExisting || options.useFactory) {
      return [this.createAsyncOptionsProvider(options)];
    }
    // useClass: 옵션 팩토리 클래스 자체도 프로바이더로 등록해야 한다
    return [
      this.createAsyncOptionsProvider(options),
      {
        provide: options.useClass!,
        useClass: options.useClass!,
      },
    ];
  }

  private static createAsyncOptionsProvider(options: JwtModuleAsyncOptions): Provider {
    if (options.useFactory) {
      return {
        provide: 'JWT_OPTIONS',
        useFactory: options.useFactory,
        inject: options.inject ?? [],
      };
    }
    return {
      provide: 'JWT_OPTIONS',
      useFactory: async (factory: JwtOptionsFactory) => factory.createJwtOptions(),
      inject: [options.useExisting ?? options.useClass!],
    };
  }
}
```

코드가 길어 보이지만 패턴은 일정하다. NestJS 공식 모듈 대부분이 이 골격을 쓴다. 사용자는 세 방식 중 골라 쓰면 된다.

```typescript
// 방식 1: useFactory — 가장 자주 쓰는 형태
JwtModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: (config: ConfigService) => ({ secret: config.get('JWT_SECRET') }),
  inject: [ConfigService],
});

// 방식 2: useClass — 옵션 만드는 로직이 복잡할 때
JwtModule.forRootAsync({
  useClass: JwtConfigService,  // implements JwtOptionsFactory
});

// 방식 3: useExisting — 이미 다른 모듈에서 만든 팩토리를 재사용
JwtModule.forRootAsync({
  imports: [SharedConfigModule],
  useExisting: SharedJwtConfigService,
});
```

`useClass`와 `useExisting`의 차이가 미묘한데, `useClass`는 새 인스턴스를 만들고 `useExisting`은 외부에서 이미 만든 인스턴스를 가져온다. 같은 팩토리 클래스를 두 dynamic module에서 동시에 쓸 때 `useClass`로 양쪽에서 등록하면 인스턴스가 두 개 생긴다. 그 인스턴스가 stateful하면 미묘한 버그가 생긴다. 이럴 때 `useExisting`을 쓴다.


## ConfigurableModuleBuilder — 보일러플레이트를 줄인다

위 코드를 모든 dynamic module마다 매번 작성하는 게 지긋지긋해서, NestJS 9부터 `ConfigurableModuleBuilder`가 들어왔다. 옵션 인터페이스만 정의하면 `forRoot`/`forRootAsync` 메서드를 자동 생성해준다.

```typescript
import { ConfigurableModuleBuilder } from '@nestjs/common';

export interface JwtOptions {
  secret: string;
  signOptions?: { expiresIn: string };
}

export const {
  ConfigurableModuleClass,
  MODULE_OPTIONS_TOKEN,
} = new ConfigurableModuleBuilder<JwtOptions>()
  .setClassMethodName('forRoot')
  .build();

@Module({
  providers: [JwtService],
  exports: [JwtService],
})
export class JwtModule extends ConfigurableModuleClass {}
```

이 다섯 줄이 위 50줄짜리 코드와 거의 동일한 일을 한다. `JwtModule.forRoot({...})`, `JwtModule.forRootAsync({ useFactory: ... })`, `JwtModule.forRootAsync({ useClass: ... })` 셋이 자동 생성된다. 옵션은 `MODULE_OPTIONS_TOKEN`이라는 자동 생성 토큰으로 주입받는다.

```typescript
@Injectable()
export class JwtService {
  constructor(
    @Inject(MODULE_OPTIONS_TOKEN) private readonly options: JwtOptions,
  ) {}
}
```

`setClassMethodName('forRoot')`로 메서드 이름을 바꿀 수 있다. `register`로 두면 `JwtModule.register({...})`, `JwtModule.registerAsync({...})`가 된다. 이름만 바꾸는 거고 동작은 같다.

`setExtras`로 옵션 외 추가 메타데이터를 받을 수도 있다. 예를 들어 모듈을 글로벌로 만들지 여부를 옵션 객체 안에 섞지 않고 별도로 받고 싶을 때.

```typescript
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<JwtOptions>()
    .setExtras(
      { isGlobal: false },
      (definition, extras) => ({
        ...definition,
        global: extras.isGlobal,
      }),
    )
    .build();

// 사용
JwtModule.forRoot({ secret: 'x', isGlobal: true });
```

이걸 직접 구현하면 forRoot 안에서 `if (options.isGlobal) return { global: true, ... }` 같은 분기를 매번 써야 한다. `setExtras`는 그 분기를 한 곳에 모아준다.

`ConfigurableModuleBuilder`를 쓸 때 한 가지 함정은, 자동 생성된 옵션 토큰의 키가 ConfigurableModuleBuilder가 만들어준 심볼이라는 점이다. 따라서 토큰을 export해야 외부에서 `@Inject(MODULE_OPTIONS_TOKEN)`으로 받을 수 있다. 라이브러리로 배포하면서 토큰 export를 빼먹으면 사용자가 "옵션을 어떻게 받지?"하고 막힌다.


## forFeature — 공유 자원에 토큰 추가하기

`forRoot`로 공유 인프라(DB Connection, Cache Manager 등)를 만들었으면, `forFeature`는 그 인프라를 기반으로 feature별 토큰을 추가 등록한다. TypeORM이 가장 직관적인 예다.

```typescript
// 루트
TypeOrmModule.forRoot({
  type: 'postgres',
  host: '...',
  // ...
});

// feature 모듈
@Module({
  imports: [TypeOrmModule.forFeature([UserEntity, OrderEntity])],
  providers: [UserService],
})
export class UserModule {}
```

`forFeature([UserEntity])`가 하는 일은 `getRepositoryToken(UserEntity)` 토큰으로 `Repository<UserEntity>`를 등록하고 export하는 것이다. `forRoot`가 만든 Connection을 참조해서 Repository를 생성한다. 즉 `forFeature`는 그 자체로 독립된 자원을 만드는 게 아니라, `forRoot`의 결과물을 활용해 feature별 토큰을 만든다.

직접 작성할 때도 이 분리를 지키면 깔끔하다. 예를 들어 외부 API 클라이언트 모듈을 만든다면, `forRoot`에서 공통 HTTP 클라이언트(인증 헤더, baseURL, 타임아웃)를 등록하고, `forFeature(['users', 'orders'])`에서 엔드포인트별 wrapper를 토큰으로 등록한다.

```typescript
@Module({})
export class ApiClientModule {
  static forRoot(options: ApiClientOptions): DynamicModule {
    return {
      module: ApiClientModule,
      global: true,  // 공유 클라이언트는 글로벌로
      providers: [
        { provide: 'API_OPTIONS', useValue: options },
        HttpClient,
      ],
      exports: [HttpClient],
    };
  }

  static forFeature(resources: string[]): DynamicModule {
    const providers = resources.map((resource) => ({
      provide: `API_${resource.toUpperCase()}_CLIENT`,
      useFactory: (httpClient: HttpClient) => httpClient.scope(resource),
      inject: [HttpClient],
    }));
    return {
      module: ApiClientModule,
      providers,
      exports: providers,
    };
  }
}
```

여기서 흔히 하는 실수가 `forFeature`에서도 `global: true`를 주는 것이다. feature별 토큰까지 글로벌로 만들면 모듈 간 의존 관계가 코드만 봐서는 안 보인다. 어디서 import했는지 추적이 안 되니까 리팩토링이 위험해진다. `forRoot`만 글로벌, `forFeature`는 명시적 import가 원칙이다.


## 라이브러리 모듈 작성 시 module reference 충돌

dynamic module을 모놀리식 앱 안에서만 쓸 때는 모르는데, 사내 라이브러리나 npm 패키지로 빼면 module reference 관련 함정이 줄줄이 나타난다.

가장 흔한 함정은 `forFeature`를 여러 번 호출했을 때 마지막 호출만 살아남는 것처럼 보이는 현상이다. 원인은 NestJS의 모듈 캐싱이다. `module: SomeModule`이 같은 클래스를 가리키면, NestJS는 같은 모듈로 간주해 dedup한다. dynamic module의 `module` 필드가 클래스 자체를 가리키므로, 같은 모듈에 대한 두 번의 dynamic 호출은 메타데이터만 머지된다.

```typescript
// UserModule에서
imports: [TypeOrmModule.forFeature([UserEntity])]

// OrderModule에서
imports: [TypeOrmModule.forFeature([OrderEntity])]
```

이렇게 쓰면 UserModule 안에서 `getRepositoryToken(OrderEntity)`를 주입받아도 동작한다. dedup된 dynamic module이 두 엔티티 모두를 export하기 때문이다. 의도한 격리(UserModule은 User만, OrderModule은 Order만)가 깨지는데, 일반적으로는 이게 편해서 NestJS가 그렇게 설계됐다.

문제는 이 동작을 모르고 "feature 모듈마다 다른 옵션을 주고 싶다"는 케이스에서 발생한다. 예를 들어 같은 `HttpModule`을 모듈 A에서는 baseURL=A로, 모듈 B에서는 baseURL=B로 쓰고 싶을 때. 위 dedup 동작 때문에 옵션이 마지막 것으로 덮어쓰이거나, 토큰 충돌이 난다.

해결책은 `provide` 토큰을 분리하는 것이다. dynamic module 내부에서 `useValue: options`로 등록하는 토큰 자체를 호출별로 다르게 만들면 충돌이 안 난다.

```typescript
static register(options: { name: string; baseURL: string }): DynamicModule {
  const optionsToken = `HTTP_OPTIONS_${options.name}`;
  const clientToken = `HTTP_CLIENT_${options.name}`;
  return {
    module: HttpClientModule,
    providers: [
      { provide: optionsToken, useValue: options },
      {
        provide: clientToken,
        useFactory: (opts) => new HttpClient(opts),
        inject: [optionsToken],
      },
    ],
    exports: [clientToken],
  };
}
```

이렇게 하면 같은 `HttpClientModule`을 여러 번 register해도 각자 다른 토큰으로 분리된다. 사용 쪽에서는 `@Inject('HTTP_CLIENT_payment')`처럼 받는다. 일종의 매뉴얼 멀티 인스턴스 패턴이다. 다만 토큰 문자열을 사용자가 알아야 하니, 보통은 토큰 생성 헬퍼를 같이 export한다.

```typescript
export const getHttpClientToken = (name: string) => `HTTP_CLIENT_${name}`;

// 사용
@Inject(getHttpClientToken('payment')) private client: HttpClient;
```


## ModuleRef — DI 컨테이너에 직접 접근

dynamic module 내부에서, 또는 dynamic하게 등록된 프로바이더가 다른 프로바이더를 런타임에 조회해야 할 때가 있다. 생성자 주입으로 안 되는 경우(주입 시점에 그 프로바이더가 어떤 토큰인지 모르는 경우)에는 `ModuleRef`를 쓴다.

```typescript
import { ModuleRef } from '@nestjs/core';

@Injectable()
export class DynamicHandlerRegistry {
  constructor(private readonly moduleRef: ModuleRef) {}

  async dispatch(type: string, payload: unknown) {
    const token = `HANDLER_${type}`;
    const handler = this.moduleRef.get(token, { strict: false });
    return handler.handle(payload);
  }
}
```

`moduleRef.get()`은 기본적으로 자기가 속한 모듈 컨텍스트에서만 찾는다. 다른 모듈의 export까지 뒤지려면 `{ strict: false }` 옵션이 필요하다. dynamic module에서 등록한 토큰이 import 모듈의 컨텍스트에 있을 때 `strict: true`(기본)로 찾으면 못 찾는다.

`moduleRef.resolve()`는 transient·request-scoped 프로바이더를 가져올 때 쓴다. `get`은 싱글톤 전용이라 transient 프로바이더에 호출하면 매번 다른 인스턴스가 나올 거란 기대와 달리 에러가 난다.

```typescript
// transient/request scope 프로바이더
const instance = await this.moduleRef.resolve(SomeTransientService);

// 싱글톤
const instance = this.moduleRef.get(SomeSingletonService);
```

dynamic module에서 ModuleRef를 자주 쓰는 시나리오는 플러그인 패턴이다. 사용자가 `forRoot`로 핸들러 클래스 목록을 넘기면, 모듈이 각 핸들러를 프로바이더로 등록하고 런타임에 토큰으로 찾아 디스패치한다.

```typescript
@Module({})
export class PluginModule {
  static forRoot(handlers: Type<Handler>[]): DynamicModule {
    const handlerProviders = handlers.map((H) => ({
      provide: `HANDLER_${H.name}`,
      useClass: H,
    }));
    return {
      module: PluginModule,
      providers: [
        ...handlerProviders,
        {
          provide: 'HANDLER_TOKENS',
          useValue: handlers.map((H) => `HANDLER_${H.name}`),
        },
        PluginRegistry,
      ],
      exports: [PluginRegistry],
    };
  }
}

@Injectable()
export class PluginRegistry {
  constructor(
    @Inject('HANDLER_TOKENS') private readonly tokens: string[],
    private readonly moduleRef: ModuleRef,
  ) {}

  getAll(): Handler[] {
    return this.tokens.map((t) => this.moduleRef.get<Handler>(t));
  }
}
```

이 패턴은 외부에서 받은 클래스 목록이 컴파일 타임에 알 수 없을 때 유용하다. 단점은 type-safety가 약해진다는 점이다. `moduleRef.get<Handler>()`의 제네릭은 컴파일러 추론용이고 런타임 검증이 아니다.

`ModuleRef.create()`로 모듈에 등록되지 않은 클래스의 인스턴스를 즉석에서 만들 수도 있다. DI는 주입되지만 컨테이너에는 등록 안 되는 일회성 인스턴스다. 잘 안 쓰는 기능이지만, 같은 클래스로 여러 격리된 인스턴스가 필요한 특수 케이스에서 등장한다.


## 전역 vs 비전역 dynamic module

dynamic module이 반환하는 객체에 `global: true`를 넣으면 글로벌 모듈이 된다. 한 번 import하면 모든 모듈에서 export된 프로바이더에 접근할 수 있다.

```typescript
static forRoot(options: ConfigOptions): DynamicModule {
  return {
    module: ConfigModule,
    global: true,
    providers: [...],
    exports: [...],
  };
}
```

또는 `@nestjs/config`처럼 옵션으로 받기도 한다.

```typescript
ConfigModule.forRoot({ isGlobal: true });
```

글로벌 모듈은 편하지만 남용하면 모듈 그래프가 망가진다. "이 서비스는 어디서 import했지?"가 코드 추적으로 안 찾아진다. 그래서 글로벌로 만들 모듈은 명확한 기준이 있어야 한다.

글로벌이 적절한 경우는 (a) 앱 전체에서 거의 모든 모듈이 쓰는 공통 인프라(`ConfigService`, `LoggerService`, `CacheManager`), (b) 한 번만 등록하는 게 의미가 분명한 자원(DB Connection, Redis Connection)이다.

비전역으로 둘 경우는 (a) 옵션 별로 여러 인스턴스가 가능한 자원(여러 외부 API 클라이언트, 여러 큐), (b) feature 모듈 단위 토큰(`forFeature` 결과물), (c) 도메인 로직 서비스 전반이다.

dynamic module을 글로벌로 만들 때 함정이 하나 있다. 이미 글로벌로 등록된 모듈을 다른 곳에서 다시 import해도 NestJS는 dedup해서 한 번만 적용한다. 그런데 dynamic module은 호출마다 메타데이터를 새로 만든다. 같은 dynamic module을 두 모듈에서 다른 옵션으로 `forRoot` 호출하면 두 번째 호출이 옵션을 덮어쓰는 식의 의도치 않은 동작이 생길 수 있다. `forRoot`는 루트 AppModule에서 단 한 번만 호출한다는 컨벤션을 라이브러리 문서에 명시해두는 게 안전하다.

`@Global()` 데코레이터를 dynamic module 클래스에 붙이는 방법도 있다.

```typescript
@Global()
@Module({})
export class ConfigModule {
  static forRoot(options): DynamicModule {
    return { module: ConfigModule, providers: [...], exports: [...] };
  }
}
```

이렇게 하면 `global: true`를 매번 반환할 필요가 없다. 단점은 비전역으로 쓸 옵션이 없어진다는 것이다. `isGlobal` 옵션으로 선택 가능하게 하려면 데코레이터 대신 `global: options.isGlobal` 식으로 반환 객체에서 결정해야 한다.


## 비동기 onModuleInit과 dynamic 의존성

dynamic module 안에서 `useFactory`로 만든 옵션 프로바이더를 다른 프로바이더가 주입받는 경우, 그 주입은 DI 컨테이너 부트 단계에서 끝난다. 즉 `useFactory`의 Promise가 resolve된 다음에 의존하는 프로바이더가 생성된다. 이 순서는 자동으로 보장된다.

문제는 `onModuleInit`에서 모듈 간 의존성을 다룰 때 생긴다. `onModuleInit` 호출 순서는 모듈 그래프의 위상 정렬을 따른다. dynamic으로 등록된 모듈이 의존 트리상 어디에 위치하는지에 따라 init 순서가 바뀐다.

```typescript
@Injectable()
export class CacheWarmer implements OnModuleInit {
  constructor(
    @Inject('CACHE_MANAGER') private cache: Cache,
    private userService: UserService,
  ) {}

  async onModuleInit() {
    const users = await this.userService.findAll();
    await this.cache.set('users', users);
  }
}
```

`CacheWarmer`가 `UserService`와 같은 모듈에 있고 `UserService`가 다른 모듈에 있으면, `UserService.onModuleInit`이 먼저 끝났는지 보장되지 않을 수 있다. UserService의 의존 모듈에 dynamic module(예: DB)이 끼어 있으면 dynamic module의 init 순서에 따라 결과가 달라진다.

이걸 해결하는 단순한 방법은 `onModuleInit` 대신 `onApplicationBootstrap`을 쓰는 것이다. 후자는 모든 모듈의 `onModuleInit`이 끝난 다음에 호출된다. 전체 DI 그래프가 완성된 상태에서 동작하는 게 보장된다. dynamic module이 끼어든 경우 특히 권장된다.

라이프사이클 훅 자체는 [Nest_JS_Lifecycle_Hooks.md](Nest_JS_Lifecycle_Hooks.md)에서 다룬다. dynamic module 작성자가 기억할 핵심은 "init 시점에 다른 모듈의 상태를 가정하지 마라"다. 라이브러리 모듈이라면 더 그렇다. 사용자가 어떤 모듈 트리에 꽂아 쓸지 모른다.


## forRoot에서 자식 모듈 import — 합쳐진 그래프

dynamic module의 반환 객체에는 `imports`도 넣을 수 있다. 옵션에 따라 동적으로 import할 모듈을 결정하고 싶을 때 쓴다.

```typescript
static forRoot(options: { useRedis: boolean }): DynamicModule {
  const imports = [];
  if (options.useRedis) {
    imports.push(RedisModule.forRoot({ host: 'localhost' }));
  }
  return {
    module: StorageModule,
    imports,
    providers: [StorageService],
    exports: [StorageService],
  };
}
```

옵션에 따라 백엔드를 갈아끼우는 패턴이다. `StorageService`는 둘 다 알 필요 없이 dynamic하게 들어온 백엔드만 쓰면 된다.

주의할 점은 `imports`로 dynamic module을 다시 쓸 때 그 자식 dynamic module의 export가 부모(여기서는 `StorageModule`)에서 다시 export되지 않는다는 것이다. NestJS는 import한 모듈의 export를 자동으로 자기 export에 포함시키지 않는다. 사용자가 `StorageModule`을 import해서 `RedisService`(가상)를 받고 싶다면 명시적으로 다시 export해야 한다.

```typescript
return {
  module: StorageModule,
  imports: [RedisModule],
  providers: [StorageService],
  exports: [StorageService, RedisModule],  // RedisModule을 다시 export하면 그 export가 노출됨
};
```

이걸 모르면 "분명 import했는데 사용 쪽에서 RedisService를 못 찾는다"는 상황을 디버깅하느라 시간을 쓴다.


## 테스트 — dynamic module override

테스트에서 dynamic module을 mock으로 교체하는 게 까다롭다. 정적 모듈은 `Test.createTestingModule({ imports: [SomeModule] })` 뒤에 `.overrideProvider(...).useValue(...)`로 갈아끼울 수 있지만, dynamic module의 옵션 토큰처럼 호출별로 다른 토큰을 쓰면 override가 안 잡힌다.

표준적인 방법은 dynamic module의 옵션을 테스트 전용 값으로 호출하는 것이다.

```typescript
const module = await Test.createTestingModule({
  imports: [
    JwtModule.forRoot({ secret: 'test-secret', signOptions: { expiresIn: '5m' } }),
  ],
}).compile();
```

옵션 자체를 외부 의존성(DB, Redis)에 의존시키지 말고 인터페이스를 통해 주입받게 설계하면 테스트가 쉽다. 예를 들어 옵션을 받는 게 아니라 옵션 팩토리 클래스를 받게 만들면, 테스트에서는 mock 팩토리를 주입한다.

```typescript
// 라이브러리
JwtModule.forRootAsync({
  useClass: JwtConfigFactory,
});

// 테스트
JwtModule.forRootAsync({
  useFactory: () => ({ secret: 'test', signOptions: { expiresIn: '1h' } }),
});
```

`useFactory`를 지원하는 dynamic module이면 테스트 코드에서 옵션을 즉석에서 만들 수 있어 편하다. 라이브러리 모듈을 작성한다면 `useFactory`를 항상 지원하는 게 좋다.


## 마무리 — 작성 순서 정리

dynamic module 하나를 처음부터 만든다면 보통 이 순서로 작성한다.

1. 옵션 인터페이스 정의 (`interface XOptions`)
2. `ConfigurableModuleBuilder`로 `forRoot`/`forRootAsync` 자동 생성
3. 옵션 토큰을 주입받는 서비스 작성
4. feature별 토큰이 필요하면 `forFeature` 정적 메서드 추가
5. 글로벌 여부 결정 (default는 비전역)
6. README에 호출 컨벤션 명시 (forRoot 1회, forFeature N회)

처음부터 `ConfigurableModuleBuilder`로 시작하는 게 가장 보일러플레이트가 적다. 옵션 구조가 복잡해지거나 `setExtras`로 처리 안 되는 분기가 생기면 그때 직접 작성으로 내려간다. 보통은 `ConfigurableModuleBuilder` 만으로 라이브러리 모듈의 80%가 커버된다.

dynamic module은 사용자 경험을 좌우한다. `MyModule.forRoot(...)` 한 줄로 끝나는 라이브러리가 사용자에게 친절하다. 그 한 줄을 만들기 위해 내부에 옵션 통로, 비동기 팩토리, 토큰 분리, 글로벌 처리, 라이프사이클 고려가 들어간다. 외부에 노출되는 API가 얼마나 단순한지가 dynamic module 설계의 품질이다.
