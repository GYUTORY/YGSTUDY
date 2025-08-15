---
title: TypeScript tsc vs ts-node 완벽 가이드
tags: [language, typescript, typescript-기본-개념, tsc, ts-node, compiler]
updated: 2025-08-10
---

# TypeScript tsc vs ts-node 완벽 가이드

## 배경

TypeScript 개발에서 `tsc`와 `ts-node`는 각각 다른 목적을 가진 중요한 도구입니다.

### tsc의 필요성
- **컴파일**: TypeScript 코드를 JavaScript로 변환
- **프로덕션 빌드**: 배포용 JavaScript 파일 생성
- **타입 검사**: 컴파일 타임에 타입 오류 감지
- **정적 분석**: 코드 품질 및 오류 검증

### ts-node의 필요성
- **개발 환경**: TypeScript 코드를 직접 실행
- **빠른 피드백**: 컴파일 없이 즉시 실행
- **REPL 지원**: 대화형 TypeScript 실행
- **테스트 환경**: 단위 테스트 및 디버깅

## 핵심

### 1. tsc (TypeScript Compiler)

#### tsc 설치 및 기본 사용법
```bash
# 전역 설치
npm install -g typescript

# 로컬 설치
npm install --save-dev typescript
```

#### 기본 컴파일
```bash
# 단일 파일 컴파일
tsc app.ts

# 여러 파일 컴파일
tsc file1.ts file2.ts file3.ts

# 전체 프로젝트 컴파일 (tsconfig.json 사용)
tsc
```

#### TypeScript 파일 예제
```typescript
// app.ts
interface User {
    id: number;
    name: string;
    email: string;
}

class UserService {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    getUser(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }
}

const userService = new UserService();
userService.addUser({ id: 1, name: '홍길동', email: 'hong@example.com' });

console.log(userService.getUser(1));
```

#### 컴파일 결과
```bash
# 컴파일 실행
tsc app.ts

# 생성된 JavaScript 파일 (app.js)
"use strict";
class UserService {
    constructor() {
        this.users = [];
    }
    addUser(user) {
        this.users.push(user);
    }
    getUser(id) {
        return this.users.find(user => user.id === id);
    }
}
const userService = new UserService();
userService.addUser({ id: 1, name: '홍길동', email: 'hong@example.com' });
console.log(userService.getUser(1));
```

### 2. ts-node (TypeScript Node.js 실행기)

#### ts-node 설치 및 기본 사용법
```bash
# 전역 설치
npm install -g ts-node

# 로컬 설치
npm install --save-dev ts-node
```

#### 직접 실행
```bash
# TypeScript 파일 직접 실행
ts-node app.ts

# REPL 모드
ts-node

# 특정 TypeScript 버전으로 실행
ts-node --compiler-options '{"target":"es2020"}' app.ts
```

#### ts-node 설정 예제
```json
// package.json
{
  "scripts": {
    "start": "ts-node src/index.ts",
    "dev": "ts-node --watch src/index.ts",
    "test": "ts-node tests/**/*.ts"
  },
  "devDependencies": {
    "ts-node": "^10.9.1",
    "typescript": "^5.0.0"
  }
}
```

### 3. tsconfig.json 설정

#### 기본 tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### ts-node 전용 설정
```json
{
  "ts-node": {
    "compilerOptions": {
      "target": "ES2022",
      "module": "CommonJS"
    },
    "files": true,
    "transpileOnly": false
  }
}
```

## 예시

### 1. 실제 사용 사례

#### 프로젝트 구조 예제
```plaintext
my-typescript-project/
├── src/
│   ├── index.ts
│   ├── utils.ts
│   └── types.ts
├── dist/
├── tests/
│   └── utils.test.ts
├── package.json
└── tsconfig.json
```

#### 개발 환경 설정
```json
// package.json
{
  "name": "my-typescript-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "test": "ts-node tests/**/*.test.ts",
    "watch": "ts-node --watch src/index.ts"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "ts-node": "^10.9.1",
    "@types/node": "^20.0.0"
  }
}
```

#### 소스 코드 예제
```typescript
// src/types.ts
export interface User {
    id: number;
    name: string;
    email: string;
    createdAt: Date;
}

export interface CreateUserRequest {
    name: string;
    email: string;
}

// src/utils.ts
import { User, CreateUserRequest } from './types';

export function createUser(data: CreateUserRequest): User {
    return {
        id: Date.now(),
        name: data.name,
        email: data.email,
        createdAt: new Date()
    };
}

export function validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// src/index.ts
import { createUser, validateEmail } from './utils';
import { CreateUserRequest } from './types';

function main() {
    const userData: CreateUserRequest = {
        name: '홍길동',
        email: 'hong@example.com'
    };

    if (validateEmail(userData.email)) {
        const user = createUser(userData);
        console.log('사용자가 생성되었습니다:', user);
    } else {
        console.error('유효하지 않은 이메일 주소입니다.');
    }
}

main();
```

