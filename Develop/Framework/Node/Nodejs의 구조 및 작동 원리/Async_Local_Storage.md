---
title: AsyncLocalStorage (요청 단위 컨텍스트 전파)
tags: [framework, node, nodejs의-구조-및-작동-원리, async-hooks, asynclocalstorage, tracing, logging]
updated: 2026-06-02
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

## 내부에서 어떻게 흐름을 따라가는가

동작 원리를 한 단계 더 파보면 두 가지 메커니즘이 보인다.

첫 번째는 `async_hooks`의 자원 그래프다. Node가 비동기 자원을 만들 때마다 고유한 `asyncId`를 발급하고, 그 자원이 만들어진 시점에 활성화돼 있던 자원의 `asyncId`를 `triggerAsyncId`로 기록한다. Promise, Timeout, TCP 소켓, FS 작업 모두 마찬가지다. 이 두 id로 부모-자식 관계가 만들어진다. `run(store, cb)`은 콜백이 실행되는 동안 활성 자원 위에 저장소를 "스택처럼" 얹어 두는데, 그 안에서 새로 만들어지는 자원들은 같은 저장소를 자기 컨텍스트로 가져간다. 콜백이 끝나면 스택을 pop하면서 원래 상태로 돌아온다.

두 번째는 V8의 continuation preserved embedder data다. Promise가 `await`로 잠시 멈췄다가 마이크로태스크 큐에서 재개될 때, V8은 멈춘 순간의 임베더 데이터(여기서는 ALS 컨텍스트)를 따로 저장해 두고 재개될 때 복원한다. `async_hooks`의 `before/after` 콜백을 거치지 않고 V8 엔진 레벨에서 직접 처리하니까 비용이 훨씬 작다. Node 20부터 ALS가 우선적으로 이 방식을 쓴다.

```js
async function flow() {
  // 컨텍스트 A
  await db.query('...'); // 멈출 때 컨텍스트 A 저장
  // 재개 시 V8이 컨텍스트 A 복원
  await http.get('...'); // 또 저장
  // 또 복원
}
```

이 구조 때문에 `await`가 몇 번을 끼어들어도 컨텍스트가 끊기지 않는다. 반대로 V8이 처리하지 못하는 경로(EventEmitter `emit`, 풀에 보관된 콜백, 네이티브 모듈이 직접 호출하는 콜백)에서는 별도 처리가 필요하고, 그게 뒤에 다룰 컨텍스트 끊김 문제로 이어진다.

자원 그래프 자체는 `executionAsyncId()`, `triggerAsyncId()`로 직접 들여다볼 수 있다.

```js
const asyncHooks = require('node:async_hooks');

setTimeout(() => {
  console.log('exec:', asyncHooks.executionAsyncId());
  console.log('trig:', asyncHooks.triggerAsyncId());
}, 0);
```

이걸 콜백이 끊기는 지점에서 찍어 보면 어떤 흐름이 부모인지 추적할 수 있다. 컨텍스트 누수나 컨텍스트 분실을 디버깅할 때 가끔 쓴다.

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

## 트랜잭션 컨텍스트 전파

DB 트랜잭션을 함수 시그니처에 끌고 다니지 않으려고 ALS를 쓰는 패턴이 자주 보인다. 트랜잭션이 시작되면 같은 트랜잭션의 모든 쿼리는 같은 커넥션에서 돌아야 하는데, 보통 트랜잭션 핸들(`tx`, `client`, `qr` 등)을 인자로 계속 넘긴다. 이걸 ALS로 숨길 수 있다.

```js
const { AsyncLocalStorage } = require('node:async_hooks');
const { Pool } = require('pg');

const pool = new Pool();
const txStorage = new AsyncLocalStorage();

async function withTransaction(fn) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await txStorage.run({ client }, fn);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

// 어디서 부르든 한 함수로 통일
async function query(sql, params) {
  const store = txStorage.getStore();
  if (store?.client) {
    return store.client.query(sql, params); // 트랜잭션 안: 같은 커넥션
  }
  return pool.query(sql, params); // 트랜잭션 밖: 풀에서 임의 커넥션
}

// 사용
await withTransaction(async () => {
  await query('UPDATE accounts SET balance = balance - 100 WHERE id = 1');
  await query('UPDATE accounts SET balance = balance + 100 WHERE id = 2');
});
```

서비스 레이어 함수 시그니처에서 트랜잭션 객체를 들고 다닐 필요가 없어진다. NestJS의 `@Transactional` 데코레이터, TypeORM의 `Transactional` 헬퍼, Prisma의 interactive transaction을 감싼 래퍼들이 거의 다 이런 식으로 동작한다.

문제가 되는 지점이 두 군데 있다.

