
# JavaScript의 함수형 프로그래밍 패턴

## 1. 함수형 프로그래밍의 기본 개념
함수형 프로그래밍은 데이터와 상태를 변경하지 않고 순수 함수를 사용하여 로직을 구현하는 프로그래밍 패러다임입니다. JavaScript에서는 `map`, `reduce`, `filter`와 같은 고차 함수를 활용해 함수형 프로그래밍을 구현할 수 있습니다.

---

## 2. 고급 함수형 유틸리티
### 2.1 Compose
`compose`는 여러 함수를 결합하여 함수의 실행 흐름을 오른쪽에서 왼쪽으로 설정합니다.

#### 예제
```javascript
const add = x => x + 1;
const multiply = x => x * 2;

const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

const addThenMultiply = compose(multiply, add);

console.log(addThenMultiply(5)); // (5 + 1) * 2 = 12
```

### 2.2 Pipe
`pipe`는 `compose`와 반대로 함수의 실행 흐름을 왼쪽에서 오른쪽으로 설정합니다.

#### 예제
```javascript
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const multiplyThenAdd = pipe(multiply, add);

console.log(multiplyThenAdd(5)); // (5 * 2) + 1 = 11
```

### 2.3 Curry
`curry`는 함수를 부분 적용할 수 있도록 변환합니다.

#### 예제
```javascript
const curry = fn => (...args) => 
    args.length >= fn.length ? fn(...args) : (...moreArgs) => curry(fn)(...args, ...moreArgs);

const addThreeNumbers = (a, b, c) => a + b + c;

const curriedAdd = curry(addThreeNumbers);

console.log(curriedAdd(1)(2)(3)); // 6
console.log(curriedAdd(1, 2)(3)); // 6
```

---

## 3. Immutable 데이터 구조와 라이브러리 활용

### 3.1 Immutable 데이터 구조
불변성(immutability)은 데이터의 변경을 방지하여 예측 가능한 코드를 작성할 수 있도록 도와줍니다.

#### 불변성 예제
```javascript
const immutableArray = Object.freeze([1, 2, 3]);

try {
    immutableArray.push(4); // 오류 발생
} catch (e) {
    console.error('Cannot modify immutable array');
}
```

### 3.2 Ramda 라이브러리
Ramda는 함수형 프로그래밍을 쉽게 구현할 수 있는 유틸리티 함수를 제공합니다.

#### Ramda 예제
```javascript
const R = require('ramda');

const double = x => x * 2;
const increment = x => x + 1;

const processNumbers = R.pipe(
    R.map(double),
    R.map(increment)
);

console.log(processNumbers([1, 2, 3])); // [3, 5, 7]
```

### 3.3 Lodash 라이브러리
Lodash는 Ramda와 유사하게 다양한 함수형 유틸리티를 제공합니다.

#### Lodash 예제
```javascript
const _ = require('lodash');

const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 },
    { name: 'Charlie', age: 35 }
];

const sortedUsers = _.sortBy(users, 'age');
console.log(sortedUsers);
```

---

## 4. 요약
- `compose`, `pipe`, `curry`를 사용하여 복잡한 함수 조합을 간결하게 구현.
- 불변성 원칙을 유지하며 예측 가능한 코드를 작성.
- Ramda, Lodash와 같은 라이브러리를 활용하여 생산성과 코드 가독성 향상.

함수형 프로그래밍 패턴을 통해 JavaScript 코드의 유연성과 유지보수성을 높일 수 있습니다!
