---
title: NestJS 사용법
tags: [framework, node, nestjs, typescript, backend]
updated: 2025-11-30
---

# NestJS

NestJS의 핵심 개념과 실제 개발에서의 활용법을 체계적으로 정리했습니다.

## 목차
1. [NestJS란 무엇인가](#nestjs란-무엇인가)
2. [핵심 아키텍처 개념](#핵심-아키텍처-개념)
3. [의존성 주입 시스템](#의존성-주입-시스템)
4. [데코레이터와 메타데이터](#데코레이터와-메타데이터)
5. [실제 개발 워크플로우](#실제-개발-워크플로우)
6. [고급 패턴과 모범 사례](#고급-패턴과-모범-사례)
7. [성능과 확장성](#성능과-확장성)

## NestJS란 무엇인가

### 기본 철학

NestJS는 Node.js 생태계에서 **구조화된 서버 사이드 애플리케이션**을 구축하기 위해 설계된 프레임워크입니다. Angular의 아키텍처 패턴을 Node.js 환경에 적용한 것이 핵심 아이디어입니다.

**선택 이유**

1. **명확한 구조**: 모듈, 컨트롤러, 서비스의 3계층 구조로 일관된 코드베이스 유지
2. **타입 안정성**: TypeScript를 기본으로 지원하여 컴파일 타임 오류 방지
3. **의존성 주입**: 객체 간의 결합도를 낮추고 테스트 용이성 확보
4. **엔터프라이즈급 기능**: 대규모 팀과 프로젝트에 적합한 아키텍처

### Express와의 근본적 차이

Express는 **미니멀한 웹 프레임워크**로, 개발자가 모든 구조를 직접 설계해야 합니다. 반면 NestJS는 **아키텍처가 내장된 프레임워크**로, 일정한 패턴을 강제하여 팀 전체의 일관성을 보장합니다.

**개발 관점에서의 차이점:**

- **Express**: 빠른 프로토타이핑에 적합, 작은 팀이나 개인 프로젝트
- **NestJS**: 장기적 유지보수에 적합, 대규모 팀이나 엔터프라이즈 프로젝트

## 핵심 아키텍처 개념

### 1. 모듈 (Modules) - 애플리케이션의 구성 단위

모듈은 **관련된 기능들을 하나로 묶는 컨테이너**입니다. 각 모듈은 독립적인 기능 단위를 나타내며, 애플리케이션을 논리적으로 분리하는 역할을 합니다.

**모듈의 핵심 구성 요소:**
- `imports`: 다른 모듈에서 가져올 의존성
- `controllers`: HTTP 요청을 처리하는 컨트롤러들
- `providers`: 비즈니스 로직을 담당하는 서비스들
- `exports`: 다른 모듈에서 사용할 수 있도록 공개하는 프로바이더들

**모듈 설계 원칙:**
1. **단일 책임**: 하나의 모듈은 하나의 도메인만 담당
2. **느슨한 결합**: 모듈 간의 의존성을 최소화
3. **높은 응집성**: 관련된 기능들을 한 곳에 모음

### 2. 컨트롤러 (Controllers) - 요청 처리의 진입점

컨트롤러는 **HTTP 요청을 받아 적절한 응답을 반환하는 역할**을 합니다. 라우팅과 요청 처리를 담당하지만, 비즈니스 로직은 포함하지 않습니다.

**컨트롤러의 책임:**
- HTTP 요청의 라우팅
- 요청 데이터의 파싱 및 검증
- 서비스 계층으로의 위임
- 응답 데이터의 변환

**컨트롤러 설계 원칙:**
1. **얇은 컨트롤러**: 비즈니스 로직은 서비스에 위임
2. **명확한 라우팅**: RESTful API 설계 원칙 준수
3. **적절한 검증**: 입력 데이터의 유효성 검사

### 3. 서비스 (Services) - 비즈니스 로직의 핵심

서비스는 **애플리케이션의 핵심 비즈니스 로직**을 담당합니다. 데이터 처리, 외부 API 호출, 복잡한 계산 등을 수행합니다.

**서비스의 특징:**
- `@Injectable()` 데코레이터로 표시
- 싱글톤으로 관리되어 메모리 효율성 확보
- 의존성 주입을 통한 다른 서비스와의 협력
- 테스트하기 쉬운 구조

## 의존성 주입 시스템

### DI의 핵심 개념

의존성 주입(Dependency Injection)은 **객체가 필요한 의존성을 외부에서 받아오는 패턴**입니다. NestJS는 강력한 DI 컨테이너를 제공하여 객체 간의 결합도를 낮춥니다.

**DI의 장점:**
1. **테스트 용이성**: Mock 객체를 쉽게 주입 가능
2. **유연성**: 런타임에 다른 구현체로 교체 가능
3. **재사용성**: 컴포넌트의 독립성 확보
4. **유지보수성**: 의존성 변경이 쉬움

### 프로바이더 (Providers) 시스템

프로바이더는 **NestJS가 의존성을 해결하는 방법**을 정의합니다. 서비스, 팩토리, 헬퍼 등 다양한 형태로 구현 가능합니다.

**프로바이더의 생명주기:**
1. **인스턴스화**: 클래스의 인스턴스 생성
2. **의존성 해결**: 필요한 의존성들을 주입
3. **싱글톤 관리**: 애플리케이션 생명주기 동안 재사용

## 데코레이터와 메타데이터

### 데코레이터의 역할

데코레이터는 **클래스, 메서드, 프로퍼티에 메타데이터를 추가**하는 TypeScript의 기능입니다. NestJS는 이를 활용하여 프레임워크의 동작을 제어합니다.

**주요 데코레이터 카테고리:**

1. **클래스 데코레이터**: `@Controller()`, `@Injectable()`, `@Module()`
2. **메서드 데코레이터**: `@Get()`, `@Post()`, `@Put()`, `@Delete()`
3. **매개변수 데코레이터**: `@Body()`, `@Param()`, `@Query()`
4. **커스텀 데코레이터**: 특정 요구사항에 맞는 사용자 정의 데코레이터

### 메타데이터 기반 프로그래밍

NestJS는 **Reflect Metadata API**를 사용하여 데코레이터로 추가된 메타데이터를 런타임에 읽어 프레임워크의 동작을 결정합니다.

**메타데이터 활용 예시:**
- 라우팅 정보 자동 생성
- 의존성 주입 정보 수집
- 유효성 검사 규칙 적용
- 권한 검사 로직 실행

## 실제 개발 워크플로우

### 1. 프로젝트 초기 설정

**CLI를 통한 프로젝트 생성:**
```bash
# NestJS CLI 설치
npm i -g @nestjs/cli

# 새 프로젝트 생성
nest new my-project

# 개발 서버 실행
npm run start:dev
```

**기본 프로젝트 구조:**
```
src/
├── app.controller.ts    # 루트 컨트롤러
├── app.service.ts      # 루트 서비스
├── app.module.ts       # 루트 모듈
└── main.ts            # 애플리케이션 진입점
```

### 2. 기능별 모듈 개발

**모듈 생성 워크플로우:**
1. `nest g module [name]` - 모듈 생성
2. `nest g service [name]` - 서비스 생성
3. `nest g controller [name]` - 컨트롤러 생성
4. DTO 및 Entity 정의
5. 비즈니스 로직 구현

### 3. 데이터 검증과 변환

**DTO (Data Transfer Object) 활용:**
- 클라이언트와 서버 간의 데이터 계약 정의
- `class-validator`를 통한 자동 유효성 검사
- `class-transformer`를 통한 데이터 변환

**파이프 (Pipes) 시스템:**
- 입력 데이터의 변환과 검증
- 전역 파이프와 로컬 파이프
- 커스텀 파이프 구현

## 완전한 CRUD 예제: User 모듈

실제 프로덕션 환경에서 사용할 수 있는 완전한 User 모듈 예제를 통해 NestJS의 핵심 개념을 학습합니다.

### 프로젝트 구조
```
src/
├── users/
│   ├── dto/
│   │   ├── create-user.dto.ts
│   │   └── update-user.dto.ts
│   ├── entities/
│   │   └── user.entity.ts
│   ├── users.controller.ts
│   ├── users.service.ts
│   └── users.module.ts
└── app.module.ts
```

### 1. Entity 정의

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

### 2. DTO 정의 (Data Transfer Object)

```typescript
// users/dto/create-user.dto.ts
import { IsString, IsEmail, IsInt, Min, Max, IsOptional } from 'class-validator';

export class CreateUserDto {
    @IsString()
    name: string;

    @IsEmail()
    email: string;

    @IsInt()
    @Min(1)
    @Max(120)
    age: number;

    @IsOptional()
    @IsString()
    password?: string;
}
```

```typescript
// users/dto/update-user.dto.ts
import { PartialType } from '@nestjs/mapped-types';
import { CreateUserDto } from './create-user.dto';

export class UpdateUserDto extends PartialType(CreateUserDto) {
    // PartialType은 CreateUserDto의 모든 속성을 선택적으로 만듦
}
```

### 3. Service 구현

```typescript
// users/users.service.ts
import { Injectable, NotFoundException } from '@nestjs/common';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { User } from './entities/user.entity';

@Injectable()
export class UsersService {
    private users: User[] = [];
    private nextId = 1;

    create(createUserDto: CreateUserDto): User {
        const user: User = {
            id: this.nextId++,
            ...createUserDto,
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
        const user = this.users.find(u => u.id === id);
        if (!user) {
            throw new NotFoundException(`User with ID ${id} not found`);
        }
        return user;
    }

    update(id: number, updateUserDto: UpdateUserDto): User {
        const user = this.findOne(id);
        Object.assign(user, updateUserDto, { updatedAt: new Date() });
        return user;
    }

    remove(id: number): void {
        const index = this.users.findIndex(u => u.id === id);
        if (index === -1) {
            throw new NotFoundException(`User with ID ${id} not found`);
        }
        this.users.splice(index, 1);
    }
}
```

### 4. Controller 구현

```typescript
// users/users.controller.ts
import {
    Controller,
    Get,
    Post,
    Body,
    Patch,
    Param,
    Delete,
    HttpCode,
    HttpStatus,
    ParseIntPipe,
} from '@nestjs/common';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';

@Controller('users')
export class UsersController {
    constructor(private readonly usersService: UsersService) {}

    @Post()
    @HttpCode(HttpStatus.CREATED)
    create(@Body() createUserDto: CreateUserDto) {
        return this.usersService.create(createUserDto);
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
        @Body() updateUserDto: UpdateUserDto,
    ) {
        return this.usersService.update(id, updateUserDto);
    }

    @Delete(':id')
    @HttpCode(HttpStatus.NO_CONTENT)
    remove(@Param('id', ParseIntPipe) id: number) {
        return this.usersService.remove(id);
    }
}
```

### 5. Module 정의

```typescript
// users/users.module.ts
import { Module } from '@nestjs/common';
import { UsersService } from './users.service';
import { UsersController } from './users.controller';

@Module({
    controllers: [UsersController],
    providers: [UsersService],
    exports: [UsersService], // 다른 모듈에서 사용 가능하도록 export
})
export class UsersModule {}
```

### 6. App Module에 등록

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { UsersModule } from './users/users.module';

@Module({
    imports: [UsersModule],
})
export class AppModule {}
```

## 데코레이터 상세 설명 및 사용 예제

### 클래스 데코레이터

#### @Controller()
HTTP 요청을 처리하는 컨트롤러 클래스를 정의합니다.

```typescript
@Controller('users')  // 기본 경로: /users
export class UsersController {
    // 모든 라우트는 /users로 시작
}

@Controller()  // 경로 없음
export class AppController {
    // 루트 경로에서 시작
}
```

#### @Injectable()
의존성 주입이 가능한 클래스를 표시합니다. 서비스, 가드, 인터셉터 등에 사용됩니다.

```typescript
@Injectable()
export class UsersService {
    // NestJS가 이 클래스를 DI 컨테이너에 등록
}
```

#### @Module()
모듈을 정의합니다. 애플리케이션의 구조를 구성하는 핵심 데코레이터입니다.

```typescript
@Module({
    imports: [OtherModule],      // 다른 모듈 import
    controllers: [UsersController], // 컨트롤러 등록
    providers: [UsersService],   // 프로바이더 등록
    exports: [UsersService],     // 다른 모듈에 공개
})
export class UsersModule {}
```

### 메서드 데코레이터 (HTTP 메서드)

#### @Get(), @Post(), @Put(), @Delete(), @Patch()

```typescript
@Controller('users')
export class UsersController {
    @Get()  // GET /users
    findAll() {
        return '모든 사용자 조회';
    }

    @Get(':id')  // GET /users/:id
    findOne(@Param('id') id: string) {
        return `사용자 ${id} 조회`;
    }

    @Post()  // POST /users
    create(@Body() createUserDto: CreateUserDto) {
        return '사용자 생성';
    }

    @Put(':id')  // PUT /users/:id
    update(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto) {
        return `사용자 ${id} 업데이트`;
    }

    @Patch(':id')  // PATCH /users/:id
    partialUpdate(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto) {
        return `사용자 ${id} 부분 업데이트`;
    }

    @Delete(':id')  // DELETE /users/:id
    remove(@Param('id') id: string) {
        return `사용자 ${id} 삭제`;
    }
}
```

#### 라우트 경로 커스터마이징

```typescript
@Controller('users')
export class UsersController {
    @Get('profile/:id')  // GET /users/profile/:id
    getProfile(@Param('id') id: string) {
        return `프로필 조회: ${id}`;
    }

    @Get('search')  // GET /users/search
    search(@Query('q') query: string) {
        return `검색: ${query}`;
    }
}
```

### 매개변수 데코레이터

#### @Body() - 요청 본문 추출

```typescript
@Post()
create(@Body() createUserDto: CreateUserDto) {
    // 전체 본문
}

@Post()
create(
    @Body('name') name: string,
    @Body('email') email: string,
) {
    // 특정 속성만 추출
}
```

#### @Param() - 경로 매개변수 추출

```typescript
@Get(':id')
findOne(@Param('id') id: string) {
    // 단일 매개변수
}

@Get(':userId/posts/:postId')
findPost(
    @Param('userId') userId: string,
    @Param('postId') postId: string,
) {
    // 여러 매개변수
}

@Get(':id')
findOne(@Param() params: { id: string }) {
    // 객체로 받기
    return params.id;
}
```

#### @Query() - 쿼리 매개변수 추출

```typescript
@Get('search')
search(
    @Query('q') query: string,
    @Query('page') page: number,
) {
    // GET /users/search?q=test&page=1
}

@Get('filter')
filter(@Query() query: { q?: string; page?: number; limit?: number }) {
    // 객체로 받기
    return query;
}
```

#### @Headers() - HTTP 헤더 추출

```typescript
@Get()
findAll(@Headers('authorization') auth: string) {
    // 특정 헤더만
}

@Get()
findAll(@Headers() headers: Record<string, string>) {
    // 모든 헤더
}
```

#### @Req(), @Res() - Request/Response 객체

```typescript
import { Request, Response } from 'express';

@Get()
findAll(@Req() req: Request, @Res() res: Response) {
    // Express의 Request/Response 객체 직접 접근
    // 권장하지 않음: 플랫폼 독립성 손실
}
```

## 의존성 주입 구체적 예제

### 생성자 주입 (Constructor Injection) - 권장

```typescript
@Controller('users')
export class UsersController {
    constructor(private readonly usersService: UsersService) {}
    // TypeScript의 접근 제어자를 사용하여 자동으로 프로퍼티로 변환
}

// 위 코드는 아래와 동일
@Controller('users')
export class UsersController {
    private readonly usersService: UsersService;
    
    constructor(usersService: UsersService) {
        this.usersService = usersService;
    }
}
```

### 속성 주입 (Property Injection) - 비권장

```typescript
@Controller('users')
export class UsersController {
    @Inject(UsersService)
    private readonly usersService: UsersService;
}
```

### 메서드 주입 (Method Injection) - 특수한 경우

```typescript
@Controller('users')
export class UsersController {
    private usersService: UsersService;

    @Inject()
    setUsersService(usersService: UsersService) {
        this.usersService = usersService;
    }
}
```

### 다중 의존성 주입

```typescript
@Controller('users')
export class UsersController {
    constructor(
        private readonly usersService: UsersService,
        private readonly emailService: EmailService,
        private readonly logger: Logger,
    ) {}
}
```

### 커스텀 프로바이더

#### 값 기반 프로바이더

```typescript
// app.module.ts
import { Module } from '@nestjs/common';

const CONFIG = {
    apiUrl: 'https://api.example.com',
    timeout: 5000,
};

@Module({
    providers: [
        {
            provide: 'CONFIG',
            useValue: CONFIG,
        },
    ],
})
export class AppModule {}

// 사용
@Controller('users')
export class UsersController {
    constructor(@Inject('CONFIG') private config: typeof CONFIG) {}
}
```

#### 팩토리 프로바이더

```typescript
// app.module.ts
@Module({
    providers: [
        {
            provide: 'DATABASE_CONNECTION',
            useFactory: (config: ConfigService) => {
                return createConnection({
                    host: config.get('DB_HOST'),
                    port: config.get('DB_PORT'),
                });
            },
            inject: [ConfigService],
        },
    ],
})
export class AppModule {}
```

#### 비동기 프로바이더

```typescript
@Module({
    providers: [
        {
            provide: 'ASYNC_CONNECTION',
            useFactory: async () => {
                const connection = await createConnection();
                return connection;
            },
        },
    ],
})
export class AppModule {}
```

## DTO와 class-validator 사용 예제

### 설치

```bash
npm install class-validator class-transformer
```

### DTO 정의 및 검증

```typescript
// users/dto/create-user.dto.ts
import {
    IsString,
    IsEmail,
    IsInt,
    Min,
    Max,
    IsOptional,
    IsNotEmpty,
    MinLength,
    MaxLength,
    Matches,
} from 'class-validator';

export class CreateUserDto {
    @IsString()
    @IsNotEmpty()
    @MinLength(2)
    @MaxLength(50)
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
    @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, {
        message: '비밀번호는 대문자, 소문자, 숫자를 포함해야 합니다',
    })
    password?: string;
}
```

### 전역 ValidationPipe 설정

```typescript
// main.ts
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
    const app = await NestFactory.create(AppModule);
    
    app.useGlobalPipes(
        new ValidationPipe({
            whitelist: true,        // DTO에 없는 속성 제거
            forbidNonWhitelisted: true,  // DTO에 없는 속성 시 오류
            transform: true,       // 자동 타입 변환
            transformOptions: {
                enableImplicitConversion: true,
            },
        }),
    );
    
    await app.listen(3000);
}
bootstrap();
```

### 커스텀 검증 데코레이터

```typescript
// common/decorators/match.decorator.ts
import {
    registerDecorator,
    ValidationOptions,
    ValidationArguments,
} from 'class-validator';

export function Match(property: string, validationOptions?: ValidationOptions) {
    return function (object: Object, propertyName: string) {
        registerDecorator({
            name: 'match',
            target: object.constructor,
            propertyName: propertyName,
            constraints: [property],
            options: validationOptions,
            validator: {
                validate(value: any, args: ValidationArguments) {
                    const [relatedPropertyName] = args.constraints;
                    const relatedValue = (args.object as any)[relatedPropertyName];
                    return value === relatedValue;
                },
                defaultMessage(args: ValidationArguments) {
                    const [relatedPropertyName] = args.constraints;
                    return `${args.property} must match ${relatedPropertyName}`;
                },
            },
        });
    };
}

// 사용
export class CreateUserDto {
    password: string;

    @Match('password')
    confirmPassword: string;
}
```

## 파이프(Pipes) 사용 예제

### 내장 파이프

```typescript
import { ParseIntPipe, ParseBoolPipe, ParseUUIDPipe, DefaultValuePipe } from '@nestjs/common';

@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
    // id는 자동으로 number로 변환
}

@Get(':uuid')
findOne(@Param('uuid', ParseUUIDPipe) uuid: string) {
    // UUID 형식 검증
}

@Get()
findAll(
    @Query('active', new DefaultValuePipe(true), ParseBoolPipe) active: boolean,
) {
    // 기본값과 타입 변환
}
```

### 커스텀 파이프

```typescript
// common/pipes/parse-int.pipe.ts
import { PipeTransform, Injectable, ArgumentMetadata, BadRequestException } from '@nestjs/common';

@Injectable()
export class CustomParseIntPipe implements PipeTransform<string, number> {
    transform(value: string, metadata: ArgumentMetadata): number {
        const val = parseInt(value, 10);
        if (isNaN(val)) {
            throw new BadRequestException(`Validation failed. "${value}" is not an integer.`);
        }
        return val;
    }
}

// 사용
@Get(':id')
findOne(@Param('id', CustomParseIntPipe) id: number) {
    return this.usersService.findOne(id);
}
```

## 가드(Guards) 기본 구현 예제

### 인증 가드

```typescript
// auth/guards/auth.guard.ts
import { Injectable, CanActivate, ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class AuthGuard implements CanActivate {
    canActivate(
        context: ExecutionContext,
    ): boolean | Promise<boolean> | Observable<boolean> {
        const request = context.switchToHttp().getRequest();
        const token = request.headers.authorization;

        if (!token) {
            throw new UnauthorizedException('인증 토큰이 필요합니다');
        }

        // 토큰 검증 로직
        const isValid = this.validateToken(token);
        if (!isValid) {
            throw new UnauthorizedException('유효하지 않은 토큰입니다');
        }

        return true;
    }

    private validateToken(token: string): boolean {
        // 실제 토큰 검증 로직
        return token.startsWith('Bearer ');
    }
}

// 사용
@Controller('users')
@UseGuards(AuthGuard)
export class UsersController {
    // 모든 엔드포인트에 가드 적용
}
```

### 역할 기반 가드

```typescript
// auth/guards/roles.guard.ts
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';

@Injectable()
export class RolesGuard implements CanActivate {
    constructor(private reflector: Reflector) {}

    canActivate(context: ExecutionContext): boolean {
        const requiredRoles = this.reflector.get<string[]>('roles', context.getHandler());
        if (!requiredRoles) {
            return true;
        }

        const request = context.switchToHttp().getRequest();
        const user = request.user;
        
        return requiredRoles.some(role => user.roles?.includes(role));
    }
}

// 커스텀 데코레이터
// auth/decorators/roles.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

// 사용
@Controller('users')
@UseGuards(AuthGuard, RolesGuard)
export class UsersController {
    @Get('admin')
    @Roles('admin')
    adminOnly() {
        return '관리자만 접근 가능';
    }
}
```

## 예외 필터(Exception Filters) 기본 구현 예제

### 커스텀 예외 필터

```typescript
// common/filters/http-exception.filter.ts
import {
    ExceptionFilter,
    Catch,
    ArgumentsHost,
    HttpException,
    HttpStatus,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
    catch(exception: HttpException, host: ArgumentsHost) {
        const ctx = host.switchToHttp();
        const response = ctx.getResponse<Response>();
        const request = ctx.getRequest<Request>();
        const status = exception.getStatus();

        response.status(status).json({
            statusCode: status,
            timestamp: new Date().toISOString(),
            path: request.url,
            message: exception.message,
        });
    }
}

// 사용
@Controller('users')
@UseFilters(HttpExceptionFilter)
export class UsersController {
    // 컨트롤러 레벨
}

@Get(':id')
@UseFilters(HttpExceptionFilter)
findOne(@Param('id') id: string) {
    // 메서드 레벨
}
```

### 전역 예외 필터

```typescript
// main.ts
import { HttpExceptionFilter } from './common/filters/http-exception.filter';

async function bootstrap() {
    const app = await NestFactory.create(AppModule);
    app.useGlobalFilters(new HttpExceptionFilter());
    await app.listen(3000);
}
bootstrap();
```

### 커스텀 예외 클래스

```typescript
// common/exceptions/business.exception.ts
import { HttpException, HttpStatus } from '@nestjs/common';

export class BusinessException extends HttpException {
    constructor(message: string, errorCode: string) {
        super(
            {
                message,
                errorCode,
                timestamp: new Date().toISOString(),
            },
            HttpStatus.BAD_REQUEST,
        );
    }
}

// 사용
@Get(':id')
findOne(@Param('id') id: string) {
    if (!id) {
        throw new BusinessException('ID는 필수입니다', 'MISSING_ID');
    }
    return this.usersService.findOne(id);
}
```

## 고급 패턴과 모범 사례

### 1. 가드 (Guards) - 인증과 권한 관리

가드는 **라우트 핸들러 실행 전에 권한을 검사**하는 역할을 합니다. 인증(Authentication)과 인가(Authorization)를 분리하여 구현하는 것이 좋습니다.

**가드 구현 패턴:**
- JWT 토큰 검증
- 역할 기반 접근 제어 (RBAC)
- 리소스 기반 권한 검사

### 2. 인터셉터 (Interceptors) - 횡단 관심사 처리

인터셉터는 **요청과 응답을 가로채서 추가 로직을 실행**할 수 있습니다. 로깅, 캐싱, 응답 변환 등에 활용됩니다.

**인터셉터 활용 사례:**
- 실행 시간 측정
- 응답 데이터 포맷팅
- 에러 처리 및 로깅
- 캐싱 로직 구현

### 3. 예외 필터 (Exception Filters) - 에러 처리

예외 필터는 **애플리케이션에서 발생하는 예외를 일관되게 처리**합니다. HTTP 상태 코드와 에러 메시지를 표준화합니다.

**예외 처리:**
- 비즈니스 예외와 시스템 예외 분리
- 사용자 친화적인 에러 메시지
- 로깅과 모니터링 연동

### 4. 미들웨어 (Middleware) - 요청 처리 파이프라인

미들웨어는 **요청이 라우트 핸들러에 도달하기 전에 실행**되는 함수입니다. CORS, 로깅, 압축 등에 활용됩니다.

## 성능과 확장성

### 1. 캐싱

**메모리 캐싱:**
- `@nestjs/cache-manager`를 통한 인메모리 캐싱
- Redis를 활용한 분산 캐싱
- 캐시 무효화

### 2. 데이터베이스 최적화

**ORM 활용:**
- TypeORM을 통한 관계형 데이터베이스 연동
- Mongoose를 통한 MongoDB 연동
- 쿼리 최적화와 인덱싱

### 3. 마이크로서비스 아키텍처

**NestJS 마이크로서비스:**
- TCP, Redis, RabbitMQ 등 다양한 전송 계층 지원
- 서비스 간 통신 패턴
- 분산 시스템에서의 데이터 일관성

### 4. 모니터링과 로깅

**운영 환경 고려사항:**
- 구조화된 로깅 (Winston, Pino)
- 메트릭 수집 (Prometheus)
- 헬스 체크 엔드포인트
- 분산 추적 (OpenTelemetry)

## 실무 적용 가이드

### 팀 개발 환경

**코드 품질 관리:**
- ESLint와 Prettier 설정
- Husky를 통한 Git hooks
- 테스트 커버리지 관리

**CI/CD 파이프라인:**
- 자동화된 테스트 실행
- 코드 품질 검사
- 배포 자동화

### 보안 고려사항

**인증과 인가:**
- JWT 토큰 기반 인증
- OAuth 2.0 / OpenID Connect
- 세션 관리와 토큰 갱신

**데이터 보호:**
- 입력 데이터 검증
- SQL 인젝션 방지
- XSS 및 CSRF 공격 방어

### 성능 튜닝

**애플리케이션 레벨:**
- 메모리 사용량 최적화
- 비동기 처리 패턴
- 연결 풀 관리

**인프라 레벨:**
- 로드 밸런싱
- 컨테이너 오케스트레이션
- CDN 활용

## 마무리

NestJS는 **현대적인 Node.js 애플리케이션 개발을 위한 강력한 도구**입니다. 구조화된 아키텍처와 TypeScript의 타입 안정성을 통해 안정적이고 확장 가능한 애플리케이션을 구축할 수 있습니다.

주요 내용:

1. 모듈 기반 설계로 코드의 재사용성과 유지보수성 확보
2. 의존성 주입을 통한 느슨한 결합과 테스트 용이성
3. 데코레이터 패턴으로 선언적이고 직관적인 코드 작성
4. 엔터프라이즈급 기능으로 대규모 프로젝트 지원

NestJS를 효과적으로 활용하려면 **아키텍처 패턴을 이해하고 일관된 코딩 스타일을 유지**하는 것이 중요합니다. 팀 전체가 동일한 패턴을 따르면 코드베이스의 일관성과 품질을 크게 향상시킬 수 있습니다.

---

## TypeScript 고급 타입과 NestJS 통합

NestJS는 TypeScript를 기반으로 하므로, TypeScript의 고급 타입 기능을 활용하면 더욱 타입 안전하고 강력한 애플리케이션을 구축할 수 있습니다.

### Record<>를 활용한 설정 객체

#### 환경 변수 타입 안전 설정

```typescript
// config/config.types.ts
type Environment = 'development' | 'staging' | 'production';

type ConfigKeys = 
    | 'DATABASE_HOST'
    | 'DATABASE_PORT'
    | 'DATABASE_NAME'
    | 'JWT_SECRET'
    | 'API_URL';

type Config = Record<ConfigKeys, string> & {
    NODE_ENV: Environment;
    PORT: number;
};

// config/config.service.ts
import { Injectable } from '@nestjs/common';

@Injectable()
export class ConfigService {
    private config: Config;

    constructor() {
        this.config = {
            NODE_ENV: process.env.NODE_ENV as Environment,
            PORT: parseInt(process.env.PORT || '3000', 10),
            DATABASE_HOST: process.env.DATABASE_HOST || 'localhost',
            DATABASE_PORT: process.env.DATABASE_PORT || '3306',
            DATABASE_NAME: process.env.DATABASE_NAME || 'test',
            JWT_SECRET: process.env.JWT_SECRET || 'secret',
            API_URL: process.env.API_URL || 'http://localhost:3000',
        };
    }

    get<K extends keyof Config>(key: K): Config[K] {
        return this.config[key];
    }

    getEnv(): Environment {
        return this.config.NODE_ENV;
    }
}
```

#### 환경별 설정 매핑

```typescript
// config/environment.config.ts
type Environment = 'development' | 'staging' | 'production';

interface EnvironmentConfig {
    apiUrl: string;
    databaseUrl: string;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
    enableSwagger: boolean;
}

type EnvironmentConfigMap = Record<Environment, EnvironmentConfig>;

const configMap: EnvironmentConfigMap = {
    development: {
        apiUrl: 'http://localhost:3000',
        databaseUrl: 'postgresql://localhost:5432/dev',
        logLevel: 'debug',
        enableSwagger: true,
    },
    staging: {
        apiUrl: 'https://staging-api.example.com',
        databaseUrl: 'postgresql://staging-db:5432/staging',
        logLevel: 'info',
        enableSwagger: true,
    },
    production: {
        apiUrl: 'https://api.example.com',
        databaseUrl: 'postgresql://prod-db:5432/prod',
        logLevel: 'warn',
        enableSwagger: false,
    },
};

@Injectable()
export class EnvironmentConfigService {
    getConfig(env: Environment): EnvironmentConfig {
        return configMap[env];
    }
}
```

### 제네릭을 활용한 서비스

#### 제네릭 CRUD 서비스

```typescript
// common/services/base.service.ts
import { Injectable } from '@nestjs/common';
import { Repository } from 'typeorm';

export interface BaseEntity {
    id: number;
    createdAt: Date;
    updatedAt: Date;
}

@Injectable()
export abstract class BaseService<T extends BaseEntity> {
    constructor(protected readonly repository: Repository<T>) {}

    async create(createDto: Partial<T>): Promise<T> {
        const entity = this.repository.create(createDto as T);
        return await this.repository.save(entity);
    }

    async findAll(): Promise<T[]> {
        return await this.repository.find();
    }

    async findOne(id: number): Promise<T> {
        const entity = await this.repository.findOne({ where: { id } as any });
        if (!entity) {
            throw new Error(`Entity with ID ${id} not found`);
        }
        return entity;
    }

    async update(id: number, updateDto: Partial<T>): Promise<T> {
        await this.repository.update(id, updateDto);
        return this.findOne(id);
    }

    async remove(id: number): Promise<void> {
        await this.repository.delete(id);
    }
}

// users/users.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { BaseService } from '../common/services/base.service';
import { User } from './entities/user.entity';

@Injectable()
export class UsersService extends BaseService<User> {
    constructor(
        @InjectRepository(User)
        repository: Repository<User>,
    ) {
        super(repository);
    }

    // User 특화 메서드 추가 가능
    async findByEmail(email: string): Promise<User | null> {
        return await this.repository.findOne({ where: { email } });
    }
}
```

#### 제네릭 응답 타입

```typescript
// common/interfaces/api-response.interface.ts
export interface ApiResponse<T> {
    success: boolean;
    data: T;
    message?: string;
    timestamp: Date;
}

export interface ApiError {
    code: string;
    message: string;
    details?: Record<string, any>;
}

export type ApiResult<T> = 
    | { success: true; data: T }
    | { success: false; error: ApiError };

// common/decorators/api-response.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const ApiResponseType = <T>(type: new () => T) =>
    SetMetadata('responseType', type);

// common/interceptors/transform.interceptor.ts
import {
    Injectable,
    NestInterceptor,
    ExecutionContext,
    CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiResponse } from '../interfaces/api-response.interface';

@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, ApiResponse<T>> {
    intercept(context: ExecutionContext, next: CallHandler): Observable<ApiResponse<T>> {
        return next.handle().pipe(
            map(data => ({
                success: true,
                data,
                timestamp: new Date(),
            })),
        );
    }
}
```

### 조건부 타입을 활용한 DTO 변환

```typescript
// common/types/dto.types.ts
type ExcludeId<T> = Omit<T, 'id' | 'createdAt' | 'updatedAt'>;
type PartialExcept<T, K extends keyof T> = Partial<T> & Pick<T, K>;

// Create DTO는 id와 타임스탬프 제외
export type CreateDto<T> = ExcludeId<T>;

// Update DTO는 모든 필드 선택적, 단 id는 필수
export type UpdateDto<T> = PartialExcept<ExcludeId<T>, never>;

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
    age: number;
    createdAt: Date;
    updatedAt: Date;
}

type CreateUserDto = CreateDto<User>;
// { name: string; email: string; age: number; }

type UpdateUserDto = UpdateDto<User>;
// { name?: string; email?: string; age?: number; }
```

### 유틸리티 타입을 활용한 엔티티 변환

```typescript
// common/types/entity.types.ts
import { Pick, Omit, Partial } from '@nestjs/mapped-types';

// 공개 필드만 선택
export type PublicEntity<T> = Pick<T, 'id' | 'name' | 'email'>;

// 민감한 정보 제외
export type SafeEntity<T> = Omit<T, 'password' | 'salt' | 'token'>;

// 업데이트용 (id와 타임스탬프 제외)
export type UpdateEntity<T> = Partial<Omit<T, 'id' | 'createdAt' | 'updatedAt'>>;

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
    password: string;
    salt: string;
    createdAt: Date;
    updatedAt: Date;
}

type PublicUser = PublicEntity<User>;
// { id: number; name: string; email: string; }

type SafeUser = SafeEntity<User>;
// { id: number; name: string; email: string; createdAt: Date; updatedAt: Date; }
```

### 타입 안전한 이벤트 시스템

```typescript
// common/events/event.types.ts
type EventMap = {
    'user.created': { userId: number; name: string; email: string };
    'user.updated': { userId: number; changes: Record<string, any> };
    'user.deleted': { userId: number };
    'order.created': { orderId: number; userId: number; total: number };
};

type EventName = keyof EventMap;
type EventHandler<T extends EventName> = (data: EventMap[T]) => void | Promise<void>;

// common/events/event-emitter.service.ts
import { Injectable } from '@nestjs/common';

@Injectable()
export class EventEmitterService {
    private handlers: Map<EventName, EventHandler<any>[]> = new Map();

    on<T extends EventName>(event: T, handler: EventHandler<T>): void {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event)!.push(handler);
    }

    async emit<T extends EventName>(event: T, data: EventMap[T]): Promise<void> {
        const handlers = this.handlers.get(event) || [];
        await Promise.all(handlers.map(handler => handler(data)));
    }

    off<T extends EventName>(event: T, handler: EventHandler<T>): void {
        const handlers = this.handlers.get(event) || [];
        const index = handlers.indexOf(handler);
        if (index > -1) {
            handlers.splice(index, 1);
        }
    }
}

// 사용 예시
@Injectable()
export class UsersService {
    constructor(private eventEmitter: EventEmitterService) {}

    async create(createUserDto: CreateUserDto): Promise<User> {
        const user = await this.repository.save(createUserDto);
        
        // 타입 안전한 이벤트 발생
        await this.eventEmitter.emit('user.created', {
            userId: user.id,
            name: user.name,
            email: user.email,
        });
        
        return user;
    }
}

// 이벤트 리스너
@Injectable()
export class UserEventListener {
    constructor(private eventEmitter: EventEmitterService) {
        this.eventEmitter.on('user.created', async (data) => {
            // data는 자동으로 { userId: number; name: string; email: string } 타입
            console.log(`New user created: ${data.name} (${data.userId})`);
        });
    }
}
```

### 타입 안전한 쿼리 빌더

```typescript
// common/types/query.types.ts
type QueryOperator = 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'like' | 'in';

type QueryCondition<T> = {
    [K in keyof T]?: T[K] | {
        operator: QueryOperator;
        value: T[K] | T[K][];
    };
};

type QueryOptions<T> = {
    where?: QueryCondition<T>;
    orderBy?: Partial<Record<keyof T, 'asc' | 'desc'>>;
    limit?: number;
    offset?: number;
};

// common/services/query.service.ts
@Injectable()
export class QueryService {
    buildQuery<T>(options: QueryOptions<T>): string {
        // 쿼리 빌더 로직
        return '';
    }
}

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
    age: number;
}

const query = queryService.buildQuery<User>({
    where: {
        age: { operator: 'gte', value: 18 },
        email: { operator: 'like', value: '%@example.com' },
    },
    orderBy: { name: 'asc' },
    limit: 10,
});
```

### 제네릭 데코레이터

```typescript
// common/decorators/current-user.decorator.ts
import { createParamDecorator, ExecutionContext } from '@nestjs/common';

export const CurrentUser = createParamDecorator(
    (data: string | undefined, ctx: ExecutionContext) => {
        const request = ctx.switchToHttp().getRequest();
        const user = request.user;

        return data ? user?.[data] : user;
    },
);

// 타입 안전한 사용
interface UserPayload {
    id: number;
    email: string;
    roles: string[];
}

@Get('profile')
getProfile(@CurrentUser() user: UserPayload) {
    // user는 UserPayload 타입으로 추론됨
    return user;
}
```

### 타입 안전한 설정 모듈

```typescript
// config/config.module.ts
import { Module, DynamicModule } from '@nestjs/common';

export interface ConfigOptions {
    env: 'development' | 'staging' | 'production';
    database: {
        host: string;
        port: number;
        name: string;
    };
    jwt: {
        secret: string;
        expiresIn: string;
    };
}

@Module({})
export class ConfigModule {
    static forRoot(options: ConfigOptions): DynamicModule {
        return {
            module: ConfigModule,
            providers: [
                {
                    provide: 'CONFIG',
                    useValue: options,
                },
            ],
            exports: ['CONFIG'],
        };
    }
}

// 사용
@Module({
    imports: [
        ConfigModule.forRoot({
            env: 'development',
            database: {
                host: 'localhost',
                port: 3306,
                name: 'test',
            },
            jwt: {
                secret: 'secret',
                expiresIn: '1h',
            },
        }),
    ],
})
export class AppModule {}
```

## 참조 자료

### 공식 문서
- [NestJS 공식 문서](https://docs.nestjs.com/)
- [NestJS GitHub 저장소](https://github.com/nestjs/nest)
- [TypeScript 공식 문서](https://www.typescriptlang.org/docs/)

### 학습 자료
- [NestJS Fundamentals Course](https://learn.nestjs.com/)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)

### 도구 및 라이브러리
- [class-validator](https://github.com/typestack/class-validator)
- [class-transformer](https://github.com/typestack/class-transformer)
- [TypeORM](https://typeorm.io/)
- [Passport.js](http://www.passportjs.org/)

### 아키텍처 패턴
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)

### 성능 및 보안
- [OWASP Node.js Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html)
- [Node.js Performance Best Practices](https://nodejs.org/en/docs/guides/simple-profiling/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)









