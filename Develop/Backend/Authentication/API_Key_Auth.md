---
title: API Key 인증 구현
tags: [backend, auth, security, performance]
updated: 2026-07-22
---

# API Key 인증 구현

## 언제 API Key를 쓰나

JWT와 OAuth2가 있는데 굳이 API Key를 쓰는 상황이 있다. 사람이 아닌 시스템이 요청하는 서버 간 통신, 외부 개발자에게 특정 기능을 열어주는 경우가 대표적이다. JWT는 만료 시간과 갱신 흐름을 관리해야 하고, OAuth2는 인가 서버가 필요하다. API Key는 이런 부가 인프라 없이 운영 가능하고, 클라이언트가 브라우저가 아닌 경우 토큰 갱신 로직을 별도로 짜야 하는 불편함도 없다.

실제로 많이 보이는 케이스:
- 내부 마이크로서비스끼리 서로를 호출할 때 서비스 계정 개념으로 사용
- B2B SaaS에서 기업 고객이 자기 시스템에서 API를 직접 호출할 때
- CI/CD 파이프라인이나 배치 작업에서 API를 쓸 때
- Slack, GitHub, Stripe 같은 서비스의 webhook 발신 검증

단점도 있다. 만료 시간이 없으니 키가 유출되면 바꾸기 전까지 계속 쓸 수 있다. 이 때문에 rotation 정책과 최소 권한 원칙(scope)을 같이 운영해야 한다.

## 키 생성

`crypto.randomBytes(32)`로 32바이트 난수를 생성하면 256비트 엔트로피가 나온다. hex로 인코딩하면 64자리 문자열이 된다.

```javascript
const crypto = require('crypto');

function generateApiKey() {
  return crypto.randomBytes(32).toString('hex');
}
// 출력 예: "a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
```

Base64url을 쓰기도 한다. 64자 → 43자로 줄어들어 HTTP 헤더에 담기 편하다.

```javascript
function generateApiKey() {
  return crypto.randomBytes(32).toString('base64url');
}
// 출력 예: "o_iywd7lR7a3yJnQ4fKiXcNnt6m0dGv8bY2PkqsjHUw"
```

UUID를 키로 쓰는 경우를 가끔 보는데, UUID v4는 122비트 엔트로피다. 그것도 충분하지만, UUID의 특정 비트는 버전과 변형을 나타내는 고정값이어서 실제 엔트로피는 그보다 낮다. `crypto.randomBytes`로 직접 생성하는 게 더 깔끔하다.

## 저장 방식 — 평문 없이 SHA-256 해싱

API Key를 DB에 평문으로 저장하면 DB가 털렸을 때 모든 키가 노출된다. 비밀번호처럼 단방향 해시로 저장해야 한다.

비밀번호와 다른 점은 bcrypt 같은 느린 KDF가 필요 없다는 것이다. API Key는 이미 무작위로 생성된 높은 엔트로피 값이라 레인보우 테이블 공격이 의미 없고, 브루트포스도 현실적으로 불가능하다. SHA-256으로 충분하다.

```javascript
function hashApiKey(rawKey) {
  return crypto.createHash('sha256').update(rawKey).digest('hex');
}
```

키를 생성하고 발급하는 흐름:

```javascript
async function issueApiKey(userId, scopes) {
  const rawKey = crypto.randomBytes(32).toString('hex');
  const hashedKey = hashApiKey(rawKey);

  await db.apiKeys.insert({
    user_id: userId,
    hashed_key: hashedKey,
    scopes: scopes,
    created_at: new Date(),
    last_used_at: null,
    rotated_at: null,
  });

  // rawKey는 이 시점에만 반환한다. DB에는 저장하지 않는다.
  return rawKey;
}
```

`rawKey`는 발급 시 딱 한 번만 사용자에게 보여 준다. 이후에는 절대 복구할 수 없다고 명시해야 한다. GitHub Personal Access Token이 이 방식을 쓴다. 생성하는 순간에만 볼 수 있고, 이후에는 마스킹된 prefix만 보여 준다.

## prefix + hash 분리 조회 패턴

전체 키로 DB를 조회하는 방법도 있지만, 이 경우 `hashed_key` 컬럼에 인덱스가 없으면 full table scan이 된다. 인덱스를 걸어도 되는데, 더 나은 방법이 있다.

