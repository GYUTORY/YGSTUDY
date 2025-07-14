# 📚 Stack (스택)

## 🎯 개요
스택은 **후입선출(LIFO, Last In First Out)** 방식으로 데이터를 관리하는 자료구조입니다.

### 💡 LIFO란?
- **Last In First Out**: 마지막에 들어온 데이터가 가장 먼저 나가는 방식
- 일상생활의 예시: 접시 쌓기, 책 쌓기, 프링글스 통

### 🔧 스택의 주요 연산
- **push**: 데이터를 스택의 맨 위에 추가
- **pop**: 스택의 맨 위 데이터를 제거하고 반환
- **peek**: 스택의 맨 위 데이터를 확인 (제거하지 않음)
- **isEmpty**: 스택이 비어있는지 확인
- **size**: 스택에 저장된 데이터 개수 확인

---

## 🛠️ 스택 클래스 구현

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

---

## 🎮 기본 사용 예시

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

// 스택에서 요소 제거 (맨 위에서부터)
console.log(stack.pop()); // 30이 제거되고 반환됨

// 스택 상태 출력
stack.printStack(); // "10,20"

// 스택 비우기
stack.clear();
console.log(stack.isEmpty()); // true
```

---

## 🔍 실전 예시: 괄호 유효성 검사

### 문제 설명
수학식이나 프로그래밍 코드에서 괄호가 올바르게 짝을 이루고 있는지 확인하는 문제입니다.

### 해결 방법
- 여는 괄호 `(`, `{`, `[`를 만나면 스택에 push
- 닫는 괄호 `)`, `}`, `]`를 만나면 스택에서 pop하여 짝이 맞는지 확인

```javascript
function isBalanced(expression) {
  const stack = new Stack();
  
  // 여는 괄호들
  const openBrackets = "({[";
  
  // 닫는 괄호들
  const closeBrackets = ")}]";
  
  // 괄호 짝 매칭 정보
  const matchingBrackets = {
    ')': '(',
    '}': '{',
    ']': '['
  };

  // 문자열의 각 문자를 순회
  for (let char of expression) {
    // 여는 괄호인 경우 스택에 추가
    if (openBrackets.includes(char)) {
      stack.push(char);
    } 
    // 닫는 괄호인 경우
    else if (closeBrackets.includes(char)) {
      // 스택이 비어있거나 짝이 맞지 않으면 false
      if (stack.isEmpty() || stack.pop() !== matchingBrackets[char]) {
        return false;
      }
    }
  }

  // 모든 괄호가 짝을 이루었는지 확인
  return stack.isEmpty();
}

// 테스트
console.log(isBalanced("{[()]}")); // true - 올바른 괄호
console.log(isBalanced("{[(])}")); // false - 잘못된 괄호
console.log(isBalanced("((()))")); // true - 중첩된 괄호
console.log(isBalanced("[({})]")); // true - 복잡한 괄호
console.log(isBalanced("{[}"));    // false - 짝이 맞지 않음
```

### 동작 과정 설명
1. `{[()]}` 입력 시:
   - `{` → 스택에 push: `[{]`
   - `[` → 스택에 push: `[{, []`
   - `(` → 스택에 push: `[{, [, (]`
   - `)` → 스택에서 pop: `(`와 매칭 → `[{, []`
   - `]` → 스택에서 pop: `[`와 매칭 → `[{]`
   - `}` → 스택에서 pop: `{`와 매칭 → `[]`
   - 스택이 비어있음 → `true` 반환

---

## 🧮 고급 예시: 중위 표기법을 후위 표기법으로 변환

### 표기법 설명
- **중위 표기법**: `a + b * c` (일반적인 수학 표기법)
- **후위 표기법**: `abc*+` (연산자가 피연산자 뒤에 오는 표기법)

### 변환 규칙
1. 피연산자는 바로 출력
2. 여는 괄호 `(`는 스택에 push
3. 닫는 괄호 `)`를 만나면 `(`를 만날 때까지 pop하여 출력
4. 연산자는 우선순위에 따라 처리

```javascript
function infixToPostfix(expression) {
  const stack = new Stack();
  
  // 연산자 우선순위 정의
  const precedence = {
    '+': 1,
    '-': 1,
    '*': 2,
    '/': 2,
    '^': 3
  };
  
  let postfix = '';

  for (let char of expression) {
    // 피연산자인 경우 (알파벳이나 숫자)
    if (char.match(/[a-z0-9]/i)) {
      postfix += char;
    } 
    // 여는 괄호인 경우
    else if (char === '(') {
      stack.push(char);
    } 
    // 닫는 괄호인 경우
    else if (char === ')') {
      // 여는 괄호를 만날 때까지 스택에서 pop하여 출력
      while (!stack.isEmpty() && stack.peek() !== '(') {
        postfix += stack.pop();
      }
      stack.pop(); // 여는 괄호 '(' 제거
    } 
    // 연산자인 경우
    else {
      // 현재 연산자보다 우선순위가 높거나 같은 연산자들을 출력
      while (!stack.isEmpty() && precedence[char] <= precedence[stack.peek()]) {
        postfix += stack.pop();
      }
      stack.push(char);
    }
  }

  // 스택에 남은 연산자들을 모두 출력
  while (!stack.isEmpty()) {
    postfix += stack.pop();
  }

  return postfix;
}

// 테스트
console.log(infixToPostfix("a+b*c"));        // "abc*+"
console.log(infixToPostfix("(a+b)*c"));      // "ab+c*"
console.log(infixToPostfix("a+b*(c^d-e)"));  // "abcd^e-*+"
```

### 변환 과정 설명
`a+b*c` → `abc*+` 변환 과정:
1. `a` → 피연산자 → 출력: `"a"`
2. `+` → 연산자 → 스택에 push: `[+]`
3. `b` → 피연산자 → 출력: `"ab"`
4. `*` → 연산자 → `+`보다 우선순위 높음 → 스택에 push: `[+, *]`
5. `c` → 피연산자 → 출력: `"abc"`
6. 끝 → 스택에서 pop: `*` → 출력: `"abc*"`
7. 스택에서 pop: `+` → 출력: `"abc*+"`

---

## 💡 스택의 활용 분야

### 1. **함수 호출 관리**
- 함수가 호출될 때마다 호출 정보가 스택에 쌓임
- 함수가 종료되면 스택에서 제거됨

### 2. **브라우저 뒤로가기/앞으로가기**
- 방문한 페이지들을 스택에 저장
- 뒤로가기 시 스택에서 pop

### 3. **실행 취소(Undo) 기능**
- 사용자의 작업을 스택에 저장
- 실행 취소 시 스택에서 pop

### 4. **괄호 검사**
- 프로그래밍 언어의 구문 분석
- 수학식의 괄호 유효성 검사

### 5. **후위 표기법 변환**
- 컴파일러에서 수식 처리
- 계산기 구현

