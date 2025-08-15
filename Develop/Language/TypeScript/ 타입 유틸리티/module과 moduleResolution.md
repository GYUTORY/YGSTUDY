---
title: TypeScript Module과 ModuleResolution 완벽 가이드
tags: [language, typescript, module, module-resolution, es-modules, commonjs]
updated: 2024-12-19
---

# TypeScript Module과 ModuleResolution 완벽 가이드

## 배경

### Module과 ModuleResolution이란?
TypeScript에서 `module`과 `moduleResolution`은 모듈 시스템과 모듈 해석 방식을 정의하는 중요한 설정입니다. 이는 TypeScript 코드가 JavaScript로 컴파일될 때 어떤 모듈 시스템을 사용할지와 import/export 구문을 어떻게 해석할지를 결정합니다.

### Module과 ModuleResolution의 필요성
- **모듈 시스템 호환성**: 다양한 JavaScript 환경에서의 모듈 사용
- **경로 해석 정확성**: import/export 구문의 올바른 해석
- **빌드 최적화**: 프로젝트 환경에 맞는 최적의 모듈 변환
- **개발 환경 통일**: 팀 내 일관된 모듈 사용 방식

### 기본 개념
- **`module`**: TypeScript 코드가 어떤 JavaScript 모듈 시스템으로 변환될지 결정
- **`moduleResolution`**: TypeScript 컴파일러가 import 경로를 어떻게 해석할지 결정
- **ES Modules**: 최신 JavaScript 모듈 시스템 (import/export)
- **CommonJS**: Node.js의 전통적인 모듈 시스템 (require/module.exports)

## 핵심

### 1. Module 설정

#### 주요 Module 옵션들

| Module 값 | 설명 | 사용 환경 | 특징 |
|-----------|------|-----------|------|
| **`"CommonJS"`** | Node.js에서 사용되는 전통적인 방식 | Node.js 서버, 레거시 환경 | require/module.exports 사용 |
| **`"ESNext"`** | 최신 JavaScript 모듈 (ECMAScript 모듈) | 최신 브라우저, Node.js 12+ | import/export 사용 |
| **`"ES2022"`** | 최신 ECMAScript 모듈 표준 | 최신 환경 | 최신 ES 모듈 기능 지원 |
| **`"AMD"`** | Asynchronous Module Definition | 구형 브라우저 | 비동기 모듈 로딩 |
| **`"UMD"`** | CommonJS + AMD의 조합 | 라이브러리 배포 | 범용 모듈 시스템 |

#### CommonJS vs ESNext 예제

**프로젝트 구조:**
```plaintext
src/
├── index.ts
├── math.ts
└── utils/
    └── helper.ts
```

**math.ts:**
```typescript
export const add = (a: number, b: number): number => a + b;
export const subtract = (a: number, b: number): number => a - b;

export default class Calculator {
    multiply(a: number, b: number): number {
        return a * b;
    }
}
```

**utils/helper.ts:**
```typescript
export const formatNumber = (num: number): string => {
    return num.toLocaleString();
};

export const validateNumber = (num: any): boolean => {
    return typeof num === 'number' && !isNaN(num);
};
```

**index.ts:**
```typescript
import Calculator, { add, subtract } from './math';
import { formatNumber, validateNumber } from './utils/helper';

const calc = new Calculator();
console.log("덧셈:", add(2, 3));
console.log("뺄셈:", subtract(5, 2));
console.log("곱셈:", calc.multiply(4, 5));
console.log("포맷:", formatNumber(1234567));
```

**CommonJS 컴파일 결과 (`dist/index.js`):**
```javascript
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const math_1 = require("./math");
const helper_1 = require("./utils/helper");

const calc = new math_1.default();
console.log("덧셈:", math_1.add(2, 3));
console.log("뺄셈:", math_1.subtract(5, 2));
console.log("곱셈:", calc.multiply(4, 5));
console.log("포맷:", helper_1.formatNumber(1234567));
```

**ESNext 컴파일 결과 (`dist/index.js`):**
```javascript
import Calculator, { add, subtract } from './math.js';
import { formatNumber } from './utils/helper.js';

const calc = new Calculator();
console.log("덧셈:", add(2, 3));
console.log("뺄셈:", subtract(5, 2));
console.log("곱셈:", calc.multiply(4, 5));
console.log("포맷:", formatNumber(1234567));
```

