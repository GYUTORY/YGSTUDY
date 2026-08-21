---
title: JavaScript Map vs find vs filter 성능 비교
tags: [language, javascript, performance]
updated: 2025-08-10
---

# JavaScript Map vs find() vs filter() 성능 비교

## 배경

JavaScript에서 데이터를 찾고 관리할 때 쓰는 주요 방법 중 하나가 `Map` 객체와 배열의 `find()`, `filter()` 메서드다. 셋은 특성도 성능도 달라서 상황에 맞게 골라 써야 한다.

### 성능 비교의 필요성
- **검색 효율성**: 대용량 데이터에서 빠른 검색 성능 확보
- **메모리 사용량**: 자료구조 선택으로 메모리 최적화
- **코드 가독성**: 상황에 맞는 메서드 선택
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

이 측정은 아무것도 말해주지 않는다. `get` 한 번에 걸리는 시간이 **`performance.now()` 를 두 번 부르는 비용과 자릿수가 같기** 때문이다.

```javascript
const t0 = performance.now();
const r = largeMap.get(50000);
const t1 = performance.now();
console.log(t1 - t0);        // 0.0039...

const t2 = performance.now();
const t3 = performance.now();
console.log(t3 - t2);        // 0.0005...  ← 사이에 아무것도 없다
```

측정 대상보다 측정 도구의 오차가 크면 나온 값은 잡음이다. 게다가 JIT 이 워밍업되기 전 첫 호출이라 이후 호출과 성격도 다르다. 이 코드로 "Map 이 빠르다"를 확인했다고 생각하면 그건 착각이다.

