---
title: TypeScript 완벽 가이드
tags: [language, typescript, typescript-기본-개념, javascript-superset]
updated: 2025-08-10
---

# TypeScript

## 배경

TypeScript는 Microsoft에서 개발한 JavaScript의 상위 집합(Superset) 언어입니다. 정적 타입 시스템을 추가하여 JavaScript의 단점을 보완하고 대규모 애플리케이션 개발을 지원합니다.

### TypeScript의 필요성
- **타입 안전성**: 컴파일 타임에 타입 오류 감지
- **개발자 경험**: IDE에서 향상된 자동완성과 오류 검사
- **대규모 프로젝트**: 복잡한 애플리케이션의 유지보수성 향상
- **JavaScript 호환성**: 기존 JavaScript 코드와 완전 호환

### 기본 개념
- **정적 타입 시스템**: 변수, 함수, 객체의 타입을 명시적으로 선언
- **JavaScript 상위 집합**: 모든 유효한 JavaScript 코드는 TypeScript 코드
- **컴파일 타임 검사**: 런타임 오류를 컴파일 타임에 감지
- **점진적 도입**: 기존 JavaScript 프로젝트에 점진적으로 적용 가능

## 핵심

### 1. TypeScript의 주요 특징

#### 정적 타입 지원
```typescript
// 기본 타입 선언
let age: number = 25;
let name: string = "홍길동";
let isStudent: boolean = true;
let hobbies: string[] = ["독서", "운동", "음악"];

// 함수 타입 선언
function greet(name: string): string {
    return `안녕하세요, ${name}님!`;
}

// 객체 타입 선언
interface User {
    id: number;
    name: string;
    email: string;
    age?: number; // 선택적 프로퍼티
}

const user: User = {
    id: 1,
    name: "홍길동",
    email: "hong@example.com"
};

console.log(greet(user.name)); // "안녕하세요, 홍길동님!"
```

#### JavaScript와의 하위 호환성
```typescript
// 기존 JavaScript 코드를 그대로 사용 가능
const existingJsCode = {
    message: "Hello from JavaScript",
    numbers: [1, 2, 3, 4, 5],
    add: function(a: number, b: number) {
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

console.log(mathUtils.add(5, 3)); // 8
console.log(mathUtils.multiply(4, 6)); // 24
```

### 2. 개발 환경 설정

#### TypeScript 설치
```bash
# 전역 설치
npm install -g typescript

# 로컬 설치 (권장)
npm install --save-dev typescript

# 버전 확인
tsc --version
```

#### 프로젝트 초기화
```bash
# TypeScript 프로젝트 초기화
npx tsc --init

# 또는 package.json과 함께 초기화
npm init -y
npm install --save-dev typescript @types/node
npx tsc --init
```

#### 기본 tsconfig.json 설정
```json
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
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
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

#### 사용자 관리 시스템
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

#### 제네릭을 사용한 데이터 처리
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

#### 비동기 처리와 타입 안전성
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

### 성능 최적화

#### 컴파일 최적화
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

### 에러 처리

#### 타입 안전한 에러 처리
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

