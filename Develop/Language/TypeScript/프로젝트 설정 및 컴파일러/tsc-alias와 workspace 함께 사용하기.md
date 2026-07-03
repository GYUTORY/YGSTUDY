---
title: TypeScript tsc-alias와 workspace 통합 사용법
tags: [language, typescript, 프로젝트-설정-및-컴파일러, tsc-alias, workspace, monorepo]
updated: 2025-08-10
---

# TypeScript tsc-alias와 workspace 통합 사용법

## 배경

`tsc-alias`와 `workspace`는 TypeScript 프로젝트에서 경로 매핑과 의존성 관리를 다루기 위한 도구입니다. 특히 모노레포 환경에서 두 도구를 함께 사용하면 효율적인 개발 환경을 구축할 수 있습니다.

### tsc-alias와 workspace의 필요성
- **경로 매핑**: TypeScript 컴파일러의 경로 매핑 문제 해결
- **의존성 관리**: 멀티 패키지 환경에서의 의존성 해석
- **빌드 순서**: 복잡한 프로젝트에서의 올바른 빌드 순서 보장
- **코드 가독성**: 절대 경로를 통한 코드 가독성 향상

### 기본 개념
- **tsc-alias**: TypeScript 컴파일 후 경로 매핑 변환
- **workspace**: 패키지 매니저의 멀티 패키지 관리 시스템
- **통합 사용**: 두 도구를 함께 사용하여 최적의 개발 환경 구축

## 핵심

### 1. tsc-alias 기본 사용법

#### 설치 및 설정
```bash
npm install --save-dev tsc-alias
```

#### tsconfig.json 설정
```json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@components/*": ["components/*"],
      "@utils/*": ["utils/*"],
      "@types/*": ["types/*"]
    }
  }
}
```

#### 사용 예시
```typescript
// src/index.ts
import { Button } from '@components/Button';
import { formatDate } from '@utils/date';
import { User } from '@types/user';

console.log('Hello, TypeScript!');
```

#### 컴파일 및 경로 변환
```bash
# TypeScript 컴파일
npx tsc

# 경로 매핑 변환
npx tsc-alias
```

#### 변환 결과
```javascript
// dist/index.js (변환 전)
const Button = require("@components/Button");
const formatDate = require("@utils/date");
const User = require("@types/user");

// dist/index.js (변환 후)
const Button = require("./components/Button");
const formatDate = require("./utils/date");
const User = require("./types/user");
```

### 2. workspace 기본 사용법

#### pnpm workspace 설정
```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
  - 'apps/*'
```

#### package.json 설정
```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

#### 프로젝트 구조
```plaintext
my-monorepo/
├── package.json
├── pnpm-workspace.yaml
├── packages/
│   ├── shared/
│   │   ├── package.json
│   │   └── src/
│   │       ├── types/
│   │       │   ├── user.ts
│   │       │   └── product.ts
│   │       ├── utils/
│   │       │   ├── validation.ts
│   │       │   └── formatting.ts
│   │       └── constants/
│   │           └── api.ts
│   ├── ui/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── components/
│   │       │   ├── Button.tsx
│   │       │   └── Input.tsx
│   │       └── hooks/
│   │           └── useLocalStorage.ts
│   └── api-client/
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── client.ts
│           └── endpoints.ts
└── apps/
    ├── web/
    │   ├── package.json
    │   ├── tsconfig.json
    │   └── src/
    │       ├── pages/
    │       ├── components/
    │       └── index.ts
    └── admin/
        ├── package.json
        ├── tsconfig.json
        └── src/
            ├── pages/
            ├── components/
            └── index.ts
```

### 3. tsc-alias와 workspace 통합

#### 패키지별 tsconfig.json 설정
```json
// packages/shared/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

