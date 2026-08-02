---
title: Observer Pattern (옵저버 패턴)
tags: [design-pattern, observer-pattern, behavioral-pattern, javascript, architecture]
updated: 2025-11-30
---

# Observer Pattern (옵저버 패턴)
## 옵저버 패턴이란?

옵저버 패턴은 객체지향 프로그래밍에서 가장 널리 사용되는 디자인 패턴 중 하나입니다. 이 패턴의 핵심은 **"한 객체의 상태가 변할 때 그 객체에 의존성을 가진 다른 객체들에게 자동으로 알림을 보내는 것"**입니다.

### 왜 옵저버 패턴이 필요한가?

실생활에서 생각해보면, 뉴스 구독 서비스를 떠올릴 수 있습니다. 뉴스 에이전시에서 새로운 뉴스가 나오면, 구독하고 있는 모든 뉴스 채널과 신문사가 자동으로 그 뉴스를 받아서 보도합니다. 이때 뉴스 에이전시는 각 채널이나 신문사가 누구인지 정확히 알 필요가 없고, 단순히 "구독자들에게 알림을 보낸다"는 것만 알면 됩니다.

프로그래밍에서도 마찬가지입니다. 사용자가 로그인하면 여러 시스템이 동시에 반응해야 합니다:
- 보안 시스템이 로그인 시도를 기록
- 이메일 시스템이 로그인 알림 발송
- 대시보드가 사용자 정보 업데이트
- 분석 시스템이 사용자 활동 추적

이런 상황에서 옵저버 패턴을 사용하면 각 시스템이 서로 강하게 연결되지 않으면서도 효율적으로 협력할 수 있습니다.

### 핵심 구성 요소

**Subject (주체/발행자)**
- 상태 변화를 관찰 대상으로 하는 객체
- Observer들을 관리하고 상태 변화 시 알림을 보냄
- 예: 뉴스 에이전시, 주식 가격 모니터, 사용자 세션

**Observer (관찰자/구독자)**
- Subject의 상태 변화를 감지하는 객체들
- Subject에 자신을 등록하고 알림을 받음
- 예: 뉴스 채널, 주식 디스플레이, 로그인 핸들러

**일대다 관계**
- 하나의 Subject에 여러 Observer가 연결
- Subject는 Observer의 구체적인 타입을 알 필요 없음

**느슨한 결합 (Loose Coupling)**
- Subject와 Observer가 서로를 직접 알 필요 없음
- 인터페이스를 통해서만 소통

## 옵저버 패턴의 구조와 동작 원리

### 패턴의 구조

옵저버 패턴은 4개의 핵심 구성 요소로 이루어져 있습니다:

1. **Subject (주체/발행자)**
   - Observer들을 관리하는 인터페이스
   - Observer 추가/제거 메서드 제공
   - 상태 변화 시 모든 Observer에게 알림

2. **Observer (관찰자/구독자)**
   - Subject의 상태 변화를 감지하는 인터페이스
   - update() 메서드를 통해 알림을 받음

3. **Concrete Subject (구체적 주체)**
   - Subject 인터페이스의 실제 구현체
   - 실제 상태를 가지고 있으며, 상태 변화 시 Observer들에게 알림

4. **Concrete Observer (구체적 관찰자)**
   - Observer 인터페이스의 실제 구현체
   - Subject로부터 받은 알림에 대한 구체적인 처리 로직 구현

### 패턴의 장점과 단점

**장점:**
- **느슨한 결합**: Subject와 Observer가 서로의 구체적인 구현을 알 필요 없음
- **확장성**: 새로운 Observer를 런타임에 쉽게 추가/제거 가능
- **재사용성**: Subject와 Observer를 독립적으로 재사용 가능
- **일관성**: Subject의 상태 변화가 모든 Observer에게 동일하게 전달
- **개방-폐쇄 원칙**: 새로운 Observer 추가 시 기존 코드 수정 불필요

