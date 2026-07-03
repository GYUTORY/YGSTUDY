---
title: forEach 실전 예제와 함정
tags: [language, javascript, 01기본javascript, forloop, foreach예제]
updated: 2026-06-08
---

# forEach 실전 예제와 함정

## 기본 사용법과 콜백 인자

forEach는 콜백에 `(요소, 인덱스, 원본배열)` 세 개를 넘긴다. 인덱스와 원본 배열은 필요할 때만 받아 쓰면 된다. 처음 forEach를 배울 때는 단순히 `arr.forEach(x => ...)` 형태만 쓰다가, 인덱스가 필요할 때 어색해지는 경우가 많다.

```javascript
const fruits = ['사과', '바나나', '오렌지'];

fruits.forEach((fruit, index, arr) => {
    console.log(`${index + 1}/${arr.length}: ${fruit}`);
});

// 출력:
// 1/3: 사과
// 2/3: 바나나
// 3/3: 오렌지
```

세 번째 인자인 원본 배열을 받으면 콜백 내부에서 다른 요소를 참조하기 편하다. 예를 들어 직전 값과 비교가 필요한 경우 자주 쓴다.

```javascript
const prices = [1000, 1200, 950, 1500];

prices.forEach((price, i, arr) => {
    if (i === 0) return;
    const diff = price - arr[i - 1];
    console.log(`${i}일차 변동: ${diff > 0 ? '+' : ''}${diff}`);
});

// 출력:
// 1일차 변동: +200
// 2일차 변동: -250
// 3일차 변동: +550
```

## 객체 배열과 인덱스로 다른 배열 참조

실무에서는 단순 숫자 배열보다 객체 배열을 더 자주 처리한다. 두 배열을 인덱스로 묶어 처리하는 패턴도 흔하다. 예전에 통계 리포트 만들 때 ID 배열과 점수 배열이 따로 들어와서 인덱스로 짝지어 처리한 적이 있다.

```javascript
const ids = ['u1', 'u2', 'u3'];
const scores = [88, 92, 75];

const result = {};
ids.forEach((id, i) => {
    result[id] = scores[i];
});

console.log(result);
// 출력: { u1: 88, u2: 92, u3: 75 }
```

두 배열 길이가 다르면 짧은 쪽 기준으로만 처리되거나, 인덱스 초과 시 `undefined`가 들어간다. 인덱스 기반 매칭은 입력 검증을 같이 두는 습관이 필요하다.

```javascript
const students = [
    { name: '김철수', score: 90 },
    { name: '이영희', score: 85 },
    { name: '박민수', score: 95 }
];

let total = 0;
students.forEach(({ name, score }) => {
    total += score;
    console.log(`${name}: ${score}`);
});

console.log(`평균: ${total / students.length}`);
// 출력:
// 김철수: 90
// 이영희: 85
// 박민수: 95
// 평균: 90
```

구조 분해 할당과 같이 쓰면 코드가 깔끔해진다. 점수 합산 같은 단순 집계는 `reduce`가 의도를 더 잘 드러내지만, 합산과 동시에 부수 작업(로그·DB 기록)이 필요하면 forEach가 자연스럽다.

## Map과 Set의 forEach

`Array.prototype.forEach`만 알고 있다가, Map이나 Set에서도 forEach가 된다는 사실을 모르는 경우를 자주 본다. 콜백 시그니처가 미묘하게 다르니 한 번 정리해두면 좋다.

```javascript
const userMap = new Map([
    ['u1', '김철수'],
    ['u2', '이영희']
]);

userMap.forEach((value, key, map) => {
    console.log(`${key} -> ${value}`);
});
// 출력:
// u1 -> 김철수
// u2 -> 이영희

const tags = new Set(['javascript', 'node', 'react']);
tags.forEach((value, valueAgain, set) => {
    console.log(value);
});
// 출력:
// javascript
// node
// react
```

Set의 콜백은 `(value, value, set)` 형태로 첫 번째와 두 번째 인자가 같다. 호환성 때문에 의도적으로 그렇게 설계됐다. 코드 리뷰에서 `(value, index)`라고 쓴 걸 본 적 있는데, Set은 인덱스가 없으니 두 번째 인자도 그냥 value다.

