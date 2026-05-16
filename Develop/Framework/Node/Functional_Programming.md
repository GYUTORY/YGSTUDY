---
title: Node.js 함수형 프로그래밍
tags: [framework, node, functional-programming, middleware, stream, rxjs, worker-threads, memoization, fp-ts, effect-ts]
updated: 2026-05-16
---

# Node.js 함수형 프로그래밍

순수 함수, 불변성, 고차 함수, 합성, 모나드 같은 일반 개념은 [[Functional_Programming]]과 [[Functional_Programming_Advanced]]에서 다룬다. 이 문서는 Node.js 런타임 위에서 함수형 스타일이 실제로 어떻게 동작하고 어디서 깨지는지에 집중한다. 이벤트 루프, 스트림, Worker thread, V8 GC, 미들웨어 체인 같은 Node 고유 맥락을 빼면 함수형 패러다임 이야기는 절반밖에 안 된다.

## 미들웨어를 함수 합성으로 보기

Express의 미들웨어는 `(req, res, next) => void` 시그니처를 따른다. 반환값이 없고, 다음 단계로 넘어가는 신호를 `next()` 호출로 전달한다. 형식적으로는 함수 합성처럼 보여도, 실제로는 콜백 체이닝에 가깝다. 합성의 관점에서 두 모델은 에러 전파 방식이 다르다.

반환값 합성은 이렇게 생겼다.

```javascript
const pipe = (...fns) => (x) => fns.reduce((acc, fn) => fn(acc), x);

const parseBody = (req) => ({ ...req, body: JSON.parse(req.rawBody) });
const validate = (req) => {
  if (!req.body.email) throw new Error('email required');
  return req;
};
const enrich = (req) => ({ ...req, traceId: crypto.randomUUID() });

const prepare = pipe(parseBody, validate, enrich);
```

`pipe`로 묶은 함수는 어느 단계에서 throw 하면 호출부의 try/catch가 잡는다. 책임 위치가 명확하다.

Express의 `next(err)` 모델은 다르다. 동기 throw는 Express 5 이상에서만 자동으로 `next(err)`로 라우팅되고, Express 4까지는 `try/catch`로 감싸지 않으면 프로세스가 죽는다. async 미들웨어를 Express 4에 그대로 넣으면 reject가 unhandledRejection으로 새어 나간다. 미들웨어를 함수 합성으로 추상화하려면 어댑터 한 겹이 필요하다.

```javascript
const asMiddleware = (fn) => async (req, res, next) => {
  try {
    const result = await fn(req);
    req.ctx = result;
    next();
  } catch (err) {
    next(err);
  }
};

app.use(asMiddleware(prepare));
```

이렇게 하면 합성된 순수 함수의 결과를 `req.ctx`에 싣고, 에러는 Express 라우터의 에러 핸들러로 일관되게 흐른다. Koa는 `ctx`와 `await next()` 구조라 합성이 더 자연스럽다. Fastify는 훅(`onRequest`, `preHandler`)이 명확히 분리돼 있어서, 합성된 순수 함수를 훅 단위로 매핑하는 편이 잘 맞는다.

미들웨어 체인을 통째로 함수 합성으로 바꾸려는 시도는 보통 실패한다. 미들웨어는 `res.send()`처럼 부작용을 일으키는 코드, 인증·로깅처럼 부분적으로만 적용되는 코드가 섞인다. 순수 영역과 부작용 영역의 경계를 명확히 긋고, 순수 영역에만 합성을 쓰는 편이 낫다.

## 비동기 합성: pipeAsync와 단계 식별

서버 코드는 fetch → parse → validate → persist 같은 비동기 파이프라인이 흔하다. 일반적인 `pipe`는 동기 함수 전용이라 Promise를 다루지 못한다. `pipeAsync`를 직접 만들어 쓴다.

```javascript
const pipeAsync = (...fns) => (input) =>
  fns.reduce((acc, fn) => acc.then(fn), Promise.resolve(input));
```

문제는 reject가 나면 어느 단계에서 실패했는지 알 수 없다. 스택트레이스는 마지막 `await` 지점만 가리키고, 단계 이름은 어디에도 없다. 단계 식별을 위한 데코레이터 `tagStep`이 유용하다.

