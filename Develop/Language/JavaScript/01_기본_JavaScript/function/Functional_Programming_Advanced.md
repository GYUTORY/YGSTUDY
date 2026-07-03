---
title: JavaScript 함수형 프로그래밍 심화
tags: [language, javascript, 01기본javascript, function, functional-programming, currying, monad, transducer, lens]
updated: 2026-04-24
---

# JavaScript 함수형 프로그래밍 심화

## 들어가며

기본 FP 문서는 순수 함수와 불변성, 고차 함수, 간단한 compose/pipe, Maybe 모나드의 감을 잡는 수준까지 다룬다. 실제 프로젝트에서는 그 선을 넘자마자 여러 곳에서 막힌다. compose 몇 개를 체인으로 엮었을 뿐인데 에러가 엉뚱한 지점에서 터지고, map을 여러 번 거치는 순간 메모리가 쑥 오르고, 불변 업데이트를 하려고 중첩 스프레드를 쓰다가 세 단계 깊어지면 가독성이 바닥을 친다. 이 문서는 그런 실무 상황에서 쓰이는 기법들만 모았다. 기본 개념은 중복하지 않는다.

## 포인트프리 스타일과 자동 커링

포인트프리(point-free)는 인자를 명시하지 않고 함수 합성만으로 표현하는 방식이다. `users.map(u => u.name)` 대신 `users.map(prop('name'))`처럼 쓰는 식이다. 이 스타일이 성립하려면 거의 모든 유틸 함수가 커링되어 있어야 한다. 커링이 된 `prop('name')`은 함수 하나를 돌려주고, 그 함수를 map의 콜백으로 바로 넣을 수 있기 때문이다.

직접 커링을 구현할 때 가장 먼저 부딪히는 게 arity 문제다. `fn.length`로 남은 인자 수를 파악하는 게 표준 관행인데, 이게 네이티브 함수나 가변 인자 함수에서 어긋난다. `console.log.length`는 0이고, 스프레드 인자를 쓰는 함수도 보통 0 또는 1을 돌려준다. 그래서 외부에서 arity를 명시적으로 받는 `curryN`과 자동 추론하는 `curry`를 분리하는 구현이 많다.

placeholder는 순서를 바꿀 수 있게 해주는 장치다. Ramda의 `R.__`, 직접 구현 시 흔히 쓰는 `_` 같은 심볼이 그 예다. 예를 들어 `divide(_, 2)`를 절반 함수로 쓰고 싶을 때 필요하다. placeholder를 지원하려면 인자를 배열로 모아두고 호출 시점마다 placeholder가 남아 있는지 훑어서 채워나가는 로직이 필요하다. 구현이 조금 복잡해지지만 한 번 만들어두면 두고두고 쓴다.

```javascript
const PLACEHOLDER = Symbol('_');

const curry = (fn, arity = fn.length) => {
    const curried = (...args) => {
        const filled = args.filter(a => a !== PLACEHOLDER).length;
        if (filled >= arity) return fn(...args);
        return (...next) => {
            const merged = [];
            let j = 0;
            for (let i = 0; i < args.length; i++) {
                merged.push(args[i] === PLACEHOLDER && j < next.length ? next[j++] : args[i]);
            }
            while (j < next.length) merged.push(next[j++]);
            return curried(...merged);
        };
    };
    return curried;
};

const divide = curry((a, b) => a / b);
const half = divide(PLACEHOLDER, 2);
half(10); // 5
```

포인트프리를 과하게 밀면 오히려 읽기 어려워지는 지점이 온다. 중첩 합성이 3단계를 넘어가면 인자 이름이 없어서 디버거로 찍어보기 전까지 무엇이 흐르는지 감이 안 온다. 팀 코드에서는 합성 2~3단계까지만 포인트프리로 쓰고, 그 위로는 이름 있는 람다를 섞어 쓰는 편이 장기적으로 덜 고생한다.

