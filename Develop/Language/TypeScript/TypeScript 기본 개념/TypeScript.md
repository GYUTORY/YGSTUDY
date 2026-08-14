---
title: TypeScript
tags: [language, typescript]
updated: 2025-12-16
---

# TypeScript

## 배경

TypeScript는 2012년 Microsoft에서 개발한 JavaScript의 상위 집합(Superset) 언어입니다. JavaScript에 정적 타입 시스템을 추가하여 대규모 애플리케이션 개발에서 발생하는 문제들을 해결하고, 개발자 경험을 향상시키기 위해 만들어졌습니다.

### TypeScript의 필요성

#### 1. 타입 안전성 (Type Safety)
JavaScript는 동적 타입 언어로, 런타임에 타입 오류가 발생할 수 있습니다. TypeScript는 컴파일 타임에 타입 오류를 감지하여 런타임 오류를 방지합니다.

```typescript
// JavaScript - 런타임 오류 발생 가능
function add(a, b) {
    return a + b;
}
console.log(add(5, "3")); // "53" (의도하지 않은 결과)

// TypeScript - 컴파일 타임 오류 감지
function add(a: number, b: number): number {
    return a + b;
}
// console.log(add(5, "3")); // 컴파일 오류: Argument of type 'string' is not assignable to parameter of type 'number'
```

#### 2. 향상된 개발자 경험 (Developer Experience)
- **IntelliSense**: IDE에서 정확한 자동완성 제공
- **리팩토링 지원**: 안전한 코드 변경과 이동
- **문서화**: 타입이 곧 문서 역할
- **오류 예방**: 개발 단계에서 버그 조기 발견

#### 3. 대규모 프로젝트 지원
- **코드 구조화**: 명확한 인터페이스와 타입 정의
- **팀 협업**: 일관된 코딩 스타일과 타입 규칙
- **유지보수성**: 코드 변경 시 영향 범위 파악 용이
- **확장성**: 모듈화된 아키텍처 지원

#### 4. JavaScript 생태계 호환성
- **점진적 도입**: 기존 JavaScript 코드를 그대로 사용 가능
- **라이브러리 지원**: npm 패키지와 완벽 호환
- **브라우저 호환**: 컴파일된 JavaScript로 모든 브라우저에서 실행

### 기본 개념

#### 1. 정적 타입 시스템 (Static Type System)
TypeScript는 변수, 함수 매개변수, 반환값, 객체 프로퍼티 등에 타입을 명시적으로 선언할 수 있습니다.

```typescript
// 기본 타입 선언
let userName: string = "홍길동";
let userAge: number = 30;
let isActive: boolean = true;
let hobbies: string[] = ["독서", "운동"];

// 함수 타입 선언
function calculateTotal(price: number, tax: number): number {
    return price + (price * tax);
}

// 객체 타입 선언
interface User {
    id: number;
    name: string;
    email: string;
    age?: number; // 선택적 프로퍼티
}
```

#### 2. JavaScript 상위 집합 (JavaScript Superset)
모든 유효한 JavaScript 코드는 TypeScript 코드로도 유효합니다. 기존 JavaScript 프로젝트에 점진적으로 TypeScript를 도입할 수 있습니다.

```typescript
// 기존 JavaScript 코드
const existingCode = {
    message: "Hello World",
    numbers: [1, 2, 3],
    add: function(a, b) {
        return a + b;
    }
};

// TypeScript 기능 추가
interface MathUtils {
    add(a: number, b: number): number;
    multiply(a: number, b: number): number;
}

const mathUtils: MathUtils = {
    add: (a, b) => a + b,
    multiply: (a, b) => a * b
};
```

#### 3. 컴파일 타임 검사 (Compile-time Checking)
TypeScript 컴파일러(tsc)가 코드를 분석하여 타입 오류를 감지합니다.

```typescript
// 타입 오류 예시
let count: number = 10;
// count = "hello"; // Error: Type 'string' is not assignable to type 'number'

function greet(name: string): string {
    return `Hello, ${name}!`;
}
// greet(123); // Error: Argument of type 'number' is not assignable to parameter of type 'string'
```

**"컴파일 타임 검사"의 뒷면은 "런타임에는 아무것도 없다"이다.** 타입은 컴파일하면서 전부 지워진다. 아래는 같은 파일의 입력과 출력이다.

```typescript
// 입력
interface User { id: number; name: string }
type Role = 'admin' | 'user';

function greet(user: User, role: Role): string {
  return `${user.name} (${role})`;
}

const u = JSON.parse('{"id":1,"name":"a"}') as User;
export default greet(u, 'admin');
```

```javascript
// 출력 — tsc 가 만든 .js
function greet(user, role) {
    return `${user.name} (${role})`;
}
const u = JSON.parse('{"id":1,"name":"a"}');
export default greet(u, 'admin');
```

`interface`·`type`·`as`·매개변수 타입이 통째로 사라지고 실행되는 코드만 남는다. 여기서 나오는 결론이 몇 가지 있고, 전부 실무에서 반복해서 걸린다.

- **경계를 넘어 들어오는 값은 타입이 지켜 주지 않는다.** HTTP 응답, `JSON.parse`, `localStorage`, `process.env`, DB 드라이버가 준 행 — 전부 컴파일러가 본 적 없는 값이다. 그 자리에는 런타임 검증(zod·ajv 같은 스키마 검사나 직접 쓴 가드)이 따로 필요하다.
- **타입으로 분기할 수 없다.** `if (x is User)` 같은 문법이 없는 이유다. 런타임에 남는 것은 `typeof`·`instanceof`·프로퍼티 존재 여부뿐이고, 그래서 판별 유니온에 `kind` 같은 **값**을 넣는다.
- **타입은 성능에 영향을 주지 않는다.** 지워지므로 실행 코드가 늘지 않는다. 대신 `enum`·`namespace`·`class` 의 프로퍼티 초기화처럼 **코드를 생성하는** 문법은 예외다. 이 둘을 구분해 두면 "왜 이건 남고 저건 사라지지"에서 헤매지 않는다.

#### 4. 점진적 타입 적용 (Gradual Typing)
기존 JavaScript 프로젝트에 TypeScript를 점진적으로 도입할 수 있습니다.

```typescript
// 1단계: 기존 JavaScript 파일을 .ts로 변경
// 2단계: 중요한 부분부터 타입 추가
// 3단계: 점진적으로 모든 코드에 타입 적용

// any 타입으로 시작하여 점진적으로 타입 강화
let data: any = fetchData();
// 나중에 구체적인 타입으로 변경
let userData: User = fetchData();
```

## 핵심

### 1. TypeScript의 주요 특징

#### 1.1 정적 타입 지원 (Static Type Support)

TypeScript는 다양한 타입을 지원하여 코드의 안전성과 가독성을 높입니다.

##### 기본 타입 (Primitive Types)
```typescript
// 숫자 타입
let age: number = 25;
let price: number = 99.99;
let binary: number = 0b1010; // 2진수
let octal: number = 0o744;   // 8진수
let hex: number = 0xff;      // 16진수

// 문자열 타입
let name: string = "홍길동";
let message: string = `안녕하세요, ${name}님!`;
let multiline: string = `
    여러 줄
    문자열
`;

// 불린 타입
let isStudent: boolean = true;
let isActive: boolean = false;

// 배열 타입
let numbers: number[] = [1, 2, 3, 4, 5];
let fruits: Array<string> = ["사과", "바나나", "오렌지"];
let mixed: (string | number)[] = ["hello", 42, "world"];

// 튜플 타입 (고정 길이 배열)
let person: [string, number, boolean] = ["홍길동", 30, true];
let coordinates: [number, number] = [10, 20];

// 열거형 (Enum)
enum Color {
    Red = "red",
    Green = "green",
    Blue = "blue"
}
let favoriteColor: Color = Color.Blue;

// Any 타입 (타입 검사 비활성화)
let dynamicValue: any = 42;
dynamicValue = "hello";
dynamicValue = true;

// Unknown 타입 (타입 안전한 any)
let userInput: unknown = getUserInput();
if (typeof userInput === "string") {
    console.log(userInput.toUpperCase());
}

// Void 타입 (함수 반환값 없음)
function logMessage(message: string): void {
    console.log(message);
}

// Never 타입 (절대 발생하지 않는 값)
function throwError(message: string): never {
    throw new Error(message);
}
```