**단점:**
- **예측 불가능성**: Observer의 실행 순서가 보장되지 않음
- **메모리 누수 위험**: Observer가 제대로 제거되지 않으면 메모리 누수 발생
- **성능 이슈**: Observer가 많을 경우 알림 전송으로 인한 성능 저하
- **디버깅 어려움**: Observer 간의 의존성이 복잡해질 수 있음

## 기본 구현 예제

### 뉴스 에이전시 시스템

가장 이해하기 쉬운 예제로 뉴스 에이전시 시스템을 구현해보겠습니다. 뉴스 에이전시에서 새로운 뉴스가 나오면 구독하고 있는 모든 뉴스 채널과 신문사가 자동으로 그 뉴스를 받아서 보도하는 시스템입니다.

```javascript
// Observer 인터페이스 - 모든 관찰자가 구현해야 하는 기본 구조
class Observer {
    update(data) {
        throw new Error("update() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// Subject 클래스 - 관찰자들을 관리하고 알림을 보내는 기본 구조
class Subject {
    constructor() {
        this.observers = []; // 관찰자 목록
    }

    // 관찰자 추가 (구독)
    attach(observer) {
        if (!this.observers.includes(observer)) {
            this.observers.push(observer);
            console.log(`새로운 구독자가 추가되었습니다. 총 구독자: ${this.observers.length}명`);
        }
    }

    // 관찰자 제거 (구독 해제)
    detach(observer) {
        const index = this.observers.indexOf(observer);
        if (index > -1) {
            this.observers.splice(index, 1);
            console.log(`구독자가 제거되었습니다. 총 구독자: ${this.observers.length}명`);
        }
    }

    // 모든 관찰자에게 알림 전송
    notify(data) {
        console.log(`\n📢 뉴스 에이전시에서 ${this.observers.length}명의 구독자에게 알림을 보냅니다...`);
        this.observers.forEach(observer => observer.update(data));
    }
}

// 구체적인 Subject - 뉴스 에이전시
class NewsAgency extends Subject {
    constructor() {
        super();
        this.news = "";
        this.newsCount = 0;
    }

    // 새로운 뉴스 발행
    setNews(news) {
        this.newsCount++;
        this.news = news;
        console.log(`\n🔥 뉴스 에이전시: ${this.newsCount}번째 뉴스 발행`);
        this.notify({
            news: this.news,
            newsId: this.newsCount,
            timestamp: new Date().toLocaleString()
        });
    }
}

// 구체적인 Observer들
class NewsChannel extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(data) {
        console.log(`📺 ${this.name}: "${data.news}" (뉴스 ID: ${data.newsId})`);
    }
}

class NewsPaper extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(data) {
        console.log(`📰 ${this.name} 신문: "${data.news}" - ${data.timestamp}`);
    }
}

class OnlineNews extends Observer {
    constructor(name) {
        super();
        this.name = name;
    }

    update(data) {
        console.log(`💻 ${this.name} 온라인: BREAKING NEWS - "${data.news}"`);
    }
}

// 사용 예시
console.log("=== 뉴스 에이전시 시스템 시작 ===");

const newsAgency = new NewsAgency();

// 구독자들 등록
const kbs = new NewsChannel("KBS");
const mbc = new NewsChannel("MBC");
const chosun = new NewsPaper("조선일보");
const naver = new OnlineNews("네이버 뉴스");

newsAgency.attach(kbs);
newsAgency.attach(mbc);
newsAgency.attach(chosun);
newsAgency.attach(naver);

// 뉴스 발행
newsAgency.setNews("정부, 새로운 경제 정책 발표 예정");
newsAgency.setNews("국제 스포츠 대회에서 한국 선수 금메달 획득");

// 구독 해제 테스트
newsAgency.detach(mbc);
newsAgency.setNews("기술 혁신으로 새로운 AI 모델 개발 성공");

console.log("\n=== 뉴스 에이전시 시스템 종료 ===");
```

