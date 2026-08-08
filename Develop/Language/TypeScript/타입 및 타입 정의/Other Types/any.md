---
title: TypeScript any 타입
tags: [language, typescript]
updated: 2026-07-25
---

# TypeScript any 타입

## 배경

`any`는 TypeScript의 타입 검사를 사실상 끄는 타입이다. 변수에 `any`를 붙이면 컴파일러는 그 변수에 대한 검사를 포기하고, 어떤 값을 넣든 어떤 멤버에 접근하든 오류를 내지 않는다. JavaScript에서 그대로 넘어온 동적 동작을 TypeScript에서 표현할 때 쓴다.

`any`는 거의 항상 문제를 만들기 때문에, "왜 쓰는지"보다 "왜 쓰면 안 되는지"를 먼저 이해하는 편이 낫다.

### any가 등장하는 상황
- 타입 정의가 없는 외부 JavaScript 라이브러리를 빠르게 붙여 쓸 때
- 외부 API 응답 형태를 아직 모르는 경우
- 기존 JavaScript 프로젝트를 TypeScript로 단계적으로 옮기는 과정에서 임시 처리할 때
- 프로토타이핑 단계에서 타입 정의에 시간을 쓰기 어려운 경우

### any를 쓰면 잃는 것
- 컴파일러의 타입 검사: 잘못된 프로퍼티 접근, 잘못된 타입 할당이 모두 통과된다
- 런타임 안전성: 빌드는 되는데 운영에서 `Cannot read property of undefined` 같은 오류로 터진다
- IDE의 자동완성과 리팩터링 지원이 사라진다
- `any`는 전염성이 있어서 그 값을 다루는 다른 변수까지 타입 정보를 잃는다

## any 타입 기본 사용법

### 변수 선언

```typescript
let value: any = 42;
value = "안녕하세요";
value = true;
value = { name: "홍길동" };
value = [1, 2, 3];

// 어떤 멤버에 접근해도 컴파일러가 막지 않음
console.log(value.length);
console.log(value.toUpperCase());
console.log(value.foo.bar.baz);
```

위 코드는 전부 컴파일 통과한다. `value`에 boolean이 들어 있을 때 `length`를 읽거나 `toUpperCase`를 호출하면 런타임에서 터진다.

### 함수 매개변수와 반환값

```typescript
function processData(data: any): any {
    return data;
}

const result1 = processData("문자열");
const result2 = processData(123);
const result3 = processData({ id: 1, name: "홍길동" });
```

이런 시그니처는 함수의 타입 정보를 의미없게 만든다. 호출부에서도 반환값이 `any`이기 때문에 그 뒤로 타입 검사가 계속 풀린 채로 흘러간다.

## any 타입의 위험성

### 타입 검사 우회

```typescript
let user: any = { name: "홍길동", age: 25 };

user.nonExistentMethod();   // 컴파일 통과, 런타임 오류
user.age = "스물다섯";       // 컴파일 통과, 이후 숫자로 다루면 오류
user = null;
user.name;                  // 컴파일 통과, 런타임에서 TypeError
```

### any의 전염성

```typescript
const raw: any = JSON.parse(input);
const user = raw.user;            // user도 any
const name = user.name;           // name도 any
const upper = name.toUpperCase(); // 여전히 any, 검사 없음
```

`any`로 시작한 값에서 파생된 변수는 전부 `any`가 된다. 코드의 일부에만 `any`를 두려고 했어도, 아무도 의식하지 않으면 모듈 전체로 퍼져나가는 경우가 흔하다.

## JSON.parse와 fetch().json()이 any를 반환하는 이유

`lib.es5.d.ts`와 `lib.dom.d.ts`를 열어보면 이렇게 정의되어 있다.

```typescript
// lib.es5.d.ts
interface JSON {
    parse(text: string, reviver?: (this: any, key: string, value: any) => any): any;
}

// lib.dom.d.ts
interface Body {
    json(): Promise<any>;
}
```

런타임에 실제로 어떤 값이 나올지 컴파일 시점에 알 수 없기 때문에 `any`로 박혀 있다. `noImplicitAny`를 켜도 이 자리에서 에러가 나지 않는다. 컴파일러가 암묵적으로 만든 `any`가 아니라, 타입 정의 파일에 명시적으로 적힌 `any`이기 때문이다.

이 문제를 다루는 실무 패턴은 래퍼 함수를 만들어 `unknown`으로 반환 타입을 좁히는 것이다.

```typescript
function parseJson(text: string): unknown {
    return JSON.parse(text);
}

async function fetchJson(url: string): Promise<unknown> {
    const res = await fetch(url);
    return res.json();
}
```

래퍼 없이 `as UserData`로 단언하는 코드가 흔히 보이는데, 서버 응답 스키마가 바뀌는 순간 조용히 망가진다. 래퍼를 만들면 사용하는 쪽에서 반드시 좁히기를 거쳐야 하므로, 경계 지점에서 검증이 누락되는 상황을 막을 수 있다.

