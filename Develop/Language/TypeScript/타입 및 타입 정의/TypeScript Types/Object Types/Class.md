---
title: TypeScript Class 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, class]
updated: 2025-12-16
---

# TypeScript Class 가이드

## 배경

TypeScript에서 Class는 특정 속성과 메서드를 가진 객체를 생성하기 위한 청사진입니다.

### Class의 필요성
- **객체지향 프로그래밍**: 상속, 다형성, 캡슐화 등 OOP 개념 지원
- **코드 재사용성**: 동일한 구조의 객체를 여러 번 생성
- **타입 안전성**: 속성과 메서드의 타입을 명시적으로 정의
- **유지보수성**: 구조화된 코드로 유지보수 용이성 향상

### 기본 개념
- **클래스**: 객체를 생성하기 위한 템플릿
- **인스턴스**: 클래스로부터 생성된 객체
- **속성**: 객체가 가지는 데이터
- **메서드**: 객체가 수행할 수 있는 동작

## 핵심

### 1. 기본 클래스 정의

#### 간단한 클래스
```typescript
class Car {
    make: string;
    model: string;
    year: number;

    constructor(make: string, model: string, year: number) {
        this.make = make;
        this.model = model;
        this.year = year;
    }

    drive(): void {
        console.log(`Driving my ${this.year} ${this.make} ${this.model}`);
    }

    getInfo(): string {
        return `${this.year} ${this.make} ${this.model}`;
    }
}

// 사용 예시
const myCar = new Car('Tesla', 'Model 3', 2021);
myCar.drive(); // "Driving my 2021 Tesla Model 3"
console.log(myCar.getInfo()); // "2021 Tesla Model 3"
```

#### 접근 제어자 사용
```typescript
class BankAccount {
    private balance: number;
    public accountNumber: string;
    protected owner: string;

    constructor(accountNumber: string, owner: string, initialBalance: number = 0) {
        this.accountNumber = accountNumber;
        this.owner = owner;
        this.balance = initialBalance;
    }

    public deposit(amount: number): void {
        if (amount > 0) {
            this.balance += amount;
            console.log(`${amount}원이 입금되었습니다.`);
        }
    }

    public withdraw(amount: number): boolean {
        if (amount > 0 && amount <= this.balance) {
            this.balance -= amount;
            console.log(`${amount}원이 출금되었습니다.`);
            return true;
        }
        console.log('잔액이 부족합니다.');
        return false;
    }

    public getBalance(): number {
        return this.balance;
    }
}
```

### 2. 상속과 다형성

#### 클래스 상속
```typescript
class Vehicle {
    protected brand: string;
    protected model: string;

    constructor(brand: string, model: string) {
        this.brand = brand;
        this.model = model;
    }

    start(): void {
        console.log(`${this.brand} ${this.model} 시동을 겁니다.`);
    }

    stop(): void {
        console.log(`${this.brand} ${this.model} 시동을 끕니다.`);
    }
}

class ElectricCar extends Vehicle {
    private batteryLevel: number;

    constructor(brand: string, model: string, batteryLevel: number = 100) {
        super(brand, model);
        this.batteryLevel = batteryLevel;
    }

    charge(): void {
        this.batteryLevel = 100;
        console.log('배터리가 완전히 충전되었습니다.');
    }

    getBatteryLevel(): number {
        return this.batteryLevel;
    }

    start(): void {
        if (this.batteryLevel > 0) {
            super.start();
        } else {
            console.log('배터리가 부족합니다. 충전해주세요.');
        }
    }
}

// 사용 예시
const tesla = new ElectricCar('Tesla', 'Model S', 80);
tesla.start(); // "Tesla Model S 시동을 겁니다."
tesla.charge(); // "배터리가 완전히 충전되었습니다."
```

### 3. 정적 멤버와 추상 클래스

