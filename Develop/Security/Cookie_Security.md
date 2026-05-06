---
title: Cookie Security
tags: [security, cookie, samesite, chips, browser, web]
updated: 2026-05-06
---

# 쿠키 보안

## 왜 쿠키 속성이 따로 정리될 가치가 있는가

세션이나 토큰을 쿠키에 담는 이야기는 이미 `Session_Management`에서 다뤘다. 이 문서는 쿠키라는 매커니즘 자체의 속성을 다룬다. 같은 세션 ID를 담더라도 어떤 속성을 붙이느냐에 따라 보안 등급이 달라진다. 그리고 2024~2025년을 거치면서 쿠키를 둘러싼 환경이 크게 흔들렸다. Chrome이 서드파티 쿠키 차단을 미루고 다시 살리는 과정을 반복했고, Safari/Firefox는 이미 ITP/ETP로 차단을 끝낸 상태다. 그 와중에 CHIPS(Partitioned 쿠키)라는 새 모델이 도입됐다. 결과적으로 "예전에 동작하던 쿠키 코드가 이제는 안 동작한다"는 신고가 운영팀에 자주 올라온다.

쿠키 속성을 한 줄씩 정확히 알아야 디버깅이 가능하다. "왜 Chrome에서는 쿠키가 안 붙냐"는 질문을 받았을 때 SameSite, Secure, Partitioned, prefix 중 어디에 걸렸는지 5초 안에 짚을 수 있어야 한다.

## 쿠키 속성 전체 목록

브라우저가 쿠키를 저장하고 보낼 때 참조하는 속성은 다음과 같다.

| 속성 | 역할 | 빠뜨리면 생기는 일 |
|---|---|---|
| `Secure` | HTTPS에서만 전송 | HTTP 요청에 평문 노출 |
| `HttpOnly` | JS에서 접근 차단 | XSS로 쿠키 탈취 가능 |
| `SameSite` | cross-site 요청 첨부 제어 | CSRF, cross-site 트래킹 노출 |
| `Domain` | 어떤 호스트로 보낼지 | 의도하지 않은 서브도메인 누출 |
| `Path` | 어떤 경로로 보낼지 | 거의 영향 없음, 보안 경계로 쓰지 말 것 |
| `Expires` / `Max-Age` | 수명 | 영구 토큰화, 잔존 위험 |
| `Partitioned` | top-level 사이트별로 격리 | iframe 임베드 시 차단됨 |
| 이름 prefix | 속성 강제 (`__Secure-`, `__Host-`) | 자체적으로는 보호 안 됨 |

각각 하나씩 본다.

## Secure

HTTPS 연결에서만 쿠키를 보낸다. HTTP 요청에는 절대 첨부되지 않는다. 운영에서는 무조건 켜야 한다는 건 누구나 안다. 헷갈리는 건 두 가지다.

첫째, `localhost`는 예외다. Chrome과 Firefox는 `localhost`에 한해 Secure가 없어도 쿠키를 받아주지만, IP 주소(예: `127.0.0.1`)나 다른 호스트명에서는 차단한다. 사내 개발 도메인이 IP 기반이면 Secure 없이는 쿠키가 안 붙어 디버깅이 꼬인다.

둘째, Chrome은 2024년부터 비-secure 컨텍스트에서 새 쿠키 설정 자체를 막는 방향으로 움직이고 있다. mixed content 환경에서 갑자기 로그인이 안 풀리는 사례가 늘었다.

## HttpOnly

`document.cookie`로 접근할 수 없게 만든다. XSS가 한 번이라도 터지면 세션 쿠키 같은 민감한 토큰을 탈취당하지 않게 막는 1차 방어다. 세션 쿠키, 인증 토큰 쿠키는 무조건 HttpOnly여야 한다.

