---
title: 백엔드 실무에서 클로저를 설계 도구로 쓰는 패턴
tags: [language, javascript, closure, nodejs, dependency-injection, currying, factory]
updated: 2026-06-15
---

# 백엔드 실무에서 클로저를 설계 도구로 쓰는 패턴

클로저가 무엇인지, 렉시컬 스코프가 어떻게 동작하는지는 같은 디렉토리의 다른 문서에서 다룬다. 여기서는 그 메커니즘을 알고 있다는 전제 아래, Node.js 백엔드 코드에서 클로저를 **의도적으로 설계 수단으로 쓰는** 경우를 정리한다. 클로저를 "어쩌다 외부 변수를 참조하게 된 함수"가 아니라 "설정과 의존성을 미리 박아둔 함수를 찍어내는 틀"로 쓰는 쪽이다.

실무에서 클로저를 쓰는 동기는 대부분 하나로 모인다. 어떤 값을 함수가 호출될 때마다 인자로 넘기기 싫고, 그렇다고 전역에 두기도 싫을 때다. 설정값, DB 커넥션, 로거 같은 것들. 이걸 함수가 만들어지는 시점에 한 번 바인딩해두면 호출부가 깨끗해진다. 대신 대가가 있는데, 함수 인스턴스마다 환경이 따로 잡힌다는 점이다. 이 두 측면을 패턴별로 같이 본다.

## 설정 주입형 커링과 부분 적용

가장 흔하게 쓰는 형태다. 핸들러나 유틸 함수가 매번 같은 설정을 받아야 하는데, 그 설정을 호출부에서 매번 넘기면 코드가 지저분해진다. 함수를 한 단계 감싸서 설정을 먼저 받고, 안쪽 함수가 실제 인자를 받게 한다.

```javascript
// 설정을 먼저 바인딩하고, 실제 요청 데이터는 나중에 받는 핸들러 팩토리
function createRetryFetcher(config) {
  const { baseUrl, maxRetries, timeoutMs } = config;

  return async function fetchWithRetry(path, options = {}) {
    let lastError;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
          const res = await fetch(`${baseUrl}${path}`, {
            ...options,
            signal: controller.signal,
          });
          return res;
        } finally {
          clearTimeout(timer);
        }
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError;
  };
}

// 서비스별로 설정이 박힌 fetcher를 미리 만들어둔다
const paymentApi = createRetryFetcher({
  baseUrl: 'https://pay.internal',
  maxRetries: 3,
  timeoutMs: 2000,
});

const searchApi = createRetryFetcher({
  baseUrl: 'https://search.internal',
  maxRetries: 1,
  timeoutMs: 500,
});

// 호출부는 path와 options만 신경 쓰면 된다
await paymentApi('/charge', { method: 'POST', body });
```

`baseUrl`, `maxRetries`, `timeoutMs`를 매 호출마다 넘기지 않고 `paymentApi`, `searchApi`라는 이름에 박아뒀다. 호출부에서 잘못된 timeout을 넘길 여지가 없어진다.

부분 적용은 커링의 사촌 격인데, 인자 일부만 미리 채우는 형태다. 로거가 대표적이다.

```javascript
function createLogger(context) {
  return function log(level, message, meta = {}) {
    console.log(JSON.stringify({
      level,
      context,        // 클로저로 박힌 값
      message,
      ...meta,
      ts: Date.now(),
    }));
  };
}

const orderLog = createLogger('order-service');
orderLog('info', 'order created', { orderId: 1234 });
// {"level":"info","context":"order-service","message":"order created","orderId":1234,"ts":...}
```

### 잘못 쓰면 생기는 문제: 설정 객체를 공유 참조로 박는 경우

`config`를 클로저에 가두면 그 객체를 함수가 계속 참조한다. 여기서 사고가 나는 패턴은 **호출부에서 같은 객체를 넘긴 뒤 나중에 그 객체를 수정하는 경우**다.

```javascript
const sharedConfig = { baseUrl: 'https://a.internal', maxRetries: 3, timeoutMs: 2000 };

const fetcherA = createRetryFetcher(sharedConfig);

// 나중에 다른 곳에서 같은 객체를 재활용한다고 수정
sharedConfig.baseUrl = 'https://b.internal';

const fetcherB = createRetryFetcher(sharedConfig);

// fetcherA도 b.internal을 쓰게 된다 — 디스트럭처링했으면 괜찮지만
// config 객체 자체를 클로저에 박았다면 둘 다 같은 객체를 본다
```

