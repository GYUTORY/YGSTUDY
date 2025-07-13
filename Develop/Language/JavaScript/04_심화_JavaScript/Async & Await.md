# async/await

## 개요
async/await는 JavaScript에서 비동기 작업을 더 쉽게 다루기 위한 문법입니다. Promise를 기반으로 하지만, Promise의 복잡한 체이닝(.then(), .catch()) 없이도 비동기 코드를 동기 코드처럼 작성할 수 있게 해줍니다.

## 기본 개념

### async 함수
- 함수 앞에 `async` 키워드를 붙이면 해당 함수는 비동기 함수가 됩니다
- async 함수는 항상 Promise를 반환합니다
- 함수 내부에서 `await` 키워드를 사용할 수 있습니다

### await 키워드
- Promise가 완료될 때까지 기다리는 키워드입니다
- await는 오직 async 함수 내부에서만 사용할 수 있습니다
- await를 만나면 해당 Promise가 완료될 때까지 함수 실행을 일시 중지합니다

## 기본 사용법

```javascript
// 기본적인 async 함수 선언
async function myAsyncFunction() {
    // 비동기 작업 수행
    const result = await someAsyncOperation();
    return result;
}

// 화살표 함수로도 사용 가능
const myAsyncArrowFunction = async () => {
    const result = await someAsyncOperation();
    return result;
};
```

## 실제 예시

### 1. 간단한 비동기 함수

```javascript
// Promise를 반환하는 함수 (기존 방식)
function delay(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

// async/await를 사용한 함수
async function waitAndLog() {
    console.log('시작');
    await delay(2000); // 2초 대기
    console.log('2초 후 실행');
    return '완료';
}

// 사용
waitAndLog().then(result => {
    console.log(result); // '완료'
});
```

### 2. API 호출 예시

```javascript
// 비동기적으로 데이터를 가져오는 함수
async function fetchUserData(userId) {
    try {
        // API 호출
        const response = await fetch(`https://api.example.com/users/${userId}`);
        
        // 응답이 성공적이지 않으면 에러 발생
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // JSON 데이터 파싱
        const userData = await response.json();
        return userData;
        
    } catch (error) {
        console.error('사용자 데이터 가져오기 실패:', error);
        throw error;
    }
}

// 사용 예시
async function displayUserInfo(userId) {
    try {
        const user = await fetchUserData(userId);
        console.log('사용자 정보:', user);
        return user;
    } catch (error) {
        console.error('사용자 정보 표시 실패:', error);
    }
}
```

### 3. 여러 비동기 작업 처리

```javascript
// 순차적으로 실행 (하나씩 기다림)
async function sequentialExecution() {
    const result1 = await fetchData1();
    const result2 = await fetchData2();
    const result3 = await fetchData3();
    
    return [result1, result2, result3];
}

// 병렬로 실행 (모두 동시에 시작)
async function parallelExecution() {
    const promise1 = fetchData1();
    const promise2 = fetchData2();
    const promise3 = fetchData3();
    
    const [result1, result2, result3] = await Promise.all([promise1, promise2, promise3]);
    return [result1, result2, result3];
}
```

## 에러 처리

### try-catch 사용

```javascript
async function handleErrors() {
    try {
        const data = await fetchData();
        return data;
    } catch (error) {
        console.error('에러 발생:', error.message);
        // 에러 처리 로직
        return null;
    }
}
```

### Promise.catch() 사용

```javascript
async function handleErrorsWithCatch() {
    const data = await fetchData().catch(error => {
        console.error('에러 발생:', error.message);
        return null;
    });
    return data;
}
```

## Promise와의 관계

### async/await는 Promise의 문법적 설탕

```javascript
// Promise 방식
function oldWay() {
    return fetchData()
        .then(data => {
            return processData(data);
        })
        .then(result => {
            console.log(result);
        })
        .catch(error => {
            console.error(error);
        });
}

// async/await 방식
async function newWay() {
    try {
        const data = await fetchData();
        const result = await processData(data);
        console.log(result);
    } catch (error) {
        console.error(error);
    }
}
```

## 주의사항

### 1. await는 async 함수 내에서만 사용 가능

```javascript
// ❌ 잘못된 사용
function wrongUsage() {
    const data = await fetchData(); // 에러 발생
}

// ✅ 올바른 사용
async function correctUsage() {
    const data = await fetchData(); // 정상 동작
}
```

### 2. async 함수는 항상 Promise 반환

```javascript
async function alwaysReturnsPromise() {
    return "hello"; // Promise<string> 반환
}

// 사용할 때
alwaysReturnsPromise().then(result => {
    console.log(result); // "hello"
});
```

### 3. await는 Promise가 아닌 값도 처리 가능

```javascript
async function handleNonPromise() {
    const value = await 42; // Promise가 아니어도 정상 동작
    console.log(value); // 42
}
```

## 실제 활용 예시

### 파일 읽기 (Node.js 환경)

```javascript
const fs = require('fs').promises;

async function readAndProcessFile(filename) {
    try {
        const content = await fs.readFile(filename, 'utf8');
        const lines = content.split('\n');
        return lines.length;
    } catch (error) {
        console.error('파일 읽기 실패:', error);
        return 0;
    }
}
```

### 데이터베이스 쿼리

```javascript
async function getUserPosts(userId) {
    try {
        const user = await db.users.findById(userId);
        const posts = await db.posts.findByUserId(userId);
        
        return {
            user: user,
            posts: posts
        };
    } catch (error) {
        console.error('데이터베이스 조회 실패:', error);
        throw error;
    }
}
```

## 요약

- **async**: 함수를 비동기 함수로 만드는 키워드
- **await**: Promise가 완료될 때까지 기다리는 키워드
- **장점**: 비동기 코드를 동기 코드처럼 읽기 쉽게 작성 가능
- **주의**: await는 async 함수 내에서만 사용 가능
- **반환값**: async 함수는 항상 Promise를 반환

async/await를 사용하면 복잡한 비동기 로직도 깔끔하고 이해하기 쉬운 코드로 작성할 수 있습니다.


```javascript
// 비동기적으로 데이터를 가져오는 함수
async function fetchData(url) {
    try {
        const response = await fetch(url); // 비동기적으로 데이터를 가져옴
        const data = await response.json(); // 비동기적으로 데이터를 JSON 형식으로 변환
        return data; // 데이터 반환
    } catch (error) {
        console.log('Error:', error);
        throw error;
    }
}

// 비동기 함수를 사용하여 데이터 처리
async function process() {
    try {
        const url = 'https://api.example.com/data';
        const data = await fetchData(url); // 비동기적으로 데이터를 가져옴

        // 데이터 처리
        console.log('Data:', data);
        // 추가 작업 수행 가능
    } catch (error) {
        console.log('Error:', error);
    }
}

// 비동기 함수 실행
process();
```


> 위의 예시에서 fetchData 함수는 비동기 함수로, fetch를 사용하여 데이터를 가져오고 response.json()을 사용하여 응답 데이터를 JSON 형식으로 변환합니다.
- 이 함수는 Promise를 반환하므로 await를 사용하여 비동기적으로 데이터를 기다릴 수 있습니다.

> process 함수에서는 fetchData 함수를 호출하여 데이터를 가져오고, 가져온 데이터를 처리합니다. 
- 이때 await 키워드를 사용하여 fetchData 함수의 비동기 처리를 기다립니다.
