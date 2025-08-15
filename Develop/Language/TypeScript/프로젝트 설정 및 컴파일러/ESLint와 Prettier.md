---
title: TypeScript ESLint와 Prettier 설정 가이드
tags: [language, typescript, 프로젝트-설정-및-컴파일러, eslint, prettier, code-quality]
updated: 2025-08-10
---

# TypeScript ESLint와 Prettier 설정 가이드

## 배경

TypeScript 프로젝트에서는 코드 품질 유지와 일관성 확보를 위해 ESLint와 Prettier를 함께 사용하는 것이 일반적입니다. 두 도구를 적절히 설정하면 개발 팀의 코드 품질과 생산성을 크게 향상시킬 수 있습니다.

### ESLint와 Prettier의 필요성
- **코드 품질**: 잠재적 버그와 오류 사전 방지
- **일관성**: 팀 전체의 일관된 코드 스타일 유지
- **가독성**: 자동 포맷팅으로 코드 가독성 향상
- **개발 효율성**: 자동 수정 기능으로 개발 시간 단축

### 기본 개념
- **ESLint**: 코드 품질 검사 및 스타일 규칙 적용
- **Prettier**: 코드 포맷팅 도구
- **통합**: 두 도구를 함께 사용하여 최적의 개발 환경 구축

## 핵심

### 1. 패키지 설치

#### 필수 패키지 설치
```bash
npm install --save-dev eslint prettier
npm install --save-dev @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install --save-dev eslint-config-prettier eslint-plugin-prettier
npm install --save-dev eslint-config-airbnb-typescript
```

#### 패키지 설명
- `eslint`: ESLint 핵심 패키지
- `prettier`: 코드 포맷팅 도구
- `@typescript-eslint/parser`: TypeScript를 위한 ESLint 파서
- `@typescript-eslint/eslint-plugin`: TypeScript용 ESLint 규칙
- `eslint-config-prettier`: Prettier와 ESLint 간 충돌 방지
- `eslint-plugin-prettier`: Prettier를 ESLint에 통합
- `eslint-config-airbnb-typescript`: Airbnb의 TypeScript 스타일 가이드

### 2. ESLint 설정

#### 기본 .eslintrc.json
```json
{
  "env": {
    "browser": true,
    "es2022": true,
    "node": true
  },
  "extends": [
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "plugin:prettier/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module",
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint",
    "prettier"
  ],
  "rules": {
    "prettier/prettier": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/explicit-module-boundary-types": "off"
  }
}
```

#### Airbnb 스타일 가이드 적용
```json
{
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
    "@typescript-eslint/no-explicit-any": "warn",
    "import/prefer-default-export": "off",
    "class-methods-use-this": "off",
    "no-console": "warn",
    "no-debugger": "error"
  }
}
```

### 3. Prettier 설정

