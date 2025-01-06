
# Node.js Event Loop

Node.js의 **Event Loop**는 JavaScript 런타임에서 비동기 작업을 처리하는 핵심 메커니즘입니다. Node.js는 단일 스레드로 작동하지만, 비동기 작업을 효율적으로 처리하여 높은 성능을 제공합니다.

## Event Loop의 역할

Event Loop는 다음을 수행합니다:

1. **비동기 작업 관리**: I/O 작업(파일 읽기/쓰기, 네트워크 요청 등)과 같은 비동기 작업을 관리합니다.
2. **콜백 실행**: 완료된 비동기 작업의 콜백 함수를 적절한 시점에 실행합니다.
3. **Task Queue 확인**: Task Queue에 쌓인 작업을 메인 스레드에서 순차적으로 실행합니다.

## Event Loop의 6단계

Node.js의 Event Loop는 6단계로 나뉩니다.

1. **Timers 단계**: `setTimeout`과 `setInterval`의 콜백을 실행합니다.
2. **Pending Callbacks 단계**: 지연된 I/O 콜백(예: 일부 네트워크 작업)이 처리됩니다.
3. **Idle, Prepare 단계**: 내부 작업을 준비하거나 조정하는 단계입니다.
4. **Poll 단계**: 새로운 I/O 이벤트를 처리하거나, 적합한 콜백을 실행합니다.
5. **Check 단계**: `setImmediate`로 예약된 콜백을 실행합니다.
6. **Close Callbacks 단계**: 닫기 콜백(예: 소켓 종료 등)이 실행됩니다.

## 예시 코드

다음은 Event Loop의 동작을 이해하기 위한 예제 코드입니다.

```javascript
console.log("Start");

setTimeout(() => {
  console.log("setTimeout");
}, 0);

setImmediate(() => {
  console.log("setImmediate");
});

Promise.resolve().then(() => {
  console.log("Promise");
});

console.log("End");
```

### 출력 결과

```
Start
End
Promise
setTimeout
setImmediate
```

### 이유
1. **동기 코드**인 `console.log("Start")`와 `console.log("End")`가 먼저 실행됩니다.
2. **Promise**의 `then`은 `microtask queue`에 들어가고, 이벤트 루프가 우선 처리합니다.
3. `setTimeout`과 `setImmediate`는 각각 **Timer Queue**와 **Check Queue**에 들어가며, `setTimeout`이 먼저 실행됩니다.

## Event Loop와 비동기 프로그래밍

Node.js에서 Event Loop를 활용하면 I/O 집약적인 작업을 효율적으로 처리할 수 있습니다. 예를 들어, 서버 요청을 비동기적으로 처리하면 단일 스레드에서도 높은 처리량을 달성할 수 있습니다.

### 비동기 서버 예제

```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  if (req.url === "/") {
    setTimeout(() => {
      res.end("Hello, World!");
    }, 2000);
  } else {
    res.end("Other route");
  }
});

server.listen(3000, () => {
  console.log("Server is running on http://localhost:3000");
});
```

위 코드는 비동기적으로 요청을 처리하여 동시에 여러 클라이언트를 처리할 수 있게 합니다.

## 참고 자료

- [Node.js 공식 문서](https://nodejs.org/en/docs/)
- [MDN Event Loop](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop)
