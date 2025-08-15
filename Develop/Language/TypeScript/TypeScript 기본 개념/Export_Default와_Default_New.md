---
title: TypeScript export default와 default new 완벽 가이드
tags: [language, typescript, typescript-기본-개념, export-default, default-new]
updated: 2025-08-10
---

# TypeScript export default와 default new 완벽 가이드

## 배경

TypeScript에서 `export default`는 모듈에서 기본적으로 내보낼 값을 지정할 때 사용됩니다. `default new` 패턴은 클래스의 인스턴스를 바로 내보내는 방식입니다.

### export default의 필요성
- **단일 내보내기**: 모듈에서 하나의 주요 객체, 함수, 클래스를 내보낼 때
- **간편한 import**: 중괄호 없이 임의의 이름으로 가져올 수 있음
- **모듈 설계**: 명확한 모듈 인터페이스 제공
- **코드 가독성**: 모듈의 주요 기능을 명확히 표현

### default new 패턴의 필요성
- **싱글톤 패턴**: 클래스의 단일 인스턴스 제공
- **즉시 사용**: 인스턴스화 없이 바로 사용 가능
- **상태 관리**: 전역 상태나 설정 객체 관리
- **의존성 주입**: 미리 구성된 객체 제공

## 핵심

### 1. export default 기본 사용법

#### 함수 내보내기
```typescript
// math.ts - 함수를 기본 내보내기
export default function add(a: number, b: number): number {
    return a + b;
}

// main.ts - 기본 내보내기 가져오기
import add from './math';
console.log(add(2, 3)); // 5

// 다른 이름으로 가져오기 가능
import myAdd from './math';
console.log(myAdd(5, 3)); // 8
```

#### 클래스 내보내기
```typescript
// Logger.ts - 클래스를 기본 내보내기
export default class Logger {
    log(message: string): void {
        console.log(`[LOG]: ${message}`);
    }
    
    error(message: string): void {
        console.error(`[ERROR]: ${message}`);
    }
}

// main.ts - 클래스 가져오기 및 인스턴스화
import Logger from './Logger';
const logger = new Logger();
logger.log('Hello, TypeScript!'); // [LOG]: Hello, TypeScript!
logger.error('Something went wrong!'); // [ERROR]: Something went wrong!
```

#### 객체 내보내기
```typescript
// config.ts - 객체를 기본 내보내기
export default {
    apiUrl: 'https://api.example.com',
    timeout: 5000,
    retries: 3
};

// main.ts - 설정 객체 가져오기
import config from './config';
console.log(config.apiUrl); // "https://api.example.com"
console.log(config.timeout); // 5000
```

### 2. default new 패턴

#### 기본 default new 패턴
```typescript
// Logger.ts - 클래스 인스턴스를 바로 내보내기
export default new (class Logger {
    log(message: string): void {
        console.log(`[LOG]: ${message}`);
    }
    
    error(message: string): void {
        console.error(`[ERROR]: ${message}`);
    }
})();

// main.ts - 인스턴스화된 객체 가져오기
import logger from './Logger';
logger.log('This is default new!'); // [LOG]: This is default new!
logger.error('Error with default new!'); // [ERROR]: Error with default new!
```

#### 싱글톤 패턴 구현
```typescript
// Database.ts - 싱글톤 데이터베이스 연결
export default new (class Database {
    private connection: string = '';
    
    connect(url: string): void {
        this.connection = url;
        console.log(`데이터베이스 연결: ${url}`);
    }
    
    query(sql: string): string {
        if (!this.connection) {
            throw new Error('데이터베이스가 연결되지 않았습니다.');
        }
        return `실행된 쿼리: ${sql}`;
    }
    
    disconnect(): void {
        this.connection = '';
        console.log('데이터베이스 연결 해제');
    }
})();

// main.ts - 싱글톤 데이터베이스 사용
import db from './Database';

db.connect('mysql://localhost:3306/mydb');
console.log(db.query('SELECT * FROM users')); // "실행된 쿼리: SELECT * FROM users"
db.disconnect();
```

### 3. export default와 named export 혼용

#### 기본 내보내기와 명명된 내보내기 함께 사용
```typescript
// utils.ts - 기본 내보내기와 명명된 내보내기 혼용
export function multiply(a: number, b: number): number {
    return a * b;
}

export function divide(a: number, b: number): number {
    return a / b;
}

export default function add(a: number, b: number): number {
    return a + b;
}

// main.ts - 혼합 가져오기
import add, { multiply, divide } from './utils';

console.log(add(2, 3));      // 5
console.log(multiply(4, 5)); // 20
console.log(divide(10, 2));  // 5
```