#### .prettierrc.json
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "avoid",
  "endOfLine": "lf"
}
```

#### .prettierignore
```plaintext
node_modules/
dist/
build/
coverage/
*.min.js
*.min.css
package-lock.json
yarn.lock
pnpm-lock.yaml
```

### 4. 통합 설정

#### package.json 스크립트
```json
{
  "scripts": {
    "lint": "eslint src --ext .ts,.tsx",
    "lint:fix": "eslint src --ext .ts,.tsx --fix",
    "format": "prettier --write src/**/*.{ts,tsx,js,jsx,json,md}",
    "format:check": "prettier --check src/**/*.{ts,tsx,js,jsx,json,md}",
    "code-quality": "npm run lint && npm run format:check"
  }
}
```

## 예시

### 1. 실제 사용 사례

#### TypeScript 프로젝트 설정
```typescript
// src/utils/validation.ts
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export function validateEmail(email: string): ValidationResult {
  const errors: string[] = [];
  
  if (!email) {
    errors.push('이메일은 필수입니다.');
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.push('유효한 이메일 형식이 아닙니다.');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validatePassword(password: string): ValidationResult {
  const errors: string[] = [];
  
  if (!password) {
    errors.push('비밀번호는 필수입니다.');
  } else if (password.length < 8) {
    errors.push('비밀번호는 최소 8자 이상이어야 합니다.');
  } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
    errors.push('비밀번호는 대소문자와 숫자를 포함해야 합니다.');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
```

#### React 컴포넌트 예제
```typescript
// src/components/UserForm.tsx
import React, { useState } from 'react';
import { validateEmail, validatePassword, ValidationResult } from '../utils/validation';

interface UserFormProps {
  onSubmit: (userData: { email: string; password: string }) => void;
}

export const UserForm: React.FC<UserFormProps> = ({ onSubmit }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailValidation, setEmailValidation] = useState<ValidationResult>({
    isValid: true,
    errors: [],
  });
  const [passwordValidation, setPasswordValidation] = useState<ValidationResult>({
    isValid: true,
    errors: [],
  });

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEmail = e.target.value;
    setEmail(newEmail);
    setEmailValidation(validateEmail(newEmail));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPassword = e.target.value;
    setPassword(newPassword);
    setPasswordValidation(validatePassword(newPassword));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const emailResult = validateEmail(email);
    const passwordResult = validatePassword(password);
    
    setEmailValidation(emailResult);
    setPasswordValidation(passwordResult);

    if (emailResult.isValid && passwordResult.isValid) {
      onSubmit({ email, password });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="user-form">
      <div className="form-group">
        <label htmlFor="email">이메일</label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={handleEmailChange}
          className={emailValidation.isValid ? 'valid' : 'invalid'}
        />
        {!emailValidation.isValid && (
          <ul className="error-list">
            {emailValidation.errors.map((error, index) => (
              <li key={index} className="error-item">
                {error}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="password">비밀번호</label>
        <input
          type="password"
          id="password"
          value={password}
          onChange={handlePasswordChange}
          className={passwordValidation.isValid ? 'valid' : 'invalid'}
        />
        {!passwordValidation.isValid && (
          <ul className="error-list">
            {passwordValidation.errors.map((error, index) => (
              <li key={index} className="error-item">
                {error}
              </li>
            ))}
          </ul>
        )}
      </div>

      <button type="submit" disabled={!emailValidation.isValid || !passwordValidation.isValid}>
        제출
      </button>
    </form>
  );
};
```

### 2. 고급 패턴

#### 커스텀 ESLint 규칙
```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    'plugin:prettier/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: './tsconfig.json',
  },
  plugins: ['@typescript-eslint', 'prettier'],
  rules: {
    'prettier/prettier': 'error',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'prefer-const': 'error',
    'no-var': 'error',
    'object-shorthand': 'error',
    'prefer-template': 'error',
  },
  overrides: [
    {
      files: ['*.test.ts', '*.spec.ts'],
      rules: {
        '@typescript-eslint/no-explicit-any': 'off',
        'no-console': 'off',
      },
    },
  ],
};
```

#### VS Code 설정
```json
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact"
  ],
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true
}
```

#### Git Hooks 설정
```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{js,jsx,json,md}": [
      "prettier --write"
    ]
  }
}
```

## 운영 팁

### 성능 최적화

#### ESLint 캐싱 설정
```json
// .eslintrc.json
{
  "cache": true,
  "cacheLocation": "./node_modules/.cache/.eslintcache"
}
```

#### Prettier 성능 최적화
```json
// .prettierrc.json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "avoid",
  "endOfLine": "lf",
  "overrides": [
    {
      "files": "*.json",
      "options": {
        "printWidth": 120
      }
    }
  ]
}
```

### 에러 처리

#### ESLint 오류 해결
```bash
# 특정 규칙 비활성화 (임시)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const data: any = response.json();

# 파일 전체에서 규칙 비활성화
/* eslint-disable @typescript-eslint/no-explicit-any */

# 특정 라인에서 규칙 비활성화
// eslint-disable-line @typescript-eslint/no-unused-vars
const unusedVariable = 'test';
```

#### Prettier 충돌 해결
```json
// .eslintrc.json - Prettier 충돌 방지
{
  "extends": [
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "prettier"  // ESLint 규칙과 Prettier 충돌 방지
  ],
  "plugins": [
    "@typescript-eslint",
    "prettier"
  ],
  "rules": {
    "prettier/prettier": "error"
  }
}
```

## 참고

### ESLint vs Prettier 비교표

| 구분 | ESLint | Prettier |
|------|--------|----------|
| **목적** | 코드 품질 검사 | 코드 포맷팅 |
| **규칙** | 프로그래밍 규칙 | 스타일 규칙 |
| **설정** | 복잡한 규칙 설정 | 간단한 스타일 설정 |
| **자동 수정** | 제한적 | 포괄적 |

### 일반적인 ESLint 규칙

| 규칙 | 설명 | 권장 설정 |
|------|------|-----------|
| `@typescript-eslint/no-explicit-any` | any 타입 사용 제한 | warn |
| `@typescript-eslint/no-unused-vars` | 사용하지 않는 변수 | error |
| `no-console` | console 사용 제한 | warn |
| `prefer-const` | const 사용 권장 | error |

### 결론
ESLint와 Prettier를 함께 사용하여 TypeScript 프로젝트의 코드 품질을 향상시키세요.
적절한 규칙 설정으로 팀의 일관된 코드 스타일을 유지하세요.
자동화된 도구를 활용하여 개발 효율성을 높이세요.
VS Code 설정과 Git Hooks를 통해 개발 워크플로우를 최적화하세요.
성능 최적화 옵션을 활용하여 빌드 및 검사 속도를 개선하세요.
규칙 충돌을 방지하기 위한 적절한 설정을 적용하세요.

