---
title: TypeScript 컴파일러(tsc) 완벽 가이드
tags: [language, typescript, 프로젝트-설정-및-컴파일러, tsc, compiler, tsconfig, build]
updated: 2026-04-28
---

# TypeScript 컴파일러(tsc) 완벽 가이드

## tsc가 실제로 하는 일

`tsc`는 단순히 `.ts`를 `.js`로 바꾸는 도구가 아니다. 내부적으로는 다섯 단계를 거치는 풀 컴파일러다. 이 단계를 이해하고 있어야 빌드가 느려지거나 타입 에러가 이상하게 잡힐 때 원인을 찾을 수 있다.

```
스캐너(Scanner) → 파서(Parser) → 바인더(Binder) → 체커(Checker) → 이미터(Emitter)
                                                                    └─ 트랜스폼(Transformers)
```

각 단계의 역할은 다음과 같다.

- **스캐너**: 소스 텍스트를 토큰 스트림으로 쪼갠다. `const x = 1;`이 `const`, `x`, `=`, `1`, `;` 다섯 토큰이 된다. 이 단계에서는 의미를 따지지 않는다.
- **파서**: 토큰 스트림을 AST(Abstract Syntax Tree)로 만든다. 이 단계에서 문법 오류(`SyntaxError`)가 잡힌다. JSX 파싱 여부, target에 따른 문법 허용 범위가 여기서 갈린다.
- **바인더**: AST를 돌면서 심볼 테이블을 만든다. 같은 스코프에 같은 이름이 두 번 선언됐는지, 어느 식별자가 어느 선언을 가리키는지를 연결한다. **타입은 아직 없다.** 단순히 "이 변수가 어디 선언됐는가"를 추적한다.
- **체커**: 실제 타입 추론과 검증이 일어나는 단계다. 컴파일 시간의 대부분이 여기서 소비된다. 제네릭 인스턴스화, 컨디셔널 타입 풀이, 함수 시그니처 매칭 같은 무거운 연산이 모두 여기서 돈다.
- **이미터**: 체커가 끝난 AST를 받아서 JavaScript와 `.d.ts`를 생성한다. 도중에 트랜스폼 파이프라인이 끼어들어 데코레이터를 풀거나 JSX를 변환하거나 import elision을 수행한다.

이 구조에서 **체커가 병목**이다. 빌드가 느리다고 느껴지면 거의 항상 체커 단계에서 시간을 쓰고 있다. `--diagnostics`로 단계별 시간을 찍어보면 바로 보인다.

```bash
$ npx tsc --diagnostics
Files:                  1234
Lines:                190423
Identifiers:          156782
Symbols:              289103
Types:                124538
Memory used:        892456K
I/O Read time:        0.32s
Parse time:           1.84s
Bind time:            0.71s
Check time:           7.63s   ← 대부분 여기
Emit time:            1.12s
Total time:          11.62s
```

`Check time`이 다른 항목 합보다 크게 나오면 타입 단순화 작업을 하거나, `skipLibCheck: true`로 라이브러리 타입 검증을 건너뛰는 방향이 답이다.

## tsconfig.json 핵심 옵션

`tsc --init`이 만들어주는 기본 파일은 보수적이라 실무에는 거의 쓰지 않는다. Node 백엔드 기준으로 실제로 손대는 옵션은 정해져 있다.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,

    "outDir": "dist",
    "rootDir": "src",

    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,

    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo",

    "isolatedModules": true,
    "verbatimModuleSyntax": true,

    "sourceMap": true,
    "declaration": true,
    "declarationMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### target과 module의 관계

`target`은 **언어 문법**(arrow function, class field, optional chaining 같은 ES 신문법)이 다운레벨링되는지를 결정한다. `module`은 **모듈 시스템**(import/export가 어떻게 변환되는지)을 결정한다. 둘은 별개로 움직인다.

자주 헷갈리는 부분: `target: ES2015`이어도 `module: CommonJS`면 `import`는 `require`로 바뀐다. 반대로 `target: ES2022`인데 `module: ES2020`이면 `require`로 바뀌지 않고 `import`가 그대로 남는다. Node 환경에서 이걸 잘못 잡으면 런타임에 `Cannot use import statement outside a module`을 만난다.

