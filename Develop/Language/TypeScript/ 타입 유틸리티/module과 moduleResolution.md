
# 🌟 TypeScript `module`과 `moduleResolution`의 차이

## 📚 개요
- TypeScript에서 `module`과 `moduleResolution`은 **모듈 시스템**과 **모듈 해석 방식**을 정의하는 중요한 설정입니다.

---

# 📦 `module`이란?

`module`은 **TypeScript 코드가 어떤 방식으로 JavaScript 모듈로 변환될지**를 결정하는 옵션ㅁ입니다.

### ✅ 주요 모듈 시스템
| `module` 값          | 설명                                 |
|---------------------|------------------------------------|
| `"CommonJS"`       | Node.js에서 사용되는 전통적인 방식  |
| `"ESNext"`          | 최신 JavaScript 모듈 (ECMAScript 모듈) |
| `"AMD"`             | Asynchronous Module Definition (구형 브라우저용) |
| `"UMD"`             | CommonJS + AMD의 조합 (라이브러리 배포 시 사용) |
| `"ES2022"`          | 최신 ECMAScript 모듈 표준           |

---

### ✅ `module` 예제 (`CommonJS` vs `ESNext`)

### 📂 프로젝트 구조

```plaintext
src/
├── index.ts
├── math.ts
```

### ✅ `src/math.ts`
```typescript
export const add = (a: number, b: number): number => a + b;
```

### ✅ `src/index.ts` (`CommonJS` 예제)

```typescript
const { add } = require('./math'); // CommonJS 방식의 import
console.log("결과:", add(2, 3));
```

### ✅ `src/index.ts` (`ESNext` 예제)

```typescript
import { add } from './math'; // ESNext 방식의 import
console.log("결과:", add(2, 3));
```

---

### ✅ `tsconfig.json` (`CommonJS` 설정)
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS"
  }
}
```

### ✅ `tsconfig.json` (`ESNext` 설정)
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext"
  }
}
```

### ✅ 컴파일 결과 비교

**CommonJS (`dist/index.js`):**
```javascript
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const math_1 = require("./math");
console.log("결과:", math_1.add(2, 3));
```

**ESNext (`dist/index.js`):**
```javascript
import { add } from './math.js';
console.log("결과:", add(2, 3));
```

---

# 📦 `moduleResolution`이란?

`moduleResolution`은 **TypeScript 컴파일러가 import 경로를 해석하는 방식**을 정의합니다.

### ✅ 주요 옵션
| `moduleResolution` 값 | 설명                                   |
|----------------------|--------------------------------------|
| `"node"`             | Node.js 방식 (기본값, `node_modules` 탐색) |
| `"classic"`          | TypeScript 초기 방식 (상대 경로만 지원) |

---

### ✅ `moduleResolution` 예제

#### 📂 프로젝트 구조

```plaintext
src/
├── index.ts
├── utils/
│   └── math.ts
└── node_modules/
```

#### ✅ `src/utils/math.ts`
```typescript
export const multiply = (a: number, b: number): number => a * b;
```

#### ✅ `src/index.ts`
```typescript
import { multiply } from './utils/math';
console.log(multiply(2, 3));
```

### ✅ `tsconfig.json` (`moduleResolution: node`)
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "node"
  }
}
```

### ✅ 설명:
- `moduleResolution: "node"`일 경우:
    - **상대 경로**는 직접 파일을 찾고,
    - `node_modules` 내의 모듈도 탐색합니다.

- `moduleResolution: "classic"`일 경우:
    - **상대 경로**만 참조합니다.
    - `node_modules`를 탐색하지 않습니다.

---

# 🎯 `module` vs `moduleResolution` 비교

| 특징                  | `module`                      | `moduleResolution`                |
|---------------------|-----------------------------|---------------------------------|
| **역할**            | JS 모듈 시스템 결정         | import 경로 해석 방식 정의         |
| **주요 옵션**       | `"CommonJS"`, `"ESNext"`    | `"node"`, `"classic"`            |
| **사용 시점**       | JS로 컴파일 시 적용         | 컴파일 시 import 경로 해석         |
| **Node.js 지원**    | `CommonJS`                  | `node`                          |
| **모던 브라우저 지원** | `ESNext`                    | `node` (ESNext와 사용)            |

---

## ✅ 결론

- **`module`**은 TypeScript가 어떤 **JavaScript 모듈 시스템**으로 변환할지 설정합니다.
- **`moduleResolution`**은 TypeScript가 **import 경로를 어떻게 해석할지**를 결정합니다.
- **Node.js 프로젝트** → `"CommonJS"` + `"node"` 사용
- **최신 브라우저 프로젝트** → `"ESNext"` + `"node"` 사용
