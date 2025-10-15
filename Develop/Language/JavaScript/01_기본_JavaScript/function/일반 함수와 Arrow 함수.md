---
title: JavaScript 일반 함수와 화살표 함수 비교
tags: [language, javascript, 01기본javascript, function, arrow-function, this-binding]
updated: 2025-10-15
---

# JavaScript 일반 함수와 화살표 함수 비교

## 배경

JavaScript에서 함수를 정의하는 방법은 크게 두 가지가 있습니다: 일반 함수와 화살표 함수입니다. 각각의 방식은 고유한 특징과 사용 사례가 있으며, 적절한 상황에 맞는 함수 정의 방식을 선택하는 것이 중요합니다.

### 함수 정의 방식의 필요성
- **코드 가독성**: 상황에 맞는 함수 정의 방식으로 코드의 의도를 명확히 표현
- **this 바인딩**: 함수 내부에서 this가 가리키는 객체의 차이
- **메모리 효율성**: 함수 생성과 실행의 성능 차이
- **호이스팅**: 함수 선언의 호이스팅 여부

### 기본 개념
- **일반 함수**: 전통적인 함수 선언식과 표현식
- **화살표 함수**: ES6에서 도입된 간결한 함수 표현 방식
- **this 바인딩**: 함수 내부에서 this가 참조하는 객체
- **렉시컬 스코프**: 함수가 정의된 위치의 스코프

## 핵심

### 1. 함수 정의 방식의 차이

#### 일반 함수 (Function Declaration/Expression)
일반 함수는 JavaScript의 전통적인 함수 정의 방식으로, 두 가지 형태로 나뉩니다.

**함수 선언식 (Function Declaration)**
- `function` 키워드로 시작하는 함수 정의 방식
- 호이스팅이 발생하여 함수 선언 전에도 호출 가능
- 함수명이 필수이며, 함수 전체가 스코프의 최상단으로 끌어올려짐

**함수 표현식 (Function Expression)**
- 변수에 함수를 할당하는 방식
- 호이스팅되지 않아 선언 전 호출 시 오류 발생
- 익명 함수나 기명 함수 모두 가능

**즉시 실행 함수 (IIFE)**
- 정의와 동시에 실행되는 함수
- 전역 스코프 오염 방지에 주로 사용
- 모듈 패턴 구현의 기초가 되는 개념

#### 화살표 함수 (Arrow Function)
ES6에서 도입된 화살표 함수는 기존 함수 정의 방식을 간소화한 문법입니다.

**기본 특징**
- `=>` 화살표 문법을 사용한 간결한 함수 표현
- 항상 익명 함수로 정의됨
- `function` 키워드 없이 함수 정의 가능

**문법적 특징**
- 단일 표현식의 경우 `return`과 중괄호 생략 가능
- 매개변수가 하나인 경우 괄호 생략 가능
- 매개변수가 없는 경우 괄호는 필수
- 객체 반환 시 괄호로 감싸야 함

### 2. 주요 차이점

#### this 바인딩의 핵심 차이
가장 중요한 차이점은 `this` 키워드의 동작 방식입니다. 이는 JavaScript의 함수 호출 방식과 밀접한 관련이 있습니다.

**일반 함수의 this 바인딩**
- **동적 바인딩**: 함수가 호출되는 시점에 `this`가 결정됨
- **호출 컨텍스트에 의존**: 함수를 어떻게 호출하느냐에 따라 `this`가 달라짐
- **메서드 호출**: 객체의 메서드로 호출 시 해당 객체를 `this`로 참조
- **일반 함수 호출**: 전역 객체(브라우저에서는 `window`, Node.js에서는 `global`)를 `this`로 참조
- **생성자 함수 호출**: 새로 생성되는 인스턴스를 `this`로 참조

**화살표 함수의 this 바인딩**
- **렉시컬 바인딩**: 함수가 정의된 위치의 `this`를 그대로 사용
- **정적 바인딩**: 함수 정의 시점에 `this`가 결정되어 변경되지 않음
- **상위 스코프 상속**: 화살표 함수 자체의 `this`가 없고, 상위 스코프의 `this`를 참조
- **호출 방식 무관**: 어떻게 호출하든 상위 스코프의 `this`를 유지

#### this 바인딩의 실제 동작

