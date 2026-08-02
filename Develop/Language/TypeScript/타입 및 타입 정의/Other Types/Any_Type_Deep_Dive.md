---
title: TypeScript any 타입 심화
tags: [language, typescript, 타입-및-타입-정의, typescript-types, other-types, any, deep-dive]
updated: 2026-05-02
---

# TypeScript any 타입 심화

## 들어가며

`any`는 단순히 "타입 검사를 끄는 키워드"가 아니다. 컴파일러 내부에서는 다른 타입과 전혀 다른 방식으로 처리된다. `unknown`이 도입된 이후에도 `any`가 사라지지 않는 데에는 이유가 있고, 라이브러리 타입 정의를 들춰보면 의도적으로 `any`를 쓴 자리가 곳곳에 보인다. 이 문서는 컴파일러가 `any`를 어떻게 다루는지, 그리고 실무에서 마주치는 함정들을 정리한다.

## any가 타입 시스템에서 갖는 특수 지위

### top type이자 bottom type처럼 동작

타입 이론에서 top type은 모든 타입의 상위 타입(모든 값이 할당 가능), bottom type은 모든 타입의 하위 타입(어떤 변수에도 할당 가능)을 말한다. TypeScript에서 top type은 `unknown`, bottom type은 `never`다. `any`는 이 구분을 무시하고 양쪽 모두처럼 행동한다.

```typescript
// any → 다른 타입으로 할당 가능 (bottom처럼)
const a: any = 1;
const s: string = a;     // OK
const n: number = a;     // OK
const u: { x: number } = a; // OK

// 다른 타입 → any로 할당 가능 (top처럼)
const b: any = "hello";
const c: any = { x: 1 };
const d: any = null;
```

`unknown`은 top type이지만 bottom처럼 동작하지 않는다. 즉, `unknown` 값을 다른 구체 타입에 그냥 할당할 수 없다.

```typescript
const u: unknown = 1;
const s: string = u;
// error TS2322: Type 'unknown' is not assignable to type 'string'.
```

이 한 줄 차이가 `any`와 `unknown`의 본질이다. `any`는 양방향 할당이 무조건 통과되므로 한 번 사용된 시점부터 타입 검사가 사실상 비활성화된다. 반면 `unknown`은 들어오는 건 다 받지만, 나갈 때는 좁히기(narrowing)나 단언이 필요하다.

### 컴파일러 내부 동작 차이

`tsc`의 체커(`checker.ts`)에서 `any`는 `TypeFlags.Any` 플래그를 가진다. 두 타입을 비교하는 `isTypeAssignableTo` 단계에서 한쪽이 `Any`이면 비교 자체를 스킵하고 true를 반환한다. 이 단축 평가가 곳곳에서 적용되기 때문에 객체 프로퍼티 접근, 함수 호출, 인덱스 시그니처 어디에서도 즉시 통과된다.

```typescript
declare const x: any;
x.foo.bar.baz();        // OK
x();                    // OK
x[0][1][2];             // OK
new x();                // OK
```

`unknown`은 같은 단축 평가가 없기 때문에 모든 접근에서 에러가 발생한다.

## any 전염 원리

`any`는 표현식 단위로 전파된다. `any` 값을 만지는 모든 표현식의 결과 타입이 다시 `any`로 추론된다. 이 전염은 코드 한 줄 단위가 아니라 호출 그래프 전체로 퍼진다.

### 함수 반환값을 통한 전파

```typescript
function getConfig(): any {
    return JSON.parse(process.env.CONFIG ?? "{}");
}

const port = getConfig().server.port;
// port의 타입: any

const portNumber: number = port * 2 + 1;
// portNumber도 any로 추론됨
// number 타입에 any를 할당하는 것이 허용되어 컴파일 통과
// 런타임에 NaN이 되어도 잡히지 않음
```

