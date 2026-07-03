---
title: JavaScript static 멤버
tags: [language, javascript, oop, static, class]
updated: 2026-06-22
---

# JavaScript static 멤버

## 정의

`static`은 클래스 자체에 붙는 프로퍼티와 메서드를 정의한다. 인스턴스(`new`로 만든 객체)가 아니라 클래스 객체에 직접 매달린다.

```javascript
class MathUtils {
  static PI = 3.14159;

  static add(a, b) {
    return a + b;
  }
}

console.log(MathUtils.PI);        // 3.14159
console.log(MathUtils.add(5, 3)); // 8

const m = new MathUtils();
console.log(m.PI);  // undefined — 인스턴스에는 없다
console.log(m.add); // undefined
```

`MathUtils.PI`는 `MathUtils`라는 함수 객체의 프로퍼티고, `MathUtils.add`도 마찬가지다. 인스턴스 `m`의 프로토타입 체인에는 올라가지 않기 때문에 `m.PI`는 `undefined`다. 여기까지가 흔히 아는 내용이고, 실무에서 발목 잡는 건 그 다음이다. `static` 메서드의 `this`가 무엇인지, `static` 필드가 상속될 때 참조가 어떻게 공유되는지, private static에 서브클래스가 접근하면 왜 터지는지를 모르면 디버깅에 시간을 쏟게 된다.

## static 메서드의 this — 떼어내면 깨진다

`static` 메서드 안의 `this`는 그 메서드를 호출한 클래스다. `MathUtils.add()`로 부르면 `this === MathUtils`다. 문제는 메서드를 변수에 담거나 콜백으로 넘기는 순간 이 연결이 끊긴다는 점이다.

```javascript
class StringUtils {
  static prefix = '>> ';

  static decorate(str) {
    return this.prefix + str; // this에 의존
  }
}

console.log(StringUtils.decorate('hello')); // ">> hello"

// 메서드를 변수에 떼어내면 this가 사라진다
const fn = StringUtils.decorate;
console.log(fn('hello'));
// TypeError: Cannot read properties of undefined (reading 'prefix')
```

`const fn = StringUtils.decorate`로 함수만 꺼내면 호출 시점에 앞에 `StringUtils.`가 없으므로 `this`가 `undefined`가 된다(클래스 본문은 strict mode라 `undefined`이지 전역 객체가 아니다). `this.prefix`에서 바로 터진다.

콜백으로 넘길 때도 같은 일이 벌어진다.

```javascript
class Validator {
  static rules = ['notEmpty', 'maxLength'];

  static check(value) {
    return this.rules.length > 0 && value != null;
  }
}

const inputs = ['a', 'b', 'c'];

// 이렇게 넘기면 깨진다
inputs.map(Validator.check);
// TypeError: Cannot read properties of undefined (reading 'length')
```

`map`은 콜백을 `this` 없이 호출하므로 `Validator.check` 내부의 `this.rules`가 죽는다. 해결법은 세 가지다.

```javascript
// 1. 화살표 함수로 감싸 호출 컨텍스트를 유지
inputs.map(v => Validator.check(v));

// 2. bind로 this를 박아둔다
const boundCheck = Validator.check.bind(Validator);
inputs.map(boundCheck);

// 3. 애초에 this를 안 쓰게 클래스 이름으로 직접 참조
class Validator2 {
  static rules = ['notEmpty'];
  static check(value) {
    return Validator2.rules.length > 0 && value != null; // this 대신 클래스명
  }
}
```

세 번째 방식은 `this`를 포기하는 대신 상속에서 서브클래스의 오버라이드를 못 받는다는 단점이 있다. `Validator2.check`를 자식이 상속받아도 항상 `Validator2.rules`를 본다. 상속을 쓸 계획이 없는 유틸 클래스라면 클래스명 직접 참조가 사고를 줄인다. 상속 다형성이 필요하면 `this`를 쓰되 콜백으로 넘길 때 화살표 함수나 `bind`로 감싸는 습관을 들여야 한다.

