---
title: NestJS Guards
tags:
  - nestjs
  - guards
  - authorization
  - jwt
  - rbac
  - reflector
updated: 2026-06-06
---

# NestJS Guards

Guard는 요청이 라우트 핸들러까지 도달할지를 결정하는 컴포넌트다. 인증된 사용자인지, 특정 권한을 가졌는지, 특정 조건을 만족하는지를 판별하는 자리다. `CanActivate` 인터페이스 하나만 구현하면 끝나는 단순한 구조지만, 미들웨어·인터셉터와 역할이 헷갈리기 시작하면 어디에 무엇을 넣어야 할지 감이 안 잡힌다.

실무에서 Guard를 잘못 쓰는 사례가 꽤 많다. 미들웨어로 인가 처리를 하다가 Reflector를 못 써서 메타데이터 기반 권한 검사를 별도 로직으로 우회하거나, 인터셉터에서 토큰 검증을 하다가 핸들러보다 늦게 실행되어 응답 변환 단계에서 권한 오류를 내는 식이다. Guard의 자리를 정확히 이해해야 이런 혼란이 줄어든다.

## Guard, 미들웨어, 인터셉터의 자리

NestJS의 요청 라이프사이클에서 셋의 실행 순서가 다르다.

```
Request
  └─ Middleware
       └─ Guard
            └─ Interceptor (before)
                 └─ Pipe
                      └─ Handler
                 └─ Interceptor (after)
                      └─ Exception Filter
                           └─ Response
```

미들웨어는 가장 먼저 실행된다. Express/Fastify의 미들웨어와 같은 자리다. 라우트 매칭 이전에도 동작할 수 있고, NestJS의 실행 컨텍스트(`ExecutionContext`)에 접근할 수 없다. 어떤 핸들러가 호출될지, 어떤 컨트롤러 클래스인지, 어떤 메서드인지 모른다. 그래서 라우트별 권한 처리에는 부적합하다.

Guard는 미들웨어 다음에 실행된다. 핵심은 `ExecutionContext`를 받는다는 점이다. 어떤 컨트롤러의 어떤 메서드인지 알 수 있고, 클래스나 메서드에 붙은 데코레이터의 메타데이터를 `Reflector`로 읽어올 수 있다. 즉, "이 라우트는 admin만 접근 가능" 같은 메타데이터 기반 권한 검사를 할 수 있는 첫 자리다.

인터셉터는 Guard보다 늦게 실행된다. 정확히는 핸들러 전후를 감싼다. 그래서 인터셉터에서 인가 검사를 하면 이미 Guard가 통과시킨 요청에 대해 추가 처리를 하는 셈인데, "통과·차단"이라는 이진 결정에 인터셉터를 쓸 이유가 없다. 인터셉터는 로깅, 응답 변환, 캐싱, 타임아웃 같은 횡단 관심사에 쓴다.

정리하면 이렇다.

- **미들웨어**: 요청 객체에 무언가 붙이거나 변형. CORS, body parsing, 로깅 헤더 추가. 라우트 정보가 필요 없는 일.
- **Guard**: "통과시킬지 말지"의 이진 결정. 인증, 인가, 권한 검사.
- **인터셉터**: 핸들러 전후 처리. 응답 변환, 로깅, 캐싱, 타임아웃.

미들웨어에서 토큰 파싱은 가능하다. 하지만 "관리자만 접근" 같은 메타데이터 기반 분기는 Guard에서 한다. JWT 디코딩과 사용자 주입은 미들웨어에서 하고, 권한 검사는 Guard에서 분리하는 패턴이 흔하다.

## CanActivate 인터페이스

Guard는 `CanActivate` 인터페이스 하나만 구현하면 된다.

```typescript
export interface CanActivate {
  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean>;
}
```

반환값은 세 가지 중 하나다.

- `true`: 통과
- `false`: 차단 (자동으로 `ForbiddenException` 던짐)
- `Promise<boolean>` 또는 `Observable<boolean>`: 비동기 처리 후 위 둘 중 하나

`false`를 반환하면 NestJS가 자동으로 403을 던지지만, 메시지를 커스터마이즈하고 싶으면 `throw new UnauthorizedException('토큰 만료됨')` 식으로 직접 예외를 던지는 편이 낫다. 클라이언트가 401과 403을 구분해야 하는 경우가 많아서다.

가장 단순한 Guard 예시다.

```typescript
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';

@Injectable()
export class SimpleAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return request.headers['x-api-key'] === process.env.INTERNAL_API_KEY;
  }
}
```

이 Guard는 내부 API 호출에 흔히 쓰는 패턴이다. 헤더에 정해진 키가 있는지만 확인한다. 운영 환경에서 키 노출 사고가 있을 수 있으므로 HMAC 서명 같은 방식이 더 안전하다.

### Observable 반환 시 주의점

