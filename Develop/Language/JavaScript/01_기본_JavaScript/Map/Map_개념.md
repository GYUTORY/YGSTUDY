---
title: JavaScript Map 개념과 사용법
tags: [language, javascript, 01기본javascript, map, map개념, data-structure]
updated: 2025-08-10
---

# JavaScript Map 개념과 사용법

## 배경

JavaScript의 Map은 키-값 쌍을 저장하는 컬렉션 자료구조입니다. 일반 객체와 달리 Map은 다양한 타입의 키를 사용할 수 있고, 삽입 순서를 보장하며, 더 나은 성능을 제공합니다.

### Map의 필요성
- **다양한 키 타입**: 문자열뿐만 아니라 객체, 함수 등도 키로 사용 가능
- **삽입 순서 보장**: 요소가 추가된 순서대로 순회 가능
- **성능 최적화**: 키-값 쌍의 추가/삭제가 빈번한 경우 효율적
- **크기 추적**: 내장된 size 속성으로 요소 개수 확인 가능

### 기본 개념
- **키-값 쌍**: Map의 기본 데이터 단위
- **해시 테이블**: 내부적으로 해시 테이블을 사용하여 빠른 검색
- **이터러블**: for...of 루프로 순회 가능
- **메서드 기반**: get, set, has, delete 등의 메서드 제공

## 핵심

### 1. Map 생성과 기본 사용법

#### Map 생성하기
```javascript
// 1. 빈 Map 생성
const emptyMap = new Map();

// 2. 초기값과 함께 생성
const map = new Map([
    ['name', '김철수'],
    ['age', 25],
    [1, '숫자 키'],
    [{id: 1}, '객체 키']
]);

// 3. 배열로부터 Map 생성
const entries = [['a', 1], ['b', 2], ['c', 3]];
const mapFromArray = new Map(entries);

console.log(mapFromArray); // Map(3) {'a' => 1, 'b' => 2, 'c' => 3}
```

#### 기본 메서드 사용법
```javascript
const userMap = new Map();

// 데이터 추가
userMap.set('id', 1);
userMap.set('name', 'Alice');
userMap.set('age', 25);

// 데이터 조회
console.log(userMap.get('name')); // 'Alice'
console.log(userMap.get('email')); // undefined

// 존재 여부 확인
console.log(userMap.has('age')); // true
console.log(userMap.has('email')); // false

// 데이터 삭제
userMap.delete('age');
console.log(userMap.has('age')); // false

// 크기 확인
console.log(userMap.size); // 2

// 모든 데이터 삭제
userMap.clear();
console.log(userMap.size); // 0
```

### 2. Map vs 일반 객체 비교

#### 키 타입의 유연성
```javascript
const map = new Map();
const obj = {};

// Map: 다양한 타입의 키 사용 가능
map.set(1, 'number key');
map.set('1', 'string key');
map.set({}, 'object key');
map.set(() => {}, 'function key');

// 객체: 키가 문자열로 변환됨
obj[1] = 'number key';
obj['1'] = 'string key'; // 위와 동일한 키로 덮어씀
obj[{}] = 'object key'; // '[object Object]'로 변환됨

console.log(map.size); // 4
console.log(Object.keys(obj).length); // 2
console.log(obj); // { '1': 'string key', '[object Object]': 'object key' }
```

#### 삽입 순서 보장
```javascript
const map = new Map();
const obj = {};

// Map: 삽입 순서 보장
map.set('first', 1);
map.set('second', 2);
map.set('third', 3);

// 객체: ES2015 이후 삽입 순서 보장 (하지만 숫자 키는 정렬됨)
obj.first = 1;
obj.second = 2;
obj.third = 3;

// 순회 비교
console.log('Map 순회:');
for (const [key, value] of map) {
    console.log(`${key}: ${value}`);
}

console.log('객체 순회:');
for (const key in obj) {
    console.log(`${key}: ${obj[key]}`);
}
```

