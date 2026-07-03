---
title: NestJS 부트스트랩 및 모듈 시스템
tags: [nestjs, bootstrap, module, lifecycle, dynamic-module, module-ref, lazy-loading, graceful-shutdown, forwardref, global-module, hmr, node]
updated: 2026-06-06
---

# NestJS 부트스트랩 및 모듈 시스템

NestJS 애플리케이션이 시작될 때 `NestFactory.create()` 한 줄 뒤에서 꽤 많은 일이 벌어진다. 모듈을 스캔하고, 의존성 그래프를 만들고, 프로바이더 인스턴스를 생성하는 과정이 순서대로 진행된다. 이 과정을 모르면 "왜 내 서비스가 아직 초기화 안 됐지?", "왜 OnModuleInit에서 다른 모듈의 서비스를 못 쓰지?"같은 문제를 만난다. main.ts 부트스트랩 흐름과 NestFactory.create 옵션부터, AppModule 구성, imports/exports/providers/controllers의 역할, forwardRef로 순환참조를 푸는 방법, @Global 모듈의 함정, HMR 설정, Graceful Shutdown까지 정리한다.


## main.ts에서 일어나는 일

NestJS 진입점은 보통 `src/main.ts`다. CLI로 프로젝트를 만들면 다음 형태의 코드가 생성된다.

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
}
bootstrap();
```

이 짧은 코드 안에서 두 단계가 일어난다. `NestFactory.create()`는 DI 컨테이너를 구성하고 모든 프로바이더를 초기화한다. `app.listen()`은 HTTP 서버를 띄워 포트에 바인딩한다. 두 단계가 분리되어 있다는 점이 중요한데, `create()`만 호출하고 `listen()`을 호출하지 않으면 서버는 안 뜨지만 모든 DI는 끝난 상태가 된다. 마이그레이션 스크립트나 CLI 도구에서 NestJS DI만 빌려 쓰고 싶을 때 이 동작을 활용한다.

실무 main.ts는 보통 글로벌 설정을 한곳에 모은다.

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true,
    cors: { origin: ['https://app.example.com'], credentials: true },
  });

  // 글로벌 파이프·필터·인터셉터
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.useGlobalFilters(new HttpExceptionFilter());
  app.useGlobalInterceptors(new LoggingInterceptor());

  // 종료 훅 활성화 (쿠버네티스 환경에서 필수)
  app.enableShutdownHooks();

  // 글로벌 prefix
  app.setGlobalPrefix('api/v1');

  // Swagger는 개발·스테이징에서만
  if (process.env.NODE_ENV !== 'production') {
    const config = new DocumentBuilder()
      .setTitle('API')
      .setVersion('1.0')
      .build();
    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('docs', app, document);
  }

  await app.listen(process.env.PORT ?? 3000);
}
bootstrap();
```

main.ts에서 `useGlobalPipes()`로 등록한 인스턴스는 모듈 시스템 밖에서 만들어진다. 그래서 그 파이프 내부에서 다른 프로바이더(예: `ConfigService`)를 주입받을 수 없다. DI가 필요한 글로벌 인스턴스는 `APP_PIPE`, `APP_FILTER`, `APP_INTERCEPTOR`, `APP_GUARD` 토큰으로 모듈에 등록해야 한다.

```typescript
@Module({
  providers: [
    {
      provide: APP_PIPE,
      useClass: ValidationPipe,  // ConfigService를 생성자 주입 가능
    },
  ],
})
export class AppModule {}
```

두 방식의 차이를 모르고 main.ts에서만 글로벌로 등록하면 "왜 내 글로벌 인터셉터에서 LoggerService가 undefined로 들어오지?" 같은 상황을 만난다. DI가 필요하면 모듈 토큰으로 등록한다. DI가 필요 없는 단순 미들웨어성 글로벌(예: 정적 옵션만 받는 ValidationPipe)이면 main.ts에서 등록해도 무방하다.


## NestFactory.create() 옵션

`NestFactory.create()`는 두 번째 파라미터로 옵션 객체를 받는다. 자주 쓰는 옵션은 다음과 같다.

| 옵션 | 설명 |
|------|------|
| `cors` | CORS 미들웨어 설정. `true`면 모든 origin 허용, 객체로 세부 설정 |
| `bodyParser` | JSON/URL-encoded 바디 파서 자동 활성화 여부. 기본 `true` |
| `logger` | 로거 인스턴스나 로그 레벨 배열. `['log', 'error', 'warn', 'debug']` 형태 |
| `bufferLogs` | 커스텀 로거 적용 전까지 로그를 버퍼링. ConfigModule로 로그 레벨을 결정할 때 |
| `abortOnError` | 부트스트랩 실패 시 `process.exit(1)` 여부. 기본 `true` |
| `rawBody` | Stripe 웹훅처럼 원본 body가 필요한 경우. `req.rawBody`로 접근 |
| `httpsOptions` | HTTPS 서버용 인증서 설정 |
| `snapshot` | DI 그래프 스냅샷 생성. Devtools에서 의존성 시각화할 때 사용 |

```typescript
const app = await NestFactory.create(AppModule, {
  cors: false,                 // CORS를 미들웨어에서 직접 처리
  bodyParser: false,           // 커스텀 바디 파서를 모듈에서 등록
  logger: ['error', 'warn'],   // 프로덕션에서 verbose 로그를 끔
  bufferLogs: true,            // PinoLogger 적용 전까지 로그를 버퍼링
  abortOnError: false,         // 부트스트랩 실패해도 프로세스를 유지 (테스트)
  rawBody: true,               // Stripe 웹훅 서명 검증
});
```

`bufferLogs: true`는 실무에서 자주 쓴다. NestJS 기본 로거가 ConfigModule이 로드되기 전에 동작하면 로그 레벨 설정이 늦게 반영되는데, 버퍼링을 켜두면 커스텀 로거가 준비된 시점에 한꺼번에 flush한다.

```typescript
const app = await NestFactory.create(AppModule, { bufferLogs: true });
app.useLogger(app.get(PinoLogger));  // 버퍼링된 로그가 Pino로 흘러감
```

### Express vs Fastify 어댑터

기본은 Express 어댑터다. Fastify로 바꾸려면 어댑터를 명시적으로 넘긴다.

```typescript
import { FastifyAdapter, NestFastifyApplication } from '@nestjs/platform-fastify';

const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({ logger: true }),
);

await app.listen(3000, '0.0.0.0');  // Fastify는 host 명시를 권장
```

Fastify가 Express보다 처리량은 빠르지만, NestJS 생태계의 일부 미들웨어가 Express용으로 작성되어 호환성 문제가 있다. `passport`, `express-session`은 Fastify에서 별도 어댑터(`@fastify/passport`, `@fastify/session`)를 써야 한다. 처리량이 크리티컬한 게이트웨이가 아니라면 굳이 Fastify로 바꿀 이유가 적다.

### createMicroservice / createApplicationContext

`NestFactory`는 `create()` 외에 두 가지 메서드를 더 제공한다.

- `createMicroservice()`: TCP, Redis, gRPC 등 마이크로서비스 트랜스포트 위에 NestJS 앱을 띄운다. HTTP 서버 없이 메시지 핸들러만 동작한다.
- `createApplicationContext()`: HTTP 서버도 메시지 트랜스포트도 없는 순수 DI 컨테이너. 마이그레이션 스크립트, CLI 도구, 일회성 배치 작업에 사용한다.

```typescript
// 마이그레이션 CLI 예시
async function runMigration() {
  const app = await NestFactory.createApplicationContext(AppModule);
  const migrationService = app.get(MigrationService);
  await migrationService.run();
  await app.close();
}
runMigration();
```

`createApplicationContext()`로 만든 앱은 HTTP 포트를 잡지 않아 부트스트랩이 더 빠르다. 컨트롤러, 가드, 인터셉터 같은 HTTP 레이어 구성요소는 의미가 없다.

하이브리드 앱이라는 패턴도 있다. HTTP와 마이크로서비스 트랜스포트를 한 프로세스에 동시에 띄울 때 쓴다.

```typescript
const app = await NestFactory.create(AppModule);
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.TCP,
  options: { host: '0.0.0.0', port: 4000 },
});
await app.startAllMicroservices();  // 마이크로서비스 먼저
await app.listen(3000);              // 그다음 HTTP
```


## NestFactory.create() 내부 동작

`NestFactory.create(AppModule)` 호출 시 내부에서 일어나는 일을 순서대로 보면:

### 1단계: 모듈 스캐닝

AppModule의 `@Module()` 데코레이터에 선언된 `imports` 배열을 재귀적으로 탐색한다. imports 안에 있는 모듈이 또 다른 모듈을 import하고 있으면 그것도 따라 들어간다. 이 과정에서 모든 모듈의 메타데이터(`controllers`, `providers`, `imports`, `exports`)를 수집한다.

```
AppModule
  ├── AuthModule
  │     ├── JwtModule
  │     └── UserModule
  ├── OrderModule
  │     └── PaymentModule
  └── CommonModule
```

이런 구조가 있으면 AppModule부터 시작해서 모든 leaf 모듈까지 탐색한다. 같은 모듈이 여러 곳에서 import되면 한 번만 인스턴스를 만든다. NestJS 모듈은 기본적으로 싱글톤이다.

### 2단계: 의존성 그래프 빌드

스캔이 끝나면 모든 프로바이더 간의 의존성 관계를 그래프로 구성한다. `@Injectable()`로 선언된 클래스의 생성자 파라미터를 리플렉션으로 읽어서 어떤 프로바이더가 어떤 프로바이더를 필요로 하는지 파악한다.

```typescript
@Injectable()
export class OrderService {
  constructor(
    private readonly paymentService: PaymentService,  // PaymentService에 의존
    private readonly userService: UserService,          // UserService에 의존
  ) {}
}
```

이 시점에서 순환 의존성이 있으면 감지된다. 순환 의존성이 발견되면 에러가 나는데, `forwardRef()`로 해결할 수 있다. 다만 `forwardRef()`는 정말 필요한 경우에만 써야 한다. 순환 의존성이 생겼다는 건 보통 모듈 설계가 잘못된 신호다.

### 3단계: 프로바이더 인스턴스 생성

의존성 그래프를 기반으로 인스턴스를 생성한다. 의존하는 것이 없는(leaf) 프로바이더부터 만들고, 그 위로 올라간다.

```
JwtService (의존성 없음) → 먼저 생성
UserRepository (의존성 없음) → 생성
UserService (UserRepository 필요) → UserRepository 생성 후 생성
AuthService (JwtService, UserService 필요) → 둘 다 생성된 후 생성
```

여기서 주의할 점: **프로바이더의 생성자는 이 단계에서 실행된다.** 생성자에서 무거운 작업(DB 연결, 파일 읽기 등)을 하면 부트스트랩이 느려진다. 초기화 로직은 생성자가 아니라 `OnModuleInit` 훅에 넣어야 한다.

