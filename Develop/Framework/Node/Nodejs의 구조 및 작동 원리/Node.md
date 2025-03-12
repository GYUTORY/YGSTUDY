# Node.js - 개념과 핵심 기술 🚀

## 1. Node.js란? 🤔

Node.js는 **JavaScript 실행 환경(Run-time Environment)**으로, 웹 브라우저가 아닌 **컴퓨터에서 JavaScript를 실행할 수 있도록 만들어진 프로그램**입니다.

> **✨ Node.js의 특징**
> - JavaScript를 브라우저 밖에서도 실행 가능
> - 싱글 스레드 기반의 **이벤트 루프(Event Loop) 모델** 활용
> - **비동기 논블로킹 I/O(Non-Blocking I/O)**를 지원하여 빠른 성능 제공
> - 내장된 HTTP 서버 기능을 통해 별도의 웹 서버 없이 서버 구축 가능
> - **V8 엔진**과 **libuv** 라이브러리를 기반으로 동작

✅ **즉, Node.js는 JavaScript로 서버 애플리케이션을 개발할 수 있도록 도와주는 실행기입니다.**

---

## 2. Node.js의 핵심 요소 🔥

Node.js는 **V8 엔진**과 **libuv** 라이브러리를 활용하여 동작합니다.

### 2.1 V8 엔진이란? 🚀

✔ **V8은 구글이 만든 오픈소스 JavaScript 엔진**입니다.  
✔ 크롬 브라우저와 안드로이드 브라우저에서도 사용됨.  
✔ **JavaScript 코드를 빠르게 실행하도록 최적화**되어 있음.  
✔ Just-In-Time (JIT) 컴파일을 통해 JavaScript 코드를 즉시 기계어로 변환하여 성능 향상.

#### ✅ V8을 활용한 JavaScript 실행 예제
```javascript
console.log("Hello, Node.js!"); // V8 엔진이 실행
```  

> **📌 Node.js는 V8 엔진을 이용하여 JavaScript 코드를 실행!**

---

### 2.2 libuv란? ⚙️

✔ **Node.js의 비동기 I/O 모델을 담당하는 라이브러리**  
✔ 이벤트 기반(Event-Driven) 및 논블로킹(Non-Blocking) I/O 모델 구현  
✔ 멀티플랫폼(Windows, Linux, macOS)에서 동작 가능  
✔ **파일 시스템, 네트워크, 프로세스, 스레드 풀 등을 관리**

#### ✅ libuv의 주요 역할
- **이벤트 루프(Event Loop) 관리**
- **비동기 파일 입출력 (fs 모듈)**
- **네트워크 통신 관리 (HTTP, TCP, UDP)**
- **타이머 (setTimeout, setInterval)**

> **📌 Node.js의 핵심 기능을 담당하는 비동기 이벤트 처리 시스템!**

---

## 3. 이벤트 기반(Event-Driven) 프로그래밍 🔄

✔ **이벤트가 발생하면 미리 등록해둔 콜백 함수를 실행하는 방식**  
✔ 이벤트 리스너(Event Listener)를 활용하여 특정 이벤트가 발생할 때 동작을 정의

#### ✅ 이벤트 기반 시스템 예제 (클릭 이벤트)
```javascript
const button = document.getElementById("myButton");
button.addEventListener("click", () => {
    console.log("버튼이 클릭되었습니다!");
});
```  

> **📌 이벤트 발생 시 미리 등록된 콜백 함수가 실행됨!**

#### ✅ Node.js의 이벤트 기반 예제
```javascript
const fs = require('fs');

fs.readFile('example.txt', 'utf8', (err, data) => {
    if (err) throw err;
    console.log("파일 읽기 완료:", data);
});

console.log("파일 읽기 요청 보냄!");
```
📌 **출력 결과:**
```
파일 읽기 요청 보냄!
파일 읽기 완료: (파일 내용 출력)
```
> **📌 파일을 읽는 동안 다른 작업이 블로킹되지 않음 (비동기 동작)**

---

