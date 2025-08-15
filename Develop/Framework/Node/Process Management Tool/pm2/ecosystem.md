---
title: PM2 Ecosystem File (에코시스템 파일)
tags: [framework, node, process-management-tool, pm2, ecosystem, configuration]
updated: 2025-08-10
---

# PM2 Ecosystem File (에코시스템 파일)

## 배경

### PM2 에코시스템 파일이란?
PM2 에코시스템 파일은 JavaScript나 JSON 형식으로 작성되는 설정 파일로, `ecosystem.config.js`라는 이름의 파일을 사용합니다. 이 파일을 통해 한 번에 여러 애플리케이션을 설정하고, PM2의 다양한 옵션을 체계적으로 관리할 수 있습니다.

### 에코시스템 파일의 필요성
- **중앙 집중식 설정 관리**: 모든 PM2 설정을 하나의 파일에서 관리
- **환경별 설정 분리**: 개발, 스테이징, 프로덕션 환경별 설정 분리
- **복잡한 애플리케이션 관리**: 여러 애플리케이션을 동시에 관리
- **배포 자동화**: CI/CD 파이프라인에서 설정 파일 활용

### 주요 기능
- **클러스터 모드 활성화**: 멀티코어 환경에서 성능 최적화
- **자동 재시작 및 메모리 관리**: 안정적인 애플리케이션 운영
- **환경 변수 설정**: 환경별 설정 분리
- **여러 애플리케이션 관리**: 복잡한 시스템 구성
- **로그 관리 및 파일 감시**: 개발 및 운영 편의성

## 핵심

### 기본 구조 (ecosystem.config.js)

```javascript
module.exports = {
    apps: [
        {
            name: "my-app",              // 애플리케이션 이름
            script: "./app.js",          // 실행할 파일 경로
            instances: "max",            // 모든 CPU 코어를 사용 (클러스터 모드)
            exec_mode: "cluster",        // 클러스터 모드 활성화
            watch: true,                 // 파일 변경 감시 및 자동 재시작
            max_memory_restart: "500M",  // 메모리 사용이 500MB를 초과할 경우 재시작
            env: {                       // 기본 환경 변수 설정
                NODE_ENV: "development"
            },
            env_production: {            // 프로덕션 환경 변수 설정
                NODE_ENV: "production"
            }
        }
    ]
};
```

### 주요 옵션 설명

| 옵션 | 설명 | 예시 |
|------|------|------|
| `name` | 애플리케이션 이름 | `"my-app"` |
| `script` | 실행할 메인 파일 경로 | `"./app.js"` |
| `instances` | 실행할 프로세스 수 | `"max"` (CPU 코어 수만큼) |
| `exec_mode` | 실행 모드 | `"fork"` 또는 `"cluster"` |
| `watch` | 파일 변경 감시 및 자동 재시작 | `true` |
| `max_memory_restart` | 메모리 사용량 초과 시 자동 재시작 | `"500M"` |
| `env` | 개발 환경의 환경 변수 | `{ NODE_ENV: "development" }` |
| `env_production` | 프로덕션 환경의 환경 변수 | `{ NODE_ENV: "production" }` |

### 기본 실행 방법

```bash
# 기본 실행
pm2 start ecosystem.config.js

# 프로덕션 환경에서 실행
pm2 start ecosystem.config.js --env production
```

## 예시

### 단일 애플리케이션 설정

```javascript
// ecosystem.config.js
module.exports = {
    apps: [{
        name: 'express-server',
        script: 'server.js',
        instances: 'max',
        exec_mode: 'cluster',
        env: {
            NODE_ENV: 'development',
            PORT: 3000,
            DB_HOST: 'localhost',
            DB_PORT: 5432
        },
        env_production: {
            NODE_ENV: 'production',
            PORT: 3000,
            DB_HOST: 'production-db.example.com',
            DB_PORT: 5432
        },
        env_staging: {
            NODE_ENV: 'staging',
            PORT: 3000,
            DB_HOST: 'staging-db.example.com',
            DB_PORT: 5432
        },
        max_memory_restart: '1G',
        min_uptime: '10s',
        max_restarts: 10,
        restart_delay: 4000,
        autorestart: true,
        watch: false,
        ignore_watch: ['node_modules', 'logs'],
        error_file: './logs/err.log',
        out_file: './logs/out.log',
        log_file: './logs/combined.log',
        time: true,
        merge_logs: true,
        log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }]
};
```

### 다중 애플리케이션 설정

