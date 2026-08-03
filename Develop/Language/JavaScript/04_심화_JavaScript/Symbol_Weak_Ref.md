---
title: Symbol, WeakRef, FinalizationRegistry
tags: [javascript, symbol, weakref, finalizationregistry, memory-management, es2021, iterator, well-known-symbol]
updated: 2026-08-03
---

# Symbol, WeakRef, FinalizationRegistry

## Symbol

Symbol은 ES2015에서 추가된 원시 타입이다. `Symbol()`을 호출할 때마다 전역에서 고유한 값이 하나 생성된다.

```javascript
const a = Symbol('label');
const b = Symbol('label');
a === b; // false — 설명 문자열이 같아도 값은 다르다
typeof a; // 'symbol'
```

주로 객체 프로퍼티 키로 쓴다. 문자열 키와 달리 `for...in`이나 `Object.keys()`에 나타나지 않아서, 라이브러리 내부 상태를 외부에 노출하지 않고 보관할 때 유용하다.

```javascript
const _private = Symbol('private');

class Connection {
  constructor() {
    this[_private] = { socket: null };
  }
  connect() {
    this[_private].socket = createSocket();
  }
}

const conn = new Connection();
Object.keys(conn);              // []
conn[_private];                 // { socket: ... } — 키를 알면 접근은 된다
JSON.stringify(conn);           // '{}' — Symbol 키는 직렬화에서 빠진다
Object.getOwnPropertySymbols(conn); // [Symbol(private)] — 이걸로 조회 가능
```

Symbol 키는 완전한 은닉이 아니다. `Object.getOwnPropertySymbols()`로 노출된다. 진짜 프라이빗 상태가 필요하면 ES2022의 `#field`를 쓰는 게 낫다.

## Symbol.for() / Symbol.keyFor()

`Symbol()`은 호출마다 새 Symbol을 만든다. 모듈 경계나 iframe, Node.js의 여러 require() 호출 간에 같은 Symbol을 공유해야 할 때는 전역 레지스트리를 쓴다.

```javascript
const key1 = Symbol.for('app.userId');
const key2 = Symbol.for('app.userId');
key1 === key2; // true — 같은 키 문자열이면 같은 Symbol을 반환

// 역방향 조회
Symbol.keyFor(key1);             // 'app.userId'
Symbol.keyFor(Symbol('local'));  // undefined — 레지스트리에 등록되지 않은 Symbol
```

전역 레지스트리는 런타임 전체가 공유한다. 브라우저라면 탭 단위, Node.js라면 프로세스 단위다. iframe끼리도 공유된다.

키 이름 충돌에 주의해야 한다. 여러 라이브러리가 `Symbol.for('id')`처럼 짧은 키를 쓰면 서로 같은 Symbol을 가리키게 된다. 라이브러리를 배포할 때는 네임스페이스를 붙여야 한다.

```javascript
// 충돌 위험
Symbol.for('id');

// 네임스페이스로 분리
Symbol.for('mylib.v2.userId');
```

내부 상태 보관 목적으로 `Symbol.for()`를 쓰는 건 잘못된 선택이다. 전역 레지스트리에 등록된 Symbol은 누구나 같은 키로 접근할 수 있어서, 접근 차단 효과가 없다.

## Well-known Symbol

JavaScript 엔진이 특정 동작을 위해 미리 예약해둔 Symbol이다. 객체에 이 키로 메서드를 정의하면 언어가 해당 동작을 그 메서드로 위임한다.

### Symbol.iterator

`for...of`, 스프레드 문법, 구조 분해 할당이 내부적으로 `Symbol.iterator`를 호출한다.

```javascript
class Range {
  constructor(start, end) {
    this.start = start;
    this.end = end;
  }

  [Symbol.iterator]() {
    let current = this.start;
    const end = this.end;
    return {
      next() {
        if (current <= end) {
          return { value: current++, done: false };
        }
        return { value: undefined, done: true };
      }
    };
  }
}

const range = new Range(1, 5);
[...range];                           // [1, 2, 3, 4, 5]
for (const n of range) { /* ... */ } // 1, 2, 3, 4, 5
const [first, ...rest] = range;       // first=1, rest=[2,3,4,5]
```

제너레이터 함수로 구현하면 이터레이터 객체를 직접 만들지 않아도 된다.

