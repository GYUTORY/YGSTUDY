---
title: TypeScript tsc-alias
tags: [language, typescript]
updated: 2025-12-16
---

# TypeScript tsc-alias
## 배경

`tsc-alias` 는 TypeScript 의 `paths` 와 `baseUrl` 을 쓰는 프로젝트에서 경로 별칭(Path Alias)을 컴파일이 끝난 뒤 자동으로 바꿔 주는 도구다.

### tsc-alias 가 필요한 이유
- **경로 별칭 변환**: TypeScript 컴파일이 끝난 뒤 별칭을 상대 경로로 바꾼다
- **런타임 호환성**: JavaScript 실행 환경에서 생기는 경로 별칭 문제를 해결한다
- **개발 편의성**: 복잡한 상대 경로 대신 의미가 드러나는 별칭을 쓴다
- **유지보수성**: 파일 구조를 바꿔도 경로 수정이 적다

### 기본 개념
- **경로 별칭**: 복잡한 상대 경로를 짧은 별칭으로 대신 쓴다
- **컴파일 후 처리**: TypeScript 컴파일이 끝난 뒤에 경로를 바꾼다
- **tsconfig.json 연동**: TypeScript 설정 파일의 paths 설정을 그대로 쓴다
- **자동 변환**: 손으로 경로를 고치지 않아도 상대 경로로 바뀐다

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

이 도구가 왜 필요한지는 **직접 돌려 보면 한 번에 이해된다.** 위 tsconfig 로 `tsc` 만 실행한 결과와 실행 결과다.

```javascript
// dist/index.js — tsc 만 실행
const helper_1 = require("@utils/helper");
```

```
$ node dist/index.js
Error: Cannot find module '@utils/helper'
```

```javascript
// dist/index.js — tsc-alias 실행 후
const helper_1 = require("./utils/helper");
```

```
$ node dist/index.js
Hello TypeScript
```

**컴파일은 성공하는데 실행이 안 된다**는 게 핵심이다. `paths` 는 타입 검사기에게 "이 별칭이 어느 파일인지" 알려 줄 뿐이고, **`tsc` 는 import 문자열을 다시 쓰지 않는다.** 타입 검사와 모듈 해석이 분리돼 있어서 생기는 간극이라, 별도 도구 없이는 메워지지 않는다.

그래서 `paths` 를 쓰는 순간 **런타임 쪽에도 같은 매핑을 알려 줄 장치가 반드시 필요해진다.** 선택지는 셋이다.

- **번들러를 쓴다** — webpack·vite·esbuild 는 자체 alias 설정으로 해결한다. 번들링하는 프로젝트라면 `tsc-alias` 가 필요 없다.
- **런타임 해석기를 쓴다** — `tsconfig-paths` 를 `node -r tsconfig-paths/register` 로 물린다. 실행 시점에 해석하므로 산출물은 별칭 그대로 남는다.
- **컴파일 후 산출물을 고친다** — `tsc-alias` 가 이쪽이다. 산출물이 순수 상대 경로가 되므로 실행할 때 추가 의존성이 없다. **라이브러리를 배포할 때는 이 방식이어야 한다.** 소비자에게 `tsconfig-paths` 를 깔라고 요구할 수 없기 때문이다.

위 "컴파일 후" 예시가 `import` 구문인 점은 짚어 둘 만하다. tsconfig 가 `"module": "CommonJS"` 이므로 실제 산출물은 `require(...)` 다. `import` 형태로 남으려면 `"module"` 이 `ESNext`·`ES2020` 계열이어야 한다.

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

**위 세 줄 중 실제로 있는 옵션은 `--verbose` 와 `--outDir` · `--project` 뿐이다.** tsc-alias 1.8.10 에서 나머지는 전부 거부된다.

```
$ npx tsc-alias --config ./tsconfig.json
error: unknown option '--config'

$ npx tsc-alias --extensions .js,.mjs
error: unknown option '--extensions'
```

실제 옵션 목록은 이렇다(`tsc-alias --help`).

| 문서에 적힌 것 | 실제 |
|---|---|
| `--config <file>` | `-p, --project <file>` |
| `--extensions .js,.mjs` | `--outputcheck <extensions...>` |
| `--check` | 없음 |
| `--files <path>` | `--inputglob <glob>` |
| `--verbose` · `--debug` · `--outDir` · `--project` | 그대로 있음 |

이 밖에 `-w, --watch`(변경 감시), `-f, --resolve-full-paths`(확장자까지 붙여 완전 경로로 해석), `-r, --replacer`(사용자 정의 치환기)가 있다. `--resolve-full-paths` 는 **ESM 산출물에서 특히 중요하다.** Node 의 ESM 로더는 확장자 생략을 허용하지 않으므로 `./utils/helper` 로는 실행되지 않고 `./utils/helper.js` 여야 한다.

옵션 이름은 버전에 따라 달라지니 **`--help` 로 확인하는 습관이 문서를 믿는 것보다 안전하다.**

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

**이 모노레포 설정은 그대로 쓰면 컴파일되지 않는다.** 같은 구조를 만들어 돌려 보면 두 단계로 막힌다.

첫째, **`../../` 의 깊이가 모자란다.** `baseUrl` 이 `./src` 이므로 상대 경로의 기준점은 패키지 루트가 아니라 `src` 안이다. `apps/web/src` 에서 두 단계만 올라가면 `apps/` 이고, 거기에는 `packages/` 가 없다.

