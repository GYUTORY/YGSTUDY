> "use strict" 선언시, 엄격모드 비선언시 비엄격모드로 정의한다. 

## "use strict" 모드의 유무
- 일반 함수에서 this의 동작에 영향을 주지만, 화살표 함수에서는 this의 동작에 영향을 주지 않습니다.
- 화살표 함수의 this는 언제나 렉시컬 환경(함수가 정의된 스코프)의 this를 상속하기 때문에, 엄격 모드와 관계없이 동일하게 동작합니다.

### 1. 일반 함수에서 this 동작
#### 비엄격 모드
- 전역 컨텍스트에서 this는 전역 객체(window 또는 globalThis)를 가리킵니다. 
- 일반 함수 호출 시 this는 자동으로 전역 객체를 참조합니다.
- 메서드로 호출될 때는 해당 객체를 this로 가리킵니다.
- 생성자 함수로 사용될 때는 새로 생성된 인스턴스를 this로 가리킵니다.

```javascript
// 비엄격 모드 예제들
// 1. 전역 컨텍스트
console.log(this);  // window 또는 globalThis

// 2. 일반 함수 호출
function regularFunction() {
  console.log(this);
}
regularFunction();  // window 또는 globalThis

// 3. 메서드 호출
const obj = {
  name: 'Object',
  method: function() {
    console.log(this);
  }
};
obj.method();  // { name: 'Object', method: [Function] }

// 4. 생성자 함수
function Person(name) {
  this.name = name;
  console.log(this);
}
new Person('John');  // Person { name: 'John' }
```

#### 엄격 모드
- 전역 컨텍스트에서 this는 여전히 전역 객체를 가리키지만, 함수 내부에서 호출할 때 this는 undefined로 설정됩니다.
- 즉, 엄격 모드에서는 함수 내 this가 자동으로 전역 객체에 바인딩되지 않습니다.
- 메서드와 생성자 함수의 동작은 비엄격 모드와 동일합니다.

```javascript
"use strict";

// 1. 전역 컨텍스트
console.log(this);  // window 또는 globalThis

// 2. 일반 함수 호출
function strictFunction() {
  console.log(this);
}
strictFunction();  // undefined

// 3. 메서드 호출 (엄격 모드에서도 동일)
const strictObj = {
  name: 'Strict Object',
  method: function() {
    console.log(this);
  }
};
strictObj.method();  // { name: 'Strict Object', method: [Function] }

// 4. 생성자 함수 (엄격 모드에서도 동일)
function StrictPerson(name) {
  this.name = name;
  console.log(this);
}
new StrictPerson('John');  // StrictPerson { name: 'John' }
```

### 2. Arrow Function에서 this 동작
- 비엄격 모드와 엄격 모드 모두에서 동일하게 동작합니다.
- 화살표 함수는 언제나 상위 스코프의 this를 상속하므로, 엄격 모드의 영향을 받지 않습니다.
- 화살표 함수는 자신만의 this를 가지지 않고, 항상 정의된 위치의 this를 참조합니다.

```javascript
"use strict";  // 엄격 모드 활성화

// 1. 전역 스코프의 화살표 함수
const globalArrow = () => {
  console.log(this);
};
globalArrow();  // window 또는 globalThis

// 2. 객체 메서드로 사용된 화살표 함수
const person = {
  name: "Alice",
  greet: () => {
    console.log(this);
  }
};
person.greet();  // window 또는 globalThis (person 객체가 아닌 전역 객체를 가리킴)

// 3. 일반 함수 내부의 화살표 함수
function outerFunction() {
  const innerArrow = () => {
    console.log(this);
  };
  innerArrow();
}
outerFunction();  // undefined (엄격 모드에서 outerFunction의 this가 undefined이므로)

// 4. 메서드 내부의 화살표 함수
const obj = {
  name: "Object",
  method: function() {
    const arrow = () => {
      console.log(this);
    };
    arrow();
  }
};
obj.method();  // { name: "Object", method: [Function] } (obj를 가리킴)
```

### 3. this 바인딩의 주요 특징
1. **일반 함수의 this 바인딩**
   - 함수 호출 방식에 따라 this가 동적으로 결정됩니다.
   - 엄격 모드에서는 함수 내부의 this가 undefined가 됩니다.
   - call(), apply(), bind() 메서드를 사용하여 this를 명시적으로 바인딩할 수 있습니다.

2. **화살표 함수의 this 바인딩**
   - 정의된 시점의 상위 스코프의 this를 정적으로 바인딩합니다.
   - call(), apply(), bind() 메서드를 사용해도 this 바인딩을 변경할 수 없습니다.
   - 항상 자신이 정의된 위치의 this를 참조합니다.

---

# 결론
### 일반 함수
- "use strict"의 유무에 따라 this의 값이 달라집니다 (undefined 또는 전역 객체).
- 함수 호출 방식(일반 호출, 메서드 호출, 생성자 호출)에 따라 this가 동적으로 결정됩니다.
- call(), apply(), bind() 메서드로 this를 명시적으로 바인딩할 수 있습니다.

### 화살표 함수
- "use strict"의 영향을 받지 않으며, 항상 렉시컬 환경의 this를 상속합니다.
- 정의된 위치의 this를 정적으로 바인딩하며, 변경할 수 없습니다.
- 메서드나 콜백 함수로 사용할 때 주의가 필요합니다.