---
title: TypeScript undefined 타입
tags: [language, typescript, javascript]
updated: 2025-08-10
---

# TypeScript undefined 타입
## 배경

TypeScript에서 `undefined` 타입은 값이 할당되지 않은 변수의 상태를 나타내는 타입이다.

### undefined 타입의 필요성
- **초기화되지 않은 변수**: 값이 할당되지 않은 변수 표현
- **선택적 속성**: 객체의 선택적 프로퍼티 표현
- **함수 반환값**: 명시적으로 값을 반환하지 않는 함수
- **타입 안전성**: undefined 값의 안전한 처리

### 기본 개념
- **원시 타입**: JavaScript의 원시 타입 중 하나
- **값의 부재**: 값이 없음을 나타내는 특별한 값
- **타입 가드**: undefined 체크로 안전하게 처리
- **선택적 프로퍼티**: 객체에서 선택적으로 존재하는 프로퍼티

## 핵심

### 1. undefined 타입 기본 사용법

#### undefined 변수 선언
```typescript
// 명시적 undefined 타입 선언
let name: undefined;
let value: undefined = undefined;

// 초기화되지 않은 변수
let uninitialized: string;
console.log(uninitialized); // undefined

// undefined 값 할당
let message: string | undefined = undefined;
let age: number | undefined;

// undefined 체크
function checkUndefined(value: unknown): boolean {
    return value === undefined;
}

console.log(checkUndefined(undefined)); // true
console.log(checkUndefined(null));      // false
console.log(checkUndefined('hello'));   // false
```

`let uninitialized: string;` 뒤의 `console.log` 는 `strict` 에서 컴파일되지 않는다. 주석은 `undefined` 가 찍힌다고 하지만 그 지점에 도달하지 못한다.

```
error TS2454: Variable 'uninitialized' is used before being assigned.
```

런타임 값이 `undefined` 인 건 맞다. TypeScript 가 그 상태를 읽지 못하게 막는 것이고, 이게 `strictNullChecks` 가 하는 일이다. 그래서 `string` 으로 선언한 변수는 `undefined` 를 담을 수 있는 시점이 있어도 타입에는 그게 안 보인다. 실제로 값이 없을 수 있으면 `string | undefined` 로 적어야 타입과 사실이 맞는다.

`checkUndefined(null)` 이 `false` 인 것도 짚어 둘 만하다. `undefined` 와 `null` 은 다른 값이고 `===` 로는 구분된다. 반면 `==` 는 둘을 같게 본다.

```javascript
null === undefined   // false
null ==  undefined   // true   ← 이 성질 때문에 == null 이 관용구가 됐다
```

"둘 중 하나면 참"을 원할 때만 `== null` 을 쓰고, 나머지 자리에서는 `===` 를 쓴다. `== null` 은 ESLint 의 `eqeqeq` 규칙도 예외로 허용하는 유일한 `==` 용법이다.

#### undefined와 함수
```typescript
// undefined를 반환하는 함수
function findUser(id: number): string | undefined {
    const users = ['홍길동', '김철수', '이영희'];
    return users[id] || undefined;
}

// void vs undefined
function logMessage(message: string): void {
    console.log(message);
    // return 문이 없음 (암묵적으로 undefined 반환)
}

function processData(data: string): undefined {
    if (!data) {
        return undefined; // 명시적으로 undefined 반환
    }
    console.log('데이터 처리:', data);
    return undefined;
}

// 사용 예시
const user = findUser(1);
console.log(user); // "김철수"

const user2 = findUser(10);
console.log(user2); // undefined

logMessage('안녕하세요'); // "안녕하세요"
processData(''); // 아무것도 출력되지 않음
```

### 2. undefined와 선택적 프로퍼티

#### 선택적 프로퍼티 정의
```typescript
// 선택적 프로퍼티가 있는 인터페이스
interface Person {
    name: string;
    age?: number;        // 선택적 프로퍼티
    email?: string;      // 선택적 프로퍼티
    address?: string;    // 선택적 프로퍼티
}

// 선택적 프로퍼티 사용
const person1: Person = {
    name: '홍길동',
    age: 30
    // email과 address는 선택적이므로 생략 가능
};

const person2: Person = {
    name: '김철수'
    // age, email, address 모두 생략
};

// 선택적 프로퍼티 접근
function getPersonInfo(person: Person): string {
    let info = `이름: ${person.name}`;
    
    if (person.age !== undefined) {
        info += `, 나이: ${person.age}`;
    }
    
    if (person.email !== undefined) {
        info += `, 이메일: ${person.email}`;
    }
    
    return info;
}

console.log(getPersonInfo(person1)); // "이름: 홍길동, 나이: 30"
console.log(getPersonInfo(person2)); // "이름: 김철수"
```