```javascript
class Range {
  constructor(start, end) { this.start = start; this.end = end; }

  *[Symbol.iterator]() {
    for (let i = this.start; i <= this.end; i++) yield i;
  }
}
```

제너레이터가 반환하는 객체는 `[Symbol.iterator]() { return this; }`를 이미 가지고 있어서 이터러블이기도 한 이터레이터가 된다. 직접 구현할 때 이 메서드를 빠뜨리면 일부 API에서 문제가 생긴다.

### Symbol.asyncIterator

`for await...of`는 `Symbol.asyncIterator`를 호출한다. 비동기 데이터 스트림을 순회할 때 쓴다.

```javascript
class AsyncQueue {
  #items = [];
  #resolvers = [];

  push(item) {
    if (this.#resolvers.length > 0) {
      this.#resolvers.shift()(item);
    } else {
      this.#items.push(item);
    }
  }

  async *[Symbol.asyncIterator]() {
    while (true) {
      if (this.#items.length > 0) {
        yield this.#items.shift();
      } else {
        yield new Promise(resolve => this.#resolvers.push(resolve));
      }
    }
  }
}

const queue = new AsyncQueue();
setTimeout(() => queue.push('first'), 100);
setTimeout(() => queue.push('second'), 200);

for await (const item of queue) {
  console.log(item); // 'first', 'second', ...
}
```

Node.js의 `stream.Readable`은 `Symbol.asyncIterator`를 구현해서 `for await...of`로 읽을 수 있다.

```javascript
import { createReadStream } from 'fs';

const stream = createReadStream('./large-file.txt', { encoding: 'utf-8' });
for await (const chunk of stream) {
  process(chunk);
}
```

### Symbol.toPrimitive

객체가 원시 타입으로 변환될 때 호출된다. hint는 `'number'`, `'string'`, `'default'` 세 가지다.

```javascript
class Money {
  constructor(amount, currency) {
    this.amount = amount;
    this.currency = currency;
  }

  [Symbol.toPrimitive](hint) {
    if (hint === 'number') return this.amount;
    if (hint === 'string') return `${this.amount} ${this.currency}`;
    return this.amount; // default — 산술 연산이나 비교에서 발생
  }
}

const price = new Money(100, 'USD');
+price;       // 100 — hint: 'number'
`${price}`;   // '100 USD' — hint: 'string'
price + 50;   // 150 — hint: 'default'
price > 50;   // true — hint: 'number'
```

`Symbol.toPrimitive`가 없으면 `valueOf()`와 `toString()`을 순서대로 시도한다. `Symbol.toPrimitive`가 있으면 이 두 메서드는 무시된다.

`'default'` hint는 `==` 비교나 `+` 연산에서 발생한다. 대부분의 경우 `'number'`와 같게 처리해도 무방하다.

### Symbol.toStringTag

`Object.prototype.toString.call()`이 반환하는 태그 문자열을 지정한다.

```javascript
class HttpResponse {
  get [Symbol.toStringTag]() {
    return 'HttpResponse';
  }
}

const res = new HttpResponse();
Object.prototype.toString.call(res); // '[object HttpResponse]'
```

일부 라이브러리는 `instanceof` 대신 `Object.prototype.toString`으로 타입을 판별한다. 다른 라이브러리와 통합할 때 이 값이 맞지 않아서 처리를 건너뛰는 버그가 발생하는 경우가 있다.

### Symbol.hasInstance

`instanceof` 연산자 동작을 재정의한다.

```javascript
class EvenNumber {
  static [Symbol.hasInstance](value) {
    return typeof value === 'number' && value % 2 === 0;
  }
}

2 instanceof EvenNumber; // true
3 instanceof EvenNumber; // false
```

자주 쓰는 패턴은 아니다. `instanceof`를 범용 타입 판별에 쓰는 코드베이스에서 duck typing 방식으로 확장할 때 유용하다.

## WeakRef

객체에 대한 약한 참조(weak reference)를 만든다. 약한 참조는 GC가 객체를 수집하는 것을 막지 않는다.

```javascript
let target = { name: 'important data' };
const ref = new WeakRef(target);

ref.deref(); // { name: 'important data' } — 아직 살아있으면 반환
target = null; // 강한 참조 제거

// GC가 수집한 뒤에는
ref.deref(); // undefined
```

`deref()` 결과를 두 번 이상 호출해서 쓰는 건 위험하다.