`NodeNext`는 비교적 최근에 추가된 값으로, 패키지의 `package.json` `type` 필드와 `.cts/.mts` 확장자를 함께 본다. ESM/CommonJS 혼용 환경에서는 `NodeNext`가 사실상 정답이다.

### strict 계열을 다 켜는 이유

5년차쯤 되면 `strict: true`만으로는 부족하다는 걸 안다. 실제로 버그를 잡아주는 추가 옵션은 다음 두 가지다.

- `noUncheckedIndexedAccess`: `arr[0]`, `obj[key]`의 결과 타입이 `T`가 아니라 `T | undefined`가 된다. 처음 켜면 코드가 빨갛게 변하지만, 인덱스 접근으로 인한 런타임 `undefined`를 컴파일 타임에 거의 다 잡는다.
- `exactOptionalPropertyTypes`: `{ name?: string }`에 명시적으로 `undefined`를 넣는 걸 막는다. `optional`과 `undefined`를 구분해서 쓰는 코드베이스에서 도움이 된다.

`noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`는 `strict: true`에 이미 포함된다.

### isolatedModules와 verbatimModuleSyntax

`isolatedModules: true`는 **각 파일이 독립적으로 트랜스파일 가능한지**를 검증하는 옵션이다. swc, esbuild, Babel 같은 단일 파일 트랜스파일러는 다른 파일의 타입 정보를 보지 않고 한 파일씩 변환한다. 이 모드에서 깨지는 문법(예: `export const enum`, 타입과 값이 섞인 re-export)을 tsc가 미리 걸러준다.

`verbatimModuleSyntax: true`는 그 강화판이다. `import` 구문에서 타입만 쓰는 import는 반드시 `import type`으로 명시해야 한다. tsc의 import elision 동작을 단순화해서, 트랜스파일러가 어떤 import를 지워야 할지 헷갈릴 여지를 없앤다. 번들러나 swc로 빌드하는 프로젝트라면 켜두는 게 안전하다.

```typescript
// verbatimModuleSyntax: true에서는 컴파일 에러
import { User } from './types';
function f(u: User) {}

// 정상
import type { User } from './types';
function f(u: User) {}
```

## 컴파일 파이프라인 디버깅

빌드가 느리거나 모듈 해석이 이상할 때 쓰는 진단 플래그가 있다. 이걸 모르면 무작정 옵션만 갈아끼우면서 시간을 버린다.

### --diagnostics와 --extendedDiagnostics

`--diagnostics`는 앞에서 본 단계별 시간 요약을 출력한다. `--extendedDiagnostics`는 더 상세한 정보, 특히 어떤 트랜스폼이 시간을 썼는지까지 찍어준다.

```bash
npx tsc --noEmit --extendedDiagnostics
```

체커 시간이 길게 찍히면 다음 순서로 의심한다.

1. `skipLibCheck`가 꺼져 있는가. 큰 의존성(특히 `@types/node`, `aws-sdk`)을 매번 검증하면 수 초가 그냥 사라진다.
2. 복잡한 컨디셔널 타입이나 재귀 제네릭이 있는가. `Type instantiation is excessively deep` 경고가 한 번이라도 보인다면 그 타입을 단순화해야 한다.
3. 같은 타입을 여러 파일에서 다르게 추론하고 있지 않은가. `tsc --generateTrace ./trace`로 타입 추론 트레이스를 뽑으면 `chrome://tracing`에서 시각화할 수 있다.

### --listFiles와 --traceResolution

"이 파일이 왜 컴파일에 포함되지" 또는 "왜 이 모듈을 못 찾지"를 디버깅할 때 쓴다.

```bash
# 컴파일에 포함된 모든 파일 목록 출력
npx tsc --listFiles --noEmit | head -50

# 모듈 해석 과정을 단계별로 출력
npx tsc --traceResolution --noEmit 2>&1 | grep "lodash"
```

`--traceResolution`은 출력이 어마어마하게 많아서 보통 grep으로 특정 패키지만 골라본다. `paths` 설정이 안 먹거나, `node_modules` 안에서 다른 버전을 끌어가고 있을 때 결정적 단서를 준다.

### tsc 단독으로는 못 보는 것

JS 런타임 에러, 의존성 사이클 검출, dead code 분석은 tsc의 책임 범위 밖이다. 컴파일이 통과했다고 코드가 동작한다는 보장은 없다. tsc는 **타입과 문법**까지만 검증한다.

