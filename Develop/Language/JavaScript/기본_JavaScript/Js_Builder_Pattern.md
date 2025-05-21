# JavaScript Builder 패턴

## 1️⃣ Builder 패턴이란?
**Builder 패턴**은 **객체를 단계적으로 생성할 수 있도록 도와주는 디자인 패턴**입니다.  
객체의 생성 과정이 복잡할 때, **생성 로직을 분리하여 더 읽기 쉽고 유지보수하기 쉽게 만듭니다.**

> **👉🏻 Builder 패턴은 특히 옵션이 많은 객체를 만들 때 유용합니다.**

### 🔍 Builder 패턴의 핵심 개념
1. **단계적 생성**: 객체를 한 번에 생성하는 대신, 여러 단계를 거쳐 생성합니다.
2. **유연성**: 선택적 매개변수를 쉽게 설정할 수 있습니다.
3. **가독성**: 메서드 체이닝을 통해 코드의 의도를 명확하게 표현할 수 있습니다.
4. **유지보수성**: 객체 생성 로직을 분리하여 코드의 유지보수가 용이합니다.

---

## 2️⃣ 왜 Builder 패턴을 사용할까?

### ✅ 객체 생성의 복잡성 해결
```javascript
// 일반적인 객체 생성 방식
const user1 = {
    name: "Alice",
    age: 25,
    email: "alice@example.com",
    address: "Seoul",
    phone: "010-1234-5678",
    role: "admin",
    permissions: ["read", "write", "delete"],
    settings: {
        theme: "dark",
        notifications: true,
        language: "ko"
    }
};

// Builder 패턴을 사용한 객체 생성
const user2 = new UserBuilder("Alice")
    .setAge(25)
    .setEmail("alice@example.com")
    .setAddress("Seoul")
    .setPhone("010-1234-5678")
    .setRole("admin")
    .setPermissions(["read", "write", "delete"])
    .setSettings({
        theme: "dark",
        notifications: true,
        language: "ko"
    })
    .build();
```

> **👉🏻 위처럼 직접 객체를 생성하면, 속성이 많아질수록 코드가 지저분해지고 유지보수가 어려워집니다.**

### 🔍 Builder 패턴의 장점
1. **명확한 의도**: 각 속성의 설정이 명확하게 구분됩니다.
2. **유연한 확장**: 새로운 속성을 추가하기 쉽습니다.
3. **타입 안정성**: 각 단계에서 타입 체크가 가능합니다.
4. **재사용성**: 동일한 생성 로직을 여러 곳에서 재사용할 수 있습니다.

---

## 3️⃣ 기본적인 Builder 패턴 구현

### ✨ 클래스를 이용한 Builder 패턴
```javascript
class UserBuilder {
    constructor(name) {
        this.name = name; // 필수 값
        this.age = null;
        this.email = null;
        this.address = null;
        this.phone = null;
        this.role = "user"; // 기본값 설정
        this.permissions = [];
        this.settings = {};
    }

    setAge(age) {
        if (age < 0 || age > 150) {
            throw new Error("Invalid age");
        }
        this.age = age;
        return this;
    }

    setEmail(email) {
        if (!email.includes("@")) {
            throw new Error("Invalid email");
        }
        this.email = email;
        return this;
    }

    setAddress(address) {
        this.address = address;
        return this;
    }

    setPhone(phone) {
        if (!/^\d{3}-\d{4}-\d{4}$/.test(phone)) {
            throw new Error("Invalid phone number");
        }
        this.phone = phone;
        return this;
    }

    setRole(role) {
        const validRoles = ["user", "admin", "manager"];
        if (!validRoles.includes(role)) {
            throw new Error("Invalid role");
        }
        this.role = role;
        return this;
    }

    setPermissions(permissions) {
        this.permissions = permissions;
        return this;
    }

    setSettings(settings) {
        this.settings = { ...this.settings, ...settings };
        return this;
    }

    build() {
        // 필수 값 검증
        if (!this.name) {
            throw new Error("Name is required");
        }
        return new User(this);
    }
}

class User {
    constructor(builder) {
        this.name = builder.name;
        this.age = builder.age;
        this.email = builder.email;
        this.address = builder.address;
        this.phone = builder.phone;
        this.role = builder.role;
        this.permissions = builder.permissions;
        this.settings = builder.settings;
    }

    display() {
        console.log(`
            User Information:
            Name: ${this.name}
            Age: ${this.age}
            Email: ${this.email}
            Address: ${this.address}
            Phone: ${this.phone}
            Role: ${this.role}
            Permissions: ${this.permissions.join(", ")}
            Settings: ${JSON.stringify(this.settings, null, 2)}
        `);
    }
}

// 사용 예시
try {
    const user = new UserBuilder("Alice")
        .setAge(25)
        .setEmail("alice@example.com")
        .setAddress("Seoul")
        .setPhone("010-1234-5678")
        .setRole("admin")
        .setPermissions(["read", "write", "delete"])
        .setSettings({
            theme: "dark",
            notifications: true,
            language: "ko"
        })
        .build();

    user.display();
} catch (error) {
    console.error("Error creating user:", error.message);
}
```