CSRF 방어를 위해 double-submit 패턴으로 토큰을 쿠키에 심는 경우가 있다. 이때는 JS가 읽어야 하므로 HttpOnly를 끈다. 즉 쿠키마다 역할이 다르다는 점을 인지하고 분리해야 한다. 같은 쿠키 하나에 세션 ID와 CSRF 토큰을 같이 담는 설계는 잘못된 설계다.

HttpOnly가 있어도 XSS가 만능 방어는 아니다. 공격자는 세션 쿠키를 직접 못 읽어도, 같은 origin의 권한으로 요청을 대신 보낼 수 있다. 그래서 XSS 자체를 막는 게 본질이고, HttpOnly는 보조다.

## SameSite

브라우저 보안 정책에서 가장 자주 바뀐 영역이다. 값은 셋이다.

### Strict

이 사이트에서 시작된 요청에만 쿠키를 보낸다. 외부 링크를 클릭해 들어오면 로그인이 풀린 것처럼 보인다. 사용자 경험이 거칠지만, 결제·관리자 페이지처럼 외부에서 들어와 그대로 액션이 실행되면 안 되는 곳에 쓴다. 일부 은행 사이트는 모든 쿠키를 Strict로 두고, 외부 진입 시 다시 로그인 시킨다.

### Lax

top-level GET 네비게이션(주소창 입력, 링크 클릭)에는 쿠키를 붙이고, iframe·image·cross-site fetch에는 붙이지 않는다. 일반 웹 서비스는 보통 Lax가 합리적인 기본값이다. Chrome은 SameSite 미지정 쿠키를 Lax로 간주한다(Lax-by-default). Safari는 명시적 표기를 권장하지만 동작은 비슷하다.

Lax는 "GET이면서 top-level 이동"일 때만 첨부된다는 점을 정확히 기억해야 한다. 외부에서 POST 폼을 우리 사이트로 보내면 쿠키가 안 붙는다. 이게 CSRF 방어 효과의 본질이다.

### None

cross-site 요청에도 쿠키를 보낸다. 외부 사이트에 임베드된 iframe, 외부 도메인에서 호출하는 API에서 인증을 유지하려면 None이 필요하다. None을 쓰려면 반드시 Secure를 같이 켜야 한다. Chrome/Firefox/Safari 모두 `SameSite=None; Secure` 쌍이 아니면 쿠키를 거부한다.

문제는 Lax-by-default가 도입된 후, SameSite를 지정하지 않으면 모든 cross-site 요청이 Lax 취급을 받는다는 점이다. 옛날 코드를 그대로 두면 어느 날 갑자기 외부 임베드 위젯, 결제 PG 콜백에서 쿠키가 안 붙기 시작한다. 개편 없이 운영해 온 레거시 시스템에서 자주 터진다.

### 브라우저별 차이

같은 SameSite=Lax라도 브라우저가 다르게 다룬다.

- **Chrome**: Lax-by-default. SameSite 미지정 쿠키도 Lax로 처리. 단, "Lax+POST" 임시 완화 정책이 있어, 새로 발급되고 2분 이내인 쿠키는 cross-site POST top-level 네비게이션에서도 첨부된다. 이게 OAuth 콜백 등이 그럭저럭 돌아간 이유다.
- **Firefox**: 비슷하게 Lax-by-default. ETP(Enhanced Tracking Protection)에서 알려진 트래커는 추가로 차단.
- **Safari**: 2020년부터 ITP로 모든 서드파티 쿠키 차단. SameSite 값과 무관하게 cross-site iframe 안에서는 쿠키가 안 붙는다고 봐야 한다. CHIPS(Partitioned)는 2024년부터 부분 지원.

같은 코드인데 Safari에서만 로그인이 풀리는 사례는 거의 ITP 때문이다. SameSite=None을 줘도 소용 없고, CHIPS로 가거나 first-party 컨텍스트로 옮기는 수밖에 없다.

## Domain과 Path

