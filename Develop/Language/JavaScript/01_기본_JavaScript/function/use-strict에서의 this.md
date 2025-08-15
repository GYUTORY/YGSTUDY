---
title: JavaScript use strict에서의 this 바인딩
tags: [language, javascript, 01기본javascript, function, use-strict, this-binding]
updated: 2025-08-10
---

# JavaScript use strict에서의 this 바인딩

## 배경

JavaScript의 `"use strict"` 모드는 코드의 안전성을 높이고 잠재적인 오류를 방지하기 위한 엄격한 모드입니다. 이 모드에서는 `this` 키워드의 동작 방식이 일반 모드와 다르게 작동합니다.

### use strict의 필요성
- **안전성 향상**: 잠재적인 오류를 컴파일 타임에 감지
- **this 바인딩**: 함수 내부에서 this의 명확한 동작
- **오류 방지**: 실수로 인한 전역 객체 오염 방지
- **코드 품질**: 더 엄격한 JavaScript 코드 작성

### 기본 개념
- **엄격 모드**: `"use strict"` 지시어로 활성화되는 JavaScript 모드
- **this 바인딩**: 함수 내부에서 this가 참조하는 객체
- **렉시컬 스코프**: 함수가 정의된 위치의 스코프
- **동적 바인딩**: 함수 호출 방식에 따라 달라지는 this 값

## 핵심

### 1. 일반 모드 vs 엄격 모드

#### 일반 모드에서의 this
```javascript
// 일반 모드 (기본 모드)
console.log(this); // window 또는 globalThis

function regularFunction() {
    console.log(this);
}

// 일반 함수 호출
regularFunction(); // window 또는 globalThis

// 메서드 호출
const obj = {
    name: 'Object',
    method: function() {
        console.log(this);
    }
};
obj.method(); // { name: 'Object', method: [Function] }

// 생성자 함수
function Person(name) {
    this.name = name;
    console.log(this);
}
new Person('John'); // Person { name: 'John' }
```

#### 엄격 모드에서의 this
```javascript
"use strict";

console.log(this); // window 또는 globalThis

function strictFunction() {
    console.log(this);
}

// 일반 함수 호출 - this가 undefined
strictFunction(); // undefined

// 메서드 호출 - 엄격 모드에서도 동일
const strictObj = {
    name: 'Strict Object',
    method: function() {
        console.log(this);
    }
};
strictObj.method(); // { name: 'Strict Object', method: [Function] }

// 생성자 함수 - 엄격 모드에서도 동일
function StrictPerson(name) {
    this.name = name;
    console.log(this);
}
new StrictPerson('John'); // StrictPerson { name: 'John' }
```

### 2. 함수 호출 방식별 this 바인딩

#### 일반 함수 호출
```javascript
// 일반 모드
function normalMode() {
    console.log('Normal mode this:', this);
}
normalMode(); // window 또는 globalThis

// 엄격 모드
"use strict";
function strictMode() {
    console.log('Strict mode this:', this);
}
strictMode(); // undefined
```

#### 메서드 호출
```javascript
const user = {
    name: 'Alice',
    greet: function() {
        console.log(`Hello, ${this.name}!`);
    }
};

// 일반 모드와 엄격 모드 모두 동일
user.greet(); // "Hello, Alice!"

// 메서드를 변수에 할당 후 호출
const greetFunction = user.greet;

// 일반 모드
greetFunction(); // "Hello, undefined!" (this가 window)

// 엄격 모드
"use strict";
greetFunction(); // "Hello, undefined!" (this가 undefined)
```

#### 생성자 함수 호출
```javascript
function Person(name) {
    this.name = name;
    console.log('Constructor this:', this);
}

// 일반 모드와 엄격 모드 모두 동일
const person = new Person('Bob'); // Person { name: 'Bob' }
```

### 3. 화살표 함수와 use strict

