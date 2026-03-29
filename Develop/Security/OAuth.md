---
title: OAuth 2.0
tags: [auth, oauth, authentication, authorization, security, pkce]
updated: 2026-03-29
---

# OAuth 2.0

## OAuth 2.0이 뭔가

OAuth 2.0은 권한 위임 프로토콜이다. 사용자가 비밀번호를 제3자 앱에 넘기지 않고, 특정 리소스에 대한 접근 권한만 위임하는 구조다.

예를 들어 "우리 서비스에서 Google 캘린더 읽기"를 구현한다고 하자. OAuth가 없으면 사용자의 Google 비밀번호를 직접 받아서 로그인해야 한다. 당연히 말이 안 된다. OAuth는 이 문제를 해결한다. 사용자가 Google 로그인 화면에서 직접 인증하고, 우리 앱에는 "캘린더 읽기 권한"이 담긴 토큰만 전달된다.

### 구성 요소

| 역할 | 설명 | 실제 예시 |
|------|------|----------|
| Resource Owner | 리소스의 실제 소유자 | 사용자 본인 |
| Client | 리소스에 접근하려는 앱 | 우리가 만드는 서비스 |
| Authorization Server | 인증 처리, 토큰 발급 | Google OAuth 서버, Kakao 인증 서버 |
| Resource Server | 보호된 리소스를 가진 서버 | Google Calendar API, Kakao 사용자 정보 API |

실제 서비스에서는 Authorization Server와 Resource Server가 같은 회사 소속인 경우가 대부분이다. Google OAuth 서버에서 토큰 받고, Google API 서버에서 데이터 가져오는 식이다.

## Grant Type별 동작 방식

### Authorization Code Grant

서버 사이드 앱에서 쓰는 기본 방식이다. 대부분의 경우 이걸 쓰면 된다.

흐름은 단순하다:

1. 사용자를 인증 서버 로그인 페이지로 리다이렉트
2. 사용자가 로그인하면 인증 서버가 `authorization_code`를 redirect_uri로 전달
3. 서버가 이 code를 가지고 인증 서버에 토큰 요청 (이때 client_secret 포함)
4. access_token, refresh_token 수령

핵심은 3번이다. code를 토큰으로 교환하는 과정이 서버-서버 간 통신이라 client_secret이 브라우저에 노출되지 않는다.

### Authorization Code Grant + PKCE

SPA나 모바일 앱처럼 client_secret을 안전하게 보관할 수 없는 환경에서 쓴다. OAuth 2.1에서는 모든 클라이언트에 PKCE를 필수로 요구한다.

동작 원리:

1. 클라이언트가 `code_verifier`(랜덤 문자열)를 생성
2. `code_verifier`를 SHA-256 해싱해서 `code_challenge`를 만듦
3. 인증 요청 시 `code_challenge`를 함께 전송
4. 토큰 교환 시 원본 `code_verifier`를 전송
5. 인증 서버가 `code_verifier`를 해싱해서 처음 받은 `code_challenge`와 비교

code를 중간에서 가로채더라도 `code_verifier`가 없으면 토큰 교환이 불가능하다.

### Client Credentials Grant

사용자 개입 없이 서버-서버 간 통신에 쓴다. 마이크로서비스 간 API 호출이 대표적이다.

```
POST /token
grant_type=client_credentials
&client_id=service-a
&client_secret=xxxxx
&scope=read:orders
```

client_id와 client_secret만으로 토큰을 발급받는다. 사용자 컨텍스트가 없으므로 사용자 데이터에 접근하는 용도로는 쓰면 안 된다.

### Device Authorization Grant (Device Code Flow)

스마트 TV, CLI 도구, IoT 기기처럼 브라우저가 없거나 입력이 불편한 환경에서 쓴다. GitHub CLI(`gh auth login`)가 이 방식을 사용한다.

흐름:

1. 기기가 인증 서버에 device code 요청
2. 인증 서버가 `device_code`, `user_code`, `verification_uri` 반환
3. 기기가 화면에 "https://github.com/login/device 에 접속해서 코드 ABCD-1234를 입력하세요" 표시
4. 사용자가 PC나 폰 브라우저에서 해당 URL 접속, 코드 입력, 로그인
5. 기기는 일정 간격으로 인증 서버에 폴링하면서 사용자 인증 완료를 기다림
6. 인증 완료되면 토큰 수령

