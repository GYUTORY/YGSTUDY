---
title: JavaScript Builder
tags: [language, javascript, 01기본javascript, object, jsbuilderpattern]
updated: 2026-06-28
---
# JavaScript Builder 패턴

## 어떤 상황에서 쓰게 되는가

객체 하나를 만드는데 인자가 일고여덟 개씩 되는 함수를 마주친 적이 있을 것이다. 처음엔 생성자에 인자를 쭉 나열한다. 그러다 선택 인자가 늘어나면 `new User("Alice", null, "alice@example.com", null, null, "admin")` 같은 호출이 생기고, 중간의 `null`이 무슨 자리인지 호출부만 봐서는 알 수가 없다. 인자 순서를 한 칸 잘못 넣어도 타입이 같으면 에러도 안 난다. 이 지점에서 Builder를 꺼내게 된다.

객체 리터럴로 한 번에 넘기는 방법도 있다. 실제로 인자가 적고 검증이 필요 없으면 그게 정답이다. Builder가 값을 하는 건 (1) 각 속성을 넣는 시점에 검증을 걸고 싶을 때, (2) 속성 간에 기본값·파생값 처리 로직이 있을 때, (3) 같은 생성 절차를 여러 호출부에서 반복할 때다. 이 세 조건이 안 걸리면 Builder는 코드만 늘린다.

```javascript
// 인자 순서에 의존하는 생성자 — 호출부가 읽기 어렵다
const user = new User("Alice", 25, "alice@example.com", "Seoul", "010-1234-5678", "admin");

// 객체 리터럴 — 키 이름은 보이지만 생성 시점 검증이 없다
const user = {
    name: "Alice",
    age: 25,
    email: "alice@example.com",
    role: "admin",
    permissions: ["read", "write", "delete"]
};
```

객체 리터럴은 키 이름이 보여서 순서 문제는 사라진다. 다만 `age`에 -1이 들어가거나 `email`에 `@`가 빠져도 그대로 통과한다. 검증을 넣으려면 생성 후에 별도 함수를 호출해야 하는데, 그러면 "검증 안 된 객체"가 잠깐 존재하는 구간이 생긴다. Builder는 검증을 set 단계로 끌어와서 그 구간을 없앤다.

## 클래스 기반 Builder

각 setter가 `this`를 반환하면 메서드 체이닝이 된다. `build()`에서 필수값을 마지막으로 점검하고 완성 객체를 돌려준다.

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
}

const user = new UserBuilder("Alice")
    .setAge(25)
    .setEmail("alice@example.com")
    .setRole("admin")
    .setPermissions(["read", "write", "delete"])
    .build();
