---
title: JavaScript Truthy와 Falsy 완벽 가이드
tags: [language, javascript, 09es6및고급문법, truthy, falsy, boolean-conversion]
updated: 2025-08-10
---

# JavaScript Truthy와 Falsy 완벽 가이드

## 배경

JavaScript에서는 모든 값이 조건문에서 **참(true)** 또는 **거짓(false)**으로 평가됩니다.

### Truthy와 Falsy의 개념
- **Truthy**: 조건문에서 `true`로 평가되는 값
- **Falsy**: 조건문에서 `false`로 평가되는 값

### 타입 변환의 종류
- **명시적 변환**: 개발자가 직접 타입을 변환하는 것
- **암시적 변환**: JavaScript가 자동으로 타입을 변환하는 것

## 핵심

### 1. Falsy 값들

JavaScript에서 falsy로 평가되는 값들은 다음과 같습니다:

#### false
```javascript
if (false) {
    console.log('이 코드는 실행되지 않음');
}
```

#### 0 (숫자)
```javascript
if (0) {
    console.log('이 코드는 실행되지 않음');
}

// 문자열 '0'은 truthy입니다!
if ('0') {
    console.log('문자열 0은 truthy'); // 실행됨
}
```

#### 빈 문자열 ("")
```javascript
let emptyString = "";
if (emptyString) {
    console.log('빈 문자열은 falsy'); // 실행되지 않음
}

// 주의: 공백이 있는 문자열은 truthy입니다!
let spaceString = "   ";
if (spaceString) {
    console.log('공백 문자열은 truthy!'); // 실행됨
}
```

#### null
```javascript
let user = null;
if (user) {
    console.log('사용자가 있음'); // 실행되지 않음
}
```

#### undefined
```javascript
let name;
if (name) {
    console.log('이름이 있음'); // 실행되지 않음
}

// 객체의 존재하지 않는 속성에 접근할 때도 undefined
let person = {};
if (person.age) {
    console.log('나이가 있음'); // 실행되지 않음
}
```

#### NaN (Not a Number)
```javascript
let invalidNumber = 0 / 0; // NaN
if (invalidNumber) {
    console.log('유효한 숫자'); // 실행되지 않음
}

// NaN은 자기 자신과도 같지 않습니다
console.log(NaN === NaN); // false
console.log(isNaN(NaN)); // true (NaN 확인하는 올바른 방법)
```

### 2. Truthy 값들

Falsy가 아닌 모든 값은 truthy입니다:

#### true
```javascript
let isActive = true;
if (isActive) {
    console.log('활성화됨'); // 실행됨
}
```

#### 0이 아닌 모든 숫자
```javascript
if (42) console.log('양수는 truthy'); // 실행됨
if (-1) console.log('음수도 truthy'); // 실행됨
if (3.14) console.log('소수점도 truthy'); // 실행됨
```

#### 빈 문자열이 아닌 모든 문자열
```javascript
if ('hello') console.log('문자열은 truthy'); // 실행됨
if ('0') console.log('문자열 0도 truthy'); // 실행됨
if (' ') console.log('공백 문자열도 truthy'); // 실행됨
```

#### 모든 배열 (빈 배열 포함)
```javascript
if ([]) console.log('빈 배열은 truthy'); // 실행됨
if ([1, 2, 3]) console.log('요소가 있는 배열도 truthy'); // 실행됨
```

#### 모든 객체 (빈 객체 포함)
```javascript
if ({}) console.log('빈 객체는 truthy'); // 실행됨
if ({ name: 'John' }) console.log('속성이 있는 객체도 truthy'); // 실행됨
```

#### 모든 함수
```javascript
if (function() {}) console.log('함수는 truthy'); // 실행됨
if (() => {}) console.log('화살표 함수도 truthy'); // 실행됨
```

### 3. 타입 변환 방법

#### 명시적 변환
```javascript
// Boolean() 함수 사용
console.log(Boolean(0)); // false
console.log(Boolean('')); // false
console.log(Boolean(null)); // false
console.log(Boolean(undefined)); // false

console.log(Boolean(42)); // true
console.log(Boolean('hello')); // true
console.log(Boolean([])); // true
console.log(Boolean({})); // true

// 이중 부정 연산자 !! 사용
console.log(!!0); // false
console.log(!!''); // false
console.log(!!null); // false

console.log(!!42); // true
console.log(!!'hello'); // true
console.log(!![]); // true
```

#### 암시적 변환
```javascript
// 조건문에서의 암시적 변환
let value = 0;
if (value) {
    // value가 자동으로 false로 평가됨
    console.log('이 코드는 실행되지 않음');
}

let name = 'John';
if (name) {
    // name이 자동으로 true로 평가됨
    console.log('이름이 있음'); // 실행됨
}

// 논리 연산자에서의 암시적 변환
// OR 연산자 (||) - 첫 번째 truthy 값을 반환
console.log(0 || '기본값'); // '기본값'
console.log('' || '기본값'); // '기본값'
console.log('실제값' || '기본값'); // '실제값'

// AND 연산자 (&&) - 첫 번째 falsy 값을 반환하거나 마지막 truthy 값
console.log(0 && '실행되지 않음'); // 0
console.log('실행됨' && '마지막값'); // '마지막값'
```

