---
title: API 인증/인가 실무 패턴
tags: [api, security, jwt, oauth2, hmac]
---

# API 인증/인가 실무 패턴

## JWT 토큰 설계

### payload 크기 문제

JWT는 매 요청마다 헤더에 실려 간다. payload에 권한 목록, 사용자 프로필 전부 넣으면 토큰이 수 KB까지 커진다. 실제로 겪는 문제:

- **Nginx/ALB 기본 헤더 크기 제한**에 걸린다. Nginx는 `large_client_header_buffers` 기본값이 8KB다. 토큰이 커지면 431 Request Header Fields Too Large가 뜬다.
- **Redis 세션 저장 대비 이점이 사라진다.** payload가 크면 네트워크 비용이 세션 방식과 비슷해진다.

payload에는 `sub`(사용자 ID), `roles`(역할 배열), `exp`, `iat` 정도만 넣는다. 상세 권한은 서버에서 캐시로 조회한다.

```json
{
  "sub": "user-123",
  "roles": ["admin"],
  "exp": 1711468800,
  "iat": 1711465200
}
```

### 만료 처리

access token 만료 시간을 짧게 잡으면(15분 이하) 보안은 좋지만, 클라이언트에서 만료 처리를 제대로 안 하면 사용자가 수시로 로그아웃된다.

NestJS에서 passport-jwt로 토큰을 검증할 때 주의할 점:

```typescript
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';

interface JwtPayload {
  sub: string;
  roles: string[];
  exp: number;
  iat: number;
  ver?: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(private configService: ConfigService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: configService.get<string>('JWT_SECRET'),
      // clockTolerance: 서버 간 시간 차이 허용 (초 단위)
      clockTolerance: 30,
    });
  }

  async validate(payload: JwtPayload): Promise<JwtPayload> {
    return payload;
  }
}
```

`clockTolerance`를 안 넣으면 서버 간 시간이 1초만 어긋나도 토큰 검증이 실패한다. 멀티 인스턴스 환경에서 NTP 동기화가 완벽하지 않은 경우 반드시 넣어야 한다.

만료된 토큰에서 사용자 식별 정보를 꺼내야 하는 경우(refresh token 갱신):

```typescript
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class TokenService {
  constructor(private jwtService: JwtService) {}

  extractExpiredPayload(token: string): JwtPayload | null {
    try {
      // ignoreExpiration: true로 만료된 토큰도 파싱 가능
      return this.jwtService.verify(token, { ignoreExpiration: true }) as JwtPayload;
    } catch {
      return null;
    }
  }
}
```

### Refresh Token Rotation

refresh token은 한 번 사용하면 폐기하고 새 refresh token을 발급한다. 탈취된 refresh token이 재사용되면 즉시 감지할 수 있다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { RefreshTokenEntity } from './refresh-token.entity';

interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(RefreshTokenEntity)
    private refreshTokenRepository: Repository<RefreshTokenEntity>,
    private dataSource: DataSource,
  ) {}

  async refresh(refreshToken: string): Promise<TokenPair> {
    return this.dataSource.transaction(async (manager) => {
      const stored = await manager.findOne(RefreshTokenEntity, {
        where: { token: refreshToken },
      });

      if (!stored) {
        throw new Error('존재하지 않는 토큰');
      }

      // 이미 사용된 토큰이면 토큰 탈취로 판단
      if (stored.isUsed) {
        // 해당 사용자의 모든 refresh token 폐기
        await manager.update(
          RefreshTokenEntity,
          { userId: stored.userId },
          { isUsed: true },
        );
        throw new Error('토큰 재사용 감지');
      }

      // 현재 토큰을 사용 처리
      stored.isUsed = true;
      await manager.save(stored);

      // 새 토큰 쌍 발급
      const newAccessToken = this.generateAccessToken(stored.userId);
      const newRefreshToken = this.generateRefreshToken(stored.userId);

      const newEntity = manager.create(RefreshTokenEntity, {
        token: newRefreshToken,
        userId: stored.userId,
      });
      await manager.save(newEntity);

      return { accessToken: newAccessToken, refreshToken: newRefreshToken };
    });
  }

  private generateAccessToken(userId: string): string {
    // JwtService.sign() 호출
    return '';
  }

  private generateRefreshToken(userId: string): string {
    return '';
  }
}
```

주의할 점: rotation 구현 시 DB 트랜잭션을 걸어야 한다. 동시에 같은 refresh token으로 2개 요청이 들어오면, 하나는 성공하고 하나는 토큰 탈취로 감지되는 게 정상이다. 트랜잭션 없이 구현하면 둘 다 성공해서 refresh token이 2개 생긴다.

### 토큰 강제 무효화 (jti blacklist)

JWT는 stateless가 장점인데, 그게 단점도 된다. 만료 전에는 폐기 수단이 없다. 비밀번호 변경, 계정 정지, 이상 로그인 감지 같은 상황에서 발급된 토큰을 즉시 막아야 하는 일이 실무에서는 자주 생긴다.

표준 방식은 `jti`(JWT ID) 클레임을 넣고, 폐기된 jti를 Redis에 올려놓는 것이다. 모든 access token에 jti를 발급한다.

```typescript
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class TokenService {
  constructor(private jwtService: JwtService) {}

  generateAccessToken(userId: string): string {
    const jti = uuidv4();
    return this.jwtService.sign(
      { sub: userId, jti },
      { expiresIn: '15m' },
    );
  }
}
```

폐기 시 Redis에 jti를 저장한다. TTL은 토큰 남은 만료 시간으로 잡는다. 만료가 지나면 어차피 토큰이 무효라 blacklist에 둘 필요가 없다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class TokenBlacklistService {
  constructor(@InjectRedis() private redis: Redis) {}

  async revokeToken(jti: string, expiresInSeconds: number): Promise<void> {
    const key = `jwt:blacklist:${jti}`;
    await this.redis.set(key, '1', 'EX', expiresInSeconds);
  }

  async revokeAllUserTokens(userId: string): Promise<void> {
    // 사용자 전체 토큰 무효화는 jti 단위로는 어렵다
    // 사용자별 token version을 올리는 방식이 실무에서 많이 쓴다
    const key = `jwt:user_version:${userId}`;
    await this.redis.incr(key);
  }
}
```

