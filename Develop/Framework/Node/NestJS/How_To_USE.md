---
title: NestJS 동작 과정과 핵심 문법
tags: [framework, node, nestjs, typescript, di, decorator]
updated: 2026-04-01
---

# NestJS 동작 과정과 핵심 문법

NestJS가 내부적으로 어떻게 동작하는지, 그리고 실무에서 자주 부딪히는 문제를 중심으로 정리한다.

---

## NestJS가 하는 일

NestJS는 결국 Express(또는 Fastify) 위에 올라가는 래퍼다. 직접 하는 일은 크게 세 가지다.

1. **데코레이터로 메타데이터를 수집**해서 라우팅, DI, 미들웨어 체인을 자동으로 구성한다
2. **IoC 컨테이너**가 클래스 인스턴스의 생성과 주입을 관리한다
3. **요청 파이프라인**(미들웨어 → 가드 → 인터셉터 → 파이프 → 핸들러 → 인터셉터 → 예외 필터)을 실행한다

Express만 쓸 때는 이 세 가지를 개발자가 직접 구성해야 한다. NestJS는 이 구성을 데코레이터와 모듈 시스템으로 자동화한 것이다.

---

## 부트스트랩 과정

`NestFactory.create(AppModule)`을 호출하면 내부에서 어떤 일이 벌어지는지 알아야 디버깅이 편하다.

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
}
```

`create()` 내부 동작 순서:

1. `AppModule`의 `@Module()` 데코레이터에서 메타데이터를 읽는다
2. `imports`에 선언된 모듈을 재귀적으로 탐색한다
3. 각 모듈의 `providers`를 IoC 컨테이너에 등록한다
4. 의존성 그래프를 만들고, 순서대로 인스턴스를 생성한다
5. `controllers`에 선언된 클래스의 메서드 데코레이터를 읽어 라우트 테이블을 만든다
6. Express(또는 Fastify) 인스턴스에 라우트를 등록한다

여기서 중요한 건 **4번**이다. 의존성 그래프에 순환이 있으면 부트스트랩 자체가 실패한다. 이 문제는 뒤에서 다룬다.

---

## 데코레이터가 실제로 하는 일

NestJS 데코레이터는 마법이 아니다. 내부적으로 `reflect-metadata` 라이브러리를 써서 클래스에 메타데이터를 붙이는 게 전부다.

### reflect-metadata 동작 방식

`@Controller('users')`가 실행되면 내부에서 이런 코드가 돌아간다:

```typescript
// NestJS 내부 구현을 단순화한 것
function Controller(prefix?: string): ClassDecorator {
  return (target: Function) => {
    Reflect.defineMetadata('path', prefix || '', target);
    Reflect.defineMetadata('__isController__', true, target);
  };
}
```

`@Get(':id')`도 마찬가지다:

```typescript
function Get(path?: string): MethodDecorator {
  return (target, propertyKey, descriptor) => {
    Reflect.defineMetadata('path', path || '', descriptor.value);
    Reflect.defineMetadata('method', 'GET', descriptor.value);
  };
}
```

NestJS는 부트스트랩 시점에 `Reflect.getMetadata()`로 이 정보를 꺼내서 라우트를 등록한다.

### @Injectable()의 진짜 역할

`@Injectable()`은 클래스에 "이 클래스는 DI 대상이다"라는 표시를 남기는 것 외에, TypeScript의 `emitDecoratorMetadata` 옵션과 결합해서 **생성자 파라미터의 타입 정보**를 메타데이터로 저장한다.

```typescript
@Injectable()
export class UsersService {
  constructor(private readonly usersRepo: UsersRepository) {}
}
```

컴파일 후 TypeScript가 자동으로 이런 메타데이터를 생성한다:

```typescript
Reflect.defineMetadata('design:paramtypes', [UsersRepository], UsersService);
```

IoC 컨테이너는 이 `design:paramtypes`를 읽어서 `UsersService`를 만들 때 `UsersRepository` 인스턴스를 주입해야 한다는 걸 안다.

**주의**: `@Injectable()`을 빼먹으면 `design:paramtypes` 메타데이터가 생성되지 않아서 DI가 실패한다. "왜 주입이 안 되지?" 할 때 가장 먼저 확인할 것이다.

### tsconfig.json 필수 설정

```json
{
  "compilerOptions": {
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true
  }
}
```

이 두 옵션이 빠지면 데코레이터 기반 DI 자체가 작동하지 않는다.

---

## 모듈 시스템

### 모듈의 역할

모듈은 관련된 컨트롤러와 프로바이더를 묶는 단위다. 중요한 건 **스코프**다.

```typescript
@Module({
  imports: [DatabaseModule],
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}
```

- `providers`에 등록한 것은 **이 모듈 안에서만** 사용 가능하다
- 다른 모듈에서 쓰게 하려면 반드시 `exports`에 넣어야 한다
- `imports`에 다른 모듈을 넣으면, 그 모듈이 `exports`한 프로바이더를 사용할 수 있다

자주 하는 실수: `UsersModule`에서 `UsersService`를 exports하지 않고, `OrdersModule`에서 `UsersService`를 주입하려고 하면 런타임에 에러가 난다. 에러 메시지가 "Nest can't resolve dependencies"로 나오는데, exports를 빠뜨린 경우가 대부분이다.

### 글로벌 모듈

매번 imports하기 귀찮은 모듈은 `@Global()`로 선언한다:

```typescript
@Global()
@Module({
  providers: [ConfigService],
  exports: [ConfigService],
})
export class ConfigModule {}
```

`AppModule`에 한 번만 import하면 모든 모듈에서 `ConfigService`를 주입받을 수 있다. 다만 남용하면 의존성 추적이 어려워진다. 정말 전역으로 필요한 것(설정, 로거 정도)만 글로벌로 만든다.

### 동적 모듈

설정값을 받아서 모듈을 구성해야 할 때 쓴다. `@nestjs/config`의 `ConfigModule.forRoot()`가 대표적인 예다.

```typescript
@Module({})
export class DatabaseModule {
  static forRoot(options: { host: string; port: number }): DynamicModule {
    return {
      module: DatabaseModule,
      providers: [
        {
          provide: 'DB_OPTIONS',
          useValue: options,
        },
        DatabaseService,
      ],
      exports: [DatabaseService],
    };
  }
}

// 사용
@Module({
  imports: [DatabaseModule.forRoot({ host: 'localhost', port: 5432 })],
})
export class AppModule {}
```

`forRoot`과 `forRootAsync`의 차이: `forRoot`은 동기적으로 설정값을 받고, `forRootAsync`는 다른 프로바이더에 의존하는 비동기 설정이 필요할 때 쓴다.

---

## 프로바이더와 의존성 주입

### 기본 주입 방식

생성자 주입이 표준이다:

```typescript
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}
}
```

TypeScript의 `private readonly` 축약 문법을 쓰면 필드 선언과 할당을 한 줄로 할 수 있다. NestJS 코드에서 이 패턴이 거의 관례다.

### 커스텀 프로바이더

`providers` 배열에 클래스를 직접 넣는 건 사실 축약 표현이다:

```typescript
// 이 두 줄은 같은 의미다
providers: [UsersService]
providers: [{ provide: UsersService, useClass: UsersService }]
```

실무에서 커스텀 프로바이더가 필요한 상황:

#### useClass — 환경별 구현체 교체

```typescript
@Module({
  providers: [
    {
      provide: PaymentService,
      useClass:
        process.env.NODE_ENV === 'production'
          ? StripePaymentService
          : MockPaymentService,
    },
  ],
})
export class PaymentModule {}
```

테스트 환경에서 외부 API를 호출하지 않으려고 할 때 자주 쓴다. 인터페이스를 기준으로 주입하는 것이라서 사용하는 쪽 코드는 변경할 필요가 없다.

#### useValue — 고정값, 설정 객체

```typescript
@Module({
  providers: [
    {
      provide: 'API_KEY',
      useValue: process.env.API_KEY,
    },
  ],
})
export class AppModule {}