`Observable<boolean>`을 반환할 수 있다는 점 때문에 RxJS 기반으로 Guard를 짜는 경우가 있다. 한 가지 함정은 NestJS가 첫 번째 emit 값만 본다는 점이다. 스트림이 여러 값을 흘려도 두 번째 이후는 무시된다. `take(1)` 또는 단발성 Observable로 만들어야 의도대로 동작한다.

```typescript
import { from, map } from 'rxjs';

canActivate(context: ExecutionContext): Observable<boolean> {
  return from(this.authService.validateToken(token)).pipe(
    map(user => {
      if (!user) throw new UnauthorizedException();
      context.switchToHttp().getRequest().user = user;
      return true;
    }),
  );
}
```

Observable이 에러를 throw하면 그 에러가 그대로 응답까지 전달된다. `catchError`에서 RxJS 에러를 NestJS 예외로 변환하지 않으면 5xx로 떨어진다.

### 동기 vs 비동기 선택

`canActivate`를 `async`로 선언하면 어떤 경우든 `Promise<boolean>`이 된다. 동기 가드를 굳이 `async`로 만들 필요는 없지만, 일부분만 비동기인 가드에서 일관성을 위해 전부 `async`로 두는 편이 안전하다. 가장 흔한 사고가 동기 분기에서 `return true`만 하고 비동기 분기에서 `await`를 빼먹는 경우다. 항상 `Promise<boolean>`을 반환한다고 가정하고 함수를 설계하면 이 실수가 줄어든다.

### 차단의 의미를 정확히 하라

`false` 반환과 `throw` 사이에는 미묘한 차이가 있다. `false`를 반환하면 NestJS가 던지는 `ForbiddenException`의 메시지가 일반화된 문자열이라 디버깅이 힘들다. 운영 로그를 봐도 어느 Guard가 차단했는지 파악이 어렵다. 차단할 때마다 명시적으로 예외를 던지고, 차단 사유를 메시지나 별도 로깅에 남기는 편이 운영에 유리하다.

```typescript
if (!user.isVerified) {
  this.logger.warn(`미인증 사용자 접근 차단: userId=${user.id}, route=${context.getHandler().name}`);
  throw new ForbiddenException('이메일 인증이 필요합니다');
}
```

## Guard 적용 범위

Guard는 세 곳에 붙일 수 있다.

```typescript
// 핸들러 단위
@UseGuards(JwtAuthGuard)
@Get('me')
getMyProfile() { ... }

// 컨트롤러 단위
@UseGuards(JwtAuthGuard)
@Controller('users')
export class UsersController { ... }

// 전역
@Module({
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
  ],
})
export class AppModule {}
```

전역 Guard를 깔고 특정 라우트만 인증을 면제하고 싶을 때 `@Public()` 같은 커스텀 데코레이터를 만든다. 이게 Reflector 활용의 전형이다.

```typescript
import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
```

```typescript
@Public()
@Get('health')
healthCheck() {
  return { status: 'ok' };
}
```

전역 Guard에서 `@Public()` 메타데이터가 붙은 핸들러는 그냥 통과시킨다.

```typescript
@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;

    return this.verifyToken(context);
  }

  private async verifyToken(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const token = request.headers.authorization?.replace('Bearer ', '');
    if (!token) throw new UnauthorizedException('토큰 없음');

    try {
      request.user = await this.jwtService.verify(token);
      return true;
    } catch (e) {
      throw new UnauthorizedException('토큰 검증 실패');
    }
  }
}
```

전역 Guard + `@Public()` 패턴은 화이트리스트보다 블랙리스트 방식이 안전할 때 쓴다. 인증을 기본값으로 깔고 공개 엔드포인트만 예외 처리하는 식이다. 인증이 필요한 라우트가 더 많은 일반적인 API 서버에 잘 맞는다.

## Reflector와 메타데이터 기반 권한 처리

Reflector는 NestJS가 제공하는 메타데이터 리더다. `@SetMetadata`나 커스텀 데코레이터로 붙인 메타데이터를 핸들러·클래스 양쪽에서 읽는다. 주요 메서드는 네 가지다.

- `get(key, target)`: 특정 대상에서만 읽기
- `getAll(key, targets)`: 여러 대상에서 배열로 읽기
- `getAllAndMerge(key, targets)`: 여러 대상에서 배열·객체를 병합
- `getAllAndOverride(key, targets)`: 첫 번째로 찾은 값을 우선

`getAllAndOverride`는 "핸들러 메타데이터가 있으면 그걸 쓰고, 없으면 컨트롤러 메타데이터를 쓴다" 같은 우선순위 처리에 쓴다. 컨트롤러 단위로 `@Roles('admin')`을 걸어두고 특정 핸들러만 `@Roles('user')`로 덮어쓰는 시나리오가 흔하다.

```typescript
// Roles 데코레이터
export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);
```

