---
title: TypeScript ESLint와 Prettier 설정
tags: [language, typescript, 프로젝트-설정-및-컴파일러, eslint, prettier, code-quality]
updated: 2026-06-22
---

# TypeScript ESLint와 Prettier 설정

## 배경

ESLint는 코드의 문제를 잡아내는 도구고, Prettier는 코드 모양을 통일하는 도구다. 역할이 다르다. ESLint는 "선언만 하고 안 쓰는 변수가 있다", "any를 썼다" 같은 코드 품질 문제를 본다. Prettier는 들여쓰기, 따옴표, 줄바꿈 같은 모양만 본다. 두 도구를 같이 쓰면 영역이 겹치는 부분에서 충돌이 나는데, 이 충돌을 어떻게 정리하느냐가 설정의 핵심이다.

2024년 ESLint 9가 나오면서 설정 방식이 크게 바뀌었다. 기존 `.eslintrc.json` 방식(eslintrc, 흔히 레거시 config라 부른다)이 deprecated 되고 `eslint.config.js` 기반의 flat config가 기본이 됐다. ESLint 9 이상에서는 flat config가 없으면 에러가 난다. 그래서 지금 새 프로젝트를 시작한다면 flat config로 가는 게 맞고, 기존 프로젝트라면 마이그레이션을 고려해야 한다. 이 문서는 flat config를 기준으로 설명하되, 레거시 방식과 어떻게 다른지도 같이 다룬다.

## 레거시 .eslintrc 방식

먼저 기존 방식을 알아야 flat config가 왜 바뀌었는지 이해가 된다. ESLint 8까지는 `.eslintrc.json` 또는 `.eslintrc.js`를 썼다.

```bash
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install --save-dev prettier eslint-config-prettier
```

```json
// .eslintrc.json (레거시 — ESLint 8 이하)
{
  "root": true,
  "env": {
    "browser": true,
    "es2022": true,
    "node": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "plugins": ["@typescript-eslint"],
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }]
  }
}
```

여기서 자주 틀리는 부분이 `extends`에 들어가는 이름이다. `@typescript-eslint/recommended`라고 쓰면 동작하지 않는다. 레거시 config의 `extends`에서 플러그인이 제공하는 설정을 참조할 때는 `plugin:` 접두사가 붙어야 한다. 정확한 이름은 `plugin:@typescript-eslint/recommended`다. 접두사 없이 `@typescript-eslint/recommended`라고 쓰면 ESLint가 그걸 패키지 이름으로 해석해서 모듈을 찾지 못하거나 엉뚱한 곳을 본다. 레거시 config를 손볼 일이 있으면 이 접두사를 꼭 확인해야 한다.

`extends` 배열에서 `prettier`(eslint-config-prettier)는 항상 맨 마지막에 와야 한다. 뒤에 오는 설정이 앞 설정을 덮어쓰기 때문이다. eslint-config-prettier는 Prettier와 충돌하는 ESLint 스타일 규칙을 전부 끄는 역할을 하는데, 이게 다른 설정보다 먼저 오면 뒤에 오는 설정이 다시 그 규칙들을 켜버린다.

## flat config (ESLint 9 표준)

flat config는 `eslint.config.js` 파일 하나로 설정한다. 가장 큰 변화는 `extends`/`plugins`를 문자열 이름으로 참조하지 않고, 패키지를 직접 import해서 객체로 넣는다는 점이다. 이름 오타로 동작 안 하는 문제가 사라졌다.

TypeScript 프로젝트는 `typescript-eslint` 패키지를 쓴다. 기존의 `@typescript-eslint/parser`와 `@typescript-eslint/eslint-plugin`을 묶어서 flat config에 맞게 헬퍼를 제공하는 패키지다.

```bash
npm install --save-dev eslint typescript-eslint
npm install --save-dev prettier eslint-config-prettier
```

```js
// eslint.config.js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
  {
    ignores: ['dist/', 'build/', 'coverage/', 'node_modules/'],
  },
  prettier, // 항상 마지막. Prettier와 충돌하는 규칙을 끈다
);
```

`tseslint.config()`는 typescript-eslint가 제공하는 헬퍼다. 타입 추론이 붙어서 IDE에서 자동완성이 되고, 잘못된 키를 넣으면 바로 잡아준다. ESLint 9.x에서는 `eslint` 패키지에 들어있는 `defineConfig`를 써도 된다.

```js
// defineConfig 사용 (ESLint 9.x)
import { defineConfig } from 'eslint/config';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default defineConfig([
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,
]);
```

