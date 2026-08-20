---
title: TypeScript unknown 타입
tags: [language, typescript]
updated: 2025-08-10
---

# TypeScript unknown 타입
## 배경

TypeScript에서 `unknown` 타입은 모든 타입의 슈퍼 타입이다. 타입 안전성을 지키면서도 값을 유연하게 다룬다.

### unknown 타입의 필요성
- **타입 안전성**: any보다 안전한 타입 처리
- **동적 데이터**: 런타임에 타입이 결정되는 데이터 처리
- **외부 API**: 타입을 알 수 없는 외부 데이터 처리
- **점진적 타입화**: JavaScript 코드의 점진적 TypeScript 마이그레이션

### 기본 개념
- **모든 타입의 슈퍼 타입**: 어떤 값도 unknown에 할당 가능
- **타입 검사 필요**: 명시적 타입 확인이나 타입 단언 필요
- **안전한 접근**: 타입이 확인되기 전까지는 안전하지 않은 동작 금지
- **any의 안전한 대안**: any보다 타입 안전성 보장

## 핵심

### 1. unknown 타입 기본 사용법

#### unknown 타입 선언과 할당
```typescript
// unknown 타입 변수 선언
let value: unknown;

// 모든 타입의 값을 할당 가능
value = "Hello";        // string 할당
value = 42;             // number 할당
value = true;           // boolean 할당
value = { name: "홍길동" }; // object 할당
value = [1, 2, 3];      // array 할당

// 하지만 직접 접근은 불가능
// console.log(value.toUpperCase()); // 오류: unknown 타입에는 toUpperCase가 없음
```

#### unknown vs any 비교
```typescript
let anyValue: any;
let unknownValue: unknown;

anyValue = "Hello";
unknownValue = "Hello";

// any는 모든 동작 허용 (위험)
console.log(anyValue.toUpperCase()); // 정상 작동 (런타임 오류 가능)

// unknown은 타입 확인 필요 (안전)
// console.log(unknownValue.toUpperCase()); // 오류: unknown 타입에는 toUpperCase가 없음

// 타입 확인 후 사용
if (typeof unknownValue === 'string') {
    console.log(unknownValue.toUpperCase()); // 안전하게 사용 가능
}
```

`unknown` 의 성질은 두 줄로 요약된다. **무엇이든 들어오지만 아무 데도 못 나간다.**

```typescript
let u: unknown;
const n: number = u;   // error TS2322: Type 'unknown' is not assignable to type 'number'
```

`any` 와의 진짜 차이가 여기다. `any` 는 들어오는 것도 나가는 것도 다 통과시켜서, 한 번 `any` 가 섞이면 그 값이 흘러가는 경로 전체에서 검사가 꺼진다. `unknown` 은 나가는 쪽을 막으므로 오염이 번지지 않는다.

타입 연산에서도 `unknown` 은 특별하게 동작한다. 최상위 타입이라 합집합에서는 다른 타입을 흡수하고, 교집합에서는 사라진다.

```typescript
type U1 = unknown | string;   // unknown  ← string 이 흡수된다
type U2 = unknown & string;   // string   ← unknown 이 사라진다
```

그래서 `unknown` 을 유니온 멤버로 끼워 넣는 건 의미가 없다. `unknown | Foo` 는 그냥 `unknown` 이다.

### 2. unknown 타입과 타입 가드

#### typeof를 사용한 타입 가드
```typescript
function processValue(value: unknown): string {
    if (typeof value === 'string') {
        return value.toUpperCase();
    } else if (typeof value === 'number') {
        return value.toString();
    } else if (typeof value === 'boolean') {
        return value ? '참' : '거짓';
    } else if (Array.isArray(value)) {
        return value.join(', ');
    } else if (value === null) {
        return 'null';
    } else if (typeof value === 'object') {
        return JSON.stringify(value);
    } else {
        return '알 수 없는 타입';
    }
}

// 사용 예시
console.log(processValue("hello"));           // "HELLO"
console.log(processValue(42));                // "42"
console.log(processValue(true));              // "참"
console.log(processValue([1, 2, 3]));         // "1, 2, 3"
console.log(processValue({ name: "홍길동" })); // '{"name":"홍길동"}'
```