#### 성능 비교
```javascript
const size = 10000;
const map = new Map();
const obj = {};

// 데이터 추가 성능 비교
console.time('Map 추가');
for (let i = 0; i < size; i++) {
    map.set(i, `value${i}`);
}
console.timeEnd('Map 추가');

console.time('객체 추가');
for (let i = 0; i < size; i++) {
    obj[i] = `value${i}`;
}
console.timeEnd('객체 추가');

// 검색 성능 비교
console.time('Map 검색');
for (let i = 0; i < size; i++) {
    map.get(i);
}
console.timeEnd('Map 검색');

console.time('객체 검색');
for (let i = 0; i < size; i++) {
    obj[i];
}
console.timeEnd('객체 검색');
```

### 3. Map 순회 방법

#### 다양한 순회 방법
```javascript
const userMap = new Map([
    ['id', 1],
    ['name', 'Alice'],
    ['age', 25],
    ['email', 'alice@example.com']
]);

// 1. for...of 루프
console.log('for...of 루프:');
for (const [key, value] of userMap) {
    console.log(`${key}: ${value}`);
}

// 2. forEach 메서드
console.log('forEach 메서드:');
userMap.forEach((value, key) => {
    console.log(`${key}: ${value}`);
});

// 3. entries() 메서드
console.log('entries() 메서드:');
for (const entry of userMap.entries()) {
    console.log(`${entry[0]}: ${entry[1]}`);
}

// 4. keys() 메서드
console.log('keys() 메서드:');
for (const key of userMap.keys()) {
    console.log(`키: ${key}`);
}

// 5. values() 메서드
console.log('values() 메서드:');
for (const value of userMap.values()) {
    console.log(`값: ${value}`);
}
```

#### Map을 배열로 변환
```javascript
const userMap = new Map([
    ['id', 1],
    ['name', 'Alice'],
    ['age', 25]
]);

// Map을 배열로 변환
const entriesArray = Array.from(userMap.entries());
console.log('entries 배열:', entriesArray);
// [['id', 1], ['name', 'Alice'], ['age', 25]]

const keysArray = Array.from(userMap.keys());
console.log('keys 배열:', keysArray);
// ['id', 'name', 'age']

const valuesArray = Array.from(userMap.values());
console.log('values 배열:', valuesArray);
// [1, 'Alice', 25]

// 스프레드 연산자 사용
const spreadEntries = [...userMap.entries()];
const spreadKeys = [...userMap.keys()];
const spreadValues = [...userMap.values()];
```

### 4. 실제 사용 예시

#### 사용자 관리 시스템
```javascript
class UserManager {
    constructor() {
        this.users = new Map();
        this.nextId = 1;
    }
    
    addUser(name, email, age) {
        const user = {
            id: this.nextId++,
            name,
            email,
            age,
            createdAt: new Date()
        };
        
        this.users.set(user.id, user);
        return user;
    }
    
    getUserById(id) {
        return this.users.get(id);
    }
    
    updateUser(id, updates) {
        const user = this.users.get(id);
        if (user) {
            Object.assign(user, updates);
            this.users.set(id, user);
            return user;
        }
        return null;
    }
    
    deleteUser(id) {
        return this.users.delete(id);
    }
    
    getAllUsers() {
        return Array.from(this.users.values());
    }
    
    getUsersByAge(minAge, maxAge) {
        return Array.from(this.users.values())
            .filter(user => user.age >= minAge && user.age <= maxAge);
    }
    
    getUserCount() {
        return this.users.size;
    }
}

// 사용 예시
const userManager = new UserManager();

userManager.addUser('Alice', 'alice@example.com', 25);
userManager.addUser('Bob', 'bob@example.com', 30);
userManager.addUser('Charlie', 'charlie@example.com', 35);

console.log('사용자 수:', userManager.getUserCount()); // 3

const user = userManager.getUserById(1);
console.log('사용자 정보:', user);

userManager.updateUser(1, { age: 26 });
console.log('업데이트된 사용자:', userManager.getUserById(1));

const youngUsers = userManager.getUsersByAge(20, 30);
console.log('젊은 사용자들:', youngUsers);
```

