---
title: Session Management
tags: [security, session, cookie, authentication, redis]
updated: 2026-04-30
---

# 세션 기반 인증

## 세션이라는 개념

HTTP는 stateless다. 매 요청마다 "너 누구냐"를 다시 물어봐야 하는데, 그걸 매번 ID/PW로 검증하면 답이 없다. 그래서 한 번 로그인하면 서버가 "너 식별자는 이거야"라는 표를 발행해주고, 클라이언트는 그 표만 들고 다닌다. 이 표가 세션 ID고, 쿠키에 담긴다.

JWT가 유행하면서 세션이 한물간 기술처럼 취급받는 경우가 있는데, 실무에서는 여전히 세션이 더 적합한 시나리오가 많다. 사내 어드민, 일반 BtoC 웹 서비스, 결제 플로우, 즉시 로그아웃이 필요한 시스템 등은 세션이 정답인 경우가 대부분이다.

세션이 동작하려면 두 가지가 필요하다. 첫째, 서버가 세션 ID를 발급하고 그 ID에 매핑된 사용자 정보를 어딘가에 저장해야 한다. 둘째, 클라이언트는 그 ID를 안전하게 보관하고 매 요청마다 자동으로 보내야 한다. 보통 첫 번째는 Redis나 DB가, 두 번째는 브라우저의 쿠키가 담당한다.

## 세션 ID 생성

세션 ID는 추측 불가능해야 한다. 순차 번호나 사용자 ID 기반으로 만들면 끝장이다. 옆 자리 사람의 세션을 1씩 증가시켜 가로챌 수 있다. 그래서 무작위 바이트를 충분히 길게 뽑아서 base64나 hex로 인코딩하는 게 정석이다.

Node.js 기준으로 `crypto.randomBytes(32)` 정도면 충분하다. 32바이트면 256비트라 brute force는 사실상 불가능하다. Express의 `express-session`도 기본적으로 이 정도 길이를 쓴다. 직접 구현할 때 `Math.random()`이나 타임스탬프 기반으로 만드는 실수를 종종 보는데, 절대 그러면 안 된다.

```javascript
const crypto = require('crypto');

function generateSessionId() {
  return crypto.randomBytes(32).toString('hex');
}
```

세션 ID 자체에 의미가 들어가면 안 된다. 사용자 ID나 권한 정보를 ID에 인코딩하지 말고, 그냥 무작위 토큰으로만 쓰고 실제 데이터는 서버 측 저장소에서 조회해야 한다. 클라이언트가 가진 건 "표"고, 표의 내용은 서버에만 있어야 한다.

## 쿠키 속성

세션 ID를 쿠키에 담아 보낼 때 속성을 잘못 설정하면 모든 보안이 무너진다. 다음 속성들은 거의 필수다.

### Secure

HTTPS에서만 쿠키가 전송되도록 한다. 로컬 개발에서는 빼고, 운영에서는 무조건 켜야 한다. 이걸 안 켜면 HTTP로 보내는 어떤 요청에서든 쿠키가 평문으로 새어나간다. 카페 와이파이에서 패킷 한 번만 캡처하면 끝이다.

### HttpOnly

JavaScript에서 `document.cookie`로 접근하지 못하게 막는다. XSS가 발생해도 세션 쿠키를 훔쳐갈 수 없게 하는 1차 방어선이다. 세션 쿠키는 무조건 켜야 한다. 단, JS에서 읽어야 하는 쿠키(예: CSRF 토큰을 double submit 패턴으로 쓰는 경우)는 별도로 분리해야 한다.

### SameSite

CSRF 방어의 핵심이다. `Strict`, `Lax`, `None` 세 가지 값이 있다.

- `Strict`: 외부 사이트에서 시작된 모든 요청에 쿠키가 안 붙는다. 가장 안전하지만 외부 링크로 들어와도 로그인이 풀려있는 것처럼 보인다.
- `Lax`: top-level 네비게이션(주소창에 입력, 링크 클릭)에는 붙고, 이미지/iframe/AJAX의 cross-site 요청에는 안 붙는다. 대부분의 서비스는 이게 무난하다. 최신 브라우저들은 SameSite를 지정하지 않으면 기본값으로 Lax를 쓴다.
- `None`: cross-site에서 항상 보낸다. 반드시 `Secure`와 같이 써야 한다. iframe 내 결제, 외부 임베드 같은 시나리오 외에는 쓰지 않는 게 좋다.

