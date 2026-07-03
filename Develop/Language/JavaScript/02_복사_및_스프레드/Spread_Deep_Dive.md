---
title: Spread 연산자 심화 — 내부 동작과 성능
tags: [language, javascript, spread, iterator, performance, v8, structuredClone]
updated: 2026-06-02
---

# Spread 연산자 심화 — 내부 동작과 성능

기본 사용법은 `Spread.md`에, 실무 패턴은 `Spread & Rest 연산자.md`에 정리돼 있다. 이 문서는 그 뒤에 남는 부분, 즉 명세상 어떻게 동작하는지, V8에서 어떤 비용이 드는지, 그리고 실무에서 발이 걸리는 엣지 케이스만 다룬다. 한 줄 요약: 배열 스프레드는 이터레이터를 돈다, 객체 스프레드는 자체 열거 가능 속성만 복사한다, 둘 다 한 단계 얕다.

## 1. 배열 Spread는 이터레이터를 돈다

`[...x]`가 동작하는 조건은 단 하나다. `x[Symbol.iterator]`가 함수여야 한다. 배열인지, 길이가 있는지, 인덱스가 정수인지는 전혀 보지 않는다. 명세상 `ArrayAccumulation`은 `GetIterator(value, sync)`를 호출하고 `IteratorStep`이 `done: true`를 반환할 때까지 `IteratorValue`를 모은다. 그래서 다음 두 결과는 다르다.

```javascript
const arrayLike = { 0: 'a', 1: 'b', length: 2 };

console.log(Array.from(arrayLike));   // ['a', 'b']
console.log([...arrayLike]);          // TypeError: arrayLike is not iterable
```

`Array.from`은 이터러블이 없으면 `length` 기반 fallback을 쓰지만, 스프레드는 그런 길이 없다. `arguments`가 이터러블인 이유는 `arguments[Symbol.iterator]`가 정의돼 있어서지, length가 있어서가 아니다. DOM의 `NodeList`도 마찬가지로 `Symbol.iterator`가 prototype에 들어가서야 스프레드 가능해졌다(2016년 이후 브라우저).

이 특성 때문에 무한 제너레이터에 스프레드를 걸면 그대로 멈춘다.

```javascript
function* naturals() {
  let n = 1;
  while (true) yield n++;
}

// 절대 끝나지 않는다. 페이지가 멈춘다.
const all = [...naturals()];
```

신입 코드 리뷰에서 자주 잡히는 패턴이다. 제너레이터를 받았을 때는 `take(n, gen)` 같은 유한화를 반드시 한 번 끼워야 한다.

### Set·Map의 동작

```javascript
const s = new Set([1, 2, 3]);
const m = new Map([['a', 1], ['b', 2]]);

[...s];  // [1, 2, 3]
[...m];  // [['a', 1], ['b', 2]]
```

`Set.prototype[Symbol.iterator]`는 `values()`를, `Map.prototype[Symbol.iterator]`는 `entries()`를 반환한다. 그래서 Map을 스프레드하면 항상 `[key, value]` 튜플 배열이 나온다. Map을 다시 객체로 만들고 싶다면 `Object.fromEntries(m)`이 정답이지 `{...m}`이 아니다. `{...m}`은 Map 인스턴스의 자체 열거 가능 속성만 보는데, Map이 데이터를 자체 속성으로 들고 있지 않기 때문에 빈 객체가 나온다.

```javascript
const m = new Map([['a', 1]]);
console.log({...m});               // {}
console.log(Object.fromEntries(m)); // { a: 1 }
```

### TypedArray

`Uint8Array`, `Float64Array` 같은 TypedArray도 이터러블이지만 스프레드 결과는 일반 배열이다.

```javascript
const u = new Uint8Array([1, 2, 3]);
const a = [...u];

console.log(a instanceof Uint8Array); // false
console.log(a instanceof Array);      // true
```

