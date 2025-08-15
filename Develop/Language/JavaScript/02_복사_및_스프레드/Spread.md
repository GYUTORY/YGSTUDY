---
title: JavaScript Spread 연산자 개념과 사용법
tags: [language, javascript, 02복사및스프레드, spread, shallow-copy]
updated: 2025-08-10
---

# JavaScript Spread 연산자 개념과 사용법

## 배경

Spread 연산자(`...`)는 ES6에서 도입된 강력한 문법으로, 배열이나 객체의 요소를 펼쳐서 새로운 배열이나 객체를 생성할 수 있습니다. 특히 얕은 복사(shallow copy)를 간편하게 수행할 수 있어 현대 JavaScript 개발에서 널리 사용됩니다.

### Spread 연산자의 필요성
- **간편한 복사**: 복잡한 복사 로직 없이 간단한 문법으로 복사
- **배열 조작**: 배열의 요소를 쉽게 추가, 삭제, 결합
- **객체 병합**: 여러 객체를 하나로 병합
- **함수 인자**: 배열을 함수의 개별 인자로 전달

### 기본 개념
- **얕은 복사**: 최상위 레벨의 값만 복사, 중첩 객체는 참조 공유
- **이터러블**: 배열, 문자열 등 순회 가능한 객체
- **불변성**: 원본 데이터를 변경하지 않고 새로운 데이터 생성
- **구조 분해**: 복잡한 데이터 구조를 개별 요소로 분해

## 핵심

### 1. 배열에서의 Spread 연산자

#### 기본 사용법
```javascript
// 배열 복사
const originalArray = [1, 2, 3];
const copiedArray = [...originalArray];

console.log(copiedArray); // [1, 2, 3]
console.log(originalArray === copiedArray); // false (다른 참조)
```

#### 배열 조작
```javascript
// 배열 앞에 요소 추가
const numbers = [1, 2, 3];
const newNumbers = [0, ...numbers];
console.log(newNumbers); // [0, 1, 2, 3]

// 배열 뒤에 요소 추가
const moreNumbers = [...numbers, 4, 5];
console.log(moreNumbers); // [1, 2, 3, 4, 5]

// 배열 중간에 요소 삽입
const insertNumbers = [...numbers.slice(0, 1), 1.5, ...numbers.slice(1)];
console.log(insertNumbers); // [1, 1.5, 2, 3]

// 배열 결합
const array1 = [1, 2];
const array2 = [3, 4];
const combined = [...array1, ...array2];
console.log(combined); // [1, 2, 3, 4]
```

#### 얕은 복사의 특성
```javascript
// 원시 타입 요소 - 독립적 복사
const originalArray = [1, 2, 3];
const shallowCopy = [...originalArray];

shallowCopy[0] = 99;
console.log(originalArray); // [1, 2, 3] (원본 변경 없음)
console.log(shallowCopy); // [99, 2, 3]

// 객체 요소 - 참조 공유
const objectArray = [{ a: 1 }, { b: 2 }];
const objectCopy = [...objectArray];

objectCopy[0].a = 99;
console.log(objectArray[0].a); // 99 (원본도 변경됨)
console.log(objectCopy[0].a); // 99
```

### 2. 객체에서의 Spread 연산자

#### 기본 사용법
```javascript
// 객체 복사
const originalObject = { a: 1, b: 2 };
const copiedObject = { ...originalObject };

console.log(copiedObject); // { a: 1, b: 2 }
console.log(originalObject === copiedObject); // false (다른 참조)
```

#### 객체 조작
```javascript
// 속성 추가
const person = { name: 'John', age: 30 };
const personWithCity = { ...person, city: 'Seoul' };
console.log(personWithCity); // { name: 'John', age: 30, city: 'Seoul' }

// 속성 수정
const updatedPerson = { ...person, age: 31 };
console.log(updatedPerson); // { name: 'John', age: 31 }

// 속성 제거 (구조 분해와 함께)
const { age, ...personWithoutAge } = person;
console.log(personWithoutAge); // { name: 'John' }

// 객체 병합
const obj1 = { a: 1, b: 2 };
const obj2 = { c: 3, d: 4 };
const merged = { ...obj1, ...obj2 };
console.log(merged); // { a: 1, b: 2, c: 3, d: 4 }

// 중복 속성 처리 (나중에 오는 값이 우선)
const base = { a: 1, b: 2 };
const override = { b: 3, c: 4 };
const result = { ...base, ...override };
console.log(result); // { a: 1, b: 3, c: 4 }
```

