

# JavaScript Builder 패턴

## 1️⃣ Builder 패턴이란?
**Builder 패턴**은 **객체를 단계적으로 생성할 수 있도록 도와주는 디자인 패턴**입니다.  
객체의 생성 과정이 복잡할 때, **생성 로직을 분리하여 더 읽기 쉽고 유지보수하기 쉽게 만듭니다.**

> **👉🏻 Builder 패턴은 특히 옵션이 많은 객체를 만들 때 유용합니다.**

---

## 2️⃣ 왜 Builder 패턴을 사용할까?

### ✅ 객체 생성의 복잡성 해결
```javascript
const user1 = {
    name: "Alice",
    age: 25,
    email: "alice@example.com",
    address: "Seoul",
    phone: "010-1234-5678",
};
```
> **👉🏻 위처럼 직접 객체를 생성하면, 속성이 많아질수록 코드가 지저분해지고 유지보수가 어려워집니다.**

✅ **Builder 패턴을 사용하면 더 깔끔한 방식으로 객체를 생성할 수 있습니다.**

---

## 3️⃣ 기본적인 Builder 패턴 구현

### ✨ 클래스를 이용한 Builder 패턴
```javascript
class UserBuilder {
    constructor(name) {
        this.name = name; // 필수 값
    }

    setAge(age) {
        this.age = age;
        return this; // 메서드 체이닝 지원
    }

    setEmail(email) {
        this.email = email;
        return this;
    }

    setAddress(address) {
        this.address = address;
        return this;
    }

    build() {
        return new User(this);
    }
}

class User {
    constructor(builder) {
        this.name = builder.name;
        this.age = builder.age;
        this.email = builder.email;
        this.address = builder.address;
    }

    display() {
        console.log(`User: ${this.name}, Age: ${this.age}, Email: ${this.email}, Address: ${this.address}`);
    }
}

const user = new UserBuilder("Alice")
    .setAge(25)
    .setEmail("alice@example.com")
    .setAddress("Seoul")
    .build();

user.display(); // User: Alice, Age: 25, Email: alice@example.com, Address: Seoul
```

> **👉🏻 `UserBuilder`를 사용하여 단계적으로 객체를 생성할 수 있습니다.**

✅ **메서드 체이닝을 활용하면 코드가 더 간결해집니다.**

---

## 4️⃣ 함수형 Builder 패턴 구현

클래스를 사용하지 않고, **함수형 방식으로도 Builder 패턴을 구현할 수 있습니다.**

```javascript
function createUser(name) {
    const user = { name };

    return {
        setAge(age) {
            user.age = age;
            return this;
        },
        setEmail(email) {
            user.email = email;
            return this;
        },
        setAddress(address) {
            user.address = address;
            return this;
        },
        build() {
            return user;
        },
    };
}

const user = createUser("Bob")
    .setAge(30)
    .setEmail("bob@example.com")
    .setAddress("Busan")
    .build();

console.log(user);
// { name: 'Bob', age: 30, email: 'bob@example.com', address: 'Busan' }
```

> **👉🏻 함수형 방식도 동일한 메서드 체이닝을 지원합니다.**

---

## 5️⃣ Builder 패턴의 장점과 단점

| 장점 | 단점 |
|------|------|
| 객체 생성 과정을 단계적으로 관리 가능 | 코드가 다소 길어질 수 있음 |
| 선택적 매개변수를 쉽게 설정 가능 | 작은 객체에는 불필요할 수 있음 |
| 가독성이 높고 유지보수가 쉬움 | 초기 학습이 필요함 |

> **👉🏻 특히 옵션이 많은 객체를 생성할 때 유용합니다!**

---

## 6️⃣ 실제 사용 사례

### ✅ 1. HTTP 요청 생성기
```javascript
class RequestBuilder {
    constructor(url) {
        this.url = url;
        this.method = "GET"; // 기본값
        this.headers = {};
        this.body = null;
    }

    setMethod(method) {
        this.method = method;
        return this;
    }

    setHeaders(headers) {
        this.headers = headers;
        return this;
    }

    setBody(body) {
        this.body = body;
        return this;
    }

    build() {
        return fetch(this.url, {
            method: this.method,
            headers: this.headers,
            body: this.body,
        });
    }
}

// 요청 생성 및 실행
new RequestBuilder("https://api.example.com/data")
    .setMethod("POST")
    .setHeaders({ "Content-Type": "application/json" })
    .setBody(JSON.stringify({ key: "value" }))
    .build()
    .then(response => response.json())
    .then(data => console.log(data));
```