## 빌드 최적화 실전

### isolatedModules vs transpileOnly의 진짜 차이

둘 다 "타입 검사를 건너뛰는" 옵션처럼 보이지만 동작이 다르다.

- `isolatedModules`는 **tsc가 컴파일하면서** 단일 파일 트랜스파일에서 깨질 코드를 검출하는 것이다. 타입 검사는 정상적으로 한다.
- `transpileOnly`는 `ts-node`나 `ts-loader`의 옵션으로, **타입 검사를 아예 끄고** 변환만 한다. 빌드는 빨라지지만 `any` 같은 게 무방비로 흘러간다.

실무 패턴은 보통 이렇다. 빠른 빌드용 트랜스파일은 swc/esbuild가 담당하고(`transpileOnly`에 해당), 타입 검사는 tsc `--noEmit`로 별도 잡(job)으로 돌린다.

```json
{
  "scripts": {
    "build": "swc src -d dist",
    "type-check": "tsc --noEmit",
    "ci": "npm run type-check && npm run build"
  }
}
```

이렇게 분리하면 dev 빌드는 1초 안에 끝나고, 타입 검증은 CI나 pre-push에서만 돈다.

### swc / esbuild 대비 tsc 성능

대략적인 체감으로, 같은 코드베이스를 변환만 한다고 했을 때 esbuild는 tsc보다 50~100배, swc는 20~50배 빠르다. 이유는 두 가지다.

1. esbuild는 Go, swc는 Rust로 짜여 있어서 네이티브 속도다.
2. 둘 다 타입 검사를 안 한다. 단일 파일 트랜스파일러일 뿐이다.

즉, 비교 자체가 공정하지 않다. tsc는 타입 검사가 본업이고, 트랜스파일은 부산물에 가깝다. **타입 검사가 필요 없는 변환**은 swc/esbuild에 맡기고 **타입 검사**만 tsc에 맡기는 게 5년차 현실이다.

### Project References와 빌드 그래프

모노레포나 큰 프로젝트에서 tsc가 진가를 발휘하는 부분이 Project References다. `references` 필드로 다른 프로젝트를 참조하면, 그 프로젝트의 `.d.ts`만 읽고 본문은 다시 컴파일하지 않는다.

```
repo/
├── tsconfig.json          (root)
├── packages/
│   ├── core/
│   │   └── tsconfig.json  (composite: true)
│   ├── api/
│   │   └── tsconfig.json  (references: core)
│   └── worker/
│       └── tsconfig.json  (references: core)
```

```json
// packages/api/tsconfig.json
{
  "compilerOptions": {
    "composite": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "references": [
    { "path": "../core" }
  ],
  "include": ["src/**/*"]
}
```

`composite: true`는 이 프로젝트가 다른 곳에서 참조될 수 있다는 의미다. 강제되는 옵션이 몇 가지 있다(`declaration: true`, `tsBuildInfoFile` 자동 설정 등).

### --build 모드

Project References가 있는 프로젝트는 일반 `tsc` 대신 `tsc --build`(또는 `tsc -b`)로 빌드한다. 이 모드는 의존 그래프를 따라가면서 변경된 프로젝트만 다시 빌드한다.

```bash
# 변경된 것만 빌드
npx tsc -b

# 강제로 전체 다시 빌드
npx tsc -b --force

# 빌드 산출물과 .tsbuildinfo 모두 삭제
npx tsc -b --clean

# watch 모드로 그래프 추적
npx tsc -b --watch
```

`--clean`은 명시적으로 산출물을 지운다. `rm -rf dist`보다 안전하다. 다른 디렉토리를 건드리지 않고 tsc가 만든 것만 정확히 지우기 때문이다.

`--force`는 변경 검출을 무시하고 전부 다시 빌드한다. 캐시가 꼬였다고 의심될 때 쓴다.

### .tsbuildinfo 캐시 무효화

`incremental: true` 또는 `composite: true`일 때 tsc는 `.tsbuildinfo` 파일에 이전 빌드의 시그니처를 저장한다. 다음 빌드에서 변경된 파일만 다시 처리하기 위해서다.

이 캐시가 무효화되는 케이스는 다음과 같다.