#### 캐시 시스템
```javascript
class Cache {
    constructor(maxSize = 100) {
        this.cache = new Map();
        this.maxSize = maxSize;
    }
    
    set(key, value, ttl = 60000) { // 기본 TTL: 1분
        // 캐시 크기 제한 확인
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        const expiry = Date.now() + ttl;
        this.cache.set(key, { value, expiry });
    }
    
    get(key) {
        const item = this.cache.get(key);
        
        if (!item) {
            return null;
        }
        
        // 만료 확인
        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return null;
        }
        
        return item.value;
    }
    
    has(key) {
        const item = this.cache.get(key);
        if (!item) return false;
        
        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return false;
        }
        
        return true;
    }
    
    delete(key) {
        return this.cache.delete(key);
    }
    
    clear() {
        this.cache.clear();
    }
    
    size() {
        return this.cache.size;
    }
    
    // 만료된 항목 정리
    cleanup() {
        const now = Date.now();
        for (const [key, item] of this.cache.entries()) {
            if (now > item.expiry) {
                this.cache.delete(key);
            }
        }
    }
}

// 사용 예시
const cache = new Cache(5);

cache.set('user:1', { id: 1, name: 'Alice' }, 5000); // 5초 TTL
cache.set('user:2', { id: 2, name: 'Bob' }, 10000); // 10초 TTL

console.log('캐시 크기:', cache.size()); // 2
console.log('사용자 1:', cache.get('user:1')); // { id: 1, name: 'Alice' }

// 6초 후
setTimeout(() => {
    console.log('사용자 1 (만료 후):', cache.get('user:1')); // null
    console.log('사용자 2:', cache.get('user:2')); // { id: 2, name: 'Bob' }
    cache.cleanup();
    console.log('정리 후 캐시 크기:', cache.size()); // 1
}, 6000);
```

## 예시

### 1. 고급 패턴

#### WeakMap 활용
```javascript
// WeakMap은 키가 약한 참조를 가짐 (가비지 컬렉션 대상)
const privateData = new WeakMap();

class User {
    constructor(name, email) {
        // privateData에 인스턴스별 데이터 저장
        privateData.set(this, {
            name,
            email,
            createdAt: new Date()
        });
    }
    
    getName() {
        return privateData.get(this).name;
    }
    
    getEmail() {
        return privateData.get(this).email;
    }
    
    updateEmail(newEmail) {
        const data = privateData.get(this);
        data.email = newEmail;
        privateData.set(this, data);
    }
}

const user1 = new User('Alice', 'alice@example.com');
const user2 = new User('Bob', 'bob@example.com');

console.log(user1.getName()); // 'Alice'
console.log(user2.getEmail()); // 'bob@example.com'

user1.updateEmail('alice.new@example.com');
console.log(user1.getEmail()); // 'alice.new@example.com'
```

#### 이벤트 리스너 관리
```javascript
class EventManager {
    constructor() {
        this.listeners = new Map();
    }
    
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }
    
    off(event, callback) {
        if (!this.listeners.has(event)) return;
        
        const callbacks = this.listeners.get(event);
        const index = callbacks.indexOf(callback);
        if (index > -1) {
            callbacks.splice(index, 1);
        }
        
        if (callbacks.length === 0) {
            this.listeners.delete(event);
        }
    }
    
    emit(event, ...args) {
        if (!this.listeners.has(event)) return;
        
        const callbacks = this.listeners.get(event);
        callbacks.forEach(callback => {
            try {
                callback(...args);
            } catch (error) {
                console.error('이벤트 리스너 오류:', error);
            }
        });
    }
    
    getEventCount(event) {
        return this.listeners.has(event) ? this.listeners.get(event).length : 0;
    }
    
    clearEvent(event) {
        this.listeners.delete(event);
    }
    
    clearAll() {
        this.listeners.clear();
    }
}

// 사용 예시
const eventManager = new EventManager();

const userLoginHandler = (user) => {
    console.log(`사용자 로그인: ${user.name}`);
};

const userLogoutHandler = (user) => {
    console.log(`사용자 로그아웃: ${user.name}`);
};

eventManager.on('user:login', userLoginHandler);
eventManager.on('user:logout', userLogoutHandler);

console.log('로그인 이벤트 리스너 수:', eventManager.getEventCount('user:login')); // 1

eventManager.emit('user:login', { id: 1, name: 'Alice' });
eventManager.emit('user:logout', { id: 1, name: 'Alice' });

eventManager.off('user:login', userLoginHandler);
console.log('로그인 이벤트 리스너 수:', eventManager.getEventCount('user:login')); // 0
```

