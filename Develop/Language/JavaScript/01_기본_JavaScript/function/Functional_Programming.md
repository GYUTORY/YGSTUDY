---
title: JavaScript 함수형 프로그래밍 패턴
tags: [language, javascript, 01기본javascript, function, functional-programming, pure-functions]
updated: 2025-08-10
---

# JavaScript 함수형 프로그래밍 패턴

## 배경

함수형 프로그래밍은 순수 함수, 불변성, 참조 투명성 등의 핵심 원칙을 기반으로 하는 프로그래밍 패러다임입니다. JavaScript에서 함수형 프로그래밍을 적용하면 코드의 가독성과 유지보수성을 크게 향상시킬 수 있습니다.

### 함수형 프로그래밍의 필요성
- **코드 가독성**: 선언적이고 명확한 코드 작성
- **부수 효과 제거**: 예측 가능한 함수 동작
- **테스트 용이성**: 순수 함수의 쉬운 테스트
- **병렬 처리**: 부수 효과 없는 함수의 안전한 병렬 실행

### 기본 개념
- **순수 함수**: 동일한 입력에 대해 항상 동일한 출력을 반환하는 함수
- **불변성**: 데이터를 직접 수정하지 않고 새로운 데이터를 생성
- **참조 투명성**: 함수 호출을 그 결과값으로 대체 가능한 특성
- **고차 함수**: 함수를 인자로 받거나 함수를 반환하는 함수

## 핵심

### 1. 순수 함수 (Pure Functions)

#### 순수 함수의 특징
```javascript
// 순수 함수의 예
const add = (a, b) => a + b;
const multiply = (a, b) => a * b;
const square = x => x * x;

// 순수 함수는 항상 동일한 결과를 반환
console.log(add(2, 3)); // 5
console.log(add(2, 3)); // 5 (항상 동일)

// 부수 효과가 있는 함수 (순수하지 않음)
let total = 0;
const addToTotal = (x) => {
    total += x;  // 외부 상태를 변경
    return total;
};

console.log(addToTotal(5)); // 5
console.log(addToTotal(5)); // 10 (다른 결과)
```

#### 순수 함수의 장점
```javascript
// 테스트하기 쉬운 순수 함수
const calculateTax = (income, rate) => income * (rate / 100);

// 테스트 케이스
console.log(calculateTax(1000, 10) === 100); // true
console.log(calculateTax(2000, 15) === 300); // true

// 캐싱 가능한 순수 함수
const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        if (cache.has(key)) {
            return cache.get(key);
        }
        const result = fn(...args);
        cache.set(key, result);
        return result;
    };
};

const expensiveCalculation = memoize((n) => {
    console.log('계산 중...');
    return n * n;
});

console.log(expensiveCalculation(5)); // 계산 중... 25
console.log(expensiveCalculation(5)); // 25 (캐시된 결과)
```

### 2. 불변성 (Immutability)

#### 배열의 불변성
```javascript
// 가변적(mutable) 접근
const numbers = [1, 2, 3];
numbers.push(4);  // 원본 배열 수정
console.log(numbers); // [1, 2, 3, 4]

// 불변적(immutable) 접근
const originalNumbers = [1, 2, 3];
const newNumbers = [...originalNumbers, 4];  // 새 배열 생성
console.log(originalNumbers); // [1, 2, 3] (원본 유지)
console.log(newNumbers); // [1, 2, 3, 4]

// 배열 메서드의 불변적 사용
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 }
];

// map을 사용한 불변적 업데이트
const updatedUsers = users.map(user => 
    user.name === 'Alice' 
        ? { ...user, age: 26 }
        : user
);

console.log(users); // 원본 유지
console.log(updatedUsers); // Alice의 나이가 26으로 변경된 새 배열
```