## 함수 합성 심화

기본 문서의 compose/pipe는 reduce/reduceRight로 간단히 구현한 형태다. 실제로 쓸 때는 여러 변형이 필요하다. 첫째는 다중 인자 지원인데, 일반적으로 파이프라인은 단일 값을 받아 단일 값을 돌려주는 함수만 쓸 수 있다. 그래서 첫 번째 함수만 가변 인자를 받게 허용하는 구현을 쓰기도 한다.

```javascript
const pipe = (...fns) => (...args) =>
    fns.slice(1).reduce((v, f) => f(v), fns[0](...args));
```

둘째는 비동기 합성이다. 파이프 중간에 Promise를 반환하는 함수가 끼면 단순 pipe는 Promise 객체를 다음 함수에 넘겨버려 엉망이 된다. `pipeAsync`는 각 단계를 `await`으로 풀어 순차 실행한다.

```javascript
const pipeAsync = (...fns) => (x) =>
    fns.reduce((acc, f) => acc.then(f), Promise.resolve(x));
```

여기서 놓치기 쉬운 게 에러 전파 방식이다. pipeAsync 중간 어느 단계에서 throw가 발생하면 이후 단계는 전부 건너뛰고 최종 Promise가 reject된다. 이 동작은 직관적이지만 문제는 스택 트레이스다. `await` 체인 내부에서 발생한 에러는 어느 단계에서 터졌는지 식별하기 어렵다. 합성에 넘기는 함수에서 `Error` 생성 시 단계 이름을 메시지에 박아두거나, 각 단계를 감싸는 데코레이터를 두는 편이 실무에서 훨씬 편하다.

```javascript
const tagStep = (name, fn) => async (x) => {
    try {
        return await fn(x);
    } catch (e) {
        e.message = `[${name}] ${e.message}`;
        throw e;
    }
};

const run = pipeAsync(
    tagStep('fetchUser', fetchUser),
    tagStep('loadOrders', loadOrders),
    tagStep('summarize', summarize),
);
```

동기/비동기가 섞인 경우에는 pipeAsync가 일관성 면에서 낫다. 동기 함수의 반환값도 `.then()` 한 단계를 거치면서 Promise로 감싸지기 때문에 어느 단계에서 `await`이 생길지 호출자가 신경 쓸 필요가 없다. 대신 동기 구간도 마이크로태스크 큐를 한 번 타기 때문에 병목이 될 만큼 작은 연산을 반복하면 체감된다.

## 트랜스듀서

`arr.map(f).filter(g).map(h)` 형태의 체인은 읽기 좋지만 중간 배열을 매번 만든다. 100만 개짜리 배열이면 map에서 100만 개, filter에서 대략 수십만 개, 다시 map에서 비슷한 수의 배열을 만든다. GC 압박이 올라가고 캐시 미스도 늘어난다. 트랜스듀서(transducer)는 이 문제를 풀기 위한 기법이다. map/filter/reduce의 본질이 "누산기에 어떻게 새 값을 얹을지"라는 공통 구조를 가지는 점을 이용한다.

reducer를 `(acc, x) => acc`로 통일하고, map과 filter를 reducer를 변환하는 함수로 다시 정의한다. 이렇게 정의된 변환들을 합성하면 체인 전체가 하나의 reduce로 통합되어 단일 순회로 끝난다. 중간 배열이 하나도 생기지 않는다.

```javascript
const mapT = (f) => (reducer) => (acc, x) => reducer(acc, f(x));
const filterT = (pred) => (reducer) => (acc, x) => pred(x) ? reducer(acc, x) : acc;

const compose = (...fns) => x => fns.reduceRight((v, f) => f(v), x);

const xf = compose(
    mapT(x => x * 2),
    filterT(x => x > 10),
    mapT(x => x + 1),
);

const push = (acc, x) => (acc.push(x), acc);
const result = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].reduce(xf(push), []);
```

