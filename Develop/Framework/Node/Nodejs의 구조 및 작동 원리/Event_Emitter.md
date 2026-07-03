---
title: EventEmitter (events 모듈)
tags: [framework, node, nodejs의-구조-및-작동-원리, events, eventemitter, async, memory-leak]
updated: 2026-06-02
---

# EventEmitter (events 모듈)

## 배경

Node.js 코어 대부분이 EventEmitter 위에 올라가 있다. `http.Server`도, `net.Socket`도, `fs.ReadStream`도, `process` 객체 자체도 전부 EventEmitter를 상속한다. `server.on('request', ...)`나 `stream.on('data', ...)`를 쓸 때 우리가 실제로 호출하는 건 `events` 모듈이 정의한 메서드다. 그래서 EventEmitter의 동작을 정확히 모르면 스트림이나 소켓에서 생기는 미묘한 버그를 추적하기 어렵다.

특히 두 가지를 헷갈리는 경우가 많다. 하나는 `emit`이 비동기일 거라고 착각하는 것이고, 다른 하나는 `error` 이벤트를 그냥 흔한 이벤트 중 하나로 취급하는 것이다. 둘 다 운영 환경에서 프로세스가 죽거나 콜백이 꼬이는 원인이 된다.

```js
const { EventEmitter } = require('node:events');

const emitter = new EventEmitter();

emitter.on('order', (id) => {
  console.log('주문 처리:', id);
});

emitter.emit('order', 1001);
// 주문 처리: 1001
```

## EventEmitter 내부 구조

내부 구현을 대충 알아두면 누수 디버깅이 훨씬 빨라진다. EventEmitter 인스턴스는 사실 몇 개 안 되는 필드로 돌아간다.

- `_events`: 이벤트 이름을 키로, 등록된 리스너를 값으로 들고 있는 객체. 핵심 자료구조다.
- `_eventsCount`: `_events`에 등록된 키 개수. `eventNames()`가 이 값을 기반으로 동작한다.
- `_maxListeners`: 이 인스턴스의 최대 리스너 한도. 기본값은 `undefined`이고 그땐 `EventEmitter.defaultMaxListeners`(기본 10)를 본다.

`_events`의 값 모양이 특이하다. 한 이벤트에 리스너가 하나만 등록되면 함수 자체가 값으로 들어간다. 두 개 이상이 되면 그제서야 배열로 승격된다. 메모리와 호출 성능을 아끼려는 마이크로 최적화다.

```js
const { EventEmitter } = require('node:events');
const e = new EventEmitter();

e.on('x', () => {});
console.log(typeof e._events.x);       // function ← 하나면 함수 그대로

e.on('x', () => {});
console.log(Array.isArray(e._events.x)); // true   ← 두 개부터 배열
console.log(e._events.x.length);         // 2
```

평소엔 신경 쓸 일이 없는데, heap snapshot이나 디버깅 중에 `emitter._events`를 직접 까보면 차이가 드러난다. 어떤 키는 Function, 어떤 키는 Array(N)이다. Array의 length가 수천 개씩 되면 그게 누수 1순위 후보다.

호출 순서는 배열에 들어간 순서 그대로다. 0번 인덱스부터 동기로 순차 호출된다. `prependListener`나 `prependOnceListener`로 등록하면 배열 앞쪽에 꽂혀 먼저 실행된다. 코어 모듈 일부는 자기 리스너를 prepend로 등록해서 사용자 리스너보다 먼저 돌게 만들어 둔다.

`once`로 등록한 리스너는 등록 시점에 래퍼 함수로 감싸서 `_events`에 들어간다. 래퍼는 호출되자마자 자기 자신을 `removeListener`로 떼고 원본 함수를 부른다. 그래서 once 리스너도 `_events`를 까보면 그냥 함수다. 다만 이 래퍼에는 `listener` 속성으로 원본 함수 참조가 붙어 있다. `removeListener`에 원본 함수를 넘기면 Node.js가 배열을 돌면서 각 원소의 `listener` 속성과도 비교해서 매칭한다. 그래서 once로 등록한 핸들러도 원본 참조로 떼는 게 가능하다.