## 예시

### 1. 실제 사용 사례

#### 기본값 설정
```javascript
// 사용자 이름이 없을 때 기본값 설정
function greetUser(name) {
    const displayName = name || '손님';
    return `안녕하세요, ${displayName}님!`;
}

console.log(greetUser('홍길동')); // '안녕하세요, 홍길동님!'
console.log(greetUser('')); // '안녕하세요, 손님님!'
console.log(greetUser(null)); // '안녕하세요, 손님님!'

// 객체 속성의 기본값 설정
function createUser(userData) {
    return {
        name: userData.name || '이름 없음',
        age: userData.age || 0,
        email: userData.email || '이메일 없음',
        isActive: userData.isActive || false
    };
}

const user1 = createUser({ name: '김철수', age: 25 });
console.log(user1); // { name: '김철수', age: 25, email: '이메일 없음', isActive: false }

const user2 = createUser({});
console.log(user2); // { name: '이름 없음', age: 0, email: '이메일 없음', isActive: false }
```

#### 조건부 실행
```javascript
// 조건부 함수 실행
function showMessage(message) {
    console.log(message);
}

// message가 있을 때만 실행
function displayMessage(message) {
    message && showMessage(message);
}

displayMessage('안녕하세요!'); // '안녕하세요!' 출력
displayMessage(''); // 아무것도 출력되지 않음
displayMessage(null); // 아무것도 출력되지 않음

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
// { host: 'localhost', port: 3000, logLevel: 'debug' }

console.log(createConfig({ ssl: true }));
// { host: 'localhost', port: 3000, protocol: 'https' }
```

#### 배열 필터링
```javascript
// falsy 값 제거
function removeFalsyValues(array) {
    return array.filter(Boolean);
}

const mixedArray = [0, 1, false, 2, '', 3, null, 4, undefined, 5, NaN];
const truthyArray = removeFalsyValues(mixedArray);
console.log(truthyArray); // [1, 2, 3, 4, 5]

// 실제 사용 예시
const userInputs = ['', '홍길동', null, '김철수', undefined, '이영희'];
const validNames = removeFalsyValues(userInputs);
console.log(validNames); // ['홍길동', '김철수', '이영희']
```

### 2. 고급 활용 패턴

#### 단축 평가 (Short-circuit evaluation)
```javascript
// 조건부 접근
const user = {
    profile: {
        name: '홍길동',
        settings: {
            theme: 'dark'
        }
    }
};

// 안전한 속성 접근
const theme = user && user.profile && user.profile.settings && user.profile.settings.theme;
console.log(theme); // 'dark'

// 더 간단한 방법 (옵셔널 체이닝)
const theme2 = user?.profile?.settings?.theme;
console.log(theme2); // 'dark'

// 기본값과 함께 사용
const displayName = user?.profile?.name || '이름 없음';
console.log(displayName); // '홍길동'

// 조건부 함수 호출
function expensiveOperation() {
    console.log('비용이 많이 드는 연산 수행');
    return '결과';
}

let shouldRun = false;
const result = shouldRun && expensiveOperation();
// shouldRun이 false이므로 expensiveOperation은 호출되지 않음
```

#### 논리 연산자 활용
```javascript
// 조건부 렌더링 (React 스타일)
function renderUserInfo(user) {
    return `
        <div class="user-info">
            <h2>${user.name || '이름 없음'}</h2>
            ${user.email && `<p>이메일: ${user.email}</p>`}
            ${user.age && `<p>나이: ${user.age}세</p>`}
            ${user.isAdmin ? '<span class="admin-badge">관리자</span>' : ''}
        </div>
    `;
}

const user1 = { name: '홍길동', email: 'hong@example.com', age: 25 };
const user2 = { name: '김철수', isAdmin: true };

console.log(renderUserInfo(user1));
console.log(renderUserInfo(user2));

// 조건부 객체 생성
function createUserConfig(user) {
    return {
        id: user.id,
        name: user.name,
        ...(user.isAdmin && { role: 'admin', permissions: ['read', 'write', 'delete'] }),
        ...(user.email && { contact: { email: user.email } }),
        ...(user.phone && { contact: { ...user.contact, phone: user.phone } })
    };
}

const adminUser = { id: 1, name: '관리자', isAdmin: true, email: 'admin@example.com' };
const regularUser = { id: 2, name: '일반사용자', email: 'user@example.com', phone: '010-1234-5678' };

console.log(createUserConfig(adminUser));
console.log(createUserConfig(regularUser));
```

## 운영 팁

### 성능 최적화

