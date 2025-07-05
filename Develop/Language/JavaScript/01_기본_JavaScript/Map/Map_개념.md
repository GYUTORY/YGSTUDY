# JavaScript Map

## 📋 목차
- [Map이란 무엇인가?](#map이란-무엇인가)
- [기본 문법과 사용법](#기본-문법과-사용법)
- [Map vs 일반 객체 비교](#map-vs-일반-객체-비교)
- [실제 사용 예시](#실제-사용-예시)
- [직렬화와 역직렬화](#직렬화와-역직렬화)
- [주의사항과 팁](#주의사항과-팁)

---

## Map이란 무엇인가?

### 🔍 Map의 정의
`Map`은 **키(key)와 값(value)의 쌍으로 데이터를 저장하는 자료구조**입니다. 

### 💡 왜 Map을 사용할까?
일반 객체(`{}`)와 달리 Map은:
- **어떤 타입이든 키로 사용 가능** (객체, 함수, 숫자 등)
- **삽입 순서가 보장됨**
- **키-값 쌍의 개수를 쉽게 알 수 있음**

### 🎯 언제 Map을 사용해야 할까?
- 키가 문자열이 아닌 경우 (객체를 키로 사용하고 싶을 때)
- 키-값 쌍을 자주 추가/삭제하는 경우
- 데이터의 순서가 중요한 경우

---

## 기본 문법과 사용법

### 📝 Map 생성하기
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
```

### 🛠️ 주요 메서드

#### 데이터 추가/수정
```javascript
const map = new Map();

// set(key, value): 키-값 쌍 추가 또는 수정
map.set('name', '김철수');
map.set('age', 25);
map.set('age', 26); // 기존 값 덮어쓰기

console.log(map); // Map(2) {'name' => '김철수', 'age' => 26}
```

#### 데이터 조회
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// get(key): 키에 해당하는 값 반환
console.log(map.get('name')); // '김철수'
console.log(map.get('height')); // undefined (존재하지 않는 키)

// has(key): 키 존재 여부 확인 (boolean 반환)
console.log(map.has('name')); // true
console.log(map.has('height')); // false
```

#### 데이터 삭제
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25],
  ['city', '서울']
]);

// delete(key): 특정 키-값 쌍 삭제
map.delete('age');
console.log(map.has('age')); // false

// clear(): 모든 데이터 삭제
map.clear();
console.log(map.size); // 0
```

#### 크기 확인
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// size: 키-값 쌍의 개수
console.log(map.size); // 2
```

### 🔄 반복과 순회

#### forEach 사용
```javascript
const userMap = new Map([
  ['name', '김철수'],
  ['age', 25],
  ['city', '서울']
]);

// forEach(callback): 각 요소에 대해 함수 실행
userMap.forEach((value, key) => {
  console.log(`${key}: ${value}`);
});
// 출력:
// name: 김철수
// age: 25
// city: 서울
```

#### for...of 사용
```javascript
const userMap = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// 전체 Map 순회
for (const [key, value] of userMap) {
  console.log(`${key}: ${value}`);
}

// 키만 순회
for (const key of userMap.keys()) {
  console.log(key);
}

// 값만 순회
for (const value of userMap.values()) {
  console.log(value);
}
```

#### 반복 메서드들
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// keys(): 모든 키를 반환
console.log([...map.keys()]); // ['name', 'age']

// values(): 모든 값을 반환
console.log([...map.values()]); // ['김철수', 25]

// entries(): 모든 [키, 값] 쌍을 반환
console.log([...map.entries()]); // [['name', '김철수'], ['age', 25]]
```

---

## Map vs 일반 객체 비교

### 📊 비교표

| 특징 | Map | 일반 객체 |
|------|-----|-----------|
| **키 타입** | 모든 타입 가능 | 문자열, 심볼만 가능 |
| **순서** | 삽입 순서 보장 | ES2015 이후 삽입 순서 보장 |
| **크기 확인** | `map.size` | `Object.keys(obj).length` |
| **반복** | 내장 반복 메서드 | `for...in`, `Object.keys()` 등 |
| **성능** | 키-값 추가/삭제 최적화 | 일반적인 사용에 최적화 |

### 🔍 실제 비교 예시

#### 키 타입의 차이
```javascript
// Map: 다양한 타입을 키로 사용 가능
const map = new Map();
map.set('문자열', '값1');
map.set(123, '값2');
map.set({id: 1}, '값3');
map.set(() => {}, '값4');

// 일반 객체: 문자열과 심볼만 키로 사용 가능
const obj = {};
obj['문자열'] = '값1';
obj[123] = '값2'; // 숫자는 문자열로 변환됨
// obj[{id: 1}] = '값3'; // 객체는 문자열로 변환되어 '[object Object]'가 됨
```

#### 크기 확인의 차이
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

const obj = {
  name: '김철수',
  age: 25
};

// Map: 간단하게 크기 확인
console.log(map.size); // 2

// 객체: 메서드를 통해 크기 확인
console.log(Object.keys(obj).length); // 2
```

---

## 실제 사용 예시

### 🏪 쇼핑몰 장바구니 구현
```javascript
class ShoppingCart {
  constructor() {
    this.items = new Map(); // 상품ID를 키로, 수량을 값으로
  }

  addItem(productId, quantity = 1) {
    const currentQuantity = this.items.get(productId) || 0;
    this.items.set(productId, currentQuantity + quantity);
  }

  removeItem(productId) {
    this.items.delete(productId);
  }

  getQuantity(productId) {
    return this.items.get(productId) || 0;
  }

  getTotalItems() {
    let total = 0;
    for (const quantity of this.items.values()) {
      total += quantity;
    }
    return total;
  }

  clear() {
    this.items.clear();
  }
}

// 사용 예시
const cart = new ShoppingCart();
cart.addItem('P001', 2); // 상품 P001을 2개 추가
cart.addItem('P002', 1); // 상품 P002를 1개 추가
cart.addItem('P001', 1); // 상품 P001을 1개 더 추가

console.log(cart.getQuantity('P001')); // 3
console.log(cart.getTotalItems()); // 4
```

### 🎮 게임 캐릭터 스킬 관리
```javascript
class Character {
  constructor(name) {
    this.name = name;
    this.skills = new Map(); // 스킬명을 키로, 레벨을 값으로
  }

  learnSkill(skillName, level = 1) {
    this.skills.set(skillName, level);
  }

  upgradeSkill(skillName) {
    const currentLevel = this.skills.get(skillName);
    if (currentLevel) {
      this.skills.set(skillName, currentLevel + 1);
    }
  }

  getSkillLevel(skillName) {
    return this.skills.get(skillName) || 0;
  }

  getAllSkills() {
    return Array.from(this.skills.entries());
  }
}

// 사용 예시
const warrior = new Character('전사');
warrior.learnSkill('검술', 3);
warrior.learnSkill('방어술', 2);
warrior.upgradeSkill('검술');

console.log(warrior.getSkillLevel('검술')); // 4
console.log(warrior.getAllSkills()); // [['검술', 4], ['방어술', 2]]
```

### 📊 사용자 세션 관리
```javascript
class SessionManager {
  constructor() {
    this.sessions = new Map(); // 세션ID를 키로, 사용자 정보를 값으로
  }

  createSession(sessionId, userInfo) {
    this.sessions.set(sessionId, {
      ...userInfo,
      createdAt: new Date(),
      lastAccess: new Date()
    });
  }

  getSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.lastAccess = new Date();
    }
    return session;
  }

  removeSession(sessionId) {
    this.sessions.delete(sessionId);
  }

  getActiveSessions() {
    return this.sessions.size;
  }
}

// 사용 예시
const sessionManager = new SessionManager();
sessionManager.createSession('sess_123', {
  userId: 'user_001',
  username: '김철수',
  role: 'admin'
});

const session = sessionManager.getSession('sess_123');
console.log(session.username); // '김철수'
```

---

## 직렬화와 역직렬화

### 🔄 직렬화란?
**직렬화(Serialization)**는 데이터 구조를 문자열로 변환하는 과정입니다. 주로 데이터를 저장하거나 네트워크로 전송할 때 사용됩니다.

### ⚠️ Map의 직렬화 문제
Map 객체는 `JSON.stringify()`로 직접 직렬화할 수 없습니다:

```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// ❌ 이렇게 하면 빈 객체가 됨
console.log(JSON.stringify(map)); // {}
```

### ✅ 올바른 직렬화 방법

#### 1. 배열로 변환 후 직렬화
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25],
  ['city', '서울']
]);

