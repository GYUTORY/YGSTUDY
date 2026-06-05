---
title: TypeScript Interface 심화
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, interface, declaration-merging, module-augmentation]
updated: 2026-06-05
---

# TypeScript Interface 심화

기본 문법은 [Interface.md](Interface.md)에서 다뤘다. 여기서는 실무에서 자주 부딪치는 주제만 모아 정리한다. 선언 병합, 모듈 보강, 인덱스 시그니처, 호출/생성자 시그니처, 제네릭 제약, 함수 오버로드, variance, 그리고 type alias와 어디서 갈리는지를 5년차 백엔드 환경 기준으로 다룬다.

---

## 1. 선언 병합 (Declaration Merging)

### 같은 이름 interface는 자동으로 합쳐진다

`interface` 키워드는 같은 스코프에서 같은 이름으로 여러 번 선언하면 컴파일러가 자동으로 멤버를 합친다. `type alias`로는 안 된다. 같은 이름으로 두 번 쓰면 "Duplicate identifier" 에러가 나온다.

```typescript
interface User {
  id: number;
  name: string;
}

interface User {
  email: string;
  createdAt: Date;
}

// 컴파일러 입장에서는 아래와 동일
const u: User = {
  id: 1,
  name: "홍길동",
  email: "a@b.c",
  createdAt: new Date(),
};
```

병합 규칙은 단순하다.

- 동일 시그니처의 비함수 멤버: 한쪽에만 있으면 그대로 추가된다. 양쪽에 같은 이름이 있고 타입이 다르면 컴파일 에러가 난다.
- 함수 멤버(호출 시그니처): 충돌이 아니라 오버로드로 누적된다. 단, 매칭 순서가 까다롭다.

### 함수 시그니처 오버로드 병합 순서

같은 이름의 메서드를 여러 번 선언하면 오버로드로 쌓인다. 호출 시 매칭은 **나중에 선언된 시그니처가 먼저** 검사된다. 단, 같은 interface 블록 안의 시그니처들은 선언 순서대로 매칭된다.

```typescript
interface Cloner {
  clone(source: string): string;
}

interface Cloner {
  clone(source: number): number;
  clone(source: Date): Date;
}

// 매칭 순서 (위에서 아래로):
// 1. clone(source: number): number     ← 두 번째 블록의 첫 줄
// 2. clone(source: Date): Date         ← 두 번째 블록의 두 번째 줄
// 3. clone(source: string): string     ← 첫 번째 블록
```

순서가 중요한 이유는 유니온이나 좁은 리터럴 타입을 다룰 때 의도하지 않은 시그니처가 잡힐 수 있어서다. 외부 라이브러리 타입을 보강할 때는 가장 일반적인 시그니처가 먼저, 특수 시그니처가 나중에 가도록 두는 게 안전하다. 두 번째 블록에서 더 특수한 케이스를 추가하면 그게 먼저 매칭된다.

### namespace와 interface 병합

namespace를 같은 이름의 interface와 함께 선언하면, namespace 안의 export 멤버는 interface의 정적 속성처럼 붙는다. 정확히는 값 공간(namespace)과 타입 공간(interface)이 한 식별자 아래에 합쳐진다.

```typescript
interface Logger {
  log(msg: string): void;
}

namespace Logger {
  export const DEFAULT_LEVEL = "info";
  export function create(): Logger {
    return { log: (m) => console.log(m) };
  }
}

const l = Logger.create();
l.log("hi");
console.log(Logger.DEFAULT_LEVEL);
```

`Logger`는 타입(인스턴스 형태)이자 값(static 멤버 모음)이다. 예전 jQuery 스타일 타입 정의가 이 패턴을 많이 썼다.

### class와 interface 병합 (mixin)

class와 같은 이름의 interface를 선언하면 class에 그 멤버가 "있다고 약속"하는 형태가 된다. 런타임에 실제 그 멤버를 끼워 넣는 건 mixin 헬퍼가 한다. 컴파일러는 interface 쪽 선언만 보고 통과시킨다.

