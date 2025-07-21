# NestJS 사용법 가이드

## 목차
1. [NestJS 소개](#nestjs-소개)
2. [설치 및 설정](#설치-및-설정)
3. [기본 명령어](#기본-명령어)
4. [프로젝트 구조](#프로젝트-구조)
5. [핵심 개념](#핵심-개념)
6. [실제 사용 예제](#실제-사용-예제)
7. [배포 및 운영](#배포-및-운영)

## NestJS 소개

NestJS는 Node.js를 위한 진보적인 프레임워크로, 효율적이고 확장 가능한 서버 사이드 애플리케이션을 구축하기 위해 설계되었습니다. TypeScript를 완전히 지원하며, 객체지향 프로그래밍, 함수형 프로그래밍, 함수형 반응형 프로그래밍의 요소들을 결합합니다.

### 주요 특징
- **TypeScript 우선**: 완전한 TypeScript 지원
- **의존성 주입**: 강력한 DI 컨테이너
- **모듈화**: 모듈 기반 아키텍처
- **데코레이터**: 메타데이터 기반 프로그래밍
- **OpenAPI**: 자동 API 문서 생성
- **테스트**: Jest 기반 테스트 지원



### 코드 생성 명령어

#### 1. 컨트롤러 생성
```bash
# 컨트롤러 생성
nest generate controller [name]
nest g co [name]

# 예시
nest g co users
```

**실행 결과:**
```
CREATE src/users/users.controller.spec.ts (478 bytes)
CREATE src/users/users.controller.ts (89 bytes)
UPDATE src/app.module.ts (312 bytes)
```

**생성된 파일:**
```typescript
// src/users/users.controller.ts
import { Controller } from '@nestjs/common';

@Controller('users')
export class UsersController {}
```

#### 2. 서비스 생성
```bash
# 서비스 생성
nest generate service [name]
nest g s [name]

# 예시
nest g s users
```

**실행 결과:**
```
CREATE src/users/users.service.spec.ts (453 bytes)
CREATE src/users/users.service.ts (25 bytes)
UPDATE src/app.module.ts (312 bytes)
```

**생성된 파일:**
```typescript
// src/users/users.service.ts
import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {}
```

#### 3. 모듈 생성
```bash
# 모듈 생성
nest generate module [name]
nest g mo [name]

# 예시
nest g mo users
```

**실행 결과:**
```
CREATE src/users/users.module.ts (83 bytes)
UPDATE src/app.module.ts (312 bytes)
```

**생성된 파일:**
```typescript
// src/users/users.module.ts
import { Module } from '@nestjs/common';

@Module({})
export class UsersModule {}
```

#### 4. 가드 생성
```bash
# 가드 생성
nest generate guard [name]
nest g gu [name]

# 예시
nest g gu auth
```

**실행 결과:**
```
CREATE src/auth/auth.guard.spec.ts (456 bytes)
CREATE src/auth/auth.guard.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/auth/auth.guard.ts
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    return true;
  }
}
```

#### 5. 인터셉터 생성
```bash
# 인터셉터 생성
nest generate interceptor [name]
nest g in [name]

# 예시
nest g in logging
```

**실행 결과:**
```
CREATE src/logging/logging.interceptor.spec.ts (489 bytes)
CREATE src/logging/logging.interceptor.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/logging/logging.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle();
  }
}
```

#### 6. 파이프 생성
```bash
# 파이프 생성
nest generate pipe [name]
nest g pi [name]

# 예시
nest g pi validation
```

**실행 결과:**
```
CREATE src/validation/validation.pipe.spec.ts (456 bytes)
CREATE src/validation/validation.pipe.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/validation/validation.pipe.ts
import { Injectable, PipeTransform, ArgumentMetadata } from '@nestjs/common';

@Injectable()
export class ValidationPipe implements PipeTransform {
  transform(value: any, metadata: ArgumentMetadata) {
    return value;
  }
}
```

#### 7. 필터 생성
```bash
# 필터 생성
nest generate filter [name]
nest g f [name]

# 예시
nest g f http-exception
```

**실행 결과:**
```
CREATE src/http-exception/http-exception.filter.spec.ts (456 bytes)
CREATE src/http-exception/http-exception.filter.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/http-exception/http-exception.filter.ts
import { ExceptionFilter, Catch, ArgumentsHost, HttpException } from '@nestjs/common';
import { Response } from 'express';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const status = exception.getStatus();
    const exceptionResponse = exception.getResponse();

    response
      .status(status)
      .json({
        statusCode: status,
        timestamp: new Date().toISOString(),
        message: exceptionResponse,
      });
  }
}
```

#### 8. 미들웨어 생성
```bash
# 미들웨어 생성
nest generate middleware [name]
nest g mi [name]

# 예시
nest g mi logger
```

**실행 결과:**
```
CREATE src/logger/logger.middleware.spec.ts (456 bytes)
CREATE src/logger/logger.middleware.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/logger/logger.middleware.ts
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    console.log('Request...');
    next();
  }
}
```

#### 9. 리졸버 생성 (GraphQL)
```bash
# 리졸버 생성 (GraphQL)
nest generate resolver [name]
nest g r [name]

# 예시
nest g r users
```

**실행 결과:**
```
CREATE src/users/users.resolver.spec.ts (456 bytes)
CREATE src/users/users.resolver.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/users/users.resolver.ts
import { Resolver, Query } from '@nestjs/graphql';

@Resolver()
export class UsersResolver {
  @Query()
  getUsers() {
    return 'This action returns all users';
  }
}
```

#### 10. 게이트웨이 생성 (WebSockets)
```bash
# 게이트웨이 생성 (WebSockets)
nest generate gateway [name]
nest g ga [name]

# 예시
nest g ga chat
```

**실행 결과:**
```
CREATE src/chat/chat.gateway.spec.ts (456 bytes)
CREATE src/chat/chat.gateway.ts (26 bytes)
```

**생성된 파일:**
```typescript
// src/chat/chat.gateway.ts
import {
  SubscribeMessage,
  WebSocketGateway,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import { Socket } from 'socket.io';

@WebSocketGateway()
export class ChatGateway implements OnGatewayConnection, OnGatewayDisconnect {
  handleConnection(client: Socket) {
    console.log('Client connected:', client.id);
  }

  handleDisconnect(client: Socket) {
    console.log('Client disconnected:', client.id);
  }

  @SubscribeMessage('message')
  handleMessage(client: Socket, payload: any): void {
    console.log('Message received:', payload);
  }
}
```

### 개발 서버 명령어

```bash


# 빌드
npm run build

# 테스트 실행
npm run test
npm run test:e2e
npm run test:cov
```

## 프로젝트 구조

### 기본 디렉토리 구조

```
src/
├── app.controller.ts          # 기본 컨트롤러
├── app.service.ts            # 기본 서비스
├── app.module.ts             # 루트 모듈
├── main.ts                   # 애플리케이션 엔트리 포인트
└── [feature]/                # 기능별 디렉토리
    ├── [feature].controller.ts
    ├── [feature].service.ts
    ├── [feature].module.ts
    └── dto/
        └── [feature].dto.ts
```

### 권장 프로젝트 구조

```
src/
├── common/                   # 공통 모듈
│   ├── decorators/
│   ├── filters/
│   ├── guards/
│   ├── interceptors/
│   └── pipes/
├── config/                   # 설정 파일
│   ├── database.config.ts
│   └── app.config.ts
├── modules/                  # 기능별 모듈
│   ├── users/
│   │   ├── dto/
│   │   ├── entities/
│   │   ├── users.controller.ts
│   │   ├── users.service.ts
│   │   └── users.module.ts
│   └── auth/
│       ├── dto/
│       ├── guards/
│       ├── auth.controller.ts
│       ├── auth.service.ts
│       └── auth.module.ts
├── database/                 # 데이터베이스 관련
│   ├── migrations/
│   └── seeds/
├── app.controller.ts
├── app.service.ts
├── app.module.ts
└── main.ts
```

## 핵심 개념

### 1. 모듈 (Modules)

모듈은 애플리케이션의 구성 요소를 그룹화하는 방법입니다.

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { UsersModule } from './modules/users/users.module';

@Module({
  imports: [UsersModule],
  controllers: [AppController],
  providers: [AppService],
  exports: [AppService], // 다른 모듈에서 사용할 수 있도록 내보내기
})
export class AppModule {}
```

### 2. 컨트롤러 (Controllers)

컨트롤러는 들어오는 요청을 처리하고 클라이언트에 응답을 반환합니다.

```typescript
// users.controller.ts
import { Controller, Get, Post, Body, Param, Put, Delete } from '@nestjs/common';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';

@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() createUserDto: CreateUserDto) {
    return this.usersService.create(createUserDto);
  }

  @Get()
  findAll() {
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.usersService.findOne(+id);
  }

  @Put(':id')
  update(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto) {
    return this.usersService.update(+id, updateUserDto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.usersService.remove(+id);
  }
}
```

### 3. 서비스 (Services)

서비스는 비즈니스 로직을 포함하는 클래스입니다.

```typescript
// users.service.ts
import { Injectable, NotFoundException } from '@nestjs/common';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';

@Injectable()
export class UsersService {
  private users = [];

  create(createUserDto: CreateUserDto) {
    const user = { id: Date.now(), ...createUserDto };
    this.users.push(user);
    return user;
  }

  findAll() {
    return this.users;
  }

  findOne(id: number) {
    const user = this.users.find(user => user.id === id);
    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    return user;
  }

  update(id: number, updateUserDto: UpdateUserDto) {
    const index = this.users.findIndex(user => user.id === id);
    if (index === -1) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    this.users[index] = { ...this.users[index], ...updateUserDto };
    return this.users[index];
  }

  remove(id: number) {
    const index = this.users.findIndex(user => user.id === id);
    if (index === -1) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    const removedUser = this.users.splice(index, 1)[0];
    return removedUser;
  }
}
```

### 4. DTO (Data Transfer Objects)

DTO는 데이터 전송 객체로, 요청과 응답의 데이터 구조를 정의합니다.

```typescript
// dto/create-user.dto.ts
import { IsEmail, IsString, MinLength } from 'class-validator';

export class CreateUserDto {
  @IsString()
  @MinLength(2)
  name: string;

  @IsEmail()
  email: string;

  @IsString()
  @MinLength(6)
  password: string;
}
```

```typescript
// dto/update-user.dto.ts
import { PartialType } from '@nestjs/mapped-types';
import { CreateUserDto } from './create-user.dto';

export class UpdateUserDto extends PartialType(CreateUserDto) {}
```

### 5. 가드 (Guards)

가드는 라우트 핸들러가 실행되기 전에 인증, 권한 등을 확인합니다.

```typescript
// guards/auth.guard.ts
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    const request = context.switchToHttp().getRequest();
    // 인증 로직 구현
    return true;
  }
}
```

### 6. 인터셉터 (Interceptors)

인터셉터는 요청/응답을 변환하거나 추가 로직을 실행할 수 있습니다.

```typescript
// interceptors/logging.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const now = Date.now();
    return next
      .handle()
      .pipe(
        tap(() => console.log(`Execution time: ${Date.now() - now}ms`)),
      );
  }
}
```

### 7. 파이프 (Pipes)

파이프는 데이터 변환과 유효성 검사를 담당합니다.

```typescript
// pipes/validation.pipe.ts
import { PipeTransform, Injectable, ArgumentMetadata, BadRequestException } from '@nestjs/common';
import { validate } from 'class-validator';
import { plainToClass } from 'class-transformer';

@Injectable()
export class ValidationPipe implements PipeTransform<any> {
  async transform(value: any, { metatype }: ArgumentMetadata) {
    if (!metatype || !this.toValidate(metatype)) {
      return value;
    }
    const object = plainToClass(metatype, value);
    const errors = await validate(object);
    if (errors.length > 0) {
      throw new BadRequestException('Validation failed');
    }
    return value;
  }

  private toValidate(metatype: Function): boolean {
    const types: Function[] = [String, Boolean, Number, Array, Object];
    return !types.includes(metatype);
  }
}
```

## 실제 사용 예제

### 1. 데이터베이스 연동 (TypeORM)

```bash
# TypeORM 설치
npm install @nestjs/typeorm typeorm mysql2
```

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { UsersModule } from './modules/users/users.module';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'password',
      database: 'test',
      entities: [__dirname + '/**/*.entity{.ts,.js}'],
      synchronize: true, // 개발 환경에서만 사용
    }),
    UsersModule,
  ],
})
export class AppModule {}
```

### 2. 환경 변수 설정

```bash
# 환경 변수 패키지 설치
npm install @nestjs/config
```

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    // 다른 모듈들...
  ],
})
export class AppModule {}
```

### 3. JWT 인증 구현

```bash
# JWT 패키지 설치
npm install @nestjs/jwt @nestjs/passport passport passport-jwt
npm install -D @types/passport-jwt
```

```typescript
// auth/auth.module.ts
import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { AuthService } from './auth.service';
import { AuthController } from './auth.controller';
import { JwtStrategy } from './jwt.strategy';

