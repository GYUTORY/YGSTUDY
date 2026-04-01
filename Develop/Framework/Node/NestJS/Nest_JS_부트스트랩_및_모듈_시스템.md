---
title: NestJS 부트스트랩 및 모듈 시스템
tags: [nestjs, bootstrap, module, lifecycle, dynamic-module, graceful-shutdown, node]
updated: 2026-04-01
---

# NestJS 부트스트랩 및 모듈 시스템

NestJS 애플리케이션이 시작될 때 `NestFactory.create()` 한 줄 뒤에서 꽤 많은 일이 벌어진다. 모듈을 스캔하고, 의존성 그래프를 만들고, 프로바이더 인스턴스를 생성하는 과정이 순서대로 진행된다. 이 과정을 모르면 "왜 내 서비스가 아직 초기화 안 됐지?", "왜 OnModuleInit에서 다른 모듈의 서비스를 못 쓰지?"같은 문제를 만난다. 부트스트랩 내부 동작부터 동적 모듈 패턴, Graceful Shutdown까지 정리한다.


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
