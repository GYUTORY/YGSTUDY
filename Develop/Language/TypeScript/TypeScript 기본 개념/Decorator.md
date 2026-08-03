---
title: TypeScript 데코레이터
tags: [typescript, decorator, nestjs, reflect-metadata, tc39, experimental-decorators]
updated: 2026-08-03
---

# TypeScript 데코레이터

데코레이터는 클래스·메서드·프로퍼티·파라미터에 메타데이터를 붙이거나 동작을 변경하는 문법이다. TypeScript에는 현재 두 개의 구현이 공존한다. `experimentalDecorators: true`로 활성화하는 레거시 방식과 TypeScript 5.0부터 기본 지원하는 TC39 Stage 3 방식이다. 문법이 비슷해 보이지만 내부 동작이 완전히 다르다.

## tsconfig 설정 차이

### 레거시 데코레이터 (TypeScript 4.x 스타일)

```json
{
  "compilerOptions": {
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true
  }
}
```

`emitDecoratorMetadata`는 `reflect-metadata` 폴리필과 함께 써야 의미가 있다. 이 옵션이 켜지면 TypeScript 컴파일러가 각 클래스의 생성자 파라미터 타입 정보를 `design:paramtypes`라는 키로 자동 emit한다. NestJS의 의존성 주입은 이 메타데이터를 읽어 작동한다.

```typescript
import 'reflect-metadata';

@Injectable()
class UserService {
  constructor(private readonly repo: UserRepository) {}
}

// 컴파일 후 JS에 이런 구문이 자동으로 생성된다
Reflect.metadata('design:paramtypes', [UserRepository])(UserService);
```

### TC39 Stage 3 데코레이터 (TypeScript 5.0+)

```json
{
  "compilerOptions": {
    // experimentalDecorators 없음 (또는 false)
    // emitDecoratorMetadata 불필요
  }
}
```

`experimentalDecorators`를 설정하지 않으면 TypeScript 5.0+는 TC39 Stage 3 스펙을 사용한다. `emitDecoratorMetadata`는 Stage 3 모드에서 동작하지 않고 `reflect-metadata` 기반 DI 시스템과 호환되지 않는다. NestJS는 2026년 현재까지 Stage 3 방식을 공식 지원하지 않는다.

## 레거시 데코레이터 동작 원리

레거시 데코레이터는 함수다. 어디에 붙이느냐에 따라 시그니처가 달라진다.

### 클래스 데코레이터

```typescript
function Sealed(constructor: Function) {
  Object.seal(constructor);
  Object.seal(constructor.prototype);
}

@Sealed
class BugReport {
  type = 'report';
  title: string;
  constructor(t: string) { this.title = t; }
}
```

클래스 정의가 끝난 직후 실행된다. 첫 번째 인자로 생성자 함수를 받는다. 반환값으로 새로운 생성자를 반환하면 원본 클래스를 교체할 수 있다.

### 메서드 데코레이터

```typescript
function Log(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
  const originalMethod = descriptor.value;

  descriptor.value = function (...args: any[]) {
    console.log(`${propertyKey} 호출:`, args);
    const result = originalMethod.apply(this, args);
    console.log(`${propertyKey} 반환:`, result);
    return result;
  };

  return descriptor;
}

class Calculator {
  @Log
  add(a: number, b: number) {
    return a + b;
  }
}
```

`PropertyDescriptor`의 `value`를 교체하는 방식이다. `this`를 올바르게 바인딩하려면 화살표 함수가 아니라 일반 함수로 래핑해야 한다. 화살표 함수를 쓰면 인스턴스의 `this`가 아니라 상위 스코프의 `this`를 캡처한다.

### 파라미터 데코레이터

```typescript
function Validate(target: Object, methodName: string, parameterIndex: number) {
  // parameterIndex: 0부터 시작하는 파라미터 위치
  const existing: number[] =
    Reflect.getOwnMetadata('validators', target, methodName) || [];
  existing.push(parameterIndex);
  Reflect.defineMetadata('validators', existing, target, methodName);
}
```