Map은 `(value, key, map)` 순서다. 객체의 `for...in`과 비슷한 감각으로 쓰면 된다.

## NodeList와 HTMLCollection의 차이

DOM 작업하면서 가장 많이 혼동되는 부분이다. `querySelectorAll`은 NodeList를, `getElementsByClassName`/`getElementsByTagName`은 HTMLCollection을 반환한다. NodeList에는 forEach가 있지만 HTMLCollection에는 없다.

```javascript
// NodeList - forEach 직접 사용 가능
const items = document.querySelectorAll('.item');
items.forEach((item, i) => {
    item.textContent = `항목 ${i + 1}`;
});

// HTMLCollection - forEach 없음, 에러 발생
const items2 = document.getElementsByClassName('item');
items2.forEach(item => { /* ... */ });
// TypeError: items2.forEach is not a function
```

HTMLCollection에 forEach를 쓰려면 배열로 변환해야 한다. `Array.from`이나 스프레드 연산자를 쓴다.

```javascript
const items = document.getElementsByClassName('item');

Array.from(items).forEach((item, i) => {
    item.textContent = `항목 ${i + 1}`;
});

// 또는
[...items].forEach((item, i) => {
    item.textContent = `항목 ${i + 1}`;
});
```

HTMLCollection은 라이브 컬렉션이라는 점도 주의해야 한다. DOM이 변경되면 컬렉션도 같이 바뀐다. 순회 중 요소를 제거하면 인덱스가 어긋난다. NodeList(querySelectorAll 기준)는 정적이라 이 문제가 없다.

## async/await와 forEach가 어긋나는 문제

forEach 안에서 `await`를 써도 순차 실행이 안 된다. 이 함정에 빠져 시간을 날린 개발자가 한둘이 아니다. forEach의 콜백은 async 함수로 만들 수 있지만, forEach 자체가 그 Promise를 기다리지 않는다.

```javascript
const urls = ['https://api.example.com/1', 'https://api.example.com/2'];

// 의도와 다르게 동작
urls.forEach(async (url) => {
    const res = await fetch(url);
    console.log(await res.json());
});
console.log('완료');

// 출력 순서:
// 완료
// (응답 1)
// (응답 2)
```

`완료`가 먼저 찍히고, 응답은 비동기로 흘러나온다. 순차 처리가 필요하면 `for...of`로 바꿔야 한다.

```javascript
async function fetchAll(urls) {
    for (const url of urls) {
        const res = await fetch(url);
        console.log(await res.json());
    }
    console.log('완료');
}
```

병렬 처리가 목적이라면 `Promise.all`과 `map`을 쓴다.

```javascript
async function fetchAll(urls) {
    const results = await Promise.all(
        urls.map(url => fetch(url).then(r => r.json()))
    );
    console.log(results);
}
```

실제로 트랜잭션 안에서 forEach + await를 쓴 코드가 운영 중에 터진 적이 있다. 트랜잭션이 닫힌 뒤에 비동기 작업이 실행돼서 데이터 정합성이 깨졌다. 비동기 + 순서 보장이 동시에 필요하면 무조건 `for...of`다.

## break/continue 대용으로 some/every/find

forEach는 중간에 멈출 수 없다. `return`을 써도 그건 콜백 함수의 반환일 뿐, 다음 요소 처리를 막지 못한다. `throw`로 빠져나오는 트릭이 있긴 하지만 가독성이 떨어져서 잘 안 쓴다.

```javascript
const numbers = [1, 2, 3, 4, 5];

// break가 동작하지 않음 - SyntaxError
numbers.forEach(n => {
    if (n === 3) break;  // Illegal break statement
    console.log(n);
});

// return은 continue처럼 동작 (다음 요소로 진행)
numbers.forEach(n => {
    if (n === 3) return;
    console.log(n);
});
// 출력: 1, 2, 4, 5
```

