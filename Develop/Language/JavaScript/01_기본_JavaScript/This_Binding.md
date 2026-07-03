---
title: JavaScript this 바인딩
tags:
  - JavaScript
  - this
  - Binding
  - Arrow Function
  - call
  - apply
  - bind
updated: 2026-04-20
---

# JavaScript this 바인딩

자바스크립트의 `this`만큼 초심자를 괴롭히는 개념도 드물다. 다른 언어에서 `this`는 보통 "현재 인스턴스"를 가리키는 고정된 키워드지만, 자바스크립트에서는 함수를 어떻게 호출했느냐에 따라 `this`가 달라진다. 선언 시점이 아니라 호출 시점에 결정된다는 점이 헷갈림의 근원이다. Node.js 백엔드 코드에서도 이벤트 핸들러나 콜백을 넘길 때 `this`가 예상과 다르게 잡혀서 런타임에 `Cannot read properties of undefined` 같은 오류가 터진다. React나 Vue 같은 프론트엔드 프레임워크에서도 클래스 컴포넌트나 Options API를 쓰면 비슷한 문제가 반복된다.

이 문서는 `this` 바인딩의 네 가지 규칙, `call`/`apply`/`bind`의 실제 차이, 화살표 함수에서 `this`가 왜 다르게 동작하는지, 그리고 클래스 메서드에서 `this`를 잃어버리는 전형적인 상황을 정리한다. 이론을 외우는 것보다 호출 지점에서 어떤 규칙이 적용되는지 읽어내는 감각이 중요하다.

## this는 언제 결정되는가

자바스크립트에서 `this`는 함수가 정의된 위치가 아니라 **호출된 방식**에 따라 결정된다. 똑같은 함수라도 어떤 객체의 메서드로 호출했는지, 독립적으로 호출했는지, `new`와 함께 호출했는지, `call`/`apply`로 바인딩을 강제했는지에 따라 값이 바뀐다. 함수 선언부를 아무리 들여다봐도 `this`가 무엇인지 알 수 없다는 뜻이다. 호출 지점까지 가봐야 한다.

```javascript
function showThis() {
  console.log(this);
}

const obj = { name: 'kim', showThis };

showThis();        // 전역 객체 (strict mode에서는 undefined)
obj.showThis();    // obj
```

`showThis`라는 함수 하나지만, 호출 방식에 따라 `this`가 전혀 다른 값을 가리킨다. 이 차이를 이해하려면 바인딩 규칙 네 가지를 알아야 한다.

## 바인딩 규칙 네 가지

호출 패턴에 따라 적용되는 규칙이 정해져 있고, 여러 규칙이 동시에 충돌할 때는 우선순위가 있다. 순서대로 살펴보자.

### 기본 바인딩 (Default Binding)

함수를 아무 객체에도 연결하지 않고 독립적으로 호출할 때 적용되는 기본 규칙이다. 비엄격 모드(sloppy mode)에서는 `this`가 전역 객체를 가리킨다. 브라우저에서는 `window`, Node.js에서는 `global`(또는 `globalThis`)다. 엄격 모드(strict mode)에서는 `this`가 `undefined`가 된다.

```javascript
function foo() {
  console.log(this);
}

foo(); // 비엄격: 전역 객체, 엄격: undefined
```

ES 모듈이나 TypeScript로 작성한 코드는 기본적으로 엄격 모드이기 때문에 `this`가 `undefined`로 잡히는 경우가 훨씬 많다. 모듈 최상위에서 `this`를 찍으면 Node.js에서는 `module.exports`를 가리키는 등 환경에 따른 미묘한 차이가 있어서 라이브러리 코드에서 `this`를 독립 호출로 쓰는 건 피해야 한다.

### 암시적 바인딩 (Implicit Binding)

함수를 객체의 메서드로 호출할 때 `this`는 그 객체를 가리킨다. 호출 시점에 "점(.) 앞에 뭐가 있는지"를 보면 된다. `obj.foo()`처럼 점 앞에 `obj`가 있으면 `this`가 `obj`다.

```javascript
const user = {
  name: 'park',
  greet() {
    console.log(`hello, ${this.name}`);
  },
};

user.greet(); // hello, park
```

암시적 바인딩이 헷갈리는 지점은 함수를 변수에 꺼내서 호출할 때다. 이때는 더 이상 객체의 메서드 호출이 아니라 독립 호출이 되기 때문에 기본 바인딩으로 돌아간다.

```javascript
const greet = user.greet;
greet(); // hello, undefined (엄격 모드면 TypeError)
```

`greet`라는 변수에 함수 참조만 복사됐을 뿐이고, `user`와의 연결은 끊어진다. 콜백으로 메서드를 넘기는 순간 이런 현상이 발생한다. `setTimeout(user.greet, 100)` 같은 코드가 대표적인 함정이다. `setTimeout`은 내부에서 전달받은 함수를 독립적으로 호출하기 때문에 `this`가 날아간다.