**실행 결과:**
```
=== 뉴스 에이전시 시스템 시작 ===
새로운 구독자가 추가되었습니다. 총 구독자: 1명
새로운 구독자가 추가되었습니다. 총 구독자: 2명
새로운 구독자가 추가되었습니다. 총 구독자: 3명
새로운 구독자가 추가되었습니다. 총 구독자: 4명

🔥 뉴스 에이전시: 1번째 뉴스 발행

📢 뉴스 에이전시에서 4명의 구독자에게 알림을 보냅니다...
📺 KBS: "정부, 새로운 경제 정책 발표 예정" (뉴스 ID: 1)
📺 MBC: "정부, 새로운 경제 정책 발표 예정" (뉴스 ID: 1)
📰 조선일보 신문: "정부, 새로운 경제 정책 발표 예정" - 2025-09-23 오후 2:30:15
💻 네이버 뉴스 온라인: BREAKING NEWS - "정부, 새로운 경제 정책 발표 예정"
```

## 실전 활용 예제

### 1. 사용자 인증 시스템

실제 웹 애플리케이션에서 가장 많이 사용되는 사례 중 하나입니다. 사용자가 로그인하면 여러 시스템이 동시에 반응해야 하는 상황을 구현해보겠습니다.

```javascript
const EventEmitter = require('events');

// 사용자 인증을 관리하는 클래스
class UserAuth extends EventEmitter {
    constructor() {
        super();
        this.activeUsers = new Set();
    }

    login(username, password) {
        // 실제 인증 로직 (간단히 구현)
        if (this.authenticate(username, password)) {
            this.activeUsers.add(username);
            console.log(`✅ ${username}님이 로그인했습니다.`);
            
            // 로그인 이벤트 발생 - 모든 구독자에게 알림
            this.emit('login', {
                username,
                timestamp: new Date(),
                sessionId: this.generateSessionId()
            });
            return true;
        }
        return false;
    }

    logout(username) {
        if (this.activeUsers.has(username)) {
            this.activeUsers.delete(username);
            console.log(`👋 ${username}님이 로그아웃했습니다.`);
            
            // 로그아웃 이벤트 발생
            this.emit('logout', {
                username,
                timestamp: new Date()
            });
        }
    }

    authenticate(username, password) {
        // 간단한 인증 로직 (실제로는 해시 비교 등)
        return password === 'password123';
    }

    generateSessionId() {
        return Math.random().toString(36).substr(2, 9);
    }
}

// 인증 시스템 초기화
const authSystem = new UserAuth();

// 보안 시스템 - 로그인 시도 기록
authSystem.on('login', (data) => {
    console.log(`🔒 보안 시스템: ${data.username}의 로그인 시도를 기록했습니다. (세션: ${data.sessionId})`);
});

// 이메일 시스템 - 로그인 알림 발송
authSystem.on('login', (data) => {
    console.log(`📧 이메일 시스템: ${data.username}님에게 로그인 알림 이메일을 발송했습니다.`);
});

// 분석 시스템 - 사용자 활동 추적
authSystem.on('login', (data) => {
    console.log(`📊 분석 시스템: ${data.username}의 로그인 활동을 추적 데이터에 추가했습니다.`);
});

// 대시보드 시스템 - 실시간 사용자 수 업데이트
authSystem.on('login', (data) => {
    console.log(`📈 대시보드: 현재 활성 사용자 수를 업데이트했습니다.`);
});

// 세션 관리 시스템 - 로그아웃 시 세션 정리
authSystem.on('logout', (data) => {
    console.log(`🧹 세션 관리: ${data.username}의 세션을 정리하고 리소스를 해제했습니다.`);
});

// 사용 예시
console.log("=== 사용자 인증 시스템 테스트 ===");
authSystem.login("김철수", "password123");
authSystem.login("이영희", "password123");
authSystem.logout("김철수");
```

### 2. 주식 거래 시스템

실시간 주식 가격 변화를 모니터링하고 다양한 조건에 따라 알림을 보내는 시스템입니다.

