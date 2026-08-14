---
title: Factory Method Pattern (팩토리 메서드 패턴)
tags: [design-patterns, javascript, architecture, language]
updated: 2025-11-30
---

# Factory Method Pattern (팩토리 메서드 패턴)
## Factory Method 패턴이란?

Factory Method 패턴은 **객체를 생성하는 방법을 추상화**하는 디자인 패턴입니다. 쉽게 말해, "어떤 객체를 만들지"는 결정하되, "어떻게 만들지"는 서브클래스에 맡기는 방식입니다.

### 패턴의 핵심 아이디어

**"객체 생성을 캡슐화하여 클라이언트가 구체적인 클래스를 알 필요 없게 만든다"**

마치 자동차 공장에서 고객이 "빨간색 세단을 주세요"라고 요청하면, 공장에서 적절한 자동차를 만들어 주는 것과 같습니다. 고객은 자동차가 어떻게 만들어지는지 알 필요가 없고, 단지 원하는 결과물만 받으면 됩니다.

### 🤔 왜 이 패턴이 필요한가?

#### 문제 상황 1: 직접 생성의 한계
```javascript
// 문제가 있는 코드
if (userType === "premium") {
    const user = new PremiumUser(name, email);
} else if (userType === "basic") {
    const user = new BasicUser(name, email);
} else {
    const user = new GuestUser(name, email);
}
```

**문제점:**
- 새로운 사용자 타입이 추가될 때마다 코드를 수정해야 함
- 클라이언트 코드가 모든 구체 클래스를 알아야 함
- 객체 생성 로직이 여러 곳에 흩어져 있음

#### 문제 상황 2: 복잡한 생성 과정
```javascript
// 복잡한 객체 생성
const database = new DatabaseConnection({
    host: "localhost",
    port: 3306,
    username: "user",
    password: "password",
    ssl: true,
    poolSize: 10,
    timeout: 5000
});
```

**문제점:**
- 생성 과정이 복잡하고 매개변수가 많음
- 설정에 따라 다른 타입의 객체를 생성해야 함
- 에러 처리가 어려움

### Factory Method 패턴의 해결책

#### 해결책 1: 생성 책임 분리
```javascript
// 팩토리 패턴 적용
const user = UserFactory.createUser(userType, name, email);
const database = DatabaseFactory.createConnection(config);
```

**장점:**
- 클라이언트는 팩토리만 알면 됨
- 새로운 타입 추가 시 팩토리만 수정
- 생성 로직이 한 곳에 집중

#### 해결책 2: 유연한 확장
```javascript
// 새로운 타입 추가가 쉬움
class VIPUserFactory extends UserFactory {
    createUser(type, name, email) {
        return new VIPUser(name, email, "VIP");
    }
}
```

### 패턴의 핵심 원칙

#### 1. 단일 책임 원칙 (SRP)
- **객체 생성**이라는 하나의 책임만 가짐
- 다른 비즈니스 로직과 분리

#### 2. 개방-폐쇄 원칙 (OCP)
- **확장에는 열려있고, 수정에는 닫혀있음**
- 새로운 타입 추가 시 기존 코드 수정 없이 확장 가능

#### 3. 의존성 역전 원칙 (DIP)
- **구체적인 클래스가 아닌 추상화에 의존**
- 클라이언트는 인터페이스만 알면 됨

#### 4. 리스코프 치환 원칙 (LSP)
- **서브클래스는 부모 클래스를 대체할 수 있어야 함**
- 모든 팩토리는 동일한 인터페이스 제공

## 🏗 패턴 구조 이해하기

Factory Method 패턴은 **4개의 핵심 구성 요소**로 이루어져 있습니다. 각각의 역할을 쉽게 이해해보겠습니다.

### 📦 구성 요소별 역할

#### 1⃣ Product (제품) - "만들어질 것"
**역할**: 팩토리에서 만들 객체들의 **공통 규격**을 정의

**실생활 비유**: 자동차의 기본 설계도
- 모든 자동차는 "시동을 걸고", "달리고", "멈춘다"는 공통 기능을 가져야 함
- 하지만 각각의 자동차는 다른 방식으로 구현됨

```javascript
// 추상 제품 - 공통 인터페이스
class Vehicle {
    start() { throw new Error("구현 필요"); }
    drive() { throw new Error("구현 필요"); }
    stop() { throw new Error("구현 필요"); }
}
```

#### 2⃣ ConcreteProduct (구체적 제품) - "실제 만들어지는 것"
**역할**: Product의 규격에 맞춰 **실제로 만들어진 객체**

**실생활 비유**: 실제 자동차들 (세단, SUV, 트럭 등)
- 각각 다른 특징을 가지지만 모두 자동차의 기본 기능은 수행

```javascript
// 구체적 제품들
class Car extends Vehicle {
    start() { return "자동차 시동을 겁니다"; }
    drive() { return "자동차가 달립니다"; }
    stop() { return "자동차가 멈춥니다"; }
}

class Motorcycle extends Vehicle {
    start() { return "오토바이 시동을 겁니다"; }
    drive() { return "오토바이가 달립니다"; }
    stop() { return "오토바이가 멈춥니다"; }
}
```

#### 3⃣ Creator (생성자) - "만드는 방법을 정하는 것"
**역할**: **어떻게 만들지**에 대한 규칙을 정의하는 추상 클래스

**실생활 비유**: 자동차 제조 공정의 기본 틀
- "자동차를 만드는 과정"은 정의하지만, 구체적인 자동차 타입은 서브클래스에서 결정

```javascript
// 추상 생성자
class VehicleFactory {
    // 팩토리 메서드 - 서브클래스에서 구현
    createVehicle() {
        throw new Error("서브클래스에서 구현해야 합니다");
    }
    
    // 템플릿 메서드 - 공통 로직
    manufactureVehicle() {
        console.log("제조 시작...");
        const vehicle = this.createVehicle();
        console.log("제조 완료!");
        return vehicle;
    }
}
```

#### 4⃣ ConcreteCreator (구체적 생성자) - "실제로 만드는 것"
**역할**: **어떤 구체적인 객체를 만들지** 결정하고 실제로 생성

**실생활 비유**: 특정 자동차를 만드는 공장들
- 세단 공장, SUV 공장, 트럭 공장 등 각각 다른 타입의 자동차를 생산

```javascript
// 구체적 생성자들
class CarFactory extends VehicleFactory {
    createVehicle() {
        return new Car();
    }
}

class MotorcycleFactory extends VehicleFactory {
    createVehicle() {
        return new Motorcycle();
    }
}
```

### 패턴의 동작 흐름

```
1. 클라이언트 → ConcreteCreator에게 객체 생성 요청
2. ConcreteCreator → createVehicle() 메서드 호출
3. createVehicle() → 적절한 ConcreteProduct 생성
4. ConcreteProduct → 클라이언트에게 반환
```

**실생활 예시:**
1. 고객이 "자동차를 주세요"라고 요청
2. 자동차 공장에서 적절한 자동차를 제조
3. 완성된 자동차를 고객에게 전달
4. 고객은 자동차를 사용 (어떻게 만들어졌는지 몰라도 됨)

## ⚖ 장단점 분석

### 장점

#### 1. **느슨한 결합 (Loose Coupling)**
```javascript
// ❌ 강한 결합 - 클라이언트가 모든 클래스를 알아야 함
if (type === "car") {
    const vehicle = new Car();
} else if (type === "motorcycle") {
    const vehicle = new Motorcycle();
}

// ✅ 느슨한 결합 - 클라이언트는 팩토리만 알면 됨
const vehicle = VehicleFactory.createVehicle(type);
```

#### 2. **확장성 (Extensibility)**
```javascript
// 새로운 타입 추가가 쉬움 - 기존 코드 수정 없이
class ElectricCarFactory extends VehicleFactory {
    createVehicle() {
        return new ElectricCar();
    }
}
```

#### 3. **유지보수성 (Maintainability)**
- 객체 생성 로직이 **한 곳에 집중**
- 버그 수정이나 로직 변경 시 **한 곳만 수정**하면 됨
- 코드의 **일관성** 유지

