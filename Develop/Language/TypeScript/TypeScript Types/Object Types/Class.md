
# Class란?
- TypeScript에서 특정 속성과 메서드를 가진 객체를 생성하기 위한 청사진입니다.
- 클래스는 객체지향 프로그래밍의 기본 개념입니다.

# Class의 장점은?
- 객체지향 프로그래밍의 상속, 다형성, 캡슐화등의 개념을 지원하여 유지 보수 가능하고 재사용 가능한 코드를 작성하는데 도움이 됩니다.
- 또한, TypeScript는 클래스에 타입 주석을 추가하여 각 속성과 메서드의 타입을 명시할 수 있습니다.

# 기본 예시
    class Car {
        make: string;
        model: string;
        year: number;
    
        constructor(make: string, model: string, year: number) {
            this.make = make;
            this.model = model;
            this.year = year;
        }
    
        drive() {
            console.log(`Driving my ${this.year} ${this.make} ${this.model}`);
        }
    }

> 위의 코드에서 Car 클래스는 make, model, year라는 세 개의 속성을 가지고 있습니다. 이 속성들은 생성자(constructor)에서 전달된 인자로 초기화됩니다.

클래스에는 또한 'drive'라는 메서드가 있습니다. 이 메서드는 객체의 속성을 사용하여 메시지를 출력합니다.
- 클래스를 사용하여 객체를 생성할 수 있는데, 


    const myCar = new Car('Tesla', 'Model 3', 2021);
    myCar.drive(); // 출력: Driving my 2021 Tesla Model 3

> 위의 예시에는 'myCar'라는 객체를 'Car'클래스의 생성자를 통해 생성하고, 'drive' 메서드를 호출하여 메시지를 출력합니다.

