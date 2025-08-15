---
title: Proxy Pattern (프록시 패턴) 개념과 예제
tags: [design-pattern, proxy-pattern, structural-pattern, javascript, architecture]
updated: 2024-12-19
---

# Proxy Pattern (프록시 패턴) 개념과 예제

## 배경

### 프록시 패턴의 필요성
프록시 패턴은 어떤 객체에 대한 접근을 제어하는 중간 객체(프록시)를 두는 디자인 패턴입니다. 클라이언트와 실제 객체 사이에 프록시를 두어 직접 접근하지 않고 우회적으로 제어할 수 있습니다. 이를 통해 보안 강화, 캐싱, 로깅, 원격 접근 등의 기능을 추가할 수 있습니다.

### 기본 개념
- **RealSubject (실제 객체)**: 원래 실행하고자 하는 객체
- **Proxy (프록시 객체)**: 실제 객체를 감싸서 중간에서 제어하는 객체
- **Client (클라이언트)**: 프록시 객체를 통해 실제 객체에 접근하는 사용자
- **접근 제어**: 객체에 대한 접근을 제한하거나 추가 기능 제공

## 핵심

### 1. 프록시 패턴의 구조

#### 기본 구성 요소
1. **Subject (주체)**: RealSubject와 Proxy가 공통으로 구현하는 인터페이스
2. **RealSubject (실제 주체)**: 실제 비즈니스 로직을 수행하는 객체
3. **Proxy (프록시)**: RealSubject에 대한 접근을 제어하는 객체
4. **Client (클라이언트)**: Proxy를 통해 RealSubject에 접근하는 객체

#### 패턴의 장점
- **접근 제어**: 객체에 대한 접근을 제한하거나 추가 기능 제공
- **보안 강화**: 권한 검증, 인증 등의 보안 기능 추가
- **성능 최적화**: 캐싱, 지연 로딩 등을 통한 성능 향상
- **로깅 및 모니터링**: 객체 사용에 대한 추적 및 로깅

#### 패턴의 단점
- **복잡성 증가**: 추가적인 추상화 계층으로 인한 복잡성
- **성능 오버헤드**: 프록시를 통한 간접 호출로 인한 성능 저하
- **디버깅 어려움**: 프록시를 통한 간접 호출로 인한 디버깅 복잡성

### 2. 기본 프록시 패턴 구현

```javascript
// Subject 인터페이스
class Subject {
    request() {
        throw new Error("request() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// RealSubject 클래스
class RealSubject extends Subject {
    request() {
        return "실제 서비스에서 데이터를 가져옵니다.";
    }
}

// Proxy 클래스
class Proxy extends Subject {
    constructor() {
        super();
        this.realSubject = new RealSubject();
    }

    request() {
        // 프록시에서 추가 작업 수행
        console.log("프록시: 요청 전에 추가 작업 수행 중...");
        
        // 실제 객체에 요청 전달
        const result = this.realSubject.request();
        
        console.log("프록시: 요청 후 추가 작업 수행 중...");
        return result;
    }
}

// 클라이언트 코드
const proxy = new Proxy();
console.log(proxy.request());
```

## 예시

### 1. 실제 사용 사례

#### 접근 제어 프록시
```javascript
// 실제 데이터 서비스
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

// 접근 제어 프록시
class AccessControlProxy {
    constructor() {
        this.dataService = new DataService();
        this.adminUsers = ["admin", "manager"];
        this.readOnlyUsers = ["guest", "user"];
    }

    modifyData(user, data) {
        if (!this.adminUsers.includes(user)) {
            console.log("🚫 접근 거부: 관리자만 수정할 수 있습니다.");
            return null;
        }
        
        console.log("✅ 접근 허용: 관리자 권한 확인됨");
        return this.dataService.modifyData(user, data);
    }

    readData(user) {
        if (!this.adminUsers.includes(user) && !this.readOnlyUsers.includes(user)) {
            console.log("🚫 접근 거부: 권한이 없습니다.");
            return null;
        }
        
        return this.dataService.readData(user);
    }
}

// 사용 예시
const proxy = new AccessControlProxy();

proxy.modifyData("guest", "비밀번호 변경"); // 🚫 접근 거부
proxy.modifyData("admin", "비밀번호 변경"); // ✅ 접근 허용
proxy.readData("user"); // 데이터 읽기 허용
```

#### 캐싱 프록시
```javascript
// 실제 API 서비스
class APIService {
    fetchData(query) {
        console.log(`🌐 API 요청: ${query} 검색`);
        // 실제로는 네트워크 요청을 수행
        return `📄 ${query} 검색 결과`;
    }
}

// 캐싱 프록시
class CachingProxy {
    constructor() {
        this.apiService = new APIService();
        this.cache = new Map();
        this.cacheExpiry = 5 * 60 * 1000; // 5분
    }

    fetchData(query) {
        const cacheKey = query;
        const cached = this.cache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < this.cacheExpiry) {
            console.log("✅ 캐시된 데이터 반환");
            return cached.data;
        }

        console.log("🔍 새로운 요청 처리...");
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
}

// 사용 예시
const apiProxy = new CachingProxy();

console.log(apiProxy.fetchData("Node.js")); // 🌐 API 요청
console.log(apiProxy.fetchData("Node.js")); // ✅ 캐시된 데이터 반환
console.log(apiProxy.fetchData("JavaScript")); // 🌐 새로운 API 요청
```

