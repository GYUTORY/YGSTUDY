---
title: Node.js Cluster vs Worker Threads (클러스터 vs 멀티스레드)
tags: [nodejs, kubernetes]
updated: 2025-08-15
---

# Node.js Cluster vs Worker Threads (클러스터 vs 멀티스레드)

## 배경

Node.js는 기본적으로 싱글 스레드로 동작한다. 멀티코어 CPU를 쓰려면 Cluster와 Worker Threads 두 가지 방법이 있다.

### 핵심 차이점
- **Cluster**: 프로세스를 여러 개 띄워 요청을 병렬 처리
- **Worker Threads**: 한 프로세스 안에서 스레드를 여러 개 만들어 병렬 연산 처리

### 각각의 필요성
- **Cluster**: 웹 서버의 요청 분산 처리, 고가용성 확보
- **Worker Threads**: CPU 집약적인 작업 처리, 메모리 공유가 필요한 경우

## 핵심

### Cluster와 Worker Threads의 비교

| 비교 항목 | Cluster (클러스터) | Worker Threads (멀티 스레드) |
|-----------|-----------------|-----------------|
| **기본 개념** | 여러 개의 프로세스를 생성하여 부하를 분산 | 하나의 프로세스 내에서 여러 개의 스레드 실행 |
| **사용 목적** | 웹 서버의 요청 분산 처리 | CPU 집약적인 작업 (암호화, 데이터 처리 등) |
| **멀티코어 활용** | O (각 프로세스가 개별 CPU 코어 사용) | O (스레드가 병렬 연산 가능) |
| **메모리 공유** | X (각 프로세스는 독립적인 메모리 공간 사용) | O (스레드는 동일한 메모리 공간 공유) |
| **성능 최적화** | 다수의 요청을 병렬 처리할 때 유리 | CPU 연산이 많은 작업에서 유리 |
| **대표적인 활용 예제** | HTTP 서버 부하 분산 | 이미지 처리, 대규모 데이터 연산 |

#### 표의 "메모리 공유 O" 는 조건부다

이 한 칸을 오해하면 설계가 통째로 틀어진다. Worker Threads 가 같은 프로세스 주소 공간에 있는 건 맞지만, **`postMessage` 와 `workerData` 로 넘긴 일반 객체는 구조화 복제(structured clone)로 복사된다.** 공유되는 건 `SharedArrayBuffer` 뿐이다.

```javascript
// share.js — 같은 파일을 워커로도 실행한다
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
if (isMainThread) {
  const plain = { n: 1 };
  const sab = new SharedArrayBuffer(4);
  const view = new Int32Array(sab);
  view[0] = 1;
  const w = new Worker(__filename, { workerData: { plain, sab } });
  w.on('message', () => {
    console.log('plain.n =', plain.n);      // 워커가 99 로 바꾼 뒤
    console.log('view[0] =', view[0]);
    process.exit(0);
  });
} else {
  workerData.plain.n = 99;
  Atomics.store(new Int32Array(workerData.sab), 0, 99);
  parentPort.postMessage('done');
}
```

```
plain.n = 1     ← 복사본이라 반영 안 됨
view[0] = 99    ← 공유 메모리라 반영됨
```

(Node v22.21.1 실측)

그래서 "메모리를 공유하니까 큰 데이터를 그냥 넘기면 되겠다"는 판단은 반대로 간다. 큰 배열을 `workerData` 로 넘기면 **직렬화 비용을 그대로 문다.** 진짜로 복사를 피하려면 `SharedArrayBuffer` 를 쓰거나 `transferList` 로 `ArrayBuffer` 소유권을 넘겨야 한다(넘긴 쪽은 그 버퍼를 못 쓰게 된다).

### Cluster (클러스터) 활용