`port * 2 + 1`은 산술 연산이지만 한쪽 피연산자가 `any`이므로 결과 타입도 `any`다. 명시적으로 `: number`라고 적었어도 `any`는 `number`에 할당 가능하므로 타입 단언처럼 동작한다.

### 객체 프로퍼티를 통한 전파

```typescript
interface Container {
    payload: any;
}

const c: Container = { payload: { user: { id: "abc" } } };

const userId: number = c.payload.user.id;
// userId의 선언 타입은 number지만 RHS는 any
// 컴파일 통과, 런타임에 string 값이 number 변수에 들어감
```

타입 정의에 `any`가 한 자리만 있어도 그 객체를 거치는 모든 후속 접근이 `any` 영역으로 들어간다. 이걸 막는 게 `unknown`을 페이로드 자리에 넣는 것이다.

### 배열 요소를 통한 전파

```typescript
const items: any[] = JSON.parse(rawJson);
const first = items[0];          // first: any
const mapped = items.map(x => x.name);
// mapped: any[]
// x도 any로 추론되어 .name 접근이 검증 없이 통과
```

`Array.prototype.map`의 시그니처가 `<U>(callbackfn: (value: T, ...) => U): U[]`인데, `T`가 `any`로 묶이면 `U`도 `any`로 흘러간다. `noImplicitAny`가 켜져 있어도 이미 `any[]`로 선언된 배열에서 추론된 `any`는 명시된 타입에서 비롯된 것이므로 에러가 나지 않는다.

### 디버깅 방법

전염의 진원지를 찾을 때는 IDE에서 변수 위에 마우스를 올려 `any`로 추론된 가장 위쪽 노드를 추적한다. CLI에서는 `tsc --noErrorTruncation` 옵션과 함께 `// $ExpectType`을 다음과 같이 박아 확인한다.

```typescript
const x = someExpr;
type T = typeof x;
// 호버해서 T가 any인지 확인
```

또는 `tsc`에 `--listFiles --traceResolution` 같은 옵션을 켜고, 의심되는 외부 모듈의 `.d.ts`가 어디서 로드되는지 추적한다. 외부 패키지의 타입 정의가 누락돼 암묵적 `any`가 흘러나오는 경우가 가장 흔한 원인이다.

## noImplicitAny와 strict의 동작 방식

`strict: true`는 `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `alwaysStrict`, `useUnknownInCatchVariables`를 한꺼번에 켠다. 이 중 `noImplicitAny`는 컴파일러가 타입을 추론하려다 실패해서 `any`를 backfill한 자리에서 에러를 내는 옵션이다.

### 암묵적 any가 발생하는 시점

#### 콜백 매개변수에서 컨텍스트 추론이 실패할 때

```typescript
// noImplicitAny: true
function noop() {}

const fn = function(x) {  // error TS7006: Parameter 'x' implicitly has an 'any' type.
    return x;
};

[1, 2, 3].forEach(function(x) {
    // 여기 x는 number로 추론됨 (Array<number>.forEach의 콜백 시그니처에서 컨텍스트 흘러들어옴)
});
```

콜백이 컨텍스트 타입을 받지 못하면 매개변수가 암묵적 `any`가 된다. `Array<number>.forEach`처럼 호출 위치에서 시그니처가 정해지면 추론이 흘러들어간다.

#### 인덱스 시그니처가 없는 객체에 대한 동적 인덱싱

```typescript
const obj = { a: 1, b: 2 };
const key: string = "a";
const val = obj[key];
// noUncheckedIndexedAccess가 꺼져 있어도
// 정의된 키가 아닌 임의의 string으로 접근하면
// error TS7053: Element implicitly has an 'any' type because expression of type 'string' can't be used to index type '{ a: number; b: number; }'.
```

이걸 우회하려고 `as keyof typeof obj`를 끼얹는 코드가 많은데, 잘못된 단언으로 `obj[k]`가 `undefined`인데 `number`로 취급되는 사고가 자주 발생한다. `noUncheckedIndexedAccess`까지 켜면 인덱스 결과가 항상 `T | undefined`로 잡혀서 더 안전하다.

#### JSON.parse, fetch().json()

```typescript
const parsed = JSON.parse('{"x":1}');
// parsed의 타입: any (lib.es5.d.ts에서 JSON.parse의 반환 타입이 any로 정의됨)

