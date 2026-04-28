---
title: TypeScript tsconfig.json 옵션과 컴파일 동작 깊이 보기
tags: [language, typescript, 프로젝트-설정-및-컴파일러, tsconfig, configuration]
updated: 2026-04-28
---

# tsconfig.json 옵션과 컴파일 동작 깊이 보기

`tsconfig.json`은 단순히 컴파일러에 옵션을 넘기는 파일처럼 보이지만, 실제로는 모듈 해석 알고리즘, 타입 좁히기 규칙, 런타임 호환성, 빌드 캐시 동작을 동시에 결정한다. 그래서 옵션 하나를 잘못 넣으면 빌드는 통과하는데 런타임에서 모듈을 못 찾는다거나, 동일한 코드를 두 번 컴파일하면 결과가 달라지는 일이 생긴다. 이 문서는 tsconfig를 다루며 실제로 마주친 문제와, 그 문제가 왜 생겼는지를 옵션 의미와 함께 정리한 글이다.

## 파일 포함 규칙: files / include / exclude / extends

tsconfig는 어떤 파일을 컴파일 대상에 넣을지 결정하는 규칙이 의외로 복잡하다. 작은 차이가 "컴파일러는 통과하는데 일부 파일이 빠져 있다"라는 미묘한 상황을 만든다.

### 우선순위와 의미

`files`는 정확한 경로 목록이다. glob을 받지 않고, 여기에 적힌 파일은 무조건 포함된다. `include`는 glob을 받는 후보 목록이고, `exclude`는 `include` 결과에서 제외할 패턴이다. 둘이 동시에 있으면 동작은 다음과 같이 정리된다.

- `files`만 있고 `include`가 없으면 정확히 그 파일들과 그것들이 import한 파일만 들어간다.
- `files`도 `include`도 없으면 프로젝트 루트의 모든 `.ts/.tsx/.d.ts`(그리고 `allowJs`면 `.js/.jsx`)가 포함된다.
- `exclude`는 `include`에만 작용한다. `files`로 명시된 파일은 `exclude` 패턴에 걸려도 빠지지 않는다.

가장 자주 헷갈리는 지점은 `import`로 끌려 들어오는 파일이다. `exclude`에 `**/*.test.ts`를 넣어도, `src/foo.ts`가 `import './foo.test'`처럼 테스트 파일을 import하면 그 파일은 다시 컴파일 대상이 된다. `exclude`는 "초기 후보에서 빼라"이지 "절대 빌드하지 마라"가 아니다.

### extends 체인

`extends`는 여러 단계를 거칠 수 있다. 머지 규칙이 옵션마다 다르다는 점만 잘 기억하면 된다.

- `compilerOptions`는 얕은 머지다. 자식이 같은 키를 정의하면 부모 값을 통째로 덮어쓴다. `compilerOptions.paths`에 부모가 `{"@a/*": [...]}`을 넣고 자식이 `{"@b/*": [...]}`을 넣으면 결과는 `@b/*`만 남는다. `paths`를 합치고 싶다면 자식에서 부모 키까지 다시 적어야 한다.
- `include`, `exclude`, `files`, `references`는 자식이 정의하면 부모 값을 통째로 대체한다. 머지가 아니다.
- `extends`로 가리키는 경로는 상대 경로이거나 패키지 이름이다. 패키지 이름이면 노드 모듈 해석 규칙으로 찾는다. `@tsconfig/node20`처럼 공유 베이스를 패키지로 받는 식이 자주 쓰인다.

`extends`가 배열을 받기 시작한 건 5.0부터다. 그 전에는 한 단계씩 체인을 만들어야 한다. 베이스를 두 개 합치고 싶을 때 자주 막힌다.

## target / lib / module / moduleResolution

이 네 옵션은 한 묶음이다. 나눠서 보면 잘못된 조합을 만들기 쉽다.

### target과 lib의 차이

