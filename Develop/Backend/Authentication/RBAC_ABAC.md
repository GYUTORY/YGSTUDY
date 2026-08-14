---
title: "RBAC/ABAC 권한 모델 설계와 구현"
tags: [nodejs, rdbms, auth, backend]
updated: 2026-03-26
---

# RBAC/ABAC 권한 모델 설계와 구현

## RBAC (Role-Based Access Control)

사용자에게 역할(Role)을 부여하고, 역할에 권한(Permission)을 매핑하는 방식이다. 대부분의 서비스에서 기본 인가 모델로 사용한다.

핵심 개념은 세 가지다:

- **User**: 실제 사용자
- **Role**: 사용자에게 부여되는 역할 (ADMIN, MANAGER, USER 등)
- **Permission**: 역할이 수행할 수 있는 구체적인 행위 (READ_USER, WRITE_ORDER 등)

사용자가 직접 권한을 갖는 게 아니라, 역할을 통해 간접적으로 권한을 갖는다. 사용자가 수백 명이어도 역할은 몇 개로 관리할 수 있다.

---

## RBAC DB 스키마 설계

```sql
-- 사용자
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 역할
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,  -- ROLE_ADMIN, ROLE_MANAGER
    description VARCHAR(200)
);

-- 권한
CREATE TABLE permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,  -- USER_READ, ORDER_WRITE
    description VARCHAR(200)
);

-- 사용자-역할 매핑 (N:M)
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- 역할-권한 매핑 (N:M)
CREATE TABLE role_permissions (
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (permission_id) REFERENCES permissions(id)
);
```

테이블이 5개다. `user_roles`와 `role_permissions` 두 개의 매핑 테이블이 핵심이다.

NestJS에서는 역할 이름에 접두사를 강제하지 않는다. `@Roles('ADMIN')`처럼 직접 문자열로 지정하거나, enum으로 관리한다. Guard에서 `req.user.authorities`에 포함된 역할을 확인하는 방식이므로 DB 저장값과 일치하면 된다. 팀 내 컨벤션을 통일하는 게 낫다.

### 역할 계층 구조가 필요한 경우

ADMIN이 MANAGER의 권한을 포함하고, MANAGER가 USER의 권한을 포함하는 구조라면 별도 테이블을 추가한다:

```sql
CREATE TABLE role_hierarchy (
    parent_role_id BIGINT NOT NULL,
    child_role_id BIGINT NOT NULL,
    PRIMARY KEY (parent_role_id, child_role_id),
    FOREIGN KEY (parent_role_id) REFERENCES roles(id),
    FOREIGN KEY (child_role_id) REFERENCES roles(id)
);
```

NestJS에서는 `RolesGuard`와 `SetMetadata`로 역할 계층을 직접 구현한다:

```typescript
// roles.ts — 역할 계층 정의
export enum Role {
    ADMIN = 'ADMIN',
    MANAGER = 'MANAGER',
    USER = 'USER',
}

// 역할 계층: ADMIN > MANAGER > USER
export const ROLE_HIERARCHY: Record<Role, Role[]> = {
    [Role.ADMIN]:   [Role.ADMIN, Role.MANAGER, Role.USER],
    [Role.MANAGER]: [Role.MANAGER, Role.USER],
    [Role.USER]:    [Role.USER],
};
```

이렇게 하면 ADMIN으로 로그인한 사용자는 MANAGER, USER 권한을 모두 갖는다. `role_permissions` 테이블에 ADMIN에게 모든 권한을 일일이 매핑하지 않아도 된다.

---

## NestJS에서 역할-권한 매핑 구현

### Entity 설계

```typescript
import { Entity, PrimaryGeneratedColumn, Column, ManyToMany, JoinTable } from 'typeorm';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  username: string;

  @Column()
  password: string;

  @Column({ default: true })
  enabled: boolean;

  @ManyToMany(() => Role, { lazy: true })
  @JoinTable({
    name: 'user_roles',
    joinColumn: { name: 'user_id' },
    inverseJoinColumn: { name: 'role_id' },
  })
  roles: Promise<Role[]>;
}

@Entity('roles')
export class Role {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @ManyToMany(() => Permission, { lazy: true })
  @JoinTable({
    name: 'role_permissions',
    joinColumn: { name: 'role_id' },
    inverseJoinColumn: { name: 'permission_id' },
  })
  permissions: Promise<Permission[]>;
}

@Entity('permissions')
export class Permission {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;
}
```

