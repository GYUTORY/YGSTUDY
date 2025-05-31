# JavaScript의 프로토타입 기반 상속 🧬

JavaScript는 프로토타입 기반 언어로, 객체 지향 프로그래밍의 핵심 개념인 상속을 프로토타입 체인을 통해 구현합니다. 이 문서에서는 프로토타입 기반 상속의 개념과 실제 활용 방법을 자세히 살펴보겠습니다.

## 목차 📚
- [프로토타입의 기본 개념](#프로토타입의-기본-개념)
- [프로토타입 체인과 상속](#프로토타입-체인과-상속)
- [실제 활용 예제](#실제-활용-예제)
- [프로토타입 상속의 장단점](#프로토타입-상속의-장단점)

---

## 프로토타입의 기본 개념 🔍

### 1. 프로토타입 객체란?
JavaScript의 모든 객체는 내부적으로 `[[Prototype]]`이라는 숨겨진 속성을 가지고 있습니다. 이 속성은 다른 객체를 참조하며, 이를 통해 상속이 이루어집니다. 프로토타입 객체는 객체의 속성과 메서드를 공유하는 템플릿 역할을 합니다.

### 2. 프로토타입 접근 방법
```javascript
// __proto__ 속성을 통한 접근 (비표준)
const obj = {};
console.log(obj.__proto__);

// Object.getPrototypeOf() 메서드를 통한 접근 (표준)
console.log(Object.getPrototypeOf(obj));
```

### 3. 프로토타입 설정 방법
```javascript
// Object.create()를 사용한 프로토타입 설정
const parent = { name: 'Parent' };
const child = Object.create(parent);
console.log(child.name); // 'Parent'
```

---

## 프로토타입 체인과 상속 🔄

### 1. 프로토타입 체인
프로토타입 체인은 객체의 속성이나 메서드를 찾을 때, 해당 객체에 없으면 프로토타입 객체를 거슬러 올라가며 찾는 메커니즘입니다.

```javascript
const grandparent = { name: 'Grandparent' };
const parent = Object.create(grandparent);
const child = Object.create(parent);

console.log(child.name); // 'Grandparent'
```

### 2. 생성자 함수와 프로토타입
생성자 함수를 사용하면 객체를 초기화하고, 해당 객체의 프로토타입을 설정할 수 있습니다.

```javascript
function Person(name) {
    this.name = name;
}

Person.prototype.sayHello = function() {
    console.log(`Hello, I'm ${this.name}`);
};

const person = new Person('John');
person.sayHello(); // "Hello, I'm John"
```

---

## 실제 활용 예제 🛠️

### 1. 동물 클래스 계층 구조 구현

```javascript
// 기본 Animal 클래스
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

// Dog 클래스 (Animal 상속)
function Dog(name, breed) {
    Animal.call(this, name);
    this.breed = breed;
}

Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog;

Dog.prototype.bark = function() {
    console.log(`${this.name}이(가) ${this.breed}답게 짖습니다!`);
};

// Cat 클래스 (Animal 상속)
function Cat(name, color) {
    Animal.call(this, name);
    this.color = color;
}

Cat.prototype = Object.create(Animal.prototype);
Cat.prototype.constructor = Cat;

Cat.prototype.meow = function() {
    console.log(`${this.name}이(가) ${this.color}색 고양이답게 야옹합니다!`);
};
```

### 2. 사용 예시
```javascript
const dog = new Dog('바둑이', '진돗개');
dog.speak();  // 바둑이가 소리를 냅니다.
dog.bark();   // 바둑이가 진돗개답게 짖습니다!
dog.eat();    // 바둑이가 먹이를 먹었습니다. (체력: 110)

const cat = new Cat('나비', '검정');
cat.speak();  // 나비가 소리를 냅니다.
cat.meow();   // 나비가 검정색 고양이답게 야옹합니다!
cat.eat();    // 나비가 먹이를 먹었습니다. (체력: 110)
```

---

## 프로토타입 상속의 장단점 ⚖️

### 장점 ✨
1. **메모리 효율성**
   - 공통 속성과 메서드는 프로토타입에 저장되어 모든 인스턴스가 공유
   - 각 인스턴스마다 메서드를 복제하지 않아도 됨

2. **유연한 확장성**
   - 런타임에 프로토타입을 수정하여 모든 인스턴스에 즉시 반영 가능
   - 동적으로 메서드 추가/수정 가능

3. **코드 재사용성**
   - 상속을 통한 코드 재사용으로 중복 코드 최소화
   - 유지보수성 향상

### 단점 ⚠️
1. **복잡한 디버깅**
   - 프로토타입 체인을 통한 속성 검색으로 디버깅이 어려울 수 있음
   - `this` 바인딩 관련 주의 필요

2. **성능 고려사항**
   - 프로토타입 체인이 길어질수록 속성 검색 시간 증가
   - 깊은 상속 구조는 성능에 영향을 줄 수 있음

---

## 결론 🎯

JavaScript의 프로토타입 기반 상속은 강력하면서도 유연한 객체지향 프로그래밍을 가능하게 합니다. 적절히 활용하면 코드의 재사용성과 유지보수성을 크게 향상시킬 수 있으며, 메모리 사용도 효율적으로 관리할 수 있습니다. 다만, 프로토타입 체인의 복잡성과 성능 고려사항을 잘 이해하고 사용하는 것이 중요합니다.

