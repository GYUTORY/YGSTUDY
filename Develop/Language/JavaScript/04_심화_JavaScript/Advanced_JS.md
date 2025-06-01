
# JavaScript 심화 개념 정리

## 1. 호이스팅 (Hoisting)

### 개념
- 자바스크립트 엔진이 코드를 실행하기 전에 **변수 선언**과 **함수 선언**을 스코프의 최상단으로 끌어올리는 동작.
- 변수의 초기화는 호이스팅되지 않고, 선언만 호이스팅됨.

### 예제
```javascript
console.log(x); // undefined
var x = 5;
console.log(x); // 5
```

- 위 코드는 내부적으로 다음과 같이 동작:
```javascript
var x;
console.log(x); // undefined
x = 5;
console.log(x); // 5
```

---

## 2. 이벤트 루프와 콜 스택 (Event Loop and Call Stack)

### 개념
- **콜 스택(Call Stack)**: 실행 중인 함수가 쌓이는 자료 구조. LIFO(Last In, First Out) 방식.
- **이벤트 루프(Event Loop)**: 콜 스택이 비워지면, 태스크 큐(Task Queue)에 대기 중인 비동기 작업을 실행.

### 예제
```javascript
console.log('Start');

setTimeout(() => {
    console.log('Timeout');
}, 0);

console.log('End');
```

### 실행 순서
1. `console.log('Start')` 실행 → 콜 스택에서 제거.
2. `setTimeout` 실행 → 비동기 함수이므로 태스크 큐로 이동.
3. `console.log('End')` 실행 → 콜 스택에서 제거.
4. 콜 스택이 비어지면 태스크 큐의 `setTimeout` 콜백 함수 실행.

---

## 3. 객체지향 프로그래밍: 클래스와 상속

### 클래스 정의
```javascript
class Animal {
    constructor(name) {
        this.name = name;
    }

    speak() {
        console.log(`${this.name}이(가) 소리를 냅니다.`);
    }
}
```

### 클래스 상속
```javascript
class Dog extends Animal {
    speak() {
        console.log(`${this.name}이(가) 멍멍 짖습니다.`);
    }
}

const dog = new Dog('강아지');
dog.speak(); // 강아지가 멍멍 짖습니다.
```

---

## 4. 함수형 프로그래밍 기본: 고차 함수와 순수 함수

### 고차 함수 (Higher-order Function)
- 다른 함수를 **매개변수로 받거나 반환**하는 함수.

```javascript
function higherOrderFunction(callback) {
    console.log('고차 함수 실행');
    callback();
}

higherOrderFunction(() => {
    console.log('콜백 함수 실행');
});
```

### 순수 함수 (Pure Function)
- 동일한 입력에 대해 항상 **동일한 출력**을 반환하며, **부작용이 없음**.

```javascript
function pureFunction(a, b) {
    return a + b;
}

console.log(pureFunction(2, 3)); // 5
console.log(pureFunction(2, 3)); // 5 (항상 동일한 출력)
```

---