### Domain

쿠키가 어떤 도메인으로 보내질지 결정한다. `example.com`으로 설정하면 `api.example.com`, `www.example.com` 모두에 보내진다. 너무 넓게 잡으면 서브도메인 중 하나가 뚫렸을 때 전체가 영향을 받는다. 가능하면 정확한 호스트로 한정하는 게 좋다.

서브도메인 간 SSO가 필요한 경우에만 상위 도메인을 쓰고, 그 외에는 host-only 쿠키(Domain 미지정)로 두는 게 안전하다.

### Path

기본은 `/`다. 특정 경로에서만 쿠키가 필요하면 좁힐 수 있지만, 보안 효과는 거의 없다. 같은 도메인의 다른 path에서 XSS가 나면 우회된다. 그냥 `/`로 두고 다른 방어에 집중하는 게 낫다.

### Max-Age vs Expires

세션 쿠키는 보통 `Max-Age`로 절대 시간을 지정하거나, 둘 다 빼서 브라우저 종료 시 사라지게 한다. "30일 자동 로그인" 같은 기능은 별도의 remember-me 토큰으로 분리하는 게 좋다. 세션 쿠키 자체를 30일짜리로 만들면 위험이 너무 크다.

## 실전 설정 예제

```javascript
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const { createClient } = require('redis');

const redisClient = createClient({ url: process.env.REDIS_URL });
redisClient.connect();

app.use(session({
  store: new RedisStore({ client: redisClient, prefix: 'sess:' }),
  secret: process.env.SESSION_SECRET,
  name: 'sid',
  resave: false,
  saveUninitialized: false,
  rolling: true,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax',
    maxAge: 1000 * 60 * 60 * 2,
    domain: '.example.com'
  }
}));
```

`rolling: true`는 요청이 올 때마다 만료 시간을 갱신한다. 사용자가 활동 중이면 세션이 안 끊기는 동작인데, 대부분 서비스에서 자연스럽다. `saveUninitialized: false`는 로그인 안 한 익명 방문자에게 세션을 만들지 않는 옵션이라 Redis 부담을 크게 줄여준다.

`name`을 기본값인 `connect.sid` 그대로 두면 Express 쓴다는 게 노출된다. 적당히 일반적인 이름으로 바꾸는 게 좋다.

## 세션 고정 공격 (Session Fixation)

공격자가 자신이 알고 있는 세션 ID를 피해자에게 심어놓고, 피해자가 로그인하면 그 세션 ID로 같이 들어가는 공격이다. 시나리오는 이렇다.

1. 공격자가 사이트에 접속해 세션 ID `ABC123`을 발급받는다.
2. 피해자에게 `https://victim.com/?sid=ABC123` 같은 링크나, XSS로 쿠키를 심는다.
3. 피해자가 그 세션 ID 상태로 로그인한다.
4. 서버가 같은 세션 ID에 사용자 정보를 매핑한다.
5. 공격자도 `ABC123`으로 로그인된 상태가 된다.

방어는 단순하다. **로그인 성공 시점에 무조건 세션 ID를 새로 발급해야 한다.** 권한이 바뀌는 모든 시점(로그인, 권한 상승, 비밀번호 변경 등)에 세션을 재생성하는 게 원칙이다.

```javascript
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body.email, req.body.password);
  if (!user) return res.status(401).send('Unauthorized');

  req.session.regenerate((err) => {
    if (err) return res.status(500).send('Session error');
    req.session.userId = user.id;
    req.session.save(() => res.redirect('/'));
  });
});
```

`req.session.regenerate()`는 기존 세션을 파기하고 새 ID로 세션을 만든다. 직접 구현한 세션 시스템이라면 `DELETE`로 기존 키를 지우고 새 ID로 다시 `SET`해야 한다.

URL에 세션 ID를 박는 옛날 방식(`?JSESSIONID=...`)은 절대 쓰면 안 된다. 리퍼러로 새고, 로그에 남고, 북마크에 박힌다. 무조건 쿠키로만 전달해야 한다.

## 동시 로그인 제한

서비스 정책에 따라 한 계정에서 동시 접속을 제한해야 할 때가 있다. 게임이나 유료 콘텐츠 서비스에서 자주 보이는 요구사항이다. 두 가지 방식이 있다.

