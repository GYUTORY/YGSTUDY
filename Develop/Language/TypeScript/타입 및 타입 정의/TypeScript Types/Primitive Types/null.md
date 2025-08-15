---
title: TypeScript null 타입 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, null]
updated: 2025-08-10
---

# TypeScript null 타입 완벽 가이드

## 배경

TypeScript에서 `null`은 값이 없음을 명시적으로 나타내는 특별한 타입입니다.

### null 타입의 필요성
- **명시적 값 부재**: 의도적으로 값이 없음을 나타내는 용도
- **타입 안전성**: null 체크를 통한 런타임 오류 방지
- **API 응답 처리**: 데이터베이스나 외부 API에서 값이 없는 경우 처리
- **선택적 속성**: 객체의 특정 속성이 없을 수 있음을 표현

### 기본 개념
- **null**: 의도적으로 할당되는 "값 없음" 표현
- **undefined**: 선언되었지만 초기화되지 않은 상태
- **strictNullChecks**: null과 undefined의 엄격한 타입 검사

## 핵심

### 1. null 타입 기본 사용법

#### 변수 선언과 초기화
```typescript
// null 타입 명시적 선언
let name: string | null = null;
let age: number | null = null;

// 초기값 설정
name = "홍길동";
age = 25;

// 다시 null로 설정
name = null;
age = null;
```

#### 함수 매개변수와 반환값
```typescript
// null을 허용하는 매개변수
function processName(name: string | null): string {
    if (name === null) {
        return "이름 없음";
    }
    return name.toUpperCase();
}

// null을 반환할 수 있는 함수
function findUser(id: number): User | null {
    const user = users.find(u => u.id === id);
    return user || null;
}
```

### 2. 객체와 인터페이스에서의 null

#### 선택적 속성
```typescript
interface Person {
    id: number;
    name: string;
    email: string | null;  // 이메일이 없을 수 있음
    phone: string | null;  // 전화번호가 없을 수 있음
}

const person: Person = {
    id: 1,
    name: "홍길동",
    email: null,
    phone: "010-1234-5678"
};
```

#### 중첩 객체에서의 null
```typescript
interface Address {
    street: string;
    city: string;
    country: string;
}

interface User {
    id: number;
    name: string;
    address: Address | null;  // 주소 정보가 없을 수 있음
}

const user: User = {
    id: 1,
    name: "김철수",
    address: null
};
```

### 3. null 체크와 타입 가드

#### 기본 null 체크
```typescript
function processValue(value: string | null): string {
    if (value === null) {
        return "값이 없습니다";
    }
    return value.toUpperCase();
}

// 사용 예시
console.log(processValue("hello"));  // "HELLO"
console.log(processValue(null));     // "값이 없습니다"
```

#### 타입 가드 함수
```typescript
function isNotNull<T>(value: T | null): value is T {
    return value !== null;
}

function processArray(values: (string | null)[]): string[] {
    return values.filter(isNotNull);
}

// 사용 예시
const mixedArray = ["hello", null, "world", null, "typescript"];
const result = processArray(mixedArray);
console.log(result); // ["hello", "world", "typescript"]
```

## 예시

### 1. 실제 사용 사례

#### API 응답 처리
```typescript
interface ApiResponse<T> {
    success: boolean;
    data: T | null;
    error: string | null;
}

interface User {
    id: number;
    name: string;
    email: string;
}

async function fetchUser(id: number): Promise<ApiResponse<User>> {
    try {
        const response = await fetch(`/api/users/${id}`);
        const data = await response.json();
        
        if (response.ok) {
            return {
                success: true,
                data: data,
                error: null
            };
        } else {
            return {
                success: false,
                data: null,
                error: data.message || "사용자를 찾을 수 없습니다"
            };
        }
    } catch (error) {
        return {
            success: false,
            data: null,
            error: "네트워크 오류가 발생했습니다"
        };
    }
}

// 사용 예시
fetchUser(1).then(response => {
    if (response.success && response.data) {
        console.log(`사용자: ${response.data.name}`);
    } else {
        console.error(`오류: ${response.error}`);
    }
});
```

