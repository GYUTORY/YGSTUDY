---
title: JavaScript forEach 메서드 심화 (동작 원리·콜백 시그니처·break 불가 한계)
tags: [language, javascript, 01기본javascript, forloop, foreach, deep-dive, ecmascript]
updated: 2026-06-05
---

# JavaScript forEach 메서드 심화 (동작 원리·콜백 시그니처·break 불가 한계)

기본 사용법은 `forEach_개념.md`, `forEach_예제.md`에서 다룬다. 이 문서는 한 단계 더 들어가서 ECMAScript 스펙이 정의하는 내부 동작, 콜백 시그니처에 숨은 함정, `break`가 안 되는 진짜 이유, sparse array·순회 중 변경·async 환경에서의 실제 거동까지 정리한다. 실무에서 forEach 때문에 디버깅 두세 시간 날린 경험이 있으면 이 문서가 도움이 된다.

## 스펙이 정의하는 forEach 알고리즘

ECMAScript는 `Array.prototype.forEach`를 다음 절차로 정의한다 (의역).

```
1. O    ← ToObject(this)
2. len  ← LengthOfArrayLike(O)          // 시작 시점에 length를 캐시한다
3. callbackfn이 callable이 아니면 TypeError
4. k    ← 0
5. while k < len:
     Pk ← ToString(k)
     kPresent ← HasProperty(O, Pk)      // 핵심: 키 존재 여부를 먼저 본다
     if kPresent:
        kValue ← Get(O, Pk)
        Call(callbackfn, thisArg, [kValue, k, O])
     k ← k + 1
6. return undefined
```

여기서 실무에 영향이 큰 포인트는 세 가지다.

**첫째, `length`는 루프 진입 직전 한 번만 읽고 캐시한다.** 콜백 안에서 배열에 `push`를 해도 새로 들어간 요소는 절대 순회하지 않는다. 반대로 `length`를 줄여버리면 그 이후 인덱스에 도달했을 때 멈춘다.

**둘째, 각 인덱스를 방문할 때 `HasProperty`로 키 존재 여부를 먼저 확인한다.** 이게 sparse array에서 hole을 건너뛰는 이유다. `[ , , 1]`처럼 hole이 있는 배열은 콜백 자체가 호출되지 않는다.

**셋째, 콜백의 반환값을 무시한다.** `return true`든 `return false`든 의미가 없다. 이게 곧 `break` 불가의 원인이다.

```javascript
const arr = [10, 20, 30];

arr.forEach((v, i, src) => {
    console.log(v, i, src === arr);  // 10 0 true / 20 1 true / 30 2 true
    if (i === 0) src.push(40);       // push 해도 새 요소는 순회 X
});
console.log(arr);  // [10, 20, 30, 40] — 추가는 됐지만 forEach는 못 본다
```

```javascript
const arr2 = [10, 20, 30, 40, 50];
arr2.forEach((v, i, src) => {
    console.log(v);
    if (i === 1) src.length = 2;     // length를 2로 줄임
});
// 출력: 10, 20 — 인덱스 2부터는 k < len(=5)지만 Get이 undefined를 반환,
// 정확히는 length 변경 후 k=2에서 HasProperty 체크 → 그러나 length는 캐시되어 있어
// 루프 자체는 k=2,3,4까지 돈다. 다만 잘려나간 인덱스에는 키가 없어 콜백 호출 안 됨.
```

두 번째 예제가 헷갈리는 부분인데, 스펙상 `len`은 처음 한 번 읽고 안 다시 읽지만 `HasProperty(O, "2")` 체크는 매 반복마다 한다. 그래서 `length = 2`로 줄이면 인덱스 2,3,4는 실제 프로퍼티가 사라져서 skip 된다. 결과적으로 안 돌지만, 메커니즘은 `length` 캐시가 아니라 `HasProperty` 실패 때문이다.

## 콜백 시그니처와 thisArg의 함정

`forEach(callback, thisArg)`의 두 번째 인자 `thisArg`는 콜백 안에서 `this`로 쓰이는 값이다. 그런데 콜백이 **arrow function**이면 `thisArg`가 무력화된다. arrow function은 자기 자신만의 `this`를 가지지 않고 어휘적 스코프의 `this`를 그대로 캡처하기 때문이다.