이 목록에서 **`enum` 만 성격이 다르다.** 나머지는 전부 컴파일하면 사라지는데 `enum` 은 실제 자바스크립트 객체를 만들어 낸다. 위 `Color` 가 이렇게 나간다.

```javascript
var Color;
(function (Color) {
    Color["Red"] = "red";
    Color["Green"] = "green";
    Color["Blue"] = "blue";
})(Color || (Color = {}));
```

숫자 enum 은 여기서 한 걸음 더 간다. **양방향 매핑을 만들려고 각 멤버를 두 번 대입한다.**

```javascript
Status[Status["Active"] = 0] = "Active";
```

그 결과가 실무에서 자주 걸린다.

```javascript
Object.keys(Status)   // ['0','1','2','Active','Inactive','Pending']  ← 멤버 3개인데 키 6개
Object.keys(Color)    // ['Red','Green','Blue']                       ← 문자열 enum 은 3개
Status[0]             // 'Active'   역방향 조회가 된다
Color['red']          // undefined  문자열 enum 은 역방향이 없다
```

**숫자 enum 을 `Object.keys` 나 `for...in` 으로 순회하면 값이 두 배로 나온다.** 셀렉트 박스 옵션을 만들다가 항목이 두 배가 되는 사고가 여기서 나온다. 순회할 일이 있으면 문자열 enum 을 쓰거나 숫자 키를 걸러 낸다.

```typescript
Object.keys(Status).filter(k => isNaN(Number(k)));   // ['Active','Inactive','Pending']
```

enum 은 **명목적(nominal)으로 동작한다**는 점도 이 언어에서 드문 특성이다. 값이 같아도 다른 enum 끼리는 대입되지 않는다.

```typescript
enum A { X = 1 }
enum B { X = 1 }
const cross: A = B.X;   // error TS2322: Type 'B' is not assignable to type 'A'
const n: A = 1;         // error TS2322: Type '1' is not assignable to type 'A'
```

구조적 타이핑이 기본인 TypeScript 에서 이것만 이름으로 판단한다. 값 실수를 막아 주지만, 라이브러리 경계를 넘나들 때는 같은 모양인데 대입이 안 돼 불편해진다.

이런 특수성 때문에 **enum 대신 리터럴 유니온과 `as const` 객체를 쓰는 쪽이 요즘 더 흔하다.**

```typescript
const Color = { Red: 'red', Green: 'green', Blue: 'blue' } as const;
type Color = typeof Color[keyof typeof Color];   // 'red' | 'green' | 'blue'
```

런타임 객체가 평범한 객체 하나뿐이라 `Object.keys` 가 예상대로 동작하고, 타입은 문자열 리터럴 유니온이라 JSON 으로 오간 값과도 그대로 맞는다. 반대로 enum 은 API 응답의 문자열을 받을 때 `as Color` 단언이 필요해진다.

`const enum` 은 아예 인라인돼 런타임 객체를 만들지 않는다.

```typescript
const enum Direction { Up, Down }
export const d = Direction.Up;
```

```javascript
exports.d = 0 /* Direction.Up */;   // 객체 없이 값만 박힌다
```

번들 크기에는 유리하지만 **선언을 보지 않고는 값을 알 수 없어서** 파일 단위로 트랜스파일하는 도구(Babel, esbuild, SWC)와 잘 맞지 않는다. 그런 빌드 체인을 쓴다면 `const enum` 은 피한다.

##### 함수 타입 선언
```typescript
// 기본 함수 선언
function greet(name: string): string {
    return `안녕하세요, ${name}님!`;
}

// 화살표 함수
const add = (a: number, b: number): number => a + b;

// 함수 타입 별칭
type MathOperation = (a: number, b: number) => number;
const multiply: MathOperation = (a, b) => a * b;

// 선택적 매개변수
function createUser(name: string, age?: number): User {
    return {
        id: Math.random(),
        name,
        age: age || 0
    };
}

// 기본값 매개변수
function greetWithDefault(name: string = "익명"): string {
    return `안녕하세요, ${name}님!`;
}

// 나머지 매개변수
function sum(...numbers: number[]): number {
    return numbers.reduce((total, num) => total + num, 0);
}

// 함수 오버로드
function processValue(value: string): string;
function processValue(value: number): number;
function processValue(value: string | number): string | number {
    if (typeof value === "string") {
        return value.toUpperCase();
    }
    return value * 2;
}
```

##### 객체 타입 선언
```typescript
// 인터페이스 정의
interface User {
    readonly id: number;        // 읽기 전용
    name: string;
    email: string;
    age?: number;              // 선택적 프로퍼티
    [key: string]: any;        // 인덱스 시그니처
}

// 인터페이스 확장
interface AdminUser extends User {
    permissions: string[];
    isActive: boolean;
}

// 타입 별칭
type Status = "pending" | "approved" | "rejected";
type UserRole = "admin" | "user" | "guest";

// 교집합 타입
type Admin = User & {
    role: "admin";
    permissions: string[];
};

// 유니온 타입
type StringOrNumber = string | number;

// 객체 리터럴 타입
const user: User = {
    id: 1,
    name: "홍길동",
    email: "hong@example.com",
    age: 30
};

// user.id = 2; // 오류: 읽기 전용 프로퍼티는 수정할 수 없음
```

#### 1.2 JavaScript와의 하위 호환성 (JavaScript Compatibility)

TypeScript는 JavaScript의 상위 집합이므로 기존 JavaScript 코드를 그대로 사용할 수 있습니다.

```typescript
// 기존 JavaScript 코드를 그대로 사용 가능
const existingJsCode = {
    message: "Hello from JavaScript",
    numbers: [1, 2, 3, 4, 5],
    add: function(a: number, b: number) {
        return a + b;
    }
};

// JavaScript의 모든 기능 지원
const jsFeatures = {
    // 화살표 함수
    arrowFunction: (x: number) => x * 2,
    
    // 구조 분해 할당
    destructuring: ({ name, age }: { name: string; age: number }) => {
        return `${name} is ${age} years old`;
    },
    
    // 스프레드 연산자
    spread: (...args: number[]) => Math.max(...args),
    
    // 템플릿 리터럴
    template: (name: string) => `Hello, ${name}!`,
    
    // 클래스
    class: class Person {
        constructor(public name: string, public age: number) {}
        
        greet(): string {
            return `Hi, I'm ${this.name}`;
        }
    }
};

// TypeScript 기능 추가
interface MathUtils {
    add(a: number, b: number): number;
    multiply(a: number, b: number): number;
    divide(a: number, b: number): number;
}

const mathUtils: MathUtils = {
    add: (a, b) => a + b,
    multiply: (a, b) => a * b,
    divide: (a, b) => {
        if (b === 0) {
            throw new Error("Division by zero");
        }
        return a / b;
    }
};

// 사용 예시
console.log(mathUtils.add(5, 3));        // 8
console.log(mathUtils.multiply(4, 6));   // 24
console.log(mathUtils.divide(10, 2));    // 5
```

#### 1.3 타입 추론 (Type Inference)

TypeScript는 명시적으로 타입을 지정하지 않아도 값으로부터 타입을 자동으로 추론합니다.

**기본 타입 추론**:
```typescript
// 변수 초기화 시 타입 추론
let name = "홍길동";        // string으로 추론
let age = 30;              // number로 추론
let isActive = true;        // boolean으로 추론
let numbers = [1, 2, 3];    // number[]로 추론

// 함수 반환 타입 추론
function add(a: number, b: number) {
    return a + b;  // 반환 타입이 number로 추론됨
}

