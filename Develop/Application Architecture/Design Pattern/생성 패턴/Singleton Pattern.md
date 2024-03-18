
## 디자인 패턴 중 하나인 싱글톤 패턴

### 요약
- 전역적으로 사용할 수 있는 유일한 인스턴스를 생성하는 패턴.

### 설명
- 싱글톤 패턴은 특정 인스턴스가 오직 하나만 존재하도록 보장하는 소프트웨어 설계 패턴이다.
- 전역 변수를 사용하지 않고도 해당 객체를 전역적으로 접근 할 수 있게 되며 공유 자원에 대한 동시 접근을 제어할 수 있다.



--- 

## class 문법을 이용한 싱글톤
### 기본예시
```javascript
// Singleton.js
let instance;

export default class Singleton {
    constructor(data = 'Initial data') {
        if (instance) {
            return instance;
        }
        this.data = data;
        instance = this;
    }

    getData() {
        return this.data;
    }

    setData(data) {
        this.data = data;
    }
}
```

### 코드 설명
- Singleton 클래스를 만들어 만약 instance가 있는 경우에는 return instance를 통해 새로운 클래스가 생성되지 않도록 막고 있다.
- data를 받지 않을 시 기본 데이터로 “Initial data”를 주고 있다.
- 기본적인 getData, setData 함수를 통해 Singleton 클래스 안에서 값을 가져오고, 업데이트 하는 기능을 제공한다.

### 사용 예시
```javascript
import Singleton from './Singleton.js';

// Singleton 클래스의 인스턴스를 생성합니다.
let singleton = new Singleton('First data');

// 데이터를 가져옵니다.
console.log(singleton.getData());  // "First data"

// 데이터를 업데이트합니다.
singleton.setData('Updated data');
console.log(singleton.getData());  // "Updated data"

// 또 다른 인스턴스를 생성하려고 시도합니다.
let anotherSingleton = new Singleton('Another data');

// 하지만 싱글톤 패턴에 따라, 이전에 생성된 인스턴스가 반환됩니다.
console.log(anotherSingleton === singleton);  // true
console.log(anotherSingleton.getData());  // "Updated data"
```

### 코드 설명
- Singleton 클래스를 import 해와서 singleton 이라는 변수에 저장한다.
- 저장 함과 동시에 “First data” 라는 스트링을 전달해 Singleton의 constructor를 통해 this 바인딩을 통해 data = “First data”가 된다.
- 그래서 콘솔에 처음 찍히는 getData함수는 “First data”가 되고 Singeton은 새로운 변수에 저장하더라도 여전히 “First data” 라는 data 값을 갖고 있다.

--- 

## 즉시 실행 함수 싱글톤 패턴

### 사용예시
```javascript
let Singleton = (function() {
  let instance = null;

  function SingletonClass(data = 'Initial data') {
    if (instance) {
      return instance;
    }

    this.data = data;
    instance = this;
  }

  SingletonClass.prototype.getData = function() {
    return this.data;
  }

  SingletonClass.prototype.setData = function(data) {
    this.data = data;
  }

  return SingletonClass;
})();

export default Singleton;
```

### 사용 예시
```javascript
import Singleton from './Singleton.js';

let singleton = new Singleton('First data');
console.log(singleton.getData()); // 'First data'

singleton.setData('Updated data');
console.log(singleton.getData()); // 'Updated data'

let anotherSingleton = new Singleton();

console.log(anotherSingleton.getData()); // 'Updated data'
console.log(singleton === anotherSingleton); // true
```

---



```
출처
https://chaeoff.medium.com/singleton-pattern-%EC%8B%B1%EA%B8%80%ED%86%A4-%ED%8C%A8%ED%84%B4-1131fae052f5
```