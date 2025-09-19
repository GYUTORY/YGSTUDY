# Node.js 성능 최적화 및 프로파일링 가이드 (Node.js Performance Optimization and Profiling Guide)

## 목차 (Table of Contents)
1. [Node.js 성능 최적화 개요 (Node.js Performance Optimization Overview)](#nodejs-성능-최적화-개요)
2. [성능 프로파일링 도구 (Performance Profiling Tools)](#성능-프로파일링-도구)
3. [메모리 누수 탐지 및 해결 (Memory Leak Detection and Resolution)](#메모리-누수-탐지-및-해결)
4. [CPU 사용률 최적화 (CPU Usage Optimization)](#cpu-사용률-최적화)
5. [비동기 처리 최적화 (Asynchronous Processing Optimization)](#비동기-처리-최적화) 📌 *기존 파일들 통합*
6. [실제 성능 병목 지점 분석 및 해결 사례 (Real Performance Bottleneck Analysis and Solutions)](#실제-성능-병목-지점-분석-및-해결-사례)
7. [성능 모니터링 및 알림 (Performance Monitoring and Alerting)](#성능-모니터링-및-알림)

### 📌 통합된 기존 파일들
이 가이드는 다음 기존 파일들의 내용을 통합하여 더 체계적으로 정리한 것입니다:
- **논블로킹 I/O**: 논블로킹 개념, 블로킹 vs 논블로킹 비교, 실행 순서 예제, 활용 사례
- **Promise**: Promise 기초, 체이닝, 고급 패턴, API 클라이언트 구현
- **async/await**: async/await 문법, 에러 처리, 실용적인 예제들
- **Event Loop**: 이벤트 루프 동작 과정, 마이크로태스크/매크로태스크 큐, 실행 우선순위

## Node.js 성능 최적화 개요 (Node.js Performance Optimization Overview)

Node.js 성능 최적화는 애플리케이션의 응답 시간, 처리량, 리소스 사용률을 개선하여 더 나은 사용자 경험과 비용 효율성을 달성하는 과정입니다.

### 성능 최적화의 핵심 원칙 (Core Performance Optimization Principles)

1. **측정 우선 (Measure First)**: 최적화 전에 현재 성능을 정확히 측정
2. **병목 지점 식별 (Identify Bottlenecks)**: 실제 성능 저하 원인 파악
3. **점진적 개선 (Incremental Improvement)**: 한 번에 하나씩 최적화
4. **지속적 모니터링 (Continuous Monitoring)**: 성능 변화 추적

### Node.js 성능 특성 (Node.js Performance Characteristics)

- **싱글 스레드 이벤트 루프**: CPU 집약적 작업에 취약
- **비동기 I/O**: I/O 바운드 작업에 강점
- **메모리 관리**: V8 엔진의 가비지 컬렉션 의존
- **모듈 시스템**: CommonJS와 ES Modules의 성능 차이

## 성능 프로파일링 도구 (Performance Profiling Tools)

### 1. Clinic.js - 종합 성능 진단 도구

#### Clinic.js 설치 및 기본 사용법
```bash
# Clinic.js 설치
npm install -g clinic

# 기본 성능 진단
clinic doctor -- node app.js

# 특정 기능별 진단
clinic bubbleprof -- node app.js  # 비동기 흐름 분석
clinic flame -- node app.js       # CPU 사용률 분석
clinic heapprofiler -- node app.js # 메모리 사용량 분석
```

#### Clinic.js 설정 및 고급 사용법
```javascript
// clinic.config.js
module.exports = {
  // 진단 설정
  doctor: {
    duration: 30000,  // 30초간 진단
    sampleInterval: 10, // 10ms 간격 샘플링
    threshold: 100    // 100ms 이상 지연 시 경고
  },
  
  // 메모리 프로파일링 설정
  heapprofiler: {
    duration: 60000,  // 60초간 메모리 추적
    sampleInterval: 100, // 100ms 간격 샘플링
    maxMemory: 512    // 512MB 메모리 제한
  },
  
  // CPU 프로파일링 설정
  flame: {
    duration: 30000,  // 30초간 CPU 추적
    sampleInterval: 1, // 1ms 간격 샘플링
    threshold: 0.1    // 0.1% 이상 CPU 사용 시 추적
  }
};
```

### 2. 0x - V8 프로파일링 도구

#### 0x 설치 및 사용법
```bash
# 0x 설치
npm install -g 0x

# 기본 프로파일링
0x -- node app.js

# 고급 옵션
0x --on-port 'echo "서버 시작됨"' -- node app.js
0x --collect-only -- node app.js
```

#### 0x 결과 분석
```javascript
// 0x 결과 해석을 위한 헬퍼 함수
class ZeroXAnalyzer {
  constructor() {
    this.hotSpots = [];
    this.memoryLeaks = [];
  }
  
  // 핫스팟 분석
  analyzeHotSpots(profileData) {
    const functions = profileData.nodes;
    const hotSpots = functions
      .filter(node => node.selfTime > 100) // 100ms 이상 실행
      .sort((a, b) => b.selfTime - a.selfTime)
      .slice(0, 10); // 상위 10개
      
    return hotSpots.map(spot => ({
      function: spot.functionName,
      selfTime: spot.selfTime,
      totalTime: spot.totalTime,
      calls: spot.callCount,
      location: spot.location
    }));
  }
  
  // 메모리 누수 패턴 감지
  detectMemoryLeaks(profileData) {
    const leaks = [];
    
    // 큰 객체 할당 패턴
    const largeAllocations = profileData.nodes
      .filter(node => node.selfSize > 1024 * 1024) // 1MB 이상
      .map(node => ({
        type: 'Large Allocation',
        size: node.selfSize,
        function: node.functionName,
        location: node.location
      }));
      
    leaks.push(...largeAllocations);
    
    return leaks;
  }
}
```

### 3. Node.js 내장 프로파일링 도구

#### --prof 플래그를 사용한 프로파일링
```bash
# V8 프로파일링 활성화
node --prof app.js

# 프로파일링 결과 분석
node --prof-process isolate-*.log > profile.txt
```

#### --inspect 플래그를 사용한 디버깅
```bash
# Chrome DevTools 연결
node --inspect app.js

# 브레이크포인트 설정
node --inspect-brk app.js
```

#### 내장 프로파일링 스크립트
```javascript
// profiling.js
const fs = require('fs');
const path = require('path');

class NodeProfiler {
  constructor() {
    this.startTime = Date.now();
    this.memoryUsage = [];
    this.cpuUsage = [];
  }
  
  // 메모리 사용량 추적
  trackMemory() {
    const usage = process.memoryUsage();
    this.memoryUsage.push({
      timestamp: Date.now(),
      rss: usage.rss,
      heapTotal: usage.heapTotal,
      heapUsed: usage.heapUsed,
      external: usage.external
    });
  }
  
  // CPU 사용률 추적
  trackCPU() {
    const usage = process.cpuUsage();
    this.cpuUsage.push({
      timestamp: Date.now(),
      user: usage.user,
      system: usage.system
    });
  }
  
  // 프로파일링 결과 저장
  saveProfile() {
    const profile = {
      duration: Date.now() - this.startTime,
      memoryUsage: this.memoryUsage,
      cpuUsage: this.cpuUsage,
      summary: this.generateSummary()
    };
    
    fs.writeFileSync(
      path.join(__dirname, 'profile.json'),
      JSON.stringify(profile, null, 2)
    );
  }
  
  // 요약 정보 생성
  generateSummary() {
    const avgMemory = this.memoryUsage.reduce((sum, m) => sum + m.heapUsed, 0) / this.memoryUsage.length;
    const maxMemory = Math.max(...this.memoryUsage.map(m => m.heapUsed));
    
    return {
      averageMemoryUsage: avgMemory,
      maxMemoryUsage: maxMemory,
      memoryGrowth: maxMemory - this.memoryUsage[0].heapUsed,
      totalSamples: this.memoryUsage.length
    };
  }
}

// 사용 예시
const profiler = new NodeProfiler();

// 1초마다 메모리 추적
setInterval(() => {
  profiler.trackMemory();
  profiler.trackCPU();
}, 1000);

// 30초 후 프로파일링 결과 저장
setTimeout(() => {
  profiler.saveProfile();
  process.exit(0);
}, 30000);
```

## 메모리 누수 탐지 및 해결 (Memory Leak Detection and Resolution)

### 1. 메모리 누수 패턴 및 감지

#### 일반적인 메모리 누수 패턴
```javascript
// 메모리 누수 패턴 예시
class MemoryLeakPatterns {
  constructor() {
    this.listeners = new Map();
    this.timers = new Set();
    this.data = new Map();
  }
  
  // 1. 이벤트 리스너 누수
  addEventListenerLeak(element, eventType, handler) {
    element.addEventListener(eventType, handler);
    // 문제: 이벤트 리스너가 제거되지 않음
  }
  
  // 해결책: 적절한 제거
  addEventListenerSafe(element, eventType, handler) {
    element.addEventListener(eventType, handler);
    
    // 제거 함수 반환
    return () => {
      element.removeEventListener(eventType, handler);
    };
  }
  
  // 2. 타이머 누수
  createTimerLeak() {
    const timer = setInterval(() => {
      console.log('타이머 실행 중...');
    }, 1000);
    // 문제: clearInterval이 호출되지 않음
  }
  
  // 해결책: 타이머 관리
  createTimerSafe() {
    const timer = setInterval(() => {
      console.log('타이머 실행 중...');
    }, 1000);
    
    this.timers.add(timer);
    
    return () => {
      clearInterval(timer);
      this.timers.delete(timer);
    };
  }
  
  // 3. 클로저 누수
  createClosureLeak() {
    const largeData = new Array(1000000).fill('data');
    
    return function() {
      console.log('클로저에서 largeData 참조');
      // 문제: largeData가 계속 메모리에 유지됨
    };
  }
  
  // 해결책: 필요 없을 때 null 설정
  createClosureSafe() {
    let largeData = new Array(1000000).fill('data');
    
    return function() {
      console.log('클로저에서 largeData 참조');
      // 사용 후 참조 해제
      largeData = null;
    };
  }
}
```

### 2. 메모리 누수 감지 도구

#### heapdump를 사용한 메모리 스냅샷
```bash
# heapdump 설치
npm install heapdump
```

```javascript
// heapdump 사용 예시
const heapdump = require('heapdump');

class MemoryLeakDetector {
  constructor() {
    this.snapshots = [];
    this.leakThreshold = 50 * 1024 * 1024; // 50MB
  }
  
  // 메모리 스냅샷 생성
  takeSnapshot(label) {
    const filename = `heap-${Date.now()}-${label}.heapsnapshot`;
    heapdump.writeSnapshot(filename, (err, filename) => {
      if (err) {
        console.error('스냅샷 생성 실패:', err);
        return;
      }
      
      console.log('메모리 스냅샷 생성:', filename);
      this.snapshots.push({ filename, timestamp: Date.now() });
    });
  }
  
  // 메모리 사용량 모니터링
  monitorMemory() {
    setInterval(() => {
      const usage = process.memoryUsage();
      
      if (usage.heapUsed > this.leakThreshold) {
        console.warn('⚠️ 메모리 사용량이 임계값을 초과했습니다:', usage.heapUsed);
        this.takeSnapshot('high-memory');
      }
      
      // 메모리 사용량 로깅
      console.log('메모리 사용량:', {
        rss: (usage.rss / 1024 / 1024).toFixed(2) + ' MB',
        heapTotal: (usage.heapTotal / 1024 / 1024).toFixed(2) + ' MB',
        heapUsed: (usage.heapUsed / 1024 / 1024).toFixed(2) + ' MB',
        external: (usage.external / 1024 / 1024).toFixed(2) + ' MB'
      });
    }, 5000); // 5초마다 체크
  }
}

// 사용 예시
const detector = new MemoryLeakDetector();
detector.monitorMemory();

// 초기 스냅샷
detector.takeSnapshot('initial');
```

### 3. 메모리 누수 해결 전략

#### WeakMap과 WeakSet 활용
```javascript
// WeakMap을 사용한 메모리 효율적인 캐싱
class WeakMapCache {
  constructor() {
    this.cache = new WeakMap();
  }
  
  set(key, value) {
    this.cache.set(key, value);
  }
  
  get(key) {
    return this.cache.get(key);
  }
  
  has(key) {
    return this.cache.has(key);
  }
}

// WeakSet을 사용한 객체 추적
class ObjectTracker {
  constructor() {
    this.trackedObjects = new WeakSet();
  }
  
  track(obj) {
    this.trackedObjects.add(obj);
  }
  
  isTracked(obj) {
    return this.trackedObjects.has(obj);
  }
}
```

#### 메모리 풀링 패턴
```javascript
// 객체 풀링을 통한 메모리 최적화
class ObjectPool {
  constructor(createFn, resetFn, initialSize = 10) {
    this.createFn = createFn;
    this.resetFn = resetFn;
    this.pool = [];
    
    // 초기 객체 생성
    for (let i = 0; i < initialSize; i++) {
      this.pool.push(this.createFn());
    }
  }
  
  acquire() {
    if (this.pool.length > 0) {
      return this.pool.pop();
    }
    return this.createFn();
  }
  
  release(obj) {
    this.resetFn(obj);
    this.pool.push(obj);
  }
}

// 사용 예시
const userPool = new ObjectPool(
  () => ({ id: null, name: null, email: null }),
  (user) => {
    user.id = null;
    user.name = null;
    user.email = null;
  }
);

// 객체 사용
const user = userPool.acquire();
user.id = 1;
user.name = 'John';
user.email = 'john@example.com';

// 사용 후 반환
userPool.release(user);
```

## CPU 사용률 최적화 (CPU Usage Optimization)

### 1. CPU 집약적 작업 최적화

#### Worker Threads를 사용한 CPU 집약적 작업 분산
```javascript
// worker.js
const { parentPort, workerData } = require('worker_threads');

// CPU 집약적 작업
function heavyComputation(data) {
  let result = 0;
  for (let i = 0; i < data.length; i++) {
    result += Math.sqrt(data[i] * data[i] + data[i]);
  }
  return result;
}

// 워커에서 작업 실행
const result = heavyComputation(workerData);
parentPort.postMessage(result);
```

```javascript
// main.js
const { Worker } = require('worker_threads');
const path = require('path');

class CPUOptimizer {
  constructor(numWorkers = require('os').cpus().length) {
    this.numWorkers = numWorkers;
    this.workers = [];
    this.taskQueue = [];
    this.activeWorkers = 0;
  }
  
  // 워커 초기화
  initializeWorkers() {
    for (let i = 0; i < this.numWorkers; i++) {
      const worker = new Worker(path.join(__dirname, 'worker.js'));
      this.workers.push(worker);
    }
  }
  
  // CPU 집약적 작업을 워커에 위임
  async processData(data) {
    return new Promise((resolve, reject) => {
      const worker = this.getAvailableWorker();
      
      if (!worker) {
        // 모든 워커가 사용 중이면 큐에 추가
        this.taskQueue.push({ data, resolve, reject });
        return;
      }
      
      this.activeWorkers++;
      
      worker.postMessage(data);
      
      worker.once('message', (result) => {
        this.activeWorkers--;
        resolve(result);
        this.processNextTask();
      });
      
      worker.once('error', (error) => {
        this.activeWorkers--;
        reject(error);
        this.processNextTask();
      });
    });
  }
  
  // 사용 가능한 워커 찾기
  getAvailableWorker() {
    return this.workers.find(worker => !worker.busy);
  }
  
  // 다음 작업 처리
  processNextTask() {
    if (this.taskQueue.length > 0) {
      const task = this.taskQueue.shift();
      this.processData(task.data).then(task.resolve).catch(task.reject);
    }
  }
}

// 사용 예시
const optimizer = new CPUOptimizer();
optimizer.initializeWorkers();

// 대량 데이터 처리
const largeData = Array.from({ length: 1000000 }, (_, i) => i);
optimizer.processData(largeData).then(result => {
  console.log('처리 결과:', result);
});
```

### 2. 알고리즘 최적화

#### 효율적인 데이터 구조 사용
```javascript
// Set을 사용한 중복 제거 최적화
class DataOptimizer {
  // 비효율적인 중복 제거
  removeDuplicatesSlow(arr) {
    const result = [];
    for (let i = 0; i < arr.length; i++) {
      if (result.indexOf(arr[i]) === -1) {
        result.push(arr[i]);
      }
    }
    return result;
  }
  
  // 효율적인 중복 제거
  removeDuplicatesFast(arr) {
    return [...new Set(arr)];
  }
  
  // Map을 사용한 빠른 검색
  createLookupMap(data) {
    const map = new Map();
    data.forEach((item, index) => {
      map.set(item.id, { ...item, index });
    });
    return map;
  }
  
  // 빠른 검색
  findById(map, id) {
    return map.get(id);
  }
}
```

#### 메모이제이션을 통한 계산 최적화
```javascript
// 메모이제이션 데코레이터
function memoize(fn) {
  const cache = new Map();
  
  return function(...args) {
    const key = JSON.stringify(args);
    
    if (cache.has(key)) {
      return cache.get(key);
    }
    
    const result = fn.apply(this, args);
    cache.set(key, result);
    return result;
  };
}

// 피보나치 수열 계산 최적화
const fibonacci = memoize(function(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
});

// 사용 예시
console.time('fibonacci');
console.log(fibonacci(40));
console.timeEnd('fibonacci');
```

### 3. 비동기 처리 최적화

#### Promise.all을 사용한 병렬 처리
```javascript
// 순차 처리 (비효율적)
async function processSequentially(items) {
  const results = [];
  for (const item of items) {
    const result = await processItem(item);
    results.push(result);
  }
  return results;
}

// 병렬 처리 (효율적)
async function processInParallel(items) {
  const promises = items.map(item => processItem(item));
  return Promise.all(promises);
}

// 제한된 병렬 처리
async function processWithLimit(items, limit = 5) {
  const results = [];
  
  for (let i = 0; i < items.length; i += limit) {
    const batch = items.slice(i, i + limit);
    const batchPromises = batch.map(item => processItem(item));
    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults);
  }
  
  return results;
}
```

#### 스트림을 사용한 대용량 데이터 처리
```javascript
const fs = require('fs');
const { Transform } = require('stream');

// 대용량 파일 처리 최적화
class DataProcessor extends Transform {
  constructor(options = {}) {
    super(options);
    this.processedCount = 0;
  }
  
  _transform(chunk, encoding, callback) {
    try {
      // 데이터 처리 로직
      const processed = this.processChunk(chunk);
      this.processedCount++;
      
      if (this.processedCount % 1000 === 0) {
        console.log(`처리된 항목 수: ${this.processedCount}`);
      }
      
      callback(null, processed);
    } catch (error) {
      callback(error);
    }
  }
  
  processChunk(chunk) {
    // 실제 데이터 처리 로직
    return chunk.toString().toUpperCase();
  }
}

// 스트림 사용 예시
const processor = new DataProcessor();
const inputStream = fs.createReadStream('large-file.txt');
const outputStream = fs.createWriteStream('processed-file.txt');

inputStream
  .pipe(processor)
  .pipe(outputStream)
  .on('finish', () => {
    console.log('파일 처리 완료');
  });
```

## 비동기 처리 최적화 (Asynchronous Processing Optimization)

> **📌 통합된 기존 파일들**: 이 섹션은 다음 기존 파일들의 내용을 통합하여 더 체계적으로 정리한 것입니다.
> - JavaScript 비동기 처리 메커니즘 (동기 vs 비동기, 이벤트 루프)
> - Node.js 비동기 콜백 패턴 및 콜백 지옥 해결
> - Promise 개념, 체이닝, 고급 패턴 (Promise.all, Promise.allSettled, Promise.race)
> - async/await 문법 및 실용적인 예제
> - 이벤트 루프 동작 원리 및 큐 우선순위
> - Web Workers와 멀티스레딩 활용

### 1. JavaScript 비동기 처리 메커니즘

#### 동기(Synchronous) vs 비동기(Asynchronous)

JavaScript는 기본적으로 싱글 스레드 언어입니다. 즉, 한 번에 하나의 작업만 수행할 수 있습니다. 하지만 웹 애플리케이션에서는 네트워크 요청, 파일 읽기, 타이머 등 여러 작업을 동시에 처리해야 할 필요가 있습니다.

```javascript
// 동기적 실행
console.log('1. 시작');
console.log('2. 중간');
console.log('3. 끝');
// 출력: 1. 시작, 2. 중간, 3. 끝 (순차적 실행)

// 비동기적 실행
console.log('1. 시작');
setTimeout(() => {
    console.log('2. 비동기 작업');
}, 1000);
console.log('3. 끝');
// 출력: 1. 시작, 3. 끝, 2. 비동기 작업 (1초 후)
```

#### 이벤트 루프(Event Loop) 상세 분석

이벤트 루프는 JavaScript의 비동기 처리를 가능하게 하는 핵심 메커니즘입니다.

```javascript
console.log('1. 스크립트 시작');

setTimeout(() => {
    console.log('2. setTimeout 콜백');
}, 0);

Promise.resolve().then(() => {
    console.log('3. Promise 콜백');
});

console.log('4. 스크립트 끝');

// 출력:
// 1. 스크립트 시작
// 4. 스크립트 끝
// 3. Promise 콜백
// 2. setTimeout 콜백
```

**이벤트 루프 구성요소:**
1. **콜 스택(Call Stack)**: 실행 중인 코드의 위치를 추적
2. **태스크 큐(Task Queue)**: 비동기 작업의 콜백 함수들이 대기하는 곳
3. **마이크로태스크 큐(Microtask Queue)**: Promise의 콜백 함수들이 대기하는 곳

### 2. 콜백 패턴과 콜백 지옥 해결

#### 콜백 함수의 기본 개념

콜백 함수는 다른 함수에 인자로 전달되어 나중에 실행되는 함수입니다. Node.js에서는 비동기 작업의 결과를 처리하기 위해 콜백 패턴을 광범위하게 사용합니다.

```javascript
// 기본적인 콜백 예제
function fetchData(callback) {
    setTimeout(() => {
        const data = { id: 1, name: 'John Doe' };
        callback(data);
    }, 1000);
}

fetchData((data) => {
    console.log('데이터:', data);
});
```

#### Node.js에서의 콜백 패턴

```javascript
const fs = require('fs');

// 파일 읽기
fs.readFile('example.txt', 'utf8', (err, data) => {
    if (err) {
        console.error('파일 읽기 오류:', err);
        return;
    }
    console.log('파일 내용:', data);
});

// HTTP 요청
const http = require('http');

http.get('http://api.example.com/data', (res) => {
    let data = '';
    
    res.on('data', (chunk) => {
        data += chunk;
    });
    
    res.on('end', () => {
        console.log('응답 데이터:', data);
    });
}).on('error', (err) => {
    console.error('요청 오류:', err);
});
```

#### 콜백 지옥(Callback Hell) 문제

콜백을 과도하게 사용하면 코드가 복잡해지고 가독성이 떨어지는 "콜백 지옥"이 발생할 수 있습니다.

```javascript
// 콜백 지옥 예제
fs.readFile('file1.txt', 'utf8', (err, data1) => {
    if (err) {
        console.error('첫 번째 파일 읽기 오류:', err);
        return;
    }
    
    fs.readFile('file2.txt', 'utf8', (err, data2) => {
        if (err) {
            console.error('두 번째 파일 읽기 오류:', err);
            return;
        }
        
        fs.writeFile('result.txt', data1 + data2, (err) => {
            if (err) {
                console.error('파일 쓰기 오류:', err);
                return;
            }
            console.log('작업 완료!');
        });
    });
});
```

#### 콜백 지옥 해결 방법

##### 1. 콜백 분리
```javascript
function readFileCallback(err, data) {
    if (err) {
        console.error('파일 읽기 오류:', err);
        return;
    }
    console.log('파일 내용:', data);
}

fs.readFile('example.txt', 'utf8', readFileCallback);
```

##### 2. Promise로 변환
```javascript
const fs = require('fs').promises;

async function readAndProcessFile() {
    try {
        const data = await fs.readFile('example.txt', 'utf8');
        const processedData = data.toUpperCase();
        await fs.writeFile('processed.txt', processedData);
        console.log('파일 처리가 완료되었습니다.');
    } catch (err) {
        console.error('처리 중 오류 발생:', err);
    }
}
```

### 3. Promise 최적화

#### Promise 기본 개념

Promise는 비동기 작업의 최종 완료(또는 실패)와 그 결과값을 나타내는 객체입니다.

```javascript
const promise = new Promise((resolve, reject) => {
    setTimeout(() => {
        const success = true;
        if (success) {
            resolve('작업 성공!');
        } else {
            reject('작업 실패!');
        }
    }, 1000);
});

promise
    .then((result) => {
        console.log(result);
    })
    .catch((error) => {
        console.error(error);
    });
```

#### Promise 체이닝 최적화

```javascript
// 비효율적인 Promise 체이닝
function inefficientPromiseChain() {
    return fetchUser(1)
        .then(user => {
            return fetchUserProfile(user.id)
                .then(profile => {
                    return fetchUserPosts(user.id)
                        .then(posts => {
                            return { user, profile, posts };
                        });
                });
        });
}

// 효율적인 Promise 체이닝
async function efficientPromiseChain() {
    const user = await fetchUser(1);
    const [profile, posts] = await Promise.all([
        fetchUserProfile(user.id),
        fetchUserPosts(user.id)
    ]);
    
    return { user, profile, posts };
}
```

#### Promise 병렬 처리 방법들

##### Promise.all() - 모든 Promise가 성공해야 하는 경우
```javascript
const promises = [
    fetch('/api/users'),
    fetch('/api/posts'),
    fetch('/api/comments')
];

Promise.all(promises)
    .then(([users, posts, comments]) => {
        console.log('모든 데이터 로드 완료');
        console.log('사용자:', users);
        console.log('게시글:', posts);
        console.log('댓글:', comments);
    })
    .catch(error => {
        // 하나라도 실패하면 전체 실패
        console.error('하나라도 실패:', error);
    });
```

##### Promise.allSettled() - 일부가 실패해도 나머지 결과를 얻고 싶은 경우
```javascript
const promises = [
    Promise.resolve('성공1'),
    Promise.reject('실패1'),
    Promise.resolve('성공2'),
    Promise.reject('실패2')
];

Promise.allSettled(promises)
    .then(results => {
        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                console.log(`Promise ${index} 성공:`, result.value);
            } else {
                console.log(`Promise ${index} 실패:`, result.reason);
            }
        });
    });
```

##### Promise.race() - 가장 먼저 완료되는 Promise의 결과만 필요한 경우
```javascript
// 여러 API 중 가장 빠른 응답을 받고 싶을 때
const apiPromises = [
    fetch('https://api1.example.com/data'),
    fetch('https://api2.example.com/data'),
    fetch('https://api3.example.com/data')
];

Promise.race(apiPromises)
    .then(response => response.json())
    .then(data => {
        console.log('가장 빠른 API 응답:', data);
    });
```

##### Promise.any() - 하나라도 성공하면 되는 경우
```javascript
const promises = [
    Promise.reject('실패1'),
    Promise.resolve('성공1'),
    Promise.reject('실패2')
];

Promise.any(promises)
    .then(result => {
        console.log('하나라도 성공:', result); // "성공1" 출력
    })
    .catch(error => {
        // 모든 Promise가 실패한 경우에만 실행
        console.error('모든 Promise 실패:', error);
    });
```

### 4. Node.js 비동기 처리 기초

#### 논블로킹 I/O의 핵심 개념
Node.js는 기본적으로 **논블로킹 I/O(Non-Blocking I/O) 모델**을 사용하여 싱글 스레드에서도 높은 성능을 유지합니다.

> **✨ 논블로킹의 핵심 개념**
> - **작업이 끝날 때까지 기다리지 않고 즉시 다음 코드 실행**
> - **비동기(Asynchronous) 방식으로 실행**
> - **CPU가 유휴 상태가 되지 않도록 최적화**
> - **파일 시스템, 네트워크 요청, 데이터베이스 등 I/O 작업을 효율적으로 처리**

#### 블로킹 vs 논블로킹 비교

| 비교 항목 | 블로킹(Blocking) | 논블로킹(Non-Blocking) |
|-----------|-----------------|-----------------|
| **기본 개념** | 작업이 끝날 때까지 기다린 후 다음 코드 실행 | 작업을 요청한 후 바로 다음 코드 실행 |
| **처리 방식** | 동기(Synchronous) | 비동기(Asynchronous) |
| **예제** | 파일 읽기가 완료될 때까지 다음 코드 실행 안 됨 | 파일 읽기를 요청한 후 다른 코드 실행 가능 |
| **성능 영향** | 응답 속도 저하 (동시에 하나의 작업만 가능) | 높은 처리량 (여러 작업을 동시에 진행 가능) |
| **사용 사례** | 단순한 스크립트, CPU 집중적인 작업 | 서버 애플리케이션, 네트워크 요청, DB 작업 |

#### 실행 순서 비교 예제

```javascript
// 블로킹 방식 (비효율적)
const fs = require('fs');
console.log("1️⃣ 파일 읽기 시작");
const data = fs.readFileSync('example.txt', 'utf8'); // 블로킹
console.log("2️⃣ 파일 내용:", data);
console.log("3️⃣ 파일 읽기 완료");

// 출력 결과 (동기적 실행)
// 1️⃣ 파일 읽기 시작
// 2️⃣ 파일 내용: (파일 내용 출력)
// 3️⃣ 파일 읽기 완료
```

```javascript
// 논블로킹 방식 (효율적)
console.log("1️⃣ 파일 읽기 시작");
fs.readFile('example.txt', 'utf8', (err, data) => {
    if (err) throw err;
    console.log("3️⃣ 파일 내용:", data);
});
console.log("2️⃣ 파일 읽기 요청 완료");

// 출력 결과 (비동기적 실행)
// 1️⃣ 파일 읽기 시작
// 2️⃣ 파일 읽기 요청 완료
// 3️⃣ 파일 내용: (파일 내용 출력)
```

#### 이벤트 루프 실행 순서 예제

```javascript
console.log("1️⃣ Start");

setTimeout(() => console.log("4️⃣ setTimeout 실행"), 0);
setImmediate(() => console.log("3️⃣ setImmediate 실행"));

Promise.resolve().then(() => console.log("2️⃣ Promise 실행"));

console.log("1️⃣ End");

// 출력 결과:
// 1️⃣ Start
// 1️⃣ End
// 2️⃣ Promise 실행
// 3️⃣ setImmediate 실행
// 4️⃣ setTimeout 실행
```

> **📌 `Promise.then()`이 먼저 실행되고, `setImmediate()`가 `setTimeout(0)`보다 먼저 실행될 가능성이 높음!**

#### 이벤트 루프의 동작 과정
Node.js의 Event Loop는 다음과 같은 단계로 실행됩니다:

1. **Timers**: `setTimeout()`, `setInterval()` 콜백 실행
2. **I/O Callbacks**: 완료된 비동기 I/O 콜백 실행
3. **Idle, Prepare**: 내부 정리 작업
4. **Poll**: 새로운 I/O 이벤트 대기 및 처리
5. **Check**: `setImmediate()` 콜백 실행
6. **Close Callbacks**: 소켓 종료 등 작업 처리

#### 이벤트 큐의 종류와 우선순위

##### 1. Microtask Queue (마이크로태스크 큐)
```javascript
// Microtask Queue에 들어가는 작업들
Promise.then(() => console.log('Promise resolved'));
process.nextTick(() => console.log('nextTick'));
queueMicrotask(() => console.log('queueMicrotask'));
```

##### 2. Macrotask Queue (매크로태스크 큐)
```javascript
// Macrotask Queue에 들어가는 작업들
setTimeout(() => console.log('setTimeout'), 0);
setInterval(() => console.log('setInterval'), 1000);
setImmediate(() => console.log('setImmediate'));
```

##### 3. 실행 우선순위
```javascript
// 실행 우선순위: nextTick > Promise > setImmediate > setTimeout
process.nextTick(() => console.log('1. nextTick'));
Promise.resolve().then(() => console.log('2. Promise'));
setImmediate(() => console.log('3. setImmediate'));
setTimeout(() => console.log('4. setTimeout'), 0);
```

#### 논블로킹이 중요한 이유

✔ **동시 요청 처리 가능** → 서버가 한 번에 여러 요청을 처리할 수 있음  
✔ **CPU 유휴 상태 최소화** → 하나의 요청이 끝날 때까지 기다리지 않고 다른 작업 수행  
✔ **빠른 응답 속도** → 파일, 데이터베이스, 네트워크 요청을 병렬로 처리 가능  
✔ **Node.js 서버 성능 극대화** → 싱글 스레드에서도 고성능 처리 가능

#### 논블로킹 방식 활용 사례

##### 웹 서버 구축 (Express.js)
```javascript
const express = require('express');
const fs = require('fs');

const app = express();

app.get('/', (req, res) => {
    fs.readFile('example.txt', 'utf8', (err, data) => {
        if (err) return res.status(500).send("파일 읽기 오류");
        res.send(data);
    });
});

app.listen(3000, () => console.log("서버 실행 중..."));
```

##### 데이터베이스 연동 (MongoDB - Mongoose)
```javascript
const mongoose = require('mongoose');

mongoose.connect('mongodb://localhost:27017/testDB')
    .then(() => console.log("DB 연결 성공"))
    .catch(err => console.error("DB 연결 실패:", err));
```

##### 네트워크 요청 (Axios)
```javascript
const axios = require('axios');

axios.get('https://jsonplaceholder.typicode.com/posts/1')
    .then(response => console.log(response.data))
    .catch(error => console.error("네트워크 오류:", error));
```

### 2. Promise 최적화

#### Promise 체이닝 최적화
```javascript
// 비효율적인 Promise 체이닝
function inefficientPromiseChain() {
  return fetchUser(1)
    .then(user => {
      return fetchUserProfile(user.id)
        .then(profile => {
          return fetchUserPosts(user.id)
            .then(posts => {
              return { user, profile, posts };
            });
        });
    });
}

// 효율적인 Promise 체이닝
async function efficientPromiseChain() {
  const user = await fetchUser(1);
  const [profile, posts] = await Promise.all([
    fetchUserProfile(user.id),
    fetchUserPosts(user.id)
  ]);
  
  return { user, profile, posts };
}
```

#### Promise 풀링을 통한 리소스 관리
```javascript
class PromisePool {
  constructor(size = 10) {
    this.size = size;
    this.running = 0;
    this.queue = [];
  }
  
  async execute(task) {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject });
      this.process();
    });
  }
  
  async process() {
    if (this.running >= this.size || this.queue.length === 0) {
      return;
    }
    
    this.running++;
    const { task, resolve, reject } = this.queue.shift();
    
    try {
      const result = await task();
      resolve(result);
    } catch (error) {
      reject(error);
    } finally {
      this.running--;
      this.process();
    }
  }
}

// 사용 예시
const pool = new PromisePool(5);
const tasks = Array.from({ length: 20 }, (_, i) => 
  () => fetch(`https://api.example.com/data/${i}`)
);
const results = await Promise.all(tasks.map(task => pool.execute(task)));
```

#### API 클라이언트 구현 예제
```javascript
class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP 에러! 상태: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API 요청 실패:', error);
      throw error;
    }
  }

  async get(endpoint) {
    return this.request(endpoint);
  }

  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE'
    });
  }
}

