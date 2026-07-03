---
title: 로그인 무차별 대입 방어
tags: [backend, authentication, security, rate-limiting, brute-force, redis]
updated: 2026-06-27
---

# 로그인 무차별 대입 방어

로그인 엔드포인트는 외부에 노출된 입력 검증 지점 중에서 공격이 가장 집중되는 곳이다. 인증 방식이 세션이든 JWT든 OAuth2든, 비밀번호를 검증하는 순간 무차별 대입(brute force)과 크리덴셜 스터핑(credential stuffing)의 표적이 된다. 인증 방식 선택과는 별개로 로그인 엔드포인트 자체를 어떻게 지킬지는 따로 설계해야 한다.

이 문서는 토큰 저장이나 CSRF 같은 인증 방식 내부 문제가 아니라, `POST /login` 하나를 운영하면서 실제로 부딪히는 문제와 처리 방법을 다룬다.

## 공격 유형 구분

방어를 설계하기 전에 막으려는 공격이 무엇인지 구분해야 한다. 대응 방식이 다르다.

```
무차별 대입 (Brute Force)
  - 한 계정에 대해 비밀번호를 바꿔가며 반복 시도
  - 같은 username, 다른 password
  - 계정 단위 카운터로 잡힌다

크리덴셜 스터핑 (Credential Stuffing)
  - 다른 사이트에서 유출된 (이메일, 비밀번호) 쌍을 그대로 시도
  - 계정마다 1~2회만 시도, 계정은 수천 개
  - 계정 단위 카운터로는 안 잡힌다 (각 계정 시도 횟수가 적으니까)
  - IP 단위, 디바이스 핑거프린트, 유출 비밀번호 탐지로 잡는다

비밀번호 스프레이 (Password Spraying)
  - 흔한 비밀번호 하나(예: Password123!)를 수많은 계정에 시도
  - 계정당 시도 횟수가 임계값 아래라 계정 잠금을 우회한다
```

계정 단위 잠금만 걸어두면 스터핑과 스프레이는 그대로 통과한다. 계정 단위와 IP/네트워크 단위 방어를 같이 둬야 하는 이유다.

## 레이트 리미팅: 고정 윈도우 vs 토큰 버킷

로그인 시도 빈도를 제한하는 게 1차 방어선이다. 알고리즘 선택에서 운영 차이가 갈린다.

### 고정 윈도우 (Fixed Window)

"1분에 5회"처럼 시간 구간을 고정해두고 카운트한다. 구현이 단순하다.

```javascript
// Redis 고정 윈도우
async function fixedWindow(key, limit, windowSec) {
  const count = await redis.incr(key);
  if (count === 1) {
    await redis.expire(key, windowSec);
  }
  return count <= limit;
}

// 사용
const allowed = await fixedWindow(`login:ip:${ip}`, 5, 60);
if (!allowed) throw new TooManyRequestsError();
```

문제는 경계에서 터진다. 윈도우가 12:00:00에 리셋된다고 하면, 공격자는 11:59:59에 5회, 12:00:01에 5회를 쏴서 2초 안에 10회를 보낸다. 한도가 분당 5회인데 실질적으로 짧은 구간에 두 배가 통과한다. 로그인 방어에서는 이 경계 폭발이 무시 못 할 구멍이 된다.

### 토큰 버킷 (Token Bucket)

버킷에 토큰을 일정 속도로 채우고, 요청마다 토큰을 하나 뺀다. 토큰이 없으면 거부한다. 순간적인 묶음 요청(burst)은 버킷 용량만큼 허용하되 평균 속도는 채움 속도로 묶인다. 경계 폭발이 없다.

```javascript
// Redis Lua로 토큰 버킷 (원자적 실행)
const TOKEN_BUCKET = `
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])  -- 초당 채워지는 토큰 수
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local last = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  last = now
end

local delta = math.max(0, now - last)
tokens = math.min(capacity, tokens + delta * refill_rate)

