---
title: Async/Await & Promise 심화 가이드
tags: [javascript, async, await, promise, error-handling, concurrency, event-loop]
updated: 2026-06-30
---

# Async/Await & Promise 심화

## 개요

Promise는 비동기 작업의 결과를 나타내는 객체다. async/await는 그 Promise를 동기 코드처럼 읽히게 쓰는 문법이다. 콜백 중첩을 풀어내고 에러 처리를 try/catch로 일원화하려고 쓴다.

```javascript
// 콜백 중첩 (콜백 지옥)
getUser(id, (user) => {
    getOrders(user.id, (orders) => {
        getPayment(orders[0].id, (payment) => {
            console.log(payment);  // 3단 중첩
        });
    });
});

// Promise 체이닝
getUser(id)
    .then(user => getOrders(user.id))
    .then(orders => getPayment(orders[0].id))
    .then(payment => console.log(payment));

// async/await
const user = await getUser(id);
const orders = await getOrders(user.id);
const payment = await getPayment(orders[0].id);
console.log(payment);
```

## Promise 기초

```javascript
// Promise 생성
const promise = new Promise((resolve, reject) => {
    // 비동기 작업 수행
    const data = fetchData();
    if (data) {
        resolve(data);   // 성공 → then으로 전달
    } else {
        reject(new Error('데이터 없음'));  // 실패 → catch로 전달
    }
});

// Promise 상태
// pending   → 대기 (초기 상태)
// fulfilled → 이행 (resolve 호출)
// rejected  → 거부 (reject 호출)
```

상태는 한 방향으로만 전이한다. pending에서 fulfilled나 rejected로 한 번 바뀌면 다시 돌아오지 않고, 그 뒤의 resolve/reject 호출은 무시된다.

즉시 만들어진 Promise가 필요할 때는 정적 메서드를 쓴다.

```javascript
Promise.resolve(42);           // 즉시 이행된 Promise
Promise.reject(new Error());   // 즉시 거부된 Promise
```

## Promise 체이닝

```javascript
fetch('/api/users/1')
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();        // 새 Promise 반환
    })
    .then(user => {
        return fetch(`/api/orders?userId=${user.id}`);
    })
    .then(response => response.json())
    .then(orders => {
        console.log('주문:', orders);
    })
    .catch(error => {
        console.error('에러:', error);  // 체인 어디서 발생해도 여기서 잡음
    })
    .finally(() => {
        hideLoadingSpinner();           // 성공/실패 무관하게 실행
    });
```

`then`이 항상 새 Promise를 반환한다는 게 체이닝의 전부다. 콜백에서 값을 반환하면 다음 `then`이 그 값을 받고, Promise를 반환하면 그게 풀릴 때까지 다음 `then`이 기다린다.

## Promise 조합 메서드

```javascript
const userPromise = fetch('/api/user');
const ordersPromise = fetch('/api/orders');
const cartPromise = fetch('/api/cart');

// Promise.all: 모두 성공해야 함. 하나라도 실패하면 전체 실패
const [user, orders, cart] = await Promise.all([
    userPromise.then(r => r.json()),
    ordersPromise.then(r => r.json()),
    cartPromise.then(r => r.json()),
]);

// Promise.allSettled: 결과 상관없이 모두 완료까지 대기
// 실패해도 나머지 결과는 받음
const results = await Promise.allSettled([
    fetch('/api/user'),
    fetch('/api/orders'),
    fetch('/api/cart'),
]);
// results: [
//   { status: 'fulfilled', value: Response },
//   { status: 'rejected', reason: Error },
//   { status: 'fulfilled', value: Response },
// ]

// Promise.race: 가장 빠르게 끝난 하나 (성공이든 실패든)
const fastest = await Promise.race([
    fetch('/api/server1'),
    fetch('/api/server2'),
]);

// Promise.any: 첫 번째 성공 (ES2021). 모두 실패하면 AggregateError
const firstSuccess = await Promise.any([
    fetch('/api/cache'),
    fetch('/api/db'),
    fetch('/api/fallback'),
]);
```