### 명시적 바인딩 (Explicit Binding)

`call`, `apply`, `bind`를 써서 `this`를 직접 지정하는 방식이다. 호출 지점에서 개발자가 명시적으로 컨텍스트를 고정한다.

```javascript
function greet(greeting) {
  console.log(`${greeting}, ${this.name}`);
}

const user = { name: 'lee' };

greet.call(user, 'hi');    // hi, lee
greet.apply(user, ['hello']); // hello, lee

const boundGreet = greet.bind(user);
boundGreet('안녕');        // 안녕, lee
```

명시적 바인딩은 암시적 바인딩보다 우선순위가 높다. `call`/`apply`/`bind`로 고정한 `this`는 어떤 객체의 메서드처럼 호출해도 덮어쓰이지 않는다.

### new 바인딩

함수 앞에 `new` 키워드를 붙여서 호출하면 다음과 같은 일이 순서대로 일어난다. 먼저 새 객체가 만들어지고, 그 객체가 함수 내부의 `this`로 바인딩되고, 함수 본문이 실행되고, 함수가 객체를 명시적으로 반환하지 않으면 새로 만든 객체가 반환된다.

```javascript
function User(name) {
  this.name = name;
}

const u = new User('choi');
console.log(u.name); // choi
```

`new` 바인딩은 명시적 바인딩보다도 우선순위가 높다. `bind`로 고정한 함수라도 `new`와 함께 호출하면 새로 생성된 객체가 `this`가 된다(이건 ES6 이전에 `bind`를 폴리필로 구현하던 시절에 꽤 골치 아픈 주제였다).

### 우선순위 정리

네 가지 규칙이 겹칠 때는 다음 순서로 적용된다. `new` 바인딩 > 명시적 바인딩 > 암시적 바인딩 > 기본 바인딩. 실무에서 `this`를 추적할 때는 호출 지점을 보고 "어떤 규칙이 적용되고 있는지"를 순서대로 체크하면 된다.

## call, apply, bind의 차이

세 메서드 모두 `this`를 명시적으로 지정한다는 공통점이 있지만, 인자 전달 방식과 실행 시점이 다르다.

### call과 apply

`call`과 `apply`는 함수를 **즉시 호출**한다. 차이는 인자를 어떻게 넘기느냐다. `call`은 인자를 쉼표로 구분해서 나열하고, `apply`는 배열로 넘긴다.

```javascript
function sum(a, b, c) {
  return a + b + c;
}

sum.call(null, 1, 2, 3);       // 6
sum.apply(null, [1, 2, 3]);    // 6
```

ES6 전개 연산자(`...`)가 들어오기 전에는 배열의 요소들을 인자로 넘겨야 할 때 `apply`를 썼다. `Math.max.apply(null, [1, 2, 3])` 같은 패턴이 흔했다. 지금은 `Math.max(...[1, 2, 3])`로 쓰면 되니까 `apply`를 쓸 이유가 많이 줄었다. `call`은 여전히 쓰이는데, 특히 배열이 아닌 유사 배열(예: `arguments`, `NodeList`)에 배열 메서드를 빌려 쓸 때 `Array.prototype.slice.call(arguments)` 같은 관용구로 등장한다(이 역시 요즘은 `Array.from`이나 전개 연산자로 대체된다).

### bind

`bind`는 함수를 즉시 호출하지 않는다. `this`와 일부 인자가 미리 고정된 **새로운 함수**를 반환한다. 나중에 호출할 수 있도록 함수 자체를 만들어주는 것이다.

```javascript
function multiply(a, b) {
  return a * b;
}

const double = multiply.bind(null, 2);
double(5); // 10
```

`bind`는 콜백에 메서드를 안전하게 넘길 때 자주 쓴다. React 클래스 컴포넌트에서 생성자에 `this.handleClick = this.handleClick.bind(this)` 같은 코드가 있는 이유가 이것이다. 나중에 다룬다.

한번 `bind`된 함수는 다시 `bind`하거나 `call`/`apply`로 `this`를 바꾸려고 해도 바뀌지 않는다. 처음 `bind`된 값이 고정된다.

```javascript
function foo() {
  console.log(this.name);
}

const a = foo.bind({ name: 'A' });
a.call({ name: 'B' }); // A — B로 바뀌지 않음
```

단, `new`와 함께 호출하면 `bind`를 덮어쓰고 새 객체가 `this`가 된다. 이 예외가 우선순위 규칙에서 `new` 바인딩이 명시적 바인딩보다 위에 있는 이유다.

## 화살표 함수의 this