local allowed = 0
if tokens >= requested then
  tokens = tokens - requested
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
return allowed
`;

async function tokenBucket(key, capacity, refillRate) {
  const now = Math.floor(Date.now() / 1000);
  const allowed = await redis.eval(
    TOKEN_BUCKET, 1, key, capacity, refillRate, now, 1
  );
  return allowed === 1;
}

// 분당 5회 평균, 순간 최대 5회 허용
await tokenBucket(`login:ip:${ip}`, 5, 5 / 60);
```

로그인 방어에는 토큰 버킷을 쓴다. 사용자가 비밀번호를 한 번 틀리고 바로 다시 치는 정상 패턴(짧은 버스트)은 버킷 용량 안에서 통과하고, 자동화된 연속 시도는 채움 속도에 묶인다. 고정 윈도우는 내부 API 호출 제한처럼 경계 폭발이 치명적이지 않은 곳에 쓴다.

Redis 외에 Nginx `limit_req`(leaky bucket)나 API 게이트웨이의 레이트 리밋을 앞단에 두는 경우도 많다. 게이트웨이 레벨은 IP 단위 거친 차단, 애플리케이션 레벨은 계정 단위 정교한 차단으로 역할을 나눈다.

## 실패 카운터의 원자성 문제 (INCR + EXPIRE)

Redis로 실패 카운터를 만들 때 가장 자주 나오는 버그가 INCR과 EXPIRE를 따로 호출하는 데서 온다.

```javascript
// 잘못된 코드 - 경쟁 조건 있음
await redis.incr(key);
await redis.expire(key, 900);
```

INCR로 키를 만든 직후, EXPIRE를 실행하기 전에 프로세스가 죽거나 네트워크가 끊기면 TTL이 안 걸린 카운터가 영원히 남는다. 그 키는 절대 리셋되지 않으니 해당 계정이나 IP는 영구 잠금 상태가 된다. 실제로 운영 중에 "특정 사용자만 계속 로그인이 막힌다"는 문의가 들어와서 Redis를 까보면 TTL이 -1인 카운터가 나오는 경우가 있다.

해결은 둘을 원자적으로 묶는 것이다. INCR 결과가 1일 때(=키가 막 생성됐을 때)만 EXPIRE를 거는 패턴은 여전히 두 명령 사이 틈이 있으니, Lua로 한 번에 처리한다.

```javascript
// 원자적 증가 + TTL 보장
const INCR_WITH_TTL = `
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
-- 혹시 TTL이 빠진 키가 있으면 복구
if redis.call('TTL', KEYS[1]) == -1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
`;

async function incrFailCount(accountKey, ttlSec) {
  return await redis.eval(INCR_WITH_TTL, 1, accountKey, ttlSec);
}
```

`SET key value EX ttl NX`로 먼저 키를 만들고 INCR을 거는 방식도 있지만, 로그인 카운터는 위처럼 Lua 한 방으로 묶는 게 가장 깔끔하다. TTL이 -1인 키를 그 자리에서 복구하는 줄을 넣어두면 과거에 잘못 만들어진 키까지 자연스럽게 정리된다.

윈도우 방식을 슬라이딩으로 가져가려면 정렬 집합(ZSET)에 타임스탬프를 넣고 윈도우 밖 항목을 ZREMRANGEBYSCORE로 제거하는 패턴을 쓴다. 다만 키마다 멤버가 쌓이니 메모리를 더 먹는다. 로그인 실패 카운트 정도는 단순 INCR 카운터로 충분한 경우가 대부분이다.

## 점진적 지연 (Exponential Backoff)

실패할 때마다 응답을 조금씩 늦추면 자동화 도구의 처리량이 급격히 떨어진다. 정상 사용자는 한두 번 틀리는 수준이라 체감하지 못한다.

```javascript
async function loginDelay(failCount) {
  if (failCount <= 2) return;  // 2회까지는 지연 없음
  // 3회부터 지수적으로 증가, 상한 8초
  const delayMs = Math.min(2 ** (failCount - 2) * 250, 8000);
  await new Promise(r => setTimeout(r, delayMs));
}
```

