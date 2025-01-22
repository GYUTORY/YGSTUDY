
# TypeScript Generic

- TypeScript의 제네릭(Generic)은 재사용 가능한 컴포넌트를 작성할 때 사용되는 강력한 도구입니다.
- 제네릭을 활용하면 타입의 유연성과 안정성을 동시에 확보할 수 있습니다.

---

## 👉🏻 Generic의 기본 개념

- 제네릭은 **타입을 매개변수로 받을 수 있는 함수, 클래스, 인터페이스를 정의**할 수 있게 해줍니다.
- 코드 재사용성을 높이고 타입 안정성을 보장합니다.

### 기본 사용법

```typescript
function identity<T>(value: T): T { // T는 타입 매개변수
    return value;
}

const num = identity<number>(42); // T를 number로 지정
const str = identity<string>('Hello'); // T를 string으로 지정

console.log(num); // 42
console.log(str); // Hello
```

#### 주석으로 설명:
- `T`는 타입 매개변수로, 함수 호출 시 실제 타입이 결정됩니다.
- `identity<number>(42)`는 `T`를 `number`로, `identity<string>('Hello')`는 `T`를 `string`으로 설정합니다.

---

## ✨ Generic 함수를 활용한 예제

### 배열 반환 함수

```typescript
function getArray<T>(items: T[]): T[] {
    return items;
}

const numArray = getArray<number>([1, 2, 3]); // number 배열
const strArray = getArray<string>(['a', 'b', 'c']); // string 배열

console.log(numArray); // [1, 2, 3]
console.log(strArray); // ['a', 'b', 'c']
```

#### 주석으로 설명:
- `T[]`는 `T` 타입의 배열을 나타냅니다.
- 동일한 함수가 다양한 타입의 배열을 처리할 수 있습니다.

---

## 👉🏻 Generic 인터페이스

제네릭은 인터페이스에도 적용할 수 있습니다.

### 기본 사용법

```typescript
interface Pair<K, V> {
    key: K;
    value: V;
}

const numPair: Pair<number, string> = { key: 1, value: 'one' };
const strPair: Pair<string, boolean> = { key: 'isActive', value: true };

console.log(numPair); // { key: 1, value: 'one' }
console.log(strPair); // { key: 'isActive', value: true }
```

#### 주석으로 설명:
- `Pair<K, V>`는 두 개의 타입 매개변수 `K`와 `V`를 사용합니다.
- `numPair`와 `strPair`는 각각 다른 타입 조합을 사용합니다.

---

## ✨ Generic 클래스

제네릭은 클래스에서도 유용하게 사용할 수 있습니다.

### 기본 사용법

```typescript
class DataStorage<T> {
    private items: T[] = [];

    addItem(item: T): void {
        this.items.push(item);
    }

    removeItem(item: T): void {
        this.items = this.items.filter(i => i !== item);
    }

    getItems(): T[] {
        return this.items;
    }
}

const stringStorage = new DataStorage<string>();
stringStorage.addItem('Apple');
stringStorage.addItem('Banana');
stringStorage.removeItem('Apple');
console.log(stringStorage.getItems()); // ['Banana']

const numberStorage = new DataStorage<number>();
numberStorage.addItem(10);
numberStorage.addItem(20);
console.log(numberStorage.getItems()); // [10, 20]
```

#### 주석으로 설명:
- `DataStorage<T>` 클래스는 `T` 타입의 데이터를 저장, 삭제, 조회할 수 있습니다.
- 서로 다른 타입의 데이터를 각각 관리할 수 있습니다.

---

## 👉🏻 제약 조건 (Constraints)

제네릭에 타입 제약 조건을 추가하여 특정 타입만 허용할 수 있습니다.

### 기본 사용법

```typescript
interface Lengthwise {
    length: number;
}

function logWithLength<T extends Lengthwise>(value: T): void {
    console.log(value.length);
}

logWithLength('Hello'); // 5 (문자열은 length 속성이 있음)
logWithLength([1, 2, 3]); // 3 (배열은 length 속성이 있음)
// logWithLength(42); // 오류: number에는 length 속성이 없음
```

#### 주석으로 설명:
- `T extends Lengthwise`는 `T`가 반드시 `length` 속성을 가져야 함을 명시합니다.
- 문자열과 배열은 허용되지만, `number`는 허용되지 않습니다.

---

## ✨ 여러 타입 매개변수 사용

제네릭은 여러 개의 타입 매개변수를 사용할 수 있습니다.

```typescript
function merge<T, U>(obj1: T, obj2: U): T & U {
    return { ...obj1, ...obj2 };
}

const mergedObj = merge({ name: 'Alice' }, { age: 25 });
console.log(mergedObj); // { name: 'Alice', age: 25 }
```

#### 주석으로 설명:
- `T`와 `U`는 각각 객체의 타입을 나타냅니다.
- 반환 타입은 두 객체의 속성을 모두 포함하는 교차 타입(`T & U`)입니다.

---

## 👉🏻 제네릭 유틸리티 타입

TypeScript에는 제네릭과 함께 사용할 수 있는 유틸리티 타입이 존재합니다.

### `keyof` 연산자

```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
    return obj[key];
}

const person = { name: 'Bob', age: 30 };
const name = getProperty(person, 'name'); // 'Bob'
const age = getProperty(person, 'age'); // 30
```

#### 주석으로 설명:
- `K extends keyof T`는 `K`가 반드시 `T`의 키 중 하나임을 보장합니다.
- 반환 타입은 `T[K]`로, 키의 값 타입을 나타냅니다.

---

## 📋 제네릭의 주요 장점

1. **타입 안전성**: 컴파일 단계에서 타입 검사가 이루어져 런타임 오류를 줄입니다.
2. **재사용성**: 다양한 타입을 처리할 수 있는 범용 함수와 클래스를 작성할 수 있습니다.
3. **가독성**: 코드를 이해하기 쉽고 유지보수가 용이합니다.

---

## 🛠️ 제네릭 조합 예제

제네릭을 조합하여 더욱 복잡한 타입을 정의할 수 있습니다.

```typescript
interface ApiResponse<T> {
    data: T;
    success: boolean;
}

function fetchData<T>(url: string): ApiResponse<T> {
    // 가상의 데이터 반환
    return {
        data: {} as T,
        success: true,
    };
}

const userResponse = fetchData<{ id: number; name: string }>('api/user');
console.log(userResponse.data.id); // number
console.log(userResponse.data.name); // string
```

---

