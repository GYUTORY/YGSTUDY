---
title: JavaScript Truthy와 Falsy
tags: [language, javascript, 09es6및고급문법, truthy, falsy, boolean-conversion]
updated: 2025-12-19
---

# JavaScript Truthy와 Falsy

## 정의

JavaScript에서는 모든 값이 조건문에서 참(true) 또는 거짓(false)으로 평가됩니다.

- **Truthy**: 조건문에서 `true`로 평가되는 값
- **Falsy**: 조건문에서 `false`로 평가되는 값

## 동작 원리

### Falsy 값들

JavaScript에서 falsy로 평가되는 값은 정확히 8가지입니다:

```javascript
const falsyValues = [
    false,      // 불린 false
    0,          // 숫자 0
    -0,         // 음수 0
    0n,         // BigInt 0
    '',         // 빈 문자열
    null,       // null
    undefined,  // undefined
    NaN         // Not a Number
];

// 모든 falsy 값 확인
falsyValues.forEach(value => {
    console.log(`${value} is falsy:`, !value);
});
```

### Truthy 값들

Falsy가 아닌 모든 값은 truthy입니다:

```javascript
// 주의할 점
if ('0') console.log('문자열 0은 truthy');     // 실행됨
if (' ') console.log('공백 문자열도 truthy');   // 실행됨
if ([]) console.log('빈 배열은 truthy');        // 실행됨
if ({}) console.log('빈 객체는 truthy');        // 실행됨
```

## 사용법

### 타입 변환

**명시적 변환**
```javascript
// Boolean() 함수 사용
console.log(Boolean(0));       // false
console.log(Boolean(''));      // false
console.log(Boolean(null));    // false
console.log(Boolean(42));      // true
console.log(Boolean('hello')); // true
console.log(Boolean([]));      // true

// 이중 부정 연산자 !!
console.log(!!0);     // false
console.log(!!'');    // false
console.log(!!42);    // true
console.log(!!'text'); // true
```

**암시적 변환**
```javascript
// 조건문에서의 암시적 변환
let value = 0;
if (value) {
    console.log('이 코드는 실행되지 않음');
}

// OR 연산자 (||) - 첫 번째 truthy 값을 반환
console.log(0 || '기본값');      // '기본값'
console.log('' || '기본값');     // '기본값'
console.log('실제값' || '기본값'); // '실제값'

// AND 연산자 (&&) - 첫 번째 falsy 값 또는 마지막 truthy 값
console.log(0 && '실행되지 않음');    // 0
console.log('실행됨' && '마지막값');  // '마지막값'
```

## 예제

### 기본값 설정

```javascript
function greetUser(name) {
    const displayName = name || '손님';
    return `안녕하세요, ${displayName}님!`;
}

console.log(greetUser('홍길동')); // '안녕하세요, 홍길동님!'
console.log(greetUser(''));       // '안녕하세요, 손님님!'
console.log(greetUser(null));     // '안녕하세요, 손님님!'

// 객체 속성의 기본값 설정
function createUser(userData) {
    return {
        name: userData.name || '이름 없음',
        age: userData.age || 0,
        email: userData.email || '이메일 없음'
    };
}
```

### 조건부 실행

```javascript
// 조건부 함수 실행
function displayMessage(message) {
    message && console.log(message);
}

displayMessage('안녕하세요!'); // '안녕하세요!' 출력
displayMessage('');           // 아무것도 출력되지 않음
displayMessage(null);         // 아무것도 출력되지 않음

// 조건부 객체 속성 설정
function createConfig(options = {}) {
    return {
        host: 'localhost',
        port: 3000,
        ...(options.debug && { logLevel: 'debug' }),
        ...(options.ssl && { protocol: 'https' })
    };
}

console.log(createConfig({ debug: true }));
```

### 배열 필터링

```javascript
// falsy 값 제거
function removeFalsyValues(array) {
    return array.filter(Boolean);
}

const mixedArray = [0, 1, false, 2, '', 3, null, 4, undefined, 5, NaN];
const truthyArray = removeFalsyValues(mixedArray);
console.log(truthyArray); // [1, 2, 3, 4, 5]
```

### 단축 평가 (Short-circuit evaluation)

```javascript
const user = {
    profile: {
        name: '홍길동',
        settings: {
            theme: 'dark'
        }
    }
};

// 안전한 속성 접근 (옵셔널 체이닝 이전 방식)
const theme = user && user.profile && user.profile.settings && user.profile.settings.theme;
console.log(theme); // 'dark'

// 옵셔널 체이닝 사용 (모던 방식)
const theme2 = user?.profile?.settings?.theme;
console.log(theme2); // 'dark'

// 기본값과 함께 사용
const displayName = user?.profile?.name || '이름 없음';
console.log(displayName); // '홍길동'
```

## 참고

### 값 검증 유틸리티

```javascript
class ValueValidator {
    static isTruthy(value) {
        return Boolean(value);
    }

    static isFalsy(value) {
        return !Boolean(value);
    }

    static hasValue(value) {
        return value !== null && value !== undefined && value !== '';
    }

    static isNotEmpty(value) {
        if (Array.isArray(value)) return value.length > 0;
        if (typeof value === 'string') return value.trim().length > 0;
        if (typeof value === 'object' && value !== null) return Object.keys(value).length > 0;
        return Boolean(value);
    }

    static getDefaultIfFalsy(value, defaultValue) {
        return value || defaultValue;
    }
}

// 사용 예시
console.log(ValueValidator.isTruthy(0));           // false
console.log(ValueValidator.hasValue(''));          // false
console.log(ValueValidator.isNotEmpty([]));        // false
console.log(ValueValidator.getDefaultIfFalsy('', '기본값')); // '기본값'
```

### Nullish Coalescing 연산자 (??)

```javascript
// || 연산자의 문제점
console.log(0 || 10);    // 10 (0은 유효한 값일 수 있음)
console.log('' || '기본'); // '기본' (빈 문자열도 유효한 값일 수 있음)

// ?? 연산자는 null과 undefined만 falsy로 취급
console.log(0 ?? 10);    // 0
console.log('' ?? '기본'); // ''
console.log(null ?? '기본'); // '기본'
console.log(undefined ?? '기본'); // '기본'
```

Truthy와 Falsy는 JavaScript의 핵심 개념으로, 조건문과 논리 연산자에서 중요한 역할을 합니다. 값의 존재 여부를 확인하고 기본값을 설정하는 등 다양한 상황에서 활용됩니다.
