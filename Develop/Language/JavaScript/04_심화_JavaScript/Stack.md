---
title: JavaScript Stack (스택) 자료구조
tags: [language, javascript, 04심화javascript, stack, data-structure]
updated: 2025-08-10
---

# JavaScript Stack (스택) 자료구조

## 배경

스택은 **후입선출(LIFO, Last In First Out)** 방식으로 데이터를 관리하는 자료구조입니다. 마지막에 들어온 데이터가 가장 먼저 나가는 방식으로, 일상생활에서 접시 쌓기, 책 쌓기, 프링글스 통과 같은 예시로 이해할 수 있습니다.

### 스택의 필요성
- **함수 호출 관리**: 함수의 실행 컨텍스트와 반환 주소 저장
- **브라우저 히스토리**: 뒤로 가기/앞으로 가기 기능 구현
- **실행 취소**: Ctrl+Z 같은 실행 취소 기능
- **괄호 검증**: 수식의 괄호 짝 맞추기 검증
- **깊이 우선 탐색**: 그래프나 트리의 깊이 우선 탐색

### 기본 개념
- **LIFO**: Last In First Out (후입선출)
- **push**: 데이터를 스택의 맨 위에 추가
- **pop**: 스택의 맨 위 데이터를 제거하고 반환
- **peek**: 스택의 맨 위 데이터를 확인 (제거하지 않음)
- **isEmpty**: 스택이 비어있는지 확인
- **size**: 스택에 저장된 데이터 개수 확인

## 핵심

### 1. 기본 스택 구현

#### 배열을 이용한 스택 구현
```javascript
class Stack {
    constructor() {
        this.items = []; // 스택을 저장할 배열
    }

    // 스택에 요소 추가 (맨 위에 쌓기)
    push(element) {
        this.items.push(element);
    }

    // 스택에서 요소 제거 (맨 위에서 꺼내기)
    pop() {
        if (this.isEmpty()) {
            return undefined; // 스택이 비어있으면 undefined 반환
        }
        return this.items.pop();
    }

    // 스택의 가장 위에 있는 요소 확인 (제거하지 않음)
    peek() {
        if (this.isEmpty()) {
            return undefined;
        }
        return this.items[this.items.length - 1];
    }

    // 스택이 비어 있는지 확인
    isEmpty() {
        return this.items.length === 0;
    }

    // 스택의 크기 확인
    size() {
        return this.items.length;
    }

    // 스택 비우기
    clear() {
        this.items = [];
    }

    // 스택 내용 출력
    printStack() {
        console.log(this.items.toString());
    }
}
```

#### 기본 사용법
```javascript
// 스택 생성
const stack = new Stack();

// 스택에 요소 추가 (아래에서 위로 쌓임)
stack.push(10);  // [10]
stack.push(20);  // [10, 20]
stack.push(30);  // [10, 20, 30]

// 스택 상태 출력
stack.printStack(); // "10,20,30"

// 스택의 크기 확인
console.log(stack.size()); // 3

// 스택의 가장 위에 있는 요소 확인 (제거하지 않음)
console.log(stack.peek()); // 30

// 스택에서 요소 제거
console.log(stack.pop()); // 30
console.log(stack.pop()); // 20
console.log(stack.pop()); // 10

// 스택이 비어있는지 확인
console.log(stack.isEmpty()); // true
```

### 2. 고급 스택 구현

#### 제네릭 스택 클래스
```javascript
class GenericStack {
    constructor() {
        this.items = [];
    }

    push(element) {
        this.items.push(element);
        return this; // 메서드 체이닝을 위해 this 반환
    }

    pop() {
        if (this.isEmpty()) {
            throw new Error('Stack is empty');
        }
        return this.items.pop();
    }

    peek() {
        if (this.isEmpty()) {
            throw new Error('Stack is empty');
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
        return this;
    }

    // 스택의 모든 요소를 배열로 반환
    toArray() {
        return [...this.items];
    }

    // 스택의 요소들을 문자열로 변환
    toString() {
        return this.items.toString();
    }

    // 스택 복사
    clone() {
        const newStack = new GenericStack();
        newStack.items = [...this.items];
        return newStack;
    }
}
```

