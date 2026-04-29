---
title: JWT (JSON Web Token)
tags: [auth, jwt, jws, jwe, jwk, security, authentication, token]
updated: 2026-04-29
---

# JWT (JSON Web Token)

## JWT가 뭔가

JWT는 당사자 간에 정보를 JSON 객체로 안전하게 전달하기 위한 토큰 포맷이다. RFC 7519에 정의되어 있고, 보통 인증 토큰으로 쓴다. 핵심은 "서명된 JSON"이라는 것. 서명이 있기 때문에 토큰이 변조되었는지 검증할 수 있고, 자체 검증이 가능하므로 서버가 세션 저장소를 따로 두지 않아도 된다.

세션 기반 인증과 비교하면 차이가 명확하다. 세션은 서버가 상태를 가지고 있어야 한다. 사용자가 로그인하면 세션 ID를 쿠키로 발급하고, 서버는 메모리나 Redis에 세션 데이터를 보관한다. 매 요청마다 세션 ID로 서버 저장소를 조회한다. JWT는 그 반대다. 토큰 자체에 사용자 정보가 들어 있고, 서명만 검증하면 된다. 서버가 stateless하게 동작할 수 있다.

다만 이게 항상 좋은 건 아니다. 토큰을 한 번 발급하면 만료될 때까지 무효화하기 어렵다. 세션은 서버에서 즉시 삭제하면 끝나지만, JWT는 발급된 이후에는 서버가 직접 통제할 수 없다. 이 때문에 짧은 만료 시간 + 리프레시 토큰 조합을 쓰거나, 별도 블랙리스트를 유지해야 한다.

## 토큰 구조

JWT는 점(`.`)으로 구분된 세 부분으로 되어 있다.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NSIsImV4cCI6MTcxNDUwMDAwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

각각 Header, Payload, Signature이고 모두 Base64URL로 인코딩되어 있다. 주의할 점은 인코딩이지 암호화가 아니라는 것. 누구나 디코딩해서 내용을 볼 수 있다.

### Header

알고리즘과 토큰 타입이 들어간다.

```json
{
  "alg": "HS256",
  "typ": "JWT",
  "kid": "2026-04-key-1"
}
```

`alg`은 서명 알고리즘. `typ`은 보통 `JWT`로 고정. `kid`(Key ID)는 키 회전을 위해 쓴다. 여러 개의 키 중 어떤 키로 서명했는지 식별하는 용도다.

### Payload

실제 데이터가 들어간다. 예약된 클레임이 몇 가지 있다.

| 클레임 | 의미 | 예시 |
|--------|------|------|
| `iss` | 발급자 (issuer) | "https://auth.example.com" |
| `sub` | 주체 (subject) | 사용자 ID |
| `aud` | 대상자 (audience) | "api.example.com" |
| `exp` | 만료 시각 (Unix timestamp) | 1714500000 |
| `nbf` | 이 시각 이전엔 무효 | 1714490000 |
| `iat` | 발급 시각 | 1714490000 |
| `jti` | 토큰 고유 ID | UUID |

이 외에 커스텀 클레임을 넣을 수 있다. 사용자 권한, 이메일, 닉네임 같은 것들. 하지만 민감한 정보는 절대 넣지 마라. 비밀번호, 주민번호, 카드번호 같은 건 안 된다. JWT는 암호화되지 않는다는 걸 다시 한 번 강조한다.

페이로드 크기도 신경 써야 한다. JWT는 보통 헤더에 실어 보낸다. 너무 커지면 요청 헤더 크기 제한에 걸린다. 토큰 하나에 권한 100개 넣고 그러면 안 된다. 사용자 ID와 최소한의 정보만 넣고, 나머지는 서버에서 조회하는 게 낫다.

### Signature

Header와 Payload를 합친 문자열을 비밀키로 서명한 결과다.