```
// 1. device code 요청
POST /device/code
client_id=my-cli-app
&scope=repo user

// 응답
{
  "device_code": "xxxx",
  "user_code": "ABCD-1234",
  "verification_uri": "https://example.com/device",
  "expires_in": 900,
  "interval": 5   // 폴링 간격 (초)
}

// 2. 폴링
POST /token
grant_type=urn:ietf:params:oauth:grant-type:device_code
&device_code=xxxx
&client_id=my-cli-app

// 아직 인증 안 됨
{ "error": "authorization_pending" }

// 인증 완료 후
{ "access_token": "...", "refresh_token": "..." }
```

폴링 간격(`interval`)을 반드시 지켜야 한다. 너무 빠르게 폴링하면 `slow_down` 에러가 온다.

### Implicit Grant (deprecated)

**이 방식은 더 이상 쓰면 안 된다.** OAuth 2.1에서 공식적으로 제거되었다.

인증 코드 교환 단계 없이 access_token을 URL fragment(`#access_token=xxx`)로 바로 전달하는 방식이었다. SPA를 위해 만들어졌지만, 토큰이 브라우저 히스토리에 남고, Referer 헤더로 유출될 수 있는 문제가 있다.

SPA에서는 Authorization Code + PKCE를 쓰면 된다. 레거시 시스템에서 Implicit Grant를 발견하면 마이그레이션해야 한다.

## redirect_uri 검증 — 가장 흔한 실수

Authorization Code 탈취의 가장 흔한 원인이 redirect_uri 검증 실패다.

### 문제 상황

인증 서버에서 redirect_uri를 느슨하게 검증하면 공격자가 이렇게 요청할 수 있다:

```
GET /authorize?
  response_type=code
  &client_id=legitimate-app
  &redirect_uri=https://legitimate-app.com.attacker.com/callback
  &scope=openid profile
```

인증 서버가 prefix만 체크하면 `legitimate-app.com.attacker.com`도 통과한다. 사용자는 정상적인 로그인 화면을 보고 인증하지만, authorization code는 공격자 서버로 간다.

### 지켜야 할 것

- redirect_uri는 **정확히 일치(exact match)** 해야 한다. 와일드카드나 prefix 매칭은 쓰면 안 된다
- 인증 서버에 등록된 redirect_uri와 요청의 redirect_uri가 문자열 단위로 동일해야 한다
- 개발 환경용 `http://localhost` URI는 프로덕션 설정에 절대 남기면 안 된다
- 인증 서버를 직접 구축하는 경우, redirect_uri 비교 로직에 URL 정규화(normalize)를 넣지 마라. path traversal(`/callback/../admin/callback`)로 우회당할 수 있다

Spring Authorization Server는 기본적으로 exact match를 한다. 직접 구현할 때가 문제다.

## PKCE 구현에서 겪는 문제들

### code_verifier 세션 유실

PKCE에서 가장 많이 겪는 문제다. 인증 요청 시점에 `code_verifier`를 세션에 저장하고, 콜백에서 꺼내 쓰는데, 이 사이에 세션이 날아가는 경우가 있다.

발생하는 상황:

- 로드밸런서 뒤에 서버가 여러 대 있고 세션이 sticky 되지 않을 때
- 인증 화면에서 시간이 오래 걸려서 세션이 만료될 때
- 모바일 앱에서 외부 브라우저로 인증하고 돌아올 때 앱이 메모리에서 내려간 경우

해결 방법:

- 서버 세션 대신 Redis 같은 외부 저장소에 `code_verifier`를 저장한다. key는 state 파라미터를 쓰면 된다
- SPA라면 `sessionStorage`에 저장한다. `localStorage`는 탭 간 공유되므로 여러 탭에서 동시 로그인 시 꼬일 수 있다
- 모바일 앱은 Keychain/Keystore에 저장하고, 앱 복원 시 읽을 수 있게 해야 한다

### S256을 지원하지 않는 서버

PKCE의 `code_challenge_method`에는 `plain`과 `S256` 두 가지가 있다. `plain`은 code_verifier를 그대로 보내는 거라 보안상 의미가 거의 없다. 반드시 `S256`(SHA-256 해시)을 써야 한다.

