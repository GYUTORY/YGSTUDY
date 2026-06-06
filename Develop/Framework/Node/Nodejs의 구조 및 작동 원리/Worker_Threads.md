---
title: worker_threads 모듈 심화
tags: [framework, node, nodejs, worker-threads, message-port, shared-array-buffer, atomics]
updated: 2026-06-06
---

# worker_threads 모듈 심화

같은 디렉토리의 `Thread.md`는 워커 스레드 개념을 잡아주고, `Cluster.md`는 프로세스 단위 분기를 다룬다. 이 문서는 그 사이에서 빠져있던 `worker_threads` 모듈 내부, 그러니까 `MessagePort`로 어떻게 데이터가 오가는지, ArrayBuffer 소유권을 넘기면 실제로 메모리에서 무슨 일이 벌어지는지, `SharedArrayBuffer`와 `Atomics`로 락을 어떻게 직접 구현하는지를 적는다.

운영에서 워커 풀을 돌려본 경험이 있다면 "이게 왜 안 빠르지", "왜 OOM이 터지지", "왜 메시지가 한 박자 늦지" 같은 질문이 떠오를 텐데, 그 답은 대부분 이 모듈의 내부 동작을 모른 채 그냥 `postMessage`만 쓰고 있어서다.

## 워커는 어디서 도는가 — 프로세스 한 개, V8 isolate 여러 개

Node.js의 워커는 OS 스레드 위에 V8 isolate를 새로 띄워서 동작한다. 핵심은 다음 세 가지다.

- 프로세스는 하나다. `process.pid`는 메인과 워커가 같다.
- V8 isolate는 별도다. 즉 힙(heap)이 분리된다. 메인의 객체를 워커에서 직접 참조할 수 없다.
- libuv 이벤트 루프도 워커마다 별도로 돈다. 워커 안에서 `setTimeout`을 걸어도 메인 루프와 무관하다.

이게 Cluster와 결정적으로 다른 점이다. Cluster는 `child_process.fork`로 진짜 별도 프로세스를 띄운다. PID도 다르고, V8 인스턴스도 다르고, OS가 격리한다. 한쪽이 죽어도 다른 쪽은 멀쩡하다. Worker는 같은 프로세스 안에서 도니까 한 워커에서 `process.exit(1)`을 호출하면 메인까지 같이 죽는다. 실수로라도 워커 코드 안에 `process.exit`을 쓰지 말아야 한다. 워커를 종료하려면 `parentPort.close()`나 그냥 함수를 끝내라.

```javascript
// main.js
const { Worker, threadId } = require('worker_threads');

console.log(`메인 threadId=${threadId}, pid=${process.pid}`);
const w = new Worker(`
  const { threadId, parentPort } = require('worker_threads');
  parentPort.postMessage({ threadId, pid: process.pid });
`, { eval: true });

w.on('message', (m) => console.log('워커:', m));
// 출력: 메인 threadId=0, pid=12345
//      워커: { threadId: 1, pid: 12345 }  ← pid 동일, threadId만 다름
```

`threadId`는 메인이 0, 워커가 1부터 증가한다. 워커끼리도 unique하다.

## MessagePort와 MessageChannel — postMessage가 실제로 하는 일

워커를 만들면 `parentPort`라는 게 자동으로 주어진다. 이건 `MessagePort` 인스턴스다. 그리고 메인 쪽에서 `worker.postMessage(x)`를 호출하면 그 메시지는 워커의 `parentPort`로 들어간다. 반대 방향도 같다.

여기까지가 보통 알고 있는 그림인데, 실제로는 `MessagePort` 두 개가 쌍으로 묶여 있다. 이걸 `MessageChannel`로 직접 만들 수 있다.

```javascript
const { MessageChannel, Worker } = require('worker_threads');

const { port1, port2 } = new MessageChannel();
// port1, port2는 양 끝이다. 한쪽으로 보내면 다른 쪽으로 도착한다.

port1.on('message', (m) => console.log('port1 수신:', m));
port2.postMessage('hello');  // → port1.on('message')가 받음
```