// Map을 배열로 변환
const array = Array.from(map);
console.log(array); // [['name', '김철수'], ['age', 25], ['city', '서울']]

// JSON으로 직렬화
const jsonString = JSON.stringify(array);
console.log(jsonString); // '[["name","김철수"],["age",25],["city","서울"]]'
```

#### 2. 객체로 변환 후 직렬화
```javascript
const map = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// Map을 객체로 변환
const obj = Object.fromEntries(map);
console.log(obj); // {name: '김철수', age: 25}

// JSON으로 직렬화
const jsonString = JSON.stringify(obj);
console.log(jsonString); // '{"name":"김철수","age":25}'
```

### 🔄 역직렬화 (JSON에서 Map으로 변환)

#### 배열 형태에서 복원
```javascript
const jsonString = '[["name","김철수"],["age",25]]';

// JSON을 배열로 파싱
const array = JSON.parse(jsonString);

// 배열을 Map으로 변환
const map = new Map(array);
console.log(map.get('name')); // '김철수'
```

#### 객체 형태에서 복원
```javascript
const jsonString = '{"name":"김철수","age":25}';

// JSON을 객체로 파싱
const obj = JSON.parse(jsonString);

// 객체를 Map으로 변환
const map = new Map(Object.entries(obj));
console.log(map.get('name')); // '김철수'
```

### 🎯 실용적인 직렬화 유틸리티
```javascript
class MapSerializer {
  // Map을 JSON 문자열로 변환
  static toJSON(map) {
    return JSON.stringify(Array.from(map));
  }

