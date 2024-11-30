
# TypeScript 주요 문법 및 개념

TypeScript는 JavaScript의 상위 집합 언어로, 정적 타입 시스템과 추가 기능을 통해 코드의 가독성과 안정성을 높입니다. 아래는 TypeScript에서 자주 사용되는 주요 문법과 개념을 예제와 함께 정리한 내용입니다.

---

## 1. **기본 타입 (Basic Types)**

### 기본 타입 종류
- `string`, `number`, `boolean`
- `null`, `undefined`
- `any`, `unknown`
- `void`
- `never`

### 예시
```typescript
let username: string = "John";
let age: number = 25;
let isActive: boolean = true;
let anything: any = "hello"; // 어떤 값도 가능
let notSure: unknown = 42; // 사용 전 검사 필요

function sayHello(): void {
    console.log("Hello, World!");
}

function throwError(): never {
    throw new Error("에러 발생!");
}
```

---

## 2. **인터페이스 (Interface)**

인터페이스는 객체의 구조를 정의합니다.

### 예시
```typescript
interface User {
    id: number;
    name: string;
    email?: string; // 선택적 속성
}

const user: User = {
    id: 1,
    name: "Alice",
};
```

### 함수와 인터페이스
```typescript
interface Login {
    (username: string, password: string): boolean;
}

const login: Login = (username, password) => {
    return username === "admin" && password === "1234";
};
```

---

## 3. **유니온 타입 (Union Type)**

여러 타입 중 하나를 가질 수 있습니다.

### 예시
```typescript
let value: string | number;
value = "hello";
value = 123;

function printValue(input: string | number) {
    if (typeof input === "string") {
        console.log(`문자열: ${input}`);
    } else {
        console.log(`숫자: ${input}`);
    }
}
```

---

## 4. **제네릭 (Generics)**

타입을 매개변수화하여 재사용성을 높입니다.

### 예시
```typescript
function identity<T>(value: T): T {
    return value;
}

let num = identity<number>(42);
let str = identity<string>("TypeScript");
```

### 제네릭 인터페이스
```typescript
interface Box<T> {
    content: T;
}

const box: Box<string> = { content: "Hello" };
```

---

## 5. **타입 별칭 (Type Alias)**

`type` 키워드를 사용해 새로운 타입을 정의합니다.

### 예시
```typescript
type ID = string | number;

let userId: ID = "123";
userId = 456;
```

---

## 6. **리터럴 타입 (Literal Type)**

특정 값만 허용하는 타입입니다.

### 예시
```typescript
type Direction = "up" | "down" | "left" | "right";

function move(direction: Direction) {
    console.log(`Moving ${direction}`);
}

move("up");
```

---

## 7. **타입 가드 (Type Guards)**

런타임에 타입을 좁히기 위한 조건문입니다.

### 예시
```typescript
function isString(value: unknown): value is string {
    return typeof value === "string";
}

function printInput(input: string | number) {
    if (isString(input)) {
        console.log(`문자열: ${input}`);
    } else {
        console.log(`숫자: ${input}`);
    }
}
```

---

## 8. **고급 유틸리티 타입**

### `Readonly`
```typescript
interface User {
    id: number;
    name: string;
}

const readonlyUser: Readonly<User> = {
    id: 1,
    name: "Bob",
};

// readonlyUser.name = "Alice"; // 에러 발생
```

### `Record`
```typescript
type Roles = "admin" | "user";
type Permissions = Record<Roles, string[]>;

const rolePermissions: Permissions = {
    admin: ["read", "write", "delete"],
    user: ["read"],
};
```

### `Omit`
```typescript
interface User {
    id: number;
    name: string;
    email: string;
}

type UserWithoutEmail = Omit<User, "email">;

const user: UserWithoutEmail = {
    id: 1,
    name: "Tom",
};
```

---

## 9. **클래스 (Class)**

### 기본 클래스
```typescript
class Person {
    name: string;
    age: number;

    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }

    greet() {
        console.log(`Hello, my name is ${this.name}.`);
    }
}

const person = new Person("Alice", 30);
person.greet();
```

### 상속과 접근 제한자
```typescript
class Employee extends Person {
    private employeeId: number;

    constructor(name: string, age: number, employeeId: number) {
        super(name, age);
        this.employeeId = employeeId;
    }

    getDetails() {
        console.log(`ID: ${this.employeeId}, Name: ${this.name}`);
    }
}

const employee = new Employee("Bob", 25, 123);
employee.getDetails();
```

---

## 10. **모듈 (Modules)**

TypeScript는 ES6 모듈 시스템을 사용합니다.

### 예시
#### math.ts
```typescript
export function add(a: number, b: number): number {
    return a + b;
}
export const PI = 3.14;
```

#### main.ts
```typescript
import { add, PI } from "./math";

console.log(add(1, 2)); // 3
console.log(PI);       // 3.14
```

---

## 참고 문서
- [TypeScript 공식 문서](https://www.typescriptlang.org/docs/)
- [TypeScript 핸드북](https://www.typescriptlang.org/docs/handbook/intro.html)