`target`은 출력 JS 문법 수준이다. ES2020을 넣으면 `??`, `?.`이 그대로 남고, ES2017이면 `async/await`은 남지만 `??`은 변환된다. 폴리필은 만들지 않는다. 즉 `target: ES2022`로 빌드하고 Node 14에서 돌리면 `Array.prototype.at`이 없어서 런타임 에러가 난다.

`lib`은 타입 정의의 범위다. `lib: ["ES2022"]`로 두면 `Array.prototype.at`을 타입 시스템이 안다. 보통 `target`을 정하면 `lib`도 같이 따라가는 기본값이 적용되지만, DOM이 필요하거나(브라우저 환경) DOM이 필요 없는데 빠뜨리고 싶다면(서버 환경, `setTimeout`은 `@types/node`로 가져옴) `lib`을 직접 명시해야 한다.

서버 코드에서 `lib: ["ES2022", "DOM"]`을 두면 `fetch`, `console`이 두 번 정의되고, 어떤 타입은 DOM 쪽이 우선되어 `@types/node` 타입과 어긋나는 일이 생긴다. 노드 전용이면 DOM은 빼는 게 안전하다.

### module과 moduleResolution

`module`은 컴파일러가 import/export를 어떤 모듈 시스템으로 변환할지 결정한다. `commonjs`면 `require/exports`로 바뀌고, `esnext`면 `import/export`가 그대로 남는다.

`moduleResolution`은 import 경로를 실제 파일로 매핑할 때 어떤 알고리즘을 쓰는지다. 이게 헷갈리는 이유는 값이 진화하면서 의미가 겹치기 때문이다.

- `node` (또는 `node10`): TypeScript의 클래식 노드 해석. CommonJS만 가정한다. `package.json`의 `main`만 본다. `.ts/.tsx`만 처리하고 확장자 없이 import할 수 있다.
- `node16`, `nodenext`: 노드의 최신 ESM 해석을 따른다. `package.json`의 `exports` 필드와 `type: "module"`을 본다. ESM 환경에서는 import할 때 확장자(`.js`)를 반드시 적어야 한다(원본이 `.ts`여도 `.js`로 적는 게 맞다). `.mts`는 ESM, `.cts`는 CJS, `.ts`는 가장 가까운 `package.json`의 `type`으로 결정된다.
- `bundler`: webpack, esbuild, vite 같은 번들러가 모듈을 해석하므로 컴파일러가 굳이 노드 규칙을 흉내내지 않아도 된다는 의미다. 확장자 없이 import해도 되고, `exports` 필드도 본다. `module`은 `esnext` 또는 `preserve`를 같이 쓴다.

`module: commonjs` + `moduleResolution: nodenext` 같은 조합은 동작하지 않는다. `nodenext`는 `module`도 `nodenext`여야 한다. 이걸 모르고 `moduleResolution`만 바꾸면 컴파일러가 옵션 충돌을 알려준다.

### .ts / .mts / .cts 동작

`node16` 이상에서는 파일 확장자가 출력 모듈 형식을 결정한다.

- `.mts` → 항상 ESM. 출력은 `.mjs`. `require`를 쓰면 에러.
- `.cts` → 항상 CommonJS. 출력은 `.cjs`. top-level `await`를 쓰면 에러.
- `.ts` → 가까운 `package.json`의 `type`을 따라간다. `type: "module"`이면 ESM, 아니면 CJS.

ESM 모드에서 `import './foo'`라고만 적으면 모듈 해석에 실패한다. 노드 ESM은 확장자 생략을 허용하지 않기 때문이다. `import './foo.js'`로 적어야 하고, 원본이 `foo.ts`라도 그렇게 적어야 한다. 처음 보면 어색한데, 이건 TypeScript가 출력 경로를 다시 쓰지 않는다는 원칙(타입 정보만 지운다) 때문이다.

## strict 하위 플래그

