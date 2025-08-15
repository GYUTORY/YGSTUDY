---
title: Factory Method(팩토리 메서드) 패턴 개념과 예제
tags: [design-pattern, factory-method, creational-pattern, javascript, architecture]
updated: 2024-12-19
---

# Factory Method(팩토리 메서드) 패턴 개념과 예제

## 배경

### 팩토리 메서드 패턴의 필요성
팩토리 메서드 패턴은 객체 생성의 복잡성을 캡슐화하고, 클라이언트 코드가 구체적인 클래스에 의존하지 않도록 하는 디자인 패턴입니다. 객체 생성 로직을 별도로 분리하여 코드의 유지보수성과 확장성을 향상시킵니다.

### 기본 개념
- **객체 생성 캡슐화**: 객체 생성 과정을 팩토리 메서드에 위임
- **의존성 분리**: 클라이언트가 구체적인 클래스에 직접 의존하지 않음
- **확장성**: 새로운 객체 타입을 기존 코드 변경 없이 추가 가능
- **유연성**: 런타임에 객체 타입을 결정할 수 있음

## 핵심

### 1. 팩토리 메서드 패턴의 구조

#### 기본 구성 요소
1. **추상 생성자 (Creator)**: 팩토리 메서드를 정의하는 추상 클래스/인터페이스
2. **구체 생성자 (Concrete Creator)**: 실제 객체를 생성하는 팩토리 메서드 구현
3. **추상 제품 (Product)**: 생성될 객체의 인터페이스 정의
4. **구체 제품 (Concrete Product)**: 실제 생성될 객체 클래스

#### 패턴의 장점
- **객체 생성 로직 캡슐화**: 클라이언트는 객체 생성 방식을 알 필요 없음
- **유지보수성 향상**: 새로운 제품 타입 추가 시 기존 코드 변경 최소화
- **의존성 감소**: 클라이언트가 구체적인 클래스에 강하게 결합되지 않음
- **확장성**: 새로운 제품 타입을 쉽게 추가 가능

#### 패턴의 단점
- **클래스 수 증가**: 팩토리 클래스와 서브클래스가 많아질 수 있음
- **복잡성 증가**: 단순한 객체 생성에는 과도한 복잡성 초래 가능
- **추상화 오버헤드**: 작은 프로젝트에서는 불필요한 추상화

### 2. 기본 팩토리 메서드 패턴 구현

```javascript
// 추상 제품 클래스
class Vehicle {
    constructor() {
        if (new.target === Vehicle) {
            throw new Error("Vehicle 클래스는 직접 인스턴스를 생성할 수 없습니다.");
        }
    }

    drive() {
        throw new Error("drive() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 구체적인 제품 클래스들
class Car extends Vehicle {
    drive() {
        return "자동차를 운전합니다.";
    }
}

class Motorcycle extends Vehicle {
    drive() {
        return "오토바이를 운전합니다.";
    }
}

class Bicycle extends Vehicle {
    drive() {
        return "자전거를 탑니다.";
    }
}

// 추상 생성자 클래스
class VehicleFactory {
    createVehicle() {
        throw new Error("createVehicle() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 구체적인 생성자 클래스들
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

class BicycleFactory extends VehicleFactory {
    createVehicle() {
        return new Bicycle();
    }
}

// 클라이언트 코드
function useVehicle(factory) {
    const vehicle = factory.createVehicle();
    console.log(vehicle.drive());
}

// 사용 예시
useVehicle(new CarFactory());      // 자동차를 운전합니다.
useVehicle(new MotorcycleFactory()); // 오토바이를 운전합니다.
useVehicle(new BicycleFactory());    // 자전거를 탑니다.
```

## 예시

### 1. 실제 사용 사례

#### 데이터베이스 연결 팩토리
```javascript
// 추상 데이터베이스 연결 클래스
class DatabaseConnection {
    constructor() {
        if (new.target === DatabaseConnection) {
            throw new Error("DatabaseConnection 클래스는 직접 인스턴스를 생성할 수 없습니다.");
        }
    }

    connect() {
        throw new Error("connect() 메서드는 서브클래스에서 구현해야 합니다.");
    }
    
    disconnect() {
        throw new Error("disconnect() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 구체적인 데이터베이스 연결 클래스들
class MySQLConnection extends DatabaseConnection {
    constructor(config) {
        super();
        this.config = config;
    }
    
    connect() {
        return `MySQL 연결: ${this.config.host}:${this.config.port}`;
    }
    
    disconnect() {
        return "MySQL 연결 해제";
    }
}

class PostgreSQLConnection extends DatabaseConnection {
    constructor(config) {
        super();
        this.config = config;
    }
    
    connect() {
        return `PostgreSQL 연결: ${this.config.host}:${this.config.port}`;
    }
    
    disconnect() {
        return "PostgreSQL 연결 해제";
    }
}

// 데이터베이스 팩토리 클래스
class DatabaseFactory {
    static createConnection(type, config) {
        switch (type) {
            case "mysql":
                return new MySQLConnection(config);
            case "postgresql":
                return new PostgreSQLConnection(config);
            default:
                throw new Error("지원하지 않는 데이터베이스 타입입니다.");
        }
    }
}

// 사용 예시
const mysqlConfig = { host: "localhost", port: 3306 };
const postgresConfig = { host: "localhost", port: 5432 };

const mysqlConnection = DatabaseFactory.createConnection("mysql", mysqlConfig);
const postgresConnection = DatabaseFactory.createConnection("postgresql", postgresConfig);

console.log(mysqlConnection.connect());     // MySQL 연결: localhost:3306
console.log(postgresConnection.connect());  // PostgreSQL 연결: localhost:5432
```

