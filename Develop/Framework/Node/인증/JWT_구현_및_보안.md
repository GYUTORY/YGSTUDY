---
title: JWT 구현 및 보안
tags: [nodejs, jwt, auth, security]
updated: 2025-12-27
---

# JWT 구현 및 보안

## 개요

JWT (JSON Web Token)는 클레임 기반의 토큰 인증 방식으로, 상태를 유지하지 않는(stateless) 인증 메커니즘을 제공합니다.

### JWT의 구조

```mermaid
mindmap
  root((JWT))
    구조
      Header
      Payload
      Signature
    특징
      Stateless
      Self-contained
      Compact
    사용 사례
      API 인증
      Single Sign-On
      정보 교환
```

### JWT vs 세션 비교

```mermaid
graph TB
    subgraph "세션 기반"
        S1[클라이언트] -->|로그인| S2[서버]
        S2 -->|세션 ID| S3[세션 저장소]
        S2 -->|세션 ID| S1
        S1 -->|요청 + 세션 ID| S2
        S2 -->|세션 확인| S3
    end
    
    subgraph "JWT 기반"
        J1[클라이언트] -->|로그인| J2[서버]
        J2 -->|JWT 토큰| J1
        J1 -->|요청 + JWT| J2
        J2 -->|토큰 검증| J2
    end
    
    style S3 fill:#ffcdd2
    style J2 fill:#c8e6c9
```

#### 비교표

| 항목 | 세션 | JWT |
|------|------|-----|
| **상태 저장** | 서버에 저장 필요 | 상태 없음 |
| **확장성** | 세션 저장소 필요 | 높음 |
| **크로스 도메인** | 제한적 | 용이 |
| **토큰 크기** | 작음 (세션 ID) | 큼 (모든 정보 포함) |
| **취소** | 즉시 가능 | 어려움 |
| **보안** | 서버 관리 | 클라이언트 관리 |

## JWT 구조

### JWT 구성 요소

```mermaid
graph LR
    A[JWT] --> B[Header]
    A --> C[Payload]
    A --> D[Signature]
    
    B --> E[알고리즘 정보]
    C --> F[클레임 정보]
    D --> G[서명 검증]
    
    style A fill:#4fc3f7
    style B fill:#66bb6a
    style C fill:#ff9800
    style D fill:#ef5350,color:#fff
```

#### JWT 구조 예시

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxMjMiLCJ1c2VybmFtZSI6ImpvaG4iLCJpYXQiOjE2MDAwMDAwMDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

**분해:**
- **Header**: `{"alg":"HS256","typ":"JWT"}`
- **Payload**: `{"userId":"123","username":"john","iat":1600000000}`
- **Signature**: `HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload), secret)`

이 "분해"를 **비밀키 없이 누구나 할 수 있다**는 점이 JWT 를 다룰 때 가장 먼저 새겨야 할 사실이다. 위 예시 토큰을 그대로 넣어보면:

```
$ node -e "console.log(require('jsonwebtoken').decode('eyJhbGciOi...'))"
{ userId: '123', username: 'john', iat: 1600000000 }
```

Base64 는 **인코딩이지 암호화가 아니다.** 서명은 "내용이 변조되지 않았음"을 보장할 뿐, "내용을 못 읽음"을 보장하지 않는다. 그래서 페이로드에 넣으면 안 되는 것이 분명하다.

- 주민번호·전화번호·이메일 같은 개인정보
- 내부 시스템 식별자, 권한 정책의 상세 내용
- "이 사람은 무료 체험 사용자" 처럼 노출되면 곤란한 비즈니스 상태

토큰은 브라우저 개발자 도구, 프록시 로그, APM 트레이스, CDN 액세스 로그에 그대로 남는다. **`jwt.io` 에 붙여넣는 순간 남의 서버에도 남는다.** 페이로드에는 식별자와 권한 코드처럼 노출돼도 되는 최소한만 담고, 나머지는 그 식별자로 서버에서 조회한다.

### Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- **alg**: 서명 알고리즘 (HS256, RS256 등)
- **typ**: 토큰 타입 (항상 "JWT")

### Payload (클레임)

```json
{
  "userId": "123",
  "username": "john",
  "email": "john@example.com",
  "iat": 1600000000,
  "exp": 1600003600,
  "iss": "api-server"
}
```

