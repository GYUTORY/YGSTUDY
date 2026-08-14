---
title: TypeScript number 타입
tags: [language, typescript, javascript]
updated: 2025-08-10
---

# TypeScript number 타입
## 배경

TypeScript에서 `number` 타입은 숫자 값을 나타내는 기본 데이터 타입입니다.

### number 타입의 필요성
- **수치 연산**: 덧셈, 뺄셈, 곱셈, 나눗셈 등 기본 연산
- **반복문**: for 루프의 카운터 변수
- **수학 함수**: Math 객체의 다양한 수학 함수 사용
- **API 응답**: 숫자 형태의 데이터 처리

### 기본 개념
- **정수**: 소수점이 없는 숫자 (예: 42, -10, 0)
- **부동소수점**: 소수점이 있는 숫자 (예: 3.14, -2.5)
- **64비트**: IEEE 754 표준을 따르는 64비트 부동소수점
- **특수값**: Infinity, -Infinity, NaN

## 핵심

### 1. number 타입 기본 사용법

#### 변수 선언과 초기화
```typescript
// 정수 값
let age: number = 25;
let count: number = 0;
let negative: number = -10;

// 부동소수점 값
let price: number = 29.99;
let pi: number = 3.14159;
let temperature: number = -5.5;

// 지수 표기법
let largeNumber: number = 1e6; // 1,000,000
let smallNumber: number = 1e-6; // 0.000001
```

#### 기본 연산
```typescript
let a: number = 10;
let b: number = 3;

// 기본 사칙연산
let sum: number = a + b;        // 13
let difference: number = a - b;  // 7
let product: number = a * b;     // 30
let quotient: number = a / b;    // 3.333...

// 나머지 연산
let remainder: number = a % b;   // 1

// 거듭제곱
let power: number = a ** b;      // 1000
```

### 2. Math 객체 활용

#### 수학 함수 사용
```typescript
let value: number = 3.7;

// 반올림
let rounded: number = Math.round(value);    // 4

// 올림
let ceiling: number = Math.ceil(value);     // 4

// 내림
let floor: number = Math.floor(value);      // 3

// 절댓값
let absolute: number = Math.abs(-5);        // 5

// 제곱근
let sqrt: number = Math.sqrt(16);           // 4

// 최대값, 최소값
let max: number = Math.max(1, 2, 3, 4, 5);  // 5
let min: number = Math.min(1, 2, 3, 4, 5);  // 1
```

#### 랜덤 숫자 생성
```typescript
// 0과 1 사이의 랜덤 숫자
let random: number = Math.random();

// 1과 10 사이의 정수
let randomInt: number = Math.floor(Math.random() * 10) + 1;

// 특정 범위의 랜덤 숫자
function getRandomNumber(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

let diceRoll: number = getRandomNumber(1, 6); // 주사위 굴리기
```

### 3. 특수 값과 처리

#### NaN (Not a Number)
```typescript
// NaN 생성
let result1: number = 0 / 0;           // NaN
let result2: number = parseInt("abc"); // NaN

// NaN 체크
console.log(isNaN(result1));           // true
console.log(Number.isNaN(result1));    // true

// NaN과의 비교
console.log(NaN === NaN);              // false
console.log(Object.is(NaN, NaN));      // true
```

이 예제에서 놓치기 쉬운 게 첫 두 줄이다. **`NaN` 의 타입은 `number` 다.** `let result1: number = 0 / 0` 이 타입 에러 없이 통과하는 건 실수가 아니라 설계다. 그래서 `number` 로 선언해 뒀다는 사실이 그 값이 계산에 쓸 만하다는 걸 전혀 보장하지 않는다. `Infinity` 도 마찬가지다.

```typescript
function f(n: number) { return n * 2; }
f(NaN);       // 컴파일 통과
f(Infinity);  // 컴파일 통과
```

타입 검사기는 여기서 아무 일도 안 한다. 방어는 전부 런타임 검사로 해야 한다.

`isNaN` 과 `Number.isNaN` 은 같은 걸 확인하는 두 방법이 아니다. **전역 `isNaN` 은 인자를 먼저 숫자로 변환한 뒤 판정한다.**

