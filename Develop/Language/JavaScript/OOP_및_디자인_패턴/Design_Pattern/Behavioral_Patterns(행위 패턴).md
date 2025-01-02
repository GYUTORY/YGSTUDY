
# JavaScript 행위 패턴 (Behavioral Patterns)

행위 패턴(Behavioral Patterns)은 객체 간의 상호작용과 책임 분배를 다루는 디자인 패턴입니다.
이 패턴들은 객체 간의 효율적인 통신과 행동의 캡슐화를 돕습니다.

## 주요 행위 패턴과 설명

### 1. Observer (옵저버 패턴)
옵저버 패턴은 객체의 상태 변화를 관찰하고, 변화가 발생하면 관련된 객체들에게 이를 통보하는 패턴입니다. 주로 이벤트 시스템에서 사용됩니다.

#### 예시 코드:

```javascript
class Subject {
  constructor() {
    this.observers = [];
  }
  attach(observer) {
    this.observers.push(observer);
  }
  detach(observer) {
    this.observers = this.observers.filter(obs => obs !== observer);
  }
  notify(data) {
    this.observers.forEach(observer => observer.update(data));
  }
}

class Observer {
  update(data) {
    console.log("Observer received data:", data);
  }
}

// 사용 예:
const subject = new Subject();
const observer1 = new Observer();
const observer2 = new Observer();

subject.attach(observer1);
subject.attach(observer2);

subject.notify("Hello Observers!"); // 두 옵저버가 메시지를 받음
```

---

### 2. Strategy (전략 패턴)
전략 패턴은 동작(알고리즘)을 정의하고 이를 캡슐화하여 런타임에 동적으로 교체할 수 있게 하는 패턴입니다.

#### 예시 코드:

```javascript
class StrategyA {
  execute() {
    console.log("Strategy A executed.");
  }
}

class StrategyB {
  execute() {
    console.log("Strategy B executed.");
  }
}

class Context {
  setStrategy(strategy) {
    this.strategy = strategy;
  }
  executeStrategy() {
    this.strategy.execute();
  }
}

// 사용 예:
const context = new Context();

context.setStrategy(new StrategyA());
context.executeStrategy(); // Strategy A executed.

context.setStrategy(new StrategyB());
context.executeStrategy(); // Strategy B executed.
```

---

### 3. Command (커맨드 패턴)
커맨드 패턴은 요청을 캡슐화하여 실행할 객체와 요청을 분리하는 패턴입니다. 주로 요청의 기록, 취소 및 재실행 기능을 구현할 때 사용됩니다.

#### 예시 코드:

```javascript
class Command {
  execute() {}
}

class LightOnCommand extends Command {
  constructor(light) {
    super();
    this.light = light;
  }
  execute() {
    this.light.on();
  }
}

class LightOffCommand extends Command {
  constructor(light) {
    super();
    this.light = light;
  }
  execute() {
    this.light.off();
  }
}

class Light {
  on() {
    console.log("Light is ON");
  }
  off() {
    console.log("Light is OFF");
  }
}

// 사용 예:
const light = new Light();
const lightOnCommand = new LightOnCommand(light);
const lightOffCommand = new LightOffCommand(light);

lightOnCommand.execute(); // Light is ON
lightOffCommand.execute(); // Light is OFF
```

---

### 4. State (상태 패턴)
상태 패턴은 객체의 상태에 따라 행동이 달라지는 경우, 상태를 객체로 분리하여 관리하는 패턴입니다.

#### 예시 코드:

```javascript
class Context {
  setState(state) {
    this.state = state;
  }
  request() {
    this.state.handle();
  }
}

class StateA {
  handle() {
    console.log("Handling State A");
  }
}

class StateB {
  handle() {
    console.log("Handling State B");
  }
}

// 사용 예:
const context = new Context();

const stateA = new StateA();
const stateB = new StateB();

context.setState(stateA);
context.request(); // Handling State A

context.setState(stateB);
context.request(); // Handling State B
```

---

## 요약
- **Observer**: 객체의 상태를 관찰하고 변경을 통보.
- **Strategy**: 알고리즘을 캡슐화하여 교체 가능.
- **Command**: 요청을 캡슐화하여 실행, 기록, 취소 가능.
- **State**: 상태에 따라 객체의 행동을 변경.

행위 패턴은 코드의 유연성과 확장성을 높이는 데 유용합니다.
