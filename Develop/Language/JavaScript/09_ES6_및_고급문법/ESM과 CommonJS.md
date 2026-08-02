---
title: ESM과 CommonJS
tags: [language, javascript, 09es6및고급문법, es6, esm과-commonjs]
updated: 2026-07-17
---

# ESM과 CommonJS

JavaScript에는 모듈 시스템이 두 개 공존한다. Node.js가 2009년에 CommonJS를 채택해서 `require`/`module.exports` 방식을 정착시켰고, ES6(2015)에서 `import`/`export` 문법이 언어 표준으로 들어왔다. Node.js가 ESM을 v14에서야 안정 지원한 탓에 그 사이 수년간 CommonJS가 생태계를 지배했고, 지금도 두 시스템이 뒤섞인 코드베이스가 많다.

## CommonJS

### 래퍼 함수

Node.js는 파일을 실행하기 전에 내용을 함수로 감싼다.

```javascript
(function(exports, require, module, __filename, __dirname) {
    // 작성한 모듈 코드가 여기 들어간다
});
```

`__filename`과 `__dirname`이 전역 변수처럼 보이지만, 실제로는 래퍼 함수가 주입하는 인자다. ESM에서 이 두 변수가 없는 이유도 여기에 있다. ESM은 래퍼 함수 방식을 쓰지 않는다.

`exports`는 `module.exports`를 참조한다. `exports.foo = bar`는 잘 동작하지만, `exports = { foo: bar }`는 참조를 끊기 때문에 아무 효과가 없다.

### 기본 문법

```javascript
// math.js
const add = (a, b) => a + b;
const subtract = (a, b) => a - b;

module.exports = { add, subtract };
```

```javascript
// main.js
const { add } = require('./math');
const math = require('./math');

console.log(math === require('./math')); // true - 캐시에서 반환
```

### 모듈 캐시

CommonJS 모듈 캐시의 키는 해석된 절대 경로다.

```javascript
require('./math');
console.log(Object.keys(require.cache));
// ['/absolute/path/to/math.js']
```

같은 파일을 경로 표기를 달리해서 require해도 같은 캐시 엔트리를 반환한다. 테스트에서 모듈을 재실행해야 할 때 캐시를 직접 지운다.

```javascript
delete require.cache[require.resolve('./config')];
const freshConfig = require('./config');
```

`require.resolve()`는 모듈을 탐색만 하고 실행하지 않는다. 캐시 키 확인이나 파일 경로 조회에 쓴다.

조건에 따라 다른 모듈을 런타임에 로딩하는 것도 가능하다.

```javascript
const dbType = process.env.DB_TYPE || 'sqlite';
const db = require(`./adapters/${dbType}`);
```

## ESM

### 정적 분석과 로딩 단계

ESM은 실행 전에 모듈 그래프 전체를 파악한다. 파싱 → 인스턴스화 → 평가 세 단계를 거친다.

`import` 구문은 파싱 단계에서 처리된다. `if` 블록 안에 static import를 쓸 수 없는 이유다.

```javascript
// SyntaxError
if (condition) {
    import { foo } from './foo.js';
}
```

조건부 로딩은 dynamic import를 써야 한다.

```javascript
const module = await import(condition ? './a.js' : './b.js');
```

### Node.js에서 ESM 활성화

`package.json`에 `"type": "module"`을 추가하거나, 파일 확장자를 `.mjs`로 쓴다.

```json
{
  "type": "module"
}
```

ESM 파일에서는 상대 경로에 확장자를 명시해야 한다.

```javascript
// CJS는 확장자 생략 가능
// ESM은 확장자 필수
import { add } from './math.js';
```

### 기본 문법

```javascript
// math.js
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;

export default function multiply(a, b) {
    return a * b;
}
```

```javascript
// main.js
import multiply, { add, subtract } from './math.js';
import * as math from './math.js';
```

default export와 named export를 섞는 것은 가능하지만, 라이브러리를 소비할 때 혼동을 일으키는 경우가 많다. default export는 소비자가 이름을 자유롭게 짓기 때문에 IDE 자동완성 지원도 약해진다.

### import.meta 활용

ESM에는 `__dirname`과 `__filename`이 없다. `import.meta.url`로 현재 파일의 URL을 얻어서 직접 만든다.

```javascript
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 현재 파일 기준 상대 경로 조립
const configPath = resolve(__dirname, '../config/app.json');
```

단순히 `__dirname`을 대체하는 용도 외에도 쓸 곳이 있다. 현재 모듈을 기준으로 리소스 파일 경로를 동적으로 만들거나, `createRequire`에 넘겨 ESM 안에서 CJS require를 쓸 때도 사용한다.

```javascript
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const legacyLib = require('./legacy-module');
```

Node.js v20.6부터 `import.meta.resolve()`가 정식 지원된다. 모듈을 실제로 로딩하지 않고 경로만 해석한다.

```javascript
// 파일을 실행하지 않고 절대 URL만 반환
const resolvedPath = import.meta.resolve('./config.json');
// file:///project/src/config.json
```

### top-level await

ESM 모듈은 자체적으로 비동기로 처리된다. 그래서 모듈 최상위에서 `await`를 직접 쓸 수 있다.

```javascript
// config.js
const response = await fetch('https://api.example.com/config');
const config = await response.json();

export { config };
```