마이크로벤치를 굳이 손으로 짜야 한다면 최소한 (1) 충분히 많이 반복해서 총 시간을 재고, (2) 워밍업 루프를 먼저 돌리고, (3) 결과를 어딘가에 누적해 최적화가 통째로 걷어내지 못하게 해야 한다. 셋 중 하나라도 빠지면 숫자를 믿지 않는 편이 낫다. 실제로는 [tinybench](https://github.com/tinylibs/tinybench) 같은 라이브러리에 맡기는 쪽이 정확하다.

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
console.log(Object.keys(obj).length); // 1 — obj[1] 과 obj['1'] 은 같은 키다

// 2. 크기 확인의 용이성
console.log(map.size); // 3
console.log(Object.keys(obj).length); // 1

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

이 코드는 어느 환경에서도 의미 있는 값을 내지 않는다. 세 가지가 겹쳤다.

**`performance.memory` 는 표준이 아니다.** Node 에서는 `undefined` 라 `?? 0` 이 아니라 `|| 0` 을 거쳐 항상 0 이 되고, 결과는 `0.00MB` 로 고정된다. 브라우저에서도 Chromium 계열에만 있고 값은 의도적으로 뭉뚱그려져 있다.

```javascript
performance.memory              // Node: undefined
performance.memory?.usedJSHeapSize || 0   // 0
```

**측정 구간이 대상을 감싸지 못한다.** `measureMemoryUsage('Array')` 를 먼저 부르고 그 다음 줄에서 배열을 만든다. `startMemory` 는 할당 전에 찍히지만 `endMemory` 는 `setTimeout` 안이라, 그 사이에 Map 생성까지 끝나 있다. 두 측정 구간이 서로 겹쳐서 Array 몫에 Map 이 섞인다.

**GC 시점을 모른다.** 힙 사용량은 수집이 언제 도는지에 따라 왔다 갔다 한다. Node 라면 `--expose-gc` 로 `global.gc()` 를 강제한 뒤 `process.memoryUsage().heapUsed` 를 재는 게 그나마 재현된다. 그래도 오차는 크다.

아래 "메모리 사용량 비교표"의 수치도 이 코드로는 재현되지 않는다. 자료구조의 메모리를 근거로 설계를 정할 일이 있으면 그때 자기 데이터로 직접 재는 수밖에 없다.

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

`getCachedResult` 에는 캐시 코드에서 가장 흔한 함정이 그대로 들어 있다. **없는 것을 찾은 결과는 캐시되지 않는다.**

```javascript
// 찾은 id: 두 번째부터 캐시 히트
m.getById(1); m.getById(1); m.getById(1);
// 실제 배열 스캔 횟수 = 1

// 없는 id: 매번 다시 스캔
m.getById(999); m.getById(999); m.getById(999);
// 실제 배열 스캔 횟수 = 3
```

`find` 가 `undefined` 를 돌려주면 `this.cache.set(key, undefined)` 로 저장은 되지만, 다음 조회에서 `if (cached && ...)` 가 falsy 로 막는다. 하필 없는 키를 찾는 요청이 **가장 비싼 경우**(배열 전체를 끝까지 훑는다)인데 그것만 캐시가 안 걸린다. 존재하지 않는 ID 로 들어오는 트래픽이 그대로 전부 풀스캔이 된다.

고치려면 값이 아니라 **키가 있는지**로 판단해야 한다 — `if (this.cache.has(key) && expiry && now < expiry)`. 값이 `0`, `''`, `false` 인 정상 결과에도 같은 문제가 생기므로 캐시를 짤 때는 항상 `has` 로 검사한다.

`getByCondition` 의 캐시 키에도 문제가 있다.

```javascript
'condition_' + JSON.stringify({ a: 1, b: 2 })   // 'condition_{"a":1,"b":2}'
'condition_' + JSON.stringify({ b: 2, a: 1 })   // 'condition_{"b":2,"a":1}'
```

의미가 완전히 같은 조건인데 키가 다르다. `JSON.stringify` 는 속성 순서를 그대로 옮기고, 그 순서는 호출부가 객체를 어떻게 썼느냐에 달렸다. 캐시 적중률이 이유 없이 낮으면 이걸 의심한다. 키를 만들 때 `Object.keys(condition).sort()` 로 순서를 고정하면 된다.

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

`safeArrayFind` 의 `array.find(predicate) || defaultValue` 는 안전하지 않다. **찾은 값이 falsy 면 못 찾은 것으로 처리한다.**

```javascript
safeArrayFind([0, 1, 2],  x => x === 0,     'DEFAULT');  // 'DEFAULT'
safeArrayFind(['', 'a'],  x => x === '',    'DEFAULT');  // 'DEFAULT'
safeArrayFind([false],    x => x === false, 'DEFAULT');  // 'DEFAULT'
```

숫자 0, 빈 문자열, `false` 는 배열에 흔히 들어 있는 정상 값이다. 수량 0인 항목이나 빈 메모를 찾을 때만 기본값이 튀어나오는 식으로 나타나서 재현 조건을 잡기 까다롭다.

`||` 대신 `??` 를 쓰면 `null` 과 `undefined` 만 걸러진다. `find` 는 못 찾았을 때 정확히 `undefined` 를 돌려주므로 이게 맞다.

```javascript
return array.find(predicate) ?? defaultValue;
```

`try/catch` 로 감싼 것도 다시 볼 만하다. `map.get` 이나 `array.filter` 자체는 던지지 않는다. 여기서 실제로 잡히는 예외는 **넘겨받은 `predicate` 안에서 난 것**뿐이고, 그걸 `console.error` 하고 기본값으로 삼키면 호출부는 "조건에 맞는 게 없었다"와 "콜백이 터졌다"를 구분하지 못한다. 조용히 빈 배열을 돌려주는 코드는 원인 추적을 어렵게 만든다.

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
Map은 키 기반 검색에서 가장 빠르다.
find()는 요소 하나를 찾을 때 적합하고 메모리도 덜 쓴다.
filter()는 조건이 복잡할 때 유연하다.
데이터 크기와 검색 빈도를 보고 방법을 고른다.
캐싱과 인덱싱으로 성능을 끌어올린다.
메모리 사용량과 성능 사이 균형을 보고 설계한다.

