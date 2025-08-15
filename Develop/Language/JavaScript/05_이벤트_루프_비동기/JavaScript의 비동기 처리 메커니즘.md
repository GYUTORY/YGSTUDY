---
title: JavaScript
tags: [language, javascript, 05이벤트루프비동기, javascript의-비동기-처리-메커니즘, java]
updated: 2025-08-10
---
# JavaScript의 비동기 처리 메커니즘

## 1. 동기(Synchronous) vs 비동기(Asynchronous)

JavaScript는 기본적으로 싱글 스레드 언어입니다. 즉, 한 번에 하나의 작업만 수행할 수 있습니다. 하지만 웹 애플리케이션에서는 네트워크 요청, 파일 읽기, 타이머 등 여러 작업을 동시에 처리해야 할 필요가 있습니다. 이를 위해 JavaScript는 비동기 처리 메커니즘을 제공합니다.

## 배경
```javascript
console.log('1. 시작');
console.log('2. 중간');
console.log('3. 끝');
// 출력:
// 1. 시작
// 2. 중간
// 3. 끝
```

```javascript
console.log('1. 시작');

setTimeout(() => {
    console.log('2. 비동기 작업');
}, 1000);

console.log('3. 끝');
// 출력:
// 1. 시작
// 3. 끝
// 2. 비동기 작업 (1초 후)
```

```javascript
console.log('1. 스크립트 시작');

setTimeout(() => {
    console.log('2. setTimeout 콜백');
}, 0);

Promise.resolve().then(() => {
    console.log('3. Promise 콜백');
});

console.log('4. 스크립트 끝');

// 출력:
// 1. 스크립트 시작
// 4. 스크립트 끝
// 3. Promise 콜백
// 2. setTimeout 콜백
```

```javascript
function fetchData(callback) {
    setTimeout(() => {
        const data = { id: 1, name: 'John' };
        callback(data);
    }, 1000);
}

fetchData((data) => {
    console.log('받은 데이터:', data);
});
```

```javascript
async function fetchMultipleResources() {
    // 순차 처리
    console.time('순차 처리');
    const result1 = await fetch('/api/resource1');
    const result2 = await fetch('/api/resource2');
    const result3 = await fetch('/api/resource3');
    console.timeEnd('순차 처리');

    // 병렬 처리
    console.time('병렬 처리');
    const [result4, result5, result6] = await Promise.all([
        fetch('/api/resource1'),
        fetch('/api/resource2'),
        fetch('/api/resource3')
    ]);
    console.timeEnd('병렬 처리');
}
```










## 2. 이벤트 루프(Event Loop)

이벤트 루프는 JavaScript의 비동기 처리를 가능하게 하는 핵심 메커니즘입니다. 이벤트 루프는 다음과 같은 구성요소로 이루어져 있습니다:

1. **콜 스택(Call Stack)**: 실행 중인 코드의 위치를 추적
2. **태스크 큐(Task Queue)**: 비동기 작업의 콜백 함수들이 대기하는 곳
3. **마이크로태스크 큐(Microtask Queue)**: Promise의 콜백 함수들이 대기하는 곳

## 3. 콜백(Callback)

콜백은 비동기 작업이 완료된 후 실행될 함수를 지정하는 방식입니다.

### 콜백 지옥(Callback Hell)
콜백을 중첩해서 사용하면 코드가 복잡해지고 가독성이 떨어집니다.

```javascript
fetchUserData((user) => {
    fetchUserPosts(user.id, (posts) => {
        fetchPostComments(posts[0].id, (comments) => {
            console.log('댓글:', comments);
        });
    });
});
```

## 4. Promise

Promise는 비동기 작업의 최종 완료(또는 실패)와 그 결과값을 나타내는 객체입니다.

### Promise 기본 사용법
```javascript
const promise = new Promise((resolve, reject) => {
    setTimeout(() => {
        const success = true;
        if (success) {
            resolve('작업 성공!');
        } else {
            reject('작업 실패!');
        }
    }, 1000);
});

promise
    .then((result) => {
        console.log(result);
    })
    .catch((error) => {
        console.error(error);
    });
```

### Promise 체이닝
```javascript
fetchUserData()
    .then(user => fetchUserPosts(user.id))
    .then(posts => fetchPostComments(posts[0].id))
    .then(comments => console.log('댓글:', comments))
    .catch(error => console.error('에러:', error));
```

### Promise.all
여러 Promise를 병렬로 실행하고 모든 결과를 기다립니다.

```javascript
const promise1 = fetch('/api/data1');
const promise2 = fetch('/api/data2');
const promise3 = fetch('/api/data3');

Promise.all([promise1, promise2, promise3])
    .then(results => {
        console.log('모든 데이터:', results);
    })
    .catch(error => {
        console.error('에러 발생:', error);
    });
```