`strict: true`는 다음 7개를 한꺼번에 켜는 별칭이다. 큰 코드베이스에 한 번에 켜면 수천 개 에러가 쏟아지므로, 보통은 끄고 시작해서 하나씩 켠다.

1. `noImplicitAny`: 타입을 추론할 수 없는 매개변수, 변수에 암시적 `any`를 금지한다. 이게 첫 단계다. 여기서 걸리는 곳이 가장 많다. 라이브러리에 타입이 없어서 `any`로 흘러들어오는 경우가 많고, `// @ts-expect-error` 또는 명시적 `any`로 마킹하면서 진행한다.
2. `strictNullChecks`: `null/undefined`를 일반 타입에서 분리한다. 도입 효과가 가장 크고 충돌도 가장 많다. 옵셔널 체이닝과 nullish 연산자를 적극 쓰는 코드라면 비교적 잘 흡수되지만, 옛날 코드에서는 "변수가 정의됐는지 확신할 수 없는데 메서드를 부른다" 패턴이 광범위하게 깨진다.
3. `strictFunctionTypes`: 함수 매개변수 위치에서 contravariance를 강제한다. `(x: Animal) => void`에 `(x: Dog) => void`를 대입할 수 없게 된다. 콜백을 인자로 받는 API에서 의외로 깨지는 게 많다. 메서드 문법(`foo(x: T): void`)은 이 규칙에서 빠지고 함수 속성 문법(`foo: (x: T) => void`)에만 적용된다는 점을 알아두면 디버깅이 빨라진다.
4. `strictBindCallApply`: `bind`, `call`, `apply` 호출에서 타입 검사를 한다. 이건 거의 무난하게 켜진다.
5. `strictPropertyInitialization`: 클래스 인스턴스 속성이 생성자에서 초기화됐는지 검사한다. `strictNullChecks`가 켜져 있어야 동작한다. DI 프레임워크나 ORM 데코레이터로 속성을 채우는 코드에서 깨진다. 회피 방법으로 `!`(definite assignment) 또는 생성자에서 명시적 초기화를 쓴다.
6. `noImplicitThis`: 함수 안에서 `this`가 암시적 `any`로 추론되면 에러다. 콜백에 `function`을 쓰는 옛날 패턴(jQuery 류)에서 잡힌다.
7. `useUnknownInCatchVariables`: `catch (e)`에서 `e`의 타입이 `any`가 아니라 `unknown`이 된다. 4.4부터의 기본이다. catch 블록에서 `e.message`로 바로 쓰는 코드가 모두 깨진다. `if (e instanceof Error)` 같은 좁히기를 강제한다.

마이그레이션 순서는 보통 `noImplicitAny` → `strictNullChecks` → 나머지다. `strictNullChecks`를 가장 마지막에 켜고 싶은 유혹이 들지만, `noImplicitAny`가 켜진 상태에서 `strictNullChecks`가 꺼져 있으면 새 코드가 또 `null` 가정 없이 작성되어 부채가 더 쌓인다. 가능하면 둘을 빠르게 묶어서 진행하는 게 낫다.

## noUncheckedIndexedAccess와 exactOptionalPropertyTypes

이 둘은 `strict`에 포함되지 않은 추가 엄격성 옵션이다. 켰을 때 깨지는 패턴이 잘 알려져 있어 도입 결정 전에 살펴보는 게 낫다.

### noUncheckedIndexedAccess

배열, 객체에 인덱스 접근(`arr[0]`, `obj[key]`)했을 때 결과 타입에 `undefined`가 합쳐진다. `string[]`의 인덱스 접근은 `string | undefined`가 된다. 의미 있는 안전장치인데, 다음 패턴이 광범위하게 깨진다.

```typescript
const items: number[] = [1, 2, 3];

// 깨진다: items[0]는 number | undefined
const sum = items[0] + items[1];

// for 루프 인덱스도 마찬가지
for (let i = 0; i < items.length; i++) {
  // items[i]는 number | undefined
  doSomething(items[i]);
}

// Record<string, T>에 키로 접근
const config: Record<string, string> = { host: 'localhost' };
config['host'].toUpperCase();  // string | undefined
```