```js
const onReady = () => console.log('ready');
e.once('ready', onReady);

console.log(typeof e._events.ready);            // function (래퍼)
console.log(e._events.ready.listener === onReady); // true
e.off('ready', onReady);                        // 원본 참조로 떼도 정상 제거
```

리스너 호출 자체는 V8 입장에서 그냥 함수 호출이라 EventEmitter 자체 오버헤드는 무시할 수 있다. 다만 `emit`이 인자 개수에 따라 분기된 빠른 경로(arg 0~3개)를 가지고 있어, 인자 4개 이상이면 약간 느려진다. 마이크로벤치에선 보이지만 실무에서 신경 쓸 정도는 아니다.

## on, once, off

`on`은 같은 이벤트에 리스너를 계속 쌓는다. `addListener`와 완전히 같은 메서드이고, 보통 `on`을 쓴다. 같은 함수를 두 번 등록하면 두 번 다 호출된다. 중복 등록을 막아주지 않는다.

```js
const handler = (id) => console.log('처리:', id);

emitter.on('order', handler);
emitter.on('order', handler); // 같은 함수를 또 등록

emitter.emit('order', 1);
// 처리: 1
// 처리: 1   ← 두 번 호출됨
```

`once`는 한 번만 실행되고 자동으로 제거된다. 초기화 완료 신호, 연결 성공 같은 일회성 이벤트에 쓴다.

```js
emitter.once('ready', () => {
  console.log('초기화 완료');
});

emitter.emit('ready'); // 초기화 완료
emitter.emit('ready'); // 아무 일도 안 일어남
```

`off`(= `removeListener`)로 리스너를 떼어낸다. 여기서 자주 실수하는 게 익명 함수를 등록하고 나중에 떼려고 하는 경우다. 등록할 때와 같은 함수 참조를 넘겨야만 제거된다.

```js
// 이렇게 하면 절대 못 뗀다
emitter.on('data', (chunk) => process(chunk));
emitter.off('data', (chunk) => process(chunk)); // 다른 함수라서 무시됨

// 참조를 변수에 담아둬야 한다
const onData = (chunk) => process(chunk);
emitter.on('data', onData);
emitter.off('data', onData); // 정상 제거
```

`removeAllListeners()`로 특정 이벤트나 전체 리스너를 한 번에 지울 수도 있는데, 코어 모듈 인스턴스에 대고 쓰면 Node.js 내부가 등록해둔 리스너까지 날아가서 동작이 깨질 수 있다. 직접 만든 emitter에만 쓰는 게 안전하다.

`once`의 핵심을 한 가지 더 짚으면, `once`는 내부적으로 래퍼 함수를 등록한다. 그래서 등록 후 `off`로 떼려면 원본 함수가 아니라 그 래퍼를 알아야 하는데, `removeListener`에 원본 함수를 넘기면 Node.js가 알아서 매칭해서 떼어준다. 이건 신경 쓸 필요 없이 동작한다.

```js
const onReady = () => console.log('ready');
emitter.once('ready', onReady);
emitter.off('ready', onReady); // 원본 함수로 떼도 정상 제거됨
```

## emit은 동기로 실행된다

가장 중요한 부분이다. `emit`은 등록된 리스너를 등록된 순서대로 **동기적으로, 순차적으로** 호출한다. 큐에 넣고 나중에 처리하는 게 아니다. `emit`을 호출한 그 자리에서 모든 리스너가 끝날 때까지 코드가 블로킹된다.

```js
emitter.on('task', () => {
  console.log('1');
});
emitter.on('task', () => {
  console.log('2');
});

console.log('emit 전');
emitter.emit('task');
console.log('emit 후');

// emit 전
// 1
// 2
// emit 후   ← 리스너가 다 끝난 뒤에 찍힌다
```

이 특성 때문에 리스너 안에서 무거운 동기 작업을 하면 이벤트 루프가 그만큼 멈춘다. CPU를 많이 쓰는 동기 연산을 리스너에 넣으면 그 시간 동안 다른 요청 처리가 다 밀린다.

