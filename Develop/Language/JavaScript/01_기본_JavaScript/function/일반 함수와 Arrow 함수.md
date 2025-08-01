# JavaScript의 함수 정의 방식: 일반 함수 vs 화살표 함수

## 1. 함수 정의 방식의 차이

### 1.1 일반 함수 (Function Declaration/Expression)
```javascript
// 함수 선언식 (Function Declaration)
function main() {
	return 'function';
}

// 함수 표현식 (Function Expression)
const main = function() {
	return 'function';
};
```

### 1.2 화살표 함수 (Arrow Function)
```javascript
// 기본 화살표 함수
const main = () => {
	return 'function';
};

// 단일 표현식의 경우 return과 중괄호 생략 가능
const main = () => 'function';

// 매개변수가 하나인 경우 괄호 생략 가능
const square = x => x * x;

// 매개변수가 없는 경우 괄호 필수
const sayHello = () => 'Hello!';
```

## 2. 주요 차이점

### 2.1 this 바인딩
가장 중요한 차이점은 `this` 키워드의 동작 방식입니다.

#### 일반 함수의 this
- 일반 함수에서 `this`는 함수가 호출되는 방식에 따라 동적으로 결정됩니다.
- 함수를 호출한 객체를 가리키며, 호출 방식에 따라 달라질 수 있습니다.

```javascript
const person = {
	name: "Alice",
	greet: function() {
		console.log(`Hello, my name is ${this.name}`);
	}
};

person.greet();  // "Hello, my name is Alice"

const greet = person.greet;
greet();  // "Hello, my name is undefined" (전역 객체의 name)
```

#### 화살표 함수의 this
- 화살표 함수는 자신만의 `this`를 가지지 않고, 상위 스코프의 `this`를 그대로 사용합니다.
- 이를 "렉시컬 this"라고도 합니다.

```javascript
const person = {
	name: "Alice",
	greet: () => {
		console.log(`Hello, my name is ${this.name}`);
	}
};

person.greet();  // "Hello, my name is undefined"
```

### 2.2 arguments 객체
- 일반 함수는 자체적으로 `arguments` 객체를 가집니다.
- 화살표 함수는 `arguments` 객체를 가지지 않습니다.

```javascript
// 일반 함수
function regular() {
	console.log(arguments);
}
regular(1, 2, 3);  // Arguments(3) [1, 2, 3]

// 화살표 함수
const arrow = () => {
	console.log(arguments);
}
arrow(1, 2, 3);  // ReferenceError: arguments is not defined
```

### 2.3 생성자 함수
- 일반 함수는 `new` 키워드로 생성자 함수로 사용할 수 있습니다.
- 화살표 함수는 생성자 함수로 사용할 수 없습니다.

```javascript
// 일반 함수는 생성자로 사용 가능
function Person(name) {
	this.name = name;
}
const person = new Person('Alice');

// 화살표 함수는 생성자로 사용 불가
const Person = (name) => {
	this.name = name;
}
const person = new Person('Alice');  // TypeError: Person is not a constructor
```

## 3. 실제 사용 사례

### 3.1 이벤트 핸들러
```javascript
class Button {
	constructor() {
		this.clicks = 0;
		this.button = document.querySelector('button');
		
		// 일반 함수: this가 이벤트 타겟을 가리킴
		this.button.addEventListener('click', function() {
			this.clicks++;  // this는 button 요소
		});
		
		// 화살표 함수: this가 Button 인스턴스를 가리킴
		this.button.addEventListener('click', () => {
			this.clicks++;  // this는 Button 인스턴스
		});
	}
}
```

### 3.2 콜백 함수
```javascript
class Timer {
	constructor() {
		this.seconds = 0;
	}
	
	start() {
		// 일반 함수: this가 undefined
		setInterval(function() {
			this.seconds++;
		}, 1000);
		
		// 화살표 함수: this가 Timer 인스턴스
		setInterval(() => {
			this.seconds++;
		}, 1000);
	}
}
```

### 3.3 메서드 축약
```javascript
const obj = {
	// 일반 함수 메서드
	method: function() {
		return this;
	},
	
	// 화살표 함수 메서드
	arrowMethod: () => {
		return this;
	}
};
```

## 4. 모범 사례와 주의사항

### 4.1 화살표 함수 사용이 적절한 경우
- 콜백 함수
- 이벤트 핸들러
- 클래스 메서드
- `this` 바인딩이 필요한 경우

### 4.2 일반 함수 사용이 적절한 경우
- 생성자 함수
- 메서드 정의
- `arguments` 객체가 필요한 경우
- `this`가 동적으로 바인딩되어야 하는 경우