const res = await fetch("/api");
const data = await res.json();
// data의 타입: any (Body.json(): Promise<any>)
```

`JSON.parse`와 `Body.json`의 반환 타입은 `lib.es5.d.ts`, `lib.dom.d.ts`에서 `any`로 박혀 있다. 이건 `noImplicitAny`로 잡히지 않는다. 명시적 `any`이기 때문이다. 이걸 잡으려면 직접 래퍼를 만들어 `unknown`을 반환하게 해야 한다.

```typescript
function parseJson(text: string): unknown {
    return JSON.parse(text);
}

async function fetchJson(url: string): Promise<unknown> {
    const r = await fetch(url);
    return r.json();
}
```

#### 외부 모듈에 타입 정의가 없을 때

```typescript
import legacy from "old-lib";
// noImplicitAny: true
// error TS7016: Could not find a declaration file for module 'old-lib'.
//   '.../old-lib/index.js' implicitly has an 'any' type.
```

`@types/old-lib` 패키지를 받거나, `src/types/old-lib.d.ts`에 `declare module 'old-lib';`를 추가하면 `any`로 통과시킬 수 있다. 후자는 모듈 전체를 `any`로 만드는 우회로다.

#### this 바인딩이 모호한 클래스 메서드

`noImplicitThis`가 켜져 있으면, 분리된 함수에서 `this`가 `any`로 추론되는 자리도 에러가 난다.

```typescript
class Foo {
    val = 10;
    show() { console.log(this.val); }
}

const f = new Foo();
const bare = f.show;
// bare(): this가 any가 되어 에러 발생
```

## any[] vs unknown[] vs Array&lt;any&gt; 그리고 readonly any[] 함정

### any[]와 Array&lt;any&gt;는 같은 타입

문법만 다를 뿐 컴파일러는 동일하게 처리한다.

```typescript
const a: any[] = [];
const b: Array<any> = [];
type Same = typeof a extends typeof b ? true : false; // true
```

### any[]는 안에 들어 있는 모든 메서드 호출을 통과시킨다

```typescript
const arr: any[] = [];
arr.push(1);
arr.somethingThatDoesNotExist();  // OK, 런타임 에러
arr[0].foo.bar();                  // OK, 런타임 에러
```

### unknown[]는 요소 접근 시점에서 좁히기를 강제한다

```typescript
const arr: unknown[] = [];
const x = arr[0];
x.toFixed(2);
// error TS18046: 'x' is of type 'unknown'.

if (typeof x === "number") {
    x.toFixed(2); // OK
}
```

`JSON.parse` 결과를 받을 때 `any[]` 대신 `unknown[]`을 쓰면 요소를 만질 때마다 검증을 강제한다.

### readonly any[] 함정

`readonly any[]`는 한 번 선언되면 가변 배열로 취급되는 자리에 넘길 수 없다.

```typescript
function take(xs: any[]): void {}

const r: readonly any[] = [1, 2, 3];
take(r);
// error TS4104: The type 'readonly any[]' is 'readonly' and cannot be assigned to the mutable type 'any[]'.
```

`any`가 들어 있어도 `readonly` 변경자는 살아 있다. 이건 의외로 자주 걸리는데, `Object.freeze` 결과나 `as const` 배열을 다른 함수로 넘길 때 발견된다. 함수 시그니처를 `readonly any[]`로 바꾸거나, 호출부에서 `[...r]`로 풀어야 한다.

### 빈 배열 리터럴의 함정

```typescript
const xs = [];
// noImplicitAny: true에서도 통과 (지역 추론으로 시작)
xs.push(1);
xs.push("a");
// xs의 타입은 점차 (number | string)[]로 evolution