#### 기본적인 Cluster 예제
```javascript
const cluster = require('cluster');
const http = require('http');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
    console.log(`마스터 프로세스 실행 (PID: ${process.pid})`);

    // CPU 코어 개수만큼 워커 프로세스 생성
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    // 워커 종료 이벤트 처리 (자동 복구)
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨`);
        cluster.fork();
    });
} else {
    // 워커 프로세스 실행
    http.createServer((req, res) => {
        res.writeHead(200);
        res.end('Hello, Cluster!');
    }).listen(3000);

    console.log(`워커 프로세스 실행 (PID: ${process.pid})`);
}
```  

#### 실행 결과
```
마스터 프로세스 실행 (PID: 12345)
워커 프로세스 실행 (PID: 12346)
워커 프로세스 실행 (PID: 12347)
워커 프로세스 실행 (PID: 12348)
워커 프로세스 실행 (PID: 12349)
```

이 예제의 `cluster.isMaster` 는 지금도 동작하지만 **현재 이름은 `cluster.isPrimary`** 다.

```
$ node -e "const c=require('cluster');console.log(c.isMaster, c.isPrimary, process.version)"
true true v22.21.1
```

v22.21.1 에서 둘 다 살아 있고 값도 같다. 실행 시 경고도 안 뜬다. 그래서 옛 코드가 조용히 남아 있기 쉬운데, 새로 쓰는 코드는 `isPrimary` 를 쓴다. 마스터/워커라는 말도 `primary`/`worker` 로 갈렸다.

한 가지 더 — `cluster.on('exit')` 에서 조건 없이 `cluster.fork()` 를 다시 부르는 이 패턴은 **부팅 단계에서 죽는 버그와 만나면 무한 재시작 루프**가 된다. 워커가 `listen` 도 못 하고 즉사하는 상황을 재현해 재시작 횟수를 세보면:

```javascript
const cluster = require('cluster');
if (cluster.isPrimary) {
  let n = 0; const t0 = Date.now();
  cluster.fork();
  cluster.on('exit', () => {
    n++;
    if (Date.now() - t0 > 1000) { console.log('1초 동안 재시작:', n); process.exit(0); }
    cluster.fork();
  });
} else {
  throw new Error('부팅 실패');
}
// → 1초 동안 재시작: 39   (실행 환경에 따라 달라진다)
```

죽고 살아나기를 쉬지 않고 반복하는데 로그에는 "워커 종료됨"만 계속 찍혀서 원인이 안 보인다. 아래 `HighAvailabilityCluster` 처럼 재시작 횟수 상한을 두거나, 최소한 재시작 사이에 backoff 를 넣는다.

### Worker Threads (멀티 스레드) 활용

#### 기본적인 Worker Threads 예제

**메인 스레드 (`main.js`)**
```javascript
const { Worker } = require('worker_threads');

console.log("메인 스레드 시작");

const worker = new Worker('./worker.js'); // Worker 스레드 실행

// Worker로부터 메시지 수신
worker.on('message', (result) => {
    console.log('Worker로부터 결과 수신:', result);
});

// Worker 오류 처리
worker.on('error', (error) => {
    console.error('Worker 오류:', error);
});

// Worker 종료 처리
worker.on('exit', (code) => {
    if (code !== 0) {
        console.error(`Worker가 코드 ${code}로 종료됨`);
    }
    console.log('메인 스레드 종료');
});
```

**Worker 스레드 (`worker.js`)**
```javascript
const { parentPort } = require('worker_threads');

console.log("Worker 스레드 시작");

// CPU 집약적인 작업 수행
let result = 0;
for (let i = 0; i < 1000000; i++) {
    result += Math.sqrt(i);
}

// 메인 스레드로 결과 전송
parentPort.postMessage({
    result: result,
    message: '계산 완료'
});

console.log("Worker 스레드 종료");
```

## 예시

### 실전 비교 예제

#### HTTP 서버 부하 분산 (Cluster)
```javascript
const cluster = require('cluster');
const express = require('express');
const os = require('os');

