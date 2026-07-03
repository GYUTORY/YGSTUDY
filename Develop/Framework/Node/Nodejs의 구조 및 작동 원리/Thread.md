---
title: Node.js Worker Threads (워커 스레드)
tags: [framework, node, nodejs의-구조-및-작동-원리, worker-threads, nodejs, multi-threading]
updated: 2025-08-15
---

# Node.js Worker Threads (워커 스레드)

## 배경

Node.js는 기본적으로 싱글 스레드(Single Thread) 기반의 실행 환경입니다. 하지만, Worker Threads를 활용하면 멀티 스레드 기반의 작업 처리가 가능합니다.

Node.js는 Event Loop 기반의 싱글 스레드 모델이지만, CPU 바운드 작업은 워커 스레드로 넘겨 메인 루프를 비우는 식으로 접근합니다. I/O는 기존 논블로킹 모델이 더 효율적입니다.

### Worker Threads의 필요성
- **CPU 집약적인 작업**: 복잡한 계산이나 데이터 처리를 별도 스레드에서 실행
- **이벤트 루프 블로킹 방지**: 메인 스레드가 차단되지 않도록 보장
- **병렬 처리**: 여러 작업을 동시에 처리하여 성능 향상
- **메모리 공유**: SharedArrayBuffer를 통한 스레드 간 데이터 공유

### Worker Threads vs Event Loop

| 비교 항목 | 기본 Event Loop | Worker Threads |
|-----------|---------------|---------------|
| **기본 개념** | 싱글 스레드 기반 비동기 실행 | 멀티 스레드 기반 작업 분산 |
| **사용 목적** | I/O 작업, 네트워크 요청 처리 | CPU 집약적인 연산 처리 |
| **비동기 방식** | 이벤트 기반 (Event-Driven) | 백그라운드 워커 스레드 사용 |
| **예제** | `setTimeout`, `setImmediate`, `Promise` | `worker_threads` 모듈 사용 |

## 핵심

### Worker Threads 기본 사용법

#### 메인 스레드에서 Worker 실행

**main.js**
```javascript
const { Worker } = require('worker_threads');

const worker = new Worker('./worker.js'); // 별도의 스레드 실행

worker.on('message', (msg) => console.log("워커에서 받은 메시지:", msg));
worker.postMessage("작업 시작");
```

**worker.js (Worker 스레드)**
```javascript
const { parentPort } = require('worker_threads');

parentPort.on('message', (msg) => {
    console.log("메인 스레드로부터 메시지:", msg);
    parentPort.postMessage("작업 완료!");
});
```

**실행 결과**
```
메인 스레드로부터 메시지: 작업 시작
워커에서 받은 메시지: 작업 완료!
```

워커는 메인과 별도 스레드라 이벤트 루프를 막지 않습니다.

### Worker Threads를 활용한 CPU 집약 작업

#### 싱글 스레드에서 연산 실행 (비효율적)

**single-thread.js**
```javascript
const heavyComputation = () => {
    let sum = 0;
    for (let i = 0; i < 1e9; i++) {
        sum += i;
    }
    return sum;
};

console.log("계산 시작");
console.log("결과:", heavyComputation());
console.log("계산 완료");
```

**실행 결과 (느림)**
```
계산 시작
(연산 지연)
결과: 499999999500000000
계산 완료
```

연산이 끝날 때까지 이벤트 루프가 막힙니다.

#### Worker Threads로 병렬 연산 (효율적)

**main.js (메인 스레드)**
```javascript
const { Worker } = require('worker_threads');

console.log("메인 스레드 시작");

const worker = new Worker('./computation-worker.js');

worker.on('message', (result) => {
    console.log("계산 결과:", result);
    console.log("메인 스레드 계속 실행 가능");
});

worker.on('error', (error) => {
    console.error("워커 오류:", error);
});

worker.on('exit', (code) => {
    if (code !== 0) {
        console.error(`워커가 코드 ${code}로 종료됨`);
    }
});

console.log("메인 스레드에서 다른 작업 수행 가능");
```

