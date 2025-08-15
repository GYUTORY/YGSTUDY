---
title: JWT (JSON Web Token) 완벽 가이드
tags: [auth, jwt, json-web-token, authentication, authorization]
updated: 2024-12-19
---

# JWT (JSON Web Token) 완벽 가이드

## 배경

### JWT란?
JWT(JSON Web Token)는 JSON 형식으로 데이터를 안전하게 전송하기 위한 토큰 기반 인증 방식입니다. 웹 애플리케이션에서 사용자 인증 및 정보 교환에 널리 사용되며, 서버의 상태를 유지하지 않고도 인증 정보를 관리할 수 있습니다.

### JWT의 필요성
- **상태 없는 인증**: 서버가 세션을 저장할 필요 없이 토큰만으로 인증
- **확장성**: 마이크로서비스 아키텍처에서 서비스 간 인증
- **모바일 지원**: 모바일 앱에서 효율적인 인증 처리
- **단일 사인온**: 여러 서비스에서 동일한 토큰으로 인증
- **API 인증**: RESTful API에서 표준적인 인증 방식

### 기본 개념
- **토큰 기반 인증**: 상태를 유지하지 않고도 인증 정보 관리
- **자기 포함 토큰**: 토큰 자체에 모든 정보를 포함
- **서명(Signature)**: 데이터 위변조 방지를 위한 디지털 서명
- **클레임(Claim)**: 토큰에 포함된 사용자 정보나 권한

## 핵심

### 1. JWT 구조

#### JWT 구성 요소
JWT는 Header, Payload, Signature로 구성된 3개의 JSON 객체를 `.`으로 구분하여 Base64 URL 인코딩한 문자열입니다.

```javascript
// JWT 구조 예시
const jwtStructure = {
    header: {
        alg: 'HS256',  // 서명 알고리즘
        typ: 'JWT'     // 토큰 타입
    },
    payload: {
        sub: 'user123',           // 주체 (사용자 ID)
        name: '김철수',           // 사용자 이름
        role: 'admin',            // 사용자 역할
        iat: 1516239022,          // 발급 시간
        exp: 1516242622           // 만료 시간
    },
    signature: 'HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload), secret)'
};

// 실제 JWT 토큰 예시
const jwtToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwibmFtZSI6Iuq5gO2ZlOyIrCIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTUxNjIzOTAyMiwiZXhwIjoxNTE2MjQyNjIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
```

#### Header (헤더)
```javascript
// JWT 헤더 예시
const header = {
    alg: 'HS256',  // HMAC SHA256 알고리즘
    typ: 'JWT'     // 토큰 타입
};

// Base64 URL 인코딩된 헤더
const encodedHeader = btoa(JSON.stringify(header))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
```

#### Payload (페이로드)
```javascript
// JWT 페이로드 예시
const payload = {
    // 등록된 클레임 (Registered Claims)
    iss: 'my-app.com',           // 발급자
    sub: 'user123',              // 주체
    aud: 'api.my-app.com',       // 대상
    exp: Math.floor(Date.now() / 1000) + 3600,  // 만료 시간 (1시간 후)
    nbf: Math.floor(Date.now() / 1000),         // 활성화 시간
    iat: Math.floor(Date.now() / 1000),         // 발급 시간
    jti: 'unique-token-id',      // 토큰 ID
    
    // 공개 클레임 (Public Claims)
    name: '김철수',
    email: 'kim@example.com',
    
    // 비공개 클레임 (Private Claims)
    role: 'admin',
    permissions: ['read', 'write', 'delete']
};
```

#### Signature (서명)
```javascript
// JWT 서명 생성
function createSignature(header, payload, secret) {
    const data = header + '.' + payload;
    const signature = crypto.createHmac('sha256', secret)
        .update(data)
        .digest('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
    
    return signature;
}

// 전체 JWT 생성
function createJWT(payload, secret) {
    const header = {
        alg: 'HS256',
        typ: 'JWT'
    };
    
    const encodedHeader = btoa(JSON.stringify(header))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
    
    const encodedPayload = btoa(JSON.stringify(payload))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
    
    const signature = createSignature(encodedHeader, encodedPayload, secret);
    
    return `${encodedHeader}.${encodedPayload}.${signature}`;
}
```

### 2. JWT 생성 및 검증

