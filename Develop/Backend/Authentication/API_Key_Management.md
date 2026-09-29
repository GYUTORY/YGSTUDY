---
title: API 키 관리
tags: [auth, security, api, backend]
updated: 2026-09-29
---

API 키는 사람이 아닌 클라이언트(서버, 봇, CLI 도구)를 식별할 때 쓴다. OAuth 토큰보다 단순하고 세션 기반보다 stateless하게 관리할 수 있어서 B2B API나 내부 서비스 간 통신에 여전히 많이 쓰인다.

## 발급과 저장

API 키는 생성 시점에 클라이언트에게 딱 한 번만 보여준다. 서버는 이후 원문을 버리고 해시만 저장한다. 비밀번호 저장과 같은 원칙이다.

키 생성은 crypto-secure 난수로 한다. `randomBytes(32)`면 256비트 엔트로피고, 이걸 `base64url`로 인코딩하면 43자가 나온다. 여기에 환경 prefix를 붙여 사람이 눈으로 어떤 키인지 구분할 수 있게 한다.

```javascript
import { randomBytes } from 'crypto';

function generateApiKey(env: 'live' | 'test') {
  const prefix = `sk_${env}_`;
  const secret = randomBytes(32).toString('base64url');
  return `${prefix}${secret}`;
}
// 결과 예: sk_live_a1b2c3d4_xYz7K9mQ...
```

발급 시 클라이언트에게 원문을 전달하고 DB에는 해시만 저장한다. 원문은 이 순간 이후 서버 어디에도 남으면 안 된다.

## bcrypt냐 HMAC-SHA256이냐

비밀번호 저장에 bcrypt를 쓰는 이유는 의도적으로 느리기 때문이다. 오프라인 사전 공격을 막으려는 목적이다. 그런데 API 키에 bcrypt를 그대로 쓰면 요청마다 수십 밀리초짜리 연산이 붙는다. 트래픽이 수천 RPS를 넘으면 CPU가 버텨주지 않는다.

API 키는 다르게 접근해야 한다. 비밀번호와 달리 API 키는 클라이언트가 브루트포스로 추측할 수 없다. 256비트 랜덤 키에 대한 오프라인 추측 공격은 의미가 없다. 여기서 필요한 건 속도가 아니라 DB가 털렸을 때 원문을 역산하지 못하게 하는 것이다.

HMAC-SHA256은 마이크로초 단위로 빠르고 결정론적이다. 서버가 가진 secret을 HMAC key로 쓰기 때문에, DB에 있는 `key_hash`만 가지고는 원문을 복원할 수 없다.

```javascript
import { createHmac } from 'crypto';

const HMAC_SECRET = process.env.API_KEY_HMAC_SECRET; // 32바이트 이상

function hashApiKey(rawKey: string): string {
  return createHmac('sha256', HMAC_SECRET)
    .update(rawKey)
    .digest('hex');
}
```

`API_KEY_HMAC_SECRET`은 애플리케이션 배포 시 주입하는 환경변수다. 이 값이 유출되면 DB 해시에서 역산이 가능해지므로 다른 secret과 분리해서 관리한다.

## prefix로 DB 조회 최적화

들어온 키 전체를 해시해서 `key_hash` 컬럼으로 풀스캔하는 건 DB 규모가 커지면 감당이 안 된다. 키에서 고유한 prefix를 분리해서 인덱스 조회를 먼저 하는 방식으로 해결한다.

키 형식을 `sk_live_{8자리 prefix}_{나머지 secret}` 으로 정의하면:

```sql
CREATE TABLE api_keys (
  id          BIGSERIAL PRIMARY KEY,
  prefix      CHAR(8)     NOT NULL,  -- 인덱스 대상
  key_hash    CHAR(64)    NOT NULL,  -- HMAC-SHA256 hex
  user_id     BIGINT      NOT NULL,
  scopes      TEXT[]      NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at  TIMESTAMPTZ,
  revoked_at  TIMESTAMPTZ
);

CREATE INDEX ON api_keys (prefix) WHERE revoked_at IS NULL;
```

검증 시 prefix로 후보를 좁히고 hash를 비교한다:

```javascript
import { timingSafeEqual } from 'crypto';

async function verifyApiKey(rawKey: string) {
  // 'sk_live_' 8자 이후 8자리가 prefix
  const prefix = rawKey.slice(8, 16);
  const hash = hashApiKey(rawKey);

  const rows = await db.query(
    `SELECT * FROM api_keys
     WHERE prefix = $1
       AND revoked_at IS NULL
       AND (expires_at IS NULL OR expires_at > NOW())`,
    [prefix]
  );

  for (const row of rows) {
    const match = timingSafeEqual(
      Buffer.from(row.key_hash, 'hex'),
      Buffer.from(hash, 'hex')
    );
    if (match) return row;
  }
  return null;
}
```

`timingSafeEqual`은 타이밍 공격 방어를 위해 반드시 써야 한다. 문자열 `===` 비교는 첫 번째 불일치 위치에서 조기 종료해서 비교 소요 시간으로 정보가 유출된다. prefix가 충분히 고유하면 `rows`는 거의 항상 1개라서 hash 비교는 1회로 끝난다.

## 스코프 설계

스코프 없이 발급하면 키 하나로 모든 API를 쓸 수 있어서 탈취 시 피해 범위가 크다. 스코프는 리소스와 액션의 조합으로 정의한다.

```
read:orders          주문 조회만
write:orders         주문 생성·수정
read:customers       고객 조회
admin:keys           키 발급·폐기 권한
```