검증 Guard에서는 jti를 매번 Redis에 조회한다. 모든 요청에서 1번 추가 조회가 발생하지만, Redis 단순 GET은 1ms 미만이라 실측상 큰 부담은 아니다.

```typescript
import { Injectable, CanActivate, ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import { JwtService } from '@nestjs/jwt';

interface JwtPayload {
  sub: string;
  jti: string;
  ver?: number;
}

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private jwtService: JwtService,
    @InjectRedis() private redis: Redis,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const token = this.extractToken(request);

    if (!token) throw new UnauthorizedException();

    let payload: JwtPayload;
    try {
      payload = this.jwtService.verify(token) as JwtPayload;
    } catch {
      throw new UnauthorizedException();
    }

    const { jti, sub: userId, ver: tokenVersion } = payload;

    // blacklist 조회
    const isBlacklisted = await this.redis.exists(`jwt:blacklist:${jti}`);
    if (isBlacklisted) {
      throw new UnauthorizedException('폐기된 토큰');
    }

    // 사용자 단위 무효화 (token version)
    const currentVersion = await this.redis.get(`jwt:user_version:${userId}`);
    if (
      currentVersion !== null &&
      tokenVersion !== undefined &&
      Number(currentVersion) > tokenVersion
    ) {
      throw new UnauthorizedException('사용자 토큰 버전 불일치');
    }

    request.user = payload;
    return true;
  }

  private extractToken(request: Request): string | null {
    const authHeader = (request as any).headers?.authorization as string;
    if (!authHeader?.startsWith('Bearer ')) return null;
    return authHeader.slice(7);
  }
}
```

사용자 단위 무효화는 토큰에 `ver` 클레임을 넣고, 폐기 시점에 Redis 카운터를 올리는 방식이 깔끔하다. jti 하나하나를 다 blacklist에 넣을 필요가 없다.

실무에서 자주 빠뜨리는 것:
- access token만 무효화하고 refresh token은 그대로 두는 경우. 비밀번호 변경 같은 시나리오에서는 refresh token도 같이 폐기해야 한다.
- Redis가 죽었을 때 blacklist 조회가 실패하면 어떻게 처리할지. fail-open(통과)이면 보안 구멍, fail-closed(거부)면 가용성 문제가 된다. 실무에서는 fail-closed + 회로 차단기로 짧게 끊고, blacklist 조회 실패율을 알람으로 걸어둔다.

---

## OAuth2 Authorization Code + PKCE

모바일 앱이나 SPA에서 OAuth2를 쓸 때 Authorization Code + PKCE를 써야 한다. client_secret을 클라이언트에 넣을 수 없기 때문이다.

### PKCE 흐름

```
1. 클라이언트가 code_verifier(랜덤 문자열)를 생성
2. code_verifier를 SHA256 해시 → code_challenge
3. 인가 요청 시 code_challenge 전달
4. 인가 코드를 받으면 토큰 요청 시 code_verifier 전달
5. 서버가 code_verifier를 해시해서 code_challenge와 비교
```

NestJS 환경에서 PKCE를 직접 구현해야 하는 경우:

```typescript
import * as crypto from 'crypto';

export class PkceUtil {
  static generateCodeVerifier(): string {
    const bytes = crypto.randomBytes(32);
    return bytes.toString('base64url');
  }

  static generateCodeChallenge(codeVerifier: string): string {
    const hash = crypto
      .createHash('sha256')
      .update(codeVerifier, 'utf8')
      .digest();
    return hash.toString('base64url');
  }
}
```

