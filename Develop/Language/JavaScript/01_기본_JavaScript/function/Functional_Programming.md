# JavaScript의 함수형 프로그래밍 패턴

## 1. 함수형 프로그래밍의 기본 개념

### 1.1 함수형 프로그래밍이란?
함수형 프로그래밍은 다음과 같은 핵심 원칙을 가진 프로그래밍 패러다임입니다:

1. **순수 함수 (Pure Functions)**
   - 동일한 입력에 대해 항상 동일한 출력을 반환
   - 부수 효과(side effects)가 없음
   - 외부 상태에 의존하지 않음

```javascript
// 순수 함수의 예
const add = (a, b) => a + b;

// 부수 효과가 있는 함수 (순수하지 않음)
let total = 0;
const addToTotal = (x) => {
    total += x;  // 외부 상태를 변경
    return total;
};
```

2. **불변성 (Immutability)**
   - 데이터는 한번 생성되면 변경할 수 없음
   - 새로운 데이터를 생성하여 변경사항을 반영

```javascript
// 가변적(mutable) 접근
const numbers = [1, 2, 3];
numbers.push(4);  // 원본 배열 수정

// 불변적(immutable) 접근
const numbers = [1, 2, 3];
const newNumbers = [...numbers, 4];  // 새 배열 생성
```

3. **참조 투명성 (Referential Transparency)**
   - 함수의 결과가 입력값에만 의존
   - 함수 호출을 그 결과값으로 대체 가능

```javascript
// 참조 투명성이 있는 함수
const square = x => x * x;
const result = square(4);  // 16

// 참조 투명성이 없는 함수
const getRandom = () => Math.random();
const result = getRandom();  // 매번 다른 값
```

### 1.2 고차 함수 (Higher-Order Functions)
함수를 인자로 받거나 함수를 반환하는 함수를 고차 함수라고 합니다.

```javascript
// 함수를 인자로 받는 고차 함수
const map = (fn, array) => array.map(fn);
const double = x => x * 2;
console.log(map(double, [1, 2, 3]));  // [2, 4, 6]

// 함수를 반환하는 고차 함수
const multiply = (x) => (y) => x * y;
const multiplyByTwo = multiply(2);
console.log(multiplyByTwo(4));  // 8
```

### 1.3 함수 합성 (Function Composition)
여러 함수를 조합하여 새로운 함수를 만드는 기법입니다.

```javascript
// 기본적인 함수 합성
const addOne = x => x + 1;
const double = x => x * 2;
const addOneAndDouble = x => double(addOne(x));

// 고급 함수 합성
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const addOneAndDouble = compose(double, addOne);
const doubleAndAddOne = pipe(double, addOne);
```

## 2. 고급 함수형 유틸리티

### 2.1 Compose
여러 함수를 오른쪽에서 왼쪽으로 실행하는 함수 합성 유틸리티입니다.

```javascript
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

// 사용 예시
const add = x => x + 1;
const multiply = x => x * 2;
const square = x => x * x;

const complexOperation = compose(
    square,
    multiply,
    add
);

console.log(complexOperation(5));  // ((5 + 1) * 2)² = 144
```

### 2.2 Pipe
여러 함수를 왼쪽에서 오른쪽으로 실행하는 함수 합성 유틸리티입니다.

```javascript
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

// 사용 예시
const complexOperation = pipe(
    add,
    multiply,
    square
);

console.log(complexOperation(5));  // ((5 + 1) * 2)² = 144
```

### 2.3 Curry
함수를 부분적으로 적용할 수 있게 변환하는 기법입니다.

```javascript
const curry = fn => {
    const arity = fn.length;
    
    return function curried(...args) {
        if (args.length >= arity) {
            return fn.apply(this, args);
        }
        
        return function(...moreArgs) {
            return curried.apply(this, args.concat(moreArgs));
        };
    };
};

// 사용 예시
const add = (a, b, c) => a + b + c;
const curriedAdd = curry(add);

console.log(curriedAdd(1)(2)(3));     // 6
console.log(curriedAdd(1, 2)(3));     // 6
console.log(curriedAdd(1)(2, 3));     // 6
console.log(curriedAdd(1, 2, 3));     // 6
```

## 3. 실전 함수형 프로그래밍 패턴

### 3.1 데이터 변환 파이프라인
함수형 프로그래밍을 사용한 데이터 처리 예시입니다.

```javascript
const users = [
    { name: 'Alice', age: 25, active: true },
    { name: 'Bob', age: 30, active: false },
    { name: 'Charlie', age: 35, active: true }
];

const processUsers = pipe(
    // 활성 사용자만 필터링
    users => users.filter(user => user.active),
    // 나이로 정렬
    users => users.sort((a, b) => a.age - b.age),
    // 이름만 추출
    users => users.map(user => user.name)
);

console.log(processUsers(users));  // ['Alice', 'Charlie']
```

### 3.2 에러 처리
함수형 프로그래밍에서의 에러 처리 패턴입니다.

```javascript
const Either = {
    Left: value => ({
        map: () => Either.Left(value),
        fold: (f, g) => f(value)
    }),
    Right: value => ({
        map: fn => Either.Right(fn(value)),
        fold: (f, g) => g(value)
    })
};

const safeDivide = (a, b) => 
    b === 0 ? Either.Left('Division by zero') : Either.Right(a / b);

const result = safeDivide(10, 2)
    .map(x => x * 2)
    .fold(
        error => `Error: ${error}`,
        value => `Result: ${value}`
    );

console.log(result);  // "Result: 10"
```

### 3.3 메모이제이션
함수 결과를 캐싱하여 성능을 최적화하는 기법입니다.

```javascript
const memoize = fn => {
    const cache = new Map();
    
    return (...args) => {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            return cache.get(key);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
};

const expensiveOperation = memoize(n => {
    console.log('Computing...');
    return n * n;
});

console.log(expensiveOperation(5));  // Computing... 25
console.log(expensiveOperation(5));  // 25 (캐시된 결과)
```

## 4. 함수형 프로그래밍의 장점과 단점

### 4.1 장점
1. **예측 가능성**: 순수 함수와 불변성으로 인해 코드의 동작을 예측하기 쉬움
2. **테스트 용이성**: 부수 효과가 없어 단위 테스트가 쉬움
3. **병렬 처리**: 데이터 불변성으로 인해 동시성 처리가 안전함
4. **코드 재사용**: 함수 조합을 통한 높은 재사용성

### 4.2 단점
1. **학습 곡선**: 함수형 개념을 이해하고 적용하기 어려울 수 있음
2. **성능 오버헤드**: 불변 데이터 구조로 인한 메모리 사용량 증가
3. **디버깅 어려움**: 함수 체인으로 인한 스택 트레이스 복잡성

## 5. 실무 적용 팁

1. **점진적 도입**: 기존 코드를 점진적으로 함수형 패턴으로 리팩토링
2. **라이브러리 활용**: Ramda, Lodash-FP 등의 함수형 라이브러리 활용
3. **명명 규칙**: 함수형 코드의 의도를 명확히 전달하는 이름 사용
4. **문서화**: 복잡한 함수 조합에 대한 문서화 철저히 하기

함수형 프로그래밍은 코드의 품질과 유지보수성을 크게 향상시킬 수 있는 강력한 패러다임입니다. 적절한 상황에서 선택적으로 적용하면 큰 효과를 볼 수 있습니다!
