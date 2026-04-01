---
title: NestJS 요청 라이프사이클
tags: [nestjs, lifecycle, middleware, guard, interceptor, pipe, node]
updated: 2026-04-01
---

# NestJS 요청 라이프사이클

NestJS에서 HTTP 요청이 들어오면 여러 레이어를 거쳐 핸들러에 도달한다. 각 레이어가 어떤 시점에 실행되는지 정확히 모르면 "분명 Guard에서 막았는데 왜 Pipe가 실행되지?"같은 혼란을 겪게 된다. 실행 순서를 정확히 이해하고, 각 레이어를 어디에 써야 하는지 정리한다.

## 요청 처리 순서

```
Client Request
    ↓
Middleware (Global → Module → Route)
    ↓
Guard (Global → Controller → Route)
    ↓
Interceptor - before (Global → Controller → Route)
    ↓
Pipe (Global → Controller → Route Parameter)
    ↓
Route Handler
    ↓
Interceptor - after (Route → Controller → Global)
    ↓
Exception Filter (Route → Controller → Global)
    ↓
Client Response
```

주의할 점은 **Interceptor의 after 처리와 Exception Filter는 실행 순서가 반대**라는 것이다. before 처리는 Global → Controller → Route 순이지만, after 처리와 에러 핸들링은 Route → Controller → Global 순으로 버블링된다. 스택처럼 동작한다고 생각하면 된다.


## Middleware

Express 미들웨어와 동일한 개념이다. `req`, `res`, `next`를 받고, 라우트 핸들러에 도달하기 전에 실행된다.

### 실무에서 주로 쓰는 경우

- 요청 로깅 (어떤 IP에서 어떤 경로로 요청했는지)
- 요청 본문 파싱 (커스텀 파서가 필요한 경우)
- CORS 처리 (NestJS 내장 옵션으로 대부분 해결되지만 세밀한 제어가 필요할 때)

```typescript
@Injectable()
export class RequestLoggerMiddleware implements NestMiddleware {
  private readonly logger = new Logger('HTTP');

  use(req: Request, res: Response, next: NextFunction) {
    const { method, originalUrl, ip } = req;
    const startTime = Date.now();

    res.on('finish', () => {
      const duration = Date.now() - startTime;
      this.logger.log(
        `${method} ${originalUrl} ${res.statusCode} ${duration}ms - ${ip}`,
      );
    });

    next();
  }
}
```

### Middleware 등록

```typescript
@Module({})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(RequestLoggerMiddleware)
      .forRoutes('*'); // 전체 라우트에 적용
  }
}
```

### 흔한 실수

`next()` 호출을 빼먹으면 요청이 멈춘다. Express 쓸 때와 똑같은 실수인데, NestJS에서도 동일하게 발생한다. 타임아웃 에러만 나오고 원인을 찾기 어려우니 미들웨어 작성 시 `next()` 호출 여부를 반드시 확인한다.

`res.send()`를 미들웨어에서 호출하면 이후 레이어가 전부 무시된다. Guard나 Interceptor에서 처리해야 할 로직이 있다면 미들웨어에서 응답을 보내면 안 된다.


## Guard

**인가(Authorization)** 처리 전용 레이어다. `canActivate()` 메서드가 `true`를 반환하면 다음 단계로 진행하고, `false`를 반환하면 `ForbiddenException`이 발생한다.

Guard는 Middleware와 다르게 `ExecutionContext`에 접근할 수 있다. 이 말은 "어떤 컨트롤러의 어떤 핸들러가 실행될 예정인지" 알 수 있다는 것이다. 이 차이가 핵심이다.

### 역할 기반 인가 처리

```typescript
// 역할 데코레이터 정의
export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);
```

```typescript
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    // 핸들러에 설정된 역할 메타데이터를 가져온다
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(
      ROLES_KEY,
      [context.getHandler(), context.getClass()],
    );

    // 역할이 지정되지 않은 핸들러는 누구나 접근 가능
    if (!requiredRoles) {
      return true;
    }

    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user) {
      throw new UnauthorizedException('인증 정보가 없습니다');
    }

    const hasRole = requiredRoles.some((role) => user.roles?.includes(role));
    if (!hasRole) {
      throw new ForbiddenException(
        `필요한 역할: ${requiredRoles.join(', ')}`,
      );
    }

    return true;
  }
}
```

```typescript
@Controller('admin')
@UseGuards(AuthGuard, RolesGuard)  // AuthGuard가 먼저 실행된다
export class AdminController {
  @Get('users')
  @Roles('ADMIN', 'SUPER_ADMIN')
  findAllUsers() {
    return this.adminService.findAllUsers();
  }

  @Delete('users/:id')
  @Roles('SUPER_ADMIN')  // 삭제는 SUPER_ADMIN만
  removeUser(@Param('id') id: string) {
    return this.adminService.removeUser(id);
  }
}
```

