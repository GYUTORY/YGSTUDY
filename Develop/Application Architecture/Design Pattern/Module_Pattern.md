# 모듈 패턴 (Module Pattern) 📦

## 1. 모듈 패턴이란?
- **모듈 패턴(Module Pattern)** 은 코드를 여러 파일로 나누어 **재사용성을 높이고**, **네임스페이스 오염을 방지**하는 패턴입니다.

- Node.js에서는 `require()` 또는 `import`를 사용하여 모듈을 불러올 수 있습니다.
- 모듈을 사용하면 코드를 **더 구조적으로 관리**할 수 있습니다.

---

## 2. 기본적인 모듈 패턴 사용법 ✨

### 📌 모듈을 만들고 내보내기 (Export)

```javascript
// math.js (모듈 파일)

// 덧셈 함수 정의
function add(a, b) {
    return a + b;
}

// 뺄셈 함수 정의
function subtract(a, b) {
    return a - b;
}

// 곱셈 함수 정의
function multiply(a, b) {
    return a * b;
}

// 나눗셈 함수 정의
function divide(a, b) {
    if (b === 0) throw new Error("0으로 나눌 수 없습니다!");
    return a / b;
}

// 모듈 내보내기
module.exports = {
    add,
    subtract,
    multiply,
    divide
};
```

> `module.exports`를 사용하여 여러 개의 함수를 외부에서 사용할 수 있도록 내보냅니다.

---

### 📌 모듈을 불러와서 사용하기 (Import)

```javascript
// main.js (메인 파일)

// math.js 모듈 불러오기
const math = require('./math');  

// 모듈 내 함수 사용하기
console.log(math.add(2, 3));       // 5
console.log(math.subtract(10, 4)); // 6
console.log(math.multiply(3, 5));  // 15
console.log(math.divide(8, 2));    // 4
```

> `require('./math')`를 사용하여 모듈을 가져오고, 내보낸 함수를 사용할 수 있습니다.

---

## 3. 모듈 패턴의 다양한 방식

### 📌 특정 함수만 내보내기
```javascript
// greeting.js (모듈 파일)

// 특정 함수만 내보내기
module.exports = function(name) {
    return `안녕하세요, ${name}님!`;
};
```

```javascript
// main.js (메인 파일)

// greeting 모듈 불러오기
const greet = require('./greeting');

console.log(greet("철수")); // 안녕하세요, 철수님!
```

> `module.exports = function(...)` 방식으로 **단일 함수만** 내보낼 수도 있습니다.

---

### 📌 클래스(Class)를 이용한 모듈 패턴
```javascript
// User.js (모듈 파일)

// User 클래스 정의
class User {
    constructor(name) {
        this.name = name;
    }

    sayHello() {
        return `안녕하세요! 저는 ${this.name}입니다.`;
    }
}

// User 클래스를 모듈로 내보내기
module.exports = User;
```

```javascript
// main.js (메인 파일)

// User 모듈 불러오기
const User = require('./User');

const user1 = new User("영희");
console.log(user1.sayHello()); // 안녕하세요! 저는 영희입니다.
```

> 클래스도 모듈로 내보낼 수 있으며, 여러 개의 인스턴스를 생성할 수 있습니다.

---

## 4. `exports` vs `module.exports` 차이점

| 구분 | 설명 |
|------|------|
| `module.exports` | 객체, 함수, 클래스 등 **모든 값**을 내보낼 수 있음 |
| `exports` | 기본적으로 `{}` 객체이며, 속성을 추가하는 방식으로 내보낼 수 있음 |

### 📌 `exports` 사용 예시
```javascript
// utils.js (모듈 파일)

// 여러 개의 함수 추가 가능
exports.sayHello = function() {
    return "Hello!";
};

exports.sayBye = function() {
    return "Goodbye!";
};
```

```javascript
// main.js (메인 파일)

// utils 모듈 불러오기
const utils = require('./utils');

console.log(utils.sayHello()); // Hello!
console.log(utils.sayBye());   // Goodbye!
```

> `exports`는 `{}` 객체이므로, 개별적인 속성으로 함수를 추가하여 내보낼 수 있습니다.

---

## 5. 모듈 캐싱 (Caching) ⚡️

Node.js에서 모듈은 **한 번 로드되면 캐싱**됩니다. 즉, 같은 모듈을 여러 번 `require()` 해도 **처음 로드된 객체가 재사용**됩니다.

```javascript
// counter.js (모듈 파일)
let count = 0;

function increment() {
    count++;
    console.log(`현재 카운트: ${count}`);
}

module.exports = { increment };
```

```javascript
// main.js (메인 파일)
const counter1 = require('./counter');
const counter2 = require('./counter');

counter1.increment(); // 현재 카운트: 1
counter2.increment(); // 현재 카운트: 2 (같은 인스턴스 공유)
```

> `counter1`과 `counter2`가 같은 모듈을 참조하고 있어, `count` 값이 공유됩니다.

---

## 6. ES6 모듈 (`import`, `export`) 사용하기 ✨

Node.js는 기본적으로 CommonJS(`require()`)를 사용하지만, **ES6 모듈(`import`, `export`)도 지원**합니다.

### 📌 ES6 모듈 내보내기
```javascript
// math.mjs (ES6 모듈 파일)
export function add(a, b) {
    return a + b;
}

export function subtract(a, b) {
    return a - b;
}
```

### 📌 ES6 모듈 불러오기
```javascript
// main.mjs (ES6 모듈 파일)
import { add, subtract } from './math.mjs';

console.log(add(5, 3));      // 8
console.log(subtract(10, 2)); // 8
```

> ES6 모듈을 사용하려면 파일 확장자를 `.mjs`로 해야 합니다.