TypeORM에서 ManyToMany 관계에 `lazy: true`를 설정한다. EAGER로 하면 사용자를 조회할 때마다 역할과 권한까지 전부 JOIN해서 가져온다. 인증 시점에만 필요한 데이터를 매 조회마다 끌어오면 성능 문제가 생긴다.

### Passport Strategy 구현

```typescript
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PassportStrategy } from '@nestjs/passport';
import { Strategy } from 'passport-local';
import * as bcrypt from 'bcrypt';
import { User } from './user.entity';

@Injectable()
export class LocalStrategy extends PassportStrategy(Strategy) {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {
    super({ usernameField: 'username' });
  }

  async validate(username: string, password: string): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { username },
      relations: ['roles', 'roles.permissions'],
    });

    if (!user || !user.enabled) {
      throw new UnauthorizedException('사용자 없음: ' + username);
    }

    const isValid = await bcrypt.compare(password, user.password);
    if (!isValid) {
      throw new UnauthorizedException('비밀번호 불일치');
    }

    return user;
  }
}

// 사용자의 역할과 권한 목록 추출 헬퍼
export async function getAuthorities(user: User): Promise<string[]> {
  const authorities = new Set<string>();

  const roles = await user.roles;
  for (const role of roles) {
    // 역할 자체를 authority로 추가
    authorities.add(role.name);

    // 역할에 매핑된 권한도 authority로 추가
    const permissions = await role.permissions;
    for (const permission of permissions) {
      authorities.add(permission.name);
    }
  }

  return Array.from(authorities);
}
```

`@Transactional(readOnly = true)`이 없으면 `LazyInitializationException`이 발생한다. `roles`와 `permissions`가 LAZY로 설정되어 있어서, 트랜잭션 밖에서 접근하면 프록시가 초기화되지 않는다.

### NestJS Guard 등록

```typescript
import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { RolesGuard } from './guards/roles.guard';

// NestJS에서는 Guard를 전역 또는 컨트롤러/메서드 단위로 적용한다.
// APP_GUARD로 전역 등록하면 모든 라우트에 기본 적용된다.
@Module({
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },  // JWT 인증 (전역)
    { provide: APP_GUARD, useClass: RolesGuard },    // 역할 인가 (전역)
  ],
})
export class AuthModule {}
```

메서드 레벨에서 세밀하게 제어할 수도 있다 (`@Roles`, `@Permissions` 커스텀 데코레이터 활용):

```typescript
import { Controller, Get, Post, Delete, Param, Body, UseGuards } from '@nestjs/common';
import { Roles } from './decorators/roles.decorator';
import { Permissions } from './decorators/permissions.decorator';
import { RolesGuard } from './guards/roles.guard';
import { Order } from './order.entity';

@Controller('api/orders')
@UseGuards(RolesGuard)
export class OrderController {

  @Get()
  @Permissions('ORDER_READ')
  getOrders(): Promise<Order[]> { /* ... */ return Promise.resolve([]); }

  @Post()
  @Permissions('ORDER_WRITE')
  createOrder(@Body() request: OrderRequest): Promise<Order> { /* ... */ return Promise.resolve({} as Order); }

  @Delete(':id')
  @Roles('ADMIN')
  deleteOrder(@Param('id') id: string): Promise<void> { /* ... */ return Promise.resolve(); }
}
```

---

## 동적 권한 관리 — DB 변경이 즉시 반영되지 않는 문제

실무에서 자주 마주치는 문제다. 관리자가 어떤 역할의 권한을 DB에서 변경했는데, 이미 로그인한 사용자에게 변경 사항이 반영되지 않는다.

### 왜 이런 일이 생기나

NestJS(Passport)는 인증 시점에 JWT Strategy의 `validate()`를 호출해서 권한 정보를 `req.user`에 저장한다. 이후 요청에서는 이 캐싱된 권한을 Guard가 사용한다. DB가 바뀌어도 이미 발급된 토큰·세션의 권한은 그대로다.

JWT를 쓰는 경우 더 심하다. 토큰 안에 권한 정보가 들어가 있으면, 토큰이 만료될 때까지 이전 권한이 유지된다.

### 해결 방법 1: 매 요청마다 권한 재조회