`MessageChannel`을 직접 만드는 이유는 두 가지다.

첫째, 메인-워커 통신 채널을 여러 개 두고 싶을 때. 메인은 워커와 `parentPort` 하나로만 묶여 있지만, 별도의 채널을 만들어서 워커에게 한쪽 끝(`port2`)을 넘겨주면 그 채널은 별개의 메시지 큐로 동작한다. 작업 큐와 헬스체크 큐를 분리하고 싶을 때 쓴다.

```javascript
// main.js
const { Worker, MessageChannel } = require('worker_threads');

const worker = new Worker('./worker.js');
const { port1, port2 } = new MessageChannel();

worker.postMessage({ kind: 'init', port: port2 }, [port2]);
// 두 번째 인자가 transferList. port2의 소유권을 워커로 넘긴다.
// 이제 메인은 port1, 워커는 port2를 쥔다.

port1.on('message', (m) => console.log('헬스체크 응답:', m));
setInterval(() => port1.postMessage('ping'), 1000);
```

```javascript
// worker.js
const { parentPort } = require('worker_threads');

parentPort.on('message', ({ kind, port }) => {
  if (kind === 'init') {
    port.on('message', (m) => {
      if (m === 'ping') port.postMessage('pong');
    });
  }
});
```

이렇게 하면 `parentPort`로 오는 작업 메시지와 별도 채널의 헬스체크가 섞이지 않는다. 작업 큐가 막혀도 헬스체크는 따로 동작한다.

둘째, 워커끼리 직접 통신시키고 싶을 때. 메인이 두 워커를 만들고, `MessageChannel`의 양 끝을 각 워커에 하나씩 넘겨주면 워커 A와 워커 B가 메인을 거치지 않고 직접 메시지를 주고받는다.

```javascript
// main.js
const { Worker, MessageChannel } = require('worker_threads');

const a = new Worker('./worker.js');
const b = new Worker('./worker.js');
const { port1, port2 } = new MessageChannel();

a.postMessage({ peer: port1 }, [port1]);
b.postMessage({ peer: port2 }, [port2]);
// 이제 a와 b는 메인을 거치지 않고 통신한다.
```

메인을 거치는 hop을 줄이면 메시지 지연이 줄어든다. 메인이 다른 일로 바쁘면 hop 한 번이 수 ms 단위로 늘어지기도 한다.

### 구조화 복제(structured clone)와 ref/unref

`postMessage`로 보낸 값은 기본적으로 구조화 복제 알고리즘으로 직렬화된다. JSON.stringify와 비슷하지만 다르다. JSON에서 못 보내는 `Map`, `Set`, `Date`, `RegExp`, 순환 참조까지 다 보낸다. 대신 함수와 클래스 인스턴스의 prototype 체인은 잃는다. 워커 쪽에서 받으면 그냥 평범한 객체다.

복제 비용을 무시하면 안 된다. 큰 객체를 매번 `postMessage`로 보내면 직렬화에 시간이 박힌다. 100MB짜리 버퍼를 그냥 보내면 메인에서 직렬화, 워커에서 역직렬화로 두 번 복사하는 셈이다. 이 비용을 피하려면 transferable 객체를 써야 한다(아래에서 자세히 다룬다).

또 하나, `MessagePort`는 기본적으로 이벤트 루프를 살아있게 만든다. 메시지를 더 기다리지 않아도 되는 상태가 되면 `port.unref()`로 풀어줘야 한다. 안 그러면 프로세스가 종료되지 않는다. 헬스체크 채널을 만들었는데 메인이 안 죽는다면 거의 이 문제다.

```javascript
port.unref();   // 이 포트가 있어도 이벤트 루프 종료 막지 않음
port.ref();     // 다시 살림
```

## Transferable — ArrayBuffer 소유권을 넘긴다는 것

100MB짜리 데이터를 워커에 넘겨야 한다고 하자. 그냥 `postMessage`로 보내면 메인 힙에 있는 100MB가 직렬화돼서 워커 힙에 똑같이 100MB가 만들어진다. 메모리 200MB, 시간도 두 번 들어간다.