// 사용 예시
const apiClient = new ApiClient('https://api.example.com');

// 병렬 API 호출
async function fetchUserData(userId) {
  const [user, posts, comments] = await Promise.all([
    apiClient.get(`/users/${userId}`),
    apiClient.get(`/users/${userId}/posts`),
    apiClient.get(`/users/${userId}/comments`)
  ]);
  
  return { user, posts, comments };
}
```

#### 실용적인 async/await 예제

##### 파일 읽기 Promise 래퍼
```javascript
// 파일 읽기 Promise
function readFileAsync(filename) {
  return new Promise((resolve, reject) => {
    // 실제 파일 읽기 작업 시뮬레이션
    setTimeout(() => {
      if (filename === 'data.txt') {
        resolve('파일 내용: Hello World!');
      } else {
        reject(new Error('파일을 찾을 수 없습니다.'));
      }
    }, 1000);
  });
}

// 사용하기
async function processFile() {
  try {
    const content = await readFileAsync('data.txt');
    console.log('파일 내용:', content);
  } catch (error) {
    console.error('파일 읽기 실패:', error.message);
  }
}
```

##### API 호출 예시
```javascript
// 비동기적으로 데이터를 가져오는 함수
async function fetchUserData(userId) {
  try {
    // API 호출
    const response = await fetch(`https://api.example.com/users/${userId}`);
    
    // 응답이 성공적이지 않으면 에러 발생
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // JSON 데이터 파싱
    const userData = await response.json();
    return userData;
    
  } catch (error) {
    console.error('사용자 데이터 가져오기 실패:', error);
    throw error;
  }
}

