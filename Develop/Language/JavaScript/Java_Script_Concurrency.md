---
title: Node.js 동시성과 CPU 블로킹
tags: [javascript, nodejs, performance, backend]
updated: 2026-08-22
---

# Node.js 동시성과 CPU 블로킹

Node.js 이벤트 루프가 왜 블로킹되는지, 블로킹을 피하려면 무엇을 써야 하는지, Promise.all에서 자주 틀리는 부분을 정리했다. 브라우저 이벤트 루프가 아니라 서버 사이드 Node.js에 초점을 맞췄다.

---

## libuv가 돌리는 이벤트 루프 페이즈

Node.js의 이벤트 루프는 V8이 아니라 libuv가 돌린다. libuv는 여섯 페이즈를 순서대로 돌고, 각 페이즈 사이에 마이크로태스크 큐를 먼저 비운다.

```
timers → pending callbacks → idle/prepare → poll → check → close callbacks
                         ↑              ↑
               각 페이즈 진입 전, process.nextTick + Promise 마이크로태스크 소진
```

### timers 페이즈

`setTimeout`과 `setInterval`의 콜백이 여기서 실행된다. 주의할 점은 "만료된 타이머 전부"가 아니라 "이 루프 진입 시점 기준으로 만료된 타이머"만 처리한다는 거다. 루프를 한 바퀴 도는 동안 추가로 만료된 타이머는 다음 루프에서 처리한다.

### pending callbacks 페이즈

TCP 에러 같은 시스템 오류 콜백이 여기 온다. 직접 다룰 일은 드물다.

### poll 페이즈

I/O 완료 콜백을 처리하는 핵심 페이즈다. 파일 읽기, 네트워크 응답, DB 쿼리 결과가 전부 여기서 콜 스택에 올라간다.

poll 큐가 비면 libuv는 다음 타이머가 만료될 때까지 여기서 대기한다. `setTimeout(fn, 100)`을 걸어두면 poll이 최대 100ms 동안 블록된다는 뜻이다. `setImmediate`를 걸어두면 대기 없이 즉시 check 페이즈로 넘어간다.

### check 페이즈

`setImmediate` 콜백만 처리한다. I/O 콜백 안에서 `setImmediate`를 쓰면 "이번 루프의 나머지 I/O보다 먼저, 타이머보다는 확실히 먼저" 실행된다.

```javascript
const fs = require('fs');

fs.readFile('/etc/hosts', () => {
  setTimeout(() => console.log('setTimeout'), 0);
  setImmediate(() => console.log('setImmediate'));
});

// 출력 항상: setImmediate → setTimeout
// poll 직후가 check 페이즈라 setImmediate가 앞선다
```

메인 모듈(I/O 바깥)에서 `setTimeout`과 `setImmediate`를 같이 쓰면 순서가 비결정적이다. 시스템 부하에 따라 첫 루프에서 timers를 처리할 수도, check를 먼저 돌 수도 있다.

### process.nextTick의 위치

`process.nextTick`은 페이즈가 아니다. 어느 페이즈에서든 콜 스택이 비는 순간 마이크로태스크 큐보다 먼저 처리되는 별도 큐다.

```javascript
setImmediate(() => console.log('setImmediate'));
setTimeout(() => console.log('setTimeout'), 0);
process.nextTick(() => console.log('nextTick'));
Promise.resolve().then(() => console.log('promise'));

// 출력: nextTick → promise → (setTimeout 또는 setImmediate)
```

`process.nextTick`을 재귀적으로 계속 등록하면 nextTick 큐가 비워지지 않아 I/O 콜백이 실행되지 않는 기아 현상이 생긴다.

```javascript
// 이벤트 루프 기아
function recursiveTick() {
  process.nextTick(recursiveTick);
}
recursiveTick(); // 파일 I/O, 네트워크 요청 전부 멈춤
```

---

## CPU-bound 작업이 이벤트 루프를 블로킹하는 패턴

Node.js는 I/O를 비동기로 처리하지만 CPU 연산은 동기다. 무거운 연산이 콜 스택에 올라오면 그 시간 동안 이벤트 루프가 멈춘다.

### JSON 파싱

요청마다 수십 MB JSON을 파싱하는 API를 만들면 파싱 시간 동안 다른 요청을 처리하지 못한다.

```javascript
app.post('/process', (req, res) => {
  // 50MB JSON이면 파싱에 200ms 이상 걸린다
  // 이 동안 다른 연결은 전부 대기
  const data = JSON.parse(req.body);
  res.json({ count: data.items.length });
});
```