**일반 함수에서의 this 변화**
일반 함수는 호출 방식에 따라 `this`가 동적으로 변경됩니다. 메서드로 호출할 때는 해당 객체를, 일반 함수로 호출할 때는 전역 객체를 참조합니다. 이는 JavaScript의 함수가 일급 객체이면서 동시에 메서드로도 사용될 수 있기 때문입니다.

**화살표 함수에서의 this 고정**
화살표 함수는 자신만의 `this`를 가지지 않고, 정의된 시점의 상위 스코프의 `this`를 그대로 사용합니다. 이는 화살표 함수가 `this`를 바인딩하지 않기 때문이며, 이로 인해 예측 가능한 `this` 동작을 보장합니다.

### 2-1. this와 화살표 함수의 깊은 관계

#### this 바인딩의 메커니즘

**일반 함수의 this 바인딩 규칙**
JavaScript에서 `this`는 함수가 호출되는 방식에 따라 결정됩니다:

1. **메서드 호출**: `obj.method()` - `this`는 `obj`
2. **일반 함수 호출**: `function()` - `this`는 전역 객체 (strict mode에서는 `undefined`)
3. **생성자 호출**: `new Function()` - `this`는 새로 생성된 객체
4. **명시적 바인딩**: `function.call(obj)` - `this`는 `obj`

**화살표 함수의 this 상속**
화살표 함수는 이러한 `this` 바인딩 규칙을 무시하고, 렉시컬 스코프의 `this`를 그대로 사용합니다:

```javascript
// 일반 함수의 this 바인딩
const obj = {
    name: 'Object',
    regularMethod: function() {
        console.log(this.name); // 'Object'
        
        // 내부 함수에서 this는 전역 객체
        function innerFunction() {
            console.log(this.name); // undefined (strict mode) 또는 전역 객체
        }
        innerFunction();
    }
};

// 화살표 함수의 this 상속
const obj2 = {
    name: 'Object',
    arrowMethod: function() {
        console.log(this.name); // 'Object'
        
        // 화살표 함수는 상위 스코프의 this를 사용
        const innerArrow = () => {
            console.log(this.name); // 'Object' (상위 스코프의 this)
        };
        innerArrow();
    }
};
```

#### this 바인딩 문제와 해결책

**전통적인 해결 방법들**
화살표 함수가 도입되기 전에는 `this` 바인딩 문제를 해결하기 위해 여러 방법을 사용했습니다:

```javascript
class EventHandler {
    constructor() {
        this.count = 0;
    }
    
    // 방법 1: 변수에 this 저장
    setupEvent1() {
        const self = this;
        document.addEventListener('click', function() {
            self.count++;
        });
    }
    
    // 방법 2: bind 메서드 사용
    setupEvent2() {
        document.addEventListener('click', function() {
            this.count++;
        }.bind(this));
    }
    
    // 방법 3: 화살표 함수 사용 (ES6+)
    setupEvent3() {
        document.addEventListener('click', () => {
            this.count++; // 가장 간단하고 직관적
        });
    }
}
```

**화살표 함수의 this 바인딩 장점**
- **예측 가능성**: `this`가 언제나 상위 스코프의 값을 유지
- **간결성**: `bind()`나 변수 저장 없이도 `this` 바인딩 문제 해결
- **일관성**: 함수가 어디서 호출되든 `this` 값이 변하지 않음

### 3. 호이스팅 차이

#### 호이스팅의 개념
호이스팅은 JavaScript의 변수와 함수 선언이 스코프의 최상단으로 끌어올려지는 현상입니다. 이는 JavaScript 엔진이 코드를 실행하기 전에 선언을 먼저 처리하기 때문입니다.

#### 일반 함수의 호이스팅

**함수 선언식의 호이스팅**
- 함수 선언식은 전체 함수가 스코프의 최상단으로 끌어올려짐
- 함수 선언 전에도 함수를 호출할 수 있음
- 함수의 이름과 본문 모두 호이스팅됨
- 이는 함수 선언식이 "완전한 호이스팅"을 받기 때문

**함수 표현식의 호이스팅**
- 함수 표현식은 호이스팅되지 않음
- 변수 선언만 호이스팅되고, 함수 할당은 원래 위치에서 실행됨
- 선언 전 호출 시 `TypeError` 발생
- 이는 함수 표현식이 변수에 할당되는 방식이기 때문

