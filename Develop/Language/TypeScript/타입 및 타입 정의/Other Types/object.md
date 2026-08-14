---
title: TypeScript object 타입
tags: [language, typescript]
updated: 2025-08-10
---

# TypeScript object 타입
## 배경

TypeScript에서 `object` 타입은 모든 객체 유형을 포함하는 일반적인 객체 타입입니다.

### object 타입의 필요성
- **일반적인 객체 처리**: 구체적인 구조를 알 수 없는 객체 처리
- **동적 객체**: 런타임에 구조가 결정되는 객체
- **외부 라이브러리**: 타입 정의가 없는 외부 라이브러리 객체
- **타입 안전성**: 객체임을 보장하면서도 유연한 처리

### 기본 개념
- **모든 객체 포함**: 프로퍼티를 가지는 모든 JavaScript 객체
- **구조 불명**: 구체적인 프로퍼티 구조를 알 수 없음
- **타입 제한**: null, undefined, 원시 타입은 제외
- **유연성**: 다양한 객체 구조를 수용

## 핵심

### 1. object 타입 기본 사용법

#### 기본 object 타입 선언
```typescript
// 기본 object 타입
let person: object = {
    name: '홍길동',
    age: 30,
    city: '서울'
};

// object 타입은 구체적인 프로퍼티에 접근할 수 없음
// console.log(person.name); // 오류: Property 'name' does not exist on type 'object'

// 대신 인덱스 접근 사용
console.log((person as any).name); // '홍길동'

// 또는 타입 단언 사용
const typedPerson = person as { name: string; age: number; city: string };
console.log(typedPerson.name); // '홍길동'
```

#### object 타입과 타입 가드
```typescript
// object 타입 체크
function isObject(value: unknown): value is object {
    return typeof value === 'object' && value !== null;
}

// 사용 예시
function processValue(value: unknown): void {
    if (isObject(value)) {
        // value는 object 타입으로 좁혀짐
        console.log('객체입니다:', value);
        
        // 하지만 여전히 구체적인 프로퍼티에 접근할 수 없음
        // console.log(value.name); // 오류
    } else {
        console.log('객체가 아닙니다:', value);
    }
}

processValue({ name: '홍길동' }); // "객체입니다: { name: '홍길동' }"
processValue('문자열');           // "객체가 아닙니다: 문자열"
processValue(null);               // "객체가 아닙니다: null"
```

**`isObject` 는 이름이 약속한 `object` 타입과 범위가 다르다.** TypeScript 의 `object` 는 함수도 포함하는데, `typeof` 는 함수를 `'function'` 으로 보고하므로 이 가드가 함수를 떨어뜨린다.

```typescript
let f: object = () => {};      // 통과 — 함수는 object 다
let a: object = [1, 2, 3];     // 통과 — 배열도 object 다
let n: object = null;          // error TS2322: Type 'null' is not assignable to type 'object'
let s: object = 'str';         // error TS2322
```

```javascript
isObject(() => {})     // false  ← 그런데 함수는 object 타입이다
isObject([])           // true
isObject(new Date())   // true
```

즉 `value is object` 라는 술어가 거짓말을 한다. 함수를 넘기면 "객체가 아닙니다"가 찍히지만 그 값은 `object` 자리에 얼마든지 대입된다. `typeof` 의 `'object'` 와 타입으로서의 `object` 는 **이름만 같고 경계가 다르다.**

배열이 `true` 로 나오는 것도 실무에서 자주 문제가 된다. JSON 을 받아 "객체인지" 확인할 때 배열을 걸러내고 싶은 경우가 대부분인데 이 가드는 통과시킨다. 의도한 범위를 직접 적는 편이 낫다.

```typescript
function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}
```

`typeof null === 'object'` 는 JavaScript 초기부터 남아 있는 결함이고 고쳐질 계획이 없다. **`typeof x === 'object'` 를 쓸 때 `x !== null` 을 붙이는 건 선택이 아니라 의무다.** 위 코드가 그 점은 제대로 지키고 있다.

### 2. object 타입과 Record 타입