function fn() {
    const xs = [];
    return xs;
}
// fn의 반환 타입: any[]
// 함수 경계를 넘어가면 evolution이 닫혀 any[]로 고정
```

evolving array는 함수 내부 지역 변수에서만 동작한다. 반환되는 순간 `any[]`로 굳어진다. 이걸 모르면 빈 배열을 반환하는 헬퍼 함수가 호출 측에 `any` 전염을 퍼뜨린다.

## ESLint 규칙 실전 설정

`@typescript-eslint`의 `no-explicit-any`와 `no-unsafe-*` 계열은 `any`를 잡는 두 축이다. `no-explicit-any`는 명시적으로 적은 `any`를, `no-unsafe-*`는 `any` 값을 사용하는 모든 자리를 잡는다.

### 권장 설정

```json
{
    "rules": {
        "@typescript-eslint/no-explicit-any": ["error", { "fixToUnknown": false, "ignoreRestArgs": false }],
        "@typescript-eslint/no-unsafe-assignment": "error",
        "@typescript-eslint/no-unsafe-member-access": "error",
        "@typescript-eslint/no-unsafe-call": "error",
        "@typescript-eslint/no-unsafe-return": "error",
        "@typescript-eslint/no-unsafe-argument": "error"
    }
}
```

`no-unsafe-*`는 타입 정보가 필요하므로 `parserOptions.project`가 필수다. `tsconfig.json`을 가리키지 않으면 규칙이 동작하지 않는다.

### 예외 처리 패턴

테스트 코드, 마이그레이션 중인 파일, 외부 라이브러리 어댑터에서는 일시적으로 끄는 게 현실적이다.

```typescript
// 한 줄 비활성화
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function bridge(x: any): unknown {
    return x;
}
```

전역으로 끄는 대신, `overrides`로 디렉터리 단위 예외를 두는 편이 유지보수가 쉽다.

```json
{
    "overrides": [
        {
            "files": ["src/legacy/**/*.ts", "tests/**/*.ts"],
            "rules": {
                "@typescript-eslint/no-explicit-any": "off",
                "@typescript-eslint/no-unsafe-assignment": "off"
            }
        }
    ]
}
```

`fixToUnknown: true`를 켜면 `--fix`가 명시적 `any`를 자동으로 `unknown`으로 바꿔준다. 큰 코드베이스의 첫 정리에는 유용하지만, 자동 변환 후 컴파일 에러가 한꺼번에 터지므로 한 디렉터리씩 끊어서 적용해야 한다.

## declare module에서 any 줄이기

타입 정의가 없는 모듈을 처음 도입할 때는 `declare module 'xxx';` 한 줄로 모듈 전체를 `any`로 만들어 우선 컴파일을 통과시킨다.

```typescript
// src/types/legacy-lib.d.ts
declare module "legacy-lib";
// 이 시점부터 import 한 모든 것이 any
```

이 상태로 두면 호출 측 코드 전체가 `any` 전염에 노출된다. 점진적으로 좁혀가는 패턴은 다음과 같다.

### 1단계: 사용하는 export만 선언

```typescript
declare module "legacy-lib" {
    export function process(input: any, opts?: any): any;
    export const VERSION: string;
}
```

### 2단계: 입력 타입부터 명시 (반환은 unknown으로)

```typescript
declare module "legacy-lib" {
    export interface ProcessOptions {
        retries?: number;
        timeout?: number;
    }
    export function process(input: string, opts?: ProcessOptions): unknown;
    export const VERSION: string;
}
```

### 3단계: 반환 타입 좁히기

```typescript
declare module "legacy-lib" {
    export interface ProcessResult {
        ok: boolean;
        data: unknown;
    }
    export function process(input: string, opts?: ProcessOptions): Promise<ProcessResult>;
}
```

이 단계 작업의 핵심은 "외부 데이터가 들어오는 자리는 `unknown`, 내부에서 의미가 정해진 자리는 구체 타입"이라는 원칙이다. 처음부터 모든 필드를 추론해 적으려 하면 라이브러리 내부 변경에 깨지기 쉽다.

## Function, object, {}와 any의 실제 차이

이름이 비슷해 보이지만 컴파일에서 전혀 다르게 동작한다.

### Function

`Function`은 lib에 정의된 모든 함수의 상위 타입이다. 호출은 가능하지만 매개변수와 반환이 모두 `any`로 잡힌다.

```typescript
const f: Function = (x: number) => x + 1;
const r = f(1, 2, 3);  // OK, r: any
f.bind(null, 1);       // OK
```

`@typescript-eslint/no-unsafe-function-type` 규칙이 권장되는 이유는 `Function`이 사실상 `(...args: any[]) => any`와 같기 때문이다. 시그니처를 알 수 있다면 `(x: number) => number` 같은 구체 함수 타입을 써야 한다.

### object (소문자)

`object`는 원시 타입을 제외한 모든 비-원시 값. 프로퍼티 접근은 막혀 있다.

```typescript
function fn(o: object) {
    o.foo;
    // error TS2339: Property 'foo' does not exist on type 'object'.
}