```javascript
// 잘못된 방식
if (ref.deref()) {
  doSomething(ref.deref()); // 첫 번째와 두 번째 deref 사이에 GC될 수 있다
}

// 올바른 방식
const obj = ref.deref();
if (obj) {
  doSomething(obj); // 지역 변수에 담으면 이 스코프 안에서 GC되지 않는다
}
```

## FinalizationRegistry

GC가 객체를 수집할 때 콜백을 실행한다. 수집 타이밍은 GC에 달려있어서 콜백이 언제 호출될지 보장이 없다.

```javascript
const registry = new FinalizationRegistry((heldValue) => {
  console.log(`수집됨: ${heldValue}`);
});

let obj = { data: 'important' };
registry.register(obj, 'my-object-label'); // 두 번째 인자가 콜백에 전달된다

obj = null; // 강한 참조 해제
// GC가 실행되면 언젠가 '수집됨: my-object-label' 출력
```

`register()`의 세 번째 인자는 해제 토큰이다. `unregister()`로 콜백 등록을 취소할 때 쓴다.

```javascript
const token = {};
registry.register(obj, 'label', token);
registry.unregister(token); // 이 이후에는 콜백이 호출되지 않는다
```

콜백 안에서 등록한 객체에 접근할 수 없다. 이미 수집된 객체다. `heldValue`에 담아서 전달받은 값만 쓸 수 있다.

## WeakRef + FinalizationRegistry 캐시 패턴

Map 기반 캐시는 참조를 강하게 잡아서 GC가 캐시된 객체를 수집하지 못한다. WeakRef로 캐시를 구현하면 메모리 압박이 생길 때 GC가 캐시 항목을 수집할 수 있다.

```javascript
class WeakCache {
  #cache = new Map();
  #registry = new FinalizationRegistry((key) => {
    const ref = this.#cache.get(key);
    if (ref && !ref.deref()) {
      this.#cache.delete(key);
    }
  });

  set(key, value) {
    this.#cache.set(key, new WeakRef(value));
    this.#registry.register(value, key);
  }

  get(key) {
    const ref = this.#cache.get(key);
    if (!ref) return undefined;
    const value = ref.deref();
    if (!value) {
      this.#cache.delete(key); // 수집됐으면 즉시 정리
      return undefined;
    }
    return value;
  }

  has(key) {
    return this.get(key) !== undefined;
  }
}
```

이 패턴에는 한계가 있다.

`#cache`에 죽은 WeakRef 항목이 잠시 남아있을 수 있다. FinalizationRegistry 콜백이 아직 실행되기 전에 `get()`을 호출하면 null 체크로 걸러내고 즉시 정리하지만, `size`를 신뢰할 수 없다.

GC가 언제 수집할지 모르기 때문에 캐시 히트율이 예측 불가하다. TTL 기반 캐시와 조합해서 쓰는 경우가 많다.

DOM 요소를 키로 쓰는 캐시라면 WeakMap이 더 적합하다.

```javascript
class DOMCache {
  #cache = new WeakMap(); // DOM 요소가 사라지면 자동으로 정리된다

  compute(element, fn) {
    if (this.#cache.has(element)) {
      return this.#cache.get(element);
    }
    const result = fn(element);
    this.#cache.set(element, result);
    return result;
  }
}
```

WeakRef가 필요한 경우는 WeakMap/WeakSet으로 해결이 안 될 때다. 주로 객체가 아닌 원시 값을 키로 쓰는 캐시에서 값의 생존 여부를 직접 추적해야 하는 상황이다.

## 주의사항

WeakRef와 FinalizationRegistry는 GC 타이밍을 엔진에 완전히 위임한다. Node.js에서 단위 테스트로 FinalizationRegistry 콜백을 검증하기가 어렵다. `--expose-gc` 플래그로 `global.gc()`를 강제 실행할 수 있지만, 프로덕션 코드에서 이 플래그에 의존해선 안 된다.

TypeScript에서는 `lib`에 `"ES2021"` 이상이 있어야 `WeakRef`와 `FinalizationRegistry` 타입이 잡힌다.

```json
{
  "compilerOptions": {
    "target": "ES2021",
    "lib": ["ES2021"]
  }
}
```

Node.js는 v14.6.0부터 WeakRef와 FinalizationRegistry를 지원한다. 브라우저는 Chrome 84, Firefox 79, Safari 14.1부터 지원한다.