```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

이 서명이 있어서 토큰을 변조하면 검증이 실패한다. 페이로드만 바꿔서 권한을 admin으로 올린다거나 하는 게 안 된다.

## 서명 알고리즘

알고리즘 선택은 운영 환경에 따라 다르다.

### HS256 (HMAC-SHA256)

대칭키 방식이다. 발급자와 검증자가 같은 비밀키를 공유한다.

장점은 단순하다는 것. 비밀키 하나만 관리하면 된다. 단일 서비스 내에서 인증 서버와 리소스 서버가 같은 시스템이라면 이걸 쓰는 게 편하다.

단점은 키 분배 문제. 검증해야 하는 모든 서비스가 비밀키를 알아야 하므로, 마이크로서비스 환경에서는 키가 여러 곳에 흩어진다. 한 서비스가 털리면 다 털린다.

비밀키는 충분히 길어야 한다. RFC 7518에 따르면 HS256은 최소 256비트 키를 권장한다. 짧은 비밀번호 같은 걸 키로 쓰면 brute-force가 가능하다. 32바이트 이상 랜덤 바이트를 base64로 인코딩한 값을 써야 한다.

### RS256 (RSA-SHA256)

비대칭키 방식이다. 발급자는 개인키로 서명하고, 검증자는 공개키로 검증한다.

마이크로서비스 환경에서 주로 쓴다. 인증 서버만 개인키를 가지고, 다른 서비스들은 공개키만 받아서 검증한다. 공개키는 노출되어도 안전하다.

OIDC(OpenID Connect) 환경에서는 거의 RS256이다. Google, Auth0, Keycloak 같은 IdP들이 모두 JWK Set 엔드포인트로 공개키를 노출한다.

단점은 토큰이 좀 더 크고 검증이 HS256보다 느리다는 것. 하지만 운영 환경에서 체감되는 차이는 거의 없다.

### ES256 (ECDSA-SHA256)

타원곡선 기반 비대칭키. RS256과 비슷한 용도지만 키 크기가 훨씬 작다. RSA 2048비트와 ECDSA 256비트가 비슷한 보안 강도다. 토큰 크기와 서명 속도 면에서 유리해서 모바일이나 IoT 환경에서 쓴다.

### 어떤 걸 골라야 하나

- 단일 모놀리식 서비스: HS256
- 마이크로서비스 + 자체 IdP: RS256 또는 ES256
- 외부 OIDC 연동: 발급자가 정한 알고리즘 (보통 RS256)

알고리즘을 클라이언트가 결정하게 두면 절대 안 된다. 서버는 허용된 알고리즘 목록을 명시적으로 갖고 있어야 한다. 이 얘기는 잠시 후 `alg=none` 공격에서 다시 한다.

## 검증 절차

JWT 검증은 단순히 서명만 확인하는 게 아니다. 라이브러리가 알아서 다 해주는 것 같지만, 옵션을 잘못 주면 검증을 일부 건너뛸 수 있다. 어떤 단계가 있는지 알고 있어야 한다.

```mermaid
flowchart TD
    A[토큰 수신] --> B[Header 디코딩]
    B --> C{alg 화이트리스트 확인}
    C -->|불일치| X[거부]
    C -->|일치| D[kid로 검증 키 조회]
    D --> E{서명 검증}
    E -->|실패| X
    E -->|성공| F{exp 확인}
    F -->|만료| X
    F -->|유효| G{nbf 확인}
    G -->|아직 무효| X
    G -->|유효| H{iss/aud 확인}
    H -->|불일치| X
    H -->|일치| I[검증 통과]
