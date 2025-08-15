---
title: CommonJS vs ESM (ECMAScript Modules)
tags: [framework, node, 모듈-시스템, commonjs, esm, nodejs]
updated: 2024-12-19
---

# CommonJS vs ESM (ECMAScript Modules)

## 배경

### CommonJS와 ESM이란?
Node.js에서 모듈을 사용하는 방식은 크게 **CommonJS (CJS)**와 **ECMAScript Modules (ESM)** 두 가지로 나뉩니다.

| 모듈 시스템 | 설명 |
|------------|----------------------------------------|
| **CommonJS (CJS)** | Node.js에서 기본적으로 사용되던 모듈 시스템 |
| **ECMAScript Modules (ESM)** | 최신 JavaScript 표준 모듈 시스템 |

CommonJS는 Node.js의 기존 방식이고, ESM은 최신 JavaScript 표준 방식입니다.

### 모듈 시스템의 필요성
- 코드의 재사용성과 유지보수성 향상
- 네임스페이스 분리로 전역 변수 오염 방지
- 의존성 관리와 로딩 순서 제어
- 코드의 구조화와 모듈화

## 핵심

### CommonJS (CJS) 개념 및 사용법

#### CommonJS 특징
- `require()`을 사용하여 모듈을 불러옴
- `module.exports` 또는 `exports`를 사용하여 모듈을 내보냄
- 동기적으로 모듈을 로드함
- Node.js에서 기본적으로 지원되며, `package.json` 설정 없이 사용 가능

#### CommonJS 예제

##### 모듈 내보내기 (export)
```javascript
// math.js
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;

// 모듈 내보내기
module.exports = { add, subtract };
```

##### 모듈 가져오기 (import)
```javascript
// main.js
const math = require('./math'); // require() 사용

console.log(math.add(5, 3)); // 8
console.log(math.subtract(5, 3)); // 2
```

CommonJS에서는 `require()`을 사용하여 모듈을 가져옵니다.

### ECMAScript Modules (ESM) 개념 및 사용법

#### ESM 특징
- `import` / `export` 문법 사용
- 비동기적으로 모듈을 로드할 수 있음
- `package.json`에 `"type": "module"` 설정이 필요
- 최신 JavaScript 표준으로 브라우저와 Node.js에서 모두 사용 가능

#### ESM 예제

##### 모듈 내보내기 (export)
```javascript
// math.mjs
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
```

##### 모듈 가져오기 (import)
```javascript
// main.mjs
import { add, subtract } from './math.mjs'; // import 사용

console.log(add(5, 3)); // 8
console.log(subtract(5, 3)); // 2
```

#### ESM을 사용하려면?
1. **파일 확장자를 `.mjs`로 변경**하거나
2. **`package.json`에 `"type": "module"`을 추가**해야 함

```json
{
  "type": "module"
}
```

ESM에서는 `import` / `export` 문법을 사용합니다.

## 예시

### CommonJS vs ESM 차이점

| 비교 항목 | CommonJS (CJS) | ESM (ECMAScript Modules) |
|-----------|----------------|-------------------------|
| **모듈 불러오기** | `require()` | `import` |
| **모듈 내보내기** | `module.exports` | `export` |
| **로딩 방식** | 동기적 (synchronous) | 비동기적 (asynchronous 가능) |
| **Node.js 기본 지원** | ✅ 기본 지원 | ❌ `package.json` 설정 필요 |
| **브라우저 지원** | ❌ 지원 안 함 | ✅ 브라우저에서 사용 가능 |
| **실행 속도** | 빠름 (캐싱됨) | 더 빠름 (최적화 가능) |
| **사용 용도** | 기존 Node.js 프로젝트 | 최신 JavaScript 및 웹 프로젝트 |

ESM은 최신 JavaScript 표준이며, 브라우저와 Node.js에서 모두 사용 가능합니다.

### 다양한 내보내기/가져오기 패턴

#### CommonJS 패턴
```javascript
// math.js
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;
const multiply = (a, b) => a * b;

// 개별 내보내기
module.exports.add = add;
module.exports.subtract = subtract;

// 또는 객체로 한 번에 내보내기
module.exports = { add, subtract, multiply };

// 또는 exports 사용
exports.add = add;
exports.subtract = subtract;
```