## 4. 이벤트 루프(Event Loop) 🌀

Node.js는 **이벤트 루프(Event Loop)를 활용하여 비동기 작업을 처리**합니다.

> **✨ 이벤트 루프의 역할**
> - 이벤트 발생 시 호출할 콜백 함수들을 관리
> - 비동기 작업(파일 읽기, 네트워크 요청 등) 실행 후, 완료되면 콜백 함수 실행
> - 작업이 없을 때 대기 상태 유지

### ✅ 이벤트 루프의 단계
1️⃣ **Timers (setTimeout, setInterval 등 타이머 처리)**  
2️⃣ **I/O Callbacks (비동기 I/O 작업 완료 시 콜백 실행)**  
3️⃣ **Idle, Prepare (내부적인 작업 처리, 일반적으로 신경 쓰지 않아도 됨)**  
4️⃣ **Poll (I/O 이벤트 대기 및 실행, 가장 중요한 단계!)**  
5️⃣ **Check (setImmediate() 실행 단계)**  
6️⃣ **Close Callbacks (닫기 이벤트 처리, 예: 소켓 연결 종료)**

#### ✅ 이벤트 루프 실행 예제
```javascript
console.log("1️⃣ Start");

setTimeout(() => console.log("4️⃣ setTimeout 실행"), 0);
setImmediate(() => console.log("3️⃣ setImmediate 실행"));

Promise.resolve().then(() => console.log("2️⃣ Promise 실행"));

console.log("1️⃣ End");
```
📌 **출력 결과:**
```
1️⃣ Start
1️⃣ End
2️⃣ Promise 실행
3️⃣ setImmediate 실행
4️⃣ setTimeout 실행
```  
> **📌 `Promise.then()`은 Microtask Queue에서 처리되므로 먼저 실행됨!**  
> **📌 `setImmediate()`는 Poll 단계 이후 실행되므로 `setTimeout(0)`보다 먼저 실행될 가능성이 높음!**

---

## 5. 백그라운드(Background) 🛠️

✔ Node.js 내부에서 실행되는 **비동기 작업을 처리하는 공간**  
✔ JavaScript가 아닌 C/C++로 작성된 코드가 실행되는 영역  
✔ 여러 작업이 동시에 실행될 수 있음

#### ✅ 예제 (비동기 타이머 실행)
```javascript
setTimeout(() => console.log("타이머 실행!"), 1000);
console.log("메인 스레드 실행 중...");
```  

> **📌 setTimeout이 실행될 동안 Node.js는 다른 작업을 수행 가능!**

---

## 6. 태스크 큐(Task Queue) 📌

✔ 이벤트가 발생한 후, **콜백 함수를 실행하기 위해 관리하는 대기열**  
✔ **완료된 비동기 작업의 콜백들이 대기하는 곳**  
✔ `setTimeout()`, `setImmediate()`, `Promise` 등이 대기

#### ✅ 예제 (콜백 실행 순서)
```javascript
setTimeout(() => console.log("setTimeout 실행"), 0);
setImmediate(() => console.log("setImmediate 실행"));
process.nextTick(() => console.log("nextTick 실행"));
```  
📌 **출력 결과:**
```
nextTick 실행
setImmediate 실행
setTimeout 실행
```  
> **📌 `process.nextTick()`이 가장 먼저 실행됨! (Microtask Queue 우선 처리)**

---

## 📌 결론

- **Node.js는 JavaScript 실행 환경으로, 서버 애플리케이션 개발이 가능**
- **V8 엔진을 사용하여 빠른 JavaScript 실행 성능 제공**
- **libuv를 이용해 비동기 논블로킹 I/O 모델을 구현**
- **이벤트 기반(Event-Driven)으로 동작하며, 이벤트 루프(Event Loop)를 통해 비동기 작업 관리**
- **I/O 작업과 비동기 작업을 효율적으로 처리하기 위한 Task Queue 활용**

> **👉🏻 Node.js의 이벤트 루프와 비동기 모델을 이해하면 고성능 애플리케이션을 구축할 수 있음!**  

