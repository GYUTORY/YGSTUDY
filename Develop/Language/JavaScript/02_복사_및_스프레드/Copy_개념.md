---
title: JavaScript 얕은 복사와 깊은 복사 (Shallow vs Deep Copy)
tags: [language, javascript, 02복사및스프레드, copy, shallow-copy, deep-copy, immutability]
updated: 2026-05-03
---

# JavaScript 얕은 복사와 깊은 복사

## 들어가기 전에

복사 문제는 자바스크립트로 백엔드든 프론트든 어떤 코드든 짜다 보면 한 번은 호되게 당하는 주제다. 객체를 받아서 한 줄 바꿨을 뿐인데 호출한 쪽 데이터가 통째로 바뀌어 있다거나, Redux store에 들어간 값을 직접 수정해 디버깅 도구가 변경을 못 잡는다거나, `JSON.parse(JSON.stringify(...))`로 복사한 값에서 `Date`가 문자열이 되어 있다거나—전부 같은 뿌리에서 나오는 문제다.

이 문서는 입문~실무 기본을 정리한다. V8 힙 구조나 `structuredClone` 알고리즘의 내부 동작은 [Copy_Deep_Dive.md](Copy_Deep_Dive.md)에 따로 정리했다.

---

## 1. 원시 타입과 참조 타입의 메모리 동작

자바스크립트의 값은 원시 타입(primitive)과 참조 타입(reference)으로 갈린다. 이 둘은 변수에 들어가는 방식 자체가 다르다.

### 원시 타입은 값이 박힌다

원시 타입은 `number`, `string`, `boolean`, `null`, `undefined`, `symbol`, `bigint` 일곱 가지다. 변수에 대입하면 변수 슬롯에 그 값 자체가 들어간다고 보면 된다.

```javascript
let a = 42;
let b = a;   // 42라는 값이 슬롯 단위로 통째로 복사됨
b = 100;
console.log(a); // 42 — a는 영향 없음
```

문자열도 마찬가지다. 길이가 길든 짧든, 값처럼 다뤄진다(엔진 내부에서는 immutable 힙 객체로 관리되지만, 사용자 입장에서는 값 의미론으로 동작한다).

```javascript
let s1 = "hello";
let s2 = s1;
s2 = "world";
console.log(s1); // "hello"
```

원시 타입은 immutable이라서 바뀌는 순간 새 값이 만들어진다. `s2 = "world"`는 기존 슬롯의 내용을 덮어쓰는 게 아니라 새 문자열을 가리키도록 슬롯을 갱신하는 동작이다.

### 참조 타입은 주소가 들어간다

`object`, `array`, `function`, `Date`, `Map`, `Set`, `RegExp`, 클래스 인스턴스—전부 참조 타입이다. 객체 본체는 힙에 따로 할당되고, 변수에는 그 객체를 가리키는 포인터(주소)가 들어간다.

```javascript
const obj = { x: 1 };
const ref = obj;     // obj가 가리키는 주소를 ref에도 복사
ref.x = 99;
console.log(obj.x);  // 99 — 같은 객체를 두 변수가 가리키고 있을 뿐
```

이게 "참조 타입은 주소를 복사한다"의 실제 동작이다. `ref = obj`는 객체를 새로 만드는 게 아니라 같은 객체에 두 번째 이름표를 붙이는 일이다.

### 함수 인자도 같은 규칙을 따른다

자바스크립트는 모든 인자를 값으로 전달하지만, 참조 타입의 경우 그 "값"이 주소이기 때문에 결과적으로 호출자의 객체가 수정된다.

```javascript
function tryToReset(user) {
  user = { name: "" };  // 로컬 변수만 새 객체를 가리키게 됨
}

function actuallyMutate(user) {
  user.name = "";       // 호출자의 객체가 직접 수정됨
}

const u = { name: "kim" };
tryToReset(u);
console.log(u.name);    // "kim"
actuallyMutate(u);
console.log(u.name);    // ""
```

서버에서 입력 DTO를 함수에 넘겨놓고 안에서 정규화한다고 키를 덮어쓰면, 호출한 라우터/컨트롤러 쪽 객체도 같이 바뀐다. 의도된 동작이라면 명시적으로 문서화하고, 아니라면 함수 진입 시점에 복사부터 하는 게 안전하다.