// 객체 타입 추론
const user = {
    id: 1,
    name: "홍길동",
    email: "hong@example.com"
};
// { id: number; name: string; email: string }로 추론
```

**타입 추론의 한계**:
```typescript
// 배열 초기화 시 빈 배열은 any[]로 추론됨
let items = [];  // any[]로 추론 (의도하지 않은 경우)

// 명시적 타입 지정 필요
let items: number[] = [];  // number[]로 명확히 지정

// 함수 매개변수는 추론되지 않음
function process(data) {  // 오류: 'data' 매개변수에 타입이 없습니다
    return data.length;
}

// 명시적 타입 지정 필요
function process(data: string) {
    return data.length;
}
```

**최적 공통 타입 (Best Common Type)**:
```typescript
// 여러 타입이 섞여 있을 때 유니온 타입으로 추론
let values = [1, "hello", true];
// (string | number | boolean)[]로 추론

// 명시적 타입 지정으로 더 구체적인 타입 지정 가능
let values: (string | number)[] = [1, "hello"];  // boolean 제외
```

**문맥적 타입 (Contextual Typing)**:
```typescript
// 이벤트 핸들러에서 문맥적 타입 추론
window.onclick = function(event) {
    // event는 MouseEvent로 추론됨
    console.log(event.clientX, event.clientY);
};

// 배열 메서드에서 문맥적 타입 추론
const numbers = [1, 2, 3, 4, 5];
numbers.map(function(n) {
    // n은 number로 추론됨
    return n * 2;
});
```

#### 1.4 타입 단언 (Type Assertion) vs 타입 가드 (Type Guard)

**타입 단언 (Type Assertion)**:
타입 단언은 개발자가 TypeScript에게 "이 값은 특정 타입이다"라고 알려주는 방법입니다. 런타임에는 아무 영향이 없으며, 컴파일 타임에만 사용됩니다.

```typescript
// as 문법 사용
let someValue: unknown = "this is a string";
let strLength: number = (someValue as string).length;

// angle-bracket 문법 사용 (JSX에서는 사용 불가)
let strLength2: number = (<string>someValue).length;

// 실제 사용 예시
interface ApiResponse {
    data: unknown;
}

function processResponse(response: ApiResponse) {
    // data가 실제로 User 객체라고 확신할 때
    const user = response.data as { id: number; name: string };
    console.log(user.id, user.name);
}
```

**`as` 는 검증이 아니라 검사 포기 선언이다.** 위 `processResponse` 가 정확히 그 모양이다. 실제로 돌려 보면 이렇게 된다.

```typescript
interface User { id: number; name: string; roles: string[] }

const raw = '{"id":1}';                  // name 도 roles 도 없는 응답
const user = JSON.parse(raw) as User;    // 컴파일 오류 0건

user.name;                // 타입은 string, 값은 undefined
user.name.toUpperCase();  // TypeError: Cannot read properties of undefined
```

컴파일러는 `raw` 안에 뭐가 들었는지 볼 방법이 없다. `as User` 는 "확인했으니 믿어라"가 아니라 **"확인하지 않을 테니 따지지 마라"** 에 가깝다. 그래서 단언이 많은 코드는 타입이 있는데도 런타임 오류가 나고, 오류가 나는 자리는 단언한 곳이 아니라 **한참 뒤에 그 값을 쓰는 곳**이다.

`as` 로도 못 넘는 벽이 하나 있는데, 그걸 넘는 관용구가 더 위험하다.

```typescript
const n = '1' as number;              // error TS2352: 충분히 겹치지 않는 타입
const n2 = '1' as unknown as number;  // 통과

n2 + 1;      // 타입은 number, 실행하면 '11' (문자열 이어붙이기)
typeof n2;   // 'string'
```

`as unknown as X` 는 컴파일러가 "이건 아무리 봐도 아니다"라고 막은 것을 강제로 뚫는 문법이다. 테스트 목킹처럼 정당한 쓰임이 있긴 하지만, **애플리케이션 코드에 있으면 대개 타입 설계가 잘못됐다는 신호**다. 코드베이스에서 이 패턴을 grep 해 보는 것만으로 위험 지점 목록이 나온다.

들어오는 값을 정말 믿고 싶으면 단언 대신 검사를 쓴다. 아래 타입 가드가 그 방법이다.

**타입 가드 (Type Guard)**:
타입 가드는 런타임에 타입을 검사하여 TypeScript의 타입 좁히기(Type Narrowing)를 수행합니다.

```typescript
// typeof 타입 가드
function isString(value: unknown): value is string {
    return typeof value === 'string';
}

function process(value: unknown) {
    if (isString(value)) {
        // 이 블록에서 value는 string 타입
        console.log(value.toUpperCase());
    }
}

// instanceof 타입 가드
class User {
    constructor(public name: string) {}
}

class Admin {
    constructor(public name: string, public role: string) {}
}

function isUser(obj: User | Admin): obj is User {
    return obj instanceof User;
}

function greet(person: User | Admin) {
    if (isUser(person)) {
        // person은 User 타입
        console.log(`Hello, ${person.name}`);
    } else {
        // person은 Admin 타입
        console.log(`Hello, Admin ${person.name}`);
    }
}

// in 연산자 타입 가드
interface Dog {
    type: 'dog';
    bark: () => void;
}

interface Cat {
    type: 'cat';
    meow: () => void;
}

function makeSound(animal: Dog | Cat) {
    if ('bark' in animal) {
        // animal은 Dog 타입
        animal.bark();
    } else {
        // animal은 Cat 타입
        animal.meow();
    }
}

// 커스텀 타입 가드 함수
interface Fish {
    swim: () => void;
}

interface Bird {
    fly: () => void;
}

function isFish(pet: Fish | Bird): pet is Fish {
    return (pet as Fish).swim !== undefined;
}

function move(pet: Fish | Bird) {
    if (isFish(pet)) {
        pet.swim();  // Fish 타입으로 좁혀짐
    } else {
        pet.fly();   // Bird 타입으로 좁혀짐
    }
}
```

**타입 단언 vs 타입 가드 비교**:

| 특징 | 타입 단언 | 타입 가드 |
|------|----------|----------|
| **실행 시점** | 컴파일 타임만 | 런타임 검사 포함 |
| **안전성** | 개발자 책임 (위험) | 타입 검사로 안전 |
| **사용 시기** | 타입을 확실히 알 때 | 타입을 확인해야 할 때 |
| **권장 여부** | 최소한으로 사용 | 가능한 많이 사용 |

**다만 "타입 가드니까 안전"은 절반만 맞다.** `pet is Fish` 라는 반환 타입은 컴파일러에게 좁혀 달라고 부탁하는 것이지, 함수 본문이 실제로 검사한다는 보장이 아니다. 아래는 오류 없이 컴파일된다.

```typescript
function isUser(o: unknown): o is User { return true; }

const anything: unknown = 42;
if (isUser(anything)) {
  anything.roles;   // 타입은 string[], 값은 undefined
}
```

**`is` 를 쓰는 순간 그 함수 본문이 새로운 신뢰 경계가 된다.** 컴파일러는 본문을 검증하지 않으므로 여기가 틀리면 그 뒤 모든 좁히기가 틀린다. 위 `isFish` 의 `(pet as Fish).swim !== undefined` 도 같은 부류다 — 단언으로 프로퍼티를 들여다보고 그 결과로 다시 단언을 만들어 낸다. 대상이 `Fish | Bird` 로 이미 좁혀진 자리에서는 괜찮지만, `unknown` 을 받는 자리에서 이 형태를 쓰면 `null` 하나에 무너진다.

경계에서 쓸 가드는 이 정도까지는 확인해야 한다.

```typescript
function isUser(o: unknown): o is User {
  return typeof o === 'object' && o !== null
    && typeof (o as Record<string, unknown>).id === 'number'
    && typeof (o as Record<string, unknown>).name === 'string';
}
```

필드가 늘수록 이 코드는 길어지고, 타입 정의와 가드가 따로 놀기 시작한다(필드를 추가했는데 가드를 안 고치면 조용히 통과한다). 그래서 실무에서는 **스키마를 한 번 정의하고 타입과 검증기를 함께 얻는** 도구(zod 같은 것)를 쓴다. 판단 기준은 단순하다.

| 상황 | 방법 |
|---|---|
| 이미 좁혀진 유니온을 더 좁힐 때 | `typeof` · `instanceof` · `in` · 판별 필드 |
| 내가 만든 값의 모양을 확인할 때 | 직접 쓴 `is` 가드 |
| 외부에서 들어온 값(HTTP·파일·환경변수) | 스키마 검증기. 타입과 검사를 한 곳에서 |
| "확실히 안다"고 느낄 때 | 그 근거를 주석이 아니라 코드로 남긴다 |

또 하나, 위 `isUser` 예제는 클래스라 `instanceof` 가 통하지만 **인터페이스는 런타임에 없다.** `obj instanceof User` 에서 `User` 가 인터페이스면 컴파일 자체가 안 된다. 클래스와 인터페이스가 이 지점에서 갈린다.

**구조적 타이핑의 빈틈도 함께 봐야 한다.** 타입스크립트는 이름이 아니라 모양으로 판단하므로, 별칭을 나눠도 서로 대입된다.

```typescript
type UserId = string;
type OrderId = string;

