---
title: TypeScript 제네릭 (Generics)
tags: [language, typescript]
updated: 2026-08-09
---

# 제네릭

## 타입을 잃지 않고 함수를 재사용하기

같은 로직을 여러 타입에 쓰고 싶을 때 처음 떠오르는 건 `any`다.

```typescript
function first(xs: any[]): any {
  return xs[0];
}

const n = first([1, 2, 3]);   // any
n.toUpperCase();              // 컴파일 통과, 런타임에 터짐
```

`any`는 검사를 끄는 것이지 재사용이 아니다. 반대로 오버로드를 쌓으면 타입은 지키지만 타입 조합마다 선언이 늘어난다.

제네릭은 **입력 타입과 출력 타입의 관계를 식으로 적어두는** 방식이다.

```typescript
function first<T>(xs: T[]): T | undefined {
  return xs[0];
}

const n = first([1, 2, 3]);        // number | undefined
const s = first(["a", "b"]);       // string | undefined
```

`T`는 값이 아니라 호출 시점에 채워지는 자리다. 반환 타입이 인자 타입을 따라간다는 관계를 한 줄로 표현했고, 호출부는 아무것도 명시하지 않았는데 정확한 타입을 받는다.

## 타입 인자는 대개 적지 않는다

제네릭을 쓸 때 `first<number>([1,2,3])`처럼 매번 꺾쇠를 채우는 코드를 보게 되는데, 대부분 불필요하다. 컴파일러가 인자에서 역으로 추론한다.

```typescript
declare function pair<A, B>(a: A, b: B): [A, B];

pair(1, "x");                 // [number, string] — 추론
pair<number, string>(1, "x"); // 같은 결과. 적을 이유 없음
```

명시가 필요한 건 추론할 근거가 없을 때다.

```typescript
declare function make<T>(): T[];

const xs = make();            // unknown[] — 인자가 없어 추론 불가
const ys = make<string>();    // string[]
```

추론된 타입이 너무 넓거나 좁을 때도 명시한다. 리터럴은 기본적으로 넓혀지기 때문이다.

```typescript
declare function box<T>(v: T): { value: T };

const a = box("red");                  // { value: string }
const b = box<"red" | "blue">("red");  // { value: "red" | "blue" }
```

## 제약 — extends 로 쓸 수 있는 것을 좁힌다

`T`에 아무 제약이 없으면 그 값으로 할 수 있는 게 거의 없다.

```typescript
function len<T>(x: T): number {
  return x.length;
}
// Property 'length' does not exist on type 'T'.
```

`extends`로 최소 조건을 건다.

```typescript
function len<T extends { length: number }>(x: T): number {
  return x.length;
}

len("hello");      // 5
len([1, 2, 3]);    // 3
len(42);
// Argument of type 'number' is not assignable to parameter of type '{ length: number; }'.
```

키를 다루는 경우엔 `keyof`와 함께 쓴다. 이게 제네릭이 실제로 값어치를 하는 대표적인 자리다.

```typescript
function get<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const user = { id: 1, name: "kim" };
get(user, "name");   // string
get(user, "id");     // number
get(user, "age");
// Argument of type '"age"' is not assignable to parameter of type '"id" | "name"'.
```

오타가 컴파일 시점에 잡히고, 반환 타입이 키마다 달라진다. `any`로는 둘 다 못 한다.

## 추론이 어긋나는 지점

**리터럴이 넓혀진다**

```typescript
declare function pick<T>(xs: T[]): T;
const x = pick(["a", "b"]);   // string — "a" | "b" 가 아니다
```

리터럴 유니온을 유지하려면 제약을 걸어 추론 방향을 바꾼다.

```typescript
declare function pick2<T extends string>(xs: T[]): T;
const y = pick2(["a", "b"]);  // "a" | "b"
```

**여러 인자에서 나온 타입이 합쳐진다**

```typescript
declare function two<T>(a: T, b: T): T;
two(1, "x");   // T는 number | string 으로 추론된다 — 에러가 아니다
```

두 인자가 같은 타입이길 강제하려는 의도였다면 실패한다. 타입 파라미터를 나누거나 한쪽을 기준으로 삼아야 한다.

**기본값과 제약은 다르다**

```typescript
interface Box<T = string> { value: T }
const b: Box = { value: "x" };      // T 생략 시 string

interface Box2<T extends string> { value: T }
const c: Box2 = { value: "x" };
// Generic type 'Box2<T>' requires 1 type argument(s).
```

`=`는 생략했을 때 채워지는 값이고 `extends`는 넣을 수 있는 것의 상한이다.

## 클래스와 인터페이스에서

클래스에 붙은 타입 파라미터는 인스턴스마다 고정된다.

```typescript
class Stack<T> {
  private items: T[] = [];
  push(x: T): void { this.items.push(x); }
  pop(): T | undefined { return this.items.pop(); }
}

const s = new Stack<number>();
s.push(1);
s.push("x");
// Argument of type 'string' is not assignable to parameter of type 'number'.
```

정적 멤버에는 클래스의 타입 파라미터를 쓸 수 없다. 정적 멤버는 인스턴스가 아니라 클래스에 속하는데, `T`는 인스턴스를 만들 때 정해지기 때문이다.

```typescript
class Bad<T> {
  static make(): T { return null as any; }
  // Static members cannot reference class type parameters.
}
```

이럴 땐 메서드 자체에 타입 파라미터를 둔다 — `static make<U>(): U`.

## 언제 제네릭을 쓰지 않는가

**타입 파라미터가 한 번만 쓰일 때.** 아래는 제네릭처럼 보이지만 아무것도 하지 않는다.

```typescript
function log<T>(x: T): void { console.log(x); }
```

`T`가 반환 타입이나 다른 인자와 연결되지 않으므로 `unknown`을 쓰면 된다. 타입 파라미터는 **둘 이상의 자리를 이어줄 때** 의미가 있다.

**유니온으로 충분할 때.** 받을 타입이 두세 개로 정해져 있다면 `string | number`가 더 읽기 쉽다. 제네릭은 열린 집합을 다루는 도구다.

**타입 퍼즐로 넘어갈 때.** 조건부 타입과 매핑된 타입을 몇 겹 쌓으면 표현은 되지만 에러 메시지가 해독 불가능해진다. 컴파일 에러를 읽고 원인을 짚을 수 없는 수준이면 그 지점이 한계다. 타입으로 증명하는 대신 런타임 검증을 하나 두는 편이 나은 경우가 많다.

## 참고

- [TypeScript Handbook — Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html)
- [TypeScript Handbook — Type Inference](https://www.typescriptlang.org/docs/handbook/type-inference.html)
- [TypeScript Handbook — keyof Type Operator](https://www.typescriptlang.org/docs/handbook/2/keyof-types.html)
