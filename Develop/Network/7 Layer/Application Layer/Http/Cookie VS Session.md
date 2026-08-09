---
title: Cookie VS Session
tags: [network, http]
updated: 2026-07-11
---

# Cookie VS Session

## 배경

HTTP는 Stateless 프로토콜이다. 서버는 이전 요청을 기억하지 않는다. 로그인 후 다음 요청에서도 서버가 "이 사람이 로그인했다"는 사실을 알려면 별도의 상태 저장 수단이 필요하다. 쿠키와 세션이 그 수단이다.

---

## 쿠키(Cookie)

### 정의

서버가 HTTP 응답의 `Set-Cookie` 헤더로 클라이언트에 저장시키는 작은 데이터 파일이다. 이후 브라우저는 동일 도메인에 요청할 때마다 `Cookie` 헤더에 이 값을 자동으로 포함한다. 데이터가 클라이언트 측에 저장된다는 것이 세션과 핵심적인 차이다.

### 쿠키의 종류

세션 쿠키는 `Max-Age`나 `Expires` 속성이 없어 브라우저를 닫으면 삭제된다. 영구 쿠키는 만료일이 지정되어 디스크에 저장된다. 보안 쿠키는 `Secure` 플래그를 붙여 HTTPS 연결에서만 전송된다. 실무에서는 이 세 가지를 조합해 쓰는 경우가 많다. 세션 ID는 세션 쿠키로, 자동 로그인 토큰은 영구 쿠키 + `Secure`로 관리한다.

### 쿠키의 특징

쿠키는 이름, 값, 만료일, 경로 정보로 구성된다. 브라우저 기준으로 도메인당 20개, 총 300개, 개당 4KB 제한이 있다. 용량 제한이 작기 때문에 민감하지 않은 경량 데이터를 저장하는 데 적합하다. 브라우저가 자동으로 전송하기 때문에, 저장하는 데이터가 많아질수록 매 요청마다 불필요한 네트워크 트래픽이 증가한다.

### 쿠키 동작 과정

첫 방문 시 서버가 응답 헤더에 `Set-Cookie`를 포함해 쿠키를 내려준다. 이후 브라우저는 해당 도메인으로 요청할 때마다 `Cookie` 헤더에 저장된 값을 자동으로 실어 보낸다.

```http
# 첫 로그인 응답
HTTP/1.1 200 OK
Set-Cookie: sessionId=abc123; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=3600
Set-Cookie: theme=dark; Path=/; Max-Age=2592000

# 이후 요청
GET /dashboard HTTP/1.1
Host: example.com
Cookie: sessionId=abc123; theme=dark
```

`theme` 쿠키는 영구 쿠키로 30일 유지되고, `sessionId`는 1시간 후 만료되는 보안 쿠키다.

### 쿠키 보안 위험 및 대응

XSS 공격에서는 악성 스크립트가 `document.cookie`로 쿠키를 탈취한다. `HttpOnly` 플래그를 설정하면 JavaScript에서 쿠키에 접근할 수 없어 이 공격을 차단한다.

CSRF 공격은 사용자 모르게 다른 사이트에서 쿠키를 이용한 요청을 위조한다. `SameSite=Strict`로 설정하면 외부 사이트에서 발생한 요청에는 쿠키가 포함되지 않는다. 단, `Strict`는 외부 링크를 통한 접근에도 쿠키를 보내지 않아 사용자 경험에 영향을 줄 수 있다. 이 경우 `SameSite=Lax`가 타협점이 된다.

네트워크 스니핑은 패킷을 가로채 쿠키를 탈취한다. `Secure` 플래그로 HTTPS 연결에서만 쿠키를 전송하도록 강제한다.

---

## 세션(Session)

### 정의

사용자 상태 정보를 서버 측에 저장하는 방식이다. 서버는 클라이언트별로 고유한 Session ID를 발급하고, 이 ID를 쿠키로 클라이언트에 내려준다. 이후 클라이언트는 Session ID만 서버에 전달하고, 서버는 이를 키로 저장소에서 사용자 정보를 조회한다.

### 세션의 특징

데이터는 서버에 있으므로 클라이언트에서 위변조할 수 없다. 저장 용량은 서버 용량 범위 내에서 제한이 없다. 서버 메모리나 Redis 같은 외부 저장소를 사용하기 때문에, 동시 접속자가 많아지면 저장소 부하가 증가한다.

서버를 수평 확장할 때 세션 공유 문제가 생긴다. 특정 서버에만 세션이 있으면 로드 밸런서가 다른 서버로 요청을 보낼 때 세션을 찾지 못한다. Redis 같은 중앙 세션 저장소를 두거나, Sticky Session을 사용해야 한다.

### 세션 동작 과정

