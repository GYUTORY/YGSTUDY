---
title: JWT 구현 및 보안 전략
tags: [framework, node, jwt, authentication, security, token, refresh-token]
updated: 2025-11-27
---

# 🔐 JWT 구현 및 보안 전략

## 📌 개요

> **JWT (JSON Web Token)**는 클레임 기반의 토큰 인증 방식으로, 상태를 유지하지 않는(stateless) 인증 메커니즘을 제공합니다.

### 🎯 JWT의 구조

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

### 📊 JWT vs 세션 비교

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

## 🏗️ JWT 구조

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

## 🔧 JWT 구현

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

## 🔄 Access Token vs Refresh Token

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

## 🛡️ JWT 보안 취약점 및 대응

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
// ❌ 취약한 코드
jwt.verify(token, secret); // 알고리즘 검증 없음

// 공격자가 "none" 알고리즘으로 토큰 생성
// 서버가 알고리즘을 검증하지 않으면 통과
```

#### 대응 방법

```javascript
// ✅ 안전한 코드
jwt.verify(token, secret, {
  algorithms: ['HS256'] // 명시적으로 알고리즘 지정
});

// 또는
const decoded = jwt.decode(token, { complete: true });
if (decoded.header.alg !== 'HS256') {
  throw new Error('Invalid algorithm');
}
```

### 2. Secret 키 관리

#### ❌ 취약한 방법

```javascript
// 하드코딩된 Secret
const secret = 'my-secret-key';

// 약한 Secret
const secret = '123456';

// 코드에 포함
const secret = process.env.JWT_SECRET || 'default-secret';
```

#### ✅ 안전한 방법

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
// ✅ 적절한 만료 시간
const accessToken = jwt.sign(payload, secret, {
  expiresIn: '15m' // 짧은 만료 시간
});

const refreshToken = jwt.sign(payload, refreshSecret, {
  expiresIn: '7d' // 긴 만료 시간
});

// ❌ 만료 시간 없음
const token = jwt.sign(payload, secret); // 위험!
```

### 5. 클레임 검증

```javascript
// ✅ 모든 클레임 검증
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

## 🔒 보안 모범 사례

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

## 🎯 JWT vs 세션 선택 가이드

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
| **확장성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **토큰 크기** | 큼 | 작음 |
| **즉시 취소** | 어려움 | 쉬움 |
| **서버 부하** | 낮음 | 높음 |
| **크로스 도메인** | 용이 | 제한적 |

## 🔧 JWT 트러블슈팅

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

## 💡 5년차 개발자를 위한 고급 전략

**1. 토큰 갱신 전략:**
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

## 📝 결론

JWT는 강력한 인증 메커니즘이지만, 올바르게 구현하지 않으면 보안 취약점이 발생할 수 있습니다.

### 핵심 포인트

- ✅ **이중 토큰 구조**: Access Token + Refresh Token
- ✅ **토큰 블랙리스트**: 로그아웃 및 토큰 무효화
- ✅ **보안 강화**: 알고리즘 명시, 강력한 Secret, 클레임 검증
- ✅ **HTTPS 사용**: 프로덕션 환경 필수
- ✅ **적절한 만료 시간**: Access Token은 짧게, Refresh Token은 길게

### 보안 체크리스트

1. ✅ 알고리즘 명시적으로 지정
2. ✅ 강력한 Secret 키 사용 (최소 32자)
3. ✅ 적절한 만료 시간 설정
4. ✅ 모든 클레임 검증
5. ✅ HTTPS 사용 (프로덕션)
6. ✅ HttpOnly Cookie 사용 (가능한 경우)
7. ✅ 토큰 블랙리스트 구현
8. ✅ Secret 키 로테이션 계획

### 관련 문서

- [보안 모범 사례](../보안/Node.js_보안_모범사례.md) - 전체 보안 전략
- [API 설계 원칙](../API/API_설계_원칙.md) - 인증이 포함된 API 설계
- [Rate Limiting](../API/Rate_Limiting.md) - 인증 시도 제한
- [에러 핸들링](../에러_핸들링/에러_핸들링_전략.md) - 인증 에러 처리

