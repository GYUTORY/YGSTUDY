---
title: JavaScript Map vs find vs filter 성능 비교
tags: [language, javascript, 01기본javascript, map, find, filter, performance]
updated: 2025-08-10
---

# JavaScript Map vs find() vs filter() 성능 비교 및 최적화 가이드

## 배경

JavaScript에서 데이터를 검색하고 관리할 때 사용할 수 있는 주요 방법들 중 하나가 `Map` 객체와 배열의 `find()`, `filter()` 메서드입니다. 각각은 서로 다른 특성과 성능 특성을 가지고 있어, 상황에 따라 적절한 선택이 필요합니다.

### 성능 비교의 필요성
- **검색 효율성**: 대용량 데이터에서 빠른 검색 성능 확보
- **메모리 사용량**: 적절한 자료구조 선택으로 메모리 최적화
- **코드 가독성**: 상황에 맞는 적절한 메서드 선택
- **확장성**: 데이터 크기 증가에 따른 성능 변화 고려

### 기본 개념
- **Map**: 키-값 쌍을 저장하는 해시맵 구조, O(1) 검색 성능
- **find()**: 배열에서 조건을 만족하는 첫 번째 요소를 찾아 반환
- **filter()**: 배열에서 조건을 만족하는 모든 요소를 새로운 배열로 반환

## 핵심

### 1. Map 객체 상세 분석

#### Map의 기본 사용법
```javascript
// Map 기본 사용법
const userMap = new Map();

// 데이터 추가
userMap.set(1, { id: 1, name: 'Alice', age: 25 });
userMap.set(2, { id: 2, name: 'Bob', age: 30 });
userMap.set(3, { id: 3, name: 'Charlie', age: 35 });

// 데이터 검색
const user = userMap.get(2);
console.log(user); // { id: 2, name: 'Bob', age: 30 }

// 존재 여부 확인
console.log(userMap.has(2)); // true
console.log(userMap.has(4)); // false

// 데이터 삭제
userMap.delete(2);

// 크기 확인
console.log(userMap.size); // 2
```

#### Map의 성능 특성
```javascript
// Map의 O(1) 검색 성능
const largeMap = new Map();
const size = 100000;

// 데이터 초기화
for (let i = 0; i < size; i++) {
    largeMap.set(i, { id: i, name: `User${i}`, age: 20 + (i % 50) });
}

// 검색 성능 측정
const startTime = performance.now();
const result = largeMap.get(50000);
const endTime = performance.now();

console.log(`Map 검색 시간: ${endTime - startTime}ms`);
console.log('검색 결과:', result);
```

#### Map vs Object 비교
```javascript
// Map의 장점들
const map = new Map();
const obj = {};

// 1. 키 타입의 유연성
map.set(1, 'number key');
map.set('1', 'string key');
map.set({}, 'object key');

obj[1] = 'number key';
obj['1'] = 'string key'; // 위와 동일한 키로 덮어씀

console.log(map.size); // 3
console.log(Object.keys(obj).length); // 2

// 2. 크기 확인의 용이성
console.log(map.size); // 3
console.log(Object.keys(obj).length); // 2

// 3. 순회의 일관성
map.forEach((value, key) => {
    console.log(`${key}: ${value}`);
});

for (const [key, value] of map.entries()) {
    console.log(`${key}: ${value}`);
}
```

### 2. find() 메서드 상세 분석

#### find()의 기본 사용법
```javascript
const users = [
    { id: 1, name: 'Alice', age: 25 },
    { id: 2, name: 'Bob', age: 30 },
    { id: 3, name: 'Charlie', age: 35 },
    { id: 4, name: 'David', age: 28 }
];

// ID로 사용자 찾기
const user = users.find(user => user.id === 2);
console.log(user); // { id: 2, name: 'Bob', age: 30 }

// 이름으로 사용자 찾기
const alice = users.find(user => user.name === 'Alice');
console.log(alice); // { id: 1, name: 'Alice', age: 25 }

// 조건을 만족하지 않는 경우
const notFound = users.find(user => user.id === 999);
console.log(notFound); // undefined
```