```typescript
class Timestamped {
  createdAt!: Date;
}

interface Timestamped {
  touch(): void;
}

function applyMixin(target: any) {
  target.prototype.touch = function () {
    this.createdAt = new Date();
  };
}
applyMixin(Timestamped);

const t = new Timestamped();
t.touch();
console.log(t.createdAt);
```

장점은 class 본체에 모든 멤버를 박지 않아도 타입이 통한다는 점이다. 단점은 런타임 mixin 적용을 깜빡하면 `touch()` 호출 시 `undefined is not a function`이 터지는데 컴파일러는 절대 잡아주지 않는다. mixin 적용 코드는 모듈 최상단에 두고 import 시점에 무조건 실행되도록 만들어야 사고가 적다.

---

## 2. 모듈 보강 (Module Augmentation)

### 외부 모듈의 타입에 멤버 추가

Express 미들웨어에서 `req.user`를 채우는 패턴은 거의 모든 NestJS/Express 프로젝트에서 본다. 그런데 그냥 쓰면 `Property 'user' does not exist on type 'Request'` 에러가 난다. Express 타입 정의에 `user`가 없기 때문이다. 모듈 보강으로 추가한다.

```typescript
// src/types/express.d.ts
import "express";

declare module "express-serve-static-core" {
  interface Request {
    user?: {
      id: number;
      roles: string[];
    };
  }
}
```

핵심은 세 가지다.

- 파일 안에 `import` 또는 `export` 가 있어야 한다. 그래야 TS가 이 파일을 "스크립트"가 아닌 "모듈"로 본다. 모듈 보강은 모듈 안에서만 동작한다.
- 보강 대상은 `@types/express`의 실제 모듈명인 `express-serve-static-core`다. `Request` 인터페이스가 거기서 export된다. `declare module "express"` 안에 적어도 동작하지만, 실제 정의가 있는 모듈을 직접 보강하는 게 정확하다.
- `tsconfig.json`의 `include`나 `typeRoots`로 이 `.d.ts` 파일이 컴파일 단위에 잡혀야 한다. 잡히지 않으면 보강이 적용되지 않는다. 실제로 가장 자주 보는 함정이다.

### lodash 같은 외부 모듈 보강

라이브러리 메서드 시그니처를 보강할 때도 같은 방식이다. 단, 메서드를 추가한다고 런타임 구현이 생기지는 않는다. 구현을 prototype에 직접 끼워 넣어야 한다.

```typescript
// src/types/lodash-ext.d.ts
import "lodash";

declare module "lodash" {
  interface LoDashStatic {
    deepFreeze<T>(obj: T): Readonly<T>;
  }
}
```

```typescript
// src/lodash-ext.ts
import _ from "lodash";

_.mixin({
  deepFreeze<T>(obj: T): Readonly<T> {
    Object.values(obj as any).forEach((v) => {
      if (v && typeof v === "object") (_ as any).deepFreeze(v);
    });
    return Object.freeze(obj);
  },
});
```

타입 보강 파일과 런타임 구현 파일은 분리하지만 import 순서가 어긋나면 타입은 통하는데 런타임에서 폭발한다. 진입점에서 `import "./lodash-ext"`를 가장 먼저 두는 게 안전하다.

### 글로벌 보강

`declare global` 블록을 모듈 안에 두면 전역 타입에도 멤버를 추가할 수 있다. NodeJS의 `process.env` 타입을 좁히는 게 흔한 사례다.

```typescript
// src/types/env.d.ts
export {};

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      DATABASE_URL: string;
      JWT_SECRET: string;
      NODE_ENV: "development" | "production" | "test";
    }
  }
}
```

`export {};`는 이 파일을 모듈로 만들기 위한 마커다. `declare global`은 스크립트 파일 안에서는 동작하지 않는다.

`process.env.DATABASE_URL`이 더 이상 `string | undefined`가 아니라 `string`으로 잡힌다. 실제로는 undefined일 수 있으니 부팅 시점 검증과 같이 가야 한다. 타입을 좁혔다고 검증을 생략하면 운영에서 환경변수 누락이 그대로 런타임 에러로 흘러간다.

---

## 3. Index Signature

### 기본 형태와 키 타입