code_verifier는 반드시 `crypto.randomBytes()`를 써야 한다. `Math.random()`은 예측 가능성이 있다.

### Resource Server 검증 패턴

OAuth2에서 access token을 받은 Resource Server(API 서버)가 토큰을 검증하는 방식은 둘 중 하나다.

**JWT 자체 검증 (local validation)**: 토큰 안에 서명이 들어 있어서 서버에서 공개키로 검증만 하면 된다. Authorization Server에 요청을 보낼 필요가 없다. Auth Server의 JWKS 엔드포인트에서 공개키를 받아 캐시한다.

```typescript
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { passportJwtSecret } from 'jwks-rsa';

@Injectable()
export class JwksStrategy extends PassportStrategy(Strategy, 'jwks') {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKeyProvider: passportJwtSecret({
        cache: true,
        rateLimit: true,
        jwksRequestsPerMinute: 5,
        jwksUri: 'https://auth.example.com/.well-known/jwks.json',
      }),
    });
  }

  async validate(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    return payload;
  }
}
```

**Token Introspection (RFC 7662)**: 토큰을 받을 때마다 Authorization Server에 물어본다. opaque token(서명되지 않은 임의 문자열)을 쓸 때 사용한다.

```typescript
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';

interface IntrospectionResponse {
  active: boolean;
  scope?: string;
  client_id?: string;
  username?: string;
  exp?: number;
  sub?: string;
}

@Injectable()
export class OpaqueTokenIntrospector {
  constructor(private httpService: HttpService) {}

  async introspect(token: string): Promise<IntrospectionResponse> {
    const { data } = await firstValueFrom(
      this.httpService.post<IntrospectionResponse>(
        'https://auth.example.com/oauth2/introspect',
        new URLSearchParams({ token }),
        {
          auth: { username: 'client-id', password: 'client-secret' },
        },
      ),
    );
    return data;
  }
}
```

introspection 응답은 RFC 7662 표준 형식을 따른다.

```json
{
  "active": true,
  "scope": "read write",
  "client_id": "abc123",
  "username": "user@example.com",
  "exp": 1711468800,
  "sub": "user-123"
}
```

`active: false`면 토큰이 만료됐거나 폐기된 것이다. 다른 필드는 표시되지 않을 수도 있다.

둘 중 무엇을 쓸지 판단 기준:

| 기준 | JWT (local) | Introspection (remote) |
|------|------------|------------------------|
| 검증 속도 | 빠름 (공개키 검증만) | 느림 (HTTP 호출) |
| 즉시 폐기 | 어려움 (jti blacklist 필요) | 쉬움 (Auth Server에서 무효화하면 끝) |
| 네트워크 의존 | JWKS 캐시 갱신 시점만 | 모든 요청 |
| 토큰 크기 | 큼 (KB 단위) | 작음 (랜덤 문자열) |

실무에서 자주 보는 절충안: access token은 JWT(빠른 검증) + jti blacklist(즉시 폐기), refresh token은 opaque(introspection으로만 검증). 양쪽 장점만 챙기는 패턴이다.

introspection을 쓸 때는 캐시가 필수다. 매 API 요청마다 Auth Server를 때리면 Auth Server가 병목이 된다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';
import * as crypto from 'crypto';

interface IntrospectionResponse {
  active: boolean;
  sub?: string;
  scope?: string;
}

@Injectable()
export class CachingOpaqueTokenIntrospector {
  private readonly ttlSeconds = 60; // 토큰 유효 기간보다 짧게

  constructor(
    private delegate: OpaqueTokenIntrospector,
    @InjectRedis() private redis: Redis,
  ) {}

