---
title: 인증/인가 방식 비교
tags: [backend, authentication, authorization, session, jwt, oauth2, sso, api-key]
updated: 2026-03-26
---

# 인증/인가 방식 비교

## 개요

인증(Authentication)과 인가(Authorization)는 모든 백엔드 시스템에서 빠질 수 없다. 세션, JWT, OAuth2, API Key 등 여러 방식이 있고, 시스템 요구사항에 맞는 방식을 골라야 한다.

### 인증 vs 인가

```
인증 (Authentication): "너 누구야?"
  → 로그인, 신원 확인

인가 (Authorization): "너 이거 할 수 있어?"
  → 권한 확인, 접근 제어
```

## 핵심

### 1. 인증 방식 비교

| 항목 | Session | JWT | OAuth2 |
|------|---------|-----|--------|
| **상태** | Stateful (서버 저장) | Stateless (토큰 자체) | 둘 다 가능 |
| **저장 위치** | 서버 메모리/Redis | 클라이언트 (쿠키/헤더) | 인가 서버 |
| **확장성** | 세션 공유 필요 (Redis) | 서버 간 공유 불필요 | 높음 |
| **보안** | 서버 제어 (즉시 무효화) | 만료 전 무효화 어려움 | 토큰 위임 |
| **적합한 상황** | 전통적 웹, 소규모 | REST API, MSA | 소셜 로그인, 3rd party |

### 2. Session 기반 인증

```
1. 로그인 요청 (ID/PW)
2. 서버: 세션 생성, 세션 ID 발급
3. 클라이언트: 쿠키에 세션 ID 저장
4. 이후 요청마다 쿠키로 세션 ID 전송
5. 서버: 세션 ID → 세션 스토어 조회 → 사용자 확인

Client ──Cookie: JSESSIONID=abc123──▶ Server
                                       │
                                  Session Store
                                  (Memory / Redis)
```

**장점:**
- 서버가 세션을 완전히 제어 (즉시 로그아웃, 강제 종료)
- 구현이 단순 (Spring Security 기본)
- 민감 정보가 서버에만 존재

**단점:**
- 서버 수 증가 시 세션 공유 필요 (Sticky Session 또는 Redis)
- 모바일 앱에서 쿠키 관리 불편
- CSRF 공격에 취약 (쿠키 자동 전송)

```typescript
// NestJS 세션 설정 (express-session 사용)
import * as session from 'express-session';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);

  app.use(
    session({
      secret: process.env.SESSION_SECRET ?? 'change-me',
      resave: false,
      saveUninitialized: false,
      cookie: {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        maxAge: 30 * 60 * 1000, // 30분
      },
      // 동시 세션 1개 제한은 별도 미들웨어나 store 레벨에서 구현
    }),
  );

  await app.listen(3000);
}
bootstrap();
```

### 3. JWT 기반 인증

```
1. 로그인 요청 (ID/PW)
2. 서버: JWT Access Token + Refresh Token 발급
3. 클라이언트: 토큰 저장 (메모리/localStorage)
4. 이후 요청마다 Authorization 헤더로 전송
5. 서버: 토큰 서명 검증 → 페이로드에서 사용자 확인 (DB 조회 불필요)

Client ──Authorization: Bearer eyJhbG...──▶ Server
                                             │
                                      서명 검증만 (DB 조회 X)
```

**장점:**
- Stateless: 서버 확장 용이 (세션 공유 불필요)
- 모바일/SPA에 적합 (헤더 기반)
- 마이크로서비스 간 토큰 전달 용이

**단점:**
- 발급된 토큰 즉시 무효화 불가 (만료까지 유효)
- 토큰 크기가 세션 ID보다 큼 (매 요청 전송)
- 탈취 시 만료까지 악용 가능

#### Access Token / Refresh Token 분리

```
Access Token (짧은 수명: 15~30분)
  └─ API 요청 인증에 사용
  └─ 탈취 시 피해 최소화

Refresh Token (긴 수명: 7~14일)
  └─ Access Token 재발급에만 사용
  └─ DB/Redis에 저장하여 서버 측 무효화 가능
  └─ Rotation: 사용 시 새 Refresh Token 발급, 이전 것 폐기
```