`ArrayBuffer`는 transferable 객체다. transferList에 넣어서 보내면 데이터를 복사하지 않고 소유권만 워커로 넘긴다. 메인 쪽 `ArrayBuffer`는 detached 상태(`byteLength === 0`)가 된다. 워커는 같은 메모리 영역을 그대로 잡고 작업한다.

```javascript
const { Worker } = require('worker_threads');

const buf = new ArrayBuffer(100 * 1024 * 1024); // 100MB
const u8 = new Uint8Array(buf);
u8[0] = 42;

const w = new Worker(`
  const { parentPort } = require('worker_threads');
  parentPort.on('message', ({ buf }) => {
    const view = new Uint8Array(buf);
    console.log('워커가 받은 첫 바이트:', view[0]); // 42
    view[0] = 99;
    parentPort.postMessage({ buf }, [buf]); // 다시 메인으로 소유권 반환
  });
`, { eval: true });

w.postMessage({ buf }, [buf]); // transferList에 buf
console.log('전송 후 메인 buf.byteLength:', buf.byteLength); // 0 (detached)

w.on('message', ({ buf: returned }) => {
  console.log('반환된 첫 바이트:', new Uint8Array(returned)[0]); // 99
});
```

여기서 중요한 두 가지.

첫째, transfer가 끝나면 메인의 원본은 못 쓴다. detached된 `ArrayBuffer`에 접근하면 `TypeError: Cannot perform Construct on a detached ArrayBuffer`가 난다. 워커에 보낸 다음 메인에서도 같이 쓰고 싶으면 `SharedArrayBuffer`를 써야 한다.

둘째, transfer 가능한 객체는 정해져 있다. `ArrayBuffer`, `MessagePort`, `FileHandle`, `Blob`, `X509Certificate` 등이다. `Buffer`(Node.js의)는 `ArrayBuffer`를 감싼 것이므로 `buffer.buffer`(underlying ArrayBuffer)를 transferList에 넣어야 한다.

```javascript
const buf = Buffer.allocUnsafe(1024 * 1024);
w.postMessage({ data: buf }, [buf.buffer]); // buf.buffer가 ArrayBuffer
// 이후 메인의 buf는 사용 불가
```

`Buffer.allocUnsafe`로 만든 버퍼는 Node.js 내부 풀(Pool)을 공유하기도 하는데, transfer를 쓸 거면 `Buffer.allocUnsafeSlow`나 `Buffer.alloc`으로 만드는 게 안전하다. 풀의 일부만 떼서 쓰는 버퍼를 transfer하면 풀 전체가 detached되어 다른 코드가 깨진다.

### 운영에서 보이는 transferable 실수

이미지 처리 파이프라인에서 봤던 사례. 워커에 raw bytes를 보내고 처리 결과를 다시 받는 구조였는데, 메모리 사용량이 워커 수에 비례해서 늘었다. 코드를 보니 `postMessage(buf)`로 transferList 없이 보내고 있었다. 즉 매 요청마다 복사가 일어났다. transferList에 넣는 한 줄만 추가하니 메모리가 절반으로 떨어졌다.

반대 케이스도 있다. transfer해놓고 메인에서 원본을 다시 읽으려고 해서 `TypeError`가 터지는 경우. 한 번 보낸 버퍼는 잊어버려야 한다. 어느 쪽이든 detached 여부는 `buf.byteLength === 0`으로 확인할 수 있다.

## SharedArrayBuffer + Atomics — 메모리를 진짜로 공유한다

`ArrayBuffer`는 한 번에 한 곳만 소유한다. `SharedArrayBuffer`는 다르다. 여러 스레드가 동시에 같은 메모리 영역을 본다. 메인과 워커가, 또는 워커끼리, 같은 바이트에 동시에 쓸 수 있다.

당연히 race condition이 생긴다. 그래서 `Atomics`가 같이 있다. `Atomics.add`, `Atomics.compareExchange`, `Atomics.wait`, `Atomics.notify` 같은 것들이다.

