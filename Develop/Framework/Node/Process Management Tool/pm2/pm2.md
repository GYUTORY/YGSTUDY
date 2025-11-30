---
title: PM2 Node.js
tags: [framework, node, process-management-tool, pm2, nodejs]
updated: 2025-11-30
---
# PM2와 Node.js

## 배경
- [주요 특징](#주요-특징)
- [설치 및 기본 사용법](#설치-및-기본-사용법)
- [클러스터 모드](#클러스터-모드)
- [무중단 배포](#무중단-배포)
- [로그 관리](#로그-관리)
- [모니터링 및 대시보드](#모니터링-및-대시보드)
- [환경 변수 및 설정 관리](#환경-변수-및-설정-관리)
- [고급 기능](#고급-기능)
- [문제 해결 및 디버깅](#문제-해결-및-디버깅)
- [프로덕션 환경 설정](#프로덕션-환경-설정)
- [PM2와 Docker 통합](#pm2와-docker-통합)
- [모범 사례](#모범-사례)
- [명령어 요약](#명령어-요약)

---


| 특징 | 설명 |
|------|------|
| 🔄 **무중단 서비스** | 클러스터 모드로 여러 CPU 코어에 분산 실행 |
| 🔁 **자동 재시작** | 비정상 종료 시 자동 재시작 |
| ⚖️ **로드 밸런싱** | 여러 코어에 작업 분배로 성능 최적화 |
| 📝 **로그 관리** | 중앙 집중식 로그 관리 및 파일 저장 |
| 📊 **모니터링** | 웹 대시보드 및 CLI를 통한 실시간 모니터링 |
| 🚀 **무중단 배포** | 서비스 중단 없이 애플리케이션 업데이트 |
| 🌍 **환경 변수 관리** | 개발/스테이징/프로덕션 환경별 설정 관리 |
| 💾 **리소스 모니터링** | 메모리 및 CPU 사용량 실시간 추적 |
| ⏰ **스케줄링** | cron 작업을 통한 자동화된 작업 실행 |

---


### PM2 설치

```bash

npm install -g pm2

pm2 --version
```

### 시스템 서비스로 등록

```bash


```bash

pm2 save

pm2 unstartup
```

### 애플리케이션 실행

#### 1. 간단한 서버 생성

```javascript:app.js
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello, PM2!');
});

server.listen(3000, () => {
  console.log('Server running at http://localhost:3000/');
});
```

#### 2. PM2로 애플리케이션 실행

```bash


#### 1. 간단한 서버 생성

```javascript:app.js
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello, PM2!');
});

server.listen(3000, () => {
  console.log('Server running at http://localhost:3000/');
});
```

#### 2. PM2로 애플리케이션 실행

```bash

pm2 start app.js

pm2 start app.js --name "my-app"

pm2 start app.js --name "my-app" -- --port 3000

pm2 start app.js --name "my-app" --env production
```

### 기본 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 실행 중인 프로세스 목록 확인 |
| `pm2 show app-name` | 특정 프로세스 정보 확인 |
| `pm2 restart app-name` | 프로세스 재시작 |
| `pm2 stop app-name` | 프로세스 중지 |
| `pm2 delete app-name` | 프로세스 삭제 |
| `pm2 pause app-name` | 프로세스 일시정지 |
| `pm2 resume app-name` | 프로세스 재개 |
| `pm2 kill` | 프로세스 강제 종료 |

---


```bash


```bash

pm2 save

pm2 unstartup
```


#### 1. 간단한 서버 생성

```javascript:app.js
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello, PM2!');
});

server.listen(3000, () => {
  console.log('Server running at http://localhost:3000/');
});
```

#### 2. PM2로 애플리케이션 실행

```bash


#### 1. 간단한 서버 생성

```javascript:app.js
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello, PM2!');
});

server.listen(3000, () => {
  console.log('Server running at http://localhost:3000/');
});
```

#### 2. PM2로 애플리케이션 실행

```bash

pm2 start app.js

pm2 start app.js --name "my-app"

pm2 start app.js --name "my-app" -- --port 3000

pm2 start app.js --name "my-app" --env production
```


| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 실행 중인 프로세스 목록 확인 |
| `pm2 show app-name` | 특정 프로세스 정보 확인 |
| `pm2 restart app-name` | 프로세스 재시작 |
| `pm2 stop app-name` | 프로세스 중지 |
| `pm2 delete app-name` | 프로세스 삭제 |
| `pm2 pause app-name` | 프로세스 일시정지 |
| `pm2 resume app-name` | 프로세스 재개 |
| `pm2 kill` | 프로세스 강제 종료 |

---


PM2는 클러스터 모드를 통해 멀티코어 환경에서 애플리케이션 성능을 극대화할 수 있습니다.

### 클러스터 모드 실행 방법

```bash


| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 실행 중인 프로세스 목록 확인 |
| `pm2 show app-name` | 특정 프로세스 정보 확인 |
| `pm2 restart app-name` | 프로세스 재시작 |
| `pm2 stop app-name` | 프로세스 중지 |
| `pm2 delete app-name` | 프로세스 삭제 |
| `pm2 pause app-name` | 프로세스 일시정지 |
| `pm2 resume app-name` | 프로세스 재개 |
| `pm2 kill` | 프로세스 강제 종료 |

---


PM2는 클러스터 모드를 통해 멀티코어 환경에서 애플리케이션 성능을 극대화할 수 있습니다.

### 클러스터 모드 실행 방법

```bash


```bash

pm2 start app.js -i 4


```javascript
// 클러스터 모드에서 프로세스 ID 확인
const cluster = require('cluster');

if (cluster.isMaster) {
  console.log('Master process is running');
} else {
  console.log(`Worker process ${process.pid} is running`);
}
```


```bash

pm2 scale app-name 4

pm2 reload app-name

pm2 stop app-name
```

---


```bash


| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 실행 중인 프로세스 목록 확인 |
| `pm2 show app-name` | 특정 프로세스 정보 확인 |
| `pm2 restart app-name` | 프로세스 재시작 |
| `pm2 stop app-name` | 프로세스 중지 |
| `pm2 delete app-name` | 프로세스 삭제 |
| `pm2 pause app-name` | 프로세스 일시정지 |
| `pm2 resume app-name` | 프로세스 재개 |
| `pm2 kill` | 프로세스 강제 종료 |

---


PM2는 클러스터 모드를 통해 멀티코어 환경에서 애플리케이션 성능을 극대화할 수 있습니다.


```bash


```bash

pm2 start app.js -i 4


```javascript
// 클러스터 모드에서 프로세스 ID 확인
const cluster = require('cluster');

if (cluster.isMaster) {
  console.log('Master process is running');
} else {
  console.log(`Worker process ${process.pid} is running`);
}
```


```bash

pm2 scale app-name 4

pm2 reload app-name

pm2 stop app-name
```

---


```bash


```bash


1. **순차적 재시작**: PM2는 한 번에 하나씩 워커 프로세스를 재시작
2. **로드 밸런싱**: 활성 상태인 다른 워커들이 요청을 처리
3. **헬스 체크**: 새로운 워커가 정상적으로 시작되면 다음 워커를 재시작
4. **완료**: 모든 워커가 새로운 코드로 업데이트


```bash

pm2 reload app-name

pm2 restart app-name

pm2 restart app-name --only 0
```

---


PM2는 로그 파일을 자동으로 생성하고 관리합니다.

### 로그 확인 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |

### 로그 파일 위치

```bash


PM2는 로그 파일을 자동으로 생성하고 관리합니다.

### 로그 확인 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |

### 로그 파일 위치

```bash


| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |


```bash


```bash

pm2 start app.js --max-memory-restart 300M --log-date-format "YYYY-MM-DD HH:mm:ss"

pm2 install pm2-logrotate
```

### 커스텀 로그 설정

```javascript
// app.js에서 로그 설정
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}
```

---


| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |


```bash


PM2는 로그 파일을 자동으로 생성하고 관리합니다.


| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |


```bash


| 명령어 | 설명 |
|--------|------|
| `pm2 logs` | 모든 로그 확인 |
| `pm2 logs app-name` | 특정 앱의 로그 확인 |
| `pm2 logs --follow` | 실시간 로그 스트리밍 |
| `pm2 logs --lines 100` | 로그 라인 수 제한 |
| `pm2 logs --err` | 에러 로그만 확인 |
| `pm2 logs --out` | 출력 로그만 확인 |


```bash


```bash

pm2 start app.js --max-memory-restart 300M --log-date-format "YYYY-MM-DD HH:mm:ss"

pm2 install pm2-logrotate
```


```javascript
// app.js에서 로그 설정
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}
```

---


### CLI 모니터링

```bash


```javascript
// app.js에서 로그 설정
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}
```

---


### CLI 모니터링

```bash

pm2 monit

pm2 status

pm2 show app-name
```

### 웹 대시보드

```bash


```bash


```bash

pm2 metrics

pm2 reset app-name
```

---


```bash


```bash


```bash

pm2 metrics

pm2 reset app-name
```

---


### 환경별 설정

```bash


### 환경별 설정

```bash


```bash

pm2 start app.js --env development

pm2 start app.js --env production

pm2 start app.js --env staging
```

### ecosystem.config.js 파일 사용

```javascript:ecosystem.config.js
module.exports = {
  apps: [{
    name: 'my-app',
    script: 'app.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'development',
      PORT: 3000
    },
    env_production: {
      NODE_ENV: 'production',
      PORT: 8080
    },
    env_staging: {
      NODE_ENV: 'staging',
      PORT: 5000
    }
  }]
};
```

### ecosystem 파일 사용

```bash

pm2 start ecosystem.config.js --env production


### 메모리 및 CPU 제한

```bash

pm2 start app.js --max-memory-restart 300M

pm2 start app.js --max-memory-restart 300M --min-uptime 10000
```

### 스케줄링 (Cron Jobs)

```bash

pm2 start backup.js --cron "0 0 * * *" --name "daily-backup"
```

### 헬스 체크

```javascript
// app.js에서 헬스 체크 엔드포인트
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage()
  });
});
```

### PM2 플러그인

```bash


```javascript
// app.js에서 헬스 체크 엔드포인트
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage()
  });
});
```

pm2 install pm2-logrotate
pm2 install pm2-server-monit

pm2 plugin list

pm2 uninstall pm2-logrotate
```

---


```bash



```bash


```bash

pm2 start app.js --env development

pm2 start app.js --env production

pm2 start app.js --env staging
```


```javascript
// app.js에서 헬스 체크 엔드포인트
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage()
  });
});
```


### 일반적인 문제들

#### 1. 포트 충돌
```bash


### 일반적인 문제들

#### 1. 포트 충돌
```bash


#### 1. 포트 충돌
```bash

lsof -i :3000

pm2 start app.js -- --port 3001
```

#### 2. 권한 문제
```bash

sudo pm2 startup
```

#### 3. 메모리 누수
```bash

pm2 monit

pm2 start app.js --max-memory-restart 500M
```

### 디버깅 명령어

```bash


```bash

pm2 logs --lines 200

pm2 show app-name


### 보안 설정

```bash


```bash


```javascript:ecosystem.config.js
// 프로덕션 최적화 설정
module.exports = {
  apps: [{
    name: 'production-app',
    script: 'app.js',
    instances: 'max',
    exec_mode: 'cluster',
    max_memory_restart: '1G',
    node_args: '--max-old-space-size=1024',
    env_production: {
      NODE_ENV: 'production',
      PORT: 8080
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    min_uptime: '10s',
    max_restarts: 10,
    autorestart: true,
    watch: false,
    ignore_watch: ['node_modules', 'logs'],
    source_map_support: true
  }]
};
```


```bash

pm2 install pm2-server-monit

pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 30
```

---


#### 1. 포트 충돌
```bash



#### 1. 포트 충돌
```bash


#### 1. 포트 충돌
```bash

lsof -i :3000

pm2 start app.js -- --port 3001
```

#### 2. 권한 문제
```bash

sudo pm2 startup
```

#### 3. 메모리 누수
```bash

pm2 monit

pm2 start app.js --max-memory-restart 500M
```


```bash


```bash

pm2 logs --lines 200

pm2 show app-name



```bash


```bash


```javascript:ecosystem.config.js
// 프로덕션 최적화 설정
module.exports = {
  apps: [{
    name: 'production-app',
    script: 'app.js',
    instances: 'max',
    exec_mode: 'cluster',
    max_memory_restart: '1G',
    node_args: '--max-old-space-size=1024',
    env_production: {
      NODE_ENV: 'production',
      PORT: 8080
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    min_uptime: '10s',
    max_restarts: 10,
    autorestart: true,
    watch: false,
    ignore_watch: ['node_modules', 'logs'],
    source_map_support: true
  }]
};
```


```bash

pm2 install pm2-server-monit

pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 30
```

---


### 기본 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |

### 고급 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---


| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |


| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---







### 기본 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |

### 고급 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---


| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |


| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---






> PM2(Process Manager 2)는 Node.js 애플리케이션을 위한 프로덕션 프로세스 관리 도구입니다.


| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |


| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---


| 명령어 | 설명 |
|--------|------|
| `pm2 start app.js` | 애플리케이션 시작 |
| `pm2 stop app-name` | 애플리케이션 중지 |
| `pm2 restart app-name` | 애플리케이션 재시작 |
| `pm2 reload app-name` | 무중단 재시작 |
| `pm2 delete app-name` | 애플리케이션 삭제 |
| `pm2 list` | 실행 중인 프로세스 목록 |
| `pm2 show app-name` | 프로세스 상세 정보 |
| `pm2 logs` | 로그 확인 |
| `pm2 monit` | 모니터링 대시보드 |


| 명령어 | 설명 |
|--------|------|
| `pm2 scale app-name 4` | 클러스터 크기 조정 |
| `pm2 startup` | 시스템 서비스 등록 |
| `pm2 save` | 현재 상태 저장 |
| `pm2 resurrect` | 저장된 상태 복구 |
| `pm2 update` | PM2 업데이트 |
| `pm2 kill` | 모든 프로세스 종료 |
| `pm2 ping` | PM2 상태 확인 |
| `pm2 plus` | PM2 Plus 대시보드 |

---






> PM2(Process Manager 2)는 Node.js 애플리케이션을 위한 프로덕션 프로세스 관리 도구입니다.





## 무중단 배포 (Zero Downtime Deployment)

PM2는 `reload` 명령을 통해 애플리케이션을 중단 없이 재배포할 수 있습니다.

## 🐳 PM2와 Docker 통합

### Dockerfile 예시

```dockerfile:Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000


### 1. 애플리케이션 구조
```
project/
├── app.js
├── ecosystem.config.js
├── package.json
├── logs/
└── .env
```

### 2. 환경 변수 관리
```bash

mkdir -p logs

chmod 755 logs
```

### 4. 백업 및 복구
```bash

pm2 resurrect
```

---

# 또는 yarn 사용
yarn global add pm2

# PM2를 시스템 서비스로 등록
pm2 startup

# 모든 CPU 코어 사용
pm2 start app.js -i max

# CPU 코어 수만큼 실행
pm2 start app.js -i 0

# 클러스터 모드로 실행 (기본값: 1개 인스턴스)
pm2 start app.js -i cluster
```

# 1. 배포 준비: 기존 애플리케이션 실행
pm2 start app.js -i max --name "my-app"

# 2. 코드 업데이트 후 재배포
pm2 reload my-app

# 3. 배포 상태 확인
pm2 show my-app
```

# Linux/Mac
~/.pm2/logs/

# Windows
%USERPROFILE%\.pm2\logs\
```

# PM2 Plus 대시보드 실행
pm2 plus

# 로컬 웹 대시보드 (PM2 Plus 필요)
pm2 web
```

# ecosystem 파일로 실행
pm2 start ecosystem.config.js

# ecosystem 파일로 재시작
pm2 restart ecosystem.config.js
```

---

# CPU 사용률 제한
pm2 start app.js --max-cpu-percent 80

# cron 작업 추가
pm2 start cron.js --cron "0 0 * * *"

# PM2 권한 확인
sudo chown -R $USER:$USER ~/.pm2

# PM2 상태 확인
pm2 ping

# PM2 버전 확인
pm2 --version
```

### PM2 초기화

```bash
# PM2 완전 초기화
pm2 kill
pm2 cleardump
rm -rf ~/.pm2
```

---

# PM2 키 생성
pm2 key

# PM2 Plus 연결
pm2 link <secret_key> <public_key>
```

# PM2 설치 및 실행
RUN npm install -g pm2
CMD ["pm2-runtime", "start", "ecosystem.config.js", "--env", "production"]
```

### Docker Compose 예시

```yaml:docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

---

# .env 파일 사용
pm2 start ecosystem.config.js --env production
```

### 3. 로그 관리
```bash
# PM2 설정 백업
pm2 save

