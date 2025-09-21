---
title: Proxy Pattern (프록시 패턴) 완전 가이드
tags: [design-pattern, proxy-pattern, structural-pattern, javascript, architecture]
updated: 2025-09-23
---

# Proxy Pattern (프록시 패턴) 완전 가이드

## 개요

### 프록시 패턴이란
프록시 패턴(Proxy Pattern)은 구조적 디자인 패턴의 하나로, 다른 객체에 대한 접근을 제어하는 대리 객체를 제공하는 패턴입니다. 이 패턴은 원본 객체와 동일한 인터페이스를 제공하면서도, 클라이언트의 요청을 가로채서 추가적인 작업을 수행하거나 원본 객체에 대한 접근을 제어할 수 있습니다.

### 프록시 패턴의 핵심 원리
프록시 패턴은 "대리자"의 개념을 프로그래밍에 적용한 것입니다. 실제 객체에 직접 접근하는 대신, 프록시 객체를 통해 간접적으로 접근함으로써 다음과 같은 이점을 얻을 수 있습니다:

1. **접근 제어**: 객체에 대한 접근 권한을 세밀하게 제어
2. **기능 확장**: 원본 객체의 기능을 수정하지 않고도 새로운 기능 추가
3. **성능 최적화**: 캐싱, 지연 로딩 등을 통한 효율성 향상
4. **보안 강화**: 인증, 권한 검증 등의 보안 기능 구현

### 기본 구성 요소
- **Subject (주체)**: RealSubject와 Proxy가 공통으로 구현하는 인터페이스
- **RealSubject (실제 주체)**: 실제 비즈니스 로직을 수행하는 원본 객체
- **Proxy (프록시)**: RealSubject에 대한 접근을 제어하는 대리 객체
- **Client (클라이언트)**: Proxy를 통해 RealSubject에 접근하는 사용자

## 프록시 패턴의 상세 분석

### 1. 프록시 패턴의 구조와 동작 원리

#### UML 다이어그램 구조
```
Client → Proxy → RealSubject
         ↓
    Subject Interface
```

프록시 패턴은 다음과 같은 구조로 동작합니다:

1. **Subject Interface**: RealSubject와 Proxy가 공통으로 구현하는 인터페이스
2. **RealSubject**: 실제 비즈니스 로직을 수행하는 원본 객체
3. **Proxy**: RealSubject에 대한 접근을 제어하는 대리 객체
4. **Client**: Proxy를 통해 RealSubject에 접근하는 사용자

#### 동작 흐름
1. 클라이언트가 프록시 객체에 요청을 전송
2. 프록시가 요청을 받아 추가적인 작업 수행 (인증, 로깅, 캐싱 등)
3. 프록시가 실제 객체(RealSubject)에 요청을 전달
4. 실제 객체가 요청을 처리하고 결과를 프록시에 반환
5. 프록시가 결과를 받아 추가적인 후처리 수행
6. 최종 결과를 클라이언트에 반환

### 2. 프록시 패턴의 장단점

#### 장점
- **투명성**: 클라이언트는 프록시와 실제 객체를 구분하지 않고 동일한 인터페이스로 사용
- **유연성**: 실제 객체를 수정하지 않고도 기능을 확장하거나 제어 가능
- **보안**: 접근 권한 제어, 인증, 권한 검증 등의 보안 기능 구현 가능
- **성능**: 캐싱, 지연 로딩 등을 통한 성능 최적화 가능
- **모니터링**: 객체 사용에 대한 로깅, 추적, 모니터링 기능 추가 가능

#### 단점
- **복잡성**: 추가적인 추상화 계층으로 인한 시스템 복잡성 증가
- **성능 오버헤드**: 프록시를 통한 간접 호출로 인한 약간의 성능 저하
- **디버깅 어려움**: 프록시를 통한 간접 호출로 인한 디버깅 복잡성
- **메모리 사용량**: 프록시 객체로 인한 추가 메모리 사용

### 3. 기본 프록시 패턴 구현

