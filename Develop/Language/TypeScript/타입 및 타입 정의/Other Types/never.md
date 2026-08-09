---
title: TypeScript never 타입
tags: [language, typescript]
updated: 2026-08-09
---

# never

## never가 필요한 순간

유니온을 다루는 함수를 하나 쓴다고 하자.

```typescript
type Shape =
  | { kind: "circle"; r: number }
  | { kind: "square"; side: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.r ** 2;
    case "square": return s.side ** 2;
  }
}
```

여기까지는 문제가 없다. 그런데 몇 달 뒤 삼각형이 추가된다.

```typescript
type Shape =
  | { kind: "circle"; r: number }
  | { kind: "square"; side: number }
  | { kind: "triangle"; base: number; height: number };
```

`area`는 여전히 컴파일된다. 삼각형을 넣으면 `undefined`가 나온다. 런타임에 조용히 틀린 값이 돌아다니고, 그걸 곱하거나 더한 어딘가에서 `NaN`으로 터진다. 원인 지점과 증상 지점이 멀어서 추적이 오래 걸린다.

`never`는 이 상황을 **컴파일 시점의 에러로 바꾸기 위해** 존재한다. 타입을 하나 추가했을 때 그 타입을 처리하지 않은 곳이 전부 빨간 줄로 뜨게 만드는 장치다.

## 값이 존재할 수 없다는 뜻

`never`는 공집합이다. 어떤 값도 이 타입을 만족하지 못한다. `null`도, `undefined`도 아니다.

여기서 두 가지 성질이 따라 나온다.

```typescript
declare const n: never;
const a: string = n;   // OK — never는 모든 타입에 대입 가능
const b: number = n;   // OK

declare const s: string;
const c: never = s;
// Type 'string' is not assignable to type 'never'.
```

원소가 없는 집합은 모든 집합의 부분집합이므로 `never`는 어디에나 들어간다. 반대로 `never` 자리에는 아무것도 못 들어간다 — 넣을 수 있는 값이 없기 때문이다.

이 성질 때문에 `never`는 유니온의 항등원이 된다.

```typescript
type A = string | never;   // string
type B = never | never;    // never
type C = string & never;   // never — 인터섹션에서는 흡수원
```

`T | never`가 `T`가 되는 건 나중에 조건부 타입에서 걸러내기로 쓰인다.

## 컴파일러가 never를 만드는 세 경우

직접 `never`라고 쓰는 일은 드물다. 대부분은 컴파일러가 추론해서 만든다.

**1. 반환하지 않는 함수**

```typescript
function fail(msg: string): never {
  throw new Error(msg);
}

function loop(): never {
  while (true) {}
}
```

값을 반환하지 않는 것(`void`)과 **반환이라는 사건 자체가 일어나지 않는 것**(`never`)은 다르다. `fail`은 정상 종료가 없으므로 반환값의 타입을 말할 수 없다.

이 구분은 제어 흐름 분석에 쓰인다.

```typescript
function parse(input: string | null): string {
  if (input === null) fail("input is null");
  return input.toUpperCase();  // input은 여기서 string
}
```

`fail`의 반환 타입이 `void`였다면 `input`은 여전히 `string | null`이라 `toUpperCase` 호출에서 에러가 난다. `never`이기 때문에 컴파일러가 "이 줄 아래로는 `input === null`인 경우가 도달하지 않는다"고 판단한다.

**2. 좁히기를 다 소진한 분기**

```typescript
function f(x: string | number) {
  if (typeof x === "string") return;
  if (typeof x === "number") return;
  x;  // never
}
```

가능한 경우를 전부 걷어내면 남는 자리의 타입은 `never`다. 이게 다음 절의 배타성 검사가 작동하는 원리다.

**3. 불가능한 인터섹션**

```typescript
type Impossible = string & number;  // never
```

문자열이면서 동시에 숫자인 값은 없다. 이건 실수로 만들어지는 경우가 많다 — 제네릭 제약을 잘못 걸었을 때 결과 타입이 `never`로 붕괴하고, 그 뒤로 모든 대입이 실패한다.

## 배타성 검사 — never를 쓰는 주된 이유

앞의 `area`로 돌아가자. `default` 분기에 `never` 변수를 하나 두면 된다.

```typescript
function assertNever(x: never): never {
  throw new Error(`처리하지 않은 분기: ${JSON.stringify(x)}`);
}

function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.r ** 2;
    case "square": return s.side ** 2;
    default: return assertNever(s);
  }
}
```

