---
title: JavaScript Stack (스택) 자료구조
tags: [language, javascript]
updated: 2026-09-28
---

# JavaScript Stack (스택) 자료구조

## Call Stack — JS 엔진이 실제로 쓰는 스택

JavaScript 엔진은 함수를 호출할 때마다 호출 프레임을 Call Stack에 쌓는다. 함수가 반환하면 프레임이 제거된다. LIFO 규칙 그대로다.

```javascript
function c() {
    // 이 시점 Call Stack (아래에서 위 순서):
    // anonymous → a → b → c
    console.trace('c 실행 중');
}

function b() {
    c();
}

function a() {
    b();
}

a();
```

`console.trace()` 실제 출력:
```
Trace: c 실행 중
    at c (example.js:3)
    at b (example.js:9)
    at a (example.js:13)
    at <anonymous>:1:1
```

맨 위(첫 줄)가 현재 실행 중인 함수다. `c`가 반환하면 그 프레임이 제거되고 `b`가 실행을 재개한다. `b`가 반환하면 `a`로, `a`가 반환하면 호출 지점으로 돌아간다.

프레임에는 지역 변수, 매개변수, 반환 주소가 들어있다. 함수가 중첩될수록 프레임이 쌓이고, 모두 반환해야 원래 상태로 돌아온다.

`Error.stack`으로 호출 스택을 문자열로 잡을 수 있다.

```javascript
function getStackTrace() {
    return new Error().stack;
}

function inner() {
    console.log(getStackTrace());
}

function outer() {
    inner();
}

outer();
// Error
//     at getStackTrace (example.js:2)
//     at inner (example.js:6)
//     at outer (example.js:11)
//     at <anonymous>:1:1
```

스택은 후입선출(LIFO)로 동작하는 자료구조다. push로 맨 위에 쌓고, pop으로 맨 위를 꺼낸다. JS 엔진의 Call Stack, 브라우저 뒤로가기, 실행 취소(Ctrl+Z), 괄호 검증, DFS 탐색이 모두 이 구조를 쓴다.

## 스택 오버플로우

재귀 함수가 종료 조건 없이 계속 호출되면 Call Stack이 꽉 찬다.

```javascript
function infinite() {
    return infinite();
}
infinite();
// Uncaught RangeError: Maximum call stack size exceeded
```

V8의 콜 스택 한도는 프레임 크기에 따라 달라진다. Node.js 20 기준으로 지역 변수가 없는 단순 함수는 약 14,000~15,000프레임 수준에서 터진다. `--stack-size=<KB>` 플래그로 스택 크기를 늘릴 수 있다.

```javascript
// 실제 한도 측정
let count = 0;
function measure() {
    count++;
    measure();
}
try {
    measure();
} catch (e) {
    console.log(`재귀 한도: ${count}`);
    // Node.js 20 실측: 약 14,165 (환경마다 다름)
}
```

### Chrome DevTools로 확인하는 방법

DevTools를 열고(F12) Sources 패널로 이동한다. 오른쪽 상단 "Pause on exceptions" 아이콘(육각형 멈춤 표시)을 클릭하면 예외가 발생하는 순간 실행이 멈춘다. 스택 오버플로우가 터지면 오른쪽 Call Stack 패널에 같은 함수 이름이 수백~수천 줄 반복되는 게 보인다. DevTools는 프레임을 전부 표시하지 않고 "... N more frames" 형태로 접어둔다.

중간 상태를 확인하고 싶으면 `console.trace()`를 조건부로 찍는다.

```javascript
function countdown(n) {
    if (n % 500 === 0) console.trace(`n=${n}`); // 500마다 스택 출력
    if (n <= 0) return;
    countdown(n - 1);
}
countdown(3000);
```

Performance 패널에서 녹화하면 깊은 재귀가 JS 스레드를 얼마나 잡아먹는지 플레임 차트로 확인할 수 있다. 같은 함수가 수직으로 쌓인 구간이 보이면 재귀 깊이 문제다.

## V8에서 꼬리 재귀 최적화가 동작하지 않는 이유

ES2015 스펙에 TCO(Proper Tail Calls)가 포함됐다. 함수가 반환하기 직전(꼬리 위치)에서 다른 함수를 호출할 때 새 프레임을 쌓는 대신 현재 프레임을 재사용해도 된다는 내용이다. 이론상 꼬리 재귀 함수는 스택 오버플로우가 발생하지 않는다.