**computation-worker.js (Worker 스레드)**
```javascript
const { parentPort } = require('worker_threads');

const heavyComputation = () => {
    let sum = 0;
    for (let i = 0; i < 1e9; i++) {
        sum += i;
    }
    return sum;
};

console.log("워커 스레드에서 계산 시작");
const result = heavyComputation();
parentPort.postMessage(result);
console.log("워커 스레드 계산 완료");
```

**실행 결과 (빠름)**
```
메인 스레드 시작
메인 스레드에서 다른 작업 수행 가능
워커 스레드에서 계산 시작
(백그라운드에서 계산 진행)
워커 스레드 계산 완료
계산 결과: 499999999500000000
메인 스레드 계속 실행 가능
```

## 예시

### 실전 Worker Threads 예제

#### 이미지 처리 Worker
```javascript
// main.js - 메인 스레드
const { Worker } = require('worker_threads');
const express = require('express');

const app = express();
app.use(express.json());

// 이미지 처리 워커 생성
function createImageProcessingWorker() {
    return new Worker('./image-worker.js');
}

// 이미지 처리 요청 처리
app.post('/api/process-image', async (req, res) => {
    const { imageData, operations } = req.body;
    
    try {
        const result = await processImageWithWorker(imageData, operations);
        res.json({
            success: true,
            processedImage: result,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 워커를 사용한 이미지 처리
function processImageWithWorker(imageData, operations) {
    return new Promise((resolve, reject) => {
        const worker = createImageProcessingWorker();
        
        worker.on('message', (result) => {
            if (result.success) {
                resolve(result.processedImage);
            } else {
                reject(new Error(result.error));
            }
            worker.terminate();
        });
        
        worker.on('error', (error) => {
            reject(error);
            worker.terminate();
        });
        
        worker.on('exit', (code) => {
            if (code !== 0) {
                reject(new Error(`Worker exited with code ${code}`));
            }
        });
        
        // 워커에게 작업 전송
        worker.postMessage({
            imageData: imageData,
            operations: operations
        });
    });
}

// 서버 시작
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`서버가 포트 ${PORT}에서 실행 중`);
});

// 기본 라우트
app.get('/', (req, res) => {
    res.json({
        message: 'Image Processing Server with Worker Threads',
        endpoints: {
            'POST /api/process-image': '이미지 처리 요청'
        }
    });
});
```

```javascript
// image-worker.js - 이미지 처리 워커
const { parentPort } = require('worker_threads');

// 이미지 처리 작업
function processImage(imageData, operations) {
    // 실제 이미지 처리 로직 시뮬레이션
    let processedImage = imageData;
    
    operations.forEach(operation => {
        switch (operation.type) {
            case 'resize':
                processedImage = `resized_${processedImage}`;
                break;
            case 'filter':
                processedImage = `filtered_${processedImage}`;
                break;
            case 'compress':
                processedImage = `compressed_${processedImage}`;
                break;
            case 'enhance':
                processedImage = `enhanced_${processedImage}`;
                break;
            default:
                throw new Error(`Unknown operation: ${operation.type}`);
        }
    });
    
    return processedImage;
}

// 메인 스레드로부터 메시지 수신
parentPort.on('message', (data) => {
    try {
        const { imageData, operations } = data;
        
        console.log('이미지 처리 시작:', operations);
        
        // CPU 집약적인 이미지 처리 작업
        const processedImage = processImage(imageData, operations);
        
        // 처리 완료 후 결과 전송
        parentPort.postMessage({
            success: true,
            processedImage: processedImage,
            operations: operations
        });
        
        console.log('이미지 처리 완료');
        
    } catch (error) {
        parentPort.postMessage({
            success: false,
            error: error.message
        });
    }
});
```

