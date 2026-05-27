---
title: AsyncLocalStorage (요청 단위 컨텍스트 전파)
tags: [framework, node, nodejs의-구조-및-작동-원리, async-hooks, asynclocalstorage, tracing, logging]
updated: 2026-05-27
---

# AsyncLocalStorage (요청 단위 컨텍스트 전파)

## 어떤 문제를 푸는가

웹 서버에서 로그를 찍을 때 가장 답답한 게 "이 로그가 어떤 요청에서 나온 거냐"를 알 수 없다는 점이다. 동시 요청이 100개 들어오면 로그가 뒤섞인다. 그래서 요청마다 `request-id`를 발급하고 그 요청에서 나오는 모든 로그에 같은 id를 붙이고 싶어진다.

가장 단순한 방법은 id를 인자로 계속 넘기는 것이다.

```js
async function handleRequest(reqId, body) {
  const user = await findUser(reqId, body.userId);
  await saveOrder(reqId, user, body.items);
}

async function findUser(reqId, userId) {
  logger.info(reqId, 'user 조회', userId);
  const u = await db.query(reqId, 'SELECT ...');
  return u;
}
```

함수 하나에 `reqId`가 다 끼어든다. 비즈니스 로직과 아무 상관없는 인자가 시그니처를 오염시키고, 한 군데라도 안 넘기면 그 아래로는 전부 끊긴다. DAO, 유틸 함수, 외부 라이브러리 호출까지 전부 `reqId`를 받게 만들 수는 없다.

Java 진영에서는 이걸 `ThreadLocal`로 푼다. 스레드마다 별도 저장소를 두고 같은 스레드 안에서는 어디서든 꺼내 쓴다. 그런데 Node.js는 단일 스레드에서 수많은 요청을 비동기로 번갈아 처리하니까 "스레드 = 요청"이 성립하지 않는다. 한 스레드 위에서 요청 A의 콜백과 요청 B의 콜백이 계속 교대로 실행된다. 스레드 기준으로 저장하면 A 값을 B가 덮어쓴다.

`AsyncLocalStorage`는 스레드 대신 "비동기 실행 흐름" 단위로 저장소를 묶는다. `await`로 함수가 잠시 멈췄다가 다시 깨어나도, `setTimeout` 콜백 안으로 들어가도, 같은 흐름에서 시작된 코드라면 같은 저장소를 본다.

## async_hooks와의 관계

`AsyncLocalStorage`는 `node:async_hooks` 모듈에 들어 있다.

```js
const { AsyncLocalStorage } = require('node:async_hooks');
```

이름이 같은 모듈에 있는 이유가 있다. 내부 구현이 `async_hooks`의 비동기 자원 추적에 기대고 있기 때문이다. `async_hooks`는 Node가 비동기 자원(Promise, Timeout, TCP 소켓 등)을 만들 때마다 `init`, `before`, `after`, `destroy` 콜백을 걸 수 있게 해주는 저수준 API다. 자원이 생길 때 부모-자식 관계를 추적할 수 있어서, "지금 실행 중인 콜백이 어느 흐름에서 파생됐는지"를 알 수 있다.

`AsyncLocalStorage`는 이 추적 위에서 동작한다. `run()`으로 저장소를 심으면, 그 안에서 만들어지는 모든 비동기 자원에 같은 저장소가 따라붙는다. 그래서 `await` 뒤에서도, 콜백 안에서도 `getStore()`가 같은 값을 돌려준다.

`async_hooks` 자체를 직접 쓸 일은 거의 없다. API가 까다롭고, 잘못 쓰면 무한 루프나 성능 저하를 만들기 쉽다. 컨텍스트 전파가 목적이라면 `AsyncLocalStorage`만 쓰면 된다. `async_hooks`의 `createHook`은 디버깅 도구나 APM 라이브러리를 직접 만들 때나 손대는 영역이다.