위 `createRetryFetcher`는 `const { baseUrl } = config`로 원시값을 꺼냈기 때문에 안전하다. 하지만 `return function (path) { fetch(config.baseUrl + path) }`처럼 객체를 통째로 참조하면 외부 수정이 그대로 반영된다. 팩토리 안에서 필요한 값을 꺼내 두거나 얕은 복사라도 떠두는 편이 안전하다. 설정을 클로저에 가두는 순간 그 객체의 수명은 함수의 수명과 같아진다는 점을 기억해야 한다.

## 초기화를 한 번만 수행하는 once-guard

커넥션 풀 초기화, 설정 파일 로드, 외부 클라이언트 생성 같은 작업은 프로세스 동안 한 번만 일어나야 한다. 호출하는 쪽이 여러 군데라 누가 먼저 부를지 모를 때, 플래그를 클로저에 가둬 두면 중복 실행을 막는다.

```javascript
function once(fn) {
  let called = false;
  let result;
  return function (...args) {
    if (!called) {
      called = true;
      result = fn.apply(this, args);
    }
    return result;
  };
}

const initDb = once(() => {
  console.log('connecting to db...');
  return createPool({ max: 10 });
});

const pool1 = initDb(); // "connecting to db..." 출력
const pool2 = initDb(); // 출력 없음, 같은 pool 반환
console.log(pool1 === pool2); // true
```

`called`와 `result`가 클로저에 잡혀 있어서 두 번째 호출부터는 캐시된 결과만 돌려준다. 모듈 스코프 변수로 같은 걸 만들 수도 있지만, `once`로 감싸면 재사용 가능한 단위가 된다.

### 비동기 초기화에서 흔히 터지는 문제

위 `once`는 동기 함수 기준이다. 비동기 초기화에 그대로 쓰면 동시 호출 시 초기화가 두 번 돈다.

```javascript
// 잘못된 경우: async 함수에 위 once를 쓰면
const initDbBad = once(async () => {
  await connect();
  return pool;
});

// 두 요청이 거의 동시에 들어오면
const [a, b] = await Promise.all([initDbBad(), initDbBad()]);
// 첫 호출이 await에서 멈춰 있는 사이 called가 아직 false라서
// 두 번째 호출도 통과한다 → connect()가 두 번 실행
```

`called = true`로 바꾸는 시점과 `await`로 제어권을 넘기는 시점 사이에 두 번째 호출이 끼어든다. 비동기는 결과 값이 아니라 **Promise 자체를 캐시**해야 한다.

```javascript
function onceAsync(fn) {
  let promise;
  return function (...args) {
    if (!promise) {
      promise = fn.apply(this, args);  // Promise를 즉시 저장
    }
    return promise;
  };
}

const initDb = onceAsync(async () => {
  await connect();
  return pool;
});

// 동시에 불러도 같은 Promise를 기다린다 → connect()는 한 번만
const [a, b] = await Promise.all([initDb(), initDb()]);
console.log(a === b); // true
```

`promise` 할당은 동기적으로 끝나므로 두 번째 호출은 이미 진행 중인 Promise를 받는다. 한 가지 주의점은 초기화가 실패했을 때다. 실패한 Promise가 그대로 캐시되면 이후 호출이 전부 같은 에러를 받는다. 재시도가 필요하면 `catch`에서 `promise = undefined`로 되돌려야 한다.

```javascript
function onceAsyncResettable(fn) {
  let promise;
  return function (...args) {
    if (!promise) {
      promise = fn.apply(this, args).catch((err) => {
        promise = undefined; // 실패 시 다음 호출에서 재시도 가능
        throw err;
      });
    }
    return promise;
  };
}
```

## 미들웨어와 라우터 팩토리 기반 의존성 주입

Express나 Koa를 쓰면 미들웨어 시그니처가 `(req, res, next)`로 고정돼 있다. 여기에 DB 레포지토리나 설정 같은 의존성을 끼워 넣을 자리가 없다. 미들웨어를 반환하는 팩토리 함수를 만들면 의존성을 클로저로 주입할 수 있다.

```javascript
// 의존성을 받아 미들웨어를 반환하는 팩토리
function requireRole(role, { userRepo }) {
  return async function (req, res, next) {
    try {
      const user = await userRepo.findById(req.userId);
      if (!user || user.role !== role) {
        return res.status(403).json({ error: 'forbidden' });
      }
      req.user = user;
      next();
    } catch (err) {
      next(err);
    }
  };
}

// 라우터 설정 시 의존성을 한 번 주입
const userRepo = createUserRepo(pool);
router.get('/admin', requireRole('admin', { userRepo }), adminHandler);
router.delete('/users/:id', requireRole('admin', { userRepo }), deleteHandler);
```