```typescript
@Roles('admin')
@Controller('admin')
export class AdminController {
  @Get('dashboard')
  getDashboard() { ... }  // admin만 접근

  @Roles('admin', 'auditor')  // 핸들러 메타데이터가 우선
  @Get('audit-logs')
  getAuditLogs() { ... }  // admin 또는 auditor 접근
}
```

`getAllAndMerge`는 컨트롤러와 핸들러 메타데이터를 합쳐야 할 때 쓴다. 예를 들어 "컨트롤러 전체에 read 권한이 필요하고, 특정 핸들러는 write도 추가로 필요"한 경우다.

```typescript
@RequirePermissions('users:read')
@Controller('users')
export class UsersController {
  @RequirePermissions('users:write')
  @Post()
  create(@Body() dto: CreateUserDto) { ... }
}
```

`getAllAndMerge`로 읽으면 `['users:read', 'users:write']` 두 개가 모두 필요한 권한으로 합쳐진다. 누적이 필요한 권한 모델에 맞는 방식이다.

### 메타데이터 키 충돌

`SetMetadata`의 키를 문자열 리터럴로 직접 박는 사람이 많은데, 키 이름이 겹치면 라이브러리가 사용하는 메타데이터와 충돌할 수 있다. `@nestjs/common`이 내부적으로 `path`, `method`, `guards` 같은 키를 쓰고 있어서 이런 키를 그대로 쓰면 라우팅이 깨지는 사고가 난다. 키 상수는 모듈 이름이나 도메인 접두사를 붙여 격리한다.

```typescript
export const ROLES_KEY = Symbol('auth:roles');
export const PERMISSIONS_KEY = Symbol('auth:permissions');
```

`Symbol`을 키로 쓰면 충돌 가능성이 0이 된다. 다만 `getAllAndOverride`나 `getAll`은 Symbol 키를 그대로 받아들이므로 동작에 차이는 없다. 문자열 키를 쓰더라도 `'auth.roles'` 같은 네임스페이스 접두사를 붙이는 편이 안전하다.

### Reflector 메서드 선택 기준

- 메서드 하나에만 메타데이터를 박는다면 `get`으로 충분하다.
- 컨트롤러 단위 폴백이 필요하면 `getAllAndOverride`.
- 누적 권한 모델이면 `getAllAndMerge`.
- 여러 데코레이터를 다중 키로 읽어 합쳐야 하면 `getAll`로 받아 직접 처리.

`getAllAndOverride`를 무지성으로 쓰는 경우가 많은데, 누적이 필요한 곳에서 이 메서드를 쓰면 컨트롤러 권한이 핸들러 권한에 의해 통째로 덮여 보안 사고가 난다. 메타데이터의 의미가 "추가"인지 "덮어쓰기"인지를 먼저 결정해야 한다.

### 커스텀 데코레이터 팩토리

`SetMetadata` 자체를 노출하지 말고 의미를 가진 데코레이터로 감싸는 편이 낫다. 데코레이터 시그니처에서 인자 검증을 할 수 있고, 메타데이터 키를 외부에 노출하지 않을 수 있다.

```typescript
import { applyDecorators, SetMetadata, UseGuards } from '@nestjs/common';

export const Auth = (...roles: string[]) => {
  if (roles.length === 0) {
    throw new Error('Auth 데코레이터에는 최소 하나의 역할이 필요합니다');
  }
  return applyDecorators(
    SetMetadata(ROLES_KEY, roles),
    UseGuards(JwtAuthGuard, RolesGuard),
  );
};
```

`applyDecorators`로 여러 데코레이터를 묶으면 라우트마다 `@UseGuards(JwtAuthGuard, RolesGuard)`를 반복하지 않아도 된다. 사용처에서는 `@Auth('admin')` 한 줄이면 끝난다.

## Role/Permission Guard 구현

역할 기반 접근 제어(RBAC)는 가장 흔한 인가 패턴이다. 사용자에게 역할을 부여하고, 라우트마다 필요한 역할을 명시한다.

```typescript
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (!requiredRoles) return true;

    const { user } = context.switchToHttp().getRequest();
    if (!user) throw new UnauthorizedException('인증되지 않음');

    return requiredRoles.some(role => user.roles?.includes(role));
  }
}
```

이 Guard는 JWT Guard가 먼저 실행되어 `request.user`를 채워둔 상태를 전제로 한다. Guard의 실행 순서는 `@UseGuards(JwtAuthGuard, RolesGuard)` 처럼 데코레이터에 명시한 순서대로다.

### 역할 계층 처리

플랫한 역할 모델은 금방 한계가 온다. "admin은 user의 모든 권한을 자동으로 가진다" 같은 계층 관계를 모든 라우트에 일일이 적기 시작하면 데코레이터가 지저분해진다. 역할 계층을 Guard 내부에서 풀어주는 패턴이 깔끔하다.