```javascript
const ctx = { multiplier: 10 };

// 일반 함수 — thisArg가 적용된다
[1, 2, 3].forEach(function(v) {
    console.log(v * this.multiplier);  // 10, 20, 30
}, ctx);

// arrow function — thisArg가 무시된다
[1, 2, 3].forEach((v) => {
    console.log(v * this.multiplier);  // NaN, NaN, NaN (this는 외부 스코프)
}, ctx);
```

실무에서 클래스 메서드 안에서 forEach 돌릴 때 이 차이가 자주 문제가 된다. arrow function을 쓰면 `this`가 클래스 인스턴스를 자연스럽게 가리키니까 보통 더 편하지만, 의도적으로 다른 컨텍스트를 주입하려면 일반 함수를 써야 한다.

```javascript
class OrderProcessor {
    constructor(taxRate) {
        this.taxRate = taxRate;
    }

    // arrow function — 외부 this(=인스턴스)를 캡처
    calculate(prices) {
        const total = { value: 0 };
        prices.forEach((p) => {
            total.value += p * (1 + this.taxRate);  // this.taxRate 정상 접근
        });
        return total.value;
    }

    // 일반 함수 + thisArg 주입
    calculateWithCtx(prices) {
        const total = { value: 0 };
        prices.forEach(function(p) {
            total.value += p * (1 + this.taxRate);  // this = 인스턴스
        }, this);
        return total.value;
    }

    // 일반 함수 + thisArg 누락 — strict mode에서 this는 undefined
    calculateBroken(prices) {
        const total = { value: 0 };
        prices.forEach(function(p) {
            total.value += p * (1 + this.taxRate);  // TypeError: Cannot read 'taxRate' of undefined
        });
        return total.value;
    }
}
```

콜백이 호출되는 조건도 짚어둘 만하다. **콜백은 키가 실제로 존재하는 인덱스에서만 호출된다.** undefined가 값으로 들어있는 것과 hole은 다르다.

```javascript
[1, undefined, 3].forEach((v, i) => console.log(i, v));
// 0 1 / 1 undefined / 2 3 — 모두 호출됨

[1, , 3].forEach((v, i) => console.log(i, v));
// 0 1 / 2 3 — 인덱스 1은 hole이라 skip
```

`new Array(3)`처럼 length만 가진 배열도 마찬가지로 콜백이 한 번도 호출되지 않는다. 이걸 모르면 "왜 안 도는지" 한참 헤맨다.

```javascript
const arr = new Array(3);
arr.forEach(() => console.log('called'));  // 아무것도 안 찍힘

// hole을 채우려면
Array.from({ length: 3 }).forEach(() => console.log('called'));  // 3번 찍힘
// 또는
[...new Array(3)].forEach(() => console.log('called'));          // 3번 찍힘
```

## break가 안 되는 진짜 이유

`for` 루프에서 쓰는 `break`, `continue`는 문법적으로 루프문에만 붙는다. forEach는 **메서드**일 뿐 루프문이 아니므로 콜백 안에서 `break`를 쓰면 `SyntaxError: Illegal break statement`가 난다. `continue`도 같은 이유로 못 쓴다.

콜백에서 `return`을 쓰는 건 가능하지만, 이건 **현재 콜백 호출만 종료**할 뿐 forEach 자체를 멈추지 못한다. 스펙이 콜백의 반환값을 명시적으로 무시한다고 정해놨다. 즉, `return`은 `continue`처럼 보일 수는 있어도 `break`처럼 동작하지는 않는다.

```javascript
[1, 2, 3, 4, 5].forEach((v) => {
    if (v === 3) return;     // continue처럼 보임
    console.log(v);
});
// 1, 2, 4, 5 — 3만 건너뛰고 끝까지 돈다
```

스펙 레벨에서 forEach는 콜백의 abrupt completion(return/throw/break/continue) 중 **throw만 전파**한다. 그래서 강제 종료하려면 throw를 던지는 트릭이 있다.

```javascript
class BreakError extends Error {}

try {
    [1, 2, 3, 4, 5].forEach((v) => {
        if (v === 3) throw new BreakError();
        console.log(v);
    });
} catch (e) {
    if (!(e instanceof BreakError)) throw e;
}
// 출력: 1, 2 — 3에서 강제 종료
```

