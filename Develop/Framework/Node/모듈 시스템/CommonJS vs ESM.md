---
title: CommonJS vs ESM (ECMAScript Modules)
tags: [nodejs]
updated: 2026-07-17
---

# CommonJS vs ESM

## 배경

초기 JavaScript에는 모듈 시스템이 없었다. 스크립트를 HTML에 순서대로 나열하고, 코드는 전역 스코프에 올라갔다. 프로젝트가 커지면 변수 충돌이 생기고, 로딩 순서 문제로 런타임 오류가 발생했다.

Node.js는 2009년 CommonJS 명세를 채택해 `require()`/`module.exports` 방식을 도입했다. 서버에서 파일 시스템에 직접 접근할 수 있어 동기 로딩이 자연스러웠다.

ES6(2015)에 `import`/`export` 문법이 표준으로 들어왔다. 브라우저와 Node.js를 모두 아우르는 공식 규격이었지만, Node.js가 v12에서야 실험적 지원을 시작하고 v14에서 안정화했다. 그 사이 수년간 CommonJS가 생태계를 지배한 탓에, 지금도 두 시스템이 뒤섞인 상황이 이어진다.

## CommonJS 내부 동작

### 모듈 래퍼 함수

Node.js는 파일을 실행하기 전에 내용을 함수로 감싼다.

```javascript
(function(exports, require, module, __filename, __dirname) {
    // 작성한 모듈 코드가 여기 들어간다
});
```

`__filename`과 `__dirname`이 "자동으로 생기는 전역 변수"처럼 느껴지지만, 실제로는 이 래퍼 함수가 주입하는 인자다. ESM에서 이 두 변수가 없는 이유도 여기에 있다. ESM은 래퍼 함수 방식을 쓰지 않는다.

`exports`는 `module.exports`의 참조다. `exports.foo = bar`는 잘 작동하지만 `exports = { foo: bar }`는 참조를 끊기 때문에 아무 효과가 없다.

### 캐시 키 구조

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

테스트에서 모듈을 재실행해야 할 때 캐시를 직접 지운다.

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

## ESM 내부 동작

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

`__dirname`과 `__filename`은 ESM에서 없다. 필요하면 직접 만든다.

```javascript
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
```

### 기본 사용

```javascript
// math.js
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
```

```javascript
// main.js
import { add } from './math.js';
import * as math from './math.js';
```

default export와 named export를 섞는 것은 가능하지만, 라이브러리를 쓸 때 혼동을 일으키는 경우가 많다. default export는 소비자가 이름을 자유롭게 짓기 때문에 IDE 자동완성 지원도 약해진다.

## CJS와 ESM 핵심 차이

| 항목 | CommonJS | ESM |
|------|----------|-----|
| 문법 | `require` / `module.exports` | `import` / `export` |
| 의존성 결정 시점 | 런타임 | 파싱 단계 |
| 로딩 방식 | 동기 | 비동기 |
| 트리 쉐이킹 | 불가 | 가능 |
| `__dirname` / `__filename` | 있음 | 없음 |
| 조건부 로딩 | `if` 블록 안에서 `require` 가능 | dynamic import 필요 |

## Interop 오류 - 실무에서 자주 밟는 상황

### ESM-only 라이브러리를 CJS에서 require할 때

chalk v5, got v12부터 ESM-only가 됐다. CJS 프로젝트에서 버전을 올리면 런타임에 바로 터진다.

```
Error [ERR_REQUIRE_ESM]: require() of ES Module
/node_modules/chalk/source/index.js from /src/logger.js not supported.
chalk is loaded as an ES module from
/node_modules/chalk/source/index.js
which can not be require()'d.
Change the require of index.js in /src/logger.js to a dynamic import()
which is available in all CommonJS modules.
```

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

함수 호출마다 `import()`를 반복해도 모듈 캐시가 있어 파일을 다시 읽지 않는다.

### ESM에서 CJS 모듈 사용

ESM에서 CJS 모듈은 대부분 default import로 가져온다. named import가 실패하는 경우가 있다.

```javascript
// named import가 안 되는 경우
import { foo } from 'some-cjs-library'; // ReferenceError 가능

// default import가 안전하다
import cjsLib from 'some-cjs-library';
const { foo } = cjsLib;
```

Node.js v22부터 CJS named export를 ESM에서 직접 named import로 가져오는 실험적 지원이 추가됐다. 아직 `--experimental-require-module` 플래그가 필요하다.

`createRequire`로 ESM 파일 안에서 CJS require를 쓸 수도 있다.

```javascript
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const legacyLib = require('./legacy-module');
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

---

## 참조

- [Node.js Modules Documentation](https://nodejs.org/api/modules.html)
- [ECMAScript Modules in Node.js](https://nodejs.org/api/esm.html)
- [Node.js - Dual CommonJS/ESM packages](https://nodejs.org/api/packages.html#dual-commonjses-module-packages)