#### 클레임 타입

| 클레임 | 설명 | 필수 여부 |
|--------|------|----------|
| **iss** (Issuer) | 토큰 발급자 | 선택 |
| **sub** (Subject) | 토큰 주제 | 선택 |
| **aud** (Audience) | 토큰 수신자 | 선택 |
| **exp** (Expiration) | 만료 시간 | 권장 |
| **iat** (Issued At) | 발급 시간 | 권장 |
| **jti** (JWT ID) | 토큰 고유 ID | 선택 |

## JWT 구현

### 기본 구현

```javascript
const jwt = require('jsonwebtoken');

// JWT 생성
function generateToken(payload, secret, options = {}) {
  return jwt.sign(payload, secret, {
    expiresIn: options.expiresIn || '1h',
    issuer: options.issuer || 'api-server',
    audience: options.audience || 'api-client'
  });
}

// JWT 검증
function verifyToken(token, secret) {
  try {
    return jwt.verify(token, secret, {
      issuer: 'api-server',
      audience: 'api-client'
    });
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new Error('Token has expired');
    }
    if (error.name === 'JsonWebTokenError') {
      throw new Error('Invalid token');
    }
    throw error;
  }
}

// 사용 예시
const payload = {
  userId: '123',
  username: 'john',
  email: 'john@example.com'
};

const token = generateToken(payload, process.env.JWT_SECRET, {
  expiresIn: '1h'
});

const decoded = verifyToken(token, process.env.JWT_SECRET);
```

### Express 미들웨어

```javascript
const jwt = require('jsonwebtoken');

// JWT 인증 미들웨어
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }
  
  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      if (err.name === 'TokenExpiredError') {
        return res.status(401).json({ error: 'Token expired' });
      }
      return res.status(403).json({ error: 'Invalid token' });
    }
    
    req.user = user;
    next();
  });
}

// 사용 예시
app.get('/protected', authenticateToken, (req, res) => {
  res.json({ message: 'Protected resource', user: req.user });
});
```

## Access Token vs Refresh Token

### 이중 토큰 구조

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant S as 서버
    
    C->>S: 로그인 요청
    S-->>C: Access Token (15분)<br/>Refresh Token (7일)
    
    Note over C,S: 정상 사용 중
    C->>S: API 요청 (Access Token)
    S-->>C: 응답
    
    Note over C,S: Access Token 만료
    C->>S: API 요청 (만료된 Access Token)
    S-->>C: 401 Unauthorized
    
    C->>S: 토큰 갱신 (Refresh Token)
    S-->>C: 새로운 Access Token
    
    C->>S: API 요청 (새 Access Token)
    S-->>C: 응답
```

### 이중 토큰 구현

```javascript
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

class TokenManager {
  constructor() {
    this.accessTokenSecret = process.env.JWT_ACCESS_SECRET;
    this.refreshTokenSecret = process.env.JWT_REFRESH_SECRET;
    this.accessTokenExpiry = '15m';
    this.refreshTokenExpiry = '7d';
    this.refreshTokens = new Set(); // 실제로는 Redis 사용 권장
  }
  
  // Access Token 생성
  generateAccessToken(payload) {
    return jwt.sign(payload, this.accessTokenSecret, {
      expiresIn: this.accessTokenExpiry,
      issuer: 'api-server',
      audience: 'api-client'
    });
  }
  
  // Refresh Token 생성
  generateRefreshToken(payload) {
    const token = jwt.sign(payload, this.refreshTokenSecret, {
      expiresIn: this.refreshTokenExpiry,
      issuer: 'api-server',
      audience: 'api-client'
    });
    
    // Refresh Token 저장 (실제로는 DB 또는 Redis)
    this.refreshTokens.add(token);
    
    return token;
  }
  
  // 토큰 쌍 생성
  generateTokenPair(payload) {
    return {
      accessToken: this.generateAccessToken(payload),
      refreshToken: this.generateRefreshToken(payload)
    };
  }
  