한 가지 알아둘 점은, 구버전 Node에서는 `AsyncLocalStorage`가 켜지면 `async_hooks` 추적이 전역으로 활성화돼서 모든 비동기 연산에 약간의 비용이 붙었다는 것이다. Node 20 이후로는 V8의 컨텍스트 보존 기능을 쓰는 더 가벼운 구현으로 옮겨가는 중이라 오버헤드가 많이 줄었다. (성능 측정은 아래에서 다룬다.)

## run과 getStore

기본 사용법은 두 메서드면 끝난다. `run(store, callback)`으로 저장소를 심고 콜백을 실행하면, 콜백 안 어디서든 `getStore()`로 그 저장소를 꺼낸다.

```js
const { AsyncLocalStorage } = require('node:async_hooks');

const als = new AsyncLocalStorage();

function logWithId(msg) {
  const store = als.getStore();
  const reqId = store ? store.reqId : 'no-context';
  console.log(`[${reqId}] ${msg}`);
}

als.run({ reqId: 'abc-123' }, () => {
  logWithId('시작');
  setTimeout(() => {
    logWithId('타이머 콜백'); // 여기서도 abc-123이 나온다
  }, 100);
});

logWithId('run 밖'); // no-context
```

`run` 콜백 밖에서 `getStore()`를 부르면 `undefined`가 나온다. 저장소는 그 흐름 안에서만 살아 있다. 위 예제에서 `setTimeout` 콜백은 100ms 뒤 이벤트 루프에서 별도로 실행되는데도 `abc-123`을 본다. 그 타이머가 `run` 안에서 만들어졌기 때문에 저장소가 따라붙은 것이다.

저장소로는 보통 객체나 `Map`을 쓴다. `Map`을 쓰면 흐름 도중에 값을 추가하기 편하다.

```js
als.run(new Map(), () => {
  const store = als.getStore();
  store.set('reqId', 'abc-123');
  store.set('userId', 42);
  // 나중에 다른 함수에서
  store.set('orderId', 9001); // 같은 흐름이면 누적된다
});
```

`run`은 콜백의 반환값을 그대로 돌려준다. async 함수도 넘길 수 있다.

```js
const result = await als.run(store, async () => {
  return await handleRequest();
});
```

저장소는 흐름마다 독립이다. `run`을 동시에 여러 번 호출해도 서로 섞이지 않는다. 이게 `ThreadLocal`과 다른 핵심이다.

```js
als.run({ reqId: 'A' }, async () => {
  await delay(10);
  console.log(als.getStore().reqId); // A
});

als.run({ reqId: 'B' }, async () => {
  await delay(5);
  console.log(als.getStore().reqId); // B
});
// 출력: B, A — 두 흐름이 교차 실행돼도 각자 자기 값을 본다
```

## enterWith과 exit

`run`은 콜백으로 범위를 감싼다. 그런데 미들웨어 같은 데서는 "이 시점부터 끝까지"를 콜백으로 감싸기 애매할 때가 있다. 그럴 때 `enterWith(store)`를 쓴다. 콜백 없이 현재 실행 흐름에 저장소를 심고, 그 흐름이 끝날 때까지 유지된다.

```js
function middleware(req, res, next) {
  als.enterWith({ reqId: req.headers['x-request-id'] });
  next(); // 이 뒤로 이어지는 모든 비동기 작업이 저장소를 본다
}
```

편해 보이지만 `enterWith`는 주의해서 써야 한다. `run`은 콜백이 끝나면 저장소가 자동으로 사라지지만, `enterWith`는 명시적 경계가 없다. 현재 비동기 흐름이 살아 있는 동안 계속 유지되고, 같은 흐름에서 파생된 다른 코드로 값이 새어 나갈 수 있다. 특히 흐름이 깔끔하게 끝나지 않는 위치(예: 이벤트 루프의 상위 틱)에서 호출하면 의도치 않게 다음 작업까지 같은 저장소를 보게 되는 경우가 있다. Node 문서도 `enterWith`를 "사용에 주의가 필요한" 메서드로 표시한다.

