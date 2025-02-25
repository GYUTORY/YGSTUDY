# Node.js 프록시 패턴 (Proxy Pattern) 🛡️

## 1. 프록시 패턴이란?
**프록시 패턴(Proxy Pattern)**은 **어떤 객체에 대한 접근을 제어하는 중간 객체(프록시)를 두는 디자인 패턴**입니다.  
즉, **클라이언트와 실제 객체 사이에 프록시를 두어 직접 접근하지 않고 우회적으로 제어**할 수 있습니다.

### 👉🏻 프록시 패턴을 사용하는 이유
- **보안 강화**: 특정 데이터에 대한 접근을 제한
- **캐싱(Cache)**: 동일한 요청이 반복될 경우, 성능을 향상시키기 위해 이전 데이터를 저장
- **로깅(Logging)**: 객체의 사용을 추적하여 로깅 가능
- **원격 접근(Remote Access)**: 네트워크를 통해 원격 객체를 다룰 때 유용

---

## 2. 프록시 패턴의 기본 구조 ✨

프록시 패턴에서는 **3가지 주요 구성 요소**가 있습니다.

1. **RealSubject (실제 객체)** → 원래 실행하고자 하는 객체
2. **Proxy (프록시 객체)** → 실제 객체를 감싸서 중간에서 제어하는 객체
3. **Client (클라이언트)** → 프록시 객체를 통해 실제 객체에 접근하는 사용자

### 📌 기본 프록시 패턴 예제
```javascript
// 실제 객체 (RealSubject)
class RealService {
    request() {
        return "🌍 실제 서비스에서 데이터 가져오기";
    }
}

// 프록시 객체 (Proxy)
class ProxyService {
    constructor() {
        this.realService = new RealService();
    }

    request() {
        console.log("🔍 프록시: 요청 전에 추가 작업 수행 중...");
        return this.realService.request();
    }
}

// 클라이언트 코드
const proxy = new ProxyService();
console.log(proxy.request()); // 🔍 프록시: 요청 전에 추가 작업 수행 중... 🌍 실제 서비스에서 데이터 가져오기
```

> - **프록시 객체**가 `RealService`를 감싸고 있어, 요청을 직접 전달하기 전에 **추가 작업(로깅, 검증 등)**을 수행할 수 있음
> - 클라이언트는 `RealService`가 아니라 `ProxyService`를 사용하여 **보안 및 성능 최적화 가능**

---

## 3. 프록시 패턴을 활용한 캐싱 시스템 구현 🚀

프록시 패턴은 **반복적인 API 호출을 줄이기 위한 캐싱 시스템**에도 유용하게 사용할 수 있습니다.

### 📌 API 요청을 캐싱하는 프록시 패턴 예제

```javascript
// 실제 API 서비스 (RealSubject)
class APIService {
    fetchData(query) {
        console.log(`🌐 API 요청: ${query} 검색`);
        return `📄 ${query} 검색 결과`;
    }
}

// 프록시 객체 (캐싱 기능 추가)
class APIProxy {
    constructor() {
        this.apiService = new APIService();
        this.cache = {}; // 캐시 저장소
    }

    fetchData(query) {
        if (this.cache[query]) {
            console.log("✅ 캐시된 데이터 반환");
            return this.cache[query];
        }

        console.log("🔍 새로운 요청 처리...");
        const result = this.apiService.fetchData(query);
        this.cache[query] = result; // 결과를 캐시에 저장
        return result;
    }
}

// 클라이언트 코드
const apiProxy = new APIProxy();

console.log(apiProxy.fetchData("Node.js")); // 🌐 API 요청 → 결과 저장
console.log(apiProxy.fetchData("Node.js")); // ✅ 캐시된 데이터 반환
console.log(apiProxy.fetchData("JavaScript")); // 🌐 새로운 API 요청 처리
console.log(apiProxy.fetchData("JavaScript")); // ✅ 캐시된 데이터 반환
```

> **설명**
> - 프록시 객체(`APIProxy`)가 API 요청을 감싸고 있으며, **반복적인 요청을 캐싱하여 성능을 최적화**
> - 한 번 요청된 데이터는 `cache`에 저장되고, 동일한 요청이 들어오면 **API를 호출하지 않고 캐싱된 데이터를 반환**
> - 네트워크 요청을 줄여 **성능 향상과 비용 절감** 가능

---

## 4. 접근 제한을 위한 프록시 패턴 🔒

프록시 패턴은 **보안 강화를 위해 특정 객체에 대한 접근을 제한할 때** 사용할 수도 있습니다.

### 📌 관리자 권한이 있는 사용자만 데이터를 수정할 수 있도록 제한하는 프록시

```javascript
// 실제 서비스 (데이터 수정 기능 포함)
class DataService {
    modifyData(user, data) {
        console.log(`📝 ${user}가 데이터를 수정함: ${data}`);
    }
}

// 프록시 객체 (관리자만 수정 가능하도록 제한)
class AccessControlProxy {
    constructor() {
        this.dataService = new DataService();
        this.adminUsers = ["admin"]; // 관리자 계정 목록
    }

    modifyData(user, data) {
        if (!this.adminUsers.includes(user)) {
            console.log("🚫 접근 거부: 관리자만 수정할 수 있습니다.");
            return;
        }
        this.dataService.modifyData(user, data);
    }
}

// 클라이언트 코드
const proxy = new AccessControlProxy();

proxy.modifyData("guest", "비밀번호 변경"); // 🚫 접근 거부
proxy.modifyData("admin", "비밀번호 변경"); // 📝 admin이 데이터를 수정함
```

> **설명**
> - `AccessControlProxy`는 **관리자 계정인지 확인한 후, 권한이 있는 경우에만 데이터 수정 실행**
> - `guest` 계정으로 접근하면 **거부 메시지가 출력**, `admin` 계정만 데이터 수정 가능

---

## 5. JavaScript `Proxy` 객체 활용하기 ✨

JavaScript에는 **프록시 패턴을 쉽게 구현할 수 있도록 돕는 `Proxy` 내장 객체**가 존재합니다.

### 📌 `Proxy` 객체를 활용한 자동 로깅 기능 추가
```javascript
// 기본 객체
const user = {
    name: "철수",
    age: 25
};

// 프록시 생성
const userProxy = new Proxy(user, {
    get(target, property) {
        console.log(`🔍 속성 접근: ${property}`);
        return target[property];
    },
    set(target, property, value) {
        console.log(`✏️ 속성 변경: ${property} = ${value}`);
        target[property] = value;
    }
});

// 속성 읽기
console.log(userProxy.name); // 🔍 속성 접근: name → 철수

// 속성 변경
userProxy.age = 30; // ✏️ 속성 변경: age = 30
console.log(userProxy.age); // 🔍 속성 접근: age → 30
```

> **설명**
> - `Proxy` 객체를 사용하면 **객체의 속성 접근(`get`)과 수정(`set`) 시 자동으로 로깅 가능**
> - 객체의 사용을 추적하고, **보안 강화 및 디버깅을 쉽게 할 수 있음**