키 앞에 prefix를 붙이는 패턴이다. Stripe의 `sk_live_xxx...`, GitHub의 `ghp_xxx...` 같은 형식이 이것이다. prefix는 평문으로 DB에 저장해서 먼저 후보를 좁히고, 나머지 부분의 해시로 최종 검증한다.

```javascript
function generateApiKey(prefix = 'sk') {
  const randomPart = crypto.randomBytes(24).toString('hex'); // 48자
  const rawKey = `${prefix}_${randomPart}`;
  return rawKey;
}
// 출력 예: "sk_a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2"

function parseApiKey(rawKey) {
  const underscoreIdx = rawKey.indexOf('_');
  if (underscoreIdx === -1) return null;
  const prefix = rawKey.substring(0, underscoreIdx);
  const token = rawKey.substring(underscoreIdx + 1);
  return { prefix, token };
}

async function issueApiKey(userId, scopes, keyPrefix = 'sk') {
  const rawKey = generateApiKey(keyPrefix);
  const { prefix, token } = parseApiKey(rawKey);
  const hashedToken = crypto.createHash('sha256').update(token).digest('hex');

  await db.apiKeys.insert({
    user_id: userId,
    key_prefix: prefix,           // 인덱스 컬럼
    hashed_token: hashedToken,    // 검증용
    scopes: JSON.stringify(scopes),
    created_at: new Date(),
  });

  return rawKey;
}
```

검증 미들웨어:

```javascript
async function authenticateApiKey(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing API key' });
  }

  const rawKey = authHeader.slice(7);
  const parsed = parseApiKey(rawKey);
  if (!parsed) {
    return res.status(401).json({ error: 'Invalid API key format' });
  }

  const { prefix, token } = parsed;
  const hashedToken = crypto.createHash('sha256').update(token).digest('hex');

  // prefix로 좁히고, hashed_token으로 최종 검증
  const apiKey = await db.apiKeys.findOne({
    key_prefix: prefix,
    hashed_token: hashedToken,
    revoked_at: null,
  });

  if (!apiKey) {
    return res.status(401).json({ error: 'Invalid API key' });
  }

  // 마지막 사용 시각 갱신 (비동기로 넘김)
  db.apiKeys.update(
    { id: apiKey.id },
    { last_used_at: new Date() }
  ).catch(console.error);

  req.apiKey = apiKey;
  next();
}
```

prefix를 단순 문자열 대신 의미 있는 값으로 쓰면 디버깅에 도움이 된다. `sk`(secret key), `pk`(public key), `test_sk`(테스트용 시크릿) 같이 환경과 용도를 구분한다.

## Scope 기반 권한

키 하나로 모든 API를 열어 주면, 키 하나가 유출될 때 피해 범위가 전체가 된다. scope를 정의해서 키마다 허용 범위를 좁힌다.

```javascript
const SCOPES = {
  'read:orders':    '주문 조회',
  'write:orders':   '주문 생성/수정',
  'read:products':  '상품 조회',
  'write:products': '상품 생성/수정',
  'read:users':     '사용자 조회',
  'admin':          '모든 권한',
};

function requireScope(...requiredScopes) {
  return (req, res, next) => {
    const keyScopes = JSON.parse(req.apiKey.scopes);

    if (keyScopes.includes('admin')) {
      return next();
    }

    const hasAll = requiredScopes.every(s => keyScopes.includes(s));
    if (!hasAll) {
      return res.status(403).json({
        error: 'Insufficient scope',
        required: requiredScopes,
        current: keyScopes,
      });
    }

    next();
  };
}

// 라우트에서 사용
router.get('/orders',
  authenticateApiKey,
  requireScope('read:orders'),
  listOrdersHandler
);

router.post('/orders',
  authenticateApiKey,
  requireScope('write:orders'),
  createOrderHandler
);
```

scope 설계에서 자주 보이는 실수는 너무 세분화하는 것이다. 10개 scope보다 3~4개가 낫다. 외부 개발자 입장에서 어떤 scope를 요청해야 하는지 직관적이어야 한다. Stripe처럼 `read_only` / `restricted` / `full` 세 단계로 나누는 것도 현실적인 선택이다.

## Per-key Rate Limiting

전체 API에 rate limiting을 거는 것과 별개로, 키마다 다른 한도를 적용해야 하는 경우가 있다. 기업 고객 키는 분당 1000 req, 무료 플랜 키는 분당 60 req 같은 식이다.

Redis를 쓴다면 키 ID로 카운터를 관리하는 게 자연스럽다.

