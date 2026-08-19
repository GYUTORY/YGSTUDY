---
title: CommonJS vs ESM (ECMAScript Modules)
tags: [nodejs, javascript, language]
updated: 2026-08-19
---

# CommonJS vs ESM

## 배경

초기 JavaScript에는 모듈 시스템이 없었다. 스크립트를 HTML에 순서대로 나열하고, 코드는 전역 스코프에 올라갔다. 프로젝트가 커지면 변수 충돌이 생기고, 로딩 순서 문제로 런타임 오류가 발생했다.

Node.js는 2009년 CommonJS 명세를 채택해 `require()`/`module.exports` 방식을 도입했다. 서버에서 파일 시스템에 직접 접근할 수 있어 동기 로딩이 자연스러웠다.

ES6(2015)에 `import`/`export` 문법이 표준으로 들어왔다. 브라우저와 Node.js를 모두 아우르는 공식 규격이었지만, Node.js에서 플래그 없이 쓸 수 있게 된 건 v12.17(v13.2)이고 구현이 Stable로 표시된 건 v14.17(v12.22, v15.3)이다. 그 사이 수년간 CommonJS가 생태계를 지배한 탓에, 지금도 두 시스템이 뒤섞인 상황이 이어진다.

## CommonJS

### 모듈 래퍼 함수

Node.js는 파일을 실행하기 전에 내용을 함수로 감싼다.

```javascript
(function(exports, require, module, __filename, __dirname) {
    // 작성한 모듈 코드가 여기 들어간다
});
```

`__filename`과 `__dirname`이 "자동으로 생기는 전역 변수"처럼 느껴지지만, 실제로는 이 래퍼 함수가 주입하는 인자다. ESM에서 이 두 변수가 없는 이유도 여기에 있다. ESM은 래퍼 함수 방식을 쓰지 않는다.

`exports`는 `module.exports`의 참조다. `exports.foo = bar`는 잘 작동하지만 `exports = { foo: bar }`는 참조를 끊기 때문에 아무 효과가 없다.

```javascript
exports = { foo: 'bar' };        // 작동 안 함 — module.exports와 분리됨
module.exports = { foo: 'bar' }; // 이게 맞다
```

### 모듈 캐시

CommonJS 모듈 캐시의 키는 **해석된 절대 경로**다.

```javascript
require('./math');
console.log(Object.keys(require.cache));
// ['/absolute/path/to/math.js']
```

같은 파일을 경로 표기를 달리해서 require해도 같은 캐시 엔트리를 반환한다.

```javascript
const a = require('./utils');
const b = require('../src/utils'); // 같은 파일이면 a === b
```

`require()`는 처음 호출될 때만 파일을 실행하고 결과를 `require.cache`에 저장한다. 두 번째 호출부터는 캐시된 `module.exports` 객체를 그대로 반환한다. 모듈이 상태를 들고 있으면 그 상태가 프로세스 전체에서 공유된다.

```javascript
// a.js
let count = 0;
module.exports = { get: () => count, inc: () => ++count };

// 어디서 require해도 같은 인스턴스
const mod1 = require('./a');
const mod2 = require('./a');
mod1.inc();
console.log(mod2.get()); // 1 — 같은 객체
```

이 캐싱으로 싱글톤처럼 쓸 수 있지만, 테스트에서 모듈 상태를 리셋해야 할 때는 캐시를 직접 지워야 한다.

```javascript
delete require.cache[require.resolve('./config')];
const freshConfig = require('./config');
```

`require.resolve()`는 모듈 탐색만 하고 실행은 하지 않는다. 캐시 키 확인이나 파일 경로 조회에 쓴다.

### 기본 사용

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

동적 require는 런타임에 경로를 결정할 수 있다.

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

이 구조 덕분에 번들러가 실제로 사용하는 export만 남기는 트리 쉐이킹이 가능하다.

### .cjs / .mjs 확장자와 package.json "type" 필드

