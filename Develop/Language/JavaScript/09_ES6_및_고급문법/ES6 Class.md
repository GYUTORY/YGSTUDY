---
title: ES6 Class
tags: [language, javascript]
updated: 2025-12-21
---
# ES6 Class

## 배경

ES6 클래스는 JavaScript에서 객체 지향 프로그래밍을 더 쉽게 구현할 수 있도록 도와주는 문법입니다. 

**핵심 포인트:**
- ES5까지는 클래스가 없어서 프로토타입으로 객체를 만들었음
- ES6부터는 다른 언어처럼 `class` 키워드를 사용할 수 있음
- 내부적으로는 여전히 프로토타입 방식으로 동작함 (단지 문법만 클래스처럼 보임)

---


### 클래스 선언과 생성자

```javascript
class Person {
   // 클래스 필드 (인스턴스 변수) - ES2022 문법
   height = 180;  // 기본값 설정
   
   // 생성자 - 객체 생성 시 호출되는 특별한 메서드
   constructor(name, age) {
      this.name = name;  // 인스턴스 속성 설정
      this.age = age;
   }
}

// 객체 생성
let person1 = new Person('john', 23);
console.log(person1.name);    // "john"
console.log(person1.age);     // 23
console.log(person1.height);  // 180
```

**중요한 포인트:**
- `constructor`는 클래스당 하나만 존재 가능
- `constructor` 이름은 변경 불가
- `this`는 생성될 인스턴스를 가리킴
- 클래스 필드는 `public` (외부에서 접근 가능)

### 클래스 필드 vs 생성자 내부 속성

```javascript
class Student {
   // 클래스 필드 방식
   school = '서울고등학교';
   
   constructor(name, grade) {
      // 생성자 내부에서 설정하는 방식
      this.name = name;
      this.grade = grade;
   }
}

const student = new Student('김철수', 2);
console.log(student.school);  // "서울고등학교"
console.log(student.name);    // "김철수"
console.log(student.grade);   // 2
```

두 방식의 진짜 차이는 문법이 아니라 **실행 순서**다. 클래스 필드는 코드에서 어디에 적혀 있든 **생성자 본문보다 먼저** 실행된다.

```javascript
class A {
  b = this.a;                       // 이 줄이 먼저다
  constructor(a) { this.a = a; }    // 이 줄이 나중이다
}
new A(10).b;    // undefined — 생성자 인자를 볼 수 없다
```

필드에 `this.무언가` 를 쓰는 순간 이 순서에 걸린다. 위 `school = '서울고등학교'` 처럼 상수만 넣으면 문제가 없지만, `fullName = this.first + this.last` 같은 것을 쓰면 언제나 `undefined undefined` 다. 계산이 필요한 값은 필드가 아니라 생성자 안에서 만든다.

순서는 속성이 만들어지는 순서에도 그대로 나타난다.

```javascript
class B {
  constructor(a) { this.a = a; }
  b = 'field';
}
Object.keys(new B(1));   // ['b', 'a'] — 아래 적힌 b 가 먼저다
```

`JSON.stringify` 결과의 키 순서가 코드 순서와 다른 이유가 이것이다. 응답 필드 순서를 눈으로 대조하다 헷갈리기 좋은 지점이다.

상속이 끼면 순서가 하나 더 생긴다. 자식 필드는 `super()` 가 끝난 **뒤에** 초기화된다.

```javascript
class P {
  constructor() { console.log(this.childField); this.init(); }
  init() {}
}
class C extends P {
  childField = 'ready';
  constructor() { super(); console.log(this.childField); }
  init() { console.log(this.childField); }
}
new C();
// undefined   ← 부모 생성자에서 본 값
// undefined   ← 부모가 부른 init() 안에서 본 값 (오버라이드된 자식 메서드다)
// ready       ← super() 가 끝난 뒤
```

