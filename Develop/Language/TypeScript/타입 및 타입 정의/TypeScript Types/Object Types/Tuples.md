---
title: TypeScript Tuples 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, tuples]
updated: 2025-12-16
---

# TypeScript Tuples 가이드

## 배경

TypeScript에서 튜플(Tuple)은 길이와 타입이 고정된 배열입니다.

### Tuples의 필요성
- **타입 안전성**: 각 위치의 타입이 사전에 정해져 있어 엄격한 타입 검사
- **구조적 데이터**: 순서가 중요한 데이터 구조 표현
- **함수 반환값**: 여러 값을 반환하는 함수의 타입 정의
- **메모리 효율성**: 객체 대신 사용하여 메모리 절약

### 기본 개념
- **고정 길이**: 배열의 길이가 미리 정해짐
- **타입 고정**: 각 인덱스의 타입이 사전에 정의됨
- **순서 중요**: 요소의 순서가 타입의 일부
- **구조 분해**: 배열 구조 분해 할당 지원

## 핵심

### 1. 기본 튜플 선언과 사용

#### 튜플 선언
```typescript
// 기본 튜플 선언
let userInfo: [string, number];
userInfo = ["홍길동", 30];  // 올바른 사용
// userInfo = [30, "홍길동"]; // 오류: 순서가 다름

// 선언과 초기화 함께
let person: [string, number] = ["김철수", 28];

// 다양한 타입 조합
let mixedTuple: [string, number, boolean] = ["홍길동", 35, true];
let coordinates: [number, number] = [10, 20];
```

#### 튜플 값 접근
```typescript
let user: [string, number, string] = ["홍길동", 30, "서울"];

// 인덱스로 접근
console.log(user[0]); // "홍길동"
console.log(user[1]); // 30
console.log(user[2]); // "서울"

// 구조 분해 할당
let [name, age, city] = user;
console.log(name); // "홍길동"
console.log(age);  // 30
console.log(city); // "서울"

// 일부만 분해
let [firstName, ...rest] = user;
console.log(firstName); // "홍길동"
console.log(rest);      // [30, "서울"]
```

### 2. 튜플과 함수

#### 튜플을 반환하는 함수
```typescript
// 여러 값을 반환하는 함수
function getUserInfo(): [string, number, string] {
    return ["홍길동", 30, "서울"];
}

// 사용 예시
let [userName, userAge, userCity] = getUserInfo();
console.log(`${userName}은 ${userAge}세이고 ${userCity}에 살고 있습니다.`);

// 튜플을 매개변수로 받는 함수
function processUserInfo(user: [string, number, string]): string {
    const [name, age, city] = user;
    return `${name} (${age}세, ${city})`;
}

console.log(processUserInfo(["김철수", 25, "부산"])); // "김철수 (25세, 부산)"
```

#### 튜플과 제네릭
```typescript
// 제네릭 튜플 타입
type Pair<T, U> = [T, U];
type Triple<T, U, V> = [T, U, V];

// 사용 예시
let stringNumberPair: Pair<string, number> = ["hello", 42];
let mixedTriple: Triple<string, number, boolean> = ["test", 123, true];

// 제네릭 함수에서 튜플 사용
function swap<T, U>(pair: [T, U]): [U, T] {
    return [pair[1], pair[0]];
}

let swapped = swap(["hello", 42]);
console.log(swapped); // [42, "hello"]
```

### 3. 고급 튜플 패턴

#### 선택적 요소와 나머지 요소
```typescript
// 선택적 요소가 있는 튜플
type OptionalTuple = [string, number?];
let optional: OptionalTuple = ["홍길동"];        // 두 번째 요소 생략 가능
let optional2: OptionalTuple = ["홍길동", 30];   // 두 번째 요소 포함

// 나머지 요소가 있는 튜플
type RestTuple = [string, number, ...string[]];
let rest: RestTuple = ["홍길동", 30, "서울", "한국"];
let rest2: RestTuple = ["김철수", 25]; // 나머지 요소 생략 가능
```

#### 읽기 전용 튜플
```typescript
// 읽기 전용 튜플
type ReadonlyTuple = readonly [string, number];
let readonlyUser: ReadonlyTuple = ["홍길동", 30];

// readonlyUser[0] = "김철수"; // 오류: 읽기 전용

// 함수에서 읽기 전용 튜플 반환
function createUser(): readonly [string, number] {
    return ["홍길동", 30] as const;
}

const user = createUser();
// user[0] = "김철수"; // 오류: 읽기 전용
```

## 예시

### 1. 실제 사용 사례

#### API 응답 처리
```typescript
// API 응답을 튜플로 표현
type ApiResponse<T> = [boolean, T | null, string];

async function fetchUser(id: number): Promise<ApiResponse<User>> {
    try {
        const response = await fetch(`/api/users/${id}`);
        const data = await response.json();
        
        if (response.ok) {
            return [true, data, "성공"];
        } else {
            return [false, null, "사용자를 찾을 수 없습니다."];
        }
    } catch (error) {
        return [false, null, "네트워크 오류가 발생했습니다."];
    }
}

interface User {
    id: number;
    name: string;
    email: string;
}

// 사용 예시
async function handleUserFetch() {
    const [success, user, message] = await fetchUser(1);
    
    if (success && user) {
        console.log(`사용자: ${user.name}`);
    } else {
        console.error(`오류: ${message}`);
    }
}
```

