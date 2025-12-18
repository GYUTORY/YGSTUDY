---
title: TypeScript 타입 단언 가이드
tags: [language, typescript, 타입-및-타입-정의, type-assertion]
updated: 2025-12-18
---

# TypeScript 타입 단언 가이드

## 배경

TypeScript에서 타입 단언(Type Assertion)은 개발자가 특정 값의 타입을 컴파일러에게 "알려주는" 방식으로 사용됩니다.

### 타입 단언의 필요성
- **타입 추론 한계 극복**: 컴파일러가 타입을 제대로 추론하지 못할 때
- **DOM 조작**: HTML 요소의 구체적인 타입 지정
- **API 응답 처리**: 외부 데이터의 타입 명시
- **레거시 코드 통합**: 기존 JavaScript 코드와의 호환성

### 기본 문법
타입 단언은 두 가지 형태로 작성할 수 있습니다:

```typescript
// as 키워드 사용 (권장)
let someValue: unknown = "Hello, TypeScript";
let strLength: number = (someValue as string).length;

// 꺾쇠 괄호 사용 (React JSX와 충돌 가능성)
let someValue2: unknown = "Hello, TypeScript";
let strLength2: number = (<string>someValue2).length;
```

## 핵심

### 1. 컴파일러 타입 추론 한계 극복

#### unknown 타입 처리
```typescript
let someValue: unknown = "Hello, TypeScript";

// 컴파일러가 someValue를 문자열로 간주하지 않음
// console.log(someValue.length); // 오류 발생

// 타입 단언으로 해결
let strLength: number = (someValue as string).length;
console.log(strLength); // 17
```

#### any 타입 처리
```typescript
let apiData: any = { id: 1, name: "홍길동", age: 25 };

// 타입 단언으로 인터페이스 적용
interface User {
    id: number;
    name: string;
    age: number;
}

let user = apiData as User;
console.log(user.name); // 홍길동
```

### 2. DOM 요소 타입 지정

#### HTML 요소 타입 단언
```typescript
// 기본적으로 HTMLElement | null 타입 반환
let inputElement = document.getElementById("myInput") as HTMLInputElement;

// 구체적인 타입으로 단언
inputElement.value = "Hello!";
inputElement.focus();
```

#### 다양한 DOM 요소 타입
```typescript
// 버튼 요소
let button = document.getElementById("submitBtn") as HTMLButtonElement;
button.disabled = true;

// 이미지 요소
let image = document.getElementById("profileImg") as HTMLImageElement;
image.src = "profile.jpg";

// 폼 요소
let form = document.getElementById("userForm") as HTMLFormElement;
form.submit();
```

### 3. API 응답 처리

#### 외부 API 데이터 타입 단언
```typescript
interface User {
    id: number;
    name: string;
    email: string;
}

// API 응답 데이터
let apiResponse: any = { 
    id: 1, 
    name: "김철수", 
    email: "kim@example.com" 
};

// 타입 단언으로 안전한 타입 적용
let user = apiResponse as User;

console.log(user.name); // 김철수
console.log(user.email); // kim@example.com
```

#### 배열 데이터 타입 단언
```typescript
interface Product {
    id: number;
    name: string;
    price: number;
}

// API에서 받은 배열 데이터
let productsData: any = [
    { id: 1, name: "노트북", price: 1000000 },
    { id: 2, name: "마우스", price: 50000 }
];

// 배열 타입 단언
let products = productsData as Product[];

products.forEach(product => {
    console.log(`${product.name}: ${product.price}원`);
});
```

### 4. 고급 타입 단언 패턴

#### 이중 타입 단언
```typescript
// string -> unknown -> number (이중 단언)
let strValue: string = "42";
let numValue: number = (strValue as unknown) as number;

// 주의: 실제 값 변환이 아닌 타입만 변경
console.log(numValue); // "42" (문자열 그대로)
```

#### 조건부 타입 단언
```typescript
function processValue(value: unknown): string {
    if (typeof value === 'string') {
        return value.toUpperCase();
    } else if (typeof value === 'number') {
        return value.toString();
    } else {
        // 타입 단언으로 기본값 처리
        return (value as any).toString() || 'unknown';
    }
}
```

## 예시

### 1. 실제 사용 사례

#### 이벤트 핸들러에서 DOM 요소 타입 단언
```typescript
interface FormData {
    username: string;
    email: string;
    age: number;
}

function handleFormSubmit(event: Event) {
    event.preventDefault();
    
    // 폼 요소 타입 단언
    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);
    
    // 입력 요소들 타입 단언
    const usernameInput = document.getElementById('username') as HTMLInputElement;
    const emailInput = document.getElementById('email') as HTMLInputElement;
    const ageInput = document.getElementById('age') as HTMLInputElement;
    
    const data: FormData = {
        username: usernameInput.value,
        email: emailInput.value,
        age: parseInt(ageInput.value)
    };
    
    console.log('폼 데이터:', data);
}

// 이벤트 리스너 등록
document.getElementById('userForm')?.addEventListener('submit', handleFormSubmit);
```