```typescript
const ROLE_HIERARCHY: Record<string, string[]> = {
  superadmin: ['admin', 'manager', 'user'],
  admin: ['manager', 'user'],
  manager: ['user'],
  user: [],
};

function expandRoles(userRoles: string[]): Set<string> {
  const expanded = new Set<string>();
  for (const role of userRoles) {
    expanded.add(role);
    for (const child of ROLE_HIERARCHY[role] ?? []) {
      expanded.add(child);
    }
  }
  return expanded;
}

@Injectable()
export class HierarchicalRolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<string[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!required) return true;

    const { user } = context.switchToHttp().getRequest();
    const effective = expandRoles(user?.roles ?? []);
    return required.some(role => effective.has(role));
  }
}
```

DB나 설정 파일에서 계층을 로드해도 되지만, 변경 빈도가 낮으면 코드에 박아두는 편이 추적이 쉽다. 계층이 동적으로 바뀌어야 하면 Redis 캐시 + 갱신 이벤트로 동기화한다.

### Permission 기반 인가

RBAC만으로 부족한 경우가 있다. "관리자라도 다른 회사의 데이터는 못 봐야 한다" 같은 조건은 역할만으로 표현되지 않는다. 이럴 때는 권한(Permission) 단위로 쪼개거나, 리소스 기반 인가를 도입한다.

```typescript
// Permission 데코레이터
export const PERMISSIONS_KEY = 'permissions';
export const RequirePermissions = (...permissions: string[]) =>
  SetMetadata(PERMISSIONS_KEY, permissions);
```

```typescript
@Injectable()
export class PermissionsGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    private permissionService: PermissionService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const required = this.reflector.getAllAndOverride<string[]>(PERMISSIONS_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!required) return true;

    const { user } = context.switchToHttp().getRequest();
    const userPermissions = await this.permissionService.getPermissions(user.id);

    const hasAll = required.every(p => userPermissions.includes(p));
    if (!hasAll) {
      throw new ForbiddenException(`권한 부족: ${required.join(', ')}`);
    }
    return true;
  }
}
```

Permission Guard에서 매 요청마다 DB를 조회하면 성능 문제가 생긴다. 사용자별 권한을 Redis에 캐싱하거나, JWT 페이로드에 권한 목록을 박아 넣는 방식을 자주 쓴다. JWT에 박는 경우 토큰 크기가 커지고 권한 변경 시 즉시 반영되지 않는 문제가 있다. 권한 변경 빈도와 토큰 만료 시간의 균형을 보고 결정한다.

권한 캐시는 TTL을 짧게 가져가야 한다. 5분 이상으로 잡으면 권한 회수 시점과 실제 차단 시점 사이에 큰 갭이 생긴다. 보안 등급이 높은 시스템은 권한 변경 시 명시적으로 캐시를 무효화하는 이벤트 핸들러까지 만들어 두는 편이 안전하다.

### 리소스 기반 인가는 Guard에서 처리하기 까다롭다

리소스 기반 인가는 더 까다롭다. "이 게시글의 작성자만 수정 가능" 같은 조건은 라우트만 봐서는 판단이 안 된다. 게시글을 먼저 조회한 뒤 작성자와 현재 사용자를 비교해야 한다. 이 경우 Guard에서 처리하기도 하지만, 보통은 서비스 레이어로 옮기는 편이 깔끔하다. Guard는 라우트 수준의 정적 검사에 집중하고, 동적인 리소스 검사는 서비스에서 한다는 분리가 명확해야 한다.

Guard에서 굳이 처리하고 싶다면 URL 파라미터를 이용한다.

```typescript
@Injectable()
export class PostOwnerGuard implements CanActivate {
  constructor(private postRepository: PostRepository) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const postId = request.params.id;
    const post = await this.postRepository.findOne(postId);
    if (!post) throw new NotFoundException();
    if (post.authorId !== request.user.id) {
      throw new ForbiddenException('본인 게시글만 수정 가능');
    }
    request.post = post;
    return true;
  }
}
```

Guard에서 조회한 리소스를 `request`에 붙여두면 핸들러에서 중복 조회를 피할 수 있다. 다만 Guard 의존성이 늘어나고, Guard 단위 테스트가 무거워진다는 단점이 있다. 리소스 조회 로직이 복잡해지면 서비스로 옮기는 게 좋다.

## JWT Guard와의 결합

`@nestjs/passport`의 `AuthGuard('jwt')`를 그대로 쓰면 토큰 검증과 사용자 주입을 한 번에 처리한다. 그런데 실무에서는 `@Public()` 처리나 커스텀 에러 메시지 때문에 확장해서 쓰는 경우가 많다.

