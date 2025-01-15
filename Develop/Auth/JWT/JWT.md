
# 🔐 JSON Web Token (JWT) 완벽 가이드

---

## 1. JWT란?
**JWT (JSON Web Token)**는 JSON 형식으로 데이터를 안전하게 전송하기 위한 **토큰 기반 인증 방식**입니다.  
웹 애플리케이션에서 **사용자 인증** 및 **정보 교환**에 자주 사용됩니다.

---

### 👉🏻 JWT의 주요 특징
- **토큰 기반 인증**: 상태를 유지하지 않고도 인증 정보를 관리.
- **자기 포함 토큰**: 토큰 자체에 모든 정보를 포함.
- **서명(Signature) 포함**: 데이터 위변조 방지.
- **가벼운 데이터 포맷**: JSON 기반의 경량 토큰.

---

## 2. JWT의 구성 요소 📦
JWT는 **Header, Payload, Signature**로 구성된 **3개의 JSON 객체**를 `.`으로 구분하여 인코딩한 문자열입니다.

### 📌 예제 JWT (Base64 인코딩)
```plaintext
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.
eyJ1c2VybmFtZSI6ImpvaG5kb2UiLCJyb2xlIjoiYWRtaW4ifQ
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

---

### 📦 2.1 Header (헤더)
JWT의 **알고리즘과 타입**을 명시합니다.

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg`: 서명 알고리즘 (예: HS256)
- `typ`: 토큰의 타입 (JWT)

---

### 📦 2.2 Payload (페이로드)
**클레임(Claim)** 정보를 담고 있는 데이터 부분입니다.

```json
{
  "username": "johndoe",
  "role": "admin",
  "exp": 1681234567
}
```

- `username`: 사용자 이름
- `role`: 사용자 역할
- `exp`: 만료 시간 (Unix Timestamp)

---

### 📦 2.3 Signature (서명)
서명은 **데이터 무결성을 보장**하며, 헤더와 페이로드를 기반으로 생성됩니다.

```plaintext
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload), 
  secret_key
)
```

---

## 3. JWT의 동작 방식 🛠️
1. **클라이언트 로그인 요청** → 사용자가 로그인 정보를 서버에 전송.
2. **서버 인증 및 JWT 발급** → 서버가 사용자 정보를 검증 후 JWT를 발급.
3. **클라이언트 JWT 저장** → JWT를 로컬 스토리지나 쿠키에 저장.
4. **클라이언트 요청 시 JWT 전송** → 요청 시 JWT를 `Authorization` 헤더에 포함.
5. **서버 JWT 검증 및 응답** → 서버가 JWT를 검증하고 리소스 제공.

---

### ✅ JWT 예제 (Node.js)
```javascript
const jwt = require('jsonwebtoken');

const payload = {
    username: 'johndoe',
    role: 'admin'
};

const secretKey = 'mySecretKey123';
const token = jwt.sign(payload, secretKey, { expiresIn: '1h' });
console.log('Generated JWT:', token);
```

---

### ✅ JWT 검증 예제 (Node.js)
```javascript
const decoded = jwt.verify(token, secretKey);
console.log('Decoded Token:', decoded);
```

---

## 4. JWT의 장점과 단점 📊
### ✅ 장점
- **무상태성 (Stateless)**: 서버에 세션을 저장할 필요 없음.
- **확장성 (Scalable)**: 마이크로서비스와 잘 어울림.
- **간편한 데이터 전송**: JSON 포맷으로 쉽게 인코딩 및 디코딩.

---

### ❗ 단점
- **서명만 확인 가능**: 암호화가 아닌 서명 검증 방식.
- **Payload 노출 가능성**: Base64로 인코딩되었기 때문에 쉽게 디코딩 가능.
- **만료 시간 관리 어려움**: 토큰 발급 후 취소가 어려움.

---

## 5. JWT 보안 모범 사례 🔒
- **강력한 시크릿 키 사용**: 예측 불가능한 시크릿 키 사용.
- **만료 시간 짧게 설정**: 토큰 재발급을 자주 수행.
- **HTTPS 사용**: 데이터 전송 시 반드시 HTTPS 사용.
- **Refresh Token 사용**: 장기 인증은 리프레시 토큰으로 관리.

---

## 6. JWT와 OAuth의 차이점 🔄
| **항목**                  | **JWT**                   | **OAuth**             |
|:--------------------------|:--------------------------|:----------------------|
| **정의**                  | 인증 정보 자체 포함       | 권한 부여 프레임워크 |
| **주요 용도**              | 자체 인증 및 인가          | 외부 서비스 접근 제어|
| **보안 수준**             | 중간 수준 (서명 기반)      | 더 높은 보안 (토큰 기반)|
| **세션 관리**             | 무상태성                  | 상태 관리 (Access, Refresh Token) |

---

## 7. JWT 사용 사례 📦
- **사용자 로그인 및 세션 관리**
- **API 인증 및 권한 부여**
- **마이크로서비스 간 데이터 교환**

---

## 8. JWT 사용 시 주의사항 ⚠️
- **민감한 데이터 포함 금지**: JWT는 **서명**만 포함하고 **암호화**는 하지 않음.
- **짧은 만료 시간 유지**: 보안을 위해 만료 시간 짧게 설정.
- **토큰 저장 위치**: 로컬 스토리지보다는 **쿠키** 사용 권장.

---

## 9. 결론 ✅
- **JWT**는 가벼운 **토큰 기반 인증 방식**으로, RESTful 서비스에 적합합니다.
- **보안 모범 사례**를 준수하지 않으면 보안 문제가 발생할 수 있습니다.
- **OAuth 2.0**과의 비교를 통해 사용 목적에 맞는 기술을 선택하는 것이 중요합니다.
