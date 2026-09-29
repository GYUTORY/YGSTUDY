---
title: 서버 세션 인증
tags: [auth, security, redis, backend, web-server]
updated: 2026-09-29
---

# 서버 세션 인증

JWT가 대세처럼 보이지만, 세션 기반 인증이 여전히 맞는 상황이 있다. 서버가 상태를 관리하기 때문에 토큰 무효화가 즉각적이고, 클라이언트에 민감한 정보를 노출하지 않는다. 대신 서버가 늘어날수록 세션 공유 문제가 따라온다.

## 세션 저장소: 메모리 vs Redis

### 메모리 세션

Express의 기본 `session()` 미들웨어나 Spring의 `HttpSession`은 별도 설정 없이 프로세스 메모리에 세션을 저장한다. 단일 서버에서는 잘 동작하지만, 배포하는 순간부터 문제가 생긴다.

서버를 2대로 늘리면 로드밸런서가 요청을 분산한다. 사용자가 서버 A에서 로그인했는데 다음 요청이 서버 B로 가면, B는 해당 세션을 모른다. 매번 재로그인을 요구하는 현상이 생긴다.

임시 방편으로 Sticky Session(IP 해싱 또는 쿠키 기반 라우팅)을 쓰는 경우가 있다. 특정 사용자 요청을 항상 같은 서버로 보내는 방식인데, 그 서버가 죽으면 세션이 통째로 날아간다. 블루/그린 배포나 롤링 업데이트를 하면 세션 손실이 반드시 발생한다.

서버를 재시작할 때마다 모든 사용자가 로그아웃되는 것도 운영 현장에서 불만이 많이 나오는 문제다.

### Redis 세션

외부 저장소를 쓰면 이 문제들이 사라진다. 어느 서버가 요청을 받아도 Redis에서 같은 세션 데이터를 읽어온다.

```
로드밸런서
   ├── 서버 A ─┐
   └── 서버 B ─┴── Redis (세션 저장소)
```

`express-session` + `connect-redis` 조합 예시:

```javascript
import session from 'express-session';
import { createClient } from 'redis';
import connectRedis from 'connect-redis';

const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

const RedisStore = connectRedis(session);

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 1000 * 60 * 60 * 24, // 24시간
  },
}));
```

`resave: false`는 세션이 변경되지 않으면 Redis에 재저장하지 않는다. `saveUninitialized: false`는 빈 세션을 저장하지 않는다. 둘 다 켜두면 모든 요청마다 Redis 쓰기가 발생해서 쓸데없는 부하가 생긴다.

Spring Boot에서는 `spring-session-data-redis` 의존성 하나로 `HttpSession`이 자동으로 Redis에 저장된다:

```yaml
spring:
  session:
    store-type: redis
    timeout: 86400s
  data:
    redis:
      host: ${REDIS_HOST}
      port: 6379
```

Redis 장애 시 대응을 미리 정해야 한다. Redis가 죽으면 모든 사용자가 로그아웃된다. Read Replica를 두거나 Redis Sentinel/Cluster를 구성하는 것이 일반적이다. 세션 서버의 가용성 요구사항은 애플리케이션 자체와 동일하다.

## 쿠키 속성

세션 ID는 쿠키로 전달된다. 쿠키 속성 하나가 XSS나 CSRF 공격의 차단 여부를 결정한다.

### HttpOnly

`HttpOnly`가 없으면 JavaScript에서 `document.cookie`로 세션 쿠키를 읽을 수 있다. XSS 취약점이 있는 페이지가 하나라도 있으면 세션 탈취로 이어진다.

반드시 켜야 한다. 예외는 없다.

### Secure

`Secure`가 없으면 HTTP 연결에서도 쿠키가 전송된다. 공용 와이파이에서 평문 HTTP 트래픽을 보면 세션 쿠키가 그대로 보인다.

로컬 개발 환경은 HTTP를 쓰기 때문에 `secure: process.env.NODE_ENV === 'production'`처럼 환경으로 구분한다. 스테이징 환경도 HTTPS를 쓴다면 `production`이 아닌 `development`만 제외하는 방향으로 조건을 작성한다.