### 4단계: 라이프사이클 훅 실행

인스턴스가 모두 만들어진 후 라이프사이클 훅이 순서대로 실행된다. 이 부분은 아래에서 자세히 다룬다.

### 5단계: HTTP 서버 리스닝

`app.listen(3000)` 호출 시점에 Express/Fastify 서버가 실제로 포트를 열고 요청을 받기 시작한다. `listen()` 전에는 모든 초기화가 완료된 상태여야 한다.


## @Module 메타데이터 4종 — imports / providers / controllers / exports

`@Module()` 데코레이터에 넘기는 메타데이터 4종의 역할을 정리하면:

- **imports**: 다른 모듈에서 export한 프로바이더를 사용하겠다고 선언한다. 모듈 단위의 의존성 선언.
- **providers**: 이 모듈이 소유하는 프로바이더. DI 컨테이너에 등록되어 모듈 내부의 컨트롤러와 다른 프로바이더에서 주입할 수 있다.
- **controllers**: HTTP 요청을 받는 컨트롤러. 라우터에 등록된다.
- **exports**: 모듈의 프로바이더 중 외부 모듈에 노출할 것. exports에 명시하지 않은 프로바이더는 모듈 내부 전용이다.

```typescript
@Module({
  imports: [DatabaseModule, AuthModule],    // 외부 모듈의 export를 끌어옴
  controllers: [OrderController],            // HTTP 라우트
  providers: [
    OrderService,                            // 모듈 내부 비즈니스 로직
    OrderRepository,                         // 모듈 내부 데이터 액세스
    {                                         // 커스텀 프로바이더
      provide: 'ORDER_CONFIG',
      useValue: { maxItems: 100 },
    },
  ],
  exports: [OrderService],                   // 다른 모듈에서 OrderService 사용
})
export class OrderModule {}
```

### 캡슐화 동작

NestJS 모듈은 캡슐화되어 있다. 다른 모듈에서 `OrderService`를 사용하려면 두 조건을 모두 만족해야 한다.

1. `OrderModule`이 `OrderService`를 `exports`에 명시
2. 사용하는 쪽 모듈이 `OrderModule`을 `imports`에 추가

둘 중 하나라도 빠지면 다음과 같은 에러가 난다. NestJS 입문자가 가장 많이 만나는 에러다.

```
Nest can't resolve dependencies of XXX (?, YYY).
Please make sure that the argument YYY at index [0]
is available in the ZZZ context.
```

읽는 법:
- `XXX`: 의존성을 주입받지 못한 클래스
- `YYY`: 주입받으려는 프로바이더
- `ZZZ`: 현재 모듈 컨텍스트

해결 순서:

1. `YYY`가 등록된 모듈의 exports를 확인 → 없으면 추가
2. `ZZZ` 모듈의 imports에 `YYY`가 있는 모듈을 추가 → 없으면 추가
3. `YYY`가 동적 모듈이면 `forRoot()`/`register()` 호출 결과를 imports에 넣었는지 확인

### exports에 모듈 자체를 넣는 경우

`exports` 배열에는 프로바이더뿐 아니라 모듈도 넣을 수 있다. 모듈을 export하면 그 모듈이 export한 모든 프로바이더가 자동으로 노출된다(re-export).

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([User])],
  providers: [UserService],
  exports: [UserService, TypeOrmModule],  // TypeOrmModule도 re-export
})
export class UserModule {}
```

이렇게 하면 `UserModule`을 import한 쪽에서 `@InjectRepository(User)`를 바로 쓸 수 있다.

### imports에 들어갈 수 있는 형태

- 모듈 클래스: `UserModule`
- 동적 모듈 객체: `TypeOrmModule.forRoot({...})`
- forwardRef로 감싼 모듈: `forwardRef(() => OtherModule)`
- DynamicModule을 리턴하는 팩토리 호출 결과

문자열이나 프로바이더를 직접 imports에 넣으면 안 된다. 프로바이더는 `providers`에, 다른 모듈의 프로바이더는 그 모듈을 `imports`에 추가하는 식으로만 접근한다.

### controllers vs providers — 자주 헷갈리는 부분

5년차 코드 리뷰에서도 가끔 보이는 실수가 컨트롤러를 `providers`에 넣는 것이다. 동작은 한다 — DI 컨테이너에 등록되니까. 하지만 라우터에는 등록되지 않아 HTTP 요청을 처리하지 못한다. "엔드포인트가 404 나는데 클래스는 분명 있다"는 상황이 이 실수에서 자주 나온다.

반대로 `@Injectable()` 서비스를 `controllers`에 넣어도 NestJS가 라우트 메타데이터를 찾지 못해 무의미하게 등록된다. 컨트롤러는 `controllers`, 그 외 주입 가능한 클래스는 `providers`로 명확히 구분해야 한다.

### AppModule 구성 패턴

규모가 커지면 AppModule이 비대해진다. 실무에서는 보통 다음과 같은 레이어로 나눈다.

```typescript
@Module({
  imports: [
    // 1. 인프라/공통 모듈 (global)
    ConfigModule.forRoot({ isGlobal: true }),
    LoggerModule.forRoot(),

    // 2. 외부 시스템 연동
    DatabaseModule,
    CacheModule,
    QueueModule,

    // 3. 횡단 관심사
    AuthModule,
    HealthModule,

    // 4. 도메인/feature 모듈
    UserModule,
    OrderModule,
    PaymentModule,
  ],
  controllers: [AppController],  // 헬스체크 정도만 남김
  providers: [
    {
      provide: APP_FILTER,
      useClass: AllExceptionsFilter,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
```

도메인 모듈은 AppModule이 직접 알아야 하는 구체적인 서비스가 거의 없는 게 보통이다. AppModule은 "어떤 모듈을 조립하는지"만 책임지고, 비즈니스 로직은 도메인 모듈 안에 캡슐화한다. AppModule에 `OrderService`나 `UserRepository` 같은 게 직접 들어있으면 모듈 분리가 안 되어 있다는 신호다.


## 모듈 라이프사이클 훅

NestJS는 4개의 라이프사이클 훅을 제공한다. 실행 순서가 중요하다.

### 실행 순서

**시작 시:**

```
1. OnModuleInit      — 모듈의 프로바이더 인스턴스가 모두 생성된 직후
2. OnApplicationBootstrap — 모든 모듈의 OnModuleInit이 끝난 후
```

**종료 시:**

```
3. OnModuleDestroy           — 종료 시그널(SIGTERM 등) 수신 후
4. BeforeApplicationShutdown — 모든 OnModuleDestroy 완료 후, 서버 연결 종료 전
```

### OnModuleInit

해당 모듈 내의 모든 프로바이더가 인스턴스화된 직후 호출된다. 같은 모듈 안의 다른 프로바이더는 이미 생성되어 있으니 사용할 수 있다.

```typescript
@Injectable()
export class CacheService implements OnModuleInit {
  constructor(private readonly configService: ConfigService) {}

  async onModuleInit() {
    // ConfigService는 이미 생성되어 있으므로 사용 가능
    const redisUrl = this.configService.get('REDIS_URL');
    await this.connectToRedis(redisUrl);
  }
}
```

**호출 순서**: imports 배열에 선언된 모듈 순서대로 실행된다. 하위 모듈의 `OnModuleInit`이 먼저 실행되고, 상위 모듈이 나중에 실행된다.

```
AppModule imports: [DatabaseModule, AuthModule, OrderModule]

실행 순서:
DatabaseModule.onModuleInit()
AuthModule.onModuleInit()
OrderModule.onModuleInit()
AppModule.onModuleInit()
```

### OnApplicationBootstrap

모든 모듈의 `OnModuleInit`이 완료된 후 실행된다. 다른 모듈의 초기화 결과에 의존하는 작업을 여기에 넣는다.

```typescript
@Injectable()
export class HealthCheckService implements OnApplicationBootstrap {
  constructor(
    private readonly dbService: DatabaseService,
    private readonly cacheService: CacheService,
  ) {}

  async onApplicationBootstrap() {
    // 이 시점에서 DB, 캐시 모두 초기화가 끝난 상태
    const dbHealthy = await this.dbService.ping();
    const cacheHealthy = await this.cacheService.ping();

    if (!dbHealthy || !cacheHealthy) {
      throw new Error('필수 인프라 연결 실패, 서버를 시작할 수 없음');
    }
  }
}
```

### OnModuleDestroy

`app.close()`가 호출되거나 프로세스 종료 시그널을 받으면 실행된다. 리소스 정리 작업(DB 커넥션 풀 종료, 열린 파일 닫기 등)을 여기서 한다.

```typescript
@Injectable()
export class DatabaseService implements OnModuleDestroy {
  async onModuleDestroy() {
    await this.connectionPool.end();
    console.log('DB 커넥션 풀 종료');
  }
}
```

### BeforeApplicationShutdown

`OnModuleDestroy`가 모두 끝난 후 실행된다. 이 훅에는 시그널 문자열이 파라미터로 들어온다. HTTP 서버 연결이 아직 열려있는 시점이라 진행 중인 요청을 마무리할 수 있다.

```typescript
@Injectable()
export class ShutdownService implements BeforeApplicationShutdown {
  beforeApplicationShutdown(signal?: string) {
    console.log(`종료 시그널: ${signal}`);  // 'SIGTERM', 'SIGINT' 등
    // 이 시점에서 HTTP 연결은 아직 살아있음
    // 진행 중인 요청이 완료될 때까지 대기하는 로직을 넣을 수 있음
  }
}
```


### 실무에서 흔히 잘못 쓰는 사례

**1. OnModuleInit에서 다른 모듈의 초기화 결과에 의존하는 경우**

```typescript
// 문제 코드
@Injectable()
export class NotificationService implements OnModuleInit {
  constructor(private readonly templateService: TemplateService) {}

  async onModuleInit() {
    // TemplateService의 OnModuleInit에서 템플릿 파일을 로딩하는데,
    // NotificationModule이 TemplateModule보다 먼저 초기화되면
    // 여기서 아직 로딩 안 된 템플릿을 참조하게 됨
    this.defaultTemplate = this.templateService.getTemplate('welcome');
  }
}
```

이런 경우는 `OnApplicationBootstrap`에 넣어야 한다. `OnApplicationBootstrap`은 모든 모듈의 `OnModuleInit`이 끝난 후 실행되니까.

**2. 생성자에 비동기 초기화 로직을 넣는 경우**

```typescript
// 문제 코드 — 생성자는 async가 아니다
@Injectable()
export class CacheService {
  constructor() {
    // 이건 await가 안 되므로 fire-and-forget이 됨
    this.connect();  // Promise가 반환되지만 누구도 기다리지 않음
  }

  private async connect() {
    this.client = await createRedisClient();
  }
}
```

```typescript
// 올바른 코드
@Injectable()
export class CacheService implements OnModuleInit {
  async onModuleInit() {
    // 여기서는 async/await를 정상적으로 사용할 수 있고,
    // NestJS가 이 Promise가 resolve될 때까지 기다려줌
    this.client = await createRedisClient();
  }
}
```

**3. OnModuleDestroy에서 종료 순서를 고려하지 않는 경우**

```typescript
// 문제 상황: LogService가 DatabaseService보다 먼저 destroy됨
@Injectable()
export class LogService implements OnModuleDestroy {
  async onModuleDestroy() {
    await this.flushLogs();  // DB에 남은 로그를 flush
    // 근데 DatabaseService가 이미 destroy되어 커넥션이 끊겼으면?
  }
}
```

OnModuleDestroy의 실행 순서는 OnModuleInit의 역순이다. imports 배열 순서가 `[DatabaseModule, LogModule]`이면, destroy는 `LogModule → DatabaseModule` 순이다. 순서를 제어하려면 imports 배열 순서를 신경 써야 한다.


## 동적 모듈 패턴

정적 모듈은 `@Module()` 데코레이터에 모든 것이 고정되어 있다. 동적 모듈은 런타임에 설정을 받아서 모듈의 프로바이더 구성을 바꿀 수 있다.

### forRoot / forRootAsync

전역 설정이 필요한 모듈에 사용한다. 애플리케이션 전체에서 하나의 설정으로 공유해야 할 때 쓴다.

```typescript
@Module({})
export class DatabaseModule {
  static forRoot(options: DatabaseOptions): DynamicModule {
    return {
      module: DatabaseModule,
      global: true,  // 한 번 등록하면 어디서든 import 없이 사용 가능
      providers: [
        {
          provide: 'DATABASE_OPTIONS',
          useValue: options,
        },
        DatabaseService,
      ],
      exports: [DatabaseService],
    };
  }
}
```

내부적으로 일어나는 일: `forRoot()`는 단순히 `DynamicModule` 객체를 리턴하는 **정적 메서드**다. NestJS는 이 리턴값을 받아서 일반 모듈의 메타데이터처럼 처리한다. `module` 필드에 지정된 클래스가 모듈 토큰이 되고, `providers`와 `exports`가 그 모듈의 메타데이터에 합쳐진다.

```typescript
// 사용하는 쪽
@Module({
  imports: [
    DatabaseModule.forRoot({
      host: 'localhost',
      port: 5432,
      database: 'myapp',
    }),
  ],
})
export class AppModule {}
```

`forRootAsync`는 설정값을 비동기로 가져와야 할 때 사용한다. ConfigService에서 환경변수를 읽어야 하는 경우가 대표적이다.

```typescript
@Module({})
export class DatabaseModule {
  static forRootAsync(options: DatabaseAsyncOptions): DynamicModule {
    return {
      module: DatabaseModule,
      global: true,
      imports: options.imports || [],
      providers: [
        {
          provide: 'DATABASE_OPTIONS',
          useFactory: options.useFactory,
          inject: options.inject || [],
        },
        DatabaseService,
      ],
      exports: [DatabaseService],
    };
  }
}
```

```typescript
// 사용하는 쪽
@Module({
  imports: [
    DatabaseModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        host: configService.get('DB_HOST'),
        port: configService.get<number>('DB_PORT'),
        database: configService.get('DB_NAME'),
      }),
      inject: [ConfigService],
    }),
  ],
})
export class AppModule {}
```

`useFactory`에 전달된 함수는 의존성 주입 컨테이너가 `inject` 배열에 명시된 프로바이더들을 주입해서 호출한다. ConfigModule이 `imports`에 있어야 ConfigService를 주입받을 수 있다.

### register / registerAsync

`forRoot`와 구조는 같지만, 의미가 다르다. `forRoot`는 애플리케이션 전체에서 한 번 설정하는 용도고, `register`는 모듈별로 다른 설정을 적용할 때 사용한다.

```typescript
@Module({})
export class HttpClientModule {
  static register(options: HttpClientOptions): DynamicModule {
    return {
      module: HttpClientModule,
      providers: [
        {
          provide: 'HTTP_CLIENT_OPTIONS',
          useValue: options,
        },
        HttpClientService,
      ],
      exports: [HttpClientService],
    };
  }
}
```

```typescript
// 모듈마다 다른 설정으로 등록
@Module({
  imports: [
    HttpClientModule.register({
      baseUrl: 'https://api.payment.com',
      timeout: 5000,
    }),
  ],
})
export class PaymentModule {}