리스너가 던진 예외도 동기로 전파된다. 한 리스너에서 예외가 나면 그 뒤에 등록된 리스너는 실행되지 않고, 예외가 `emit` 호출부로 그대로 올라온다.

```js
emitter.on('task', () => {
  throw new Error('첫 번째 리스너 폭발');
});
emitter.on('task', () => {
  console.log('이 줄은 실행 안 됨');
});

try {
  emitter.emit('task');
} catch (err) {
  console.log('잡힘:', err.message); // 잡힘: 첫 번째 리스너 폭발
}
```

리스너끼리 격리되길 원한다면 각 리스너 내부에서 try/catch를 하거나, 리스너 안에서 작업을 `setImmediate`로 던져 분리해야 한다. EventEmitter 자체는 리스너 간 격리를 해주지 않는다.

## error 이벤트는 특별하다

`error` 이벤트는 다른 이벤트와 취급이 다르다. `error` 이벤트를 emit했는데 등록된 리스너가 하나도 없으면, EventEmitter는 그 에러 객체를 throw한다. 그리고 이건 보통 잡히지 않은 예외가 되어 **프로세스를 종료시킨다**.

```js
const emitter = new EventEmitter();

emitter.emit('error', new Error('처리 안 된 에러'));
// throws:
// Error: 처리 안 된 에러
//     at ...
// 프로세스 종료 (exit code 1)
```

이게 의도된 설계다. 스트림이나 소켓에서 에러가 났는데 아무도 처리하지 않는 상태를 조용히 넘기면 더 위험하다고 보기 때문에, 일부러 시끄럽게 죽인다. 그래서 스트림이나 소켓을 다룰 때 `error` 리스너 등록을 빼먹으면 운영 중에 갑자기 프로세스가 내려간다.

```js
const fs = require('node:fs');

const stream = fs.createReadStream('/없는/파일');

// error 리스너가 없으면 ENOENT 에러가 throw되어 프로세스가 죽는다
stream.on('error', (err) => {
  console.error('스트림 에러 처리:', err.code); // ENOENT
});
```

직접 만든 EventEmitter에서도 마찬가지다. 에러를 emit하는 코드를 짰다면 그 emitter를 쓰는 쪽에서 반드시 `error` 리스너를 달아야 한다. 안 그러면 사용하는 사람이 영문도 모르고 프로세스가 죽는 걸 겪는다.

한 가지 더, `errorMonitor`라는 심볼이 있다. 이걸로 등록한 리스너는 모니터링용이라 에러를 "소비"하지 않는다. 즉 `errorMonitor` 리스너만 있고 일반 `error` 리스너가 없으면, 모니터링 리스너가 호출된 뒤에도 여전히 에러가 throw된다. 로깅만 하고 에러 처리 책임은 그대로 두고 싶을 때 쓴다.

```js
const { EventEmitter, errorMonitor } = require('node:events');
const emitter = new EventEmitter();

emitter.on(errorMonitor, (err) => {
  console.log('모니터링 로깅:', err.message);
  // 여기서 에러를 소비하지 않는다
});

emitter.emit('error', new Error('xx'));
// 모니터링 로깅: xx
// 그 다음 여전히 throw됨 → 프로세스 종료
```

## MaxListenersExceededWarning과 setMaxListeners

한 이벤트에 리스너가 11개 이상 쌓이면 Node.js가 경고를 찍는다.

```
(node:12345) MaxListenersExceededWarning: Possible EventEmitter memory leak detected.
11 order listeners added to [EventEmitter]. Use emitter.setMaxListeners() to increase limit
```

이건 에러가 아니라 경고다. 동작은 멈추지 않는다. 기본 한도가 10인 이유는, 보통 한 이벤트에 리스너가 그렇게 많이 붙을 일이 없는데 11개를 넘어간다면 어딘가에서 리스너를 제거하지 않고 계속 쌓고 있을 가능성, 즉 메모리 누수를 의심하라는 신호다.

진짜로 리스너가 많이 필요한 정당한 경우라면 한도를 올린다.

```js
emitter.setMaxListeners(50); // 이 인스턴스만 한도 50
```

전역으로 기본값을 바꾸려면 이렇게 한다. 다만 전역으로 올리면 진짜 누수가 났을 때 경고를 못 보게 되니 신중해야 한다.