| 메서드 | 완료 조건 | 실패 조건 | 용도 |
|--------|---------|---------|------|
| `all` | 모두 성공 | 하나라도 실패 | 병렬 API 호출 |
| `allSettled` | 모두 완료 | 실패 없음 | 결과 개별 확인 |
| `race` | 첫 번째 완료 | 첫 번째가 실패 | 타임아웃, 최빠른 응답 |
| `any` | 첫 번째 성공 | 모두 실패 | 폴백 패턴 |

`Promise.all`은 하나가 실패하면 즉시 reject하지만, 이미 시작된 나머지 요청을 취소하지는 않는다. 실패 후에도 다른 요청은 계속 돌아 응답이 오고, 그 결과는 버려진다. 취소까지 필요하면 뒤에 나오는 AbortController를 같이 써야 한다.

## async/await

```javascript
// async 함수는 항상 Promise를 반환
async function fetchUser(id) {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();  // Promise<User>를 반환
}

// 호출
const user = await fetchUser(1);
// 또는
fetchUser(1).then(user => console.log(user));
```

### 에러 처리

```javascript
// try/catch
async function getOrderDetail(orderId) {
    try {
        const order = await fetchOrder(orderId);
        const payment = await fetchPayment(order.paymentId);
        const delivery = await fetchDelivery(order.deliveryId);
        return { order, payment, delivery };
    } catch (error) {
        if (error instanceof NetworkError) {
            return getCachedOrderDetail(orderId);  // 폴백
        }
        throw error;  // 알 수 없는 에러는 재throw
    }
}

// .catch() 체이닝
const user = await fetchUser(id).catch(err => null);
if (!user) {
    // 사용자 없음 처리
}

// [err, data] 튜플 유틸
async function to(promise) {
    try {
        const data = await promise;
        return [null, data];
    } catch (error) {
        return [error, null];
    }
}

const [err, user] = await to(fetchUser(id));
if (err) {
    console.error('실패:', err);
}
```

## 병렬 vs 순차 실행

await를 잘못 쓰면 동시에 끝낼 수 있는 작업을 줄 세워 느려진다.

```javascript
// 순차 실행 (느림: 3초)
const user = await fetchUser();      // 1초
const orders = await fetchOrders();  // 1초
const cart = await fetchCart();      // 1초
// 총 3초

// 병렬 실행 (1초)
const [user, orders, cart] = await Promise.all([
    fetchUser(),      // 1초 ─┐
    fetchOrders(),    // 1초 ─┤── 동시 실행
    fetchCart(),      // 1초 ─┘
]);
// 총 1초

// 앞 결과가 필요하면 순차, 나머지는 병렬
const user = await fetchUser();  // user가 있어야 다음 호출 가능
const [orders, cart] = await Promise.all([
    fetchOrders(user.id),
    fetchCart(user.id),
]);
```

순차/병렬의 갈림길은 "다음 작업이 앞 작업 결과를 쓰는가"다. 안 쓰면 병렬로 묶을 수 있다.

## 실전 패턴

### 타임아웃

```javascript
function withTimeout(promise, ms) {
    const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    );
    return Promise.race([promise, timeout]);
}

const user = await withTimeout(fetchUser(id), 5000);
```

`Promise.race`로 원본과 타임아웃 Promise를 경쟁시킨다. 타임아웃이 먼저 reject되면 그 에러가 나오지만, 여기서도 원본 요청 자체는 멈추지 않는다. fetch라면 signal로 실제 취소까지 묶는 편이 낫다.

### 재시도

```javascript
async function retry(fn, maxAttempts = 3, delay = 1000) {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (attempt === maxAttempts) throw error;
            await new Promise(r => setTimeout(r, delay * attempt));  // 시도마다 대기 증가
        }
    }
}

const data = await retry(() => fetch('/api/data'), 3, 1000);
```

재시도에 무조건 모든 에러를 넣으면 안 된다. 4xx 같은 클라이언트 에러는 다시 보내도 똑같이 실패하므로, 재시도는 네트워크 오류나 5xx, 타임아웃에만 거는 게 맞다.

### 동시성 제한