#### 화살표 함수의 호이스팅
- 화살표 함수는 함수 표현식과 동일하게 동작
- 변수 선언만 호이스팅되고, 함수 할당은 원래 위치에서 실행
- 선언 전 호출 시 `TypeError` 발생
- 화살표 함수도 본질적으로 변수에 할당되는 함수 표현식이기 때문

### 4. 생성자 함수 사용

#### 생성자 함수의 개념
생성자 함수는 `new` 키워드와 함께 사용되어 새로운 객체 인스턴스를 생성하는 함수입니다. 이는 JavaScript의 프로토타입 기반 객체 지향 프로그래밍의 핵심 개념입니다.

#### 일반 함수의 생성자 기능

**생성자 함수로서의 일반 함수**
- 일반 함수는 `new` 키워드와 함께 생성자로 사용 가능
- 생성자 함수 내부에서 `this`는 새로 생성되는 인스턴스를 참조
- `prototype` 속성을 통해 인스턴스 간 공유되는 메서드 정의 가능
- 생성자 함수는 객체의 초기 상태를 설정하는 역할

**프로토타입 체인의 활용**
- 생성자 함수의 `prototype` 속성은 모든 인스턴스가 공유
- 인스턴스는 생성자 함수의 `prototype` 객체에 접근 가능
- 메모리 효율적인 메서드 공유 방식 제공

#### 화살표 함수의 생성자 제한

**생성자로 사용할 수 없는 이유**
- 화살표 함수는 `prototype` 속성을 가지지 않음
- `new` 키워드와 함께 호출할 수 없음
- `this` 바인딩이 렉시컬이므로 생성자 함수의 동작과 맞지 않음
- 화살표 함수는 본질적으로 생성자 함수가 아닌 일반 함수

**설계 철학의 차이**
- 화살표 함수는 간결한 함수 표현을 위한 문법적 설탕
- 생성자 함수는 객체 지향 프로그래밍을 위한 특별한 함수
- 두 개념은 서로 다른 목적을 가지고 있어 호환되지 않음

## 예시

### 1. this 바인딩 차이

#### this 바인딩 메커니즘 비교
```javascript
// 일반 함수의 this 바인딩
const person = {
    name: 'Alice',
    greet: function() {
        console.log(`Hello, I'm ${this.name}`);
        
        // 내부 함수에서 this는 전역 객체
        function innerFunction() {
            console.log(`Inner: ${this.name}`); // undefined 또는 전역 객체
        }
        innerFunction();
        
        // 화살표 함수는 상위 스코프의 this 사용
        const innerArrow = () => {
            console.log(`Arrow: ${this.name}`); // 'Alice'
        };
        innerArrow();
    }
};

person.greet();
// 출력:
// Hello, I'm Alice
// Inner: undefined
// Arrow: Alice
```

#### 이벤트 핸들러에서의 차이
```javascript
class Button {
    constructor() {
        this.count = 0;
        this.setupEvent();
    }
    
    setupEvent() {
        // 일반 함수 - this가 button 요소를 참조
        document.getElementById('btn1').addEventListener('click', function() {
            console.log(this); // <button> 요소
            // this.count 접근 불가
        });
        
        // 화살표 함수 - this가 Button 인스턴스를 참조
        document.getElementById('btn2').addEventListener('click', () => {
            console.log(this); // Button 인스턴스
            this.count++;
            console.log('Count:', this.count);
        });
    }
}
```

#### 클래스 메서드에서의 차이
```javascript
class Timer {
    constructor() {
        this.seconds = 0;
    }
    
    // 일반 함수 메서드
    startRegular() {
        setInterval(function() {
            this.seconds++; // this는 전역 객체
            console.log(this.seconds); // NaN
        }, 1000);
    }
    
    // 화살표 함수 메서드
    startArrow = () => {
        setInterval(() => {
            this.seconds++; // this는 Timer 인스턴스
            console.log(this.seconds); // 정상 동작
        }, 1000);
    };
}
```

#### this 바인딩 문제 해결 방법 비교
```javascript
class DataProcessor {
    constructor() {
        this.data = [];
    }
    
