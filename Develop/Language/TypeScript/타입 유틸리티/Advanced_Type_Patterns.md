---
title: TypeScript 고급 타입 패턴 가이드
tags: [typescript, conditional-types, mapped-types, template-literal, type-guard, discriminated-union, infer]
updated: 2026-03-01
---

# TypeScript 고급 타입 패턴

## 개요

TypeScript의 타입 시스템은 **튜링 완전**하다. 조건부 타입, 매핑 타입, 템플릿 리터럴 타입 등을 조합하면 런타임 에러를 컴파일 타임에 잡는 강력한 타입 안전성을 확보할 수 있다.

## 핵심

### 1. Conditional Types (조건부 타입)

타입 레벨의 `if/else`이다.

```typescript
// 기본 형태: T extends U ? X : Y
type IsString<T> = T extends string ? true : false;

type A = IsString<'hello'>;  // true
type B = IsString<42>;       // false

// 실전: API 응답 타입 분기
type ApiResponse<T> = T extends 'user'
    ? { id: number; name: string }
    : T extends 'order'
    ? { id: number; amount: number }
    : never;

type UserRes = ApiResponse<'user'>;   // { id: number; name: string }
type OrderRes = ApiResponse<'order'>; // { id: number; amount: number }
```

#### infer 키워드

조건부 타입 내에서 **타입을 추론**한다.

```typescript
// 함수의 반환 타입 추출
type ReturnType<T> = T extends (...args: any[]) => infer R ? R : never;

type Fn = (x: number) => string;
type Result = ReturnType<Fn>;  // string

// Promise의 내부 타입 추출
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;

type A = UnwrapPromise<Promise<string>>;  // string
type B = UnwrapPromise<number>;           // number

// 배열 요소 타입 추출
type ElementType<T> = T extends (infer E)[] ? E : never;
type C = ElementType<string[]>;  // string

// 함수 첫 번째 파라미터 타입
type FirstParam<T> = T extends (first: infer F, ...rest: any[]) => any ? F : never;
type D = FirstParam<(name: string, age: number) => void>;  // string
```

### 2. Mapped Types (매핑 타입)

기존 타입의 각 프로퍼티를 **변환**하여 새 타입을 만든다.

```typescript
// 기본 형태
type Readonly<T> = {
    readonly [K in keyof T]: T[K];
};

type Partial<T> = {
    [K in keyof T]?: T[K];
};

// 실전: 모든 필드를 nullable로
type Nullable<T> = {
    [K in keyof T]: T[K] | null;
};

interface User {
    id: number;
    name: string;
    email: string;
}

type NullableUser = Nullable<User>;
// { id: number | null; name: string | null; email: string | null }
```

#### Key Remapping (키 재매핑, TS 4.1+)

```typescript
// 키 이름 변환
type Getters<T> = {
    [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

type UserGetters = Getters<User>;
// { getId: () => number; getName: () => string; getEmail: () => string }

// 특정 타입의 키만 선택
type StringKeys<T> = {
    [K in keyof T as T[K] extends string ? K : never]: T[K];
};

type StringProps = StringKeys<User>;
// { name: string; email: string }  (id는 number이므로 제외)
```

### 3. Template Literal Types (템플릿 리터럴 타입)

문자열 리터럴을 **타입 레벨에서 조합**한다.

```typescript
type EventName = 'click' | 'focus' | 'blur';
type Handler = `on${Capitalize<EventName>}`;
// 'onClick' | 'onFocus' | 'onBlur'

// HTTP 메서드 + 경로 조합
type Method = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Route = '/users' | '/orders';
type Endpoint = `${Method} ${Route}`;
// 'GET /users' | 'GET /orders' | 'POST /users' | ... (8가지)

// CSS 단위
type CSSUnit = 'px' | 'em' | 'rem' | '%';
type CSSValue = `${number}${CSSUnit}`;
const width: CSSValue = '100px';   // ✅
const height: CSSValue = '50vh';   // ❌ 'vh'는 CSSUnit이 아님
```