이 트릭은 동작하긴 하는데 부작용이 만만치 않다.

- 예외 던지기 자체가 일반 분기보다 훨씬 비싸다. V8에서 try-catch가 함수 전체의 최적화를 막던 시절이 있었고 (지금은 많이 개선됐지만), 핫 패스에서는 여전히 권장하지 않는다.
- 의도하지 않은 다른 예외까지 같이 잡힐 위험이 있다. 위 예제에서 `instanceof BreakError`로 거르는 게 그래서 중요하다.
- 디버거에서 "uncaught exception" 일시 정지에 걸려 디버깅 흐름을 방해한다.
- 코드 의도가 명확하지 않다. 리뷰어가 "왜 throw로 break를 흉내내지?"라고 묻게 된다.

조기 종료가 필요하면 forEach를 포기하고 `for...of`, `for`, `some`, `every`, `find`를 쓰는 게 정석이다.

```javascript
// some: 콜백이 true 반환 시 즉시 종료 (break 흉내)
[1, 2, 3, 4, 5].some((v) => {
    if (v === 3) return true;
    console.log(v);
    return false;
});
// 출력: 1, 2

// for...of: 가장 자연스러운 break
for (const v of [1, 2, 3, 4, 5]) {
    if (v === 3) break;
    console.log(v);
}
```

`some`은 의미적으로 "조건을 만족하는 요소가 하나라도 있는가"를 묻는 메서드인데, 조기 종료 트릭으로 쓰는 건 의도를 왜곡한다. 짧은 코드에서는 괜찮지만 길어지면 `for...of`가 낫다.

## 순회 도중 배열 변경

스펙이 `length`를 캐시하고 매 반복마다 `HasProperty`를 체크한다는 사실을 알면, 순회 중 배열을 바꿨을 때 동작을 예측할 수 있다. 케이스별로 정리하면 이렇다.

```javascript
// 1) push: 새 요소는 순회 안 함
const a = [1, 2, 3];
a.forEach((v, i, src) => {
    if (i === 0) src.push(4);
    console.log(v);
});
// 1, 2, 3 — push된 4는 못 본다

// 2) pop: 아직 도달 안 한 끝 요소가 사라지면 그 인덱스에서 끝
const b = [1, 2, 3, 4];
b.forEach((v, i, src) => {
    if (i === 1) src.pop();  // 4가 사라짐
    console.log(v);
});
// 1, 2, 3 — k=3에서 HasProperty 실패, 콜백 호출 안 됨

// 3) shift: 인덱스가 밀려서 같은 요소를 두 번 보거나 건너뛴다
const c = [1, 2, 3, 4];
c.forEach((v, i) => {
    console.log(v, i);
    if (i === 0) c.shift();
});
// 1 0 / 3 1 / 4 2 — 2를 건너뜀 (shift 후 인덱스가 한 칸씩 당겨졌기 때문)

// 4) splice 중간 삽입
const d = [1, 2, 3];
d.forEach((v, i, src) => {
    if (i === 0) src.splice(1, 0, 99);  // 인덱스 1에 99 삽입
    console.log(v);
});
// 1, 99, 2 — 새 99가 인덱스 1로 들어가 순회 대상이 됨, 단 length가 4가 됐어도 k=3에서 멈춤

// 5) 인덱스로 직접 덮어쓰기
const e = [1, 2, 3];
e.forEach((v, i, src) => {
    if (i === 0) src[2] = 99;
    console.log(v);
});
// 1, 2, 99 — 아직 방문 안 한 인덱스 2는 변경된 값을 본다
```

이런 동작은 결과 예측이 어렵고 코드 리뷰에서 항상 의심을 산다. 순회 중 변경이 필요하면 원본을 건드리지 말고 새 배열을 만들거나, 인덱스 기반 `for` 루프로 명시적으로 처리한다.

## sparse array와 hole

자바스크립트 배열은 본질적으로 객체이고, 인덱스는 문자열 키다. hole은 "키가 아예 존재하지 않는 상태"고 `undefined`는 "키는 있고 값이 undefined"인 상태다. forEach는 hole을 건너뛴다.

