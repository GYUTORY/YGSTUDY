---
title: JavaScript 함수형 프로그래밍
tags: [language, javascript, 01기본javascript, function, functional-programming, pure-functions]
updated: 2026-06-15
---

# JavaScript 함수형 프로그래밍

## 이 문서의 범위

함수형 프로그래밍의 기본기를 다룬다. 순수 함수, 불변성, 고차 함수, 간단한 compose/pipe, Maybe 정도까지다. 커링 구현, 트랜스듀서, 모나드 법칙, Lens, 트램폴린, 메모이제이션 심화, TypeScript 합성 타입 같은 실무 심화 주제는 [함수형 프로그래밍 심화](Functional_Programming_Advanced.md) 문서로 분리했다. 여기서 다루는 개념은 거기서 중복하지 않으니, 기본 감을 잡았으면 심화 문서로 넘어가면 된다.

## 순수 함수

같은 입력에 항상 같은 출력을 내고, 함수 바깥의 무언가를 건드리지 않는 함수를 순수 함수라고 한다. 함수형 코드의 출발점이고, 테스트가 쉬운 이유도 여기서 나온다. 입력만 맞춰주면 실행 환경과 무관하게 결과가 고정되기 때문에 목(mock)을 깔 일이 없다.

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

순수 함수만으로는 프로그램을 만들 수 없다는 점은 처음부터 알아둬야 한다. 로그를 찍고, DB에 쓰고, HTTP 응답을 보내는 건 전부 부수 효과다. 목표는 부수 효과를 없애는 게 아니라 순수한 계산 로직과 부수 효과를 내는 코드를 분리해서, 핵심 로직을 순수하게 유지하는 것이다. 부수 효과를 한곳으로 몰아 격리하는 구체적인 기법은 심화 문서의 IO/Task 부분에서 다룬다.

자주 하는 실수는 "리턴값이 있으니 순수 함수"라고 착각하는 것이다. 함수 안에서 `Date.now()`를 읽거나 전역 설정 객체를 참조하면 입력이 같아도 결과가 달라진다. 이런 함수를 나중에 메모이즈하면 캐시가 오래된 값을 계속 돌려주는 버그로 이어진다.

## 불변성

데이터를 제자리에서 수정하지 않고, 바뀐 새 값을 만들어 쓴다. `push`, `splice`, 객체 프로퍼티 직접 대입 같은 변경 메서드 대신 스프레드와 `map`/`filter`를 쓴다.

```javascript
// 배열을 직접 바꾸지 않고 새 배열을 만든다
const numbers = [1, 2, 3];
const newNumbers = [...numbers, 4]; // 원본 numbers는 그대로

const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 }
];

const adultUsers = users.map(user => ({ ...user, isAdult: user.age >= 18 }));
const youngUsers = users.filter(user => user.age < 30);

// 객체도 새로 만든다
const person = { name: 'Alice', age: 25 };
const updatedPerson = { ...person, age: 26 };
```

여기서 반드시 짚어야 할 함정이 얕은 복사다. 스프레드는 한 단계만 복사한다. 중첩 객체는 안쪽 참조가 그대로 공유되므로, 깊은 객체를 불변으로 갱신하려면 경로상의 객체를 단계마다 펼쳐야 한다.

```javascript
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

이 중첩 스프레드는 깊이가 3~4단계만 넘어가도 가독성이 무너지고, 중간 단계 하나를 빠뜨리면 의도치 않게 이전 객체와 참조가 공유되는 버그가 난다. Redux 리듀서를 손으로 짜다 보면 거의 반드시 한 번은 겪는다. 이 문제를 Lens나 Immer로 푸는 방법은 심화 문서에서 다룬다. 기본 문서 수준에서는 "스프레드는 한 단계만 복사한다"는 사실을 확실히 기억하는 걸로 충분하다.

`Object.freeze`로 변경을 막을 수도 있는데, 이것도 얕다. 최상위 프로퍼티만 얼리고 중첩 객체는 그대로 수정 가능하다. 진짜 깊은 동결이 필요하면 재귀로 직접 얼려야 한다.

## 고차 함수

함수를 인자로 받거나 함수를 돌려주는 함수다. `map`, `filter`, `reduce`가 매일 쓰는 대표적인 고차 함수다.

```javascript
const numbers = [1, 2, 3, 4, 5];

