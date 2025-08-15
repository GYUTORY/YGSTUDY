---
title: Node.js Event Loop (이벤트 루프)
tags: [framework, node, nodejs의-구조-및-작동-원리, event-loop, nodejs, asynchronous]
updated: 2025-08-15
---

# Node.js Event Loop (이벤트 루프)

## 배경

Node.js의 Event Loop(이벤트 루프)는 비동기 처리를 가능하게 하는 핵심 메커니즘입니다. Node.js는 싱글 스레드(Single Thread) 기반이지만, Event Loop를 활용하여 비동기 I/O 작업을 효율적으로 처리할 수 있습니다.

### Node.js의 비동기 처리 필요성
- **싱글 스레드 환경**: JavaScript는 기본적으로 싱글 스레드로 동작
- **I/O 작업의 비동기 처리**: 파일 읽기, 네트워크 요청 등은 시간이 오래 걸림
- **성능 최적화**: 블로킹 작업으로 인한 전체 애플리케이션 성능 저하 방지
- **동시성 처리**: 여러 작업을 동시에 처리할 수 있는 능력

### Event Loop의 핵심 개념
- **Node.js는 기본적으로 싱글 스레드**
- **비동기 작업(I/O, 타이머, 네트워크 요청 등)을 처리**
- **이벤트 기반(Event-Driven)으로 실행**
- **논-블로킹(Non-Blocking) 방식으로 동작**
- **콜백 함수와 함께 실행 흐름을 관리**

## 핵심

### Event Loop의 동작 과정

Node.js의 Event Loop는 다음과 같은 단계로 실행됩니다:

#### 1. Timers (타이머 실행)
- `setTimeout()`, `setInterval()` 등의 타이머 콜백 실행
- 지정된 시간이 지난 콜백들을 실행

#### 2. I/O Callbacks (I/O 작업 완료 후 콜백 실행)
- 파일 시스템, 네트워크 요청 등의 비동기 작업이 완료되면 실행됨
- 이전 루프에서 지연된 I/O 콜백들을 실행

#### 3. Idle, Prepare (내부적인 작업)
- 내부적으로 사용되며, 일반적인 애플리케이션 개발에서는 거의 사용되지 않음
- Node.js 내부 정리 작업 수행

#### 4. Poll (I/O 이벤트 대기 및 처리)
- 가장 중요한 단계! 비동기 I/O 작업을 처리하는 핵심 부분
- 새로운 I/O 이벤트가 있으면 처리하고, 없으면 다음 단계로 이동
- 새로운 연결이나 데이터를 기다림

#### 5. Check (setImmediate() 실행)
- `setImmediate()`로 예약된 콜백이 실행됨
- Poll 단계가 완료된 직후 실행

#### 6. Close Callbacks (닫기 이벤트 처리)
- 소켓 연결 종료, `process.exit()` 등 실행
- 리소스 정리 작업 수행

### 이벤트 큐의 종류

#### 1. Microtask Queue (마이크로태스크 큐)
```javascript
// Microtask Queue에 들어가는 작업들
Promise.then(() => console.log('Promise resolved'));
process.nextTick(() => console.log('nextTick'));
queueMicrotask(() => console.log('queueMicrotask'));
```

#### 2. Macrotask Queue (매크로태스크 큐)
```javascript
// Macrotask Queue에 들어가는 작업들
setTimeout(() => console.log('setTimeout'), 0);
setInterval(() => console.log('setInterval'), 1000);
setImmediate(() => console.log('setImmediate'));
```

#### 3. 실행 우선순위
```javascript
// 실행 우선순위: nextTick > Promise > setImmediate > setTimeout
process.nextTick(() => console.log('1. nextTick'));
Promise.resolve().then(() => console.log('2. Promise'));
setImmediate(() => console.log('3. setImmediate'));
setTimeout(() => console.log('4. setTimeout'), 0);
```

## 예시

### 기본적인 Event Loop 실행 순서

