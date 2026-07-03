---
title: Prototype Pattern (프로토타입 패턴)
tags: [design-pattern, prototype-pattern, creational-pattern, javascript, deep-copy]
updated: 2026-03-30
---

# Prototype Pattern (프로토타입 패턴)

## 정의

프로토타입 패턴은 기존 객체를 복제해서 새 객체를 만드는 생성 패턴이다. `new`로 처음부터 생성하는 대신, 이미 만들어진 객체를 템플릿 삼아 복사한다.

객체 생성 비용이 크거나, 비슷한 객체를 반복 생성해야 할 때 쓴다. DB에서 설정값을 읽어와 초기화하는 객체가 있다면, 매번 DB를 조회하는 것보다 한 번 만든 객체를 복제하는 쪽이 낫다.

## JavaScript의 prototype과 디자인 패턴의 Prototype

이름이 같아서 혼동하기 쉬운데, 둘은 다른 개념이다.

### JavaScript의 프로토타입 체인

JavaScript에서 `prototype`은 객체 간 상속을 구현하는 언어 내장 메커니즘이다. 모든 객체는 `[[Prototype]]` 내부 슬롯을 가지고, 프로퍼티 탐색 시 체인을 따라 올라간다.

```javascript
function Animal(name) {
    this.name = name;
}

Animal.prototype.speak = function() {
    return `${this.name} makes a sound`;
};

const dog = new Animal('Rex');
// dog 자체에는 speak가 없지만, Animal.prototype에서 찾는다
dog.speak(); // "Rex makes a sound"
```

이건 **메서드 공유와 상속**을 위한 것이다. 객체를 복제하는 게 아니라, 공통 메서드를 프로토타입 체인에 올려놓고 여러 인스턴스가 참조하는 구조다.

### 디자인 패턴의 Prototype

디자인 패턴에서 Prototype은 **객체 복제**가 핵심이다. 원본 객체의 상태(데이터)를 그대로 복사해서 독립적인 새 객체를 만든다.

```javascript
class ServerConfig {
    constructor(host, port, options) {
        this.host = host;
        this.port = port;
        this.options = options;
        this.timestamp = Date.now();
    }

    clone() {
        // 자기 자신을 복제해서 새 객체 반환
        const cloned = new ServerConfig(this.host, this.port, { ...this.options });
        cloned.timestamp = this.timestamp;
        return cloned;
    }
}

const production = new ServerConfig('prod.example.com', 443, {
    ssl: true,
    timeout: 30000,
    retries: 3
});

// production 설정을 기반으로 staging 환경 설정을 만든다
const staging = production.clone();
staging.host = 'staging.example.com';
staging.port = 8443;
```

차이를 정리하면:

| 구분 | JavaScript prototype | Prototype 패턴 |
|------|---------------------|----------------|
| 목적 | 메서드 공유, 상속 체인 | 객체 상태 복제 |
| 동작 | 프로퍼티 탐색 시 체인을 타고 올라감 | 원본의 데이터를 복사해서 새 객체 생성 |
| 결과 | 여러 인스턴스가 같은 메서드를 참조 | 원본과 동일한 상태를 가진 독립 객체 |

## 깊은 복사 구현

Prototype 패턴에서 가장 까다로운 부분이 깊은 복사(deep copy)다. 얕은 복사로는 중첩 객체가 원본과 참조를 공유하게 되어, 복제본 수정이 원본에 영향을 준다.

### 얕은 복사의 문제

```javascript
const original = {
    name: 'config',
    database: {
        host: 'localhost',
        credentials: { user: 'admin', password: 'secret' }
    }
};

// 얕은 복사
const shallow = { ...original };
shallow.database.host = 'remote-server';

console.log(original.database.host); // "remote-server" — 원본이 바뀐다
```

`spread` 연산자나 `Object.assign`은 1뎁스만 복사한다. 중첩된 `database` 객체는 같은 참조를 가리키므로 복제본을 수정하면 원본도 같이 변한다.