#### 정적 멤버
```typescript
class MathUtils {
    static PI: number = 3.14159;

    static add(a: number, b: number): number {
        return a + b;
    }

    static multiply(a: number, b: number): number {
        return a * b;
    }

    static calculateCircleArea(radius: number): number {
        return this.PI * radius * radius;
    }
}

// 사용 예시
console.log(MathUtils.PI); // 3.14159
console.log(MathUtils.add(5, 3)); // 8
console.log(MathUtils.calculateCircleArea(5)); // 78.53975
```

#### 추상 클래스
```typescript
abstract class Animal {
    protected name: string;

    constructor(name: string) {
        this.name = name;
    }

    abstract makeSound(): void;

    move(): void {
        console.log(`${this.name}이(가) 움직입니다.`);
    }
}

class Dog extends Animal {
    makeSound(): void {
        console.log(`${this.name}: 멍멍!`);
    }
}

class Cat extends Animal {
    makeSound(): void {
        console.log(`${this.name}: 야옹!`);
    }
}

// 사용 예시
const dog = new Dog('멍멍이');
const cat = new Cat('야옹이');

dog.makeSound(); // "멍멍이: 멍멍!"
cat.makeSound(); // "야옹이: 야옹!"
```

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```typescript
abstract class User {
    protected id: number;
    protected name: string;
    protected email: string;
    protected createdAt: Date;

    constructor(id: number, name: string, email: string) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.createdAt = new Date();
    }

    abstract getRole(): string;

    getInfo(): string {
        return `ID: ${this.id}, Name: ${this.name}, Email: ${this.email}`;
    }

    getCreatedAt(): Date {
        return this.createdAt;
    }
}

class AdminUser extends User {
    private permissions: string[];

    constructor(id: number, name: string, email: string, permissions: string[] = []) {
        super(id, name, email);
        this.permissions = permissions;
    }

    getRole(): string {
        return 'Admin';
    }

    addPermission(permission: string): void {
        if (!this.permissions.includes(permission)) {
            this.permissions.push(permission);
        }
    }

    hasPermission(permission: string): boolean {
        return this.permissions.includes(permission);
    }
}

class RegularUser extends User {
    private lastLogin: Date | null = null;

    constructor(id: number, name: string, email: string) {
        super(id, name, email);
    }

    getRole(): string {
        return 'User';
    }

    login(): void {
        this.lastLogin = new Date();
        console.log(`${this.name}이(가) 로그인했습니다.`);
    }

    getLastLogin(): Date | null {
        return this.lastLogin;
    }
}

// 사용 예시
const admin = new AdminUser(1, '관리자', 'admin@example.com', ['read', 'write', 'delete']);
const user = new RegularUser(2, '사용자', 'user@example.com');

console.log(admin.getRole()); // "Admin"
console.log(user.getRole()); // "User"

admin.addPermission('execute');
console.log(admin.hasPermission('execute')); // true

user.login(); // "사용자이(가) 로그인했습니다."
```

### 2. 고급 패턴

#### 싱글톤 패턴
```typescript
class DatabaseConnection {
    private static instance: DatabaseConnection;
    private connectionString: string;

    private constructor(connectionString: string) {
        this.connectionString = connectionString;
    }

    static getInstance(connectionString?: string): DatabaseConnection {
        if (!DatabaseConnection.instance) {
            DatabaseConnection.instance = new DatabaseConnection(connectionString || 'default');
        }
        return DatabaseConnection.instance;
    }

    connect(): void {
        console.log(`데이터베이스에 연결합니다: ${this.connectionString}`);
    }

    disconnect(): void {
        console.log('데이터베이스 연결을 종료합니다.');
    }
}

// 사용 예시
const db1 = DatabaseConnection.getInstance('mysql://localhost:3306');
const db2 = DatabaseConnection.getInstance(); // 같은 인스턴스 반환

console.log(db1 === db2); // true
```

