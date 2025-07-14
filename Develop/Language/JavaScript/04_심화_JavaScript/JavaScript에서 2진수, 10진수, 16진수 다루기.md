# JavaScript에서 2진수, 10진수, 16진수 다루기

> 💡 **이 글을 읽기 전에 알아야 할 것들**
> - JavaScript 기본 문법 (변수, 함수, 콘솔 출력)
> - 숫자와 문자열의 기본 개념

---

## 📚 숫자 체계란?

우리가 일상에서 사용하는 숫자는 **10진수**입니다. 하지만 컴퓨터는 **2진수**를 기본으로 사용하고, 프로그래밍에서는 **16진수**도 자주 사용됩니다.

### 각 진수의 특징
- **10진수**: 0~9까지의 숫자 사용 (우리가 일상에서 사용)
- **2진수**: 0과 1만 사용 (컴퓨터가 이해하는 방식)
- **16진수**: 0~9와 A~F 사용 (프로그래밍에서 자주 사용)

---

## 🔢 기본 숫자 변환하기

### 10진수를 다른 진수로 변환하기

```js
// 10진수 숫자
let number = 255;

// 10진수를 2진수로 변환
let binary = number.toString(2);
console.log(binary); // "11111111"

// 10진수를 16진수로 변환  
let hexadecimal = number.toString(16);
console.log(hexadecimal); // "ff"

// 10진수를 8진수로 변환 (참고용)
let octal = number.toString(8);
console.log(octal); // "377"
```

**설명**: `toString(진수)` 메서드는 숫자를 지정한 진수로 변환해줍니다.

### 다른 진수를 10진수로 변환하기

```js
// 2진수 문자열
let binaryString = "1010";
let decimalFromBinary = parseInt(binaryString, 2);
console.log(decimalFromBinary); // 10

// 16진수 문자열
let hexString = "1f";
let decimalFromHex = parseInt(hexString, 16);
console.log(decimalFromHex); // 31

// 8진수 문자열 (참고용)
let octalString = "17";
let decimalFromOctal = parseInt(octalString, 8);
console.log(decimalFromOctal); // 15
```

**설명**: `parseInt(문자열, 진수)`는 문자열을 특정 진수로 해석해서 10진수로 변환합니다.

---

## ⚡ 비트 연산자로 2진수 다루기

비트 연산자는 숫자를 2진수로 변환해서 각 자릿수별로 연산을 수행합니다.

### 기본 비트 연산자들

```js
let a = 5;  // 2진수로는 0101
let b = 3;  // 2진수로는 0011

// AND 연산 (&) - 둘 다 1일 때만 1
console.log(a & b);  // 1 (0101 & 0011 = 0001)

// OR 연산 (|) - 둘 중 하나라도 1이면 1  
console.log(a | b);  // 7 (0101 | 0011 = 0111)

// XOR 연산 (^) - 둘이 다를 때만 1
console.log(a ^ b);  // 6 (0101 ^ 0011 = 0110)

// NOT 연산 (~) - 모든 비트를 뒤집음
console.log(~a);     // -6 (0101 → 1010, 음수로 표현)

// 왼쪽 시프트 (<<) - 비트를 왼쪽으로 이동
console.log(a << 1); // 10 (0101 → 1010)

// 오른쪽 시프트 (>>) - 비트를 오른쪽으로 이동
console.log(a >> 1); // 2 (0101 → 0010)
```

### 비트 연산자의 실제 활용 예시

```js
// 플래그(flag) 설정하기
const READ = 1;      // 0001
const WRITE = 2;     // 0010  
const EXECUTE = 4;   // 0100

// 권한 설정
let permissions = READ | WRITE; // 0011 (읽기 + 쓰기 권한)
console.log(permissions); // 3

// 권한 확인
console.log(permissions & READ);    // 1 (읽기 권한 있음)
console.log(permissions & EXECUTE); // 0 (실행 권한 없음)

// 권한 추가
permissions = permissions | EXECUTE; // 0111 (실행 권한 추가)
console.log(permissions); // 7
```

---

## 📦 Buffer로 데이터 변환하기

Buffer는 Node.js에서 바이너리 데이터를 다룰 때 사용하는 클래스입니다.

### 16진수 문자열을 일반 문자열로 변환

