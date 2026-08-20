---
title: TypeScript 타입 단언
tags: [language, typescript]
updated: 2025-12-18
---

# TypeScript 타입 단언
## 배경

TypeScript에서 타입 단언(Type Assertion)은 개발자가 특정 값의 타입을 컴파일러에게 "알려주는" 방식이다.

### 타입 단언의 필요성
- **타입 추론 한계 극복**: 컴파일러가 타입을 제대로 추론하지 못할 때
- **DOM 조작**: HTML 요소의 구체적인 타입 지정
- **API 응답 처리**: 외부 데이터의 타입 명시
- **레거시 코드 통합**: 기존 JavaScript 코드와의 호환성

### 기본 문법
타입 단언은 두 가지 형태로 쓸 수 있다.

```typescript
// as 키워드 사용 (권장)
let someValue: unknown = "Hello, TypeScript";
let strLength: number = (someValue as string).length;

// 꺾쇠 괄호 사용 (React JSX와 충돌 가능성)
let someValue2: unknown = "Hello, TypeScript";
let strLength2: number = (<string>someValue2).length;
```

꺾쇠 문법이 "React JSX와 충돌 가능성"이 있다는 건 정확히는 **`.tsx` 파일에서 아예 파싱되지 않는다**는 뜻이다. 가능성이 아니라 확정이다.

```
ta.tsx(3,20): error TS17008: JSX element 'string' has no corresponding closing tag.
ta.tsx(4,1): error TS1005: '</' expected.
```

컴파일러가 `<string>` 을 여는 JSX 태그로 읽어 버린다. 같은 코드가 `.ts` 에서는 통과한다. 파일 확장자에 따라 문법이 갈리는 자리이므로 **`as` 하나로 통일하는 게 맞다.** 아래 예제들도 전부 `as` 를 쓴다.

한 가지 짚어 둘 것은 두 문법 모두 **런타임에는 아무것도 남기지 않는다**는 점이다. 타입 단언은 컴파일 시 통째로 지워진다. 값을 바꾸지도, 검사하지도 않는다. 이 문서 전체를 읽을 때 기준으로 삼아야 할 사실이다.

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
image.src = "profile.webp";

// 폼 요소
let form = document.getElementById("userForm") as HTMLFormElement;
form.submit();
```

이 절의 단언은 **두 가지를 한꺼번에 주장하는데, 그중 하나가 훨씬 위험하다.**

`getElementById` 의 반환 타입은 `HTMLElement | null` 이다. `as HTMLInputElement` 는 "이건 input 이다"뿐 아니라 **"null 이 아니다"까지 함께 주장한다.** 앞쪽은 대개 맞지만 뒤쪽은 id 오타 하나로 무너진다.

```typescript
const el = document.getElementById("myInput");
el.value = "x";
// error TS18047: 'el' is possibly 'null'.
// error TS2339: Property 'value' does not exist on type 'HTMLElement'.

