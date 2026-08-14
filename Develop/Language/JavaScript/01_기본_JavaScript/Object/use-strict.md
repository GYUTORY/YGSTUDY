---
title: JavaScript Strict Mode (엄격 모드)
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript Strict Mode (엄격 모드)

## 배경

JavaScript의 Strict Mode(엄격 모드)는 더 엄격한 문법 규칙을 적용하여 오류를 방지하고 코드의 안정성을 높이는 모드입니다. 기본적으로 JavaScript는 유연한 문법을 허용하지만, 엄격 모드를 사용하면 실수로 인한 오류를 사전에 방지할 수 있습니다.

### Strict Mode의 필요성
- **오류 방지**: 실수로 인한 잠재적 오류 사전 감지
- **안전성 향상**: 의도치 않은 전역 객체 수정 방지
- **성능 최적화**: 일부 최적화 기회 제공
- **코드 품질**: 더 엄격하고 명확한 코드 작성

### 기본 개념
- **엄격 모드**: `"use strict"` 지시어로 활성화되는 JavaScript 모드
- **암시적 선언**: 변수 선언 없이 사용하는 것 금지
- **this 바인딩**: 함수 내부에서 this의 동작 변화
- **읽기 전용 속성**: 수정 불가능한 속성의 보호

## 핵심

### 1. Strict Mode 활성화 방법

#### 전체 스크립트에 적용
```javascript
"use strict";  // 스크립트 전체에 엄격 모드 적용

function test() {
    x = 10; // ReferenceError: x is not defined
    console.log(x);
}

test();
```

#### 특정 함수에만 적용
```javascript
function strictFunction() {
    "use strict";
    let a = 5;
    b = 10; // ReferenceError: b is not defined
    console.log(a + b);
}

function normalFunction() {
    b = 10; // 정상 동작 (전역 변수로 선언됨)
    console.log(b);
}

strictFunction(); // 오류 발생
normalFunction(); // 정상 동작
```

#### 모듈에서의 자동 적용
```javascript
// ES6 모듈에서는 자동으로 엄격 모드 적용
export function moduleFunction() {
    x = 10; // ReferenceError: x is not defined
    console.log(x);
}
```

`"use strict"` 는 문자열 리터럴일 뿐이라 **위치를 틀리면 아무 일도 하지 않는다.** 스크립트나 함수 본문의 **첫 문장**이어야 한다.

```javascript
function notFirst() {
  const a = 1;
  "use strict";                       // ← 그냥 문자열. 무시된다
  return (function () { return this; })();
}
notFirst();   // globalThis — 엄격 모드가 아니다

function first() {
  "use strict";
  return (function () { return this; })();
}
first();      // undefined — 엄격 모드다
```

에러도 경고도 없다. 파일을 열어 보면 `"use strict"` 가 분명히 적혀 있으니 켜져 있다고 믿게 된다. 실제로 이 문제가 나는 자리는 대개 이렇다.

- 주석이나 라이선스 헤더 위에 두는 것은 괜찮다(주석은 문장이 아니다). `import` 나 변수 선언 아래로 밀리면 죽는다.
- 여러 파일을 **연결(concat)** 하는 번들 설정에서, 엄격 모드가 아닌 파일이 앞에 붙으면 뒤 파일의 지시어가 통째로 무효가 된다. 반대로 엄격 파일이 앞에 오면 비엄격 파일까지 엄격해진다.

지금 이 지시어를 손으로 쓸 일이 남아 있는지부터 확인하는 편이 낫다. **ES 모듈과 `class` 본문은 언제나 엄격 모드다.**

```javascript
class C { m() { return this; } }
const m = new C().m;
m();          // undefined — "use strict" 를 쓴 적이 없다
```

`import`/`export` 를 쓰는 파일이나 클래스 안에서는 이 지시어가 아무것도 바꾸지 않는다. 남은 대상은 `<script>` 로 직접 넣는 옛 코드와 CommonJS 파일 정도다.

### 2. Strict Mode에서 달라지는 점

#### 암시적 변수 선언 금지
```javascript
"use strict";

// 일반 모드에서는 전역 변수로 선언됨
x = 10; // ReferenceError: x is not defined

// 올바른 방법
let y = 10;
const z = 20;
var w = 30;
```

#### this의 값이 undefined가 됨
```javascript
"use strict";

function showThis() {
    console.log(this); // undefined (일반 모드에서는 window)
}

showThis();

// 메서드에서는 여전히 객체를 참조
const obj = {
    name: 'Object',
    method: function() {
        console.log(this); // { name: 'Object', method: [Function] }
    }
};

obj.method();
```

