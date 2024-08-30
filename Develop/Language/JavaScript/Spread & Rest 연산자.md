

# Spread 연산자
- ... 연산자는 JavaScript에서 **스프레드 연산자(spread operator)**와 **전개 연산자(rest operator)**로 사용됩니다. 각각의 용도는 다음과 같습니다.

## 1.스프레드 연산자 (Spread Operator)
   스프레드 연산자는 배열이나 객체를 쉽게 펼치는 데 사용됩니다.

### 배열에서의 사용

```javascript
const arr1 = [1, 2, 3];
const arr2 = [4, 5, ...arr1]; // arr2는 [4, 5, 1, 2, 3]
```


- arr1의 요소들이 arr2에 펼쳐져 추가됩니다.

### 객체에서의 사용 

```javascript
const obj1 = { a: 1, b: 2 };
const obj2 = { c: 3, ...obj1 }; // obj2는 { c: 3, a: 1, b: 2 }
```

- obj1의 속성이 obj2에 펼쳐져 추가됩니다.

## 2. 전개 연산자 (Rest Operator)
- 전개 연산자는 주로 함수의 매개변수에서 여러 개의 인수를 배열로 모을 때 사용합니다.

```javascript
function sum(...numbers) {
    return numbers.reduce((acc, curr) => acc + curr, 0);
}

console.log(sum(1, 2, 3, 4)); // 10
```


- ...numbers는 모든 인수를 하나의 배열로 모읍니다.


### 사용 예시

#### 1. 배열 결합
```javascript
const arr1 = [1, 2];
const arr2 = [3, 4];
const combined = [...arr1, ...arr2]; // [1, 2, 3, 4]
```

#### 2. 객체 결합 
```javascript
const obj1 = { a: 1 };
const obj2 = { b: 2 };
const merged = { ...obj1, ...obj2 }; // { a: 1, b: 2 }
```

<br>

### 주의사항
-  객체 병합: 동일한 속성이 있을 경우, 나중에 나오는 객체의 속성이 우선합니다.
```javascript
const obj1 = { a: 1 };
const obj2 = { a: 2, b: 2 };
const merged = { ...obj1, ...obj2 }; // { a: 2, b: 2 }
```