문제는 일부 오래된 인증 서버가 `S256`을 지원하지 않는 경우다. 이때 `plain`으로 fallback하면 PKCE를 안 쓰는 것과 다를 바 없다. 서버가 S256을 지원하지 않으면 해당 서버의 OAuth 구현 자체를 의심해야 한다.

## 토큰 갱신 시 race condition

access_token 만료 후 refresh_token으로 갱신할 때, 동시에 여러 API 요청이 발생하면 문제가 생긴다.

### 시나리오

1. 요청 A가 401 응답을 받음 (access_token 만료)
2. 요청 B도 401 응답을 받음
3. 요청 A가 refresh_token으로 새 access_token 요청
4. 요청 B도 같은 refresh_token으로 새 access_token 요청
5. 인증 서버가 refresh_token rotation을 적용하고 있으면, 요청 A에서 refresh_token이 교체됨
6. 요청 B는 이미 폐기된 refresh_token을 사용하게 되어 실패
7. 일부 인증 서버는 이 시점에 해당 refresh_token family를 전부 폐기함 (보안 정책)

### 해결 방법

```javascript
// 토큰 갱신을 하나의 Promise로 직렬화
let refreshPromise = null;

async function getValidAccessToken() {
    if (isTokenValid(accessToken)) return accessToken;

    // 이미 갱신 중이면 같은 Promise를 반환
    if (!refreshPromise) {
        refreshPromise = refreshAccessToken(refreshToken)
            .then(tokens => {
                accessToken = tokens.access_token;
                if (tokens.refresh_token) {
                    refreshToken = tokens.refresh_token;
                }
                return accessToken;
            })
            .finally(() => { refreshPromise = null; });
    }
    return refreshPromise;
}
```

핵심은 갱신 요청을 하나로 모으는 것이다. 첫 번째 갱신 요청이 진행 중이면 나머지는 같은 Promise를 기다린다.

서버 사이드에서도 마찬가지다. 분산 환경이라면 Redis lock으로 refresh_token 갱신을 직렬화해야 한다.

## 소셜 로그인 provider별 차이점

OAuth 2.0은 표준이지만 provider마다 구현이 다르다. "OAuth 붙이면 끝"이라고 생각하면 provider마다 삽질한다.

### Google

- refresh_token을 받으려면 `access_type=offline` 파라미터가 필요하다. 이게 없으면 access_token만 온다
- 최초 동의 시에만 refresh_token을 발급한다. 이후에는 `prompt=consent`를 명시해야 다시 받을 수 있다
- scope에 `openid`를 넣으면 id_token도 같이 온다 (OpenID Connect)

```
GET /authorize?
  access_type=offline     // 이게 없으면 refresh_token 안 줌
  &prompt=consent         // 매번 동의 화면 = 매번 refresh_token 발급
  &scope=openid profile email
```

### Kakao

- token endpoint에 client_secret을 보낼 때 `client_secret_post` 방식을 써야 한다. 기본값인 `client_secret_basic`(HTTP Basic Auth)을 지원하지 않는다
- 앱 설정에서 "카카오 로그인 → 동의항목"에서 scope를 미리 설정해야 한다. API 요청에서 scope를 보내도 앱 설정에 없으면 무시된다
- 연결 끊기(`unlink`) API를 호출해야 완전한 회원 탈퇴가 된다. access_token만 폐기하면 다음 로그인 시 자동 연결된다

### Naver

- `client_secret`이 필수다. 다른 provider처럼 public client 설정이 없다
- 프로필 API 응답 구조가 `response` 객체 안에 한 번 더 감싸져 있다
- 회원 탈퇴 시 "네이버 아이디로 로그인 연동 해제" API를 별도로 호출해야 한다

### Apple

- Sign in with Apple은 최초 인증 시에만 사용자 이름과 이메일을 준다. 이걸 놓치면 다시 받을 방법이 없다. 반드시 첫 응답에서 저장해야 한다
- client_secret이 JWT다. Apple Developer 콘솔에서 받은 private key로 직접 JWT를 만들어서 사용한다
- id_token의 `sub` 값이 사용자 식별자인데, 같은 Apple 계정이라도 앱이 다르면 다른 값이 나온다

### Spring Security에서 provider별 처리

Spring Security OAuth2 Client를 쓰면 Google, GitHub 같은 CommonOAuth2Provider는 자동 설정된다. 하지만 Kakao, Naver 같은 국내 서비스는 provider 설정을 직접 해야 한다.