```javascript
isNaN('abc')          // true   ← 'abc' 는 NaN 이 아니라 문자열이다
Number.isNaN('abc')   // false  ← 이쪽이 질문에 정확히 답한다
isNaN(undefined)      // true
isNaN('')             // false  ← 빈 문자열은 0 으로 변환된다
isNaN([])             // false  ← 빈 배열도 0
```

"이 값이 NaN 인가"를 묻는 자리에는 `Number.isNaN` 을 쓴다. 전역 `isNaN` 이 답하는 질문은 "이 값을 숫자로 바꾸면 NaN 이 되는가"이고, 이건 대개 묻고 싶었던 게 아니다.

#### Infinity 처리
```typescript
// 무한대 값
let positiveInfinity: number = Infinity;
let negativeInfinity: number = -Infinity;

// 무한대 체크
console.log(Number.isFinite(positiveInfinity)); // false
console.log(Number.isFinite(42));               // true

// 안전한 나눗셈
function safeDivide(a: number, b: number): number {
    if (b === 0) {
        throw new Error("0으로 나눌 수 없습니다.");
    }
    return a / b;
}
```

`safeDivide` 는 이름만큼 안전하지 않다. `b === 0` 만 막으므로 `NaN` 이 그대로 빠져나간다.

```javascript
safeDivide(1, NaN)     // NaN  ← 예외 없이 NaN 을 리턴한다
safeDivide(NaN, 2)     // NaN
safeDivide(1, -0)      // 예외  ← -0 === 0 이 true 라 이건 잡힌다
```

`NaN` 은 여기서 조용히 통과한 뒤 이후 모든 계산을 오염시킨다. 예외로 멈추는 것보다 나쁜데, 터진 지점과 원인 지점이 멀어지기 때문이다. 반면 `-0` 은 `-0 === 0` 이 `true` 라 가드에 걸린다 — 이쪽은 걱정하지 않아도 된다.

입력을 하나씩 열거하는 대신 **결과가 유한한지** 보면 검사 하나로 전부 잡힌다.

```typescript
function safeDivide(a: number, b: number): number {
    const result = a / b;
    if (!Number.isFinite(result)) {
        throw new Error("나눗셈 결과가 유한하지 않습니다.");
    }
    return result;
}
```

`Number.isFinite` 는 `NaN` · `Infinity` · `-Infinity` 를 한꺼번에 걸러낸다. 전역 `isFinite` 는 앞서 `isNaN` 과 같은 이유로 인자를 숫자 변환부터 하니 `Number.` 붙은 쪽을 쓴다.

## 예시

### 1. 실제 사용 사례

#### 계산기 함수
```typescript
interface Calculator {
    add(a: number, b: number): number;
    subtract(a: number, b: number): number;
    multiply(a: number, b: number): number;
    divide(a: number, b: number): number;
    power(base: number, exponent: number): number;
}

class SimpleCalculator implements Calculator {
    add(a: number, b: number): number {
        return a + b;
    }

    subtract(a: number, b: number): number {
        return a - b;
    }

    multiply(a: number, b: number): number {
        return a * b;
    }

    divide(a: number, b: number): number {
        if (b === 0) {
            throw new Error("0으로 나눌 수 없습니다.");
        }
        return a / b;
    }

    power(base: number, exponent: number): number {
        return Math.pow(base, exponent);
    }
}

// 사용 예시
const calc = new SimpleCalculator();
console.log(calc.add(5, 3));      // 8
console.log(calc.multiply(4, 7)); // 28
console.log(calc.power(2, 8));    // 256
```

#### 통계 계산
```typescript
class Statistics {
    static mean(numbers: number[]): number {
        if (numbers.length === 0) {
            throw new Error("빈 배열입니다.");
        }
        const sum = numbers.reduce((acc, num) => acc + num, 0);
        return sum / numbers.length;
    }

    static median(numbers: number[]): number {
        if (numbers.length === 0) {
            throw new Error("빈 배열입니다.");
        }
        
        const sorted = [...numbers].sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        
        if (sorted.length % 2 === 0) {
            return (sorted[mid - 1] + sorted[mid]) / 2;
        } else {
            return sorted[mid];
        }
    }

    static standardDeviation(numbers: number[]): number {
        if (numbers.length === 0) {
            throw new Error("빈 배열입니다.");
        }
        
        const mean = Statistics.mean(numbers);
        const squaredDifferences = numbers.map(num => Math.pow(num - mean, 2));
        const variance = Statistics.mean(squaredDifferences);
        
        return Math.sqrt(variance);
    }
}

// 사용 예시
const scores = [85, 92, 78, 96, 88, 90];
console.log(`평균: ${Statistics.mean(scores).toFixed(2)}`);
console.log(`중앙값: ${Statistics.median(scores)}`);
console.log(`표준편차: ${Statistics.standardDeviation(scores).toFixed(2)}`);
```

