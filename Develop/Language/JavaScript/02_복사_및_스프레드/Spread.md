---
title: JavaScript Spread 연산자 개념과 사용법
tags: [language, javascript]
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

"얕은 복사"라는 말이 중첩 객체만 가리키는 것으로 읽히기 쉬운데, 실제로 잃는 것이 더 있다. 스프레드가 옮기는 것은 **자기 소유의 열거 가능한 속성값**뿐이다. 프로토타입은 따라오지 않는다.

```javascript
class P {
  constructor(n) { this.name = n; }
  get upper() { return this.name.toUpperCase(); }
  greet() { return 'hi'; }
}

const copy = { ...new P('john') };
copy;                     // { name: 'john' }
typeof copy.greet;        // 'undefined'   ← 메서드가 사라졌다
'upper' in copy;          // false          ← getter 도 사라졌다
```

클래스 메서드와 getter 는 프로토타입에 있어서 하나도 넘어오지 않는다. 인스턴스를 스프레드한 순간 그것은 더 이상 그 클래스가 아니라 일반 객체다. `instanceof` 도 당연히 실패한다.

**객체 자신이 가진 getter 는 반대로 위험하다.** 값으로 굳어 버린다.

```javascript
const src = { _v: 1, get v() { return this._v * 10; } };
const c = { ...src };

src._v = 5;
src.v;    // 50   ← 다시 계산된다
c.v;      // 10   ← 복사한 순간의 값에 멈춰 있다
```

`c.v` 는 getter 가 아니라 그냥 숫자 `10` 이다. 원본을 아무리 바꿔도 따라오지 않는다. 계산 속성을 가진 설정 객체를 스프레드로 복사하면 이 시점에 계산이 한 번 일어나고 그대로 얼어붙는다.

`Object.assign(target, src)` 와도 다르다. `assign` 은 **대상의 setter 를 호출**하지만 스프레드는 새 객체에 값을 직접 정의한다.

```javascript
const target = { set x(v) { console.log('setter 호출:', v); } };

Object.assign(target, { x: 1 });   // 'setter 호출: 1'
const r = { ...target, x: 1 };     // setter 호출 없음. r 은 { x: 1 }
```

둘을 바꿔 쓰면 검증 로직이 걸린 setter 가 조용히 건너뛰어진다.

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

`Math.max(...values)` 는 배열이 작을 때만 쓸 수 있다. 스프레드로 넘긴 값은 전부 **개별 인자**가 되고, 인자 개수에는 엔진 한계가 있다.

```javascript
const big = new Array(200000).fill(1);
Math.max(...big);
// RangeError: Maximum call stack size exceeded
```

에러가 나는 경계는 엔진과 그때의 스택 상황에 따라 달라진다. 개발 중 1,000건으로 테스트할 때는 멀쩡하다가 운영에서 데이터가 늘면 터지는 전형적인 형태다. `values.reduce((a, b) => Math.max(a, b), -Infinity)` 는 인자 개수를 늘리지 않으니 이 한계가 없다.

빈 배열도 조심해야 한다.

```javascript
Math.max(...[]);   // -Infinity
Math.min(...[]);   //  Infinity
```

`0` 이나 `NaN` 이 아니라 무한대다. 최댓값 자리에 `-Infinity` 가 들어가면 이후 비교가 전부 통과해 버려서, 조회 결과가 비었을 때만 이상 동작하는 코드가 된다.

스프레드가 인자를 만들 때 문자열이 섞여도 조용히 넘어간다. 문자열은 이터러블이라 글자 단위로 펼쳐진다.

```javascript
[...'a👍b'];         // ['a', '👍', 'b']   — 코드 포인트 단위
'a👍b'.split('');    // ['a', '\ud83d', '\udc4d', 'b']  — 서로게이트가 쪼개진다
'a👍b'.length;       // 4
```

이모지나 한자 확장 영역이 들어간 문자열을 다룰 때는 `split('')` 보다 스프레드가 안전하다. 다만 스프레드도 만능은 아니어서, 결합 문자나 여러 코드 포인트로 이뤄진 이모지(가족 이모지 등)는 여전히 여러 조각으로 나뉜다.

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

이 패턴이 동작하는 이유는 **객체 스프레드가 어떤 값을 넣어도 던지지 않기** 때문이다.

```javascript
{...null}       // {}
{...undefined}  // {}
{...false}      // {}
{...5}          // {}
```

조건이 falsy 면 그 falsy 값 자체가 스프레드되는데, 원시값에는 자기 소유 열거 속성이 없어서 아무것도 안 붙는다. 우연히 맞아떨어지는 동작이다.

우연이 깨지는 값이 하나 있다. **문자열**이다.

```javascript
const name = 'ab';
({ a: 1, ...(name && { x: 1 }) });   // { a: 1, x: 1 }   의도대로
({ a: 1, ...(name && name) });       // { '0': 'a', '1': 'b', a: 1 }   ← 글자가 키가 됐다
```

조건 자리에 문자열이 들어가고 오른쪽을 실수로 빠뜨리면 인덱스 키가 객체에 박힌다. 에러 없이 이상한 객체가 만들어져서 나중에 직렬화 결과를 보고서야 알게 된다.

배열 스프레드는 이렇게 관대하지 않다.

```javascript
[...null];   // TypeError: null is not iterable
```

그래서 문서 아래쪽 `safeSpread` 의 `if (!obj) return {}` 는 사실 필요 없고(`{...null}` 이 이미 `{}` 다), `safeArraySpread` 의 검사는 꼭 필요하다. 두 함수가 대칭으로 보이지만 위험도는 다르다.

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

"제한적"이라는 단서가 붙어 있는데, 그 제한이 어디까지인지가 중요하다. 이 `deepCopy` 는 **평범한 객체와 배열, 원시값만** 다룬다. 나머지는 조용히 빈 객체가 된다.

```javascript
const src = {
  when: new Date('2020-01-01'),
  re:   /ab+/g,
  m:    new Map([['k', 1]]),
  s:    new Set([1, 2])
};
const out = deepCopy(src);

out.when;                    // {}    ← 날짜가 사라졌다
out.when instanceof Date;    // false
out.re;                      // {}
out.m.size;                  // undefined
```

`typeof new Date() === 'object'` 이고 `Array.isArray` 도 아니니 마지막 분기로 떨어져 속성을 훑는데, `Date` 는 값을 내부 슬롯에 들고 있어서 열거할 속성이 하나도 없다. 그래서 `{}` 가 나온다. 에러도 경고도 없다. **API 응답을 복사하다 날짜 필드만 빈 객체가 되는 사고**가 여기서 나온다.

순환 참조는 더 직접적으로 터진다.

```javascript
const circ = { name: 'a' };
circ.self = circ;
deepCopy(circ);
// RangeError: Maximum call stack size exceeded
```

트리 구조에 부모 참조를 넣어 두었거나 DOM 노드가 섞이면 바로 만난다.

지금은 손으로 짤 이유가 별로 없다. `structuredClone` 이 이 셋을 다 처리한다.

```javascript
const sc = structuredClone({ when: new Date('2020-01-01'), m: new Map([['k', 1]]) });
sc.when instanceof Date;   // true
sc.m.size;                 // 1

const c = { n: 1 }; c.self = c;
structuredClone(c).self.n; // 1  — 순환 참조도 그대로 복원한다
```

대신 함수는 복사하지 못하고 예외를 던진다(`DOMException`). `JSON.parse(JSON.stringify(...))` 가 함수와 `undefined` 를 조용히 버리는 것과 반대다 — **못 하는 일을 소리 내서 알려주는 쪽**이 대체로 낫다.

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
