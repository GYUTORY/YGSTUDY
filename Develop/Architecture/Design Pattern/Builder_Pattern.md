---
title: Builder Pattern (빌더 패턴)
tags: [design-patterns, nodejs, backend, architecture]
updated: 2026-08-07
---

# Builder Pattern (빌더 패턴)

## 빌더 패턴

빌더 패턴은 **복잡한 객체의 생성 과정을 단계별로 분리하여 가독성과 유연성을 높이는** 패턴입니다. Node.js 백엔드 개발에서 주로 사용되는 경우:

**사용 사례:**
- **HTTP 요청 구성**: 복잡한 API 요청 파라미터 구성
- **데이터베이스 쿼리 빌더**: 동적 SQL 쿼리 생성
- **이메일 메시지 구성**: 복잡한 이메일 템플릿 생성
- **설정 객체 구성**: 환경별 복잡한 설정 객체 생성
- **API 응답 구성**: 복잡한 JSON 응답 구조 생성
- **로그 메시지 구성**: 구조화된 로그 엔트리 생성

**언제 사용하는가?**
- 생성자에 많은 매개변수가 필요한 경우
- 매개변수의 순서가 중요하지 않은 경우
- 객체 생성 과정이 복잡한 경우
- 불변 객체를 생성해야 하는 경우

## 패턴 구조

```
Director (감독자)
├── Builder (추상 빌더)
│   ├── ConcreteBuilderA (구체 빌더 A)
│   └── ConcreteBuilderB (구체 빌더 B)
└── Product (제품)
```

## 기본 구현

### 1. HTTP 요청 빌더

```javascript
// builders/http-request-builder.js - HTTP 요청 빌더
const axios = require('axios');

class HttpRequest {
    constructor(builder) {
        // 필수 구성 요소
        this.url = builder.url;
        this.method = builder.method;
        
        // 선택적 구성 요소
        this.headers = builder.headers || {};
        this.params = builder.params || {};
        this.data = builder.data || null;
        this.timeout = builder.timeout || 5000;
        this.retries = builder.retries || 0;
        this.retryDelay = builder.retryDelay || 1000;
        this.auth = builder.auth || null;
        this.proxy = builder.proxy || null;
        this.validateStatus = builder.validateStatus || null;
        this.maxRedirects = builder.maxRedirects || 5;
        this.responseType = builder.responseType || 'json';
        this.withCredentials = builder.withCredentials || false;
        
        // 메타데이터
        this.createdAt = new Date();
        this.id = Math.random().toString(36).substr(2, 9);
    }

    async execute() {
        try {
            const response = await axios({
                url: this.url,
                method: this.method,
                headers: this.headers,
                params: this.params,
                data: this.data,
                timeout: this.timeout,
                auth: this.auth,
                proxy: this.proxy,
                validateStatus: this.validateStatus,
                maxRedirects: this.maxRedirects,
                responseType: this.responseType,
                withCredentials: this.withCredentials
            });
            
            return {
                success: true,
                data: response.data,
                status: response.status,
                headers: response.headers,
                requestId: this.id
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                status: error.response?.status,
                requestId: this.id
            };
        }
    }

    getInfo() {
        return {
            id: this.id,
            method: this.method,
            url: this.url,
            headers: this.headers,
            timeout: this.timeout,
            retries: this.retries,
            createdAt: this.createdAt
        };
    }
}

// HTTP 요청 빌더
class HttpRequestBuilder {
    constructor() {
        this.reset();
    }

    reset() {
        this.url = null;
        this.method = 'GET';
        this.headers = {};
        this.params = {};
        this.data = null;
        this.timeout = 5000;
        this.retries = 0;
        this.retryDelay = 1000;
        this.auth = null;
        this.proxy = null;
        this.validateStatus = null;
        this.maxRedirects = 5;
        this.responseType = 'json';
        this.withCredentials = false;
        return this;
    }
    
    setUrl(url) {
        this.url = url;
        return this;
    }
    
    setMethod(method) {
        this.method = method.toUpperCase();
        return this;
    }
    
    setHeaders(headers) {
        this.headers = { ...this.headers, ...headers };
        return this;
    }
    
    setHeader(key, value) {
        this.headers[key] = value;
        return this;
    }

    setParams(params) {
        this.params = { ...this.params, ...params };
        return this;
    }

    setParam(key, value) {
        this.params[key] = value;
        return this;
    }

    setData(data) {
        this.data = data;
        return this;
    }

    setTimeout(timeout) {
        this.timeout = timeout;
        return this;
    }

    setRetries(retries, delay = 1000) {
        this.retries = retries;
        this.retryDelay = delay;
        return this;
    }

    setAuth(username, password) {
        this.auth = { username, password };
        return this;
    }

    setBearerToken(token) {
        this.headers['Authorization'] = `Bearer ${token}`;
        return this;
    }

    setProxy(proxy) {
        this.proxy = proxy;
        return this;
    }

    setResponseType(type) {
        this.responseType = type;
        return this;
    }

    setWithCredentials(credentials) {
        this.withCredentials = credentials;
        return this;
    }

    // 편의 메서드들
    asGet() {
        return this.setMethod('GET');
    }

    asPost() {
        return this.setMethod('POST');
    }

    asPut() {
        return this.setMethod('PUT');
    }

    asDelete() {
        return this.setMethod('DELETE');
    }

    withJson(data) {
        return this.setMethod('POST')
                  .setHeader('Content-Type', 'application/json')
                  .setData(data);
    }

    withFormData(data) {
        return this.setMethod('POST')
                  .setHeader('Content-Type', 'application/x-www-form-urlencoded')
                  .setData(data);
    }

    withAuth(token) {
        return this.setBearerToken(token);
    }

    withTimeout(timeout) {
        return this.setTimeout(timeout);
    }

    withRetries(retries, delay = 1000) {
        return this.setRetries(retries, delay);
    }
    
    build() {
        if (!this.url) {
            throw new Error('URL은 필수입니다.');
        }
        
        return new HttpRequest(this);
    }
}

module.exports = {
    HttpRequest,
    HttpRequestBuilder
};
```

