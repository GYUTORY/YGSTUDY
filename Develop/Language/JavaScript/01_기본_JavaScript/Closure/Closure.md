---
title: JavaScript Closure (클로저)
tags: [language, javascript, 01기본javascript, closure, functional-programming]
updated: 2025-08-10
---

# JavaScript Closure (클로저)

## 배경

JavaScript의 Closure(클로저)는 함수가 자신이 선언된 환경(Lexical Scope)의 변수를 기억하고 접근할 수 있는 개념입니다. 함수가 실행된 이후에도 외부 함수의 변수에 접근할 수 있는 기능을 제공합니다.

### 클로저의 필요성
- **데이터 은닉**: 외부에서 직접 접근할 수 없는 private 변수 생성
- **상태 유지**: 함수 호출 간에 상태 정보 보존
- **함수형 프로그래밍**: 고차 함수와 콜백 함수 구현
- **모듈 패턴**: 캡슐화된 코드 구조 생성

### 기본 개념
- **렉시컬 스코프**: 함수가 선언된 위치에 따라 스코프가 결정되는 방식
- **스코프 체인**: 변수를 찾기 위해 거슬러 올라가는 경로
- **클로저**: 함수와 그 함수가 선언된 렉시컬 환경의 조합
- **메모리 관리**: 클로저로 인한 메모리 누수 방지

## 핵심

### 1. 클로저의 기본 원리

#### 클로저의 정의
```javascript
function outerFunction(outerVariable) {
    return function innerFunction(innerVariable) {
        console.log(`Outer: ${outerVariable}, Inner: ${innerVariable}`);
    };
}

const newFunction = outerFunction("Hello");
newFunction("World"); // Outer: Hello, Inner: World
```

#### 클로저의 동작 원리
```javascript
function createCounter() {
    let count = 0; // 외부 함수의 변수
    
    return function() {
        count++; // 내부 함수에서 외부 변수 접근
        return count;
    };
}

const counter1 = createCounter();
const counter2 = createCounter();

console.log(counter1()); // 1
console.log(counter1()); // 2
console.log(counter2()); // 1 (별도의 클로저)
console.log(counter1()); // 3
```

#### 렉시컬 스코프와 클로저
```javascript
let globalVariable = "Global";

function outer() {
    let outerVariable = "Outer";
    
    function inner() {
        let innerVariable = "Inner";
        
        function deepest() {
            console.log(globalVariable); // "Global"
            console.log(outerVariable);  // "Outer"
            console.log(innerVariable);  // "Inner"
        }
        
        return deepest;
    }
    
    return inner;
}

const innerFunc = outer();
const deepestFunc = innerFunc();
deepestFunc();
```

### 2. 클로저의 활용 사례

#### 데이터 은닉 (Encapsulation)
```javascript
function createBankAccount(initialBalance) {
    let balance = initialBalance; // private 변수
    
    return {
        deposit: function(amount) {
            if (amount > 0) {
                balance += amount;
                console.log(`입금: ${amount}, 잔액: ${balance}`);
            }
        },
        
        withdraw: function(amount) {
            if (amount > 0 && amount <= balance) {
                balance -= amount;
                console.log(`출금: ${amount}, 잔액: ${balance}`);
                return amount;
            } else {
                console.log('잔액 부족');
                return 0;
            }
        },
        
        getBalance: function() {
            return balance;
        }
    };
}

const account = createBankAccount(1000);
account.deposit(500);  // 입금: 500, 잔액: 1500
account.withdraw(200); // 출금: 200, 잔액: 1300
console.log(account.getBalance()); // 1300

// balance 변수에 직접 접근 불가
// console.log(account.balance); // undefined
```

#### 상태 유지
```javascript
function createTimer() {
    let startTime = Date.now();
    let isRunning = false;
    
    return {
        start: function() {
            if (!isRunning) {
                startTime = Date.now();
                isRunning = true;
                console.log('타이머 시작');
            }
        },
        
        stop: function() {
            if (isRunning) {
                isRunning = false;
                const elapsed = Date.now() - startTime;
                console.log(`경과 시간: ${elapsed}ms`);
                return elapsed;
            }
        },
        
        getStatus: function() {
            return {
                isRunning,
                elapsed: isRunning ? Date.now() - startTime : 0
            };
        }
    };
}

const timer = createTimer();
timer.start();
setTimeout(() => {
    timer.stop();
}, 1000);
```

#### 함수 팩토리
```javascript
function createMultiplier(factor) {
    return function(number) {
        return number * factor;
    };
}

const double = createMultiplier(2);
const triple = createMultiplier(3);
const quadruple = createMultiplier(4);

console.log(double(5));   // 10
console.log(triple(5));   // 15
console.log(quadruple(5)); // 20
```

### 3. 고급 클로저 패턴

