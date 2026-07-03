---
title: JavaScript 클로저와 렉시컬 스코프 심화 가이드
tags: [language, javascript, closure, lexical-scope, v8, memory-leak, react-hooks]
updated: 2026-04-25
---

# JavaScript 클로저와 렉시컬 스코프 심화 가이드

클로저는 입문서에서 "함수가 외부 변수를 기억한다"로 끝나지만, 실제로 프로덕션에서 메모리 누수를 추적하거나 React에서 stale closure로 4시간씩 헤매고 나면 그 한 줄 설명이 얼마나 부족한지 깨닫게 된다. 이 문서는 ECMAScript 명세 수준의 정의에서 시작해 V8 엔진의 실제 구현, 그리고 5년차 백엔드 개발자가 Node.js 서비스와 React Admin을 다루면서 실제로 겪었던 문제들을 다룬다.

## 실행 컨텍스트와 렉시컬 환경의 실체

### LexicalEnvironment와 VariableEnvironment

ECMAScript 명세에서 모든 실행 컨텍스트(Execution Context)는 두 개의 환경 컴포넌트를 가진다. LexicalEnvironment와 VariableEnvironment다. ES5까지는 두 환경이 분리된 의미를 가졌지만, ES6 이후에는 사실상 LexicalEnvironment 하나만 활성 환경으로 동작하고 VariableEnvironment는 `var` 선언과 함수 선언을 담는 별도 레코드 역할만 남았다.

각 환경은 두 개의 슬롯으로 구성된다. EnvironmentRecord(식별자-값 매핑을 보관)와 OuterEnv 참조(외부 환경을 가리키는 포인터)다. 이 OuterEnv 체인이 곧 스코프 체인이다.

```javascript
function outer() {
  const a = 1;
  function inner() {
    const b = 2;
    return a + b;
  }
  return inner;
}

const fn = outer();
fn(); // 3
```

`inner`가 실행될 때 자신의 LexicalEnvironment에는 `b`만 있다. `a`를 찾으려면 OuterEnv를 따라 `outer`의 환경까지 올라가야 한다. `outer`가 이미 반환됐는데도 `a`에 접근할 수 있는 이유는, `inner`가 자기 내부 슬롯 `[[Environment]]`에 `outer`의 LexicalEnvironment 참조를 박아두고 있기 때문이다.

### [[Environment]] 내부 슬롯

함수 객체가 생성되는 시점, 그러니까 `function` 선언이나 함수 표현식이 평가되는 시점에 엔진은 그 함수 객체에 `[[Environment]]`라는 내부 슬롯을 만들고 현재 활성 LexicalEnvironment를 거기에 저장한다. 이 슬롯은 사용자 코드에서 직접 접근할 수 없지만 명세상 함수 객체가 반드시 가져야 하는 필드다.

함수가 호출될 때 새로 만들어지는 실행 컨텍스트의 LexicalEnvironment는 두 부분으로 조립된다. 새로 만든 EnvironmentRecord(파라미터와 지역 변수)와 OuterEnv = 함수 객체의 `[[Environment]]`다. 즉 함수가 어디서 호출됐느냐가 아니라 어디서 정의됐느냐가 스코프를 결정한다는 렉시컬 스코프의 본질이 바로 이 슬롯에 있다.

이 차이가 실무에서 의외로 중요한 이유는 Node.js의 `require()`로 불러온 모듈이 다른 모듈의 함수를 호출할 때 그 함수의 스코프가 호출자가 아니라 정의된 모듈의 스코프를 따른다는 점이다. 모듈 A에서 정의된 함수가 모듈 B의 변수를 읽는 일은 절대 일어나지 않는다.

## V8 엔진의 실제 구현

### Context 객체와 ScopeInfo

명세상의 LexicalEnvironment를 V8은 두 개의 내부 자료구조로 구현한다. `Context`(런타임 객체)와 `ScopeInfo`(컴파일 타임 메타데이터)다.

