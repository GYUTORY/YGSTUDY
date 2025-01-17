
# 🌟 TypeScript `tsc-alias`

## 📚 개요

`tsc-alias`는 TypeScript의 `paths`와 `baseUrl`을 사용하는 프로젝트에서 **경로 별칭(Path Alias)**을 컴파일 후에 자동으로 변환해주는 도구입니다.

---

## ✅ `tsc-alias`란?

- TypeScript의 `tsconfig.json`에서 `paths`를 사용하여 **경로 별칭**을 정의할 수 있습니다.
- TypeScript는 `tsc` 컴파일 시 **경로 별칭**을 변환하지 않고, 상대 경로로 컴파일합니다.
- `tsc-alias`는 컴파일 이후에 이러한 **경로를 자동으로 변환**해주는 역할을 합니다.

---

## 📦 `tsc-alias` 설치

```bash
npm install --save-dev tsc-alias
```

또는

```bash
yarn add -D tsc-alias
```

---

## 🛠️ `tsc-alias` 사용 예제

### 📂 프로젝트 구조

```plaintext
my-project/
├── tsconfig.json
├── src/
│   ├── utils/
│   │   └── helper.ts
│   └── index.ts
├── dist/ (컴파일 후 생성)
└── package.json
```

### ✅ `tsconfig.json` 설정

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "strict": true,
    "outDir": "dist",
    "rootDir": "src",
    "baseUrl": "./src",
    "paths": {
      "@utils/*": ["utils/*"]
    }
  }
}
```

📦 **설명:**
- `baseUrl`: `src` 디렉터리를 기준으로 경로를 설정.
- `paths`: `@utils`라는 별칭으로 `src/utils` 경로를 참조.

### ✅ `src/utils/helper.ts`

```typescript
export const sayHello = (name: string) => {
    return `안녕하세요, ${name}!`;
};
```

### ✅ `src/index.ts`

```typescript
import { sayHello } from "@utils/helper";

console.log(sayHello("TypeScript"));
```

---

## 🚀 **Step 1: TypeScript 컴파일 (`tsc`)**

```bash
npx tsc
```

📦 **컴파일 결과 (`dist/index.js`):**
```javascript
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const helper_1 = require("@utils/helper"); // 아직 변환되지 않음
console.log((0, helper_1.sayHello)("TypeScript"));
```

### ❗ **문제점:**
- `tsc`로 컴파일했을 때, `@utils/helper`가 여전히 경로 별칭으로 남아있음.
- JavaScript에서는 `@utils`를 해석할 수 없으므로 **런타임 에러** 발생.

---

## 🚀 **Step 2: `tsc-alias` 적용**

```bash
npx tsc-alias
```

📦 **변환된 `dist/index.js` (정상 작동):**
```javascript
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const helper_1 = require("../utils/helper"); // 경로 변환 완료
console.log((0, helper_1.sayHello)("TypeScript"));
```

✅ **이제 `tsc-alias`가 경로를 변환했으므로, 프로젝트가 정상적으로 실행됩니다.**

---

## 🛠️ **tsc-alias를 `package.json`에 추가하기**

`tsc`와 `tsc-alias`를 함께 사용하도록 `package.json`에 스크립트를 추가할 수 있습니다.

```json
{
  "scripts": {
    "build": "tsc && tsc-alias"
  }
}
```

✅ **빌드 실행:**

```bash
npm run build
```

---

## 🎯 **tsc-alias 주요 옵션**

| 옵션                      | 설명                                   |
|--------------------------|--------------------------------------|
| `--config`               | `tsconfig.json`의 경로를 지정합니다. |
| `--verbose`              | 변환 과정을 자세하게 출력합니다.     |
| `--resolveFullPaths`     | 전체 경로를 절대 경로로 변환합니다.  |

### ✅ 예시:
```bash
npx tsc-alias --config ./tsconfig.json --verbose
```

---

## 🛠️ **경로 별칭 없이 사용하는 경우 (비교)**

### ✅ 기존 방식 (상대 경로 사용):

```typescript
import { sayHello } from "../utils/helper";
```

### ✅ 경로 별칭 사용 (`tsc-alias` 적용 전):

```typescript
import { sayHello } from "@utils/helper";
```

✅ **경로 별칭 사용의 장점:**
- **코드 가독성 향상**
- **복잡한 경로 참조 최소화**
- **대규모 프로젝트에서 유지보수 용이**

---

## 📦 **tsc-alias vs tsconfig-paths 비교**

| 특징                        | `tsc-alias`                       | `tsconfig-paths`                  |
|-----------------------------|-----------------------------------|-----------------------------------|
| **사용 시점**              | 컴파일 후 사용                   | 런타임 시 사용                    |
| **설치 방식**              | `devDependencies`                | `dependencies`                    |
| **적용 방식**              | `tsc` 실행 후 경로 변환          | 런타임에서 경로 해석              |
| **사용 목적**              | Node.js 환경                     | Node.js + TypeScript 프로젝트    |
| **지원 환경**              | `CommonJS`, `ESM` 모두 지원      | 주로 Node.js 기반 프로젝트        |

---

## ✅ **결론: `tsc-alias`를 사용하는 이유**
- TypeScript의 **경로 별칭을 손쉽게 변환**할 수 있습니다.
- **프로젝트의 코드 가독성을 향상**시킬 수 있습니다.
- 대규모 프로젝트의 **경로 복잡성 문제**를 해결합니다.

이 문서가 `tsc-alias`를 사용하는데 도움이 되었길 바랍니다! ✅