#### 모듈 패턴
```javascript
const calculator = (function() {
    // private 변수들
    let history = [];
    let result = 0;
    
    // private 함수들
    function addToHistory(operation, value) {
        history.push({
            operation,
            value,
            timestamp: new Date()
        });
    }
    
    function validateNumber(num) {
        if (typeof num !== 'number' || isNaN(num)) {
            throw new Error('유효하지 않은 숫자입니다.');
        }
    }
    
    // public API
    return {
        add: function(num) {
            validateNumber(num);
            result += num;
            addToHistory('add', num);
            return this;
        },
        
        subtract: function(num) {
            validateNumber(num);
            result -= num;
            addToHistory('subtract', num);
            return this;
        },
        
        multiply: function(num) {
            validateNumber(num);
            result *= num;
            addToHistory('multiply', num);
            return this;
        },
        
        divide: function(num) {
            validateNumber(num);
            if (num === 0) {
                throw new Error('0으로 나눌 수 없습니다.');
            }
            result /= num;
            addToHistory('divide', num);
            return this;
        },
        
        getResult: function() {
            return result;
        },
        
        getHistory: function() {
            return [...history]; // 복사본 반환
        },
        
        clear: function() {
            result = 0;
            history = [];
            return this;
        }
    };
})();

// 사용 예시
try {
    calculator
        .add(10)
        .multiply(2)
        .subtract(5);
    
    console.log('결과:', calculator.getResult()); // 15
    console.log('히스토리:', calculator.getHistory());
} catch (error) {
    console.error('계산 오류:', error.message);
}
```

#### 이벤트 핸들러에서의 클로저
```javascript
function createButtonHandler(buttonId) {
    let clickCount = 0;
    
    return function(event) {
        clickCount++;
        console.log(`버튼 ${buttonId} 클릭 횟수: ${clickCount}`);
        
        // 클릭 횟수에 따른 다른 동작
        if (clickCount === 1) {
            console.log('첫 번째 클릭!');
        } else if (clickCount === 5) {
            console.log('5번째 클릭! 특별한 이벤트 발생!');
        }
        
        // 이벤트 객체도 사용 가능
        console.log('클릭 위치:', event.clientX, event.clientY);
    };
}

// 여러 버튼에 각각 다른 핸들러 할당
const button1Handler = createButtonHandler('btn1');
const button2Handler = createButtonHandler('btn2');

// 실제 DOM 이벤트에 연결하는 예시
// document.getElementById('button1').addEventListener('click', button1Handler);
// document.getElementById('button2').addEventListener('click', button2Handler);
```

## 예시

### 1. 실제 사용 사례

#### 캐시 시스템
```javascript
function createCache() {
    const cache = new Map();
    let hitCount = 0;
    let missCount = 0;
    
    return {
        get: function(key) {
            if (cache.has(key)) {
                hitCount++;
                console.log(`캐시 히트: ${key}`);
                return cache.get(key);
            } else {
                missCount++;
                console.log(`캐시 미스: ${key}`);
                return null;
            }
        },
        
        set: function(key, value) {
            cache.set(key, value);
            console.log(`캐시 저장: ${key}`);
        },
        
        clear: function() {
            cache.clear();
            console.log('캐시 초기화');
        },
        
        getStats: function() {
            return {
                size: cache.size,
                hitCount,
                missCount,
                hitRate: hitCount / (hitCount + missCount)
            };
        }
    };
}

const cache = createCache();

// 사용 예시
cache.set('user:1', { id: 1, name: 'Alice' });
cache.set('user:2', { id: 2, name: 'Bob' });

console.log(cache.get('user:1')); // 캐시 히트
console.log(cache.get('user:3')); // 캐시 미스
console.log(cache.getStats());
```

#### 설정 관리자
```javascript
function createConfigManager(defaultConfig) {
    let config = { ...defaultConfig };
    let changeListeners = [];
    
    return {
        get: function(key) {
            return config[key];
        },
        
        set: function(key, value) {
            const oldValue = config[key];
            config[key] = value;
            
            // 변경 리스너 호출
            changeListeners.forEach(listener => {
                listener(key, value, oldValue);
            });
        },
        
        getAll: function() {
            return { ...config };
        },
        
        reset: function() {
            config = { ...defaultConfig };
            changeListeners.forEach(listener => {
                listener('reset', config, null);
            });
        },
        
        onChange: function(listener) {
            changeListeners.push(listener);
        },
        
        removeListener: function(listener) {
            const index = changeListeners.indexOf(listener);
            if (index > -1) {
                changeListeners.splice(index, 1);
            }
        }
    };
}

const config = createConfigManager({
    theme: 'light',
    language: 'ko',
    notifications: true
});

// 설정 변경 리스너 등록
config.onChange((key, newValue, oldValue) => {
    console.log(`설정 변경: ${key} = ${newValue} (이전: ${oldValue})`);
});

config.set('theme', 'dark');
config.set('language', 'en');
```

### 2. 고급 패턴

