---
title: JavaScript 프로토타입 기반 상속
tags: [language, javascript, 01기본javascript, object, prototype, inheritance]
updated: 2025-08-10
---

# JavaScript 프로토타입 기반 상속

## 배경

JavaScript는 프로토타입 기반의 객체지향 프로그래밍 언어입니다. 클래스 기반 언어와 달리, JavaScript에서는 프로토타입 체인을 통해 상속과 객체 간의 관계를 구현합니다.

### 프로토타입의 필요성
- **상속 구현**: 객체 간의 속성과 메서드 공유
- **메모리 효율성**: 공통 속성을 프로토타입에 저장하여 메모리 절약
- **동적 확장**: 런타임에 객체의 기능을 확장 가능
- **유연성**: 객체 간의 관계를 동적으로 변경 가능

### 기본 개념
- **프로토타입 객체**: 객체의 속성과 메서드를 공유하는 템플릿
- **프로토타입 체인**: 객체에서 속성을 찾을 때 거슬러 올라가는 경로
- **생성자 함수**: 객체를 생성하고 프로토타입을 설정하는 함수
- **상속**: 부모 객체의 속성과 메서드를 자식 객체가 사용할 수 있는 기능

## 핵심

### 1. 프로토타입 객체

#### 프로토타입의 기본 개념
```javascript
// 모든 객체는 내부적으로 [[Prototype]] 속성을 가짐
const obj = {};
console.log(obj.__proto__); // Object.prototype

// 프로토타입 체인 확인
console.log(obj.__proto__ === Object.prototype); // true
console.log(Object.prototype.__proto__); // null (체인의 끝)
```

#### 프로토타입 접근 방법
```javascript
const obj = { name: 'Object' };

// __proto__ 속성을 통한 접근 (비표준, 권장하지 않음)
console.log(obj.__proto__);

// Object.getPrototypeOf() 메서드를 통한 접근 (표준)
console.log(Object.getPrototypeOf(obj));

// Object.setPrototypeOf() 메서드를 통한 프로토타입 설정
const parent = { type: 'Parent' };
Object.setPrototypeOf(obj, parent);
console.log(obj.type); // 'Parent'
```

#### Object.create()를 사용한 프로토타입 설정
```javascript
// 부모 객체 정의
const animal = {
    name: 'Animal',
    speak() {
        console.log(`${this.name}이(가) 소리를 냅니다.`);
    }
};

// 자식 객체 생성 (프로토타입 설정)
const dog = Object.create(animal);
dog.name = 'Dog';
dog.breed = 'Golden Retriever';

dog.speak(); // "Dog이(가) 소리를 냅니다."
console.log(dog.breed); // "Golden Retriever"
```

### 2. 프로토타입 체인과 상속

#### 프로토타입 체인 동작 원리
```javascript
const grandparent = { 
    name: 'Grandparent',
    sayHello() {
        console.log(`Hello from ${this.name}`);
    }
};

const parent = Object.create(grandparent);
parent.name = 'Parent';

const child = Object.create(parent);
child.name = 'Child';

// 프로토타입 체인을 통한 속성 접근
console.log(child.name); // 'Child' (자신의 속성)
child.sayHello(); // "Hello from Child" (프로토타입 체인을 통해 찾음)

// 프로토타입 체인 확인
console.log(Object.getPrototypeOf(child) === parent); // true
console.log(Object.getPrototypeOf(parent) === grandparent); // true
```

#### 생성자 함수와 프로토타입
```javascript
// 생성자 함수 정의
function Person(name, age) {
    this.name = name;
    this.age = age;
}

// 프로토타입에 메서드 추가
Person.prototype.sayHello = function() {
    console.log(`Hello, I'm ${this.name} and I'm ${this.age} years old.`);
};

Person.prototype.haveBirthday = function() {
    this.age++;
    console.log(`Happy birthday! Now I'm ${this.age} years old.`);
};

// 객체 생성
const person1 = new Person('Alice', 25);
const person2 = new Person('Bob', 30);

person1.sayHello(); // "Hello, I'm Alice and I'm 25 years old."
person2.sayHello(); // "Hello, I'm Bob and I'm 30 years old."

person1.haveBirthday(); // "Happy birthday! Now I'm 26 years old."

// 프로토타입 체인 확인
console.log(person1.__proto__ === Person.prototype); // true
console.log(Person.prototype.__proto__ === Object.prototype); // true
```

### 3. 상속 구현

#### 기본 상속 패턴
```javascript
// 부모 생성자 함수
function Animal(name) {
    this.name = name;
    this.health = 100;
}

Animal.prototype.speak = function() {
    console.log(`${this.name}이(가) 소리를 냅니다.`);
};

Animal.prototype.eat = function() {
    this.health += 10;
    console.log(`${this.name}이(가) 먹이를 먹었습니다. (체력: ${this.health})`);
};

// 자식 생성자 함수
function Dog(name, breed) {
    // 부모 생성자 호출
    Animal.call(this, name);
    this.breed = breed;
}

// 프로토타입 상속 설정
Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog; // 생성자 참조 복원

