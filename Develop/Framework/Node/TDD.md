

# 🚀 Node.js TDD(Test-Driven Development) 개념과 예제

## ✨ TDD란?
TDD(Test-Driven Development, **테스트 주도 개발**)는 **테스트를 먼저 작성하고, 이후에 실제 코드를 구현하는 방식**이다.  
즉, 기능을 개발하기 전에 먼저 테스트를 작성한 후, 테스트를 통과할 수 있도록 코드를 작성하는 개발 방법론이다.

---

## 🎯 TDD 개발 프로세스
TDD는 **Red ➝ Green ➝ Refactor** 3단계를 반복한다.

1️⃣ **Red(실패)**: 먼저 **테스트를 작성**하고 실행 → 당연히 처음에는 실패  
2️⃣ **Green(성공)**: 테스트를 통과할 수 있도록 **최소한의 코드**를 작성  
3️⃣ **Refactor(리팩토링)**: 중복 제거 및 코드 개선 (테스트는 계속 통과해야 함)

```plaintext
1. 테스트 코드 작성 (실패)  🔴 Red
2. 기능 코드 작성 (성공)  🟢 Green
3. 리팩토링 (성능 개선)  ♻️ Refactor
4. 반복...
```

---

## 🌐 Node.js에서 TDD를 위한 필수 패키지
TDD를 수행하려면 **테스트 프레임워크**가 필요하다.  
Node.js 환경에서는 아래 패키지들이 많이 사용된다.

| 패키지 | 설명 |
|--------|----------------------|
| `Jest` | 가장 인기 있는 JavaScript 테스트 프레임워크 |
| `Mocha` | 유연한 테스트 러너 |
| `Chai` | 가독성이 좋은 assertion 라이브러리 |
| `Supertest` | HTTP 요청 테스트를 위한 라이브러리 (Express API 테스트에 유용) |

👉🏻 **우리는 Jest + Supertest 조합을 사용할 것!**

---

## 🚀 TDD 예제: 간단한 API 테스트 및 개발

### 📌 프로젝트 초기 설정
```bash
mkdir node-tdd-example  # 프로젝트 폴더 생성
cd node-tdd-example

npm init -y             # package.json 생성

npm install express     # Express 설치
npm install jest supertest --save-dev  # Jest, Supertest 설치
```

### 📌 Jest 설정 (package.json 수정)
`package.json` 파일에서 `"scripts"` 부분을 아래처럼 수정

```json
"scripts": {
  "test": "jest"
}
```

---

## ✅ 1단계: 테스트 먼저 작성 (Red 🔴)

우리는 `/api/hello` 엔드포인트를 만들려고 한다.  
테스트 코드부터 먼저 작성해보자.

📌 `tests/app.test.js` 파일 생성 후, 아래 코드 작성

```js
const request = require("supertest"); // HTTP 요청 테스트 라이브러리
const app = require("../app"); // 우리가 만들 Express 앱

describe("GET /api/hello", () => {
    it("200 상태코드와 함께 'Hello, TDD!' 응답을 반환해야 한다", async () => {
        const response = await request(app).get("/api/hello"); // API 요청 보내기
        expect(response.status).toBe(200); // 응답 상태 코드가 200인지 확인
        expect(response.body.message).toBe("Hello, TDD!"); // 응답 데이터 확인
    });
});
```

📌 테스트 실행
```bash
npm test
```

👉🏻 당연히 테스트는 **실패한다**! (아직 API를 만들지 않았으니까)  
이제 실제 코드를 작성해 테스트를 통과시키자.

---

## ✅ 2단계: 실제 기능 코드 작성 (Green 🟢)

📌 `app.js` 파일 생성 후, Express 서버 코드 작성

```js
const express = require("express"); // Express 가져오기
const app = express();

// JSON 응답을 위해 설정
app.use(express.json());

// 📌 /api/hello 엔드포인트 생성 (테스트 통과를 위해 추가)
app.get("/api/hello", (req, res) => {
    res.status(200).json({ message: "Hello, TDD!" });
});

module.exports = app; // 서버 객체 내보내기
```

📌 `server.js` 파일 생성 후, 서버 실행 코드 작성

```js
const app = require("./app");

const PORT = 5000;
app.listen(PORT, () => console.log(`🚀 서버 실행 중: http://localhost:${PORT}`));
```

📌 다시 테스트 실행
```bash
npm test
```

✅ 이번에는 테스트가 **통과**할 것이다! 🎉

---

## ✅ 3단계: 리팩토링 (Refactor ♻️)

이제 코드 개선을 해보자.  
코드를 정리하고, 필요하면 중복 제거 등을 수행한다.

```js
// app.js
const express = require("express");
const app = express();

app.use(express.json());

// ✅ 엔드포인트들을 따로 파일로 분리 가능
const apiRouter = require("./routes/api");
app.use("/api", apiRouter);

module.exports = app;
```

📌 `routes/api.js` 파일을 생성하고, API 엔드포인트를 분리

```js
const express = require("express");
const router = express.Router();

router.get("/hello", (req, res) => {
    res.status(200).json({ message: "Hello, TDD!" });
});

module.exports = router;
```

📌 다시 테스트 실행하여 여전히 통과하는지 확인
```bash
npm test
```

✅ **테스트가 통과하면 리팩토링 성공!** 🚀

---

## 📌 추가적인 테스트

### 1️⃣ 새로운 API 엔드포인트 추가 후, 테스트 작성

📌 `tests/app.test.js` 파일에 새로운 테스트 추가

```js
describe("GET /api/greet", () => {
    it("200 상태코드와 함께 'Welcome to TDD!' 메시지를 반환해야 한다", async () => {
        const response = await request(app).get("/api/greet");
        expect(response.status).toBe(200);
        expect(response.body.message).toBe("Welcome to TDD!");
    });
});
```

📌 `routes/api.js`에 엔드포인트 추가

```js
router.get("/greet", (req, res) => {
    res.status(200).json({ message: "Welcome to TDD!" });
});
```

📌 테스트 실행
```bash
npm test
```

✅ 테스트를 추가하고 코드를 작성하여 **TDD를 반복적으로 적용**하는 것이 핵심이다.