```javascript
const arr = [1, , 3];
console.log(arr.length);           // 3
console.log(arr[1]);               // undefined (Get 결과는 undefined를 반환)
console.log(1 in arr);             // false (HasProperty가 false)

arr.forEach((v, i) => console.log(i, v));
// 0 1 / 2 3 — 인덱스 1은 hole이라 skip

// 비교: undefined를 명시적으로 넣은 경우
const arr2 = [1, undefined, 3];
console.log(1 in arr2);            // true
arr2.forEach((v, i) => console.log(i, v));
// 0 1 / 1 undefined / 2 3 — 전부 호출됨
```

배열을 일관되게 다루고 싶으면 hole이 생기지 않게 한다. `new Array(n)`, `delete arr[i]`, `arr.length = n`으로 늘리기, 인덱스 점프로 할당(`arr[10] = x`) 같은 작업이 hole을 만든다.

```javascript
// hole 채우기
const sparse = new Array(3);
const dense = Array.from(sparse, () => 0);  // [0, 0, 0]

// 또는
const dense2 = new Array(3).fill(0);         // [0, 0, 0]
```

## async forEach 안티패턴

forEach는 콜백의 반환값을 무시한다고 했다. 콜백이 `async function`이어도 마찬가지로 반환된 Promise를 무시하고 다음 반복으로 넘어간다. 그래서 "forEach 안에서 await"이 기대대로 동작하지 않는다.

```javascript
async function fetchAll(ids) {
    const results = [];
    ids.forEach(async (id) => {
        const data = await fetch(`/api/${id}`).then(r => r.json());
        results.push(data);
    });
    return results;  // 거의 항상 [] — fetch 끝나기 전에 반환
}
```

위 코드는 세 가지가 잘못됐다.

1. forEach가 콜백의 Promise를 await하지 않으므로 `return results`가 fetch 완료 전에 실행된다.
2. async 콜백이 던지는 거부(rejection)도 forEach 입장에서는 그냥 무시되는 Promise라서 처리되지 않은 거부(unhandled rejection)가 된다.
3. `results.push` 순서가 fetch 응답 순서에 좌우되어 입력 순서와 어긋날 수 있다.

해결은 forEach를 버리는 것이다.

```javascript
// 병렬로 다 받고 한 번에 기다리기
async function fetchAllParallel(ids) {
    return Promise.all(
        ids.map(id => fetch(`/api/${id}`).then(r => r.json()))
    );
}

// 순차로 처리해야 한다면 for...of
async function fetchAllSequential(ids) {
    const results = [];
    for (const id of ids) {
        const data = await fetch(`/api/${id}`).then(r => r.json());
        results.push(data);
    }
    return results;
}

// 동시 실행 수를 제한해야 한다면 p-limit 같은 라이브러리 또는 직접 구현
async function fetchAllLimited(ids, concurrency = 5) {
    const results = new Array(ids.length);
    let cursor = 0;
    const workers = Array.from({ length: concurrency }, async () => {
        while (cursor < ids.length) {
            const i = cursor++;
            const data = await fetch(`/api/${ids[i]}`).then(r => r.json());
            results[i] = data;
        }
    });
    await Promise.all(workers);
    return results;
}
```

forEach 안에서 await을 써야 할 때는 99% 의 경우 `for...of` 또는 `Promise.all + map`이 정답이다. async forEach는 "동작하지 않는다"가 아니라 "동작하긴 하는데 await을 무시한다"는 게 더 정확한 표현이다.

## Set·Map의 forEach 시그니처 차이

Array뿐 아니라 Set, Map, NodeList도 `forEach`를 가지고 있는데 시그니처가 미묘하게 다르다.

```javascript
// Array.prototype.forEach
// callback(currentValue, index, array)
[10, 20].forEach((v, i, arr) => console.log(v, i, arr));
// 10 0 [10, 20] / 20 1 [10, 20]

// Set.prototype.forEach
// callback(value, value, set) — value가 두 번 들어온다
new Set(['a', 'b']).forEach((v, k, set) => console.log(v, k, set));
// 'a' 'a' Set / 'b' 'b' Set

// Map.prototype.forEach
// callback(value, key, map)
new Map([['x', 1], ['y', 2]]).forEach((v, k, map) => console.log(v, k, map));
// 1 'x' Map / 2 'y' Map
```