// 주입받을 때는 @Inject() 데코레이터 필요
@Injectable()
export class ExternalApiService {
  constructor(@Inject('API_KEY') private apiKey: string) {}
}
```

문자열 토큰 대신 Symbol이나 클래스를 쓸 수도 있다. 문자열 토큰은 오타가 나면 런타임에서야 잡히기 때문에, 프로젝트가 커지면 상수로 관리하는 게 낫다.

#### useFactory — 비동기 초기화, 다른 프로바이더 의존

```typescript
@Module({
  providers: [
    {
      provide: 'DATABASE_CONNECTION',
      useFactory: async (configService: ConfigService) => {
        const connection = await createConnection({
          host: configService.get('DB_HOST'),
          port: configService.get<number>('DB_PORT'),
        });
        return connection;
      },
      inject: [ConfigService], // useFactory에 주입할 프로바이더
    },
  ],
})
export class DatabaseModule {}
```

`inject` 배열의 순서가 factory 함수 파라미터 순서와 일치해야 한다. 순서가 어긋나면 타입 에러 없이 잘못된 객체가 주입되어서 디버깅이 힘들다.

#### useExisting — 별칭(alias)

```typescript
@Module({
  providers: [
    UsersService,
    {
      provide: 'AliasedUsersService',
      useExisting: UsersService,
    },
  ],
})
export class UsersModule {}
```

같은 인스턴스를 다른 토큰으로 참조할 때 쓴다. 레거시 코드와 새 코드가 공존하는 상황에서 가끔 필요하다. 새 인스턴스를 만드는 게 아니라 기존 인스턴스에 대한 참조를 하나 더 만드는 것이다.

### 프로바이더 스코프

기본적으로 NestJS의 모든 프로바이더는 **싱글톤**이다. 애플리케이션 시작 시 한 번 생성되고, 모든 요청에서 같은 인스턴스를 공유한다.

#### DEFAULT (싱글톤)

```typescript
@Injectable() // scope 지정 안 하면 DEFAULT
export class UsersService {}
```

대부분의 서비스는 이걸로 충분하다. 상태를 갖지 않는 서비스라면 싱글톤이 맞다.

#### REQUEST 스코프

```typescript
@Injectable({ scope: Scope.REQUEST })
export class RequestContextService {
  private tenantId: string;

