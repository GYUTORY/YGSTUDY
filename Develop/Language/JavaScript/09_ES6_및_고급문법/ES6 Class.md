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

---

