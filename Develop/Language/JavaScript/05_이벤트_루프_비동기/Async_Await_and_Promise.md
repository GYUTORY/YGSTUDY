---
title: Async/Await & Promise 심화 가이드
tags: [javascript, async, await, promise, error-handling, concurrency, event-loop]
updated: 2026-03-01
---

# Async/Await & Promise 심화

## 개요

Promise는 **비동기 작업의 결과를 나타내는 객체**이고, async/await는 Promise를 **동기 코드처럼 작성**할 수 있는 문법이다. 콜백 지옥을 해결하고 가독성 높은 비동기 코드를 작성하는 핵심 기술이다.

```javascript
// ❌ 콜백 지옥
getUser(id, (user) => {
    getOrders(user.id, (orders) => {
        getPayment(orders[0].id, (payment) => {
            console.log(payment);  // 3단 중첩
        });
    });
});

// ✅ Promise 체이닝
getUser(id)
    .then(user => getOrders(user.id))
    .then(orders => getPayment(orders[0].id))
    .then(payment => console.log(payment));

// ✅✅ async/await (가장 가독성 좋음)
const user = await getUser(id);
const orders = await getOrders(user.id);
const payment = await getPayment(orders[0].id);
console.log(payment);
```

## 핵심

### 1. Promise 기초

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
// pending  → 대기 (초기 상태)
// fulfilled → 이행 (resolve 호출)
// rejected  → 거부 (reject 호출)
```

#### 즉시 생성 유틸

```javascript
Promise.resolve(42);           // 즉시 이행된 Promise
Promise.reject(new Error());   // 즉시 거부된 Promise
```

### 2. Promise 체이닝

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
        console.error('에러:', error);  // 어디서든 발생한 에러 잡음
    })
    .finally(() => {
        hideLoadingSpinner();           // 성공/실패 무관하게 실행
    });
```

### 3. Promise 조합 메서드

```javascript
const userPromise = fetch('/api/user');
const ordersPromise = fetch('/api/orders');
const cartPromise = fetch('/api/cart');

// ── Promise.all: 모두 성공해야 ──
// 하나라도 실패하면 전체 실패
const [user, orders, cart] = await Promise.all([
    userPromise.then(r => r.json()),
    ordersPromise.then(r => r.json()),
    cartPromise.then(r => r.json()),
]);

// ── Promise.allSettled: 결과 상관없이 모두 완료 대기 ──
// 실패해도 다른 결과는 받을 수 있음
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

// ── Promise.race: 가장 빠른 하나 ──
const fastest = await Promise.race([
    fetch('/api/server1'),
    fetch('/api/server2'),
]);

// ── Promise.any: 첫 번째 성공 (ES2021) ──
// 모두 실패하면 AggregateError
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

### 4. async/await

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

#### 에러 처리

```javascript
// 방법 1: try/catch (권장)
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

// 방법 2: .catch() 체이닝
const user = await fetchUser(id).catch(err => null);
if (!user) {
    // 사용자 없음 처리
}

// 방법 3: 유틸 함수
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

### 5. 병렬 vs 순차 실행

```javascript
// ❌ 순차 실행 (느림: 3초)
const user = await fetchUser();      // 1초
const orders = await fetchOrders();  // 1초
const cart = await fetchCart();      // 1초
// 총 3초

// ✅ 병렬 실행 (빠름: 1초)
const [user, orders, cart] = await Promise.all([
    fetchUser(),      // 1초 ─┐
    fetchOrders(),    // 1초 ─┤── 동시 실행
    fetchCart(),      // 1초 ─┘
]);
// 총 1초

// ✅ 일부는 순차, 일부는 병렬
const user = await fetchUser();  // 순차 (user 필요)
const [orders, cart] = await Promise.all([
    fetchOrders(user.id),   // 병렬
    fetchCart(user.id),     // 병렬
]);
```

### 6. 실전 패턴

#### 타임아웃 패턴

```javascript
function withTimeout(promise, ms) {
    const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    );
    return Promise.race([promise, timeout]);
}

const user = await withTimeout(fetchUser(id), 5000);
```

#### 재시도 패턴

```javascript
async function retry(fn, maxAttempts = 3, delay = 1000) {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (attempt === maxAttempts) throw error;
            await new Promise(r => setTimeout(r, delay * attempt));  // 지수 백오프
        }
    }
}

const data = await retry(() => fetch('/api/data'), 3, 1000);
```

#### 동시성 제한 (Concurrency Limit)

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

// 100개 API 요청을 5개씩 병렬 처리
const urls = Array.from({ length: 100 }, (_, i) => `/api/items/${i}`);
const results = await parallelLimit(
    urls.map(url => () => fetch(url).then(r => r.json())),
    5  // 최대 5개 동시 요청
);
```

#### 순차 처리 (for...of)

```javascript
// 순서를 보장하며 하나씩 처리
const files = ['file1.txt', 'file2.txt', 'file3.txt'];

// ❌ forEach는 await를 기다리지 않음
files.forEach(async (file) => {
    await processFile(file);  // 병렬 실행됨!
});

// ✅ for...of는 순차 실행
for (const file of files) {
    await processFile(file);  // 순차 실행
}
```

#### AbortController (요청 취소)

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

### 7. 마이크로태스크 & 실행 순서

```javascript
console.log('1. 동기');

setTimeout(() => console.log('2. 매크로태스크 (setTimeout)'), 0);

Promise.resolve().then(() => console.log('3. 마이크로태스크 (Promise)'));

queueMicrotask(() => console.log('4. 마이크로태스크 (queueMicrotask)'));

console.log('5. 동기');

// 출력 순서:
// 1. 동기
// 5. 동기
// 3. 마이크로태스크 (Promise)
// 4. 마이크로태스크 (queueMicrotask)
// 2. 매크로태스크 (setTimeout)
```

```
실행 순서:
  1. 콜 스택 (동기 코드) — 가장 먼저
  2. 마이크로태스크 큐 (Promise, queueMicrotask, MutationObserver)
  3. 매크로태스크 큐 (setTimeout, setInterval, I/O)

  콜 스택 비움 → 마이크로태스크 전부 처리 → 매크로태스크 1개 → 반복
```

### 8. 안티패턴

```javascript
// ❌ 불필요한 async/await
async function getUser(id) {
    return await fetchUser(id);  // await 불필요
}
// ✅
function getUser(id) {
    return fetchUser(id);  // Promise를 그대로 반환
}

// ❌ await in loop (순차 실행됨)
for (const id of userIds) {
    const user = await fetchUser(id);  // 하나씩 순차
    results.push(user);
}
// ✅ Promise.all (병렬 실행)
const results = await Promise.all(userIds.map(id => fetchUser(id)));

// ❌ catch 없는 async 함수
async function process() {
    const data = await riskyOperation();  // 에러 시 UnhandledPromiseRejection
}
// ✅ 항상 에러 처리
async function process() {
    try {
        const data = await riskyOperation();
    } catch (error) {
        handleError(error);
    }
}

// ❌ Promise 생성자 안에서 async 사용
new Promise(async (resolve) => {  // 에러가 삼켜짐
    const data = await fetch(url);
    resolve(data);
});
// ✅ async 함수로 직접 반환
async function getData() {
    return fetch(url);
}
```

## 참고

- [MDN Promise](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise)
- [MDN async function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
- [이벤트 루프](실행 순서 이해.md) — 이벤트 루프 기초
- [Closure](../01_기본_JavaScript/Closure/Closure.md) — 비동기 콜백과 클로저
