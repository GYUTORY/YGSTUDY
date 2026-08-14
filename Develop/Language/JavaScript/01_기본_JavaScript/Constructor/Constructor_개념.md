---
title: JavaScript 생성자 (Constructor) 개념과 사용법
tags: [language, javascript]
updated: 2025-08-10
---

# JavaScript 생성자 (Constructor) 개념과 사용법

## 배경

생성자는 객체를 생성하고 초기화하는 특별한 메서드입니다. 새로운 객체를 만들 때 해당 객체의 초기 상태와 동작을 설정하는 역할을 합니다. JavaScript에서는 함수를 생성자로 사용하여 객체를 생성할 수 있습니다.

### 생성자의 필요성
- **객체 생성**: 동일한 구조의 객체를 여러 개 생성
- **초기화**: 객체의 초기 상태 설정
- **코드 재사용**: 공통된 객체 구조 정의
- **캡슐화**: 객체의 속성과 메서드 묶기

### 기본 개념
- **생성자 함수**: 객체를 생성하는 함수
- **new 키워드**: 생성자 호출을 위한 키워드
- **this 바인딩**: 새로 생성되는 객체 참조
- **프로토타입**: 인스턴스 간 공유되는 속성과 메서드

## 핵심

### 1. 생성자 기본 문법

#### 생성자 함수 정의
```javascript
function Constructor(parameter1, parameter2, ...) {
    this.property1 = parameter1;
    this.property2 = parameter2;
    // ...
}

// 사용
const instance = new Constructor(value1, value2);
```

#### 기본 예제
```javascript
function Person(name, age) {
    this.name = name;
    this.age = age;
    
    this.sayHello = function() {
        console.log(`안녕하세요! 저는 ${this.name}이고 ${this.age}살입니다.`);
    };
}

// 인스턴스 생성
const person1 = new Person('Alice', 25);
const person2 = new Person('Bob', 30);

person1.sayHello(); // "안녕하세요! 저는 Alice이고 25살입니다."
person2.sayHello(); // "안녕하세요! 저는 Bob이고 30살입니다."
```

### 2. new 키워드의 역할

#### new 키워드 없이 호출
```javascript
function Person(name, age) {
    this.name = name;
    this.age = age;
}

// new 없이 호출하면 일반 함수로 동작
const person = Person('Alice', 25);
console.log(person); // undefined
console.log(name); // 'Alice' (전역 변수로 설정됨)
console.log(age); // 25 (전역 변수로 설정됨)
```

이 "전역 변수로 설정됨"은 **비엄격 모드에서만** 일어난다. 그리고 지금 쓰는 코드 대부분은 비엄격 모드가 아니다.

```javascript
function Person(name) { this.name = name; }
Person('Alice');
globalThis.name;   // 'Alice'   ← 전역이 오염된다

function StrictPerson(name) { 'use strict'; this.name = name; }
StrictPerson('Bob');
// TypeError: Cannot set properties of undefined (setting 'name')

class CPerson { constructor(n) { this.n = n; } }
CPerson('x');
// TypeError: Class constructor CPerson cannot be invoked without 'new'
```

세 가지 결과가 다 다르다. 비엄격 함수는 조용히 전역을 더럽히고, 엄격 함수는 `undefined` 에 대입하려다 터지고, 클래스는 아예 호출 자체를 거부한다.

셋 중 클래스가 가장 정확한 에러 메시지를 준다. `new` 를 빠뜨렸다는 사실을 **그 자리에서** 알려주기 때문이다. 엄격 함수의 `Cannot set properties of undefined` 는 원인이 `new` 누락이라는 것까지는 말해주지 않는다.

ES 모듈에서는 지시어 없이도 엄격 모드라, `import`/`export` 를 쓰는 파일이라면 이 문서의 "전역 변수로 설정됨" 예제는 재현되지 않는다.

#### new 키워드와 함께 호출
```javascript
function Person(name, age) {
    this.name = name;
    this.age = age;
}

// new와 함께 호출하면 생성자로 동작
const person = new Person('Alice', 25);
console.log(person); // Person { name: 'Alice', age: 25 }
console.log(person.name); // 'Alice'
console.log(person.age); // 25
```

#### new 키워드의 동작 과정
```javascript
function Person(name, age) {
    // 1. 빈 객체 생성: {}
    // 2. this를 새 객체에 바인딩: this = {}
    // 3. 프로토타입 연결: this.__proto__ = Person.prototype
    
    this.name = name;
    this.age = age;
    
    // 4. this 반환 (암시적)
}

// new 키워드 사용 시 내부적으로 다음과 같이 동작
function createPerson(name, age) {
    const obj = {};
    obj.__proto__ = Person.prototype;
    
    Person.call(obj, name, age);
    
    return obj;
}
```