```javascript
// ecosystem.config.js
module.exports = {
    apps: [
        {
            name: 'api-server',
            script: 'api/server.js',
            instances: 4,
            exec_mode: 'cluster',
            env: {
                NODE_ENV: 'development',
                PORT: 3000,
                DB_HOST: 'localhost',
                DB_PORT: 5432,
                REDIS_URL: 'redis://localhost:6379'
            },
            env_production: {
                NODE_ENV: 'production',
                PORT: 3000,
                DB_HOST: 'production-db.example.com',
                DB_PORT: 5432,
                REDIS_URL: 'redis://production-redis.example.com:6379'
            },
            max_memory_restart: '1G',
            min_uptime: '10s',
            max_restarts: 10,
            restart_delay: 4000,
            autorestart: true,
            watch: false,
            ignore_watch: ['node_modules', 'logs'],
            error_file: './logs/api-err.log',
            out_file: './logs/api-out.log',
            log_file: './logs/api-combined.log',
            time: true,
            merge_logs: true,
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
        },
        {
            name: 'worker',
            script: 'worker/processor.js',
            instances: 2,
            exec_mode: 'cluster',
            env: {
                NODE_ENV: 'development',
                REDIS_URL: 'redis://localhost:6379',
                QUEUE_NAME: 'default'
            },
            env_production: {
                NODE_ENV: 'production',
                REDIS_URL: 'redis://production-redis.example.com:6379',
                QUEUE_NAME: 'production'
            },
            max_memory_restart: '512M',
            min_uptime: '10s',
            max_restarts: 5,
            restart_delay: 2000,
            autorestart: true,
            watch: false,
            error_file: './logs/worker-err.log',
            out_file: './logs/worker-out.log',
            log_file: './logs/worker-combined.log',
            time: true,
            merge_logs: true
        },
        {
            name: 'scheduler',
            script: 'scheduler/cron.js',
            instances: 1,
            exec_mode: 'fork',
            env: {
                NODE_ENV: 'development',
                DB_HOST: 'localhost',
                DB_PORT: 5432
            },
            env_production: {
                NODE_ENV: 'production',
                DB_HOST: 'production-db.example.com',
                DB_PORT: 5432
            },
            max_memory_restart: '256M',
            min_uptime: '10s',
            max_restarts: 3,
            restart_delay: 1000,
            autorestart: true,
            watch: false,
            error_file: './logs/scheduler-err.log',
            out_file: './logs/scheduler-out.log',
            log_file: './logs/scheduler-combined.log',
            time: true,
            merge_logs: true
        }
    ]
};
```

### 고급 설정 예시

```javascript
// ecosystem.config.js
module.exports = {
    apps: [
        {
            name: 'production-app',
            script: 'server.js',
            instances: 'max',
            exec_mode: 'cluster',
            
            // 환경별 설정
            env: {
                NODE_ENV: 'development',
                PORT: 3000,
                LOG_LEVEL: 'debug'
            },
            env_production: {
                NODE_ENV: 'production',
                PORT: 3000,
                LOG_LEVEL: 'info',
                DB_URL: 'postgresql://user:pass@host:5432/db',
                REDIS_URL: 'redis://host:6379',
                JWT_SECRET: 'your-secret-key'
            },
            
            // 성능 최적화
            max_memory_restart: '1G',
            min_uptime: '10s',
            max_restarts: 10,
            restart_delay: 4000,
            autorestart: true,
            
            // 파일 감시 설정
            watch: false,
            ignore_watch: [
                'node_modules',
                'logs',
                '*.log',
                'uploads',
                'temp'
            ],
            
            // 로그 설정
            error_file: '/var/log/pm2/err.log',
            out_file: '/var/log/pm2/out.log',
            log_file: '/var/log/pm2/combined.log',
            time: true,
            merge_logs: true,
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
            
            // 무중단 배포 설정
            wait_ready: true,
            listen_timeout: 10000,
            kill_timeout: 5000,
            health_check_grace_period: 3000,
            
            // 추가 옵션
            source_map_support: true,
            node_args: '--max-old-space-size=1024',
            cwd: '/var/www/app',
            uid: 'www-data',
            gid: 'www-data'
        }
    ]
};
```

### 개발 환경 설정

```javascript
// ecosystem.config.js
module.exports = {
    apps: [
        {
            name: 'dev-server',
            script: 'server.js',
            instances: 1,
            exec_mode: 'fork',
            
            // 개발 환경 설정
            env: {
                NODE_ENV: 'development',
                PORT: 3000,
                DB_HOST: 'localhost',
                DB_PORT: 5432,
                REDIS_URL: 'redis://localhost:6379',
                LOG_LEVEL: 'debug'
            },
            
            // 개발 편의 기능
            watch: true,
            ignore_watch: [
                'node_modules',
                'logs',
                '*.log',
                '.git'
            ],
            
            // 로그 설정
            error_file: './logs/dev-err.log',
            out_file: './logs/dev-out.log',
            log_file: './logs/dev-combined.log',
            time: true,
            merge_logs: true,
            
            // 개발용 성능 설정
            max_memory_restart: '512M',
            min_uptime: '5s',
            max_restarts: 5,
            restart_delay: 2000,
            autorestart: true
        }
    ]
};
```

## 운영 팁

### 성능 최적화