실무에서는 `run`으로 감쌀 수 있으면 무조건 `run`을 쓴다. Express처럼 미들웨어가 `next()` 콜백 구조라면 `run` 안에서 `next`를 호출하는 식으로 감쌀 수 있다.

```js
function middleware(req, res, next) {
  als.run({ reqId: req.headers['x-request-id'] }, () => {
    next();
  });
}
```

`exit(callback)`은 반대로 저장소 밖에서 콜백을 실행한다. 컨텍스트를 잠깐 벗어나야 하는 드문 상황에 쓴다.

```js
als.run(store, () => {
  als.exit(() => {
    console.log(als.getStore()); // undefined — 저장소 밖
  });
});
```

`disable()`은 인스턴스를 완전히 끈다. 한 번 끄면 진행 중이던 흐름의 저장소까지 다 사라지므로, 보통 테스트 정리 용도 외에는 쓸 일이 없다.

## request-id를 로깅에 자동 주입하기

가장 흔한 용도다. 요청 진입점에서 `run`으로 id를 심어 두고, 로거가 매번 `getStore()`로 id를 꺼내 붙이게 만든다.

```js
const { AsyncLocalStorage } = require('node:async_hooks');
const { randomUUID } = require('node:crypto');

const als = new AsyncLocalStorage();

// 어디서든 import해서 쓰는 컨텍스트 헬퍼
function getReqId() {
  return als.getStore()?.reqId;
}

// 로거 래퍼
const logger = {
  info(msg, meta = {}) {
    console.log(JSON.stringify({
      level: 'info',
      reqId: getReqId() ?? null,
      msg,
      ...meta,
      time: new Date().toISOString(),
    }));
  },
};

module.exports = { als, getReqId, logger };
```

이제 비즈니스 로직 어디서 `logger.info('...')`를 불러도 `reqId`가 자동으로 붙는다. 함수 시그니처에 id를 넘길 필요가 없다.

```js
async function findUser(userId) {
  logger.info('user 조회', { userId }); // reqId 자동 포함
  return db.query('SELECT ...');
}
```

이게 가장 큰 이점이다. 로깅뿐 아니라 외부 시스템으로 나가는 트레이싱에도 똑같이 쓴다. 분산 트레이싱에서 `trace-id`를 상류 서비스에서 받아 저장소에 넣어 두면, 하류 서비스로 HTTP 요청을 보낼 때 헤더에 같은 `trace-id`를 자동으로 실어 보낼 수 있다.

```js
const axios = require('axios');

async function callDownstream(url) {
  const traceId = als.getStore()?.traceId;
  return axios.get(url, {
    headers: traceId ? { 'x-trace-id': traceId } : {},
  });
}
```

OpenTelemetry 같은 APM 라이브러리도 내부적으로 `AsyncLocalStorage`(또는 비슷한 컨텍스트 매니저)로 스팬 컨텍스트를 전파한다. 직접 트레이싱을 깔지 않더라도 원리는 같다.

## 컨텍스트가 끊기는 지점들

`AsyncLocalStorage`를 쓰다가 "분명 `run` 안에서 호출했는데 `getStore()`가 `undefined`로 나온다"는 상황을 만나면 거의 다음 세 경우 중 하나다.

### EventEmitter 리스너

이게 가장 자주 걸린다. 리스너를 등록한 시점과 이벤트가 발생(`emit`)하는 시점의 흐름이 다르면, 리스너는 `emit`이 일어난 흐름의 저장소를 본다. 등록 시점의 저장소가 아니다.

```js
const { EventEmitter } = require('node:events');
const bus = new EventEmitter(); // 요청들이 공유하는 emitter

// 요청 A 흐름 안에서 리스너 등록
als.run({ reqId: 'A' }, () => {
  bus.on('done', () => {
    console.log(als.getStore()?.reqId); // A를 기대하지만...
  });
});

// 다른 흐름에서 emit
als.run({ reqId: 'B' }, () => {
  bus.emit('done'); // 리스너는 B를 본다 (또는 컨텍스트 밖이면 undefined)
});
```