`Domain` 속성은 쿠키가 어떤 호스트로 전송될지 결정한다. 생략하면 쿠키를 발급한 호스트에만 한정된다. `Domain=example.com`으로 주면 모든 서브도메인(api.example.com, admin.example.com, anything.example.com)에 전송된다.

여기서 실수가 자주 난다. 운영팀이 `Domain=.example.com`을 넓게 잡으면 그 도메인의 어떤 서브도메인이든 쿠키를 읽고 쓴다. 만약 `static.example.com`이 외부 CDN이고 거기서 XSS가 나면 메인 서비스 쿠키도 같이 노출된다. Domain은 가능한 한 좁게, 발급 호스트로 한정하는 게 안전하다.

또 한 가지, `Domain` 속성이 있는 쿠키와 없는 쿠키는 같은 이름이라도 다른 쿠키로 취급된다. 옛날에 `Domain=.example.com`으로 발급된 쿠키와 새로 `Domain` 없이 발급한 쿠키가 같은 이름이면 두 개가 동시에 남아 브라우저가 둘 다 보낸다. 서버는 어느 쪽이 진짜인지 모른다. 마이그레이션 중 이 문제를 자주 본다.

`Path`는 보안 경계로 절대 쓰면 안 된다. 같은 origin이면 JS로 어느 path든 쿠키를 읽고 쓸 수 있는 우회가 가능하다. Path는 "어떤 요청에 첨부할지" 최적화 용도일 뿐이다.

## __Host- / __Secure- prefix

쿠키 이름 자체에 prefix를 붙이면 브라우저가 속성을 강제한다.

### __Secure-

`__Secure-`로 시작하는 쿠키는 반드시 `Secure` 속성이 있어야 하고, HTTPS에서 발급돼야 브라우저가 받아준다. 빠뜨리면 set 자체가 거부된다.

### __Host-

훨씬 강력하다. `__Host-`로 시작하는 쿠키는

- `Secure` 필수
- HTTPS에서 발급
- `Domain` 속성 금지 (즉 발급한 정확한 호스트에만 매칭)
- `Path=/` 필수

이걸 강제하면 서브도메인 누출이 원천 차단된다. 인증 쿠키처럼 절대 다른 호스트로 새면 안 되는 쿠키는 `__Host-` prefix를 붙이는 게 정석이다. OAuth state 쿠키, CSRF 토큰 쿠키, 세션 쿠키 모두 이 prefix를 검토할 가치가 있다.

prefix는 그냥 이름 규칙이라 서버가 모르면 동작하지 않는다. 서버 코드에서 쿠키 이름을 `__Host-session`으로 set 하면 끝이다. 클라이언트는 `__Host-` 접두어가 붙은 그대로 받고, 추후 매번 그 이름으로 보낸다.

```javascript
// Express 예시
res.cookie('__Host-session', sessionId, {
  httpOnly: true,
  secure: true,
  sameSite: 'lax',
  path: '/',
  // domain은 절대 지정하지 않는다 — __Host-는 Domain이 없어야 함
});
```

`Domain`을 함께 줘버리면 브라우저가 쿠키 set을 거부한다. 서버 로그에는 "쿠키 잘 줬다"고 나오는데 클라이언트에는 안 박히는 현상이 발생한다.

## 수명: Expires / Max-Age

`Expires`는 만료 시각, `Max-Age`는 발급 시점부터의 초 단위 수명이다. 둘 다 없으면 세션 쿠키(브라우저 종료 시 삭제)다.

세션 쿠키라고 안전한 건 아니다. 모던 브라우저들은 "세션 복원" 기능 때문에 브라우저를 닫아도 쿠키를 보존하기도 한다. Chrome의 "Continue where you left off" 옵션이 켜져 있으면 세션 쿠키가 며칠씩 살아남는다. 보안상 만료가 필요한 토큰이라면 명시적으로 `Max-Age`를 짧게 박아야 한다.

