---
title: CORS (Cross-Origin Resource Sharing) 개념과 예제
tags: [webserver, nginx, cors, cross-origin, security]
updated: 2024-12-19
---

# CORS (Cross-Origin Resource Sharing) 개념과 예제

## 배경

### CORS란?
CORS(Cross-Origin Resource Sharing)는 한 웹사이트에서 다른 도메인의 리소스에 접근할 때 발생하는 보안 정책입니다. 브라우저는 보안상의 이유로 기본적으로 다른 출처(origin)의 요청을 차단합니다. 하지만 서버에서 CORS 설정을 명시적으로 허용하면 다른 도메인에서도 데이터를 주고받을 수 있습니다.

### CORS의 주요 목적
1. **보안 강화**: 악의적인 웹사이트가 다른 도메인의 민감한 데이터에 접근하는 것을 방지
2. **리소스 접근 제어**: 서버가 어떤 출처에서의 요청을 허용할지 명시적으로 지정
3. **API 보호**: 무분별한 API 호출을 제한하여 서버 리소스 보호

### Same-Origin Policy(동일 출처 정책)
브라우저는 기본적으로 동일 출처 정책(Same-Origin Policy, SOP)을 따릅니다. 즉, 같은 출처(origin)에서만 리소스를 요청할 수 있습니다.

출처는 다음 세 가지 요소로 구성됩니다:
- `프로토콜 (http, https)`
- `도메인 (example.com, api.example.com)`
- `포트 (:80, :443)`

이 세 가지가 완전히 같아야 동일 출처로 인정됩니다. 만약 하나라도 다르면 다른 출처(=Cross-Origin)로 간주되어 요청이 차단될 수 있습니다.

```plaintext
https://example.com  ✅ 동일 출처
https://example.com:3000 ❌ 다른 출처 (포트 다름)
https://api.example.com ❌ 다른 출처 (서브도메인 다름)
http://example.com ❌ 다른 출처 (프로토콜 다름)
```

### CORS가 필요한 상황
1. **개발 환경**: 
   - 프론트엔드: `http://localhost:3000`
   - 백엔드: `http://localhost:8080`
   - 포트가 다르므로 CORS 설정 필요

2. **프로덕션 환경**:
   - 프론트엔드: `https://example.com`
   - 백엔드: `https://api.example.com`
   - 서브도메인이 다르므로 CORS 설정 필요

## 핵심

### CORS 오류 발생 원리
브라우저는 `api.example.com`이 CORS 설정을 하지 않았다고 판단하여 요청을 차단합니다. 따라서 클라이언트에서 데이터를 가져올 수 없습니다. 브라우저 콘솔에서 다음과 같은 오류 메시지를 확인할 수 있습니다:

```
Access to fetch at 'http://api.example.com/data' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present 
on the requested resource.
```

### CORS가 필요한 주요 시나리오
1. **SPA(Single Page Application) 개발**
   - 프론트엔드와 백엔드가 분리된 아키텍처
   - API 서버와의 통신이 빈번

2. **마이크로서비스 아키텍처**
   - 여러 서비스가 다른 도메인에서 운영
   - 서비스 간 통신 필요

3. **서드파티 API 통합**
   - 외부 서비스 API 호출
   - 결제, 지도, 소셜 로그인 등

## 예시

### CORS 오류가 발생하는 예제
아래 코드에서 `http://localhost:3000`에서 `http://api.example.com`으로 데이터를 요청합니다. 하지만 CORS 설정이 되어 있지 않다면 요청이 차단됩니다.

#### 클라이언트 (JavaScript)
```javascript
// 기본 fetch 요청
fetch('http://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('CORS 오류 발생:', error));

// 커스텀 헤더가 포함된 요청
fetch('http://api.example.com/data', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123'
    },
    body: JSON.stringify({ key: 'value' })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('CORS 오류 발생:', error));
```

#### 서버 (Node.js - Express)
```javascript
const express = require('express');
const app = express();

app.get('/data', (req, res) => {
    res.json({ message: "데이터 전송 완료!" });
});

app.listen(5000, () => console.log('서버 실행 중: http://localhost:5000'));
```

### CORS 해결 방법

#### 1. 서버에서 CORS 설정 추가하기

##### Node.js (Express)에서 CORS 허용
```javascript
const express = require('express');
const cors = require('cors'); // CORS 모듈 추가

const app = express();

// 기본 CORS 설정
app.use(cors()); // 모든 출처 허용

// 또는 상세 설정
app.use(cors({
    origin: ['http://localhost:3000', 'https://example.com'],
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true, // 쿠키, 인증 헤더 허용
    maxAge: 86400 // preflight 요청 캐시 시간 (초)
}));

app.get('/data', (req, res) => {
    res.json({ message: "CORS 설정 완료!" });
});

app.listen(5000, () => console.log('서버 실행 중: http://localhost:5000'));
```

#### 2. 특정 출처만 허용하기
보안 강화를 위해 특정 도메인만 허용할 수도 있습니다.