Set의 두 번째 인자가 인덱스가 아니라 같은 value인 게 처음 보면 어리둥절하다. Map과 시그니처를 맞추기 위한 결정이라는 설명이 있다. Map의 `(value, key, map)`을 Set에 그대로 적용하려면 Set은 key=value이므로 같은 값이 두 번 들어오는 형태가 된다.

실무에서 헷갈리는 케이스는 Array를 Set으로 바꾼 뒤 인덱스가 필요할 때다. Set은 인덱스 개념 자체가 없으므로 `[...set].forEach((v, i) => ...)` 식으로 배열로 변환해서 돌려야 한다.

NodeList도 `forEach`를 가지고 있지만 Array가 아니다. 따라서 Array의 다른 메서드(`map`, `filter`)는 직접 못 쓴다.

```javascript
const nodes = document.querySelectorAll('.item');
nodes.forEach((node, i) => node.dataset.index = i);  // 잘 동작

nodes.map(n => n.textContent);   // TypeError: nodes.map is not a function
[...nodes].map(n => n.textContent);  // OK
Array.from(nodes).map(n => n.textContent);  // OK
```

오래된 브라우저(IE 11)는 `NodeList.prototype.forEach`도 없다. 호환성이 중요하면 `Array.from(nodes).forEach(...)`나 polyfill을 쓴다. HTMLCollection은 `forEach`가 아예 없으므로 항상 배열 변환이 필요하다.

## forEach 폴리필 — 직접 구현해보기

스펙 알고리즘을 그대로 옮기면 이렇게 된다. 동작 원리를 이해하는 데 가장 확실한 방법이다.

```javascript
function forEachPolyfill(callback, thisArg) {
    // 1. this를 객체로 변환
    if (this == null) {
        throw new TypeError('Array.prototype.forEach called on null or undefined');
    }
    const O = Object(this);

    // 2. length 캐시 (>>> 0 으로 unsigned 32bit 정수화)
    const len = O.length >>> 0;

    // 3. callback이 callable인지 검사
    if (typeof callback !== 'function') {
        throw new TypeError(callback + ' is not a function');
    }

    // 4. 순회
    let k = 0;
    while (k < len) {
        // HasProperty 체크 — sparse array의 hole을 건너뛰는 핵심
        if (k in O) {
            const kValue = O[k];
            callback.call(thisArg, kValue, k, O);
        }
        k++;
    }

    // 5. undefined 반환 (스펙)
}

// Array.prototype에 붙이지 않고 함수형으로 호출
forEachPolyfill.call([1, , 3], (v, i) => console.log(i, v));
// 0 1 / 2 3 — hole skip 확인
```

이 폴리필을 보면 왜 `length`가 캐시되고 hole이 skip되는지 한 줄씩 추적할 수 있다. `k in O` 체크를 빼면 hole도 콜백을 받지만 값은 `undefined`가 되어 native forEach와 동작이 달라진다.

## 성능 — for 루프 vs forEach

JIT 최적화 관점에서 보면 단순 인덱스 `for` 루프가 forEach보다 약간 빠르다. forEach는 매 반복마다 함수 호출이 들어가서 호출 오버헤드와 스택 프레임 비용이 누적된다. V8은 forEach의 콜백을 인라이닝하는 최적화를 어느 정도 하지만, 콜백이 다형성(polymorphic) 호출 사이트가 되면 인라이닝이 깨진다.

```javascript
// 같은 forEach에 다양한 모양의 콜백이 들어가면 monomorphic → megamorphic 전이
[1,2,3].forEach(a);   // a는 (number) => void
[1,2,3].forEach(b);   // b는 다른 모양
[1,2,3].forEach(c);   // ...
// 콜 사이트가 megamorphic이 되면 인라이닝/특수화가 풀린다
```

실측 차이는 보통 수 % 수준이라 가독성을 희생할 만한 수준은 아니다. 다만 다음 상황에서는 `for`가 명확히 유리하다.

- 수백만 건 처리하는 핫 패스 (분석 파이프라인, 게임 루프, 렌더링 hot path)
- 배열이 typed array (Float64Array 같은) 라서 인덱스 접근 비용이 매우 낮을 때
- 조기 종료가 필요할 때 (`break`)
- 인덱스 산술이 필요할 때 (역순, 2칸씩 건너뛰기 등)