긴 세션을 원하면 짧은 access 쿠키 + 긴 refresh 쿠키 패턴이 일반적이다. 단일 쿠키에 1년짜리 만료를 박는 건 잔존 위험이 너무 크다.

## Partitioned (CHIPS)

CHIPS = Cookies Having Independent Partitioned State. 2024년부터 Chrome이 도입했고, Edge·Firefox(부분)·Safari(부분)도 지원에 합류했다.

기존 cross-site 쿠키는 임베드된 위치와 무관하게 같은 쿠키 jar를 공유했다. 광고 트래커가 여러 사이트를 가로질러 사용자를 추적할 수 있던 이유다. CHIPS는 이걸 깬다. `Partitioned` 속성이 붙은 쿠키는 top-level 사이트(임베드된 페이지의 주소창 도메인)별로 별개 jar에 저장된다.

예시. `widget.example.com`이 `siteA.com`과 `siteB.com`에 모두 iframe으로 임베드된다고 하자. CHIPS 이전에는 widget이 어디 임베드돼 있건 같은 쿠키를 봤다. CHIPS 이후에는 siteA에서 iframe이 발급한 쿠키와 siteB에서 발급한 쿠키가 완전히 분리된다. siteA로 다시 들어가면 siteA용 쿠키만 보이고, siteB용은 절대 안 보인다.

```
Set-Cookie: __Host-widget=abc123;
            Secure;
            HttpOnly;
            SameSite=None;
            Path=/;
            Partitioned
```

`Partitioned`를 쓰려면 `SameSite=None; Secure`를 함께 줘야 한다. `__Host-` prefix와 결합하는 게 일반적인 패턴이다.

CHIPS가 도입된 직접적인 이유: 서드파티 쿠키가 차단되는 환경에서도 결제 위젯, 채팅 임베드, SSO 위젯처럼 "이 사이트 안에서만 상태를 유지하면 되는" 합법적 cross-site 사용 사례를 지원하기 위해서다. 추적 목적의 cross-site 공유는 못 하게 막으면서, 사이트 내부 임베드의 상태 유지는 허용한다.

서드파티 쿠키에 의존하던 위젯이 CHIPS 없이는 동작 안 하는 케이스가 늘고 있다. 임베드 환경에서 로그인 상태가 안 풀리는 이슈를 보면 거의 이쪽이다.

## Cross-site cookie blocking 현황

서드파티 쿠키 deprecation 흐름을 정리하면 이렇다.

- **Safari (ITP)**: 2017년 시작. 2020년부터 모든 서드파티 쿠키 완전 차단. 회피 우회도 단계적으로 막아왔다.
- **Firefox (ETP)**: 2019년부터 알려진 트래커 차단. 2021년 Total Cookie Protection으로 cross-site 쿠키를 사이트별 jar에 격리(CHIPS와 유사한 개념을 먼저 구현).
- **Chrome**: 2024년 1월 1% 사용자 대상 시작 → 2024년 7월 전면 시행 발표 → 2024년 7월 보류 결정 → 2025년 사용자 선택 모델로 전환. 결국 강제 차단 대신 사용자가 선택하도록 바뀌었다.

"Chrome이 안 막았다"고 안심하면 안 된다. Safari·Firefox 사용자, 그리고 Chrome에서 차단을 켠 사용자는 이미 서드파티 쿠키가 안 동작한다. 글로벌 서비스라면 사실상 못 쓰는 환경이라고 봐야 한다.

대안으로 권장되는 것들:

- **first-party 컨텍스트로 이전**: 서비스의 핵심 인증을 같은 eTLD+1에 둔다. CDN이나 위젯도 가능하면 자체 도메인 서브로 호스팅한다.
- **CHIPS(Partitioned)**: 임베드된 위젯이 사이트별 상태만 유지하면 충분한 경우.
- **Storage Access API**: iframe이 사용자 액션 직후 명시적으로 first-party storage 접근을 요청. Safari·Firefox·Chrome 모두 지원.
- **FedCM**: 연합 로그인을 브라우저 네이티브 API로. SSO 시나리오에서 서드파티 쿠키 의존 제거.