```typescript
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import { RefreshToken } from './refresh-token.entity';

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
}

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(RefreshToken)
    private readonly refreshTokenRepository: Repository<RefreshToken>,
    private readonly jwtService: JwtService,
    private readonly dataSource: DataSource,
  ) {}

  // Refresh Token Rotation
  async refresh(refreshToken: string): Promise<AuthResponse> {
    // 1. Refresh Token 유효성 확인
    let email: string;
    try {
      const payload = this.jwtService.verify<{ email: string }>(refreshToken);
      email = payload.email;
    } catch {
      throw new UnauthorizedException('유효하지 않은 토큰');
    }

    return this.dataSource.transaction(async (manager) => {
      // 2. DB에서 저장된 Refresh Token과 비교
      const stored = await manager.findOne(RefreshToken, { where: { email } });
      if (!stored) {
        throw new UnauthorizedException('유효하지 않은 토큰');
      }

      if (stored.token !== refreshToken) {
        // 이미 사용된 토큰 → 탈취 의심 → 모든 토큰 무효화
        await manager.delete(RefreshToken, { email });
        throw new UnauthorizedException('토큰 재사용 감지. 재로그인 필요.');
      }

      // 3. 새 토큰 쌍 발급 (Rotation)
      const newAccessToken = this.jwtService.sign({ email, role: stored.role }, { expiresIn: '15m' });
      const newRefreshToken = this.jwtService.sign({ email }, { expiresIn: '14d' });

      // 4. 기존 Refresh Token 교체
      stored.token = newRefreshToken;
      await manager.save(stored);

      return { accessToken: newAccessToken, refreshToken: newRefreshToken };
    });
  }
}
```

JWT payload 설계, 만료 처리, Refresh Token Rotation의 구체적인 주의사항은 [API 인증/인가 실무 패턴](../API/API_Security_Patterns.md)에 정리되어 있다.

### 4. OAuth2 / OpenID Connect

**제3자 인증 위임** 방식이다. 사용자가 Google, Kakao 등에 로그인하면, 해당 서비스가 인증을 대신 처리한다.

```
1. 사용자 → "Google로 로그인" 클릭
2. Google 로그인 페이지로 리다이렉트
3. 사용자: Google에서 로그인
4. Google → 우리 서버로 Authorization Code 전달
5. 우리 서버: Code → Google API → Access Token 획득
6. 우리 서버: Access Token으로 Google 사용자 정보 조회
7. 우리 서버: 자체 JWT/Session 발급

사용자 ──▶ 우리 서비스 ──▶ Google (인가 서버)
                           │
                     Code 발급
                           │
            우리 서비스 ◀───┘
                │
          Token 교환 → 사용자 정보 획득
                │
          자체 JWT 발급
```

| 용어 | 설명 |
|------|------|
| **Authorization Code** | 일회용 코드 (토큰 교환에 사용) |
| **Access Token** | 리소스 접근용 토큰 (Google API 호출) |
| **Refresh Token** | Access Token 재발급용 |
| **Scope** | 접근 범위 (email, profile 등) |
| **OpenID Connect** | OAuth2 위에 인증 계층 추가 (ID Token) |

### 5. SSO (Single Sign-On)

한 번 로그인하면 여러 서비스에 자동 로그인되는 방식이다.

```
사용자 → 서비스 A (로그인 필요)
           │
      SSO 서버로 리다이렉트
           │
      SSO 서버에서 로그인
           │
      서비스 A 접근 가능
           │
사용자 → 서비스 B (로그인 필요)
           │
      SSO 서버 확인 → 이미 인증됨
           │
      서비스 B 접근 가능 (재로그인 불필요)
```

#### 구현 방식별 차이

**SAML**: XML 기반. 엔터프라이즈 환경(Active Directory, ADFS 등)에서 주로 쓴다. XML 파싱 때문에 구현이 번거롭고, 모바일 앱과는 궁합이 안 맞는다. 레거시 시스템과 연동해야 하는 경우가 아니면 선택할 이유가 별로 없다.

**OAuth2 + OIDC**: 모던 SSO의 사실상 표준. JSON 기반이라 다루기 쉽고, SPA/모바일에서도 잘 동작한다. Google Workspace, Okta, Azure AD 등 대부분의 IdP가 지원한다.

