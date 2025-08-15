---
title: JavaScript static
tags: [language, javascript, 08oop및디자인패턴, static, java]
updated: 2025-08-10
---
# JavaScript static 

## 배경
`static` 키워드는 클래스에서 **인스턴스 없이도 호출할 수 있는 메서드나 속성**을 정의할 때 사용합니다. 

### 🔍 핵심 개념
- **정적(Static)**: "고정된", "변하지 않는"이라는 의미
- **인스턴스**: 클래스로부터 생성된 객체
- **유틸리티 함수**: 자주 사용되는 도구 함수들

---

- **정적(Static)**: "고정된", "변하지 않는"이라는 의미
- **인스턴스**: 클래스로부터 생성된 객체
- **유틸리티 함수**: 자주 사용되는 도구 함수들

---


### 정적 속성과 메서드 정의
```javascript
class MathUtils {
  // 정적 속성
  static PI = 3.14159;
  
  // 정적 메서드
  static add(a, b) {
    return a + b;
  }
  
  // 정적 초기화 블록 (클래스가 로드될 때 한 번만 실행)
  static {
    console.log('MathUtils 클래스가 로드되었습니다.');
  }
}

// 사용법
console.log(MathUtils.PI);        // 3.14159
console.log(MathUtils.add(5, 3)); // 8
```

**실행 결과:**
```
MathUtils 클래스가 로드되었습니다.
3.14159
8
```

---

```javascript
class MathUtils {
  // 정적 속성
  static PI = 3.14159;
  
  // 정적 메서드
  static add(a, b) {
    return a + b;
  }
  
  // 정적 초기화 블록 (클래스가 로드될 때 한 번만 실행)
  static {
    console.log('MathUtils 클래스가 로드되었습니다.');
  }
}

// 사용법
console.log(MathUtils.PI);        // 3.14159
console.log(MathUtils.add(5, 3)); // 8
```

**실행 결과:**
```
MathUtils 클래스가 로드되었습니다.
3.14159
8
```

---

```javascript
class Calculator {
  static multiply(a, b) {
    return a * b;
  }
}

// 인스턴스 없이 직접 호출
console.log(Calculator.multiply(4, 5)); // 20
```

```javascript
class Calculator {
  constructor() {
    this.result = 0;
  }
  
  add(a) {
    this.result += a;
    return this.result;
  }
}

// 인스턴스를 생성해야 호출 가능
const calc = new Calculator();
console.log(calc.add(10)); // 10
```

---


같은 클래스 내의 정적 메서드들은 `this` 키워드로 서로를 호출할 수 있습니다.

```javascript
class StringUtils {
  static toUpperCase(str) {
    return str.toUpperCase();
  }
  
  static toLowerCase(str) {
    return str.toLowerCase();
  }
  
  // 다른 정적 메서드 호출
  static processText(str, operation) {
    if (operation === 'upper') {
      return this.toUpperCase(str);
    } else if (operation === 'lower') {
      return this.toLowerCase(str);
    }
    return str;
  }
}

console.log(StringUtils.processText('Hello World', 'upper')); // HELLO WORLD
console.log(StringUtils.processText('Hello World', 'lower')); // hello world
```

---


정적 메서드도 상속이 가능하며, `super` 키워드로 부모 클래스의 정적 메서드를 호출할 수 있습니다.

```javascript
class Shape {
  static getArea(width, height) {
    return width * height;
  }
  
  static getPerimeter(width, height) {
    return 2 * (width + height);
  }
}

class Rectangle extends Shape {
  // 부모의 정적 메서드를 오버라이드
  static getArea(width, height) {
    return super.getArea(width, height);
  }
  
  // 새로운 정적 메서드 추가
  static isSquare(width, height) {
    return width === height;
  }
}

console.log(Shape.getArea(5, 3));        // 15
console.log(Rectangle.getArea(5, 3));    // 15 (상속받음)
console.log(Rectangle.isSquare(5, 5));   // true
console.log(Rectangle.isSquare(5, 3));   // false
```

