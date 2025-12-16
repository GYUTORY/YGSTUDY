---
title: TypeScript 제네릭 (Generics) 가이드
tags: [language, typescript, generics, type-utility, constraints]
updated: 2025-12-16
---

# TypeScript 제네릭 (Generics) 가이드

## 배경

### 제네릭이란?
제네릭(Generic)은 타입을 매개변수로 받을 수 있는 함수, 클래스, 인터페이스를 정의할 수 있게 해주는 TypeScript의 핵심 기능입니다. 이를 통해 다양한 타입에 대해 동일한 로직을 적용할 수 있습니다.

### 제네릭의 필요성
- **타입 안전성**: 컴파일 타임에 타입 검사로 런타임 오류 방지
- **코드 재사용성**: 다양한 타입을 처리할 수 있는 범용 컴포넌트 작성
- **가독성**: 명확한 타입 정보로 코드 이해도 향상
- **유지보수성**: 타입 변경 시 자동으로 관련 코드 업데이트

### 기본 개념
- **타입 매개변수**: 제네릭에서 사용하는 타입 변수 (보통 T, U, V 등)
- **타입 추론**: TypeScript가 자동으로 타입을 추론하는 기능
- **제약 조건**: 타입 매개변수에 대한 제한 사항
- **제네릭 인스턴스화**: 특정 타입으로 제네릭을 구체화하는 과정

## 핵심

### 1. 제네릭 함수

#### 기본 제네릭 함수
```typescript
function identity<T>(value: T): T {
    return value;
}

// 타입 매개변수 명시
const num = identity<number>(42);
const str = identity<string>('Hello');

// 타입 추론 활용
const inferredNum = identity(42); // T는 number로 추론
const inferredStr = identity('Hello'); // T는 string으로 추론

console.log(num); // 42
console.log(str); // Hello
```

#### 배열을 다루는 제네릭 함수
```typescript
function getArray<T>(items: T[]): T[] {
    return items;
}

function getFirstItem<T>(items: T[]): T | undefined {
    return items[0];
}

const numArray = getArray<number>([1, 2, 3]);
const strArray = getArray<string>(['a', 'b', 'c']);

const firstNum = getFirstItem([1, 2, 3]); // number | undefined
const firstStr = getFirstItem(['a', 'b', 'c']); // string | undefined
```

### 2. 제네릭 인터페이스

#### 기본 제네릭 인터페이스
```typescript
interface Pair<K, V> {
    key: K;
    value: V;
}

interface Container<T> {
    items: T[];
    add(item: T): void;
    remove(item: T): void;
    get(index: number): T | undefined;
}

// 사용 예시
const numPair: Pair<number, string> = { key: 1, value: 'one' };
const strPair: Pair<string, boolean> = { key: 'isActive', value: true };

class ArrayContainer<T> implements Container<T> {
    constructor(public items: T[] = []) {}

    add(item: T): void {
        this.items.push(item);
    }

    remove(item: T): void {
        this.items = this.items.filter(i => i !== item);
    }

    get(index: number): T | undefined {
        return this.items[index];
    }
}
```

#### API 응답 인터페이스
```typescript
interface ApiResponse<T> {
    data: T;
    success: boolean;
    message?: string;
    timestamp: Date;
}

interface User {
    id: number;
    name: string;
    email: string;
}

interface Product {
    id: string;
    name: string;
    price: number;
}

// 사용 예시
const userResponse: ApiResponse<User> = {
    data: { id: 1, name: '홍길동', email: 'hong@example.com' },
    success: true,
    message: '사용자 조회 성공',
    timestamp: new Date()
};

const productResponse: ApiResponse<Product> = {
    data: { id: 'prod-001', name: '노트북', price: 1000000 },
    success: true,
    timestamp: new Date()
};
```

### 3. 제네릭 클래스