  async introspect(token: string): Promise<IntrospectionResponse> {
    // 토큰 자체를 캐시 키로 쓰면 토큰이 로그에 남을 수 있다
    // SHA-256 해시를 키로 쓰는 게 안전하다
    const cacheKey = `introspection:${crypto
      .createHash('sha256')
      .update(token)
      .digest('hex')}`;

    const cached = await this.redis.get(cacheKey);
    if (cached) {
      return JSON.parse(cached) as IntrospectionResponse;
    }

    const result = await this.delegate.introspect(token);
    await this.redis.set(cacheKey, JSON.stringify(result), 'EX', this.ttlSeconds);
    return result;
  }
}
```

캐시 TTL은 60초 이하로 짧게 잡아야 한다. 길게 잡으면 토큰을 폐기해도 캐시가 살아 있는 동안 통과한다. 즉시 폐기가 중요하면 캐시를 안 쓰거나, Auth Server에서 폐기 이벤트를 받아 캐시를 무효화하는 구조를 만든다.

---

## API Key 관리

### 발급

API Key는 충분히 길어야 한다. 최소 32바이트(256비트). 저장할 때는 해시값만 저장하고, 원본은 발급 시점에만 보여준다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import * as crypto from 'crypto';
import { ApiKeyEntity } from './api-key.entity';

interface ApiKeyResponse {
  rawKey: string;
  prefix: string;
  id: number;
}

@Injectable()
export class ApiKeyService {
  constructor(
    @InjectRepository(ApiKeyEntity)
    private apiKeyRepository: Repository<ApiKeyEntity>,
    private dataSource: DataSource,
  ) {}

  async issueApiKey(clientId: number, description: string): Promise<ApiKeyResponse> {
    return this.dataSource.transaction(async (manager) => {
      // 원본 키 생성
      const keyBytes = crypto.randomBytes(32);
      const rawKey = `sk_live_${keyBytes.toString('base64url')}`;

      // prefix만 저장 (목록 조회용)
      const prefix = rawKey.substring(0, 12);

      // SHA-256 해시만 DB에 저장
      const hashedKey = crypto.createHash('sha256').update(rawKey).digest('hex');

      const entity = manager.create(ApiKeyEntity, {
        clientId,
        keyHash: hashedKey,
        keyPrefix: prefix,
        description,
        createdAt: new Date(),
      });
      const saved = await manager.save(entity);

      // 원본은 이 응답에서만 보여줌
      return { rawKey, prefix, id: saved.id };
    });
  }
}
```

prefix(`sk_live_`)를 붙이는 이유: 로그나 코드에서 실수로 노출됐을 때 어떤 종류의 키인지 바로 알 수 있고, secret scanning 도구가 탐지할 수 있다. Stripe, OpenAI 등 대부분의 서비스가 이 패턴을 쓴다.

### 폐기

즉시 폐기가 가능해야 한다. API Key 검증 시 캐시를 쓰고 있다면, 폐기 시점에 캐시도 같이 날려야 한다.

```typescript
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { Cache } from 'cache-manager';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Inject } from '@nestjs/common';
import { ApiKeyEntity } from './api-key.entity';

@Injectable()
export class ApiKeyService {
  constructor(
    @InjectRepository(ApiKeyEntity)
    private apiKeyRepository: Repository<ApiKeyEntity>,
    private dataSource: DataSource,
    @Inject(CACHE_MANAGER) private cacheManager: Cache,
  ) {}

  async revokeApiKey(keyId: number, clientId: number): Promise<void> {
    return this.dataSource.transaction(async (manager) => {
      const key = await manager.findOne(ApiKeyEntity, {
        where: { id: keyId, clientId },
      });

      if (!key) throw new NotFoundException('API Key not found');

      key.revokedAt = new Date();
      await manager.save(key);

      // 캐시 즉시 무효화
      await this.cacheManager.del(key.keyHash);
    });
  }
}
```

폐기된 키로 요청이 들어오면 401이 아니라 403을 반환하는 게 맞다. 401은 "인증 안 됨", 403은 "인증은 됐지만 권한 없음(폐기됨)"이다. 클라이언트가 키를 재발급해야 하는지, 다른 키를 써야 하는지 구분할 수 있다.

### Rate Limit 연동

API Key별로 rate limit을 걸어야 한다. Redis의 sliding window 방식이 실무에서 가장 많이 쓰인다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

interface RateLimitPlan {
  windowMillis: number;
  maxRequests: number;
}

@Injectable()
export class ApiKeyRateLimiter {
  constructor(@InjectRedis() private redis: Redis) {}

  async isAllowed(keyHash: string, plan: RateLimitPlan): Promise<boolean> {
    const redisKey = `rate:${keyHash}`;
    const now = Date.now();
    const windowStart = now - plan.windowMillis;

    // Lua 스크립트로 원자적 처리
    const luaScript = `
      redis.call('ZREMRANGEBYSCORE', KEYS[1], '0', ARGV[1])
      local count = redis.call('ZCARD', KEYS[1])
      if count < tonumber(ARGV[2]) then
        redis.call('ZADD', KEYS[1], ARGV[3], ARGV[3])
        redis.call('EXPIRE', KEYS[1], ARGV[4])
        return 1
      end
      return 0
    `;

    const result = await this.redis.eval(
      luaScript,
      1,
      redisKey,
      String(windowStart),
      String(plan.maxRequests),
      String(now),
      String(Math.ceil(plan.windowMillis / 1000) + 1),
    );

    return result === 1;
  }
}
```

Lua 스크립트를 쓰는 이유: ZREMRANGEBYSCORE → ZCARD → ZADD를 별도 명령으로 보내면 그 사이에 다른 요청이 끼어들 수 있다. Lua 스크립트는 Redis에서 원자적으로 실행된다.

rate limit 응답 헤더도 내려줘야 한다:

```typescript
import { Response } from 'express';