---


### 1. 인스턴스에서 정적 메서드 호출 불가
```javascript
class Example {
  static staticMethod() {
    return '정적 메서드입니다.';
  }
  
  instanceMethod() {
    return '인스턴스 메서드입니다.';
  }
}

const example = new Example();

// ❌ 오류 발생
// console.log(example.staticMethod()); 

// ✅ 올바른 방법
console.log(Example.staticMethod()); // 정적 메서드입니다.

// ✅ 인스턴스 메서드는 정상 호출
console.log(example.instanceMethod()); // 인스턴스 메서드입니다.
```

### 2. 정적 메서드에서 인스턴스 속성 접근 불가
```javascript
class User {
  constructor(name) {
    this.name = name; // 인스턴스 속성
  }
  
  static createUser(name) {
    // ❌ this.name으로 접근 불가 (this는 클래스 자체를 가리킴)
    return new User(name);
  }
  
  static getClassName() {
    return this.name; // ✅ 클래스 이름 반환
  }
}

const user = User.createUser('김철수');
console.log(user.name);           // 김철수
console.log(User.getClassName()); // User
```

---


### 1. 유틸리티 클래스
```javascript
class DateUtils {
  static formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  static isToday(date) {
    const today = new Date();
    return this.formatDate(date) === this.formatDate(today);
  }
  
  static getDaysBetween(date1, date2) {
    const timeDiff = Math.abs(date2.getTime() - date1.getTime());
    return Math.ceil(timeDiff / (1000 * 3600 * 24));
  }
}

const today = new Date();
const yesterday = new Date(today);
yesterday.setDate(yesterday.getDate() - 1);

console.log(DateUtils.formatDate(today));           // 2024-01-15
console.log(DateUtils.isToday(today));              // true
console.log(DateUtils.getDaysBetween(today, yesterday)); // 1
```

### 2. 설정 관리
```javascript
class Config {
  static API_BASE_URL = 'https://api.example.com';
  static VERSION = '1.0.0';
  
  static getFullUrl(endpoint) {
    return `${this.API_BASE_URL}/${endpoint}`;
  }
  
  static isDevelopment() {
    return process.env.NODE_ENV === 'development';
  }
}

console.log(Config.getFullUrl('users')); // https://api.example.com/users
console.log(Config.VERSION);             // 1.0.0
```

---


### ✅ 정적 메서드가 적합한 경우
- **유틸리티 함수**: 수학 계산, 날짜 처리, 문자열 변환 등
- **팩토리 메서드**: 객체 생성 로직
- **설정 관리**: 앱 설정, 상수 값들
- **순수 함수**: 입력에 따른 출력이 항상 동일한 함수

### ❌ 정적 메서드가 부적합한 경우
- **상태 관리**: 인스턴스별로 다른 값을 가져야 하는 경우
- **인스턴스 속성 접근**: `this`를 통해 인스턴스 데이터에 접근해야 하는 경우
- **인스턴스 메서드 호출**: 다른 인스턴스 메서드를 호출해야 하는 경우

---

- **유틸리티 함수**: 수학 계산, 날짜 처리, 문자열 변환 등
- **팩토리 메서드**: 객체 생성 로직
- **설정 관리**: 앱 설정, 상수 값들
- **순수 함수**: 입력에 따른 출력이 항상 동일한 함수

- **상태 관리**: 인스턴스별로 다른 값을 가져야 하는 경우
- **인스턴스 속성 접근**: `this`를 통해 인스턴스 데이터에 접근해야 하는 경우
- **인스턴스 메서드 호출**: 다른 인스턴스 메서드를 호출해야 하는 경우

---


### 정적 getter/setter
```javascript
class Settings {
  static _theme = 'light';
  
  static get theme() {
    return this._theme;
  }
  
  static set theme(value) {
    if (['light', 'dark'].includes(value)) {
      this._theme = value;
    } else {
      throw new Error('테마는 light 또는 dark여야 합니다.');
    }
  }
}

console.log(Settings.theme); // light
Settings.theme = 'dark';
console.log(Settings.theme); // dark
```