### JSON.parse/JSON.stringify

가장 간단한 깊은 복사 방법이다.

```javascript
const deepCopy = JSON.parse(JSON.stringify(original));
deepCopy.database.host = 'remote-server';

console.log(original.database.host); // "localhost" — 원본 유지
```

간단하지만 한계가 명확하다:

```javascript
const problematic = {
    date: new Date('2026-01-01'),        // Date → 문자열로 변환됨
    regex: /pattern/gi,                   // RegExp → 빈 객체 {}
    func: function() { return 1; },       // 함수 → 사라짐
    undef: undefined,                     // undefined → 사라짐
    map: new Map([['key', 'value']]),     // Map → 빈 객체 {}
    set: new Set([1, 2, 3]),              // Set → 빈 객체 {}
    infinity: Infinity,                   // Infinity → null
    nan: NaN,                             // NaN → null
};

const copied = JSON.parse(JSON.stringify(problematic));

console.log(copied.date);      // "2026-01-01T00:00:00.000Z" (문자열)
console.log(copied.regex);     // {}
console.log(copied.func);      // undefined (프로퍼티 자체가 없음)
console.log(copied.undef);     // undefined (프로퍼티 자체가 없음)
console.log(copied.map);       // {}
console.log(copied.set);       // {}
```

순환 참조가 있으면 아예 에러가 난다:

```javascript
const circular = { name: 'test' };
circular.self = circular;

JSON.parse(JSON.stringify(circular));
// TypeError: Converting circular structure to JSON
```

단순한 데이터 객체(문자열, 숫자, 불리언, 배열, 일반 객체만 포함)라면 JSON 방식으로 충분하다. 그 외에는 다른 방법을 써야 한다.

### structuredClone (권장)

Node.js 17+, 브라우저 대부분에서 지원하는 내장 API다. JSON 방식의 한계를 상당 부분 해결한다.

```javascript
const data = {
    date: new Date('2026-01-01'),
    map: new Map([['key', 'value']]),
    set: new Set([1, 2, 3]),
    buffer: new ArrayBuffer(8),
    nested: { deep: { value: 42 } }
};

const cloned = structuredClone(data);

console.log(cloned.date instanceof Date);  // true — Date 유지
console.log(cloned.map instanceof Map);    // true — Map 유지
console.log(cloned.set instanceof Set);    // true — Set 유지
```

순환 참조도 처리한다:

```javascript
const circular = { name: 'test' };
circular.self = circular;

const cloned = structuredClone(circular);
console.log(cloned.self === cloned); // true — 순환 참조 유지, 원본과는 별개
```

그러나 `structuredClone`도 한계가 있다:

```javascript
// 함수는 복제 불가
structuredClone({ fn: () => {} });
// DOMException: () => {} could not be cloned.

// 클래스 인스턴스의 프로토타입 체인이 사라진다
class MyClass {
    constructor(value) { this.value = value; }
    getValue() { return this.value; }
}

const instance = new MyClass(42);
const cloned = structuredClone(instance);

console.log(cloned instanceof MyClass);  // false
console.log(cloned.getValue);            // undefined — 메서드 없음
console.log(cloned.value);               // 42 — 데이터는 복사됨
```

함수나 클래스 인스턴스를 포함하는 객체라면 재귀 복사를 직접 구현해야 한다.

### 재귀 복사

타입별로 분기 처리하는 방식이다. 실무에서 필요한 수준으로 구현하면 이 정도다:

