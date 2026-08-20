---
title: Singleton Pattern (싱글톤 패턴)
tags: [design-patterns, javascript, architecture]
updated: 2025-11-30
---

# Singleton Pattern (싱글톤 패턴)
## 배경

### 싱글톤 패턴의 정의와 목적
싱글톤 패턴(Singleton Pattern)은 생성 패턴(Creational Pattern)의 하나다. 특정 클래스의 인스턴스가 애플리케이션 전체에 오직 하나만 존재하도록 보장한다.

어디서든 접근할 수 있는 단일 인스턴스를 내준다. 대신 그 인스턴스를 언제 어떻게 만들지는 패턴 쪽이 쥐고 있다.

### 싱글톤 패턴이 필요한 상황
1. **리소스 관리**: 데이터베이스 연결, 파일 시스템 접근, 네트워크 연결처럼 제한된 리소스를 효율적으로 관리
2. **설정 관리**: 애플리케이션의 전역 설정값을 중앙에서 관리
3. **로깅 시스템**: 모든 컴포넌트가 같은 로깅 인스턴스를 써서 로그를 일관되게 관리
4. **캐시 시스템**: 애플리케이션 전체가 공유하는 캐시 데이터 관리
5. **상태 관리**: 전역 상태를 관리하는 매니저 객체

### 싱글톤 패턴의 핵심 원리
- **단일 인스턴스 보장**: 클래스의 인스턴스가 오직 하나만 생성되도록 제어
- **전역 접근점 제공**: 애플리케이션 어느 곳에서든 같은 인스턴스에 접근 가능
- **지연 초기화**: 실제로 쓰이기 전까지 인스턴스를 만들지 않음
- **상태 일관성**: 모든 클라이언트가 같은 상태를 공유해 데이터 일관성 보장

## 핵심

### 1. 싱글톤 패턴의 구조적 특징

#### 핵심 구성 요소
1. **Private Constructor (비공개 생성자)**: 밖에서 `new` 로 직접 인스턴스를 만들지 못하게 차단
2. **Static Instance Variable (정적 인스턴스 변수)**: 유일한 인스턴스를 담아 두는 클래스 레벨 변수
3. **Static Access Method (정적 접근 메서드)**: 인스턴스 접근을 제어하는 정적 메서드
4. **Thread Safety Mechanism (스레드 안전성 메커니즘)**: 멀티스레드 환경에서의 동시성 제어

#### 싱글톤 패턴의 장점
- **메모리 효율성**: 같은 일을 하는 인스턴스가 여럿 생기지 않으니 메모리를 덜 쓴다
- **데이터 일관성**: 전역 상태를 한 인스턴스가 관리하므로 데이터가 어긋나지 않는다
- **전역 접근성**: 애플리케이션 어느 부분에서든 같은 인스턴스에 접근한다
- **리소스 제어**: DB 연결, 파일 핸들처럼 제한된 리소스를 효율적으로 관리한다
- **초기화 제어**: 인스턴스를 언제 어떤 방식으로 만들지 제어한다

#### 싱글톤 패턴의 한계점
- **전역 상태의 복잡성**: 싱글톤을 남발하면 전역 상태 관리가 복잡해진다
- **테스트의 어려움**: 상태가 계속 남아 있어서 단위 테스트에서 격리가 깨진다
- **의존성 은닉**: 클래스 간 의존 관계가 드러나지 않아 코드를 읽기 어렵다
- **동시성 복잡성**: 멀티스레드 환경에서 동시성 제어가 까다롭다
- **확장성 제약**: 상속으로 확장하기 어렵고 인터페이스 구현에도 제약이 붙는다

### 2. 기본 싱글톤 패턴 구현

#### 기본 구현 방식
가장 기본적인 구현은 생성자에서 인스턴스가 이미 있는지 확인하는 방식이다.

있으면 기존 인스턴스를 그대로 돌려준다.

