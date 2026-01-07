---
title: JavaScript 함수형 프로그래밍
tags: [language, javascript, 01기본javascript, function, functional-programming, pure-functions]
updated: 2025-10-13
---

# JavaScript 함수형 프로그래밍

## 정의

함수형 프로그래밍(Functional Programming)은 수학적 함수의 개념을 프로그래밍에 적용한 패러다임입니다. 함수를 일급 객체로 취급하고 부수 효과(side effects)를 최소화하여 더 예측 가능하고 안전한 코드를 작성하는 방법론입니다.

### 핵심 원칙

- **순수 함수**: 외부 상태에 의존하지 않고 부수 효과가 없는 함수
- **불변성**: 데이터를 직접 수정하지 않고 새로운 데이터를 생성
- **참조 투명성**: 함수 호출을 그 결과값으로 대체해도 동일한 동작
- **고차 함수**: 함수를 인자로 받거나 함수를 반환하는 함수
- **함수 합성**: 작은 함수들을 조합하여 더 큰 기능을 만드는 것

## 동작 원리

### 순수 함수 (Pure Functions)

순수 함수는 같은 입력에 대해 항상 같은 출력을 반환하고, 부수 효과가 없는 함수입니다.

```javascript
// 순수 함수
const add = (a, b) => a + b;
const multiply = (a, b) => a * b;
const formatName = (firstName, lastName) => `${firstName} ${lastName}`;

// 순수하지 않은 함수
let counter = 0;
const increment = () => ++counter;  // 외부 상태 변경

const getCurrentTime = () => new Date();  // 매번 다른 결과

const logMessage = (msg) => {
    console.log(msg);  // 부수 효과 (콘솔 출력)
    return msg;
};
```

### 불변성 (Immutability)

데이터를 직접 수정하지 않고 새로운 데이터를 생성합니다.

```javascript
// 배열의 불변적 조작
const numbers = [1, 2, 3];
const newNumbers = [...numbers, 4]; // 원본 유지

const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 }
];

// map: 변환
const adultUsers = users.map(user => ({ ...user, isAdult: user.age >= 18 }));

// filter: 필터링
const youngUsers = users.filter(user => user.age < 30);

// 객체의 불변적 조작
const person = { name: 'Alice', age: 25 };
const updatedPerson = { ...person, age: 26 }; // 새 객체 생성

// 중첩 객체 업데이트
const user = {
    name: 'Alice',
    profile: {
        age: 25,
        address: { city: 'Seoul', country: 'Korea' }
    }
};

const updatedUser = {
    ...user,
    profile: {
        ...user.profile,
        address: {
            ...user.profile.address,
            city: 'Busan'
        }
    }
};
```

### 고차 함수 (Higher-Order Functions)

함수를 인자로 받거나 함수를 반환하는 함수입니다.

```javascript
const numbers = [1, 2, 3, 4, 5];

// 함수를 인자로 받는 고차 함수
const doubled = numbers.map(x => x * 2);
const evens = numbers.filter(x => x % 2 === 0);
const sum = numbers.reduce((acc, x) => acc + x, 0);

// 함수를 반환하는 고차 함수 (커링)
const multiply = (x) => (y) => x * y;
const multiplyByTwo = multiply(2);
const multiplyByTen = multiply(10);

console.log(multiplyByTwo(5)); // 10
console.log(multiplyByTen(5)); // 50

// 부분 적용
const partial = (fn, ...fixedArgs) => (...remainingArgs) => 
    fn(...fixedArgs, ...remainingArgs);

const add = (a, b, c) => a + b + c;
const addFive = partial(add, 5);
console.log(addFive(2, 1)); // 8
```

### 함수 합성 (Function Composition)

작은 함수들을 조합하여 더 큰 기능을 만듭니다.

```javascript
// compose: 오른쪽에서 왼쪽으로 실행
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

// pipe: 왼쪽에서 오른쪽으로 실행
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

const piped = pipe(addOne, double, square);
console.log(piped(3)); // ((3 + 1) * 2)² = 64
```

## 사용법

### 데이터 처리 파이프라인