부모 생성자가 오버라이드 가능한 메서드를 호출하는 구조는 그래서 위험하다. 자식이 그 메서드를 재정의하면 **자기 필드가 아직 준비되지 않은 상태에서** 불린다. 초기화 로직을 생성자에서 부르는 대신 호출부가 명시적으로 부르게 하거나, 부모에서 부를 메서드는 오버라이드하지 못하게(private) 만든다.

---


```javascript
class Person {
   // 클래스 필드 (인스턴스 변수) - ES2022 문법
   height = 180;  // 기본값 설정
   
   // 생성자 - 객체 생성 시 호출되는 특별한 메서드
   constructor(name, age) {
      this.name = name;  // 인스턴스 속성 설정
      this.age = age;
   }
}

// 객체 생성
let person1 = new Person('john', 23);
console.log(person1.name);    // "john"
console.log(person1.age);     // 23
console.log(person1.height);  // 180
```

**중요한 포인트:**
- `constructor`는 클래스당 하나만 존재 가능
- `constructor` 이름은 변경 불가
- `this`는 생성될 인스턴스를 가리킴
- 클래스 필드는 `public` (외부에서 접근 가능)


### 기본 메서드 정의

```javascript
class Calculator {
   // 더하기 메서드
   add(x, y) {
     return x + y;
   }
   
   // 빼기 메서드
   subtract(x, y) {
     return x - y;
   }
   
   // 곱하기 메서드
   multiply(x, y) {
     return x * y;
   }
   
   // 나누기 메서드
   divide(x, y) {
     if (y === 0) {
       throw new Error('0으로 나눌 수 없습니다.');
     }
     return x / y;
   }
}

// 사용 예시
let calc = new Calculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.subtract(10, 4)); // 6
console.log(calc.multiply(2, 6));  // 12
console.log(calc.divide(15, 3));   // 5
```

### 계산된 속성명을 사용한 메서드

```javascript
// 동적으로 메서드 이름을 결정할 수 있음
const methodName = 'introduce';
const greetingMethod = 'sayHello';

class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }
  
  // 대괄호를 사용해 동적 메서드명 설정
  [methodName]() {
    return `안녕하세요, 제 이름은 ${this.name}입니다.`;
  }
  
  [greetingMethod]() {
    return `안녕! ${this.name}이라고 해요.`;
  }
}

const person = new Person('윤아준', 19);
console.log(person.introduce());  // "안녕하세요, 제 이름은 윤아준입니다."
console.log(person.sayHello());   // "안녕! 윤아준이라고 해요."
```

---


```javascript
class Calculator {
   // 더하기 메서드
   add(x, y) {
     return x + y;
   }
   
   // 빼기 메서드
   subtract(x, y) {
     return x - y;
   }
   
   // 곱하기 메서드
   multiply(x, y) {
     return x * y;
   }
   
   // 나누기 메서드
   divide(x, y) {
     if (y === 0) {
       throw new Error('0으로 나눌 수 없습니다.');
     }
     return x / y;
   }
}

// 사용 예시
let calc = new Calculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.subtract(10, 4)); // 6
console.log(calc.multiply(2, 6));  // 12
console.log(calc.divide(15, 3));   // 5
```


```javascript
// 동적으로 메서드 이름을 결정할 수 있음
const methodName = 'introduce';
const greetingMethod = 'sayHello';

class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }
  
  // 대괄호를 사용해 동적 메서드명 설정
  [methodName]() {
    return `안녕하세요, 제 이름은 ${this.name}입니다.`;
  }
  
  [greetingMethod]() {
    return `안녕! ${this.name}이라고 해요.`;
  }
}

const person = new Person('윤아준', 19);
console.log(person.introduce());  // "안녕하세요, 제 이름은 윤아준입니다."
console.log(person.sayHello());   // "안녕! 윤아준이라고 해요."
```

---


### 사용자 관리 시스템