  setTenantId(id: string) {
    this.tenantId = id;
  }

  getTenantId() {
    return this.tenantId;
  }
}
```

요청마다 새 인스턴스가 생성된다. 멀티테넌트 환경에서 요청별로 다른 DB 연결을 써야 할 때 같은 경우에 필요하다.

**주의할 점**: REQUEST 스코프 프로바이더를 주입받는 프로바이더도 자동으로 REQUEST 스코프가 된다. 이게 **버블링**이다. `UsersService`(DEFAULT) → `RequestContextService`(REQUEST) 의존 관계면, `UsersService`도 REQUEST 스코프로 승격된다.

이게 성능에 미치는 영향이 크다. 싱글톤이었던 서비스가 요청마다 새로 생성되니까 GC 부담이 늘어난다. REQUEST 스코프가 전파되는 범위를 꼭 확인해야 한다.

```typescript
// 의존성 체인 예시
// UsersController → UsersService → RequestContextService(REQUEST)
// → UsersService도 REQUEST로 승격
// → UsersController도 REQUEST로 승격
// 결과: 요청마다 컨트롤러, 서비스 전부 새로 생성
```

#### TRANSIENT 스코프

```typescript
@Injectable({ scope: Scope.TRANSIENT })
export class LoggerService {
  private context: string;

  setContext(context: string) {
    this.context = context;
  }