---

## 2. 얕은 복사

얕은 복사는 객체의 최상위 키만 새 객체로 옮기고, 그 안쪽이 또 객체면 같은 참조를 그대로 들고 가는 방식이다. "한 겹만 벗겨서 새 봉투에 담는다"가 정확한 비유다.

```javascript
const original = {
  name: "kim",
  address: { city: "Seoul" }
};

const copy = { ...original };
copy.name = "lee";              // 최상위 키 → 원본 영향 없음
copy.address.city = "Busan";    // 안쪽 객체 → 원본도 같이 바뀜

console.log(original.name);         // "kim"
console.log(original.address.city); // "Busan"
```

이 동작이 직관에 안 맞아서 처음 겪으면 한참을 디버깅하게 된다. "복사했는데 왜 같이 바뀌지?"의 99%가 여기서 나온다.

### 2.1 방법별 차이

얕은 복사 방법은 네 가지가 자주 쓰인다. 결과는 비슷해 보여도 디테일에서 갈린다.

#### Object.assign({}, src)

```javascript
const src = { a: 1, b: 2 };
const out = Object.assign({}, src);
```

- 열거 가능한(enumerable) 자기 자신의 속성(own property)만 복사한다. `Symbol` 키도 포함된다.
- `getter`는 호출되어 그 시점의 값으로 복사된다. 즉, getter 함수 자체는 사라지고 평범한 데이터 속성으로 바뀐다.
- 첫 인자 객체에 직접 쓰기(write)를 하기 때문에 그 객체에 setter나 readonly 속성이 있으면 예외가 날 수 있다. 그래서 보통 빈 객체 `{}`를 첫 인자로 넘긴다.

#### 스프레드 `{ ...src }`

```javascript
const out = { ...src };
```

- 동작은 `Object.assign({}, src)`와 거의 같다. enumerable own property만, Symbol 키도 포함.
- 차이가 한 가지 있다. 스프레드는 `[[Set]]`이 아니라 `CreateDataPropertyOrThrow`로 키를 박는다. 즉 결과 객체의 setter나 prototype 체인의 영향을 받지 않고 그냥 데이터 속성으로 만든다. 대부분의 경우 이게 더 안전하다.
- 그래서 보통 객체 복사는 스프레드, 동적으로 키를 합쳐야 할 때만 `Object.assign`을 쓰는 식으로 갈라 쓴다.

#### Array.from(src) / src.slice()

배열 전용 두 가지 방법이다.

```javascript
const arr = [1, [2, 3], { x: 4 }];
const copy1 = Array.from(arr);
const copy2 = arr.slice();
```

- 둘 다 얕은 복사다. 인덱스 0~length-1까지 새 배열로 옮기되, 안쪽 요소가 객체면 같은 참조를 공유한다.
- `Array.from`은 두 번째 인자로 매핑 함수를 받는다. `Array.from(arr, x => x * 2)`처럼 변환과 복사를 동시에 할 수 있다.
- `slice()`는 더 빠르다. 단순히 같은 길이의 배열을 복사할 거라면 `slice()`가 미세하게 유리하다.
- 둘 다 `Symbol.iterator`를 쓰는 게 아니라 length-기반으로 동작한다(`Array.from`은 iterable도 받지만 배열에 대해서는 length를 본다). sparse array의 빈 슬롯 처리는 약간 다르다. `slice`는 빈 슬롯을 빈 슬롯으로 보존하고, `Array.from`은 빈 슬롯을 `undefined`로 채워 dense하게 만든다.

```javascript
const sparse = [1, , 3];   // 인덱스 1이 hole
console.log(sparse.slice());     // [1, <1 empty item>, 3]
console.log(Array.from(sparse)); // [1, undefined, 3]
```

실무에서 sparse array를 일부러 만들 일은 거의 없다. 하지만 `new Array(10)` 같은 코드를 다른 사람이 만들어서 넘겨주면 차이가 생길 수 있다는 정도는 기억해두자.

### 2.2 얕은 복사가 놓치는 것

#### 중첩 객체는 참조가 공유된다