#### 선택적 프로퍼티와 기본값
```typescript
// 기본값이 있는 함수 매개변수
function createUser(
    name: string,
    age: number = 20,
    email?: string
): Person {
    return {
        name,
        age,
        email
    };
}

// 사용 예시
const user1 = createUser('홍길동', 30, 'hong@example.com');
const user2 = createUser('김철수'); // age는 기본값 20, email은 undefined
const user3 = createUser('이영희', 25); // email은 undefined

console.log(user1); // { name: '홍길동', age: 30, email: 'hong@example.com' }
console.log(user2); // { name: '김철수', age: 20, email: undefined }
console.log(user3); // { name: '이영희', age: 25, email: undefined }
```

주석의 `email: undefined` 를 그냥 넘기면 안 된다. `createUser` 는 선택적 프로퍼티를 생략하지 않고 `undefined` 값으로 채워 넣는다. 둘은 읽을 때만 같아 보이고 실제로는 다른 객체다.

```javascript
const u2 = createUser('김철수');        // { name, age, email: undefined }
const u3 = { name: '김철수', age: 20 }; // email 키 자체가 없음

u2.email          // undefined
u3.email          // undefined   ← 여기까지는 똑같다

'email' in u2     // true
'email' in u3     // false
Object.keys(u2)   // ['name', 'age', 'email']
Object.keys(u3)   // ['name', 'age']
```

차이가 실제로 터지는 곳은 병합이다. 스프레드와 `Object.assign` 은 키의 존재만 보고 값을 덮어쓰므로, 명시적 `undefined` 가 기본값을 지운다.

```javascript
const defaults = { email: 'default@x.com' };

{ ...defaults, ...u2 }   // { email: undefined,         name: '김철수', age: 20 }
{ ...defaults, ...u3 }   // { email: 'default@x.com',   name: '김철수', age: 20 }
```

설정 병합이나 PATCH 요청 본문을 만드는 코드에서 기본값이 사라지는 사고가 여기서 나온다. "값을 안 보냈다"와 "값을 비우라고 보냈다"가 구분되지 않기 때문이다.

`JSON.stringify` 는 또 다르게 동작해서 명시적 `undefined` 를 조용히 버린다.

```javascript
JSON.stringify(u2)   // {"name":"김철수","age":20}   ← email 이 사라진다
```

그래서 서버로 나갈 때는 두 객체가 같아 보이고, 로컬 병합에서는 다르게 동작한다. 재현이 어려운 버그의 전형이다.

키를 아예 만들지 않으려면 조건부로 넣는다.

```typescript
return { name, age, ...(email !== undefined && { email }) };
```

TypeScript 쪽에서는 `exactOptionalPropertyTypes` 옵션을 켜면 `age?: number` 에 `undefined` 를 명시적으로 대입하는 것을 막아 준다. `strict` 에 포함되지 않으므로 따로 켜야 한다.

### 3. undefined와 타입 가드

#### undefined 타입 가드
```typescript
// undefined 체크를 위한 타입 가드
function isDefined<T>(value: T | undefined): value is T {
    return value !== undefined;
}

function isUndefined(value: unknown): value is undefined {
    return value === undefined;
}

// undefined 안전 처리
function processValue(value: string | undefined): string {
    if (value === undefined) {
        return '기본값';
    }
    return value.toUpperCase();
}

// 타입 가드 사용
function safeProcessValue(value: string | undefined): string {
    if (isDefined(value)) {
        return value.toUpperCase(); // value는 string 타입으로 좁혀짐
    }
    return '기본값';
}

// 사용 예시
console.log(processValue('hello'));     // "HELLO"
console.log(processValue(undefined));   // "기본값"

console.log(safeProcessValue('world')); // "WORLD"
console.log(safeProcessValue(undefined)); // "기본값"
```

## 예시

### 1. 실제 사용 사례