    // 문제 상황: 일반 함수에서 this 바인딩 문제
    processDataProblem() {
        setTimeout(function() {
            this.data.push('processed'); // TypeError: this.data is undefined
        }, 1000);
    }
    
    // 해결 1: 화살표 함수 사용 (권장)
    processDataArrow() {
        setTimeout(() => {
            this.data.push('processed'); // 정상 동작
        }, 1000);
    }
    
    // 해결 2: bind 메서드 사용
    processDataBind() {
        setTimeout(function() {
            this.data.push('processed');
        }.bind(this), 1000);
    }
    
    // 해결 3: 변수에 this 저장 (전통적 방법)
    processDataSelf() {
        const self = this;
        setTimeout(function() {
            self.data.push('processed');
        }, 1000);
    }
    
    // 해결 4: call/apply 사용
    processDataCall() {
        setTimeout(function() {
            this.data.push('processed');
        }.call(this), 1000);
    }
}
```

### 2. 배열 메서드에서의 사용

#### 간단한 변환 작업
```javascript
const numbers = [1, 2, 3, 4, 5];

// 화살표 함수 - 간결함
const doubled = numbers.map(n => n * 2);
const evens = numbers.filter(n => n % 2 === 0);
const sum = numbers.reduce((acc, n) => acc + n, 0);

// 일반 함수 - 더 명시적
const doubledRegular = numbers.map(function(n) {
    return n * 2;
});
```

#### 객체 배열 처리
```javascript
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 },
    { name: 'Charlie', age: 35 }
];

// 화살표 함수
const adultNames = users
    .filter(user => user.age >= 30)
    .map(user => user.name);

// 일반 함수
const adultNamesRegular = users
    .filter(function(user) {
        return user.age >= 30;
    })
    .map(function(user) {
        return user.name;
    });
```

### 3. 고급 패턴

#### 클래스 메서드 정의
```javascript
class Calculator {
    constructor() {
        this.result = 0;
    }
    
    // 일반 함수 메서드 - 프로토타입에 정의
    add(x, y) {
        this.result = x + y;
        return this.result;
    }
    
    // 화살표 함수 메서드 - 인스턴스 필드로 정의
    multiply = (x, y) => {
        this.result = x * y;
        return this.result;
    };
}

const calc = new Calculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.multiply(4, 6)); // 24
```

#### 비동기 작업에서의 차이
```javascript
class DataFetcher {
    constructor() {
        this.data = null;
    }
    
    // 일반 함수 - this 바인딩 문제 발생 가능
    fetchDataRegular() {
        fetch('/api/data')
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                this.data = data; // this는 전역 객체
            });
    }
    
    // 화살표 함수 - this 바인딩 유지
    fetchDataArrow = () => {
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                this.data = data; // this는 DataFetcher 인스턴스
            });
    };
}
```

#### Promise 체인에서의 활용
```javascript
// 화살표 함수로 간결한 Promise 체인
const fetchUserData = (userId) => {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            console.log('User:', user.name);
            return user;
        })
        .catch(error => {
            console.error('Error:', error);
            throw error;
        });
};