```javascript
// 한 번에 최대 N개만 병렬 실행
async function parallelLimit(tasks, limit) {
    const results = [];
    const executing = new Set();

    for (const task of tasks) {
        const promise = task().then(result => {
            executing.delete(promise);
            return result;
        });
        executing.add(promise);
        results.push(promise);

        if (executing.size >= limit) {
            await Promise.race(executing);
        }
    }
    return Promise.all(results);
}

// 100개 요청을 5개씩 묶어 처리
const urls = Array.from({ length: 100 }, (_, i) => `/api/items/${i}`);
const results = await parallelLimit(
    urls.map(url => () => fetch(url).then(r => r.json())),
    5
);
```

`Promise.all`에 100개를 한 번에 던지면 서버 입장에서는 동시 접속 100개다. 상대 API에 rate limit이 있거나 DB 커넥션 풀이 작으면 이쪽이 먼저 터진다. 외부 자원을 건드리는 대량 호출은 동시성을 묶어야 한다.

### 순차 처리 (for...of)

```javascript
const files = ['file1.txt', 'file2.txt', 'file3.txt'];

// forEach는 내부 async 함수의 await를 기다리지 않음
files.forEach(async (file) => {
    await processFile(file);  // 셋이 동시에 시작됨
});

// for...of는 한 번에 하나씩 끝까지 기다림
for (const file of files) {
    await processFile(file);
}
```

`forEach`에 async 콜백을 넘기면 콜백이 반환하는 Promise를 `forEach`가 그냥 버린다. 순서 보장이나 완료 대기가 필요하면 `for...of`를 쓴다.

### AbortController (요청 취소)

```javascript
const controller = new AbortController();

// 5초 후 자동 취소
setTimeout(() => controller.abort(), 5000);

try {
    const response = await fetch('/api/data', {
        signal: controller.signal,
    });
    const data = await response.json();
} catch (error) {
    if (error.name === 'AbortError') {
        console.log('요청이 취소되었습니다');
    }
}

// React에서 컴포넌트 언마운트 시 취소
useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();  // 클린업
}, []);
```

타임아웃 한 줄짜리는 `AbortSignal.timeout(5000)`으로도 만들 수 있다. 여러 요청을 한 번에 끊으려면 같은 signal을 모든 fetch에 넘기면 된다.

## Node.js에서의 함정

### await + 스트림/이벤트

스트림은 Promise가 아니라 이벤트로 완료를 알린다. 그냥 `await stream` 하면 안 되고, 완료 이벤트를 Promise로 감싸야 한다. Node에는 이걸 해주는 헬퍼가 있다.

```javascript
const fs = require('fs');
const { pipeline } = require('stream/promises');
const { once } = require('events');

// stream/promises의 pipeline: 스트림 연결 + 완료까지 await
await pipeline(
    fs.createReadStream('input.txt'),
    transformStream,
    fs.createWriteStream('output.txt')
);

// 단일 이벤트는 events.once로 await
const server = http.createServer().listen(3000);
await once(server, 'listening');

// for await...of로 스트림 청크를 순회
const readStream = fs.createReadStream('big.log', { encoding: 'utf8' });
for await (const chunk of readStream) {
    process(chunk);  // 청크가 올 때마다 순차 처리, 백프레셔 자동 적용
}
```

직접 `new Promise`로 `'end'`, `'error'` 이벤트를 감쌀 때는 `'error'` 리스너를 빠뜨리면 안 된다. 에러 이벤트를 안 잡으면 reject가 아니라 프로세스가 그대로 죽는다.

```javascript
function streamToString(stream) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        stream.on('data', c => chunks.push(c));
        stream.on('end', () => resolve(Buffer.concat(chunks).toString()));
        stream.on('error', reject);  // 이거 빠뜨리면 프로세스 crash
    });
}
```

### top-level await (ESM)

ESM(`.mjs` 또는 `"type": "module"`)에서는 함수 밖에서 바로 await를 쓸 수 있다. 편하지만 모듈 로딩을 막는다는 점을 알고 써야 한다.

```javascript
// config.mjs
const res = await fetch('https://example.com/config.json');
export const config = await res.json();
```

이 모듈을 import하는 쪽은 위 await가 끝날 때까지 평가가 멈춘다. top-level await가 느리면 그 모듈에 의존하는 전체 그래프의 시작이 늦어진다. 초기화 시점에 네트워크나 DB를 때리는 top-level await는 앱 부팅을 그만큼 지연시키므로 주의해야 한다.

