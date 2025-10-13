---
title: JavaScript 함수형 프로그래밍
tags: [language, javascript, 01기본javascript, function, functional-programming, pure-functions]
updated: 2025-10-13
---

# JavaScript 함수형 프로그래밍

## 함수형 프로그래밍이란?

함수형 프로그래밍(Functional Programming)은 수학적 함수의 개념을 프로그래밍에 적용한 패러다임입니다. 이는 단순히 함수를 많이 사용하는 것이 아니라, **함수를 일급 객체로 취급**하고 **부수 효과(side effects)를 최소화**하여 더 예측 가능하고 안전한 코드를 작성하는 방법론입니다.

### 왜 함수형 프로그래밍을 사용해야 할까?

현대 JavaScript 개발에서 함수형 프로그래밍이 중요한 이유는 다음과 같습니다:

**1. 예측 가능성 (Predictability)**
- 같은 입력에 항상 같은 출력을 보장
- 디버깅과 테스트가 쉬워짐
- 코드의 동작을 추론하기 용이

**2. 안전성 (Safety)**
- 부수 효과로 인한 버그 방지
- 데이터 불변성으로 예상치 못한 변경 차단
- 동시성 프로그래밍에서 안전한 병렬 처리

**3. 재사용성 (Reusability)**
- 작은 순수 함수들의 조합으로 복잡한 로직 구성
- 함수 합성(composition)을 통한 코드 재사용
- 모듈화된 설계로 유지보수성 향상

**4. 성능 최적화**
- 메모이제이션을 통한 계산 결과 캐싱
- 지연 평가로 불필요한 계산 방지
- 컴파일러 최적화에 유리한 구조

### 핵심 원칙

함수형 프로그래밍의 핵심 원칙들을 이해하면 더 나은 코드를 작성할 수 있습니다:

- **순수 함수**: 외부 상태에 의존하지 않고 부수 효과가 없는 함수
- **불변성**: 데이터를 직접 수정하지 않고 새로운 데이터를 생성
- **참조 투명성**: 함수 호출을 그 결과값으로 대체해도 동일한 동작
- **고차 함수**: 함수를 인자로 받거나 함수를 반환하는 함수
- **함수 합성**: 작은 함수들을 조합하여 더 큰 기능을 만드는 것

## 핵심

### 1. 순수 함수 (Pure Functions)

순수 함수는 함수형 프로그래밍의 가장 기본이 되는 개념입니다. **같은 입력에 대해 항상 같은 출력을 반환**하고, **부수 효과(side effects)가 없는** 함수를 말합니다.

#### 순수 함수의 조건

1. **동일한 입력 → 동일한 출력**: 같은 인자를 전달하면 항상 같은 결과를 반환
2. **부수 효과 없음**: 외부 상태를 변경하지 않음
3. **외부 의존성 없음**: 전역 변수나 외부 상태에 의존하지 않음

```javascript
// ✅ 순수 함수들
const add = (a, b) => a + b;
const multiply = (a, b) => a * b;
const formatName = (firstName, lastName) => `${firstName} ${lastName}`;

// ❌ 순수하지 않은 함수들
let counter = 0;
const increment = () => ++counter;  // 외부 상태 변경

const getCurrentTime = () => new Date();  // 매번 다른 결과

const logMessage = (msg) => {
    console.log(msg);  // 부수 효과 (콘솔 출력)
    return msg;
};
```

#### 순수 함수의 실용적 이점

**테스트 용이성**
```javascript
// 순수 함수는 테스트가 간단합니다
const calculateDiscount = (price, discountRate) => 
    price * (1 - discountRate / 100);

// 예측 가능한 결과로 테스트 작성이 쉬움
console.log(calculateDiscount(1000, 10)); // 900
console.log(calculateDiscount(1000, 10)); // 900 (항상 동일)
```

**메모이제이션 가능**
```javascript
// 비용이 큰 계산을 캐싱할 수 있습니다
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
```

### 2. 불변성 (Immutability)

불변성은 데이터를 **직접 수정하지 않고 새로운 데이터를 생성**하는 원칙입니다. 이는 예상치 못한 부작용을 방지하고 코드의 안전성을 크게 향상시킵니다.

