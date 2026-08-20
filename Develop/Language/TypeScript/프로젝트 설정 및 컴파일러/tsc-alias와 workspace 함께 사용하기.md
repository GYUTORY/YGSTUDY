---
title: TypeScript tsc-alias와 workspace 통합 사용법
tags: [language, typescript]
updated: 2025-08-10
---

# TypeScript tsc-alias와 workspace 통합 사용법

## 배경

`tsc-alias` 와 `workspace` 는 TypeScript 프로젝트에서 경로 매핑과 의존성 관리를 맡는 도구다. 특히 모노레포에서는 둘을 같이 써야 개발 환경이 굴러간다.

### tsc-alias와 workspace의 필요성
- **경로 매핑**: TypeScript 컴파일러의 경로 매핑 문제 해결
- **의존성 관리**: 멀티 패키지 환경의 의존성 해석
- **빌드 순서**: 복잡한 프로젝트에서 올바른 빌드 순서 보장
- **코드 가독성**: 절대 경로로 코드 가독성 향상

### 기본 개념
- **tsc-alias**: TypeScript 컴파일 후 경로 매핑 변환
- **workspace**: 패키지 매니저의 멀티 패키지 관리 시스템
- **통합 사용**: 두 도구를 함께 써서 개발 환경 구축

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

변환 전후는 실제로 이렇게 동작한다. 다만 **`@types/*` 별칭만은 여기까지 오지도 못한다.**

```typescript
import { User } from '@types/user';
// error TS6137: Cannot import type declaration files.
//              Consider importing 'user' instead of '@types/user'.
```

TypeScript 는 `@types/` 로 시작하는 import 를 **DefinitelyTyped 타입 선언 패키지**로 판정하고 값 import 를 거부한다. `paths` 에 뭘 적든 이 판정이 먼저라 매핑이 적용되지 않는다. `@types` 는 예약된 이름이므로 `@t/*` 나 `@models/*` 같은 다른 접두어를 쓴다.

그리고 `const User = require("./types/user")` 라는 변환 결과 자체가 성립하지 않는다. `User` 는 **인터페이스라 컴파일하면 완전히 사라진다.** 타입만 import 하는 구문은 산출물에 `require` 를 남기지 않는다.

```typescript
// 컴파일 전
import { User } from './types/user';
const u: User = { id: 1 };

// 컴파일 후 — import 문이 통째로 사라진다
const u = { id: 1 };
```

이걸 **import elision** 이라 한다. TypeScript 가 "이 import 에서 값으로 쓰이는 게 하나도 없다"고 판단하면 구문 전체를 지운다. 그래서 타입만 들어 있는 모듈은 `tsc-alias` 가 고칠 대상 자체가 없다. 반대로 부수 효과를 위해 import 한 모듈이 값으로 안 쓰이면 **의도치 않게 지워지는** 문제도 여기서 나온다 — 그때는 `import './polyfill'` 처럼 바인딩 없이 쓰거나 `verbatimModuleSyntax` 를 켠다.

#### 왜 이 도구가 따로 필요한가 — `tsc` 는 경로를 고치지 않는다

`paths` 는 **타입을 찾을 때만** 쓰인다. 컴파일러가 `@utils/date` 를 어느 파일로 읽을지 정하는 데는 쓰이지만, 산출물의 `require`/`import` 문자열은 손대지 않는다. 그래서 `tsc` 만 돌리면 검사는 전부 통과하고 실행만 죽는다. 위 설정을 그대로 만들어 확인한 결과다.

```
$ tsc --noEmit
오류 0건

$ tsc && grep require dist/index.js
const date_1 = require("@utils/date");     ← 별칭이 그대로 남는다

$ node dist/index.js
Error: Cannot find module '@utils/date'
  code: 'MODULE_NOT_FOUND'

$ tsc-alias -p tsconfig.json && grep require dist/index.js
const date_1 = require("./utils/date");    ← 여기서 고쳐진다

$ node dist/index.js
오늘: 2026-08-14
```

**타입 검사와 실행 가능성이 별개**라는 것이 요점이다. CI 가 `tsc --noEmit` 만 돌린다면 이 사고를 절대 못 잡는다. `type-check` 와 `build` 를 둘 다 돌리고, 빌드 산출물을 한 번 실행해 보는 스모크 테스트가 있어야 걸린다.

`tsc-alias` 를 안 쓰는 선택지도 있고, 각각 대가가 다르다.

| 방법 | 대가 |
|---|---|
| `tsc-alias` 로 빌드 후 재작성 | 빌드 단계가 하나 늘고, 문자열이 아닌 동적 `require` 는 못 고친다 |
| 런타임 해석기(`tsconfig-paths` 등) | 프로세스 시작 시 훅을 걸어야 하고, 번들러·워커·자식 프로세스마다 따로 챙겨야 한다 |
| 번들러(esbuild·swc·webpack)에 맡김 | 번들러가 `paths` 를 읽는지 별도 설정이 필요한지 확인해야 한다 |
| `paths` 를 안 쓰고 상대 경로만 | 아무 문제가 없다. `../../../` 이 길어지는 것만 감수한다 |
| `imports` 필드(`#utils/*`) | Node 가 직접 해석하므로 후처리가 필요 없다. 지원 범위를 확인해야 한다 |