```javascript
const tagStep = (name, fn) => async (input) => {
  try {
    return await fn(input);
  } catch (err) {
    err.step = name;
    err.message = `[${name}] ${err.message}`;
    throw err;
  }
};

const ingest = pipeAsync(
  tagStep('fetch', fetchUserFromUpstream),
  tagStep('parse', parsePayload),
  tagStep('validate', validateSchema),
  tagStep('persist', writeToDb),
);
```

`AbortSignal`과의 결합은 한 단계 더 까다롭다. 합성된 파이프라인 중간에서 요청이 취소되면 남은 단계는 실행하지 않아야 한다. `pipeAsync`에 시그널을 흘리는 방식은 두 가지다. 클로저로 캡처하거나, 입력 객체에 실어 넘긴다. 후자가 합성 가능성이 높다.

```javascript
const withSignal = (signal) => (fn) => async (input) => {
  if (signal.aborted) throw new DOMException('aborted', 'AbortError');
  return fn({ ...input, signal });
};
```

각 단계 함수가 자기 `signal`을 받아서 fetch나 DB 드라이버에 넘기면 된다. 합성 단계 하나라도 signal을 무시하면 취소가 안 통한다. 이건 FP의 한계가 아니라 합성의 정직함이다 — 단계가 시그널을 받아야 한다고 시그니처에 박혀 있으므로 빠뜨릴 수 없다.

## Stream을 map/filter/reduce로 보기

Node.js Stream은 함수형 컬렉션 연산의 lazy 버전이다. Readable은 지연된 iterable, Transform은 map, filter, reduce를 합친 연산자다. 메모리에 다 못 올리는 GB급 파일을 다룰 때 이 관점이 빛난다.

`Array.prototype.map`을 이어 붙이면 중간 배열이 생긴다. 100GB 로그 파일을 라인별로 처리하면서 `lines.map(parse).filter(isError).map(format)`처럼 쓰면 GC가 무너진다. `pipeline()`과 Transform 스트림은 한 줄 단위로 흘려보낸다.

```javascript
import { pipeline } from 'node:stream/promises';
import { Transform } from 'node:stream';
import { createReadStream, createWriteStream } from 'node:fs';
import { createInterface } from 'node:readline';

const mapStream = (fn) => new Transform({
  objectMode: true,
  transform(chunk, _enc, cb) {
    try { cb(null, fn(chunk)); } catch (e) { cb(e); }
  },
});

const filterStream = (pred) => new Transform({
  objectMode: true,
  transform(chunk, _enc, cb) {
    cb(null, pred(chunk) ? chunk : undefined);
  },
});

await pipeline(
  createReadStream('access.log'),
  createInterface({ crlfDelay: Infinity }),
  mapStream(parseLogLine),
  filterStream((line) => line.status >= 500),
  mapStream((line) => JSON.stringify(line) + '\n'),
  createWriteStream('errors.ndjson'),
);
```

배열 기반 코드와 모양은 같지만, 메모리 점유는 청크 크기 + Transform 내부 버퍼 정도로 일정하다. 이게 트랜스듀서가 약속하는 "중간 컬렉션 없는 합성"의 Node식 구현이다.

스트림 모델의 backpressure는 lazy 평가의 자연스러운 산물이다. 소비자가 느리면 producer가 자동으로 멈춘다. `Readable.pause()`/`resume()`은 백프레셔 신호를 직접 다루는 API다. 함수형으로 보면, 다음 값을 "요청"받기 전까지 계산을 미루는 것이 곧 백프레셔다.

여기서 자주 깨지는 부분이 하나 있다. Transform에 `async` 함수를 넘기지 않고 동기 throw 위주의 함수를 합성하면 백프레셔가 무력화된다. `transform(chunk, _enc, cb)` 콜백에서 `cb(null, result)`를 동기로 즉시 호출하면, 다음 청크가 큐에 쌓이는 속도가 소비자 속도와 무관해진다. 외부 I/O를 호출하는 단계라면 `await`로 자연스럽게 backpressure가 작동하도록 둬야 한다.

## EventEmitter 위의 Observable

EventEmitter는 푸시 기반 비동기 컬렉션이다. `on('data', ...)`은 무한 컬렉션의 forEach다. 여기에 map/filter를 얹고 싶다면 RxJS가 자연스럽게 들어온다.

