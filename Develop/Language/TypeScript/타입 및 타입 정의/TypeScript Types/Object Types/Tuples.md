---
title: TypeScript Tuple 타입 심화
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, tuples]
updated: 2026-06-05
---

# TypeScript Tuple 타입 심화

튜플은 길이가 고정되고 각 위치의 타입이 정해진 배열이다. 자바스크립트 런타임에는 튜플이라는 개념이 없다. 런타임에는 그냥 배열이고, 컴파일 타임에만 TypeScript가 길이와 위치별 타입을 검사해준다. 이 차이를 모르고 쓰면 readonly가 사라지거나 `map` 한 번에 튜플성이 날아가는 경험을 하게 된다.

이 글은 단순한 `[string, number]` 선언법을 넘어, 4.0에서 도입된 Labeled Tuple, Variadic Tuple, 그리고 실무에서 자주 부딪히는 추론 문제까지 정리한 글이다.

---

## 1. 고정 길이 배열이라는 말의 진짜 의미

### 1.1 `[string, number]`와 `(string | number)[]`의 차이

가장 흔한 오해부터 짚는다. 두 타입은 완전히 다르다.

```typescript
const tuple: [string, number] = ["foo", 1];
const union: (string | number)[] = ["foo", 1];

// 인덱스 접근 결과가 다르다
const a = tuple[0]; // string
const b = tuple[1]; // number
const c = union[0]; // string | number
const d = union[1]; // string | number
```

`(string | number)[]`는 어느 위치를 꺼내도 `string | number`라서, 꺼낸 값이 문자열인지 숫자인지 따로 분기해야 쓸 수 있다. 튜플은 위치별로 타입이 박혀 있어서 `tuple[0].toUpperCase()`가 그냥 된다. 이게 튜플을 쓰는 첫 번째 이유다.

길이 검사도 다르다.

```typescript
const tuple: [string, number] = ["foo", 1];
const union: (string | number)[] = ["foo", 1];

const tLen = tuple.length; // 타입: 2
const uLen = union.length; // 타입: number
```

튜플의 `length`는 숫자 리터럴 타입(`2`)이고, 일반 배열은 그냥 `number`다. 이게 변형(variadic) 튜플에서 위치를 계산할 때 핵심 단서가 된다.

### 1.2 length가 리터럴 유니온으로 좁혀지는 경우

선택적 요소가 있는 튜플은 `length`가 가능한 길이들의 유니온이 된다.

```typescript
type Optional = [string, number?, boolean?];

const x: Optional = ["a"];
const y: Optional = ["a", 1];
const z: Optional = ["a", 1, true];

// x.length, y.length, z.length 모두 동일한 타입을 가진다
type Len = Optional["length"]; // 1 | 2 | 3
```

`Len`이 `1 | 2 | 3`이라는 건, 컴파일러가 이 튜플의 가능한 모든 길이를 알고 있다는 뜻이다. 분기문에서 `if (tuple.length === 3)`을 쓰면 그 안에서는 `tuple[1]`과 `tuple[2]`가 `undefined`가 아니라고 좁혀진다.

### 1.3 push와 pop은 왜 허용되는데 위험한가

튜플도 런타임에는 배열이라, `push`나 `pop`을 막을 방법이 없다. TypeScript는 일부 변형 작업을 허용한다.

```typescript
const t: [string, number] = ["foo", 1];

t.push("bar"); // 컴파일은 통과한다
t.push(42);    // 이것도 통과
console.log(t.length); // 런타임: 3, 타입: 2

const third = t[2]; // 타입은 undefined (튜플 길이가 2니까)
console.log(third); // 런타임: "bar"
```

타입은 여전히 `[string, number]`라서 `t[2]`에 접근하면 `undefined`로 추론되지만, 런타임에는 값이 들어있다. 이게 가장 무서운 케이스다. 길이가 고정되어야 하는 데이터를 튜플로 받았으면 `readonly`를 붙여서 push 자체를 막아야 한다.

```typescript
const safe: readonly [string, number] = ["foo", 1];
safe.push("bar");
// Property 'push' does not exist on type 'readonly [string, number]'.
```