**`paths` 는 편의를 위해 런타임 해석과 타입 해석을 갈라 놓는 설정**이고, 여기 나오는 문제 대부분이 그 틈에서 나온다. 별칭이 정말 필요한지 먼저 따져 보는 편이 낫다.

> `baseUrl` 은 TypeScript 7 에서 제거됐다. 5.9 에서는 위 설정이 그대로 동작하지만 7.0 에서는 이렇게 막힌다.
>
> ```
> error TS5102: Option 'baseUrl' has been removed. Please remove it from your configuration.
>   Use '"paths": {"*": ["./src/*"]}' instead.
> ```
>
> 대체 방법은 `paths` 값을 `baseUrl` 기준 상대 경로가 아니라 **`tsconfig.json` 위치 기준 상대 경로**로 적는 것이다(`"./src/*"` 처럼 `./` 로 시작해야 한다). 뒤에 나오는 `../../` 개수 문제도 이 규칙이 바뀌면서 함께 달라지므로, 올릴 때 `paths` 를 전부 다시 계산해야 한다.

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

위 `apps/web/tsconfig.json` 은 그대로 쓰면 컴파일되지 않는다. 같은 구조를 만들어 확인한 결과 두 단계로 막힌다.

**첫째, `../../` 의 깊이가 모자라다.** `baseUrl` 이 `./src` 이므로 상대 경로 기준점은 패키지 루트가 아니라 `apps/web/src` 다. 두 단계 올라가면 `apps/` 이고 거기엔 `packages/` 가 없다.

```
error TS2307: Cannot find module '@shared/index' or its corresponding type declarations.
```

`../../../` 이어야 한다. **`baseUrl` 을 `./src` 로 두느냐 `./` 로 두느냐에 따라 필요한 `../` 개수가 달라진다** — `paths` 를 다른 패키지에서 복사할 때 가장 자주 어긋나는 지점이다.

**둘째, 깊이를 고치면 `rootDir` 이 막는다.**

```
error TS6059: File '.../packages/shared/src/index.ts' is not under 'rootDir' '.../apps/web/src'.
```

`paths` 가 다른 패키지의 **소스 파일**을 직접 가리키므로 `tsc` 가 그 파일까지 컴파일 대상으로 끌어들이는데, `rootDir` 밖이라 출력 위치를 정할 수 없다.

여기서 `rootDir` 을 지우는 것이 흔한 대응이고, **그게 배포를 깨뜨린다.** `rootDir` 이 없으면 `tsc` 가 포함된 모든 파일의 공통 조상을 계산해 출력 트리가 그만큼 깊어진다.

```
rootDir 있을 때 : dist/index.js
rootDir 지웠을 때: dist/apps/web/src/index.js
                   dist/packages/shared/src/index.js
```

`package.json` 의 `main` 이 `dist/index.js` 를 가리키면 **빌드는 통과하고 실행만 `MODULE_NOT_FOUND` 로 죽는다.** `tsc --noEmit` 은 파일을 내보내지 않으므로 이걸 잡지 못한다. 빌드 뒤 `find dist -name '*.js'` 로 실제 위치를 확인해야 한다.

**근본 원인은 같은 의존성을 두 방식으로 선언한 것**이다. 아래 `package.json` 은 `"@my-monorepo/shared": "workspace:*"` 로 패키지 의존성을 선언하는데, `tsconfig.json` 의 `paths` 는 그 패키지의 소스를 직접 가리킨다. 둘 중 하나만 써야 한다.

- **`paths` 로 소스 직접 참조** — 빌드 없이 즉시 반영돼 개발이 빠르지만, 위 `rootDir` 문제가 따라오고 패키지 경계가 사라진다. 소비하는 쪽이 공유 패키지 전체를 매번 다시 컴파일한다.
- **패키지 이름으로 import** — `import { User } from '@my-monorepo/shared'`. `node_modules` 심볼릭 링크를 통해 **빌드된 `dist` 와 `.d.ts`** 를 참조하므로 `rootDir` 을 지킬 수 있고 경계도 유지된다. 대신 공유 패키지를 먼저 빌드해야 한다.

모노레포에서는 **후자가 기본**이고, 빌드 순서는 아래 "빌드 순서 최적화"처럼 수동으로 맞추는 대신 프로젝트 참조(`references`)나 turborepo·nx 같은 도구에 맡긴다.

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

첫 import 줄이 이 문서의 앞선 파일 구조와 맞지 않는다.

```typescript
import { User, validateUser, API_ENDPOINTS } from '@shared/types/user';
```

세 심볼이 **서로 다른 파일에 정의돼 있다.** 위 "공유 패키지 구현" 절을 보면 이렇다.

| 심볼 | 실제 위치 |
|---|---|
| `User` | `packages/shared/src/types/user.ts` |
| `validateUser` | `packages/shared/src/utils/validation.ts` |
| `API_ENDPOINTS` | `packages/shared/src/constants/api.ts` |