#### 스택 이터레이터 구현
```javascript
class IterableStack extends GenericStack {
    [Symbol.iterator]() {
        let index = this.items.length - 1;
        return {
            next: () => {
                if (index >= 0) {
                    return {
                        value: this.items[index--],
                        done: false
                    };
                } else {
                    return { done: true };
                }
            }
        };
    }

    // 스택의 모든 요소를 순회 (위에서부터)
    forEach(callback) {
        for (let i = this.items.length - 1; i >= 0; i--) {
            callback(this.items[i], this.items.length - 1 - i);
        }
    }

    // 스택에서 조건에 맞는 요소 찾기
    find(predicate) {
        for (let i = this.items.length - 1; i >= 0; i--) {
            if (predicate(this.items[i])) {
                return this.items[i];
            }
        }
        return undefined;
    }
}

// 사용 예시
const iterableStack = new IterableStack();
iterableStack.push(1).push(2).push(3);

// 이터레이터 사용
for (const item of iterableStack) {
    console.log(item); // 3, 2, 1 (위에서부터)
}

// forEach 사용
iterableStack.forEach((item, index) => {
    console.log(`Index ${index}: ${item}`);
});
```

### 3. 스택 활용 사례

#### 괄호 검증
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
                // 여는 괄호는 스택에 push
                stack.push(char);
            } else if (Object.values(brackets).includes(char)) {
                // 닫는 괄호는 스택의 top과 매칭 확인
                if (stack.isEmpty() || brackets[stack.pop()] !== char) {
                    return false;
                }
            }
        }

        return stack.isEmpty();
    }
}

// 사용 예시
console.log(BracketValidator.isValid('()')); // true
console.log(BracketValidator.isValid('({[]})')); // true
console.log(BracketValidator.isValid('({[}])')); // false
console.log(BracketValidator.isValid('(((')); // false
```

#### 실행 취소 기능
```javascript
class UndoManager {
    constructor() {
        this.undoStack = new Stack();
        this.redoStack = new Stack();
    }

    // 액션 실행
    execute(action) {
        this.undoStack.push(action);
        this.redoStack.clear(); // 새로운 액션 실행 시 redo 스택 초기화
        action.execute();
    }

    // 실행 취소
    undo() {
        if (this.undoStack.isEmpty()) {
            return false;
        }

        const action = this.undoStack.pop();
        action.undo();
        this.redoStack.push(action);
        return true;
    }

    // 다시 실행
    redo() {
        if (this.redoStack.isEmpty()) {
            return false;
        }

        const action = this.redoStack.pop();
        action.execute();
        this.undoStack.push(action);
        return true;
    }

    // 실행 취소 가능 여부
    canUndo() {
        return !this.undoStack.isEmpty();
    }

    // 다시 실행 가능 여부
    canRedo() {
        return !this.redoStack.isEmpty();
    }
}

// 액션 클래스 예시
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

#### 깊이 우선 탐색 (DFS)
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

    // 스택을 이용한 깊이 우선 탐색
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

                // 인접한 정점들을 스택에 추가
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

// 사용 예시
const graph = new Graph();
graph.addVertex('A');
graph.addVertex('B');
graph.addVertex('C');
graph.addVertex('D');
graph.addEdge('A', 'B');
graph.addEdge('A', 'C');
graph.addEdge('B', 'D');
graph.addEdge('C', 'D');

console.log(graph.dfs('A')); // ['A', 'C', 'D', 'B']
```

## 예시

### 1. 실제 사용 사례

#### 브라우저 히스토리 관리
```javascript
class BrowserHistory {
    constructor() {
        this.backStack = new Stack();
        this.forwardStack = new Stack();
        this.currentPage = null;
    }

    // 페이지 방문
    visit(page) {
        if (this.currentPage) {
            this.backStack.push(this.currentPage);
        }
        this.currentPage = page;
        this.forwardStack.clear(); // 새로운 페이지 방문 시 forward 스택 초기화
        console.log(`방문: ${page}`);
    }

    // 뒤로 가기
    back() {
        if (this.backStack.isEmpty()) {
            console.log('뒤로 갈 페이지가 없습니다.');
            return;
        }

        this.forwardStack.push(this.currentPage);
        this.currentPage = this.backStack.pop();
        console.log(`뒤로 가기: ${this.currentPage}`);
    }

    // 앞으로 가기
    forward() {
        if (this.forwardStack.isEmpty()) {
            console.log('앞으로 갈 페이지가 없습니다.');
            return;
        }

        this.backStack.push(this.currentPage);
        this.currentPage = this.forwardStack.pop();
        console.log(`앞으로 가기: ${this.currentPage}`);
    }