```javascript
const { Worker } = require('worker_threads');

const sab = new SharedArrayBuffer(4); // 4바이트, Int32 하나
const counter = new Int32Array(sab);

const N = 4;
const workers = [];
for (let i = 0; i < N; i++) {
  workers.push(new Worker(`
    const { parentPort, workerData } = require('worker_threads');
    const counter = new Int32Array(workerData.sab);
    for (let j = 0; j < 100000; j++) {
      Atomics.add(counter, 0, 1); // 원자적 증가
    }
    parentPort.postMessage('done');
  `, { eval: true, workerData: { sab } }));
}

Promise.all(workers.map(w => new Promise(r => w.on('message', r))))
  .then(() => {
    console.log('최종 카운터:', Atomics.load(counter, 0)); // 정확히 400000
    workers.forEach(w => w.terminate());
  });
```

`Atomics.add` 대신 `counter[0]++`를 쓰면 결과가 400000보다 작게 나온다. `++`는 읽기-증가-쓰기 세 단계라서 중간에 다른 스레드가 끼어들면 갱신이 사라진다. 이게 lost update다.

### Atomics.wait / Atomics.notify — 진짜 동기화 프리미티브

`Atomics.wait`는 특정 메모리 위치의 값이 기대값과 같으면 스레드를 블록한다. 다른 스레드가 `Atomics.notify`로 깨워주거나 타임아웃이 나야 풀린다. 이걸로 mutex, semaphore, condition variable 다 만들 수 있다.

워커 풀에서 작업이 들어올 때까지 워커를 재워두는 패턴.

```javascript
// 워커 쪽
const { workerData } = require('worker_threads');
const flag = new Int32Array(workerData.flagBuf);

while (true) {
  // flag[0]이 0이면 1초까지 잠. 0이 아니면 즉시 진행.
  Atomics.wait(flag, 0, 0, 1000);

  if (Atomics.load(flag, 0) === 1) {
    // 작업 수행
    Atomics.store(flag, 0, 0); // 다시 대기 상태로
  } else if (Atomics.load(flag, 0) === -1) {
    break; // 종료 신호
  }
}
```

메인 쪽에서는 작업이 생기면 `Atomics.store(flag, 0, 1); Atomics.notify(flag, 0, 1);`로 깨운다.

주의할 점. `Atomics.wait`는 메인 스레드에서는 못 쓴다. 메인이 블록되면 이벤트 루프가 멈춰서 I/O가 다 죽는다. 그래서 메인에서 호출하면 `TypeError: Atomics.wait cannot be called in this context`가 난다. 메인에서 메모리 위치를 동기적으로 기다려야 한다면 `Atomics.waitAsync`(비교적 최근 추가됨)를 쓴다. Promise를 반환하므로 이벤트 루프를 막지 않는다.

### SharedArrayBuffer 쓸 때 머리 아픈 것들

- 모든 값이 정수 배열이 된다. 객체 그래프를 통째로 공유할 수 없다. JSON으로 직렬화해서 바이트로 쑤셔넣거나, MessagePack/FlatBuffers 같은 바이너리 포맷을 쓰거나, 큰 행렬·이미지처럼 처음부터 typed array에 맞는 데이터일 때만 쓸 만하다.
- 메모리 모델이 복잡하다. C/C++ 다뤄본 경험이 있다면 익숙하겠지만, JS만 했다면 sequenced-before, happens-before 같은 개념을 처음 만난다. 잘못 쓰면 같은 인덱스를 읽는데 워커마다 다른 값을 본다.
- 보안 헤더 이슈. 브라우저에서는 `Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy` 설정 없이 `SharedArrayBuffer`를 못 쓴다. Node.js에서는 상관없지만, 같은 코드를 브라우저로 옮기면 깨진다.

90%의 케이스에서는 transferable로 ArrayBuffer 소유권을 주고받는 게 충분하다. `SharedArrayBuffer`는 정말 락이 필요한 작업, 예를 들어 락프리 큐, 카운터, 큰 typed array에 여러 워커가 동시에 쓰는 경우에만 꺼낸다.