#### 커스텀 타입 가드
```typescript
// 커스텀 타입 가드 함수
function isString(value: unknown): value is string {
    return typeof value === 'string';
}

function isNumber(value: unknown): value is number {
    return typeof value === 'number';
}

function isUser(value: unknown): value is { name: string; age: number } {
    return (
        typeof value === 'object' &&
        value !== null &&
        'name' in value &&
        'age' in value &&
        typeof (value as any).name === 'string' &&
        typeof (value as any).age === 'number'
    );
}

// 사용 예시
function processUserData(data: unknown): void {
    if (isUser(data)) {
        console.log(`사용자: ${data.name}, 나이: ${data.age}`);
    } else {
        console.log('유효하지 않은 사용자 데이터');
    }
}

processUserData({ name: "홍길동", age: 30 }); // "사용자: 홍길동, 나이: 30"
processUserData({ name: "김철수" });          // "유효하지 않은 사용자 데이터"
```

타입 술어(`value is T`)는 강력한 만큼 위험하다. **컴파일러는 반환값이 `boolean` 인지만 확인하고, 함수 본문이 정말 `T` 를 검사하는지는 확인하지 않는다.**

```typescript
// 컴파일 에러가 나지 않는다
function isUser(value: unknown): value is { name: string; age: number } {
    return true;
}
```

`as` 를 함수 안에 숨긴 것과 같은 상태가 된다. `isUser` 를 통과한 값은 그 이후 전 구간에서 `{name, age}` 로 취급되므로, 술어 본문이 한 항목이라도 빠뜨리면 그 거짓말이 코드 전체로 퍼진다. 위 `isUser` 가 네 조건을 전부 나열한 건 그래서 필수다.

본문에 `(value as any).name` 이 등장하는 것도 눈여겨볼 만하다. `'name' in value` 로 좁힌 뒤에도 값의 타입이 충분히 좁혀지지 않아 `any` 로 빠져나간 것인데, **술어 안에서 `any` 를 쓰면 술어 자신을 검증할 수단이 사라진다.** 손으로 쓰는 술어를 늘리는 대신 zod·valibot 같은 스키마 검증기를 쓰면 검사 로직과 타입이 한 곳에서 같이 생성돼 이 어긋남이 구조적으로 막힌다.

`isUser` 는 통과 조건도 생각보다 넓다. 배열 역시 `typeof` 가 `'object'` 라서, `name` 과 `age` 프로퍼티를 붙인 배열도 통과한다. 여분 프로퍼티도 막지 않는다 — 술어는 "적어도 이만큼 있다"를 확인할 뿐 "정확히 이것뿐"을 확인하지 않는다.

### 3. unknown 타입과 타입 단언

#### 타입 단언 사용
```typescript
let value: unknown = "Hello World";

// 타입 단언으로 안전하게 사용
const stringValue = value as string;
console.log(stringValue.toUpperCase()); // "HELLO WORLD"

// 조건부 타입 단언
function safeStringOperation(value: unknown): string {
    if (typeof value === 'string') {
        return value.toUpperCase();
    }
    throw new Error('문자열이 아닙니다.');
}

// 사용 예시
try {
    console.log(safeStringOperation("hello")); // "HELLO"
    console.log(safeStringOperation(42));      // 오류 발생
} catch (error) {
    console.error(error.message);
}
```

**"타입 단언으로 안전하게 사용" 이라는 주석은 사실과 다르다.** `as` 는 검사가 아니라 검사를 *끄는* 지시다. 컴파일하면 `as string` 은 통째로 사라져 런타임에는 아무 코드도 남지 않는다.

```typescript
let value: unknown = 42;      // 문자열이 아니다
const s = value as string;    // 컴파일 통과 — 확인하는 코드가 생기지 않는다
s.toUpperCase();              // TypeError: s.toUpperCase is not a function
```

위 예제가 잘 도는 건 `value` 에 실제로 문자열이 들어 있어서지 `as` 가 뭘 해줘서가 아니다. `as` 가 하는 일은 **컴파일러에게 "따지지 마라"고 말하는 것**뿐이다. 같은 블록의 `safeStringOperation` 은 `typeof` 로 실제로 확인하니 이름값을 한다. 둘의 차이가 이 문서에서 제일 중요한 지점이다.