여기서 주의할 점이 있다. 서버 측에서 `setTimeout`으로 응답을 늦추면 그 요청은 커넥션과 워커를 점유한 채 대기한다. 공격자가 의도적으로 실패 요청을 대량으로 보내면 지연 대기 중인 커넥션이 쌓여서 서버 자원이 고갈된다. 지연으로 공격자를 늦추려다 자기 서버를 묶어버리는 셈이다.

그래서 지연은 짧은 상한(몇 초)으로 두고, 진짜 차단은 레이트 리미팅과 잠금으로 처리한다. 지연만으로 막으려 하지 않는다. 비동기 처리가 되는 런타임(Node.js)에서는 커넥션 점유 부담이 덜하지만, 스레드 풀 기반(전통적 서블릿)에서는 지연 시간만큼 스레드가 묶이니 상한을 더 보수적으로 잡아야 한다.

## 임계값 기반 계정 잠금과 잠금 해제

실패가 임계값을 넘으면 계정을 일시 잠근다. 잠금에는 두 가지 방식이 있다.

```
하드 락 (Hard Lock)
  - 임계값 도달 시 계정을 잠그고, 관리자나 본인 인증 절차로만 해제
  - 강력하지만 DoS 자기유발 위험이 크다

소프트 락 (Soft Lock / 시간 기반 자동 해제)
  - 임계값 도달 시 일정 시간 잠그고, 시간이 지나면 자동 해제
  - 대부분의 서비스에 적합
```

시간 기반 자동 해제를 기본으로 둔다. Redis TTL이 그대로 잠금 해제 타이머가 된다.

```javascript
const MAX_FAILS = 5;
const LOCK_TTL = 900;  // 15분

async function checkAndRecordFail(accountId) {
  const key = `login:fail:account:${accountId}`;
  const count = await incrFailCount(key, LOCK_TTL);
  if (count >= MAX_FAILS) {
    // 카운터 자체의 TTL이 잠금 해제 시점이다
    return { locked: true, retryAfter: await redis.ttl(key) };
  }
  return { locked: false };
}

// 로그인 성공 시 카운터 삭제
async function onLoginSuccess(accountId) {
  await redis.del(`login:fail:account:${accountId}`);
}
```

실패 카운터 키 하나로 카운트와 잠금 시간을 동시에 표현하면 별도 잠금 플래그를 관리할 필요가 없다. 카운터가 살아있는 동안(TTL 안) 임계값을 넘었으면 잠긴 상태고, TTL이 끝나 카운터가 사라지면 자동으로 풀린다.

성공 시 카운터를 지우는 것도 중요하다. 어제 3번 틀린 기록이 남아서 오늘 2번 틀렸다고 잠기면 사용자는 영문을 모른다. 단, 카운터 삭제는 비밀번호 검증을 통과한 다음에만 한다. 통과 전에 지우면 카운터를 우회하는 길이 생긴다.

## 잠금으로 인한 DoS 자기유발

계정 잠금의 가장 큰 함정이다. 공격자가 피해자의 이메일만 알면, 일부러 비밀번호를 5번 틀려서 그 계정을 잠가버릴 수 있다. 비밀번호를 모르는데도 정상 사용자를 로그인 못 하게 만드는 서비스 거부(DoS)가 된다. 표적이 임원이나 특정 고객이면 업무 마비로 직결된다.

이걸 줄이는 방법들:

계정 단위 하드 락을 피하고 시간 기반 소프트 락으로 둔다. 15분 뒤 자동 해제면 공격자가 계속 잠그려면 계속 시도해야 하고, 그건 IP 레이트 리밋에 걸린다.

잠금 판단을 계정만이 아니라 (계정 + 출처) 조합으로 본다. 정상 사용자가 평소 쓰던 IP/디바이스에서 온 요청은 다른 IP에서 발생한 실패로 잠그지 않는다. 공격자가 외부 IP에서 5번 틀려도, 피해자 본인의 익숙한 디바이스에서는 로그인이 된다.