파라미터 데코레이터 자체로는 값을 변경하거나 검증할 수 없다. 메타데이터에 표시만 해두고, 메서드 데코레이터가 그 정보를 읽어 처리한다. NestJS의 `@Body()`, `@Param()`, `@Query()`가 이 패턴이다.

### 데코레이터 실행 순서

```typescript
@ClassDeco            // (4) 마지막
class Example {
  @MethodDeco         // (2)
  method(
    @ParamDeco arg    // (1) 가장 먼저
  ) {}

  @PropDeco           // (3)
  prop: string;
}
```

파라미터 → 메서드/프로퍼티(선언 역순) → 클래스 순서로 실행된다. 같은 대상에 여러 데코레이터가 겹치면 아래에서 위 순서다.

```typescript
@First   // (2)
@Second  // (1) — 안쪽이 먼저
class Foo {}
```

## TC39 Stage 3 데코레이터

TypeScript 5.0 이후 `experimentalDecorators` 없이 쓰는 데코레이터다. 시그니처가 완전히 바뀐다.

```typescript
// 레거시
function legacy(target: any, key: string, descriptor: PropertyDescriptor) { ... }

// TC39 Stage 3
function stage3(value: Function, context: ClassMethodDecoratorContext) { ... }
```

`context` 객체가 핵심이다. `kind`(데코레이터 대상 종류), `name`(요소 이름), `addInitializer`(인스턴스 초기화 훅)를 담고 있다.

```typescript
function readonly(value: Function, context: ClassMethodDecoratorContext) {
  context.addInitializer(function (this: any) {
    // 인스턴스가 생성될 때마다 실행된다
    Object.defineProperty(this, context.name, {
      value,
      writable: false,
    });
  });
}

class Circle {
  @readonly
  getArea() { return Math.PI * (this as any).radius ** 2; }
}
```

`accessor` 키워드는 Stage 3에서 추가됐다. 자동으로 getter/setter를 생성하고 데코레이터가 이를 가로챌 수 있다.

```typescript
function clamp(min: number, max: number) {
  return function (
    value: ClassAccessorDecoratorTarget<unknown, number>,
    context: ClassAccessorDecoratorContext,
  ): ClassAccessorDecoratorResult<unknown, number> {
    return {
      get(this: unknown) {
        return value.get.call(this);
      },
      set(this: unknown, v: number) {
        value.set.call(this, Math.min(Math.max(v, min), max));
      },
    };
  };
}

class Temperature {
  @clamp(0, 100)
  accessor celsius = 20;
}

const t = new Temperature();
t.celsius = 150;  // set 호출 → 100으로 클램핑
console.log(t.celsius);  // 100
```

레거시에서 같은 동작을 구현하려면 `Object.defineProperty`를 직접 써야 했다. `accessor`는 이 패턴을 언어 레벨에서 지원한다.

## NestJS 내부 동작

NestJS는 레거시 데코레이터와 `reflect-metadata`를 기반으로 구축돼 있다. Stage 3 방식으로 전환하면 DI 컨테이너 전체가 깨진다.

### @Controller

```typescript
// NestJS 소스 (단순화)
const PATH_METADATA = 'path';
const SCOPE_OPTIONS_METADATA = 'scope:options';

export const Controller = (prefix?: string | string[]): ClassDecorator => {
  const path = prefix
    ? Array.isArray(prefix) ? prefix : [prefix]
    : [''];

  return (target: object) => {
    Reflect.defineMetadata(PATH_METADATA, path, target);
    Reflect.defineMetadata(SCOPE_OPTIONS_METADATA, {}, target);
  };
};
```

`@Controller('users')`는 `Reflect.defineMetadata('path', ['users'], UserController)`를 실행한다. NestJS 라우터는 부트스트랩 과정에서 `Reflect.getMetadata('path', UserController)`로 경로를 읽어 라우팅 테이블을 구성한다.

