---
title: Node.js Cluster (클러스터)
tags: [framework, node, nodejs의-구조-및-작동-원리, cluster, nodejs, multi-process]
updated: 2025-08-15
---

# Node.js Cluster (클러스터)

## 배경

Node.js의 Cluster 모듈은 단일 프로세스에서 여러 개의 워커 프로세스를 생성하여 멀티코어 CPU를 활용할 수 있게 해주는 기능입니다. Node.js는 기본적으로 싱글 스레드이지만, Cluster를 사용하면 여러 프로세스를 통해 병렬 처리가 가능합니다.

### Cluster의 필요성
- **CPU 활용**: 멀티코어 시스템의 모든 코어를 활용
- **성능 향상**: 동시 요청 처리 능력 증가
- **고가용성**: 하나의 프로세스가 죽어도 다른 프로세스가 계속 동작
- **부하 분산**: 요청을 여러 프로세스에 분산 처리

### Cluster의 동작 원리
- **마스터 프로세스**: 워커 프로세스를 생성하고 관리
- **워커 프로세스**: 실제 요청을 처리하는 프로세스
- **로드 밸런싱**: 운영체제가 요청을 워커 프로세스에 분산

## 핵심

### 기본 Cluster 구조

#### 마스터-워커 패턴
```javascript
const cluster = require('cluster');
const http = require('http');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
    // 마스터 프로세스 실행
    console.log(`마스터 프로세스 ${process.pid} 실행 중`);

    // CPU 코어 개수만큼 워커 생성
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork(); // 워커 프로세스 생성
    }

    // 워커 종료 이벤트 처리 (고가용성 유지)
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨`);
        cluster.fork(); // 새로운 워커 생성
    });
} else {
    // 워커 프로세스 실행
    http.createServer((req, res) => {
        res.writeHead(200);
        res.end('Hello, Cluster!');
    }).listen(3000);

    console.log(`워커 프로세스 ${process.pid} 실행 중`);
}
```

#### 실행 결과
```
마스터 프로세스 12345 실행 중
워커 프로세스 12346 실행 중
워커 프로세스 12347 실행 중
워커 프로세스 12348 실행 중
워커 프로세스 12349 실행 중
```

### Cluster 모듈의 주요 기능

#### 워커 프로세스 관리
```javascript
const cluster = require('cluster');

