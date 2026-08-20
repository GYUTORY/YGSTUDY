---
title: tsc와 ts-node의 차이
tags: [language, typescript]
updated: 2025-11-01
---

# tsc와 ts-node의 차이

## 배경

TypeScript로 개발할 때 코드를 실행하는 방법은 크게 두 가지다. 하나는 JavaScript로 변환한 뒤 실행하는 방법(tsc), 다른 하나는 TypeScript를 바로 실행하는 방법(ts-node)이다.

### tsc가 필요한 이유

tsc는 TypeScript 공식 컴파일러다. 주요 역할은 TypeScript 코드를 JavaScript로 바꾸는 것이지만, 그 과정에서 하는 일이 더 있다.

**타입 검사와 정적 분석**
컴파일 시점에 코드의 타입 오류를 잡는다. 런타임에 터질 오류를 미리 찾아내 안정성을 높인다. 코드 구조를 분석해 문제가 될 만한 곳도 경고한다.

**프로덕션 배포**
브라우저나 Node.js 환경에서 돌아가는 JavaScript 파일을 만든다. 이때 타입 정보는 제거되고, 타겟 환경에 맞는 JavaScript 버전으로 바뀐다. 최적화된 코드라 배포 환경에서 효율적으로 동작한다.

**코드 변환과 호환성**
최신 JavaScript 문법을 구버전 JavaScript로 낮출 수 있다. async/await 같은 최신 문법도 ES5 환경에서 동작하도록 변환한다. 그래서 실행 환경을 가리지 않는다.

### ts-node가 필요한 이유

ts-node는 개발 과정의 생산성을 위한 도구다. TypeScript 파일을 중간 과정 없이 바로 실행한다.

**개발 속도 향상**
코드를 고칠 때마다 컴파일하고 실행하는 건 번거롭다. ts-node는 이 둘을 하나로 합쳐 결과를 곧바로 보여준다. 작은 변경을 테스트할 때 특히 쓸모 있다.

**REPL 환경**
대화형 실행 환경이 있어 TypeScript 코드를 즉석에서 테스트한다. JavaScript의 Node.js REPL처럼 TypeScript를 바로 실험해보는 환경을 만들어 준다.

**테스트와 디버깅**
테스트 코드를 쓰고 돌릴 때 컴파일 단계가 없으니 피드백이 빠르다. 디버깅할 때도 TypeScript 코드를 직접 실행하면서 문제를 짚는다.

## 핵심

### 1. tsc의 동작 방식

tsc는 TypeScript 소스 코드를 읽어 JavaScript 파일을 만든다. 이 과정은 크게 세 단계다.

**파싱과 타입 검사**
먼저 TypeScript 코드를 분석해 추상 구문 트리(AST)를 만든다. 여기서 문법 오류가 있는지 확인한다. 그 다음 타입 정보를 기반으로 코드의 타입 안정성을 검사한다. 인터페이스, 제네릭, 타입 별칭 등 TypeScript 타입 시스템 전체가 검증 대상이다.

**변환과 최적화**
타입 검사가 끝나면 TypeScript 고유의 문법을 걷어낸다. 인터페이스, 타입 별칭, enum의 타입 정보는 런타임에 필요 없으므로 삭제된다. 그리고 설정된 타겟 JavaScript 버전에 맞게 코드를 변환한다. ES2022 문법을 ES5로 낮추는 식이다.

**파일 생성**
변환된 JavaScript 코드를 파일로 저장한다. 설정에 따라 소스맵(.map 파일)과 타입 선언 파일(.d.ts)도 같이 나온다. 소스맵은 디버깅할 때 원본 TypeScript 코드를 짚어주고, 타입 선언 파일은 다른 프로젝트에서 이 코드를 쓸 때 타입 정보를 제공한다.

```bash
# 기본 사용법
npm install -g typescript

# 단일 파일 컴파일
tsc app.ts

# 프로젝트 전체 컴파일
tsc
```

**컴파일 예시**
```typescript
// app.ts
interface User {
    id: number;
    name: string;
}

const user: User = { id: 1, name: '홍길동' };
console.log(user.name);
```

위 코드를 컴파일하면 interface와 타입 정보가 제거된 JavaScript가 나온다:

```javascript
// app.js
"use strict";
const user = { id: 1, name: '홍길동' };
console.log(user.name);
```

### 2. ts-node의 동작 방식

ts-node는 TypeScript 파일을 메모리상에서 즉시 컴파일해 실행한다. 별도의 JavaScript 파일은 만들지 않는다.