**사용 예시:**
```javascript
// services/api-client.js
const { HttpRequestBuilder } = require('../builders/http-request-builder');

class ApiClient {
    async getUserById(id, token) {
        const request = new HttpRequestBuilder()
            .setUrl(`https://api.example.com/users/${id}`)
            .asGet()
            .withAuth(token)
            .withTimeout(10000)
            .withRetries(3, 2000)
            .build();

        return await request.execute();
    }

    async createUser(userData, token) {
        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com/users')
            .withJson(userData)
            .withAuth(token)
            .setHeader('X-Request-ID', Math.random().toString(36))
            .build();

        return await request.execute();
    }

    async uploadFile(file, token) {
        const formData = new FormData();
        formData.append('file', file);

        const request = new HttpRequestBuilder()
            .setUrl('https://api.example.com/upload')
            .withFormData(formData)
            .withAuth(token)
            .setTimeout(30000)
            .build();

        return await request.execute();
    }
}
```

### 2. 데이터베이스 쿼리 빌더

```javascript
// builders/query-builder.js - 데이터베이스 쿼리 빌더
class Query {
    constructor(builder) {
        this.table = builder.table;
        this.select = builder.select || ['*'];
        this.where = builder.where || [];
        this.orderBy = builder.orderBy || [];
        this.groupBy = builder.groupBy || [];
        this.having = builder.having || [];
        this.limit = builder.limit || null;
        this.offset = builder.offset || null;
        this.joins = builder.joins || [];
        this.distinct = builder.distinct || false;
        this.lock = builder.lock || null;
    }