#### 기본 실행 순서 예제
```javascript
console.log("1. Start");

setTimeout(() => console.log("4. setTimeout"), 0);
setImmediate(() => console.log("3. setImmediate"));

Promise.resolve().then(() => console.log("2. Promise"));

console.log("5. End");

// 출력 결과:
// 1. Start
// 5. End
// 2. Promise
// 3. setImmediate
// 4. setTimeout
```

#### 복잡한 실행 순서 예제
```javascript
console.log('=== Event Loop 실행 순서 테스트 ===');

// 동기 코드
console.log('1. 동기 코드 시작');

// 마이크로태스크
Promise.resolve().then(() => {
    console.log('2. Promise 1');
    return Promise.resolve();
}).then(() => {
    console.log('3. Promise 2');
});

process.nextTick(() => {
    console.log('4. nextTick 1');
    process.nextTick(() => {
        console.log('5. nextTick 2');
    });
});

// 매크로태스크
setTimeout(() => {
    console.log('6. setTimeout 1');
    Promise.resolve().then(() => {
        console.log('7. Promise in setTimeout');
    });
}, 0);

setImmediate(() => {
    console.log('8. setImmediate 1');
    process.nextTick(() => {
        console.log('9. nextTick in setImmediate');
    });
});

console.log('10. 동기 코드 끝');

// 출력 결과:
// === Event Loop 실행 순서 테스트 ===
// 1. 동기 코드 시작
// 10. 동기 코드 끝
// 4. nextTick 1
// 5. nextTick 2
// 2. Promise 1
// 3. Promise 2
// 8. setImmediate 1
// 9. nextTick in setImmediate
// 6. setTimeout 1
// 7. Promise in setTimeout
```

### 실제 애플리케이션 예제

#### 파일 읽기와 Event Loop
```javascript
const fs = require('fs');

console.log('1. 애플리케이션 시작');

// 동기 파일 읽기 (블로킹)
const syncData = fs.readFileSync('./data.txt', 'utf8');
console.log('2. 동기 파일 읽기 완료:', syncData.length, '바이트');

// 비동기 파일 읽기 (논-블로킹)
fs.readFile('./data.txt', 'utf8', (err, data) => {
    if (err) {
        console.error('파일 읽기 오류:', err);
        return;
    }
    console.log('3. 비동기 파일 읽기 완료:', data.length, '바이트');
});

// 타이머 설정
setTimeout(() => {
    console.log('4. setTimeout 실행');
}, 100);

// Promise 체인
Promise.resolve()
    .then(() => {
        console.log('5. Promise 1 실행');
        return new Promise(resolve => {
            setTimeout(resolve, 50);
        });
    })
    .then(() => {
        console.log('6. Promise 2 실행');
    });

console.log('7. 애플리케이션 초기화 완료');
```

#### HTTP 서버와 Event Loop
```javascript
const http = require('http');

const server = http.createServer((req, res) => {
    console.log(`요청 받음: ${req.method} ${req.url}`);
    
    // 비동기 작업 시뮬레이션
    setTimeout(() => {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Hello World\n');
        console.log('응답 완료');
    }, 100);
});

server.listen(3000, () => {
    console.log('서버가 포트 3000에서 실행 중입니다.');
    
    // 서버 시작 후 이벤트 루프 확인
    setImmediate(() => {
        console.log('서버 초기화 완료');
    });
});

// 서버 이벤트 리스너
server.on('connection', (socket) => {
    console.log('새로운 연결:', socket.remoteAddress);
});

server.on('error', (err) => {
    console.error('서버 오류:', err);
});
```

### 고급 Event Loop 예제

