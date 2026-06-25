---
title: Spread & Rest 연산자
tags: [language, javascript, es6, spread, rest, destructuring]
updated: 2026-06-25
---

# Spread & Rest 연산자

## 개요

`...` 기호는 똑같이 생겼지만 어디에 쓰였느냐에 따라 정반대로 동작한다. 펼치면 Spread, 모으면 Rest다.

| 이름 | 위치 | 역할 |
|------|------|------|
| Spread (전개) | 함수 호출, 배열/객체 리터럴 | 이터러블/객체를 펼쳐서 개별 요소로 분리 |
| Rest (나머지) | 함수 파라미터, 구조분해 좌변 | 나머지 요소들을 배열/객체로 수집 |

헷갈릴 때는 `=`을 기준으로 본다. 우변(값을 만드는 쪽)에 있으면 Spread, 좌변(값을 받는 쪽)이나 파라미터 자리에 있으면 Rest다.

---

## Spread 연산자

### 배열 Spread

```javascript
const arr1 = [1, 2, 3];
const arr2 = [4, 5, 6];

// 배열 복사 (얕은 복사)
const copy = [...arr1];                 // [1, 2, 3]

// 배열 합치기
const merged = [...arr1, ...arr2];      // [1, 2, 3, 4, 5, 6]

// 중간에 삽입
const inserted = [...arr1, 99, ...arr2]; // [1, 2, 3, 99, 4, 5, 6]

// 함수 인수로 전개
Math.max(...arr1);                      // 3
console.log(...arr1);                   // 1 2 3
```

`Math.max(...arr)` 같은 전개는 인수 개수가 곧 콜스택 슬롯이라, 원소 수십만 개짜리 배열을 넘기면 `RangeError: Maximum call stack size exceeded`가 난다. 엔진마다 한계가 다른데 보통 10만 안팎에서 터진다. 큰 배열의 최댓값은 `arr.reduce((m, n) => n > m ? n : m)`로 돌리는 게 안전하다.

### 객체 Spread

```javascript
const base = { a: 1, b: 2 };
const extra = { c: 3, d: 4 };

// 객체 복사 (얕은 복사)
const copy = { ...base };              // { a: 1, b: 2 }

// 객체 병합
const merged = { ...base, ...extra };  // { a: 1, b: 2, c: 3, d: 4 }

// 속성 오버라이드 — 나중 값이 우선
const updated = { ...base, b: 99 };   // { a: 1, b: 99 }

// 기본값 + 실제값 패턴 (실무에서 자주 사용)
const defaults = { theme: 'light', lang: 'ko', pageSize: 20 };
const userConfig = { theme: 'dark', pageSize: 50 };
const config = { ...defaults, ...userConfig };
// { theme: 'dark', lang: 'ko', pageSize: 50 }
```

기본값 병합에서 한 번씩 당하는 게 `undefined` 덮어쓰기다. `{ ...defaults, ...userConfig }`에서 `userConfig.theme`이 `undefined`로 명시돼 있으면 `theme`이 `undefined`로 덮인다. 키가 아예 없는 것과 값이 `undefined`인 것은 다르게 취급되니까, API 응답을 그대로 스프레드하기 전에 `undefined` 필드를 걸러내거나 받는 쪽에서 다시 기본값을 채워야 한다.

### 문자열 / 이터러블 Spread

```javascript
// 문자열을 문자 배열로
const chars = [..."hello"];            // ['h', 'e', 'l', 'l', 'o']

// Set → 배열 (중복 제거)
const set = new Set([1, 2, 2, 3, 3]);
const unique = [...set];               // [1, 2, 3]

// Map → 배열
const map = new Map([['a', 1], ['b', 2]]);
const entries = [...map];              // [['a', 1], ['b', 2]]
```

문자열 스프레드는 글자 단위가 아니라 코드 포인트 단위로 자른다. `[..."hello"]`는 직관대로 나오지만 이모지나 결합 문자가 섞이면 `"á"`(á)이 `['a', '́']`로 쪼개지는 식이라 길이가 어긋난다. 단순 ASCII가 아니면 `.split('')`과도 결과가 다르니 주의한다.

배열 스프레드의 동작 조건, 무한 제너레이터에서 멈추는 문제, TypedArray·`arguments`·`NodeList`의 차이 같은 내부 동작은 [Spread 연산자 심화](../02_복사_및_스프레드/Spread_Deep_Dive.md)에 정리돼 있다.

---

## Rest 파라미터

### 가변 인수 수집