합성 순서가 왼쪽에서 오른쪽으로 적용되는 것처럼 보이는 게 헷갈리는 포인트다. `compose`는 오른쪽부터 실행되지만, 트랜스듀서는 reducer를 감싸는 방식이라 외곽에서 reducer로 값이 흘러들어가는 순서가 뒤집힌다. 결과적으로 `compose(mapT(f), filterT(g))`는 데이터 관점에서 먼저 f를 적용하고 그다음 g로 거르는 동작이 된다. 직관과 어긋나서 `pipe`로 쓰는 팀도 있는데, 정석은 compose 쪽이고 Ramda도 그쪽을 쓴다.

성능 이득은 데이터 크기가 클수록, 체인이 길수록 커진다. 배열 수천 개, 체인 두세 단계 수준에서는 일반 체인과 차이가 유의미하지 않다. 오히려 트랜스듀서가 함수 호출 오버헤드 때문에 소폭 느리다. 파일 파싱처럼 수십만 행을 처리하는 경로에서 도입하는 게 맞다. 무조건 이득이라는 설명은 사실이 아니다.

## Functor, Applicative, Monad 법칙과 구현

`map`을 가진 자료구조를 Functor라고 부른다. 자바스크립트 배열은 이미 Functor다. Functor에는 두 법칙이 있다. 항등성 `x.map(v => v)`는 `x`와 같아야 하고, 합성 `x.map(f).map(g)`는 `x.map(v => g(f(v)))`와 같아야 한다. 법칙을 지키지 않으면 추상화의 장점이 사라진다. 직접 타입을 만들 때 이 법칙을 의식적으로 지키는지 테스트해야 한다.

Applicative는 "박스 안에 든 함수"를 "박스 안에 든 값"에 적용할 수 있는 `ap`를 추가한다. `Maybe.just(f).ap(Maybe.just(x))`가 `Maybe.just(f(x))`가 되는 구조다. 인자가 여러 개인 함수를 Maybe에 들어 있는 여러 값에 동시에 적용하고 싶을 때 쓴다.

Monad는 Applicative에 `chain`(`flatMap`)을 더한다. `map`은 박스 안의 값을 변환해 다시 박스에 담고, `chain`은 박스 안의 값을 변환한 결과가 이미 박스일 때 그 박스를 납작하게 펴준다. 이게 없으면 `Maybe<Maybe<T>>` 같은 중첩이 생긴다. 비동기로 치면 Promise의 `.then`이 실질적으로 `map`과 `chain`을 겸하는 메서드다. 콜백이 Promise를 반환하면 자동으로 펴주기 때문이다.

```javascript
const Either = {
    right: (v) => ({
        map: (f) => Either.right(f(v)),
        chain: (f) => f(v),
        ap: (other) => other.map(v),
        fold: (_, r) => r(v),
    }),
    left: (e) => ({
        map: () => Either.left(e),
        chain: () => Either.left(e),
        ap: () => Either.left(e),
        fold: (l) => l(e),
    }),
};

const parseJSON = (s) => {
    try { return Either.right(JSON.parse(s)); }
    catch (err) { return Either.left(err); }
};

const getField = (key) => (obj) =>
    obj[key] != null ? Either.right(obj[key]) : Either.left(new Error(`missing ${key}`));

parseJSON('{"user":{"id":7}}')
    .chain(getField('user'))
    .chain(getField('id'))
    .fold(err => `error: ${err.message}`, id => `id=${id}`);
```

Task는 Promise의 FP 버전이다. Promise와 다른 점은 생성 시점에 실행되지 않는다는 것이다. Task는 "언제 실행할지 아직 모르는 비동기 계산"의 값이다. `fork`를 호출하기 전까지는 아무 일도 일어나지 않는다. 이 지연 실행 덕분에 합성은 순수한 상태로 유지되고, 실행 시점을 경계로 몰아 부수효과를 격리할 수 있다.