// 사용 예시
async function displayUserInfo(userId) {
  try {
    const user = await fetchUserData(userId);
    console.log('사용자 정보:', user);
    return user;
  } catch (error) {
    console.error('사용자 정보 표시 실패:', error);
  }
}
```

##### 지연 함수와 활용
```javascript
// Promise를 반환하는 지연 함수
function delay(ms) {
  return new Promise(resolve => {
    setTimeout(resolve, ms);
  });
}

// async/await를 사용한 지연 처리
async function waitAndLog() {
  console.log('시작');
  await delay(2000); // 2초 대기
  console.log('2초 후 실행');
  return '완료';
}

// 사용
waitAndLog().then(result => {
  console.log(result); // '완료'
});
```

### 5. async/await 고급 패턴

#### async/await 기본 개념

async/await는 Promise를 더 쉽게 사용할 수 있게 해주는 문법적 설탕입니다.

```javascript
// 기존 Promise 방식
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .then(data => {
            console.log('사용자 데이터:', data);
            return data;
        })
        .catch(error => {
            console.error('에러 발생:', error);
        });
}

// async/await 방식
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        console.log('사용자 데이터:', data);
        return data;
    } catch (error) {
        console.error('에러 발생:', error);
    }
}
```

#### 순차 처리 vs 병렬 처리

```javascript
// 순차 처리 (느림)
async function fetchMultipleUsers(userIds) {
    const users = [];
    
    for (const id of userIds) {
        const user = await fetchUserData(id);
        users.push(user);
    }
    
    return users;
}