@Module({
  imports: [
    HttpClientModule.register({
      baseUrl: 'https://api.notification.com',
      timeout: 3000,
    }),
  ],
})
export class NotificationModule {}
```

여기서 주의해야 할 점: `register`로 여러 번 등록하면 각각 별도의 모듈 인스턴스가 생긴다. 하지만 `HttpClientService`가 같은 토큰을 사용하기 때문에, 다른 모듈에서 `HttpClientService`를 주입받으면 어떤 인스턴스가 들어올지 모호해진다. 이 경우 각 모듈이 자신의 `HttpClientService`만 사용하도록 exports 범위를 잘 관리해야 한다.

### 동적 모듈 내부 메타데이터 조합 과정

NestJS가 동적 모듈을 처리하는 과정을 조금 더 구체적으로 보면:

1. `imports` 배열에서 클래스가 아닌 객체(DynamicModule)를 만나면 동적 모듈로 처리한다.
2. `DynamicModule` 객체의 `module` 필드를 모듈 토큰으로 사용한다.
3. 해당 클래스에 `@Module()` 데코레이터가 있으면 그 메타데이터와 `DynamicModule` 객체의 메타데이터를 **병합**한다.
4. `providers`, `controllers`, `imports`, `exports`가 각각 합쳐진다.

```typescript
// @Module 데코레이터의 메타데이터
@Module({
  providers: [InternalHelper],
})
export class SomeModule {
  static forRoot(): DynamicModule {
    return {
      module: SomeModule,
      providers: [SomeService],  // 이건 InternalHelper와 합쳐짐
      exports: [SomeService],
    };
  }
}

// 결과적으로 SomeModule의 providers = [InternalHelper, SomeService]
```

이 병합 동작을 모르면 "분명 forRoot에서 providers를 지정했는데 왜 @Module의 providers도 같이 등록되지?"같은 혼란이 생긴다. 반대로, `@Module({})`을 비워두고 동적 메서드에서만 providers를 지정하면 깔끔하게 관리할 수 있다.


## ModuleRef — 런타임에 프로바이더 꺼내기

`ModuleRef`는 DI 컨테이너에서 런타임에 프로바이더 인스턴스를 직접 조회하는 객체다. 생성자 주입만으로 해결이 안 되는 상황에서 사용한다.

### 기본 사용법

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { ModuleRef } from '@nestjs/core';

@Injectable()
export class TaskRunner implements OnModuleInit {
  private reportService: ReportService;

  constructor(private readonly moduleRef: ModuleRef) {}

  onModuleInit() {
    // 현재 모듈 컨텍스트에서 프로바이더를 조회
    this.reportService = this.moduleRef.get(ReportService, { strict: false });
  }
}
```

`get()` 메서드의 두 번째 파라미터 `{ strict: false }`를 주면 현재 모듈뿐 아니라 전역 컨테이너에서도 검색한다. 기본값은 `strict: true`로, 현재 모듈 내에서만 찾는다. 다른 모듈의 프로바이더를 조회하려면 `strict: false`가 필요한데, 이건 해당 프로바이더가 export된 상태여야 동작한다.

### resolve() — REQUEST 스코프 프로바이더 조회

`get()`은 싱글톤 프로바이더에만 사용한다. `Scope.REQUEST`나 `Scope.TRANSIENT`로 등록된 프로바이더는 `resolve()`를 써야 한다.

```typescript
@Injectable()
export class AuditService {
  constructor(private readonly moduleRef: ModuleRef) {}

  async createAuditContext() {
    // resolve()는 호출할 때마다 새 인스턴스를 만든다 (transient)
    const logger = await this.moduleRef.resolve(TransientLogger);
    return logger;
  }

  async createSharedContext() {
    // contextId를 지정하면 같은 contextId 내에서 인스턴스를 공유한다
    const contextId = ContextIdFactory.create();
    const a = await this.moduleRef.resolve(TransientLogger, contextId);
    const b = await this.moduleRef.resolve(TransientLogger, contextId);
    // a === b → true (같은 contextId이므로)
  }
}
```

`resolve()`는 항상 Promise를 반환한다. `get()`과 다르게 동기가 아니니까 생성자에서 호출하면 안 되고, `onModuleInit`이나 비즈니스 로직 안에서 써야 한다.

### create() — DI 컨테이너 밖에서 인스턴스 생성

등록되지 않은 클래스의 인스턴스를 DI 컨테이너의 의존성 주입을 적용해서 만들 수 있다.

```typescript
@Injectable()
export class HandlerFactory {
  constructor(private readonly moduleRef: ModuleRef) {}

  async createHandler(type: string) {
    // EventHandler가 providers에 등록되어 있지 않아도,
    // 생성자에 주입이 필요한 의존성은 컨테이너에서 가져와서 넣어준다
    const handler = await this.moduleRef.create(EventHandler);
    return handler;
  }
}
```

`create()`로 만든 인스턴스는 NestJS 모듈 시스템이 관리하지 않는다. 라이프사이클 훅(`OnModuleInit` 등)이 호출되지 않고, GC가 수거하기 전까지 메모리에 남는다. 동적으로 핸들러를 생성하는 패턴에서 유용하지만, 남용하면 메모리 누수 원인이 된다.

### 실무에서 ModuleRef가 필요한 경우

대부분의 상황에서는 생성자 주입으로 충분하다. ModuleRef가 필요한 상황은 제한적이다:

- **런타임에 타입이 결정되는 경우**: 이벤트 타입에 따라 다른 핸들러를 선택해야 할 때
- **순환 의존성 회피**: `forwardRef()` 대신 런타임에 필요한 시점에 조회
- **REQUEST 스코프 프로바이더를 싱글톤에서 사용해야 할 때**: 싱글톤 서비스가 요청별 컨텍스트에 접근해야 하는 경우

```typescript
// 이벤트 타입에 따라 핸들러를 동적으로 선택하는 예시
@Injectable()
export class EventDispatcher {
  private handlerMap: Map<string, Type<EventHandler>>;

  constructor(private readonly moduleRef: ModuleRef) {
    this.handlerMap = new Map([
      ['order.created', OrderCreatedHandler],
      ['order.cancelled', OrderCancelledHandler],
      ['payment.completed', PaymentCompletedHandler],
    ]);
  }

  async dispatch(event: DomainEvent) {
    const handlerType = this.handlerMap.get(event.type);
    if (!handlerType) {
      throw new Error(`핸들러 없음: ${event.type}`);
    }
    const handler = this.moduleRef.get(handlerType, { strict: false });
    await handler.handle(event);
  }
}
```


