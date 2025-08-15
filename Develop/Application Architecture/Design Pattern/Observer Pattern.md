---
title: Observer Pattern (옵저버 패턴) 개념과 예제
tags: [design-pattern, observer-pattern, behavioral-pattern, javascript, architecture]
updated: 2024-12-19
---

# Observer Pattern (옵저버 패턴) 개념과 예제

## 배경

### 옵저버 패턴의 필요성
옵저버 패턴은 객체 간의 일대다(1:N) 관계를 형성하여, 특정 객체(Subject)의 상태 변화가 발생하면 연결된 여러 객체(Observer)들이 자동으로 변경을 감지하도록 하는 디자인 패턴입니다. 이 패턴은 느슨한 결합(Loose Coupling)을 유지하면서 객체 간의 통신을 가능하게 합니다.

### 기본 개념
- **Subject (주체)**: 상태 변화를 관찰 대상으로 하는 객체
- **Observer (관찰자)**: Subject의 상태 변화를 감지하는 객체들
- **일대다 관계**: 하나의 Subject에 여러 Observer가 연결
- **느슨한 결합**: Subject와 Observer가 서로를 직접 알 필요 없음

## 핵심

### 1. 옵저버 패턴의 구조

#### 기본 구성 요소
1. **Subject (주체)**: Observer들을 관리하고 상태 변화를 알림
2. **Observer (관찰자)**: Subject의 상태 변화를 감지하는 인터페이스
3. **Concrete Subject**: 실제 Subject 구현체
4. **Concrete Observer**: 실제 Observer 구현체

#### 패턴의 장점
- **느슨한 결합**: Subject와 Observer가 서로를 직접 알 필요 없음
- **확장성**: 새로운 Observer를 쉽게 추가 가능
- **재사용성**: Subject와 Observer를 독립적으로 재사용 가능
- **일관성**: Subject의 상태 변화가 모든 Observer에게 일관되게 전달

#### 패턴의 단점
- **예측 불가능성**: Observer의 실행 순서가 보장되지 않음
- **메모리 누수**: Observer가 제대로 제거되지 않으면 메모리 누수 발생
- **성능 저하**: Observer가 많을 경우 성능 저하 가능

### 2. 기본 옵저버 패턴 구현

```javascript
// Observer 인터페이스
class Observer {
    update(data) {
        throw new Error("update() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// Subject 클래스
class Subject {
    constructor() {
        this.observers = [];
    }

    // Observer 추가
    attach(observer) {
        if (!this.observers.includes(observer)) {
            this.observers.push(observer);
        }
    }

    // Observer 제거
    detach(observer) {
        const index = this.observers.indexOf(observer);
        if (index > -1) {
            this.observers.splice(index, 1);
        }
    }

    // 모든 Observer에게 알림
    notify(data) {
        this.observers.forEach(observer => observer.update(data));
    }
}

// 구체적인 Subject 클래스
class NewsAgency extends Subject {
    constructor() {
        super();
        this.news = "";
    }

    setNews(news) {
        this.news = news;
        this.notify(this.news);
    }
}

// 구체적인 Observer 클래스들
class NewsChannel extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(news) {
        console.log(`${this.name}: ${news}`);
    }
}

class NewsPaper extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(news) {
        console.log(`${this.name} 신문: ${news}`);
    }
}

// 사용 예시
const newsAgency = new NewsAgency();
const channel1 = new NewsChannel("KBS");
const channel2 = new NewsChannel("MBC");
const newspaper = new NewsPaper("조선일보");

newsAgency.attach(channel1);
newsAgency.attach(channel2);
newsAgency.attach(newspaper);

newsAgency.setNews("중요한 뉴스가 발생했습니다!");

// 출력:
// KBS: 중요한 뉴스가 발생했습니다!
// MBC: 중요한 뉴스가 발생했습니다!
// 조선일보 신문: 중요한 뉴스가 발생했습니다!
```

## 예시

### 1. 실제 사용 사례

#### 사용자 로그인 시스템
```javascript
const EventEmitter = require('events');

// 사용자 로그인 이벤트를 관리할 클래스
class User extends EventEmitter {
    login(username) {
        console.log(`${username}님이 로그인했습니다.`);
        
        // 로그인 이벤트 발생
        this.emit('login', username);
    }

    logout(username) {
        console.log(`${username}님이 로그아웃했습니다.`);
        
        // 로그아웃 이벤트 발생
        this.emit('logout', username);
    }
}

// 새로운 User 인스턴스 생성
const user = new User();

// 옵저버(리스너) 추가: 로그인 시 이메일 알림 발송
user.on('login', (username) => {
    console.log(`📧 ${username}님에게 로그인 알림 이메일을 보냈습니다.`);
});

// 옵저버(리스너) 추가: 로그인 시 데이터베이스 업데이트
user.on('login', (username) => {
    console.log(`💾 ${username}님의 로그인 정보를 데이터베이스에 저장했습니다.`);
});

// 옵저버(리스너) 추가: 로그아웃 시 세션 정리
user.on('logout', (username) => {
    console.log(`🧹 ${username}님의 세션을 정리했습니다.`);
});

// 사용자 로그인/로그아웃 실행
user.login("철수");
user.logout("철수");
```

