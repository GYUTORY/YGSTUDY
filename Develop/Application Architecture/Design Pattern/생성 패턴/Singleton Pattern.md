
# 싱글톤 패턴
- 단 하나의 인스턴스만을 생성하고, 이에 대한 전역적인 접근을 제공하는 패턴입니다. 
- 이를 구현하기 위해 클래스 내부에서 자체적으로 인스턴스를 생성하고, 외부에서는 해당 인스턴스에 접근할 수 있는 정적 메서드를 제공합니다.

```typescript
class Singleton {
    // 클래스 내부에서 유일한 인스턴스를 저장하기 위한 정적 멤버 변수입니다. 외부에서 접근할 수 없도록 private로 선언되었습니다.
    private static instance: Singleton;

    // 외부에서의 인스턴스화를 막기 위해 생성자를 private로 선언했습니다.
    private constructor() {
        // ...
    }

    // 인스턴스에 접근하기 위한 정적 메서드입니다. 해당 메서드에서는 인스턴스가 존재하지 않을 경우에만 인스턴스를 생성하고 반환합니다.
    public static getInstance(): Singleton {
        if (!Singleton.instance) {
            // 인스턴스가 존재하지 않을 경우에만 인스턴스를 생성합니다.
            Singleton.instance = new Singleton();
        }
        return Singleton.instance;
    }

    // 싱글톤 객체의 메서드입니다.
    public someMethod(): void {
        console.log("Singleton method called.");
    }
}

// 인스턴스 생성
const instance1 = Singleton.getInstance();
const instance2 = Singleton.getInstance();

// 두 개의 변수 instance1과 instance2를 비교하여 동일한 인스턴스를 참조하는지 확인합니다.
console.log(instance1 === instance2); // true (동일한 인스턴스)

// 싱글톤 객체의 메서드를 호출합니다.
instance1.someMethod(); // "Singleton method called."
```
