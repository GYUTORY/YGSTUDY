---
title: JavaScript 모듈 시스템
tags: [javascript, nodejs, language]
updated: 2026-08-03
---

# JavaScript 모듈 시스템

## CommonJS

Node.js가 처음부터 써온 모듈 시스템이다. `require()`를 호출하면 해당 파일을 즉시 동기로 읽고 실행한다.

```javascript
// utils.js
function add(a, b) { return a + b; }
module.exports = { add };

// index.js
const { add } = require('./utils');
console.log(add(1, 2));
```

`require()`는 처음 호출될 때만 파일을 실행하고 결과를 `require.cache`에 저장한다. 두 번째 호출부터는 캐시된 `module.exports` 객체를 그대로 반환한다.

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

이 캐싱으로 싱글톤처럼 쓸 수 있지만, 테스트에서 모듈 상태를 리셋해야 할 때 `delete require.cache[require.resolve('./a')]`로 직접 제거해야 한다.

`exports`에 직접 할당하는 것과 `module.exports`를 재할당하는 건 다르게 동작한다. `exports`는 `module.exports`를 가리키는 참조지만, 재할당하면 참조가 끊어진다.

```javascript
exports = { foo: 'bar' };        // 작동 안 함 — module.exports와 분리됨
module.exports = { foo: 'bar' }; // 이게 맞다
```

## ESM (ECMAScript Modules)

`import`/`export` 문법을 쓰는 표준 모듈 시스템이다. Node.js는 v14.13부터 안정적으로 지원한다.

```javascript
// utils.mjs
export function add(a, b) { return a + b; }
export default class Calculator { /* ... */ }

// index.mjs
import Calculator, { add } from './utils.mjs';
```

ESM의 핵심은 정적 분석이다. `import` 문은 파일 최상위에만 위치할 수 있고, 런타임 이전 파싱 단계에서 의존성 그래프를 완성한다. 이 구조 덕분에 번들러가 실제로 사용하는 export만 남기는 트리 쉐이킹이 가능하다.

라이브 바인딩(live binding)도 CommonJS와 다르다. ESM에서 import한 값은 원본 모듈의 export 값과 연결된 참조다. 원본 모듈이 export 값을 변경하면 import한 쪽에도 반영된다.

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

## 두 시스템의 핵심 차이

| 항목 | CommonJS | ESM |
|---|---|---|
| 로딩 방식 | 동기 (런타임 실행) | 비동기 (정적 분석 후 로드) |
| 내보내기 | `module.exports` 객체 복사 | 라이브 바인딩 |
| 분석 시점 | 런타임 | 파싱 타임 |
| 조건부 로드 | 가능 (`if` 안에 `require`) | 불가 (최상위만 가능) |
| 트리 쉐이킹 | 불가 | 가능 |
| `__dirname` / `__filename` | 사용 가능 | 사용 불가 |
| Top-level await | 불가 | 가능 |

ESM에서 `__dirname`은 없다. `import.meta.url`로 대체한다.

```javascript
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
```

## .cjs / .mjs 확장자와 package.json "type" 필드

Node.js가 `.js` 파일을 CJS로 처리할지 ESM으로 처리할지 결정하는 기준은 `package.json`의 `"type"` 필드다.

- `"type"` 없거나 `"type": "commonjs"` → `.js` 파일은 CJS로 해석
- `"type": "module"` → `.js` 파일은 ESM으로 해석

`.cjs`와 `.mjs` 확장자는 이 설정과 무관하게 항상 각자의 방식으로 해석된다. `.cjs`는 무조건 CommonJS, `.mjs`는 무조건 ESM이다.

혼재 상황에서 발생하는 전형적인 오류는 두 가지다.

```
SyntaxError: Cannot use import statement in a module
```

```
Error [ERR_REQUIRE_ESM]: require() of ES Module ... is not supported
```

`"type"` 설정과 실제 코드가 맞지 않거나, CJS에서 ESM 파일을 `require()`로 불러오려 할 때 발생한다.

