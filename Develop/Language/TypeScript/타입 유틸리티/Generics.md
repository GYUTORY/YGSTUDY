---
title: TypeScript 제네릭 (Generics)
tags: [language, typescript]
updated: 2026-09-03
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

## 조건부 타입

`T extends U ? X : Y` 형태로 타입을 조건문으로 분기할 수 있다. `T`가 `U`에 할당 가능하면 `X`, 아니면 `Y`다.

```typescript
type IsArray<T> = T extends any[] ? true : false;

type A = IsArray<string[]>;  // true
type B = IsArray<number>;    // false
```

조건부 타입이 유니온과 만나면 분배가 일어난다. `T`가 유니온이면 각 멤버마다 조건을 따로 적용하고 결과를 다시 합친다.

```typescript
type Flatten<T> = T extends any[] ? T[number] : T;

type C = Flatten<string[]>;            // string
type D = Flatten<string | number[]>;   // string | number
```

`string | number[]`에 Flatten을 걸면 `string`(배열 아님, 그대로)과 `number`(배열, 원소 타입)가 분리돼 합쳐진다.

분배가 일어나지 않게 막으려면 튜플로 감싼다.

```typescript
type NoDistribute<T> = [T] extends [any[]] ? true : false;

type E = NoDistribute<string | number[]>;  // false — 전체를 한 번만 비교
```

## infer — 타입 안에서 타입을 꺼낸다

조건부 타입의 `extends` 오른쪽에 `infer R`을 두면 그 자리의 타입을 캡처해서 참인 분기에서 쓸 수 있다. 조건부 타입 안에서만 동작하는 키워드다.

함수 반환 타입을 꺼내는 게 전형적인 사용처다.

```typescript
type ReturnType<T> = T extends (...args: any[]) => infer R ? R : never;

type F = ReturnType<() => string>;                    // string
type G = ReturnType<(n: number) => Promise<number>>;  // Promise<number>
```

TypeScript 내장 `ReturnType<T>`가 정확히 이렇게 구현돼 있다.

Promise를 벗기는 것도 같은 방식이다.

```typescript
type Awaited<T> = T extends Promise<infer V> ? Awaited<V> : T;

type H = Awaited<Promise<Promise<string>>>;  // string
```

재귀적으로 자신을 호출해 중첩된 Promise를 처리한다. TypeScript 4.5부터는 내장 유틸리티 타입으로 들어왔다.

첫 번째 인자 타입만 꺼내고 싶을 때는 나머지 인자를 rest로 잡는다.

```typescript
type FirstArg<T> = T extends (first: infer F, ...rest: any[]) => any ? F : never;

type I = FirstArg<(x: number, y: string) => void>;  // number
type J = FirstArg<() => void>;                       // never — 인자 없음
```

`infer`는 패턴 매칭에 가깝다. 타입 구조에서 원하는 위치를 콕 집어 꺼낸다. 여러 자리에 동시에 쓸 수도 있다.

```typescript
type Unzip<T> = T extends [infer Head, ...infer Tail]
  ? [Head[], Unzip<Tail>]
  : [];
```

실제로 쓸 일이 많지는 않지만, 라이브러리 타입 정의를 읽을 때 `infer`가 뭘 하는지 알고 있어야 해독이 된다.

## 매핑된 타입과 제네릭

`keyof T`의 각 키를 순회하면서 새로운 프로퍼티를 만드는 패턴이다.

```typescript
type Readonly<T> = {
  readonly [K in keyof T]: T[K];
};

type Nullable<T> = {
  [K in keyof T]: T[K] | null;
};
```

제네릭과 조합하면 어떤 객체 타입이든 동일한 변환을 적용할 수 있다.

### 조건부 타입과 조합

프로퍼티 타입마다 다른 변환을 적용할 수 있다.

```typescript
type Stringify<T> = {
  [K in keyof T]: T[K] extends number ? string : T[K];
};

type User = { id: number; name: string; age: number };
type StringifiedUser = Stringify<User>;
// { id: string; name: string; age: string }
```

`id`와 `age`는 `number`라서 `string`으로 바뀌고, `name`은 이미 `string`이라 그대로 남는다.

### as로 키를 재매핑

TypeScript 4.1부터 `as` 절로 키 이름 자체를 바꿀 수 있다.

```typescript
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

type Config = { host: string; port: number };
type ConfigGetters = Getters<Config>;
// { getHost: () => string; getPort: () => number }
```

