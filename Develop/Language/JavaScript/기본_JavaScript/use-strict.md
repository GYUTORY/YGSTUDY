
## "use strict"
- JavaScript의 엄격 모드(strict mode)를 활성화하는 지시어로, 코드에서 잠재적인 오류를 줄이고, 안전하고 예측 가능한 코딩 환경을 만들기 위해 추가된 기능입니다.
- "use strict"를 코드의 최상단에 추가하거나 함수 내에서 선언하여 엄격 모드를 사용할 수 있습니다.
- 엄격 모드는 ECMAScript 5 (ES5)에서 처음 도입되었으며, 이를 통해 기존의 비표준적이거나 잘못된 코드를 방지하고, 최신 버전의 자바스크립트로 업그레이드할 때 발생할 수 있는 오류를 최소화합니다.

## "use strict" 사용 방법

#### 1. 전체 스크립트에 적용: 파일의 최상단에 "use strict"를 작성하여 파일 전체에 엄격 모드를 적용할 수 있습니다.

```javascript
"use strict";

// 모든 코드가 엄격 모드에서 실행됩니다.
```

<br>

#### 2. 함수 내부에만 적용 : 함수 내에서 "use strict"를 작성하여 해당 함수에만 엄격 모드를 적용할 수도 있습니다.
```javascript
function myFunction() {
"use strict";
// 이 함수 안에서만 엄격 모드가 적용됩니다.
}
```

<br>


## 엄격 모드에서의 주요 변화
- 엄격 모드는 다음과 같은 규칙을 적용하여 코드의 안전성을 높입니다.

### 1. 암시적 전역 변수 생성 방지: 변수를 선언하지 않고 사용하면 오류가 발생합니다.

```javascript
"use strict";
x = 3.14;  // ReferenceError: x is not defined
```

### 2. 읽기 전용 속성 수정 불가: 객체의 읽기 전용 속성에 값을 할당하려고 하면 오류가 발생합니다.

```javascript
"use strict";
const obj = {};
Object.defineProperty(obj, "prop", { value: 42, writable: false });
obj.prop = 77;  // TypeError: Cannot assign to read-only property 'prop'
```

### 3. 중복 속성 정의 불가: 객체 리터럴에서 중복된 속성 이름을 사용할 수 없습니다.

```javascript
"use strict";
const obj = { name: "Alice", name: "Bob" };  // SyntaxError: Duplicate data property in object literal
```


### 4. this 값이 undefined로 설정: 엄격 모드에서 함수가 전역 컨텍스트에서 호출될 경우, this는 undefined로 설정됩니다.

```javascript
"use strict";
function myFunction() {
    console.log(this);  // undefined
}
myFunction();
```


### 5. with 문 사용 금지: with 문은 변수 스코프를 모호하게 만들기 때문에 엄격 모드에서는 사용이 금지됩니다.

```javascript
"use strict";
with (Math) {  // SyntaxError: Strict mode code may not include a with statement
    x = cos(2);
}
```
