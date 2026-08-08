---
title: TypeScript module과 moduleResolution
tags: [language, typescript]
updated: 2026-07-17
---

# TypeScript module과 moduleResolution

tsconfig에는 `module`과 `moduleResolution`이라는 두 옵션이 있다. `module`은 컴파일된 JavaScript 파일이 어떤 모듈 포맷을 쓸지 결정하고, `moduleResolution`은 TypeScript 컴파일러가 import 경로를 실제 파일로 어떻게 매핑할지 결정한다. 이 둘은 연관되어 있어서 쌍으로 이해해야 한다.

## module 옵션

`module` 옵션 값마다 컴파일 결과가 달라진다.

**CommonJS**: Node.js 기본 모듈 시스템이다. `import/export` 구문이 `require/module.exports`로 변환된다. `esModuleInterop: true`와 함께 쓰는 게 표준이다.

**ESNext / ES2022**: `import/export`를 그대로 유지한다. 번들러(Webpack, Vite, Rollup)가 처리하는 환경이나 최신 브라우저 타깃 프로젝트에 쓴다. 번들러가 트리쉐이킹을 할 수 있는 건 ESM 포맷의 정적 구조 덕분이다.

**node16 / nodenext**: Node.js 12+의 네이티브 ESM 지원을 위한 값이다. `moduleResolution` 옵션의 같은 값과 반드시 짝을 이뤄야 한다. `module: "node16"`이면 `moduleResolution: "node16"`, `module: "nodenext"`면 `moduleResolution: "nodenext"`다. 섞으면 컴파일러 오류가 난다.

**UMD**: CommonJS + AMD를 동시에 지원하는 포맷이다. 라이브러리를 CDN에 배포하거나 다양한 환경에서 써야 할 때 쓴다.

### CommonJS vs ESNext 컴파일 결과

```typescript
// math.ts
export const add = (a: number, b: number): number => a + b;
export default class Calculator {
  multiply(a: number, b: number): number { return a * b; }
}
```

CommonJS로 컴파일하면:

```javascript
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Calculator = exports.add = void 0;
const add = (a, b) => a + b;
exports.add = add;
class Calculator {
  multiply(a, b) { return a * b; }
}
exports.default = Calculator;
```

ESNext로 컴파일하면 원본과 거의 동일한 구조가 나온다. 차이는 상대 경로 import에 `.js` 확장자가 붙는 것 정도다.

## moduleResolution 옵션

| 값 | 특징 |
|---|---|
| `node` | 확장자 생략 허용, `package.json`의 `main` 필드 우선 |
| `node16` | 상대 경로에 확장자 명시 강제, `exports` 필드 우선 탐색 |
| `nodenext` | node16과 현재는 동작 동일. Node.js 최신 기능 반영 예정 |
| `bundler` | 확장자 생략 허용, `exports` 필드 지원. Vite/Webpack 등 번들러 환경용 |
| `classic` | TypeScript 초기 방식. 거의 쓰지 않는다 |

## node16 / nodenext moduleResolution

Node.js가 ESM을 공식 지원하면서 모듈 해석 규칙이 CommonJS와 달라졌다. `node16` / `nodenext`는 이 새로운 규칙을 반영한다.

### 확장자 명시 강제

`moduleResolution: "node16"`부터는 상대 경로 import에 반드시 `.js` 확장자를 붙여야 한다.

```typescript
// node16에서 올바른 import
import { add } from './math.js';
import { User } from './types/user.js';

// 오류: relative import path must end with a supported extension
import { add } from './math';
```

TypeScript 파일인데 `.js`를 쓰는 게 이상해 보이지만, 이게 Node.js ESM의 실제 동작 방식이다. TypeScript는 `./math.js`를 보면 `math.ts` → `math.tsx` → `math.d.ts` 순으로 탐색한다. 런타임에는 tsc가 `math.ts`를 `math.js`로 컴파일하므로 실제로 `math.js`가 존재한다.

