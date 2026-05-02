---
title: TypeScript any 타입
tags: [language, typescript, 타입-및-타입-정의, typescript-types, other-types, any]
updated: 2026-05-02
---

# TypeScript any 타입

## 배경

`any`는 TypeScript의 타입 검사를 사실상 끄는 타입입니다. 변수에 `any`를 붙이면 컴파일러는 그 변수에 대한 검사를 포기하고, 어떤 값을 넣든 어떤 멤버에 접근하든 오류를 내지 않습니다. JavaScript에서 그대로 넘어온 동적 동작을 TypeScript에서 표현해야 할 때 사용합니다.

다만 실무에서 `any`는 거의 항상 문제를 만들기 때문에, "왜 쓰는지"보다 "왜 쓰면 안 되는지"를 먼저 이해하는 편이 낫습니다.

### any가 등장하는 상황
- 타입 정의가 없는 외부 JavaScript 라이브러리를 빠르게 붙여 쓸 때
- 외부 API 응답 형태를 아직 모르는 경우
- 기존 JavaScript 프로젝트를 TypeScript로 단계적으로 옮기는 과정에서 임시 처리할 때
- 프로토타이핑 단계에서 타입 정의에 시간을 쓰기 어려운 경우

### any를 쓰면 잃는 것
- 컴파일러의 타입 검사: 잘못된 프로퍼티 접근, 잘못된 타입 할당이 모두 통과합니다
- 런타임 안전성: 빌드는 되는데 운영에서 `Cannot read property of undefined` 같은 오류로 터집니다
- IDE의 자동완성과 리팩터링 지원이 사라집니다
- `any`는 전염성이 있어서 그 값을 다루는 다른 변수까지 타입 정보를 잃습니다

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

위 코드는 전부 컴파일 통과합니다. 하지만 `value`에 boolean이 들어 있을 때 `length`를 읽거나 `toUpperCase`를 호출하면 런타임에서 터집니다.

### 함수 매개변수와 반환값

```typescript
function processData(data: any): any {
    return data;
}

const result1 = processData("문자열");
const result2 = processData(123);
const result3 = processData({ id: 1, name: "홍길동" });
```

이런 시그니처는 사실상 함수의 타입 정보를 의미가 없게 만듭니다. 호출부에서도 반환값이 `any`이기 때문에 그 뒤로 타입 검사가 계속 풀린 채로 흘러갑니다.

## any 타입의 위험성

### 타입 검사 우회

```typescript
let user: any = { name: "홍길동", age: 25 };

user.nonExistentMethod();   // 컴파일 통과, 런타임 오류
user.age = "스물다섯";       // 컴파일 통과, 이후 숫자로 다루면 오류
user = null;
user.name;                  // 컴파일 통과, 런타임에서 TypeError
```

### 런타임 오류로 이어지는 패턴

```typescript
function calculateArea(shape: any): number {
    return shape.width * shape.height;
}

const result = calculateArea({ width: "10", height: 5 });
// "10" * 5 = 50처럼 보이지만 입력이 조금만 달라지면 NaN이 됨
// 예: { width: "10cm", height: 5 } → NaN
```

`any`로 받은 값은 컴파일러가 검증을 안 해주기 때문에, 호출부에서 잘못된 데이터를 넘겼을 때 함수 안쪽에서 조용히 망가집니다. 이런 코드는 보통 운영 환경에서 처음 발견됩니다.

### any의 전염성

```typescript
const raw: any = JSON.parse(input);
const user = raw.user;        // user도 any
const name = user.name;       // name도 any
const upper = name.toUpperCase(); // 여전히 any, 검사 없음
```

`any`로 시작한 값에서 파생된 변수는 전부 `any`가 됩니다. 코드의 일부에만 `any`를 두려고 했어도, 아무도 의식하지 않으면 모듈 전체로 퍼져나가는 경우가 흔합니다.

## any 대신 쓸 수 있는 것

### unknown

타입을 모르는 값을 받을 때는 거의 대부분 `unknown`이 더 낫습니다. `unknown`은 `any`처럼 어떤 값이든 받지만, 사용하기 전에 타입 검사를 강제합니다.

```typescript
let value: unknown = 42;

if (typeof value === "string") {
    console.log(value.toUpperCase());
} else if (typeof value === "number") {
    console.log(value.toFixed(2));
}
```

`unknown`은 타입 가드를 거치지 않으면 어떤 멤버에도 접근할 수 없습니다. 컴파일러가 "확인하고 써라"라고 강제하는 셈입니다.

### 제네릭

함수가 입력 타입과 반환 타입을 그대로 이어 줘야 할 때는 `any`가 아니라 제네릭을 씁니다.

```typescript
function processData<T>(data: T): T {
    return data;
}

const result1 = processData("문자열"); // string
const result2 = processData(123);       // number
```