  // JSON 문자열을 Map으로 변환
  static fromJSON(jsonString) {
    const array = JSON.parse(jsonString);
    return new Map(array);
  }

  // Map을 객체로 변환
  static toObject(map) {
    return Object.fromEntries(map);
  }

  // 객체를 Map으로 변환
  static fromObject(obj) {
    return new Map(Object.entries(obj));
  }
}

// 사용 예시
const userMap = new Map([
  ['name', '김철수'],
  ['age', 25]
]);

// 직렬화
const jsonString = MapSerializer.toJSON(userMap);
console.log(jsonString); // '[["name","김철수"],["age",25]]'

// 역직렬화
const restoredMap = MapSerializer.fromJSON(jsonString);
console.log(restoredMap.get('name')); // '김철수'
```

---

## 주의사항과 팁

### ⚠️ 주요 주의사항

#### 1. NaN 키의 특별한 동작
```javascript
const map = new Map();

// NaN은 키로 사용 가능하지만, 모든 NaN이 같은 키로 취급됨
map.set(NaN, '값1');
map.set(NaN, '값2'); // 이전 값 덮어쓰기

console.log(map.get(NaN)); // '값2'
console.log(map.size); // 1 (NaN 키는 하나로 취급)
```

#### 2. 객체 키의 참조 비교
```javascript
const map = new Map();

const obj1 = {id: 1};
const obj2 = {id: 1};

map.set(obj1, '값1');
map.set(obj2, '값2');

console.log(map.get(obj1)); // '값1'
console.log(map.get(obj2)); // '값2'
console.log(map.size); // 2 (다른 객체 참조)

// 하지만 같은 내용의 객체라도 다른 참조이므로 다른 키로 취급됨
console.log(map.get({id: 1})); // undefined
```

#### 3. 직렬화 시 데이터 손실
```javascript
const map = new Map();
map.set({id: 1}, '객체 키');
map.set(() => {}, '함수 키');

// 직렬화하면 객체나 함수 키는 문자열로 변환되어 정보 손실
const array = Array.from(map);
console.log(array); // [['[object Object]', '객체 키'], ['() => {}', '함수 키']]
```

### 💡 성능 팁

#### 1. Map vs Object 성능 비교
```javascript
// Map: 키-값 추가/삭제가 빠름
const map = new Map();
const start1 = performance.now();

for (let i = 0; i < 10000; i++) {
  map.set(`key${i}`, `value${i}`);
}

const end1 = performance.now();
console.log(`Map 시간: ${end1 - start1}ms`);

// Object: 일반적인 접근이 빠름
const obj = {};
const start2 = performance.now();