```javascript
const users = [
    { name: 'Alice', age: 25, city: 'Seoul' },
    { name: 'Bob', age: 30, city: 'Busan' },
    { name: 'Charlie', age: 35, city: 'Seoul' }
];

const filterByCity = (city) => (users) => 
    users.filter(user => user.city === city);

const filterAdults = (users) => 
    users.filter(user => user.age >= 30);

const getNames = (users) => 
    users.map(user => user.name);

const joinWithComma = (names) => 
    names.join(', ');

const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const getAdultNamesInSeoul = pipe(
    filterByCity('Seoul'),
    filterAdults,
    getNames,
    joinWithComma
);

console.log(getAdultNamesInSeoul(users)); // "Charlie"
```

### 유효성 검사

```javascript
const isString = (value) => typeof value === 'string';
const isNotEmpty = (value) => value.length > 0;
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const isMinLength = (min) => (value) => value.length >= min;

const validate = (...validators) => (value) => 
    validators.every(validator => validator(value));

const validateEmail = validate(isString, isNotEmpty, isEmail);
const validatePassword = validate(isString, isMinLength(8));

console.log(validateEmail('test@example.com')); // true
console.log(validatePassword('password123')); // true
```

## 예제

### E-commerce 주문 처리

```javascript
const orders = [
    { id: 1, amount: 100, status: 'pending', customer: 'Alice' },
    { id: 2, amount: 200, status: 'completed', customer: 'Bob' },
    { id: 3, amount: 150, status: 'pending', customer: 'Charlie' }
];

const filterByStatus = (status) => (orders) => 
    orders.filter(order => order.status === status);

const calculateTotal = (orders) => 
    orders.reduce((sum, order) => sum + order.amount, 0);

const formatCurrency = (amount) => `$${amount.toFixed(2)}`;

const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const getCompletedOrdersTotal = pipe(
    filterByStatus('completed'),
    calculateTotal,
    formatCurrency
);

console.log(getCompletedOrdersTotal(orders)); // "$200.00"
```

### 에러 처리 (Maybe 모나드)

```javascript
const Maybe = {
    just: (value) => ({
        map: (fn) => Maybe.just(fn(value)),
        getOrElse: (defaultValue) => value
    }),
    
    nothing: () => ({
        map: () => Maybe.nothing(),
        getOrElse: (defaultValue) => defaultValue
    }),
    
    fromNullable: (value) => 
        value == null ? Maybe.nothing() : Maybe.just(value)
};

const getCity = (user) => 
    Maybe.fromNullable(user)
        .map(u => u.address)
        .map(addr => addr.city)
        .getOrElse('Unknown');

console.log(getCity({ address: { city: 'Seoul' } })); // "Seoul"
console.log(getCity(null)); // "Unknown"
```

### 메모이제이션

```javascript
const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        return cache.has(key) ? cache.get(key) : cache.set(key, fn(...args)).get(key);
    };
};

const fibonacci = memoize((n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
});

console.log(fibonacci(40)); // 빠른 계산
```

## 참고

### 함수형 vs 명령형

| 측면 | 함수형 프로그래밍 | 명령형 프로그래밍 |
|------|-------------------|-------------------|
| 사고 방식 | "무엇을" 할지 선언 | "어떻게" 할지 명령 |
| 상태 관리 | 불변성 유지 | 가변 상태 허용 |
| 부수 효과 | 최소화/제거 | 자유롭게 허용 |
| 테스트 | 순수 함수로 쉬움 | 복잡한 상태로 어려움 |

### 추천 라이브러리

- **Ramda**: 함수형 유틸리티의 완전한 세트
- **Lodash/fp**: Lodash의 함수형 버전
- **Immutable.js**: 불변 데이터 구조
- **Folktale**: 모나드와 함수형 자료구조

### 실무 적용 가이드

- 기존 코드를 한 번에 바꾸지 말고 점진적으로 적용
- 작은 순수 함수부터 시작하여 점차 복잡한 로직으로 확장
- 팀 내에서 함수형 프로그래밍 컨벤션 정립
- 적절한 라이브러리 활용으로 개발 효율성 향상

**참고 자료**
- [MDN - 함수형 프로그래밍](https://developer.mozilla.org/ko/docs/Glossary/Functional_programming)
- [Ramda 공식 문서](https://ramdajs.com/)
- [Mostly Adequate Guide to Functional Programming](https://github.com/MostlyAdequate/mostly-adequate-guide)