조건을 만나면 즉시 멈춰야 할 때는 `some`이나 `every`를 쓴다. some은 콜백이 `true`를 반환하는 순간 멈추고, every는 `false`를 반환하는 순간 멈춘다.

```javascript
const numbers = [1, 2, 3, 4, 5];

// 3을 만나면 멈춤
numbers.some(n => {
    if (n === 3) return true;
    console.log(n);
    return false;
});
// 출력: 1, 2

// 처음으로 100을 넘는 값 찾기
const orders = [{ id: 1, price: 50 }, { id: 2, price: 120 }, { id: 3, price: 200 }];
const first = orders.find(o => o.price > 100);
console.log(first);  // { id: 2, price: 120 }
```

순회 + 조기 종료가 필요한 코드에서 some/every를 쓰는 게 관용구다. find는 값 자체가 필요할 때 쓴다. 단순히 "조기 종료 가능한 forEach"가 필요하면 `for...of`가 가장 명확하다.

## 순회 중 배열 수정의 함정

forEach 안에서 원본 배열에 `push`/`splice`를 호출하면 동작이 미묘하다. forEach는 순회 시작 시점의 길이를 기준으로 동작한다.

```javascript
const arr = [1, 2, 3];

arr.forEach((v, i) => {
    console.log(`처리: ${v}`);
    if (v === 2) arr.push(99);
});
// 출력:
// 처리: 1
// 처리: 2
// 처리: 3
// (99는 처리되지 않음)
console.log(arr);  // [1, 2, 3, 99]
```

push로 추가한 요소는 순회되지 않는다. 반대로 splice로 앞쪽을 자르면 뒷 요소를 건너뛴다.

```javascript
const arr = [1, 2, 3, 4, 5];

arr.forEach((v, i) => {
    console.log(`i=${i}, v=${v}`);
    if (v === 2) arr.splice(0, 1);  // 앞 요소 제거
});
// 출력:
// i=0, v=1
// i=1, v=2
// i=2, v=4   <- 3은 건너뜀
// i=3, v=5   (이제 arr는 [2, 3, 4, 5])
```

순회 중 인덱스 0을 제거하면 뒤 요소들이 한 칸씩 앞으로 당겨지고, 내부 카운터는 그대로 증가한다. 한 요소를 건너뛰는 결과가 된다. 순회 중 원본을 수정해야 한다면 역순 `for` 루프나 별도 결과 배열을 만들어 끝나고 교체하는 방식이 안전하다.

```javascript
// 안전한 패턴: 새 배열 생성
const arr = [1, 2, 3, 4, 5];
const filtered = arr.filter(v => v !== 3);

// 또는 역순 for 루프 (제거가 필요한 경우)
const arr2 = [1, 2, 3, 4, 5];
for (let i = arr2.length - 1; i >= 0; i--) {
    if (arr2[i] === 3) arr2.splice(i, 1);
}
```

## sparse 배열과 Array.prototype.forEach.call

희소(sparse) 배열에서 forEach는 빈 슬롯을 건너뛴다. `undefined`가 들어있는 게 아니라 슬롯 자체가 없는 경우다.

```javascript
const sparse = [1, , 3];  // 인덱스 1이 비어있음
sparse.forEach((v, i) => console.log(i, v));
// 출력:
// 0 1
// 2 3
// (인덱스 1은 건너뜀)

const withUndef = [1, undefined, 3];
withUndef.forEach((v, i) => console.log(i, v));
// 출력:
// 0 1
// 1 undefined
// 2 3
```

`new Array(5)`로 만든 배열도 sparse다. forEach가 아무것도 출력하지 않아서 당황한 경험이 있다. `Array.from({length: 5}, () => 0)`처럼 채워 만들어야 한다.

Array-like 객체(예: `arguments`, 옛 DOM API의 HTMLCollection)에는 forEach 메서드가 없지만, `Array.prototype.forEach.call`로 빌려 쓸 수 있다.

```javascript
function logArgs() {
    Array.prototype.forEach.call(arguments, (arg, i) => {
        console.log(`인자 ${i}: ${arg}`);
    });
}
logArgs('a', 'b', 'c');
// 출력:
// 인자 0: a
// 인자 1: b
// 인자 2: c

// HTMLCollection도 동일하게
const divs = document.getElementsByTagName('div');
Array.prototype.forEach.call(divs, div => {
    div.classList.add('processed');
});
```

