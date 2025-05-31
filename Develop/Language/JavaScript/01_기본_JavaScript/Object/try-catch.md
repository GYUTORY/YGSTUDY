# JavaScript try-catch 

## 목차
1. [try-catch란?](#try-catch란)
2. [기본 문법](#기본-문법)
3. [에러 객체](#에러-객체)
4. [throw new Error vs throw err](#throw-new-error-vs-throw-err)
5. [finally 블록](#finally-블록)
6. [중첩된 try-catch](#중첩된-try-catch)
7. [실제 사용 사례](#실제-사용-사례)
8. [모범 사례](#모범-사례)

## try-catch란?

try-catch는 JavaScript에서 예외 처리를 위한 구문입니다. 코드 실행 중 발생할 수 있는 오류를 처리하고 프로그램이 중단되지 않도록 하는 중요한 메커니즘입니다.

### 기본 개념
- `try` 블록: 오류가 발생할 수 있는 코드를 포함
- `catch` 블록: 오류가 발생했을 때 실행될 코드를 포함
- `finally` 블록: 오류 발생 여부와 관계없이 항상 실행되는 코드를 포함

## 기본 문법

```javascript
try {
    // 오류가 발생할 수 있는 코드
} catch (error) {
    // 오류 처리
} finally {
    // 항상 실행되는 코드
}
```

### 간단한 예제

```javascript
try {
    const result = 10 / 0;
    console.log(result);
} catch (error) {
    console.log('오류가 발생했습니다:', error.message);
}
```

## 에러 객체

JavaScript의 에러 객체는 다양한 속성과 메서드를 가지고 있습니다.

### 주요 에러 타입

1. **Error**: 기본 에러 객체
2. **SyntaxError**: 구문 오류
3. **TypeError**: 타입 오류
4. **ReferenceError**: 참조 오류
5. **RangeError**: 범위 오류
6. **URIError**: URI 처리 오류
7. **EvalError**: eval() 함수 관련 오류

### 에러 객체의 주요 속성

```javascript
try {
    throw new Error('테스트 에러');
} catch (error) {
    console.log('에러 이름:', error.name);
    console.log('에러 메시지:', error.message);
    console.log('스택 트레이스:', error.stack);
}
```

### 커스텀 에러 생성

```javascript
class CustomError extends Error {
    constructor(message) {
        super(message);
        this.name = 'CustomError';
    }
}

try {
    throw new CustomError('커스텀 에러 발생!');
} catch (error) {
    if (error instanceof CustomError) {
        console.log('커스텀 에러 처리:', error.message);
    } else {
        console.log('일반 에러 처리:', error.message);
    }
}
```

## throw new Error vs throw err

JavaScript에서 에러를 발생시키는 두 가지 주요 방법인 `throw new Error()`와 `throw err`의 사용 시나리오와 차이점에 대해 알아보겠습니다.

### throw new Error()

`throw new Error()`는 새로운 에러 객체를 생성하여 발생시킬 때 사용합니다.

#### 사용 시나리오

1. **새로운 에러 상황 발생 시**
```javascript
function validateAge(age) {
    if (age < 0) {
        throw new Error('나이는 0보다 커야 합니다.');
    }
    if (age > 150) {
        throw new Error('유효하지 않은 나이입니다.');
    }
    return true;
}
```

2. **비즈니스 로직 검증 시**
```javascript
function processOrder(order) {
    if (!order.items || order.items.length === 0) {
        throw new Error('주문 항목이 비어있습니다.');
    }
    if (!order.customerId) {
        throw new Error('고객 ID가 필요합니다.');
    }
    // 주문 처리 로직
}
```

3. **API 응답 검증 시**
```javascript
async function fetchUserData(userId) {
    const response = await fetch(`/api/users/${userId}`);
    if (!response.ok) {
        throw new Error(`사용자 데이터를 가져오는데 실패했습니다. 상태 코드: ${response.status}`);
    }
    return response.json();
}
```

### throw err

`throw err`는 이미 발생한 에러를 다시 던질 때 사용합니다.

#### 사용 시나리오

1. **에러를 상위 레벨로 전파할 때**
```javascript
async function processUserData(userId) {
    try {
        const userData = await fetchUserData(userId);
        return userData;
    } catch (err) {
        // 에러 로깅 후 상위로 전파
        console.error('사용자 데이터 처리 중 오류:', err);
        throw err;  // 원본 에러를 그대로 전파
    }
}
```

2. **에러를 변환하지 않고 전달할 때**
```javascript
function readConfigFile() {
    try {
        const config = fs.readFileSync('config.json', 'utf8');
        return JSON.parse(config);
    } catch (err) {
        // 파일 읽기 실패나 JSON 파싱 실패 시 원본 에러 전파
        throw err;
    }
}
```

3. **중첩된 try-catch에서 에러 전파 시**
```javascript
async function complexOperation() {
    try {
        try {
            await someAsyncOperation();
        } catch (innerErr) {
            // 내부 에러를 로깅하고 외부로 전파
            console.error('내부 작업 실패:', innerErr);
            throw innerErr;
        }
    } catch (outerErr) {
        // 외부 에러 처리
        console.error('전체 작업 실패:', outerErr);
    }
}
```

### 두 방식의 주요 차이점

1. **에러 스택 트레이스**
   - `throw new Error()`: 새로운 스택 트레이스가 생성됨
   - `throw err`: 기존 에러의 스택 트레이스가 유지됨

2. **에러 정보 보존**
   - `throw new Error()`: 새로운 에러 객체이므로 원본 에러 정보가 손실될 수 있음
   - `throw err`: 원본 에러의 모든 정보가 보존됨

3. **디버깅 용이성**
   - `throw new Error()`: 새로운 에러 메시지로 상황을 명확히 설명 가능
   - `throw err`: 원본 에러의 컨텍스트가 유지되어 디버깅이 용이

### 모범 사례

1. **새로운 에러 생성이 필요한 경우**
```javascript
function validateInput(input) {
    if (!input) {
        throw new Error('입력값이 필요합니다.');
    }
    if (typeof input !== 'string') {
        throw new Error('문자열 입력이 필요합니다.');
    }
}
```

2. **에러 전파가 필요한 경우**
```javascript
async function handleUserRequest(userId) {
    try {
        const userData = await fetchUserData(userId);
        return userData;
    } catch (err) {
        // 에러 로깅
        console.error('사용자 요청 처리 실패:', err);
        // 원본 에러 전파
        throw err;
    }
}
```

3. **에러 변환이 필요한 경우**
```javascript
async function processData() {
    try {
        await someOperation();
    } catch (err) {
        // 원본 에러 정보를 포함한 새로운 에러 생성
        throw new Error(`데이터 처리 실패: ${err.message}`);
    }
}
```

### 결론

- `throw new Error()`: 새로운 에러 상황을 정의하거나, 사용자 정의 에러 메시지가 필요할 때 사용
- `throw err`: 기존 에러를 그대로 전파하거나, 에러 정보를 보존해야 할 때 사용

적절한 상황에 맞는 방식을 선택하여 사용하는 것이 중요합니다. 에러 처리의 일관성과 디버깅 용이성을 고려하여 선택하세요.

## finally 블록

finally 블록은 try-catch 구문에서 선택적으로 사용할 수 있으며, 오류 발생 여부와 관계없이 항상 실행됩니다.

```javascript
function divideNumbers(a, b) {
    try {
        if (b === 0) {
            throw new Error('0으로 나눌 수 없습니다.');
        }
        return a / b;
    } catch (error) {
        console.log('에러 발생:', error.message);
        return null;
    } finally {
        console.log('계산 완료');
    }
}

console.log(divideNumbers(10, 2));  // 5
console.log(divideNumbers(10, 0));  // null
```

## 중첩된 try-catch

try-catch 블록은 중첩하여 사용할 수 있습니다. 이는 복잡한 에러 처리 시나리오에서 유용합니다.

### 기본 중첩 구조

```javascript
try {
    // 외부 try 블록
    try {
        // 내부 try 블록
        throw new Error('내부 에러');
    } catch (innerError) {
        console.log('내부 에러 처리:', innerError.message);
        throw new Error('외부로 전파되는 에러');
    }
} catch (outerError) {
    console.log('외부 에러 처리:', outerError.message);
}
```

### 실제 사용 예제

```javascript
async function processUserData(userId) {
    try {
        // 사용자 데이터 가져오기
        const userData = await fetchUserData(userId);
        
        try {
            // 사용자 데이터 처리
            const processedData = await processData(userData);
            return processedData;
        } catch (processingError) {
            console.log('데이터 처리 중 오류:', processingError.message);
            throw new Error('데이터 처리 실패');
        }
    } catch (fetchError) {
        console.log('데이터 가져오기 실패:', fetchError.message);
        throw new Error('사용자 데이터 처리 실패');
    }
}
```

## 실제 사용 사례

### 1. API 호출 처리

```javascript
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('데이터 가져오기 실패:', error);
        throw error;
    }
}
```

### 2. 파일 처리

```javascript
function readFile(filePath) {
    try {
        const content = fs.readFileSync(filePath, 'utf8');
        return content;
    } catch (error) {
        if (error.code === 'ENOENT') {
            console.log('파일을 찾을 수 없습니다.');
        } else {
            console.log('파일 읽기 오류:', error.message);
        }
        throw error;
    }
}
```

### 3. 데이터 유효성 검사

```javascript
function validateUserData(userData) {
    try {
        if (!userData.name) {
            throw new Error('이름이 필요합니다.');
        }
        
        try {
            if (userData.age < 0) {
                throw new Error('나이는 0보다 커야 합니다.');
            }
        } catch (ageError) {
            console.log('나이 검증 실패:', ageError.message);
            throw new Error('나이 데이터가 유효하지 않습니다.');
        }
        
        return true;
    } catch (error) {
        console.log('사용자 데이터 검증 실패:', error.message);
        return false;
    }
}
```

## 모범 사례

### 1. 구체적인 에러 처리

```javascript
try {
    // 코드 실행
} catch (error) {
    if (error instanceof TypeError) {
        // 타입 에러 처리
    } else if (error instanceof ReferenceError) {
        // 참조 에러 처리
    } else {
        // 기타 에러 처리
    }
}
```

### 2. 비동기 코드에서의 에러 처리

```javascript
async function asyncOperation() {
    try {
        const result = await someAsyncFunction();
        return result;
    } catch (error) {
        console.error('비동기 작업 실패:', error);
        throw error;
    }
}
```

### 3. 에러 로깅

```javascript
function logError(error, context) {
    console.error({
        timestamp: new Date().toISOString(),
        error: {
            name: error.name,
            message: error.message,
            stack: error.stack
        },
        context: context
    });
}

try {
    // 코드 실행
} catch (error) {
    logError(error, { operation: '데이터 처리' });
}
```

## 결론

try-catch는 JavaScript에서 예외 처리를 위한 강력한 도구입니다. 적절한 에러 처리는 애플리케이션의 안정성과 사용자 경험을 크게 향상시킬 수 있습니다. 구체적인 에러 처리, 적절한 로깅, 그리고 명확한 에러 메시지를 통해 더 나은 디버깅과 유지보수가 가능해집니다.

## 참고 자료
- MDN Web Docs: Error
- JavaScript.info: Error handling
- ECMAScript 2021 Specification

## JavaScript 심화 개념

JavaScript의 고급 개념들을 이해하면 더 효율적이고 견고한 코드를 작성할 수 있습니다.

### 1. 프로토타입과 상속

JavaScript는 프로토타입 기반의 객체지향 언어입니다.

```javascript
// 프로토타입 체인 예제
function Animal(name) {
    this.name = name;
}

Animal.prototype.speak = function() {
    console.log(`${this.name}이(가) 소리를 냅니다.`);
};

function Dog(name, breed) {
    Animal.call(this, name);
    this.breed = breed;
}

// 프로토타입 상속 설정
Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog;

// 메서드 오버라이딩
Dog.prototype.speak = function() {
    console.log(`${this.name}이(가) 멍멍!`);
};

const dog = new Dog('바둑이', '진돗개');
dog.speak(); // "바둑이이(가) 멍멍!"
```

### 2. 클로저(Closure)

클로저는 함수와 그 함수가 선언된 렉시컬 환경의 조합입니다.

```javascript
function createCounter() {
    let count = 0;  // private 변수
    
    return {
        increment() {
            count++;
            return count;
        },
        decrement() {
            count--;
            return count;
        },
        getCount() {
            return count;
        }
    };
}

const counter = createCounter();
console.log(counter.increment()); // 1
console.log(counter.increment()); // 2
console.log(counter.getCount());  // 2
```

### 3. Promise와 비동기 처리

Promise는 비동기 작업의 최종 완료(또는 실패)와 그 결과값을 나타냅니다.

```javascript
// Promise 체이닝
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(userData => {
            return processUserData(userData);
        })
        .catch(error => {
            console.error('Error:', error);
            throw error;
        });
}

// async/await 사용
async function getUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const userData = await response.json();
        return await processUserData(userData);
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}
```

### 4. 이벤트 루프와 비동기 실행

JavaScript의 이벤트 루프는 비동기 작업을 처리하는 핵심 메커니즘입니다.

```javascript
console.log('1. 시작');

setTimeout(() => {
    console.log('4. 타이머 완료');
}, 0);

Promise.resolve().then(() => {
    console.log('3. Promise 완료');
});

console.log('2. 끝');

// 출력 순서:
// 1. 시작
// 2. 끝
// 3. Promise 완료
// 4. 타이머 완료
```

### 5. 제너레이터와 이터레이터

제너레이터는 함수의 실행을 일시 중지하고 재개할 수 있는 특별한 함수입니다.

```javascript
function* numberGenerator() {
    yield 1;
    yield 2;
    yield 3;
}

const generator = numberGenerator();
console.log(generator.next().value); // 1
console.log(generator.next().value); // 2
console.log(generator.next().value); // 3
console.log(generator.next().done);  // true

// 무한 시퀀스 생성
function* infiniteSequence() {
    let i = 0;
    while (true) {
        yield i++;
    }
}

const infinite = infiniteSequence();
console.log(infinite.next().value); // 0
console.log(infinite.next().value); // 1
console.log(infinite.next().value); // 2
```

### 6. 프록시와 리플렉션

프록시는 객체의 기본 동작을 가로채고 재정의할 수 있는 객체입니다.

```javascript
const handler = {
    get(target, prop) {
        console.log(`속성 ${prop}에 접근`);
        return target[prop];
    },
    set(target, prop, value) {
        console.log(`속성 ${prop}을(를) ${value}로 설정`);
        target[prop] = value;
        return true;
    }
};

const person = new Proxy({}, handler);
person.name = 'John';  // "속성 name을(를) John으로 설정"
console.log(person.name);  // "속성 name에 접근" "John"
```

### 7. 모듈 시스템

ES6 모듈 시스템은 코드를 모듈화하고 재사용할 수 있게 해줍니다.

```javascript
// math.js
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export default class Calculator {
    multiply(a, b) {
        return a * b;
    }
}

// main.js
import Calculator, { add, subtract } from './math.js';

const calc = new Calculator();
console.log(add(5, 3));      // 8
console.log(subtract(5, 3)); // 2
console.log(calc.multiply(5, 3)); // 15
```

### 8. 메모리 관리와 가비지 컬렉션

JavaScript의 메모리 관리와 가비지 컬렉션에 대한 이해는 중요합니다.

```javascript
// 메모리 누수 예제
function createClosure() {
    const largeArray = new Array(1000000).fill('data');
    
    return function() {
        console.log(largeArray.length);
    };
}

// 올바른 메모리 관리
function createOptimizedClosure() {
    const largeArray = new Array(1000000).fill('data');
    
    return function() {
        console.log(largeArray.length);
        // 사용이 끝난 후 참조 제거
        largeArray.length = 0;
    };
}
```

### 9. 디자인 패턴

자주 사용되는 JavaScript 디자인 패턴들입니다.

```javascript
// 싱글톤 패턴
class Singleton {
    static instance;
    
    constructor() {
        if (Singleton.instance) {
            return Singleton.instance;
        }
        Singleton.instance = this;
    }
}

// 팩토리 패턴
class UserFactory {
    static createUser(type) {
        switch(type) {
            case 'admin':
                return new AdminUser();
            case 'regular':
                return new RegularUser();
            default:
                throw new Error('Invalid user type');
        }
    }
}

// 옵저버 패턴
class EventEmitter {
    constructor() {
        this.events = {};
    }
    
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }
    
    emit(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(callback => callback(data));
        }
    }
}
```

### 10. 성능 최적화

JavaScript 코드의 성능을 최적화하는 방법들입니다.

```javascript
// 메모이제이션
function memoize(fn) {
    const cache = new Map();
    
    return function(...args) {
        const key = JSON.stringify(args);
        if (cache.has(key)) {
            return cache.get(key);
        }
        
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
}

// 디바운싱
function debounce(func, wait) {
    let timeout;
    
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 쓰로틀링
function throttle(func, limit) {
    let inThrottle;
    
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
```

이러한 고급 개념들을 이해하고 적절히 활용하면 더 효율적이고 유지보수가 용이한 코드를 작성할 수 있습니다. 각 개념은 실제 프로젝트에서 자주 사용되며, JavaScript 개발자로서 반드시 알아야 하는 중요한 내용들입니다.