실제 프로덕션에서 이 패턴으로 타임아웃이 났다. 클라이언트는 응답 없이 연결이 끊기고 서버 로그에는 아무것도 없다. 이벤트 루프 자체가 멈춰 있어서 로그를 쓸 여유가 없다.

### 암호화 연산

`crypto.pbkdf2Sync`는 이름부터 동기다. 비밀번호 해싱 같은 용도로 쓰면 해싱 시간 동안 서버가 완전히 멈춘다.

```javascript
// 위험
app.post('/register', (req, res) => {
  const hash = crypto.pbkdf2Sync(req.body.password, salt, 100000, 64, 'sha512');
  // pbkdf2Sync로 100000 반복이면 수백ms 동안 이벤트 루프 블로킹
});

// 비동기 버전으로 교체
app.post('/register', async (req, res) => {
  const hash = await util.promisify(crypto.pbkdf2)(
    req.body.password, salt, 100000, 64, 'sha512'
  );
  // libuv 스레드 풀에서 돌아 이벤트 루프를 막지 않는다
});
```

libuv는 스레드 풀(기본 4개)을 관리한다. `crypto.pbkdf2` 같은 비동기 버전은 이 스레드 풀에서 실행되어 메인 스레드를 막지 않는다.

### 정규식 재앙

catastrophic backtracking이 발생하는 정규식은 입력에 따라 실행 시간이 기하급수적으로 늘어난다.

```javascript
// 악의적 입력으로 이벤트 루프 수십 초 블로킹 가능
const vulnerable = /^(a+)+$/;
vulnerable.test('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!');
```

사용자 입력을 그대로 정규식에 넣거나, 중첩 수량자(`(a+)+`, `(a|a)+`)가 있는 패턴을 쓰면 이 문제에 취약하다.

### 이벤트 루프 지연 측정

블로킹 여부를 수치로 보려면 `--perf` 플래그나 아래 패턴으로 측정한다.

```javascript
// 이벤트 루프 지연을 주기적으로 측정
let lastCheck = process.hrtime.bigint();

setInterval(() => {
  const now = process.hrtime.bigint();
  const delay = Number(now - lastCheck) / 1e6 - 100; // ms 단위, 기대값 100ms에서 차이
  if (delay > 10) {
    console.warn(`이벤트 루프 지연: ${delay.toFixed(1)}ms`);
  }
  lastCheck = now;
}, 100);
```

`clinic.js` 같은 도구를 쓰면 페이즈별 블로킹 시간을 시각화할 수 있다.

---

## Worker Threads vs child_process vs cluster

CPU-bound 작업을 메인 스레드에서 분리하는 방법이 세 가지 있다. 용도가 다르다.

### Worker Threads

Node.js 10.5부터 정식 지원한다. 같은 프로세스 안에서 별도 V8 인스턴스를 스레드로 돌린다. `SharedArrayBuffer`로 메모리를 공유할 수 있고, `MessageChannel`로 통신한다.

```javascript
// main.js
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

if (isMainThread) {
  const worker = new Worker(__filename, {
    workerData: { input: [1, 2, 3, 4, 5] }
  });

  worker.on('message', result => {
    console.log('결과:', result); // 메인 스레드는 블로킹 없이 다른 요청 처리 가능
  });

  worker.on('error', err => {
    console.error('워커 에러:', err);
  });
} else {
  // 워커 스레드에서 실행
  const result = heavyCpuWork(workerData.input);
  parentPort.postMessage(result);
}
```

**언제 쓰나**: CPU-bound 연산을 메인 스레드와 데이터를 공유하며 병렬로 처리해야 할 때. JSON 파싱, 이미지 리사이징, 암호화 같은 단발성 CPU 작업. 데이터를 복사하지 않고 전달하려면 `transferList`에 `ArrayBuffer`를 넣어 소유권 이전(transfer)을 쓴다.

**주의**: Worker 생성 비용이 적지 않다. 요청마다 새 Worker를 만들면 오버헤드가 크다. 워커 풀을 미리 만들어두는 패턴이 필요하다.

```javascript
// 워커 풀 패턴 (단순화)
const os = require('os');
const { Worker } = require('worker_threads');

class WorkerPool {
  constructor(workerPath, size = os.cpus().length) {
    this.queue = [];
    this.workers = Array.from({ length: size }, () => this.createWorker(workerPath));
  }

  createWorker(path) {
    const worker = new Worker(path);
    worker.on('message', result => {
      worker.busy = false;
      if (this.queue.length > 0) {
        const { data, resolve } = this.queue.shift();
        this.runOnWorker(worker, data, resolve);
      }
    });
    return worker;
  }

  run(data) {
    return new Promise(resolve => {
      const idle = this.workers.find(w => !w.busy);
      if (idle) {
        this.runOnWorker(idle, data, resolve);
      } else {
        this.queue.push({ data, resolve });
      }
    });
  }

  runOnWorker(worker, data, resolve) {
    worker.busy = true;
    worker.once('message', resolve);
    worker.postMessage(data);
  }
}
```