```javascript
class StockMarket extends Subject {
    constructor() {
        super();
        this.stocks = new Map(); // 종목별 가격 정보
    }

    // 주식 가격 업데이트
    updateStockPrice(symbol, newPrice) {
        const oldPrice = this.stocks.get(symbol) || 0;
        this.stocks.set(symbol, newPrice);
        
        const change = newPrice - oldPrice;
        const changePercent = oldPrice > 0 ? (change / oldPrice) * 100 : 0;
        
        console.log(`\n📈 ${symbol} 주가 변동: ${oldPrice}원 → ${newPrice}원 (${change > 0 ? '+' : ''}${change.toFixed(2)}원, ${changePercent.toFixed(2)}%)`);
        
        // 모든 관찰자에게 주가 변동 알림
        this.notify({
            symbol,
            price: newPrice,
            oldPrice,
            change,
            changePercent,
            timestamp: new Date()
        });
    }
}

// 주식 모니터링 디스플레이
class StockDisplay extends Observer {
    constructor(name) {
        super();
        this.name = name;
        this.watchedStocks = new Set();
    }

    watchStock(symbol) {
        this.watchedStocks.add(symbol);
    }

    update(data) {
        if (this.watchedStocks.has(data.symbol)) {
            const trend = data.change > 0 ? '📈 상승' : data.change < 0 ? '📉 하락' : '➡️ 보합';
            console.log(`🖥️  ${this.name}: ${data.symbol} ${trend} - ${data.price}원`);
        }
    }
}

// 가격 알림 시스템
class PriceAlert extends Observer {
    constructor(symbol, threshold, direction = 'above') {
        super();
        this.symbol = symbol;
        this.threshold = threshold;
        this.direction = direction; // 'above' 또는 'below'
        this.triggered = false;
    }

    update(data) {
        if (data.symbol === this.symbol && !this.triggered) {
            const shouldAlert = this.direction === 'above' 
                ? data.price >= this.threshold 
                : data.price <= this.threshold;
            
            if (shouldAlert) {
                console.log(`🚨 가격 알림: ${this.symbol}이 ${this.threshold}원을 ${this.direction === 'above' ? '상회' : '하회'}했습니다! (현재: ${data.price}원)`);
                this.triggered = true;
            }
        }
    }
}

// 포트폴리오 관리 시스템
class PortfolioManager extends Observer {
    constructor() {
        super();
        this.portfolio = new Map(); // 종목별 보유 수량
    }

    buyStock(symbol, quantity) {
        const current = this.portfolio.get(symbol) || 0;
        this.portfolio.set(symbol, current + quantity);
        console.log(`💰 포트폴리오: ${symbol} ${quantity}주 매수 완료 (총 보유: ${current + quantity}주)`);
    }

    update(data) {
        const quantity = this.portfolio.get(data.symbol);
        if (quantity && quantity > 0) {
            const totalValue = data.price * quantity;
            const changeValue = data.change * quantity;
            console.log(`💼 포트폴리오: ${data.symbol} 보유가치 ${totalValue.toLocaleString()}원 (${changeValue > 0 ? '+' : ''}${changeValue.toLocaleString()}원)`);
        }
    }
}

// 사용 예시
console.log("\n=== 주식 거래 시스템 테스트 ===");

const stockMarket = new StockMarket();

// 관찰자들 등록
const display1 = new StockDisplay("거래소 모니터 1");
const display2 = new StockDisplay("거래소 모니터 2");
const alert1 = new PriceAlert("AAPL", 150, 'above');
const alert2 = new PriceAlert("GOOGL", 2500, 'below');
const portfolio = new PortfolioManager();

stockMarket.attach(display1);
stockMarket.attach(display2);
stockMarket.attach(alert1);
stockMarket.attach(alert2);
stockMarket.attach(portfolio);

// 관심 종목 설정
display1.watchStock("AAPL");
display1.watchStock("GOOGL");
display2.watchStock("AAPL");

// 포트폴리오에 주식 추가
portfolio.buyStock("AAPL", 10);
portfolio.buyStock("GOOGL", 5);

// 주가 변동 시뮬레이션
stockMarket.updateStockPrice("AAPL", 145);
stockMarket.updateStockPrice("AAPL", 155); // 알림 발생
stockMarket.updateStockPrice("GOOGL", 2600);
stockMarket.updateStockPrice("GOOGL", 2400); // 알림 발생
```

## 고급 활용 기법