#### Event Loop 블로킹 방지
```javascript
// 잘못된 예: Event Loop 블로킹
function blockingOperation() {
    console.log('블로킹 작업 시작');
    const start = Date.now();
    
    // CPU 집약적인 작업 (Event Loop 블로킹)
    while (Date.now() - start < 5000) {
        // 5초간 무한 루프
    }
    
    console.log('블로킹 작업 완료');
}

// 올바른 예: 비동기 처리
function nonBlockingOperation() {
    console.log('비동기 작업 시작');
    
    return new Promise((resolve) => {
        // 작업을 청크로 나누어 처리
        let count = 0;
        const maxCount = 1000000;
        
        function processChunk() {
            const chunkSize = 1000;
            const end = Math.min(count + chunkSize, maxCount);
            
            for (let i = count; i < end; i++) {
                // 작업 수행
                Math.sqrt(i);
            }
            
            count = end;
            
            if (count < maxCount) {
                // 다음 청크를 다음 틱에서 처리
                setImmediate(processChunk);
            } else {
                console.log('비동기 작업 완료');
                resolve();
            }
        }
        
        processChunk();
    });
}

// 사용 예시
async function compareOperations() {
    console.log('=== 블로킹 vs 비동기 작업 비교 ===');
    
    // 비동기 작업 (권장)
    console.log('비동기 작업 시작');
    await nonBlockingOperation();
    console.log('비동기 작업 후 다른 작업 가능');
    
    // 블로킹 작업 (비권장)
    console.log('블로킹 작업 시작');
    blockingOperation();
    console.log('블로킹 작업 후 실행 (5초 후)');
}

compareOperations();
```

#### Event Loop 모니터링
```javascript
class EventLoopMonitor {
    constructor() {
        this.metrics = {
            startTime: Date.now(),
            tickCount: 0,
            averageTickTime: 0,
            maxTickTime: 0,
            minTickTime: Infinity
        };
        this.lastTickTime = Date.now();
    }

    // Event Loop 틱 모니터링
    startMonitoring() {
        const monitorTick = () => {
            const now = Date.now();
            const tickTime = now - this.lastTickTime;
            
            this.metrics.tickCount++;
            this.metrics.maxTickTime = Math.max(this.metrics.maxTickTime, tickTime);
            this.metrics.minTickTime = Math.min(this.metrics.minTickTime, tickTime);
            
            // 평균 틱 시간 계산
            this.metrics.averageTickTime = 
                (this.metrics.averageTickTime * (this.metrics.tickCount - 1) + tickTime) / this.metrics.tickCount;
            
            this.lastTickTime = now;
            
            // 다음 틱에서 다시 실행
            setImmediate(monitorTick);
        };
        
        setImmediate(monitorTick);
    }

    // 메트릭 출력
    getMetrics() {
        const uptime = Date.now() - this.metrics.startTime;
        return {
            uptime: Math.floor(uptime / 1000),
            tickCount: this.metrics.tickCount,
            averageTickTime: this.metrics.averageTickTime.toFixed(2),
            maxTickTime: this.metrics.maxTickTime,
            minTickTime: this.metrics.minTickTime,
            ticksPerSecond: (this.metrics.tickCount / (uptime / 1000)).toFixed(2)
        };
    }

    // 경고 체크
    checkWarnings() {
        const warnings = [];
        
        if (this.metrics.averageTickTime > 50) {
            warnings.push('평균 틱 시간이 50ms를 초과합니다. Event Loop가 느려질 수 있습니다.');
        }
        
        if (this.metrics.maxTickTime > 100) {
            warnings.push('최대 틱 시간이 100ms를 초과했습니다. 블로킹 작업이 있을 수 있습니다.');
        }
        
        return warnings;
    }
}

// 사용 예시
const monitor = new EventLoopMonitor();
monitor.startMonitoring();

// 주기적으로 메트릭 출력
setInterval(() => {
    const metrics = monitor.getMetrics();
    const warnings = monitor.checkWarnings();
    
    console.log('Event Loop 메트릭:', metrics);
    
    if (warnings.length > 0) {
        console.warn('경고:', warnings);
    }
}, 5000);
```

## 운영 팁

### 성능 최적화