```javascript
const Task = (computation) => ({
    fork: computation,
    map: (f) => Task((reject, resolve) => computation(reject, v => resolve(f(v)))),
    chain: (f) => Task((reject, resolve) =>
        computation(reject, v => f(v).fork(reject, resolve))),
});
```

`traverse`는 "컨테이너의 구조를 뒤집는" 연산이다. `[Either<A>, Either<B>]` 형태가 있을 때 이를 `Either<[A, B]>`로 바꾼다. 검증 파이프라인에서 자주 쓴다. 여러 필드에 대한 검증 결과가 각각 Either로 나오는데, 하나라도 실패하면 전체를 실패로 보고 성공일 때만 값 배열을 꺼내 쓰고 싶을 때 필요하다. 직접 구현해도 크게 어렵지 않지만 Applicative 타입에 맞춰 올바르게 짜려면 까다롭다. 이 수준까지 가면 Ramda나 Folktale을 쓰는 게 낫다.

## 게으른 평가와 제너레이터

배열 메서드는 eager하다. `arr.map(f).find(pred)`를 쓰면 find에서 조건이 맞는 첫 요소를 찾았더라도 map은 이미 배열 전체를 만들어놨다. 제너레이터를 쓰면 이걸 lazy하게 바꿀 수 있다. `yield`는 값을 요청받을 때만 다음 계산을 수행하기 때문에 소비자가 멈추면 생산자도 멈춘다.

```javascript
function* map(iter, f) {
    for (const x of iter) yield f(x);
}

function* filter(iter, pred) {
    for (const x of iter) if (pred(x)) yield x;
}

function* naturals() {
    let n = 1;
    while (true) yield n++;
}

const take = (iter, n) => {
    const out = [];
    for (const x of iter) {
        if (out.length >= n) break;
        out.push(x);
    }
    return out;
};

const firstFiveSquaredEvens = take(
    filter(map(naturals(), x => x * x), x => x % 2 === 0),
    5,
);
```

무한 시퀀스를 다룰 수 있다는 점이 제너레이터 파이프라인의 핵심이다. 배열로는 `naturals()` 같은 걸 표현할 수 없지만 제너레이터로는 자연스럽다. 대신 제너레이터는 한 번 소비하면 끝이다. `for...of`를 두 번 돌리면 두 번째에는 빈 결과가 나온다. 재사용하려면 매번 새로 호출해야 한다. 이 점을 의식하지 못하고 함수 인자로 넘기다가 "어디선가 조용히 비어 있는" 현상을 겪는 경우가 많다.

성능 면에서 lazy가 무조건 유리한 건 아니다. 제너레이터는 호출마다 상태 저장/복원 비용이 들어서, 전체를 훑어야 하는 경우에는 일반 배열 체인보다 느리다. `find`처럼 조기 종료 가능성이 있거나, 무한 시퀀스처럼 전체를 구체화할 수 없는 경우에만 이득이다.

## Lens로 불변 중첩 갱신

깊은 객체를 불변으로 바꾸려고 중첩 스프레드를 쓰다 보면 지옥이 된다.

```javascript
const updated = {
    ...state,
    users: {
        ...state.users,
        [id]: {
            ...state.users[id],
            profile: {
                ...state.users[id].profile,
                address: {
                    ...state.users[id].profile.address,
                    city: 'Busan',
                },
            },
        },
    },
};
```

이 코드는 실수하기 쉽고, 중간에 경로가 하나 잘못되면 얕은 복사가 의도하지 않게 공유된다. Lens는 이 문제를 추상화한다. Lens는 "객체의 특정 위치를 읽고 쓰는 방법을 묶은 값"이다. `view`로 읽고, `set`으로 교체하고, `over`로 변환한다.