#### 얕은 복사의 특성
```javascript
// 원시 타입 속성 - 독립적 복사
const originalObject = { a: 1, b: 2 };
const shallowCopy = { ...originalObject };

shallowCopy.a = 99;
console.log(originalObject.a); // 1 (원본 변경 없음)
console.log(shallowCopy.a); // 99

// 중첩 객체 - 참조 공유
const nestedObject = { a: 1, b: { c: 2 } };
const nestedCopy = { ...nestedObject };

nestedCopy.b.c = 99;
console.log(nestedObject.b.c); // 99 (원본도 변경됨)
console.log(nestedCopy.b.c); // 99
```

### 3. 함수 인자에서의 Spread 연산자

#### 함수 호출 시 사용
```javascript
// 배열을 개별 인자로 전달
function sum(a, b, c) {
    return a + b + c;
}

const numbers = [1, 2, 3];
const result = sum(...numbers);
console.log(result); // 6

// Math 함수와 함께 사용
const values = [1, 5, 3, 9, 2];
const max = Math.max(...values);
const min = Math.min(...values);
console.log(max); // 9
console.log(min); // 1

// 여러 배열 결합하여 전달
const array1 = [1, 2];
const array2 = [3, 4];
const array3 = [5, 6];
const allNumbers = [...array1, ...array2, ...array3];
console.log(allNumbers); // [1, 2, 3, 4, 5, 6]
```

#### Rest 매개변수와의 차이
```javascript
// Spread 연산자 (함수 호출 시)
function spreadExample(a, b, c) {
    console.log(a, b, c);
}
const args = [1, 2, 3];
spreadExample(...args); // 1 2 3

// Rest 매개변수 (함수 정의 시)
function restExample(...args) {
    console.log(args);
}
restExample(1, 2, 3); // [1, 2, 3]
```

## 예시

### 1. 실제 사용 사례

#### 상태 관리 (React 스타일)
```javascript
// 사용자 정보 업데이트
const user = {
    name: 'John',
    age: 30,
    preferences: {
        theme: 'dark',
        language: 'ko'
    }
};

// 나이만 업데이트
const updatedUser = { ...user, age: 31 };

// 선호도만 업데이트 (얕은 복사 주의)
const userWithNewTheme = {
    ...user,
    preferences: {
        ...user.preferences,
        theme: 'light'
    }
};

console.log(updatedUser.age); // 31
console.log(user.age); // 30 (원본 유지)
console.log(userWithNewTheme.preferences.theme); // 'light'
```

#### 배열 조작
```javascript
// 배열에서 특정 요소 제거
function removeItem(array, index) {
    return [...array.slice(0, index), ...array.slice(index + 1)];
}

const fruits = ['apple', 'banana', 'orange'];
const withoutBanana = removeItem(fruits, 1);
console.log(withoutBanana); // ['apple', 'orange']

// 배열에서 특정 요소 교체
function replaceItem(array, index, newItem) {
    return [...array.slice(0, index), newItem, ...array.slice(index + 1)];
}

const updatedFruits = replaceItem(fruits, 1, 'grape');
console.log(updatedFruits); // ['apple', 'grape', 'orange']
```

### 2. 고급 패턴

#### 조건부 속성 추가
```javascript
// 조건에 따라 속성 추가
function createUser(name, age, isAdmin = false) {
    const user = {
        name,
        age,
        ...(isAdmin && { role: 'admin' }),
        ...(age >= 18 && { canVote: true })
    };
    return user;
}

console.log(createUser('John', 25, true));
// { name: 'John', age: 25, role: 'admin', canVote: true }

console.log(createUser('Jane', 16, false));
// { name: 'Jane', age: 16 }
```