function findUser(id: UserId) { /* ... */ }

const oid: OrderId = 'order-1';
findUser(oid);   // 오류 없음
```

ID 를 뒤바꿔 넘기는 사고를 타입으로 막고 싶으면 모양을 실제로 다르게 만들어야 한다. 흔한 방법이 브랜드 타입이다.

```typescript
type UserId = string & { readonly __brand: 'UserId' };
type OrderId = string & { readonly __brand: 'OrderId' };

findUser(oid);   // error TS2345: Type 'OrderId' is not assignable to parameter of type 'UserId'
```

`__brand` 는 런타임에 존재하지 않는 가짜 필드다. 값을 만들 때 단언이 한 번 필요해지는 대신, 그 뒤로는 컴파일러가 두 ID 를 구분한다. **타입 이름을 나누는 것과 타입을 나누는 것은 다르다**는 점이 요점이다.

```typescript
// 나쁜 예: 타입 단언 남용
function badExample(data: unknown) {
    const user = data as User;  // 위험: 실제로 User가 아닐 수 있음
    console.log(user.name);     // 런타임 에러 가능
}

// 좋은 예: 타입 가드 사용
function goodExample(data: unknown) {
    if (isUser(data)) {  // 타입 검사
        console.log(data.name);  // 안전함
    } else {
        console.error('Invalid user data');
    }
}
```

#### 1.5 인터페이스 vs 타입 별칭 상세 비교

**인터페이스 (Interface)**:
인터페이스는 객체의 구조를 정의하는 TypeScript의 주요 방법입니다. 선언 병합(Declaration Merging)이 가능합니다.

```typescript
// 기본 인터페이스 정의
interface User {
    id: number;
    name: string;
    email: string;
}

// 선언 병합 (Declaration Merging)
interface User {
    age?: number;  // 기존 인터페이스에 속성 추가
}

// 결과: User는 id, name, email, age를 모두 가짐

// 인터페이스 확장
interface Admin extends User {
    role: 'admin';
    permissions: string[];
}

// 다중 확장
interface SuperAdmin extends User, Admin {
    level: number;
}
```

**타입 별칭 (Type Alias)**:
타입 별칭은 타입에 이름을 부여하는 방법입니다. 인터페이스보다 더 유연하며, 유니온, 교집합, 튜플 등 다양한 타입을 표현할 수 있습니다.

```typescript
// 기본 타입 별칭
type UserId = number;
type UserName = string;

// 객체 타입 별칭
type User = {
    id: number;
    name: string;
    email: string;
};

// 유니온 타입
type Status = 'pending' | 'approved' | 'rejected';

// 교집합 타입
type Admin = User & {
    role: 'admin';
    permissions: string[];
};

// 튜플 타입
type Point = [number, number];
type RGB = [number, number, number];

// 함수 타입
type MathOperation = (a: number, b: number) => number;

// 조건부 타입
type NonNullable<T> = T extends null | undefined ? never : T;
```

**인터페이스 vs 타입 별칭 비교**:

| 특징 | 인터페이스 | 타입 별칭 |
|------|-----------|----------|
| **선언 병합** | 가능 | 불가능 |
| **확장** | extends 키워드 | & 연산자 |
| **유니온 타입** | 불가능 | 가능 |
| **튜플** | 가능하나 제한적 | 완전 지원 |
| **조건부 타입** | 불가능 | 가능 |
| **성능** | 약간 빠름 | 약간 느림 |
| **가독성** | 객체 구조에 적합 | 복잡한 타입에 적합 |

**사용 시나리오**:

1. **인터페이스가 적합한 경우**:
```typescript
// 객체 구조 정의
interface Config {
    apiUrl: string;
    timeout: number;
}

// 클래스 구현
interface Drawable {
    draw(): void;
}

class Circle implements Drawable {
    draw() {
        console.log('Drawing circle');
    }
}

// 선언 병합이 필요한 경우
interface Window {
    myCustomProperty: string;
}
```

2. **타입 별칭이 적합한 경우**:
```typescript
// 유니온 타입
type Status = 'loading' | 'success' | 'error';

// 복잡한 타입 조합
type ApiResponse<T> = 
    | { status: 'success'; data: T }
    | { status: 'error'; message: string };

// 함수 타입
type EventHandler<T> = (event: T) => void;

// 유틸리티 타입과 조합
type PartialUser = Partial<User>;
type ReadonlyConfig = Readonly<Config>;
```

**실전 권장사항**:
- 객체 구조 정의: 인터페이스 사용
- 유니온, 교집합, 조건부 타입: 타입 별칭 사용
- 클래스 구현: 인터페이스 사용
- 재사용 가능한 타입 유틸리티: 타입 별칭 사용

#### 1.6 함수 타입 선언의 고급 패턴

**함수 오버로드 (Function Overloads)**:
동일한 함수 이름으로 여러 시그니처를 정의할 수 있습니다.

```typescript
// 오버로드 시그니처
function process(value: string): string;
function process(value: number): number;
function process(value: boolean): boolean;

// 구현 시그니처
function process(value: string | number | boolean): string | number | boolean {
    if (typeof value === 'string') {
        return value.toUpperCase();
    } else if (typeof value === 'number') {
        return value * 2;
    } else {
        return !value;
    }
}

// 사용 예시
const str = process('hello');    // string
const num = process(42);         // number
const bool = process(true);      // boolean
```

**제네릭 함수**:
```typescript
// 기본 제네릭 함수
function identity<T>(arg: T): T {
    return arg;
}

// 제네릭 제약 조건
interface Lengthwise {
    length: number;
}

function logLength<T extends Lengthwise>(arg: T): T {
    console.log(arg.length);
    return arg;
}

// 다중 타입 매개변수
function pair<K, V>(key: K, value: V): [K, V] {
    return [key, value];
}

// 제네릭 함수 타입 별칭
type Transformer<T, U> = (input: T) => U;

const stringToNumber: Transformer<string, number> = (str) => 
    parseInt(str, 10);
```

**고급 함수 패턴**:
```typescript
// 조건부 반환 타입
function processValue<T>(value: T): T extends string ? string[] : T {
    if (typeof value === 'string') {
        return value.split('') as any;
    }
    return value as any;
}

// 나머지 매개변수와 튜플 타입
function callWithArgs<T extends any[], R>(
    fn: (...args: T) => R,
    ...args: T
): R {
    return fn(...args);
}

// 함수 타입 추출
type FunctionType = typeof Math.max;
// (value1: number, value2: number, ...values: number[]) => number
```

#### 1.7 클래스와 인터페이스의 관계

**implements 키워드**:
클래스가 인터페이스를 구현한다는 것을 명시합니다.

```typescript
// 인터페이스 정의
interface Flyable {
    fly(): void;
    maxAltitude: number;
}

interface Swimmable {
    swim(): void;
    maxDepth: number;
}

// 단일 인터페이스 구현
class Bird implements Flyable {
    maxAltitude: number = 10000;
    