// 병렬 처리 (빠름)
async function fetchMultipleUsersParallel(userIds) {
    const promises = userIds.map(id => fetchUserData(id));
    const users = await Promise.all(promises);
    
    return users;
}
```

#### 복잡한 비동기 처리 예제

```javascript
async function processUserData() {
    try {
        // 사용자 데이터 가져오기
        const user = await fetchUserData();
        console.log('사용자:', user);

        // 사용자의 게시물 가져오기
        const posts = await fetchUserPosts(user.id);
        console.log('게시물:', posts);

        // 각 게시물의 댓글 가져오기
        const commentsPromises = posts.map(post => 
            fetchPostComments(post.id)
        );
        const comments = await Promise.all(commentsPromises);
        console.log('댓글들:', comments);

        return { user, posts, comments };
    } catch (error) {
        console.error('처리 중 에러 발생:', error);
        throw error;
    }
}
```

### 6. Web Workers와 멀티스레딩

#### Web Workers란?

JavaScript는 기본적으로 **싱글 스레드**로 동작합니다. 즉, 한 번에 하나의 작업만 처리할 수 있습니다. Web Workers를 사용하면 **별도의 스레드에서 작업을 수행**할 수 있어 메인 스레드가 멈추지 않습니다.

#### 기본 Web Worker 사용법

##### worker.js (별도 파일)
```javascript
// Worker 스레드에서 실행되는 코드
self.onmessage = function(e) {
    const data = e.data;
    
    // 복잡한 계산 작업
    let result = 0;
    for (let i = 0; i < data.iterations; i++) {
        result += Math.sqrt(i) * Math.PI;
    }
    
    // 계산 완료 후 메인 스레드로 결과 전송
    self.postMessage({
        result: result,
        message: '계산 완료!'
    });
};
```

##### main.js (메인 스레드)
```javascript
// Worker 생성
const worker = new Worker('worker.js');