## LazyModuleLoader — 모듈 지연 로딩

`LazyModuleLoader`는 부트스트랩 시점에 모듈을 로딩하지 않고, 실제로 필요해지는 시점에 로딩하는 기능이다. 콜드 스타트 시간이 중요한 서버리스 환경이나, 특정 조건에서만 사용하는 무거운 모듈이 있을 때 유용하다.

### 기본 사용법

```typescript
import { Injectable } from '@nestjs/common';
import { LazyModuleLoader } from '@nestjs/core';

@Injectable()
export class ReportController {
  constructor(private readonly lazyModuleLoader: LazyModuleLoader) {}

  async generateReport() {
    // ReportModule을 이 시점에 처음 로딩한다
    const moduleRef = await this.lazyModuleLoader.load(() => ReportModule);

    // 로딩된 모듈에서 서비스를 꺼낸다
    const reportService = moduleRef.get(ReportService);
    return reportService.generate();
  }
}
```

`load()`는 팩토리 함수를 받는다. 화살표 함수로 감싸야 하며, 직접 클래스를 넘기면 안 된다. 한 번 로딩된 모듈은 캐시되어 두 번째 `load()` 호출부터는 즉시 반환된다.

### 지연 로딩 시 주의사항

지연 로딩된 모듈은 몇 가지 제약이 있다:

**컨트롤러가 등록되지 않는다.** 지연 로딩된 모듈에 선언된 컨트롤러는 라우트로 등록되지 않는다. HTTP 라우팅은 부트스트랩 시점에 결정되기 때문이다. 지연 로딩은 프로바이더 위주의 백그라운드 작업에 적합하다.

**`global: true` 모듈은 지연 로딩할 수 없다.** 글로벌 모듈은 부트스트랩 시점에 이미 전역 컨테이너에 등록되어야 하기 때문이다.

**라이프사이클 훅은 정상 동작한다.** `OnModuleInit`과 `OnApplicationBootstrap`이 `load()` 시점에 실행된다. 단, `OnModuleDestroy`는 애플리케이션 종료 시 호출된다.

```typescript
// 서버리스에서 콜드 스타트를 줄이는 패턴
@Injectable()
export class PdfService {
  constructor(private readonly lazyModuleLoader: LazyModuleLoader) {}

  async generatePdf(data: any) {
    // PDF 생성 라이브러리가 무거워서 (puppeteer 등)
    // 모든 요청에서 필요하지 않으면 지연 로딩한다
    const { PdfModule } = await import('./pdf/pdf.module');
    const moduleRef = await this.lazyModuleLoader.load(() => PdfModule);
    const generator = moduleRef.get(PdfGenerator);
    return generator.create(data);
  }
}
```

동적 import(`import()`)와 `LazyModuleLoader.load()`를 함께 쓰면 모듈의 JavaScript 번들 자체도 필요할 때만 로딩할 수 있다.


## ConfigurableModuleBuilder — 동적 모듈 보일러플레이트 제거

NestJS 9부터 추가된 `ConfigurableModuleBuilder`는 `forRoot`, `forRootAsync`, 옵션 인터페이스 등의 반복 코드를 자동 생성한다. 동적 모듈을 직접 구현하면 매번 비슷한 코드를 짜야 하는데, 이걸 줄여준다.

### 기본 사용법

```typescript
// notification.module-definition.ts
import { ConfigurableModuleBuilder } from '@nestjs/common';

export interface NotificationModuleOptions {
  apiKey: string;
  sender: string;
  retryCount?: number;
}

export const {
  ConfigurableModuleClass,
  MODULE_OPTIONS_TOKEN,
} = new ConfigurableModuleBuilder<NotificationModuleOptions>()
  .build();
```

`build()`를 호출하면 두 가지가 생성된다:
- `ConfigurableModuleClass`: `register()`와 `registerAsync()` 정적 메서드가 포함된 클래스
- `MODULE_OPTIONS_TOKEN`: 옵션을 주입받을 때 사용하는 토큰

```typescript
// notification.module.ts
import { Module } from '@nestjs/common';
import { ConfigurableModuleClass } from './notification.module-definition';
import { NotificationService } from './notification.service';

@Module({
  providers: [NotificationService],
  exports: [NotificationService],
})
export class NotificationModule extends ConfigurableModuleClass {}
```

모듈 클래스가 `ConfigurableModuleClass`를 extends하면 `register()`와 `registerAsync()`가 자동으로 붙는다.

```typescript
// notification.service.ts
import { Inject, Injectable } from '@nestjs/common';
import {
  MODULE_OPTIONS_TOKEN,
  NotificationModuleOptions,
} from './notification.module-definition';

@Injectable()
export class NotificationService {
  constructor(
    @Inject(MODULE_OPTIONS_TOKEN)
    private readonly options: NotificationModuleOptions,
  ) {}

  async send(to: string, message: string) {
    // this.options.apiKey, this.options.sender 사용
  }
}
```

### 메서드 이름 변경

기본으로 `register`/`registerAsync`가 생성되는데, `forRoot`/`forRootAsync`로 바꾸려면:

```typescript
export const {
  ConfigurableModuleClass,
  MODULE_OPTIONS_TOKEN,
} = new ConfigurableModuleBuilder<NotificationModuleOptions>()
  .setClassMethodName('forRoot')
  .build();
```

이렇게 하면 `NotificationModule.forRoot()`과 `NotificationModule.forRootAsync()`가 생성된다.

### 글로벌 모듈로 만들기

```typescript
export const {
  ConfigurableModuleClass,
  MODULE_OPTIONS_TOKEN,
} = new ConfigurableModuleBuilder<NotificationModuleOptions>()
  .setClassMethodName('forRoot')
  .setExtras({ isGlobal: false }, (definition, extras) => ({
    ...definition,
    global: extras.isGlobal,
  }))
  .build();
```

`setExtras`를 사용하면 옵션 외에 추가 파라미터를 받을 수 있다. 사용하는 쪽에서 `isGlobal: true`를 넘기면 글로벌 모듈로 동작한다.

```typescript
@Module({
  imports: [
    NotificationModule.forRoot({
      apiKey: 'xxx',
      sender: 'noreply@example.com',
      isGlobal: true,  // setExtras에서 정의한 추가 옵션
    }),
  ],
})
export class AppModule {}
```

### 직접 구현 vs ConfigurableModuleBuilder

직접 구현하는 게 나은 경우도 있다. `ConfigurableModuleBuilder`는 `register`/`registerAsync` 패턴을 따르는 단순한 동적 모듈에 적합하다. `forRoot`과 `forFeature`를 동시에 제공하거나, 옵션에 따라 providers가 크게 달라지는 복잡한 모듈에서는 직접 구현하는 게 코드를 이해하기 쉽다.


## 순환 참조와 forwardRef

모듈 A가 모듈 B를 import하고, 모듈 B가 모듈 A를 다시 import하면 순환 참조가 생긴다. 부트스트랩 단계에서 NestJS는 이 사이클을 감지하지 못해 다음과 같은 에러를 던진다.

```
A circular dependency between modules has been detected.
Please, make sure that each side of a bidirectional relationship
are decorated with "forwardRef()". Note that circular relationships
should be avoided when possible.
```

같은 문제는 프로바이더 간에도 생긴다. `ServiceA`가 `ServiceB`를 주입받고, `ServiceB`도 `ServiceA`를 주입받으면 의존성 그래프를 만들 때 무한 사이클이 발생한다.

### 모듈 간 순환 참조

```typescript
// auth.module.ts
@Module({
  imports: [UserModule],
  providers: [AuthService],
  exports: [AuthService],
})
export class AuthModule {}

// user.module.ts
@Module({
  imports: [AuthModule],   // 양쪽이 서로 import → 순환
  providers: [UserService],
  exports: [UserService],
})
export class UserModule {}
```

해결책은 한쪽 또는 양쪽을 `forwardRef()`로 감싸는 것이다.

```typescript
// auth.module.ts
@Module({
  imports: [forwardRef(() => UserModule)],
  providers: [AuthService],
  exports: [AuthService],
})
export class AuthModule {}

// user.module.ts
@Module({
  imports: [forwardRef(() => AuthModule)],
  providers: [UserService],
  exports: [UserService],
})
export class UserModule {}
```

`forwardRef()`는 모듈 클래스를 즉시 참조하지 않고 팩토리 함수로 감싼다. NestJS는 부트스트랩 시점에 한쪽 모듈을 먼저 등록하고, 다른 쪽이 등록된 후에 참조를 해결한다.

### 프로바이더 간 순환 참조

서비스끼리 양방향으로 주입받는 경우는 `@Inject(forwardRef(() => ...))`로 감싼다.

```typescript
@Injectable()
export class AuthService {
  constructor(
    @Inject(forwardRef(() => UserService))
    private readonly userService: UserService,
  ) {}
}

@Injectable()
export class UserService {
  constructor(
    @Inject(forwardRef(() => AuthService))
    private readonly authService: AuthService,
  ) {}
}
```

생성자 파라미터에 타입만 적어두면 TypeScript 리플렉션이 클래스 메타데이터를 읽어 자동으로 토큰을 결정한다. 순환 참조 상황에서는 한쪽 클래스가 아직 로드되지 않은 시점에 리플렉션이 호출되어 `undefined`가 토큰으로 들어간다. 그래서 `@Inject(forwardRef(...))`로 명시적으로 늦은 참조를 만들어줘야 한다.

### forwardRef의 비용과 함정

`forwardRef()`는 동작은 하지만, 두 가지를 알고 써야 한다.

**1. 진짜 문제는 설계에 있다는 신호다.** 두 서비스가 서로를 호출한다는 건 보통 책임 분리가 잘못된 경우가 많다. 예를 들어 `AuthService`가 `UserService.findById()`를 호출하고, `UserService`가 `AuthService.validateToken()`을 호출하는 구조라면 토큰 검증과 사용자 조회를 합친 상위 서비스를 만들거나, 공통 의존성을 별도 모듈로 분리하는 게 정상이다.

흔한 해결 패턴 세 가지:

```
A → B, B → A
  ↓ 리팩터링
  
(a) A, B가 공통으로 의존하는 C를 만들어 A → C, B → C
(b) A, B 둘 다의 책임을 가진 상위 서비스 D를 만들어 D → A, D → B
(c) 한쪽이 이벤트를 발행하고 다른 쪽이 구독하게 → A → EventBus ← B
```

**2. 라이프사이클 훅에서 늦게 주입되는 인스턴스를 사용할 때 주의해야 한다.** `forwardRef`로 주입한 의존성은 생성자 실행 시점에 완전히 초기화되지 않은 상태일 수 있다. 생성자에서 그 의존성의 메서드를 호출하면 런타임 에러가 난다. `OnModuleInit` 이후에 접근하는 게 안전하다.