    toSQL() {
        let sql = '';
        
        // SELECT 절
        if (this.distinct) {
            sql += `SELECT DISTINCT ${this.select.join(', ')}`;
        } else {
            sql += `SELECT ${this.select.join(', ')}`;
        }
        
        // FROM 절
        sql += ` FROM ${this.table}`;
        
        // JOIN 절
        if (this.joins.length > 0) {
            sql += ' ' + this.joins.join(' ');
        }
        
        // WHERE 절
        if (this.where.length > 0) {
            sql += ` WHERE ${this.where.join(' AND ')}`;
        }
        
        // GROUP BY 절
        if (this.groupBy.length > 0) {
            sql += ` GROUP BY ${this.groupBy.join(', ')}`;
        }
        
        // HAVING 절
        if (this.having.length > 0) {
            sql += ` HAVING ${this.having.join(' AND ')}`;
        }
        
        // ORDER BY 절
        if (this.orderBy.length > 0) {
            sql += ` ORDER BY ${this.orderBy.join(', ')}`;
        }
        
        // LIMIT 절
        if (this.limit) {
            sql += ` LIMIT ${this.limit}`;
        }
        
        // OFFSET 절
        if (this.offset) {
            sql += ` OFFSET ${this.offset}`;
        }
        
        // LOCK 절
        if (this.lock) {
            sql += ` ${this.lock}`;
        }
        
        return sql;
    }

    getInfo() {
        return {
            table: this.table,
            select: this.select,
            where: this.where,
            orderBy: this.orderBy,
            limit: this.limit,
            offset: this.offset,
            sql: this.toSQL()
        };
    }
}

// 쿼리 빌더
class QueryBuilder {
    constructor() {
        this.reset();
    }

    reset() {
        this.table = null;
        this.select = ['*'];
        this.where = [];
        this.orderBy = [];
        this.groupBy = [];
        this.having = [];
        this.limit = null;
        this.offset = null;
        this.joins = [];
        this.distinct = false;
        this.lock = null;
        return this;
    }

    from(table) {
        this.table = table;
        return this;
    }

    select(columns) {
        if (Array.isArray(columns)) {
            this.select = columns;
        } else {
            this.select = [columns];
        }
        return this;
    }

    where(condition, operator = 'AND') {
        if (typeof condition === 'string') {
            this.where.push(condition);
        } else if (typeof condition === 'object') {
            const conditions = Object.entries(condition)
                .map(([key, value]) => `${key} = '${value}'`)
                .join(` ${operator} `);
            this.where.push(conditions);
        }
        return this;
    }

    whereIn(column, values) {
        const valueList = values.map(v => `'${v}'`).join(', ');
        this.where.push(`${column} IN (${valueList})`);
        return this;
    }

    whereBetween(column, min, max) {
        this.where.push(`${column} BETWEEN '${min}' AND '${max}'`);
        return this;
    }

    whereNull(column) {
        this.where.push(`${column} IS NULL`);
        return this;
    }

    whereNotNull(column) {
        this.where.push(`${column} IS NOT NULL`);
        return this;
    }

    orderBy(column, direction = 'ASC') {
        this.orderBy.push(`${column} ${direction.toUpperCase()}`);
        return this;
    }

    groupBy(columns) {
        if (Array.isArray(columns)) {
            this.groupBy = [...this.groupBy, ...columns];
        } else {
            this.groupBy.push(columns);
        }
        return this;
    }

    having(condition) {
        this.having.push(condition);
        return this;
    }

    limit(count) {
        this.limit = count;
        return this;
    }

    offset(count) {
        this.offset = count;
        return this;
    }

    join(table, on, type = 'INNER') {
        this.joins.push(`${type} JOIN ${table} ON ${on}`);
        return this;
    }

    leftJoin(table, on) {
        return this.join(table, on, 'LEFT');
    }

    rightJoin(table, on) {
        return this.join(table, on, 'RIGHT');
    }

    distinct() {
        this.distinct = true;
        return this;
    }

    lock(lockType = 'FOR UPDATE') {
        this.lock = lockType;
        return this;
    }

    // 편의 메서드들
    findById(id) {
        return this.where('id', id).limit(1);
    }

    findByEmail(email) {
        return this.where('email', email).limit(1);
    }

    paginate(page, perPage = 10) {
        const offset = (page - 1) * perPage;
        return this.limit(perPage).offset(offset);
    }

    build() {
        if (!this.table) {
            throw new Error('테이블명은 필수입니다.');
        }
        
        return new Query(this);
    }
}

