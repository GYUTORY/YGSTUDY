---
title: ESM CommonJS
tags: [language, javascript, 09es6및고급문법, es6, esm과-commonjs]
updated: 2025-08-10
---
# ESM과 CommonJS 모듈 시스템 완벽 가이드

## 배경

### 모듈(Module)이란?
- **모듈**은 코드를 기능별로 나누어 관리하는 단위입니다
- 예를 들어, 계산기 앱을 만들 때 덧셈, 뺄셈, 곱셈, 나눗셈 기능을 각각 다른 파일로 나누어 관리하는 것
- 이렇게 나누면 코드가 깔끔해지고, 다른 프로젝트에서도 재사용할 수 있습니다

### 모듈 시스템이 필요한 이유
- JavaScript는 원래 모듈 시스템이 없었습니다
- 모든 코드가 하나의 파일에 있어서 복잡한 프로젝트에서는 관리가 어려웠습니다
- 그래서 코드를 나누어 관리할 수 있는 방법이 필요했고, **CommonJS**와 **ESM**이 등장했습니다

---

- JavaScript는 원래 모듈 시스템이 없었습니다
- 모든 코드가 하나의 파일에 있어서 복잡한 프로젝트에서는 관리가 어려웠습니다
- 그래서 코드를 나누어 관리할 수 있는 방법이 필요했고, **CommonJS**와 **ESM**이 등장했습니다

---


### Node.js에서의 혼용 사용

Node.js에서는 ESM과 CommonJS를 함께 사용할 수 있지만, 몇 가지 규칙이 있습니다:

#### ESM에서 CommonJS 가져오기
```javascript
// 📁 math.cjs (CommonJS 파일)
module.exports = {
    add: (a, b) => a + b,
    subtract: (a, b) => a - b
};

// 📁 main.mjs (ESM 파일)
// 방법 1: 동적 import 사용
const math = await import('./math.cjs');
console.log(math.add(2, 3)); // 5

// 방법 2: createRequire 사용
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const math = require('./math.cjs');
console.log(math.add(2, 3)); // 5
```

#### CommonJS에서 ESM 가져오기
```javascript
// 📁 math.mjs (ESM 파일)
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;

// 📁 main.js (CommonJS 파일)
// CommonJS에서는 ESM을 직접 require할 수 없습니다
// 대신 동적 import를 사용해야 합니다
async function loadMath() {
    const math = await import('./math.mjs');
    console.log(math.add(2, 3)); // 5
}

loadMath();
```

---


### ESM을 선택해야 하는 경우
- **새로운 프로젝트**를 시작할 때
- **최신 브라우저**를 지원해야 할 때
- **코드 최적화**가 중요할 때
- **비동기 모듈 로딩**이 필요할 때

### CommonJS를 선택해야 하는 경우
- **기존 Node.js 프로젝트**를 유지보수할 때
- **레거시 라이브러리**와 호환성이 필요할 때
- **동적 모듈 로딩**이 자주 필요할 때

### package.json 설정

#### ESM 프로젝트 설정
```json
{
  "name": "my-esm-project",
  "type": "module",
  "main": "index.js"
}
```

#### CommonJS 프로젝트 설정
```json
{
  "name": "my-commonjs-project",
  "main": "index.js"
}
```

---


### 1. 파일 확장자 문제
```javascript
// ❌ ESM에서 확장자 생략 시 오류
import { add } from './math'; // 오류!

// ✅ 올바른 방법
import { add } from './math.js';
```

### 2. __dirname, __filename 사용
```javascript
// ❌ ESM에서는 사용할 수 없음
console.log(__dirname); // 오류!

// ✅ ESM에서 대체 방법
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
console.log(__dirname); // 정상 작동
```

### 3. 조건부 모듈 로딩
```javascript
// CommonJS - 동적 로딩 가능
let math;
if (process.env.NODE_ENV === 'production') {
    math = require('./math.prod.js');
} else {
    math = require('./math.dev.js');
}

// ESM - 정적 로딩만 가능
import { add } from './math.js'; // 항상 같은 파일
```