### 흔한 실수

**Guard 순서를 잘못 지정하는 경우**: `@UseGuards(RolesGuard, AuthGuard)` 이렇게 쓰면 인증 전에 역할 검사를 하게 된다. `request.user`가 없는 상태에서 역할을 확인하니 당연히 에러가 난다. 인증 Guard를 항상 먼저 배치해야 한다.

**`getAllAndOverride` vs `getAllAndMerge`**: `getAllAndOverride`는 핸들러 메타데이터가 있으면 컨트롤러 메타데이터를 무시한다. `getAllAndMerge`는 둘 다 합친다. 컨트롤러에 `@Roles('USER')`를 달고 핸들러에 `@Roles('ADMIN')`을 달았을 때, Override면 `['ADMIN']`만, Merge면 `['USER', 'ADMIN']`이 된다. 의도한 동작이 뭔지 정확히 파악하고 써야 한다.


## Interceptor

Guard를 통과하면 Interceptor가 실행된다. Interceptor는 **핸들러 실행 전후를 모두 감싸는** 레이어다. RxJS의 `Observable`을 반환하기 때문에 응답 스트림을 조작할 수 있다.

### 응답 변환 Interceptor

API 응답 형식을 통일하고 싶을 때 가장 많이 쓴다.

```typescript
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
}

@Injectable()
export class TransformInterceptor<T>
  implements NestInterceptor<T, ApiResponse<T>>
{
  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<ApiResponse<T>> {
    return next.handle().pipe(
      map((data) => ({
        success: true,
        data,
        timestamp: new Date().toISOString(),
      })),
    );
  }
}
```

핸들러에서 `{ id: 1, name: 'Kim' }`을 반환하면, 클라이언트에는 `{ success: true, data: { id: 1, name: 'Kim' }, timestamp: '...' }` 형태로 전달된다.

### 로깅 Interceptor

```typescript
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('Request');

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url } = request;
    const handler = context.getHandler().name;
    const controller = context.getClass().name;

    this.logger.log(`→ ${method} ${url} [${controller}.${handler}]`);
    const now = Date.now();

    return next.handle().pipe(
      tap(() => {
        this.logger.log(
          `← ${method} ${url} [${controller}.${handler}] ${Date.now() - now}ms`,
        );
      }),
    );
  }
}
```

### 캐싱 Interceptor

```typescript
@Injectable()
export class HttpCacheInterceptor implements NestInterceptor {
  constructor(
    @Inject(CACHE_MANAGER) private cacheManager: Cache,
    private reflector: Reflector,
  ) {}

  async intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Promise<Observable<any>> {
    const request = context.switchToHttp().getRequest();

    // GET 요청만 캐싱
    if (request.method !== 'GET') {
      return next.handle();
    }

    const ttl = this.reflector.get<number>('cacheTTL', context.getHandler());
    if (!ttl) {
      return next.handle();
    }

    const key = `cache:${request.url}`;
    const cached = await this.cacheManager.get(key);

    if (cached) {
      return of(cached);
    }

    return next.handle().pipe(
      tap(async (response) => {
        await this.cacheManager.set(key, response, ttl);
      }),
    );
  }
}
```

### 주의사항

`next.handle()`을 호출하지 않으면 핸들러가 실행되지 않는다. 캐싱 Interceptor처럼 의도적으로 핸들러를 건너뛰는 경우가 아니라면, 반드시 `next.handle()`을 호출해야 한다.

Interceptor에서 `catchError`를 쓰면 Exception Filter보다 먼저 에러를 잡을 수 있다. 의도한 거라면 괜찮지만, Exception Filter에서 처리하려던 에러가 Interceptor에서 먹혀버리면 디버깅이 힘들어진다.


## Pipe

Pipe는 핸들러의 **파라미터를 변환하거나 검증**하는 레이어다. 핸들러에 도달하기 직전에 실행된다.

### 내장 Pipe

NestJS에서 기본 제공하는 Pipe들이 있다.

| Pipe | 하는 일 |
|------|---------|
| `ValidationPipe` | class-validator로 DTO 검증 |
| `ParseIntPipe` | 문자열 → 정수 변환 |
| `ParseUUIDPipe` | UUID 형식 검증 |
| `ParseBoolPipe` | 문자열 → boolean 변환 |
| `DefaultValuePipe` | 값이 없으면 기본값 설정 |

### DTO 변환과 Validation

```typescript
// DTO 정의
export class CreateUserDto {
  @IsString()
  @MinLength(2)
  @MaxLength(50)
  name: string;

  @IsEmail()
  email: string;

  @IsEnum(UserRole)
  role: UserRole;

  @IsOptional()
  @IsString()
  nickname?: string;
}
```