`Context`는 힙에 할당되는 일반 JS 객체와 비슷한 구조를 가진다. 고정 슬롯들(`previous`, `extension`, `native_context` 등)과 함께 캡처된 변수들을 위한 슬롯이 이어진다. 즉 클로저 변수는 함수 내부의 임의 객체 어딘가에 떠 있는 게 아니라, V8 힙에 할당된 `Context` 객체의 명시적인 슬롯에 박혀 있다.

`ScopeInfo`는 컴파일 시점에 만들어지는 불변(immutable) 객체로, 어떤 변수가 어느 슬롯 인덱스에 있는지, 어떤 변수가 캡처되는지, 변수 타입(let, const, var) 등을 기록한다. V8 코드 베이스에서 `src/objects/scope-info.cc`를 보면 이 자료구조의 실제 정의가 있다.

V8은 **모든 변수에 대해 Context를 만들지 않는다**. 클로저로 캡처되지 않는 지역 변수는 그냥 레지스터나 스택 슬롯에 들어간다. 컴파일러가 함수 본문을 분석해서 "이 변수는 내부 함수에서 참조됨"으로 판정한 변수만 Context 슬롯에 할당된다. 이걸 V8 내부에서는 `IsContextSlot` 분류라고 한다.

```javascript
function makeCounter() {
  let count = 0;        // 캡처됨 → Context slot
  let unused = 'temp';  // 캡처 안됨 → 스택 (또는 즉시 dead)
  return () => ++count;
}
```

`unused`는 어디에서도 캡처되지 않으므로 V8은 이걸 Context에 넣지 않는다. 따라서 `makeCounter()`가 반환한 클로저가 살아있어도 `unused`는 GC된다. 이 최적화 덕분에 함수 안에 큰 객체를 잠깐 선언하고 캡처되지 않으면 메모리 부담은 없다.

### 스코프 체인 탐색 비용

스코프 체인은 연결 리스트다. 변수 `x`를 찾을 때 엔진은 현재 Context의 ScopeInfo에서 `x`를 찾고, 없으면 `previous`로 한 칸 올라가서 또 찾는다. 글로벌 스코프까지 가면 결국 글로벌 객체의 프로퍼티 룩업까지 동반된다.

수치적으로는 한 칸당 수 나노초 수준이지만, 핫 루프에서 4~5단계 깊이의 클로저 변수를 매번 읽으면 측정 가능한 수준이 된다. 5년차쯤 되면 마이크로 최적화에 매달리지 말라는 게 몸에 배지만, 이미지 처리 워커에서 100만 회 반복문 안의 깊은 클로저 변수를 지역 변수로 끌어내려서 30%를 깎은 적이 있다.

```javascript
function processor(config) {
  return function(data) {
    return function(item) {
      // 핫루프
      for (let i = 0; i < item.length; i++) {
        // config.threshold는 2단계 위 Context
        if (item[i] > config.threshold) { /* ... */ }
      }
    };
  };
}

// 개선
function processor(config) {
  return function(data) {
    return function(item) {
      const threshold = config.threshold;  // 한 번만 룩업
      for (let i = 0; i < item.length; i++) {
        if (item[i] > threshold) { /* ... */ }
      }
    };
  };
}
```

물론 V8의 TurboFan은 이런 패턴 일부를 자동으로 호이스팅하지만, 함수가 인라인되지 않거나 다형성(polymorphic) IC에 걸리면 최적화가 깨진다. 측정 없이 손으로 끌어내리는 건 시간 낭비다.

## 클로저가 GC에 잡히지 않는 진짜 메커니즘

### 루트 도달성

JS의 GC는 mark-and-sweep 계열이다. "참조되지 않으면 수거된다"는 표현은 부정확하고, 정확히는 "GC 루트로부터 도달 가능하지 않으면 수거된다"가 맞다. GC 루트는 글로벌 객체, 실행 중인 함수의 스택, DOM 트리, 활성 Promise 큐, 타이머 콜백 등이다.

클로저 메모리 누수의 본질은 단순하다. 어떤 함수 객체가 GC 루트에서 도달 가능하면, 그 함수의 `[[Environment]]`가 가리키는 Context도 도달 가능하고, 그 Context 안의 모든 캡처 변수가 살아남는다. 그게 1MB짜리 버퍼든 DOM 노드든 상관없다.

