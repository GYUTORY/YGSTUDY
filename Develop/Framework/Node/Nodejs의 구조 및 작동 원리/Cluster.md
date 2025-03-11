# 서버를 클러스터로 분산 처리하는 방법 🚀

## 1. Node.js에서 클러스터란? 🤔

**클러스터(Cluster)**는 **Node.js가 싱글 스레드(Single Thread) 기반이라는 한계를 극복하기 위해 여러 개의 프로세스를 활용하여 부하를 분산시키는 방식**입니다.  
이를 통해 **CPU의 모든 코어를 활용**하여 **고성능 서버 운영이 가능**해집니다.

> **✨ 클러스터의 주요 특징**
> - 기본적으로 **싱글 스레드 기반이지만, 멀티코어 활용 가능**
> - **Worker 프로세스**를 여러 개 생성하여 요청을 분산 처리
> - **마스터 프로세스**가 Worker 프로세스를 관리하고 조정
> - Worker 프로세스가 다운되면 자동으로 재시작하여 **고가용성 유지**
> - **Node.js 내장 모듈인 `cluster`를 활용하여 쉽게 구현 가능**

✅ **즉, 클러스터를 사용하면 하나의 Node.js 서버에서 여러 개의 프로세스를 실행하여 부하를 분산할 수 있습니다.**

---

## 2. Node.js에서 클러스터로 서버 실행하는 방법

### 2.1 `cluster` 모듈을 사용한 기본 클러스터 처리

✔ **`cluster` 모듈을 활용하여 마스터(관리) 프로세스와 워커(실행) 프로세스를 생성**  
✔ **CPU 코어 개수만큼 워커 프로세스를 생성하여 성능 최적화**  
✔ **워커 프로세스가 종료되면 자동으로 재시작**

#### ✅ 기본 클러스터 예제
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

📌 **실행 결과:**
```
마스터 프로세스 12345 실행 중
워커 프로세스 12346 실행 중
워커 프로세스 12347 실행 중
...
```  

> **📌 클러스터를 사용하면 각 요청이 여러 개의 워커 프로세스로 분산 처리됨!**

---

## 3. Express에서 클러스터 활용하기

✔ Express 애플리케이션도 **클러스터를 활용하여 부하를 분산 가능**  
✔ 클러스터를 활용하면 **다중 요청 처리 성능을 향상**시킬 수 있음

#### ✅ Express 클러스터 예제
```javascript
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;
const express = require('express');

if (cluster.isMaster) {
    console.log(`마스터 프로세스 ${process.pid} 실행 중`);

    // CPU 코어 개수만큼 워커 프로세스 생성
    for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
    }

    // 워커 종료 시 다시 생성
    cluster.on('exit', (worker, code, signal) => {
        console.log(`워커 ${worker.process.pid} 종료됨`);
        cluster.fork();
    });
} else {
    // Express 서버 실행 (워커 프로세스에서 실행됨)
    const app = express();

    app.get('/', (req, res) => {
        res.send('Hello, Express with Cluster!');
    });

    app.listen(3000, () => {
        console.log(`워커 ${process.pid}에서 Express 서버 실행 중`);
    });
}
```  

> **📌 여러 개의 워커 프로세스가 동일한 Express 서버를 실행하여 요청을 분산 처리!**

---

## 4. PM2를 활용한 클러스터 모드 실행

Node.js의 `cluster` 모듈을 직접 사용하는 것도 가능하지만, **PM2(Process Manager 2)를 활용하면 더욱 쉽게 클러스터를 운영할 수 있습니다.**

### 4.1 PM2 설치
```sh
npm install pm2 -g
```

### 4.2 애플리케이션 폴더로 이동
```sh
cd /path/to/your/app
```

### 4.3 PM2 설정 파일 생성 및 편집

📌 **`pm2.config.js` 생성:**
```javascript
module.exports = {
    apps: [{
        name: "my-app",        // 애플리케이션 이름
        script: "server.js",   // 실행할 파일
        instances: "max",      // CPU 개수만큼 워커 생성 (또는 직접 숫자 지정 가능)
        exec_mode: "cluster"   // 클러스터 모드 활성화
    }]
};
```

### 4.4 PM2로 애플리케이션 실행
```sh
pm2 start pm2.config.js
```  

📌 **출력 결과:**
```
[PM2] Starting server.js in cluster mode (instances: max)
[PM2] Started my-app with process ID 1001, 1002, 1003, ...
```  

> **📌 PM2는 자동으로 클러스터를 관리하며, 장애 발생 시 자동 복구 기능도 제공!**

---

## 5. PM2 클러스터 관리 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 실행 중인 애플리케이션 목록 확인 |
| `pm2 status` | 프로세스 상태 확인 |
| `pm2 logs` | 로그 확인 |
| `pm2 restart my-app` | 애플리케이션 재시작 |
| `pm2 stop my-app` | 애플리케이션 중지 |
| `pm2 delete my-app` | 애플리케이션 삭제 |
| `pm2 scale my-app 4` | 4개의 인스턴스로 확장 |

✅ **PM2를 사용하면 클러스터 기반의 Node.js 서버를 쉽고 안정적으로 운영 가능!**

---

## 📌 결론

- **Node.js의 기본 실행 방식은 싱글 스레드이지만, `cluster` 모듈을 활용하면 멀티코어를 활용하여 성능을 최적화할 수 있음**
- **CPU 코어 개수만큼 워커 프로세스를 실행하여 요청을 병렬로 처리 가능**
- **Express 서버에서도 클러스터 기능을 적용하여 고성능 API 서버 운영 가능**
- **PM2를 활용하면 클러스터 관리를 더욱 쉽게 할 수 있으며, 자동 복구 및 확장 기능을 제공**

> **👉🏻 클러스터를 활용하면 대규모 트래픽을 처리할 수 있는 강력한 Node.js 서버를 구축할 수 있음!**  