## static 필드가 가변 객체일 때 — 상속 체인에서 참조 공유

`static` 필드가 원시값이면 별 문제가 없는데, 배열이나 객체 같은 가변 값일 때 상속이 끼면 골치 아파진다. 핵심은 **자식 클래스가 자기만의 static 필드를 따로 갖느냐**다.

```javascript
class Repository {
  static cache = []; // 부모에 정의

  static add(item) {
    this.cache.push(item);
  }
}

class UserRepository extends Repository {}
class OrderRepository extends Repository {}

UserRepository.add('user-1');
OrderRepository.add('order-1');

console.log(UserRepository.cache);  // ['user-1', 'order-1']
console.log(OrderRepository.cache); // ['user-1', 'order-1'] — 섞였다!
console.log(Repository.cache);      // ['user-1', 'order-1']
```

`UserRepository`는 `cache`를 자기 필드로 갖고 있지 않다. `cache`는 부모 `Repository`에만 있고, 자식들은 프로토타입 체인을 타고 같은 배열 하나를 본다. `this.cache.push()`는 그 공유 배열에 그대로 밀어 넣는다. 그래서 `UserRepository`에 넣은 데이터가 `OrderRepository`에서도 보인다. 서브클래스별로 독립된 상태가 필요한 상황이라면 이건 명백한 버그다.

해결은 서브클래스마다 자기 필드를 다시 선언하는 것이다.

```javascript
class Repository {
  static cache = [];
  static add(item) {
    this.cache.push(item);
  }
}

class UserRepository extends Repository {
  static cache = []; // 자식이 자기 필드를 새로 가진다
}
class OrderRepository extends Repository {
  static cache = [];
}

UserRepository.add('user-1');
OrderRepository.add('order-1');

console.log(UserRepository.cache);  // ['user-1']
console.log(OrderRepository.cache); // ['order-1'] — 분리됐다
```

`static cache = []`를 자식에 다시 쓰면 자식 클래스 객체에 별도의 배열이 생긴다. 이제 `this.cache`가 가리키는 배열이 클래스마다 다르다.

매번 자식에 필드 재선언을 강제하는 건 잊어먹기 쉽다. 지연 초기화 패턴으로 자식이 필드를 안 가졌으면 그때 만들게 하는 방법도 있다.

```javascript
class Repository {
  static getCache() {
    // 자기 자신이 직접 cache를 소유하는지 확인
    if (!Object.hasOwn(this, 'cache')) {
      this.cache = [];
    }
    return this.cache;
  }
  static add(item) {
    this.getCache().push(item);
  }
}

class UserRepository extends Repository {}
UserRepository.add('user-1');
console.log(UserRepository.cache); // ['user-1'] — 자기 필드로 생성됨
```

`Object.hasOwn(this, 'cache')`는 프로토타입 체인을 거슬러 올라가지 않고 `this`가 직접 소유한 프로퍼티인지만 본다. 상속받은 부모 것은 `false`로 잡히므로, 자식이 처음 `add`를 호출할 때 자기 `cache`를 새로 만든다. 라이브러리에서 base 클래스를 제공하고 사용자가 마음대로 상속하는 구조라면 이런 방어가 필요하다.

## static private (#) 멤버 — 접근 범위와 서브클래스의 함정

`#`을 붙인 static 멤버는 그 클래스 본문 안에서만 접근된다. private 메서드를 `static`으로 만들면 내부 헬퍼로 쓰기 좋다.

```javascript
class TokenService {
  static #secret = 'a1b2c3';

  static #hash(value) {
    return value + ':' + this.#secret;
  }

  static issue(userId) {
    return this.#hash(userId);
  }
}

console.log(TokenService.issue('u-100')); // "u-100:a1b2c3"
console.log(TokenService.#secret);
// SyntaxError: Private field '#secret' must be declared in an enclosing class
```