if (cluster.isMaster) {
    const numCPUs = os.cpus().length;
    console.log(`마스터 프로세스 시작 (PID: ${process.pid})`);
    console.log(`${numCPUs}개의 CPU 코어 감지됨`);

    // CPU 코어 개수만큼 워커 생성
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    // 워커 이벤트 처리
    cluster.on('fork', (worker) => {
        console.log(`워커 ${worker.process.pid} 생성됨`);
    });

    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨 (코드: ${code}, 시그널: ${signal})`);
        
        // 새로운 워커 생성 (고가용성 유지)
        const newWorker = cluster.fork();
        console.log(`새 워커 ${newWorker.process.pid} 생성됨`);
    });

    // 클러스터 상태 모니터링
    setInterval(() => {
        const workers = Object.keys(cluster.workers);
        console.log(`활성 워커 수: ${workers.length}`);
    }, 10000);

} else {
    // 워커 프로세스에서 Express 서버 실행
    const app = express();
    const port = process.env.PORT || 3000;

    // 미들웨어 설정
    app.use(express.json());
    app.use(express.urlencoded({ extended: true }));

    // 라우트 설정
    app.get('/', (req, res) => {
        res.json({
            message: 'Hello from Cluster!',
            workerId: process.pid,
            timestamp: new Date().toISOString()
        });
    });

    app.get('/api/data', async (req, res) => {
        try {
            // 비동기 작업 시뮬레이션
            await new Promise(resolve => setTimeout(resolve, 100));
            
            res.json({
                data: 'Sample data from cluster',
                workerId: process.pid,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    app.post('/api/process', (req, res) => {
        const { data } = req.body;
        
        // CPU 집약적인 작업
        let result = 0;
        for (let i = 0; i < 100000; i++) {
            result += Math.sqrt(i);
        }
        
        res.json({
            result: result,
            processedData: data,
            workerId: process.pid
        });
    });

    // 서버 시작
    app.listen(port, () => {
        console.log(`워커 ${process.pid}가 포트 ${port}에서 실행 중`);
    });

    // 워커 종료 처리
    process.on('SIGTERM', () => {
        console.log(`워커 ${process.pid} 종료 신호 수신`);
        process.exit(0);
    });
}
```

#### CPU 집약적인 작업 처리 (Worker Threads)
```javascript
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
const express = require('express');

if (isMainThread) {
    // 메인 스레드 (Express 서버)
    const app = express();
    const port = process.env.PORT || 3000;

    app.use(express.json());
    app.use(express.urlencoded({ extended: true }));

    // 기본 라우트
    app.get('/', (req, res) => {
        res.json({
            message: 'Hello from Worker Threads!',
            mainThreadId: process.pid,
            timestamp: new Date().toISOString()
        });
    });

    // CPU 집약적인 작업을 Worker Thread로 처리
    app.post('/api/heavy-computation', async (req, res) => {
        const { data, iterations = 1000000 } = req.body;

        try {
            const result = await performHeavyComputation(data, iterations);
            res.json({
                result: result,
                processedData: data,
                mainThreadId: process.pid,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    // 이미지 처리 작업
    app.post('/api/image-processing', async (req, res) => {
        const { imageData, operations } = req.body;

        try {
            const processedImage = await processImage(imageData, operations);
            res.json({
                processedImage: processedImage,
                operations: operations,
                mainThreadId: process.pid,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    // 데이터 분석 작업
    app.post('/api/data-analysis', async (req, res) => {
        const { dataset, analysisType } = req.body;

        try {
            const analysisResult = await analyzeData(dataset, analysisType);
            res.json({
                analysisResult: analysisResult,
                analysisType: analysisType,
                mainThreadId: process.pid,
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    // 서버 시작
    app.listen(port, () => {
        console.log(`메인 스레드 ${process.pid}가 포트 ${port}에서 실행 중`);
    });

} else {
    // Worker Thread에서 실행될 코드
    const { operation, data } = workerData;

    switch (operation) {
        case 'heavy-computation':
            const result = performHeavyComputation(data.data, data.iterations);
            parentPort.postMessage({ success: true, result: result });
            break;
            
        case 'image-processing':
            const processedImage = processImage(data.imageData, data.operations);
            parentPort.postMessage({ success: true, processedImage: processedImage });
            break;
            
        case 'data-analysis':
            const analysisResult = analyzeData(data.dataset, data.analysisType);
            parentPort.postMessage({ success: true, analysisResult: analysisResult });
            break;
            
        default:
            parentPort.postMessage({ success: false, error: 'Unknown operation' });
    }
}

// CPU 집약적인 계산 함수
function performHeavyComputation(data, iterations) {
    return new Promise((resolve, reject) => {
        try {
            let result = 0;
            for (let i = 0; i < iterations; i++) {
                result += Math.sqrt(i) + Math.sin(i) + Math.cos(i);
            }
            
            // 데이터 처리 시뮬레이션
            const processedData = data ? data.split('').reverse().join('') : '';
            
            resolve({
                computationResult: result,
                processedData: processedData,
                iterations: iterations
            });
        } catch (error) {
            reject(error);
        }
    });
}

// 이미지 처리 함수 (시뮬레이션)
function processImage(imageData, operations) {
    return new Promise((resolve, reject) => {
        try {
            // 이미지 처리 시뮬레이션
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
                }
            });
            
            resolve(processedImage);
        } catch (error) {
            reject(error);
        }
    });
}

// 데이터 분석 함수 (시뮬레이션)
function analyzeData(dataset, analysisType) {
    return new Promise((resolve, reject) => {
        try {
            let analysisResult = {};
            
            switch (analysisType) {
                case 'statistical':
                    analysisResult = {
                        mean: dataset.reduce((sum, val) => sum + val, 0) / dataset.length,
                        median: dataset.sort((a, b) => a - b)[Math.floor(dataset.length / 2)],
                        standardDeviation: Math.sqrt(dataset.reduce((sum, val) => sum + Math.pow(val - (dataset.reduce((s, v) => s + v, 0) / dataset.length), 2), 0) / dataset.length)
                    };
                    break;
                    
                case 'pattern':
                    analysisResult = {
                        patterns: dataset.filter((val, index) => index > 0 && val > dataset[index - 1]).length,
                        trends: dataset[dataset.length - 1] > dataset[0] ? 'increasing' : 'decreasing'
                    };
                    break;
                    
                default:
                    analysisResult = { error: 'Unknown analysis type' };
            }
            
            resolve(analysisResult);
        } catch (error) {
            reject(error);
        }
    });
}

// Worker Thread 생성 함수
function createWorker(operation, data) {
    return new Promise((resolve, reject) => {
        const worker = new Worker(__filename, {
            workerData: { operation, data }
        });

        worker.on('message', (result) => {
            if (result.success) {
                resolve(result);
            } else {
                reject(new Error(result.error));
            }
        });

        worker.on('error', reject);
        worker.on('exit', (code) => {
            if (code !== 0) {
                reject(new Error(`Worker stopped with exit code ${code}`));
            }
        });
    });
}
```

위 `analyzeData` 의 `median` 계산에는 걸리기 쉬운 함정이 둘 있다.

```
$ node -e "
> const ds=[5,1,4,2,3];
> const median = ds.sort((a,b)=>a-b)[Math.floor(ds.length/2)];
> console.log('정렬 후 원본:', ds, '/ median:', median);
> const even=[1,2,3,4];
> console.log('짝수 길이:', even.sort((a,b)=>a-b)[Math.floor(even.length/2)]);"
정렬 후 원본: [ 1, 2, 3, 4, 5 ] / median: 3
짝수 길이: 3
```

첫째, `Array.prototype.sort` 는 **인자로 받은 배열을 그 자리에서 정렬한다.** 호출한 쪽의 `dataset` 순서가 바뀐다. 원본 순서를 쓰는 코드가 뒤에 있으면 조용히 결과가 달라진다. `[...dataset].sort(...)` 로 복사본을 만든다.

둘째, 짝수 길이에서 위 식은 산술 중앙값(2.5)이 아니라 위쪽 값(3)을 준다. 통계 지표로 쓸 거면 짝수일 때 두 값의 평균을 내야 한다.

`worker.on('exit')` 핸들러도 눈여겨본다. 종료 코드가 0 이면 `reject` 도 `resolve` 도 하지 않는다. 워커가 `postMessage` 없이 정상 종료하면 이 `Promise` 는 영원히 매달린다 — 아래 벤치마크 코드가 정확히 이 상태에 빠진다.

### 고급 비교 예제

#### 성능 비교 테스트
```javascript
const cluster = require('cluster');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
const express = require('express');
const os = require('os');

class PerformanceComparison {
    constructor() {
        this.numCPUs = os.cpus().length;
        this.testData = new Array(1000000).fill(0).map((_, i) => i);
    }

    async runClusterTest() {
        if (cluster.isMaster) {
            console.log('=== Cluster 성능 테스트 시작 ===');
            
            const startTime = Date.now();
            const promises = [];
            
            // 여러 워커 생성
            for (let i = 0; i < this.numCPUs; i++) {
                const promise = new Promise((resolve) => {
                    const worker = cluster.fork();
                    worker.on('message', (result) => {
                        resolve(result);
                    });
                });
                promises.push(promise);
            }
            
            const results = await Promise.all(promises);
            const endTime = Date.now();
            
            console.log(`Cluster 테스트 완료: ${endTime - startTime}ms`);
            console.log('결과:', results);
            
            return { method: 'cluster', duration: endTime - startTime, results };
        } else {
            // 워커에서 계산 수행
            const result = this.performHeavyCalculation(this.testData);
            process.send({ workerId: process.pid, result: result });
        }
    }

    async runWorkerThreadsTest() {
        if (isMainThread) {
            console.log('=== Worker Threads 성능 테스트 시작 ===');
            
            const startTime = Date.now();
            const promises = [];
            
            // 여러 Worker Thread 생성
            for (let i = 0; i < this.numCPUs; i++) {
                const promise = new Promise((resolve, reject) => {
                    const worker = new Worker(__filename, {
                        workerData: { 
                            type: 'worker-thread',
                            data: this.testData.slice(i * 250000, (i + 1) * 250000)
                        }
                    });
                    
                    worker.on('message', (result) => {
                        resolve(result);
                    });
                    
                    worker.on('error', reject);
                });
                promises.push(promise);
            }
            
            const results = await Promise.all(promises);
            const endTime = Date.now();
            
            console.log(`Worker Threads 테스트 완료: ${endTime - startTime}ms`);
            console.log('결과:', results);
            
            return { method: 'worker-threads', duration: endTime - startTime, results };
        } else {
            // Worker Thread에서 계산 수행
            const { data } = workerData;
            const result = this.performHeavyCalculation(data);
            parentPort.postMessage({ threadId: process.threadId, result: result });
        }
    }

    performHeavyCalculation(data) {
        let result = 0;
        for (let i = 0; i < data.length; i++) {
            result += Math.sqrt(data[i]) + Math.sin(data[i]) + Math.cos(data[i]);
        }
        return result;
    }

    async comparePerformance() {
        console.log('성능 비교 테스트 시작...');
        
        const clusterResult = await this.runClusterTest();
        const workerThreadsResult = await this.runWorkerThreadsTest();
        
        console.log('\n=== 성능 비교 결과 ===');
        console.log(`Cluster: ${clusterResult.duration}ms`);
        console.log(`Worker Threads: ${workerThreadsResult.duration}ms`);
        
        const difference = clusterResult.duration - workerThreadsResult.duration;
        const faster = difference > 0 ? 'Worker Threads' : 'Cluster';
        const improvement = Math.abs(difference) / Math.max(clusterResult.duration, workerThreadsResult.duration) * 100;
        
        console.log(`${faster}가 ${improvement.toFixed(2)}% 더 빠릅니다.`);
        
        return { clusterResult, workerThreadsResult, faster, improvement };
    }
}

// 성능 비교 실행
if (isMainThread && !cluster.isMaster) {
    const comparison = new PerformanceComparison();
    comparison.comparePerformance();
}
```

#### 위 벤치마크 코드는 실행되지 않는다 — 세 군데가 막혀 있다

읽고 넘어가면 그럴듯한데, 실제로 돌리면 아무 일도 안 일어난다. 순서대로 짚는다.

**1. 진입 조건이 프라이머리에서 항상 false 다.**

```
$ node -e "const c=require('cluster');const {isMainThread}=require('worker_threads');
> console.log(isMainThread, c.isMaster, (isMainThread && !c.isMaster))"
true true false
```

`isMainThread` 는 워커 스레드가 아니면 true, `cluster.isMaster` 는 클러스터 워커가 아니면 true 다. 즉 **평범하게 `node file.js` 로 띄운 프로세스에서는 두 조건이 동시에 만족될 수 없다.** 이 조건이 true 가 되는 곳은 오직 *클러스터 워커 프로세스 안*이다(실측: 워커에서 `isMainThread=true, isMaster=false` → true). 그런데 그 워커를 만드는 코드는 `comparePerformance()` 안에 있으니, 아무도 첫 fork 를 하지 않는다. 스크립트는 조용히 끝난다.

설령 어떻게든 워커 안에서 실행됐다면 이번엔 `runClusterTest()` 가 또 `cluster.fork()` 를 하고, 그 손자 워커에서 조건이 다시 true 가 되어 **재귀적으로 fork** 한다. 안 도는 게 차라리 다행인 코드다.

**2. 워커 쪽 `else` 분기는 클래스 메서드 안에 있어서 절대 실행되지 않는다.**

`new Worker(__filename)` 은 그 파일을 **처음부터 다시 실행**한다. 워커에서 다시 도는 건 모듈 최상위 코드뿐이고, `runWorkerThreadsTest()` 라는 메서드는 누가 부르지 않으면 호출되지 않는다. 최상위에는 그걸 부르는 코드가 없다. 결과는 "워커가 아무것도 안 하고 즉시 종료 → `postMessage` 없음 → `Promise` 영원히 미해결" 이다.

```javascript
// 같은 구조를 최소로 재현
const { Worker, isMainThread, parentPort } = require('worker_threads');
class T {
  async run() {
    if (isMainThread) {
      return new Promise((resolve) => {
        const w = new Worker(__filename);
        w.on('message', resolve);
        w.on('exit', c => console.log('워커 종료 code=' + c + ' — resolve 호출 안 됨'));
      });
    } else {
      parentPort.postMessage({ ok: true });   // 여기 못 온다
    }
  }
}
if (isMainThread) new T().run().then(r => console.log('resolved', r));
```

```
워커 종료 code=0 — resolve 호출 안 됨
(그리고 프로그램은 멈춘 채로 남는다)
```

워커 진입점은 **모듈 최상위에서 갈라야 한다.** 클래스 메서드 안의 `if (isMainThread)` 는 메인 쪽 코드에만 쓸모가 있다.

**3. `process.threadId` 는 존재하지 않는다.**

`parentPort.postMessage({ threadId: process.threadId, ... })` 는 예외 없이 `undefined` 를 보낸다. 스레드 ID 는 `worker_threads` 모듈에 있다.

```
from worker: { process_threadId: undefined, wt_threadId: 1 }
```

```javascript
const { threadId } = require('worker_threads');   // ← 이쪽
```

에러가 안 나고 `undefined` 만 조용히 실려 나가는 부류라, 로그에 `threadId: undefined` 가 찍히기 전까지 아무도 모른다.

## 운영 팁

### 선택 가이드

#### 언제 Cluster를 사용할까?
```javascript
// 1. HTTP 서버 부하 분산이 필요한 경우
const cluster = require('cluster');
const express = require('express');

if (cluster.isMaster) {
    // 마스터 프로세스
    const numCPUs = require('os').cpus().length;
    
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }
    
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨`);
        cluster.fork(); // 자동 복구
    });
} else {
    // 워커 프로세스
    const app = express();
    
    app.get('/', (req, res) => {
        res.json({ workerId: process.pid });
    });
    
    app.listen(3000, () => {
        console.log(`워커 ${process.pid} 실행 중`);
    });
}

