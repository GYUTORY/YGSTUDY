---
title: JavaScript 깊은 복사와 얕은 복사
tags: [language, javascript, 02복사및스프레드, copy개념, deep-copy, shallow-copy]
updated: 2025-12-30
---

# JavaScript 깊은 복사와 얕은 복사

## 정의

JavaScript에서 데이터를 복사할 때는 두 가지 방식이 있습니다:
- **얕은 복사(Shallow Copy)**: 객체의 첫 번째 레벨에 있는 값만 복사
- **깊은 복사(Deep Copy)**: 객체의 모든 레벨을 완전히 새로운 메모리에 복사

### 데이터 타입과 복사

**원시 타입(Primitive Type)**: 값이 그대로 복사됩니다.
```javascript
const num = 42;
const copyNum = num; // 42가 그대로 복사됨
```

**참조 타입(Reference Type)**: 참조(메모리 주소)가 복사됩니다.
```javascript
const arr = [1, 2, 3];
const copyArr = arr; // arr의 메모리 주소가 복사됨
```

## 동작 원리

### 얕은 복사 (Shallow Copy)

객체의 최상위 레벨 속성만 복사하고, 중첩된 객체는 참조만 복사합니다.

```javascript
// 얕은 복사 방법들
// 1. Object.assign()
const copy1 = Object.assign({}, original);

// 2. 전개 연산자 (Spread Operator)
const copy2 = { ...original };

// 3. Array.from()
const copy3 = Array.from(original);

// 4. slice()
const copy4 = original.slice();
```

**얕은 복사의 한계**
```javascript
const original = {
    name: 'John',
    address: {
        city: 'Seoul',
        country: 'Korea'
    }
};

const shallowCopy = { ...original };
shallowCopy.address.city = 'Busan';
console.log(original.address.city); // 'Busan' (원본도 변경됨)
```

### 깊은 복사 (Deep Copy)

모든 레벨의 객체가 독립적으로 복사됩니다.

```javascript
// 1. JSON 방식
const copy = JSON.parse(JSON.stringify(original));

// 2. 재귀 함수
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

// 3. structuredClone() (모던 브라우저)
const copy = structuredClone(original);
```

**JSON 방식의 한계**
```javascript
const complexObj = {
    func: function() { return 'Hello'; }, // 손실됨
    undef: undefined, // 손실됨
    date: new Date(), // 문자열로 변환됨
    regex: /test/, // 손실됨
};

const jsonCopy = JSON.parse(JSON.stringify(complexObj));
console.log(jsonCopy.func); // undefined
```

## 사용법

### 실용적인 불변성 패턴

```javascript
// 배열에서 요소 제거
const removeItem = (array, index) => [
    ...array.slice(0, index),
    ...array.slice(index + 1)
];

// 객체에서 속성 제거
const removeProperty = (obj, key) => {
    const { [key]: removed, ...rest } = obj;
    return rest;
};

// 조건부 업데이트
const updateIf = (condition, updater) => (obj) => 
    condition(obj) ? updater(obj) : obj;
```

### 복잡한 객체의 깊은 복사

```javascript
function deepCopyAdvanced(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    
    if (obj instanceof Date) {
        return new Date(obj.getTime());
    }
    
    if (obj instanceof RegExp) {
        return new RegExp(obj);
    }
    
    if (obj instanceof Map) {
        return new Map(Array.from(obj, ([key, val]) => [key, deepCopyAdvanced(val)]));
    }
    
    if (obj instanceof Set) {
        return new Set(Array.from(obj, val => deepCopyAdvanced(val)));
    }
    
    const copy = Array.isArray(obj) ? [] : {};
    
    for (let key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            copy[key] = deepCopyAdvanced(obj[key]);
        }
    }
    
    return copy;
}
```

## 예제

### 사용자 데이터 관리

```javascript
class UserDataManager {
    constructor() {
        this.users = [
            {
                id: 1,
                name: '김철수',
                profile: {
                    age: 25,
                    preferences: { theme: 'dark' }
                }
            }
        ];
    }
    
    getUsersShallow() {
        return [...this.users];
    }
    
    getUsersDeep() {
        return JSON.parse(JSON.stringify(this.users));
    }
}

const userManager = new UserDataManager();

// 얕은 복사 사용
const shallowUsers = userManager.getUsersShallow();
shallowUsers[0].profile.preferences.theme = 'light';
console.log(userManager.users[0].profile.preferences.theme); // 'light' (원본 변경됨)

// 깊은 복사 사용
const deepUsers = userManager.getUsersDeep();
deepUsers[0].profile.preferences.theme = 'light';
console.log(userManager.users[0].profile.preferences.theme); // 'dark' (원본 유지됨)
```

### 복사 방법 선택 가이드

```javascript
function selectCopyMethod(data, requirements) {
    const { needsDeepCopy, hasFunctions, hasDates, performanceCritical } = requirements;
    
    if (performanceCritical && !needsDeepCopy) {
        return 'shallow';
    }
    
    if (needsDeepCopy) {
        if (hasFunctions || hasDates) {
            return 'library'; // structuredClone 또는 lodash
        }
        return 'json';
    }
    
    return 'shallow';
}

// 사용 예시
const userData = {
    name: 'John',
    profile: { age: 25 },
    lastLogin: new Date(),
    updateProfile: function() { /* ... */ }
};

const requirements = {
    needsDeepCopy: true,
    hasFunctions: true,
    hasDates: true,
    performanceCritical: false
};

const method = selectCopyMethod(userData, requirements);
console.log('선택된 복사 방법:', method); // 'library'
```

## 참고

### 복사 방법 비교

| 방법 | 성능 | 메모리 | 제한사항 | 추천 사용 |
|------|------|--------|----------|----------|
| 얕은 복사 | 빠름 | 낮음 | 중첩 객체 참조 공유 | 단순한 객체, 성능 중요 |
| JSON 복사 | 보통 | 중간 | 함수/undefined 손실 | 단순 데이터 구조 |
| 재귀 복사 | 느림 | 높음 | 순환 참조 처리 필요 | 복잡한 객체 |
| structuredClone | 빠름 | 중간 | 함수 복사 불가 | 모던 브라우저 |

### 사용 시나리오

- **얕은 복사**: 단순한 객체, 성능이 중요한 경우
- **JSON 복사**: 함수가 없는 객체, 빠른 구현 필요
- **재귀 복사**: 복잡한 객체 구조, 특수 객체 타입 포함
- **라이브러리**: 프로덕션 환경, 안정성 중요

성능과 기능적 요구사항을 모두 고려하여 최적의 방식을 선택하는 것이 중요합니다.