## Express 설정

Node.js + Express 기준. `cookie-parser`나 `express-session`을 쓴다.

```javascript
const express = require('express');
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const { createClient } = require('redis');

const redisClient = createClient({ url: process.env.REDIS_URL });
redisClient.connect();

const app = express();

app.set('trust proxy', 1); // ALB/Nginx 뒤라면 필수

app.use(session({
  store: new RedisStore({ client: redisClient }),
  name: '__Host-sid',
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 1000 * 60 * 60 * 2, // 2시간
    // domain 지정 금지 (__Host- prefix 때문)
  },
}));
```

`trust proxy`를 빠뜨리면 ALB/Nginx 뒤에서 `secure: true`가 동작 안 한다. Express가 클라이언트 IP를 프록시 IP로 보고 HTTPS인지 판단을 못 한다. 운영에 올린 직후 "secure cookie을 안 보낸다"는 신고가 오면 거의 이거다.

cross-site 임베드 위젯이라면:

```javascript
res.cookie('__Host-widget', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'none',
  path: '/',
  partitioned: true, // Express 4.21+ / Node cookie 라이브러리 0.7+
});
```

오래된 `cookie` 라이브러리는 `partitioned` 옵션을 모른다. 직접 `Set-Cookie` 헤더에 `Partitioned`를 붙이거나 라이브러리를 올려야 한다.

## Spring Boot 설정

Spring Session + Redis 기준. `application.yml`에서:

```yaml
server:
  servlet:
    session:
      cookie:
        name: __Host-SID
        http-only: true
        secure: true
        same-site: lax
        path: /
        max-age: 7200
        # domain은 비워둔다
```

코드로 직접 쿠키를 세팅할 때:

```java
ResponseCookie cookie = ResponseCookie.from("__Host-csrf", token)
    .httpOnly(false)
    .secure(true)
    .sameSite("Lax")
    .path("/")
    .maxAge(Duration.ofHours(2))
    .build();

response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());
```

`ResponseCookie`는 Spring 5부터 권장 API다. `Cookie` 클래스 직접 쓰는 옛날 방식은 SameSite를 지원하지 않아 헤더에 직접 박아야 했다.

Partitioned가 필요하면 Spring Boot 3.4 이상 또는 Tomcat 11에서 지원이 추가됐다. 그 이전 버전이라면 헤더에 직접 추가한다.

```java
String header = String.format(
    "%s=%s; Path=/; HttpOnly; Secure; SameSite=None; Partitioned",
    name, value
);
response.addHeader("Set-Cookie", header);
```

리버스 프록시(Nginx, ALB) 뒤일 때 `server.forward-headers-strategy: native` 또는 `framework`를 켜야 `secure`가 정확히 판정된다. Express의 `trust proxy`와 같은 맥락이다.

## Next.js 설정

App Router 기준. `cookies()` API로 쿠키를 읽고 쓴다.

```typescript
// app/api/login/route.ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const sessionId = await createSession(/* ... */);

  const cookieStore = await cookies();
  cookieStore.set('__Host-session', sessionId, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 2,
  });

  return NextResponse.json({ ok: true });
}
```

Next.js 15부터 `cookies()`가 비동기로 바뀌어 `await`가 필요하다. 14 이전 코드를 마이그레이션할 때 빠뜨리면 빌드가 깨진다.

middleware에서 인증 쿠키를 검사하는 패턴이 일반적이다.

```typescript
// middleware.ts
import { NextResponse, type NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
  const sid = req.cookies.get('__Host-session')?.value;

  if (!sid && req.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*'],
};
```

Vercel 배포 환경은 자동으로 HTTPS이므로 `secure: true`가 항상 만족된다. 로컬 개발에서 `secure: true`를 켠 채로 테스트하면 쿠키가 안 박힌다. 환경 변수로 분기하는 게 일반적이다.