와일드카드(`*`)는 내부 서비스끼리만 쓴다. 외부 클라이언트에 발급하는 키에 와일드카드를 주는 건 스코프를 안 쓰는 것과 같다.

```javascript
function requireScope(scope: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const key = req.apiKey;
    if (!key.scopes.includes(scope) && !key.scopes.includes('*')) {
      return res.status(403).json({ error: 'insufficient_scope' });
    }
    next();
  };
}

router.get('/orders', requireScope('read:orders'), ordersController.list);
router.post('/orders', requireScope('write:orders'), ordersController.create);
```

`admin:keys` 스코프가 포함된 키는 별도 테이블로 분리하거나 발급 횟수를 극도로 제한한다. 이 스코프로 발급된 키가 탈취되면 공격자가 새 키를 무한정 만들 수 있다.

## 교체 절차

교체가 필요한 상황은 주기적 로테이션 정책과 키 노출 사고 두 가지다. 노출 사고는 아래 절에서 따로 다룬다.

주기적 교체 시 기존 키를 바로 폐기하면 클라이언트 배포가 완료되기 전에 서비스가 끊긴다. 겹치는 구간이 필요하다. 새 키를 발급한 뒤 기존 키에 유예 시간을 준다:

```sql
-- 기존 키에 24시간 후 만료 설정
UPDATE api_keys
SET expires_at = NOW() + INTERVAL '24 hours'
WHERE id = $1 AND revoked_at IS NULL;
```

클라이언트가 새 키로 전환을 완료했다고 확인되면 기존 키를 완전히 폐기한다:

```sql
UPDATE api_keys SET revoked_at = NOW() WHERE id = $1;
```

행을 삭제하지 않고 `revoked_at`을 쓰는 이유는 감사 로그에 폐기 시점이 남아야 해서다. "이 키가 언제까지 유효했는가"는 나중에 보안 사고 분석 시 중요한 정보가 된다.

## rate limiting 연동

rate limiting은 IP가 아니라 키 단위로 걸어야 한다. IP 기반이면 NAT 뒤에 있는 정상 클라이언트들이 한도를 공유한다.

Redis sliding window 방식으로 키 단위 한도를 관리한다:

```javascript
async function checkRateLimit(
  keyId: string,
  limit: number,
  windowSec: number
): Promise<{ allowed: boolean; remaining: number }> {
  const now = Date.now();
  const windowStart = now - windowSec * 1000;
  const redisKey = `rl:${keyId}`;

  const pipe = redis.pipeline();
  pipe.zremrangebyscore(redisKey, '-inf', windowStart);
  pipe.zadd(redisKey, now, `${now}-${Math.random()}`);
  pipe.zcard(redisKey);
  pipe.expire(redisKey, windowSec + 1);

  const results = await pipe.exec();
  const count = results[2][1] as number;

  return {
    allowed: count <= limit,
    remaining: Math.max(0, limit - count),
  };
}
```

응답 헤더에 `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`를 반드시 붙인다. 클라이언트가 재시도 타이밍을 모르면 무조건 빠르게 재시도해서 한도를 더 빨리 소진한다.

스코프별로 한도를 다르게 줄 수도 있다. 읽기 전용 키에 분당 10,000을 허용하더라도 쓰기 키는 분당 1,000으로 제한하는 식이다.

```javascript
const SCOPE_LIMITS: Record<string, number> = {
  'read:orders': 10_000,
  'write:orders': 1_000,
  'admin:keys': 100,
};

function getLimitForKey(scopes: string[]): number {
  const min = scopes.reduce((acc, scope) => {
    return Math.min(acc, SCOPE_LIMITS[scope] ?? 5_000);
  }, Infinity);
  return min === Infinity ? 5_000 : min;
}
```

## 키가 로그에 찍혔을 때

가장 흔한 경로는 요청 전체를 로그에 찍는 미들웨어다. `Authorization: Bearer sk_live_...` 헤더가 access log에 그대로 들어간다. git에 `.env`를 커밋하거나 Slack에 붙여넣는 경우도 있다.

발견하는 즉시 교체를 기다리지 말고 해당 키를 먼저 폐기한다. 서비스 일부가 끊기더라도 폐기가 우선이다.

```sql
UPDATE api_keys SET revoked_at = NOW() WHERE key_hash = $1;
```

새 키를 발급해서 클라이언트에 전달하고, 전환 완료를 확인한 뒤에 다음 단계로 넘어간다.

노출 범위를 파악해야 한다. 로그라면 해당 로그 파일에 접근 가능한 인원을 확인한다. git이라면 `git log --all --source` 로 커밋 히스토리를 확인하고, 이미 GitHub에 올라갔다면 push 시각을 기록한다. GitHub secret scanning 알림이 오기를 기다리지 말고 직접 확인한다.

마지막으로 해당 키로 발생한 요청을 감사한다. access log에서 `api_key_id`로 필터링해 평소와 다른 IP, 비정상 엔드포인트 접근, 대량 조회가 있었는지 본다. 의심스러운 요청이 발견되면 그때부터 보안 사고 대응 프로세스로 넘어간다.

로그 마스킹은 사후 대책이 아니라 미리 해두는 것이다:

```javascript
// morgan에서 Authorization 헤더 마스킹
morgan.token('masked-auth', (req) => {
  const auth = req.headers['authorization'];
  if (!auth) return '-';
  // 'Bearer sk_live_' + 처음 8자만 남기고 나머지 마스킹
  return auth.slice(0, 24) + '****';
});
```

쿼리 파라미터로 API 키를 받는 설계는 피한다. URL은 프록시, CDN, 브라우저 히스토리에 전부 기록된다. 키는 반드시 헤더로만 받는다.