#### 데이터 분석 Worker
```javascript
// main.js - 메인 스레드
const { Worker } = require('worker_threads');
const express = require('express');

const app = express();
app.use(express.json());

// 데이터 분석 워커 풀
class DataAnalysisWorkerPool {
    constructor(size = 4) {
        this.workers = [];
        this.taskQueue = [];
        this.availableWorkers = [];
        
        this.initializeWorkers(size);
    }
    
    initializeWorkers(size) {
        for (let i = 0; i < size; i++) {
            const worker = new Worker('./data-analysis-worker.js');
            
            worker.on('message', (result) => {
                this.handleWorkerResult(worker, result);
            });
            
            worker.on('error', (error) => {
                console.error(`Worker ${i} 오류:`, error);
                this.replaceWorker(worker);
            });
            
            this.workers.push(worker);
            this.availableWorkers.push(worker);
        }
    }
    
    async analyzeData(dataset, analysisType) {
        return new Promise((resolve, reject) => {
            const task = {
                dataset: dataset,
                analysisType: analysisType,
                resolve: resolve,
                reject: reject
            };
            
            this.taskQueue.push(task);
            this.processNextTask();
        });
    }
    
    processNextTask() {
        if (this.taskQueue.length === 0 || this.availableWorkers.length === 0) {
            return;
        }
        
        const task = this.taskQueue.shift();
        const worker = this.availableWorkers.shift();
        
        worker.currentTask = task;
        worker.postMessage({
            dataset: task.dataset,
            analysisType: task.analysisType
        });
    }
    
    handleWorkerResult(worker, result) {
        const task = worker.currentTask;
        
        if (result.success) {
            task.resolve(result.analysisResult);
        } else {
            task.reject(new Error(result.error));
        }
        
        worker.currentTask = null;
        this.availableWorkers.push(worker);
        this.processNextTask();
    }
    
    replaceWorker(failedWorker) {
        const index = this.workers.indexOf(failedWorker);
        if (index !== -1) {
            const newWorker = new Worker('./data-analysis-worker.js');
            
            newWorker.on('message', (result) => {
                this.handleWorkerResult(newWorker, result);
            });
            
            newWorker.on('error', (error) => {
                console.error('Replacement worker 오류:', error);
                this.replaceWorker(newWorker);
            });
            
            this.workers[index] = newWorker;
            this.availableWorkers.push(newWorker);
        }
    }
    
    shutdown() {
        this.workers.forEach(worker => worker.terminate());
    }
}

// 워커 풀 생성
const workerPool = new DataAnalysisWorkerPool(4);

// 데이터 분석 API
app.post('/api/analyze-data', async (req, res) => {
    const { dataset, analysisType } = req.body;
    
    try {
        const result = await workerPool.analyzeData(dataset, analysisType);
        res.json({
            success: true,
            analysisResult: result,
            analysisType: analysisType,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 서버 시작
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`데이터 분석 서버가 포트 ${PORT}에서 실행 중`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('서버 종료 중...');
    workerPool.shutdown();
    process.exit(0);
});
```

