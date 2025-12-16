---
title: TypeScript Arrays 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, object-types, arrays]
updated: 2025-12-16
---

# TypeScript Arrays 가이드

## 배경

TypeScript에서 배열은 동일한 타입의 요소들을 순서대로 저장하는 데이터 구조입니다.

### Arrays의 필요성
- **데이터 집합**: 관련된 데이터를 하나의 구조로 관리
- **순차적 접근**: 인덱스를 통한 빠른 요소 접근
- **반복 처리**: for 루프와 함께 사용하여 데이터 순회
- **메서드 활용**: 다양한 배열 메서드를 통한 데이터 조작

### 기본 개념
- **인덱스**: 0부터 시작하는 요소 위치
- **길이**: 배열에 포함된 요소의 개수
- **타입 안전성**: 모든 요소가 동일한 타입을 가져야 함
- **가변 길이**: 요소 추가/제거로 크기 변경 가능

## 핵심

### 1. 배열 선언과 초기화

#### 기본 배열 선언
```typescript
// 숫자 배열
let numbers: number[] = [1, 2, 3, 4, 5];

// 문자열 배열
let names: string[] = ['홍길동', '김철수', '이영희'];

// 불린 배열
let flags: boolean[] = [true, false, true];

// 빈 배열 선언
let emptyArray: number[] = [];
```

#### 제네릭 배열 타입
```typescript
// Array<T> 형태로 선언
let numbers: Array<number> = [1, 2, 3, 4, 5];
let names: Array<string> = ['홍길동', '김철수'];

// 복합 타입 배열
let mixed: Array<string | number> = ['hello', 42, 'world'];
```

### 2. 배열 요소 접근과 조작

#### 인덱스 접근
```typescript
let fruits: string[] = ['사과', '바나나', '오렌지'];

// 인덱스로 요소 접근
console.log(fruits[0]); // '사과'
console.log(fruits[1]); // '바나나'

// 요소 수정
fruits[1] = '포도';
console.log(fruits); // ['사과', '포도', '오렌지']

// 배열 길이
console.log(fruits.length); // 3
```

#### 기본 배열 메서드
```typescript
let numbers: number[] = [1, 2, 3];

// 요소 추가
numbers.push(4, 5);        // 끝에 추가
numbers.unshift(0);        // 앞에 추가

// 요소 제거
let last = numbers.pop();   // 마지막 요소 제거 및 반환
let first = numbers.shift(); // 첫 번째 요소 제거 및 반환

// 요소 삽입/제거
numbers.splice(1, 1, 10);  // 인덱스 1에서 1개 제거하고 10 삽입
```

### 3. 배열 메서드 활용

#### 변환 메서드
```typescript
let numbers: number[] = [1, 2, 3, 4, 5];

// map: 각 요소를 변환
let doubled = numbers.map(x => x * 2);
console.log(doubled); // [2, 4, 6, 8, 10]

// filter: 조건에 맞는 요소만 선택
let evenNumbers = numbers.filter(x => x % 2 === 0);
console.log(evenNumbers); // [2, 4]

// reduce: 배열을 단일 값으로 축소
let sum = numbers.reduce((acc, curr) => acc + curr, 0);
console.log(sum); // 15
```

