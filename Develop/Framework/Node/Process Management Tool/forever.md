---
title: Node.js Forever 프로세스 관리 도구
tags: [framework, node, process-management-tool, forever, nodejs, process-manager]
updated: 2025-08-10
---

# Node.js Forever 프로세스 관리 도구

## 배경

**Forever**는 Node.js 애플리케이션을 백그라운드에서 지속적으로 실행하고 관리하는 명령줄 도구입니다. 애플리케이션이 예기치 않게 종료되더라도 자동으로 재시작하여 안정적인 서비스를 제공할 수 있도록 도와줍니다.

### Forever의 필요성
- **프로덕션 안정성**: 애플리케이션 크래시 시 자동 복구
- **백그라운드 실행**: 터미널 종료 후에도 계속 실행
- **간단한 설정**: 복잡한 설정 없이 빠른 프로세스 관리
- **로그 관리**: 애플리케이션 로그 수집 및 관리

### Forever의 주요 기능
- **자동 재시작**: 애플리케이션 크래시 시 자동 복구
- **백그라운드 실행**: 터미널 종료 후에도 계속 실행
- **프로세스 모니터링**: 실행 상태 실시간 감시
- **로그 관리**: 애플리케이션 로그 수집 및 관리
- **다중 프로세스 관리**: 여러 애플리케이션 동시 관리

## 핵심

### Forever 설치 및 기본 설정

#### 전역 설치
```bash
npm install -g forever
```

#### 버전 확인
```bash
forever --version
```

### 기본 애플리케이션 실행

#### 애플리케이션 시작
```bash
# 기본 시작
forever start app.js

# 포트 지정하여 시작
forever start app.js --port 3000

# 환경 변수와 함께 시작
forever start app.js --env production
```

#### 프로세스 관리
```bash
# 실행 중인 프로세스 목록 확인
forever list

# 특정 프로세스 재시작 (인덱스 또는 파일명으로)
forever restart 0
forever restart app.js

# 특정 프로세스 중지
forever stop 0
forever stop app.js

# 모든 프로세스 중지
forever stopall
```

#### 로그 관리
```bash
# 모든 로그 확인
forever logs

# 특정 프로세스 로그 확인
forever logs 0

# 일반 텍스트 형식으로 로그 확인
forever logs --plain
```

## 예시

### Express 애플리케이션 Forever 설정

#### Express 서버 생성
```javascript
// server.js
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

// 미들웨어 설정
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 라우트 설정
app.get('/', (req, res) => {
    res.json({
        message: 'Hello from Forever!',
        timestamp: new Date().toISOString(),
        processId: process.pid,
        uptime: process.uptime()
    });
});

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        memory: process.memoryUsage(),
        cpu: process.cpuUsage()
    });
});

// 에러 핸들링
app.use((err, req, res, next) => {
    console.error('Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
```

#### Forever로 서버 실행
```bash
# 개발 환경에서 실행
forever start server.js

# 프로덕션 환경에서 실행
forever start server.js --env production

# 로그 파일 지정하여 실행
forever start -o logs/out.log -e logs/err.log server.js

# 이름 지정하여 실행
forever start --uid "my-app" server.js
```

#### Forever 설정 파일 사용
```javascript
// forever.json
{
    "uid": "my-app",
    "append": true,
    "watch": false,
    "script": "server.js",
    "sourceDir": "/path/to/app",
    "logFile": "/path/to/logs/forever.log",
    "outFile": "/path/to/logs/out.log",
    "errFile": "/path/to/logs/err.log",
    "env": {
        "NODE_ENV": "production",
        "PORT": 3000
    }
}
```

```bash
# 설정 파일로 실행
forever start forever.json
```

### 고급 Forever 설정

#### 다중 애플리케이션 관리
```bash
# API 서버 시작
forever start --uid "api-server" api/server.js

# 워커 프로세스 시작
forever start --uid "worker" worker/processor.js

# 스케줄러 시작
forever start --uid "scheduler" scheduler/cron.js

# 모든 프로세스 목록 확인
forever list
```

#### 로그 관리 설정
```bash
# 로그 파일 지정하여 실행
forever start -o logs/app-out.log -e logs/app-err.log app.js

# 로그 크기 제한 설정
forever start --max-old-space-size=1024 app.js

# 로그 레벨 설정
forever start --env production app.js
```

#### 환경별 설정
```bash
# 개발 환경
forever start --env development app.js

# 스테이징 환경
forever start --env staging app.js

# 프로덕션 환경
forever start --env production app.js
```

## 운영 팁

### 성능 최적화