큰 TypedArray를 스프레드하면 두 가지 비용이 동시에 발생한다. 한 요소씩 박싱(number로 변환)되고, 결과 배열은 elements kind가 `PACKED_DOUBLE_ELEMENTS` 또는 `PACKED_SMI_ELEMENTS`로 결정된다. 100만 개짜리 `Uint8Array`를 스프레드하면 메모리 사용량이 8배 가량 뛴다. TypedArray 복사는 `u.slice()` 또는 `new Uint8Array(u)`를 써야 한다.

## 2. Object Spread는 자체 열거 가능 속성만 본다

ES2018에서 들어온 Object Rest/Spread Properties 명세를 한 줄로 요약하면 `CopyDataProperties(target, source, excludedNames)`다. 이 추상 연산은 다음 규칙으로 동작한다.

소스에서 키 목록을 가져올 때 `[[OwnPropertyKeys]]`를 호출한다. 즉 자체(own) 속성만 본다. prototype 체인은 무시한다. 그다음 각 키에 대해 `GetOwnPropertyDescriptor`를 호출해서 `enumerable: true`인 것만 골라낸다. 마지막으로 `Get(source, key)`로 값을 읽고 `CreateDataProperty(target, key, value)`로 쓴다.

이 명세에서 실무에 영향을 주는 결론이 네 가지 나온다.

**첫째, prototype은 사라진다.**

```javascript
class User {
  constructor(name) { this.name = name; }
  greet() { return `hi ${this.name}`; }
}

const u = new User('kim');
const copy = { ...u };

console.log(copy.name);     // 'kim'
console.log(copy.greet);    // undefined
console.log(copy instanceof User); // false
```

`greet`은 `User.prototype`에 있지 자체 속성이 아니다. 클래스 인스턴스를 스프레드하면 메서드 없는 plain object가 나온다. Redux store에 클래스 인스턴스를 넣으면 안 되는 이유 중 하나가 이거다. immer를 쓰지 않는 한 spread/assign이 매번 prototype을 떨궈낸다.

**둘째, getter는 그 자리에서 호출된다.**

```javascript
const src = {
  get expensive() {
    console.log('called');
    return computeBigThing();
  }
};

const dst = { ...src }; // 'called' 출력. dst.expensive는 평범한 값 속성.
```

이건 자주 디버깅 거리가 된다. Vue 2의 reactivity는 getter/setter 기반이라 데이터 객체를 무심코 스프레드하면 의도치 않게 의존성 트래킹이 일어나거나, 반대로 반응성이 끊긴다. MobX도 마찬가지다. 라이브러리가 정의한 getter가 있는 객체는 스프레드 대신 라이브러리가 제공하는 복사 함수를 써야 한다.

**셋째, Symbol 키도 자체 + 열거 가능이면 복사된다.**

`Object.assign`과 동일하다. 이건 거의 알려져 있지 않은데, ES2018 명세상 `OwnPropertyKeys`는 string 키와 symbol 키를 모두 반환한다.

```javascript
const sym = Symbol('id');
const src = { name: 'a', [sym]: 1 };
const dst = { ...src };

console.log(dst[sym]); // 1
```

**넷째, non-enumerable 속성과 descriptor는 사라진다.**

```javascript
const src = {};
Object.defineProperty(src, 'hidden', {
  value: 1,
  enumerable: false,
  configurable: true,
  writable: true
});
src.visible = 2;

const dst = { ...src };
console.log(dst); // { visible: 2 }
```

`Object.getOwnPropertyDescriptors` + `Object.defineProperties` 조합을 써야 descriptor까지 보존된다. spread는 항상 `enumerable: true, writable: true, configurable: true`인 data property로 만든다.

## 3. Object.assign과의 세부 차이

겉보기에 `Object.assign(target, source)`와 `{ ...source }`는 같은 일을 한다. 그러나 명세 단계에서 두 군데가 다르다.

### target 변형 여부

`Object.assign`은 첫 인수를 그 자리에서 수정한다. spread는 항상 새 객체를 만든다. 이게 React의 setState 패턴에서 결정적이다.

```javascript
// 잘못된 코드. state를 직접 변형한다.
Object.assign(state, { count: state.count + 1 });

// 올바른 코드. 새 객체.
setState({ ...state, count: state.count + 1 });
```