### 1. 조건부 옵저버 (Conditional Observer)

특정 조건을 만족할 때만 반응하는 옵저버를 구현할 수 있습니다. 이는 불필요한 처리나 알림을 줄여 성능을 향상시킬 수 있습니다.

```javascript
class ConditionalObserver extends Observer {
    constructor(condition, name) {
        super();
        this.condition = condition; // 조건 함수
        this.name = name;
        this.notificationCount = 0;
    }

    update(data) {
        if (this.condition(data)) {
            this.notificationCount++;
            console.log(`🔔 ${this.name}: 조건 만족! 알림 #${this.notificationCount} - ${JSON.stringify(data)}`);
        } else {
            console.log(`⏸️  ${this.name}: 조건 불만족으로 알림 무시`);
        }
    }
}

// 사용 예시
const stockMarket = new StockMarket();

// 고가 알림 (150원 이상일 때만)
const highPriceAlert = new ConditionalObserver(
    data => data.price >= 150,
    "고가 알림"
);

// 급등 알림 (5% 이상 상승할 때만)
const surgeAlert = new ConditionalObserver(
    data => data.changePercent >= 5,
    "급등 알림"
);

// 거래량 알림 (변화가 클 때만)
const volumeAlert = new ConditionalObserver(
    data => Math.abs(data.change) >= 10,
    "대량 거래 알림"
);

stockMarket.attach(highPriceAlert);
stockMarket.attach(surgeAlert);
stockMarket.attach(volumeAlert);

// 테스트
stockMarket.updateStockPrice("AAPL", 140); // 조건 불만족
stockMarket.updateStockPrice("AAPL", 160); // 고가 알림만 발생
stockMarket.updateStockPrice("AAPL", 168); // 5% 상승으로 급등 알림도 발생
```

### 2. 우선순위 옵저버 (Priority Observer)

중요도에 따라 옵저버의 실행 순서를 제어할 수 있습니다. 예를 들어, 보안 관련 알림은 일반 알림보다 우선적으로 처리되어야 합니다.

```javascript
class PriorityObserver extends Observer {
    constructor(priority, name) {
        super();
        this.priority = priority; // 숫자가 클수록 높은 우선순위
        this.name = name;
    }

    update(data) {
        console.log(`🎯 [우선순위 ${this.priority}] ${this.name}: ${JSON.stringify(data)}`);
    }
}

class PrioritySubject extends Subject {
    notify(data) {
        // 우선순위에 따라 내림차순 정렬 (높은 우선순위가 먼저 실행)
        const sortedObservers = [...this.observers].sort((a, b) => b.priority - a.priority);
        
        console.log(`\n📢 우선순위에 따른 알림 전송 시작 (총 ${sortedObservers.length}개)`);
        sortedObservers.forEach(observer => observer.update(data));
        console.log(`✅ 모든 알림 전송 완료\n`);
    }
}

// 사용 예시
const prioritySystem = new PrioritySubject();

// 다양한 우선순위의 옵저버들
const securityAlert = new PriorityObserver(100, "보안 시스템");
const criticalAlert = new PriorityObserver(80, "중요 알림");
const normalAlert = new PriorityObserver(50, "일반 알림");
const lowPriorityAlert = new PriorityObserver(10, "낮은 우선순위");

prioritySystem.attach(normalAlert);
prioritySystem.attach(securityAlert);
prioritySystem.attach(lowPriorityAlert);
prioritySystem.attach(criticalAlert);

// 알림 전송 - 우선순위 순으로 실행됨
prioritySystem.notify({ message: "시스템 점검 예정", type: "maintenance" });
```

### 3. 체이닝 옵저버 (Chaining Observer)

옵저버들이 연쇄적으로 실행되도록 하는 패턴입니다. 한 옵저버의 결과가 다음 옵저버의 입력이 되는 경우에 유용합니다.

```javascript
class ChainingObserver extends Observer {
    constructor(name, processor) {
        super();
        this.name = name;
        this.processor = processor; // 데이터를 처리하는 함수
    }