> **👉🏻 `UserBuilder`를 사용하여 단계적으로 객체를 생성할 수 있습니다.**

### 🔍 주요 특징
1. **유효성 검사**: 각 단계에서 입력값의 유효성을 검사합니다.
2. **기본값 설정**: 선택적 속성에 대한 기본값을 제공합니다.
3. **메서드 체이닝**: 각 메서드가 `this`를 반환하여 체이닝이 가능합니다.
4. **에러 처리**: 잘못된 입력에 대한 예외 처리가 포함되어 있습니다.

---

## 4️⃣ 함수형 Builder 패턴 구현

클래스를 사용하지 않고, **함수형 방식으로도 Builder 패턴을 구현할 수 있습니다.**

```javascript
function createUser(name) {
    // private 변수로 user 객체 관리
    const user = { 
        name,
        age: null,
        email: null,
        address: null,
        phone: null,
        role: "user",
        permissions: [],
        settings: {}
    };

    // 유효성 검사 함수들
    const validators = {
        age: (age) => age >= 0 && age <= 150,
        email: (email) => email.includes("@"),
        phone: (phone) => /^\d{3}-\d{4}-\d{4}$/.test(phone),
        role: (role) => ["user", "admin", "manager"].includes(role)
    };

    return {
        setAge(age) {
            if (!validators.age(age)) {
                throw new Error("Invalid age");
            }
            user.age = age;
            return this;
        },
        setEmail(email) {
            if (!validators.email(email)) {
                throw new Error("Invalid email");
            }
            user.email = email;
            return this;
        },
        setAddress(address) {
            user.address = address;
            return this;
        },
        setPhone(phone) {
            if (!validators.phone(phone)) {
                throw new Error("Invalid phone number");
            }
            user.phone = phone;
            return this;
        },
        setRole(role) {
            if (!validators.role(role)) {
                throw new Error("Invalid role");
            }
            user.role = role;
            return this;
        },
        setPermissions(permissions) {
            user.permissions = permissions;
            return this;
        },
        setSettings(settings) {
            user.settings = { ...user.settings, ...settings };
            return this;
        },
        build() {
            if (!user.name) {
                throw new Error("Name is required");
            }
            return { ...user }; // 불변성을 위해 복사본 반환
        }
    };
}

// 사용 예시
try {
    const user = createUser("Bob")
        .setAge(30)
        .setEmail("bob@example.com")
        .setAddress("Busan")
        .setPhone("010-1234-5678")
        .setRole("manager")
        .setPermissions(["read", "write"])
        .setSettings({
            theme: "light",
            notifications: false,
            language: "en"
        })
        .build();

    console.log(user);
} catch (error) {
    console.error("Error creating user:", error.message);
}
```

> **👉🏻 함수형 방식도 동일한 메서드 체이닝을 지원하며, 클로저를 활용하여 private 변수를 관리합니다.**

### 🔍 함수형 Builder의 특징
1. **캡슐화**: 클로저를 통해 private 변수를 관리합니다.
2. **유효성 검사**: 각 단계에서 입력값의 유효성을 검사합니다.
3. **불변성**: `build()` 메서드에서 객체의 복사본을 반환합니다.
4. **재사용성**: 유효성 검사 로직을 별도로 분리하여 재사용할 수 있습니다.

---

## 5️⃣ Builder 패턴의 장점과 단점

### ✅ 장점
1. **객체 생성 과정의 명확성**
   - 각 단계가 명확하게 구분되어 있어 코드의 의도를 쉽게 파악할 수 있습니다.
   - 메서드 체이닝을 통해 가독성이 향상됩니다.

2. **유연한 확장성**
   - 새로운 속성을 추가하기 쉽습니다.
   - 기존 코드를 수정하지 않고도 새로운 기능을 추가할 수 있습니다.

3. **유효성 검사**
   - 각 단계에서 입력값의 유효성을 검사할 수 있습니다.
   - 잘못된 입력에 대한 예외 처리가 용이합니다.

