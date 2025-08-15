---
title: JavaScript 깊은 복사와 얕은 복사
tags: [language, javascript, 02복사및스프레드, copy개념, deep-copy, shallow-copy]
updated: 2025-08-10
---

# JavaScript 깊은 복사와 얕은 복사

## 배경

JavaScript에서 데이터를 복사할 때는 두 가지 방식이 있습니다:
- **얕은 복사(Shallow Copy)**: 객체의 첫 번째 레벨에 있는 값만 복사
- **깊은 복사(Deep Copy)**: 객체의 모든 레벨을 완전히 새로운 메모리에 복사

### 복사의 필요성
- **데이터 무결성**: 원본 데이터를 변경하지 않고 복사본을 수정
- **상태 관리**: 애플리케이션 상태의 불변성 유지
- **성능 최적화**: 필요한 경우에만 복사하여 메모리 효율성 확보
- **버그 방지**: 의도치 않은 데이터 변경으로 인한 오류 방지

### JavaScript 데이터 타입과 복사
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

## 핵심

### 1. 얕은 복사 (Shallow Copy)

#### 얕은 복사의 특징
- 객체의 최상위 레벨 속성만 복사
- 중첩된 객체는 참조만 복사
- 원본과 복사본이 중첩 객체를 공유

#### 얕은 복사 방법
```javascript
// 1. Object.assign()
const original = { a: 1, b: 2 };
const copy = Object.assign({}, original);

// 2. 전개 연산자 (Spread Operator)
const original = { a: 1, b: 2 };
const copy = { ...original };

// 3. Array.from()
const original = [1, 2, 3];
const copy = Array.from(original);

// 4. slice()
const original = [1, 2, 3];
const copy = original.slice();
```

#### 얕은 복사의 한계
```javascript
// 중첩 객체의 참조 공유 문제
const original = {
    name: 'John',
    address: {
        city: 'Seoul',
        country: 'Korea'
    }
};

const shallowCopy = { ...original };

// 중첩 객체 수정 시 원본도 변경됨
shallowCopy.address.city = 'Busan';
console.log(original.address.city); // 'Busan'
console.log(shallowCopy.address.city); // 'Busan'
```

### 2. 깊은 복사 (Deep Copy)

#### 깊은 복사의 특징
1. **원시 타입**: 값이 그대로 복사됩니다.
2. **참조 타입**: 새로운 메모리 공간에 완전히 복사됩니다.
3. **중첩 객체**: 모든 레벨의 객체가 독립적으로 복사됩니다.

#### 깊은 복사 방법
```javascript
// 1. JSON.parse(JSON.stringify())
const original = { a: { b: 1 } };
const copy = JSON.parse(JSON.stringify(original));

// 2. 재귀 함수를 사용한 복사
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

// 3. 라이브러리 사용
// lodash 사용
const copy = _.cloneDeep(original);
```

#### JSON 방식의 깊은 복사 한계
```javascript
const complexObj = {
    func: function() { return 'Hello'; },
    undef: undefined,
    date: new Date(),
    regex: /test/,
    bigInt: BigInt(123),
    circular: null
};
complexObj.circular = complexObj; // 순환 참조

// JSON 방식으로 복사 시 문제 발생
try {
    const jsonCopy = JSON.parse(JSON.stringify(complexObj));
    console.log(jsonCopy.func); // undefined
    console.log(jsonCopy.undef); // undefined
    console.log(jsonCopy.date); // 문자열로 변환됨
} catch (error) {
    console.log('순환 참조로 인한 오류:', error.message);
}
```

## 예시

### 1. 실제 사용 사례