@Module({
  imports: [
    PassportModule,
    JwtModule.register({
      secret: 'your-secret-key',
      signOptions: { expiresIn: '1h' },
    }),
  ],
  providers: [AuthService, JwtStrategy],
  controllers: [AuthController],
  exports: [AuthService],
})
export class AuthModule {}
```

### 4. API 문서화 (Swagger)

```bash
# Swagger 패키지 설치
npm install @nestjs/swagger swagger-ui-express
```

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const config = new DocumentBuilder()
    .setTitle('Users API')
    .setDescription('The users API description')
    .setVersion('1.0')
    .addTag('users')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api', app, document);

  await app.listen(3000);
}
bootstrap();
```

## 배포 및 운영

### 1. 프로덕션 빌드

```bash
# 프로덕션 빌드
npm run build

# 프로덕션 실행
npm run start:prod
```

### 2. Docker 배포

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist ./dist

EXPOSE 3000

CMD ["node", "dist/main"]
```

```bash
# Docker 이미지 빌드
docker build -t my-nest-app .

# Docker 컨테이너 실행
docker run -p 3000:3000 my-nest-app
```

### 3. PM2를 사용한 프로세스 관리

```bash
# PM2 설치
npm install -g pm2

# PM2로 애플리케이션 실행
pm2 start dist/main.js --name "nest-app"

# PM2 상태 확인
pm2 status

# PM2 로그 확인
pm2 logs nest-app
```

### 4. 환경별 설정

```typescript
// config/configuration.ts
export default () => ({
  port: parseInt(process.env.PORT, 10) || 3000,
  database: {
    host: process.env.DATABASE_HOST,
    port: parseInt(process.env.DATABASE_PORT, 10) || 5432,
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '1h',
  },
});
```

## 유용한 팁

### 1. 개발 생산성 향상

```bash
# 파일 변경 감지로 자동 재시작
npm run start:dev

# 디버그 모드로 실행
npm run start:debug

# 테스트 커버리지 확인
npm run test:cov
```

### 2. 코드 품질 관리

```bash
# ESLint 설치 및 설정
npm install -D @nestjs/eslint-plugin eslint

# Prettier 설치 및 설정
npm install -D prettier

# Husky로 Git hooks 설정
npm install -D husky lint-staged
```

### 3. 성능 최적화

```typescript
// 캐싱 구현
import { CacheModule } from '@nestjs/cache-manager';

@Module({
  imports: [
    CacheModule.register({
      ttl: 60000, // 1분
      max: 100, // 최대 100개 항목
    }),
  ],
})
export class AppModule {}
```