function setRateLimitHeaders(
  res: Response,
  maxRequests: number,
  remaining: number,
  resetTimestamp: number,
): void {
  res.setHeader('X-RateLimit-Limit', String(maxRequests));
  res.setHeader('X-RateLimit-Remaining', String(remaining));
  res.setHeader('X-RateLimit-Reset', String(resetTimestamp));
}
```

### 키 회전 (rotation)

API Key는 정기적으로 회전시켜야 한다. 회전 자체보다 회전 중 다운타임 없이 교체하는 게 어렵다. 클라이언트가 새 키로 한 번에 갈아탈 수 없는 환경(여러 서버, 배포 시차, 외부 파트너)에서는 새 키와 옛 키가 동시에 유효한 grace period가 필요하다.

스키마 설계는 한 클라이언트에 여러 키가 동시 존재할 수 있게 만든다. `is_primary` 같은 플래그는 두지 않는다. 모든 활성 키가 검증을 통과하게 두는 게 운영이 단순하다.

```sql
CREATE TABLE api_keys (
    id BIGINT PRIMARY KEY,
    client_id BIGINT NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    key_prefix VARCHAR(16) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    INDEX idx_key_hash (key_hash),
    INDEX idx_client_active (client_id, revoked_at, expires_at)
);
```

회전 흐름은 보통 이렇게 간다.

1. 새 키 발급. 옛 키는 그대로 둔다. 두 키 모두 유효.
2. 클라이언트가 새 키로 교체. `last_used_at`을 보면서 옛 키가 여전히 쓰이는지 모니터링.
3. 옛 키 사용이 멈추거나 grace period(보통 7~30일)가 지나면 옛 키 폐기.

```typescript
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { ApiKeyEntity } from './api-key.entity';

@Injectable()
export class ApiKeyService {
  constructor(
    @InjectRepository(ApiKeyEntity)
    private apiKeyRepository: Repository<ApiKeyEntity>,
    private dataSource: DataSource,
  ) {}

  async rotateApiKey(
    oldKeyId: number,
    clientId: number,
    gracePeriodMs: number,
  ): Promise<ApiKeyResponse> {
    return this.dataSource.transaction(async (manager) => {
      const oldKey = await manager.findOne(ApiKeyEntity, {
        where: { id: oldKeyId, clientId },
      });

      if (!oldKey) throw new NotFoundException('API Key not found');

      if (oldKey.revokedAt !== null) {
        throw new Error('이미 폐기된 키');
      }

      // 옛 키에 만료 시각 설정. 즉시 폐기는 아님
      oldKey.expiresAt = new Date(Date.now() + gracePeriodMs);
      await manager.save(oldKey);

      // 새 키 발급
      const newKey = await this.issueApiKey(clientId, oldKey.description);

      // 클라이언트에 회전 알림 (이메일, 웹훅)
      // rotationNotifier.notify(...)

      return newKey;
    });
  }

  private async issueApiKey(clientId: number, description: string): Promise<ApiKeyResponse> {
    // 위 issueApiKey 구현 참조
    return {} as ApiKeyResponse;
  }
}
```

`last_used_at`을 매 요청마다 DB에 업데이트하면 부하가 크다. Redis에 1분 단위로 모았다가 백그라운드 잡에서 DB로 flush하는 식으로 처리한다.

회전 시점 판단: AWS, GCP 같은 클라우드 IAM은 90일 권장이지만, B2B API에서는 6개월~1년이 현실적이다. 짧을수록 좋지만 클라이언트 운영 부담을 같이 봐야 한다. 사고 발생 시(키 유출 의심)는 즉시 강제 회전. 정기 회전은 캘린더에 박아두고 한다.

옛 키 만료가 임박했을 때 클라이언트가 아직 새 키로 교체 못 했으면 차단보다 알림이 먼저다. 이메일 + 응답 헤더로 경고한다.

```typescript
import { Response } from 'express';
import { ApiKeyEntity } from './api-key.entity';

function setKeyDeprecationHeaders(res: Response, key: ApiKeyEntity): void {
  if (key.expiresAt && key.expiresAt.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000) {
    res.setHeader(
      'X-ApiKey-Deprecation',
      `key ${key.keyPrefix} expires at ${key.expiresAt.toISOString()}`,
    );
    res.setHeader('Sunset', key.expiresAt.toUTCString());
  }
}
```

`Sunset` 헤더는 RFC 8594 표준이다. 클라이언트 SDK가 이 헤더를 보고 자동으로 경고 로그를 찍게 만들 수 있다.

### IP allowlist의 한계

API Key + IP allowlist 조합은 자주 쓰이지만, IP만 믿으면 안 된다. 실무에서 부딪히는 한계가 명확하다.

**클라우드 IP는 동적이다.** AWS Lambda, ECS Fargate, Cloud Run 같은 환경은 outbound IP가 풀에서 동적으로 할당된다. NAT Gateway를 고정해서 EIP를 쓰지 않으면 IP가 매번 바뀐다. 클라이언트에게 "이 IP로 요청하세요"라고 알려줘도 인프라 변경 한 번이면 무용지물이 된다.

**IP 풀을 받으면 의미가 약해진다.** AWS는 region별 IP 대역을 공개한다(`ip-ranges.json`). 어떤 클라이언트가 "AWS us-east-1 전체"를 allowlist에 올려달라고 하면, 그 안에서 누구든 요청을 보낼 수 있다는 뜻이다. allowlist 자체의 의미가 거의 사라진다.

**프록시 환경에서 IP 추출이 까다롭다.** ALB, CloudFront, Nginx 뒤에 있는 서버에서 클라이언트 IP를 받으려면 `X-Forwarded-For`를 파싱해야 하는데, 이 헤더는 클라이언트가 임의로 보낼 수 있다. 신뢰 가능한 프록시만 거치는지 확인 안 하고 `X-Forwarded-For`의 첫 IP를 그대로 쓰면 우회된다.

```typescript
import { Request } from 'express';

