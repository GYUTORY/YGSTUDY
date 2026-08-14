---
title: PM2 Ecosystem File (에코시스템 파일)
tags: [nodejs, devops]
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

#### `env` 는 "개발 환경"이 아니라 **모든 환경의 바탕**이다

이름 때문에 `env` = 개발용, `env_production` = 운영용으로 갈린다고 읽기 쉽다. 아니다. `--env production` 은 **`env` 위에 `env_production` 을 덮어쓴다.** `env` 에만 있는 키는 운영에서도 그대로 살아 있다.

```javascript
// 확인용 설정
env:            { NODE_ENV: 'development', ONLY_IN_ENV: 'yes', DB_HOST: 'localhost' },
env_production: { NODE_ENV: 'production',                      DB_HOST: 'prod-db'   }
```

```
$ pm2 start ecosystem.config.js
NODE_ENV=development ONLY_IN_ENV=yes DB_HOST=localhost

$ pm2 restart ecosystem.config.js --env production
NODE_ENV=production ONLY_IN_ENV=yes DB_HOST=prod-db
```

(PM2 7.0.3 실측)

`ONLY_IN_ENV` 가 운영까지 따라왔다. 그래서 `env` 에 디버그 플래그나 로컬 DB 주소를 넣어두면 **운영에서 조용히 살아난다.** `env_production` 에서 반드시 덮어쓰거나, 애초에 `env` 를 비워 두고 프로필마다 전부 명시한다.

#### 없는 프로필 이름을 주면 경고 없이 `env` 로 떨어진다

이게 더 위험하다. `env_staging` 을 정의하지 않은 설정에 `--env staging` 을 줘도, 오타로 `--env prod` 라고 써도, PM2 는 아무 말 없이 기본 `env` 로 띄운다.

```
$ pm2 start ecosystem.config.js --env staging     # env_staging 없음
NODE_ENV=development ONLY_IN_ENV=yes DB_HOST=localhost

$ pm2 start ecosystem.config.js --env prod        # production 오타
NODE_ENV=development ONLY_IN_ENV=yes DB_HOST=localhost
```

에러도 경고도 없다. 운영 배포 명령을 한 글자 틀리면 개발 설정으로 뜨는데 `pm2 list` 는 초록불이다. 배포 스크립트에 프로필 이름을 하드코딩하고, 앱 부팅 로그에 `NODE_ENV` 를 반드시 찍는다.

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

위 설정의 `JWT_SECRET: 'your-secret-key'` 와 `DB_URL: 'postgresql://user:pass@host:5432/db'` 는 그대로 두면 안 된다. **에코시스템 파일은 저장소에 커밋되는 코드다.** 비밀값은 파일 밖에 두고 프로세스 환경변수나 시크릿 매니저에서 읽는다.

```javascript
env_production: {
    NODE_ENV: 'production',
    JWT_SECRET: process.env.JWT_SECRET,   // 셸 환경에서 주입
}
```

`ecosystem.config.js` 는 JSON 이 아니라 **PM2 가 `require` 하는 자바스크립트 모듈**이라 이렇게 코드를 쓸 수 있다. 다만 이 파일이 평가되는 시점은 `pm2 start` 를 실행한 셸이라, 그 셸에 값이 없으면 `undefined` 가 조용히 들어간다. 값이 비면 부팅을 실패시키는 검증을 앱 진입점에 둔다.

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

이 설정에는 **`instances` 가 두 번 있다.** 위에서 `'max'`, 아래에서 `4`. 자바스크립트 객체 리터럴은 뒤에 온 키가 이긴다.

```
$ node -e "const o={instances:'max', exec_mode:'cluster', instances:4};
> console.log(o.instances, Object.keys(o).join(','))"
4 instances,exec_mode
```

에러도 경고도 없이 `'max'` 가 사라진다. `Object.keys` 에도 키는 하나뿐이라 나중에 설정을 덤프해 봐도 흔적이 없다. 설정 파일이 길어지면 이런 중복이 눈에 안 띈다 — ESLint 의 `no-dupe-keys` 를 설정 파일에도 걸어 두면 잡힌다.

`instances: 4` 를 넣을 거면 `'max'` 줄을 지운다. 둘 다 남겨두고 "위에 max 라고 써 있으니 코어를 다 쓰겠지"라고 읽는 게 이 버그의 본체다.

`UV_THREADPOOL_SIZE: 64` 도 그냥 크게 잡을 값이 아니다. 클러스터 인스턴스는 **각각 독립된 OS 프로세스**라(`pm2 list` 의 pid 가 전부 다르다) 이 값은 인스턴스 수만큼 곱해서 붙는다. 인스턴스 4개면 프로세스 4개가 각자 64짜리 스레드풀을 든다.

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

**`wait_ready: true` 를 켜놓고 `process.send('ready')` 를 빠뜨리면 앱은 그냥 뜬다.** 실패하지 않는다는 게 함정이다. PM2 는 `listen_timeout` 만큼 기다렸다가 포기하고 online 으로 표시한다.

```
$ pm2 start eco2.config.js          # wait_ready: true, listen_timeout: 3000, ready 신호 없음
pm2 start 반환까지 걸린 시간(초): 3
status: online  restarts: 0
```

`status: online` 이라 모니터링에도 안 걸린다. 대신 배포가 느려진다. `pm2 reload` 는 인스턴스를 하나씩 갈아끼우면서 매번 이 대기를 반복한다. `listen_timeout: 2000` 으로 재보면:

| instances | reload 소요 |
|---|---|
| 1 | 4.4초 |
| 2 | 8.6초 |
| 4 | 8.6초 |

(PM2 7.0.3, ready 신호 없는 앱. 인스턴스가 늘어도 무한정 늘지는 않는 걸 보면 PM2 가 일정 개수씩 묶어 처리한다)

문서 예시대로 `listen_timeout: 10000` 을 주고 ready 신호를 안 보내면 배포 때마다 이만큼을 그냥 버린다. **`wait_ready` 를 켰으면 앱에 `process.send('ready')` 가 실제로 있는지 확인한다** — 켰는지 여부는 설정 파일에, 보내는지 여부는 앱 코드에 있어서 둘이 따로 논다.

반대 방향도 있다. 같은 앱에서 `wait_ready` 만 빼고 재보면:

```
wait_ready 없음, instances=2 → reload 0.6초
```

PM2 가 **준비 여부를 확인하지 않고 곧장 다음 인스턴스로 넘어가서** 이렇게 빠른 것이다. 앱이 아직 DB 연결도 못 했는데 앞 인스턴스는 이미 내려간 상태가 되어, 무중단 배포라고 해놓고 배포 창에서 에러가 난다. 이 옵션의 값은 여기에 있다 — 켜되, 신호를 실제로 보낸다.

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