**JIT 컴파일**
ts-node는 Just-In-Time 방식으로 동작한다. TypeScript 파일을 읽으면 내부에서 tsc를 호출해 JavaScript로 변환하는데, 그 결과를 파일로 저장하지 않고 메모리에 들고 있는다. 그리고 변환된 JavaScript를 Node.js에서 바로 실행한다.

**캐싱 메커니즘**
매번 전체 파일을 컴파일하면 느리다. 그래서 ts-node는 변경되지 않은 파일에 캐시를 쓴다. 파일이 수정되었을 때만 다시 컴파일한다. 초기 실행만 넘기면 그 뒤로는 빠른 속도를 유지한다.

**모듈 후킹**
Node.js의 모듈 시스템을 확장해 `.ts` 파일을 인식하게 만든다. `require()`나 `import`로 TypeScript 파일을 불러올 때 자동으로 컴파일해서 넘겨준다. 덕분에 JavaScript와 TypeScript 파일을 섞어서 쓸 수 있다.

```bash
# 기본 사용법
npm install -g ts-node

# TypeScript 파일 직접 실행
ts-node app.ts

# REPL 모드
ts-node
```

### 3. tsconfig.json의 역할

두 도구 모두 `tsconfig.json` 설정 파일을 참조한다. 이 파일이 TypeScript 컴파일러의 동작 방식을 제어한다.

**컴파일 옵션**
`compilerOptions`에서 타겟 JavaScript 버전, 모듈 시스템, 출력 디렉토리 등을 지정한다. `strict` 옵션을 켜면 타입 검사가 엄격해진다. `sourceMap` 옵션은 디버깅용 소스맵을 만들지 말지 결정한다.

**파일 포함/제외**
`include`로 컴파일 대상 파일을 지정하고, `exclude`로 제외할 파일을 명시한다. 보통 `node_modules`나 빌드 결과물 디렉토리는 제외한다.

**ts-node 특화 설정**
ts-node 전용 설정도 넣을 수 있다. `transpileOnly` 옵션을 켜면 타입 검사를 건너뛰고 변환만 해서 실행 속도가 올라간다.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "outDir": "./dist",
    "strict": true
  },
  "ts-node": {
    "transpileOnly": true  // 빠른 실행을 위해 타입 검사 생략
  }
}
```

## 예시

### 실제 개발 워크플로우

일반적인 TypeScript 프로젝트에서 두 도구를 함께 쓰는 방법을 보자.

**개발 단계**
코드를 쓰다가 빠른 테스트가 필요할 때는 ts-node를 쓴다. 파일을 수정하고 곧바로 실행해보면서 결과를 확인한다. 새로운 함수를 작성했다면 `ts-node app.ts`로 바로 실행해서 동작을 확인하는 식이다.

```bash
# 개발 중 빠른 테스트
ts-node src/index.ts

