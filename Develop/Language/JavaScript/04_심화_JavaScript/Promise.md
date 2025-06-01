# JavaScript Promise 핸들링 완벽 가이드

## 1. Promise의 기본 개념

### Promise란?
Promise는 JavaScript에서 비동기 작업을 처리하기 위한 객체입니다. 비동기 작업의 최종 완료(또는 실패)와 그 결과값을 나타내며, 콜백 지옥을 해결하기 위해 도입되었습니다.

```javascript
// 기본적인 Promise 생성
const promise = new Promise((resolve, reject) => {
    // 비동기 작업 수행
    setTimeout(() => {
        const random = Math.random();
        if (random > 0.5) {
            resolve('작업 성공!');
        } else {
            reject(new Error('작업 실패!'));
        }
    }, 1000);
});

// Promise 사용
promise
    .then(result => {
        console.log('성공:', result);
        return result.toUpperCase(); // 체이닝 가능
    })
    .then(uppercaseResult => {
        console.log('대문자 변환:', uppercaseResult);
    })
    .catch(error => {
        console.error('에러 발생:', error.message);
    })
    .finally(() => {
        console.log('작업 완료 (성공/실패 상관없이 실행)');
    });
```

### Promise의 상태
Promise는 다음 세 가지 상태 중 하나를 가집니다:

1. **pending**: 초기 상태, 이행되지도 거부되지도 않은 상태
2. **fulfilled**: 작업이 성공적으로 완료된 상태
3. **rejected**: 작업이 실패한 상태

```javascript
// Promise 상태 확인 예제
const checkPromise = new Promise((resolve, reject) => {
    console.log('Promise 생성 직후 상태: pending');
    
    setTimeout(() => {
        resolve('성공');
        console.log('resolve 호출 후 상태: fulfilled');
    }, 1000);
});

console.log('Promise 객체:', checkPromise); // Promise { <pending> }
```

## 2. async/await과 Promise의 관계

### async/await 소개
async/await는 Promise를 더 쉽게 사용할 수 있게 해주는 문법적 설탕(syntactic sugar)입니다. 코드를 동기적으로 작성하듯이 비동기 코드를 작성할 수 있게 해줍니다.

```javascript
// Promise를 사용한 코드
function fetchUserData() {
    return fetch('https://api.example.com/user')
        .then(response => response.json())
        .then(data => {
            console.log('사용자 데이터:', data);
            return data;
        })
        .catch(error => {
            console.error('에러 발생:', error);
            throw error;
        });
}

// async/await를 사용한 동일한 코드
async function fetchUserData() {
    try {
        const response = await fetch('https://api.example.com/user');
        const data = await response.json();
        console.log('사용자 데이터:', data);
        return data;
    } catch (error) {
        console.error('에러 발생:', error);
        throw error;
    }
}
```

### async/await의 장점
1. **가독성 향상**: 비동기 코드를 동기 코드처럼 작성할 수 있습니다.
2. **에러 처리 용이**: try-catch 블록으로 에러 처리가 가능합니다.
3. **디버깅 용이**: 동기 코드처럼 디버깅이 가능합니다.

```javascript
// 복잡한 비동기 작업 예제
async function processUserData(userId) {
    try {
        // 사용자 정보 가져오기
        const userResponse = await fetch(`https://api.example.com/users/${userId}`);
        const userData = await userResponse.json();
        
        // 사용자의 게시물 가져오기
        const postsResponse = await fetch(`https://api.example.com/users/${userId}/posts`);
        const postsData = await postsResponse.json();
        
        // 사용자의 친구 목록 가져오기
        const friendsResponse = await fetch(`https://api.example.com/users/${userId}/friends`);
        const friendsData = await friendsResponse.json();
        
        return {
            user: userData,
            posts: postsData,
            friends: friendsData
        };
    } catch (error) {
        console.error('데이터 처리 중 에러 발생:', error);
        throw error;
    }
}
```

## 3. async 메서드에서 await 없이 try-catch 사용 시 주의사항

### async/await와 try-catch의 관계
async/await와 try-catch는 함께 사용할 때 매우 강력한 에러 처리 메커니즘을 제공합니다. 하지만 await 키워드 없이 Promise를 사용하면 try-catch가 제대로 작동하지 않습니다.

### 잘못된 사용 예시와 설명
```javascript
// 잘못된 사용 예시
async function wrongExample() {
    try {
        fetch('https://api.example.com/data'); // await 없음
        console.log('이 코드는 fetch가 완료되기 전에 실행됨');
    } catch (error) {
        console.error('에러 발생:', error);
    }
}

