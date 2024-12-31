
# JavaScript의 프로토타입 기반 상속을 활용한 커스텀 객체 모델 설계

JavaScript는 프로토타입 기반 언어로, 객체 간 상속 관계를 설정하여 코드의 재사용성을 높이고 확장이 가능한 설계를 할 수 있습니다.
이 문서에서는 프로토타입 기반 상속의 개념과 이를 활용한 커스텀 객체 모델 설계 방법을 예제와 함께 설명합니다.

---

## 프로토타입 기반 상속의 기본 개념

1. **프로토타입 객체**  
   JavaScript의 모든 객체는 내부적으로 `[[Prototype]]`이라는 숨겨진 속성을 가지고 있습니다. 이 속성은 다른 객체를 참조하며, 이를 통해 상속이 이루어집니다.

2. **`Object.create`를 이용한 상속**  
   `Object.create` 메서드를 사용하면 특정 객체를 프로토타입으로 가지는 새 객체를 생성할 수 있습니다.

3. **생성자 함수와 프로토타입**  
   생성자 함수를 사용하면 객체를 초기화하고, 해당 객체의 프로토타입을 설정하여 상속 관계를 구축할 수 있습니다.

---

## 예제: 커스텀 객체 모델 설계

아래 예제는 프로토타입 기반 상속을 활용하여 `Animal` 객체를 정의하고, 이를 상속받아 `Dog`와 `Cat` 객체를 설계하는 방법을 보여줍니다.

### 1. 기본 객체 설계

```javascript
// Animal 객체 정의
function Animal(name) {
    this.name = name;
}

Animal.prototype.speak = function () {
    console.log(`${this.name}이(가) 소리를 냅니다.`);
};
```

### 2. 상속을 통해 확장된 객체 설계

```javascript
// Dog 객체 정의
function Dog(name, breed) {
    Animal.call(this, name); // 부모 생성자 호출
    this.breed = breed;
}

// Animal을 상속
Dog.prototype = Object.create(Animal.prototype);
Dog.prototype.constructor = Dog;

// Dog만의 메서드 추가
Dog.prototype.bark = function () {
    console.log(`${this.name}이(가) 짖습니다.`);
};

// Cat 객체 정의
function Cat(name, color) {
    Animal.call(this, name); // 부모 생성자 호출
    this.color = color;
}

// Animal을 상속
Cat.prototype = Object.create(Animal.prototype);
Cat.prototype.constructor = Cat;

// Cat만의 메서드 추가
Cat.prototype.meow = function () {
    console.log(`${this.name}이(가) 야옹합니다.`);
};
```

### 3. 사용 예시

```javascript
const dog = new Dog('바둑이', '진돗개');
dog.speak(); // 바둑이가 소리를 냅니다.
dog.bark();  // 바둑이가 짖습니다.

const cat = new Cat('나비', '검정색');
cat.speak(); // 나비가 소리를 냅니다.
cat.meow();  // 나비가 야옹합니다.
```

---

## 프로토타입 상속의 장점

1. **메모리 효율성**  
   공통 속성과 메서드는 프로토타입에 저장되며, 모든 인스턴스가 이를 공유합니다.

2. **유연한 확장**  
   프로토타입 체인을 활용하면 기존 객체를 쉽게 확장할 수 있습니다.

---

## 요약

JavaScript의 프로토타입 기반 상속은 객체지향 프로그래밍을 지원하며, 객체 간의 관계를 효율적으로 설계할 수 있는 강력한 도구입니다. 이를 활용하면 코드의 재사용성과 유지보수성을 크게 향상시킬 수 있습니다.