# 코드 수정 후 즉시 재실행
ts-node src/index.ts
```

**테스트 단계**
단위 테스트를 작성할 때도 ts-node가 쓸모 있다. 테스트 프레임워크와 함께 쓰면 TypeScript 테스트 코드를 직접 실행한다. 컴파일 단계를 거치지 않으니 테스트 실행 속도가 빠르다.

```json
// package.json
{
  "scripts": {
    "dev": "ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
```

**배포 단계**
프로덕션 환경에 배포할 때는 반드시 tsc로 컴파일한다. 타입 검사를 완료하고, 최적화된 JavaScript 파일을 생성한다. 생성된 JavaScript는 타입 정보가 없어 더 작고 빠르게 실행된다.

```bash
# 프로덕션 빌드
tsc

# 컴파일된 JavaScript 실행
node dist/index.js
```

### 성능과 최적화

**tsc의 성능 특성**
tsc는 전체 프로젝트를 컴파일하므로 초기에는 시간이 걸린다. 대신 한 번 컴파일하면 그 결과물을 계속 쓴다. 대규모 프로젝트에서는 증분 컴파일 기능을 켜서 변경된 부분만 다시 컴파일하면 속도가 올라간다.

```json
// tsconfig.json
{
  "compilerOptions": {
    "incremental": true,  // 증분 컴파일 활성화
    "tsBuildInfoFile": "./.tsbuildinfo"
  }
}
```

**ts-node의 성능 특성**
ts-node는 실행할 때마다 컴파일 과정을 거친다. 캐싱을 쓰긴 하지만 프로덕션 환경에서는 권장하지 않는다. 개발 환경에서 속도를 높이려면 `transpileOnly` 옵션을 쓴다. 타입 검사를 건너뛰고 변환만 하니 실행 속도가 크게 올라간다.

```json
// tsconfig.json
{
  "ts-node": {
    "transpileOnly": true,  // 타입 검사 생략으로 속도 향상
    "files": false
  }
}
```

**언제 어떤 도구를 사용할까**
개발 중에는 ts-node로 빠르게 코드를 테스트한다. 다만 주기적으로 tsc를 실행해 타입 오류가 없는지 확인해야 한다. CI/CD 파이프라인에서는 항상 tsc로 빌드해 타입 안정성을 보장한다. 이러면 개발 속도와 코드 품질을 둘 다 유지한다.

## 운영 팁

### 타입 검사와 실행 속도의 균형

개발하다 보면 타입 검사와 실행 속도 사이에서 고민하게 된다. ts-node는 기본적으로 타입 검사를 수행하면서 실행하기 때문에 느릴 수 있다.

**transpileOnly 옵션**
이 옵션을 켜면 타입 검사를 건너뛰고 단순히 TypeScript를 JavaScript로 변환만 한다. 실행 속도는 크게 올라가지만, 타입 오류를 감지하지 못한다. 그래서 개발 중에는 transpileOnly로 돌리고, 커밋 전에는 tsc로 타입 검사를 하는 게 좋다.

**캐싱 메커니즘**
ts-node는 컴파일 결과를 캐시에 저장한다. 파일이 변경되지 않으면 캐시된 결과를 재사용해 빠르게 실행된다. 캐시 디렉토리를 지정하면 여러 실행 간에도 캐시를 공유한다.

```bash
# 캐시 디렉토리 지정
ts-node --cachedir ./node_modules/.cache/ts-node app.ts
```

### 에러 처리 전략

**타입 오류와 런타임 오류의 차이**
TypeScript의 타입 시스템은 컴파일 시점의 오류를 잡아낸다. 런타임에 터지는 오류는 얘기가 다르다. tsc는 타입 오류가 있으면 컴파일을 중단하지만, ts-node는 설정에 따라 타입 오류가 있어도 실행을 계속한다.

**엄격 모드 설정**
tsconfig.json의 `strict` 옵션은 타입 검사를 엄격하게 수행한다. 켜두면 더 많은 오류를 사전에 발견한다. `noImplicitAny`, `strictNullChecks` 같은 세부 옵션도 함께 쓰면 코드 안정성이 그만큼 올라간다.

**타입 검사만 수행하기**
코드를 컴파일하지 않고 타입 검사만 하고 싶을 때가 있다. `tsc --noEmit` 명령을 쓰면 JavaScript 파일을 생성하지 않고 타입 검사만 수행한다. CI/CD 파이프라인에서 타입 검사 단계로 쓰기 좋다.

```bash
# 타입 검사만 수행
tsc --noEmit
```

## 참고

### 주요 차이점 비교

| 구분 | tsc | ts-node |
|------|-----|---------|
| **주요 목적** | TypeScript → JavaScript 변환 | TypeScript 직접 실행 |
| **파일 생성** | JavaScript 파일 생성 | 메모리 내에서 실행 |
| **사용 환경** | 프로덕션 빌드 | 개발 및 테스트 |
| **실행 방식** | 컴파일 후 실행 | 즉시 실행 |
| **타입 검사** | 항상 수행 | 선택 가능 |

### 상황별 선택 기준

| 상황 | 추천 도구 | 이유 |
|----------|-----------|------|
| **빠른 코드 테스트** | ts-node | 컴파일 없이 즉시 확인 |
| **배포용 빌드** | tsc | 최적화된 JavaScript 생성 |
| **CI/CD 빌드** | tsc | 타입 안정성 보장 |
| **REPL 실험** | ts-node | 대화형 환경 제공 |
| **타입 검사만 필요** | tsc --noEmit | 빌드 없이 타입만 확인 |

### 정리

tsc와 ts-node는 서로 대체하는 관계가 아니라 보완하는 관계다.

개발할 때는 ts-node로 빠르게 코드를 작성하고 테스트한다. 수정사항을 즉시 확인할 수 있어 생산성이 높아진다.

다만 프로덕션 환경에서는 반드시 tsc로 빌드해야 한다. 타입 검사를 완료하고 최적화된 코드를 생성해야 안정성과 성능이 보장된다.
