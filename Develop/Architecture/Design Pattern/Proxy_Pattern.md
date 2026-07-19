---
title: Proxy Pattern (프록시 패턴)
tags: [design-pattern, proxy-pattern, structural-pattern, javascript, architecture]
updated: 2026-07-19
---

# Proxy Pattern (프록시 패턴)

## 개요

프록시 패턴은 원본 객체 앞에 대리 객체를 두고 클라이언트 요청을 가로채는 구조적 패턴이다. 클라이언트는 프록시를 원본 객체처럼 사용하고, 프록시는 요청을 받아 인증·캐싱·지연 로딩 같은 부가 처리를 한 뒤 원본에 전달한다.

실무에서 이 패턴이 필요한 상황은 대개 세 가지다. 원본 객체에 접근 권한을 걸어야 할 때, 비용이 큰 연산 결과를 재사용해야 할 때, 초기화 비용이 큰 객체를 실제 사용 시점까지 미뤄야 할 때다.

## 구성 요소

Subject는 RealSubject와 Proxy가 공통으로 구현하는 인터페이스다. RealSubject는 실제 비즈니스 로직을 담은 원본 객체고, Proxy는 RealSubject와 동일한 인터페이스를 구현하면서 그 앞에 선다. Client는 Subject 인터페이스만 알고 Proxy를 호출한다.

```
Client → Proxy → RealSubject
```

요청 흐름은 단순하다. 클라이언트가 프록시에 요청을 보내면 프록시가 사전 처리(권한 확인, 캐시 조회 등)를 하고 원본을 호출한다. 원본의 응답을 받아 사후 처리(로깅, 캐시 저장 등)를 한 뒤 클라이언트에 반환한다.

## 접근 제어 프록시

권한 없는 사용자가 특정 메서드를 호출하지 못하게 막는 방식이다. 원본 서비스에는 권한 로직을 두지 않고 프록시에서 처리한다.

```javascript
class DataService {
    modifyData(user, data) {
        console.log(`${user}가 데이터를 수정함: ${data}`);
        return "수정 완료";
    }

    readData(user) {
        return `${user}의 데이터`;
    }
}

class AccessControlProxy {
    constructor() {
        this.dataService = new DataService();
        this.adminUsers = new Set(["admin", "manager"]);
    }

    modifyData(user, data) {
        if (!this.adminUsers.has(user)) {
            throw new Error("권한 없음: 관리자만 수정할 수 있다.");
        }
        return this.dataService.modifyData(user, data);
    }

    readData(user) {
        return this.dataService.readData(user);
    }
}

const proxy = new AccessControlProxy();
proxy.modifyData("guest", "내용 변경"); // Error: 권한 없음
proxy.modifyData("admin", "내용 변경"); // 수정 완료
```

프록시를 우회하는 경로가 생기지 않는 게 중요하다. DataService 인스턴스를 외부에 직접 노출하면 프록시가 무의미해진다. 생성자에서 외부 주입을 막거나 DataService를 private으로 두는 방식으로 막아야 한다.

## 캐싱 프록시

동일 쿼리가 반복 들어올 때 실제 서비스 호출을 줄이는 방식이다.

```javascript
class APIService {
    fetchData(query) {
        console.log(`실제 API 호출: ${query}`);
        return `${query} 결과`;
    }
}

class CachingProxy {
    constructor(ttlMs = 5 * 60 * 1000) {
        this.service = new APIService();
        this.cache = new Map();
        this.ttl = ttlMs;
    }

    fetchData(query) {
        const cached = this.cache.get(query);
        if (cached && Date.now() - cached.ts < this.ttl) {
            return cached.data;
        }

        const result = this.service.fetchData(query);
        this.cache.set(query, { data: result, ts: Date.now() });
        return result;
    }

    invalidate(query) {
        this.cache.delete(query);
    }
}
```

TTL만 두면 캐시 무효화가 어렵다. 데이터가 갱신됐을 때 관련 캐시를 즉시 날려야 하는 경우가 생기므로 `invalidate` 메서드를 함께 두는 게 맞다. 캐시 키 설계도 중요한데, 쿼리 파라미터 순서가 달라도 같은 키로 처리해야 한다면 정규화 로직이 필요하다.

메모리 누수도 신경 써야 한다. 캐시 크기를 제한하지 않으면 장기 운영 시 힙이 계속 늘어난다. LRU(Least Recently Used) 방식을 쓰거나 최대 항목 수를 두는 방식으로 관리한다.

## 가상 프록시 (지연 로딩)

초기화 비용이 큰 객체를 실제 메서드를 처음 호출하는 시점까지 생성하지 않는 방식이다.

```javascript
class HeavyReport {
    constructor() {
        // 수십만 건 데이터 로딩, 복잡한 집계 처리
        this.data = this._loadAllData();
    }

    _loadAllData() {
        console.log("대용량 데이터 로딩 중...");
        return { rows: [], summary: {} };
    }

    generate() {
        return this.data;
    }
}

class LazyReportProxy {
    constructor() {
        this._report = null;
    }

    generate() {
        if (!this._report) {
            this._report = new HeavyReport();
        }
        return this._report.generate();
    }
}

const report = new LazyReportProxy();
// 이 시점엔 HeavyReport가 생성되지 않는다.
console.log(report.generate()); // 첫 호출 시 생성된다.
```