## 예시

### 1. 실제 사용 사례

#### HTTP 클라이언트 (기본 클래스 내보내기)
```typescript
// HttpClient.ts
export default class HttpClient {
    private baseUrl: string;
    
    constructor(baseUrl: string = 'https://api.example.com') {
        this.baseUrl = baseUrl;
    }
    
    async get<T>(endpoint: string): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`);
        return response.json();
    }
    
    async post<T>(endpoint: string, data: any): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        return response.json();
    }
}

// main.ts
import HttpClient from './HttpClient';

const client = new HttpClient('https://jsonplaceholder.typicode.com');

// 사용 예시
client.get('/users/1').then(user => {
    console.log('사용자 정보:', user);
});

client.post('/posts', {
    title: '새 게시물',
    body: '게시물 내용',
    userId: 1
}).then(post => {
    console.log('생성된 게시물:', post);
});
```

#### 설정 관리자 (default new 패턴)
```typescript
// ConfigManager.ts
export default new (class ConfigManager {
    private config: Record<string, any> = {};
    
    set(key: string, value: any): void {
        this.config[key] = value;
    }
    
    get<T>(key: string, defaultValue?: T): T | undefined {
        return this.config[key] ?? defaultValue;
    }
    
    has(key: string): boolean {
        return key in this.config;
    }
    
    remove(key: string): void {
        delete this.config[key];
    }
    
    getAll(): Record<string, any> {
        return { ...this.config };
    }
})();

// main.ts
import config from './ConfigManager';

// 설정 값 설정
config.set('apiUrl', 'https://api.example.com');
config.set('timeout', 5000);
config.set('debug', true);

// 설정 값 가져오기
console.log(config.get('apiUrl')); // "https://api.example.com"
console.log(config.get('timeout', 3000)); // 5000
console.log(config.get('unknown', 'default')); // "default"

// 설정 확인
console.log(config.has('debug')); // true
console.log(config.has('unknown')); // false

// 전체 설정 가져오기
console.log(config.getAll()); // { apiUrl: '...', timeout: 5000, debug: true }
```

### 2. 고급 패턴

#### 팩토리 패턴과 default new
```typescript
// UserFactory.ts
interface User {
    id: number;
    name: string;
    email: string;
}

class UserFactory {
    private users: User[] = [];
    private nextId: number = 1;
    
    createUser(name: string, email: string): User {
        const user: User = {
            id: this.nextId++,
            name,
            email
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
    
    deleteUser(id: number): boolean {
        const index = this.users.findIndex(user => user.id === id);
        if (index !== -1) {
            this.users.splice(index, 1);
            return true;
        }
        return false;
    }
}

// 싱글톤 팩토리 인스턴스 내보내기
export default new UserFactory();

// main.ts
import userFactory from './UserFactory';

// 사용자 생성
const user1 = userFactory.createUser('홍길동', 'hong@example.com');
const user2 = userFactory.createUser('김철수', 'kim@example.com');

console.log(user1); // { id: 1, name: '홍길동', email: 'hong@example.com' }
console.log(user2); // { id: 2, name: '김철수', email: 'kim@example.com' }

// 사용자 조회
const foundUser = userFactory.getUser(1);
console.log(foundUser); // { id: 1, name: '홍길동', email: 'hong@example.com' }

// 모든 사용자 조회
console.log(userFactory.getAllUsers()); // [user1, user2]
```

#### 이벤트 시스템 (default new 패턴)
```typescript
// EventEmitter.ts
type EventHandler = (...args: any[]) => void;

class EventEmitter {
    private events: Record<string, EventHandler[]> = {};
    
    on(event: string, handler: EventHandler): void {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(handler);
    }
    
    off(event: string, handler: EventHandler): void {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(h => h !== handler);
        }
    }
    
    emit(event: string, ...args: any[]): void {
        if (this.events[event]) {
            this.events[event].forEach(handler => handler(...args));
        }
    }
    
    once(event: string, handler: EventHandler): void {
        const onceHandler = (...args: any[]) => {
            handler(...args);
            this.off(event, onceHandler);
        };
        this.on(event, onceHandler);
    }
}

// 전역 이벤트 시스템으로 내보내기
export default new EventEmitter();

// main.ts
import eventEmitter from './EventEmitter';

// 이벤트 리스너 등록
eventEmitter.on('userCreated', (user) => {
    console.log('새 사용자가 생성되었습니다:', user);
});

eventEmitter.on('userDeleted', (userId) => {
    console.log('사용자가 삭제되었습니다:', userId);
});

// 한 번만 실행되는 이벤트
eventEmitter.once('appStarted', () => {
    console.log('애플리케이션이 시작되었습니다!');
});

// 이벤트 발생
eventEmitter.emit('appStarted'); // "애플리케이션이 시작되었습니다!"
eventEmitter.emit('appStarted'); // 아무것도 출력되지 않음 (once)

eventEmitter.emit('userCreated', { id: 1, name: '홍길동' });
eventEmitter.emit('userDeleted', 1);
```

## 운영 팁

### 성능 최적화

#### default new 패턴 최적화
```typescript
// LazySingleton.ts - 지연 초기화 싱글톤
class LazySingleton {
    private static instance: LazySingleton | null = null;
    private data: any[] = [];
    
