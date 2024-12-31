

> "use strict" 선언시, 엄격모드 비선언시 비엄격모드로 정의한다. 

## "use strict" 모드의 유무
- 일반 함수에서 this의 동작에 영향을 주지만, 화살표 함수에서는 this의 동작에 영향을 주지 않습니다.
- 화살표 함수의 this는 언제나 렉시컬 환경(함수가 정의된 스코프)의 this를 상속하기 때문에, 엄격 모드와 관계없이 동일하게 동작합니다.


### 1. 일반 함수에서 this 동작
#### 비엄격 모드
- 전역 컨텍스트에서 this는 전역 객체(window 또는 globalThis)를 가리킵니다. 
- 일반 함수 호출 시 this는 자동으로 전역 객체를 참조합니다.

#### 엄격 모드
- 전역 컨텍스트에서 this는 여전히 전역 객체를 가리키지만, 함수 내부에서 호출할 때 this는 undefined로 설정됩니다.
- 즉, 엄격 모드에서는 함수 내 this가 자동으로 전역 객체에 바인딩되지 않습니다.

```javascript
// 비엄격 모드
function myFunction() {
  console.log(this);
}
myFunction();  // 전역 객체 (window 또는 globalThis)

// 엄격 모드
"use strict";
function myFunction() {
  console.log(this);
}
myFunction();  // undefined
```

### 2. Arrow Function에서 this 동작
- 비엄격 모드와 엄격 모드 모두에서 동일하게 동작합니다.
- 화살표 함수는 언제나 상위 스코프의 this를 상속하므로, 엄격 모드의 영향을 받지 않습니다.

```javascript
"use strict";  // 엄격 모드 활성화

const person = {
  name: "Alice",
  greet: () => {
    console.log(this);
  }
};

person.greet();  // 상위 스코프의 this (전역 객체)
```
- 위 코드에서 person.greet()에 정의된 화살표 함수는 this를 상위 스코프에서 가져옵니다.
- this는 전역 객체(window 또는 globalThis)로 평가됩니다. "use strict"가 있어도 화살표 함수의 this 동작은 변하지 않습니다.

---

# 결론
### 일반 함수
- "use strict"의 유무에 따라 this의 값이 달라집니다 (undefined 또는 전역 객체).

### 화살표 함수
- "use strict"의 영향을 받지 않으며, 항상 렉시컬 환경의 this를 상속합니다.