호출부에서 타입이 자동으로 추론되기 때문에 검사가 풀리지 않습니다.

## 실제 사용 사례

### 외부 API 응답

응답 스키마를 모르거나 신뢰할 수 없을 때, `any`로 받기보다는 `unknown`으로 받고 타입 가드로 좁히는 편이 안전합니다.

```typescript
async function fetchExternalData(): Promise<unknown> {
    const response = await fetch('https://api.example.com/data');
    return response.json();
}

async function processExternalData() {
    const data = await fetchExternalData();

    if (typeof data === 'object' && data !== null && 'users' in data) {
        const users = (data as { users: unknown }).users;
        if (Array.isArray(users)) {
            for (const user of users) {
                if (typeof user === 'object' && user !== null && 'name' in user) {
                    const name = (user as { name: unknown }).name;
                    if (typeof name === 'string') {
                        console.log(name);
                    }
                }
            }
        }
    }
}
```

코드가 길어 보이지만, 이 검증을 한 번 해두면 그 뒤로는 타입이 좁혀진 상태에서 안전하게 다룰 수 있습니다. 실제 프로젝트에서는 zod, io-ts, valibot 같은 런타임 검증 라이브러리를 쓰면 검증 코드를 훨씬 간결하게 만들 수 있습니다.

### 레거시 라이브러리 통합

타입 정의가 없는 외부 라이브러리를 임시로 쓸 때만 `any`를 허용합니다. 이때도 사용 범위를 한 함수, 한 모듈로 좁혀야 합니다.

```typescript
declare const legacyLibrary: any;

function useLegacyLibrary(): unknown {
    const result = legacyLibrary.processData("some data");
    return result;
}
```

`legacyLibrary` 자체는 `any`로 두더라도, 함수 반환 타입은 `unknown`으로 좁혀서 외부로 `any`가 새어 나가지 않게 막습니다. 이것이 `any`의 전염을 막는 가장 단순한 방법입니다.

## 타입 가드로 안전하게 좁히기

`any`나 `unknown`으로 받은 값을 안전하게 사용하려면 타입 술어(type predicate)를 쓰는 사용자 정의 타입 가드를 만듭니다.

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

function processData(data: unknown): User | null {
    if (isUser(data)) {
        return data;
    }
    return null;
}
```

이 패턴은 외부 입력을 받는 모든 경계 지점(API 응답, 폼 입력, 메시지 큐 페이로드)에 적용할 수 있습니다.

## any vs unknown vs object 비교

| 특징 | any | unknown | object |
|------|-----|---------|--------|
| 타입 검사 | 없음 | 필요 | 필요 |
| 할당 가능성 | 모든 타입 | 모든 타입 | 객체만 |
| 안전성 | 낮음 | 높음 | 높음 |
| 사용 목적 | 타입 검사 우회 | 타입 미상의 안전한 처리 | 객체 타입 표현 |

세 타입 모두 "어떤 값인지 미리 모를 때" 쓰지만, `any`는 검사를 끄는 쪽이고 `unknown`과 `object`는 검사를 유지하면서 범위를 좁히는 쪽입니다. 실무에서는 `any`를 기본값으로 두지 말고, 정말 검사를 풀어야 하는 이유가 있을 때만 예외적으로 사용해야 합니다.

## 실무에서 any를 다루는 방법

`any`를 완전히 금지하는 것은 비현실적입니다. 외부 라이브러리 타입이 부족하거나, 마이그레이션 중인 코드, 동적 메타프로그래밍이 들어간 곳에서는 일시적으로 `any`가 필요합니다.

대신 사용 범위를 최대한 좁혀야 합니다. 한 변수에 머무르도록, 또는 한 함수의 내부 구현에만 머무르도록 격리합니다. 외부로 노출되는 시그니처에는 `any` 대신 `unknown`을 쓰고, 안에서만 타입 단언으로 풀어 쓰는 방식이 흔히 사용됩니다.

`any`를 쓸 수밖에 없을 때는 `eslint-disable-next-line @typescript-eslint/no-explicit-any` 주석을 함께 남기고, 그 위에 왜 `any`가 필요한지 한 줄로 적어 두는 편이 좋습니다. 시간이 지나 다른 사람이 그 코드를 봤을 때, 의도적인 `any`인지 잊혀진 `any`인지 구분할 수 있어야 합니다.

`tsconfig.json`의 `noImplicitAny: true` 옵션은 켜둬야 합니다. 이 옵션이 꺼져 있으면 타입을 명시하지 않은 매개변수가 자동으로 `any`가 되고, 코드베이스 전체에 의도하지 않은 `any`가 깔리게 됩니다.

심화 사용 패턴, 점진적 마이그레이션 전반의 흐름, ESLint 규칙 설정 등은 [Any_Type_Deep_Dive](Any_Type_Deep_Dive.md)에서 다룹니다.