```javascript
class Singleton {
    constructor() {
        // 이미 인스턴스가 존재하는지 확인
        if (Singleton.instance) {
            return Singleton.instance; // 기존 인스턴스 반환
        }
        
        // 첫 번째 생성 시에만 실행되는 초기화 로직
        this.data = "싱글톤 데이터";
        this.createdAt = new Date();
        Singleton.instance = this; // 인스턴스를 클래스 속성에 저장
    }

    getData() {
        return this.data;
    }

    setData(newData) {
        this.data = newData;
    }

    getCreatedAt() {
        return this.createdAt;
    }
}

// 사용 예시 및 검증
const instance1 = new Singleton();
const instance2 = new Singleton();

console.log(instance1 === instance2); // true - 동일한 객체 참조
console.log(instance1.getData()); // "싱글톤 데이터"
console.log(instance1.getCreatedAt() === instance2.getCreatedAt()); // true - 동일한 생성 시간

// 상태 변경 테스트
instance1.setData("새로운 데이터");
console.log(instance2.getData()); // "새로운 데이터" - 동일한 객체이므로 상태 공유
```

#### 구현 방식의 특징
- **즉시 초기화**: 클래스가 로드되는 시점에 인스턴스가 만들어진다
- **간단한 구조**: 이해하기 쉽고 구현도 간단하다
- **스레드 안전성 부족**: 멀티스레드 환경에서는 동시성 문제가 생길 수 있다

## 예시

### 1. 실제 사용 사례

#### 로그 관리 시스템
애플리케이션 전체에 일관된 로깅을 제공하는 싱글톤 로거 예시다.

```javascript
class Logger {
    constructor() {
        if (Logger.instance) {
            return Logger.instance;
        }
        
        this.logs = [];
        this.logLevel = 'INFO';
        Logger.instance = this;
    }

    log(message, level = 'INFO') {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            id: this.logs.length + 1
        };
        
        this.logs.push(logEntry);
        console.log(`[${timestamp}] [${level}] ${message}`);
    }

    getLogs() {
        return [...this.logs]; // 복사본 반환으로 외부 수정 방지
    }

    clearLogs() {
        this.logs = [];
    }

    setLogLevel(level) {
        this.logLevel = level;
    }
}

// 사용 예시
const logger1 = new Logger();
const logger2 = new Logger();

logger1.log("애플리케이션 시작", "INFO");
logger2.log("데이터베이스 연결 완료", "DEBUG");

console.log(logger1.getLogs().length); // 2 - 두 개의 로그가 모두 포함됨
console.log(logger1 === logger2); // true - 동일한 인스턴스
```

#### 설정 관리 시스템
애플리케이션의 전역 설정을 중앙에서 관리하는 싱글톤 설정 매니저다.

```javascript
class Config {
    constructor() {
        if (Config.instance) {
            return Config.instance;
        }
        
        this.settings = {
            apiUrl: "https://api.example.com",
            timeout: 5000,
            retryCount: 3,
            environment: process.env.NODE_ENV || 'development'
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
        return { ...this.settings }; // 불변성을 위한 복사본 반환
    }

    loadFromFile(configPath) {
        // 설정 파일에서 값을 로드하는 로직
        // 실제 구현에서는 fs 모듈 등을 사용
    }
}

// 사용 예시
const config1 = new Config();
const config2 = new Config();

config1.set("timeout", 10000);
console.log(config2.get("timeout")); // 10000 - 동일한 인스턴스이므로 설정 공유
console.log(config1 === config2); // true
```

#### 데이터베이스 연결 관리
데이터베이스 연결을 효율적으로 관리하는 싱글톤 연결 매니저다.

```javascript
class DatabaseConnection {
    constructor() {
        if (DatabaseConnection.instance) {
            return DatabaseConnection.instance;
        }
        
        this.connectionString = process.env.DB_URL || "mongodb://localhost:27017";
        this.isConnected = false;
        this.connectionPool = null;
        DatabaseConnection.instance = this;
    }

    async connect() {
        if (!this.isConnected) {
            try {
                console.log("데이터베이스 연결을 시도합니다...");
                // 실제 데이터베이스 연결 로직
                // this.connectionPool = await mongoose.connect(this.connectionString);
                this.isConnected = true;
                console.log("데이터베이스 연결이 완료되었습니다.");
            } catch (error) {
                console.error("데이터베이스 연결 실패:", error);
                throw error;
            }
        }
        return this.connectionString;
    }

    async disconnect() {
        if (this.isConnected) {
            try {
                // this.connectionPool.close();
                this.isConnected = false;
                console.log("데이터베이스 연결이 해제되었습니다.");
            } catch (error) {
                console.error("데이터베이스 연결 해제 실패:", error);
            }
        }
    }

    getConnectionStatus() {
        return this.isConnected;
    }

    getConnectionString() {
        return this.connectionString;
    }
}

// 사용 예시
const db1 = new DatabaseConnection();
const db2 = new DatabaseConnection();

db1.connect(); // "데이터베이스 연결을 시도합니다..."
console.log(db2.getConnectionStatus()); // true - 동일한 인스턴스이므로 연결 상태 공유
console.log(db1 === db2); // true
```

