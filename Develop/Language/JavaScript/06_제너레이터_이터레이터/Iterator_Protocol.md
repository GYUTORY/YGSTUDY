---
title: 이터레이터 프로토콜과 커스텀 이터러블
tags: [javascript, language]
updated: 2026-08-24
---

# 이터레이터 프로토콜과 커스텀 이터러블

`for...of`, 스프레드 연산자, 구조분해 할당이 어떻게 **어떤 객체든** 순회할 수 있는지를 이터레이터 프로토콜이 설명한다.

---

## 두 가지 프로토콜

### Iterable Protocol

`Symbol.iterator` 메서드를 구현하면 **이터러블**이다.
호출 결과로 **이터레이터**를 반환해야 한다.

```js
const iterable = {
  [Symbol.iterator]() {
    return iterator; // ← 이터레이터 반환
  }
};
```

### Iterator Protocol

`next()` 메서드를 구현한 객체가 **이터레이터**다.
`next()`는 `{ value, done }` 형태의 객체를 반환한다.

```js
const iterator = {
  next() {
    return { value: 42, done: false };
    // 또는 종료 시: { value: undefined, done: true }
  }
};
```

---

## 내장 이터러블

JavaScript 표준 내장 타입 중 이터러블인 것들:

```js
// Array
for (const x of [1, 2, 3]) { ... }

// String — 유니코드 코드 포인트 단위
for (const ch of "안녕") { console.log(ch); } // 안, 녕

// Map / Set
const m = new Map([['a', 1], ['b', 2]]);
for (const [k, v] of m) { ... }

// arguments 객체 (유사 배열 — 이터러블이기도 함)
function fn() {
  for (const arg of arguments) { ... }
}
```

---

## 커스텀 이터러블 만들기

### 범위(Range) 이터러블

```js
function range(start, end, step = 1) {
  return {
    [Symbol.iterator]() {
      let current = start;
      return {
        next() {
          if (current <= end) {
            const value = current;
            current += step;
            return { value, done: false };
          }
          return { value: undefined, done: true };
        }
      };
    }
  };
}

for (const n of range(1, 10, 2)) {
  console.log(n); // 1 3 5 7 9
}

console.log([...range(0, 4)]); // [0, 1, 2, 3, 4]
```

### 클래스로 구현

이터러블 자신이 이터레이터도 되게 하는 패턴 — `[Symbol.iterator]()` 가 `this`를 반환한다:

```js
class InfiniteCounter {
  #current = 0;

  [Symbol.iterator]() {
    return this; // 자기 자신이 이터레이터
  }

  next() {
    return { value: this.#current++, done: false };
  }

  return() {
    // for...of가 break로 중단될 때 호출됨 (선택적)
    return { done: true };
  }
}

const counter = new InfiniteCounter();
for (const n of counter) {
  if (n >= 5) break;
  console.log(n); // 0 1 2 3 4
}
```

---

## 지연 평가(Lazy Evaluation)

이터레이터의 핵심 장점: **필요한 만큼만** 계산한다.

```js
function* naturals() {
  let n = 1;
  while (true) yield n++;
}

// 무한 시퀀스지만 take 5개만 꺼낸다
function take(iterable, n) {
  const result = [];
  for (const x of iterable) {
    result.push(x);
    if (result.length === n) break;
  }
  return result;
}

console.log(take(naturals(), 5)); // [1, 2, 3, 4, 5]
```

배열 버전과 비교:
- 배열: 100만 개 미리 생성 → 메모리 ∝ 전체 크기
- 이터레이터: 필요한 것만 생성 → 메모리 O(1)

---

## 이터레이터 컴비네이터 패턴

이터레이터를 감싸는 변환 이터레이터를 직접 만들면 체이닝이 가능하다:

```js
function map(iterable, fn) {
  return {
    [Symbol.iterator]() {
      const iter = iterable[Symbol.iterator]();
      return {
        next() {
          const { value, done } = iter.next();
          return done ? { value, done } : { value: fn(value), done };
        }
      };
    }
  };
}

function filter(iterable, pred) {
  return {
    [Symbol.iterator]() {
      const iter = iterable[Symbol.iterator]();
      return {
        next() {
          while (true) {
            const { value, done } = iter.next();
            if (done) return { value, done };
            if (pred(value)) return { value, done };
          }
        }
      };
    }
  };
}

// 사용
const result = [
  ...filter(
    map(range(1, 20), x => x * x),
    x => x % 2 === 0
  )
];
// [4, 16, 36, 64, 100, 144, 196, 256, 324, 400]
```

---

## `for...of` vs `forEach` vs `for`

| 구분 | `for...of` | `forEach` | `for` |
|------|-----------|-----------|-------|
| 이터러블 지원 | ✅ 모든 이터러블 | ❌ 배열만 | ❌ 인덱스 객체만 |
| `break` / `continue` | ✅ | ❌ | ✅ |
| `async/await` | ✅ (for await) | ⚠️ 주의 필요 | ✅ |
| 성능 | 일반적으로 충분 | V8 최적화 잘 됨 | 가장 낮은 오버헤드 |

---

## `for await...of` — 비동기 이터러블

`Symbol.asyncIterator`를 구현하면 비동기 스트림을 표현할 수 있다:

```js
async function* paginate(url) {
  let page = 1;
  while (true) {
    const res = await fetch(`${url}?page=${page}`);
    const data = await res.json();
    if (!data.items.length) return;
    yield* data.items;
    page++;
  }
}

for await (const item of paginate('/api/posts')) {
  console.log(item);
}
```

---

## 요약

- **이터러블**: `Symbol.iterator`를 구현한 객체. `for...of`, 스프레드, 구조분해에 쓸 수 있다.
- **이터레이터**: `next()` → `{ value, done }`을 반환하는 객체.
- 지연 평가 덕분에 무한 시퀀스를 메모리 걱정 없이 다룰 수 있다.
- `for await...of` + `Symbol.asyncIterator`로 비동기 스트림도 같은 문법으로 처리한다.