```typescript
import {
  Injectable,
  NestMiddleware,
} from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import { User } from './user.entity';
import { getAuthorities } from './auth.service';

// NestJS에서는 NestMiddleware 또는 NestInterceptor로 동적 권한 갱신을 구현한다.
@Injectable()
export class DynamicAuthorizationMiddleware implements NestMiddleware {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    private readonly jwtService: JwtService,
  ) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (token) {
      const payload = this.jwtService.verify<{ sub: string }>(token);

      // DB에서 최신 권한 조회
      const user = await this.userRepository.findOne({
        where: { username: payload.sub },
        relations: ['roles', 'roles.permissions'],
      });

      if (user) {
        // req.user에 최신 권한 주입 (Guard에서 참조)
        (req as Request & { user: unknown }).user = {
          username: user.username,
          authorities: await getAuthorities(user),
        };
      }
    }
    next();
  }
}
```

매 요청마다 DB를 조회하므로 부하가 크다. 사용자 수가 많은 서비스에서는 쓰면 안 된다. NestJS에서는 Middleware 또는 Guard에서 구현한다.

### 해결 방법 2: 캐시 + 이벤트 기반 갱신 (실무에서 많이 씀)

```typescript
import { Injectable, Inject } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { User } from './user.entity';
import { getAuthorities } from './auth.service';

const PERMISSION_TTL_MS = 5 * 60 * 1000; // 5분

@Injectable()
export class PermissionCacheService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @Inject(CACHE_MANAGER) private readonly cache: Cache,
  ) {}

  async getAuthorities(username: string): Promise<string[]> {
    const cacheKey = `permissions:${username}`;
    const cached = await this.cache.get<string[]>(cacheKey);
    if (cached) return cached;

    return this.loadFromDb(username);
  }

  private async loadFromDb(username: string): Promise<string[]> {
    const user = await this.userRepository.findOne({
      where: { username },
      relations: ['roles', 'roles.permissions'],
    });
    if (!user) throw new Error(`사용자 없음: ${username}`);

    const authorities = await getAuthorities(user);
    await this.cache.set(`permissions:${username}`, authorities, PERMISSION_TTL_MS);
    return authorities;
  }

  // 권한 변경 시 호출
  async evictUser(username: string): Promise<void> {
    await this.cache.del(`permissions:${username}`);
  }

  // 역할의 권한이 변경되면 해당 역할을 가진 모든 사용자의 캐시를 날린다
  async evictByRole(roleName: string): Promise<void> {
    const users = await this.userRepository
      .createQueryBuilder('u')
      .innerJoin('u.roles', 'r')
      .where('r.name = :roleName', { roleName })
      .select('u.username')
      .getMany();

    await Promise.all(users.map((u) => this.evictUser(u.username)));
  }
}
```

관리자 API에서 권한을 변경할 때 `evictByRole()`을 호출한다:

```typescript
import { Controller, Put, Param, Body, UseGuards } from '@nestjs/common';
import { Roles } from './decorators/roles.decorator';
import { RolesGuard } from './guards/roles.guard';
import { RoleService } from './role.service';
import { PermissionCacheService } from './permission-cache.service';

@Controller('admin/roles')
@UseGuards(RolesGuard)
@Roles('ADMIN')
export class RoleManagementController {
  constructor(
    private readonly roleService: RoleService,
    private readonly permissionCacheService: PermissionCacheService,
  ) {}

  @Put(':roleId/permissions')
  async updatePermissions(
    @Param('roleId') roleId: string,
    @Body() permissionIds: number[],
  ): Promise<void> {
    const role = await this.roleService.updatePermissions(Number(roleId), permissionIds);
    await this.permissionCacheService.evictByRole(role.name);
  }
}
```

캐시 TTL을 5분으로 설정했으므로, 이벤트가 누락되더라도 최대 5분 뒤에는 반영된다. NestJS `cache-manager`를 사용하며, Caffeine 대신 메모리 캐시(기본) 또는 Redis 스토어를 연결할 수 있다. 완전한 실시간은 아니지만 대부분의 서비스에서 충분하다.

**여기서 "메모리 캐시(기본)"를 그대로 쓰면 회수가 한 대에만 적용된다.** `cache-manager` 의 기본 스토어는 프로세스 메모리다. 서버가 세 대면 `evictByRole()` 을 호출한 그 한 대만 캐시를 비우고, 나머지 두 대는 TTL 이 끝날 때까지 옛 권한으로 판정한다. 사용자 눈에는 **요청이 어느 서버로 갔느냐에 따라 되기도 하고 안 되기도 하는** 것으로 보인다.

