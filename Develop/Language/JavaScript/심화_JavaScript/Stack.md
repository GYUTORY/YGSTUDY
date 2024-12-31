
## Stack
- 스택(Stack)은 데이터를 후입선출(LIFO, Last In First Out) 방식으로 관리하는 자료 구조



### 1.  스택 클래스 구현
```typescript
class Stack<T> {
  private items: T[];

  constructor() {
    this.items = [];
  }

  // 스택에 요소 추가
  push(element: T): void {
    this.items.push(element);
  }

  // 스택에서 요소 제거
  pop(): T | undefined {
    if (this.isEmpty()) {
      return undefined;
    }
    return this.items.pop();
  }

  // 스택의 가장 위에 있는 요소 확인
  peek(): T | undefined {
    if (this.isEmpty()) {
      return undefined;
    }
    return this.items[this.items.length - 1];
  }

  // 스택이 비어 있는지 확인
  isEmpty(): boolean {
    return this.items.length === 0;
  }

  // 스택의 크기 확인
  size(): number {
    return this.items.length;
  }

  // 스택 비우기
  clear(): void {
    this.items = [];
  }

  // 스택 출력
  printStack(): void {
    console.log(this.items.toString());
  }
}

```

---

### 2. 스택 사용 예시
```typescript
const stack = new Stack<number>();

// 스택에 요소 추가
stack.push(10);
stack.push(20);
stack.push(30);

// 스택 상태 출력
stack.printStack(); // 10,20,30

// 스택의 크기 확인
console.log(stack.size()); // 3

// 스택의 가장 위에 있는 요소 확인
console.log(stack.peek()); // 30

// 스택에서 요소 제거
console.log(stack.pop()); // 30

// 스택 상태 출력
stack.printStack(); // 10,20

// 스택 비우기
stack.clear();
console.log(stack.isEmpty()); // true
```

---

### 3. 복잡한 예시: 괄호 유효성 검사

```typescript
function isBalanced(expression: string): boolean {
  const stack = new Stack<string>();
  const openBrackets = "({[";
  const closeBrackets = ")}]";
  const matchingBrackets: { [key: string]: string } = {
    ')': '(',
    '}': '{',
    ']': '['
  };

  for (let char of expression) {
    if (openBrackets.includes(char)) {
      stack.push(char);
    } else if (closeBrackets.includes(char)) {
      if (stack.isEmpty() || stack.pop() !== matchingBrackets[char]) {
        return false;
      }
    }
  }

  return stack.isEmpty();
}

// 예시 테스트
console.log(isBalanced("{[()]}")); // true
console.log(isBalanced("{[(])}")); // false
console.log(isBalanced("((()))")); // true
console.log(isBalanced("[({})]")); // true
console.log(isBalanced("{[}"));    // false
```

---

### 4. . 고급 예시: 스택을 이용한 중위 표기법을 후위 표기법으로 변환

```typescript
function infixToPostfix(expression: string): string {
  const stack = new Stack<string>();
  const precedence: { [key: string]: number } = {
    '+': 1,
    '-': 1,
    '*': 2,
    '/': 2,
    '^': 3
  };
  let postfix = '';

  for (let char of expression) {
    if (char.match(/[a-z0-9]/i)) {
      postfix += char;
    } else if (char === '(') {
      stack.push(char);
    } else if (char === ')') {
      while (!stack.isEmpty() && stack.peek() !== '(') {
        postfix += stack.pop();
      }
      stack.pop(); // Pop the '('
    } else {
      while (!stack.isEmpty() && precedence[char] <= precedence[stack.peek()!]) {
        postfix += stack.pop();
      }
      stack.push(char);
    }
  }

  while (!stack.isEmpty()) {
    postfix += stack.pop();
  }

  return postfix;
}

// 예시 테스트
console.log(infixToPostfix("a+b*c"));        // abc*+
console.log(infixToPostfix("(a+b)*c"));      // ab+c*
console.log(infixToPostfix("a+b*(c^d-e)"));  // abcd^e-*+
console.log(infixToPostfix("a+b*(c^d-e)^(f+g*h)-i")); // abcd^e-fgh*+^*+i-

```