#### 커링 (Currying)
```javascript
function curry(fn) {
    return function curried(...args) {
        if (args.length >= fn.length) {
            return fn.apply(this, args);
        } else {
            return function(...moreArgs) {
                return curried.apply(this, args.concat(moreArgs));
            };
        }
    };
}

// 사용 예시
function add(a, b, c) {
    return a + b + c;
}

const curriedAdd = curry(add);

console.log(curriedAdd(1)(2)(3));     // 6
console.log(curriedAdd(1, 2)(3));     // 6
console.log(curriedAdd(1)(2, 3));     // 6
console.log(curriedAdd(1, 2, 3));     // 6
```

#### 메모이제이션 (Memoization)
```javascript
function memoize(fn) {
    const cache = new Map();
    
    return function(...args) {
        const key = JSON.stringify(args);
        
        if (cache.has(key)) {
            console.log('캐시에서 반환');
            return cache.get(key);
        }
        
        console.log('계산 수행');
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
}

// 사용 예시
const expensiveCalculation = memoize(function(n) {
    console.log(`계산 중: ${n}`);
    return n * n;
});

console.log(expensiveCalculation(5)); // 계산 수행, 계산 중: 5, 25
console.log(expensiveCalculation(5)); // 캐시에서 반환, 25
console.log(expensiveCalculation(6)); // 계산 수행, 계산 중: 6, 36
```

## 운영 팁

### 성능 최적화

#### 메모리 누수 방지
```javascript
// 문제가 있는 코드: 메모리 누수 가능성
function createProblematicClosure() {
    const largeData = new Array(1000000).fill('data');
    
    return function() {
        console.log('클로저 실행');
        // largeData를 참조하지만 실제로는 사용하지 않음
    };
}

// 해결 방법 1: 필요 없는 클로저 해제
let closure = createProblematicClosure();
closure(); // 사용 후
closure = null; // 참조 해제

// 해결 방법 2: 필요한 데이터만 클로저에 포함
function createOptimizedClosure() {
    const smallData = '필요한 데이터만';
    
    return function() {
        console.log(smallData);
    };
}

// 해결 방법 3: WeakMap 사용 (가능한 경우)
const privateData = new WeakMap();

function createWeakMapClosure() {
    const obj = {};
    privateData.set(obj, 'private data');
    
    return function() {
        return privateData.get(obj);
    };
}
```

### 에러 처리

#### 클로저에서의 안전한 에러 처리
```javascript
function createSafeClosure() {
    let state = 'initial';
    let errorCount = 0;
    
    return {
        execute: function(operation) {
            try {
                if (errorCount > 3) {
                    throw new Error('너무 많은 오류가 발생했습니다.');
                }
                
                // 안전한 작업 수행
                const result = operation();
                state = 'success';
                return result;
                
            } catch (error) {
                errorCount++;
                state = 'error';
                console.error('클로저 실행 오류:', error.message);
                
                // 오류 복구 시도
                if (errorCount <= 3) {
                    console.log('오류 복구 시도 중...');
                    return null;
                } else {
                    throw error;
                }
            }
        },
        
        getState: function() {
            return { state, errorCount };
        },
        
        reset: function() {
            state = 'initial';
            errorCount = 0;
        }
    };
}

const safeClosure = createSafeClosure();

// 사용 예시
try {
    safeClosure.execute(() => {
        throw new Error('테스트 오류');
    });
} catch (error) {
    console.log('최종 오류:', error.message);
}

console.log('상태:', safeClosure.getState());
```

## 참고

### 클로저 vs 일반 함수 비교표

| 구분 | 클로저 | 일반 함수 |
|------|--------|-----------|
| **상태 유지** | 가능 | 불가능 |
| **데이터 은닉** | 가능 | 불가능 |
| **메모리 사용량** | 높음 | 낮음 |
| **성능** | 약간 느림 | 빠름 |
| **복잡성** | 높음 | 낮음 |

### 클로저 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **데이터 은닉 필요** | 클로저 사용 | 캡슐화 구현 |
| **상태 유지 필요** | 클로저 사용 | 함수 간 상태 공유 |
| **모듈 패턴** | 클로저 사용 | private 변수 구현 |
| **단순한 계산** | 일반 함수 | 성능 최적화 |
| **메모리 제약** | 일반 함수 | 메모리 효율성 |

### 결론
클로저는 JavaScript의 강력한 기능으로 데이터 은닉과 상태 유지를 가능하게 합니다.
렉시컬 스코프를 기반으로 외부 변수에 접근할 수 있습니다.
모듈 패턴과 함수형 프로그래밍에서 핵심적인 역할을 합니다.
메모리 누수를 방지하기 위해 적절한 참조 해제가 필요합니다.
성능과 복잡성을 고려하여 적절한 상황에서 사용하세요.
클로저를 활용하여 안전하고 유지보수하기 쉬운 코드를 작성하세요.