가장 흔하다. 위에서 본 `address.city` 케이스다. React `setState`에서 객체 안의 객체를 바꿀 때 바깥만 spread하고 끝내면 자식 객체 참조가 그대로라서 메모이제이션이 풀리지 않거나 거꾸로 같은 참조 비교가 깨진다.

```javascript
// 안티패턴
setUser({ ...user, profile: user.profile });
user.profile.age = 30;  // 같은 참조이므로 메모이제이션이 갱신을 감지 못함

// 올바른 패턴
setUser({ ...user, profile: { ...user.profile, age: 30 } });
```

#### getter/setter는 일반 속성으로 변한다

```javascript
const src = {
  _name: "kim",
  get name() { return this._name.toUpperCase(); }
};

const copy = { ...src };
console.log(copy.name);  // "KIM" — 한 번 호출된 결과값
src._name = "park";
console.log(copy.name);  // 여전히 "KIM" — getter가 함수째 복사된 게 아니라 값만 박힘
```

getter를 살리려면 `Object.defineProperty`나 `Object.getOwnPropertyDescriptors`로 디스크립터 단위 복사를 해야 한다.

```javascript
const realCopy = Object.defineProperties({},
  Object.getOwnPropertyDescriptors(src));
```

#### prototype 체인은 끊긴다

```javascript
class User {
  constructor(name) { this.name = name; }
  greet() { return `hi, ${this.name}`; }
}

const u = new User("kim");
const copy = { ...u };
copy.greet();   // TypeError: copy.greet is not a function
```

스프레드/`Object.assign`은 enumerable own property만 가져간다. 클래스 메서드는 `User.prototype`에 정의되어 있어서 own property가 아니다. 그래서 메서드가 통째로 빠진다. 클래스 인스턴스를 진짜로 복사하려면 새 인스턴스를 만들거나 `Object.create(Object.getPrototypeOf(src))`로 프로토타입을 살린 빈 객체에 속성을 옮겨 담아야 한다.

```javascript
const properCopy = Object.assign(
  Object.create(Object.getPrototypeOf(u)),
  u
);
properCopy.greet();  // "hi, kim"
```

#### Symbol 키는 일부만 챙겨진다

```javascript
const tag = Symbol("tag");
const src = { a: 1, [tag]: "secret" };

const copy1 = { ...src };
console.log(copy1[tag]);  // "secret" — 스프레드는 Symbol 키 포함

const copy2 = JSON.parse(JSON.stringify(src));
console.log(copy2[tag]);  // undefined — JSON은 Symbol 키 무시
```

이게 헷갈리는 이유는 사람들이 보통 `for...in`을 떠올려서 "Symbol은 어차피 안 나오겠지" 한다는 점이다. 스프레드와 `Object.assign`은 Symbol 키를 포함한다. 반면 `Object.keys`/`for...in`/`JSON.stringify`/`Object.entries`는 다 무시한다. 라이브러리 의존도가 높은 코드라면 이 차이로 메타데이터가 새 객체에서 사라지는 일이 생긴다.

#### non-enumerable은 빠진다

```javascript
const src = {};
Object.defineProperty(src, "secret", { value: 42, enumerable: false });

const copy = { ...src };
console.log(copy.secret);  // undefined
```

라이브러리가 객체에 메타데이터를 enumerable: false로 박아두는 경우가 있다(특히 ORM의 lazy-loaded 관계 같은 자리). 이런 객체를 spread로 복사하면 메타데이터가 사라진다.

---

## 3. 깊은 복사

깊은 복사는 객체 안의 객체까지 끝까지 새 메모리에 복사한다. 트리를 통째로 새로 그리는 작업이다. 옵션은 네 가지가 자주 쓰인다.

### 3.1 `JSON.parse(JSON.stringify(...))`

가장 짧게 쓰는 방법이고, 가장 많이 망하는 방법이기도 하다.

```javascript
const copy = JSON.parse(JSON.stringify(original));
```

JSON 직렬화/역직렬화를 거치기 때문에 JSON 표현 가능한 데이터만 살아남는다. 잘리는 것들과 모양이 바뀌는 것들을 케이스로 보자.