#### 검색 메서드
```typescript
let fruits: string[] = ['사과', '바나나', '오렌지', '포도'];

// find: 조건에 맞는 첫 번째 요소 찾기
let found = fruits.find(fruit => fruit.startsWith('바'));
console.log(found); // '바나나'

// findIndex: 조건에 맞는 첫 번째 요소의 인덱스
let index = fruits.findIndex(fruit => fruit === '오렌지');
console.log(index); // 2

// includes: 요소 포함 여부 확인
console.log(fruits.includes('포도')); // true
```

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```typescript
interface User {
    id: number;
    name: string;
    age: number;
    email: string;
}

class UserManager {
    private users: User[] = [];

    addUser(user: User): void {
        this.users.push(user);
    }

    removeUser(id: number): boolean {
        const index = this.users.findIndex(user => user.id === id);
        if (index !== -1) {
            this.users.splice(index, 1);
            return true;
        }
        return false;
    }

    findUserById(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }

    getUsersByAge(minAge: number, maxAge: number): User[] {
        return this.users.filter(user => 
            user.age >= minAge && user.age <= maxAge
        );
    }

    getAverageAge(): number {
        if (this.users.length === 0) return 0;
        const totalAge = this.users.reduce((sum, user) => sum + user.age, 0);
        return totalAge / this.users.length;
    }

    sortUsersByName(): User[] {
        return [...this.users].sort((a, b) => a.name.localeCompare(b.name));
    }
}

// 사용 예시
const userManager = new UserManager();

userManager.addUser({ id: 1, name: '홍길동', age: 25, email: 'hong@example.com' });
userManager.addUser({ id: 2, name: '김철수', age: 30, email: 'kim@example.com' });
userManager.addUser({ id: 3, name: '이영희', age: 28, email: 'lee@example.com' });

console.log(userManager.getAverageAge()); // 27.67
console.log(userManager.getUsersByAge(25, 30)); // 25-30세 사용자들
```

#### 데이터 처리 유틸리티
```typescript
class ArrayUtils {
    static chunk<T>(array: T[], size: number): T[][] {
        const chunks: T[][] = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    }

    static unique<T>(array: T[]): T[] {
        return [...new Set(array)];
    }

    static groupBy<T, K extends string | number>(
        array: T[], 
        keySelector: (item: T) => K
    ): Record<K, T[]> {
        return array.reduce((groups, item) => {
            const key = keySelector(item);
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(item);
            return groups;
        }, {} as Record<K, T[]>);
    }

    static shuffle<T>(array: T[]): T[] {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }
}

// 사용 예시
const numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
console.log(ArrayUtils.chunk(numbers, 3)); // [[1,2,3], [4,5,6], [7,8,9], [10]]

const fruits = ['사과', '바나나', '사과', '오렌지', '바나나'];
console.log(ArrayUtils.unique(fruits)); // ['사과', '바나나', '오렌지']
```

### 2. 고급 패턴

#### 다차원 배열
```typescript
// 2차원 배열 (행렬)
let matrix: number[][] = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

// 행렬 전치
function transpose<T>(matrix: T[][]): T[][] {
    return matrix[0].map((_, i) => matrix.map(row => row[i]));
}

console.log(transpose(matrix));
// [[1, 4, 7], [2, 5, 8], [3, 6, 9]]

// 3차원 배열
let cube: number[][][] = [
    [[1, 2], [3, 4]],
    [[5, 6], [7, 8]]
];
```

#### 타입 안전한 배열 조작
```typescript
// 읽기 전용 배열
const readonlyNumbers: readonly number[] = [1, 2, 3, 4, 5];
// readonlyNumbers.push(6); // 컴파일 오류

// 부분 읽기 전용
type PartialReadonly<T> = {
    readonly [P in keyof T]: T[P] extends readonly any[] 
        ? readonly T[P] 
        : T[P];
};

interface Config {
    settings: string[];
    options: number[];
}

const config: PartialReadonly<Config> = {
    settings: ['option1', 'option2'],
    options: [1, 2, 3]
};
// config.settings.push('option3'); // 컴파일 오류
```

## 운영 팁

### 성능 최적화

#### 배열 조작 최적화
```typescript
// 큰 배열에서 성능 최적화
function optimizedFilter<T>(array: T[], predicate: (item: T) => boolean): T[] {
    const result: T[] = [];
    for (let i = 0; i < array.length; i++) {
        if (predicate(array[i])) {
            result.push(array[i]);
        }
    }
    return result;
}

// 메모리 효율적인 배열 복사
function shallowCopy<T>(array: T[]): T[] {
    return array.slice();
}

function deepCopy<T>(array: T[]): T[] {
    return JSON.parse(JSON.stringify(array));
}
```

### 에러 처리

