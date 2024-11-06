

# 클로저의 정의
- 클로저는 내부 함수가 외부 함수의 스코프(변수)에 접근할 수 있는 기능을 제공합니다. 
- 즉, 내부 함수가 외부 함수의 변수를 기억하고 사용할 수 있게 되는 것입니다. 
- 이 과정에서 외부 함수의 실행이 끝난 후에도 내부 함수는 외부 함수의 변수에 접근할 수 있습니다.

# 클로저의 구조
- 클로저는 일반적으로 다음과 같은 구조로 이루어집니다:

```javascript
function outerFunction() {
    let outerVariable = 'I am from outer function';

    function innerFunction() {
        console.log(outerVariable); // 외부 변수에 접근
    }

    return innerFunction; // innerFunction을 반환
}

const closure = outerFunction(); // outerFunction 실행
closure(); // innerFunction 호출
```

- 위 예제에서 outerFunction이 실행되면 innerFunction을 반환합니다.
- 그리고 closure 변수에 저장된 innerFunction을 호출하면, outerVariable에 접근할 수 있게 됩니다.
- 이는 innerFunction이 자신의 스코프에 outerFunction의 렉시컬 환경을 기억하고 있기 때문입니다.


---

## 클로저의 주요 사용 사례


### 1. 상태 유지 클로저
- 함수의 실행 컨텍스트가 사라지더라도 그 안의 변수를 유지할 수 있게 해줍니다. 
- 예를 들어, 카운터를 구현할 때 클로저를 사용하면 각 카운터의 상태를 유지할 수 있습니다.

```javascript
function createCounter() {
    let count = 0;

    return {
        increment: function() {
            count++;
            return count;
        },
        decrement: function() {
            count--;
            return count;
        },
        getCount: function() {
            return count;
        }
    };
}

const counter = createCounter();
console.log(counter.increment()); // 1
console.log(counter.increment()); // 2
console.log(counter.getCount()); // 2
console.log(counter.decrement()); // 1
```

### 2. 데이터 은닉 클로저 
- 객체의 내부 상태를 은닉할 수 있습니다.
- 외부에서 직접 접근할 수 없게 하여, 데이터의 무결성을 유지할 수 있습니다.

```javascript
function createUser(name) {
    let userName = name; // 은닉된 변수

    return {
        getName: function() {
            return userName;
        },
        setName: function(newName) {
            userName = newName;
        }
    };
}

const user = createUser('Alice');
console.log(user.getName()); // Alice
user.setName('Bob');
console.log(user.getName()); // Bob
```

### 3. 비동기 프로그래밍 클로저
- 비동기 작업에서도 유용하게 사용됩니다.
- 예를 들어, setTimeout과 함께 사용할 때, 클로저를 통해 외부 변수를 기억할 수 있습니다.

```javascript
function delayedMessage(message) {
    setTimeout(function() {
        console.log(message);
    }, 1000);
}

delayedMessage('Hello after 1 second!'); // 1초 후 "Hello after 1 second!" 출력
```

--- 

# 클로저의 장단점

## 장점

### 1. 상태 유지
- 클로저를 사용하면 함수가 종료된 후에도 변수를 기억할 수 있어, 상태를 유지할 수 있습니다.
### 2. 은닉
- 외부에서 직접 접근할 수 없는 변수를 만들 수 있어, 데이터 은닉을 구현할 수 있습니다.
### 3. 모듈화
- 코드의 재사용성을 높이고, 깔끔한 모듈 구조를 유지할 수 있습니다.

## 단점
### 1. 메모리 사용
- 클로저는 외부 변수를 기억하므로, 필요한 경우에도 메모리 사용이 증가할 수 있습니다. 
- 너무 많은 클로저를 생성하면 메모리 누수(leak)가 발생할 수 있습니다.

### 2. 디버깅
- 클로저는 함수가 여러 번 중첩되어 생성될 수 있기 때문에, 디버깅이 어려워질 수 있습니다.
- 스코프가 복잡해져 추적이 힘들 수 있습니다.

## 결론
- 클로저는 자바스크립트의 강력한 기능 중 하나로, 상태 관리, 데이터 은닉, 비동기 프로그래밍에서 매우 유용하게 사용됩니다. 
- 클로저를 잘 활용하면 코드의 유연성과 재사용성을 높일 수 있습니다.