flat config에서 달라진 점 몇 가지를 정리하면, `env` 키가 없어졌다. 대신 `languageOptions.globals`로 전역 변수를 지정한다. `globals` 패키지를 받아서 쓴다.

```js
import globals from 'globals';

export default tseslint.config({
  languageOptions: {
    globals: {
      ...globals.node,
      ...globals.browser,
    },
  },
});
```

`.eslintignore` 파일도 더 이상 읽지 않는다. 무시할 경로는 config 안의 `ignores`로 넣는다. 위 예제처럼 `ignores`만 있는 객체를 따로 두면 전역 ignore로 동작한다.

## .eslintrc에서 flat config로 마이그레이션

기존 프로젝트를 옮길 때 손으로 다 바꾸기 번거로우면 자동 변환 도구가 있다.

```bash
npx @eslint/migrate-config .eslintrc.json
```

`@eslint/eslintrc`의 `FlatCompat`를 써서 변환한 `eslint.config.mjs`를 만들어준다. 다만 자동 변환 결과는 `FlatCompat`로 레거시 설정을 감싼 형태라 깔끔하지 않다. 동작은 하지만, 시간이 되면 위처럼 import 기반으로 직접 다시 쓰는 게 유지보수에 낫다. 변환 후에 `npx eslint .`를 한 번 돌려서 규칙 적용 결과가 이전과 같은지 확인해야 한다. 레거시에서 켜져 있던 규칙이 flat config에서 빠지는 경우가 있다.

마이그레이션하면서 자주 막히는 부분이 플러그인 이름이다. 레거시에서 `plugins: ['@typescript-eslint']`라고 문자열로 등록하던 걸 flat config에서는 객체 키로 등록한다.

```js
import tseslint from 'typescript-eslint';

export default [
  {
    plugins: { '@typescript-eslint': tseslint.plugin },
    languageOptions: { parser: tseslint.parser },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
];
```

`tseslint.config()` 헬퍼를 쓰면 이런 등록을 알아서 해주므로 직접 객체로 쓸 일은 타입 정보 린팅이나 특수한 플러그인을 끼울 때 정도다.

## Prettier 설정

Prettier 설정은 flat config와 무관하게 별도 파일이다.

```json
// .prettierrc.json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "endOfLine": "lf"
}
```

`trailingComma`는 기본값이 Prettier 3부터 `"all"`로 바뀌었다. 후행 쉼표가 붙으면 함수 인자나 배열에 한 줄 추가할 때 diff가 그 줄 하나만 잡혀서 코드 리뷰가 깔끔해진다. 굳이 `"es5"`로 내릴 이유가 없으면 `"all"`을 둔다.

`endOfLine`을 `"lf"`로 박아두는 건 윈도우/맥 혼합 팀에서 줄바꿈 문자 때문에 전체 파일이 diff로 잡히는 사고를 막기 위해서다. 이걸 안 넣고 `.gitattributes`도 없으면 윈도우 사용자가 커밋할 때마다 CRLF로 바뀌어서 변경 안 한 파일이 통째로 수정된 것처럼 보인다.

## ESLint와 Prettier 충돌 정리 — 두 가지 방식

여기가 실무에서 가장 헷갈리는 지점이다. ESLint와 Prettier를 연결하는 방식이 두 가지 있는데 트레이드오프가 있다.

### 방식 1: eslint-plugin-prettier로 통합

eslint-plugin-prettier를 쓰면 Prettier를 ESLint 규칙으로 돌린다. 포맷이 안 맞는 곳이 ESLint 에러(`prettier/prettier`)로 뜬다.

```js
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  eslintPluginPrettierRecommended, // 이게 eslint-config-prettier까지 포함한다
);
```

장점은 `eslint --fix` 한 번으로 린트와 포맷이 같이 처리된다는 점이다. 단점이 더 크다. Prettier를 ESLint 엔진 위에서 돌리니까 린트 속도가 눈에 띄게 느려진다. 그리고 포맷 문제가 빨간 줄로 잔뜩 뜨면 진짜 코드 문제가 그 안에 묻힌다. 포맷은 에러가 아니라 그냥 기계가 고치면 되는 일인데 에러 취급을 받는 게 거슬린다.

### 방식 2: Prettier를 ESLint 밖에서 따로 실행

요즘은 이 방식을 더 많이 쓴다. ESLint는 코드 품질만 보고, 포맷은 Prettier CLI로 따로 돌린다. 충돌하는 ESLint 스타일 규칙만 eslint-config-prettier로 끈다.

```js
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettier, // 충돌 규칙만 끄고 끝. Prettier 자체는 ESLint가 안 돌림
);
```

