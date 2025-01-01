
# TypeScript의 `Partial`과 `Pick`

TypeScript는 코드 재사용성과 가독성을 높이기 위해 다양한 유틸리티 타입을 제공합니다. 이 중 `Partial`과 `Pick`은 타입 변환과 선택에 매우 유용한 도구입니다.

---

## 1. `Partial`

`Partial`은 **주어진 타입의 모든 프로퍼티를 선택적으로 변경**할 수 있는 새로운 타입을 생성합니다. 즉, 기존 타입의 모든 필드를 `optional`로 변환합니다.

### **사용법**
```typescript
type Partial<T> = {
    [P in keyof T]?: T[P];
};
```

### **예시**

#### 기존 타입 정의
```typescript
interface User {
    id: number;
    name: string;
    email: string;
}
```

#### `Partial`을 사용한 새로운 타입
```typescript
type PartialUser = Partial<User>;

// PartialUser 타입
// {
//   id?: number;
//   name?: string;
//   email?: string;
// }
```

#### 사용 예시
```typescript
function updateUser(user: Partial<User>) {
    // user의 일부 속성만 업데이트 가능
    console.log("업데이트된 사용자 정보:", user);
}

// id와 name만 업데이트
updateUser({ id: 1, name: "John Doe" });
```

---

## 2. `Pick`

`Pick`은 **주어진 타입에서 특정 프로퍼티만 선택**하여 새로운 타입을 생성합니다.

### **사용법**
```typescript
type Pick<T, K extends keyof T> = {
    [P in K]: T[P];
};
```

### **예시**

#### 기존 타입 정의
```typescript
interface User {
    id: number;
    name: string;
    email: string;
}
```

#### `Pick`을 사용한 새로운 타입
```typescript
type UserPreview = Pick<User, "id" | "name">;

// UserPreview 타입
// {
//   id: number;
//   name: string;
// }
```

#### 사용 예시
```typescript
const userPreview: UserPreview = {
    id: 1,
    name: "Jane Doe",
};

console.log(userPreview);
```

---

## 3. `Partial`과 `Pick`의 조합

`Partial`과 `Pick`을 조합하여 타입을 더욱 유연하게 조작할 수 있습니다.

### 예시
```typescript
type PartialUserPreview = Partial<Pick<User, "id" | "name">>;

// PartialUserPreview 타입
// {
//   id?: number;
//   name?: string;
// }
```

#### 사용 예시
```typescript
const partialUserPreview: PartialUserPreview = {
    id: 2, // name은 선택적으로 생략 가능
};

console.log(partialUserPreview);
```

---

## 정리

- `Partial`: 타입의 모든 속성을 선택적으로 변경 (`?` 추가).
- `Pick`: 타입에서 특정 속성만 선택.
- 조합하여 더 유연한 타입 조작 가능.

### 참고 문서
- [TypeScript 공식 문서](https://www.typescriptlang.org/docs/)