```javascript
const lens = (getter, setter) => ({ getter, setter });
const view = (l, obj) => l.getter(obj);
const set = (l, val, obj) => l.setter(val, obj);
const over = (l, f, obj) => l.setter(f(l.getter(obj)), obj);

const lensProp = (key) => lens(
    (o) => o[key],
    (v, o) => ({ ...o, [key]: v }),
);

const lensPath = (path) => lens(
    (o) => path.reduce((acc, k) => acc?.[k], o),
    (v, o) => {
        if (path.length === 0) return v;
        const [head, ...rest] = path;
        return { ...o, [head]: lensPath(rest).setter(v, o?.[head] ?? {}) };
    },
);

const cityLens = lensPath(['users', 7, 'profile', 'address', 'city']);
const updated = set(cityLens, 'Busan', state);
```

두 Lens를 합성해 더 깊은 Lens를 만들 수도 있다. 합성된 Lens에서 `view`를 호출하면 중간 경로가 하나라도 없으면 `undefined`가 나오고, `set`은 중간 객체를 모두 얕은 복사로 새로 만든다. 손으로 스프레드를 쌓던 코드를 경로 리스트 하나로 줄일 수 있다. 성능상으로는 수동 스프레드와 유사하다. 두 방식 모두 경로 상의 객체들을 복사하고, 경로를 벗어난 부분은 참조 공유한다.

Lens 라이브러리로 Ramda가 유명하고, 불변 자료구조에 특화된 Immer를 쓰는 팀도 많다. Immer는 "mutable처럼 쓰면 내부적으로 불변 업데이트"를 해주는 방식이라 Lens와 접근법이 다르지만 해결하려는 문제가 같다. Redux Toolkit이 내부적으로 Immer를 쓰는 이유도 중첩 상태 업데이트의 피로를 덜기 위해서다.

## 재귀와 꼬리호출, 트램폴린

FP에서는 반복 대신 재귀가 자연스럽게 쓰인다. 문제는 자바스크립트 엔진, 특히 V8이 꼬리호출 최적화(TCO)를 지원하지 않는다는 점이다. ES2015 스펙에는 strict mode에서 TCO를 지원하라고 명시되어 있지만 V8은 구현하지 않기로 결정했고 앞으로도 계획이 없다. Safari의 JavaScriptCore만 일부 구현했다. 그래서 재귀 깊이가 커지는 순간 `RangeError: Maximum call stack size exceeded`를 만난다.

스택을 쌓지 않고 재귀 구조를 그대로 유지하는 기법이 트램폴린(trampoline)이다. 재귀 함수가 즉시 결과를 반환하는 대신 "다음 호출을 나타내는 thunk"를 반환하도록 바꾼다. 트램폴린 러너가 while 루프로 thunk를 계속 꺼내 실행하면서 스택을 풀어 쓴다.

```javascript
const trampoline = (fn) => (...args) => {
    let result = fn(...args);
    while (typeof result === 'function') result = result();
    return result;
};

const sumTo = trampoline(function rec(n, acc = 0) {
    if (n === 0) return acc;
    return () => rec(n - 1, acc + n);
});

sumTo(1_000_000); // 스택 오버플로 없음
```

트램폴린의 단점은 모든 재귀 호출이 클로저 생성과 함수 호출을 거치기 때문에 일반 반복보다 느리다는 것이다. 평소에는 for 루프로 충분하고, 재귀 구조가 의미상 자연스러운 경우(트리 순회 등)에만 선택한다. 실무에서는 재귀 깊이가 예측 가능한지 먼저 확인하고, 깊이가 입력에 비례해서 무제한으로 커질 수 있는 자리에만 트램폴린이나 명시적 스택 기반 반복을 쓴다.

## 부수효과 격리

함수형 코드의 목적 중 하나는 부수효과의 발생 지점을 한곳으로 모으는 것이다. IO 모나드는 부수효과가 있는 계산을 "아직 실행되지 않은 값"으로 감싼다. Task가 비동기 버전이라면 IO는 동기 버전에 가깝다.