```javascript
// 출처를 함께 보는 잠금 판단
async function isLockedForRequest(accountId, ip, deviceId) {
  const globalKey = `login:fail:account:${accountId}`;
  const failCount = parseInt(await redis.get(globalKey) || '0');
  if (failCount < MAX_FAILS) return false;

  // 임계값을 넘었어도, 신뢰된 디바이스면 통과시킨다
  const trusted = await redis.sismember(
    `trusted:device:${accountId}`, deviceId
  );
  if (trusted) return false;

  return true;
}
```

신뢰 디바이스 목록은 과거 성공 로그인에서 디바이스를 등록해두고 채운다. 완벽하진 않지만, 표적형 계정 잠금 DoS의 피해를 크게 줄인다.

실패 임계값을 너무 낮게 잡지 않는 것도 자기유발 DoS를 줄인다. 3회는 정상 사용자가 비밀번호를 헷갈릴 때 쉽게 닿는다. 5~10회 정도로 두고, 대신 지연과 CAPTCHA로 그 사이를 메운다.

## CAPTCHA 단계적 도입

CAPTCHA를 모든 로그인에 붙이면 전환율이 떨어지고 사용자가 짜증낸다. 의심스러운 신호가 있을 때만 단계적으로 띄운다.

```
정상 흐름:        username + password
실패 누적 (예 3회): + CAPTCHA 요구
명백한 자동화:     CAPTCHA로도 안 풀리면 차단
```

```javascript
async function needsCaptcha(accountId, ip) {
  const accountFails = parseInt(
    await redis.get(`login:fail:account:${accountId}`) || '0'
  );
  const ipFails = parseInt(
    await redis.get(`login:fail:ip:${ip}`) || '0'
  );
  // 계정 3회 이상이거나, IP에서 단시간 10회 이상이면 CAPTCHA
  return accountFails >= 3 || ipFails >= 10;
}
```

CAPTCHA 검증은 반드시 서버에서 한다. 클라이언트가 보낸 "통과했음" 플래그를 믿으면 안 된다. reCAPTCHA나 hCaptcha의 경우 클라이언트 토큰을 받아 제공자 API로 서버에서 검증하고, 점수(reCAPTCHA v3는 0~1 점수)가 임계값 미만이면 추가 단계를 요구한다.

주의할 점은 CAPTCHA가 크리덴셜 스터핑의 결정적 방어가 아니라는 것이다. CAPTCHA 풀이 서비스를 돈 주고 우회하는 공격자가 있다. CAPTCHA는 자동화 비용을 올리는 수단이지, 그것 하나로 끝나지 않는다.

## 유출 비밀번호 탐지 (HIBP k-anonymity)

크리덴셜 스터핑은 이미 유출된 비밀번호를 그대로 쓴다. 사용자가 설정하려는(또는 로그인에 쓰는) 비밀번호가 알려진 유출 목록에 있는지 검사하면 스터핑이 통할 계정을 줄일 수 있다. Have I Been Pwned(HIBP)의 Pwned Passwords API가 이걸 제공한다.

핵심은 비밀번호 자체나 전체 해시를 외부로 보내지 않는다는 점이다. k-anonymity 방식으로 SHA-1 해시의 앞 5자리만 보낸다.

```javascript
const crypto = require('crypto');

async function isPwnedPassword(password) {
  const hash = crypto.createHash('sha1')
    .update(password)
    .digest('hex')
    .toUpperCase();

  const prefix = hash.slice(0, 5);   // 앞 5자리만 전송
  const suffix = hash.slice(5);      // 나머지는 로컬에서 비교

  const res = await fetch(
    `https://api.pwnedpasswords.com/range/${prefix}`
  );
  const text = await res.text();

  // 응답은 "접미사:노출횟수" 목록. 내 suffix가 있는지 본다
  for (const line of text.split('\n')) {
    const [respSuffix, count] = line.trim().split(':');
    if (respSuffix === suffix) {
      return parseInt(count);  // 유출 횟수 반환
    }
  }
  return 0;
}