### 2. 고급 패턴

#### 숫자 유효성 검사
```typescript
function isValidNumber(value: unknown): value is number {
    return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

function validatePercentage(value: number): number {
    if (!isValidNumber(value)) {
        throw new Error("유효하지 않은 숫자입니다.");
    }
    
    if (value < 0 || value > 100) {
        throw new Error("퍼센트는 0과 100 사이여야 합니다.");
    }
    
    return value;
}

// 사용 예시
try {
    const percentage = validatePercentage(75);
    console.log(`${percentage}%`);
} catch (error) {
    console.error(error.message);
}
```

**이 catch 블록은 `strict` 에서 컴파일되지 않는다.** TypeScript 4.4 부터 `useUnknownInCatchVariables`(strict 에 포함)가 켜지면 catch 변수의 타입이 `any` 가 아니라 `unknown` 이다.

```
error TS18046: 'error' is of type 'unknown'.
```

`throw` 는 어떤 값이든 던질 수 있으니 맞는 판정이다. 문자열도, `undefined` 도 던져진다. 좁혀서 쓴다.

```typescript
} catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
}
```

`isValidNumber` 쪽은 잘 만들어져 있다. `value is number` 라는 타입 술어 덕에 호출한 쪽에서 타입이 좁혀지고, `typeof` → `isNaN` → `isFinite` 순서라 `isNaN` 이 문자열을 변환해 버리는 문제도 피한다. 앞의 `typeof value === 'number'` 가 이미 문자열을 걸러냈기 때문이다. 순서를 바꾸면 그 보호가 사라진다.

#### 숫자 포맷팅
```typescript
class NumberFormatter {
    static formatCurrency(amount: number, currency: string = 'KRW'): string {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    static formatPercentage(value: number, decimals: number = 2): string {
        return `${value.toFixed(decimals)}%`;
    }

    static formatNumber(value: number, locale: string = 'ko-KR'): string {
        return new Intl.NumberFormat(locale).format(value);
    }
}

// 사용 예시
console.log(NumberFormatter.formatCurrency(1234567));     // ₩1,234,567
console.log(NumberFormatter.formatPercentage(85.6789));  // 85.68%
console.log(NumberFormatter.formatNumber(1234567));      // 1,234,567
```

## 운영 팁

### 성능 최적화

#### 정수 연산 최적화
```typescript
// 부동소수점 연산 대신 정수 연산 사용
function calculateTax(amount: number, rate: number): number {
    // 부동소수점 오차를 피하기 위해 정수로 계산
    const taxAmount = Math.round(amount * rate * 100) / 100;
    return taxAmount;
}

// 비트 연산 활용
function isEven(num: number): boolean {
    return (num & 1) === 0;
}

function isPowerOfTwo(num: number): boolean {
    return num > 0 && (num & (num - 1)) === 0;
}
```

이 절의 세 함수 모두 주석이 약속한 것을 지키지 않는다.

**`calculateTax` 는 부동소수점 오차를 피하지 못한다.** 주석은 "정수로 계산"한다고 하지만 `amount * rate * 100` 이 이미 부동소수점 곱셈이다. `Math.round` 는 그 오차가 생긴 **뒤에** 호출된다.

```javascript
1.005 * 100                    // 100.49999999999999  ← 여기서 이미 틀렸다
Math.round(100.49999999999999) // 100
calculateTax(1.005, 1)         // 1     ← 기대값 1.01
```

세율 계산에서 1원이 어긋나는 전형적인 형태다. 진짜로 피하려면 금액을 처음부터 최소 단위 정수(원, 센트)로 들고 다니거나 `Decimal` 계열 라이브러리를 쓴다. 곱한 뒤에 반올림하는 건 오차를 줄이는 게 아니라 **감추는** 것이다.