```js
const { EventEmitter } = require('node:events');
EventEmitter.defaultMaxListeners = 20; // 모든 emitter의 기본 한도
```

경고가 떴을 때 무작정 `setMaxListeners`로 한도를 올려서 경고를 끄는 건 대부분 잘못된 대응이다. 한도를 올리기 전에, 정말 그만큼 리스너가 필요한 건지 아니면 어디선가 같은 리스너를 반복 등록하고 안 떼는 건지부터 확인해야 한다. 후자라면 한도를 올려도 리스너는 계속 쌓이고 결국 메모리가 샌다.

## 리스너 메모리 누수 디버깅

리스너 누수는 거의 항상 같은 구조에서 나온다. 수명이 긴 객체에 수명이 짧은 객체가 리스너를 달고 떼지 않는다. 짧은 객체가 GC되어야 하는데 긴 객체의 `_events` 안에 함수 참조가 남아 있으니 영영 못 죽는다. 운영에서 만난 패턴 몇 개를 정리한다.

### 패턴 1: 공유 bus에 요청마다 리스너 등록

```js
// 안티패턴: 요청마다 공유 emitter에 리스너를 등록하고 안 뗀다
function handleRequest(req, res) {
  globalBus.on('shutdown', () => {
    res.end('서버 종료 중');
  });
  // 요청이 끝나도 위 리스너가 globalBus에 남는다 → 요청 수만큼 누적
}
```

요청마다 `shutdown` 리스너가 쌓이고, 익명 함수가 클로저로 `res`를 잡고 있어 GC도 안 된다. RPS 100 정도만 돼도 몇 분 안에 수만 개 리스너가 쌓이고 경고가 뜬다. 더 무서운 건 실제 shutdown이 일어나면 수만 개 리스너가 동기로 한 번에 호출된다는 점이다. graceful shutdown이 안 끝나서 헬스체크에 죽지 않은 채로 떠다니는 좀비 프로세스가 된다.

수정은 응답이 끝날 때 리스너를 떼는 것이다.

```js
function handleRequest(req, res) {
  const onShutdown = () => res.end('서버 종료 중');
  globalBus.on('shutdown', onShutdown);

  res.on('close', () => {
    globalBus.off('shutdown', onShutdown);
  });
}
```

`AbortController`를 쓰는 방법도 있다. `signal` 옵션으로 등록하면 signal이 aborted되는 시점에 Node.js가 알아서 떼준다. 떼는 코드를 까먹기 쉬운 환경에서 안전판으로 쓸 만하다.

```js
function handleRequest(req, res) {
  const ac = new AbortController();
  globalBus.on('shutdown', () => res.end('서버 종료 중'), { signal: ac.signal });
  res.on('close', () => ac.abort());
}
```

### 패턴 2: DB 풀, HTTP 에이전트 같은 싱글톤에 리스너

데이터베이스 풀이나 HTTP 에이전트는 보통 프로세스 전체에서 하나만 살아 있는 싱글톤이다. 거기에 매 요청 단위로 리스너를 달면 같은 결과가 나온다. 경고가 이런 모양으로 찍힌다.

```
(node:1234) MaxListenersExceededWarning: Possible EventEmitter memory leak detected.
11 error listeners added to [Pool]. Use emitter.setMaxListeners() to increase limit
```

대상이 `Pool`이면 보통 DB나 HTTP 풀, `Socket`이면 net/http 소켓, `ReadStream`이면 fs 스트림이다. 어떤 객체가 누수의 보유자인지 클래스 이름으로 먼저 좁힌다. `[EventEmitter]`로 찍히는 경우는 직접 만든 emitter나 사용자 정의 클래스라 추가 단서가 필요하다.

겪었던 사례 한 가지. http(s) 에이전트 keepAlive를 쓰면서 요청별로 `socket.on('error', ...)`를 다는 미들웨어가 있었다. 에이전트가 keepAlive로 같은 소켓을 재사용하니까 같은 소켓 인스턴스에 error 리스너가 계속 쌓였다. 트래픽 피크 때 경고가 떴고, 응답 다 보낸 후에 떼는 코드를 넣어 해결했다.