```

순서가 중요하다. 서명 검증 전에 페이로드를 신뢰하면 안 된다. 그래서 alg, kid 같은 헤더 정보는 서버가 미리 정한 값과 비교만 해야 하고, 페이로드의 클레임은 서명 검증 후에만 사용한다.

### 실패 케이스

검증을 잘못하면 어떤 공격이 가능한지 알아둬야 한다.

#### alg=none 공격

JWT 명세에는 `alg`을 `none`으로 설정해서 서명 없이 보내는 옵션이 있다. 디버깅용으로 들어간 거다. 라이브러리가 이걸 그대로 받아들이면 공격자가 페이로드를 마음대로 바꿀 수 있다.

```
헤더: {"alg":"none","typ":"JWT"}
페이로드: {"sub":"admin","exp":9999999999}
서명: (없음)
```

서버가 `alg=none`을 허용하면 이 토큰이 통과된다. 옛날 JWT 라이브러리들이 이 문제로 많이 털렸다. 요즘 라이브러리는 명시적으로 허용하지 않는 한 거부한다. 하지만 직접 검증 코드를 짜거나 옵션을 잘못 주면 여전히 가능하다.

방어는 간단하다. 허용 알고리즘을 화이트리스트로 명시하면 된다.

```javascript
// jsonwebtoken (Node.js)
jwt.verify(token, secret, { algorithms: ['HS256'] });
```

`algorithms` 옵션을 빼먹으면 라이브러리에 따라 `alg=none`을 통과시킬 수 있다. 항상 명시해라.

#### 알고리즘 혼동 공격

RS256으로 서명한 토큰을 받는 서버가, 검증 시 알고리즘을 페이로드에서 가져온다고 하자. 공격자가 헤더의 `alg`을 `HS256`으로 바꾸고, 공개키를 비밀키로 사용해서 HMAC 서명을 만들면 검증을 통과한다. 공개키는 노출되어 있으니까 공격자도 가질 수 있다.

```
원래: alg=RS256, 검증키=공개키 (RSA 검증)
공격: alg=HS256, 서명=HMAC(payload, 공개키), 검증키=공개키 (HMAC 검증)
```

서버가 토큰의 `alg`을 그대로 믿고 그 알고리즘으로 검증하면 통과된다. 방어는 알고리즘 화이트리스트.

#### kid 조작 공격

`kid` 필드로 검증 키를 조회한다고 하자. 어떤 구현은 `kid`를 파일 경로나 SQL 쿼리에 그대로 넣는다.

```python
key = open(f"/keys/{header['kid']}").read()
```

공격자가 `kid`를 `../../../dev/null` 같은 걸로 보내면 빈 키로 서명을 검증하게 된다. 빈 비밀키로 만든 HMAC 서명을 같이 보내면 통과한다.

SQL 인젝션도 마찬가지. `kid`로 `' UNION SELECT 'attacker_known_key' --` 같은 페이로드를 보내면 알려진 키로 검증하게 만들 수 있다.

`kid`는 외부 입력이다. 화이트리스트 검증을 거쳐야 하고, 직접 파일 경로나 쿼리에 넣지 마라. 미리 로드된 키 맵에서 조회하는 식으로 처리해야 한다.

#### 만료 검증 누락

`exp` 클레임이 있어도 라이브러리가 자동으로 검증하지 않는 경우가 있다. 특히 직접 파싱하는 코드에서 자주 빠진다.

```javascript
// 잘못된 예
const decoded = jwt.decode(token);  // 검증 안 함
if (decoded.sub === userId) { /* 통과 */ }
```

`jwt.decode`는 단순 디코딩이고 서명 검증도, 만료 검증도 안 한다. `jwt.verify`를 써야 한다. Spring Security 같은 프레임워크에서도 검증 옵션을 직접 비활성화하면 만료된 토큰이 통과된다.

#### 시계 차이 (Clock Skew)

서버 간 시간이 정확히 맞지 않을 수 있다. 발급 서버 시간이 검증 서버보다 1초 빠르면, 방금 발급된 토큰이 `nbf` 검증에서 실패할 수 있다.

대부분의 라이브러리는 `clockTolerance` 옵션을 제공한다. 보통 30초 정도 두고, NTP로 시간 동기화는 별도로 해야 한다.

## 액세스 토큰과 리프레시 토큰

JWT를 인증에 쓸 때 단일 토큰으로 쓰면 만료 시간 설정이 까다롭다. 짧으면 사용자가 자주 로그인해야 하고, 길면 탈취당했을 때 위험하다.

해결 방법은 두 종류 토큰을 분리하는 것.

| 종류 | 만료 시간 | 용도 | 저장 위치 |
|------|-----------|------|-----------|
| Access Token | 짧음 (5~30분) | API 호출 인증 | 메모리 또는 짧은 쿠키 |
| Refresh Token | 김 (1주~30일) | Access Token 재발급 | HttpOnly Secure 쿠키 또는 별도 저장 |

### 동작 흐름

```mermaid
sequenceDiagram
    participant Client as 클라이언트
    participant Auth as 인증 서버
    participant API as API 서버

    Client->>Auth: 로그인 (id/pw)
    Auth-->>Client: Access Token + Refresh Token
    Note right of Client: 두 토큰 모두 보관

    Client->>API: API 요청 (Access Token)
    API-->>Client: 응답

    Note over Client: 30분 후, Access Token 만료

    Client->>API: API 요청 (만료된 Access Token)
    API-->>Client: 401 Unauthorized

    Client->>Auth: Refresh Token으로 재발급 요청
    Auth->>Auth: Refresh Token 검증 + DB 조회
    Auth-->>Client: 새 Access Token (선택: 새 Refresh Token)

    Client->>API: API 재시도 (새 Access Token)
    API-->>Client: 응답
```