function getClientIp(request: Request): string {
  // 신뢰할 수 있는 프록시 IP 목록
  const trustedProxies = new Set(['10.0.0.0/8', '172.16.0.0/12']);

  const xForwardedFor = request.headers['x-forwarded-for'] as string | undefined;
  if (!xForwardedFor) {
    return request.socket.remoteAddress ?? '';
  }

  // X-Forwarded-For는 "client, proxy1, proxy2" 형태
  // 오른쪽부터 신뢰 가능한 프록시를 벗기고, 첫 untrusted IP가 실제 클라이언트
  const ips = xForwardedFor.split(',').map((ip) => ip.trim());
  for (let i = ips.length - 1; i >= 0; i--) {
    if (!isTrustedProxy(ips[i], trustedProxies)) {
      return ips[i];
    }
  }
  return request.socket.remoteAddress ?? '';
}

function isTrustedProxy(ip: string, trustedProxies: Set<string>): boolean {
  // CIDR 매칭 라이브러리(ip-range-check 등) 사용 권장
  return false;
}
```

이 작업은 직접 구현하기보다 NestJS의 `trust proxy` 설정이나 `express-ip` 미들웨어를 활용하는 게 안전하다. 직접 짜면 십중팔구 한두 곳에서 틀린다.

**IPv6 매칭 실수.** allowlist를 IPv4만 검사하다가 IPv6로 들어오는 요청을 놓치는 경우가 있다. CIDR 매칭 라이브러리를 쓰는 게 안전하다.

결론: IP allowlist는 보조 통제다. 단독으로 쓰지 말고 API Key 또는 mTLS 같은 강한 인증과 같이 써야 의미가 있다. "IP만 맞으면 통과"는 사실상 인증이 없는 상태다.

---

## CORS 설정에서 자주 틀리는 부분

### 와일드카드와 credentials

`Access-Control-Allow-Origin: *`와 `Access-Control-Allow-Credentials: true`는 동시에 쓸 수 없다. 브라우저가 거부한다.

NestJS에서 CORS를 설정할 때:

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);

  app.enableCors({
    // 이렇게 하면 credentials 요청이 안 된다
    // origin: '*',
    // credentials: true,

    // 명시적으로 origin을 지정해야 한다
    origin: ['https://app.example.com', 'https://admin.example.com'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Authorization', 'Content-Type'],
    maxAge: 3600,
  });

  await app.listen(3000);
}
bootstrap();
```

### preflight 캐시

브라우저는 `Content-Type: application/json` 같은 비표준 헤더가 있으면 매번 OPTIONS preflight 요청을 보낸다. `maxAge`를 안 주면 매 API 호출마다 OPTIONS + 실제 요청, 총 2번 요청이 간다. `maxAge: 3600`을 주면 1시간 동안 preflight 결과를 캐시한다.

### allowedHeaders 누락

클라이언트가 응답에서 커스텀 헤더를 읽어야 하는 경우:

```typescript
app.enableCors({
  origin: 'https://app.example.com',
  exposedHeaders: ['X-Request-Id', 'X-RateLimit-Remaining'],
});
```

`exposedHeaders`를 안 넣으면 브라우저 JavaScript에서 해당 헤더 값을 읽을 수 없다. 네트워크 탭에서는 보이는데 코드에서 접근이 안 되면 이 설정을 확인해야 한다.

---

## 요청 서명(HMAC) 검증

웹훅 수신이나 서버 간 통신에서 요청이 변조되지 않았는지 검증할 때 HMAC을 쓴다. Stripe, GitHub Webhook 등이 이 방식을 사용한다.

### 서명 생성

```typescript
import * as crypto from 'crypto';

export class HmacUtil {
  static sign(secret: string, payload: string): string {
    return crypto
      .createHmac('sha256', secret)
      .update(payload, 'utf8')
      .digest('hex');
  }
}
```

### 서명 검증 NestJS Interceptor

