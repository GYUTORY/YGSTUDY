
# Observer_Pattern Pattern


<div align="center">
    <img src="../../../etc/image/Application Architecture/Design Pattern/Observer Pattern.png" alt="Observer_Pattern" width="50%">
</div>


## 개요
- 옵저버 패턴은 객체의 상태 변화를 관찰하는 관찰자들, 즉 옵저버들의 목록을 객체에 등록하여 상태 변화가 있을 때마다 메서드 등을 통해 객체가 직접 목록의 각 옵저버에게 통지하도록 하는 디자인 패턴이다.
- 쉽게 말해 어떤 객체의 상태가 변할 때 그와 연관된 객체들에게 알림을 보내는 패턴이다.

## 내용
- Observer Pattern은 소프트웨어 개발에서 종종 발생하는 "이벤트 처리" 문제를 해결하기 위해 등장하였습니다. 
- 예를 들어, GUI 애플리케이션에서는 사용자 인터페이스 요소들 간에 서로 상호작용이 필요하며, 한 요소의 상태 변경이 다른 요소에 영향을 주는 경우가 많습니다. 
- 이때 Observer_Pattern Pattern은 각 요소들을 독립적으로 유지하면서 상호작용을 가능하게 해줍니다.

--- 

## Observer_Pattern Pattern 구조 

<div align="center">
    <img src="../../../etc/image/Application Architecture/Design Pattern/Observer_Structure.png" alt="Obeserver Structure" width="30%">
</div>


**1. Subject**
- Observer_Pattern 목록을 유지하고 Observer_Pattern 추가 또는 제거를 용이하게 하는 역할

**2. ConcreteSubject**
- 상태 변경에 대한 알림을 Observer에게 제공하고, concreteObserver의 상태를 저장하는 역할

**3. Observer_Pattern**
- Subject의 상태 변경을 통지해야 하는 객체에 대한 업데이트 인터페이스를 제공하는 역할

**4. ConcreteObserver**
- concreteSubject에 대한 참조를 저장하고, Observer에 대한 업데이트 인터페이스를 구현하여 상태가 Subject와 일치하는지 확인하는 역할

---

## Js로 알아보는 사용예제

```javascript
// Subject 클래스 정의
class Subject {
    constructor() {
        this.observers = []; // 옵저버(구독자) 리스트 초기화
    }

    // 옵저버 등록 메소드
    addObserver(observer) {
        this.observers.push(observer);
    }

    // 옵저버 제거 메소드
    removeObserver(observer) {
        this.observers = this.observers.filter(obs => obs !== observer);
    }

    // 모든 옵저버에게 알림을 보내는 메소드
    notifyObservers() {
        this.observers.forEach(observer => observer.update());
    }
}

// Observer_Pattern 클래스 정의
class Observer_Pattern {
    constructor(name) {
        this.name = name;
    }

    // 업데이트 메소드 (옵저버가 알림을 받을 때 호출되는 메소드)
    update() {
        console.log(`${this.name}가 알림을 받았습니다.`);
    }
}

// 예제 사용

// Subject 인스턴스 생성
const subject = new Subject();

// Observer_Pattern 인스턴스 생성
const observer1 = new Observer_Pattern('옵저버 1');
const observer2 = new Observer_Pattern('옵저버 2');

// 옵저버 등록
subject.addObserver(observer1);
subject.addObserver(observer2);

// 상태 변화 발생 및 알림
console.log('모든 옵저버에게 알림을 보냅니다.');
subject.notifyObservers(); // 모든 옵저버의 update 메소드가 호출됩니다.

// 옵저버 제거 후 알림
subject.removeObserver(observer1);
console.log('옵저버 1을 제거한 후, 남은 옵저버에게 알림을 보냅니다.');
subject.notifyObservers(); // 옵저버 1은 알림을 받지 않습니다.


```

## 설명 

### 1. Subject 클래스
- this.observers는 옵저버들을 저장하는 배열입니다.
- addObserver(observer) 메소드는 옵저버를 배열에 추가합니다.
- removeObserver(observer) 메소드는 배열에서 옵저버를 제거합니다.
- notifyObservers() 메소드는 배열에 있는 모든 옵저버의 update() 메소드를 호출하여 알림을 보냅니다.

### 2. Observer_Pattern 클래스:
- name은 옵저버의 이름을 저장하는 속성입니다.
- update() 메소드는 옵저버가 알림을 받을 때 실행됩니다. 여기서는 단순히 콘솔에 메시지를 출력합니다.


---

> [출처] [디자인 패턴] Observer_Pattern Pattern|작성자 공부쟁이