---
title: Refresh Token Rotation
tags:
  - Authentication
  - JWT
  - Refresh Token
  - RTR
  - Security
  - Redis
updated: 2026-08-01
---

# Refresh Token Rotation

Refresh Token을 쓸 때마다 새 토큰을 발급하고 이전 토큰을 폐기하는 패턴이다. 단순 만료 방식과 달리 토큰 재사용 여부를 추적하기 때문에, 탈취된 토큰이 사용되는 순간 감지할 수 있다.

## 단순 만료 방식과의 차이

단순 만료 방식은 DB에 `(user_id, token, expires_at)`을 저장하고, 요청 시 만료 여부만 확인한다. 토큰이 탈취됐을 때가 문제다. 공격자가 Refresh Token을 훔쳐가면, 원래 사용자는 만료될 때까지 아무것도 알 수 없다.

```
단순 만료 방식:
클라이언트 → /refresh (token=abc) → Access Token 발급
공격자     → /refresh (token=abc) → Access Token 발급 (감지 불가)
```

RTR(Refresh Token Rotation)은 Refresh Token을 1회용으로 만든다. 사용할 때마다 새 토큰으로 교체하고, 이전 토큰은 즉시 폐기된다. 정상 사용자가 `token_v1`으로 갱신하면 `token_v2`를 받는다. 공격자가 폐기된 `token_v1`을 나중에 사용하면, 서버는 재사용을 감지하고 해당 사용자의 모든 토큰을 무효화한다.

```mermaid
sequenceDiagram
    participant C as 정상 클라이언트
    participant S as 서버
    participant DB as DB/Redis

    C->>S: POST /auth/refresh (token_v1)
    S->>DB: findByHash(hash(token_v1))
    DB-->>S: isUsed=false, familyId=F1
    S->>DB: markUsed(token_v1)
    S->>DB: insert(token_v2, familyId=F1)
    S-->>C: accessToken + refreshToken=token_v2

    Note over C,S: 이후 공격자가 token_v1 재사용 시도
    C->>S: POST /auth/refresh (token_v1)
    S->>DB: findByHash(hash(token_v1))
    DB-->>S: isUsed=true
    S->>DB: revokeFamily(familyId=F1)
    S-->>C: 401 REUSE_DETECTED
```

재사용 감지 시 폐기 범위는 `familyId` 기준이다. 같은 로그인 세션에서 발급된 토큰들이 하나의 family를 이룬다. 공격자가 `token_v1`을 먼저 써서 `token_v2`를 받아갔다면, 정상 사용자가 뒤늦게 `token_v1`을 쓸 때 서버는 `token_v2`까지 폐기한다.

어느 쪽이 먼저 사용하든 탈취를 감지한다. 단, 감지 전까지 공격자가 활동한 짧은 시간의 피해는 막지 못한다.

## 탈취 시나리오별 대응

### Access Token 탈취

Access Token이 탈취돼도 RTR이 직접 막아주지는 않는다. 탈취된 Access Token은 만료 시간까지 그대로 쓸 수 있다. 방어 방법은 만료 시간을 15분 이하로 짧게 가져가는 것이다.

공격자가 Access Token을 훔쳤지만 Refresh Token은 못 훔쳤다면, 15분 뒤 접근이 끊긴다. 이 시나리오에서 피해는 제한된다.

`localStorage`에 Access Token을 저장하면 XSS 한 번에 바로 탈취된다. 메모리 변수에 저장하고, Refresh Token은 `httpOnly` 쿠키로 관리하는 것이 기본 구조다.

```javascript
// 프론트엔드 패턴
let accessToken = null; // 메모리 저장

async function getAccessToken() {
  if (!accessToken || isExpired(accessToken)) {
    // 쿠키의 Refresh Token으로 갱신 요청
    const res = await fetch('/auth/refresh', { method: 'POST', credentials: 'include' });
    const data = await res.json();
    accessToken = data.accessToken;
  }
  return accessToken;
}
```

페이지 새로고침 시 메모리가 초기화되므로, 갱신 요청을 자동으로 보내는 로직이 필요하다.

### Refresh Token 탈취

더 심각하다. Refresh Token은 수명이 길고(7일~30일), 탈취되면 지속적으로 Access Token을 발급할 수 있다.

단순 만료 방식에서는 사용자가 직접 "다른 기기에서 로그아웃"을 실행하거나 비밀번호를 변경해야만 대응이 가능하다. 탈취 사실을 사용자가 스스로 인지해야 한다는 전제다.