요즘은 `Array.from(arguments).forEach(...)`나 `[...arguments].forEach(...)` 쪽이 더 읽기 좋다. 다만 화살표 함수 안에서는 `arguments`가 없으니, 그 경우는 나머지 매개변수(`...args`)로 받는 게 정석이다.

## 예외가 다른 요소를 막지 않는 점 활용

forEach 콜백 안에서 `try-catch`로 잡으면 한 요소의 실패가 다음 요소 처리를 막지 않는다. 일괄 처리 작업에서 일부 실패를 허용해야 할 때 쓴다.

```javascript
const userIds = ['u1', 'u2', 'bad-id', 'u4'];
const failed = [];

userIds.forEach(id => {
    try {
        sendNotification(id);
    } catch (err) {
        failed.push({ id, reason: err.message });
    }
});

if (failed.length > 0) {
    console.error(`실패 ${failed.length}건:`, failed);
}
```

배치 작업에서 자주 쓰는 패턴이다. 메일 발송, 푸시 알림, 외부 API 호출 같이 일부 실패가 정상인 상황에서 유용하다. 단 비동기 작업이라면 위에서 말한 대로 forEach + async가 안 되니, `Promise.allSettled`를 써야 한다.

```javascript
const results = await Promise.allSettled(
    userIds.map(id => sendNotificationAsync(id))
);

const failed = results
    .map((r, i) => ({ id: userIds[i], result: r }))
    .filter(x => x.result.status === 'rejected');
```

`Promise.all`은 하나라도 실패하면 즉시 reject되지만, `allSettled`는 모두 끝날 때까지 기다린 뒤 각각의 결과를 돌려준다. 일부 실패 허용 + 비동기 조합이면 `allSettled` 쪽이다.

## 성능 비교 - for vs for...of vs forEach

대용량 처리에서 for, for...of, forEach 사이에 의미 있는 차이가 있는지 직접 측정해봤다. 1000만 건 숫자 배열에서 단순 합산 작업이다.

```javascript
const N = 10_000_000;
const arr = new Array(N).fill(1);

// 1. 전통 for
console.time('for');
let s1 = 0;
for (let i = 0; i < arr.length; i++) s1 += arr[i];
console.timeEnd('for');

// 2. for...of
console.time('for...of');
let s2 = 0;
for (const v of arr) s2 += v;
console.timeEnd('for...of');

// 3. forEach
console.time('forEach');
let s3 = 0;
arr.forEach(v => s3 += v);
console.timeEnd('forEach');

// 측정 예시 (Node.js v20, M1 Mac):
// for: 12ms
// for...of: 120ms
// forEach: 85ms
```

수치는 환경에 따라 다르지만 경향은 비슷하다. 단순 인덱스 접근만 필요한 핫패스라면 전통 `for`가 압도적으로 빠르다. for...of는 이터레이터 프로토콜을 거쳐서 가장 느린 편이고, forEach는 함수 호출 오버헤드는 있지만 V8 최적화 덕에 for...of보다 빠른 경우가 많다.

실무 코드 99%는 이 차이가 의미 없다. API 응답 100건 처리할 때 200ns 차이는 무시할 수준이다. 성능이 정말 문제 되는 지점에서만 측정하고 바꾸면 된다. 가독성과 의도 표현이 우선이고, 그 다음이 성능이다. 다만 수백만 건 이상의 핫패스라면 한 번쯤 측정해볼 가치는 있다.

forEach는 콜백 함수 호출 비용 때문에 인덱스 기반 단순 루프보다 느리지만, 인라인 함수가 V8에서 최적화되면 격차는 줄어든다. 콜백 안에서 클로저로 외부 변수를 많이 잡거나, this 바인딩이 복잡하면 최적화가 깨져서 더 느려질 수도 있다. 벤치마크 한 번에 결론 내리지 말고, 실제 프로파일링 데이터를 봐야 한다.
