---
title: OAuth 2.0 + OIDC
tags: [auth, security, jwt]
updated: 2026-09-22
---

# OAuth 2.0 + OIDC

## OIDC가 OAuth 2.0에 추가하는 것

OAuth 2.0은 권한 위임 프로토콜이지 인증 프로토콜이 아니다. access_token을 받았다는 건 "이 앱이 사용자 대신 특정 작업을 할 수 있다"는 의미지, "이 사용자가 실제로 누구인지"를 보장하지 않는다. scope에 `openid`를 포함하면 OIDC 모드가 활성화되고 토큰 응답에 `id_token`이 추가된다.

OIDC는 OAuth 2.0 위에 구체적으로 세 가지를 얹는다.

- `id_token`: 사용자 신원이 담긴 JWT. Authorization Server가 직접 서명한다.
- `nonce`: 재사용 공격 방어용 일회성 파라미터
- UserInfo 엔드포인트: id_token 클레임을 보완하는 추가 사용자 정보 API

## Access Token과 ID Token

둘 다 토큰 응답에 같이 오지만 용도가 완전히 다르다.

**access_token은 Resource Server가 쓴다.** API 요청의 `Authorization: Bearer xxx`에 실어 보내는 게 이것이다. 형식도 Provider마다 다르다. JWT로 발급하기도 하고 불투명한 문자열로 발급하기도 한다. 클라이언트가 access_token을 파싱하거나 내용을 해석하면 안 된다. 형식에 의존하기 시작하는 순간 Provider가 구현을 바꿀 때 코드가 깨진다.

**id_token은 클라이언트가 쓴다.** Authorization Server가 서명한 JWT로 발급되며, "이 사용자가 실제로 인증했다"는 증명이 들어있다. id_token을 API 서버에 Bearer 토큰으로 보내면 안 된다. 인증 확인용이지 권한 증명이 아니다.

id_token에 담긴 표준 클레임들:

| 클레임 | 의미 | 주의사항 |
|---|---|---|
| `sub` | 사용자 식별자 | Provider 내에서 유일. Provider가 달라지면 같은 사람도 다른 값 |
| `iss` | 토큰 발급자 URL | 검증 필수. 뒤에 슬래시 하나도 다른 값으로 처리 |
| `aud` | 토큰 수신자 (client_id) | 검증 필수. 안 하면 다른 앱 토큰 재사용 가능 |
| `exp` | 만료 시간 | clock skew 고려해 30~60초 여유 허용 |
| `iat` | 발급 시간 | |
| `auth_time` | 실제 인증 시각 | `max_age` 파라미터와 함께 사용 |
| `nonce` | 재사용 공격 방어 | 요청 시 보낸 값과 반드시 일치해야 함 |
| `amr` | 인증 방법 목록 (password, otp 등) | MFA 강제 여부 판단에 사용 |
| `at_hash` | access_token 앞 절반의 SHA-256 해시 | access_token 교체 공격 방어 |

`at_hash`는 종종 빠뜨린다. id_token과 access_token이 같은 요청에서 발급됐다는 걸 검증하는 클레임이다. 공격자가 다른 사용자의 id_token을 훔쳐서 자신의 access_token과 조합하는 시나리오를 막는다. access_token의 ASCII bytes를 SHA-256으로 해싱한 뒤 앞 16바이트를 base64url 인코딩한 값이 at_hash와 일치해야 한다.

## Implicit Flow를 피해야 하는 이유

Implicit Flow는 authorization_code 교환 없이 access_token을 URL fragment(`#access_token=xxx`)로 바로 전달한다. SPA를 위해 만들어졌지만 여러 경로로 토큰이 노출된다.

**Analytics 스크립트 유출.** 브라우저는 fragment를 서버에 보내지 않는다. 문제는 페이지에 심긴 서드파티 스크립트다. `location.href`를 읽어 외부 서버로 보내는 analytics 코드가 fragment를 그대로 수집한다. Google Analytics가 이 방식으로 URL을 수집한 사례가 있었다.

**Referer 헤더 유출.** 토큰을 받은 페이지에서 외부 CDN의 JS나 CSS를 로드하면, 해당 요청의 Referer 헤더에 fragment가 포함된 원본 URL이 실린다. Referrer-Policy를 별도로 설정하지 않은 서비스에서 발생한다.

**window.opener 공격.** 팝업 창에서 Implicit Flow로 인증하면, opener 창이 `window.opener.location.href`로 fragment를 읽을 수 있다. 피싱 사이트가 링크를 열어 OAuth 인증을 유도하는 시나리오다.

**postMessage 브로드캐스트.** hidden iframe으로 silent refresh를 구현할 때, `postMessage`의 `targetOrigin`을 `*`로 설정하면 모든 열린 창이 토큰을 받는다.