// 2. 고가용성이 중요한 경우
class HighAvailabilityCluster {
    constructor() {
        this.workers = new Map();
        this.maxRestarts = 5;
        this.restartCounts = new Map();
    }
    
    start() {
        if (cluster.isMaster) {
            this.startMaster();
        } else {
            this.startWorker();
        }
    }
    
    startMaster() {
        const numCPUs = require('os').cpus().length;
        
        for (let i = 0; i < numCPUs; i++) {
            this.createWorker();
        }
        
        cluster.on('exit', (worker, code, signal) => {
            const restartCount = this.restartCounts.get(worker.id) || 0;
            
            if (restartCount < this.maxRestarts) {
                console.log(`워커 ${worker.process.pid} 재시작 중... (${restartCount + 1}/${this.maxRestarts})`);
                const newWorker = this.createWorker();
                this.restartCounts.set(newWorker.id, restartCount + 1);
            } else {
                console.error(`워커 ${worker.process.pid} 최대 재시작 횟수 초과`);
            }
        });
    }
    
    createWorker() {
        const worker = cluster.fork();
        this.workers.set(worker.id, worker);
        return worker;
    }
    
    startWorker() {
        // 워커 프로세스 로직
        console.log(`워커 ${process.pid} 시작됨`);
    }
}
```

#### 언제 Worker Threads를 사용할까?
```javascript
// 1. CPU 집약적인 작업이 필요한 경우
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