---

## 2. Labeled Tuple Elements (TS 4.0+)

### 2.1 라벨이 주는 효과는 IDE 힌트뿐

튜플 각 위치에 이름을 붙일 수 있다. 4.0에서 추가된 문법이다.

```typescript
type Range = [start: number, end: number];
type HttpResult = [status: number, body: string];
```

여기서 중요한 건 `start`, `end`라는 라벨이 **타입 시스템에는 영향을 주지 않는다**는 점이다. 단순히 IDE가 함수 시그니처를 표시할 때 보여주는 힌트 역할만 한다.

```typescript
function setRange(...args: [start: number, end: number]): void {
  // ...
}

setRange(0, 10);
// IDE에서 호출 시 (start: number, end: number) 형태로 힌트가 뜬다
```

라벨 없이 `(...args: [number, number])`로 쓰면 IDE 힌트는 `args_0: number, args_1: number`로 나온다. 가독성 차이가 크다. 함수 오버로드나 가변 인자를 정의할 때 라벨을 붙이는 게 거의 표준이 됐다.

### 2.2 라벨을 섞으면 컴파일 에러

한 튜플 안에서 라벨이 있는 요소와 없는 요소를 섞으면 안 된다. 전부 붙이거나 전부 빼야 한다.

```typescript
type Bad = [name: string, number];
// Tuple members must all have names or all not have names.

type Good1 = [string, number];
type Good2 = [name: string, age: number];
```

이건 컴파일러가 강제하는 규칙이라 우회 방법이 없다.

### 2.3 라벨과 선택적/나머지 요소 조합

선택적 요소나 rest 요소에도 라벨을 붙일 수 있다.

```typescript
type Request = [method: string, path: string, body?: unknown];
type Args = [first: string, ...rest: number[]];

function log(...args: [level: "info" | "warn" | "error", message: string, ...meta: unknown[]]) {
  const [level, message, ...meta] = args;
  console.log(`[${level}] ${message}`, meta);
}

log("info", "user signed in", { userId: 1 });
```

`...rest: number[]`처럼 rest 요소에 라벨을 붙이면 호출 측에서 어떤 가변 인자를 받는지 의도가 드러난다.

---

## 3. Variadic Tuple Types (TS 4.0+)

여기부터가 튜플의 진짜 활용 영역이다. 4.0 이전에는 함수 합성이나 커링 타입을 제대로 쓰기 어려웠는데, Variadic Tuple이 들어오면서 거의 다 가능해졌다.

### 3.1 스프레드는 위치가 자유롭다

타입 레벨에서 스프레드 `...T`는 튜플 안 어디에든 올 수 있다.

```typescript
type Front<T extends unknown[]> = [string, ...T];
type Back<T extends unknown[]> = [...T, string];
type Middle<T extends unknown[]> = [boolean, ...T, number];

type F = Front<[number, boolean]>; // [string, number, boolean]
type B = Back<[number, boolean]>;  // [number, boolean, string]
type M = Middle<[string]>;          // [boolean, string, number]
```

런타임 배열 스프레드는 마지막에만 의미가 있지만, 타입 시스템은 위치를 가리지 않는다.

### 3.2 concat 타입 추론

가장 기본적인 활용은 두 튜플을 이어 붙이는 타입이다.

```typescript
function concat<T extends unknown[], U extends unknown[]>(a: [...T], b: [...U]): [...T, ...U] {
  return [...a, ...b];
}

const r = concat([1, 2] as const, ["a", "b"] as const);
// r: readonly [1, 2, ...readonly ["a", "b"]] 형태로 추론된다
// 좀 더 정확히는 [1, 2, "a", "b"]에 가깝게 좁혀진다
```

`as const`를 빼면 `concat([1, 2], ["a", "b"])`의 결과는 `(string | number)[]`처럼 일반 배열로 넓어진다. 튜플로 받고 싶으면 입력부터 튜플로 만들어야 한다.

### 3.3 head/tail 분해

스프레드를 패턴 매칭처럼 써서 첫 요소나 나머지를 뽑을 수 있다.

