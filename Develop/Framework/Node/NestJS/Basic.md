# NestJS 핵심 개념 가이드

## Express와 NestJS의 차이점

### 1. 아키텍처 패턴
- **Express**: 
  - 미니멀리스트 프레임워크로, 자유도가 높지만 구조화된 아키텍처를 제공하지 않음
  - 개발자가 직접 구조를 설계해야 함
  - 미들웨어 기반의 단순한 라우팅 시스템

- **NestJS**:
  - Angular에서 영감을 받은 구조화된 아키텍처 제공
  - 모듈, 컨트롤러, 서비스 등 명확한 구조화된 패턴 제공
  - TypeScript 기반으로 타입 안정성 보장
  - 의존성 주입(DI) 시스템 내장

### 2. 개발 생산성
- **Express**:
  - 빠른 프로토타이핑에 적합
  - 작은 규모의 프로젝트에 유리
  - 보일러플레이트 코드 작성 필요

- **NestJS**:
  - CLI 도구를 통한 빠른 개발 환경 구축
  - 자동 생성된 코드로 개발 시간 단축
  - 대규모 프로젝트에 적합한 구조화된 개발 방식

## NestJS의 핵심 개념

### 1. 모듈 (Modules)
모듈은 NestJS 애플리케이션의 기본 구성 단위입니다.

```typescript
@Module({
  imports: [], // 다른 모듈 가져오기
  controllers: [], // 컨트롤러 선언
  providers: [], // 서비스, 팩토리 등 선언
  exports: [] // 다른 모듈에서 사용할 수 있도록 내보내기
})
export class AppModule {}
```

#### 모듈의 특징
- 각 모듈은 캡슐화된 기능 단위
- 모듈 간의 명확한 경계 설정
- 재사용 가능한 기능 단위로 구성
- 의존성 주입의 기본 단위

### 2. 컨트롤러 (Controllers)
컨트롤러는 들어오는 요청을 처리하고 클라이언트에 응답을 반환하는 역할을 합니다.

```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll(): string {
    return '모든 사용자 조회';
  }

  @Get(':id')
  findOne(@Param('id') id: string): string {
    return `사용자 ${id} 조회`;
  }

  @Post()
  create(@Body() createUserDto: CreateUserDto): string {
    return '새 사용자 생성';
  }
}
```

#### 주요 데코레이터
- `@Controller()`: 컨트롤러 클래스 정의
- `@Get()`, `@Post()`, `@Put()`, `@Delete()`: HTTP 메서드 매핑
- `@Param()`: URL 파라미터 추출
- `@Body()`: 요청 본문 데이터 추출
- `@Query()`: 쿼리 파라미터 추출
- `@Headers()`: 요청 헤더 추출

### 3. 프로바이더 (Providers)
프로바이더는 NestJS의 기본 개념으로, 서비스, 리포지토리, 팩토리 등을 포함합니다.

```typescript
@Injectable()
export class UsersService {
  private readonly users: User[] = [];

  findAll(): User[] {
    return this.users;
  }

  findOne(id: number): User {
    return this.users.find(user => user.id === id);
  }

  create(user: CreateUserDto): User {
    const newUser = { id: Date.now(), ...user };
    this.users.push(newUser);
    return newUser;
  }
}
```

#### 프로바이더의 특징
- `@Injectable()` 데코레이터로 표시
- 의존성 주입 시스템의 핵심
- 싱글톤으로 관리됨
- 테스트 용이성 제공

### 4. 미들웨어 (Middleware)
미들웨어는 라우트 핸들러 이전에 실행되는 함수입니다.

```typescript
@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: Function) {
    console.log('Request...');
    next();
  }
}
```

#### 미들웨어 적용 방법
```typescript
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('users');
  }
}
```

### 5. 예외 필터 (Exception Filters)
예외 처리를 위한 필터를 제공합니다.

```typescript
@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const status = exception.getStatus();

    response
      .status(status)
      .json({
        statusCode: status,
        timestamp: new Date().toISOString(),
        message: exception.message,
      });
  }
}
```

### 6. 파이프 (Pipes)
입력 데이터의 변환과 유효성 검사를 담당합니다.