## resourceLimits — 워커 하나가 OOM으로 메인까지 끌고 가는 걸 막는다

같은 프로세스라는 게 단점이다. 워커가 메모리를 잡아먹으면 메인의 힙도 같이 압박을 받는다. V8 힙 전체가 같이 죽는다.

`Worker` 옵션에 `resourceLimits`를 주면 워커별 힙 한도를 설정할 수 있다.

```javascript
const { Worker } = require('worker_threads');

const w = new Worker('./worker.js', {
  resourceLimits: {
    maxOldGenerationSizeMb: 256,   // old generation 힙 (장수 객체) 최대 256MB
    maxYoungGenerationSizeMb: 32,  // young generation (단기 객체)
    codeRangeSizeMb: 16,           // JIT 코드 영역
    stackSizeMb: 4,                // 호출 스택
  },
});

w.on('exit', (code) => {
  if (code === 1) console.log('워커가 OOM으로 종료됨');
});
```

한도를 넘으면 워커는 `process.exit(1)`로 죽는다. `exit` 이벤트가 발생하고, 메인은 다른 워커를 띄워 복구할 수 있다. 한도 없이 돌리면 V8가 힙을 계속 늘리다가 결국 시스템 OOM killer가 프로세스를 죽이는데, 그러면 모든 워커와 메인이 한꺼번에 날아간다.

운영에서 워커별 한도를 잡아두면 "PDF 변환 워커 하나가 미친 파일을 만나서 죽었지만 서버는 살아있다" 같은 상황이 가능해진다. 한도 없이 돌리면 그 PDF 한 장에 서버 전체가 내려간다.

수치는 워크로드 보고 정한다. 이미지 디코딩이면 입력 크기의 3~4배 정도, JSON 파싱이면 입력 크기의 8~10배까지 본다. 실제 측정해보고 잡는 게 안전하다.

## 워커 풀 패턴 — 매번 워커를 띄우지 마라

워커 생성은 싸지 않다. 새 V8 isolate를 만들고, 모듈 로딩하고, 초기화한다. 작은 작업마다 새 워커를 띄우면 워커 생성 비용이 작업 비용보다 더 클 수 있다.

풀(pool)을 두고 작업을 분배하는 게 표준이다. CPU 코어 수만큼 워커를 띄워두고, 큐에 작업을 쌓고, 놀고 있는 워커에 할당한다.

```javascript
// pool.js
const { Worker } = require('worker_threads');
const os = require('os');

class WorkerPool {
  constructor(workerPath, size = os.cpus().length) {
    this.workerPath = workerPath;
    this.size = size;
    this.workers = [];
    this.idle = [];
    this.queue = [];

    for (let i = 0; i < size; i++) this.spawn();
  }

  spawn() {
    const w = new Worker(this.workerPath, {
      resourceLimits: { maxOldGenerationSizeMb: 256 },
    });
    w.busy = false;
    w.on('message', (result) => {
      const { resolve } = w.currentJob;
      w.currentJob = null;
      w.busy = false;
      resolve(result);
      this.dispatch();
    });
    w.on('error', (err) => {
      if (w.currentJob) w.currentJob.reject(err);
      // 죽은 워커 교체
      this.workers = this.workers.filter(x => x !== w);
      this.spawn();
    });
    w.on('exit', (code) => {
      if (code !== 0 && w.currentJob) w.currentJob.reject(new Error(`exit ${code}`));
      this.workers = this.workers.filter(x => x !== w);
      if (this.workers.length < this.size) this.spawn();
    });
    this.workers.push(w);
    this.idle.push(w);
  }

  run(data, transferList = []) {
    return new Promise((resolve, reject) => {
      this.queue.push({ data, transferList, resolve, reject });
      this.dispatch();
    });
  }

  dispatch() {
    while (this.queue.length && this.idle.length) {
      const job = this.queue.shift();
      const w = this.idle.shift();
      w.busy = true;
      w.currentJob = job;
      w.postMessage(job.data, job.transferList);
    }
    // idle 다시 채우기
    this.idle = this.workers.filter(w => !w.busy);
  }

  async terminate() {
    await Promise.all(this.workers.map(w => w.terminate()));
  }
}

module.exports = WorkerPool;
```