```javascript
// 가변 인수 함수
function sum(...numbers) {
    return numbers.reduce((acc, n) => acc + n, 0);
}
sum(1, 2, 3, 4, 5);  // 15

// 첫 인수 분리 후 나머지 수집
function log(level, ...messages) {
    console.log(`[${level}]`, ...messages);
}
log('INFO', '서버 시작', '포트 3000');  // [INFO] 서버 시작 포트 3000
```

Rest로 받은 `numbers`는 진짜 배열이라 `reduce`, `map`이 바로 먹는다. 옛날 코드의 `arguments`는 배열처럼 생겼을 뿐 배열 메서드가 없어서 `Array.from(arguments)`를 한 번 거쳐야 했다. 그리고 `arguments`는 화살표 함수 안에서는 아예 존재하지 않으니, 화살표 함수로 가변 인수를 받으려면 Rest 말고는 방법이 없다.

```javascript
const sum = (...nums) => nums.reduce((a, b) => a + b, 0);  // OK
const broken = () => arguments.length;                      // ReferenceError 또는 바깥 arguments 참조
```

### Rest는 항상 마지막에 와야 한다

Rest 파라미터는 함수 시그니처에서 무조건 마지막 자리다. 뒤에 다른 파라미터가 오면 파싱 단계에서 `SyntaxError`라 실행조차 안 된다. 트레일링 콤마도 마찬가지로 막혀 있다.

```javascript
function bad(a, ...rest, b) {}   // SyntaxError: Rest parameter must be last formal parameter
function bad2(...rest,) {}        // SyntaxError: Rest parameter may not have a trailing comma
```

구조분해에서도 동일하다. `const [first, ...mid, last] = arr`는 안 된다. "앞에서 몇 개 떼고 뒤에서 몇 개 떼기"가 필요하면 Rest로 한 번에 못 하고 `slice`로 직접 잘라야 한다.

### Rest는 기본값을 가질 수 없다

기본값(default)을 붙일 수 있는 건 Rest 앞의 일반 파라미터까지다. Rest 자체는 인수가 하나도 없어도 항상 빈 배열 `[]`이라 기본값을 줄 자리가 없고, 주려고 하면 문법 에러다.

```javascript
// 앞 파라미터에 기본값 + Rest 조합은 정상
function paginate(page = 1, size = 20, ...filters) {
    return { page, size, filters };
}
paginate();                    // { page: 1, size: 20, filters: [] }
paginate(2, 50, 'active', 'kr'); // { page: 2, size: 50, filters: ['active', 'kr'] }

// Rest에 직접 기본값을 주면 에러
function bad(...args = []) {}   // SyntaxError
```

인수가 없을 때 `filters`가 `undefined`가 아니라 `[]`로 들어온다는 점이 편하다. 가변 인수는 들어온 게 없어도 `for...of`나 `reduce`를 그냥 돌릴 수 있다.

### 객체 Rest는 얕게, 자체 속성만 수집한다

객체 구조분해의 Rest는 떼고 남은 속성을 새 객체로 모은다. 이때 두 가지를 기억해야 한다. 모인 값은 얕은 복사고, 자체(own) 열거 가능 속성만 들어온다.

```javascript
const source = {
    id: 1,
    nested: { level: 1 },
};
const { id, ...rest } = source;

rest.nested.level = 99;
console.log(source.nested.level);  // 99 — nested는 같은 참조
```

`rest.nested`는 새로 복사된 객체가 아니라 `source.nested`와 같은 참조다. Rest로 민감 필드만 떼어낸 안전한 객체를 만들었다고 안심하고 응답으로 내보냈는데, 중첩 객체 안에 또 민감 정보가 있으면 그대로 새어 나간다. 한 단계만 막아준다는 걸 잊으면 안 된다.

프로토타입에서 상속받은 속성은 Rest에 안 잡힌다. 클래스 인스턴스나 `Object.create`로 만든 객체를 구조분해하면 메서드와 상속 속성은 전부 빠지고 자체 속성만 남는다.

```javascript
class User {
    constructor() { this.name = 'Alice'; }
    greet() {}                       // prototype 메서드
}
const { ...plain } = new User();
console.log(plain);                  // { name: 'Alice' } — greet 없음
```

### function.length는 Rest를 세지 않는다

`fn.length`는 그 함수의 "기대 인수 개수"를 돌려주는데, Rest 파라미터와 기본값이 붙은 파라미터, 그리고 그 뒤의 파라미터는 전부 카운트에서 빠진다.