`Shape`가 두 종류일 때는 `default`에 도달한 `s`가 `never`로 좁혀져 통과한다. 삼각형을 추가하는 순간 `s`는 `never`가 아니라 삼각형 타입이 되고, `assertNever`에 넘길 수 없어 에러가 난다.

> `Argument of type '{ kind: "triangle"; base: number; height: number; }' is not assignable to parameter of type 'never'.`

에러 메시지가 **빠뜨린 타입을 그대로 알려준다**. 이게 핵심이다. 유니온에 멤버를 추가하면 처리를 빠뜨린 모든 위치가 한 번에 드러나고, 메시지만 읽어도 무엇을 더 써야 하는지 안다.

`assertNever`가 런타임에도 던지는 이유는 타입 단언이나 `any`로 뚫고 들어온 값에 대비하기 위해서다. 타입 검사는 컴파일 시점에서 끝나므로, 외부 JSON처럼 검증 없이 들어온 값은 여전히 `default`에 도달할 수 있다.

## 조건부 타입에서의 never

분배 조건부 타입에서 `never`는 "이 멤버를 결과에서 뺀다"는 뜻으로 동작한다. `T | never === T`이기 때문이다.

```typescript
type Exclude<T, U> = T extends U ? never : T;

type R = Exclude<"a" | "b" | "c", "b">;
// "a" extends "b" ? never : "a"  →  "a"
// "b" extends "b" ? never : "b"  →  never
// "c" extends "b" ? never : "c"  →  "c"
// 합치면  "a" | never | "c"  →  "a" | "c"
```

`Exclude`가 저렇게 생긴 이유가 여기 있다. 걸러낼 항목을 `never`로 만들어두면 유니온으로 합쳐질 때 저절로 사라진다.

주의할 점은 분배가 **네이키드 타입 파라미터**에서만 일어난다는 것이다.

```typescript
type NoDistribute<T, U> = [T] extends [U] ? never : T;
type X = NoDistribute<"a" | "b", "b">;  // "a" | "b" — 통째로 비교되어 걸러지지 않음
```

## 자주 틀리는 지점

**`never[]`가 튀어나오는 경우**

```typescript
const xs = [];        // never[] (noImplicitAny 켜져 있고 추론 문맥이 없을 때)
xs.push(1);
// Argument of type 'number' is not assignable to parameter of type 'never'.
```

빈 배열 리터럴은 원소 타입을 알 수 없어 `never[]`로 추론될 수 있다. 선언 시점에 타입을 주면 된다 — `const xs: number[] = []`.

**`Promise<never>`**

절대 이행되지 않는 프로미스다. 거부되거나 영원히 대기한다. `Promise<void>`(값 없이 이행됨)와 다르다.

**`void`와 혼동**

| | 의미 | 반환문 |
|---|---|---|
| `void` | 반환값이 없음 | 정상적으로 끝남 |
| `never` | 반환 자체가 일어나지 않음 | throw 하거나 끝나지 않음 |

```typescript
function a(): void { return; }        // OK
function b(): never { return; }
// A function returning 'never' cannot have a reachable end point.
```

**`strictNullChecks`를 끄면**

`strictNullChecks`가 꺼져 있으면 `null`과 `undefined`가 모든 타입에 대입 가능해지고, 좁히기 결과도 달라진다. 배타성 검사가 의도대로 동작하려면 이 옵션이 켜져 있어야 한다.

## never를 쓰면 안 되는 곳

**에러 타입 자리에 습관적으로 넣는 것.** `Result<T, never>` 같은 표기를 "에러가 없다"는 뜻으로 쓰는 경우가 있는데, 그 타입을 다루는 쪽에서 `catch` 분기를 만들 수 없게 된다. 에러가 실제로 발생하지 않는다는 보장이 있을 때만 쓴다.

**타입 퍼즐을 위한 타입 퍼즐.** 조건부 타입을 몇 겹씩 쌓아 `never`로 분기시키는 코드는 작성자 말고는 읽지 못한다. 타입 수준에서 표현할 수 있다고 해서 표현해야 하는 건 아니다. 컴파일 에러 메시지가 의미를 잃기 시작하면 그 지점이 한계다.

## 참고

- [TypeScript Handbook — Narrowing: Exhaustiveness checking](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#exhaustiveness-checking)
- [TypeScript Handbook — Conditional Types: Distributive conditional types](https://www.typescriptlang.org/docs/handbook/2/conditional-types.html#distributive-conditional-types)
- [TypeScript Handbook — More on Functions: never](https://www.typescriptlang.org/docs/handbook/2/functions.html#never)