```javascript
const src = {
  date:   new Date("2026-01-01"),
  re:     /abc/g,
  fn:     () => 1,
  un:     undefined,
  nan:    NaN,
  inf:    Infinity,
  bi:     10n,                    // BigInt
  set:    new Set([1, 2]),
  map:    new Map([["a", 1]])
};

const copy = JSON.parse(JSON.stringify(src));
// copy.date  → "2026-01-01T00:00:00.000Z" (문자열로 변환됨)
// copy.re    → {} (정규식의 source/flags가 사라짐)
// copy.fn    → undefined (키 자체가 사라짐)
// copy.un    → undefined (마찬가지로 키가 사라짐)
// copy.nan   → null (NaN, Infinity는 JSON에 없어서 null로 박힘)
// copy.inf   → null
// copy.bi    → TypeError: Do not know how to serialize a BigInt
// copy.set   → {} (Set은 자체 toJSON이 없어 빈 객체)
// copy.map   → {} (Map도 마찬가지)
```

게다가 순환 참조가 있으면 `TypeError: Converting circular structure to JSON`으로 죽는다.

```javascript
const a = {};
a.self = a;
JSON.parse(JSON.stringify(a));  // TypeError
```

이것만 보면 못 쓸 물건 같지만, "내가 다루는 데이터는 평범한 plain object와 number/string/boolean/array 뿐"이라는 확신이 있다면 가장 빠르고 가장 짧다. 백엔드에서 DTO 같은 단순 구조를 한 번 복제할 때는 여전히 1순위다. 단, 도메인 객체가 끼어들면 즉시 다른 방법으로 갈아타야 한다.

### 3.2 `structuredClone`

Node 17+, 모든 모던 브라우저에서 동작하는 표준 함수다. HTML 명세의 Structured Clone Algorithm을 노출한 것이다.

```javascript
const copy = structuredClone(original);
```

JSON 방식이 무너지는 거의 모든 케이스를 잡아준다.

```javascript
const src = {
  date: new Date(),
  re:   /abc/g,
  set:  new Set([1, 2]),
  map:  new Map([["a", 1]]),
  buf:  new Uint8Array([1, 2, 3]),
};
const copy = structuredClone(src);
// 전부 같은 타입의 새 인스턴스로 복제됨
```

순환 참조도 처리한다.

```javascript
const a = {};
a.self = a;
const c = structuredClone(a);
console.log(c.self === c);  // true
```

다만 만능은 아니다. 다음은 `DataCloneError`로 죽는다.

- 함수: `() => 1`
- DOM 노드 일부 (브라우저 환경)
- 클래스 인스턴스의 메서드 (값 부분은 복사되지만 prototype은 사라짐 → `Object.prototype`이 됨)
- WeakMap, WeakSet
- 일부 Symbol 키

```javascript
class User { constructor(n) { this.name = n; } greet() {} }
const u = new User("kim");
const c = structuredClone(u);
console.log(c instanceof User);  // false — 데이터는 살았지만 타입은 죽음
```

성능은 보통 `JSON.parse(JSON.stringify(...))`보다 약간 빠르거나 비슷하다. 큰 객체일수록 `structuredClone`이 유리하다. "함수랑 클래스 인스턴스만 안 들어 있으면" 기본값으로 쓸 만한 도구다.

### 3.3 `lodash.cloneDeep`

라이브러리가 이미 들어 있다면 가장 무난한 선택이다.

```javascript
import cloneDeep from "lodash/cloneDeep";
const copy = cloneDeep(original);
```

- 순환 참조 처리. 함수도 그대로 참조 복사. 클래스 인스턴스의 prototype 보존.
- Date, RegExp, Map, Set, TypedArray, ArrayBuffer 모두 타입을 살림.
- 단점은 번들 크기. 프론트에서 cloneDeep 하나 때문에 lodash 전체를 끌어오는 일은 피하고, `lodash/cloneDeep` 또는 `lodash-es`를 쓰는 식으로 import 단위를 좁힌다.

### 3.4 직접 재귀 구현

라이브러리 없이, 동작도 명확히 하고 싶을 때 쓴다. 단순한 시작점은 이렇다.