기존 `node` 방식에서는 확장자를 생략하면 컴파일러가 `.ts`, `.tsx`, `.d.ts`를 순서대로 시도했다. `node16`부터는 그 관대함이 없어졌다. Node.js ESM 런타임 자체가 확장자 생략을 허용하지 않기 때문이다.

### exports 필드 우선 탐색

`node` 방식은 `package.json`의 `main` 필드로 패키지 진입점을 찾았다. `node16`부터는 `exports` 필드를 먼저 확인한다.

```json
// node_modules/some-lib/package.json
{
  "exports": {
    ".": {
      "import": "./esm/index.js",
      "require": "./cjs/index.js",
      "types": "./types/index.d.ts"
    },
    "./utils": {
      "import": "./esm/utils.js",
      "require": "./cjs/utils.js"
    }
  }
}
```

`exports` 필드가 있으면 `main`은 무시된다. `exports`에 없는 경로는 접근할 수 없다.

```typescript
import { something } from 'some-lib';          // OK
import { util } from 'some-lib/utils';         // OK
import { internal } from 'some-lib/internal';  // Error: Package subpath './internal' is not defined by "exports"
```

`node` 방식에서는 `some-lib/src/internal`처럼 패키지 내부 파일에 직접 접근하는 코드가 흔했다. `node16`에서는 라이브러리가 `exports`로 공개 API를 제한한다. 의존하던 내부 경로가 `exports`에 없으면 컴파일 오류가 난다.

## .mts와 .cts 확장자

`package.json`에 `"type": "module"`을 넣으면 `.js` 파일이 전부 ESM으로 취급된다. `"type"`이 없거나 `"commonjs"`면 CJS다. 한 프로젝트에서 ESM과 CJS를 섞어야 할 때 `.mts`와 `.cts`를 쓴다.

| 확장자 | 컴파일 결과 | 모듈 방식 |
|---|---|---|
| `.ts` | `.js` | `package.json`의 `type` 필드에 따름 |
| `.mts` | `.mjs` | 항상 ESM |
| `.cts` | `.cjs` | 항상 CJS |

`.mts` 파일 안에서 상대 경로 import는 `.mjs`로 끝나야 한다. TypeScript는 이를 `.mts` 파일로 해석한다.

```typescript
// server.mts - package.json에 "type": "module"이 없어도 ESM으로 취급
import { readFile } from 'node:fs/promises';
import { parseConfig } from './config.mjs';  // config.mts를 가리킴
```

`.cts` 파일 안에서는 `import` 구문을 쓸 수 없다. `require`를 써야 한다. `import type`은 타입만 가져오므로 허용된다.

```typescript
// jest.config.cts - "type": "module" 프로젝트에서 Jest 설정을 CJS로 유지
import type { Config } from 'jest';

const config: Config = {
  testEnvironment: 'node',
  transform: { '^.+\\.tsx?$': 'ts-jest' },
};

module.exports = config;
```

`.mts`와 `.cts`가 실용적인 상황은 주로 `"type": "module"` 프로젝트에서 도구 설정 파일(Jest, Webpack 설정)을 CJS로 유지해야 할 때다. 설정 파일 확장자를 `.cts`로 바꾸면 `package.json`의 `type` 필드 영향을 받지 않는다.

## verbatimModuleSyntax

TypeScript 5.0에서 추가된 옵션으로, `importsNotUsedAsValues`와 `preserveValueImports`를 대체한다.

### type-only import를 강제하는 이유

TypeScript는 타입으로만 쓰이는 import를 컴파일 시 제거(elide)한다. CommonJS에서는 이 동작이 예측 가능했다.

```typescript
// types.ts
export interface User { name: string; }

// service.ts
import { User } from './types';  // User는 타입으로만 쓰임

function greet(user: User): string {
  return `Hello, ${user.name}`;
}
```

