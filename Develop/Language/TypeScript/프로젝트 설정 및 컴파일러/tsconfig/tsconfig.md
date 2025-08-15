---
title: TypeScript tsconfig.json 설정 가이드
tags: [language, typescript, 프로젝트-설정-및-컴파일러, tsconfig, configuration]
updated: 2025-08-10
---

# TypeScript tsconfig.json 설정 가이드

## 배경

`tsconfig.json`은 TypeScript 프로젝트의 구성 파일로, TypeScript 컴파일러(`tsc`)가 코드를 어떻게 변환하고 검사할지를 정의하는 설정 파일입니다. 프로젝트의 타입 검사 규칙과 컴파일 옵션을 중앙에서 관리할 수 있게 해줍니다.

### tsconfig.json의 필요성
- **컴파일 옵션 설정**: 코드의 변환 방식 정의
- **타입 검사 설정**: 코드의 엄격성 설정
- **출력 경로 설정**: 컴파일 결과 파일 위치 정의
- **모듈 해석 설정**: 외부 모듈과의 경로 연결 설정

### 기본 개념
- **정적 타입 검사**: 컴파일 타임에 타입 오류 감지
- **JavaScript 변환**: TypeScript를 JavaScript로 변환
- **프로젝트 설정**: 일관된 개발 환경 구축

## 핵심

### 1. 프로젝트 초기화

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

### 2. 주요 컴파일러 옵션

#### 기본 컴파일 옵션
```json
{
  "compilerOptions": {
    "target": "ES2022",           // 컴파일 대상 JavaScript 버전
    "module": "CommonJS",         // 모듈 시스템
    "outDir": "./dist",           // 출력 디렉토리
    "rootDir": "./src",           // 소스 루트 디렉토리
    "strict": true,               // 엄격한 타입 검사
    "sourceMap": true,            // 소스맵 생성
    "declaration": true,          // 타입 선언 파일 생성
    "declarationMap": true        // 타입 선언 소스맵 생성
  }
}
```

#### 타입 검사 옵션
```json
{
  "compilerOptions": {
    "strict": true,                    // 모든 엄격한 타입 검사 활성화
    "noImplicitAny": true,            // 암시적 any 타입 금지
    "strictNullChecks": true,         // null/undefined 엄격 검사
    "strictFunctionTypes": true,      // 함수 타입 엄격 검사
    "strictBindCallApply": true,      // bind/call/apply 엄격 검사
    "strictPropertyInitialization": true, // 클래스 속성 초기화 검사
    "noImplicitThis": true,           // 암시적 this 타입 금지
    "useUnknownInCatchVariables": true // catch 변수를 unknown으로
  }
}
```

### 3. 파일 포함 및 제외 설정

#### include와 exclude
```json
{
  "include": [
    "src/**/*",           // src 폴더의 모든 TypeScript 파일
    "tests/**/*"          // tests 폴더의 모든 TypeScript 파일
  ],
  "exclude": [
    "node_modules",       // node_modules 제외
    "dist",               // 빌드 결과물 제외
    "**/*.test.ts",       // 테스트 파일 제외
    "**/*.spec.ts"        // 스펙 파일 제외
  ]
}
```

### 4. 모듈 해석 설정

#### 경로 매핑
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

#### 모듈 해석 옵션
```json
{
  "compilerOptions": {
    "moduleResolution": "node",
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true
  }
}
```

## 예시

### 1. 실제 사용 사례

#### Node.js 프로젝트 설정
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
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "sourceMap": true,
    "removeComments": false,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  },
  "include": [
    "src/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "**/*.test.ts",
    "**/*.spec.ts"
  ]
}
```

#### React 프로젝트 설정
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["DOM", "DOM.Iterable", "ES6"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "ESNext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": [
    "src"
  ]
}
```

#### 라이브러리 프로젝트 설정
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true
  },
  "include": [
    "src/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "**/*.test.ts",
    "**/*.spec.ts"
  ]
}
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

#### 개발/프로덕션 환경별 설정
```json
// tsconfig.dev.json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "sourceMap": true,
    "declaration": false,
    "removeComments": false
  }
}

// tsconfig.prod.json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "sourceMap": false,
    "declaration": true,
    "removeComments": true,
    "noEmitOnError": true
  }
}
```

## 운영 팁

### 성능 최적화

#### 빌드 성능 최적화
```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

#### 타입 검사 최적화
```json
{
  "compilerOptions": {
    "noEmit": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true
  }
}
```

### 에러 처리

#### 타입 오류 해결
```json
{
  "compilerOptions": {
    "noImplicitAny": false,        // 암시적 any 허용
    "strictNullChecks": false,     // null/undefined 엄격 검사 비활성화
    "noImplicitReturns": false,    // 암시적 반환 허용
    "suppressImplicitAnyIndexErrors": true  // 인덱스 오류 억제
  }
}
```

#### 일반적인 문제 해결
```json
{
  "compilerOptions": {
    "allowJs": true,               // JavaScript 파일 허용
    "checkJs": false,              // JavaScript 파일 타입 검사 비활성화
    "resolveJsonModule": true,     // JSON 모듈 해석 허용
    "esModuleInterop": true,       // ES 모듈 호환성
    "allowSyntheticDefaultImports": true  // 합성 기본 import 허용
  }
}
```

## 참고

### 주요 컴파일러 옵션 비교표

| 옵션 | 설명 | 기본값 | 권장값 |
|------|------|--------|--------|
| `target` | JavaScript 버전 | ES3 | ES2022 |
| `module` | 모듈 시스템 | CommonJS | CommonJS/ESNext |
| `strict` | 엄격 모드 | false | true |
| `sourceMap` | 소스맵 생성 | false | true |
| `declaration` | 선언 파일 생성 | false | true |

### 환경별 권장 설정

| 환경 | target | module | strict | sourceMap |
|------|--------|--------|--------|-----------|
| **Node.js** | ES2022 | CommonJS | true | true |
| **React** | ES2022 | ESNext | true | true |
| **라이브러리** | ES2022 | ESNext | true | true |
| **레거시** | ES5 | CommonJS | false | false |

### 결론
tsconfig.json은 TypeScript 프로젝트의 핵심 설정 파일입니다.
프로젝트 요구사항에 맞는 적절한 컴파일러 옵션을 설정하세요.
엄격한 타입 검사를 통해 코드 품질을 향상시키세요.
성능 최적화 옵션을 활용하여 빌드 속도를 개선하세요.
다중 설정 파일을 활용하여 다양한 환경에 대응하세요.
모듈 해석 설정으로 외부 라이브러리와의 호환성을 확보하세요.