#### find()의 성능 특성
```javascript
// find()의 O(n) 검색 성능
const largeArray = Array.from({ length: 100000 }, (_, i) => ({
    id: i,
    name: `User${i}`,
    age: 20 + (i % 50)
}));

// 첫 번째 요소 검색 (최선의 경우)
let startTime = performance.now();
const firstResult = largeArray.find(user => user.id === 0);
let endTime = performance.now();
console.log(`첫 번째 요소 검색: ${endTime - startTime}ms`);

// 중간 요소 검색 (평균적인 경우)
startTime = performance.now();
const middleResult = largeArray.find(user => user.id === 50000);
endTime = performance.now();
console.log(`중간 요소 검색: ${endTime - startTime}ms`);

// 마지막 요소 검색 (최악의 경우)
startTime = performance.now();
const lastResult = largeArray.find(user => user.id === 99999);
endTime = performance.now();
console.log(`마지막 요소 검색: ${endTime - startTime}ms`);
```

### 3. filter() 메서드 상세 분석

#### filter()의 기본 사용법
```javascript
const users = [
    { id: 1, name: 'Alice', age: 25 },
    { id: 2, name: 'Bob', age: 30 },
    { id: 3, name: 'Charlie', age: 35 },
    { id: 4, name: 'David', age: 28 },
    { id: 5, name: 'Eve', age: 32 }
];

// 나이가 30 이상인 사용자들 찾기
const olderUsers = users.filter(user => user.age >= 30);
console.log(olderUsers);
// [
//   { id: 2, name: 'Bob', age: 30 },
//   { id: 3, name: 'Charlie', age: 35 },
//   { id: 5, name: 'Eve', age: 32 }
// ]

// 이름이 'A'로 시작하는 사용자들 찾기
const aUsers = users.filter(user => user.name.startsWith('A'));
console.log(aUsers); // [{ id: 1, name: 'Alice', age: 25 }]
```

#### filter()의 성능 특성
```javascript
// filter()의 O(n) 성능
const largeArray = Array.from({ length: 100000 }, (_, i) => ({
    id: i,
    name: `User${i}`,
    age: 20 + (i % 50)
}));

// 모든 요소를 검사하는 경우
const startTime = performance.now();
const filtered = largeArray.filter(user => user.age >= 30);
const endTime = performance.now();

console.log(`filter() 실행 시간: ${endTime - startTime}ms`);
console.log(`필터링된 요소 수: ${filtered.length}`);
```

### 4. 성능 비교 분석

#### 검색 성능 비교
```javascript
// 테스트 데이터 준비
const testSize = 100000;
const testArray = Array.from({ length: testSize }, (_, i) => ({
    id: i,
    name: `User${i}`,
    age: 20 + (i % 50)
}));

const testMap = new Map();
testArray.forEach(user => testMap.set(user.id, user));

// 1. 단일 요소 검색 성능 비교
function compareSingleSearch() {
    const searchId = 50000;
    
    // Map 검색
    let startTime = performance.now();
    const mapResult = testMap.get(searchId);
    let endTime = performance.now();
    const mapTime = endTime - startTime;
    
    // find() 검색
    startTime = performance.now();
    const findResult = testArray.find(user => user.id === searchId);
    endTime = performance.now();
    const findTime = endTime - startTime;
    
    console.log(`Map 검색 시간: ${mapTime}ms`);
    console.log(`find() 검색 시간: ${findTime}ms`);
    console.log(`성능 차이: ${(findTime / mapTime).toFixed(2)}배`);
}

// 2. 다중 요소 검색 성능 비교
function compareMultipleSearch() {
    const searchIds = [1000, 5000, 10000, 50000, 90000];
    
    // Map으로 다중 검색
    let startTime = performance.now();
    const mapResults = searchIds.map(id => testMap.get(id));
    let endTime = performance.now();
    const mapTime = endTime - startTime;
    
    // find()로 다중 검색
    startTime = performance.now();
    const findResults = searchIds.map(id => 
        testArray.find(user => user.id === id)
    );
    endTime = performance.now();
    const findTime = endTime - startTime;
    
    console.log(`Map 다중 검색 시간: ${mapTime}ms`);
    console.log(`find() 다중 검색 시간: ${findTime}ms`);
    console.log(`성능 차이: ${(findTime / mapTime).toFixed(2)}배`);
}

compareSingleSearch();
compareMultipleSearch();
```

#### 메모리 사용량 비교
```javascript
// 메모리 사용량 측정 함수
function measureMemoryUsage(dataStructure) {
    const startMemory = performance.memory?.usedJSHeapSize || 0;
    
    // 가비지 컬렉션을 위한 지연
    setTimeout(() => {
        const endMemory = performance.memory?.usedJSHeapSize || 0;
        const memoryUsed = endMemory - startMemory;
        console.log(`${dataStructure} 메모리 사용량: ${(memoryUsed / 1024 / 1024).toFixed(2)}MB`);
    }, 100);
}

// 배열과 Map의 메모리 사용량 비교
const size = 10000;
const testData = Array.from({ length: size }, (_, i) => ({
    id: i,
    name: `User${i}`,
    age: 20 + (i % 50)
}));

// 배열 메모리 측정
measureMemoryUsage('Array');
const array = [...testData];

// Map 메모리 측정
measureMemoryUsage('Map');
const map = new Map(testData.map(item => [item.id, item]));
```