### 방식 1: 새 로그인 시 기존 세션 무효화

새로 로그인하면 그 계정의 다른 모든 세션을 강제 종료한다. Redis에 `user:<userId>:sessions` 같은 Set으로 활성 세션 ID를 추적하고, 로그인할 때 기존 세션들을 다 지운다.

```javascript
async function login(userId, sessionId) {
  const oldSessions = await redis.smembers(`user:${userId}:sessions`);
  if (oldSessions.length > 0) {
    const keys = oldSessions.map(s => `sess:${s}`);
    await redis.del(...keys);
    await redis.del(`user:${userId}:sessions`);
  }
  await redis.sadd(`user:${userId}:sessions`, sessionId);
}
```

### 방식 2: 새 로그인 차단

이미 활성 세션이 있으면 새 로그인을 거부한다. "다른 기기에서 로그아웃 후 다시 시도하세요" 같은 메시지를 보여준다. 하지만 이 방식은 세션이 비정상 종료되면 사용자가 자기 계정에서 갇히는 문제가 있어서, 항상 강제 로그아웃 옵션을 같이 제공해야 한다.

세션을 무효화할 때 Redis 키만 지우면 되는 게 아니라, 사용자가 다음 요청에서 어떤 응답을 받는지 고려해야 한다. 기존 세션 쿠키를 들고 와도 서버에 데이터가 없으니 401을 반환하게 되고, 클라이언트는 로그인 페이지로 리다이렉트시키면 된다.

## Redis 세션 스토어 운영

세션을 메모리에 저장하면 서버 재시작하면 다 날아가고, 여러 인스턴스로 스케일아웃하면 sticky session이 필요해진다. Redis 같은 외부 저장소가 사실상 표준이다.

### 만료 처리

Redis는 키마다 TTL을 설정할 수 있어서, 세션 만료 정리를 따로 안 해도 된다. `EXPIRE` 또는 `SET ... EX`로 TTL을 박아두면 자동으로 사라진다. `connect-redis` 같은 라이브러리는 쿠키의 maxAge에 맞춰 자동으로 TTL을 설정한다.

`rolling` 옵션을 켜면 매 요청마다 TTL이 갱신된다. 활동 기반 만료를 구현할 때 유용하다.

### 메모리 사용량

세션에 큰 데이터를 저장하면 안 된다. userId 하나만 넣고, 나머지 사용자 정보는 필요할 때 DB에서 조회하는 게 원칙이다. 세션에 사용자 프로필 전체를 캐싱하면 권한이 바뀌었을 때 반영이 안 되고, Redis 메모리가 빠르게 차오른다.

DAU 100만짜리 서비스에서 세션마다 1KB만 써도 1GB가 필요하다. 세션 객체는 가볍게 유지해야 한다.

### 고가용성

세션 Redis가 죽으면 모든 사용자가 로그아웃된다. 운영 환경에서는 Redis Sentinel이나 Cluster로 가용성을 확보해야 한다. AWS면 ElastiCache Multi-AZ를 쓰는 게 일반적이다.

세션 저장소를 캐시 Redis와 분리하는 것도 권장한다. 캐시 Redis는 메모리 가득 차면 LRU로 키를 evict하는데, 세션이 evict되면 사용자가 갑자기 로그아웃된다. 정책이 다른 데이터는 인스턴스를 분리해야 한다. 세션 Redis는 `maxmemory-policy noeviction`이나 `volatile-ttl`로 설정해야 한다.

### 장애 시 동작

Redis가 일시적으로 끊어지면 세션 검증이 실패한다. 라이브러리에 따라 동작이 다른데, `connect-redis`는 기본적으로 에러를 던지고 요청이 실패한다. 운영하면서 가장 골치 아픈 부분이라, Redis 연결 모니터링과 알림을 반드시 걸어둬야 한다.

타임아웃을 짧게 잡고 retry는 1~2회로 제한하는 게 좋다. Redis가 느려지면 모든 요청이 그쪽에서 막혀서 서비스 전체가 느려진다.

## 세션 다이어그램

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant R as Redis

    C->>S: POST /login (email, password)
    S->>S: Validate credentials
    S->>R: SET sess:<newId> {userId} EX 7200
    S-->>C: Set-Cookie: sid=<newId>; Secure; HttpOnly; SameSite=Lax

    C->>S: GET /profile (Cookie: sid=<newId>)
    S->>R: GET sess:<newId>
    R-->>S: {userId: 42}
    S-->>C: 200 OK profile data

    C->>S: POST /logout
    S->>R: DEL sess:<newId>
    S-->>C: Set-Cookie: sid=; Max-Age=0