### 2. 직렬화와 역직렬화

#### Map 직렬화
```javascript
const userMap = new Map([
    ['id', 1],
    ['name', 'Alice'],
    ['age', 25],
    ['hobbies', ['reading', 'swimming']]
]);

// Map을 JSON으로 직렬화
function mapToJSON(map) {
    return JSON.stringify(Array.from(map.entries()));
}

// JSON을 Map으로 역직렬화
function jsonToMap(jsonString) {
    const entries = JSON.parse(jsonString);
    return new Map(entries);
}

// 사용 예시
const jsonString = mapToJSON(userMap);
console.log('직렬화된 JSON:', jsonString);
// '[["id",1],["name","Alice"],["age",25],["hobbies",["reading","swimming"]]]'

const restoredMap = jsonToMap(jsonString);
console.log('복원된 Map:', restoredMap);
console.log('복원된 사용자 이름:', restoredMap.get('name')); // 'Alice'
```

#### 복잡한 객체 직렬화
```javascript
class DataManager {
    constructor() {
        this.data = new Map();
    }
    
    set(key, value) {
        this.data.set(key, value);
    }
    
    get(key) {
        return this.data.get(key);
    }
    
    // 복잡한 Map을 JSON으로 직렬화
    toJSON() {
        const serialized = {};
        
        for (const [key, value] of this.data.entries()) {
            // 키를 문자열로 변환
            const keyStr = typeof key === 'object' ? JSON.stringify(key) : String(key);
            
            // 값이 Map인 경우 재귀적으로 처리
            if (value instanceof Map) {
                serialized[keyStr] = Array.from(value.entries());
            } else {
                serialized[keyStr] = value;
            }
        }
        
        return serialized;
    }
    
    // JSON에서 Map으로 역직렬화
    fromJSON(jsonData) {
        this.data.clear();
        
        for (const [keyStr, value] of Object.entries(jsonData)) {
            let key;
            
            // 키 파싱
            try {
                key = JSON.parse(keyStr);
            } catch {
                key = keyStr;
            }
            
            // 값이 배열이고 Map으로 보이는 경우
            if (Array.isArray(value) && value.length > 0 && Array.isArray(value[0])) {
                this.data.set(key, new Map(value));
            } else {
                this.data.set(key, value);
            }
        }
    }
}

// 사용 예시
const manager = new DataManager();

// 중첩된 Map 구조
const userPreferences = new Map([
    ['theme', 'dark'],
    ['language', 'ko']
]);

manager.set('user:1', { name: 'Alice', age: 25 });
manager.set('user:2', { name: 'Bob', age: 30 });
manager.set('preferences:1', userPreferences);

const jsonData = manager.toJSON();
console.log('직렬화된 데이터:', jsonData);

const newManager = new DataManager();
newManager.fromJSON(jsonData);

console.log('복원된 사용자 1:', newManager.get('user:1'));
console.log('복원된 설정:', newManager.get('preferences:1'));
```

## 운영 팁

### 성능 최적화