    fly() {
        console.log('Flying at high altitude');
    }
}

// 다중 인터페이스 구현
class Duck implements Flyable, Swimmable {
    maxAltitude: number = 1000;
    maxDepth: number = 5;
    
    fly() {
        console.log('Duck is flying');
    }
    
    swim() {
        console.log('Duck is swimming');
    }
}

// 추상 클래스와 인터페이스 조합
abstract class Animal {
    abstract makeSound(): void;
}

interface Pet {
    name: string;
    play(): void;
}

class Dog extends Animal implements Pet {
    name: string;
    
    constructor(name: string) {
        super();
        this.name = name;
    }
    
    makeSound() {
        console.log('Woof!');
    }
    
    play() {
        console.log(`${this.name} is playing`);
    }
}
```

**인터페이스 확장 vs 클래스 상속**:
```typescript
// 인터페이스 확장 (구조만 정의)
interface Base {
    id: number;
}

interface Extended extends Base {
    name: string;
}

// 클래스 상속 (구현 포함)
class BaseClass {
    id: number;
    
    constructor(id: number) {
        this.id = id;
    }
}

class ExtendedClass extends BaseClass {
    name: string;
    
    constructor(id: number, name: string) {
        super(id);
        this.name = name;
    }
}
```

#### 1.8 모듈 시스템 (Import/Export)

**기본 Export/Import**:
```typescript
// math.ts
export function add(a: number, b: number): number {
    return a + b;
}

export function subtract(a: number, b: number): number {
    return a - b;
}

// 사용
import { add, subtract } from './math';

// 또는
import * as Math from './math';
Math.add(1, 2);
```

**Default Export**:
```typescript
// Calculator.ts
export default class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}

// 사용
import Calculator from './Calculator';
// 또는
import Calc from './Calculator';  // 이름 변경 가능
```

**Named Export와 Default Export 혼용**:
```typescript
// utils.ts
export function formatDate(date: Date): string {
    return date.toISOString();
}

export default function formatCurrency(amount: number): string {
    return `$${amount.toFixed(2)}`;
}

// 사용
import formatCurrency, { formatDate } from './utils';
```

**타입 Export/Import**:
```typescript
// types.ts
export interface User {
    id: number;
    name: string;
}

export type Status = 'active' | 'inactive';

// 사용
import type { User, Status } from './types';
// 또는
import { type User, type Status } from './types';
```

**Re-export (재내보내기)**:
```typescript
// index.ts
export { User, Status } from './types';
export { Calculator } from './Calculator';
export { default as formatCurrency } from './utils';
```

#### 1.9 네임스페이스와 모듈의 차이점

**네임스페이스 (Namespace)**:
네임스페이스는 관련된 코드를 논리적으로 그룹화하는 방법입니다. 전역 스코프에 추가됩니다.

```typescript
// 네임스페이스 정의
namespace MathUtils {
    export function add(a: number, b: number): number {
        return a + b;
    }
    
    export function multiply(a: number, b: number): number {
        return a * b;
    }
    
    // 중첩 네임스페이스
    export namespace Geometry {
        export function area(radius: number): number {
            return Math.PI * radius * radius;
        }
    }
}

// 사용
MathUtils.add(1, 2);
MathUtils.Geometry.area(5);

// 네임스페이스 병합
namespace MathUtils {
    export function subtract(a: number, b: number): number {
        return a - b;
    }
}
```

**모듈 (Module)**:
모듈은 파일 기반의 코드 조직화 방법입니다. 각 파일이 자체 스코프를 가지며, 명시적으로 export/import해야 합니다.

```typescript
// math.ts (모듈)
export function add(a: number, b: number): number {
    return a + b;
}

// 사용
import { add } from './math';
```

**네임스페이스 vs 모듈 비교**:

| 특징 | 네임스페이스 | 모듈 |
|------|------------|------|
| **스코프** | 전역 | 파일별 독립 |
| **파일 구조** | 여러 파일에 분산 가능 | 파일 단위 |
| **의존성 관리** | 수동 | 자동 (번들러) |
| **트리 쉐이킹** | 어려움 | 쉬움 |
| **권장 여부** | 레거시 코드 | 현대적 프로젝트 |

**현대적 권장사항**:
- **모듈 사용 권장**: 대부분의 경우 모듈을 사용하는 것이 좋습니다
- **네임스페이스 사용 시기**: 
  - 타입 정의 파일(.d.ts)에서 전역 타입 정의
  - 레거시 코드와의 호환성
  - 복잡한 타입 선언 병합

```typescript
// 모듈 방식 (권장)
// math.ts
export function add(a: number, b: number): number {
    return a + b;
}

// app.ts
import { add } from './math';

// 네임스페이스 방식 (특수한 경우만)
// types.d.ts
declare namespace NodeJS {
    interface ProcessEnv {
        NODE_ENV: 'development' | 'production';
    }
}
```

### 2. 개발 환경 설정

#### 2.1 TypeScript 설치

##### 전역 설치 (개발 도구용)
```bash
# TypeScript 컴파일러 전역 설치
npm install -g typescript

# 버전 확인
tsc --version

# TypeScript 컴파일러 업데이트
npm update -g typescript
```

##### 프로젝트별 설치 (권장)
```bash
# 개발 의존성으로 설치
npm install --save-dev typescript

# 타입 정의 파일 설치 (Node.js 환경)
npm install --save-dev @types/node

# React 프로젝트의 경우
npm install --save-dev @types/react @types/react-dom

# Express 프로젝트의 경우
npm install --save-dev @types/express
```

#### 2.2 프로젝트 초기화

##### 기본 프로젝트 설정
```bash
# 1. 프로젝트 디렉토리 생성
mkdir my-typescript-project
cd my-typescript-project

# 2. package.json 초기화
npm init -y

# 3. TypeScript 및 관련 패키지 설치
npm install --save-dev typescript @types/node ts-node nodemon

# 4. TypeScript 설정 파일 생성
npx tsc --init

# 5. 프로젝트 구조 생성
mkdir src
mkdir dist
```

##### 프로젝트 구조
```
my-typescript-project/
├── src/                    # TypeScript 소스 코드
│   ├── index.ts
│   ├── types/
│   ├── utils/
│   └── services/
├── dist/                   # 컴파일된 JavaScript 코드
├── node_modules/
├── package.json
├── tsconfig.json          # TypeScript 설정
└── README.md
```

#### 2.3 TypeScript 설정 (tsconfig.json)

##### 기본 설정
```json
{
  "compilerOptions": {
    // 컴파일 대상 JavaScript 버전
    "target": "ES2022",
    
    // 모듈 시스템
    "module": "CommonJS",
    
    // 사용할 라이브러리
    "lib": ["ES2022", "DOM"],
    
    // 출력 디렉토리
    "outDir": "./dist",
    
    // 소스 디렉토리
    "rootDir": "./src",
    
    // 엄격한 타입 검사 활성화
    "strict": true,
    
    // ES 모듈 상호 운용성
    "esModuleInterop": true,
    
    // 라이브러리 타입 검사 건너뛰기
    "skipLibCheck": true,
    
    // 파일명 대소문자 일관성 강제
    "forceConsistentCasingInFileNames": true,
    
    // 선언 파일 생성
    "declaration": true,
    
    // 소스맵 생성
    "sourceMap": true,
    
    // 증분 컴파일
    "incremental": true,
    
    // 빌드 정보 파일 위치
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo"
  },
  
  // 컴파일할 파일/디렉토리
  "include": [
    "src/**/*"
  ],
  
  // 제외할 파일/디렉토리
  "exclude": [
    "node_modules",
    "dist",
    "tests",
    "**/*.test.ts"
  ]
}
```

##### 고급 설정 옵션
```json
{
  "compilerOptions": {
    // 기본 설정...
    
    // 타입 검사 옵션
    "noImplicitAny": true,           // 암시적 any 타입 금지
    "noImplicitReturns": true,       // 함수의 모든 경로에서 반환값 요구
    "noImplicitThis": true,          // 암시적 this 타입 금지
    "noUnusedLocals": true,          // 사용하지 않는 지역 변수 오류
    "noUnusedParameters": true,      // 사용하지 않는 매개변수 오류
    "exactOptionalPropertyTypes": true, // 선택적 프로퍼티 타입 정확성
    
    // 모듈 해석 옵션
    "moduleResolution": "node",      // 모듈 해석 전략
    "baseUrl": "./src",              // 모듈 해석 기본 경로
    "paths": {                       // 경로 매핑
      "@/*": ["*"],
      "@/types/*": ["types/*"],
      "@/utils/*": ["utils/*"]
    },
    
    // 출력 옵션
    "removeComments": false,         // 주석 제거 여부
    "preserveConstEnums": true,      // const enum 보존
    "declarationMap": true,          // 선언 파일 소스맵 생성
    
    // 실험적 기능
    "experimentalDecorators": true,  // 데코레이터 지원
    "emitDecoratorMetadata": true    // 데코레이터 메타데이터 생성
  }
}
```

#### 2.4 개발 도구 설정

##### package.json 스크립트
```json
{
  "scripts": {
    "build": "tsc",
    "build:watch": "tsc --watch",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "dev:watch": "nodemon --exec ts-node src/index.ts",
    "clean": "rimraf dist",
    "type-check": "tsc --noEmit",
    "lint": "eslint src/**/*.ts",
    "test": "jest"
  }
}
```

##### VS Code 설정 (.vscode/settings.json)
```json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true,
  "typescript.updateImportsOnFileMove.enabled": "always",
  "editor.codeActionsOnSave": {
    "source.organizeImports": true,
    "source.fixAll.eslint": true
  },
  "files.associations": {
    "*.ts": "typescript",
    "*.tsx": "typescriptreact"
  }
}
```

### 3. 기본 개발 워크플로우

#### TypeScript 코드 작성
```typescript
// src/app.ts
interface Calculator {
    add(a: number, b: number): number;
    subtract(a: number, b: number): number;
    multiply(a: number, b: number): number;
    divide(a: number, b: number): number;
}