`for...of`나 `forEach`는 영향이 없다(요소 타입을 직접 받기 때문). 인덱스 기반 루프를 쓰던 코드만 깨진다. 대부분은 변수에 한 번 받아 좁히기를 추가하는 식으로 해결된다.

```typescript
const first = items[0];
if (first !== undefined) {
  // 여기서는 number
}
```

배열 destructuring도 영향을 받는다. `const [a, b] = arr`에서 `a`, `b`는 `T | undefined`다.

### exactOptionalPropertyTypes

`?` 옵셔널 속성에 `undefined`를 명시적으로 대입할 수 없게 만든다. 평소 같으면 동일하게 다뤄지던 두 가지가 분리된다.

```typescript
interface User {
  name?: string;
}

// 평소: 둘 다 허용
const a: User = {};                   // 속성 없음
const b: User = { name: undefined };  // 속성 있고 값이 undefined

// exactOptionalPropertyTypes: true 면 b는 에러
```

이 차이는 `Object.keys`나 직렬화 결과가 달라지기 때문에 실무에서 의미가 있다. 그런데 실수로 깨지는 코드가 많다. `delete obj.name`이나 `obj.name = undefined`를 같은 의미로 쓰던 코드, 옵셔널 인자에 명시적 `undefined`를 넘기던 호출이 모두 잡힌다.

```typescript
function foo(opts: { timeout?: number }) {}

foo({ timeout: undefined });  // 에러
foo({});                       // OK
```

이 옵션을 켜면 라이브러리 타입 정의와도 자주 부딪힌다. 어떤 라이브러리는 `{ x?: T }`를 `{ x?: T | undefined }`처럼 가정하고 타입을 만들어 둔다. 그래서 도입 비용이 의외로 크다. 신규 프로젝트에는 켜둘 만하지만, 기존 코드베이스에 후행 도입할 때는 별도 모듈부터 시작해 점진 확장하는 게 안전하다.

## paths / baseUrl의 한계

`paths`와 `baseUrl`은 모듈 별칭을 만든다. `@/utils/foo` 같은 경로를 컴파일러가 `src/utils/foo.ts`로 해석한다.

```json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"],
      "@shared/*": ["../shared/*"]
    }
  }
}
```

여기서 가장 자주 막히는 부분은 이 별칭이 **타입 검사에만 적용된다**는 점이다. 출력된 JS 파일에는 `import { x } from '@/utils/foo'` 그대로 남는다. 노드는 `@/utils/foo`를 모듈로 해석하지 못한다. 즉 컴파일은 통과하는데 런타임에 `Cannot find module '@/utils/foo'`가 난다.

해결 방법은 환경에 따라 갈린다.

- **번들러를 쓰는 경우** (webpack, vite, esbuild): 번들러 설정에 동일한 별칭을 다시 적어야 한다. 컴파일러의 `paths`와 번들러의 alias가 따로 동작하기 때문이다. vite는 `resolve.alias`, webpack은 `resolve.alias`, esbuild는 `alias` 옵션이다.
- **컴파일된 JS를 그대로 노드에서 실행하는 경우**: `tsc-alias`로 후처리하거나, 실행 시 `tsconfig-paths/register`를 로더로 등록해야 한다. `tsc-alias`는 출력된 JS 파일의 import 경로를 실제 상대 경로로 바꿔준다. `tsconfig-paths`는 노드의 모듈 해석에 별칭을 끼워넣는다. 둘 중 무엇을 쓰든 별도 의존성이 필요하다.
- **`ts-node`나 `tsx`로 실행하는 경우**: `ts-node`는 `tsconfig-paths`를 옵션으로 켤 수 있고, `tsx`는 `paths`를 직접 인식한다.

