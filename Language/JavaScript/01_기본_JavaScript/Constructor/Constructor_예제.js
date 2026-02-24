// 1. 기본적인 생성자 함수
console.log('1. 기본적인 생성자 함수');

function Person(name, age) {
    this.name = name;
    this.age = age;
    this.sayHello = function() {
        console.log(`안녕하세요! 저는 ${this.name}이고, ${this.age}살입니다.`);
    };
}

const person1 = new Person('김철수', 25);
const person2 = new Person('이영희', 30);

person1.sayHello(); // 출력: 안녕하세요! 저는 김철수이고, 25살입니다.
person2.sayHello(); // 출력: 안녕하세요! 저는 이영희이고, 30살입니다.

// 2. 프로토타입을 사용한 메서드 정의
console.log('\n2. 프로토타입을 사용한 메서드 정의');

function Animal(name, species) {
    this.name = name;
    this.species = species;
}

Animal.prototype.makeSound = function() {
    console.log(`${this.name}이(가) 소리를 냅니다.`);
};

const dog = new Animal('멍멍이', '개');
const cat = new Animal('야옹이', '고양이');

dog.makeSound(); // 출력: 멍멍이이(가) 소리를 냅니다.
cat.makeSound(); // 출력: 야옹이이(가) 소리를 냅니다.

// 3. private 속성 구현
console.log('\n3. private 속성 구현');

function BankAccount(initialBalance) {
    let balance = initialBalance; // private 변수

    this.getBalance = function() {
        return balance;
    };

    this.deposit = function(amount) {
        if (amount > 0) {
            balance += amount;
            return true;
        }
        return false;
    };

    this.withdraw = function(amount) {
        if (amount > 0 && balance >= amount) {
            balance -= amount;
            return true;
        }
        return false;
    };
}

const account = new BankAccount(1000);
console.log(account.getBalance()); // 출력: 1000
account.deposit(500);
console.log(account.getBalance()); // 출력: 1500
account.withdraw(200);
console.log(account.getBalance()); // 출력: 1300
console.log(account.balance); // 출력: undefined (private)

// 4. 생성자 함수 상속
console.log('\n4. 생성자 함수 상속');

function Vehicle(brand, year) {
    this.brand = brand;
    this.year = year;
}

Vehicle.prototype.getInfo = function() {
    return `${this.year}년식 ${this.brand}`;
};

function Car(brand, year, doors) {
    Vehicle.call(this, brand, year);
    this.doors = doors;
}

Car.prototype = Object.create(Vehicle.prototype);
Car.prototype.constructor = Car;

Car.prototype.getDoors = function() {
    return `${this.doors}개의 문이 있습니다.`;
};

const myCar = new Car('현대', 2023, 4);
console.log(myCar.getInfo()); // 출력: 2023년식 현대
console.log(myCar.getDoors()); // 출력: 4개의 문이 있습니다.

// 5. Factory 패턴과 생성자
console.log('\n5. Factory 패턴과 생성자');

function createUser(type, userData) {
    if (type === 'admin') {
        return new AdminUser(userData);
    } else if (type === 'regular') {
        return new RegularUser(userData);
    }
}

function AdminUser(userData) {
    this.name = userData.name;
    this.permissions = ['read', 'write', 'delete'];
}

function RegularUser(userData) {
    this.name = userData.name;
    this.permissions = ['read'];
}

const admin = createUser('admin', { name: '관리자' });
const regular = createUser('regular', { name: '일반사용자' });

console.log(admin.permissions); // 출력: ['read', 'write', 'delete']
console.log(regular.permissions); // 출력: ['read']

// 6. 생성자 함수 내부 메서드 최적화
console.log('\n6. 생성자 함수 내부 메서드 최적화');

function Counter() {
    // 메서드를 프로토타입에 정의
    if (typeof Counter.prototype.increment !== 'function') {
        Counter.prototype.increment = function() {
            this.count++;
        };
    }
    this.count = 0;
}

const counter1 = new Counter();
const counter2 = new Counter();

counter1.increment();
console.log(counter1.count); // 출력: 1
console.log(counter2.count); // 출력: 0
console.log(counter1.increment === counter2.increment); // 출력: true

// 7. new.target 사용
console.log('\n7. new.target 사용');

function User(name) {
    if (!new.target) {
        return new User(name);
    }
    this.name = name;
}

const user1 = new User('김철수');
const user2 = User('이영희'); // new 없이 호출해도 동작

console.log(user1.name); // 출력: 김철수
console.log(user2.name); // 출력: 이영희

// 8. ES6 클래스와 비교
console.log('\n8. ES6 클래스와 비교');

// 생성자 함수
function BookConstructor(title, author) {
    this.title = title;
    this.author = author;
}

BookConstructor.prototype.getInfo = function() {
    return `${this.title} by ${this.author}`;
};

// ES6 클래스
class Book {
    constructor(title, author) {
        this.title = title;
        this.author = author;
    }

    getInfo() {
        return `${this.title} by ${this.author}`;
    }
}

const book1 = new BookConstructor('JavaScript Guide', '김개발');
const book2 = new Book('JavaScript Guide', '김개발');

console.log(book1.getInfo()); // 출력: JavaScript Guide by 김개발
console.log(book2.getInfo()); // 출력: JavaScript Guide by 김개발
console.log(book1.getInfo === book2.getInfo); // 출력: false 