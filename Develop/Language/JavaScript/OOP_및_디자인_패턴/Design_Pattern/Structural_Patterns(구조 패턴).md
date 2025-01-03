
# JavaScript 구조 패턴 (Structural Patterns)

구조 패턴은 클래스나 객체의 구조를 조합하는 방법을 다루는 설계 패턴입니다.  
복잡한 시스템에서 구성 요소를 효율적으로 결합하고 유지 관리하기 위해 사용됩니다.

---

## 1. Adapter Pattern
### 개념
Adapter 패턴은 기존 클래스나 객체의 인터페이스를 다른 인터페이스로 변환하여 호환성을 제공하는 패턴입니다.

### 특징
- 호환되지 않는 인터페이스 간의 문제를 해결합니다.
- 기존 코드를 수정하지 않고도 사용할 수 있습니다.

### 예시 코드

```javascript
class OldSystem {
  getData() {
    return "Old Data Format";
  }
}

class NewSystem {
  fetchData() {
    return "New Data Format";
  }
}

class Adapter {
  constructor(oldSystem) {
    this.oldSystem = oldSystem;
  }

  fetchData() {
    return this.oldSystem.getData();
  }
}

const oldSystem = new OldSystem();
const adapter = new Adapter(oldSystem);

console.log(adapter.fetchData()); // "Old Data Format"
```

---

## 2. Bridge Pattern
### 개념
Bridge 패턴은 구현과 추상화를 분리하여 둘을 독립적으로 확장할 수 있도록 하는 패턴입니다.

### 특징
- 다양한 구현체를 동일한 인터페이스로 사용할 수 있습니다.
- 계층 구조를 단순화합니다.

### 예시 코드

```javascript
class Device {
  turnOn() {}
  turnOff() {}
}

class TV extends Device {
  turnOn() {
    console.log("TV가 켜졌습니다.");
  }
  turnOff() {
    console.log("TV가 꺼졌습니다.");
  }
}

class Remote {
  constructor(device) {
    this.device = device;
  }

  power() {
    console.log("리모컨으로 전원을 조작합니다.");
    this.device.turnOn();
    this.device.turnOff();
  }
}

const tv = new TV();
const remote = new Remote(tv);

remote.power();
// 리모컨으로 전원을 조작합니다.
// TV가 켜졌습니다.
// TV가 꺼졌습니다.
```

---

## 3. Composite Pattern
### 개념
Composite 패턴은 객체를 트리 구조로 구성하여 단일 객체와 복합 객체를 동일하게 다룰 수 있도록 하는 패턴입니다.

### 특징
- 개별 객체와 객체 그룹을 동일한 방식으로 처리합니다.
- 계층 구조를 쉽게 관리할 수 있습니다.

### 예시 코드

```javascript
class Component {
  operation() {}
}

class Leaf extends Component {
  operation() {
    console.log("Leaf의 작업 수행");
  }
}

class Composite extends Component {
  constructor() {
    super();
    this.children = [];
  }

  add(component) {
    this.children.push(component);
  }

  operation() {
    this.children.forEach(child => child.operation());
  }
}

const leaf1 = new Leaf();
const leaf2 = new Leaf();
const composite = new Composite();

composite.add(leaf1);
composite.add(leaf2);
composite.operation();
// Leaf의 작업 수행
// Leaf의 작업 수행
```

---

## 4. Decorator Pattern
### 개념
Decorator 패턴은 객체에 동적으로 기능을 추가할 수 있도록 하는 패턴입니다.

### 특징
- 기존 객체를 수정하지 않고 새로운 기능을 추가할 수 있습니다.
- 다수의 데코레이터를 사용하여 유연한 설계가 가능합니다.

### 예시 코드

```javascript
class Coffee {
  cost() {
    return 5;
  }
}

class MilkDecorator {
  constructor(coffee) {
    this.coffee = coffee;
  }

  cost() {
    return this.coffee.cost() + 2;
  }
}

class SugarDecorator {
  constructor(coffee) {
    this.coffee = coffee;
  }

  cost() {
    return this.coffee.cost() + 1;
  }
}

let coffee = new Coffee();
coffee = new MilkDecorator(coffee);
coffee = new SugarDecorator(coffee);

console.log(coffee.cost()); // 8
```

---

## 5. Facade Pattern
### 개념
Facade 패턴은 복잡한 시스템의 하위 인터페이스를 단순화하여 단일 인터페이스로 제공하는 패턴입니다.

### 특징
- 복잡한 시스템을 숨기고 간단한 API를 제공합니다.
- 코드의 가독성과 사용성을 높입니다.

### 예시 코드

```javascript
class SubSystem1 {
  operation() {
    return "Subsystem1 작업 수행";
  }
}

class SubSystem2 {
  operation() {
    return "Subsystem2 작업 수행";
  }
}

class Facade {
  constructor() {
    this.subsystem1 = new SubSystem1();
    this.subsystem2 = new SubSystem2();
  }

  operation() {
    return `${this.subsystem1.operation()} + ${this.subsystem2.operation()}`;
  }
}

const facade = new Facade();
console.log(facade.operation()); // "Subsystem1 작업 수행 + Subsystem2 작업 수행"
```

---

## 요약
| 패턴      | 주요 특징                                                             |
|-----------|---------------------------------------------------------------------|
| Adapter   | 호환되지 않는 인터페이스를 변환. 기존 코드 수정 없이 사용 가능.         |
| Bridge    | 구현과 추상화를 분리하여 독립적으로 확장 가능.                        |
| Composite | 단일 객체와 복합 객체를 동일하게 처리. 계층 구조 관리에 유용.          |
| Decorator | 기존 객체를 수정하지 않고 동적으로 기능 추가.                         |
| Facade    | 복잡한 시스템을 단순화하여 단일 인터페이스 제공.                      |

JavaScript에서 구조 패턴을 적절히 활용하면 복잡한 시스템을 더 효율적으로 관리하고 유지보수할 수 있습니다.