```typescript
interface StringMap {
  [key: string]: string;
}

interface NumericArray {
  [index: number]: number;
}
```

키로 쓸 수 있는 건 `string`, `number`, `symbol`, 그리고 template literal 타입이다. `number` 인덱스 시그니처는 사실 JS에서 `arr[0]`을 호출해도 내부적으로 `arr["0"]`이 되기 때문에, TS는 `number` 인덱스 시그니처의 값 타입이 `string` 인덱스 시그니처의 값 타입에 할당 가능해야 한다는 제약을 둔다.

```typescript
interface Bad {
  [k: string]: number;
  [k: number]: string; // 에러: number index value type이 string index value type에 호환 안 됨
}
```

### 기존 속성과 인덱스 시그니처의 호환성

인덱스 시그니처가 있으면 그 interface의 **모든 명시 속성**이 인덱스 시그니처 값 타입의 서브타입이어야 한다. 이게 실무에서 가장 자주 막히는 지점이다.

```typescript
interface Config {
  [key: string]: string;
  port: number; // 에러: number는 string 인덱스 시그니처와 호환 안 됨
}
```

해결책은 보통 둘 중 하나다.

- 값 타입을 유니온으로 넓힌다: `[key: string]: string | number`
- 특수 키만 따로 빼고 나머지를 별도 맵으로 분리한다: `{ port: number; meta: Record<string, string> }`

후자가 거의 항상 더 깔끔하다. 인덱스 시그니처에 특수 속성을 섞기 시작하면 코드 어느 곳에서든 임의의 키로 접근이 가능해져서 오타를 컴파일러가 못 잡는다.

### Template literal index signature

TS 4.4 이후로 key를 template literal 타입으로 제한할 수 있다. 이벤트 핸들러 패턴이 대표적이다.

```typescript
interface EventHandlers {
  [event: `on${Capitalize<string>}`]: (...args: any[]) => void;
}

const h: EventHandlers = {
  onClick: () => {},
  onSubmit: () => {},
  // click: () => {},   // 에러: 키가 `on...` 형태가 아님
};
```

DB 컬럼명을 카멜케이스로 강제하거나 SDK 메서드 명명 규칙을 타입으로 강제할 때 쓴다. 키 충돌이 많은 흔한 이름은 IDE 자동완성이 어색해지는 단점이 있다.

---

## 4. Call Signature와 Construct Signature

### 호출 시그니처 (Call Signature)

함수 타입을 type alias 대신 interface로 정의할 때 쓴다. 단순 시그니처 하나만 필요하면 `type F = (x: number) => string`가 더 짧지만, 함수에 속성도 같이 붙여야 하면 interface가 거의 강제된다.

```typescript
interface Handler {
  (req: Request): Promise<Response>;
}
```

### 생성자 시그니처 (Construct Signature)

`new` 키워드로 호출되는 함수 타입이다. 클래스를 1급 시민으로 다루는 팩토리 함수에서 매우 자주 쓴다.

```typescript
interface Ctor<T> {
  new (...args: any[]): T;
}

function create<T>(C: Ctor<T>, ...args: any[]): T {
  return new C(...args);
}

class UserRepo {
  constructor(public db: string) {}
}

const r = create(UserRepo, "postgres://...");
```

`typeof UserRepo`를 직접 받을 수도 있는데, 추상 클래스나 generic을 다루려면 명시적 `Ctor<T>` 인터페이스가 더 자유롭다.

추상 클래스를 받으려면 `abstract new (...args: any[]): T` 시그니처가 필요하다. 그냥 `new`로 정의하면 추상 클래스를 인자로 못 받는다.

```typescript
interface AbstractCtor<T> {
  abstract new (...args: any[]): T;
}
```

### Hybrid Type

함수이면서 속성도 갖는 타입이다. jQuery의 `$`가 고전적인 예시다. `$(selector)`로 호출도 되고 `$.ajax(...)`로 메서드 접근도 된다.

```typescript
interface JQueryLike {
  (selector: string): Element | null;
  ajax(url: string): Promise<unknown>;
  version: string;
}

function makeJQuery(): JQueryLike {
  const f = ((selector: string) => document.querySelector(selector)) as JQueryLike;
  f.ajax = (url) => fetch(url).then((r) => r.json());
  f.version = "1.0.0";
  return f;
}
```