#### 기본 구조 구현
```javascript
// Subject 인터페이스 정의
class Subject {
    request() {
        throw new Error("request() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// RealSubject 클래스 - 실제 비즈니스 로직을 수행하는 객체
class RealSubject extends Subject {
    request() {
        console.log("RealSubject: 실제 서비스에서 데이터를 처리합니다.");
        return "실제 서비스에서 데이터를 가져옵니다.";
    }
}

// Proxy 클래스 - RealSubject에 대한 접근을 제어하는 대리 객체
class Proxy extends Subject {
    constructor() {
        super();
        this.realSubject = new RealSubject();
    }

    request() {
        // 프록시에서 요청 전 추가 작업 수행
        console.log("Proxy: 요청 전에 접근 권한을 확인합니다.");
        
        // 실제 객체에 요청 전달
        const result = this.realSubject.request();
        
        // 프록시에서 요청 후 추가 작업 수행
        console.log("Proxy: 요청 후 로깅을 수행합니다.");
        return result;
    }
}

// 클라이언트 코드
const proxy = new Proxy();
console.log(proxy.request());
```

#### 실행 결과
```
Proxy: 요청 전에 접근 권한을 확인합니다.
RealSubject: 실제 서비스에서 데이터를 처리합니다.
Proxy: 요청 후 로깅을 수행합니다.
실제 서비스에서 데이터를 가져옵니다.
```

## 프록시 패턴의 실제 구현 사례

### 1. 접근 제어 프록시 (Access Control Proxy)

접근 제어 프록시는 사용자의 권한에 따라 객체에 대한 접근을 제어하는 프록시입니다. 이는 보안이 중요한 시스템에서 매우 유용합니다.

```javascript
// 실제 데이터 서비스 클래스
class DataService {
    modifyData(user, data) {
        console.log(`${user}가 데이터를 수정함: ${data}`);
        return "데이터 수정 완료";
    }

    readData(user) {
        console.log(`${user}가 데이터를 읽음`);
        return "데이터 내용";
    }
}

// 접근 제어 프록시 클래스
class AccessControlProxy {
    constructor() {
        this.dataService = new DataService();
        this.adminUsers = ["admin", "manager"];
        this.readOnlyUsers = ["guest", "user"];
    }

    modifyData(user, data) {
        // 관리자 권한 확인
        if (!this.adminUsers.includes(user)) {
            console.log("접근 거부: 관리자만 데이터를 수정할 수 있습니다.");
            return null;
        }
        
        console.log("접근 허용: 관리자 권한이 확인되었습니다.");
        return this.dataService.modifyData(user, data);
    }

    readData(user) {
        // 읽기 권한 확인
        if (!this.adminUsers.includes(user) && !this.readOnlyUsers.includes(user)) {
            console.log("접근 거부: 데이터 읽기 권한이 없습니다.");
            return null;
        }
        
        return this.dataService.readData(user);
    }
}

// 사용 예시
const proxy = new AccessControlProxy();

// 권한이 없는 사용자의 수정 시도
proxy.modifyData("guest", "비밀번호 변경"); // 접근 거부

// 관리자의 수정 시도
proxy.modifyData("admin", "비밀번호 변경"); // 접근 허용

// 일반 사용자의 읽기 시도
proxy.readData("user"); // 데이터 읽기 허용
```

### 2. 캐싱 프록시 (Caching Proxy)

캐싱 프록시는 자주 요청되는 데이터를 메모리에 저장하여 성능을 향상시키는 프록시입니다. 동일한 요청이 반복될 때 실제 서비스를 호출하지 않고 캐시된 데이터를 반환합니다.