일반 캐시라면 5분 낡은 값이 괜찮다. 권한은 다르다. **권한 회수는 대개 사고 대응 중에 일어난다** — 계정이 털렸거나, 퇴사자를 막거나, 잘못 부여한 권한을 거두는 상황이다. "최대 5분"이 허용되는지는 그 5분에 무슨 일이 일어날 수 있는지로 판단해야 한다.

| 상황 | 5분 지연이 괜찮은가 |
|---|---|
| 권한 **추가** | 대체로 괜찮다. 사용자가 다시 시도하면 된다 |
| 역할 이름·설명 변경 | 괜찮다 |
| 권한 **회수**, 계정 정지 | 괜찮지 않다. 그 사이 실행되는 요청은 전부 통과한다 |

그래서 실무에서는 방향을 나눈다. 추가는 TTL 에 맡기고, **회수만 공유 저장소(Redis)에 즉시 반영**하거나 별도의 차단 목록을 두는 식이다. 어느 쪽이든 캐시가 프로세스 밖에 있어야 성립한다.

무효화 자체도 완전하지 않다. `evictByRole` 은 **호출 시점에 그 역할을 가진 사용자**만 찾는다. 역할에서 사용자를 빼는 것과 역할의 권한을 바꾸는 것이 다른 트랜잭션이면 그 사이 사용자는 어느 목록에도 안 잡힐 수 있다. 사용자가 많은 역할이면 `Promise.all` 로 개별 삭제를 수만 번 날리는 것도 부담이다. 이런 이유로 개별 키 삭제 대신 **전역 버전 번호를 올려 캐시 키를 통째로 무효화**하는 방식을 쓰기도 한다 — 정확도 대신 캐시 히트율을 내주는 선택이다.

### 해결 방법 3: JWT + 짧은 만료 시간 + 블랙리스트

JWT를 쓴다면 토큰에 권한을 넣지 않는 방법도 있다. 토큰에는 사용자 식별 정보만 넣고, 권한은 매번 서버에서 조회한다:

```typescript
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { PermissionCacheService } from './permission-cache.service';

interface JwtPayload {
  sub: string;
  iat: number;
  exp: number;
}

interface AuthenticatedUser {
  username: string;
  authorities: string[];
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private readonly configService: ConfigService,
    private readonly permissionCacheService: PermissionCacheService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get<string>('JWT_SECRET'),
    });
  }

  async validate(payload: JwtPayload): Promise<AuthenticatedUser> {
    // 토큰에서 권한을 꺼내지 않고, 캐시에서 조회
    const authorities = await this.permissionCacheService.getAuthorities(payload.sub);

    return { username: payload.sub, authorities };
  }
}
```

토큰에 권한을 넣으면 토큰 크기가 커지는 문제도 해결된다. 권한이 20개만 되어도 JWT 크기가 상당히 커진다. NestJS Passport에서 `validate()`의 반환값이 `req.user`가 되므로, 이 시점에 캐시에서 권한을 조회해 주입하면 된다.

---

## ABAC (Attribute-Based Access Control)

RBAC은 "이 사용자가 어떤 역할인가"로 판단한다. ABAC은 여기에 더해 사용자 속성, 리소스 속성, 환경 속성을 조합해서 판단한다.

예를 들어 "부서가 '영업팀'이고 문서의 보안등급이 '일반'이면 읽기 허용"은 RBAC으로 표현하기 어렵다. 이런 조건을 처리하려면 ABAC이 필요하다.

### ABAC 정책 구성 요소

| 구성 요소 | 설명 | 예시 |
|-----------|------|------|
| Subject | 요청 주체의 속성 | 부서, 직급, 소속 팀 |
| Resource | 대상 리소스의 속성 | 문서 보안등급, 소유자, 생성일 |
| Action | 수행하려는 행위 | READ, WRITE, DELETE |
| Environment | 요청 환경 | 시간, IP 대역, 접속 위치 |

### 정책 정의

```typescript
// 정책 효과
export enum PolicyEffect {
  PERMIT = 'PERMIT',
  DENY = 'DENY',
}

export interface SubjectCondition {
  department?: string;       // undefined이면 조건 무시
  position?: string;
  minLevel?: number;
}

export interface ResourceCondition {
  securityLevel?: string;
  ownerDepartment?: string;
  resourceType?: string;
}

export interface ActionCondition {
  allowedActions: string[];
}

export interface EnvironmentCondition {
  accessTimeFrom?: string;   // HH:MM 형식
  accessTimeTo?: string;
  allowedIpRanges?: string[];
}

export interface Policy {
  name: string;
  description: string;
  effect: PolicyEffect;        // PERMIT, DENY
  subject?: SubjectCondition;
  resource?: ResourceCondition;
  action?: ActionCondition;
  environment?: EnvironmentCondition;
}
```