// 일반 함수로 작성한 경우
const fetchUserDataRegular = function(userId) {
    return fetch(`/api/users/${userId}`)
        .then(function(response) {
            return response.json();
        })
        .then(function(user) {
            console.log('User:', user.name);
            return user;
        })
        .catch(function(error) {
            console.error('Error:', error);
            throw error;
        });
};
```

## 운영 팁

### 성능 최적화 전략

#### 메모리 사용량 최적화

**함수 객체 생성의 차이점**
- 일반 함수와 화살표 함수 모두 매번 새로운 함수 객체를 생성
- 성능상 큰 차이는 없지만, 화살표 함수가 약간 더 간결한 문법 제공
- 대량의 함수 생성 시 메모리 사용량을 고려해야 함

**메모리 효율성 고려사항**
- 클래스 메서드에서 일반 함수는 프로토타입에 정의되어 인스턴스 간 공유
- 화살표 함수 메서드는 각 인스턴스마다 별도 생성되어 메모리 사용량 증가
- 상황에 따라 적절한 방식을 선택하여 메모리 효율성 확보

#### 디버깅과 개발자 도구 활용

**스택 트레이스의 차이점**
- 일반 함수는 함수명이 스택 트레이스에 명확히 표시됨
- 화살표 함수는 익명 함수로 표시될 수 있어 디버깅 시 어려움 발생 가능
- 복잡한 로직에서는 명명된 함수를 사용하는 것이 디버깅에 유리

**디버깅 전략**
- 중요한 함수는 명시적으로 이름을 부여하여 스택 트레이스에서 식별 가능하게 함
- 화살표 함수 사용 시에도 내부 로직을 명확하게 작성하여 가독성 확보
- 개발자 도구의 프로파일러를 활용하여 성능 병목 지점 파악

### 에러 처리와 문제 해결

#### this 바인딩 오류의 원인과 해결

**일반적인 this 바인딩 문제**
- 콜백 함수에서 `this`가 예상과 다른 객체를 참조하는 문제
- 비동기 작업에서 클래스 인스턴스의 상태에 접근할 수 없는 문제
- 이벤트 핸들러에서 `this` 컨텍스트가 변경되는 문제

**해결 방법의 종류와 특징**
- **화살표 함수 사용**: 가장 간단하고 직관적인 해결 방법
- **bind 메서드 사용**: 기존 함수의 `this`를 명시적으로 바인딩
- **변수에 this 저장**: 전통적인 해결 방법으로 `self` 또는 `that` 변수 사용

**각 해결 방법의 장단점**
- 화살표 함수: 간결하지만 `arguments` 객체 사용 불가
- bind 메서드: 기존 함수의 모든 기능 유지하지만 추가 메모리 사용
- 변수 저장: 전통적 방법이지만 코드가 다소 장황해짐

## 참고

### 일반 함수 vs 화살표 함수 비교표

| 구분 | 일반 함수 | 화살표 함수 |
|------|-----------|-------------|
| **this 바인딩** | 동적 바인딩 | 렉시컬 바인딩 |
| **생성자 사용** | 가능 | 불가능 |
| **호이스팅** | 함수 선언식만 | 불가능 |
| **arguments 객체** | 사용 가능 | 사용 불가능 |
| **prototype** | 있음 | 없음 |
| **메서드 정의** | 가능 | 클래스 필드로만 |

### 사용 권장사항

| 상황 | 권장 방식 | 이유 |
|------|-----------|------|
| **클래스 메서드** | 일반 함수 | this 바인딩이 명확함 |
| **이벤트 핸들러** | 화살표 함수 | this 바인딩 유지 |
| **콜백 함수** | 화살표 함수 | 간결하고 this 바인딩 유지 |
| **생성자 함수** | 일반 함수 | new 키워드 사용 가능 |
| **고차 함수** | 화살표 함수 | 간결한 문법 |

### 결론

일반 함수와 화살표 함수는 각각의 장단점이 있으며, 상황에 따라 적절한 선택이 필요합니다. 

**핵심 고려사항**
- `this` 바인딩 차이를 정확히 이해하고 적절한 상황에 맞는 함수를 선택
- 화살표 함수는 콜백과 이벤트 핸들러에서 특히 유용
- 일반 함수는 생성자와 메서드 정의에 적합
- 성능보다는 코드의 의도와 가독성을 우선시
- `this` 바인딩 문제를 해결하기 위한 다양한 방법을 숙지

**실무 적용 가이드**
- 팀 내 코딩 컨벤션을 정립하여 일관성 있는 코드 작성
- 복잡한 로직에서는 가독성을 우선시하여 적절한 함수 타입 선택
- 디버깅과 유지보수를 고려한 함수 설계
- 성능이 중요한 부분에서는 프로파일링을 통한 최적화 검토

---

## 참조

- [MDN Web Docs - Arrow functions](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/Arrow_functions)
- [MDN Web Docs - Function](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function)
- [MDN Web Docs - this](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this)
- [ECMAScript 2015 Language Specification - Arrow Function Definitions](https://262.ecma-international.org/6.0/#sec-arrow-function-definitions)
- [JavaScript.info - Arrow functions revisited](https://javascript.info/arrow-functions)
- [You Don't Know JS: this & Object Prototypes](https://github.com/getify/You-Dont-Know-JS/blob/1st-ed/this%20%26%20object%20prototypes/README.md)
- [Exploring ES6 - Arrow functions](https://exploringjs.com/es6/ch_arrow-functions.html)
