
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
- 화살표 함수는 일반 함수와 달리 새로운 this를 생성하지 않습니다.
- 즉, 화살표 함수 내부의 this는 화살표 함수가 선언된 **상위 스코프의 this**를 그대로 사용합니다.
- 따라서, 화살표 함수는 this가 고정되어 있으며, call, apply, bind 메서드로도 this를 변경할 수 없습니다.

```javascript
const person = {
    name: "Alice",
    greet: () => {
        console.log(`Hello, my name is ${this.name}`);
    }
};

person.greet();  // "Hello, my name is undefined"
```

- 위 코드에서 greet 메서드는 화살표 함수로 작성되었습니다.
- 화살표 함수는 this를 person 객체가 아닌 **상위 스코프(글로벌 스코프)의 this**를 참조하기 때문에, this.name은 undefined가 됩니다.
- 일반 함수로 작성된 메서드라면 this가 person 객체를 가리키겠지만, 화살표 함수에서는 그렇지 않습니다.

> 즉, 화살표 함수는 함수가 선언된 당시의 this를 기억하고 그대로 사용하기 때문에, 함수 안에서 this가 변하지 않아요.