  log(message: string) {
    console.log(`[${this.context}] ${message}`);
  }
}
```

주입받는 곳마다 별도의 인스턴스가 생성된다. `UsersService`와 `OrdersService`가 각각 `LoggerService`를 주입받으면, 서로 다른 인스턴스를 가진다.

REQUEST와 TRANSIENT의 차이:
- REQUEST: 같은 요청 안에서는 같은 인스턴스를 공유
- TRANSIENT: 주입받는 곳마다 항상 다른 인스턴스

---

## 순환 참조와 forwardRef

실무에서 꽤 자주 마주치는 문제다. `UsersModule`이 `OrdersModule`을 import하고, `OrdersModule`도 `UsersModule`을 import하면 순환 참조가 발생한다.

### 모듈 간 순환 참조

```typescript
// users.module.ts
@Module({
  imports: [forwardRef(() => OrdersModule)],
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}

// orders.module.ts
@Module({
  imports: [forwardRef(() => UsersModule)],
  providers: [OrdersService],
  exports: [OrdersService],
})
export class OrdersModule {}
```

`forwardRef(() => OrdersModule)`는 "아직 정의되지 않았을 수 있지만, 나중에 이 모듈을 참조하겠다"는 의미다. 양쪽 모듈 모두에 `forwardRef`를 적용해야 한다.

### 프로바이더 간 순환 참조

```typescript
@Injectable()
export class UsersService {
  constructor(
    @Inject(forwardRef(() => OrdersService))
    private ordersService: OrdersService,
  ) {}
}

@Injectable()
export class OrdersService {
  constructor(
    @Inject(forwardRef(() => UsersService))
    private usersService: UsersService,
  ) {}
}
```

### 순환 참조를 피하는 방법

`forwardRef`는 임시 해결책이다. 가능하면 설계를 바꾸는 게 맞다.

1. **중간 서비스 도입**: `UsersService`와 `OrdersService`가 서로를 직접 호출하는 대신, `UserOrderService` 같은 조합 서비스를 만든다
2. **이벤트 기반 통신**: 한쪽이 이벤트를 발행하고 다른 쪽이 구독하는 방식. `@nestjs/event-emitter`를 쓰면 된다
3. **의존성 방향 재설계**: 대부분의 순환 참조는 책임 분리가 잘못된 신호다

---

## 컨트롤러와 라우팅

### 기본 구조

```typescript
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() dto: CreateUserDto) {
    return this.usersService.create(dto);
  }

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }

  @Patch(':id')
  update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateUserDto,
  ) {
    return this.usersService.update(id, dto);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  remove(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.remove(id);
  }
}
```

### 파라미터 데코레이터

`@Body()`, `@Param()`, `@Query()`, `@Headers()` 등이 있다. 내부적으로 `ExecutionContext`에서 Express의 `req` 객체를 꺼낸 뒤, 지정된 키의 값을 추출한다.

```typescript
// @Body('name')이 하는 일을 단순화하면
const name = req.body['name'];

// @Query()가 하는 일
const query = req.query;

// @Param('id')가 하는 일
const id = req.params['id'];
```

`@Req()`와 `@Res()`로 Express 객체에 직접 접근할 수 있지만, 그렇게 하면 Fastify로 전환할 때 코드를 다 고쳐야 한다. 가능하면 NestJS 파라미터 데코레이터만 쓴다.

### 커스텀 파라미터 데코레이터

```typescript
export const CurrentUser = createParamDecorator(
  (data: string | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);

// 사용
@Get('me')
getProfile(@CurrentUser() user: UserPayload) {
  return user;
}

@Get('me/email')
getEmail(@CurrentUser('email') email: string) {
  return { email };
}
```

---

## 요청 파이프라인

요청이 들어오면 거치는 순서:

```
클라이언트 요청
  → 미들웨어 (Middleware)
    → 가드 (Guard)
      → 인터셉터 (pre-handler)
        → 파이프 (Pipe)
          → 핸들러 (Controller method)
        → 인터셉터 (post-handler)
      → 예외 필터 (Exception Filter)
  → 클라이언트 응답
```

각 단계의 역할:

- **미들웨어**: Express 미들웨어와 같다. 요청/응답 객체를 변경할 수 있다. CORS, 로깅 같은 범용 처리에 쓴다
- **가드**: `canActivate()` 메서드가 true를 반환하면 요청을 통과시킨다. 인증/인가에 쓴다
- **인터셉터**: 핸들러 실행 전후에 로직을 끼워 넣는다. 응답 변환, 로깅, 캐싱에 쓴다
- **파이프**: 핸들러에 전달되는 인자를 변환하거나 검증한다
- **예외 필터**: 파이프라인 어디서든 발생한 예외를 잡아서 응답 형식을 통일한다

### 가드 구현

```typescript
@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const token = request.headers.authorization?.replace('Bearer ', '');

    if (!token) {
      throw new UnauthorizedException();
    }

    try {
      const payload = this.jwtService.verify(token);
      request.user = payload;
      return true;
    } catch {
      throw new UnauthorizedException();
    }
  }
}
```

### 역할 기반 접근 제어

가드와 커스텀 데코레이터를 조합한다:

```typescript
// 데코레이터 정의
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