#### 왜 불변성이 중요한가?

1. **예측 가능성**: 데이터가 언제 어떻게 변경되는지 명확함
2. **디버깅 용이성**: 변경 이력을 추적하기 쉬움
3. **동시성 안전**: 여러 스레드에서 안전하게 접근 가능
4. **성능 최적화**: 변경 감지와 최적화가 쉬워짐

#### 배열의 불변적 조작

```javascript
// ❌ 가변적 접근 (원본 수정)
const numbers = [1, 2, 3];
numbers.push(4);  // 원본이 변경됨

// ✅ 불변적 접근 (새 배열 생성)
const originalNumbers = [1, 2, 3];
const newNumbers = [...originalNumbers, 4];

// 배열 메서드 활용
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 }
];

// map: 변환
const adultUsers = users.map(user => ({ ...user, isAdult: user.age >= 18 }));

// filter: 필터링
const youngUsers = users.filter(user => user.age < 30);

// find + map: 특정 요소 업데이트
const updatedUsers = users.map(user => 
    user.name === 'Alice' ? { ...user, age: 26 } : user
);
```

#### 객체의 불변적 조작

```javascript
// ❌ 가변적 접근
const person = { name: 'Alice', age: 25 };
person.age = 26;  // 원본 수정

// ✅ 불변적 접근
const originalPerson = { name: 'Alice', age: 25 };
const updatedPerson = { ...originalPerson, age: 26 };

// 중첩 객체 업데이트
const user = {
    name: 'Alice',
    profile: {
        age: 25,
        address: { city: 'Seoul', country: 'Korea' }
    }
};

// 깊은 복사로 중첩 객체 업데이트
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

#### 실용적인 불변성 패턴

```javascript
// 배열에서 요소 제거
const removeItem = (array, index) => [
    ...array.slice(0, index),
    ...array.slice(index + 1)
];

// 객체에서 속성 제거
const removeProperty = (obj, key) => {
    const { [key]: removed, ...rest } = obj;
    return rest;
};

// 조건부 업데이트
const updateIf = (condition, updater) => (obj) => 
    condition(obj) ? updater(obj) : obj;
```

### 3. 고차 함수 (Higher-Order Functions)

고차 함수는 **함수를 인자로 받거나 함수를 반환하는 함수**입니다. 이는 함수형 프로그래밍의 핵심 도구로, 코드의 재사용성과 추상화를 크게 향상시킵니다.

#### 함수를 인자로 받는 고차 함수

JavaScript의 배열 메서드들이 대표적인 고차 함수입니다:

```javascript
const numbers = [1, 2, 3, 4, 5];

// map: 각 요소를 변환
const doubled = numbers.map(x => x * 2);
const squared = numbers.map(x => x * x);

// filter: 조건에 맞는 요소만 선택
const evens = numbers.filter(x => x % 2 === 0);
const largeNumbers = numbers.filter(x => x > 3);

// reduce: 배열을 단일 값으로 축약
const sum = numbers.reduce((acc, x) => acc + x, 0);
const max = numbers.reduce((acc, x) => Math.max(acc, x), -Infinity);

// find: 조건에 맞는 첫 번째 요소 찾기
const firstEven = numbers.find(x => x % 2 === 0);

// some/every: 조건 검사
const hasEven = numbers.some(x => x % 2 === 0);
const allPositive = numbers.every(x => x > 0);
```

#### 함수를 반환하는 고차 함수

**커링(Currying)**
```javascript
// 다중 인자를 받는 함수를 단일 인자를 받는 함수들의 체인으로 변환
const multiply = (x) => (y) => x * y;
const multiplyByTwo = multiply(2);
const multiplyByTen = multiply(10);

// 실용적인 예시
const createValidator = (minLength) => (text) => text.length >= minLength;
const isLongEnough = createValidator(8);
const isShortEnough = createValidator(3);
```

**부분 적용(Partial Application)**
```javascript
// 함수의 일부 인자를 미리 고정
const partial = (fn, ...fixedArgs) => (...remainingArgs) => 
    fn(...fixedArgs, ...remainingArgs);

const add = (a, b, c) => a + b + c;
const addFive = partial(add, 5);
const addFiveAndThree = partial(add, 5, 3);