### 정책 평가 엔진

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Policy, PolicyEffect, SubjectCondition, ResourceCondition, ActionCondition, EnvironmentCondition } from './policy.interface';
import { PolicyEntity } from './policy.entity';

export interface AccessRequest {
  username: string;
  userDepartment?: string;
  userLevel?: number;
  resourceType?: string;
  resourceId?: string;
  resourceSecurityLevel?: string;
  resourceOwnerDepartment?: string;
  action: string;
  requestIp?: string;
  requestTime?: Date;
}

@Injectable()
export class PolicyEvaluator {
  constructor(
    @InjectRepository(PolicyEntity)
    private readonly policyRepository: Repository<PolicyEntity>,
  ) {}

  async evaluate(request: AccessRequest): Promise<boolean> {
    const policies = await this.policyRepository.find({ where: { active: true } });

    // 기본 거부 (Deny by default)
    let permitted = false;

    for (const policy of policies) {
      if (!this.matches(policy, request)) {
        continue;
      }

      // DENY가 하나라도 매칭되면 즉시 거부
      if (policy.effect === PolicyEffect.DENY) {
        return false;
      }

      if (policy.effect === PolicyEffect.PERMIT) {
        permitted = true;
      }
    }

    return permitted;
  }

  private matches(policy: Policy, request: AccessRequest): boolean {
    return (
      this.matchesSubject(policy.subject, request) &&
      this.matchesResource(policy.resource, request) &&
      this.matchesAction(policy.action, request) &&
      this.matchesEnvironment(policy.environment, request)
    );
  }

  private matchesSubject(condition: SubjectCondition | undefined, request: AccessRequest): boolean {
    if (!condition) return true;

    if (condition.department != null && condition.department !== request.userDepartment) {
      return false;
    }
    if (condition.minLevel != null && (request.userLevel ?? 0) < condition.minLevel) {
      return false;
    }
    return true;
  }

  private matchesResource(condition: ResourceCondition | undefined, request: AccessRequest): boolean {
    if (!condition) return true;

    if (condition.securityLevel != null && condition.securityLevel !== request.resourceSecurityLevel) {
      return false;
    }
    if (condition.ownerDepartment != null && condition.ownerDepartment !== request.resourceOwnerDepartment) {
      return false;
    }
    return true;
  }

  private matchesAction(condition: ActionCondition | undefined, request: AccessRequest): boolean {
    if (!condition) return true;
    return condition.allowedActions.includes(request.action);
  }

  private matchesEnvironment(condition: EnvironmentCondition | undefined, request: AccessRequest): boolean {
    if (!condition) return true;

    const now = request.requestTime ?? new Date();
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    if (condition.accessTimeFrom != null && hhmm < condition.accessTimeFrom) {
      return false;
    }
    if (condition.accessTimeTo != null && hhmm > condition.accessTimeTo) {
      return false;
    }
    return true;
  }
}
```

DENY 우선 방식을 쓴다. PERMIT과 DENY가 동시에 매칭되면 DENY가 이긴다. 보안 정책에서는 거부가 허용보다 우선해야 한다. TypeScript에서도 동일한 로직으로 구현한다.

#### 선언은 했는데 검사하지 않는 조건이 셋 있다

인터페이스와 `matches*` 구현을 대조하면 세 필드가 어디에서도 쓰이지 않는다.

| 선언된 조건 | 검사하는 곳 |
|---|---|
| `SubjectCondition.position` | 없음 |
| `ResourceCondition.resourceType` | 없음 |
| `EnvironmentCondition.allowedIpRanges` | 없음 |

**조건이 무시되면 정책이 더 넓게 열린다.** PERMIT 정책에 `allowedIpRanges: ['10.0.0.0/8']` 을 적어 두면 관리자는 사내 IP 제한이 걸렸다고 믿지만 실제로는 모든 IP 에서 통과한다. 정책 화면에도 그대로 보이니 검토를 해도 안 잡힌다. 이런 종류의 결함은 **거부가 아니라 허용 쪽으로 실패한다는 점**에서 위험하다.

정책 엔진을 직접 만들 거면 **모르는 조건 키를 만났을 때 무시하지 말고 거부하거나 예외를 던지는 것**이 기본이어야 한다. 조건 스키마와 평가 구현을 한 자리에서 정의해 둘이 어긋날 수 없게 만드는 방법도 있다.

```typescript
const MATCHERS: Record<string, (v: unknown, req: AccessRequest) => boolean> = {
  department: (v, r) => v === r.userDepartment,
  minLevel:   (v, r) => (r.userLevel ?? 0) >= (v as number),
};