// 자식만의 메서드 추가
Dog.prototype.bark = function() {
    console.log(`${this.name}이(가) ${this.breed}답게 짖습니다!`);
};

// 객체 생성 및 사용
const myDog = new Dog('Max', 'Golden Retriever');
myDog.speak(); // "Max이(가) 소리를 냅니다."
myDog.eat(); // "Max이(가) 먹이를 먹었습니다. (체력: 110)"
myDog.bark(); // "Max이(가) Golden Retriever답게 짖습니다!"
```

#### ES6 클래스와 프로토타입
```javascript
// ES6 클래스는 내부적으로 프로토타입을 사용
class Animal {
    constructor(name) {
        this.name = name;
        this.health = 100;
    }
    
    speak() {
        console.log(`${this.name}이(가) 소리를 냅니다.`);
    }
    
    eat() {
        this.health += 10;
        console.log(`${this.name}이(가) 먹이를 먹었습니다. (체력: ${this.health})`);
    }
}

class Dog extends Animal {
    constructor(name, breed) {
        super(name); // 부모 생성자 호출
        this.breed = breed;
    }
    
    bark() {
        console.log(`${this.name}이(가) ${this.breed}답게 짖습니다!`);
    }
}

const dog = new Dog('Buddy', 'Labrador');
dog.speak(); // "Buddy이(가) 소리를 냅니다."
dog.bark(); // "Buddy이(가) Labrador답게 짖습니다!"

// 프로토타입 체인 확인
console.log(dog.__proto__ === Dog.prototype); // true
console.log(Dog.prototype.__proto__ === Animal.prototype); // true
```

## 예시

### 1. 실제 사용 사례

#### 게임 캐릭터 시스템
```javascript
// 기본 캐릭터 클래스
function Character(name, level) {
    this.name = name;
    this.level = level;
    this.hp = 100;
    this.mp = 50;
}

Character.prototype.attack = function(target) {
    const damage = this.level * 10;
    target.hp -= damage;
    console.log(`${this.name}이(가) ${target.name}에게 ${damage}의 피해를 입혔습니다.`);
};

Character.prototype.heal = function() {
    if (this.mp >= 20) {
        this.hp += 30;
        this.mp -= 20;
        console.log(`${this.name}이(가) 치료를 받았습니다. (HP: ${this.hp}, MP: ${this.mp})`);
    } else {
        console.log(`${this.name}의 MP가 부족합니다.`);
    }
};

// 전사 클래스
function Warrior(name, level) {
    Character.call(this, name, level);
    this.strength = level * 2;
}

Warrior.prototype = Object.create(Character.prototype);
Warrior.prototype.constructor = Warrior;

Warrior.prototype.charge = function(target) {
    const damage = this.strength * 1.5;
    target.hp -= damage;
    console.log(`${this.name}이(가) 돌진 공격으로 ${damage}의 피해를 입혔습니다!`);
};

// 마법사 클래스
function Mage(name, level) {
    Character.call(this, name, level);
    this.intelligence = level * 2;
}

Mage.prototype = Object.create(Character.prototype);
Mage.prototype.constructor = Mage;

Mage.prototype.fireball = function(target) {
    if (this.mp >= 30) {
        const damage = this.intelligence * 1.2;
        target.hp -= damage;
        this.mp -= 30;
        console.log(`${this.name}이(가) 파이어볼로 ${damage}의 피해를 입혔습니다!`);
    } else {
        console.log(`${this.name}의 MP가 부족합니다.`);
    }
};

// 게임 실행
const warrior = new Warrior('Aragorn', 5);
const mage = new Mage('Gandalf', 5);
const monster = new Character('Orc', 3);

warrior.attack(monster); // "Aragorn이(가) Orc에게 50의 피해를 입혔습니다."
mage.fireball(monster); // "Gandalf이(가) 파이어볼로 12의 피해를 입혔습니다!"
warrior.charge(monster); // "Aragorn이(가) 돌진 공격으로 15의 피해를 입혔습니다!"
```

### 2. 고급 패턴

#### 믹스인 패턴
```javascript
// 믹스인 유틸리티
function mixin(target, ...sources) {
    sources.forEach(source => {
        Object.getOwnPropertyNames(source).forEach(name => {
            const descriptor = Object.getOwnPropertyDescriptor(source, name);
            Object.defineProperty(target, name, descriptor);
        });
    });
    return target;
}

// 믹스인 객체들
const Movable = {
    move(x, y) {
        this.x += x;
        this.y += y;
        console.log(`${this.name}이(가) (${x}, ${y})만큼 이동했습니다.`);
    }
};

const Drawable = {
    draw() {
        console.log(`${this.name}을(를) (${this.x}, ${this.y})에 그렸습니다.`);
    }
};

const Collidable = {
    checkCollision(other) {
        const distance = Math.sqrt(
            Math.pow(this.x - other.x, 2) + Math.pow(this.y - other.y, 2)
        );
        return distance < (this.radius + other.radius);
    }
};

// 게임 객체 클래스
function GameObject(name, x, y, radius) {
    this.name = name;
    this.x = x;
    this.y = y;
    this.radius = radius;
}

// 믹스인 적용
mixin(GameObject.prototype, Movable, Drawable, Collidable);