`as` 가 위험을 경고해 주리라 기대해서도 안 된다. TypeScript 는 두 타입이 "전혀 겹치지 않을 때"만 막는데, 그 기준이 생각보다 헐겁다.

```typescript
interface User { id: number; name: string; email?: string }

const k = 'age' as keyof User;   // 통과한다. 'age' 는 User 의 키가 아닌데도.
const n = 'age' as number;       // error TS2352: neither type sufficiently overlaps
```

두 문자열 리터럴은 모두 `string` 으로 넓혀지면 겹친다고 판정돼 첫 줄이 통과한다. **`as` 로 키 이름을 넘기는 코드는 오타를 잡아주지 못한다.** 그리고 `as unknown as T` 로 두 번 단언하면 남은 이 최소한의 검사마저 없어진다. 그 패턴이 보이면 대개 타입 설계가 틀렸다는 신호다.

## 예시

### 1. 실제 사용 사례

#### JSON 파싱과 unknown
```typescript
// JSON 파싱 결과는 unknown 타입
function parseJSON(jsonString: string): unknown {
    try {
        return JSON.parse(jsonString);
    } catch (error) {
        throw new Error('유효하지 않은 JSON 형식입니다.');
    }
}

// 안전한 JSON 처리
function processJSONData(jsonString: string): void {
    const data = parseJSON(jsonString);
    
    if (typeof data === 'object' && data !== null) {
        if ('users' in data && Array.isArray((data as any).users)) {
            console.log('사용자 수:', (data as any).users.length);
        }
        
        if ('settings' in data && typeof (data as any).settings === 'object') {
            console.log('설정:', (data as any).settings);
        }
    } else {
        console.log('객체가 아닌 데이터:', data);
    }
}

// 사용 예시
const validJSON = '{"users": ["홍길동", "김철수"], "settings": {"theme": "dark"}}';
const invalidJSON = '{"users": "not an array"}';

processJSONData(validJSON);   // "사용자 수: 2", "설정: { theme: 'dark' }"
processJSONData(invalidJSON); // "객체가 아닌 데이터: { users: 'not an array' }"
```

여기에 확인된 오류가 둘 있다.

**첫째, 주석 "JSON 파싱 결과는 unknown 타입" 이 틀렸다.** `JSON.parse` 의 반환 타입은 `any` 다. 이 문서가 강조해 온 안전장치가 바로 그 자리에서 꺼져 있다.

```typescript
const p = JSON.parse('{}');
const n: number = p;   // 에러 없이 통과한다 — any 이기 때문

let u: unknown;
const m: number = u;   // error TS2322: Type 'unknown' is not assignable to type 'number'
```

그래서 `parseJSON` 이 반환 타입을 `unknown` 으로 **명시한 것**이 이 함수의 핵심 가치다. 자동으로 그렇게 되는 게 아니라 손으로 좁힌 것이다. `JSON.parse` 를 직접 부르는 코드는 전부 `any` 를 그대로 받아 안전성을 잃는다. 감싸서 쓰는 습관이 필요한 이유다.

**둘째, 마지막 줄 주석의 출력이 실제와 다르다.** `'{"users": "not an array"}'` 는 명백히 객체이므로 `typeof data === 'object' && data !== null` 을 통과한다. `else` 로 가지 않는다. 안에서 `'users' in data` 는 참이지만 `Array.isArray` 가 거짓, `settings` 는 아예 없으니 — **아무것도 출력되지 않는다.**

```
processJSONData(invalidJSON)  →  (출력 없음)
```

주석에 적힌 `"객체가 아닌 데이터: ..."` 는 나올 수 없는 문자열이다. 이건 단순 오타가 아니라 이 함수의 설계 문제를 드러낸다. **형태가 어긋난 입력이 조용히 통과한다.** 검증 함수가 "틀렸다"고 말하지 않고 침묵하면 호출한 쪽은 성공했다고 착각한다. `else` 절을 붙여 어긋난 경우를 명시적으로 보고해야 한다.