```typescript
@Controller('users')
class UserController {
  @Get(':id')
  findOne(@Param('id') id: string) {}
}

// 내부 메타데이터 상태:
// Reflect.getMetadata('path', UserController)             → ['users']
// Reflect.getMetadata('path', UserController, 'findOne') → ':id'
// Reflect.getMetadata('method', UserController, 'findOne') → RequestMethod.GET
// Reflect.getMetadata('params', UserController, 'findOne') → [{ index: 0, type: 'param', data: 'id' }]
```

### @Injectable

```typescript
// NestJS 소스 (단순화)
const INJECTABLE_WATERMARK = '__injectable__';

export const Injectable = (options?: InjectableOptions): ClassDecorator => {
  return (target: object) => {
    Reflect.defineMetadata(INJECTABLE_WATERMARK, true, target);
    Reflect.defineMetadata(SCOPE_OPTIONS_METADATA, options, target);
  };
};
```

`@Injectable()` 자체는 마커 메타데이터 두 개만 저장한다. 의존성 주입의 핵심은 `emitDecoratorMetadata: true` 옵션이 활성화됐을 때 TypeScript 컴파일러가 자동으로 추가하는 부분이다.

```typescript
@Injectable()
class UserService {
  constructor(
    private readonly userRepo: UserRepository,
    private readonly mailer: MailService,
  ) {}
}

// 컴파일 결과 (자동 생성 부분):
__decorate([Injectable()], UserService);
__metadata('design:paramtypes', [UserRepository, MailService])(UserService);
```

NestJS IoC 컨테이너는 모듈 초기화 시 `Reflect.getMetadata('design:paramtypes', UserService)`를 호출해 `[UserRepository, MailService]`를 얻는다. 이 생성자 참조를 DI 토큰으로 사용해 이미 생성된 인스턴스를 주입한다.

인터페이스를 DI 토큰으로 쓸 수 없는 이유가 여기 있다. TypeScript 인터페이스는 컴파일 후 사라지므로 `design:paramtypes`에 남지 않는다. 이럴 때 `@Inject(TOKEN)` 파라미터 데코레이터로 수동 토큰을 지정한다.

```typescript
const DB_CONNECTION = Symbol('DB_CONNECTION');

@Injectable()
class UserRepository {
  constructor(@Inject(DB_CONNECTION) private db: DatabaseConnection) {}
  // Reflect.defineMetadata('self:paramtypes', [{ index: 0, token: DB_CONNECTION }], UserRepository)
  // design:paramtypes에서 index 0의 타입을 DB_CONNECTION으로 덮어쓴다
}
```

### @UseGuards와 Guard 실행 흐름

```typescript
// NestJS 소스 (단순화)
const GUARDS_METADATA = '__guards__';

export const UseGuards = (
  ...guards: (CanActivate | Function)[]
): MethodDecorator & ClassDecorator => {
  return (target: any, key?: string | symbol, descriptor?: any) => {
    if (descriptor) {
      // 메서드에 적용
      Reflect.defineMetadata(GUARDS_METADATA, guards, descriptor.value);
      return descriptor;
    }
    // 클래스에 적용
    Reflect.defineMetadata(GUARDS_METADATA, guards, target);
    return target;
  };
};
```

라우터 실행 파이프라인:

```
요청 수신
 → RouterExecutionContext가 클래스·메서드 GUARDS_METADATA 병합
 → 각 Guard의 canActivate(ExecutionContext) 실행
 → false 또는 예외 → ForbiddenException (403)
 → true → 인터셉터 → 파이프 → 핸들러 실행
```

클래스에 `@UseGuards`를 붙이면 컨트롤러의 모든 라우트에 적용된다. 메서드에 붙이면 해당 라우트에만 적용된다. NestJS는 클래스 레벨과 메서드 레벨 가드를 합친 후 순서대로 실행한다.