if (isMainThread) {
    // 메인 스레드
    const worker = new Worker(__filename, {
        workerData: { 
            operation: 'encrypt',
            data: 'sensitive-data',
            algorithm: 'sha256'
        }
    });
    
    worker.on('message', (result) => {
        console.log('암호화 완료:', result);
    });
} else {
    // Worker 스레드
    const { operation, data, algorithm } = workerData;
    
    if (operation === 'encrypt') {
        const crypto = require('crypto');
        const hash = crypto.createHash(algorithm).update(data).digest('hex');
        parentPort.postMessage({ hash: hash });
    }
}

// 2. 메모리 공유가 필요한 경우
const { Worker, isMainThread, parentPort, SharedArrayBuffer, Atomics } = require('worker_threads');

if (isMainThread) {
    // 메인 스레드
    const sharedBuffer = new SharedArrayBuffer(1024);
    const sharedArray = new Int32Array(sharedBuffer);
    
    const worker = new Worker(__filename, {
        workerData: { sharedBuffer: sharedBuffer }
    });
    
    worker.on('message', (result) => {
        console.log('공유 메모리 값:', sharedArray[0]);
    });
} else {
    // Worker 스레드
    const { sharedBuffer } = workerData;
    const sharedArray = new Int32Array(sharedBuffer);
    
    // 공유 메모리에 값 쓰기
    Atomics.store(sharedArray, 0, 42);
    parentPort.postMessage({ success: true });
}
```

바로 위 "메모리 공유" 예제는 **첫 줄에서 터진다.** `worker_threads` 는 `SharedArrayBuffer` 도 `Atomics` 도 export 하지 않는데, 구조 분해로 받으면서 두 전역을 `undefined` 로 덮어버린다.

```
$ node -e "const wt=require('worker_threads');
> console.log('SharedArrayBuffer' in wt, 'Atomics' in wt)"
false false