Node.js가 `.js` 파일을 CJS로 처리할지 ESM으로 처리할지 결정하는 기준은 `package.json`의 `"type"` 필드다.

- `"type"` 없거나 `"type": "commonjs"` → `.js` 파일은 CJS로 해석
- `"type": "module"` → `.js` 파일은 ESM으로 해석

```json
{
  "type": "module"
}
```

`.cjs`와 `.mjs` 확장자는 이 설정과 무관하게 항상 각자의 방식으로 해석된다. `.cjs`는 무조건 CommonJS, `.mjs`는 무조건 ESM이다.

ESM 파일에서는 상대 경로에 확장자를 명시해야 한다.

```javascript
// CJS는 확장자 생략 가능
// ESM은 확장자 필수
import { add } from './math.js';
```

혼재 상황에서 발생하는 전형적인 오류는 두 가지다.

```
SyntaxError: Cannot use import statement in a module
```

```
Error [ERR_REQUIRE_ESM]: require() of ES Module ... is not supported
```

`"type"` 설정과 실제 코드가 맞지 않거나, CJS에서 ESM 파일을 `require()`로 불러오려 할 때 발생한다.

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

### 라이브 바인딩

ESM에서 import한 값은 원본 모듈의 export 값과 연결된 참조다. 원본 모듈이 export 값을 변경하면 import한 쪽에도 반영된다.

```javascript
// counter.mjs
export let count = 0;
export function increment() { count++; }

// main.mjs
import { count, increment } from './counter.mjs';
console.log(count); // 0
increment();
console.log(count); // 1 — 라이브 바인딩으로 반영됨
```

CommonJS였다면 `count`는 복사본이라 변경이 반영되지 않는다.

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

Node.js v20.6(v18.19)부터 `import.meta.resolve()`가 플래그 없이 쓸 수 있다. 모듈을 실제로 로딩하지 않고 경로만 해석한다.

```javascript
// 파일을 실행하지 않고 절대 URL만 반환
const resolvedPath = import.meta.resolve('./config.json');
// file:///project/src/config.json
```

### top-level await

ESM 모듈은 자체적으로 비동기로 처리된다. 그래서 모듈 최상위에서 `await`를 직접 쓸 수 있고, `async` 함수로 감쌀 필요가 없다.

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

Node.js에서는 `"type": "module"` 환경 또는 `.mjs` 파일에서만 쓸 수 있다. `.js` 파일이고 `"type"` 설정이 없으면 CJS로 해석되어 `SyntaxError`가 난다. CommonJS에서 흔히 보이는 우회 방법은 즉시 실행 async 함수다.

```javascript
// CommonJS에서의 우회
(async () => {
    const data = await fetchData();
    startServer(data);
})();
```

TypeScript를 쓴다면 `tsconfig.json`에서 `"module": "NodeNext"` 이상으로 설정해야 컴파일 에러가 없다.

```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2022"
  }
}
```

### ESM에서 JSON import

CJS에서는 `require('./data.json')`이 바로 된다. ESM에서는 import attributes 구문 `with { type: 'json' }`을 써야 한다. 이 구문은 Node.js v20.10(v21.0)에 들어왔고, v22.12(v23.1)에서 실험 딱지를 뗐다.

```javascript
import data from './config.json' with { type: 'json' };

console.log(data.version);
```

그 이전에는 import assertions 구문 `assert { type: 'json' }`을 썼다. 이 문법은 v22.0.0에서 지원이 아예 제거됐으므로, 남아 있으면 최신 Node에서 그대로 터진다.

```javascript
// 구 문법 — v22.0.0에서 제거됨
import data from './config.json' assert { type: 'json' };
```