#### 메모리 및 CPU 설정
```javascript
// ecosystem.config.js
module.exports = {
    apps: [{
        name: 'optimized-app',
        script: 'server.js',
        instances: 'max',
        exec_mode: 'cluster',
        
        // 메모리 최적화
        max_memory_restart: '1G',
        node_args: '--max-old-space-size=1024',
        
        // CPU 최적화
        instances: 4, // CPU 코어 수에 맞게 조정
        
        // 재시작 정책
        min_uptime: '10s',
        max_restarts: 10,
        restart_delay: 4000,
        autorestart: true,
        
        // 환경 변수
        env_production: {
            NODE_ENV: 'production',
            PORT: 3000,
            UV_THREADPOOL_SIZE: 64, // Node.js 스레드풀 크기
            NODE_OPTIONS: '--max-old-space-size=1024'
        }
    }]
};
```

### 로그 관리

#### 로그 설정 최적화
```javascript
// ecosystem.config.js
module.exports = {
    apps: [{
        name: 'logging-app',
        script: 'server.js',
        
        // 로그 파일 설정
        error_file: '/var/log/pm2/err.log',
        out_file: '/var/log/pm2/out.log',
        log_file: '/var/log/pm2/combined.log',
        
        // 로그 옵션
        time: true,
        merge_logs: true,
        log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
        
        // 로그 로테이션 (PM2 로그로테이트 플러그인과 함께 사용)
        log_type: 'json',
        
        // 환경별 로그 레벨
        env: {
            NODE_ENV: 'development',
            LOG_LEVEL: 'debug'
        },
        env_production: {
            NODE_ENV: 'production',
            LOG_LEVEL: 'info'
        }
    }]
};
```

### 무중단 배포

#### 무중단 배포 설정
```javascript
// ecosystem.config.js
module.exports = {
    apps: [{
        name: 'zero-downtime-app',
        script: 'server.js',
        instances: 'max',
        exec_mode: 'cluster',
        
        // 무중단 배포 설정
        wait_ready: true,
        listen_timeout: 10000,
        kill_timeout: 5000,
        health_check_grace_period: 3000,
        
        // 헬스체크 엔드포인트 설정
        env_production: {
            NODE_ENV: 'production',
            PORT: 3000,
            HEALTH_CHECK_PATH: '/health'
        }
    }]
};
```

```javascript
// server.js (무중단 배포를 위한 준비 신호)
const express = require('express');
const app = express();

// 헬스체크 엔드포인트
app.get('/health', (req, res) => {
    res.status(200).json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

app.listen(process.env.PORT || 3000, () => {
    console.log('Server started');
    
    // PM2에게 준비 완료 신호 전송
    if (process.send) {
        process.send('ready');
    }
});
```

## 참고

### 환경별 실행 명령어

#### 기본 실행
```bash
# 개발 환경
pm2 start ecosystem.config.js

# 프로덕션 환경
pm2 start ecosystem.config.js --env production

# 스테이징 환경
pm2 start ecosystem.config.js --env staging
```

#### 고급 실행 옵션
```bash
# 특정 앱만 실행
pm2 start ecosystem.config.js --only api-server

# 모든 앱 재시작
pm2 restart ecosystem.config.js

# 특정 환경으로 재시작
pm2 restart ecosystem.config.js --env production

# 앱 중지
pm2 stop ecosystem.config.js

# 앱 삭제
pm2 delete ecosystem.config.js
```

### 에코시스템 파일 검증

#### 설정 검증 도구
```javascript
// validate-ecosystem.js
const ecosystem = require('./ecosystem.config.js');

function validateEcosystem() {
    const errors = [];
    
    if (!ecosystem.apps || !Array.isArray(ecosystem.apps)) {
        errors.push('apps 배열이 필요합니다.');
        return errors;
    }
    
    ecosystem.apps.forEach((app, index) => {
        if (!app.name) {
            errors.push(`앱 ${index}: name이 필요합니다.`);
        }
        
        if (!app.script) {
            errors.push(`앱 ${index}: script가 필요합니다.`);
        }
        
        if (app.instances && typeof app.instances !== 'number' && app.instances !== 'max') {
            errors.push(`앱 ${index}: instances는 숫자 또는 'max'여야 합니다.`);
        }
        
        if (app.exec_mode && !['fork', 'cluster'].includes(app.exec_mode)) {
            errors.push(`앱 ${index}: exec_mode는 'fork' 또는 'cluster'여야 합니다.`);
        }
    });
    
    return errors;
}

const errors = validateEcosystem();
if (errors.length > 0) {
    console.error('에코시스템 파일 오류:');
    errors.forEach(error => console.error(`- ${error}`));
    process.exit(1);
} else {
    console.log('에코시스템 파일이 유효합니다.');
}
```

### 결론
PM2 에코시스템 파일은 Node.js 애플리케이션의 설정을 체계적으로 관리할 수 있는 강력한 도구입니다.
환경별 설정 분리, 다중 애플리케이션 관리, 성능 최적화 등 다양한 기능을 제공합니다.
적절한 설정을 통해 안정적이고 확장 가능한 Node.js 애플리케이션을 운영할 수 있습니다.
무중단 배포, 로그 관리, 모니터링 등 프로덕션 환경에 필요한 모든 기능을 설정할 수 있습니다.
CI/CD 파이프라인과 통합하여 자동화된 배포 프로세스를 구축할 수 있습니다.