#### API 클라이언트에서 응답 타입 단언
```typescript
interface ApiResponse<T> {
    data: T;
    status: number;
    message: string;
}

interface User {
    id: number;
    name: string;
    email: string;
}

class ApiClient {
    async fetchUser(id: number): Promise<User> {
        try {
            const response = await fetch(`/api/users/${id}`);
            const result = await response.json();
            
            // API 응답 타입 단언
            const apiResponse = result as ApiResponse<User>;
            
            if (apiResponse.status === 200) {
                return apiResponse.data;
            } else {
                throw new Error(apiResponse.message);
            }
        } catch (error) {
            throw new Error(`사용자 조회 실패: ${error}`);
        }
    }
}

// 사용 예시
const apiClient = new ApiClient();
apiClient.fetchUser(1).then(user => {
    console.log(`사용자: ${user.name} (${user.email})`);
});
```

### 2. 고급 활용 패턴

#### 타입 가드와 함께 사용
```typescript
interface Admin {
    id: number;
    name: string;
    role: 'admin';
    permissions: string[];
}

interface RegularUser {
    id: number;
    name: string;
    role: 'user';
    email: string;
}

type User = Admin | RegularUser;

// 타입 가드 함수
function isAdmin(user: User): user is Admin {
    return user.role === 'admin';
}

function processUser(user: User) {
    if (isAdmin(user)) {
        // 타입 가드로 인해 Admin 타입으로 추론됨
        console.log(`관리자 권한: ${user.permissions.join(', ')}`);
    } else {
        // RegularUser 타입으로 추론됨
        console.log(`사용자 이메일: ${user.email}`);
    }
}

// 타입 단언과 타입 가드 조합
function getUserFromApi(data: any): User {
    // 기본적인 타입 단언
    const user = data as User;
    
    // 추가 검증
    if (!user.id || !user.name || !user.role) {
        throw new Error('유효하지 않은 사용자 데이터');
    }
    
    return user;
}
```

#### 제네릭과 타입 단언
```typescript
interface ApiResult<T> {
    success: boolean;
    data?: T;
    error?: string;
}

class TypedApiClient {
    async request<T>(url: string): Promise<T> {
        const response = await fetch(url);
        const result = await response.json();
        
        // 제네릭 타입 단언
        const apiResult = result as ApiResult<T>;
        
        if (apiResult.success && apiResult.data) {
            return apiResult.data;
        } else {
            throw new Error(apiResult.error || 'API 요청 실패');
        }
    }
}

// 사용 예시
const client = new TypedApiClient();

interface Product {
    id: number;
    name: string;
    price: number;
}

// 타입 안전한 API 호출
client.request<Product[]>('/api/products').then(products => {
    products.forEach(product => {
        console.log(`${product.name}: ${product.price}원`);
    });
});
```

## 운영 팁

### 성능 최적화

#### 타입 단언 최소화
```typescript
// 좋지 않은 예: 과도한 타입 단언
function processData(data: any) {
    const user = data as User;
    const settings = data.settings as Settings;
    const preferences = data.preferences as Preferences;
    // ...
}

// 좋은 예: 타입 가드 활용
function processData(data: unknown) {
    if (isValidUserData(data)) {
        // 타입 가드로 안전한 타입 추론
        console.log(data.name); // User 타입으로 추론됨
    }
}

function isValidUserData(data: unknown): data is User {
    return typeof data === 'object' && 
           data !== null && 
           'id' in data && 
           'name' in data;
}
```

### 에러 처리

#### 안전한 타입 단언
```typescript
function safeTypeAssertion<T>(value: unknown, typeGuard: (value: unknown) => value is T): T {
    if (typeGuard(value)) {
        return value;
    }
    throw new Error(`타입 단언 실패: ${typeof value}는 유효하지 않은 타입입니다.`);
}

// 사용 예시
interface User {
    id: number;
    name: string;
}

function isUser(value: unknown): value is User {
    return typeof value === 'object' && 
           value !== null && 
           typeof (value as any).id === 'number' &&
           typeof (value as any).name === 'string';
}

const userData: unknown = { id: 1, name: "홍길동" };
const user = safeTypeAssertion(userData, isUser);
console.log(user.name); // 홍길동
```

## 참고

### 타입 단언 사용 시 주의사항

1. **런타임 에러 위험**: 잘못된 타입 단언은 런타임 에러를 유발할 수 있습니다
2. **타입 안전성 손실**: 컴파일러의 타입 검사를 우회하므로 신중하게 사용해야 합니다
3. **타입 가드 우선**: 가능한 한 타입 가드를 사용하여 안전성을 확보하세요
4. **문서화**: 복잡한 타입 단언은 주석으로 이유를 명시하세요

### 타입 단언 vs 타입 가드

```typescript
// 타입 단언 (위험)
let value: unknown = "hello";
let length = (value as string).length; // 런타임 에러 가능성

// 타입 가드 (안전)
let value2: unknown = "hello";
if (typeof value2 === 'string') {
    let length2 = value2.length; // 안전한 타입 추론
}
```

### 결론
TypeScript의 타입 단언은 강력한 도구이지만 신중하게 사용해야 합니다.
타입 가드를 우선적으로 사용하고, 필요한 경우에만 타입 단언을 활용하세요.
DOM 조작, API 응답 처리 등에서 유용하게 사용할 수 있습니다.
타입 안전성을 최대한 유지하면서 개발 효율성을 향상시키는 균형을 찾으세요.
복잡한 타입 단언은 문서화하고 테스트를 통해 검증하세요.





