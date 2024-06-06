
# Spread 연산자 
- Spread 연산자 (...)는 JavaScript에서 객체와 배열을 복사하거나 병합할 때 유용하게 사용되는 연산자입니다. 
- 하지만 Spread 연산자는 얕은 복사를 수행한다는 점에서 주의가 필요합니다.

---

## Spread 연산자를 사용한 얕은 복사

---

## 배열의 얕은 복사

### 1.1 배열의 얕은 복사 1

```javascript
let originalArray = [1, 2, 3];
let shallowCopyArray = [...originalArray];

shallowCopyArray[0] = 99;

console.log(originalArray); // 출력: [1, 2, 3]
console.log(shallowCopyArray); // 출력: [99, 2, 3]
```

### 설명 
- 위의 예시에서 배열의 최상위 요소들은 숫자이기 때문에 변경 사항이 원본 배열에 영향을 미치지 않습니다. 
- 그러나 배열 안에 객체가 포함된 경우 얕은 복사의 특성이 드러납니다.


### 1.2 배열의 얕은 복사 2

```javascript
let originalArray = [{ a: 1 }, { b: 2 }];
let shallowCopyArray = [...originalArray];

shallowCopyArray[0].a = 99;

console.log(originalArray[0].a); // 출력: 99
console.log(shallowCopyArray[0].a); // 출력: 99
```

### 설명
- 여기서 객체 shallowCopyArray[0]는 originalArray[0]과 같은 참조를 공유하므로, 하나를 변경하면 다른 것도 변경됩니다.

---

## 객체의 얕은 복사

### 1.1 객체의 얕은 복사 1

```javascript
let originalObject = { a: 1, b: 2 };
let shallowCopyObject = { ...originalObject };

shallowCopyObject.a = 99;

console.log(originalObject); // 출력: { a: 1, b: 2 }
console.log(shallowCopyObject); // 출력: { a: 99, b: 2 }
```

### 설명
- 이 경우도 마찬가지로 객체의 최상위 속성들은 원시 값이므로 변경 사항이 원본 객체에 영향을 미치지 않습니다.
- 하지만 중첩된 객체의 경우는 다릅니다.


### 1.2 객체의 얕은 복사 2

```javascript
let originalObject = { a: 1, b: { c: 2 } };
let shallowCopyObject = { ...originalObject };

shallowCopyObject.b.c = 99;

console.log(originalObject.b.c); // 출력: 99
console.log(shallowCopyObject.b.c); // 출력: 99
```

### 설명
- 여기서 중첩된 객체 b는 얕은 복사로 인해 참조를 공유하게 되므로, 하나를 변경하면 다른 것도 변경됩니다.

---

## Spread 연산자를 사용한 깊은 복사
- Spread 연산자는 깊은 복사를 직접적으로 지원하지 않습니다. 
- 깊은 복사를 위해서는 다른 방법이 필요합니다.

```javascript
let originalObject = { a: 1, b: { c: 2 } };
let deepCopyObject = JSON.parse(JSON.stringify(originalObject));

deepCopyObject.b.c = 99;

console.log(originalObject.b.c); // 출력: 2
console.log(deepCopyObject.b.c); // 출력: 99

```

### 설명 
1. JSON.parse와 JSON.stringify를 사용할 수 있지만, 이는 함수와 undefined 같은 값들을 처리하지 못합니다.


---

# 깊은복사를 위한 결론
- **간단한 객체**: JSON.parse와 JSON.stringify 사용.
- **복잡한 객체 및 순환 참조**: Lodash의 _.cloneDeep 또는 structuredClone 사용.
- **맞춤형 요구사항**: 재귀적 복사 함수 작성. 





