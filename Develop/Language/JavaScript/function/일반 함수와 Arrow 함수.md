
### 자바스크립트(ES6)에서 함수를 정의하는 방법은 크게 두가지로 나뉜다.
- 일반함수와 화살표 함수 이다.

```javascript
function main() { // 일반 함수
	return 'function';
};

const main = () => 'function'; // 화살표 함수
```

---

# this!
- 일반함수와 화살표함수의 가장 큰 차이는 this이다.

## 일반 Function의 this
- 일반 함수에서 this는 함수를 호출한 객체를 가리킵니다.
- 즉, 함수를 호출하는 방법에 따라 this가 동적으로 바인딩됩니다.
- 예를 들어, 메서드로 호출할 때는 그 메서드의 호출자가 this가 되고, 단독 호출일 경우 this는 전역 객체(window 또는 global)를 가리킵니다.
- 또한 call, apply, bind 메서드를 사용하여 this를 명시적으로 설정할 수도 있습니다.

```javascript
const person = {
    name: "Alice",
    greet: function() {
        console.log(`Hello, my name is ${this.name}`);
    }
};

person.greet();  // "Hello, my name is Alice"
```

> 위의 코드에서 greet 함수는 person 객체의 메서드로 호출되었기 때문에, this는 person 객체를 가리킵니다.

<br>
<br>

## Arrow Function의 this
- 일반 함수와 다르게, 화살표 함수는 새로운 this를 가지지 않고, 화살표 함수가 선언된 위치에서 화살표 함수가 정의된 렉시컬 환경(상위 스코프)의 this를 상속합니다.
- 즉, 화살표 함수 내부에서 this는 화살표 함수가 선언된 위치의 this를 가리킵니다. 화살표 함수는 call, apply, bind로 this를 변경할 수 없으며, this가 고정되어 있습니다.
- 
```javascript
const person = {
    name: "Alice",
    greet: () => {
        console.log(`Hello, my name is ${this.name}`);
    }
};

person.greet();  // "Hello, my name is undefined"
```

- regularFunction에서는 this가 exampleObj를 가리키지만, arrowFunction에서는 this가 상위 스코프의 this를 그대로 사용합니다.
> 즉, 화살표 함수는 함수가 선언된 당시의 this를 기억하고 그대로 사용하기 때문에, 함수 안에서 this가 변하지 않아요.