for (const [key, value] of Object.entries(policy.subject ?? {})) {
  const matcher = MATCHERS[key];
  if (!matcher) throw new Error(`알 수 없는 조건: ${key}`);  // 조용히 넘어가지 않는다
  if (!matcher(value, request)) return false;
}
```

#### 시간 조건이 자정을 넘으면 항상 거부한다

`matchesEnvironment` 는 `HH:MM` 문자열을 사전순으로 비교한다. 시작이 끝보다 큰 구간에서는 두 조건을 동시에 만족할 수 없다.

```
업무시간 09:00~18:00
  8시 → false    12시 → true    19시 → false      정상

야간 당직 22:00~06:00
  23시 → false   2시 → false    5시 → false       하루 종일 거부
```

`22:00~06:00`, `18:00~09:00` 같은 야간 구간은 당직·배치 작업 권한에서 흔하다. 정책을 등록한 사람은 야간에만 열린다고 생각하지만 실제로는 아무도 못 들어온다. 이쪽은 허용이 아니라 거부로 실패하니 발견은 되지만, 원인을 찾기 전까지는 "권한이 있는데 왜 안 되지" 로 시간을 쓴다. 자정을 넘는 경우를 나눠 처리한다.

```typescript
const from = condition.accessTimeFrom, to = condition.accessTimeTo;
if (from != null && to != null) {
  const inRange = from <= to
    ? (hhmm >= from && hhmm <= to)      // 같은 날 안에서
    : (hhmm >= from || hhmm <= to);     // 자정을 넘는 구간
  if (!inRange) return false;
}
```

시간대도 정해야 한다. `now.getHours()` 는 **서버의 로컬 타임존**을 쓴다. 서버가 UTC 로 돌고 정책은 KST 기준으로 적혀 있으면 창이 통째로 어긋난다. 시간 조건을 쓸 거면 정책에 타임존을 함께 저장하는 편이 안전하다.

#### 요청마다 정책 전체를 읽는다

`policyRepository.find({ where: { active: true } })` 가 인가 체크마다 돈다. 정책이 수십 개일 때는 문제가 없지만, 수백 개가 되고 요청마다 도는 순간 인가가 DB 부하의 원인이 된다. 정책은 자주 바뀌지 않으므로 캐싱하기 좋은 대상이고, 대신 위 권한 캐시와 똑같은 무효화 문제를 다시 떠안는다.

리소스 목록을 조회하는 API 에서는 더 큰 문제가 생긴다. 문서 100건을 반환하려면 100번 평가해야 하고, 정책이 리소스 속성(`resourceSecurityLevel`)을 보는 이상 **먼저 100건을 다 읽은 뒤 걸러야 한다.** 페이지네이션과 맞지 않는다 — 20건을 요청했는데 걸러 보니 3건만 남는 식이다. ABAC 을 도입하기 전에 **목록 조회를 어떻게 처리할지** 먼저 정해야 하고, 대개는 정책 일부를 SQL 조건으로 내려보내는 별도 경로를 만들게 된다. 이게 ABAC 의 가장 큰 숨은 비용이다.

### NestJS Guard와 연동

NestJS에서는 `AbacGuard`에서 `AbacPermissionService.check()`를 직접 호출한다:

```typescript
import { Injectable } from '@nestjs/common';
import { PolicyEvaluator, AccessRequest } from './policy-evaluator.service';

interface AuthenticatedUser {
  username: string;
  department?: string;
  level?: number;
}

@Injectable()
export class AbacPermissionService {
  constructor(private readonly policyEvaluator: PolicyEvaluator) {}

  async check(
    user: AuthenticatedUser,
    resourceType: string,
    resourceId: string,
    action: string,
  ): Promise<boolean> {
    const request: AccessRequest = {
      username: user.username,
      userDepartment: user.department,
      userLevel: user.level,
      resourceType,
      resourceId,
      action,
    };

    return this.policyEvaluator.evaluate(request);
  }
}
```

```typescript
import { Controller, Get, Delete, Param, UseGuards } from '@nestjs/common';
import { AbacGuard } from './guards/abac.guard';
import { AbacResource } from './decorators/abac-resource.decorator';
import { Document } from './document.entity';