```typescript
// Global ValidationPipe 설정
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,         // DTO에 정의되지 않은 속성 자동 제거
    forbidNonWhitelisted: true, // 정의되지 않은 속성이 있으면 에러
    transform: true,         // 요청 데이터를 DTO 인스턴스로 자동 변환
    transformOptions: {
      enableImplicitConversion: true, // @Type() 없이도 타입 변환
    },
  }),
);
```

### Validation 실패 시 디버깅

Validation 에러 메시지가 부족할 때가 있다. `exceptionFactory`를 커스터마이즈하면 어떤 필드에서 어떤 규칙이 실패했는지 명확하게 볼 수 있다.

```typescript
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,
    transform: true,
    exceptionFactory: (errors: ValidationError[]) => {
      const messages = errors.map((error) => {
        const constraints = error.constraints
          ? Object.values(error.constraints)
          : ['알 수 없는 검증 오류'];
        return {
          field: error.property,
          value: error.value,
          errors: constraints,
        };
      });
      return new BadRequestException({
        message: 'Validation 실패',
        details: messages,
      });
    },
  }),
);
```

이렇게 하면 응답이 다음과 같이 나온다.

```json
{
  "message": "Validation 실패",
  "details": [
    {
      "field": "email",
      "value": "not-an-email",
      "errors": ["email must be an email"]
    }
  ]
}
```

### 커스텀 Pipe

특정 파라미터에 대해 커스텀 변환이 필요한 경우에 쓴다.

```typescript
@Injectable()
export class ParseDatePipe implements PipeTransform<string, Date> {
  transform(value: string, metadata: ArgumentMetadata): Date {
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      throw new BadRequestException(
        `'${value}'는 유효한 날짜 형식이 아닙니다`,
      );
    }
    return date;
  }
}
```

```typescript
@Get('logs')
findLogs(
  @Query('from', ParseDatePipe) from: Date,
  @Query('to', ParseDatePipe) to: Date,
) {
  return this.logService.findBetween(from, to);
}
```

### 흔한 실수

**`transform: true` 빼먹기**: 이 옵션 없이 `@Param('id', ParseIntPipe) id: number`를 쓰면 ParseIntPipe가 변환은 하지만, 핸들러에 도달할 때 여전히 문자열일 수 있다. `transform: true`를 전역으로 설정해두는 게 편하다.

**`whitelist: true`만 쓰고 `forbidNonWhitelisted`를 안 쓰는 경우**: `whitelist`만 쓰면 DTO에 없는 필드를 조용히 제거한다. 클라이언트 입장에서는 보낸 데이터가 왜 반영되지 않는지 알 수 없다. `forbidNonWhitelisted: true`를 같이 써야 잘못된 필드를 보냈다는 에러를 받을 수 있다.

**중첩 객체 Validation**: DTO 안에 다른 DTO가 있으면 `@ValidateNested()`와 `@Type(() => ChildDto)`를 같이 써야 한다. 이걸 빼먹으면 중첩 객체 내부의 검증이 동작하지 않는다.

```typescript
export class CreateOrderDto {
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];
}
```


## ExecutionContext 활용

Guard와 Interceptor에서 받는 `ExecutionContext`는 현재 실행 중인 요청에 대한 정보를 담고 있다. 어떤 컨트롤러의 어떤 핸들러가 호출될 예정인지, HTTP/WebSocket/RPC 중 어떤 컨텍스트인지 확인할 수 있다.

### 주요 메서드

```typescript
// 핸들러 함수 참조
const handler = context.getHandler();   // e.g., findAllUsers

// 컨트롤러 클래스 참조
const controller = context.getClass();  // e.g., AdminController

// 요청 타입 확인
const type = context.getType();         // 'http' | 'ws' | 'rpc'

// HTTP 요청/응답 객체 접근
const request = context.switchToHttp().getRequest();
const response = context.switchToHttp().getResponse();
```

### 메타데이터와 함께 활용

`Reflector`를 통해 데코레이터로 설정한 메타데이터를 읽을 수 있다. Guard에서 역할을 확인하거나, Interceptor에서 캐시 TTL을 확인하는 등의 패턴에서 쓴다.

```typescript
// 커스텀 데코레이터 정의
export const Public = () => SetMetadata('isPublic', true);

// Guard에서 활용
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private reflector: Reflector) {
    super();
  }

  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>('isPublic', [
      context.getHandler(),
      context.getClass(),
    ]);

    if (isPublic) {
      return true; // @Public() 데코레이터가 붙은 핸들러는 인증 생략
    }

    return super.canActivate(context);
  }
}
```