console.log(addFive(2, 1)); // 8
console.log(addFiveAndThree(2)); // 10
```

**데코레이터 패턴**
```javascript
// 함수에 기능을 추가하는 래퍼
const withLogging = (fn) => (...args) => {
    console.log(`Calling ${fn.name} with:`, args);
    const result = fn(...args);
    console.log(`Result:`, result);
    return result;
};

const withTiming = (fn) => (...args) => {
    const start = Date.now();
    const result = fn(...args);
    console.log(`Execution time: ${Date.now() - start}ms`);
    return result;
};

// 조합 가능한 데코레이터
const add = (a, b) => a + b;
const enhancedAdd = withTiming(withLogging(add));
```

### 4. 함수 합성 (Function Composition)

함수 합성은 **작은 함수들을 조합하여 더 큰 기능을 만드는** 함수형 프로그래밍의 핵심 기법입니다. 이는 복잡한 로직을 작고 재사용 가능한 함수들로 분해하여 관리하기 쉽게 만듭니다.

#### 함수 합성의 원리

함수 합성은 수학의 합성함수 개념과 동일합니다:
- `f(x) = x + 1`
- `g(x) = x * 2`
- `(g ∘ f)(x) = g(f(x)) = (x + 1) * 2`

```javascript
// 기본 함수들
const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

// 수동 합성 (가독성이 떨어짐)
const complexOperation = x => square(double(addOne(x)));
console.log(complexOperation(3)); // ((3 + 1) * 2)² = 64
```

#### compose와 pipe 유틸리티

**compose (오른쪽에서 왼쪽으로 실행)**
```javascript
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

const composed = compose(square, double, addOne);
console.log(composed(3)); // 64
```

**pipe (왼쪽에서 오른쪽으로 실행)**
```javascript
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const piped = pipe(addOne, double, square);
console.log(piped(3)); // 64
```

#### 실용적인 함수 합성 예시

**데이터 처리 파이프라인**
```javascript
const users = [
    { name: 'Alice', age: 25, city: 'Seoul' },
    { name: 'Bob', age: 30, city: 'Busan' },
    { name: 'Charlie', age: 35, city: 'Seoul' }
];

// 작은 순수 함수들
const filterByCity = (city) => (users) => 
    users.filter(user => user.city === city);

const filterAdults = (users) => 
    users.filter(user => user.age >= 30);

const getNames = (users) => 
    users.map(user => user.name);

const joinWithComma = (names) => 
    names.join(', ');

const addPrefix = (prefix) => (text) => 
    `${prefix}: ${text}`;

// 함수 합성으로 파이프라인 구성
const getAdultNamesInSeoul = pipe(
    filterByCity('Seoul'),
    filterAdults,
    getNames,
    joinWithComma,
    addPrefix('Adults in Seoul')
);

console.log(getAdultNamesInSeoul(users)); // "Adults in Seoul: Charlie"
```

**유효성 검사 체인**
```javascript
const isString = (value) => typeof value === 'string';
const isNotEmpty = (value) => value.length > 0;
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

const validate = (...validators) => (value) => 
    validators.every(validator => validator(value));

const validateEmail = validate(isString, isNotEmpty, isEmail);

console.log(validateEmail('test@example.com')); // true
console.log(validateEmail('invalid')); // false
```

## 실전 활용 예시

### 1. E-commerce 주문 처리 시스템

```javascript
const orders = [
    { id: 1, amount: 100, status: 'pending', customer: 'Alice' },
    { id: 2, amount: 200, status: 'completed', customer: 'Bob' },
    { id: 3, amount: 150, status: 'pending', customer: 'Charlie' },
    { id: 4, amount: 300, status: 'completed', customer: 'Alice' }
];

// 순수 함수들
const filterByStatus = (status) => (orders) => 
    orders.filter(order => order.status === status);

const filterByCustomer = (customer) => (orders) => 
    orders.filter(order => order.customer === customer);

const calculateTotal = (orders) => 
    orders.reduce((sum, order) => sum + order.amount, 0);

const formatCurrency = (amount) => `$${amount.toFixed(2)}`;

const getOrderCount = (orders) => orders.length;

