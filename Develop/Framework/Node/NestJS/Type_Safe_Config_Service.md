---
title: Type-safe하게 ConfigService로 환경변수 관리하기
tags: [nestjs, config, typescript, type-safety, configservice]
updated: 2026-05-20
---

# Type-safe하게 ConfigService로 환경변수 관리하기

NestJS에서 `ConfigService`를 그냥 쓰면 `string | undefined`가 사방에서 튀어나온다. `get('DB_PORT')`라고 쳤을 때 반환 타입이 무엇인지 IDE가 모르면, 결국 `as number`나 `parseInt(value!, 10)` 같은 캐스팅이 코드 전체에 박힌다. 한번은 `JWT_SECRET`이 `undefined`인데도 타입은 `string`으로 단언되어 토큰이 빈 문자열로 서명된 채 배포된 적이 있다. 그 일 이후로 환경변수에 타입을 못 박는 작업을 별도 문서로 정리하게 됐다.

환경변수 로딩, `.env` 검증 같은 일반론은 [Nest_JS_설정_관리.md](Nest_JS_설정_관리.md)에서 다룬다. 본 문서는 그 위에서 한 단계 더 들어가, `ConfigService`를 어떻게 컴파일 타임에 안전하게 만드는가에만 집중한다.


## ConfigService의 두 가지 제네릭 모드

`@nestjs/config` 5.x 이후부터 `ConfigService`는 두 개의 타입 매개변수를 받는다.

```ts
class ConfigService<K = Record<string, unknown>, WasValidated extends boolean = false>
```

첫 번째 `K`는 설정 객체의 모양이고, 두 번째 `WasValidated`는 값이 검증되었는지를 표시한다. 이 두 번째 인자가 핵심이다. `false`이면 모든 `get()`이 `T | undefined`를 돌려준다. `true`이면 `T`를 돌려준다. 검증이 끝났다는 약속을 타입 시스템에 알려주는 플래그라고 보면 된다.

```ts
// 검증되지 않았다고 본 모드 - 반환은 undefined가 섞임
const port = configService.get<number>('DB_PORT'); // number | undefined

// 검증되었다고 선언한 모드 - undefined 사라짐
const validatedConfig: ConfigService<EnvConfig, true>;
const port2 = validatedConfig.get('DB_PORT', { infer: true }); // number
```

두 번째 인자에 `true`를 넣는 순간 `strictNullChecks`와 맞물려 동작이 달라진다. 검증 함수에서 모든 필수 값을 보장했다는 전제가 깔리는 셈이라, 검증 로직과 타입 선언이 어긋나면 런타임에 폭탄이 된다. `JWT_SECRET`을 `validate` 함수에서 검사하지 않은 채 `ConfigService<EnvConfig, true>`라고 선언해두면, 컴파일러는 `string`이라 믿지만 실제로는 `undefined`인 상황이 그대로 만들어진다.

검증된 모드를 쓰려면 다음 둘 중 하나가 보장되어야 한다.

1. `validate` 함수가 `class-validator`로 모든 필드를 검사한다
2. `validationSchema`(Joi)에서 모든 필드를 `required()`로 묶는다

한쪽이라도 빠지면 `WasValidated`를 `true`로 쓰지 않는 게 낫다.


## infer: true 옵션의 정체

`ConfigService.get()` 시그니처를 펼쳐보면 옵션 객체로 `{ infer: true }`를 받는 오버로드가 있다.

```ts
get<P extends Path<K>>(propertyPath: P, options: { infer: true }): PathValue<K, P>;
```

`infer: true`를 빼면 어떻게 되나? `get<number>('DB.PORT')` 처럼 제네릭으로 직접 타입을 명시해야 한다. 명시하지 않으면 `unknown`이거나 첫 번째 제네릭 자리에 있는 키의 값 전체 타입이 돌아온다. `infer: true`를 넣어야만 NestJS가 `K`의 경로에서 실제 값 타입을 추론해 돌려준다.

```ts
type EnvConfig = {
    database: {
        host: string;
        port: number;
    };
    jwt: {
        secret: string;
    };
};

@Injectable()
class SomeService {
    constructor(private readonly config: ConfigService<EnvConfig, true>) {}

    bad() {
        // infer 누락 - any 또는 잘못된 타입이 추론된다
        const host = this.config.get('database.host'); // 결과 타입이 의도와 다름
    }

    good() {
        // infer: true - PathValue<EnvConfig, 'database.host'>로 추론 = string
        const host = this.config.get('database.host', { infer: true }); // string
        const port = this.config.get('database.port', { infer: true }); // number
    }
}
```