```javascript
class User {
   constructor(username, email, role = 'user') {
     this.username = username;
     this.email = email;
     this.role = role;
     this.createdAt = new Date();
     this.isActive = true;
   }
   
   // 사용자 정보 출력
   getInfo() {
     return {
       username: this.username,
       email: this.email,
       role: this.role,
       createdAt: this.createdAt,
       isActive: this.isActive
     };
   }
   
   // 사용자 비활성화
   deactivate() {
     this.isActive = false;
     return `${this.username} 사용자가 비활성화되었습니다.`;
   }
   
   // 사용자 활성화
   activate() {
     this.isActive = true;
     return `${this.username} 사용자가 활성화되었습니다.`;
   }
   
   // 역할 변경
   changeRole(newRole) {
     this.role = newRole;
     return `${this.username}의 역할이 ${newRole}로 변경되었습니다.`;
   }
}

// 사용 예시
const user1 = new User('john_doe', 'john@example.com', 'admin');
const user2 = new User('jane_smith', 'jane@example.com');

console.log(user1.getInfo());
// {
//   username: 'john_doe',
//   email: 'john@example.com',
//   role: 'admin',
//   createdAt: 2024-01-15T10:30:00.000Z,
//   isActive: true
// }

console.log(user2.changeRole('moderator')); // "jane_smith의 역할이 moderator로 변경되었습니다."
console.log(user1.deactivate()); // "john_doe 사용자가 비활성화되었습니다."
```

---


```javascript
class User {
   constructor(username, email, role = 'user') {
     this.username = username;
     this.email = email;
     this.role = role;
     this.createdAt = new Date();
     this.isActive = true;
   }
   
   // 사용자 정보 출력
   getInfo() {
     return {
       username: this.username,
       email: this.email,
       role: this.role,
       createdAt: this.createdAt,
       isActive: this.isActive
     };
   }
   
   // 사용자 비활성화
   deactivate() {
     this.isActive = false;
     return `${this.username} 사용자가 비활성화되었습니다.`;
   }
   
   // 사용자 활성화
   activate() {
     this.isActive = true;
     return `${this.username} 사용자가 활성화되었습니다.`;
   }
   
   // 역할 변경
   changeRole(newRole) {
     this.role = newRole;
     return `${this.username}의 역할이 ${newRole}로 변경되었습니다.`;
   }
}

// 사용 예시
const user1 = new User('john_doe', 'john@example.com', 'admin');
const user2 = new User('jane_smith', 'jane@example.com');

console.log(user1.getInfo());
// {
//   username: 'john_doe',
//   email: 'john@example.com',
//   role: 'admin',
//   createdAt: 2024-01-15T10:30:00.000Z,
//   isActive: true
// }

console.log(user2.changeRole('moderator')); // "jane_smith의 역할이 moderator로 변경되었습니다."
console.log(user1.deactivate()); // "john_doe 사용자가 비활성화되었습니다."
```

---


### ES6 클래스의 특징
1. **문법적 설탕**: 내부적으로는 프로토타입 방식으로 동작
2. **생성자**: `constructor` 메서드로 객체 초기화
3. **메서드**: 클래스 내부에 직접 정의 가능
4. **상속**: `extends` 키워드로 상속 구현 가능 (다음 챕터에서 학습)
5. **캡슐화**: `private` 필드 지원 (ES2022)

### 자주 사용되는 패턴
- 객체 생성 시 초기값 설정
- 메서드를 통한 객체 상태 변경
- 계산된 속성명을 활용한 동적 메서드 생성
- 클래스 필드를 통한 기본값 설정

---

**참고 자료:** Inpa Dev - 자바스크립트 ES6 Class 문법 완벽 정리

- 객체 생성 시 초기값 설정
- 메서드를 통한 객체 상태 변경
- 계산된 속성명을 활용한 동적 메서드 생성
- 클래스 필드를 통한 기본값 설정

---

**참고 자료:** Inpa Dev - 자바스크립트 ES6 Class 문법 완벽 정리







```javascript
class Person {
   // 클래스 필드 (인스턴스 변수) - ES2022 문법
   height = 180;  // 기본값 설정
   
   // 생성자 - 객체 생성 시 호출되는 특별한 메서드
   constructor(name, age) {
      this.name = name;  // 인스턴스 속성 설정
      this.age = age;
   }
}

// 객체 생성
let person1 = new Person('john', 23);
console.log(person1.name);    // "john"
console.log(person1.age);     // 23
console.log(person1.height);  // 180
```