## 5. async/await

async/await는 Promise를 더 쉽게 사용할 수 있게 해주는 문법적 설탕입니다.

### async/await 기본 사용법
```javascript
async function fetchUserData() {
    try {
        const response = await fetch('/api/user');
        const user = await response.json();
        return user;
    } catch (error) {
        console.error('에러:', error);
    }
}
```

### async/await를 사용한 복잡한 비동기 처리
```javascript
async function processUserData() {
    try {
        // 사용자 데이터 가져오기
        const user = await fetchUserData();
        console.log('사용자:', user);

        // 사용자의 게시물 가져오기
        const posts = await fetchUserPosts(user.id);
        console.log('게시물:', posts);

        // 각 게시물의 댓글 가져오기
        const commentsPromises = posts.map(post => 
            fetchPostComments(post.id)
        );
        const comments = await Promise.all(commentsPromises);
        console.log('댓글들:', comments);

        return { user, posts, comments };
    } catch (error) {
        console.error('처리 중 에러 발생:', error);
        throw error;
    }
}
```

## 6. 실제 사용 예시: API 통신

### REST API 호출 예시
```javascript
async function fetchUserProfile(userId) {
    try {
        // 사용자 정보 가져오기
        const userResponse = await fetch(`/api/users/${userId}`);
        const user = await userResponse.json();

        // 사용자의 주문 내역 가져오기
        const ordersResponse = await fetch(`/api/users/${userId}/orders`);
        const orders = await ordersResponse.json();

        // 사용자의 리뷰 가져오기
        const reviewsResponse = await fetch(`/api/users/${userId}/reviews`);
        const reviews = await reviewsResponse.json();

        return {
            user,
            orders,
            reviews
        };
    } catch (error) {
        console.error('프로필 로딩 실패:', error);
        throw error;
    }
}

// 사용 예시
async function displayUserProfile(userId) {
    try {
        const profile = await fetchUserProfile(userId);
        console.log('사용자 프로필:', profile);
    } catch (error) {
        console.error('프로필 표시 실패:', error);
    }
}
```

## 7. 에러 처리

### Promise의 에러 처리
```javascript
function riskyOperation() {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            const random = Math.random();
            if (random > 0.5) {
                resolve('성공!');
            } else {
                reject(new Error('실패!'));
            }
        }, 1000);
    });
}

// 방법 1: try-catch
async function handleError1() {
    try {
        const result = await riskyOperation();
        console.log(result);
    } catch (error) {
        console.error('에러 발생:', error);
    }
}

// 방법 2: Promise 체이닝
function handleError2() {
    riskyOperation()
        .then(result => console.log(result))
        .catch(error => console.error('에러 발생:', error));
}
```

## 8. 성능 최적화

## 9. 실전 팁

1. **Promise.all vs Promise.allSettled**
```javascript
// Promise.all: 하나라도 실패하면 전체 실패
Promise.all([promise1, promise2, promise3])
    .then(results => console.log('모두 성공:', results))
    .catch(error => console.error('하나라도 실패:', error));

// Promise.allSettled: 모든 Promise의 결과를 기다림
Promise.allSettled([promise1, promise2, promise3])
    .then(results => {
        results.forEach(result => {
            if (result.status === 'fulfilled') {
                console.log('성공:', result.value);
            } else {
                console.log('실패:', result.reason);
            }
        });
    });
```

2. **타임아웃 처리**
```javascript
function timeout(ms) {
    return new Promise((_, reject) => {
        setTimeout(() => reject(new Error('타임아웃')), ms);
    });
}

async function fetchWithTimeout(url, ms) {
    try {
        const response = await Promise.race([
            fetch(url),
            timeout(ms)
        ]);
        return response;
    } catch (error) {
        console.error('요청 실패:', error);
        throw error;
    }
}
```

## 10. 결론

JavaScript의 비동기 처리 메커니즘은 현대 웹 개발에서 필수적인 요소입니다. 콜백부터 시작하여 Promise, async/await까지 발전해온 이 메커니즘들은 각각의 장단점이 있습니다. 상황에 맞는 적절한 방식을 선택하여 사용하는 것이 중요합니다.

- 콜백: 간단한 비동기 작업에 적합
- Promise: 복잡한 비동기 작업의 체이닝에 적합
- async/await: 가독성이 좋고 에러 처리가 쉬움

이러한 비동기 처리 메커니즘을 잘 이해하고 활용하면, 더 효율적이고 유지보수가 용이한 코드를 작성할 수 있습니다.