```typescript
@Controller('posts')
@UseGuards(JwtAuthGuard)
export class PostsController {
  @Public()
  @Get()
  findAll() {
    // 인증 없이 접근 가능
    return this.postsService.findAll();
  }

  @Post()
  create(@Body() dto: CreatePostDto) {
    // JWT 인증 필요
    return this.postsService.create(dto);
  }
}
```

### HTTP 외 컨텍스트

WebSocket이나 마이크로서비스를 같은 Guard/Interceptor로 처리해야 할 때, `getType()`으로 분기할 수 있다.

```typescript
canActivate(context: ExecutionContext): boolean {
  if (context.getType() === 'http') {
    const request = context.switchToHttp().getRequest();
    return this.validateHttpRequest(request);
  }

  if (context.getType() === 'ws') {
    const client = context.switchToWs().getClient();
    return this.validateWsClient(client);
  }

  // RPC
  const data = context.switchToRpc().getData();
  return this.validateRpcData(data);
}
```


## Exception Filter

핸들러나 각 레이어에서 발생한 예외를 잡아 응답으로 변환하는 레이어다. 라이프사이클 마지막에 위치한다.

```typescript
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger('Exception');

  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = exception.getStatus();
    const exceptionResponse = exception.getResponse();

    const body = {
      statusCode: status,
      path: request.url,
      method: request.method,
      message:
        typeof exceptionResponse === 'string'
          ? exceptionResponse
          : (exceptionResponse as any).message,
      timestamp: new Date().toISOString(),
    };

    this.logger.error(
      `${request.method} ${request.url} ${status} - ${JSON.stringify(body.message)}`,
    );

    response.status(status).json(body);
  }
}
```

### 주의사항

`@Catch()` 데코레이터에 인자를 안 넣으면 모든 예외를 잡는다. 특정 예외만 처리하고 싶으면 반드시 타입을 명시해야 한다. 모든 예외를 잡는 전역 필터를 만들 때는 NestJS가 내부적으로 사용하는 예외까지 잡아버릴 수 있으니, `HttpException`이 아닌 경우에 대한 처리를 분리해야 한다.


## 전체 레이어 적용 범위 정리

각 레이어를 적용할 수 있는 범위가 다르다.

| 레이어 | Global | Controller | Handler |
|--------|--------|------------|---------|
| Middleware | O (app.use) | O (module configure) | O (forRoutes 지정) |
| Guard | O (useGlobalGuards) | O (@UseGuards) | O (@UseGuards) |
| Interceptor | O (useGlobalInterceptors) | O (@UseInterceptors) | O (@UseInterceptors) |
| Pipe | O (useGlobalPipes) | O (@UsePipes) | O (파라미터 단위) |
| Filter | O (useGlobalFilters) | O (@UseFilters) | O (@UseFilters) |

전역으로 등록하면 모든 라우트에 적용되지만, DI 컨테이너 밖에서 생성되기 때문에 의존성 주입이 안 된다. DI가 필요한 전역 Guard/Interceptor/Pipe/Filter는 `APP_GUARD`, `APP_INTERCEPTOR`, `APP_PIPE`, `APP_FILTER` 토큰을 사용해 모듈에서 등록해야 한다.

```typescript
@Module({
  providers: [
    {
      provide: APP_GUARD,
      useClass: RolesGuard,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
```

이렇게 하면 전역 적용이면서도 `Reflector` 같은 의존성을 주입받을 수 있다.


## 실무에서 자주 겪는 문제

### Guard에서 throw한 에러가 Interceptor의 catchError에 잡히지 않는 경우

Guard는 Interceptor보다 먼저 실행된다. Guard에서 예외가 발생하면 Interceptor는 아예 실행되지 않는다. Guard 단계의 에러를 잡으려면 Exception Filter에서 처리해야 한다.

### Pipe에서 변환한 값이 핸들러에 안 들어오는 경우

`@Body()` 데코레이터 없이 파라미터를 선언하면 Pipe가 적용되지 않는다. 당연한 것 같지만, 파라미터 데코레이터를 빼먹은 채 "왜 validation이 안 되지?"라고 삽질하는 경우가 의외로 많다.

```typescript
// 잘못된 코드 - Pipe 미적용
@Post()
create(dto: CreateUserDto) { ... }

// 올바른 코드
@Post()
create(@Body() dto: CreateUserDto) { ... }
```

### 여러 Interceptor의 실행 순서 혼동

`@UseInterceptors(A, B, C)`로 등록하면 before 순서는 A → B → C이고, after 순서는 C → B → A다. `tap`이나 `map` 연산자의 실행 순서가 예상과 다르다면 Interceptor 등록 순서를 확인한다.

### Global Guard에서 Reflector가 undefined

`app.useGlobalGuards(new RolesGuard())`로 등록하면 DI 컨테이너 밖에서 인스턴스가 생성되므로 `Reflector`가 주입되지 않는다. `APP_GUARD` 토큰을 사용해야 한다.