#### 화살표 함수의 this 바인딩
```javascript
// 화살표 함수는 use strict의 영향을 받지 않음
const arrowFunction = () => {
    console.log('Arrow function this:', this);
};

// 일반 모드
arrowFunction(); // window 또는 globalThis

// 엄격 모드
"use strict";
arrowFunction(); // window 또는 globalThis (동일)

// 클래스 내부의 화살표 함수
class Example {
    constructor() {
        this.name = 'Example';
    }
    
    regularMethod() {
        console.log('Regular method this:', this);
    }
    
    arrowMethod = () => {
        console.log('Arrow method this:', this);
    }
}

const example = new Example();

// 일반 모드와 엄격 모드 모두 동일
example.regularMethod(); // Example { name: 'Example', arrowMethod: [Function] }
example.arrowMethod(); // Example { name: 'Example', arrowMethod: [Function] }
```

## 예시

### 1. 실제 사용 사례

#### 이벤트 핸들러에서의 차이
```javascript
// DOM 요소 선택
const button = document.getElementById('myButton');

// 일반 함수 이벤트 핸들러
function handleClick() {
    console.log('Button clicked!');
    console.log('this in handler:', this);
}

// 일반 모드
button.addEventListener('click', handleClick);
// 클릭 시: this는 button 요소

// 엄격 모드
"use strict";
button.addEventListener('click', handleClick);
// 클릭 시: this는 button 요소 (이벤트 핸들러는 예외)

// 화살표 함수 이벤트 핸들러
const arrowHandleClick = () => {
    console.log('Arrow function clicked!');
    console.log('this in arrow handler:', this);
};

// 일반 모드와 엄격 모드 모두 동일
button.addEventListener('click', arrowHandleClick);
// 클릭 시: this는 전역 객체 (렉시컬 this)
```

#### 클래스 메서드에서의 차이
```javascript
class Calculator {
    constructor() {
        this.result = 0;
    }
    
    // 일반 함수 메서드
    addRegular(x, y) {
        this.result = x + y;
        return this.result;
    }
    
    // 화살표 함수 메서드
    addArrow = (x, y) => {
        this.result = x + y;
        return this.result;
    };
    
    // 콜백에서의 차이
    processWithCallback(callback) {
        // 일반 함수 콜백
        callback(5, 3);
    }
}

const calc = new Calculator();

// 일반 모드
calc.processWithCallback(function(x, y) {
    console.log('Regular callback this:', this); // undefined (엄격 모드)
    console.log('Result:', x + y);
});

// 화살표 함수 콜백
calc.processWithCallback((x, y) => {
    console.log('Arrow callback this:', this); // 전역 객체
    console.log('Result:', x + y);
});
```

### 2. 고급 패턴

#### this 바인딩 유지 방법
```javascript
class DataProcessor {
    constructor() {
        this.data = [];
    }
    
    // 방법 1: 화살표 함수 사용
    processDataArrow = () => {
        setTimeout(() => {
            this.data.push('processed');
            console.log('Arrow function - data:', this.data);
        }, 1000);
    };
    
    // 방법 2: bind 사용
    processDataBind() {
        setTimeout(function() {
            this.data.push('processed');
            console.log('Bind function - data:', this.data);
        }.bind(this), 1000);
    }
    
    // 방법 3: 변수에 this 저장
    processDataVar() {
        const self = this;
        setTimeout(function() {
            self.data.push('processed');
            console.log('Variable function - data:', self.data);
        }, 1000);
    }
    
    // 방법 4: call/apply 사용
    processDataCall() {
        const callback = function() {
            this.data.push('processed');
            console.log('Call function - data:', this.data);
        };
        setTimeout(() => callback.call(this), 1000);
    }
}

const processor = new DataProcessor();

// 모든 방법이 동일하게 작동
processor.processDataArrow();
processor.processDataBind();
processor.processDataVar();
processor.processDataCall();
```