### 4.3 주의사항
```javascript
// 잘못된 사용 예시
const person = {
	name: "Alice",
	greet: () => {
		console.log(`Hello, my name is ${this.name}`);
	}
};

// 올바른 사용 예시
const person = {
	name: "Alice",
	greet() {
		console.log(`Hello, my name is ${this.name}`);
	}
};
```

## 5. 결론
- 일반 함수와 화살표 함수는 각각의 용도에 맞게 사용해야 합니다.
- `this` 바인딩이 중요한 경우 화살표 함수를 사용하세요.
- 생성자 함수나 메서드 정의에는 일반 함수를 사용하세요.
- 코드의 가독성과 유지보수성을 고려하여 적절한 함수 타입을 선택하세요.

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
- 이는 특히 클래스나 생성자 함수에서 매우 유용한 특성입니다.

#### 2.1 생성자 함수 내부에서의 화살표 함수
```javascript
function Person(name) {
	this.name = name;
	
	// 일반 함수로 메서드 정의
	this.sayHello = function() {
		console.log(`Hello, my name is ${this.name}`);
	};
	
	// 화살표 함수로 메서드 정의
	this.sayHelloArrow = () => {
		console.log(`Hello, my name is ${this.name}`);
	};
}

const alice = new Person("Alice");

// 일반 함수 메서드 호출
alice.sayHello();  // "Hello, my name is Alice"

// 화살표 함수 메서드 호출
alice.sayHelloArrow();  // "Hello, my name is Alice"

// this 바인딩이 다른 경우
const greet = alice.sayHello;
const greetArrow = alice.sayHelloArrow;

greet();  // "Hello, my name is undefined"
greetArrow();  // "Hello, my name is Alice"
```

- 위 예제에서 중요한 차이점을 볼 수 있습니다:
  1. 일반 함수(`sayHello`)는 호출 방식에 따라 `this`가 달라집니다.
  2. 화살표 함수(`sayHelloArrow`)는 생성자 함수의 `this`를 그대로 유지합니다.
  3. 메서드를 변수에 할당하여 호출할 때, 일반 함수는 `this`를 잃어버리지만 화살표 함수는 `this`를 유지합니다.

#### 2.2 이벤트 핸들러에서의 화살표 함수
```javascript
class Button {
	constructor() {
		this.clicks = 0;
		
		// 일반 함수로 이벤트 핸들러 정의
		this.handleClick = function() {
			this.clicks++;
			console.log(`Clicked ${this.clicks} times`);
		};
		
		// 화살표 함수로 이벤트 핸들러 정의
		this.handleClickArrow = () => {
			this.clicks++;
			console.log(`Clicked ${this.clicks} times`);
		};
	}
}

const button = new Button();

// 이벤트 핸들러로 사용할 때
document.addEventListener('click', button.handleClick);  // this가 document를 가리킴
document.addEventListener('click', button.handleClickArrow);  // this가 Button 인스턴스를 가리킴
```

- 이벤트 핸들러에서도 비슷한 차이가 발생합니다:
  1. 일반 함수는 이벤트가 발생한 요소를 `this`로 가리킵니다.
  2. 화살표 함수는 클래스의 `this`를 유지합니다.

#### 2.3 콜백 함수에서의 화살표 함수
```javascript
class Counter {
	constructor() {
		this.count = 0;
	}
	
	startCounting() {
		// 일반 함수를 콜백으로 사용
		setInterval(function() {
			this.count++;
			console.log(this.count);
		}, 1000);  // this가 undefined 또는 window를 가리킴
		
		// 화살표 함수를 콜백으로 사용
		setInterval(() => {
			this.count++;
			console.log(this.count);
		}, 1000);  // this가 Counter 인스턴스를 가리킴
	}
}
```

- 콜백 함수에서도 화살표 함수의 `this` 바인딩이 유용합니다:
  1. 일반 함수는 콜백으로 사용될 때 `this` 컨텍스트를 잃어버립니다.
  2. 화살표 함수는 상위 스코프의 `this`를 유지합니다.

## 요약
> 화살표 함수는 함수 내부에서 사용될 때, 상위 함수의 this를 그대로 사용하는 특성이 있습니다. 이는 특히 클래스나 생성자 함수에서 메서드를 정의할 때, 이벤트 핸들러를 작성할 때, 그리고 콜백 함수를 사용할 때 매우 유용합니다. 일반 함수와 달리 this가 고정되어 있어 예측 가능한 동작을 보장할 수 있습니다.