#### API 응답 처리
```typescript
// API 응답 타입 정의
interface ApiResponse<T> {
    data: T | undefined;
    success: boolean;
    message: string;
}

// 사용자 데이터 타입
interface User {
    id: number;
    name: string;
    email: string;
}

// API 호출 함수
async function fetchUser(id: number): Promise<ApiResponse<User>> {
    try {
        // 실제로는 API 호출
        if (id === 1) {
            return {
                data: {
                    id: 1,
                    name: '홍길동',
                    email: 'hong@example.com'
                },
                success: true,
                message: '사용자 조회 성공'
            };
        } else {
            return {
                data: undefined,
                success: false,
                message: '사용자를 찾을 수 없습니다.'
            };
        }
    } catch (error) {
        return {
            data: undefined,
            success: false,
            message: 'API 호출 실패'
        };
    }
}

// 안전한 데이터 처리
async function processUserData(id: number): Promise<void> {
    const response = await fetchUser(id);
    
    if (response.success && response.data !== undefined) {
        console.log(`사용자: ${response.data.name} (${response.data.email})`);
    } else {
        console.log(`오류: ${response.message}`);
    }
}

// 사용 예시
processUserData(1);  // "사용자: 홍길동 (hong@example.com)"
processUserData(999); // "오류: 사용자를 찾을 수 없습니다."
```

#### 설정 관리 시스템
```typescript
// 설정 타입 정의
interface Config {
    apiUrl: string;
    timeout?: number;
    retries?: number;
    debug?: boolean;
}

class ConfigManager {
    private config: Config;

    constructor(defaultConfig: Config) {
        this.config = {
            ...defaultConfig,
            timeout: defaultConfig.timeout ?? 5000,
            retries: defaultConfig.retries ?? 3,
            debug: defaultConfig.debug ?? false
        };
    }

    // 설정값 가져오기 (undefined 안전)
    getConfig<K extends keyof Config>(key: K): Config[K] {
        return this.config[key];
    }

    // 설정값 설정
    setConfig<K extends keyof Config>(key: K, value: Config[K]): void {
        this.config[key] = value;
    }

    // 선택적 설정값 가져오기
    getOptionalConfig<K extends keyof Config>(key: K): Config[K] | undefined {
        return this.config[key];
    }

    // 설정값이 있는지 확인
    hasConfig<K extends keyof Config>(key: K): boolean {
        return this.config[key] !== undefined;
    }

    // 전체 설정 가져오기
    getAllConfig(): Config {
        return { ...this.config };
    }
}

// 사용 예시
const configManager = new ConfigManager({
    apiUrl: 'https://api.example.com'
});

console.log(configManager.getConfig('apiUrl')); // "https://api.example.com"
console.log(configManager.getConfig('timeout')); // 5000 (기본값)

console.log(configManager.hasConfig('debug')); // true
console.log(configManager.getOptionalConfig('retries')); // 3

configManager.setConfig('debug', true);
console.log(configManager.getConfig('debug')); // true
```

### 2. 고급 패턴

#### undefined와 제네릭
```typescript
// undefined를 처리하는 제네릭 클래스
class Optional<T> {
    private value: T | undefined;

    constructor(value?: T) {
        this.value = value;
    }

    // 값이 있는지 확인
    isPresent(): boolean {
        return this.value !== undefined;
    }

    // 값이 없으면 기본값 반환
    orElse(defaultValue: T): T {
        return this.value !== undefined ? this.value : defaultValue;
    }

    // 값이 있으면 처리, 없으면 기본값
    map<U>(fn: (value: T) => U, defaultValue: U): U {
        return this.value !== undefined ? fn(this.value) : defaultValue;
    }

    // 값이 있을 때만 실행
    ifPresent(fn: (value: T) => void): void {
        if (this.value !== undefined) {
            fn(this.value);
        }
    }

    // 값 가져오기 (undefined 가능)
    get(): T | undefined {
        return this.value;
    }
}

// 사용 예시
const optional1 = new Optional<string>('hello');
const optional2 = new Optional<string>();

console.log(optional1.isPresent()); // true
console.log(optional2.isPresent()); // false

console.log(optional1.orElse('default')); // "hello"
console.log(optional2.orElse('default')); // "default"

optional1.ifPresent(value => console.log(`값: ${value}`)); // "값: hello"
optional2.ifPresent(value => console.log(`값: ${value}`)); // 아무것도 출력되지 않음

const result = optional1.map(value => value.toUpperCase(), 'DEFAULT');
console.log(result); // "HELLO"
```

