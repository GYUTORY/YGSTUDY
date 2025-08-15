---
title: OAuth 2.0 완벽 가이드
tags: [auth, oauth, authentication, authorization, security]
updated: 2025-08-10
---

# OAuth 2.0 완벽 가이드

## 배경

OAuth 2.0(Open Authorization)은 제3자 애플리케이션이 사용자의 자격 증명 정보 없이 보안적으로 리소스에 접근할 수 있도록 하는 권한 부여 프로토콜입니다. Google 로그인, GitHub 로그인, Facebook 로그인 등이 OAuth 2.0을 기반으로 동작합니다.

### OAuth 2.0의 필요성
- **보안성**: 사용자의 비밀번호를 제3자에게 노출하지 않음
- **제한적 접근**: 특정 리소스에 대해서만 접근 권한 부여
- **토큰 기반**: 액세스 토큰을 통한 세션리스 인증
- **표준화**: 다양한 플랫폼과 서비스 간의 표준 인증 방식
- **사용자 경험**: 복잡한 가입 과정 없이 간편한 로그인

### 기본 개념
- **리소스 소유자**: 리소스의 실제 소유자 (사용자)
- **클라이언트**: 리소스에 접근하려는 애플리케이션
- **인증 서버**: 사용자 인증 및 액세스 토큰 발급
- **리소스 서버**: 보호된 리소스를 제공하는 서버
- **액세스 토큰**: 리소스 접근 권한을 나타내는 토큰

## 핵심

### 1. OAuth 2.0 구성 요소

#### 주요 역할자
```javascript
// OAuth 2.0 구성 요소 예시
class OAuthComponents {
    constructor() {
        this.resourceOwner = {
            id: 'user123',
            name: '김철수',
            email: 'kim@example.com'
        };
        
        this.client = {
            id: 'my-app-client-id',
            secret: 'my-app-client-secret',
            redirectUri: 'https://myapp.com/callback'
        };
        
        this.authorizationServer = {
            url: 'https://oauth-provider.com',
            endpoints: {
                authorize: '/oauth/authorize',
                token: '/oauth/token',
                userinfo: '/oauth/userinfo'
            }
        };
        
        this.resourceServer = {
            url: 'https://api.resource.com',
            scopes: ['read', 'write', 'delete']
        };
    }
}
```

#### 액세스 토큰 구조
```javascript
// 액세스 토큰 예시
const accessToken = {
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    tokenType: 'Bearer',
    expiresIn: 3600,
    scope: 'read write',
    refreshToken: 'refresh_token_here'
};

// 토큰 사용 예시
const headers = {
    'Authorization': `Bearer ${accessToken.token}`,
    'Content-Type': 'application/json'
};
```

### 2. OAuth 2.0 인증 흐름

#### 인증 코드 그랜트 (Authorization Code Grant)
```javascript
// 가장 안전한 OAuth 2.0 흐름
class AuthorizationCodeFlow {
    constructor(clientId, clientSecret, redirectUri) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.redirectUri = redirectUri;
        this.authServerUrl = 'https://oauth-provider.com';
    }
    
    // 1단계: 사용자를 인증 서버로 리디렉션
    getAuthorizationUrl(scope = 'read', state = '') {
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            scope: scope,
            state: state
        });
        
        return `${this.authServerUrl}/oauth/authorize?${params.toString()}`;
    }
    
    // 2단계: 인증 코드로 액세스 토큰 교환
    async exchangeCodeForToken(authorizationCode) {
        const response = await fetch(`${this.authServerUrl}/oauth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Basic ${btoa(`${this.clientId}:${this.clientSecret}`)}`
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: authorizationCode,
                redirect_uri: this.redirectUri
            })
        });
        
        return await response.json();
    }
    
    // 3단계: 액세스 토큰으로 리소스 접근
    async getResource(accessToken, resourceUrl) {
        const response = await fetch(resourceUrl, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        return await response.json();
    }
}

// 사용 예시
const oauth = new AuthorizationCodeFlow(
    'your-client-id',
    'your-client-secret',
    'https://myapp.com/callback'
);

// 인증 URL 생성
const authUrl = oauth.getAuthorizationUrl('read write', 'random-state');
console.log('인증 URL:', authUrl);
```

