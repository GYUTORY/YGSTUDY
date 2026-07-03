---
title: JavaScript 스코프와 var/let/const
tags:
  - JavaScript
  - Scope
  - var
  - let
  - const
  - Closure
updated: 2026-04-20
---

# JavaScript 스코프와 var/let/const

자바스크립트에서 변수 선언 키워드를 고르는 일은 단순히 취향 문제가 아니다. `var`, `let`, `const`는 각각 다른 스코프 규칙과 재할당 정책을 가지고 있고, 잘못 고르면 프로덕션에서 재현하기 어려운 버그가 터진다. Node.js로 실제 서비스를 운영하다 보면 `for` 루프 안의 비동기 콜백이 이상한 값을 출력하거나, 모듈 어디선가 전역이 오염되어 테스트 순서에 따라 결과가 달라지는 상황을 한 번쯤은 겪는다. 대부분의 원인은 스코프를 잘못 이해한 채 `var`를 남발한 데서 온다.

이 문서에서는 함수 스코프와 블록 스코프가 실제로 어떻게 다른지, `var`가 왜 문제였고 `let`과 `const`가 왜 등장했는지, 그리고 `const`의 불변성이 정확히 무엇을 고정하는지 실제 경험 관점에서 정리한다.

## 스코프란 무엇인가

스코프는 변수가 유효한 범위를 말한다. 자바스크립트는 렉시컬 스코프(lexical scope)를 쓴다. 변수가 어디서 참조 가능한지는 코드가 실행되는 시점이 아니라 작성되는 시점에 결정된다. 함수를 어디서 호출했는지가 아니라 어디서 선언했는지가 중요하다.

```javascript
const name = 'outer';

function printName() {
  console.log(name); // 'outer'
}

function run() {
  const name = 'inner';
  printName(); // 'outer' — 호출 위치의 name이 아니라 선언 위치의 name
}

run();
```

`printName`은 선언될 당시의 바깥 스코프에 있던 `name`을 기억한다. `run` 안에서 다른 `name`을 만들어도 영향을 주지 않는다. 이 원리가 클로저의 기반이 된다.

자바스크립트의 스코프는 크게 세 가지로 나뉜다. 전역 스코프(global scope), 함수 스코프(function scope), 블록 스코프(block scope). 전역과 함수 스코프는 초창기부터 있었지만 블록 스코프는 ES6(2015)에서 `let`과 `const`가 들어오면서 비로소 제대로 된 형태를 갖췄다.

## 함수 스코프 vs 블록 스코프

`var`로 선언한 변수는 함수 스코프를 가진다. `if`, `for`, `while` 같은 블록 안에서 선언해도 가장 가까운 함수 경계까지 끌어올려진다. 반면 `let`과 `const`는 블록 스코프다. `{}`로 감싸진 블록 안에서 선언하면 그 블록을 벗어나는 순간 접근할 수 없다.

```javascript
function example() {
  if (true) {
    var a = 1;
    let b = 2;
    const c = 3;
  }

  console.log(a); // 1 — 블록을 벗어나도 접근 가능
  console.log(b); // ReferenceError: b is not defined
  console.log(c); // ReferenceError: c is not defined
}
```

C, Java, Go 같은 언어에 익숙한 사람이 처음 자바스크립트를 만나면 `var`의 동작에서 당황하는 경우가 많다. 다른 언어에서는 블록 안에서 선언한 변수가 블록 밖으로 새어 나오지 않는 게 상식인데, `var`는 그렇지 않기 때문이다. 이런 차이가 실무에서 어떤 문제를 만드는지 보자.

## var의 문제점 1 — 반복문 클로저

가장 유명한 사례다. `for` 루프 안에서 비동기 작업을 걸고 루프 변수를 참조하면 기대와 다른 값이 나온다.

```javascript
for (var i = 0; i < 3; i++) {
  setTimeout(() => {
    console.log(i);
  }, 100);
}
// 출력: 3, 3, 3
```

처음 보면 당황스럽다. 0, 1, 2가 나올 것 같은데 전부 3이 찍힌다. 이유는 간단하다. `var i`는 함수 스코프라 루프 블록 안이 아니라 바깥 함수(혹은 전역)에 단 하나만 존재한다. `setTimeout`에 넘긴 콜백 세 개는 모두 같은 `i`를 참조하고, 콜백이 실제로 실행되는 시점엔 이미 루프가 끝나 `i`가 3이 된 상태다.

`let`으로 바꾸면 해결된다.

```javascript
for (let i = 0; i < 3; i++) {
  setTimeout(() => {
    console.log(i);
  }, 100);
}
// 출력: 0, 1, 2
```

`let`은 블록 스코프라 루프가 한 번 돌 때마다 새로운 `i`가 생긴다. 정확히는 ES6 명세에서 `for` 루프의 `let` 선언은 매 반복마다 새 바인딩을 만들도록 정의되어 있다. 콜백 세 개가 각자 자기만의 `i`를 참조하게 되니 0, 1, 2가 찍힌다.