`emit`은 동기로 리스너를 호출하므로, 리스너는 호출되는 순간의 활성 저장소를 본다. 등록 시점 저장소를 유지하려면 등록할 함수를 `AsyncResource.bind`로 감싸 그 순간의 컨텍스트를 스냅샷해야 한다.

```js
const { AsyncResource } = require('node:async_hooks');

als.run({ reqId: 'A' }, () => {
  // bind가 호출된 시점(A)의 컨텍스트를 함수에 묶는다
  const bound = AsyncResource.bind(() => {
    console.log(als.getStore()?.reqId); // 항상 A
  });
  bus.on('done', bound);
});
```

`AsyncResource.bind`는 함수에 현재 비동기 컨텍스트를 고정한다. 이벤트 핸들러, 콜백 큐에 넣는 함수, 커넥션 풀에 등록하는 콜백처럼 "나중에, 다른 흐름에서 호출될 함수"에 컨텍스트를 들고 가야 할 때 쓴다.

### 커넥션 풀과 재사용되는 객체

DB 드라이버나 HTTP keep-alive 클라이언트는 소켓을 풀에 담아 재사용한다. 이 소켓은 어떤 요청보다도 먼저, 서버 부팅 시점에 만들어졌을 수 있다. 소켓이 만들어진 흐름과 요청 흐름이 다르니, 풀에서 꺼낸 소켓의 내부 콜백은 요청의 저장소를 못 볼 때가 있다.

대부분의 메이저 드라이버(`pg`, `mysql2` 등)는 사용자 콜백/프로미스를 호출할 때 호출 시점의 컨텍스트를 유지하도록 동작하므로, `await db.query(...)` 뒤에서 `getStore()`는 보통 잘 나온다. 문제가 되는 건 드라이버가 내부적으로 영구 소켓의 `data` 이벤트 등에 직접 건 콜백 정도다. 직접 풀이나 커넥션 관리 코드를 짠다면, 콜백을 풀에 넣기 전에 `AsyncResource.bind`로 감싸는 걸 고려해야 한다.

### 스트림 경계와 수동 콜백 큐

스트림 파이프라인 도중에 컨텍스트가 끊기는 경우도 비슷한 원리다. 스트림 인스턴스가 `run` 밖에서 만들어졌고, `data`/`end` 핸들러를 그 스트림에 거는 흐름이 요청 흐름과 다르면 저장소를 놓친다. 직접 콜백 배열에 함수를 쌓아 두고 나중에 꺼내 호출하는 코드(자체 작업 큐, 배치 처리기)도 같은 함정을 갖는다. 해법은 동일하다. 나중에 실행될 함수를 큐에 넣기 전에 `AsyncResource.bind`로 컨텍스트를 묶는다.

정리하면 규칙은 하나다. 함수를 "지금 이 흐름에서 정의하지만 나중에 다른 흐름에서 호출"한다면 컨텍스트가 끊길 수 있고, `AsyncResource.bind`로 막는다. `await`, `then`, `setTimeout`, `setImmediate`, `process.nextTick`처럼 흐름이 자연스럽게 이어지는 비동기는 자동으로 전파되니 손댈 필요가 없다.

## 성능 오버헤드 측정

`AsyncLocalStorage`가 공짜는 아니다. 비동기 자원이 생길 때마다 컨텍스트를 따라붙이는 작업이 들어간다. 얼마나 느려지는지는 직접 재는 게 맞다. 환경마다 다르고 Node 버전에 따라 크게 달라졌다.

간단한 벤치마크는 이렇게 짠다.