첫째, 중첩 호출. 한 흐름 안에서 `withTransaction`을 또 부르면 안쪽 `run`이 새 `{ client }`를 심으면서 바깥의 트랜잭션 커넥션을 가린다. 안쪽 `query`는 새 커넥션을 쓰니까 두 트랜잭션이 분리된다. 이게 원하는 동작인 경우는 드물다. 대부분은 안쪽도 바깥 트랜잭션에 합류하거나 SAVEPOINT로 다뤄야 한다.

```js
async function withTransaction(fn) {
  const existing = txStorage.getStore();
  if (existing?.client) {
    // 이미 트랜잭션 안 — SAVEPOINT로 처리
    const sp = `sp_${process.hrtime.bigint()}`;
    await existing.client.query(`SAVEPOINT ${sp}`);
    try {
      const result = await fn();
      await existing.client.query(`RELEASE SAVEPOINT ${sp}`);
      return result;
    } catch (err) {
      await existing.client.query(`ROLLBACK TO ${sp}`);
      throw err;
    }
    return;
  }
  // 새 트랜잭션 (위와 동일)
  ...
}
```

둘째, after-commit 콜백. 트랜잭션 안에서 "커밋 끝나면 캐시 무효화", "이벤트 발행" 같은 작업을 예약하는 패턴을 자주 본다. 콜백을 배열에 모아 뒀다가 `COMMIT` 뒤에 실행하는데, `COMMIT`이 끝나면 `run` 콜백을 빠져나오기 직전이라 컨텍스트가 살아 있다. 단, 그 콜백 안에서 다시 `query`를 부르면 트랜잭션 커넥션이 이미 release된 상태라 풀에서 새 커넥션을 받아 실행된다. 의도와 다르게 동작하기 쉽다. 차라리 트랜잭션 끝난 뒤 별도의 `run` 없이 명시적으로 부르는 게 안전하다.

세번째 함정도 있다. 트랜잭션 안에서 `setImmediate`나 `process.nextTick`으로 작업을 떼어 내면 그 작업도 같은 컨텍스트라 같은 트랜잭션 커넥션을 본다. 하지만 그 작업이 `COMMIT` 뒤에 실행되면 release된 커넥션을 건드린다. 이 버그는 로그도 안 남으니 추적이 까다롭다. 트랜잭션 안에서는 "이 흐름이 끝나기 전에 완료될 작업"만 돌리는 걸 원칙으로 한다.

## 유저 ID와 권한 컨텍스트 전파

멀티 테넌트 API에서 가장 위험한 버그는 "엉뚱한 테넌트 데이터를 본다"이다. 모든 쿼리에 `WHERE tenant_id = ?` 조건이 들어가야 하는데, 한 군데라도 빠지면 데이터가 새거나 다른 테넌트 데이터를 덮어쓴다. 매 함수에 `userId`/`tenantId`를 인자로 받게 만들면 빠뜨릴 위험이 있고, 시그니처도 망가진다. ALS에 인증된 유저 정보를 심어 두면 DAO에서 한 줄로 꺼내 쓸 수 있다.

```js
const userContext = new AsyncLocalStorage();

function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const user = verifyToken(token); // { id, tenantId, roles }
  userContext.run({ user }, () => next());
}

function getCurrentUser() {
  const store = userContext.getStore();
  if (!store?.user) {
    throw new Error('NO_USER_CONTEXT');
  }
  return store.user;
}

// Repository 레이어
async function findOrders() {
  const user = getCurrentUser();
  return db.query(
    'SELECT * FROM orders WHERE tenant_id = $1',
    [user.tenantId],
  );
}
```

이 패턴의 가장 큰 함정은 컨텍스트 없이 도는 경로다. 배치 잡, 스케줄러, 메시지 큐 컨슈머는 HTTP 미들웨어를 거치지 않으니까 `userContext.run`이 한 번도 안 불린 상태에서 `findOrders` 같은 함수를 부른다. 이때 `getCurrentUser`가 그냥 `null`을 돌려주는 구현이면, `WHERE tenant_id = $1`에 `null`이 들어가서 한 줄도 안 나오거나(다행) `WHERE` 조건 자체를 빼버린 코드면 모든 테넌트 데이터를 뽑아낸다(재앙).

방어선을 두 군데 만든다.

첫째, `getCurrentUser`는 컨텍스트가 없을 때 무조건 던진다. `null` 같은 부드러운 기본값을 주면 안 된다. 던지면 배치 잡 진입점에서 못 부르고 깨지니까 누구라도 알아챈다.

둘째, 시스템 진입점에서 명시적으로 시스템 컨텍스트를 만들어 감싼다.