#### 4. **테스트 용이성 (Testability)**
```javascript
// Mock 객체로 쉽게 테스트 가능
class MockVehicleFactory extends VehicleFactory {
    createVehicle() {
        return new MockVehicle();
    }
}
```

### 단점

#### 1. **클래스 수 증가**
- 각 제품마다 팩토리 클래스가 필요
- 작은 프로젝트에서는 **과도한 설계**가 될 수 있음

#### 2. **복잡성 증가**
- 단순한 객체 생성에 **과도한 추상화**
- 초보자에게는 **이해하기 어려울 수 있음**

#### 3. **성능 오버헤드**
- 추가적인 추상화 계층으로 인한 **약간의 성능 저하**
- 하지만 대부분의 경우 **무시할 수 있는 수준**

### 이 문서의 팩토리는 OCP 를 만족하지 않는다

위에서 개방-폐쇄 원칙을 장점으로 들었지만, 문서 전반에 나오는 형태는 그 원칙을 지키지 않는다.

```javascript
static createNewVehicle(type, brand, model) {
    switch (type.toLowerCase()) {
        case "car": return new Car(brand, model);
        case "motorcycle": return new Motorcycle(brand, model);
        // 트럭을 추가하려면? 이 함수를 연다.
    }
}
```

새 타입마다 팩토리를 **수정**해야 하니 "수정에는 닫혀 있다"가 성립하지 않는다. 달라진 것은 흩어져 있던 분기가 한 곳으로 모였다는 점이고, 그것만으로 충분히 값을 한다. 다만 그건 OCP 가 아니라 **분기의 국소화**다.

GoF 가 말한 Factory Method 는 서브클래스가 오버라이드하는 인스턴스 메서드다(`CarCreator extends Creator` 가 `createVehicle()` 을 구현). 위 `static create...(type)` 은 보통 Simple Factory 로 따로 부르는 것이고, 확장 방식이 다르다. 이름이 같아 보여서 "팩토리를 썼으니 OCP 를 지켰다"고 넘어가기 쉽다.

수정 없이 확장하려면 등록표를 둔다.

```javascript
class VehicleFactory {
  static #registry = new Map();
  static register(type, Ctor) { this.#registry.set(type, Ctor); }
  static create(type, ...args) {
    const Ctor = this.#registry.get(type);
    if (!Ctor) throw new Error(`지원하지 않는 차량 타입: ${type}`);
    return new Ctor(...args);
  }
}

VehicleFactory.register('truck', Truck);   // 팩토리 파일은 그대로 둔다
```

대신 대가가 있다. **등록 코드가 실행돼야 그 타입이 존재한다.** 등록이 든 모듈을 import 하지 않으면 런타임에야 "지원하지 않는 타입"이 나오고, 번들러가 부수효과뿐인 import 를 지워 같은 증상이 배포 환경에서만 나타나기도 한다. switch 는 이런 문제가 없고 타입스크립트라면 유니온으로 누락을 컴파일 시점에 잡을 수 있다.

| | switch 팩토리 | 등록표 팩토리 |
|---|---|---|
| 새 타입 추가 | 팩토리 파일 수정 | 등록 한 줄 |
| 누락 감지 | 컴파일·리뷰 시점 | 런타임 |
| 타입 좁히기 | 유니온으로 가능 | 대체로 문자열 키 |
| 맞는 자리 | 타입이 유한하고 한 팀이 관리 | 플러그인처럼 밖에서 타입이 들어옴 |

타입이 자주 늘지 않는다면 switch 쪽이 낫다. 등록표는 "팩토리를 고칠 수 없는 사람이 타입을 추가해야 할 때" 값을 한다.

## 언제 사용해야 할까?

### 적합한 상황

#### 1. **런타임에 객체 타입이 결정되는 경우**
```javascript
// 사용자 입력이나 설정에 따라 다른 객체 생성
const userType = getUserInput();
const user = UserFactory.createUser(userType);
```

#### 2. **객체 생성 로직이 복잡한 경우**
```javascript
// 복잡한 설정과 검증이 필요한 경우
const database = DatabaseFactory.createConnection({
    type: "mysql",
    host: "localhost",
    // ... 복잡한 설정들
});
```

#### 3. **확장이 예상되는 경우**
```javascript
// 새로운 결제 방식이 계속 추가될 예정
const payment = PaymentFactory.createPayment(paymentType);
```

#### 4. **의존성 주입이 필요한 경우**
```javascript
// 테스트나 다른 환경에서 다른 구현체가 필요한 경우
const logger = LoggerFactory.createLogger(environment);
```

### 부적합한 상황

#### 1. **단순한 객체 생성**
```javascript
// 단순한 객체는 직접 생성하는 것이 더 명확
const point = new Point(x, y);
```

#### 2. **객체 타입이 고정된 경우**
```javascript
// 항상 같은 타입만 생성한다면 팩토리가 불필요
const config = new AppConfig();
```

#### 3. **성능이 매우 중요한 경우**
```javascript
// 게임 엔진의 루프에서 매 프레임마다 호출되는 경우
// 직접 생성이 더 효율적일 수 있음
```

#### 4. **작은 프로젝트**
```javascript
// 프로토타입이나 간단한 스크립트에서는 과도한 설계
```

## 🤔 사용 여부 판단 기준

### 다음 질문들에 답해보세요:

1. **"새로운 타입이 추가될 가능성이 있나요?"**
   - Yes → Factory Method 패턴 고려
   - No → 직접 생성 고려

2. **"객체 생성 로직이 복잡한가요?"**
   - Yes → Factory Method 패턴 고려
   - No → 직접 생성 고려

3. **"클라이언트가 구체적인 클래스를 알 필요가 없나요?"**
   - Yes → Factory Method 패턴 고려
   - No → 직접 생성 고려

4. **"테스트에서 다른 구현체가 필요한가요?"**
   - Yes → Factory Method 패턴 고려
   - No → 직접 생성 고려

**2개 이상 "Yes"라면 Factory Method 패턴을 사용하는 것을 권장합니다!**

## 단계별 구현 예제

### 1단계: 기본 Factory Method 패턴

가장 기본적인 Factory Method 패턴을 **교통수단 예제**로 구현해보겠습니다. 단계별로 따라해보세요!

#### Step 1: Product (제품) 정의
```javascript
// 1️⃣ 추상 제품 클래스 - 모든 교통수단의 공통 규격
class Vehicle {
    constructor() {
        if (new.target === Vehicle) {
            throw new Error("Vehicle은 추상 클래스입니다. 직접 인스턴스화할 수 없습니다.");
        }
    }

    // 모든 교통수단이 가져야 할 공통 메서드들
    start() {
        throw new Error("start() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    stop() {
        throw new Error("stop() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    getInfo() {
        throw new Error("getInfo() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}
```

#### Step 2: ConcreteProduct (구체적 제품) 구현
```javascript
// 2️⃣ 구체적인 제품들 - 실제 교통수단들
class Car extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "자동차";
    }

    start() {
        return `${this.brand} ${this.model} 자동차가 시동을 겁니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 자동차가 정지합니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}

class Motorcycle extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "오토바이";
    }

    start() {
        return `${this.brand} ${this.model} 오토바이가 시동을 겁니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 오토바이가 정지합니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}

class Bicycle extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "자전거";
    }

    start() {
        return `${this.brand} ${this.model} 자전거를 타기 시작합니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 자전거를 멈춥니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}
```

#### Step 3: Creator (생성자) 정의
```javascript
// 3️⃣ 추상 생성자 클래스 - 팩토리의 기본 틀
class VehicleFactory {
    // 팩토리 메서드 - 서브클래스에서 구현
    createVehicle(brand, model) {
        throw new Error("createVehicle() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    // 템플릿 메서드 - 공통 로직 (제조 과정)
    manufactureVehicle(brand, model) {
        console.log(`🏭 ${brand} ${model} 제조를 시작합니다...`);
        const vehicle = this.createVehicle(brand, model);
        console.log(`✅ ${brand} ${model} 제조가 완료되었습니다.`);
        return vehicle;
    }
}
```

#### Step 4: ConcreteCreator (구체적 생성자) 구현
```javascript
// 4️⃣ 구체적인 생성자들 - 실제 공장들
class CarFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Car(brand, model);
    }
}

class MotorcycleFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Motorcycle(brand, model);
    }
}

class BicycleFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Bicycle(brand, model);
    }
}
```

#### Step 5: 클라이언트 코드 작성
```javascript
// 5️⃣ 클라이언트 코드 - 팩토리를 사용하는 코드
class VehicleDealer {
    constructor(factory) {
        this.factory = factory;
    }

    orderVehicle(brand, model) {
        const vehicle = this.factory.manufactureVehicle(brand, model);
        console.log(`📋 주문 완료: ${vehicle.getInfo()}`);
        return vehicle;
    }

    testDrive(vehicle) {
        console.log(`🚗 ${vehicle.start()}`);
        console.log("🛣️ 테스트 드라이브 중...");
        console.log(`🛑 ${vehicle.stop()}`);
    }
}
```

#### Step 6: 사용 예시
```javascript
// 6️⃣ 실제 사용 예시
console.log("=== Factory Method 패턴 데모 ===\n");

// 각각의 공장 생성
const carFactory = new CarFactory();
const motorcycleFactory = new MotorcycleFactory();
const bicycleFactory = new BicycleFactory();

// 딜러 생성
const carDealer = new VehicleDealer(carFactory);
const motorcycleDealer = new VehicleDealer(motorcycleFactory);
const bicycleDealer = new VehicleDealer(bicycleFactory);

// 자동차 주문 및 테스트
console.log("🚗 자동차 주문:");
const toyota = carDealer.orderVehicle("Toyota", "Camry");
carDealer.testDrive(toyota);

console.log("\n🏍️ 오토바이 주문:");
const honda = motorcycleDealer.orderVehicle("Honda", "CBR600RR");
motorcycleDealer.testDrive(honda);

console.log("\n🚲 자전거 주문:");
const giant = bicycleDealer.orderVehicle("Giant", "Defy Advanced");
bicycleDealer.testDrive(giant);
```

#### 실행 결과
```
=== Factory Method 패턴 데모 ===

🚗 자동차 주문:
🏭 Toyota Camry 제조를 시작합니다...
✅ Toyota Camry 제조가 완료되었습니다.
📋 주문 완료: 타입: 자동차, 브랜드: Toyota, 모델: Camry
🚗 Toyota Camry 자동차가 시동을 겁니다.
🛣️ 테스트 드라이브 중...
🛑 Toyota Camry 자동차가 정지합니다.

🏍️ 오토바이 주문:
🏭 Honda CBR600RR 제조를 시작합니다...
✅ Honda CBR600RR 제조가 완료되었습니다.
📋 주문 완료: 타입: 오토바이, 브랜드: Honda, 모델: CBR600RR
🚗 Honda CBR600RR 오토바이가 시동을 겁니다.
🛣️ 테스트 드라이브 중...
🛑 Honda CBR600RR 오토바이가 정지합니다.

🚲 자전거 주문:
🏭 Giant Defy Advanced 제조를 시작합니다...
✅ Giant Defy Advanced 제조가 완료되었습니다.
📋 주문 완료: 타입: 자전거, 브랜드: Giant, 모델: Defy Advanced
🚗 Giant Defy Advanced 자전거를 타기 시작합니다.
🛣️ 테스트 드라이브 중...
🛑 Giant Defy Advanced 자전거를 멈춥니다.
```

### 주요 내용

1. **클라이언트는 구체적인 클래스를 모름** - `Car`, `Motorcycle`, `Bicycle` 클래스를 직접 사용하지 않음
2. **팩토리가 객체 생성 책임** - 어떤 객체를 만들지 팩토리가 결정
3. **확장이 쉬움** - 새로운 교통수단 타입 추가 시 새로운 팩토리만 만들면 됨
4. **일관된 인터페이스** - 모든 교통수단은 동일한 메서드를 가짐

```javascript
// 1. Product (추상 제품)
class Vehicle {
    constructor() {
        if (new.target === Vehicle) {
            throw new Error("Vehicle은 추상 클래스입니다. 직접 인스턴스화할 수 없습니다.");
        }
    }

