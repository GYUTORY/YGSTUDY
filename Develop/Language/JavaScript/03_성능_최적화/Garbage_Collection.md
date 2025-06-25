# JavaScript 가비지 컬렉션 (Garbage Collection) 완벽 가이드

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

가비지 컬렉션(GC)은 프로그래머가 직접 메모리를 관리하지 않아도 되도록 자동으로 사용하지 않는 메모리를 해제하는 메모리 관리 기법입니다.

### 주요 특징
- **자동 메모리 관리**: 개발자가 수동으로 메모리를 해제할 필요 없음
- **메모리 안전성**: 댕글링 포인터나 메모리 누수 방지
- **성능 오버헤드**: GC 실행 시 일시적인 성능 저하 발생

---

## 🔍 메모리 관리의 필요성

### 메모리 누수의 위험성
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

---

## 🏗️ JavaScript 메모리 구조

### 1. 메모리 힙 (Memory Heap)
```javascript
// 힙에 저장되는 데이터
const obj = { name: 'John', age: 30 };  // 객체
const arr = [1, 2, 3, 4, 5];           // 배열
const func = function() { return true; }; // 함수
```

### 2. 콜 스택 (Call Stack)
```javascript
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);  // 재귀 호출로 스택 쌓임
}
```

### 3. 메모리 생명주기
1. **할당 (Allocation)**: 메모리 요청
2. **사용 (Use)**: 할당된 메모리 읽기/쓰기
3. **해제 (Release)**: 사용하지 않는 메모리 반환

---

## ⚙️ 가비지 컬렉션 알고리즘

### 1. Mark-and-Sweep 알고리즘

가장 일반적인 GC 알고리즘으로, 두 단계로 구성됩니다:

#### Mark 단계
```javascript
// 가비지 컬렉터가 도달 가능한 객체들을 마킹
function markPhase() {
    // 1. 루트 객체들에서 시작
    // 2. 루트에서 도달 가능한 모든 객체를 마킹
    // 3. 재귀적으로 모든 참조를 따라가며 마킹
}
```

#### Sweep 단계
```javascript
// 마킹되지 않은 객체들을 메모리에서 해제
function sweepPhase() {
    // 1. 힙 전체를 순회
    // 2. 마킹되지 않은 객체들을 해제
    // 3. 마킹된 객체들의 마크를 제거
}
```

### 2. Generational Garbage Collection

V8 엔진에서 사용하는 고급 GC 기법:

#### Young Generation (New Space)
```javascript
// 새로 생성된 객체들이 저장되는 공간
const newObject = { data: 'new' };  // Young generation에 할당
```

#### Old Generation (Old Space)
```javascript
// 오래 살아남은 객체들이 이동하는 공간
// 여러 번의 GC를 거쳐도 살아남은 객체들
```

### 3. Incremental Garbage Collection

```javascript
// GC를 여러 단계로 나누어 실행
// 사용자 인터페이스 블로킹 방지
function incrementalGC() {
    // 1. 짧은 시간 동안만 GC 실행
    // 2. 나머지 작업은 다음 틱에서 실행
    // 3. 사용자 경험 개선
}
```

---

## 🚨 메모리 누수 (Memory Leak)

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

---

## 🚀 성능 최적화 팁

### 1. 객체 풀링 (Object Pooling)
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

---

## 📊 실제 예제와 모니터링

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

---

## 🎯 결론

JavaScript의 가비지 컬렉션은 개발자가 메모리 관리를 신경 쓰지 않아도 되게 해주지만, 여전히 메모리 누수와 성능 문제를 피하기 위해서는 다음과 같은 점들을 고려해야 합니다:

### 핵심 포인트
1. **메모리 누수 패턴 이해**: 전역 변수, 클로저, 이벤트 리스너 등
2. **적절한 데이터 구조 선택**: WeakMap, TypedArray, Set 등 활용
3. **자원 해제 철저**: 타이머, 이벤트 리스너, 데이터베이스 커넥션 등
4. **정기적인 모니터링**: 메모리 사용량 추적 및 분석
5. **성능 최적화 도구 활용**: 프로파일링 및 디버깅 도구

### 성능 모니터링 도구
- **브라우저**: Chrome DevTools Memory 탭, `performance.memory` API
- **Node.js**: `process.memoryUsage()`, `v8.getHeapStatistics()`, `--inspect` 플래그
- **서버**: PM2 모니터링, Docker 메모리 제한
- **프로파일링**: heapdump, clinic.js, v8-profiler

가비지 컬렉션을 이해하고 올바르게 활용하면, JavaScript 애플리케이션의 메모리 효율성과 전반적인 성능을 크게 향상시킬 수 있습니다.

---

## 📚 참고 자료
- [MDN - Memory Management](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Memory_Management)
- [V8 Garbage Collection](https://v8.dev/blog/free-buffer)
- [JavaScript Memory Leaks](https://auth0.com/blog/four-types-of-leaks-in-your-javascript-code-and-how-to-get-rid-of-them/)
- [Node.js Memory Management](https://nodejs.org/en/docs/guides/memory-management/)
- [PM2 Memory Management](https://pm2.keymetrics.io/docs/usage/memory-limit/)