SPA에서는 Authorization Code + PKCE로 교체하면 된다. client_secret 없이도 PKCE의 code_verifier로 code 가로채기를 막을 수 있다. PKCE 구현 세부 내용은 [OAuth 2.0](OAuth.md) 문서 참조.

## state와 nonce — 방어 대상이 다르다

둘 다 랜덤 값이고 비슷해 보이지만 막는 공격이 다르다.

**state는 CSRF 방어다.** 인증 요청을 시작한 주체(브라우저)와 콜백을 받는 주체가 동일하다는 걸 확인한다.

로그인 CSRF 공격 시나리오: 공격자가 자신의 계정으로 OAuth 인증을 시작하고, 콜백 직전에 멈춘다. 그 콜백 URL(`/callback?code=attacker_code&state=xxx`)을 피해자에게 클릭하게 한다. state 검증이 없으면 피해자 브라우저에서 공격자의 code가 처리되고, 피해자는 공격자의 계정으로 로그인된다. 이후 공격자가 자신의 계정으로 로그인하면 피해자의 세션을 공유하게 된다. 결제 정보, 개인 데이터가 노출된다.

**nonce는 토큰 재사용 방어다.** 인증 요청에 포함한 nonce 값이 id_token의 nonce 클레임으로 돌아오는지 확인한다. 공격자가 이전에 유효했던 id_token을 가로채서 다시 쓰거나, 다른 앱에서 발급된 id_token을 재생(replay)하는 시나리오를 막는다.

state는 콜백 URL 쿼리 파라미터로 돌아오고, nonce는 id_token 내부 클레임으로 돌아온다. 둘 다 인증 요청 시 생성해서 서버 세션이나 Redis에 저장하고, 검증 후 즉시 삭제해야 한다.

## ID Token 검증 직접 구현 시 주의점

라이브러리 없이 구현하면 여러 단계를 빠뜨린다. 실제로 자주 빠뜨리는 것들이다.

**알고리즘 고정.** JWT 헤더의 `alg` 필드로 검증 알고리즘을 결정하면 안 된다. `alg: none`으로 서명 없는 JWT를 만들어 보내는 공격이 있다. 검증 라이브러리에 허용할 알고리즘 목록을 명시적으로 전달해야 한다. Google은 RS256, Kakao는 RS256을 쓴다. 허용 목록 없이 헤더를 그대로 신뢰하면 공격에 노출된다.

**iss 정확히 비교.** `https://accounts.google.com`과 `https://accounts.google.com/`은 다른 문자열이다. Provider마다 trailing slash 처리가 다르므로 허용값을 하드코딩할 때 실제 응답값을 그대로 써야 한다.

**aud 검증 빠뜨리기.** `aud` 클레임이 자신의 client_id인지 확인하지 않으면, 같은 Provider를 사용하는 다른 앱에서 발급된 id_token을 재사용할 수 있다. `aud`는 배열일 수 있고, 배열인 경우 `azp` 클레임도 확인해야 한다.

**clock skew 무시.** `exp`를 현재 시간과 비교할 때 서버 시간이 완벽히 동기화됐다고 가정하면 안 된다. 발급 서버와 검증 서버 간 수십 초 차이가 날 수 있다. 60초 이내의 clock skew는 허용하는 게 일반적이다.

**nonce 검증 누락.** OIDC를 쓰면서 nonce를 확인하지 않는 코드가 많다. 인증 요청 시 생성한 nonce와 id_token의 nonce 클레임이 일치해야 한다. 검증 후 서버 측 저장소에서 삭제해서 재사용을 막는다.

**JWKS 캐시 전략.** Provider의 공개키는 JWKS 엔드포인트에서 가져온다. 요청마다 가져오면 안 된다. 키 교체 주기가 수 시간~수일이므로 캐시해야 하고, JWT 헤더의 `kid`(key ID)가 캐시에 없을 때만 갱신한다. 단, 존재하지 않는 `kid`를 계속 보내서 JWKS 엔드포인트를 반복 호출하게 만드는 공격 패턴이 있다. 알 수 없는 `kid`는 즉시 거부하고, 캐시 재요청에 rate limit을 둬야 한다.

## 실무 구현 코드

### OIDC Authorization Code + PKCE 요청 생성

```javascript
const crypto = require('crypto');

function buildAuthRequest(session) {
    const codeVerifier  = crypto.randomBytes(32).toString('base64url');
    const codeChallenge = crypto
        .createHash('sha256')
        .update(codeVerifier)
        .digest('base64url');

    const state = crypto.randomBytes(16).toString('hex');
    const nonce = crypto.randomBytes(16).toString('hex');

    // state와 nonce를 서버 세션에 저장 — 콜백에서 검증
    session.oauth = { codeVerifier, state, nonce };

    const params = new URLSearchParams({
        response_type:         'code',
        client_id:             process.env.OIDC_CLIENT_ID,
        redirect_uri:          'https://myapp.com/callback',
        scope:                 'openid profile email',
        state,
        nonce,
        code_challenge:        codeChallenge,
        code_challenge_method: 'S256',
    });

    return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
}
```