fn({ a: 1 });   // OK
fn([1, 2]);     // OK
fn("hello");    // error: string은 object가 아님
```

값을 받기는 하지만 속을 들여다볼 수 없는 타입이다. "임의의 객체를 통째로 패스스루하고 안은 안 본다"는 자리에 적합하다.

### {} (빈 객체)

`{}`는 `null`과 `undefined`를 제외한 모든 값을 받는다. `string`, `number`도 할당 가능하다.

```typescript
const a: {} = 1;          // OK
const b: {} = "hello";    // OK
const c: {} = { x: 1 };   // OK
const d: {} = null;       // error
```

`{}`도 프로퍼티 접근은 사실상 막혀 있다(없는 프로퍼티 에러). `unknown`이 도입되기 전에는 `{}`가 top type 대용으로 쓰였지만, `null`/`undefined`를 거르지 않는 함정 때문에 이제는 `unknown`을 쓰는 게 맞다.

### any와 비교 정리

| 타입 | 할당 받는 값 | 프로퍼티 접근 | 호출 | 다른 타입에 할당 |
|------|------------|------------|------|--------------|
| `any` | 모두 | 무엇이든 통과 | 가능 | 어디에든 가능 |
| `unknown` | 모두 | 차단 | 차단 | 좁히기/단언 필요 |
| `{}` | null/undefined 제외 모두 | 차단 | 차단 | 거의 모든 곳 가능 |
| `object` | 비-원시 값만 | 차단 | 차단 | 비-원시 자리만 |
| `Function` | 함수만 | any 메서드 | 가능 (any 시그니처) | 함수 자리 |

## any에서 unknown으로 마이그레이션할 때 자주 만나는 에러

`fixToUnknown` 자동 변환이나 수동 치환을 하면 갑자기 빨간 줄이 도배된다. 패턴별로 어떻게 푸는지 정리한다.

### TS2571: Object is of type 'unknown'

가장 흔한 에러. `unknown` 값을 좁히지 않고 사용하려 할 때 발생한다.

```typescript
const data: unknown = JSON.parse(raw);
console.log(data.user.name);
// error TS18046: 'data' is of type 'unknown'.
```

#### in 연산자로 좁히기

```typescript
if (typeof data === "object" && data !== null && "user" in data) {
    // data: object & { user: unknown }
    const u = data.user;
    if (typeof u === "object" && u !== null && "name" in u) {
        console.log(u.name);
    }
}
```

`in` 연산자는 4.9 이후 좁힌 객체에 해당 키를 `unknown`으로 추가해준다. 그 이전 버전에서는 `keyof`를 직접 캐스팅해야 했다.

#### instanceof로 좁히기

```typescript
function handle(e: unknown) {
    if (e instanceof Error) {
        console.log(e.message);
    }
}
```

`useUnknownInCatchVariables`가 켜져 있으면 `try/catch`의 `e`가 `unknown`이 된다. 이때는 거의 무조건 `instanceof Error` 검사를 거쳐야 한다.

#### 사용자 정의 타입 가드

복잡한 구조는 타입 가드 함수로 분리한다.

```typescript
interface User {
    id: number;
    name: string;
}