$ node -e "const { SharedArrayBuffer } = require('worker_threads'); new SharedArrayBuffer(1024)"
TypeError: SharedArrayBuffer is not a constructor
```

`SharedArrayBuffer` 와 `Atomics` 는 **JavaScript 전역**이라 아무것도 import 하지 않아도 쓸 수 있다. `require` 목록에서 지우기만 하면 된다.

이 부류는 "없는 이름을 import 하면 에러가 나겠지"라는 감각으로는 못 잡는다. CommonJS 구조 분해는 없는 키를 `undefined` 로 조용히 내주고, 이름이 전역과 겹칠 때만 이렇게 전역을 가린다.

덧붙여 이 절의 예제 1·2·3 은 **한 파일에 이어 붙이면 파싱 자체가 안 된다.** 같은 스코프에서 `const { Worker, ... }` 를 두 번 선언하기 때문이다.

```
$ node --check dup.js
SyntaxError: Identifier 'Worker' has already been declared
```

`node --check` 로 3초면 확인된다. 문서의 코드를 복사해 한 파일에 모을 때 자주 밟는다.

```javascript
// 3. 실시간 데이터 처리가 필요한 경우
class RealTimeDataProcessor {
    constructor() {
        this.workers = new Map();
        this.dataQueue = [];
    }
    
