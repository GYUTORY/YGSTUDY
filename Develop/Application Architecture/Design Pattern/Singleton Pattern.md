# 🚀 Singleton Pattern (싱글톤 패턴)

## 📖 개요

싱글톤 패턴은 **클래스의 인스턴스가 프로그램 전체에서 단 하나만 존재하도록 보장하는 디자인 패턴**입니다.

### 🤔 왜 싱글톤 패턴이 필요할까?

일반적으로 클래스를 사용할 때는 이렇게 됩니다:

```js
class Database {
    constructor() {
        this.connection = "데이터베이스 연결";
    }
}

// 매번 새로운 인스턴스가 생성됨
const db1 = new Database();
const db2 = new Database();
const db3 = new Database();

console.log(db1 === db2); // false (서로 다른 객체)
console.log(db2 === db3); // false (서로 다른 객체)
```

하지만 데이터베이스 연결처럼 **하나만 있어야 하는 것**들이 있습니다. 이런 경우 싱글톤 패턴을 사용합니다.

---

## 🎯 싱글톤 패턴의 핵심 개념

### 📝 주요 특징

1. **단일 인스턴스**: 클래스의 인스턴스가 오직 하나만 생성됨
2. **전역 접근**: 프로그램 어디서든 같은 인스턴스에 접근 가능
3. **자동 생성**: 첫 번째 요청 시에만 인스턴스가 생성됨

### 🔍 언제 사용하나요?

- **데이터베이스 연결 관리**: 연결은 하나만 유지하는 것이 효율적
- **로그 시스템**: 모든 로그를 하나의 객체에서 관리
- **설정 관리**: 애플리케이션 설정을 전역적으로 관리
- **캐시 시스템**: 여러 곳에서 같은 캐시를 공유

---

## 💻 JavaScript에서 싱글톤 패턴 구현하기

### 방법 1: 클래스 기반 구현

```js
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

### 방법 2: 모듈 패턴 (Node.js)

Node.js에서는 모듈 시스템의 특성을 활용할 수 있습니다.

**singleton.js**
```js
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

**app.js**
```js
const db1 = require('./singleton');
const db2 = require('./singleton');

console.log(db1 === db2); // true (같은 인스턴스)

db1.connect(); // "데이터베이스에 연결 중..."
db2.connect(); // 아무것도 출력되지 않음 (이미 연결됨)
```

### 방법 3: 클로저를 이용한 구현

```js
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

---

## 🔧 실제 사용 예시

### 로그 관리 시스템

```js
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

### 설정 관리 시스템

```js
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

---

## ⚖️ 장단점 분석

### ✅ 장점

- **메모리 효율성**: 불필요한 객체 생성을 방지
- **데이터 일관성**: 하나의 인스턴스로 전역 상태 관리
- **접근 용이성**: 어디서든 같은 인스턴스에 접근 가능

### ❌ 단점

- **전역 상태**: 너무 많은 싱글톤 사용 시 코드 복잡성 증가
- **테스트 어려움**: 상태가 유지되어 테스트 시 격리가 어려움
- **의존성 숨김**: 클래스가 싱글톤에 의존하는지 명확하지 않을 수 있음

---

## 🎯 사용 시 주의사항

1. **정말 필요한 경우에만 사용**: 단순히 편리하다고 남용하지 말 것
2. **상태 관리 주의**: 전역 상태이므로 변경 시 영향 범위 고려
3. **테스트 환경 고려**: 테스트 시 인스턴스 초기화 방법 준비

---

## 📚 정리

싱글톤 패턴은 **전역적으로 하나의 인스턴스만 필요한 경우**에 유용한 패턴입니다. 

데이터베이스 연결, 로그 시스템, 설정 관리 등에서 자주 사용되지만, 과도한 사용은 코드의 유연성을 떨어뜨릴 수 있으므로 신중하게 사용해야 합니다.

JavaScript에서는 클래스, 모듈 패턴, 클로저 등 다양한 방법으로 구현할 수 있으며, 각각의 상황에 맞는 적절한 방법을 선택하는 것이 중요합니다.