```typescript
// 문제 코드
@Injectable()
export class AuthService {
  constructor(
    @Inject(forwardRef(() => UserService))
    private readonly userService: UserService,
  ) {
    this.userService.preload();  // userService가 아직 준비 안 됐을 수 있음
  }
}

// 안전한 코드
@Injectable()
export class AuthService implements OnModuleInit {
  constructor(
    @Inject(forwardRef(() => UserService))
    private readonly userService: UserService,
  ) {}

  onModuleInit() {
    this.userService.preload();  // 이 시점에는 준비된 상태
  }
}
```

### ModuleRef로 forwardRef 회피

생성자 주입을 포기하고 `ModuleRef`로 런타임에 조회하는 방식으로도 순환 참조를 풀 수 있다.

```typescript
@Injectable()
export class AuthService implements OnModuleInit {
  private userService: UserService;

  constructor(private readonly moduleRef: ModuleRef) {}

  onModuleInit() {
    this.userService = this.moduleRef.get(UserService, { strict: false });
  }
}
```

이 방식은 컴파일 타임에 의존성이 보이지 않아 코드 추적이 어려워진다. 일회성 우회로만 쓰고, 가능하면 모듈 구조를 다시 설계하는 게 낫다.


## @Global() — 글로벌 모듈

`@Global()` 데코레이터를 모듈에 붙이면, 그 모듈이 export한 프로바이더가 모든 모듈에서 import 없이 사용 가능해진다. `ConfigModule.forRoot({ isGlobal: true })` 같은 옵션이 내부적으로 이걸 사용한다.

```typescript
@Global()
@Module({
  providers: [LoggerService],
  exports: [LoggerService],
})
export class LoggerModule {}

// AppModule에 한 번만 import
@Module({
  imports: [LoggerModule],
})
export class AppModule {}

// 어떤 모듈에서든 import 없이 LoggerService를 주입받을 수 있음
@Module({
  providers: [OrderService],
})
export class OrderModule {}

@Injectable()
export class OrderService {
  constructor(private readonly logger: LoggerService) {}  // 동작함
}
```

### 글로벌 모듈은 한 번만 import한다

글로벌 모듈도 결국 모듈이라 어딘가에서 한 번은 import해야 한다. 보통 AppModule에 import한다. 두 번 이상 import하면 인스턴스가 두 개 만들어지지 않고 첫 번째만 사용된다 — NestJS가 같은 모듈 토큰의 중복을 자동으로 제거한다.

### 글로벌 모듈을 써야 할 때

다음 조건을 모두 만족할 때만 글로벌로 만든다.

- 거의 모든 모듈에서 사용한다 (로거, ConfigService 등)
- 인스턴스를 하나로 공유해야 한다
- 모듈 간 결합도가 글로벌 노출로 인해 더 나빠지지 않는다

`ConfigModule`, `LoggerModule`, `CacheModule` 같은 인프라 모듈이 전형적인 사용 사례다. 도메인 모듈(`UserModule`, `OrderModule`)을 글로벌로 만드는 건 거의 항상 잘못된 선택이다. 도메인 의존성이 어디서 어떻게 연결되는지 명시적으로 보이지 않게 되어, 모듈 분리·테스트·리팩터링이 모두 어려워진다.

### 글로벌 모듈의 함정

**1. 토큰 충돌이 조용히 일어난다.** 글로벌 모듈에서 export한 `LoggerService`와 로컬 모듈에서 등록한 `LoggerService`가 같은 토큰을 쓰면, 로컬 등록이 글로벌을 덮는다. 에러나 경고 없이 동작이 달라진다.

```typescript
@Global()
@Module({
  providers: [
    { provide: LoggerService, useFactory: () => new ProdLogger() },
  ],
  exports: [LoggerService],
})
export class GlobalLoggerModule {}

@Module({
  providers: [LoggerService],  // 기본 클래스로 다시 등록 → 글로벌 무시됨
})
export class SomeFeatureModule {}
```

`SomeFeatureModule` 내부에서는 `ProdLogger`가 아니라 기본 `LoggerService`가 주입된다. 모듈 작성자가 의도하지 않은 동작이다.

**2. 테스트에서 격리가 어려워진다.** 글로벌 모듈은 import 선언 없이 의존성이 연결되니까, 테스트 모듈을 만들 때 어떤 글로벌 프로바이더가 영향을 주는지 한눈에 보이지 않는다. 결국 테스트에서 글로벌 모듈을 통째로 import하거나 mock을 따로 등록하게 된다.

**3. 모듈 그래프 시각화가 의미를 잃는다.** NestJS Devtools나 의존성 분석 도구가 그리는 모듈 그래프에서, 글로벌 모듈은 모든 모듈과 보이지 않는 선으로 연결된 상태가 된다. 그래프를 봐도 실제 의존 관계를 파악하기 어렵다.

### 동적 글로벌 모듈

`forRoot()`가 반환하는 `DynamicModule`에 `global: true`를 넣으면 동적으로도 글로벌로 만들 수 있다.

```typescript
@Module({})
export class CoreModule {
  static forRoot(options: CoreOptions): DynamicModule {
    return {
      module: CoreModule,
      global: true,             // 동적 글로벌
      providers: [
        { provide: 'CORE_OPTIONS', useValue: options },
        CoreService,
      ],
      exports: [CoreService],
    };
  }
}
```

이때 `@Global()` 데코레이터는 클래스에 붙이지 않는다. `DynamicModule`의 `global: true`로 충분하다. 두 가지를 모두 쓰면 결과는 같지만 의도가 흐려지므로 한쪽으로 통일한다.

### "import 쓰기 귀찮아서" 글로벌은 금지

5년차 코드 리뷰에서 가장 흔히 잡는 안티패턴이다. 매 모듈마다 `imports: [LoggerModule]`을 추가하기 귀찮다는 이유로 `@Global()`을 붙이면, 처음엔 편하지만 시간이 지나면서 토큰 충돌, 의존성 불투명, 테스트 격리 실패로 돌아온다. 명시적인 의존성 선언이 결국 더 적은 비용으로 끝난다.


## 모듈 재내보내기 (Re-exporting)

한 모듈이 import한 모듈을 다시 export하면, 그 모듈을 import하는 쪽에서 원본 모듈을 따로 import하지 않아도 된다.

### 기본 패턴

```typescript
@Module({
  imports: [DatabaseModule, CacheModule],
  exports: [DatabaseModule, CacheModule],  // import한 모듈을 다시 export
})
export class CoreModule {}
```

```typescript
// AppModule에서 CoreModule만 import하면
// DatabaseModule과 CacheModule의 exported 프로바이더를 모두 사용할 수 있다
@Module({
  imports: [CoreModule],
})
export class AppModule {}
```

내부 동작을 보면, `CoreModule`이 `DatabaseModule`을 re-export하면 NestJS는 `DatabaseModule`의 exports 배열에 명시된 프로바이더들을 `CoreModule`을 import하는 모든 모듈에 노출한다. `DatabaseModule` 내부에서 export하지 않은 프로바이더는 여전히 접근할 수 없다.

### 동적 모듈 재내보내기

동적 모듈도 re-export할 수 있다. 단, `forRoot()`를 호출한 결과를 re-export해야 한다.

```typescript
@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: 'localhost',
      // ...
    }),
  ],
  exports: [TypeOrmModule],  // TypeOrmModule 클래스를 re-export
})
export class DatabaseModule {}
```

여기서 `exports`에 `TypeOrmModule`(클래스)을 넣는다. `TypeOrmModule.forRoot()`의 반환값(DynamicModule 객체)이 아니라 클래스 자체를 넣는다. NestJS는 모듈 토큰(클래스)을 기준으로 매칭하기 때문이다.

### 재내보내기를 쓰는 이유

- **관련 모듈을 하나로 묶어서 import 줄이기**: 여러 인프라 모듈을 `CoreModule` 하나로 묶으면 각 feature 모듈에서 import 목록이 짧아진다.
- **간접 의존성 관리**: 내부 구현 모듈을 직접 노출하지 않고, 래핑 모듈을 통해서만 접근하게 한다. 나중에 내부 모듈을 교체할 때 래핑 모듈만 수정하면 된다.

주의할 점: re-export을 남발하면 모듈 의존성이 불투명해진다. `CoreModule`이 뭘 re-export하는지 알려면 항상 `CoreModule` 코드를 열어봐야 한다. 명확한 목적 없이 "편하니까" re-export하는 건 피해야 한다.


## forFeature 패턴

`forRoot`이 전역 설정을 담당한다면, `forFeature`는 각 feature 모듈에서 필요한 부분만 등록하는 패턴이다. TypeORM의 `TypeOrmModule.forFeature([User, Order])`가 대표적인 예시다.

### forFeature의 동작 원리

`forRoot`에서 전역 설정(DB 연결 정보 등)을 등록하고, `forFeature`에서는 그 설정을 기반으로 특정 리소스(엔티티, 리포지토리 등)만 모듈 스코프에 등록한다.

```typescript
@Module({})
export class EventStoreModule {
  // 전역 설정: 이벤트 스토어 연결 정보
  static forRoot(options: EventStoreOptions): DynamicModule {
    return {
      module: EventStoreModule,
      global: true,
      providers: [
        {
          provide: 'EVENT_STORE_OPTIONS',
          useValue: options,
        },
        EventStoreConnection,
      ],
      exports: [EventStoreConnection],
    };
  }

  // 모듈별 설정: 해당 모듈에서 사용할 이벤트 스트림 등록
  static forFeature(streams: string[]): DynamicModule {
    const providers = streams.map(stream => ({
      provide: `EVENT_STREAM_${stream}`,
      useFactory: (connection: EventStoreConnection) => {
        return connection.getStream(stream);
      },
      inject: [EventStoreConnection],
    }));

    return {
      module: EventStoreModule,
      providers,
      exports: providers.map(p => p.provide),
    };
  }
}
```

```typescript
// AppModule에서 연결 설정
@Module({
  imports: [
    EventStoreModule.forRoot({
      host: 'localhost',
      port: 1113,
    }),
    OrderModule,
    PaymentModule,
  ],
})
export class AppModule {}

// OrderModule에서 필요한 스트림만 등록
@Module({
  imports: [
    EventStoreModule.forFeature(['order-created', 'order-cancelled']),
  ],
})
export class OrderModule {}

// PaymentModule에서 다른 스트림 등록
@Module({
  imports: [
    EventStoreModule.forFeature(['payment-completed', 'payment-failed']),
  ],
})
export class PaymentModule {}
```

### forFeature 구현 시 핵심 포인트

