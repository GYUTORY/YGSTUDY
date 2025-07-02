# JavaScript 가비지 컬렉션 (Garbage Collection) 완벽 가이드

> 💡 **이 문서는 JavaScript의 메모리 관리 시스템을 이해하고 싶은 개발자를 위한 가이드입니다.**

## 📋 목차
1. [가비지 컬렉션이란?](#가비지-컬렉션이란)
2. [메모리 관리의 필요성](#메모리-관리의-필요성)
3. [JavaScript 메모리 구조](#javascript-메모리-구조)
4. [가비지 컬렉션 알고리즘](#가비지-컬렉션-알고리즘)
5. [메모리 누수 (Memory Leak)](#메모리-누수-memory-leak)
6. [성능 최적화 팁](#성능-최적화-팁)
7. [실제 예제와 모니터링](#실제-예제와-모니터링)
8. [백엔드(Node.js) 환경에서의 메모리 관리](#백엔드nodejs-환경에서의-메모리-관리)
9. [서버 성능 최적화 전략](#서버-성능-최적화-전략)

---

## 🎯 가비지 컬렉션이란?

### 🏠 실생활 비유로 이해하기
**가비지 컬렉션은 집 청소부와 같습니다.**

- **우리가 하는 일**: 물건을 사용하고 필요 없으면 버리기만 하면 됨
- **청소부(GC)가 하는 일**: 버려진 물건들을 자동으로 수거해서 정리
- **결과**: 집이 깔끔하게 유지됨

### 기본 개념
가비지 컬렉션(GC)은 프로그래머가 직접 메모리를 관리하지 않아도 되도록 자동으로 사용하지 않는 메모리를 해제하는 메모리 관리 기법입니다.

**쉽게 설명하면**: 우리가 사용하지 않는 물건들을 자동으로 정리해주는 청소부 같은 역할을 합니다.

### 주요 특징
- **자동 메모리 관리**: 개발자가 수동으로 메모리를 해제할 필요 없음
- **메모리 안전성**: 댕글링 포인터나 메모리 누수 방지
- **성능 오버헤드**: GC 실행 시 일시적인 성능 저하 발생

### 📚 용어 설명
- **댕글링 포인터**: 이미 해제된 메모리를 가리키는 포인터 (마치 이미 철거된 건물 주소를 가지고 있는 것과 같음)
- **메모리 누수**: 사용하지 않는 메모리가 해제되지 않고 계속 쌓이는 현상 (마치 쓰레기통이 가득 차도 비우지 않는 것과 같음)
- **성능 오버헤드**: 추가적인 작업으로 인한 성능 저하 (청소부가 청소하는 동안 잠시 방해받는 것과 같음)

---

## 🔍 메모리 관리의 필요성

### 🚨 메모리 누수의 위험성
```javascript
// 메모리 누수 예제
function createLeak() {
    const element = document.getElementById('myElement');
    element.addEventListener('click', function() {
        // 이 함수는 element를 참조하므로 메모리 누수 발생
        console.log('Clicked!');
    });
}
```

### 수동 메모리 관리의 복잡성
- 포인터 관리의 어려움
- 메모리 해제 시점 판단의 복잡성
- 멀티스레드 환경에서의 동시성 문제

### 📚 용어 설명
- **포인터**: 메모리 주소를 가리키는 변수 (마치 집 주소를 적어둔 메모지와 같음)
- **멀티스레드**: 여러 작업이 동시에 실행되는 환경 (여러 사람이 동시에 집을 사용하는 것과 같음)
- **동시성**: 여러 작업이 동시에 일어나는 상황

---

## 🏗️ JavaScript 메모리 구조

### 🏠 집 구조로 비유하기
**JavaScript 메모리는 2층 집과 같습니다.**

- **1층 (콜 스택)**: 현재 사용 중인 공간 (거실, 주방)
- **2층 (메모리 힙)**: 물건을 보관하는 창고 (다락방, 창고)

### 1. 메모리 힙 (Memory Heap)
메모리 힙은 객체, 배열, 함수 등이 저장되는 공간입니다.

```javascript
// 힙에 저장되는 데이터
const obj = { name: 'John', age: 30 };  // 객체
const arr = [1, 2, 3, 4, 5];           // 배열
const func = function() { return true; }; // 함수
```

### 2. 콜 스택 (Call Stack)
함수 호출 정보가 저장되는 공간입니다.

```javascript
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);  // 재귀 호출로 스택 쌓임
}
```

### 3. 메모리 생명주기
1. **할당 (Allocation)**: 메모리 요청 (물건을 창고에 넣기)
2. **사용 (Use)**: 할당된 메모리 읽기/쓰기 (물건 사용하기)
3. **해제 (Release)**: 사용하지 않는 메모리 반환 (물건을 창고에서 빼기)

### 📚 용어 설명
- **재귀 호출**: 함수가 자기 자신을 호출하는 것 (마치 거울 속의 거울을 보는 것과 같음)
- **스택**: LIFO(Last In, First Out) 구조의 데이터 저장소 (마치 접시를 쌓아놓은 것과 같음 - 마지막에 쌓은 것을 먼저 사용)

---

## ⚙️ 가비지 컬렉션 알고리즘

### 🧹 청소 과정으로 이해하기
**가비지 컬렉션은 집 청소 과정과 같습니다.**

1. **Mark 단계**: 사용 중인 물건에 표시하기
2. **Sweep 단계**: 표시되지 않은 물건들을 버리기

### 1. Mark-and-Sweep 알고리즘

가장 일반적인 GC 알고리즘으로, 두 단계로 구성됩니다:

#### Mark 단계
가비지 컬렉터가 도달 가능한 객체들을 마킹합니다.

```javascript
// 가비지 컬렉터가 도달 가능한 객체들을 마킹
function markPhase() {
    // 1. 루트 객체들에서 시작 (현재 사용 중인 물건들)
    // 2. 루트에서 도달 가능한 모든 객체를 마킹 (연결된 물건들)
    // 3. 재귀적으로 모든 참조를 따라가며 마킹 (더 연결된 물건들)
}
```

#### Sweep 단계
마킹되지 않은 객체들을 메모리에서 해제합니다.

```javascript
// 마킹되지 않은 객체들을 메모리에서 해제
function sweepPhase() {
    // 1. 힙 전체를 순회 (집 전체를 둘러보기)
    // 2. 마킹되지 않은 객체들을 해제 (표시되지 않은 물건들 버리기)
    // 3. 마킹된 객체들의 마크를 제거 (표시 지우기)
}
```

### 2. Generational Garbage Collection

V8 엔진에서 사용하는 고급 GC 기법:

#### Young Generation (New Space)
새로 생성된 객체들이 저장되는 공간입니다.

```javascript
// 새로 생성된 객체들이 저장되는 공간
const newObject = { data: 'new' };  // Young generation에 할당
```

#### Old Generation (Old Space)
오래 살아남은 객체들이 이동하는 공간입니다.

```javascript
// 오래 살아남은 객체들이 이동하는 공간
// 여러 번의 GC를 거쳐도 살아남은 객체들
```

### 3. Incremental Garbage Collection

GC를 여러 단계로 나누어 실행하여 사용자 인터페이스 블로킹을 방지합니다.

```javascript
// GC를 여러 단계로 나누어 실행
// 사용자 인터페이스 블로킹 방지
function incrementalGC() {
    // 1. 짧은 시간 동안만 GC 실행 (잠시만 청소하기)
    // 2. 나머지 작업은 다음 틱에서 실행 (나중에 계속하기)
    // 3. 사용자 경험 개선 (방해받지 않기)
}
```

### 📚 용어 설명
- **루트 객체**: 전역 변수, 현재 실행 중인 함수의 지역 변수 등 (현재 사용 중인 물건들)
- **도달 가능한 객체**: 루트 객체에서 참조를 통해 접근할 수 있는 객체 (연결된 물건들)
- **블로킹**: 작업이 완료될 때까지 다른 작업을 멈추는 현상 (청소하는 동안 다른 일을 못하는 것)

---

## 🚨 메모리 누수 (Memory Leak)

### 🚨 메모리 누수란?
**메모리 누수는 쓰레기통을 비우지 않는 것과 같습니다.**

- 물건을 사용하고 버리지 않으면 계속 쌓임
- 결국 메모리가 가득 차서 프로그램이 느려지거나 멈춤

### 1. 전역 변수
```javascript
// ❌ 잘못된 예제
function createGlobalLeak() {
    // 'this'가 전역 객체를 참조
    this.leakedData = new Array(1000000);
}

// ✅ 올바른 예제
function createProperFunction() {
    const localData = new Array(1000000);
    // 함수 종료 시 자동으로 해제됨
}
```

### 2. 클로저 (Closure)
클로저는 함수가 선언될 때의 환경을 기억하는 함수입니다.

```javascript
// ❌ 메모리 누수 가능성
function createClosureLeak() {
    const largeData = new Array(1000000);
    
    return function() {
        console.log('Closure executed');
        // largeData가 클로저에 의해 계속 참조됨
    };
}

// ✅ 개선된 예제
function createOptimizedClosure() {
    const largeData = new Array(1000000);
    
    return function() {
        console.log('Closure executed');
        // 필요한 데이터만 참조하거나
        // 사용 후 참조 해제
    };
}
```

### 3. 이벤트 리스너
```javascript
// ❌ 메모리 누수
function addEventListenerLeak() {
    const button = document.getElementById('myButton');
    button.addEventListener('click', function() {
        console.log('Button clicked');
        // 이벤트 리스너가 제거되지 않음
    });
}

// ✅ 올바른 예제
function addEventListenerProper() {
    const button = document.getElementById('myButton');
    const handler = function() {
        console.log('Button clicked');
    };
    
    button.addEventListener('click', handler);
    
    // 필요시 리스너 제거
    // button.removeEventListener('click', handler);
}
```

### 4. 타이머와 인터벌
```javascript
// ❌ 메모리 누수
function createTimerLeak() {
    setInterval(() => {
        console.log('Timer running');
        // clearInterval이 호출되지 않음
    }, 1000);
}

// ✅ 올바른 예제
function createTimerProper() {
    const intervalId = setInterval(() => {
        console.log('Timer running');
    }, 1000);
    
    // 필요시 타이머 정리
    // clearInterval(intervalId);
}
```

### 📚 용어 설명
- **클로저**: 함수가 선언될 때의 환경을 기억하는 함수 (마치 사진을 찍어서 그 순간을 기억하는 것과 같음)
- **이벤트 리스너**: 특정 이벤트가 발생했을 때 실행되는 함수 (마치 문이 열리면 알람이 울리는 것과 같음)
- **타이머**: 일정 시간 후에 실행되는 함수 (마치 알람 시계와 같음)
- **인터벌**: 일정 시간마다 반복 실행되는 함수 (마치 매일 같은 시간에 울리는 알람과 같음)

---

## 🚀 성능 최적화 팁

### 🎯 최적화의 목표
**메모리 사용을 효율적으로 만들어 프로그램을 빠르게 만드는 것이 목표입니다.**

### 1. 객체 풀링 (Object Pooling)
객체를 재사용하여 메모리 할당/해제 비용을 줄이는 기법입니다.

**쉽게 설명하면**: 물건을 버리지 말고 다시 사용하는 것과 같습니다.

```javascript
class ObjectPool {
    constructor(createFn, resetFn, initialSize = 10) {
        this.createFn = createFn;
        this.resetFn = resetFn;
        this.pool = [];
        
        // 초기 객체들 생성
        for (let i = 0; i < initialSize; i++) {
            this.pool.push(createFn());
        }
    }
    
    acquire() {
        return this.pool.pop() || this.createFn();
    }
    
    release(obj) {
        this.resetFn(obj);
        this.pool.push(obj);
    }
}

// 사용 예제
const particlePool = new ObjectPool(
    () => ({ x: 0, y: 0, velocity: 0 }),
    (particle) => { particle.x = 0; particle.y = 0; particle.velocity = 0; }
);
```

### 2. WeakMap과 WeakSet 활용
WeakMap과 WeakSet은 키 객체가 해제되면 자동으로 엔트리가 제거됩니다.

**쉽게 설명하면**: 물건이 없어지면 자동으로 정리되는 메모장과 같습니다.

```javascript
// ❌ 일반 Map 사용
const cache = new Map();
function cacheWithMap(key, value) {
    cache.set(key, value);
    // key 객체가 해제되어도 cache에서 참조가 유지됨
}

// ✅ WeakMap 사용
const weakCache = new WeakMap();
function cacheWithWeakMap(key, value) {
    weakCache.set(key, value);
    // key 객체가 해제되면 자동으로 cache에서도 제거됨
}
```

### 3. 메모리 효율적인 데이터 구조
```javascript
// ❌ 비효율적인 배열 사용
const largeArray = new Array(1000000).fill(0);

// ✅ TypedArray 사용 (메모리 효율적)
const efficientArray = new Uint8Array(1000000);

// ✅ Set 사용 (중복 제거)
const uniqueValues = new Set([1, 2, 2, 3, 3, 4]);
```

### 4. 실용적인 최적화 팁

#### 4.1 변수 스코프 최소화
```javascript
// ❌ 전역 변수 사용
let globalData = [];

function processData() {
    globalData.push('data');
}

// ✅ 지역 변수 사용
function processData() {
    const localData = [];
    localData.push('data');
    return localData;
}
```

#### 4.2 불필요한 객체 생성 방지
```javascript
// ❌ 매번 새로운 객체 생성
function createUser(name, age) {
    return { name, age, timestamp: new Date() };
}

// ✅ 객체 재사용
const userTemplate = { name: '', age: 0, timestamp: null };
function createUser(name, age) {
    const user = Object.create(userTemplate);
    user.name = name;
    user.age = age;
    user.timestamp = new Date();
    return user;
}
```

### 📚 용어 설명
- **객체 풀링**: 객체를 미리 생성해두고 재사용하는 기법 (마치 도서관에서 책을 빌리고 반납하는 것과 같음)
- **WeakMap**: 키가 약한 참조를 가지는 Map (물건이 없어지면 자동으로 정리되는 메모장)
- **WeakSet**: 값이 약한 참조를 가지는 Set
- **TypedArray**: 특정 타입의 데이터만 저장하는 배열 (마치 특정 크기의 상자에만 물건을 담는 것과 같음)
- **스코프**: 변수가 사용될 수 있는 범위 (마치 집의 방과 같음 - 방 안에서만 사용 가능)

---

## 📊 실제 예제와 모니터링

### 🔍 모니터링의 중요성
**메모리 사용량을 지켜보는 것은 건강검진과 같습니다.**

- 정기적으로 체크해서 문제를 미리 발견
- 이상이 있으면 즉시 대응

### 1. 메모리 사용량 모니터링
```javascript
// 메모리 사용량 확인
function logMemoryUsage() {
    if (performance.memory) {
        console.log('Used JS Heap Size:', performance.memory.usedJSHeapSize);
        console.log('Total JS Heap Size:', performance.memory.totalJSHeapSize);
        console.log('JS Heap Size Limit:', performance.memory.jsHeapSizeLimit);
    }
}

// 주기적으로 메모리 사용량 체크
setInterval(logMemoryUsage, 5000);
```

### 2. 메모리 누수 감지
```javascript
class MemoryLeakDetector {
    constructor() {
        this.snapshots = [];
    }
    
    takeSnapshot() {
        if (performance.memory) {
            this.snapshots.push({
                timestamp: Date.now(),
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize
            });
        }
    }
    
    analyzeLeaks() {
        if (this.snapshots.length < 2) return;
        
        const latest = this.snapshots[this.snapshots.length - 1];
        const previous = this.snapshots[this.snapshots.length - 2];
        
        const growth = latest.used - previous.used;
        console.log(`Memory growth: ${growth} bytes`);
        
        if (growth > 1000000) { // 1MB 이상 증가
            console.warn('Potential memory leak detected!');
        }
    }
}
```

### 3. 실전 예제: 이미지 캐싱
```javascript
class ImageCache {
    constructor(maxSize = 50) {
        this.cache = new Map();
        this.maxSize = maxSize;
    }
    
    async loadImage(url) {
        if (this.cache.has(url)) {
            return this.cache.get(url);
        }
        
        const img = new Image();
        const promise = new Promise((resolve, reject) => {
            img.onload = () => resolve(img);
            img.onerror = reject;
        });
        
        img.src = url;
        
        // 캐시 크기 제한
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(url, promise);
        return promise;
    }
    
    clear() {
        this.cache.clear();
    }
}
```

### 4. 실용적인 모니터링 도구

#### 4.1 브라우저 개발자 도구 활용
```javascript
// Chrome DevTools에서 사용할 수 있는 코드
function debugMemory() {
    // 메모리 사용량 로그
    console.log('Memory Usage:', performance.memory);
    
    // 가비지 컬렉션 강제 실행 (개발 환경에서만)
    if (window.gc) {
        window.gc();
        console.log('Garbage collection triggered');
    }
}
```

#### 4.2 성능 측정
```javascript
// 함수 실행 시간 측정
function measurePerformance(fn, iterations = 1000) {
    const start = performance.now();
    
    for (let i = 0; i < iterations; i++) {
        fn();
    }
    
    const end = performance.now();
    console.log(`Average execution time: ${(end - start) / iterations}ms`);
}

// 사용 예제
measurePerformance(() => {
    const arr = new Array(1000).fill(0);
    return arr.map(x => x * 2);
});
```

### 📚 용어 설명
- **스냅샷**: 특정 시점의 상태를 저장한 것 (마치 사진을 찍는 것과 같음)
- **캐싱**: 자주 사용되는 데이터를 임시로 저장하는 기법 (마치 자주 사용하는 물건을 가까이 두는 것과 같음)
- **LRU**: Least Recently Used, 가장 오래 사용되지 않은 것을 먼저 제거하는 알고리즘 (마치 오래된 음식을 먼저 먹는 것과 같음)
- **성능 측정**: 프로그램이 얼마나 빠르게 실행되는지 확인하는 것

---

## 🖥️ 백엔드(Node.js) 환경에서의 메모리 관리

### 1. Node.js 특화 메모리 누수

#### 1.1 데이터베이스 커넥션 누수
```javascript
const mysql = require('mysql2');
const pool = mysql.createPool({ connectionLimit: 10, /* ... */ });

// ❌ 누수 예시: 커넥션 반환 안함
function leakDbConn() {
    pool.getConnection((err, conn) => {
        if (err) return;
        conn.query('SELECT 1', () => {
            // conn.release() 빠짐! 누수 발생
        });
    });
}

// ✅ 해결: 항상 release 호출
function safeDbConn() {
    pool.getConnection((err, conn) => {
        if (err) return;
        conn.query('SELECT 1', () => {
            conn.release(); // 커넥션 반환
        });
    });
}
```

#### 1.2 무한 캐시/맵 누수
```javascript
// ❌ 누수 예시: 크기 제한 없는 캐시
const cache = new Map();
function addToCache(key, value) {
    cache.set(key, value); // 계속 쌓이면 메모리 폭증
}

// ✅ 해결: LRU 캐시 구현
class LRUCache {
    constructor(max = 100) {
        this.max = max;
        this.cache = new Map();
    }
    
    get(key) {
        if (!this.cache.has(key)) return undefined;
        const value = this.cache.get(key);
        this.cache.delete(key);
        this.cache.set(key, value);
        return value;
    }
    
    set(key, value) {
        if (this.cache.has(key)) this.cache.delete(key);
        else if (this.cache.size >= this.max) {
            this.cache.delete(this.cache.keys().next().value);
        }
        this.cache.set(key, value);
    }
}
```

#### 1.3 스트림 미사용으로 인한 메모리 폭증
```javascript
const fs = require('fs');

// ❌ 누수 예시: 대용량 파일을 한 번에 읽음
function readBigFileSync() {
    const data = fs.readFileSync('bigfile.txt'); // 메모리 부족 위험
}

// ✅ 해결: 스트림 사용
function readBigFileStream() {
    const stream = fs.createReadStream('bigfile.txt');
    stream.on('data', chunk => {
        // 청크 단위로 처리
    });
}
```

#### 1.4 워커/서브프로세스 누수
```javascript
const { Worker } = require('worker_threads');

// ❌ 누수 예시: 워커 종료 안함
function leakWorker() {
    const worker = new Worker('./worker.js');
    // worker.terminate() 호출 안함
}

// ✅ 해결: 작업 완료 후 종료
function safeWorker() {
    const worker = new Worker('./worker.js');
    worker.on('exit', () => console.log('worker 종료'));
    // 필요시 worker.terminate() 호출
}
```

### 2. Node.js 메모리 모니터링

#### 2.1 프로세스 메모리 사용량 체크
```javascript
setInterval(() => {
    const mu = process.memoryUsage();
    console.log(`heapUsed: ${(mu.heapUsed/1024/1024).toFixed(2)}MB, rss: ${(mu.rss/1024/1024).toFixed(2)}MB`);
}, 10000);
```

#### 2.2 GC 강제 실행 및 모니터링
```javascript
// node --expose-gc 옵션 필요
if (global.gc) {
    setInterval(() => {
        const before = process.memoryUsage().heapUsed;
        global.gc();
        const after = process.memoryUsage().heapUsed;
        console.log(`GC 실행, 해제된 메모리: ${((before-after)/1024/1024).toFixed(2)}MB`);
    }, 60000);
}
```

#### 2.3 V8 힙 통계
```javascript
const v8 = require('v8');
console.log(v8.getHeapStatistics());
```

### 용어 설명
- **커넥션 풀**: 데이터베이스 연결을 미리 생성해두고 재사용하는 기법
- **스트림**: 데이터를 청크 단위로 처리하는 방식
- **워커**: 별도의 스레드에서 실행되는 프로세스
- **RSS**: Resident Set Size, 프로세스가 실제로 사용하는 메모리 크기

---

## 🚀 서버 성능 최적화 전략

### 1. 메모리 제한 설정
```bash
# Node.js 메모리 제한 설정 (2GB)
node --max-old-space-size=2048 app.js

# PM2 메모리 제한 설정
pm2 start app.js --max-memory-restart 2G
```

### 2. 실전 최적화 팁

#### 2.1 자원 관리
- **커넥션 풀**: 데이터베이스 커넥션 재사용
- **캐시 관리**: LRU 캐시로 메모리 사용량 제한
- **이벤트 리스너**: 컴포넌트 해제 시 리스너 정리
- **스트림 활용**: 대용량 데이터 처리 시 메모리 효율성

#### 2.2 모니터링 도구
- **Chrome DevTools**: Memory 탭으로 힙 스냅샷 분석
- **Node.js Inspector**: `--inspect` 플래그로 디버깅
- **PM2**: 실시간 메모리 모니터링
- **Docker**: 컨테이너 메모리 제한 및 모니터링

#### 2.3 프로파일링 도구
- **heapdump**: 힙 덤프 생성 및 분석
- **clinic.js**: Node.js 성능 프로파일링
- **v8-profiler**: V8 엔진 프로파일링

### 용어 설명
- **프로파일링**: 프로그램의 성능을 분석하는 과정
- **힙 덤프**: 메모리 힙의 상태를 파일로 저장한 것
- **컨테이너**: 격리된 환경에서 실행되는 애플리케이션

---

## 🎯 결론

### 💡 핵심 요약
JavaScript의 가비지 컬렉션은 개발자가 메모리 관리를 신경 쓰지 않아도 되게 해주지만, 여전히 메모리 누수와 성능 문제를 피하기 위해서는 다음과 같은 점들을 고려해야 합니다:

### 🔑 핵심 포인트

#### 1. 메모리 누수 패턴 이해
- **전역 변수**: 전역에 데이터를 저장하지 말고 지역 변수 사용
- **클로저**: 필요한 데이터만 참조하고 사용 후 해제
- **이벤트 리스너**: 컴포넌트 해제 시 리스너도 함께 제거
- **타이머**: clearInterval, clearTimeout으로 정리

#### 2. 적절한 데이터 구조 선택
- **WeakMap/WeakSet**: 자동 정리가 필요한 경우 사용
- **TypedArray**: 대용량 데이터 처리 시 메모리 효율적
- **Set**: 중복 제거가 필요한 경우 사용
- **객체 풀링**: 자주 생성/해제되는 객체 재사용

#### 3. 자원 해제 철저
```javascript
// ✅ 좋은 예제
function cleanup() {
    // 타이머 정리
    clearInterval(intervalId);
    
    // 이벤트 리스너 제거
    element.removeEventListener('click', handler);
    
    // 캐시 정리
    cache.clear();
    
    // 데이터베이스 커넥션 반환
    connection.release();
}
```

#### 4. 정기적인 모니터링
```javascript
// 메모리 사용량 체크
setInterval(() => {
    const memory = performance.memory;
    if (memory.usedJSHeapSize > 100 * 1024 * 1024) { // 100MB
        console.warn('High memory usage detected!');
    }
}, 30000); // 30초마다 체크
```

#### 5. 성능 최적화 도구 활용
- **브라우저**: Chrome DevTools Memory 탭, `performance.memory` API
- **Node.js**: `process.memoryUsage()`, `v8.getHeapStatistics()`, `--inspect` 플래그
- **서버**: PM2 모니터링, Docker 메모리 제한
- **프로파일링**: heapdump, clinic.js, v8-profiler


## 📚 참고 자료
- [MDN - Memory Management](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Memory_Management)
- [V8 Garbage Collection](https://v8.dev/blog/free-buffer)
- [JavaScript Memory Leaks](https://auth0.com/blog/four-types-of-leaks-in-your-javascript-code-and-how-to-get-rid-of-them/)
- [Node.js Memory Management](https://nodejs.org/en/docs/guides/memory-management/)
- [PM2 Memory Management](https://pm2.keymetrics.io/docs/usage/memory-limit/)
