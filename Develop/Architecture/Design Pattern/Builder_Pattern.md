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