### 2. 고급 싱글톤 패턴 구현

#### 지연 초기화 (Lazy Initialization)
인스턴스가 실제로 필요해질 때까지 생성을 미루는 방식이다. 그만큼 메모리를 아낀다.

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
        this.initializedAt = new Date();
        LazySingleton.instance = this;
    }

    getData() {
        return this.data;
    }

    getInitializedAt() {
        return this.initializedAt;
    }
}

// 사용 예시
const instance1 = LazySingleton.getInstance();
const instance2 = LazySingleton.getInstance();

console.log(instance1 === instance2); // true - 동일한 인스턴스
console.log(instance1.getInitializedAt() === instance2.getInitializedAt()); // true - 동일한 초기화 시간
```

#### 모듈 패턴 (Node.js)
Node.js의 모듈 시스템을 활용한 구현이다. 모듈은 한 번 로드되면 캐시되니, 그 성질만으로 자연스럽게 싱글톤이 된다.

```javascript
// database.js
class DatabaseConnection {
    constructor() {
        this.connectionString = process.env.DB_URL || "mongodb://localhost:27017";
        this.isConnected = false;
        this.connectionPool = null;
    }

    async connect() {
        if (!this.isConnected) {
            console.log("데이터베이스 연결을 시도합니다...");
            // 실제 연결 로직
            this.isConnected = true;
            console.log("데이터베이스 연결이 완료되었습니다.");
        }
        return this.connectionString;
    }

    async disconnect() {
        if (this.isConnected) {
            this.isConnected = false;
            console.log("데이터베이스 연결이 해제되었습니다.");
        }
    }

    getConnectionStatus() {
        return this.isConnected;
    }
}

// 모듈을 내보낼 때 인스턴스를 생성하여 내보냄
module.exports = new DatabaseConnection();
```

```javascript
// app.js
const db1 = require('./database');
const db2 = require('./database');

console.log(db1 === db2); // true - Node.js 모듈 캐시로 인해 동일한 인스턴스