// 사용 예시
const player = new GameObject('Player', 0, 0, 10);
const enemy = new GameObject('Enemy', 15, 15, 8);

player.move(5, 5); // "Player이(가) (5, 5)만큼 이동했습니다."
player.draw(); // "Player을(를) (5, 5)에 그렸습니다."

if (player.checkCollision(enemy)) {
    console.log('충돌이 발생했습니다!');
} else {
    console.log('충돌이 없습니다.');
}
```

#### 프로토타입 확장
```javascript
// Array 프로토타입 확장 (주의: 표준 라이브러리 확장은 권장하지 않음)
Array.prototype.first = function() {
    return this[0];
};

Array.prototype.last = function() {
    return this[this.length - 1];
};

Array.prototype.sum = function() {
    return this.reduce((sum, num) => sum + num, 0);
};

Array.prototype.average = function() {
    return this.sum() / this.length;
};

// 사용 예시
const numbers = [1, 2, 3, 4, 5];
console.log(numbers.first()); // 1
console.log(numbers.last()); // 5
console.log(numbers.sum()); // 15
console.log(numbers.average()); // 3

// 안전한 프로토타입 확장
if (!Array.prototype.find) {
    Array.prototype.find = function(predicate) {
        for (let i = 0; i < this.length; i++) {
            if (predicate(this[i], i, this)) {
                return this[i];
            }
        }
        return undefined;
    };
}
```

## 운영 팁

### 성능 최적화

#### 프로토타입 체인 최적화
```javascript
// 비효율적인 방법: 프로토타입 체인이 깊음
const level1 = { prop1: 'value1' };
const level2 = Object.create(level1);
const level3 = Object.create(level2);
const level4 = Object.create(level3);
const level5 = Object.create(level4);

// 효율적인 방법: 필요한 속성만 상속
const base = {
    commonMethod() {
        console.log('Common functionality');
    }
};

const specific1 = Object.create(base);
specific1.specificMethod1 = function() { /* ... */ };

const specific2 = Object.create(base);
specific2.specificMethod2 = function() { /* ... */ };
```

#### 메모리 효율성
```javascript
// 메서드를 프로토타입에 정의하여 메모리 절약
function EfficientClass(name) {
    this.name = name; // 인스턴스별 속성
}

// 모든 인스턴스가 공유하는 메서드
EfficientClass.prototype.method = function() {
    console.log(`Hello, ${this.name}!`);
};

// 비효율적인 방법: 각 인스턴스마다 메서드 생성
function InefficientClass(name) {
    this.name = name;
    this.method = function() { // 인스턴스별 메서드
        console.log(`Hello, ${this.name}!`);
    };
}
```

### 에러 처리

#### 프로토타입 오류 해결
```javascript
// 문제: 프로토타입 체인 오류
function ProblemClass() {}

const instance = new ProblemClass();
console.log(instance.nonExistentMethod()); // TypeError

// 해결: 안전한 메서드 호출
function SafeClass() {}

SafeClass.prototype.safeMethod = function(methodName, ...args) {
    if (typeof this[methodName] === 'function') {
        return this[methodName](...args);
    } else {
        console.warn(`Method ${methodName} does not exist`);
        return null;
    }
};

const safeInstance = new SafeClass();
safeInstance.safeMethod('nonExistentMethod'); // 경고 메시지 출력

// 해결: hasOwnProperty 사용
function PropertyCheckClass() {}

PropertyCheckClass.prototype.checkProperty = function(propName) {
    if (this.hasOwnProperty(propName)) {
        console.log(`${propName} is own property`);
    } else if (propName in this) {
        console.log(`${propName} is inherited property`);
    } else {
        console.log(`${propName} does not exist`);
    }
};
```

## 참고

### 프로토타입 vs 클래스 비교표

| 구분 | 프로토타입 | 클래스 |
|------|------------|--------|
| **문법** | 함수 기반 | class 키워드 |
| **상속** | Object.create() | extends |
| **메서드** | prototype에 정의 | 클래스 내부에 정의 |
| **호이스팅** | 함수 선언만 | 호이스팅되지 않음 |
| **private** | 구현 어려움 | # 키워드로 지원 |

### 프로토타입 체인 검사 방법

| 방법 | 설명 | 예시 |
|------|------|------|
| `instanceof` | 생성자 함수 체크 | `obj instanceof Constructor` |
| `isPrototypeOf` | 프로토타입 체크 | `Parent.prototype.isPrototypeOf(child)` |
| `hasOwnProperty` | 자신의 속성 체크 | `obj.hasOwnProperty('prop')` |
| `in` 연산자 | 프로토타입 포함 체크 | `'prop' in obj` |

### 결론
프로토타입은 JavaScript의 핵심 개념입니다.
프로토타입 체인을 통해 효율적인 상속을 구현하세요.
생성자 함수와 Object.create()를 적절히 활용하세요.
메모리 효율성을 위해 공통 메서드는 프로토타입에 정의하세요.
프로토타입 체인의 깊이를 최소화하여 성능을 최적화하세요.
안전한 프로토타입 확장을 통해 오류를 방지하세요.