    private constructor() {}
    
    static getInstance(): LazySingleton {
        if (!LazySingleton.instance) {
            LazySingleton.instance = new LazySingleton();
        }
        return LazySingleton.instance;
    }
    
    addData(item: any): void {
        this.data.push(item);
    }
    
    getData(): any[] {
        return [...this.data];
    }
}

// 지연 초기화된 인스턴스 내보내기
export default LazySingleton.getInstance();

// main.ts
import singleton from './LazySingleton';

// 실제 사용할 때만 초기화됨
singleton.addData('item1');
singleton.addData('item2');
console.log(singleton.getData()); // ['item1', 'item2']
```

### 에러 처리

#### 안전한 default new 사용
```typescript
// SafeConfig.ts - 안전한 설정 관리
class SafeConfig {
    private config: Record<string, any> = {};
    private validators: Record<string, (value: any) => boolean> = {};
    
    set(key: string, value: any, validator?: (value: any) => boolean): boolean {
        try {
            if (validator && !validator(value)) {
                console.error(`유효하지 않은 값: ${key} = ${value}`);
                return false;
            }
            
            this.config[key] = value;
            if (validator) {
                this.validators[key] = validator;
            }
            return true;
        } catch (error) {
            console.error(`설정 설정 오류: ${error}`);
            return false;
        }
    }
    
    get<T>(key: string, defaultValue?: T): T | undefined {
        try {
            return this.config[key] ?? defaultValue;
        } catch (error) {
            console.error(`설정 가져오기 오류: ${error}`);
            return defaultValue;
        }
    }
    
    validate(key: string): boolean {
        const validator = this.validators[key];
        const value = this.config[key];
        
        if (!validator) {
            return true; // 검증기가 없으면 유효하다고 간주
        }
        
        return validator(value);
    }
}

// 안전한 설정 인스턴스 내보내기
export default new SafeConfig();

// main.ts
import config from './SafeConfig';

// 유효성 검사와 함께 설정
config.set('port', 3000, (value) => typeof value === 'number' && value > 0);
config.set('host', 'localhost', (value) => typeof value === 'string' && value.length > 0);
config.set('debug', 'invalid', (value) => typeof value === 'boolean'); // 실패

console.log(config.get('port')); // 3000
console.log(config.get('host')); // "localhost"
console.log(config.get('debug')); // undefined

console.log(config.validate('port')); // true
console.log(config.validate('debug')); // false
```

## 참고

### export default vs named export 비교표

| 구분 | export default | named export |
|------|----------------|--------------|
| **가져오기 방식** | `import name from './module'` | `import { name } from './module'` |
| **이름 변경** | 가능 | 불가능 (as 사용 필요) |
| **여러 개 내보내기** | 불가능 | 가능 |
| **트리 쉐이킹** | 제한적 | 완전 지원 |
| **사용 목적** | 주요 기능 하나 | 여러 기능 |

### default new vs 일반 클래스 비교표

| 구분 | default new | 일반 클래스 |
|------|-------------|-------------|
| **인스턴스화** | 자동 | 수동 (`new` 키워드 필요) |
| **싱글톤** | 자동 보장 | 별도 구현 필요 |
| **메모리 사용** | 즉시 할당 | 사용 시 할당 |
| **상태 공유** | 전역 | 인스턴스별 |
| **사용 목적** | 전역 객체, 설정 | 재사용 가능한 클래스 |

### 결론
TypeScript의 export default는 모듈의 주요 기능을 명확하게 표현합니다.
default new 패턴은 싱글톤 객체를 쉽게 구현할 수 있게 해줍니다.
적절한 패턴을 선택하여 모듈의 의도를 명확히 표현하세요.
성능과 메모리 사용을 고려하여 default new 패턴을 사용하세요.
안전한 에러 처리를 통해 런타임 오류를 방지하세요.
export default와 named export를 적절히 조합하여 모듈을 설계하세요.

