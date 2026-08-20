---
title: JavaScript forEach 메서드 개념과 사용법
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript forEach 메서드 개념과 사용법

## 배경

`forEach` 는 배열의 각 요소마다 주어진 함수를 실행하는 메서드다. 배열을 처음부터 끝까지 돌면서 요소 하나하나를 콜백에 넘긴다. 전통적인 for 루프로 쓰던 순회를 더 선언적이고 함수형에 가까운 스타일로 적을 수 있다.

### forEach의 필요성
- **선언적 프로그래밍**: 명령형 for 루프 대신 선언적 스타일
- **함수형 프로그래밍**: 고차 함수를 활용한 데이터 처리
- **코드 가독성**: 의도가 명확한 배열 순회 코드
- **부수 효과 처리**: 각 요소마다 작업 수행

### 기본 개념
- **콜백 함수**: 각 요소마다 실행되는 함수
- **순회**: 배열의 모든 요소를 차례대로 처리
- **부수 효과**: 반환값 없이 작업만 수행
- **동기 실행**: 비동기 작업에는 적합하지 않음

## 핵심

### 1. forEach 기본 문법

#### 메서드 시그니처
```javascript
array.forEach(callback(currentValue[, index[, array]])[, thisArg])
```

#### 매개변수 설명
- **callback**: 각 요소마다 실행할 함수
  - `currentValue`: 처리할 현재 요소
  - `index` (선택사항): 처리할 현재 요소의 인덱스
  - `array` (선택사항): forEach를 호출한 배열
- **thisArg** (선택사항): callback을 실행할 때 this로 사용할 값

#### 기본 사용법
```javascript
// 기본적인 사용법
const numbers = [1, 2, 3, 4, 5];
numbers.forEach((number) => {
    console.log(number);
});

// 인덱스와 배열 사용
const fruits = ['apple', 'banana', 'orange'];
fruits.forEach((fruit, index, array) => {
    console.log(`${index}: ${fruit}`);
    console.log('전체 배열:', array);
});

// thisArg 사용 예제
class Counter {
    constructor() {
        this.count = 0;
    }
    
    increment() {
        this.count++;
    }
}

const counter = new Counter();
const items = [1, 2, 3];
items.forEach(function() {
    this.increment();
}, counter);
console.log(counter.count); // 3
```

여기서 콜백이 화살표 함수가 아닌 것은 실수가 아니다. **화살표 함수를 쓰면 `thisArg` 가 무시된다.**

```javascript
const ctx = { c: 0 };
[1, 2, 3].forEach(() => { this.c++; }, ctx);
ctx.c;   // 0 — 두 번째 인자가 아무 일도 안 했다
```

화살표 함수는 자기 `this` 를 갖지 않고 정의된 위치의 `this` 를 그대로 쓴다. `forEach` 가 아무리 `thisArg` 를 넘겨도 바꿀 대상이 없다. 에러가 나지 않고 그냥 다른 객체를 건드리기 때문에, 카운터가 안 올라가는 것만 보고 원인을 찾기 어렵다.

`thisArg` 자체가 화살표 함수 이전 시대의 유물이다. 지금은 두 번째 인자를 쓰기보다 필요한 값을 클로저로 잡는 편이 낫다.

### 2. forEach의 특징

#### 반환값이 없음
```javascript
// forEach는 undefined를 반환
const result = [1, 2, 3].forEach(x => x * 2);
console.log(result); // undefined

// 체이닝이 불가능
const numbers = [1, 2, 3];
numbers.forEach(x => console.log(x)).map(x => x * 2); // TypeError
```

#### 중간에 중단할 수 없음
```javascript
// break나 return으로 루프를 중단할 수 없음
[1, 2, 3, 4, 5].forEach(num => {
    if (num === 3) return; // 중단되지 않고 계속 실행됨
    console.log(num);
});
// 출력: 1, 2, 4, 5 (3은 건너뛰지만 루프는 계속됨)

// 중단이 필요한 경우 for...of 사용
for (const num of [1, 2, 3, 4, 5]) {
    if (num === 3) break; // 실제로 중단됨
    console.log(num);
}
// 출력: 1, 2
```

#### 원본 배열 변경 가능
```javascript
const numbers = [1, 2, 3];
numbers.forEach((num, index, arr) => {
    arr[index] = num * 2; // 원본 배열 직접 수정
});
console.log(numbers); // [2, 4, 6]

// 객체 배열에서 속성 수정
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 }
];

users.forEach(user => {
    user.age += 1; // 객체 속성 수정
});

console.log(users);
// [{ name: 'Alice', age: 26 }, { name: 'Bob', age: 31 }]
```