@Controller('api/documents')
export class DocumentController {

  @Get(':id')
  @UseGuards(AbacGuard)
  @AbacResource({ type: 'DOCUMENT', action: 'READ' })
  getDocument(@Param('id') id: string): Promise<Document> { /* ... */ return Promise.resolve({} as Document); }

  @Delete(':id')
  @UseGuards(AbacGuard)
  @AbacResource({ type: 'DOCUMENT', action: 'DELETE' })
  deleteDocument(@Param('id') id: string): Promise<void> { /* ... */ return Promise.resolve(); }
}
```

NestJS에서는 Guard에서 `AbacPermissionService`를 주입해 `check()` 메서드를 직접 호출한다. `@SetMetadata`로 라우트에 리소스 정보를 붙이고 Guard가 이를 읽어 판단한다.

---

## 실무에서 RBAC + ABAC 혼합 패턴

대부분의 서비스에서 RBAC만으로 충분하다. ABAC은 "같은 역할이지만 조건에 따라 접근이 달라야 하는 경우"에만 도입한다.

### 패턴: 1차 RBAC, 2차 ABAC

```typescript
import { Injectable } from '@nestjs/common';
import { PolicyEvaluator, AccessRequest } from './policy-evaluator.service';

interface AuthenticatedUser {
  username: string;
  authorities: string[];
  department?: string;
  level?: number;
}

@Injectable()
export class HybridAuthorizationService {
  constructor(private readonly abacEvaluator: PolicyEvaluator) {}

  /**
   * RBAC으로 기본 접근 여부를 판단하고,
   * 추가 조건이 필요한 경우 ABAC 정책을 평가한다.
   */
  async check(
    user: AuthenticatedUser,
    resourceType: string,
    resourceId: string,
    action: string,
  ): Promise<boolean> {
    // 1차: RBAC — ADMIN은 모든 접근 허용
    if (this.hasRole(user, 'ADMIN')) {
      return true;
    }

    // 1차: RBAC — 해당 권한이 없으면 바로 거부
    const requiredPermission = `${resourceType}_${action}`;
    if (!this.hasAuthority(user, requiredPermission)) {
      return false;
    }

    // 2차: ABAC — 세부 조건 평가
    const request: AccessRequest = {
      username: user.username,
      userDepartment: user.department,
      userLevel: user.level,
      resourceType,
      resourceId,
      action,
    };
    return this.abacEvaluator.evaluate(request);
  }

  private hasRole(user: AuthenticatedUser, role: string): boolean {
    return user.authorities.includes(role);
  }

  private hasAuthority(user: AuthenticatedUser, authority: string): boolean {
    return user.authorities.includes(authority);
  }
}
```

```typescript
// Guard에서 HybridAuthorizationService를 주입해 check()를 호출한다
@Get('api/documents/:id')
@UseGuards(HybridAuthorizationGuard)
@SetMetadata('resource', { type: 'DOCUMENT', action: 'READ' })
async getDocument(@Param('id') id: string): Promise<Document> { /* ... */ return {} as Document; }
```

이 방식의 장점은 RBAC에서 걸러지면 ABAC 정책 평가를 하지 않는다는 것이다. ABAC 정책이 수십 개라도 RBAC에서 먼저 걸러내면 불필요한 연산을 줄일 수 있다. NestJS에서는 `HybridAuthorizationGuard`에서 `HybridAuthorizationService.check()`를 호출한다.

#### 다만 ADMIN 지름길이 ABAC 정책을 통째로 건너뛴다

첫 줄의 `if (this.hasRole(user, 'ADMIN')) return true;` 때문에 관리자에게는 어떤 DENY 정책도 적용되지 않는다. "업무 시간에만 접근", "사내 IP 에서만", "보안등급 이하만" — 위에서 예로 든 조건들이 전부 무력해진다. **가장 강한 계정이 가장 적은 통제를 받는 구조**이고, 계정이 탈취됐을 때 피해가 가장 큰 것도 그 계정이다.

DENY 는 역할과 무관하게 먼저 평가하는 편이 안전하다.

```typescript
// DENY 정책은 ADMIN 지름길보다 앞에 둔다
if (await this.abacEvaluator.hasMatchingDeny(request)) return false;
if (this.hasRole(user, 'ADMIN')) return true;
```

#### 역할과 권한이 한 배열에 섞여 있다

`hasRole` 과 `hasAuthority` 가 둘 다 `user.authorities.includes(x)` 를 본다. 이름만 다를 뿐 같은 검사다. 그래서 두 방향으로 사고가 난다.

- `ADMIN` 이라는 이름의 **권한**을 누군가 만들면, 그 권한을 가진 사용자가 위 지름길로 전부 통과한다.
- `DOCUMENT_READ` 라는 이름의 **역할**을 만들면 권한처럼 동작한다.

스프링 시큐리티가 역할에 `ROLE_` 접두사를 붙이는 관행을 갖는 이유가 이것이다. 한 배열에 담을 거면 접두사로 이름 공간을 나누고, 그럴 게 아니면 `roles` 와 `permissions` 를 분리해서 검사 함수가 서로 다른 것을 보게 만든다.

`requiredPermission = \`${resourceType}_${action}\`` 처럼 권한 이름을 문자열로 조립하는 것도 같은 부류의 위험이다. DB 에 등록된 권한명과 한 글자만 달라도 컴파일러가 잡지 못한다. 이쪽은 거부로 실패하니 그나마 낫지만, 새 리소스 타입을 추가할 때 권한 등록을 빠뜨리면 "권한을 줬는데 안 된다"는 문의로 돌아온다. 권한명은 상수나 enum 으로 모아 두고 조립은 그 안에서 한다.