```javascript
function deepClone(obj, visited = new WeakMap()) {
    // 원시값이나 함수는 그대로 반환
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }

    // 순환 참조 처리
    if (visited.has(obj)) {
        return visited.get(obj);
    }

    // 특수 타입 처리
    if (obj instanceof Date) {
        return new Date(obj.getTime());
    }

    if (obj instanceof RegExp) {
        return new RegExp(obj.source, obj.flags);
    }

    if (obj instanceof Map) {
        const map = new Map();
        visited.set(obj, map);
        obj.forEach((value, key) => {
            map.set(deepClone(key, visited), deepClone(value, visited));
        });
        return map;
    }

    if (obj instanceof Set) {
        const set = new Set();
        visited.set(obj, set);
        obj.forEach(value => {
            set.add(deepClone(value, visited));
        });
        return set;
    }

    // 배열 또는 일반 객체
    const clone = Array.isArray(obj) ? [] : Object.create(Object.getPrototypeOf(obj));
    visited.set(obj, clone);

    for (const key of Reflect.ownKeys(obj)) {
        const descriptor = Object.getOwnPropertyDescriptor(obj, key);
        if (descriptor.value !== undefined) {
            descriptor.value = deepClone(descriptor.value, visited);
        }
        Object.defineProperty(clone, key, descriptor);
    }

    return clone;
}
```

핵심 포인트:
- `WeakMap`으로 순환 참조를 추적한다. 이미 복제한 객체를 다시 만나면 복제본을 반환한다.
- `Object.create(Object.getPrototypeOf(obj))`로 프로토타입 체인을 보존한다. 클래스 인스턴스를 복제해도 `instanceof` 검사가 통과한다.
- `Reflect.ownKeys`는 Symbol 키를 포함한 모든 자체 프로퍼티를 순회한다.

### 깊은 복사 방법 비교

| 방법 | 순환 참조 | Date/Map/Set | 함수 | 클래스 인스턴스 | 속도 |
|------|----------|-------------|------|--------------|------|
| JSON.parse/stringify | X (에러) | X (손실) | X (소실) | X (소실) | 빠름 |
| structuredClone | O | O | X (에러) | 데이터만 복사 | 보통 |
| 재귀 복사 | O | O | 참조 복사 | O | 느림 |

실무에서는 대부분 `structuredClone`으로 충분하다. 클래스 인스턴스 복제가 필요한 경우에만 재귀 복사나 `clone()` 메서드를 직접 구현한다.

## 프로토타입 레지스트리

복제할 원본 객체들을 한 곳에서 관리하는 패턴이다. 객체 유형별로 원본을 등록해두고, 필요할 때 이름으로 찾아서 복제한다.

```javascript
class PrototypeRegistry {
    #prototypes = new Map();

    register(name, prototype) {
        this.#prototypes.set(name, prototype);
    }

    unregister(name) {
        this.#prototypes.delete(name);
    }

    clone(name) {
        const prototype = this.#prototypes.get(name);
        if (!prototype) {
            throw new Error(`프로토타입 "${name}"이 등록되지 않았다`);
        }

        if (typeof prototype.clone === 'function') {
            return prototype.clone();
        }

        return structuredClone(prototype);
    }

    has(name) {
        return this.#prototypes.has(name);
    }
}
```

사용 예시:

```javascript
class NotificationTemplate {
    constructor(type, title, body, channels) {
        this.type = type;
        this.title = title;
        this.body = body;
        this.channels = [...channels];
        this.metadata = {};
    }

    clone() {
        const cloned = new NotificationTemplate(
            this.type,
            this.title,
            this.body,
            [...this.channels]
        );
        cloned.metadata = structuredClone(this.metadata);
        return cloned;
    }
}

// 레지스트리에 알림 템플릿 등록
const registry = new PrototypeRegistry();

registry.register('welcome-email', new NotificationTemplate(
    'email',
    '가입을 환영합니다',
    '서비스 이용 안내...',
    ['email']
));

registry.register('order-alert', new NotificationTemplate(
    'push',
    '주문이 접수되었습니다',
    '주문번호: {orderId}',
    ['push', 'sms']
));

// 복제해서 개별 알림 생성
const welcomeNotification = registry.clone('welcome-email');
welcomeNotification.body = `안녕하세요, ${userName}님. 서비스 이용 안내...`;

const orderNotification = registry.clone('order-alert');
orderNotification.body = orderNotification.body.replace('{orderId}', 'ORD-20260330-001');
```