```java
// provider별 사용자 정보 파싱이 다르다
public class OAuth2UserInfoFactory {
    public static OAuth2UserInfo of(String provider, Map<String, Object> attributes) {
        return switch (provider) {
            case "google" -> new GoogleUserInfo(attributes);
            case "kakao"  -> new KakaoUserInfo(
                (Map<String, Object>) attributes.get("kakao_account")  // 중첩 구조
            );
            case "naver"  -> new NaverUserInfo(
                (Map<String, Object>) attributes.get("response")  // response 안에 실제 데이터
            );
            default -> throw new IllegalArgumentException("지원하지 않는 provider: " + provider);
        };
    }
}
```

## state 파라미터와 CSRF

state는 CSRF 방어용이다. 인증 요청 시 랜덤 값을 생성해서 세션에 저장하고, 콜백에서 돌아온 state와 비교한다. 일치하지 않으면 요청을 거부한다.

state 없이 구현하면 공격자가 자신의 authorization code를 피해자에게 주입할 수 있다. 피해자가 공격자의 계정으로 로그인하게 되는 거다. 이걸 "로그인 CSRF"라고 한다.

```javascript
// state 생성
const state = crypto.randomBytes(16).toString('hex');
session.oauthState = state;

// 콜백에서 검증
if (req.query.state !== session.oauthState) {
    return res.status(403).send('CSRF 검증 실패');
}
delete session.oauthState;  // 재사용 방지
```

## 토큰 저장과 보안

### access_token 저장 위치

| 환경 | 저장 위치 | 주의사항 |
|------|----------|---------|
| 서버 사이드 렌더링 | 서버 세션 또는 Redis | 가장 안전. 토큰이 브라우저에 노출되지 않음 |
| SPA | 메모리 (변수) | 새로고침하면 날아감. silent refresh나 iframe으로 재발급 |
| SPA (차선) | HttpOnly + Secure 쿠키 | BFF(Backend For Frontend) 패턴과 함께 사용 |
| 모바일 | iOS Keychain / Android Keystore | 루팅/탈옥 기기 대응 필요 |

`localStorage`에 access_token을 저장하는 코드가 많이 돌아다니는데, XSS 공격에 취약하다. XSS가 하나라도 터지면 토큰이 바로 탈취된다.

### refresh_token 관리

- refresh_token은 access_token보다 수명이 길다. 보통 7일~30일
- refresh_token rotation을 적용하면 갱신할 때마다 새 refresh_token을 발급하고 이전 것을 폐기한다
- 폐기된 refresh_token이 사용되면 해당 token family 전체를 폐기하는 것이 권장사항이다. 토큰 탈취 감지용이다

## OAuth 서버 직접 구축 vs SaaS

### 직접 구축하는 경우

- 인증/인가 로직에 대한 완전한 제어가 필요할 때
- 규제 요건상 사용자 데이터가 외부로 나가면 안 될 때 (금융, 의료)
- 커스텀 grant type이나 특수한 토큰 정책이 필요할 때

Spring Authorization Server, Keycloak, ORY Hydra 같은 프레임워크가 있다. 직접 RFC를 읽고 처음부터 만드는 건 권장하지 않는다. 빠뜨리기 쉬운 보안 요구사항이 너무 많다.

### SaaS를 쓰는 경우 (Auth0, AWS Cognito, Firebase Auth)

- 빠르게 출시해야 하는 서비스
- 인증 인프라를 운영할 팀이 없을 때
- MFA, passwordless 같은 기능을 직접 구현하기 부담스러울 때

SaaS를 쓸 때 주의할 점:

- vendor lock-in이 생긴다. 나중에 마이그레이션하려면 사용자 비밀번호 해시를 export할 수 없는 경우가 많다
- 비용이 MAU(월간 활성 사용자) 기준인 경우가 많다. 사용자가 늘면 비용도 빠르게 증가한다
- 커스터마이징 한계가 있다. 특히 토큰 클레임 커스터마이징이나 로그인 플로우 변경에 제약이 있을 수 있다

### 판단 기준

"인증은 핵심 도메인인가?" 라는 질문에 "예"라면 직접 구축을 고려하고, "아니오"라면 SaaS로 시작하는 게 맞다. 대부분의 서비스에서 인증은 핵심 도메인이 아니다.

## OAuth 2.0 vs OAuth 2.1

