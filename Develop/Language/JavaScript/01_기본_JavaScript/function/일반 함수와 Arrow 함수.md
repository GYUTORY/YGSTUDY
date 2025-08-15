---
title: JavaScript 일반 함수와 화살표 함수 비교
tags: [language, javascript, 01기본javascript, function, arrow-function, this-binding]
updated: 2025-08-10
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
```javascript
// 함수 선언식 (Function Declaration)
function greet(name) {
    return `Hello, ${name}!`;
}

// 함수 표현식 (Function Expression)
const greet = function(name) {
    return `Hello, ${name}!`;
};

// 즉시 실행 함수 (IIFE)
(function() {
    console.log('즉시 실행됩니다.');
})();
```

#### 화살표 함수 (Arrow Function)
```javascript
// 기본 화살표 함수
const greet = (name) => {
    return `Hello, ${name}!`;
};

// 단일 표현식의 경우 return과 중괄호 생략 가능
const greet = (name) => `Hello, ${name}!`;

// 매개변수가 하나인 경우 괄호 생략 가능
const square = x => x * x;

// 매개변수가 없는 경우 괄호 필수
const sayHello = () => 'Hello!';

// 객체를 반환하는 경우 괄호로 감싸기
const createUser = (name, age) => ({ name, age });
```

### 2. 주요 차이점

#### this 바인딩
가장 중요한 차이점은 `this` 키워드의 동작 방식입니다.

#### 일반 함수의 this
```javascript
// 일반 함수의 this 바인딩 예제
class Person {
    constructor(name) {
        this.name = name;
    }
    
    // 일반 함수로 정의된 메서드
    greet() {
        console.log(`Hello, my name is ${this.name}`);
    }
    
    // 일반 함수로 정의된 메서드 (setTimeout에서 사용)
    delayedGreet() {
        setTimeout(function() {
            console.log(`Hello, my name is ${this.name}`);
        }, 1000);
    }
}

const person = new Person('Alice');
person.greet();  // "Hello, my name is Alice"

// setTimeout 내부의 일반 함수는 전역 객체의 this를 참조
person.delayedGreet();  // "Hello, my name is undefined"
```

#### 화살표 함수의 this
```javascript
// 화살표 함수의 this 바인딩 예제
class Person {
    constructor(name) {
        this.name = name;
    }
    
    // 화살표 함수로 정의된 메서드
    greet = () => {
        console.log(`Hello, my name is ${this.name}`);
    };
    
    // 화살표 함수로 정의된 메서드 (setTimeout에서 사용)
    delayedGreet() {
        setTimeout(() => {
            console.log(`Hello, my name is ${this.name}`);
        }, 1000);
    }
}

const person = new Person('Alice');
person.greet();  // "Hello, my name is Alice"

// setTimeout 내부의 화살표 함수는 상위 스코프의 this를 참조
person.delayedGreet();  // "Hello, my name is Alice"
```

### 3. 호이스팅 차이

#### 일반 함수의 호이스팅
```javascript
// 함수 선언식은 호이스팅됨
console.log(greet('Alice')); // "Hello, Alice!"

function greet(name) {
    return `Hello, ${name}!`;
}

// 함수 표현식은 호이스팅되지 않음
console.log(greet2('Bob')); // TypeError: greet2 is not a function

const greet2 = function(name) {
    return `Hello, ${name}!`;
};
```

#### 화살표 함수의 호이스팅
```javascript
// 화살표 함수는 호이스팅되지 않음
console.log(greet('Alice')); // TypeError: greet is not a function

const greet = (name) => `Hello, ${name}!`;
```

### 4. 생성자 함수 사용

#### 일반 함수는 생성자로 사용 가능
```javascript
function Person(name, age) {
    this.name = name;
    this.age = age;
}

Person.prototype.greet = function() {
    return `Hello, I'm ${this.name} and I'm ${this.age} years old.`;
};

const person = new Person('Alice', 30);
console.log(person.greet()); // "Hello, I'm Alice and I'm 30 years old."
```

#### 화살표 함수는 생성자로 사용 불가
```javascript
const Person = (name, age) => {
    this.name = name;
    this.age = age;
};

// TypeError: Person is not a constructor
const person = new Person('Alice', 30);
```

## 예시

### 1. 실제 사용 사례

#### 이벤트 핸들러에서의 사용
```javascript
// DOM 요소 선택
const button = document.getElementById('myButton');
const input = document.getElementById('myInput');

// 일반 함수를 이벤트 핸들러로 사용
button.addEventListener('click', function() {
    console.log('Button clicked!');
    console.log('this refers to:', this); // button 요소
});

// 화살표 함수를 이벤트 핸들러로 사용
button.addEventListener('click', () => {
    console.log('Button clicked!');
    console.log('this refers to:', this); // 전역 객체 (window)
});

// 클래스 메서드에서 이벤트 핸들러 사용
class FormHandler {
    constructor() {
        this.data = [];
        this.button = document.getElementById('submitButton');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // 일반 함수 사용 - this가 FormHandler 인스턴스를 참조하지 않음
        this.button.addEventListener('click', function() {
            console.log('this in regular function:', this); // button 요소
            // this.data에 접근할 수 없음
        });
        
        // 화살표 함수 사용 - this가 FormHandler 인스턴스를 참조
        this.button.addEventListener('click', () => {
            console.log('this in arrow function:', this); // FormHandler 인스턴스
            this.data.push('new item');
            console.log('Data updated:', this.data);
        });
    }
}

const formHandler = new FormHandler();
```