#### 데이터 저장소 클래스
```typescript
class DataStorage<T> {
    private items: T[] = [];

    addItem(item: T): void {
        this.items.push(item);
    }

    removeItem(item: T): void {
        const index = this.items.indexOf(item);
        if (index > -1) {
            this.items.splice(index, 1);
        }
    }

    getItems(): T[] {
        return [...this.items];
    }

    getItem(index: number): T | undefined {
        return this.items[index];
    }

    clear(): void {
        this.items = [];
    }

    size(): number {
        return this.items.length;
    }
}

// 사용 예시
const numberStorage = new DataStorage<number>();
numberStorage.addItem(1);
numberStorage.addItem(2);
numberStorage.addItem(3);

const stringStorage = new DataStorage<string>();
stringStorage.addItem('apple');
stringStorage.addItem('banana');
stringStorage.addItem('orange');

console.log(numberStorage.getItems()); // [1, 2, 3]
console.log(stringStorage.getItems()); // ['apple', 'banana', 'orange']
```

#### 제네릭 스택 클래스
```typescript
class Stack<T> {
    private items: T[] = [];

    push(item: T): void {
        this.items.push(item);
    }

    pop(): T | undefined {
        return this.items.pop();
    }

    peek(): T | undefined {
        return this.items[this.items.length - 1];
    }

    isEmpty(): boolean {
        return this.items.length === 0;
    }

    size(): number {
        return this.items.length;
    }

    clear(): void {
        this.items = [];
    }
}

// 사용 예시
const numberStack = new Stack<number>();
numberStack.push(1);
numberStack.push(2);
numberStack.push(3);

console.log(numberStack.pop()); // 3
console.log(numberStack.peek()); // 2
console.log(numberStack.size()); // 2
```

### 4. 제약 조건 (Constraints)

#### 기본 제약 조건
```typescript
// length 속성을 가진 타입만 허용
function getLength<T extends { length: number }>(item: T): number {
    return item.length;
}

console.log(getLength('Hello')); // 5
console.log(getLength([1, 2, 3, 4, 5])); // 5
console.log(getLength({ length: 10, value: 'test' })); // 10
// console.log(getLength(42)); // 오류: number는 length 속성이 없음
```

#### 키 제약 조건
```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
    return obj[key];
}

const user = { name: '홍길동', age: 25, email: 'hong@example.com' };

console.log(getProperty(user, 'name')); // '홍길동'
console.log(getProperty(user, 'age')); // 25
// console.log(getProperty(user, 'address')); // 오류: 'address'는 user의 키가 아님
```

#### 생성자 제약 조건
```typescript
function createInstance<T extends { new(): any }>(constructor: T): InstanceType<T> {
    return new constructor();
}

class User {
    name: string;
    
    constructor() {
        this.name = '기본 사용자';
    }
}

const userInstance = createInstance(User);
console.log(userInstance.name); // '기본 사용자'
```

### 5. 다중 타입 매개변수

#### 객체 병합 함수
```typescript
function merge<T, U>(obj1: T, obj2: U): T & U {
    return { ...obj1, ...obj2 };
}

const mergedObj = merge({ name: 'Alice' }, { age: 25 });
console.log(mergedObj); // { name: 'Alice', age: 25 }

// 더 구체적인 타입 지정
function mergeWithDefaults<T extends object, U extends object>(
    obj1: T, 
    obj2: U
): T & U {
    return { ...obj1, ...obj2 };
}
```

#### 키-값 쌍 처리
```typescript
function processKeyValue<T, U>(key: T, value: U): { key: T; value: U } {
    return { key, value };
}

const result = processKeyValue('userId', 123);
console.log(result); // { key: 'userId', value: 123 }

// 맵 생성 함수
function createMap<T, U>(keys: T[], values: U[]): Map<T, U> {
    const map = new Map<T, U>();
    keys.forEach((key, index) => {
        map.set(key, values[index]);
    });
    return map;
}
```

## 예시

### 1. 실제 사용 사례