```javascript
const IO = (effect) => ({
    run: effect,
    map: (f) => IO(() => f(effect())),
    chain: (f) => IO(() => f(effect()).run()),
});

const readEnv = (key) => IO(() => process.env[key]);
const log = (msg) => IO(() => console.log(msg));

const program = readEnv('NODE_ENV')
    .chain(env => log(`env=${env}`));

program.run();
```

`program`을 만들어 전달하는 동안에는 부수효과가 발생하지 않는다. `run`을 호출하는 엔트리포인트에서만 실제 I/O가 일어난다. 이 분리 덕분에 내부 로직은 테스트하기 쉽고, 합성도 순수하다. 현실적으로는 이 스타일을 팀 코드 전체에 강제하기 쉽지 않다. 작은 내부 유틸이나 특히 반복되는 비동기 합성 구간에 선택적으로 쓴다. React 쪽에서 Redux-Observable이나 Redux-Saga가 하는 일이 비슷한 격리를 프레임워크 층에서 대신해주는 것으로 볼 수 있다.

## 메모이제이션 심화

기본 문서의 `JSON.stringify(args)`로 키를 만드는 방식은 잘 동작하는 듯 보이지만 실무에서 금방 문제가 드러난다. 객체 키 순서에 따라 다른 문자열이 나오고, Date나 Map처럼 `JSON.stringify`가 제대로 처리 못 하는 값이 섞이면 망가진다. 함수가 인자로 들어오면 `"[object Function]"`처럼 구별 불가능한 문자열이 된다.

인자가 객체 참조라면 WeakMap을 키로 쓰는 게 자연스럽다. WeakMap은 키로 쓴 객체가 다른 곳에서 참조되지 않으면 GC가 엔트리를 회수한다. 메모이제이션이 메모리 누수를 일으키는 전형적인 문제를 덜어준다.

```javascript
const memoizeWeak = (fn) => {
    const cache = new WeakMap();
    return (obj) => {
        if (cache.has(obj)) return cache.get(obj);
        const result = fn(obj);
        cache.set(obj, result);
        return result;
    };
};
```

인자가 원시값이거나 여러 개라면 WeakMap을 못 쓴다. 이때는 Map 기반 LRU를 쓴다. 캐시 크기 상한을 두고, 꽉 찼을 때 가장 오래된 항목을 버린다. Map은 삽입 순서를 유지하기 때문에 `map.keys().next().value`로 가장 오래된 키를 얻을 수 있다.

```javascript
const memoizeLRU = (fn, max = 100) => {
    const cache = new Map();
    return (...args) => {
        const key = args.length === 1 ? args[0] : JSON.stringify(args);
        if (cache.has(key)) {
            const v = cache.get(key);
            cache.delete(key);
            cache.set(key, v);
            return v;
        }
        const result = fn(...args);
        cache.set(key, result);
        if (cache.size > max) cache.delete(cache.keys().next().value);
        return result;
    };
};
```

메모이제이션이 성립하는 전제는 참조 투명성이다. 같은 입력에 같은 출력을 보장해야 한다. 내부에서 Date를 읽거나 외부 상태를 참조하는 함수를 메모이즈하면 캐시된 오래된 값을 계속 돌려주게 된다. 실무에서는 "순수 함수로 만들어놓고 나중에 외부 조회를 추가"하면서 메모이즈 유효성이 깨지는 경우가 흔하다. 캐시를 단 함수에 수정이 들어오면 캐시 가정이 유지되는지 다시 확인하는 습관이 필요하다.

## 성능 함정

`arr.map(f).filter(g).reduce(h, init)` 같은 체인은 작은 배열에서는 거의 공짜다. 그러나 큰 배열에서는 단순 for 루프보다 두세 배 느린 경우가 드물지 않다. 이유는 세 가지다. 첫째, 중간 배열 생성. 둘째, 배열 메서드의 함수 호출 오버헤드. 셋째, V8 인라인 캐시 관점에서 배열 메서드 내부의 콜백 호출 사이트가 모놀리픽이 아닐 때 폴리모픽으로 바뀌어 최적화가 덜 된다.