```javascript
function f(a, b, ...rest) {}
f.length;  // 2 — rest는 안 셈

function g(a, b = 1, c) {}
g.length;  // 1 — 기본값이 붙은 b부터 끝까지 제외
```

평소엔 신경 쓸 일 없지만, 라이브러리가 함수의 arity를 보고 동작을 바꾸는 경우 함정이 된다. Express는 미들웨어 인수가 4개(`err, req, res, next`)면 에러 핸들러로 판단하는데, 이걸 `(...args) => {}` 형태로 감싸면 `length`가 0이라 에러 핸들러로 인식되지 않는다. 커링 라이브러리나 의존성 주입 컨테이너도 `fn.length`로 받을 인수 수를 추정하니, Rest로 함수를 래핑할 때는 arity가 0으로 바뀐다는 걸 알고 있어야 한다.

### 구조분해에서 Rest

```javascript
// 배열 구조분해 + Rest
const [first, second, ...rest] = [1, 2, 3, 4, 5];
// first = 1, second = 2, rest = [3, 4, 5]

// 객체 구조분해 + Rest
const { a, b, ...others } = { a: 1, b: 2, c: 3, d: 4 };
// a = 1, b = 2, others = { c: 3, d: 4 }

// 함수 파라미터 구조분해 + Rest
function process({ id, name, ...metadata }) {
    console.log(id, name);
    console.log(metadata);  // 나머지 속성 전부
}
process({ id: 1, name: 'Alice', age: 30, role: 'admin' });
```

---

## 실무 패턴

### 불변 상태 업데이트 (React/Redux 패턴)

```javascript
// 배열 아이템 추가
const addItem = (list, item) => [...list, item];

// 배열 아이템 제거
const removeItem = (list, id) => list.filter(item => item.id !== id);

// 배열 아이템 수정
const updateItem = (list, id, changes) =>
    list.map(item => item.id === id ? { ...item, ...changes } : item);

// 중첩 객체 업데이트
const state = { user: { name: 'Alice', age: 30 }, theme: 'dark' };
const newState = {
    ...state,
    user: { ...state.user, age: 31 }
};
```

중첩 객체를 바꿀 때 바깥만 스프레드하면 안에 있는 `user`는 이전 참조 그대로다. 그래서 위 예제처럼 바꾸려는 깊이까지 한 단계씩 스프레드를 타고 들어가야 한다. depth가 3단 넘어가면 코드가 지저분해지니 immer 같은 도구를 쓰는 게 낫다.

### 함수 인수 전달 (Forwarding)

```javascript
// props 전달 패턴 (React)
function Button({ onClick, children, ...rest }) {
    return <button onClick={onClick} {...rest}>{children}</button>;
}

// 함수 래핑
function withLogging(fn) {
    return function(...args) {
        console.log('호출:', fn.name, args);
        const result = fn(...args);
        console.log('결과:', result);
        return result;
    };
}
const loggedAdd = withLogging((a, b) => a + b);
loggedAdd(3, 4);  // 호출: ... [3, 4] → 결과: 7
```

함수 래핑은 Rest(인수 모으기)와 Spread(다시 펼치기)를 한 쌍으로 쓰는 전형이다. 다만 위 `withLogging`은 원본 함수의 `length`를 0으로 만들어버리니, arity에 의존하는 코드를 감쌀 때는 위에서 말한 함정을 기억해야 한다.

### API 요청/응답 처리

```javascript
// 쿼리 파라미터 병합
function buildQuery(base, overrides) {
    return { ...base, ...overrides };
}
const query = buildQuery(
    { page: 1, size: 20, sort: 'createdAt' },
    { size: 50, filter: 'active' }
);
// { page: 1, size: 50, sort: 'createdAt', filter: 'active' }

// 민감 필드 제거 후 반환
function sanitizeUser({ password, secretToken, ...safeFields }) {
    return safeFields;
}
const user = sanitizeUser({ id: 1, name: 'Alice', password: 'hashed', secretToken: 'xxx' });
// { id: 1, name: 'Alice' }

// 배열 평탄화 (flat 사용 불가 환경)
const nested = [[1, 2], [3, 4], [5, 6]];
const flat = [].concat(...nested);  // [1, 2, 3, 4, 5, 6]
```

`sanitizeUser` 패턴은 깔끔해 보이지만 앞서 본 객체 Rest의 얕은 수집 때문에 한 단계만 가린다. `safeFields` 안에 또 객체가 있고 그 안에 토큰이 들어 있으면 그대로 빠져나간다. 응답 직렬화 전에 중첩까지 점검하는 게 맞다.

