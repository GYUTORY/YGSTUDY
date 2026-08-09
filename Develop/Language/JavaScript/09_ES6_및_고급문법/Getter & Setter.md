---
title: JavaScript Getter Setter
tags: [language, javascript]
updated: 2025-12-21
---
# JavaScript Getter & Setter

## 배경

### Getter & Setter란?
- **Getter**: 객체의 속성 값을 안전하게 가져오는 메서드
- **Setter**: 객체의 속성 값을 안전하게 설정하는 메서드
- 객체 지향 프로그래밍의 **캡슐화(Encapsulation)** 원칙을 구현하는 방법

### 왜 Getter & Setter를 사용할까?

#### 직접 접근 방식 (문제가 있는 코드)
```javascript
const user = {
    name: '김철수',
    age: 25
}

// 직접 접근 - 위험!
console.log(user.name); // 김철수
user.age = 999; // 나이에 999를 넣어도 아무 제한이 없음
```

#### Getter & Setter 방식 (안전한 코드)
```javascript
const user = {
    name: '김철수',
    age: 25,
    
    // Getter: 값을 안전하게 가져오기
    getName() {
        return this.name;
    },
    
    // Setter: 값을 안전하게 설정하기
    setAge(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this.age = newAge;
    }
}

console.log(user.getName()); // 김철수
user.setAge(999); // 나이는 0~150 사이여야 합니다.
```

```javascript
const user = {
    name: '김철수',
    age: 25
}

// 직접 접근 - 위험!
console.log(user.name); // 김철수
user.age = 999; // 나이에 999를 넣어도 아무 제한이 없음
```

```javascript
const 객체명 = {
    // 기존 속성들...
    
    get 속성명() {
        // 값을 반환하는 로직
        return this.실제속성명;
    },
    
    set 속성명(새값) {
        // 값을 검증하고 설정하는 로직
        this.실제속성명 = 새값;
    }
}
```

```javascript
const user = {
    _name: '김철수',    // 언더스코어(_)는 내부 속성임을 나타냄
    _age: 25,
    
    // name에 대한 getter
    get name() {
        return this._name;
    },
    
    // name에 대한 setter
    set name(newName) {
        if (typeof newName !== 'string' || newName.length < 2) {
            console.error('이름은 2글자 이상의 문자열이어야 합니다.');
            return;
        }
        this._name = newName;
    },
    
    // age에 대한 getter
    get age() {
        return this._age;
    },
    
    // age에 대한 setter
    set age(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this._age = newAge;
    }
}
```

```javascript
// Getter 사용 - 함수 호출이 아닌 속성처럼 접근
console.log(user.name); // 김철수
console.log(user.age);  // 25

// Setter 사용 - 함수 호출이 아닌 할당처럼 사용
user.name = '박영희';    // 정상 설정
user.age = 30;          // 정상 설정

user.name = 'A';        // 이름은 2글자 이상의 문자열이어야 합니다.
user.age = 999;         // 나이는 0~150 사이여야 합니다.
```


### 1. 가상 속성 (Virtual Property)
- `name`과 `age`는 실제로는 존재하지 않는 가상의 속성
- 내부적으로는 `_name`, `_age`에 실제 데이터가 저장됨
- 사용자는 마치 일반 속성처럼 사용할 수 있음

### 2. 데이터 검증 (Validation)
```javascript
const bankAccount = {
    _balance: 1000,
    
    get balance() {
        return this._balance;
    },
    
    set balance(amount) {
        if (amount < 0) {
            console.error('잔액은 음수가 될 수 없습니다.');
            return;
        }
        this._balance = amount;
    }
}

bankAccount.balance = -500; // 잔액은 음수가 될 수 없습니다.
console.log(bankAccount.balance); // 1000 (변경되지 않음)
```

### 3. 계산된 속성 (Computed Property)
```javascript
const rectangle = {
    _width: 10,
    _height: 5,
    
    get area() {
        return this._width * this._height;
    },
    
    get perimeter() {
        return 2 * (this._width + this._height);
    }
}

console.log(rectangle.area);      // 50
console.log(rectangle.perimeter); // 30
```


### 1. 무한 루프 방지
```javascript
const user = {
    _name: '김철수',
    
    // ❌ 잘못된 예 - 무한 루프 발생
    get name() {
        return this.name; // this.name을 호출하면 다시 getter가 실행됨
    },
    
    // ✅ 올바른 예
    get name() {
        return this._name; // 내부 속성에 접근
    }
}
```

### 2. Getter만 정의한 경우
```javascript
const user = {
    _name: '김철수',
    
    get name() {
        return this._name;
    }
    // setter가 없으면 읽기 전용 속성이 됨
}

console.log(user.name); // 김철수
user.name = '박영희';    // 에러는 발생하지 않지만 값이 변경되지 않음
console.log(user.name); // 여전히 김철수
```


