---
title: TypeScript tsc-alias 가이드
tags: [language, typescript, typescript-기본-개념, tsc-alias, path-alias]
updated: 2025-12-16
---

# TypeScript tsc-alias 가이드

## 배경

`tsc-alias`는 TypeScript의 `paths`와 `baseUrl`을 사용하는 프로젝트에서 경로 별칭(Path Alias)을 컴파일 후에 자동으로 변환해주는 도구입니다.

### tsc-alias의 필요성
- **경로 별칭 변환**: TypeScript 컴파일 후 경로 별칭을 상대 경로로 변환
- **런타임 호환성**: JavaScript 환경에서 경로 별칭 문제 해결
- **개발 편의성**: 복잡한 상대 경로 대신 의미있는 별칭 사용
- **유지보수성**: 파일 구조 변경 시 경로 수정 최소화

### 기본 개념
- **경로 별칭**: 복잡한 상대 경로를 간단한 별칭으로 대체
- **컴파일 후 처리**: TypeScript 컴파일 후 경로 변환 작업
- **tsconfig.json 연동**: TypeScript 설정 파일의 paths 설정 활용
- **자동 변환**: 수동 경로 수정 없이 자동으로 상대 경로 변환

## 핵심

### 1. tsc-alias 기본 사용법

#### 설치 및 설정
```bash
# npm으로 설치
npm install --save-dev tsc-alias

# yarn으로 설치
yarn add -D tsc-alias
```

#### tsconfig.json 설정
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@utils/*": ["utils/*"],
      "@components/*": ["components/*"],
      "@types/*": ["types/*"],
      "@services/*": ["services/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### 프로젝트 구조 예제
```plaintext
my-project/
├── tsconfig.json
├── src/
│   ├── utils/
│   │   ├── helper.ts
│   │   └── validator.ts
│   ├── components/
│   │   ├── Button.ts
│   │   └── Input.ts
│   ├── services/
│   │   └── api.ts
│   └── index.ts
├── dist/
└── package.json
```

### 2. 경로 별칭 사용 예제

#### 경로 별칭을 사용한 import
```typescript
// src/index.ts
import { sayHello } from '@utils/helper';
import { validateEmail } from '@utils/validator';
import { Button } from '@components/Button';
import { fetchData } from '@services/api';

console.log(sayHello('TypeScript'));
console.log(validateEmail('test@example.com'));
```

#### 컴파일 전후 비교
```typescript
// 컴파일 전 (TypeScript)
import { sayHello } from '@utils/helper';
import { Button } from '@components/Button';

// 컴파일 후 (JavaScript) - tsc-alias 적용 전
import { sayHello } from '@utils/helper';
import { Button } from '@components/Button';

// 컴파일 후 (JavaScript) - tsc-alias 적용 후
import { sayHello } from './utils/helper';
import { Button } from './components/Button';
```

### 3. tsc-alias 실행 방법

#### 기본 실행
```bash
# TypeScript 컴파일
npx tsc

# 경로 별칭 변환
npx tsc-alias
```

#### 통합 실행
```bash
# 컴파일과 별칭 변환을 한 번에 실행
npx tsc && npx tsc-alias
```

#### 고급 옵션
```bash
# 상세 출력과 함께 실행
npx tsc-alias --config ./tsconfig.json --verbose

# 특정 디렉토리만 처리
npx tsc-alias --outDir ./dist --project ./tsconfig.json

# 파일 확장자 지정
npx tsc-alias --extensions .js,.mjs
```

## 예시

### 1. 실제 사용 사례

#### 복잡한 프로젝트 구조
```plaintext
large-project/
├── tsconfig.json
├── src/
│   ├── core/
│   │   ├── types/
│   │   │   ├── user.ts
│   │   │   └── api.ts
│   │   ├── utils/
│   │   │   ├── validation.ts
│   │   │   └── formatting.ts
│   │   └── services/
│   │       ├── auth.ts
│   │       └── database.ts
│   ├── features/
│   │   ├── users/
│   │   │   ├── components/
│   │   │   ├── services/
│   │   │   └── types/
│   │   └── products/
│   │       ├── components/
│   │       ├── services/
│   │       └── types/
│   └── shared/
│       ├── constants/
│       ├── hooks/
│       └── components/
└── dist/
```

#### tsconfig.json 설정
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@core/*": ["core/*"],
      "@core/types/*": ["core/types/*"],
      "@core/utils/*": ["core/utils/*"],
      "@core/services/*": ["core/services/*"],
      "@features/*": ["features/*"],
      "@features/users/*": ["features/users/*"],
      "@features/products/*": ["features/products/*"],
      "@shared/*": ["shared/*"],
      "@shared/constants/*": ["shared/constants/*"],
      "@shared/hooks/*": ["shared/hooks/*"],
      "@shared/components/*": ["shared/components/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### 경로 별칭 사용 예제
```typescript
// src/features/users/components/UserList.ts
import { User } from '@core/types/user';
import { validateUser } from '@core/utils/validation';
import { formatName } from '@core/utils/formatting';
import { userService } from '@core/services/database';
import { Button } from '@shared/components/Button';
import { API_ENDPOINTS } from '@shared/constants/api';

export class UserList {
    private users: User[] = [];

    async loadUsers(): Promise<void> {
        try {
            const response = await fetch(API_ENDPOINTS.USERS);
            const data = await response.json();
            
            this.users = data.filter((user: any) => validateUser(user));
        } catch (error) {
            console.error('사용자 로딩 실패:', error);
        }
    }

    displayUsers(): void {
        this.users.forEach(user => {
            const formattedName = formatName(user.name);
            console.log(`사용자: ${formattedName}`);
        });
    }
}
```

### 2. 고급 패턴

#### package.json 스크립트 설정
```json
{
  "name": "my-typescript-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc && tsc-alias",
    "build:watch": "tsc --watch",
    "build:prod": "tsc && tsc-alias --verbose",
    "dev": "ts-node src/index.ts",
    "start": "node dist/index.js",
    "clean": "rimraf dist",
    "rebuild": "npm run clean && npm run build"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tsc-alias": "^1.8.0",
    "ts-node": "^10.9.0",
    "rimraf": "^5.0.0"
  }
}
```

#### CI/CD 파이프라인 통합
```yaml
# .github/workflows/build.yml
name: Build and Deploy

on:
  push:
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
    
    - name: Build with tsc-alias
      run: npm run build:prod
    
    - name: Upload build artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: dist/
```

#### 모노레포 설정
```json
// packages/app/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@app/*": ["*"],
      "@shared/*": ["../../packages/shared/src/*"],
      "@ui/*": ["../../packages/ui/src/*"]
    }
  },
  "include": ["src/**/*"],
  "references": [
    { "path": "../shared" },
    { "path": "../ui" }
  ]
}
```

## 운영 팁

### 성능 최적화

#### 빌드 최적화
```json
// tsconfig.json - 빌드 최적화
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    },
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

