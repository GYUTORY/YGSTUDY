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