#### 배열 메서드에서의 사용
```javascript
const numbers = [1, 2, 3, 4, 5];
const users = [
    { name: 'Alice', age: 25 },
    { name: 'Bob', age: 30 },
    { name: 'Charlie', age: 35 }
];

// map 메서드에서 화살표 함수 사용
const doubled = numbers.map(num => num * 2);
console.log(doubled); // [2, 4, 6, 8, 10]

// filter 메서드에서 화살표 함수 사용
const adults = users.filter(user => user.age >= 30);
console.log(adults); // [{ name: 'Bob', age: 30 }, { name: 'Charlie', age: 35 }]

// reduce 메서드에서 화살표 함수 사용
const totalAge = users.reduce((sum, user) => sum + user.age, 0);
console.log(totalAge); // 90

// 일반 함수를 사용한 경우
const doubledRegular = numbers.map(function(num) {
    return num * 2;
});
console.log(doubledRegular); // [2, 4, 6, 8, 10]
```

### 2. 고급 패턴

#### 클래스에서의 메서드 정의
```javascript
class Calculator {
    constructor() {
        this.result = 0;
    }
    
    // 일반 함수 메서드
    add(x, y) {
        this.result = x + y;
        return this.result;
    }
    
    // 화살표 함수 메서드 (클래스 필드)
    multiply = (x, y) => {
        this.result = x * y;
        return this.result;
    };
    
    // 비동기 작업에서의 차이
    async fetchDataRegular() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();
            this.result = data.value;
            return this.result;
        } catch (error) {
            console.error('Error:', error);
        }
    }
    
    // 화살표 함수로 비동기 메서드 정의
    fetchDataArrow = async () => {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();
            this.result = data.value;
            return this.result;
        } catch (error) {
            console.error('Error:', error);
        }
    };
}

const calc = new Calculator();
console.log(calc.add(5, 3)); // 8
console.log(calc.multiply(4, 6)); // 24
```

#### 콜백 함수에서의 사용
```javascript
// Promise 체인에서의 사용
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .then(user => {
            console.log('User data:', user);
            return user;
        })
        .catch(error => {
            console.error('Error fetching user:', error);
            throw error;
        });
}

// async/await에서의 사용
const fetchUserDataAsync = async (userId) => {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const user = await response.json();
        console.log('User data:', user);
        return user;
    } catch (error) {
        console.error('Error fetching user:', error);
        throw error;
    }
};

// setTimeout에서의 사용
class Timer {
    constructor() {
        this.count = 0;
    }
    
    startRegular() {
        setTimeout(function() {
            console.log('Count:', this.count); // undefined
        }, 1000);
    }
    
    startArrow() {
        setTimeout(() => {
            console.log('Count:', this.count); // 0
            this.count++;
        }, 1000);
    }
}

const timer = new Timer();
timer.startRegular(); // Count: undefined
timer.startArrow();   // Count: 0
```

## 운영 팁

### 성능 최적화

#### 메모리 사용량 최적화
```javascript
// 일반 함수는 매번 새로운 함수 객체 생성
const handlers = [];
for (let i = 0; i < 1000; i++) {
    handlers.push(function() {
        console.log(i);
    });
}

// 화살표 함수도 매번 새로운 함수 객체 생성
const arrowHandlers = [];
for (let i = 0; i < 1000; i++) {
    arrowHandlers.push(() => {
        console.log(i);
    });
}

// 성능상 큰 차이는 없지만, 화살표 함수가 약간 더 간결
```

#### 디버깅 고려사항
```javascript
// 일반 함수는 함수명이 스택 트레이스에 나타남
function processData(data) {
    return data.map(function(item) {
        return item * 2;
    });
}

// 화살표 함수는 익명 함수로 표시될 수 있음
function processDataArrow(data) {
    return data.map(item => item * 2);
}

// 디버깅을 위해 명명된 화살표 함수 사용
function processDataNamed(data) {
    return data.map((item) => {
        const doubled = item * 2;
        return doubled;
    });
}
```

### 에러 처리

#### this 바인딩 오류 해결
```javascript
// 문제: 일반 함수에서 this 바인딩 오류
class DataProcessor {
    constructor() {
        this.data = [];
    }
    
    processData() {
        // 일반 함수 사용 시 this 바인딩 문제
        setTimeout(function() {
            this.data.push('processed');
        }, 1000);
    }
}

// 해결 1: 화살표 함수 사용
class DataProcessorFixed {
    constructor() {
        this.data = [];
    }
    
    processData() {
        setTimeout(() => {
            this.data.push('processed');
        }, 1000);
    }
}

// 해결 2: bind 사용
class DataProcessorBind {
    constructor() {
        this.data = [];
    }
    
    processData() {
        setTimeout(function() {
            this.data.push('processed');
        }.bind(this), 1000);
    }
}

// 해결 3: 변수에 this 저장
class DataProcessorVar {
    constructor() {
        this.data = [];
    }
    
    processData() {
        const self = this;
        setTimeout(function() {
            self.data.push('processed');
        }, 1000);
    }
}
```

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
일반 함수와 화살표 함수는 각각의 장단점이 있습니다.
this 바인딩 차이를 이해하고 적절한 상황에 맞는 함수를 선택하세요.
화살표 함수는 콜백과 이벤트 핸들러에서 특히 유용합니다.
일반 함수는 생성자와 메서드 정의에 적합합니다.
성능보다는 코드의 의도와 가독성을 우선시하세요.
this 바인딩 문제를 해결하기 위한 다양한 방법을 숙지하세요.