#### 클라이언트 자격 증명 그랜트 (Client Credentials Grant)
```javascript
// 서버 간 통신용 OAuth 2.0 흐름
class ClientCredentialsFlow {
    constructor(clientId, clientSecret) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.authServerUrl = 'https://oauth-provider.com';
    }
    
    // 클라이언트 자격 증명으로 액세스 토큰 획득
    async getAccessToken() {
        const response = await fetch(`${this.authServerUrl}/oauth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Basic ${btoa(`${this.clientId}:${this.clientSecret}`)}`
            },
            body: new URLSearchParams({
                grant_type: 'client_credentials',
                scope: 'read write'
            })
        });
        
        return await response.json();
    }
}

// 사용 예시
const clientOAuth = new ClientCredentialsFlow('client-id', 'client-secret');
const token = await clientOAuth.getAccessToken();
console.log('액세스 토큰:', token);
```

### 3. 실제 구현 예시

#### Express.js를 사용한 OAuth 2.0 서버
```javascript
const express = require('express');
const crypto = require('crypto');

class OAuthServer {
    constructor() {
        this.app = express();
        this.clients = new Map();
        this.authorizationCodes = new Map();
        this.accessTokens = new Map();
        this.setupRoutes();
    }
    
    setupRoutes() {
        this.app.get('/oauth/authorize', this.handleAuthorization.bind(this));
        this.app.post('/oauth/token', this.handleTokenRequest.bind(this));
        this.app.get('/oauth/userinfo', this.handleUserInfo.bind(this));
    }
    
    // 인증 엔드포인트
    handleAuthorization(req, res) {
        const { response_type, client_id, redirect_uri, scope, state } = req.query;
        
        // 클라이언트 검증
        if (!this.clients.has(client_id)) {
            return res.status(400).json({ error: 'invalid_client' });
        }
        
        // 인증 코드 생성
        const authCode = crypto.randomBytes(32).toString('hex');
        this.authorizationCodes.set(authCode, {
            client_id,
            redirect_uri,
            scope,
            user_id: 'user123', // 실제로는 로그인된 사용자 ID
            expires_at: Date.now() + 600000 // 10분 후 만료
        });
        
        // 리디렉션
        const redirectUrl = `${redirect_uri}?code=${authCode}&state=${state}`;
        res.redirect(redirectUrl);
    }
    
    // 토큰 엔드포인트
    handleTokenRequest(req, res) {
        const { grant_type, code, client_id, client_secret } = req.body;
        
        if (grant_type === 'authorization_code') {
            // 인증 코드 검증
            const authData = this.authorizationCodes.get(code);
            if (!authData || authData.expires_at < Date.now()) {
                return res.status(400).json({ error: 'invalid_grant' });
            }
            
            // 액세스 토큰 생성
            const accessToken = crypto.randomBytes(32).toString('hex');
            this.accessTokens.set(accessToken, {
                user_id: authData.user_id,
                scope: authData.scope,
                expires_at: Date.now() + 3600000 // 1시간 후 만료
            });
            
            // 인증 코드 삭제
            this.authorizationCodes.delete(code);
            
            res.json({
                access_token: accessToken,
                token_type: 'Bearer',
                expires_in: 3600,
                scope: authData.scope
            });
        }
    }
    
    // 사용자 정보 엔드포인트
    handleUserInfo(req, res) {
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'invalid_token' });
        }
        
        const token = authHeader.substring(7);
        const tokenData = this.accessTokens.get(token);
        
        if (!tokenData || tokenData.expires_at < Date.now()) {
            return res.status(401).json({ error: 'invalid_token' });
        }
        
        // 사용자 정보 반환
        res.json({
            user_id: tokenData.user_id,
            name: '김철수',
            email: 'kim@example.com'
        });
    }
    
    // 클라이언트 등록
    registerClient(clientId, clientSecret, redirectUri) {
        this.clients.set(clientId, {
            secret: clientSecret,
            redirect_uri: redirectUri
        });
    }
    
    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`OAuth 서버가 포트 ${port}에서 실행 중입니다.`);
        });
    }
}

// 서버 시작
const oauthServer = new OAuthServer();
oauthServer.registerClient('my-app', 'my-secret', 'https://myapp.com/callback');
oauthServer.start();
```

