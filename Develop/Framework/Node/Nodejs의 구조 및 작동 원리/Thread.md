# Node.js - Threads (멀티스레딩) 개념 및 활용 🚀

## 1. Node.js에서 Threads란? 🤔

Node.js는 **기본적으로 싱글 스레드(Single Thread) 기반**의 실행 환경입니다.  
하지만, **Worker Threads**를 활용하면 멀티 스레드 기반의 작업 처리가 가능합니다.

> **✨ Node.js의 스레드 모델**
> - 기본적으로 **Event Loop**를 활용하여 싱글 스레드에서 논-블로킹 방식으로 동작
> - **CPU 집중적인 작업(예: 암호화, 이미지 처리)**을 할 경우 Worker Threads를 활용하여 멀티스레드 처리 가능
> - **I/O 작업(파일 읽기, 네트워크 요청)**은 Event Loop가 효율적으로 처리

---

## 2. Worker Threads란? 🔄

**Worker Threads**는 **Node.js에서 멀티스레딩을 지원하는 기능**으로,  
CPU 집약적인 작업을 별도의 스레드에서 실행할 수 있도록 합니다.

| 비교 항목 | 기본 Event Loop | Worker Threads |
|-----------|---------------|---------------|
| **기본 개념** | 싱글 스레드 기반 비동기 실행 | 멀티 스레드 기반 작업 분산 |
| **사용 목적** | I/O 작업, 네트워크 요청 처리 | CPU 집중적인 연산 처리 |
| **비동기 방식** | 이벤트 기반 (Event-Driven) | 백그라운드 워커 스레드 사용 |
| **예제** | `setTimeout`, `setImmediate`, `Promise` | `worker_threads` 모듈 사용 |

---

## 3. Worker Threads 기본 사용법 🔥

### 3.1 메인 스레드에서 Worker 실행

#### ✅ `main.js`
```javascript
const { Worker } = require('worker_threads');

const worker = new Worker('./worker.js'); // 별도의 스레드 실행

worker.on('message', (msg) => console.log("워커에서 받은 메시지:", msg));
worker.postMessage("작업 시작");
```

#### ✅ `worker.js` (Worker 스레드)
```javascript
const { parentPort } = require('worker_threads');

parentPort.on('message', (msg) => {
    console.log("메인 스레드로부터 메시지:", msg);
    parentPort.postMessage("작업 완료!");
});
```

### 📌 실행 결과:
```
메인 스레드로부터 메시지: 작업 시작
워커에서 받은 메시지: 작업 완료!
```

> **📌 `Worker`를 사용하면 메인 스레드와 독립적으로 작업을 실행 가능!**

---

## 4. Worker Threads를 활용한 CPU 집중 작업

### 4.1 싱글 스레드에서 연산 실행 (비효율적)

#### ✅ `single-thread.js`
```javascript
const heavyComputation = () => {
    let sum = 0;
    for (let i = 0; i < 1e9; i++) {
        sum += i;
    }
    return sum;
};

console.log("계산 시작");
console.log("결과:", heavyComputation());
console.log("계산 완료");
```

### 📌 실행 결과 (느림)
```
계산 시작
(연산 지연)
결과: 499999999500000000
계산 완료
```
> **🛑 연산이 끝날 때까지 Event Loop가 멈춰버림 (Block 현상 발생)**

---

### 4.2 Worker Threads로 병렬 연산 (효율적)

#### ✅ `main.js` (메인 스레드)
```javascript
const { Worker } = require('worker_threads');

console.log("계산 시작");

const worker = new Worker("./worker.js");

worker.on("message", (result) => {
    console.log("결과:", result);
    console.log("계산 완료");
});
```

#### ✅ `worker.js` (Worker 스레드)
```javascript
const { parentPort } = require('worker_threads');

const heavyComputation = () => {
    let sum = 0;
    for (let i = 0; i < 1e9; i++) {
        sum += i;
    }
    return sum;
};

parentPort.postMessage(heavyComputation());
```

### 📌 실행 결과 (빠름)
```
계산 시작
(백그라운드에서 연산 수행)
결과: 499999999500000000
계산 완료
```
> **✅ Worker Threads를 사용하면 Event Loop가 차단되지 않고 병렬 연산 수행 가능!**

---

## 5. 부모와 Worker 간 데이터 교환

✔ `postMessage(data)` → 부모 스레드에서 Worker에게 데이터 전송  
✔ `parentPort.on('message', callback)` → Worker 스레드에서 메시지 수신  
✔ `parentPort.postMessage(data)` → Worker 스레드에서 부모에게 응답

#### ✅ 부모 → Worker 데이터 전송
```javascript
const { Worker } = require('worker_threads');

const worker = new Worker("./worker.js");

worker.postMessage({ task: "연산", number: 5 });

worker.on("message", (result) => console.log("결과:", result));
```

#### ✅ Worker에서 부모에게 응답
```javascript
const { parentPort } = require('worker_threads');

parentPort.on("message", (msg) => {
    console.log("메시지 수신:", msg);
    parentPort.postMessage("작업 완료!");
});
```

> **📌 `postMessage()`를 이용하면 부모 스레드와 Worker 간 데이터를 주고받을 수 있음!**

---

## 6. 언제 Worker Threads를 사용해야 할까? 🤔

| 사용해야 하는 경우 | 사용하지 않아도 되는 경우 |
|-----------------|-----------------|
| **CPU 집중적인 작업** (예: 암호화, 이미지 처리) | **I/O 작업** (예: 파일 읽기, 네트워크 요청) |
| **병렬 연산이 필요한 경우** | **Event Loop를 활용할 수 있는 경우** |
| **메인 스레드가 차단되는 문제 발생 시** | **간단한 비동기 코드 실행 시** |

✅ **I/O 작업은 Event Loop가 더 적합하고, CPU 연산은 Worker Threads가 효과적!**

---

## 📌 결론

- **Node.js는 기본적으로 싱글 스레드 기반**이지만, `worker_threads` 모듈을 사용하여 **멀티 스레드 지원 가능**
- **Worker Threads는 CPU 집중적인 연산을 백그라운드에서 실행하여 메인 스레드의 Event Loop를 방해하지 않음**
- **I/O 작업에는 Event Loop가 더 적합하며, CPU 연산 작업에는 Worker Threads가 효과적**
- **`postMessage()`를 이용하여 부모와 Worker 간 데이터를 주고받을 수 있음**

> **👉🏻 Worker Threads를 적절히 활용하면 Node.js에서도 멀티스레딩이 가능하며, CPU 집중적인 작업을 효과적으로 분산할 수 있음!**  

