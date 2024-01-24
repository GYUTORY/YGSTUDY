
### Nodejs에서 서버 실행을 클러스터로 분산 처리하는 방법

1. cluster 모듈 로드
- Node.js에는 내장된 cluster 모듈이 있어 클러스터 기능을 활용할 수 있습니다. 
- 이 모듈을 사용하여 서버를 분산 처리할 수 있습니다.

2. 마스터 프로세스 생성
- 클러스터 기능을 사용하기 위해 먼저 마스터 프로세스를 생성해야 합니다.
- 마스터 프로세스는 워커 프로세스를 관리하고 분산 처리를 조정하는 역할을 담당합니다.

3. 워커 프로세스 생성
- 마스터 프로세스에서 워커 프로세스를 생성합니다. 
- 워커 프로세스는 실제 서버 요청을 처리하는 개별 프로세스입니다. 
- 일반적으로 CPU 코어의 수에 따라 여러 개의 워커 프로세스를 생성합니다.

4. 포트 공유
- 각 워커 프로세스가 동일한 포트를 사용할 수 있도록 포트 공유를 설정합니다. 
- 이를 통해 클라이언트 요청이 여러 워커 프로세스로 분산되어 처리될 수 있습니다.


5. 요청 분배
- 마스터 프로세스는 들어오는 요청을 워커 프로세스로 분배합니다. 
- 이는 Round-robin 방식으로 처리되어 각 워커 프로세스가 균등하게 요청을 처리할 수 있습니다.

6. 고가용성 처리
- 워커 프로세스가 종료되거나 다운될 경우, 마스터 프로세스는 해당 프로세스를 다시 생성하여 고가용성을 유지합니다.


## 예제 코드
```typescript
const cluster = require('cluster');
const http = require('http');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
    // 마스터 프로세스 생성
    for (let i = 0; i < numCPUs; i++) {
    cluster.fork(); // 워커 프로세스 생성
    }
} else {
    // 실제 서버 로직을 담당하는 워커 프로세스
    http.createServer((req, res) => {
    res.writeHead(200);
    res.end('Hello, World!');
    }).listen(3000);
}

// 워커 프로세스 종료 시 이벤트 처리
cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died`);
    cluster.fork(); // 다시 워커 프로세스 생성
});
```

## express에서 클러스터 처리 하는 방법
```typescript
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;
const express = require('express');

if (cluster.isMaster) {
// 마스터 프로세스 생성
for (let i = 0; i < numCPUs; i++) {
cluster.fork(); // 워커 프로세스 생성
}
} else {
// Express 애플리케이션 로직
const app = express();

app.get('/', (req, res) => {
res.send('Hello, World!');
});

app.listen(3000, () => {
console.log('Server is running');
});
}

// 워커 프로세스 종료 시 이벤트 처리
cluster.on('exit', (worker, code, signal) => {
console.log(`Worker ${worker.process.pid} died`);
cluster.fork(); // 다시 워커 프로세스 생성
});


```
