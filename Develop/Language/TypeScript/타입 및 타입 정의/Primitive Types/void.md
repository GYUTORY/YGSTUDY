---
title: TypeScript void 타입
tags: [language, typescript]
updated: 2026-08-09
---

# void

## 반환값을 무시하겠다는 선언

`void`는 "이 함수가 무엇을 반환하든 나는 안 본다"는 뜻이다. "아무것도 반환하지 않는다"가 아니다. 이 차이가 `void`의 거의 모든 특이 동작을 만든다.

가장 흔하게 마주치는 곳은 콜백이다.

```typescript
declare function forEach<T>(xs: T[], f: (x: T) => void): void;

const out: number[] = [];
forEach([1, 2, 3], x => out.push(x));   // push는 number를 반환하는데 통과한다
```

`f`의 반환 타입이 `void`인데 `out.push(x)`는 `number`를 반환한다. 그런데도 에러가 나지 않는다. `void`가 "반환값이 없어야 한다"는 제약이었다면 이 코드는 컴파일되지 않고, `x => { out.push(x); }`처럼 중괄호를 씌워야 했을 것이다.

TypeScript가 이렇게 설계한 이유는 실용성이다. 콜백을 넘길 때마다 반환값을 버리려고 중괄호를 씌우는 건 번거롭고, 호출하는 쪽이 그 값을 쓰지 않는다면 아무 문제도 생기지 않는다.

## undefined 와 무엇이 다른가

둘은 자주 혼동되지만 다른 층위의 개념이다. `undefined`는 값이고 `void`는 "값을 보지 않겠다"는 계약이다.

```typescript
function f(): void {}
function g(): undefined { return undefined; }

const a: void = undefined;      // OK
const b: undefined = f();
// Type 'void' is not assignable to type 'undefined'.
```

`undefined`는 `void`에 넣을 수 있지만 반대는 안 된다. `void`를 반환하는 함수의 결과를 실제로 쓰려고 하면 막힌다는 뜻이다.

`strictNullChecks`를 끄면 이 구분이 흐려진다. `null`과 `undefined`가 모든 타입에 대입 가능해지면서 위 에러가 사라진다.

반환 타입을 명시하지 않으면 추론 결과도 다르다.

```typescript
function h() {}                 // 추론: void
function i() { return; }        // 추론: void
function j() { return undefined; }  // 추론: undefined
```

## 대입 가능성의 방향

`void`는 타입 시스템에서 특이한 자리에 있다. 함수 타입끼리 비교할 때만 특별 취급을 받는다.

```typescript
type Handler = () => void;

const h1: Handler = () => 42;        // OK — 반환 타입이 달라도 통과
const h2: Handler = () => "hello";   // OK

const n: number = h1();
// Type 'void' is not assignable to type 'number'.
```

`() => number`를 `() => void`에 대입하는 건 허용되지만, 그렇게 대입한 뒤에는 반환값을 꺼낼 수 없다. 값은 런타임에 실제로 존재하지만 타입 시스템이 접근을 막는다.

이 비대칭이 실수를 만드는 지점이 있다.

```typescript
declare function each<T>(xs: T[], f: (x: T) => void): void;

// 의도: 모든 값이 조건을 만족하는지 보려 했다
each([1, 2, 3], x => x > 0);   // 반환값이 그냥 버려진다. 경고도 없다
```

`f`가 `boolean`을 돌려줘도 `each`는 무시한다. 검사 함수를 넘길 자리에 `void` 콜백을 쓰면 결과가 조용히 사라진다. 콜백의 반환값을 실제로 쓸 거라면 시그니처에 그 타입을 써야 한다.

## async 함수와 Promise&lt;void&gt;

```typescript
async function save(): Promise<void> {
  await db.write();
}
```

`Promise<void>`는 "이행되지만 값이 없다"는 뜻이다. 앞서 나온 콜백 규칙이 여기서도 그대로 적용되어, 이벤트 핸들러에 `async` 함수를 넘길 때 문제가 된다.

```typescript
declare function on(event: string, f: () => void): void;

on("click", async () => {
  await mightThrow();   // 여기서 던지면 아무도 못 잡는다
});
```

`() => Promise<void>`가 `() => void`에 대입되면서 프로미스가 버려진다. 거부된 프로미스를 아무도 기다리지 않으므로 `unhandledRejection`으로 빠진다. `void` 콜백 자리에 `async`를 넣을 때는 함수 안에서 직접 `try/catch`로 닫아야 한다.

## void 연산자

타입이 아니라 JavaScript 연산자인 `void`도 있다. 피연산자를 평가하고 `undefined`를 돌려준다.

```typescript
void 0            // undefined
void someCall()   // someCall()을 실행하고 결과는 버림
```

린터가 "프로미스를 안 기다렸다"고 경고할 때 의도적으로 무시한다는 표시로 쓰인다.

```typescript
void logAsync();   // 기다리지 않는 게 의도임을 명시
```

타입 `void`와 이름만 같고 관계는 없다.

## 자주 틀리는 지점

**`void`를 매개변수 타입으로 쓰는 것**

```typescript
function f(x: void) {}
f(undefined);   // 이것만 가능
```

받을 수 있는 값이 사실상 `undefined` 하나뿐이라 의미가 없다. 제네릭 기본값 자리(`Promise<void>`)가 아니라면 매개변수에 쓸 일이 없다.

**메서드 오버라이드에서 반환 타입을 좁히는 것**

```typescript
class Base { run(): void {} }
class Child extends Base {
  run(): number { return 1; }   // OK — void 규칙 때문에 통과한다
}
```

통과하지만 `Base` 타입으로 다루는 코드에서는 반환값을 못 쓴다. 자식만 아는 반환값은 인터페이스를 분리하는 게 맞다.

**`never`와 혼동**

| | 의미 | 함수가 |
|---|---|---|
| `void` | 반환값을 보지 않음 | 정상적으로 끝남 |
| `never` | 반환이 일어나지 않음 | throw 하거나 끝나지 않음 |

`void`를 반환하는 함수는 제어 흐름을 이어가지만 `never`는 그 아래를 도달 불가로 만든다.

## void 를 쓰면 안 되는 곳

**반환값을 쓸 가능성이 있는 콜백 시그니처.** 위의 `each` 예처럼 결과가 조용히 버려진다. 검사·변환 콜백이라면 `(x: T) => boolean`, `(x: T) => U`로 정확히 쓴다.

**"아직 안 정했다"는 뜻으로.** 반환 타입을 미루려고 `void`를 두면 나중에 값을 반환하도록 바꿀 때 호출부가 전부 그 값을 못 쓴다. 값이 생길 예정이라면 처음부터 그 타입을 쓰거나 `unknown`을 쓴다.

## 참고

- [TypeScript Handbook — More on Functions: void](https://www.typescriptlang.org/docs/handbook/2/functions.html#void)
- [TypeScript Handbook — Assignability of functions](https://www.typescriptlang.org/docs/handbook/2/functions.html#assignability-of-functions)
- [TypeScript FAQ — Why are functions returning non-void assignable to functions returning void?](https://github.com/microsoft/TypeScript/wiki/FAQ#why-are-functions-returning-non-void-assignable-to-function-returning-void)