```javascript
// 실제 API 서비스 클래스
class APIService {
    fetchData(query) {
        console.log(`API 요청: ${query} 검색을 수행합니다.`);
        // 실제로는 네트워크 요청을 수행하는 비용이 큰 작업
        return `${query} 검색 결과 데이터`;
    }
}

// 캐싱 프록시 클래스
class CachingProxy {
    constructor() {
        this.apiService = new APIService();
        this.cache = new Map();
        this.cacheExpiry = 5 * 60 * 1000; // 5분 캐시 유효 시간
    }

    fetchData(query) {
        const cacheKey = query;
        const cached = this.cache.get(cacheKey);
        
        // 캐시된 데이터가 있고 유효한지 확인
        if (cached && Date.now() - cached.timestamp < this.cacheExpiry) {
            console.log("캐시된 데이터를 반환합니다.");
            return cached.data;
        }

        console.log("새로운 API 요청을 처리합니다.");
        const result = this.apiService.fetchData(query);
        
        // 결과를 캐시에 저장
        this.cache.set(cacheKey, {
            data: result,
            timestamp: Date.now()
        });
        
        return result;
    }

    clearCache() {
        this.cache.clear();
        console.log("캐시가 초기화되었습니다.");
    }

    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }
}

// 사용 예시
const apiProxy = new CachingProxy();

// 첫 번째 요청 - API 호출
console.log(apiProxy.fetchData("Node.js"));

// 두 번째 요청 - 캐시에서 반환
console.log(apiProxy.fetchData("Node.js"));

// 다른 쿼리 요청 - 새로운 API 호출
console.log(apiProxy.fetchData("JavaScript"));

// 캐시 통계 확인
console.log(apiProxy.getCacheStats());
```

### 3. 가상 프록시 (Virtual Proxy) - 지연 로딩

가상 프록시는 실제 객체의 생성 비용이 클 때, 실제로 필요할 때까지 객체 생성을 지연시키는 프록시입니다. 이는 메모리 사용량을 최적화하고 초기 로딩 시간을 단축시킵니다.

```javascript
// 무거운 객체 클래스 - 초기화에 많은 리소스가 필요한 객체
class HeavyObject {
    constructor() {
        console.log("무거운 객체가 생성되었습니다.");
        // 실제로는 많은 리소스를 사용하는 초기화 작업
        // 예: 대용량 데이터 로딩, 복잡한 계산, 외부 리소스 연결 등
        this.initialize();
    }

    initialize() {
        // 시뮬레이션을 위한 지연
        console.log("무거운 초기화 작업을 수행합니다...");
    }

    doSomething() {
        return "무거운 작업을 수행합니다.";
    }

    getData() {
        return "대용량 데이터";
    }
}

// 가상 프록시 클래스
class VirtualProxy {
    constructor() {
        this.realObject = null;
        this.isInitialized = false;
    }

    doSomething() {
        this.ensureInitialized();
        return this.realObject.doSomething();
    }

    getData() {
        this.ensureInitialized();
        return this.realObject.getData();
    }

    ensureInitialized() {
        if (!this.isInitialized) {
            console.log("가상 프록시: 실제 객체 생성을 시작합니다...");
            this.realObject = new HeavyObject();
            this.isInitialized = true;
        }
    }

    isObjectCreated() {
        return this.isInitialized;
    }
}

// 사용 예시
const proxy = new VirtualProxy();

// 이 시점에서는 실제 객체가 생성되지 않음
console.log("프록시 생성 완료. 실제 객체는 아직 생성되지 않았습니다.");
console.log("객체 생성 여부:", proxy.isObjectCreated());

// 실제 메서드 호출 시에만 객체가 생성됨
console.log(proxy.doSomething());
console.log("객체 생성 여부:", proxy.isObjectCreated());
```

### 4. 보호 프록시 (Protection Proxy)

보호 프록시는 객체에 대한 접근을 제어하여 보안을 강화하는 프록시입니다. 사용자의 권한이나 역할에 따라 특정 작업의 수행을 허용하거나 거부합니다.