### 배열 유틸리티 패턴

```javascript
// 중복 제거
const dedup = arr => [...new Set(arr)];
dedup([1, 2, 2, 3, 3, 3]);  // [1, 2, 3]

// 배열 앞/뒤에 값 추가
const prepend = (arr, val) => [val, ...arr];
const append = (arr, val) => [...arr, val];

// 배열 특정 인덱스에 삽입
const insertAt = (arr, index, val) => [
    ...arr.slice(0, index),
    val,
    ...arr.slice(index)
];
insertAt([1, 2, 4, 5], 2, 3);  // [1, 2, 3, 4, 5]
```

`[...new Set(arr)]` 중복 제거는 원시값 배열에만 통한다. 객체 배열은 참조로 비교하니 내용이 같아도 다른 객체면 안 걸러진다. 키로 묶어야 하면 `Map`에 키를 넣어 직접 골라야 한다.

---

## TypeScript에서의 사용

```typescript
// 제네릭 타입 보존
function first<T>([head, ...tail]: T[]): [T, T[]] {
    return [head, tail];
}
const [f, rest] = first([1, 2, 3]);  // f: number, rest: number[]

// 객체 타입 병합
type Base = { id: number; name: string };
type Extra = { age: number; role: string };
type User = Base & Extra;

function createUser(base: Base, extra: Partial<Extra>): User {
    return { ...base, age: 0, role: 'user', ...extra };
}

// Readonly 배열 Spread
const nums: readonly number[] = [1, 2, 3];
const extended = [...nums, 4, 5];  // number[] (mutable 복사본)

// 함수 파라미터 타입
function format(template: string, ...values: (string | number)[]): string {
    return values.reduce<string>(
        (str, val, i) => str.replace(`{${i}}`, String(val)),
        template
    );
}
format('Hello {0}, you are {1}', 'Alice', 30);
```

타입스크립트에서 객체 스프레드 병합은 타입상으로는 통과해도 런타임 값과 어긋날 때가 있다. `{ ...base, age: 0, ...extra }`에서 `extra.age`가 런타임에 `undefined`로 들어오면 값은 `undefined`인데 타입은 `number`로 남아, 컴파일러가 못 잡는 구멍이 된다. 외부에서 온 객체를 스프레드로 합칠 때는 타입을 믿지 말고 값 검증을 따로 둔다.

---

## 주의사항

```javascript
// 잘못된 패턴 — 얕은 복사라 중첩 참조가 공유된다
const original = { a: { b: 1 } };
const copy = { ...original };
copy.a.b = 999;
console.log(original.a.b);  // 999 (같은 참조!)

// 권장 패턴 — 깊은 복사가 필요하면 structuredClone (최신 브라우저/Node 17+)
const deep = structuredClone(original);

// 잘못된 패턴 — Rest를 마지막이 아닌 자리에 두면 SyntaxError
// const [first, ...middle, last] = arr;

// 잘못된 패턴 — 객체 스프레드를 배열 자리에 펼치면 이터러블이 아니라 TypeError
// const arr = [...{ a: 1 }];  // TypeError: object is not iterable

// 권장 패턴 — 객체를 배열로 펼치려면 Object.entries/keys/values를 거친다
const entries = [...Object.entries({ a: 1, b: 2 })];
```

가장 자주 사고 나는 건 첫 번째, 얕은 복사다. 스프레드로 복사했으니 원본과 분리됐겠지 하고 중첩 값을 바꾸면 원본까지 바뀐다. 한 단계만 복사된다는 사실을 코드 리뷰에서 매번 짚게 된다.

`structuredClone`은 함수, `Symbol` 키, prototype, class 인스턴스의 클래스성은 복사하지 못하고, 함수가 든 객체를 넣으면 `DataCloneError`를 던진다. 깊은 복사가 항상 만능은 아니라는 점을 알고 써야 한다.

---

## Spread vs Object.assign

겉보기엔 `Object.assign(target, source)`와 `{ ...source }`가 같은 일을 하지만, target을 직접 수정하느냐 새 객체를 만드느냐, getter/setter를 호출하느냐 무시하느냐, symbol 키를 어떻게 다루느냐에서 명세 단계가 갈린다. 이 차이가 Vue 반응성이나 ORM의 dirty tracking이 끊기는 버그로 이어진다. 두 방식의 세부 차이와 성능 비교는 [Spread 연산자 심화 — Object.assign과의 세부 차이](../02_복사_및_스프레드/Spread_Deep_Dive.md#3-objectassign과의-세부-차이)에 정리돼 있다.