    // 현재 페이지
    getCurrentPage() {
        return this.currentPage;
    }
}

// 사용 예시
const browser = new BrowserHistory();
browser.visit('google.com');
browser.visit('github.com');
browser.visit('stackoverflow.com');

browser.back(); // 뒤로 가기: github.com
browser.back(); // 뒤로 가기: google.com
browser.forward(); // 앞으로 가기: github.com
```

#### 계산기 구현 (후위 표기법)
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

// 사용 예시
console.log(PostfixCalculator.evaluate('5 3 +')); // 8
console.log(PostfixCalculator.evaluate('10 5 2 * -')); // 0
console.log(PostfixCalculator.evaluate('3 4 5 * +')); // 23
```

### 2. 고급 패턴

#### 스택 기반 메모리 관리
```javascript
class MemoryManager {
    constructor() {
        this.memoryStack = new Stack();
        this.freeList = new Stack();
    }

    // 메모리 할당
    allocate(size) {
        if (!this.freeList.isEmpty()) {
            const freeBlock = this.freeList.pop();
            if (freeBlock.size >= size) {
                return freeBlock;
            }
        }

        const newBlock = { id: Date.now(), size, data: null };
        this.memoryStack.push(newBlock);
        return newBlock;
    }

    // 메모리 해제
    deallocate(blockId) {
        const tempStack = new Stack();
        let found = false;

        while (!this.memoryStack.isEmpty()) {
            const block = this.memoryStack.pop();
            if (block.id === blockId) {
                this.freeList.push(block);
                found = true;
                break;
            }
            tempStack.push(block);
        }

        // 스택 복원
        while (!tempStack.isEmpty()) {
            this.memoryStack.push(tempStack.pop());
        }

        return found;
    }

    // 메모리 상태 출력
    getMemoryStatus() {
        return {
            allocated: this.memoryStack.size(),
            free: this.freeList.size(),
            totalBlocks: this.memoryStack.size() + this.freeList.size()
        };
    }
}
```

## 운영 팁

### 성능 최적화

#### 메모리 효율성
```javascript
// 스택 크기 제한
class LimitedStack {
    constructor(maxSize = 1000) {
        this.items = [];
        this.maxSize = maxSize;
    }

    push(element) {
        if (this.items.length >= this.maxSize) {
            this.items.shift(); // 가장 오래된 요소 제거
        }
        this.items.push(element);
    }

    // 기타 메서드들...
}

// 스택 풀링 (객체 재사용)
class StackPool {
    constructor() {
        this.pool = [];
    }

    getStack() {
        return this.pool.pop() || new Stack();
    }

    returnStack(stack) {
        stack.clear();
        this.pool.push(stack);
    }
}
```

### 에러 처리

#### 안전한 스택 조작
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

    peek() {
        try {
            return super.peek();
        } catch (error) {
            console.warn('스택이 비어있습니다.');
            return null;
        }
    }

    // 스택 오버플로우 방지
    push(element) {
        if (this.size() >= 10000) {
            console.warn('스택 크기가 너무 큽니다.');
            return false;
        }
        super.push(element);
        return true;
    }
}
```

## 참고

### 스택 vs 다른 자료구조

| 자료구조 | 접근 방식 | 삽입/삭제 | 용도 |
|----------|-----------|-----------|------|
| **스택** | LIFO | O(1) | 함수 호출, 실행 취소 |
| **큐** | FIFO | O(1) | 작업 대기열, BFS |
| **배열** | 인덱스 | O(n) | 일반적인 데이터 저장 |
| **링크드 리스트** | 순차 | O(1) | 동적 데이터 구조 |

### 스택 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **함수 호출 관리** | 스택 사용 | 자연스러운 LIFO 구조 |
| **실행 취소 기능** | 스택 사용 | 액션 히스토리 관리 |
| **괄호 검증** | 스택 사용 | 짝 맞추기 로직 |
| **깊이 우선 탐색** | 스택 사용 | 재귀 대체 |
| **대용량 데이터** | 크기 제한 고려 | 메모리 효율성 |

### 결론
스택은 후입선출(LIFO) 방식의 효율적인 자료구조입니다.
함수 호출 관리와 실행 취소 기능에 자연스럽게 적용됩니다.
괄호 검증과 깊이 우선 탐색에서 매우 유용합니다.
메모리 효율성을 고려하여 적절한 크기 제한을 설정하세요.
스택을 활용하여 복잡한 알고리즘을 간단하게 구현할 수 있습니다.