```javascript
// 꼬리 재귀 형태
function factorial(n, acc = 1) {
    if (n <= 1) return acc;
    return factorial(n - 1, n * acc); // 꼬리 위치 — TCO 대상
}
```

V8은 2016년 Chrome 54 즈음에 `--harmony-tailcalls` 플래그로 TCO를 실험적으로 지원했다가 제거했다. 현재까지 V8 메인라인에 TCO는 없다. Safari의 JavaScriptCore만 TCO를 구현하고 있다.

V8이 TCO를 제거한 이유는 두 가지다. 첫째, 디버깅이 불가능해진다. 프레임을 제거하면 DevTools Call Stack에서 호출 경로가 사라지고 `Error.stack`도 끊긴다. 어느 함수에서 호출했는지 추적할 수 없게 된다. 둘째, TCO가 적용되는 조건이 까다롭다. `return f()` 형태여야 하고 `return f() + 1`이나 `return 1 + f()` 같은 경우는 해당 안 된다. 이 판정 비용과 실용적 이점을 견준 결과 지원을 중단했다.

Node.js에서 실제로 확인하면 꼬리 재귀 형태라도 스택 오버플로우가 난다.

```javascript
// Node.js 20 (V8 11.x) 기준 실측
function factorial(n, acc = 1) {
    if (n <= 1) return acc;
    return factorial(n - 1, n * acc);
}

try {
    console.log(factorial(100000));
} catch (e) {
    console.log(e.message); // Maximum call stack size exceeded
}
```

V8에서 깊은 재귀가 필요한 경우 트램폴린(trampolining) 패턴을 쓴다.

```javascript
function trampoline(fn) {
    return function(...args) {
        let result = fn(...args);
        while (typeof result === 'function') {
            result = result();
        }
        return result;
    };
}

// 호출 대신 함수를 반환하도록 변환
function factorial(n, acc = 1) {
    if (n <= 1) return acc;
    return () => factorial(n - 1, n * acc);
}

const safeFactorial = trampoline(factorial);
safeFactorial(100000); // 스택 오버플로우 없이 동작 (결과는 Infinity — 정수 오버플로)
```

`trampoline`이 반환값이 함수인 동안 반복 실행하므로 스택 깊이가 항상 1을 유지한다. 재귀를 루프로 바꾼 것과 같다.

## push·pop·peek 핵심 연산

### 기본 스택 구현

#### 배열을 이용한 스택 구현
```javascript
class Stack {
    constructor() {
        this.items = [];
    }

    push(element) {
        this.items.push(element);
    }

    pop() {
        if (this.isEmpty()) {
            return undefined;
        }
        return this.items.pop();
    }

    peek() {
        if (this.isEmpty()) {
            return undefined;
        }
        return this.items[this.items.length - 1];
    }

    isEmpty() {
        return this.items.length === 0;
    }

    size() {
        return this.items.length;
    }

    clear() {
        this.items = [];
    }

    printStack() {
        console.log(this.items.toString());
    }
}
```

#### 기본 사용법
```javascript
const stack = new Stack();

stack.push(10);  // [10]
stack.push(20);  // [10, 20]
stack.push(30);  // [10, 20, 30]

stack.printStack(); // "10,20,30"

console.log(stack.size()); // 3
console.log(stack.peek()); // 30

console.log(stack.pop()); // 30
console.log(stack.pop()); // 20
console.log(stack.pop()); // 10

console.log(stack.isEmpty()); // true
```

## 실전 예제

### 괄호 검증
```javascript
class BracketValidator {
    static isValid(expression) {
        const stack = new Stack();
        const brackets = {
            '(': ')',
            '{': '}',
            '[': ']'
        };

        for (const char of expression) {
            if (brackets[char]) {
                stack.push(char);
            } else if (Object.values(brackets).includes(char)) {
                if (stack.isEmpty() || brackets[stack.pop()] !== char) {
                    return false;
                }
            }
        }

        return stack.isEmpty();
    }
}

console.log(BracketValidator.isValid('()'));     // true
console.log(BracketValidator.isValid('({[]})')); // true
console.log(BracketValidator.isValid('({[}])')); // false
console.log(BracketValidator.isValid('((('));    // false
```