`infer: true`는 매번 호출할 때마다 적어야 한다. 빼먹으면 타입이 슬그머니 `unknown`이나 `string`으로 빠진다. 이게 귀찮으면 뒤에서 설명할 `TypedConfigService` 래퍼를 만들면 된다.

한 가지 더, `infer: true`는 점 표기법 경로(`database.host`)를 통째로 처리한다. 내부적으로 `Path<K>` 타입을 써서 가능한 모든 경로를 union으로 뽑아낸다. 즉 키 자체에 오타가 있으면 컴파일 에러로 잡힌다. `database.hsot`라고 적으면 빌드가 깨진다. 이 자동완성과 오타 검출이 `infer: true`를 쓰는 가장 큰 이유다.


## registerAs와 ReturnType 추론 패턴

설정을 도메인별로 쪼개는 방법이 `registerAs`다. 단순히 함수를 모듈에 등록하는 도구로 끝나지 않고, 반환 타입을 추론해 `ConfigType<typeof xxxConfig>`로 끌어낼 수 있는 게 진짜 쓰임새다.

```ts
// config/database.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('database', () => ({
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT ?? '5432', 10),
    username: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    synchronize: process.env.DB_SYNCHRONIZE === 'true',
}));
```

이 함수의 반환 타입은 `{ host: string | undefined; port: number; ... }`다. NestJS는 이 함수를 `ConfigType`이라는 헬퍼로 다시 끌어낸다.

```ts
import { ConfigType } from '@nestjs/config';
import databaseConfig from './database.config';

type DatabaseConfig = ConfigType<typeof databaseConfig>;
// = { host: string | undefined; port: number; ... }
```

여기서 의도와 어긋나는 점이 하나 있다. `process.env.DB_HOST`는 `string | undefined`라서, 검증을 했더라도 반환 타입은 그대로 `string | undefined`로 잡힌다. 이걸 좁히려면 팩토리 함수 내부에서 단언하거나, `as const`와 `satisfies`로 모양을 못 박는 패턴을 쓴다.


## as const와 satisfies로 타입 좁히기

`satisfies`는 4.9에서 들어온 연산자로, 표현식이 특정 타입을 만족하는지 검사하면서도 표현식의 좁혀진 리터럴 타입은 그대로 보존한다. 환경변수 설정에선 두 가지 효과가 동시에 필요하다.

1. 필수 필드가 빠지지 않았는지 검사하고 싶다
2. 리터럴 값(예: `'production'`, `'development'`)은 좁은 타입으로 남기고 싶다

```ts
type DatabaseShape = {
    host: string;
    port: number;
    type: 'postgres' | 'mysql';
};

export default registerAs('database', () => {
    const config = {
        host: process.env.DB_HOST!,
        port: Number(process.env.DB_PORT),
        type: 'postgres',
    } as const satisfies DatabaseShape;

    return config;
});
```

`as const`는 `type: string`이 아니라 `type: 'postgres'`로 좁히고, `satisfies DatabaseShape`는 모양이 어긋나면 컴파일 에러를 낸다. 이 두 가지가 합쳐지면 `ConfigType<typeof databaseConfig>`로 끌어냈을 때 `type`이 좁은 리터럴로 살아있다.

다만 `process.env.X!`로 단언하는 부분은 위험하다. 위에서 말한 대로 검증 함수가 실제로 `X`를 보장해야 한다. 비검증 환경에서는 `!`를 빼고 `string | undefined`로 두는 편이 안전하다.


## ConfigType<typeof xxxConfig>를 활용한 네임스페이스 주입

`registerAs`로 등록한 설정은 `@Inject(KEY)`로 직접 주입할 수 있다. 이 방식이 `ConfigService.get()`보다 안전하다. 키 경로 문자열이 사라지고, 객체 통째로 들어오기 때문이다.

```ts
// config/jwt.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('jwt', () => ({
    secret: process.env.JWT_SECRET!,
    expiresIn: process.env.JWT_EXPIRES_IN ?? '1h',
    issuer: process.env.JWT_ISSUER ?? 'ygstudy',
}));
```

```ts
// auth.service.ts
import { Inject, Injectable } from '@nestjs/common';
import { ConfigType } from '@nestjs/config';
import jwtConfig from './config/jwt.config';

@Injectable()
export class AuthService {
    constructor(
        @Inject(jwtConfig.KEY)
        private readonly jwt: ConfigType<typeof jwtConfig>,
    ) {}

    sign(payload: object) {
        // jwt.secret, jwt.expiresIn, jwt.issuer 모두 정적 타입
        return jsonwebtoken.sign(payload, this.jwt.secret, {
            expiresIn: this.jwt.expiresIn,
            issuer: this.jwt.issuer,
        });
    }
}
```

