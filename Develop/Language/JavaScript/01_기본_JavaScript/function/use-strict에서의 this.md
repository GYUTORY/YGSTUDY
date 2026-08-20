---
title: JavaScript use strict에서의 this 바인딩
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript use strict에서의 this 바인딩

## 배경

JavaScript의 `"use strict"` 모드는 코드를 더 안전하게 만들고 잠재적인 오류를 막으려고 쓰는 엄격한 모드다. 이 모드에서는 `this` 키워드가 일반 모드와 다르게 동작한다.

### use strict의 필요성
- 안전성 향상: 잠재적인 오류를 컴파일 타임에 감지
- this 바인딩: 함수 내부에서 this의 명확한 동작
- 오류 방지: 실수로 인한 전역 객체 오염 방지
- 코드 품질: 더 엄격한 JavaScript 코드 작성

### 기본 개념
- 엄격 모드: `"use strict"` 지시어로 활성화되는 JavaScript 모드
- this 바인딩: 함수 내부에서 this가 참조하는 객체
- 렉시컬 스코프: 함수가 정의된 위치의 스코프
- 동적 바인딩: 함수 호출 방식에 따라 달라지는 this 값

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

이 문서 곳곳의 `"use strict";` 는 **실제로는 켜지지 않는다.** 지시어는 스크립트나 함수 본문의 **첫 문장**일 때만 효력이 있다. 위 블록처럼 다른 코드 아래에 두면 그냥 문자열 하나가 평가될 뿐이다.

```javascript
function notFirst() {
  const a = 1;
  "use strict";                        // ← 무시된다
  return (function () { return this; })();
}
notFirst();   // globalThis

function first() {
  "use strict";                        // ← 첫 문장이라 유효하다
  return (function () { return this; })();
}
first();      // undefined
```

그래서 "일반 모드"와 "엄격 모드"를 한 파일 안에서 위아래로 비교하는 것은 불가능하다. 위쪽에 지시어를 제대로 놓으면 아래 전부가 엄격해지고, 아래에 놓으면 아무 데도 안 걸린다. 두 모드를 정말 비교하려면 **파일을 나누거나 함수 안에 넣어야** 한다.

이 차이는 눈에 띄지 않는다. 문서 예제를 콘솔에 붙여넣고 "설명과 다르게 나오네"로 끝나기 쉬운 지점이다.

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

`class` 본문은 지시어와 무관하게 **언제나 엄격 모드**다. 그래서 클래스 메서드를 떼어내면 `this` 가 전역이 아니라 `undefined` 다.

```javascript
class C { m() { return this; } }
const m = new C().m;
m();          // undefined
```

같은 모양을 객체 리터럴로 만들면 결과가 다르다.

```javascript
const o = { m: function () { return this; } };
const om = o.m;
om();         // globalThis  (비엄격 파일에서)
```

이 차이가 실무에서 드러나는 자리가 콜백이다. 클래스 메서드를 `arr.map(this.format)` 이나 `addEventListener('click', this.onClick)` 로 넘기면 `this` 가 `undefined` 가 되어 `Cannot read properties of undefined` 로 터진다. 객체 리터럴 메서드였다면 전역 객체가 들어가서 **에러 대신 `undefined` 값**이 흘러 다녔을 것이다. 클래스 쪽이 시끄럽게 실패하는 만큼 낫다.

`arrowMethod = () => {}` 같은 클래스 필드는 프로토타입이 아니라 **인스턴스마다 하나씩** 만들어진다. 그래서 `Object.keys(example)` 에 잡히고, 위 출력에서 `arrowMethod` 가 인스턴스 속성으로 함께 찍힌다. 떼어내도 `this` 를 잃지 않는 대신 인스턴스가 늘어날수록 함수 객체도 같이 늘어난다.

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

`arrowMethod` 의 주석은 틀렸다. **전역 객체가 아니라 `undefined` 다.**