```

## JWT와의 비교

세션과 JWT는 자주 비교되는데, 둘은 본질이 다르다. 세션은 "서버가 진실을 갖고, 클라이언트는 표만 보여준다"는 모델이고, JWT는 "서버가 서명한 데이터를 클라이언트가 들고 다닌다"는 모델이다.

| 항목 | 세션 | JWT |
|------|------|-----|
| 저장 위치 | 서버 (Redis 등) | 클라이언트 |
| 즉시 무효화 | 가능 (DELETE 한 줄) | 어렵다 (블랙리스트 필요) |
| 권한 변경 반영 | 즉시 | 만료까지 대기 |
| 서버 stateless | X | O |
| 페이로드 크기 | 작음 (ID만) | 큼 (서명 + 클레임) |
| 분산 환경 | 스토어 필요 | 자체 검증 |
| 모바일/SPA | 쿠키 처리 번거로움 | 헤더로 간단 |

### 세션이 적합한 경우

- 즉시 로그아웃이 중요한 서비스 (금융, 결제, 어드민)
- 사용자 권한이 자주 바뀌는 시스템
- 동시 로그인 제한이 필요한 경우
- 같은 도메인의 웹앱 (브라우저 쿠키 자동 처리)
- 세션 하이재킹 시 즉시 차단해야 하는 시스템

### JWT가 적합한 경우

- 서버 간 stateless 통신 (마이크로서비스 간 인증)
- 토큰 발급 서버와 검증 서버가 분리된 경우
- 매우 짧은 만료 시간으로 운영 가능한 API
- 모바일 앱에서 쿠키 없이 헤더 인증
- 외부 서비스에 권한 위임 (OAuth access token)

### 하이브리드 패턴

실무에서는 둘을 섞어 쓰는 경우가 많다. 일반적인 패턴은 access token으로 짧은 JWT를 쓰고, refresh token을 세션처럼 서버에 저장해서 무효화 가능하게 만드는 방식이다. 무효화 가능성은 refresh 단계로 옮기고, 일반 API 호출은 stateless로 처리한다.

다만 이 패턴은 복잡도가 올라간다. 단일 도메인 웹앱이라면 그냥 세션 쿠키 하나로 끝내는 게 운영하기 훨씬 편하다. 복잡도와 요구사항을 저울질해서 선택해야 한다.

## 자주 마주치는 문제

### 로컬에서는 되는데 운영에서 쿠키가 안 박힌다

대부분 `Secure: true`인데 HTTP로 접근하거나, `SameSite: None`인데 `Secure`가 빠진 경우다. 브라우저 콘솔에서 Set-Cookie 응답 헤더가 무시되는 메시지를 보면 원인이 나온다.

### 로드밸런서 뒤에서 secure 쿠키가 안 박힌다

LB에서 TLS termination 하고 백엔드에는 HTTP로 연결하는 구성이다. Express라면 `app.set('trust proxy', 1)`로 X-Forwarded-Proto 헤더를 신뢰하게 해야 `secure: true` 쿠키가 정상 발급된다.

### CORS 환경에서 쿠키가 안 보내진다

서버에서 `Access-Control-Allow-Credentials: true`, 클라이언트에서 `fetch(..., { credentials: 'include' })`, 쿠키에 `SameSite: None; Secure`가 모두 맞아야 한다. 하나라도 빠지면 쿠키가 안 붙는다.

### 세션이 가끔씩 끊긴다

Redis 연결 끊김, 메모리 evict, TTL 만료 중 하나다. Redis 로그와 메트릭을 먼저 확인해야 한다. `maxmemory-policy`가 `allkeys-lru`로 되어 있으면 캐시 키와 세션 키가 같이 evict된다.

### 세션 ID가 자꾸 바뀐다

`saveUninitialized: true`로 두면 빈 세션이 매번 만들어졌다 사라진다. 또는 클라이언트에서 쿠키 도메인이 안 맞아서 매 요청마다 새 세션이 생성되는 경우도 있다. 응답 헤더의 Set-Cookie와 요청 헤더의 Cookie를 비교해서 도메인/path가 일치하는지 확인해야 한다.