#### 캐싱 활용
```bash
# 캐시 디렉토리 설정
export TS_NODE_CACHE_DIRECTORY=./node_modules/.cache/ts-node

# 빌드 캐시 활용
npx tsc --incremental && npx tsc-alias
```

### 에러 처리

#### 경로 별칭 오류 해결
```bash
# 경로 별칭 확인
npx tsc-alias --check

# 상세 디버깅
npx tsc-alias --verbose --debug

# 특정 파일만 처리
npx tsc-alias --files src/index.ts
```

#### 일반적인 문제 해결
```typescript
// 문제: 경로 별칭이 제대로 변환되지 않음
// 해결: tsconfig.json의 paths 설정 확인

// 올바른 설정
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]  // 올바름
    }
  }
}

// 잘못된 설정
{
  "compilerOptions": {
    "baseUrl": "./",
    "paths": {
      "@/*": ["src/*"]  // 중복 경로
    }
  }
}
```

## 참고

### tsc-alias vs 다른 도구 비교표

| 도구 | 목적 | 장점 | 단점 |
|------|------|------|------|
| **tsc-alias** | 컴파일 후 경로 변환 | 간단한 설정, TypeScript 전용 | TypeScript 프로젝트만 지원 |
| **webpack** | 번들링 및 경로 해석 | 강력한 기능, 다양한 로더 | 복잡한 설정 |
| **rollup** | 번들링 | 트리 쉐이킹, 작은 번들 | 플러그인 의존성 |
| **vite** | 개발 서버 및 빌드 | 빠른 개발, 현대적 | 새로운 도구 |

### 경로 별칭 패턴

| 패턴 | 설명 | 예시 |
|------|------|------|
| `@/*` | 루트 디렉토리 | `@/utils/helper` |
| `@utils/*` | 특정 디렉토리 | `@utils/validation` |
| `@core/*` | 핵심 모듈 | `@core/types/user` |
| `@shared/*` | 공유 모듈 | `@shared/components/Button` |

### 결론
tsc-alias는 TypeScript 프로젝트에서 경로 별칭을 효과적으로 관리할 수 있게 해줍니다.
복잡한 상대 경로 대신 의미있는 별칭을 사용하여 코드 가독성을 향상시키세요.
적절한 tsconfig.json 설정으로 경로 별칭을 효율적으로 구성하세요.
빌드 프로세스에 tsc-alias를 통합하여 자동화된 경로 변환을 구현하세요.
성능 최적화 옵션을 활용하여 빌드 속도를 개선하세요.
경로 별칭 오류를 사전에 방지하기 위한 적절한 설정과 검증을 수행하세요.