### 4. Discriminated Unions (판별 유니온)

공통 **판별 필드**로 유니온 타입을 좁힌다.

```typescript
// 판별 필드: type
type Shape =
    | { type: 'circle'; radius: number }
    | { type: 'rectangle'; width: number; height: number }
    | { type: 'triangle'; base: number; height: number };

function area(shape: Shape): number {
    switch (shape.type) {
        case 'circle':
            return Math.PI * shape.radius ** 2;
        case 'rectangle':
            return shape.width * shape.height;  // 타입 자동 좁혀짐
        case 'triangle':
            return (shape.base * shape.height) / 2;
    }
}

// API 응답에 활용
type ApiResult<T> =
    | { success: true; data: T }
    | { success: false; error: string };

function handleResult(result: ApiResult<User>) {
    if (result.success) {
        console.log(result.data.name);  // data 접근 가능
    } else {
        console.error(result.error);    // error 접근 가능
    }
}
```

#### Exhaustiveness Check (완전성 검사)

```typescript
function assertNever(value: never): never {
    throw new Error(`Unexpected value: ${value}`);
}

function area(shape: Shape): number {
    switch (shape.type) {
        case 'circle': return Math.PI * shape.radius ** 2;
        case 'rectangle': return shape.width * shape.height;
        case 'triangle': return (shape.base * shape.height) / 2;
        default: return assertNever(shape);
        // Shape에 새 타입 추가 시 → 컴파일 에러 발생 (누락 방지)
    }
}
```

### 5. Type Guards (타입 가드)

런타임에서 타입을 **좁히는** 기법.

```typescript
// typeof
function process(value: string | number) {
    if (typeof value === 'string') {
        value.toUpperCase();  // string으로 좁혀짐
    } else {
        value.toFixed(2);     // number로 좁혀짐
    }
}

// instanceof
function handleError(error: unknown) {
    if (error instanceof TypeError) {
        console.log(error.message);  // TypeError로 좁혀짐
    }
}

// in 연산자
type Fish = { swim: () => void };
type Bird = { fly: () => void };

function move(animal: Fish | Bird) {
    if ('swim' in animal) {
        animal.swim();  // Fish로 좁혀짐
    }
}

// 커스텀 타입 가드 (is 키워드)
function isString(value: unknown): value is string {
    return typeof value === 'string';
}

function process(value: unknown) {
    if (isString(value)) {
        value.toUpperCase();  // string으로 좁혀짐
    }
}

// 실전: API 응답 검증
interface User {
    id: number;
    name: string;
    email: string;
}

function isUser(data: unknown): data is User {
    return (
        typeof data === 'object' &&
        data !== null &&
        'id' in data &&
        'name' in data &&
        'email' in data
    );
}
```

### 6. 내장 유틸리티 타입 심화

```typescript
// ── 변환 유틸리티 ──
type Partial<T>    // 모든 프로퍼티를 선택적으로
type Required<T>   // 모든 프로퍼티를 필수로
type Readonly<T>   // 모든 프로퍼티를 읽기 전용으로

// ── 선택 유틸리티 ──
type Pick<T, K>    // 특정 프로퍼티만 선택
type Omit<T, K>    // 특정 프로퍼티 제외
type Extract<T, U> // T에서 U에 할당 가능한 것만
type Exclude<T, U> // T에서 U에 할당 가능한 것 제외

// ── 실전 활용 ──
interface User {
    id: number;
    name: string;
    email: string;
    password: string;
    createdAt: Date;
}

// 생성 시 (id, createdAt 제외)
type CreateUserDto = Omit<User, 'id' | 'createdAt'>;

// 수정 시 (부분 수정)
type UpdateUserDto = Partial<Omit<User, 'id' | 'createdAt'>>;

// 조회 시 (password 제외)
type UserResponse = Omit<User, 'password'>;

// 검색 필터
type UserFilter = Partial<Pick<User, 'name' | 'email'>>;
```