레지스트리를 쓰면 객체 생성 로직이 사용처에서 분리된다. 새 템플릿을 추가할 때 기존 코드를 수정할 필요 없이 레지스트리에 등록만 하면 된다.

## 실무 사용 사례

### 설정 객체 복제

환경별 설정을 만들 때 자주 쓰는 패턴이다. 기본 설정을 먼저 만들고, 환경에 따라 일부만 바꾼다.

```javascript
class AppConfig {
    constructor() {
        this.server = { host: 'localhost', port: 3000 };
        this.database = {
            host: 'localhost',
            port: 5432,
            name: 'myapp',
            pool: { min: 2, max: 10 }
        };
        this.cache = { ttl: 3600, maxSize: 1000 };
        this.logging = { level: 'info', format: 'json' };
    }

    clone() {
        const cloned = new AppConfig();
        cloned.server = structuredClone(this.server);
        cloned.database = structuredClone(this.database);
        cloned.cache = structuredClone(this.cache);
        cloned.logging = structuredClone(this.logging);
        return cloned;
    }
}

// 기본 설정
const baseConfig = new AppConfig();

// production 설정: 기본 설정을 복제하고 필요한 부분만 변경
const prodConfig = baseConfig.clone();
prodConfig.server.host = '0.0.0.0';
prodConfig.server.port = 443;
prodConfig.database.host = 'db.prod.internal';
prodConfig.database.pool.min = 10;
prodConfig.database.pool.max = 50;
prodConfig.logging.level = 'warn';

// staging 설정
const stagingConfig = baseConfig.clone();
stagingConfig.server.port = 8080;
stagingConfig.database.host = 'db.staging.internal';
stagingConfig.database.name = 'myapp_staging';
stagingConfig.logging.level = 'debug';
```

설정 항목이 수십 개인 경우, `new`로 매번 전부 지정하는 것보다 복제 후 차이점만 수정하는 쪽이 실수가 적다.

### 테스트 데이터 생성

테스트 코드에서 기본 데이터를 만들어두고 테스트마다 필요한 부분만 바꾸는 방식이다.

```javascript
// 테스트용 기본 사용자 객체
const baseUser = {
    id: null,
    email: 'test@example.com',
    name: '홍길동',
    role: 'user',
    profile: {
        age: 30,
        address: { city: '서울', district: '강남구' },
        preferences: { theme: 'light', language: 'ko' }
    },
    permissions: ['read'],
    createdAt: new Date('2026-01-01')
};

function createTestUser(overrides = {}) {
    const user = structuredClone(baseUser);
    user.id = `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    // 중첩 객체도 부분 덮어쓰기
    for (const [key, value] of Object.entries(overrides)) {
        if (typeof value === 'object' && value !== null && !Array.isArray(value)
            && typeof user[key] === 'object' && user[key] !== null) {
            Object.assign(user[key], value);
        } else {
            user[key] = value;
        }
    }

    return user;
}

// 테스트에서 사용
const adminUser = createTestUser({
    role: 'admin',
    permissions: ['read', 'write', 'delete'],
    profile: { address: { city: '부산' } }
});

const inactiveUser = createTestUser({
    role: 'user',
    permissions: []
});
```

테스트마다 객체를 처음부터 만들면 테스트 코드가 길어지고, 스키마가 바뀔 때 모든 테스트를 수정해야 한다. 기본 객체를 복제하면 변경 지점이 하나로 줄어든다.

### 캐시된 객체 복제

캐시에서 꺼낸 객체를 그대로 반환하면, 호출자가 수정했을 때 캐시 데이터가 오염된다. 복제본을 반환해야 안전하다.

```javascript
class ObjectCache {
    #cache = new Map();
    #ttl;

    constructor(ttlMs = 60000) {
        this.#ttl = ttlMs;
    }