`var`로도 해결할 수 있다. IIFE(즉시 실행 함수)를 써서 인위적으로 스코프를 만들면 된다.

```javascript
for (var i = 0; i < 3; i++) {
  (function (j) {
    setTimeout(() => {
      console.log(j);
    }, 100);
  })(i);
}
// 출력: 0, 1, 2
```

ES5 시절에는 이 패턴을 자주 썼다. 지금은 `let`이 있으니 굳이 이럴 필요가 없다. 오래된 코드베이스에 들어가면 이런 IIFE가 곳곳에 박혀 있는데, 대부분 블록 스코프가 없던 시절의 유산이다.

## var의 문제점 2 — 중복 선언과 덮어쓰기

`var`는 같은 스코프에서 여러 번 선언해도 에러가 나지 않는다.

```javascript
var user = 'Alice';
var user = 'Bob'; // 에러 없음, 그냥 덮어쓴다
console.log(user); // 'Bob'
```

규모가 작은 스크립트에서는 문제가 잘 안 보이지만, 파일이 길어지고 팀이 커지면 치명적이다. 누군가 위쪽에 선언한 변수를 아래쪽에서 모르고 다시 선언해 버리면 기존 값이 조용히 덮어써진다. 린터가 없던 시절엔 이런 버그를 찾느라 반나절을 쓰기도 했다.

`let`과 `const`는 같은 스코프에서 재선언하면 `SyntaxError`를 낸다.

```javascript
let user = 'Alice';
let user = 'Bob'; // SyntaxError: Identifier 'user' has already been declared
```

선언 실수를 컴파일/파싱 단계에서 바로 잡아준다. 운영 중인 서비스에서 이런 에러가 늦게 발견될 가능성이 줄어든다.

## var의 문제점 3 — 전역 오염

브라우저 환경에서 `var`를 최상단에서 선언하면 `window` 객체의 프로퍼티가 된다. Node.js의 CommonJS 모듈은 각 파일이 함수로 감싸지기 때문에 전역 오염이 덜하지만, 스크립트 태그로 불러온 코드나 REPL에서는 여전히 일어난다.

```javascript
// 브라우저 환경
var count = 10;
console.log(window.count); // 10

let total = 20;
console.log(window.total); // undefined
```

`var`로 선언한 전역은 `window`를 통해 누구나 덮어쓸 수 있고, 서드파티 스크립트와 이름이 겹치면 충돌이 난다. `let`, `const`는 전역 스코프에서 선언해도 전역 객체의 프로퍼티가 되지 않는다. 모듈 시스템이 자리 잡기 전의 자바스크립트는 이 전역 오염 문제로 악명이 높았다.

## let과 const의 등장 배경

ES6가 설계될 때 가장 큰 과제 중 하나는 "기존 코드를 깨뜨리지 않으면서 `var`의 문제를 해결한다"였다. `var`의 동작을 바꿀 수는 없었다. 이미 수많은 웹페이지가 그 동작에 의존하고 있었기 때문이다. 그래서 새로운 키워드를 도입하는 방향으로 갔다.

`let`은 블록 스코프를 가지면서 재할당은 허용하는 변수다. `const`는 블록 스코프에 재할당까지 금지한다. 이름은 수학이나 다른 언어의 관례에서 따왔다. `let x = 5`는 "x를 5라고 두자"는 선언적 느낌이고, `const`는 상수(constant)다.

여기에 TDZ(Temporal Dead Zone)라는 개념도 함께 들어왔다. `let`과 `const`로 선언한 변수는 스코프 시작 지점부터 실제 선언문에 도달할 때까지 접근할 수 없다. 접근하면 `ReferenceError`가 난다.

```javascript
console.log(x); // ReferenceError: Cannot access 'x' before initialization
let x = 5;
```

`var`는 같은 상황에서 `undefined`를 돌려주지만 `let`/`const`는 에러를 던진다. 이 동작 덕분에 선언 전 사용이라는 실수를 런타임에서 바로 잡을 수 있다.

## const 불변성의 실제 의미

많이 오해하는 부분이다. `const`로 선언한 변수는 재할당이 불가능할 뿐, 값 자체가 불변이 되는 건 아니다. 참조(바인딩)가 고정되는 것이고, 그 참조가 가리키는 객체의 내부 상태는 여전히 바꿀 수 있다.

```javascript
const user = { name: 'Alice', age: 30 };

user.age = 31;        // 정상 동작 — 객체의 프로퍼티는 변경 가능
user.name = 'Bob';    // 정상 동작

user = { name: 'Carol' }; // TypeError: Assignment to constant variable.
```

배열도 마찬가지다.

```javascript
const nums = [1, 2, 3];
nums.push(4);        // 정상 — [1, 2, 3, 4]
nums[0] = 100;       // 정상 — [100, 2, 3, 4]
nums = [];           // TypeError
```

`const`는 "이 식별자가 가리키는 참조를 바꾸지 마라"라는 의미지 "이 값은 변하지 않는다"가 아니다. 처음 자바스크립트를 배우는 사람이 "객체를 `const`로 선언했는데 왜 값이 바뀌지?"라고 혼란을 겪는 경우가 많다.