```typescript
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  UnauthorizedException,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import * as crypto from 'crypto';
import { Request, Response } from 'express';

@Injectable()
export class HmacVerificationInterceptor implements NestInterceptor {
  private readonly webhookSecret: string;

  constructor(webhookSecret: string) {
    this.webhookSecret = webhookSecret;
  }

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const request = context.switchToHttp().getRequest<Request & { rawBody?: Buffer }>();

    // 서명 헤더 확인
    const signature = request.headers['x-signature-256'] as string | undefined;
    const timestamp = request.headers['x-timestamp'] as string | undefined;

    if (!signature || !timestamp) {
      throw new UnauthorizedException('서명 헤더 누락');
    }

    // 타임스탬프 검증 (replay attack 방지)
    const requestTime = Number(timestamp);
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - requestTime) > 300) {
      // 5분 허용
      throw new UnauthorizedException('요청 시간 초과');
    }

    // body는 raw body middleware로 미리 파싱된 값을 사용
    const body = request.rawBody?.toString('utf8') ?? '';

    // 서명 검증
    const signPayload = `${timestamp}.${body}`;
    const expected = HmacUtil.sign(this.webhookSecret, signPayload);

    // timing-safe 비교
    const expectedBuf = Buffer.from(`sha256=${expected}`, 'utf8');
    const signatureBuf = Buffer.from(signature, 'utf8');

    if (
      expectedBuf.length !== signatureBuf.length ||
      !crypto.timingSafeEqual(expectedBuf, signatureBuf)
    ) {
      throw new UnauthorizedException('서명 불일치');
    }

    return next.handle();
  }
}
```

중요한 부분 3가지:

**1. timing-safe 비교를 써야 한다.** `===` 연산자는 첫 번째 다른 문자에서 바로 false를 리턴한다. 공격자가 응답 시간을 측정해서 서명을 한 글자씩 맞출 수 있다(timing attack). `crypto.timingSafeEqual()`은 항상 전체 바이트를 비교한다.

**2. timestamp를 서명에 포함해야 한다.** timestamp 없이 body만 서명하면, 과거에 유효했던 요청을 그대로 다시 보내는 replay attack이 가능하다. timestamp를 서명 payload에 넣고, 서버에서 현재 시간과 비교해서 5분 이내 요청만 허용한다.

**3. request body 캐싱이 필요하다.** NestJS에서는 `rawBody` 옵션을 활성화하거나 별도 미들웨어로 raw body를 보존해야 한다.

```typescript
// main.ts에서 raw body 활성화
const app = await NestFactory.create(AppModule, { rawBody: true });
```

### nonce 기반 replay 방어

timestamp 5분 윈도우만 두면 그 5분 안에는 같은 요청을 그대로 재전송할 수 있다. 결제처럼 멱등성이 깨지면 안 되는 API에서는 timestamp 검증만으로 부족하다. nonce를 같이 검증한다.

nonce는 요청마다 유일한 값이다. UUID를 쓰는 게 일반적이다. 서버에서 받은 nonce는 Redis에 timestamp 윈도우와 같은 TTL로 저장한다. 같은 nonce가 다시 오면 replay로 본다.

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class NonceVerifier {
  private readonly NONCE_TTL_SECONDS = 300; // 5분

  constructor(@InjectRedis() private redis: Redis) {}

  async verifyAndStore(clientId: string, nonce: string): Promise<boolean> {
    const key = `nonce:${clientId}:${nonce}`;

    // SET NX: 키가 없을 때만 set, 있으면 null 반환
    const inserted = await this.redis.set(key, '1', 'EX', this.NONCE_TTL_SECONDS, 'NX');

    return inserted === 'OK';
  }
}
```

Interceptor에 nonce 검증을 추가한다.

```typescript
const nonce = request.headers['x-nonce'] as string | undefined;
if (!nonce || nonce.length < 16) {
  throw new UnauthorizedException('nonce 누락 또는 길이 부족');
}

const clientId = request.headers['x-client-id'] as string;
const isValid = await this.nonceVerifier.verifyAndStore(clientId, nonce);
if (!isValid) {
  throw new UnauthorizedException('nonce 재사용 감지');
}

// nonce도 서명 payload에 포함시킨다
const signPayload = `${timestamp}.${nonce}.${body}`;
```

nonce도 서명 payload에 포함해야 한다. 안 그러면 공격자가 nonce만 바꿔서 서명을 다시 보내면 검증이 통과해버린다(서명은 timestamp + body로만 만든 거라).

nonce 저장 비용이 부담스러우면 client별로 prefix를 나눠서 저장한다. 여러 client의 nonce가 우연히 충돌해도 영향이 없다. TTL을 짧게(timestamp 윈도우와 동일) 잡으면 메모리 사용량은 분당 요청 수 × TTL 정도로 예측 가능하다.

### AWS SigV4 스타일 헤더 설계

웹훅 단방향 검증을 넘어 양방향 API 호출(B2B, 내부 서비스 간)에서 서명을 도입할 때 AWS Signature Version 4의 헤더 구조를 따라가는 게 합리적이다. 자체 발명하면 빠뜨리는 게 생긴다.

핵심 헤더 4개와 의미:

```
Authorization: HMAC-SHA256
  Credential=ak_abc123/20260506/api/v1,
  SignedHeaders=host;x-timestamp;x-nonce;content-type,
  Signature=a3c2...