`typeof data === 'object'` 자체도 `null` 을 잡아내지 못해 `data !== null` 을 늘 함께 써야 하는데, 이 예제는 그건 제대로 하고 있다.

#### 외부 API 응답 처리
```typescript
// 외부 API 응답 타입 정의
interface ApiResponse<T> {
    success: boolean;
    data: T;
    message: string;
}

// API 호출 함수
async function fetchUserData(userId: number): Promise<unknown> {
    try {
        const response = await fetch(`/api/users/${userId}`);
        return await response.json();
    } catch (error) {
        throw new Error('API 호출 실패');
    }
}

// 안전한 API 응답 처리
async function processUserData(userId: number): Promise<void> {
    try {
        const response = await fetchUserData(userId);
        
        // 응답 구조 검증
        if (
            typeof response === 'object' &&
            response !== null &&
            'success' in response &&
            'data' in response &&
            'message' in response
        ) {
            const apiResponse = response as ApiResponse<any>;
            
            if (apiResponse.success) {
                const userData = apiResponse.data;
                
                if (
                    typeof userData === 'object' &&
                    userData !== null &&
                    'id' in userData &&
                    'name' in userData
                ) {
                    console.log(`사용자: ${userData.name} (ID: ${userData.id})`);
                } else {
                    console.log('유효하지 않은 사용자 데이터');
                }
            } else {
                console.error('API 오류:', apiResponse.message);
            }
        } else {
            console.error('유효하지 않은 API 응답 형식');
        }
    } catch (error) {
        console.error('데이터 처리 오류:', error);
    }
}
```

### 2. 고급 패턴

#### 제네릭과 unknown
```typescript
// 제네릭 함수에서 unknown 사용
function safeParse<T>(value: unknown, validator: (value: unknown) => value is T): T {
    if (validator(value)) {
        return value;
    }
    throw new Error('유효하지 않은 데이터 형식입니다.');
}

// 타입 검증 함수들
function isStringArray(value: unknown): value is string[] {
    return Array.isArray(value) && value.every(item => typeof item === 'string');
}

function isNumberArray(value: unknown): value is number[] {
    return Array.isArray(value) && value.every(item => typeof item === 'number');
}

// 사용 예시
try {
    const stringData = safeParse(['a', 'b', 'c'], isStringArray);
    console.log('문자열 배열:', stringData); // ["a", "b", "c"]
    
    const numberData = safeParse([1, 2, 3], isNumberArray);
    console.log('숫자 배열:', numberData); // [1, 2, 3]
    
    // 잘못된 데이터
    const invalidData = safeParse(['a', 2, 'c'], isStringArray); // 오류 발생
} catch (error) {
    console.error('파싱 오류:', error.message);
}
```

#### 조건부 타입과 unknown
```typescript
// unknown을 사용한 조건부 타입
type SafeProperty<T, K extends keyof T> = T[K] extends unknown ? T[K] : never;

// 안전한 프로퍼티 접근 함수
function safeGetProperty<T, K extends keyof T>(
    obj: T,
    key: K
): SafeProperty<T, K> | undefined {
    if (obj && typeof obj === 'object' && key in obj) {
        return obj[key] as SafeProperty<T, K>;
    }
    return undefined;
}

// 사용 예시
interface User {
    id: number;
    name: string;
    email?: string;
}

const user: User = {
    id: 1,
    name: '홍길동'
};

console.log(safeGetProperty(user, 'name')); // '홍길동'
console.log(safeGetProperty(user, 'email')); // undefined
console.log(safeGetProperty(user, 'age' as keyof User)); // undefined
```

**`SafeProperty<T, K>` 는 아무 일도 하지 않는다.** 모든 타입이 `unknown` 을 확장하므로 `T[K] extends unknown` 은 언제나 참이고, 조건부 타입은 항상 참 가지를 택한다. 즉 이 타입은 `T[K]` 와 완전히 같다.

```typescript
type SafeProperty<T, K extends keyof T> = T[K] extends unknown ? T[K] : never;
type A = SafeProperty<User, 'name'>;

const a1: A = 'x';   // 통과
const a2: A = 123;   // error TS2322: Type 'number' is not assignable to type 'string'
```