`userRepo`를 미들웨어 안에서 전역으로 끌어다 쓰거나 `req`에 미리 붙여두지 않아도 된다. 테스트할 때는 가짜 `userRepo`를 넘겨서 미들웨어를 단독으로 검증할 수 있다.

```javascript
// 테스트: 실제 DB 없이 미들웨어만 검증
const fakeRepo = { findById: async () => ({ role: 'user' }) };
const mw = requireRole('admin', { userRepo: fakeRepo });

const res = { status: (c) => ({ json: (b) => ({ code: c, body: b }) }) };
await mw({ userId: 1 }, res, () => { throw new Error('next 호출되면 안 됨'); });
// role이 user이므로 403 응답
```

라우터 자체를 팩토리로 만드는 것도 같은 원리다. 모듈마다 `createUserRouter(deps)` 형태로 의존성을 받아 라우터를 조립하면, 앱 부트스트랩 코드에서 의존성 그래프가 한눈에 보인다.

```javascript
function createUserRouter({ userRepo, logger }) {
  const router = express.Router();

  router.get('/:id', async (req, res, next) => {
    logger('info', 'fetching user', { id: req.params.id });
    const user = await userRepo.findById(req.params.id);
    if (!user) return res.status(404).end();
    res.json(user);
  });

  return router;
}

// app.js — 의존성을 한 곳에서 주입
const userRouter = createUserRouter({ userRepo, logger: createLogger('user') });
app.use('/users', userRouter);
```

이 방식은 DI 컨테이너 라이브러리 없이도 의존성 주입을 구현한다. 클로저가 곧 생성자 주입 역할을 한다.

## 요청별 상태를 클로저로 보존하는 컨텍스트 패턴

한 요청을 처리하는 동안 여러 함수가 같은 값(요청 ID, 트랜잭션 핸들, 추적용 타이머)을 공유해야 할 때가 있다. 매 함수에 인자로 넘기면 시그니처가 오염된다. 요청이 들어올 때 컨텍스트를 클로저로 잡아두고, 그 안의 함수들이 공유하게 만든다.

```javascript
// 요청마다 컨텍스트를 만들어 핸들러들에 클로저로 공유
function createRequestContext(requestId) {
  const startedAt = Date.now();
  const events = [];

  function track(name) {
    events.push({ name, at: Date.now() - startedAt });
  }

  function summary() {
    return { requestId, totalMs: Date.now() - startedAt, events };
  }

  return { requestId, track, summary };
}

app.use((req, res, next) => {
  req.ctx = createRequestContext(req.headers['x-request-id'] ?? genId());
  res.on('finish', () => {
    console.log(JSON.stringify(req.ctx.summary()));
  });
  next();
});

// 핸들러 어디서든 같은 컨텍스트에 기록
async function handler(req, res) {
  req.ctx.track('handler-start');
  const data = await loadData();
  req.ctx.track('data-loaded');
  res.json(data);
}
```

`startedAt`과 `events`는 요청마다 독립적이다. 요청 A의 `track`과 요청 B의 `track`은 서로 다른 클로저라 배열이 섞이지 않는다. 이게 클로저 기반 컨텍스트의 핵심이다. 요청별로 함수 묶음을 새로 찍어내기 때문에 자연스럽게 격리된다.

### 모듈 스코프에 컨텍스트를 두면 생기는 사고

클로저 대신 모듈 레벨 변수에 현재 요청 상태를 두는 코드를 가끔 본다. 단일 요청 테스트에서는 멀쩡히 돌아가다가 동시 요청에서 상태가 섞인다.

```javascript
// 절대 이렇게 하면 안 되는 경우
let currentRequestId; // 모듈 스코프 공유 상태

app.use((req, res, next) => {
  currentRequestId = req.headers['x-request-id'];
  next();
});

async function handler(req, res) {
  await loadData(); // await 동안 다른 요청이 currentRequestId를 덮어씀
  console.log(currentRequestId); // 내 요청 ID가 아닐 수 있다
}
```

Node.js는 단일 스레드지만 `await`마다 다른 요청의 코드가 끼어든다. 모듈 변수는 모든 요청이 공유하므로 `await` 이후의 `currentRequestId`는 다른 요청이 덮어쓴 값일 수 있다. 요청별 격리가 필요하면 클로저로 잡거나, 표준 해법인 `AsyncLocalStorage`를 쓴다. 클로저는 함수에 명시적으로 컨텍스트를 들고 다니는 방식이고, `AsyncLocalStorage`는 비동기 호출 체인을 따라 암묵적으로 전파하는 방식이다. 인자로 `req.ctx`를 넘기기 번거로운 깊은 호출 스택이면 후자가 낫다.

