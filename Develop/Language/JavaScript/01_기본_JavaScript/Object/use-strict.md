---
title: JavaScript Strict Mode (엄격 모드)
tags: [language, javascript, 01기본javascript, object, use-strict, strict-mode]
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