```javascript
// data-analysis-worker.js - 데이터 분석 워커
const { parentPort } = require('worker_threads');

// 통계 분석 함수
function performStatisticalAnalysis(dataset) {
    const n = dataset.length;
    if (n === 0) {
        throw new Error('빈 데이터셋');
    }
    
    const sum = dataset.reduce((acc, val) => acc + val, 0);
    const mean = sum / n;
    
    const variance = dataset.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / n;
    const standardDeviation = Math.sqrt(variance);
    
    const sortedData = [...dataset].sort((a, b) => a - b);
    const median = n % 2 === 0 
        ? (sortedData[n/2 - 1] + sortedData[n/2]) / 2
        : sortedData[Math.floor(n/2)];
    
    const min = sortedData[0];
    const max = sortedData[n - 1];
    
    return {
        count: n,
        mean: mean,
        median: median,
        standardDeviation: standardDeviation,
        variance: variance,
        min: min,
        max: max,
        range: max - min
    };
}

// 패턴 분석 함수
function performPatternAnalysis(dataset) {
    const patterns = {
        increasing: 0,
        decreasing: 0,
        alternating: 0,
        constant: 0
    };
    
    if (dataset.length < 2) {
        return patterns;
    }
    
    let isIncreasing = true;
    let isDecreasing = true;
    let isAlternating = true;
    let isConstant = true;
    
    for (let i = 1; i < dataset.length; i++) {
        const current = dataset[i];
        const previous = dataset[i - 1];
        
        if (current <= previous) isIncreasing = false;
        if (current >= previous) isDecreasing = false;
        if (current !== previous) isConstant = false;
        
        if (i > 1) {
            const prevDiff = dataset[i - 1] - dataset[i - 2];
            const currentDiff = current - previous;
            
            if (Math.sign(prevDiff) === Math.sign(currentDiff)) {
                isAlternating = false;
            }
        }
    }
    
    if (isIncreasing) patterns.increasing = 1;
    if (isDecreasing) patterns.decreasing = 1;
    if (isAlternating) patterns.alternating = 1;
    if (isConstant) patterns.constant = 1;
    
    return patterns;
}

// 메인 스레드로부터 메시지 수신
parentPort.on('message', (data) => {
    try {
        const { dataset, analysisType } = data;
        
        console.log('데이터 분석 시작:', analysisType);
        
        let analysisResult;
        
        switch (analysisType) {
            case 'statistical':
                analysisResult = performStatisticalAnalysis(dataset);
                break;
            case 'pattern':
                analysisResult = performPatternAnalysis(dataset);
                break;
            case 'comprehensive':
                analysisResult = {
                    statistical: performStatisticalAnalysis(dataset),
                    pattern: performPatternAnalysis(dataset)
                };
                break;
            default:
                throw new Error(`알 수 없는 분석 유형: ${analysisType}`);
        }
        
        // 분석 완료 후 결과 전송
        parentPort.postMessage({
            success: true,
            analysisResult: analysisResult,
            analysisType: analysisType
        });
        
        console.log('데이터 분석 완료');
        
    } catch (error) {
        parentPort.postMessage({
            success: false,
            error: error.message
        });
    }
});
```

### 고급 Worker Threads 예제

#### SharedArrayBuffer를 활용한 메모리 공유
```javascript
// main.js - 메인 스레드
const { Worker, SharedArrayBuffer, Atomics } = require('worker_threads');

class SharedMemoryManager {
    constructor(bufferSize = 1024) {
        this.sharedBuffer = new SharedArrayBuffer(bufferSize);
        this.sharedArray = new Int32Array(this.sharedBuffer);
        this.workers = [];
    }
    
    createWorker(workerScript) {
        const worker = new Worker(workerScript, {
            workerData: {
                sharedBuffer: this.sharedBuffer,
                bufferSize: this.sharedArray.length
            }
        });
        
        this.workers.push(worker);
        return worker;
    }
    
    // 공유 메모리에 데이터 쓰기
    writeToSharedMemory(index, value) {
        if (index >= 0 && index < this.sharedArray.length) {
            Atomics.store(this.sharedArray, index, value);
            return true;
        }
        return false;
    }
    
    // 공유 메모리에서 데이터 읽기
    readFromSharedMemory(index) {
        if (index >= 0 && index < this.sharedArray.length) {
            return Atomics.load(this.sharedArray, index);
        }
        return null;
    }
    
    // 모든 워커 종료
    shutdown() {
        this.workers.forEach(worker => worker.terminate());
    }
    
    // 공유 메모리 상태 출력
    printSharedMemory() {
        console.log('공유 메모리 상태:');
        for (let i = 0; i < this.sharedArray.length; i++) {
            const value = Atomics.load(this.sharedArray, i);
            if (value !== 0) {
                console.log(`[${i}]: ${value}`);
            }
        }
    }
}

// 사용 예제
async function demonstrateSharedMemory() {
    const memoryManager = new SharedMemoryManager(100);
    
    // 워커들 생성
    const worker1 = memoryManager.createWorker('./shared-memory-worker.js');
    const worker2 = memoryManager.createWorker('./shared-memory-worker.js');
    
    // 메인 스레드에서 초기 데이터 설정
    memoryManager.writeToSharedMemory(0, 100);
    memoryManager.writeToSharedMemory(1, 200);
    
    console.log('초기 공유 메모리:');
    memoryManager.printSharedMemory();
    
    // 워커들에게 작업 전송
    worker1.postMessage({ action: 'process', startIndex: 0, endIndex: 50 });
    worker2.postMessage({ action: 'process', startIndex: 50, endIndex: 100 });
    
    // 워커 완료 대기
    await new Promise(resolve => {
        let completedWorkers = 0;
        
        const checkCompletion = () => {
            completedWorkers++;
            if (completedWorkers === 2) {
                resolve();
            }
        };
        
        worker1.on('message', (msg) => {
            if (msg.type === 'completed') {
                console.log('Worker 1 완료');
                checkCompletion();
            }
        });
        
        worker2.on('message', (msg) => {
            if (msg.type === 'completed') {
                console.log('Worker 2 완료');
                checkCompletion();
            }
        });
    });
    
    console.log('\n최종 공유 메모리:');
    memoryManager.printSharedMemory();
    
    // 정리
    memoryManager.shutdown();
}

// 실행
demonstrateSharedMemory();
```

