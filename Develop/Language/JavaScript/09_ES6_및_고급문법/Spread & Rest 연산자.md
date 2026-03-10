---
title: Spread & Rest 연산자
tags: [language, javascript, es6, spread, rest, destructuring]
updated: 2026-03-08
---

# Spread & Rest 연산자

## 개요

`...` 연산자는 위치에 따라 두 가지 역할을 한다.

| 이름 | 위치 | 역할 |
|------|------|------|
| **Spread (전개)** | 함수 호출, 배열/객체 리터럴 | 이터러블/객체를 펼쳐서 개별 요소로 분리 |
| **Rest (나머지)** | 함수 파라미터, 구조분해 좌변 | 나머지 요소들을 배열/객체로 수집 |

---

## Spread 연산자

### 배열 Spread

```javascript
const arr1 = [1, 2, 3];
const arr2 = [4, 5, 6];

// 배열 복사 (얕은 복사)
const copy = [...arr1];                 // [1, 2, 3]

// 배열 합치기
const merged = [...arr1, ...arr2];      // [1, 2, 3, 4, 5, 6]

// 중간에 삽입
const inserted = [...arr1, 99, ...arr2]; // [1, 2, 3, 99, 4, 5, 6]

// 함수 인수로 전개
Math.max(...arr1);                      // 3
console.log(...arr1);                   // 1 2 3
```

### 객체 Spread

```javascript
const base = { a: 1, b: 2 };
const extra = { c: 3, d: 4 };

// 객체 복사 (얕은 복사)
const copy = { ...base };              // { a: 1, b: 2 }

// 객체 병합
const merged = { ...base, ...extra };  // { a: 1, b: 2, c: 3, d: 4 }

// 속성 오버라이드 — 나중 값이 우선
const updated = { ...base, b: 99 };   // { a: 1, b: 99 }

// 기본값 + 실제값 패턴 (실무에서 자주 사용)
const defaults = { theme: 'light', lang: 'ko', pageSize: 20 };
const userConfig = { theme: 'dark', pageSize: 50 };
const config = { ...defaults, ...userConfig };
// { theme: 'dark', lang: 'ko', pageSize: 50 }
```

### 문자열 / 이터러블 Spread

```javascript
// 문자열을 문자 배열로
const chars = [..."hello"];            // ['h', 'e', 'l', 'l', 'o']

// Set → 배열 (중복 제거)
const set = new Set([1, 2, 2, 3, 3]);
const unique = [...set];               // [1, 2, 3]

// Map → 배열
const map = new Map([['a', 1], ['b', 2]]);
const entries = [...map];              // [['a', 1], ['b', 2]]
```

---

## Rest 파라미터

### 함수에서 Rest

```javascript
// 가변 인수 함수
function sum(...numbers) {
    return numbers.reduce((acc, n) => acc + n, 0);
}
sum(1, 2, 3, 4, 5);  // 15

// 첫 인수 분리 후 나머지 수집
function log(level, ...messages) {
    console.log(`[${level}]`, ...messages);
}
log('INFO', '서버 시작', '포트 3000');  // [INFO] 서버 시작 포트 3000

// arguments 객체와의 차이점
function oldStyle() {
    // arguments는 진짜 배열이 아님 → Array.from() 필요
    return Array.from(arguments).reduce((a, b) => a + b, 0);
}
function newStyle(...args) {
    // args는 진짜 배열 → 배열 메서드 바로 사용
    return args.reduce((a, b) => a + b, 0);
}
```

### 구조분해에서 Rest

```javascript
// 배열 구조분해 + Rest
const [first, second, ...rest] = [1, 2, 3, 4, 5];
// first = 1, second = 2, rest = [3, 4, 5]

// 객체 구조분해 + Rest
const { a, b, ...others } = { a: 1, b: 2, c: 3, d: 4 };
// a = 1, b = 2, others = { c: 3, d: 4 }

// 함수 파라미터 구조분해 + Rest
function process({ id, name, ...metadata }) {
    console.log(id, name);
    console.log(metadata);  // 나머지 속성 전부
}
process({ id: 1, name: 'Alice', age: 30, role: 'admin' });
```

---

## 실무 패턴

### 불변 상태 업데이트 (React/Redux 패턴)

```javascript
// 배열 아이템 추가
const addItem = (list, item) => [...list, item];

// 배열 아이템 제거
const removeItem = (list, id) => list.filter(item => item.id !== id);

// 배열 아이템 수정
const updateItem = (list, id, changes) =>
    list.map(item => item.id === id ? { ...item, ...changes } : item);

// 중첩 객체 업데이트
const state = { user: { name: 'Alice', age: 30 }, theme: 'dark' };
const newState = {
    ...state,
    user: { ...state.user, age: 31 }
};
```