```json
// package.json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  }
}
```

`eslint-config-prettier`가 정확히 무슨 일을 하는지 보고 싶으면 이 명령으로 확인할 수 있다.

```bash
npx eslint-config-prettier eslint.config.js
```

지금 설정에서 Prettier와 충돌하는 ESLint 규칙이 켜져 있는지 목록으로 알려준다. 역할 분리가 명확해서 디버깅이 쉽고, 포맷이 안 맞아도 린트 결과가 더러워지지 않는다. 단점은 명령을 두 개 돌려야 한다는 것뿐인데, lint-staged로 묶으면 그것도 사실상 신경 쓸 일이 없다.

## 타입 정보 린팅과 성능 문제

`@typescript-eslint`에는 타입 정보를 활용하는 규칙들이 있다(`no-floating-promises`, `no-misused-promises` 같은 것). 이런 규칙을 켜려면 ESLint가 타입스크립트 타입 정보에 접근해야 하고, 그러려면 `parserOptions.project`(또는 flat config의 `projectService`)를 설정해야 한다.

```js
export default tseslint.config(
  ...tseslint.configs.recommendedTypeChecked, // 타입 정보 기반 규칙 추가
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
);
```

문제는 속도다. 타입 정보 린팅을 켜면 ESLint가 내부에서 타입스크립트 프로그램을 통째로 빌드한다. 파일 몇 개만 린트해도 프로젝트 전체 타입 그래프를 만들어야 하니까, 큰 프로젝트에서는 린트가 몇 배 느려진다. 에디터에서 저장할 때마다 멈칫하는 게 느껴지면 이게 원인인 경우가 많다.

예전에는 `parserOptions.project: './tsconfig.json'`을 직접 지정했는데, typescript-eslint 8부터 `projectService: true`가 권장된다. 타입스크립트 언어 서비스를 재활용해서 매번 프로그램을 새로 안 만들고, 어느 tsconfig에 속하는지도 알아서 찾는다. 그래도 근본적으로 타입 정보 린팅 자체가 무겁다는 사실은 변하지 않는다.

현실적으로는 타입 정보가 필요한 규칙과 아닌 규칙을 나눠서, 평소 에디터에서는 가벼운 규칙만 돌리고 타입 기반 규칙은 CI에서만 돌리는 식으로 운영하기도 한다. 테스트 파일이나 설정 파일은 타입 린팅 대상에서 빼는 것도 방법이다.

```js
export default tseslint.config(
  ...tseslint.configs.recommendedTypeChecked,
  {
    // JS 설정 파일은 타입 정보 린팅에서 제외
    files: ['**/*.js'],
    ...tseslint.configs.disableTypeChecked,
  },
);
```

## monorepo와 다중 tsconfig

monorepo에서는 패키지마다 tsconfig가 따로 있다. 루트에 `eslint.config.js` 하나를 두고 모든 패키지를 린트하려면 어느 파일이 어느 tsconfig에 속하는지 ESLint가 알아야 한다.

`projectService: true`를 쓰면 이걸 대체로 알아서 처리한다. 각 파일이 속한 가장 가까운 tsconfig를 찾는다. 그래도 안 잡히는 파일이 있으면(어느 tsconfig에도 포함 안 된 파일) `allowDefaultProject` 옵션으로 예외를 둔다.

```js
languageOptions: {
  parserOptions: {
    projectService: {
      allowDefaultProject: ['*.js', '*.config.ts'],
    },
    tsconfigRootDir: import.meta.dirname,
  },
}
```

"파일이 어떤 tsconfig에도 포함되지 않았다"는 에러(`parserOptions.project has been provided but ... was not found`)가 monorepo에서 자주 나오는데, 보통 그 파일이 어느 패키지의 `include`에도 안 들어가 있어서 그렇다. 해당 tsconfig의 `include`를 고치거나, 위처럼 default project로 빼야 한다.

## lint-staged와 husky v9

커밋 전에 변경된 파일만 골라서 린트/포맷을 돌리려면 lint-staged와 husky를 같이 쓴다. husky가 v9로 올라오면서 설정 방식이 바뀌었다. 예전 husky v4의 `package.json` 안 `"husky": { "hooks": {...} }` 방식은 더 이상 안 쓴다. v9는 `.husky/` 디렉토리 안에 훅 스크립트 파일을 직접 둔다.

```bash
npm install --save-dev husky lint-staged
npx husky init
```