OAuth 2.1은 새로운 프로토콜이 아니라, 기존 OAuth 2.0 + 보안 BCP(Best Current Practice)를 하나로 합친 것이다.

주요 변경사항:

| 항목 | OAuth 2.0 | OAuth 2.1 |
|------|-----------|-----------|
| PKCE | public client에 권장 | 모든 client에 필수 |
| Implicit Grant | 지원 | 제거 |
| Resource Owner Password Grant | 지원 | 제거 |
| refresh_token | rotation 선택 | rotation 권장 |
| redirect_uri | exact match 권장 | exact match 필수 |

신규 프로젝트라면 OAuth 2.1 기준으로 구현하면 된다. 인증 서버가 아직 OAuth 2.1을 공식 지원하지 않더라도, 위 변경사항은 OAuth 2.0에서도 다 적용 가능한 것들이다.

## OpenID Connect (OIDC)

OAuth 2.0은 "권한 위임" 프로토콜이지 "인증" 프로토콜이 아니다. "이 사용자가 누구인지"를 확인하는 건 OAuth의 범위 밖이다.

OpenID Connect는 OAuth 2.0 위에 인증 레이어를 얹은 것이다. scope에 `openid`를 넣으면 access_token과 함께 `id_token`(JWT)이 발급된다. id_token에는 사용자 식별 정보(`sub`), 인증 시각(`auth_time`), 인증 방법(`amr`) 등이 들어있다.

소셜 로그인에서 "사용자 정보 가져오기"를 구현한다면 OAuth 2.0이 아니라 OIDC를 쓰는 거다. 구분해서 이해해야 한다.

---

## 코드 예제

### OAuth 2.0 Authorization Code Flow (Node.js)

```javascript
// -- 1. 인증 요청 URL 생성 (클라이언트 → 인증 서버) -----
const crypto = require('crypto');

function generateAuthUrl() {
    // PKCE: Code Verifier / Code Challenge 생성
    const codeVerifier = crypto.randomBytes(32).toString('base64url');
    const codeChallenge = crypto.createHash('sha256')
        .update(codeVerifier).digest('base64url');
    const state = crypto.randomBytes(16).toString('hex');  // CSRF 방어

    const params = new URLSearchParams({
        response_type: 'code',
        client_id:     process.env.OAUTH_CLIENT_ID,
        redirect_uri:  'https://myapp.com/callback',
        scope:         'openid profile email',
        state,
        code_challenge:        codeChallenge,
        code_challenge_method: 'S256'
    });

    // session에 저장 (callback에서 검증)
    session.codeVerifier = codeVerifier;
    session.state = state;

    return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
}

// -- 2. 콜백 처리 (인증 코드 → 액세스 토큰 교환) --------
app.get('/callback', async (req, res) => {
    const { code, state } = req.query;

    // state 검증 (CSRF 방어)
    if (state !== session.state) return res.status(400).send('Invalid state');

    // 토큰 교환
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type:    'authorization_code',
            code,
            redirect_uri:  'https://myapp.com/callback',
            client_id:     process.env.OAUTH_CLIENT_ID,
            client_secret: process.env.OAUTH_CLIENT_SECRET,
            code_verifier: session.codeVerifier  // PKCE
        })
    });

    const tokens = await tokenResponse.json();
    // tokens = { access_token, refresh_token, id_token, expires_in }

    // 사용자 정보 조회
    const userInfo = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
        headers: { Authorization: `Bearer ${tokens.access_token}` }
    }).then(r => r.json());

    // JWT id_token 검증
    const payload = await verifyIdToken(tokens.id_token);
    req.session.userId = payload.sub;
    res.redirect('/dashboard');
});

// -- 3. 토큰 갱신 (race condition 방지 포함) -----------
let refreshPromise = null;

async function refreshAccessToken(refreshToken) {
    if (refreshPromise) return refreshPromise;

    refreshPromise = fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type:    'refresh_token',
            refresh_token: refreshToken,
            client_id:     process.env.OAUTH_CLIENT_ID,
            client_secret: process.env.OAUTH_CLIENT_SECRET
        })
    })
    .then(r => r.json())
    .finally(() => { refreshPromise = null; });

    return refreshPromise;
}
```

### Spring Security OAuth2 설정

