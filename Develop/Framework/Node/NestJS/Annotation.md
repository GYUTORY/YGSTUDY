# NestJS Annotation 가이드

## 목차
1. [소개](#소개)
2. [기본 데코레이터](#기본-데코레이터)
3. [컨트롤러 데코레이터](#컨트롤러-데코레이터)
4. [프로바이더 데코레이터](#프로바이더-데코레이터)
5. [미들웨어 데코레이터](#미들웨어-데코레이터)
6. [예외 필터 데코레이터](#예외-필터-데코레이터)
7. [파이프 데코레이터](#파이프-데코레이터)
8. [가드 데코레이터](#가드-데코레이터)
9. [인터셉터 데코레이터](#인터셉터-데코레이터)
10. [사용자 정의 데코레이터](#사용자-정의-데코레이터)

## 소개

NestJS는 TypeScript로 작성된 Node.js 프레임워크로, 데코레이터(Annotation)를 적극적으로 활용하여 코드의 가독성과 유지보수성을 높입니다. 데코레이터는 클래스, 메서드, 프로퍼티에 메타데이터를 추가하는 기능을 제공하며, 이를 통해 의존성 주입, 라우팅, 미들웨어 등 다양한 기능을 선언적으로 구현할 수 있습니다.

## 기본 데코레이터

### @Module()
모듈은 NestJS 애플리케이션의 기본 구성 단위입니다. 관련된 기능들을 하나의 단위로 묶어주는 역할을 합니다.

```typescript
@Module({
  imports: [], // 다른 모듈을 가져올 때 사용
  controllers: [], // 컨트롤러 선언
  providers: [], // 프로바이더(서비스 등) 선언
  exports: [] // 다른 모듈에서 사용할 프로바이더 선언
})
export class AppModule {}
```

### @Injectable()
서비스나 프로바이더 클래스를 선언할 때 사용하는 데코레이터입니다.

```typescript
@Injectable()
export class UsersService {
  constructor() {}
}
```

## 컨트롤러 데코레이터

### @Controller()
HTTP 요청을 처리하는 컨트롤러를 선언합니다.

```typescript
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}
}
```

### HTTP 메서드 데코레이터
- @Get()
- @Post()
- @Put()
- @Delete()
- @Patch()
- @Options()
- @Head()

```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll(): User[] {
    return this.usersService.findAll();
  }

  @Post()
  create(@Body() createUserDto: CreateUserDto): User {
    return this.usersService.create(createUserDto);
  }
}
```

### 요청 객체 데코레이터
- @Body() - 요청 본문
- @Param() - URL 파라미터
- @Query() - 쿼리 파라미터
- @Headers() - HTTP 헤더
- @Ip() - 요청 IP
- @Session() - 세션 객체

```typescript
@Get(':id')
findOne(
  @Param('id') id: string,
  @Query('include') include: string,
  @Headers('authorization') auth: string
) {
  return this.usersService.findOne(id);
}
```

## 프로바이더 데코레이터

### @Injectable()
서비스나 프로바이더를 선언할 때 사용합니다.

```typescript
@Injectable()
export class UsersService {
  constructor(
    @Inject('DATABASE_CONNECTION')
    private readonly connection: Connection
  ) {}
}
```

### @Inject()
의존성 주입 시 특정 토큰을 사용하여 주입할 때 사용합니다.

```typescript
@Injectable()
export class ConfigService {
  constructor(
    @Inject('CONFIG_OPTIONS')
    private readonly options: ConfigOptions
  ) {}
}
```

## 미들웨어 데코레이터

### @Injectable()
미들웨어 클래스를 선언할 때 사용합니다.

```typescript
@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: Function) {
    console.log('Request...');
    next();
  }
}
```

## 예외 필터 데코레이터

### @Catch()
예외 필터를 선언할 때 사용합니다.

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

## 파이프 데코레이터

### @UsePipes()
컨트롤러나 라우트 핸들러에 파이프를 적용할 때 사용합니다.

```typescript
@Post()
@UsePipes(new ValidationPipe())
create(@Body() createUserDto: CreateUserDto) {
  return this.usersService.create(createUserDto);
}
```

## 가드 데코레이터

### @UseGuards()
인증이나 권한 검사를 위한 가드를 적용할 때 사용합니다.

```typescript
@Get('profile')
@UseGuards(AuthGuard)
getProfile(@Request() req) {
  return req.user;
}
```

## 인터셉터 데코레이터

### @UseInterceptors()
요청/응답을 가로채서 변환하거나 로깅하는 인터셉터를 적용할 때 사용합니다.

```typescript
@Get()
@UseInterceptors(LoggingInterceptor)
findAll() {
  return this.usersService.findAll();
}
```

## 사용자 정의 데코레이터

### 커스텀 데코레이터 생성
필요에 따라 사용자 정의 데코레이터를 만들 수 있습니다.

```typescript
export const User = createParamDecorator(
  (data: string, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;

    return data ? user?.[data] : user;
  },
);

// 사용 예시
@Get('profile')
getProfile(@User() user: UserEntity) {
  return user;
}
```

## 메타데이터 데코레이터

### @SetMetadata()
커스텀 메타데이터를 설정할 때 사용합니다.

```typescript
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

@Get()
@Roles('admin')
findAll() {
  return this.usersService.findAll();
}
```

## 결론

NestJS의 데코레이터는 강력한 기능을 제공하며, 이를 통해 코드의 가독성과 유지보수성을 크게 향상시킬 수 있습니다. 위에서 설명한 데코레이터들을 적절히 활용하면, 깔끔하고 확장 가능한 애플리케이션을 구축할 수 있습니다.

각 데코레이터는 특정한 목적을 가지고 있으며, 상황에 맞게 적절히 사용하는 것이 중요합니다. 또한, 필요에 따라 커스텀 데코레이터를 만들어 사용할 수 있다는 점도 NestJS의 큰 장점 중 하나입니다.