에러 메시지가 `'string'` 을 기대한다고 말하는 게 증거다. `A` 는 그냥 `string` 이다. 거짓 가지 `never` 는 도달할 수 없다. `unknown` 을 조건부 타입의 제약으로 쓰면 항상 이렇게 되니, 실제로 무언가 걸러내려면 `T[K] extends string` 처럼 **구체적인 타입**을 조건에 둬야 한다.

마지막 줄의 `'age' as keyof User` 도 앞서 본 `as` 의 한계를 그대로 보여준다. `age` 는 `User` 에 없는 키인데 컴파일러가 막지 않는다. 런타임에서는 `key in obj` 가 거짓이라 `undefined` 가 나오지만, **타입 시스템 쪽에서는 존재하지 않는 키가 유효한 키인 척 통과했다.** 주석의 `undefined` 는 맞는 출력이되 맞는 이유로 나온 게 아니다.

## 운영 팁

### 성능 최적화

#### unknown 타입 최적화
```typescript
// 타입 가드 캐싱
function createTypeGuard<T>(predicate: (value: unknown) => value is T) {
    return predicate;
}

// 자주 사용되는 타입 가드들
const isString = createTypeGuard((value: unknown): value is string => 
    typeof value === 'string'
);

const isNumber = createTypeGuard((value: unknown): value is number => 
    typeof value === 'number'
);

const isArray = createTypeGuard((value: unknown): value is any[] => 
    Array.isArray(value)
);

// 사용 예시
function processOptimized(value: unknown): string {
    if (isString(value)) {
        return value.toUpperCase();
    } else if (isNumber(value)) {
        return value.toString();
    } else if (isArray(value)) {
        return value.join(', ');
    }
    return '알 수 없는 타입';
}
```

### 에러 처리

#### 안전한 unknown 타입 처리
```typescript
// 안전한 unknown 타입 처리 함수
function safeUnknownOperation<T>(
    value: unknown,
    operation: (value: T) => string,
    validator: (value: unknown) => value is T,
    fallback: string = '처리할 수 없는 타입'
): string {
    try {
        if (validator(value)) {
            return operation(value);
        }
        return fallback;
    } catch (error) {
        return `오류 발생: ${error instanceof Error ? error.message : '알 수 없는 오류'}`;
    }
}

// 사용 예시
const stringOperation = (value: string) => value.toUpperCase();
const numberOperation = (value: number) => value.toFixed(2);

console.log(safeUnknownOperation("hello", stringOperation, isString)); // "HELLO"
console.log(safeUnknownOperation(3.14159, numberOperation, isNumber)); // "3.14"
console.log(safeUnknownOperation(true, stringOperation, isString)); // "처리할 수 없는 타입"
```

## 참고

### unknown 타입 특성

| 특성 | 설명 |
|------|------|
| **할당 가능성** | 모든 타입의 값을 할당 가능 |
| **접근 제한** | 타입 확인 전까지 접근 불가 |
| **타입 안전성** | 높음 (any보다 안전) |
| **사용 목적** | 동적 데이터, 외부 API, 점진적 타입화 |

### unknown vs any vs object 비교표

| 타입 | 할당 가능성 | 접근 제한 | 타입 안전성 | 사용 목적 |
|------|-------------|-----------|-------------|-----------|
| **unknown** | 모든 타입 | 있음 | 높음 | 동적 데이터, 외부 API |
| **any** | 모든 타입 | 없음 | 없음 | 레거시 코드, 타입 검사 우회 |
| **object** | 객체만 | 있음 | 중간 | 일반적인 객체 처리 |

### 결론
TypeScript의 unknown 타입은 타입 안전성을 유지하면서도 타입을 유연하게 처리한다.
any보다 안전한 대안으로 쓰면 런타임 오류를 막는다.
unknown 값은 타입 가드를 거쳐 안전하게 처리한다.
외부 API나 동적 데이터를 다룰 때 unknown 타입을 쓴다.
점진적 타입화 과정에서도 unknown 타입을 끼우면 마이그레이션이 안전해진다.
unknown 타입의 특성을 이해하고 맞는 상황에 쓴다.

