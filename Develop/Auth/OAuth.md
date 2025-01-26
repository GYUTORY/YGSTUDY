
# 🔑 OAuth 완벽 가이드

---

## 1. OAuth란?
**OAuth (Open Authorization)**는 **제3자 애플리케이션**이 사용자의 **자격 증명 정보 없이** 보안적으로 리소스에 접근할 수 있도록 하는 **권한 부여 프로토콜**입니다.  
대표적으로 **Google 로그인**, **GitHub 로그인** 등이 OAuth를 기반으로 동작합니다.

---

### 👉🏻 OAuth의 주요 특징
- **안전한 권한 부여**: 사용자의 비밀번호를 제공하지 않고 외부 서비스에 접근.
- **제한적 접근 제공**: 특정 리소스에 대해서만 접근 허용.
- **세션리스 인증**: 액세스 토큰 기반 인증 및 권한 부여.
- **다중 플랫폼 지원**: 웹, 모바일, 데스크톱 애플리케이션 지원.

---

## 2. OAuth의 주요 개념 📦
### 📌 리소스 소유자 (Resource Owner)
- 리소스의 실제 소유자 (예: 사용자).

### 📌 클라이언트 (Client)
- 리소스 소유자를 대신하여 리소스에 접근하려는 애플리케이션 (예: 웹 앱, 모바일 앱).

### 📌 인증 서버 (Authorization Server)
- 리소스 소유자를 인증하고, **액세스 토큰**을 발급하는 서버.

### 📌 리소스 서버 (Resource Server)
- 보호된 리소스를 제공하는 서버 (예: Google Drive, GitHub).

---

## 3. OAuth 2.0의 동작 방식 🛠️
1. **사용자가 애플리케이션에 로그인 요청.**
2. **클라이언트가 인증 서버에 권한 요청.**
3. **사용자가 로그인 및 권한 부여.**
4. **인증 서버가 클라이언트에게 **액세스 토큰** 발급.**
5. **클라이언트가 리소스 서버에 요청 시 토큰 사용.**
6. **리소스 서버가 토큰을 검증하고 데이터 제공.**

---

## 4. OAuth 2.0의 인증 흐름 📊
### ✅ 4.1 인증 코드 그랜트 (Authorization Code Grant)
- **가장 안전하고 일반적인 방식**으로, 웹 애플리케이션에서 주로 사용.

```plaintext
사용자 → 클라이언트 → 인증 서버 → 리디렉션 및 토큰 발급 → 리소스 서버
```

**예시 (Node.js)**:
```javascript
const express = require('express');
const axios = require('axios');

const app = express();
const clientId = 'your-client-id';
const clientSecret = 'your-client-secret';
const redirectUri = 'http://localhost:3000/callback';

app.get('/login', (req, res) => {
    res.redirect(`https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}`);
});

app.get('/callback', async (req, res) => {
    const code = req.query.code;
    const tokenResponse = await axios.post('https://github.com/login/oauth/access_token', {
        client_id: clientId,
        client_secret: clientSecret,
        code: code
    }, { headers: { Accept: 'application/json' }});

    const accessToken = tokenResponse.data.access_token;
    res.send(`Access Token: ${accessToken}`);
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));
```

---

### ✅ 4.2 임플리시트 그랜트 (Implicit Grant)
- **브라우저 기반 애플리케이션**에서 사용 (보안이 다소 약함).

```plaintext
사용자 → 클라이언트 → 인증 서버 (토큰 바로 발급)
```

---

### ✅ 4.3 비밀번호 기반 그랜트 (Resource Owner Password Credentials)
- **내부 서비스**에서 사용 (보안 취약, 비추천).

```plaintext
사용자 → 클라이언트 (아이디/비밀번호 제공) → 인증 서버
```

---

### ✅ 4.4 클라이언트 자격 증명 그랜트 (Client Credentials Grant)
- **서버 간 통신**이나 백엔드에서 사용.

```plaintext
클라이언트 → 인증 서버 (클라이언트 아이디/시크릿 제공) → 액세스 토큰 발급
```

---

## 5. OAuth 2.0의 토큰 종류 📦
### 📌 액세스 토큰 (Access Token)
- **리소스 서버에 접근**하기 위한 토큰.
- 짧은 수명 (일반적으로 1시간 이내).

### 📌 리프레시 토큰 (Refresh Token)
- **액세스 토큰 갱신**을 위해 사용.
- 더 긴 수명을 가지며, 주로 백엔드에서 관리.

---

## 6. OAuth 보안 모범 사례 🔒
- **시크릿 키 보호**: 클라이언트 ID 및 시크릿 키를 안전하게 관리.
- **HTTPS 사용**: 민감한 정보 전송 시 HTTPS 사용.
- **액세스 토큰 만료 설정**: 짧은 수명의 토큰 사용.
- **리프레시 토큰 암호화**: 장기 사용 토큰을 암호화하여 저장.
- **CORS 설정**: 외부 도메인의 토큰 사용 제한.

---

## 7. OAuth와 JWT의 차이점 🔄
| **항목**                  | **OAuth**                | **JWT**              |
|:--------------------------|:-------------------------|:--------------------|
| **정의**                  | 권한 부여 프로토콜       | JSON 데이터 포맷 인증 |
| **주요 용도**             | 외부 서비스 접근 제어    | 자체 인증 및 데이터 전송|
| **보안 수준**             | 높은 수준 (토큰 갱신 포함) | 중간 수준 (서명 기반) |
| **상태 관리**             | Access, Refresh Token 사용 | 상태 없는 토큰 기반 |

---

## 8. OAuth의 장단점 📊
### ✅ 장점
- **보안성 강화**: 민감한 사용자 비밀번호를 공유하지 않음.
- **유연성**: 다양한 애플리케이션 환경 지원.
- **토큰 기반 관리**: 세션리스 방식으로 확장성 제공.

---

### ❗ 단점
- **구현 복잡성**: 다중 엔드포인트와 토큰 관리.
- **추가 보안 위험**: 리프레시 토큰이 유출되면 장기 보안 위험 발생.
- **서드파티 의존**: 외부 인증 서버에 의존.

---

## 9. OAuth 사용 사례 📦
- **Google, GitHub, Facebook 로그인**
- **마이크로서비스 간 인증**
- **서드파티 애플리케이션과 데이터 공유**

---

## 10. 결론 ✅
- **OAuth 2.0**은 **외부 서비스와의 안전한 데이터 공유**를 위한 업계 표준입니다.
- **액세스 토큰 및 리프레시 토큰**을 기반으로, 세션리스 인증을 제공합니다.
- **보안 모범 사례**를 준수하여, 민감한 데이터 보호를 강화해야 합니다.
