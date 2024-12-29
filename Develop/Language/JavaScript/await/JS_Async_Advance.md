
# JavaScript의 비동기 처리 심화

## 1. async/await 패턴 최적화
`async/await`는 JavaScript의 비동기 코드를 동기적으로 작성할 수 있도록 도와주는 문법입니다. 이를 효과적으로 사용하면 가독성과 유지보수성이 크게 향상됩니다.

### 최적화 예제
```javascript
async function fetchData(urls) {
    const results = [];
    for (const url of urls) {
        const response = await fetch(url);
        results.push(await response.json());
    }
    return results;
}

// 사용법
const urls = ['https://api.example.com/data1', 'https://api.example.com/data2'];
fetchData(urls).then(data => console.log(data));
```
위 코드는 URL 배열을 순차적으로 처리합니다. 만약 병렬 처리가 가능하다면 `Promise.all`과 같은 방식을 고려할 수 있습니다.

### 병렬 처리로 최적화
```javascript
async function fetchDataInParallel(urls) {
    const promises = urls.map(url => fetch(url).then(res => res.json()));
    return Promise.all(promises);
}

// 사용법
fetchDataInParallel(urls).then(data => console.log(data));
```

---

## 2. Promise.allSettled, Promise.race 등을 활용한 병렬 작업 처리
### Promise.allSettled
`Promise.allSettled`는 모든 Promise가 완료될 때까지 기다리고, 각 Promise의 성공 또는 실패 상태를 반환합니다.

#### 예제
```javascript
const promises = [
    Promise.resolve('성공1'),
    Promise.reject('실패1'),
    Promise.resolve('성공2')
];

Promise.allSettled(promises).then(results => {
    results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
            console.log(`Promise ${index} 성공:`, result.value);
        } else {
            console.log(`Promise ${index} 실패:`, result.reason);
        }
    });
});
```

### Promise.race
`Promise.race`는 가장 먼저 완료되는 Promise의 결과를 반환합니다.

#### 예제
```javascript
const promises = [
    new Promise(resolve => setTimeout(() => resolve('1초 후 완료'), 1000)),
    new Promise(resolve => setTimeout(() => resolve('2초 후 완료'), 2000))
];

Promise.race(promises).then(result => {
    console.log('가장 먼저 완료된 Promise:', result);
});
```

---

## 3. Web Workers와 멀티스레딩을 통한 성능 최적화
JavaScript는 기본적으로 싱글 스레드로 동작하지만, Web Workers를 사용하면 멀티스레딩 환경에서 작업을 분리할 수 있습니다. Web Workers는 CPU 집약적인 작업을 메인 스레드에서 분리하여 성능을 향상시킬 수 있습니다.

### Web Workers의 기본 구조
#### worker.js
```javascript
self.onmessage = function(e) {
    const result = e.data * 2; // 받은 데이터를 2배로 처리
    self.postMessage(result); // 결과 전송
};
```

#### main.js
```javascript
const worker = new Worker('worker.js');

worker.onmessage = function(e) {
    console.log('Worker로부터 받은 메시지:', e.data);
};

worker.postMessage(5); // Worker로 5 전달
```

### Web Workers 활용 예제
이미지 처리, 대규모 계산 등 CPU 집약적인 작업에 Web Workers를 활용하면 성능을 크게 개선할 수 있습니다.

---

### 요약
- `async/await`를 사용하여 비동기 코드를 동기적으로 작성하되, 병렬 처리가 가능한 경우 `Promise.all`로 최적화.
- `Promise.allSettled`, `Promise.race` 등을 활용하여 다양한 병렬 처리 전략 구현.
- Web Workers를 사용하여 메인 스레드와 작업을 분리해 성능을 향상.

JavaScript 비동기 처리를 이해하고 최적화하여 더 나은 성능과 효율성을 달성하세요!