#### 읽기 전용 속성 수정 불가
```javascript
"use strict";

const obj = Object.freeze({ name: "Alice" });
obj.name = "Bob"; // TypeError: Cannot assign to read only property 'name'

// Object.defineProperty로 읽기 전용 속성 정의
const user = {};
Object.defineProperty(user, 'id', {
    value: 1,
    writable: false
});

user.id = 2; // TypeError: Cannot assign to read only property 'id'
```

#### 중복된 매개변수 금지
```javascript
"use strict";

// 일반 모드에서는 마지막 값이 사용됨
function duplicateParams(a, a, a) {
    console.log(a); // SyntaxError: Duplicate parameter name not allowed in this context
}

duplicateParams(1, 2, 3);
```

#### eval과 arguments 제한
```javascript
"use strict";

// eval에서 변수 선언 금지
eval("var x = 10;"); // x는 eval 스코프에만 존재

// arguments 객체 수정 금지
function testArguments(a, b) {
    arguments[0] = 100; // TypeError: 'caller', 'callee', and 'arguments' properties may not be accessed on strict mode functions
    console.log(a, b);
}

testArguments(1, 2);
```

이 예제의 주석은 실제 동작과 다르다. **엄격 모드에서 `arguments[0] = 100` 은 던지지 않는다.** 대입은 그냥 성공한다. 달라지는 것은 매개변수와의 연동이다.

```javascript
function strictArgs(a, b) {
  "use strict";
  arguments[0] = 100;
  return [a, arguments[0]];      // [1, 100]   ← a 는 그대로
}

function sloppyArgs(a, b) {
  arguments[0] = 100;
  return [a, arguments[0]];      // [100, 100] ← a 까지 바뀐다
}
```

비엄격 모드의 `arguments` 는 매개변수와 **양방향으로 묶여 있다.** `a` 를 바꾸면 `arguments[0]` 이 바뀌고 그 반대도 된다. 엄격 모드는 이 연결을 끊어 스냅샷으로 만든다. 인자를 정규화하려고 `arguments` 를 수정하는 코드가 있으면, 엄격 모드로 바꾸는 순간 조용히 동작이 달라진다 — **에러가 나지 않아서 더 위험하다.**

주석이 인용한 `'caller', 'callee', and 'arguments' properties may not be accessed` 는 다른 상황의 메시지다. 그건 엄격 모드 함수의 `fn.caller` 나 `arguments.callee` 에 **접근**할 때 나온다.

애초에 `arguments` 를 쓸 이유가 거의 없다. 나머지 매개변수(`function f(...args)`)는 진짜 배열이라 `map`·`filter` 가 바로 된다. 화살표 함수는 자기 `arguments` 를 만들지 않는데, 이게 "없다"는 뜻은 아니다 — `this` 처럼 **바깥 함수의 것을 그대로 집어 온다.** 화살표 함수 안에서 `arguments` 를 읽으면 엉뚱한 함수의 인자 목록이 잡히고 에러도 나지 않는다.

### 3. 추가 제한사항

#### 8진수 리터럴 금지
```javascript
"use strict";

const octal = 010; // SyntaxError: Octal literals are not allowed in strict mode

// 올바른 방법
const decimal = 8;
const hex = 0x8;
```

#### with 문 금지
```javascript
"use strict";

const obj = { x: 1, y: 2 };

// 일반 모드에서는 가능
with (obj) {
    console.log(x, y); // SyntaxError: Strict mode code may not include a with statement
}
```

#### 함수 선언 제한
```javascript
"use strict";

// 블록 내부에서 함수 선언 금지
if (true) {
    function blockFunction() {
        console.log('Block function');
    }
    // SyntaxError: In strict mode code, functions can only be declared at top level or inside a block
}

// 올바른 방법
if (true) {
    const blockFunction = function() {
        console.log('Block function expression');
    };
    blockFunction();
}
```

이 예제도 지금 기준으로는 맞지 않는다. **엄격 모드에서 블록 안 함수 선언은 문법 에러가 아니다.**

```javascript
'use strict';
if (true) {
  function f() { return 1; }
  f();        // 1 — 정상 동작한다
}
```

ES5 시절에는 정말 금지였다. ES6 가 블록 스코프 함수 선언을 정식으로 넣으면서 규칙이 바뀌었고, 지금은 `let` 처럼 **그 블록 안에서만 보이는 함수**가 된다.

바뀐 것은 허용 여부가 아니라 스코프다.

```javascript
'use strict';
if (true) { function f() {} }
typeof f;      // 'undefined' — 블록 밖에서는 안 보인다
```