**`isEven` 은 정수가 아닌 입력에서 틀린 답을 한다.** 비트 연산자는 피연산자를 32비트 정수로 변환(`ToInt32`)하는데, 이 변환이 소수부를 버리고 `NaN` 을 0 으로 만든다.

```javascript
isEven(2.5)   // true   ← 2.5 는 짝수가 아니다
isEven(NaN)   // true   ← NaN 은 짝수도 홀수도 아니다
```

큰 정수는 걱정하지 않아도 된다. `ToInt32` 는 2³² 로 나눈 나머지를 취하는데 2³² 가 짝수라 **홀짝은 보존된다.** 안전 정수 범위 안이면 `isEven(2**53)` 까지 정확하다. 문제는 오직 정수가 아닌 입력이다. 앞서 만든 `isValidNumber` 로 거르거나 `Number.isInteger(num) && num % 2 === 0` 을 쓴다.

**`isPowerOfTwo` 는 2³¹ 을 넘으면 오답을 낸다.** 이쪽은 `ToInt32` 가 홀짝처럼 보존해 주는 성질이 없다.

```javascript
isPowerOfTwo(3 * 2**32)   // true   ← 12884901888 = 3 × 2³², 2의 거듭제곱이 아니다
Math.log2(3 * 2**32)      // 33.584962500721154
isPowerOfTwo(5 * 2**32)   // true   ← 역시 오답
```

`3 * 2**32` 의 하위 32비트가 전부 0 이라 `ToInt32` 가 `0` 을 내놓고, `0 & -1 === 0` 이 성립해 통과한다. 32비트를 넘는 값을 다룰 가능성이 있으면 비트 연산 대신 로그나 나눗셈으로 판정한다.

```typescript
function isPowerOfTwo(num: number): boolean {
    return Number.isInteger(num) && num > 0 && Math.log2(num) % 1 === 0;
}
```

이 버전은 2⁰ ~ 2⁵² 전 구간과 위 오답 사례를 전부 맞힌다. 다만 이쪽도 만능은 아니라서 안전 정수 범위를 넘기면 `isPowerOfTwo(2**53 + 2)` 가 `true` 로 나온다 — `log2` 결과가 53 으로 반올림되기 때문이다. 그 위까지 정확해야 하면 `BigInt` 로 간다.

정리하면 **비트 연산은 32비트 정수 위에서만 정의된 최적화**다. JavaScript 의 `number` 는 그보다 넓으니, 입력 범위를 스스로 보증할 수 있을 때만 쓴다.

### 에러 처리

#### 안전한 숫자 변환
```typescript
function safeParseInt(value: string, defaultValue: number = 0): number {
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? defaultValue : parsed;
}

function safeParseFloat(value: string, defaultValue: number = 0): number {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? defaultValue : parsed;
}

// 사용 예시
const userInput = "abc";
const number = safeParseInt(userInput, 0); // 0 반환
```

`"abc"` 처럼 완전히 틀린 입력은 잡히지만, **부분적으로 숫자인 입력이 조용히 통과한다.** `parseInt` 는 앞에서부터 읽다가 숫자가 아닌 문자를 만나면 거기서 멈추고 그때까지 읽은 값을 돌려준다. `NaN` 이 아니니 기본값 대체도 일어나지 않는다.

```javascript
safeParseInt('12abc')        // 12        ← 오류로 보고되지 않는다
safeParseFloat('1.2.3')      // 1.2       ← 두 번째 점부터 버린다
safeParseFloat('Infinity')   // Infinity  ← NaN 이 아니라 통과한다
safeParseFloat('1e999')      // Infinity
```

`safeParseFloat('Infinity')` 가 특히 나쁘다. 이후 계산이 전부 `Infinity` 나 `NaN` 이 되는데 함수 이름은 "safe" 다.

여기에 `parseInt` 만의 함정이 하나 더 있다. **인자를 문자열로 읽기 때문에 지수 표기가 잘린다.**

```javascript
parseInt('0.0000005')   // 0     ← 문자열 '0.0000005' 의 '0' 까지만 읽는다
Number('0.0000005')     // 5e-7
String(0.0000005)       // '5e-7' → parseInt 는 여기서 5 를 읽는다
```

