---
title: TypeScript 컴파일러(tsc) 사용법
tags: [language, typescript, 프로젝트-설정-및-컴파일러, tsc, compiler]
updated: 2025-08-10
---

# TypeScript 컴파일러(tsc) 사용법

## 배경

`tsc`는 TypeScript Compiler(타입스크립트 컴파일러)의 약자로, TypeScript 코드를 JavaScript 코드로 변환하는 명령어입니다. TypeScript의 핵심 도구로 타입 검사와 코드 변환을 담당합니다.

### tsc의 필요성
- **타입 검사**: 컴파일 타임에 타입 오류 감지
- **코드 변환**: TypeScript를 JavaScript로 변환
- **프로젝트 빌드**: 대규모 프로젝트의 효율적인 빌드
- **개발 환경**: 다양한 JavaScript 환경에서의 실행

### 기본 개념
- **컴파일**: TypeScript(.ts) 파일을 JavaScript(.js) 파일로 변환
- **타입 검사**: 컴파일 과정에서 타입 오류 검출
- **설정 파일**: `tsconfig.json`을 통한 컴파일 옵션 관리

## 핵심

### 1. 기본 컴파일

#### 단일 파일 컴파일
```bash
npx tsc src/index.ts
```

#### 예제 파일
```typescript
// src/index.ts
const greet = (name: string): string => {
    return `안녕하세요, ${name}!`;
};

console.log(greet('TypeScript'));
```

#### 컴파일 결과
```javascript
// src/index.js
"use strict";
const greet = (name) => {
    return `안녕하세요, ${name}!`;
};
console.log(greet('TypeScript'));
```

### 2. 프로젝트 초기화

#### tsconfig.json 생성
```bash
npx tsc --init
```

#### 기본 tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "strict": true,
    "outDir": "dist",
    "rootDir": "src",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### 주요 설정 설명
- `"target"`: 컴파일 대상 JavaScript 버전
- `"module"`: 모듈 시스템 (CommonJS는 Node.js 환경에 적합)
- `"strict"`: 엄격한 타입 검사 활성화
- `"outDir"`: 컴파일된 JavaScript 파일의 출력 폴더
- `"rootDir"`: 소스 파일의 루트 경로
- `"include"`: 포함할 파일 경로 패턴
- `"exclude"`: 제외할 파일 경로 패턴

### 3. 감시 모드 (Watch Mode)

#### 파일 변경 감지 및 자동 컴파일
```bash
npx tsc --watch
```

#### 사용 예시
```bash
# 백그라운드에서 감시 모드 실행
npx tsc --watch &

# 특정 설정 파일로 감시 모드 실행
npx tsc --watch --project ./tsconfig.json
```

### 4. 고급 컴파일 옵션

#### 타입 검사만 수행 (컴파일 없음)
```bash
npx tsc --noEmit
```

#### 소스맵 생성
```bash
npx tsc --sourceMap
```

#### 선언 파일 생성
```bash
npx tsc --declaration
```

#### 증분 컴파일
```bash
npx tsc --incremental
```

## 예시

### 1. 실제 사용 사례

#### 간단한 TypeScript 프로젝트
```typescript
// src/types/user.ts
export interface User {
    id: number;
    name: string;
    email: string;
    age?: number;
}

export interface CreateUserRequest {
    name: string;
    email: string;
    age?: number;
}

// src/utils/validation.ts
import { User, CreateUserRequest } from '../types/user';

export function validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

export function validateUser(user: any): user is User {
    return (
        typeof user === 'object' &&
        typeof user.id === 'number' &&
        typeof user.name === 'string' &&
        validateEmail(user.email)
    );
}

export function createUser(data: CreateUserRequest): User {
    if (!validateEmail(data.email)) {
        throw new Error('유효하지 않은 이메일입니다.');
    }

    return {
        id: Date.now(),
        name: data.name,
        email: data.email,
        age: data.age,
    };
}

// src/index.ts
import { createUser, validateUser } from './utils/validation';
import { User } from './types/user';

const userData = {
    name: '홍길동',
    email: 'hong@example.com',
    age: 30,
};

try {
    const newUser = createUser(userData);
    console.log('사용자 생성 성공:', newUser);

    if (validateUser(newUser)) {
        console.log('유효한 사용자입니다.');
    }
} catch (error) {
    console.error('사용자 생성 실패:', error.message);
}
```