#### 깊은 복사 구현
```javascript
// 간단한 깊은 복사 (제한적)
function deepCopy(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    
    if (Array.isArray(obj)) {
        return obj.map(item => deepCopy(item));
    }
    
    const copied = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            copied[key] = deepCopy(obj[key]);
        }
    }
    return copied;
}

const complexObject = {
    a: 1,
    b: { c: 2, d: [3, 4] },
    e: [5, { f: 6 }]
};

const deepCopied = deepCopy(complexObject);
deepCopied.b.c = 99;
deepCopied.e[1].f = 99;

console.log(complexObject.b.c); // 2 (원본 유지)
console.log(complexObject.e[1].f); // 6 (원본 유지)
console.log(deepCopied.b.c); // 99
console.log(deepCopied.e[1].f); // 99
```

## 운영 팁

### 성능 최적화

#### 메모리 효율성
```javascript
// 큰 배열의 경우 성능 고려
const largeArray = new Array(10000).fill(0);

// 비효율적: 전체 배열 복사
const inefficient = [...largeArray];

// 효율적: 필요한 부분만 복사
const efficient = largeArray.slice(0, 100);

// 조건부 복사
function conditionalCopy(array, shouldCopy = false) {
    return shouldCopy ? [...array] : array;
}
```

### 에러 처리

#### 안전한 Spread 사용
```javascript
// null/undefined 체크
function safeSpread(obj) {
    if (!obj) return {};
    return { ...obj };
}

// 배열 체크
function safeArraySpread(arr) {
    if (!Array.isArray(arr)) return [];
    return [...arr];
}

// 사용 예시
console.log(safeSpread(null)); // {}
console.log(safeArraySpread('not array')); // []
```

### 주의사항

#### 얕은 복사의 한계
```javascript
// 중첩 객체의 참조 공유 문제
const original = {
    user: { name: 'John' },
    settings: { theme: 'dark' }
};

const copy = { ...original };

// 중첩 객체 수정 시 원본도 변경
copy.user.name = 'Jane';
console.log(original.user.name); // 'Jane' (원본 변경됨)

// 해결책: 중첩 객체도 spread
const deepCopy = {
    ...original,
    user: { ...original.user },
    settings: { ...original.settings }
};

deepCopy.user.name = 'Bob';
console.log(original.user.name); // 'Jane' (원본 유지)
console.log(deepCopy.user.name); // 'Bob'
```

## 참고

### Spread 연산자 vs 다른 복사 방법

| 방법 | 얕은 복사 | 깊은 복사 | 성능 | 가독성 |
|------|-----------|-----------|------|--------|
| **Spread 연산자** | ✅ | ❌ | 빠름 | 높음 |
| **Object.assign()** | ✅ | ❌ | 빠름 | 보통 |
| **JSON.parse/stringify** | ❌ | ✅ | 느림 | 보통 |
| **구조 분해** | ✅ | ❌ | 빠름 | 높음 |

### Spread 연산자 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **간단한 복사** | Spread 연산자 사용 | 간결하고 직관적 |
| **객체 병합** | Spread 연산자 사용 | 명확한 우선순위 |
| **배열 조작** | Spread 연산자 사용 | 불변성 유지 |
| **중첩 객체** | 깊은 복사 고려 | 참조 공유 문제 |
| **대용량 데이터** | 부분 복사 고려 | 성능 최적화 |

### 결론
Spread 연산자는 JavaScript에서 데이터를 복사하고 조작하는 강력한 도구입니다.
얕은 복사의 특성을 이해하고 적절한 상황에 사용하세요.
중첩 객체의 경우 참조 공유 문제를 고려하여 깊은 복사를 사용하세요.
함수 인자 전달과 배열/객체 조작에서 매우 유용합니다.
Spread 연산자를 활용하여 불변성을 유지하면서 데이터를 안전하게 조작하세요.