module.exports = {
    Query,
    QueryBuilder
};
```

**사용 예시:**
```javascript
// services/user-service.js
const { QueryBuilder } = require('../builders/query-builder');

class UserService {
    async getUsers(filters = {}) {
        const query = new QueryBuilder()
            .from('users')
            .select(['id', 'name', 'email', 'created_at'])
            .where('active', true)
            .orderBy('created_at', 'DESC')
            .limit(100)
            .build();

        return await this.db.query(query.toSQL());
    }

    async getUserById(id) {
        const query = new QueryBuilder()
            .from('users')
            .findById(id)
            .build();

        const result = await this.db.query(query.toSQL());
        return result[0];
    }

    async searchUsers(searchTerm, page = 1) {
        const query = new QueryBuilder()
            .from('users')
            .select(['id', 'name', 'email'])
            .where(`name LIKE '%${searchTerm}%' OR email LIKE '%${searchTerm}%'`)
            .orderBy('name', 'ASC')
            .paginate(page, 20)
            .build();

        return await this.db.query(query.toSQL());
    }

    async getUsersWithOrders() {
        const query = new QueryBuilder()
            .from('users')
            .select(['users.id', 'users.name', 'COUNT(orders.id) as order_count'])
            .leftJoin('orders', 'users.id = orders.user_id')
            .where('users.active', true)
            .groupBy(['users.id', 'users.name'])
            .having('COUNT(orders.id) > 0')
            .orderBy('order_count', 'DESC')
            .build();

        return await this.db.query(query.toSQL());
    }
}
```

### 위 쿼리 빌더는 실행하면 첫 체이닝에서 죽는다

`QueryBuilder` 를 그대로 옮겨 실행하면 `.select([...])` 에서 `TypeError: ... .select is not a function` 이 난다. SQL 문법 문제가 아니라 프로퍼티 조회 순서 문제다.

`reset()` 이 `this.select = ['*']` 로 **인스턴스 자기 프로퍼티**를 만든다. 같은 이름의 메서드는 프로토타입에 있다. 조회는 인스턴스가 먼저라 배열이 메서드를 가린다.

```javascript
const b = new QueryBuilder();
typeof b.select                       // 'object'   ← reset() 이 넣은 배열
typeof QueryBuilder.prototype.select  // 'function' ← 가려진 메서드
```

`reset()` 의 키와 메서드 이름이 겹치는 것은 9개다 — `select` `where` `orderBy` `groupBy` `having` `limit` `offset` `distinct` `lock`. 사실상 빌더의 주요 메서드 전부다. `from()` 과 `join()` 계열만 살아남는다.

빌더는 "메서드 이름 = 만들려는 필드 이름" 으로 수렴하는 성질이 있어서 이 충돌은 우연이 아니라 구조적으로 잘 난다. **문법 오류가 아니라 린터도 그냥 넘어가고**, 그 메서드를 실제로 호출하는 경로가 실행돼야 드러난다. 상태 필드에 접두사를 붙여 이름 공간을 나누는 것이 가장 단순한 해법이다.

```javascript
class QueryBuilder {
  reset() {
    this._table = null;
    this._select = ['*'];
    this._where = [];
    return this;
  }
  select(columns) { this._select = Array.isArray(columns) ? columns : [columns]; return this; }
  where(condition) { this._where.push(condition); return this; }
}
```

### `where('active', true)` 는 `active = true` 가 되지 않는다

`where(condition, operator = 'AND')` 의 두 번째 인자는 값이 아니라 조건들을 잇는 연산자 자리다. 첫 인자가 문자열이면 그대로 WHERE 절에 밀어 넣으므로 `.where('active', true)` 는 `WHERE active` 를 만들고 `true` 는 버린다. `findById(id)` 도 내부에서 `this.where('id', id)` 를 부르니 `WHERE id LIMIT 1` 이 된다 — 찾으려던 id 값이 통째로 사라진다.

키-값을 넘기려면 객체 분기를 써야 한다.

```javascript
.where({ active: true })   // → active = 'true'
```

이름 충돌을 고치더라도 위 사용 예시(`getUsers`, `getUsersWithOrders`)는 전부 문자열 2인자 형태라 조건이 빠진 SQL 이 나간다. **체이닝 API 는 잘못 써도 예외가 안 나고 조용히 다른 쿼리를 만든다** — 빌더를 직접 만들 때 가장 신경 써야 할 지점이다.

### 값을 문자열로 이어 붙이면 쿼리 빌더가 아니다

`${key} = '${value}'`, `values.map(v => "'" + v + "'")` 에는 이스케이프가 없다. `searchUsers` 는 사용자 입력을 `LIKE '%...%'` 안에 그대로 넣는다. 작은따옴표 하나만 들어와도 문법이 깨지고, 그 지점이 곧 주입 지점이다.

빌더 패턴 자체의 결함은 아니지만, **쿼리 빌더를 만들 때 먼저 결정할 것은 체이닝 API 모양이 아니라 "값을 어디에 담을 것인가"** 다. SQL 문자열과 바인딩 파라미터를 함께 쌓아 두 개를 같이 반환하는 형태가 기본이다.

```javascript
build() {
  return {
    sql: `SELECT ${this._select.join(', ')} FROM ${this._table} WHERE email = ?`,
    params: [this._email]
  };
}
```

식별자(테이블명·컬럼명)는 파라미터로 바인딩할 수 없으니 화이트리스트로 검증하는 수밖에 없다. 이 둘을 구분하지 않으면 "파라미터 쓰니까 안전하다"고 착각하게 된다.

## Builder 패턴 장단점

### 장점

**1. 뛰어난 가독성**
```javascript
// 빌더 패턴 사용 - 가독성 좋음
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asPost()
    .withJson(userData)
    .withAuth(token)
    .withTimeout(10000)
    .withRetries(3, 2000)
    .build();

