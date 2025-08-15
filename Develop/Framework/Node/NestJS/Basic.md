---
title: NestJS 기본 개념과 사용법
tags: [framework, node, nestjs, basic, nodejs, typescript, dependency-injection]
updated: 2025-08-15
---

# NestJS 기본 개념과 사용법

## 배경

NestJS는 현대적인 Node.js 애플리케이션 개발을 위한 강력한 프레임워크입니다. Express의 단순함을 유지하면서도, 엔터프라이즈급 애플리케이션 개발에 필요한 구조와 기능을 제공합니다. TypeScript를 기반으로 하여 타입 안정성을 보장하고, 의존성 주입을 통한 모듈화된 개발을 가능하게 합니다.

### NestJS의 필요성
- **구조화된 아키텍처**: 명확한 모듈, 컨트롤러, 서비스 구조 제공
- **타입 안정성**: TypeScript 기반으로 컴파일 타임 오류 방지
- **의존성 주입**: 객체 간의 결합도를 낮추고 테스트 용이성 확보
- **엔터프라이즈급 기능**: 대규모 프로젝트에 적합한 구조와 기능

### 기본 개념
- **모듈**: 애플리케이션의 기본 구성 단위
- **컨트롤러**: HTTP 요청을 처리하는 엔드포인트 정의
- **서비스**: 비즈니스 로직을 담당하는 클래스
- **의존성 주입**: 객체 간의 의존성을 자동으로 관리

## 핵심

### 1. Express와 NestJS의 차이점

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

### 2. NestJS의 핵심 개념

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

#### 컨트롤러 데코레이터
- `@Controller()`: 컨트롤러 클래스 정의
- `@Get()`, `@Post()`, `@Put()`, `@Delete()`: HTTP 메서드 매핑
- `@Param()`: URL 파라미터 추출
- `@Body()`: 요청 본문 데이터 추출
- `@Query()`: 쿼리 파라미터 추출
- `@Headers()`: 요청 헤더 추출

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

### 3. 미들웨어와 파이프

#### 미들웨어 (Middleware)
미들웨어는 요청과 응답 사이에서 실행되는 함수입니다.

```typescript
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
```

#### 파이프 (Pipes)
파이프는 데이터 변환과 유효성 검사를 담당합니다.

```typescript
@Get(':id')
findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
}

@Post()
create(@Body(ValidationPipe) createUserDto: CreateUserDto) {
    return this.usersService.create(createUserDto);
}
```

#### 주요 파이프
- `ValidationPipe`: DTO 유효성 검사
- `ParseIntPipe`: 문자열을 정수로 변환
- `ParseBoolPipe`: 문자열을 불리언으로 변환
- `ParseArrayPipe`: 배열 데이터 처리
- `ParseUUIDPipe`: UUID 문자열 검증

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```typescript
// DTO (Data Transfer Object)
export class CreateUserDto {
    @IsString()
    @IsNotEmpty()
    name: string;
    
    @IsEmail()
    email: string;
    
    @IsString()
    @MinLength(6)
    password: string;
}

export class UpdateUserDto {
    @IsOptional()
    @IsString()
    name?: string;
    
    @IsOptional()
    @IsEmail()
    email?: string;
}

// Entity
export class User {
    id: string;
    name: string;
    email: string;
    password: string;
    createdAt: Date;
    updatedAt: Date;
}

// Repository (실제로는 TypeORM 등 사용)
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

// Service
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

// Controller
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

// Module
@Module({
    controllers: [UsersController],
    providers: [UsersService, UsersRepository],
    exports: [UsersService]
})
export class UsersModule {}
```

### 2. 고급 패턴

#### 인터셉터 (Interceptors)
인터셉터는 요청과 응답을 가로채서 변환할 수 있습니다.

```typescript
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
가드는 인증, 권한 검사 등을 담당합니다.

```typescript
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

## 운영 팁

### 성능 최적화

#### 캐싱 활용
```typescript
@Injectable()
export class UsersService {
    @Cacheable('users')
    async findAll(): Promise<User[]> {
        // 데이터베이스에서 사용자 목록 조회
        return this.usersRepository.findAll();
    }
    
    @CacheEvict('users')
    async create(createUserDto: CreateUserDto): Promise<User> {
        // 새 사용자 생성 후 캐시 무효화
        return this.usersRepository.create(createUserDto);
    }
}
```

### 에러 처리

#### 글로벌 예외 필터
```typescript
@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
    catch(exception: unknown, host: ArgumentsHost) {
        const ctx = host.switchToHttp();
        const response = ctx.getResponse<Response>();
        const request = ctx.getRequest<Request>();
        
        const status = exception instanceof HttpException
            ? exception.getStatus()
            : HttpStatus.INTERNAL_SERVER_ERROR;
        
        const message = exception instanceof HttpException
            ? exception.message
            : 'Internal server error';
        
        response.status(status).json({
            statusCode: status,
            timestamp: new Date().toISOString(),
            path: request.url,
            message
        });
    }
}

// main.ts에서 등록
app.useGlobalFilters(new GlobalExceptionFilter());
```

## 참고

### NestJS vs Express 비교

| 측면 | Express | NestJS |
|------|---------|--------|
| **학습 곡선** | 낮음 | 중간 |
| **구조화** | 수동 | 자동 |
| **타입 안정성** | 없음 | TypeScript |
| **의존성 주입** | 없음 | 내장 |
| **테스트** | 수동 설정 | 자동 Mock |
| **확장성** | 작은 프로젝트 | 대규모 프로젝트 |

### NestJS 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **소규모 프로젝트** | Express 고려 | 빠른 개발 |
| **대규모 프로젝트** | NestJS 사용 | 구조화된 개발 |
| **팀 개발** | NestJS 사용 | 일관된 구조 |
| **타입 안정성** | NestJS 사용 | TypeScript 지원 |
| **마이크로서비스** | NestJS 사용 | 내장 지원 |

### 결론
NestJS는 현대적인 Node.js 애플리케이션 개발을 위한 강력한 프레임워크입니다.
TypeScript와 의존성 주입을 통해 타입 안정성과 테스트 용이성을 확보하세요.
모듈, 컨트롤러, 서비스의 명확한 구조를 활용하여 유지보수하기 쉬운 코드를 작성하세요.
대규모 프로젝트나 팀 개발에서 특히 유용하며, 엔터프라이즈급 기능을 제공합니다.