### 실무에서 자주 쓰는 ABAC 조건들

```
# 본인 데이터만 접근 가능
subject.id == resource.ownerId

# 같은 부서 데이터만 접근 가능
subject.department == resource.department

# 업무 시간에만 접근 가능 (금융권에서 자주 씀)
environment.time >= 09:00 AND environment.time <= 18:00

# 사내 IP에서만 접근 가능
environment.ip IN allowedIpRanges

# 보안등급이 사용자 등급 이하인 리소스만 접근 가능
resource.securityLevel <= subject.clearanceLevel
```

"본인 데이터만 접근"은 거의 모든 서비스에서 필요한데, RBAC만으로는 표현이 안 된다. 이 하나 때문에라도 ABAC을 부분적으로 도입하는 경우가 많다.

### 주의할 점

**ABAC 정책을 DB에 저장하면 디버깅이 어렵다.** 왜 접근이 거부됐는지 추적하려면 어떤 정책이 매칭됐는지 로그를 남겨야 한다. NestJS `Logger`를 사용한다:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PolicyEffect } from './policy.interface';
import { PolicyEntity } from './policy.entity';
import { AccessRequest } from './policy-evaluator.service';

@Injectable()
export class PolicyEvaluatorWithLogging {
  private readonly logger = new Logger(PolicyEvaluatorWithLogging.name);

  constructor(
    @InjectRepository(PolicyEntity)
    private readonly policyRepository: Repository<PolicyEntity>,
  ) {}

  async evaluate(request: AccessRequest): Promise<boolean> {
    const policies = await this.policyRepository.find({ where: { active: true } });
    let permitted = false;

    for (const policy of policies) {
      if (!this.matches(policy, request)) {
        continue;
      }

      this.logger.log(
        `정책 매칭: policy=${policy.name}, effect=${policy.effect}, user=${request.username}, resource=${request.resourceId}, action=${request.action}`,
      );

      if (policy.effect === PolicyEffect.DENY) {
        this.logger.warn(`접근 거부: policy=${policy.name}, user=${request.username}`);
        return false;
      }
      permitted = true;
    }

    if (!permitted) {
      this.logger.warn(
        `매칭된 PERMIT 정책 없음: user=${request.username}, resource=${request.resourceId}, action=${request.action}`,
      );
    }

    return permitted;
  }

  private matches(_policy: PolicyEntity, _request: AccessRequest): boolean {
    // 실제 구현은 PolicyEvaluator.matches()와 동일
    return true;
  }
}
```

**정책 순서 의존성을 만들지 않는다.** 정책 간에 순서가 중요해지면 관리가 불가능해진다. "DENY 우선" 규칙 하나로 충분하다. 정책 순서에 따라 결과가 달라지는 구조는 시간이 지나면 아무도 이해하지 못한다. NestJS Logger로 정책 매칭 결과를 남기면 디버깅이 쉬워진다.

**RBAC으로 해결 가능한 건 RBAC으로 한다.** ABAC은 유연하지만 복잡하다. "관리자만 삭제 가능"을 ABAC 정책으로 만들 이유가 없다. `@Roles('ADMIN')`과 `RolesGuard`이면 된다.

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