### 패턴 3: process 객체에 SIGTERM/SIGINT 다발 등록

graceful shutdown을 한다고 모듈마다 `process.on('SIGTERM', ...)`을 달면 모듈 수만큼 핸들러가 쌓인다. 자체 모듈 + 의존 라이브러리가 각자 등록하면 11개를 금방 넘는다. 신호가 한 번 들어오면 그 핸들러들이 동기로 줄줄이 호출되어, 한 핸들러가 오래 걸리면 뒤 핸들러는 SIGKILL 타임아웃에 잘려나간다.

정리 로직을 한군데로 모아 해결한다. shutdown 코디네이터를 만들고 다른 모듈은 거기에 정리 함수를 등록한다. `process`에는 코디네이터만 한 번 단다.

```js
const shutdownTasks = [];
process.once('SIGTERM', async () => {
  for (const task of shutdownTasks) {
    await task().catch((err) => console.error('shutdown 실패', err));
  }
  process.exit(0);
});

function onShutdown(fn) { shutdownTasks.push(fn); }
module.exports = { onShutdown };
```

### 추적 순서

경고가 떴을 때 실무에서 거치는 순서다.

먼저 경고 메시지에서 이벤트 이름과 클래스 이름을 본다. 위에서 본 것처럼 `11 close listeners added to [Pool]` 같은 형태로 찍히니까 어떤 객체, 어떤 이벤트인지 한눈에 좁혀진다.

그다음 `--trace-warnings`로 재현한다.

```bash
node --trace-warnings app.js
```

경고에 스택이 같이 찍혀서 11번째 리스너가 등록된 위치가 나온다. 자기 코드가 스택에 있으면 거기가 범인이다. node_modules 안에서만 보이면 라이브러리 이슈를 의심하고 그쪽 트래커를 본다. 라이브러리 코드와 자기 호출이 섞여 있을 땐 자기 호출 지점에서 등록 빈도를 먼저 검토한다.

그래도 안 좁혀지면 등록 시점마다 스택을 찍는 임시 후킹을 끼운다.

```js
const orig = emitter.addListener.bind(emitter);
emitter.addListener = function (event, fn) {
  if (event === 'close') {
    console.log('close 등록:', new Error().stack);
  }
  return orig(event, fn);
};
```

지저분하지만 어디서 N번째가 들어왔는지 확실히 잡힌다. 운영에 켜두면 안 되는 코드라 로컬 재현용으로만 쓴다.

현재 등록 상태를 들여다보는 API도 알아두면 좋다.

```js
console.log(emitter.eventNames());                // 등록된 이벤트 이름 목록
console.log(emitter.listenerCount('shutdown'));   // 특정 이벤트 리스너 수
console.log(emitter.listeners('shutdown'));       // 리스너 함수 배열

const { getEventListeners } = require('node:events');
console.log(getEventListeners(emitter, 'shutdown').length);
```

`getEventListeners`는 일반 EventEmitter뿐 아니라 `AbortSignal` 같은 DOM 스타일 EventTarget에도 동작한다. 라이브러리 코드를 디버깅할 때 어느 쪽 타입인지 미리 모를 때 무난하게 쓰는 함수다.

### 그래도 못 잡을 때: heap snapshot

스택만으로 안 잡히는 경우가 있다. 등록 코드는 한 줄인데 그 함수가 호출되는 경로가 여러 개라 어느 경로에서 누수가 났는지 모르겠는 경우다. 이때는 heap snapshot을 뜬다.

`node --inspect app.js`로 띄우고 Chrome DevTools Memory 탭에서 트래픽 들어오기 전과 후로 snapshot을 두 번 떠서 Comparison 뷰로 본다. Delta가 큰 객체 중 `EventEmitter`, `Pool`, `Socket`, `Array`가 늘어나 있으면 그게 후보다. Retainers 트리를 타고 올라가면 어느 변수가 잡고 있는지 보이고, 거기서 등록 코드를 역추적한다.