```typescript
@Post()
async create(@Body(new ValidationPipe()) createUserDto: CreateUserDto) {
  return this.usersService.create(createUserDto);
}
```

#### 내장 파이프
- `ValidationPipe`: DTO 유효성 검사
- `ParseIntPipe`: 문자열을 정수로 변환
- `ParseBoolPipe`: 문자열을 불리언으로 변환
- `ParseArrayPipe`: 배열 데이터 처리
- `ParseUUIDPipe`: UUID 문자열 검증

### 7. 가드 (Guards)
요청이 라우트 핸들러에 의해 처리될지 여부를 결정합니다.

```typescript
@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return validateRequest(request);
  }
}
```

### 8. 인터셉터 (Interceptors)
메서드 실행 전후에 추가 로직을 바인딩할 수 있습니다.

```typescript
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    console.log('Before...');
    const now = Date.now();
    return next
      .handle()
      .pipe(
        tap(() => console.log(`After... ${Date.now() - now}ms`)),
      );
  }
}
```

### 9. 커스텀 데코레이터 (Custom Decorators)
자주 사용되는 로직을 데코레이터로 추상화할 수 있습니다.

```typescript
export const User = createParamDecorator(
  (data: string, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);
```

### 10. 환경 설정 (Configuration)
환경 변수와 설정을 관리하는 방법을 제공합니다.

```typescript
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
  ],
})
export class AppModule {}
```

### 11. 데이터베이스 통합
TypeORM, Mongoose 등 다양한 데이터베이스와의 통합을 지원합니다.

```typescript
@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: 'localhost',
      port: 5432,
      username: 'user',
      password: 'password',
      database: 'db',
      entities: [User],
      synchronize: true,
    }),
  ],
})
export class AppModule {}
```

### 12. 웹소켓 (WebSockets)
실시간 양방향 통신을 위한 웹소켓 지원을 제공합니다.

```typescript
@WebSocketGateway()
export class EventsGateway {
  @WebSocketServer()
  server: Server;

  @SubscribeMessage('events')
  handleEvent(@MessageBody() data: string): string {
    return data;
  }
}
```

### 13. GraphQL 지원
GraphQL API를 쉽게 구현할 수 있는 기능을 제공합니다.

```typescript
@Resolver(of => User)
export class UsersResolver {
  constructor(private usersService: UsersService) {}

  @Query(returns => User)
  async user(@Args('id') id: number) {
    return this.usersService.findOne(id);
  }
}
```

### 14. 테스트
단위 테스트와 E2E 테스트를 위한 도구를 제공합니다.

```typescript
describe('UsersController', () => {
  let controller: UsersController;
  let service: UsersService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
      providers: [UsersService],
    }).compile();

    controller = module.get<UsersController>(UsersController);
    service = module.get<UsersService>(UsersService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
```

## NestJS의 장점

1. **구조화된 아키텍처**
   - 명확한 디렉토리 구조
   - 모듈화된 코드 구성
   - 확장 가능한 설계

2. **TypeScript 지원**
   - 타입 안정성
   - 향상된 개발자 경험
   - 더 나은 IDE 지원

3. **의존성 주입**
   - 느슨한 결합
   - 테스트 용이성
   - 코드 재사용성

4. **풍부한 생태계**
   - 다양한 내장 기능
   - 확장 가능한 구조
   - 활발한 커뮤니티

5. **엔터프라이즈급 기능**
   - 미들웨어
   - 예외 처리
   - 유효성 검사
   - 보안 기능

## 결론

NestJS는 현대적인 Node.js 애플리케이션 개발을 위한 강력한 프레임워크입니다. Express의 단순함을 유지하면서도, 엔터프라이즈급 애플리케이션 개발에 필요한 구조와 기능을 제공합니다. TypeScript를 기반으로 하여 타입 안정성을 보장하고, 의존성 주입을 통한 모듈화된 개발을 가능하게 합니다.

대규모 프로젝트나 팀 단위 개발에서 특히 유용하며, Angular와 유사한 구조로 인해 프론트엔드 개발자들도 쉽게 적응할 수 있습니다. 또한, 다양한 데이터베이스 통합과 웹소켓, GraphQL 등 현대적인 웹 개발에 필요한 기능들을 모두 제공합니다.