    createWorker() {
        const worker = new Worker(__filename, {
            workerData: { type: 'data-processor' }
        });
        
        worker.on('message', (result) => {
            this.handleProcessedData(result);
        });
        
        return worker;
    }
    
    processData(data) {
        const worker = this.createWorker();
        worker.postMessage({ data: data });
    }
    
    handleProcessedData(result) {
        console.log('처리된 데이터:', result);
    }
}
```

### 성능 최적화

#### Cluster 최적화 기법
```javascript
// 1. 워커 수 최적화
class OptimizedCluster {
    constructor() {
        this.numCPUs = require('os').cpus().length;
        this.optimalWorkerCount = this.calculateOptimalWorkerCount();
    }
    
    calculateOptimalWorkerCount() {
        // I/O 집약적인 애플리케이션: CPU 코어 수보다 많은 워커
        // CPU 집약적인 애플리케이션: CPU 코어 수만큼 워커
        const isIOIntensive = process.env.IO_INTENSIVE === 'true';
        return isIOIntensive ? this.numCPUs * 2 : this.numCPUs;
    }
    
    start() {
        if (cluster.isMaster) {
            console.log(`최적화된 워커 수: ${this.optimalWorkerCount}`);
            
            for (let i = 0; i < this.optimalWorkerCount; i++) {
                cluster.fork();
            }
        } else {
            this.startWorker();
        }
    }
    
    startWorker() {
        // 워커 프로세스 로직
        console.log(`워커 ${process.pid} 시작됨`);
    }
}

// 2. 로드 밸런싱 최적화
class LoadBalancedCluster {
    constructor() {
        this.workerStats = new Map();
    }
    
    start() {
        if (cluster.isMaster) {
            this.startMaster();
        } else {
            this.startWorker();
        }
    }
    
    startMaster() {
        const numCPUs = require('os').cpus().length;
        
        for (let i = 0; i < numCPUs; i++) {
            const worker = cluster.fork();
            this.workerStats.set(worker.id, {
                requests: 0,
                startTime: Date.now()
            });
        }
        
        cluster.on('message', (worker, message) => {
            if (message.type === 'request') {
                const stats = this.workerStats.get(worker.id);
                if (stats) {
                    stats.requests++;
                }
            }
        });
    }
    
    startWorker() {
        // 워커 프로세스 로직
        process.on('message', (message) => {
            if (message.type === 'request') {
                process.send({ type: 'request' });
            }
        });
    }
}
```

#### Worker Threads 최적화 기법
```javascript
// 1. 스레드 풀 관리
class ThreadPool {
    constructor(size) {
        this.size = size;
        this.workers = [];
        this.taskQueue = [];
        this.activeWorkers = 0;
    }
    
    initialize() {
        for (let i = 0; i < this.size; i++) {
            const worker = new Worker(__filename, {
                workerData: { type: 'worker' }
            });
            
            worker.on('message', (result) => {
                this.handleWorkerResult(worker, result);
            });
            
            worker.on('error', (error) => {
                console.error('Worker 오류:', error);
                this.replaceWorker(worker);
            });
            
            this.workers.push(worker);
        }
    }
    
    executeTask(task) {
        return new Promise((resolve, reject) => {
            const taskWrapper = { task, resolve, reject };
            this.taskQueue.push(taskWrapper);
            this.processNextTask();
        });
    }
    
