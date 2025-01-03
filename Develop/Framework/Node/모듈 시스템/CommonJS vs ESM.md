
# CommonJS vs ESM

Node.js에서 모듈을 사용하는 방식은 **CommonJS**와 **ESM(ECMAScript Modules)** 두 가지가 있습니다. 각 방식은 모듈 정의와 가져오는 방식에서 차이가 있으며, 사용되는 환경이나 요구 사항에 따라 적합한 방식을 선택해야 합니다.

## CommonJS

### 특징
1. **Node.js에서 기본적으로 지원**: CommonJS는 Node.js의 기본 모듈 시스템입니다.
2. **`require`와 `module.exports` 사용**: 모듈을 가져오고 내보낼 때 `require`와 `module.exports`를 사용합니다.
3. **동기적 로딩**: CommonJS는 파일을 동기적으로 로드합니다.

### 문법 예시

#### 모듈 내보내기 (export)
```javascript
// math.js
function add(a, b) {
  return a + b;
}

module.exports = { add };
```

#### 모듈 가져오기 (import)
```javascript
// app.js
const math = require('./math');
console.log(math.add(2, 3)); // 출력: 5
```

### 장단점

- **장점**: 간단하고 널리 사용됨. 기존 Node.js 프로젝트에서 호환성이 뛰어남.
- **단점**: 동기적 로딩으로 인해 브라우저 환경에서는 비효율적일 수 있음.

---

## ESM (ECMAScript Modules)

### 특징
1. **JavaScript의 표준 모듈 시스템**: 브라우저와 Node.js 모두에서 사용 가능.
2. **`import`와 `export` 사용**: 모듈을 가져오고 내보낼 때 `import`와 `export`를 사용합니다.
3. **비동기적 로딩**: ESM은 비동기로 로딩하여 브라우저와 서버 모두에서 효율적으로 작동합니다.

### 문법 예시

#### 모듈 내보내기 (export)
```javascript
// math.mjs
export function add(a, b) {
  return a + b;
}
```

#### 모듈 가져오기 (import)
```javascript
// app.mjs
import { add } from './math.mjs';
console.log(add(2, 3)); // 출력: 5
```

### 장단점

- **장점**: 표준화된 방식으로 브라우저와 서버에서 일관된 사용 가능. 비동기 로딩으로 성능 개선.
- **단점**: 기존 Node.js 프로젝트와 호환하려면 추가 설정이 필요할 수 있음.

---

## 주요 차이점

| 특성                  | CommonJS                   | ESM                        |
|-----------------------|----------------------------|----------------------------|
| 모듈 시스템           | Node.js의 기본 시스템      | JavaScript의 표준 시스템   |
| 문법                  | `require`, `module.exports`| `import`, `export`         |
| 로딩 방식             | 동기적 로딩               | 비동기적 로딩              |
| 브라우저 지원         | 기본적으로 지원 안 함      | 기본적으로 지원            |
| 사용 파일 확장자       | `.js`                     | `.mjs` 또는 `.js` (설정 필요)|

---

## CommonJS vs ESM 예제 비교

### CommonJS
```javascript
// greetings.js
module.exports = function(name) {
  return `Hello, ${name}!`;
};

// app.js
const greet = require('./greetings');
console.log(greet('World')); // 출력: Hello, World!
```

### ESM
```javascript
// greetings.mjs
export default function(name) {
  return `Hello, ${name}!`;
}

// app.mjs
import greet from './greetings.mjs';
console.log(greet('World')); // 출력: Hello, World!
```

---

## 사용 시 고려사항

1. **프로젝트 환경**: 브라우저 또는 Node.js 환경에 따라 적합한 방식을 선택하세요.
2. **호환성**: 기존 코드베이스가 CommonJS를 사용한다면 그대로 유지하거나, 점진적으로 ESM으로 마이그레이션하세요.
3. **성능**: 브라우저 환경에서는 ESM의 비동기 로딩이 더 적합합니다.

---

## 참고 자료

- [Node.js 공식 문서: Modules](https://nodejs.org/docs/latest/api/modules.html)
- [MDN Web Docs: ESM](https://developer.mozilla.org/ko/docs/Web/JavaScript/Guide/Modules)