```yaml
# application.yml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: openid,profile,email
            redirect-uri: "{baseUrl}/login/oauth2/code/google"
          kakao:
            client-id: ${KAKAO_CLIENT_ID}
            client-secret: ${KAKAO_CLIENT_SECRET}
            client-authentication-method: client_secret_post
            authorization-grant-type: authorization_code
            scope: profile_nickname,account_email
            redirect-uri: "{baseUrl}/login/oauth2/code/kakao"
        provider:
          kakao:
            authorization-uri: https://kauth.kakao.com/oauth/authorize
            token-uri: https://kauth.kakao.com/oauth/token
            user-info-uri: https://kapi.kakao.com/v2/user/me
            user-name-attribute: id
```

```java
// SecurityConfig.java
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {
    private final CustomOAuth2UserService oAuth2UserService;
    private final OAuth2SuccessHandler successHandler;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/login/**", "/oauth2/**").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2Login(oauth2 -> oauth2
                .userInfoEndpoint(ui -> ui.userService(oAuth2UserService))
                .successHandler(successHandler)
            );
        return http.build();
    }
}

// CustomOAuth2UserService.java
@Service
@RequiredArgsConstructor
public class CustomOAuth2UserService implements OAuth2UserService<OAuth2UserRequest, OAuth2User> {
    private final UserRepository userRepo;

    @Override
    public OAuth2User loadUser(OAuth2UserRequest req) {
        OAuth2User oAuth2User = new DefaultOAuth2UserService().loadUser(req);
        String registrationId = req.getClientRegistration().getRegistrationId();

        OAuth2UserInfo userInfo = OAuth2UserInfoFactory.of(registrationId, oAuth2User.getAttributes());
        User user = userRepo.findByEmail(userInfo.getEmail())
            .orElseGet(() -> userRepo.save(User.of(userInfo, registrationId)));

        return new CustomOAuth2User(user, oAuth2User.getAttributes());
    }
}

// OAuth2SuccessHandler.java — 로그인 성공 후 JWT 발급
@Component
@RequiredArgsConstructor
public class OAuth2SuccessHandler extends SimpleUrlAuthenticationSuccessHandler {
    private final JwtTokenProvider jwtTokenProvider;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest req, HttpServletResponse res,
                                        Authentication auth) throws IOException {
        CustomOAuth2User user = (CustomOAuth2User) auth.getPrincipal();
        String accessToken = jwtTokenProvider.createAccessToken(user.getId(), user.getRole());
        String refreshToken = jwtTokenProvider.createRefreshToken(user.getId());

        // HttpOnly 쿠키에 저장
        res.addCookie(createCookie("access_token", accessToken, 3600));
        res.addCookie(createCookie("refresh_token", refreshToken, 604800));
        getRedirectStrategy().sendRedirect(req, res, "/dashboard");
    }
}
```

### JWT 발급 / 검증

```java
// JwtTokenProvider.java
@Component
public class JwtTokenProvider {
    @Value("${jwt.secret}") private String secret;
    private static final long ACCESS_TOKEN_EXPIRE  = 60 * 60 * 1000L;       // 1시간
    private static final long REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60 * 1000L; // 7일

    private Key getKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String createAccessToken(Long userId, String role) {
        return Jwts.builder()
            .setSubject(userId.toString())
            .claim("role", role)
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + ACCESS_TOKEN_EXPIRE))
            .signWith(getKey(), SignatureAlgorithm.HS256)
            .compact();
    }

    public Claims validateToken(String token) {
        try {
            return Jwts.parserBuilder()
                .setSigningKey(getKey()).build()
                .parseClaimsJws(token).getBody();
        } catch (ExpiredJwtException e) {
            throw new TokenExpiredException("토큰이 만료되었습니다.");
        } catch (JwtException e) {
            throw new InvalidTokenException("유효하지 않은 토큰입니다.");
        }
    }
}
```

---

## 참조

- RFC 6749: The OAuth 2.0 Authorization Framework
- RFC 6750: The OAuth 2.0 Authorization Framework: Bearer Token Usage
- RFC 7636: Proof Key for Code Exchange by OAuth Public Clients
- RFC 8628: OAuth 2.0 Device Authorization Grant
- OAuth 2.1 Draft Specification (draft-ietf-oauth-v2-1)
- OpenID Connect Core 1.0 Specification
- OAuth 2.0 Security Best Current Practice (RFC 9700)
- OWASP OAuth 2.0 Security Cheat Sheet