#### 객체의 불변성
```javascript
// 가변적 객체 수정
const person = { name: 'Alice', age: 25 };
person.age = 26;  // 원본 객체 수정

// 불변적 객체 수정
const originalPerson = { name: 'Alice', age: 25 };
const updatedPerson = { ...originalPerson, age: 26 };

console.log(originalPerson); // { name: 'Alice', age: 25 }
console.log(updatedPerson); // { name: 'Alice', age: 26 }

// 중첩 객체의 불변적 업데이트
const user = {
    name: 'Alice',
    address: {
        city: 'Seoul',
        country: 'Korea'
    }
};

const updatedUser = {
    ...user,
    address: {
        ...user.address,
        city: 'Busan'
    }
};

console.log(user.address.city); // 'Seoul'
console.log(updatedUser.address.city); // 'Busan'
```

### 3. 고차 함수 (Higher-Order Functions)

#### 함수를 인자로 받는 고차 함수
```javascript
// 배열 처리 고차 함수들
const numbers = [1, 2, 3, 4, 5];

// map: 각 요소를 변환
const doubled = numbers.map(x => x * 2);
console.log(doubled); // [2, 4, 6, 8, 10]

// filter: 조건에 맞는 요소만 선택
const evens = numbers.filter(x => x % 2 === 0);
console.log(evens); // [2, 4]

// reduce: 배열을 단일 값으로 축약
const sum = numbers.reduce((acc, x) => acc + x, 0);
console.log(sum); // 15

// 커스텀 고차 함수
const forEach = (array, fn) => {
    for (let i = 0; i < array.length; i++) {
        fn(array[i], i, array);
    }
};

forEach(numbers, (num, index) => {
    console.log(`Index ${index}: ${num}`);
});
```

#### 함수를 반환하는 고차 함수
```javascript
// 커링(Currying) 패턴
const multiply = (x) => (y) => x * y;
const multiplyByTwo = multiply(2);
const multiplyByTen = multiply(10);

console.log(multiplyByTwo(5)); // 10
console.log(multiplyByTen(5)); // 50

// 부분 적용(Partial Application)
const add = (a, b, c) => a + b + c;
const partial = (fn, ...args) => (...moreArgs) => fn(...args, ...moreArgs);

const addFive = partial(add, 5);
console.log(addFive(3, 2)); // 10

// 로깅 래퍼 함수
const withLogging = (fn) => (...args) => {
    console.log(`Calling ${fn.name} with:`, args);
    const result = fn(...args);
    console.log(`Result:`, result);
    return result;
};

const addWithLogging = withLogging(add);
addWithLogging(1, 2, 3); // 로깅과 함께 실행
```

### 4. 함수 합성 (Function Composition)

#### 기본 함수 합성
```javascript
// 기본적인 함수 합성
const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

// 수동 합성
const addOneAndDouble = x => double(addOne(x));
const addOneDoubleAndSquare = x => square(double(addOne(x)));

console.log(addOneAndDouble(3)); // 8
console.log(addOneDoubleAndSquare(3)); // 64
```

#### 고급 함수 합성
```javascript
// compose: 오른쪽에서 왼쪽으로 실행
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

// pipe: 왼쪽에서 오른쪽으로 실행
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

// compose 사용
const composed = compose(square, double, addOne);
console.log(composed(3)); // ((3 + 1) * 2)² = 64

// pipe 사용
const piped = pipe(addOne, double, square);
console.log(piped(3)); // ((3 + 1) * 2)² = 64

// 실용적인 예시
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 },
    { name: 'Charlie', age: 35 }
];

const getNames = users => users.map(user => user.name);
const filterAdults = users => users.filter(user => user.age >= 30);
const joinNames = names => names.join(', ');

const getAdultNames = pipe(filterAdults, getNames, joinNames);
console.log(getAdultNames(users)); // "Bob, Charlie"
```

## 예시

### 1. 실제 사용 사례