### 실행 취소
```javascript
class UndoManager {
    constructor() {
        this.undoStack = new Stack();
        this.redoStack = new Stack();
    }

    execute(action) {
        this.undoStack.push(action);
        this.redoStack.clear();
        action.execute();
    }

    undo() {
        if (this.undoStack.isEmpty()) {
            return false;
        }

        const action = this.undoStack.pop();
        action.undo();
        this.redoStack.push(action);
        return true;
    }

    redo() {
        if (this.redoStack.isEmpty()) {
            return false;
        }

        const action = this.redoStack.pop();
        action.execute();
        this.undoStack.push(action);
        return true;
    }

    canUndo() {
        return !this.undoStack.isEmpty();
    }

    canRedo() {
        return !this.redoStack.isEmpty();
    }
}

class TextAction {
    constructor(text, oldValue, newValue) {
        this.text = text;
        this.oldValue = oldValue;
        this.newValue = newValue;
    }

    execute() {
        this.text.value = this.newValue;
    }

    undo() {
        this.text.value = this.oldValue;
    }
}
```

### 브라우저 히스토리 관리
```javascript
class BrowserHistory {
    constructor() {
        this.backStack = new Stack();
        this.forwardStack = new Stack();
        this.currentPage = null;
    }

    visit(page) {
        if (this.currentPage) {
            this.backStack.push(this.currentPage);
        }
        this.currentPage = page;
        this.forwardStack.clear();
        console.log(`방문: ${page}`);
    }

    back() {
        if (this.backStack.isEmpty()) {
            console.log('뒤로 갈 페이지가 없습니다.');
            return;
        }

        this.forwardStack.push(this.currentPage);
        this.currentPage = this.backStack.pop();
        console.log(`뒤로 가기: ${this.currentPage}`);
    }

    forward() {
        if (this.forwardStack.isEmpty()) {
            console.log('앞으로 갈 페이지가 없습니다.');
            return;
        }

        this.backStack.push(this.currentPage);
        this.currentPage = this.forwardStack.pop();
        console.log(`앞으로 가기: ${this.currentPage}`);
    }
}

const browser = new BrowserHistory();
browser.visit('google.com');
browser.visit('github.com');
browser.visit('stackoverflow.com');

browser.back();    // 뒤로 가기: github.com
browser.back();    // 뒤로 가기: google.com
browser.forward(); // 앞으로 가기: github.com
```

### 깊이 우선 탐색 (DFS)
```javascript
class Graph {
    constructor() {
        this.adjacencyList = new Map();
    }

    addVertex(vertex) {
        if (!this.adjacencyList.has(vertex)) {
            this.adjacencyList.set(vertex, []);
        }
    }

    addEdge(vertex1, vertex2) {
        this.adjacencyList.get(vertex1).push(vertex2);
        this.adjacencyList.get(vertex2).push(vertex1);
    }

    dfs(startVertex) {
        const visited = new Set();
        const result = [];
        const stack = new Stack();

        stack.push(startVertex);

        while (!stack.isEmpty()) {
            const currentVertex = stack.pop();

            if (!visited.has(currentVertex)) {
                visited.add(currentVertex);
                result.push(currentVertex);

                const neighbors = this.adjacencyList.get(currentVertex);
                for (let i = neighbors.length - 1; i >= 0; i--) {
                    if (!visited.has(neighbors[i])) {
                        stack.push(neighbors[i]);
                    }
                }
            }
        }

        return result;
    }
}

const graph = new Graph();
graph.addVertex('A');
graph.addVertex('B');
graph.addVertex('C');
graph.addVertex('D');
graph.addEdge('A', 'B');
graph.addEdge('A', 'C');
graph.addEdge('B', 'D');
graph.addEdge('C', 'D');

console.log(graph.dfs('A')); // ['A', 'B', 'D', 'C']
```

이웃을 역순으로 스택에 넣기 때문이다. `A`의 이웃 `['B', 'C']`를 뒤에서부터 넣으면 스택은 `[C, B]`가 되고, `pop`은 맨 위인 `B`를 먼저 꺼낸다. 재귀 DFS와 같은 방문 순서를 맞추려고 뒤집은 것이라, 인접 리스트 순서 그대로 방문한다고 읽으면 어긋난다. `for` 루프를 정순으로 바꾸면 `['A', 'C', 'D', 'B']`가 나온다. 어느 쪽이든 유효한 DFS지만 **결과가 다르므로**, 이 순서에 의존하는 테스트를 짜기 전에 실제 출력을 확인해야 한다.

`addEdge`는 정점이 없으면 던진다.

```javascript
graph.addEdge('A', 'Z');
// TypeError: Cannot read properties of undefined (reading 'push')
```

`addVertex`를 먼저 부르지 않으면 `adjacencyList.get('Z')`가 `undefined`이고 거기에 `push`를 부른다. 에지 목록을 파일이나 API에서 읽어 넣는 코드라면 정점이 빠지는 일이 흔하다. `addEdge` 안에서 `addVertex`를 먼저 호출하게 하는 편이 안전하다.

