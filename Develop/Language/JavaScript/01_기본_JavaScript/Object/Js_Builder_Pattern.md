---
title: JavaScript Builder
tags: [language, javascript, 01기본javascript, object, jsbuilderpattern]
updated: 2026-01-11
---
# JavaScript Builder 패턴

## 개요

Builder 패턴은 객체를 단계적으로 생성하는 디자인 패턴이다. 속성이 많거나 생성 로직이 복잡할 때 사용한다.

**핵심 개념:**
- 단계적 생성: 여러 단계를 거쳐 객체 생성
- 메서드 체이닝: `builder.setName().setAge().build()` 형태
- 유효성 검사: 각 단계에서 입력값 검증 가능
- 선택적 속성: 필요한 속성만 설정

## 문제 상황

속성이 많은 객체를 생성할 때 문제가 생긴다.

```javascript
// 속성이 많아지면 코드가 지저분해짐
const user = {
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
```

**문제점:**
- 속성이 많아질수록 가독성 저하
- 유효성 검사가 어려움
- 기본값 설정이 복잡함
- 선택적 속성 처리 불편
- 에러 처리가 일관되지 않음

## 해결 방법

### 클래스 기반 Builder 패턴

클래스를 사용해 Builder를 구현한다.

```javascript
class UserBuilder {
    constructor(name) {
        this.name = name;
        this.age = null;
        this.email = null;
        this.address = null;
        this.phone = null;
        this.role = "user";
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
const user = new UserBuilder("Alice")
    .setAge(25)
    .setEmail("alice@example.com")
    .setRole("admin")
    .setPermissions(["read", "write", "delete"])
    .build();

user.display();
```

**특징:**
- 각 메서드가 `this`를 반환해 메서드 체이닝 가능
- 각 단계에서 유효성 검사 수행
- `build()` 호출 시 최종 객체 생성

**주의사항:**
- `build()` 전까지는 객체가 완성되지 않음
- 필수 속성은 `build()`에서 검증해야 함

### 함수형 Builder 패턴

클로저를 사용해 Builder를 구현한다.

```javascript
function createUser(name) {
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

    const validators = {
        age: (age) => age >= 0 && age <= 150,
        email: (email) => email.includes("@"),
        phone: (phone) => /^\d{3}-\d{4}-\d{4}$/.test(phone),
        role: (role) => ["user", "admin", "manager"].includes(role)
    };

    return {
        setAge(age) {
            if (!validators.age(age)) throw new Error("Invalid age");
            user.age = age;
            return this;
        },
        setEmail(email) {
            if (!validators.email(email)) throw new Error("Invalid email");
            user.email = email;
            return this;
        },
        setAddress(address) {
            user.address = address;
            return this;
        },
        setPhone(phone) {
            if (!validators.phone(phone)) throw new Error("Invalid phone number");
            user.phone = phone;
            return this;
        },
        setRole(role) {
            if (!validators.role(role)) throw new Error("Invalid role");
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
            if (!user.name) throw new Error("Name is required");
            return { ...user };
        }
    };
}

// 사용 예시
const user = createUser("Bob")
    .setAge(30)
    .setEmail("bob@example.com")
    .setRole("user")
    .build();
```

**클래스 vs 함수형:**
- 클래스: 상속 가능, 인스턴스 메서드 사용
- 함수형: 클로저로 상태 캡슐화, 더 가벼움

**실무 팁:**
간단한 경우 함수형이 더 가볍고, 복잡한 경우 클래스가 더 관리하기 쉽다.

## 실제 사용 예제

### HTTP 요청 Builder

fetch API를 래핑해 재시도 로직과 타임아웃을 추가한 예제다.

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
        if (timeout < 0) throw new Error("Timeout must be positive");
        this.timeout = timeout;
        return this;
    }

    setRetries(retries) {
        if (retries < 0) throw new Error("Retries must be positive");
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
                if (attempts === this.retries) throw error;
                await new Promise(resolve => setTimeout(resolve, 1000 * attempts));
            }
        }
    }
}

// 사용 예시
const response = await new RequestBuilder("https://api.example.com/users")
    .setMethod("POST")
    .setHeaders({ "Authorization": "Bearer token123" })
    .setBody({ name: "John Doe", email: "john@example.com" })
    .setTimeout(10000)
    .setRetries(3)
    .build();

const data = await response.json();
```

**실무 팁:**
- 재시도 로직은 네트워크 오류에만 적용하고, 4xx 오류는 재시도하지 않는다
- 타임아웃을 너무 짧게 설정하면 정상 요청도 실패할 수 있다
- 헤더 설정은 `setHeaders()`로 한 번에 하는 게 편하다

### SQL 쿼리 Builder

SQL 쿼리를 동적으로 생성하는 예제다.

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
        query += this.select.length > 0 ? this.select.join(", ") : "*";
        query += ` FROM ${this.table}`;
        
        if (this.where.length > 0) {
            query += " WHERE " + this.where.join(" AND ");
        }
        
        if (this.orderBy.length > 0) {
            query += " ORDER BY " + this.orderBy
                .map(({ field, direction }) => `${field} ${direction}`)
                .join(", ");
        }
        
        if (this.limit !== null) query += ` LIMIT ${this.limit}`;
        if (this.offset !== null) query += ` OFFSET ${this.offset}`;
        
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
    .build();

// 결과: SELECT id, name, email FROM users WHERE age > 18 AND status = 'active' ORDER BY name ASC LIMIT 10
```

**주의사항:**
- SQL 인젝션 방지를 위해 파라미터화된 쿼리를 사용해야 한다
- 실제 프로덕션에서는 ORM이나 쿼리 빌더 라이브러리(Knex, TypeORM 등)를 사용하는 게 좋다

## 장단점

### 장점

- 가독성: 메서드 체이닝으로 코드 의도가 명확함
- 유효성 검사: 각 단계에서 입력값 검증 가능
- 유연성: 선택적 속성을 쉽게 설정
- 재사용성: 동일한 생성 로직을 여러 곳에서 재사용

### 단점

- 복잡성: 속성이 적은 객체에는 오버엔지니어링
- 성능: 메서드 체이닝으로 인한 함수 호출 오버헤드 (미미함)
- 학습 곡선: 팀원들이 패턴을 이해해야 함

## 사용 시기

**Builder 패턴을 사용하는 경우:**
- 속성이 5개 이상인 객체
- 선택적 속성이 많은 경우
- 유효성 검사가 필요한 경우
- 동일한 생성 로직을 여러 곳에서 재사용하는 경우

**사용하지 않는 경우:**
- 속성이 2~3개 정도인 간단한 객체
- 항상 모든 속성이 필요한 경우
- 생성 로직이 단순한 경우

**실무 팁:**
작은 객체는 일반 객체 리터럴이나 생성자 함수로 충분하다. Builder 패턴은 복잡한 객체 생성에만 사용한다.
