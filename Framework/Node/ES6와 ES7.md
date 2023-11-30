
## ES6와 ES7의 주요 차이점
###  변수 선언 키워드
- ES6에서는 var, let, const의 세 가지 변수 선언 키워드가 추가되었다.
- var는 기존의 변수 선언 키워드로, 함수 스코프에서 선언된 변수의 값을 변경할 수 있다. 
- let은 함수 스코프에서 선언된 변수의 값을 변경할 수 있지만, 블록 스코프에서 선언된 변수의 값을 변경할 수 없다.
- const는 상수를 선언하는 키워드로, 값을 변경할 수 없다.


```javascript
// ES6

var a = 1; // 함수 스코프에서 선언된 변수로, 값을 변경할 수 있다.
let b = 2; // 함수 스코프에서 선언된 변수로, 값을 변경할 수 있지만, 블록 스코프에서 선언된 변수의 값을 변경할 수 없다.
const c = 3; // 상수로 선언된 변수로, 값을 변경할 수 없다.

// ES7

a = 2; // var로 선언된 변수의 값을 변경할 수 있다.
b = 4; // let으로 선언된 변수의 값을 변경할 수 있다.
c = 5; // const로 선언된 변수의 값을 변경할 수 없다.
```


### 화살표 함수
- ES6에서는 화살표 함수가 도입되었다. 
- 화살표 함수는 기존의 함수 선언 방식과 달리 this 바인딩을 제어할 수 있으며, 함수 표현식과 동일하게 사용할 수 있다.

```javascript
// ES6

const f = (x) => x * 2; // 화살표 함수로 선언된 함수
const g = function(x) { return x * 2; }; // 기존의 함수 선언 방식으로 선언된 함수

console.log(f(2)); // 4
console.log(g(2)); // 4
```

### Promise
- ES6에서는 Promise 객체가 도입되었다.
- Promise 객체는 비동기 작업의 결과를 비동기적으로 처리할 수 있도록 도와주는 객체이다.


```javascript
// ES6

const p = new Promise((resolve, reject) => {
  setTimeout(() => {
    resolve("완료되었습니다.");
  }, 1000);
});

p.then((result) => {
  console.log(result); // "완료되었습니다."
});
```

### Async/Await
- ES7에서는 Async/Await 구문이 도입되었다. Async/Await 구문은 Promise 객체를 사용하여 비동기 작업을 처리할 수 있는 간결한 구문을 제공한다.


```javascript
// ES7 

async function f() {
  const result = await new Promise((resolve, reject) => {
    setTimeout(() => {
      resolve("완료되었습니다.");
    }, 1000);
  });

  console.log(result); // "완료되었습니다."
}

f();
```

> await를 사용하면 비동기 작업이 완료될 때까지 함수 실행을 중단하므로, 마치 동기적으로 실행되는 것처럼 보이게 할 수 있습니다.