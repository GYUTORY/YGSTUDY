---
title: Dual Package Build (CJS + ESM 동시 지원)
tags: [nodejs]
updated: 2026-07-17
---

# Dual Package Build

npm 패키지를 만들 때 CJS만 배포하면 ESM 프로젝트에서 static analysis가 안 되고 tree-shaking이 깨진다. ESM만 배포하면 `require()`를 쓰는 레거시 프로젝트에서 `ERR_REQUIRE_ESM`이 터진다. 두 형식을 모두 내보내야 하는 이유다.

## package.json exports 필드

Node.js 12+에서 `exports` 필드가 도입됐다. 이 필드가 있으면 기존 `main`과 `module` 필드는 무시된다. 진입점을 조건부로 분기하는 게 핵심이다.

```json
{
  "name": "my-lib",
  "version": "1.0.0",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": {
        "types": "./dist/index.d.ts",
        "default": "./dist/index.js"
      },
      "require": {
        "types": "./dist/index.d.cts",
        "default": "./dist/index.cjs"
      }
    },
    "./package.json": "./package.json"
  },
  "files": ["dist"]
}
```

`import` 조건은 ESM `import` 문으로 불러올 때, `require` 조건은 CJS `require()`로 불러올 때 적용된다. TypeScript 5.0+에서는 `types` 조건을 각 분기 안에 넣어야 타입 파일도 올바르게 분기된다. `d.ts`와 `d.cts`를 따로 생성해야 하는 이유다.

`"./package.json": "./package.json"` 항목을 빠뜨리면 일부 번들러가 패키지 버전을 읽지 못해 에러를 낸다. 습관적으로 추가해두는 게 낫다.

서브패스 export가 필요하면 이렇게 추가한다.

```json
{
  "exports": {
    ".": { ... },
    "./utils": {
      "import": "./dist/utils.js",
      "require": "./dist/utils.cjs"
    }
  }
}
```

`exports` 필드를 정의하는 순간 명시되지 않은 경로는 모두 막힌다. `dist/internal.js`를 직접 import하던 사용자가 있다면 패키지 업그레이드 후 바로 깨진다. breaking change로 취급해야 한다.

## tsup으로 dual build

tsup은 esbuild 기반 번들러로, TypeScript 라이브러리 빌드에 설정이 거의 필요 없다.

```bash
npm install -D tsup
```

```typescript
// tsup.config.ts
import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  clean: true,
  outExtension({ format }) {
    return {
      js: format === 'cjs' ? '.cjs' : '.js',
    }
  },
})
```

`dts: true`를 켜면 `index.d.ts`와 `index.d.cts` 두 파일을 모두 생성한다. `splitting: false`는 코드 스플리팅을 끈다. 라이브러리 빌드에서 스플리팅을 켜면 chunk 파일이 생기고 exports 매핑이 복잡해진다.

빌드 결과 `dist/` 구조는 이렇게 된다.

```
dist/
  index.js      ← ESM
  index.cjs     ← CJS
  index.d.ts    ← ESM types
  index.d.cts   ← CJS types
```

`package.json` scripts에 추가한다.

```json
{
  "scripts": {
    "build": "tsup",
    "dev": "tsup --watch"
  }
}
```

## Rollup으로 dual build

Rollup은 tsup보다 설정이 많지만 출력을 세밀하게 제어할 수 있다. 번들 크기가 중요하거나 복잡한 플러그인 체인이 필요할 때 선택한다.

```bash
npm install -D rollup @rollup/plugin-typescript rollup-plugin-dts
```

```javascript
// rollup.config.js
import typescript from '@rollup/plugin-typescript'
import dts from 'rollup-plugin-dts'

const config = [
  {
    input: 'src/index.ts',
    output: [
      {
        file: 'dist/index.js',
        format: 'esm',
        sourcemap: true,
      },
      {
        file: 'dist/index.cjs',
        format: 'cjs',
        sourcemap: true,
        exports: 'named',
      },
    ],
    plugins: [typescript({ tsconfig: './tsconfig.json' })],
    external: ['node:fs', 'node:path'],
  },
  {
    input: 'dist/index.d.ts',
    output: { file: 'dist/index.d.ts', format: 'esm' },
    plugins: [dts()],
  },
]

export default config
```

`external` 배열에 Node.js 내장 모듈을 반드시 명시해야 한다. 빠뜨리면 `fs`, `path` 같은 모듈까지 번들에 포함시키려다 에러가 난다. 피어 의존성도 여기에 넣어야 한다.

CJS 출력에서 `exports: 'named'`를 지정하지 않으면 Rollup이 default export만 내보내는 구조로 만든다. named export를 쓰는 패키지라면 반드시 명시한다.

## Named exports CJS wrapper 패턴

ESM과 CJS 간 named export 호환이 깨지는 경우가 있다. 특히 CJS 번들을 ESM에서 `import { foo } from 'pkg'`로 불러올 때, 번들러가 named export를 제대로 인식 못 하면 `foo is not exported` 에러가 난다.