#### OAuth 2.0 클라이언트 구현
```javascript
class OAuthClient {
    constructor(clientId, clientSecret, redirectUri) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.redirectUri = redirectUri;
        this.authServerUrl = 'http://localhost:3000';
    }
    
    // 인증 URL 생성
    getAuthUrl(scope = 'read', state = '') {
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            scope: scope,
            state: state
        });
        
        return `${this.authServerUrl}/oauth/authorize?${params.toString()}`;
    }
    
    // 인증 코드 처리
    async handleCallback(code, state) {
        try {
            const tokenResponse = await fetch(`${this.authServerUrl}/oauth/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    grant_type: 'authorization_code',
                    code: code,
                    client_id: this.clientId,
                    client_secret: this.clientSecret,
                    redirect_uri: this.redirectUri
                })
            });
            
            const tokenData = await tokenResponse.json();
            
            if (tokenData.error) {
                throw new Error(tokenData.error);
            }
            
            return tokenData;
        } catch (error) {
            console.error('토큰 교환 실패:', error);
            throw error;
        }
    }
    
    // 사용자 정보 가져오기
    async getUserInfo(accessToken) {
        try {
            const response = await fetch(`${this.authServerUrl}/oauth/userinfo`, {
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                }
            });
            
            return await response.json();
        } catch (error) {
            console.error('사용자 정보 가져오기 실패:', error);
            throw error;
        }
    }
}

// 클라이언트 사용 예시
const client = new OAuthClient('my-app', 'my-secret', 'https://myapp.com/callback');

// 인증 URL 생성
const authUrl = client.getAuthUrl('read write', 'random-state');
console.log('인증 URL:', authUrl);

// 콜백 처리 (실제로는 Express.js 라우트에서 처리)
async function handleOAuthCallback(code, state) {
    try {
        const tokenData = await client.handleCallback(code, state);
        console.log('액세스 토큰:', tokenData.access_token);
        
        const userInfo = await client.getUserInfo(tokenData.access_token);
        console.log('사용자 정보:', userInfo);
    } catch (error) {
        console.error('OAuth 처리 실패:', error);
    }
}
```

## 예시

### 1. 실제 사용 사례

#### Google OAuth 2.0 로그인
```javascript
// Google OAuth 2.0 클라이언트
class GoogleOAuthClient {
    constructor(clientId, clientSecret) {
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.redirectUri = 'http://localhost:3000/auth/google/callback';
        this.googleAuthUrl = 'https://accounts.google.com';
        this.googleApiUrl = 'https://www.googleapis.com';
    }
    
    // Google 로그인 URL 생성
    getLoginUrl(state = '') {
        const params = new URLSearchParams({
            client_id: this.clientId,
            redirect_uri: this.redirectUri,
            response_type: 'code',
            scope: 'openid email profile',
            access_type: 'offline',
            prompt: 'consent',
            state: state
        });
        
        return `${this.googleAuthUrl}/o/oauth2/v2/auth?${params.toString()}`;
    }
    