### Refresh Token 설계

Refresh Token은 그냥 JWT로 만들 수도 있지만, 보통은 DB에 저장하는 불투명 토큰(opaque token)으로 만든다. 이유가 있다.

Refresh Token은 무효화가 가능해야 한다. 사용자가 로그아웃하거나, 비밀번호를 바꾸거나, 의심스러운 활동이 감지되면 즉시 폐기해야 한다. JWT로 만들면 즉시 폐기가 어렵다. 그래서 보통 랜덤 문자열을 DB에 저장하고, 매 요청마다 DB를 조회한다.

Access Token은 stateless하게 빠르게 검증, Refresh Token은 stateful하게 안전하게 관리. 이 조합이 일반적이다.

### Refresh Token Rotation

리프레시 토큰을 한 번 쓰면 새 토큰으로 교체하는 방식이다. 토큰이 탈취되어도 합법 사용자가 한 번만 사용하면 공격자의 토큰은 무효화된다.

탈취 감지도 가능하다. 이미 사용된 리프레시 토큰이 또 들어오면 누군가 훔친 것이다. 이때 해당 사용자의 모든 토큰을 무효화한다.

```javascript
async function refreshTokens(oldRefreshToken) {
  const stored = await db.refreshTokens.findOne({ token: oldRefreshToken });
  
  if (!stored) {
    // 알려지지 않은 토큰 - 즉시 거부
    throw new Error('Invalid refresh token');
  }
  
  if (stored.used) {
    // 이미 사용된 토큰이 또 들어왔다 - 탈취 의심
    await db.refreshTokens.deleteMany({ userId: stored.userId });
    throw new Error('Token reuse detected');
  }
  
  await db.refreshTokens.updateOne({ _id: stored._id }, { used: true });
  
  const newAccess = signAccessToken(stored.userId);
  const newRefresh = await createRefreshToken(stored.userId);
  
  return { accessToken: newAccess, refreshToken: newRefresh };
}
```

## 토큰 무효화 (블랙리스트)

JWT의 가장 큰 약점이 무효화다. 만료 전에 강제로 막아야 하는 상황이 분명히 있다.

- 사용자가 로그아웃
- 비밀번호 변경
- 계정 정지
- 보안 사고로 모든 토큰 폐기

Access Token이 짧으면(5~15분) 무효화 없이도 견딜 만하다. 다음 갱신 때 Refresh Token을 차단하면 더는 발급 안 되니까. 하지만 이 시간 동안은 어쩔 수 없이 유효하다.

즉시 차단이 필요하면 블랙리스트를 두어야 한다.

### Redis 블랙리스트

토큰의 `jti`(JWT ID)를 키로 Redis에 저장한다. TTL은 토큰의 남은 유효 시간으로 설정. 그러면 토큰이 만료될 때 Redis 항목도 자동으로 사라진다.

```javascript
async function revokeToken(token) {
  const decoded = jwt.verify(token, secret);
  const ttl = decoded.exp - Math.floor(Date.now() / 1000);
  if (ttl > 0) {
    await redis.set(`blacklist:${decoded.jti}`, '1', 'EX', ttl);
  }
}

async function isRevoked(jti) {
  return Boolean(await redis.get(`blacklist:${jti}`));
}
```

매 요청마다 Redis 조회를 해야 하니까 stateless의 장점은 사라진다. Refresh Token만 Redis로 관리하고 Access Token은 짧게 가져가는 게 일반적인 절충안이다.

### 사용자별 토큰 무효화

비밀번호 변경 같은 상황에서는 해당 사용자의 모든 토큰을 무효화해야 한다. `jti`로 일일이 차단하기 어려우니까, 사용자 레코드에 `tokenVersion` 같은 필드를 둔다.

토큰 발급 시 현재 `tokenVersion`을 페이로드에 넣고, 검증 시 DB의 값과 비교한다. 비밀번호 변경 시 `tokenVersion`을 증가시키면 기존 토큰들이 모두 무효화된다.

```javascript
function signToken(user) {
  return jwt.sign({
    sub: user.id,
    tokenVersion: user.tokenVersion
  }, secret, { expiresIn: '15m' });
}

async function verifyToken(token) {
  const decoded = jwt.verify(token, secret);
  const user = await db.users.findOne({ id: decoded.sub });
  if (decoded.tokenVersion !== user.tokenVersion) {
    throw new Error('Token revoked');
  }
  return decoded;
}
```