#### 데이터 처리 파이프라인
```javascript
// 주문 데이터 처리 예시
const orders = [
    { id: 1, amount: 100, status: 'pending' },
    { id: 2, amount: 200, status: 'completed' },
    { id: 3, amount: 150, status: 'pending' },
    { id: 4, amount: 300, status: 'completed' }
];

// 순수 함수들
const filterByStatus = status => orders => 
    orders.filter(order => order.status === status);

const calculateTotal = orders => 
    orders.reduce((sum, order) => sum + order.amount, 0);

const formatCurrency = amount => 
    `$${amount.toFixed(2)}`;

// 함수 합성을 통한 파이프라인
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const getCompletedOrdersTotal = pipe(
    filterByStatus('completed'),
    calculateTotal,
    formatCurrency
);

console.log(getCompletedOrdersTotal(orders)); // "$500.00"

// 더 복잡한 파이프라인
const getPendingOrdersCount = pipe(
    filterByStatus('pending'),
    orders => orders.length
);

const getAverageOrderAmount = pipe(
    calculateTotal,
    total => total / orders.length,
    formatCurrency
);

console.log(getPendingOrdersCount(orders)); // 2
console.log(getAverageOrderAmount(orders)); // "$187.50"
```

#### 유효성 검사 체인
```javascript
// 유효성 검사 함수들
const isString = value => typeof value === 'string';
const isNotEmpty = value => value.length > 0;
const isEmail = value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const isMinLength = min => value => value.length >= min;

// 검사 결과를 나타내는 객체
const ValidationResult = {
    success: (value) => ({ isValid: true, value, errors: [] }),
    failure: (errors) => ({ isValid: false, value: null, errors })
};

// 검사 체인 함수
const validate = (...validators) => value => {
    const errors = [];
    
    for (const validator of validators) {
        if (!validator(value)) {
            errors.push(validator.message || 'Validation failed');
        }
    }
    
    return errors.length === 0 
        ? ValidationResult.success(value)
        : ValidationResult.failure(errors);
};

// 이메일 검사 체인
const validateEmail = validate(
    isString,
    isNotEmpty,
    isEmail
);

// 비밀번호 검사 체인
const validatePassword = validate(
    isString,
    isMinLength(8)
);

// 사용 예시
console.log(validateEmail('test@example.com')); // { isValid: true, value: 'test@example.com', errors: [] }
console.log(validateEmail('invalid-email')); // { isValid: false, value: null, errors: ['Validation failed'] }
console.log(validatePassword('short')); // { isValid: false, value: null, errors: ['Validation failed'] }
```

### 2. 고급 패턴

#### 모나드 패턴
```javascript
// Maybe 모나드 구현
const Maybe = {
    just: (value) => ({
        map: (fn) => Maybe.just(fn(value)),
        flatMap: (fn) => fn(value),
        getOrElse: (defaultValue) => value,
        isJust: () => true,
        isNothing: () => false
    }),
    
    nothing: () => ({
        map: () => Maybe.nothing(),
        flatMap: () => Maybe.nothing(),
        getOrElse: (defaultValue) => defaultValue,
        isJust: () => false,
        isNothing: () => true
    }),
    
    fromNullable: (value) => 
        value === null || value === undefined 
            ? Maybe.nothing() 
            : Maybe.just(value)
};

// 사용 예시
const user = { name: 'Alice', address: { city: 'Seoul' } };

const getCity = (user) => 
    Maybe.fromNullable(user)
        .map(u => u.address)
        .map(addr => addr.city)
        .getOrElse('Unknown');

console.log(getCity(user)); // "Seoul"
console.log(getCity(null)); // "Unknown"
```

#### 함수형 상태 관리
```javascript
// 불변적 상태 업데이트
const createStore = (initialState) => {
    let state = initialState;
    let listeners = [];
    
    return {
        getState: () => state,
        
        dispatch: (action) => {
            state = action(state);
            listeners.forEach(listener => listener(state));
        },
        
        subscribe: (listener) => {
            listeners.push(listener);
            return () => {
                listeners = listeners.filter(l => l !== listener);
            };
        }
    };
};

// 액션 생성자들
const addTodo = (text) => (state) => ({
    ...state,
    todos: [...state.todos, { id: Date.now(), text, completed: false }]
});

const toggleTodo = (id) => (state) => ({
    ...state,
    todos: state.todos.map(todo =>
        todo.id === id 
            ? { ...todo, completed: !todo.completed }
            : todo
    )
});

// 사용 예시
const store = createStore({ todos: [] });

store.subscribe((state) => {
    console.log('State updated:', state);
});

store.dispatch(addTodo('Learn functional programming'));
store.dispatch(addTodo('Build a project'));
store.dispatch(toggleTodo(store.getState().todos[0].id));
```