```javascript
// main.js
import { config } from './config.js';
// config는 이미 로딩 완료 상태다
console.log(config.apiKey);
```

`config.js`를 import하는 모듈은 `config.js`의 top-level await가 완료될 때까지 평가를 기다린다. fetch가 실패하면 해당 모듈을 import하는 쪽 전체가 실패한다. 초기화 지연이 의존 모듈 전체로 전파되기 때문에, 서버 시작 시 지연이 길어질 수 있다.

CommonJS에서는 top-level await를 쓸 수 없다. 흔히 보이는 우회 방법은 즉시 실행 async 함수다.

```javascript
// CommonJS에서의 우회
(async () => {
    const data = await fetchData();
    startServer(data);
})();
```

### ESM에서 JSON import

Node.js 22부터 JSON import가 정식 지원된다. `with { type: 'json' }` 구문을 쓴다.

```javascript
import data from './config.json' with { type: 'json' };

console.log(data.version);
```

Node.js 18~21에서는 `assert { type: 'json' }` 구문을 썼는데, 이 문법은 deprecated됐다.

```javascript
// Node.js 18~21 (deprecated)
import data from './config.json' assert { type: 'json' };
```

Node.js 18 이하나 JSON import가 부담스러운 경우, `createRequire`를 쓰거나 `fs`로 직접 읽는다.

```javascript
// createRequire 방법
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const config = require('./config.json');

// fs 방법
import { readFileSync } from 'fs';
const config = JSON.parse(readFileSync(new URL('./config.json', import.meta.url)));
```

`new URL('./config.json', import.meta.url)`은 현재 파일을 기준으로 config.json의 URL을 만든다. `__dirname`을 쓰지 않고 같은 결과를 얻는 ESM 방식이다.

## CJS와 ESM 핵심 차이

| 항목 | CommonJS | ESM |
|------|----------|-----|
| 문법 | `require` / `module.exports` | `import` / `export` |
| 의존성 결정 시점 | 런타임 | 파싱 단계 |
| 로딩 방식 | 동기 | 비동기 |
| top-level await | 불가 | 가능 |
| 트리 쉐이킹 | 불가 | 가능 |
| `__dirname` / `__filename` | 있음 | 없음 |
| 조건부 로딩 | `if` 블록 안에서 `require` 가능 | dynamic import 필요 |

## Interop - 실무에서 자주 밟는 상황

### ESM-only 라이브러리를 CJS에서 require할 때

chalk v5, got v12부터 ESM-only가 됐다. CJS 프로젝트에서 버전을 올리면 런타임에 바로 오류가 난다.

```
Error [ERR_REQUIRE_ESM]: require() of ES Module
/node_modules/chalk/source/index.js from /src/logger.js not supported.
```

버전을 낮게 고정하는 것이 마이그레이션 여유가 없을 때 가장 빠른 선택이다.

```json
{
  "dependencies": {
    "chalk": "^4.1.2",
    "got": "^11.8.6"
  }
}
```

dynamic import로 감싸는 방법도 있다.

```javascript
async function createLogger() {
    const { default: chalk } = await import('chalk');
    return {
        info: (msg) => console.log(chalk.blue(msg)),
        error: (msg) => console.log(chalk.red(msg)),
    };
}

let logger;
async function getLogger() {
    if (!logger) logger = await createLogger();
    return logger;
}
```

함수 호출마다 `import()`를 반복해도 모듈 캐시가 있어 파일을 다시 읽지 않는다.

### ESM에서 CJS 모듈 사용

ESM에서 CJS 모듈은 대부분 default import로 가져온다. named import가 실패하는 경우가 있다.

```javascript
// named import가 안 되는 경우가 있다
import { foo } from 'some-cjs-library'; // ReferenceError 가능

// default import가 안전하다
import cjsLib from 'some-cjs-library';
const { foo } = cjsLib;
```

Node.js v22부터 CJS named export를 ESM에서 직접 named import로 가져오는 실험적 지원이 추가됐다. 아직 `--experimental-require-module` 플래그가 필요하다.

## 순환 의존성

### CommonJS

CJS에서 순환 참조가 발생하면 아직 완성되지 않은 `exports` 객체를 받는다.

```javascript
// a.js
const b = require('./b');
console.log('a에서 b.value:', b.value); // undefined - b가 아직 완성 안 됨
module.exports = { value: 'A' };

// b.js
const a = require('./a');
console.log('b에서 a.value:', a.value); // 로딩 순서에 따라 다름
module.exports = { value: 'B' };
```

런타임에서만 문제가 드러나고, 값이 `undefined`인 이유를 추적하기 어렵다.

### ESM

ESM은 정적 분석 단계에서 순환을 감지하고 참조를 미리 연결한다. 단, 초기화 순서 문제는 여전히 발생할 수 있다.

```javascript
// a.js
import { value as bValue } from './b.js';
export const value = 'A';
export function getB() { return bValue; } // 함수는 호출 시점에 평가된다
```

함수로 감싸면 값이 초기화된 후 접근하기 때문에 순환 문제를 피할 수 있다.

## 참조

- [Node.js Modules Documentation](https://nodejs.org/api/modules.html)
- [ECMAScript Modules in Node.js](https://nodejs.org/api/esm.html)
- [import.meta.resolve() - Node.js](https://nodejs.org/api/esm.html#importmetaresolvespecifier)