**중요한 포인트:**
- `constructor`는 클래스당 하나만 존재 가능
- `constructor` 이름은 변경 불가
- `this`는 생성될 인스턴스를 가리킴
- 클래스 필드는 `public` (외부에서 접근 가능)


```javascript
class Calculator {
   // 더하기 메서드
   add(x, y) {
     return x + y;
   }
   
   // 빼기 메서드
   subtract(x, y) {
     return x - y;
   }
   
   // 곱하기 메서드
   multiply(x, y) {
     return x * y;
   }
   
   // 나누기 메서드
   divide(x, y) {
     if (y === 0) {
       throw new Error('0으로 나눌 수 없습니다.');
     }
     return x / y;
   }
}

// 사용 예시
let calc = new Calculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.subtract(10, 4)); // 6
console.log(calc.multiply(2, 6));  // 12
console.log(calc.divide(15, 3));   // 5
```


```javascript
// 동적으로 메서드 이름을 결정할 수 있음
const methodName = 'introduce';
const greetingMethod = 'sayHello';

class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }
  
  // 대괄호를 사용해 동적 메서드명 설정
  [methodName]() {
    return `안녕하세요, 제 이름은 ${this.name}입니다.`;
  }
  
  [greetingMethod]() {
    return `안녕! ${this.name}이라고 해요.`;
  }
}

const person = new Person('윤아준', 19);
console.log(person.introduce());  // "안녕하세요, 제 이름은 윤아준입니다."
console.log(person.sayHello());   // "안녕! 윤아준이라고 해요."
```

---


```javascript
class Calculator {
   // 더하기 메서드
   add(x, y) {
     return x + y;
   }
   
   // 빼기 메서드
   subtract(x, y) {
     return x - y;
   }
   
   // 곱하기 메서드
   multiply(x, y) {
     return x * y;
   }
   
   // 나누기 메서드
   divide(x, y) {
     if (y === 0) {
       throw new Error('0으로 나눌 수 없습니다.');
     }
     return x / y;
   }
}

// 사용 예시
let calc = new Calculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.subtract(10, 4)); // 6
console.log(calc.multiply(2, 6));  // 12
console.log(calc.divide(15, 3));   // 5
```


```javascript
// 동적으로 메서드 이름을 결정할 수 있음
const methodName = 'introduce';
const greetingMethod = 'sayHello';

class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }
  
  // 대괄호를 사용해 동적 메서드명 설정
  [methodName]() {
    return `안녕하세요, 제 이름은 ${this.name}입니다.`;
  }
  
  [greetingMethod]() {
    return `안녕! ${this.name}이라고 해요.`;
  }
}

const person = new Person('윤아준', 19);
console.log(person.introduce());  // "안녕하세요, 제 이름은 윤아준입니다."
console.log(person.sayHello());   // "안녕! 윤아준이라고 해요."
```

---



```javascript
class User {
   constructor(username, email, role = 'user') {
     this.username = username;
     this.email = email;
     this.role = role;
     this.createdAt = new Date();
     this.isActive = true;
   }
   
   // 사용자 정보 출력
   getInfo() {
     return {
       username: this.username,
       email: this.email,
       role: this.role,
       createdAt: this.createdAt,
       isActive: this.isActive
     };
   }
   
   // 사용자 비활성화
   deactivate() {
     this.isActive = false;
     return `${this.username} 사용자가 비활성화되었습니다.`;
   }
   
   // 사용자 활성화
   activate() {
     this.isActive = true;
     return `${this.username} 사용자가 활성화되었습니다.`;
   }
   
   // 역할 변경
   changeRole(newRole) {
     this.role = newRole;
     return `${this.username}의 역할이 ${newRole}로 변경되었습니다.`;
   }
}

// 사용 예시
const user1 = new User('john_doe', 'john@example.com', 'admin');
const user2 = new User('jane_smith', 'jane@example.com');

console.log(user1.getInfo());
// {
//   username: 'john_doe',
//   email: 'john@example.com',
//   role: 'admin',
//   createdAt: 2024-01-15T10:30:00.000Z,
//   isActive: true
// }

console.log(user2.changeRole('moderator')); // "jane_smith의 역할이 moderator로 변경되었습니다."
console.log(user1.deactivate()); // "john_doe 사용자가 비활성화되었습니다."
```