```javascript
// 실제 은행 계좌 클래스
class BankAccount {
    constructor(balance) {
        this.balance = balance;
    }

    getBalance() {
        return this.balance;
    }

    withdraw(amount) {
        if (amount <= this.balance) {
            this.balance -= amount;
            return `출금 완료: ${amount}원`;
        }
        return "잔액 부족";
    }

    deposit(amount) {
        this.balance += amount;
        return `입금 완료: ${amount}원`;
    }
}

// 보호 프록시 클래스
class ProtectedBankAccount {
    constructor(balance, owner) {
        this.bankAccount = new BankAccount(balance);
        this.owner = owner;
    }

    getBalance(user) {
        if (user === this.owner) {
            return this.bankAccount.getBalance();
        }
        console.log("잔액 조회 권한이 없습니다.");
        return null;
    }

    withdraw(user, amount) {
        if (user !== this.owner) {
            console.log("출금 권한이 없습니다.");
            return null;
        }
        
        return this.bankAccount.withdraw(amount);
    }

    deposit(user, amount) {
        if (user !== this.owner) {
            console.log("입금 권한이 없습니다.");
            return null;
        }
        
        return this.bankAccount.deposit(amount);
    }

    getOwner() {
        return this.owner;
    }
}

// 사용 예시
const account = new ProtectedBankAccount(10000, "철수");

// 계좌 소유자의 작업
console.log(account.getBalance("철수")); // 10000
console.log(account.withdraw("철수", 5000)); // 출금 완료: 5000원
console.log(account.deposit("철수", 2000)); // 입금 완료: 2000원

// 권한이 없는 사용자의 작업 시도
console.log(account.getBalance("영희")); // null (권한 없음)
console.log(account.withdraw("영희", 1000)); // null (권한 없음)
console.log(account.deposit("영희", 1000)); // null (권한 없음)
```

## JavaScript의 내장 Proxy 객체 활용

### 1. ES6 Proxy 객체를 이용한 프록시 패턴 구현

JavaScript의 내장 Proxy 객체를 사용하면 더욱 유연하고 강력한 프록시 패턴을 구현할 수 있습니다. 이는 객체의 기본 동작을 가로채서 커스터마이징할 수 있게 해줍니다.

```javascript
// 기본 사용자 객체
const user = {
    name: "철수",
    age: 25,
    email: "chulsoo@example.com",
    password: "secret123"
};

// Proxy 객체를 이용한 프록시 생성
const userProxy = new Proxy(user, {
    get(target, property) {
        console.log(`속성 접근: ${property}`);
        
        // 민감한 정보는 마스킹하여 반환
        if (property === 'email') {
            const email = target[property];
            return email.replace(/(.{2}).*@/, '$1***@');
        }
        
        if (property === 'password') {
            return '***';
        }
        
        return target[property];
    },
    
    set(target, property, value) {
        console.log(`속성 변경: ${property} = ${value}`);
        
        // 유효성 검사
        if (property === 'age' && (value < 0 || value > 150)) {
            throw new Error("나이는 0에서 150 사이여야 합니다.");
        }
        
        if (property === 'email' && !value.includes('@')) {
            throw new Error("올바른 이메일 형식이 아닙니다.");
        }
        
        target[property] = value;
        return true;
    },
    
    deleteProperty(target, property) {
        console.log(`속성 삭제: ${property}`);
        
        // 중요한 속성은 삭제 방지
        if (property === 'name') {
            throw new Error("이름은 삭제할 수 없습니다.");
        }
        
        delete target[property];
        return true;
    },
    
    has(target, property) {
        console.log(`속성 존재 확인: ${property}`);
        return property in target;
    }
});

// 사용 예시
console.log(userProxy.name); // 속성 접근: name → 철수
console.log(userProxy.email); // 속성 접근: email → ch***@example.com
console.log(userProxy.password); // 속성 접근: password → ***

userProxy.age = 30; // 속성 변경: age = 30
console.log('name' in userProxy); // 속성 존재 확인: name → true

// 에러 발생 예시
try {
    userProxy.age = -5; // Error: 나이는 0에서 150 사이여야 합니다.
} catch (error) {
    console.log(error.message);
}
```

### 2. 성능 최적화를 위한 프록시 구현

프록시 패턴을 사용할 때 성능을 최적화하는 방법들을 살펴보겠습니다.

