# JavaScript 깊은 복사와 얕은 복사 🎯

JavaScript에서 데이터를 다룰 때 가장 중요한 개념 중 하나가 바로 복사입니다. 특히 객체나 배열과 같은 참조 타입 데이터를 다룰 때는 얕은 복사(Shallow Copy)와 깊은 복사(Deep Copy)의 차이를 정확히 이해하는 것이 매우 중요합니다. 이번 글에서는 이 두 가지 복사 방식의 차이점과 각각의 사용 사례를 자세히 살펴보겠습니다.

## 복사의 기본 개념 📚

JavaScript에서 데이터를 복사할 때는 두 가지 방식이 있습니다:
- **얕은 복사(Shallow Copy)**: 객체의 첫 번째 레벨에 있는 값만 복사
- **깊은 복사(Deep Copy)**: 객체의 모든 레벨을 완전히 새로운 메모리에 복사

## 얕은 복사 (Shallow Copy) 🔄

### 특징
1. **원시 타입(Primitive Type)**: 값이 그대로 복사됩니다.
   ```javascript
   const num = 42;
   const copyNum = num; // 42가 그대로 복사됨
   ```

2. **참조 타입(Reference Type)**: 참조(메모리 주소)가 복사됩니다.
   ```javascript
   const arr = [1, 2, 3];
   const copyArr = arr; // arr의 메모리 주소가 복사됨
   ```

3. **중첩 객체**: 원본 객체와 동일한 참조를 공유합니다.
   ```javascript
   const obj = { a: { b: 1 } };
   const copyObj = { ...obj };
   obj.a.b = 2; // copyObj.a.b도 2로 변경됨
   ```

### 얕은 복사 방법
1. **Object.assign()**
   ```javascript
   const original = { a: 1, b: 2 };
   const copy = Object.assign({}, original);
   ```

2. **전개 연산자 (Spread Operator)**
   ```javascript
   const original = { a: 1, b: 2 };
   const copy = { ...original };
   ```

3. **Array.from()**
   ```javascript
   const original = [1, 2, 3];
   const copy = Array.from(original);
   ```

4. **slice()**
   ```javascript
   const original = [1, 2, 3];
   const copy = original.slice();
   ```

## 깊은 복사 (Deep Copy) 🔍

### 특징
1. **원시 타입**: 값이 그대로 복사됩니다.
2. **참조 타입**: 새로운 메모리 공간에 완전히 복사됩니다.
3. **중첩 객체**: 모든 레벨의 객체가 독립적으로 복사됩니다.

### 깊은 복사 방법
1. **JSON.parse(JSON.stringify())**
   ```javascript
   const original = { a: { b: 1 } };
   const copy = JSON.parse(JSON.stringify(original));
   ```

2. **재귀 함수를 사용한 복사**
   ```javascript
   function deepCopy(obj) {
     if (obj === null || typeof obj !== 'object') return obj;
     const copy = Array.isArray(obj) ? [] : {};
     for (let key in obj) {
       if (Object.prototype.hasOwnProperty.call(obj, key)) {
         copy[key] = deepCopy(obj[key]);
       }
     }
     return copy;
   }
   ```

3. **라이브러리 사용**
   ```javascript
   // lodash 사용
   const copy = _.cloneDeep(original);
   ```

## 주의사항 ⚠️

### 얕은 복사의 한계
1. 중첩된 객체는 여전히 원본과 참조를 공유합니다.
2. 원본 객체의 중첩된 값을 변경하면 복사본도 영향을 받습니다.

### JSON 방식의 깊은 복사 한계
1. 함수는 복사되지 않습니다.
2. undefined 값은 무시됩니다.
3. Date 객체는 문자열로 변환됩니다.
4. 순환 참조가 있는 객체는 에러가 발생합니다.
5. BigInt 값은 처리할 수 없습니다.

## 실무에서의 활용 💡

### 얕은 복사 사용 시나리오
1. 단순한 객체의 복사가 필요할 때
2. 중첩된 데이터가 없는 경우
3. 성능이 중요한 경우
4. 원본 데이터의 일부 참조를 유지해야 할 때

### 깊은 복사 사용 시나리오
1. 완전히 독립적인 복사본이 필요할 때
2. 중첩된 객체 구조를 다룰 때
3. 원본 데이터의 불변성이 중요할 때
4. 복잡한 데이터 구조를 다룰 때

## 성능 고려사항 ⚡

- 얕은 복사는 깊은 복사보다 일반적으로 더 빠릅니다.
- 대규모 객체나 배열을 다룰 때는 성능을 고려하여 적절한 방식을 선택해야 합니다.
- JSON 방식의 깊은 복사는 간단하지만, 성능이 중요한 경우에는 라이브러리를 사용하는 것이 좋습니다.

## 결론 🎯

JavaScript에서 데이터를 복사할 때는 상황과 요구사항에 따라 적절한 방식을 선택해야 합니다. 단순한 데이터 구조라면 얕은 복사로 충분할 수 있지만, 복잡한 중첩 구조를 다룰 때는 깊은 복사를 사용하는 것이 안전합니다. 또한, 성능과 기능적 요구사항을 모두 고려하여 최적의 방식을 선택하는 것이 중요합니다. 