#### 좌표 시스템
```typescript
// 2D 좌표
type Point2D = [number, number];
type Point3D = [number, number, number];

class GeometryCalculator {
    static distance(p1: Point2D, p2: Point2D): number {
        const [x1, y1] = p1;
        const [x2, y2] = p2;
        return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }

    static midpoint(p1: Point2D, p2: Point2D): Point2D {
        const [x1, y1] = p1;
        const [x2, y2] = p2;
        return [(x1 + x2) / 2, (y1 + y2) / 2];
    }

    static translate(point: Point2D, dx: number, dy: number): Point2D {
        const [x, y] = point;
        return [x + dx, y + dy];
    }
}

// 사용 예시
const point1: Point2D = [0, 0];
const point2: Point2D = [3, 4];

console.log(GeometryCalculator.distance(point1, point2)); // 5
console.log(GeometryCalculator.midpoint(point1, point2)); // [1.5, 2]
console.log(GeometryCalculator.translate(point1, 2, 3));  // [2, 3]
```

### 2. 고급 패턴

#### 튜플과 맵핑 타입
```typescript
// 튜플의 각 요소를 변환하는 유틸리티 타입
type MapTuple<T extends any[], F> = {
    [K in keyof T]: F extends (arg: T[K]) => infer R ? R : never;
};

// 사용 예시
type StringTuple = [string, string, string];
type NumberTuple = MapTuple<StringTuple, (arg: string) => number>;

// 실제 사용
function convertToNumbers(tuple: StringTuple): NumberTuple {
    return tuple.map(str => parseInt(str, 10)) as NumberTuple;
}

const result = convertToNumbers(["1", "2", "3"]);
console.log(result); // [1, 2, 3]
```

#### 조건부 튜플 타입
```typescript
// 조건에 따라 튜플 타입 결정
type ConditionalTuple<T extends boolean> = T extends true 
    ? [string, number] 
    : [number, string];

// 사용 예시
type Tuple1 = ConditionalTuple<true>;   // [string, number]
type Tuple2 = ConditionalTuple<false>;  // [number, string]

function createTuple<T extends boolean>(flag: T): ConditionalTuple<T> {
    if (flag) {
        return ["hello", 42] as ConditionalTuple<T>;
    } else {
        return [42, "hello"] as ConditionalTuple<T>;
    }
}

const tuple1 = createTuple(true);   // [string, number]
const tuple2 = createTuple(false);  // [number, string]
```

## 운영 팁

### 성능 최적화

#### 튜플 vs 객체 선택
```typescript
// 튜플 사용 (메모리 효율적)
type UserTuple = [string, number, string];
const userTuple: UserTuple = ["홍길동", 30, "서울"];

// 객체 사용 (가독성 좋음)
interface User {
    name: string;
    age: number;
    city: string;
}
const user: User = { name: "홍길동", age: 30, city: "서울" };

// 성능 비교
function processTuple(user: UserTuple): void {
    const [name, age, city] = user;
    // 처리 로직
}

function processObject(user: User): void {
    const { name, age, city } = user;
    // 처리 로직
}
```

### 에러 처리

#### 안전한 튜플 접근
```typescript
function safeTupleAccess<T extends any[]>(
    tuple: T, 
    index: number
): T[number] | undefined {
    if (index >= 0 && index < tuple.length) {
        return tuple[index];
    }
    return undefined;
}

// 사용 예시
const tuple: [string, number] = ["홍길동", 30];
console.log(safeTupleAccess(tuple, 0)); // "홍길동"
console.log(safeTupleAccess(tuple, 2)); // undefined
```

## 참고

### 튜플 vs 배열 비교표

| 특징 | 튜플(Tuple) | 배열(Array) |
|------|-------------|-------------|
| **길이** | 고정됨 | 가변적 |
| **타입** | 각 요소 타입이 다를 수 있음 | 동일한 타입 |
| **순서** | 순서가 타입의 일부 | 순서 상관 없음 |
| **타입 안전성** | 높음 | 상대적으로 낮음 |
| **사용 목적** | 구조적 데이터 | 동적 데이터 |

### 튜플 사용 권장사항

1. **명확한 구조**: 순서가 중요한 데이터 구조
2. **함수 반환값**: 여러 값을 반환하는 함수
3. **타입 안전성**: 엄격한 타입 검사가 필요한 경우
4. **성능**: 메모리 효율성이 중요한 경우

### 결론
TypeScript의 튜플은 고정된 길이와 타입을 가진 강력한 데이터 구조입니다.
함수의 여러 반환값을 안전하게 처리할 수 있습니다.
구조 분해 할당을 통해 깔끔한 코드를 작성할 수 있습니다.
적절한 상황에서 튜플을 사용하여 타입 안전성과 성능을 향상시키세요.
튜플과 배열의 차이를 이해하고 상황에 맞게 선택하세요.
고급 패턴을 활용하여 더욱 유연한 튜플 사용법을 익히세요.