```javascript
// main.js
// 전체 모듈 가져오기
const math = require('./math');
console.log(math.add(5, 3));

// 구조분해 할당으로 가져오기
const { add, subtract } = require('./math');
console.log(add(5, 3));
```

#### ESM 패턴
```javascript
// math.mjs
// 개별 내보내기
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;

// 기본 내보내기
const multiply = (a, b) => a * b;
export default multiply;

// 또는 모든 것을 한 번에 내보내기
export { add, subtract, multiply as default };
```

```javascript
// main.mjs
// 개별 가져오기
import { add, subtract } from './math.mjs';

// 기본 내보내기 가져오기
import multiply from './math.mjs';

// 모든 것을 가져오기
import * as math from './math.mjs';

// 기본과 개별을 함께 가져오기
import multiply, { add, subtract } from './math.mjs';
```

### 동적 모듈 로딩

#### CommonJS 동적 로딩
```javascript
// 조건부 모듈 로딩
let math;
if (process.env.NODE_ENV === 'production') {
    math = require('./math.prod');
} else {
    math = require('./math.dev');
}
```

#### ESM 동적 로딩
```javascript
// 동적 import (비동기)
async function loadMath() {
    const math = await import('./math.mjs');
    return math;
}

// 조건부 동적 로딩
async function loadConditionalModule() {
    if (process.env.NODE_ENV === 'production') {
        const module = await import('./production.mjs');
        return module;
    } else {
        const module = await import('./development.mjs');
        return module;
    }
}
```

## 운영 팁

### CommonJS vs ESM 사용 시 주의할 점

#### CommonJS에서 ESM 모듈을 불러올 때
CommonJS 환경에서는 ESM 모듈을 직접 불러올 수 없습니다.

```javascript
// 오류 발생
const { add } = await import('./math.mjs');
```

해결 방법: 동적 `import()` 사용
```javascript
(async () => {
    const math = await import('./math.mjs');
    console.log(math.add(5, 3)); // 8
})();
```

#### ESM에서 CommonJS 모듈을 불러올 때
```javascript
// 오류 발생 (CJS 모듈은 import 불가능)
import math from './math.js';
```

해결 방법: `createRequire` 사용
```javascript
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const math = require('./math.js');

console.log(math.add(5, 3)); // 8
```

CommonJS와 ESM은 완전히 다른 방식이므로, 섞어 쓸 경우 주의해야 합니다.

### 프로젝트 마이그레이션 전략

#### 단계적 마이그레이션
1. **새로운 파일은 ESM으로 작성**
2. **기존 CommonJS 파일은 점진적으로 변환**
3. **호환성 문제가 있는 라이브러리는 유지**

#### package.json 설정
```json
{
  "type": "module",
  "exports": {
    ".": {
      "import": "./index.mjs",
      "require": "./index.cjs"
    }
  }
}
```

### 성능 최적화
```javascript
// ESM에서 트리 쉐이킹 활용
import { add } from './math.mjs'; // subtract는 번들에 포함되지 않음

// CommonJS에서는 전체 모듈 로드
const math = require('./math'); // 모든 함수가 로드됨
```

## 참고

### 모듈 시스템 선택 가이드

| 상황 | 권장 모듈 시스템 | 이유 |
|------|----------------|------|
| **새로운 프로젝트** | ESM | 최신 표준, 브라우저 호환성 |
| **기존 Node.js 프로젝트** | CommonJS | 안정성, 호환성 |
| **라이브러리 개발** | 둘 다 지원 | 사용자 호환성 |
| **브라우저 환경** | ESM | 네이티브 지원 |

### 모듈 시스템 관련 도구
- **Babel**: ES6+ 코드를 ES5로 변환
- **Webpack**: 모듈 번들링 및 변환
- **Rollup**: ESM 기반 번들러
- **ESLint**: 모듈 시스템 규칙 검사

### 결론
CommonJS와 ESM은 각각의 장단점이 있습니다.
CommonJS는 Node.js에서 안정적이고 호환성이 좋지만,
ESM은 최신 JavaScript 표준으로 브라우저와 Node.js에서 모두 사용할 수 있습니다.
프로젝트의 요구사항과 환경에 따라 적절한 모듈 시스템을 선택하는 것이 중요합니다.