CommonJS 컴파일 시 TypeScript는 `User`가 타입으로만 쓰였다는 걸 파악하고 `require('./types')`를 통째로 제거한다.

문제는 esbuild, SWC, Babel 같은 트랜스파일러가 개입할 때 발생한다. 이 도구들은 타입 정보 없이 파일 단위로 변환한다. TypeScript의 타입 소거 로직을 모른다. `import { User } from './types'`를 보면 `User`가 값인지 타입인지 판단하지 못하고 import를 그대로 둔다. 런타임에 `types.js`에 `User`라는 실제 export가 없으면 오류가 난다.

`verbatimModuleSyntax: true`를 켜면 타입으로만 쓰이는 import에 반드시 `import type`을 써야 한다.

```typescript
// verbatimModuleSyntax: true 설정 시

// 오류: User가 타입인데 import type을 사용하지 않음
import { User } from './types';

// 올바른 방법
import type { User } from './types';

// 값과 타입을 같은 모듈에서 가져올 때
import { DEFAULT_USER, type User } from './types';
```

`import type`으로 가져온 것은 컴파일 결과에서 완전히 사라진다. 일반 `import`는 남는다. "verbatim(원문 그대로)"이라는 이름은 여기서 왔다. 컴파일러가 import 생략 여부를 판단하지 않고, 개발자가 명시한 형태 그대로 출력한다.

```typescript
import type { User } from './types';       // 컴파일 결과에서 제거됨
import { DEFAULT_USER } from './constants'; // 컴파일 결과에 남음
```

`verbatimModuleSyntax`를 켜면 `importsNotUsedAsValues`와 `preserveValueImports`는 오류가 된다. 두 옵션은 deprecated됐으므로 `verbatimModuleSyntax`만 쓰면 된다.

## 환경별 설정

### Node.js ESM 프로젝트

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "node16",
    "moduleResolution": "node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "verbatimModuleSyntax": true
  }
}
```

`package.json`에 `"type": "module"`도 함께 넣어야 한다. import 경로에 `.js` 확장자를 반드시 붙여야 한다.

### Node.js CommonJS 프로젝트

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "esModuleInterop": true,
    "strict": true
  }
}
```

### 번들러(Vite, Webpack) 환경

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "noEmit": true,
    "strict": true,
    "verbatimModuleSyntax": true,
    "allowImportingTsExtensions": true
  }
}
```

`moduleResolution: "bundler"`는 `exports` 필드를 지원하면서도 확장자 생략을 허용한다. 번들러가 파일 해석을 담당하므로 TypeScript는 타입 검사만 하고 emit은 하지 않는 경우가 많다.

## 자주 겪는 문제

**node16 전환 시 확장자 오류**: 기존 import에 확장자가 없으면 일괄적으로 `.js`를 붙여야 한다. 파일 수가 많으면 jscodeshift나 간단한 스크립트로 처리한다. `.ts` 확장자를 쓰면 별도 오류가 나므로 반드시 `.js`를 써야 한다.

**esModuleInterop 없이 default import 오류**: `module: "CommonJS"` + `esModuleInterop: false` 상태에서 `import express from 'express'`를 쓰면 컴파일은 되지만 런타임에 `express is not a function` 오류가 난다. `esModuleInterop: true`를 추가하면 해결된다.

**exports 필드로 막힌 내부 경로**: `node16`이나 `bundler` moduleResolution에서 라이브러리 내부 파일에 직접 접근하다가 오류가 난다면, 해당 라이브러리가 `exports` 필드로 공개 경로를 제한한 것이다. 라이브러리가 공식으로 제공하는 subpath export로만 접근해야 한다.

**verbatimModuleSyntax 에러가 너무 많이 난다**: 레거시 코드에서 켜면 수백 개의 import 오류가 날 수 있다. ESLint의 `@typescript-eslint/consistent-type-imports` 규칙을 켜면 자동 수정(`--fix`)으로 처리할 수 있다.