`Object.assign({}, state, { count: state.count + 1 })`처럼 빈 객체를 첫 인수로 주면 동일해진다. 한 가지 차이는 `__proto__`다. `Object.assign({}, src)`는 `__proto__`를 `Object.prototype`으로 둔다. `{...src}` 역시 마찬가지지만, `{ ...src, __proto__: x }`는 식별자 `__proto__`를 prototype 변경으로 처리하지 않고 일반 속성으로 만든다(객체 리터럴에서 `__proto__:` 형태로 직접 적은 것만 prototype 변경으로 취급).

### 쓰기 방식: defineProperty vs assignment

이게 가장 자주 발을 잡는 차이다.

`Object.assign`은 내부적으로 `Set(target, key, value, target)`을 호출한다. 즉 일반 대입 연산자처럼 동작한다. 그래서 target에 동일 키의 setter가 있으면 setter가 실행된다. target이 그 키에 대해 read-only이거나 setter가 던지면 `Object.assign`도 던진다.

Spread는 `CreateDataProperty`를 호출한다. 이건 `[[DefineOwnProperty]]`를 사용하고 setter를 무시한다. setter가 있던 자리에 그냥 data property를 새로 정의해버린다.

```javascript
const target = {
  set name(v) { console.log('setter:', v); }
};

Object.assign(target, { name: 'a' }); // 'setter: a'
const newObj = { ...target, name: 'b' }; // 호출 없음. newObj.name === 'b' (data property)
```

이게 왜 중요한가. Proxy, Vue의 reactive 객체, Mongoose document처럼 내부에서 setter trap을 거는 객체에 `Object.assign`을 쓰면 trap이 발동한다. spread는 발동하지 않는다. ORM 객체를 spread로 복사하면 dirty tracking이 끊어지는 케이스가 여기서 나온다.

읽기 측은 동일하다. 둘 다 source의 getter를 호출한다.

### 다중 소스 처리 순서

`Object.assign(t, a, b, c)`는 a → b → c 순으로 처리하고, `{...a, ...b, ...c}`도 동일하게 좌→우 순서다. 같은 키가 여러 소스에 있으면 마지막 값이 이긴다. 이 부분은 일치한다.

## 4. V8 성능 특성

스프레드의 성능은 elements kind와 fast path가 있느냐로 갈린다.

### 배열 스프레드

V8은 `[...arr]`에서 arr이 packed array이고 prototype이 손대지 않은 `Array.prototype`이면 fast path를 탄다. 이 fast path는 이터레이터를 진짜로 호출하지 않고 `CopyArrayElements` 같은 내장 헬퍼로 직접 메모리 복사한다. 이 조건이 깨지면(예: `Array.prototype[Symbol.iterator]`를 덮어쓰거나, holey array거나) 일반 이터레이터 경로로 떨어져서 한 요소씩 도는 비용을 낸다.

벤치마크상 packed SMI 배열 1만 개 기준 대략적인 순서는 다음과 같다.

- `arr.slice()` — 가장 빠름. 전용 builtin, 한 번의 메모리 복사
- `[...arr]` — fast path에서는 slice와 5~15% 차이. fast path 깨지면 2~5배 느려짐
- `Array.from(arr)` — slice 대비 20~40% 느림. length 체크와 iterator 분기 비용
- `arr.concat()` — slice와 비슷하거나 약간 느림. 인수 처리 비용
- `[].concat(arr)` — 위와 동일

대용량(10만+)에서 hot path라면 `slice()`가 가장 안전하다. 스프레드는 가독성과 다중 소스 결합을 위해 쓰는 게 맞고, 단순 복사 hot path에는 적합하지 않다.

Holey array(`[1, , 3]`)에 스프레드를 걸면 hole이 `undefined`로 머티리얼라이즈된다. `slice`도 동일하다. 그러나 `Array.from`은 hole 처리 동작이 다르므로 sparse array 의도가 있다면 주의해야 한다.

### 객체 스프레드

객체 스프레드는 배열보다 비용이 크다. 매번 새 객체를 만들면서 hidden class 전이가 일어나기 때문이다.

