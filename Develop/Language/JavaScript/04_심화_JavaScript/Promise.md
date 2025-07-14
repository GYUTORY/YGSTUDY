# JavaScript Promise

## 📋 목차
- [Promise란 무엇인가?](#promise란-무엇인가)
- [Promise의 3가지 상태](#promise의-3가지-상태)
- [Promise 기본 사용법](#promise-기본-사용법)
- [async/await 이해하기](#asyncawait-이해하기)
- [Promise 고급 기능들](#promise-고급-기능들)
- [실제 사용 예시](#실제-사용-예시)

---

## Promise란 무엇인가?

### 🔍 Promise의 정의
Promise는 **"나중에 완료될 작업의 결과를 담는 상자"**라고 생각하면 됩니다.

예를 들어, 친구에게 "점심 메뉴 추천해줘"라고 부탁했을 때:
- 친구가 "좋아, 잠깐만 생각해볼게"라고 말함 → **Promise 생성**
- 친구가 생각하는 동안 → **Promise 진행 중 (pending)**
- 친구가 "치킨 어때?"라고 답함 → **Promise 완료 (fulfilled)**
- 친구가 "몰라, 너가 알아서 해"라고 답함 → **Promise 실패 (rejected)**

### 💡 왜 Promise가 필요한가?

**콜백 지옥(Callback Hell)** 문제를 해결하기 위해 만들어졌습니다.

```javascript
// 콜백 지옥 예시 (Promise 이전)
fetchUserData(function(user) {
    fetchUserPosts(user.id, function(posts) {
        fetchPostComments(posts[0].id, function(comments) {
            fetchCommentAuthor(comments[0].id, function(author) {
                console.log('작성자:', author.name);
            });
        });
    });
});

// Promise 사용 (깔끔한 코드)
async function getUserInfo() {
    const user = await fetchUserData();
    const posts = await fetchUserPosts(user.id);
    const comments = await fetchPostComments(posts[0].id);
    const author = await fetchCommentAuthor(comments[0].id);
    console.log('작성자:', author.name);
}
```

---

## Promise의 3가지 상태

Promise는 항상 다음 3가지 상태 중 하나를 가집니다:

### 1️⃣ **Pending (대기 중)**
- Promise가 생성된 직후의 상태
- 아직 작업이 완료되지 않은 상태

### 2️⃣ **Fulfilled (이행됨)**
- 작업이 성공적으로 완료된 상태
- 결과값을 가지고 있음

### 3️⃣ **Rejected (거부됨)**
- 작업이 실패한 상태
- 에러 정보를 가지고 있음

```javascript
// Promise 상태 확인 예시
const promise = new Promise((resolve, reject) => {
    console.log('Promise 생성 - 상태: Pending');
    
    setTimeout(() => {
        const random = Math.random();
        if (random > 0.5) {
            resolve('성공!'); // 상태: Fulfilled
            console.log('Promise 완료 - 상태: Fulfilled');
        } else {
            reject('실패!'); // 상태: Rejected
            console.log('Promise 실패 - 상태: Rejected');
        }
    }, 1000);
});

console.log('Promise 객체:', promise); // Promise { <pending> }
```

---

## Promise 기본 사용법

### 🔧 Promise 생성하기

```javascript
// 기본 Promise 생성
const myPromise = new Promise((resolve, reject) => {
    // 여기에 비동기 작업을 작성
    setTimeout(() => {
        const success = Math.random() > 0.5;
        
        if (success) {
            resolve('작업 성공!'); // 성공 시 호출
        } else {
            reject(new Error('작업 실패!')); // 실패 시 호출
        }
    }, 2000);
});
```

### 📝 Promise 사용하기

```javascript
// 방법 1: .then()과 .catch() 사용
myPromise
    .then(result => {
        console.log('성공:', result);
        return result.toUpperCase(); // 다음 .then()으로 전달
    })
    .then(upperResult => {
        console.log('대문자 변환:', upperResult);
    })
    .catch(error => {
        console.error('에러 발생:', error.message);
    })
    .finally(() => {
        console.log('작업 완료 (성공/실패 상관없이 실행)');
    });

// 방법 2: async/await 사용 (더 깔끔함)
async function handlePromise() {
    try {
        const result = await myPromise;
        console.log('성공:', result);
        
        const upperResult = result.toUpperCase();
        console.log('대문자 변환:', upperResult);
    } catch (error) {
        console.error('에러 발생:', error.message);
    } finally {
        console.log('작업 완료');
    }
}
```

### 🎯 실제 사용 예시

```javascript
// 파일 읽기 Promise
function readFileAsync(filename) {
    return new Promise((resolve, reject) => {
        // 실제 파일 읽기 작업 시뮬레이션
        setTimeout(() => {
            if (filename === 'data.txt') {
                resolve('파일 내용: Hello World!');
            } else {
                reject(new Error('파일을 찾을 수 없습니다.'));
            }
        }, 1000);
    });
}

// 사용하기
async function processFile() {
    try {
        const content = await readFileAsync('data.txt');
        console.log('파일 내용:', content);
    } catch (error) {
        console.error('파일 읽기 실패:', error.message);
    }
}
```

---

## async/await 이해하기

### 🔍 async/await란?

async/await는 Promise를 더 쉽게 사용할 수 있게 해주는 **문법적 설탕(Syntactic Sugar)**입니다.

- **async**: 함수가 Promise를 반환한다는 표시
- **await**: Promise가 완료될 때까지 기다린다는 표시

### 📊 Promise vs async/await 비교

```javascript
// Promise 방식
function fetchUserData() {
    return fetch('https://api.example.com/user')
        .then(response => {
            if (!response.ok) {
                throw new Error('네트워크 에러');
            }
            return response.json();
        })
        .then(data => {
            console.log('사용자 데이터:', data);
            return data;
        })
        .catch(error => {
            console.error('에러 발생:', error);
            throw error;
        });
}

// async/await 방식 (더 읽기 쉬움)
async function fetchUserData() {
    try {
        const response = await fetch('https://api.example.com/user');
        
        if (!response.ok) {
            throw new Error('네트워크 에러');
        }
        
        const data = await response.json();
        console.log('사용자 데이터:', data);
        return data;
    } catch (error) {
        console.error('에러 발생:', error);
        throw error;
    }
}
```

### ⚠️ async/await 사용 시 주의사항

#### 1. await 없이 Promise 사용하면 안 됨

```javascript
// ❌ 잘못된 사용
async function wrongExample() {
    try {
        fetch('https://api.example.com/data'); // await 없음!
        console.log('이 코드는 fetch 완료 전에 실행됨');
    } catch (error) {
        console.error('에러 발생:', error); // 이 catch는 실행되지 않음
    }
}

// ✅ 올바른 사용
async function correctExample() {
    try {
        const response = await fetch('https://api.example.com/data');
        console.log('이 코드는 fetch 완료 후에 실행됨');
    } catch (error) {
        console.error('에러 발생:', error); // 이제 에러를 잡을 수 있음
    }
}
```

#### 2. 왜 await이 필요한가?

```javascript
// Promise의 동작 방식 이해
async function explainPromise() {
    console.log('1. 함수 시작');
    
    // await 없이 Promise 사용
    const promise1 = fetch('https://api.example.com/data');
    console.log('2. Promise 생성됨:', promise1); // Promise { <pending> }
    
    // await으로 Promise 완료 대기
    const response = await fetch('https://api.example.com/data');
    console.log('3. Promise 완료됨:', response); // 실제 응답 객체
    
    console.log('4. 함수 종료');
}

// 실행 순서:
// 1. 함수 시작
// 2. Promise 생성됨: Promise { <pending> }
// 3. Promise 완료됨: Response { ... }
// 4. 함수 종료
```

---

## Promise 고급 기능들

### 🔗 Promise.all() - 모든 Promise 완료 대기

여러 Promise를 **병렬로 실행**하고 모든 Promise가 완료될 때까지 기다립니다.

```javascript
async function fetchAllData() {
    try {
        // 3개의 API를 동시에 호출
        const [users, posts, comments] = await Promise.all([
            fetch('https://api.example.com/users').then(res => res.json()),
            fetch('https://api.example.com/posts').then(res => res.json()),
            fetch('https://api.example.com/comments').then(res => res.json())
        ]);

        console.log('사용자:', users);
        console.log('게시물:', posts);
        console.log('댓글:', comments);
        
        return { users, posts, comments };
    } catch (error) {
        console.error('하나라도 실패하면 전체 실패:', error);
        throw error;
    }
}
```

### 🏁 Promise.race() - 가장 빠른 Promise 결과

여러 Promise 중 **가장 먼저 완료되는 Promise**의 결과만 가져옵니다.

```javascript
// 타임아웃 구현 예시
function timeout(ms) {
    return new Promise((_, reject) => {
        setTimeout(() => reject(new Error('타임아웃!')), ms);
    });
}

async function fetchWithTimeout(url, timeoutMs = 5000) {
    try {
        const response = await Promise.race([
            fetch(url),           // 실제 API 호출
            timeout(timeoutMs)    // 타임아웃 Promise
        ]);
        
        return await response.json();
    } catch (error) {
        console.error('요청 실패:', error.message);
        throw error;
    }
}

// 사용 예시
fetchWithTimeout('https://api.example.com/data', 3000)
    .then(data => console.log('데이터:', data))
    .catch(error => console.error('에러:', error));
```

### 📊 Promise.allSettled() - 모든 Promise 결과 확인

모든 Promise가 완료될 때까지 기다리고, **성공/실패 여부와 관계없이 모든 결과**를 확인합니다.

```javascript
async function fetchAllDataSafely() {
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
            console.log(`✅ 데이터 ${index + 1} 성공:`, result.value);
        } else {
            console.log(`❌ 데이터 ${index + 1} 실패:`, result.reason);
        }
    });
}
```

### 🎯 Promise.any() - 하나라도 성공하면 OK

여러 Promise 중 **하나라도 성공하면** 그 결과를 반환합니다.

```javascript
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

---

## 실제 사용 예시

### 🏗️ API 클라이언트 만들기

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
                throw new Error(`HTTP 에러! 상태: ${response.status}`);
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

### 🔄 재시도 로직 구현

```javascript
async function fetchWithRetry(url, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.log(`시도 ${i + 1}/${maxRetries} 실패:`, error.message);
            
            if (i === maxRetries - 1) {
                throw new Error(`최대 재시도 횟수 초과: ${error.message}`);
            }
            
            // 지수 백오프 (1초, 2초, 4초...)
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        }
    }
}

// 사용 예시
fetchWithRetry('https://api.example.com/data')
    .then(data => console.log('성공:', data))
    .catch(error => console.error('최종 실패:', error));
```

### 🎨 에러 처리 패턴

```javascript
// 에러 복구 패턴
async function fetchWithFallback() {
    try {
        const response = await fetch('https://api.example.com/data');
        return await response.json();
    } catch (error) {
        console.warn('기본 API 실패, 대체 API 시도:', error.message);
        
        // 대체 API 호출
        const fallbackResponse = await fetch('https://backup-api.example.com/data');
        return await fallbackResponse.json();
    }
}

// 에러 전파 패턴
async function processData() {
    try {
        const data = await fetchData();
        const processed = await processData(data);
        const result = await saveData(processed);
        return result;
    } catch (error) {
        console.error('처리 중 에러 발생:', error);
        throw error; // 상위로 에러 전파
    }
}
```

---

## 📝 정리

### ✅ Promise의 핵심 개념
1. **Promise는 비동기 작업의 결과를 담는 상자**
2. **3가지 상태**: Pending → Fulfilled/Rejected
3. **async/await**로 더 쉽게 사용 가능
4. **await 없이 Promise 사용하면 에러 처리 불가**

### 🛠️ 자주 사용하는 패턴
- `Promise.all()`: 모든 Promise 완료 대기
- `Promise.race()`: 가장 빠른 Promise 결과
- `Promise.allSettled()`: 모든 결과 확인
- `Promise.any()`: 하나라도 성공하면 OK

### 💡 실무 팁
- 항상 `await`과 함께 사용하기
- `try-catch`로 에러 처리하기
- `Promise.all()`로 병렬 처리하기
- 재시도 로직 구현하기 