### 2. 고급 패턴

#### 가상 프록시 (지연 로딩)
```javascript
// 무거운 객체
class HeavyObject {
    constructor() {
        console.log("무거운 객체가 생성되었습니다.");
        // 실제로는 많은 리소스를 사용하는 초기화 작업
    }

    doSomething() {
        return "무거운 작업 수행";
    }
}

// 가상 프록시
class VirtualProxy {
    constructor() {
        this.realObject = null;
    }

    doSomething() {
        if (!this.realObject) {
            console.log("가상 프록시: 실제 객체 생성 중...");
            this.realObject = new HeavyObject();
        }
        
        return this.realObject.doSomething();
    }
}

// 사용 예시
const proxy = new VirtualProxy();
// 이 시점에서는 실제 객체가 생성되지 않음

console.log(proxy.doSomething()); // 실제 객체 생성 후 작업 수행
```

#### 보호 프록시
```javascript
// 실제 객체
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
}

// 보호 프록시
class ProtectedBankAccount {
    constructor(balance, owner) {
        this.bankAccount = new BankAccount(balance);
        this.owner = owner;
    }

    getBalance(user) {
        if (user === this.owner) {
            return this.bankAccount.getBalance();
        }
        console.log("🚫 잔액 조회 권한이 없습니다.");
        return null;
    }

    withdraw(user, amount) {
        if (user !== this.owner) {
            console.log("🚫 출금 권한이 없습니다.");
            return null;
        }
        
        return this.bankAccount.withdraw(amount);
    }
}

// 사용 예시
const account = new ProtectedBankAccount(10000, "철수");

console.log(account.getBalance("철수")); // 10000
console.log(account.getBalance("영희")); // 🚫 잔액 조회 권한이 없습니다.
console.log(account.withdraw("철수", 5000)); // 출금 완료: 5000원
console.log(account.withdraw("영희", 1000)); // 🚫 출금 권한이 없습니다.
```

## 운영 팁

### 1. JavaScript Proxy 객체 활용
```javascript
// 기본 객체
const user = {
    name: "철수",
    age: 25,
    email: "chulsoo@example.com"
};

// 프록시 생성
const userProxy = new Proxy(user, {
    get(target, property) {
        console.log(`🔍 속성 접근: ${property}`);
        
        // 민감한 정보는 마스킹
        if (property === 'email') {
            const email = target[property];
            return email.replace(/(.{2}).*@/, '$1***@');
        }
        
        return target[property];
    },
    
    set(target, property, value) {
        console.log(`✏️ 속성 변경: ${property} = ${value}`);
        
        // 유효성 검사
        if (property === 'age' && (value < 0 || value > 150)) {
            throw new Error("나이는 0에서 150 사이여야 합니다.");
        }
        
        target[property] = value;
        return true;
    },
    
    deleteProperty(target, property) {
        console.log(`🗑️ 속성 삭제: ${property}`);
        delete target[property];
        return true;
    }
});

// 사용 예시
console.log(userProxy.name); // 🔍 속성 접근: name → 철수
console.log(userProxy.email); // 🔍 속성 접근: email → ch***@example.com
userProxy.age = 30; // ✏️ 속성 변경: age = 30
```

### 2. 성능 최적화
```javascript
class OptimizedProxy {
    constructor() {
        this.cache = new Map();
        this.methodCache = new Map();
    }

    // 메서드 호출 결과 캐싱
    callMethod(methodName, ...args) {
        const cacheKey = `${methodName}_${JSON.stringify(args)}`;
        
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        const result = this.realObject[methodName](...args);
        this.cache.set(cacheKey, result);
        
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
}
```

### 3. 에러 처리
```javascript
class SafeProxy {
    constructor(realObject) {
        this.realObject = realObject;
    }

    request(...args) {
        try {
            return this.realObject.request(...args);
        } catch (error) {
            console.error("프록시 에러 처리:", error.message);
            
            // 기본값 반환 또는 대체 로직 수행
            return this.getFallbackResponse();
        }
    }

    getFallbackResponse() {
        return "서비스 일시적 장애로 인해 기본 응답을 반환합니다.";
    }
}
```

## 참고

### 다른 패턴과의 관계
- **Decorator**: 객체에 동적으로 기능을 추가
- **Adapter**: 호환되지 않는 인터페이스를 연결
- **Facade**: 복잡한 서브시스템에 대한 단순한 인터페이스 제공

### 실제 사용 사례
1. **웹 프록시**: 클라이언트와 서버 간의 중간 역할
2. **데이터베이스 연결 풀**: 데이터베이스 연결 관리
3. **API 게이트웨이**: 마이크로서비스 간 통신 제어
4. **캐싱 시스템**: 반복 요청에 대한 응답 캐싱
5. **보안 프록시**: 인증 및 권한 검증

### 결론
프록시 패턴은 객체에 대한 접근을 제어하고 추가 기능을 제공하는 강력한 디자인 패턴입니다. 보안 강화, 성능 최적화, 로깅 등 다양한 목적으로 활용할 수 있으며, JavaScript의 내장 Proxy 객체를 활용하면 더욱 쉽게 구현할 수 있습니다. 다만 과도한 사용은 복잡성을 증가시킬 수 있으므로 적절한 상황에서 사용하는 것이 중요합니다.