`#secret`은 클래스 밖에서는 문법 에러로 막힌다. 여기까지는 의도대로다. 함정은 상속이다. private static 멤버는 **선언된 클래스 객체에만** 존재하고, 서브클래스 객체에는 없다. 그런데 서브클래스에서 부모의 static 메서드를 통해 접근하면 `this`가 서브클래스가 되면서 터진다.

```javascript
class Base {
  static #registry = new Map();

  static register(key, value) {
    // this가 누구냐에 따라 #registry 접근 성공/실패가 갈린다
    this.#registry.set(key, value);
  }
}

class Child extends Base {}

Base.register('a', 1);   // 정상
Child.register('b', 2);
// TypeError: Cannot read private member #registry from an object
//            whose class did not declare it
```

`Child.register('b', 2)`를 호출하면 상속받은 `register`가 실행되는데 그 안의 `this`는 `Child`다. `#registry`는 `Base` 클래스 객체에만 박혀 있고 `Child` 객체에는 없다. private 멤버 접근은 "이 객체의 클래스가 해당 private을 선언했는가"를 런타임에 검사하기 때문에 `Child`로는 통과하지 못하고 `TypeError`를 던진다.

이 문제를 피하려면 private static 메서드 안에서 `this` 대신 클래스 이름을 직접 박는다.

```javascript
class Base {
  static #registry = new Map();

  static register(key, value) {
    Base.#registry.set(key, value); // this가 아니라 Base로 고정
  }
  static get(key) {
    return Base.#registry.get(key);
  }
}

class Child extends Base {}

Base.register('a', 1);
Child.register('b', 2);  // this가 Child여도 Base.#registry를 본다
console.log(Base.get('b')); // 2
```

레지스트리를 부모 한 곳에 모으는 게 의도라면 이게 맞다. 반대로 서브클래스마다 별도 레지스트리가 필요하다면 private static은 애초에 안 맞고, 앞서 본 `Object.hasOwn` 방식의 public 혹은 protected 패턴을 써야 한다. private은 상속 다형성과 같이 가기 어렵다는 걸 기억하면 된다.

## static 초기화 블록 — 실행 시점과 순서

`static {}` 블록은 클래스가 평가될 때(정의가 실행될 때) 딱 한 번 돈다. 인스턴스를 만들든 안 만들든 상관없다. 모듈이 import되고 클래스 선언이 실행되는 그 시점이다.

```javascript
console.log('before class');

class Config {
  static env = 'production';
  static endpoints;

  static {
    console.log('static block runs');
    this.endpoints = this.env === 'production'
      ? ['api.prod.com']
      : ['localhost'];
  }
}

console.log('after class');
console.log(Config.endpoints); // ['api.prod.com']

// 출력 순서:
// before class
// static block runs   ← 인스턴스 생성 없이 클래스 평가 시점에 실행
// after class
// ['api.prod.com']
```

초기화 블록 안의 `this`는 클래스 자신이다. 그래서 `this.env`, `this.endpoints`로 다른 static 멤버에 접근한다. 단순 필드로는 표현 못 하는 복잡한 초기화 로직(조건 분기, try/catch, 여러 필드를 엮은 계산)을 여기에 넣는다.

여러 static 필드와 블록이 섞여 있으면 **본문에 적힌 순서대로 위에서 아래로** 평가된다. 이게 중요한 이유는 아래 필드가 위 필드를 참조할 수 있고 그 역은 안 되기 때문이다.

```javascript
class Pipeline {
  static a = 1;

  static {
    console.log('block-1, a =', this.a, ', b =', this.b);
    // block-1, a = 1, b = undefined  ← b는 아직 선언 전
  }

  static b = this.a + 10; // 11

  static {
    console.log('block-2, b =', this.b);
    // block-2, b = 11  ← 이제 b가 초기화됨
  }
}
```