#### 메모리 및 CPU 모니터링
```javascript
// monitoring.js
const fs = require('fs');
const path = require('path');

class ForeverMonitor {
    constructor() {
        this.logDir = './logs';
        this.metrics = [];
    }

    // 메모리 사용량 모니터링
    monitorMemory() {
        const used = process.memoryUsage();
        
        const metric = {
            timestamp: new Date().toISOString(),
            memory: {
                rss: Math.round(used.rss / 1024 / 1024),
                heapTotal: Math.round(used.heapTotal / 1024 / 1024),
                heapUsed: Math.round(used.heapUsed / 1024 / 1024),
                external: Math.round(used.external / 1024 / 1024)
            },
            cpu: process.cpuUsage(),
            uptime: process.uptime()
        };

        this.metrics.push(metric);
        
        // 최근 100개 메트릭만 유지
        if (this.metrics.length > 100) {
            this.metrics.shift();
        }

        // 로그 파일에 기록
        this.writeMetricToLog(metric);
        
        return metric;
    }

    // 메트릭을 로그 파일에 기록
    writeMetricToLog(metric) {
        const logFile = path.join(this.logDir, 'metrics.log');
        const logEntry = JSON.stringify(metric) + '\n';
        
        fs.appendFileSync(logFile, logEntry);
    }

    // 메트릭 리포트 생성
    generateReport() {
        if (this.metrics.length === 0) {
            return { message: '메트릭 데이터가 없습니다.' };
        }

        const latest = this.metrics[this.metrics.length - 1];
        const avgMemory = this.metrics.reduce((sum, m) => sum + m.memory.heapUsed, 0) / this.metrics.length;

        return {
            current: latest,
            average: {
                memory: Math.round(avgMemory),
                uptime: latest.uptime
            },
            totalMetrics: this.metrics.length
        };
    }
}

// 사용 예시
const monitor = new ForeverMonitor();

// 30초마다 메모리 모니터링
setInterval(() => {
    const metric = monitor.monitorMemory();
    console.log('메모리 사용량:', metric.memory.heapUsed, 'MB');
}, 30000);

// 5분마다 리포트 생성
setInterval(() => {
    const report = monitor.generateReport();
    console.log('모니터링 리포트:', report);
}, 300000);
```

### 로그 관리

#### 로그 로테이션 및 관리
```javascript
// log-manager.js
const fs = require('fs');
const path = require('path');

class ForeverLogManager {
    constructor(logDir = './logs') {
        this.logDir = logDir;
        this.maxLogSize = 10 * 1024 * 1024; // 10MB
        this.maxLogFiles = 5;
    }

    // 로그 파일 크기 확인
    checkLogSize(logFile) {
        try {
            const stats = fs.statSync(logFile);
            return stats.size;
        } catch (error) {
            return 0;
        }
    }

    // 로그 로테이션
    rotateLog(logFile) {
        const size = this.checkLogSize(logFile);
        
        if (size > this.maxLogSize) {
            const dir = path.dirname(logFile);
            const ext = path.extname(logFile);
            const base = path.basename(logFile, ext);
            
            // 기존 로그 파일들을 이동
            for (let i = this.maxLogFiles - 1; i > 0; i--) {
                const oldFile = path.join(dir, `${base}.${i}${ext}`);
                const newFile = path.join(dir, `${base}.${i + 1}${ext}`);
                
                if (fs.existsSync(oldFile)) {
                    fs.renameSync(oldFile, newFile);
                }
            }
            
            // 현재 로그 파일을 .1로 이동
            const rotatedFile = path.join(dir, `${base}.1${ext}`);
            fs.renameSync(logFile, rotatedFile);
            
            console.log(`로그 파일 로테이션 완료: ${logFile}`);
        }
    }

    // 모든 로그 파일 로테이션
    rotateAllLogs() {
        const logFiles = [
            path.join(this.logDir, 'out.log'),
            path.join(this.logDir, 'err.log'),
            path.join(this.logDir, 'forever.log')
        ];

        logFiles.forEach(logFile => {
            if (fs.existsSync(logFile)) {
                this.rotateLog(logFile);
            }
        });
    }

    // 오래된 로그 파일 정리
    cleanupOldLogs() {
        const files = fs.readdirSync(this.logDir);
        const now = Date.now();
        const maxAge = 30 * 24 * 60 * 60 * 1000; // 30일

        files.forEach(file => {
            const filePath = path.join(this.logDir, file);
            const stats = fs.statSync(filePath);
            
            if (now - stats.mtime.getTime() > maxAge) {
                fs.unlinkSync(filePath);
                console.log(`오래된 로그 파일 삭제: ${file}`);
            }
        });
    }
}

// 사용 예시
const logManager = new ForeverLogManager();

// 매일 자정에 로그 로테이션
setInterval(() => {
    logManager.rotateAllLogs();
}, 24 * 60 * 60 * 1000);

// 매주 일요일에 오래된 로그 정리
setInterval(() => {
    logManager.cleanupOldLogs();
}, 7 * 24 * 60 * 60 * 1000);
```

### 오류 처리