```json
// apps/web/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@shared/*": ["../../packages/shared/src/*"],
      "@ui/*": ["../../packages/ui/src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### 패키지 간 의존성 설정
```json
// apps/web/package.json
{
  "name": "@my-monorepo/web",
  "version": "1.0.0",
  "dependencies": {
    "@my-monorepo/shared": "workspace:*",
    "@my-monorepo/ui": "workspace:*"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tsc-alias": "^1.8.0"
  },
  "scripts": {
    "build": "tsc && tsc-alias",
    "dev": "ts-node src/index.ts"
  }
}
```

## 예시

### 1. 실제 사용 사례

#### 모노레포 구조 예제
```plaintext
ecommerce-monorepo/
├── package.json
├── pnpm-workspace.yaml
├── packages/
│   ├── shared/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── types/
│   │       │   ├── user.ts
│   │       │   └── product.ts
│   │       ├── utils/
│   │       │   ├── validation.ts
│   │       │   └── formatting.ts
│   │       └── constants/
│   │           └── api.ts
│   ├── ui/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── components/
│   │       │   ├── Button.tsx
│   │       │   └── Input.tsx
│   │       └── hooks/
│   │           └── useLocalStorage.ts
│   └── api-client/
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── client.ts
│           └── endpoints.ts
└── apps/
    ├── web/
    │   ├── package.json
    │   ├── tsconfig.json
    │   └── src/
    │       ├── pages/
    │       ├── components/
    │       └── index.ts
    └── admin/
        ├── package.json
        ├── tsconfig.json
        └── src/
            ├── pages/
            ├── components/
            └── index.ts
```

#### 공유 패키지 구현
```typescript
// packages/shared/src/types/user.ts
export interface User {
    id: number;
    name: string;
    email: string;
    role: 'admin' | 'user';
    createdAt: Date;
}

export interface CreateUserRequest {
    name: string;
    email: string;
    role?: 'admin' | 'user';
}

// packages/shared/src/utils/validation.ts
export function validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

export function validateUser(user: any): user is User {
    return (
        typeof user === 'object' &&
        typeof user.id === 'number' &&
        typeof user.name === 'string' &&
        validateEmail(user.email) &&
        ['admin', 'user'].includes(user.role)
    );
}

// packages/shared/src/constants/api.ts
export const API_ENDPOINTS = {
    USERS: '/api/users',
    PRODUCTS: '/api/products',
    ORDERS: '/api/orders'
} as const;
```

#### UI 패키지 구현
```typescript
// packages/ui/src/components/Button.tsx
import React from 'react';

export interface ButtonProps {
    children: React.ReactNode;
    onClick?: () => void;
    variant?: 'primary' | 'secondary';
    disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
    children,
    onClick,
    variant = 'primary',
    disabled = false
}) => {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`btn btn-${variant}`}
        >
            {children}
        </button>
    );
};

// packages/ui/src/hooks/useLocalStorage.ts
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
    const [storedValue, setStoredValue] = useState<T>(() => {
        try {
            const item = window.localStorage.getItem(key);
            return item ? JSON.parse(item) : initialValue;
        } catch (error) {
            console.error(`Error reading localStorage key "${key}":`, error);
            return initialValue;
        }
    });

    const setValue = (value: T | ((val: T) => T)) => {
        try {
            const valueToStore = value instanceof Function ? value(storedValue) : value;
            setStoredValue(valueToStore);
            window.localStorage.setItem(key, JSON.stringify(valueToStore));
        } catch (error) {
            console.error(`Error setting localStorage key "${key}":`, error);
        }
    };

    return [storedValue, setValue] as const;
}
```

#### 웹 앱에서 패키지 사용
```typescript
// apps/web/src/pages/UserList.tsx
import React, { useState, useEffect } from 'react';
import { User, validateUser, API_ENDPOINTS } from '@shared/types/user';
import { Button } from '@ui/components/Button';
import { useLocalStorage } from '@ui/hooks/useLocalStorage';