```
error TS2307: Cannot find module '@shared/index' or its corresponding type declarations.
```

`../../../` 로 한 단계 더 올라가야 한다. **`baseUrl` 이 `src` 인지 패키지 루트인지에 따라 필요한 `../` 개수가 달라진다** — `paths` 를 복사해 쓸 때 가장 자주 어긋나는 지점이다.

둘째, 깊이를 고쳐도 다음 에러가 기다린다.

```
error TS6059: File '.../packages/shared/src/index.ts' is not under 'rootDir' '.../apps/web/src'.
             'rootDir' is expected to contain all source files.
```

`paths` 로 **다른 패키지의 소스 파일을 직접 가리켰기 때문**이다. `tsc` 는 그 파일도 컴파일 대상으로 끌어들이는데 `rootDir` 밖이라 출력 위치를 정할 수 없다.

여기서 `rootDir` 을 지우는 것이 흔한 "해결책"인데, **이게 배포를 깨뜨린다.** `rootDir` 이 없으면 `tsc` 가 포함된 모든 파일의 공통 조상을 스스로 계산하고, 그만큼 출력 트리가 깊어진다.

```
rootDir 있을 때 : dist/index.js
rootDir 지웠을 때: dist/apps/web/src/index.js
                   dist/packages/shared/src/index.js
```

`package.json` 의 `main` 이 `dist/index.js` 를 가리키고 있으면 **빌드는 성공하고 실행만 `MODULE_NOT_FOUND` 로 죽는다.** `tsc --noEmit` 으로는 절대 안 잡힌다 — 파일을 내보내지 않으니 트리가 어떻게 생겼는지 알 수 없기 때문이다. 빌드 후 `find dist -name '*.js'` 로 실제 산출물 위치를 확인해야 한다.

제대로 된 해법은 **다른 패키지의 소스를 `paths` 로 가리키지 않는 것**이다. 위 설정에 이미 `references` 가 있으니 프로젝트 참조를 쓰면 된다. 각 패키지를 독립적으로 빌드하고, 소비하는 쪽은 `paths` 대신 패키지 이름(`@my-monorepo/shared`)으로 import 해서 `node_modules` 심볼릭 링크를 통해 **빌드된 `dist` 와 `.d.ts`** 를 참조한다. 그러면 `rootDir` 도 지킬 수 있고 패키지 경계도 유지된다.

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
```jsonc
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

**"잘못된 설정"으로 표시된 쪽은 잘못되지 않았다.** 실제로 만들어 컴파일하고 실행해 보면 위쪽과 똑같이 동작한다.

```
$ tsc -p tsconfig.alt.json && tsc-alias -p tsconfig.alt.json
$ cat dist2/index.js
const helper_1 = require("./utils/helper");
$ node dist2/index.js
Hello TypeScript
```

`baseUrl` 은 `paths` 의 기준점을 정할 뿐이다. `baseUrl: "./"` + `["src/*"]` 와 `baseUrl: "./src"` + `["*"]` 는 **같은 위치를 가리키는 두 가지 표기**이고 중복이 아니다. 오히려 전자가 널리 쓰인다 — `tsconfig.json` 이 프로젝트 루트에 있으니 기준점이 루트인 편이 읽기 쉽고, `src` 밖의 디렉터리(`tests/`·`scripts/`)에도 별칭을 붙일 수 있기 때문이다.

진짜 "잘못된 설정"은 다른 데 있다. **이 문서 맨 앞 tsconfig 의 `"@types/*": ["types/*"]` 는 절대 동작하지 않는다.**

```typescript
import { User } from '@types/user';
// error TS6137: Cannot import type declaration files.
//              Consider importing 'user' instead of '@types/user'.
```

TypeScript 는 `@types/` 로 시작하는 import 를 **DefinitelyTyped 타입 선언 패키지**로 간주하고 값 import 를 거부한다. `paths` 로 뭘 매핑하든 이 판정이 먼저다. `@types` 는 예약된 이름이라 별칭으로 쓸 수 없으니 `@t/*` 나 `@models/*` 처럼 다른 접두어를 쓴다.

별칭을 정할 때 피해야 할 이름을 정리하면 이렇다.

- **`@types/*`** — 위 이유로 사용 불가
- **`@` 로 시작하되 실제 npm 스코프와 겹치는 이름** — `@babel/*`·`@aws-sdk/*` 등. 별칭이 이기면 진짜 패키지를 못 찾고, 반대면 별칭이 안 먹는다
- **`node_modules` 의 패키지 이름과 같은 접두어 없는 별칭** — `utils/*` 처럼 `@` 를 뗀 형태는 실제 `utils` 패키지와 충돌한다

`@` 접두어를 붙이되 **널리 쓰이는 스코프가 아닌 이름**을 고르는 것이 안전하다.

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
tsc-alias 를 쓰면 TypeScript 프로젝트의 경로 별칭을 효과적으로 관리할 수 있다.
복잡한 상대 경로 대신 의미가 드러나는 별칭을 쓰면 코드가 읽기 쉬워진다.
tsconfig.json 을 제대로 잡아 두면 경로 별칭 구성이 깔끔해진다.
빌드 과정에 tsc-alias 를 끼워 넣으면 경로 변환이 자동으로 돌아간다.
성능 최적화 옵션으로 빌드 속도를 끌어올린다.
경로 별칭 오류는 적절한 설정과 검증으로 미리 막는다.