---


### 모듈을 찾을 수 없을 때
1. **파일 경로 확인**: 상대 경로가 올바른지 확인
2. **파일 확장자 확인**: ESM에서는 확장자 필수
3. **package.json 설정 확인**: `"type": "module"` 설정 여부

### 호환성 문제 해결
1. **파일 확장자 변경**: `.js` → `.mjs` 또는 `.cjs`
2. **동적 import 사용**: CommonJS에서 ESM 가져올 때
3. **createRequire 사용**: ESM에서 CommonJS 가져올 때

1. **파일 경로 확인**: 상대 경로가 올바른지 확인
2. **파일 확장자 확인**: ESM에서는 확장자 필수
3. **package.json 설정 확인**: `"type": "module"` 설정 여부

1. **파일 확장자 변경**: `.js` → `.mjs` 또는 `.cjs`
2. **동적 import 사용**: CommonJS에서 ESM 가져올 때
3. **createRequire 사용**: ESM에서 CommonJS 가져올 때






- JavaScript는 원래 모듈 시스템이 없었습니다
- 모든 코드가 하나의 파일에 있어서 복잡한 프로젝트에서는 관리가 어려웠습니다
- 그래서 코드를 나누어 관리할 수 있는 방법이 필요했고, **CommonJS**와 **ESM**이 등장했습니다

---

- JavaScript는 원래 모듈 시스템이 없었습니다
- 모든 코드가 하나의 파일에 있어서 복잡한 프로젝트에서는 관리가 어려웠습니다
- 그래서 코드를 나누어 관리할 수 있는 방법이 필요했고, **CommonJS**와 **ESM**이 등장했습니다

---


1. **파일 경로 확인**: 상대 경로가 올바른지 확인
2. **파일 확장자 확인**: ESM에서는 확장자 필수
3. **package.json 설정 확인**: `"type": "module"` 설정 여부

1. **파일 확장자 변경**: `.js` → `.mjs` 또는 `.cjs`
2. **동적 import 사용**: CommonJS에서 ESM 가져올 때
3. **createRequire 사용**: ESM에서 CommonJS 가져올 때

1. **파일 경로 확인**: 상대 경로가 올바른지 확인
2. **파일 확장자 확인**: ESM에서는 확장자 필수
3. **package.json 설정 확인**: `"type": "module"` 설정 여부

1. **파일 확장자 변경**: `.js` → `.mjs` 또는 `.cjs`
2. **동적 import 사용**: CommonJS에서 ESM 가져올 때
3. **createRequire 사용**: ESM에서 CommonJS 가져올 때










## 🔄 ESM(ECMAScript Modules)

### ESM이란?
- **ESM**은 JavaScript의 공식 표준 모듈 시스템입니다
- 2015년에 도입되어 현재는 모든 최신 브라우저와 Node.js에서 지원합니다
- `import`와 `export` 키워드를 사용합니다

### ESM의 핵심 특징

#### 1. 정적 구조 (Static Structure)
- 코드가 실행되기 전에 모듈 간의 관계를 미리 파악합니다
- 이 덕분에 코드 최적화가 가능하고, 사용하지 않는 코드를 제거할 수 있습니다

#### 2. 파일 확장자 필수
- ESM에서는 반드시 파일 확장자를 명시해야 합니다
- `.js`, `.mjs` 확장자를 사용합니다

### ESM 기본 사용법

#### 📁 math.js (모듈 파일)
```javascript
// 개별 함수 내보내기
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export const multiply = (a, b) => a * b;

// 기본 내보내기 (한 번에 하나만 가능)
export default function divide(a, b) {
    return a / b;
}

// 상수도 내보낼 수 있습니다
export const PI = 3.14159;
```

