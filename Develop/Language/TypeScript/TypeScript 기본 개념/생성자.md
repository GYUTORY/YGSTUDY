
# TypeScript에서 생성자(constructor)

TypeScript의 생성자는 클래스에서 객체를 생성할 때 호출되는 특별한 메서드입니다. 생성자를 사용하면 객체 초기화, 기본값 설정, 의존성 주입 등을 간편하게 처리할 수 있습니다.

---

## 👉🏻 생성자의 기본 개념

- 생성자는 `constructor` 키워드를 사용해 정의합니다.
- 생성자는 클래스 내에서 단 하나만 정의할 수 있습니다.
- 클래스의 인스턴스를 생성할 때 호출됩니다.

### 기본 생성자 예제

```typescript
class Person {
    name: string; // 이름을 저장하는 속성

    constructor(name: string) { // 생성자 정의
        this.name = name; // 인스턴스 속성 초기화
    }

    greet(): void {
        console.log(`Hello, my name is ${this.name}`);
    }
}

const john = new Person('John Doe'); // Person 클래스의 인스턴스 생성
john.greet(); // Hello, my name is John Doe
```

#### 주석으로 설명:
- `constructor`는 객체를 초기화하는 역할을 합니다.
- `this.name = name;`은 전달받은 매개변수를 인스턴스 속성에 할당합니다.
- 생성자를 통해 인스턴스마다 다른 값을 가질 수 있습니다.

---

## ✨ 생성자 오버로드

TypeScript는 JavaScript와 달리 생성자 오버로드를 지원합니다. 단, 오버로드를 구현할 때는 명시적으로 타입과 매개변수를 설정해야 합니다.

### 생성자 오버로드 예제

```typescript
class Person {
    name: string;
    age: number;

    constructor(name: string); // 매개변수가 하나인 생성자 시그니처
    constructor(name: string, age: number); // 매개변수가 두 개인 생성자 시그니처
    constructor(name: string, age?: number) { // 실제 구현체
        this.name = name;
        this.age = age ?? 0; // age가 제공되지 않으면 기본값 0을 사용
    }

    describe(): void {
        console.log(`${this.name} is ${this.age} years old.`);
    }
}

const alice = new Person('Alice'); // 하나의 매개변수 사용
const bob = new Person('Bob', 30); // 두 개의 매개변수 사용

alice.describe(); // Alice is 0 years old.
bob.describe(); // Bob is 30 years old.
```

#### 주석으로 설명:
- 여러 생성자 시그니처를 정의할 수 있습니다.
- `age`는 선택적 매개변수(`?`)로 정의되어 값을 제공하지 않을 수도 있습니다.
- `age ?? 0`은 `age`가 `undefined`일 때 기본값 `0`을 설정합니다.

---

## 🛠️ 생성자 매개변수와 접근 제한자

생성자 매개변수에 접근 제한자(`public`, `private`, `protected`, `readonly`)를 추가하면, 자동으로 클래스 속성이 생성되고 초기화됩니다.

### 접근 제한자 사용 예제

```typescript
class Car {
    constructor(public brand: string, private model: string, readonly year: number) { // 매개변수에 접근 제한자 설정
        // 매개변수에서 직접 속성이 생성되고 초기화됨
    }

    getDetails(): string {
        return `${this.brand} ${this.model} (${this.year})`;
    }
}

const car = new Car('Toyota', 'Corolla', 2021); // Car 인스턴스 생성
console.log(car.brand); // Toyota
console.log(car.getDetails()); // Toyota Corolla (2021)
// console.log(car.model); // 오류: 'model'은 private 속성이므로 접근할 수 없음
// car.year = 2022; // 오류: 'year'는 readonly 속성이므로 수정할 수 없음
```

#### 주석으로 설명:
- `public`: 클래스 외부에서 접근 가능.
- `private`: 클래스 내부에서만 접근 가능.
- `readonly`: 읽기 전용으로 설정되어 값 수정 불가.

---

## 📊 생성자에서 기본값 설정

생성자 매개변수에 기본값을 지정할 수 있습니다.

### 기본값 설정 예제

```typescript
class Product {
    name: string;
    price: number;

    constructor(name: string, price: number = 100) { // price의 기본값은 100
        this.name = name;
        this.price = price;
    }

    display(): void {
        console.log(`${this.name}: $${this.price}`);
    }
}

const item1 = new Product('Laptop'); // 기본값 사용
const item2 = new Product('Phone', 799); // 기본값 덮어쓰기

item1.display(); // Laptop: $100
item2.display(); // Phone: $799
```

#### 주석으로 설명:
- `price`에 기본값 `100`이 지정되어 값이 제공되지 않으면 이를 사용합니다.
- 기본값은 매개변수의 타입과 일치해야 합니다.

---

## 🗂️ 추상 클래스와 생성자

추상 클래스는 직접 인스턴스를 생성할 수 없으며, 파생 클래스에서 구현해야 할 메서드를 정의합니다.

### 추상 클래스 예제

```typescript
abstract class Shape {
    constructor(public color: string) { // 공통 속성 초기화
    }

    abstract getArea(): number; // 구현은 파생 클래스에서 수행
}

class Circle extends Shape {
    constructor(color: string, private radius: number) {
        super(color); // 부모 클래스의 생성자 호출
    }

    getArea(): number {
        return Math.PI * this.radius ** 2;
    }
}

const circle = new Circle('red', 10);
console.log(circle.color); // red
console.log(circle.getArea()); // 314.159...
```

#### 주석으로 설명:
- 추상 클래스는 `abstract` 키워드로 선언됩니다.
- 추상 클래스의 생성자는 파생 클래스에서 `super()`를 통해 호출해야 합니다.

---

## 🌟 생성자와 의존성 주입

의존성 주입은 클래스 생성 시 필요한 객체나 값을 생성자를 통해 전달받는 패턴입니다.

### 의존성 주입 예제

```typescript
class Database {
    connect(): void {
        console.log('Database connected!');
    }
}

class UserService {
    constructor(private database: Database) {} // 의존성 주입

    initialize(): void {
        this.database.connect(); // 주입받은 데이터베이스 객체 사용
    }
}

const db = new Database();
const userService = new UserService(db); // Database 객체를 주입
userService.initialize(); // Database connected!
```

#### 주석으로 설명:
- 생성자를 통해 외부 객체를 전달받아 유연성을 제공합니다.
- 의존성 주입은 테스트 가능성과 코드 재사용성을 높이는 데 유용합니다.

---

## 📋 생성자 요약

1. 생성자는 클래스의 객체를 초기화하는 특별한 메서드입니다.
2. TypeScript는 생성자 오버로드, 기본값, 접근 제한자를 지원합니다.
3. 추상 클래스와 의존성 주입 등 다양한 패턴에 생성자를 활용할 수 있습니다.