## 예시

### 1. 실제 사용 사례

#### 사용자 관리 시스템
```javascript
class UserManager {
    constructor() {
        this.users = [];
        this.userMap = new Map();
        this.isMapInitialized = false;
    }
    
    addUser(user) {
        this.users.push(user);
        this.userMap.set(user.id, user);
    }
    
    // Map을 사용한 빠른 검색 (권장)
    getUserById(id) {
        return this.userMap.get(id);
    }
    
    // find()를 사용한 검색 (Map이 없는 경우)
    getUserByIdSlow(id) {
        return this.users.find(user => user.id === id);
    }
    
    // filter()를 사용한 다중 검색
    getUsersByAge(minAge, maxAge) {
        return this.users.filter(user => 
            user.age >= minAge && user.age <= maxAge
        );
    }
    
    // 복잡한 조건 검색
    searchUsers(criteria) {
        return this.users.filter(user => {
            if (criteria.name && !user.name.includes(criteria.name)) {
                return false;
            }
            if (criteria.minAge && user.age < criteria.minAge) {
                return false;
            }
            if (criteria.maxAge && user.age > criteria.maxAge) {
                return false;
            }
            return true;
        });
    }
}

// 사용 예시
const userManager = new UserManager();

// 사용자 추가
for (let i = 0; i < 10000; i++) {
    userManager.addUser({
        id: i,
        name: `User${i}`,
        age: 20 + (i % 50),
        email: `user${i}@example.com`
    });
}

// 성능 비교
const searchId = 5000;

// Map 검색 (빠름)
const startTime1 = performance.now();
const user1 = userManager.getUserById(searchId);
const endTime1 = performance.now();
console.log(`Map 검색: ${endTime1 - startTime1}ms`);

// find() 검색 (느림)
const startTime2 = performance.now();
const user2 = userManager.getUserByIdSlow(searchId);
const endTime2 = performance.now();
console.log(`find() 검색: ${endTime2 - startTime2}ms`);
```

### 2. 고급 패턴

#### 캐싱과 성능 최적화
```javascript
class OptimizedDataManager {
    constructor() {
        this.data = [];
        this.cache = new Map();
        this.cacheExpiry = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5분
    }
    
    setData(data) {
        this.data = data;
        this.clearCache();
    }
    
    // 캐시된 검색
    getCachedResult(key, searchFunction) {
        const now = Date.now();
        const cached = this.cache.get(key);
        const expiry = this.cacheExpiry.get(key);
        
        if (cached && expiry && now < expiry) {
            return cached;
        }
        
        const result = searchFunction();
        this.cache.set(key, result);
        this.cacheExpiry.set(key, now + this.cacheTimeout);
        
        return result;
    }
    
    // ID로 검색 (캐시 적용)
    getById(id) {
        return this.getCachedResult(`id_${id}`, () => {
            return this.data.find(item => item.id === id);
        });
    }
    
    // 조건 검색 (캐시 적용)
    getByCondition(condition) {
        const key = `condition_${JSON.stringify(condition)}`;
        return this.getCachedResult(key, () => {
            return this.data.filter(item => {
                return Object.entries(condition).every(([prop, value]) => {
                    return item[prop] === value;
                });
            });
        });
    }
    
    clearCache() {
        this.cache.clear();
        this.cacheExpiry.clear();
    }
    
    // 캐시 통계
    getCacheStats() {
        return {
            cacheSize: this.cache.size,
            cacheKeys: Array.from(this.cache.keys())
        };
    }
}

// 사용 예시
const manager = new OptimizedDataManager();

// 대용량 데이터 설정
const largeDataset = Array.from({ length: 100000 }, (_, i) => ({
    id: i,
    name: `Item${i}`,
    category: `Category${i % 10}`,
    value: Math.random() * 1000
}));

manager.setData(largeDataset);

// 첫 번째 검색 (캐시 미스)
const startTime1 = performance.now();
const result1 = manager.getById(50000);
const endTime1 = performance.now();
console.log(`첫 번째 검색: ${endTime1 - startTime1}ms`);

// 두 번째 검색 (캐시 히트)
const startTime2 = performance.now();
const result2 = manager.getById(50000);
const endTime2 = performance.now();
console.log(`두 번째 검색: ${endTime2 - startTime2}ms`);

console.log('캐시 통계:', manager.getCacheStats());
```