```javascript
import { fromEvent, filter, map, debounceTime } from 'rxjs';

const click$ = fromEvent(emitter, 'click').pipe(
  filter((e) => e.button === 0),
  debounceTime(150),
  map((e) => ({ x: e.x, y: e.y })),
);

click$.subscribe((point) => process(point));
```

RxJS는 두 가지를 해준다. 하나는 시간 기반 연산자(`debounceTime`, `throttle`, `bufferTime`)이고, 다른 하나는 구독 해제 같은 리소스 관리다. EventEmitter는 `removeListener`를 잊으면 누수가 난다. Observable은 `unsubscribe`로 정리한다.

도입을 망설이게 되는 지점은 번들 크기와 학습 비용이다. operator 하나 쓰자고 RxJS 전체를 가져오면 백엔드 의존성에 30~50KB가 추가되고, 팀원이 `switchMap`과 `mergeMap`의 차이를 모르면 디버깅 비용이 커진다. 백엔드에서 RxJS가 진짜로 답인 경우는 — WebSocket이나 SSE 같은 스트림 데이터에 시간 윈도우 연산을 얹어야 할 때, NestJS처럼 프레임워크가 이미 의존하고 있을 때 정도다. 단순 이벤트 처리는 EventEmitter + async iterator(`events.on(emitter, 'data')`)가 더 가볍다.

## Worker thread, Cluster, 직렬화

Worker thread의 `postMessage`는 구조화 복제(structured clone)로 데이터를 옮긴다. 함수는 직렬화 대상이 아니다. 클로저로 캡처된 상태도 함께 사라진다.

```javascript
const multiplier = 10;
const calculate = (x) => x * multiplier;

worker.postMessage({ fn: calculate.toString() });
```

`calculate.toString()`은 함수 본문 텍스트는 주지만 `multiplier`는 잃는다. 워커 측에서 `eval`로 복원해도 자유 변수는 undefined다.

여기서 순수 함수의 가치가 명확해진다. 자유 변수가 없는 함수는 직렬화 가능한 영역에 있다. 입력만으로 결정되므로 워커에 인자만 보내면 끝난다. 함수 자체를 보낼 필요도 없다 — 워커 코드가 같은 함수를 import 해두고, 부모는 인자만 `postMessage`로 보낸다.

```javascript
// worker.js
import { parentPort } from 'node:worker_threads';
import { hashPassword } from './crypto.js';

parentPort.on('message', ({ id, password }) => {
  parentPort.postMessage({ id, hash: hashPassword(password) });
});

// main.js
worker.postMessage({ id: 1, password: 'plain' });
```

함수가 부작용을 가지면 이 모델이 깨진다. 메인 프로세스의 DB 커넥션 풀, 캐시, 로거를 캡처한 함수는 워커에서 실행할 수 없다. "워커로 옮기기 쉬운 함수가 좋은 함수"라는 판단 기준이 자연스럽게 따라온다.

Cluster는 프로세스 단위라 상황이 더 명확하다. 워커끼리 메모리를 공유하지 않으므로 함수형으로 짜인 코드는 그대로 동작하지만, 모듈 로드 시점의 전역 상태(connection pool 초기화, 캐시 워밍업)는 워커마다 별도로 일어난다. 메모이제이션 캐시가 워커마다 따로 존재하므로 hit rate가 인스턴스 수에 반비례한다는 점은 자주 놓친다.

## 메모이제이션과 GC 압박

함수형 코드는 `memoize` 유혹이 크다. 같은 입력에 같은 출력을 보장하는 순수 함수에 캐싱을 붙이면 공짜로 속도가 오른다 — 단기 스크립트라면. 장기 실행 서버에서는 다르다.

가장 흔한 버그는 `Map`을 캐시로 쓰면서 키를 제한하지 않는 패턴이다.

```javascript
const cache = new Map();
const heavy = (input) => {
  const key = JSON.stringify(input);
  if (cache.has(key)) return cache.get(key);
  const result = expensive(input);
  cache.set(key, result);
  return result;
};
```