### child_process

별도 Node.js 프로세스를 포크한다. `fork()`로 새 프로세스를 만들어 IPC 채널로 통신하거나, `exec()`·`spawn()`으로 외부 프로그램을 실행할 때 쓴다.

```javascript
const { fork, exec } = require('child_process');

// Node.js 자식 프로세스
const child = fork('./heavy-computation.js');
child.send({ task: 'compute', data: largeArray });
child.on('message', result => {
  console.log('연산 완료:', result);
});

// 외부 프로그램 실행 — 절대로 사용자 입력을 직접 넣지 마라
const { stdout } = await exec('ffmpeg -version');
```

**언제 쓰나**: 외부 바이너리(ffmpeg, ImageMagick, Python 스크립트)를 실행할 때. 자식 프로세스가 크래시해도 메인 프로세스에 영향이 없어야 할 때. 완전히 격리된 환경이 필요할 때.

**주의**: Worker Threads와 달리 메모리를 공유하지 않는다. 데이터를 IPC로 주고받으면 직렬화(JSON) 비용이 발생한다. 큰 데이터를 주고받으면 느리다.

```javascript
// exec에 사용자 입력 그대로 넣으면 명령어 인젝션
// 절대 금지
exec(`ls ${req.query.dir}`); // req.query.dir = '; rm -rf /'

// spawn으로 인자를 분리해서 넘긴다
const { spawn } = require('child_process');
spawn('ls', [req.query.dir]); // 안전
```

### cluster

메인 프로세스(마스터)가 워커 프로세스들을 포크하고 같은 포트로 들어오는 연결을 라운드로빈으로 분산한다. CPU 코어 수만큼 프로세스를 띄워 멀티코어를 활용한다.

```javascript
const cluster = require('cluster');
const http = require('http');
const os = require('os');

if (cluster.isPrimary) {
  const numCPUs = os.cpus().length;
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }

  cluster.on('exit', (worker, code) => {
    console.log(`워커 ${worker.process.pid} 종료 (${code}), 재시작`);
    cluster.fork();
  });
} else {
  http.createServer((req, res) => {
    res.end(`PID: ${process.pid}`);
  }).listen(3000);
}
```

**언제 쓰나**: HTTP 서버를 멀티코어로 수평 확장할 때. 각 워커가 독립적으로 요청을 처리해야 할 때. Kubernetes 환경이라면 cluster 대신 replicas로 처리하는 게 낫다 — 프로세스 관리를 컨테이너 오케스트레이션에 맡기는 게 더 가시성이 좋다.

**주의**: 워커들이 메모리를 공유하지 않는다. 세션, 캐시 같은 상태를 Redis 같은 외부 저장소로 빼야 한다.

### 선택 기준 정리

| 상황 | 선택 |
|---|---|
| CPU-bound 연산, 데이터 공유 필요 | Worker Threads |
| 외부 프로그램 실행 | child_process (spawn/exec) |
| Node.js 서브프로세스, 격리 필요 | child_process (fork) |
| HTTP 서버 멀티코어 확장 | cluster (또는 PM2/K8s replicas) |

---

## Promise.all에서 에러 처리 실수

### 하나만 실패해도 전체가 reject된다

`Promise.all`은 하나라도 reject되면 즉시 reject된다. 나머지 Promise가 완료되길 기다리지 않는다.

```javascript
const results = await Promise.all([
  fetchUser(1),
  fetchUser(2),
  fetchUser(3) // 이게 실패하면
]);
// fetchUser(1), fetchUser(2)가 완료됐어도 results를 못 얻는다
```

이 특성이 문제가 되는 경우는 "가능한 것만 가져오고 싶을 때"다. 예를 들어 외부 API 10개를 호출해서 성공한 결과만 쓰고 싶은데 `Promise.all`을 쓰면 하나만 실패해도 전체를 잃는다.