```javascript
module.arrowMethod();               // undefined
module.arrowMethod() === globalThis;  // false
```

화살표 함수는 정의된 위치의 `this` 를 그대로 쓴다. 여기서 정의된 위치는 IIFE 함수 본문이고, 그 IIFE 는 `"use strict"` 가 첫 문장이라 엄격 모드로 평범하게 호출된다 — 즉 IIFE 의 `this` 가 `undefined` 다. 화살표 함수는 그 `undefined` 를 물려받는다.

"화살표 함수는 use strict 의 영향을 받지 않는다"는 말이 여기서 오해를 만든다. 화살표 함수 자신이 `this` 를 정하지 않는 건 맞지만, **물려받는 바깥의 `this` 는 엄격 모드에 따라 달라진다.** 그러니 영향을 안 받는 게 아니라 한 단계 건너서 받는다.

`publicMethod` 쪽은 주석대로 동작한다. 반환된 객체의 메서드로 호출하니 `this` 는 그 객체다. 다만 그 안에서 `privateMethod()` 를 평범하게 호출하면 `this` 는 다시 `undefined` 로 떨어진다. 같은 함수 안에 있어도 **호출 방식이 바뀌면 `this` 도 바뀐다.**

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

`EfficientClass` 는 효율적인 게 아니라 **동작하지 않는다.** `addItem` 이 자기 자신을 다시 예약하기만 하고 `data` 에는 아무것도 넣지 않는다.

```
addItem 호출됨, item = X          | data = []
addItem 호출됨, item = undefined  | data = []
addItem 호출됨, item = undefined  | data = []
...
```

두 가지가 겹쳤다. 하나, `this.data.push` 가 없어서 저장이 일어나지 않는다. 둘, `setTimeout(this.addItem, 100)` 은 **인자를 넘기지 않으므로** 다음 호출부터 `item` 이 `undefined` 다. 타이머는 멈추지 않고 계속 새 타이머를 건다.

`bind` 를 생성자에서 한 번만 한다는 아이디어 자체는 맞다. 이 코드가 보여주려던 것은 아마 이런 형태다.

```javascript
class C {
  constructor() {
    this.data = [];
    this.flush = this.flush.bind(this);   // 한 번만 바인딩
  }
  add(item) {
    this.data.push(item);
    setTimeout(this.flush, 100);          // 매번 새 함수를 만들지 않는다
  }
  flush() { console.log(this.data); }
}
```

바로 위 `InefficientClass` 를 "비효율"이라 부른 근거도 이 문서에는 없다. 화살표 함수 하나가 호출마다 만들어지는 건 사실이지만, 그게 문제가 되는지는 호출 빈도에 달렸고 여기서는 재지 않았다. `bind` 를 생성자에서 한 번 해 두는 진짜 이유는 성능보다 **참조가 고정된다**는 데 있다.

```javascript
f.bind(o) === f.bind(o);      // false — 호출할 때마다 새 함수다
(() => {}) === (() => {});    // false — 인라인 화살표도 마찬가지
c.h === c.h;                  // true  — 생성자에서 한 번 만들어 두면 같다
```

등록한 리스너를 나중에 떼거나, 이전 값과 같은지 비교해 다시 그릴지 정하는 코드(React 의 의존성 배열 같은 것)에서는 이 동등성이 곧 정확성이다. "새 함수가 만들어져서 느리다"보다 "매번 다른 함수라 이전 것을 못 찾는다"가 먼저 문제가 된다.

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
use strict 모드는 JavaScript 코드를 더 안전하게 만든다.
일반 함수에서 this 바인딩이 더 엄격해진다.
화살표 함수는 use strict의 영향을 받지 않는다.
상황에 맞는 this 바인딩 방법을 골라 오류를 막는다.
성능을 따져 효율적인 바인딩 방법을 쓴다.
this 바인딩 오류를 미리 막는 패턴을 익혀 둔다.