```js
const { AsyncLocalStorage } = require('node:async_hooks');
const als = new AsyncLocalStorage();

const N = 1_000_000;

function delay() {
  return new Promise((r) => setImmediate(r));
}

async function withoutALS() {
  const start = process.hrtime.bigint();
  for (let i = 0; i < N; i++) await delay();
  return Number(process.hrtime.bigint() - start) / 1e6;
}

async function withALS() {
  const start = process.hrtime.bigint();
  for (let i = 0; i < N; i++) {
    await als.run({ reqId: i }, async () => {
      await delay();
    });
  }
  return Number(process.hrtime.bigint() - start) / 1e6;
}

(async () => {
  await withoutALS(); // 워밍업
  console.log('without:', (await withoutALS()).toFixed(0), 'ms');
  console.log('with   :', (await withALS()).toFixed(0), 'ms');
})();
```

직접 돌려 보면 두 가지를 확인할 수 있다. 첫째, `run` 자체의 비용보다 "`AsyncLocalStorage` 인스턴스가 하나라도 활성화돼 있으면 그 프로세스의 모든 비동기 연산이 조금씩 느려지는" 비용이 더 크다. 구버전 Node에서는 이 전역 비용 때문에 비동기를 많이 쓰는 워크로드에서 수십 % 느려지는 경우도 있었다. 둘째, Node 20 이후의 새 구현에서는 이 전역 비용이 많이 줄어서, 일반적인 웹 서버처럼 요청당 수 ms 단위 작업이 도는 환경에서는 사실상 측정 오차 수준으로 묻힌다.

실무 판단은 이렇게 한다. 요청당 한 번 `run`으로 감싸고 컨텍스트를 읽고 쓰는 정도라면 오버헤드를 걱정할 필요가 없다. 그 정도 비용보다 `reqId`를 모든 함수에 손으로 넘기다가 빠뜨리는 비용이 훨씬 크다. 반대로 초당 수십만 건씩 짧은 비동기를 돌리는 핫 패스(예: 고성능 프록시 내부 루프)라면, 활성 인스턴스 개수를 최소화하고 실제 환경에서 측정한 뒤 결정한다. 인스턴스는 애플리케이션당 하나만 두고 모듈로 공유하는 게 좋다. 여러 개를 켤수록 전역 추적 비용이 누적된다.

## Express 미들웨어 연동

요청 진입점에서 `run`으로 감싸는 미들웨어를 맨 앞에 둔다. 그 뒤로 등록되는 모든 미들웨어와 라우트 핸들러가 같은 저장소를 공유한다.

```js
const express = require('express');
const { AsyncLocalStorage } = require('node:async_hooks');
const { randomUUID } = require('node:crypto');

const als = new AsyncLocalStorage();
const app = express();

// 가장 앞에 둔다
app.use((req, res, next) => {
  const reqId = req.headers['x-request-id'] || randomUUID();
  const store = new Map();
  store.set('reqId', reqId);
  res.setHeader('x-request-id', reqId); // 응답에도 실어 준다

  als.run(store, () => next());
});

app.get('/users/:id', async (req, res) => {
  const user = await findUser(req.params.id); // 내부에서 logger가 reqId를 본다
  res.json(user);
});

async function findUser(id) {
  const reqId = als.getStore()?.get('reqId');
  console.log(`[${reqId}] findUser ${id}`);
  return { id };
}

app.listen(3000);
```

핵심은 `als.run(store, () => next())` 형태로 `next`를 `run` 안에서 부르는 것이다. 이렇게 하면 이후 미들웨어 체인 전체가 `run` 콜백의 비동기 흐름 안에 들어간다. `enterWith`를 써도 동작은 하지만, 위에 적은 이유로 `run`을 권한다.

에러 핸들러도 같은 흐름에 들어오므로, 에러 로그에도 `reqId`가 자동으로 붙는다.

```js
app.use((err, req, res, next) => {
  const reqId = als.getStore()?.get('reqId');
  console.error(`[${reqId}] 처리 실패:`, err.message);
  res.status(500).json({ error: 'internal', reqId });
});
```

## Fastify 연동