---


```javascript
class User {
   constructor(username, email, role = 'user') {
     this.username = username;
     this.email = email;
     this.role = role;
     this.createdAt = new Date();
     this.isActive = true;
   }
   
   // 사용자 정보 출력
   getInfo() {
     return {
       username: this.username,
       email: this.email,
       role: this.role,
       createdAt: this.createdAt,
       isActive: this.isActive
     };
   }
   
   // 사용자 비활성화
   deactivate() {
     this.isActive = false;
     return `${this.username} 사용자가 비활성화되었습니다.`;
   }
   
   // 사용자 활성화
   activate() {
     this.isActive = true;
     return `${this.username} 사용자가 활성화되었습니다.`;
   }
   
   // 역할 변경
   changeRole(newRole) {
     this.role = newRole;
     return `${this.username}의 역할이 ${newRole}로 변경되었습니다.`;
   }
}

// 사용 예시
const user1 = new User('john_doe', 'john@example.com', 'admin');
const user2 = new User('jane_smith', 'jane@example.com');

console.log(user1.getInfo());
// {
//   username: 'john_doe',
//   email: 'john@example.com',
//   role: 'admin',
//   createdAt: 2024-01-15T10:30:00.000Z,
//   isActive: true
// }

console.log(user2.changeRole('moderator')); // "jane_smith의 역할이 moderator로 변경되었습니다."
console.log(user1.deactivate()); // "john_doe 사용자가 비활성화되었습니다."
```

---


- 객체 생성 시 초기값 설정
- 메서드를 통한 객체 상태 변경
- 계산된 속성명을 활용한 동적 메서드 생성
- 클래스 필드를 통한 기본값 설정

---

**참고 자료:** Inpa Dev - 자바스크립트 ES6 Class 문법 완벽 정리

- 객체 생성 시 초기값 설정
- 메서드를 통한 객체 상태 변경
- 계산된 속성명을 활용한 동적 메서드 생성
- 클래스 필드를 통한 기본값 설정

---

**참고 자료:** Inpa Dev - 자바스크립트 ES6 Class 문법 완벽 정리










## ES5 vs ES6 비교

### ES5 방식 (기존 프로토타입 문법)

```javascript
// 1. 생성자 함수 정의
function Person(name, age) {
   this.name = name;  // this는 새로 생성될 객체를 가리킴
   this.age = age;
}

// 2. 프로토타입에 메서드 추가
Person.prototype.introduce = function() {
   return `안녕하세요, 제 이름은 ${this.name}입니다.`;
};

// 3. 객체 생성 및 사용
const person = new Person('윤아준', 19);
console.log(person.introduce()); // "안녕하세요, 제 이름은 윤아준입니다."
```

**용어 설명:**
- **생성자 함수**: `new` 키워드와 함께 사용되어 객체를 생성하는 함수
- **프로토타입**: 객체가 공유하는 속성과 메서드를 저장하는 특별한 객체
- **this**: 현재 생성 중인 객체를 가리키는 키워드

### ES6 방식 (클래스 문법)

```javascript
// 1. 클래스 정의
class Person {
   // 2. 생성자 메서드 (객체 초기화)
   constructor(name, age) {
     this.name = name;
     this.age = age;
   }
   
   // 3. 클래스 메서드 정의
   introduce() {
     return `안녕하세요, 제 이름은 ${this.name}입니다.`;
   }
}

// 4. 객체 생성 및 사용
const person = new Person('윤아준', 19);
console.log(person.introduce()); // "안녕하세요, 제 이름은 윤아준입니다."
```