if (cluster.isMaster) {
    // 워커 생성
    const worker1 = cluster.fork();
    const worker2 = cluster.fork();
    
    // 워커 이벤트 리스너
    worker1.on('message', (msg) => {
        console.log('워커1로부터 메시지:', msg);
    });
    
    worker2.on('message', (msg) => {
        console.log('워커2로부터 메시지:', msg);
    });
    
    // 워커 종료 처리
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨 (코드: ${code}, 시그널: ${signal})`);
        
        // 새로운 워커 생성
        const newWorker = cluster.fork();
        console.log(`새 워커 ${newWorker.process.pid} 생성됨`);
    });
    
    // 모든 워커 종료 시 마스터도 종료
    cluster.on('exit', (worker, code, signal) => {
        if (Object.keys(cluster.workers).length === 0) {
            console.log('모든 워커가 종료되었습니다.');
            process.exit(0);
        }
    });
} else {
    // 워커 프로세스에서 실행할 코드
    console.log(`워커 ${process.pid} 시작됨`);
    
    // 마스터에게 메시지 전송
    process.send({ type: 'ready', pid: process.pid });
}
```

## 예시

### Express 애플리케이션에서 Cluster 사용

#### 기본 Express Cluster 설정
```javascript
const cluster = require('cluster');
const express = require('express');
const os = require('os');

if (cluster.isMaster) {
    const numCPUs = os.cpus().length;
    console.log(`마스터 프로세스 ${process.pid} 시작`);
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

    app.get('/health', (req, res) => {
        res.json({
            status: 'healthy',
            workerId: process.pid,
            uptime: process.uptime(),
            memory: process.memoryUsage()
        });
    });

    app.get('/heavy-task', (req, res) => {
        // CPU 집약적인 작업 시뮬레이션
        const start = Date.now();
        let result = 0;
        
        for (let i = 0; i < 1000000; i++) {
            result += Math.sqrt(i);
        }
        
        const duration = Date.now() - start;
        
        res.json({
            result: result,
            duration: duration,
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

### 실전 애플리케이션 예제

#### 고급 Cluster 설정
```javascript
const cluster = require('cluster');
const express = require('express');
const os = require('os');
const path = require('path');

class ClusterManager {
    constructor() {
        this.numCPUs = os.cpus().length;
        this.workers = new Map();
        this.restartCount = new Map();
        this.maxRestarts = 5;
        this.restartDelay = 1000;
    }

    start() {
        if (cluster.isMaster) {
            this.startMaster();
        } else {
            this.startWorker();
        }
    }

    startMaster() {
        console.log(`마스터 프로세스 ${process.pid} 시작`);
        console.log(`CPU 코어 수: ${this.numCPUs}`);

        // 워커 생성
        for (let i = 0; i < this.numCPUs; i++) {
            this.createWorker();
        }

        // 이벤트 리스너 설정
        this.setupEventListeners();

        // 모니터링 시작
        this.startMonitoring();

        // Graceful shutdown 처리
        this.setupGracefulShutdown();
    }

    createWorker() {
        const worker = cluster.fork();
        
        this.workerStats.set(worker.id, {
            pid: worker.process.pid,
            connections: 0,
            requests: 0,
            startTime: Date.now(),
            status: 'active'
        });

        console.log(`워커 ${worker.process.pid} 생성됨 (ID: ${worker.id})`);
    }

    setupEventListeners() {
        cluster.on('exit', (worker, code, signal) => {
            const workerId = worker.id;
            const restartCount = this.restartCount.get(workerId) || 0;

            console.log(`워커 ${worker.process.pid} 종료됨 (코드: ${code}, 시그널: ${signal})`);

            if (restartCount < this.maxRestarts) {
                console.log(`워커 ${workerId} 재시작 중... (${restartCount + 1}/${this.maxRestarts})`);
                
                setTimeout(() => {
                    const newWorker = cluster.fork();
                    this.workers.set(newWorker.id, workerId);
                    this.restartCount.set(newWorker.id, restartCount + 1);
                }, this.restartDelay);
            } else {
                console.error(`워커 ${workerId} 최대 재시작 횟수 초과`);
            }

            this.workers.delete(workerId);
        });

        cluster.on('message', (worker, message) => {
            console.log(`워커 ${worker.process.pid}로부터 메시지:`, message);
            
            if (message.type === 'ready') {
                console.log(`워커 ${worker.process.pid} 준비 완료`);
            }
        });
    }

    updateWorkerStats(workerId, stats) {
        const workerStat = this.workerStats.get(workerId);
        if (workerStat) {
            Object.assign(workerStat, stats);
        }
    }

    handleWorkerRequest(workerId, message) {
        const workerStat = this.workerStats.get(workerId);
        if (workerStat) {
            workerStat.requests++;
            workerStat.connections = message.connections || workerStat.connections;
        }
    }

    startMonitoring() {
        setInterval(() => {
            const activeWorkers = Object.keys(cluster.workers).length;
            const totalMemory = process.memoryUsage();
            
            console.log(`=== 클러스터 상태 ===`);
            console.log(`활성 워커 수: ${activeWorkers}`);
            console.log(`마스터 메모리 사용량: ${Math.round(totalMemory.heapUsed / 1024 / 1024)}MB`);
            console.log(`========================`);
        }, 30000);
    }

    setupGracefulShutdown() {
        const shutdown = (signal) => {
            console.log(`\n${signal} 신호 수신. Graceful shutdown 시작...`);
            
            // 모든 워커에게 종료 신호 전송
            for (const [id, worker] of cluster.workers) {
                console.log(`워커 ${worker.process.pid} 종료 신호 전송`);
                worker.send({ type: 'shutdown' });
            }

            // 일정 시간 후 강제 종료
            setTimeout(() => {
                console.log('강제 종료 실행');
                process.exit(1);
            }, 10000);
        };

        process.on('SIGTERM', () => shutdown('SIGTERM'));
        process.on('SIGINT', () => shutdown('SIGINT'));
    }

    startWorker() {
        const app = express();
        const port = process.env.PORT || 3000;

        // 미들웨어 설정
        app.use(express.json());
        app.use(express.urlencoded({ extended: true }));

        // 로깅 미들웨어
        app.use((req, res, next) => {
            console.log(`[${new Date().toISOString()}] ${req.method} ${req.path} - Worker ${process.pid}`);
            next();
        });

        // 라우트 설정
        app.get('/', (req, res) => {
            res.json({
                message: 'Hello from Cluster!',
                workerId: process.pid,
                connections: connections,
                requests: requests,
                timestamp: new Date().toISOString()
            });
        });

        app.get('/api/data', async (req, res) => {
            try {
                // 비동기 작업 시뮬레이션
                await new Promise(resolve => setTimeout(resolve, 100));
                
                res.json({
                    data: 'Sample data',
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
        const server = app.listen(port, () => {
            console.log(`워커 ${process.pid}가 포트 ${port}에서 실행 중`);
            
            // 마스터에게 준비 완료 신호 전송
            process.send({ type: 'ready', pid: process.pid });
        });

        // 주기적 통계 전송
        setInterval(() => {
            process.send({
                type: 'stats',
                stats: { connections, requests }
            });
        }, 5000);

        // Graceful shutdown
        process.on('message', (message) => {
            if (message.type === 'shutdown') {
                console.log(`워커 ${process.pid} 종료 신호 수신`);
                server.close(() => {
                    console.log(`워커 ${process.pid} 정상 종료`);
                    process.exit(0);
                });
            }
        });

        process.on('SIGTERM', () => {
            console.log(`워커 ${process.pid} SIGTERM 신호 수신`);
            server.close(() => {
                process.exit(0);
            });
        });
    }
}

// 클러스터 매니저 시작
const clusterManager = new ClusterManager();
clusterManager.start();
```

### 고급 Cluster 예제

#### 로드 밸런싱 및 상태 관리
```javascript
const cluster = require('cluster');
const express = require('express');
const os = require('os');

class AdvancedClusterManager {
    constructor() {
        this.numCPUs = os.cpus().length;
        this.workerStats = new Map();
        this.loadBalancer = {
            strategy: 'round-robin', // 'round-robin', 'least-connections', 'weighted'
            currentIndex: 0
        };
    }

    start() {
        if (cluster.isMaster) {
            this.startMaster();
        } else {
            this.startWorker();
        }
    }

    startMaster() {
        console.log(`고급 클러스터 마스터 시작 (PID: ${process.pid})`);

        // 워커 생성
        for (let i = 0; i < this.numCPUs; i++) {
            this.createWorker();
        }

        // 이벤트 리스너 설정
        this.setupMasterEventListeners();

        // 상태 모니터링
        this.startStatusMonitoring();

        // 로드 밸런서 시작
        this.startLoadBalancer();
    }

    createWorker() {
        const worker = cluster.fork();
        
        this.workerStats.set(worker.id, {
            pid: worker.process.pid,
            connections: 0,
            requests: 0,
            startTime: Date.now(),
            status: 'active'
        });

        console.log(`워커 ${worker.process.pid} 생성됨 (ID: ${worker.id})`);
    }

    setupMasterEventListeners() {
        cluster.on('exit', (worker, code, signal) => {
            console.log(`워커 ${worker.process.pid} 종료됨 (코드: ${code}, 시그널: ${signal})`);
            
            // 통계에서 제거
            this.workerStats.delete(worker.id);
            
            // 새로운 워커 생성
            setTimeout(() => {
                this.createWorker();
            }, 1000);
        });

        cluster.on('message', (worker, message) => {
            if (message.type === 'stats') {
                this.updateWorkerStats(worker.id, message.stats);
            } else if (message.type === 'request') {
                this.handleWorkerRequest(worker.id, message);
            }
        });
    }

    updateWorkerStats(workerId, stats) {
        const workerStat = this.workerStats.get(workerId);
        if (workerStat) {
            Object.assign(workerStat, stats);
        }
    }

    handleWorkerRequest(workerId, message) {
        const workerStat = this.workerStats.get(workerId);
        if (workerStat) {
            workerStat.requests++;
            workerStat.connections = message.connections || workerStat.connections;
        }
    }

    startStatusMonitoring() {
        setInterval(() => {
            console.log('\n=== 클러스터 상태 리포트 ===');
            
            for (const [workerId, stats] of this.workerStats) {
                const uptime = Math.floor((Date.now() - stats.startTime) / 1000);
                console.log(`워커 ${stats.pid}: ${stats.requests} 요청, ${stats.connections} 연결, ${uptime}s 실행`);
            }
            
            const totalRequests = Array.from(this.workerStats.values())
                .reduce((sum, stats) => sum + stats.requests, 0);
            
            console.log(`총 요청 수: ${totalRequests}`);
            console.log('=============================\n');
        }, 10000);
    }

    startLoadBalancer() {
        // 로드 밸런서는 실제로는 별도의 프로세스나 서비스로 구현
        console.log('로드 밸런서 시작됨');
    }

    startWorker() {
        const app = express();
        const port = process.env.PORT || 3000;
        let connections = 0;
        let requests = 0;

        // 연결 수 추적
        app.use((req, res, next) => {
            connections++;
            requests++;
            
            res.on('close', () => {
                connections--;
            });
            
            // 주기적으로 마스터에게 통계 전송
            if (requests % 10 === 0) {
                process.send({
                    type: 'stats',
                    stats: { connections, requests }
                });
            }
            
            next();
        });

        // 라우트 설정
        app.get('/', (req, res) => {
            res.json({
                message: 'Advanced Cluster Response',
                workerId: process.pid,
                connections: connections,
                requests: requests,
                timestamp: new Date().toISOString()
            });
        });

        app.get('/api/worker-info', (req, res) => {
            res.json({
                pid: process.pid,
                connections: connections,
                requests: requests,
                uptime: process.uptime(),
                memory: process.memoryUsage()
            });
        });

        app.get('/api/heavy-task', (req, res) => {
            const start = Date.now();
            
            // CPU 집약적인 작업
            let result = 0;
            for (let i = 0; i < 500000; i++) {
                result += Math.sqrt(i);
            }
            
            const duration = Date.now() - start;
            
            res.json({
                result: result,
                duration: duration,
                workerId: process.pid,
                connections: connections
            });
        });

        // 서버 시작
        const server = app.listen(port, () => {
            console.log(`고급 워커 ${process.pid}가 포트 ${port}에서 실행 중`);
        });

        // 주기적 통계 전송
        setInterval(() => {
            process.send({
                type: 'stats',
                stats: { connections, requests }
            });
        }, 5000);

        // Graceful shutdown
        process.on('SIGTERM', () => {
            console.log(`워커 ${process.pid} 종료 신호 수신`);
            server.close(() => {
                console.log(`워커 ${process.pid} 정상 종료`);
                process.exit(0);
            });
        });
    }
}

// 고급 클러스터 매니저 시작
const advancedClusterManager = new AdvancedClusterManager();
advancedClusterManager.start();
```

## 운영 팁

### 성능 최적화

#### Cluster 성능 최적화 기법
```javascript
// 1. 워커 수 최적화
class OptimizedClusterManager {
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
            this.startOptimizedWorker();
        }
    }

    startOptimizedWorker() {
        const app = express();
        
        // 메모리 사용량 모니터링
        setInterval(() => {
            const memUsage = process.memoryUsage();
            if (memUsage.heapUsed > 100 * 1024 * 1024) { // 100MB
                console.warn(`워커 ${process.pid} 메모리 사용량 높음: ${Math.round(memUsage.heapUsed / 1024 / 1024)}MB`);
            }
        }, 30000);

        // 라우트 설정...
        app.get('/', (req, res) => {
            res.json({ workerId: process.pid, optimized: true });
        });
    }
}

// 2. 워커 간 통신 최적화
class InterWorkerCommunication {
    constructor() {
        this.messageQueue = new Map();
    }

    setupWorkerCommunication() {
        if (cluster.isMaster) {
            // 마스터에서 메시지 라우팅
            cluster.on('message', (worker, message) => {
                if (message.targetWorker) {
                    const targetWorker = cluster.workers[message.targetWorker];
                    if (targetWorker) {
                        targetWorker.send(message);
                    }
                }
            });
        } else {
            // 워커에서 메시지 처리
            process.on('message', (message) => {
                this.handleMessage(message);
            });
        }
    }

    handleMessage(message) {
        switch (message.type) {
            case 'cache-update':
                this.updateCache(message.data);
                break;
            case 'config-change':
                this.updateConfig(message.data);
                break;
            case 'health-check':
                this.sendHealthStatus();
                break;
        }
    }

    sendMessage(targetWorker, type, data) {
        process.send({
            targetWorker: targetWorker,
            type: type,
            data: data,
            fromWorker: process.pid
        });
    }
}
```

### 모니터링 및 로깅

#### Cluster 모니터링 시스템
```javascript
class ClusterMonitor {
    constructor() {
        this.metrics = {
            startTime: Date.now(),
            totalRequests: 0,
            totalErrors: 0,
            workerStats: new Map()
        };
    }

    startMonitoring() {
        if (cluster.isMaster) {
            this.startMasterMonitoring();
        } else {
            this.startWorkerMonitoring();
        }
    }

    startMasterMonitoring() {
        // 워커 상태 모니터링
        cluster.on('online', (worker) => {
            console.log(`워커 ${worker.process.pid} 온라인`);
        });

        cluster.on('exit', (worker, code, signal) => {
            console.log(`워커 ${worker.process.pid} 종료 (코드: ${code}, 시그널: ${signal})`);
        });

        // 주기적 상태 리포트
        setInterval(() => {
            this.generateStatusReport();
        }, 30000);
    }

    startWorkerMonitoring() {
        // 요청 수 추적
        let requestCount = 0;
        let errorCount = 0;

        // 미들웨어로 요청 추적
        const trackRequest = (req, res, next) => {
            requestCount++;
            
            res.on('finish', () => {
                if (res.statusCode >= 400) {
                    errorCount++;
                }
            });
            
            next();
        };

        // 주기적으로 마스터에게 통계 전송
        setInterval(() => {
            process.send({
                type: 'metrics',
                data: {
                    pid: process.pid,
                    requests: requestCount,
                    errors: errorCount,
                    memory: process.memoryUsage(),
                    uptime: process.uptime()
                }
            });
        }, 10000);

        return trackRequest;
    }

    generateStatusReport() {
        const uptime = Date.now() - this.metrics.startTime;
        const activeWorkers = Object.keys(cluster.workers).length;
        
        console.log('\n=== 클러스터 상태 리포트 ===');
        console.log(`실행 시간: ${Math.floor(uptime / 1000)}초`);
        console.log(`활성 워커 수: ${activeWorkers}`);
        console.log(`총 요청 수: ${this.metrics.totalRequests}`);
        console.log(`총 오류 수: ${this.metrics.totalErrors}`);
        console.log(`오류율: ${((this.metrics.totalErrors / this.metrics.totalRequests) * 100).toFixed(2)}%`);
        console.log('=============================\n');
    }
}
```

### 오류 처리

#### Cluster 오류 처리 패턴
```javascript
class ClusterErrorHandler {
    constructor() {
        this.errorCounts = new Map();
        this.maxErrors = 10;
        this.errorWindow = 60000; // 1분
    }

    setupErrorHandling() {
        if (cluster.isMaster) {
            this.setupMasterErrorHandling();
        } else {
            this.setupWorkerErrorHandling();
        }
    }

    setupMasterErrorHandling() {
        cluster.on('exit', (worker, code, signal) => {
            const workerId = worker.id;
            const errorCount = this.errorCounts.get(workerId) || 0;
            
            if (code !== 0) {
                this.errorCounts.set(workerId, errorCount + 1);
                console.error(`워커 ${worker.process.pid} 비정상 종료 (코드: ${code})`);
                
                if (errorCount >= this.maxErrors) {
                    console.error(`워커 ${worker.process.pid} 최대 오류 횟수 초과. 재시작 중단.`);
                    return;
                }
            }
            
            // 새로운 워커 생성
            setTimeout(() => {
                const newWorker = cluster.fork();
                console.log(`새 워커 ${newWorker.process.pid} 생성됨`);
            }, 1000);
        });
    }

    setupWorkerErrorHandling() {
        // 처리되지 않은 예외 처리
        process.on('uncaughtException', (error) => {
            console.error(`워커 ${process.pid} 처리되지 않은 예외:`, error);
            
            // 마스터에게 오류 보고
            process.send({
                type: 'error',
                error: error.message,
                stack: error.stack
            });
            
            // Graceful shutdown
            process.exit(1);
        });

        // 처리되지 않은 Promise 거부 처리
        process.on('unhandledRejection', (reason, promise) => {
            console.error(`워커 ${process.pid} 처리되지 않은 Promise 거부:`, reason);
            
            process.send({
                type: 'error',
                error: 'Unhandled Promise Rejection',
                reason: reason
            });
        });

        // 메모리 부족 처리
        process.on('warning', (warning) => {
            if (warning.name === 'MaxListenersExceededWarning') {
                console.warn(`워커 ${process.pid} 이벤트 리스너 수 초과`);
            }
        });
    }
}
```

## 참고

### Cluster vs Worker Threads

#### Cluster와 Worker Threads 비교
```javascript
// Cluster 사용 예시 (프로세스 기반)
const cluster = require('cluster');
const express = require('express');

if (cluster.isMaster) {
    // 마스터 프로세스
    for (let i = 0; i < 4; i++) {
        cluster.fork();
    }
} else {
    // 워커 프로세스
    const app = express();
    app.get('/', (req, res) => {
        res.json({ workerId: process.pid });
    });
    app.listen(3000);
}

// Worker Threads 사용 예시 (스레드 기반)
const { Worker, isMainThread, parentPort } = require('worker_threads');

if (isMainThread) {
    // 메인 스레드
    const worker = new Worker(__filename);
    worker.on('message', (result) => {
        console.log('Worker 결과:', result);
    });
} else {
    // 워커 스레드
    const result = performHeavyCalculation();
    parentPort.postMessage(result);
}
```

### PM2와 함께 사용

#### PM2 Cluster 모드 설정
```javascript
// ecosystem.config.js
module.exports = {
    apps: [{
        name: 'cluster-app',
        script: 'app.js',
        instances: 'max', // CPU 코어 수만큼
        exec_mode: 'cluster',
        watch: false,
        max_memory_restart: '1G',
        env: {
            NODE_ENV: 'development'
        },
        env_production: {
            NODE_ENV: 'production'
        },
        // 클러스터 관련 설정
        kill_timeout: 5000,
        wait_ready: true,
        listen_timeout: 3000,
        max_restarts: 10,
        min_uptime: '10s'
    }]
};
```

### 결론
Cluster는 Node.js에서 멀티코어 CPU를 활용하는 강력한 방법입니다.
적절한 Cluster 설정으로 성능과 고가용성을 동시에 확보할 수 있습니다.
워커 프로세스 관리와 오류 처리를 통해 안정적인 클러스터를 구축해야 합니다.
모니터링과 로깅을 통해 클러스터 상태를 지속적으로 관리해야 합니다.
Cluster와 Worker Threads의 차이점을 이해하여 적절한 상황에 맞는 기술을 선택해야 합니다.