**자체 호스팅 (Keycloak 등)**: 인증 서버를 직접 운영해야 하는 경우. SaaS IdP에 사용자 데이터를 넘길 수 없거나, 인증 플로우를 세밀하게 제어해야 할 때 쓴다.

#### Keycloak으로 SSO 구현

Keycloak은 Realm(테넌트) 단위로 사용자와 클라이언트(서비스)를 관리한다. 같은 Realm에 등록된 서비스들은 SSO가 자동으로 동작한다.

Spring Boot에서 Keycloak 연동:

```yaml
# application.yml
spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            client-id: my-service
            client-secret: ${KEYCLOAK_CLIENT_SECRET}
            scope: openid, profile, email
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
        provider:
          keycloak:
            issuer-uri: https://auth.example.com/realms/my-realm
```

```typescript
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { Strategy, VerifyCallback } from 'passport-openidconnect';
import { ConfigService } from '@nestjs/config';

// Keycloak의 realm_access.roles를 NestJS 권한으로 매핑하는 전략
@Injectable()
export class OidcStrategy extends PassportStrategy(Strategy, 'oidc') {
  constructor(
    private readonly configService: ConfigService,
    private readonly userSyncService: UserSyncService,
  ) {
    super({
      issuer: configService.get<string>('OAUTH_ISSUER'),
      authorizationURL: `${configService.get<string>('OAUTH_ISSUER')}/protocol/openid-connect/auth`,
      tokenURL: `${configService.get<string>('OAUTH_ISSUER')}/protocol/openid-connect/token`,
      userInfoURL: `${configService.get<string>('OAUTH_ISSUER')}/protocol/openid-connect/userinfo`,
      clientID: configService.get<string>('OAUTH_CLIENT_ID'),
      clientSecret: configService.get<string>('OAUTH_CLIENT_SECRET'),
      callbackURL: configService.get<string>('OAUTH_REDIRECT_URI'),
      scope: ['openid', 'profile', 'email'],
    });
  }

  async validate(
    _issuer: string,
    profile: Record<string, unknown>,
    _context: unknown,
    idToken: string,
    accessToken: string,
    _refreshToken: string,
    _params: unknown,
    done: VerifyCallback,
  ): Promise<void> {
    try {
      // Keycloak의 realm_access.roles 추출
      const realmAccess = profile['realm_access'] as { roles?: string[] } | undefined;
      const roles = (realmAccess?.roles ?? []).map((role) => 'ROLE_' + role);

      const user = {
        sub: profile['id'] as string,
        email: profile['emails']?.[0],
        name: profile['displayName'] as string,
        roles,
        idToken,
        accessToken,
      };

      // Keycloak에서 받은 사용자 정보로 자체 DB 동기화
      // 최초 로그인 시 사용자 생성, 이후에는 정보 갱신
      await this.userSyncService.syncFromOidc(user);

      done(null, user);
    } catch (err) {
      done(err as Error);
    }
  }
}
```

#### SSO 운영 시 자주 겪는 문제

**세션 타임아웃 불일치**: Keycloak SSO 세션은 30분인데, 서비스 세션은 60분이면 문제가 생긴다. SSO 세션이 만료된 후 서비스 세션이 살아있는 동안은 접근이 되다가, 서비스 세션도 만료되면 갑자기 재로그인을 요구한다. Keycloak SSO 세션 타임아웃 >= 서비스 세션 타임아웃으로 맞춰야 한다.

**로그아웃 전파**: 서비스 A에서 로그아웃했는데 서비스 B에서는 여전히 로그인 상태인 경우가 흔하다. Keycloak의 Back-Channel Logout을 설정해야 한다.

```typescript
import { Controller, Post, Body } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Controller('logout')
export class LogoutController {
  constructor(
    private readonly jwtService: JwtService,
    private readonly sessionRegistry: SessionRegistry,
  ) {}

  // Back-Channel Logout 수신 엔드포인트
  @Post('/backchannel')
  async backChannelLogout(@Body('logout_token') logoutToken: string): Promise<void> {
    // logout_token에서 sid(세션 ID)를 추출
    const decoded = this.jwtService.decode<{ sid: string }>(logoutToken);
    const sessionId = decoded?.sid;
    if (!sessionId) return;

    // 해당 세션으로 로그인한 사용자의 로컬 세션 무효화
    await this.sessionRegistry.removeSession(sessionId);
  }
}
```