이때 CJS wrapper 파일을 직접 작성한다.

```javascript
// dist/index.cjs (수동 wrapper)
'use strict'

const mod = require('./index.cjs.js') // 실제 번들

Object.defineProperty(exports, '__esModule', { value: true })
exports.foo = mod.foo
exports.bar = mod.bar
exports.default = mod.default
```

tsup을 쓰면 이 패턴을 자동으로 처리하지만, 간혹 복잡한 re-export 구조에서 named export가 누락되는 경우가 있다. 이때 `dist/index.cjs`를 열어 실제로 어떤 exports가 붙었는지 확인해야 한다.

TypeScript를 쓰는 경우 `allowSyntheticDefaultImports: true`와 `esModuleInterop: true` 설정이 이 문제를 일부 감춰준다. 번들러 레벨에서 해결된 게 아니라 TypeScript가 import 구문을 변환할 때 `__importDefault` 헬퍼를 주입하는 방식이다. 런타임에서 실제로 동작하는지는 테스트로 확인해야 한다.

## ERR_REQUIRE_ESM 대응

ESM-only 라이브러리를 CJS 프로젝트에서 `require()`로 불러오면 이 에러가 난다.

```
Error [ERR_REQUIRE_ESM]: require() of ES Module /node_modules/some-pkg/index.js not supported.
```

`some-pkg`의 `package.json`에 `"type": "module"`이 있거나, 파일 확장자가 `.mjs`인 경우다. Node.js는 이 파일을 ESM으로 처리하고 `require()`를 거부한다.

### 방법 1: 동적 import 사용

```javascript
// CJS 파일에서 ESM 패키지 불러오기
async function loadPkg() {
  const { foo } = await import('esm-only-pkg')
  return foo
}
```

최상위 레벨에서 `require()`를 쓰던 코드라면 `async` 함수로 감싸야 한다. 초기화 코드나 설정 파일에서 쓰기 까다로운 상황이 생긴다.

### 방법 2: 프로젝트를 ESM으로 전환

`package.json`에 `"type": "module"` 추가하고, 모든 `require()`를 `import`로 바꾼다. 기존 `.js` 파일은 ESM으로 취급되고, CJS가 필요한 파일은 `.cjs`로 이름을 바꿔야 한다.

설정 파일(예: `jest.config.js`, `.eslintrc.js`)도 ESM 문법으로 바꾸거나 `.cjs` 확장자를 써야 한다. 도구 생태계 호환성 문제가 터지는 구간이다.

### 방법 3: CJS 버전 제공 패키지로 교체

`chalk` v5는 ESM-only로 전환했는데, CJS 프로젝트라면 `chalk` v4를 유지하는 게 현실적이다. `node-fetch` v3도 마찬가지로 ESM-only다. v2를 쓰거나 Node.js 내장 `fetch`(v18+)를 쓴다.

라이브러리가 dual package를 제공하는지 먼저 확인한다. `package.json`의 `exports` 필드에 `require` 조건이 있으면 CJS로도 불러올 수 있다.

### 방법 4: create-require로 우회

번들러나 메타프레임워크 내부에서 동적으로 모듈을 로드해야 할 때 쓴다.

```javascript
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)

// 이제 ESM 파일 내에서 require() 사용 가능
const lodash = require('lodash')
```

반대 방향이다. ESM 파일에서 CJS 패키지를 `require()`로 불러오는 패턴이다. ESM에서는 `require`가 없으므로 `createRequire`로 만들어 쓴다.

## 배포 전 검증

빌드한 패키지가 실제로 CJS와 ESM에서 모두 동작하는지 확인하는 방법이다.

```bash
# node_modules에 설치 없이 로컬 패키지 테스트
node --input-type=module <<'EOF'
import { foo } from './dist/index.js'
console.log(foo)
EOF

node -e "const { foo } = require('./dist/index.cjs'); console.log(foo)"
```

`publint` 도구를 쓰면 `package.json` exports 설정의 일반적인 실수를 잡아준다.

```bash
npx publint
```

`are-the-types-wrong`은 TypeScript 타입 파일 분기가 올바른지 검증한다.

```bash
npx @arethetypeswrong/cli ./dist
```

`attw` 출력에서 `Resolution failed`나 `Masquerading as CJS`가 뜨면 `d.ts`/`d.cts` 분기가 잘못된 것이다.

## 흔한 실수

`exports` 필드에 경로를 `./dist/index.js`로 쓰지 않고 `dist/index.js`처럼 앞에 `./`를 빠뜨리는 경우가 있다. Node.js는 `./`가 없으면 패키지 이름으로 해석해 `MODULE_NOT_FOUND`를 낸다.

CJS 출력 파일을 `.js`로 내보내고 `package.json`에 `"type": "module"`을 넣으면 모든 `.js` 파일이 ESM이 된다. CJS 파일은 `.cjs` 확장자를 쓰거나, `"type": "module"` 없이 ESM 파일만 `.mjs`를 써야 한다. tsup의 `outExtension` 설정에서 cjs를 `.cjs`로 내보내는 이유다.