원본을 바꿀 수 있다는 것과 **바꾸면서 순회해도 된다**는 것은 다르다. `forEach` 는 시작할 때 길이를 한 번 읽고, 매 회 그 인덱스를 다시 조회한다. 그래서 순회 중 요소를 지우면 뒤가 밀려 건너뛴다.

```javascript
const arr = [1, 2, 3, 4];
const seen = [];
arr.forEach(x => { seen.push(x); if (x === 1) arr.splice(0, 1); });

seen;   // [1, 3, 4]   ← 2 를 한 번도 안 봤다
arr;    // [2, 3, 4]   ← 그런데 2 는 배열에 남아 있다
```

첫 회에 인덱스 0 을 지우자 뒤가 전부 한 칸씩 당겨졌다. 다음 차례는 인덱스 1 인데, 그 자리는 이미 3 이다. **2 는 배열에 멀쩡히 있는데 순회에서만 빠진다.**

지운 자리가 현재 인덱스보다 뒤라면 이런 일은 없다 — `splice(1, 1)` 로 2 를 지우면 3·4 는 당겨진 자리에서 정상 방문된다. **건너뛰기는 현재 위치 이하를 지울 때 생긴다.**

반대로 순회 중에 `push` 로 추가한 요소는 방문하지 않는다 — 길이가 이미 고정됐기 때문이다. "필터링하면서 삭제"를 `forEach` 로 짜면 절반쯤만 지워지는 이유가 이것이다. 지울 목적이면 `filter` 로 새 배열을 만든다.

**빈 슬롯(hole)은 아예 건너뛴다.** 이건 `map`·`filter` 도 마찬가지다.

```javascript
let n = 0;
[1, , 3].forEach(() => n++);
n;   // 2 — 가운데 구멍은 방문하지 않는다

let m = 0;
new Array(3).forEach(() => m++);
m;   // 0 — 콜백이 한 번도 안 불린다

new Array(3).map(() => 1);   // [비어 있음 × 3] — 채워지지 않는다
```

`new Array(n)` 은 길이만 `n` 이고 요소가 하나도 없는 배열이다. `length` 는 3 인데 순회는 0 회라서 "왜 아무 일도 안 일어나지"로 막히기 쉽다. 길이만큼 채우려면 `Array.from({ length: 3 })` 이나 `new Array(3).fill()` 을 쓴다. 이렇게 만든 배열은 `undefined` 로 채워져 있어서 `forEach` 가 3번 돈다.

### 3. forEach vs 다른 배열 메서드

#### forEach vs map
```javascript
const numbers = [1, 2, 3, 4, 5];

// forEach: 부수 효과만 수행
const forEachResult = numbers.forEach(num => {
    console.log(num * 2); // 출력만 하고 반환하지 않음
});
console.log(forEachResult); // undefined

// map: 새로운 배열 반환
const mapResult = numbers.map(num => num * 2);
console.log(mapResult); // [2, 4, 6, 8, 10]

// forEach로 map 구현
const forEachMap = [];
numbers.forEach(num => {
    forEachMap.push(num * 2);
});
console.log(forEachMap); // [2, 4, 6, 8, 10]
```

#### forEach vs for...of
```javascript
const fruits = ['apple', 'banana', 'orange'];

// forEach: 함수형 스타일
fruits.forEach((fruit, index) => {
    console.log(`${index}: ${fruit}`);
});

// for...of: 명령형 스타일
for (const [index, fruit] of fruits.entries()) {
    console.log(`${index}: ${fruit}`);
}

// forEach는 중단 불가, for...of는 중단 가능
fruits.forEach(fruit => {
    if (fruit === 'banana') return; // 중단되지 않음
    console.log(fruit);
});

for (const fruit of fruits) {
    if (fruit === 'banana') break; // 실제로 중단됨
    console.log(fruit);
}
```

## 예시

### 1. 실제 사용 사례

#### DOM 요소 처리
```javascript
// HTML 요소들의 텍스트 내용 수집
const elements = document.querySelectorAll('.item');
const texts = [];

elements.forEach(element => {
    texts.push(element.textContent);
});

console.log(texts);

// 이벤트 리스너 등록
const buttons = document.querySelectorAll('.btn');
buttons.forEach((button, index) => {
    button.addEventListener('click', () => {
        console.log(`버튼 ${index} 클릭됨`);
    });
});
```

