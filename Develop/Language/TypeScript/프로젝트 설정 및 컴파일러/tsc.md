
# 🌟 TypeScript 컴파일러 (`tsc`) 기본 사용법

## 📚 개요

`tsc`는 **TypeScript Compiler (타입스크립트 컴파일러)**의 약자로, TypeScript 코드를 JavaScript 코드로 변환하는 명령어입니다.

이 문서에서는 `tsc`의 사용법을 **예제와 함께 한 줄 한 줄 주석**을 포함하여 자세히 설명합니다.

---

## ✅ `tsc`란?

- **TypeScript 소스 코드 (.ts)**를 **JavaScript 코드 (.js)**로 변환하는 도구입니다.
- **타입 검사**와 **코드 컴파일**을 동시에 수행합니다.

---

# 🛠️ 1. `tsc` 명령어 사용법

TypeScript 파일을 컴파일하는 가장 기본적인 방법입니다.

### 📂 `src/index.ts` (예제 파일)

```typescript
// TypeScript 코드 예제
const greet = (name: string): string => {
    return `안녕하세요, ${name}!`;
};

console.log(greet('TypeScript'));
```

### ✅ `tsc` 명령어 실행

```bash
npx tsc src/index.ts
```

📦 **결과:**
- `src/index.ts` → `src/index.js`로 변환됨.

### 📦 **변환된 `src/index.js` 파일:**
```javascript
"use strict";
const greet = (name) => {
    return `안녕하세요, ${name}!`;
};
console.log(greet('TypeScript'));
```

---

# 🛠️ 2. `tsc --init`을 통한 프로젝트 초기화

`tsc --init` 명령어를 사용하면 **TypeScript 프로젝트를 초기화**할 수 있습니다.

```bash
npx tsc --init
```

📦 **실행 결과:**
- 프로젝트 루트에 `tsconfig.json` 파일이 생성됩니다.

### 📦 **기본 `tsconfig.json` 예제:**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "strict": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### ✅ 주요 설정 설명:
- `"target"`: 컴파일 대상 JavaScript 버전 (`ES2022`).
- `"module"`: 모듈 시스템 (`CommonJS`는 Node.js 환경에 적합).
- `"strict"`: 엄격한 타입 검사 활성화.
- `"outDir"`: 컴파일된 JavaScript 파일의 출력 폴더 (`dist`).
- `"rootDir"`: 소스 파일의 루트 경로 (`src`).
- `"include"`: 포함할 파일 경로 패턴.
- `"exclude"`: 제외할 파일 경로 패턴.

---

# 🛠️ 3. `tsc --watch` (파일 변경 감지 및 자동 컴파일)

`tsc --watch` 명령어는 **파일이 변경될 때 자동으로 컴파일**합니다.

```bash
npx tsc --watch
```

### ✅ 동작 방식:
- `src/` 폴더를 실시간으로 감시합니다.
- 파일이 수정될 때마다 **자동으로 컴파일**을 수행합니다.

📦 **예제 실행 순서:**
1. `npx tsc --watch`를 실행합니다.
2. `src/index.ts`를 수정합니다.
3. 변경이 감지되고 `dist/index.js`가 업데이트됩니다.

---

# 🛠️ 4. `tsc --build` (증분 빌드)

**증분 빌드**는 변경된 파일만 컴파일하여 **빌드 속도를 최적화**하는 기능입니다.

### ✅ `tsconfig.json`에서 `incremental` 활성화:

```json
{
  "compilerOptions": {
    "incremental": true
  }
}
```

### ✅ 증분 빌드 실행:

```bash
npx tsc --build
```

📦 **설명:**
- 첫 번째 빌드 시 모든 파일을 컴파일.
- 이후 변경된 파일만 재컴파일.

---

# 🎯 **TSC 사용법 요약 비교표**

| 명령어                 | 설명                                |
|----------------------|--------------------------------|
| `tsc --init`        | 프로젝트 초기화 (`tsconfig.json` 생성) |
| `tsc <파일명>.ts`    | 특정 파일을 컴파일 (JavaScript로 변환) |
| `tsc --watch`        | 파일 변경 감지 및 자동 컴파일         |
| `tsc --build`        | 증분 빌드 (변경된 파일만 재컴파일)    |

---

# ✅ **결론: TypeScript 컴파일러 정리**
- `tsc`는 **TypeScript를 JavaScript로 변환**하는 도구입니다.
- `tsc --init`으로 프로젝트를 초기화하고, `tsconfig.json`을 생성합니다.
- `tsc --watch`를 사용하면 **자동 컴파일**이 가능하며, `tsc --build`는 **효율적인 빌드**를 제공합니다.

이 문서가 TypeScript 프로젝트를 설정하고 사용하는 데 도움이 되었기를 바랍니다! ✅