#### 사용자 데이터 복사
```javascript
// 사용자 데이터 관리 클래스
class UserDataManager {
    constructor() {
        this.users = [
            {
                id: 1,
                name: '김철수',
                profile: {
                    age: 25,
                    email: 'kim@example.com',
                    preferences: {
                        theme: 'dark',
                        language: 'ko'
                    }
                }
            }
        ];
    }
    
    // 얕은 복사로 사용자 목록 반환
    getUsersShallow() {
        return [...this.users];
    }
    
    // 깊은 복사로 사용자 목록 반환
    getUsersDeep() {
        return this.deepCopy(this.users);
    }
    
    // 재귀적 깊은 복사 구현
    deepCopy(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        
        if (obj instanceof RegExp) {
            return new RegExp(obj);
        }
        
        const copy = Array.isArray(obj) ? [] : {};
        
        for (let key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = this.deepCopy(obj[key]);
            }
        }
        
        return copy;
    }
    
    // 사용자 프로필 수정 (얕은 복사 사용)
    updateUserProfileShallow(userId, updates) {
        const users = this.getUsersShallow();
        const userIndex = users.findIndex(user => user.id === userId);
        
        if (userIndex !== -1) {
            users[userIndex] = { ...users[userIndex], ...updates };
            // 중첩 객체는 여전히 참조를 공유
            return users;
        }
        
        return null;
    }
    
    // 사용자 프로필 수정 (깊은 복사 사용)
    updateUserProfileDeep(userId, updates) {
        const users = this.getUsersDeep();
        const userIndex = users.findIndex(user => user.id === userId);
        
        if (userIndex !== -1) {
            users[userIndex] = { ...users[userIndex], ...updates };
            // 모든 중첩 객체가 독립적으로 복사됨
            return users;
        }
        
        return null;
    }
}

// 사용 예시
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

### 2. 성능 비교

#### 복사 방법별 성능 측정
```javascript
// 성능 측정 유틸리티
class CopyPerformanceTester {
    static createTestObject(depth, breadth) {
        const obj = {};
        
        for (let i = 0; i < breadth; i++) {
            if (depth === 1) {
                obj[`key${i}`] = `value${i}`;
            } else {
                obj[`key${i}`] = this.createTestObject(depth - 1, breadth);
            }
        }
        
        return obj;
    }
    
    static measureCopyPerformance(obj, copyMethod, iterations = 1000) {
        const start = performance.now();
        
        for (let i = 0; i < iterations; i++) {
            copyMethod(obj);
        }
        
        const end = performance.now();
        return {
            method: copyMethod.name,
            time: end - start,
            iterations: iterations,
            averageTime: (end - start) / iterations
        };
    }
    
    // 다양한 복사 방법들
    static shallowCopySpread(obj) {
        return { ...obj };
    }
    
    static shallowCopyAssign(obj) {
        return Object.assign({}, obj);
    }
    
    static deepCopyJSON(obj) {
        return JSON.parse(JSON.stringify(obj));
    }
    
    static deepCopyRecursive(obj) {
        return this.recursiveCopy(obj);
    }
    
    static recursiveCopy(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        
        const copy = Array.isArray(obj) ? [] : {};
        
        for (let key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = this.recursiveCopy(obj[key]);
            }
        }
        
        return copy;
    }
}

// 성능 테스트 실행
const testObj = CopyPerformanceTester.createTestObject(3, 5);

const results = [
    CopyPerformanceTester.measureCopyPerformance(testObj, CopyPerformanceTester.shallowCopySpread),
    CopyPerformanceTester.measureCopyPerformance(testObj, CopyPerformanceTester.shallowCopyAssign),
    CopyPerformanceTester.measureCopyPerformance(testObj, CopyPerformanceTester.deepCopyJSON),
    CopyPerformanceTester.measureCopyPerformance(testObj, CopyPerformanceTester.deepCopyRecursive)
];

console.log('복사 방법별 성능 비교:');
results.forEach(result => {
    console.log(`${result.method}: ${result.averageTime.toFixed(4)}ms per copy`);
});
```

## 운영 팁

### 적절한 복사 방법 선택

#### 사용 시나리오별 권장 방법
```javascript
// 복사 방법 선택 가이드
class CopyMethodSelector {
    static selectCopyMethod(data, requirements) {
        const { needsDeepCopy, hasFunctions, hasDates, hasCircularRefs, performanceCritical } = requirements;
        
        if (performanceCritical && !needsDeepCopy) {
            return 'shallow';
        }
        
        if (needsDeepCopy) {
            if (hasFunctions || hasDates || hasCircularRefs) {
                return 'library'; // lodash, structuredClone 등
            } else {
                return 'json';
            }
        }
        
        return 'shallow';
    }
    
    static copy(data, method) {
        switch (method) {
            case 'shallow':
                return Array.isArray(data) ? [...data] : { ...data };
            case 'json':
                return JSON.parse(JSON.stringify(data));
            case 'library':
                // 실제로는 lodash나 structuredClone 사용
                return this.deepCopyRecursive(data);
            default:
                throw new Error(`Unknown copy method: ${method}`);
        }
    }
    