비엄격 모드는 호환성 때문에 이 이름을 바깥 함수 스코프로도 끌어올린다. 그래서 같은 코드가 모드에 따라 **바깥에서 보이기도 하고 안 보이기도 한다.** 문서가 권하는 대로 `const` + 함수 표현식을 쓰면 이 차이 자체가 사라진다 — 이유는 "금지되어서"가 아니라 "모드마다 다르게 동작해서"다.

## 예시

### 1. 실제 사용 사례

#### 안전한 객체 조작
```javascript
"use strict";

// 객체 속성 보호
const config = Object.freeze({
    apiUrl: 'https://api.example.com',
    timeout: 5000
});

// 엄격 모드에서 읽기 전용 속성 수정 시도
try {
    config.apiUrl = 'https://new-api.example.com';
} catch (error) {
    console.error('Config modification failed:', error.message);
    // "Config modification failed: Cannot assign to read only property 'apiUrl'"
}

// 안전한 객체 복사
const safeConfig = { ...config };
safeConfig.apiUrl = 'https://new-api.example.com';
console.log(safeConfig.apiUrl); // 'https://new-api.example.com'
```

#### 함수 내부 안전성
```javascript
"use strict";

class UserManager {
    constructor() {
        this.users = [];
    }
    
    addUser(name, age) {
        // 엄격 모드에서 매개변수 검증
        if (typeof name !== 'string' || typeof age !== 'number') {
            throw new TypeError('Invalid parameters');
        }
        
        // 암시적 변수 선언 방지
        const user = {
            id: this.users.length + 1,
            name: name,
            age: age
        };
        
        this.users.push(user);
        return user;
    }
    
    findUser(id) {
        // this 바인딩 확인
        if (!this.users) {
            throw new Error('Users array not initialized');
        }
        
        return this.users.find(user => user.id === id);
    }
}

const manager = new UserManager();
const user = manager.addUser('Alice', 25);
console.log(user); // { id: 1, name: 'Alice', age: 25 }
```

### 2. 고급 패턴

#### 모듈 패턴에서의 엄격 모드
```javascript
// 즉시 실행 함수 표현식 (IIFE)에서 엄격 모드 사용
const calculator = (function() {
    "use strict";
    
    // private 변수
    let result = 0;
    
    // private 함수
    function validateNumber(num) {
        if (typeof num !== 'number' || isNaN(num)) {
            throw new TypeError('Invalid number');
        }
    }
    
    // public API
    return {
        add: function(num) {
            validateNumber(num);
            result += num;
            return this;
        },
        
        subtract: function(num) {
            validateNumber(num);
            result -= num;
            return this;
        },
        
        multiply: function(num) {
            validateNumber(num);
            result *= num;
            return this;
        },
        
        divide: function(num) {
            validateNumber(num);
            if (num === 0) {
                throw new Error('Division by zero');
            }
            result /= num;
            return this;
        },
        
        getResult: function() {
            return result;
        },
        
        clear: function() {
            result = 0;
            return this;
        }
    };
})();

// 사용 예시
try {
    const calc = calculator
        .add(10)
        .multiply(2)
        .subtract(5);
    
    console.log(calc.getResult()); // 15
} catch (error) {
    console.error('Calculation error:', error.message);
}
```

#### 클래스에서의 엄격 모드
```javascript
"use strict";

class BankAccount {
    constructor(initialBalance) {
        // 엄격 모드에서 속성 초기화 검증
        if (typeof initialBalance !== 'number' || initialBalance < 0) {
            throw new TypeError('Initial balance must be a non-negative number');
        }
        
        this.balance = initialBalance;
        this.transactions = [];
    }
    
    deposit(amount) {
        // 매개변수 검증
        if (typeof amount !== 'number' || amount <= 0) {
            throw new TypeError('Deposit amount must be a positive number');
        }
        
        this.balance += amount;
        this.transactions.push({
            type: 'deposit',
            amount: amount,
            timestamp: new Date()
        });
        
        return this.balance;
    }
    
    withdraw(amount) {
        // 매개변수 검증
        if (typeof amount !== 'number' || amount <= 0) {
            throw new TypeError('Withdrawal amount must be a positive number');
        }
        
        if (amount > this.balance) {
            throw new Error('Insufficient funds');
        }
        
        this.balance -= amount;
        this.transactions.push({
            type: 'withdrawal',
            amount: amount,
            timestamp: new Date()
        });
        
        return this.balance;
    }
    
    getBalance() {
        return this.balance;
    }
    
    getTransactionHistory() {
        return [...this.transactions]; // 불변 복사본 반환
    }
}

// 사용 예시
try {
    const account = new BankAccount(1000);
    account.deposit(500);
    account.withdraw(200);
    
    console.log('Balance:', account.getBalance()); // 1300
    console.log('Transactions:', account.getTransactionHistory());
} catch (error) {
    console.error('Bank operation failed:', error.message);
}
```

