
# 인터페이스란?
- TypeScript에서 객체의 타입을 정의하는 역할을 합니다.
- 인터페이스는 객체의 구조를 명시적으로 선언하여 해당 구조에 맞는 속성과 메서드를 가지도록 지정할 수 있습니다.
- 이를 통해 객체의 타입을 추상화하고, 코드의 가독성과 유지 보수성을 높일 수 있습니다.

# 사용법
    interface Person {
        name: string;
        age: number;
    }
> 인터페이스는 'interface' 키워드를 사용하여 정의합니다.
> 아래는 'Person' 인터페이스의 예시입니다.
    
    function greet(person: Person) {
        return 'Hello ' + person.name;
    }

> 위 예시에서 'Person' 인터페이스는 'name'과 'age'라는 두 개의 속성을 가지고 있습니다.
- 'name'은 문자열 타입이고, 'age'는 숫자 타입입니다.
- 인터페이스를 사용하여 함수의 매개변수나 리턴 타입으로 객체의 타입을 지정할 수 있습니다.
- 예를 들어, 'greet' 함수는 'Person' 인터페이스를 매개변수로 받으며, 'person.name' 을 이용하여 인사말을 생성합니다.

# 좀 더 고도화를 한다면?
    // 인터페이스 선언: User 인터페이스
    interface User {
        id: number;
        name: string;
        email: string;
        age?: number; // 선택적 속성
        greet: () => void; // 메서드 선언
    }
    
    // User 인터페이스를 구현하는 User 클래스
    class UserImpl implements User {
        id: number;
        name: string;
        email: string;
    
        constructor(id: number, name: string, email: string) {
            this.id = id;
            this.name = name;
            this.email = email;
        }
    
        greet() {
            console.log(`Hello, ${this.name}!`);
        }
    }
    
    // User 객체 생성
    const user1: User = new UserImpl(1, 'John Doe', 'john@example.com');
    user1.greet(); // 출력: Hello, John Doe!
    
    // User 객체 배열
    const users: User[] = [
    user1,
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', greet: () => console.log('Hi!') }
    ];
    
    // users 배열 순회 및 출력
    users.forEach((user: User) => {
        console.log(`ID: ${user.id}`);
        console.log(`Name: ${user.name}`);
        console.log(`Email: ${user.email}`);
    
        if (user.age) {
            console.log(`Age: ${user.age}`);
        }
        user.greet();
        console.log('-------------');
    });


