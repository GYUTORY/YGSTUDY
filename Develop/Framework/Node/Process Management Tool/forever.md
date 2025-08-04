
# Node.js Forever - 프로세스 관리 도구

## 📋 개요
**Forever**는 Node.js 애플리케이션을 백그라운드에서 지속적으로 실행하고 관리하는 명령줄 도구입니다.

### 🎯 주요 기능
- ✅ **자동 재시작**: 애플리케이션 크래시 시 자동 복구
- ✅ **백그라운드 실행**: 터미널 종료 후에도 계속 실행
- ✅ **프로세스 모니터링**: 실행 상태 실시간 감시
- ✅ **로그 관리**: 애플리케이션 로그 수집 및 관리

---

## 🚀 설치 및 설정

### 1. 설치
```bash
npm install -g forever
```

### 2. 버전 확인
```bash
forever --version
```

---

## 📖 기본 사용법

### 애플리케이션 시작
```bash
# 기본 시작
forever start app.js

# 포트 지정
forever start app.js --port 3000

# 환경변수 설정
forever start app.js --env production
```

### 프로세스 관리
```bash
# 실행 중인 프로세스 목록
forever list

# 특정 프로세스 재시작
forever restart 0
forever restart app.js

# 특정 프로세스 중지
forever stop 0
forever stop app.js

# 모든 프로세스 중지
forever stopall
```

### 로그 관리
```bash
# 로그 확인
forever logs

# 특정 프로세스 로그
forever logs 0

# 로그 파일 경로 확인
forever logs --plain
```

---

## 💻 실전 예제

### 1. Express 서버 애플리케이션
```javascript
// app.js
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.json({
        message: 'Hello from Forever!',
        timestamp: new Date().toISOString(),
        pid: process.pid
    });
});

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK' });
});

app.listen(PORT, () => {
    console.log(`🚀 서버 시작: http://localhost:${PORT}`);
    console.log(`📊 PID: ${process.pid}`);
});
```

### 2. Forever 실행 스크립트
```bash
#!/bin/bash
# start-server.sh

echo "🔄 Node.js 서버를 Forever로 시작합니다..."

# 기존 프로세스 정리
forever stopall

# 새 프로세스 시작
forever start \
    --uid "my-app" \
    --name "my-node-app" \
    --minUptime 1000 \
    --spinSleepTime 1000 \
    app.js

echo "✅ 서버가 시작되었습니다."
forever list
```

### 3. 프로덕션 환경 설정
```bash
# 프로덕션 환경에서 실행
forever start \
    --uid "production-app" \
    --name "production-server" \
    --env production \
    --minUptime 5000 \
    --spinSleepTime 2000 \
    --max 3 \
    app.js
```

---

## ⚙️ 고급 설정 옵션

### Forever 설정 파일 (forever.json)
```json
{
    "uid": "my-app",
    "append": true,
    "watch": false,
    "script": "app.js",
    "sourceDir": "/path/to/app",
    "logFile": "/var/log/forever/my-app.log",
    "outFile": "/var/log/forever/my-app-out.log",
    "errorFile": "/var/log/forever/my-app-error.log",
    "minUptime": "10s",
    "spinSleepTime": "2s",
    "max": 3,
    "env": {
        "NODE_ENV": "production",
        "PORT": 3000
    }
}
```

### 주요 옵션 설명
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--uid` | 프로세스 고유 식별자 | 파일명 |
| `--name` | 프로세스 표시 이름 | 파일명 |
| `--minUptime` | 최소 실행 시간 (재시작 기준) | 1000ms |
| `--spinSleepTime` | 재시작 간 대기 시간 | 1000ms |
| `--max` | 최대 재시작 횟수 | 무제한 |
| `--watch` | 파일 변경 감지 | false |
| `--env` | 환경변수 설정 | development |

---

## 📊 모니터링 및 관리

### 프로세스 상태 확인
```bash
# 상세 정보 포함 목록
forever list --plain

# JSON 형식 출력
forever list --json
```

### 로그 파일 관리
```bash
# 로그 파일 위치 확인
forever logs --plain

# 로그 파일 크기 확인
ls -lh ~/.forever/*.log

# 로그 파일 정리
forever cleanlogs
```

### 성능 모니터링
```bash
# CPU/메모리 사용량 확인
ps aux | grep node

# 포트 사용 확인
netstat -tlnp | grep :3000
```

---

## 🔧 문제 해결

### 일반적인 문제들

#### 1. 포트 충돌
```bash
# 포트 사용 확인
lsof -i :3000

# 강제 종료
kill -9 $(lsof -t -i:3000)
```

#### 2. 권한 문제
```bash
# 로그 디렉토리 권한 설정
sudo mkdir -p /var/log/forever
sudo chown $USER:$USER /var/log/forever
```

#### 3. 메모리 누수
```bash
# 메모리 사용량 모니터링
forever list --plain | grep -E "(memory|heap)"
```

---

## 📈 Forever vs PM2 비교

| 기능 | Forever | PM2 |
|------|---------|-----|
| **설치 복잡도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **사용 편의성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **클러스터링** | ❌ | ✅ |
| **로드 밸런싱** | ❌ | ✅ |
| **메트릭 대시보드** | ❌ | ✅ |
| **환경별 설정** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **로그 관리** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 언제 Forever를 사용할까?
- 🎯 **간단한 프로젝트**: 복잡한 설정이 필요 없는 경우
- 🚀 **빠른 프로토타이핑**: 빠른 개발 및 테스트 환경
- 💡 **학습 목적**: Node.js 프로세스 관리 기초 학습
- 🔧 **단일 서버**: 클러스터링이 필요 없는 경우

---

## 🛡️ 보안 및 모범 사례

### 보안 설정
```bash
# 특정 사용자로 실행
forever start --uid "app-user" app.js

# 환경변수 파일 사용
forever start --env-file .env app.js
```

### 로그 보안
```bash
# 민감한 정보 필터링
forever start app.js 2>&1 | grep -v "password\|token"
```

### 정기적인 관리
```bash
# 주간 로그 정리
0 2 * * 0 forever cleanlogs

# 월간 프로세스 재시작
0 3 1 * * forever restartall
```

---

## 📚 추가 리소스

### 유용한 명령어 모음
```bash
# 전체 프로세스 재시작
forever restartall

# 특정 조건으로 재시작
forever restart app.js --env production

# 로그 실시간 모니터링
forever logs -f

# 설정 파일로 시작
forever start forever.json
```

### 관련 도구
- **PM2**: 고급 프로세스 관리
- **nodemon**: 개발 환경 자동 재시작
- **supervisor**: Python 기반 프로세스 관리

---

## 🎉 결론

Forever는 Node.js 애플리케이션의 안정적인 운영을 위한 **간단하고 효과적인 도구**입니다. 

### 핵심 장점
- ✅ **간편한 설치 및 사용**
- ✅ **안정적인 프로세스 관리**
- ✅ **자동 복구 기능**
- ✅ **백그라운드 실행 지원**

### 권장 사용 시나리오
- 🎯 개발 및 테스트 환경
- 🚀 소규모 프로덕션 서버
- 💡 Node.js 학습 및 실습
- 🔧 단일 애플리케이션 운영