    // 공통 인터페이스 정의
    start() {
        throw new Error("start() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    stop() {
        throw new Error("stop() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    getInfo() {
        throw new Error("getInfo() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 2. ConcreteProduct (구체적 제품들)
class Car extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "자동차";
    }

    start() {
        return `${this.brand} ${this.model} 자동차가 시동을 겁니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 자동차가 정지합니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}

class Motorcycle extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "오토바이";
    }

    start() {
        return `${this.brand} ${this.model} 오토바이가 시동을 겁니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 오토바이가 정지합니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}

class Bicycle extends Vehicle {
    constructor(brand, model) {
        super();
        this.brand = brand;
        this.model = model;
        this.type = "자전거";
    }

    start() {
        return `${this.brand} ${this.model} 자전거를 타기 시작합니다.`;
    }

    stop() {
        return `${this.brand} ${this.model} 자전거를 멈춥니다.`;
    }

    getInfo() {
        return `타입: ${this.type}, 브랜드: ${this.brand}, 모델: ${this.model}`;
    }
}

// 3. Creator (추상 생성자)
class VehicleFactory {
    // 팩토리 메서드 - 서브클래스에서 구현
    createVehicle(brand, model) {
        throw new Error("createVehicle() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    // 템플릿 메서드 - 공통 로직
    manufactureVehicle(brand, model) {
        console.log(`${brand} ${model} 제조를 시작합니다...`);
        const vehicle = this.createVehicle(brand, model);
        console.log(`${brand} ${model} 제조가 완료되었습니다.`);
        return vehicle;
    }
}

// 4. ConcreteCreator (구체적 생성자들)
class CarFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Car(brand, model);
    }
}

class MotorcycleFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Motorcycle(brand, model);
    }
}

class BicycleFactory extends VehicleFactory {
    createVehicle(brand, model) {
        return new Bicycle(brand, model);
    }
}

// 5. 클라이언트 코드
class VehicleDealer {
    constructor(factory) {
        this.factory = factory;
    }

    orderVehicle(brand, model) {
        const vehicle = this.factory.manufactureVehicle(brand, model);
        console.log(`주문 완료: ${vehicle.getInfo()}`);
        return vehicle;
    }

    testDrive(vehicle) {
        console.log(vehicle.start());
        console.log("테스트 드라이브 중...");
        console.log(vehicle.stop());
    }
}

// 6. 사용 예시
const carFactory = new CarFactory();
const motorcycleFactory = new MotorcycleFactory();
const bicycleFactory = new BicycleFactory();

const carDealer = new VehicleDealer(carFactory);
const motorcycleDealer = new VehicleDealer(motorcycleFactory);
const bicycleDealer = new VehicleDealer(bicycleFactory);

// 자동차 주문 및 테스트
const toyota = carDealer.orderVehicle("Toyota", "Camry");
carDealer.testDrive(toyota);

// 오토바이 주문 및 테스트
const honda = motorcycleDealer.orderVehicle("Honda", "CBR600RR");
motorcycleDealer.testDrive(honda);

// 자전거 주문 및 테스트
const giant = bicycleDealer.orderVehicle("Giant", "Defy Advanced");
bicycleDealer.testDrive(giant);
```

### 2. 정적 팩토리 메서드 패턴

클래스 인스턴스화 없이 정적 메서드로 객체를 생성하는 방식입니다.

```javascript
class VehicleStaticFactory {
    static createCar(brand, model) {
        return new Car(brand, model);
    }

    static createMotorcycle(brand, model) {
        return new Motorcycle(brand, model);
    }

    static createBicycle(brand, model) {
        return new Bicycle(brand, model);
    }

    // 타입 기반 생성
    static createVehicle(type, brand, model) {
        switch (type.toLowerCase()) {
            case 'car':
                return this.createCar(brand, model);
            case 'motorcycle':
                return this.createMotorcycle(brand, model);
            case 'bicycle':
                return this.createBicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }

    // 설정 객체 기반 생성
    static createFromConfig(config) {
        const { type, brand, model, ...options } = config;
        const vehicle = this.createVehicle(type, brand, model);
        
        // 추가 옵션 설정
        if (options.color) {
            vehicle.color = options.color;
        }
        if (options.year) {
            vehicle.year = options.year;
        }
        
        return vehicle;
    }
}

// 사용 예시
const vehicle1 = VehicleStaticFactory.createCar("BMW", "X5");
const vehicle2 = VehicleStaticFactory.createVehicle("motorcycle", "Yamaha", "R1");
const vehicle3 = VehicleStaticFactory.createFromConfig({
    type: "bicycle",
    brand: "Trek",
    model: "Madone",
    color: "Red",
    year: 2024
});
```

## 실제 사용 사례

### 1. 데이터베이스 연결 관리 시스템

실제 프로덕션 환경에서 가장 많이 사용되는 사례 중 하나입니다.

```javascript
// 추상 데이터베이스 연결 클래스
class DatabaseConnection {
    constructor(config) {
        if (new.target === DatabaseConnection) {
            throw new Error("DatabaseConnection은 추상 클래스입니다.");
        }
        this.config = config;
        this.isConnected = false;
    }

    async connect() {
        throw new Error("connect() 메서드는 서브클래스에서 구현해야 합니다.");
    }
    
    async disconnect() {
        throw new Error("disconnect() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    async query(sql, params = []) {
        throw new Error("query() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    getConnectionInfo() {
        throw new Error("getConnectionInfo() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// MySQL 연결 구현
class MySQLConnection extends DatabaseConnection {
    async connect() {
        try {
            // 실제 MySQL 연결 로직 (예시)
            console.log(`MySQL 연결 시도: ${this.config.host}:${this.config.port}`);
            this.isConnected = true;
            return { success: true, message: "MySQL 연결 성공" };
        } catch (error) {
            throw new Error(`MySQL 연결 실패: ${error.message}`);
        }
    }
    
    async disconnect() {
        this.isConnected = false;
        return { success: true, message: "MySQL 연결 해제" };
    }

    async query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error("데이터베이스에 연결되지 않았습니다.");
        }
        // 실제 쿼리 실행 로직
        return { rows: [], affectedRows: 0 };
    }

    getConnectionInfo() {
        return {
            type: "MySQL",
            host: this.config.host,
            port: this.config.port,
            database: this.config.database,
            isConnected: this.isConnected
        };
    }
}

// PostgreSQL 연결 구현
class PostgreSQLConnection extends DatabaseConnection {
    async connect() {
        try {
            console.log(`PostgreSQL 연결 시도: ${this.config.host}:${this.config.port}`);
            this.isConnected = true;
            return { success: true, message: "PostgreSQL 연결 성공" };
        } catch (error) {
            throw new Error(`PostgreSQL 연결 실패: ${error.message}`);
        }
    }
    
    async disconnect() {
        this.isConnected = false;
        return { success: true, message: "PostgreSQL 연결 해제" };
    }

    async query(sql, params = []) {
        if (!this.isConnected) {
            throw new Error("데이터베이스에 연결되지 않았습니다.");
        }
        // 실제 쿼리 실행 로직
        return { rows: [], affectedRows: 0 };
    }

    getConnectionInfo() {
        return {
            type: "PostgreSQL",
            host: this.config.host,
            port: this.config.port,
            database: this.config.database,
            isConnected: this.isConnected
        };
    }
}

// MongoDB 연결 구현
class MongoDBConnection extends DatabaseConnection {
    async connect() {
        try {
            console.log(`MongoDB 연결 시도: ${this.config.host}:${this.config.port}`);
            this.isConnected = true;
            return { success: true, message: "MongoDB 연결 성공" };
        } catch (error) {
            throw new Error(`MongoDB 연결 실패: ${error.message}`);
        }
    }
    
    async disconnect() {
        this.isConnected = false;
        return { success: true, message: "MongoDB 연결 해제" };
    }

    async query(collection, operation, data = {}) {
        if (!this.isConnected) {
            throw new Error("데이터베이스에 연결되지 않았습니다.");
        }
        // 실제 MongoDB 쿼리 실행 로직
        return { documents: [], modifiedCount: 0 };
    }

    getConnectionInfo() {
        return {
            type: "MongoDB",
            host: this.config.host,
            port: this.config.port,
            database: this.config.database,
            isConnected: this.isConnected
        };
    }
}

// 데이터베이스 팩토리 클래스
class DatabaseFactory {
    static createConnection(type, config) {
        const normalizedType = type.toLowerCase();
        
        switch (normalizedType) {
            case "mysql":
                return new MySQLConnection(config);
            case "postgresql":
            case "postgres":
                return new PostgreSQLConnection(config);
            case "mongodb":
            case "mongo":
                return new MongoDBConnection(config);
            default:
                throw new Error(`지원하지 않는 데이터베이스 타입: ${type}`);
        }
    }

    // 설정 기반 연결 생성
    static createFromConfig(config) {
        const { type, ...dbConfig } = config;
        return this.createConnection(type, dbConfig);
    }

    // 연결 풀 관리
    static createConnectionPool(type, config, poolSize = 10) {
        const connections = [];
        for (let i = 0; i < poolSize; i++) {
            connections.push(this.createConnection(type, config));
        }
        return connections;
    }
}

// 사용 예시
async function demonstrateDatabaseFactory() {
    // MySQL 연결
    const mysqlConfig = { 
        host: "localhost", 
        port: 3306, 
        database: "myapp",
        username: "user",
        password: "password"
    };
    
    const mysqlConnection = DatabaseFactory.createConnection("mysql", mysqlConfig);
    await mysqlConnection.connect();
    console.log(mysqlConnection.getConnectionInfo());

    // PostgreSQL 연결
    const postgresConfig = { 
        host: "localhost", 
        port: 5432, 
        database: "myapp",
        username: "user",
        password: "password"
    };
    
    const postgresConnection = DatabaseFactory.createConnection("postgresql", postgresConfig);
    await postgresConnection.connect();
    console.log(postgresConnection.getConnectionInfo());

    // 설정 기반 연결
    const mongoConfig = {
        type: "mongodb",
        host: "localhost",
        port: 27017,
        database: "myapp"
    };
    
    const mongoConnection = DatabaseFactory.createFromConfig(mongoConfig);
    await mongoConnection.connect();
    console.log(mongoConnection.getConnectionInfo());
}

// demonstrateDatabaseFactory();
```

### 2. UI 컴포넌트 라이브러리

React, Vue 등의 프레임워크에서 사용되는 컴포넌트 팩토리 패턴입니다.

```javascript
// 추상 UI 컴포넌트 클래스
class UIComponent {
    constructor(props = {}) {
        if (new.target === UIComponent) {
            throw new Error("UIComponent는 추상 클래스입니다.");
        }
        this.props = props;
        this.id = this.generateId();
    }

    generateId() {
        return `component_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    render() {
        throw new Error("render() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    mount(container) {
        throw new Error("mount() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    unmount() {
        throw new Error("unmount() 메서드는 서브클래스에서 구현해야 합니다.");
    }

    getProps() {
        return { ...this.props };
    }
}

// 버튼 컴포넌트
class Button extends UIComponent {
    constructor(props) {
        super(props);
        this.text = props.text || "Button";
        this.onClick = props.onClick || (() => {});
        this.variant = props.variant || "primary";
        this.size = props.size || "medium";
    }
    
    render() {
        const classes = `btn btn-${this.variant} btn-${this.size}`;
        return `<button id="${this.id}" class="${classes}" onclick="window.handleClick('${this.id}')">${this.text}</button>`;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        
        // 이벤트 리스너 등록
        window.handleClick = window.handleClick || {};
        window.handleClick[this.id] = this.onClick;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
        delete window.handleClick[this.id];
    }
}

// 입력 필드 컴포넌트
class InputField extends UIComponent {
    constructor(props) {
        super(props);
        this.placeholder = props.placeholder || "";
        this.type = props.type || "text";
        this.value = props.value || "";
        this.onChange = props.onChange || (() => {});
        this.required = props.required || false;
    }
    
    render() {
        const requiredAttr = this.required ? 'required' : '';
        return `<input id="${this.id}" type="${this.type}" placeholder="${this.placeholder}" value="${this.value}" ${requiredAttr} onchange="window.handleInputChange('${this.id}', this.value)">`;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        
        // 이벤트 리스너 등록
        window.handleInputChange = window.handleInputChange || {};
        window.handleInputChange[this.id] = this.onChange;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
        delete window.handleInputChange[this.id];
    }
}

// 모달 컴포넌트
class Modal extends UIComponent {
    constructor(props) {
        super(props);
        this.title = props.title || "Modal";
        this.content = props.content || "";
        this.onClose = props.onClose || (() => {});
        this.showCloseButton = props.showCloseButton !== false;
    }
    
    render() {
        const closeButton = this.showCloseButton ? 
            `<button class="modal-close" onclick="window.handleModalClose('${this.id}')">&times;</button>` : '';
        
        return `
            <div id="${this.id}" class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>${this.title}</h3>
                        ${closeButton}
                    </div>
                    <div class="modal-body">
                        ${this.content}
                    </div>
                </div>
            </div>
        `;
    }

    mount(container) {
        const element = document.createElement('div');
        element.innerHTML = this.render();
        container.appendChild(element.firstElementChild);
        
        // 이벤트 리스너 등록
        window.handleModalClose = window.handleModalClose || {};
        window.handleModalClose[this.id] = this.onClose;
    }

    unmount() {
        const element = document.getElementById(this.id);
        if (element) {
            element.remove();
        }
        delete window.handleModalClose[this.id];
    }
}

// UI 컴포넌트 팩토리
class UIComponentFactory {
    static createComponent(type, props = {}) {
        const normalizedType = type.toLowerCase();
        
        switch (normalizedType) {
            case "button":
                return new Button(props);
            case "input":
            case "inputfield":
                return new InputField(props);
            case "modal":
                return new Modal(props);
            default:
                throw new Error(`지원하지 않는 컴포넌트 타입: ${type}`);
        }
    }

    // 설정 기반 컴포넌트 생성
    static createFromConfig(config) {
        const { type, ...props } = config;
        return this.createComponent(type, props);
    }

    // 여러 컴포넌트 일괄 생성
    static createComponents(componentConfigs) {
        return componentConfigs.map(config => this.createFromConfig(config));
    }
}

// 사용 예시
function demonstrateUIComponentFactory() {
    const container = document.getElementById('app') || document.body;
    
    // 버튼 생성
    const button = UIComponentFactory.createComponent("button", {
        text: "클릭하세요",
        variant: "primary",
        size: "large",
        onClick: () => alert("버튼이 클릭되었습니다!")
    });
    button.mount(container);

    // 입력 필드 생성
    const input = UIComponentFactory.createComponent("input", {
        placeholder: "이름을 입력하세요",
        type: "text",
        required: true,
        onChange: (value) => console.log("입력값:", value)
    });
    input.mount(container);

    // 모달 생성
    const modal = UIComponentFactory.createComponent("modal", {
        title: "알림",
        content: "이것은 팩토리 패턴으로 생성된 모달입니다.",
        onClose: () => console.log("모달이 닫혔습니다.")
    });
    modal.mount(container);

    // 설정 기반 생성
    const components = UIComponentFactory.createComponents([
        {
            type: "button",
            text: "저장",
            variant: "success"
        },
        {
            type: "button", 
            text: "취소",
            variant: "secondary"
        },
        {
            type: "input",
            placeholder: "이메일",
            type: "email"
        }
    ]);

    components.forEach(component => component.mount(container));
}

// demonstrateUIComponentFactory();
```

## 고급 패턴과 최적화

### 1. 캐싱 팩토리 패턴

자주 생성되는 객체를 캐시하여 성능을 최적화하는 패턴입니다.

```javascript
class CachedVehicleFactory {
    static cache = new Map();
    static maxCacheSize = 100;
    
    static createVehicle(type, brand, model) {
        const cacheKey = `${type}_${brand}_${model}`;
        
        // 캐시에서 확인
        if (this.cache.has(cacheKey)) {
            console.log(`캐시에서 ${cacheKey} 반환`);
            return this.cache.get(cacheKey);
        }
        
        // 새 객체 생성
        const vehicle = this.createNewVehicle(type, brand, model);
        
        // 캐시 크기 제한
        if (this.cache.size >= this.maxCacheSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        // 캐시에 저장
        this.cache.set(cacheKey, vehicle);
        console.log(`새로 생성된 ${cacheKey}를 캐시에 저장`);
        
        return vehicle;
    }
    
    static createNewVehicle(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
    
    static clearCache() {
        this.cache.clear();
        console.log("캐시가 초기화되었습니다.");
    }
    
    static getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize,
            keys: Array.from(this.cache.keys())
        };
    }
}

// 사용 예시
const vehicle1 = CachedVehicleFactory.createVehicle("car", "Toyota", "Camry");
const vehicle2 = CachedVehicleFactory.createVehicle("car", "Toyota", "Camry"); // 캐시에서 반환
console.log(CachedVehicleFactory.getCacheStats());
```

#### 이 "캐싱 팩토리" 는 캐시가 아니라 인스턴스 공유다

같은 키로 두 번 부르면 **같은 객체**가 돌아온다.

```javascript
const v1 = CachedVehicleFactory.createVehicle("car", "Toyota", "Camry");
const v2 = CachedVehicleFactory.createVehicle("car", "Toyota", "Camry");
v1 === v2        // true
v1.start();
v2.isRunning     // true  ← v2 는 건드린 적이 없다
```

"캐시" 라는 이름 때문에 생성 비용만 아끼는 것처럼 읽히지만, 실제로는 호출자 전원이 하나의 가변 객체를 나눠 쓰는 구조다. 한 요청이 상태를 바꾸면 다른 요청이 그 상태를 본다. **팩토리에 캐시를 붙이려면 만들어지는 객체가 불변이거나 무상태여야 한다.** 주행 상태를 갖는 차량은 그 조건에 맞지 않는다. 굳이 재사용하겠다면 캐시에는 생성 재료만 담고 매 호출에 새 인스턴스를 만들거나, 반환 직전에 복제한다.

축출 정책도 이름과 다르다. `this.cache.keys().next().value` 는 Map 에 **가장 먼저 넣은** 키를 지운다. `get` 은 Map 의 순서를 바꾸지 않으므로 아무리 자주 읽어도 오래된 항목부터 나간다 — LRU 가 아니라 FIFO 다.

```
상한 3에서 A B C 를 넣고 → A 를 다시 읽고 → D 를 넣으면
남는 키: B C D        (A 를 방금 읽었는데도 축출된다)
```

LRU 로 만들려면 히트 시 `delete` 후 `set` 으로 다시 넣어 순서를 갱신한다.

`static cache` 를 상속과 함께 쓸 때도 봐야 한다. 정적 필드는 프로토타입 체인을 타고 상속되므로 `class SubFactory extends CachedVehicleFactory {}` 는 자기 Map 을 갖지 않고 **부모의 Map 에 쓴다.** 서브 팩토리마다 캐시를 나누려면 각 클래스에 `static cache = new Map()` 을 다시 선언해야 한다. 이 공유는 조용해서, 서브 팩토리를 여러 개 만든 뒤에야 "왜 남의 차량이 나오지" 로 드러난다.

### 2. 빌더 패턴과 결합한 팩토리

복잡한 객체 생성을 단계별로 처리하는 패턴입니다.

```javascript
class VehicleBuilder {
    constructor() {
        this.reset();
    }
    
    reset() {
        this.vehicle = null;
        this.type = null;
        this.brand = null;
        this.model = null;
        this.options = {};
        return this;
    }
    
    setType(type) {
        this.type = type;
        return this;
    }
    
    setBrand(brand) {
        this.brand = brand;
        return this;
    }
    
    setModel(model) {
        this.model = model;
        return this;
    }
    
    setColor(color) {
        this.options.color = color;
        return this;
    }
    
    setYear(year) {
        this.options.year = year;
        return this;
    }
    
    setEngine(engine) {
        this.options.engine = engine;
        return this;
    }
    
    build() {
        if (!this.type || !this.brand || !this.model) {
            throw new Error("필수 정보가 누락되었습니다: type, brand, model");
        }
        
        const vehicle = VehicleFactory.createVehicle(this.type, this.brand, this.model);
        
        // 추가 옵션 설정
        Object.assign(vehicle, this.options);
        
        this.reset();
        return vehicle;
    }
}

class AdvancedVehicleFactory {
    static builder() {
        return new VehicleBuilder();
    }
    
    static createFromSpec(spec) {
        return this.builder()
            .setType(spec.type)
            .setBrand(spec.brand)
            .setModel(spec.model)
            .setColor(spec.color)
            .setYear(spec.year)
            .setEngine(spec.engine)
            .build();
    }
}

// 사용 예시
const luxuryCar = AdvancedVehicleFactory.builder()
    .setType("car")
    .setBrand("BMW")
    .setModel("X5")
    .setColor("Black")
    .setYear(2024)
    .setEngine("V8")
    .build();

const sportBike = AdvancedVehicleFactory.createFromSpec({
    type: "motorcycle",
    brand: "Yamaha",
    model: "R1",
    color: "Blue",
    year: 2024,
    engine: "1000cc"
});
```

### 3. 프로토타입 팩토리 패턴

기존 객체를 복제하여 새로운 객체를 생성하는 패턴입니다.

```javascript
class VehiclePrototype {
    constructor() {
        this.prototypes = new Map();
        this.initializePrototypes();
    }
    
    initializePrototypes() {
        // 기본 프로토타입 등록
        this.prototypes.set("car", new Car("", ""));
        this.prototypes.set("motorcycle", new Motorcycle("", ""));
        this.prototypes.set("bicycle", new Bicycle("", ""));
    }
    
    createVehicle(type, brand, model) {
        const prototype = this.prototypes.get(type.toLowerCase());
        if (!prototype) {
            throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
        
        // 프로토타입 복제
        const vehicle = Object.create(Object.getPrototypeOf(prototype));
        vehicle.brand = brand;
        vehicle.model = model;
        vehicle.type = prototype.type;
        
        return vehicle;
    }
    
    registerPrototype(type, prototype) {
        this.prototypes.set(type.toLowerCase(), prototype);
    }
}

// 사용 예시
const prototypeFactory = new VehiclePrototype();
const car1 = prototypeFactory.createVehicle("car", "Honda", "Civic");
const car2 = prototypeFactory.createVehicle("car", "Toyota", "Corolla");
```

### 4. 의존성 주입과 결합한 팩토리

외부에서 의존성을 주입받아 객체를 생성하는 패턴입니다.

```javascript
class DependencyInjectionFactory {
    constructor(dependencies = {}) {
        this.dependencies = dependencies;
    }
    
    registerDependency(name, dependency) {
        this.dependencies[name] = dependency;
    }
    
    createVehicle(type, brand, model) {
        const vehicle = this.createBaseVehicle(type, brand, model);
        
        // 의존성 주입
        if (this.dependencies.logger) {
            vehicle.logger = this.dependencies.logger;
        }
        
        if (this.dependencies.config) {
            vehicle.config = this.dependencies.config;
        }
        
        if (this.dependencies.eventBus) {
            vehicle.eventBus = this.dependencies.eventBus;
        }
        
        return vehicle;
    }
    
    createBaseVehicle(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
}

// 사용 예시
const logger = { log: (msg) => console.log(msg) };
const config = { debug: true, version: "1.0.0" };
const eventBus = { emit: (event) => console.log(`Event: ${event}`) };

const diFactory = new DependencyInjectionFactory({
    logger,
    config,
    eventBus
});

const vehicle = diFactory.createVehicle("car", "Tesla", "Model S");
```

## 운영 환경에서의 고려사항

### 1. 성능 최적화 전략

#### 1.1 객체 풀링 (Object Pooling)
자주 생성되고 소멸되는 객체의 메모리 할당/해제 비용을 줄이는 기법입니다.

```javascript
class VehiclePool {
    constructor(vehicleType, initialSize = 10, maxSize = 50) {
        this.vehicleType = vehicleType;
        this.pool = [];
        this.maxSize = maxSize;
        this.initializePool(initialSize);
    }
    
    initializePool(size) {
        for (let i = 0; i < size; i++) {
            this.pool.push(this.createVehicle());
        }
    }
    
    createVehicle() {
        switch (this.vehicleType) {
            case "car":
                return new Car("", "");
            case "motorcycle":
                return new Motorcycle("", "");
            case "bicycle":
                return new Bicycle("", "");
            default:
                throw new Error(`지원하지 않는 차량 타입: ${this.vehicleType}`);
        }
    }
    
    acquire(brand, model) {
        let vehicle;
        if (this.pool.length > 0) {
            vehicle = this.pool.pop();
        } else {
            vehicle = this.createVehicle();
        }
        
        vehicle.brand = brand;
        vehicle.model = model;
        vehicle.reset && vehicle.reset(); // 객체 초기화
        
        return vehicle;
    }
    
    release(vehicle) {
        if (this.pool.length < this.maxSize) {
            vehicle.reset && vehicle.reset();
            this.pool.push(vehicle);
        }
    }
    
    getStats() {
        return {
            available: this.pool.length,
            maxSize: this.maxSize,
            type: this.vehicleType
        };
    }
}

// 사용 예시
const carPool = new VehiclePool("car", 5, 20);
const car1 = carPool.acquire("Toyota", "Camry");
// 사용 후 반환
carPool.release(car1);
```

#### 1.2 지연 초기화 (Lazy Initialization)
객체가 실제로 필요할 때까지 생성을 지연시키는 기법입니다.

```javascript
class LazyVehicleFactory {
    constructor() {
        this.vehicles = new Map();
    }
    
    getVehicle(type, brand, model) {
        const key = `${type}_${brand}_${model}`;
        
        if (!this.vehicles.has(key)) {
            console.log(`지연 초기화: ${key} 생성`);
            this.vehicles.set(key, this.createVehicle(type, brand, model));
        }
        
        return this.vehicles.get(key);
    }
    
    createVehicle(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
}
```

### 2. 에러 처리 및 복구 전략

#### 2.1 안전한 팩토리 패턴
```javascript
class SafeVehicleFactory {
    static createVehicle(type, brand, model) {
        try {
            return this.createVehicleInternal(type, brand, model);
        } catch (error) {
            console.error(`객체 생성 실패: ${error.message}`);
            
            // 폴백 전략
            if (this.isRetryableError(error)) {
                return this.retryCreation(type, brand, model);
            }
            
            // 기본 객체 반환
            return this.createDefaultVehicle(type);
        }
    }
    
    static createVehicleInternal(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
    
    static isRetryableError(error) {
        return error.message.includes("일시적") || 
               error.message.includes("네트워크") ||
               error.message.includes("타임아웃");
    }
    
    static retryCreation(type, brand, model, maxRetries = 3) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                console.log(`재시도 ${i + 1}/${maxRetries}: ${type} 생성`);
                return this.createVehicleInternal(type, brand, model);
            } catch (error) {
                if (i === maxRetries - 1) {
                    console.error(`최대 재시도 횟수 초과: ${error.message}`);
                    return this.createDefaultVehicle(type);
                }
                // 지수 백오프
                const delay = Math.pow(2, i) * 1000;
                console.log(`${delay}ms 후 재시도...`);
                // 실제로는 setTimeout이나 Promise를 사용
            }
        }
    }
    
    static createDefaultVehicle(type) {
        console.log(`기본 ${type} 객체 생성`);
        return new Car("Unknown", "Default");
    }
}
```

### 3. 로깅 및 모니터링

#### 3.1 상세한 로깅 팩토리
```javascript
class LoggedVehicleFactory {
    constructor(logger) {
        this.logger = logger || console;
        this.metrics = {
            totalCreated: 0,
            creationTimes: [],
            errors: 0
        };
    }
    
    createVehicle(type, brand, model) {
        const startTime = Date.now();
        const requestId = this.generateRequestId();
        
        this.logger.info(`[${requestId}] 객체 생성 시작: ${type}`, {
            type,
            brand,
            model,
            timestamp: new Date().toISOString()
        });
        
        try {
            const vehicle = this.createVehicleInternal(type, brand, model);
            const endTime = Date.now();
            const duration = endTime - startTime;
            
            this.metrics.totalCreated++;
            this.metrics.creationTimes.push(duration);
            
            this.logger.info(`[${requestId}] 객체 생성 완료`, {
                type,
                brand,
                model,
                duration: `${duration}ms`,
                totalCreated: this.metrics.totalCreated
            });
            
            return vehicle;
        } catch (error) {
            this.metrics.errors++;
            this.logger.error(`[${requestId}] 객체 생성 실패`, {
                type,
                brand,
                model,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }
    
    createVehicleInternal(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
    
    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    getMetrics() {
        const avgCreationTime = this.metrics.creationTimes.length > 0 
            ? this.metrics.creationTimes.reduce((a, b) => a + b, 0) / this.metrics.creationTimes.length
            : 0;
            
        return {
            ...this.metrics,
            averageCreationTime: Math.round(avgCreationTime),
            errorRate: this.metrics.totalCreated > 0 
                ? (this.metrics.errors / this.metrics.totalCreated * 100).toFixed(2) + '%'
                : '0%'
        };
    }
}
```

### 4. 테스트 전략

#### 4.1 Mock 팩토리
```javascript
class MockVehicleFactory {
    constructor() {
        this.createdVehicles = [];
        this.shouldThrowError = false;
        this.errorMessage = "Mock error";
    }
    
    createVehicle(type, brand, model) {
        if (this.shouldThrowError) {
            throw new Error(this.errorMessage);
        }
        
        const mockVehicle = {
            type,
            brand,
            model,
            id: `mock_${Date.now()}`,
            isMock: true
        };
        
        this.createdVehicles.push(mockVehicle);
        return mockVehicle;
    }
    
    // 테스트 헬퍼 메서드들
    setShouldThrowError(shouldThrow, message = "Mock error") {
        this.shouldThrowError = shouldThrow;
        this.errorMessage = message;
    }
    
    getCreatedVehicles() {
        return [...this.createdVehicles];
    }
    
    clearCreatedVehicles() {
        this.createdVehicles = [];
    }
    
    getCreatedVehicleCount() {
        return this.createdVehicles.length;
    }
}

// 테스트 예시
function testVehicleFactory() {
    const mockFactory = new MockVehicleFactory();
    
    // 정상 케이스 테스트
    const vehicle = mockFactory.createVehicle("car", "Toyota", "Camry");
    console.assert(vehicle.type === "car");
    console.assert(vehicle.brand === "Toyota");
    console.assert(vehicle.model === "Camry");
    console.assert(mockFactory.getCreatedVehicleCount() === 1);
    
    // 에러 케이스 테스트
    mockFactory.setShouldThrowError(true, "Test error");
    try {
        mockFactory.createVehicle("car", "Honda", "Civic");
        console.assert(false, "에러가 발생해야 합니다");
    } catch (error) {
        console.assert(error.message === "Test error");
    }
    
    console.log("모든 테스트 통과!");
}
```

### 5. 설정 관리

#### 5.1 환경별 설정 팩토리
```javascript
class ConfigurableVehicleFactory {
    constructor(config) {
        this.config = {
            enableCaching: true,
            cacheSize: 100,
            enableLogging: false,
            defaultBrand: "Unknown",
            defaultModel: "Default",
            ...config
        };
        
        this.cache = this.config.enableCaching ? new Map() : null;
    }
    
    createVehicle(type, brand, model) {
        const finalBrand = brand || this.config.defaultBrand;
        const finalModel = model || this.config.defaultModel;
        
        // 캐싱 확인
        if (this.cache) {
            const cacheKey = `${type}_${finalBrand}_${finalModel}`;
            if (this.cache.has(cacheKey)) {
                return this.cache.get(cacheKey);
            }
        }
        
        const vehicle = this.createVehicleInternal(type, finalBrand, finalModel);
        
        // 캐싱 저장
        if (this.cache && this.cache.size < this.config.cacheSize) {
            this.cache.set(cacheKey, vehicle);
        }
        
        return vehicle;
    }
    
    createVehicleInternal(type, brand, model) {
        switch (type.toLowerCase()) {
            case "car":
                return new Car(brand, model);
            case "motorcycle":
                return new Motorcycle(brand, model);
            case "bicycle":
                return new Bicycle(brand, model);
            default:
                throw new Error(`지원하지 않는 차량 타입: ${type}`);
        }
    }
    
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // 캐싱 설정 변경 시 캐시 초기화
        if (newConfig.enableCaching === false && this.cache) {
            this.cache.clear();
            this.cache = null;
        } else if (newConfig.enableCaching === true && !this.cache) {
            this.cache = new Map();
        }
    }
}
```

## 다른 디자인 패턴과의 관계

### 1. Abstract Factory 패턴과의 차이점

| Factory Method | Abstract Factory |
|---|---|
| 단일 제품군의 객체 생성 | 여러 관련 제품군의 객체 생성 |
| 상속을 통한 팩토리 구현 | 구성을 통한 팩토리 구현 |
| 런타임에 하나의 제품 타입 결정 | 런타임에 여러 제품 타입 조합 결정 |

```javascript
// Factory Method: 단일 제품군
class VehicleFactory {
    createVehicle() { /* 구현 */ }
}

// Abstract Factory: 여러 제품군
class VehicleAbstractFactory {
    createEngine() { /* 구현 */ }
    createWheel() { /* 구현 */ }
    createBody() { /* 구현 */ }
}
```

### 2. Builder 패턴과의 조합

Factory Method는 "무엇을" 생성할지 결정하고, Builder는 "어떻게" 생성할지 관리합니다.

```javascript
class VehicleBuilderFactory {
    static createBuilder(type) {
        switch (type) {
            case "car":
                return new CarBuilder();
            case "motorcycle":
                return new MotorcycleBuilder();
            default:
                throw new Error("지원하지 않는 타입");
        }
    }
}
```

### 3. Singleton 패턴과의 결합

팩토리 자체를 싱글톤으로 구현하여 전역에서 하나의 인스턴스만 사용합니다.

```javascript
class SingletonVehicleFactory {
    static instance = null;
    
    static getInstance() {
        if (!this.instance) {
            this.instance = new SingletonVehicleFactory();
        }
        return this.instance;
    }
    
    createVehicle(type, brand, model) {
        // 팩토리 로직
    }
}
```

## 실제 프로덕션 사용 사례

### 1. 프레임워크 및 라이브러리

#### React 컴포넌트 팩토리
```javascript
// React에서의 팩토리 패턴 활용
const ComponentFactory = {
    createButton: (props) => <Button {...props} />,
    createInput: (props) => <Input {...props} />,
    createModal: (props) => <Modal {...props} />
};
```

#### Express.js 미들웨어 팩토리
```javascript
class MiddlewareFactory {
    static createAuthMiddleware(type) {
        switch (type) {
            case "jwt":
                return jwtAuthMiddleware;
            case "session":
                return sessionAuthMiddleware;
            case "oauth":
                return oauthAuthMiddleware;
            default:
                throw new Error("지원하지 않는 인증 타입");
        }
    }
}
```

### 2. 데이터베이스 및 ORM

#### Sequelize 모델 팩토리
```javascript
class ModelFactory {
    static createModel(type, attributes) {
        switch (type) {
            case "user":
                return sequelize.define('User', {
                    name: DataTypes.STRING,
                    email: DataTypes.STRING,
                    ...attributes
                });
            case "product":
                return sequelize.define('Product', {
                    title: DataTypes.STRING,
                    price: DataTypes.DECIMAL,
                    ...attributes
                });
            default:
                throw new Error("지원하지 않는 모델 타입");
        }
    }
}
```

### 3. API 클라이언트 라이브러리

#### HTTP 클라이언트 팩토리
```javascript
class HttpClientFactory {
    static createClient(type, config) {
        switch (type) {
            case "axios":
                return new AxiosClient(config);
            case "fetch":
                return new FetchClient(config);
            case "xhr":
                return new XHRClient(config);
            default:
                throw new Error("지원하지 않는 HTTP 클라이언트 타입");
        }
    }
}
```

### 4. 게임 엔진

#### 게임 객체 팩토리
```javascript
class GameObjectFactory {
    static createEnemy(type, position) {
        switch (type) {
            case "zombie":
                return new Zombie(position);
            case "skeleton":
                return new Skeleton(position);
            case "dragon":
                return new Dragon(position);
            default:
                throw new Error("지원하지 않는 적 타입");
        }
    }
    
    static createWeapon(type, damage) {
        switch (type) {
            case "sword":
                return new Sword(damage);
            case "bow":
                return new Bow(damage);
            case "staff":
                return new Staff(damage);
            default:
                throw new Error("지원하지 않는 무기 타입");
        }
    }
}
```

## 성능 벤치마크 및 최적화

### 1. 성능 비교

```javascript
// 직접 생성 vs 팩토리 패턴 성능 테스트
function performanceTest() {
    const iterations = 100000;
    
    // 직접 생성
    console.time("Direct Creation");
    for (let i = 0; i < iterations; i++) {
        new Car("Toyota", "Camry");
    }
    console.timeEnd("Direct Creation");
    
    // 팩토리 패턴
    console.time("Factory Pattern");
    for (let i = 0; i < iterations; i++) {
        VehicleFactory.createVehicle("car", "Toyota", "Camry");
    }
    console.timeEnd("Factory Pattern");
}
```

### 2. 메모리 사용량 분석

```javascript
// 메모리 사용량 모니터링
function memoryUsageTest() {
    const initialMemory = process.memoryUsage();
    
    // 객체 생성
    const vehicles = [];
    for (let i = 0; i < 10000; i++) {
        vehicles.push(VehicleFactory.createVehicle("car", "Brand", "Model"));
    }
    
    const finalMemory = process.memoryUsage();
    console.log("메모리 사용량 증가:", {
        heapUsed: finalMemory.heapUsed - initialMemory.heapUsed,
        heapTotal: finalMemory.heapTotal - initialMemory.heapTotal
    });
}
```

### 3. 위 두 측정으로는 아무것도 판정할 수 없다

성능 비교 코드에는 문제가 셋 겹쳐 있다.

**결과를 아무 데도 쓰지 않는다.** `new Car(...)` 를 만들고 버리므로 최적화가 할당 자체를 들어낼 수 있다. 10만 회 반복이 밀리초 단위에서 끝나는데, 이 규모면 재려던 차이보다 잡음이 크다.

**한 프로세스에서 순서대로 잰다.** 앞 루프가 JIT 워밍업과 힙 상태를 남긴 채 뒤 루프가 돈다. 그래서 순서만 바꿔 돌리면 승자가 뒤집힌다. 같은 코드를 별도 프로세스에서 여섯 번 돌린 결과다.

```
direct-first : 직접 1.51 / 팩토리 1.17
factory-first: 직접 0.82 / 팩토리 1.67
direct-first : 직접 1.14 / 팩토리 1.17
factory-first: 직접 0.63 / 팩토리 1.32
direct-first : 직접 1.12 / 팩토리 1.05
factory-first: 직접 0.70 / 팩토리 1.37
        (단위 밀리초, 각 10만 회, node 단독 실행)
```

먼저 도는 쪽이 손해를 보고 있을 뿐이라는 게 보인다. 결과를 배열에 담아 버려지지 않게 하면 두 값 모두 몇 배로 커진다 — 원래 재려던 것은 생성 비용이 아니라 최적화기의 기분이었던 셈이다.

**GC 를 통제하지 않는다.** 메모리 테스트의 `process.memoryUsage()` 차이는 그 사이 수집이 돌았는지에 좌우된다. `--expose-gc` 로 앞뒤에 강제 수집을 넣지 않으면 증가량이 음수로 나오기도 한다.

측정을 하지 말라는 뜻이 아니라 **팩토리 도입 여부를 이런 미시 측정으로 정하지 말라는 뜻이다.** 함수 호출 하나와 `switch` 한 번이 병목인 코드는 드물다. 이 패턴의 실제 비용은 호출 오버헤드가 아니라 위에 적힌 "클래스 수 증가", 그리고 **`new` 가 코드에서 사라져 어떤 구현이 만들어졌는지 추적하기 어려워지는 것** 쪽이다. 스택 트레이스에 팩토리만 찍히고 정작 어떤 구체 타입인지는 디버거를 붙여야 아는 상황이 그 대가다.

## 마이그레이션 가이드

### 1. 기존 코드에서 팩토리 패턴 도입

#### Before (직접 생성)
```javascript
// 기존 코드
const car = new Car("Toyota", "Camry");
const motorcycle = new Motorcycle("Honda", "CBR");
const bicycle = new Bicycle("Giant", "Defy");
```

#### After (팩토리 패턴 적용)
```javascript
// 팩토리 패턴 적용
const car = VehicleFactory.createVehicle("car", "Toyota", "Camry");
const motorcycle = VehicleFactory.createVehicle("motorcycle", "Honda", "CBR");
const bicycle = VehicleFactory.createVehicle("bicycle", "Giant", "Defy");
```

### 2. 점진적 마이그레이션 전략

```javascript
// 1단계: 팩토리 클래스 추가 (기존 코드 유지)
class VehicleFactory {
    static createVehicle(type, brand, model) {
        // 새로운 팩토리 로직
    }
}

// 2단계: 새로운 코드에서만 팩토리 사용
// 3단계: 기존 코드를 점진적으로 팩토리로 교체
// 4단계: 직접 생성자 호출 제거
```

### 장점
- **유연성**: 새로운 객체 타입을 기존 코드 수정 없이 추가 가능
- **확장성**: 시스템의 확장이 용이하고 유지보수 비용 감소
- **테스트 용이성**: Mock 객체를 통한 단위 테스트 간소화
- **의존성 관리**: 클라이언트와 구체 클래스 간의 느슨한 결합

### 주의사항
- **복잡성 증가**: 단순한 객체 생성에는 과도한 추상화
- **성능 오버헤드**: 추가적인 추상화 계층으로 인한 약간의 성능 저하
- **학습 곡선**: 팀원들의 패턴 이해 필요

### 권장사항
1. **적절한 시점에 도입**: 객체 생성 로직이 복잡해지거나 확장이 예상될 때
2. **점진적 적용**: 기존 시스템에 점진적으로 도입하여 리스크 최소화
3. **성능 모니터링**: 도입 후 성능 영향 지속적 모니터링
4. **팀 교육**: 팀원들의 패턴 이해도 향상을 위한 교육 실시

Factory Method 패턴은 올바르게 사용될 때 코드의 품질과 유지보수성을 크게 향상시키는 강력한 도구입니다. 프로젝트의 요구사항과 팀의 상황을 고려하여 신중하게 도입하시기 바랍니다.

---

## 참고 자료

- **Design Patterns: Elements of Reusable Object-Oriented Software** - Gang of Four
- **Head First Design Patterns** - Eric Freeman, Elisabeth Robson
- **JavaScript Patterns** - Stoyan Stefanov
- **Effective Java** - Joshua Bloch (Java 관점에서의 팩토리 패턴)
- **Clean Code** - Robert C. Martin
- **Refactoring: Improving the Design of Existing Code** - Martin Fowler
- **JavaScript.info** - Factory Functions and Constructor Functions
- **MDN Web Docs** - Object-oriented JavaScript
- **React Documentation** - Component Composition Patterns
- **Node.js Best Practices** - Factory Pattern in Node.js Applications


