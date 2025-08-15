---
title: TypeScript number 타입 완벽 가이드
tags: [language, typescript, 타입-및-타입-정의, typescript-types, primitive-types, number]
updated: 2025-08-10
---

# TypeScript number 타입 완벽 가이드

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

## 참고

### number 타입 특성

| 특성 | 설명 | 예시 |
|------|------|------|
| **정밀도** | 64비트 부동소수점 | 0.1 + 0.2 ≠ 0.3 |
| **범위** | ±2^53 - 1 | Number.MAX_SAFE_INTEGER |
| **특수값** | NaN, Infinity, -Infinity | 0/0, 1/0, -1/0 |
| **타입 체크** | typeof 연산자 | typeof 42 === 'number' |

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