### 3. 생성자 함수의 특징

#### 이름 규칙
```javascript
// 생성자 함수는 대문자로 시작 (관례)
function User(name, email) {
    this.name = name;
    this.email = email;
}

// 일반 함수는 소문자로 시작
function createUser(name, email) {
    return { name, email };
}

const user1 = new User('Alice', 'alice@example.com');
const user2 = createUser('Bob', 'bob@example.com');
```

#### this 바인딩
```javascript
function Car(brand, model) {
    this.brand = brand;
    this.model = model;
    
    // this는 새로 생성되는 객체를 가리킴
    this.getInfo = function() {
        return `${this.brand} ${this.model}`;
    };
}

const car1 = new Car('Toyota', 'Camry');
const car2 = new Car('Honda', 'Civic');

console.log(car1.getInfo()); // "Toyota Camry"
console.log(car2.getInfo()); // "Honda Civic"
```

#### return 문의 동작
```javascript
function TestConstructor() {
    this.value = 'test';
    
    // 객체를 반환하면 해당 객체가 반환됨
    return { custom: 'object' };
}

function TestConstructor2() {
    this.value = 'test';
    
    // 원시값을 반환하면 무시되고 this가 반환됨
    return 'primitive';
}

const test1 = new TestConstructor();
console.log(test1); // { custom: 'object' }

const test2 = new TestConstructor2();
console.log(test2); // TestConstructor2 { value: 'test' }
```

### 4. 프로토타입과 생성자

#### 프로토타입 프로퍼티
```javascript
function Person(name, age) {
    this.name = name;
    this.age = age;
}

// 프로토타입에 메서드 추가 (모든 인스턴스가 공유)
Person.prototype.sayHello = function() {
    console.log(`안녕하세요! 저는 ${this.name}입니다.`);
};

Person.prototype.getAge = function() {
    return this.age;
};

const person1 = new Person('Alice', 25);
const person2 = new Person('Bob', 30);

person1.sayHello(); // "안녕하세요! 저는 Alice입니다."
person2.sayHello(); // "안녕하세요! 저는 Bob입니다."

console.log(person1.getAge()); // 25
console.log(person2.getAge()); // 30
```

#### 프로토타입 체인
```javascript
function Animal(name) {
    this.name = name;
}

Animal.prototype.speak = function() {
    console.log(`${this.name}이(가) 소리를 냅니다.`);
};

function Dog(name, breed) {
    Animal.call(this, name); // 부모 생성자 호출
    this.breed = breed;
}

// 프로토타입 상속 설정
Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog; // 생성자 참조 복원

Dog.prototype.bark = function() {
    console.log(`${this.name}이(가) 짖습니다!`);
};

const dog = new Dog('Max', 'Golden Retriever');
dog.speak(); // "Max이(가) 소리를 냅니다."
dog.bark(); // "Max이(가) 짖습니다!"
```

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```javascript
function User(name, email, role = 'user') {
    this.name = name;
    this.email = email;
    this.role = role;
    this.createdAt = new Date();
    this.isActive = true;
}

User.prototype.getInfo = function() {
    return {
        name: this.name,
        email: this.email,
        role: this.role,
        createdAt: this.createdAt,
        isActive: this.isActive
    };
};

User.prototype.activate = function() {
    this.isActive = true;
    console.log(`${this.name} 계정이 활성화되었습니다.`);
};

User.prototype.deactivate = function() {
    this.isActive = false;
    console.log(`${this.name} 계정이 비활성화되었습니다.`);
};

User.prototype.changeRole = function(newRole) {
    this.role = newRole;
    console.log(`${this.name}의 역할이 ${newRole}로 변경되었습니다.`);
};

// 사용 예시
const user1 = new User('Alice', 'alice@example.com', 'admin');
const user2 = new User('Bob', 'bob@example.com');

console.log(user1.getInfo());
user1.changeRole('moderator');
user2.deactivate();
```

#### 상품 관리 시스템
```javascript
function Product(name, price, category) {
    this.name = name;
    this.price = price;
    this.category = category;
    this.id = Date.now() + Math.random().toString(36).substr(2, 9);
    this.stock = 0;
    this.isAvailable = false;
}

Product.prototype.addStock = function(quantity) {
    this.stock += quantity;
    this.isAvailable = this.stock > 0;
    console.log(`${this.name} 재고 ${quantity}개 추가. 총 재고: ${this.stock}개`);
};

Product.prototype.removeStock = function(quantity) {
    if (this.stock >= quantity) {
        this.stock -= quantity;
        this.isAvailable = this.stock > 0;
        console.log(`${this.name} 재고 ${quantity}개 감소. 총 재고: ${this.stock}개`);
        return true;
    } else {
        console.log(`${this.name} 재고 부족. 요청: ${quantity}개, 보유: ${this.stock}개`);
        return false;
    }
};

Product.prototype.getPriceWithTax = function(taxRate = 0.1) {
    return this.price * (1 + taxRate);
};

Product.prototype.getInfo = function() {
    return {
        id: this.id,
        name: this.name,
        price: this.price,
        category: this.category,
        stock: this.stock,
        isAvailable: this.isAvailable,
        priceWithTax: this.getPriceWithTax()
    };
};

// 사용 예시
const product1 = new Product('노트북', 1000000, 'Electronics');
const product2 = new Product('책', 15000, 'Books');

product1.addStock(10);
product2.addStock(50);

console.log(product1.getInfo());
console.log(product2.getInfo());

product1.removeStock(3);
product2.removeStock(60); // 재고 부족
```

