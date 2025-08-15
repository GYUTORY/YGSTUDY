---
title: TypeScript Interface 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, interface]
updated: 2025-08-10
---

# TypeScript Interface 완벽 가이드

## 배경

TypeScript에서 Interface는 객체의 타입을 정의하는 역할을 합니다.

### Interface의 필요성
- **타입 안전성**: 객체의 구조를 명시적으로 정의하여 타입 오류 방지
- **코드 가독성**: 객체의 구조를 명확하게 문서화
- **재사용성**: 동일한 구조를 여러 곳에서 재사용
- **유지보수성**: 인터페이스 변경 시 관련 코드 자동 업데이트

### 기본 개념
- **Interface**: 객체의 구조를 정의하는 TypeScript 기능
- **구현**: 클래스가 인터페이스를 구현하여 구조를 따름
- **확장**: 인터페이스 간 상속을 통한 구조 확장

## 핵심

### 1. 기본 Interface 정의

#### 간단한 Interface
```typescript
interface Person {
    name: string;
    age: number;
}

// 사용 예시
const person: Person = {
    name: "홍길동",
    age: 25
};
```

#### 선택적 속성과 읽기 전용 속성
```typescript
interface User {
    id: number;
    name: string;
    email: string;
    age?: number;           // 선택적 속성
    readonly createdAt: Date; // 읽기 전용 속성
}

// 사용 예시
const user: User = {
    id: 1,
    name: "김철수",
    email: "kim@example.com",
    createdAt: new Date()
};

// user.createdAt = new Date(); // 오류: 읽기 전용 속성
```

### 2. Interface와 클래스

#### 클래스에서 Interface 구현
```typescript
interface Vehicle {
    brand: string;
    model: string;
    start(): void;
    stop(): void;
}

class Car implements Vehicle {
    constructor(
        public brand: string,
        public model: string
    ) {}

    start(): void {
        console.log(`${this.brand} ${this.model} 시동을 겁니다.`);
    }

    stop(): void {
        console.log(`${this.brand} ${this.model} 시동을 끕니다.`);
    }
}

// 사용 예시
const myCar = new Car("현대", "아반떼");
myCar.start(); // "현대 아반떼 시동을 겁니다."
```

#### 다중 Interface 구현
```typescript
interface Flyable {
    fly(): void;
}

interface Swimmable {
    swim(): void;
}

class Duck implements Flyable, Swimmable {
    fly(): void {
        console.log("오리가 날아갑니다.");
    }

    swim(): void {
        console.log("오리가 수영합니다.");
    }
}
```

### 3. Interface 확장

#### Interface 상속
```typescript
interface Animal {
    name: string;
    age: number;
}

interface Dog extends Animal {
    breed: string;
    bark(): void;
}

// 사용 예시
const myDog: Dog = {
    name: "멍멍이",
    age: 3,
    breed: "진돗개",
    bark(): void {
        console.log("멍멍!");
    }
};
```

#### 다중 Interface 확장
```typescript
interface Printable {
    print(): void;
}

interface Scannable {
    scan(): void;
}

interface Faxable {
    fax(): void;
}

interface AllInOnePrinter extends Printable, Scannable, Faxable {
    copy(): void;
}
```

## 예시

### 1. 실제 사용 사례

#### API 응답 Interface
```typescript
interface ApiResponse<T> {
    success: boolean;
    data: T;
    message: string;
    timestamp: Date;
}

interface User {
    id: number;
    name: string;
    email: string;
    profile: {
        avatar: string;
        bio: string;
    };
}

// 사용 예시
async function fetchUser(id: number): Promise<ApiResponse<User>> {
    const response = await fetch(`/api/users/${id}`);
    const data = await response.json();
    
    return {
        success: true,
        data: data,
        message: "사용자 정보를 성공적으로 가져왔습니다.",
        timestamp: new Date()
    };
}
```

#### 이벤트 시스템 Interface
```typescript
interface EventHandler<T = any> {
    (event: T): void;
}

interface EventEmitter {
    on<T>(event: string, handler: EventHandler<T>): void;
    off(event: string, handler: EventHandler): void;
    emit<T>(event: string, data: T): void;
}

class MyEventEmitter implements EventEmitter {
    private events: Map<string, EventHandler[]> = new Map();

    on<T>(event: string, handler: EventHandler<T>): void {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        this.events.get(event)!.push(handler);
    }

    off(event: string, handler: EventHandler): void {
        const handlers = this.events.get(event);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    emit<T>(event: string, data: T): void {
        const handlers = this.events.get(event);
        if (handlers) {
            handlers.forEach(handler => handler(data));
        }
    }
}
```