```typescript
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private reflector: Reflector) {
    super();
  }

  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;

    return super.canActivate(context);
  }

  handleRequest(err: any, user: any, info: any) {
    if (err || !user) {
      if (info?.name === 'TokenExpiredError') {
        throw new UnauthorizedException('토큰이 만료되었습니다');
      }
      if (info?.name === 'JsonWebTokenError') {
        throw new UnauthorizedException('유효하지 않은 토큰입니다');
      }
      throw err || new UnauthorizedException();
    }
    return user;
  }
}
```

`handleRequest`를 오버라이드하면 토큰 만료, 서명 오류, 토큰 없음 같은 케이스를 구분해서 다른 메시지를 줄 수 있다. 프론트엔드가 토큰 만료 시 자동으로 refresh를 시도하려면 이 구분이 필요하다.

Guard 체인을 구성할 때 순서가 중요하다. JWT Guard가 `request.user`를 채우고, 그다음 Roles Guard나 Permissions Guard가 `request.user`를 보고 판단하는 순서여야 한다.

```typescript
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
@Roles('admin')
@RequirePermissions('users:write')
@Post('users')
createUser(@Body() dto: CreateUserDto) { ... }
```

전역으로 JWT Guard를 깔고, Roles/Permissions는 필요한 라우트에만 붙이는 방식이 코드 중복을 줄인다.

```typescript
@Module({
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
  ],
})
export class AppModule {}
```

```typescript
@Roles('admin')
@UseGuards(RolesGuard)  // RolesGuard만 명시
@Get('admin/stats')
getStats() { ... }
```

JWT Guard는 이미 전역으로 깔려 있으니 RolesGuard만 추가로 붙이면 된다.

## 실행 컨텍스트 분기 처리 (HTTP/WS/RPC)

NestJS는 HTTP뿐 아니라 WebSocket, gRPC, Microservice 트랜스포트를 같은 모듈 구조로 다룬다. Guard도 이 모든 컨텍스트에서 동작할 수 있도록 설계되어 있다. `ExecutionContext.getType()`으로 현재 컨텍스트가 무엇인지 확인하고, 그에 맞게 요청 객체를 추출한다.

```typescript
@Injectable()
export class UniversalAuthGuard implements CanActivate {
  constructor(private jwtService: JwtService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const type = context.getType();
    let token: string | undefined;

    if (type === 'http') {
      const request = context.switchToHttp().getRequest();
      token = request.headers.authorization?.replace('Bearer ', '');
    } else if (type === 'ws') {
      const client = context.switchToWs().getClient();
      token = client.handshake?.auth?.token || client.handshake?.headers?.authorization;
    } else if (type === 'rpc') {
      const ctx = context.switchToRpc().getContext();
      token = ctx.get('authorization')?.[0];
    }

    if (!token) throw new UnauthorizedException('토큰 없음');

    try {
      const payload = await this.jwtService.verify(token);
      this.attachUser(context, type, payload);
      return true;
    } catch {
      throw new UnauthorizedException('토큰 검증 실패');
    }
  }

  private attachUser(context: ExecutionContext, type: string, payload: any) {
    if (type === 'http') {
      context.switchToHttp().getRequest().user = payload;
    } else if (type === 'ws') {
      const client = context.switchToWs().getClient();
      client.data = client.data || {};
      client.data.user = payload;
    }
  }
}
```

### WebSocket Guard의 함정

WebSocket Guard에서 주의할 점이 있다. WebSocket은 연결 수립 시 한 번만 인증하면 되는 게 보통이지만, NestJS의 Guard는 메시지 단위로도 동작할 수 있다. `@SubscribeMessage` 핸들러에 Guard를 붙이면 메시지마다 검증이 돈다. 토큰을 매번 검증하는 건 비효율적이라 핸드셰이크 시점에 검증한 사용자 정보를 `client.data.user`에 저장하고, 이후 메시지에서는 이 값을 신뢰하는 패턴이 흔하다.

```typescript
@WebSocketGateway()
export class ChatGateway implements OnGatewayConnection {
  constructor(private jwtService: JwtService) {}

  async handleConnection(client: Socket) {
    try {
      const token = client.handshake.auth?.token;
      const payload = await this.jwtService.verify(token);
      client.data.user = payload;
    } catch {
      client.disconnect(true);
    }
  }

  @UseGuards(WsRolesGuard)  // 메시지마다 역할 검사
  @Roles('admin')
  @SubscribeMessage('broadcast')
  handleBroadcast(@MessageBody() data: any) { ... }
}
```

`handleConnection`에서 검증한 사용자를 `client.data.user`에 저장하고, 이후 Guard는 이 값을 신뢰한다. 핸드셰이크 시점에 거부된 연결은 메시지 단계까지 도달하지 못한다.

### RPC/마이크로서비스 컨텍스트

gRPC나 마이크로서비스 컨텍스트에서는 메타데이터에 토큰을 실어 보낸다. NestJS의 `@nestjs/microservices` 사용 시 `context.switchToRpc().getContext()`로 메타데이터에 접근한다. 트랜스포트별로 메타데이터 형식이 달라서 (gRPC는 Metadata 객체, NATS는 헤더 등) 트랜스포트 종류까지 구분해야 할 수 있다.