실무에선 라이브러리 entry export가 이 패턴인 경우가 많다. `import logger from "./logger"` 했을 때 `logger("msg")`도 되고 `logger.warn("msg")`도 되는 식이다. 직접 만들 일은 줄었고 외부 라이브러리 타입 정의를 읽을 일이 더 많다.

---

## 5. Generic Interface 제약

### extends 제약

제네릭 매개변수에 `extends T`를 붙여 받을 수 있는 타입을 좁힌다.

```typescript
interface Identifiable {
  id: number;
}

interface Repo<T extends Identifiable> {
  findById(id: number): Promise<T | null>;
  save(entity: T): Promise<T>;
}
```

### keyof 제약

키 이름만 받고 싶을 때 쓴다. ORM의 `select` 옵션이 대표적이다.

```typescript
interface QueryBuilder<T> {
  select<K extends keyof T>(...keys: K[]): Pick<T, K>;
}
```

`K extends keyof T`로 막아두면 오타 키를 컴파일러가 잡아준다. 이걸 빼면 임의의 문자열이 들어가서 런타임에 `undefined` 컬럼이 SELECT문에 박힌다.

### 기본 타입 매개변수

```typescript
interface ApiResponse<T = unknown> {
  status: number;
  data: T;
}

const r: ApiResponse = { status: 200, data: { foo: 1 } };
//    ^ T = unknown으로 추론
```

기본값을 두면 호출부에서 매개변수를 생략할 수 있다. `any`보다 `unknown`을 기본값으로 쓰는 게 안전하다. 사용 시점에 narrowing을 강제하니까.

### Conditional 제약

조건부 타입을 제약으로 쓰는 패턴이다. 매개변수 타입에 따라 메서드 시그니처가 달라지는 경우다.

```typescript
interface Cache<K, V> {
  get(key: K): V extends Promise<infer U> ? Promise<U | null> : V | null;
  set(key: K, value: V): void;
}
```

V가 Promise면 get도 Promise로 풀어주고, 아니면 동기 반환을 약속한다. 호출부에서는 타입 분기 없이 사용 가능하지만, 정의가 무거워지니 정말 필요한 곳에만 쓴다.

---

## 6. Interface vs Type Alias 실무 차이

선언 병합 가능 여부 외에도 차이가 더 있다.

### 컴파일 성능

TS 컴파일러는 interface를 캐시하기 좋게 다룬다. type alias는 매번 평가될 수 있다. 대규모 코드베이스에서 깊이 중첩된 union/intersection을 type으로만 짜면 컴파일이 눈에 띄게 느려진다. 객체 형태가 명확한 도메인 타입은 interface로 두는 게 컴파일 시간 측면에서 유리하다.

### 에러 메시지

```typescript
interface User {
  id: number;
  name: string;
}

type UserAlias = {
  id: number;
  name: string;
};

function f(u: User) {}
function g(u: UserAlias) {}

f({ id: 1, name: 2 as any });
// Type '{ id: number; name: any; }' is not assignable to parameter of type 'User'.
//                                                                        ^^^^^

g({ id: 1, name: 2 as any });
// Type '{ id: number; name: any; }' is not assignable to parameter of type '{ id: number; name: string; }'.
//                                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

interface는 이름이 그대로 노출되어 에러 메시지가 짧고 잡기 쉽다. type alias는 종종 풀어쓴 형태가 그대로 찍혀서 메시지가 길어진다. 도메인 핵심 타입은 이름이 살아남도록 interface로 두는 게 디버깅에 유리하다.

### 재귀 타입

type alias로 재귀를 정의하면 일부 케이스에서 "Type alias 'X' circularly references itself" 에러가 난다. interface는 같은 자기참조에서 더 관대하다.

```typescript
interface TreeNode {
  value: number;
  children: TreeNode[]; // OK
}

type TreeNodeT = {
  value: number;
  children: TreeNodeT[]; // 이것도 OK
};