**서비스별 권한 분리**: Keycloak에서 Realm Role은 모든 서비스에 적용되고, Client Role은 특정 서비스에만 적용된다. 관리자 포털과 일반 사용자 앱이 같은 Realm에 있을 때, Realm Role만 쓰면 일반 사용자가 관리자 포털에 접근할 수 있다. Client Role로 서비스별 권한을 분리해야 한다.

### 6. API Key 인증

서버 간 통신이나 외부 API 연동에 사용하는 인증 방식이다.

```
Client ──X-API-Key: sk_live_abc123──▶ Server
```

**사용자 인증(JWT/Session)과의 차이**: API Key는 "어떤 서비스/클라이언트인지"를 식별하고, JWT/Session은 "어떤 사용자인지"를 식별한다. API Key로 사용자 인증을 대체하면 안 된다. 키 하나로 모든 요청이 나가기 때문에 누가 어떤 작업을 했는지 추적이 안 된다.

#### 발급과 저장

API Key는 발급 시점에 원본을 보여주고, DB에는 해시값만 저장한다. 비밀번호와 같은 원리다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { randomBytes, createHash } from 'crypto';
import { ApiKeyEntity } from './api-key.entity';

export interface ApiKeyResponse {
  rawKey: string;
  prefix: string;
  id: number;
}

@Injectable()
export class ApiKeyService {
  constructor(
    @InjectRepository(ApiKeyEntity)
    private readonly apiKeyRepository: Repository<ApiKeyEntity>,
  ) {}

  async issueApiKey(clientId: number, description: string): Promise<ApiKeyResponse> {
    const keyBytes = randomBytes(32);
    const rawKey = 'sk_live_' + keyBytes.toString('base64url');

    // prefix는 목록 조회/식별용
    const prefix = rawKey.substring(0, 12);

    // SHA-256 해시만 DB에 저장
    const hashedKey = createHash('sha256').update(rawKey).digest('hex');

    const entity = this.apiKeyRepository.create({
      clientId,
      keyHash: hashedKey,
      keyPrefix: prefix,
      description,
      createdAt: new Date(),
    });
    const saved = await this.apiKeyRepository.save(entity);

    // 원본은 이 응답에서만 반환. 이후 조회 불가
    return { rawKey, prefix, id: saved.id };
  }
}
```

`sk_live_` 같은 prefix를 붙이는 이유: 로그나 코드에 실수로 노출됐을 때 어떤 종류의 키인지 바로 알 수 있고, GitHub의 secret scanning 같은 도구가 탐지할 수 있다. Stripe, OpenAI 등이 이 패턴을 쓴다.

#### 검증 필터

```typescript
import { Injectable, NestMiddleware, UnauthorizedException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Request, Response, NextFunction } from 'express';
import { createHash } from 'crypto';
import { ApiKeyEntity } from './api-key.entity';

// 간단한 인메모리 캐시 (운영에서는 Redis 사용 권장)
const keyCache = new Map<string, { entity: ApiKeyEntity | null; expiresAt: number }>();

@Injectable()
export class ApiKeyAuthMiddleware implements NestMiddleware {
  constructor(
    @InjectRepository(ApiKeyEntity)
    private readonly apiKeyRepository: Repository<ApiKeyEntity>,
  ) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const apiKey = req.headers['x-api-key'] as string | undefined;
    if (!apiKey) {
      next();
      return;
    }

    const hashedKey = createHash('sha256').update(apiKey).digest('hex');

    // 캐시: DB 조회를 매 요청마다 하면 느리다
    let entity: ApiKeyEntity | null = null;
    const cached = keyCache.get(hashedKey);
    if (cached && cached.expiresAt > Date.now()) {
      entity = cached.entity;
    } else {
      entity = await this.apiKeyRepository.findOne({ where: { keyHash: hashedKey } }) ?? null;
      keyCache.set(hashedKey, { entity, expiresAt: Date.now() + 5 * 60 * 1000 }); // 5분 캐시
    }

    if (!entity) {
      res.status(401).end();
      return;
    }

    if (entity.revokedAt) {
      // 폐기된 키: 401이 아니라 403
      // 클라이언트가 키 재발급이 필요한지 구분할 수 있다
      res.status(403).json({ message: 'API Key revoked' });
      return;
    }