#### undefined와 조건부 타입
```typescript
// undefined를 제거하는 유틸리티 타입
type NonUndefined<T> = T extends undefined ? never : T;

// 선택적 프로퍼티를 필수로 만드는 타입
type RequiredOptional<T> = {
    [K in keyof T]-?: NonUndefined<T[K]>;
};

// undefined 안전한 함수 타입
type SafeFunction<T, R> = (value: NonUndefined<T>) => R;

// 사용 예시
interface OptionalUser {
    name: string;
    age?: number;
    email?: string;
}

// 선택적 프로퍼티를 필수로 변환
type RequiredUser = RequiredOptional<OptionalUser>;
// 결과: { name: string; age: number; email: string }

// undefined 안전한 함수
function processUser(user: RequiredUser): void {
    console.log(`이름: ${user.name}, 나이: ${user.age}, 이메일: ${user.email}`);
}

// 사용 예시
const user: RequiredUser = {
    name: '홍길동',
    age: 30,
    email: 'hong@example.com'
};

processUser(user); // "이름: 홍길동, 나이: 30, 이메일: hong@example.com"
```

주석의 결과 `{ name: string; age: number; email: string }` 는 맞다. 다만 `NonUndefined<T[K]>` 는 있으나 없으나 결과가 같다. 매핑 타입의 `-?` 수식자가 선택성만 없애는 게 아니라 프로퍼티 타입에서 `undefined` 까지 함께 제거하기 때문이다.

```typescript
type Without = { [K in keyof OptionalUser]-?: OptionalUser[K] };   // NonUndefined 없이
const z: Without = { name: 'a', age: undefined, email: 'e' };
// error TS2322: Type 'undefined' is not assignable to type 'number'
```

`NonUndefined` 를 빼도 똑같이 막힌다. 즉 `RequiredOptional` 은 표준 유틸리티 타입 `Required<T>` 와 같은 것을 다시 만든 것이다.

```typescript
type RequiredUser = Required<OptionalUser>;   // 동일한 결과
```

`NonUndefined<T>` 자체가 쓸모없다는 뜻은 아니다. 매핑 타입 밖에서 유니온의 `undefined` 를 걷어낼 때는 제 역할을 한다. 이것도 표준으로 `NonNullable<T>` 가 있는데, 그쪽은 `null` 까지 같이 제거한다는 점이 다르다. 둘 중 무엇이 필요한지 정해서 쓴다.

## 운영 팁

### 성능 최적화

#### undefined 처리 최적화
```typescript
// undefined 체크 최적화
class UndefinedOptimizer {
    // 빠른 undefined 체크
    static isUndefined(value: unknown): value is undefined {
        return value === undefined;
    }

    // 안전한 프로퍼티 접근
    static safeGet<T, K extends keyof T>(obj: T, key: K): T[K] | undefined {
        return obj[key];
    }

    // 기본값과 함께 안전한 접근
    static safeGetWithDefault<T, K extends keyof T>(
        obj: T,
        key: K,
        defaultValue: NonUndefined<T[K]>
    ): NonUndefined<T[K]> {
        const value = obj[key];
        return value !== undefined ? value : defaultValue;
    }

    // 조건부 실행
    static executeIfDefined<T>(
        value: T | undefined,
        fn: (value: T) => void
    ): void {
        if (value !== undefined) {
            fn(value);
        }
    }
}

// 사용 예시
const data = { name: '홍길동', age: 30 };

console.log(UndefinedOptimizer.safeGet(data, 'name')); // "홍길동"
console.log(UndefinedOptimizer.safeGet(data, 'email')); // undefined

console.log(UndefinedOptimizer.safeGetWithDefault(data, 'age', 0)); // 30
console.log(UndefinedOptimizer.safeGetWithDefault(data, 'email', 'unknown')); // "unknown"

UndefinedOptimizer.executeIfDefined(data.name, name => console.log(`이름: ${name}`)); // "이름: 홍길동"
```

`'email'` 을 넘기는 두 줄은 컴파일되지 않는다. `data` 는 `{ name: string; age: number }` 로 추론되므로 `keyof` 에 `'email'` 이 없다.