반대로 forEach가 유리한 상황은 가독성과 컬렉션 의미를 살리고 싶을 때다. 일반적인 비즈니스 로직에서는 forEach가 충분히 빠르다.

## 실무 트러블슈팅 패턴

### this 손실

```javascript
class Logger {
    constructor(prefix) { this.prefix = prefix; }

    logAll(items) {
        // 일반 함수 콜백 + thisArg 누락 → this는 strict mode에서 undefined
        items.forEach(function(item) {
            console.log(this.prefix, item);  // TypeError
        });
    }
}
```

해결: arrow function을 쓰거나 `forEach(fn, this)`로 명시적으로 전달한다. arrow function이 짧고 직관적이라 보통 이쪽을 선호한다.

### return을 break로 착각

```javascript
function findUser(users, targetId) {
    let found = null;
    users.forEach(u => {
        if (u.id === targetId) {
            found = u;
            return;  // forEach가 멈추지 않는다 — 나머지도 다 돈다
        }
    });
    return found;
}
```

작은 배열에서는 동작하지만 큰 배열에서는 불필요한 순회가 일어난다. `find`, `for...of`, `some` 중 적합한 것으로 바꾼다.

```javascript
function findUserFixed(users, targetId) {
    return users.find(u => u.id === targetId) ?? null;
}
```

### 인덱스 누락

```javascript
items.forEach((item) => {
    saveAt(/* index? */, item);  // 인덱스가 필요한데 콜백에 안 받아옴
});
```

콜백 시그니처가 `(value, index, array)`인 걸 잊고 첫 번째 인자만 받는 경우. 인덱스가 필요하면 두 번째 인자를 받는다.

```javascript
items.forEach((item, i) => saveAt(i, item));
```

### 중첩 forEach에서 외부 break 흉내

```javascript
// 2차원 배열에서 특정 값을 찾으면 모든 순회를 중단하고 싶다
const matrix = [[1, 2], [3, 4], [5, 6]];
let found = null;

matrix.forEach(row => {
    row.forEach(cell => {
        if (cell === 4) found = cell;
        // 여기서 어떻게 외부 forEach까지 중단하지?
    });
});
```

forEach로는 외부 루프 중단이 깔끔하지 않다. throw 트릭을 쓰거나, 차라리 `for...of`로 바꾸고 라벨 break를 쓴다.

```javascript
outer: for (const row of matrix) {
    for (const cell of row) {
        if (cell === 4) {
            console.log('found');
            break outer;
        }
    }
}

// 또는 some 체이닝
const found = matrix.some(row =>
    row.some(cell => cell === 4)
);
```

### 비동기 작업 누적

```javascript
const results = [];
items.forEach(async item => {
    const r = await process(item);
    results.push(r);
});
console.log(results);  // [] — 거의 항상 빈 배열
```

위 async forEach 안티패턴 섹션 참고. `for...of` 또는 `Promise.all(items.map(...))`로 대체한다.

## 정리하면서

forEach는 "그냥 배열 돌리는 메서드"로 시작했다가 막상 깊이 들어가면 스펙·this 바인딩·sparse array·async 같은 자바스크립트의 까다로운 부분이 거의 다 얽혀 있다. 5년 차 시점에서 다시 forEach를 보면, 단순 순회는 어떻게든 돌지만 다음 상황에서는 다른 도구를 쓰는 게 옳다.

- 조기 종료가 필요하면 `for...of`, `some`, `find`
- 결과를 변형해서 새 배열을 만들려면 `map`
- 비동기 작업이 필요하면 `for...of` + `await` 또는 `Promise.all`
- hole이 있는 배열을 일관되게 다루려면 hole부터 채우거나 `for` 인덱스 루프

forEach 자체는 부수 효과 위주 작업(로깅, DOM 업데이트, 외부 상태 갱신)에 어울리는 도구다. 반환값이 없는 메서드라는 점이 곧 "이 코드는 어딘가에 부수 효과를 일으키고 있다"는 신호를 준다는 점에서 가독성에 도움이 된다. 다만 위 한계들을 알고 쓰는 것과 모르고 쓰는 것은 디버깅 난이도가 다르다.