#### 데이터베이스 쿼리 결과
```typescript
interface DatabaseResult<T> {
    found: boolean;
    data: T | null;
}

class UserRepository {
    async findById(id: number): Promise<DatabaseResult<User>> {
        // 데이터베이스 쿼리 시뮬레이션
        const user = await this.queryDatabase(id);
        
        if (user) {
            return {
                found: true,
                data: user
            };
        } else {
            return {
                found: false,
                data: null
            };
        }
    }
    
    private async queryDatabase(id: number): Promise<User | null> {
        // 실제 데이터베이스 쿼리 로직
        return null;
    }
}
```

### 2. 고급 패턴

#### Nullish Coalescing 연산자
```typescript
function getDisplayName(name: string | null): string {
    return name ?? "익명 사용자";
}

// 사용 예시
console.log(getDisplayName("홍길동"));  // "홍길동"
console.log(getDisplayName(null));      // "익명 사용자"
```

#### Optional Chaining과 함께 사용
```typescript
interface User {
    id: number;
    profile: {
        name: string;
        avatar: string | null;
    } | null;
}

function getUserAvatar(user: User): string {
    return user.profile?.avatar ?? "default-avatar.jpg";
}

// 사용 예시
const user1: User = {
    id: 1,
    profile: {
        name: "홍길동",
        avatar: "avatar1.jpg"
    }
};

const user2: User = {
    id: 2,
    profile: null
};

console.log(getUserAvatar(user1));  // "avatar1.jpg"
console.log(getUserAvatar(user2));  // "default-avatar.jpg"
```

## 운영 팁

### 성능 최적화

#### null 체크 최적화
```typescript
// 좋지 않은 예: 중복 null 체크
function processUser(user: User | null): string {
    if (user === null) return "사용자 없음";
    if (user.profile === null) return "프로필 없음";
    if (user.profile.name === null) return "이름 없음";
    return user.profile.name;
}

// 좋은 예: early return 패턴
function processUser(user: User | null): string {
    if (!user) return "사용자 없음";
    if (!user.profile) return "프로필 없음";
    if (!user.profile.name) return "이름 없음";
    return user.profile.name;
}
```

### 에러 처리

#### 안전한 null 처리
```typescript
function safeNullCheck<T>(value: T | null, defaultValue: T): T {
    return value !== null ? value : defaultValue;
}

// 사용 예시
const userName = safeNullCheck(user?.name, "익명");
const userAge = safeNullCheck(user?.age, 0);
```

## 참고

### null vs undefined 비교표

| 특징 | null | undefined |
|------|------|-----------|
| **할당 방식** | 의도적으로 할당 | 자동으로 할당 |
| **타입** | null 타입 | undefined 타입 |
| **할당 가능성** | null, any에만 할당 | 모든 타입에 할당 |
| **체크 방법** | `=== null` | `=== undefined` 또는 `typeof` |
| **사용 목적** | 명시적 값 부재 | 초기화되지 않은 상태 |

### strictNullChecks 설정

```json
// tsconfig.json
{
  "compilerOptions": {
    "strictNullChecks": true
  }
}
```

**strictNullChecks 활성화 시**:
- null과 undefined는 다른 타입에 자동 할당되지 않음
- 명시적인 타입 체크가 필요
- 더 안전한 타입 시스템 제공

### 결론
TypeScript의 null 타입은 의도적인 값 부재를 표현하는 중요한 도구입니다.
적절한 null 체크와 타입 가드를 사용하여 런타임 오류를 방지하세요.
null과 undefined의 차이를 이해하고 상황에 맞게 사용하세요.
strictNullChecks 옵션을 활성화하여 더 안전한 타입 시스템을 구축하세요.
Optional Chaining과 Nullish Coalescing 연산자를 활용하여 코드를 간결하게 작성하세요.