```typescript
const type = context.getType<'http' | 'ws' | 'rpc'>();
```

이 제네릭은 마이크로서비스 패키지를 쓸 때 `'rpc'`로 확장된다. gRPC의 경우 `Metadata` 객체를 다뤄야 한다.

```typescript
import { Metadata } from '@grpc/grpc-js';

if (type === 'rpc') {
  const metadata = context.switchToRpc().getContext<Metadata>();
  const token = metadata.get('authorization')?.[0]?.toString();
}
```

마이크로서비스 트랜스포트마다 컨텍스트 객체 타입이 다르기 때문에, 가드 하나로 모든 트랜스포트를 다루면 분기 로직이 늘어난다. 트랜스포트별로 별도 Guard를 두고, 공통 검증 로직만 헬퍼 클래스로 추출하는 패턴이 유지보수에 유리하다.

### GraphQL 컨텍스트

GraphQL의 경우 `GqlExecutionContext.create(context)`로 별도 래핑이 필요하다.

```typescript
import { GqlExecutionContext } from '@nestjs/graphql';

@Injectable()
export class GqlAuthGuard implements CanActivate {
  canActivate(context: ExecutionContext) {
    const ctx = GqlExecutionContext.create(context);
    const request = ctx.getContext().req;
    return !!request.user;
  }
}
```

GraphQL은 HTTP 위에서 동작하지만 `context.switchToHttp().getRequest()`로는 정상적인 요청 객체를 못 얻는다. GraphQL 컨텍스트로 한 번 더 감싸야 한다. `getType()` 값도 `'http'`가 아니라 `'graphql'`이 나올 수 있어서 분기 처리할 때 주의가 필요하다.

GraphQL Subscription을 쓰는 경우 트랜스포트가 WebSocket이 된다. `context.getType()`만으로는 HTTP GraphQL과 WebSocket GraphQL을 구분하기 어렵다. `ctx.getInfo()`의 operation type을 보고 분기하거나, Subscription 전용 Guard를 따로 두는 편이 안전하다.

## 글로벌 가드와 DI 충돌 문제

전역 Guard 등록 방식이 두 가지인데, 둘 사이의 동작 차이가 사고의 원인이 된다.

```typescript
// 방식 1: useGlobalGuards (main.ts)
const app = await NestFactory.create(AppModule);
app.useGlobalGuards(new JwtAuthGuard(/* ??? */));

// 방식 2: APP_GUARD 프로바이더 (모듈)
@Module({
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
  ],
})
export class AppModule {}
```

방식 1은 Guard 인스턴스를 직접 만들어서 등록한다. NestJS의 DI 컨테이너 밖에서 생성되기 때문에 다른 서비스를 주입받을 수 없다. `JwtAuthGuard`가 `JwtService`나 `Reflector`를 필요로 하면 직접 인스턴스화할 수 없게 된다.

방식 2는 모듈 프로바이더로 등록되어 DI 컨테이너가 인스턴스를 만들어 준다. 다른 서비스를 자유롭게 주입받을 수 있다. 의존성이 있는 Guard는 항상 방식 2로 등록한다.

### 어느 모듈에 등록해야 하는가

`APP_GUARD`를 어느 모듈에서 등록하든 전역으로 적용된다. 하지만 Guard가 의존하는 서비스가 그 모듈의 스코프 안에 있어야 한다. `JwtAuthGuard`가 `JwtService`를 주입받는다면 `JwtModule`이 같은 모듈 또는 import된 상태여야 한다.

```typescript
@Module({
  imports: [JwtModule.register({ secret: 'xxx' })],
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
  ],
})
export class AuthModule {}
```

`AuthModule`에 `APP_GUARD`를 등록하고, `AppModule`에서 `AuthModule`을 import하는 구조다. 일부 개발자가 `AppModule`에 `APP_GUARD`만 박고 `JwtModule`을 import하지 않아서 런타임에 `JwtService를 찾을 수 없습니다` 에러를 만난다.

### 순환 의존성

`JwtAuthGuard`가 `AuthService`를 주입받고, `AuthService`가 다시 `UserService`를 주입받는데 `UserService`가 어떤 이유로 Guard를 알아야 한다면 순환 의존성이 생긴다. 이런 경우 `forwardRef`로 풀거나, Guard의 책임을 더 작은 단위로 쪼개야 한다.

실무에서는 Guard 안에 비즈니스 로직이 깊게 들어가지 않도록 막는 게 더 근본적인 해결책이다. Guard는 토큰을 디코딩하고 사용자 객체를 조회하는 정도까지만 한다. 사용자 상태 검사, 권한 산정 같은 로직은 별도 서비스로 분리한다.

### Request-scoped 프로바이더와의 충돌