RTR에서는 정상 사용자가 다음 갱신 요청을 보낼 때 자동으로 감지된다. 사용자가 아무것도 몰랐어도, 오래된 토큰으로 갱신을 시도하는 시점에 재사용이 감지된다.

다만, 감지 즉시 `familyId` 전체를 폐기하므로 사용자도 강제 로그아웃된다. 사용자 입장에서는 갑자기 로그인이 풀리는 경험을 하게 된다. 이 상황에서 "보안상 재로그인이 필요합니다" 안내와 함께, 필요하다면 이메일/앱 푸시 알림으로 보안 이벤트를 알려주는 것이 좋다.

## 저장 구조

### PostgreSQL 스키마

```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id   UUID NOT NULL,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  CHAR(64) NOT NULL,      -- SHA-256 hex
    parent_id   UUID REFERENCES refresh_tokens(id),
    is_used     BOOLEAN NOT NULL DEFAULT FALSE,
    used_at     TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    revoke_reason VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_rt_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_rt_family_id ON refresh_tokens(family_id);
CREATE INDEX idx_rt_user_id ON refresh_tokens(user_id);
```

`token_hash`에 원문 대신 SHA-256 해시를 저장한다. DB가 유출되더라도 해시로는 실제 토큰을 복원할 수 없다. 클라이언트에게는 원문을 주고, 서버는 해시로만 조회한다.

`family_id`는 같은 로그인 세션에서 발급된 토큰들을 묶는다. 재사용 감지 시 이 단위로 일괄 폐기한다.

`revoke_reason`은 선택 사항이지만, 나중에 사고 추적 시 "왜 폐기됐는지" 기록이 있으면 유용하다.

### Redis 전용 구조

DB 없이 Redis만 쓸 수도 있다. 조회는 빠르지만 영구 기록이 없고, TTL이 지나면 데이터가 사라진다.

```
# 토큰별 메타데이터
key: rt:{tokenHash}
value: JSON {
  "familyId": "uuid",
  "userId": "123",
  "parentHash": "sha256...",
  "isUsed": false,
  "createdAt": 1722470400,
  "expiresAt": 1723075200
}
TTL: 7일

# family 구성원 목록 (재사용 감지 시 일괄 삭제용)
key: rt:family:{familyId}
members: Set["hash1", "hash2", "hash3"]
TTL: 30일
```

`rt:family:{familyId}`를 Redis Set으로 관리하면, 폐기 시 `SMEMBERS`로 목록을 가져와 `DEL` 일괄 처리가 가능하다.

### DB + Redis 혼합

실무에서 가장 많이 쓰는 구조다. 영구 기록은 DB에, 빠른 조회는 Redis 캐시로 처리한다.

```
요청 → Redis에서 tokenHash 조회
     → 캐시 히트: is_used 즉시 확인
     → 캐시 미스: DB 조회 후 5분 캐싱
```

Redis 장애 시 DB로 폴백한다. Redis와 DB 상태가 다를 때 DB를 원본으로 신뢰한다. 토큰 폐기 시 Redis 캐시도 즉시 삭제해야 한다.

## 재사용 감지 구현

### 기본 로직

```javascript
// token.service.js
const crypto = require('crypto');

async function rotateRefreshToken(rawToken) {
  const tokenHash = sha256(rawToken);

  const tokenRecord = await db.refreshTokens.findOne({ tokenHash });

  if (!tokenRecord) {
    throw new AuthError('INVALID_TOKEN');
  }

  if (tokenRecord.expiresAt < new Date()) {
    throw new AuthError('TOKEN_EXPIRED');
  }

  if (tokenRecord.isUsed) {
    // 재사용 감지: family 전체 폐기
    await db.refreshTokens.updateMany(
      { familyId: tokenRecord.familyId },
      {
        isUsed: true,
        revokedAt: new Date(),
        revokeReason: 'REUSE_DETECTED',
      }
    );
    throw new AuthError('REUSE_DETECTED');
  }

  // 현재 토큰 사용 처리
  await db.refreshTokens.updateOne(
    { id: tokenRecord.id },
    { isUsed: true, usedAt: new Date() }
  );

  // 새 토큰 발급
  const newRaw = crypto.randomBytes(40).toString('hex');
  await db.refreshTokens.insertOne({
    id: crypto.randomUUID(),
    familyId: tokenRecord.familyId,
    userId: tokenRecord.userId,
    tokenHash: sha256(newRaw),
    parentId: tokenRecord.id,
    isUsed: false,
    createdAt: new Date(),
    expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
  });

  const accessToken = issueAccessToken(tokenRecord.userId);
  return { accessToken, refreshToken: newRaw };
}

function sha256(raw) {
  return crypto.createHash('sha256').update(raw).digest('hex');
}
```