// Worker로부터 메시지 받기
worker.onmessage = function(e) {
    const data = e.data;
    console.log('계산 결과:', data.result);
    console.log('메시지:', data.message);
};

// Worker로 데이터 전송
worker.postMessage({
    iterations: 1000000
});

// 메인 스레드는 계속 다른 작업 수행 가능
console.log('Worker에게 작업 요청 완료');
console.log('메인 스레드는 다른 작업 계속 수행 중...');
```

#### 이미지 처리 Worker 예제

##### imageWorker.js
```javascript
self.onmessage = function(e) {
    const imageData = e.data;
    const canvas = new OffscreenCanvas(imageData.width, imageData.height);
    const ctx = canvas.getContext('2d');
    
    // 이미지 데이터를 캔버스에 그리기
    ctx.putImageData(imageData, 0, 0);
    
    // 이미지 필터 적용 (예: 흑백 변환)
    const filteredData = applyGrayscaleFilter(imageData);
    
    self.postMessage(filteredData);
};

function applyGrayscaleFilter(imageData) {
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
        const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
        data[i] = gray;     // Red
        data[i + 1] = gray; // Green
        data[i + 2] = gray; // Blue
    }
    
    return imageData;
}
```

##### 메인 스레드에서 사용
```javascript
const imageWorker = new Worker('imageWorker.js');