V8은 객체의 형태(어떤 키들이 어떤 순서로 있는지)를 hidden class(map)로 추적한다. `{ ...a, b: 1 }`은 a의 키 형태에 b를 더한 새로운 형태를 만들어낸다. 이게 매번 다른 형태로 호출되면 polymorphic IC가 megamorphic으로 전이하면서 인라인 캐시가 깨진다.

루프 안에서 동일한 형태의 객체를 계속 스프레드하면 V8이 형태를 캐시해서 비교적 빠르지만, 키 순서가 가변적이거나 동적으로 키를 더하는 코드는 매 호출마다 hidden class 트랜지션이 일어난다.

```javascript
// 형태가 매번 다르다. hidden class 폭발.
function update(state, dynamicKey, value) {
  return { ...state, [dynamicKey]: value };
}

// 형태가 안정적이다.
function setCount(state, count) {
  return { ...state, count };
}
```

성능이 정말 중요한 hot path(예: Redux reducer가 초당 수천 번 돈다)에서는 immer 같은 라이브러리가 오히려 빨라진다. immer는 Proxy로 mutation을 추적해서 변경된 가지만 새로 만든다.

## 5. 한 단계 얕음과 중첩 참조 버그

스프레드는 한 단계 얕다. 1차 키의 값이 객체면 그 객체는 참조로 공유된다. 이게 React/Redux에서 가장 흔한 버그 원인이다.

```javascript
const state = {
  user: { name: 'kim', address: { city: 'seoul' } },
  items: [1, 2, 3]
};

const next = { ...state };
next.user.address.city = 'busan';

console.log(state.user.address.city); // 'busan'
```

`next.user.address`와 `state.user.address`는 같은 객체를 가리킨다. Redux에서 reducer가 이 패턴을 쓰면 컴포넌트가 리렌더링되지 않는다. React-Redux는 기본적으로 `===`로 변경을 감지하는데, 참조가 같으니 변경이 없다고 판단한다.

진짜 무서운 건 디버깅이 어렵다는 점이다. 콘솔에 찍으면 state도 'busan'이라 "내가 mutation을 했나?" 의심하게 된다. 실제로는 안 했고, spread가 한 단계만 자른 것뿐이다.

올바른 패턴은 변경 경로를 따라가며 모든 레벨을 새로 만드는 것이다.

```javascript
const next = {
  ...state,
  user: {
    ...state.user,
    address: {
      ...state.user.address,
      city: 'busan'
    }
  }
};
```

3단계만 들어가도 코드가 보기 싫어진다. 그래서 실무에서는 immer를 쓰거나 lodash `set`을 쓰거나 RTK(Redux Toolkit)의 `createSlice`를 쓴다. RTK는 내부적으로 immer를 쓰므로 mutation처럼 적어도 immutable update가 된다.

배열에서도 동일한 문제가 있다.

```javascript
const list = [{ id: 1, tags: ['a', 'b'] }];
const copy = [...list];
copy[0].tags.push('c');
console.log(list[0].tags); // ['a', 'b', 'c']
```

`map`을 써서 안에서 새 객체를 만들어야 한다.

```javascript
const copy = list.map(item =>
  item.id === 1 ? { ...item, tags: [...item.tags, 'c'] } : item
);
```

## 6. 깊은 복사 대안의 트레이드오프

진짜 깊은 복사가 필요한 순간이 있다. 그때 선택지는 네 가지다.

### structuredClone (2022~)

Node 17+, 모든 최신 브라우저에서 글로벌로 제공된다. HTML Structured Clone 알고리즘을 그대로 노출했다.

```javascript
const deep = structuredClone(original);
```

가장 빠르고, Date·Map·Set·RegExp·ArrayBuffer·TypedArray·Blob·File을 모두 보존한다. 순환 참조도 처리한다. 그러나 함수, Symbol 키, prototype, getter/setter, DOM 노드(브라우저), class 인스턴스의 클래스성(타입) 모두 복사하지 못한다. Function이 든 객체를 넣으면 `DataCloneError`를 던진다.

서버 사이드에서 plain data만 깊은 복사할 때는 거의 항상 정답이다.

### JSON.parse(JSON.stringify(x))

