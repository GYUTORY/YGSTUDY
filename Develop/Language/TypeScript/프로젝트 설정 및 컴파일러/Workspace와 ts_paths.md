
# 🌟 TypeScript 워크스페이스와 `ts-paths` 차이 이해하기 (A, B, C, D 각각 독립 레포 설정)

## 📚 개요

TypeScript 프로젝트에서 여러 개의 독립 레포지토리를 구성할 수 있습니다.
여기서는 **워크스페이스(workspaces)**와 **ts-paths**를 비교하며, 각각의 설정과 차이점을 설명합니다.

- **워크스페이스(workspaces)**: 프로젝트를 물리적으로 분리하고, 각 레포를 하나의 프로젝트로 관리합니다.
- **ts-paths**: TypeScript `tsconfig.json`의 경로 매핑을 사용하여, 코드를 모듈화하고 가상 경로를 지정합니다.

---

## 🏗️ 프로젝트 구조 (각각 독립 레포)

A, B, C, D 레포지토리는 각각 **독립적으로** 존재하지만, A 레포에서 B, C, D를 참조합니다.

```plaintext
project-dir/
├── A-Repo/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
├── B-Repo/
│   ├── package.json
│   ├── tsconfig.json
│   └── lib/
├── C-Repo/
│   ├── package.json
│   ├── tsconfig.json
│   └── utils/
├── D-Repo/
│   ├── package.json
│   ├── tsconfig.json
│   └── api/
```

---

## 🛠️ Step 1: A-Repo의 `package.json` (워크스페이스 사용 예시)

```json
{
  "name": "A-Repo",
  "private": true,
  "workspaces": [
    "../B-Repo",
    "../C-Repo",
    "../D-Repo"
  ],
  "dependencies": {
    "B-Repo": "workspace:*",
    "C-Repo": "workspace:*",
    "D-Repo": "workspace:*"
  }
}
```

### ✍️ 설명
- `private`: 외부 배포를 방지.
- `workspaces`: A 레포에서 B, C, D를 직접 참조.

### 📦 B-Repo, C-Repo, D-Repo의 `package.json`

각 하위 레포는 `package.json` 파일에서 독립적으로 구성됩니다.

```json
{
  "name": "B-Repo",
  "version": "1.0.0",
  "main": "lib/index.js",
  "scripts": {
    "build": "tsc"
  }
}
```

---

## 📝 Step 2: TypeScript 설정 (`tsconfig.json`)

### `A-Repo/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "composite": true,
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src",
    "strict": true
  },
  "references": [
    { "path": "../B-Repo" },
    { "path": "../C-Repo" },
    { "path": "../D-Repo" }
  ]
}
```

### `B-Repo/tsconfig.json`

```json
{
  "extends": "../A-Repo/tsconfig.json",
  "compilerOptions": {
    "rootDir": "lib",
    "outDir": "dist"
  },
  "include": ["lib"]
}
```

---

## 🚀 Step 3: 실행 및 빌드

1. **패키지 설치**
   ```bash
   pnpm install
   ```

2. **빌드 실행**
   ```bash
   pnpm run build
   ```

---

# 📊 `ts-paths`란?

**`ts-paths`**는 TypeScript에서 가상 경로를 사용하여 모듈을 참조할 수 있게 합니다.

### ✅ 사용 예시 (`tsconfig.json`)

```json
{
  "compilerOptions": {
    "baseUrl": "./",
    "paths": {
      "@utils/*": ["utils/*"],
      "@api/*": ["api/*"]
    }
  }
}
```

### ✅ `import` 방식

```typescript
import { fetchData } from "@api/fetch";
import { formatDate } from "@utils/date";
```

---

# 🔑 **워크스페이스 vs ts-paths 비교**

| 특징                    | 워크스페이스 (`workspaces`) | `ts-paths` |
|-------------------------|-----------------------------|------------|
| **사용 목적**           | 여러 독립 레포지토리 관리   | 경로 단축 |
| **종속성 관리**         | `package.json`에서 직접 관리 | `tsconfig.json` 경로 설정 |
| **빌드 방식**           | 패키지 매니저에 의해 자동 빌드 | TypeScript 컴파일러 사용 |
| **적용 방식**           | 패키지 전체 참조            | 모듈 단위 참조 |
| **장점**                | 대규모 프로젝트에 적합      | 소규모 프로젝트에 적합 |
| **단점**                | 설정 복잡도 증가            | 패키지 간 의존성 약함 |

---

# ✅ 결론

- **워크스페이스**는 **독립된 프로젝트** 간의 강한 종속성을 유지할 때 유용합니다.
- **ts-paths**는 **단순 경로 매핑**으로, 의존성 관리보다 코드를 보기 쉽게 하기 위한 용도입니다.

이 문서가 A, B, C, D 각각 독립 레포지토리와 `ts-paths`의 차이를 이해하는데 도움이 되었길 바랍니다.
