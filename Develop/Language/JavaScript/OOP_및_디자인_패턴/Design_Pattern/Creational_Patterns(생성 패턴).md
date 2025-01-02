
# JavaScript 생성 패턴 (Creational Patterns)

생성 패턴은 객체 생성과 관련된 문제를 해결하기 위한 설계 패턴입니다.  
효율적이고 유연하게 객체를 생성하고 관리할 수 있도록 다양한 방법을 제공합니다.

---

## 1. Singleton Pattern
### 개념
Singleton 패턴은 클래스의 인스턴스를 단 하나만 생성하고, 어디서든 해당 인스턴스에 접근할 수 있도록 보장하는 패턴입니다.

### 특징
- 글로벌 상태를 유지하고자 할 때 사용됩니다.
- 동일한 인스턴스를 여러 번 생성하지 않으므로 메모리를 절약할 수 있습니다.

### 예시 코드

```javascript
const Singleton = (function () {
  let instance;

  function createInstance() {
    return { message: "This is the singleton instance" };
  }

  return {
    getInstance: function () {
      if (!instance) {
        instance = createInstance();
      }
      return instance;
    }
  };
})();

const instance1 = Singleton.getInstance();
const instance2 = Singleton.getInstance();

console.log(instance1 === instance2); // true
```

---

## 2. Factory Pattern
### 개념
Factory 패턴은 객체 생성 로직을 별도의 메서드로 캡슐화하여 객체 생성 과정을 단순화하는 패턴입니다.

### 특징
- 객체 생성 코드를 반복하지 않고 재사용할 수 있습니다.
- 객체 생성 시점에 반환할 객체의 타입을 동적으로 결정할 수 있습니다.

### 예시 코드

```javascript
class Animal {
  constructor(name) {
    this.name = name;
  }
}

class AnimalFactory {
  static createAnimal(type, name) {
    switch (type) {
      case "dog":
        return new Animal(`Dog: ${name}`);
      case "cat":
        return new Animal(`Cat: ${name}`);
      default:
        return new Animal(`Unknown: ${name}`);
    }
  }
}

const dog = AnimalFactory.createAnimal("dog", "Buddy");
const cat = AnimalFactory.createAnimal("cat", "Kitty");

console.log(dog.name); // "Dog: Buddy"
console.log(cat.name); // "Cat: Kitty"
```

---

## 3. Builder Pattern
### 개념
Builder 패턴은 복잡한 객체를 단계적으로 생성할 수 있도록 돕는 패턴입니다.  
객체 생성의 과정과 표현을 분리하여 다양한 객체를 동일한 생성 코드로 만들 수 있습니다.

### 특징
- 복잡한 객체를 효율적으로 생성할 수 있습니다.
- 가독성과 유연성을 높여줍니다.

### 예시 코드

```javascript
class Car {
  constructor() {
    this.make = "";
    this.model = "";
    this.year = "";
  }
}

class CarBuilder {
  constructor() {
    this.car = new Car();
  }

  setMake(make) {
    this.car.make = make;
    return this;
  }

  setModel(model) {
    this.car.model = model;
    return this;
  }

  setYear(year) {
    this.car.year = year;
    return this;
  }

  build() {
    return this.car;
  }
}

const car = new CarBuilder()
  .setMake("Toyota")
  .setModel("Corolla")
  .setYear("2023")
  .build();

console.log(car); // { make: 'Toyota', model: 'Corolla', year: '2023' }
```

---

## 4. Prototype Pattern
### 개념
Prototype 패턴은 기존 객체를 복사하여 새로운 객체를 생성하는 패턴입니다.

### 특징
- 새로운 객체를 생성할 때 초기화 비용을 줄일 수 있습니다.
- 객체의 구조와 데이터를 복제할 때 유용합니다.

### 예시 코드

```javascript
const carPrototype = {
  make: "Default",
  model: "Default",
  displayInfo: function () {
    return `${this.make} ${this.model}`;
  }
};

const car1 = Object.create(carPrototype);
car1.make = "Tesla";
car1.model = "Model 3";

const car2 = Object.create(carPrototype);
car2.make = "Ford";
car2.model = "Mustang";

console.log(car1.displayInfo()); // "Tesla Model 3"
console.log(car2.displayInfo()); // "Ford Mustang"
```

---

## 요약
| 패턴       | 주요 특징                                                              |
|------------|------------------------------------------------------------------------|
| Singleton  | 단 하나의 인스턴스만 생성. 전역 상태 관리에 유용.                       |
| Factory    | 객체 생성 로직을 캡슐화. 생성 과정과 타입 선택을 동적으로 처리.          |
| Builder    | 복잡한 객체를 단계적으로 생성. 생성 과정과 표현 분리.                   |
| Prototype  | 기존 객체를 복사하여 새로운 객체를 생성. 초기화 비용 절감.              |

JavaScript에서 생성 패턴을 적절히 활용하면 더 효율적이고 유지보수성이 높은 코드를 작성할 수 있습니다.