    // 인증 코드로 액세스 토큰 교환
    async exchangeCodeForToken(code) {
        const response = await fetch(`${this.googleAuthUrl}/o/oauth2/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                client_id: this.clientId,
                client_secret: this.clientSecret,
                code: code,
                grant_type: 'authorization_code',
                redirect_uri: this.redirectUri
            })
        });
        
        return await response.json();
    }
    
    // Google 사용자 정보 가져오기
    async getUserInfo(accessToken) {
        const response = await fetch(`${this.googleApiUrl}/oauth2/v2/userinfo`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        return await response.json();
    }
}

// Express.js 서버에서 Google OAuth 사용
const express = require('express');
const app = express();

const googleOAuth = new GoogleOAuthClient(
    'your-google-client-id',
    'your-google-client-secret'
);

// 로그인 페이지
app.get('/login', (req, res) => {
    const loginUrl = googleOAuth.getLoginUrl('random-state');
    res.redirect(loginUrl);
});

// OAuth 콜백 처리
app.get('/auth/google/callback', async (req, res) => {
    const { code, state } = req.query;
    
    try {
        // 액세스 토큰 획득
        const tokenData = await googleOAuth.exchangeCodeForToken(code);
        
        // 사용자 정보 가져오기
        const userInfo = await googleOAuth.getUserInfo(tokenData.access_token);
        
        // 세션에 사용자 정보 저장
        req.session.user = {
            id: userInfo.id,
            email: userInfo.email,
            name: userInfo.name,
            picture: userInfo.picture
        };
        
        res.redirect('/dashboard');
    } catch (error) {
        console.error('Google OAuth 오류:', error);
        res.redirect('/login?error=auth_failed');
    }
});

app.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다.');
});
```

### 2. 고급 패턴

#### 토큰 갱신 및 관리
```javascript
class TokenManager {
    constructor() {
        this.tokens = new Map();
    }
    
    // 토큰 저장
    saveToken(userId, tokenData) {
        this.tokens.set(userId, {
            accessToken: tokenData.access_token,
            refreshToken: tokenData.refresh_token,
            expiresAt: Date.now() + (tokenData.expires_in * 1000),
            scope: tokenData.scope
        });
    }
    
    // 토큰 가져오기
    getToken(userId) {
        const tokenData = this.tokens.get(userId);
        if (!tokenData) {
            return null;
        }
        
        // 토큰이 만료되었는지 확인
        if (Date.now() >= tokenData.expiresAt) {
            return this.refreshToken(userId);
        }
        
        return tokenData.accessToken;
    }
    
    // 토큰 갱신
    async refreshToken(userId) {
        const tokenData = this.tokens.get(userId);
        if (!tokenData || !tokenData.refreshToken) {
            throw new Error('Refresh token not available');
        }
        
        try {
            const response = await fetch('https://oauth-provider.com/oauth/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    grant_type: 'refresh_token',
                    refresh_token: tokenData.refreshToken,
                    client_id: 'your-client-id',
                    client_secret: 'your-client-secret'
                })
            });
            
            const newTokenData = await response.json();
            
            // 새 토큰 저장
            this.saveToken(userId, newTokenData);
            
            return newTokenData.access_token;
        } catch (error) {
            console.error('토큰 갱신 실패:', error);
            this.tokens.delete(userId);
            throw error;
        }
    }
    
    // 토큰 삭제
    removeToken(userId) {
        this.tokens.delete(userId);
    }
}

// 사용 예시
const tokenManager = new TokenManager();

// 토큰 저장
tokenManager.saveToken('user123', {
    access_token: 'access_token_here',
    refresh_token: 'refresh_token_here',
    expires_in: 3600,
    scope: 'read write'
});

// 토큰 사용
const accessToken = tokenManager.getToken('user123');
if (accessToken) {
    // API 호출
    console.log('액세스 토큰:', accessToken);
}
```

## 운영 팁

### 보안 고려사항

#### CSRF 공격 방지
```javascript
// State 파라미터를 사용한 CSRF 방지
class CSRFProtection {
    constructor() {
        this.states = new Map();
    }
    
    // State 생성
    generateState(userId) {
        const state = crypto.randomBytes(32).toString('hex');
        this.states.set(state, {
            userId: userId,
            createdAt: Date.now()
        });
        
        return state;
    }
    
    // State 검증
    validateState(state, userId) {
        const stateData = this.states.get(state);
        if (!stateData) {
            return false;
        }
        
        // 10분 이내에 생성된 state만 유효
        if (Date.now() - stateData.createdAt > 600000) {
            this.states.delete(state);
            return false;
        }
        
        // 사용자 ID 검증
        if (stateData.userId !== userId) {
            return false;
        }
        
        // 사용된 state 삭제
        this.states.delete(state);
        return true;
    }
    
    // 만료된 state 정리
    cleanup() {
        const now = Date.now();
        for (const [state, data] of this.states.entries()) {
            if (now - data.createdAt > 600000) {
                this.states.delete(state);
            }
        }
    }
}

// 사용 예시
const csrfProtection = new CSRFProtection();

// 로그인 시 state 생성
app.get('/login', (req, res) => {
    const state = csrfProtection.generateState(req.session.userId);
    const authUrl = oauthClient.getAuthUrl('read write', state);
    res.redirect(authUrl);
});

// 콜백에서 state 검증
app.get('/callback', (req, res) => {
    const { code, state } = req.query;
    
    if (!csrfProtection.validateState(state, req.session.userId)) {
        return res.status(400).json({ error: 'invalid_state' });
    }
    
    // OAuth 처리 계속...
});
```

### 성능 최적화

#### 토큰 캐싱
```javascript
// Redis를 사용한 토큰 캐싱
class TokenCache {
    constructor(redisClient) {
        this.redis = redisClient;
        this.defaultTTL = 3600; // 1시간
    }
    
    // 토큰 저장
    async saveToken(userId, tokenData) {
        const key = `oauth_token:${userId}`;
        await this.redis.setex(key, this.defaultTTL, JSON.stringify(tokenData));
    }
    
    // 토큰 가져오기
    async getToken(userId) {
        const key = `oauth_token:${userId}`;
        const tokenData = await this.redis.get(key);
        
        if (!tokenData) {
            return null;
        }
        
        return JSON.parse(tokenData);
    }
    
    // 토큰 삭제
    async removeToken(userId) {
        const key = `oauth_token:${userId}`;
        await this.redis.del(key);
    }
    
    // 토큰 만료 시간 설정
    async setTokenExpiry(userId, ttl) {
        const key = `oauth_token:${userId}`;
        await this.redis.expire(key, ttl);
    }
}

// 사용 예시
const redis = require('redis');
const redisClient = redis.createClient();

const tokenCache = new TokenCache(redisClient);

// 토큰 저장
await tokenCache.saveToken('user123', {
    accessToken: 'token_here',
    refreshToken: 'refresh_here',
    expiresAt: Date.now() + 3600000
});

// 토큰 가져오기
const tokenData = await tokenCache.getToken('user123');
if (tokenData) {
    console.log('캐시된 토큰:', tokenData);
}
```

## 참고

### OAuth 2.0 vs 다른 인증 방식

| 인증 방식 | 특징 | 사용 시기 |
|-----------|------|-----------|
| **OAuth 2.0** | 토큰 기반, 제3자 인증 | 외부 서비스 연동 |
| **JWT** | 자체 서명 토큰 | 내부 API 인증 |
| **Session** | 서버 세션 기반 | 전통적인 웹 애플리케이션 |
| **API Key** | 단순 키 기반 | 서버 간 통신 |

### OAuth 2.0 그랜트 타입 비교

| 그랜트 타입 | 보안 수준 | 사용 분야 | 권장도 |
|-------------|-----------|-----------|--------|
| **Authorization Code** | 높음 | 웹 애플리케이션 | ⭐⭐⭐⭐⭐ |
| **Client Credentials** | 높음 | 서버 간 통신 | ⭐⭐⭐⭐ |
| **Implicit** | 중간 | SPA, 모바일 앱 | ⭐⭐⭐ |
| **Password** | 낮음 | 레거시 시스템 | ⭐⭐ |

### 결론
OAuth 2.0은 현대적인 웹 애플리케이션에서 필수적인 인증 표준으로, 사용자 경험과 보안성을 모두 만족시킵니다.
적절한 그랜트 타입 선택과 보안 고려사항을 통해 안전한 OAuth 2.0 시스템을 구축하세요.
토큰 관리와 캐싱을 통해 성능을 최적화하고, CSRF 공격 등 보안 위협에 대비하세요.