```typescript
@Injectable()
class AuthGuard implements CanActivate {
  constructor(private readonly jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const token = request.headers.authorization?.split(' ')[1];

    if (!token) return false;

    try {
      const payload = this.jwtService.verify(token);
      request['user'] = payload;
      return true;
    } catch {
      return false;
    }
  }
}

@Controller('admin')
@UseGuards(AuthGuard)     // 모든 admin 라우트에 적용
class AdminController {
  @Get('users')
  @UseGuards(RoleGuard)   // AuthGuard 다음으로 RoleGuard도 실행
  getUsers() {}
}
```

`@SetMetadata`로 Guard에 커스텀 데이터를 전달하는 패턴도 자주 쓴다.

```typescript
// roles.decorator.ts
export const Roles = (...roles: string[]) => SetMetadata('roles', roles);

// role.guard.ts
@Injectable()
class RoleGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    // Reflector는 클래스·메서드 메타데이터를 병합해 읽는 헬퍼다
    const roles = this.reflector.getAllAndOverride<string[]>('roles', [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!roles) return true;

    const { user } = context.switchToHttp().getRequest();
    return roles.some(role => user.roles?.includes(role));
  }
}

@Get('dashboard')
@Roles('admin')           // Reflect.defineMetadata('roles', ['admin'], handler)
@UseGuards(RoleGuard)
getDashboard() {}
```

## 실무에서 겪는 문제

**레거시와 Stage 3 혼용 불가**: 하나의 프로젝트에서 두 방식을 섞으면 예측하기 어려운 동작이 발생한다. NestJS 프로젝트는 `experimentalDecorators: true`를 반드시 유지해야 한다. Stage 3 데코레이터가 있는 라이브러리를 임포트할 때도 충돌이 날 수 있다.

**순환 참조로 `undefined` 주입**: `@Injectable()` 클래스들 사이에 순환 참조가 생기면 `design:paramtypes`에서 해당 타입이 `undefined`로 나온다. 모듈 로딩 시점에 클래스가 아직 정의되지 않아 참조를 캡처하지 못하기 때문이다. NestJS는 `forwardRef(() => ServiceClass)` 패턴으로 우회한다.

```typescript
// A가 B를 참조하고 B가 A를 참조하는 상황
@Injectable()
class ServiceA {
  constructor(@Inject(forwardRef(() => ServiceB)) private b: ServiceB) {}
}

@Injectable()
class ServiceB {
  constructor(@Inject(forwardRef(() => ServiceA)) private a: ServiceA) {}
}
```

**`reflect-metadata` import 누락**: `emitDecoratorMetadata: true` 설정 후 엔트리 포인트에서 `import 'reflect-metadata'`를 빠뜨리면 런타임에 `Reflect.defineMetadata is not a function` 에러가 난다. NestJS는 `@nestjs/core` 내부에서 자동 import하므로 NestJS 프로젝트에서는 대부분 숨겨진다. 직접 `reflect-metadata`를 쓰는 코드를 작성할 때는 최상단 파일에서 명시적으로 import해야 한다.

**팩토리 패턴과 직접 적용 구분**: 괄호 유무가 핵심이다.

```typescript
// 팩토리 패턴 — Controller()가 실제 데코레이터 함수를 반환한다
function Controller(prefix: string) {
  return function (target: Function) {
    Reflect.defineMetadata('path', prefix, target);
  };
}

// 직접 적용 — Sealed 함수 자체가 데코레이터다
function Sealed(target: Function) {
  Object.seal(target);
}

@Controller('users')  // Controller 호출 → 반환된 함수를 클래스에 적용
@Sealed               // Sealed를 클래스에 직접 적용
class UserController {}
```

데코레이터에 설정값을 넘겨야 한다면 팩토리 패턴을 쓴다. 고정된 동작만 필요하다면 직접 적용 방식이 단순하다.