### Race Condition 처리

클라이언트가 동시에 두 번 갱신 요청을 보내면 오탐이 발생한다. 모바일 앱에서 네트워크 타임아웃 후 자동 재시도할 때 자주 생기는 상황이다. 두 번째 요청이 이미 폐기된 토큰으로 들어오면 탈취로 잘못 판단한다.

grace period로 처리한다. 토큰이 사용된 지 N초 이내의 재요청은 동시 요청으로 간주하고, 가장 최근에 발급된 유효 토큰을 반환한다.

```javascript
if (tokenRecord.isUsed) {
  const GRACE_MS = 10_000; // 10초
  const usedAgo = Date.now() - new Date(tokenRecord.usedAt).getTime();

  if (usedAgo < GRACE_MS) {
    // 동시 요청으로 판단 — 최신 유효 토큰 조회
    const latestValid = await db.refreshTokens.findOne({
      familyId: tokenRecord.familyId,
      isUsed: false,
    });

    if (latestValid) {
      // latestValid의 rawToken은 DB에 없으므로, 이 패턴은
      // 클라이언트가 직전 응답의 토큰을 다시 보내도록 유도하거나
      // Redis 분산 락 방식으로 대체하는 것이 더 안전하다
      throw new AuthError('CONCURRENT_REQUEST');
    }
  }

  await revokeFamily(tokenRecord.familyId);
  throw new AuthError('REUSE_DETECTED');
}
```

grace period보다 Redis 분산 락이 더 정확하다. 동일 토큰에 대한 요청을 직렬화하면 동시 요청 자체가 불가능해진다.

```javascript
async function rotateWithLock(rawToken) {
  const tokenHash = sha256(rawToken);
  const lockKey = `lock:rt:${tokenHash}`;

  const acquired = await redis.set(lockKey, '1', 'NX', 'EX', 5);
  if (!acquired) {
    throw new AuthError('CONCURRENT_REQUEST');
  }

  try {
    return await rotateRefreshToken(rawToken);
  } finally {
    await redis.del(lockKey);
  }
}
```

락 TTL(5초)은 rotate 함수 처리 시간보다 넉넉하게 설정한다. DB 응답이 느린 경우를 고려해야 한다.

## Node.js 전체 구현