구버전을 함께 지원해야 하거나 JSON import가 부담스러운 경우, `createRequire`를 쓰거나 `fs`로 직접 읽는다.

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
| 내보내기 의미 | 값 복사 | 라이브 바인딩 |
| 트리 쉐이킹 | 불가 | 가능 |
| top-level await | 불가 | 가능 |
| `__dirname` / `__filename` | 있음 | 없음 |
| 조건부 로딩 | `if` 블록 안에서 `require` 가능 | dynamic import 필요 |

## 동적 import()

`import()`는 런타임에 조건부로 모듈을 불러올 수 있다. ESM은 물론 CJS 파일에서도 쓸 수 있다.

```javascript
// 조건부 로드
async function loadPlugin(name) {
  if (name === 'csv') {
    const { parse } = await import('./plugins/csv.js');
    return parse;
  }
  const { parse } = await import('./plugins/json.js');
  return parse;
}

// 사용자 인터랙션 후 코드 스플리팅
button.addEventListener('click', async () => {
  const { HeavyComponent } = await import('./HeavyComponent.js');
  // ...
});
```

`import()`의 반환값은 Promise이고, 모듈 네임스페이스 객체를 resolve한다. default export는 `.default`로 접근한다.

```javascript
const mod = await import('./module.js');
mod.default;       // default export
mod.namedExport;   // named export
```

## Interop - 실무에서 자주 밟는 상황

### CJS에서 ESM 모듈 사용

오랫동안 CJS에서 ESM은 `require()`로 부를 수 없었다. ESM 로딩이 비동기라 동기인 `require()`와 맞지 않기 때문이었다. chalk v5, got v12처럼 ESM-only로 전환한 패키지를 CJS 프로젝트에서 버전만 올리면 런타임에 바로 터졌다.

```
Error [ERR_REQUIRE_ESM]: require() of ES Module
/node_modules/chalk/source/index.js from /src/logger.js not supported.
chalk is loaded as an ES module from
/node_modules/chalk/source/index.js
which can not be require()'d.
Change the require of index.js in /src/logger.js to a dynamic import()
which is available in all CommonJS modules.
```

지금은 상황이 다르다. Node.js v20.19, v22.12, v23.0부터 `require(esm)`이 `--experimental-require-module` 플래그 없이 동작하고, v25.4.0에서 실험 딱지도 떨어졌다. 단 **동기 모듈 그래프에 한해서**다. 부르려는 모듈이나 그 모듈이 import하는 그래프 어딘가에 top-level await가 있으면 `ERR_REQUIRE_ASYNC_MODULE`이 난다.

```javascript
// sync.mjs — top-level await 없음
export const x = 42;

// r.cjs
const m = require('./sync.mjs');
console.log(m.x); // 42 — Node 20.19+ 에서 플래그 없이 동작
```

```javascript
// tla.mjs — top-level await 있음
export const y = await Promise.resolve(1);

// r2.cjs
try { require('./tla.mjs'); } catch (e) { console.log(e.code); }
// ERR_REQUIRE_ASYNC_MODULE
```

그래프에 top-level await가 있거나 구버전 Node를 지원해야 하면 선택지는 여전히 셋이다.

**버전을 고정하는 방법**

```json
{
  "dependencies": {
    "chalk": "^4.1.2",
    "got": "^11.8.6"
  }
}
```

chalk v4, got v11은 CJS를 지원한다. 마이그레이션 여유가 없을 때 가장 빠른 선택이다.

**dynamic import로 감싸는 방법**

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

got도 같은 방식이다.

```javascript
async function fetchData(url) {
    const { default: got } = await import('got');
    return got(url).json();
}
```

함수 호출마다 `import()`를 반복해도 모듈 캐시가 있어 파일을 다시 읽지 않는다. 다만 최상위에서 `require()`를 쓰던 코드를 `async` 함수로 감싸야 하므로, 초기화 코드나 설정 파일에서는 쓰기 까다롭다.

**전체 프로젝트를 ESM으로 전환하는 방법**

