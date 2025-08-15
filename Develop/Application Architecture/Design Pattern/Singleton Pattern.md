---
title: Singleton Pattern (싱글톤 패턴) 개념과 예제
tags: [design-pattern, singleton-pattern, creational-pattern, javascript, architecture]
updated: 2024-12-19
---

# Singleton Pattern (싱글톤 패턴) 개념과 예제

## 배경

### 싱글톤 패턴의 필요성
싱글톤 패턴은 클래스의 인스턴스가 프로그램 전체에서 단 하나만 존재하도록 보장하는 디자인 패턴입니다. 전역적으로 하나의 인스턴스만 필요한 경우에 사용되며, 메모리 효율성과 데이터 일관성을 제공합니다.

### 기본 개념
- **단일 인스턴스**: 클래스의 인스턴스가 오직 하나만 생성됨
- **전역 접근**: 프로그램 어디서든 같은 인스턴스에 접근 가능
- **자동 생성**: 첫 번째 요청 시에만 인스턴스가 생성됨
- **상태 공유**: 모든 클라이언트가 같은 상태를 공유

## 핵심

### 1. 싱글톤 패턴의 구조

#### 기본 구성 요소
1. **Private Constructor**: 외부에서 직접 인스턴스 생성 방지
2. **Static Instance**: 유일한 인스턴스를 저장하는 정적 변수
3. **Static Method**: 인스턴스에 접근하는 정적 메서드
4. **Thread Safety**: 멀티스레드 환경에서의 안전성 보장

#### 패턴의 장점
- **메모리 효율성**: 불필요한 객체 생성을 방지
- **데이터 일관성**: 하나의 인스턴스로 전역 상태 관리
- **접근 용이성**: 어디서든 같은 인스턴스에 접근 가능
- **리소스 관리**: 공유 리소스의 효율적 관리

#### 패턴의 단점
- **전역 상태**: 너무 많은 싱글톤 사용 시 코드 복잡성 증가
- **테스트 어려움**: 상태가 유지되어 테스트 시 격리가 어려움
- **의존성 숨김**: 클래스가 싱글톤에 의존하는지 명확하지 않을 수 있음
- **동시성 문제**: 멀티스레드 환경에서 동시성 제어 필요

### 2. 기본 싱글톤 패턴 구현

```javascript
class Singleton {
    constructor() {
        // 이미 인스턴스가 존재하는지 확인
        if (Singleton.instance) {
            return Singleton.instance; // 기존 인스턴스 반환
        }
        
        // 첫 번째 생성 시에만 실행
        this.data = "싱글톤 데이터";
        Singleton.instance = this; // 인스턴스를 클래스 속성에 저장
    }

    getData() {
        return this.data;
    }

    setData(newData) {
        this.data = newData;
    }
}

// 테스트
const instance1 = new Singleton();
const instance2 = new Singleton();

console.log(instance1 === instance2); // true (같은 객체)
console.log(instance1.getData()); // "싱글톤 데이터"

instance1.setData("새로운 데이터");
console.log(instance2.getData()); // "새로운 데이터" (같은 객체이므로 변경됨)
```

## 예시

### 1. 실제 사용 사례

#### 로그 관리 시스템
```javascript
class Logger {
    constructor() {
        if (Logger.instance) {
            return Logger.instance;
        }
        
        this.logs = [];
        Logger.instance = this;
    }

    log(message) {
        const timestamp = new Date().toISOString();
        const logEntry = `[${timestamp}] ${message}`;
        this.logs.push(logEntry);
        console.log(logEntry);
    }

    getLogs() {
        return this.logs;
    }

    clearLogs() {
        this.logs = [];
    }
}

// 사용 예시
const logger1 = new Logger();
const logger2 = new Logger();

logger1.log("첫 번째 로그");
logger2.log("두 번째 로그");

console.log(logger1.getLogs()); // 두 개의 로그가 모두 포함됨
console.log(logger1 === logger2); // true
```

#### 설정 관리 시스템
```javascript
class Config {
    constructor() {
        if (Config.instance) {
            return Config.instance;
        }
        
        this.settings = {
            apiUrl: "https://api.example.com",
            timeout: 5000,
            retryCount: 3
        };
        
        Config.instance = this;
    }

    get(key) {
        return this.settings[key];
    }

    set(key, value) {
        this.settings[key] = value;
    }

    getAll() {
        return { ...this.settings };
    }
}

// 사용 예시
const config1 = new Config();
const config2 = new Config();

config1.set("timeout", 10000);
console.log(config2.get("timeout")); // 10000 (같은 객체이므로 변경됨)
```

#### 데이터베이스 연결 관리
```javascript
class DatabaseConnection {
    constructor() {
        if (DatabaseConnection.instance) {
            return DatabaseConnection.instance;
        }
        
        this.connectionString = "mongodb://localhost:27017";
        this.isConnected = false;
        DatabaseConnection.instance = this;
    }

    connect() {
        if (!this.isConnected) {
            console.log("데이터베이스에 연결 중...");
            this.isConnected = true;
        }
        return this.connectionString;
    }

    disconnect() {
        this.isConnected = false;
        console.log("데이터베이스 연결 해제");
    }

    isConnected() {
        return this.isConnected;
    }
}

// 사용 예시
const db1 = new DatabaseConnection();
const db2 = new DatabaseConnection();

db1.connect(); // "데이터베이스에 연결 중..."
console.log(db2.isConnected()); // true (같은 객체이므로 연결 상태 공유)
```

### 2. 고급 패턴