const el2 = document.getElementById("myInput") as HTMLInputElement;
el2.value = "x";   // 에러 없음 — 두 경고가 모두 사라졌다
```

단언을 붙이는 순간 컴파일러가 정확히 짚어 주던 두 문제가 동시에 침묵한다. 요소가 없으면 `Cannot read properties of null` 로 런타임에 터지는데, 그때는 어느 id 가 틀렸는지 스택만 보고 찾아야 한다.

DOM 은 **HTML 이 바뀌면 조용히 깨지는 곳**이다. 마크업은 컴파일러가 검사하지 않으니 `as` 로 눌러 둔 가정을 지켜 줄 장치가 어디에도 없다. null 검사를 남기는 편이 낫다.

```typescript
const input = document.getElementById("myInput");
if (!(input instanceof HTMLInputElement)) {
    throw new Error("#myInput 이 없거나 input 요소가 아닙니다");
}
input.value = "Hello!";   // 여기서부터 타입도 존재도 보장된다
```

`instanceof` 는 런타임에 실제로 확인하므로 타입 좁히기와 존재 확인을 동시에 해결한다. `as` 와 달리 틀렸을 때 **원인이 적힌 에러**가 난다.

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

이중 단언 예제의 주석은 정확하다. 값은 그대로 문자열이다. 그런데 그 뒤가 더 중요하다. **타입 시스템만 `number` 로 믿고 있으므로 숫자처럼 쓰는 순간 전부 어긋난다.**

```javascript
numValue + 1         // "421"   ← 덧셈이 아니라 문자열 이어붙이기
numValue.toFixed(2)  // TypeError: numValue.toFixed is not a function
```

`numValue.toFixed(2)` 는 컴파일을 통과한다. `number` 라고 단언했으니 컴파일러 입장에서는 있는 메서드다. **`as unknown as T` 는 TypeScript 가 제공하는 마지막 안전장치까지 끄는 문법**이라, 코드에서 발견되면 대개 타입 설계가 틀렸다는 신호로 읽어야 한다.

**`processValue` 의 `else` 절은 `null` 과 `undefined` 에서 예외를 던진다.** 반환 타입은 `string` 인데 값을 돌려주지 못한다.

```javascript
processValue(null)       // TypeError: Cannot read properties of null (reading 'toString')
processValue(undefined)  // TypeError: Cannot read properties of undefined (reading 'toString')
processValue(true)       // "true"          정상
processValue({})         // "[object Object]"
```

`|| 'unknown'` 이 기본값을 대준다고 착각하기 쉽지만, 그 자리에 닿기도 전에 `.toString()` 호출에서 터진다. `null` 과 `undefined` 는 `toString` 을 갖지 않는 유일한 두 값이고, 하필 **함수가 방어해야 할 대표적인 입력**이다.

`(value as any)` 가 이걸 가렸다. `any` 로 바꾸는 순간 컴파일러는 `null` 가능성 검사를 그만둔다. `String(value)` 를 쓰면 이 부류를 전부 흡수한다 — `String(null)` 은 `'null'` 이고 예외가 아니다.

```typescript
} else {
    return value == null ? 'unknown' : String(value);
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

`fetchUser` 의 `try` 가 **자기가 던진 에러까지 다시 잡는다.** `throw new Error(apiResponse.message)` 는 같은 `try` 블록 안에 있으므로 곧바로 아래 `catch` 로 들어가 한 번 더 감싸진다.

```
사용자 조회 실패: Error: 사용자를 찾을 수 없습니다
```

`${error}` 로 문자열 보간을 하면 `Error` 객체가 `"Error: 메시지"` 로 변환되므로 접두어가 중첩된다. 호출한 쪽은 원본 `Error` 인스턴스도, 스택 트레이스도 받지 못한다 — 새 `Error` 가 만들어지면서 스택이 이 줄로 덮인다. 네트워크 오류와 API 가 정상 응답한 실패가 **구분 불가능해지는** 것도 문제다.

`cause` 로 원인을 보존하고, 던질 범위를 좁힌다.

```typescript
const response = await fetch(`/api/users/${id}`);
let result: unknown;
try {
    result = await response.json();
} catch (error) {
    throw new Error(`사용자 조회 실패(응답 파싱)`, { cause: error });
}
// 검증과 throw 는 try 밖에서 — 자기 에러를 자기가 잡지 않는다
```

`try` 블록은 **실제로 실패할 수 있는 호출만** 감싼다. 넓게 잡을수록 의도한 예외와 사고를 뭉뚱그리게 된다.

`getUserFromApi` 에도 확인된 결함이 있다. `!user.id` 는 **`id` 가 `0` 일 때도 참**이다.

```javascript
!({ id: 0, name: 'a', role: 'user' }).id   // true → "유효하지 않은 사용자 데이터"
!({ id: 1, name: '', role: 'user' }).name  // true → 빈 이름도 같은 에러로
```

`0` 은 유효한 ID 이고 빈 문자열은 이름 누락과 다른 문제인데, 셋 다 같은 메시지로 거절된다. 존재 여부를 물을 때는 falsy 검사 대신 `== null` 이나 `in` 을 쓴다.

```typescript
if (user.id == null || user.name == null || user.role == null) { ... }
```

그리고 이 함수의 `data as User` 는 `User` 가 `Admin | RegularUser` 유니온이라는 점에서 특히 위험하다. **`role` 값이 `'admin'` 도 `'user'` 도 아닌 문자열이어도 단언은 통과한다.** 그 뒤 `isAdmin` 이 거짓을 반환해 `RegularUser` 로 좁혀지고, 있지도 않은 `user.email` 을 읽어 `undefined` 가 나온다. 판별 유니온은 판별자 값을 실제로 검사해야 의미가 있다.

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

1. **런타임 에러 위험**: 잘못된 타입 단언은 런타임 에러를 유발할 수 있다
2. **타입 안전성 손실**: 컴파일러의 타입 검사를 우회하므로 신중하게 써야 한다
3. **타입 가드 우선**: 가능하면 타입 가드를 써서 안전성을 확보한다
4. **문서화**: 복잡한 타입 단언은 주석으로 이유를 남긴다

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
TypeScript의 타입 단언은 강력한 도구지만 신중하게 써야 한다.
타입 가드를 먼저 쓰고, 꼭 필요할 때만 타입 단언을 쓴다.
DOM 조작, API 응답 처리 등에서 유용하다.
타입 안전성을 최대한 유지하면서 개발 효율을 높이는 균형점을 찾는다.
복잡한 타입 단언은 문서로 남기고 테스트로 검증한다.