`package.json`에 `"type": "module"`을 추가하고 모든 `require()`를 `import`로 바꾼다. 설정 파일(`jest.config.js`, `.eslintrc.js` 등)도 ESM 문법으로 바꾸거나 `.cjs` 확장자를 써야 한다. 도구 생태계 호환성 문제가 터지는 구간이라, 프로젝트 규모에 따라 이전 버전 고정이 현실적인 경우가 많다.

### ESM에서 CJS 모듈 사용

`import`로 CJS 모듈을 불러올 수 있다. CJS의 `module.exports` 전체가 default export로 들어온다.

named import도 플래그 없이 된다. Node.js가 정적 분석으로 CJS의 named export를 추측해 별도의 ES module export로 제공하기 때문이다. 다만 이건 정적 분석이라 패키지마다 결과가 다르고, `module.exports`에 런타임으로 붙인 export나 라이브 바인딩 갱신은 감지하지 못한다.

```javascript
import lodash from 'lodash';    // default로 전체 객체 — 항상 안전하다
import { merge } from 'lodash'; // 정적 분석이 추측 — 불완전할 수 있음
```

추측이 실패하면 링크 단계에서 `SyntaxError`가 난다. 모듈 평가 전에 터지는 것이라 **그 모듈 안에서는 try/catch 로 감쌀 수 없다** — static `import` 는 애초에 `try` 블록 안에 쓸 수 없기 때문이다. 다만 다른 모듈에서 `await import('./x.mjs')` 로 부르면 그 자리에서는 잡힌다. 실측(Node v22.21.1)으로 확인한 동작이다.

```
SyntaxError: Named export 'nope' not found. The requested module './lib.cjs'
is a CommonJS module, which may not support all module.exports as named exports.
```

named import가 깨지면 default import로 받아서 구조 분해하면 된다.

```javascript
import cjsLib from 'some-cjs-library';
const { foo } = cjsLib;
```

### createRequire

`createRequire`로 ESM 파일 안에서 CJS require를 쓸 수도 있다. ESM에는 `require`가 없으므로 `import.meta.url`을 넘겨 만들어 쓴다.

```javascript
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const legacyLib = require('./legacy-module');
```

## 순환 의존성

### CommonJS

```javascript
// a.js
const b = require('./b');
console.log('a에서 b.value:', b.value); // undefined - b가 아직 완성 안 됨
module.exports = { value: 'A' };

// b.js
const a = require('./a');
console.log('b에서 a.value:', a.value); // 'A' 또는 undefined - 로딩 순서 따라 다름
module.exports = { value: 'B' };
```

CJS에서 순환 참조가 발생하면 아직 완성되지 않은 `exports` 객체(빈 객체 또는 부분 초기화 상태)를 받는다. 런타임에서만 문제가 드러나고, 값이 `undefined`인 이유를 추적하기 어렵다.

### ESM

ESM은 정적 분석 단계에서 순환을 감지하고 참조를 미리 연결한다. 단, 초기화 순서 문제는 여전히 발생할 수 있다.

```javascript
// a.js
import { value as bValue } from './b.js';
export const value = 'A';
export function getB() { return bValue; } // 함수는 호출 시점에 평가
```

함수로 감싸면 값이 초기화된 후 접근하기 때문에 순환 문제를 피할 수 있다.

### 순환 참조와 top-level await

top-level await가 있는 모듈을 import하면 그 await가 완료될 때까지 import한 쪽도 대기한다. 순환 참조와 조합되면 교착 상태가 발생할 수 있다.

```javascript
// 순환 참조 + top-level await 조합은 피해야 한다
// a.mjs
import { b } from './b.mjs';
export const a = await someAsyncOp(); // b.mjs가 a를 기다리면 교착

// b.mjs
import { a } from './a.mjs';
export const b = await anotherAsyncOp(a);
```

## 툴체인에서 막히는 지점

### Jest와 ts-jest