**forRoot은 global, forFeature는 non-global이다.** `forRoot`이 `global: true`로 등록되어 있어야 `forFeature`에서 `EventStoreConnection`을 `inject`로 가져올 수 있다. `forFeature`가 반환하는 `DynamicModule`에는 `global: true`를 넣으면 안 된다. forFeature의 프로바이더는 해당 모듈 스코프에만 존재해야 한다.

**같은 module 클래스를 사용하면 모듈 토큰이 겹친다.** 위 예시에서 `OrderModule`과 `PaymentModule` 모두 `EventStoreModule.forFeature()`를 호출하는데, 반환되는 `DynamicModule`의 `module` 필드가 둘 다 `EventStoreModule`이다. NestJS는 같은 토큰의 모듈을 한 번만 등록하기 때문에, 하나가 무시될 수 있다.

이 문제를 해결하는 방법:

```typescript
static forFeature(streams: string[]): DynamicModule {
  const providers = streams.map(stream => ({
    provide: `EVENT_STREAM_${stream}`,
    useFactory: (connection: EventStoreConnection) => {
      return connection.getStream(stream);
    },
    inject: [EventStoreConnection],
  }));

  return {
    module: EventStoreModule,
    providers,
    exports: providers.map(p => p.provide),
  };
}
```

실제로 NestJS는 동적 모듈의 경우 `module` 클래스 + 전달된 메타데이터 조합으로 중복을 판단한다. providers 배열이 다르면 별개의 모듈 인스턴스로 취급된다. TypeOrmModule이 여러 곳에서 `forFeature()`를 호출해도 동작하는 이유가 이것이다. 다만 직접 구현할 때 이 동작에 의존하지 말고, 프로바이더 토큰이 겹치지 않도록 설계하는 게 안전하다.

### forFeature에서 동적 프로바이더 토큰 패턴

TypeORM의 `getRepositoryToken()` 같은 함수를 만들면, forFeature로 등록한 프로바이더를 다른 서비스에서 주입받을 때 편하다.

```typescript
// 토큰 생성 함수
export function getEventStreamToken(stream: string): string {
  return `EVENT_STREAM_${stream}`;
}

// 서비스에서 주입
@Injectable()
export class OrderService {
  constructor(
    @Inject(getEventStreamToken('order-created'))
    private readonly orderCreatedStream: EventStream,
  ) {}
}
```

문자열 토큰을 직접 쓰면 오타 위험이 있으니, 토큰 생성 함수를 한 곳에서 관리한다.


## 모듈 단위 테스트

NestJS에서 모듈 단위로 격리 테스트를 하려면 `Test.createTestingModule()`을 사용한다. 실제 모듈 구조를 그대로 가져오되, 외부 의존성만 가짜로 교체하는 방식이다.

### 기본 구조

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import { OrderService } from './order.service';
import { PaymentService } from './payment.service';

describe('OrderService', () => {
  let service: OrderService;
  let paymentService: PaymentService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        OrderService,
        {
          provide: PaymentService,
          useValue: {
            charge: jest.fn().mockResolvedValue({ success: true }),
            refund: jest.fn().mockResolvedValue({ success: true }),
          },
        },
      ],
    }).compile();

    service = module.get<OrderService>(OrderService);
    paymentService = module.get<PaymentService>(PaymentService);
  });

  it('주문 생성 시 결제를 호출한다', async () => {
    await service.createOrder({ productId: 1, amount: 10000 });
    expect(paymentService.charge).toHaveBeenCalledWith(10000);
  });
});
```

`createTestingModule()`은 `@Module()` 데코레이터에 넘기는 것과 같은 형태의 메타데이터를 받는다. 테스트에서 필요한 프로바이더만 등록하고, 외부 의존성은 mock 객체로 대체한다.

### overrideProvider 패턴

실제 모듈을 통째로 가져와서 특정 프로바이더만 교체하는 방법이 있다. 모듈에 프로바이더가 많을 때 mock 객체를 일일이 만드는 것보다 낫다.

```typescript
describe('OrderModule 통합 테스트', () => {
  let module: TestingModule;

  beforeEach(async () => {
    module = await Test.createTestingModule({
      imports: [OrderModule],
    })
      .overrideProvider(PaymentService)
      .useValue({
        charge: jest.fn().mockResolvedValue({ success: true }),
      })
      .overrideProvider(NotificationService)
      .useValue({
        send: jest.fn(),
      })
      .compile();
  });
});
```

`overrideProvider()`는 체이닝으로 여러 개를 연달아 교체할 수 있다. `compile()` 전에 호출해야 한다.

교체 방식은 세 가지가 있다:

```typescript
// 1. useValue — 객체를 직접 넘긴다
.overrideProvider(PaymentService)
.useValue({ charge: jest.fn() })

// 2. useClass — 다른 클래스로 교체한다
.overrideProvider(PaymentService)
.useClass(MockPaymentService)

// 3. useFactory — 팩토리 함수로 생성한다
.overrideProvider(PaymentService)
.useFactory({
  factory: (configService: ConfigService) => {
    return new StubPaymentService(configService.get('TEST_API_KEY'));
  },
  inject: [ConfigService],
})
```

### 테스트에서 자주 빠지는 실수

**import한 모듈의 의존성까지 따라 들어오는 문제**

```typescript
// OrderModule이 PaymentModule을 import하고,
// PaymentModule이 HttpModule을 import한다면
const module = await Test.createTestingModule({
  imports: [OrderModule],
}).compile();
// → HttpModule의 실제 HTTP 클라이언트까지 초기화된다
```

이런 경우 `overrideProvider`로 HttpService를 교체하거나, OrderModule 대신 필요한 프로바이더만 직접 등록하는 게 낫다. 모듈을 통째로 import하면 테스트 실행 시간이 느려지고, 외부 서비스 연결 실패로 테스트가 깨지는 경우가 생긴다.

**커스텀 프로바이더 토큰 교체 시 문자열 토큰 누락**

```typescript
// 모듈에서 문자열 토큰으로 등록한 프로바이더
{
  provide: 'PAYMENT_CLIENT',
  useFactory: () => new PaymentClient(),
}

// 테스트에서 교체할 때 클래스가 아니라 같은 문자열 토큰을 써야 한다
.overrideProvider('PAYMENT_CLIENT')
.useValue(mockClient)
```

클래스 토큰은 타입 추론이 되니까 실수할 일이 적은데, 문자열 토큰은 오타가 나면 교체가 안 되고 원본 프로바이더가 그대로 실행된다. 에러도 안 나서 디버깅이 어렵다.


## 멀티 프로바이더

같은 토큰에 여러 구현체를 등록해야 하는 경우가 있다. 이벤트 핸들러, 검증 파이프, 플러그인 같은 패턴에서 사용한다.

### 기본 구현

NestJS에서 같은 토큰에 여러 프로바이더를 등록하면 마지막에 등록된 것이 이긴다. 배열로 여러 구현체를 받으려면 별도로 설계해야 한다.

```typescript
// 각 검증기를 개별 토큰으로 등록하고, 배열 토큰으로 묶는 패턴
@Module({
  providers: [
    EmailValidator,
    PhoneValidator,
    AddressValidator,
    {
      provide: 'VALIDATORS',
      useFactory: (...validators: Validator[]) => validators,
      inject: [EmailValidator, PhoneValidator, AddressValidator],
    },
  ],
  exports: ['VALIDATORS'],
})
export class ValidationModule {}
```

```typescript
@Injectable()
export class UserService {
  constructor(
    @Inject('VALIDATORS')
    private readonly validators: Validator[],
  ) {}

  async validate(input: CreateUserDto) {
    for (const validator of this.validators) {
      const result = validator.validate(input);
      if (!result.valid) {
        throw new BadRequestException(result.message);
      }
    }
  }
}
```

### 동적으로 멀티 프로바이더 수집하기

검증기가 추가될 때마다 `useFactory`의 `inject` 배열을 수정하는 건 번거롭다. `DiscoveryService`를 사용하면 데코레이터로 표시된 프로바이더를 자동으로 수집할 수 있다.

```typescript
import { DiscoveryService } from '@nestjs/core';
import { SetMetadata } from '@nestjs/common';

// 커스텀 데코레이터
export const VALIDATOR_KEY = 'VALIDATOR';
export const IsValidator = () => SetMetadata(VALIDATOR_KEY, true);
```

```typescript
@IsValidator()
@Injectable()
export class EmailValidator implements Validator {
  validate(input: any) { /* ... */ }
}

@IsValidator()
@Injectable()
export class PhoneValidator implements Validator {
  validate(input: any) { /* ... */ }
}
```

```typescript
@Injectable()
export class ValidationService implements OnModuleInit {
  private validators: Validator[] = [];

  constructor(private readonly discoveryService: DiscoveryService) {}

  onModuleInit() {
    const providers = this.discoveryService.getProviders();
    this.validators = providers
      .filter(wrapper => {
        if (!wrapper.metatype) return false;
        return Reflect.getMetadata(VALIDATOR_KEY, wrapper.metatype);
      })
      .map(wrapper => wrapper.instance as Validator);
  }

  async validateAll(input: any) {
    for (const validator of this.validators) {
      validator.validate(input);
    }
  }
}
```

`DiscoveryService`는 `@nestjs/core`에서 제공한다. 별도로 import할 모듈은 없지만, `DiscoveryModule`을 import해야 사용할 수 있다.

### 멀티 프로바이더 주의사항

**같은 토큰에 providers 배열로 여러 번 등록하면 마지막이 이긴다**

```typescript
@Module({
  providers: [
    { provide: 'LOGGER', useClass: ConsoleLogger },
    { provide: 'LOGGER', useClass: FileLogger },    // 이게 최종 등록됨
  ],
})
export class AppModule {}
```

NestJS DI 컨테이너는 같은 토큰에 대해 마지막으로 등록된 프로바이더를 사용한다. 에러나 경고가 나지 않으니 의도와 다르게 동작하는 걸 눈치채기 어렵다. 여러 구현체를 배열로 받으려면 위에서 설명한 팩토리 패턴이나 DiscoveryService를 써야 한다.

**순서 의존성이 있는 경우**

멀티 프로바이더를 수집해서 순차 실행한다면 실행 순서가 중요할 수 있다. `useFactory`로 직접 배열을 만들면 순서를 제어할 수 있지만, `DiscoveryService`로 자동 수집하면 순서가 보장되지 않는다. 순서가 중요하면 메타데이터에 priority 값을 넣고 정렬하는 식으로 처리해야 한다.

```typescript
export const IsValidator = (priority = 0) =>
  SetMetadata(VALIDATOR_KEY, { enabled: true, priority });
```


## 모듈 간 프로바이더 충돌

모듈이 많아지면 같은 토큰의 프로바이더가 여러 모듈에 존재하는 상황이 생긴다. 어떤 인스턴스가 주입되는지 이해하지 못하면 디버깅하기 어려운 버그가 나온다.

### 같은 토큰이 여러 모듈에 있을 때

```typescript
@Module({
  providers: [
    { provide: 'CONFIG', useValue: { timeout: 3000 } },
    ServiceA,
  ],
  exports: ['CONFIG', ServiceA],
})
export class ModuleA {}