### 함수 인수 전달 (Forwarding)

```javascript
// props 전달 패턴 (React)
function Button({ onClick, children, ...rest }) {
    return <button onClick={onClick} {...rest}>{children}</button>;
}

// 함수 래핑
function withLogging(fn) {
    return function(...args) {
        console.log('호출:', fn.name, args);
        const result = fn(...args);
        console.log('결과:', result);
        return result;
    };
}
const loggedAdd = withLogging((a, b) => a + b);
loggedAdd(3, 4);  // 호출: ... [3, 4] → 결과: 7
```

### API 요청/응답 처리

```javascript
// 쿼리 파라미터 병합
function buildQuery(base, overrides) {
    return { ...base, ...overrides };
}
const query = buildQuery(
    { page: 1, size: 20, sort: 'createdAt' },
    { size: 50, filter: 'active' }
);
// { page: 1, size: 50, sort: 'createdAt', filter: 'active' }

// 민감 필드 제거 후 반환
function sanitizeUser({ password, secretToken, ...safeFields }) {
    return safeFields;
}
const user = sanitizeUser({ id: 1, name: 'Alice', password: 'hashed', secretToken: 'xxx' });
// { id: 1, name: 'Alice' }

// 배열 평탄화 (flat 사용 불가 환경)
const nested = [[1, 2], [3, 4], [5, 6]];
const flat = [].concat(...nested);  // [1, 2, 3, 4, 5, 6]
```

### 배열 유틸리티 패턴

```javascript
// 중복 제거
const dedup = arr => [...new Set(arr)];
dedup([1, 2, 2, 3, 3, 3]);  // [1, 2, 3]

// 배열 앞/뒤에 값 추가
const prepend = (arr, val) => [val, ...arr];
const append = (arr, val) => [...arr, val];

// 배열 특정 인덱스에 삽입
const insertAt = (arr, index, val) => [
    ...arr.slice(0, index),
    val,
    ...arr.slice(index)
];
insertAt([1, 2, 4, 5], 2, 3);  // [1, 2, 3, 4, 5]
```

---

## TypeScript에서의 사용

```typescript
// 제네릭 타입 보존
function first<T>([head, ...tail]: T[]): [T, T[]] {
    return [head, tail];
}
const [f, rest] = first([1, 2, 3]);  // f: number, rest: number[]

// 객체 타입 병합
type Base = { id: number; name: string };
type Extra = { age: number; role: string };
type User = Base & Extra;

function createUser(base: Base, extra: Partial<Extra>): User {
    return { ...base, age: 0, role: 'user', ...extra };
}

// Readonly 배열 Spread
const nums: readonly number[] = [1, 2, 3];
const extended = [...nums, 4, 5];  // number[] (mutable 복사본)

// 함수 파라미터 타입
function format(template: string, ...values: (string | number)[]): string {
    return values.reduce<string>(
        (str, val, i) => str.replace(`{${i}}`, String(val)),
        template
    );
}
format('Hello {0}, you are {1}', 'Alice', 30);
```

---

## 주의사항

```javascript
// ❌ 얕은 복사 — 중첩 참조 공유
const original = { a: { b: 1 } };
const copy = { ...original };
copy.a.b = 999;
console.log(original.a.b);  // 999 (같은 참조!)

// ✅ 깊은 복사가 필요하면 structuredClone 사용 (최신 브라우저)
const deep = structuredClone(original);

// ❌ Rest는 마지막에만 사용 가능
// const [first, ...middle, last] = arr;  // SyntaxError

// ❌ 객체 Spread는 이터러블이 아닌 객체에만 적용
// const arr = [...{a: 1}];  // TypeError: not iterable
// ✅ Object.entries 사용
const entries = [...Object.entries({ a: 1, b: 2 })];
```

---

## Spread vs Object.assign

```javascript
const target = { a: 1 };
const source = { b: 2 };

// Object.assign — target을 직접 수정
Object.assign(target, source);  // target = { a: 1, b: 2 }

// Spread — 새 객체 반환 (불변)
const result = { ...target, ...source };  // target 그대로

// 주의: prototype 메서드는 Spread로 복사되지 않음
class Foo { bar() {} }
const foo = new Foo();
const copy = { ...foo };
copy.bar;  // undefined ← prototype 메서드 손실
```