## noImplicitAny와 strict 설정 시 실제 문제

`strict: true`를 켜면 `noImplicitAny`가 함께 활성화된다. 기존 코드베이스에 처음 켰을 때 흔히 마주치는 문제들이 있다.

### 콜백 매개변수

```typescript
// noImplicitAny: true
const fn = function(x) {  // error TS7006: Parameter 'x' implicitly has an 'any' type.
    return x;
};
```

`Array.prototype.forEach` 같은 배열 메서드 콜백은 컨텍스트 타입이 흘러들어와 추론이 되지만, 단독 함수 표현식에서 매개변수 타입이 없으면 에러가 난다.

### 이벤트 핸들러 분리

```typescript
// addEventListener에 직접 넘기면 MouseEvent로 추론됨
document.addEventListener('click', function(e) {
    console.log(e.clientX);
});

// 별도 변수로 분리하면 에러
const handleClick = function(e) {  // error: 'e' implicitly has an 'any' type.
    console.log(e.clientX);
};
```

같은 콜백이지만 `addEventListener`에 직접 넘기면 컨텍스트 타입 덕분에 추론이 되고, 별도 변수로 분리하면 에러가 난다. `(e: MouseEvent) => void`처럼 타입을 명시하거나 `EventListener` 타입으로 선언해야 한다.

### 동적 인덱싱

```typescript
const obj = { a: 1, b: 2 };
const key: string = "a";
const val = obj[key];
// error TS7053: Element implicitly has an 'any' type because expression of type
// 'string' can't be used to index type '{ a: number; b: number; }'.
```

`keyof typeof obj`로 단언하면 통과되지만, 잘못된 키가 들어와도 `undefined`가 `number`로 취급되는 문제가 생긴다. `noUncheckedIndexedAccess`를 함께 켜면 인덱스 결과가 `T | undefined`로 잡혀서 더 안전하다.

### catch 블록의 error 타입

`strict`에 포함된 `useUnknownInCatchVariables`가 켜지면 catch 변수의 타입이 `any`에서 `unknown`으로 바뀐다. 기존에 `e.message`를 그냥 쓰던 코드가 전부 에러가 난다.

```typescript
try {
    // ...
} catch (e) {
    // strict 이전: e가 any라 e.message 바로 접근 가능
    // strict 이후: e가 unknown이라 instanceof 검사 필요
    if (e instanceof Error) {
        console.error(e.message);
    }
}
```

## ESLint no-explicit-any 실전 설정

`@typescript-eslint/no-explicit-any`는 코드에 명시적으로 적힌 `any`를 잡는다. `noImplicitAny`가 잡지 못하는 의도적 `any`를 추가로 막는 용도다.

```json
{
    "rules": {
        "@typescript-eslint/no-explicit-any": ["error", {
            "fixToUnknown": false,
            "ignoreRestArgs": false
        }]
    }
}
```

### ignoreRestArgs 옵션

`ignoreRestArgs: true`로 켜면 rest 매개변수 자리의 `any`는 허용한다.

```typescript
// ignoreRestArgs: false (기본값) → 에러
function log(...args: any[]): void {
    console.log(...args);
}

// ignoreRestArgs: true → 에러 없음
function log(...args: any[]): void {
    console.log(...args);
}
```

로깅 유틸, 가변 인자를 그대로 전달하는 래퍼 함수처럼 인자 타입을 알 수 없거나 고정할 수 없는 케이스에서 유용하다. 남발하면 규칙의 의미가 없어지므로, 정말 필요한 파일에만 적용하는 편이 낫다.

### 의도적 any 사용 시 eslint-disable 관례

`any`를 써야 하는 자리가 있을 때는 줄 단위 비활성화 주석과 이유를 같이 남긴다.

```typescript
// 외부 SDK가 반환 타입을 any로 정의해 래핑이 불가한 상황
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function bridgeLegacySdk(input: string): unknown {
    return legacySdk.process(input) as any;
}
```

이유 주석 없이 `eslint-disable`만 달려 있는 코드는 코드 리뷰에서 반드시 되물어야 한다. 의도적인 `any`인지 잊혀진 `any`인지 구분하기 위해서다. 마이그레이션 중인 파일이나 레거시 어댑터 모듈처럼 범위가 명확하다면, 파일 단위로 끄는 방식을 `overrides`로 관리한다.

```json
{
    "overrides": [
        {
            "files": ["src/legacy/**/*.ts", "tests/**/*.ts"],
            "rules": {
                "@typescript-eslint/no-explicit-any": "off"
            }
        }
    ]
}
```

## any 대신 쓸 수 있는 것

### unknown

타입을 모르는 값을 받을 때는 거의 대부분 `unknown`이 낫다. `unknown`은 `any`처럼 어떤 값이든 받지만, 사용하기 전에 타입 검사를 강제한다.