4. **재사용성**
   - 동일한 생성 로직을 여러 곳에서 재사용할 수 있습니다.
   - 코드 중복을 줄일 수 있습니다.

### ❌ 단점
1. **코드 복잡성**
   - 작은 객체의 경우 Builder 패턴이 오버엔지니어링이 될 수 있습니다.
   - 초기 설정이 필요하여 코드가 길어질 수 있습니다.

2. **학습 곡선**
   - 패턴을 이해하고 적용하는 데 시간이 필요합니다.
   - 팀원들이 패턴에 익숙해져야 합니다.

3. **성능 오버헤드**
   - 객체 생성 과정이 여러 단계로 나뉘어 있어 약간의 성능 저하가 있을 수 있습니다.
   - 메서드 체이닝으로 인한 추가적인 함수 호출이 발생합니다.

---

## 6️⃣ 실제 사용 사례

### ✅ 1. HTTP 요청 생성기
```javascript
class RequestBuilder {
    constructor(url) {
        this.url = url;
        this.method = "GET";
        this.headers = {};
        this.body = null;
        this.timeout = 5000;
        this.retries = 3;
        this.cache = false;
    }

    setMethod(method) {
        const validMethods = ["GET", "POST", "PUT", "DELETE", "PATCH"];
        if (!validMethods.includes(method.toUpperCase())) {
            throw new Error("Invalid HTTP method");
        }
        this.method = method.toUpperCase();
        return this;
    }

    setHeaders(headers) {
        this.headers = { ...this.headers, ...headers };
        return this;
    }

    setBody(body) {
        if (typeof body === "object") {
            this.body = JSON.stringify(body);
            this.setHeaders({ "Content-Type": "application/json" });
        } else {
            this.body = body;
        }
        return this;
    }

    setTimeout(timeout) {
        if (timeout < 0) {
            throw new Error("Timeout must be positive");
        }
        this.timeout = timeout;
        return this;
    }

    setRetries(retries) {
        if (retries < 0) {
            throw new Error("Retries must be positive");
        }
        this.retries = retries;
        return this;
    }

    setCache(cache) {
        this.cache = cache;
        return this;
    }

    async build() {
        const options = {
            method: this.method,
            headers: this.headers,
            body: this.body,
            timeout: this.timeout,
            cache: this.cache ? "force-cache" : "no-cache"
        };

        let attempts = 0;
        while (attempts < this.retries) {
            try {
                const response = await fetch(this.url, options);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response;
            } catch (error) {
                attempts++;
                if (attempts === this.retries) {
                    throw error;
                }
                await new Promise(resolve => setTimeout(resolve, 1000 * attempts));
            }
        }
    }
}

// 사용 예시
async function fetchUserData() {
    try {
        const response = await new RequestBuilder("https://api.example.com/users")
            .setMethod("POST")
            .setHeaders({
                "Authorization": "Bearer token123",
                "Accept": "application/json"
            })
            .setBody({
                name: "John Doe",
                email: "john@example.com"
            })
            .setTimeout(10000)
            .setRetries(3)
            .setCache(false)
            .build();

        const data = await response.json();
        console.log(data);
    } catch (error) {
        console.error("Error fetching user data:", error.message);
    }
}
```

### ✅ 2. UI 컴포넌트 생성기
```javascript
class UIComponentBuilder {
    constructor(type) {
        this.type = type;
        this.props = {};
        this.children = [];
        this.styles = {};
        this.events = {};
    }

    setProps(props) {
        this.props = { ...this.props, ...props };
        return this;
    }

    addChild(child) {
        this.children.push(child);
        return this;
    }

    setStyle(styles) {
        this.styles = { ...this.styles, ...styles };
        return this;
    }

    addEvent(eventName, handler) {
        this.events[eventName] = handler;
        return this;
    }

    build() {
        const element = document.createElement(this.type);
        
        // 속성 설정
        Object.entries(this.props).forEach(([key, value]) => {
            element.setAttribute(key, value);
        });

        // 스타일 설정
        Object.entries(this.styles).forEach(([key, value]) => {
            element.style[key] = value;
        });

        // 이벤트 리스너 설정
        Object.entries(this.events).forEach(([eventName, handler]) => {
            element.addEventListener(eventName, handler);
        });

        // 자식 요소 추가
        this.children.forEach(child => {
            if (typeof child === "string") {
                element.appendChild(document.createTextNode(child));
            } else {
                element.appendChild(child);
            }
        });

        return element;
    }
}

// 사용 예시
const button = new UIComponentBuilder("button")
    .setProps({
        type: "submit",
        disabled: false
    })
    .setStyle({
        backgroundColor: "#007bff",
        color: "white",
        padding: "10px 20px",
        border: "none",
        borderRadius: "5px",
        cursor: "pointer"
    })
    .addEvent("click", () => console.log("Button clicked!"))
    .addChild("Submit")
    .build();

document.body.appendChild(button);
```