```typescript
type Head<T extends unknown[]> = T extends [infer H, ...unknown[]] ? H : never;
type Tail<T extends unknown[]> = T extends [unknown, ...infer R] ? R : [];
type Last<T extends unknown[]> = T extends [...unknown[], infer L] ? L : never;

type H = Head<[1, 2, 3]>; // 1
type T = Tail<[1, 2, 3]>; // [2, 3]
type L = Last<[1, 2, 3]>; // 3
```

`Last`처럼 끝에서 분해하는 패턴은 4.0 이전엔 불가능했다. 4.0 이후 자주 쓰는 패턴이다.

### 3.4 함수 합성과 부분 적용 타입

`Parameters<F>`를 튜플로 다루면 커링이나 부분 적용 함수의 타입을 정확히 적을 수 있다.

```typescript
function partial<T extends unknown[], U extends unknown[], R>(
  fn: (...args: [...T, ...U]) => R,
  ...preset: T
): (...rest: U) => R {
  return (...rest) => fn(...preset, ...rest);
}

function send(method: string, path: string, body: object): void {
  console.log(method, path, body);
}

const post = partial(send, "POST");
// post: (path: string, body: object) => void

post("/users", { name: "kim" });
```

`partial`의 입력 함수 시그니처를 `[...T, ...U]`로 쪼개서, 앞쪽 `T`를 미리 받고 나머지 `U`를 반환 함수에서 받는 구조를 만들었다. 4.0 이전엔 이 시그니처 자체를 쓸 수 없었다.

### 3.5 Parameters 조작 예시

API 클라이언트 래퍼를 만들 때 자주 쓴다.

```typescript
function withRetry<F extends (...args: never[]) => Promise<unknown>>(
  fn: F,
  retries: number,
): (...args: Parameters<F>) => ReturnType<F> {
  return (async (...args: Parameters<F>) => {
    let lastError: unknown;
    for (let i = 0; i <= retries; i++) {
      try {
        return await fn(...args);
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError;
  }) as (...args: Parameters<F>) => ReturnType<F>;
}

async function fetchUser(id: number, opts: { signal?: AbortSignal }) {
  // ...
  return { id, name: "kim" };
}

const safeFetchUser = withRetry(fetchUser, 3);
// safeFetchUser: (id: number, opts: { signal?: AbortSignal }) => Promise<{ id: number; name: string }>
```

`Parameters<F>`가 튜플이고, 그 튜플이 그대로 새 함수의 시그니처로 전파된다. 라벨이 있던 원래 파라미터의 이름까지 IDE 힌트에 그대로 따라온다.

---

## 4. readonly 튜플 심화

### 4.1 `readonly [A, B]`와 `as const`는 같지 않다

겉보기엔 비슷해 보이는데 의미가 다르다.

```typescript
const a = ["foo", 1] as [string, number];      // [string, number]
const b: readonly [string, number] = ["foo", 1]; // readonly [string, number]
const c = ["foo", 1] as const;                  // readonly ["foo", 1]
```

- `readonly [string, number]`: 길이와 위치별 타입은 고정, 값은 `string`/`number` 그대로
- `as const`: 길이와 타입에 더해 **값까지 리터럴로 좁힘**, 그리고 모든 중첩 객체/배열까지 재귀적으로 readonly

`as const`는 `c[0]`의 타입이 `"foo"`가 된다. 상수 매핑 테이블이나 enum 대체용으로 쓸 때 이 동작이 필요하다. 단순히 변형을 막고 싶을 뿐이면 `readonly` 한정자로 충분하다.

### 4.2 readonly 튜플과 가변 튜플의 호환성 (공변/반공변)

readonly 튜플을 가변 튜플 자리에 넘기는 건 막혀 있다. 반대 방향은 허용된다.

```typescript
function mutate(t: [string, number]) {
  t[0] = "bar";
}

const ro: readonly [string, number] = ["foo", 1];
mutate(ro);
// Argument of type 'readonly [string, number]' is not assignable to parameter of type '[string, number]'.

function read(t: readonly [string, number]) {
  return t[0];
}

const mut: [string, number] = ["foo", 1];
read(mut); // OK
```