운영 중 재현이 안 되고 메모리만 천천히 새는 경우엔 `--heapsnapshot-signal=SIGUSR2`를 켜두고 의심 시점에 SIGUSR2를 보내 snapshot을 받아오기도 한다. 컨테이너 환경이면 디스크 마운트와 권한을 미리 확인해 둬야 snapshot이 떨어진다.

```bash
node --heapsnapshot-signal=SIGUSR2 app.js
# 별도 셸에서
kill -SIGUSR2 <pid>
```

### 한도를 올리는 게 맞는 경우

리스너가 정말 많이 필요한 정당한 경우도 있다. 큰 풀 객체에 여러 워커가 자기 리스너를 정상적으로 등록하는 경우, 또는 pub/sub 허브처럼 설계상 구독자 수가 많은 경우다. 이때는 `setMaxListeners`로 인스턴스 단위로 한도를 올린다.

```js
pool.setMaxListeners(50);
```

전역 기본값 `EventEmitter.defaultMaxListeners`는 가급적 건드리지 않는다. 전역으로 올리면 진짜 누수가 났을 때 경고가 안 떠서 발견 시점이 늦어진다. 한도를 올릴 거면 그 인스턴스에 좁혀서 올리고, 왜 올렸는지를 주석으로 남겨둔다. 다음에 본 사람이 누수와 헷갈리지 않는다.

## 비동기 핸들러에서 emit 쓸 때 주의점

`emit`이 동기라는 점이 비동기 핸들러와 만나면 함정이 된다. 리스너를 `async` 함수로 등록하면 EventEmitter는 그 함수를 호출만 하고, 반환된 Promise는 신경 쓰지 않는다. await도 안 하고 catch도 안 한다.

```js
emitter.on('order', async (id) => {
  await saveToDb(id); // 여기서 reject되면?
});

emitter.emit('order', 1);
// emit은 saveToDb가 끝나길 기다리지 않고 바로 다음 줄로 넘어간다
```

문제는 두 가지다. 첫째, `emit`이 비동기 작업의 완료를 기다리지 않으므로 `emit` 다음 줄에서 작업이 끝났다고 가정하면 안 된다. 둘째, 그리고 더 위험한 건, async 리스너 안에서 발생한 reject는 잡히지 않은 Promise 거부(unhandledRejection)가 된다. 동기 리스너의 throw와 달리 `emit`을 감싼 try/catch로는 절대 못 잡는다.

```js
emitter.on('order', async () => {
  throw new Error('비동기 리스너 폭발');
});

try {
  emitter.emit('order', 1);
} catch (err) {
  // 여기로 안 들어온다. emit은 이미 동기적으로 끝났고
  // 에러는 마이크로태스크에서 unhandledRejection으로 떠돈다
}
// → UnhandledPromiseRejection 경고, Node 버전/설정에 따라 프로세스 종료
```

그래서 async 리스너를 쓸 거면 리스너 안에서 직접 try/catch로 닫아야 한다.

```js
emitter.on('order', async (id) => {
  try {
    await saveToDb(id);
  } catch (err) {
    logger.error('주문 저장 실패', { id, err });
  }
});
```

반대로, 어떤 이벤트가 발생할 때까지 await로 기다리고 싶다면 `events.once`(정적 메서드)를 쓴다. 이건 인스턴스 메서드 `once`와 이름은 같지만 다른 것으로, 이벤트가 한 번 발생하길 기다리는 Promise를 돌려준다.

```js
const { once } = require('node:events');

async function waitForReady(server) {
  await once(server, 'listening'); // listening 이벤트를 기다린다
  console.log('서버 준비됨');
}
```

여기서도 주의할 점이 있다. `once(emitter, 'event')`로 기다리는 동안 그 emitter가 `error`를 emit하면, 그 Promise가 reject된다. 그래서 보통 try/catch로 감싼다. 또 이벤트를 영영 안 보내면 Promise가 영원히 안 풀리므로, 타임아웃이 필요하면 `AbortSignal`을 같이 넘긴다.

```js
const { once } = require('node:events');

const ac = new AbortController();
setTimeout(() => ac.abort(), 5000); // 5초 타임아웃

try {
  await once(emitter, 'done', { signal: ac.signal });
} catch (err) {
  if (err.name === 'AbortError') {
    console.log('5초 안에 done 이벤트가 안 옴');
  }
}
```