이 방식도 매 요청 DB 조회가 필요하지만, 캐시를 끼면 부담을 줄일 수 있다.

## 키 회전

비밀키는 주기적으로 바꿔야 한다. 한 키를 너무 오래 쓰면 노출 위험이 커진다. 그런데 키를 바꾸는 순간 기존 토큰들이 모두 무효화되면 곤란하다. 그래서 점진적 회전이 필요하다.

### JWK Set

JSON Web Key Set은 여러 공개키를 노출하는 표준 포맷이다. OIDC IdP들이 모두 이걸 쓴다.

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "2026-04-key-1",
      "use": "sig",
      "alg": "RS256",
      "n": "0vx7agoebGc...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "2026-03-key-1",
      "use": "sig",
      "alg": "RS256",
      "n": "xGeKzlhx...",
      "e": "AQAB"
    }
  ]
}
```

검증자는 토큰의 `kid`를 보고 JWK Set에서 해당 키를 찾아 검증한다. 그래서 이전 키와 새 키를 동시에 노출하다가, 충분한 시간이 지난 후 이전 키를 제거한다.

### 회전 절차

```mermaid
flowchart LR
    A[기존: K1으로 서명/검증] --> B[K2 추가, K1으로 서명 유지]
    B --> C[K2로 서명 시작, K1은 검증만]
    C --> D[K1 만료, K2만 사용]
```

1. 새 키 K2를 생성하고 JWK Set에 추가. 이때는 여전히 K1으로 서명한다.
2. 검증자들이 새 JWK Set을 캐싱했을 시간(보통 몇 시간)이 지난 후, 서명을 K2로 전환한다.
3. K1으로 서명된 토큰들이 모두 만료될 때까지 K1을 JWK Set에 유지한다.
4. 충분히 시간이 지나면 K1을 JWK Set에서 제거한다.

이 사이클은 보통 며칠~몇 주 단위로 돈다. 자동화하지 않으면 운영자 실수가 생긴다.

## 흔한 실수

### localStorage에 토큰 저장

브라우저에서 가장 자주 보는 실수다. 편하다고 localStorage에 토큰을 저장한다.

```javascript
// 절대 하지 마라
localStorage.setItem('accessToken', token);
```

문제는 XSS다. 페이지에 악성 스크립트가 한 줄이라도 실행되면 `localStorage`의 모든 데이터를 가져갈 수 있다. 광고 라이브러리, 외부 위젯, 사용자가 입력한 콘텐츠 등 XSS 경로는 너무 많다.

대안:

- **Refresh Token**: HttpOnly + Secure + SameSite 쿠키. JS로 접근 불가능.
- **Access Token**: 메모리에 보관. 페이지 새로고침되면 Refresh Token으로 재발급. 또는 짧은 만료의 HttpOnly 쿠키.

쿠키만 쓰면 CSRF가 걸린다. 그래서 SameSite=Strict 또는 Lax를 설정하거나, 별도 CSRF 토큰을 두어야 한다. 또는 Authorization 헤더로 보내고 Access Token은 메모리, Refresh Token만 HttpOnly 쿠키로 두는 패턴이 일반적이다.

### 만료 검증 우회

`jwt.decode`와 `jwt.verify`를 헷갈려서 검증 없이 디코딩만 하는 코드를 자주 본다.

```javascript
// 잘못된 예
const payload = JSON.parse(atob(token.split('.')[1]));
if (payload.role === 'admin') { /* ... */ }
```

이건 검증을 전혀 안 한다. 공격자가 임의로 만든 토큰을 보내도 통과된다. 라이브러리의 verify 함수를 써라.

### JWS와 JWE 혼동

JWS(JSON Web Signature)는 서명만, JWE(JSON Web Encryption)는 암호화까지 포함한다. 우리가 보통 JWT라고 부르는 건 JWS다. 페이로드는 누구나 디코딩해서 볼 수 있다.

민감 정보를 페이로드에 넣었다가 "JWT는 안전하다고 들었는데 왜 보이지?" 하는 경우가 있다. JWE를 쓰면 페이로드를 숨길 수 있지만, 암호화 키 관리가 추가로 필요하고 복잡하다. 대부분의 경우는 민감 정보를 토큰에 안 넣는 게 맞다.

### Audience 검증 누락

`aud` 클레임을 검증하지 않으면 다른 서비스용 토큰이 우리 서비스에 통과될 수 있다. 같은 인증 서버를 쓰는 여러 서비스가 있다면 특히 위험하다.

### 토큰을 URL에 노출

OAuth callback에서 fragment(`#`)에 토큰을 받는 경우는 표준이지만, 그 외 상황에서 토큰을 쿼리 파라미터로 보내면 서버 로그, 브라우저 히스토리, Referer 헤더에 남는다. 항상 Authorization 헤더로 보내야 한다.

