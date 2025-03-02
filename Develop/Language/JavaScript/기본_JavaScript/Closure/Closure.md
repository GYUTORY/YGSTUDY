

# 🚀 JavaScript Closure (클로저)

## 1️⃣ Closure란?
**Closure(클로저)**는 **함수가 자신이 선언된 환경(Lexical Scope)의 변수를 기억하고 접근할 수 있는 개념**입니다.  
즉, 함수가 실행된 이후에도 **외부 함수의 변수에 접근할 수 있는 기능**을 의미합니다.

> **👉🏻 클로저는 JavaScript에서 함수형 프로그래밍과 데이터 은닉(Encapsulation)에 자주 사용됩니다.**

---

## 2️⃣ Closure의 기본 원리

### ✅ 클로저의 핵심 개념
1. **함수 안에서 다른 함수를 정의하고, 내부 함수가 외부 함수의 변수를 참조하는 구조**
2. **외부 함수가 실행을 마쳐도, 내부 함수에서 해당 변수를 계속 참조 가능**
3. **Lexical Scope(렉시컬 스코프, 정적 스코프)를 기반으로 동작**

### ✨ 기본적인 Closure 예제
```javascript
function outerFunction(outerVariable) {
    return function innerFunction(innerVariable) {
        console.log(`Outer: ${outerVariable}, Inner: ${innerVariable}`);
    };
}

const newFunction = outerFunction("Hello");
newFunction("World"); // Outer: Hello, Inner: World
```

> **👉🏻 `newFunction`은 `outerFunction`이 종료된 후에도 `outerVariable`에 접근할 수 있습니다.**

---

## 3️⃣ Closure의 활용 사례

### ✅ 1. 데이터 은닉 (Encapsulation)
- 클로저를 사용하면 **외부에서 직접 접근할 수 없는 private 변수**를 만들 수 있음

#### ✨ 예제: private 변수 만들기
```javascript
function counter() {
    let count = 0; // private 변수

    return {
        increment: function () {
            count++;
            console.log(`Count: ${count}`);
        },
        decrement: function () {
            count--;
            console.log(`Count: ${count}`);
        },
        getCount: function () {
            return count;
        }
    };
}

const myCounter = counter();
myCounter.increment(); // Count: 1
myCounter.increment(); // Count: 2
console.log(myCounter.getCount()); // 2
myCounter.decrement(); // Count: 1
```

> **👉🏻 `count` 변수는 `counter()` 함수 내부에서만 접근 가능하며, 직접 변경할 수 없습니다.**

---

### ✅ 2. setTimeout과 클로저

#### ✨ 예제: setTimeout에서 클로저 사용
```javascript
function delayMessage(message, delay) {
    setTimeout(function () {
        console.log(message);
    }, delay);
}

delayMessage("클로저 예제입니다!", 2000); // 2초 후 출력
```

> **👉🏻 `setTimeout()` 내부의 함수가 `message` 변수를 기억하고 있다가 나중에 실행됩니다.**

---

### ✅ 3. 반복문과 클로저 문제 해결

#### ❌ 잘못된 예제: var를 사용할 경우 문제 발생
```javascript
for (var i = 1; i <= 3; i++) {
    setTimeout(function () {
        console.log(i); // 4, 4, 4 출력됨 (의도한 결과가 아님)
    }, i * 1000);
}
```

#### ✅ 올바른 해결 방법: let 또는 클로저 사용
```javascript
for (let i = 1; i <= 3; i++) {
    setTimeout(function () {
        console.log(i); // 1, 2, 3 순서대로 출력됨
    }, i * 1000);
}
```

> **👉🏻 `let`을 사용하면 블록 스코프가 적용되어 원하는 결과가 출력됩니다.**

또는 클로저를 활용하여 해결할 수도 있습니다.

```javascript
for (var i = 1; i <= 3; i++) {
    (function (num) {
        setTimeout(function () {
            console.log(num);
        }, num * 1000);
    })(i);
}
```

> **👉🏻 즉시 실행 함수(IIFE)를 사용하면 `num`이 클로저로 유지됩니다.**

---

## 4️⃣ Closure를 사용할 때 주의할 점

### ✅ 1. 메모리 누수 (Memory Leak)
클로저는 **외부 함수의 변수를 계속 참조**하므로, 필요 없는 클로저가 많아지면 **메모리 누수가 발생할 수 있음**

#### 해결 방법
- 필요 없는 클로저는 `null`을 할당하여 참조 해제
```javascript
let myClosure = (function () {
    let count = 0;
    return function () {
        return ++count;
    };
})();

console.log(myClosure()); // 1
console.log(myClosure()); // 2

myClosure = null; // 메모리 해제
```

### ✅ 2. 성능 문제
- 클로저를 과도하게 사용하면 **메모리를 계속 유지**해야 하므로 성능 저하 발생 가능
- 너무 많은 클로저를 생성하는 것은 피하는 것이 좋음

---

## 5️⃣ 정리: Closure의 장점과 단점

| 장점 | 단점 |
|------|------|
| 데이터 은닉 가능 | 메모리 누수 위험 |
| 함수형 프로그래밍에 유용 | 과도한 사용 시 성능 저하 |
| 비동기 작업에서 변수 유지 | 디버깅이 어려울 수 있음 |

> **👉🏻 클로저는 강력한 기능이지만, 올바르게 사용하지 않으면 성능 문제를 일으킬 수 있습니다!**