    // 요청 컨텍스트에 인증 정보 설정
    (req as Request & { apiKeyEntity: ApiKeyEntity }).apiKeyEntity = entity;
    next();
  }
}
```

#### 운영 시 주의사항

**키 폐기 시 캐시 무효화**: 위 코드처럼 캐시를 쓰면, 키를 폐기해도 캐시 TTL(5분) 동안은 계속 접근이 된다. 즉시 차단이 필요하면 폐기 시점에 캐시를 직접 날려야 한다.

```typescript
// ApiKeyService 내 메서드 — 키 폐기 + 캐시 즉시 무효화
import { Injectable, NotFoundException } from '@nestjs/common';

// (ApiKeyService 클래스 내부)
// async revokeApiKey(keyId: number, clientId: number): Promise<void>
export async function revokeApiKey(
  keyId: number,
  clientId: number,
  apiKeyRepository: ApiKeyRepository,
  keyCache: Map<string, ApiKey>,
): Promise<void> {
  const key = await apiKeyRepository.findOne({ where: { id: keyId, clientId } });
  if (!key) {
    throw new NotFoundException('API Key not found');
  }
  key.revokedAt = new Date();
  await apiKeyRepository.save(key);

  // 캐시 즉시 무효화
  keyCache.delete(key.keyHash);
}
```

**Rate Limit**: API Key별로 요청 제한을 걸어야 한다. 하나의 키가 전체 서버 리소스를 잡아먹는 걸 막아야 한다. Redis sliding window 방식이 실무에서 가장 많이 쓰인다. 구현 예시는 [API 인증/인가 실무 패턴](../API/API_Security_Patterns.md)에 있다.

**환경별 키 분리**: `sk_live_`(운영), `sk_test_`(테스트) 형태로 환경별 prefix를 다르게 두면, 테스트 키로 운영 API를 호출하는 실수를 서버 측에서 차단할 수 있다.

## 운영 시 공통 주의사항

**HTTPS 필수**: 토큰이든 쿠키든 세션 ID든, 평문(HTTP)으로 전송되면 네트워크에서 탈취당한다. 개발 환경이라도 가능하면 HTTPS를 쓰는 게 좋다. 운영에서는 당연히 필수다.

**비밀번호 해싱**: BCrypt를 쓰고 cost는 10 이상으로 잡는다. SHA-256으로 비밀번호를 해싱하면 안 된다. SHA-256은 빨라서 무차별 대입 공격에 취약하다. BCrypt는 의도적으로 느리게 설계됐다.

**CSRF 대응**: 쿠키 기반 인증(세션, httpOnly 쿠키에 저장한 토큰)을 쓰면 CSRF 토큰이 필수다. Authorization 헤더로 토큰을 보내는 방식에서는 CSRF를 신경 쓸 필요 없다. 브라우저가 헤더를 자동으로 붙이지 않기 때문이다.

**로그인 시도 제한**: 로그인 엔드포인트에 rate limit을 안 걸면 brute force 공격에 노출된다. IP 기준 분당 10회, 계정 기준 시간당 50회 정도가 일반적이다. 계정 기준 제한만 걸면 공격자가 여러 계정을 돌려가며 시도할 수 있으니, IP 기준 제한도 같이 걸어야 한다.

**로그아웃 처리**: Session 방식은 서버에서 세션을 무효화하면 끝이다. JWT는 서버에서 토큰을 무효화할 수 없으니, Refresh Token을 삭제하고 Access Token 만료를 기다리거나, 블랙리스트(Redis)를 운영해야 한다. 블랙리스트를 쓰면 매 요청마다 Redis를 조회해야 해서, JWT의 Stateless 장점이 줄어든다.

## 참고

- [OAuth 2.0 스펙](https://oauth.net/2/)
- [JWT.io](https://jwt.io/)
- [API 인증/인가 실무 패턴](../API/API_Security_Patterns.md) — JWT 설계, API Key 관리, HMAC 서명 상세
- [Spring Security](../../Framework/Java/Spring/Spring_Security.md) — Spring 구현 상세
- [OAuth 개요](../../Security/OAuth.md)
- [CORS](../../WebServer/Nginx/CORS.md)

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
