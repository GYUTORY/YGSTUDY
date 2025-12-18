---
title: TypeScript Workspace와 ts-paths 가이드
tags: [language, typescript, 프로젝트-설정-및-컴파일러, workspace, ts-paths]
updated: 2025-12-18
---

# TypeScript Workspace와 ts-paths 가이드

## 배경

TypeScript 프로젝트에서 여러 개의 독립 레포지토리를 구성할 때 워크스페이스(workspaces)와 ts-paths를 사용할 수 있습니다.

### Workspace와 ts-paths의 필요성
- **멀티 패키지 관리**: 여러 독립적인 패키지를 하나의 프로젝트로 관리
- **경로 단순화**: 복잡한 상대 경로를 절대 경로로 단순화
- **의존성 관리**: 패키지 간 의존성을 체계적으로 관리
- **빌드 최적화**: 의존성 순서를 고려한 효율적인 빌드

### 기본 개념
- **Workspace**: 패키지 매니저의 멀티 패키지 관리 시스템
- **ts-paths**: TypeScript의 경로 매핑 기능
- **독립 레포**: 각각 별도의 패키지로 관리되는 레포지토리

## 핵심

### 1. Workspace 기본 설정

#### 프로젝트 구조
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
└── D-Repo/
    ├── package.json
    ├── tsconfig.json
    └── api/
```

#### A-Repo의 package.json (워크스페이스 설정)
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

#### 하위 레포의 package.json
```json
// B-Repo/package.json
{
  "name": "B-Repo",
  "version": "1.0.0",
  "main": "lib/index.js",
  "types": "lib/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  }
}
```

### 2. ts-paths 기본 설정

#### tsconfig.json 설정
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "baseUrl": "./",
    "paths": {
      "@utils/*": ["utils/*"],
      "@api/*": ["api/*"],
      "@lib/*": ["lib/*"],
      "@shared/*": ["shared/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### 사용 예시
```typescript
// src/index.ts
import { fetchData } from "@api/fetch";
import { formatDate } from "@utils/date";
import { Database } from "@lib/database";

console.log('Application started');
```

### 3. 통합 설정 패턴

#### 모노레포 구조
```plaintext
monorepo/
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.json
├── apps/
│   └── web/
│       ├── package.json
│       └── tsconfig.json
└── packages/
    ├── utils/
    │   ├── package.json
    │   └── tsconfig.json
    └── api/
        ├── package.json
        └── tsconfig.json
```

#### 루트 설정
```yaml
# pnpm-workspace.yaml
packages:
  - "apps/*"
  - "packages/*"
```

```json
// package.json
{
  "name": "monorepo",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "scripts": {
    "build": "pnpm -r build",
    "dev": "pnpm -r --parallel dev",
    "clean": "pnpm -r clean"
  }
}
```

## 예시

### 1. 실제 사용 사례

#### pnpm 워크스페이스 구성
```json
// packages/utils/package.json
{
  "name": "@acme/utils",
  "version": "1.0.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc -b",
    "clean": "tsc -b --clean"
  }
}
```

```json
// apps/web/package.json
{
  "name": "@acme/web",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build"
  },
  "dependencies": {
    "@acme/utils": "workspace:*",
    "@acme/api": "workspace:*"
  }
}
```

#### 빌드 설정
```json
// tsconfig.build.json
{
  "files": [],
  "references": [
    { "path": "packages/utils" },
    { "path": "packages/api" },
    { "path": "apps/web" }
  ]
}
```

### 2. 고급 설정 패턴

#### 조건부 경로 매핑
```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@components/*": ["components/*"],
      "@utils/*": ["utils/*"],
      "@api/*": ["api/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"],
  "ts-node": {
    "require": ["tsconfig-paths/register"]
  }
}
```

#### 개발 환경별 설정
```json
// tsconfig.dev.json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "sourceMap": true,
    "declaration": false
  }
}
```

```json
// tsconfig.prod.json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "sourceMap": false,
    "declaration": true,
    "removeComments": true
  }
}
```

## 운영 팁

### 성능 최적화

#### 빌드 순서 최적화
```bash
# 모든 패키지 빌드 (의존성 순서 고려)
pnpm -r build

# 특정 패키지만 빌드
pnpm --filter @acme/utils build

# 병렬 빌드
pnpm -r --parallel build
```

#### 캐싱 설정
```json
// .npmrc
store-dir=./node_modules/.pnpm-store
cache-dir=./node_modules/.cache
```

### 에러 처리

#### 의존성 문제 해결
```bash
# 의존성 그래프 확인
pnpm list --depth=1

# 워크스페이스 상태 확인
pnpm list --depth=0

# 특정 패키지 재설치
pnpm --filter @acme/utils install
```

#### 빌드 오류 해결
```bash
# 빌드 캐시 정리
pnpm -r clean

# TypeScript 빌드 정보 정리
rm -rf node_modules/.cache

# 전체 재설치
pnpm install --force
```

## 참고

### Workspace vs ts-paths 비교표

| 특징 | Workspace | ts-paths |
|------|-----------|----------|
| **사용 목적** | 멀티 패키지 관리 | 경로 단축 |
| **종속성 관리** | package.json에서 관리 | tsconfig.json 경로 설정 |
| **빌드 방식** | 패키지 매니저 자동 빌드 | TypeScript 컴파일러 |
| **적용 방식** | 패키지 전체 참조 | 모듈 단위 참조 |
| **장점** | 대규모 프로젝트 적합 | 소규모 프로젝트 적합 |
| **단점** | 설정 복잡도 증가 | 패키지 간 의존성 약함 |

### 권장 사용 패턴

#### 소규모 프로젝트
```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    }
  }
}
```

#### 대규모 모노레포
```json
// 루트 package.json
{
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

```json
// 루트 tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@core/*": ["packages/core/src/*"],
      "@utils/*": ["packages/utils/src/*"],
      "@ui/*": ["packages/ui/src/*"]
    }
  },
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/utils" },
    { "path": "./packages/ui" }
  ]
}
```

### 결론
Workspace와 ts-paths는 TypeScript 프로젝트의 구조화를 위한 상호 보완적인 도구입니다.
소규모 프로젝트에서는 ts-paths만으로도 충분하지만, 대규모 모노레포에서는 workspace를 함께 사용하는 것이 권장됩니다.
적절한 설정으로 개발 효율성과 코드 가독성을 동시에 향상시킬 수 있습니다.
정기적인 의존성 검토와 빌드 최적화로 프로젝트의 안정성을 유지하세요.

