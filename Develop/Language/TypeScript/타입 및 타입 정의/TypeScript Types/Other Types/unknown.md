---
title: TypeScript unknown 타입 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, other-types, unknown]
updated: 2025-08-10
---

# TypeScript unknown 타입 완벽 가이드

## 배경

TypeScript에서 `unknown` 타입은 모든 타입의 슈퍼 타입으로, 타입 안전성을 유지하면서도 유연한 타입 처리를 제공합니다.

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
TypeScript의 unknown 타입은 타입 안전성을 유지하면서도 유연한 타입 처리를 제공합니다.
any보다 안전한 대안으로 사용하여 런타임 오류를 방지하세요.
타입 가드를 사용하여 unknown 값을 안전하게 처리하세요.
외부 API나 동적 데이터 처리에 unknown 타입을 활용하세요.
점진적 타입화 과정에서 unknown 타입을 활용하여 안전한 마이그레이션을 진행하세요.
unknown 타입의 특성을 이해하고 적절한 상황에서 사용하세요.