```javascript
// worker.js (풀에서 돌릴 작업자)
const { parentPort } = require('worker_threads');

parentPort.on('message', (input) => {
  // 무거운 계산
  let result = 0;
  for (let i = 0; i < input.iterations; i++) result += Math.sqrt(i);
  parentPort.postMessage(result);
});
```

```javascript
// 사용
const WorkerPool = require('./pool');
const pool = new WorkerPool('./worker.js');

(async () => {
  const results = await Promise.all([
    pool.run({ iterations: 1e7 }),
    pool.run({ iterations: 1e7 }),
    pool.run({ iterations: 1e7 }),
  ]);
  console.log(results);
  await pool.terminate();
})();
```

이 패턴에서 자주 놓치는 부분.

- **에러 처리**. 워커가 죽으면 진행 중이던 작업은 reject해야 한다. 안 그러면 호출자의 Promise가 영원히 pending이다. 위 코드에서 `error`와 `exit` 핸들러가 그걸 한다.
- **워커 교체**. 워커가 죽으면 풀 크기가 줄어든다. 새로 띄워서 채워야 한다. resourceLimits를 잡았다면 OOM으로 가끔씩 죽는 게 정상이라 더 중요하다.
- **백프레셔**. 큐에 작업이 무한정 쌓이면 메모리가 터진다. `queue.length`가 일정 수 이상이면 새 요청을 거절하거나 대기시켜야 한다. Promise를 그냥 만들어주면 호출자는 자기 작업이 큐에 들어갔는지조차 모른다.
- **transferList**. 큰 버퍼를 작업으로 보낼 거면 transferList를 같이 받아야 한다. 그냥 `run(data)`만 받으면 큰 객체는 매번 복사된다.

`piscina` 같은 라이브러리가 이 패턴을 잘 구현해뒀다. 직접 만들기 귀찮으면 그걸 쓴다.

## Cluster와 Worker의 차이 — 언제 무엇을 쓰나

같은 디렉토리에 `Cluster.md`, `Cluster와 Multi Thread.md`가 있으니 자세한 비교는 거기에 맡기고, 선택 기준만 정리한다.

| 항목 | Cluster (프로세스) | Worker Threads (스레드) |
|---|---|---|
| 격리 단위 | OS 프로세스 (PID 분리) | V8 isolate (PID 동일) |
| 메모리 공유 | 불가능. IPC만 가능 | SharedArrayBuffer로 공유 가능 |
| 데이터 전달 | JSON 직렬화 (느림) | 구조화 복제 + transferable (빠름) |
| 한 쪽 크래시 영향 | 다른 프로세스 멀쩡 | 같은 프로세스라 같이 죽음 |
| 부트 시간 | 느림 (수백 ms) | 빠름 (수십 ms) |
| 네이티브 애드온 | 각 프로세스가 각자 로드 | 워커마다 다시 로드되는데 일부 애드온은 thread-safe하지 않으면 깨짐 |
| 적합한 워크로드 | HTTP 서버 부하 분산 | CPU 집약 계산, 큰 버퍼 처리 |

대충 이렇게 갈린다.

- HTTP 요청을 코어 수만큼 나눠서 받고 싶다 → Cluster. 각 프로세스가 자기 포트를 들고 OS의 SO_REUSEPORT나 마스터가 round-robin으로 분배한다.
- 들어온 HTTP 요청 안에서 무거운 계산(이미지 리사이즈, PDF 생성, 암호화)을 해야 한다 → Worker Threads. 메인 이벤트 루프 비우는 게 목적이다.
- 둘 다 필요한 경우도 많다. Cluster로 프로세스 N개 띄우고, 각 프로세스 안에 Worker 풀을 두는 식.

네이티브 애드온 호환성도 무시하면 안 된다. 일부 C++ 애드온은 thread-safe하지 않아서 워커에서 로드하면 크래시난다. `node-canvas`나 오래된 DB 드라이버 같은 것들이 그런 경우가 있다. 그럴 땐 Cluster로 가야 한다.