#### Node.js에서 JWT 사용
```javascript
const jwt = require('jsonwebtoken');

class JWTManager {
    constructor(secretKey) {
        this.secretKey = secretKey;
    }
    
    // JWT 생성
    createToken(payload, options = {}) {
        const defaultOptions = {
            expiresIn: '1h',
            issuer: 'my-app.com',
            audience: 'api.my-app.com'
        };
        
        const tokenOptions = { ...defaultOptions, ...options };
        
        return jwt.sign(payload, this.secretKey, tokenOptions);
    }
    
    // JWT 검증
    verifyToken(token) {
        try {
            const decoded = jwt.verify(token, this.secretKey);
            return { valid: true, payload: decoded };
        } catch (error) {
            return { valid: false, error: error.message };
        }
    }
    
    // JWT 디코딩 (검증 없이)
    decodeToken(token) {
        return jwt.decode(token);
    }
    
    // 토큰 만료 시간 확인
    isTokenExpired(token) {
        try {
            const decoded = jwt.decode(token);
            if (!decoded || !decoded.exp) {
                return true;
            }
            
            return Date.now() >= decoded.exp * 1000;
        } catch (error) {
            return true;
        }
    }
}

// 사용 예시
const jwtManager = new JWTManager('your-secret-key');

// 토큰 생성
const payload = {
    userId: 'user123',
    username: '김철수',
    role: 'admin'
};

const token = jwtManager.createToken(payload, { expiresIn: '2h' });
console.log('생성된 JWT:', token);

// 토큰 검증
const result = jwtManager.verifyToken(token);
if (result.valid) {
    console.log('토큰 검증 성공:', result.payload);
} else {
    console.log('토큰 검증 실패:', result.error);
}
```

#### Express.js 미들웨어
```javascript
const express = require('express');
const jwt = require('jsonwebtoken');

class JWTMiddleware {
    constructor(secretKey) {
        this.secretKey = secretKey;
    }
    
    // JWT 인증 미들웨어
    authenticate(req, res, next) {
        const authHeader = req.headers.authorization;
        
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'Access token required' });
        }
        
        const token = authHeader.substring(7);
        
        try {
            const decoded = jwt.verify(token, this.secretKey);
            req.user = decoded;
            next();
        } catch (error) {
            if (error.name === 'TokenExpiredError') {
                return res.status(401).json({ error: 'Token expired' });
            } else if (error.name === 'JsonWebTokenError') {
                return res.status(401).json({ error: 'Invalid token' });
            } else {
                return res.status(500).json({ error: 'Token verification failed' });
            }
        }
    }
    
    // 역할 기반 권한 확인 미들웨어
    requireRole(role) {
        return (req, res, next) => {
            if (!req.user) {
                return res.status(401).json({ error: 'Authentication required' });
            }
            
            if (req.user.role !== role) {
                return res.status(403).json({ error: 'Insufficient permissions' });
            }
            
            next();
        };
    }
}

// Express.js 앱에서 사용
const app = express();
const jwtMiddleware = new JWTMiddleware('your-secret-key');

// 로그인 엔드포인트
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    
    // 사용자 인증 로직 (실제로는 데이터베이스에서 확인)
    if (username === 'admin' && password === 'password') {
        const payload = {
            userId: 'user123',
            username: username,
            role: 'admin'
        };
        
        const token = jwt.sign(payload, 'your-secret-key', { expiresIn: '1h' });
        res.json({ token });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

// 보호된 엔드포인트
app.get('/profile', jwtMiddleware.authenticate, (req, res) => {
    res.json({ user: req.user });
});

// 관리자 전용 엔드포인트
app.get('/admin', 
    jwtMiddleware.authenticate, 
    jwtMiddleware.requireRole('admin'), 
    (req, res) => {
        res.json({ message: 'Admin access granted' });
    }
);
```

### 3. 리프레시 토큰 구현
```javascript
class RefreshTokenManager {
    constructor(secretKey, refreshSecretKey) {
        this.secretKey = secretKey;
        this.refreshSecretKey = refreshSecretKey;
        this.refreshTokens = new Map(); // 실제로는 Redis 사용 권장
    }
    
    // 액세스 토큰과 리프레시 토큰 생성
    createTokenPair(payload) {
        const accessToken = jwt.sign(payload, this.secretKey, { expiresIn: '15m' });
        const refreshToken = jwt.sign(payload, this.refreshSecretKey, { expiresIn: '7d' });
        
        // 리프레시 토큰 저장
        this.refreshTokens.set(refreshToken, {
            userId: payload.userId,
            createdAt: Date.now()
        });
        
        return { accessToken, refreshToken };
    }
    
    // 리프레시 토큰으로 새 액세스 토큰 생성
    refreshAccessToken(refreshToken) {
        try {
            // 리프레시 토큰 검증
            const decoded = jwt.verify(refreshToken, this.refreshSecretKey);
            
            // 저장된 리프레시 토큰 확인
            const storedToken = this.refreshTokens.get(refreshToken);
            if (!storedToken || storedToken.userId !== decoded.userId) {
                throw new Error('Invalid refresh token');
            }
            
            // 새 액세스 토큰 생성
            const newAccessToken = jwt.sign(
                { userId: decoded.userId, username: decoded.username, role: decoded.role },
                this.secretKey,
                { expiresIn: '15m' }
            );
            
            return { accessToken: newAccessToken };
        } catch (error) {
            throw new Error('Refresh token invalid or expired');
        }
    }
}

// 사용 예시
const tokenManager = new RefreshTokenManager('access-secret', 'refresh-secret');

// 로그인 시 토큰 쌍 생성
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    
    if (username === 'admin' && password === 'password') {
        const payload = {
            userId: 'user123',
            username: username,
            role: 'admin'
        };
        
        const tokens = tokenManager.createTokenPair(payload);
        res.json(tokens);
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

// 토큰 갱신
app.post('/refresh', (req, res) => {
    const { refreshToken } = req.body;
    
    try {
        const result = tokenManager.refreshAccessToken(refreshToken);
        res.json(result);
    } catch (error) {
        res.status(401).json({ error: error.message });
    }
});
```