// 비밀번호 설정/변경 시
const pwnedCount = await isPwnedPassword(newPassword);
if (pwnedCount > 0) {
  throw new ValidationError(
    '이 비밀번호는 외부 유출 목록에 포함돼 있습니다. 다른 비밀번호를 사용하세요.'
  );
}
```

5자리 접두사로 조회하면 같은 접두사를 가진 해시 수백 개가 한 번에 응답으로 온다. 그 안에서 내 나머지 해시를 로컬 비교하니, HIBP 서버는 사용자가 어떤 비밀번호를 조회했는지 알 수 없다. SHA-1을 쓰는 건 저장용 해싱이 아니라 단순 조회 식별용이라 문제되지 않는다(저장은 당연히 bcrypt/argon2로 한다. → [Password_Hashing.md](Password_Hashing.md)).

이 검사는 회원가입과 비밀번호 변경 시점에 거는 게 기본이다. 로그인 시점에 거는 건 외부 API 호출이 로그인 지연으로 들어오니 신중해야 한다. 외부 의존을 로그인 임계 경로에 넣고 싶지 않으면, HIBP 데이터셋을 내려받아 자체 Redis/DB에 적재해두고 로컬 조회하는 방법도 있다.

## 타이밍 공격과 사용자 존재 여부 노출

로그인 응답에서 "존재하지 않는 계정"과 "비밀번호가 틀림"을 구분해서 알려주면, 공격자가 어떤 이메일이 가입돼 있는지 열거(enumeration)할 수 있다. 메시지를 통일하는 건 기본이다.

```javascript
// 나쁜 예 - 계정 존재 여부가 노출됨
if (!user) throw new Error('존재하지 않는 사용자입니다');
if (!validPassword) throw new Error('비밀번호가 틀렸습니다');

// 좋은 예 - 동일 메시지
if (!user || !validPassword) {
  throw new Error('이메일 또는 비밀번호가 올바르지 않습니다');
}
```

메시지만 통일해서는 부족하다. 응답 시간으로도 새어 나간다. 계정이 없으면 비밀번호 해시 비교를 건너뛰니 응답이 빠르고, 계정이 있으면 bcrypt 비교에 수십~수백 ms가 걸려 느리다. 공격자는 이 시간 차이만으로 계정 존재 여부를 알아낸다.

막으려면 계정이 없어도 더미 해시로 비교 연산을 똑같이 수행해서 응답 시간을 맞춘다.

```javascript
const bcrypt = require('bcrypt');

// 서버 시작 시 한 번 만들어두는 더미 해시
const DUMMY_HASH = bcrypt.hashSync('dummy-password-for-timing', 12);