const doubled = numbers.map(x => x * 2);
const evens = numbers.filter(x => x % 2 === 0);
const sum = numbers.reduce((acc, x) => acc + x, 0);
```

함수를 돌려주는 쪽이 처음엔 낯설다. 인자 일부를 미리 고정해두고 나머지를 나중에 받는 식으로 쓴다. 아래 `multiply`는 `x`를 받아 "x를 곱하는 함수"를 돌려준다.

```javascript
const multiply = (x) => (y) => x * y;
const multiplyByTwo = multiply(2);
const multiplyByTen = multiply(10);

multiplyByTwo(5); // 10
multiplyByTen(5); // 50
```

인자 일부만 미리 적용해두는 패턴을 부분 적용이라고 한다. 설정값처럼 호출마다 똑같이 들어가는 인자를 한 번 묶어두고 재사용할 때 쓴다.

```javascript
const partial = (fn, ...fixedArgs) => (...remainingArgs) =>
    fn(...fixedArgs, ...remainingArgs);

const add = (a, b, c) => a + b + c;
const addFive = partial(add, 5);
addFive(2, 1); // 8
```

이 부분 적용을 일반화해서 인자를 하나씩 받을 수 있게 만든 게 커링이다. 위 `multiply`가 손으로 짠 커링이고, 임의 함수를 자동으로 커링하는 구현과 placeholder까지 붙이는 방법은 심화 문서에서 다룬다.

## 함수 합성

작은 함수를 이어 붙여 큰 동작을 만든다. `compose`는 오른쪽 함수부터, `pipe`는 왼쪽 함수부터 실행한다. 둘 다 reduce 한 줄이면 만들어진다.

```javascript
const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);
const pipe = (...fns) => x => fns.reduce((v, f) => f(v), x);

const addOne = x => x + 1;
const double = x => x * 2;
const square = x => x * x;

const piped = pipe(addOne, double, square);
piped(3); // ((3 + 1) * 2)² = 64
```

읽는 순서는 `pipe`가 자연스럽다. 위에서 아래로 데이터가 흐르는 모양 그대로 쓰면 된다. `compose`는 수학 표기 `f(g(x))`와 순서가 같아서 학술 자료나 Ramda 쪽에서 더 자주 보인다. 팀 코드에서는 한쪽으로 통일해두는 게 혼란이 적다.

여기까지의 compose/pipe는 단일 값을 받아 단일 값을 돌려주는 동기 함수만 처리한다. 중간에 Promise를 반환하는 함수가 끼거나 인자가 여러 개인 경우는 이 구현으로는 깨진다. 비동기 합성(`pipeAsync`), 다중 인자 지원, 단계별 에러 태깅은 심화 문서에서 다룬다.

## 데이터 처리 파이프라인

실무에서 함수형이 가장 많이 쓰이는 자리다. 거르고, 변환하고, 추리는 작은 함수들을 pipe로 엮으면 중간 변수 없이 흐름이 한눈에 들어온다.

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

getAdultNamesInSeoul(users); // "Charlie"
```

각 단계 함수는 모두 순수해서 따로 떼어 테스트하기 쉽다. 단, 큰 배열에서 `map`과 `filter`를 여러 번 체인하면 단계마다 중간 배열이 새로 생긴다. 수만 행 이상을 처리하는 핫패스라면 이 비용이 무시 못 할 수준이 되는데, 이 문제와 해결책(트랜스듀서, for 루프 전환)은 심화 문서의 성능 함정 절에서 다룬다.

검증 로직도 같은 방식으로 작은 술어(predicate)를 조합해 만든다.

```javascript
const isString = (value) => typeof value === 'string';
const isNotEmpty = (value) => value.length > 0;
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const isMinLength = (min) => (value) => value.length >= min;

const validate = (...validators) => (value) =>
    validators.every(validator => validator(value));

const validateEmail = validate(isString, isNotEmpty, isEmail);
const validatePassword = validate(isString, isMinLength(8));

validateEmail('test@example.com'); // true
validatePassword('password123');   // true
```