```http
# 최초 로그인 요청
POST /login HTTP/1.1
Host: example.com
Content-Type: application/json

{"username": "user1", "password": "pass"}

# 서버 응답 — 세션 ID를 쿠키로 전달
HTTP/1.1 200 OK
Set-Cookie: JSESSIONID=XYZ789; Path=/; HttpOnly; Secure; SameSite=Strict

# 이후 인증 요청 — 브라우저가 쿠키 자동 전송
GET /api/profile HTTP/1.1
Host: example.com
Cookie: JSESSIONID=XYZ789

# 서버: Redis에서 XYZ789 키로 사용자 정보 조회 후 응답
HTTP/1.1 200 OK
Content-Type: application/json

{"userId": 42, "username": "user1"}
```

서버는 `JSESSIONID=XYZ789`를 받아 Redis에서 해당 키의 데이터를 조회한다. 세션이 없거나 만료됐으면 401을 반환한다.

### 세션 저장 방식

메모리 기반 세션은 별도 설정 없이 사용할 수 있고 속도가 빠르지만, 서버 재시작 시 모든 세션이 날아간다. 개발 환경에서는 괜찮지만 운영 환경에서는 쓰지 않는다. 파일 기반 세션은 재시작 후에도 세션이 유지되지만 I/O가 느리고 서버 확장 시 공유 파일 시스템이 필요해진다. 데이터베이스 기반 세션은 안정적이지만 쿼리 오버헤드가 있다. 현재는 대부분 Redis를 사용한다. 메모리 기반으로 빠르고, 클러스터를 구성하면 수평 확장도 된다.

### 세션 보안 및 관리

세션 하이재킹은 유효한 Session ID를 탈취해 피해자로 위장하는 공격이다. HTTPS를 강제하고, Session ID를 충분히 길고 무작위로 생성해야 한다. 일정 시간 요청이 없으면 세션을 만료시키는 타임아웃 설정도 필수다.

세션 고정 공격은 공격자가 미리 만든 Session ID를 피해자에게 사용하게 만든 뒤, 피해자가 로그인하면 그 세션을 탈취하는 방식이다. 로그인 성공 시 반드시 새 Session ID를 발급해야 이 공격을 막는다.

---

## 쿠키와 세션의 차이점

| 구분 | 쿠키 | 세션 |
|------|------|------|
| 저장 위치 | 클라이언트 측 | 서버 측 |
| 보안 | 클라이언트에 저장되어 변조 가능 | 서버에 저장되어 상대적으로 안전 |
| 용량 제한 | 도메인당 20개, 총 300개, 개당 4KB | 서버 용량에 따라 제한 없음 |
| 라이프사이클 | 만료 기간 설정 가능 | 브라우저 종료 또는 서버에서 삭제 시 종료 |
| 서버 자원 | 서버 자원 사용하지 않음 | 서버 메모리 사용 |

---

## Q&A: 세션이 더 안전한데 왜 쿠키를 사용할까?

세션은 서버 메모리를 소비한다. 동시 접속자가 수만 명이면 세션 데이터 저장소가 그만큼의 부하를 받는다. 쿠키는 데이터를 클라이언트에 두므로 서버 자원이 필요 없다. 사용자 선호도(테마, 언어 설정 등)는 탈취당해도 피해가 크지 않고, 서버 요청마다 조회할 필요도 없다. 이런 데이터는 쿠키에 저장하는 편이 낫다. 수평 확장 시에도 세션은 공유 저장소가 필요하지만 쿠키는 클라이언트가 관리하니 서버 측 고려사항이 없다.

---

## 코드 예제

### Set-Cookie 헤더

```http
HTTP/1.1 200 OK
Set-Cookie: sessionId=abc123; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=3600
Set-Cookie: theme=dark; Path=/; Max-Age=2592000
```

#### 쿠키 속성 설명

| 속성 | 설명 |
|------|------|
| `HttpOnly` | JavaScript에서 접근 불가 (XSS 방어) |
| `Secure` | HTTPS에서만 전송 |
| `SameSite=Strict` | 동일 사이트 요청에만 전송 (CSRF 방어) |
| `SameSite=Lax` | 안전한 교차 사이트 GET 요청 허용 |
| `Max-Age=3600` | 1시간 후 만료 (초 단위) |
| `Path=/` | 모든 경로에서 전송 |

### Express.js 쿠키 & 세션 설정