이게 라이브러리 함수 시그니처를 짤 때 중요하다. **읽기만 하는 파라미터는 항상 `readonly`로 받아야** 호출 측이 readonly 데이터든 가변 데이터든 가리지 않고 넘길 수 있다. 가변 튜플로 받으면 호출자에게 불필요한 제약을 거는 셈이다.

### 4.3 ReadonlyArray와의 차이

`readonly T[]`(또는 `ReadonlyArray<T>`)와 `readonly [T, T]`도 다르다.

```typescript
const arr: readonly number[] = [1, 2, 3];
const tup: readonly [number, number, number] = [1, 2, 3];

const a0 = arr[0]; // number
const t0 = tup[0]; // number

const aLen = arr.length; // number
const tLen = tup.length; // 3
```

readonly 튜플은 길이 정보와 위치별 타입을 모두 보존한다. readonly 배열은 길이가 `number`로 풀린다. 함수 파라미터로 받을 때 위치별 타입이 중요하면 튜플, 동일 타입의 가변 길이면 readonly 배열을 쓴다.

---

## 5. 실무 활용 예시

### 5.1 useState 스타일 훅 반환 타입

리액트의 `useState`가 튜플을 반환하는 게 사실상 표준이 됐다. 직접 비슷한 훅을 만들 때 시그니처가 핵심이다.

```typescript
function useToggle(initial: boolean): [state: boolean, toggle: () => void, set: (v: boolean) => void] {
  let state = initial;
  const toggle = () => { state = !state; };
  const set = (v: boolean) => { state = v; };
  return [state, toggle, set];
}

const [enabled, toggle, setEnabled] = useToggle(false);
```

라벨을 붙이면 호출하는 쪽 IDE에서 `[state: boolean, toggle: () => void, set: (v: boolean) => void]`로 보인다. 라벨이 없으면 그냥 `[boolean, () => void, (v: boolean) => void]`로 뜨는데, 의미를 파악하려면 정의를 다시 봐야 한다.

### 5.2 Result/Either 패턴

Go 스타일로 에러와 데이터를 함께 반환하는 패턴이다.

```typescript
type Result<T, E = Error> = [data: T, error: null] | [data: null, error: E];

async function safe<T>(promise: Promise<T>): Promise<Result<T>> {
  try {
    const data = await promise;
    return [data, null];
  } catch (e) {
    return [null, e as Error];
  }
}

const [user, err] = await safe(fetchUser(1));
if (err) {
  console.error(err);
  return;
}
console.log(user.name); // err가 null이라 user는 not-null로 좁혀진다
```

판별된 유니온(discriminated union)으로 짜면 `err`가 `null`인지 검사한 뒤 `user`가 자동으로 non-null로 좁혀진다. 객체 기반 `{ data, error }` 패턴보다 구조 분해가 깔끔해서 선호하는 사람이 많다.

### 5.3 Express 미들웨어 체인 타입

미들웨어의 다음 핸들러 인자 시그니처를 정확히 잡고 싶을 때 튜플이 유용하다.

```typescript
type Middleware<Args extends unknown[], Result> = (
  ...args: Args
) => Promise<Result>;

function compose<A extends unknown[], B, C>(
  m1: Middleware<A, B>,
  m2: Middleware<[B], C>,
): Middleware<A, C> {
  return async (...args) => {
    const intermediate = await m1(...args);
    return m2(intermediate);
  };
}

const parseBody: Middleware<[Request], { userId: number }> = async (req) => {
  return { userId: Number(req.headers.get("x-user")) };
};

const loadUser: Middleware<[{ userId: number }], { id: number; name: string }> = async ({ userId }) => {
  return { id: userId, name: "kim" };
};

const handler = compose(parseBody, loadUser);
// handler: Middleware<[Request], { id: number; name: string }>
```

`A`가 가변 튜플이라 첫 미들웨어의 입력 시그니처가 그대로 합성 결과에 전파된다.

### 5.4 Promise.all 결과 튜플

`Promise.all`은 입력이 튜플이면 결과도 튜플로 추론된다. 이게 4.0 Variadic Tuple 덕에 가능해진 동작이다.