#### 지연 초기화 (Lazy Initialization)
```javascript
class LazySingleton {
    static getInstance() {
        if (!LazySingleton.instance) {
            LazySingleton.instance = new LazySingleton();
        }
        return LazySingleton.instance;
    }

    constructor() {
        if (LazySingleton.instance) {
            return LazySingleton.instance;
        }
        
        this.data = "지연 초기화된 싱글톤";
        LazySingleton.instance = this;
    }

    getData() {
        return this.data;
    }
}

// 사용 예시
const instance1 = LazySingleton.getInstance();
const instance2 = LazySingleton.getInstance();
console.log(instance1 === instance2); // true
```

#### 모듈 패턴 (Node.js)
```javascript
// singleton.js
class DatabaseConnection {
    constructor() {
        this.connectionString = "mongodb://localhost:27017";
        this.isConnected = false;
    }

    connect() {
        if (!this.isConnected) {
            console.log("데이터베이스에 연결 중...");
            this.isConnected = true;
        }
        return this.connectionString;
    }

    disconnect() {
        this.isConnected = false;
        console.log("데이터베이스 연결 해제");
    }
}

// 모듈을 내보낼 때 인스턴스를 생성하여 내보냄
module.exports = new DatabaseConnection();
```

```javascript
// app.js
const db1 = require('./singleton');
const db2 = require('./singleton');

console.log(db1 === db2); // true (같은 인스턴스)

db1.connect(); // "데이터베이스에 연결 중..."
db2.connect(); // 아무것도 출력되지 않음 (이미 연결됨)
```

#### 클로저를 이용한 구현
```javascript
const Singleton = (function() {
    let instance; // 비공개 변수로 인스턴스 저장

    function createInstance() {
        return {
            name: "싱글톤 객체",
            timestamp: new Date(),
            getInfo: function() {
                return `${this.name} - 생성시간: ${this.timestamp}`;
            }
        };
    }

    return {
        getInstance: function() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

// 사용 예시
const obj1 = Singleton.getInstance();
const obj2 = Singleton.getInstance();

console.log(obj1 === obj2); // true
console.log(obj1.getInfo()); // "싱글톤 객체 - 생성시간: [현재시간]"
```

## 운영 팁

### 1. 멀티스레드 환경에서의 안전성
```javascript
class ThreadSafeSingleton {
    static getInstance() {
        if (!ThreadSafeSingleton.instance) {
            // 동기화 블록 또는 락을 사용하여 동시성 제어
            ThreadSafeSingleton.instance = new ThreadSafeSingleton();
        }
        return ThreadSafeSingleton.instance;
    }

    constructor() {
        if (ThreadSafeSingleton.instance) {
            return ThreadSafeSingleton.instance;
        }
        
        this.data = "스레드 안전한 싱글톤";
        ThreadSafeSingleton.instance = this;
    }
}
```

### 2. 테스트 환경에서의 초기화
```javascript
class TestableSingleton {
    static getInstance() {
        if (!TestableSingleton.instance) {
            TestableSingleton.instance = new TestableSingleton();
        }
        return TestableSingleton.instance;
    }

    constructor() {
        if (TestableSingleton.instance) {
            return TestableSingleton.instance;
        }
        
        this.data = "테스트 가능한 싱글톤";
        TestableSingleton.instance = this;
    }

    // 테스트를 위한 정적 메서드
    static reset() {
        TestableSingleton.instance = null;
    }
}

// 테스트에서 사용
beforeEach(() => {
    TestableSingleton.reset();
});
```

### 3. 에러 처리
```javascript
class SafeSingleton {
    static getInstance() {
        try {
            if (!SafeSingleton.instance) {
                SafeSingleton.instance = new SafeSingleton();
            }
            return SafeSingleton.instance;
        } catch (error) {
            console.error("싱글톤 인스턴스 생성 실패:", error);
            throw error;
        }
    }

    constructor() {
        if (SafeSingleton.instance) {
            return SafeSingleton.instance;
        }
        
        // 초기화 중 에러가 발생할 수 있는 작업
        this.initialize();
        SafeSingleton.instance = this;
    }

    initialize() {
        // 초기화 로직
        this.data = "안전한 싱글톤";
    }
}
```

## 참고

### 다른 패턴과의 관계
- **Factory Method**: 싱글톤 인스턴스 생성을 팩토리에서 관리
- **Abstract Factory**: 여러 관련 싱글톤들을 관리
- **Builder**: 복잡한 싱글톤 객체 생성 과정을 단계별로 분리

### 실제 사용 사례
1. **데이터베이스 연결 관리**: 연결은 하나만 유지하는 것이 효율적
2. **로그 시스템**: 모든 로그를 하나의 객체에서 관리
3. **설정 관리**: 애플리케이션 설정을 전역적으로 관리
4. **캐시 시스템**: 여러 곳에서 같은 캐시를 공유
5. **게임 매니저**: 게임 상태를 전역적으로 관리

### 결론
싱글톤 패턴은 전역적으로 하나의 인스턴스만 필요한 경우에 유용한 패턴입니다. 데이터베이스 연결, 로그 시스템, 설정 관리 등에서 자주 사용되지만, 과도한 사용은 코드의 유연성을 떨어뜨릴 수 있으므로 신중하게 사용해야 합니다. JavaScript에서는 클래스, 모듈 패턴, 클로저 등 다양한 방법으로 구현할 수 있으며, 각각의 상황에 맞는 적절한 방법을 선택하는 것이 중요합니다.