export const UserList: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [theme, setTheme] = useLocalStorage('theme', 'light');

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const response = await fetch(API_ENDPOINTS.USERS);
            const data = await response.json();
            
            const validUsers = data.filter(validateUser);
            setUsers(validUsers);
        } catch (error) {
            console.error('사용자 로딩 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleThemeToggle = () => {
        setTheme(theme === 'light' ? 'dark' : 'light');
    };

    if (loading) {
        return <div>로딩 중...</div>;
    }

    return (
        <div className={`app ${theme}`}>
            <Button onClick={handleThemeToggle}>
                테마 변경 ({theme})
            </Button>
            <div className="user-list">
                {users.map(user => (
                    <div key={user.id} className="user-item">
                        <h3>{user.name}</h3>
                        <p>{user.email}</p>
                        <span className={`role role-${user.role}`}>
                            {user.role}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};
```

### 2. 고급 패턴

#### 빌드 스크립트 통합
```json
// 루트 package.json
{
  "name": "ecommerce-monorepo",
  "private": true,
  "workspaces": [
    "packages/*",
    "apps/*"
  ],
  "scripts": {
    "build": "pnpm -r build",
    "build:shared": "pnpm --filter @my-monorepo/shared build",
    "build:ui": "pnpm --filter @my-monorepo/ui build",
    "build:web": "pnpm --filter @my-monorepo/web build",
    "dev": "pnpm --parallel -r dev",
    "clean": "pnpm -r clean",
    "type-check": "pnpm -r type-check"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tsc-alias": "^1.8.0"
  }
}
```

#### CI/CD 파이프라인 설정
```yaml
# .github/workflows/build.yml
name: Build Monorepo

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
    
    - name: Setup pnpm
      uses: pnpm/action-setup@v2
      with:
        version: 8
    
    - name: Install dependencies
      run: pnpm install --frozen-lockfile
    
    - name: Type check
      run: pnpm type-check
    
    - name: Build packages
      run: pnpm build:shared && pnpm build:ui
    
    - name: Build apps
      run: pnpm build:web
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: |
          packages/*/dist/
          apps/*/dist/
```

#### 개발 환경 최적화
```json
// apps/web/package.json - 개발 스크립트
{
  "scripts": {
    "dev": "ts-node-dev --respawn --transpile-only src/index.ts",
    "build": "tsc && tsc-alias",
    "build:watch": "tsc --watch",
    "start": "node dist/index.js",
    "clean": "rimraf dist",
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "ts-node-dev": "^2.0.0",
    "rimraf": "^5.0.0"
  }
}
```

## 운영 팁

### 성능 최적화

#### 빌드 순서 최적화
```bash
# 의존성 순서대로 빌드
pnpm build:shared  # 공유 패키지 먼저
pnpm build:ui      # UI 패키지
pnpm build:web     # 웹 앱
```

#### 캐싱 활용
```json
// tsconfig.json - 빌드 최적화
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo",
    "skipLibCheck": true
  }
}
```

### 에러 처리

#### 경로 매핑 오류 해결
```bash
# 경로 매핑 확인
npx tsc-alias --check

# 상세 디버깅
npx tsc-alias --verbose --debug

# 워크스페이스 의존성 확인
pnpm list --depth=0
```

#### 일반적인 문제 해결
```typescript
// 문제: 워크스페이스 패키지 import 오류
// 해결: package.json의 dependencies 확인

// 올바른 설정
{
  "dependencies": {
    "@my-monorepo/shared": "workspace:*"
  }
}

// 잘못된 설정
{
  "dependencies": {
    "@my-monorepo/shared": "^1.0.0"  // 버전 지정
  }
}
```

## 참고

### tsc-alias vs workspace 비교표

| 구분 | tsc-alias | workspace |
|------|-----------|-----------|
| **목적** | 경로 매핑 변환 | 패키지 관리 |
| **사용 시점** | 빌드 후 | 개발/빌드 전체 |
| **범위** | 단일 프로젝트 | 멀티 패키지 |
| **설정** | tsconfig.json | package.json |

### 워크스페이스 패턴

| 패턴 | 설명 | 예시 |
|------|------|------|
| `workspace:*` | 워크스페이스 내 패키지 | `@my-monorepo/shared` |
| `workspace:^` | 워크스페이스 내 패키지 (호환성) | `@my-monorepo/ui` |
| `workspace:~` | 워크스페이스 내 패키지 (패치) | `@my-monorepo/api` |

### 결론
tsc-alias와 workspace를 함께 사용하면 모노레포 환경에서 효율적인 개발이 가능합니다.
적절한 경로 매핑 설정으로 패키지 간 의존성을 명확하게 관리하세요.
빌드 순서를 최적화하여 의존성 문제를 방지하세요.
CI/CD 파이프라인에 통합하여 자동화된 빌드 프로세스를 구축하세요.
성능 최적화 옵션을 활용하여 개발 및 빌드 속도를 개선하세요.
워크스페이스 패턴을 이해하여 올바른 의존성 관리를 수행하세요.