#### 주식 가격 모니터링 시스템
```javascript
class StockPrice extends Subject {
    constructor(symbol) {
        super();
        this.symbol = symbol;
        this.price = 0;
    }

    setPrice(price) {
        this.price = price;
        this.notify({ symbol: this.symbol, price: this.price });
    }
}

class StockDisplay extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(data) {
        console.log(`${this.name}: ${data.symbol} 주식 가격이 ${data.price}원으로 변경되었습니다.`);
    }
}

class StockAlert extends Observer {
    constructor(threshold) {
        super();
        this.threshold = threshold;
    }

    update(data) {
        if (data.price > this.threshold) {
            console.log(`🚨 경고: ${data.symbol} 주식이 ${this.threshold}원을 초과했습니다! (현재: ${data.price}원)`);
        }
    }
}

// 사용 예시
const appleStock = new StockPrice("AAPL");
const display1 = new StockDisplay("모니터 1");
const display2 = new StockDisplay("모니터 2");
const alert = new StockAlert(150);

appleStock.attach(display1);
appleStock.attach(display2);
appleStock.attach(alert);

appleStock.setPrice(160);
```

### 2. 고급 패턴

#### 조건부 옵저버
```javascript
class ConditionalObserver extends Observer {
    constructor(condition) {
        super();
        this.condition = condition;
    }

    update(data) {
        if (this.condition(data)) {
            console.log("조건이 만족되어 알림을 받았습니다:", data);
        }
    }
}

// 사용 예시
const priceObserver = new ConditionalObserver(data => data.price > 100);
stock.attach(priceObserver);
```

#### 우선순위 옵저버
```javascript
class PriorityObserver extends Observer {
    constructor(priority) {
        super();
        this.priority = priority;
    }

    update(data) {
        console.log(`우선순위 ${this.priority}: ${data}`);
    }
}

class PrioritySubject extends Subject {
    notify(data) {
        // 우선순위에 따라 정렬
        this.observers.sort((a, b) => b.priority - a.priority);
        this.observers.forEach(observer => observer.update(data));
    }
}
```

## 운영 팁

### 1. 메모리 누수 방지
```javascript
class SafeSubject extends Subject {
    detach(observer) {
        const index = this.observers.indexOf(observer);
        if (index > -1) {
            this.observers.splice(index, 1);
            // Observer의 참조 제거
            observer = null;
        }
    }

    // 모든 Observer 제거
    clear() {
        this.observers = [];
    }
}
```

### 2. 비동기 처리
```javascript
class AsyncSubject extends Subject {
    async notify(data) {
        const promises = this.observers.map(observer => 
            Promise.resolve(observer.update(data))
        );
        await Promise.all(promises);
    }
}
```

### 3. 에러 처리
```javascript
class SafeSubject extends Subject {
    notify(data) {
        this.observers.forEach(observer => {
            try {
                observer.update(data);
            } catch (error) {
                console.error("Observer 업데이트 중 오류 발생:", error);
            }
        });
    }
}
```

### 4. 성능 최적화
```javascript
class OptimizedSubject extends Subject {
    constructor() {
        super();
        this.notificationQueue = [];
        this.isNotifying = false;
    }

    notify(data) {
        this.notificationQueue.push(data);
        
        if (!this.isNotifying) {
            this.processQueue();
        }
    }

    processQueue() {
        this.isNotifying = true;
        
        while (this.notificationQueue.length > 0) {
            const data = this.notificationQueue.shift();
            this.observers.forEach(observer => observer.update(data));
        }
        
        this.isNotifying = false;
    }
}
```

## 참고

### 다른 패턴과의 관계
- **Mediator**: 여러 객체 간의 복잡한 상호작용을 중재
- **Chain of Responsibility**: 요청을 처리할 수 있는 객체 체인 구성
- **Command**: 요청을 객체로 캡슐화하여 다양한 요청 처리

### 실제 사용 사례
1. **GUI 프레임워크**: 버튼 클릭, 텍스트 변경 등의 이벤트 처리
2. **게임 엔진**: 게임 상태 변화에 따른 UI 업데이트
3. **웹 애플리케이션**: 사용자 인터랙션에 따른 화면 업데이트
4. **데이터 바인딩**: 데이터 변화에 따른 UI 자동 업데이트
5. **로깅 시스템**: 시스템 이벤트에 따른 로그 기록

### 결론
옵저버 패턴은 객체 간의 느슨한 결합을 유지하면서 상태 변화를 효과적으로 전파할 수 있는 강력한 디자인 패턴입니다. 특히 이벤트 기반 시스템에서 매우 유용하며, Node.js의 EventEmitter와 같은 내장 기능을 통해 쉽게 구현할 수 있습니다. 다만 메모리 누수와 성능 문제를 고려하여 적절한 관리가 필요합니다.