```javascript
const cache = new Map();

function loadUser(id) {
  const heavyData = new Array(1_000_000).fill(0);  // 8MB
  
  return function getName() {
    return heavyData[0]; // heavyData 전체를 캡처
  };
}

cache.set(1, loadUser(1));
// cache가 살아있는 한 8MB 배열이 GC되지 않음
```

여기서 흥미로운 건 V8의 변수별 캡처 분석이다. `getName`이 `heavyData[0]`만 쓴다고 해서 V8이 그 한 칸만 살려두지는 않는다. 변수 단위로 캡처되므로 `heavyData` 전체가 살아남는다. 만약 `getName` 옆에 `heavyData`를 사용하지 않는 다른 함수가 있고, 그 함수만 외부로 노출되더라도 V8이 영리하게 처리하지 못하는 경우가 있다. 이게 다음 절의 ScopeInfo 공유 문제로 이어진다.

### 형제 클로저의 의도치 않은 캡처

```javascript
function createHandlers() {
  const big = new Array(1_000_000);
  const small = 'hello';
  
  return {
    a: () => big.length,    // big 캡처
    b: () => small,          // small만 사용 — 그러나?
  };
}
```

명세적으로는 `b`가 `big`을 캡처할 이유가 없다. 하지만 V8의 구현에서 두 함수는 같은 Context를 공유한다. 즉 `b`의 `[[Environment]]`도 `big`을 담은 Context를 가리킨다. `b`만 외부로 살려두고 `a`를 버려도 Context는 살아있고 따라서 `big`도 살아있다.

V8은 이 케이스에 대한 부분적 최적화를 가지고 있다. Crankshaft 시절부터 `b`가 사용하는 변수만 별도 Context로 분리하는 시도가 있었지만 실제로는 보수적이다. Chrome DevTools에서 `b`만 남기고 Heap snapshot을 찍어보면 `big`이 그대로 보인다. 이 문제를 처음 발견했을 때는 V8 버그라고 생각했는데, 명세 위반이 아니라 구현 트레이드오프다.

해결은 단순하다. 변수의 수명을 분리하라.

```javascript
function createHandlers() {
  const a = (() => {
    const big = new Array(1_000_000);
    return () => big.length;
  })();
  const b = (() => {
    const small = 'hello';
    return () => small;
  })();
  return { a, b };
}
```

## Chrome DevTools로 클로저 디버깅하기

### Scope 패널 읽는 법

Sources 탭에서 함수 안에 브레이크포인트를 걸면 우측 Scope 패널에 현재 활성 환경이 트리로 표시된다. `Local`, `Closure (함수명)`, `Script`, `Global` 순서로 쌓이는데 이게 곧 OuterEnv 체인이다.

`Closure (outer)`처럼 표시되는 항목은 그 함수의 `[[Environment]]`가 가리키는 외부 함수의 Context다. 여기서 변수 이름과 값을 직접 확인할 수 있고, 콘솔에서 그 식별자를 입력하면 현재 스코프 체인을 따라 해당 변수를 평가한다.

실무에서 자주 쓰는 흐름은 이렇다.

1. 의심스러운 함수에 `debugger;` 또는 conditional breakpoint를 건다
2. 함수 진입 시 Scope 패널에서 캡처된 변수 목록을 확인한다
3. 예상보다 많은 변수가 캡처돼 있으면 그게 곧 누수 원인 후보다
4. `Console`에서 `%DebugPrint(fn)` (Node.js + `--allow-natives-syntax`) 또는 DevTools의 함수 우클릭 → `Reveal function definition`으로 정의 위치를 확인한다

### Memory 탭의 Heap snapshot

Memory 탭에서 "Heap snapshot"을 찍으면 모든 객체의 retained size와 retainer chain을 볼 수 있다. 클로저 누수를 추적할 때 핵심은 두 가지다.

`(closure)` 타입으로 분류되는 노드들이 Function 객체이고, 각 closure의 `context` 슬롯을 펼치면 캡처된 변수들이 보인다. Retainers 탭으로 거꾸로 추적하면 GC 루트까지 이어지는 경로가 나온다. 이 경로에서 끊어내야 할 참조를 찾는 게 디버깅의 본질이다.