#### 모듈 패턴에서의 this
```javascript
// 즉시 실행 함수 표현식 (IIFE)
const module = (function() {
    "use strict";
    
    let privateData = [];
    
    function privateMethod() {
        console.log('Private method this:', this); // undefined
    }
    
    return {
        publicMethod: function() {
            console.log('Public method this:', this); // module 객체
            privateMethod();
        },
        
        arrowMethod: () => {
            console.log('Arrow method this:', this); // 전역 객체
        }
    };
})();

module.publicMethod();
module.arrowMethod();
```

## 운영 팁

### 성능 최적화

#### this 바인딩 최적화
```javascript
// 비효율적인 방법: 매번 새로운 함수 생성
class InefficientClass {
    constructor() {
        this.data = [];
    }
    
    addItem(item) {
        // 매번 새로운 화살표 함수 생성
        setTimeout(() => {
            this.data.push(item);
        }, 100);
    }
}

// 효율적인 방법: 메서드를 미리 바인딩
class EfficientClass {
    constructor() {
        this.data = [];
        // 생성자에서 한 번만 바인딩
        this.addItem = this.addItem.bind(this);
    }
    
    addItem(item) {
        setTimeout(this.addItem, 100);
    }
}
```

### 에러 처리

#### this 바인딩 오류 해결
```javascript
// 문제: this 바인딩 오류
class ProblemClass {
    constructor() {
        this.name = 'Problem';
    }
    
    problematicMethod() {
        setTimeout(function() {
            console.log('Name:', this.name); // undefined
        }, 100);
    }
}

// 해결 1: 화살표 함수 사용
class Solution1Class {
    constructor() {
        this.name = 'Solution1';
    }
    
    fixedMethod() {
        setTimeout(() => {
            console.log('Name:', this.name); // 'Solution1'
        }, 100);
    }
}

// 해결 2: bind 사용
class Solution2Class {
    constructor() {
        this.name = 'Solution2';
    }
    
    fixedMethod() {
        setTimeout(function() {
            console.log('Name:', this.name); // 'Solution2'
        }.bind(this), 100);
    }
}

// 해결 3: 변수에 this 저장
class Solution3Class {
    constructor() {
        this.name = 'Solution3';
    }
    
    fixedMethod() {
        const self = this;
        setTimeout(function() {
            console.log('Name:', self.name); // 'Solution3'
        }, 100);
    }
}
```

## 참고

### use strict 모드에서의 this 비교표

| 호출 방식 | 일반 모드 | 엄격 모드 | 화살표 함수 |
|-----------|-----------|-----------|-------------|
| **일반 함수 호출** | window/globalThis | undefined | 렉시컬 this |
| **메서드 호출** | 해당 객체 | 해당 객체 | 렉시컬 this |
| **생성자 호출** | 새 인스턴스 | 새 인스턴스 | 사용 불가 |
| **이벤트 핸들러** | 이벤트 대상 | 이벤트 대상 | 렉시컬 this |

### this 바인딩 방법 비교

| 방법 | 장점 | 단점 | 사용 시기 |
|------|------|------|-----------|
| **화살표 함수** | 간결, 안전 | 렉시컬 this 고정 | 콜백, 이벤트 핸들러 |
| **bind** | 유연한 바인딩 | 추가 코드 필요 | 동적 바인딩 필요 |
| **call/apply** | 즉시 실행 | 일회성 | 즉시 실행 필요 |
| **변수 저장** | 간단 | 변수 오염 | 간단한 경우 |

### 결론
use strict 모드는 JavaScript 코드의 안전성을 향상시킵니다.
일반 함수에서 this 바인딩이 더 엄격해집니다.
화살표 함수는 use strict의 영향을 받지 않습니다.
적절한 this 바인딩 방법을 선택하여 오류를 방지하세요.
성능을 고려하여 효율적인 바인딩 방법을 사용하세요.
this 바인딩 오류를 사전에 방지하기 위한 패턴을 숙지하세요.