// 함수 합성으로 비즈니스 로직 구성
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const getCompletedOrdersTotal = pipe(
    filterByStatus('completed'),
    calculateTotal,
    formatCurrency
);

const getCustomerPendingCount = (customer) => pipe(
    filterByCustomer(customer),
    filterByStatus('pending'),
    getOrderCount
);

console.log(getCompletedOrdersTotal(orders)); // "$500.00"
console.log(getCustomerPendingCount('Alice')(orders)); // 1
```

### 2. 사용자 입력 검증 시스템

```javascript
// 검증 함수들
const isString = (value) => typeof value === 'string';
const isNotEmpty = (value) => value.length > 0;
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const isMinLength = (min) => (value) => value.length >= min;
const hasUpperCase = (value) => /[A-Z]/.test(value);
const hasNumber = (value) => /\d/.test(value);

// 검증 결과 타입
const ValidationResult = {
    success: (value) => ({ isValid: true, value, errors: [] }),
    failure: (errors) => ({ isValid: false, value: null, errors })
};

// 검증 체인 생성기
const createValidator = (...validators) => (value) => {
    const errors = validators
        .filter(validator => !validator(value))
        .map(validator => validator.message || 'Validation failed');
    
    return errors.length === 0 
        ? ValidationResult.success(value)
        : ValidationResult.failure(errors);
};

// 특정 검증 규칙들
const validateEmail = createValidator(
    isString,
    isNotEmpty,
    isEmail
);

const validatePassword = createValidator(
    isString,
    isMinLength(8),
    hasUpperCase,
    hasNumber
);

// 사용 예시
console.log(validateEmail('user@example.com')); // { isValid: true, ... }
console.log(validatePassword('Weak123')); // { isValid: true, ... }
```

### 3. 고급 패턴: 모나드와 에러 처리

#### Maybe 모나드로 안전한 접근
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

// 안전한 중첩 객체 접근
const getCity = (user) => 
    Maybe.fromNullable(user)
        .map(u => u.address)
        .map(addr => addr.city)
        .getOrElse('Unknown');

console.log(getCity({ address: { city: 'Seoul' } })); // "Seoul"
console.log(getCity(null)); // "Unknown"
```

#### Either 모나드로 에러 처리
```javascript
const Either = {
    left: (error) => ({
        map: () => Either.left(error),
        fold: (onError, onSuccess) => onError(error)
    }),
    
    right: (value) => ({
        map: (fn) => Either.right(fn(value)),
        fold: (onError, onSuccess) => onSuccess(value)
    })
};

const safeDivide = (a, b) => 
    b === 0 ? Either.left('Division by zero') : Either.right(a / b);

const result = safeDivide(10, 2)
    .map(x => x * 2)
    .fold(
        error => `Error: ${error}`,
        value => `Result: ${value}`
    );
```

## 성능 최적화와 모범 사례

### 1. 메모이제이션으로 성능 향상

```javascript
// 간단한 메모이제이션 구현
const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        return cache.has(key) ? cache.get(key) : cache.set(key, fn(...args)).get(key);
    };
};

// 비용이 큰 계산에 적용
const fibonacci = memoize((n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
});

console.log(fibonacci(40)); // 빠른 계산
```

### 2. 지연 평가로 메모리 효율성

```javascript
// 제너레이터를 활용한 지연 평가
function* range(start, end) {
    for (let i = start; i <= end; i++) yield i;
}

function* map(iterable, fn) {
    for (const item of iterable) yield fn(item);
}

function* filter(iterable, predicate) {
    for (const item of iterable) {
        if (predicate(item)) yield item;
    }
}

// 대용량 데이터도 메모리 효율적으로 처리
const numbers = range(1, 1000000);
const doubled = map(numbers, x => x * 2);
const evens = filter(doubled, x => x % 2 === 0);

// 필요한 만큼만 계산
const firstFive = Array.from({ length: 5 }, () => evens.next().value);
```

### 3. 함수형 프로그래밍 모범 사례