### 정적 메서드와 프라이빗 필드
```javascript
class BankAccount {
  static #accounts = [];
  
  constructor(accountNumber, balance) {
    this.accountNumber = accountNumber;
    this.balance = balance;
    BankAccount.#accounts.push(this);
  }
  
  static getTotalAccounts() {
    return this.#accounts.length;
  }
  
  static getAccountByNumber(accountNumber) {
    return this.#accounts.find(account => account.accountNumber === accountNumber);
  }
}

const account1 = new BankAccount('001', 1000);
const account2 = new BankAccount('002', 2000);

console.log(BankAccount.getTotalAccounts());        // 2
console.log(BankAccount.getAccountByNumber('001')); // BankAccount { accountNumber: '001', balance: 1000 }
```

```javascript
class BankAccount {
  static #accounts = [];
  
  constructor(accountNumber, balance) {
    this.accountNumber = accountNumber;
    this.balance = balance;
    BankAccount.#accounts.push(this);
  }
  
  static getTotalAccounts() {
    return this.#accounts.length;
  }
  
  static getAccountByNumber(accountNumber) {
    return this.#accounts.find(account => account.accountNumber === accountNumber);
  }
}

const account1 = new BankAccount('001', 1000);
const account2 = new BankAccount('002', 2000);

console.log(BankAccount.getTotalAccounts());        // 2
console.log(BankAccount.getAccountByNumber('001')); // BankAccount { accountNumber: '001', balance: 1000 }
```






- **정적(Static)**: "고정된", "변하지 않는"이라는 의미
- **인스턴스**: 클래스로부터 생성된 객체
- **유틸리티 함수**: 자주 사용되는 도구 함수들

---

- **정적(Static)**: "고정된", "변하지 않는"이라는 의미
- **인스턴스**: 클래스로부터 생성된 객체
- **유틸리티 함수**: 자주 사용되는 도구 함수들

---


```javascript
class MathUtils {
  // 정적 속성
  static PI = 3.14159;
  
  // 정적 메서드
  static add(a, b) {
    return a + b;
  }
  
  // 정적 초기화 블록 (클래스가 로드될 때 한 번만 실행)
  static {
    console.log('MathUtils 클래스가 로드되었습니다.');
  }
}

// 사용법
console.log(MathUtils.PI);        // 3.14159
console.log(MathUtils.add(5, 3)); // 8
```

**실행 결과:**
```
MathUtils 클래스가 로드되었습니다.
3.14159
8
```

---

```javascript
class MathUtils {
  // 정적 속성
  static PI = 3.14159;
  
  // 정적 메서드
  static add(a, b) {
    return a + b;
  }
  
  // 정적 초기화 블록 (클래스가 로드될 때 한 번만 실행)
  static {
    console.log('MathUtils 클래스가 로드되었습니다.');
  }
}

// 사용법
console.log(MathUtils.PI);        // 3.14159
console.log(MathUtils.add(5, 3)); // 8
```

**실행 결과:**
```
MathUtils 클래스가 로드되었습니다.
3.14159
8
```

---

```javascript
class Calculator {
  static multiply(a, b) {
    return a * b;
  }
}

// 인스턴스 없이 직접 호출
console.log(Calculator.multiply(4, 5)); // 20
```

```javascript
class Calculator {
  constructor() {
    this.result = 0;
  }
  
  add(a) {
    this.result += a;
    return this.result;
  }
}

// 인스턴스를 생성해야 호출 가능
const calc = new Calculator();
console.log(calc.add(10)); // 10
```

---


같은 클래스 내의 정적 메서드들은 `this` 키워드로 서로를 호출할 수 있습니다.