`@shared/types/user` 하나에서 셋을 다 가져올 수 없다. 세 줄로 나누거나, 공유 패키지에 배럴 파일(`packages/shared/src/index.ts`)을 두고 거기서 재수출한 뒤 패키지 이름으로 한 번에 가져오는 편이 낫다.

```typescript
// packages/shared/src/index.ts
export * from './types/user';
export * from './utils/validation';
export * from './constants/api';
```

```typescript
import { User, validateUser, API_ENDPOINTS } from '@my-monorepo/shared';
```

배럴 파일에는 대가가 있다. **하나만 import 해도 배럴이 재수출하는 모듈 전체가 로드된다.** 번들러의 트리 셰이킹이 걷어내 주기를 기대하지만, 부수 효과가 있는 모듈이 섞여 있으면 걷어내지 못한다. 서버 사이드 코드에서는 시작 시간이, 프런트에서는 번들 크기가 늘어난다. 공개 API 경계에만 두고 패키지 내부에서는 직접 경로로 import 하는 것이 절충안이다.

`data.filter(validateUser)` 는 잘 쓴 부분이다. `validateUser` 가 `user is User` 술어라서 `filter` 결과가 `any[]` 가 아니라 `User[]` 로 좁혀진다. 다만 그 술어 본문이 `createdAt` 을 검사하지 않으므로 **`User` 라고 선언해 놓고 `createdAt` 이 없는 객체가 통과한다.** 술어는 컴파일러가 내용을 검증해 주지 않는다는 점을 여기서도 기억해야 한다.

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

이 세 줄 중 `skipLibCheck` 는 캐싱 옵션이 아니다. **`.d.ts` 안의 타입 오류를 통째로 안 보는 설정**이다. 빌드가 빨라지는 것은 부수 효과이고, 그 대가로 손으로 쓴 정의의 오류까지 함께 숨는다.

```
skipLibCheck 끔 → error TS2304: Cannot find name 'NonExistentType'
skipLibCheck 켬 → 오류 0건
```

원래 용도는 남의 `@types` 패키지끼리 충돌해서 빌드가 막힐 때 뚫는 것이다. 모노레포에서는 켜 둘 이유가 하나 더 있다 — 패키지마다 다른 버전의 `@types/node` 가 딸려 오면 그것만으로 빌드가 멈춘다. 다만 **그 상태를 해결한 것이 아니라 가린 것**이라는 점은 알고 있어야 하고, 자기 `.d.ts` 를 직접 쓰는 프로젝트라면 그 파일들만은 다른 방법으로 검사받아야 한다.

`incremental` 과 `tsBuildInfoFile` 도 조건이 붙는다. `--noEmit` 과 함께 쓰면 버전에 따라 캐시가 안 만들어지거나 옵션 충돌이 나므로, `type-check` 스크립트와 `build` 스크립트가 같은 `tsconfig` 를 공유한다면 확인해 봐야 한다. 캐시 파일을 `node_modules/.cache` 에 두는 것도 의도를 알고 써야 한다 — `pnpm install` 이 `node_modules` 를 갈아엎으면 캐시가 사라진다. CI 에서 캐시를 살리려면 그 경로가 캐시 대상에 들어 있어야 한다.

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
```jsonc
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

세 패턴 모두 **개발 중에는 똑같이 동작한다** — 로컬 패키지에 심볼릭 링크를 건다. 차이는 `pnpm publish` 할 때 드러난다. 발행 시점에 `workspace:` 접두어가 실제 버전으로 치환되는데, `*` 는 고정 버전으로, `^` 와 `~` 는 각각 캐럿·틸드 범위로 바뀐다([pnpm workspace 문서](https://pnpm.io/workspaces)). 사내에서만 쓰는 비공개 모노레포라면 셋 중 무엇을 써도 차이가 없고, npm 에 발행하는 패키지라면 소비자가 받을 버전 범위를 정하는 설정이 된다.

`workspace:` 를 쓰라는 권고에도 이유가 있다. 아래처럼 버전 범위로 적으면 그 범위를 만족하는 패키지가 로컬에 있을 때만 링크되고, 없으면 **레지스트리에서 남의 패키지를 받아 온다.** 이름이 겹치면 조용히 엉뚱한 코드가 들어오는 것이다. `workspace:` 접두어는 "로컬에 없으면 설치를 실패시켜라"라는 뜻이라 그 사고가 안 난다.

### 결론
tsc-alias 와 workspace 를 같이 쓰면 모노레포 개발이 수월해진다.
경로 매핑을 제대로 잡아 두면 패키지 간 의존성이 분명해진다.
빌드 순서를 맞춰 두면 의존성 문제를 미리 막는다.
CI/CD 파이프라인에 넣으면 빌드가 자동으로 돈다.
성능 최적화 옵션을 켜면 개발과 빌드 속도가 올라간다.
워크스페이스 패턴을 알아야 의존성을 제대로 관리한다.