문자열 전체가 하나의 숫자여야 한다면 `parseInt` 가 아니라 `Number()` 를 쓴다. `Number()` 는 부분 파싱을 하지 않아 `Number('12abc')` 가 `NaN` 이다. 대신 빈 문자열과 공백을 `0` 으로 바꾸는 다른 함정이 있다(`Number('')` → `0`, `Number(' ')` → `0`, `Number(null)` → `0`). 그래서 사용자 입력에는 빈 값 검사를 앞에 둔다.

```typescript
function toNumber(value: string, defaultValue = 0): number {
    if (value.trim() === '') return defaultValue;
    const n = Number(value);
    return Number.isFinite(n) ? n : defaultValue;
}
// '12abc' → 0,  '' → 0,  'Infinity' → 0,  '0.0000005' → 5e-7
```

`parseInt` 가 맞는 자리는 `"16px"` 처럼 **뒤에 단위가 붙는 걸 알고 있을 때**다. 그때는 부분 파싱이 결함이 아니라 기능이다. 그리고 이 예제처럼 두 번째 인자 `10` 은 항상 넘긴다.

## 참고

### number 타입 특성

| 특성 | 설명 | 예시 |
|------|------|------|
| **정밀도** | 64비트 부동소수점 | 0.1 + 0.2 ≠ 0.3 |
| **범위** | ±2^53 - 1 | Number.MAX_SAFE_INTEGER |
| **특수값** | NaN, Infinity, -Infinity | 0/0, 1/0, -1/0 |
| **타입 체크** | typeof 연산자 | typeof 42 === 'number' |

표의 "범위 ±2^53 - 1" 은 **표현 가능한 최댓값이 아니라 정수를 정확히 구별할 수 있는 한계**다. 둘은 자릿수가 크게 다르다.

```javascript
Number.MAX_SAFE_INTEGER   // 9007199254740991     = 2^53 - 1
Number.MAX_VALUE          // 1.7976931348623157e+308
```

`MAX_SAFE_INTEGER` 를 넘으면 값을 저장은 하는데 서로 다른 정수가 같은 값으로 뭉개진다.

```javascript
9007199254740993          // 9007199254740992  ← 리터럴이 이미 바뀐다
Number.MAX_SAFE_INTEGER + 1 === Number.MAX_SAFE_INTEGER + 2   // true
```

실무에서 이게 터지는 자리는 정해져 있다. **서버가 64비트 정수 ID 를 JSON 숫자로 내려보낼 때**다. DB 의 `BIGINT` 는 2⁶³ 까지 가는데 `JSON.parse` 는 `number` 로 받으므로, 2⁵³ 을 넘는 ID 는 조용히 다른 ID 가 된다. 예외도 경고도 없다. 그래서 큰 정수 ID 는 API 경계에서 **문자열로 주고받는 게 표준적인 해법**이다. 계산이 필요하면 `BigInt` 를 쓴다.

정밀도 행의 `0.1 + 0.2 ≠ 0.3` 도 같은 뿌리다. 2진 부동소수점은 0.1 을 정확히 표현하지 못한다.

```javascript
0.1 + 0.2                    // 0.30000000000000004
(0.1 + 0.2).toFixed(20)      // "0.30000000000000004441"
```

돈을 다루는 코드에서 `number` 로 원 단위 실수를 더하면 이 오차가 쌓인다. 최소 단위 정수로 저장하는 게 정석이다.

### 숫자 관련 유틸리티

```typescript
// 안전한 정수 범위 체크
function isSafeInteger(num: number): boolean {
    return Number.isSafeInteger(num);
}

// 유한한 숫자 체크
function isFiniteNumber(num: number): boolean {
    return Number.isFinite(num);
}

// 정수 체크
function isInteger(num: number): boolean {
    return Number.isInteger(num);
}
```

### 결론
TypeScript의 number 타입은 수치 연산과 계산을 위한 핵심 데이터 타입입니다.
Math 객체의 다양한 함수를 활용하여 복잡한 수학 연산을 수행할 수 있습니다.
NaN, Infinity 등 특수 값에 대한 적절한 처리가 중요합니다.
부동소수점 연산의 정밀도 한계를 이해하고 필요시 정수 연산을 활용하세요.
숫자 데이터의 유효성 검사와 안전한 변환을 통해 런타임 오류를 방지하세요.