### 2. ModuleResolution 설정

#### 주요 ModuleResolution 옵션들

| ModuleResolution 값 | 설명 | 특징 | 사용 시기 |
|-------------------|------|------|-----------|
| **`"node"`** | Node.js 방식 (기본값) | `node_modules` 탐색, 상대 경로 지원 | 대부분의 프로젝트 |
| **`"classic"`** | TypeScript 초기 방식 | 상대 경로만 지원, `node_modules` 미탐색 | 레거시 프로젝트 |
| **`"bundler"`** | 번들러 최적화 방식 | 번들러 환경에 최적화 | Webpack, Vite 등 |

#### 프로젝트 구조 예제

```plaintext
src/
├── index.ts
├── utils/
│   └── math.ts
├── types/
│   └── user.ts
└── node_modules/
    └── lodash/
        └── index.d.ts
```

#### ModuleResolution: "node" 동작 방식

```typescript
// 상대 경로 - 직접 파일 탐색
import { add } from './utils/math';
import { User } from './types/user';

// 절대 경로 - node_modules 탐색
import { debounce } from 'lodash';
import express from 'express';

// 타입 정의 파일도 자동 탐색
import { User } from './types/user';
```

**탐색 순서:**
1. 상대 경로 파일 직접 탐색
2. `node_modules` 디렉토리 탐색
3. 타입 정의 파일 (`.d.ts`) 자동 탐색
4. 패키지의 `main`, `module`, `types` 필드 확인

#### ModuleResolution: "classic" 동작 방식

```typescript
// 상대 경로만 지원
import { add } from './utils/math';

// node_modules 탐색 안됨
// import { debounce } from 'lodash'; // 오류 발생
```

**탐색 순서:**
1. 상대 경로 파일만 탐색
2. `node_modules` 탐색하지 않음
3. 타입 정의 파일 수동 지정 필요

### 3. 실제 사용 사례

#### Node.js 프로젝트 설정

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**사용 예시:**
```typescript
// CommonJS 방식으로 컴파일됨
import express from 'express';
import { add } from './utils/math';
import { User } from './types/user';

const app = express();

app.get('/', (req, res) => {
    res.json({ result: add(1, 2) });
});

app.post('/users', (req, res) => {
    const user: User = req.body;
    // 사용자 처리 로직
});
```

#### 브라우저 프로젝트 설정

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**사용 예시:**
```typescript
// ESNext 방식으로 컴파일됨
import { createApp } from 'vue';
import { add } from './utils/math';
import { User } from './types/user';

const app = createApp({
    setup() {
        return { 
            result: add(1, 2),
            user: {} as User
        };
    }
});
```

## 예시

### 1. 라이브러리 개발 설정

#### UMD 라이브러리 설정

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "UMD",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "strict": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "test"]
}
```

**컴파일 결과:**
```javascript
(function (global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
    typeof define === 'function' && define.amd ? define(['exports'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.MyLib = {}));
})(this, (function (exports) {
    'use strict';
    
    const add = (a, b) => a + b;
    const subtract = (a, b) => a - b;
    
    exports.add = add;
    exports.subtract = subtract;
}));
```

### 2. 모노레포 설정

#### 워크스페이스별 설정

**루트 tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "composite": true
  },
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/utils" },
    { "path": "./packages/ui" }
  ]
}
```

**packages/core/tsconfig.json:**
```json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src",
    "composite": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "test"]
}
```

**packages/utils/tsconfig.json:**
```json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src",
    "composite": true,
    "declaration": true
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "test"]
}
```

### 3. 고급 설정 패턴