#### Record 타입 사용
```typescript
// Record 타입으로 더 구체적인 object 타입 정의
type StringObject = Record<string, string>;
type NumberObject = Record<string, number>;
type MixedObject = Record<string, any>;

// 사용 예시
let stringObj: StringObject = {
    name: '홍길동',
    city: '서울',
    country: '한국'
};

let numberObj: NumberObject = {
    age: 30,
    height: 175,
    weight: 70
};

let mixedObj: MixedObject = {
    name: '홍길동',
    age: 30,
    isActive: true,
    hobbies: ['독서', '운동']
};

// 프로퍼티에 접근 가능
console.log(stringObj.name);     // '홍길동'
console.log(numberObj.age);      // 30
console.log(mixedObj.hobbies);   // ['독서', '운동']
```

`Record<string, string>` 이 `object` 보다 나은 건 맞지만, **"모든 문자열 키"를 허용한다는 건 존재하지 않는 키도 허용한다는 뜻**이다. 오타가 컴파일을 통과한다.

```typescript
const t: string = stringObj.typoKey;   // 기본 설정에서는 에러가 없다
console.log(t.toUpperCase());          // TypeError: Cannot read properties of undefined
```

`stringObj.typoKey` 의 타입은 `string` 인데 실제 값은 `undefined` 다. 타입과 값이 어긋난 채 통과하는 자리다. 이걸 잡아 주는 컴파일러 옵션이 따로 있다.

```
tsconfig: "noUncheckedIndexedAccess": true

error TS2322: Type 'string | undefined' is not assignable to type 'string'.
```

이 옵션은 `strict: true` 에 **포함되지 않는다.** 따로 켜야 한다. 켜면 인덱스 시그니처로 꺼낸 값이 전부 `| undefined` 가 붙어 코드 곳곳에서 검사를 요구하게 되는데, 그게 실제 런타임 동작과 맞는 타입이다.

키 집합이 정해져 있다면 처음부터 `Record<string, T>` 대신 유니온으로 좁히는 게 낫다. 그러면 오타가 그 자리에서 잡힌다.

```typescript
type Lang = 'ko' | 'en' | 'ja';
const labels: Record<Lang, string> = { ko: '한국어', en: 'English', ja: '日本語' };
labels.kr;   // error TS2339: Property 'kr' does not exist
```

`Record<string, any>`(예제의 `MixedObject`)는 사실상 `any` 다. 값 타입에 `any` 를 두면 그 뒤 접근은 전부 검사되지 않는다. 값의 형태를 모를 때는 `unknown` 을 쓰는 편이 좁혀 쓰도록 강제해 준다.

#### 동적 프로퍼티 처리
```typescript
// 동적으로 프로퍼티를 추가하는 함수
function createDynamicObject(properties: Record<string, any>): object {
    const obj: object = {};
    
    for (const [key, value] of Object.entries(properties)) {
        (obj as any)[key] = value;
    }
    
    return obj;
}

// 사용 예시
const dynamicObj = createDynamicObject({
    name: '홍길동',
    age: 30,
    city: '서울'
});

console.log(dynamicObj); // { name: '홍길동', age: 30, city: '서울' }
```

### 3. object 타입과 인터페이스 비교

#### object vs 인터페이스
```typescript
// object 타입 사용
let personObject: object = {
    name: '홍길동',
    age: 30
};

// 인터페이스 사용
interface Person {
    name: string;
    age: number;
}

let personInterface: Person = {
    name: '홍길동',
    age: 30
};

// 비교
console.log((personObject as any).name); // 타입 단언 필요
console.log(personInterface.name);        // 직접 접근 가능

// 함수 매개변수로 사용
function processObject(obj: object): void {
    console.log('객체 처리:', obj);
    // obj.name 접근 불가
}

function processPerson(person: Person): void {
    console.log('사람 처리:', person.name, person.age);
    // person.name, person.age 직접 접근 가능
}

processObject(personObject);
processPerson(personInterface);
```

## 예시

### 1. 실제 사용 사례

