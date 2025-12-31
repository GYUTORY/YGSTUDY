---
title: TypeScript boolean 타입 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, boolean]
updated: 2025-12-31
---

# TypeScript boolean 타입 가이드

## 배경

TypeScript에서 `boolean` 타입은 논리적인 참(true) 또는 거짓(false) 값을 나타내는 기본 데이터 타입입니다.

### boolean 타입의 필요성
- **논리적 표현**: 참/거짓을 명확하게 표현
- **조건문 제어**: 프로그램의 실행 흐름 제어
- **상태 관리**: 애플리케이션의 상태 표현
- **데이터 검증**: 입력값의 유효성 검사

### 기본 개념
- **두 가지 값**: true(참) 또는 false(거짓)
- **논리 연산**: AND(&&), OR(||), NOT(!) 연산 지원
- **타입 안전성**: boolean이 아닌 값의 할당 방지
- **조건 평가**: if문, while문 등에서 조건 평가

## 핵심

### 1. boolean 타입 기본 사용법

#### boolean 변수 선언
```typescript
// 기본 boolean 변수 선언
let isTrue: boolean = true;
let isFalse: boolean = false;

// 타입 추론을 통한 선언
let isLoggedIn = true;  // boolean으로 추론
let hasPermission = false;  // boolean으로 추론

// boolean 타입 체크
function checkBoolean(value: boolean): void {
    console.log(`값: ${value}, 타입: ${typeof value}`);
}

checkBoolean(isTrue);    // "값: true, 타입: boolean"
checkBoolean(isFalse);   // "값: false, 타입: boolean"
```

#### boolean과 조건문
```typescript
// if문에서 boolean 사용
let isLoggedIn: boolean = true;

if (isLoggedIn) {
    console.log('사용자가 로그인되어 있습니다.');
} else {
    console.log('사용자가 로그인되어 있지 않습니다.');
}

// 삼항 연산자에서 boolean 사용
let isAdmin: boolean = false;
let message: string = isAdmin ? '관리자입니다.' : '일반 사용자입니다.';
console.log(message); // "일반 사용자입니다."

// while문에서 boolean 사용
let shouldContinue: boolean = true;
let count: number = 0;

while (shouldContinue) {
    count++;
    console.log(`카운트: ${count}`);
    
    if (count >= 5) {
        shouldContinue = false;
    }
}
```

### 2. boolean과 논리 연산

#### 논리 연산자 사용
```typescript
// AND 연산자 (&&)
let hasPermission: boolean = true;
let isAuthenticated: boolean = true;
let canAccess: boolean = hasPermission && isAuthenticated;

console.log('접근 가능:', canAccess); // true

// OR 연산자 (||)
let isGuest: boolean = false;
let isMember: boolean = true;
let canView: boolean = isGuest || isMember;

console.log('조회 가능:', canView); // true

// NOT 연산자 (!)
let isBlocked: boolean = false;
let isAllowed: boolean = !isBlocked;

console.log('허용됨:', isAllowed); // true

// 복합 논리 연산
let age: number = 25;
let hasLicense: boolean = true;
let isEligible: boolean = age >= 18 && hasLicense;

console.log('운전 자격:', isEligible); // true
```

#### boolean 함수와 메서드
```typescript
// boolean을 반환하는 함수
function isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isStrongPassword(password: string): boolean {
    return password.length >= 8 && 
           /[A-Z]/.test(password) && 
           /[a-z]/.test(password) && 
           /[0-9]/.test(password);
}

// 사용 예시
console.log(isValidEmail('user@example.com')); // true
console.log(isValidEmail('invalid-email'));    // false

console.log(isStrongPassword('StrongPass123')); // true
console.log(isStrongPassword('weak'));          // false
```

### 3. boolean과 타입 변환

#### 다른 타입에서 boolean으로 변환
```typescript
// 문자열에서 boolean 변환
function stringToBoolean(value: string): boolean {
    return value.toLowerCase() === 'true';
}

// 숫자에서 boolean 변환
function numberToBoolean(value: number): boolean {
    return value !== 0;
}

// 객체에서 boolean 변환
function objectToBoolean(value: any): boolean {
    return Boolean(value);
}

// 사용 예시
console.log(stringToBoolean('true'));   // true
console.log(stringToBoolean('false'));  // false
console.log(stringToBoolean('yes'));    // false

console.log(numberToBoolean(1));        // true
console.log(numberToBoolean(0));        // false
console.log(numberToBoolean(-1));       // true

console.log(objectToBoolean({}));       // true
console.log(objectToBoolean(null));     // false
console.log(objectToBoolean(undefined)); // false
```

## 예시

### 1. 실제 사용 사례