```javascript
// shared-memory-worker.js - 공유 메모리 워커
const { parentPort, workerData, SharedArrayBuffer, Atomics } = require('worker_threads');

// 공유 메모리 접근
const sharedArray = new Int32Array(workerData.sharedBuffer);
const bufferSize = workerData.bufferSize;

// 공유 메모리 처리 작업
function processSharedMemory(startIndex, endIndex) {
    console.log(`워커가 인덱스 ${startIndex}부터 ${endIndex}까지 처리 중`);
    
    for (let i = startIndex; i < endIndex; i++) {
        // 원자적 연산으로 값 증가
        const currentValue = Atomics.load(sharedArray, i);
        Atomics.store(sharedArray, i, currentValue + 1);
        
        // 처리 지연 시뮬레이션
        if (i % 10 === 0) {
            Atomics.wait(sharedArray, i, currentValue, 1);
        }
    }
}

// 메인 스레드로부터 메시지 수신
parentPort.on('message', (data) => {
    try {
        const { action, startIndex, endIndex } = data;
        
        if (action === 'process') {
            processSharedMemory(startIndex, endIndex);
            
            // 작업 완료 알림
            parentPort.postMessage({
                type: 'completed',
                workerId: process.threadId,
                processedRange: { startIndex, endIndex }
            });
        }
        
    } catch (error) {
        parentPort.postMessage({
            type: 'error',
            error: error.message
        });
    }
});
```

## 운영 팁

### Worker Threads 최적화

#### 워커 풀 관리
```javascript
// 워커 풀 클래스
class WorkerPool {
    constructor(size, workerScript) {
        this.size = size;
        this.workerScript = workerScript;
        this.workers = [];
        this.taskQueue = [];
        this.availableWorkers = [];
        
        this.initialize();
    }
    
    initialize() {
        for (let i = 0; i < this.size; i++) {
            const worker = new Worker(this.workerScript);
            
            worker.on('message', (result) => {
                this.handleWorkerResult(worker, result);
            });
            
            worker.on('error', (error) => {
                console.error(`Worker ${i} 오류:`, error);
                this.replaceWorker(worker);
            });
            
            worker.on('exit', (code) => {
                if (code !== 0) {
                    console.error(`Worker ${i}가 코드 ${code}로 종료됨`);
                    this.replaceWorker(worker);
                }
            });
            
            this.workers.push(worker);
            this.availableWorkers.push(worker);
        }
    }
    
    executeTask(taskData) {
        return new Promise((resolve, reject) => {
            const task = {
                data: taskData,
                resolve: resolve,
                reject: reject
            };
            
            this.taskQueue.push(task);
            this.processNextTask();
        });
    }
    
    processNextTask() {
        if (this.taskQueue.length === 0 || this.availableWorkers.length === 0) {
            return;
        }
        
        const task = this.taskQueue.shift();
        const worker = this.availableWorkers.shift();
        
        worker.currentTask = task;
        worker.postMessage(task.data);
    }
    
    handleWorkerResult(worker, result) {
        const task = worker.currentTask;
        
        if (result.success) {
            task.resolve(result.data);
        } else {
            task.reject(new Error(result.error));
        }
        
        worker.currentTask = null;
        this.availableWorkers.push(worker);
        this.processNextTask();
    }
    
    replaceWorker(failedWorker) {
        const index = this.workers.indexOf(failedWorker);
        if (index !== -1) {
            const newWorker = new Worker(this.workerScript);
            
            newWorker.on('message', (result) => {
                this.handleWorkerResult(newWorker, result);
            });
            
            newWorker.on('error', (error) => {
                console.error('Replacement worker 오류:', error);
                this.replaceWorker(newWorker);
            });
            
            this.workers[index] = newWorker;
            this.availableWorkers.push(newWorker);
        }
    }
    
    shutdown() {
        this.workers.forEach(worker => worker.terminate());
    }
    
    getStats() {
        return {
            totalWorkers: this.workers.length,
            availableWorkers: this.availableWorkers.length,
            queuedTasks: this.taskQueue.length
        };
    }
}

// 사용 예제
async function demonstrateWorkerPool() {
    const pool = new WorkerPool(4, './task-worker.js');
    
    // 여러 작업 동시 실행
    const tasks = [
        { id: 1, data: 'task1', delay: 1000 },
        { id: 2, data: 'task2', delay: 800 },
        { id: 3, data: 'task3', delay: 1200 },
        { id: 4, data: 'task4', delay: 600 },
        { id: 5, data: 'task5', delay: 900 }
    ];
    
    console.log('작업 시작...');
    const startTime = Date.now();
    
    const promises = tasks.map(task => pool.executeTask(task));
    const results = await Promise.all(promises);
    
    const endTime = Date.now();
    console.log(`모든 작업 완료 (${endTime - startTime}ms):`, results);
    
    console.log('풀 상태:', pool.getStats());
    
    pool.shutdown();
}

// 실행
demonstrateWorkerPool();
```