// 가드 구현
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const roles = this.reflector.get<string[]>('roles', context.getHandler());
    if (!roles) return true;

    const request = context.switchToHttp().getRequest();
    return roles.some((role) => request.user.roles?.includes(role));
  }
}

// 적용
@Get('admin')
@Roles('admin')
@UseGuards(JwtAuthGuard, RolesGuard)
adminEndpoint() {
  return { message: 'admin only' };
}
```

`Reflector`가 `SetMetadata`로 붙인 메타데이터를 읽는 역할을 한다. 결국 내부적으로는 `Reflect.getMetadata()`를 호출한다.

### 인터셉터 구현

```typescript
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const now = Date.now();

    return next.handle().pipe(
      tap(() => {
        console.log(
          `${request.method} ${request.url} - ${Date.now() - now}ms`,
        );
      }),
    );
  }
}
```

`next.handle()`이 실제 핸들러를 실행한다. RxJS Observable을 반환하기 때문에 `pipe()`로 후처리를 할 수 있다.

### 예외 필터

```typescript
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const status = exception.getStatus();

    response.status(status).json({
      statusCode: status,
      message: exception.message,
      timestamp: new Date().toISOString(),
    });
  }
}
```

`@Catch()` 데코레이터에 인자를 넣지 않으면 모든 예외를 잡는다. 특정 예외만 잡으려면 `@Catch(NotFoundException)` 식으로 지정한다.

---

## DTO와 유효성 검증

### ValidationPipe 설정

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,           // DTO에 정의되지 않은 프로퍼티 제거
      forbidNonWhitelisted: true, // 정의되지 않은 프로퍼티가 있으면 400 에러
      transform: true,           // 쿼리 파라미터 등을 DTO 타입으로 자동 변환
    }),
  );

  await app.listen(3000);
}
```

`whitelist: true`는 꼭 켜야 한다. 클라이언트가 `isAdmin: true` 같은 필드를 몰래 보내는 걸 방지한다.

### DTO 정의

```typescript
import { IsString, IsEmail, IsInt, Min, Max, IsOptional, MinLength } from 'class-validator';

export class CreateUserDto {
  @IsString()
  @MinLength(2)
  name: string;

  @IsEmail()
  email: string;

  @IsInt()
  @Min(1)
  @Max(120)
  age: number;

  @IsOptional()
  @IsString()
  @MinLength(8)
  password?: string;
}
```

```typescript
import { PartialType } from '@nestjs/mapped-types';
import { CreateUserDto } from './create-user.dto';

export class UpdateUserDto extends PartialType(CreateUserDto) {}
```

`PartialType`은 모든 필드를 optional로 만든다. 내부적으로 class-validator 데코레이터의 메타데이터를 복사하면서 `@IsOptional()`을 추가한다.

### 커스텀 Pipe

```typescript
@Injectable()
export class ParseIntPipe implements PipeTransform<string, number> {
  transform(value: string, metadata: ArgumentMetadata): number {
    const parsed = parseInt(value, 10);
    if (isNaN(parsed)) {
      throw new BadRequestException(`"${value}"는 정수가 아니다`);
    }
    return parsed;
  }
}
```

NestJS가 내장 `ParseIntPipe`를 제공하지만, 에러 메시지를 커스터마이징하려면 직접 만들어야 하는 경우가 있다.

---

## 실무에서 자주 겪는 문제

### "Nest can't resolve dependencies" 에러

가장 흔한 에러다. 원인은 대부분 셋 중 하나:

1. **모듈에서 exports를 빠뜨렸다** — 프로바이더를 다른 모듈에서 쓰려면 exports 배열에 넣어야 한다
2. **@Injectable()을 빠뜨렸다** — DI 대상 클래스에 데코레이터가 없으면 메타데이터가 생성되지 않는다
3. **순환 참조** — A가 B를 필요로 하고 B가 A를 필요로 하는 상황. forwardRef로 임시 해결 가능

에러 메시지에 `?` 표시가 나오면 해당 위치의 파라미터 타입을 NestJS가 식별하지 못한 것이다. 인터페이스로 타입을 지정한 경우에 이런 문제가 생긴다. TypeScript 인터페이스는 런타임에 존재하지 않기 때문이다.