#### 팩토리 패턴
```typescript
abstract class Product {
    abstract getName(): string;
    abstract getPrice(): number;
}

class Book extends Product {
    constructor(private title: string, private author: string, private price: number) {
        super();
    }

    getName(): string {
        return `${this.title} by ${this.author}`;
    }

    getPrice(): number {
        return this.price;
    }
}

class Electronics extends Product {
    constructor(private name: string, private brand: string, private price: number) {
        super();
    }

    getName(): string {
        return `${this.brand} ${this.name}`;
    }

    getPrice(): number {
        return this.price;
    }
}

class ProductFactory {
    static createProduct(type: 'book' | 'electronics', data: any): Product {
        switch (type) {
            case 'book':
                return new Book(data.title, data.author, data.price);
            case 'electronics':
                return new Electronics(data.name, data.brand, data.price);
            default:
                throw new Error('Unknown product type');
        }
    }
}

// 사용 예시
const book = ProductFactory.createProduct('book', {
    title: 'TypeScript Guide',
    author: 'John Doe',
    price: 30000
});

const phone = ProductFactory.createProduct('electronics', {
    name: 'Smartphone',
    brand: 'Samsung',
    price: 800000
});

console.log(book.getName()); // "TypeScript Guide by John Doe"
console.log(phone.getName()); // "Samsung Smartphone"
```

## 운영 팁

### 성능 최적화

#### 메모리 효율성
```typescript
class MemoryEfficientClass {
    // 정적 메서드로 인스턴스 생성 없이 사용
    static processData(data: any[]): any[] {
        return data.map(item => item * 2);
    }

    // 프로토타입 메서드로 메모리 절약
    processItem(item: any): any {
        return item * 2;
    }
}

// 사용 예시
const result = MemoryEfficientClass.processData([1, 2, 3, 4, 5]);
```

### 에러 처리

#### 안전한 클래스 설계
```typescript
class SafeCalculator {
    private validateNumber(num: number): void {
        if (typeof num !== 'number' || isNaN(num)) {
            throw new Error('유효하지 않은 숫자입니다.');
        }
    }

    add(a: number, b: number): number {
        this.validateNumber(a);
        this.validateNumber(b);
        return a + b;
    }

    divide(a: number, b: number): number {
        this.validateNumber(a);
        this.validateNumber(b);
        
        if (b === 0) {
            throw new Error('0으로 나눌 수 없습니다.');
        }
        
        return a / b;
    }
}

// 사용 예시
const calculator = new SafeCalculator();

try {
    console.log(calculator.add(5, 3)); // 8
    console.log(calculator.divide(10, 2)); // 5
    console.log(calculator.divide(10, 0)); // Error: 0으로 나눌 수 없습니다.
} catch (error) {
    console.error(error.message);
}
```

## 참고

### 클래스 vs 인터페이스 비교표

| 특징 | Class | Interface |
|------|-------|-----------|
| **구현** | ✅ 구현 포함 | ❌ 구현 없음 |
| **인스턴스화** | ✅ 가능 | ❌ 불가능 |
| **생성자** | ✅ 지원 | ❌ 지원 안함 |
| **접근 제어자** | ✅ 지원 | ❌ 지원 안함 |
| **상속** | extends | extends |
| **다중 상속** | ❌ 불가능 | ✅ 가능 |

### 클래스 설계 원칙

1. **단일 책임 원칙**: 하나의 클래스는 하나의 책임만 가져야 함
2. **개방-폐쇄 원칙**: 확장에는 열려있고 수정에는 닫혀있어야 함
3. **리스코프 치환 원칙**: 하위 클래스는 상위 클래스를 대체할 수 있어야 함
4. **인터페이스 분리 원칙**: 클라이언트는 사용하지 않는 인터페이스에 의존하지 않아야 함
5. **의존성 역전 원칙**: 추상화에 의존해야 하고 구체화에 의존하지 않아야 함

### 결론
TypeScript의 Class는 객체지향 프로그래밍의 핵심 개념을 구현하는 강력한 도구입니다.
적절한 접근 제어자와 상속을 통해 안전하고 재사용 가능한 코드를 작성할 수 있습니다.
추상 클래스와 인터페이스를 활용하여 유연한 설계를 구현하세요.
싱글톤, 팩토리 등 디자인 패턴을 적용하여 코드의 품질을 향상시키세요.
메모리 효율성과 에러 처리를 고려한 안전한 클래스 설계를 하세요.