CommonJS(`require`)에서는 top-level await를 못 쓴다. `SyntaxError`가 난다. CJS에서 비슷한 게 필요하면 즉시 실행 async 함수로 감싸는 수밖에 없는데, 이러면 초기화 완료 시점을 호출부가 알 수 없어서 보통은 init Promise를 export해서 await하게 만든다.

### return await를 빠뜨려 try/catch가 못 잡는 경우

async 함수 안에서 Promise를 `await` 없이 그냥 `return`하면, 그 Promise는 함수가 끝난 뒤에 풀린다. 그래서 함수 안의 try/catch 밖에서 reject가 일어나고, 같은 함수의 catch가 못 잡는다.

```javascript
// catch가 동작하지 않음
async function load() {
    try {
        return fetchData();  // await 없이 반환
    } catch (error) {
        // fetchData가 reject돼도 여기 안 들어옴
        console.error('여기 안 옴', error);
        return null;
    }
}

// return await로 잡아야 함
async function load() {
    try {
        return await fetchData();  // 여기서 풀리므로 reject가 catch로 감
    } catch (error) {
        console.error('정상적으로 잡힘', error);
        return null;
    }
}
```

try/catch가 없는 위치라면 `return await`와 `return`은 결과가 같고, `return await`는 마이크로태스크 한 번을 더 쓴다. 그래서 ESLint `no-return-await` 규칙이 한때 `return await`를 빼라고 했다. 함정은 try/catch나 try/finally 안에서는 의미가 달라진다는 점이다. 이 위치에서는 `return await`가 맞다. 그래서 요즘 ESLint는 `no-return-await`를 폐기하고 `@typescript-eslint/return-await`로 "try 안에서는 await, 밖에서는 빼라"를 구분해 검사한다.

## 안티패턴

await 없이 단순 반환하면 되는데 async/await로 한 겹 더 감싸는 경우다. try/catch가 없다면 굳이 await할 이유가 없다.

```javascript
// 불필요한 async/await
async function getUser(id) {
    return await fetchUser(id);  // try/catch 없으면 await 불필요
}
// 권장
function getUser(id) {
    return fetchUser(id);  // Promise를 그대로 반환
}
```

반복문 안에서 await를 거는 경우다. 앞 결과가 필요 없는데도 하나씩 줄 세운다.

```javascript
// 순차 실행됨 (느림)
for (const id of userIds) {
    const user = await fetchUser(id);
    results.push(user);
}
// 병렬 실행
const results = await Promise.all(userIds.map(id => fetchUser(id)));
```

에러 처리 없는 async 함수다. await 대상이 reject되면 잡히지 않은 거부가 된다. Node에서는 기본적으로 프로세스를 종료시킨다.

```javascript
// 에러를 처리하지 않음
async function process() {
    const data = await riskyOperation();  // reject 시 UnhandledPromiseRejection
}
// 처리
async function process() {
    try {
        const data = await riskyOperation();
    } catch (error) {
        handleError(error);
    }
}
```

Promise 생성자 안에 async 콜백을 넣는 경우다. executor 안에서 던진 에러는 reject로 연결되지 않아 그대로 삼켜진다.

```javascript
// executor 안의 에러가 사라짐
new Promise(async (resolve) => {
    const data = await fetch(url);  // 여기서 throw나면 어디서도 못 잡음
    resolve(data);
});
// async 함수로 직접 반환
async function getData() {
    return fetch(url);
}
```

## 마이크로태스크와 실행 순서

await와 then 콜백이 어느 tick에 실행되는지, 마이크로태스크 큐가 매크로태스크보다 먼저 비워지는 규칙은 별도 문서에서 명세 수준으로 정리했다.

- [Promise 내부 동작 과정](../04_심화_JavaScript/Promise 내부 동작 과정.md) — 상태 슬롯, reaction 큐, await의 desugar, 마이크로태스크 고갈 규칙

## 참고

- [MDN Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise)
- [MDN async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
- [실행 순서 이해](실행 순서 이해.md) — 이벤트 루프 기초
- [Closure](../01_기본_JavaScript/Closure/Closure.md) — 비동기 콜백과 클로저