type Bad = Bad[]; // 에러: 직접 자기참조
interface Good extends Array<Good> {} // 동일 의미인데 통과
```

직접 재귀가 필요한 트리/그래프 타입은 interface로 정의하는 게 안정적이다.

### 정리

union이나 mapped/conditional 타입이 본질인 경우엔 type alias가 맞다. 객체의 모양을 묘사하는 도메인 타입, 라이브러리 보강이 필요한 타입, 클래스가 implements 할 타입은 interface로 두는 게 거의 항상 낫다.

---

## 7. Interface 안의 함수 오버로드 시그니처

같은 메서드 이름에 시그니처를 여러 개 적어 오버로드를 정의한다. 매칭 순서는 위에서 아래로 첫 번째 호환되는 시그니처가 잡힌다. 따라서 **특수한 시그니처를 먼저, 일반적인 시그니처를 나중에** 두어야 한다.

```typescript
interface Reader {
  read(path: string, encoding: "utf8"): string;
  read(path: string, encoding: "buffer"): Buffer;
  read(path: string): Buffer;
}

declare const r: Reader;
const a = r.read("a.txt", "utf8");   // string
const b = r.read("a.txt", "buffer"); // Buffer
const c = r.read("a.txt");           // Buffer
```

순서를 바꾸면 첫 시그니처가 너무 일반적이라 뒤의 시그니처가 매칭되지 않는다. Node의 `fs.readFile`이 이 순서를 정확히 따른다. 외부 타입을 읽을 때 헷갈리는 동작이 있다면 시그니처 순서부터 본다.

구현부에서는 호출 시그니처를 모두 포괄하는 한 개의 구현 시그니처를 두고 분기한다.

```typescript
function read(path: string, encoding: "utf8"): string;
function read(path: string, encoding: "buffer"): Buffer;
function read(path: string): Buffer;
function read(path: string, encoding?: "utf8" | "buffer"): string | Buffer {
  // 실제 구현
  return encoding === "utf8" ? "" : Buffer.alloc(0);
}
```

구현 시그니처는 외부에 노출되지 않는다. 호출부에서는 오버로드 시그니처만 본다.

---

## 8. Variance (공변·반공변)

타입 시스템이 함수 타입의 매개변수와 반환값을 어떻게 다루는지의 문제다. TS는 기본적으로 매개변수에 대해 **bivariant**하다. 즉, 매개변수가 더 좁든 더 넓든 통과시킨다. 이건 타입 안전성 측면에서 구멍이지만 호환성을 위해 남겨둔 동작이다.

### strictFunctionTypes 플래그

`strictFunctionTypes: true`를 켜면 함수 매개변수는 **반공변(contravariant)** 으로 검사된다. 반환값은 그대로 공변이다.

```typescript
class Animal {}
class Dog extends Animal { bark() {} }

type Handler = (a: Animal) => void;
const dogHandler: (d: Dog) => void = (d) => d.bark();

let h: Handler = dogHandler;
// strictFunctionTypes off: 통과 (잘못된 동작)
// strictFunctionTypes on: 에러
// Type '(d: Dog) => void' is not assignable to type 'Handler'.
```

`Animal`을 받기로 한 자리에 `Dog`만 받는 함수를 꽂으면 `Cat` 인스턴스가 들어왔을 때 `bark()`를 호출하다 폭발한다. 그래서 매개변수는 반공변이 옳다.

### 메서드 시그니처 vs 함수 속성

여기가 함정이다. `strictFunctionTypes`는 **함수 속성(property)** 에만 적용되고, **메서드 시그니처(method signature)** 에는 적용되지 않는다. 즉 같은 동작을 두 표기로 적으면 검사 결과가 달라진다.

```typescript
interface A {
  handle: (x: Animal) => void; // 함수 속성 → 반공변 검사
}