## 예시

### React 앱에서 JWT 사용
```javascript
// JWT 인증 훅
import { useState, useEffect, createContext, useContext } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        // 페이지 로드 시 토큰 확인
        const token = localStorage.getItem('accessToken');
        if (token) {
            verifyToken(token);
        } else {
            setLoading(false);
        }
    }, []);
    
    const verifyToken = async (token) => {
        try {
            const response = await fetch('/api/verify-token', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                // 토큰이 유효하지 않으면 제거
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
            }
        } catch (error) {
            console.error('Token verification failed:', error);
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
        } finally {
            setLoading(false);
        }
    };
    
    const login = async (username, password) => {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            if (response.ok) {
                const { accessToken, refreshToken, user } = await response.json();
                localStorage.setItem('accessToken', accessToken);
                localStorage.setItem('refreshToken', refreshToken);
                setUser(user);
                return { success: true };
            } else {
                const error = await response.json();
                return { success: false, error: error.message };
            }
        } catch (error) {
            return { success: false, error: 'Login failed' };
        }
    };
    
    const logout = () => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        setUser(null);
    };
    
    const value = {
        user,
        loading,
        login,
        logout
    };
    
    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
```

## 운영 팁

### 보안 고려사항

#### JWT 보안 모범 사례
```javascript
// JWT 보안 설정
const jwtConfig = {
    // 강력한 비밀키 사용
    secret: process.env.JWT_SECRET || 'your-super-secret-key',
    
    // 토큰 옵션
    options: {
        expiresIn: '15m',           // 짧은 만료 시간
        issuer: 'my-app.com',       // 발급자 명시
        audience: 'api.my-app.com', // 대상 명시
        algorithm: 'HS256'          // 안전한 알고리즘
    }
};

// 보안 헤더 설정
const securityHeaders = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
};
```

### 성능 최적화

#### JWT 캐싱
```javascript
// Redis를 사용한 JWT 캐싱
class JWTCache {
    constructor(redisClient) {
        this.redis = redisClient;
    }
    
    // 토큰 정보 캐싱
    async cacheTokenInfo(token, userInfo, ttl = 900) { // 15분
        const key = `jwt:${token}`;
        await this.redis.setex(key, ttl, JSON.stringify(userInfo));
    }
    
    // 캐시된 토큰 정보 가져오기
    async getCachedTokenInfo(token) {
        const key = `jwt:${token}`;
        const cached = await this.redis.get(key);
        return cached ? JSON.parse(cached) : null;
    }
}

// 캐시를 사용하는 JWT 미들웨어
class CachedJWTMiddleware {
    constructor(secretKey, cache) {
        this.secretKey = secretKey;
        this.cache = cache;
    }
    
    async authenticate(req, res, next) {
        const authHeader = req.headers.authorization;
        
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'Access token required' });
        }
        
        const token = authHeader.substring(7);
        
        try {
            // 캐시에서 먼저 확인
            let userInfo = await this.cache.getCachedTokenInfo(token);
            
            if (!userInfo) {
                // 캐시에 없으면 JWT 검증
                const decoded = jwt.verify(token, this.secretKey);
                userInfo = decoded;
                
                // 캐시에 저장
                await this.cache.cacheTokenInfo(token, userInfo);
            }
            
            req.user = userInfo;
            next();
        } catch (error) {
            return res.status(401).json({ error: 'Invalid token' });
        }
    }
}
```

## 참고

### JWT vs 다른 인증 방식

| 인증 방식 | 특징 | 장점 | 단점 |
|-----------|------|------|------|
| **JWT** | 토큰 기반, 상태 없음 | 확장성, 모바일 친화적 | 토큰 크기, 취소 어려움 |
| **Session** | 서버 상태 기반 | 안전한 취소, 세밀한 제어 | 서버 메모리, 확장성 제한 |
| **API Key** | 단순 키 기반 | 구현 간단, 빠름 | 보안성 낮음, 관리 복잡 |

### JWT 알고리즘 비교

| 알고리즘 | 타입 | 보안 수준 | 성능 | 권장도 |
|----------|------|-----------|------|--------|
| **HS256** | 대칭키 | 높음 | 빠름 | ⭐⭐⭐⭐⭐ |
| **RS256** | 비대칭키 | 매우 높음 | 느림 | ⭐⭐⭐⭐ |
| **ES256** | 타원곡선 | 높음 | 빠름 | ⭐⭐⭐⭐ |

### 결론
JWT는 현대적인 웹 애플리케이션에서 필수적인 인증 방식으로, 상태 없는 아키텍처와 마이크로서비스 환경에 적합합니다. 적절한 보안 설정과 토큰 관리를 통해 안전한 JWT 시스템을 구축하고, 리프레시 토큰과 캐싱을 활용하여 사용자 경험과 성능을 최적화하세요.