    static deepCopyRecursive(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        
        if (obj instanceof RegExp) {
            return new RegExp(obj);
        }
        
        const copy = Array.isArray(obj) ? [] : {};
        
        for (let key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = this.deepCopyRecursive(obj[key]);
            }
        }
        
        return copy;
    }
}

// 사용 예시
const userData = {
    name: 'John',
    profile: {
        age: 25,
        preferences: {
            theme: 'dark'
        }
    },
    lastLogin: new Date(),
    updateProfile: function() { /* ... */ }
};

const requirements = {
    needsDeepCopy: true,
    hasFunctions: true,
    hasDates: true,
    hasCircularRefs: false,
    performanceCritical: false
};

const method = CopyMethodSelector.selectCopyMethod(userData, requirements);
const copiedData = CopyMethodSelector.copy(userData, method);

console.log('선택된 복사 방법:', method);
console.log('복사된 데이터:', copiedData);
```

### 메모리 효율성

#### 메모리 사용량 최적화
```javascript
// 메모리 효율적인 복사 관리
class MemoryEfficientCopier {
    constructor() {
        this.cache = new WeakMap();
        this.maxCacheSize = 100;
    }
    
    // 캐시를 활용한 복사
    copyWithCache(obj, deep = false) {
        if (this.cache.has(obj)) {
            return this.cache.get(obj);
        }
        
        const copy = deep ? this.deepCopy(obj) : this.shallowCopy(obj);
        
        // 캐시 크기 제한
        if (this.cache.size >= this.maxCacheSize) {
            // 가장 오래된 항목 제거 (WeakMap은 자동으로 처리)
            this.cache = new WeakMap();
        }
        
        this.cache.set(obj, copy);
        return copy;
    }
    
    shallowCopy(obj) {
        return Array.isArray(obj) ? [...obj] : { ...obj };
    }
    
    deepCopy(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        
        const copy = Array.isArray(obj) ? [] : {};
        
        for (let key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                copy[key] = this.deepCopy(obj[key]);
            }
        }
        
        return copy;
    }
    
    // 캐시 통계
    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize
        };
    }
    
    // 캐시 정리
    clearCache() {
        this.cache = new WeakMap();
    }
}

// 사용 예시
const copier = new MemoryEfficientCopier();
const data = { a: 1, b: { c: 2 } };

// 첫 번째 복사
const copy1 = copier.copyWithCache(data, true);
console.log('첫 번째 복사:', copy1);

// 두 번째 복사 (캐시에서 반환)
const copy2 = copier.copyWithCache(data, true);
console.log('두 번째 복사:', copy2);
console.log('캐시 통계:', copier.getCacheStats());
```

## 참고

### 복사 방법 비교표

#### 성능 및 기능 비교
```javascript
// 복사 방법 비교 클래스
class CopyMethodComparison {
    static getComparisonTable() {
        return {
            shallowCopy: {
                name: '얕은 복사',
                methods: ['Object.assign()', 'Spread Operator', 'Array.from()', 'slice()'],
                performance: '빠름',
                memoryUsage: '낮음',
                limitations: ['중첩 객체 참조 공유', '함수 복사 불가'],
                useCases: ['단순한 객체 복사', '성능이 중요한 경우', '참조 공유가 허용되는 경우']
            },
            deepCopyJSON: {
                name: 'JSON 깊은 복사',
                methods: ['JSON.parse(JSON.stringify())'],
                performance: '보통',
                memoryUsage: '중간',
                limitations: ['함수 복사 불가', 'undefined 무시', 'Date 객체 문자열 변환', '순환 참조 오류'],
                useCases: ['단순한 데이터 구조', '함수가 없는 객체', '빠른 구현이 필요한 경우']
            },
            deepCopyRecursive: {
                name: '재귀 깊은 복사',
                methods: ['커스텀 재귀 함수'],
                performance: '느림',
                memoryUsage: '높음',
                limitations: ['순환 참조 처리 필요', '특수 객체 타입 처리 필요'],
                useCases: ['복잡한 객체 구조', '특수 객체 타입 포함', '완전한 독립성 필요']
            },
            deepCopyLibrary: {
                name: '라이브러리 깊은 복사',
                methods: ['lodash.cloneDeep()', 'structuredClone()'],
                performance: '빠름',
                memoryUsage: '중간',
                limitations: ['외부 의존성', '번들 크기 증가'],
                useCases: ['프로덕션 환경', '복잡한 객체 구조', '안정성 중요']
            }
        };
    }
    
