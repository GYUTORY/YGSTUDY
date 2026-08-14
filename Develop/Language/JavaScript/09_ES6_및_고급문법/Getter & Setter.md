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

이 예제 자체가 함정을 하나 더 보여준다. **같은 객체 리터럴에 `get name` 이 두 번 있으면 뒤엣것이 앞엣것을 조용히 덮는다.**

```javascript
const u = {
  _name: '김철수',
  get name() { return this.name; },    // ← 이 정의는 사라진다
  get name() { return this._name; }
};
u.name;   // '김철수' — 무한 루프는 일어나지 않는다
```

에러도 경고도 없다. 그래서 "잘못된 예"가 실제로는 실행되지 않고, 이 코드를 붙여넣어 무한 루프를 재현해 보려던 사람은 아무 일도 안 일어나는 것을 보게 된다. 진짜로 재현하려면 잘못된 정의 하나만 남겨야 한다.

```javascript
const bad = { get name() { return this.name; } };
bad.name;
// RangeError: Maximum call stack size exceeded
```

중복 키가 조용히 덮이는 것은 getter 만의 얘기가 아니다. 평범한 속성도 마찬가지고, 엄격 모드에서도 에러가 아니다. 설정 객체가 길어지면 같은 키를 두 번 쓰고도 모른 채 지나가기 쉽다 — ESLint 의 `no-dupe-keys` 같은 정적 검사에 맡기는 수밖에 없다.

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

"에러는 발생하지 않지만"은 **비엄격 모드에서만** 맞다. ES 모듈이나 클래스 안에서는 던진다.

```javascript
// 모듈 파일(엄격 모드)
const g = { _n: '김철수', get name() { return this._n; } };
g.name = '박영희';
// TypeError: Cannot set property name of #<Object> which has only a getter
```

문제는 조용히 실패하는 쪽이다. 대입은 실패했는데 **대입식의 값은 대입하려던 그 값**이라, 반환값으로 성공 여부를 판단할 수 없다.

```javascript
const result = (g.name = '박영희');
result;    // '박영희'   ← 성공한 것처럼 보인다
g.name;    // '김철수'   ← 실제로는 안 바뀌었다
```

이 문서의 setter 들도 같은 형태다. 검증에 걸리면 `console.error` 를 찍고 `return` 하는데, 호출부 입장에서는 성공과 실패가 구분되지 않는다.

```javascript
user.age = 999;    // 콘솔에는 에러가 찍히지만 코드 흐름은 그대로 이어진다
```

setter 안에서는 반환값으로 알릴 방법이 없으니, 정말 막아야 하는 값이면 **던져야** 한다. `throw new RangeError('나이는 0~150')` 이면 호출부가 `try/catch` 로 다룰 수 있다. 로그만 남기고 넘어가면 잘못된 값이 들어간 줄 모른 채 다음 단계로 간다.

setter 로 검증하는 접근 자체의 한계도 있다. 이 문서 앞쪽 `getName`/`setAge` 예제에서 `age` 는 여전히 평범한 공개 속성이라 `user.age = 999` 한 줄로 우회된다. 검증을 강제하려면 값을 밖에서 못 건드리게 해야 하고, 그 자리에 있는 것이 `#private` 필드다.


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










## 언더스코어는 접근 제어가 아니다

위 `userProfile` 의 `get password()` 마스킹은 **보안이 아니다.** `_password` 가 평범한 속성으로 옆에 그대로 남아 있어서, 객체를 통째로 다루는 순간 원문이 나온다.

```javascript
JSON.stringify(userProfile);
// {"_password":"hunter2xyz","password":"**********","_email":"a@b.c","email":"a@b.c"}

{ ...userProfile };
// { _password: 'hunter2xyz', password: '**********', _email: 'a@b.c', email: 'a@b.c' }
```

마스킹한 값과 원문이 **나란히** 들어간다. 이 객체가 API 응답이나 에러 로그로 나가면 비밀번호가 그대로 실려 나간다. 마스킹을 해 뒀다는 사실이 오히려 "가려져 있다"는 착각을 만들어서 아무도 다시 확인하지 않는다.

여기서 두 가지가 같이 보인다.

**하나, 언더스코어 접두사는 약속일 뿐이다.** `userProfile._password` 는 누구나 읽고 쓸 수 있다. 진짜로 감추려면 클래스의 private 필드를 쓴다. `#` 필드는 클래스 밖에서 접근하면 문법 에러이고, `JSON.stringify` 와 스프레드에도 나오지 않는다.

```javascript
class Profile {
  #password = '';
  set password(v) {
    if (v.length < 8) throw new RangeError('비밀번호는 8자 이상');
    this.#password = v;
  }
  get masked() { return '*'.repeat(this.#password.length); }
}

const p = new Profile();
p.password = 'hunter2xyz';
JSON.stringify(p);   // '{}'   — 새어 나갈 것이 없다
```

**둘, `JSON.stringify` 와 스프레드는 getter 를 호출한다.** 위 출력의 `"password":"**********"` 가 그 결과다. getter 가 계산 비용이 크거나 부수 효과가 있으면 객체를 로그로 찍는 것만으로 그게 실행된다. `console.log` 로 값을 들여다보다 상태가 바뀌는 코드는 원인을 찾기 극도로 어렵다. **getter 안에서는 아무것도 바꾸지 않는다**를 규칙으로 두는 편이 낫다.

## ES6 Getter & Setter 문법