## 클로저로 만든 캐시와 카운터, 그리고 인스턴스별 함수 비용

메모이제이션 캐시를 클로저로 만드는 건 교과서적인 예제다.

```javascript
function memoize(fn) {
  const cache = new Map();
  return function (arg) {
    if (cache.has(arg)) return cache.get(arg);
    const result = fn(arg);
    cache.set(arg, result);
    return result;
  };
}

const slowSquare = (n) => {
  // 무거운 계산이라고 가정
  return n * n;
};

const fastSquare = memoize(slowSquare);
fastSquare(4); // 계산
fastSquare(4); // 캐시에서
```

카운터도 마찬가지다.

```javascript
function createCounter() {
  let count = 0;
  return {
    inc: () => ++count,
    get: () => count,
  };
}
```

여기까지는 깔끔하지만, 실무에서 부딪히는 두 가지 문제가 있다.

### 캐시가 무한정 자란다

위 `memoize`의 `cache`는 클로저가 살아 있는 한 절대 비워지지 않는다. 인자 종류가 유한하면 괜찮지만, 사용자 ID나 요청 파라미터처럼 카디널리티가 높은 키를 캐싱하면 메모리가 계속 늘어난다. 프로덕션에서 이런 메모이제이션이 OOM의 원인이 되는 경우가 있다. 크기 상한이나 TTL을 두거나, GC가 회수할 수 있게 `WeakMap`(키가 객체일 때)을 쓴다.

```javascript
function memoizeWithLimit(fn, maxSize = 1000) {
  const cache = new Map();
  return function (arg) {
    if (cache.has(arg)) return cache.get(arg);
    const result = fn(arg);
    cache.set(arg, result);
    if (cache.size > maxSize) {
      // Map은 삽입 순서를 유지하므로 가장 오래된 키부터 제거
      cache.delete(cache.keys().next().value);
    }
    return result;
  };
}
```

### 인스턴스마다 함수 객체가 새로 만들어진다

클로저로 메서드를 만들면, 객체를 만들 때마다 함수 객체가 새로 생성된다. `createCounter`를 10만 번 호출하면 `inc`, `get` 함수 객체가 20만 개 생긴다. 객체가 몇 개일 때는 신경 쓸 일이 아니지만, 다량으로 생성하는 핫 패스라면 메모리와 GC 부담이 된다.

```javascript
// 클로저 방식 — 인스턴스마다 inc, get 함수가 따로 생성됨
function createCounter() {
  let count = 0;
  return { inc: () => ++count, get: () => count };
}

// 프로토타입 방식 — 메서드는 프로토타입에 한 번만 존재, 인스턴스끼리 공유
class Counter {
  #count = 0;
  inc() { return ++this.#count; }
  get() { return this.#count; }
}
```

클래스(또는 프로토타입)는 메서드를 프로토타입에 한 번만 두고 모든 인스턴스가 공유한다. 상태 캡슐화는 `#private` 필드로 해결되니, 클로저로 메서드를 만들 이유가 줄었다. 그래도 클로저 방식을 쓰는 경우는 있다. `#private`보다 강한 은닉(상속받은 쪽에서도 못 건드림)이 필요하거나, 함수 하나만 반환하면 되는 가벼운 경우다.

판단 기준은 단순하다. 소수의 장수 객체(서비스, 레포지토리, 설정)는 클로저로 만들어도 함수 객체 비용이 무시할 만하다. 요청마다 또는 루프 안에서 대량으로 찍어내는 객체라면 프로토타입 기반을 우선 검토한다. 앞서 본 컨텍스트 패턴은 요청당 하나라 클로저로 충분하고, 만약 요청당 수천 개씩 만드는 엔티티라면 클래스가 맞다.

## 정리하면서 짚어둘 것

클로저를 설계 도구로 쓸 때 공통으로 작동하는 원리는 "함수가 만들어지는 시점에 무언가를 박아둔다"는 것이다. 설정을 박으면 커링, 플래그를 박으면 once-guard, 의존성을 박으면 DI, 요청 상태를 박으면 컨텍스트가 된다. 박아둔 값은 함수가 살아 있는 동안 같이 산다는 점이 장점이자 위험이다. 캐시처럼 의도적으로 오래 들고 있어야 하는 값도 있지만, 의도치 않게 큰 객체를 붙잡고 있으면 메모리 누수가 된다.

박아둔 값이 객체일 때는 그 객체가 외부에서 수정될 수 있는지, 언제까지 살아 있어야 하는지를 항상 확인해야 한다. 그리고 같은 클로저를 대량으로 찍어내는 자리라면 함수 객체 비용을 한 번쯤 따져보는 게 좋다.