```javascript
function deepClone(value, seen = new WeakMap()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return seen.get(value);  // 순환 참조 방어

  if (value instanceof Date) return new Date(value);
  if (value instanceof RegExp) return new RegExp(value.source, value.flags);
  if (value instanceof Map) {
    const out = new Map();
    seen.set(value, out);
    for (const [k, v] of value) out.set(deepClone(k, seen), deepClone(v, seen));
    return out;
  }
  if (value instanceof Set) {
    const out = new Set();
    seen.set(value, out);
    for (const v of value) out.add(deepClone(v, seen));
    return out;
  }

  const out = Array.isArray(value) ? [] : {};
  seen.set(value, out);
  for (const key of Reflect.ownKeys(value)) {
    out[key] = deepClone(value[key], seen);
  }
  return out;
}
```

`seen` WeakMap이 핵심이다. 한 번 본 객체는 같은 새 인스턴스를 재사용하기 때문에 순환 참조에서도 무한 재귀로 빠지지 않는다. `Reflect.ownKeys`를 써야 Symbol 키와 non-enumerable 키까지 챙겨진다.

이 정도면 90% 케이스는 처리되지만, prototype 보존, getter/setter 디스크립터, TypedArray의 view/buffer 분리 같은 부분은 여전히 빠진다. 직접 구현은 "내가 다루는 데이터 모양을 정확히 알고 있고, 거기에 맞춰서 짠다"는 전제에서만 의미가 있다. 모르는 데이터를 복사할 거면 `structuredClone`이나 `cloneDeep`이 안전하다.

---

## 4. 컬렉션과 특수 객체 복사 시 주의점

### Map과 Set

스프레드와 `Object.assign`은 Map/Set을 일반 객체처럼 다루지 않는다. 스프레드를 객체 안에서 쓰면 빈 객체가 박힌다.

```javascript
const m = new Map([["a", 1]]);

const wrong = { ...m };
console.log(wrong);          // {} — Map의 enumerable own property가 없음

const right = new Map(m);
console.log(right.get("a")); // 1 — 새 Map이지만 얕은 복사 (값이 객체면 참조 공유)
```

배열 안에서 spread는 다르게 동작한다. `[...m]`은 `[[key, value], ...]` 형태로 펼쳐진다. Map/Set은 iterable이기 때문이다.

```javascript
const arr = [...m];  // [["a", 1]]
```

### TypedArray와 ArrayBuffer

TypedArray는 같은 ArrayBuffer를 가리키는 view다. 그래서 단순 복사를 잘못하면 같은 버퍼를 공유한다.

```javascript
const a = new Uint8Array([1, 2, 3]);
const b = a;            // 같은 버퍼, 같은 view
const c = a.slice();    // 새 버퍼 + 새 view
const d = a.subarray(); // 같은 버퍼, 새 view (얕은 복사 비슷)

a[0] = 99;
console.log(b[0]);  // 99
console.log(c[0]);  // 1
console.log(d[0]);  // 99
```

`slice()`는 데이터까지 복사한다. `subarray()`는 같은 메모리를 공유하는 새 view다. `structuredClone`은 버퍼까지 복사한다. 의도와 다르게 같은 버퍼를 쓰는 코드를 만들면 멀티스레드(Worker) 환경에서 디버깅이 정말 어려워진다.

### Date와 RegExp

`new Date(srcDate)`, `new RegExp(srcRegex.source, srcRegex.flags)`로 새 인스턴스를 만든다. spread로 `{ ...date }`를 하면 빈 객체가 나오니까 절대 그렇게 하지 말 것.

---

## 5. 자주 만나는 트러블슈팅

### 5.1 React: setState로 객체를 갱신했는데 리렌더가 안 됨

```javascript
// 문제 — mutate
const [user, setUser] = useState({ name: "kim", profile: { age: 25 } });

const onClick = () => {
  user.profile.age = 30;
  setUser(user);  // 같은 참조, React가 변경을 감지 못함
};
```

React는 `Object.is`로 이전 state와 새 state를 비교한다. 같은 참조면 리렌더하지 않는다. spread로 새 참조를 만들어야 한다. 그것도 바뀐 경로의 모든 단계에서.

```javascript
const onClick = () => {
  setUser(prev => ({
    ...prev,
    profile: { ...prev.profile, age: 30 }
  }));
};
```