화살표 함수(`=>`)는 앞서 설명한 네 가지 규칙을 **따르지 않는다**. 대신 화살표 함수가 선언된 위치의 상위 스코프에 있는 `this`를 그대로 사용한다. 이걸 "렉시컬 this(lexical this)"라고 부른다.

```javascript
const user = {
  name: 'kim',
  greetLater() {
    setTimeout(() => {
      console.log(this.name);
    }, 100);
  },
};

user.greetLater(); // kim
```

`setTimeout`의 콜백이 일반 함수였다면 독립 호출이 되어서 `this`가 전역 객체나 `undefined`가 됐을 것이다. 하지만 화살표 함수는 상위 스코프인 `greetLater`의 `this`를 그대로 끌어다 쓰기 때문에 `user`를 가리킨다.

화살표 함수의 이 특성은 클로저처럼 동작한다. 선언 위치의 `this`를 "포획"해서 계속 가지고 다닌다. `call`, `apply`, `bind`로 `this`를 바꾸려고 해도 화살표 함수는 무시한다.

```javascript
const arrow = () => console.log(this);
arrow.call({ a: 1 }); // this가 바뀌지 않음
```

이 특성 때문에 화살표 함수는 메서드로 쓰면 안 된다. 객체의 메서드로 화살표 함수를 쓰면 `this`가 객체를 가리키지 않고 상위 스코프(대부분 모듈 최상위)를 가리킨다.

```javascript
const user = {
  name: 'kim',
  greet: () => {
    console.log(this.name); // undefined
  },
};

user.greet();
```

반대로 콜백이나 타이머 안에서 바깥 `this`를 그대로 쓰고 싶을 때는 화살표 함수가 정답이다. 예전에는 `const self = this` 같은 관용구로 해결했지만 이제는 화살표 함수가 그 역할을 대신한다.

화살표 함수는 `new`와도 함께 쓸 수 없다. 생성자가 될 수 없기 때문에 `new arrow()`를 호출하면 `TypeError`가 발생한다.

## 클래스 메서드에서 this를 잃어버리는 문제

클래스 문법을 쓰면 객체지향 스타일로 코드를 쓸 수 있지만, 메서드를 콜백으로 넘길 때 `this`가 날아가는 문제는 여전히 존재한다. ES6 클래스는 내부적으로 엄격 모드로 동작하기 때문에 `this`가 날아가면 `undefined`가 되고 `this.something`을 읽는 순간 `TypeError`가 터진다.

```javascript
class Timer {
  constructor() {
    this.count = 0;
  }
  tick() {
    this.count += 1;
    console.log(this.count);
  }
}

const t = new Timer();
setInterval(t.tick, 1000); // TypeError: Cannot read properties of undefined
```

`t.tick`을 `setInterval`에 넘기는 순간 함수 참조만 전달되고, `setInterval`이 이 함수를 독립적으로 호출하기 때문에 `this`가 `undefined`가 된다. 해결 방법은 여러 가지가 있다.

첫 번째는 호출 지점에서 화살표 함수로 감싸는 방식이다. 가장 흔하고 직관적이다.

```javascript
setInterval(() => t.tick(), 1000);
```

두 번째는 `bind`로 고정하는 방식이다. 클래스 생성자에서 미리 바인딩해둔다.

```javascript
class Timer {
  constructor() {
    this.count = 0;
    this.tick = this.tick.bind(this);
  }
  tick() {
    this.count += 1;
  }
}
```

세 번째는 클래스 필드 문법으로 메서드 자체를 화살표 함수로 정의하는 방식이다. 이 경우 `tick`은 프로토타입이 아니라 인스턴스에 붙고, 화살표 함수라서 `this`가 인스턴스로 고정된다.

```javascript
class Timer {
  count = 0;
  tick = () => {
    this.count += 1;
  };
}
```

세 방식은 성능 특성이 조금 다르다. 생성자에서 `bind`를 하거나 클래스 필드로 화살표 함수를 정의하면 인스턴스마다 함수가 하나씩 생긴다. 인스턴스가 많아지면 메모리를 그만큼 더 쓴다. 반면 호출 지점에서 감싸는 방식은 메서드가 프로토타입에 남아있어서 인스턴스 간 공유된다. 대규모 서비스에서 수십만 개의 인스턴스를 만드는 상황이 아니라면 실무에서 체감되는 차이는 거의 없다.

## React와 Vue에서 자주 겪는 this 문제

프론트엔드에서 `this` 문제는 백엔드보다 훨씬 자주 겪는다. 이벤트 핸들러를 메서드로 정의하고 JSX나 템플릿에 넘기는 패턴이 기본이기 때문이다.

### React 클래스 컴포넌트