**용어 설명:**
- **class**: 객체를 생성하기 위한 템플릿을 정의하는 키워드
- **constructor**: 클래스의 생성자 메서드 (객체 생성 시 자동 호출)
- **메서드**: 클래스 내부에 정의된 함수

### "문법적 설탕"이라는 말의 한계

이 문서가 여러 번 말하는 "내부적으로는 프로토타입"은 맞지만, **두 코드가 같게 동작하지는 않는다.** 위 ES5 예제와 ES6 예제를 나란히 돌려 보면 네 군데가 다르다.

**1. 메서드의 열거 가능성.** 클래스 메서드는 `enumerable: false` 이고, 프로토타입에 대입한 메서드는 `true` 다.

```javascript
class C { m() {} }
function D() {}
D.prototype.m = function () {};

for (const k in new C()) console.log(k);   // 아무것도 안 찍힌다
for (const k in new D()) console.log(k);   // 'm'
```

옛 코드를 클래스로 옮기다 `for...in` 이나 `Object.assign` 으로 인스턴스를 복사하던 부분이 조용히 달라진다.

**2. 호이스팅.** 함수 선언은 정의 전에 쓸 수 있지만 클래스는 못 쓴다.

```javascript
new Later();      // ReferenceError: Cannot access 'Later' before initialization
class Later {}

hoisted();        // 동작한다
function hoisted() {}
```

파일 위쪽에서 아래 정의된 클래스를 참조하는 코드는, 그 참조가 **모듈 로드 시점**에 실행되면 터지고 함수 안에서 나중에 실행되면 멀쩡하다. 그래서 순환 import 가 얽히면 재현이 까다로운 에러가 된다.

**3. `new` 강제.** 클래스는 `new` 없이 호출하면 `TypeError` 다. 생성자 함수는 조용히 다른 일을 한다.

**4. 클래스 본문은 언제나 엄격 모드.** `"use strict"` 를 쓴 적이 없어도 그렇다.

문법만 바뀐 게 아니라 **기본값이 안전한 쪽으로 바뀐 것**에 가깝다.

### 계산된 메서드 이름의 두 가지

앞의 `[methodName]()` 예제에 딸린 성질이 둘 있다. 하나, 이름은 **클래스가 정의되는 시점에 한 번** 평가되고 그대로 굳는다.

```javascript
let mn = 'alpha';
class F { [mn]() { return 'x'; } }
mn = 'beta';
Object.getOwnPropertyNames(F.prototype);   // ['constructor', 'alpha']
```

변수를 바꿔도 메서드 이름은 따라오지 않는다. "동적"이라는 말이 실행 중에 바뀐다는 뜻은 아니다.

둘, 두 계산된 이름이 같은 값이 되면 **뒤엣것이 앞엣것을 조용히 덮는다.**

```javascript
const n1 = 'same', n2 = 'same';
class E {
  [n1]() { return 'first'; }
  [n2]() { return 'second'; }
}
new E().same();   // 'second'
```

상수 두 개가 우연히 같은 문자열이면 메서드 하나가 사라지는데 에러가 없다. 이름을 데이터에서 만들어 쓸 때는 중복 가능성을 먼저 확인해야 한다.

### getInfo 가 돌려주는 것은 복사본이 아니다

`User.getInfo()` 는 새 객체를 만들지만 **`createdAt` 은 같은 `Date` 인스턴스**를 가리킨다.

```javascript
const info = user.getInfo();
info.createdAt.setFullYear(1999);
user.createdAt.getFullYear();   // 1999 — 원본이 바뀌었다
```

"정보를 복사해서 돌려준다"고 읽히지만 얕은 복사라 참조형 필드는 그대로 새어 나간다. `Date` 는 변경 가능한 객체라 받는 쪽이 `setDate` 한 번만 불러도 원본이 오염된다. 넘길 때 `new Date(this.createdAt)` 로 새로 만들거나, 처음부터 문자열·숫자 타임스탬프로 들고 있는 편이 안전하다.

---