#### 커스텀 유틸리티 타입

```typescript
// DeepPartial: 중첩 객체도 모두 선택적
type DeepPartial<T> = {
    [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};

// DeepReadonly: 중첩 객체도 모두 읽기 전용
type DeepReadonly<T> = {
    readonly [K in keyof T]: T[K] extends object ? DeepReadonly<T[K]> : T[K];
};

// RequireAtLeastOne: 최소 하나는 필수
type RequireAtLeastOne<T, Keys extends keyof T = keyof T> =
    Pick<T, Exclude<keyof T, Keys>> &
    { [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>> }[Keys];

type SearchParams = RequireAtLeastOne<{
    name?: string;
    email?: string;
    phone?: string;
}>;
// name, email, phone 중 최소 하나는 있어야 함

// Mutable: readonly 제거
type Mutable<T> = {
    -readonly [K in keyof T]: T[K];
};
```

### 7. const assertions & satisfies

```typescript
// as const: 리터럴 타입으로 고정
const config = {
    endpoint: 'https://api.example.com',
    timeout: 5000,
    retries: 3,
} as const;
// typeof config = {
//   readonly endpoint: "https://api.example.com";
//   readonly timeout: 5000;
//   readonly retries: 3;
// }

// satisfies (TS 4.9+): 타입 검증하면서 리터럴 유지
type ColorConfig = Record<string, string | number[]>;

const colors = {
    red: '#ff0000',
    green: [0, 255, 0],
} satisfies ColorConfig;

colors.red.toUpperCase();     // ✅ string 메서드 사용 가능 (리터럴 유지)
colors.green.map(v => v);     // ✅ 배열 메서드 사용 가능
```

### 8. 실전 패턴

#### 타입 안전 이벤트 시스템

```typescript
type EventMap = {
    'user:login': { userId: string; timestamp: number };
    'user:logout': { userId: string };
    'order:created': { orderId: string; amount: number };
};

class EventEmitter<T extends Record<string, any>> {
    private listeners = new Map<string, Set<Function>>();

    on<K extends keyof T>(event: K, handler: (data: T[K]) => void) {
        if (!this.listeners.has(event as string)) {
            this.listeners.set(event as string, new Set());
        }
        this.listeners.get(event as string)!.add(handler);
    }

    emit<K extends keyof T>(event: K, data: T[K]) {
        this.listeners.get(event as string)?.forEach(handler => handler(data));
    }
}

const emitter = new EventEmitter<EventMap>();

emitter.on('user:login', (data) => {
    console.log(data.userId);    // ✅ 타입 추론됨
    console.log(data.timestamp); // ✅
});

emitter.emit('order:created', { orderId: '1', amount: 100 }); // ✅
emitter.emit('order:created', { orderId: '1' });              // ❌ amount 누락
```

#### Builder 패턴 타입

```typescript
class QueryBuilder<T extends Record<string, any>, Selected extends keyof T = never> {
    select<K extends keyof T>(...keys: K[]): QueryBuilder<T, Selected | K> {
        return this as any;
    }

    where(condition: Partial<T>): this {
        return this;
    }

    execute(): Pick<T, Selected>[] {
        return [] as any;
    }
}

interface User {
    id: number;
    name: string;
    email: string;
    age: number;
}

const results = new QueryBuilder<User>()
    .select('name', 'email')
    .where({ age: 25 })
    .execute();
// 결과 타입: Pick<User, 'name' | 'email'>[]
// results[0].name  ✅
// results[0].age   ❌ (선택하지 않은 필드)
```

## 참고

- [TypeScript Handbook — Advanced Types](https://www.typescriptlang.org/docs/handbook/2/types-from-types.html)
- [TypeScript Playground](https://www.typescriptlang.org/play)
- [Generics](Generics.md) — 제네릭 기초
- [유틸리티 타입](유틸리티 타입.md) — 내장 유틸리티 타입
- [고급 타입 기법](../타입 및 타입 정의/고급 타입 기법.md) — 기본 고급 타입