@Module({
  providers: [
    { provide: 'CONFIG', useValue: { timeout: 10000 } },
    ServiceB,
  ],
  exports: ['CONFIG', ServiceB],
})
export class ModuleB {}

@Module({
  imports: [ModuleA, ModuleB],
})
export class AppModule {}
```

이 상태에서 `AppModule` 내의 어떤 서비스가 `@Inject('CONFIG')`를 하면 어떤 값이 들어올까? imports 배열에서 나중에 선언된 모듈(`ModuleB`)의 프로바이더가 들어온다. NestJS는 같은 토큰을 나중에 등록하면 이전 것을 덮어쓴다.

문제는 이게 아무 경고 없이 일어난다는 것이다. `ModuleA`의 `ServiceA`는 자기 모듈의 `CONFIG`(timeout: 3000)를 쓰고, `AppModule`에서 직접 주입하면 `ModuleB`의 `CONFIG`(timeout: 10000)가 들어온다. 모듈 스코프에 따라 다른 값이 주입되니까 동작이 일관적이지 않다.

### exports 안 한 프로바이더가 덮어씌워지는 사례

```typescript
@Module({
  providers: [LoggerService],  // exports 안 함 → 모듈 내부 전용
})
export class InternalModule {}

@Module({
  providers: [
    {
      provide: LoggerService,
      useClass: CustomLoggerService,  // 같은 토큰으로 등록
    },
  ],
  exports: [LoggerService],
})
export class CustomLoggerModule {}

@Module({
  imports: [InternalModule, CustomLoggerModule],
})
export class AppModule {}
```

`InternalModule`이 `LoggerService`를 exports하지 않았으니까 외부에 영향이 없을 거라고 생각할 수 있다. 맞다 — `InternalModule` 내부의 서비스들은 자기 모듈의 `LoggerService`를 쓴다.

하지만 global 모듈이 끼면 상황이 달라진다:

```typescript
@Global()
@Module({
  providers: [LoggerService],
  exports: [LoggerService],
})
export class GlobalLoggerModule {}

@Module({
  providers: [LoggerService],  // 로컬에서 다시 등록
})
export class FeatureModule {}
```

`FeatureModule`이 `LoggerService`를 로컬에 등록하면 해당 모듈 내에서는 로컬 인스턴스가 우선한다. `GlobalLoggerModule`의 인스턴스를 덮는다. 의도한 거라면 괜찮지만, 모르고 같은 클래스 이름을 쓰면 글로벌 설정이 무시되는 원인이 된다.

### 충돌 방지 방법

**1. 문자열이나 Symbol 토큰을 사용한다**

```typescript
// 모듈별로 고유한 토큰을 정의
export const MODULE_A_CONFIG = Symbol('MODULE_A_CONFIG');
export const MODULE_B_CONFIG = Symbol('MODULE_B_CONFIG');

@Module({
  providers: [
    { provide: MODULE_A_CONFIG, useValue: { timeout: 3000 } },
  ],
  exports: [MODULE_A_CONFIG],
})
export class ModuleA {}
```

Symbol은 유일성이 보장되니까 토큰 충돌이 원천적으로 없다. 문자열 토큰은 모듈 prefix를 붙여서 `MODULE_A_CONFIG` 같은 형태로 관리한다.

**2. 글로벌 모듈은 신중하게 사용한다**

`@Global()`을 남발하면 토큰 충돌 가능성이 높아진다. 글로벌 모듈은 ConfigModule, DatabaseModule처럼 정말로 모든 모듈에서 필요한 것만 글로벌로 등록해야 한다. "import 쓰기 귀찮아서" 글로벌로 만들면 나중에 토큰 충돌 디버깅 지옥에 빠진다.

**3. 토큰 충돌 디버깅**

예상과 다른 프로바이더가 주입되는 것 같으면, NestJS의 디버그 로깅을 켜서 DI 컨테이너가 어떤 프로바이더를 어떤 모듈에 등록하는지 확인한다.

```typescript
const app = await NestFactory.create(AppModule, {
  logger: ['debug'],
});
```

디버그 로그에서 `"... is not unique"` 같은 경고가 나오면 토큰이 겹치고 있다는 신호다.


## 모노레포에서 모듈 분리

NestJS CLI는 `library` 모드를 제공한다. 공통 모듈(DTO, 인터페이스, 유틸리티 등)을 별도 라이브러리로 분리해서 여러 애플리케이션에서 공유하는 구조다.

### library 모드 기본 구조

```bash
nest g library common
```

이 명령을 실행하면 `libs/common` 디렉토리가 생기고, `nest-cli.json`에 라이브러리 설정이 추가된다.

```
project-root/
├── apps/
│   ├── api/          # 메인 애플리케이션
│   └── worker/       # 워커 애플리케이션
├── libs/
│   └── common/       # 공통 라이브러리
│       ├── src/
│       │   ├── common.module.ts
│       │   ├── common.service.ts
│       │   └── index.ts    ← barrel export
│       └── tsconfig.lib.json
├── nest-cli.json
└── tsconfig.json
```

`tsconfig.json`에 path alias가 자동으로 추가된다:

```json
{
  "compilerOptions": {
    "paths": {
      "@app/common": ["libs/common/src"],
      "@app/common/*": ["libs/common/src/*"]
    }
  }
}
```

사용하는 쪽에서는 이렇게 import한다:

```typescript
import { CommonModule, SomeService } from '@app/common';
```

### 실무에서 겪는 문제들

**1. barrel export(index.ts) 누락**

가장 흔한 실수다. `libs/common/src/index.ts`에서 export하지 않은 파일은 `@app/common`으로 import할 수 없다.

```typescript
// libs/common/src/index.ts
export * from './common.module';
export * from './common.service';
// dto/create-user.dto.ts를 여기에 추가하는 걸 빠뜨리면
// import { CreateUserDto } from '@app/common'; ← 컴파일 에러
```

파일을 추가할 때마다 `index.ts`를 수정해야 하는데, 이걸 잊으면 "분명 파일은 있는데 import가 안 된다"는 상황이 생긴다. 특히 코드 리뷰에서 잡기 어렵다 — 새 파일을 만든 사람은 로컬에서 상대 경로로 import해서 동작하는 걸 확인하고, 다른 앱에서 `@app/common`으로 import하려는 사람만 에러를 만난다.

**2. path alias가 런타임에 안 먹는 문제**

`tsconfig.json`의 `paths`는 TypeScript 컴파일러에게만 의미가 있다. 컴파일된 JavaScript에는 path alias가 그대로 남아있다. `tsc`로 빌드하면 `require('@app/common')`이 그대로 출력되는데, Node.js는 이 경로를 모른다.

NestJS CLI의 `nest build`는 내부적으로 이걸 처리해준다. 하지만 `tsc`를 직접 실행하거나, `ts-node`로 실행할 때는 `tsconfig-paths` 패키지를 별도로 등록해야 한다.

```typescript
// ts-node로 실행할 때
// tsconfig-paths/register를 먼저 로드해야 한다
// package.json
{
  "scripts": {
    "start:dev": "ts-node -r tsconfig-paths/register src/main.ts"
  }
}
```

Jest에서도 마찬가지다. `jest.config.ts`에 `moduleNameMapper`를 설정해야 한다:

```typescript
// jest.config.ts
{
  moduleNameMapper: {
    '^@app/common(.*)$': '<rootDir>/libs/common/src$1',
  },
}
```

이 설정을 빠뜨리면 테스트에서 `Cannot find module '@app/common'` 에러가 난다.

**3. 라이브러리 간 의존성 순환**

```
libs/
├── common/     # 공통 유틸
├── auth/       # 인증 관련 — common에 의존
└── user/       # 사용자 관련 — common, auth에 의존
```

`auth` 라이브러리가 `user`의 타입을 참조하고, `user`가 `auth`의 인터페이스를 참조하면 순환 의존성이 생긴다. TypeScript 컴파일은 되는 경우가 있지만, 런타임에 `undefined`가 주입되는 원인이 된다.

해결 방법은 공통 인터페이스를 `common` 라이브러리로 올리는 것이다. `auth`와 `user`가 서로를 직접 참조하지 않고, 공통 인터페이스에 의존하는 구조로 바꿔야 한다.

**4. 빌드 순서 문제**

라이브러리가 여러 개이고 서로 의존하면, 빌드 순서가 맞아야 한다. `nest build`는 단일 프로젝트만 빌드하므로, 의존하는 라이브러리가 먼저 빌드되어 있어야 한다.

```bash
# common을 먼저 빌드하고, auth를 빌드하고, 마지막에 api를 빌드
nest build common && nest build auth && nest build api
```

`nest-cli.json`에서 `webpack`을 사용하면 빌드 시점에 모든 라이브러리를 하나로 번들링하기 때문에 이 문제가 줄어든다. 하지만 webpack 설정이 복잡해지는 트레이드오프가 있다.

### 라이브러리 분리 기준

모든 공통 코드를 하나의 `common` 라이브러리에 넣으면 결국 거대한 유틸 모듈이 된다. 목적별로 분리하는 게 낫다:

- `libs/database` — TypeORM 엔티티, 리포지토리, 마이그레이션
- `libs/auth` — 인증 가드, JWT 설정, 세션 관리
- `libs/dto` — 공유 DTO, 인터페이스, enum

분리 기준은 "이 라이브러리를 수정했을 때 영향받는 앱이 몇 개인가"로 판단한다. 모든 앱이 영향받는 코드만 `common`에 넣고, 특정 도메인에 관련된 코드는 도메인별 라이브러리로 분리한다.


## Graceful Shutdown 구현

프로덕션에서 배포할 때 SIGTERM을 받고 바로 죽으면 진행 중인 요청이 실패한다. Graceful Shutdown은 새 요청을 거부하면서 진행 중인 요청은 완료한 후 종료하는 방식이다.

### 기본 설정

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // 종료 훅을 활성화해야 OnModuleDestroy, BeforeApplicationShutdown이 동작함
  app.enableShutdownHooks();

  await app.listen(3000);
}
bootstrap();
```

`enableShutdownHooks()`를 호출하지 않으면 `OnModuleDestroy`와 `BeforeApplicationShutdown`이 **실행되지 않는다.** 이걸 빠뜨리는 경우가 많다. 로컬에서 Ctrl+C로 종료할 때는 문제없어 보이지만, 쿠버네티스에서 Pod이 SIGTERM을 받을 때 리소스 정리가 안 되는 원인이 된다.

### 훅 순서와 주의사항

종료 시 훅 실행 순서:

```
SIGTERM 수신
    ↓
OnModuleDestroy (모든 모듈)
    ↓
BeforeApplicationShutdown (모든 모듈)
    ↓
HTTP 서버 close (리스닝 소켓 닫힘)
    ↓
프로세스 종료
```