#### 📁 main.js (모듈 가져오기)
```javascript
// 개별 함수 가져오기
import { add, subtract, multiply } from './math.js';

// 기본 내보내기 가져오기 (이름을 바꿀 수 있음)
import divideFunction from './math.js';

// 모든 것을 한 번에 가져오기
import * as MathUtils from './math.js';

console.log(add(5, 3));        // 8
console.log(subtract(10, 4));  // 6
console.log(multiply(2, 7));   // 14
console.log(divideFunction(15, 3)); // 5
console.log(MathUtils.PI);     // 3.14159
```

### ESM 고급 사용법

#### 📁 user.js
```javascript
// 클래스 내보내기
export class User {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    sayHello() {
        return `안녕하세요! 저는 ${this.name}입니다.`;
    }
}

// 함수를 기본 내보내기로 설정
export default function createUser(name, age) {
    return new User(name, age);
}
```

#### 📁 app.js
```javascript
// 클래스 가져오기
import { User } from './user.js';

// 기본 함수 가져오기
import createUser from './user.js';

const user1 = new User('김철수', 25);
const user2 = createUser('이영희', 30);

console.log(user1.sayHello()); // "안녕하세요! 저는 김철수입니다."
console.log(user2.sayHello()); // "안녕하세요! 저는 이영희입니다."
```

---

## 🛠️ CommonJS

### CommonJS란?
- **CommonJS**는 Node.js에서 주로 사용하는 모듈 시스템입니다
- ESM이 나오기 전에 JavaScript에서 모듈을 관리하는 표준 방법이었습니다
- `require`와 `module.exports`를 사용합니다

### CommonJS의 핵심 특징

#### 1. 동적 구조 (Dynamic Structure)
- 코드가 실행되는 동안에 모듈을 가져올 수 있습니다
- 조건에 따라 다른 모듈을 가져올 수 있어 유연합니다

#### 2. 파일 확장자 선택사항
- `.js`, `.cjs` 확장자를 사용하지만, 생략해도 됩니다

### CommonJS 기본 사용법

#### 📁 math.js (모듈 파일)
```javascript
// 함수 정의
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;
const multiply = (a, b) => a * b;

// 여러 함수를 객체로 내보내기
module.exports = {
    add,
    subtract,
    multiply
};

// 상수도 추가할 수 있습니다
module.exports.PI = 3.14159;
```

#### 📁 main.js (모듈 가져오기)
```javascript
// 전체 모듈 가져오기
const math = require('./math.js');

// 구조 분해 할당으로 개별 함수 가져오기
const { add, subtract, multiply } = require('./math.js');

console.log(math.add(5, 3));      // 8
console.log(add(10, 4));          // 14
console.log(math.PI);             // 3.14159
```

### CommonJS 고급 사용법

#### 📁 user.js
```javascript
// 클래스 정의
class User {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    sayHello() {
        return `안녕하세요! 저는 ${this.name}입니다.`;
    }
}

// 클래스 내보내기
module.exports = User;

// 추가로 함수도 내보낼 수 있습니다
module.exports.createUser = function(name, age) {
    return new User(name, age);
};
```

#### 📁 app.js
```javascript
// 클래스 가져오기
const User = require('./user.js');

// 추가 함수 가져오기
const { createUser } = require('./user.js');

const user1 = new User('김철수', 25);
const user2 = createUser('이영희', 30);

console.log(user1.sayHello()); // "안녕하세요! 저는 김철수입니다."
console.log(user2.sayHello()); // "안녕하세요! 저는 이영희입니다."
```

---

## 📊 ESM과 CommonJS 비교표

| 구분 | ESM | CommonJS |
|------|-----|----------|
| **구문** | `import` / `export` | `require` / `module.exports` |
| **로딩 방식** | 정적 (컴파일 시점) | 동적 (실행 시점) |
| **사용 환경** | 브라우저, Node.js | 주로 Node.js |
| **파일 확장자** | `.js`, `.mjs` (필수) | `.js`, `.cjs` (선택) |
| **비동기 지원** | ✅ 지원 | ❌ 미지원 |
| **표준화** | ✅ 공식 표준 | ❌ Node.js 전용 |

---