#### API 클라이언트
```typescript
interface ApiResponse<T> {
    data: T;
    success: boolean;
    message?: string;
    status: number;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    async get<T>(endpoint: string): Promise<ApiResponse<T>> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            const data = await response.json();
            
            return {
                data,
                success: response.ok,
                status: response.status
            };
        } catch (error) {
            return {
                data: {} as T,
                success: false,
                message: error instanceof Error ? error.message : 'Unknown error',
                status: 500
            };
        }
    }

    async post<T, U>(endpoint: string, body: U): Promise<ApiResponse<T>> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await response.json();
            
            return {
                data,
                success: response.ok,
                status: response.status
            };
        } catch (error) {
            return {
                data: {} as T,
                success: false,
                message: error instanceof Error ? error.message : 'Unknown error',
                status: 500
            };
        }
    }
}

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
}

interface CreateUserRequest {
    name: string;
    email: string;
}

const apiClient = new ApiClient('https://api.example.com');

// 사용자 조회
const userResponse = await apiClient.get<User>('/users/1');

// 사용자 생성
const createUserResponse = await apiClient.post<User, CreateUserRequest>(
    '/users',
    { name: '홍길동', email: 'hong@example.com' }
);
```

#### 상태 관리
```typescript
interface State<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
}

class StateManager<T> {
    private state: State<T> = {
        data: null,
        loading: false,
        error: null
    };

    private listeners: ((state: State<T>) => void)[] = [];

    setState(newState: Partial<State<T>>): void {
        this.state = { ...this.state, ...newState };
        this.notifyListeners();
    }

    getState(): State<T> {
        return { ...this.state };
    }

    subscribe(listener: (state: State<T>) => void): () => void {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.state));
    }

    async fetchData(fetcher: () => Promise<T>): Promise<void> {
        this.setState({ loading: true, error: null });
        try {
            const data = await fetcher();
            this.setState({ data, loading: false });
        } catch (error) {
            this.setState({ 
                error: error instanceof Error ? error.message : 'Unknown error',
                loading: false 
            });
        }
    }
}

// 사용 예시
interface User {
    id: number;
    name: string;
}

const userStateManager = new StateManager<User>();

userStateManager.subscribe((state) => {
    console.log('상태 변경:', state);
});

await userStateManager.fetchData(async () => {
    const response = await fetch('/api/users/1');
    return response.json();
});
```

### 2. 고급 활용 패턴

#### 조건부 타입과 제네릭
```typescript
type ConditionalType<T> = T extends string 
    ? { type: 'string'; value: T }
    : T extends number
    ? { type: 'number'; value: T }
    : { type: 'unknown'; value: T };

function processValue<T>(value: T): ConditionalType<T> {
    if (typeof value === 'string') {
        return { type: 'string', value } as ConditionalType<T>;
    } else if (typeof value === 'number') {
        return { type: 'number', value } as ConditionalType<T>;
    } else {
        return { type: 'unknown', value } as ConditionalType<T>;
    }
}

const stringResult = processValue('hello'); // { type: 'string', value: 'hello' }
const numberResult = processValue(42); // { type: 'number', value: 42 }
const booleanResult = processValue(true); // { type: 'unknown', value: true }
```

#### 재귀적 제네릭 타입
```typescript
type DeepPartial<T> = {
    [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

interface User {
    id: number;
    profile: {
        name: string;
        age: number;
        address: {
            city: string;
            country: string;
        };
    };
}

type PartialUser = DeepPartial<User>;
// {
//   id?: number;
//   profile?: {
//     name?: string;
//     age?: number;
//     address?: {
//       city?: string;
//       country?: string;
//     };
//   };
// }
```

#### 제네릭 유틸리티 함수
```typescript
function createFactory<T>(defaultValue: T) {
    return {
        create: (value?: T): T => value ?? defaultValue,
        createArray: (count: number, value?: T): T[] => 
            Array.from({ length: count }, () => value ?? defaultValue),
        createMap: <K extends string>(keys: K[], value?: T): Record<K, T> => {
            const result = {} as Record<K, T>;
            keys.forEach(key => {
                result[key] = value ?? defaultValue;
            });
            return result;
        }
    };
}

// 사용 예시
const numberFactory = createFactory(0);
const stringFactory = createFactory('');

console.log(numberFactory.create()); // 0
console.log(numberFactory.create(42)); // 42
console.log(numberFactory.createArray(3)); // [0, 0, 0]
console.log(numberFactory.createArray(3, 10)); // [10, 10, 10]

console.log(stringFactory.createMap(['a', 'b', 'c'])); // { a: '', b: '', c: '' }
console.log(stringFactory.createMap(['x', 'y'], 'default')); // { x: 'default', y: 'default' }
```