## 자주 보는 함정들

워커를 처음 도입할 때 보통 다음 중 하나를 밟는다.

**1. `new Worker`를 요청마다 만든다**

요청 하나당 워커 하나씩 띄우면 응답 시간이 워커 생성 시간으로 깨진다. 본격적으로 쓰려면 풀로 가야 한다.

**2. transferList 없이 큰 버퍼를 보낸다**

100MB 이미지를 그냥 postMessage로 보내면 직렬화에 시간이 박힌다. 게다가 메모리 두 배. transferList를 잊지 마라.

**3. 워커 안에서 `process.exit`을 쓴다**

워커가 메인 프로세스를 죽인다. 작업이 끝났으면 그냥 함수가 끝나게 두거나, 외부에서 `worker.terminate()`로 정리하라.

**4. unref 안 하고 프로세스가 안 죽는다**

테스트가 끝났는데 Node가 종료되지 않는다면 `MessagePort` 한쪽이 살아있을 가능성이 크다. `port.unref()` 호출하거나 명시적으로 `port.close()`한다.

**5. SharedArrayBuffer에 일반 인덱싱으로 쓴다**

여러 워커가 같은 인덱스에 쓰는데 `arr[0]++`처럼 일반 연산을 쓰면 결과가 이상하다. `Atomics.add`, `Atomics.compareExchange`를 써야 한다.

**6. resourceLimits를 안 잡고 워커 풀을 돌린다**

워커 하나가 미친 입력을 만나서 힙을 다 먹으면 V8가 메인 포함 전체를 죽인다. 풀 워커에는 한도를 잡아둔다.

**7. 워커 코드 안에서 `require`로 큰 모듈을 매번 로드한다**

워커마다 V8 isolate가 별개라서 require 캐시도 별개다. 부팅 때 한 번 로드해두고 `parentPort.on('message')` 안에서는 재사용하라.

## 디버깅 — 워커 안에서 뭔가 잘못됐을 때

워커 안의 에러는 메인 쪽에서 잘 안 보인다. `worker.on('error', ...)`를 반드시 달아라. 안 달면 워커가 throw해도 메인은 모른다.

```javascript
worker.on('error', (err) => {
  console.error('워커 에러:', err.stack);
});
worker.on('exit', (code) => {
  if (code !== 0) console.error(`워커 비정상 종료: ${code}`);
});
```

디버거를 붙이려면 메인을 `--inspect`로 띄우고 워커 생성 시 `execArgv: ['--inspect=0']`을 줘서 임의 포트로 워커 디버거를 띄운다. Chrome DevTools에서 워커 isolate를 따로 잡을 수 있다.

```javascript
new Worker('./worker.js', { execArgv: ['--inspect=0'] });
```

포트 0을 주면 OS가 빈 포트를 할당해준다. 그러면 워커마다 포트가 안 겹친다.

스택 트레이스가 워커 경계에서 끊긴다는 것도 알아둬야 한다. 메인에서 `pool.run(...)`을 호출했는데 워커 안에서 에러가 나면, 메인에 도착하는 에러의 스택은 워커 내부만 보여준다. 메인 쪽 호출 위치를 추적하려면 작업에 ID나 호출 스택 스냅샷을 같이 실어 보내야 한다.

## 정리

`worker_threads`는 같은 프로세스에서 V8 isolate를 여러 개 띄우는 모듈이다. 메시지는 `MessagePort` 쌍으로 오가고, 큰 데이터는 transferable로 소유권을 넘기는 게 정석이다. 진짜로 공유 메모리가 필요하면 `SharedArrayBuffer`와 `Atomics`를 쓰지만 90%는 transferable로 충분하다. 운영에서는 풀 패턴으로 묶고 `resourceLimits`로 워커 하나가 전체를 끌고 가는 걸 막는다. Cluster와는 격리 단위(프로세스 vs isolate)가 다르고, 한 쪽이 죽으면 같이 죽는다는 점이 워커의 가장 큰 트레이드오프다.