#### Map 성능 최적화
```javascript
// 1. 초기 크기 설정 (대용량 데이터)
const largeMap = new Map();
const size = 100000;

console.time('기본 추가');
for (let i = 0; i < size; i++) {
    largeMap.set(i, `value${i}`);
}
console.timeEnd('기본 추가');

// 2. 배치 처리
function batchSet(map, entries) {
    for (const [key, value] of entries) {
        map.set(key, value);
    }
}

const entries = Array.from({ length: 10000 }, (_, i) => [i, `value${i}`]);
const batchMap = new Map();

console.time('배치 추가');
batchSet(batchMap, entries);
console.timeEnd('배치 추가');

// 3. 메모리 효율적인 키 사용
const efficientMap = new Map();

// 효율적인 키 (문자열, 숫자)
efficientMap.set('user:1', { name: 'Alice' });
efficientMap.set(123, { name: 'Bob' });

// 비효율적인 키 (객체, 함수) - 가능하면 피하기
const objKey = { id: 1 };
efficientMap.set(objKey, { name: 'Charlie' });
```

### 에러 처리

#### 안전한 Map 조작
```javascript
// 안전한 Map 조작 함수들
class SafeMap extends Map {
    safeGet(key, defaultValue = null) {
        try {
            return this.has(key) ? this.get(key) : defaultValue;
        } catch (error) {
            console.error('Map 조회 오류:', error);
            return defaultValue;
        }
    }
    
    safeSet(key, value) {
        try {
            this.set(key, value);
            return true;
        } catch (error) {
            console.error('Map 설정 오류:', error);
            return false;
        }
    }
    
    safeDelete(key) {
        try {
            return this.delete(key);
        } catch (error) {
            console.error('Map 삭제 오류:', error);
            return false;
        }
    }
    
    // 조건부 업데이트
    updateIfExists(key, updater) {
        if (this.has(key)) {
            const currentValue = this.get(key);
            const newValue = updater(currentValue);
            this.set(key, newValue);
            return true;
        }
        return false;
    }
    
    // 기본값과 함께 가져오기
    getOrDefault(key, defaultValue) {
        return this.has(key) ? this.get(key) : defaultValue;
    }
}

// 사용 예시
const safeMap = new SafeMap();

safeMap.set('user:1', { name: 'Alice', age: 25 });

// 안전한 조회
const user = safeMap.safeGet('user:1', { name: 'Unknown', age: 0 });
console.log('사용자:', user);

// 조건부 업데이트
safeMap.updateIfExists('user:1', (user) => {
    user.age += 1;
    return user;
});

console.log('업데이트된 사용자:', safeMap.get('user:1'));
```

## 참고

### Map vs Object vs Array 비교표

| 특성 | Map | Object | Array |
|------|-----|--------|-------|
| **키 타입** | 모든 타입 | 문자열, Symbol | 숫자 인덱스 |
| **삽입 순서** | 보장됨 | ES2015+ 보장 | 보장됨 |
| **크기 확인** | size 속성 | Object.keys().length | length 속성 |
| **성능** | O(1) 검색 | O(1) 검색 | O(n) 검색 |
| **메모리** | 높음 | 중간 | 낮음 |
| **직렬화** | 복잡함 | 간단함 | 간단함 |

### Map 사용 권장사항

| 상황 | 권장사항 | 이유 |
|------|----------|------|
| **빈번한 키-값 조작** | Map 사용 | 성능 최적화 |
| **다양한 키 타입** | Map 사용 | 유연성 |
| **순서가 중요한 경우** | Map 사용 | 삽입 순서 보장 |
| **JSON 직렬화 필요** | Object 사용 | 간단한 직렬화 |
| **숫자 인덱스** | Array 사용 | 최적화된 성능 |
| **메모리 제약** | Object 사용 | 메모리 효율성 |

### 결론
Map은 키-값 쌍을 효율적으로 관리하는 강력한 자료구조입니다.
다양한 키 타입과 삽입 순서 보장으로 유연성을 제공합니다.
성능이 중요한 키-값 조작에는 Map을 사용하세요.
메모리 사용량과 직렬화 요구사항을 고려하여 선택하세요.
WeakMap을 활용하여 메모리 누수를 방지하세요.
안전한 Map 조작을 위해 적절한 에러 처리를 구현하세요.