// 이미지 파일 선택 시
fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            
            // 이미지 데이터를 Worker로 전송
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            imageWorker.postMessage(imageData);
        };
        img.src = e.target.result;
    };
    
    reader.readAsDataURL(file);
});

// Worker로부터 처리된 이미지 받기
imageWorker.onmessage = function(e) {
    const processedImageData = e.data;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = processedImageData.width;
    canvas.height = processedImageData.height;
    ctx.putImageData(processedImageData, 0, 0);
    
    // 처리된 이미지를 화면에 표시
    document.body.appendChild(canvas);
};
```

#### Web Workers 제약사항

- Worker는 DOM에 직접 접근할 수 없습니다
- Worker와 메인 스레드 간 통신은 `postMessage()`를 통해서만 가능합니다
- 복사 가능한 데이터만 전송할 수 있습니다 (함수, DOM 객체 등은 전송 불가)

### 7. async/await 최적화

#### 에러 처리 최적화
```javascript
// 비효율적인 에러 처리
async function inefficientErrorHandling() {
  try {
    const user = await fetchUser(1);
    try {
      const profile = await fetchUserProfile(user.id);
      try {
        const posts = await fetchUserPosts(user.id);
        return { user, profile, posts };
      } catch (error) {
        console.error('Posts fetch failed:', error);
        return { user, profile, posts: [] };
      }
    } catch (error) {
      console.error('Profile fetch failed:', error);
      return { user, profile: null, posts: [] };
    }
  } catch (error) {
    console.error('User fetch failed:', error);
    return null;
  }
}

// 효율적인 에러 처리
async function efficientErrorHandling() {
  try {
    const user = await fetchUser(1);
    const [profile, posts] = await Promise.allSettled([
      fetchUserProfile(user.id),
      fetchUserPosts(user.id)
    ]);
    
    return {
      user,
      profile: profile.status === 'fulfilled' ? profile.value : null,
      posts: posts.status === 'fulfilled' ? posts.value : []
    };
  } catch (error) {
    console.error('User fetch failed:', error);
    return null;
  }
}
```

#### 타임아웃 처리 최적화
```javascript
// 타임아웃이 있는 Promise 래퍼
function withTimeout(promise, timeoutMs) {
  return Promise.race([
    promise,
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Timeout')), timeoutMs)
    )
  ]);
}

// 사용 예시
async function fetchWithTimeout() {
  try {
    const result = await withTimeout(
      fetch('https://api.example.com/slow-endpoint'),
      5000 // 5초 타임아웃
    );
    return result;
  } catch (error) {
    if (error.message === 'Timeout') {
      console.error('요청이 타임아웃되었습니다');
    } else {
      console.error('요청 실패:', error);
    }
  }
}
```

### 8. 이벤트 루프 최적화

#### setImmediate와 process.nextTick 활용

```javascript
// process.nextTick - 마이크로태스크 큐에 추가 (최우선)
process.nextTick(() => {
    console.log('nextTick 1');
});

// setImmediate - 체크 단계에서 실행
setImmediate(() => {
    console.log('setImmediate 1');
});

// setTimeout - 타이머 단계에서 실행
setTimeout(() => {
    console.log('setTimeout 1');
}, 0);

console.log('메인 스레드');

// 출력 순서:
// 메인 스레드
// nextTick 1
// setTimeout 1
// setImmediate 1
```

#### 이벤트 루프 블로킹 방지

```javascript
// CPU 집약적 작업을 청크로 분할
async function processLargeDataset(data) {
    const chunkSize = 1000;
    const results = [];
    
    for (let i = 0; i < data.length; i += chunkSize) {
        const chunk = data.slice(i, i + chunkSize);
        
        // 청크 처리
        const processedChunk = processChunk(chunk);
        results.push(...processedChunk);
        
        // 이벤트 루프에 제어권 양보
        await new Promise(resolve => setImmediate(resolve));
    }
    
    return results;
}

// 사용 예시
const largeData = Array.from({ length: 100000 }, (_, i) => i);
processLargeDataset(largeData).then(results => {
    console.log('처리 완료:', results.length);
});
```

#### 이벤트 루프 모니터링

```javascript
// 이벤트 루프 지연 시간 측정
function measureEventLoopDelay() {
    const start = process.hrtime.bigint();
    
    setImmediate(() => {
        const delay = Number(process.hrtime.bigint() - start) / 1000000; // ms
        console.log(`이벤트 루프 지연: ${delay.toFixed(2)}ms`);
        
        if (delay > 10) {
            console.warn('이벤트 루프 지연이 높습니다!');
        }
    });
}