번들 결과물에 dynamic import(`import('./foo')`)나 `require`를 직접 넣는다면 별칭 변환에서 빠지는 경우가 있다. `tsc-alias`는 이 두 가지도 변환하지만 동적 경로 문자열 안의 별칭은 변환하지 못한다.

## Project References와 incremental 빌드

큰 모노레포에서 가장 흔한 문제는 빌드 시간이다. Project References(`references`)와 `composite`는 이 문제를 풀기 위한 도구다.

### composite의 의존성

`composite: true`를 켜면 다음이 강제된다.

- `declaration: true`가 강제로 켜진다. `.d.ts`를 만들지 않으면 다른 프로젝트가 이 프로젝트의 타입을 모를 수 없다.
- `incremental: true`가 강제로 켜진다. 빌드 정보 캐시를 만든다.
- 모든 입력 파일이 `files` 또는 `include`로 명시되어야 한다. 컴파일러가 의존성 그래프를 정적으로 분석할 수 있어야 하기 때문이다.

`tsc -b`(빌드 모드)는 `references`로 연결된 프로젝트들을 의존성 순서대로 빌드한다. 빌드 결과물의 `.d.ts`를 다음 프로젝트가 참조한다. 캐시는 각 프로젝트의 `tsBuildInfoFile`(기본값은 `outDir`의 `.tsbuildinfo`)에 저장된다.

`declarationMap: true`를 같이 켜면 IDE에서 "정의로 이동"을 했을 때 빌드 결과물의 `.d.ts`가 아니라 원본 `.ts`로 점프한다. 모노레포에서 이게 없으면 매번 `.d.ts`만 보게 되어 작업이 답답해진다.

`outFile`은 `composite`와 함께 쓸 수 없다. `outFile`은 모든 출력을 한 파일에 모으는 옵션인데, 이건 모듈 시스템(`commonjs`, `esm`)에서는 사용할 수 없다. AMD/SystemJS에서만 의미가 있어서 현대 프로젝트에서는 거의 안 쓴다.

### incremental 캐시 동작

`incremental: true`만 켜도(`composite` 없이) 빌드 캐시가 생긴다. `.tsbuildinfo` 파일에 파일 단위 의존성 그래프, 시그니처 해시, 타입 검사 결과가 저장된다. 다음 빌드는 변경된 파일과 그 의존성만 다시 검사한다.

캐시가 깨지는 흔한 이유:

- `tsBuildInfoFile` 경로를 옮기거나 정리하면 처음부터 다시 빌드한다.
- `compilerOptions`가 바뀌면 캐시 일부가 무효가 된다. 옵션 변경에 보수적이다.
- TypeScript 버전이 바뀌면 캐시는 무시된다.
- 파일 mtime만 바뀌고 내용은 같으면 시그니처가 같아 다음 단계 검사가 생략된다.

CI에서 `.tsbuildinfo`를 캐시해 두면 빌드 시간을 크게 줄일 수 있는데, 캐시 키에 `tsconfig.json`과 의존성 lock 파일을 같이 넣어야 한다. 그러지 않으면 옵션이 바뀐 빌드를 옛날 캐시로 진행해 결과가 어긋난다.

## verbatimModuleSyntax / isolatedModules / preserveValueImports

이 세 가지는 "TypeScript가 import를 멋대로 지우거나 바꾸지 못하게 한다"라는 같은 결을 공유한다. 그래서 자주 묶여서 등장한다.

### isolatedModules

각 파일을 독립적으로 트랜스파일할 수 있는지 검사한다. 의미는 "Babel, esbuild, swc 같은 트랜스파일러가 한 파일만 보고 변환할 수 있느냐"다. 다음을 금지한다.

- 타입만 re-export: `export { Foo } from './foo'`에서 `Foo`가 타입이면 에러. `export type { Foo } from './foo'`로 명시해야 한다.
- `const enum`: 다른 파일의 enum 값을 인라인하는데, 단일 파일만 봐서는 그 값이 뭔지 알 수 없다.
- 네임스페이스 병합 같은 일부 패턴.