```javascript
const redis = require('ioredis');
const client = new redis();

async function checkRateLimit(apiKeyId, limit, windowSeconds) {
  const key = `rate_limit:${apiKeyId}:${Math.floor(Date.now() / 1000 / windowSeconds)}`;

  const [current] = await client.multi()
    .incr(key)
    .expire(key, windowSeconds)
    .exec();

  const count = current[1];
  return {
    allowed: count <= limit,
    current: count,
    limit,
    resetAt: (Math.floor(Date.now() / 1000 / windowSeconds) + 1) * windowSeconds,
  };
}

async function rateLimitMiddleware(req, res, next) {
  const apiKey = req.apiKey;
  const limit = apiKey.rate_limit || 60;     // DB에서 가져온 키별 한도
  const window = 60;                          // 60초 윈도우

  const result = await checkRateLimit(apiKey.id, limit, window);

  res.set({
    'X-RateLimit-Limit': limit,
    'X-RateLimit-Remaining': Math.max(0, limit - result.current),
    'X-RateLimit-Reset': result.resetAt,
  });

  if (!result.allowed) {
    return res.status(429).json({ error: 'Rate limit exceeded' });
  }

  next();
}
```

sliding window가 필요하면 Redis의 sorted set으로 구현한다. 위 방식은 fixed window라서 경계 근처에서 순간 burst가 2배까지 허용되는 단점이 있다. 실제로 문제가 되는 경우는 드물지만, 정밀한 제한이 필요하면 sliding window로 간다.

per-key rate limit 설정은 DB의 `api_keys` 테이블에 두면 된다.

```sql
ALTER TABLE api_keys ADD COLUMN rate_limit_per_minute INTEGER NOT NULL DEFAULT 60;
```

플랜에 따라 키 생성 시 자동으로 적용하거나, 어드민 콘솔에서 개별 조정하는 방식으로 운영한다.

## 키 Rotation

키 rotation은 두 가지 상황에서 한다. 주기적인 보안 정책(예: 90일 주기)과, 키가 유출되었을 때다.

### 무중단 rotation

서비스가 즉시 키를 바꾸면 클라이언트가 새 키로 전환하기 전까지 요청이 401로 튕긴다. 이를 막으려면 이전 키와 새 키를 겹쳐서 유효 기간을 두는 방식이 필요하다.

```javascript
async function rotateApiKey(oldKeyId) {
  const oldKey = await db.apiKeys.findById(oldKeyId);
  if (!oldKey) throw new Error('Key not found');

  // 새 키를 발급하고 이전 키와 연결
  const rawKey = generateApiKey(oldKey.key_prefix);
  const { prefix, token } = parseApiKey(rawKey);
  const hashedToken = crypto.createHash('sha256').update(token).digest('hex');

  const newKeyId = await db.apiKeys.insert({
    user_id: oldKey.user_id,
    key_prefix: prefix,
    hashed_token: hashedToken,
    scopes: oldKey.scopes,
    rate_limit_per_minute: oldKey.rate_limit_per_minute,
    predecessor_id: oldKeyId,       // 이전 키 참조
    created_at: new Date(),
  });

  // 이전 키에 만료 예정 시각 설정 (예: 48시간 뒤 자동 만료)
  const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000);
  await db.apiKeys.update(
    { id: oldKeyId },
    { expires_at: expiresAt, rotated_to: newKeyId }
  );

  return { newKeyId, rawKey, oldKeyExpiresAt: expiresAt };
}
```

```javascript
// 검증 시 만료 시각도 함께 체크
const apiKey = await db.apiKeys.findOne({
  key_prefix: prefix,
  hashed_token: hashedToken,
  revoked_at: null,
  expires_at: { $gt: new Date() },  // 만료되지 않은 것만
});
```

rotation 후 응답 헤더에 `Deprecation` 헤더를 넣어 클라이언트에게 알려 주는 방법도 있다.

```javascript
if (req.apiKey.expires_at) {
  res.set('Deprecation', req.apiKey.expires_at.toUTCString());
  res.set('Sunset', req.apiKey.expires_at.toUTCString());
}
```

### 즉시 폐기

유출이 확인된 키는 즉시 비활성화해야 한다.

```javascript
async function revokeApiKey(keyId, reason) {
  await db.apiKeys.update(
    { id: keyId },
    {
      revoked_at: new Date(),
      revoke_reason: reason,  // "leaked", "user_request", "policy" 등
    }
  );

  // 이 키로 발급된 세션이나 캐시된 인증 정보도 무효화
  await redis.del(`auth_cache:${keyId}`);
}
```