### 콜백 처리 + state 검증 + 토큰 교환

```javascript
app.get('/callback', async (req, res) => {
    const { code, state, error } = req.query;

    if (error) {
        // 사용자가 동의를 거부한 경우 "access_denied"가 온다
        return res.redirect('/login?error=' + encodeURIComponent(error));
    }

    // state 불일치 = 잠재적 CSRF
    if (!state || state !== req.session.oauth?.state) {
        return res.status(403).send('state mismatch');
    }

    const { codeVerifier, nonce } = req.session.oauth;
    delete req.session.oauth; // 검증 후 즉시 삭제 — 재사용 방지

    const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body:    new URLSearchParams({
            grant_type:    'authorization_code',
            code,
            redirect_uri:  'https://myapp.com/callback',
            client_id:     process.env.OIDC_CLIENT_ID,
            client_secret: process.env.OIDC_CLIENT_SECRET,
            code_verifier: codeVerifier,
        }),
    });

    const tokens = await tokenRes.json();
    if (tokens.error) {
        throw new Error(`토큰 교환 실패: ${tokens.error_description}`);
    }

    const idTokenPayload = await verifyIdToken(tokens.id_token, nonce);

    // access_token과 id_token이 같은 요청에서 발급됐는지 확인
    if (idTokenPayload.at_hash) {
        const digest   = crypto.createHash('sha256').update(tokens.access_token, 'ascii').digest();
        const computed = digest.subarray(0, 16).toString('base64url');
        if (computed !== idTokenPayload.at_hash) {
            throw new Error('at_hash 불일치');
        }
    }

    req.session.userId = idTokenPayload.sub;
    res.redirect('/dashboard');
});
```

### ID Token 검증

```javascript
const { createRemoteJWKSet, jwtVerify } = require('jose');

// JWKS는 모듈 레벨에서 한 번만 생성 — 내부적으로 캐시를 관리한다
const GOOGLE_JWKS = createRemoteJWKSet(
    new URL('https://www.googleapis.com/oauth2/v3/certs')
);

async function verifyIdToken(idToken, expectedNonce) {
    const { payload } = await jwtVerify(idToken, GOOGLE_JWKS, {
        issuer:         'https://accounts.google.com',
        audience:       process.env.OIDC_CLIENT_ID,
        algorithms:     ['RS256'],  // alg:none 차단
        clockTolerance: 60,         // 60초 clock skew 허용
    });

    if (payload.nonce !== expectedNonce) {
        throw new Error('nonce mismatch — 재사용 공격 가능성');
    }

    return payload;
}
```

`jose` 라이브러리는 JWKS 캐시와 kid 선택 로직을 내장한다. `jsonwebtoken`처럼 공개키를 직접 넘기는 방식을 쓴다면 캐시 만료와 kid 조회를 직접 구현해야 한다.

### Spring Security + OIDC 설정

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
        provider:
          google:
            issuer-uri: https://accounts.google.com  # JWKS, userinfo 엔드포인트 자동 검색
```

`issuer-uri`를 설정하면 Spring Security가 Provider의 OpenID Configuration 엔드포인트(`/.well-known/openid-configuration`)에서 JWKS URL과 userinfo 엔드포인트를 자동으로 가져온다. id_token의 iss, aud, exp, nonce 검증도 자동으로 처리한다.

커스텀 클레임을 처리해야 한다면 `OidcUserService`를 확장하면 된다.

```java
@Service
public class CustomOidcUserService extends OidcUserService {

    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) throws OAuth2AuthenticationException {
        OidcUser oidcUser = super.loadUser(userRequest);

        // id_token 클레임 접근
        String sub       = oidcUser.getSubject();
        String email     = oidcUser.getEmail();
        Instant authTime = oidcUser.getAuthenticatedAt();

        // access_token은 userRequest에서 꺼낸다
        // oidcUser.getIdToken()으로 id_token 직접 접근 가능
        OAuth2AccessToken accessToken = userRequest.getAccessToken();

        return oidcUser;
    }
}
```

## 토큰 저장 위치 결정

id_token을 검증하고 나면 서버 세션에 `sub`(사용자 식별자)만 남기고 id_token 자체는 버린다. id_token을 장기 보관할 이유가 없다. 만료된 id_token은 어차피 유효하지 않다.

access_token은 사용자 대신 외부 API를 호출해야 하는 경우에만 저장한다. 그렇지 않으면 저장하지 않는 게 낫다. 저장 위치 선택 기준은 [OAuth 2.0](OAuth.md#토큰-저장과-보안) 문서 참조.
