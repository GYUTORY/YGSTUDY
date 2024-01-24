
# constructor
- constructor 메서드는 클래스의 인스턴스 객체를 생성하고 초기화하는 특별한 메서드입니다.

```javascript
class Polygon {
  constructor() {
    this.name = 'Polygon';
  }
}

const poly1 = new Polygon();

console.log(poly1.name);
// Expected output: "Polygon"

```
결과
> "Polygon"


## 구문
```javascript
constructor() { ... }
constructor(argument0) { ... }
constructor(argument0, argument1) { ... }
constructor(argument0, argument1, ... , argumentN) { ... }
```

## 설명
- constructor를 사용하면 다른 모든 메서드 호출보다 앞선 시점인, 인스턴스 객체를 초기화할 때 수행할 초기화 코드를 정의할 수 있습니다.
 
```javascript
class Person {
  constructor(name) {
    this.name = name;
  }

  introduce() {
    console.log(`Hello, my name is ${this.name}`);
  }
}

const otto = new Person("Otto");

otto.introduce();
```