```javascript
const express = require('express');
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const { createClient } = require('redis');

const app = express();

const redisClient = createClient({ url: 'redis://localhost:6379' });
redisClient.connect();

app.use(session({
    store: new RedisStore({ client: redisClient }),
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 60 * 60 * 1000  // 1시간
    }
}));

// 로그인 — regenerate로 새 Session ID 발급 (세션 고정 공격 방어)
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await authenticate(username, password);

    if (!user) return res.status(401).json({ error: 'Unauthorized' });

    req.session.regenerate((err) => {
        if (err) return res.status(500).json({ error: 'Session error' });

        req.session.userId = user.id;
        req.session.role = user.role;
        // 로그인 시점 User-Agent 저장 — 하이재킹 탐지용
        req.session.userAgent = req.headers['user-agent'];
        res.json({ message: 'Logged in' });
    });
});

// 인증 미들웨어 — User-Agent 불일치 시 세션 무효화 (하이재킹 탐지)
function requireAuth(req, res, next) {
    if (!req.session.userId) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    if (req.session.userAgent && req.session.userAgent !== req.headers['user-agent']) {
        req.session.destroy();
        return res.status(401).json({ error: 'Session invalidated' });
    }
    next();
}

// 로그아웃 — 세션 완전 삭제
app.post('/logout', (req, res) => {
    req.session.destroy((err) => {
        res.clearCookie('connect.sid');
        res.json({ message: 'Logged out' });
    });
});

// 영구 쿠키 설정 (사용자 선호도)
app.post('/preferences', (req, res) => {
    res.cookie('theme', req.body.theme, {
        maxAge: 30 * 24 * 60 * 60 * 1000,  // 30일
        httpOnly: false,  // 클라이언트 JS에서 읽을 수 있도록
        sameSite: 'lax'
    });
    res.json({ message: 'Preference saved' });
});
```

### Spring Boot 세션 설정

```yaml
# application.yml
spring:
  session:
    store-type: redis
    timeout: 3600
  data:
    redis:
      host: localhost
      port: 6379
  security:
    session:
      creation-policy: if_required
```

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
                .sessionFixation(fixation -> fixation.newSession()) // 세션 고정 공격 방어
                .maximumSessions(1)
                .maxSessionsPreventsLogin(false) // 새 로그인 시 기존 세션 만료
            )
            .csrf(csrf -> csrf.csrfTokenRepository(
                CookieCsrfTokenRepository.withHttpOnlyFalse()
            ));

        return http.build();
    }
}

@PostMapping("/login")
public ResponseEntity<?> login(@RequestBody LoginRequest req, HttpSession session) {
    User user = authService.authenticate(req.getUsername(), req.getPassword());
    session.setAttribute("userId", user.getId());
    session.setMaxInactiveInterval(3600);  // 1시간
    return ResponseEntity.ok(new LoginResponse(user));
}
```

### JWT vs Session 비교

```javascript
// ── 세션 기반 인증 흐름 ──────────────────────────────
// 1. 클라이언트: POST /login {username, password}
// 2. 서버: 세션 생성 → sessionId를 쿠키에 설정
// 3. 클라이언트: 이후 요청마다 쿠키 자동 전송
// 4. 서버: Redis에서 sessionId로 사용자 정보 조회

// ── JWT 기반 인증 흐름 ──────────────────────────────
const jwt = require('jsonwebtoken');

app.post('/login', async (req, res) => {
    const user = await authenticate(req.body);
    const token = jwt.sign(
        { userId: user.id, role: user.role },
        process.env.JWT_SECRET,
        { expiresIn: '1h' }
    );
    // JWT를 HttpOnly 쿠키에 저장 (XSS 방어)
    res.cookie('token', token, { httpOnly: true, secure: true });
    res.json({ message: 'Logged in' });
});

app.get('/api/me', (req, res) => {
    const token = req.cookies.token;
    try {
        const payload = jwt.verify(token, process.env.JWT_SECRET);
        res.json({ userId: payload.userId });
    } catch (e) {
        res.status(401).json({ error: 'Unauthorized' });
    }
});
```

| 항목 | 세션 | JWT |
|------|------|-----|
| 저장 위치 | 서버 (Redis 등) | 클라이언트 (쿠키/헤더) |
| 서버 자원 | 사용 | 미사용 |
| 즉시 무효화 | 가능 (세션 삭제) | 어려움 (만료 대기) |
| 확장성 | 공유 저장소 필요 | 무상태 — 확장 용이 |
| 정보 크기 | 제한 없음 | 최소화 권장 (Base64 인코딩) |

JWT의 "즉시 무효화 어려움" 문제를 우회하려고 JWT를 HttpOnly 쿠키에 저장하는 하이브리드 패턴을 쓰는 경우가 있다. JWT를 쿠키에 넣으면 XSS로 탈취되는 문제는 줄어들지만, CSRF에는 여전히 취약하다. `SameSite=Strict`로 어느 정도 방어할 수 있지만, 크로스 도메인 API를 써야 하는 구조라면 `SameSite=None; Secure`를 써야 하고 그러면 CSRF 방어가 약해진다.

토큰 무효화 문제도 그대로다. 로그아웃 시 서버에서 토큰을 폐기할 방법이 없으므로, Redis에 블랙리스트를 두거나 짧은 만료 시간(15분~1시간)으로 설정하고 Refresh Token으로 갱신하는 구조가 필요하다. Refresh Token을 별도로 관리해야 하는 시점에서, 단순 세션 방식 대비 복잡도가 크게 높아진다.

---

## 참고 자료
- [슬기로운 개발생활:티스토리](https://dev-coco.tistory.com/61#recentComments)
- [code-lab1.tistory.com](https://code-lab1.tistory.com/298)
- [MDN Web Docs - HTTP Cookies](https://developer.mozilla.org/ko/docs/Web/HTTP/Cookies)