```javascript
class OptimizedProxy {
    constructor(realObject) {
        this.realObject = realObject;
        this.cache = new Map();
        this.methodCache = new Map();
        this.cacheExpiry = 5 * 60 * 1000; // 5분
    }

    // 메서드 호출 결과 캐싱
    callMethod(methodName, ...args) {
        const cacheKey = `${methodName}_${JSON.stringify(args)}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < this.cacheExpiry) {
            console.log(`캐시된 결과 반환: ${methodName}`);
            return cached.result;
        }
        
        const result = this.realObject[methodName](...args);
        this.cache.set(cacheKey, {
            result: result,
            timestamp: Date.now()
        });
        
        return result;
    }

    // 메서드 바인딩 최적화
    bindMethod(methodName) {
        if (!this.methodCache.has(methodName)) {
            this.methodCache.set(methodName, 
                this.realObject[methodName].bind(this.realObject)
            );
        }
        
        return this.methodCache.get(methodName);
    }

    // 캐시 관리
    clearCache() {
        this.cache.clear();
        console.log("캐시가 초기화되었습니다.");
    }

    getCacheStats() {
        return {
            cacheSize: this.cache.size,
            methodCacheSize: this.methodCache.size
        };
    }
}
```

### 3. 에러 처리 및 안전한 프록시 구현

프록시에서 발생할 수 있는 에러를 적절히 처리하는 방법을 살펴보겠습니다.

```javascript
class SafeProxy {
    constructor(realObject) {
        this.realObject = realObject;
        this.retryCount = 3;
        this.retryDelay = 1000; // 1초
    }