```javascript
// services/token.service.js
const crypto = require('crypto');
const jwt = require('jsonwebtoken');

class TokenService {
  constructor({ db, redis, jwtSecret, jwtExpiresIn = '15m', refreshTTLDays = 7 }) {
    this.db = db;
    this.redis = redis;
    this.jwtSecret = jwtSecret;
    this.jwtExpiresIn = jwtExpiresIn;
    this.refreshTTLMs = refreshTTLDays * 24 * 60 * 60 * 1000;
  }

  async issueTokenPair(userId) {
    const familyId = crypto.randomUUID();
    const rawRefreshToken = this.#generateRaw();

    await this.db.refreshTokens.insertOne({
      id: crypto.randomUUID(),
      familyId,
      userId,
      tokenHash: this.#hash(rawRefreshToken),
      parentId: null,
      isUsed: false,
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + this.refreshTTLMs),
    });

    return {
      accessToken: this.#issueAccess(userId),
      refreshToken: rawRefreshToken,
    };
  }

  async rotate(rawRefreshToken) {
    const tokenHash = this.#hash(rawRefreshToken);
    const lockKey = `lock:rt:${tokenHash}`;

    const acquired = await this.redis.set(lockKey, '1', 'NX', 'EX', 5);
    if (!acquired) {
      throw Object.assign(new Error('CONCURRENT_REQUEST'), { status: 429 });
    }

    try {
      return await this.#doRotate(tokenHash);
    } finally {
      await this.redis.del(lockKey);
    }
  }

  async #doRotate(tokenHash) {
    const cacheKey = `rt:${tokenHash}`;
    let record = await this.#getCached(cacheKey);

    if (!record) {
      record = await this.db.refreshTokens.findOne({ tokenHash });
      if (record) {
        await this.redis.set(cacheKey, JSON.stringify(record), 'EX', 300);
      }
    }

    if (!record) {
      throw Object.assign(new Error('INVALID_TOKEN'), { status: 401 });
    }

    if (record.expiresAt < Date.now()) {
      await this.redis.del(cacheKey);
      throw Object.assign(new Error('TOKEN_EXPIRED'), { status: 401 });
    }

    if (record.isUsed) {
      await this.#revokeFamily(record.familyId);
      await this.redis.del(cacheKey);
      throw Object.assign(new Error('REUSE_DETECTED'), { status: 401 });
    }

    await this.db.refreshTokens.updateOne(
      { tokenHash },
      { isUsed: true, usedAt: new Date() }
    );
    await this.redis.del(cacheKey);

    const newRaw = this.#generateRaw();
    const newHash = this.#hash(newRaw);

    await this.db.refreshTokens.insertOne({
      id: crypto.randomUUID(),
      familyId: record.familyId,
      userId: record.userId,
      tokenHash: newHash,
      parentId: record.id,
      isUsed: false,
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + this.refreshTTLMs),
    });

    return {
      accessToken: this.#issueAccess(record.userId),
      refreshToken: newRaw,
    };
  }

  async revokeByUser(userId) {
    await this.db.refreshTokens.updateMany(
      { userId, isUsed: false },
      { isUsed: true, revokedAt: new Date(), revokeReason: 'USER_LOGOUT' }
    );
  }

  async #revokeFamily(familyId) {
    await this.db.refreshTokens.updateMany(
      { familyId },
      { isUsed: true, revokedAt: new Date(), revokeReason: 'REUSE_DETECTED' }
    );
  }

  async #getCached(key) {
    const raw = await this.redis.get(key);
    return raw ? JSON.parse(raw) : null;
  }

  #issueAccess(userId) {
    return jwt.sign({ sub: String(userId) }, this.jwtSecret, {
      algorithm: 'HS256',
      expiresIn: this.jwtExpiresIn,
    });
  }

  #generateRaw() {
    return crypto.randomBytes(40).toString('hex');
  }

  #hash(raw) {
    return crypto.createHash('sha256').update(raw).digest('hex');
  }
}

module.exports = { TokenService };
```

```javascript
// routes/auth.js
const express = require('express');
const router = express.Router();

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'strict',
  path: '/auth/refresh',
  maxAge: 7 * 24 * 60 * 60 * 1000,
};

router.post('/auth/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await userService.verify(email, password);

  const { accessToken, refreshToken } = await tokenService.issueTokenPair(user.id);

  res.cookie('refreshToken', refreshToken, COOKIE_OPTIONS);
  res.json({ accessToken });
});

router.post('/auth/refresh', async (req, res) => {
  const rawToken = req.cookies?.refreshToken;
  if (!rawToken) {
    return res.status(401).json({ error: 'MISSING_TOKEN' });
  }

  try {
    const { accessToken, refreshToken } = await tokenService.rotate(rawToken);
    res.cookie('refreshToken', refreshToken, COOKIE_OPTIONS);
    return res.json({ accessToken });
  } catch (err) {
    res.clearCookie('refreshToken', { path: '/auth/refresh' });

    if (err.message === 'REUSE_DETECTED') {
      return res.status(401).json({ error: 'TOKEN_COMPROMISED' });
    }
    if (err.status === 429) {
      return res.status(429).json({ error: 'CONCURRENT_REQUEST' });
    }
    return res.status(401).json({ error: 'UNAUTHORIZED' });
  }
});

router.post('/auth/logout', authenticate, async (req, res) => {
  await tokenService.revokeByUser(req.user.id);
  res.clearCookie('refreshToken', { path: '/auth/refresh' });
  res.status(204).end();
});
```

## Spring 구현

```java
// domain/RefreshToken.java
@Entity
@Table(name = "refresh_tokens")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class RefreshToken {

    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID familyId;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, unique = true, length = 64)
    private String tokenHash;

    private UUID parentId;

    @Column(nullable = false)
    private boolean isUsed = false;

    private LocalDateTime usedAt;
    private LocalDateTime revokedAt;
    private String revokeReason;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime expiresAt;

    public static RefreshToken create(UUID familyId, Long userId, String tokenHash, UUID parentId, int ttlDays) {
        RefreshToken token = new RefreshToken();
        token.id = UUID.randomUUID();
        token.familyId = familyId;
        token.userId = userId;
        token.tokenHash = tokenHash;
        token.parentId = parentId;
        token.isUsed = false;
        token.createdAt = LocalDateTime.now();
        token.expiresAt = LocalDateTime.now().plusDays(ttlDays);
        return token;
    }

    public void markUsed() {
        this.isUsed = true;
        this.usedAt = LocalDateTime.now();
    }

    public boolean isExpired() {
        return this.expiresAt.isBefore(LocalDateTime.now());
    }
}
```