#### 성능 모니터링
```javascript
// Worker Threads 성능 모니터링
class WorkerThreadsMonitor {
    constructor() {
        this.metrics = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            averageTaskTime: 0,
            totalTaskTime: 0,
            activeWorkers: 0,
            maxWorkers: 0
        };
        
        this.taskTimes = [];
    }
    
    startTask() {
        this.metrics.totalTasks++;
        this.metrics.activeWorkers++;
        this.metrics.maxWorkers = Math.max(this.metrics.maxWorkers, this.metrics.activeWorkers);
        
        return Date.now();
    }
    
    endTask(startTime, success = true) {
        const taskTime = Date.now() - startTime;
        
        this.metrics.activeWorkers--;
        this.metrics.totalTaskTime += taskTime;
        this.taskTimes.push(taskTime);
        
        if (success) {
            this.metrics.completedTasks++;
        } else {
            this.metrics.failedTasks++;
        }
        
        this.metrics.averageTaskTime = this.metrics.totalTaskTime / 
            (this.metrics.completedTasks + this.metrics.failedTasks);
    }
    
    getMetrics() {
        return {
            ...this.metrics,
            successRate: this.metrics.totalTasks > 0 
                ? (this.metrics.completedTasks / this.metrics.totalTasks * 100).toFixed(2) + '%'
                : '0%',
            throughput: this.metrics.completedTasks > 0 
                ? (this.metrics.completedTasks / (this.metrics.totalTaskTime / 1000)).toFixed(2) + ' tasks/sec'
                : '0 tasks/sec'
        };
    }
    
    getDetailedMetrics() {
        const sortedTimes = [...this.taskTimes].sort((a, b) => a - b);
        const median = sortedTimes[Math.floor(sortedTimes.length / 2)];
        const min = sortedTimes[0] || 0;
        const max = sortedTimes[sortedTimes.length - 1] || 0;
        
        return {
            ...this.getMetrics(),
            taskTimeStats: {
                min: min + 'ms',
                max: max + 'ms',
                median: median + 'ms',
                p95: sortedTimes[Math.floor(sortedTimes.length * 0.95)] + 'ms',
                p99: sortedTimes[Math.floor(sortedTimes.length * 0.99)] + 'ms'
            }
        };
    }
    
    reset() {
        this.metrics = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            averageTaskTime: 0,
            totalTaskTime: 0,
            activeWorkers: 0,
            maxWorkers: 0
        };
        this.taskTimes = [];
    }
}

// 모니터링이 포함된 워커 풀
class MonitoredWorkerPool extends WorkerPool {
    constructor(size, workerScript) {
        super(size, workerScript);
        this.monitor = new WorkerThreadsMonitor();
    }
    
    async executeTask(taskData) {
        const startTime = this.monitor.startTask();
        
        try {
            const result = await super.executeTask(taskData);
            this.monitor.endTask(startTime, true);
            return result;
        } catch (error) {
            this.monitor.endTask(startTime, false);
            throw error;
        }
    }
    
    getMetrics() {
        return this.monitor.getDetailedMetrics();
    }
    
    resetMetrics() {
        this.monitor.reset();
    }
}
```