### ✅ 3. 데이터베이스 쿼리 생성기
```javascript
class QueryBuilder {
    constructor() {
        this.table = "";
        this.select = [];
        this.where = [];
        this.orderBy = [];
        this.limit = null;
        this.offset = null;
    }

    from(table) {
        this.table = table;
        return this;
    }

    select(...fields) {
        this.select = fields;
        return this;
    }

    where(condition) {
        this.where.push(condition);
        return this;
    }

    orderBy(field, direction = "ASC") {
        this.orderBy.push({ field, direction });
        return this;
    }

    limit(value) {
        this.limit = value;
        return this;
    }

    offset(value) {
        this.offset = value;
        return this;
    }

    build() {
        let query = "SELECT ";
        
        // SELECT 절
        query += this.select.length > 0 
            ? this.select.join(", ") 
            : "*";
        
        // FROM 절
        query += ` FROM ${this.table}`;
        
        // WHERE 절
        if (this.where.length > 0) {
            query += " WHERE " + this.where.join(" AND ");
        }
        
        // ORDER BY 절
        if (this.orderBy.length > 0) {
            query += " ORDER BY " + this.orderBy
                .map(({ field, direction }) => `${field} ${direction}`)
                .join(", ");
        }
        
        // LIMIT 절
        if (this.limit !== null) {
            query += ` LIMIT ${this.limit}`;
        }
        
        // OFFSET 절
        if (this.offset !== null) {
            query += ` OFFSET ${this.offset}`;
        }
        
        return query;
    }
}

// 사용 예시
const query = new QueryBuilder()
    .from("users")
    .select("id", "name", "email")
    .where("age > 18")
    .where("status = 'active'")
    .orderBy("name", "ASC")
    .limit(10)
    .offset(0)
    .build();

console.log(query);
// SELECT id, name, email FROM users WHERE age > 18 AND status = 'active' ORDER BY name ASC LIMIT 10 OFFSET 0
```

---

## 7️⃣ Best Practices

### ✅ 1. 필수 값 검증
```javascript
class Builder {
    constructor(required) {
        this.required = required;
        this.values = {};
    }

    setValue(key, value) {
        this.values[key] = value;
        return this;
    }

    build() {
        // 필수 값 검증
        const missing = this.required.filter(key => !(key in this.values));
        if (missing.length > 0) {
            throw new Error(`Missing required values: ${missing.join(", ")}`);
        }
        return this.values;
    }
}
```

### ✅ 2. 타입 안정성
```javascript
class TypedBuilder {
    constructor() {
        this.values = {};
        this.types = {};
    }

    defineProperty(name, type) {
        this.types[name] = type;
        return this;
    }

    setValue(name, value) {
        if (this.types[name] && typeof value !== this.types[name]) {
            throw new Error(`Invalid type for ${name}. Expected ${this.types[name]}`);
        }
        this.values[name] = value;
        return this;
    }

    build() {
        return this.values;
    }
}
```

### ✅ 3. 불변성 보장
```javascript
class ImmutableBuilder {
    constructor() {
        this.values = {};
    }

    setValue(key, value) {
        this.values = { ...this.values, [key]: value };
        return this;
    }

    build() {
        return Object.freeze({ ...this.values });
    }
}
```

---

## 8️⃣ 결론

Builder 패턴은 복잡한 객체 생성 과정을 단순화하고, 코드의 가독성과 유지보수성을 향상시키는 강력한 디자인 패턴입니다. 특히 다음과 같은 상황에서 유용합니다:

1. **복잡한 객체 생성**: 많은 속성과 옵션을 가진 객체를 생성할 때
2. **단계적 생성**: 객체를 여러 단계에 걸쳐 생성해야 할 때
3. **유효성 검사**: 객체 생성 과정에서 입력값의 유효성을 검사해야 할 때
4. **재사용성**: 동일한 생성 로직을 여러 곳에서 재사용해야 할 때

Builder 패턴을 적절히 활용하면 코드의 품질을 크게 향상시킬 수 있습니다. 다만, 작은 객체의 경우에는 패턴의 복잡성이 이점보다 클 수 있으므로, 상황에 맞게 사용하는 것이 중요합니다.