```java
// repository/RefreshTokenRepository.java
public interface RefreshTokenRepository extends JpaRepository<RefreshToken, UUID> {

    Optional<RefreshToken> findByTokenHash(String tokenHash);

    @Modifying
    @Query("""
        UPDATE RefreshToken t SET t.isUsed = true,
        t.revokedAt = :revokedAt, t.revokeReason = :reason
        WHERE t.familyId = :familyId
    """)
    void revokeAllByFamilyId(UUID familyId, LocalDateTime revokedAt, String reason);

    @Modifying
    @Query("""
        UPDATE RefreshToken t SET t.isUsed = true,
        t.revokedAt = :revokedAt, t.revokeReason = :reason
        WHERE t.userId = :userId AND t.isUsed = false
    """)
    void revokeAllByUserId(Long userId, LocalDateTime revokedAt, String reason);
}
```

```java
// service/TokenService.java
@Service
@RequiredArgsConstructor
public class TokenService {

    private final RefreshTokenRepository tokenRepo;
    private final RedisTemplate<String, String> redis;
    private final JwtProvider jwtProvider;
    private final ObjectMapper objectMapper;

    private static final int REFRESH_TTL_DAYS = 7;
    private static final Duration CACHE_TTL = Duration.ofMinutes(5);
    private static final Duration LOCK_TTL = Duration.ofSeconds(5);

    public TokenPair issueTokenPair(Long userId) {
        String rawToken = generateRaw();
        UUID familyId = UUID.randomUUID();

        RefreshToken token = RefreshToken.create(
            familyId, userId, hash(rawToken), null, REFRESH_TTL_DAYS
        );
        tokenRepo.save(token);

        return new TokenPair(jwtProvider.issue(userId), rawToken);
    }

    @Transactional
    public TokenPair rotate(String rawToken) {
        String tokenHash = hash(rawToken);
        String lockKey = "lock:rt:" + tokenHash;

        Boolean acquired = redis.opsForValue()
            .setIfAbsent(lockKey, "1", LOCK_TTL);

        if (!Boolean.TRUE.equals(acquired)) {
            throw new ConcurrentRequestException();
        }

        try {
            return doRotate(tokenHash);
        } finally {
            redis.delete(lockKey);
        }
    }

    private TokenPair doRotate(String tokenHash) {
        String cacheKey = "rt:" + tokenHash;

        RefreshToken token = findToken(tokenHash, cacheKey);

        if (token.isExpired()) {
            redis.delete(cacheKey);
            throw new TokenExpiredException();
        }

        if (token.isUsed()) {
            tokenRepo.revokeAllByFamilyId(
                token.getFamilyId(), LocalDateTime.now(), "REUSE_DETECTED"
            );
            redis.delete(cacheKey);
            throw new TokenReuseDetectedException();
        }

        token.markUsed();
        tokenRepo.save(token);
        redis.delete(cacheKey);

        String newRaw = generateRaw();
        RefreshToken newToken = RefreshToken.create(
            token.getFamilyId(), token.getUserId(),
            hash(newRaw), token.getId(), REFRESH_TTL_DAYS
        );
        tokenRepo.save(newToken);

        return new TokenPair(jwtProvider.issue(token.getUserId()), newRaw);
    }

    public void revokeByUser(Long userId) {
        tokenRepo.revokeAllByUserId(userId, LocalDateTime.now(), "USER_LOGOUT");
    }

    private RefreshToken findToken(String tokenHash, String cacheKey) {
        String cached = redis.opsForValue().get(cacheKey);
        if (cached != null) {
            try {
                return objectMapper.readValue(cached, RefreshToken.class);
            } catch (JsonProcessingException ignored) {}
        }

        RefreshToken token = tokenRepo.findByTokenHash(tokenHash)
            .orElseThrow(InvalidTokenException::new);

        try {
            redis.opsForValue().set(cacheKey, objectMapper.writeValueAsString(token), CACHE_TTL);
        } catch (JsonProcessingException ignored) {}

        return token;
    }

    private String generateRaw() {
        byte[] bytes = new byte[40];
        new SecureRandom().nextBytes(bytes);
        return HexFormat.of().formatHex(bytes);
    }

    private String hash(String raw) {
        return Hashing.sha256()
            .hashString(raw, StandardCharsets.UTF_8)
            .toString();
    }
}
```