## 운영 팁

### 성능 최적화

#### 상황별 최적 선택 가이드
```javascript
// 1. 단일 요소 검색이 빈번한 경우 → Map 사용
const userMap = new Map();
users.forEach(user => userMap.set(user.id, user));

// 빠른 검색
const user = userMap.get(userId);

// 2. 복잡한 조건 검색이 필요한 경우 → filter() 사용
const activeUsers = users.filter(user => 
    user.isActive && user.lastLogin > oneWeekAgo
);

// 3. 첫 번째 일치 요소만 필요한 경우 → find() 사용
const firstActiveUser = users.find(user => user.isActive);

// 4. 대용량 데이터에서 성능이 중요한 경우 → Map + 인덱싱
class OptimizedUserManager {
    constructor() {
        this.users = [];
        this.idIndex = new Map();
        this.nameIndex = new Map();
    }
    
    addUser(user) {
        this.users.push(user);
        this.idIndex.set(user.id, user);
        
        // 이름 인덱스 (동명이인 고려)
        if (!this.nameIndex.has(user.name)) {
            this.nameIndex.set(user.name, []);
        }
        this.nameIndex.get(user.name).push(user);
    }
    
    getById(id) {
        return this.idIndex.get(id);
    }
    
    getByName(name) {
        return this.nameIndex.get(name) || [];
    }
}
```

### 에러 처리

#### 안전한 검색 구현
```javascript
// 안전한 Map 검색
function safeMapGet(map, key, defaultValue = null) {
    try {
        return map.has(key) ? map.get(key) : defaultValue;
    } catch (error) {
        console.error('Map 검색 오류:', error);
        return defaultValue;
    }
}

// 안전한 배열 검색
function safeArrayFind(array, predicate, defaultValue = null) {
    try {
        if (!Array.isArray(array)) {
            return defaultValue;
        }
        return array.find(predicate) || defaultValue;
    } catch (error) {
        console.error('배열 검색 오류:', error);
        return defaultValue;
    }
}

// 안전한 필터링
function safeArrayFilter(array, predicate, defaultValue = []) {
    try {
        if (!Array.isArray(array)) {
            return defaultValue;
        }
        return array.filter(predicate);
    } catch (error) {
        console.error('배열 필터링 오류:', error);
        return defaultValue;
    }
}

// 사용 예시
const userMap = new Map();
const users = [];

try {
    const user1 = safeMapGet(userMap, 1, { id: 1, name: 'Default' });
    const user2 = safeArrayFind(users, u => u.id === 1, { id: 1, name: 'Default' });
    const activeUsers = safeArrayFilter(users, u => u.isActive, []);
    
    console.log('안전한 검색 결과:', { user1, user2, activeUsers });
} catch (error) {
    console.error('검색 중 오류 발생:', error);
}
```

## 참고

### 성능 비교표

| 방법 | 검색 성능 | 메모리 사용량 | 사용 시기 |
|------|-----------|---------------|-----------|
| **Map** | O(1) | 높음 | 빈번한 키 검색 |
| **find()** | O(n) | 낮음 | 단일 요소 검색 |
| **filter()** | O(n) | 중간 | 다중 요소 검색 |

### 메모리 사용량 비교표

| 데이터 크기 | Map | Array | 차이 |
|-------------|-----|-------|------|
| 1,000개 | ~2MB | ~1MB | 2배 |
| 10,000개 | ~20MB | ~10MB | 2배 |
| 100,000개 | ~200MB | ~100MB | 2배 |

### 최적화 권장사항

| 상황 | 권장 방법 | 이유 |
|------|-----------|------|
| **빈번한 ID 검색** | Map | O(1) 성능 |
| **복잡한 조건 검색** | filter() | 유연성 |
| **첫 번째 일치 요소** | find() | 효율성 |
| **대용량 데이터** | Map + 인덱싱 | 성능 최적화 |
| **메모리 제약** | Array 메서드 | 메모리 절약 |

### 결론
Map은 키 기반 검색에서 가장 빠른 성능을 제공합니다.
find()는 단일 요소 검색에 적합하며 메모리 효율적입니다.
filter()는 복잡한 조건 검색에 유연성을 제공합니다.
데이터 크기와 검색 빈도를 고려하여 적절한 방법을 선택하세요.
캐싱과 인덱싱을 활용하여 성능을 최적화하세요.
메모리 사용량과 성능 사이의 균형을 고려하여 설계하세요.