#### 컴파일 및 실행
```bash
# TypeScript 컴파일
npx tsc

# 컴파일된 JavaScript 실행
node dist/index.js
```

### 2. 고급 패턴

#### 다중 설정 파일 사용
```json
// tsconfig.base.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}

// tsconfig.json
{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}

// tsconfig.test.json
{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist-test",
    "rootDir": "tests"
  },
  "include": ["tests/**/*"],
  "exclude": ["node_modules", "dist-test"]
}
```

#### 빌드 스크립트 설정
```json
// package.json
{
  "name": "typescript-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "build:watch": "tsc --watch",
    "build:prod": "tsc --sourceMap false --declaration false",
    "type-check": "tsc --noEmit",
    "clean": "rimraf dist",
    "rebuild": "npm run clean && npm run build"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "rimraf": "^5.0.0"
  }
}
```

#### CI/CD 파이프라인 통합
```yaml
# .github/workflows/build.yml
name: Build TypeScript

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Type check
      run: npm run type-check
    
    - name: Build
      run: npm run build
    
    - name: Upload build artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: dist/
```

## 운영 팁

### 성능 최적화

#### 증분 컴파일 활용
```json
// tsconfig.json - 성능 최적화
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

#### 빌드 캐싱
```bash
# 캐시 디렉토리 설정
export TS_NODE_CACHE_DIRECTORY=./node_modules/.cache/ts-node

# 증분 빌드 실행
npx tsc --incremental
```

### 에러 처리

#### 컴파일 오류 해결
```bash
# 상세한 오류 정보 출력
npx tsc --pretty

# 특정 파일만 컴파일
npx tsc src/index.ts

# 타입 검사만 수행
npx tsc --noEmit
```

#### 일반적인 문제 해결
```typescript
// 문제: 모듈을 찾을 수 없음
// 해결: tsconfig.json의 paths 설정 확인

// 올바른 설정
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    }
  }
}

// 문제: 타입 정의 파일 누락
// 해결: @types 패키지 설치
npm install --save-dev @types/node
```

## 참고

### tsc vs 다른 도구 비교표

| 도구 | 목적 | 장점 | 단점 |
|------|------|------|------|
| **tsc** | TypeScript 컴파일 | 공식 도구, 안정적 | 번들링 기능 없음 |
| **webpack** | 번들링 및 컴파일 | 강력한 기능 | 복잡한 설정 |
| **rollup** | 번들링 | 트리 쉐이킹 | 플러그인 의존성 |
| **vite** | 개발 서버 및 빌드 | 빠른 개발 | 새로운 도구 |

### 주요 컴파일 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--target` | JavaScript 버전 | ES3 |
| `--module` | 모듈 시스템 | CommonJS |
| `--outDir` | 출력 디렉토리 | - |
| `--rootDir` | 루트 디렉토리 | - |
| `--strict` | 엄격 모드 | false |
| `--sourceMap` | 소스맵 생성 | false |

### 결론
tsc는 TypeScript 프로젝트의 핵심 컴파일 도구입니다.
적절한 tsconfig.json 설정으로 효율적인 빌드 환경을 구축하세요.
증분 컴파일과 캐싱을 활용하여 빌드 성능을 최적화하세요.
CI/CD 파이프라인에 통합하여 자동화된 빌드 프로세스를 구축하세요.
타입 검사와 컴파일을 분리하여 개발 워크플로우를 개선하세요.
다중 설정 파일을 활용하여 다양한 환경에 대응하세요.