    async request(...args) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.retryCount; attempt++) {
            try {
                return await this.realObject.request(...args);
            } catch (error) {
                lastError = error;
                console.error(`프록시 에러 (시도 ${attempt}/${this.retryCount}):`, error.message);
                
                if (attempt < this.retryCount) {
                    console.log(`${this.retryDelay}ms 후 재시도합니다...`);
                    await this.delay(this.retryDelay);
                }
            }
        }
        
        // 모든 재시도 실패 시 대체 응답 반환
        console.error("모든 재시도가 실패했습니다. 대체 응답을 반환합니다.");
        return this.getFallbackResponse();
    }

    getFallbackResponse() {
        return {
            success: false,
            message: "서비스 일시적 장애로 인해 기본 응답을 반환합니다.",
            timestamp: new Date().toISOString()
        };
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 서킷 브레이커 패턴 적용
    setCircuitBreaker(threshold = 5, timeout = 60000) {
        this.failureCount = 0;
        this.threshold = threshold;
        this.timeout = timeout;
        this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
        this.nextAttempt = Date.now();
    }

    async requestWithCircuitBreaker(...args) {
        if (this.state === 'OPEN') {
            if (Date.now() < this.nextAttempt) {
                throw new Error('서킷 브레이커가 열려있습니다. 잠시 후 다시 시도해주세요.');
            } else {
                this.state = 'HALF_OPEN';
            }
        }

        try {
            const result = await this.realObject.request(...args);
            this.onSuccess();
            return result;
        } catch (error) {
            this.onFailure();
            throw error;
        }
    }

    onSuccess() {
        this.failureCount = 0;
        this.state = 'CLOSED';
    }

    onFailure() {
        this.failureCount++;
        if (this.failureCount >= this.threshold) {
            this.state = 'OPEN';
            this.nextAttempt = Date.now() + this.timeout;
        }
    }
}
```

## 프록시 패턴의 실제 활용 사례

### 1. 웹 개발에서의 프록시 패턴

#### API 게이트웨이
마이크로서비스 아키텍처에서 API 게이트웨이는 프록시 패턴의 대표적인 예시입니다. 클라이언트의 요청을 받아 적절한 마이크로서비스로 라우팅하고, 인증, 로깅, 캐싱 등의 기능을 제공합니다.

#### 웹 프록시 서버
클라이언트와 서버 사이에서 중간 역할을 수행하는 웹 프록시는 요청을 가로채서 캐싱, 필터링, 로깅 등의 기능을 제공합니다.

### 2. 데이터베이스 및 캐싱 시스템

#### 데이터베이스 연결 풀
데이터베이스 연결을 관리하는 연결 풀은 프록시 패턴을 사용하여 연결의 생성, 재사용, 해제를 효율적으로 관리합니다.

#### 캐싱 프록시
Redis, Memcached 등의 캐싱 시스템은 프록시 패턴을 사용하여 자주 접근되는 데이터를 메모리에 저장하여 성능을 향상시킵니다.

### 3. 보안 및 인증 시스템

#### 인증 프록시
사용자의 인증 정보를 확인하고 권한에 따라 접근을 제어하는 인증 프록시는 보안이 중요한 시스템에서 필수적입니다.

#### 방화벽 프록시
네트워크 트래픽을 모니터링하고 필터링하는 방화벽 프록시는 보안을 강화하는 데 사용됩니다.

## 다른 디자인 패턴과의 관계

### Decorator 패턴과의 차이점
- **프록시 패턴**: 객체에 대한 접근을 제어하고 대리 역할을 수행
- **Decorator 패턴**: 객체에 동적으로 새로운 기능을 추가

### Adapter 패턴과의 차이점
- **프록시 패턴**: 동일한 인터페이스를 제공하면서 접근을 제어
- **Adapter 패턴**: 호환되지 않는 인터페이스를 연결

### Facade 패턴과의 차이점
- **프록시 패턴**: 단일 객체에 대한 접근을 제어
- **Facade 패턴**: 복잡한 서브시스템에 대한 단순한 인터페이스 제공

## 프록시 패턴 사용 시 고려사항

### 언제 사용해야 하는가?
1. **접근 제어가 필요한 경우**: 객체에 대한 접근을 제한하거나 권한을 확인해야 할 때
2. **성능 최적화가 필요한 경우**: 캐싱이나 지연 로딩을 통해 성능을 향상시켜야 할 때
3. **로깅이나 모니터링이 필요한 경우**: 객체 사용에 대한 추적이나 로깅이 필요할 때
4. **원격 접근이 필요한 경우**: 네트워크를 통해 원격 객체에 접근해야 할 때

### 주의사항
1. **과도한 사용 금지**: 모든 객체에 프록시를 적용하면 시스템이 복잡해질 수 있습니다.
2. **성능 고려**: 프록시를 통한 간접 호출로 인한 성능 오버헤드를 고려해야 합니다.
3. **디버깅 복잡성**: 프록시를 통한 간접 호출로 인해 디버깅이 어려워질 수 있습니다.

## 결론

프록시 패턴은 객체에 대한 접근을 제어하고 추가 기능을 제공하는 강력한 구조적 디자인 패턴입니다. 보안 강화, 성능 최적화, 로깅, 모니터링 등 다양한 목적으로 활용할 수 있으며, JavaScript의 내장 Proxy 객체를 활용하면 더욱 유연하고 강력한 구현이 가능합니다.

프록시 패턴을 적절히 활용하면 시스템의 보안성과 성능을 향상시킬 수 있지만, 과도한 사용은 복잡성을 증가시킬 수 있으므로 신중한 설계가 필요합니다. 실제 프로젝트에서는 요구사항을 정확히 분석하여 프록시 패턴이 적합한지 판단한 후 적용하는 것이 중요합니다.

## 참조

1. Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley Professional.

2. Freeman, E., & Robson, E. (2004). *Head First Design Patterns*. O'Reilly Media.

3. Nystrom, R. (2014). *Game Programming Patterns*. Genever Benning.

4. Mozilla Developer Network. (2023). *Proxy - JavaScript*. Retrieved from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Proxy

5. Oracle Corporation. (2023). *Java Platform, Standard Edition 8 API Specification - java.lang.reflect.Proxy*. Retrieved from https://docs.oracle.com/javase/8/docs/api/java/lang/reflect/Proxy.html

6. Microsoft Corporation. (2023). *Proxy Pattern - .NET Design Patterns*. Retrieved from https://docs.microsoft.com/en-us/dotnet/standard/microservices-architecture/microservice-ddd-cqrs-patterns/domain-events-design-implementation

7. Gang of Four. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software - Proxy Pattern*. Addison-Wesley Professional.

8. Refactoring.Guru. (2023). *Proxy Pattern*. Retrieved from https://refactoring.guru/design-patterns/proxy

9. SourceMaking. (2023). *Proxy Design Pattern*. Retrieved from https://sourcemaking.com/design_patterns/proxy

10. TutorialsPoint. (2023). *Design Patterns - Proxy Pattern*. Retrieved from https://www.tutorialspoint.com/design_pattern/proxy_pattern.htm