  // Access Token 검증
  verifyAccessToken(token) {
    try {
      return jwt.verify(token, this.accessTokenSecret, {
        issuer: 'api-server',
        audience: 'api-client'
      });
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        throw new Error('Access token expired');
      }
      throw new Error('Invalid access token');
    }
  }
  
  // Refresh Token 검증 및 갱신
  async refreshAccessToken(refreshToken) {
    // Refresh Token 검증
    let decoded;
    try {
      decoded = jwt.verify(refreshToken, this.refreshTokenSecret, {
        issuer: 'api-server',
        audience: 'api-client'
      });
    } catch (error) {
      throw new Error('Invalid refresh token');
    }
    
    // Refresh Token이 저장소에 있는지 확인
    if (!this.refreshTokens.has(refreshToken)) {
      throw new Error('Refresh token not found');
    }
    
    // 새로운 Access Token 생성
    const newPayload = {
      userId: decoded.userId,
      username: decoded.username,
      email: decoded.email
    };
    
    const newAccessToken = this.generateAccessToken(newPayload);
    
    return newAccessToken;
  }
  
  // Refresh Token 무효화
  revokeRefreshToken(refreshToken) {
    this.refreshTokens.delete(refreshToken);
  }
  
  // 모든 Refresh Token 무효화 (로그아웃)
  revokeAllRefreshTokens(userId) {
    // 실제로는 사용자별로 관리
    // this.refreshTokens.forEach(token => {
    //   const decoded = jwt.decode(token);
    //   if (decoded.userId === userId) {
    //     this.refreshTokens.delete(token);
    //   }
    // });
  }
}

// 사용 예시
const tokenManager = new TokenManager();

// 로그인
app.post('/login', async (req, res) => {
  const { username, password } = req.body;
  
  // 사용자 인증
  const user = await authenticateUser(username, password);
  
  if (!user) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  
  // 토큰 생성
  const payload = {
    userId: user.id,
    username: user.username,
    email: user.email
  };
  
  const { accessToken, refreshToken } = tokenManager.generateTokenPair(payload);
  
  res.json({
    accessToken,
    refreshToken
  });
});

// 토큰 갱신
app.post('/refresh', async (req, res) => {
  const { refreshToken } = req.body;
  
  if (!refreshToken) {
    return res.status(401).json({ error: 'Refresh token required' });
  }
  
  try {
    const newAccessToken = await tokenManager.refreshAccessToken(refreshToken);
    res.json({ accessToken: newAccessToken });
  } catch (error) {
    res.status(401).json({ error: error.message });
  }
});
```

## 🚫 토큰 블랙리스트

### 블랙리스트 개념

```mermaid
graph TD
    A[토큰 무효화 요청] --> B[토큰을 블랙리스트에 추가]
    B --> C[Redis/DB에 저장]
    C --> D[토큰 검증 시 확인]
    D --> E{블랙리스트에 있음?}
    E -->|예| F[접근 거부]
    E -->|아니오| G[정상 처리]
    
    style B fill:#ef5350,color:#fff
    style F fill:#ef5350,color:#fff
    style G fill:#66bb6a
```

### 블랙리스트 구현

```javascript
const redis = require('redis');
const jwt = require('jsonwebtoken');

class TokenBlacklist {
  constructor() {
    this.redisClient = redis.createClient({
      url: process.env.REDIS_URL
    });
    this.redisClient.connect();
  }
  
  // 토큰 블랙리스트 추가
  async addToken(token, expirySeconds = 3600) {
    const decoded = jwt.decode(token);
    const expiry = decoded.exp - Math.floor(Date.now() / 1000);
    
    if (expiry > 0) {
      await this.redisClient.setEx(
        `blacklist:${token}`,
        expiry,
        '1'
      );
    }
  }
  
  // 토큰이 블랙리스트에 있는지 확인
  async isBlacklisted(token) {
    const result = await this.redisClient.get(`blacklist:${token}`);
    return result === '1';
  }
  
  // 사용자의 모든 토큰 무효화
  async revokeUserTokens(userId) {
    // 실제로는 사용자별 토큰을 추적해야 함
    // 예: userId별 토큰 목록을 Redis에 저장
    const tokenKey = `user:${userId}:tokens`;
    const tokens = await this.redisClient.sMembers(tokenKey);
    
    for (const token of tokens) {
      await this.addToken(token);
    }
    
    await this.redisClient.del(tokenKey);
  }
}

// 인증 미들웨어에 통합
const blacklist = new TokenBlacklist();

async function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }
  
  // 블랙리스트 확인
  const isBlacklisted = await blacklist.isBlacklisted(token);
  if (isBlacklisted) {
    return res.status(401).json({ error: 'Token has been revoked' });
  }
  
  // 토큰 검증
  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    
    req.user = user;
    next();
  });
}