// vs 생성자 패턴 - 가독성 나쁨
const request = new HttpRequest(
    'https://api.example.com/users',
    'POST',
    { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    userData,
    10000,
    3,
    2000,
    null,
    null,
    null,
    5,
    'json',
    false
);
```

**2. 높은 유연성**
```javascript
// 필요한 부분만 설정 가능
const simpleQuery = new QueryBuilder()
    .from('users')
    .select(['id', 'name'])
    .build();

// 복잡한 쿼리도 단계별로 구성 가능
const complexQuery = new QueryBuilder()
    .from('users')
    .select(['users.id', 'users.name', 'COUNT(orders.id) as order_count'])
    .leftJoin('orders', 'users.id = orders.user_id')
    .where('users.active', true)
    .groupBy(['users.id', 'users.name'])
    .having('COUNT(orders.id) > 0')
    .orderBy('order_count', 'DESC')
    .limit(100)
    .build();
```

**3. 불변 객체 생성**
```javascript
// 빌더로 생성된 객체는 불변
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asGet()
    .build();

// request 객체는 생성 후 변경 불가
// request.url = 'https://malicious.com'; // 불가능
```

> 이 주장은 위 코드에서 성립하지 않는다. 실제로 실행해 보면 `request.url = 'https://malicious.com'` 이 그대로 먹고 `Object.isFrozen(request)` 는 `false` 다. `HttpRequest` 는 평범한 클래스 인스턴스라 언어 차원에서 막는 것이 없다.

빌더가 주는 것은 "생성 이후 setter 를 노출하지 않는다"는 **관례**뿐이다. 불변을 실제로 강제하려면 `Object.freeze` 나 `#private` 필드를 직접 써야 한다.

여기에 더해 `HttpRequest` 는 빌더의 `headers` / `params` 객체를 **참조 그대로** 받는다. 얕은 복사조차 없다. 그래서 `build()` 이후 빌더 쪽에서 헤더를 하나 더 넣으면 이미 만들어진 요청에도 그 헤더가 나타난다. 빌더 인스턴스를 필드에 두고 재사용하는 코드에서 요청 간에 값이 조용히 섞인다.

```javascript
class HttpRequest {
  constructor(builder) {
    this.url = builder.url;
    this.headers = Object.freeze({ ...builder.headers });
    this.params  = Object.freeze({ ...builder.params });
    Object.freeze(this);
  }
}
```

`Object.freeze` 는 얕게 동작한다. 중첩 객체까지 막으려면 재귀로 얼리거나 애초에 중첩을 허용하지 않는다.

같은 맥락에서 `reset()` 을 둔 재사용형 빌더는 `build()` 가 `reset()` 을 부르지 않는다는 점을 봐야 한다. 같은 빌더로 두 번 `build()` 하면 앞 요청의 헤더·타임아웃이 그대로 남은 채 두 번째 객체가 만들어진다. 재사용을 허용할 거면 `build()` 마지막에 `reset()` 을 부르거나, 아예 매번 새 빌더를 만들도록 문서에 못 박는다.

**4. 유효성 검사와 검증**
```javascript
class HttpRequestBuilder {
    build() {
        if (!this.url) {
            throw new Error('URL은 필수입니다.');
        }
        
        if (this.method === 'POST' && !this.data) {
            throw new Error('POST 요청에는 데이터가 필요합니다.');
        }
        
        if (this.timeout < 1000) {
            throw new Error('타임아웃은 최소 1초 이상이어야 합니다.');
        }
        
        return new HttpRequest(this);
    }
}
```

**5. 단계별 객체 구성**
```javascript
// 복잡한 객체를 단계별로 구성
const email = new EmailBuilder()
    .to('user@example.com')
    .subject('환영합니다')
    .htmlBody('<h1>환영합니다!</h1>')
    .attach('welcome.pdf')
    .priority('high')
    .build();
```

### 단점

**1. 높은 복잡성**
```javascript
// 빌더 클래스가 복잡해질 수 있음
class HttpRequestBuilder {
    constructor() {
        this.reset(); // 15개 이상의 속성 초기화
    }
    
    // 20개 이상의 메서드
    setUrl() { /* ... */ }
    setMethod() { /* ... */ }
    setHeaders() { /* ... */ }
    // ... 더 많은 메서드들
}
```

**2. 메모리 오버헤드**
```javascript
// 빌더 인스턴스 생성으로 인한 메모리 사용량 증가
const builder = new HttpRequestBuilder(); // 메모리 사용
const request = builder.setUrl('...').build(); // 추가 메모리 사용
```

**3. 코드 중복**
```javascript
// 비슷한 빌더들 간의 중복 코드
class HttpRequestBuilder {
    setUrl(url) { this.url = url; return this; }
    setMethod(method) { this.method = method; return this; }
}

class DatabaseQueryBuilder {
    setUrl(url) { this.url = url; return this; } // 중복
    setMethod(method) { this.method = method; return this; } // 중복
}
```

**4. 런타임 에러 가능성**
```javascript
// 빌드 시점에 에러 발생 가능
const request = new HttpRequestBuilder()
    .setUrl('invalid-url') // 잘못된 URL
    .build(); // 런타임에 에러 발생
```

## 언제 사용해야 할까?

**적합한 경우:**
```javascript
// ✅ 복잡한 HTTP 요청 구성
const request = new HttpRequestBuilder()
    .setUrl('https://api.example.com/users')
    .asPost()
    .withJson(userData)
    .withAuth(token)
    .build();

// ✅ 동적 데이터베이스 쿼리 생성
const query = new QueryBuilder()
    .from('users')
    .where('active', true)
    .orderBy('created_at', 'DESC')
    .build();

// ✅ 복잡한 이메일 메시지 구성
const email = new EmailBuilder()
    .to(user.email)
    .subject('환영합니다')
    .htmlBody(template)
    .attach('welcome.pdf')
    .build();

// ✅ API 응답 구성
const response = new ApiResponseBuilder()
    .setData(users)
    .setPagination(page, total)
    .setMeta({ timestamp: new Date() })
    .build();
```

**부적합한 경우:**
```javascript
// ❌ 단순한 객체 생성
const user = { id: 1, name: '홍길동' }; // 빌더 불필요

// ❌ 매개변수가 적은 경우
const config = { host: 'localhost', port: 3000 }; // 빌더 불필요

// ❌ 성능이 중요한 경우
// 빌더 오버헤드로 인한 성능 저하
```

**판단 기준:**
1. **매개변수가 5개 이상인가?** (HTTP 요청, DB 쿼리)
2. **선택적 매개변수가 많은가?** (이메일, 설정 객체)
3. **가독성이 중요한가?** (API 클라이언트, 쿼리 빌더)
4. **유효성 검사가 필요한가?** (복잡한 객체 생성)

### 빌더를 넣으면 무엇을 포기하는가

장점은 위에 적혀 있으니 반대쪽만 적는다.

**검사 시점이 뒤로 밀린다.** 생성자에 인자를 빠뜨리면 타입 시스템이 잡지만, 빌더는 그 검사를 `build()` 안의 `if (!this.url) throw` 로 옮긴다. 컴파일 에러가 런타임 에러가 된다는 뜻이다. 위 "런타임 에러 가능성" 단점의 정체가 이것이고, 필수 필드가 늘수록 손해가 커진다. 타입스크립트라면 단계별 인터페이스(`UrlSet` → `MethodSet` → `Buildable`)로 되돌릴 수 있지만 그만큼 빌더가 복잡해진다.

**수정 지점이 두 배가 된다.** 필드를 하나 추가하려면 Product 와 Builder 양쪽을 고쳐야 한다. 한쪽만 고치면 예외 없이 `undefined` 가 흐른다.

**미완성 상태가 값으로 돌아다닌다.** 체이닝 중간의 빌더는 아직 유효하지 않은 객체인데도 변수에 담기고 함수 인자로 넘어갈 수 있다. 생성자는 "만들어졌으면 유효하다"가 보장되지만 빌더는 그 보장을 포기하는 대신 유연성을 얻는다.

| 빌더가 값을 하는 자리 | 빌더가 손해인 자리 |
|---|---|
| 선택 인자가 많고 대부분 기본값으로 두는 객체 | 필드가 서너 개고 전부 필수인 객체 |
| 조합이 유효한지 build 시점에 한 번 검사해야 할 때 | 객체 리터럴 + 구조 분해로 끝나는 설정 |
| 같은 골격에서 조금씩 다른 변형을 여러 개 찍을 때 | 한 곳에서 한 번 만들고 끝나는 객체 |
| 언어에 이름 있는 인자(named argument)가 없을 때 | 팩토리 함수나 DI 컨테이너가 이미 조립을 맡고 있을 때 |

마지막 줄이 자바스크립트에서 특히 중요하다. **객체 리터럴이 이미 이름 있는 인자 역할을 한다.** `new HttpRequest({ url, method, timeout })` 한 줄이면 위 "가독성" 장점의 상당 부분이 해결되고, 기본값은 구조 분해의 기본값(`{ timeout = 5000 } = {}`)으로 처리된다. 자바처럼 이름 있는 인자가 없는 언어에서 빌더가 흔한 이유가 여기 있다 — 언어가 메우지 못하는 자리를 패턴으로 메우는 것이다. 옵션 객체로 충분한지 먼저 보고 나서 빌더를 꺼낸다.

## 안티패턴

```javascript
// ❌ 나쁜 예: 단순한 객체에 빌더 사용
class SimpleUserBuilder {
    setName(name) { this.name = name; return this; }
    setEmail(email) { this.email = email; return this; }
    build() { return { name: this.name, email: this.email }; }
}

// ✅ 좋은 예: 복잡한 객체에만 빌더 사용
class ComplexHttpRequestBuilder {
    setUrl(url) { this.url = url; return this; }
    setMethod(method) { this.method = method; return this; }
    setHeaders(headers) { this.headers = headers; return this; }
    setBody(body) { this.body = body; return this; }
    setTimeout(timeout) { this.timeout = timeout; return this; }
    setRetries(retries) { this.retries = retries; return this; }
    build() { return new HttpRequest(this); }
}
```