요청마다 다른 입력이 오면 `cache`는 무한정 자란다. V8의 OldSpace를 점유하고, full GC를 더 자주 트리거하며, 결국 OOM으로 죽는다. `--trace-gc`를 켜면 mark-sweep pause가 100ms를 넘어가는 모습이 보인다.

해결은 두 가지다.

**LRU**는 키 수를 제한한다. `lru-cache` 패키지가 사실상 표준이다. `max` 항목 수 또는 `maxSize` 바이트로 상한을 둘 수 있다. 입력의 카디널리티가 높고, 핫셋이 일부에 몰릴 때 잘 맞는다.

```javascript
import { LRUCache } from 'lru-cache';

const cache = new LRUCache({ max: 10_000, ttl: 1000 * 60 * 5 });
```

**WeakMap**은 키가 객체 참조일 때만 쓴다. 키가 다른 곳에서 GC되면 캐시 항목도 함께 사라진다. 요청 객체나 유저 엔티티 같은 lifetime이 명확한 객체를 키로 쓰는 메모이제이션에 적합하다.

```javascript
const userPermissions = new WeakMap();

const getPermissions = (user) => {
  if (userPermissions.has(user)) return userPermissions.get(user);
  const perms = computePermissions(user);
  userPermissions.set(user, perms);
  return perms;
};
```

입력이 원시값(문자열·숫자)이면 WeakMap은 못 쓴다. 그때는 LRU가 답이다.

캐시를 도입하기 전에 측정부터 한다. `clinic.js`의 doctor나 `--prof`로 핫스팟을 확인하고, 진짜로 같은 입력이 반복되는지 본다. 사실상 모든 호출이 다른 입력이면 캐시는 메모리만 잡아먹는다.

## Either/Result로 라우터 정리

Express 라우터는 `try/catch + next(err)` 보일러플레이트가 반복된다.

```javascript
app.post('/users', async (req, res, next) => {
  try {
    const user = await createUser(req.body);
    res.status(201).json(user);
  } catch (err) {
    next(err);
  }
});
```

서비스 레이어가 Either나 Result를 반환하도록 바꾸면, 라우터에서 `fold`로 분기를 통합할 수 있다.

```javascript
class Result {
  static ok(value) { return new Result(true, value, null); }
  static err(error) { return new Result(false, null, error); }
  constructor(success, value, error) {
    this.success = success; this.value = value; this.error = error;
  }
  map(fn) { return this.success ? Result.ok(fn(this.value)) : this; }
  flatMap(fn) { return this.success ? fn(this.value) : this; }
  fold(onErr, onOk) { return this.success ? onOk(this.value) : onErr(this.error); }
}

const createUser = async (body) => {
  const validated = validate(body);
  if (!validated.success) return validated;
  const user = await repo.insert(validated.value);
  return Result.ok(user);
};

app.post('/users', async (req, res) => {
  const result = await createUser(req.body);
  result.fold(
    (err) => res.status(err.status ?? 400).json({ message: err.message }),
    (user) => res.status(201).json(user),
  );
});
```

타입스크립트와 함께 쓰면 라우터에서 에러 케이스를 잊을 수가 없다. `fold`의 두 인자가 강제되기 때문이다. 단점은 throw를 쓰지 않으므로 미들웨어 스택의 전역 에러 핸들러를 우회한다 — 라우터마다 응답 형식을 직접 만들어야 한다. 응답 형식을 표준화한 헬퍼를 만들어두면 일관성이 유지된다.

DB 드라이버나 외부 라이브러리는 여전히 throw 한다. 서비스 경계에서 try/catch로 감싸 Result로 변환하는 어댑터 레이어가 필요하다. 이 어댑터를 빠뜨리면 throw가 새어 나가 의도가 무너진다.

## fp-ts와 Effect-TS의 비용

순수 JS에서 모나드를 직접 구현하는 데는 한계가 있다. 타입 추론이 약하고, `do` 표기 같은 편의 문법이 없으며, 라이브러리 생태계가 작다. fp-ts와 Effect-TS는 이 빈자리를 채운다.