#### 테스트 코드 예제
```typescript
// tests/utils.test.ts
import { createUser, validateEmail } from '../src/utils';

// 간단한 테스트 함수
function test(description: string, testFn: () => boolean) {
    try {
        const result = testFn();
        console.log(`✅ ${description}: ${result ? 'PASS' : 'FAIL'}`);
    } catch (error) {
        console.log(`❌ ${description}: FAIL - ${error}`);
    }
}

// 테스트 실행
test('createUser should create user with correct properties', () => {
    const userData = { name: '홍길동', email: 'hong@example.com' };
    const user = createUser(userData);
    
    return user.id > 0 && 
           user.name === userData.name && 
           user.email === userData.email &&
           user.createdAt instanceof Date;
});

test('validateEmail should return true for valid email', () => {
    return validateEmail('test@example.com') === true;
});

test('validateEmail should return false for invalid email', () => {
    return validateEmail('invalid-email') === false;
});
```

### 2. 고급 패턴

#### 개발 환경 최적화
```json
// tsconfig.json - 개발 환경 최적화
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "sourceMap": true,
    "removeComments": false,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"],
  "ts-node": {
    "compilerOptions": {
      "module": "CommonJS"
    },
    "transpileOnly": false,
    "files": true
  }
}
```

#### 프로덕션 빌드 스크립트
```json
// package.json - 프로덕션 빌드 설정
{
  "scripts": {
    "clean": "rimraf dist",
    "build": "npm run clean && tsc",
    "build:prod": "npm run clean && tsc --project tsconfig.prod.json",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "dev:watch": "ts-node --watch src/index.ts",
    "test": "ts-node tests/**/*.test.ts",
    "test:watch": "ts-node --watch tests/**/*.test.ts"
  }
}
```

#### 프로덕션용 TypeScript 설정
```json
// tsconfig.prod.json - 프로덕션 빌드 최적화
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "removeComments": true,
    "sourceMap": false,
    "declaration": false,
    "outDir": "./dist",
    "target": "ES2020",
    "module": "CommonJS"
  },
  "exclude": ["tests/**/*", "**/*.test.ts", "**/*.spec.ts"]
}
```

## 운영 팁

### 성능 최적화

#### ts-node 성능 최적화
```json
// tsconfig.json - ts-node 성능 최적화
{
  "ts-node": {
    "compilerOptions": {
      "target": "ES2022",
      "module": "CommonJS"
    },
    "transpileOnly": true,  // 타입 검사 건너뛰기로 성능 향상
    "files": false,         // 파일 목록 로딩 건너뛰기
    "experimentalSpecifierResolution": "node"
  }
}
```

#### 캐싱 활용
```bash
# ts-node 캐시 사용
ts-node --cachedir ./node_modules/.cache/ts-node app.ts

# 또는 환경 변수 설정
export TS_NODE_CACHE_DIRECTORY=./node_modules/.cache/ts-node
ts-node app.ts
```

### 에러 처리

#### 타입 오류 처리
```typescript
// 타입 오류가 있는 코드 예제
function processUser(user: any) {
    // any 타입 사용으로 타입 안전성 저하
    console.log(user.name.toUpperCase());
    return user.age + 5;
}

// ts-node로 실행 시 타입 오류 경고
// tsc로 컴파일 시 타입 오류로 컴파일 실패
```

#### 컴파일 오류 해결
```bash
# 타입 오류 무시하고 컴파일 (권장하지 않음)
tsc --noEmitOnError false

# 특정 오류 무시
tsc --skipLibCheck

# 타입 검사만 수행 (컴파일하지 않음)
tsc --noEmit
```

## 참고

### tsc vs ts-node 비교표

| 구분 | tsc | ts-node |
|------|-----|---------|
| **주요 목적** | TypeScript → JavaScript 변환 | TypeScript 직접 실행 |
| **컴파일 파일 생성** | JavaScript 파일 생성 | 메모리 내에서 직접 실행 |
| **사용 사례** | 프로덕션 빌드, 정적 코드 변환 | 개발 환경, 빠른 테스트 |
| **속도** | 느림 (컴파일 필요) | 빠름 (컴파일 없이 실행) |
| **장점** | 정적 코드 변환, 안정성 보장 | 빠른 개발 루프, REPL 지원 |
| **설치** | `npm install -g typescript` | `npm install -g ts-node` |

### 사용 시나리오별 권장사항

| 시나리오 | 권장 도구 | 이유 |
|----------|-----------|------|
| **개발 중 빠른 테스트** | ts-node | 즉시 실행, 빠른 피드백 |
| **프로덕션 빌드** | tsc | 최적화된 JavaScript 생성 |
| **CI/CD 파이프라인** | tsc | 안정적인 빌드 프로세스 |
| **REPL 및 디버깅** | ts-node | 대화형 실행 환경 |
| **타입 검사만 수행** | tsc --noEmit | 컴파일 없이 타입 검사 |

### 결론
tsc는 TypeScript 코드를 JavaScript로 변환하는 공식 컴파일러입니다.
ts-node는 개발 환경에서 TypeScript 코드를 직접 실행할 수 있게 해주는 도구입니다.
개발 시에는 ts-node를 사용하여 빠른 피드백을 얻으세요.
프로덕션 배포 시에는 tsc를 사용하여 최적화된 JavaScript를 생성하세요.
적절한 tsconfig.json 설정으로 개발 효율성을 향상시키세요.
성능 최적화 옵션을 활용하여 개발 속도를 개선하세요.






`tsc`와 `