`jwtConfig.KEY`는 `registerAs`가 자동으로 만들어주는 심볼이다. 이 패턴의 장점은 명확하다.

- `this.jwt.secret`을 누군가 `this.jwt.scret`로 오타 내면 컴파일 에러가 난다
- 도메인별로 의존하는 설정만 주입받으니까 응집도가 올라간다
- 테스트할 때 `jwtConfig.KEY`만 모킹하면 된다 (전체 `ConfigService`를 흉내낼 필요가 없다)

`ConfigService`를 서비스 내부에 직접 두지 않는 이유는, 그렇게 두면 모든 서비스가 `'database.host'` 같은 마법 문자열을 알게 되기 때문이다. 도메인 단위로 쪼개 주입하면 그런 결합이 사라진다.


## 환경별 분기를 Discriminated Union으로 다루기

`NODE_ENV`에 따라 설정의 모양 자체가 달라지는 경우가 있다. 로컬에서는 SQLite를 쓰고 프로덕션에서는 RDS를 쓴다거나, 개발에선 콘솔 로깅이고 운영에선 Datadog로 보낸다거나. 이걸 단순한 옵셔널로 풀면 어디서나 `if (config.datadog)` 같은 가드가 박힌다. Discriminated Union으로 표현하면 분기 한 번으로 끝난다.

```ts
type LoggingConfig =
    | { driver: 'console'; level: 'debug' | 'info' }
    | { driver: 'datadog'; apiKey: string; service: string; level: 'info' | 'warn' | 'error' };

type AppConfig = {
    env: 'development' | 'production' | 'test';
    logging: LoggingConfig;
};
```

`driver`가 식별자(discriminant)다. 사용하는 쪽에선 이 키를 좁히면 나머지 타입이 자동으로 좁혀진다.

```ts
const logging = configService.get('logging', { infer: true });

if (logging.driver === 'datadog') {
    // 여기선 logging.apiKey가 string으로 좁혀짐
    initDatadog(logging.apiKey, logging.service);
} else {
    // logging.driver === 'console'
    // logging.apiKey에 접근하면 컴파일 에러
}
```

이 방식이 깔끔한 건 옵셔널 체이닝(`logging.apiKey?.length`)을 쓸 일이 사라지기 때문이다. 식별자 한 번만 검사하면 컴파일러가 나머지를 책임진다. `NODE_ENV`에 따라 `registerAs`에서 어떤 객체를 반환할지 분기시키면 된다.

```ts
export default registerAs('logging', (): LoggingConfig => {
    if (process.env.LOG_DRIVER === 'datadog') {
        return {
            driver: 'datadog',
            apiKey: process.env.DATADOG_API_KEY!,
            service: process.env.DATADOG_SERVICE!,
            level: (process.env.LOG_LEVEL as 'info' | 'warn' | 'error') ?? 'info',
        };
    }
    return {
        driver: 'console',
        level: (process.env.LOG_LEVEL as 'debug' | 'info') ?? 'debug',
    };
});
```


## Branded Type으로 비밀값과 일반값 구분

`string` 타입은 너무 헐겁다. `JWT_SECRET`과 `APP_NAME`이 모두 `string`이라면, 실수로 `console.log(jwtSecret)`을 찍어도 컴파일러가 잡아주지 못한다. Branded Type(상표 타입)을 쓰면 같은 `string`이라도 다른 타입으로 분리할 수 있다.

```ts
type Brand<T, B> = T & { readonly __brand: B };

type Secret = Brand<string, 'Secret'>;
type Url = Brand<string, 'Url'>;
type DbHost = Brand<string, 'DbHost'>;

function asSecret(v: string): Secret {
    return v as Secret;
}

function logUrl(u: Url) {
    console.log(`Connecting to ${u}`);
}
```

`Secret`은 일반 `string`을 받지 않는다. 명시적으로 `asSecret()`을 거치거나, `registerAs`에서 반환할 때 좁혀줘야 한다.

```ts
export default registerAs('jwt', () => ({
    secret: process.env.JWT_SECRET! as Secret,
    expiresIn: process.env.JWT_EXPIRES_IN ?? '1h',
}));
```