// 위 코드의 실행 순서
wrongExample();
console.log('메인 코드 실행');
// 출력 순서:
// 1. "이 코드는 fetch가 완료되기 전에 실행됨"
// 2. "메인 코드 실행"
// 3. (나중에) fetch 응답
```

위 코드의 문제점:
1. **비동기 작업 미대기**
   ```javascript
   // 문제가 있는 코드
   async function wrongExample() {
       try {
           fetch('https://api.example.com/data'); // await 없음
           console.log('이 코드는 fetch가 완료되기 전에 실행됨');
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }

   // 실행 결과
   wrongExample();
   console.log('메인 코드 실행');
   // 출력 순서:
   // 1. "이 코드는 fetch가 완료되기 전에 실행됨"
   // 2. "메인 코드 실행"
   // 3. (나중에) fetch 응답
   ```
   - fetch()는 Promise를 반환하지만, await 없이 호출하면 Promise의 완료를 기다리지 않습니다.
   - Promise가 완료되기 전에 다음 코드가 실행되어 예상치 못한 동작이 발생합니다.
   - 실제 API 응답을 받기 전에 다음 단계의 코드가 실행될 수 있습니다.

2. **에러 캐치 실패**
   ```javascript
   // 문제가 있는 코드
   async function errorExample() {
       try {
           fetch('https://api.example.com/nonexistent'); // 존재하지 않는 API
           console.log('API 호출 완료');
       } catch (error) {
           console.error('에러 발생:', error); // 이 catch 블록은 실행되지 않음
       }
   }

   // 올바른 코드
   async function correctErrorExample() {
       try {
           const response = await fetch('https://api.example.com/nonexistent');
           console.log('API 호출 완료');
       } catch (error) {
           console.error('에러 발생:', error); // 이제 에러를 잡을 수 있음
       }
   }
   ```

   ### Promise의 reject 상태와 try-catch의 관계

   Promise의 reject 상태가 try-catch로 전파되지 않는 이유는 JavaScript의 이벤트 루프와 비동기 처리 방식 때문입니다:

   1. **이벤트 루프와 마이크로태스크 큐**
   ```javascript
   // Promise의 reject는 마이크로태스크 큐에 들어감
   async function explainEventLoop() {
       try {
           // 1. fetch()는 Promise를 반환하고 즉시 다음 코드로 진행
           fetch('https://api.example.com/nonexistent');
           
           // 2. 이 코드는 fetch의 Promise가 reject되기 전에 실행됨
           console.log('이 코드는 Promise reject 전에 실행됨');
           
           // 3. try-catch 블록이 끝난 후에 Promise가 reject됨
       } catch (error) {
           // 4. 이 catch 블록은 실행되지 않음
           console.error('에러 발생:', error);
       }
   }
   ```

   2. **await의 동작 방식**
   ```javascript
   async function explainAwait() {
       try {
           // 1. await은 Promise가 완료될 때까지 함수 실행을 일시 중지
           const response = await fetch('https://api.example.com/nonexistent');
           
           // 2. Promise가 reject되면 await이 에러를 throw
           // 3. throw된 에러가 try-catch 블록에서 잡힘
           console.log('이 코드는 실행되지 않음');
       } catch (error) {
           // 4. reject된 Promise의 에러가 여기서 잡힘
           console.error('에러 발생:', error);
       }
   }
   ```

   3. **Promise 체인과 에러 전파**
   ```javascript
   // Promise 체인에서의 에러 처리
   function explainPromiseChain() {
       fetch('https://api.example.com/nonexistent')
           .then(response => response.json())
           .then(data => console.log(data))
           .catch(error => {
               // Promise 체인에서는 catch()로 에러를 잡을 수 있음
               console.error('Promise 체인에서 에러 발생:', error);
           });
   }

   // async/await에서의 에러 처리
   async function explainAsyncAwait() {
       try {
           const response = await fetch('https://api.example.com/nonexistent');
           const data = await response.json();
           console.log(data);
       } catch (error) {
           // async/await에서는 try-catch로 에러를 잡을 수 있음
           console.error('async/await에서 에러 발생:', error);
       }
   }
   ```

   ### 왜 await이 필요한가?

   1. **동기적 에러 처리**
   - await은 Promise가 완료될 때까지 함수 실행을 일시 중지합니다.
   - Promise가 reject되면 await이 자동으로 에러를 throw합니다.
   - throw된 에러는 try-catch 블록에서 잡힐 수 있습니다.

   2. **에러 전파 경로**
   ```javascript
   async function errorPropagation() {
       try {
           // 1. fetch()는 Promise를 반환
           const promise = fetch('https://api.example.com/nonexistent');
           
           // 2. await 없이 Promise 사용
           promise.then(response => {
               // 3. 이 콜백은 Promise가 resolve될 때 실행
               console.log('응답:', response);
           }).catch(error => {
               // 4. 이 콜백은 Promise가 reject될 때 실행
               console.error('Promise 에러:', error);
           });
           
           // 5. try-catch 블록은 이미 끝남
       } catch (error) {
           // 6. 이 블록은 실행되지 않음
           console.error('try-catch 에러:', error);
       }
   }

   async function correctErrorPropagation() {
       try {
           // 1. await으로 Promise 완료 대기
           const response = await fetch('https://api.example.com/nonexistent');
           
           // 2. Promise가 reject되면 여기서 에러가 throw됨
           console.log('응답:', response);
       } catch (error) {
           // 3. throw된 에러가 여기서 잡힘
           console.error('try-catch 에러:', error);
       }
   }
   ```

   3. **실제 사용 시나리오**
   ```javascript
   // 잘못된 사용
   async function wrongErrorHandling() {
       try {
           // 1. Promise 생성
           const promise = fetch('https://api.example.com/data');
           
           // 2. Promise 처리
           promise.then(response => {
               // 3. 이 콜백은 try-catch 블록 밖에서 실행됨
               if (!response.ok) {
                   throw new Error('API 에러');
               }
               return response.json();
           });
           
           // 4. try-catch 블록이 끝남
       } catch (error) {
           // 5. 이 블록은 실행되지 않음
           console.error('에러 발생:', error);
       }
   }

   // 올바른 사용
   async function correctErrorHandling() {
       try {
           // 1. await으로 Promise 완료 대기
           const response = await fetch('https://api.example.com/data');
           
           // 2. 응답 검사
           if (!response.ok) {
               throw new Error('API 에러');
           }
           
           // 3. 데이터 처리
           const data = await response.json();
           return data;
       } catch (error) {
           // 4. 모든 에러가 여기서 잡힘
           console.error('에러 발생:', error);
           throw error; // 필요한 경우 에러를 상위로 전파
       }
   }
   ```

   이러한 이유로, Promise의 reject 상태를 try-catch로 잡으려면 반드시 await을 사용해야 합니다. await은 Promise의 완료를 기다리고, reject 상태를 에러로 변환하여 try-catch 블록에서 처리할 수 있게 해줍니다.

3. **실행 순서 혼란**
   ```javascript
   // 문제가 있는 코드
   async function orderExample() {
       try {
           const response = fetch('https://api.example.com/data');
           const data = response.json(); // response가 아직 Promise 상태
           console.log('데이터:', data); // [object Promise] 출력
           
           // 데이터 처리 시도
           data.forEach(item => console.log(item)); // TypeError 발생
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }

   // 올바른 코드
   async function correctOrderExample() {
       try {
           const response = await fetch('https://api.example.com/data');
           const data = await response.json();
           console.log('데이터:', data); // 실제 데이터 출력
           
           // 데이터 처리
           data.forEach(item => console.log(item));
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }
   ```
   - 비동기 작업의 완료를 기다리지 않아 데이터가 준비되기 전에 처리하려고 시도합니다.
   - Promise 객체를 직접 사용하려고 시도하여 예상치 못한 동작이 발생합니다.
   - 데이터 처리 순서가 보장되지 않아 race condition이 발생할 수 있습니다.
   - 의존성이 있는 작업들이 잘못된 순서로 실행될 수 있습니다.

4. **메모리 누수 가능성**
   ```javascript
   // 문제가 있는 코드
   async function memoryLeakExample() {
       try {
           const promises = [];
           for (let i = 0; i < 1000; i++) {
               promises.push(fetch('https://api.example.com/data')); // await 없음
           }
           console.log('모든 요청 완료');
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }

   // 올바른 코드
   async function correctMemoryExample() {
       try {
           const promises = [];
           for (let i = 0; i < 1000; i++) {
               promises.push(fetch('https://api.example.com/data'));
           }
           await Promise.all(promises); // 모든 Promise 완료 대기
           console.log('모든 요청 완료');
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }
   ```
   - Promise가 완료되지 않은 상태로 남아있어 메모리 누수가 발생할 수 있습니다.
   - 대량의 비동기 작업을 처리할 때 리소스가 제대로 해제되지 않을 수 있습니다.
   - 가비지 컬렉션이 제대로 동작하지 않을 수 있습니다.

5. **디버깅의 어려움**
   ```javascript
   // 문제가 있는 코드
   async function debuggingExample() {
       try {
           const response = fetch('https://api.example.com/data');
           console.log('응답:', response); // [object Promise] 출력
           
           // 디버깅이 어려운 상황
           const data = response.json();
           processData(data);
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }

   // 올바른 코드
   async function correctDebuggingExample() {
       try {
           const response = await fetch('https://api.example.com/data');
           console.log('응답 상태:', response.status);
           
           const data = await response.json();
           console.log('데이터:', data);
           
           processData(data);
       } catch (error) {
           console.error('에러 발생:', error);
       }
   }
   ```
   - Promise 객체의 상태를 직접 확인하기 어렵습니다.
   - 에러가 발생한 시점과 위치를 정확히 파악하기 어렵습니다.
   - 비동기 작업의 진행 상황을 추적하기 어렵습니다.
   - 스택 트레이스가 불완전하여 디버깅이 어려워집니다.

## 4. Promise의 고급 기능

### Promise.all()
여러 Promise를 병렬로 실행하고 모든 Promise가 완료될 때까지 기다립니다.

```javascript
// 여러 API 호출을 병렬로 처리
async function fetchMultipleData() {
    try {
        const [users, posts, comments] = await Promise.all([
            fetch('https://api.example.com/users').then(res => res.json()),
            fetch('https://api.example.com/posts').then(res => res.json()),
            fetch('https://api.example.com/comments').then(res => res.json())
        ]);

        console.log('사용자:', users);
        console.log('게시물:', posts);
        console.log('댓글:', comments);
    } catch (error) {
        console.error('데이터 가져오기 실패:', error);
    }
}
```

### Promise.race()
여러 Promise 중 가장 먼저 완료되는 Promise의 결과를 반환합니다.

```javascript
// 타임아웃 구현 예제
function timeout(ms) {
    return new Promise((_, reject) => {
        setTimeout(() => reject(new Error('타임아웃')), ms);
    });
}

async function fetchWithTimeout(url, timeoutMs = 5000) {
    try {
        const response = await Promise.race([
            fetch(url),
            timeout(timeoutMs)
        ]);
        return await response.json();
    } catch (error) {
        console.error('요청 실패:', error);
        throw error;
    }
}
```

### Promise.allSettled()
모든 Promise가 완료될 때까지 기다리며, 각 Promise의 결과를 배열로 반환합니다.

```javascript
// 여러 API 호출의 결과를 모두 확인
async function fetchAllData() {
    const urls = [
        'https://api.example.com/data1',
        'https://api.example.com/data2',
        'https://api.example.com/data3'
    ];

    const results = await Promise.allSettled(
        urls.map(url => fetch(url).then(res => res.json()))
    );

    results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
            console.log(`데이터 ${index + 1} 성공:`, result.value);
        } else {
            console.error(`데이터 ${index + 1} 실패:`, result.reason);
        }
    });
}
```

### Promise.any()
여러 Promise 중 하나라도 성공하면 그 결과를 반환합니다.

```javascript
// 여러 서버 중 하나라도 응답하면 처리
async function fetchFromAnyServer() {
    const servers = [
        'https://server1.example.com',
        'https://server2.example.com',
        'https://server3.example.com'
    ];

    try {
        const response = await Promise.any(
            servers.map(server => fetch(`${server}/data`))
        );
        return await response.json();
    } catch (error) {
        console.error('모든 서버 요청 실패:', error);
        throw error;
    }
}
```

## 5. Promise 에러 처리 전략

### 에러 전파
Promise 체인에서 에러는 가장 가까운 catch 블록으로 전파됩니다.

```javascript
async function processData() {
    try {
        const data = await fetchData();
        const processed = await processData(data);
        const result = await saveData(processed);
        return result;
    } catch (error) {
        // 모든 단계의 에러를 여기서 처리
        console.error('처리 중 에러 발생:', error);
        throw error; // 상위로 에러 전파
    }
}
```

### 에러 복구
에러가 발생했을 때 대체 로직을 실행할 수 있습니다.

```javascript
async function fetchWithFallback() {
    try {
        const response = await fetch('https://api.example.com/data');
        return await response.json();
    } catch (error) {
        console.warn('기본 API 실패, 대체 API 시도:', error);
        // 대체 API 호출
        const fallbackResponse = await fetch('https://backup-api.example.com/data');
        return await fallbackResponse.json();
    }
}
```

### 재시도 로직
실패한 요청을 여러 번 재시도하는 로직을 구현할 수 있습니다.

```javascript
async function fetchWithRetry(url, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            console.log(`재시도 ${i + 1}/${maxRetries}`);
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
}
```

## 6. 실제 프로젝트에서의 Promise 활용

### API 클라이언트 구현
```javascript
class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API 요청 실패:', error);
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint);
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
}

// 사용 예시
const api = new ApiClient('https://api.example.com');

async function main() {
    try {
        // 여러 API 호출을 병렬로 처리
        const [users, posts] = await Promise.all([
            api.get('/users'),
            api.get('/posts')
        ]);

        // 새로운 게시물 작성
        const newPost = await api.post('/posts', {
            title: '새 게시물',
            content: '내용...'
        });

        console.log('사용자:', users);
        console.log('게시물:', posts);
        console.log('새 게시물:', newPost);
    } catch (error) {
        console.error('작업 실패:', error);
    }
}
```

이러한 Promise 핸들링 방법들을 적절히 활용하면 비동기 코드를 더 효율적이고 가독성 있게 작성할 수 있습니다. 실제 프로젝트에서는 이러한 패턴들을 조합하여 사용하면 됩니다. 