// 주기적으로 이벤트 루프 지연 측정
setInterval(measureEventLoopDelay, 1000);
```

### 9. 비동기 처리 성능 모니터링

#### Promise 성능 측정

```javascript
// Promise 실행 시간 측정
async function measurePromisePerformance() {
    const start = performance.now();
    
    try {
        const result = await fetchUserData(1);
        const end = performance.now();
        
        console.log(`Promise 실행 시간: ${(end - start).toFixed(2)}ms`);
        return result;
    } catch (error) {
        const end = performance.now();
        console.log(`Promise 실패 시간: ${(end - start).toFixed(2)}ms`);
        throw error;
    }
}
```

#### 병렬 처리 성능 비교

```javascript
// 순차 처리 vs 병렬 처리 성능 비교
async function performanceComparison() {
    const userIds = [1, 2, 3, 4, 5];
    
    // 순차 처리
    console.time('순차 처리');
    const sequentialResults = [];
    for (const id of userIds) {
        const user = await fetchUserData(id);
        sequentialResults.push(user);
    }
    console.timeEnd('순차 처리');
    
    // 병렬 처리
    console.time('병렬 처리');
    const parallelResults = await Promise.all(
        userIds.map(id => fetchUserData(id))
    );
    console.timeEnd('병렬 처리');
    
    console.log('순차 처리 결과:', sequentialResults.length);
    console.log('병렬 처리 결과:', parallelResults.length);
}
```

#### 메모리 사용량 모니터링

```javascript
// 비동기 작업의 메모리 사용량 모니터링
function monitorMemoryUsage() {
    const memUsage = process.memoryUsage();
    
    console.log('메모리 사용량:');
    console.log(`RSS: ${(memUsage.rss / 1024 / 1024).toFixed(2)} MB`);
    console.log(`Heap Used: ${(memUsage.heapUsed / 1024 / 1024).toFixed(2)} MB`);
    console.log(`Heap Total: ${(memUsage.heapTotal / 1024 / 1024).toFixed(2)} MB`);
    console.log(`External: ${(memUsage.external / 1024 / 1024).toFixed(2)} MB`);
}

// 주기적으로 메모리 사용량 확인
setInterval(monitorMemoryUsage, 5000);
```

#### 비동기 작업 추적

```javascript
// 비동기 작업 추적 시스템
class AsyncTaskTracker {
    constructor() {
        this.tasks = new Map();
        this.completedTasks = 0;
        this.failedTasks = 0;
    }
    
    startTask(taskId, description) {
        this.tasks.set(taskId, {
            description,
            startTime: performance.now(),
            status: 'running'
        });
    }
    
    completeTask(taskId, result) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.endTime = performance.now();
            task.duration = task.endTime - task.startTime;
            task.status = 'completed';
            task.result = result;
            this.completedTasks++;
        }
    }
    
    failTask(taskId, error) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.endTime = performance.now();
            task.duration = task.endTime - task.startTime;
            task.status = 'failed';
            task.error = error;
            this.failedTasks++;
        }
    }
    
    getStats() {
        return {
            total: this.tasks.size,
            completed: this.completedTasks,
            failed: this.failedTasks,
            running: this.tasks.size - this.completedTasks - this.failedTasks
        };
    }
}

// 사용 예시
const tracker = new AsyncTaskTracker();

async function trackedAsyncOperation(taskId, operation) {
    tracker.startTask(taskId, '비동기 작업');
    
    try {
        const result = await operation();
        tracker.completeTask(taskId, result);
        return result;
    } catch (error) {
        tracker.failTask(taskId, error);
        throw error;
    }
}
```

### 10. 이벤트 루프 최적화

#### 이벤트 루프 블로킹 방지
```javascript
// CPU 집약적 작업을 청크로 분할
async function processLargeDataset(data) {
  const chunkSize = 1000;
  const chunks = [];
  
  for (let i = 0; i < data.length; i += chunkSize) {
    chunks.push(data.slice(i, i + chunkSize));
  }
  
  const results = [];
  
  for (const chunk of chunks) {
    // 각 청크를 처리
    const chunkResult = await processChunk(chunk);
    results.push(...chunkResult);
    
    // 이벤트 루프에 제어권 양보
    await new Promise(resolve => setImmediate(resolve));
  }
  
  return results;
}

// setImmediate를 사용한 비동기 처리
function asyncProcess(items, processor) {
  return new Promise((resolve) => {
    const results = [];
    let index = 0;
    
    function processNext() {
      if (index >= items.length) {
        resolve(results);
        return;
      }
      
      const result = processor(items[index]);
      results.push(result);
      index++;
      
      // 다음 틱에서 계속 처리
      setImmediate(processNext);
    }
    
    processNext();
  });
}
```

### 5. 비동기 처리 성능 모니터링

#### 비동기 작업 성능 측정
```javascript
class AsyncPerformanceMonitor {
  constructor() {
    this.metrics = {
      promiseResolveTime: [],
      asyncFunctionTime: [],
      eventLoopDelay: []
    };
  }
  
  // Promise 해결 시간 측정
  measurePromiseResolve(promise, label) {
    const start = Date.now();
    return promise.then(result => {
      const duration = Date.now() - start;
      this.metrics.promiseResolveTime.push({ label, duration });
      return result;
    });
  }
  
  // async 함수 실행 시간 측정
  async measureAsyncFunction(asyncFn, label) {
    const start = Date.now();
    const result = await asyncFn();
    const duration = Date.now() - start;
    this.metrics.asyncFunctionTime.push({ label, duration });
    return result;
  }
  
  // 이벤트 루프 지연 측정
  measureEventLoopDelay() {
    const start = process.hrtime.bigint();
    setImmediate(() => {
      const delay = Number(process.hrtime.bigint() - start) / 1000000; // ms
      this.metrics.eventLoopDelay.push(delay);
    });
  }
  
  // 성능 리포트 생성
  generateReport() {
    return {
      averagePromiseResolveTime: this.calculateAverage(this.metrics.promiseResolveTime),
      averageAsyncFunctionTime: this.calculateAverage(this.metrics.asyncFunctionTime),
      averageEventLoopDelay: this.calculateAverage(this.metrics.eventLoopDelay),
      maxEventLoopDelay: Math.max(...this.metrics.eventLoopDelay)
    };
  }
  
  calculateAverage(metrics) {
    if (metrics.length === 0) return 0;
    return metrics.reduce((sum, m) => sum + m.duration, 0) / metrics.length;
  }
}
```

## 실제 성능 병목 지점 분석 및 해결 사례 (Real Performance Bottleneck Analysis and Solutions)

### 1. 데이터베이스 쿼리 최적화 사례

#### N+1 쿼리 문제 해결
```javascript
// 문제가 있는 코드 (N+1 쿼리)
async function getUsersWithPosts() {
  const users = await User.findAll();
  
  for (const user of users) {
    user.posts = await Post.findAll({ where: { userId: user.id } });
  }
  
  return users;
}

// 최적화된 코드 (JOIN 사용)
async function getUsersWithPostsOptimized() {
  return await User.findAll({
    include: [{
      model: Post,
      as: 'posts'
    }]
  });
}

// 또는 별도 쿼리로 최적화
async function getUsersWithPostsOptimized2() {
  const users = await User.findAll();
  const userIds = users.map(user => user.id);
  
  const posts = await Post.findAll({
    where: { userId: { [Op.in]: userIds } }
  });
  
  // 메모리에서 조인
  const postsByUser = posts.reduce((acc, post) => {
    if (!acc[post.userId]) acc[post.userId] = [];
    acc[post.userId].push(post);
    return acc;
  }, {});
  
  return users.map(user => ({
    ...user.toJSON(),
    posts: postsByUser[user.id] || []
  }));
}
```

### 2. API 응답 시간 최적화 사례

#### 캐싱을 통한 응답 시간 개선
```javascript
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 }); // 10분 TTL

class APIOptimizer {
  // 캐시를 사용한 API 응답 최적화
  async getCachedData(key, fetchFn, ttl = 600) {
    const cached = cache.get(key);
    if (cached) {
      return cached;
    }
    
    const data = await fetchFn();
    cache.set(key, data, ttl);
    return data;
  }
  
  // Redis를 사용한 분산 캐싱
  async getDistributedCache(key, fetchFn) {
    const redis = require('redis');
    const client = redis.createClient();
    
    try {
      const cached = await client.get(key);
      if (cached) {
        return JSON.parse(cached);
      }
      
      const data = await fetchFn();
      await client.setex(key, 600, JSON.stringify(data));
      return data;
    } finally {
      client.quit();
    }
  }
}

// 사용 예시
const optimizer = new APIOptimizer();

app.get('/api/users/:id', async (req, res) => {
  const userId = req.params.id;
  
  const user = await optimizer.getCachedData(
    `user:${userId}`,
    () => User.findByPk(userId)
  );
  
  res.json(user);
});
```

### 3. 메모리 사용량 최적화 사례

#### 스트림을 사용한 대용량 파일 처리
```javascript
const fs = require('fs');
const { Transform } = require('stream');