    update(data) {
        console.log(`🔗 ${this.name} 처리 시작: ${JSON.stringify(data)}`);
        
        const processedData = this.processor(data);
        console.log(`✅ ${this.name} 처리 완료: ${JSON.stringify(processedData)}`);
        
        return processedData;
    }
}

class ChainingSubject extends Subject {
    notify(data) {
        let currentData = data;
        
        console.log(`\n🔄 체이닝 처리 시작`);
        
        for (const observer of this.observers) {
            currentData = observer.update(currentData);
        }
        
        console.log(`🏁 체이닝 처리 완료\n`);
        return currentData;
    }
}

// 사용 예시
const chainingSystem = new ChainingSubject();

// 데이터 검증
const validator = new ChainingObserver("데이터 검증", (data) => {
    if (!data.value || data.value < 0) {
        throw new Error("유효하지 않은 데이터");
    }
    return { ...data, validated: true };
});

// 데이터 변환
const transformer = new ChainingObserver("데이터 변환", (data) => {
    return {
        ...data,
        value: data.value * 100,
        unit: "원"
    };
});

// 데이터 저장
const saver = new ChainingObserver("데이터 저장", (data) => {
    console.log(`💾 데이터베이스에 저장: ${data.value}${data.unit}`);
    return { ...data, saved: true };
});

chainingSystem.attach(validator);
chainingSystem.attach(transformer);
chainingSystem.attach(saver);

// 체이닝 처리 실행
chainingSystem.notify({ value: 1500, type: "price" });
```

## 실무에서 주의해야 할 점들

### 1. 메모리 누수 방지

옵저버 패턴에서 가장 흔한 문제 중 하나가 메모리 누수입니다. Observer가 제대로 제거되지 않으면 Subject가 Observer를 계속 참조하고 있어서 가비지 컬렉션이 되지 않습니다.

```javascript
class SafeSubject extends Subject {
    constructor() {
        super();
        this.observerWeakMap = new WeakMap(); // 약한 참조를 위한 WeakMap
    }

    attach(observer) {
        if (!this.observers.includes(observer)) {
            this.observers.push(observer);
            // Observer에 대한 메타데이터 저장
            this.observerWeakMap.set(observer, {
                attachedAt: new Date(),
                notificationCount: 0
            });
        }
    }

    detach(observer) {
        const index = this.observers.indexOf(observer);
        if (index > -1) {
            this.observers.splice(index, 1);
            this.observerWeakMap.delete(observer);
            console.log(`Observer가 안전하게 제거되었습니다.`);
        }
    }

    // 모든 Observer 제거
    clear() {
        this.observers.forEach(observer => {
            this.observerWeakMap.delete(observer);
        });
        this.observers = [];
        console.log("모든 Observer가 제거되었습니다.");
    }

    // 메모리 사용량 모니터링
    getMemoryInfo() {
        return {
            observerCount: this.observers.length,
            weakMapSize: this.observerWeakMap.size
        };
    }
}
```

### 2. 비동기 처리와 에러 핸들링

실제 애플리케이션에서는 Observer의 update 메서드가 비동기 작업을 수행할 수 있습니다. 이때 적절한 에러 처리와 비동기 관리가 필요합니다.

```javascript
class AsyncSubject extends Subject {
    async notify(data) {
        console.log(`\n🚀 비동기 알림 전송 시작 (${this.observers.length}개 Observer)`);
        
        const promises = this.observers.map(async (observer, index) => {
            try {
                const result = await Promise.resolve(observer.update(data));
                console.log(`✅ Observer ${index + 1} 처리 완료`);
                return { success: true, index, result };
            } catch (error) {
                console.error(`❌ Observer ${index + 1} 처리 실패:`, error.message);
                return { success: false, index, error: error.message };
            }
        });

        const results = await Promise.allSettled(promises);
        
        const successful = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
        const failed = results.length - successful;
        
        console.log(`📊 알림 전송 완료: 성공 ${successful}개, 실패 ${failed}개\n`);
        
        return results;
    }
}

// 에러가 발생할 수 있는 Observer 예제
class UnreliableObserver extends Observer {
    constructor(name, failureRate = 0.3) {
        super();
        this.name = name;
        this.failureRate = failureRate;
    }