    set(key, value) {
        this.#cache.set(key, {
            data: value,
            cachedAt: Date.now()
        });
    }

    get(key) {
        const entry = this.#cache.get(key);
        if (!entry) return null;

        // TTL 만료 확인
        if (Date.now() - entry.cachedAt > this.#ttl) {
            this.#cache.delete(key);
            return null;
        }

        // 복제본을 반환한다. 원본 캐시 데이터를 보호하기 위해서다.
        return structuredClone(entry.data);
    }
}

const cache = new ObjectCache(30000);

// API 응답을 캐시
const apiResponse = {
    users: [
        { id: 1, name: '김철수', score: 85 },
        { id: 2, name: '이영희', score: 92 }
    ],
    total: 2,
    page: 1
};
cache.set('user-list', apiResponse);

// 다른 곳에서 캐시를 가져와 가공
const result = cache.get('user-list');
result.users = result.users.filter(u => u.score >= 90);

// 원본 캐시 데이터는 영향 없음
const original = cache.get('user-list');
console.log(original.users.length); // 2 — 원본 유지
```

이 패턴을 안 쓰면 디버깅이 어려운 버그가 생긴다. A 요청에서 캐시 데이터를 수정했더니 B 요청에서 이상한 데이터가 내려오는 식이다. 캐시 복제를 빼먹어서 생기는 버그는 재현 조건이 타이밍에 따라 달라지기 때문에 원인을 찾기 어렵다.

## 주의사항

### 복사 비용

깊은 복사는 공짜가 아니다. 객체 크기에 비례해서 시간과 메모리를 소모한다. 대용량 객체를 매 요청마다 복제하면 성능 문제가 생긴다.

```javascript
// 이런 식으로 쓰면 안 된다
function handleRequest(req) {
    // 수백 KB짜리 객체를 매 요청마다 깊은 복사
    const config = structuredClone(hugeGlobalConfig);
    // config에서 server.port 하나만 읽는다면 복사할 이유가 없다
    return config.server.port;
}
```

읽기만 하는 경우에는 복제할 필요가 없다. 복제는 수정이 필요한 경우에만 한다.

### clone() 메서드의 일관성

팀에서 Prototype 패턴을 쓴다면, `clone()` 메서드의 계약을 명확히 해야 한다. 어떤 클래스는 얕은 복사를 하고, 어떤 클래스는 깊은 복사를 하면 혼란이 생긴다.

```javascript
// 인터페이스를 정해두면 혼란을 줄인다
// (JavaScript에는 인터페이스가 없으므로 규약으로 관리)

// 규약: clone()은 항상 깊은 복사를 반환한다.
// 반환된 객체를 수정해도 원본에 영향을 주지 않아야 한다.
class Order {
    clone() {
        const cloned = new Order();
        cloned.items = this.items.map(item => item.clone());
        cloned.customer = this.customer.clone();
        cloned.shippingAddress = structuredClone(this.shippingAddress);
        return cloned;
    }
}
```

### 상속 구조에서의 복제

부모 클래스의 `clone()`을 자식 클래스가 오버라이드하지 않으면, 복제본이 부모 타입으로 생성될 수 있다.

```javascript
class Shape {
    constructor(color) {
        this.color = color;
    }

    clone() {
        return new Shape(this.color);
    }
}

class Circle extends Shape {
    constructor(color, radius) {
        super(color);
        this.radius = radius;
    }

    // clone()을 오버라이드하지 않으면 Shape로 복제된다
    // radius 정보가 사라진다
}

const circle = new Circle('red', 10);
const cloned = circle.clone();

console.log(cloned instanceof Circle);  // false
console.log(cloned.radius);             // undefined
```

자식 클래스는 반드시 `clone()`을 오버라이드해야 한다:

```javascript
class Circle extends Shape {
    constructor(color, radius) {
        super(color);
        this.radius = radius;
    }

    clone() {
        return new Circle(this.color, this.radius);
    }
}
```