db1.connect(); // "데이터베이스 연결을 시도합니다..."
db2.connect(); // 아무것도 출력되지 않음 - 이미 연결된 상태
console.log(db2.getConnectionStatus()); // true
```

#### 클로저를 이용한 구현
클로저의 캡슐화를 이용해 인스턴스를 비공개로 관리하는 방식이다.

```javascript
const Singleton = (function() {
    let instance; // 비공개 변수로 인스턴스 저장

    function createInstance() {
        return {
            name: "싱글톤 객체",
            timestamp: new Date(),
            data: {},
            
            getInfo: function() {
                return `${this.name} - 생성시간: ${this.timestamp}`;
            },
            
            setData: function(key, value) {
                this.data[key] = value;
            },
            
            getData: function(key) {
                return this.data[key];
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

console.log(obj1 === obj2); // true - 동일한 인스턴스
console.log(obj1.getInfo()); // "싱글톤 객체 - 생성시간: [현재시간]"

obj1.setData('config', 'value');
console.log(obj2.getData('config')); // "value" - 동일한 객체이므로 데이터 공유
```

## 운영 환경에서의 고려사항

### 1. 멀티스레드 환경에서의 안전성
JavaScript는 단일 스레드 환경이다. 그래도 Node.js의 워커 스레드나 Web Workers를 쓰면 동시성 문제가 생길 수 있다.

```javascript
class ThreadSafeSingleton {
    static getInstance() {
        if (!ThreadSafeSingleton.instance) {
            // 동기화 메커니즘을 통한 동시성 제어
            ThreadSafeSingleton.instance = new ThreadSafeSingleton();
        }
        return ThreadSafeSingleton.instance;
    }

    constructor() {
        if (ThreadSafeSingleton.instance) {
            return ThreadSafeSingleton.instance;
        }
        
        this.data = "스레드 안전한 싱글톤";
        this.initializedAt = new Date();
        ThreadSafeSingleton.instance = this;
    }

    getData() {
        return this.data;
    }
}
```

### 2. 테스트 환경에서의 초기화
싱글톤은 상태를 계속 들고 있어서 테스트할 때 격리가 깨진다. 테스트 가능한 싱글톤을 만드는 방법이다.

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
        this.initializedAt = new Date();
        TestableSingleton.instance = this;
    }

    // 테스트를 위한 정적 메서드
    static reset() {
        TestableSingleton.instance = null;
    }

    // 테스트를 위한 인스턴스 메서드
    setData(data) {
        this.data = data;
    }

    getData() {
        return this.data;
    }
}

// 테스트에서 사용
describe('TestableSingleton', () => {
    beforeEach(() => {
        TestableSingleton.reset(); // 각 테스트 전에 인스턴스 초기화
    });

    it('should create only one instance', () => {
        const instance1 = TestableSingleton.getInstance();
        const instance2 = TestableSingleton.getInstance();
        expect(instance1).toBe(instance2);
    });
});
```

### 3. 에러 처리 및 안전성
싱글톤 인스턴스를 만들다 에러가 났을 때 제대로 처리하는 방법이다.

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
            // 에러 발생 시 기존 인스턴스가 있다면 반환
            if (SafeSingleton.instance) {
                return SafeSingleton.instance;
            }
            throw error;
        }
    }

    constructor() {
        if (SafeSingleton.instance) {
            return SafeSingleton.instance;
        }
        
        try {
            // 초기화 중 에러가 발생할 수 있는 작업
            this.initialize();
            this.initializedAt = new Date();
            SafeSingleton.instance = this;
        } catch (error) {
            console.error("싱글톤 초기화 실패:", error);
            throw error;
        }
    }

    initialize() {
        // 초기화 로직 - 외부 리소스 연결, 설정 로드 등
        this.data = "안전한 싱글톤";
        this.config = this.loadConfiguration();
    }

    loadConfiguration() {
        // 설정 로드 로직
        return { timeout: 5000, retries: 3 };
    }

    getData() {
        return this.data;
    }

    getConfig() {
        return this.config;
    }
}
```

## 참고

### 다른 패턴과의 관계
- **Factory Method**: 싱글톤 인스턴스 생성을 팩토리에서 관리
- **Abstract Factory**: 여러 관련 싱글톤들을 관리
- **Builder**: 복잡한 싱글톤 객체 생성 과정을 단계별로 분리

### 실제 사용 사례
1. **데이터베이스 연결 관리**: 연결은 하나만 유지하는 편이 효율적
2. **로그 시스템**: 모든 로그를 하나의 객체에서 관리
3. **설정 관리**: 애플리케이션 설정을 전역으로 관리
4. **캐시 시스템**: 여러 곳에서 같은 캐시를 공유
5. **게임 매니저**: 게임 상태를 전역으로 관리

### 결론
싱글톤 패턴은 인스턴스가 전역에 하나만 있으면 되는 경우에 쓸 만하다. 데이터베이스 연결, 로그 시스템, 설정 관리에서 자주 보인다. 다만 남발하면 코드의 유연성이 떨어지니 필요한 자리에만 쓴다.

JavaScript에서는 클래스, 모듈 패턴, 클로저로 구현한다. 상황에 맞는 방법을 고르는 게 중요하다. 테스트 가능성과 에러 처리, 동시성 제어까지 챙겨야 실제로 버티는 싱글톤이 나온다.

## 참조

### 관련 디자인 패턴
- **Factory Method Pattern**: 싱글톤 인스턴스 생성을 팩토리에서 관리
- **Abstract Factory Pattern**: 여러 관련 싱글톤들을 관리
- **Builder Pattern**: 복잡한 싱글톤 객체 생성 과정을 단계별로 분리
- **Dependency Injection**: 싱글톤의 의존성을 주입해 테스트를 쉽게 만듦

### 실제 사용 사례
1. **데이터베이스 연결 관리**: 연결 풀로 DB 연결을 효율적으로 관리
2. **로깅 시스템**: 애플리케이션 전체에서 일관된 로그 관리
3. **설정 관리**: 전역 설정값의 중앙 집중식 관리
4. **캐시 시스템**: 메모리 캐시의 효율적 관리
5. **게임 매니저**: 게임 상태 및 리소스의 전역 관리
6. **API 클라이언트**: HTTP 클라이언트의 재사용 및 설정 관리

### 참고 자료
- Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software
- Freeman, E., & Robson, E. (2004). Head First Design Patterns
- JavaScript Design Patterns - MDN Web Docs
- Node.js Best Practices - Singleton Pattern Implementation