```java
// controller/AuthController.java
@RestController
@RequiredArgsConstructor
public class AuthController {

    private final TokenService tokenService;
    private static final String REFRESH_COOKIE = "refreshToken";
    private static final int COOKIE_MAX_AGE = 7 * 24 * 60 * 60;

    @PostMapping("/auth/refresh")
    public ResponseEntity<AccessTokenResponse> refresh(
        @CookieValue(name = REFRESH_COOKIE, required = false) String rawToken,
        HttpServletResponse response
    ) {
        if (rawToken == null) {
            return ResponseEntity.status(UNAUTHORIZED).build();
        }

        try {
            TokenPair pair = tokenService.rotate(rawToken);
            addRefreshCookie(response, pair.refreshToken());
            return ResponseEntity.ok(new AccessTokenResponse(pair.accessToken()));

        } catch (TokenReuseDetectedException e) {
            clearRefreshCookie(response);
            return ResponseEntity.status(UNAUTHORIZED)
                .body(new AccessTokenResponse(null));

        } catch (ConcurrentRequestException e) {
            return ResponseEntity.status(TOO_MANY_REQUESTS).build();

        } catch (InvalidTokenException | TokenExpiredException e) {
            clearRefreshCookie(response);
            return ResponseEntity.status(UNAUTHORIZED).build();
        }
    }

    @PostMapping("/auth/logout")
    public ResponseEntity<Void> logout(
        @AuthenticationPrincipal UserDetails user,
        HttpServletResponse response
    ) {
        tokenService.revokeByUser(Long.parseLong(user.getUsername()));
        clearRefreshCookie(response);
        return ResponseEntity.noContent().build();
    }

    private void addRefreshCookie(HttpServletResponse response, String value) {
        ResponseCookie cookie = ResponseCookie.from(REFRESH_COOKIE, value)
            .httpOnly(true)
            .secure(true)
            .sameSite("Strict")
            .path("/auth/refresh")
            .maxAge(COOKIE_MAX_AGE)
            .build();
        response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());
    }

    private void clearRefreshCookie(HttpServletResponse response) {
        ResponseCookie cookie = ResponseCookie.from(REFRESH_COOKIE, "")
            .httpOnly(true)
            .secure(true)
            .path("/auth/refresh")
            .maxAge(0)
            .build();
        response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());
    }
}
```

## 운영 시 주의사항

**토큰 원문은 DB에 저장하지 않는다.** SHA-256 해시만 저장한다. DB가 유출돼도 해시로는 실제 토큰을 복원할 수 없다.

**만료·폐기된 토큰 정리.** `is_used = true`이거나 `expires_at`이 지난 레코드가 계속 쌓인다. 배치 잡으로 주기적으로 삭제해야 한다. 보안 사고 추적을 위해 최근 30일치 폐기 이력은 남겨두는 경우도 있다.

```sql
-- 만료 후 30일 지난 토큰 삭제 (배치)
DELETE FROM refresh_tokens
WHERE expires_at < NOW() - INTERVAL '30 days';
```

**다중 기기 로그인 처리.** 기기별로 별도 `familyId`를 관리한다. 로그인 시 기존 family를 전부 폐기하면 단일 기기만 허용된다. 다중 기기를 허용하려면 로그인마다 새 family를 생성하고, 기기 정보(user_agent, device_id)를 저장해두면 관리 UI에서 "이 기기 로그아웃" 기능을 제공할 수 있다.

**Refresh Token 쿠키 path 설정.** `path=/`로 설정하면 모든 요청에 Refresh Token 쿠키가 포함된다. `path=/auth/refresh`로 좁히면 갱신 요청에만 전송되어 노출 범위가 줄어든다.

**재사용 감지 후 알림.** `REUSE_DETECTED`가 발생하면 사용자에게 보안 이메일을 발송하는 것이 좋다. "다른 기기에서 비정상적인 접근이 감지되어 보안상 재로그인이 필요합니다" 수준의 안내다. 탈취가 아닌 grace period 범위를 벗어난 클라이언트 버그인 경우도 있으므로, 알림 문구는 단정적이기보다 가능성 수준으로 표현한다.

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
