# JavaScript 비동기 처리 심화 가이드

## 📋 목차
- [비동기 처리란?](#비동기-처리란)
- [async/await 패턴 최적화](#asyncawait-패턴-최적화)
- [Promise 병렬 처리 방법들](#promise-병렬-처리-방법들)
- [Web Workers와 멀티스레딩](#web-workers와-멀티스레딩)

---

## 비동기 처리란?

**비동기 처리**는 작업이 완료될 때까지 기다리지 않고 다른 작업을 수행할 수 있게 하는 방식입니다. 

### 동기 vs 비동기 비교

```javascript
// 동기 처리 (순차적)
console.log('1단계 시작');
const result1 = heavyTask1(); // 3초 대기
console.log('2단계 시작');
const result2 = heavyTask2(); // 2초 대기
console.log('완료'); // 총 5초 후 실행

// 비동기 처리 (병렬적)
console.log('1단계 시작');
heavyTask1().then(result => console.log('1단계 완료'));
console.log('2단계 시작');
heavyTask2().then(result => console.log('2단계 완료'));
console.log('모든 작업 시작됨'); // 즉시 실행
```

---

## async/await 패턴 최적화

### async/await란?
- **async**: 함수가 비동기적으로 동작함을 명시
- **await**: Promise가 완료될 때까지 기다림
- 동기 코드처럼 보이지만 실제로는 비동기적으로 동작

### 기본 사용법

```javascript
// 기존 Promise 방식
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .then(data => {
            console.log('사용자 데이터:', data);
            return data;
        })
        .catch(error => {
            console.error('에러 발생:', error);
        });
}

// async/await 방식
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        console.log('사용자 데이터:', data);
        return data;
    } catch (error) {
        console.error('에러 발생:', error);
    }
}
```

### 순차 처리 vs 병렬 처리

#### 순차 처리 (느림)
```javascript
async function fetchMultipleUsers(userIds) {
    const users = [];
    
    // 각 요청을 순차적으로 처리 (느림)
    for (const id of userIds) {
        const user = await fetchUserData(id);
        users.push(user);
    }
    
    return users;
}

// 사용 예시
const userIds = [1, 2, 3, 4, 5];
fetchMultipleUsers(userIds).then(users => {
    console.log('모든 사용자 데이터:', users);
});
```

#### 병렬 처리 (빠름)
```javascript
async function fetchMultipleUsersParallel(userIds) {
    // 모든 요청을 동시에 시작
    const promises = userIds.map(id => fetchUserData(id));
    
    // 모든 요청이 완료될 때까지 기다림
    const users = await Promise.all(promises);
    
    return users;
}

// 사용 예시
fetchMultipleUsersParallel(userIds).then(users => {
    console.log('모든 사용자 데이터:', users);
});
```

---

## Promise 병렬 처리 방법들

### Promise.all()
**모든 Promise가 성공해야 하는 경우**에 사용합니다.

```javascript
const promises = [
    fetch('/api/users'),
    fetch('/api/posts'),
    fetch('/api/comments')
];

Promise.all(promises)
    .then(([users, posts, comments]) => {
        console.log('모든 데이터 로드 완료');
        console.log('사용자:', users);
        console.log('게시글:', posts);
        console.log('댓글:', comments);
    })
    .catch(error => {
        // 하나라도 실패하면 전체 실패
        console.error('하나라도 실패:', error);
    });
```

### Promise.allSettled()
**일부가 실패해도 나머지 결과를 얻고 싶은 경우**에 사용합니다.

```javascript
const promises = [
    Promise.resolve('성공1'),
    Promise.reject('실패1'),
    Promise.resolve('성공2'),
    Promise.reject('실패2')
];

Promise.allSettled(promises)
    .then(results => {
        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                console.log(`Promise ${index} 성공:`, result.value);
            } else {
                console.log(`Promise ${index} 실패:`, result.reason);
            }
        });
    });
```

### Promise.race()
**가장 먼저 완료되는 Promise의 결과만 필요한 경우**에 사용합니다.

```javascript
// 여러 API 중 가장 빠른 응답을 받고 싶을 때
const apiPromises = [
    fetch('https://api1.example.com/data'),
    fetch('https://api2.example.com/data'),
    fetch('https://api3.example.com/data')
];

Promise.race(apiPromises)
    .then(response => response.json())
    .then(data => {
        console.log('가장 빠른 API 응답:', data);
    });
```

### Promise.any()
**하나라도 성공하면 되는 경우**에 사용합니다.

```javascript
const promises = [
    Promise.reject('실패1'),
    Promise.resolve('성공1'),
    Promise.reject('실패2')
];

Promise.any(promises)
    .then(result => {
        console.log('하나라도 성공:', result); // "성공1" 출력
    })
    .catch(error => {
        // 모든 Promise가 실패한 경우에만 실행
        console.error('모든 Promise 실패:', error);
    });
```

---

## Web Workers와 멀티스레딩

### Web Workers란?
JavaScript는 기본적으로 **싱글 스레드**로 동작합니다. 즉, 한 번에 하나의 작업만 처리할 수 있습니다. Web Workers를 사용하면 **별도의 스레드에서 작업을 수행**할 수 있어 메인 스레드가 멈추지 않습니다.

### 언제 사용하나요?
- 대용량 데이터 처리
- 복잡한 계산 작업
- 이미지/비디오 처리
- 실시간 데이터 분석

### 기본 구조

#### worker.js (별도 파일)
```javascript
// Worker 스레드에서 실행되는 코드
self.onmessage = function(e) {
    const data = e.data;
    
    // 복잡한 계산 작업
    let result = 0;
    for (let i = 0; i < data.iterations; i++) {
        result += Math.sqrt(i) * Math.PI;
    }
    
    // 계산 완료 후 메인 스레드로 결과 전송
    self.postMessage({
        result: result,
        message: '계산 완료!'
    });
};
```

#### main.js (메인 스레드)
```javascript
// Worker 생성
const worker = new Worker('worker.js');

// Worker로부터 메시지 받기
worker.onmessage = function(e) {
    const data = e.data;
    console.log('계산 결과:', data.result);
    console.log('메시지:', data.message);
};

// Worker로 데이터 전송
worker.postMessage({
    iterations: 1000000
});

// 메인 스레드는 계속 다른 작업 수행 가능
console.log('Worker에게 작업 요청 완료');
console.log('메인 스레드는 다른 작업 계속 수행 중...');
```

### 실제 활용 예제

#### 이미지 처리 Worker
```javascript
// imageWorker.js
self.onmessage = function(e) {
    const imageData = e.data;
    const canvas = new OffscreenCanvas(imageData.width, imageData.height);
    const ctx = canvas.getContext('2d');
    
    // 이미지 데이터를 캔버스에 그리기
    ctx.putImageData(imageData, 0, 0);
    
    // 이미지 필터 적용 (예: 흑백 변환)
    const filteredData = applyGrayscaleFilter(imageData);
    
    self.postMessage(filteredData);
};

function applyGrayscaleFilter(imageData) {
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
        const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
        data[i] = gray;     // Red
        data[i + 1] = gray; // Green
        data[i + 2] = gray; // Blue
    }
    
    return imageData;
}
```

#### 메인 스레드에서 사용
```javascript
const imageWorker = new Worker('imageWorker.js');

// 이미지 파일 선택 시
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            // 이미지 데이터를 Worker로 전송
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            imageWorker.postMessage(imageData);
        };
        img.src = e.target.result;
    };
    
    reader.readAsDataURL(file);
});

// Worker로부터 처리된 이미지 받기
imageWorker.onmessage = function(e) {
    const processedImageData = e.data;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = processedImageData.width;
    canvas.height = processedImageData.height;
    ctx.putImageData(processedImageData, 0, 0);
    
    // 처리된 이미지를 화면에 표시
    document.body.appendChild(canvas);
};
```

### 주의사항
- Worker는 DOM에 직접 접근할 수 없습니다
- Worker와 메인 스레드 간 통신은 `postMessage()`를 통해서만 가능합니다
- 복사 가능한 데이터만 전송할 수 있습니다 (함수, DOM 객체 등은 전송 불가)

---

## 마무리

JavaScript의 비동기 처리는 현대 웹 개발에서 필수적인 개념입니다. `async/await`를 활용한 깔끔한 코드 작성, 다양한 Promise 메서드를 통한 효율적인 병렬 처리, 그리고 Web Workers를 통한 성능 최적화까지 익혀두면 더 나은 사용자 경험을 제공할 수 있습니다.

실제 프로젝트에서는 이러한 기법들을 상황에 맞게 조합하여 사용하는 것이 중요합니다.