    // 권장 사용 사례
    static getRecommendations() {
        return {
            '단순한 객체 복사': 'shallowCopy',
            '배열 복사': 'shallowCopy',
            '함수가 없는 객체 깊은 복사': 'deepCopyJSON',
            '복잡한 객체 깊은 복사': 'deepCopyLibrary',
            '성능이 중요한 경우': 'shallowCopy',
            '완전한 독립성이 필요한 경우': 'deepCopyLibrary'
        };
    }
}

// 비교표 출력
const comparison = CopyMethodComparison.getComparisonTable();
console.log('복사 방법 비교표:', comparison);

const recommendations = CopyMethodComparison.getRecommendations();
console.log('권장 사용 사례:', recommendations);
```

### 결론
JavaScript에서 데이터를 복사할 때는 상황과 요구사항에 따라 적절한 방식을 선택해야 합니다.
얕은 복사는 성능이 우수하지만 중첩 객체의 참조 공유 문제가 있습니다.
깊은 복사는 완전한 독립성을 보장하지만 성능과 메모리 사용량이 증가합니다.
JSON 방식의 깊은 복사는 간단하지만 함수나 특수 객체 타입을 처리하지 못합니다.
라이브러리를 사용한 깊은 복사는 안정성과 성능을 모두 고려한 최적의 선택입니다.
성능과 기능적 요구사항을 모두 고려하여 최적의 방식을 선택하는 것이 중요합니다.






JavaScript에서 데이터를 다룰 때 가장 중요한 개념 중 하나가 바로 복사입니다. 특히 객체나 배열과 같은 참조 타입 데이터를 다룰 때는 얕은 복사(Shallow Copy)와 깊은 복사(Deep Copy)의 차이를 정확히 이해하는 것이 매우 중요합니다. 이번 글에서는 이 두 가지 복사 방식의 차이점과 각각의 사용 사례를 자세히 살펴보겠습니다.

1. 중첩된 객체는 여전히 원본과 참조를 공유합니다.
2. 원본 객체의 중첩된 값을 변경하면 복사본도 영향을 받습니다.

1. 단순한 객체의 복사가 필요할 때
2. 중첩된 데이터가 없는 경우
3. 성능이 중요한 경우
4. 원본 데이터의 일부 참조를 유지해야 할 때

1. 완전히 독립적인 복사본이 필요할 때
2. 중첩된 객체 구조를 다룰 때
3. 원본 데이터의 불변성이 중요할 때
4. 복잡한 데이터 구조를 다룰 때

1. 단순한 객체의 복사가 필요할 때
2. 중첩된 데이터가 없는 경우
3. 성능이 중요한 경우
4. 원본 데이터의 일부 참조를 유지해야 할 때

1. 완전히 독립적인 복사본이 필요할 때
2. 중첩된 객체 구조를 다룰 때
3. 원본 데이터의 불변성이 중요할 때
4. 복잡한 데이터 구조를 다룰 때


- 얕은 복사는 깊은 복사보다 일반적으로 더 빠릅니다.
- 대규모 객체나 배열을 다룰 때는 성능을 고려하여 적절한 방식을 선택해야 합니다.
- JSON 방식의 깊은 복사는 간단하지만, 성능이 중요한 경우에는 라이브러리를 사용하는 것이 좋습니다.


JavaScript에서 데이터를 복사할 때는 상황과 요구사항에 따라 적절한 방식을 선택해야 합니다. 단순한 데이터 구조라면 얕은 복사로 충분할 수 있지만, 복잡한 중첩 구조를 다룰 때는 깊은 복사를 사용하는 것이 안전합니다. 또한, 성능과 기능적 요구사항을 모두 고려하여 최적의 방식을 선택하는 것이 중요합니다. 






JavaScript에서 데이터를 다룰 때 가장 중요한 개념 중 하나가 바로 복사입니다. 특히 객체나 배열과 같은 참조 타입 데이터를 다룰 때는 얕은 복사(Shallow Copy)와 깊은 복사(Deep Copy)의 차이를 정확히 이해하는 것이 매우 중요합니다. 이번 글에서는 이 두 가지 복사 방식의 차이점과 각각의 사용 사례를 자세히 살펴보겠습니다.





## 얕은 복사 (Shallow Copy) 🔄

## 깊은 복사 (Deep Copy) 🔍