오래된 트릭이다. 빠르고 어디서나 동작하지만 제약이 많다. `undefined`는 사라지고, `Date`는 ISO 문자열이 되고, `Map`·`Set`·`RegExp`는 빈 객체 또는 `{}`가 되고, `NaN`·`Infinity`는 `null`이 되고, 순환 참조는 던진다. BigInt도 던진다.

structuredClone이 있는 환경에서는 굳이 쓸 이유가 없다. Node 16 이하 호환이 필요할 때만 fallback으로 쓴다.

### lodash cloneDeep

함수도 복사하고(같은 함수 참조 유지), prototype도 보존하고, 순환 참조도 처리한다. structuredClone보다 느리지만(약 2~3배) 제약이 적다. 함수가 포함된 복잡한 객체를 다룰 때 쓴다.

### 직접 재귀 구현

특정 객체 형태를 알고 있고, hot path라면 직접 짜는 게 가장 빠르다. 그러나 거의 항상 첫 시도에서 엣지 케이스를 놓친다(순환 참조, Date, Symbol). 권장하지 않는다.

선택 기준은 단순하다. plain JSON 같은 데이터면 `structuredClone`, 함수가 끼면 `lodash.cloneDeep`, Node 16 이하면 `JSON` 트릭. 그리고 진짜로 깊은 복사가 필요한가를 한 번 더 검토하라. 보통은 변경 경로만 새로 만드는 게 맞다.

## 7. 함수 호출에서의 스프레드

`f(...args)`는 명세상 `args[Symbol.iterator]`를 돌려서 인수 리스트로 만든다. 배열 스프레드와 동일한 이터러블 규칙을 따른다.

성능상 한 가지 주의할 점이 있다. V8은 함수 호출 인수 처리에서 packed array에 대한 fast path를 가지고 있지만, 가변 인수 함수가 인라이닝되기 어려워진다. 인수 개수가 10개를 넘어가는 경우 V8의 인라이너가 포기하는 케이스가 늘어난다. 핫 루프에서 `f(...bigArr)`를 매 호출마다 쓰는 패턴은 피하는 게 좋다.

`Math.max(...arr)`는 잘 알려진 트릭인데, 큰 배열에서는 스택 오버플로가 난다. 브라우저별로 다르지만 보통 10만~50만 개에서 터진다. 인수가 스택에 다 올라가야 하기 때문이다. 큰 배열의 max는 `arr.reduce((m, v) => v > m ? v : m, -Infinity)`로 가야 한다.

## 8. 함수형 파이프라인에서의 활용

스프레드는 immutable pipeline의 접착제 역할을 한다.

```javascript
const result = users
  .filter(u => u.active)
  .map(u => ({ ...u, displayName: u.name.toUpperCase() }))
  .reduce((acc, u) => ({ ...acc, [u.id]: u }), {});
```

이 코드는 의도는 명확하지만 비용이 크다. reduce가 매 step마다 새 객체를 만든다. n개 원소면 n번의 객체 생성과 n번의 키 복사가 일어나서 시간복잡도가 O(n²)이 된다. 1만 개면 1억 회 키 복사다.

해결은 `Object.fromEntries`를 쓰는 것이다.

```javascript
const result = Object.fromEntries(
  users
    .filter(u => u.active)
    .map(u => [u.id, { ...u, displayName: u.name.toUpperCase() }])
);
```

O(n)이 된다. reduce + spread 패턴은 가독성은 좋지만 데이터가 커지면 무조건 터진다. 이 패턴이 코드베이스에 있으면 일단 의심해야 한다.

배열의 경우도 비슷하다.

```javascript
// O(n²). 매 iteration마다 새 배열 만들고 전체 복사.
const collected = items.reduce((acc, x) => [...acc, transform(x)], []);

// O(n). map이 정답.
const collected = items.map(transform);
```

스프레드를 reducer 안에서 누산기로 쓰는 패턴은 거의 항상 잘못된 선택이다.

## 9. TypeScript에서의 추론 동작

타입스크립트는 스프레드를 다음 규칙으로 처리한다.

### 튜플 스프레드

가변 튜플 타입(variadic tuple types, TS 4.0+)이 들어온 뒤로 다음이 가능해졌다.