    processNextTask() {
        if (this.taskQueue.length === 0 || this.activeWorkers >= this.size) {
            return;
        }
        
        const availableWorker = this.workers.find(worker => !worker.busy);
        if (availableWorker) {
            const taskWrapper = this.taskQueue.shift();
            availableWorker.busy = true;
            this.activeWorkers++;
            
            availableWorker.postMessage(taskWrapper.task);
            availableWorker.currentTask = taskWrapper;
        }
    }
    
    handleWorkerResult(worker, result) {
        worker.busy = false;
        this.activeWorkers--;
        
        if (worker.currentTask) {
            worker.currentTask.resolve(result);
            worker.currentTask = null;
        }
        
        this.processNextTask();
    }
    
    replaceWorker(failedWorker) {
        const index = this.workers.indexOf(failedWorker);
        if (index !== -1) {
            const newWorker = new Worker(__filename, {
                workerData: { type: 'worker' }
            });
            
            newWorker.on('message', (result) => {
                this.handleWorkerResult(newWorker, result);
            });
            
            this.workers[index] = newWorker;
        }
    }
}

// 2. 메모리 공유 최적화
class SharedMemoryManager {
    constructor() {
        this.sharedBuffers = new Map();
    }
    
    createSharedBuffer(name, size) {
        const buffer = new SharedArrayBuffer(size);
        this.sharedBuffers.set(name, buffer);
        return buffer;
    }
    
    getSharedBuffer(name) {
        return this.sharedBuffers.get(name);
    }
    
    createWorkerWithSharedMemory(workerScript, sharedBuffers) {
        return new Worker(workerScript, {
            workerData: { sharedBuffers: sharedBuffers }
        });
    }
}
```

## 참고

### 성능 벤치마크 결과

아래 객체는 **측정값이 아니라 손으로 적어 넣은 리터럴**이다. 어떤 하드웨어에서, 어떤 부하로, 무엇을 잰 것인지가 없다. 그대로 인용하면 안 된다.

숫자보다 중요한 건 두 방식의 비용 구조가 다르다는 점이다. Cluster 는 프로세스마다 V8 힙과 런타임을 통째로 하나씩 갖는다. Worker Threads 는 힙은 스레드마다 따로지만 런타임 자체는 한 프로세스 안이라 기동이 가볍다. 대신 위에서 본 것처럼 **데이터를 주고받을 때마다 구조화 복제 비용**을 문다. 그래서 "요청당 데이터가 작고 요청 수가 많다"면 Cluster, "요청은 드문데 넘기는 데이터가 크다"면 복제 비용부터 재봐야 한다.

직접 재려면 자기 워크로드로 잰다. 남의 표를 가져다 쓰면 CPU 코어 수·Node 버전·페이로드 크기가 전부 다르다.

#### 일반적인 성능 비교
```javascript
// 성능 벤치마크 결과 예시
const benchmarkResults = {
    cluster: {
        httpRequests: {
            requestsPerSecond: 15000,
            averageResponseTime: 2.5,
            memoryUsage: '각 프로세스 50MB'
        },
        cpuIntensiveTasks: {
            tasksPerSecond: 100,
            averageTaskTime: 10,
            memoryUsage: '각 프로세스 100MB'
        }
    },
    workerThreads: {
        httpRequests: {
            requestsPerSecond: 8000,
            averageResponseTime: 5.0,
            memoryUsage: '전체 프로세스 200MB'
        },
        cpuIntensiveTasks: {
            tasksPerSecond: 500,
            averageTaskTime: 2,
            memoryUsage: '전체 프로세스 150MB'
        }
    }
};

// 권장 사용 사례
const recommendations = {
    cluster: [
        '웹 서버 부하 분산',
        '마이크로서비스 아키텍처',
        '고가용성 요구사항',
        '독립적인 프로세스 환경'
    ],
    workerThreads: [
        'CPU 집약적인 계산',
        '이미지/비디오 처리',
        '대용량 데이터 분석',
        '메모리 공유가 필요한 경우'
    ]
};
```

### 결론
Cluster와 Worker Threads는 목적도 장단점도 다르다.
HTTP 서버 부하 분산에는 Cluster가, CPU 집약적인 작업에는 Worker Threads가 적합하다.
잘 고르고 최적화하면 성능을 끌어올릴 수 있다.
메모리 공유가 필요하면 Worker Threads를, 독립적인 프로세스가 필요하면 Cluster를 쓴다.
성능 요구사항과 시스템 아키텍처를 보고 고른다.
실제 환경에서 성능을 직접 재보고 최적화한다.