세 번 찍기(3-snapshot 기법)는 누수 검출에 자주 쓴다. 페이지 로드 직후, 의심 동작을 N번 반복한 직후, 다시 한 번 반복한 직후의 스냅샷을 비교하면 두 번째와 세 번째 사이에서 누적된 객체가 누수 후보다.

## React Hooks의 stale closure 문제

### 왜 발생하는가

함수 컴포넌트는 매 렌더마다 새로 호출된다. 컴포넌트 함수가 호출될 때마다 그 안의 `useEffect`, `useCallback`, 이벤트 핸들러는 그 시점의 props/state를 캡처한 새 함수 객체로 만들어진다.

문제는 `useEffect(fn, [])`처럼 의존성 배열을 비워두면 React가 첫 렌더 때 만들어진 `fn`을 계속 들고 있다는 점이다. 그 `fn`의 `[[Environment]]`는 첫 렌더의 컴포넌트 함수 호출 컨텍스트를 가리키므로, 안에서 참조하는 state는 영원히 첫 렌더 때 값이다.

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const id = setInterval(() => {
      console.log(count);  // 항상 0
    }, 1000);
    return () => clearInterval(id);
  }, []);
  
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

이게 말로는 잘 와닿지 않지만 클로저 메커니즘으로 보면 자명하다. `setInterval` 콜백의 `[[Environment]]`는 첫 렌더 때의 LexicalEnvironment를 가리킨다. 그 환경의 `count` 슬롯은 0이고, 두 번째 렌더에서는 그 환경이 아니라 **새로** 만들어진 환경의 `count` 슬롯이 1이다. 두 환경은 별개의 Context 객체다.

### useRef로 우회하기

`useRef`는 컴포넌트 인스턴스 수명 동안 동일한 객체를 반환한다. 즉 `ref.current`로 접근하면 항상 최신 값을 읽을 수 있다.

```jsx
function Counter() {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);
  countRef.current = count;  // 매 렌더마다 동기화
  
  useEffect(() => {
    const id = setInterval(() => {
      console.log(countRef.current);  // 최신 값
    }, 1000);
    return () => clearInterval(id);
  }, []);
  
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

여기서 클로저는 여전히 `countRef`를 캡처하지만, `countRef`는 컴포넌트가 언마운트될 때까지 같은 객체이고 그 객체의 `current` 프로퍼티만 매 렌더마다 업데이트된다. 클로저는 객체 참조를 잡고 있을 뿐이고 객체의 내용은 외부에서 갱신된다.

### 함수형 setState

State 업데이트가 이전 state에만 의존한다면 함수형 setState로 클로저 캡처 자체를 피할 수 있다.

```jsx
useEffect(() => {
  const id = setInterval(() => {
    setCount(prev => prev + 1);  // count 캡처 안 함
  }, 1000);
  return () => clearInterval(id);
}, []);
```

`prev`는 React가 호출 시점에 주입하므로 외부 state를 참조할 필요가 없다. 콜백이 아무것도 캡처하지 않으니 stale 문제도 없다. 다만 다른 state나 props에 동시에 의존해야 하면 ref 패턴으로 가야 한다.

## 이벤트 리스너와 detached DOM 누수

### 발생 메커니즘

DOM 노드를 제거해도 그 노드를 참조하는 JS가 살아있으면 노드는 메모리에 남는다. 이걸 detached DOM이라고 한다. 클로저는 이 누수의 단골 원인이다.

```javascript
function attachHandler() {
  const giant = new Array(1_000_000);
  const node = document.getElementById('btn');
  
  node.addEventListener('click', function() {
    console.log(giant.length);
  });
}
attachHandler();
document.getElementById('btn').remove();
```

`btn`을 DOM에서 제거해도 다음 체인이 끊어지지 않는다. 글로벌 EventTarget 매니저 또는 노드 자체에 등록된 리스너 → 리스너 함수 → 리스너의 `[[Environment]]` → `node`와 `giant`. 노드는 detached 상태로 살아있고 8MB 배열도 함께 살아있다.

해결은 `removeEventListener` 명시 호출, 또는 `AbortController` 사용이다.

```javascript
const controller = new AbortController();
node.addEventListener('click', handler, { signal: controller.signal });