## Spring Security 검증 예제

Spring Boot 3 + Spring Security 6 기준이다. JJWT 라이브러리를 사용한다.

```kotlin
@Component
class JwtAuthFilter(
    private val tokenService: JwtTokenService
) : OncePerRequestFilter() {

    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        chain: FilterChain
    ) {
        val token = extractToken(request)
        if (token != null) {
            try {
                val claims = tokenService.verify(token)
                val auth = UsernamePasswordAuthenticationToken(
                    claims.subject,
                    null,
                    claims["roles", List::class.java]
                        ?.map { SimpleGrantedAuthority("ROLE_$it") }
                        ?: emptyList()
                )
                SecurityContextHolder.getContext().authentication = auth
            } catch (e: JwtException) {
                // 검증 실패 - 인증 컨텍스트 비우고 통과
                // 이후 인증 필요한 엔드포인트에서 401 발생
                SecurityContextHolder.clearContext()
            }
        }
        chain.doFilter(request, response)
    }

    private fun extractToken(request: HttpServletRequest): String? {
        val header = request.getHeader("Authorization") ?: return null
        return if (header.startsWith("Bearer ")) header.substring(7) else null
    }
}

@Service
class JwtTokenService(
    @Value("\${jwt.secret}") secretBase64: String
) {
    private val key: SecretKey = Keys.hmacShaKeyFor(Base64.getDecoder().decode(secretBase64))

    private val parser: JwtParser = Jwts.parser()
        .verifyWith(key)
        .requireIssuer("https://auth.example.com")
        .requireAudience("api.example.com")
        .clockSkewSeconds(30)
        .build()

    fun verify(token: String): Claims {
        return parser.parseSignedClaims(token).payload
    }

    fun issue(userId: String, roles: List<String>): String {
        val now = Instant.now()
        return Jwts.builder()
            .issuer("https://auth.example.com")
            .audience().add("api.example.com").and()
            .subject(userId)
            .issuedAt(Date.from(now))
            .expiration(Date.from(now.plus(15, ChronoUnit.MINUTES)))
            .id(UUID.randomUUID().toString())
            .claim("roles", roles)
            .signWith(key, Jwts.SIG.HS256)
            .compact()
        }
}
```

`requireIssuer`, `requireAudience`를 명시한 게 핵심이다. 이걸 안 하면 다른 서비스용 토큰이 통과될 수 있다. `clockSkewSeconds`로 시계 차이를 허용한다.

JJWT 0.12 이상은 알고리즘 혼동 공격에 대한 방어가 내장되어 있다. `verifyWith(SecretKey)`는 HMAC만, `verifyWith(PublicKey)`는 RSA/EC만 받는다. 옛날 버전은 직접 알고리즘 화이트리스트를 검증해야 했다.

## Node.js 검증 예제

`jsonwebtoken` 라이브러리 기준이다.

```javascript
const jwt = require('jsonwebtoken');

function verifyToken(token) {
  try {
    return jwt.verify(token, process.env.JWT_SECRET, {
      algorithms: ['HS256'],
      issuer: 'https://auth.example.com',
      audience: 'api.example.com',
      clockTolerance: 30,
    });
  } catch (e) {
    if (e instanceof jwt.TokenExpiredError) {
      throw new AuthError('TOKEN_EXPIRED');
    }
    if (e instanceof jwt.JsonWebTokenError) {
      throw new AuthError('INVALID_TOKEN');
    }
    throw e;
  }
}

function authMiddleware(req, res, next) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token' });
  }
  
  try {
    req.user = verifyToken(header.slice(7));
    next();
  } catch (e) {
    return res.status(401).json({ error: e.message });
  }
}
```

`algorithms: ['HS256']`은 절대 빼먹으면 안 된다. 명시하지 않으면 라이브러리 버전에 따라 `alg=none`이나 알고리즘 혼동이 가능해진다.