```typescript
async function loadDashboard() {
  const [user, orders, notifications] = await Promise.all([
    fetchUser(1),
    fetchOrders(1),
    fetchNotifications(1),
  ] as const);
  // user, orders, notifications가 각각 정확한 타입으로 추론된다
}
```

`as const` 없이도 `Promise.all`의 오버로드가 튜플 추론을 잡아주지만, 가끔 배열로 풀리는 경우가 있어서 명시적으로 `as const`나 `[...] satisfies [...]`를 붙여두면 안전하다.

---

## 6. 자주 부딪히는 트러블슈팅

### 6.1 `[1, 2, 3]`은 왜 튜플이 아니라 `number[]`로 추론되나

이게 입문자가 처음 막히는 지점이다.

```typescript
const a = [1, 2, 3];        // number[]
const b = [1, 2, 3] as const; // readonly [1, 2, 3]

function take(t: [number, number, number]) {}

take(a); // 에러: number[]는 [number, number, number]에 할당 불가
take(b); // 에러: readonly가 붙어서 안 됨
take([1, 2, 3]); // OK (인라인 리터럴은 컨텍스트 타입으로 추론)
```

배열 리터럴을 변수에 담는 순간 가장 넓은 타입(`number[]`)으로 추론된다. 튜플로 만들고 싶으면 명시적으로 타입을 적거나 `as const`를 붙여야 한다. `as const`를 붙이면 readonly가 따라오니, 가변이 필요하면 그냥 타입 어노테이션을 명시한다.

```typescript
const c: [number, number, number] = [1, 2, 3]; // [number, number, number]
```

### 6.2 spread 시 readonly가 사라지는 문제

`as const`로 만든 readonly 튜플을 스프레드하면 readonly가 풀린다.

```typescript
const ro = [1, 2, 3] as const; // readonly [1, 2, 3]
const copy = [...ro];          // number[]
const copy2: [1, 2, 3] = [...ro]; // 에러: number[]는 [1, 2, 3]에 할당 불가
```

스프레드된 결과는 일반 배열로 풀려서, 다시 튜플로 받으려면 타입 어노테이션을 다시 걸어야 한다. 라이브러리 유틸 함수를 만들 때 입력 readonly를 결과까지 보존하고 싶다면 Variadic Tuple로 시그니처를 짜야 한다.

```typescript
function clone<T extends readonly unknown[]>(t: T): [...T] {
  return [...t] as [...T];
}

const cloned = clone([1, 2, 3] as const); // [1, 2, 3] (readonly 풀림)
```

여기서도 `[...T]`는 readonly가 풀린 가변 튜플이 된다. readonly까지 보존하려면 `readonly [...T]`로 명시한다.

### 6.3 JSON.parse 후 타입 단언이 필요한 이유

`JSON.parse`의 반환 타입은 `any`다. 튜플로 받으려면 단언이 필수다.

```typescript
const raw = '["foo", 1]';
const parsed = JSON.parse(raw); // any
const tuple = JSON.parse(raw) as [string, number]; // [string, number]

// 단, 런타임 검증은 안 해준다
const broken = JSON.parse('[1, "foo"]') as [string, number];
broken[0].toUpperCase(); // 컴파일은 통과, 런타임에 TypeError
```

타입 단언은 컴파일러에게 "내가 책임진다"고 약속하는 거지 검증이 아니다. 외부에서 들어오는 데이터는 zod나 io-ts 같은 런타임 검증기를 거치고 나서 튜플로 좁히는 게 안전하다.

### 6.4 배열 메서드를 쓰면 튜플성이 사라진다

`map`, `filter`, `slice` 같은 배열 메서드는 일반 배열을 반환한다. 튜플 정보가 통째로 날아간다.

```typescript
const t: [number, number, number] = [1, 2, 3];
const doubled = t.map(x => x * 2); // number[] — 튜플 아님

function take(arr: [number, number, number]) {}
take(doubled); // 에러
```

이건 `Array.prototype.map`의 타입 정의가 `(callbackfn: ...) => U[]`로 잡혀 있기 때문이다. 튜플로 유지하려면 직접 시그니처를 짜거나, mapped tuple 패턴을 쓴다.