class SimpleCalculator implements Calculator {
    add(a: number, b: number): number {
        return a + b;
    }

    subtract(a: number, b: number): number {
        return a - b;
    }

    multiply(a: number, b: number): number {
        return a * b;
    }

    divide(a: number, b: number): number {
        if (b === 0) {
            throw new Error("0으로 나눌 수 없습니다.");
        }
        return a / b;
    }
}

// 사용 예시
const calc = new SimpleCalculator();
console.log(calc.add(10, 5));      // 15
console.log(calc.subtract(10, 5)); // 5
console.log(calc.multiply(10, 5)); // 50
console.log(calc.divide(10, 5));   // 2
```

#### 컴파일 및 실행
```bash
# TypeScript 컴파일
npx tsc src/app.ts

# 또는 전체 프로젝트 컴파일
npx tsc

# 컴파일된 JavaScript 실행
node dist/app.js
```

## 예시

### 1. 실제 사용 사례

#### 1.1 사용자 관리 시스템

실제 프로덕션 환경에서 사용할 수 있는 완전한 사용자 관리 시스템을 구현해보겠습니다.
```typescript
// src/types/user.ts
export interface User {
    id: number;
    name: string;
    email: string;
    age: number;
    isActive: boolean;
    createdAt: Date;
}

export interface CreateUserRequest {
    name: string;
    email: string;
    age: number;
}

export interface UpdateUserRequest {
    name?: string;
    email?: string;
    age?: number;
    isActive?: boolean;
}

// src/services/userService.ts
import { User, CreateUserRequest, UpdateUserRequest } from '../types/user';

export class UserService {
    private users: User[] = [];
    private nextId: number = 1;

    createUser(userData: CreateUserRequest): User {
        const user: User = {
            id: this.nextId++,
            name: userData.name,
            email: userData.email,
            age: userData.age,
            isActive: true,
            createdAt: new Date()
        };

        this.users.push(user);
        return user;
    }

    getUser(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }

    getAllUsers(): User[] {
        return [...this.users];
    }

    updateUser(id: number, updates: UpdateUserRequest): User | undefined {
        const userIndex = this.users.findIndex(user => user.id === id);
        
        if (userIndex === -1) {
            return undefined;
        }

        this.users[userIndex] = {
            ...this.users[userIndex],
            ...updates
        };

        return this.users[userIndex];
    }

    deleteUser(id: number): boolean {
        const userIndex = this.users.findIndex(user => user.id === id);
        
        if (userIndex === -1) {
            return false;
        }

        this.users.splice(userIndex, 1);
        return true;
    }

    searchUsers(query: string): User[] {
        const lowerQuery = query.toLowerCase();
        return this.users.filter(user => 
            user.name.toLowerCase().includes(lowerQuery) ||
            user.email.toLowerCase().includes(lowerQuery)
        );
    }
}

// src/index.ts
import { UserService } from './services/userService';

const userService = new UserService();

// 사용자 생성
const user1 = userService.createUser({
    name: "홍길동",
    email: "hong@example.com",
    age: 30
});

const user2 = userService.createUser({
    name: "김철수",
    email: "kim@example.com",
    age: 25
});

console.log("생성된 사용자:", user1);
console.log("생성된 사용자:", user2);

// 사용자 조회
const foundUser = userService.getUser(1);
console.log("조회된 사용자:", foundUser);

// 사용자 업데이트
const updatedUser = userService.updateUser(1, { age: 31 });
console.log("업데이트된 사용자:", updatedUser);

// 사용자 검색
const searchResults = userService.searchUsers("홍");
console.log("검색 결과:", searchResults);

// 모든 사용자 조회
const allUsers = userService.getAllUsers();
console.log("모든 사용자:", allUsers);
```

### 2. 고급 패턴

#### 2.1 제네릭 (Generics)

제네릭을 사용하여 타입 안전성을 유지하면서 재사용 가능한 코드를 작성할 수 있습니다.

##### 기본 제네릭
```typescript
// 제네릭 함수
function identity<T>(arg: T): T {
    return arg;
}

const stringResult = identity<string>("hello");     // string
const numberResult = identity<number>(42);          // number
const autoResult = identity("world");               // 타입 추론: string

// 제네릭 인터페이스
interface Container<T> {
    value: T;
    getValue(): T;
    setValue(value: T): void;
}

class Box<T> implements Container<T> {
    constructor(public value: T) {}
    
    getValue(): T {
        return this.value;
    }
    
    setValue(value: T): void {
        this.value = value;
    }
}

// 사용 예시
const stringBox = new Box<string>("Hello");
const numberBox = new Box<number>(42);
```

##### 제네릭 제약 조건
```typescript
// 타입 제약 조건
interface Lengthwise {
    length: number;
}

function logLength<T extends Lengthwise>(arg: T): T {
    console.log(arg.length);
    return arg;
}

logLength("hello");        // OK: string has length
logLength([1, 2, 3]);     // OK: array has length
// logLength(42);         // Error: number doesn't have length

// 키 제약 조건
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
    return obj[key];
}

const person = { name: "홍길동", age: 30, city: "서울" };
const name = getProperty(person, "name");    // string
const age = getProperty(person, "age");      // number
// const invalid = getProperty(person, "invalid"); // Error
```

#### 2.2 제네릭을 사용한 데이터 처리
```typescript
// src/utils/dataProcessor.ts
export interface DataProcessor<T> {
    process(data: T[]): T[];
    filter(predicate: (item: T) => boolean): T[];
    map<U>(transformer: (item: T) => U): U[];
}

export class ArrayProcessor<T> implements DataProcessor<T> {
    private data: T[];

    constructor(data: T[] = []) {
        this.data = data;
    }

    add(item: T): void {
        this.data.push(item);
    }

    process(data: T[]): T[] {
        this.data = [...this.data, ...data];
        return this.data;
    }

    filter(predicate: (item: T) => boolean): T[] {
        return this.data.filter(predicate);
    }

    map<U>(transformer: (item: T) => U): U[] {
        return this.data.map(transformer);
    }