```typescript
let value: unknown = 42;

if (typeof value === "string") {
    console.log(value.toUpperCase());
} else if (typeof value === "number") {
    console.log(value.toFixed(2));
}
```

`unknown`은 타입 가드를 거치지 않으면 어떤 멤버에도 접근할 수 없다. 컴파일러가 "확인하고 써라"라고 강제하는 셈이다.

### 제네릭

함수가 입력 타입과 반환 타입을 그대로 이어줘야 할 때는 `any` 대신 제네릭을 쓴다.

```typescript
function processData<T>(data: T): T {
    return data;
}

const result1 = processData("문자열"); // string
const result2 = processData(123);       // number
```

호출부에서 타입이 자동으로 추론되기 때문에 검사가 풀리지 않는다.

## 실제 사용 사례

### 외부 API 응답

`fetch().json()`의 반환 타입이 `any`라서 그냥 쓰면 타입 검사 없이 흘러간다. 런타임 검증 라이브러리를 쓰면 스키마 정의와 타입 좁히기를 한 번에 처리할 수 있다.

```typescript
import { z } from "zod";

const UserSchema = z.object({
    id: z.number(),
    name: z.string(),
    email: z.string().email(),
});

async function fetchUser(id: number) {
    const res = await fetch(`/api/users/${id}`);
    const data: unknown = await res.json();
    return UserSchema.parse(data); // 스키마 불일치 시 런타임 에러를 던짐
}
```

직접 타입 가드를 만드는 경우에는 타입 술어(type predicate)를 쓴다. 외부 입력을 받는 모든 경계 지점(API 응답, 폼 입력, 메시지 큐 페이로드)에 적용할 수 있다.

```typescript
interface User {
    id: number;
    name: string;
    email: string;
}

function isUser(data: unknown): data is User {
    return (
        typeof data === 'object' &&
        data !== null &&
        typeof (data as User).id === 'number' &&
        typeof (data as User).name === 'string' &&
        typeof (data as User).email === 'string'
    );
}

async function fetchUser(id: number): Promise<User | null> {
    const res = await fetch(`/api/users/${id}`);
    const data: unknown = await res.json();
    return isUser(data) ? data : null;
}
```

### 레거시 라이브러리 연동

타입 정의가 없는 외부 라이브러리를 임시로 쓸 때만 `any`를 허용한다. 사용 범위를 한 함수, 한 모듈로 좁혀야 한다.

```typescript
declare const legacyLibrary: any;

function useLegacyLibrary(): unknown {
    const result = legacyLibrary.processData("some data");
    return result;
}
```

`legacyLibrary` 자체는 `any`로 두더라도, 함수 반환 타입은 `unknown`으로 좁혀서 외부로 `any`가 새어 나가지 않게 막는다. `any`의 전염을 막는 가장 단순한 방법이다.

## any vs unknown vs object 비교

| 특징 | any | unknown | object |
|------|-----|---------|--------|
| 타입 검사 | 없음 | 필요 | 필요 |
| 할당 가능성 | 모든 타입 | 모든 타입 | 객체만 |
| 안전성 | 낮음 | 높음 | 높음 |
| 사용 목적 | 타입 검사 우회 | 타입 미상의 안전한 처리 | 객체 타입 표현 |

세 타입 모두 "어떤 값인지 미리 모를 때" 쓰지만, `any`는 검사를 끄는 쪽이고 `unknown`과 `object`는 검사를 유지하면서 범위를 좁히는 쪽이다. 실무에서는 `any`를 기본값으로 두지 말고, 정말 검사를 풀어야 하는 이유가 있을 때만 예외적으로 사용해야 한다.

## 실무에서 any를 다루는 방법

`any`를 완전히 금지하는 것은 비현실적이다. 외부 라이브러리 타입이 부족하거나, 마이그레이션 중인 코드, 동적 메타프로그래밍이 들어간 곳에서는 일시적으로 `any`가 필요하다.

사용 범위를 최대한 좁혀야 한다. 한 변수에 머무르도록, 또는 한 함수의 내부 구현에만 머무르도록 격리한다. 외부로 노출되는 시그니처에는 `any` 대신 `unknown`을 쓰고, 안에서만 타입 단언으로 풀어 쓰는 방식이 흔히 쓰인다.

`tsconfig.json`의 `noImplicitAny: true` 옵션은 켜둬야 한다. 이 옵션이 꺼져 있으면 타입을 명시하지 않은 매개변수가 자동으로 `any`가 되고, 코드베이스 전체에 의도하지 않은 `any`가 깔린다.

심화 사용 패턴, 점진적 마이그레이션 전반의 흐름, ESLint 규칙 심층 설정 등은 [Any_Type_Deep_Dive](Any_Type_Deep_Dive.md)에서 다룬다.