## 운영 팁

### 성능 최적화

#### 엄격 모드의 성능 이점
```javascript
"use strict";

// 엄격 모드에서는 일부 최적화가 가능
function optimizedFunction() {
    // 변수 선언이 명확하여 스코프 분석이 쉬움
    let x = 1;
    let y = 2;
    
    // this 바인딩이 명확하여 최적화 가능
    return x + y;
}

// 비엄격 모드에서는 추가 검사 필요
function nonStrictFunction() {
    // 암시적 전역 변수 가능성으로 인한 추가 검사
    x = 1; // 전역 변수로 선언될 수 있음
    return x;
}
```

이 블록의 두 함수는 **같은 파일 첫 줄의 `"use strict"` 아래에 있다.** 이름이 `nonStrictFunction` 이어도 비엄격 모드가 아니다. 엄격 모드는 파일이나 함수 단위로 걸리고, 한 번 켜지면 안쪽 함수가 전부 물려받는다. 함수 이름으로 모드를 끌 방법은 없다. 이 함수를 실제로 호출하면 `x = 1` 에서 `ReferenceError` 가 난다.

"엄격 모드가 최적화 기회를 준다"는 서술도 이 문서에서 잰 적이 없다. 엄격 모드를 켤 이유는 속도가 아니라 **오타가 전역 변수가 되지 않는다**는 한 가지로 충분하다.

```javascript
function calc(count) {
  let total = 0;
  toal = count * 2;      // 오타
  return total;
}
```

비엄격 모드에서 이 코드는 전역에 `toal` 을 만들고 `0` 을 돌려준다. 에러 없이 틀린 값이 나오고, 게다가 전역이 오염돼 다른 파일까지 영향을 준다. 엄격 모드는 이 줄에서 바로 `ReferenceError` 를 던진다. 나머지 규칙들은 이 하나를 위한 덤에 가깝다.

읽기 전용 속성도 같은 성격이다. 비엄격 모드는 대입을 **조용히 무시한다.**

```javascript
const o = Object.freeze({ a: 1 });
o.a = 2;
o.a;        // 1 — 비엄격 모드에서는 에러 없이 그냥 안 바뀐다
```

"분명히 값을 넣었는데 안 들어간다"를 디버깅하는 것보다 그 줄에서 터지는 쪽이 낫다.

### 에러 처리

#### 엄격 모드 오류 해결
```javascript
"use strict";

// 문제: 암시적 변수 선언
function problematicFunction() {
    x = 10; // ReferenceError
}

// 해결: 명시적 변수 선언
function fixedFunction() {
    let x = 10; // 또는 const, var
    console.log(x);
}

// 문제: this 바인딩
function thisProblem() {
    console.log(this); // undefined
}

// 해결: 명시적 바인딩
function thisSolution() {
    console.log(this); // undefined (의도된 동작)
}

// 객체 메서드에서는 정상 동작
const obj = {
    method: function() {
        console.log(this); // obj 객체
    }
};
```

## 참고

### 엄격 모드 vs 일반 모드 비교표

| 구분 | 일반 모드 | 엄격 모드 |
|------|-----------|-----------|
| **암시적 변수 선언** | 허용 (전역 변수) | 금지 (ReferenceError) |
| **this 바인딩** | window/globalThis | undefined |
| **읽기 전용 속성** | 조용히 무시 | TypeError |
| **중복 매개변수** | 마지막 값 사용 | SyntaxError |
| **8진수 리터럴** | 허용 | 금지 |
| **with 문** | 허용 | 금지 |

### 엄격 모드 활성화 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **새 프로젝트** | 항상 사용 | 오류 방지, 안전성 |
| **기존 코드** | 점진적 적용 | 호환성 고려 |
| **라이브러리** | 사용 권장 | 안정성 향상 |
| **레거시 코드** | 신중히 적용 | 기존 동작 변경 가능성 |

### 결론
Strict Mode는 JavaScript 코드의 안전성과 품질을 향상시킵니다.
암시적 변수 선언과 this 바인딩 문제를 사전에 방지하세요.
읽기 전용 속성과 중복 매개변수 오류를 조기에 감지하세요.
새 프로젝트에서는 항상 엄격 모드를 사용하는 것을 권장합니다.
기존 코드에 적용할 때는 점진적으로 적용하여 호환성을 유지하세요.
엄격 모드의 제한사항을 이해하고 적절한 에러 처리를 구현하세요.