#### Event Loop 최적화 기법
```javascript
// 1. 무거운 작업을 청크로 나누기
function processLargeArray(array) {
    return new Promise((resolve) => {
        const chunkSize = 1000;
        let index = 0;
        
        function processChunk() {
            const end = Math.min(index + chunkSize, array.length);
            
            for (let i = index; i < end; i++) {
                // 각 요소에 대한 무거운 작업
                array[i] = array[i] * 2 + Math.sqrt(array[i]);
            }
            
            index = end;
            
            if (index < array.length) {
                // 다음 청크를 다음 틱에서 처리
                setImmediate(processChunk);
            } else {
                resolve(array);
            }
        }
        
        processChunk();
    });
}

// 2. Worker Threads 사용
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

if (isMainThread) {
    // 메인 스레드
    function heavyComputation(data) {
        return new Promise((resolve, reject) => {
            const worker = new Worker(__filename, {
                workerData: data
            });
            
            worker.on('message', resolve);
            worker.on('error', reject);
            worker.on('exit', (code) => {
                if (code !== 0) {
                    reject(new Error(`Worker stopped with exit code ${code}`));
                }
            });
        });
    }
    
    // 사용 예시
    const largeArray = new Array(1000000).fill(1);
    heavyComputation(largeArray).then(result => {
        console.log('계산 완료:', result.length);
    });
} else {
    // 워커 스레드
    const result = workerData.map(x => x * 2 + Math.sqrt(x));
    parentPort.postMessage(result);
}

// 3. 비동기 작업 최적화
class AsyncTaskQueue {
    constructor(concurrency = 5) {
        this.concurrency = concurrency;
        this.running = 0;
        this.queue = [];
    }

    add(task) {
        return new Promise((resolve, reject) => {
            this.queue.push({ task, resolve, reject });
            this.process();
        });
    }

    process() {
        if (this.running >= this.concurrency || this.queue.length === 0) {
            return;
        }

        this.running++;
        const { task, resolve, reject } = this.queue.shift();

        Promise.resolve(task())
            .then(resolve)
            .catch(reject)
            .finally(() => {
                this.running--;
                this.process();
            });
    }
}

// 사용 예시
const taskQueue = new AsyncTaskQueue(3);

// 여러 비동기 작업 추가
for (let i = 0; i < 10; i++) {
    taskQueue.add(async () => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        console.log(`작업 ${i} 완료`);
        return i;
    });
}
```

### 메모리 관리

#### 메모리 누수 방지
```javascript
// 1. 이벤트 리스너 정리
class EventManager {
    constructor() {
        this.listeners = new Map();
    }

    addListener(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    removeListener(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    removeAllListeners(event) {
        this.listeners.delete(event);
    }

    // 소멸자
    destroy() {
        this.listeners.clear();
    }
}

// 2. 타이머 정리
class TimerManager {
    constructor() {
        this.timers = new Set();
    }

    setTimeout(callback, delay, ...args) {
        const timer = setTimeout(() => {
            this.timers.delete(timer);
            callback(...args);
        }, delay);
        
        this.timers.add(timer);
        return timer;
    }

    setInterval(callback, delay, ...args) {
        const timer = setInterval(callback, delay, ...args);
        this.timers.add(timer);
        return timer;
    }

    clearTimer(timer) {
        if (this.timers.has(timer)) {
            clearTimeout(timer);
            clearInterval(timer);
            this.timers.delete(timer);
        }
    }

    clearAll() {
        this.timers.forEach(timer => {
            clearTimeout(timer);
            clearInterval(timer);
        });
        this.timers.clear();
    }
}

// 사용 예시
const eventManager = new EventManager();
const timerManager = new TimerManager();

// 이벤트 리스너 추가
const callback = () => console.log('이벤트 발생');
eventManager.addListener('test', callback);

// 타이머 설정
const timer = timerManager.setInterval(() => {
    console.log('타이머 실행');
}, 1000);

// 정리
setTimeout(() => {
    eventManager.removeListener('test', callback);
    timerManager.clearTimer(timer);
    eventManager.destroy();
    timerManager.clearAll();
}, 5000);
```

### 디버깅 및 모니터링