    reduce<U>(reducer: (accumulator: U, item: T) => U, initialValue: U): U {
        return this.data.reduce(reducer, initialValue);
    }

    getData(): T[] {
        return [...this.data];
    }
}

// 사용 예시
const numberProcessor = new ArrayProcessor<number>([1, 2, 3, 4, 5]);

// 필터링
const evenNumbers = numberProcessor.filter(n => n % 2 === 0);
console.log("짝수:", evenNumbers); // [2, 4]

// 매핑
const doubledNumbers = numberProcessor.map(n => n * 2);
console.log("2배:", doubledNumbers); // [2, 4, 6, 8, 10]

// 리듀싱
const sum = numberProcessor.reduce((acc, n) => acc + n, 0);
console.log("합계:", sum); // 15

// 문자열 처리
const stringProcessor = new ArrayProcessor<string>(["apple", "banana", "cherry"]);
const upperCaseFruits = stringProcessor.map(fruit => fruit.toUpperCase());
console.log("대문자:", upperCaseFruits); // ["APPLE", "BANANA", "CHERRY"]
```

#### 2.3 고급 타입 패턴

##### 조건부 타입 (Conditional Types)
```typescript
// 기본 조건부 타입
type IsString<T> = T extends string ? true : false;

type Test1 = IsString<string>;  // true
type Test2 = IsString<number>;  // false

// 유틸리티 타입 구현
type NonNullable<T> = T extends null | undefined ? never : T;
type ReturnType<T> = T extends (...args: any[]) => infer R ? R : any;

// 분배 조건부 타입
type ToArray<T> = T extends any ? T[] : never;
type StringOrNumberArray = ToArray<string | number>; // string[] | number[]

// 템플릿 리터럴 타입
type EventName<T extends string> = `on${Capitalize<T>}`;
type MouseEvent = EventName<'click'>; // 'onClick'
type KeyboardEvent = EventName<'keydown'>; // 'onKeydown'
```

##### 매핑된 타입 (Mapped Types)
```typescript
// 기본 매핑된 타입
type Partial<T> = {
    [P in keyof T]?: T[P];
};

type Required<T> = {
    [P in keyof T]-?: T[P];
};

type Readonly<T> = {
    readonly [P in keyof T]: T[P];
};

// 조건부 매핑
type PickByType<T, U> = {
    [K in keyof T as T[K] extends U ? K : never]: T[K];
};

interface User {
    id: number;
    name: string;
    age: number;
    email: string;
    isActive: boolean;
}

type StringProps = PickByType<User, string>; // { name: string; email: string; }
type NumberProps = PickByType<User, number>; // { id: number; age: number; }
```

##### 템플릿 리터럴 타입과 패턴 매칭
```typescript
// API 엔드포인트 타입 생성
type ApiEndpoint = 
    | 'users'
    | 'posts'
    | 'comments'
    | 'categories';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

type ApiUrl<T extends ApiEndpoint, M extends HttpMethod> = 
    M extends 'GET' ? `/api/${T}` :
    M extends 'POST' ? `/api/${T}` :
    M extends 'PUT' ? `/api/${T}/${string}` :
    M extends 'DELETE' ? `/api/${T}/${string}` :
    never;

type GetUsersUrl = ApiUrl<'users', 'GET'>;        // '/api/users'
type PostUserUrl = ApiUrl<'users', 'POST'>;       // '/api/users'
type PutUserUrl = ApiUrl<'users', 'PUT'>;         // '/api/users/${string}'
type DeleteUserUrl = ApiUrl<'users', 'DELETE'>;   // '/api/users/${string}'
```

#### 2.4 비동기 처리와 타입 안전성
```typescript
// src/services/apiService.ts
export interface ApiResponse<T> {
    data: T;
    success: boolean;
    message: string;
    timestamp: Date;
}

export interface ApiError {
    code: number;
    message: string;
    details?: string;
}

export class ApiService {
    private baseUrl: string;

    constructor(baseUrl: string = 'https://api.example.com') {
        this.baseUrl = baseUrl;
    }

    async get<T>(endpoint: string): Promise<ApiResponse<T>> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            return {
                data,
                success: true,
                message: '요청이 성공적으로 처리되었습니다.',
                timestamp: new Date()
            };
        } catch (error) {
            throw {
                code: 500,
                message: 'API 요청 중 오류가 발생했습니다.',
                details: error instanceof Error ? error.message : '알 수 없는 오류'
            } as ApiError;
        }
    }

    async post<T, U>(endpoint: string, data: T): Promise<ApiResponse<U>> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const responseData = await response.json();

            return {
                data: responseData,
                success: true,
                message: '데이터가 성공적으로 전송되었습니다.',
                timestamp: new Date()
            };
        } catch (error) {
            throw {
                code: 500,
                message: 'API 요청 중 오류가 발생했습니다.',
                details: error instanceof Error ? error.message : '알 수 없는 오류'
            } as ApiError;
        }
    }
}

// 사용 예시
interface User {
    id: number;
    name: string;
    email: string;
}

const apiService = new ApiService('https://jsonplaceholder.typicode.com');

// GET 요청
apiService.get<User>('/users/1')
    .then(response => {
        console.log('사용자 정보:', response.data);
    })
    .catch(error => {
        console.error('오류:', error.message);
    });

// POST 요청
const newUser = {
    name: '홍길동',
    email: 'hong@example.com'
};

apiService.post<typeof newUser, User>('/users', newUser)
    .then(response => {
        console.log('생성된 사용자:', response.data);
    })
    .catch(error => {
        console.error('오류:', error.message);
    });
```

## 운영 팁

### 1. 성능 최적화

#### 1.1 컴파일 최적화

TypeScript 컴파일 성능을 향상시키기 위한 다양한 최적화 기법을 알아보겠습니다.

##### 증분 컴파일 설정
```json
// tsconfig.json - 성능 최적화 설정
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    
    // 성능 최적화 옵션
    "incremental": true,                    // 증분 컴파일 활성화
    "tsBuildInfoFile": "./.tsbuildinfo",   // 빌드 정보 파일 위치
    "composite": true,                      // 프로젝트 참조 활성화
    "declaration": true,                    // .d.ts 파일 생성
    "declarationMap": true,                 // 선언 파일 소스맵
    "sourceMap": true,                      // 소스맵 생성
    
    // 타입 검사 최적화
    "skipLibCheck": true,                   // 라이브러리 타입 검사 건너뛰기
    "assumeChangesOnlyAffectDirectDependencies": true
  },
  
  // 프로젝트 참조 설정 (대규모 프로젝트용)
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/ui" },
    { "path": "./packages/utils" }
  ],
  
  "include": ["src/**/*"],
  "exclude": [
    "node_modules",
    "dist",
    "tests",
    "**/*.test.ts",
    "**/*.spec.ts"
  ]
}
```

##### 프로젝트 참조 (Project References)
```json
// packages/core/tsconfig.json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"]
}

// packages/ui/tsconfig.json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "outDir": "./dist"
  },
  "references": [
    { "path": "../core" }
  ],
  "include": ["src/**/*"]
}
```

#### 1.2 개발 환경 최적화
```json
// tsconfig.json - 성능 최적화 설정
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "sourceMap": true,
    "removeComments": false,
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/.tsbuildinfo"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

#### 개발 환경 최적화
```json
// package.json - 개발 스크립트 최적화
{
  "scripts": {
    "build": "tsc",
    "build:watch": "tsc --watch",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "dev:watch": "ts-node --watch src/index.ts",
    "clean": "rimraf dist",
    "type-check": "tsc --noEmit"
  }
}
```

### 2. 에러 처리

#### 2.1 타입 안전한 에러 처리

TypeScript에서 에러를 안전하고 체계적으로 처리하는 방법을 알아보겠습니다.