### Jest와 ts-node에서 자주 막히는 지점

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

## CJS와 ESM 상호 운용

**ESM에서 CJS 로드**: 가능하다. `import`로 CJS 모듈을 불러올 수 있다. CJS의 `module.exports` 전체가 default export로 들어온다. named export는 Node.js가 정적 분석으로 추측해주지만 패키지마다 결과가 다르다.

```javascript
import lodash from 'lodash';    // default로 전체 객체
import { merge } from 'lodash'; // Node.js가 추측 — 불완전할 수 있음
```

**CJS에서 ESM 로드**: 예전에는 `require()`로 ESM 을 부를 수 없었다. ESM 로딩이 비동기라 동기인 `require()` 와 맞지 않기 때문이었다. Node 20.19·22.12·24 부터는 **동기 ESM 그래프에 한해** 플래그 없이 된다 — 그래프 안에 top-level await 가 있으면 여전히 `ERR_REQUIRE_ASYNC_MODULE` 이 난다. 그 경우에는 동적 `import()` 를 써야 한다.

```javascript
// CJS 파일에서 ESM 로드
async function loadESM() {
  const { default: someModule } = await import('./esm-module.mjs');
  return someModule;
}
```

라이브러리를 만들 때 CJS와 ESM 둘 다 지원하려면 `exports` 필드를 쓴다.

```json
{
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.cjs"
    }
  }
}
```

## 동적 import()

`import()`는 런타임에 조건부로 모듈을 불러올 수 있다. CJS 파일에서도 쓸 수 있고, top-level await 가 있는 ESM 을 CJS 에서 부르는 유일한 방법이기도 하다.

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

## Top-level await

ESM 파일 최상위에서 `await`를 쓸 수 있다. `async` 함수로 감쌀 필요가 없다.

```javascript
// config.mjs
const config = await fetch('/api/config').then(r => r.json());
export { config };
```

Node.js에서는 `"type": "module"` 환경 또는 `.mjs` 파일에서만 쓸 수 있다. `.js` 파일이고 `"type"` 설정이 없으면 CJS로 해석되어 `SyntaxError`가 난다.

`tsconfig.json`에서는 `"module": "NodeNext"` 이상으로 설정해야 컴파일 에러가 없다.

```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2022"
  }
}
```

top-level await가 있는 모듈을 import하면, 그 await가 완료될 때까지 import한 쪽도 대기한다. 순환 참조와 조합되면 교착 상태가 발생할 수 있다.

```javascript
// 순환 참조 + top-level await 조합은 피해야 한다
// a.mjs
import { b } from './b.mjs';
export const a = await someAsyncOp(); // b.mjs가 a를 기다리면 교착

// b.mjs
import { a } from './a.mjs';
export const b = await anotherAsyncOp(a);
```

## Node.js 실무 트러블슈팅

### pure-esm 패키지 문제

`chalk@5`, `node-fetch@3`, `got@12` 등은 ESM으로만 배포된다. CJS 코드베이스에서 `require()`로 불러오면 `ERR_REQUIRE_ESM`이 난다.

선택지는 두 가지다.
- 해당 패키지의 이전 CJS 버전으로 고정한다 (`chalk@4`, `node-fetch@2`)
- 전체 프로젝트를 ESM으로 전환한다

두 방법 모두 비용이 있다. 프로젝트 규모에 따라 이전 버전 고정이 현실적인 경우가 많다.

### ts-node에서 ESM 사용

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

### require()로 .json 파일 로드

CJS에서는 `require('./data.json')`이 바로 된다. ESM에서는 Node.js v22부터 `import` 속성(assertion)을 써야 한다.

```javascript
// ESM에서 JSON import (Node.js v22+)
import data from './data.json' with { type: 'json' };

// 그 이전 버전에서는 fs로 읽어야 한다
import { readFileSync } from 'fs';
const data = JSON.parse(readFileSync('./data.json', 'utf-8'));
```