`@Injectable({ scope: Scope.REQUEST })`로 만든 서비스를 Guard가 주입받으면 Guard 자체가 request-scoped가 된다. NestJS는 의존성 그래프 전체를 따라 스코프를 전파한다.

```typescript
@Injectable({ scope: Scope.REQUEST })
export class UserContextService { ... }

@Injectable()  // 자동으로 request-scoped로 변환됨
export class MyGuard implements CanActivate {
  constructor(private userContext: UserContextService) {}
  ...
}
```

`APP_GUARD`로 등록된 Guard가 request-scoped가 되면 요청마다 새 인스턴스가 만들어진다. 성능에 영향이 크다. 한 요청에 Guard가 여러 번 호출되는 경우도 있어서 (체인 구성에 따라) 인스턴스 생성 비용이 누적된다.

해결책은 Guard 안에서 request-scoped 서비스를 직접 주입받지 않는 것이다. `ModuleRef`로 동적으로 가져오거나, request 객체 자체에서 필요한 정보를 꺼낸다.

```typescript
@Injectable()
export class MyGuard implements CanActivate {
  constructor(private moduleRef: ModuleRef) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const userContext = await this.moduleRef.resolve(UserContextService, request[REQUEST_CONTEXT_ID]);
    // ...
  }
}
```

다만 이 패턴은 NestJS 내부 동작에 의존하기 때문에 복잡도가 높다. 가능하면 request-scoped 서비스 자체를 피하고, 필요한 데이터는 request 객체에 붙여두는 편이 단순하다.

### 등록 위치별 동작 정리

| 등록 방식 | DI | 인스턴스화 | 비고 |
|-----------|----|-----------|------|
| `app.useGlobalGuards(new Guard())` | 불가 | 수동 | 무의존 Guard에만 |
| `{ provide: APP_GUARD, useClass: Guard }` | 가능 | DI 컨테이너 | 전역, 의존성 OK |
| `{ provide: APP_GUARD, useExisting: Guard }` | 가능 | 기존 인스턴스 재사용 | 동일 모듈에 Guard도 등록 필요 |
| `@UseGuards(Guard)` (클래스 참조) | 가능 | DI 컨테이너 | 라우트/컨트롤러 단위 |
| `@UseGuards(new Guard())` (인스턴스) | 불가 | 수동 | 피하라 |

마지막 줄의 인스턴스 등록은 자주 보는 실수다. `@UseGuards(new RolesGuard())`처럼 인스턴스를 직접 넣으면 DI가 안 되고, Reflector를 주입받지 못해 메타데이터를 못 읽는다. 항상 클래스 참조로 넘긴다.

## Guard 테스트

Guard는 단위 테스트가 까다롭다. `ExecutionContext`를 모킹해야 하고, Reflector의 동작도 시뮬레이션해야 한다.

```typescript
describe('RolesGuard', () => {
  let guard: RolesGuard;
  let reflector: Reflector;

  beforeEach(() => {
    reflector = new Reflector();
    guard = new RolesGuard(reflector);
  });

  it('필요한 역할이 없으면 통과', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(undefined);
    const context = createMockContext({ user: { roles: [] } });
    expect(guard.canActivate(context)).toBe(true);
  });

  it('사용자가 필요한 역할을 가지면 통과', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(['admin']);
    const context = createMockContext({ user: { roles: ['admin'] } });
    expect(guard.canActivate(context)).toBe(true);
  });

  it('역할 부족 시 차단', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(['admin']);
    const context = createMockContext({ user: { roles: ['user'] } });
    expect(guard.canActivate(context)).toBe(false);
  });
});

function createMockContext(request: any): ExecutionContext {
  return {
    switchToHttp: () => ({
      getRequest: () => request,
    }),
    getHandler: () => ({}),
    getClass: () => ({}),
  } as any;
}
```

E2E 테스트에서는 실제 모듈을 띄우고 HTTP 요청을 보내서 검증하는 편이 안전하다. 단위 테스트는 Guard 로직 자체에, E2E는 Guard 체인의 통합 동작에 집중한다.

테스트에서 `Test.createTestingModule`로 모듈을 띄울 때 Guard를 오버라이드할 수 있다.

```typescript
const moduleRef = await Test.createTestingModule({
  imports: [AppModule],
})
  .overrideGuard(JwtAuthGuard)
  .useValue({ canActivate: () => true })
  .compile();
```

특정 시나리오에서 Guard를 무력화하고 핸들러 로직만 테스트하고 싶을 때 쓴다. 보안 관련 테스트가 아닌 비즈니스 로직 테스트에서는 이 패턴을 자주 쓴다.

## 실무에서 자주 겪는 문제

**문제 1: Guard에서 throw한 예외가 응답에 노출**