##### Result 패턴 구현
```typescript
// Result 타입 정의
type Result<T, E = Error> = Success<T> | Failure<E>;

interface Success<T> {
    success: true;
    data: T;
}

interface Failure<E> {
    success: false;
    error: E;
}

// Result 유틸리티 함수들
function success<T>(data: T): Success<T> {
    return { success: true, data };
}

function failure<E>(error: E): Failure<E> {
    return { success: false, error };
}

// Result를 사용한 안전한 함수
function divide(a: number, b: number): Result<number, string> {
    if (b === 0) {
        return failure("0으로 나눌 수 없습니다.");
    }
    return success(a / b);
}

// Result 사용 예시
const result = divide(10, 2);
if (result.success) {
    console.log("결과:", result.data); // number
} else {
    console.error("오류:", result.error); // string
}
```

##### 커스텀 에러 클래스
```typescript
// 기본 에러 클래스
export abstract class AppError extends Error {
    abstract readonly code: string;
    abstract readonly statusCode: number;
    
    constructor(
        message: string,
        public readonly details?: any
    ) {
        super(message);
        this.name = this.constructor.name;
        Error.captureStackTrace(this, this.constructor);
    }
}

// 구체적인 에러 클래스들
export class ValidationError extends AppError {
    readonly code = 'VALIDATION_ERROR';
    readonly statusCode = 400;
    
    constructor(message: string, details?: any) {
        super(message, details);
    }
}

export class NotFoundError extends AppError {
    readonly code = 'NOT_FOUND';
    readonly statusCode = 404;
    
    constructor(resource: string, id: string | number) {
        super(`${resource} with id ${id} not found`, { resource, id });
    }
}

export class UnauthorizedError extends AppError {
    readonly code = 'UNAUTHORIZED';
    readonly statusCode = 401;
    
    constructor(message: string = '인증이 필요합니다.') {
        super(message);
    }
}

export class InternalServerError extends AppError {
    readonly code = 'INTERNAL_SERVER_ERROR';
    readonly statusCode = 500;
    
    constructor(message: string = '내부 서버 오류가 발생했습니다.', details?: any) {
        super(message, details);
    }
}
```

##### 에러 핸들러 유틸리티
```typescript
// 에러 타입 가드
export function isAppError(error: unknown): error is AppError {
    return error instanceof AppError;
}

// 에러 처리 함수
export function handleError(error: unknown): AppError {
    if (isAppError(error)) {
        return error;
    }
    
    if (error instanceof Error) {
        return new InternalServerError(error.message, { originalError: error });
    }
    
    return new InternalServerError('알 수 없는 오류가 발생했습니다.', { originalError: error });
}

// 에러 로깅
export function logError(error: AppError, context?: any): void {
    const logData = {
        timestamp: new Date().toISOString(),
        code: error.code,
        message: error.message,
        statusCode: error.statusCode,
        details: error.details,
        context,
        stack: error.stack
    };
    
    console.error('Application Error:', JSON.stringify(logData, null, 2));
}

// 사용 예시
function processUserData(userData: any): Result<User, AppError> {
    try {
        // 유효성 검사
        if (!userData.name) {
            return failure(new ValidationError('이름은 필수입니다.'));
        }
        
        if (!userData.email) {
            return failure(new ValidationError('이메일은 필수입니다.'));
        }
        
        // 사용자 생성 로직
        const user = createUser(userData);
        return success(user);
        
    } catch (error) {
        const appError = handleError(error);
        logError(appError, { userData });
        return failure(appError);
    }
}
```

#### 2.2 타입 안전한 에러 처리
```typescript
// src/utils/errorHandler.ts
export class AppError extends Error {
    constructor(
        message: string,
        public code: number,
        public details?: any
    ) {
        super(message);
        this.name = 'AppError';
    }
}

export function handleError(error: unknown): void {
    if (error instanceof AppError) {
        console.error(`[${error.code}] ${error.name}: ${error.message}`);
        if (error.details) {
            console.error('상세 정보:', error.details);
        }
    } else if (error instanceof Error) {
        console.error(`Error: ${error.message}`);
    } else {
        console.error('알 수 없는 오류:', error);
    }
}

// 사용 예시
function divideNumbers(a: number, b: number): number {
    if (b === 0) {
        throw new AppError('0으로 나눌 수 없습니다.', 400, { a, b });
    }
    return a / b;
}

try {
    const result = divideNumbers(10, 0);
    console.log(result);
} catch (error) {
    handleError(error);
}
```

## 참고

### TypeScript vs JavaScript 비교표

| 구분 | TypeScript | JavaScript |
|------|------------|------------|
| **타입 시스템** | 정적 타입 | 동적 타입 |
| **컴파일** | 필요 (tsc) | 불필요 |
| **오류 감지** | 컴파일 타임 | 런타임 |
| **IDE 지원** | 우수 | 제한적 |
| **학습 곡선** | 높음 | 낮음 |
| **대규모 프로젝트** | 적합 | 부적합 |

### TypeScript 버전별 주요 기능

| 버전 | 주요 기능 |
|------|-----------|
| **4.x** | 가변 튜플 타입, 레이블드 튜플, 클래스 생성자 타입 추론 |
| **5.x** | 데코레이터, const 타입 매개변수, 다중 설정 파일 |

### 결론
TypeScript는 JavaScript의 상위 집합으로 정적 타입 시스템을 제공합니다.
컴파일 타임에 타입 오류를 감지하여 런타임 오류를 방지합니다.
대규모 프로젝트의 유지보수성과 개발자 경험을 향상시킵니다.
기존 JavaScript 코드와 완전 호환되어 점진적 도입이 가능합니다.
적절한 설정과 도구를 활용하여 효율적인 TypeScript 개발을 진행하세요.

## 참조

### 공식 문서 및 리소스
- [TypeScript 공식 웹사이트](https://www.typescriptlang.org/)
- [TypeScript 핸드북](https://www.typescriptlang.org/docs/)
- [TypeScript 컴파일러 옵션](https://www.typescriptlang.org/tsconfig)
- [TypeScript GitHub 저장소](https://github.com/microsoft/TypeScript)

### 학습 자료
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [TypeScript 공식 튜토리얼](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TypeScript Playground](https://www.typescriptlang.org/play)

### 도구 및 라이브러리
- [TypeScript 컴파일러 (tsc)](https://www.typescriptlang.org/docs/handbook/compiler-options.html)
- [ts-node](https://github.com/TypeStrong/ts-node) - TypeScript 실행 환경
- [ESLint TypeScript 플러그인](https://typescript-eslint.io/)
- [Prettier TypeScript 지원](https://prettier.io/docs/en/options.html#parser)

### 타입 정의 파일
- [DefinitelyTyped](https://github.com/DefinitelyTyped/DefinitelyTyped) - TypeScript 타입 정의 저장소
- [@types 패키지](https://www.npmjs.com/search?q=%40types) - npm의 타입 정의 패키지들

### 프레임워크별 TypeScript 가이드
- [React + TypeScript](https://react-typescript-cheatsheet.netlify.app/)
- [Vue.js + TypeScript](https://vuejs.org/guide/typescript/overview.html)
- [Angular + TypeScript](https://angular.io/guide/typescript-configuration)

### 고급 주제
- [TypeScript 유틸리티 타입](https://www.typescriptlang.org/docs/handbook/utility-types.html)
- [TypeScript 제네릭](https://www.typescriptlang.org/docs/handbook/2/generics.html)
- [TypeScript 모듈 시스템](https://www.typescriptlang.org/docs/handbook/modules.html)
- [TypeScript 네임스페이스](https://www.typescriptlang.org/docs/handbook/namespaces.html)

### 성능 및 최적화
- [프로젝트 참조](https://www.typescriptlang.org/docs/handbook/project-references.html)
- [증분 컴파일](https://www.typescriptlang.org/docs/handbook/project-references.html#incremental-builds)

### 커뮤니티 및 지원
- [TypeScript Discord](https://discord.gg/typescript)

### 관련 기술
- [JavaScript (ES6+)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [WebAssembly](https://webassembly.org/) - TypeScript와 함께 사용 가능
- [Deno](https://deno.land/) - TypeScript 네이티브 런타임
- [Bun](https://bun.sh/) - TypeScript 지원 JavaScript 런타임