`fp-ts`는 Haskell 스타일에 가깝다. `TaskEither<E, A>`, `Option<A>`, `Reader<R, A>` 같은 타입을 제공하고, `pipe`와 `flow`로 합성한다. 학습 곡선이 가파르다 — 5년차 백엔드 개발자가 처음 보면 첫 주는 거의 못 쓴다. 타입 시그니처가 길어져서 IDE 호버가 화면을 덮는다. 번들 영향은 트리셰이킹이 잘 되면 작은 편이지만, 백엔드라 번들 크기는 큰 이슈가 아니다.

`Effect-TS`는 fp-ts의 후계자 격이다. `Effect<R, E, A>` 하나로 모든 효과를 표현하고, fiber 기반 동시성·구조적 동시성·재시도·타임아웃을 빌트인으로 제공한다. fp-ts보다 ergonomic이 낫고, generator 기반 do 표기가 try/await처럼 읽힌다.

```typescript
import { Effect } from 'effect';

const program = Effect.gen(function* () {
  const user = yield* fetchUser('123');
  const orders = yield* fetchOrders(user.id);
  return { user, orders };
});
```

도입 의사결정에서 자주 놓치는 부분이 셋 있다.

첫째, 팀원 전원이 모나드를 이해해야 코드 리뷰가 굴러간다. 한 명만 알면 그 사람이 휴가 갔을 때 PR이 멈춘다.

둘째, 외부 라이브러리와의 경계가 마찰면이 된다. Express 미들웨어, ORM, AWS SDK는 Promise/throw 기반이다. Effect와의 경계마다 `Effect.tryPromise`로 감싸는 코드가 늘어나서, 코드베이스의 60%가 Effect로 짜인 상태에서 가장 통일감이 좋다. 30% 정도만 도입하면 두 세계가 겹쳐서 더 복잡해진다.

셋째, TypeScript 추론 한계가 종종 보인다. 깊은 합성에서 타입이 `unknown`으로 무너지거나, 컴파일 시간이 갑자기 길어진다. `tsc` watch가 30초씩 걸리기 시작하면 합성 깊이를 의도적으로 줄여야 한다.

작은 서비스에 Effect-TS를 도입한 사례에서, 코드 라인 수는 줄지만 인지 부하는 그대로거나 늘어나는 경우가 많다. 도메인 로직이 복잡하고 동시성·재시도·취소 같은 효과를 일관되게 다뤄야 하는 결제·예약 시스템에서 가치가 명확하다.

## 핫패스에서 FP를 포기하는 신호

함수형 스타일은 보통 무료다. V8이 인라이닝과 escape analysis로 대부분 비용을 흡수한다. 하지만 요청당 수천 번 도는 코드에서는 다르다.

기준선이 필요하다. `autocannon -c 100 -d 30 http://localhost:3000/api/...`로 RPS와 p99를 잡는다.

| 패턴 | 비용이 드러나는 지점 |
|------|---------------------|
| 짧은 배열에 `map().filter().reduce()` 체인 | 중간 배열 할당이 GC 압박 |
| 매 호출마다 `{...obj, field: v}` | 짧은 lifetime 객체가 NewSpace 점유 |
| `compose(f, g, h)`로 만든 함수가 핫패스 | 인라이닝이 안 되고 매번 함수 호출 비용 |
| 합성 단계마다 try/catch | V8이 함수를 deoptimize 함 |

실제로 본 사례 하나. JSON 응답 변환을 `pipe(snakeToCamel, mask, decorate)`로 짠 핸들러가 1만 RPS에서 p99가 80ms로 뛰었다. 같은 로직을 한 함수 안에서 for 루프로 풀어 쓰니 p99가 12ms로 떨어졌다. 차이는 단계별 객체 복제와 함수 호출 오버헤드였다.

판단 기준은 명확하다. 변환 단계가 핫패스 바깥(서버 시작, 배치 작업)이면 합성으로 짜고, 요청당 수천 번 도는 영역이면 측정한 뒤 결정한다. "보일러플레이트가 늘어도 측정값이 의미 있게 좋아질 때만" 회귀한다. 미리 풀어 쓰면 가독성 손해만 본다.

## 자주 만나는 트러블슈팅

### this 바인딩 손실

클래스 메서드를 미들웨어 합성에 넣으면 `this`가 사라진다.

```javascript
class UserService {
  constructor(repo) { this.repo = repo; }
  async findById(id) { return this.repo.get(id); }
}

const svc = new UserService(repo);
app.get('/users/:id', asMiddleware(svc.findById)); // this === undefined
```