내부 상태까지 정말로 고정하고 싶다면 별도의 수단이 필요하다. 얕은 수준의 동결은 `Object.freeze`로 가능하다.

```javascript
const config = Object.freeze({
  port: 3000,
  host: 'localhost',
});

config.port = 4000; // strict mode면 TypeError, sloppy mode면 조용히 무시
console.log(config.port); // 3000
```

다만 `Object.freeze`는 얕다. 중첩된 객체의 내부까지 얼리려면 재귀적으로 freeze를 적용하거나 immutable 라이브러리(Immer, immutable.js 등)를 쓰는 편이 낫다. TypeScript를 쓴다면 `readonly` 수식어나 `as const`로 타입 수준에서 불변성을 강제하는 방법도 있다.

## 실무 권장 사용 패턴

5년 정도 백엔드에서 Node.js를 다루면서 굳어진 원칙이 몇 개 있다.

첫째, 기본적으로 `const`를 쓴다. 재할당이 필요 없는 변수에 `const`를 쓰면 코드 리뷰어가 "이 변수는 여기서부터 끝까지 같은 값을 가리킨다"는 걸 바로 알 수 있다. 읽기 쉬워진다. 실제로 대부분의 지역 변수는 재할당되지 않는다.

```javascript
function formatUser(user) {
  const fullName = `${user.firstName} ${user.lastName}`;
  const age = new Date().getFullYear() - user.birthYear;
  return { fullName, age };
}
```

둘째, 재할당이 필요할 때만 `let`을 쓴다. 루프의 카운터나 조건에 따라 값이 바뀌는 변수, 누적 계산 변수 같은 경우다.

```javascript
function sum(numbers) {
  let total = 0;
  for (const n of numbers) {
    total += n;
  }
  return total;
}
```

참고로 위 코드는 `numbers.reduce((a, b) => a + b, 0)`으로 바꾸면 `let` 없이도 쓸 수 있다. 함수형 스타일로 작성하면 `let`을 쓸 일이 자연스럽게 줄어든다.

셋째, `var`는 쓰지 않는다. 신규 코드에서 `var`를 쓸 이유는 거의 없다. 아주 오래된 브라우저를 타겟으로 하거나, 특정 레거시 패턴을 유지 보수하는 경우가 아니라면 피하는 게 맞다. ESLint의 `no-var` 규칙을 켜두면 PR 단계에서 걸러진다.

넷째, 객체를 `const`로 선언했다고 안심하지 말 것. 공유되는 상태를 다룰 때는 참조가 고정된다는 점과 내부가 변경 가능하다는 점을 구분해서 설계해야 한다. 특히 모듈 레벨에서 `const` 객체를 export하면 다른 모듈에서 내부를 바꿀 수 있다. 이런 걸로 추적하기 어려운 버그가 생긴다.

```javascript
// config.js
export const config = {
  timeout: 5000,
};

// 다른 모듈에서
import { config } from './config.js';
config.timeout = 1; // 아무도 모르게 설정이 바뀐다
```

설정 객체처럼 공유되는 값은 `Object.freeze`를 쓰거나, 접근자 함수로 감싸서 읽기 전용으로 만드는 편이 안전하다.

다섯째, 블록 스코프를 적극적으로 활용한다. `switch` 문의 `case` 안에서 변수를 선언할 때는 블록으로 감싸는 습관을 들이면 좋다. `case`는 기본적으로 블록이 아니라서 `let`/`const`로 선언해도 같은 `switch` 전체에서 이름이 충돌한다.

```javascript
switch (type) {
  case 'A': {
    const data = loadA();
    process(data);
    break;
  }
  case 'B': {
    const data = loadB(); // 블록으로 감쌌기 때문에 충돌 없음
    process(data);
    break;
  }
}
```

## 정리

자바스크립트의 스코프 규칙은 언어 초기의 설계 결정과 ES6의 개선이 공존하는 형태다. `var`는 함수 스코프와 호이스팅, 재선언 허용 같은 특성 때문에 지금 기준으로는 쓰기 불편하고 위험하다. `let`과 `const`는 블록 스코프, TDZ, 재선언 금지로 이런 문제를 잡아주고, 여기에 `const`의 재할당 금지가 더해지면서 코드 의도가 훨씬 명확해졌다.

다만 `const`가 "값의 불변성"을 보장하지 않는다는 점은 꼭 기억해야 한다. 참조만 고정할 뿐이라서 객체나 배열의 내부는 그대로 변경 가능하다. 진짜로 불변이 필요하다면 `Object.freeze`나 불변 자료구조 라이브러리를 쓰거나, 타입 시스템에서 `readonly`로 강제하는 방법을 고려해야 한다.

신규 코드에서는 `const`를 기본으로 쓰고, 재할당이 반드시 필요한 자리에만 `let`을 쓴다. `var`는 특별한 이유가 없는 한 쓰지 않는다. 이 원칙 하나만 지켜도 스코프 때문에 생기는 버그의 대부분이 사라진다.