function isUser(v: unknown): v is User {
    return (
        typeof v === "object" &&
        v !== null &&
        "id" in v &&
        typeof (v as Record<string, unknown>).id === "number" &&
        "name" in v &&
        typeof (v as Record<string, unknown>).name === "string"
    );
}

const data: unknown = JSON.parse(raw);
if (isUser(data)) {
    console.log(data.id, data.name);
}
```

가드 안에서는 `Record<string, unknown>`으로 한 번 단언해 인덱스 접근을 푼다. 이걸 매번 적기 싫으면 `zod`, `valibot`, `io-ts` 같은 런타임 검증 라이브러리로 대체한다.

#### assertion function

좁히지 못하면 예외를 던지는 함수를 쓰면 호출 이후로 타입이 좁혀진다.

```typescript
function assertIsUser(v: unknown): asserts v is User {
    if (!isUser(v)) throw new Error("not a user");
}

const data: unknown = JSON.parse(raw);
assertIsUser(data);
console.log(data.id); // data: User
```

`asserts v is T` 시그니처는 호출 이후 `v`를 `T`로 좁힌다. 함수 본문에서 실제로 throw하지 않으면 런타임에 타입이 거짓이 되니 주의해야 한다.

### TS2345: Argument of type 'unknown' is not assignable to parameter of type 'X'

`any[]`에서 `unknown[]`으로 바꾸면 `arr.map(fn)` 호출에서 콜백의 매개변수 타입이 `unknown`이 되고, 콜백 본문에서 또 좁히기를 해야 한다. 외부 라이브러리 콜백이 `any`만 받는 경우 인자 자리에서 에러가 난다. 이때는 콜백 안에서 좁히거나 단언해야 한다.

### 단언이 필요한 자리는 인정한다

마이그레이션 중 어떤 자리는 끝까지 좁히기 어렵다(예: 외부 메시지 큐 페이로드, eval 결과). 이때는 `as unknown as T` 두 단계 단언으로 명시적으로 우회를 표시한다. 한 번에 `as T`로 단언하면 ESLint와 코드 리뷰어 양쪽이 못 보고 지나치는데, `as unknown as T`는 의도적인 우회임을 코드에 남긴다.

```typescript
const config = process.env.CONFIG_JSON
    ? (JSON.parse(process.env.CONFIG_JSON) as unknown as AppConfig)
    : defaultConfig;
```

## 라이브러리 타입 정의에서 어쩔 수 없이 any를 써야 하는 케이스

`unknown`이 더 안전한 건 맞지만, 라이브러리 작성자 입장에서 `any`를 의도적으로 쓰는 자리가 있다. 이유는 보통 "사용자가 아무 곳에나 넘겼을 때 그 자리에서 다시 좁히기를 하지 않아도 되게 하기 위함"이다.

### React.FC와 children

`@types/react`의 정의를 보면 children 타입이 `ReactNode`로 좁혀져 있지만, 옛 버전이나 일부 HOC는 children 자리에 `any`를 두기도 했다. 그 이유는 children에 들어올 수 있는 형태가 너무 다양하기 때문이다(엘리먼트, 문자열, 숫자, 배열, 함수형 children, null). `ReactNode`로 묶긴 했지만 실제 컴포넌트 작성자는 함수형 children 패턴 등에서 다시 `any`를 끼얹는 경우가 흔하다.

```typescript
interface RenderProps<T> {
    children: (data: T) => React.ReactNode;
}
// 여기서 T가 any로 들어오는 순간 children 호출 결과 전체가 any로 흘러감
```

라이브러리 측에서는 제네릭 `T`를 그대로 노출해 사용자 측 타입 추론에 위임하는 방식이 정답이다. 사용자가 `<Render<User>>`처럼 명시하면 `any`가 끊긴다.

### Express의 RequestHandler

`@types/express`에서 `RequestHandler`의 정의는 다음과 같이 생겼다.

```typescript
interface RequestHandler<
    P = ParamsDictionary,
    ResBody = any,
    ReqBody = any,
    ReqQuery = ParsedQs,
    LocalsObj extends Record<string, any> = Record<string, any>,