#### 경로 매핑 설정

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@components/*": ["components/*"],
      "@utils/*": ["utils/*"],
      "@types/*": ["types/*"]
    }
  }
}
```

**사용 예시:**
```typescript
// 절대 경로 사용
import { Button } from '@/components/Button';
import { formatDate } from '@/utils/date';
import { User } from '@/types/user';

// 컴파일 시 상대 경로로 변환됨
```

#### 조건부 모듈 해석

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    },
    "typeRoots": ["./node_modules/@types", "./src/types"]
  }
}
```

## 운영 팁

### 1. 성능 최적화

#### 모듈 해석 캐싱
```json
{
  "compilerOptions": {
    "moduleResolution": "node",
    "skipLibCheck": true,
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo"
  }
}
```

#### 빌드 최적화
```json
{
  "compilerOptions": {
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "noEmit": true
  }
}
```

### 2. 에러 처리

#### 모듈 해석 오류 디버깅
```json
{
  "compilerOptions": {
    "moduleResolution": "node",
    "traceResolution": true,
    "listFiles": true,
    "listEmittedFiles": true
  }
}
```

**디버깅 출력 예시:**
```bash
======== Resolving module 'lodash' from '/src/index.ts'. ========
Module resolution kind is not specified, using 'node'.
'package.json' has 'main' field 'index.js' that references '/node_modules/lodash/index.js'.
File '/node_modules/lodash/index.js' exist - use it as a name resolution result.
```

#### 일반적인 모듈 오류 해결
```typescript
// 문제: 모듈을 찾을 수 없음
// 해결: 타입 정의 파일 설치
npm install --save-dev @types/lodash

// 문제: ES 모듈과 CommonJS 혼용
// 해결: esModuleInterop 설정
{
  "compilerOptions": {
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true
  }
}
```

### 3. 개발 환경 설정

#### IDE 설정
```json
// .vscode/settings.json
{
  "typescript.preferences.includePackageJsonAutoImports": "on",
  "typescript.suggest.autoImports": true,
  "typescript.updateImportsOnFileMove.enabled": "always"
}
```

#### ESLint 설정
```json
// .eslintrc.json
{
  "extends": [
    "@typescript-eslint/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-module-boundary-types": "warn"
  }
}
```

## 참고

### Module vs ModuleResolution 비교표

| 특징 | Module | ModuleResolution |
|------|--------|------------------|
| **역할** | JS 모듈 시스템 결정 | import 경로 해석 방식 정의 |
| **주요 옵션** | `"CommonJS"`, `"ESNext"`, `"UMD"` | `"node"`, `"classic"`, `"bundler"` |
| **사용 시점** | JS로 컴파일 시 적용 | 컴파일 시 import 경로 해석 |
| **Node.js 지원** | `CommonJS` | `node` |
| **모던 브라우저 지원** | `ESNext` | `node` (ESNext와 사용) |

### 권장 설정 조합

| 프로젝트 타입 | Module | ModuleResolution | 추가 설정 |
|-------------|--------|------------------|-----------|
| **Node.js 서버** | `"CommonJS"` | `"node"` | `esModuleInterop: true` |
| **브라우저 앱** | `"ESNext"` | `"node"` | `strict: true` |
| **라이브러리** | `"UMD"` | `"node"` | `declaration: true` |
| **모노레포** | `"ESNext"` | `"node"` | `composite: true` |
| **번들러 환경** | `"ESNext"` | `"bundler"` | `noEmit: true` |

### 모듈 시스템 선택 가이드

#### CommonJS 선택 시기
- Node.js 서버 애플리케이션
- 레거시 환경 지원 필요
- 동적 모듈 로딩 필요

#### ESNext 선택 시기
- 최신 브라우저 지원
- Tree-shaking 최적화 필요
- 정적 분석 도구 사용

#### UMD 선택 시기
- 라이브러리 배포
- 다양한 환경 지원 필요
- CDN 배포 고려

### 결론
TypeScript의 module과 moduleResolution 설정은 프로젝트의 성공적인 빌드와 배포에 핵심적인 역할을 합니다. 적절한 설정으로 다양한 JavaScript 환경에서의 호환성을 확보할 수 있으며, Node.js 프로젝트는 CommonJS + node 조합을, 최신 브라우저 프로젝트는 ESNext + node 조합을 권장합니다. 모듈 해석 오류가 발생할 때는 traceResolution 옵션을 활용하여 디버깅하고, 프로젝트 환경과 요구사항에 맞는 최적의 설정을 선택하여 개발 효율성을 향상시키는 것이 중요합니다.