    async update(data) {
        // 의도적으로 실패를 시뮬레이션
        if (Math.random() < this.failureRate) {
            throw new Error(`${this.name}에서 처리 중 오류 발생`);
        }
        
        // 비동기 작업 시뮬레이션
        await new Promise(resolve => setTimeout(resolve, Math.random() * 1000));
        console.log(`🔄 ${this.name}: ${JSON.stringify(data)} 처리 완료`);
    }
}
```

### 3. 성능 최적화

Observer가 많아지면 알림 전송 성능이 저하될 수 있습니다. 이를 해결하기 위한 몇 가지 기법을 살펴보겠습니다.

```javascript
class OptimizedSubject extends Subject {
    constructor() {
        super();
        this.notificationQueue = [];
        this.isProcessing = false;
        this.batchSize = 10; // 배치 처리 크기
        this.processingInterval = 100; // 처리 간격 (ms)
    }

    notify(data) {
        this.notificationQueue.push({
            data,
            timestamp: Date.now()
        });
        
        if (!this.isProcessing) {
            this.startProcessing();
        }
    }

    startProcessing() {
        this.isProcessing = true;
        this.processQueue();
    }

    async processQueue() {
        while (this.notificationQueue.length > 0) {
            const batch = this.notificationQueue.splice(0, this.batchSize);
            
            console.log(`📦 배치 처리 시작: ${batch.length}개 알림`);
            
            // 배치 내에서 병렬 처리
            const promises = batch.map(notification => 
                this.processNotification(notification)
            );
            
            await Promise.allSettled(promises);
            
            // 다음 배치 처리 전 잠시 대기
            if (this.notificationQueue.length > 0) {
                await new Promise(resolve => setTimeout(resolve, this.processingInterval));
            }
        }
        
        this.isProcessing = false;
        console.log(`✅ 모든 알림 처리 완료\n`);
    }

    async processNotification(notification) {
        const promises = this.observers.map(observer => 
            Promise.resolve(observer.update(notification.data))
        );
        
        await Promise.allSettled(promises);
    }

    // 성능 통계
    getPerformanceStats() {
        return {
            queueLength: this.notificationQueue.length,
            isProcessing: this.isProcessing,
            observerCount: this.observers.length
        };
    }
}
```

### 4. 디버깅과 모니터링

복잡한 Observer 시스템에서는 디버깅이 어려울 수 있습니다. 적절한 로깅과 모니터링 시스템을 구축하는 것이 중요합니다.

```javascript
class MonitoredSubject extends Subject {
    constructor() {
        super();
        this.notificationHistory = [];
        this.performanceMetrics = {
            totalNotifications: 0,
            averageProcessingTime: 0,
            errorCount: 0
        };
    }

    notify(data) {
        const startTime = Date.now();
        this.performanceMetrics.totalNotifications++;
        
        console.log(`\n🔍 알림 전송 시작: ${JSON.stringify(data)}`);
        
        this.observers.forEach((observer, index) => {
            const observerStartTime = Date.now();
            
            try {
                observer.update(data);
                const processingTime = Date.now() - observerStartTime;
                
                console.log(`✅ Observer ${index + 1} 처리 완료 (${processingTime}ms)`);
                
                // 성능 메트릭 업데이트
                this.updatePerformanceMetrics(processingTime);
                
            } catch (error) {
                this.performanceMetrics.errorCount++;
                console.error(`❌ Observer ${index + 1} 오류:`, error.message);
            }
        });
        
        const totalTime = Date.now() - startTime;
        
        // 알림 히스토리 저장
        this.notificationHistory.push({
            data,
            timestamp: new Date(),
            processingTime: totalTime,
            observerCount: this.observers.length
        });
        
        // 히스토리 크기 제한 (메모리 절약)
        if (this.notificationHistory.length > 100) {
            this.notificationHistory.shift();
        }
        
        console.log(`📊 총 처리 시간: ${totalTime}ms\n`);
    }

