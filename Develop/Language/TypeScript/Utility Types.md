
# TypeScript 유틸리티 타입

TypeScript의 **유틸리티 타입(Utility Types)**은 기존 타입을 변환하거나 재활용할 수 있는 강력한 기능을 제공합니다.
이 기능을 통해 더 간결하고 유지보수하기 쉬운 코드를 작성할 수 있습니다.

---

## 1. `Partial<T>`
`Partial<T>`는 타입 `T`의 모든 속성을 **선택적으로(optional)** 변경한 타입을 생성합니다.
즉, 필수 속성을 선택적으로 만들 때 사용됩니다.

### 특징
- 기존 타입의 모든 속성을 `?` (옵셔널)로 변환합니다.
- 부분적으로 데이터를 업데이트하는 데 유용합니다.

### 사용 예시

```typescript
interface User {
  id: number;
  name: string;
  email: string;
}

type PartialUser = Partial<User>;

const updateUser: PartialUser = {
  name: "Alice"
};
```

### 구현 방식
`Partial`은 TypeScript의 **맵드 타입(Mapped Type)**으로 구현됩니다.

```typescript
type Partial<T> = {
  [P in keyof T]?: T[P];
};
```

---

## 2. `Pick<T, K>`
`Pick<T, K>`는 타입 `T`에서 특정 속성 `K`만 선택하여 새로운 타입을 생성합니다.

### 특징
- 기존 타입에서 필요한 속성만 선택해 사용할 수 있습니다.
- 불필요한 데이터를 제거하여 간결한 타입을 정의합니다.

### 사용 예시

```typescript
interface Product {
  id: number;
  name: string;
  price: number;
  description: string;
}

type ProductPreview = Pick<Product, "id" | "name" | "price">;

const product: ProductPreview = {
  id: 1,
  name: "Laptop",
  price: 1500
};
```

### 구현 방식

```typescript
type Pick<T, K extends keyof T> = {
  [P in K]: T[P];
};
```

---

## 3. `Omit<T, K>`
`Omit<T, K>`는 타입 `T`에서 특정 속성 `K`를 제거하여 새로운 타입을 생성합니다.

### 특징
- `Pick`과 반대 개념으로, 필요 없는 속성을 제외합니다.
- 코드에서 속성을 명시적으로 제거할 때 유용합니다.

### 사용 예시

```typescript
interface Product {
  id: number;
  name: string;
  price: number;
  stock: number;
}

type ProductWithoutStock = Omit<Product, "stock">;

const product: ProductWithoutStock = {
  id: 1,
  name: "Smartphone",
  price: 800
};
```

### 구현 방식

```typescript
type Omit<T, K extends keyof T> = Pick<T, Exclude<keyof T, K>>;
```

---

## 4. `Record<K, T>`
`Record<K, T>`는 키 `K`와 값 `T`를 가지는 객체 타입을 생성합니다.

### 특징
- 키와 값을 명확히 정의한 객체 타입을 생성할 때 사용합니다.
- 맵과 유사한 자료 구조를 모델링할 때 유용합니다.

### 사용 예시

```typescript
type UserRole = "admin" | "editor" | "viewer";

type Permissions = Record<UserRole, boolean>;

const roles: Permissions = {
  admin: true,
  editor: true,
  viewer: false
};
```

### 구현 방식

```typescript
type Record<K extends keyof any, T> = {
  [P in K]: T;
};
```

---

## 5. `Required<T>`
`Required<T>`는 타입 `T`의 모든 선택적 속성을 필수 속성으로 변경합니다.

### 특징
- 옵셔널 속성을 강제로 필수로 변경할 때 유용합니다.

### 사용 예시

```typescript
interface User {
  id: number;
  name?: string;
  email?: string;
}

type FullUser = Required<User>;

const user: FullUser = {
  id: 1,
  name: "Alice",
  email: "alice@example.com"
};
```

### 구현 방식

```typescript
type Required<T> = {
  [P in keyof T]-?: T[P];
};
```

---

## 6. `Exclude<T, U>`
`Exclude<T, U>`는 타입 `T`에서 타입 `U`에 할당 가능한 모든 타입을 제거합니다.

### 특징
- 유니온 타입에서 특정 타입을 제거할 때 유용합니다.

### 사용 예시

```typescript
type Roles = "admin" | "editor" | "viewer";
type WithoutViewer = Exclude<Roles, "viewer">;

const role: WithoutViewer = "admin"; // "viewer"는 허용되지 않음
```

### 구현 방식

```typescript
type Exclude<T, U> = T extends U ? never : T;
```

---

## 7. `Extract<T, U>`
`Extract<T, U>`는 타입 `T`에서 타입 `U`에 할당 가능한 모든 타입을 추출합니다.

### 특징
- 유니온 타입에서 특정 타입만 추출합니다.

### 사용 예시

```typescript
type Roles = "admin" | "editor" | "viewer";
type OnlyViewer = Extract<Roles, "viewer">;

const role: OnlyViewer = "viewer"; // "admin"과 "editor"는 허용되지 않음
```

### 구현 방식

```typescript
type Extract<T, U> = T extends U ? T : never;
```

---

이 외에도 `NonNullable<T>`, `ReturnType<T>`, `InstanceType<T>` 등 다양한 유틸리티 타입이 있습니다. 각 타입은 다양한 상황에서 코드의 가독성과 유지보수성을 높이는 데 기여합니다.