// 정리 시점
controller.abort();
```

React에서는 `useEffect`의 cleanup 함수에서 반드시 리스너를 제거한다. 안 그러면 라우트 전환할 때마다 리스너가 누적되고, 매 누적마다 그때의 props/state 클로저가 붙어서 메모리가 우상향한다. 4시간 정도 SPA를 띄워두면 1GB 넘는 사례를 본 적이 있다.

### Heap snapshot으로 detached 노드 찾기

Memory 탭에서 snapshot을 찍은 뒤 상단 필터에 `Detached`를 입력하면 `Detached HTMLDivElement` 같은 항목들이 나온다. 각 항목의 retainer를 따라가면 어떤 클로저나 클로저 안의 어떤 변수가 노드를 붙잡고 있는지 알 수 있다.

흔히 보는 retainer 패턴은 `system / Context` 노드를 거쳐 함수까지 이어진다. 이 함수의 정의 위치를 보면 어디서 리스너를 등록하고 정리를 안 했는지 바로 보인다.

## 타이머와 Promise의 캡처 변수

### setInterval/setTimeout

타이머 콜백은 콜백이 실행되는 동안만 도달 가능한 게 아니라 등록된 시점부터 clear 또는 fire(timeout 한정)까지 GC 루트에 들어간다. 등록 시점에 캡처된 변수가 그동안 통째로 살아있다는 뜻이다.

```javascript
function startPolling(largeContext) {
  setInterval(() => {
    fetch('/api', { headers: { 'X-Trace': largeContext.traceId } });
  }, 5000);
}
```

`startPolling`이 호출되고 함수가 종료되어도 `largeContext`는 GC되지 않는다. clear할 핸들조차 외부로 노출하지 않았다면 페이지가 닫힐 때까지 살아있다.

이런 코드에서 "왜 메모리가 안 줄지?"라는 질문을 받으면 보통 두 가지를 의심한다. 타이머 정리 누락과 클로저로 끌고 들어간 큰 객체. 두 번째 경우 콜백 안에서 정말 필요한 값만 별도 변수로 분리하고 큰 객체 참조를 끊으면 된다.

```javascript
function startPolling(largeContext) {
  const traceId = largeContext.traceId;  // 필요한 값만 추출
  setInterval(() => {
    fetch('/api', { headers: { 'X-Trace': traceId } });
  }, 5000);
}
```

이제 콜백의 `[[Environment]]`는 `traceId`만 잡고 있다. `largeContext`는 `startPolling` 종료와 함께 회수 가능해진다.

### Promise 체인

Promise는 settle된 후에도 체인 연결과 핸들러가 잠시 살아있다. 더 큰 문제는 미해결 Promise다.

```javascript
function setup() {
  const heavy = new Array(1_000_000);
  return new Promise((resolve) => {
    document.getElementById('btn').onclick = () => {
      resolve(heavy[0]);
    };
  });
}
```

이 Promise는 클릭이 있을 때까지 영원히 pending이다. resolve 함수가 클로저로 `heavy`를 잡고 있고, resolve 함수는 Promise 내부 슬롯에 박혀 있다. Promise를 외부에서 참조하지 않더라도 V8은 onclick 콜백이 살아있는 한 resolve를 살려둔다.

긴 체인에서도 비슷한 문제가 있다. `.then(...).then(...)`이 길게 이어지면 각 단계의 핸들러는 자신의 정의 시점 환경을 캡처한다. 한 단계의 결과가 다음 단계로만 흐르고 끝났다면 이전 핸들러들은 빨리 제거되지만, 어디선가 chain reference를 외부에서 들고 있으면 모든 단계가 살아있다.

## var와 let의 반복문 캡처 차이

### 명세적 차이

`var`는 함수 스코프 또는 글로벌 스코프에 한 번만 바인딩된다. for 문의 `var i`는 모든 반복에서 같은 바인딩을 공유한다. `let`은 블록 스코프이고, **for 문에 한해** 매 반복마다 새로운 바인딩이 만들어진다는 특별 규칙이 있다(ES6 § 13.7.4.7).

```javascript
const fnsVar = [];
for (var i = 0; i < 3; i++) fnsVar.push(() => i);
fnsVar.map(f => f()); // [3, 3, 3]