### 사용자 프로필 관리
```javascript
const userProfile = {
    _email: '',
    _password: '',
    _age: 0,
    
    // 이메일 getter/setter
    get email() {
        return this._email;
    },
    
    set email(newEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newEmail)) {
            console.error('올바른 이메일 형식이 아닙니다.');
            return;
        }
        this._email = newEmail;
    },
    
    // 비밀번호 getter/setter
    get password() {
        return '*'.repeat(this._password.length); // 보안을 위해 마스킹
    },
    
    set password(newPassword) {
        if (newPassword.length < 8) {
            console.error('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        this._password = newPassword;
    },
    
    // 나이 getter/setter
    get age() {
        return this._age;
    },
    
    set age(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this._age = newAge;
    }
}

// 사용 예시
userProfile.email = 'test@example.com';     // 정상
userProfile.email = 'invalid-email';        // 올바른 이메일 형식이 아닙니다.
userProfile.password = '12345678';          // 정상
userProfile.password = '123';               // 비밀번호는 8자 이상이어야 합니다.
userProfile.age = 25;                       // 정상

console.log(userProfile.email);    // test@example.com
console.log(userProfile.password); // ********
console.log(userProfile.age);      // 25
```

---

**참고 자료**: Inpa Dev - Getter & Setter

```javascript
const userProfile = {
    _email: '',
    _password: '',
    _age: 0,
    
    // 이메일 getter/setter
    get email() {
        return this._email;
    },
    
    set email(newEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newEmail)) {
            console.error('올바른 이메일 형식이 아닙니다.');
            return;
        }
        this._email = newEmail;
    },
    
    // 비밀번호 getter/setter
    get password() {
        return '*'.repeat(this._password.length); // 보안을 위해 마스킹
    },
    
    set password(newPassword) {
        if (newPassword.length < 8) {
            console.error('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        this._password = newPassword;
    },
    
    // 나이 getter/setter
    get age() {
        return this._age;
    },
    
    set age(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this._age = newAge;
    }
}

// 사용 예시
userProfile.email = 'test@example.com';     // 정상
userProfile.email = 'invalid-email';        // 올바른 이메일 형식이 아닙니다.
userProfile.password = '12345678';          // 정상
userProfile.password = '123';               // 비밀번호는 8자 이상이어야 합니다.
userProfile.age = 25;                       // 정상

console.log(userProfile.email);    // test@example.com
console.log(userProfile.password); // ********
console.log(userProfile.age);      // 25
```

---

**참고 자료**: Inpa Dev - Getter & Setter






```javascript
const user = {
    name: '김철수',
    age: 25
}

// 직접 접근 - 위험!
console.log(user.name); // 김철수
user.age = 999; // 나이에 999를 넣어도 아무 제한이 없음
```

```javascript
const userProfile = {
    _email: '',
    _password: '',
    _age: 0,
    
    // 이메일 getter/setter
    get email() {
        return this._email;
    },
    
    set email(newEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newEmail)) {
            console.error('올바른 이메일 형식이 아닙니다.');
            return;
        }
        this._email = newEmail;
    },
    
    // 비밀번호 getter/setter
    get password() {
        return '*'.repeat(this._password.length); // 보안을 위해 마스킹
    },
    
    set password(newPassword) {
        if (newPassword.length < 8) {
            console.error('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        this._password = newPassword;
    },
    
    // 나이 getter/setter
    get age() {
        return this._age;
    },
    
    set age(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this._age = newAge;
    }
}

// 사용 예시
userProfile.email = 'test@example.com';     // 정상
userProfile.email = 'invalid-email';        // 올바른 이메일 형식이 아닙니다.
userProfile.password = '12345678';          // 정상
userProfile.password = '123';               // 비밀번호는 8자 이상이어야 합니다.
userProfile.age = 25;                       // 정상

console.log(userProfile.email);    // test@example.com
console.log(userProfile.password); // ********
console.log(userProfile.age);      // 25
```

---

**참고 자료**: Inpa Dev - Getter & Setter

```javascript
const userProfile = {
    _email: '',
    _password: '',
    _age: 0,
    
    // 이메일 getter/setter
    get email() {
        return this._email;
    },
    
    set email(newEmail) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(newEmail)) {
            console.error('올바른 이메일 형식이 아닙니다.');
            return;
        }
        this._email = newEmail;
    },
    
    // 비밀번호 getter/setter
    get password() {
        return '*'.repeat(this._password.length); // 보안을 위해 마스킹
    },
    
    set password(newPassword) {
        if (newPassword.length < 8) {
            console.error('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        this._password = newPassword;
    },
    
    // 나이 getter/setter
    get age() {
        return this._age;
    },
    
    set age(newAge) {
        if (newAge < 0 || newAge > 150) {
            console.error('나이는 0~150 사이여야 합니다.');
            return;
        }
        this._age = newAge;
    }
}

// 사용 예시
userProfile.email = 'test@example.com';     // 정상
userProfile.email = 'invalid-email';        // 올바른 이메일 형식이 아닙니다.
userProfile.password = '12345678';          // 정상
userProfile.password = '123';               // 비밀번호는 8자 이상이어야 합니다.
userProfile.age = 25;                       // 정상

console.log(userProfile.email);    // test@example.com
console.log(userProfile.password); // ********
console.log(userProfile.age);      // 25
```

---

**참고 자료**: Inpa Dev - Getter & Setter










## ES6 Getter & Setter 문법