#### 사용자 인증 시스템
```typescript
interface User {
    id: number;
    username: string;
    isActive: boolean;
    isAdmin: boolean;
    lastLogin: Date | null;
}

class AuthManager {
    private currentUser: User | null = null;

    login(username: string, password: string): boolean {
        // 실제로는 서버에서 인증 처리
        if (username === 'admin' && password === 'password') {
            this.currentUser = {
                id: 1,
                username: 'admin',
                isActive: true,
                isAdmin: true,
                lastLogin: new Date()
            };
            return true;
        }
        return false;
    }

    logout(): void {
        this.currentUser = null;
    }

    isLoggedIn(): boolean {
        return this.currentUser !== null;
    }

    isAdmin(): boolean {
        return this.currentUser?.isAdmin ?? false;
    }

    canAccessAdminPanel(): boolean {
        return this.isLoggedIn() && this.isAdmin();
    }

    isUserActive(): boolean {
        return this.currentUser?.isActive ?? false;
    }
}

// 사용 예시
const auth = new AuthManager();

console.log(auth.isLoggedIn()); // false

const loginSuccess = auth.login('admin', 'password');
console.log('로그인 성공:', loginSuccess); // true
console.log(auth.isLoggedIn()); // true
console.log(auth.isAdmin()); // true
console.log(auth.canAccessAdminPanel()); // true

auth.logout();
console.log(auth.isLoggedIn()); // false
```

#### 폼 검증 시스템
```typescript
interface FormData {
    username: string;
    email: string;
    password: string;
    confirmPassword: string;
    agreeToTerms: boolean;
}

class FormValidator {
    validateUsername(username: string): boolean {
        return username.length >= 3 && username.length <= 20;
    }

    validateEmail(email: string): boolean {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    validatePassword(password: string): boolean {
        return password.length >= 8 && 
               /[A-Z]/.test(password) && 
               /[a-z]/.test(password) && 
               /[0-9]/.test(password);
    }

    validatePasswordMatch(password: string, confirmPassword: string): boolean {
        return password === confirmPassword;
    }

    validateTermsAgreement(agreeToTerms: boolean): boolean {
        return agreeToTerms === true;
    }

    validateForm(formData: FormData): { isValid: boolean; errors: string[] } {
        const errors: string[] = [];

        if (!this.validateUsername(formData.username)) {
            errors.push('사용자명은 3-20자 사이여야 합니다.');
        }

        if (!this.validateEmail(formData.email)) {
            errors.push('유효한 이메일 주소를 입력하세요.');
        }

        if (!this.validatePassword(formData.password)) {
            errors.push('비밀번호는 8자 이상이며 대소문자와 숫자를 포함해야 합니다.');
        }

        if (!this.validatePasswordMatch(formData.password, formData.confirmPassword)) {
            errors.push('비밀번호가 일치하지 않습니다.');
        }

        if (!this.validateTermsAgreement(formData.agreeToTerms)) {
            errors.push('이용약관에 동의해야 합니다.');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }
}

// 사용 예시
const validator = new FormValidator();
const formData: FormData = {
    username: 'user123',
    email: 'user@example.com',
    password: 'StrongPass123',
    confirmPassword: 'StrongPass123',
    agreeToTerms: true
};

const result = validator.validateForm(formData);
console.log('폼 유효성:', result.isValid); // true
console.log('오류:', result.errors); // []

// 잘못된 데이터
const invalidFormData: FormData = {
    username: 'ab',
    email: 'invalid-email',
    password: 'weak',
    confirmPassword: 'different',
    agreeToTerms: false
};

const invalidResult = validator.validateForm(invalidFormData);
console.log('폼 유효성:', invalidResult.isValid); // false
console.log('오류:', invalidResult.errors); // 여러 오류 메시지
```

### 2. 고급 패턴

#### boolean과 제네릭
```typescript
// 제네릭을 사용한 boolean 처리
class BooleanProcessor<T> {
    private data: T;

    constructor(data: T) {
        this.data = data;
    }

    // 조건에 따른 boolean 반환
    satisfies(condition: (value: T) => boolean): boolean {
        return condition(this.data);
    }

    // 두 값 비교
    equals(other: T): boolean {
        return this.data === other;
    }

    // null/undefined 체크
    isDefined(): boolean {
        return this.data !== null && this.data !== undefined;
    }

    // 타입 체크
    isType<K>(type: string): boolean {
        return typeof this.data === type;
    }
}

// 사용 예시
const stringProcessor = new BooleanProcessor('hello');
const numberProcessor = new BooleanProcessor(42);

console.log(stringProcessor.satisfies(str => str.length > 3)); // true
console.log(stringProcessor.equals('hello')); // true
console.log(stringProcessor.isDefined()); // true
console.log(stringProcessor.isType('string')); // true

console.log(numberProcessor.satisfies(num => num > 40)); // true
console.log(numberProcessor.equals(42)); // true
```

