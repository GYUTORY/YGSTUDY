---
title: NestJS
tags: [framework, node, nestjs, howtouse, nodejs]
updated: 2025-08-15
---

# NestJS 사용법 가이드

> **📌 통합된 기존 파일들**: 이 가이드는 다음 기존 파일들의 내용을 통합하여 더 체계적으로 정리한 것입니다.
> - NestJS 기본 개념과 Express와의 차이점
> - 핵심 데코레이터 가이드 (@Module, @Controller, @Injectable, @Get, @Post 등)
> - 의존성 주입 시스템
> - 모듈, 컨트롤러, 서비스 구조
> - 실제 프로젝트 예제

## 목차
1. [NestJS 소개](#nestjs-소개)
2. [NestJS 기본 개념](#nestjs-기본-개념)
3. [핵심 데코레이터 가이드](#핵심-데코레이터-가이드)
4. [설치 및 설정](#설치-및-설정)
5. [기본 명령어](#기본-명령어)
6. [프로젝트 구조](#프로젝트-구조)
7. [핵심 개념](#핵심-개념)
8. [실제 사용 예제](#실제-사용-예제)
9. [배포 및 운영](#배포-및-운영)

## NestJS 소개

NestJS는 현대적인 Node.js 애플리케이션 개발을 위한 강력한 프레임워크입니다. Express의 단순함을 유지하면서도, 엔터프라이즈급 애플리케이션 개발에 필요한 구조와 기능을 제공합니다.

### NestJS의 특징
- **TypeScript 우선**: 완전한 TypeScript 지원
- **의존성 주입**: 강력한 DI 컨테이너
- **모듈화**: 모듈 기반 아키텍처
- **데코레이터**: 메타데이터 기반 프로그래밍
- **OpenAPI**: 자동 API 문서 생성
- **테스트**: Jest 기반 테스트 지원

### NestJS의 필요성
- **구조화된 아키텍처**: 명확한 모듈, 컨트롤러, 서비스 구조 제공
- **타입 안정성**: TypeScript 기반으로 컴파일 타임 오류 방지
- **의존성 주입**: 객체 간의 결합도를 낮추고 테스트 용이성 확보
- **엔터프라이즈급 기능**: 대규모 프로젝트에 적합한 구조와 기능

## NestJS 기본 개념

### Express와 NestJS의 차이점

#### 아키텍처 패턴
```typescript
// Express 방식
const express = require('express');
const app = express();

app.get('/users', (req, res) => {
    res.json({ users: [] });
});

app.post('/users', (req, res) => {
    // 비즈니스 로직이 컨트롤러에 혼재
    res.json({ message: 'User created' });
});

// NestJS 방식
@Controller('users')
export class UsersController {
    constructor(private readonly usersService: UsersService) {}
    
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

#### 개발 생산성 비교
| 측면 | Express | NestJS |
|------|---------|--------|
| **구조화** | 개발자가 직접 설계 | 명확한 구조 제공 |
| **타입 안정성** | JavaScript 기반 | TypeScript 기반 |
| **의존성 관리** | 수동 관리 | 자동 의존성 주입 |
| **테스트** | 수동 Mock 설정 | 자동 Mock 생성 |
| **확장성** | 작은 프로젝트에 적합 | 대규모 프로젝트에 적합 |

### NestJS의 핵심 개념

#### 모듈 (Modules)
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
- **캡슐화**: 각 모듈은 독립적인 기능 단위
- **재사용성**: 다른 모듈에서 import하여 재사용 가능
- **의존성 관리**: 모듈 간의 의존성을 명확히 정의
- **구조화**: 애플리케이션을 논리적 단위로 분리

#### 컨트롤러 (Controllers)
컨트롤러는 들어오는 HTTP 요청을 처리하고 클라이언트에 응답을 반환하는 역할을 합니다.

```typescript
@Controller('users')
export class UsersController {
    constructor(private readonly usersService: UsersService) {}
    
    @Get()
    findAll(): User[] {
        return this.usersService.findAll();
    }
    
    @Get(':id')
    findOne(@Param('id') id: string): User {
        return this.usersService.findOne(id);
    }
    
    @Post()
    create(@Body() createUserDto: CreateUserDto): User {
        return this.usersService.create(createUserDto);
    }
    
    @Put(':id')
    update(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto): User {
        return this.usersService.update(id, updateUserDto);
    }
    
    @Delete(':id')
    remove(@Param('id') id: string): void {
        return this.usersService.remove(id);
    }
}
```

#### 서비스 (Services)
서비스는 비즈니스 로직을 담당하는 클래스입니다.

```typescript
@Injectable()
export class UsersService {
    private readonly users: User[] = [];
    
    create(createUserDto: CreateUserDto): User {
        const user = {
            id: Date.now().toString(),
            ...createUserDto
        };
        this.users.push(user);
        return user;
    }
    
    findAll(): User[] {
        return this.users;
    }
    
    findOne(id: string): User {
        const user = this.users.find(user => user.id === id);
        if (!user) {
            throw new NotFoundException(`User with ID ${id} not found`);
        }
        return user;
    }
    
    update(id: string, updateUserDto: UpdateUserDto): User {
        const userIndex = this.users.findIndex(user => user.id === id);
        if (userIndex === -1) {
            throw new NotFoundException(`User with ID ${id} not found`);
        }
        
        this.users[userIndex] = { ...this.users[userIndex], ...updateUserDto };
        return this.users[userIndex];
    }
    
    remove(id: string): void {
        const userIndex = this.users.findIndex(user => user.id === id);
        if (userIndex === -1) {
            throw new NotFoundException(`User with ID ${id} not found`);
        }
        
        this.users.splice(userIndex, 1);
    }
}
```

#### 서비스의 특징
- `@Injectable()` 데코레이터로 표시
- 의존성 주입 시스템의 핵심
- 싱글톤으로 관리됨
- 테스트 용이성 제공

## 핵심 데코레이터 가이드

### 기본 데코레이터

#### @Module()
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

#### @Injectable()
서비스나 프로바이더 클래스를 선언할 때 사용하는 데코레이터입니다.

```typescript
@Injectable()
export class UsersService {
  constructor() {}
}
```

### 컨트롤러 데코레이터

#### @Controller()
HTTP 요청을 처리하는 컨트롤러를 선언합니다.

```typescript
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}
}
```

#### HTTP 메서드 데코레이터
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

#### 요청 객체 데코레이터
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

### 프로바이더 데코레이터

#### @Injectable()
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

#### @Inject()
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

### 미들웨어 데코레이터

#### @Injectable()
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

### 예외 필터 데코레이터

#### @Catch()
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

### 파이프 데코레이터

#### @UsePipes()
컨트롤러나 라우트 핸들러에 파이프를 적용할 때 사용합니다.

```typescript
@Post()
@UsePipes(new ValidationPipe())
create(@Body() createUserDto: CreateUserDto) {
  return this.usersService.create(createUserDto);
}
```

### 가드 데코레이터

#### @UseGuards()
인증이나 권한 검사를 위한 가드를 적용할 때 사용합니다.

```typescript
@Get('profile')
@UseGuards(AuthGuard)
getProfile(@Request() req) {
  return req.user;
}
```

### 인터셉터 데코레이터

#### @UseInterceptors()
요청/응답을 가로채서 변환하거나 로깅하는 인터셉터를 적용할 때 사용합니다.

```typescript
@Get()
@UseInterceptors(LoggingInterceptor)
findAll() {
  return this.usersService.findAll();
}
```

### 사용자 정의 데코레이터

#### 커스텀 데코레이터 생성
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

#### @SetMetadata()
커스텀 메타데이터를 설정할 때 사용합니다.

```typescript
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

@Get()
@Roles('admin')
findAll() {
  return this.usersService.findAll();
}
```




#### 1. 컨트롤러 생성
```bash

nest generate controller [name]
nest g co [name]

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

nest generate service [name]
nest g s [name]

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

nest generate module [name]
nest g mo [name]

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

nest generate guard [name]
nest g gu [name]

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

nest generate interceptor [name]
nest g in [name]

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

nest generate pipe [name]
nest g pi [name]

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

nest generate filter [name]
nest g f [name]

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

nest generate middleware [name]
nest g mi [name]

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



```bash


npm run build

npm run test
npm run test:e2e
npm run test:cov
```


```bash



```bash


npm run build

npm run test
npm run test:e2e
npm run test:cov
```


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


### 1. 데이터베이스 연동 (TypeORM)

```bash


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


### 1. 데이터베이스 연동 (TypeORM)

```bash

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


### 1. 프로덕션 빌드

```bash

npm run build

npm run start:prod
```

### 2. Docker 배포

```dockerfile


### 1. 개발 생산성 향상

```bash

npm run start:dev

npm run start:debug

npm run test:cov
```

### 2. 코드 품질 관리

```bash


서비스 성격에 맞게 인증(누구인지 확인)과 인가(무엇을 할 수 있는지 허가)을 조합해 쓰면 된다. Nest에서는 `Guard`로 진입을 막고, `Passport`의 전략(strategy)으로 인증 방식을 꽂아 넣는 식이 일반적이다. JWT는 가볍고 빠르며, 소셜/IdP 연동은 OAuth 2.0/OpenID Connect(OIDC)를 쓰면 된다. SPA/모바일은 PKCE를 곁들이는 게 기본이다.

### Guard: 라우트 앞을 지키는 문지기
- 컨트롤러/핸들러 호출 전, 요청에 담긴 사용자/권한을 점검한다.
- 예) `JwtAuthGuard`로 액세스 토큰 검증, `RolesGuard`로 역할(Role) 확인.

```ts
// 예시: 역할 확인 데코레이터와 가드
import { SetMetadata, CanActivate, ExecutionContext, Injectable } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

@Injectable()
export class RolesGuard implements CanActivate {
  canActivate(ctx: ExecutionContext): boolean {
    const req = ctx.switchToHttp().getRequest();
    const required: string[] = Reflect.getMetadata(ROLES_KEY, ctx.getHandler()) ?? [];
    const userRoles: string[] = req.user?.roles ?? [];
    return required.length === 0 || required.some(r => userRoles.includes(r));
  }
}
```

### Passport: 인증 전략을 꽂는 슬롯
- `@nestjs/passport` + 개별 전략(passport-jwt, passport-local, OAuth 전략 등)을 결합한다.
- 로그인 시엔 `local` 전략(아이디/비밀번호)로 세션을 만들지 않고 토큰을 발급하는 구성도 흔하다.

### JWT: 빠른 검증, 짧은 수명
- 액세스 토큰(access token)은 짧게(보통 5–15분). 헤더의 `Authorization: Bearer <token>`로 전달.
- 서버는 비밀키(HS256)나 공개키(RS256)로 서명을 검증한다. 운영에선 RS256 + JWKS(키 회전)를 권장.
- 리프레시 토큰(refresh token)은 길게(보통 7–30일) 보관하고, 재발급 전용 엔드포인트에서만 사용한다.
- 보관 위치는 `HttpOnly + Secure` 쿠키가 안전하다. 로컬스토리지는 XSS에 취약하다.

### OAuth 2.0 / OpenID Connect (OIDC)
- 소셜/IdP(예: Google, Azure AD) 연동은 OIDC 표준을 쓰면 사용자 식별이 깔끔하다(`sub` 클레임으로 고유 식별).
- 코드 그랜트 + PKCE를 쓰면 클라이언트 시크릿 없이도 안전하게 토큰을 교환할 수 있다.
- 서버 사이드에선 `openid-client`를 사용하면 구현이 단순해진다.

흐름(Authorization Code + PKCE)
1) 클라이언트가 `code_verifier`를 만들고 `code_challenge`로 변환(SHA-256).
2) 사용자를 권한 부여 엔드포인트로 리다이렉트(`state`, `nonce` 포함).
3) 콜백에서 `authorization_code`와 `code_verifier`로 토큰 교환.
4) IdP의 `jwks_uri`로 서명 키를 받아 액세스/ID 토큰을 검증.

```ts
// 예시: openid-client로 PKCE 일부 흐름(개념 위주)
import { Issuer, generators } from 'openid-client';

const codeVerifier = generators.codeVerifier();
const codeChallenge = generators.codeChallenge(codeVerifier);
// 1) 로그인 시작 시, challenge를 포함해 authorize URL 생성
// 2) 콜백에서 code + codeVerifier로 토큰 교환
```

### 토큰 수명/회전/블랙리스트
- 수명(policy)
  - 액세스 토큰: 5–15분. 유출 시 피해를 줄이기 위해 짧게.
  - 리프레시 토큰: 7–30일. 기기 당 1개 세션으로 관리.
- 회전(rotation)
  - 리프레시 토큰을 사용할 때마다 새 리프레시 토큰을 발급하고, 이전 토큰은 즉시 폐기한다.
  - 토큰마다 `jti`(고유 ID)와 `tokenFamily`를 두면, 도난·재사용(Replay) 탐지에 유용하다.
  - 재사용이 감지되면 동일 `tokenFamily`를 전부 폐기한다.
- 블랙리스트(denylist)
  - 완전 무상태 JWT는 폐기가 어렵다. Redis에 `jti`를 만료 시간까지 저장해 차단한다.
  - 리프레시 토큰은 아예 화이트리스트(허용 목록)로 관리하는 편이 안전하다. DB/Redis에 유효 토큰만 저장.

### 인가: RBAC와 ABAC
- RBAC(Role-Based Access Control): 역할로 권한을 부여. `@Roles('admin')` + `RolesGuard` 패턴이 간단하다.
- ABAC(Attribute-Based Access Control): 리소스 소유자, 조직, 스코프 등 속성으로 세밀하게 통제. Guard에서 정책 함수를 호출하는 식으로 조합한다.

### 실전 구성 팁
- JWT 시크릿/키는 KMS/Secrets Manager 등에 보관. RS256을 쓰면 키 회전이 수월하다(JWKS + `kid`).
- 쿠키 기반이면 CSRF를 고려해 `SameSite`, CSRF 토큰 더블 서브밋 패턴을 함께 둔다.
- 멀티 디바이스는 세션 테이블에 기기·플랫폼 정보를 기록하고, 관리자/사용자별 강제 로그아웃을 지원한다.
- 로그아웃은 클라이언트 쿠키 제거 + 서버 측 토큰 폐기(화이트리스트 삭제/블랙리스트 등록) 둘 다 처리한다.

- 수명(policy)
  - 액세스 토큰: 5–15분. 유출 시 피해를 줄이기 위해 짧게.
  - 리프레시 토큰: 7–30일. 기기 당 1개 세션으로 관리.
- 회전(rotation)
  - 리프레시 토큰을 사용할 때마다 새 리프레시 토큰을 발급하고, 이전 토큰은 즉시 폐기한다.
  - 토큰마다 `jti`(고유 ID)와 `tokenFamily`를 두면, 도난·재사용(Replay) 탐지에 유용하다.
  - 재사용이 감지되면 동일 `tokenFamily`를 전부 폐기한다.
- 블랙리스트(denylist)
  - 완전 무상태 JWT는 폐기가 어렵다. Redis에 `jti`를 만료 시간까지 저장해 차단한다.
  - 리프레시 토큰은 아예 화이트리스트(허용 목록)로 관리하는 편이 안전하다. DB/Redis에 유효 토큰만 저장.

- JWT 시크릿/키는 KMS/Secrets Manager 등에 보관. RS256을 쓰면 키 회전이 수월하다(JWKS + `kid`).
- 쿠키 기반이면 CSRF를 고려해 `SameSite`, CSRF 토큰 더블 서브밋 패턴을 함께 둔다.
- 멀티 디바이스는 세션 테이블에 기기·플랫폼 정보를 기록하고, 관리자/사용자별 강제 로그아웃을 지원한다.
- 로그아웃은 클라이언트 쿠키 제거 + 서버 측 토큰 폐기(화이트리스트 삭제/블랙리스트 등록) 둘 다 처리한다.







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


- 수명(policy)
  - 액세스 토큰: 5–15분. 유출 시 피해를 줄이기 위해 짧게.
  - 리프레시 토큰: 7–30일. 기기 당 1개 세션으로 관리.
- 회전(rotation)
  - 리프레시 토큰을 사용할 때마다 새 리프레시 토큰을 발급하고, 이전 토큰은 즉시 폐기한다.
  - 토큰마다 `jti`(고유 ID)와 `tokenFamily`를 두면, 도난·재사용(Replay) 탐지에 유용하다.
  - 재사용이 감지되면 동일 `tokenFamily`를 전부 폐기한다.
- 블랙리스트(denylist)
  - 완전 무상태 JWT는 폐기가 어렵다. Redis에 `jti`를 만료 시간까지 저장해 차단한다.
  - 리프레시 토큰은 아예 화이트리스트(허용 목록)로 관리하는 편이 안전하다. DB/Redis에 유효 토큰만 저장.

- JWT 시크릿/키는 KMS/Secrets Manager 등에 보관. RS256을 쓰면 키 회전이 수월하다(JWKS + `kid`).
- 쿠키 기반이면 CSRF를 고려해 `SameSite`, CSRF 토큰 더블 서브밋 패턴을 함께 둔다.
- 멀티 디바이스는 세션 테이블에 기기·플랫폼 정보를 기록하고, 관리자/사용자별 강제 로그아웃을 지원한다.
- 로그아웃은 클라이언트 쿠키 제거 + 서버 측 토큰 폐기(화이트리스트 삭제/블랙리스트 등록) 둘 다 처리한다.

- 수명(policy)
  - 액세스 토큰: 5–15분. 유출 시 피해를 줄이기 위해 짧게.
  - 리프레시 토큰: 7–30일. 기기 당 1개 세션으로 관리.
- 회전(rotation)
  - 리프레시 토큰을 사용할 때마다 새 리프레시 토큰을 발급하고, 이전 토큰은 즉시 폐기한다.
  - 토큰마다 `jti`(고유 ID)와 `tokenFamily`를 두면, 도난·재사용(Replay) 탐지에 유용하다.
  - 재사용이 감지되면 동일 `tokenFamily`를 전부 폐기한다.
- 블랙리스트(denylist)
  - 완전 무상태 JWT는 폐기가 어렵다. Redis에 `jti`를 만료 시간까지 저장해 차단한다.
  - 리프레시 토큰은 아예 화이트리스트(허용 목록)로 관리하는 편이 안전하다. DB/Redis에 유효 토큰만 저장.

- JWT 시크릿/키는 KMS/Secrets Manager 등에 보관. RS256을 쓰면 키 회전이 수월하다(JWKS + `kid`).
- 쿠키 기반이면 CSRF를 고려해 `SameSite`, CSRF 토큰 더블 서브밋 패턴을 함께 둔다.
- 멀티 디바이스는 세션 테이블에 기기·플랫폼 정보를 기록하고, 관리자/사용자별 강제 로그아웃을 지원한다.
- 로그아웃은 클라이언트 쿠키 제거 + 서버 측 토큰 폐기(화이트리스트 삭제/블랙리스트 등록) 둘 다 처리한다.










## NestJS 소개

NestJS는 Node.js를 위한 진보적인 프레임워크로, 효율적이고 확장 가능한 서버 사이드 애플리케이션을 구축하기 위해 설계되었습니다. TypeScript를 완전히 지원하며, 객체지향 프로그래밍, 함수형 프로그래밍, 함수형 반응형 프로그래밍의 요소들을 결합합니다.

# 리졸버 생성 (GraphQL)
nest generate resolver [name]
nest g r [name]

# 게이트웨이 생성 (WebSockets)
nest generate gateway [name]
nest g ga [name]

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

## 실제 프로젝트 예제

### 1. 완전한 사용자 관리 시스템

#### DTO (Data Transfer Object)
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

// dto/update-user.dto.ts
import { PartialType } from '@nestjs/mapped-types';
import { CreateUserDto } from './create-user.dto';

export class UpdateUserDto extends PartialType(CreateUserDto) {}
```

#### Entity
```typescript
// entities/user.entity.ts
export class User {
  id: string;
  name: string;
  email: string;
  password: string;
  createdAt: Date;
  updatedAt: Date;
}
```

#### Repository
```typescript
// repositories/users.repository.ts
@Injectable()
export class UsersRepository {
  private users: User[] = [];
  
  async create(userData: CreateUserDto): Promise<User> {
    const user = {
      id: Date.now().toString(),
      ...userData,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    this.users.push(user);
    return user;
  }
  
  async findAll(): Promise<User[]> {
    return this.users;
  }
  
  async findById(id: string): Promise<User | null> {
    return this.users.find(user => user.id === id) || null;
  }
  
  async update(id: string, userData: UpdateUserDto): Promise<User | null> {
    const userIndex = this.users.findIndex(user => user.id === id);
    if (userIndex === -1) return null;
    
    this.users[userIndex] = {
      ...this.users[userIndex],
      ...userData,
      updatedAt: new Date()
    };
    return this.users[userIndex];
  }
  
  async delete(id: string): Promise<boolean> {
    const userIndex = this.users.findIndex(user => user.id === id);
    if (userIndex === -1) return false;
    
    this.users.splice(userIndex, 1);
    return true;
  }
}
```

#### Service
```typescript
// services/users.service.ts
@Injectable()
export class UsersService {
  constructor(private readonly usersRepository: UsersRepository) {}
  
  async create(createUserDto: CreateUserDto): Promise<User> {
    return this.usersRepository.create(createUserDto);
  }
  
  async findAll(): Promise<User[]> {
    return this.usersRepository.findAll();
  }
  
  async findOne(id: string): Promise<User> {
    const user = await this.usersRepository.findById(id);
    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    return user;
  }
  
  async update(id: string, updateUserDto: UpdateUserDto): Promise<User> {
    const user = await this.usersRepository.update(id, updateUserDto);
    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    return user;
  }
  
  async remove(id: string): Promise<void> {
    const deleted = await this.usersRepository.delete(id);
    if (!deleted) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
  }
}
```

#### Controller
```typescript
// controllers/users.controller.ts
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}
  
  @Post()
  async create(@Body(ValidationPipe) createUserDto: CreateUserDto): Promise<User> {
    return this.usersService.create(createUserDto);
  }
  
  @Get()
  async findAll(): Promise<User[]> {
    return this.usersService.findAll();
  }
  
  @Get(':id')
  async findOne(@Param('id') id: string): Promise<User> {
    return this.usersService.findOne(id);
  }
  
  @Put(':id')
  async update(
    @Param('id') id: string,
    @Body(ValidationPipe) updateUserDto: UpdateUserDto
  ): Promise<User> {
    return this.usersService.update(id, updateUserDto);
  }
  
  @Delete(':id')
  async remove(@Param('id') id: string): Promise<void> {
    return this.usersService.remove(id);
  }
}
```

#### Module
```typescript
// modules/users.module.ts
@Module({
  controllers: [UsersController],
  providers: [UsersService, UsersRepository],
  exports: [UsersService]
})
export class UsersModule {}
```

### 2. 고급 패턴 예제

#### 인터셉터 (Interceptors)
```typescript
// interceptors/transform.interceptor.ts
@Injectable()
export class TransformInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map(data => ({
        data,
        timestamp: new Date().toISOString(),
        success: true
      }))
    );
  }
}

// 컨트롤러에서 사용
@Controller('users')
@UseInterceptors(TransformInterceptor)
export class UsersController {
  // ...
}
```

#### 가드 (Guards)
```typescript
// guards/auth.guard.ts
@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const token = request.headers.authorization;
    
    if (!token) {
      throw new UnauthorizedException('No token provided');
    }
    
    // 토큰 검증 로직
    return true;
  }
}

// 컨트롤러에서 사용
@Controller('users')
@UseGuards(AuthGuard)
export class UsersController {
  // ...
}
```

#### 미들웨어와 파이프
```typescript
// middleware/logger.middleware.ts
@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: Function) {
    console.log(`Request: ${req.method} ${req.url}`);
    next();
  }
}

// 모듈에서 미들웨어 등록
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('users');
  }
}

// 파이프 사용
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
  return this.usersService.findOne(id);
}

@Post()
create(@Body(ValidationPipe) createUserDto: CreateUserDto) {
  return this.usersService.create(createUserDto);
}
```

### 3. NestJS vs Express 비교

| 측면 | Express | NestJS |
|------|---------|--------|
| **학습 곡선** | 낮음 | 중간 |
| **구조화** | 수동 | 자동 |
| **타입 안정성** | 없음 | TypeScript |
| **의존성 주입** | 없음 | 내장 |
| **테스트** | 수동 설정 | 자동 Mock |
| **확장성** | 작은 프로젝트 | 대규모 프로젝트 |

### 4. NestJS 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **소규모 프로젝트** | Express 고려 | 빠른 개발 |
| **대규모 프로젝트** | NestJS 사용 | 구조화된 개발 |
| **팀 개발** | NestJS 사용 | 일관된 구조 |
| **타입 안정성** | NestJS 사용 | TypeScript 지원 |
| **마이크로서비스** | NestJS 사용 | 내장 지원 |

### 5. 결론

NestJS는 현대적인 Node.js 애플리케이션 개발을 위한 강력한 프레임워크입니다.
TypeScript와 의존성 주입을 통해 타입 안정성과 테스트 용이성을 확보하세요.
모듈, 컨트롤러, 서비스의 명확한 구조를 활용하여 유지보수하기 쉬운 코드를 작성하세요.
대규모 프로젝트나 팀 개발에서 특히 유용하며, 엔터프라이즈급 기능을 제공합니다.