이렇게 분리하면 로깅 함수가 `Url`만 받게 시그니처를 짜둘 수 있고, 실수로 `Secret`을 로그에 넘기면 컴파일이 깨진다. 비밀값이 로그에 찍히는 사고는 운영 환경에서 한 번이라도 겪어보면 다시는 보고 싶지 않은 것이라서, 이 정도 안전망은 충분히 값어치를 한다.

Branded Type은 런타임에 아무 비용이 없다. 컴파일 시점에만 존재하는 가짜 필드라서 빌드 결과에는 영향이 없다.


## TypedConfigService 래퍼

`infer: true`를 매번 적는 일이 반복되면 실수가 생긴다. 누군가 새 코드를 짜다가 한 번 빼먹으면 그 줄만 `unknown`으로 흐트러진다. 차라리 래퍼를 하나 만들어 `ConfigService`를 직접 노출하지 않는 편이 낫다.

```ts
// typed-config.service.ts
import { Injectable } from '@nestjs/common';
import { ConfigService, Path, PathValue } from '@nestjs/config';

type EnvConfig = {
    database: {
        host: string;
        port: number;
    };
    jwt: {
        secret: string;
        expiresIn: string;
    };
    env: 'development' | 'production' | 'test';
};

@Injectable()
export class TypedConfigService {
    constructor(private readonly config: ConfigService<EnvConfig, true>) {}

    get<P extends Path<EnvConfig>>(key: P): PathValue<EnvConfig, P> {
        return this.config.get(key, { infer: true });
    }

    isProduction(): boolean {
        return this.get('env') === 'production';
    }

    isDevelopment(): boolean {
        return this.get('env') === 'development';
    }
}
```

이 래퍼에는 두 가지 의도가 들어있다.

1. `infer: true`를 강제로 못 박는다. 호출하는 쪽은 그냥 `get('database.host')`만 적으면 된다.
2. 자주 쓰는 분기를 메서드로 박제한다. `isProduction()` 한 번이면 끝난다.

도메인 서비스에서 `ConfigService`를 직접 주입받지 말고 이 `TypedConfigService`를 주입받게 강제하면, 환경변수 접근 방식이 일관된다. 룰을 회피하는 코드를 ESLint로 막고 싶다면 `no-restricted-imports`로 원래 `ConfigService` import를 차단하면 된다.


## 테스트에서 부분 모킹 - DeepPartial 활용

테스트에서 전체 `ConfigService`를 모킹하는 건 고통스럽다. `get()`, `getOrThrow()`, `set()`까지 다 흉내내야 한다. 부분 모킹이 정답인데, 부분이라고 해도 타입을 잃으면 안 된다. `DeepPartial`을 정의해두면 깔끔하다.

```ts
type DeepPartial<T> = T extends object
    ? { [K in keyof T]?: DeepPartial<T[K]> }
    : T;

function createMockConfig(partial: DeepPartial<EnvConfig>): TypedConfigService {
    return {
        get: (path: string) => {
            return path.split('.').reduce<unknown>(
                (acc, key) => (acc as Record<string, unknown> | undefined)?.[key],
                partial,
            );
        },
        isProduction: () => partial.env === 'production',
        isDevelopment: () => partial.env === 'development',
    } as TypedConfigService;
}
```

테스트 코드에서는 필요한 부분만 채워 넣는다.

```ts
describe('AuthService', () => {
    it('JWT 서명 시 secret을 사용한다', () => {
        const config = createMockConfig({
            jwt: { secret: 'test-secret', expiresIn: '5m' },
        });
        const service = new AuthService(config);
        // ...
    });
});
```

`DeepPartial`을 안 쓰고 객체 리터럴로 모킹하면 필드 하나만 채워도 컴파일러가 모든 필드를 요구한다. `DeepPartial`을 통과시키면 빠진 필드는 `undefined`로 두되, 채운 필드는 원래 타입을 지킨다. 테스트에서 `secret: 123`처럼 타입을 어긴 값을 넣으면 컴파일 에러가 난다.

`jest.Mocked<T>`로도 비슷한 효과를 낼 수 있지만, 도메인 모델이 깊으면 `DeepPartial`로 한 번 받아 변환하는 쪽이 호출부가 가볍다.


## 흔히 빠지는 타입 함정들

여기까지 안 잡으면 결국 런타임에 터진다.

### get의 기본값 인자가 타입을 바꿔버린다

```ts
// 첫 번째 시그니처: 기본값 없음
get<T>(propertyPath: KeyOf<K>): T | undefined;

// 두 번째 시그니처: 기본값 있음
get<T>(propertyPath: KeyOf<K>, defaultValue: NoInferType<T>): Exclude<T, undefined>;
```