`husky init`이 `.husky/pre-commit` 파일을 만든다. v9에서는 이 파일 안에 명령만 적으면 된다. v8까지 첫 줄에 넣던 `#!/usr/bin/env sh`와 `. "$(dirname -- "$0")/_/husky.sh"` 같은 보일러플레이트가 v9에서는 deprecated 됐다. 그냥 명령만 넣는다.

```bash
# .husky/pre-commit
npx lint-staged
```

```json
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{js,json,md,css}": ["prettier --write"]
  }
}
```

lint-staged는 git에 staged된 파일만 골라서 명령에 넘긴다. 그래서 프로젝트가 아무리 커도 커밋 전 검사가 빠르다. 단 여기서 `eslint --fix`에 타입 정보 린팅이 걸려 있으면, 파일 몇 개만 바꿔도 타입 프로그램 전체를 빌드하느라 커밋이 느려진다. 커밋 훅에서는 타입 기반 규칙을 빼는 걸 고려해야 한다.

## CI에서 운영

CI에서는 경고(warning)도 실패로 처리하는 게 안전하다. 로컬에서 warn으로 둔 규칙은 개발 중엔 거슬리지 않게 넘어가지만, 그대로 쌓이면 의미가 없어진다. `--max-warnings 0`을 주면 경고가 하나라도 있으면 CI가 실패한다.

```yaml
# .github/workflows/ci.yml 일부
- name: Lint
  run: npx eslint . --max-warnings 0

- name: Format check
  run: npx prettier --check .
```

CI에서는 `--fix`나 `--write`를 쓰면 안 된다. 검사만 해야 한다. `prettier --check`는 포맷이 안 맞는 파일이 있으면 그 목록을 출력하고 비정상 종료한다. 개발자가 커밋 전에 `format`을 안 돌렸다는 뜻이므로 CI에서 막아야 한다.

ESLint 캐시를 켜면 CI에서도 변경 안 된 파일을 건너뛴다. 캐시 파일을 CI 캐시에 저장해두면 효과가 있다.

```bash
npx eslint . --cache --cache-location .eslintcache --max-warnings 0
```

## 규칙을 끄는 방법과 주의점

특정 줄에서만 규칙을 끌 때는 주석을 쓴다.

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const data: any = JSON.parse(raw);
```

`eslint-disable`을 남발하면 규칙을 켠 의미가 사라진다. disable 주석이 늘어나는 게 보이면 그 규칙 자체를 `warn`으로 내리거나 끄는 게 맞는지 다시 봐야 한다. 규칙은 켜져 있는데 코드 곳곳이 disable로 덮여 있는 상태가 제일 안 좋다.

쓰지 않게 된 disable 주석을 찾으려면 `reportUnusedDisableDirectives`를 켠다. 더 이상 필요 없는 disable 주석을 ESLint가 경고로 잡아준다.

```js
export default tseslint.config({
  linterOptions: {
    reportUnusedDisableDirectives: 'error',
  },
});
```

## 최소 동작 예제

설정이 제대로 걸렸는지 확인하는 작은 예제다. 일부러 문제를 심어둔 코드다.

```typescript
// src/sample.ts
const unused = 42;          // no-unused-vars: error
let name = "hello"          // 세미콜론 없음(Prettier), 큰따옴표(Prettier)
const value: any = name;    // no-explicit-any: warn
```

`npx eslint src/sample.ts`를 돌리면 `unused`는 에러, `any`는 경고로 잡힌다. 세미콜론과 따옴표는 ESLint에서 안 잡힌다(eslint-config-prettier가 껐으므로). `npx prettier --check src/sample.ts`를 돌리면 포맷이 안 맞는다고 나오고, `npx prettier --write src/sample.ts`를 하면 세미콜론이 붙고 큰따옴표가 작은따옴표로 바뀐다. 두 도구가 각자 자기 영역만 보고 있는지 이 예제로 확인할 수 있다.

## 정리용 비교표

| 구분 | ESLint | Prettier |
|------|--------|----------|
| 보는 것 | 코드 품질, 잠재 버그 | 코드 모양(들여쓰기, 따옴표 등) |
| 자동 수정 | 일부 규칙만 | 전부 |
| 충돌 처리 | eslint-config-prettier로 스타일 규칙 끔 | — |

| 규칙 | 의미 | 권장 |
|------|------|------|
| `@typescript-eslint/no-explicit-any` | any 사용 | warn |
| `@typescript-eslint/no-unused-vars` | 안 쓰는 변수 | error |
| `@typescript-eslint/no-floating-promises` | await/then 없는 Promise(타입 정보 필요) | error |
| `no-console` | console 사용 | warn |
