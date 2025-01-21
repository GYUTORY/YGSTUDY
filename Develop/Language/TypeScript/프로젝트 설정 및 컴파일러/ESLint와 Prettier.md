
# 🌟 TypeScript Linter와 포매터 설정 (ESLint & Prettier)

## 📚 개요

TypeScript 프로젝트에서는 **코드 품질 유지**와 **일관성 확보**를 위해 **ESLint**와 **Prettier**를 함께 사용하는 것이 일반적입니다.

이 문서에서는 **ESLint**와 **Prettier**를 TypeScript 프로젝트에 설정하는 방법과 함께 **eslint-config-airbnb-typescript**를 사용하는 예제를 소개합니다.

---

# 📦 1. Linter와 포매터란?

### ✅ Linter (ESLint)
- **Linter**는 **코드 오류**와 **스타일 규칙 위반**을 검사하는 도구입니다.
- 코드 일관성을 유지하고 버그를 방지합니다.

### ✅ 포매터 (Prettier)
- **포매터**는 **코드 스타일을 자동으로 정리**해주는 도구입니다.
- 가독성을 높이고, 코드 리뷰에서 스타일 논쟁을 줄입니다.

---

# 📦 2. ESLint와 Prettier 설치

```bash
npm install --save-dev eslint prettier eslint-config-airbnb-typescript eslint-plugin-prettier eslint-config-prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

### ✅ 설치되는 패키지 설명
- `eslint`: ESLint 핵심 패키지
- `prettier`: 코드 포맷팅 도구
- `eslint-config-airbnb-typescript`: Airbnb의 TypeScript 스타일 가이드
- `eslint-plugin-prettier`: Prettier를 ESLint에 통합
- `eslint-config-prettier`: Prettier와 ESLint 간 충돌 방지
- `@typescript-eslint/parser`: TypeScript를 위한 ESLint 파서
- `@typescript-eslint/eslint-plugin`: TypeScript용 ESLint 규칙 모음

---

# 📦 3. **ESLint 설정 파일 (`.eslintrc.json`)**

```json
{
  "env": {
    "browser": true,
    "es2022": true,
    "node": true
  },
  "extends": [
    "airbnb-typescript/base",
    "plugin:@typescript-eslint/recommended",
    "plugin:prettier/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint",
    "prettier"
  ],
  "rules": {
    "prettier/prettier": "error",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

### ✅ 설정 설명
- `"env"`: 프로젝트 환경을 지정합니다. (`browser`, `node`)
- `"extends"`: 여러 스타일 가이드를 조합해 사용합니다.
- `"parser"`: TypeScript 코드를 파싱하기 위해 `@typescript-eslint/parser`를 사용합니다.
- `"rules"`: **사용자 정의 규칙**을 설정할 수 있습니다.

---

# 📦 4. **Prettier 설정 파일 (`.prettierrc`)**

```json
{
  "singleQuote": true,
  "semi": true,
  "trailingComma": "all",
  "tabWidth": 2
}
```

### ✅ 설정 설명
- `"singleQuote"`: 작은따옴표 사용 (`true`)
- `"semi"`: 세미콜론 사용 (`true`)
- `"trailingComma"`: 여러 줄일 때 쉼표 유지 (`all`)
- `"tabWidth"`: 탭 간격 설정 (2칸)

---

# 📦 5. **TypeScript + ESLint + Prettier 연동**

### 📦 `package.json` 수정 (스크립트 추가)

```json
{
  "scripts": {
    "lint": "eslint 'src/**/*.{ts,tsx}' --fix",
    "format": "prettier --write 'src/**/*.{ts,tsx}'",
    "build": "tsc"
  }
}
```

### ✅ 설명
- `"lint"`: ESLint를 실행하여 코드 스타일 검사 및 자동 수정
- `"format"`: Prettier를 사용해 코드 포맷팅
- `"build"`: TypeScript 컴파일

---

# 📦 6. **eslint-config-airbnb-typescript 사용법**

`eslint-config-airbnb-typescript`는 **Airbnb의 TypeScript 스타일 가이드**를 적용할 수 있도록 도와줍니다.

### 📦 `.eslintrc.json`에 적용

```json
{
  "extends": [
    "airbnb-typescript/base",
    "plugin:@typescript-eslint/recommended",
    "plugin:prettier/recommended"
  ]
}
```

### ✅ 주요 규칙 설명
- **`airbnb-typescript/base`**: Airbnb의 TypeScript 기본 규칙 적용
- **`plugin:@typescript-eslint/recommended`**: TypeScript 권장 규칙
- **`plugin:prettier/recommended`**: Prettier와의 충돌 방지

---

# 📦 7. **코드 예제 및 검사**

### 📂 `src/example.ts`
```typescript
const greet = (name: string): string => {
    return `Hello, ${name}!`;
};

console.log(greet("TypeScript"));
```

### ✅ 코드 검사 실행

```bash
npm run lint
```

📦 **출력 결과:**
```
No issues found! 🎉
```

### ✅ 코드 포맷팅 실행

```bash
npm run format
```

📦 **출력 결과:**
- 코드가 자동으로 포맷팅됩니다.

---

# 📦 8. **자주 발생하는 오류와 해결 방법**

### ❗ `Parsing error: "parserOptions.project" has been set for @typescript-eslint/parser.`

✅ **해결법:**
- `tsconfig.json`이 프로젝트 루트에 없는 경우 발생.
- `parserOptions`의 `"project"` 경로를 제대로 설정해야 합니다.

```json
{
  "parserOptions": {
    "project": "./tsconfig.json"
  }
}
```

---

# 🎯 **정리: ESLint & Prettier 주요 차이**

| 특징                  | ESLint                          | Prettier                        |
|-----------------------|--------------------------------|--------------------------------|
| **목적**              | 코드 품질 검사 (버그 방지)       | 코드 스타일 정리 (가독성 향상) |
| **설정 파일**         | `.eslintrc.json`               | `.prettierrc`                  |
| **자동 수정 가능 여부** | 가능 (`eslint --fix`)            | 가능 (`prettier --write`)       |
| **TypeScript 지원**   | `@typescript-eslint` 필요      | 별도 설정 필요 없음             |
| **주요 사용 사례**    | 코드 품질 유지, 버그 방지       | 일관된 코드 스타일 유지         |

---

## ✅ 결론

- **ESLint**는 **코드 품질 검사**, **Prettier**는 **코드 포매팅** 도구입니다.
- `eslint-config-airbnb-typescript`를 사용하면 **Airbnb의 스타일 가이드**를 쉽게 적용할 수 있습니다.
- ESLint와 Prettier를 **함께 사용하는 것이 추천**되며, 설정 파일을 조합하여 프로젝트를 더욱 효율적으로 관리할 수 있습니다.