## 운영 팁

### 성능 최적화

#### 메모이제이션 활용
```javascript
// 메모이제이션 유틸리티
const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        if (cache.has(key)) {
            return cache.get(key);
        }
        const result = fn(...args);
        cache.set(key, result);
        return result;
    };
};

// 비용이 큰 계산을 메모이제이션
const expensiveCalculation = memoize((n) => {
    console.log('계산 중...');
    return n * n * n;
});

console.log(expensiveCalculation(5)); // 계산 중... 125
console.log(expensiveCalculation(5)); // 125 (캐시된 결과)
```

#### 지연 평가 (Lazy Evaluation)
```javascript
// 지연 평가를 위한 제너레이터 활용
function* range(start, end) {
    for (let i = start; i <= end; i++) {
        yield i;
    }
}

function* map(iterable, fn) {
    for (const item of iterable) {
        yield fn(item);
    }
}

function* filter(iterable, predicate) {
    for (const item of iterable) {
        if (predicate(item)) {
            yield item;
        }
    }
}

// 사용 예시
const numbers = range(1, 1000000);
const doubled = map(numbers, x => x * 2);
const evens = filter(doubled, x => x % 2 === 0);

// 실제로 필요한 만큼만 계산
let count = 0;
for (const num of evens) {
    if (count >= 5) break;
    console.log(num);
    count++;
}
```

### 에러 처리

#### 함수형 에러 처리
```javascript
// Either 모나드로 에러 처리
const Either = {
    left: (error) => ({
        map: () => Either.left(error),
        flatMap: () => Either.left(error),
        fold: (onError, onSuccess) => onError(error),
        isLeft: () => true,
        isRight: () => false
    }),
    
    right: (value) => ({
        map: (fn) => Either.right(fn(value)),
        flatMap: (fn) => fn(value),
        fold: (onError, onSuccess) => onSuccess(value),
        isLeft: () => false,
        isRight: () => true
    }),
    
    fromNullable: (value) => 
        value === null || value === undefined 
            ? Either.left('Value is null or undefined')
            : Either.right(value)
};

// 안전한 함수 실행
const safeDivide = (a, b) => 
    b === 0 
        ? Either.left('Division by zero')
        : Either.right(a / b);

// 사용 예시
const result = safeDivide(10, 2)
    .map(x => x * 2)
    .fold(
        error => console.error('Error:', error),
        value => console.log('Result:', value)
    );
```

## 참고

### 함수형 프로그래밍 vs 명령형 프로그래밍 비교표

| 구분 | 함수형 프로그래밍 | 명령형 프로그래밍 |
|------|-------------------|-------------------|
| **접근 방식** | 선언적 | 명령적 |
| **상태 관리** | 불변성 | 가변성 |
| **부수 효과** | 최소화 | 허용 |
| **테스트** | 용이 | 복잡 |
| **병렬 처리** | 안전 | 위험 |

### 함수형 프로그래밍 라이브러리

| 라이브러리 | 특징 | 용도 |
|-----------|------|------|
| **Ramda** | 함수형 유틸리티 | 데이터 처리 |
| **Lodash/fp** | 함수형 버전 | 유틸리티 함수 |
| **Folktale** | 모나드 구현 | 에러 처리 |
| **Immutable.js** | 불변 데이터 구조 | 상태 관리 |

### 결론
함수형 프로그래밍은 JavaScript에서 강력한 패러다임입니다.
순수 함수와 불변성을 통해 예측 가능한 코드를 작성하세요.
고차 함수와 함수 합성을 활용하여 재사용 가능한 코드를 만드세요.
메모이제이션과 지연 평가로 성능을 최적화하세요.
함수형 에러 처리 패턴을 활용하여 안전한 코드를 작성하세요.
적절한 함수형 라이브러리를 활용하여 개발 효율성을 높이세요.