```javascript
// 단일 도메인 허용
app.use(cors({
    origin: 'http://localhost:3000'
}));

// 여러 도메인 허용
app.use(cors({
    origin: ['http://localhost:3000', 'https://example.com', 'https://api.example.com']
}));

// 정규식으로 도메인 패턴 허용
app.use(cors({
    origin: /\.example\.com$/
}));

// 동적 origin 설정
app.use(cors({
    origin: function(origin, callback) {
        const allowedOrigins = ['http://localhost:3000', 'https://example.com'];
        if (!origin || allowedOrigins.indexOf(origin) !== -1) {
            callback(null, true);
        } else {
            callback(new Error('CORS not allowed'));
        }
    }
}));
```

#### 3. 응답 헤더에 직접 추가
서버에서 응답할 때 CORS 관련 헤더를 추가할 수도 있습니다.

```javascript
// 모든 라우트에 적용
app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    next();
});

// 특정 라우트에만 적용
app.get('/data', (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', 'http://localhost:3000');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    res.json({ message: "CORS 헤더 추가 완료!" });
});
```

### Preflight Request (사전 요청)
CORS 요청 중 일부는 "사전 요청(Preflight Request)"이 필요합니다. 이는 브라우저가 실제 요청 전에 서버가 허용하는지 확인하는 과정입니다.

#### Preflight Request가 필요한 경우
1. **HTTP 메서드**
   - `PUT`, `DELETE`, `PATCH` 등
   - `GET`, `POST`, `HEAD`는 기본적으로 preflight가 필요 없음

2. **커스텀 헤더**
   - `Content-Type: application/json`
   - `Authorization`
   - 기타 커스텀 헤더

3. **요청 본문**
   - JSON 데이터
   - FormData
   - 기타 복잡한 데이터 구조

#### Preflight 요청 예시
```http
OPTIONS /data HTTP/1.1
Host: api.example.com
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization
```

#### Preflight 응답 예시
```http
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: POST, GET, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

#### 해결 방법 (Preflight 요청 허용)
```javascript
// Express에서 Preflight 요청 처리
app.options('/data', cors()); // 특정 라우트에 대한 Preflight 처리

// 또는 모든 OPTIONS 요청 처리
app.options('*', cors());

// 상세 설정
app.use(cors({
    origin: 'http://localhost:3000',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    maxAge: 86400 // preflight 결과 캐시 시간
}));
```

## 운영 팁

### CORS 오류 해결 체크리스트
- 서버에서 `Access-Control-Allow-Origin` 헤더 추가했는가?
- `cors()` 미들웨어를 추가했는가?
- 필요한 경우 Preflight 요청을 허용했는가?
- 특정 출처만 허용해야 하는 경우 `origin` 설정을 정확히 했는가?
- 인증이 필요한 경우 `credentials: true` 설정을 했는가?
- 필요한 HTTP 메서드와 헤더를 `allowedHeaders`에 포함했는가?
- 개발 환경과 프로덕션 환경의 CORS 설정이 올바른가?
- 보안을 위해 필요한 최소한의 출처만 허용했는가?

### 자주 발생하는 CORS 오류와 해결 방법
1. **"No 'Access-Control-Allow-Origin' header is present"**
   - 서버에 CORS 헤더가 없음
   - `Access-Control-Allow-Origin` 헤더 추가 필요

2. **"Request header field Authorization is not allowed"**
   - 커스텀 헤더가 허용되지 않음
   - `allowedHeaders`에 해당 헤더 추가 필요

3. **"Method PUT is not allowed"**
   - HTTP 메서드가 허용되지 않음
   - `methods` 옵션에 해당 메서드 추가 필요

4. **"Credentials are not supported"**
   - 인증 정보 전송이 허용되지 않음
   - `credentials: true` 설정 필요

### CORS 보안 고려사항
1. **와일드카드(*) 사용 주의**
   - `Access-Control-Allow-Origin: *`는 모든 출처를 허용
   - 프로덕션 환경에서는 특정 도메인만 허용하는 것이 안전

2. **credentials 설정**
   - `credentials: true`는 인증 정보를 포함한 요청 허용
   - 이 경우 `Access-Control-Allow-Origin`에 와일드카드 사용 불가

3. **헤더 노출 제한**
   - 필요한 헤더만 `exposedHeaders`에 포함
   - 민감한 정보가 포함된 헤더는 제외

4. **메서드 제한**
   - 필요한 HTTP 메서드만 허용
   - 불필요한 메서드는 제외

## 참고

### 실제 개발 시나리오별 CORS 설정

#### 1. 개발 환경
```javascript
// 개발 환경에서는 모든 출처 허용
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));
```

#### 2. 프로덕션 환경
```javascript
// 프로덕션 환경에서는 특정 도메인만 허용
app.use(cors({
    origin: ['https://example.com', 'https://api.example.com'],
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true
}));
```

#### 3. 마이크로서비스 환경
```javascript
// 서비스 간 통신을 위한 CORS 설정
app.use(cors({
    origin: /\.example\.com$/,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Service-Token'],
    credentials: true
}));
```

### 결론
CORS는 현대 웹 개발에서 필수적인 보안 정책입니다.
적절한 CORS 설정을 통해 보안을 유지하면서도 필요한 리소스 접근을 허용할 수 있습니다.
특히 마이크로서비스 아키텍처나 SPA 개발에서 CORS 설정은 매우 중요합니다.

