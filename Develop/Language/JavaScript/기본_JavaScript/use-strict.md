

# 🚀 JavaScript Strict Mode (엄격 모드)

## 1️⃣ Strict Mode란?
**Strict Mode(엄격 모드)**는 **JavaScript에서 좀 더 엄격한 문법을 적용하여 오류를 방지하는 모드**입니다.  
기본적으로 JavaScript는 유연한 문법을 허용하지만, 엄격 모드를 사용하면 **실수로 인한 오류를 방지하고, 코드의 안정성을 높일 수 있습니다.**

> **👉🏻 `strict mode`는 JavaScript의 보안과 성능을 개선하는 데 도움을 줍니다.**

---

## 2️⃣ Strict Mode 활성화 방법

### ✅ 스크립트 전체에서 적용
```javascript
"use strict";  // 스크립트 전체에 엄격 모드 적용

function test() {
    x = 10; // 오류 발생 (변수를 선언하지 않고 할당할 수 없음)
    console.log(x);
}

test();
```

> **👉🏻 `"use strict";`를 코드 맨 위에 작성하면 스크립트 전체에 적용됩니다.**

### ✅ 특정 함수에서만 적용
```javascript
function strictFunction() {
    "use strict";
    let a = 5;
    b = 10; // 오류 발생 (변수 선언 없이 사용 불가)
    console.log(a + b);
}

strictFunction();
```

> **👉🏻 특정 함수 내부에서만 엄격 모드를 사용할 수도 있습니다.**

---

## 3️⃣ Strict Mode에서 달라지는 점

### ✅ 1. 암시적 변수 선언 금지
```javascript
"use strict";
x = 10; // 오류 발생 (변수 선언 없이 사용 불가)
```

> **👉🏻 `var`, `let`, `const` 없이 변수를 선언하면 오류가 발생합니다.**

---

### ✅ 2. `this`의 값이 `undefined`가 됨
일반적으로 함수에서 `this`는 `window`를 가리키지만, **strict mode에서는 `undefined`가 됩니다.**

```javascript
"use strict";

function showThis() {
    console.log(this); // undefined
}

showThis();
```

> **👉🏻 `this`가 `undefined`가 되므로, 의도치 않은 전역 객체 수정이 방지됩니다.**

---

### ✅ 3. 읽기 전용 속성 수정 불가
```javascript
"use strict";

const obj = Object.freeze({ name: "Alice" });
obj.name = "Bob"; // 오류 발생 (읽기 전용 속성 수정 불가)
```

> **👉🏻 `Object.freeze()`로 정의된 객체의 속성을 변경하려고 하면 오류가 발생합니다.**

---

### ✅ 4. 중복된 매개변수 금지
```javascript
"use strict";

function duplicateParams(a, a, c) { // 오류 발생 (중복된 매개변수)
    return a + c;
}
```

> **👉🏻 엄격 모드에서는 같은 이름의 매개변수를 사용할 수 없습니다.**

---

### ✅ 5. `eval()` 사용 제한
```javascript
"use strict";

eval("var x = 10;");
console.log(x); // 오류 발생 (eval 내부 변수는 외부에서 접근 불가)
```

> **👉🏻 `eval()`을 사용해도 전역 범위에 영향을 미치지 않도록 제한됩니다.**

---

### ✅ 6. `with` 문 사용 금지
```javascript
"use strict";

var obj = { name: "Alice", age: 25 };
with (obj) { // 오류 발생 (with 문 사용 불가)
    console.log(name);
}
```

> **👉🏻 `with` 문은 속성이 어디에서 오는지 모호하게 만들기 때문에 금지됩니다.**

---

## 4️⃣ Strict Mode 사용 시 주의할 점

### ✅ 1. 기존 코드와의 호환성 확인
- 기존 코드에서 `strict mode`를 적용하면 **예기치 않은 오류가 발생할 수 있음**
- 따라서 **기존 프로젝트에 적용할 때는 부분적으로 적용하는 것이 좋음**

### ✅ 2. ES6 이상의 모듈에서는 기본 적용
- ES6 이상의 **ECMAScript Modules (ESM)**에서는 `strict mode`가 **자동으로 적용됨**
```javascript
// ES6 모듈에서 strict mode는 기본 활성화됨
export function test() {
    x = 10; // 오류 발생
}
```

> **👉🏻 ES6 모듈을 사용하면 따로 `"use strict";`를 선언할 필요가 없습니다.**

---

## 5️⃣ Strict Mode의 장점과 단점

| 장점 | 단점 |
|------|------|
| 코드 안정성 증가 | 기존 코드와 호환성 문제 발생 가능 |
| 오류 감지 강화 | 일부 기능 제한 (`with` 문 사용 불가 등) |
| 성능 최적화 | eval() 같은 기능 제한됨 |

> **👉🏻 엄격 모드는 보안성과 성능을 향상시키지만, 기존 코드에 적용할 때는 신중해야 합니다!**

