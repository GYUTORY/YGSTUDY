

# 🚀 CommonJS vs ESM (ECMAScript Modules) 차이

## 1️⃣ CommonJS와 ESM이란?
Node.js에서 모듈을 사용하는 방식은 크게 **CommonJS (CJS)**와 **ECMAScript Modules (ESM)** 두 가지로 나뉩니다.

| 모듈 시스템 | 설명 |
|------------|----------------------------------------|
| **CommonJS (CJS)** | Node.js에서 기본적으로 사용되던 모듈 시스템 |
| **ECMAScript Modules (ESM)** | 최신 JavaScript 표준 모듈 시스템 |

> **👉🏻 CommonJS는 Node.js의 기존 방식이고, ESM은 최신 JavaScript 표준 방식입니다.**

---

## 2️⃣ CommonJS (CJS) 개념 및 사용법

### ✅ CommonJS 특징
- `require()`을 사용하여 모듈을 불러옴
- `module.exports` 또는 `exports`를 사용하여 모듈을 내보냄
- 동기적으로 모듈을 로드함
- **Node.js에서 기본적으로 지원되며, `package.json` 설정 없이 사용 가능**

### ✨ CommonJS 예제

#### **모듈 내보내기 (export)**
```javascript
// math.js
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;

// 모듈 내보내기
module.exports = { add, subtract };
```

#### **모듈 가져오기 (import)**
```javascript
// main.js
const math = require('./math'); // require() 사용

console.log(math.add(5, 3)); // 8
console.log(math.subtract(5, 3)); // 2
```

> **👉🏻 CommonJS에서는 `require()`을 사용하여 모듈을 가져옵니다.**

---

## 3️⃣ ECMAScript Modules (ESM) 개념 및 사용법

### ✅ ESM 특징
- `import` / `export` 문법 사용
- 비동기적으로 모듈을 로드할 수 있음
- `package.json`에 `"type": "module"` 설정이 필요
- 최신 JavaScript 표준으로 **브라우저와 Node.js에서 모두 사용 가능**

### ✨ ESM 예제

#### **모듈 내보내기 (export)**
```javascript
// math.mjs
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
```

#### **모듈 가져오기 (import)**
```javascript
// main.mjs
import { add, subtract } from './math.mjs'; // import 사용

console.log(add(5, 3)); // 8
console.log(subtract(5, 3)); // 2
```

### ✅ ESM을 사용하려면?
1️⃣ **파일 확장자를 `.mjs`로 변경**하거나  
2️⃣ **`package.json`에 `"type": "module"`을 추가**해야 함

```json
{
  "type": "module"
}
```

> **👉🏻 ESM에서는 `import` / `export` 문법을 사용합니다.**

---

## 4️⃣ CommonJS vs ESM 차이점

| 비교 항목 | CommonJS (CJS) | ESM (ECMAScript Modules) |
|-----------|----------------|-------------------------|
| **모듈 불러오기** | `require()` | `import` |
| **모듈 내보내기** | `module.exports` | `export` |
| **로딩 방식** | 동기적 (synchronous) | 비동기적 (asynchronous 가능) |
| **Node.js 기본 지원** | ✅ 기본 지원 | ❌ `package.json` 설정 필요 |
| **브라우저 지원** | ❌ 지원 안 함 | ✅ 브라우저에서 사용 가능 |
| **실행 속도** | 빠름 (캐싱됨) | 더 빠름 (최적화 가능) |
| **사용 용도** | 기존 Node.js 프로젝트 | 최신 JavaScript 및 웹 프로젝트 |

> **👉🏻 ESM은 최신 JavaScript 표준이며, 브라우저와 Node.js에서 모두 사용 가능합니다.**

---

## 5️⃣ CommonJS vs ESM 사용 시 주의할 점

### ✅ CommonJS에서 ESM 모듈을 불러올 때
CommonJS 환경에서는 **ESM 모듈을 직접 불러올 수 없음**
```javascript
const { add } = await import('./math.mjs'); // 오류 발생
```
✅ 해결 방법: **동적 `import()` 사용**
```javascript
(async () => {
    const math = await import('./math.mjs');
    console.log(math.add(5, 3)); // 8
})();
```

### ✅ ESM에서 CommonJS 모듈을 불러올 때
```javascript
import math from './math.js'; // 오류 발생 (CJS 모듈은 `import` 불가능)
```
✅ 해결 방법: **`createRequire` 사용**
```javascript
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const math = require('./math.js');

console.log(math.add(5, 3)); // 8
```

> **👉🏻 CommonJS와 ESM은 완전히 다른 방식이므로, 섞어 쓸 경우 주의해야 합니다!**