검증 결과를 짧게 캐싱하면 DB 부하를 줄일 수 있지만, 폐기 시 해당 캐시를 명시적으로 날려야 즉시 효력이 생긴다.

## 감사 로그

어떤 키가 어느 IP에서 어떤 엔드포인트를 언제 호출했는지 기록하면, 유출 조사나 이상 탐지에 쓸 수 있다.

```javascript
async function logApiKeyUsage(req, apiKey, responseCode) {
  // 비동기로 넘겨서 응답 지연에 영향 없게
  setImmediate(async () => {
    try {
      await db.apiKeyLogs.insert({
        api_key_id: apiKey.id,
        user_id: apiKey.user_id,
        ip_address: req.ip,
        method: req.method,
        path: req.path,
        response_code: responseCode,
        timestamp: new Date(),
      });
    } catch (err) {
      console.error('Failed to log API key usage:', err);
    }
  });
}
```

로그 테이블은 빠르게 커진다. 파티셔닝이나 retention 정책을 미리 잡아야 한다. 30일 이상 된 로그는 S3로 archiving하고 DB에서 지우는 방식이 현실적이다.

## 자주 마주치는 함정

### 키를 로그에 남기는 실수

요청 전체를 `console.log`로 찍다 보면 Authorization 헤더가 고스란히 찍힌다. 로그 수집기(ELK, Datadog)에 들어가고 나면 걷어내기가 어렵다. 미들웨어 단에서 Authorization 헤더를 제거하거나 마스킹하는 처리를 해야 한다.

```javascript
// 요청 로깅 미들웨어에서
function sanitizeHeaders(headers) {
  const sanitized = { ...headers };
  if (sanitized['authorization']) {
    sanitized['authorization'] = 'Bearer [REDACTED]';
  }
  return sanitized;
}
```

### 키를 URL 쿼리 파라미터로 넘기는 것

`?api_key=sk_xxx` 형태로 넘기면 URL이 서버 로그, 브라우저 히스토리, CDN 로그, 리퍼러 헤더에 남는다. `Authorization: Bearer sk_xxx` 헤더로 넘겨야 한다. 어쩔 수 없이 쿼리 파라미터를 써야 하는 경우(일부 webhook 콜백 등)에는 반드시 HTTPS이고, 단기 유효 키를 따로 발급해서 쓴다.

### 타이밍 공격

prefix로 후보를 찾고 hashed_token을 비교하는 과정에서, `===` 같은 일반 문자열 비교를 쓰면 일치 여부가 응답 시간에 반영될 수 있다. Node.js의 `crypto.timingSafeEqual`을 써야 한다.

```javascript
function safeCompare(a, b) {
  const aBuf = Buffer.from(a, 'hex');
  const bBuf = Buffer.from(b, 'hex');
  if (aBuf.length !== bBuf.length) return false;
  return crypto.timingSafeEqual(aBuf, bBuf);
}

// 검증 시
const storedHash = apiKey.hashed_token;
const inputHash = crypto.createHash('sha256').update(token).digest('hex');
if (!safeCompare(storedHash, inputHash)) {
  return res.status(401).json({ error: 'Invalid API key' });
}
```

사실 SHA-256 해시 비교는 DB 조회 선택 쿼리에서 이미 상수 시간이 보장되지 않아서, `timingSafeEqual`로 완벽히 막기는 어렵다. 그래도 application layer에서 할 수 있는 조치는 해 두는 게 낫다. 더 중요한 건 실패 응답에 키 존재 여부를 노출하지 않는 것이다.

### 만료 없는 키 방치

API Key에는 기본적으로 만료 시간이 없다. 발급하고 잊어버리면 퇴사한 직원, 해지된 서비스, 오래된 배치 작업의 키가 계속 살아있다. 정기적으로 90일 이상 `last_used_at`이 없는 키를 찾아 비활성화하는 배치를 돌려야 한다.

```sql
SELECT id, user_id, key_prefix, created_at, last_used_at
FROM api_keys
WHERE revoked_at IS NULL
  AND (
    last_used_at IS NULL AND created_at < NOW() - INTERVAL 90 DAY
    OR last_used_at < NOW() - INTERVAL 90 DAY
  );
```

이 결과를 이메일로 알리고 일정 기간 후 자동 폐기하는 흐름으로 운영한다.

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
