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