// 로그아웃
app.post('/logout', authenticateToken, async (req, res) => {
  const token = req.headers['authorization'].split(' ')[1];
  
  await blacklist.addToken(token);
  
  res.json({ message: 'Logged out successfully' });
});
```

#### `addToken` 은 조건에 따라 아무 일도 하지 않는다

```javascript
async addToken(token, expirySeconds = 3600) {
  const decoded = jwt.decode(token);
  const expiry = decoded.exp - Math.floor(Date.now() / 1000);
  if (expiry > 0) { /* Redis 저장 */ }
}
```

두 가지가 걸린다.

**1. `exp` 없는 토큰은 조용히 무시된다.** `expiresIn` 을 안 준 토큰은 `exp` 가 없고, `undefined - 숫자` 는 `NaN` 이다. `NaN > 0` 은 언제나 false 다.

```
exp 없는 토큰 decode: {"userId":"1","iat":1786683723}
expiry = decoded.exp - now = NaN / (expiry > 0) = false
```

**만료 없는 토큰은 영원히 유효한 데다 로그아웃도 안 된다.** 가장 위험한 토큰이 정확히 블랙리스트를 빠져나간다. 에러도 안 나서 `/logout` 은 200 을 돌려주고, 사용자는 로그아웃됐다고 믿는다.

**2. 잘못된 토큰이 오면 500 이 난다.** `jwt.decode` 는 파싱 실패 시 예외가 아니라 `null` 을 반환한다.

```
jwt.decode("garbage") = null
decoded.exp 접근 → TypeError: Cannot read properties of null (reading 'exp')
```

여기서는 `authenticateToken` 을 먼저 통과하니 대부분 괜찮지만, 다른 경로에서 이 메서드를 부르면 그대로 터진다.

그리고 `expirySeconds = 3600` 파라미터는 **선언만 되고 아무 데도 안 쓰인다.** 기본값이 있어 호출부는 멀쩡해 보이고, "TTL 을 조절할 수 있구나"라고 읽게 만든다. 안 쓸 거면 지운다.

```javascript
// ✓ 고친 버전
async addToken(token) {
  const decoded = jwt.decode(token);
  if (!decoded) throw new Error('디코딩할 수 없는 토큰');
  const ttl = decoded.exp ? decoded.exp - Math.floor(Date.now() / 1000) : null;
  if (ttl === null) throw new Error('exp 없는 토큰 — 발급 정책을 먼저 고친다');
  if (ttl > 0) await this.redisClient.setEx(`blacklist:${token}`, ttl, '1');
}
```

블랙리스트 자체에 대해서도 한마디. 토큰 전체를 Redis 키로 쓰면 키가 길어지고, 같은 사용자의 토큰을 한꺼번에 지울 수도 없다. `jti` 를 키로 쓰면 짧아지고, `user:{id}:jti` 집합을 함께 두면 전체 로그아웃이 가능해진다. 위 `SecureJWTManager` 가 `jwtid` 를 넣는 이유가 이것인데, 정작 블랙리스트 쪽은 토큰 문자열을 쓰고 있어 둘이 안 맞물린다.

## JWT 보안 취약점 및 대응

### 주요 보안 취약점

```mermaid
mindmap
  root((JWT 보안 취약점))
    알고리즘
      None 알고리즘
      약한 알고리즘
      알고리즘 변경 공격
    토큰 관리
      토큰 탈취
      XSS 공격
      CSRF 공격
    구현 오류
      Secret 노출
      만료 시간 미설정
      클레임 검증 누락
```

### 1. 알고리즘 변경 공격 (Algorithm Confusion)

#### 공격 시나리오

```javascript
// 취약한 예시
jwt.verify(token, secret); // 알고리즘 검증 없음

// 공격자가 "none" 알고리즘으로 토큰 생성
// 서버가 알고리즘을 검증하지 않으면 통과
```

#### 대응 방법

```javascript
// 안전한 예시
jwt.verify(token, secret, {
  algorithms: ['HS256'] // 명시적으로 알고리즘 지정
});