`block-1` 시점에는 `b`가 아직 평가되지 않아 `undefined`다. `static b = this.a + 10`이 그 다음 줄이라 `block-1`을 지나야 11이 된다. 필드 간 의존이 있으면 선언 순서를 신경 써야 한다. 위쪽 필드가 아래쪽 필드를 참조하면 `undefined`나 `ReferenceError`(let/const TDZ와 유사하게)로 이어진다.

## 정적 멤버 상속 — super와 프로토타입 체인

`extends`로 클래스를 상속하면 static 멤버도 같이 상속된다. 이게 가능한 건 자식 클래스의 생성자 함수가 부모 생성자 함수를 프로토타입으로 갖기 때문이다. 인스턴스 쪽 체인과 별개로 클래스(생성자 함수) 자체의 체인이 따로 있다.

```javascript
class Animal {
  static planet = 'Earth';
  static describe() {
    return `lives on ${this.planet}`;
  }
}

class Dog extends Animal {}

console.log(Dog.planet);       // 'Earth' — 상속됨
console.log(Dog.describe());   // 'lives on Earth'

// 생성자 함수의 __proto__가 부모 생성자
console.log(Object.getPrototypeOf(Dog) === Animal); // true
console.log(Dog.__proto__ === Animal);              // true (같은 의미)
```

`Dog.planet`을 찾을 때 엔진은 `Dog` 자신에 없으면 `Object.getPrototypeOf(Dog)`, 즉 `Animal`로 올라가 찾는다. 일반 객체의 프로토타입 체인과 똑같은 메커니즘이 클래스 객체 레벨에서 도는 것이다. 인스턴스의 `__proto__`가 `Prototype` 객체를 가리키는 것과는 별개의 체인이라는 점을 구분해야 한다.

static 메서드 안에서 `super`를 쓰면 부모의 static 메서드를 호출한다.

```javascript
class Logger {
  static format(msg) {
    return `[LOG] ${msg}`;
  }
}

class TimestampLogger extends Logger {
  static format(msg) {
    const base = super.format(msg); // 부모의 static format 호출
    return `2026-06-22 ${base}`;
  }
}

console.log(TimestampLogger.format('start'));
// "2026-06-22 [LOG] start"
```

`super.format`은 `TimestampLogger`의 static 프로토타입(`Logger`)에서 `format`을 찾아 호출하되, `this`는 여전히 `TimestampLogger`로 유지된다. 그래서 부모 메서드 안에서 `this.somethingStatic`을 쓰면 자식의 값을 본다. 이 동작이 앞서 본 가변 필드 공유 버그와 맞물리면 헷갈리니, 부모 static 메서드가 `this`로 필드를 건드린다면 그 필드가 어느 클래스에 실제로 존재하는지 항상 확인해야 한다.

## 클래스 static 대신 모듈 레벨을 쓰는 편이 나은 경우

`static`만 잔뜩 모은 클래스, 즉 인스턴스를 아예 안 만드는 유틸 클래스는 자바 출신 개발자들이 습관적으로 만든다. 자바스크립트에서는 모듈 시스템이 그 역할을 더 잘 한다. `class`로 감쌀 이유가 없으면 모듈 레벨 `const`와 함수로 푸는 게 낫다.

```javascript
// 굳이 클래스로 감싼 형태
class MathUtils {
  static PI = 3.14159;
  static add(a, b) { return a + b; }
  static square(x) { return x * x; }
}

// 모듈로 푼 형태 — math.js
export const PI = 3.14159;
export function add(a, b) { return a + b; }
export function square(x) { return x * x; }
```

모듈 쪽이 나은 지점이 몇 가지 있다. 트리 셰이킹이 함수 단위로 동작해 안 쓰는 `square`는 번들에서 빠진다. 클래스로 묶으면 보통 통째로 들어간다. `import { add } from './math.js'`로 필요한 것만 가져오니 호출부도 짧다. `this` 바인딩 문제 자체가 사라져서 `add`를 콜백으로 넘겨도 안 깨진다.