#### 안전한 배열 접근
```typescript
function safeArrayAccess<T>(array: T[], index: number): T | undefined {
    if (index < 0 || index >= array.length) {
        return undefined;
    }
    return array[index];
}

function safeArraySlice<T>(array: T[], start: number, end?: number): T[] {
    const startIndex = Math.max(0, start);
    const endIndex = end !== undefined ? Math.min(array.length, end) : array.length;
    
    if (startIndex >= endIndex) {
        return [];
    }
    
    return array.slice(startIndex, endIndex);
}

// 사용 예시
const numbers = [1, 2, 3, 4, 5];
console.log(safeArrayAccess(numbers, 10)); // undefined
console.log(safeArraySlice(numbers, 2, 10)); // [3, 4, 5]
```

## 참고

### 배열 메서드 참조표

| 메서드 | 설명 | 반환값 |
|--------|------|--------|
| `push()` | 끝에 요소 추가 | 새로운 길이 |
| `pop()` | 마지막 요소 제거 | 제거된 요소 |
| `unshift()` | 앞에 요소 추가 | 새로운 길이 |
| `shift()` | 첫 번째 요소 제거 | 제거된 요소 |
| `splice()` | 요소 삽입/제거 | 제거된 요소들 |
| `slice()` | 부분 배열 추출 | 새로운 배열 |
| `concat()` | 배열 연결 | 새로운 배열 |
| `join()` | 문자열로 변환 | 문자열 |

### 배열 타입 선언 방식

```typescript
// 1. 타입[] 방식 (권장)
let numbers: number[] = [1, 2, 3];

// 2. Array<T> 방식
let numbers: Array<number> = [1, 2, 3];

// 3. 튜플 타입
let tuple: [string, number] = ['hello', 42];

// 4. 읽기 전용 배열
let readonlyNumbers: readonly number[] = [1, 2, 3];
```

### 결론
TypeScript의 배열은 데이터를 효율적으로 관리하고 조작하는 강력한 도구입니다.
타입 안전성을 통해 배열 요소의 타입을 보장하고 런타임 오류를 방지할 수 있습니다.
다양한 배열 메서드를 활용하여 데이터 변환, 필터링, 검색 등의 작업을 수행하세요.
성능을 고려하여 적절한 배열 조작 방법을 선택하세요.
안전한 배열 접근을 통해 인덱스 오류를 방지하세요.




배열 선언하기
- 배열을 선언할 때는 유형[] 형태의 구문을 사용합니다. 
- 유형은 배열에 포함될 요소들의 유형을 나타냅니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
let names: string[] = ['John', 'Jane', 'Mike'];
```

배열 요소 접근하기
- 배열은 0부터 시작하는 인덱스를 사용하여 요소에 접근할 수 있습니다.
- 인덱스에 대괄호([])를 사용하여 접근하거나, 배열명[인덱스] 형태로 접근합니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers[0]); // 출력: 1
console.log(numbers[2]); // 출력: 3
```


배열 길이
- 배열의 길이는 배열명.length를 통해 확인할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers.length); // 출력: 5
```

배열 메서드
- 다양한 내장 메서드를 활용하여 배열을 조작하고 변경할 수 있습니다.
- 예를 들어, push(), pop(), slice(), splice(), concat() 등을 사용할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];

// push(): 배열의 끝에 요소를 추가합니다
numbers.push(6, 7);
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6, 7]

// pop(): 배열에서 마지막 요소를 제거하고 반환합니다
let lastNumber = numbers.pop();
console.log(lastNumber); // 출력: 7
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6]

// slice(): 배열의 일부분을 새 배열로 반환합니다
let subArray = numbers.slice(2, 4);
console.log(subArray); // 출력: [3, 4]

// splice(): 배열의 내용을 변경하여 요소를 제거, 교체 또는 추가합니다
numbers.splice(1, 2, 8, 9);
console.log(numbers); // 출력: [1, 8, 9, 4, 5, 6]

// concat(): 두 개 이상의 배열을 연결하여 새 배열을 반환합니다
let moreNumbers: number[] = [10, 11, 12];
let combinedArray = numbers.concat(moreNumbers);
console.log(combinedArray); // 출력: [1, 8, 9, 4, 5, 6, 10, 11, 12]
```

