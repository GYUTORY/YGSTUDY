
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


---

## Arrow Function과 exports의 문제 

```javascript
const person = {
    name: "Alice",
    greet: () => {
        console.log(`Hello, my name is ${this.name}`);
    }
};

exports.name = "James";

person.greet();  // "Hello, my name is James"
```

- 코드에 exports.name = "James";를 추가하면, greet 메서드에서 출력되는 this.name 값이 "James"로 바뀌게 됩니다. 
- 그 이유는 화살표 함수 greet에서 this가 글로벌 스코프(또는 Node.js 환경에서는 module.exports)를 참조하기 때문입니다.


## 이유 설명
- 화살표 함수는 this를 새롭게 바인딩하지 않고, 상위 스코프의 this를 사용합니다.
- Node.js 환경에서는 모듈 전체가 module.exports라는 객체에 속하게 됩니다.
- 따라서 exports.name = "James";로 설정하면 module.exports.name이 "James"가 되고, greet 메서드에서 this.name은 module.exports.name을 참조해 "James"를 출력하게 됩니다.

### 정리
- 일반 함수는 호출된 객체에 따라 this가 바뀌지만, 화살표 함수는 상위 스코프의 this를 그대로 사용합니다.
- 이 경우, this는 module.exports를 가리켜 name의 값이 "James"로 출력됩니다.

---

# 그러면 Arrow Function은 항상, exports만 호출이 가능한가?
- 정답부터 말하자면 아니다, 화살표 함수는 선언된 위치의 상위 스코프에 따라 this가 결정되기 때문에, 그 상위 스코프가 무엇이냐에 따라 this가 달라질 수 있습니다.


## 예시로 살펴보기
- exports가 아닌 다른 환경에서도 this가 달라질 수 있는 예시를 통해 좀 더 구체적으로 설명해볼게요.

### 1. 객체 내부에서 사용되는 경우
- 화살표 함수가 객체 메서드로 선언되면, 객체의 상위 스코프에 있는 this를 참조하게 됩니다. 
- 예를 들어, 전역 컨텍스트에서 객체 내부에 선언된 화살표 함수는 전역 스코프의 this를 참조합니다.

```javascript
const person = {
    name: "Alice",
    greet: () => {
        console.log(`Hello, my name is ${this.name}`);
    }
};

global.name = "Global Name";  // Node.js에서는 글로벌 스코프에 `name`을 설정
person.greet();  // "Hello, my name is Global Name"
```

- 위 코드에서 greet의 this는 person이 아니라 전역 객체(Node.js에서는 global, 브라우저에서는 window)를 참조하게 되어, global.name의 값 "Global Name"이 출력됩니다.


### 2. 함수 내부에서 사용하는 경우
- 함수 내부에 화살표 함수를 선언하면, 화살표 함수는 그 **상위 함수의 this**를 사용하게 됩니다.

```javascript
function Person(name) {
    this.name = name;
    this.greet = () => {
        console.log(`Hello, my name is ${this.name}`);
    };
}

const alice = new Person("Alice");
alice.greet();  // "Hello, my name is Alice"
```

- 여기서 greet은 Person 생성자 함수 내부에 선언된 화살표 함수이므로, **상위 스코프인 Person 함수의 this**를 사용합니다. 
- 생성된 alice 객체에서 this.name은 "Alice"로 설정되었으므로, "Hello, my name is Alice"가 출력됩니다.

## 요약
> 화살표 함수는 exports뿐만 아니라 선언된 위치의 상위 스코프에 따라 this가 결정됩니다. 따라서, 어디에서 선언되었느냐에 따라 this는 전역 객체나 함수의 this로도 설정될 수 있습니다.












