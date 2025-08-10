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

---

# 부록: NestJS 마이크로서비스 통신(gRPC/RabbitMQ)

자세한 정리는 별도 문서에 모았다: [Microservices_Communication.md](./Microservices_Communication.md)

NestJS는 HTTP 외에도 gRPC, 메시지 브로커(RabbitMQ 등)를 통해 마이크로서비스 간 통신을 쉽게 붙일 수 있다. 아래는 핵심만 간단히 정리했다.

## 1) gRPC 패턴

개념
- gRPC는 프로토콜 버퍼(proto)로 스키마를 정의하고, HTTP/2 위에서 바이너리로 주고받는다. 엄격한 스키마와 양방향 스트리밍이 장점이다.

proto 예시
```proto
syntax = "proto3";
package user.v1;

service UserService {
  rpc GetUser (GetUserRequest) returns (GetUserResponse);
}

message GetUserRequest { string id = 1; }
message GetUserResponse { string id = 1; string name = 2; }
```

서버 쪽
```ts
// user.module.ts
import { Module } from '@nestjs/common';
import { Transport, ClientsModule } from '@nestjs/microservices';

@Module({})
export class UserModule {}

// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.GRPC,
    options: {
      package: ['user.v1'],
      protoPath: ['proto/user.proto'],
      url: '0.0.0.0:50051',
    },
  });
  await app.listen();
}
bootstrap();
```

핸들러
```ts
import { Controller } from '@nestjs/common';
import { GrpcMethod } from '@nestjs/microservices';

@Controller()
export class UserController {
  @GrpcMethod('UserService', 'GetUser')
  getUser({ id }: { id: string }) {
    return { id, name: 'Alice' };
  }
}
```

클라이언트(다른 서비스)
```ts
import { ClientsModule, Transport } from '@nestjs/microservices';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'USER_GRPC',
        transport: Transport.GRPC,
        options: { package: 'user.v1', protoPath: 'proto/user.proto', url: 'user:50051' },
      },
    ]),
  ],
})
export class ApiModule {}
```

요점
- 스키마가 명확하고, 타입 생성기를 쓰면 DTO 동기화가 쉽다.
- HTTP/1.1 프록시 환경에선 gRPC가 막힐 수 있다(HTTP/2 필요).

## 2) RabbitMQ(메시지) 패턴

개념
- 서비스 간 직접 호출 대신 메시지 브로커에 발행/구독한다. 느슨한 결합과 버퍼링이 장점이다.

발행/구독 예시
```ts
// module
import { ClientsModule, Transport } from '@nestjs/microservices';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'RMQ',
        transport: Transport.RMQ,
        options: {
          urls: ['amqp://guest:guest@rabbitmq:5672'],
          queue: 'user.events',
          queueOptions: { durable: true },
        },
      },
    ]),
  ],
})
export class MessagingModule {}

// publisher
@Injectable()
export class UserPublisher {
  constructor(@Inject('RMQ') private readonly client: ClientProxy) {}
  userCreated(evt: { id: string; name: string }) {
    return this.client.emit('user.created', evt); // fire-and-forget
  }
}

// consumer
@Controller()
export class UserConsumer {
  @EventPattern('user.created')
  handleUserCreated(@Payload() data: any, @Ctx() ctx: RmqContext) {
    // 처리 후 수동 ack
    const ch = ctx.getChannelRef();
    const msg = ctx.getMessage();
    try {
      // ...업무 처리
      ch.ack(msg);
    } catch (e) {
      ch.nack(msg, false, true); // 재시도
    }
  }
}
```

요점
- 소비자는 실패 시 재시도/지연 큐를 활용해 복구 가능하도록 만든다.
- 순서가 엄격하면 파티션 키(예: userId)로 큐를 나누거나, 메시지에 순번을 붙여 검증한다.

## 3) 메시지 스키마 버저닝

시간이 지나면 이벤트의 필드가 늘거나 의미가 바뀐다. 스키마에 버전을 붙이고, 소비자는 하위 호환을 먼저 지원한다.

간단한 방법
- 이벤트 이름에 버전을 포함: `user.created.v1`, `user.created.v2`
- 페이로드 안에 `version` 필드 추가: `{ version: 2, id, name, nickname }`

이행 전략
- 생산자는 새 필드를 추가하되 기본값을 채워 하위 소비자가 깨지지 않게 한다.
- 소비자는 알 수 없는 필드는 무시하고, 누락 필드는 기본값을 채운다.

## 4) 멱등 처리(idempotency) 예시

메시지는 중복될 수 있다. 같은 메시지가 여러 번 와도 결과가 한 번만 반영되도록 만든다.

아이디어
- 메시지에 고유 ID를 넣고, 처리한 ID를 저장한다.
- DB에서 유니크 키를 활용해 중복 삽입을 막는다.

스니펫
```ts
// 테이블: processed_event(id text primary key, at timestamptz)
@Controller()
export class PaymentConsumer {
  constructor(private readonly repo: ProcessedEventRepo) {}

  @EventPattern('payment.captured')
  async handle(@Payload() evt: { id: string; orderId: string }) {
    const seen = await this.repo.exists(evt.id);
    if (seen) return;

    await this.repo.tx(async () => {
      await this.repo.insert(evt.id);
      await this.applyBusiness(evt);
    });
  }
}
```

용어 풀기
- 멱등성: 같은 입력을 여러 번 넣어도 결과가 변하지 않는 성질. 메시징에선 “중복 수신에도 부작용이 1회만 난다”는 뜻으로 쓴다.

---

## 무엇을 고를까

동기 RPC 스타일이면 gRPC가 깔끔하다. 느슨한 결합과 버퍼링이 필요하면 메시지 브로커가 맞다. 복합 시스템에선 둘을 섞는 일이 많다. 중요한 건 스키마와 멱등 처리를 일찍부터 함께 설계하는 것이다.