```js
async function runDailyReport() {
  const systemUser = { id: 'system', tenantId: null, roles: ['system'] };
  await userContext.run({ user: systemUser }, async () => {
    for (const tenant of await loadTenants()) {
      await userContext.run(
        { user: { ...systemUser, tenantId: tenant.id } },
        () => generateReport(tenant),
      );
    }
  });
}
```

테넌트별로 `run`을 다시 부르면 안쪽 흐름은 안쪽 저장소를 본다. 바깥 `for` 루프는 매 반복에서 새 `run`을 시작하니까 테넌트가 섞이지 않는다.

권한 체크 헬퍼도 같은 컨텍스트에서 꺼낸다.

```js
function requireRole(role) {
  const user = getCurrentUser();
  if (!user.roles.includes(role)) {
    const err = new Error('FORBIDDEN');
    err.status = 403;
    throw err;
  }
}

async function deleteOrder(orderId) {
  requireRole('admin');
  await query('DELETE FROM orders WHERE id = $1 AND tenant_id = $2', [
    orderId,
    getCurrentUser().tenantId,
  ]);
}
```

ALS에 `tenantId` 같은 보안 결정에 쓰이는 값을 넣을 때 한 가지 더 신경 쓸 게 있다. 값을 절대 도중에 바꾸지 않는다. `store.set('tenantId', ...)`로 흐름 중간에 테넌트를 갈아치우는 코드를 만들면, 그 시점 이전에 시작된 비동기 작업과 이후에 시작된 작업이 다른 값을 보면서 권한 경계가 흐려진다. 새 테넌트로 전환해야 한다면 새 `run` 블록을 연다.

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

### 버전별 체감 차이

같은 코드를 Node 16, 18, 20, 22에서 돌려 보면 차이가 분명하다. Node 16/18에서는 ALS 인스턴스를 단 하나만 켜놓아도 `Promise.resolve().then()` 같은 짧은 마이크로태스크가 20~40% 느려지는 게 흔하다. EventEmitter가 많은 코드, fs 작업이 많은 코드는 더 크게 영향을 받는다. Node 20에서는 V8 continuation preserved embedder data로 갈아탄 덕에 마이크로태스크 오버헤드가 한 자릿수 %로 떨어졌고, Node 22 LTS에서는 측정 노이즈와 구분이 어려운 수준이 됐다.

실제로 발목 잡는 건 ALS 자체가 아니라 `async_hooks` 자원 추적이 켜진 상태에서 도는 부수 비용이다. 이게 켜지는 조건은 다음 중 하나라도 해당될 때다.

- 직접 `createHook()`으로 훅을 만들고 `.enable()`한 모듈이 있다(APM, 디버거 등).
- 오래된 Node에서 ALS 인스턴스를 만들었다(Node 18 이하는 ALS가 자체적으로 훅을 켠다).
- 컨텍스트 전파가 필요한 자원(EventEmitter `emit` 같은 V8 미지원 경로)을 위해 일부 추적이 켜져 있다.

이 비용은 Promise 생성마다 무시 못할 정도로 붙는다. 핫 패스에서 마이크로벤치를 돌렸을 때 `await Promise.resolve()` 1억 번이 ALS 없이 1.2초 걸리던 게, Node 18에서 ALS 켰을 때 1.9초, Node 22에서는 1.3초 정도로 측정되는 식이다(시스템에 따라 다르다). 일반 웹 서버 요청 처리는 이 단위로 묶이지 않으니 신경 쓸 일이 거의 없다.

### 무거운 저장소가 만드는 비용

ALS 자체의 성능 외에 한 가지 더. 저장소 객체가 무거우면 그 객체가 비동기 자원이 살아 있는 동안 계속 GC에 잡히지 않는다. 1MB짜리 객체를 통째로 넣어 두고 요청이 30초 걸리면, 그 30초 동안 1MB가 메모리에 떠 있다. 초당 1000 요청이면 30GB가 떠 있는 셈이다. ALS에는 작은 메타데이터(id, 이름, 권한 같은)만 넣는다.

## 흔히 만나는 버그 패턴

실무에서 ALS를 쓰다가 자주 만나는 버그를 모아 둔다. 한 번씩 다 겪는 것들이다.

**같은 클래스를 두 번 new**. 라이브러리 코드에서 한 번, 애플리케이션 코드에서 한 번 `new AsyncLocalStorage()`를 만들면 서로 다른 인스턴스다. 한쪽에서 `run`으로 심고 다른 쪽에서 `getStore()`를 부르면 `undefined`다. 인스턴스를 export하는 단일 모듈을 만들고 모두 거기서 import하게 강제한다. 모노레포라면 워크스페이스 단위로 `node:async_hooks`를 두 번 import하지 않도록 신경 쓴다.