Fastify는 `onRequest` 훅에서 감싸는데, 훅 함수의 구조 때문에 Express와 약간 다르다. Fastify의 라이프사이클 훅은 `done` 콜백이나 async 반환으로 다음 단계로 넘어간다. 훅 안에서 `run`으로 감싸도 그 콜백이 끝나면 Fastify는 별도 흐름에서 다음 단계를 호출하기 때문에, `onRequest` 훅에서는 `enterWith`를 쓰는 게 실용적이다.

```js
const fastify = require('fastify')();
const { AsyncLocalStorage } = require('node:async_hooks');
const { randomUUID } = require('node:crypto');

const als = new AsyncLocalStorage();

fastify.addHook('onRequest', (req, reply, done) => {
  const reqId = req.headers['x-request-id'] || randomUUID();
  als.enterWith(new Map([['reqId', reqId]]));
  done();
});

fastify.get('/users/:id', async (req) => {
  const reqId = als.getStore()?.get('reqId');
  req.log.info({ reqId }, 'findUser');
  return { id: req.params.id };
});

fastify.listen({ port: 3000 });
```

Fastify 5는 요청 라이프사이클 전반에서 `AsyncLocalStorage` 전파가 안정적으로 동작하도록 신경 써서 만들어졌고, 공식 문서도 `onRequest`에서 `enterWith`로 컨텍스트를 심는 방식을 안내한다. 다만 Fastify는 이미 `req.id`를 발급하고 자체 `req.log`에 그 id를 붙여 준다. 단순히 요청 로그에 id가 필요한 정도라면 `req.log`를 그대로 쓰면 되고, `AsyncLocalStorage`는 `req` 객체에 접근할 수 없는 깊은 곳(공용 유틸, DAO)에서 id가 필요할 때 의미가 있다.

직접 컨텍스트를 만들기보다 검증된 플러그인을 쓰는 방법도 있다. `@fastify/request-context`가 내부적으로 `AsyncLocalStorage`를 써서 같은 일을 해 준다. 직접 인스턴스를 관리하기 싫으면 이쪽을 쓴다.

## 운영에서 챙겨야 할 것

인스턴스는 애플리케이션당 하나만 만들어 모듈로 공유한다. 파일마다 `new AsyncLocalStorage()`를 만들면 서로 다른 저장소가 돼서 `getStore()`가 엉뚱한 값을 돌려준다. 전역 추적 비용도 인스턴스 수만큼 늘어난다.

저장소에 무거운 객체를 통째로 넣지 않는다. 요청 흐름이 살아 있는 동안 저장소도 살아 있으니, 큰 버퍼나 DB 결과 전체를 넣어 두면 그만큼 메모리를 오래 잡는다. id나 작은 메타데이터 정도만 넣는다.

`getStore()`가 `undefined`일 수 있다는 걸 항상 가정한다. 헬스체크, 스케줄러, 부팅 시 실행되는 초기화 코드는 `run` 밖에서 도니까 저장소가 없다. `als.getStore()?.get('reqId') ?? 'system'`처럼 기본값을 두지 않으면 그런 경로에서 터진다.

테스트에서 `AsyncLocalStorage`를 쓰는 코드를 단위 테스트할 때는 `als.run(테스트용_store, () => 테스트본문())`으로 감싸 주거나, `getStore()`가 `undefined`여도 동작하도록 헬퍼에 기본값을 둔다. 감싸지 않으면 컨텍스트 의존 코드가 테스트에서만 다르게 동작해서 디버깅이 어려워진다.

마지막으로, `AsyncLocalStorage`는 어디까지나 "같은 Node 프로세스, 같은 비동기 흐름" 안에서만 유효하다. 워커 스레드 경계, 자식 프로세스, 메시지 큐를 건너가면 저장소는 따라가지 않는다. 그런 경계를 넘을 때는 `reqId`를 메시지 페이로드나 헤더에 명시적으로 실어 보내고, 받는 쪽에서 다시 `run`으로 심어야 한다.
