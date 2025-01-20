
# 📦 TypeScript `tsconfig.json` 파일 완벽 가이드

## 👉🏻 `tsconfig.json`이란?
`tsconfig.json`은 **TypeScript 프로젝트의 구성 파일**로, TypeScript 컴파일러(`tsc`)가 코드를 어떻게 변환하고 검사할지를 정의하는 설정 파일입니다.

이 파일을 사용하면 프로젝트의 **컴파일 옵션, 경로 설정, 출력 폴더** 등을 구성할 수 있습니다.

---

## 🎯 `tsconfig.json` 파일의 필요성
TypeScript는 **정적 타입 검사**와 **JavaScript로 변환**을 제공하는 언어입니다.  
이를 효과적으로 사용하기 위해 `tsconfig.json`을 통해 프로젝트의 설정을 명시적으로 관리합니다.

### 📌 주요 기능:
- **컴파일 옵션 설정**: 코드의 변환 방식 정의
- **타입 검사 설정**: 코드의 엄격성 설정
- **출력 경로 설정**: 컴파일 결과 파일 위치 정의
- **모듈 해석 설정**: 외부 모듈과의 경로 연결 설정

---

## ✅ `tsconfig.json` 파일 생성하기
프로젝트 루트에서 다음 명령어를 실행하면 자동으로 `tsconfig.json` 파일을 생성할 수 있습니다:

```bash
npx tsc --init
```

기본적으로 생성되는 `tsconfig.json` 파일의 예제:

```json
{
  "compilerOptions": {
    "target": "ES6",
    "module": "CommonJS",
    "outDir": "./dist",
    "strict": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## 📦 `tsconfig.json`의 주요 옵션 설명
### **1. `compilerOptions` (컴파일러 옵션)**
`compilerOptions`는 TypeScript 컴파일러가 코드를 어떻게 해석하고 변환할지를 정의합니다.

| 옵션                   | 설명                                           | 예제                  |
|-----------------------|---------------------------------|--------------------|
| `target`             | 컴파일 대상 JavaScript 버전 설정 | `"ES6"` |
| `module`             | 모듈 시스템 설정                   | `"CommonJS"` |
| `strict`             | 엄격한 타입 검사 모드 활성화       | `true` |
| `outDir`             | 컴파일 결과물 저장 폴더             | `"./dist"` |
| `sourceMap`          | 디버깅을 위한 소스맵 생성            | `true` |

---

### **2. `include`와 `exclude` (포함 및 제외 설정)**
- **`include`**: 컴파일할 파일의 경로를 설정합니다.
- **`exclude`**: 컴파일에서 제외할 파일을 설정합니다.

```json
{
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "**/*.test.ts"]
}
```

---

### **3. `baseUrl`와 `paths` (경로 별칭 설정)**
- **`baseUrl`**: 모듈 경로의 기준점을 설정합니다.
- **`paths`**: 별칭을 정의하여 모듈 경로를 짧게 만듭니다.

```json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@components/*": ["components/*"],
      "@utils/*": ["utils/*"]
    }
  }
}
```

사용 예제:

```typescript
import { Button } from "@components/Button";
import { formatDate } from "@utils/dateFormatter";
```

---

### **4. `strict` 모드 (엄격한 타입 검사)**
- **`strict`**: 엄격 모드를 활성화합니다.
- **`noImplicitAny`**: `any` 타입을 명시적으로 지정해야 합니다.
- **`strictNullChecks`**: `null`과 `undefined`를 더욱 엄격하게 검사합니다.

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

---

## 🛠️ 실전 예제: TypeScript 프로젝트 설정하기
### **1. 프로젝트 초기화**
```bash
mkdir my-ts-project
cd my-ts-project
npm init -y
npx tsc --init
```

### **2. `tsconfig.json` 설정**
```json
{
  "compilerOptions": {
    "target": "ES6",
    "module": "CommonJS",
    "outDir": "./dist",
    "strict": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### **3. `src/index.ts` 파일 생성**
```typescript
const message: string = "Hello, TypeScript!";
console.log(message);
```

### **4. 컴파일 및 실행**
```bash
npx tsc
node dist/index.js
```

---

## 📊 `tsconfig.json` vs `jsconfig.json` 비교

| 특징                     | `tsconfig.json`         | `jsconfig.json`         |
|-------------------------|-----------------------|-----------------------|
| **언어 지원**            | TypeScript 전용       | JavaScript 전용      |
| **타입 검사**            | 타입 검사 지원         | 제한적 타입 검사     |
| **사용 환경**            | TypeScript 프로젝트 | Vanilla JS 프로젝트 |

---

## 🎯 결론
`tsconfig.json`은 TypeScript 프로젝트의 핵심 구성 요소로, **컴파일 설정, 타입 검사, 모듈 해석** 등을 체계적으로 관리할 수 있습니다.  
효율적인 TypeScript 개발 환경을 구축하기 위해, 프로젝트에 맞는 `tsconfig.json`을 구성해 보세요!

> **🚀 지금 바로 TypeScript를 사용하여 강력한 애플리케이션을 개발해보세요!**