### 2. 고급 패턴

#### 제네릭 Interface
```typescript
interface Repository<T> {
    findById(id: number): Promise<T | null>;
    findAll(): Promise<T[]>;
    create(data: Omit<T, 'id'>): Promise<T>;
    update(id: number, data: Partial<T>): Promise<T>;
    delete(id: number): Promise<boolean>;
}

interface User {
    id: number;
    name: string;
    email: string;
}

class UserRepository implements Repository<User> {
    async findById(id: number): Promise<User | null> {
        // 데이터베이스 쿼리 로직
        return null;
    }

    async findAll(): Promise<User[]> {
        // 데이터베이스 쿼리 로직
        return [];
    }

    async create(data: Omit<User, 'id'>): Promise<User> {
        // 데이터베이스 생성 로직
        return { id: 1, ...data };
    }

    async update(id: number, data: Partial<User>): Promise<User> {
        // 데이터베이스 업데이트 로직
        return { id, name: "", email: "", ...data };
    }

    async delete(id: number): Promise<boolean> {
        // 데이터베이스 삭제 로직
        return true;
    }
}
```

#### 조건부 Interface
```typescript
interface BaseConfig {
    name: string;
    version: string;
}

interface DevelopmentConfig extends BaseConfig {
    debug: true;
    logLevel: 'debug' | 'info' | 'warn' | 'error';
}

interface ProductionConfig extends BaseConfig {
    debug: false;
    logLevel: 'warn' | 'error';
}

type Config = DevelopmentConfig | ProductionConfig;

function createConfig(env: 'development' | 'production'): Config {
    if (env === 'development') {
        return {
            name: 'MyApp',
            version: '1.0.0',
            debug: true,
            logLevel: 'debug'
        };
    } else {
        return {
            name: 'MyApp',
            version: '1.0.0',
            debug: false,
            logLevel: 'warn'
        };
    }
}
```

## 운영 팁

### 성능 최적화

#### Interface 분리 원칙
```typescript
// 좋지 않은 예: 하나의 큰 Interface
interface User {
    id: number;
    name: string;
    email: string;
    password: string;
    profile: UserProfile;
    settings: UserSettings;
    // ... 많은 속성들
}

// 좋은 예: 작은 Interface들로 분리
interface UserBasic {
    id: number;
    name: string;
    email: string;
}

interface UserAuth {
    password: string;
    salt: string;
}

interface User extends UserBasic {
    auth: UserAuth;
    profile: UserProfile;
    settings: UserSettings;
}
```

### 에러 처리

#### Interface 검증
```typescript
function isValidUser(user: any): user is User {
    return (
        typeof user === 'object' &&
        user !== null &&
        typeof user.id === 'number' &&
        typeof user.name === 'string' &&
        typeof user.email === 'string'
    );
}

function processUser(user: any): User {
    if (!isValidUser(user)) {
        throw new Error('유효하지 않은 사용자 데이터입니다.');
    }
    return user;
}
```

## 참고

### Interface vs Type Alias 비교표

| 특징 | Interface | Type Alias |
|------|-----------|------------|
| **확장** | extends 키워드로 확장 | & 연산자로 교집합 |
| **선언 병합** | ✅ 가능 | ❌ 불가능 |
| **제네릭** | ✅ 지원 | ✅ 지원 |
| **유니온/교집합** | ❌ 직접 지원 안함 | ✅ 지원 |
| **기본 용도** | 객체 구조 정의 | 모든 타입 정의 |

### Interface 사용 권장사항

1. **명확한 네이밍**: Interface 이름은 명확하고 의미있게 작성
2. **단일 책임**: 하나의 Interface는 하나의 목적만 담당
3. **문서화**: 복잡한 Interface는 JSDoc으로 문서화
4. **확장성 고려**: 미래 확장을 고려한 설계

### 결론
TypeScript Interface는 객체의 구조를 정의하는 강력한 도구입니다.
적절한 Interface 설계로 타입 안전성과 코드 가독성을 향상시키세요.
Interface 분리 원칙을 적용하여 유지보수성을 높이세요.
제네릭과 조건부 타입을 활용하여 재사용 가능한 Interface를 만드세요.
Interface와 Type Alias의 차이를 이해하고 상황에 맞게 사용하세요.