### 오류 처리 및 복구

#### 견고한 Worker Threads 구현
```javascript
// 견고한 워커 스레드 관리자
class RobustWorkerManager {
    constructor(workerScript, options = {}) {
        this.workerScript = workerScript;
        this.maxWorkers = options.maxWorkers || 4;
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        
        this.workers = new Map();
        this.taskQueue = [];
        this.retryCounts = new Map();
        this.isShuttingDown = false;
    }
    
    async executeTask(taskData, retryCount = 0) {
        if (this.isShuttingDown) {
            throw new Error('Worker manager is shutting down');
        }
        
        const worker = await this.getAvailableWorker();
        
        return new Promise((resolve, reject) => {
            const taskId = Date.now() + Math.random();
            const task = {
                id: taskId,
                data: taskData,
                resolve: resolve,
                reject: reject,
                retryCount: retryCount,
                startTime: Date.now()
            };
            
            // 타임아웃 설정
            const timeout = setTimeout(() => {
                this.handleTaskTimeout(worker, task);
            }, 30000); // 30초 타임아웃
            
            worker.currentTask = task;
            worker.taskTimeout = timeout;
            
            worker.once('message', (result) => {
                clearTimeout(worker.taskTimeout);
                this.handleWorkerResult(worker, result);
            });
            
            worker.once('error', (error) => {
                clearTimeout(worker.taskTimeout);
                this.handleWorkerError(worker, error, task);
            });
            
            worker.postMessage(taskData);
        });
    }
    
    async getAvailableWorker() {
        // 사용 가능한 워커 찾기
        for (const [id, worker] of this.workers) {
            if (!worker.currentTask && !worker.isRestarting) {
                return worker;
            }
        }
        
        // 새 워커 생성
        if (this.workers.size < this.maxWorkers) {
            return this.createWorker();
        }
        
        // 워커 대기
        return new Promise((resolve) => {
            this.taskQueue.push(resolve);
        });
    }
    
    createWorker() {
        const worker = new Worker(this.workerScript);
        const workerId = Date.now() + Math.random();
        
        worker.on('message', (result) => {
            this.handleWorkerResult(worker, result);
        });
        
        worker.on('error', (error) => {
            this.handleWorkerError(worker, error);
        });
        
        worker.on('exit', (code) => {
            this.handleWorkerExit(worker, code);
        });
        
        this.workers.set(workerId, worker);
        return worker;
    }
    
    handleWorkerResult(worker, result) {
        const task = worker.currentTask;
        if (!task) return;
        
        worker.currentTask = null;
        worker.taskTimeout = null;
        
        if (result.success) {
            task.resolve(result.data);
        } else {
            task.reject(new Error(result.error));
        }
        
        // 대기 중인 워커 요청 처리
        if (this.taskQueue.length > 0) {
            const resolve = this.taskQueue.shift();
            resolve(worker);
        }
    }
    
    handleWorkerError(worker, error, task = null) {
        console.error('Worker 오류:', error);
        
        if (task && task.retryCount < this.maxRetries) {
            console.log(`작업 재시도 중... (${task.retryCount + 1}/${this.maxRetries})`);
            
            setTimeout(() => {
                this.executeTask(task.data, task.retryCount + 1)
                    .then(task.resolve)
                    .catch(task.reject);
            }, this.retryDelay);
        } else if (task) {
            task.reject(error);
        }
        
        this.restartWorker(worker);
    }
    
    handleWorkerExit(worker, code) {
        if (code !== 0) {
            console.error(`Worker가 코드 ${code}로 종료됨`);
            this.restartWorker(worker);
        }
    }
    
    handleTaskTimeout(worker, task) {
        console.error(`작업 타임아웃: ${task.id}`);
        
        if (task.retryCount < this.maxRetries) {
            console.log(`타임아웃 작업 재시도 중... (${task.retryCount + 1}/${this.maxRetries})`);
            
            setTimeout(() => {
                this.executeTask(task.data, task.retryCount + 1)
                    .then(task.resolve)
                    .catch(task.reject);
            }, this.retryDelay);
        } else {
            task.reject(new Error('Task timeout after retries'));
        }
        
        this.restartWorker(worker);
    }
    
    restartWorker(worker) {
        worker.isRestarting = true;
        
        // 워커 종료
        worker.terminate();
        
        // 새 워커 생성
        setTimeout(() => {
            const newWorker = this.createWorker();
            worker.isRestarting = false;
            
            // 대기 중인 워커 요청 처리
            if (this.taskQueue.length > 0) {
                const resolve = this.taskQueue.shift();
                resolve(newWorker);
            }
        }, 1000);
    }
    
    shutdown() {
        this.isShuttingDown = true;
        
        this.workers.forEach(worker => {
            worker.terminate();
        });
        
        this.workers.clear();
        this.taskQueue.length = 0;
    }
}
```