#### 외부 API 응답 처리
```typescript
// 외부 API에서 반환되는 객체 (구조를 알 수 없음)
async function fetchExternalData(): Promise<object> {
    const response = await fetch('https://api.example.com/data');
    return response.json();
}

// 안전한 데이터 처리
async function processExternalData(): Promise<void> {
    try {
        const data = await fetchExternalData();
        
        // object 타입이므로 타입 가드로 안전하게 처리
        if (typeof data === 'object' && data !== null) {
            // 구체적인 프로퍼티에 접근하려면 타입 단언 필요
            const typedData = data as any;
            
            if (typedData.users && Array.isArray(typedData.users)) {
                console.log('사용자 수:', typedData.users.length);
            }
            
            if (typedData.metadata && typeof typedData.metadata === 'object') {
                console.log('메타데이터:', typedData.metadata);
            }
        }
    } catch (error) {
        console.error('데이터 처리 오류:', error);
    }
}
```

#### 설정 객체 처리
```typescript
// 동적인 설정 객체
type ConfigObject = Record<string, any>;

class ConfigManager {
    private config: ConfigObject = {};

    setConfig(key: string, value: any): void {
        this.config[key] = value;
    }

    getConfig(key: string): any {
        return this.config[key];
    }

    getAllConfig(): object {
        return { ...this.config };
    }

    // 타입 안전한 설정 가져오기
    getTypedConfig<T>(key: string, defaultValue: T): T {
        const value = this.config[key];
        return value !== undefined ? value : defaultValue;
    }
}

// 사용 예시
const configManager = new ConfigManager();

configManager.setConfig('apiUrl', 'https://api.example.com');
configManager.setConfig('timeout', 5000);
configManager.setConfig('retries', 3);
configManager.setConfig('features', ['auth', 'logging']);

console.log(configManager.getConfig('apiUrl')); // 'https://api.example.com'
console.log(configManager.getTypedConfig('timeout', 3000)); // 5000
console.log(configManager.getAllConfig()); // 전체 설정 객체
```

### 2. 고급 패턴

#### object 타입과 제네릭
```typescript
// 제네릭을 사용한 유연한 객체 처리
class ObjectProcessor<T extends object> {
    private data: T;

    constructor(data: T) {
        this.data = data;
    }

    // 객체의 모든 프로퍼티를 문자열로 변환
    stringify(): Record<string, string> {
        const result: Record<string, string> = {};
        
        for (const [key, value] of Object.entries(this.data)) {
            result[key] = String(value);
        }
        
        return result;
    }

    // 특정 프로퍼티만 추출
    pick<K extends keyof T>(keys: K[]): Pick<T, K> {
        const result = {} as Pick<T, K>;
        
        for (const key of keys) {
            if (key in this.data) {
                result[key] = this.data[key];
            }
        }
        
        return result;
    }

    // 객체 병합
    merge(other: Partial<T>): T {
        return { ...this.data, ...other };
    }
}

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
    age: number;
}

const user: User = {
    id: 1,
    name: '홍길동',
    email: 'hong@example.com',
    age: 30
};

const processor = new ObjectProcessor(user);

console.log(processor.stringify());
// { id: '1', name: '홍길동', email: 'hong@example.com', age: '30' }

console.log(processor.pick(['name', 'email']));
// { name: '홍길동', email: 'hong@example.com' }

console.log(processor.merge({ age: 31 }));
// { id: 1, name: '홍길동', email: 'hong@example.com', age: 31 }
```

#### 타입 안전한 object 처리
```typescript
// 타입 안전한 객체 검증
function validateObject(obj: object, schema: Record<string, string>): boolean {
    for (const [key, expectedType] of Object.entries(schema)) {
        const value = (obj as any)[key];
        
        if (value === undefined) {
            console.error(`필수 프로퍼티 누락: ${key}`);
            return false;
        }
        
        if (typeof value !== expectedType) {
            console.error(`타입 불일치: ${key} (예상: ${expectedType}, 실제: ${typeof value})`);
            return false;
        }
    }
    
    return true;
}

// 사용 예시
const userSchema = {
    name: 'string',
    age: 'number',
    email: 'string'
};

const validUser = { name: '홍길동', age: 30, email: 'hong@example.com' };
const invalidUser = { name: '홍길동', age: '30', email: 'hong@example.com' };

console.log(validateObject(validUser, userSchema));   // true
console.log(validateObject(invalidUser, userSchema)); // false (age가 string)
```

두 예제는 통과하지만, 이 검증기는 **`typeof` 를 스키마 언어로 쓴 탓에 세 종류의 값을 그대로 받아들인다.**