#### boolean과 조건부 타입
```typescript
// boolean을 사용한 조건부 타입
type IsString<T> = T extends string ? true : false;
type IsNumber<T> = T extends number ? true : false;
type IsBoolean<T> = T extends boolean ? true : false;

// 조건부 타입을 사용한 타입 가드
function createTypeGuard<T, K extends keyof T>(
    obj: T,
    key: K,
    expectedType: 'string' | 'number' | 'boolean'
): boolean {
    const value = obj[key];
    
    switch (expectedType) {
        case 'string':
            return typeof value === 'string';
        case 'number':
            return typeof value === 'number';
        case 'boolean':
            return typeof value === 'boolean';
        default:
            return false;
    }
}

// 사용 예시
interface User {
    name: string;
    age: number;
    isActive: boolean;
}

const user: User = {
    name: '홍길동',
    age: 30,
    isActive: true
};

console.log(createTypeGuard(user, 'name', 'string')); // true
console.log(createTypeGuard(user, 'age', 'number')); // true
console.log(createTypeGuard(user, 'isActive', 'boolean')); // true
console.log(createTypeGuard(user, 'name', 'number')); // false
```

## 운영 팁

### 성능 최적화

#### boolean 연산 최적화
```typescript
// 단락 평가를 활용한 최적화
function processUser(user: any): boolean {
    // 단락 평가: 첫 번째 조건이 false면 두 번째 조건을 평가하지 않음
    return user && user.isActive && user.hasPermission;
}

// boolean 캐싱
class BooleanCache {
    private cache = new Map<string, boolean>();

    getCachedBoolean(key: string, computeFn: () => boolean): boolean {
        if (!this.cache.has(key)) {
            this.cache.set(key, computeFn());
        }
        return this.cache.get(key)!;
    }

    clearCache(): void {
        this.cache.clear();
    }
}

// 사용 예시
const cache = new BooleanCache();
const expensiveCheck = () => {
    console.log('비용이 큰 연산 실행');
    return Math.random() > 0.5;
};

console.log(cache.getCachedBoolean('check1', expensiveCheck)); // 연산 실행
console.log(cache.getCachedBoolean('check1', expensiveCheck)); // 캐시된 값 사용
```

### 에러 처리

#### 안전한 boolean 처리
```typescript
// 안전한 boolean 변환
function safeBoolean(value: unknown): boolean {
    if (typeof value === 'boolean') {
        return value;
    }
    
    if (typeof value === 'string') {
        return value.toLowerCase() === 'true';
    }
    
    if (typeof value === 'number') {
        return value !== 0;
    }
    
    return Boolean(value);
}

// boolean 검증
function validateBoolean(value: unknown): { isValid: boolean; value?: boolean } {
    if (typeof value === 'boolean') {
        return { isValid: true, value };
    }
    
    if (typeof value === 'string') {
        const lowerValue = value.toLowerCase();
        if (lowerValue === 'true' || lowerValue === 'false') {
            return { isValid: true, value: lowerValue === 'true' };
        }
    }
    
    return { isValid: false };
}

// 사용 예시
console.log(safeBoolean('true'));   // true
console.log(safeBoolean('false'));  // false
console.log(safeBoolean(1));        // true
console.log(safeBoolean(0));        // false
console.log(safeBoolean({}));       // true

const result1 = validateBoolean('true');
console.log(result1); // { isValid: true, value: true }

const result2 = validateBoolean('invalid');
console.log(result2); // { isValid: false }
```

## 참고

### boolean 타입 특성

| 특성 | 설명 |
|------|------|
| **값의 범위** | true 또는 false만 가능 |
| **논리 연산** | AND(&&), OR(||), NOT(!) 지원 |
| **타입 안전성** | boolean이 아닌 값 할당 방지 |
| **조건 평가** | if문, while문 등에서 사용 |

### boolean vs 다른 타입 비교표

| 타입 | 값의 범위 | 사용 목적 |
|------|-----------|-----------|
| **boolean** | true/false | 논리적 참/거짓 |
| **number** | 숫자 | 수치 계산 |
| **string** | 문자열 | 텍스트 처리 |
| **object** | 객체 | 복잡한 데이터 |

### 결론
TypeScript의 boolean 타입은 논리적 참/거짓을 표현하는 기본 타입입니다.
조건문과 논리 연산에서 프로그램의 실행 흐름을 제어합니다.
타입 안전성을 보장하여 boolean이 아닌 값의 할당을 방지합니다.
논리 연산자를 활용하여 복잡한 조건을 효율적으로 처리하세요.
boolean 함수와 메서드를 통해 코드의 가독성과 재사용성을 향상시키세요.
안전한 boolean 변환과 검증을 통해 런타임 오류를 방지하세요.