클래스 static을 굳이 골라야 하는 경우는 상속으로 일부를 오버라이드하는 다형성이 필요할 때, 그리고 `Map.from`이나 `Promise.resolve`처럼 인스턴스 메서드와 static 메서드를 한 타입 안에 묶어 API를 일관되게 보여줄 때다. 그 외 순수 함수 묶음은 모듈이 깔끔하다.

### 싱글톤·레지스트리 구현 시 주의점

싱글톤을 static으로 만들 때 가장 흔히 보는 실수는 모듈 캐싱을 무시하고 클래스 안에서 직접 인스턴스를 관리하는 것이다. ES 모듈은 한 번 평가되면 그 결과가 캐싱되므로, 모듈 레벨에서 인스턴스를 만들어 export하면 그 자체로 싱글톤이다.

```javascript
// db.js — 모듈 캐싱이 싱글톤을 보장한다
class Database {
  constructor() {
    this.connection = connect();
  }
  query(sql) { /* ... */ }
}

export const db = new Database(); // 모듈이 한 번만 평가되므로 인스턴스도 하나
```

`import { db } from './db.js'`를 여러 파일에서 해도 모두 같은 `db`를 받는다. 굳이 `static getInstance()` 패턴을 흉내 낼 필요가 없다. static으로 직접 구현하면 이런 함정이 있다.

```javascript
class Database {
  static #instance = null;
  static getInstance() {
    if (!this.#instance) {
      this.#instance = new Database();
    }
    return this.#instance;
  }
}
```

이 코드는 멀쩡해 보이지만 `this.#instance` 때문에 서브클래스에서 `getInstance`를 부르면 앞 절에서 본 private static `TypeError`가 난다. 그리고 동시성 측면에서 자바스크립트는 단일 스레드라 더블 체크 락 같은 건 필요 없지만, 생성자 안에서 `await`을 쓰는 비동기 초기화라면 `getInstance`가 동시에 두 번 불려 인스턴스가 두 개 생길 수 있다. 그럴 땐 인스턴스가 아니라 진행 중인 Promise를 캐싱한다.

```javascript
let initPromise = null; // 모듈 레벨

export function getDatabase() {
  if (!initPromise) {
    initPromise = (async () => {
      const conn = await connect();
      return new Database(conn);
    })();
  }
  return initPromise; // 항상 같은 Promise를 반환
}
```

레지스트리(키로 객체를 등록/조회하는 저장소)를 static으로 만들 때는 가변 필드 공유 문제가 그대로 적용된다. 라이브러리에서 base 레지스트리를 제공하고 사용자가 상속하는 구조라면, 부모 한 곳에 모을지 서브클래스별로 분리할지를 먼저 정하고 그에 맞게 `this`냐 클래스명 고정이냐를 골라야 한다. 등록 시점이 모듈 import 순서에 의존하면(A 모듈이 B 모듈에 자기를 등록하는 식) 순환 import에서 등록이 누락되는 사고가 잘 나니, 등록은 명시적 호출로 모아두는 편이 추적하기 쉽다.

## 정리

static 멤버는 클래스 객체에 직접 붙는 프로퍼티이고, 인스턴스와 별개의 프로토타입 체인을 탄다. 실무에서 사고가 나는 지점은 정해져 있다. 메서드를 떼어내거나 콜백으로 넘기면 `this`가 죽고, 가변 static 필드는 상속 체인에서 참조가 공유되며, private static은 서브클래스 `this`로 접근하면 `TypeError`가 난다. `this`에 의존할지 클래스명을 박을지를 상속 계획에 맞춰 정하는 게 핵심이고, 인스턴스를 안 만드는 순수 유틸이라면 클래스보다 모듈 레벨 함수가 대개 낫다.