async function verifyLogin(email, password) {
  const user = await userRepo.findByEmail(email);

  // 계정이 없어도 비교 연산을 수행해 시간을 맞춘다
  const hash = user ? user.passwordHash : DUMMY_HASH;
  const passwordOk = await bcrypt.compare(password, hash);

  // 결과 판정은 둘 다 본 다음에 한다
  if (!user || !passwordOk) {
    return null;  // 동일한 실패 처리
  }
  return user;
}
```

`user ? ... : DUMMY_HASH`로 분기해도 두 경로의 bcrypt 비용이 같으니 시간 차가 사라진다. 더미 해시의 cost factor는 실제 해시와 같게 맞춰야 의미가 있다. cost가 다르면 다시 시간 차가 생긴다.

이 방어는 비밀번호 재설정 같은 다른 엔드포인트에도 똑같이 적용해야 한다. "가입된 이메일이면 메일 발송"을 응답이나 시간으로 구분되게 만들면 거기서 열거가 뚫린다. 어느 경로든 "해당 이메일로 안내를 보냈습니다"로 통일한다.

## 감사 로그 설계

로그인 성공/실패를 남기는 건 사고 대응과 이상 탐지의 기본 자료다. 무엇을 남길지가 중요하다.

```javascript
async function logAuthEvent(event) {
  await auditLog.insert({
    timestamp: new Date(),
    event_type: event.type,        // 'login_success' | 'login_failure' | 'account_locked'
    user_id: event.userId || null,
    email_hash: hashEmail(event.email),  // 평문 이메일 대신 해시
    ip: event.ip,
    user_agent: event.userAgent,
    device_id: event.deviceId || null,
    failure_reason: event.reason || null,  // 'invalid_password' | 'account_locked' | 'captcha_failed'
    geo: event.geo || null,        // IP 기반 추정 위치
  });
}
```

몇 가지 원칙이 있다.

비밀번호는 절대 로그에 남기지 않는다. 틀린 비밀번호도 남기면 안 된다. 사용자가 다른 서비스 비밀번호를 실수로 입력하는 경우가 있어서, 실패한 입력값을 로그에 쌓으면 그 자체가 유출 자산이 된다. 디버깅하겠다고 평문 비밀번호를 찍는 코드를 넣지 않는다.

이메일 같은 식별자는 해시나 마스킹을 고려한다. 감사 로그가 장기 보관되고 여러 사람이 접근하니, 평문 PII가 그대로 쌓이면 그것도 관리 부담이 된다. 다만 사고 조사 시 역추적이 필요하면 정책에 맞춰 결정한다.

성공 로그도 남긴다. 실패만 보면 "공격이 결국 성공했는지"를 모른다. 같은 IP에서 수백 번 실패하다가 한 번 성공한 패턴이 보이면 그건 침해 신호다. 실패-실패-성공 시퀀스를 잡으려면 성공 이벤트가 있어야 한다.

이상 패턴은 이 로그를 집계해서 잡는다. 단시간 한 IP에서 다수 계정 실패(스터핑 신호), 한 계정에 다수 IP 실패(분산 무차별 대입 신호), 평소와 다른 지역에서의 성공(계정 탈취 신호) 같은 쿼리를 주기적으로 돌린다. 실시간 차단은 Redis 카운터가 하고, 사후 분석과 패턴 발견은 감사 로그가 한다. 역할이 다르다.

## 방어 계층 정리

로그인 하나를 지키는 데 여러 층이 겹친다. 어느 한 층도 단독으로 완전하지 않아서 같이 둔다.

```
요청 도착
  │
  ├─ 게이트웨이/Nginx: IP 단위 거친 레이트 리밋 (명백한 폭주 차단)
  │
  ├─ 앱: IP 단위 토큰 버킷 (스터핑·스프레이의 분산 시도 억제)
  │
  ├─ 앱: 계정 단위 실패 카운터 (단일 계정 무차별 대입 억제)
  │     └─ 임계값 도달 시 CAPTCHA → 시간 기반 소프트 락
  │
  ├─ 비밀번호 검증: 더미 해시로 타이밍 평탄화, 응답 메시지 통일
  │
  ├─ 유출 비밀번호 탐지: 가입·변경 시점 HIBP 조회
  │
  └─ 감사 로그: 성공·실패 기록 → 사후 이상 탐지
```

핵심은 계정 단위와 IP 단위를 같이 보고, 잠금은 자기유발 DoS를 의식해 시간 기반 소프트 락으로 두며, Redis 카운터의 TTL 누락 같은 운영 함정을 처음부터 막는 것이다. 인증 방식이 무엇이든 로그인 엔드포인트 앞에는 이 계층이 필요하다.

## 참고

- 비밀번호 저장과 해싱: [Password_Hashing.md](Password_Hashing.md)
- 인증 방식 비교: [Authentication_Strategy.md](Authentication_Strategy.md)
- 토큰 보안 심화: [Auth_Strategy_Deep_Dive.md](Auth_Strategy_Deep_Dive.md)
- HIBP Pwned Passwords API: https://haveibeenpwned.com/API/v3#PwnedPasswords