`getPriceWithTax` 는 금액을 다루는 코드에서 하지 말아야 할 일을 하고 있다. **부동소수점으로 돈을 계산한다.**

```javascript
1000000 * 1.1;   // 1100000            문제없어 보인다
15000 * 1.1;     // 16500              여기도 괜찮다
12900 * 1.1;     // 14190.000000000002 ← 여기서 샌다
```

문서의 예제 두 값이 하필 딱 떨어져서 이 함수는 정상으로 보인다. 실제 상품 가격 중에는 안 떨어지는 값이 섞여 있고, 그게 화면에 `14,190.000000000002원` 으로 나가거나 결제 금액 대조에서 1원 차이로 걸린다.

`toFixed` 로 덮는 것도 답이 아니다. 반올림 방향이 직관과 다르다.

```javascript
(1.005).toFixed(2);   // '1.00'   ← '1.01' 이 아니다
(8.165).toFixed(2);   // '8.16'
```

`1.005` 가 이진수로 정확히 표현되지 않아 실제 저장된 값이 1.005보다 아주 조금 작기 때문이다. `(1.1).toFixed(20)` 을 찍어 보면 `1.10000000000000008882` 가 나온다 — 우리가 `1.1` 이라 부르는 값의 실제 모습이다.

금액은 **정수 최소 단위로 다룬다.** 원 단위면 원으로, 센트가 필요하면 센트 정수로 계산하고 표시할 때만 나눈다. 통화가 여럿이거나 소수점 자릿수가 복잡하면 `Intl.NumberFormat` 으로 표시를 맡기고 값 자체는 정수나 `BigInt` 로 들고 있는다.

`this.id = Date.now() + Math.random().toString(36).substr(2, 9)` 도 두 가지가 걸린다. `Date.now()` 는 숫자인데 문자열과 `+` 로 이어 붙었으니 결과는 **문자열**이다(`'1786683179626w9aem1kc4'`). 의도한 것이라면 상관없지만 숫자 ID 로 알고 비교하면 어긋난다. 그리고 `substr` 은 표준 본문이 아니라 하위 호환용 부록에 남아 있는 메서드다 — `slice` 를 쓴다. ID 가 목적이면 `crypto.randomUUID()` 가 있다.

### 2. 고급 패턴

#### 팩토리 패턴
```javascript
function UserFactory() {}

UserFactory.createAdmin = function(name, email) {
    return new User(name, email, 'admin');
};

UserFactory.createModerator = function(name, email) {
    return new User(name, email, 'moderator');
};

UserFactory.createUser = function(name, email) {
    return new User(name, email, 'user');
};

// 사용 예시
const admin = UserFactory.createAdmin('Admin', 'admin@example.com');
const moderator = UserFactory.createModerator('Mod', 'mod@example.com');
const user = UserFactory.createUser('User', 'user@example.com');
```

#### 싱글톤 패턴
```javascript
function DatabaseConnection() {
    if (DatabaseConnection.instance) {
        return DatabaseConnection.instance;
    }
    
    this.connectionString = 'mongodb://localhost:27017';
    this.isConnected = false;
    
    DatabaseConnection.instance = this;
}

DatabaseConnection.prototype.connect = function() {
    if (!this.isConnected) {
        this.isConnected = true;
        console.log('데이터베이스에 연결되었습니다.');
    } else {
        console.log('이미 연결되어 있습니다.');
    }
};

DatabaseConnection.prototype.disconnect = function() {
    if (this.isConnected) {
        this.isConnected = false;
        console.log('데이터베이스 연결이 해제되었습니다.');
    } else {
        console.log('이미 연결이 해제되어 있습니다.');
    }
};

// 사용 예시
const db1 = new DatabaseConnection();
const db2 = new DatabaseConnection();

console.log(db1 === db2); // true (같은 인스턴스)

db1.connect();
db2.connect(); // 이미 연결되어 있음
```

## 운영 팁

### 성능 최적화