```js
// 16진수로 표현된 "Hello" 문자열
let hexString = "48656c6c6f";

// Buffer로 변환 후 문자열로 출력
let buffer = Buffer.from(hexString, "hex");
console.log(buffer.toString()); // "Hello"

// 각 문자의 ASCII 코드 확인
console.log(buffer); // <Buffer 48 65 6c 6c 6f>
```

**설명**: 
- `"48656c6c6f"`는 "Hello"를 16진수로 표현한 것입니다
- `Buffer.from(문자열, "hex")`는 16진수 문자열을 바이너리 데이터로 변환합니다
- `buffer.toString()`은 바이너리 데이터를 다시 문자열로 변환합니다

### 2진수 배열을 문자열로 변환

```js
// ASCII 코드를 2진수로 표현
let binaryArray = [0b01001000, 0b01001001]; // "HI"의 ASCII 코드

// Buffer로 변환
let buffer2 = Buffer.from(binaryArray);
console.log(buffer2.toString()); // "HI"

// 각 문자의 10진수 값 확인
console.log(buffer2[0]); // 72 (H의 ASCII 코드)
console.log(buffer2[1]); // 73 (I의 ASCII 코드)
```

**설명**: `0b`는 JavaScript에서 2진수를 표현하는 방법입니다.

---

## 🔢 Number 객체 활용하기

### 16진수 리터럴 사용하기

```js
// 16진수로 숫자 표현
let hexNumber = 0xff; // 255
console.log(hexNumber); // 255

// 16진수 문자열을 숫자로 변환
let hexString2 = "0xff";
let numberFromHex = Number(hexString2);
console.log(numberFromHex); // 255

// parseInt 사용
let numberFromHex2 = parseInt("ff", 16);
console.log(numberFromHex2); // 255
```

### 다양한 진수 표현 방법

```js
let num = 255;

// 다양한 진수로 변환
console.log(num.toString(2));   // "11111111" (2진수)
console.log(num.toString(8));   // "377" (8진수)
console.log(num.toString(10));  // "255" (10진수)
console.log(num.toString(16));  // "ff" (16진수)

// 대문자로 16진수 표현
console.log(num.toString(16).toUpperCase()); // "FF"
```

---

## 🚀 BigInt로 큰 숫자 다루기

일반적인 JavaScript 숫자는 약 2^53까지 표현할 수 있습니다. 더 큰 숫자는 `BigInt`를 사용해야 합니다.

```js
// 일반 숫자의 한계
console.log(Number.MAX_SAFE_INTEGER); // 9007199254740991

// BigInt 사용하기
let bigNumber = BigInt("0x123456789abcdef");
console.log(bigNumber.toString(10)); // "81985529216486895"

// BigInt 연산
let bigA = BigInt(100);
let bigB = BigInt(200);
console.log(bigA + bigB); // 300n

// 일반 숫자와 BigInt는 직접 연산 불가
// console.log(100 + bigA); // TypeError 발생
console.log(100 + Number(bigA)); // 200 (BigInt를 일반 숫자로 변환)
```

---

## 💡 실무에서 자주 사용하는 패턴들

### 색상 코드 변환하기

```js
// RGB 색상을 16진수로 변환
function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? "0" + hex : hex;
    }).join("");
}

console.log(rgbToHex(255, 0, 0)); // "#ff0000" (빨간색)

// 16진수 색상을 RGB로 변환
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

console.log(hexToRgb("#ff0000")); // {r: 255, g: 0, b: 0}
```

### 파일 크기 변환하기

```js
// 바이트를 읽기 쉬운 형태로 변환
function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

console.log(formatBytes(1024));     // "1 KB"
console.log(formatBytes(1048576));  // "1 MB"
console.log(formatBytes(1073741824)); // "1 GB"
```

---

## 📝 정리

### 주요 메서드들
- **`toString(진수)`**: 숫자를 다른 진수로 변환
- **`parseInt(문자열, 진수)`**: 문자열을 특정 진수에서 10진수로 변환
- **`Buffer.from(데이터, "hex")`**: 16진수 데이터를 바이너리로 변환

### 비트 연산자들
- **`&`**: AND 연산
- **`|`**: OR 연산  
- **`^`**: XOR 연산
- **`~`**: NOT 연산
- **`<<`**: 왼쪽 시프트
- **`>>`**: 오른쪽 시프트

### 진수 표현 방법
- **2진수**: `0b` 접두사 또는 `toString(2)`
- **8진수**: `0o` 접두사 또는 `toString(8)`
- **16진수**: `0x` 접두사 또는 `toString(16)`