// 메모리 효율적인 CSV 처리
class CSVProcessor extends Transform {
  constructor() {
    super({ objectMode: true });
    this.header = null;
    this.rowCount = 0;
  }
  
  _transform(chunk, encoding, callback) {
    const lines = chunk.toString().split('\n');
    
    for (const line of lines) {
      if (!line.trim()) continue;
      
      const columns = line.split(',');
      
      if (!this.header) {
        this.header = columns;
        continue;
      }
      
      const row = {};
      this.header.forEach((col, index) => {
        row[col] = columns[index];
      });
      
      this.rowCount++;
      this.push(row);
      
      // 메모리 사용량 모니터링
      if (this.rowCount % 10000 === 0) {
        const usage = process.memoryUsage();
        console.log(`처리된 행 수: ${this.rowCount}, 메모리 사용량: ${(usage.heapUsed / 1024 / 1024).toFixed(2)} MB`);
      }
    }
    
    callback();
  }
}

// 사용 예시
const processor = new CSVProcessor();
const inputStream = fs.createReadStream('large-file.csv');
const outputStream = fs.createWriteStream('processed-data.json');

inputStream
  .pipe(processor)
  .pipe(outputStream)
  .on('finish', () => {
    console.log('CSV 처리 완료');
  });
```

## 성능 모니터링 및 알림 (Performance Monitoring and Alerting)

### 1. 실시간 성능 모니터링

#### 성능 메트릭 수집
```javascript
class PerformanceMonitor {
  constructor() {
    this.metrics = {
      responseTime: [],
      memoryUsage: [],
      cpuUsage: [],
      errorRate: 0,
      requestCount: 0
    };
    
    this.thresholds = {
      responseTime: 1000, // 1초
      memoryUsage: 500 * 1024 * 1024, // 500MB
      errorRate: 0.05 // 5%
    };
  }
  
  // 응답 시간 측정
  measureResponseTime(req, res, next) {
    const start = Date.now();
    
    res.on('finish', () => {
      const duration = Date.now() - start;
      this.metrics.responseTime.push(duration);
      
      // 최근 100개만 유지
      if (this.metrics.responseTime.length > 100) {
        this.metrics.responseTime.shift();
      }
      
      // 임계값 체크
      if (duration > this.thresholds.responseTime) {
        this.alert('High Response Time', { duration, url: req.url });
      }
    });
    
    next();
  }
  
  // 메모리 사용량 모니터링
  monitorMemory() {
    setInterval(() => {
      const usage = process.memoryUsage();
      this.metrics.memoryUsage.push({
        timestamp: Date.now(),
        heapUsed: usage.heapUsed,
        heapTotal: usage.heapTotal
      });
      
      if (usage.heapUsed > this.thresholds.memoryUsage) {
        this.alert('High Memory Usage', { heapUsed: usage.heapUsed });
      }
    }, 5000);
  }
  
  // 알림 발송
  alert(type, data) {
    console.warn(`🚨 ${type}:`, data);
    
    // 실제 환경에서는 Slack, 이메일 등으로 알림
    // this.sendSlackNotification(type, data);
  }
  
  // 성능 리포트 생성
  generateReport() {
    const avgResponseTime = this.metrics.responseTime.reduce((a, b) => a + b, 0) / this.metrics.responseTime.length;
    const maxResponseTime = Math.max(...this.metrics.responseTime);
    
    return {
      averageResponseTime: avgResponseTime,
      maxResponseTime: maxResponseTime,
      requestCount: this.metrics.requestCount,
      errorRate: this.metrics.errorRate,
      memoryUsage: this.metrics.memoryUsage.slice(-10) // 최근 10개
    };
  }
}

// Express 미들웨어로 사용
const monitor = new PerformanceMonitor();
monitor.monitorMemory();

app.use(monitor.measureResponseTime.bind(monitor));
```

### 2. 성능 알림 시스템

#### 임계값 기반 알림
```javascript
class PerformanceAlert {
  constructor() {
    this.alerts = [];
    this.cooldown = 5 * 60 * 1000; // 5분 쿨다운
  }
  
  // 알림 조건 체크
  checkAlerts(metrics) {
    const now = Date.now();
    
    // 응답 시간 알림
    if (metrics.avgResponseTime > 1000) {
      this.sendAlert('HIGH_RESPONSE_TIME', {
        value: metrics.avgResponseTime,
        threshold: 1000
      });
    }
    
    // 메모리 사용량 알림
    if (metrics.memoryUsage > 500 * 1024 * 1024) {
      this.sendAlert('HIGH_MEMORY_USAGE', {
        value: metrics.memoryUsage,
        threshold: 500 * 1024 * 1024
      });
    }
    
    // 에러율 알림
    if (metrics.errorRate > 0.05) {
      this.sendAlert('HIGH_ERROR_RATE', {
        value: metrics.errorRate,
        threshold: 0.05
      });
    }
  }
  
  // 알림 발송
  sendAlert(type, data) {
    const alertKey = `${type}_${Math.floor(Date.now() / this.cooldown)}`;
    
    if (this.alerts.includes(alertKey)) {
      return; // 쿨다운 중
    }
    
    this.alerts.push(alertKey);
    
    // 알림 데이터 구성
    const alert = {
      type,
      timestamp: new Date().toISOString(),
      data,
      severity: this.getSeverity(type)
    };
    
    // 실제 알림 발송
    this.sendSlackNotification(alert);
    this.sendEmailNotification(alert);
    
    // 쿨다운 관리
    setTimeout(() => {
      const index = this.alerts.indexOf(alertKey);
      if (index > -1) {
        this.alerts.splice(index, 1);
      }
    }, this.cooldown);
  }
  
  // 심각도 결정
  getSeverity(type) {
    const severityMap = {
      'HIGH_RESPONSE_TIME': 'warning',
      'HIGH_MEMORY_USAGE': 'critical',
      'HIGH_ERROR_RATE': 'critical'
    };
    
    return severityMap[type] || 'info';
  }
  
  // Slack 알림
  sendSlackNotification(alert) {
    const webhook = process.env.SLACK_WEBHOOK_URL;
    if (!webhook) return;
    
    const message = {
      text: `🚨 Performance Alert: ${alert.type}`,
      attachments: [{
        color: alert.severity === 'critical' ? 'danger' : 'warning',
        fields: [
          { title: 'Type', value: alert.type, short: true },
          { title: 'Time', value: alert.timestamp, short: true },
          { title: 'Data', value: JSON.stringify(alert.data), short: false }
        ]
      }]
    };
    
    // 실제 Slack API 호출
    // fetch(webhook, { method: 'POST', body: JSON.stringify(message) });
  }
  
  // 이메일 알림
  sendEmailNotification(alert) {
    // 실제 이메일 발송 로직
    console.log('Email alert:', alert);
  }
}
```

## 결론 (Conclusion)

Node.js 성능 최적화는 지속적인 모니터링과 개선이 필요한 과정입니다. 

### 주요 포인트 (Key Points)

1. **측정 우선**: 최적화 전에 현재 성능을 정확히 측정
2. **도구 활용**: Clinic.js, 0x, heapdump 등 전문 도구 사용
3. **메모리 관리**: 메모리 누수 방지 및 효율적인 메모리 사용
4. **비동기 최적화**: Promise, async/await, 스트림 활용
5. **지속적 모니터링**: 실시간 성능 추적 및 알림 시스템

### 성능 최적화 체크리스트 (Performance Optimization Checklist)

- [ ] 성능 프로파일링 도구 설정 및 사용
- [ ] 메모리 누수 패턴 점검 및 해결
- [ ] CPU 집약적 작업 최적화
- [ ] 비동기 처리 패턴 개선
- [ ] 데이터베이스 쿼리 최적화
- [ ] 캐싱 전략 구현
- [ ] 성능 모니터링 시스템 구축
- [ ] 알림 시스템 설정

이러한 최적화를 통해 Node.js 애플리케이션의 성능을 크게 향상시킬 수 있습니다.