    updatePerformanceMetrics(processingTime) {
        const total = this.performanceMetrics.averageProcessingTime * (this.performanceMetrics.totalNotifications - 1);
        this.performanceMetrics.averageProcessingTime = (total + processingTime) / this.performanceMetrics.totalNotifications;
    }

    getMetrics() {
        return {
            ...this.performanceMetrics,
            recentNotifications: this.notificationHistory.slice(-5),
            observerCount: this.observers.length
        };
    }
}
```

## 다른 디자인 패턴과의 관계

### Mediator Pattern과의 차이점
- **Observer**: Subject가 직접 Observer들에게 알림을 보냄 (일대다)
- **Mediator**: Mediator가 중간에서 객체들 간의 통신을 중재 (다대다)

### Chain of Responsibility Pattern과의 차이점
- **Observer**: 모든 Observer가 동시에 알림을 받음
- **Chain of Responsibility**: 요청을 처리할 수 있는 객체가 나올 때까지 순차적으로 전달

### Command Pattern과의 조합
Observer 패턴과 Command 패턴을 함께 사용하면 더욱 유연한 시스템을 구축할 수 있습니다. Command 객체를 Observer로 만들어서 실행 취소(Undo) 기능을 구현할 수 있습니다.

## 실제 사용 사례

### 1. 웹 개발에서의 활용
- **React/Vue.js**: 상태 변화에 따른 컴포넌트 리렌더링
- **DOM 이벤트**: 클릭, 키보드 입력 등의 이벤트 처리
- **WebSocket**: 실시간 데이터 업데이트
- **Redux/Vuex**: 상태 관리 시스템

### 2. 백엔드 개발에서의 활용
- **Node.js EventEmitter**: 비동기 이벤트 처리
- **Express.js**: 미들웨어 체인
- **데이터베이스 트리거**: 데이터 변경 시 자동 실행
- **메시지 큐**: 비동기 작업 처리

### 3. 게임 개발에서의 활용
- **게임 이벤트 시스템**: 플레이어 행동에 따른 반응
- **UI 업데이트**: 게임 상태 변화에 따른 화면 갱신
- **사운드 시스템**: 이벤트에 따른 사운드 재생

### 4. 모바일 앱 개발에서의 활용
- **알림 시스템**: 푸시 알림 처리
- **데이터 동기화**: 서버와의 실시간 동기화
- **사용자 인터랙션**: 터치, 제스처 이벤트 처리

## 마무리

옵저버 패턴은 현대 소프트웨어 개발에서 가장 널리 사용되는 디자인 패턴 중 하나입니다. 이 패턴의 핵심 가치는 **느슨한 결합(Loose Coupling)**을 통해 시스템의 유연성과 확장성을 높이는 것입니다.

### 주요 내용
1. **이벤트 기반 아키텍처**의 기초가 되는 패턴
2. **실시간 시스템**에서 상태 변화를 효율적으로 전파
3. **확장성**이 뛰어나며 새로운 기능 추가가 용이
4. **테스트 용이성**이 높아 유지보수가 편리

### 주의사항
- 메모리 누수 방지를 위한 적절한 Observer 제거
- 성능 최적화를 위한 배치 처리 고려
- 에러 처리와 비동기 작업 관리
- 디버깅을 위한 적절한 로깅 시스템 구축

옵저버 패턴을 올바르게 이해하고 활용하면, 더욱 유연하고 확장 가능한 소프트웨어를 개발할 수 있습니다. 특히 JavaScript의 EventEmitter, React의 상태 관리, 그리고 다양한 프레임워크에서 이 패턴의 변형을 찾아볼 수 있으니, 실무에서 적극적으로 활용해보시기 바랍니다.

---

## 참조

- Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley.
- Freeman, E., & Robson, E. (2004). *Head First Design Patterns*. O'Reilly Media.
- Martin, R. C. (2017). *Clean Architecture: A Craftsman's Guide to Software Structure and Design*. Prentice Hall.
- Node.js Documentation. (2024). *Events*. https://nodejs.org/api/events.html
- React Documentation. (2024). *State and Lifecycle*. https://reactjs.org/docs/state-and-lifecycle.html