### SameSite

CSRF 방어의 핵심이다. 세 가지 값의 동작 차이가 실제 운영에서 문제를 일으킨다.

**Strict**: 모든 크로스 사이트 요청에서 쿠키를 보내지 않는다. 다른 사이트 링크를 클릭해서 들어오는 GET 요청도 포함된다. 외부에서 링크를 타고 들어오면 로그아웃 상태로 보인다. 사용성이 크게 나빠진다.

**Lax**: 크로스 사이트 POST, iframe, img 요청에서는 쿠키를 보내지 않는다. GET 요청은 허용한다. 일반적인 웹사이트에서 권장하는 값이다. 외부 링크 클릭 시 로그인 상태가 유지된다.

**None**: 크로스 사이트 요청에서도 쿠키를 전송한다. `Secure`가 없으면 브라우저가 무시한다. 서드파티 iframe이나 OAuth 리디렉션 플로우처럼 크로스 사이트 요청이 반드시 필요한 경우에 쓴다.

```
일반 웹사이트:    SameSite=Lax  + HttpOnly + Secure
민감한 작업 폼:   SameSite=Strict (별도 쿠키로 분리하는 방식)
OAuth 콜백:      SameSite=None + Secure
```

SameSite가 CSRF를 완전히 막아주지는 않는다. 구형 브라우저는 SameSite를 지원하지 않는다. 금전 거래나 중요한 상태 변경에는 CSRF 토큰을 별도로 검증하는 것이 안전하다.

### 쿠키 속성 조합 정리

| 상황 | HttpOnly | Secure | SameSite |
|------|----------|--------|----------|
| 일반 웹 서비스 | O | O | Lax |
| 내부 관리자 도구 | O | O | Strict |
| 서드파티 연동 필요 | O | O | None |
| 로컬 개발 | O | X | Lax |

## 세션 고정 공격과 세션 ID 재발급

### 공격 원리

세션 고정(Session Fixation) 공격은 공격자가 알고 있는 세션 ID를 피해자가 사용하도록 만드는 방식이다.

```
1. 공격자가 /login 에 접속해서 세션 ID(sid=ABC) 획득
2. 피해자에게 sid=ABC가 포함된 링크를 전달 (URL 파라미터나 쿠키 주입)
3. 피해자가 sid=ABC 상태로 로그인
4. 서버가 로그인 성공 후에도 sid=ABC를 그대로 유지
5. 공격자가 sid=ABC로 피해자 계정에 접근
```

핵심은 로그인 전/후에 같은 세션 ID를 사용한다는 점이다.

### 로그인 후 세션 ID 재발급

로그인 성공 시 세션 ID를 새로 발급하면 공격이 무력화된다. 공격자가 알던 `sid=ABC`는 버려지고, 피해자만 아는 새 세션 ID가 생긴다.

```javascript
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body.username, req.body.password);
  if (!user) return res.status(401).json({ error: 'invalid credentials' });

  // 기존 세션 데이터 보존
  const previousData = { returnUrl: req.session.returnUrl };

  // 세션 ID 재발급 (세션 고정 방어)
  await new Promise((resolve, reject) => {
    req.session.regenerate((err) => err ? reject(err) : resolve());
  });

  // 새 세션에 사용자 정보 저장
  req.session.userId = user.id;
  req.session.returnUrl = previousData.returnUrl;

  res.json({ ok: true });
});
```

Spring Security는 기본적으로 로그인 성공 시 세션을 재생성한다. `session-fixation` 설정을 별도로 건드리지 않았다면 이미 보호되고 있다:

```java
http.sessionManagement(session -> session
    .sessionFixation().changeSessionId() // 기본값
    // .migrateSession() // 이전 속성을 새 세션으로 복사
    // .newSession()     // 완전히 새 세션 (이전 속성 미복사)
    // .none()           // 재발급 안 함 (위험)
);
```