```javascript
class StringUtils {
  static toUpperCase(str) {
    return str.toUpperCase();
  }
  
  static toLowerCase(str) {
    return str.toLowerCase();
  }
  
  // 다른 정적 메서드 호출
  static processText(str, operation) {
    if (operation === 'upper') {
      return this.toUpperCase(str);
    } else if (operation === 'lower') {
      return this.toLowerCase(str);
    }
    return str;
  }
}

console.log(StringUtils.processText('Hello World', 'upper')); // HELLO WORLD
console.log(StringUtils.processText('Hello World', 'lower')); // hello world
```

---


정적 메서드도 상속이 가능하며, `super` 키워드로 부모 클래스의 정적 메서드를 호출할 수 있습니다.

```javascript
class Shape {
  static getArea(width, height) {
    return width * height;
  }
  
  static getPerimeter(width, height) {
    return 2 * (width + height);
  }
}

class Rectangle extends Shape {
  // 부모의 정적 메서드를 오버라이드
  static getArea(width, height) {
    return super.getArea(width, height);
  }
  
  // 새로운 정적 메서드 추가
  static isSquare(width, height) {
    return width === height;
  }
}

console.log(Shape.getArea(5, 3));        // 15
console.log(Rectangle.getArea(5, 3));    // 15 (상속받음)
console.log(Rectangle.isSquare(5, 5));   // true
console.log(Rectangle.isSquare(5, 3));   // false
```

---


- **유틸리티 함수**: 수학 계산, 날짜 처리, 문자열 변환 등
- **팩토리 메서드**: 객체 생성 로직
- **설정 관리**: 앱 설정, 상수 값들
- **순수 함수**: 입력에 따른 출력이 항상 동일한 함수

- **상태 관리**: 인스턴스별로 다른 값을 가져야 하는 경우
- **인스턴스 속성 접근**: `this`를 통해 인스턴스 데이터에 접근해야 하는 경우
- **인스턴스 메서드 호출**: 다른 인스턴스 메서드를 호출해야 하는 경우

---

- **유틸리티 함수**: 수학 계산, 날짜 처리, 문자열 변환 등
- **팩토리 메서드**: 객체 생성 로직
- **설정 관리**: 앱 설정, 상수 값들
- **순수 함수**: 입력에 따른 출력이 항상 동일한 함수

- **상태 관리**: 인스턴스별로 다른 값을 가져야 하는 경우
- **인스턴스 속성 접근**: `this`를 통해 인스턴스 데이터에 접근해야 하는 경우
- **인스턴스 메서드 호출**: 다른 인스턴스 메서드를 호출해야 하는 경우

---


```javascript
class BankAccount {
  static #accounts = [];
  
  constructor(accountNumber, balance) {
    this.accountNumber = accountNumber;
    this.balance = balance;
    BankAccount.#accounts.push(this);
  }
  
  static getTotalAccounts() {
    return this.#accounts.length;
  }
  
  static getAccountByNumber(accountNumber) {
    return this.#accounts.find(account => account.accountNumber === accountNumber);
  }
}

const account1 = new BankAccount('001', 1000);
const account2 = new BankAccount('002', 2000);

console.log(BankAccount.getTotalAccounts());        // 2
console.log(BankAccount.getAccountByNumber('001')); // BankAccount { accountNumber: '001', balance: 1000 }
```

```javascript
class BankAccount {
  static #accounts = [];
  
  constructor(accountNumber, balance) {
    this.accountNumber = accountNumber;
    this.balance = balance;
    BankAccount.#accounts.push(this);
  }
  
  static getTotalAccounts() {
    return this.#accounts.length;
  }
  
  static getAccountByNumber(accountNumber) {
    return this.#accounts.find(account => account.accountNumber === accountNumber);
  }
}

const account1 = new BankAccount('001', 1000);
const account2 = new BankAccount('002', 2000);

console.log(BankAccount.getTotalAccounts());        // 2
console.log(BankAccount.getAccountByNumber('001')); // BankAccount { accountNumber: '001', balance: 1000 }
```










## ⚡ 정적 vs 인스턴스 메서드 비교