번들러를 쓰는 프로젝트라면 거의 켜두는 게 맞다. 안 켜두면 어떤 코드는 `tsc`로는 통과하지만 esbuild나 swc로는 깨진다.

### preserveValueImports와 importsNotUsedAsValues (구버전)

TypeScript는 기본적으로 "사용되지 않는 import를 지우는" 동작을 한다. 그런데 이게 사이드 이펙트가 있는 모듈(`import './setup'`처럼 등록만 하는 경우)이나, Vue/Svelte처럼 템플릿에서 값을 쓰지만 컴파일러는 사용을 못 보는 경우에 문제가 된다.

옛날에는 `importsNotUsedAsValues: 'preserve'`나 `preserveValueImports: true`로 풀어줬다. 둘 다 5.0부터 deprecated다.

### verbatimModuleSyntax

5.0에서 도입되어 위 두 옵션을 대체한다. 동작은 단순하다. **`import type`은 지우고, 일반 `import`는 절대 건드리지 않는다.** "값으로 쓰이지 않는 import를 자동으로 type-only로 바꾼다"는 추측을 없앤다.

```typescript
// 컴파일러가 추측하지 않는다
import { Foo } from './foo';        // 출력에 그대로 남는다
import type { Bar } from './bar';   // 출력에서 사라진다

// 둘이 섞인 경우 - 에러
import { Foo, type Bar } from './baz';  // verbatim에서는 OK (5.0+)
```

이 옵션의 부수 효과 하나는 CJS와 ESM 출력 사이에서 컴파일러가 "어떤 import를 require로 바꿀지"를 더 이상 결정하지 않는다는 점이다. 즉 `module`을 `commonjs`로 두고 `verbatimModuleSyntax: true`로 두면 충돌한다. 노드 ESM에 진입한 프로젝트(`module: nodenext`)에서 같이 쓰는 게 자연스럽다.

`isolatedModules`와 `verbatimModuleSyntax`를 함께 쓰면, 트랜스파일러가 봐도 일관된 결과를 내고, 컴파일러가 import를 임의로 지우지 않는다. 모노레포에서 권장 조합이다.

## 자주 마주치는 트러블슈팅

**증상**: ESM 프로젝트에서 `Cannot find module './foo' or its corresponding type declarations`.
**원인**: `moduleResolution: nodenext`인데 import에 확장자가 없다.
**해결**: `import './foo.js'`처럼 `.js` 확장자를 적는다. 원본이 `.ts`여도 그렇다.

**증상**: 컴파일은 통과하는데 노드에서 `Cannot find module '@/foo'`.
**원인**: `paths`가 런타임에 적용되지 않는다.
**해결**: 번들러 alias를 추가하거나, `tsc-alias`로 출력 후처리, 또는 실행 시 `tsconfig-paths/register`.

**증상**: `for (let i = 0; i < arr.length; i++) { doX(arr[i]) }`에서 갑자기 타입 에러.
**원인**: `noUncheckedIndexedAccess`가 켜졌다.
**해결**: 변수에 받아 좁히기, 또는 `for...of`로 변경.

**증상**: `delete obj.foo` 또는 `obj.foo = undefined` 에러.
**원인**: `exactOptionalPropertyTypes`가 켜졌다.
**해결**: 옵셔널 타입을 `foo?: T | undefined`로 명시하거나, 의도가 "속성 자체를 없애기"라면 `delete`를 유지하되 타입을 그렇게 정의한다.

**증상**: `tsc -b`가 같은 프로젝트를 매번 처음부터 빌드한다.
**원인**: `composite`나 `incremental`이 안 켜졌거나, `tsBuildInfoFile`이 정리되거나 옵션이 자주 바뀐다.
**해결**: `composite: true` 명시, `tsBuildInfoFile` 경로 안정화, CI 캐시 키에 `tsconfig.json` 포함.