- TypeScript 버전이 바뀐 경우. 메이저는 물론 마이너 버전 차이에서도 캐시 포맷이 바뀌면 무효화된다.
- `tsconfig.json`의 `compilerOptions`가 변경된 경우.
- 참조하는 프로젝트(`references`)의 `.d.ts` 시그니처가 바뀐 경우. 본문 변경이 아니라 **공개 API 변경**이 트리거다. 함수 본문만 고치면 의존 프로젝트는 재빌드되지 않는다.
- `paths`나 `baseUrl` 같은 모듈 해석 옵션이 바뀐 경우.

캐시가 깨졌는데 정리가 안 됐을 때 보이는 증상은 "타입 에러가 안 잡힌다"거나 "지운 파일이 여전히 컴파일된 듯이 보인다"는 것이다. 이때는 `tsc -b --clean` 후 `--force`로 재빌드한다.

`.tsbuildinfo` 위치는 `tsBuildInfoFile`로 지정한다. 기본값은 `outDir` 옆이지만, 빌드 산출물과 분리하고 싶으면 `node_modules/.cache` 아래로 옮긴다. 도커 빌드 캐시 레이어를 활용할 때 위치 분리가 중요해진다.

## Watch 모드 내부

`tsc --watch`는 단순히 파일을 모니터링하는 게 아니다. OS의 파일 시스템 이벤트(macOS의 FSEvents, Linux의 inotify, Windows의 ReadDirectoryChangesW)를 사용한다. 그런데 이 이벤트가 신뢰할 수 없는 환경이 있다.

- 도커 컨테이너 안에서 호스트 볼륨을 마운트한 경우. inotify 이벤트가 안 올 수 있다.
- 네트워크 파일 시스템(NFS, SMB)을 쓰는 경우. 이벤트가 누락되거나 지연된다.
- WSL1 환경. WSL2는 괜찮다.

이런 환경에서는 폴링(polling)으로 폴백해야 한다.

```json
{
  "watchOptions": {
    "watchFile": "useFsEvents",
    "watchDirectory": "useFsEvents",
    "fallbackPolling": "dynamicPriority",
    "synchronousWatchDirectory": false,
    "excludeDirectories": ["node_modules", "dist"]
  }
}
```

`watchFile` 값으로 자주 쓰는 것은 다음과 같다.

- `useFsEvents`: OS 네이티브 이벤트. 가장 빠르지만 환경에 따라 깨진다.
- `priorityPollingInterval`: 우선순위 기반 폴링. CPU를 일정 부분 쓴다.
- `dynamicPriorityPolling`: 변경 빈도에 따라 폴링 주기를 조정한다.

도커에서 hot reload가 안 먹으면 `watchFile: "priorityPollingInterval"`로 강제하면 거의 해결된다. 다만 폴링은 CPU를 계속 쓰니 컨테이너 리소스 한계를 보고 정한다.

`excludeDirectories`로 `node_modules`를 빼는 건 필수다. 안 빼면 와처가 수만 개 파일을 감시하면서 메모리를 잡아먹는다.

## tsc 단독의 한계

tsc만으로는 부족한 영역이 있다. 5년 정도 굴리다 보면 다음 한계에 부딪힌다.

- **번들링이 없다**: tsc는 파일 단위 변환만 한다. 트리 셰이킹, 코드 스플리팅, 정적 자산(이미지, CSS) 처리는 esbuild/rollup/webpack/vite의 영역이다. 백엔드라도 단일 파일 배포를 원하면 esbuild 같은 번들러를 얹어야 한다.
- **트랜스폼 플러그인이 없다**: `transformers` API가 있긴 하지만 설정이 까다롭고, 실무에서는 babel/swc 플러그인 생태계가 훨씬 풍부하다. 데코레이터 메타데이터 같은 표준에서 벗어난 변환은 swc 쪽이 편하다.
- **다중 출력 포맷이 없다**: ESM과 CommonJS를 동시에 빌드해서 듀얼 패키지를 만들고 싶으면 tsc를 두 번 돌리거나 다른 도구를 써야 한다. tsup, unbuild 같은 래퍼가 이 문제를 해결한다.

전형적인 분리 패턴은 이렇다.