```javascript
validateObject({ cfg: null },   { cfg: 'object' })  // true  ← null 이 object 로 통과
validateObject({ cfg: [1, 2] }, { cfg: 'object' })  // true  ← 배열도 object
validateObject({ age: NaN },    { age: 'number' })  // true  ← NaN 도 number
```

앞의 두 줄은 `typeof` 의 알려진 한계 그대로다. 세 번째가 특히 조용하다. `NaN` 은 `typeof` 가 `'number'` 라서 나이 검증을 통과한 뒤 이후 계산을 전부 `NaN` 으로 만든다.

`value === undefined` 로만 누락을 판정하는 것도 좁다. **`null` 은 누락으로 잡히지 않고** 타입 검사로 넘어가, 위처럼 `'object'` 스키마라면 통과한다. JSON 에는 `undefined` 가 없고 `null` 만 있으므로, API 응답 검증에서는 이쪽이 실제로 마주치는 경우다.

`typeof` 로 표현할 수 있는 건 원시 타입 몇 가지뿐이라 이 방향은 금방 한계에 닿는다. 스키마 검증이 필요하면 zod 같은 라이브러리를 쓰는 편이 낫다. **검증 로직과 타입이 한 정의에서 함께 나오므로 둘이 어긋날 수 없다** — 손으로 쓴 스키마 문자열은 인터페이스가 바뀌어도 컴파일러가 갱신을 요구하지 않는다. 위 `userSchema` 에서 필드를 하나 빼도 아무 에러가 나지 않는다.

## 운영 팁

### 성능 최적화

#### object 타입 최적화
```typescript
// object 타입 대신 구체적인 타입 사용
// 좋지 않은 예
function processData(data: object): void {
    const typedData = data as any;
    // 처리 로직
}

// 좋은 예
interface DataStructure {
    id: number;
    value: string;
}

function processData(data: DataStructure): void {
    // 직접 프로퍼티 접근 가능
    console.log(data.id, data.value);
}

// 또는 제네릭 사용
function processGenericData<T extends object>(data: T): void {
    // T의 구체적인 타입 정보 유지
    console.log(data);
}
```

### 에러 처리

#### 안전한 object 타입 사용
```typescript
// 안전한 object 타입 처리
function safeObjectAccess(obj: object, key: string): any {
    if (typeof obj === 'object' && obj !== null && key in obj) {
        return (obj as any)[key];
    }
    return undefined;
}

// 타입 가드를 통한 안전한 처리
function isObjectWithProperty(obj: unknown, key: string): obj is Record<string, any> {
    return typeof obj === 'object' && obj !== null && key in obj;
}

// 사용 예시
const data: object = { name: '홍길동', age: 30 };

console.log(safeObjectAccess(data, 'name')); // '홍길동'
console.log(safeObjectAccess(data, 'city')); // undefined

if (isObjectWithProperty(data, 'age')) {
    console.log(data.age); // 안전하게 접근 가능
}
```

## 참고

### object 타입 특성

| 특성 | 설명 |
|------|------|
| **포함 범위** | 모든 객체 (null, undefined, 원시 타입 제외) |
| **프로퍼티 접근** | 직접 접근 불가 (타입 단언 필요) |
| **타입 안전성** | 낮음 (구체적인 구조를 알 수 없음) |
| **사용 목적** | 일반적인 객체 처리, 외부 라이브러리 |

### object vs any vs unknown 비교표

| 타입 | 설명 | 프로퍼티 접근 | 타입 안전성 |
|------|------|---------------|-------------|
| **object** | 모든 객체 | 불가능 | 낮음 |
| **any** | 모든 타입 | 가능 | 없음 |
| **unknown** | 모든 타입 | 불가능 | 높음 |

### 결론
TypeScript의 object 타입은 모든 객체를 포함하는 일반적인 타입입니다.
구체적인 프로퍼티 구조를 알 수 없는 경우에 유용합니다.
가능하면 구체적인 인터페이스나 타입을 사용하는 것이 권장됩니다.
타입 가드와 타입 단언을 통해 안전하게 object 타입을 처리하세요.
Record 타입을 사용하여 더 구체적인 object 타입을 정의할 수 있습니다.
object 타입의 한계를 이해하고 적절한 상황에서만 사용하세요.