interface B {
  handle(x: Animal): void; // 메서드 시그니처 → bivariant 검사
}
```

`Array<T>` 같은 표준 라이브러리 타입이 메서드 시그니처를 쓰는 이유가 이거다. `push`나 `forEach` 콜백을 함수 속성으로 정의하면 `T[]`에 서브타입을 못 꽂는 등 호환성이 망가진다.

실무에서의 결론은 단순하다. 매개변수 타입 검사를 엄격하게 받고 싶으면 함수 속성 표기, 라이브러리처럼 유연한 호환성이 필요하면 메서드 표기를 쓴다. 대부분의 도메인 코드는 함수 속성 표기가 안전하다.

---

## 9. 실전 트러블슈팅

### 인덱스 시그니처를 가진 타입에 더 좁은 속성 추가가 안 된다

```typescript
interface Headers {
  [key: string]: string;
  authorization: string; // OK (string 호환)
  retries: number;       // 에러
}
```

3절에서 다룬 호환성 규칙 때문이다. 해결은 보통 둘 중 하나다.

- 값 타입을 유니온으로 넓히기: `[key: string]: string | number` — 호출부의 좁힘이 귀찮아진다
- 인덱스 시그니처와 좁은 속성을 분리: `interface Headers { common: Record<string, string>; meta: { retries: number } }`

후자가 거의 항상 더 나은 설계다. 하나의 객체에 임의 키 맵과 도메인 속성을 섞지 않는다.

### 병합된 interface가 의도와 다르게 동작한다

같은 이름의 interface가 여러 파일에 흩어져 있고, 한쪽에서 추가한 메서드가 자동완성에는 뜨는데 호출은 안 잡히거나 그 반대 상황이 생긴다. 거의 항상 다음 셋 중 하나다.

1. `declare module` 안에서 보강했는데 그 `.d.ts` 파일이 `tsconfig.json`의 `include`에 잡히지 않는다. `tsc --listFiles` 출력으로 보강 파일이 포함됐는지 확인한다.
2. 보강 대상 모듈명이 잘못됐다. `@types/express` 보강은 `express`가 아니라 `express-serve-static-core`다. 패키지마다 실제 export 모듈이 어디인지 `node_modules/@types/.../index.d.ts`를 직접 열어 확인한다.
3. 보강 파일에 `import`/`export`가 하나도 없어서 TS가 스크립트 파일로 본다. `export {};`를 추가한다.

### "Property does not exist on type {}" 에러

빈 객체 `{}`나 `Record<string, never>` 비슷한 타입을 그대로 들고 다니다가 속성 접근에서 터지는 경우다. 원인은 보통 두 가지다.

- 제네릭 기본값 추론 실패: `function f<T = {}>(x: T)` 같은 시그니처에 인자를 안 넘기면 `T`가 `{}`로 잡히고, 이후 `x.foo`는 에러다. 호출부에서 명시적으로 제네릭을 지정하거나 기본값을 `Record<string, unknown>`으로 두는 게 낫다.
- spread 결과 타입: `const merged = { ...a, ...b }`에서 `a`, `b` 타입이 추론되지 않으면 `merged`가 `{}`로 잡힌다. spread 원본 타입을 명시한다.

`as` 캐스팅으로 덮으면 당장은 통과하지만 진짜 원인은 항상 위 둘 중 하나다. 캐스팅 전에 한 번만 더 들여다본다.

### 보강은 했는데 IDE만 안 잡는 경우

타입은 통과하는데 IDE 자동완성에 보강 멤버가 안 뜬다. 거의 항상 IDE의 TS 서버가 다른 `tsconfig.json`을 보거나 캐시가 오래된 거다. VS Code면 "TypeScript: Restart TS Server"를 실행한다. WebStorm이면 "Invalidate Caches"를 한 번 돌린다. 컴파일러는 옳게 보고 있는데 IDE만 늦는 사례가 의외로 많다.

---

## 정리

interface의 깊은 동작은 결국 세 가지 축으로 모인다. 선언 병합으로 같은 이름이 합쳐진다는 점, 인덱스 시그니처와 명시 속성 사이의 호환성 규칙, 그리고 메서드 표기와 함수 속성 표기가 variance 검사에서 갈린다는 점. 이 셋만 정확히 잡고 있으면 외부 라이브러리 타입 정의를 읽거나 보강할 때, 그리고 대규모 도메인 타입을 설계할 때 거의 모든 함정을 미리 피한다.