JWK Set을 쓰는 OIDC 환경에서는 `jwks-rsa`를 함께 쓴다.

```javascript
const jwksClient = require('jwks-rsa');

const client = jwksClient({
  jwksUri: 'https://auth.example.com/.well-known/jwks.json',
  cache: true,
  cacheMaxAge: 600000,  // 10분
  rateLimit: true,
});

function getKey(header, callback) {
  client.getSigningKey(header.kid, (err, key) => {
    if (err) return callback(err);
    callback(null, key.getPublicKey());
  });
}

jwt.verify(token, getKey, {
  algorithms: ['RS256'],
  issuer: 'https://auth.example.com',
  audience: 'api.example.com',
}, (err, decoded) => {
  if (err) { /* ... */ }
});
```

JWK Set은 자주 조회하면 안 된다. 검증할 때마다 외부 호출을 하면 발급자 서버가 부담된다. 캐싱은 필수다. `jwks-rsa`는 기본적으로 캐싱과 rate limit을 지원한다.

## jwt.io 디버깅

[jwt.io](https://jwt.io)는 JWT를 디코딩하고 검증하는 웹 도구다. 운영 중인 토큰 디버깅에 자주 쓴다.

### 토큰 구조 확인

토큰 문자열을 붙여넣으면 헤더와 페이로드가 디코딩되어 보인다. 이걸로 확인할 수 있는 것들:

- `alg`이 의도한 값인가
- `kid`가 있으면 어느 키로 서명되었는지
- `exp`가 너무 길지 않은가
- `iss`, `aud`가 올바른가
- 의도하지 않은 클레임이 들어가 있지 않은가
- 민감 정보가 페이로드에 노출되어 있지 않은가

### 서명 검증

비밀키나 공개키를 넣으면 jwt.io가 서명을 검증한다. 운영 환경 비밀키를 jwt.io에 넣으면 안 된다. 절대 안 된다. jwt.io는 외부 서비스고, 입력값이 어디로 가는지 보장할 수 없다.

검증이 필요하면 로컬 도구를 써야 한다. `jwt-cli` 같은 CLI 툴이 있다.

```bash
jwt decode <token>
```

또는 직접 OpenSSL로 검증할 수도 있다.

### 디버깅 시나리오

흔히 마주치는 상황들이다.

**"토큰이 invalid signature로 거부된다"**

jwt.io에 토큰을 붙여넣고 서명 부분에 키를 넣어본다. 검증이 통과하면 발급자 키와 검증자 키가 다른 것이다. 키 회전 중인지, 환경별로 다른 키를 쓰는지 확인.

**"방금 발급한 토큰인데 expired 에러"**

`iat`과 `exp`를 확인한다. 발급 서버 시간과 현재 시간 차이를 본다. NTP 동기화가 깨졌을 수도 있고, 만료 시간을 너무 짧게 설정했을 수도 있다.

**"개발 환경에서는 되는데 운영에서 안 된다"**

`iss`와 `aud`가 환경별로 다른 경우. 검증 로직에서 issuer/audience 체크를 환경 변수로 넣지 않으면 자주 발생한다.

**"가끔씩 invalid signature"**

키 회전 중일 가능성이 높다. JWK Set의 `kid`와 토큰의 `kid`가 일치하는지, 검증자가 캐싱한 JWK Set이 오래되어 새 키를 모르는 건 아닌지 확인.

**"페이로드에 들어 있어야 할 클레임이 안 보인다"**

발급 코드에서 클레임이 누락되었거나, 라이브러리 버전 차이로 인코딩이 다를 수 있다. 두 환경에서 발급한 토큰을 jwt.io에서 비교하면 빠르다.

## 정리

JWT는 도구일 뿐이다. 어떤 시스템에는 잘 맞지만 어떤 시스템에는 세션이 더 낫다. stateless가 필요한지, 즉시 무효화가 얼마나 중요한지, 마이크로서비스 환경인지 등을 따져봐야 한다.

쓰기로 했다면 검증 옵션을 빠짐없이 명시하고, 알고리즘 화이트리스트를 강제하고, 키 관리 방안을 미리 설계해라. 라이브러리에만 의존하지 말고 검증 단계가 어떻게 동작하는지 이해해야 한다. 토큰 저장 위치도 처음부터 신경 써야 한다. localStorage에 한 번 넣으면 나중에 옮기기 까다롭다.