#### 객체 배열 처리
```javascript
const users = [
    { id: 1, name: 'Alice', age: 25, active: true },
    { id: 2, name: 'Bob', age: 30, active: false },
    { id: 3, name: 'Charlie', age: 35, active: true }
];

// 활성 사용자만 필터링하여 이름 수집
const activeUserNames = [];
users.forEach(user => {
    if (user.active) {
        activeUserNames.push(user.name);
    }
});

console.log(activeUserNames); // ['Alice', 'Charlie']

// 사용자 정보 로깅
users.forEach((user, index) => {
    console.log(`사용자 ${index + 1}:`);
    console.log(`  ID: ${user.id}`);
    console.log(`  이름: ${user.name}`);
    console.log(`  나이: ${user.age}`);
    console.log(`  활성: ${user.active ? '예' : '아니오'}`);
    console.log('---');
});
```

#### 데이터 변환 및 검증
```javascript
const products = [
    { name: 'Laptop', price: 1000, category: 'Electronics' },
    { name: 'Book', price: 20, category: 'Education' },
    { name: 'Phone', price: 500, category: 'Electronics' }
];

// 가격 검증 및 수정
let totalPrice = 0;
products.forEach(product => {
    // 가격이 음수인 경우 0으로 수정
    if (product.price < 0) {
        product.price = 0;
    }
    
    // 카테고리별 가격 합계 계산
    if (product.category === 'Electronics') {
        totalPrice += product.price;
    }
});

console.log('전자제품 총 가격:', totalPrice); // 1500

// 제품 정보 출력
products.forEach(product => {
    const priceStatus = product.price > 100 ? '고가' : '저가';
    console.log(`${product.name}: ${priceStatus} (${product.price}원)`);
});
```

### 2. 고급 패턴

#### 중첩 배열 처리
```javascript
const matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

// 2차원 배열 순회
matrix.forEach((row, rowIndex) => {
    row.forEach((cell, colIndex) => {
        console.log(`[${rowIndex}][${colIndex}]: ${cell}`);
    });
});

// 행별 합계 계산
matrix.forEach((row, index) => {
    const sum = row.reduce((acc, val) => acc + val, 0);
    console.log(`행 ${index}의 합계: ${sum}`);
});
```

#### 조건부 처리
```javascript
const data = [
    { type: 'user', name: 'Alice', age: 25 },
    { type: 'admin', name: 'Bob', age: 30 },
    { type: 'user', name: 'Charlie', age: 35 },
    { type: 'guest', name: 'David', age: 20 }
];

const users = [];
const admins = [];
const guests = [];

data.forEach(item => {
    switch (item.type) {
        case 'user':
            users.push(item);
            break;
        case 'admin':
            admins.push(item);
            break;
        case 'guest':
            guests.push(item);
            break;
    }
});

console.log('사용자:', users.length);
console.log('관리자:', admins.length);
console.log('게스트:', guests.length);
```

#### 에러 처리
```javascript
const riskyData = [1, 2, 'error', 4, 5];

riskyData.forEach((item, index) => {
    try {
        if (typeof item !== 'number') {
            throw new Error(`인덱스 ${index}의 값이 숫자가 아닙니다: ${item}`);
        }
        
        console.log(`숫자 처리: ${item * 2}`);
        
    } catch (error) {
        console.error(`오류 발생 (인덱스 ${index}):`, error.message);
    }
});
```

## 운영 팁

### 성능 최적화

#### forEach 성능 고려사항
```javascript
// 대용량 배열에서의 성능 비교
const largeArray = Array.from({ length: 100000 }, (_, i) => i);

// forEach 사용
console.time('forEach');
largeArray.forEach(num => {
    // 작업 수행
});
console.timeEnd('forEach');

// for...of 사용
console.time('for...of');
for (const num of largeArray) {
    // 작업 수행
}
console.timeEnd('for...of');

// 전통적인 for 루프
console.time('for loop');
for (let i = 0; i < largeArray.length; i++) {
    // 작업 수행
}
console.timeEnd('for loop');
```

#### 메모리 효율성
```javascript
// 비효율적인 방법: 불필요한 배열 생성
const numbers = [1, 2, 3, 4, 5];
const doubled = [];

numbers.forEach(num => {
    doubled.push(num * 2); // 새로운 배열 생성
});

// 효율적인 방법: map 사용
const doubledEfficient = numbers.map(num => num * 2);

// forEach는 부수 효과에만 사용
numbers.forEach(num => {
    console.log(num * 2); // 출력만 수행
});
```

### 에러 처리