// 또는
const decoded = jwt.decode(token, { complete: true });
if (decoded.header.alg !== 'HS256') {
  throw new Error('Invalid algorithm');
}
```

#### 다만 `jsonwebtoken` 9.x 는 이미 막아준다 — 직접 확인해 볼 것

위 "취약한 예시"는 옛 라이브러리 기준이다. 지금 버전에서 `alg: none` 토큰을 만들어 던져보면 통과하지 않는다.

```javascript
const b64 = o => Buffer.from(JSON.stringify(o)).toString('base64url');
const noneToken = b64({alg:'none', typ:'JWT'}) + '.' + b64({userId:'admin', role:'admin'}) + '.';
```

```
verify(token, secret)      → JsonWebTokenError: jwt signature is required
verify(token, "")          → JsonWebTokenError: please specify "none" in "algorithms" to verify unsigned tokens
verify(algorithms:['none']) → { userId: 'admin', role: 'admin' }
```

(jsonwebtoken 9.0.3)

**직접 `algorithms: ['none']` 을 켜야만 통과한다.** HS/RS 혼동 공격도 마찬가지다. RSA 공개키를 HMAC 키로 삼아 HS256 으로 서명한 토큰을 만들어 검증시켜 보면:

```
정상 RS256 검증: user
위조 토큰, algorithms 미지정  → JsonWebTokenError: invalid algorithm
위조 토큰, algorithms:['RS256'] → JsonWebTokenError: invalid algorithm
```

키의 종류를 보고 허용 알고리즘을 좁히기 때문이다.

그렇다고 `algorithms` 를 안 써도 된다는 뜻은 아니다. **의존하는 지점이 라이브러리 버전으로 옮겨갈 뿐**이다. 버전을 올리거나 다른 언어의 라이브러리로 옮기면 보장이 사라진다. 명시하는 비용은 한 줄이니 그냥 쓴다. 중요한 건 "우리 스택에서 실제로 어떻게 동작하는지 한 번은 쳐봤는가"다.

### 2. Secret 키 관리

#### 취약한 방법

```javascript
// 하드코딩된 Secret
const secret = 'my-secret-key';

// 약한 Secret
const secret = '123456';

// 코드에 포함
const secret = process.env.JWT_SECRET || 'default-secret';
```

#### 안전한 방법

```javascript
// 강력한 Secret 생성
const crypto = require('crypto');
const secret = crypto.randomBytes(64).toString('hex');

// 환경 변수로 관리
const secret = process.env.JWT_SECRET;
if (!secret) {
  throw new Error('JWT_SECRET environment variable is required');
}

// Secret 로테이션
class SecretManager {
  constructor() {
    this.currentSecret = process.env.JWT_SECRET;
    this.previousSecret = process.env.JWT_PREVIOUS_SECRET;
  }
  
  verify(token) {
    try {
      return jwt.verify(token, this.currentSecret);
    } catch (error) {
      // 이전 Secret으로도 시도 (로테이션 기간)
      if (this.previousSecret) {
        return jwt.verify(token, this.previousSecret);
      }
      throw error;
    }
  }
}
```

### 3. 토큰 탈취 방지

#### HTTPS 사용

```javascript
// 프로덕션에서는 항상 HTTPS 사용
if (process.env.NODE_ENV === 'production') {
  app.use((req, res, next) => {
    if (req.header('x-forwarded-proto') !== 'https') {
      return res.redirect(`https://${req.header('host')}${req.url}`);
    }
    next();
  });
}
```

#### HttpOnly Cookie 사용

```javascript
// JWT를 HttpOnly Cookie에 저장 (XSS 방지)
app.post('/login', async (req, res) => {
  const { accessToken, refreshToken } = await generateTokens(user);
  
  res.cookie('accessToken', accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 15 * 60 * 1000 // 15분
  });
  
  res.cookie('refreshToken', refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000 // 7일
  });
  
  res.json({ message: 'Login successful' });
});
```

### 4. 토큰 만료 시간 설정

```javascript
// 적절한 예시: 만료 시간 설정
const accessToken = jwt.sign(payload, secret, {
  expiresIn: '15m' // 짧은 만료 시간
});

const refreshToken = jwt.sign(payload, refreshSecret, {
  expiresIn: '7d' // 긴 만료 시간
});