여기서 핵심은 **BeforeApplicationShutdown 시점에 HTTP 서버가 아직 살아있다**는 것이다. 진행 중인 요청을 마무리하는 로직은 `BeforeApplicationShutdown`에 넣어야 한다.

### 실무 Graceful Shutdown 구현 예시

```typescript
@Injectable()
export class GracefulShutdownService
  implements OnModuleDestroy, BeforeApplicationShutdown
{
  private isShuttingDown = false;
  private activeRequests = 0;

  onRequest() {
    this.activeRequests++;
  }

  onRequestComplete() {
    this.activeRequests--;
  }

  getIsShuttingDown() {
    return this.isShuttingDown;
  }

  async onModuleDestroy() {
    this.isShuttingDown = true;
    // 이 시점부터 새 요청을 받지 않도록 플래그 설정
    // 로드밸런서 헬스체크가 이 값을 보고 트래픽을 빼줌
  }

  async beforeApplicationShutdown(signal?: string) {
    console.log(`${signal} 수신, 진행 중인 요청 ${this.activeRequests}개 대기`);

    // 진행 중인 요청이 끝날 때까지 대기
    const maxWait = 30_000;  // 최대 30초
    const start = Date.now();

    while (this.activeRequests > 0 && Date.now() - start < maxWait) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    if (this.activeRequests > 0) {
      console.warn(`타임아웃: ${this.activeRequests}개 요청이 강제 종료됨`);
    }
  }
}
```

### 트러블슈팅: 자주 겪는 문제

**1. enableShutdownHooks()와 메모리 누수**

`enableShutdownHooks()`는 내부적으로 `process.on('SIGTERM')`, `process.on('SIGINT')` 리스너를 등록한다. 테스트 코드에서 매번 새로운 NestJS 앱을 만들면 리스너가 계속 쌓여서 Node.js의 `MaxListenersExceededWarning`이 뜬다.

```typescript
// 테스트에서는 enableShutdownHooks()를 호출하지 않거나,
// afterEach에서 반드시 app.close()를 호출해야 한다
afterEach(async () => {
  await app.close();
});
```

**2. OnModuleDestroy에서 DB를 먼저 끊어버리는 경우**

```
OnModuleDestroy 실행 순서:
  1. DatabaseModule.onModuleDestroy() → 커넥션 풀 종료
  2. LogModule.onModuleDestroy() → 버퍼에 쌓인 로그를 DB에 flush하려는데 실패
```

imports 순서가 `[DatabaseModule, LogModule]`이면 destroy는 역순으로 `LogModule → DatabaseModule`이 되어야 할 것 같지만, NestJS의 실제 동작에서 이 순서가 항상 보장되지 않을 수 있다. 안전하게 처리하려면 `BeforeApplicationShutdown`에서 로그 flush를 하고, `OnModuleDestroy`에서 DB를 끊는 식으로 훅을 분리해야 한다.

**3. 쿠버네티스에서 SIGTERM 타이밍 문제**

쿠버네티스는 Pod을 종료할 때 SIGTERM을 보내고 `terminationGracePeriodSeconds`(기본 30초) 후에 SIGKILL을 보낸다. NestJS의 Graceful Shutdown이 30초 안에 끝나지 않으면 SIGKILL로 강제 종료된다.

```yaml
# 쿠버네티스 설정에서 grace period를 NestJS의 종료 시간에 맞춰야 한다
spec:
  terminationGracePeriodSeconds: 60  # NestJS가 정리할 시간을 충분히 줌
  containers:
    - name: app
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 5"]
            # 로드밸런서가 트래픽을 빼는 시간을 확보
```

`preStop` 훅에서 5초 정도 sleep을 넣는 이유는, SIGTERM이 전달되는 시점과 로드밸런서가 해당 Pod으로의 트래픽을 중단하는 시점에 차이가 있기 때문이다. sleep 없이 바로 종료 프로세스에 들어가면 로드밸런서가 아직 트래픽을 보내고 있는 상태에서 새 요청 수신을 거부하게 되어 502 에러가 발생한다.

**4. 종료 훅에서 async 처리를 빠뜨리는 경우**

```typescript
// 문제 코드
async onModuleDestroy() {
  this.cleanup();  // await를 안 붙임
}

private async cleanup() {
  await this.pool.end();
}
```

`onModuleDestroy`에서 리턴된 Promise를 NestJS가 기다리는데, `cleanup()`에 await를 안 붙이면 `onModuleDestroy`가 즉시 resolve되어 cleanup이 끝나기 전에 다음 단계로 넘어간다. async 함수에서 다른 async 함수를 호출할 때 await를 빠뜨리는 건 흔한 실수지만, 종료 훅에서 이걸 빠뜨리면 리소스 누수로 이어진다.


## HMR(Hot Module Replacement) 설정

NestJS는 기본적으로 `start:dev` 스크립트로 파일 변경을 감지해 프로세스를 재시작한다. 작은 프로젝트면 충분하지만, 의존하는 모듈이 많거나 ORM 부트스트랩이 오래 걸리는 프로젝트에서는 매번 전체 재시작이 부담스럽다. HMR을 켜면 변경된 모듈만 교체되므로 부트스트랩 시간이 크게 줄어든다.

### webpack 기반 HMR 설정

NestJS는 webpack과 통합된 HMR을 지원한다. 먼저 webpack 설정 파일을 추가한다.

```javascript
// webpack-hmr.config.js
const nodeExternals = require('webpack-node-externals');
const { RunScriptWebpackPlugin } = require('run-script-webpack-plugin');

module.exports = function (options, webpack) {
  return {
    ...options,
    entry: ['webpack/hot/poll?100', options.entry],
    externals: [
      nodeExternals({
        allowlist: ['webpack/hot/poll?100'],
      }),
    ],
    plugins: [
      ...options.plugins,
      new webpack.HotModuleReplacementPlugin(),
      new webpack.WatchIgnorePlugin({
        paths: [/\.js$/, /\.d\.ts$/],
      }),
      new RunScriptWebpackPlugin({
        name: options.output.filename,
        autoRestart: false,
      }),
    ],
  };
};
```

필요한 패키지를 설치한다.

```bash
npm i -D webpack-node-externals run-script-webpack-plugin webpack
```

다음으로 main.ts에 HMR accept 코드를 추가한다.

```typescript
declare const module: any;

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);

  if (module.hot) {
    module.hot.accept();
    module.hot.dispose(() => app.close());
  }
}
bootstrap();
```

`module.hot`은 webpack HMR이 켜진 환경에서만 정의된다. 프로덕션 빌드에서는 `if` 블록이 dead code로 제거된다. `dispose` 콜백은 새 모듈로 교체되기 직전에 호출되어 기존 NestJS 앱을 정리한다.

마지막으로 package.json에 스크립트를 추가한다.

```json
{
  "scripts": {
    "start:dev": "nest build --webpack --webpackPath webpack-hmr.config.js --watch"
  }
}
```

### HMR이 효과적인 경우와 함정

HMR은 만능이 아니다. 다음 경우에서 가장 효과를 본다.

- AppModule이 30개 이상의 모듈을 import한다
- TypeORM 엔티티 메타데이터 수집이나 클래스 검증기 등록처럼 부트스트랩에 시간이 걸린다
- DB 마이그레이션, 외부 시스템 헬스체크가 부트스트랩에서 동작한다

반대로 다음 상황에서는 HMR이 오히려 디버깅을 어렵게 만든다.

**1. 글로벌 상태가 누적된다.** HMR은 모듈만 교체하지 Node.js 프로세스를 재시작하지 않는다. 모듈 바깥에 있는 전역 변수, `process.on()` 리스너, 타이머는 이전 상태가 그대로 남는다. 결과적으로 메모리 사용량이 계속 늘거나, 이벤트 리스너가 중복으로 등록되는 문제가 생긴다.

```typescript
// 문제 상황: HMR 적용 후 reload마다 이 리스너가 누적됨
process.on('SIGTERM', () => {
  // 매 reload마다 한 번씩 더 등록됨
});
```

`enableShutdownHooks()`도 같은 이유로 HMR 환경에서는 문제를 일으킨다. dev에서 메모리 누수 경고(`MaxListenersExceededWarning`)가 뜨면 HMR과의 상호작용을 의심해봐야 한다.

**2. DI 컨테이너 상태 불일치.** 싱글톤 프로바이더의 내부 상태(캐시, 커넥션 풀 등)가 모듈 교체 후에도 남아있는데, 그 상태를 참조하던 다른 프로바이더는 새 인스턴스로 교체될 수 있다. 결과적으로 "리로드 후에는 동작하는데 처음 시작했을 때만 이상하다"같은 버그가 나오기도 한다.

**3. 데코레이터 메타데이터가 갱신되지 않을 수 있다.** TypeORM 엔티티에 칼럼을 추가했는데 HMR 후에도 인식되지 않는 경우가 있다. `reflect-metadata`가 캐싱한 메타데이터를 갱신하지 못해서다. 이럴 땐 그냥 프로세스를 재시작해야 한다.

### SWC 빌더 — HMR을 안 쓰는 선택

NestJS 10 이상은 `--builder swc` 옵션으로 SWC 컴파일러를 쓸 수 있다. SWC는 TypeScript 컴파일이 tsc보다 10배 이상 빨라서, 재시작 자체가 빠르다. 작은 프로젝트나 중간 규모 프로젝트라면 HMR을 설정하는 것보다 SWC로 전환하는 게 단순하다.

```json
{
  "scripts": {
    "start:dev": "nest start --builder swc --watch"
  }
}
```

SWC는 `tsconfig`의 `paths` alias를 일부 인식하지 못하는 등 호환성 이슈가 있을 수 있으니 도입 전에 테스트가 필요하다. 그리고 SWC는 타입 체크를 안 한다 — 별도로 `tsc --noEmit`을 CI에서 돌려야 한다.

### HMR vs SWC vs nodemon — 어떤 걸 쓰나

| 환경 | 권장 도구 | 이유 |
|------|----------|------|
| 모듈 < 10개, 부트스트랩 < 2초 | 기본 `nest start --watch` | 설정 비용 대비 이득 없음 |
| 중간 규모, 부트스트랩 5~10초 | `--builder swc --watch` | 설정 간단, 재시작 충분히 빠름 |
| 대규모, 부트스트랩 15초 이상 | webpack HMR | 모듈 단위 교체로 reload 시간 최소화 |

실무에서 가장 흔한 함정은 "느리니까 HMR 켜자"고 곧장 webpack 설정을 만지는 것이다. 부트스트랩이 느린 진짜 원인(과도한 글로벌 모듈, 동기 초기화, 외부 시스템 헬스체크)을 먼저 찾고, 그게 끝나지 않을 때 HMR로 넘어가는 게 맞다.