```

`build()` 전까지는 객체가 완성된 상태가 아니다. 필수값 검증을 setter에 둘지 `build()`에 둘지 헷갈리는데, 단일 속성의 형식 검증(나이 범위, 이메일 형식)은 setter에, "이름이 없으면 안 된다" 같은 필수 여부는 `build()`에 두는 편이 자연스럽다. setter는 호출 안 될 수도 있으니 필수 검증을 setter에 넣으면 의미가 없다.

## 함수형 Builder

클로저로 내부 상태를 가두는 방식이다. 클래스보다 가볍고, 반환 객체에 노출한 메서드 외에는 외부에서 `user`에 손댈 방법이 없다.

```javascript
function createUser(name) {
    const user = {
        name,
        age: null,
        email: null,
        role: "user",
        permissions: [],
        settings: {}
    };

    const validators = {
        age: (age) => age >= 0 && age <= 150,
        email: (email) => email.includes("@"),
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

const user = createUser("Bob")
    .setAge(30)
    .setEmail("bob@example.com")
    .build();
```

클래스 쪽은 상속이 되고 `instanceof`로 타입을 구분할 수 있다. 함수형 쪽은 `user` 변수가 클로저에 갇혀서 캡슐화가 확실하다. 간단한 생성기는 함수형이 손이 덜 가고, 상속이나 타입 구분이 필요하면 클래스로 간다.

## 실무에서 밟는 지뢰

### 메서드 체이닝 호출 순서 의존성

setter가 서로의 상태를 건드리면 호출 순서가 결과를 바꾼다. HTTP 요청 Builder에서 `setBody`가 객체를 받으면 `Content-Type: application/json`을 자동으로 넣어주도록 만드는 경우가 흔하다.

```javascript
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
```

여기서 사용자가 `text/plain`으로 직접 보내려고 헤더를 지정했는데 순서를 이렇게 쓰면 의도가 깨진다.

```javascript
// setHeaders로 지정한 text/plain이 setBody 내부의 application/json에 덮인다
new RequestBuilder(url)
    .setHeaders({ "Content-Type": "text/plain" })
    .setBody(someObject)   // 여기서 Content-Type이 application/json으로 덮임
    .build();

// 반대 순서면 사용자가 마지막에 지정한 값이 남는다
new RequestBuilder(url)
    .setBody(someObject)                              // application/json 설정
    .setHeaders({ "Content-Type": "text/plain" })    // text/plain으로 덮음
    .build();
```

이런 암묵적 순서 의존은 디버깅할 때 한참 헤맨다. 호출부만 봐서는 왜 Content-Type이 바뀌는지 안 보이기 때문이다. 피하려면 setter끼리 서로 호출하지 않게 만들고, 자동 헤더 결정은 `build()` 시점에 "사용자가 Content-Type을 명시 안 했을 때만 채운다"로 미루는 게 안전하다.

```javascript
build() {
    const headers = { ...this.headers };
    if (this.body && typeof this._rawBody === "object" && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    // ...
}
```

### build()가 async인데 await을 빠뜨림

재시도나 타임아웃을 넣다 보면 `build()`가 `async`가 되는 경우가 있다. 이때 호출부에서 `await`을 빠뜨리면 객체가 아니라 Promise가 넘어온다.

```javascript
class RequestBuilder {
    constructor(url) {
        this.url = url;
        this.method = "GET";
        this.headers = {};
        this.body = null;
        this.retries = 3;
    }
    setMethod(method) { this.method = method.toUpperCase(); return this; }
    setHeaders(headers) { this.headers = { ...this.headers, ...headers }; return this; }
    setBody(body) { this.body = JSON.stringify(body); return this; }

    async build() {
        let attempts = 0;
        while (attempts < this.retries) {
            try {
                const res = await fetch(this.url, {
                    method: this.method,
                    headers: this.headers,
                    body: this.body
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res;
            } catch (e) {
                if (++attempts === this.retries) throw e;
                await new Promise(r => setTimeout(r, 1000 * attempts));
            }
        }
    }
}

// await 누락 — response는 Response가 아니라 Promise다
const response = new RequestBuilder(url).setMethod("POST").build();
const data = await response.json();   // TypeError: response.json is not a function
```

`build()`만 비동기인데 그 앞 setter는 동기라서, 체인 전체를 await로 감싼다는 감각이 안 잡혀서 자주 놓친다. `await ...build()`로 묶어야 한다. 더 큰 문제는 에러가 나도 안 터지고 묻히는 경우다. `build()` 내부에서 throw가 나면 await 없이 받은 Promise는 처리 안 된 reject가 되어 `unhandledRejection`으로 빠진다. 동기 흐름이라 생각하고 `try/catch`로 감쌌는데 catch가 안 잡힌다.

이름을 `build()` 대신 `send()`나 `execute()`처럼 비동기임이 드러나는 이름으로 바꾸면 호출부에서 await을 덜 빠뜨린다. 객체 생성과 부수효과(네트워크 호출)를 한 메서드에 섞은 게 근본 원인이라, 둘을 나눌 수 있으면 나누는 게 낫다.

### 빌더 인스턴스 재사용 시 상태 공유 버그

이게 가장 자주 당하는 함정이다. 빌더 하나를 만들어두고 `build()`를 여러 번 부르면, 각 호출이 같은 내부 상태를 공유한다. 특히 배열·객체 같은 참조 타입 속성에서 터진다.

```javascript
const builder = new UserBuilder("base")
    .setRole("user")
    .setPermissions(["read"]);

const userA = builder.build();
builder.setPermissions([...builder.permissions, "write"]);  // userA에도 영향이 갈 수 있다
const userB = builder.build();
```

`build()`가 `new User(this)`로 빌더 속성을 그대로 복사하는데, `permissions` 같은 배열은 얕은 복사라서 `userA.permissions`와 빌더의 `permissions`가 같은 배열을 가리킬 수 있다. 한쪽에서 `push`하면 다른 쪽도 바뀐다.

```javascript
build() {
    if (!this.name) throw new Error("Name is required");
    return new User({
        ...this,
        permissions: [...this.permissions],         // 배열 깊은 복사
        settings: { ...this.settings }              // 객체 복사
    });
}
```

근본 해법은 빌더를 일회용으로 쓰는 것이다. `build()` 한 번 부르면 끝, 객체가 또 필요하면 빌더를 새로 만든다. 빌더를 재사용하고 싶다면 `build()` 안에서 모든 참조 타입을 복사해서 완성 객체와 빌더가 메모리를 공유하지 않게 해야 한다. Java에서 빌더를 재사용하다 컬렉션이 공유돼 터지는 것과 같은 문제고, JS는 얕은 복사가 기본이라 더 쉽게 밟는다. [Java_Builder_Pattern.md](../../../Java/객체지향%20프로그래밍%20(OOP)/Java_Builder_Pattern.md)의 재사용 주의사항과 같은 맥락이다.

### Object.freeze로 불변 객체 만들기

`build()`가 돌려준 객체를 호출부에서 마음대로 수정하면 빌더로 검증한 의미가 없어진다. 완성 시점에 `Object.freeze`로 잠그면 이후 변경이 막힌다.

```javascript
build() {
    if (!this.name) throw new Error("Name is required");
    const user = new User({
        ...this,
        permissions: [...this.permissions]
    });
    return Object.freeze(user);
}

const user = new UserBuilder("Alice").setRole("admin").build();
user.role = "superadmin";   // strict 모드면 TypeError, 아니면 조용히 무시
```

`Object.freeze`는 얕다는 점을 기억해야 한다. 최상위 속성 재할당은 막지만 `user.permissions.push("delete")`는 그대로 통과한다. 중첩까지 막으려면 `permissions` 배열과 `settings` 객체도 각각 freeze해야 한다.

```javascript
build() {
    const user = new User({
        ...this,
        permissions: Object.freeze([...this.permissions]),
        settings: Object.freeze({ ...this.settings })
    });
    return Object.freeze(user);
}
```

비-strict 모드에서는 freeze된 객체에 쓰기를 해도 에러 없이 무시된다. 그래서 "분명 freeze했는데 왜 안 막히지"가 아니라 "값을 바꿨는데 왜 반영이 안 되지"로 증상이 나타난다. 파일 상단에 `"use strict"`를 두거나 ES 모듈을 쓰면 이런 쓰기가 TypeError로 드러나서 잡기 쉽다.

## options 객체 패턴과 언제 무엇을 쓸지

Builder를 쓸지 말지의 실제 경쟁자는 옛날식 다인자 생성자가 아니라 options 객체다. 구조 분해와 기본값을 쓰면 선택 인자 문제 대부분이 해결된다.

```javascript
function createUser(name, {
    age = null,
    email = null,
    role = "user",
    permissions = [],
    settings = {}
} = {}) {
    if (age !== null && (age < 0 || age > 150)) throw new Error("Invalid age");
    if (email !== null && !email.includes("@")) throw new Error("Invalid email");
    return { name, age, email, role, permissions, settings };
}

const user = createUser("Alice", {
    age: 25,
    email: "alice@example.com",
    role: "admin"
});
```

이 한 함수가 클래스 기반 Builder 절반의 일을 한다. 키 이름이 보이고, 기본값이 한곳에 모여 있고, 검증도 들어간다. 코드량도 훨씬 적다. 실무에서 객체 생성의 8할은 이걸로 끝난다.

Builder가 options 객체보다 나은 지점은 좁다. 첫째, 속성을 한 번에 다 못 받고 여러 단계·여러 함수를 거쳐 조립해야 할 때다. 요청 빌더처럼 한 곳에서 URL과 메서드를 정하고, 다른 곳에서 인증 헤더를 붙이고, 또 다른 곳에서 바디를 채우는 흐름이면 빌더 인스턴스를 넘기면서 단계적으로 쌓는 게 자연스럽다. options 객체는 호출 한 번에 전부 넘겨야 해서 이런 분산 조립이 안 된다. 둘째, `where()`를 여러 번 부르는 쿼리 빌더처럼 같은 종류의 항목을 누적해야 할 때다.

판단 기준은 단순하다. 생성에 필요한 값이 호출 한 번에 다 모이면 options 객체, 여러 시점·여러 함수에 걸쳐 쌓아야 하면 Builder다. 애매하면 options 객체로 시작하고, 분산 조립이 실제로 필요해지면 그때 Builder로 옮긴다.

## TypeScript에서의 반환 타입

타입스크립트로 빌더를 쓰면 setter 반환 타입을 어떻게 줄지가 문제가 된다. 매 메서드에 `: UserBuilder`를 박아도 동작은 하지만, 상속받은 빌더에서 부모 setter를 부르면 자식 타입이 아니라 부모 타입이 반환돼 체이닝이 끊긴다. 이때 `this` 타입을 쓰면 호출한 인스턴스의 실제 타입이 유지된다.

```typescript
class UserBuilder {
    private name: string;
    private age: number | null = null;
    private role: string = "user";

    constructor(name: string) {
        this.name = name;
    }

    setAge(age: number): this {
        if (age < 0 || age > 150) throw new Error("Invalid age");
        this.age = age;
        return this;
    }

    setRole(role: string): this {
        this.role = role;
        return this;
    }

    build() {
        return { name: this.name, age: this.age, role: this.role };
    }
}
```

더 나아가면 필수값을 컴파일 타임에 강제할 수 있다. 단계별 빌더는 각 단계가 다음 단계 인터페이스를 반환하게 해서, 필수 setter를 부르기 전에는 `build()`가 타입에 아예 없게 만든다.

```typescript
interface HasUrl {
    setMethod(method: string): HasMethod;
}
interface HasMethod {
    setBody(body: object): Buildable;
    build(): Request;   // 메서드 지정 후 바디 없이도 빌드 가능
}
interface Buildable {
    build(): Request;
}

class RequestBuilder implements HasUrl, HasMethod, Buildable {
    private url: string;
    private method = "GET";
    private body: string | null = null;

    private constructor(url: string) {
        this.url = url;
    }

    static create(url: string): HasUrl {
        return new RequestBuilder(url);
    }

    setMethod(method: string): HasMethod {
        this.method = method;
        return this;
    }

    setBody(body: object): Buildable {
        this.body = JSON.stringify(body);
        return this;
    }

    build(): Request {
        return new Request(this.url, { method: this.method, body: this.body });
    }
}

// setMethod를 부르기 전에는 build()가 타입에 없어서 컴파일 에러가 난다
RequestBuilder.create("https://api.example.com")
    .setMethod("POST")
    .setBody({ name: "John" })
    .build();
```

단계별 빌더는 인터페이스가 늘어나 장황하다. 필수값이 두세 개를 넘고 순서가 중요한 빌더가 아니면 보통 과하다. 필수값 강제만 필요하면 그냥 생성자 인자나 `create(url)` 같은 정적 팩토리로 받는 게 단순하다.

## Java 빌더와 다른 점

Java 빌더에 익숙하면 JS로 옮길 때 두 가지가 다르다.

Java는 `private` 생성자로 객체를 막고 빌더만 통해 생성하도록 강제한다. JS에는 진짜 `private` 생성자가 없다. 클래스 `#` 프라이빗 필드로 흉내 낼 수는 있지만, `new User(...)`를 직접 막는 깔끔한 방법은 없다. 그래서 JS 빌더는 "빌더로만 만드세요"를 강제하기보다 관례에 맡기는 쪽이다. 강제가 필요하면 함수형 빌더로 가서 생성자 자체를 외부에 노출하지 않는 게 차라리 확실하다.

캡슐화 방식도 다르다. Java는 접근 제어자로 필드를 가린다. JS 함수형 빌더는 클로저로 가린다. `createUser`가 반환하는 객체에 `setAge`만 노출하면, 내부 `user` 변수는 그 메서드들만 접근할 수 있고 밖에서는 잡을 방법이 없다. 클래스 기반 빌더는 `this.age`가 다 보여서 캡슐화가 약한데, 진짜로 숨기고 싶으면 `#age` 같은 프라이빗 필드를 쓰거나 함수형으로 가야 한다. 같은 빌더 패턴이라도 JS에서는 클로저가 Java의 접근 제어자 역할을 대신한다.

더 깊은 Java 쪽 구현과 비교가 필요하면 [Java_Builder_Pattern.md](../../../Java/객체지향%20프로그래밍%20(OOP)/Java_Builder_Pattern.md)를 참고한다.

## 쿼리 빌더 — 누적형 빌더 예제

`where()`를 여러 번 부르는 쿼리 빌더는 같은 종류 항목을 누적하는 빌더의 전형이다. options 객체로는 표현하기 어려운 형태다.

```javascript
class QueryBuilder {
    constructor() {
        this.table = "";
        this.columns = [];
        this.conditions = [];
        this.orders = [];
        this.limitValue = null;
    }

    from(table) {
        this.table = table;
        return this;
    }

    select(...fields) {
        this.columns = fields;
        return this;
    }

    where(condition) {
        this.conditions.push(condition);
        return this;
    }

    orderBy(field, direction = "ASC") {
        this.orders.push({ field, direction });
        return this;
    }

    limit(value) {
        this.limitValue = value;
        return this;
    }

    build() {
        let query = "SELECT ";
        query += this.columns.length > 0 ? this.columns.join(", ") : "*";
        query += ` FROM ${this.table}`;

        if (this.conditions.length > 0) {
            query += " WHERE " + this.conditions.join(" AND ");
        }
        if (this.orders.length > 0) {
            query += " ORDER BY " + this.orders
                .map(({ field, direction }) => `${field} ${direction}`)
                .join(", ");
        }
        if (this.limitValue !== null) query += ` LIMIT ${this.limitValue}`;

        return query;
    }
}

const query = new QueryBuilder()
    .from("users")
    .select("id", "name", "email")
    .where("age > 18")
    .where("status = 'active'")
    .orderBy("name", "ASC")
    .limit(10)
    .build();
// SELECT id, name, email FROM users WHERE age > 18 AND status = 'active' ORDER BY name ASC LIMIT 10
```

이 예제는 학습용이고, 값을 문자열에 직접 붙이면 SQL 인젝션에 그대로 노출된다. 실제로는 `where("age > ?", [18])`처럼 파라미터를 분리해 누적하고 `build()`에서 값 배열을 같이 돌려줘야 한다. 프로덕션에서는 직접 만들기보다 Knex나 TypeORM 같은 검증된 쿼리 빌더를 쓴다.