```typescript
type MapTuple<T extends readonly unknown[], U> = {
  [K in keyof T]: U;
};

function mapTuple<T extends readonly unknown[], U>(
  t: T,
  fn: (v: T[number]) => U,
): MapTuple<T, U> {
  return t.map(fn) as MapTuple<T, U>;
}

const doubled2 = mapTuple([1, 2, 3] as const, x => x * 2);
// MapTuple<readonly [1, 2, 3], number> = readonly [number, number, number]
```

`MapTuple`이 튜플의 각 위치를 동일 변환된 타입으로 다시 매핑한다. `keyof T`로 인덱스 키를 순회하는 패턴인데, 튜플에서는 이게 `"0" | "1" | "2" | "length" | ...` 같은 키가 아니라 숫자 인덱스만 골라낸다. mapped tuple은 컴파일러가 따로 지원하는 특수 케이스다.

### 6.5 빈 튜플과 단일 요소 튜플

가끔 함수 시그니처에서 `[]`나 `[T]`가 필요하다.

```typescript
type EmptyArgs = [];
type SingleArg<T> = [T];

function noArgs(...args: EmptyArgs) {}
function oneArg<T>(...args: SingleArg<T>) {}

noArgs();        // OK
noArgs(1);       // 에러: 인자 0개 기대
oneArg("foo");   // OK
oneArg();        // 에러: 인자 1개 기대
oneArg("a", "b"); // 에러
```

`...args: []`와 그냥 인자 없는 함수는 거의 동등하지만, 가변 인자 튜플과 합성할 때 명시적으로 빈 튜플이 필요한 경우가 있다. 예를 들어 `Parameters<F>`가 `[]`로 추론되는 상황에서 그대로 forwarding 함수를 짤 때다.

---

## 7. 튜플을 쓸지 객체를 쓸지 판단 기준

마지막으로 실무에서 가장 자주 망설이는 부분이다.

| 상황 | 튜플 | 객체 |
|------|------|------|
| 위치가 의미를 가짐 (좌표, 범위) | 튜플 | |
| 구조 분해를 매번 함 (훅, Result) | 튜플 | |
| 요소가 4개 이상 | | 객체 |
| 필드 이름이 코드 가독성에 중요 | | 객체 |
| 외부 API 응답 매핑 | | 객체 |
| 함수 합성/커링 타입 조작 | 튜플 | |

요소가 3개를 넘기 시작하면 구조 분해에서 무슨 값을 어디서 받는지 헷갈린다. `const [a, b, c, d, e] = thing()`을 보면 `d`가 뭔지 정의를 다시 봐야 한다. 그럴 땐 객체로 바꾸는 게 낫다. 라벨드 튜플이 IDE 힌트를 띄워줘도 변수명이 자동으로 좋아지지는 않는다.

반대로 함수 시그니처를 가변 인자로 다뤄야 하거나, `Promise.all` 같이 위치 기반으로 결과를 받아야 하는 경우엔 튜플 외에 대안이 없다.

---

## 정리

- 튜플은 런타임에 그냥 배열이다. readonly로 막지 않으면 push가 들어간다.
- Labeled Tuple은 타입 시스템에 영향이 없는 IDE 힌트일 뿐이지만, 가변 인자 시그니처에선 가독성이 크게 차이 난다.
- Variadic Tuple은 함수 합성, 커링, `Parameters<F>` 조작에서 진가가 드러난다. 4.0 이전에는 못 짜던 시그니처가 거의 다 가능해졌다.
- `readonly [A, B]`와 `as const`는 다르다. 값 리터럴이 필요한 게 아니면 readonly만 붙인다.
- 함수 파라미터는 가능하면 readonly 튜플로 받는다. 호출 측에 불필요한 제약을 안 거는 게 라이브러리 설계의 기본이다.
- `map`, `filter`, spread는 튜플성을 깨뜨린다. 보존이 필요하면 Variadic Tuple과 mapped tuple로 시그니처를 다시 짠다.
- 요소가 3개를 넘으면 객체로 바꾸는 걸 진지하게 고려한다.