X-Timestamp: 1715000000
X-Nonce: 3f8c-a2e1-...
Content-SHA256: 9b1a...
```

`Credential`은 키 ID + 날짜 + 스코프. 날짜를 분리한 이유는 derived key를 만들 때 쓰기 위해서다. AWS는 `kSecret → kDate → kRegion → kService → kSigning`으로 단계적 HMAC을 만든다. 이렇게 하면 root secret을 직접 서명에 쓰지 않고, 일자별 파생 키를 캐시할 수 있다.

`SignedHeaders`는 서명에 포함된 헤더 목록을 명시한다. 이게 없으면 서버가 어떤 헤더를 검증해야 할지 모른다. 클라이언트가 보낸 헤더 목록을 그대로 표기한다.

`Content-SHA256`은 body 해시를 별도 헤더로 분리. body가 비어 있을 때(`GET`)도 빈 문자열의 SHA-256을 넣어 일관되게 만든다.

서명 대상 문자열(canonical request) 구성:

```
HMAC-SHA256
20260506T120000Z
20260506/api/v1
SHA256(canonical_request)
```

`canonical_request`:

```
POST
/v1/payments
api_key=abc&limit=10
content-type:application/json
host:api.example.com
x-nonce:3f8c-a2e1-...
x-timestamp:1715000000

content-type;host;x-nonce;x-timestamp
9b1a5e...  (body SHA-256)
```

자체 구현 시 빠지기 쉬운 부분:

```typescript
import * as crypto from 'crypto';
import { Request } from 'express';

export class CanonicalRequestBuilder {
  build(request: Request, body: string, signedHeaders: string[]): string {
    const lines: string[] = [];

    lines.push(request.method);

    // path는 정규화
    lines.push(new URL(request.url, 'http://host').pathname);

    // query string은 키 알파벳 순으로 정렬, 같은 키는 값으로 또 정렬
    lines.push(this.canonicalQueryString(request.query as Record<string, string>));

    // header는 소문자 + trim, 알파벳 순 정렬
    for (const header of signedHeaders) {
      const value = (request.headers[header] as string ?? '').trim().replace(/\s+/g, ' ');
      lines.push(`${header.toLowerCase()}:${value}`);
    }
    lines.push('');
    lines.push(signedHeaders.join(';'));
    lines.push(crypto.createHash('sha256').update(body, 'utf8').digest('hex'));

    return lines.join('\n');
  }

  private canonicalQueryString(query: Record<string, string>): string {
    return Object.entries(query)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
  }
}
```

빠뜨리면 검증이 어긋나는 포인트:

- 헤더 값의 trim과 연속 공백 정규화. 클라이언트가 보낸 `Content-Type: application/json `(끝 공백)과 서버에서 받은 값이 다르면 서명이 깨진다.
- query string의 정렬. `?b=2&a=1`과 `?a=1&b=2`는 의미가 같지만 서명은 다르다. 클라이언트와 서버 둘 다 알파벳 순으로 정렬해야 한다.
- 헤더 이름 대소문자. HTTP 헤더는 대소문자 구분이 없지만 서명 입력은 일관돼야 한다. 둘 다 소문자로 변환한다.
- path 정규화. `/v1/payments/`와 `/v1/payments`는 라우팅이 같아도 서명은 다르다. 클라이언트가 보낸 그대로 정규화한다.

derived key 방식:

```typescript
import * as crypto from 'crypto';

function deriveSigningKey(secret: string, date: string, scope: string): Buffer {
  const kDate = crypto.createHmac('sha256', `AWS4${secret}`).update(date).digest();
  const kScope = crypto.createHmac('sha256', kDate).update(scope).digest();
  return crypto.createHmac('sha256', kScope).update('aws4_request').digest();
}
```

매 요청에서 root secret을 그대로 쓰지 않는다. 일자 + scope로 파생한 키만 서명에 사용한다. root secret이 노출되더라도 지난 키들이 자동으로 무효화되지는 않지만, 메모리에 root secret이 머무는 시간이 짧아진다. 일자별 캐시도 가능하다.

자체 프로토콜이 필요한 게 아니라면, 차라리 mTLS나 OAuth2 client_credentials를 쓰는 게 운영 부담이 적다. SigV4 스타일은 정말 클라이언트 라이브러리 없이 외부 파트너가 직접 호출해야 하고, 모든 요청에 무결성 + 인증이 필요한 상황에서만 쓴다.