#### forEach에서 안전한 에러 처리
```javascript
const data = [1, 2, null, 4, 5];

// 안전한 데이터 처리
data.forEach((item, index) => {
    try {
        if (item === null || item === undefined) {
            console.warn(`인덱스 ${index}: null/undefined 값 건너뜀`);
            return;
        }
        
        const result = item * 2;
        console.log(`결과: ${result}`);
        
    } catch (error) {
        console.error(`인덱스 ${index} 처리 중 오류:`, error.message);
    }
});

// 비동기 작업에서의 주의사항
const urls = ['url1', 'url2', 'url3'];

// 잘못된 사용: forEach는 비동기를 기다리지 않음
urls.forEach(async url => {
    const response = await fetch(url);
    console.log(response);
});
console.log('완료!'); // 비동기 작업 완료 전에 실행됨

// 올바른 사용: for...of 사용
async function processUrls() {
    for (const url of urls) {
        const response = await fetch(url);
        console.log(response);
    }
    console.log('완료!');
}
```

`forEach` 에 `async` 콜백을 넘겼을 때 실제로 일어나는 일은 "기다리지 않는다"보다 나쁘다. **예외가 사라진다.**

```javascript
try {
  urls.forEach(async url => { throw new Error('안 잡힌다'); });
  console.log('try 블록은 그냥 통과한다');
} catch (e) {
  console.log('여기는 실행되지 않는다');
}
// 출력: try 블록은 그냥 통과한다
// 그 뒤에: UnhandledPromiseRejection 으로 프로세스 종료
//         (거부는 3건 발생하지만 첫 건에서 죽으므로 화면에는 하나만 보인다)
```

`async` 함수는 던지는 대신 거부된 프로미스를 **반환**하는데, `forEach` 는 콜백의 반환값을 버린다. 아무도 잡지 않은 거부가 남아 Node 에서는 프로세스가 죽고 브라우저에서는 콘솔에만 찍힌다. `try/catch` 는 이미 지나간 뒤다.

작업 자체는 돌긴 돈다 — 순서만 어긋난다.

```
forEach 직후 done = []          ← 아직 아무것도 안 끝났다
100ms 뒤    done = ['a','b','c']
```

그래서 "완료!" 뒤에 결과를 쓰는 코드는 빈 배열을 보게 된다. 로그만 보면 요청은 다 나갔으니 원인이 비동기라는 것도 눈에 안 띈다.

순차 실행이 필요하면 문서의 `for...of` 가 맞다. 앞 요청의 결과를 뒤에서 쓰지 않는다면 `map` 으로 프로미스를 모아 `await` 한다. 요청이 동시에 나가고, 무엇보다 **에러가 정상적으로 전파된다.**

```javascript
await Promise.all(urls.map(url => fetch(url)));   // 하나라도 실패하면 거부
await Promise.allSettled(urls.map(url => fetch(url)));  // 전부 끝까지 돌린 뒤 결과 확인
```

동시 요청 수를 제한해야 하는 상황이 아니라면 `Promise.all` 이 기본값이다. `forEach` 와 `async` 를 같이 쓰는 코드는 대체로 이 둘 중 하나를 잘못 쓴 것이다.

## 참고

### forEach vs 다른 메서드 비교표

| 메서드 | 반환값 | 중단 가능 | 용도 |
|--------|--------|-----------|------|
| **forEach** | undefined | 불가능 | 부수 효과 |
| **map** | 새 배열 | 불가능 | 데이터 변환 |
| **filter** | 새 배열 | 불가능 | 데이터 필터링 |
| **reduce** | 누적값 | 불가능 | 데이터 집계 |
| **for...of** | - | 가능 | 일반 순회 |

### forEach 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **부수 효과 수행** | forEach 사용 | 로깅, DOM 조작 등 |
| **데이터 변환** | map 사용 | 새로운 배열 생성 |
| **조건부 중단** | for...of 사용 | break/return 필요 |
| **비동기 처리** | for...of 사용 | async/await 지원 |
| **성능 중요** | for 루프 사용 | 최대 성능 |

### 결론
forEach는 배열의 각 요소마다 부수 효과를 일으키는 데 적합하다.
반환값이 없고 중간에 멈출 수 없다는 점은 알고 써야 한다.
데이터를 변환해야 한다면 map이 더 맞다.
비동기 작업에는 for...of나 전통적인 for 루프를 쓴다.
성능이 중요하면 전통적인 for 루프를 고려한다.
forEach를 쓰면 선언적이고 읽기 쉬운 코드가 된다.