호출부에서 메서드만 떼어내면 메서드 안의 `this`는 호출 컨텍스트를 잃는다. `.bind(svc)`로 묶거나, 애초에 메서드 대신 클로저로 짠 함수를 쓴다.

```javascript
const findById = (id) => repo.get(id);
```

클래스를 안 쓰면 이 문제가 발생할 여지가 없다. 함수형 스타일에서 클래스 도입을 자제하는 실용적 이유 중 하나다.

### unhandledRejection으로 인한 프로세스 죽음

비동기 합성 내부에서 reject가 발생했는데 호출부가 await 하지 않으면 unhandledRejection이 터진다. Node 15부터 기본 정책이 `throw`라 프로세스가 죽는다.

```javascript
app.post('/jobs', (req, res) => {
  processJob(req.body); // await 없음
  res.status(202).end();
});
```

fire-and-forget이 의도라면 명시적으로 처리한다.

```javascript
app.post('/jobs', (req, res) => {
  processJob(req.body).catch((err) => logger.error({ err }, 'job failed'));
  res.status(202).end();
});
```

`pipeAsync`로 합성한 결과는 항상 Promise를 반환하므로, 호출부에서 await 하거나 catch를 붙이는 규칙을 코드 리뷰에서 잡아야 한다. ESLint의 `no-floating-promises`가 도움이 된다.

### Stream Transform에 동기 함수를 합성한 경우

```javascript
const fastTransform = new Transform({
  objectMode: true,
  transform(chunk, _enc, cb) {
    cb(null, chunk * 2); // 즉시 동기 콜백
  },
});
```

이 자체는 정상이지만, 다운스트림이 느리면 어떻게 될까. Transform 내부 버퍼는 `highWaterMark`(기본 16개)까지 쌓이고 그 다음 backpressure가 켜진다. 하지만 동기 변환은 변환 자체가 빠르므로 버퍼가 빠르게 차고, producer의 read가 멈추는 시점이 다운스트림 처리량에 의해서만 결정된다. 즉 backpressure 자체는 동작한다.

문제가 되는 케이스는 따로 있다. Transform에서 외부 I/O를 하는데 콜백을 동기로 부르는 잘못된 합성이다.

```javascript
const broken = new Transform({
  objectMode: true,
  transform(chunk, _enc, cb) {
    callExternalApi(chunk); // Promise를 await 하지 않음
    cb(null, chunk); // I/O 끝나기 전에 다음 청크 요청
  },
});
```

이러면 Transform은 100ms 안에 수천 개 청크를 처리한 척하고, 실제 외부 API는 뒤늦게 reject 폭탄을 던진다. backpressure가 전혀 작동하지 않는다. async 함수로 바꿔서 `await`로 자연스럽게 신호를 흘려야 한다.

```javascript
const fixed = new Transform({
  objectMode: true,
  async transform(chunk, _enc, cb) {
    try {
      await callExternalApi(chunk);
      cb(null, chunk);
    } catch (err) { cb(err); }
  },
});
```

## 정리하며 챙길 것

Node.js에서 함수형 스타일은 "어디까지가 순수 영역이고 어디부터 부작용 영역인지" 경계를 긋는 도구로 가장 잘 작동한다. 미들웨어, 라우터 응답, DB 호출은 어차피 부작용이다. 그 안에서 데이터 변환, 검증, 정책 결정 같은 순수 영역만 함수 합성으로 묶으면 테스트 가능성이 커지고 워커로 옮기기 쉬워진다.

스트림과 백프레셔는 함수형 lazy 평가가 Node 코어에 가장 깊이 박혀 있는 지점이고, 메모이제이션·캐시·합성 깊이는 V8 GC와 직접 부딪힌다. fp-ts나 Effect-TS는 도메인이 충분히 복잡하고 팀 전원이 학습 비용을 감당할 때만 의미가 있다. 핫패스에서는 측정하고, 측정값이 말하면 for 루프로 돌아간다.

관련 문서: [[Functional_Programming]] · [[Functional_Programming_Advanced]] · [[Error_Handling]] · [[Nodejs_Framework_Overview]]