이 방식이 유효한 건 객체 생성 비용이 실제로 크고 항상 사용되는 게 아닐 때다. 매번 사용하는 객체에 가상 프록시를 씌우면 `null` 체크 비용만 추가될 뿐이다.

멀티스레드 환경이라면 최초 생성 시 경쟁 조건이 생길 수 있다. Node.js 싱글 스레드 환경에서는 문제없지만, 서버 사이드 Java나 Go에서 같은 패턴을 쓴다면 double-checked locking 같은 동기화 처리가 필요하다.

## ES6 Proxy를 활용한 구현

JavaScript의 내장 `Proxy` 객체를 쓰면 클래스 기반 구현 없이 프록시 패턴을 적용할 수 있다. `get`, `set`, `deleteProperty`, `has` 같은 트랩(trap)으로 객체의 기본 동작을 가로챈다.

```javascript
const user = {
    name: "철수",
    age: 25,
    email: "chulsoo@example.com",
    password: "secret123"
};

const userProxy = new Proxy(user, {
    get(target, property) {
        if (property === "password") return "***";
        if (property === "email") {
            return target[property].replace(/(.{2}).*@/, "$1***@");
        }
        return target[property];
    },

    set(target, property, value) {
        if (property === "age" && (value < 0 || value > 150)) {
            throw new RangeError(`나이 범위 초과: ${value}`);
        }
        target[property] = value;
        return true;
    }
});

console.log(userProxy.password); // ***
console.log(userProxy.email);    // ch***@example.com
userProxy.age = -5;              // RangeError
```

ES6 `Proxy`는 클래스 기반 프록시보다 범용적이지만 디버깅이 어렵다. `console.log(userProxy)`로 출력하면 원본 객체처럼 보여서 프록시가 걸려 있다는 걸 모르고 지나칠 수 있다. `instanceof` 체크도 원본 클래스 기준으로 동작한다.

## 서킷 브레이커 결합

원격 서비스를 호출하는 프록시에서는 재시도와 서킷 브레이커를 함께 두는 경우가 많다.

```javascript
class RemoteServiceProxy {
    constructor(service) {
        this.service = service;
        this.failureCount = 0;
        this.threshold = 5;
        this.state = "CLOSED"; // CLOSED | OPEN | HALF_OPEN
        this.nextRetry = 0;
    }

    async request(args) {
        if (this.state === "OPEN") {
            if (Date.now() < this.nextRetry) {
                throw new Error("서킷 오픈: 잠시 후 재시도");
            }
            this.state = "HALF_OPEN";
        }

        try {
            const result = await this.service.request(args);
            this.failureCount = 0;
            this.state = "CLOSED";
            return result;
        } catch (err) {
            this.failureCount++;
            if (this.failureCount >= this.threshold) {
                this.state = "OPEN";
                this.nextRetry = Date.now() + 60_000;
            }
            throw err;
        }
    }
}
```

CLOSED 상태에서 실패가 threshold에 도달하면 OPEN으로 바뀌고, 이후 요청은 즉시 에러를 던진다. 일정 시간 뒤 HALF_OPEN으로 전환해 한 번 테스트하고, 성공하면 CLOSED로 돌아간다. 이 로직을 프록시에 두면 원본 서비스 코드가 깔끔하게 유지된다.

## 다른 패턴과의 차이

프록시와 Decorator는 헷갈리기 쉽다. Decorator는 기능을 추가하는 게 목적이고, 프록시는 접근을 제어하는 게 목적이다. 실무에서 둘의 경계가 모호한 경우도 있지만, 클라이언트가 원본 객체를 직접 만들 수 있다면 Decorator, 프록시만 통해서 접근해야 한다면 프록시로 보면 된다.

Adapter는 인터페이스를 변환하고, 프록시는 동일한 인터페이스를 유지한다. Facade는 여러 객체를 하나의 단순한 인터페이스로 묶고, 프록시는 단일 객체 앞에 선다.

## 주의사항

프록시 체인이 길어지면 스택 트레이스가 알아보기 어려워진다. 캐싱 프록시 → 접근 제어 프록시 → 로깅 프록시가 쌓이면 어느 계층에서 에러가 난 건지 추적하기 힘들다. 계층을 둘 이상 쌓을 때는 각 프록시에서 의미 있는 에러 메시지를 붙여야 한다.

프록시 내부에서 원본 객체를 직접 참조하는 코드가 생기면 순환 참조가 발생할 수 있다. 원본 객체가 이벤트를 발행하고 프록시가 그 이벤트를 구독하는 구조라면 특히 주의해야 한다.

모든 객체에 프록시를 씌우는 건 피해야 한다. 프록시가 없어도 되는 간단한 객체에 프록시를 두면 간접 호출 비용과 디버깅 복잡도만 늘어난다. 접근 제어, 캐싱, 지연 로딩 중 하나라도 실제 필요한 경우에만 적용하는 게 맞다.