#### 메서드를 프로토타입에 정의
```javascript
// 비효율적인 방법: 각 인스턴스마다 메서드 생성
function InefficientPerson(name) {
    this.name = name;
    this.sayHello = function() {
        console.log(`Hello, ${this.name}!`);
    };
}

// 효율적인 방법: 프로토타입에 메서드 정의
function EfficientPerson(name) {
    this.name = name;
}

EfficientPerson.prototype.sayHello = function() {
    console.log(`Hello, ${this.name}!`);
};

// 메모리 사용량 비교
const inefficient = [];
const efficient = [];

for (let i = 0; i < 1000; i++) {
    inefficient.push(new InefficientPerson(`Person${i}`));
    efficient.push(new EfficientPerson(`Person${i}`));
}
```

### 에러 처리

#### 안전한 생성자 패턴
```javascript
function SafeConstructor(name, age) {
    // new 키워드 없이 호출된 경우 처리
    if (!(this instanceof SafeConstructor)) {
        return new SafeConstructor(name, age);
    }
    
    // 매개변수 검증
    if (typeof name !== 'string' || name.trim() === '') {
        throw new Error('이름은 비어있지 않은 문자열이어야 합니다.');
    }
    
    if (typeof age !== 'number' || age < 0) {
        throw new Error('나이는 0 이상의 숫자여야 합니다.');
    }
    
    this.name = name.trim();
    this.age = age;
}

SafeConstructor.prototype.getInfo = function() {
    return `${this.name} (${this.age}세)`;
};

// 사용 예시
try {
    const person1 = new SafeConstructor('Alice', 25);
    const person2 = SafeConstructor('Bob', 30); // new 없이도 동작
    
    console.log(person1.getInfo()); // "Alice (25세)"
    console.log(person2.getInfo()); // "Bob (30세)"
    
    // 오류 발생
    const person3 = new SafeConstructor('', 25); // Error
} catch (error) {
    console.error('오류:', error.message);
}
```

`this instanceof SafeConstructor` 는 "`new` 로 불렸는가"를 정확히 판별하지 못한다. 프로토타입만 맞으면 통과한다.

```javascript
Safe.call(Object.create(Safe.prototype), 'c');
// this instanceof Safe = true   ← new 로 부른 적이 없는데 통과
// new.target = undefined        ← 이쪽이 진짜 답이다
```

`new.target` 은 `new` 로 호출됐을 때만 함수 자신을 가리키고 아니면 `undefined` 다. 판별이 목적이면 이걸 쓴다.

다만 이 패턴 자체를 다시 생각해 볼 만하다. `new` 를 써도 되고 안 써도 되게 만들면 **호출부만 봐서는 어느 쪽인지 알 수 없다.** `new` 누락은 조용히 넘어가는 대신 즉시 터지는 편이 낫고, 클래스는 이미 그렇게 동작한다.

```javascript
class Safe {
  constructor(name) {
    if (typeof name !== 'string' || !name.trim()) throw new Error('이름 필요');
    this.name = name.trim();
  }
}
Safe('x');   // TypeError: Class constructor Safe cannot be invoked without 'new'
```

바로 위 "메모리 사용량 비교" 블록에도 비교가 없다. 두 배열에 1,000개씩 넣기만 하고 재는 코드가 없어서 실행해도 출력이 나오지 않는다. 프로토타입에 메서드를 두면 인스턴스마다 함수 객체가 생기지 않는다는 것은 구조상 맞는 말이지만, 그게 이 코드로 확인되지는 않는다.

## 참고

### 생성자 vs 클래스 비교표

| 구분 | 생성자 함수 | ES6 클래스 |
|------|-------------|------------|
| **문법** | 함수 선언 | class 키워드 |
| **호이스팅** | 함수 선언 호이스팅 | 호이스팅되지 않음 |
| **new 필수** | 선택적 (안전 패턴) | 필수 |
| **메서드 열거** | 프로토타입 메서드 | 열거되지 않음 |
| **상속** | 프로토타입 체인 | extends 키워드 |

### 생성자 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **새 프로젝트** | ES6 클래스 사용 | 현대적 문법, 명확성 |
| **레거시 코드** | 생성자 함수 유지 | 호환성 |
| **프로토타입 확장** | 생성자 함수 | 유연성 |
| **단순한 객체** | 객체 리터럴 | 간단함 |

### 결론
생성자는 JavaScript에서 객체를 생성하는 전통적인 방법입니다.
new 키워드를 사용하여 생성자 함수를 호출해야 합니다.
프로토타입을 활용하여 메모리 효율적인 메서드 공유가 가능합니다.
ES6 클래스는 생성자 함수의 문법적 설탕입니다.
안전한 생성자 패턴을 사용하여 new 키워드 없이도 동작하도록 할 수 있습니다.
생성자를 활용하여 재사용 가능하고 유지보수하기 쉬운 코드를 작성하세요.