`"type": "module"`로 프로젝트를 설정했을 때 Jest가 기본 설정으로는 작동하지 않는다. `--experimental-vm-modules` 플래그를 써야 한다.

```json
{
  "type": "module",
  "scripts": {
    "test": "node --experimental-vm-modules node_modules/.bin/jest"
  }
}
```

`ts-jest`도 `useESM: true` 옵션을 별도로 설정해야 한다.

```javascript
// jest.config.js
export default {
  preset: 'ts-jest/presets/default-esm',
  extensionsToTreatAsEsm: ['.ts'],
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { useESM: true }],
  },
};
```

### ts-node

`ts-node`는 기본적으로 CJS로 컴파일한다. ESM으로 실행하려면 `tsconfig.json`에 `ts-node` 설정을 추가한다.

```json
{
  "ts-node": {
    "esm": true,
    "experimentalSpecifierResolution": "node"
  }
}
```

`NodeNext` 모드에서 `.ts` 파일을 import할 때 확장자를 `.js`로 써야 한다. TypeScript가 컴파일 결과물 기준으로 import를 처리하기 때문이다.

```typescript
import { something } from './utils.js'; // .ts가 아닌 .js로 작성
```

## Dual Package - CJS와 ESM 동시 지원

라이브러리를 만들 때 두 환경 모두 지원해야 하는 경우가 있다. `package.json`의 `exports` 필드로 소비자가 어떤 방식으로 import하느냐에 따라 다른 진입점을 제공한다.

```json
{
  "name": "my-utils",
  "version": "1.0.0",
  "main": "./dist/index.cjs",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    },
    "./helpers": {
      "import": "./dist/helpers.mjs",
      "require": "./dist/helpers.cjs",
      "types": "./dist/helpers.d.ts"
    }
  }
}
```

`"import"` 조건은 ESM `import` 문에 적용된다. `"require"` 조건은 CJS `require()` 호출에 적용된다.

소비자는 코드를 바꿀 필요 없이 환경에 맞는 파일이 자동으로 선택된다.

```javascript
// ESM 환경 → dist/index.mjs 로드
import { add } from 'my-utils';

// CJS 환경 → dist/index.cjs 로드
const { add } = require('my-utils');
```

빌드 도구 설정(tsup, Rollup), `d.ts`/`d.cts` 타입 분기, `publint`·`attw` 검증까지는 [Dual Package Build](Dual_Package_Build.md)에서 다룬다.

### Dual Package Hazard

같은 라이브러리의 CJS 버전과 ESM 버전이 동시에 메모리에 올라오는 문제다. 두 버전이 각각 내부 상태를 가지면 싱글턴 패턴이 깨진다.

```javascript
// CJS 소비자
const libCjs = require('my-utils'); // dist/index.cjs 인스턴스

// ESM 소비자 (같은 프로세스 안)
import libEsm from 'my-utils'; // dist/index.mjs 인스턴스

// libCjs.getInstance() !== libEsm.getInstance()
```

상태를 가지는 모듈(싱글턴, 전역 레지스트리 등)이라면 dual package 구조에서 이 문제가 생길 수 있다. 상태를 별도 파일로 분리하고, CJS/ESM 래퍼 양쪽이 같은 파일을 참조하도록 구성하면 회피할 수 있다.

---

## 참조

- [Node.js Modules Documentation](https://nodejs.org/api/modules.html)
- [ECMAScript Modules in Node.js](https://nodejs.org/api/esm.html)
- [Loading ECMAScript modules using require()](https://nodejs.org/api/modules.html#loading-ecmascript-modules-using-require)
- [CommonJS Namespaces - Node.js](https://nodejs.org/api/esm.html#commonjs-namespaces)
- [import.meta.resolve() - Node.js](https://nodejs.org/api/esm.html#importmetaresolvespecifier)
- [Node.js - Dual CommonJS/ESM packages](https://nodejs.org/api/packages.html#dual-commonjses-module-packages)