#### Event Loop 디버깅 도구
```javascript
// 1. Event Loop 지연 측정
function measureEventLoopDelay() {
    const start = process.hrtime.bigint();
    
    setImmediate(() => {
        const end = process.hrtime.bigint();
        const delay = Number(end - start) / 1000000; // 밀리초 단위
        
        console.log(`Event Loop 지연: ${delay.toFixed(2)}ms`);
        
        if (delay > 16) { // 60fps 기준
            console.warn('Event Loop가 느려집니다!');
        }
    });
}

// 2. 블로킹 작업 감지
class BlockingDetector {
    constructor() {
        this.lastCheck = Date.now();
        this.blockingThreshold = 50; // 50ms 이상이면 블로킹으로 간주
    }

    check() {
        const now = Date.now();
        const delay = now - this.lastCheck;
        
        if (delay > this.blockingThreshold) {
            console.warn(`블로킹 작업 감지: ${delay}ms`);
        }
        
        this.lastCheck = now;
        setImmediate(() => this.check());
    }

    start() {
        this.check();
    }
}

// 3. 메모리 사용량 모니터링
function monitorMemoryUsage() {
    setInterval(() => {
        const memUsage = process.memoryUsage();
        
        console.log('메모리 사용량:', {
            rss: `${Math.round(memUsage.rss / 1024 / 1024)}MB`,
            heapUsed: `${Math.round(memUsage.heapUsed / 1024 / 1024)}MB`,
            heapTotal: `${Math.round(memUsage.heapTotal / 1024 / 1024)}MB`,
            external: `${Math.round(memUsage.external / 1024 / 1024)}MB`
        });
        
        // 메모리 누수 경고
        if (memUsage.heapUsed > 100 * 1024 * 1024) { // 100MB
            console.warn('메모리 사용량이 높습니다!');
        }
    }, 5000);
}

// 사용 예시
measureEventLoopDelay();

const detector = new BlockingDetector();
detector.start();

monitorMemoryUsage();
```

## 참고

### Event Loop 단계별 상세 설명

#### 1. Timers Phase
```javascript
// 타이머는 정확한 시간에 실행되지 않을 수 있음
setTimeout(() => {
    console.log('타이머 실행');
}, 1000);

// 실제 실행 시간은 1000ms보다 클 수 있음
// Event Loop가 다른 작업으로 바쁘면 지연될 수 있음
```

#### 2. Poll Phase
```javascript
// Poll 단계에서 I/O 이벤트를 기다림
const fs = require('fs');

fs.readFile('large-file.txt', (err, data) => {
    // 이 콜백은 Poll 단계에서 실행됨
    console.log('파일 읽기 완료');
});

// Poll 단계가 비어있으면 다음 단계로 이동
```

#### 3. Check Phase
```javascript
// setImmediate는 Check 단계에서 실행됨
setImmediate(() => {
    console.log('Check 단계에서 실행');
});

// setTimeout(0)과 setImmediate의 실행 순서는 예측할 수 없음
setTimeout(() => {
    console.log('Timer 단계에서 실행');
}, 0);
```

### Node.js 버전별 Event Loop 차이점

#### Node.js 11+ 변경사항
```javascript
// Node.js 11 이전: nextTick이 microtask queue보다 우선
// Node.js 11+: microtask queue가 nextTick과 동일한 우선순위

// Node.js 11+에서의 실행 순서
Promise.resolve().then(() => console.log('Promise'));
process.nextTick(() => console.log('nextTick'));

// 출력: Promise, nextTick (순서가 보장되지 않음)
```

### 결론
Event Loop는 Node.js의 비동기 처리 핵심 메커니즘입니다.
적절한 Event Loop 이해로 성능 최적화와 메모리 관리를 할 수 있습니다.
블로킹 작업을 피하고 비동기 패턴을 사용해야 합니다.
모니터링과 디버깅 도구를 활용하여 Event Loop 상태를 관리해야 합니다.
Event Loop의 단계와 우선순위를 이해하여 예측 가능한 코드를 작성해야 합니다.