for (let i = 0; i < 10000; i++) {
  obj[`key${i}`] = `value${i}`;
}

const end2 = performance.now();
console.log(`Object 시간: ${end2 - start2}ms`);
```

#### 2. 메모리 효율성
```javascript
// Map은 키-값 쌍을 자주 추가/삭제할 때 메모리 효율적
const map = new Map();

// 많은 데이터 추가
for (let i = 0; i < 1000; i++) {
  map.set(`key${i}`, `value${i}`);
}

// 일부 데이터 삭제
for (let i = 0; i < 500; i++) {
  map.delete(`key${i}`);
}

// Map은 삭제된 공간을 효율적으로 관리
console.log(map.size); // 500
```

### 🎯 실무에서 자주 사용하는 패턴

#### 1. 중복 제거
```javascript
const numbers = [1, 2, 2, 3, 3, 4, 5, 5];

// Set을 사용한 중복 제거
const uniqueNumbers = [...new Set(numbers)];
console.log(uniqueNumbers); // [1, 2, 3, 4, 5]

// Map을 사용한 중복 제거 (값이 중요한 경우)
const items = [
  {id: 1, name: '상품1'},
  {id: 2, name: '상품2'},
  {id: 1, name: '상품1'} // 중복
];

const uniqueItems = new Map();
items.forEach(item => {
  uniqueItems.set(item.id, item);
});

console.log([...uniqueItems.values()]); // 중복 제거된 상품들
```

#### 2. 캐싱 (메모이제이션)
```javascript
class Calculator {
  constructor() {
    this.cache = new Map();
  }

  factorial(n) {
    // 캐시에 있으면 반환
    if (this.cache.has(n)) {
      console.log(`캐시에서 반환: ${n}!`);
      return this.cache.get(n);
    }

    // 계산 수행
    let result = 1;
    for (let i = 2; i <= n; i++) {
      result *= i;
    }

    // 캐시에 저장
    this.cache.set(n, result);
    console.log(`계산 후 캐시 저장: ${n}! = ${result}`);
    
    return result;
  }
}

const calc = new Calculator();
console.log(calc.factorial(5)); // 계산 후 캐시 저장: 5! = 120
console.log(calc.factorial(5)); // 캐시에서 반환: 5!
```

#### 3. 이벤트 리스너 관리
```javascript
class EventManager {
  constructor() {
    this.listeners = new Map(); // 이벤트명을 키로, 리스너 배열을 값으로
  }

  on(eventName, listener) {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, []);
    }
    this.listeners.get(eventName).push(listener);
  }

  off(eventName, listener) {
    if (this.listeners.has(eventName)) {
      const listeners = this.listeners.get(eventName);
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  emit(eventName, data) {
    if (this.listeners.has(eventName)) {
      this.listeners.get(eventName).forEach(listener => {
        listener(data);
      });
    }
  }
}

// 사용 예시
const eventManager = new EventManager();

const handleClick = (data) => console.log('클릭됨:', data);
const handleHover = (data) => console.log('호버됨:', data);

eventManager.on('click', handleClick);
eventManager.on('hover', handleHover);

eventManager.emit('click', {x: 100, y: 200}); // 클릭됨: {x: 100, y: 200}
eventManager.emit('hover', {x: 150, y: 250}); // 호버됨: {x: 150, y: 250}
```

---

## 📚 정리

### Map의 핵심 특징
- ✅ **다양한 타입의 키 지원**: 문자열, 숫자, 객체, 함수 등
- ✅ **순서 보장**: 삽입된 순서대로 순회 가능
- ✅ **효율적인 추가/삭제**: 키-값 쌍의 동적 관리에 최적화
- ✅ **내장 메서드**: size, has, delete, clear 등 편리한 메서드 제공

### 언제 Map을 사용할까?
- 🔑 키가 문자열이 아닌 경우
- 📊 데이터의 순서가 중요한 경우
- ⚡ 키-값 쌍을 자주 추가/삭제하는 경우
- 🎯 특정 키의 존재 여부를 자주 확인하는 경우

### 언제 일반 객체를 사용할까?
- 🔑 키가 항상 문자열인 경우
- 📝 간단한 데이터 저장
- 🚀 최대 성능이 필요한 경우
- �� JSON과의 호환성이 중요한 경우 