#### Forever 프로세스 오류 처리
```javascript
// error-handler.js
const fs = require('fs');
const path = require('path');

class ForeverErrorHandler {
    constructor() {
        this.errorLogFile = './logs/errors.log';
        this.errorCounts = new Map();
        this.maxErrors = 5;
        this.errorWindow = 5 * 60 * 1000; // 5분
    }

    // 오류 로그 기록
    logError(error, context = {}) {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            error: error.message,
            stack: error.stack,
            context: context,
            processId: process.pid,
            uptime: process.uptime()
        };

        const logEntry = JSON.stringify(errorEntry) + '\n';
        fs.appendFileSync(this.errorLogFile, logEntry);

        // 오류 카운트 업데이트
        this.updateErrorCount(context.processName || 'unknown');
    }

    // 오류 카운트 업데이트
    updateErrorCount(processName) {
        const now = Date.now();
        const processErrors = this.errorCounts.get(processName) || [];
        
        // 최근 오류만 유지
        const recentErrors = processErrors.filter(time => now - time < this.errorWindow);
        recentErrors.push(now);
        
        this.errorCounts.set(processName, recentErrors);
        
        // 오류 횟수가 임계값을 초과하면 조치
        if (recentErrors.length >= this.maxErrors) {
            this.handleExcessiveErrors(processName, recentErrors.length);
        }
    }

    // 과도한 오류 발생 시 조치
    handleExcessiveErrors(processName, errorCount) {
        console.warn(`프로세스 ${processName}에서 ${errorCount}번의 오류가 발생했습니다.`);
        
        // 알림 전송 (이메일, 슬랙 등)
        this.sendAlert(processName, errorCount);
        
        // 오류 카운트 리셋
        this.errorCounts.delete(processName);
    }

    // 알림 전송
    sendAlert(processName, errorCount) {
        const alert = {
            type: 'error',
            process: processName,
            errorCount: errorCount,
            timestamp: new Date().toISOString(),
            message: `프로세스 ${processName}에서 ${errorCount}번의 오류가 발생했습니다.`
        };

        console.error('알림:', alert);
        
        // 실제 알림 전송 로직 (이메일, 슬랙 등)
        // this.sendEmail(alert);
        // this.sendSlackNotification(alert);
    }

    // 오류 통계 확인
    getErrorStats() {
        const stats = {};
        
        for (const [processName, errors] of this.errorCounts) {
            stats[processName] = {
                errorCount: errors.length,
                lastError: errors[errors.length - 1]
            };
        }
        
        return stats;
    }
}

// 사용 예시
const errorHandler = new ForeverErrorHandler();

// 전역 오류 처리
process.on('uncaughtException', (error) => {
    errorHandler.logError(error, { processName: 'main-process' });
});

process.on('unhandledRejection', (reason, promise) => {
    errorHandler.logError(new Error(reason), { processName: 'main-process' });
});
```

## 참고

### Forever 명령어 요약

#### 기본 명령어
```bash
# 애플리케이션 시작
forever start app.js
forever start -o logs/out.log -e logs/err.log app.js
forever start --uid "my-app" app.js

# 프로세스 관리
forever list                    # 프로세스 목록
forever restart <uid|index>     # 프로세스 재시작
forever stop <uid|index>        # 프로세스 중지
forever stopall                 # 모든 프로세스 중지

# 로그 관리
forever logs                    # 모든 로그
forever logs <uid|index>        # 특정 프로세스 로그
forever logs --plain            # 일반 텍스트 형식

# 설정 파일
forever start forever.json      # 설정 파일로 시작
```

#### 고급 명령어
```bash
# 환경 변수 설정
forever start --env production app.js
forever start --env development app.js

# 로그 파일 지정
forever start -o out.log -e err.log app.js
forever start -l forever.log app.js

# 프로세스 감시
forever start --watch app.js
forever start --watchDirectory ./src app.js

# 메모리 제한
forever start --max-old-space-size=1024 app.js
```

### Forever vs PM2 비교

#### 기능 비교
```javascript
const comparison = {
    'Forever': {
        장점: [
            '간단한 설정',
            '빠른 시작',
            '가벼운 리소스 사용',
            '기본적인 프로세스 관리'
        ],
        단점: [
            '클러스터 모드 없음',
            '제한된 모니터링 기능',
            '무중단 배포 기능 없음',
            '복잡한 설정 제한'
        ],
        적합한_사용_케이스: [
            '간단한 Node.js 애플리케이션',
            '개발 환경',
            '소규모 프로젝트',
            '빠른 프로토타이핑'
        ]
    },
    'PM2': {
        장점: [
            '클러스터 모드 지원',
            '고급 모니터링',
            '무중단 배포',
            '환경별 설정 관리',
            '웹 대시보드'
        ],
        단점: [
            '복잡한 설정',
            '더 많은 리소스 사용',
            '학습 곡선',
            '과도한 기능'
        ],
        적합한_사용_케이스: [
            '프로덕션 환경',
            '대규모 애플리케이션',
            '고가용성 요구',
            '복잡한 시스템'
        ]
    }
};
```

### 결론
Forever는 Node.js 애플리케이션을 간단하고 효율적으로 관리할 수 있는 도구입니다.
자동 재시작, 백그라운드 실행, 로그 관리 등 기본적인 프로세스 관리 기능을 제공합니다.
간단한 설정으로 빠르게 프로세스 관리를 시작할 수 있어 개발 환경이나 소규모 프로젝트에 적합합니다.
PM2와 비교하여 더 가볍고 단순하지만, 고급 기능이 필요한 프로덕션 환경에서는 PM2를 고려하는 것이 좋습니다.
적절한 로그 관리와 모니터링을 통해 안정적인 애플리케이션 운영이 가능합니다.