## 운영 팁

### 1. 성능 최적화

#### 타입 캐싱
```typescript
// 복잡한 제네릭 타입을 미리 정의
type ComplexGeneric<T, U> = T extends U ? { type: 'match'; value: T } : { type: 'no-match'; value: T };

// 자주 사용되는 제네릭 조합을 타입 별칭으로 정의
type ApiResult<T> = Promise<{ data: T; success: boolean }>;
type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
```

#### 제네릭 함수 최적화
```typescript
// 제네릭 함수를 오버로드하여 성능 향상
function processData<T extends string>(data: T): string;
function processData<T extends number>(data: T): number;
function processData<T>(data: T): T {
    return data;
}
```

### 2. 에러 처리

#### 제네릭 에러 타입
```typescript
interface ApiError {
    code: string;
    message: string;
    details?: Record<string, any>;
}

type ApiResult<T> = 
    | { success: true; data: T }
    | { success: false; error: ApiError };

async function safeApiCall<T>(apiCall: () => Promise<T>): Promise<ApiResult<T>> {
    try {
        const data = await apiCall();
        return { success: true, data };
    } catch (error) {
        return {
            success: false,
            error: {
                code: 'API_ERROR',
                message: error instanceof Error ? error.message : 'Unknown error'
            }
        };
    }
}
```

### 3. 디버깅 및 테스트

#### 제네릭 타입 디버깅
```typescript
// 타입 정보를 런타임에 확인하는 유틸리티
function getTypeInfo<T>(value: T): { type: string; value: T } {
    return {
        type: typeof value,
        value
    };
}

// 제네릭 함수 테스트
function testGenericFunction<T>(fn: (value: T) => T, testValue: T): boolean {
    const result = fn(testValue);
    return result === testValue;
}
```

## 참고

### 제네릭 사용 시 주의사항

1. **타입 추론 활용**: 가능한 한 타입 매개변수를 명시적으로 지정하지 말고 타입 추론을 활용하세요
2. **제약 조건 적절히 사용**: 필요한 경우에만 제약 조건을 사용하여 유연성을 유지하세요
3. **복잡한 제네릭 타입 분해**: 너무 복잡한 제네릭 타입은 여러 단계로 나누어 정의하세요
4. **문서화**: 복잡한 제네릭 함수나 클래스는 JSDoc으로 문서화하세요

### 제네릭 vs 오버로딩

```typescript
// 제네릭 사용 (권장)
function identity<T>(value: T): T {
    return value;
}

// 오버로딩 사용 (복잡한 경우)
function processValue(value: string): string;
function processValue(value: number): number;
function processValue(value: string | number): string | number {
    return value;
}
```

### 제네릭 사용 패턴

| 패턴 | 사용 시기 | 예시 |
|------|-----------|------|
| **기본 제네릭** | 단순한 타입 매개변수 | `function identity<T>(value: T): T` |
| **제약 조건** | 특정 속성이나 메서드 필요 | `function getLength<T extends { length: number }>` |
| **다중 타입** | 여러 타입 매개변수 필요 | `function merge<T, U>(obj1: T, obj2: U)` |
| **조건부 타입** | 타입에 따른 조건부 로직 | `type ConditionalType<T> = T extends string ? ...` |

### 결론
TypeScript의 제네릭은 타입 안전성과 코드 재사용성을 동시에 제공하는 강력한 기능입니다. 적절한 제네릭 사용으로 중복 코드를 줄이고 타입 안전성을 확보할 수 있습니다. 제약 조건과 조건부 타입을 활용하여 더욱 정교한 타입 시스템을 구축할 수 있으며, 실제 프로젝트에서 API 클라이언트, 상태 관리, 유틸리티 함수 등에 널리 활용됩니다. 복잡한 제네릭 타입은 단계적으로 분해하여 가독성과 유지보수성을 향상시키는 것이 중요합니다.