```typescript
// 이렇게 하면 안 된다
constructor(private usersService: IUsersService) {} // 인터페이스 = 런타임에 없음

// 이렇게 해야 한다
constructor(
  @Inject('USERS_SERVICE') private usersService: IUsersService,
) {}
```

### REQUEST 스코프의 성능 문제

REQUEST 스코프 프로바이더를 하나 도입했더니 응답 시간이 눈에 띄게 늘어나는 경우가 있다. 스코프 버블링 때문에 연쇄적으로 싱글톤이 REQUEST 스코프로 승격되면, 요청마다 수십 개의 인스턴스를 새로 만들 수 있다.

대안으로 `@nestjs/core`의 `REQUEST` 토큰과 `ModuleRef`를 써서, REQUEST 스코프 없이 요청 컨텍스트를 처리하는 방법이 있다:

```typescript
import { REQUEST } from '@nestjs/core';

@Injectable()
export class TenantService {
  constructor(@Inject(REQUEST) private request: Request) {}

  getTenantId(): string {
    return this.request.headers['x-tenant-id'] as string;
  }
}
```

Node.js 14.8+ 환경이면 `AsyncLocalStorage`를 써서 REQUEST 스코프 없이도 요청 컨텍스트를 전파할 수 있다. NestJS에서도 `cls-hooked`나 `@nestjs-cls/core` 같은 라이브러리로 지원한다.

### 테스트에서 DI 활용

```typescript
describe('UsersService', () => {
  let service: UsersService;
  let mockRepo: jest.Mocked<Repository<User>>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        UsersService,
        {
          provide: getRepositoryToken(User),
          useValue: {
            find: jest.fn(),
            findOne: jest.fn(),
            save: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get(UsersService);
    mockRepo = module.get(getRepositoryToken(User));
  });

  it('findAll은 유저 배열을 반환한다', async () => {
    const users = [{ id: 1, name: 'test' }] as User[];
    mockRepo.find.mockResolvedValue(users);

    const result = await service.findAll();
    expect(result).toEqual(users);
  });
});
```

`Test.createTestingModule()`이 실제 앱과 동일한 DI 시스템을 사용한다. 커스텀 프로바이더를 쓰면 외부 의존성을 쉽게 모킹할 수 있다.

---

## CRUD 예제: 전체 흐름

모듈 → 서비스 → 컨트롤러가 어떻게 연결되는지 전체를 한 번에 본다.

### Entity

```typescript
// users/entities/user.entity.ts
export class User {
  id: number;
  name: string;
  email: string;
  age: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}
```

### Service

```typescript
// users/users.service.ts
@Injectable()
export class UsersService {
  private users: User[] = [];
  private nextId = 1;

  create(dto: CreateUserDto): User {
    const user: User = {
      id: this.nextId++,
      ...dto,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.users.push(user);
    return user;
  }

  findAll(): User[] {
    return this.users;
  }

  findOne(id: number): User {
    const user = this.users.find((u) => u.id === id);
    if (!user) {
      throw new NotFoundException(`User #${id} not found`);
    }
    return user;
  }

  update(id: number, dto: UpdateUserDto): User {
    const user = this.findOne(id);
    Object.assign(user, dto, { updatedAt: new Date() });
    return user;
  }

  remove(id: number): void {
    const index = this.users.findIndex((u) => u.id === id);
    if (index === -1) {
      throw new NotFoundException(`User #${id} not found`);
    }
    this.users.splice(index, 1);
  }
}
```

### Controller

```typescript
// users/users.controller.ts
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(@Body() dto: CreateUserDto) {
    return this.usersService.create(dto);
  }

  @Get()
  findAll() {
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }

  @Patch(':id')
  update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateUserDto,
  ) {
    return this.usersService.update(id, dto);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  remove(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.remove(id);
  }
}
```

### Module

```typescript
// users/users.module.ts
@Module({
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}

// app.module.ts
@Module({
  imports: [UsersModule],
})
export class AppModule {}
```

---

## 참고

- [NestJS 공식 문서](https://docs.nestjs.com/)
- [NestJS GitHub](https://github.com/nestjs/nest)
- [reflect-metadata](https://github.com/rbuckton/reflect-metadata)
- [class-validator](https://github.com/typestack/class-validator)
- [class-transformer](https://github.com/typestack/class-transformer)