#### 조건부 실행 최적화
```javascript
// 비효율적: 항상 함수 호출
function processData(data) {
    if (data) {
        return expensiveOperation(data);
    }
    return null;
}

// 효율적: 단축 평가 사용
function processDataOptimized(data) {
    return data && expensiveOperation(data);
}

// 조건부 로깅
const DEBUG = false;
function log(message) {
    DEBUG && console.log(message);
}

// 조건부 이벤트 리스너
function addConditionalListener(element, event, handler, condition) {
    condition && element.addEventListener(event, handler);
}
```

#### 메모리 효율성
```javascript
// 조건부 객체 생성
function createConfig(options) {
    const config = {
        host: 'localhost',
        port: 3000
    };

    // 필요한 속성만 추가
    if (options.timeout) config.timeout = options.timeout;
    if (options.retries) config.retries = options.retries;
    if (options.ssl) config.ssl = options.ssl;

    return config;
}

// 더 간결한 방법
function createConfigOptimized(options) {
    return {
        host: 'localhost',
        port: 3000,
        ...(options.timeout && { timeout: options.timeout }),
        ...(options.retries && { retries: options.retries }),
        ...(options.ssl && { ssl: options.ssl })
    };
}
```

### 에러 처리

#### 안전한 값 검증
```javascript
// 값 검증 유틸리티
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
        if (typeof value === 'object') return Object.keys(value).length > 0;
        return Boolean(value);
    }

    static getDefaultIfFalsy(value, defaultValue) {
        return value || defaultValue;
    }

    static getDefaultIfEmpty(value, defaultValue) {
        return this.isNotEmpty(value) ? value : defaultValue;
    }
}

// 사용 예시
console.log(ValueValidator.isTruthy(0)); // false
console.log(ValueValidator.isTruthy('hello')); // true
console.log(ValueValidator.hasValue('')); // false
console.log(ValueValidator.hasValue('hello')); // true
console.log(ValueValidator.isNotEmpty([])); // false
console.log(ValueValidator.isNotEmpty([1, 2, 3])); // true
console.log(ValueValidator.getDefaultIfFalsy('', '기본값')); // '기본값'
console.log(ValueValidator.getDefaultIfEmpty('', '기본값')); // '기본값'
```

#### 조건부 에러 처리
```javascript
// 안전한 함수 실행
function safeExecute(fn, fallback) {
    try {
        return fn();
    } catch (error) {
        return fallback;
    }
}

// 조건부 에러 발생
function validateUser(user) {
    if (!user) {
        throw new Error('사용자 정보가 필요합니다.');
    }

    if (!user.name) {
        throw new Error('사용자 이름이 필요합니다.');
    }

    if (!user.email) {
        throw new Error('사용자 이메일이 필요합니다.');
    }

    return true;
}

// 사용 예시
const user1 = { name: '홍길동', email: 'hong@example.com' };
const user2 = { name: '김철수' };
const user3 = null;

console.log(safeExecute(() => validateUser(user1), false)); // true
console.log(safeExecute(() => validateUser(user2), false)); // false (에러 발생)
console.log(safeExecute(() => validateUser(user3), false)); // false (에러 발생)
```

## 참고

### Truthy/Falsy 체크리스트

#### Falsy 값 목록
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

#### Truthy 값 예시
```javascript
const truthyExamples = [
    true,           // 불린 true
    42,             // 양수
    -42,            // 음수
    3.14,           // 소수점
    'hello',        // 문자열
    '0',            // 문자열 0
    ' ',            // 공백 문자열
    [],             // 빈 배열
    [1, 2, 3],      // 요소가 있는 배열
    {},             // 빈 객체
    { key: 'value' }, // 속성이 있는 객체
    function() {},  // 함수
    () => {},       // 화살표 함수
    new Date(),     // Date 객체
    /regex/,        // 정규식
    Infinity,       // 무한대
    -Infinity       // 음의 무한대
];

// 모든 truthy 값 확인
truthyExamples.forEach(value => {
    console.log(`${value} is truthy:`, Boolean(value));
});
```

### 성능 측정

#### Truthy/Falsy 체크 성능 비교
```javascript
// 성능 측정 함수
function measurePerformance(fn, iterations = 1000000) {
    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
        fn();
    }
    const end = performance.now();
    return end - start;
}

// 다양한 체크 방법들
const testValue = 'hello';

const methods = {
    'Boolean()': () => Boolean(testValue),
    '!!': () => !!testValue,
    'if statement': () => {
        if (testValue) return true;
        return false;
    },
    'ternary': () => testValue ? true : false
};

// 성능 측정
Object.entries(methods).forEach(([name, method]) => {
    const time = measurePerformance(method);
    console.log(`${name}: ${time.toFixed(2)}ms`);
});
```

### 결론
Truthy와 Falsy는 JavaScript의 핵심 개념으로, 조건문과 논리 연산자에서 중요한 역할을 합니다.
명시적 변환과 암시적 변환을 적절히 활용하여 코드의 가독성과 성능을 향상시킬 수 있습니다.
단축 평가를 활용하여 불필요한 연산을 방지하고 메모리 효율성을 높일 수 있습니다.
안전한 값 검증과 에러 처리를 통해 견고한 코드를 작성할 수 있습니다.