```typescript
type A = [1, 2];
type B = [3, 4];
type C = [...A, ...B]; // [1, 2, 3, 4]

function concat<T extends unknown[], U extends unknown[]>(
  a: [...T],
  b: [...U]
): [...T, ...U] {
  return [...a, ...b];
}

const r = concat([1, 2] as const, ['a'] as const);
// r의 타입: readonly [1, 2, 'a']
```

이게 함수의 인수 타입 forwarding에서 핵심이다. `Parameters<F>`를 스프레드해서 다른 함수에 그대로 넘기는 wrapper를 타입 안전하게 만들 수 있다.

```typescript
function wrap<F extends (...args: any[]) => any>(
  fn: F
): (...args: Parameters<F>) => ReturnType<F> {
  return (...args) => fn(...args);
}
```

### 객체 스프레드와 유니온

객체 스프레드에서 유니온 타입 추론은 직관에 어긋날 때가 있다.

```typescript
type A = { kind: 'a'; x: number };
type B = { kind: 'b'; y: string };

function merge(t: A | B) {
  return { ...t, extra: 1 };
  // 반환 타입: (A & { extra: number }) | (B & { extra: number })
}
```

TS 3.2부터 유니온의 각 멤버에 대해 스프레드를 분배한다. 그 전에는 `A | B`를 그대로 spread해서 `{ kind: 'a' | 'b'; x?: number; y?: string; extra: number }` 같은 어색한 형태가 나왔다.

### 같은 키의 덮어쓰기

```typescript
const a = { x: 1, y: 'a' };
const b = { ...a, x: 'overridden' };
// b의 타입: { y: string; x: string }
```

TS 3.0 전에는 `{ x: number | string; y: string }`로 추론돼서 type narrowing이 안 됐다. 지금은 뒤에 오는 키가 앞 키를 완전히 덮어쓰는 식으로 추론된다. 다만 conditional spread는 여전히 까다롭다.

```typescript
const opts = condition ? { x: 1 } : {};
const final = { ...base, ...opts };
// opts 타입이 { x: number } | {}라서 final에 x가 옵셔널로 들어간다.
```

이 패턴은 의도와 다르게 타입이 풀릴 때가 잦다. 명시적으로 별도 if 블록으로 풀어쓰는 게 낫다.

## 10. 마지막으로 정리할 엣지 케이스

`null`과 `undefined`에 대한 동작이 다르다.

```javascript
{ ...null }       // {}
{ ...undefined }  // {}
{ ...0 }          // {}
{ ...'ab' }       // { 0: 'a', 1: 'b' }  ← 문자열은 인덱스 속성을 가진다
{ ...[1, 2] }     // { 0: 1, 1: 2 }
[...null]         // TypeError
[...undefined]    // TypeError
[...'ab']         // ['a', 'b']
```

객체 스프레드는 primitive를 그냥 무시하지만(`null`/`undefined`/`number`는 자체 속성이 없거나 박싱돼도 열거 가능 속성이 없다), 배열 스프레드는 이터러블이 아니면 던진다. 옵셔널 머지 패턴 `{ ...defaults, ...maybeOverride }`에서 `maybeOverride`가 `undefined`여도 안전한 이유가 이거다.

`Promise`나 `RegExp` 같은 객체를 스프레드해도 자체 속성이 거의 없어서 빈 객체가 나온다. 이런 객체를 복사하려면 해당 타입의 생성자를 직접 호출해야 한다.

## 마치며

스프레드가 잘 쓰이는 자리는 일정하다. 작은 수의 객체나 배열을 합치거나, 함수 호출에서 인수를 펼치거나, immutable update의 한 레벨을 만드는 경우. 핫 루프에서의 대용량 복사, 깊은 mutation 회피, 반응형 객체 복사, 함수 인스턴스 복제 같은 자리에서는 다른 도구가 더 맞는다. 명세를 한 번 읽어두면 라이브러리 코드를 디버깅할 때 reactive object의 setter가 왜 안 불렸는지, 왜 클래스 인스턴스가 plain object가 됐는지 빠르게 보인다.