이벤트를 여러 번 비동기로 순회하고 싶을 땐 `events.on`(정적 메서드)이 async iterator를 만들어준다. 스트림처럼 들어오는 이벤트를 `for await`로 받는다.

```js
const { on } = require('node:events');

async function consume(emitter) {
  for await (const [id] of on(emitter, 'order')) {
    await processOrder(id); // 한 번에 하나씩 순서대로 처리
  }
}
```

`on` 정적 메서드는 이벤트를 내부 버퍼에 쌓아두기 때문에, `for await` 본문에서 처리가 느리면 버퍼가 계속 커진다. 처리 속도가 이벤트 발생 속도를 못 따라가는 상황에서는 이쪽도 메모리 문제를 일으킬 수 있으니 백프레셔를 고려해야 한다.

## 커스텀 EventEmitter 상속 패턴

자기 클래스를 이벤트 기반으로 만들고 싶으면 EventEmitter를 상속한다. 작업 진행 상황을 알리거나, 상태 변화를 구독시키고 싶을 때 쓴다.

```js
const { EventEmitter } = require('node:events');

class JobRunner extends EventEmitter {
  constructor() {
    super(); // 반드시 호출해야 한다
    this.running = false;
  }

  async run(jobs) {
    this.running = true;
    this.emit('start', jobs.length);

    for (let i = 0; i < jobs.length; i++) {
      try {
        await this.process(jobs[i]);
        this.emit('progress', i + 1, jobs.length);
      } catch (err) {
        // error 이벤트는 리스너가 없으면 throw되니, 리스너 유무를 확인하거나
        // 사용하는 쪽에서 error 리스너를 달도록 문서화해야 한다
        this.emit('error', err);
        return;
      }
    }

    this.running = false;
    this.emit('done');
  }

  async process(job) {
    // 실제 작업
  }
}
```

사용하는 쪽은 이렇게 구독한다.

```js
const runner = new JobRunner();

runner.on('start', (total) => console.log(`총 ${total}건 시작`));
runner.on('progress', (done, total) => console.log(`${done}/${total}`));
runner.on('error', (err) => console.error('작업 실패:', err.message)); // 빼면 위험
runner.on('done', () => console.log('전체 완료'));

runner.run([job1, job2, job3]);
```

`super()` 호출을 빼먹으면 `this.emit`이 정의되지 않아 터진다. 상속할 때 constructor를 직접 정의했다면 `super()`를 반드시 첫 줄에 넣어야 한다.

상속 대신 인스턴스를 내부에 들고 위임하는 방식(composition)도 있다. EventEmitter의 모든 메서드를 외부에 노출하고 싶지 않을 때 이쪽을 택한다. 필요한 메서드만 골라서 외부에 열어줄 수 있다.

```js
class JobRunner {
  constructor() {
    this._bus = new EventEmitter();
  }

  on(event, listener) {
    this._bus.on(event, listener);
    return this; // 체이닝 유지
  }

  off(event, listener) {
    this._bus.off(event, listener);
    return this;
  }

  // emit은 외부에 노출하지 않는다 → 외부에서 함부로 이벤트를 쏘지 못하게
}
```

상속은 코드가 짧지만 `setMaxListeners`, `removeAllListeners` 같은 메서드까지 전부 외부에 노출된다. 위임은 코드가 길어지는 대신 인터페이스를 통제할 수 있다. 라이브러리처럼 외부에 공개하는 객체라면 위임 쪽이 인터페이스 관리에 낫고, 내부에서만 쓰는 객체라면 상속이 간단하다.

## 운영에서 자주 겪는 문제

운영에서 EventEmitter 관련으로 실제 부딪히는 건 대체로 세 가지다. `error` 리스너를 안 달아서 프로세스가 죽는 것, 리스너를 떼지 않아서 누수와 경고가 뜨는 것, async 리스너의 reject가 unhandledRejection으로 새는 것이다. 이 셋은 emit이 동기로 동작하고 error가 특별 취급된다는 두 가지 사실만 정확히 알면 대부분 예방된다.