React 클래스 컴포넌트를 쓰던 시절에는 이벤트 핸들러에서 `this`가 날아가는 문제가 단골이었다. 아래 코드는 동작하지 않는다.

```jsx
class Counter extends React.Component {
  state = { count: 0 };
  handleClick() {
    this.setState({ count: this.state.count + 1 });
  }
  render() {
    return <button onClick={this.handleClick}>+</button>;
  }
}
```

`onClick={this.handleClick}`으로 메서드를 넘기는 순간 참조만 전달되고, React가 내부에서 독립적으로 호출하기 때문에 `this`가 `undefined`가 된다. 버튼을 누르면 `Cannot read properties of undefined (reading 'setState')` 오류가 뜬다. 해결 방법은 클래스 메서드 `this` 손실 문제와 동일하다.

```jsx
// 1. 생성자에서 bind
constructor(props) {
  super(props);
  this.handleClick = this.handleClick.bind(this);
}

// 2. 클래스 필드 + 화살표 함수
handleClick = () => {
  this.setState(...);
};

// 3. JSX에서 화살표 함수로 감싸기
<button onClick={() => this.handleClick()}>+</button>
```

세 번째 방식은 렌더링마다 새 함수를 만들기 때문에 자식 컴포넌트가 `React.memo`로 감싸져 있으면 리렌더링을 유발한다. 성능에 민감한 상황에서는 피하는 편이 낫다. 함수형 컴포넌트와 훅이 표준이 된 지금은 `this` 문제 자체가 많이 줄었다. 함수형 컴포넌트에는 `this`가 아예 없기 때문이다.

### Vue Options API

Vue 2나 Vue 3의 Options API에서는 `data`, `methods`, `computed` 안에서 `this`가 Vue 인스턴스를 가리킨다. Vue가 내부적으로 컴포넌트 인스턴스에 바인딩해주기 때문이다. 그런데 여기서 화살표 함수를 쓰면 바인딩이 풀려버린다.

```javascript
export default {
  data() {
    return { count: 0 };
  },
  methods: {
    // 잘못된 예
    increment: () => {
      this.count += 1; // this는 Vue 인스턴스가 아님
    },
  },
};
```

Vue 문서에서도 "Options API에서는 화살표 함수를 쓰지 말라"고 경고한다. 이유가 바로 이 `this` 바인딩이다. Composition API(`setup`)로 넘어오면 `this`를 쓰지 않기 때문에 이 문제도 사라진다.

### 이벤트 핸들러와 addEventListener

순수 DOM API인 `addEventListener`도 비슷한 패턴이다. 콜백 안에서 `this`는 기본적으로 이벤트가 발생한 엘리먼트를 가리킨다.

```javascript
button.addEventListener('click', function () {
  console.log(this); // button 엘리먼트
});

button.addEventListener('click', () => {
  console.log(this); // 상위 스코프의 this
});
```

일반 함수 콜백에서는 `this`가 엘리먼트를 가리키고, 화살표 함수 콜백에서는 선언 위치의 `this`를 가리킨다. 엘리먼트에 직접 접근해야 한다면 일반 함수를 쓰거나 이벤트 객체의 `event.currentTarget`을 쓰는 게 명확하다. `event.currentTarget`은 화살표 함수 안에서도 올바르게 잡힌다.

## 실무에서 this를 다룰 때 기억할 것

`this`를 다룰 때 가장 중요한 건 "호출 지점에서 어떤 규칙이 적용되는지"를 읽어내는 감각이다. 함수 선언부만 봐서는 절대 알 수 없다. 점(.)으로 호출했는지, 독립적으로 호출했는지, `new`를 붙였는지, `call`/`apply`/`bind`로 고정했는지를 확인해야 한다.

현대 자바스크립트 코드에서 `this` 문제가 줄어든 가장 큰 이유는 함수형 스타일과 화살표 함수의 보급이다. 객체지향 클래스를 깊게 쓰지 않고 모듈 함수와 클로저로 상태를 관리하면 `this`를 만날 일이 거의 없다. 다만 외부 라이브러리나 레거시 코드에서는 여전히 `this`가 등장하기 때문에 규칙을 정확히 이해하고 있어야 디버깅이 가능하다.

TypeScript를 쓰면 `this`의 타입을 미리 지정할 수 있어서 일부 문제를 컴파일 타임에 잡을 수 있다. 메서드 시그니처에 `this: void`를 붙이면 해당 메서드가 `this`를 쓰지 않도록 강제할 수 있고, `this: SomeType`을 붙이면 호출할 때 `this`가 특정 타입이어야 한다고 알려줄 수 있다. 하지만 이것도 결국 "호출 방식에 따라 `this`가 달라진다"는 자바스크립트의 근본적인 동작을 바꿔주지는 않는다. 규칙을 이해하는 것이 먼저다.
