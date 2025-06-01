
# JavaScript에서 2진수, 10진수, 16진수 다루기 ✨

JavaScript에서 다양한 숫자 시스템(2진수, 10진수, 16진수)을 다루는 방법과 `Buffer.from()` 같은 기능을 활용하는 법을 자세히 살펴보겠습니다.

## 1. 숫자 변환 방법 🔢

JavaScript에서는 `toString()`과 `parseInt()`를 사용하여 숫자 변환이 가능합니다.

### 👉🏻 10진수를 2진수, 16진수로 변환
```js
let num = 255;

console.log(num.toString(2));  // "11111111" (2진수)
console.log(num.toString(16)); // "ff" (16진수)
```
- `toString(2)`: 10진수를 2진수로 변환
- `toString(16)`: 10진수를 16진수로 변환

---

### 👉🏻 2진수, 16진수를 10진수로 변환
```js
let binary = "1010";
let hex = "1f";

console.log(parseInt(binary, 2)); // 10 (2진수를 10진수로 변환)
console.log(parseInt(hex, 16));   // 31 (16진수를 10진수로 변환)
```
- `parseInt(문자열, 진수)`: 문자열을 특정 진수에서 10진수로 변환

---

## 2. 비트 연산 활용 (2진수 다루기) 🔧

비트 연산자를 활용하면 2진수 연산이 가능합니다.

```js
let a = 5;  // 0101 (2진수)
let b = 3;  // 0011 (2진수)

console.log(a & b);  // 1  (AND 연산)
console.log(a | b);  // 7  (OR 연산)
console.log(a ^ b);  // 6  (XOR 연산)
console.log(~a);     // -6 (NOT 연산)
console.log(a << 1); // 10 (왼쪽 시프트)
console.log(a >> 1); // 2  (오른쪽 시프트)
```
- `&`: AND 연산
- `|`: OR 연산
- `^`: XOR 연산
- `~`: NOT 연산
- `<<`: 왼쪽 시프트
- `>>`: 오른쪽 시프트

---

## 3. `Buffer`를 사용한 데이터 변환

### 👉🏻 `Buffer.from()`으로 16진수 다루기
```js
let buf = Buffer.from("48656c6c6f", "hex");
console.log(buf.toString());  // "Hello"
```
- `"48656c6c6f"`: 16진수로 표현된 문자열
- `Buffer.from(문자열, "hex")`: 16진수 데이터를 버퍼로 변환 후 문자열로 변환

---

### 👉🏻 `Buffer`를 사용하여 2진수 변환
```js
let buf = Buffer.from([0b01001000, 0b01001001]);  // 2진수로 표현된 ASCII 코드
console.log(buf.toString());  // "HI"
```
- `[0b01001000, 0b01001001]`: 2진수로 표현된 ASCII 코드
- `Buffer.from(배열)`: 2진수를 버퍼로 변환 후 문자열로 변환

---

## 4. `Number` 객체와 16진수 변환

### 👉🏻 `Number.prototype.toString()` 활용
```js
let num = 255;
console.log(num.toString(16)); // "ff" (10진수를 16진수로 변환)
```

### 👉🏻 16진수를 `Number`로 변환
```js
let hexNum = "0xff";
console.log(Number(hexNum)); // 255
```

---

## 5. `BigInt`를 활용한 큰 숫자 변환

JavaScript에서 `BigInt`는 매우 큰 숫자를 다룰 때 유용합니다.

```js
let bigNum = BigInt("0x123456789abcdef");  // 16진수 BigInt
console.log(bigNum.toString(10)); // 81985529216486895 (10진수 변환)
```

---

# 결론 🏁

- **2진수 변환**: `.toString(2)`, `parseInt(값, 2)`
- **16진수 변환**: `.toString(16)`, `parseInt(값, 16)`
- **비트 연산**: `&`, `|`, `^`, `~`, `<<`, `>>`
- **Buffer 활용**: `Buffer.from(데이터, "hex")`
- **BigInt 활용**: `BigInt("0x값")`

✨ 다양한 방식으로 숫자를 변환하고 조작할 수 있습니다! 필요한 곳에 적절하게 활용하세요. 🚀