// 나쁜 예시: 만료 시간 없음
const token = jwt.sign(payload, secret); // 위험!
```

만료를 넣을 때 `expiresIn` 과 페이로드의 `exp` 를 같이 주면 서명 자체가 거부된다.

```
$ node -e "jwt.sign({userId:'1', exp: now+60}, 'k', {expiresIn:'1h'})"
Error: Bad "options.expiresIn" option the payload already has an "exp" property.
```

기존 토큰의 페이로드를 그대로 복사해 새 토큰을 만들 때 잘 걸린다. `jwt.verify` 가 돌려준 객체에는 `iat`·`exp` 가 이미 들어 있기 때문이다. 위 `refreshAccessToken` 이 `decoded` 를 통째로 넘기지 않고 `userId`/`username`/`email` 만 골라 새 페이로드를 만드는 게 바로 이 때문이다 — **의도적인 코드지 장식이 아니다.**

만료가 없는 토큰의 진짜 문제는 "오래 유효하다"가 아니라 **회수할 방법이 사실상 없다**는 것이다. 앞서 본 것처럼 블랙리스트도 `exp` 를 기준으로 TTL 을 잡기 때문에 `exp` 가 없으면 넣을 수조차 없다. 비밀키를 갈아치우는 것 말고는 손쓸 수단이 남지 않는다.

### 5. 클레임 검증

```javascript
// 좋은 예시: 모든 클레임 검증
function verifyToken(token, secret) {
  const decoded = jwt.verify(token, secret, {
    issuer: 'api-server',
    audience: 'api-client',
    algorithms: ['HS256']
  });
  
  // 추가 검증
  if (!decoded.userId) {
    throw new Error('Invalid token: missing userId');
  }
  
  if (decoded.role && !['user', 'admin'].includes(decoded.role)) {
    throw new Error('Invalid token: invalid role');
  }
  
  return decoded;
}
```

## 보안 모범 사례

### 보안 체크리스트

```mermaid
graph TD
    A[JWT 보안 체크리스트] --> B[알고리즘 명시]
    A --> C[강력한 Secret]
    A --> D[적절한 만료 시간]
    A --> E[클레임 검증]
    A --> F[HTTPS 사용]
    A --> G[HttpOnly Cookie]
    A --> H[토큰 블랙리스트]
    
    style A fill:#4fc3f7
    style B fill:#66bb6a
    style C fill:#66bb6a
    style D fill:#66bb6a
```

### 완전한 보안 구현

```javascript
const jwt = require('jsonwebtoken');
const crypto = require('crypto');

class SecureJWTManager {
  constructor() {
    this.accessSecret = this.getSecret('JWT_ACCESS_SECRET');
    this.refreshSecret = this.getSecret('JWT_REFRESH_SECRET');
    this.algorithm = 'HS256';
    this.issuer = 'api-server';
    this.audience = 'api-client';
  }
  
  getSecret(envVar) {
    const secret = process.env[envVar];
    if (!secret) {
      throw new Error(`${envVar} environment variable is required`);
    }
    if (secret.length < 32) {
      throw new Error(`${envVar} must be at least 32 characters`);
    }
    return secret;
  }
  
  generateAccessToken(payload) {
    return jwt.sign(payload, this.accessSecret, {
      algorithm: this.algorithm,
      expiresIn: '15m',
      issuer: this.issuer,
      audience: this.audience,
      jwtid: crypto.randomUUID() // 고유 ID
    });
  }
  
  generateRefreshToken(payload) {
    return jwt.sign(payload, this.refreshSecret, {
      algorithm: this.algorithm,
      expiresIn: '7d',
      issuer: this.issuer,
      audience: this.audience,
      jwtid: crypto.randomUUID()
    });
  }
  
  verifyAccessToken(token) {
    try {
      return jwt.verify(token, this.accessSecret, {
        algorithms: [this.algorithm],
        issuer: this.issuer,
        audience: this.audience
      });
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        throw new Error('Access token expired');
      }
      if (error.name === 'JsonWebTokenError') {
        throw new Error('Invalid access token');
      }
      throw error;
    }
  }
  
  verifyRefreshToken(token) {
    try {
      return jwt.verify(token, this.refreshSecret, {
        algorithms: [this.algorithm],
        issuer: this.issuer,
        audience: this.audience
      });
    } catch (error) {
      throw new Error('Invalid refresh token');
    }
  }
}

// Express 미들웨어
const jwtManager = new SecureJWTManager();