#### UI 컴포넌트 팩토리
```javascript
// 추상 UI 컴포넌트 클래스
class UIComponent {
    constructor() {
        if (new.target === UIComponent) {
            throw new Error("UIComponent 클래스는 직접 인스턴스를 생성할 수 없습니다.");
        }
    }

    render() {
        throw new Error("render() 메서드는 서브클래스에서 구현해야 합니다.");
    }
}

// 구체적인 UI 컴포넌트 클래스들
class Button extends UIComponent {
    constructor(text, onClick) {
        super();
        this.text = text;
        this.onClick = onClick;
    }
    
    render() {
        return `<button onclick="${this.onClick}">${this.text}</button>`;
    }
}

class InputField extends UIComponent {
    constructor(placeholder, type = "text") {
        super();
        this.placeholder = placeholder;
        this.type = type;
    }
    
    render() {
        return `<input type="${this.type}" placeholder="${this.placeholder}">`;
    }
}

// UI 컴포넌트 팩토리
class UIComponentFactory {
    static createComponent(type, config) {
        switch (type) {
            case "button":
                return new Button(config.text, config.onClick);
            case "input":
                return new InputField(config.placeholder, config.type);
            default:
                throw new Error("지원하지 않는 컴포넌트 타입입니다.");
        }
    }
}

// 사용 예시
const buttonConfig = { text: "클릭하세요", onClick: "handleClick()" };
const inputConfig = { placeholder: "이름을 입력하세요", type: "text" };

const button = UIComponentFactory.createComponent("button", buttonConfig);
const input = UIComponentFactory.createComponent("input", inputConfig);

console.log(button.render()); // <button onclick="handleClick()">클릭하세요</button>
console.log(input.render());  // <input type="text" placeholder="이름을 입력하세요">
```

### 2. 고급 패턴

#### 설정 기반 팩토리
```javascript
class ConfigBasedFactory {
    static createFromConfig(config) {
        const { type, ...params } = config;
        
        switch (type) {
            case "car":
                return new Car(params);
            case "motorcycle":
                return new Motorcycle(params);
            case "bicycle":
                return new Bicycle(params);
            default:
                throw new Error(`알 수 없는 타입: ${type}`);
        }
    }
}

// 설정 파일 예시
const vehicleConfigs = [
    { type: "car", brand: "Toyota", model: "Camry" },
    { type: "motorcycle", brand: "Honda", model: "CBR" },
    { type: "bicycle", brand: "Giant", model: "Defy" }
];

// 설정 기반 객체 생성
const vehicles = vehicleConfigs.map(config => 
    ConfigBasedFactory.createFromConfig(config)
);
```

#### 캐싱 팩토리
```javascript
class CachedFactory {
    static cache = new Map();
    
    static createVehicle(type) {
        if (this.cache.has(type)) {
            return this.cache.get(type);
        }
        
        const vehicle = VehicleFactory.createVehicle(type);
        this.cache.set(type, vehicle);
        return vehicle;
    }
    
    static clearCache() {
        this.cache.clear();
    }
}
```

## 운영 팁

### 1. 성능 최적화
- **객체 풀링**: 자주 생성되는 객체의 재사용
- **캐싱 전략**: 동일한 설정의 객체 캐싱
- **지연 초기화**: 필요할 때만 객체 생성

### 2. 에러 처리
```javascript
class SafeFactory {
    static createVehicle(type) {
        try {
            return VehicleFactory.createVehicle(type);
        } catch (error) {
            console.error(`객체 생성 실패: ${error.message}`);
            return new DefaultVehicle(); // 기본 객체 반환
        }
    }
}
```

### 3. 로깅과 모니터링
```javascript
class LoggedFactory {
    static createVehicle(type) {
        console.log(`객체 생성 시작: ${type}`);
        const startTime = Date.now();
        
        const vehicle = VehicleFactory.createVehicle(type);
        
        const endTime = Date.now();
        console.log(`객체 생성 완료: ${type}, 소요시간: ${endTime - startTime}ms`);
        
        return vehicle;
    }
}
```

### 4. 테스트 용이성
- **Mock 객체**: 테스트용 가짜 객체 생성
- **의존성 주입**: 테스트 시 실제 객체 대신 Mock 사용
- **단위 테스트**: 각 팩토리 메서드별 독립적 테스트

## 참고

### 다른 패턴과의 관계
- **Abstract Factory**: 여러 관련 객체들을 생성하는 팩토리 패턴
- **Builder**: 복잡한 객체 생성 과정을 단계별로 분리
- **Singleton**: 팩토리 자체를 싱글톤으로 구현하여 전역 접근
- **Strategy**: 객체 생성 전략을 동적으로 변경

### 실제 사용 사례
1. **프레임워크 라이브러리**: React, Vue 등의 컴포넌트 생성
2. **데이터베이스 연결**: 다양한 DB 드라이버 생성
3. **UI 라이브러리**: 버튼, 입력 필드 등 UI 컴포넌트 생성
4. **API 클라이언트**: 다양한 서비스별 API 클라이언트 생성
5. **게임 엔진**: 다양한 게임 객체 생성

### 결론
팩토리 메서드 패턴은 객체 생성의 복잡성을 캡슐화하고, 클라이언트 코드의 의존성을 줄이는 효과적인 디자인 패턴입니다. 적절한 상황에서 사용하면 코드의 유지보수성과 확장성을 크게 향상시킬 수 있지만, 단순한 객체 생성에는 과도한 복잡성을 가져올 수 있으므로 사용 시점을 신중히 고려해야 합니다.