const fnsLet = [];
for (let j = 0; j < 3; j++) fnsLet.push(() => j);
fnsLet.map(f => f()); // [0, 1, 2]
```

### V8 바이트코드 수준 동작

V8의 인터프리터 Ignition은 JS를 바이트코드로 컴파일한다. `var` 버전과 `let` 버전을 `--print-bytecode`로 찍어보면 차이가 보인다.

`var` 루프는 `i`를 바깥 함수의 Context 슬롯에 한 번 만들고, 클로저 생성 시 그 슬롯을 가리키는 Context 참조를 박는다. 모든 클로저가 같은 슬롯을 본다.

`let` 루프는 매 반복 시작 시점에 `CreateBlockContext` 같은 명령으로 **새 Context를 생성**하고, 새 슬롯에 `j`를 복사 또는 초기화한다. 그 반복에서 만들어진 클로저는 그 새 Context의 슬롯을 캡처한다. 다음 반복은 또 다른 Context를 만든다.

이게 무료가 아니다. `let`이 `var`보다 살짝 비싸다. 하지만 정확성을 위해 거의 항상 `let`을 쓰고, 캡처가 일어나지 않는 단순 카운터에서는 V8이 `let`을 사실상 `var`처럼 최적화하기도 한다(escape analysis).

## IIFE 모듈 패턴과 ES Modules

### IIFE의 본질

ES Modules가 표준화되기 전에는 클로저로 모듈 시스템을 직접 만들었다. IIFE(Immediately Invoked Function Expression)가 그 도구다.

```javascript
const Counter = (function() {
  let count = 0;
  return {
    increment: () => ++count,
    get: () => count,
  };
})();
```

`count`는 IIFE의 LexicalEnvironment에 갇혀 있고, 외부로는 두 메서드만 노출된다. 이게 진짜 private이다. JS 명세상 도달 불가능한 변수다.

### ES Modules와의 비교

ES Modules는 모듈 자체가 별도의 모듈 환경(Module Environment Record)을 가진다. `export`되지 않은 모듈 최상위 변수는 외부에서 접근할 수 없다.

```javascript
// counter.js
let count = 0;
export const increment = () => ++count;
export const get = () => count;
```

기능적으로 IIFE와 동일하지만 차이점이 있다. ES Modules는 정적 분석이 가능하다. 빌드 타임에 export/import 관계가 결정되므로 트리쉐이킹이 동작한다. IIFE는 런타임에 객체로 노출되기 때문에 번들러가 미사용 메서드를 제거하기 어렵다.

다른 차이는 export된 바인딩의 라이브성이다. ES Modules의 export는 "live binding"이다. import한 쪽에서 `count` 자체를 직접 import할 수는 없지만, getter처럼 동작하는 함수를 통해 항상 최신 값을 본다. IIFE는 객체의 프로퍼티 룩업이라 동등하지만 의미론적으로는 다르다.

신규 코드에서 IIFE 모듈 패턴을 쓸 일은 거의 없다. 다만 특정 함수의 일회성 로컬 스코프가 필요할 때(예: switch 안에서 `let` 선언)나 즉시 실행 후 값만 남기고 싶을 때는 여전히 유용하다.

## 클로저 vs class private 필드

### 메모리 모델 차이

클로저로 private을 구현하면 인스턴스마다 별도의 Context가 만들어진다. 인스턴스가 N개면 Context도 N개다.

```javascript
function makeCounter() {
  let count = 0;
  return {
    increment() { return ++count; },
    get() { return count; },
  };
}
```

`makeCounter()` 호출마다 `count` 슬롯을 가진 Context와 두 메서드 함수 객체가 새로 만들어진다. 메서드는 인스턴스 간에 공유되지 않는다.

class private 필드는 다르다.

```javascript
class Counter {
  #count = 0;
  increment() { return ++this.#count; }
  get() { return this.#count; }
}
```

메서드는 prototype에 한 번 정의되어 모든 인스턴스가 공유한다. `#count`는 인스턴스 자체의 숨겨진 슬롯이다. V8은 private 필드를 일반 프로퍼티처럼 인스턴스에 저장하되, ScopeInfo 수준에서 외부 접근을 차단한다.

### 성능

10만 개의 인스턴스를 만들 때 클로저 패턴은 10만 개의 Context와 20만 개의 메서드 함수 객체를 만든다. class는 10만 개의 인스턴스 슬롯과 prototype에 공유된 2개의 메서드만 만든다. 메모리 차이가 명확하다.

성능 측면에서도 class의 메서드 호출은 prototype lookup이 IC(Inline Cache)에 잘 맞아서 빠르고, 클로저 메서드는 매 인스턴스가 다른 함수 객체이기 때문에 megamorphic 호출이 되기 쉽다. 호출 빈도가 높은 핫패스에서 클로저 패턴은 V8이 인라인하기 어렵다.

그렇다고 항상 class가 옳은 건 아니다. 함수형 합성이 자연스럽고 인스턴스가 소수일 때는 클로저가 더 직관적이다. 라이브러리 만들 때 인스턴스가 수만 개 생성될 가능성이 있다면 class를 우선 고려한다.

## async/await에서 클로저 변수의 수명

### 함수 일시 정지의 의미

async 함수 안의 `await`는 함수를 일시 정지시킨다. 정지된 동안 실행 컨텍스트는 유지되고, 그 컨텍스트의 LexicalEnvironment도 살아있다. 즉 `await` 이전에 선언된 모든 지역 변수와 그 함수가 캡처한 외부 변수가 await 동안 메모리에 머무른다.

```javascript
async function process(jobs) {
  const startTime = Date.now();
  const tempBuffer = new Array(1_000_000);
  
  await fetch('/api/start');  // 네트워크 대기 동안...
  
  // tempBuffer가 여기서도 살아있다
  return tempBuffer.length;
}
```

`fetch`가 5초 걸리면 그 5초 동안 `tempBuffer`는 회수되지 않는다. 동시 요청이 많으면 메모리 사용량이 곱절로 뛴다.

### 사용 종료 후 해제

해결은 단순하다. await 이후로 더 이상 필요 없는 큰 변수는 명시적으로 null을 대입한다.

```javascript
async function process(jobs) {
  let tempBuffer = new Array(1_000_000);
  const result = computeFromBuffer(tempBuffer);
  tempBuffer = null;  // 이제 await 동안 회수 가능
  
  await fetch('/api/start');
  return result;
}
```

V8은 일부 케이스에서 escape analysis로 await 이후 사용되지 않는 변수를 자동으로 dead로 표시한다. 하지만 신뢰할 만큼 일관되지 않으므로, 큰 데이터를 다루는 long-running async 함수에서는 명시적 해제가 안전하다.

### Generator와 비교

`async/await`는 사실 generator + Promise 위에 만들어진 문법 설탕이다. `function*`도 동일한 수명 특성을 가진다. `yield`로 멈춘 generator는 자기 LexicalEnvironment를 통째로 들고 있다가 다음 `next()` 호출 시 재개한다.

이게 lazy iteration에서 메모리 효율적인 방법인데, 거꾸로 generator 인스턴스를 쥐고 다른 일을 오래 하면 그 안의 캡처 변수들이 모두 살아있게 된다. 백엔드에서 generator 기반 스트림 처리를 할 때 종종 잊고 가는 디테일이다.

## 마무리

클로저는 이론적으로 깔끔하지만 V8 구현 디테일과 실제 GC 동작을 모르면 누수를 추적하지 못한다. ScopeInfo와 Context의 존재, 형제 클로저의 Context 공유, async 일시 정지 동안의 변수 보존 같은 사실들은 명세를 읽어서는 잘 보이지 않는 부분이다. Heap snapshot을 한 번 직접 분석해보는 경험이 백 마디 글보다 낫다. 문제가 보이면 Memory 탭을 열고 retainer를 따라가는 습관을 들이면, 클로저는 더 이상 무서운 존재가 아니라 가장 강력한 도구가 된다.