**작은 순수 함수로 분해**
```javascript
// ❌ 복잡한 함수
const processUserData = (users) => {
    return users
        .filter(user => user.age >= 18)
        .map(user => ({ ...user, isAdult: true }))
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(user => user.name.toUpperCase());
};

// ✅ 작은 순수 함수들로 분해
const isAdult = (user) => user.age >= 18;
const addAdultFlag = (user) => ({ ...user, isAdult: true });
const sortByName = (users) => [...users].sort((a, b) => a.name.localeCompare(b.name));
const getName = (user) => user.name;
const toUpperCase = (str) => str.toUpperCase();

const processUserData = (users) => 
    users
        .filter(isAdult)
        .map(addAdultFlag)
        .pipe(sortByName)
        .map(getName)
        .map(toUpperCase);
```

**에러 처리 패턴**
```javascript
// Try-Catch 대신 Either 패턴 사용
const safeJsonParse = (jsonString) => {
    try {
        return Either.right(JSON.parse(jsonString));
    } catch (error) {
        return Either.left(`JSON Parse Error: ${error.message}`);
    }
};

const result = safeJsonParse('{"name": "Alice"}')
    .map(data => data.name)
    .fold(
        error => console.error(error),
        name => console.log(`Hello, ${name}!`)
    );
```

## 함수형 vs 명령형 프로그래밍

| 측면 | 함수형 프로그래밍 | 명령형 프로그래밍 |
|------|-------------------|-------------------|
| **사고 방식** | "무엇을" 할지 선언 | "어떻게" 할지 명령 |
| **상태 관리** | 불변성 유지 | 가변 상태 허용 |
| **부수 효과** | 최소화/제거 | 자유롭게 허용 |
| **테스트** | 순수 함수로 쉬움 | 복잡한 상태로 어려움 |
| **병렬 처리** | 안전함 | 동기화 필요 |
| **디버깅** | 예측 가능 | 추적 어려움 |

## 추천 라이브러리

### 핵심 라이브러리
- **Ramda**: 함수형 유틸리티의 완전한 세트
- **Lodash/fp**: Lodash의 함수형 버전
- **Immutable.js**: 불변 데이터 구조
- **Folktale**: 모나드와 함수형 자료구조

### 실무 적용 팁
```javascript
// Ramda 예시
import R from 'ramda';

const users = [
    { name: 'Alice', age: 25, city: 'Seoul' },
    { name: 'Bob', age: 30, city: 'Busan' }
];

const getAdultNamesInSeoul = R.pipe(
    R.filter(R.propEq('city', 'Seoul')),
    R.filter(R.propSatisfies(R.gte(R.__, 18), 'age')),
    R.map(R.prop('name'))
);

console.log(getAdultNamesInSeoul(users)); // ['Alice']
```

## 마무리

함수형 프로그래밍은 JavaScript 개발에서 **코드의 품질과 안정성을 크게 향상**시킬 수 있는 강력한 패러다임입니다. 

### 핵심 포인트
1. **순수 함수**로 예측 가능한 코드 작성
2. **불변성**으로 안전한 데이터 처리  
3. **고차 함수**로 재사용 가능한 로직 구성
4. **함수 합성**으로 복잡한 문제를 작은 단위로 분해
5. **모나드 패턴**으로 안전한 에러 처리

### 실무 적용 가이드
- 기존 코드를 한 번에 바꾸지 말고 **점진적으로 적용**
- 작은 순수 함수부터 시작하여 **점차 복잡한 로직으로 확장**
- 팀 내에서 **함수형 프로그래밍 컨벤션** 정립
- 적절한 **라이브러리 활용**으로 개발 효율성 향상

함수형 프로그래밍은 단순히 새로운 문법을 배우는 것이 아니라, **문제를 해결하는 새로운 사고방식**을 익히는 것입니다. 처음에는 어려울 수 있지만, 익숙해지면 더 안전하고 유지보수하기 쉬운 코드를 작성할 수 있게 됩니다.

---

**참고 자료**
- [MDN - 함수형 프로그래밍](https://developer.mozilla.org/ko/docs/Glossary/Functional_programming)
- [Ramda 공식 문서](https://ramdajs.com/)
- [Mostly Adequate Guide to Functional Programming](https://github.com/MostlyAdequate/mostly-adequate-guide)
- [Functional-Light JavaScript](https://github.com/getify/Functional-Light-JS)