`string & K`는 `K`가 `symbol`일 수 있어서 `Capitalize`에 넘기기 전에 string으로 좁히는 것이다.

`as`와 조건부 타입을 합치면 특정 조건의 프로퍼티만 남길 수 있다. 키를 `never`로 매핑하면 해당 프로퍼티가 결과에서 제거된다.

```typescript
type PickByType<T, V> = {
  [K in keyof T as T[K] extends V ? K : never]: T[K];
};

type Obj = { id: number; name: string; active: boolean; count: number };
type NumberFields = PickByType<Obj, number>;
// { id: number; count: number }
```

`Pick<T, K>`는 키 이름을 직접 열거해야 하지만 이 패턴은 타입으로 필터링한다. 타입이 추가될 때 `PickByType` 쪽은 자동으로 따라온다.

## 제네릭 남용으로 추론이 깨지는 사례

### 연결이 끊긴 타입 파라미터

타입 파라미터는 두 곳 이상에 쓰여야 의미가 있다. 한 곳에만 쓰이면 호출부에서 캐스팅과 다를 게 없다.

```typescript
function parseJson<T>(json: string): T {
  return JSON.parse(json);
}

const user = parseJson<{ name: string }>('{"name":"kim"}');
```

`T`가 입력에서 추론되지 않는다. 호출자가 직접 명시해야 하는데, 이는 런타임 검증 없는 캐스팅이다. 잘못된 JSON이 들어와도 컴파일 에러가 나지 않는다. `unknown`을 반환하고 런타임에서 검증하는 게 맞다.

### 조건부 반환 타입에서 추론이 지연된다

```typescript
function wrap<T>(x: T): T extends string ? "string" : "other" {
  return (typeof x === "string" ? "string" : "other") as any;
}

const result = wrap("hello");  // "string" | "other" — "string"이 아니다
```

반환 타입이 조건부 타입이면 TypeScript는 호출 시점에도 분기를 완전히 해소하지 못하는 경우가 있다. `T`가 확정됐는데도 `"string" | "other"`가 나온다. 이런 경우엔 오버로드가 더 명확하다.

```typescript
function wrap(x: string): "string";
function wrap(x: number): "other";
function wrap(x: string | number): "string" | "other" {
  return typeof x === "string" ? "string" : "other";
}

const result = wrap("hello");  // "string"
```

### 겹치는 키가 있는 객체 병합

```typescript
declare function merge<T, U>(a: T, b: U): T & U;

const result = merge({ x: 1 }, { x: "a" });
result.x;  // number & string — never
```

`number & string`은 `never`다. 컴파일 에러는 나지 않지만 `result.x`를 쓸 수 없는 타입이 된다. 나중 객체가 앞의 키를 덮는 게 목적이라면 `T & U`가 아니라 `Omit<T, keyof U> & U`를 반환 타입으로 써야 한다.

### 재귀 깊이 제한

```typescript
type DeepReadonly<T> = {
  readonly [K in keyof T]: T[K] extends object ? DeepReadonly<T[K]> : T[K];
};
```

순환 참조가 있는 타입에 적용하면 컴파일러가 멈추거나 `Type instantiation is excessively deep and possibly infinite` 에러를 낸다. TypeScript의 재귀 한계는 45단계다.

실제로 깊은 중첩 객체에 재귀 타입을 붙이면 에러 메시지가 수십 줄이 되고 어디가 원인인지 추적이 어려워진다. 라이브러리에서 가져다 쓰는 재귀 유틸리티 타입은 어떤 타입에 적용하는지 확인한 후 쓴다.

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

**에러 메시지가 해독 불가능해질 때.** 조건부 타입과 매핑된 타입을 몇 겹 쌓으면 표현은 되지만 에러 메시지가 수십 줄짜리 타입 체인을 뱉는다. 컴파일 에러를 읽고 원인을 짚을 수 없는 수준이면 그 지점이 한계다. 타입으로 증명하는 대신 런타임 검증을 하나 두는 편이 나은 경우가 많다.

## 참고

- [TypeScript Handbook — Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html)
- [TypeScript Handbook — Conditional Types](https://www.typescriptlang.org/docs/handbook/2/conditional-types.html)
- [TypeScript Handbook — Mapped Types](https://www.typescriptlang.org/docs/handbook/2/mapped-types.html)
- [TypeScript Handbook — Type Inference](https://www.typescriptlang.org/docs/handbook/type-inference.html)
- [TypeScript Handbook — keyof Type Operator](https://www.typescriptlang.org/docs/handbook/2/keyof-types.html)