**증상**: `tsc`로는 빌드되는데 esbuild/swc로는 `Type-only import` 관련 에러.
**원인**: `isolatedModules` 위반.
**해결**: 타입만 사용하는 import를 `import type`으로 바꾸고 `isolatedModules: true`를 켜서 사전 검출.

**증상**: catch 블록에서 `e.message`가 갑자기 에러.
**원인**: `useUnknownInCatchVariables`(strict 또는 4.4+ 기본).
**해결**: `if (e instanceof Error) ...`로 좁히고 사용.

## 옵션 카테고리별 빠른 참조

### 출력 동작

| 옵션 | 의미 | 주의 |
|------|------|------|
| `target` | 출력 JS 문법 수준 | 폴리필은 없다. 런타임이 지원 안 하면 에러 |
| `module` | import/export 변환 형식 | `nodenext`는 `moduleResolution`도 같아야 함 |
| `outDir` | 출력 디렉토리 | `rootDir` 밖의 파일이 포함되면 출력 구조가 어긋남 |
| `noEmit` | 컴파일 결과를 쓰지 않음 | 타입 검사만 할 때 사용 |
| `declaration` | `.d.ts` 생성 | `composite`면 강제로 켜짐 |
| `declarationMap` | `.d.ts.map` 생성 | IDE 점프 정확도가 올라감 |
| `sourceMap` | `.js.map` 생성 | 디버깅에 필요 |

### 모듈 해석

| 옵션 | 의미 | 주의 |
|------|------|------|
| `moduleResolution` | 경로 → 파일 매핑 알고리즘 | `node`/`node16`/`nodenext`/`bundler` |
| `baseUrl` | 비-상대 import의 기준 | `paths` 없이 단독으로는 잘 안 씀 |
| `paths` | 별칭 매핑 | 런타임에 적용되지 않음 |
| `resolveJsonModule` | `.json` import 허용 | `module: commonjs`에서만 자동 동작 |
| `esModuleInterop` | CJS 모듈을 ESM처럼 import | 거의 항상 true |
| `allowSyntheticDefaultImports` | 타입 검사용 default import 허용 | `esModuleInterop: true`면 자동 |

### 타입 검사 강도

| 옵션 | strict 포함 | 도입 비용 |
|------|-------------|-----------|
| `noImplicitAny` | 예 | 보통 |
| `strictNullChecks` | 예 | 큼 |
| `strictFunctionTypes` | 예 | 작음 |
| `strictBindCallApply` | 예 | 작음 |
| `strictPropertyInitialization` | 예 | DI/ORM에서 큼 |
| `noImplicitThis` | 예 | 작음 |
| `useUnknownInCatchVariables` | 예 | 보통 |
| `noUncheckedIndexedAccess` | 아니오 | 큼 |
| `exactOptionalPropertyTypes` | 아니오 | 큼 |
| `noImplicitReturns` | 아니오 | 작음 |
| `noFallthroughCasesInSwitch` | 아니오 | 작음 |

### 트랜스파일러 호환성

| 옵션 | 역할 |
|------|------|
| `isolatedModules` | 단일 파일 트랜스파일 가능성 검사 |
| `verbatimModuleSyntax` | import 형태를 그대로 유지 |
| `importsNotUsedAsValues` | 5.0+ deprecated. `verbatimModuleSyntax`로 대체 |
| `preserveValueImports` | 5.0+ deprecated. `verbatimModuleSyntax`로 대체 |

### 빌드 최적화

| 옵션 | 역할 | 주의 |
|------|------|------|
| `incremental` | 빌드 캐시 활성 | `.tsbuildinfo` 생성 |
| `composite` | Project References 사용 | `declaration`, `incremental` 강제 |
| `tsBuildInfoFile` | 캐시 파일 경로 | CI에서 캐시할 때 명시 |
| `skipLibCheck` | `node_modules`의 `.d.ts` 검사 생략 | 거의 항상 true. 라이브러리 간 충돌 회피 |