`changeSessionId()`는 서블릿 컨테이너 수준에서 ID만 바꾼다. `migrateSession()`은 새 세션 객체를 만들고 이전 세션 속성을 복사한다. 실제 차이가 있는 경우는 드물지만, 세션 리스너나 특정 필터가 세션 객체 참조를 직접 다루면 `migrateSession()` 쪽이 더 안전하다.

### 로그아웃 처리

로그아웃 시 서버 측 세션을 반드시 삭제해야 한다. 쿠키만 지우면 클라이언트 브라우저에서는 세션이 없어 보이지만, Redis에 세션이 남아 있어서 해당 세션 ID를 아는 공격자는 계속 사용할 수 있다.

```javascript
app.post('/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      console.error('session destroy failed:', err);
      return res.status(500).json({ error: 'logout failed' });
    }
    res.clearCookie('connect.sid'); // 쿠키 이름은 설정에 따라 다름
    res.json({ ok: true });
  });
});
```

## 분산 환경에서의 세션 공유 문제

Redis를 쓴다고 세션 공유가 완전히 해결되지는 않는다. 실제 운영에서 마주치는 문제들이 있다.

### 세션 직렬화

세션에 저장하는 객체가 직렬화/역직렬화 가능해야 한다. JavaScript는 `JSON.stringify`로 처리되는데, Date 객체가 문자열로 복원된다. 역직렬화 후 `session.loginTime instanceof Date`가 false가 되는 현상이 생긴다.

```javascript
// 저장 시
req.session.loginTime = new Date();

// 복원 후 (문제 발생)
console.log(typeof req.session.loginTime); // 'string'
console.log(req.session.loginTime instanceof Date); // false
```

세션에는 `Date` 객체 대신 숫자 타임스탬프를 저장하거나, 사용 시점에 명시적으로 변환한다.

Java에서는 세션에 저장하는 객체가 `Serializable`을 구현해야 한다. 구현하지 않으면 Redis에 저장할 때 예외가 발생한다. 레거시 코드에서 세션에 비직렬화 객체를 넣어두는 경우가 있어서, Spring Session 도입 시 반드시 확인한다.

### 세션 만료와 TTL 일관성

Redis 키에 TTL을 설정하지 않으면 세션이 영원히 남는다. `express-session`은 `maxAge`를 쿠키에 설정하지만, Redis TTL은 `touch` 옵션으로 별도로 관리된다.

```javascript
new RedisStore({
  client: redisClient,
  ttl: 86400, // Redis TTL (초), maxAge와 맞춰야 함
  touchAfter: 3600, // 1시간 이내 재접근은 TTL 갱신 생략
})
```

`touchAfter`를 설정하지 않으면 모든 요청마다 Redis에 TTL 갱신 명령이 간다. 활성 사용자가 많으면 Redis 쓰기 부하가 상당하다.

### 세션 크기

세션에 너무 많은 데이터를 넣는 경우가 있다. 역할 목록, 권한 목록, 사용자 프로필 전체를 저장하면 세션 크기가 수 KB가 된다. 모든 요청마다 이 데이터를 Redis에서 읽어온다.

세션에는 `userId`처럼 최소한의 식별자만 저장하고, 나머지는 요청마다 DB나 캐시에서 조회하는 방식이 관리하기 편하다. 권한 체계가 바뀌었을 때 모든 활성 세션을 무효화하지 않아도 다음 요청부터 바로 적용된다.

### 멀티 테넌트에서의 세션 격리

여러 서비스가 같은 Redis를 공유할 때 세션 키가 충돌하는 경우가 있다. 기본 키 형식이 `sess:세션ID` 인데, 서비스마다 prefix를 다르게 설정한다:

```javascript
new RedisStore({
  client: redisClient,
  prefix: 'myapp:sess:',
})
```

쿠키 이름도 서비스마다 다르게 설정하지 않으면, 같은 도메인에서 서로 다른 서비스가 쿠키를 덮어쓸 수 있다.

```javascript
app.use(session({
  name: 'myapp.sid', // 기본값 'connect.sid' 대신 서비스 고유 이름 사용
  // ...
}));
```
