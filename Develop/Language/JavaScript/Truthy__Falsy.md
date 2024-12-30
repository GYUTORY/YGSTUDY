
# JavaScript에서 `true`와 `false`가 될 수 있는 조건

JavaScript에서 값은 조건문에서 **truthy**(참 같은 값) 또는 **falsy**(거짓 같은 값)으로 평가됩니다.  
이 문서에서는 truthy와 falsy의 조건을 자세히 설명하고, 예제와 함께 개념을 이해할 수 있도록 돕습니다.

---

## 1. Falsy 값
Falsy 값은 JavaScript에서 조건문이나 논리 연산에서 `false`로 평가되는 값입니다.

### Falsy 값 목록
JavaScript에서 falsy로 간주되는 값은 다음과 같습니다:

1. `false`
2. `0` (숫자 0)
3. `-0` (음수 0)
4. `0n` (BigInt에서의 0)
5. `""`, `''`, `` (빈 문자열)
6. `null`
7. `undefined`
8. `NaN` (Not-a-Number)

### Falsy 값 예시

```javascript
if (!false) console.log("false는 falsy 값입니다."); // 출력
if (!0) console.log("0은 falsy 값입니다."); // 출력
if (!"") console.log("빈 문자열은 falsy 값입니다."); // 출력
if (!null) console.log("null은 falsy 값입니다."); // 출력
if (!undefined) console.log("undefined는 falsy 값입니다."); // 출력
if (!NaN) console.log("NaN은 falsy 값입니다."); // 출력
```

---

## 2. Truthy 값
Falsy 값이 아닌 모든 값은 truthy로 간주됩니다.  
즉, 조건문에서 `true`로 평가됩니다.

### Truthy 값 목록
Truthy로 평가되는 값의 대표적인 예는 다음과 같습니다:

1. `true`
2. 0이 아닌 모든 숫자 (예: `1`, `-1`, `3.14`)
3. 빈 문자열이 아닌 모든 문자열 (예: `"hello"`, `"0"`, `"false"`)
4. `[]` (빈 배열)
5. `{}` (빈 객체)
6. 함수 (예: `function() {}`)
7. `Symbol()`
8. `Infinity`, `-Infinity`

#### 배열과 객체의 본질적인 특성
(1) 빈 배열 []
-  빈 배열도 JavaScript에서 객체로 취급됩니다. 배열이 비어있어도 메모리에서 실제로 객체로 존재하며, 이는 Falsy 값이 아닌 실제 값이기 때문에 truthy로 평가됩니다.

```javascript
console.log(typeof []); // "object"
console.log([] == true); // false
console.log(Boolean([])); // true
```
(2) 빈 객체 {}
- 빈 객체도 마찬가지로 JavaScript에서 객체로 취급되며, 값이 할당되지 않았어도 실제 메모리에서 존재합니다. 객체 자체는 Falsy 값이 아니기 때문에 truthy로 평가됩니다.

```javascript
console.log(typeof {}); // "object"
console.log({} == true); // false
console.log(Boolean({})); // true
```

### Truthy 값 예시

```javascript
if (true) console.log("true는 truthy 값입니다."); // 출력
if (1) console.log("1은 truthy 값입니다."); // 출력
if ("hello") console.log("문자열은 truthy 값입니다."); // 출력
if ([]) console.log("빈 배열은 truthy 값입니다."); // 출력
if ({}) console.log("빈 객체는 truthy 값입니다."); // 출력
if (function() {}) console.log("함수는 truthy 값입니다."); // 출력
if (Symbol()) console.log("Symbol은 truthy 값입니다."); // 출력
```

---

## 3. 주의사항: 비교와 변환
값이 truthy 또는 falsy로 평가되는 조건과 값 자체를 비교하는 것은 다릅니다.

### 느슨한 비교 (`==`)와 엄격한 비교 (`===`)
```javascript
console.log(0 == false);  // true (느슨한 비교에서 타입 강제 변환 발생)
console.log(0 === false); // false (엄격한 비교에서는 타입이 다름)
```

### Boolean 변환
`Boolean()` 함수를 사용하면 값이 truthy인지 falsy인지 명확히 확인할 수 있습니다.

```javascript
console.log(Boolean(0));        // false
console.log(Boolean("hello"));  // true
console.log(Boolean([]));       // true
console.log(Boolean(null));     // false
```

---

## 요약
- **Falsy 값**: `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined`, `NaN`
- **Truthy 값**: Falsy 값이 아닌 모든 값

JavaScript에서 truthy와 falsy의 동작 원리를 이해하면, 조건문에서 의도하지 않은 버그를 예방하고 더 직관적인 코드를 작성할 수 있습니다.