`UnauthorizedException('DB 조회 실패: connection timeout')` 같은 메시지를 클라이언트에 그대로 던지는 사고가 있다. 내부 오류 정보가 노출된다. Guard 내부에서 catch 후 일반화된 메시지로 다시 throw하는 패턴이 안전하다.

```typescript
try {
  const user = await this.userRepository.findOne(id);
  // ...
} catch (e) {
  this.logger.error('Guard 내부 오류', e);
  throw new UnauthorizedException('인증 처리 실패');
}
```

**문제 2: Guard 안에서 비동기 처리 잊음**

`canActivate`가 `Promise<boolean>`을 반환하는데 내부에서 `await`을 빼먹으면 항상 truthy한 Promise 객체가 반환되어 무조건 통과한다. 비동기 함수로 선언하고 모든 비동기 호출에 `await`을 붙이는 습관이 필요하다.

**문제 3: WebSocket에서 핸드셰이크 인증 누락**

`@UseGuards`를 메시지 핸들러에만 붙이고 연결 시점에는 인증을 안 하면, 인증 없이 연결된 클라이언트가 일부 메시지를 보낼 수 있다. Gateway의 `handleConnection`에서 명시적으로 토큰 검증을 하거나, `OnGatewayConnection`을 구현해 연결 거부 로직을 넣는다.

**문제 4: Guard의 순서 실수**

`@UseGuards(RolesGuard, JwtAuthGuard)` 처럼 RolesGuard를 먼저 두면 `request.user`가 아직 채워지지 않은 상태에서 역할 검사를 한다. JWT Guard가 먼저여야 한다. 전역으로 JWT Guard를 깔고 라우트에 Roles Guard만 추가하는 방식이 이런 실수를 줄인다.

**문제 5: 전역 Guard에서 모듈 import 누락**

`APP_GUARD`로 등록한 Guard가 `JwtService`를 주입받는데 등록한 모듈에 `JwtModule`이 import되어 있지 않으면 `Nest can't resolve dependencies` 에러가 부트스트랩 시점에 난다. 에러 메시지가 길어서 Guard와 무관해 보이지만, providers 목록을 잘 보면 `APP_GUARD`가 등장한다. Guard와 그 의존성은 같은 모듈에 함께 두는 게 추적이 쉽다.

**문제 6: 메타데이터 키가 라이브러리 키와 충돌**

`@SetMetadata('guards', ...)` 같이 NestJS가 내부적으로 쓰는 키와 동일한 문자열을 쓰면 라우팅이 깨진다. 키는 도메인 접두사를 붙이거나 Symbol로 만든다.

**문제 7: Guard가 request-scoped로 의도치 않게 변환**

Guard가 request-scoped 서비스를 주입받으면 Guard 자체가 request-scoped가 되어 요청마다 인스턴스를 새로 만든다. 트래픽이 많은 API에서는 성능 저하가 체감된다. Guard의 의존성은 가능한 한 singleton으로 유지한다.

## Guard와 다른 인가 처리 방식

Guard 외에 인가 로직을 둘 만한 곳이 몇 군데 더 있다.

**서비스 레이어**: 리소스 소유권 검사처럼 동적 조건이 들어가면 서비스에서 처리한다. `if (post.authorId !== userId) throw new ForbiddenException()` 같은 코드. Guard에서 처리하기 어렵다.

**커스텀 데코레이터 + Pipe 조합**: `@CurrentUser()` 같은 파라미터 데코레이터로 사용자 정보를 핸들러에 주입하고, Pipe에서 추가 검증. Guard보다 더 세밀한 통제가 가능하지만 복잡도가 올라간다.

**ABAC (Attribute-Based Access Control)**: CASL 같은 라이브러리로 정책을 선언적으로 표현하고, Guard 안에서 정책 엔진을 호출. RBAC로 표현이 어려운 복합 조건이 많을 때 도입한다.

```typescript
@Injectable()
export class PoliciesGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    private caslAbilityFactory: CaslAbilityFactory,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const handlers = this.reflector.get<PolicyHandler[]>(POLICY_KEY, context.getHandler()) ?? [];
    const { user } = context.switchToHttp().getRequest();
    const ability = this.caslAbilityFactory.createForUser(user);
    return handlers.every(handler => handler(ability));
  }
}
```

CASL은 정책을 함수로 표현하고, Guard에서 모든 정책이 통과하는지 확인한다. 권한 모델이 복잡해질수록 코드 자체로 표현하기 어려워지는데, CASL 같은 정책 엔진은 이 복잡도를 도메인 객체와 동작 쌍으로 추상화해 준다.

작은 서비스는 Guard 안에서 RBAC만으로 충분하다. 권한 모델이 복잡해지면 CASL이나 OPA 같은 외부 정책 엔진으로 옮기는 시점이 온다. 그 시점이 오기 전에 Guard 안에 인가 로직이 너무 비대해지지 않도록 주의한다. Guard는 "통과·차단"의 자리지, 비즈니스 로직의 자리가 아니다.