이 `validate`는 통과/실패만 알려주고 어느 검증에서 걸렸는지는 모른다. 실패 사유까지 누적해서 보여주려면 Either나 Validation 타입이 필요한데, 그건 심화 영역이다.

## 실무 예제

### 주문 합계 계산

상태로 거르고 금액을 합산해 포맷까지 한 흐름으로 처리한다.

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

getCompletedOrdersTotal(orders); // "$200.00"
```

### null 안전 접근 (Maybe)

`user.address.city`처럼 중첩 프로퍼티를 따라가다가 중간이 `null`이면 터진다. 옵셔널 체이닝 `user?.address?.city`로 충분한 경우가 대부분이지만, 값이 없을 때의 기본값 처리와 변환을 한 흐름으로 묶고 싶을 때 Maybe를 쓴다. 박스 안에 값이 있으면 변환을 이어가고, 비어 있으면 변환을 건너뛰고 기본값을 돌려준다.

```javascript
const Maybe = {
    just: (value) => ({
        map: (fn) => Maybe.just(fn(value)),
        getOrElse: () => value
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

getCity({ address: { city: 'Seoul' } }); // "Seoul"
getCity(null);                           // "Unknown"
```

이 Maybe는 "값이 없음"만 표현한다. "왜 없는지"까지 실어 나르려면 Either가 필요하고, 비동기 계산을 같은 방식으로 다루려면 Task가 필요하다. Functor/Monad 법칙과 Either/Task 구현은 심화 문서에서 다룬다.

### 간단한 메모이제이션

같은 입력으로 반복 호출되는 순수 함수의 결과를 캐시한다.

```javascript
const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        if (cache.has(key)) return cache.get(key);
        const result = fn(...args);
        cache.set(key, result);
        return result;
    };
};

const fibonacci = memoize((n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
});

fibonacci(40); // 재귀가 캐시를 타서 빠르게 계산된다
```

`JSON.stringify`로 키를 만드는 이 방식은 학습용으로는 충분하지만 실무에서 금방 깨진다. 객체 프로퍼티 순서가 바뀌면 다른 키가 되고, `Date`나 `Map`, 함수가 인자로 들어오면 직렬화가 제대로 안 된다. 캐시 크기 상한도 없어서 키 종류가 많으면 메모리가 계속 늘어난다. 객체 참조 기반 WeakMap 캐시, 크기를 제한하는 LRU, 메모이제이션이 깨지는 조건은 심화 문서에서 다룬다.

## 함수형과 명령형

| 측면 | 함수형 | 명령형 |
|------|--------|--------|
| 표현 방식 | "무엇을" 할지 선언 | "어떻게" 할지 단계로 기술 |
| 상태 | 불변, 새 값 생성 | 가변 상태 직접 변경 |
| 부수 효과 | 분리·격리 | 자유롭게 허용 |
| 테스트 | 순수 함수라 입력만 맞추면 됨 | 상태 준비가 필요해 손이 더 감 |

둘은 배타적이지 않다. JavaScript에서는 핵심 계산을 순수 함수로 짜고, 그 함수를 호출하는 바깥쪽은 명령형으로 두는 식으로 섞어 쓴다. 한 함수 안에서도 루프 안의 계산만 순수하게 떼어내면 그만큼 테스트가 쉬워진다. 전부 함수형으로 밀어붙이는 것보다, 부수 효과 경계를 명확히 긋는 쪽이 유지보수에 낫다.

JavaScript는 `map`/`filter`/`reduce`, 스프레드, 클로저, 화살표 함수를 언어 차원에서 지원하니 별도 라이브러리 없이도 위 패턴 대부분을 쓸 수 있다. Ramda나 Lodash/fp 같은 유틸 라이브러리는 커링과 포인트프리를 본격적으로 쓸 때 의미가 있는데, 도입 판단과 직접 구현의 경계는 심화 문서에서 다룬다.

## 참고 자료

- [함수형 프로그래밍 심화](Functional_Programming_Advanced.md) — 커링 구현, 트랜스듀서, 모나드, Lens, 트램폴린, 성능 함정
- [MDN - 함수형 프로그래밍](https://developer.mozilla.org/ko/docs/Glossary/Functional_programming)
- [Mostly Adequate Guide to Functional Programming](https://github.com/MostlyAdequate/mostly-adequate-guide)
