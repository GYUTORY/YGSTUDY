
# TypeScript 컴파일러(`tsc`)와 `tsc-alias`

## 1. TypeScript와 `tsc`란?
TypeScript는 JavaScript의 상위 집합으로, 정적 타입 시스템을 제공하여 코드 안정성을 높이는 프로그래밍 언어입니다.  
`tsc`(TypeScript Compiler)는 TypeScript 코드를 JavaScript로 변환해주는 **컴파일러**입니다.

### 👉🏻 `tsc`의 주요 기능
- **TypeScript 파일을 JavaScript로 변환** (`.ts` → `.js`)
- **타입 검사 수행**: 컴파일 시 코드의 타입을 검사하고 에러를 알려줍니다.
- **설정 파일 사용 (`tsconfig.json`)**: 프로젝트 전반의 컴파일 옵션을 설정할 수 있습니다.

### ✨ `tsc` 설치 및 사용법
1. TypeScript 전역 설치:
   ```bash
   npm install -g typescript
   ```
2. TypeScript 프로젝트 생성:
   ```bash
   tsc --init
   ```
3. 특정 파일 컴파일:
   ```bash
   tsc example.ts
   ```
4. 프로젝트 전체 컴파일:
   ```bash
   tsc
   ```

---

## 2. `tsconfig.json` 설정 예제
`tsconfig.json` 파일은 TypeScript 프로젝트의 핵심 설정 파일입니다.

```json
{
  "compilerOptions": {
    "target": "ES6",
    "module": "CommonJS",
    "outDir": "./dist",
    "strict": true,
    "baseUrl": "./src",
    "paths": {
      "@utils/*": ["utils/*"],
      "@components/*": ["components/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

- **target**: 컴파일된 JS의 버전 (예: ES6, ES2015)
- **module**: 사용할 모듈 시스템 (예: CommonJS, ESNext)
- **outDir**: 컴파일된 JS 파일의 출력 경로
- **baseUrl**: 기본 경로 설정
- **paths**: 경로 별칭 설정

---

## 3. `tsc-alias`란?
`tsc-alias`는 TypeScript 프로젝트에서 **경로 별칭(Path Alias)**을 사용하는 경우,  
`tsc`로 컴파일한 JS 코드에서도 해당 별칭을 적용할 수 있도록 도와주는 도구입니다.

### 👉🏻 왜 필요한가요?
`tsc`만 사용했을 때:
```typescript
import { myFunction } from "@utils/myFunction";
```
컴파일 후 JS 파일에서는:
```javascript
const myFunction = require("@utils/myFunction");
```
이렇게 별칭이 그대로 남아 오류가 발생합니다.

---

### ✨ `tsc-alias` 설치 및 사용법
1. `tsc-alias` 설치:
   ```bash
   npm install --save-dev tsc-alias
   ```
2. `tsc`로 프로젝트 컴파일:
   ```bash
   tsc
   ```
3. 별칭 변환 적용:
   ```bash
   npx tsc-alias
   ```
4. 실행 스크립트 (`package.json`):
   ```json
   {
     "scripts": {
       "build": "tsc && tsc-alias"
     }
   }
   ```
---

## 4. `tsc`와 `tsc-alias`를 사용한 프로젝트 예제

### 📂 프로젝트 구조
```
my-project/
├── src/
│   ├── utils/
│   │   └── sum.ts
│   └── index.ts
├── dist/
├── tsconfig.json
├── package.json
├── tsconfig.json
```

### `sum.ts`
```typescript
export const sum = (a: number, b: number): number => {
    return a + b;
};
```

### `index.ts`
```typescript
import { sum } from "@utils/sum";

const result = sum(3, 5);
console.log("결과:", result);
```

---

## 5. 결론 🏁
- `tsc`: TypeScript를 JavaScript로 컴파일하고 타입 검사를 수행합니다.
- `tsc-alias`: 경로 별칭을 JS로 변환 후에도 유지시킵니다.
- **조합하여 사용**하면 TypeScript 프로젝트를 더 쉽게 관리할 수 있습니다.
