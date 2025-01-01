
# TypeScript `tsconfig.json` 상세 설명

`tsconfig.json`은 TypeScript 컴파일러(tsc)가 프로젝트를 빌드하는 데 사용하는 설정 파일입니다. 이 파일을 통해 프로젝트 전반에 걸친 컴파일 옵션, 포함할 파일 및 제외할 파일 등을 정의할 수 있습니다.

---

## 기본 구조

```json
{
  "compilerOptions": {
    // 컴파일러 옵션 정의
  },
  "include": [
    // 컴파일에 포함할 파일/폴더 정의
  ],
  "exclude": [
    // 컴파일에서 제외할 파일/폴더 정의
  ],
  "files": [
    // 명시적으로 컴파일할 파일 정의
  ],
  "extends": "./base.tsconfig.json",
  "references": []
}
```

---

## 주요 키 설명

### `compilerOptions`

`compilerOptions`는 TypeScript 컴파일러의 동작 방식을 세부적으로 제어하는 설정입니다. 주요 옵션은 다음과 같습니다:

#### 기본 컴파일 설정

- **`target`**  
  컴파일된 JavaScript 파일의 ECMAScript 버전을 지정합니다.  
  예: `"ES3"`, `"ES5"`, `"ES6"`, `"ES2020"`, `"ESNext"`

- **`module`**  
  사용할 모듈 시스템을 정의합니다.  
  예: `"CommonJS"`, `"ESNext"`, `"AMD"`, `"System"`

- **`lib`**  
  프로젝트에서 사용할 JavaScript API를 정의합니다.  
  예: `["DOM", "ES6", "DOM.Iterable"]`

- **`outDir`**  
  컴파일된 파일이 출력될 디렉터리를 지정합니다.

- **`rootDir`**  
  입력 파일의 기본 디렉터리를 지정합니다.

- **`strict`**  
  엄격한 TypeScript 컴파일 옵션을 활성화합니다. (`true`로 설정 시 하위 옵션도 모두 활성화)

- **`moduleResolution`**  
  모듈을 해석하는 방식을 정의합니다.  
  예: `"node"`, `"classic"`

---

#### 추가 옵션

- **`declaration`**  
  `.d.ts` 파일(타입 선언 파일)을 생성합니다.  
  값: `true` 또는 `false`

- **`sourceMap`**  
  `.map` 파일을 생성하여 디버깅을 지원합니다.

- **`removeComments`**  
  컴파일된 결과에서 주석을 제거합니다.

- **`noEmit`**  
  JavaScript 출력 파일을 생성하지 않습니다. 타입 체크만 수행할 때 사용합니다.

- **`skipLibCheck`**  
  `.d.ts` 파일의 타입 체크를 건너뜁니다. (빌드 속도 향상)

---

### `include`

컴파일에 포함할 파일 또는 디렉터리를 지정합니다.  
예:

```json
"include": ["src/**/*", "types/**/*.d.ts"]
```

---

### `exclude`

컴파일에서 제외할 파일 또는 디렉터리를 지정합니다.  
예:

```json
"exclude": ["node_modules", "dist", "**/*.test.ts"]
```

> 기본적으로 `node_modules`는 제외됩니다.

---

### `files`

명시적으로 컴파일할 파일 목록을 정의합니다.  
예:

```json
"files": ["src/index.ts", "src/config.ts"]
```

---

### `extends`

기존의 `tsconfig.json` 파일을 확장하여 설정을 상속받습니다.  
예:

```json
"extends": "./base.tsconfig.json"
```

---

### `references`

프로젝트 간 종속성을 정의하여 멀티 프로젝트 빌드를 지원합니다.  
예:

```json
"references": [
  { "path": "./core" },
  { "path": "./ui" }
]
```
