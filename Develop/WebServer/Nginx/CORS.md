

# 🛠️ CORS (Cross-Origin Resource Sharing) 개념과 예제

## ✨ CORS란?
CORS(Cross-Origin Resource Sharing)는 한 웹사이트에서 다른 도메인의 리소스에 접근할 때 발생하는 **보안 정책**이다.  
브라우저는 보안상의 이유로 기본적으로 **다른 출처(origin)의 요청을 차단**한다. 하지만 서버에서 **CORS 설정을 명시적으로 허용**하면 다른 도메인에서도 데이터를 주고받을 수 있다.

---

## 🎯 Same-Origin Policy(동일 출처 정책)란?
브라우저는 기본적으로 **동일 출처 정책(Same-Origin Policy, SOP)**을 따른다.  
즉, **같은 출처(origin)**에서만 리소스를 요청할 수 있다.

### 👉🏻 동일 출처란?
- `프로토콜 (http, https)`
- `도메인 (example.com, api.example.com)`
- `포트 (:80, :443)`

이 **세 가지가 완전히 같아야 동일 출처**로 인정된다.  
만약 하나라도 다르면 다른 출처(=Cross-Origin)로 간주되어 요청이 차단될 수 있다.

```plaintext
https://example.com  ✅ 동일 출처
https://example.com:3000 ❌ 다른 출처 (포트 다름)
https://api.example.com ❌ 다른 출처 (서브도메인 다름)
http://example.com ❌ 다른 출처 (프로토콜 다름)
```

---

## 🌐 CORS가 필요한 이유
현대 웹 애플리케이션에서는 **API 요청이 많아지고**, 프론트엔드(React, Vue, etc.)와 백엔드(Node.js, Django 등)가 분리되는 경우가 많다.  
이 과정에서 **서버와 클라이언트의 출처가 다를 가능성이 크다.** 따라서 CORS 정책을 통해 보안은 유지하면서, 필요한 요청을 허용할 수 있어야 한다.

---

## 🚀 CORS 예제 코드

### ✅ CORS 오류가 발생하는 예제
아래 코드에서 **http://localhost:3000**에서 **http://api.example.com**으로 데이터를 요청한다.  
하지만 **CORS 설정이 되어 있지 않다면 요청이 차단**된다.

#### 🔹 클라이언트 (JavaScript)
```js
fetch('http://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('CORS 오류 발생:', error));
```

#### 🔹 서버 (Node.js - Express)
```js
const express = require('express');
const app = express();

app.get('/data', (req, res) => {
    res.json({ message: "데이터 전송 완료!" });
});

app.listen(5000, () => console.log('서버 실행 중: http://localhost:5000'));
```

### 👉🏻 오류 발생 원인
- 브라우저는 `api.example.com`이 CORS 설정을 하지 않았다고 판단하여 요청을 차단한다.
- 따라서 클라이언트에서 데이터를 가져올 수 없다.

---

## ✅ CORS 해결 방법

### 1️⃣ 서버에서 CORS 설정 추가하기

#### 🔹 Node.js (Express)에서 CORS 허용
```js
const express = require('express');
const cors = require('cors'); // CORS 모듈 추가

const app = express();

app.use(cors()); // 모든 출처 허용

app.get('/data', (req, res) => {
    res.json({ message: "CORS 설정 완료!" });
});

app.listen(5000, () => console.log('서버 실행 중: http://localhost:5000'));
```

### 2️⃣ 특정 출처만 허용하기
보안 강화를 위해 **특정 도메인만 허용**할 수도 있다.

```js
app.use(cors({
    origin: 'http://localhost:3000' // 특정 출처 허용
}));
```

### 3️⃣ 응답 헤더에 직접 추가
서버에서 응답할 때 **CORS 관련 헤더를 추가**할 수도 있다.

```js
app.get('/data', (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*'); // 모든 출처 허용
    res.json({ message: "CORS 헤더 추가 완료!" });
});
```

---

## 🛑 Preflight Request (사전 요청)
**CORS 요청 중 일부는 "사전 요청(Preflight Request)"이 필요**하다.  
이는 브라우저가 **실제 요청 전에 서버가 허용하는지 확인하는 과정**이다.

### ✅ Preflight Request가 필요한 경우
- `PUT`, `DELETE`, `PATCH` 같은 HTTP 메서드를 사용할 때
- `Content-Type`이 `application/json` 같은 커스텀 헤더를 포함할 때

### ✨ 해결 방법 (Preflight 요청 허용)
```js
app.use(cors({
    origin: 'http://localhost:3000',
    methods: 'GET, POST, PUT, DELETE',
    allowedHeaders: 'Content-Type'
}));
```

---

## 📌 CORS 오류 해결 체크리스트
✅ 서버에서 `Access-Control-Allow-Origin` 헤더 추가했는가?  
✅ `cors()` 미들웨어를 추가했는가?  
✅ 필요한 경우 Preflight 요청을 허용했는가?  
✅ 특정 출처만 허용해야 하는 경우 `origin` 설정을 정확히 했는가?



