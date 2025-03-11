# Node.js - Event Loop 개념 및 동작 방식 🚀

## 1. Event Loop란? 🤔

**Node.js의 Event Loop(이벤트 루프)**는 **비동기 처리를 가능하게 하는 핵심 메커니즘**입니다.  
Node.js는 **싱글 스레드(Single Thread) 기반**이지만, **Event Loop**를 활용하여 **비동기 I/O 작업을 효율적으로 처리**할 수 있습니다.

> **✨ Event Loop의 핵심 개념**
> - **Node.js는 기본적으로 싱글 스레드**
> - **비동기 작업(I/O, 타이머, 네트워크 요청 등)을 처리**
> - **이벤트 기반(Event-Driven)으로 실행**
> - **논-블로킹(Non-Blocking) 방식으로 동작**
> - **콜백 함수와 함께 실행 흐름을 관리**

---

## 2. Event Loop의 동작 과정 🔄

Node.js의 **Event Loop**는 다음과 같은 단계로 실행됩니다.

1️⃣ **Timers (타이머 실행)**
- `setTimeout()`, `setInterval()` 등의 타이머 콜백 실행

2️⃣ **I/O Callbacks (I/O 작업 완료 후 콜백 실행)**
- 파일 시스템, 네트워크 요청 등의 비동기 작업이 완료되면 실행됨

3️⃣ **Idle, Prepare (내부적인 작업)**
- 내부적으로 사용되며, 일반적인 애플리케이션 개발에서는 거의 사용되지 않음

4️⃣ **Poll (I/O 이벤트 대기 및 처리)**
- 가장 중요한 단계! 비동기 I/O 작업을 처리하는 핵심 부분
- 새로운 I/O 이벤트가 있으면 처리하고, 없으면 다음 단계로 이동

5️⃣ **Check (setImmediate() 실행)**
- `setImmediate()`로 예약된 콜백이 실행됨

6️⃣ **Close Callbacks (닫기 이벤트 처리)**
- 소켓 연결 종료, `process.exit()` 등 실행

---

## 3. Event Loop의 단계별 실행 예제

### 3.1 기본적인 Event Loop 실행 순서

#### ✅ 예제 (Event Loop 실행 순서)
```javascript
console.log("1️⃣ Start");

setTimeout(() => console.log("4️⃣ setTimeout"), 0);
setImmediate(() => console.log("3️⃣ setImmediate"));

Promise.resolve().then(() => console.log("2️⃣ Promise"));

console.log("1️⃣ End");
```

### 📌 실행 결과:
```
1️⃣ Start
1️⃣ End
2️⃣ Promise
3️⃣ setImmediate
4️⃣ setTimeout
```

> **📌 `Promise.then()`은 Microtask Queue에서 처리되므로 먼저 실행됨!**  
> **📌 `setImmediate()`는 Poll 단계 이후 실행되므로 `setTimeout(0)`보다 먼저 실행될 가능성이 높음!**

---

### 3.2 setTimeout vs. setImmediate 차이점

#### ✅ 예제 (setTimeout vs. setImmediate)
```javascript
const fs = require("fs");

fs.readFile(__filename, () => {
    setTimeout(() => console.log("setTimeout 실행"), 0);
    setImmediate(() => console.log("setImmediate 실행"));
});
```

### 📌 실행 결과:
```
setImmediate 실행
setTimeout 실행
```

> **📌 파일 읽기(`fs.readFile`) 후 `setImmediate()`가 먼저 실행됨!**
> - `setImmediate()`는 Poll 단계가 끝나면 즉시 실행
> - `setTimeout(0)`은 Poll 단계 이후 Timers 단계에서 실행

---

### 3.3 process.nextTick() (Microtask Queue)

#### ✅ 예제 (process.nextTick() vs. Promise)
```javascript
console.log("1️⃣ Start");

process.nextTick(() => console.log("2️⃣ nextTick"));
Promise.resolve().then(() => console.log("3️⃣ Promise"));

console.log("1️⃣ End");
```

### 📌 실행 결과:
```
1️⃣ Start
1️⃣ End
2️⃣ nextTick
3️⃣ Promise
```

> **📌 `process.nextTick()`은 현재 실행 중인 코드가 끝난 직후 실행되며, Promise보다 먼저 실행됨!**

---

## 4. Event Loop과 Worker Threads 비교

| 비교 항목 | Event Loop | Worker Threads |
|-----------|-----------|---------------|
| **기본 개념** | 싱글 스레드 기반 비동기 실행 | 멀티 스레드 기반 작업 분산 |
| **사용 목적** | I/O 작업, 네트워크 요청 처리 | CPU 집중적인 연산 처리 |
| **비동기 방식** | 이벤트 기반 (Event-Driven) | 백그라운드 워커 스레드 사용 |
| **예제** | `setTimeout`, `setImmediate`, `Promise` | `worker_threads` 모듈 사용 |

#### ✅ Worker Threads 예제
```javascript
const { Worker } = require('worker_threads');

const worker = new Worker('./worker.js'); // 별도의 스레드 실행

worker.on('message', (msg) => console.log("워커에서 받은 메시지:", msg));
worker.postMessage("작업 시작");
```

> **📌 Worker Threads는 CPU 집중적인 연산 처리에 적합하며, I/O 작업에는 Event Loop가 더 효과적!**

---

## 📌 결론

- **Node.js의 Event Loop는 싱글 스레드이지만 논-블로킹 방식으로 비동기 작업을 처리**
- **setTimeout(), setImmediate(), process.nextTick(), Promise 등 실행 순서를 이해하는 것이 중요**
- **CPU 집중적인 작업은 Worker Threads를 활용하는 것이 적절**

> **👉🏻 Event Loop의 동작을 이해하면 Node.js의 비동기 동작을 효율적으로 활용할 수 있음!**