다차원 배열
- TypeScript에서는 다차원 배열도 지원됩니다.
- 이는 배열의 요소로 또 다른 배열을 포함하는 배열을 의미합니다.

```typescript
let matrix: number[][] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]];
console.log(matrix[0][1]); // 출력: 2
```

* 배열은 데이터를 집합적으로 저장하고 조작하는 데 유용한 도구입니다. 
* 다양한 배열 메서드를 활용하여 데이터를 필터링, 변환, 정렬 등 다양한 작업을 수행할 수 있습니다.
* TypeScript는 배열의 유형을 추론하고 유형 검사를 수행하여 유효성을 보장합니다.



배열 선언하기
- 배열을 선언할 때는 유형[] 형태의 구문을 사용합니다. 
- 유형은 배열에 포함될 요소들의 유형을 나타냅니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
let names: string[] = ['John', 'Jane', 'Mike'];
```

배열 요소 접근하기
- 배열은 0부터 시작하는 인덱스를 사용하여 요소에 접근할 수 있습니다.
- 인덱스에 대괄호([])를 사용하여 접근하거나, 배열명[인덱스] 형태로 접근합니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers[0]); // 출력: 1
console.log(numbers[2]); // 출력: 3
```


배열 길이
- 배열의 길이는 배열명.length를 통해 확인할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];
console.log(numbers.length); // 출력: 5
```

배열 메서드
- 다양한 내장 메서드를 활용하여 배열을 조작하고 변경할 수 있습니다.
- 예를 들어, push(), pop(), slice(), splice(), concat() 등을 사용할 수 있습니다.

```typescript
let numbers: number[] = [1, 2, 3, 4, 5];

// push(): 배열의 끝에 요소를 추가합니다
numbers.push(6, 7);
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6, 7]

// pop(): 배열에서 마지막 요소를 제거하고 반환합니다
let lastNumber = numbers.pop();
console.log(lastNumber); // 출력: 7
console.log(numbers); // 출력: [1, 2, 3, 4, 5, 6]

// slice(): 배열의 일부분을 새 배열로 반환합니다
let subArray = numbers.slice(2, 4);
console.log(subArray); // 출력: [3, 4]

// splice(): 배열의 내용을 변경하여 요소를 제거, 교체 또는 추가합니다
numbers.splice(1, 2, 8, 9);
console.log(numbers); // 출력: [1, 8, 9, 4, 5, 6]

// concat(): 두 개 이상의 배열을 연결하여 새 배열을 반환합니다
let moreNumbers: number[] = [10, 11, 12];
let combinedArray = numbers.concat(moreNumbers);
console.log(combinedArray); // 출력: [1, 8, 9, 4, 5, 6, 10, 11, 12]
```

다차원 배열
- TypeScript에서는 다차원 배열도 지원됩니다.
- 이는 배열의 요소로 또 다른 배열을 포함하는 배열을 의미합니다.

```typescript
let matrix: number[][] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]];
console.log(matrix[0][1]); // 출력: 2
```

* 배열은 데이터를 집합적으로 저장하고 조작하는 데 유용한 도구입니다. 
* 다양한 배열 메서드를 활용하여 데이터를 필터링, 변환, 정렬 등 다양한 작업을 수행할 수 있습니다.
* TypeScript는 배열의 유형을 추론하고 유형 검사를 수행하여 유효성을 보장합니다.

# Arrays
- 여러 개의 값들을 순서대로 저장하는 데이터 구조입니다.
- 배열은 동일한 유형의 값을 담을 수 있는 인덱스로 접근할 수 있는 컬렉션입니다. 
- TypeScript에서 배열은 특정 유형(type)의 요소로 구성되며, 배열의 길이는 동적으로 확장할 수 있습니다.