> {
    (
        req: Request<P, ResBody, ReqBody, ReqQuery, LocalsObj>,
        res: Response<ResBody, LocalsObj>,
        next: NextFunction,
    ): void | Promise<void>;
}
```

`ResBody`와 `ReqBody`의 기본값이 `any`다. `unknown`으로 바꾸면 사용자가 매번 제네릭을 채워야 컴파일이 통과된다. Express 미들웨어를 작성하는 모든 사용자가 `req.body.foo`를 쓰기 위해 매번 좁히기를 해야 한다면 라이브러리 사용성이 무너진다. 그래서 라이브러리 측은 의도적으로 `any`를 기본값으로 두고, 사용자가 안전성이 필요하면 제네릭을 채우거나 검증 미들웨어를 쓰게 한다.

```typescript
// 사용자 측에서 안전을 원하면 좁힘
interface CreateUserBody { name: string; email: string; }
const handler: RequestHandler<{}, unknown, CreateUserBody> = (req, res) => {
    req.body.name; // string으로 추론됨
};
```

### Promise.all의 가변 길이 튜플

`Promise.all`의 시그니처는 가변 길이 튜플을 처리하기 위해 내부적으로 `T[number]`와 conditional type을 동원한다. 일부 폴리필이나 호환 라이브러리에서는 결국 `Promise<any[]>` 오버로드로 폴백되는 경우가 있다. 이런 자리는 라이브러리 작성자가 가변 입력의 표현 한계 때문에 `any`로 처리한 흔적이다.

### EventEmitter 계열

Node.js의 `EventEmitter`는 이벤트 이름과 인자를 모두 동적으로 받는다. `@types/node`의 정의는 `(event: string | symbol, listener: (...args: any[]) => void)`다. 이벤트 이름과 인자 타입을 묶으려면 declaration merging이나 strictly-typed-emitter 같은 별도 래퍼가 필요하다. 라이브러리가 `any`를 쓴 건 약속된 인자 타입이 없는 이벤트 시스템의 본질적 한계 때문이다.

### 정리하자면

라이브러리 작성자가 `any`를 쓴 자리는 다음 셋 중 하나다.

- 사용자 코드의 사용성을 우선해 매번 좁히기를 강요하지 않으려는 경우(Express body)
- 가변 길이 튜플, 동적 이벤트처럼 타입으로 표현이 어려운 자리
- 제네릭으로 위임할 수 있지만 기본값을 안전하게 둘 수 없는 자리(React children 일부)

자기 코드에서 `any`를 쓸 때도 이 셋 중 하나의 이유에 해당하는지 점검하면, 무의식적인 `any` 사용을 줄일 수 있다.

## 마무리

`any`는 타입 검사 우회 키워드가 아니라, 컴파일러가 모든 타입 비교를 단축 평가하는 특수 표식이다. 한 번 들어오면 표현식 그래프 전체로 전염되고, 라이브러리 정의 한 줄이 사용자 코드 수백 줄을 검증 없는 영역으로 만든다. `unknown`으로의 마이그레이션은 한꺼번에 하지 말고 외부 데이터가 들어오는 경계부터 시작해 호출 그래프 안쪽으로 좁혀 들어가는 게 현실적이다. 라이브러리 정의에 박힌 `any`는 의도가 있는 자리가 많으므로, 호출 측에서 제네릭을 채우거나 검증 레이어를 두는 식으로 대응한다.