기본값을 주면 반환에서 `undefined`가 빠진다. 그럴듯해 보이지만 함정이 있다. 기본값의 타입이 추론을 흐트러뜨릴 때가 있다.

```ts
const port = configService.get('DB_PORT', 5432); // number, OK
const host = configService.get('DB_HOST', 'localhost'); // string, OK

// 함정: 기본값을 잘못 주면 타입이 좁아진다
const env = configService.get('NODE_ENV', 'development');
// env의 타입이 string으로만 잡혀, 'development' | 'production' | 'test'로 좁아지지 않음
```

해결은 `infer: true`와 함께 객체 형태로 옵션을 주는 것이다.

```ts
const env = configService.get('NODE_ENV', { infer: true });
// 'development' | 'production' | 'test'로 좁혀짐
```

### number/boolean 변환 누락으로 타입과 런타임이 어긋난다

`process.env.X`는 항상 `string`이다. `EnvConfig`에 `port: number`라고 적어두고 `process.env.DB_PORT`를 그대로 넣으면, 타입은 `number`인데 런타임 값은 `'5432'` 같은 문자열인 상태가 된다. ORM이나 외부 라이브러리가 이걸 받아서 이상한 동작을 일으킨다. `port + 1`이 `'54321'`이 되는 식이다.

`registerAs`에서 변환을 강제하는 게 맞다.

```ts
export default registerAs('database', () => ({
    host: process.env.DB_HOST!,
    port: Number.parseInt(process.env.DB_PORT ?? '5432', 10),
    // boolean도 비슷하게
    synchronize: process.env.DB_SYNCHRONIZE === 'true',
    ssl: ['1', 'true', 'yes'].includes(process.env.DB_SSL?.toLowerCase() ?? ''),
}));
```

`Number()`만 쓰면 `Number('abc') === NaN`이라서 검증 단계에서 막아야 한다. `Joi.number().integer().min(1).max(65535)` 같은 식으로 ConfigModule 검증에 걸어두면 잘못된 값이 들어왔을 때 부팅이 막힌다.

`class-validator`로 검증할 때도 `@Transform`이나 `@Type`을 잊지 말아야 한다. `@IsNumber()`만 달면 `'5432'`는 통과하지 못한다.

```ts
import { Transform } from 'class-transformer';
import { IsNumber, IsString } from 'class-validator';

class EnvSchema {
    @IsString()
    DB_HOST!: string;

    @Transform(({ value }) => Number.parseInt(value, 10))
    @IsNumber()
    DB_PORT!: number;
}
```

### 옵셔널과 필수의 분리 실패

타입 선언에선 모두 필수로 적어놓고, 실제로는 옵셔널인 값이 섞여 있는 경우가 많다.

```ts
type EnvConfig = {
    DB_HOST: string;
    DB_PORT: number;
    SENTRY_DSN: string; // 로컬에서는 없을 수도 있음
};
```

`SENTRY_DSN`이 없는 로컬 환경에서 `ConfigService<EnvConfig, true>`로 받으면 `sentry.dsn`이 `string`이라고 단언되지만 런타임에서는 `undefined`다. 두 가지 방법 중 하나를 골라야 한다.

1. 진짜 필수면 검증 함수에서 막고, 타입은 그대로 `string`으로 둔다 (그러면 로컬에서도 값을 넣어야 부팅된다)
2. 진짜 옵셔널이면 타입을 `string | undefined`로 적고, 사용처에서 가드한다

```ts
type EnvConfig = {
    DB_HOST: string;
    DB_PORT: number;
    SENTRY_DSN?: string; // 명시적 옵셔널
};
```

또는 Discriminated Union으로 환경별 모양 차이를 풀어버리는 것도 방법이다. 무엇이든 "타입에는 필수, 실제로는 옵셔널" 상태는 가장 디버깅하기 어려운 함정이다.


## 한 줄로 줄이면

`ConfigService<T, true>`로 검증 약속을 박고, `registerAs` + `ConfigType<typeof X>`로 도메인별 주입을 쓰고, `infer: true`를 강제하는 `TypedConfigService` 래퍼를 만들고, Branded Type으로 비밀값을 격리하고, `DeepPartial`로 테스트 모킹을 가볍게 한다. 핵심은 하나다. 환경변수에 닿는 코드는 전부 컴파일 타임에 형태가 결정되어야 한다는 것이다. `.env` 로딩과 검증 일반론은 [Nest_JS_설정_관리.md](Nest_JS_설정_관리.md)에서 따로 다룬다.