깊이가 3~4단계 이상 들어가면 가독성이 무너진다. 그 시점에서는 [Immer](https://immerjs.github.io/immer/)를 검토하는 게 낫다.

### 5.2 Redux: store를 직접 mutate해서 디버깅이 안 됨

```javascript
// 안티패턴
const reducer = (state, action) => {
  state.users.push(action.payload);  // store 직접 수정
  return state;
};
```

Redux DevTools의 시간 여행 디버깅, `connect`/`useSelector`의 참조 비교 전부 이전 state와 새 state가 다른 참조라는 전제 위에서 돌아간다. 직접 mutate하면 이게 깨진다. 그래서 Redux Toolkit은 기본으로 Immer를 깔고 작성자가 mutate처럼 짜도 내부에서 새 객체를 만들어준다.

### 5.3 백엔드: 캐시한 객체를 응답에 그대로 주는 실수

```javascript
const cache = new Map();

function getUser(id) {
  if (cache.has(id)) return cache.get(id);
  const user = db.findUser(id);
  cache.set(id, user);
  return user;
}

// 핸들러에서
const user = getUser(1);
user.name = req.body.name;  // 캐시 객체가 같이 바뀜
db.update(user);
```

캐시에서 꺼낸 객체를 호출자가 수정하면 다음 요청에서 그 캐시를 읽는 사람이 오염된 데이터를 받는다. 캐시에서 꺼내는 시점에 복사를 하든지, 캐시에 넣을 때 freeze를 걸든지 둘 중 하나여야 한다. 인메모리 캐시를 직접 만드는 코드라면 거의 100% 만나는 함정이다.

### 5.4 폼 라이브러리: 초기값을 통째로 mutate

`react-hook-form`이나 `formik`에서 초기값으로 받은 객체를 폼 내부에서 직접 수정해버리면, 폼을 reset해도 초기 상태로 못 돌아간다. 초기값을 함수 호출마다 새로 만들거나(`{ ...defaultUser }`), 폼에 넘기기 전에 복사부터 하는 패턴이 안전하다.

---

## 6. 어떤 복사를 언제 쓰는가

상황별로 갈라쓰는 기준은 이렇다.

- **참조형 한 단계만 갈아끼우면 충분한 경우** → 스프레드 `{ ...obj }` / `[...arr]`
- **plain object에 number/string/boolean/array만 있고 빠르게 복사하면 되는 경우** → `JSON.parse(JSON.stringify(...))`
- **Date, RegExp, Map, Set, TypedArray 같은 표준 객체가 섞여 있는 경우** → `structuredClone`
- **함수, 클래스 메서드, 커스텀 prototype까지 살려야 하는 경우** → `lodash.cloneDeep` 또는 직접 구현
- **깊은 트리를 자주 갱신하는 React/Redux 코드** → Immer

| 방법 | 깊이 | 함수 | 클래스 | Date/RegExp | Map/Set | 순환 참조 | Symbol 키 |
|------|------|------|--------|-------------|---------|-----------|-----------|
| spread / Object.assign | 1단계 | 참조 유지 | 데이터만 | 참조 유지 | 참조 유지 | OK | OK |
| JSON.parse(JSON.stringify) | 무한 | 손실 | 데이터만 | 문자열화 | 빈 객체 | TypeError | 손실 |
| structuredClone | 무한 | DataCloneError | 데이터만 | OK | OK | OK | 일부 |
| lodash.cloneDeep | 무한 | 참조 유지 | OK | OK | OK | OK | OK |

이 표는 머리에 외우려고 보는 게 아니라, "내 데이터에 무엇이 들어 있는지 먼저 알자"고 다시 한 번 환기하기 위한 것이다. 들어 있는 게 무엇인지 모르면 어떤 복사도 안전하다고 단언할 수 없다.

---

## 참고

- [Copy_Deep_Dive.md](Copy_Deep_Dive.md) — V8 힙/스택, structuredClone 알고리즘, Hidden Class와 복사 비용
- [MDN: Structured clone algorithm](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm)
- [HTML 명세: structuredClone](https://html.spec.whatwg.org/multipage/structured-data.html#structured-cloning)