**`reqId`가 일부 로그에서만 빠진다**. 대부분 두 가지 중 하나다. 인스턴스를 두 번 만든 경우거나, 부팅/스케줄러 같이 컨텍스트 밖에서 도는 코드가 같은 로거를 부르는 경우다. 로그에 `reqId`가 늘 있어야 한다고 가정하지 말고, `getStore()?.reqId ?? 'system'`처럼 기본값을 넣어 둔다.

**테스트에서 컨텍스트 누수**. 한 테스트에서 `enterWith`로 심은 컨텍스트가 다음 테스트로 새어 나간다. 테스트 러너가 await로 이어지면 같은 흐름이라 저장소가 살아 있다. 테스트는 무조건 `run`으로 감싸거나, 테스트 헬퍼에서 새로 `run`을 열어 그 안에서 본문을 실행한다.

```js
function runInContext(fn) {
  return als.run(new Map(), fn);
}

it('finds user', () =>
  runInContext(async () => {
    als.getStore().set('reqId', 'test-1');
    ...
  }));
```

**`new Promise` 직접 만들 때**. `new Promise((resolve) => { ... })`로 만들고 그 resolve를 외부 콜백(예: 외부 라이브러리의 이벤트)에서 호출하는 코드가 있다. resolve가 호출되는 흐름이 `new Promise`를 만든 흐름과 다르면 then 뒤로 컨텍스트가 안 따라간다. 이런 케이스는 `AsyncResource.bind`로 resolve를 감싸 등록한다.

```js
const { AsyncResource } = require('node:async_hooks');

function fromEvent(emitter, name) {
  return new Promise((resolve) => {
    emitter.once(name, AsyncResource.bind(resolve));
  });
}
```

**재귀적 `run` 호출**. `run` 안에서 다시 `run`을 부르면 안쪽 콜백이 도는 동안은 안쪽 저장소를 본다. 콜백이 끝나면 다시 바깥 저장소로 돌아온다. 의도한 동작이지만, 둘이 같은 저장소라고 가정한 코드는 깨진다. 트랜잭션 중첩 같은 데서 자주 헷갈린다.

**Worker Thread로 옮길 때**. 워커는 별도의 V8 isolate에서 도니까 ALS 저장소가 따라가지 않는다. 메인 스레드에서 워커로 작업을 넘길 때 `postMessage` 페이로드에 필요한 컨텍스트 값을 명시적으로 실어 보내고, 워커 쪽에서 받아서 다시 `run`으로 감싼다. 자식 프로세스도 똑같다.

**메시지 큐 컨슈머**. Redis, RabbitMQ, Kafka 컨슈머가 메시지를 받을 때 ALS는 비어 있다. 메시지 헤더에 `reqId`(또는 `traceId`)를 실어 보내고, 컨슈머 진입점에서 그 값으로 `run`을 연다. 분산 환경에서 컨텍스트를 이어가려면 결국 경계마다 명시적으로 주입해야 한다.

```js
async function handleMessage(msg) {
  const reqId = msg.headers['x-request-id'] || randomUUID();
  await als.run(new Map([['reqId', reqId]]), () => processMessage(msg));
}
```

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

`AsyncLocalStorage`는 어디까지나 "같은 Node 프로세스, 같은 비동기 흐름" 안에서만 유효하다. 워커 스레드 경계, 자식 프로세스, 메시지 큐를 건너가면 저장소는 따라가지 않는다. 그런 경계를 넘을 때는 `reqId`를 메시지 페이로드나 헤더에 명시적으로 실어 보내고, 받는 쪽에서 다시 `run`으로 심어야 한다.

운영 환경에서 ALS를 처음 도입할 때는 한 번에 모든 곳을 바꾸지 말고, 진입점 한 곳에서 `run`으로 감싸 컨텍스트만 심어 두는 단계부터 시작한다. 그 다음 단계로 로거를 컨텍스트 인지형으로 바꾸고, 마지막에 트랜잭션이나 권한 같은 보안 관련 코드를 옮긴다. 보안과 데이터 격리가 걸린 부분을 가장 먼저 옮기면 컨텍스트가 끊기는 자리를 못 찾았을 때 사고가 크다. 로깅이 먼저 깨지는 게 훨씬 발견하기 쉽고 회복도 빠르다.

마지막으로, ALS가 만능 도구는 아니라는 점도 기억한다. 함수 인자로 명시적으로 넘기는 게 더 적합한 경우도 많다. 단일 함수 안에서만 쓰이는 값, 호출 그래프가 얕고 명시성이 더 중요한 코어 도메인 로직, 정적 타입으로 컴파일 타임에 검증하고 싶은 값은 인자로 넘기는 편이 낫다. ALS는 "값을 모든 레이어에 끌고 다니기 싫지만 모든 레이어에서 읽을 수는 있어야 하는" 횡단 관심사(로깅, 추적, 트랜잭션, 권한)에 어울리는 도구다.