```
error TS2345: Argument of type '"email"' is not assignable to parameter of type '"age" | "name"'.
```

이건 결함이 아니라 `K extends keyof T` 가 제대로 일한 결과다. 주석이 기대한 `undefined` 반환은 자바스크립트의 동작이고, TypeScript 는 그 접근 자체를 오타로 보고 막는다. 없는 키를 조회하는 게 정말 의도라면 시그니처를 `key: string` 으로 넓히거나 인덱스 시그니처가 있는 타입을 받아야 한다. 지금 상태에서는 예제와 구현이 서로 다른 걸 가정하고 있다.

`safeGet` 이 반환 타입에 `| undefined` 를 붙인 것도 실제로는 겉돈다. `T[K]` 는 이미 `keyof T` 로 좁혀진 실재하는 키의 타입이라 `undefined` 가 추가로 나올 일이 없다. 인덱스 접근이 정말 `undefined` 를 낼 수 있다고 타입에 반영하려면 `noUncheckedIndexedAccess` 를 켜야 하는데, 그건 인덱스 시그니처에만 적용되고 `keyof` 로 좁힌 접근에는 적용되지 않는다.

### 에러 처리

#### 안전한 undefined 처리
```typescript
// 안전한 undefined 처리 클래스
class SafeUndefinedHandler {
    // undefined 값 검증
    static validate<T>(value: T | undefined, errorMessage: string): T {
        if (value === undefined) {
            throw new Error(errorMessage);
        }
        return value;
    }

    // undefined 값 변환
    static transform<T, U>(
        value: T | undefined,
        transformer: (value: T) => U,
        defaultValue: U
    ): U {
        if (value === undefined) {
            return defaultValue;
        }
        return transformer(value);
    }

    // undefined 값 필터링
    static filterUndefined<T>(values: (T | undefined)[]): T[] {
        return values.filter((value): value is T => value !== undefined);
    }

    // 안전한 객체 생성
    static createSafeObject<T extends Record<string, any>>(
        obj: Partial<T>,
        defaults: T
    ): T {
        const result = { ...defaults };
        
        for (const [key, value] of Object.entries(obj)) {
            if (value !== undefined) {
                result[key as keyof T] = value;
            }
        }
        
        return result;
    }
}

// 사용 예시
try {
    const name = SafeUndefinedHandler.validate(
        undefined,
        '이름이 필요합니다.'
    );
} catch (error) {
    console.error(error.message); // "이름이 필요합니다."
}

const numbers = [1, undefined, 3, undefined, 5];
const filteredNumbers = SafeUndefinedHandler.filterUndefined(numbers);
console.log(filteredNumbers); // [1, 3, 5]

const userDefaults = { name: 'Unknown', age: 0, email: 'unknown@example.com' };
const userData = { name: '홍길동', age: 30 };
const safeUser = SafeUndefinedHandler.createSafeObject(userData, userDefaults);
console.log(safeUser); // { name: '홍길동', age: 30, email: 'unknown@example.com' }
```

## 참고

### undefined 타입 특성

| 특성 | 설명 |
|------|------|
| **원시 타입** | JavaScript의 원시 타입 중 하나 |
| **값의 부재** | 값이 할당되지 않았음을 나타냄 |
| **타입 가드** | undefined 체크를 통한 안전한 처리 |
| **선택적 프로퍼티** | 객체에서 선택적으로 존재하는 프로퍼티 |

### undefined vs null vs void 비교표

| 타입 | 설명 | 사용 목적 |
|------|------|-----------|
| **undefined** | 값이 할당되지 않음 | 초기화되지 않은 변수, 선택적 프로퍼티 |
| **null** | 의도적으로 값이 없음 | 명시적으로 값이 없음을 표현 |
| **void** | 반환값이 없음 | 함수의 반환 타입 |

### 결론
TypeScript의 undefined 타입은 값이 할당되지 않은 상태를 나타낸다.
선택적 프로퍼티와 같이 쓰면 유연한 객체 구조를 만들 수 있다.
undefined 값은 타입 가드로 걸러서 안전하게 처리한다.
undefined와 null의 차이를 알고 상황에 맞게 쓴다.
제네릭과 조건부 타입으로 undefined를 처리한다.
undefined를 안전하게 처리해서 런타임 오류를 막는다.
undefined 타입의 특성을 이해하고 타입 안전성을 지킨다.