```
[변환]   swc / esbuild       → 빠른 JS 출력
[타입]   tsc --noEmit        → 타입 검증만
[번들]   esbuild / rollup    → 단일 파일 배포 (필요 시)
[.d.ts]  tsc --emitDeclarationOnly → 타입 정의 파일만
```

라이브러리 패키지를 만들 때 자주 보이는 구성이다. 변환은 빠른 도구에 맡기고, tsc는 타입 검증과 `.d.ts` 생성에만 사용한다.

## 트러블슈팅

### 메모리 초과

큰 프로젝트에서 다음 에러를 보는 일이 있다.

```
<--- Last few GCs --->
[12345:0x108008000] FATAL ERROR: Reached heap limit
Allocation failed - JavaScript heap out of memory
```

Node 기본 힙 한계가 4GB 정도라 큰 모노레포에서 한계에 닿는다. 임시 처방은 환경 변수로 한계를 올리는 것이다.

```bash
NODE_OPTIONS="--max-old-space-size=8192" npx tsc -b
```

다만 메모리가 부족하다는 건 거의 항상 **체커가 비효율적인 타입을 처리하고 있다**는 신호다. 진짜 해법은 다음을 확인하는 것이다.

1. `tsc --generateTrace ./trace` 후 trace 파일을 분석해서 어느 타입이 메모리를 잡는지 본다.
2. 깊이 중첩된 컨디셔널 타입이나 재귀 제네릭을 단순화한다.
3. Project References로 그래프를 쪼개서 한 번에 처리하는 파일 수를 줄인다.
4. `skipLibCheck: true`를 켠다. 의외로 안 켜져 있는 경우가 많다.

힙 사이즈를 키우는 건 응급 처치다. 근본 원인을 안 잡으면 6개월 뒤에 또 같은 에러를 본다.

### 빌드가 느릴 때 원인 분석 순서

1. `tsc --diagnostics`로 단계별 시간을 본다. Check time이 70% 이상이면 타입 문제, Parse/Bind time이 크면 파일 수 문제다.
2. `tsc --listFiles`로 컴파일에 들어가는 파일 수를 센다. 의도하지 않은 파일이 들어오면 `exclude`나 `include` 패턴이 잘못된 것이다.
3. `tsc --traceResolution | grep "Resolving module"` 출력이 비정상적으로 길면 모듈 해석에 시간을 쓰는 것이다. `paths` 설정과 심볼릭 링크를 의심한다.
4. `--generateTrace`로 trace 파일을 뽑고 `chrome://tracing`에서 본다. 가장 오래 걸리는 타입 인스턴스화를 찾는다.

### 모듈을 못 찾을 때

```
error TS2307: Cannot find module './foo' or its corresponding type declarations.
```

순서대로 의심한다.

1. `moduleResolution`이 `NodeNext`인데 import 경로에 확장자(`.js`)를 안 붙였는가. ESM 모드에서는 확장자가 필수다.
2. `paths`를 설정했지만 `baseUrl`이 없는가. tsc 5.0부터는 `baseUrl` 없이도 paths가 동작하지만, 번들러는 여전히 `baseUrl`을 요구할 수 있다.
3. 심볼릭 링크(`pnpm`, `yarn workspace`)가 걸려 있는데 `preserveSymlinks` 설정이 어긋났는가.
4. `node_modules`에 같은 패키지가 두 버전 깔려 있어서 다른 경로로 해석되는가. `npm ls <패키지>`로 확인한다.

### 타입 검사 통과한 코드가 런타임에 깨질 때

거의 다음 셋 중 하나다.

- 외부에서 받은 데이터(JSON, 환경 변수, DB 결과)를 타입 단언(`as`)으로 강제 캐스팅했다. 런타임 검증을 안 했으니 타입과 실제가 어긋날 수 있다. zod 같은 검증 라이브러리를 써야 한다.
- `any` 또는 `unknown`이 어딘가에서 흘러들어왔다. `noImplicitAny`를 켜도 명시적 `any`는 막지 못한다.
- 의존성의 `.d.ts`가 실제 구현과 다르다. `@types/*` 패키지가 본 코드보다 늦게 업데이트되는 일이 흔하다.

타입 시스템은 약속이지 보증이 아니다. 외부 경계에서는 항상 런타임 검증을 한 번 더 한다고 생각하는 게 안전하다.