## 참고

### Worker Threads vs Cluster 비교

#### 성능 비교 결과
```javascript
// 성능 비교 예제
const performanceComparison = {
    workerThreads: {
        advantages: [
            '메모리 공유 가능 (SharedArrayBuffer)',
            '스레드 생성 오버헤드가 적음',
            '통신 오버헤드가 적음',
            'CPU 집약적 작업에 최적화'
        ],
        disadvantages: [
            '단일 프로세스 내에서 실행',
            '한 스레드의 오류가 전체 프로세스에 영향',
            '메모리 공유로 인한 복잡성 증가'
        ],
        useCases: [
            '이미지/비디오 처리',
            '복잡한 수학 계산',
            '대용량 데이터 분석',
            '암호화/복호화 작업'
        ]
    },
    cluster: {
        advantages: [
            '프로세스 격리로 안정성 높음',
            '한 프로세스 오류가 다른 프로세스에 영향 없음',
            '메모리 격리로 안전함',
            'HTTP 서버 부하 분산에 최적화'
        ],
        disadvantages: [
            '프로세스 생성 오버헤드가 큼',
            '통신 오버헤드가 큼',
            '메모리 사용량이 많음'
        ],
        useCases: [
            '웹 서버 부하 분산',
            '마이크로서비스 아키텍처',
            '고가용성과 안정성이 중요한 경우',
            '독립적인 서비스 환경'
        ]
    }
};

// 권장 사용 가이드
const usageGuide = {
    useWorkerThreads: [
        'CPU 집약적인 계산 작업',
        '메모리 공유가 필요한 경우',
        '빠른 스레드 간 통신이 필요한 경우',
        '단일 애플리케이션 내에서 병렬 처리'
    ],
    useCluster: [
        'HTTP 요청 부하 분산',
        '프로세스 격리가 중요한 경우',
        '고가용성과 안정성이 중요한 경우',
        '독립적인 서비스 환경'
    ]
};
```

### 결론
Worker Threads는 Node.js에서 CPU 집약적인 작업을 효율적으로 처리할 수 있는 강력한 도구입니다.
메인 스레드의 이벤트 루프를 블로킹하지 않고 백그라운드에서 작업을 수행할 수 있습니다.
SharedArrayBuffer를 통해 스레드 간 메모리 공유가 가능하여 성능을 최적화할 수 있습니다.
적절한 워커 풀 관리와 오류 처리를 통해 안정적인 멀티스레드 애플리케이션을 구축할 수 있습니다.
Worker Threads와 Cluster를 적절히 선택하여 애플리케이션의 요구사항에 맞는 최적의 성능을 달성해야 합니다.