```typescript
secure: process.env.NODE_ENV === 'production',
```

Server Action에서 cross-site fetch를 받아야 하면 SameSite=None을 검토한다. 다만 Next.js Server Action은 기본적으로 same-origin이 강제되므로, 진짜 cross-site 시나리오인지 다시 확인하는 게 좋다.

## 자주 부딪히는 문제

### Chrome에서만 쿠키가 사라지는 경우

대부분 SameSite 미지정 → Lax-by-default 적용으로 cross-site 요청에 쿠키가 안 붙는 케이스다. 명시적으로 `SameSite=None; Secure`로 바꾸거나, 시나리오를 first-party로 옮긴다.

### Safari에서만 안 되는 경우

ITP다. SameSite=None을 줘도 cross-site iframe에서는 쿠키 자체가 차단된다. CHIPS(`Partitioned`)로 가거나, Storage Access API로 사용자 동의를 받거나, 도메인 구조를 first-party로 재설계해야 한다.

### Set-Cookie가 떨어지는데 다음 요청에 안 붙는 경우

응답에는 분명히 `Set-Cookie`가 있는데 브라우저가 저장 안 하는 케이스다. 의심 순서:

1. `Secure` 속성이 있는데 HTTP로 응답한 경우(브라우저가 거부)
2. `__Host-` prefix인데 `Domain`을 지정했거나 `Path=/`가 아닌 경우
3. `__Secure-` prefix인데 `Secure`를 안 줬거나 HTTP인 경우
4. `SameSite=None`인데 `Secure`를 빠뜨린 경우
5. 쿠키 크기가 4KB 초과(브라우저별로 차이가 있지만 보통 4KB)

Chrome DevTools의 Application > Cookies 패널에서 reject 사유를 표시해주므로 거기서 가장 빨리 잡힌다.

### 같은 이름 쿠키가 두 개로 보이는 경우

Domain 속성을 바꾸는 마이그레이션 중에 자주 발생한다. 옛날에 `Domain=.example.com`으로 박힌 쿠키와 새로 `Domain` 없이 박은 쿠키가 동시에 살아 있다. 서버는 둘 다 받아서 어느 쪽이 신선한 값인지 모른다. 마이그레이션 시 옛 쿠키를 명시적으로 같은 도메인 속성으로 만료(`Max-Age=0`) 시켜야 깔끔하다.

```javascript
// 마이그레이션 시 옛 쿠키 정리
res.clearCookie('session', { domain: '.example.com', path: '/' });
res.clearCookie('session', { path: '/' });
res.cookie('__Host-session', newSid, { /* 새 속성 */ });
```

### iframe 위젯이 갑자기 안 동작하는 경우

서드파티 쿠키 차단 영향이다. 위젯 쿠키를 `Partitioned`로 발급하도록 바꾸거나, 위젯 자체를 메인 사이트의 서브도메인(first-party)으로 재배포한다.

## 정리

쿠키는 단순해 보이지만 브라우저 정책 변화의 최전선이다. 운영 중인 서비스라면 다음 항목을 확인해 둘 만하다.

- 인증 쿠키에 `__Host-` prefix가 붙어 있는가
- `Secure`, `HttpOnly`, `SameSite` 셋 다 명시적으로 지정되어 있는가
- `Domain` 속성을 불필요하게 넓게 잡고 있지 않은가
- cross-site 임베드 시나리오가 있다면 `Partitioned`로 전환됐는가
- Safari/Chrome/Firefox에서 동일하게 동작하는지 실제로 확인했는가
- 리버스 프록시 뒤에서 `secure` 판정이 정확히 되는가

브라우저 정책은 매년 바뀐다. Chrome status, WebKit blog, MDN 변경 로그를 정기적으로 확인하는 게 운영 책임의 일부다.