```javascript
// 잘못된 패턴: 독립적인 요청인데 하나 실패로 전체 실패
const allData = await Promise.all(
  userIds.map(id => fetchUserData(id))
);

// 올바른 패턴: 독립적이면 Promise.allSettled 사용
const settled = await Promise.allSettled(
  userIds.map(id => fetchUserData(id))
);

const successes = settled
  .filter(r => r.status === 'fulfilled')
  .map(r => r.value);

const failures = settled
  .filter(r => r.status === 'rejected')
  .map(r => r.reason);
```

### 에러를 삼키는 패턴

`.catch`를 각 Promise에 달아서 에러를 null로 바꾸면 `Promise.all`이 실패하지 않지만, 어디서 실패했는지 파악이 어려워진다.

```javascript
// 에러를 null로 삼키는 패턴
const results = await Promise.all(
  userIds.map(id => fetchUserData(id).catch(() => null))
);
// results는 [data1, null, data3, ...] 형태
// null이 어느 유저인지 추적하기 어렵다
```

실패를 추적하려면 id와 결과를 같이 반환한다.

```javascript
const results = await Promise.all(
  userIds.map(async id => {
    try {
      const data = await fetchUserData(id);
      return { id, data, error: null };
    } catch (error) {
      return { id, data: null, error };
    }
  })
);

results.forEach(({ id, data, error }) => {
  if (error) {
    console.error(`유저 ${id} 실패:`, error.message);
  }
});
```

### reject 후 나머지 Promise의 side effect

`Promise.all`이 reject되어도 나머지 Promise는 계속 실행된다. Promise는 취소 메커니즘이 없다. 비용이 큰 요청이면 하나 실패한 뒤에도 나머지가 끝까지 실행되어 리소스를 낭비한다.

```javascript
// 첫 번째가 실패해도 두 번째, 세 번째 요청은 계속 진행된다
const [a, b, c] = await Promise.all([
  expensiveApiCall1(), // 실패
  expensiveApiCall2(), // 계속 실행 중
  expensiveApiCall3(), // 계속 실행 중
]);
```

AbortController로 취소 신호를 연결할 수 있다.

```javascript
const controller = new AbortController();
const { signal } = controller;

const promises = [
  fetchWithSignal(url1, signal),
  fetchWithSignal(url2, signal),
  fetchWithSignal(url3, signal),
];

try {
  const results = await Promise.all(promises);
} catch (err) {
  controller.abort(); // 나머지 요청 취소
  throw err;
}
```

### Promise.all vs Promise.allSettled vs Promise.race vs Promise.any

```javascript
// Promise.all: 전부 성공 필요, 하나라도 실패하면 reject
// → 모든 결과가 다 있어야 의미 있을 때 (예: 트랜잭션 묶음)

// Promise.allSettled: 전부 기다리고 성공/실패 각각 알려줌
// → 독립적인 요청의 결과를 모두 수집하고 싶을 때

// Promise.race: 가장 먼저 완료(성공 또는 실패)된 것 반환
// → 타임아웃 구현
const withTimeout = (promise, ms) =>
  Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('timeout')), ms)
    )
  ]);

// Promise.any: 가장 먼저 성공한 것 반환, 전부 실패하면 AggregateError
// → 여러 CDN에서 같은 파일을 요청하고 빠른 것을 쓸 때
const fastest = await Promise.any([
  fetchFromCDN1(url),
  fetchFromCDN2(url),
  fetchFromCDN3(url),
]);
```

---

## 실제로 겪은 블로킹 사례

### Express에서 동기 XML 파싱

레거시 코드에서 `xml2js.parseString`의 동기 버전을 쓰고 있었다. 요청 크기가 작을 때는 괜찮았는데 특정 클라이언트가 3MB XML을 보내기 시작하면서 다른 요청들이 수백ms씩 지연됐다. 이벤트 루프 지연 측정을 도입하고서야 원인을 찾았다. `xml2js.parseStringPromise`로 교체하는 것만으로 해결됐다.

### bcrypt 반복 수 과다

bcrypt의 salt round를 12에서 14로 올렸더니 회원가입 요청 중에 다른 API가 3~5초씩 지연됐다. round 12는 약 250ms, round 14는 약 1초다. 이 1초 동안 이벤트 루프가 멈춘다. bcrypt 자체는 비동기 API를 제공하지만 내부에서 C++ 애드온이 블로킹으로 동작하는 구현도 있다. `bcrypt.hash`의 비동기 버전을 써도 내부 구현을 확인해야 한다.

---

이벤트 루프 기본 구조는 [이벤트 루프](05_이벤트_루프_비동기/Event_Loop.md)에서, async/await 동작 방식은 [Async Await and Promise](05_이벤트_루프_비동기/Async_Await_and_Promise.md)에서 다룬다.