성능이 중요한 경로에서는 다음 중 하나를 택한다. for 루프로 전개, 트랜스듀서 도입, Node.js라면 스트림 활용. 조기 최적화는 피해야 하지만, 요청당 수천 번 돌아가는 핫패스라면 측정한 뒤 for 루프가 답일 때가 있다. 일반 비즈니스 로직에서는 배열 메서드의 가독성 이득이 성능 손실보다 훨씬 크다.

클로저로 만든 함수는 상위 스코프의 변수들을 붙잡고 있기 때문에 의도보다 오래 메모리를 점유할 수 있다. 특히 "큰 객체를 캡처한 채 어딘가에 저장되는 콜백"이 위험하다. 이벤트 리스너에 등록된 클로저가 큰 DOM 참조를 물고 있는 경우, 리스너를 제거해도 개발자가 별도 참조를 남겨두면 GC가 회수하지 못한다. 디버그할 때는 Chrome DevTools의 Memory 탭에서 Retainers를 따라 올라가며 누가 붙잡고 있는지 확인한다.

GC 압박은 map/filter/reduce를 자주 호출할수록 커진다. 매 호출마다 함수 객체, 중간 배열, 새 객체들이 생성된다. 부하 테스트에서 "요청 지연이 예고 없이 튀는 스파이크"가 보이면 GC를 의심한다. `--trace-gc`를 붙여 패턴을 본 뒤, 핫패스의 할당을 줄이는 방향으로 수정한다. Node.js에서 FP 스타일을 적극적으로 쓰되 미들웨어의 가장 뜨거운 지점만 명령형으로 바꾸는 절충이 흔한 답이다.

## 라이브러리 vs 직접 구현

Ramda와 Lodash/fp는 비슷한 문제를 풀지만 설계 철학이 다르다. Ramda는 처음부터 커링, data-last 인자 순서, 포인트프리에 맞춰 만들어졌다. Lodash/fp는 기존 Lodash를 감싸 data-last와 자동 커링을 입힌 래퍼다. Ramda 쪽이 API가 일관되지만, 기존 Lodash 지식을 이어서 쓰고 싶으면 후자가 낫다.

직접 구현하면 번들 크기와 학습 곡선을 아낄 수 있고 프로젝트 스타일에 맞게 튜닝할 수 있다. curry, compose, pipe, pipeAsync 정도는 20~30줄로 충분하다. 반대로 Lens, Transducer, 모나드 변형까지 갈 거라면 라이브러리를 쓰는 게 낫다. 법칙을 지키면서 성능까지 챙기는 구현은 만만치 않다.

번들 크기가 문제인 웹 프런트라면 Ramda는 tree-shaking이 덜 친화적이라 커지기 쉽다. 요즘은 Remeda처럼 ESM/TS 친화적인 대안이 떠오르고 있다.

## TypeScript에서 함수 합성 타입 추론의 한계

TypeScript로 `pipe`, `compose`를 타이핑하면 특정 개수까지는 제네릭 오버로딩으로 추론이 되지만, 임의 개수의 함수를 받는 경우 타입 추론이 무너진다.

```typescript
function pipe<A, B>(f1: (a: A) => B): (a: A) => B;
function pipe<A, B, C>(f1: (a: A) => B, f2: (b: B) => C): (a: A) => C;
function pipe<A, B, C, D>(f1: (a: A) => B, f2: (b: B) => C, f3: (c: C) => D): (a: A) => D;
function pipe(...fns: Function[]): Function { /* ... */ }
```