### 계산기 구현 (후위 표기법)
```javascript
class PostfixCalculator {
    static evaluate(expression) {
        const stack = new Stack();
        const tokens = expression.split(' ');

        for (const token of tokens) {
            if (this.isNumber(token)) {
                stack.push(parseFloat(token));
            } else if (this.isOperator(token)) {
                const b = stack.pop();
                const a = stack.pop();
                const result = this.performOperation(a, b, token);
                stack.push(result);
            }
        }

        return stack.pop();
    }

    static isNumber(token) {
        return !isNaN(token) && token !== '';
    }

    static isOperator(token) {
        return ['+', '-', '*', '/'].includes(token);
    }

    static performOperation(a, b, operator) {
        switch (operator) {
            case '+': return a + b;
            case '-': return a - b;
            case '*': return a * b;
            case '/': return a / b;
            default: throw new Error(`Unknown operator: ${operator}`);
        }
    }
}

console.log(PostfixCalculator.evaluate('5 3 +'));       // 8
console.log(PostfixCalculator.evaluate('10 5 2 * -'));  // 0
console.log(PostfixCalculator.evaluate('3 4 5 * +'));   // 23
```

`isNumber`가 숫자를 제대로 걸러내지 못한다. `isNaN`은 인자를 먼저 숫자로 **변환**하고 나서 판정하기 때문에, 숫자로 변환되는 것은 전부 통과한다.

```javascript
const isNumber = t => !isNaN(t) && t !== '';

isNumber(' ');        // true   ← 공백은 0으로 변환된다
isNumber(null);       // true   ← null도 0이다
isNumber('0x10');     // true
isNumber('Infinity'); // true
```

그 다음 줄의 `parseFloat`는 변환 규칙이 또 달라서 값이 어긋난다.

```javascript
parseFloat(' ');    // NaN   ← isNumber는 통과시켰는데 파싱은 실패
parseFloat('0x10'); // 0     ← 16이 아니다
```

`'0x10'`이 스택에 `0`으로 들어가면 계산 결과만 틀리고 에러는 없다. 입력 검증과 실제 파싱이 **서로 다른 함수**를 쓰면 이런 틈이 생긴다. 판정과 변환을 한 번에 하는 편이 안전하다.

```javascript
const n = Number(token);
if (Number.isFinite(n)) stack.push(n);
```

피연산자가 모자라면 `pop()`이 `undefined`를 돌려주고 그대로 계산에 들어간다.

```javascript
PostfixCalculator.evaluate('5 +'); // NaN — undefined + 5
```

`NaN`은 이후 모든 연산을 오염시키며 끝까지 흘러간다. 잘못된 수식이 에러 대신 `NaN`으로 반환되면 호출부는 계산이 성공했다고 믿는다. 스택 크기를 먼저 확인하고 부족하면 던져야 한다.

### SafeStack 분석

```javascript
class SafeStack extends Stack {
    pop() {
        try {
            return super.pop();
        } catch (error) {
            console.warn('스택이 비어있습니다.');
            return null;
        }
    }
}
```

이 `try/catch`는 한 번도 실행되지 않는다. **`SafeStack`이 상속한 `Stack`은 던지지 않기 때문이다.**

```javascript
const s = new SafeStack();
s.pop(); // undefined — 경고도 안 찍히고 null도 아니다
```

맨 위의 `Stack`은 비어 있을 때 `undefined`를 **반환**한다. 잡을 예외 자체가 없다.

이런 종류의 코드가 특히 나쁜 이유는 **아무 증상이 없다**는 것이다. 에러도 없고 경고도 없고, 약속한 `null` 대신 `undefined`가 나온다. 호출부가 `if (v === null)`로 검사하면 빈 스택을 못 알아챈다. `try/catch`로 감싸 놓고 "이제 안전하다"고 믿기 전에 **잡으려는 예외가 실제로 던져지는지** 확인해야 한다.

## 스택 vs 다른 자료구조

| 자료구조 | 접근 방식 | 삽입/삭제 | 용도 |
|----------|-----------|-----------|------|
| **스택** | LIFO | O(1) | 함수 호출, 실행 취소 |
| **큐** | FIFO | O(1) | 작업 대기열, BFS |
| **배열** | 인덱스 | O(n) | 일반적인 데이터 저장 |
| **링크드 리스트** | 순차 | O(1) | 동적 데이터 구조 |