function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }
  
  try {
    const decoded = jwtManager.verifyAccessToken(token);
    req.user = decoded;
    next();
  } catch (error) {
    if (error.message.includes('expired')) {
      return res.status(401).json({ error: 'Token expired' });
    }
    return res.status(403).json({ error: 'Invalid token' });
  }
}
```

## JWT vs 세션 선택 가이드

### 의사결정 트리

```mermaid
flowchart TD
    START([인증 방식 선택]) --> Q1{확장성<br/>중요한가?}
    
    Q1 -->|예| Q2{상태 관리<br/>필요한가?}
    Q1 -->|아니오| Q3{즉시 취소<br/>필요한가?}
    
    Q2 -->|아니오| JWT[JWT]
    Q2 -->|예| SESSION[세션]
    
    Q3 -->|예| SESSION
    Q3 -->|아니오| JWT
    
    JWT --> JWT_REASON[Stateless<br/>확장성 우수<br/>취소 어려움]
    SESSION --> SESSION_REASON[Stateful<br/>즉시 취소<br/>확장성 제한]
    
    style JWT fill:#66bb6a
    style SESSION fill:#4fc3f7
```

### JWT vs 세션 비교표

| 기준 | JWT | 세션 |
|------|-----|------|
| **상태 관리** | Stateless | Stateful |
| **확장성** | 5 | 3 |
| **토큰 크기** | 큼 | 작음 |
| **즉시 취소** | 어려움 | 쉬움 |
| **서버 부하** | 낮음 | 높음 |
| **크로스 도메인** | 용이 | 제한적 |

## JWT 트러블슈팅

### 일반적인 JWT 문제와 해결책

**1. 토큰 갱신 문제:**

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| **토큰 만료 시 재로그인** | Refresh Token 부재 | Refresh Token 구현 |
| **토큰 갱신 실패** | Refresh Token 만료 | Refresh Token 연장 로직 |
| **동시 갱신 충돌** | Race Condition | 토큰 갱신 락 사용 |

**2. 보안 취약점:**

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| **토큰 탈취** | HTTPS 미사용 | HTTPS 필수 |
| **XSS 공격** | localStorage 저장 | httpOnly 쿠키 사용 |
| **CSRF 공격** | 쿠키 사용 시 | CSRF 토큰 추가 |

## 고급 활용

**1. 토큰 갱신:**
- Refresh Token을 사용하여 Access Token 자동 갱신
- 토큰 갱신 시 Race Condition 방지
- Refresh Token Rotation으로 보안 강화

**2. 비용 고려사항:**
- JWT는 Stateless로 서버 부하 감소
- 세션은 세션 저장소 비용 필요
- 토큰 크기로 인한 네트워크 비용 고려

**3. 팀 협업 관점:**
- 토큰 구조 표준화
- 토큰 검증 로직 공유
- 보안 취약점 점검 체크리스트

## 요약
JWT는 강력한 인증 메커니즘이지만, 올바르게 구현하지 않으면 보안 취약점이 발생할 수 있습니다.

### 주요 내용

- **이중 토큰 구조**: Access Token + Refresh Token
- **토큰 블랙리스트**: 로그아웃 및 토큰 무효화
- **보안 강화**: 알고리즘 명시, 강력한 Secret, 클레임 검증
- **HTTPS 사용**: 프로덕션 환경 필수
- **적절한 만료 시간**: Access Token은 짧게, Refresh Token은 길게

### 보안 체크리스트

1. 알고리즘 명시적으로 지정
2. 강력한 Secret 키 사용 (최소 32자)
3. 적절한 만료 시간 설정
4. 모든 클레임 검증
5. HTTPS 사용 (프로덕션)
6. HttpOnly Cookie 사용 (가능한 경우)
7. 토큰 블랙리스트 구현
8. Secret 키 로테이션 계획

### 관련 문서

- [보안 모범 사례](../보안/Node.js_보안_모범사례.md) - 전체 보안
- [API 설계 원칙](../API/API_설계_원칙.md) - 인증이 포함된 API 설계
- [Rate Limiting](../API/Rate_Limiting.md) - 인증 시도 제한
- [에러 핸들링](../에러_핸들링/에러_핸들링_전략.md) - 인증 에러 처리

---
이 문서는 [인증과 토큰 허브](../../../_hub/인증과_토큰.md)의 일부입니다.