Ramda 타입 정의도 이런 식으로 10~20개쯤 오버로드를 미리 깔아둔다. 그 이상이 필요하면 `any`로 추락한다. 최신 TypeScript의 variadic tuple types를 활용하면 어느 정도 일반화가 가능하지만 여전히 에지 케이스에서 깨진다. 함수 합성을 타입 안전하게 유지하려면 합성 길이를 제한하거나, Effect-TS 같은 프레임워크가 제공하는 검증된 추론을 빌려 쓰는 편이 현실적이다.

커링된 함수의 반환 타입을 정확히 추론하는 것도 까다롭다. 특히 placeholder가 섞이면 타입 시스템으로 표현하기 사실상 어렵다. Ramda의 타입 정의가 placeholder 호출에서 `any`로 떨어지는 걸 확인할 수 있다. 실무에서는 포인트프리의 타입 안정성을 포기하는 대신 호출부에서 명시적 애노테이션을 걸어두는 타협을 한다.

## 실무 트러블슈팅 기록

### 중첩 스프레드 깊이 문제

Redux 스토어를 쓰던 프로젝트에서 상태 깊이가 5단계쯤 되었고, 리듀서마다 스프레드가 5중첩으로 쌓여 있었다. 새로운 기능에서 4번째 단계 객체를 업데이트하는 코드를 작성했는데, 다른 브랜치의 참조가 예전 값을 가리키는 버그가 발생했다. 원인은 중간 단계 하나에서 `...prev.child`가 누락되어 이전 객체의 자식들을 덮어쓴 것이었다. 육안 리뷰에서 놓치기 쉬운 종류의 실수다. 이 사건 이후 팀에서 Immer를 도입했고, 해당 종류의 버그가 사실상 사라졌다. Lens를 직접 만들어 쓰는 방안도 검토했으나 학습 비용과 타입 안정성 때문에 Immer로 갔다.

### async 합성 에러 전파

Node.js 배치 작업에서 `pipeAsync(parse, validate, transform, persist)` 형태로 파이프라인을 엮었다. 프로덕션에서 간헐적으로 "Cannot read property 'id' of undefined"가 로그에 남았는데, 스택 트레이스만으로는 어느 단계에서 발생했는지 파악이 어려웠다. 각 단계 함수를 `tagStep('parse', parse)`처럼 감싸서 에러 메시지에 단계 이름을 붙이자 즉시 위치가 드러났다. transform 단계에서 API 응답 캐시가 빈 객체를 돌려주고 있었고, validate가 이 경우를 통과시키고 있었다. validate 강화와 에러 태깅을 같이 배포하면서 해결됐다. 비동기 합성을 도입할 때는 반드시 단계별 에러 컨텍스트를 보강해두는 습관이 필요하다.

### this 바인딩 소실

FP 스타일로 클래스 메서드를 pipe에 넣으면 거의 항상 깨진다. `pipe(parser.parse, validator.validate)`를 쓰면 parse와 validate가 원래 인스턴스에서 분리되어 this가 undefined가 된다. 처음 겪으면 "parse는 되는데 validate에서 갑자기 죽는" 형태로 나타나 한참 디버깅한다. 해결책은 세 가지다. 메서드를 클래스 필드 화살표 함수로 정의해 항상 묶인 상태로 만들거나, `parser.parse.bind(parser)`로 명시적으로 묶거나, 애초에 클래스 대신 평범한 함수 모듈로 설계하는 방법이다. FP와 클래스 기반 OOP를 섞는 프로젝트에서는 이 혼란이 반복적으로 발생하므로 팀 컨벤션 수준에서 한쪽 스타일로 정렬하는 게 스트레스가 덜하다.

## 참고 자료

- [Mostly Adequate Guide to Functional Programming](https://github.com/MostlyAdequate/mostly-adequate-guide)
- [Ramda Documentation](https://ramdajs.com/docs/)
- [Transducers in JavaScript (Rich Hickey 원본 발표 번역본)](https://clojure.org/reference/transducers)
- [V8 and Tail Call Optimization](https://v8.dev/blog/modern-javascript)
- [Immer Documentation](https://immerjs.github.io/immer/)
