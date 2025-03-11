# Cluster와 Multi-Thread의 차이 🚀

## 1. Node.js에서 Cluster와 Multi-Thread란? 🤔

Node.js는 기본적으로 **싱글 스레드 기반**으로 동작하지만,  
멀티코어 CPU를 활용하기 위해 **Cluster와 Worker Threads** 두 가지 방법을 사용할 수 있습니다.

> **✨ 핵심 차이점**
> - **Cluster** → **여러 개의 프로세스를 생성하여 요청을 병렬 처리**
> - **Multi-Thread** → **싱글 프로세스 내에서 여러 개의 스레드를 생성하여 병렬 연산 처리**

✅ **즉, Cluster는 다중 프로세스를 활용하여 여러 개의 Node.js 인스턴스를 실행하는 방식이고, Multi-Thread는 하나의 프로세스 내에서 병렬 처리를 수행하는 방식입니다.**

---

## 2. Cluster와 Multi-Thread의 비교 🔄

| 비교 항목 | Cluster (클러스터) | Multi-Thread (멀티 스레드) |
|-----------|-----------------|-----------------|
| **기본 개념** | 여러 개의 프로세스를 생성하여 부하를 분산 | 하나의 프로세스 내에서 여러 개의 스레드 실행 |
| **사용 목적** | 웹 서버의 요청 분산 처리 | CPU 집중적인 작업 (암호화, 데이터 처리 등) |
| **멀티코어 활용** | O (각 프로세스가 개별 CPU 코어 사용) | O (스레드가 병렬 연산 가능) |
| **비동기 지원** | O (각 프로세스가 독립적으로 실행) | X (각 스레드는 프로세스 내에서 실행) |
| **메모리 공유** | X (각 프로세스는 독립적인 메모리 공간 사용) | O (스레드는 동일한 메모리 공간 공유) |
| **성능 최적화** | 다수의 요청을 병렬 처리할 때 유리 | CPU 연산이 많은 작업에서 유리 |
| **대표적인 활용 예제** | HTTP 서버 부하 분산 | 이미지 처리, 대규모 데이터 연산 |

✅ **Cluster는 요청을 여러 프로세스로 나누어 처리하고, Multi-Thread는 하나의 프로세스 내에서 여러 스레드를 실행하여 병렬 연산을 수행합니다.**

---

## 3. Cluster (클러스터) 활용 예제

✔ **Node.js의 `cluster` 모듈을 활용하여 다중 프로세스를 실행**  
✔ **각 프로세스는 독립적인 메모리를 가지고 있으며, 요청을 나누어 처리**  
✔ **CPU 코어 개수만큼 워커 프로세스를 생성하여 서버 성능 최적화**

#### ✅ 기본적인 Cluster 예제
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

📌 **실행 결과:**
```
마스터 프로세스 실행 (PID: 12345)
워커 프로세스 실행 (PID: 12346)
워커 프로세스 실행 (PID: 12347)
...
```  

> **📌 클러스터를 사용하면 여러 개의 프로세스를 생성하여 서버 부하를 분산할 수 있음!**

---

## 4. Worker Threads (멀티 스레드) 활용 예제

✔ **Node.js의 `worker_threads` 모듈을 사용하여 멀티스레딩 구현 가능**  
✔ **싱글 프로세스 내에서 여러 개의 스레드를 실행하여 연산을 분산**  
✔ **CPU 집중적인 작업을 처리할 때 효과적**

#### ✅ 기본적인 Worker Threads 예제

📌 **`main.js` (메인 스레드)**
```javascript
const { Worker } = require('worker_threads');

console.log("메인 스레드 시작");

const worker = new Worker('./worker.js'); // Worker 스레드 실행

worker.on('message', (msg) => console.log("워커에서 받은 메시지:", msg));
worker.postMessage("작업 시작");
```  

📌 **`worker.js` (Worker 스레드)**
```javascript
const { parentPort } = require('worker_threads');

parentPort.on('message', (msg) => {
    console.log("메인 스레드로부터 메시지:", msg);
    parentPort.postMessage("작업 완료!");
});
```  

📌 **실행 결과:**
```
메인 스레드 시작
메인 스레드로부터 메시지: 작업 시작
워커에서 받은 메시지: 작업 완료!
```  

> **📌 Worker Threads를 사용하면 CPU 집중적인 작업을 백그라운드에서 실행할 수 있음!**

---

## 5. 언제 Cluster와 Multi-Thread를 사용해야 할까? 🤔

| 사용해야 하는 경우 | Cluster 사용 | Worker Threads 사용 |
|-----------------|-------------|-----------------|
| **웹 서버 부하 분산** | ✅ | ❌ |
| **CPU 연산이 많은 작업** | ❌ | ✅ |
| **네트워크 요청 처리** | ✅ | ❌ |
| **이미지 처리, 데이터 분석** | ❌ | ✅ |
| **메모리를 개별적으로 할당해야 하는 경우** | ✅ | ❌ |
| **공유 메모리를 활용해야 하는 경우** | ❌ | ✅ |

✅ **즉, HTTP 요청과 같은 서버 트래픽을 처리할 때는 Cluster를 사용하고, CPU 연산이 많은 작업을 처리할 때는 Worker Threads를 사용하면 됩니다.**

---

## 📌 결론

- **Cluster** → 여러 개의 프로세스를 생성하여 서버 부하를 분산 (각 프로세스는 독립적인 메모리 사용)
- **Multi-Thread (Worker Threads)** → 하나의 프로세스 내에서 여러 개의 스레드를 생성하여 병렬 연산 처리 (메모리 공유 가능)
- **Cluster는 웹 서버의 부하를 분산하는 데 적합**하며, **Multi-Thread는 CPU 연산이 많은 작업을 처리하는 데 적합**
- **둘 다 Node.js에서 성능을 최적화하는 중요한 기술이며, 상황에 맞게 적절히 활용해야 함**

> **👉🏻 클러스터는 여러 개의 프로세스를 실행하여 요청을 병렬로 처리하고, 멀티 스레드는 하나의 프로세스 내에서 병렬 연산을 수행하는 방식입니다.**  

